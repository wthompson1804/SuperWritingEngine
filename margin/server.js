'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { open, helpers } = require('./lib/db');
const { seed } = require('./lib/seed');
const { render, esc } = require('./lib/markdown');
const { checkDraft } = require('./lib/draftcheck');
const auth = require('./lib/auth');
const signals = require('./lib/signals');
const views = require('./lib/views');
const ring = require('./lib/ring');
const { importSubstack, exportAuthor } = require('./lib/portability');
const { toCsv } = require('./lib/csv');
const ap = require('./lib/activitypub');

const STATIC = path.join(__dirname, 'public');
const MIME = { '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8' };
const SECURITY_HEADERS = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

class HttpError extends Error { constructor(status, msg) { super(msg); this.status = status; } }

function createApp({ dbFile = process.env.MARGIN_DB || path.join(__dirname, 'data', 'margin.db'), demoSignals = process.env.MARGIN_DEMO_SIGNALS !== '0', secureCookies = process.env.MARGIN_SECURE_COOKIES === '1',
  // No mail provider is wired up, so by default the confirmation link is shown on screen
  // instead of being emailed. Set MARGIN_SHOW_MAIL=0 once real delivery exists.
  showMail = process.env.MARGIN_SHOW_MAIL !== '0',
  // The canonical public URL. Fediverse ids must be stable, so set this in
  // production (e.g. https://margin.example). Falls back to the request host.
  publicUrl = process.env.MARGIN_PUBLIC_URL || '',
  // Tests and local development federate over http with private addresses.
  apInsecure = process.env.MARGIN_AP_INSECURE === '1' } = {}) {
  const h = helpers(open(dbFile));
  seed(h, { demoSignals });

  // In-memory rate limit for anonymous writes. IPs are never persisted.
  const buckets = new Map();
  function limited(ip, max = 120) {
    const now = Date.now();
    const b = buckets.get(ip);
    if (!b || now - b.t > 60000) { buckets.set(ip, { t: now, n: 1 }); return false; }
    b.n += 1;
    return b.n > max;
  }
  setInterval(() => { const cut = Date.now() - 60000; for (const [k, b] of buckets) if (b.t < cut) buckets.delete(k); }, 60000).unref();

  // ---------- helpers ----------
  const send = (res, status, body, headers = {}) => {
    res.writeHead(status, { ...SECURITY_HEADERS, ...headers });
    res.end(body);
  };
  const html = (res, body, status = 200, headers = {}) => send(res, status, body, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', ...headers });
  const json = (res, obj, status = 200) => send(res, status, JSON.stringify(obj), { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
  const redirect = (res, to, headers = {}) => send(res, 303, '', { Location: to, ...headers });

  async function readBody(req, limit = 1_000_000) {
    const chunks = [];
    let size = 0;
    for await (const c of req) {
      size += c.length;
      if (size > limit) throw new HttpError(413, 'Too large');
      chunks.push(c);
    }
    const text = Buffer.concat(chunks).toString('utf8');
    const type = String(req.headers['content-type'] || '');
    if (type.includes('application/json') || type.includes('text/plain')) {
      try { return text ? JSON.parse(text) : {}; } catch { throw new HttpError(400, 'Bad JSON'); }
    }
    return Object.fromEntries(new URLSearchParams(text));
  }

  async function readRaw(req, limit) {
    const chunks = [];
    let size = 0;
    for await (const c of req) {
      size += c.length;
      if (size > limit) throw new HttpError(413, 'That file is too large (50 MB max).');
      chunks.push(c);
    }
    return Buffer.concat(chunks);
  }

  const baseUrl = (req) => publicUrl.replace(/\/$/, '') || `${req.headers['x-forwarded-proto'] === 'https' ? 'https' : 'http'}://${req.headers.host}`;
  const fed = ap.createFederation(h, { allowHttp: apInsecure, allowPrivate: apInsecure, log: (m) => console.warn('[ap]', m) });
  const apJson = (res, obj, status = 200, type = 'application/activity+json') => send(res, status, JSON.stringify(obj), { 'Content-Type': `${type}; charset=utf-8`, 'Cache-Control': 'max-age=60', 'Access-Control-Allow-Origin': '*' });
  const queueMail = (to, subject, body, kind) => h.run('INSERT INTO mail (to_email, subject, body, kind, created_at) VALUES (?,?,?,?,?)', to, subject, body, kind, Date.now());
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function reach(authorId) {
    return {
      email: h.get(`SELECT count(*) AS n FROM email_subs WHERE author_id = ? AND status = 'active'`, authorId).n,
      fedi: h.get('SELECT count(*) AS n FROM ap_followers WHERE author_id = ?', authorId).n,
    };
  }
  const reachText = (authorId) => {
    const r = reach(authorId);
    return `It went to ${r.email} email follower${r.email === 1 ? '' : 's'} and ${r.fedi} fediverse follower${r.fedi === 1 ? '' : 's'}; everyone else sees it on your homepage and in the ring.`;
  };

  // Everything that happens the first time a piece goes public: email to
  // confirmed followers, and a Create to fediverse followers. Used by the
  // editor and by the scheduler.
  let lastBase = '';
  function publishNow(postId, base) {
    const post = h.get('SELECT * FROM posts WHERE id = ?', postId);
    if (!post) return;
    const first = !post.published_at;
    h.run(`UPDATE posts SET status = 'published', publish_at = NULL, published_at = coalesce(published_at, ?) WHERE id = ?`, Date.now(), postId);
    if (!first) return;
    const author = h.get('SELECT * FROM authors WHERE id = ?', post.author_id);
    const fresh = h.get('SELECT * FROM posts WHERE id = ?', postId);
    fed.publish(base, author, fresh);
    for (const sub of h.all(`SELECT email, token FROM email_subs WHERE author_id = ? AND status = 'active'`, author.id)) {
      queueMail(sub.email, `New from ${author.name}: ${fresh.title}`,
        `${fresh.title}\n${fresh.dek}\n\nRead it: ${base}/p/${fresh.slug}?via=follow\n\nYou get this because you asked for ${author.name}'s new pieces. One click stops it: ${base}/unsubscribe/${sub.token}`, 'new-post');
    }
  }

  // Background jobs: scheduled posts, and one reminder for unconfirmed email
  // follows (about 6 in 10 double opt-ins go unconfirmed without one).
  function runJobs(now = Date.now()) {
    const base = publicUrl.replace(/\/$/, '') || lastBase;
    if (!base) return;
    for (const p of h.all(`SELECT id FROM posts WHERE status = 'scheduled' AND publish_at <= ?`, now)) publishNow(p.id, base);
    for (const sub of h.all(`SELECT s.id, s.email, s.token, a.name FROM email_subs s JOIN authors a ON a.id = s.author_id
                             WHERE s.status = 'pending' AND s.reminded_at IS NULL AND s.created_at < ? AND s.created_at > ?`, now - 86400000, now - 7 * 86400000)) {
      queueMail(sub.email, `Still want ${sub.name}'s new pieces?`, `You asked to get ${sub.name}'s new pieces by email but haven't confirmed yet.\n\nConfirm: ${base}/confirm/${sub.token}\n\nIf you've changed your mind, ignore this. We won't ask again.`, 'reminder');
      h.run('UPDATE email_subs SET reminded_at = ? WHERE id = ?', now, sub.id);
    }
  }
  setInterval(runJobs, 30000).unref();

  const MEDIA_DIR = dbFile === ':memory:' ? path.join(require('node:os').tmpdir(), `margin-media-${process.pid}`) : path.join(path.dirname(dbFile), 'media');
  // Accept only formats we can recognize by their first bytes.
  function sniffImage(buf) {
    if (buf.length > 8 && buf.readUInt32BE(0) === 0x89504e47) return ['image/png', 'png'];
    if (buf.length > 3 && buf[0] === 0xff && buf[1] === 0xd8 && buf[2] === 0xff) return ['image/jpeg', 'jpg'];
    if (buf.length > 6 && /^GIF8[79]a/.test(buf.toString('latin1', 0, 6))) return ['image/gif', 'gif'];
    if (buf.length > 12 && buf.toString('latin1', 0, 4) === 'RIFF' && buf.toString('latin1', 8, 12) === 'WEBP') return ['image/webp', 'webp'];
    return null;
  }

  function currentAuthor(req) {
    const t = auth.parseCookies(req.headers.cookie).ms;
    if (!t) return null;
    return h.get('SELECT a.id, a.handle, a.name, a.bio, a.accent FROM sessions s JOIN authors a ON a.id = s.author_id WHERE s.token = ?', t) || null;
  }
  const sessionCookie = (tok, maxAge) => `ms=${tok}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secureCookies ? '; Secure' : ''}`;

  const publishedPost = (slug) => h.get(`SELECT * FROM posts WHERE slug = ? AND status = 'published'`, String(slug || ''));
  const readerByKey = (key) => { const kh = auth.hashKey(key); return kh ? h.get('SELECT * FROM readers WHERE key_hash = ?', kh) : null; };

  function slugify(title, exceptId) {
    const base = String(title).toLowerCase().normalize('NFKD').replace(/[^\w\s-]/g, '').trim().replace(/[\s_-]+/g, '-').slice(0, 80) || 'untitled';
    let slug = base; let n = 2;
    while (h.get('SELECT id FROM posts WHERE slug = ? AND id != ?', slug, exceptId || -1)) slug = `${base}-${n++}`;
    return slug;
  }

  // Merge two commonplace blobs entry by entry; newest timestamp wins.
  function mergeData(a, b) {
    const out = {};
    for (const k of ['kept', 'follows', 'finished']) {
      const m = { ...(a?.[k] || {}) };
      for (const [id, v] of Object.entries(b?.[k] || {})) {
        if (!v || typeof v !== 'object') continue;
        if (!m[id] || (Number(v.ts) || 0) >= (Number(m[id].ts) || 0)) m[id] = v;
      }
      out[k] = m;
    }
    return out;
  }

  function syncFollows(reader, follows) {
    for (const [handle, f] of Object.entries(follows || {})) {
      const a = h.get('SELECT id FROM authors WHERE handle = ?', handle);
      if (!a) continue;
      if (f.on) h.run('INSERT OR IGNORE INTO reader_follows (reader_id, author_id, created_at) VALUES (?,?,?)', reader.id, a.id, Number(f.ts) || Date.now());
      else h.run('DELETE FROM reader_follows WHERE reader_id = ? AND author_id = ?', reader.id, a.id);
    }
  }

  const prefsOf = (r) => ({ email: r.email || '', digest: !!r.digest, share_email: !!r.share_email });

  // ---------- routes ----------
  const routes = [];
  const on = (method, pattern, fn) => routes.push({ method, pattern, fn });

  on('GET', /^\/$/, (req, res, m, ctx) => {
    const picks = signals.frontPage(h);
    html(res, views.home({ picks, author: ctx.author, liveNow: ring.readingNow(h), spot: ring.spotlight(h), now: Date.now() }));
  });

  on('GET', /^\/p\/([\w-]+)$/, (req, res, m, ctx) => {
    const post = publishedPost(m[1]);
    if (!post) return html(res, views.notFound({ viewer: ctx.author }), 404);
    if (ap.wantsActivityJson(req)) {
      const a = h.get('SELECT * FROM authors WHERE id = ?', post.author_id);
      return apJson(res, { '@context': 'https://www.w3.org/ns/activitystreams', ...ap.articleJson(baseUrl(req), a, post) });
    }
    const author = h.get('SELECT id, handle, name, bio, accent, blogroll FROM authors WHERE id = ?', post.author_id);
    const rendered = render(post.body_md);
    const notes = h.all('SELECT id, para, display_name, quote, body, created_at FROM notes WHERE post_id = ? AND hidden = 0 ORDER BY created_at', post.id);
    const passP = ctx.url.searchParams.get('via') === 'passed' ? Number(ctx.url.searchParams.get('p')) : NaN;
    const passage = Number.isInteger(passP) ? rendered.blocks[passP]?.text : null;
    const kc = h.all('SELECT para, count(*) AS n FROM keeps WHERE post_id = ? GROUP BY para ORDER BY n DESC', post.id);
    const keepCounts = Object.fromEntries(kc.map((r) => [r.para, r.n]));
    const topKeep = kc[0] && kc[0].n >= 3 ? { para: kc[0].para, n: kc[0].n } : null;
    const reads = h.get(`SELECT count(*) AS n FROM views WHERE post_id = ? AND max_depth >= 0.9 AND dwell_ms >= ?`, post.id, post.words * signals.MS_PER_WORD_FLOOR).n;
    html(res, views.article({ post, author, rendered, notes, topKeep, keepCounts, next: signals.nextReads(h, post), viewer: ctx.author,
      stats: { now: ring.readingNow(h, post.id), reads }, blogroll: ring.parseBlogroll(h, author.blogroll),
      og: { url: `${baseUrl(req)}/p/${post.slug}`, passage, fediHandle: `@${author.handle}@${new URL(baseUrl(req)).host}`,
        published: ctx.author && ctx.author.id === post.author_id && ctx.url.searchParams.has('published') ? reachText(post.author_id) : '' } }));
  });

  on('GET', /^\/@([\w]+)$/, (req, res, m, ctx) => {
    const author = h.get('SELECT id, handle, name, bio, now_line, accent, blogroll, created_at FROM authors WHERE handle = ?', m[1].toLowerCase());
    if (!author) return html(res, views.notFound({ viewer: ctx.author }), 404);
    if (ap.wantsActivityJson(req)) return apJson(res, ap.actorJson(h, baseUrl(req), author));
    const posts = h.all(`SELECT slug, title, dek, words, published_at FROM posts WHERE author_id = ? AND status = 'published' ORDER BY published_at DESC`, author.id);
    const recommendedBy = h.all('SELECT handle, name, blogroll FROM authors WHERE id != ?', author.id)
      .filter((a) => a.blogroll.split('\n').map((l) => l.trim().toLowerCase()).includes('@' + author.handle));
    html(res, views.authorPage({ author, posts, viewer: ctx.author, blogroll: ring.parseBlogroll(h, author.blogroll), recommendedBy,
      fediHandle: `@${author.handle}@${new URL(baseUrl(req)).host}` }));
  });

  on('GET', /^\/ring$/, (req, res, m, ctx) => html(res, views.ringPage({ ring: ring.ringOrder(h), viewer: ctx.author })));
  on('GET', /^\/ring\/(next|prev|random)$/, (req, res, m, ctx) => {
    const to = ring.ringStep(h, String(ctx.url.searchParams.get('from') || ''), m[1]);
    redirect(res, to ? `/@${to.handle}?via=ring` : '/ring');
  });
  on('GET', /^\/declaration$/, (req, res, m, ctx) => html(res, views.declaration({ viewer: ctx.author })));

  on('GET', /^\/commonplace$/, (req, res, m, ctx) => html(res, views.commonplace({ viewer: ctx.author })));
  on('GET', /^\/brief$/, (req, res, m, ctx) => html(res, views.brief({ picks: signals.frontPage(h).slice(0, 5), viewer: ctx.author })));
  on('GET', /^\/about$/, (req, res, m, ctx) => html(res, views.about({ viewer: ctx.author })));

  // The Brief as RSS: same five pieces, no email needed.
  on('GET', /^\/brief\.xml$/, (req, res) => {
    const base = baseUrl(req);
    const picks = signals.frontPage(h).slice(0, 5);
    const items = picks.map((p) => `<item><title>${esc(p.title)}</title><link>${base}/p/${p.slug}?via=brief</link><guid isPermaLink="false">brief:${p.slug}</guid>
<dc:creator>${esc(p.author_name)}</dc:creator><description>${esc(p.dek)} (${p.minutes} min)</description></item>`).join('\n');
    send(res, 200, `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
<title>The Brief · Margin</title><link>${base}/brief</link><description>Five pieces at most. When you've read them, you're done.</description>
${items}
</channel></rss>`, { 'Content-Type': 'application/rss+xml; charset=utf-8' });
  });

  on('GET', /^\/feed\.xml$/, (req, res, m, ctx) => {
    const handle = ctx.url.searchParams.get('author');
    const rows = h.all(`SELECT p.*, a.name AS author_name, a.handle FROM posts p JOIN authors a ON a.id = p.author_id
      WHERE p.status = 'published' ${handle ? 'AND a.handle = ?' : ''} ORDER BY p.published_at DESC LIMIT 20`, ...(handle ? [handle] : []));
    const base = `${ctx.proto}://${req.headers.host}`;
    const items = rows.map((p) => `<item><title>${esc(p.title)}</title><link>${base}/p/${p.slug}</link><guid>${base}/p/${p.slug}</guid>
<dc:creator>${esc(p.author_name)}</dc:creator><pubDate>${new Date(p.published_at).toUTCString()}</pubDate>
<description>${esc(render(p.body_md).html)}</description></item>`).join('\n');
    send(res, 200, `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
<title>Margin${handle ? ` · @${esc(handle)}` : ''}</title><link>${base}/</link><description>Read anything. No account.</description>
${items}
</channel></rss>`, { 'Content-Type': 'application/rss+xml; charset=utf-8' });
  });

  on('GET', /^\/static\/((?:fonts\/)?[\w.-]+)$/, (req, res, m) => {
    const file = path.join(STATIC, m[1]);
    if (!file.startsWith(STATIC + path.sep) || !fs.existsSync(file)) return send(res, 404, 'not found');
    const long = file.endsWith('.woff2');
    send(res, 200, fs.readFileSync(file), { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': long ? 'public, max-age=31536000, immutable' : 'public, max-age=300' });
  });

  // ----- writer auth -----
  on('GET', /^\/login$/, (req, res) => html(res, views.authForm({ mode: 'login' })));
  on('GET', /^\/signup$/, (req, res) => html(res, views.authForm({ mode: 'signup' })));
  on('GET', /^\/write$/, (req, res, m, ctx) => redirect(res, ctx.author ? '/dashboard' : '/signup'));

  on('POST', /^\/login$/, async (req, res) => {
    const b = await readBody(req);
    const a = h.get('SELECT * FROM authors WHERE handle = ?', String(b.handle || '').toLowerCase().trim());
    if (!a || !auth.verifyPassword(b.password || '', a.pw_hash)) return html(res, views.authForm({ mode: 'login', error: 'That handle and password don\'t match.', values: b }), 401);
    const tok = auth.token();
    h.run('INSERT INTO sessions (token, author_id, created_at) VALUES (?,?,?)', tok, a.id, Date.now());
    redirect(res, '/dashboard', { 'Set-Cookie': sessionCookie(tok, 60 * 60 * 24 * 30) });
  });

  on('POST', /^\/signup$/, async (req, res) => {
    const b = await readBody(req);
    const handle = String(b.handle || '').toLowerCase().trim();
    const name = String(b.name || '').trim().slice(0, 60);
    let error = null;
    if (!/^[a-z0-9_]{2,24}$/.test(handle)) error = 'Handles are 2–24 lowercase letters, numbers, or underscores.';
    else if (!name) error = 'Add a name.';
    else if (String(b.password || '').length < 10) error = 'Use a password of at least 10 characters.';
    else if (h.get('SELECT id FROM authors WHERE handle = ?', handle)) error = 'That handle is taken.';
    if (error) return html(res, views.authForm({ mode: 'signup', error, values: b }), 400);
    const id = Number(h.run('INSERT INTO authors (handle, name, bio, pw_hash, created_at) VALUES (?,?,?,?,?)', handle, name, '', auth.hashPassword(b.password), Date.now()).lastInsertRowid);
    const tok = auth.token();
    h.run('INSERT INTO sessions (token, author_id, created_at) VALUES (?,?,?)', tok, id, Date.now());
    redirect(res, '/write/new', { 'Set-Cookie': sessionCookie(tok, 60 * 60 * 24 * 30) });
  });

  on('POST', /^\/logout$/, (req, res) => {
    const t = auth.parseCookies(req.headers.cookie).ms;
    if (t) h.run('DELETE FROM sessions WHERE token = ?', t);
    redirect(res, '/', { 'Set-Cookie': sessionCookie('', 0) });
  });

  // ----- writer desk -----
  const needAuthor = (fn) => (req, res, m, ctx) => (ctx.author ? fn(req, res, m, ctx) : redirect(res, '/login'));

  on('GET', /^\/dashboard$/, needAuthor((req, res, m, ctx) => html(res, views.dashboard({ author: ctx.author, dash: signals.authorDashboard(h, ctx.author.id) }))));

  on('GET', /^\/desk\/profile$/, needAuthor((req, res, m, ctx) => {
    const author = h.get('SELECT id, handle, name, bio, now_line, accent, blogroll FROM authors WHERE id = ?', ctx.author.id);
    html(res, views.profileForm({ author, accents: ring.ACCENTS, saved: ctx.url.searchParams.has('saved') }));
  }));

  on('POST', /^\/desk\/profile$/, needAuthor(async (req, res, m, ctx) => {
    const b = await readBody(req, 20000);
    const name = String(b.name || '').trim().slice(0, 60);
    const accent = ring.ACCENTS.includes(b.accent) ? b.accent : 'cobalt';
    if (!name) {
      const author = { ...h.get('SELECT * FROM authors WHERE id = ?', ctx.author.id), ...b, accent };
      return html(res, views.profileForm({ author, accents: ring.ACCENTS, error: 'Your homepage needs a name.' }), 400);
    }
    const lines = String(b.blogroll || '').split('\n').map((l) => l.trim()).filter(Boolean);
    const dropped = [];
    for (const line of lines) {
      if (/^@[a-z0-9_]{2,24}$/i.test(line)) {
        if (!h.get('SELECT id FROM authors WHERE handle = ?', line.slice(1).toLowerCase())) dropped.push({ line, why: 'no writer with that handle on Margin' });
      } else if (!/^https?:\/\/\S+/i.test(line)) dropped.push({ line, why: 'use @handle or a link starting with https://' });
    }
    if (lines.length - dropped.length > 12) dropped.push({ line: '…', why: 'only the first 12 are kept' });
    h.run('UPDATE authors SET name = ?, bio = ?, now_line = ?, accent = ?, blogroll = ? WHERE id = ?',
      name, String(b.bio || '').trim().slice(0, 280), String(b.now_line || '').trim().slice(0, 140), accent,
      ring.normalizeBlogroll(lines.filter((l) => !dropped.some((d) => d.line === l)).join('\n')), ctx.author.id);
    if (!dropped.length) return redirect(res, '/desk/profile?saved=1');
    const author = h.get('SELECT id, handle, name, bio, now_line, accent, blogroll FROM authors WHERE id = ?', ctx.author.id);
    html(res, views.profileForm({ author, accents: ring.ACCENTS, saved: true, dropped }));
  }));

  on('GET', /^\/dashboard\/p\/([\w-]+)$/, needAuthor((req, res, m, ctx) => {
    const post = h.get('SELECT * FROM posts WHERE slug = ? AND author_id = ?', m[1], ctx.author.id);
    if (!post) return html(res, views.notFound({ viewer: ctx.author }), 404);
    const stats = signals.authorDashboard(h, ctx.author.id).posts.find((p) => p.id === post.id) || { views: 0, reads: 0, keeps: 0, notes: 0 };
    html(res, views.postDetail({ author: ctx.author, post, stats, paras: signals.paragraphMap(h, post) }));
  }));

  on('GET', /^\/dashboard\/list\.csv$/, needAuthor((req, res, m, ctx) => {
    const subs = h.all(`SELECT email, source, coalesce(confirmed_at, created_at) AS since FROM email_subs WHERE author_id = ? AND status = 'active'`, ctx.author.id);
    const keyed = signals.authorDashboard(h, ctx.author.id).list;
    const seen = new Set(subs.map((r) => r.email));
    const rows = [...subs.map((r) => ({ email: r.email, source: r.source === 'import' ? 'imported' : 'email follow', since: new Date(r.since).toISOString() })),
      ...keyed.filter((r) => !seen.has(r.email)).map((r) => ({ email: r.email, source: 'reader key (shared)', since: new Date(r.created_at).toISOString() }))];
    const csv = toCsv(['email', 'source', 'since'], rows);
    send(res, 200, csv, { 'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': `attachment; filename="margin-${ctx.author.handle}-list.csv"` });
  }));

  on('GET', /^\/write\/(new|\d+)$/, needAuthor((req, res, m, ctx) => {
    if (m[1] === 'new') return html(res, views.editor({ author: ctx.author, reach: reach(ctx.author.id) }));
    const post = h.get('SELECT * FROM posts WHERE id = ? AND author_id = ?', Number(m[1]), ctx.author.id);
    if (!post) return html(res, views.notFound({ viewer: ctx.author }), 404);
    const q = ctx.url.searchParams;
    html(res, views.editor({ author: ctx.author, post, reach: reach(ctx.author.id), notice: q.has('scheduled') ? 'Scheduled. It will go live on its own.' : q.has('saved') ? 'Saved.' : '' }));
  }));

  on('POST', /^\/write\/(new|\d+)$/, needAuthor(async (req, res, m, ctx) => {
    const b = await readBody(req);
    const title = String(b.title || '').trim().slice(0, 140);
    const dek = String(b.dek || '').trim().slice(0, 240);
    const body = String(b.body_md || '').slice(0, 200_000);
    const action = ['save', 'publish', 'unpublish', 'schedule', 'unschedule'].includes(b.action) ? b.action : 'save';
    const now = Date.now();
    let post = m[1] === 'new' ? null : h.get('SELECT * FROM posts WHERE id = ? AND author_id = ?', Number(m[1]), ctx.author.id);
    if (m[1] !== 'new' && !post) return html(res, views.notFound({ viewer: ctx.author }), 404);
    if (!title) return html(res, views.editor({ author: ctx.author, post: { ...(post || { id: 'new', status: 'draft', slug: '' }), title, dek, body_md: body }, error: 'A piece needs a title.' }), 400);
    const words = render(body).words;
    if (!post) {
      const id = Number(h.run(`INSERT INTO posts (author_id, slug, title, dek, body_md, words, status, created_at, updated_at) VALUES (?,?,?,?,?,?, 'draft', ?, ?)`,
        ctx.author.id, slugify(title), title, dek, body, words, now, now).lastInsertRowid);
      post = h.get('SELECT * FROM posts WHERE id = ?', id);
    } else {
      // Slugs are frozen once published so links never break.
      const slug = post.status === 'published' || post.published_at ? post.slug : slugify(title, post.id);
      h.run('UPDATE posts SET title = ?, dek = ?, body_md = ?, words = ?, slug = ?, updated_at = ? WHERE id = ?', title, dek, body, words, slug, now, post.id);
    }
    if (action === 'publish') publishNow(post.id, baseUrl(req));
    if (action === 'schedule') {
      const at = Date.parse(String(b.publish_at || ''));
      if (!Number.isFinite(at) || at < now + 60000) {
        return html(res, views.editor({ author: ctx.author, post: h.get('SELECT * FROM posts WHERE id = ?', post.id), error: 'Pick a time at least a minute from now.' }), 400);
      }
      h.run(`UPDATE posts SET status = 'scheduled', publish_at = ? WHERE id = ?`, at, post.id);
    }
    if (action === 'unpublish' || action === 'unschedule') h.run(`UPDATE posts SET status = 'draft', publish_at = NULL WHERE id = ?`, post.id);
    const fresh = h.get('SELECT * FROM posts WHERE id = ?', post.id);
    redirect(res, action === 'publish' ? `/p/${fresh.slug}${post.published_at ? '' : '?published=1'}` : `/write/${fresh.id}${action === 'schedule' ? '?scheduled=1' : '?saved=1'}`);
  }));

  // ----- anonymous reading signals -----
  on('POST', /^\/api\/read$/, async (req, res) => {
    const b = await readBody(req, 4096);
    const post = publishedPost(b.slug);
    if (!post || !UUID.test(String(b.pv))) return json(res, { ok: false }, 400);
    const depth = Math.min(1, Math.max(0, Number(b.depth) || 0));
    const dwell = Math.min(6 * 3600 * 1000, Math.max(0, Math.floor(Number(b.dwell) || 0)));
    const source = ['front', 'follow', 'brief', 'author', 'next', 'ring', 'passed', 'direct'].includes(b.source) ? b.source : 'direct';
    const now = Date.now();
    // seen_at only moves while the page is visible, so "reading now" means reading now.
    const seen = b.visible === false ? 0 : now;
    h.run(`INSERT INTO views (pv, post_id, max_depth, dwell_ms, source, keyed, created_at, seen_at) VALUES (?,?,?,?,?,?,?,?)
      ON CONFLICT(pv) DO UPDATE SET max_depth = max(max_depth, excluded.max_depth), dwell_ms = max(dwell_ms, excluded.dwell_ms),
        seen_at = CASE WHEN excluded.seen_at > 0 THEN excluded.seen_at ELSE 0 END
      WHERE views.post_id = excluded.post_id`, b.pv, post.id, depth, dwell, source, b.keyed ? 1 : 0, now, seen);
    json(res, { ok: true, now: ring.readingNow(h, post.id) });
  });

  on('GET', /^\/api\/presence$/, (req, res, m, ctx) => {
    const post = publishedPost(ctx.url.searchParams.get('slug'));
    if (!post) return json(res, { ok: false }, 404);
    const reads = h.get(`SELECT count(*) AS n FROM views WHERE post_id = ? AND max_depth >= 0.9 AND dwell_ms >= ?`, post.id, post.words * signals.MS_PER_WORD_FLOOR).n;
    json(res, { ok: true, now: ring.readingNow(h, post.id), reads });
  });

  on('POST', /^\/api\/pass$/, async (req, res) => {
    const b = await readBody(req, 4096);
    const post = publishedPost(b.slug);
    const para = Number(b.para);
    if (!post || !Number.isInteger(para) || para < 0 || para > 5000) return json(res, { ok: false }, 400);
    h.run('INSERT INTO passes (post_id, para, created_at) VALUES (?,?,?)', post.id, para, Date.now());
    json(res, { ok: true, url: `/p/${post.slug}?via=passed&p=${para}` });
  });

  on('POST', /^\/api\/keep$/, async (req, res) => {
    const b = await readBody(req, 4096);
    const post = publishedPost(b.slug);
    const para = Number(b.para);
    if (!post || !Number.isInteger(para) || para < 0 || para > 5000 || !UUID.test(String(b.pv))) return json(res, { ok: false }, 400);
    h.run('INSERT OR IGNORE INTO keeps (post_id, pv, para, created_at) VALUES (?,?,?,?)', post.id, b.pv, para, Date.now());
    json(res, { ok: true });
  });

  on('POST', /^\/api\/follow$/, async (req, res) => {
    const b = await readBody(req, 4096);
    const a = h.get('SELECT id FROM authors WHERE handle = ?', String(b.handle || ''));
    if (!a) return json(res, { ok: false }, 400);
    const post = b.slug ? publishedPost(b.slug) : null;
    const delta = Number(b.delta) < 0 ? -1 : 1;
    const reader = b.key ? readerByKey(b.key) : null;
    const via = b.via ? h.get('SELECT id FROM authors WHERE handle = ?', String(b.via)) : null;
    h.run('INSERT INTO follow_events (author_id, post_id, delta, keyed, via_author_id, created_at) VALUES (?,?,?,?,?,?)', a.id, post ? post.id : null, delta, reader ? 1 : 0, via && via.id !== a.id ? via.id : null, Date.now());
    if (reader) syncFollows(reader, { [b.handle]: { on: delta > 0, ts: Date.now() } });
    json(res, { ok: true });
  });

  on('POST', /^\/api\/ask$/, async (req, res) => {
    const b = await readBody(req, 4096);
    const post = publishedPost(b.slug);
    if (!post || !['follow', 'key'].includes(b.kind) || !['shown', 'accepted'].includes(b.event)) return json(res, { ok: false }, 400);
    h.run('INSERT INTO asks (post_id, kind, event, created_at) VALUES (?,?,?,?)', post.id, b.kind, b.event, Date.now());
    json(res, { ok: true });
  });

  on('POST', /^\/api\/tip$/, async (req, res) => {
    const b = await readBody(req, 4096);
    const post = publishedPost(b.slug);
    const cents = Math.floor(Number(b.cents));
    if (!post || !(cents >= 100 && cents <= 50000)) return json(res, { ok: false }, 400);
    h.run('INSERT INTO tips (post_id, amount_cents, note, created_at) VALUES (?,?,?,?)', post.id, cents, String(b.note || '').slice(0, 280), Date.now());
    json(res, { ok: true, simulated: true });
  });

  on('GET', /^\/api\/latest$/, (req, res, m, ctx) => {
    const handles = String(ctx.url.searchParams.get('handles') || '').split(',').map((s) => s.trim()).filter(Boolean).slice(0, 50);
    if (!handles.length) return json(res, { posts: [] });
    const rows = h.all(`SELECT p.slug, p.title, p.dek, p.words, p.published_at, a.handle, a.name AS author_name FROM posts p JOIN authors a ON a.id = p.author_id
      WHERE p.status = 'published' AND a.handle IN (${handles.map(() => '?').join(',')}) ORDER BY p.published_at DESC LIMIT 5`, ...handles);
    json(res, { posts: rows.map((r) => ({ ...r, minutes: signals.readingMinutes(r.words) })) });
  });

  on('POST', /^\/api\/check$/, async (req, res) => {
    const b = await readBody(req, 300_000);
    json(res, checkDraft(String(b.body_md || '')));
  });

  // ----- reader keys -----
  on('POST', /^\/api\/key\/new$/, async (req, res) => {
    const b = await readBody(req, 600_000);
    const key = auth.newReaderKey();
    const data = mergeData({}, b.data || {});
    const now = Date.now();
    const id = Number(h.run('INSERT INTO readers (key_hash, data, created_at, updated_at) VALUES (?,?,?,?)', auth.hashKey(key), JSON.stringify(data), now, now).lastInsertRowid);
    syncFollows({ id }, data.follows);
    json(res, { key, data, prefs: prefsOf({}) });
  });

  on('POST', /^\/api\/key\/sync$/, async (req, res) => {
    const b = await readBody(req, 600_000);
    const reader = readerByKey(b.key);
    if (!reader) return json(res, { ok: false, error: 'That key doesn\'t match any reader. Check the spelling.' }, 404);
    let stored = {};
    try { stored = JSON.parse(reader.data); } catch { /* start fresh */ }
    const data = mergeData(stored, b.data || {});
    const blob = JSON.stringify(data);
    if (blob.length > 2_000_000) return json(res, { ok: false, error: 'Commonplace is too large to sync.' }, 413);
    h.run('UPDATE readers SET data = ?, updated_at = ? WHERE id = ?', blob, Date.now(), reader.id);
    syncFollows(reader, data.follows);
    json(res, { ok: true, data, prefs: prefsOf(reader) });
  });

  on('POST', /^\/api\/key\/prefs$/, async (req, res) => {
    const b = await readBody(req, 4096);
    const reader = readerByKey(b.key);
    if (!reader) return json(res, { ok: false }, 404);
    const email = String(b.email || '').trim().slice(0, 200);
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return json(res, { ok: false, error: 'That email doesn\'t look right.' }, 400);
    if (!email && (b.digest || b.share_email)) return json(res, { ok: false, error: 'Add an email address first. The Brief and sharing both need one.' }, 400);
    h.run('UPDATE readers SET email = ?, digest = ?, share_email = ?, updated_at = ? WHERE id = ?', email || null, b.digest && email ? 1 : 0, b.share_email && email ? 1 : 0, Date.now(), reader.id);
    json(res, { ok: true, prefs: prefsOf(h.get('SELECT * FROM readers WHERE id = ?', reader.id)) });
  });

  on('POST', /^\/api\/note$/, async (req, res) => {
    const b = await readBody(req, 8192);
    const reader = readerByKey(b.key);
    if (!reader) return json(res, { ok: false, error: 'You need a reader key to write in the margin.' }, 403);
    const post = publishedPost(b.slug);
    const para = Number(b.para);
    const body = String(b.body || '').trim().slice(0, 1200);
    if (!post || !Number.isInteger(para) || para < 0 || !body) return json(res, { ok: false, error: 'Write something first.' }, 400);
    const today = h.get('SELECT count(*) AS n FROM notes WHERE reader_id = ? AND created_at > ?', reader.id, Date.now() - 86400000).n;
    if (today >= 20) return json(res, { ok: false, error: 'That\'s 20 notes today. Come back tomorrow.' }, 429);
    const name = String(b.name || '').trim().slice(0, 40) || 'A reader';
    const quote = String(b.quote || '').trim().slice(0, 400);
    const id = Number(h.run('INSERT INTO notes (post_id, para, reader_id, display_name, quote, body, created_at) VALUES (?,?,?,?,?,?,?)', post.id, para, reader.id, name, quote, body, Date.now()).lastInsertRowid);
    json(res, { ok: true, note: { id, para, display_name: name, quote, body } });
  });

  // Anyone can flag a note. Three flags hide it until the writer looks.
  const flagged = new Set();
  on('POST', /^\/api\/note\/flag$/, async (req, res) => {
    const b = await readBody(req, 1024);
    const id = Number(b.id);
    const k = `${req.socket.remoteAddress}:${id}`;
    if (!Number.isInteger(id) || !h.get('SELECT id FROM notes WHERE id = ?', id)) return json(res, { ok: false }, 400);
    if (!flagged.has(k)) {
      flagged.add(k);
      h.run('UPDATE notes SET flags = flags + 1, hidden = CASE WHEN flags + 1 >= 3 AND hidden = 0 THEN 1 ELSE hidden END WHERE id = ?', id);
    }
    json(res, { ok: true });
  });

  // Who this writer recommends: the moment after a follow is when readers
  // are most open to the next writer (it's what drives Substack's network).
  on('GET', /^\/api\/recs$/, (req, res, m, ctx) => {
    const a = h.get('SELECT id, blogroll FROM authors WHERE handle = ?', String(ctx.url.searchParams.get('handle') || ''));
    if (!a) return json(res, { recs: [] });
    const recs = ring.parseBlogroll(h, a.blogroll).filter((r) => r.kind === 'writer').slice(0, 3).map((r) => {
      const handle = r.href.slice(2);
      const latest = h.get(`SELECT p.slug, p.title FROM posts p JOIN authors x ON x.id = p.author_id WHERE x.handle = ? AND p.status = 'published' ORDER BY p.published_at DESC LIMIT 1`, handle);
      return { handle, name: r.title, now_line: r.note, latest };
    });
    json(res, { recs });
  });

  // Email follow: double opt-in, one writer at a time, no account.
  on('POST', /^\/api\/subscribe$/, async (req, res) => {
    const b = await readBody(req, 2048);
    const a = h.get('SELECT id, handle, name FROM authors WHERE handle = ?', String(b.handle || ''));
    const email = String(b.email || '').trim().toLowerCase().slice(0, 200);
    if (!a) return json(res, { ok: false, error: 'Unknown writer.' }, 400);
    if (!EMAIL_RE.test(email)) return json(res, { ok: false, error: 'That email doesn’t look right.' }, 400);
    const via = b.via ? h.get('SELECT id FROM authors WHERE handle = ?', String(b.via)) : null;
    let sub = h.get('SELECT * FROM email_subs WHERE author_id = ? AND email = ?', a.id, email);
    if (sub && sub.status === 'active') return json(res, { ok: true, already: true });
    if (!sub) {
      h.run(`INSERT INTO email_subs (author_id, email, token, status, source, via_author_id, created_at) VALUES (?,?,?, 'pending', 'follow', ?, ?)`,
        a.id, email, auth.token(18), via && via.id !== a.id ? via.id : null, Date.now());
      sub = h.get('SELECT * FROM email_subs WHERE author_id = ? AND email = ?', a.id, email);
    } else if (sub.status === 'unsubscribed') h.run(`UPDATE email_subs SET status = 'pending' WHERE id = ?`, sub.id);
    const link = `${baseUrl(req)}/confirm/${sub.token}`;
    queueMail(email, `Confirm: new pieces from ${a.name}`, `Someone (hopefully you) asked to get ${a.name}'s new pieces on Margin by email.\n\nConfirm: ${link}\n\nIf it wasn't you, ignore this and nothing happens.`, 'confirm');
    json(res, { ok: true, pending: true, ...(showMail ? { previewLink: `/confirm/${sub.token}` } : {}) });
  });

  on('GET', /^\/confirm\/([\w-]{10,64})$/, (req, res, m, ctx) => {
    const sub = h.get('SELECT s.*, a.name, a.handle FROM email_subs s JOIN authors a ON a.id = s.author_id WHERE s.token = ?', m[1]);
    if (!sub) return html(res, views.notFound({ viewer: ctx.author }), 404);
    if (sub.status !== 'active') h.run(`UPDATE email_subs SET status = 'active', confirmed_at = ? WHERE id = ?`, Date.now(), sub.id);
    html(res, views.mailResult({ kind: 'confirmed', sub, viewer: ctx.author }));
  });

  on('GET', /^\/unsubscribe\/([\w-]{10,64})$/, (req, res, m, ctx) => {
    const sub = h.get('SELECT s.*, a.name, a.handle FROM email_subs s JOIN authors a ON a.id = s.author_id WHERE s.token = ?', m[1]);
    if (!sub) return html(res, views.notFound({ viewer: ctx.author }), 404);
    h.run(`UPDATE email_subs SET status = 'unsubscribed' WHERE id = ?`, sub.id);
    html(res, views.mailResult({ kind: 'unsubscribed', sub, viewer: ctx.author }));
  });

  // ----- portability and moderation on the desk -----
  on('GET', /^\/desk\/import$/, needAuthor((req, res, m, ctx) => html(res, views.importPage({ author: ctx.author }))));
  on('POST', /^\/desk\/import$/, needAuthor(async (req, res, m, ctx) => {
    const buf = await readRaw(req, 50 * 1024 * 1024);
    try {
      json(res, { ok: true, report: importSubstack(h, ctx.author.id, buf) });
    } catch (e) {
      json(res, { ok: false, error: e.message || 'Could not read that file.' }, 400);
    }
  }));
  on('GET', /^\/desk\/export\.zip$/, needAuthor((req, res, m, ctx) => {
    send(res, 200, exportAuthor(h, ctx.author), { 'Content-Type': 'application/zip', 'Content-Disposition': `attachment; filename="margin-${ctx.author.handle}-export.zip"` });
  }));
  on('POST', /^\/desk\/notes\/(\d+)\/(hide|show)$/, needAuthor((req, res, m, ctx) => {
    const note = h.get('SELECT n.id FROM notes n JOIN posts p ON p.id = n.post_id WHERE n.id = ? AND p.author_id = ?', Number(m[1]), ctx.author.id);
    if (!note) return html(res, views.notFound({ viewer: ctx.author }), 404);
    h.run('UPDATE notes SET hidden = ?, flags = CASE WHEN ? = 0 THEN 0 ELSE flags END WHERE id = ?', m[2] === 'hide' ? 2 : 0, m[2] === 'hide' ? 2 : 0, note.id);
    redirect(res, '/dashboard#notes');
  }));

  // ---------- writer tools: autosave, uploads, test hooks ----------
  on('POST', /^\/write\/(\d+)\/autosave$/, needAuthor(async (req, res, m, ctx) => {
    const b = await readBody(req, 300_000);
    const post = h.get('SELECT * FROM posts WHERE id = ? AND author_id = ?', Number(m[1]), ctx.author.id);
    if (!post) return json(res, { ok: false }, 404);
    // Autosave never publishes and never touches a published piece's live text.
    if (post.status === 'published') return json(res, { ok: false, reason: 'published' }, 409);
    const body = String(b.body_md ?? post.body_md).slice(0, 200_000);
    h.run('UPDATE posts SET title = ?, dek = ?, body_md = ?, words = ?, updated_at = ? WHERE id = ?',
      String(b.title ?? post.title).trim().slice(0, 140) || post.title, String(b.dek ?? post.dek).trim().slice(0, 240), body, render(body).words, Date.now(), post.id);
    json(res, { ok: true, savedAt: Date.now() });
  }));

  on('POST', /^\/desk\/upload$/, needAuthor(async (req, res, m, ctx) => {
    const buf = await readRaw(req, 5 * 1024 * 1024);
    const kind = sniffImage(buf);
    if (!kind) return json(res, { ok: false, error: 'Use a PNG, JPEG, GIF or WebP image under 5 MB.' }, 400);
    const file = `${crypto.createHash('sha256').update(buf).digest('hex').slice(0, 24)}.${kind[1]}`;
    fs.mkdirSync(MEDIA_DIR, { recursive: true });
    const dest = path.join(MEDIA_DIR, file);
    if (!fs.existsSync(dest)) fs.writeFileSync(dest, buf);
    h.run('INSERT OR IGNORE INTO media (author_id, file, mime, bytes, created_at) VALUES (?,?,?,?,?)', ctx.author.id, file, kind[0], buf.length, Date.now());
    json(res, { ok: true, url: `/media/${file}` });
  }));

  on('GET', /^\/media\/([a-f0-9]{24}\.(png|jpg|gif|webp))$/, (req, res, m) => {
    const row = h.get('SELECT mime FROM media WHERE file = ?', m[1]);
    const file = path.join(MEDIA_DIR, m[1]);
    if (!row || !fs.existsSync(file)) return send(res, 404, 'not found');
    send(res, 200, fs.readFileSync(file), { 'Content-Type': row.mime, 'Cache-Control': 'public, max-age=31536000, immutable', 'Content-Security-Policy': "default-src 'none'; img-src 'self'" });
  });

  // ---------- fediverse ----------
  on('GET', /^\/\.well-known\/webfinger$/, (req, res, m, ctx) => {
    const doc = ap.webfinger(h, baseUrl(req), ctx.url.searchParams.get('resource'));
    if (!doc) return json(res, { error: 'not found' }, 404);
    apJson(res, doc, 200, 'application/jrd+json');
  });
  const apAuthor = (handle) => h.get('SELECT * FROM authors WHERE handle = ?', handle);
  on('GET', /^\/ap\/users\/([a-z0-9_]+)$/, (req, res, m) => {
    const a = apAuthor(m[1]);
    return a ? apJson(res, ap.actorJson(h, baseUrl(req), a)) : json(res, { error: 'not found' }, 404);
  });
  on('GET', /^\/ap\/users\/([a-z0-9_]+)\/outbox$/, (req, res, m) => {
    const a = apAuthor(m[1]);
    return a ? apJson(res, ap.outboxJson(h, baseUrl(req), a)) : json(res, { error: 'not found' }, 404);
  });
  on('GET', /^\/ap\/users\/([a-z0-9_]+)\/followers$/, (req, res, m) => {
    const a = apAuthor(m[1]);
    return a ? apJson(res, ap.followersJson(h, baseUrl(req), a)) : json(res, { error: 'not found' }, 404);
  });
  on('GET', /^\/ap\/posts\/(\d+)$/, (req, res, m) => {
    const post = h.get(`SELECT * FROM posts WHERE id = ? AND status = 'published'`, Number(m[1]));
    if (!post) return json(res, { error: 'not found' }, 404);
    apJson(res, { '@context': 'https://www.w3.org/ns/activitystreams', ...ap.articleJson(baseUrl(req), h.get('SELECT * FROM authors WHERE id = ?', post.author_id), post) });
  });
  const inbox = async (req, res, m) => {
    const raw = await readRaw(req, 256 * 1024);
    let activity;
    try { activity = JSON.parse(raw.toString('utf8')); } catch { return json(res, { error: 'bad json' }, 400); }
    // Sign our key fetches as the writer being addressed (or any writer, for the shared inbox).
    const target = (m && m[1] && apAuthor(m[1])) || h.get('SELECT * FROM authors ORDER BY id LIMIT 1');
    const base = baseUrl(req);
    try {
      const signer = await fed.verifyInbox(req, raw, fed.signerFor(base, target));
      const result = fed.receive(base, activity, signer);
      json(res, { ok: true, result }, 202);
    } catch (e) {
      json(res, { error: String(e.message || e) }, 401);
    }
  };
  on('POST', /^\/ap\/users\/([a-z0-9_]+)\/inbox$/, inbox);
  on('POST', /^\/ap\/inbox$/, inbox);

  // ---------- dispatcher ----------
  async function handle(req, res) {
    const url = new URL(req.url, 'http://x');
    const ip = req.socket.remoteAddress || '';
    const ctx = { url, author: currentAuthor(req), proto: req.headers['x-forwarded-proto'] === 'https' ? 'https' : 'http' };
    if (req.headers.host) lastBase = `${ctx.proto}://${req.headers.host}`;
    if (req.method === 'POST' && url.pathname.startsWith('/api/') && limited(ip)) return json(res, { ok: false, error: 'Slow down a little.' }, 429);
    if (req.method === 'POST' && (url.pathname === '/login' || url.pathname === '/signup') && limited('auth:' + ip, 20)) return html(res, views.tooMany(), 429);
    const method = req.method === 'HEAD' ? 'GET' : req.method;
    for (const r of routes) {
      if (r.method !== method) continue;
      const m = url.pathname.match(r.pattern);
      if (m) return r.fn(req, res, m, ctx);
    }
    html(res, views.notFound({ viewer: ctx.author }), 404);
  }

  const server = http.createServer((req, res) => {
    Promise.resolve(handle(req, res)).catch((e) => {
      const status = e.status || 500;
      if (status === 500) console.error(e);
      if (!res.headersSent) json(res, { ok: false, error: status === 500 ? 'Something broke.' : e.message }, status);
    });
  });
  return { server, h, fed, runJobs };
}

module.exports = { createApp };

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  const { server } = createApp();
  server.listen(port, () => console.log(`Margin is running at http://localhost:${port}`));
}
