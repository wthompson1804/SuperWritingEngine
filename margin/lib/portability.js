'use strict';
// Getting in and getting out. Import reads a Substack export zip. The layout
// matches what Ghost's open-source migrator (@tryghost/mg-substack) expects:
// posts.csv with post_id,post_date,is_published,email_sent_at,type,audience,
// title,subtitle,podcast_url; posts/<post_id>.html; and email_list.*.csv with
// email,active_subscription,expiry,email_disabled,prefer_digests,created_at.
// Export writes the same layout back out, so any tool that imports Substack
// (Ghost's migrator, for one) can import a Margin writer too.

const crypto = require('node:crypto');
const { readZip, writeZip } = require('./zip');
const { parseCsv, toCsv } = require('./csv');
const { htmlToMarkdown } = require('./htmlmd');
const { render } = require('./markdown');

const truthy = (v) => /^(true|t|1|yes)$/i.test(String(v || '').trim());

function uniqueSlug(h, base) {
  const clean = String(base || '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'untitled';
  let slug = clean; let n = 2;
  while (h.get('SELECT id FROM posts WHERE slug = ?', slug)) slug = `${clean}-${n++}`;
  return slug;
}

function findFile(files, test) {
  for (const [name, data] of files) if (test(name)) return [name, data];
  return null;
}

function importSubstack(h, authorId, zipBuf, { saveMedia = null, now = Date.now() } = {}) {
  const files = readZip(zipBuf);
  const report = { posts: { published: 0, drafts: 0, skipped: 0, already: 0 }, subscribers: { imported: 0, skipped: 0, paid: 0, already: 0 }, warnings: [] };
  const postsCsv = findFile(files, (n) => /(^|\/)posts\.csv$/i.test(n));
  const htmlByKey = new Map();
  for (const [name, data] of files) {
    const m = name.match(/(?:^|\/)posts\/(.+)\.html$/i);
    if (m) htmlByKey.set(m[1], data.toString('utf8'));
  }
  // A Margin export also carries each piece's original Markdown and its
  // images, so moving between Margin sites loses nothing.
  const mediaMap = new Map();
  if (saveMedia) {
    for (const [name, data] of files) {
      const m = name.match(/(?:^|\/)media\/([a-f0-9]{24}\.(?:png|jpg|gif|webp))$/);
      if (m) { const f = saveMedia(authorId, data); if (f) mediaMap.set(m[1], f); }
    }
  }
  const marginMd = new Map();
  for (const [name, data] of files) {
    const m = name.match(/(?:^|\/)margin\/(.+)\.md$/);
    if (m) marginMd.set(m[1], data.toString('utf8'));
  }
  if (!postsCsv && !findFile(files, (n) => /email_list.*\.csv$/i.test(n))) {
    throw new Error('This doesn’t look like a Substack export. Expected posts.csv or an email_list CSV inside the zip.');
  }

  h.tx(() => {
    for (const row of postsCsv ? parseCsv(postsCsv[1].toString('utf8')) : []) {
      const postId = String(row.post_id || '').trim();
      if (!postId) { report.posts.skipped++; continue; }
      const type = String(row.type || 'newsletter').toLowerCase();
      if (type === 'thread') { report.posts.skipped++; continue; }
      const html = htmlByKey.get(postId);
      const original = marginMd.get(postId);
      if (!html && original == null) { report.posts.skipped++; continue; }
      if ((original ?? html).length > 2 * 1024 * 1024) { report.posts.skipped++; report.tooBig = (report.tooBig || 0) + 1; continue; }
      const origin = `substack:${postId}`;
      if (h.get('SELECT id FROM posts WHERE author_id = ? AND imported_from = ?', authorId, origin)) { report.posts.already++; continue; }
      const body = original != null
        ? original.replace(/\(\/media\/([a-f0-9]{24}\.(?:png|jpg|gif|webp))\)/g, (m, f) => `(/media/${mediaMap.get(f) || f})`)
        : htmlToMarkdown(html);
      // Titles are one line: newlines from the CSV become spaces.
      const unguard = (v) => String(v || '').replace(/\s+/g, ' ').trim().replace(/^'(?=[=+\-@])/, '');
      const title = unguard(row.title) || 'Untitled';
      const dek = unguard(row.subtitle).slice(0, 240);
      if (title.length > 140) report.shortened = (report.shortened || 0) + 1;
      const audience = String(row.audience || 'everyone').toLowerCase();
      const published = truthy(row.is_published) && audience === 'everyone';
      const date = Date.parse(row.post_date) || now;
      const slug = uniqueSlug(h, postId.includes('.') ? postId.slice(postId.indexOf('.') + 1) : title);
      h.run(`INSERT INTO posts (author_id, slug, title, dek, body_md, words, status, published_at, created_at, updated_at, imported_from)
             VALUES (?,?,?,?,?,?,?,?,?,?,?)`, authorId, slug, title.slice(0, 140), dek, body, render(body).words,
      published ? 'published' : 'draft', published ? date : null, date, now, origin);
      if (published) report.posts.published++; else report.posts.drafts++;
      if (truthy(row.is_published) && audience !== 'everyone') report.posts.paidToDraft = (report.posts.paidToDraft || 0) + 1;
    }

    for (const [, data] of [...files].filter(([n]) => /(^|\/)email_list[^/]*\.csv$/i.test(n))) {
      for (const row of parseCsv(data.toString('utf8'))) {
        const email = String(row.email || '').trim().toLowerCase();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || truthy(row.email_disabled)) { report.subscribers.skipped++; continue; }
        if (truthy(row.active_subscription)) report.subscribers.paid++;
        const res = h.run(`INSERT OR IGNORE INTO email_subs (author_id, email, token, status, source, created_at, confirmed_at)
                           VALUES (?,?,?, 'active', 'import', ?, ?)`, authorId, email, crypto.randomBytes(18).toString('base64url'), Date.parse(row.created_at) || now, Date.parse(row.created_at) || now);
        if (res.changes) report.subscribers.imported++; else report.subscribers.already++;
      }
    }
  });

  const n = (x, one, many) => `${x} ${x === 1 ? one : many}`;
  if (report.shortened) report.warnings.push(`${n(report.shortened, 'title was', 'titles were')} longer than 140 characters and shortened.`);
  if (report.tooBig) report.warnings.push(`${n(report.tooBig, 'post was', 'posts were')} over 2 MB of HTML and skipped.`);
  if (report.posts.paidToDraft) report.warnings.push(`${n(report.posts.paidToDraft, 'paid-only post', 'paid-only posts')} came in as drafts. Margin has no paywall, so publishing makes them free.`);
  if (report.subscribers.paid) report.warnings.push(`${n(report.subscribers.paid, 'paid subscriber', 'paid subscribers')} came in as email followers. Their billing stays with Substack until you move it (Margin has no payments yet).`);
  if (report.posts.published + report.posts.drafts) report.warnings.push('Images still load from Substack’s servers. Notes, comments and podcast audio aren’t in Substack’s export.');
  return report;
}

function exportAuthor(h, author, { readMedia = null } = {}) {
  const posts = h.all('SELECT * FROM posts WHERE author_id = ? ORDER BY created_at', author.id);
  const subs = h.all(`SELECT email, created_at FROM email_subs WHERE author_id = ? AND status = 'active' ORDER BY created_at`, author.id);
  const iso = (ms) => (ms ? new Date(ms).toISOString() : '');
  const files = [];
  files.push(['posts.csv', toCsv(['post_id', 'post_date', 'is_published', 'email_sent_at', 'type', 'audience', 'title', 'subtitle', 'podcast_url'],
    posts.map((p) => ({ post_id: `${p.id}.${p.slug}`, post_date: iso(p.published_at || p.created_at), is_published: p.status === 'published' ? 'true' : 'false',
      email_sent_at: '', type: 'newsletter', audience: 'everyone', title: p.title, subtitle: p.dek, podcast_url: '' })), { guard: false })]);
  const media = new Set();
  for (const p of posts) {
    files.push([`posts/${p.id}.${p.slug}.html`, render(p.body_md).html.replace(/ data-p="\d+"/g, '')]);
    files.push([`margin/${p.id}.${p.slug}.md`, p.body_md]);
    for (const m of p.body_md.matchAll(/\(\/media\/([a-f0-9]{24}\.(?:png|jpg|gif|webp))\)/g)) media.add(m[1]);
    files.push([`markdown/${p.slug}.md`, `# ${p.title}\n\n${p.dek ? `*${p.dek}*\n\n` : ''}${p.body_md}\n`]);
  }
  for (const f of media) { const data = readMedia && readMedia(f); if (data) files.push([`media/${f}`, data]); }
  files.push([`email_list.${author.handle}.csv`, toCsv(['email', 'active_subscription', 'expiry', 'email_disabled', 'prefer_digests', 'created_at'],
    subs.map((s) => ({ email: s.email, active_subscription: 'false', expiry: '', email_disabled: 'false', prefer_digests: 'false', created_at: iso(s.created_at) })), { guard: false })]);
  files.push(['README.txt', `Export of @${author.handle} from Margin, ${new Date().toISOString()}.

posts.csv, posts/*.html and email_list.*.csv follow Substack's export layout,
so tools that import from Substack (for example Ghost's migrator) can read this.
markdown/ has every piece as plain Markdown with its title. margin/ has the
exact source Margin stores, and media/ has the images, so importing this into
another Margin site brings everything across unchanged.

The email list contains people who confirmed they want your posts, plus anyone
you imported. Treat it with care.
`]);
  return writeZip(files);
}

module.exports = { importSubstack, exportAuthor, uniqueSlug };
