'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { open, helpers } = require('./lib/db');
const { seed } = require('./lib/seed');
const { render, esc } = require('./lib/markdown');
const { checkDraft } = require('./lib/draftcheck');
const auth = require('./lib/auth');
const signals = require('./lib/signals');
const views = require('./lib/views');
const ring = require('./lib/ring');

const STATIC = path.join(__dirname, 'public');
const MIME = { '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8' };
const SECURITY_HEADERS = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
};
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

class HttpError extends Error { constructor(status, msg) { super(msg); this.status = status; } }

function createApp({ dbFile = process.env.MARGIN_DB || path.join(__dirname, 'data', 'margin.db'), demoSignals = process.env.MARGIN_DEMO_SIGNALS !== '0', secureCookies = process.env.MARGIN_SECURE_COOKIES === '1' } = {}) {
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
    const author = h.get('SELECT id, handle, name, bio, accent, blogroll FROM authors WHERE id = ?', post.author_id);
    const rendered = render(post.body_md);
    const notes = h.all('SELECT para, display_name, quote, body, created_at FROM notes WHERE post_id = ? ORDER BY created_at', post.id);
    const kc = h.all('SELECT para, count(*) AS n FROM keeps WHERE post_id = ? GROUP BY para ORDER BY n DESC', post.id);
    const keepCounts = Object.fromEntries(kc.map((r) => [r.para, r.n]));
    const topKeep = kc[0] && kc[0].n >= 3 ? { para: kc[0].para, n: kc[0].n } : null;
    const reads = h.get(`SELECT count(*) AS n FROM views WHERE post_id = ? AND max_depth >= 0.9 AND dwell_ms >= ?`, post.id, post.words * signals.MS_PER_WORD_FLOOR).n;
    html(res, views.article({ post, author, rendered, notes, topKeep, keepCounts, next: signals.nextReads(h, post), viewer: ctx.author,
      stats: { now: ring.readingNow(h, post.id), reads }, blogroll: ring.parseBlogroll(h, author.blogroll) }));
  });

  on('GET', /^\/@([\w]+)$/, (req, res, m, ctx) => {
    const author = h.get('SELECT id, handle, name, bio, now_line, accent, blogroll FROM authors WHERE handle = ?', m[1].toLowerCase());
    if (!author) return html(res, views.notFound({ viewer: ctx.author }), 404);
    const posts = h.all(`SELECT slug, title, dek, words, published_at FROM posts WHERE author_id = ? AND status = 'published' ORDER BY published_at DESC`, author.id);
    const recommendedBy = h.all('SELECT handle, name, blogroll FROM authors WHERE id != ?', author.id)
      .filter((a) => a.blogroll.split('\n').map((l) => l.trim().toLowerCase()).includes('@' + author.handle));
    html(res, views.authorPage({ author, posts, viewer: ctx.author, blogroll: ring.parseBlogroll(h, author.blogroll), recommendedBy }));
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
    h.run('UPDATE authors SET name = ?, bio = ?, now_line = ?, accent = ?, blogroll = ? WHERE id = ?',
      name, String(b.bio || '').trim().slice(0, 280), String(b.now_line || '').trim().slice(0, 140), accent, ring.normalizeBlogroll(b.blogroll), ctx.author.id);
    redirect(res, '/desk/profile?saved=1');
  }));

  on('GET', /^\/dashboard\/p\/([\w-]+)$/, needAuthor((req, res, m, ctx) => {
    const post = h.get('SELECT * FROM posts WHERE slug = ? AND author_id = ?', m[1], ctx.author.id);
    if (!post) return html(res, views.notFound({ viewer: ctx.author }), 404);
    const stats = signals.authorDashboard(h, ctx.author.id).posts.find((p) => p.id === post.id) || { views: 0, reads: 0, keeps: 0, notes: 0 };
    html(res, views.postDetail({ author: ctx.author, post, stats, paras: signals.paragraphMap(h, post) }));
  }));

  on('GET', /^\/dashboard\/list\.csv$/, needAuthor((req, res, m, ctx) => {
    const rows = signals.authorDashboard(h, ctx.author.id).list;
    const csv = ['email,following_since', ...rows.map((r) => `"${String(r.email).replace(/"/g, '""')}",${new Date(r.created_at).toISOString()}`)].join('\n');
    send(res, 200, csv, { 'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': `attachment; filename="margin-${ctx.author.handle}-list.csv"` });
  }));

  on('GET', /^\/write\/(new|\d+)$/, needAuthor((req, res, m, ctx) => {
    if (m[1] === 'new') return html(res, views.editor({ author: ctx.author }));
    const post = h.get('SELECT * FROM posts WHERE id = ? AND author_id = ?', Number(m[1]), ctx.author.id);
    if (!post) return html(res, views.notFound({ viewer: ctx.author }), 404);
    html(res, views.editor({ author: ctx.author, post }));
  }));

  on('POST', /^\/write\/(new|\d+)$/, needAuthor(async (req, res, m, ctx) => {
    const b = await readBody(req);
    const title = String(b.title || '').trim().slice(0, 140);
    const dek = String(b.dek || '').trim().slice(0, 240);
    const body = String(b.body_md || '').slice(0, 200_000);
    const action = ['save', 'publish', 'unpublish'].includes(b.action) ? b.action : 'save';
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
    if (action === 'publish') h.run(`UPDATE posts SET status = 'published', published_at = coalesce(published_at, ?) WHERE id = ?`, now, post.id);
    if (action === 'unpublish') h.run(`UPDATE posts SET status = 'draft' WHERE id = ?`, post.id);
    const fresh = h.get('SELECT * FROM posts WHERE id = ?', post.id);
    redirect(res, action === 'publish' ? `/p/${fresh.slug}` : `/write/${fresh.id}`);
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
    h.run('INSERT INTO follow_events (author_id, post_id, delta, keyed, created_at) VALUES (?,?,?,?,?)', a.id, post ? post.id : null, delta, reader ? 1 : 0, Date.now());
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
    h.run('INSERT INTO notes (post_id, para, reader_id, display_name, quote, body, created_at) VALUES (?,?,?,?,?,?,?)', post.id, para, reader.id, name, quote, body, Date.now());
    json(res, { ok: true, note: { para, display_name: name, quote, body } });
  });

  // ---------- dispatcher ----------
  async function handle(req, res) {
    const url = new URL(req.url, 'http://x');
    const ip = req.socket.remoteAddress || '';
    const ctx = { url, author: currentAuthor(req), proto: req.headers['x-forwarded-proto'] === 'https' ? 'https' : 'http' };
    if (req.method === 'POST' && url.pathname.startsWith('/api/') && limited(ip)) return json(res, { ok: false, error: 'Slow down a little.' }, 429);
    if (req.method === 'POST' && (url.pathname === '/login' || url.pathname === '/signup') && limited('auth:' + ip, 20)) return html(res, views.notFound({}), 429);
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
  return { server, h };
}

module.exports = { createApp };

if (require.main === module) {
  const port = Number(process.env.PORT) || 3000;
  const { server } = createApp();
  server.listen(port, () => console.log(`Margin is running at http://localhost:${port}`));
}
