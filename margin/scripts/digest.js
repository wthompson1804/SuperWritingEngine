'use strict';
// Builds this week's Brief for every reader who asked for it and writes each
// email to the outbox table and to data/outbox/*.html. No email is actually
// sent: wiring a mail provider is the next step, and it goes here.
const fs = require('node:fs');
const path = require('node:path');
const { open, helpers } = require('../lib/db');
const { frontPage, readingMinutes } = require('../lib/signals');
const { esc } = require('../lib/markdown');

const WEEK = 7 * 86400000;
const BASE = process.env.MARGIN_BASE_URL || 'http://localhost:3000';

function buildBrief(h, reader, now = Date.now()) {
  let data = {};
  try { data = JSON.parse(reader.data); } catch { /* empty */ }
  const finished = data.finished || {};
  const followed = h.all(`SELECT p.slug, p.title, p.dek, p.words, a.name AS author_name FROM reader_follows rf
    JOIN posts p ON p.author_id = rf.author_id AND p.status = 'published' AND p.published_at > ?
    JOIN authors a ON a.id = p.author_id WHERE rf.reader_id = ? ORDER BY p.published_at DESC`, now - WEEK, reader.id);
  const picks = [];
  const seen = new Set();
  for (const p of [...followed.map((x) => ({ ...x, why: 'From a writer you follow' })), ...frontPage(h, now).map((x) => ({ ...x, why: x.reason }))]) {
    if (picks.length >= 5) break;
    if (seen.has(p.slug) || finished[p.slug]) continue;
    seen.add(p.slug); picks.push(p);
  }
  const minutes = picks.reduce((n, p) => n + readingMinutes(p.words), 0);
  const html = `<!doctype html><html><body style="font-family:Georgia,serif;max-width:36rem;margin:auto;color:#1f1c18">
<h1 style="font-size:1.5rem">The Brief</h1>
<p>${picks.length} pieces, about ${minutes} minutes. That's all of it this week.</p>
${picks.map((p) => `<div style="margin:1.4rem 0"><p style="font:12px sans-serif;color:#b4441f;margin:0">${esc(p.why)}</p>
<a href="${BASE}/p/${p.slug}?via=brief" style="font-size:1.2rem;color:#1f1c18">${esc(p.title)}</a>
<p style="margin:.2rem 0;color:#57514a">${esc(p.dek)}</p><p style="font:12px sans-serif;color:#57514a;margin:0">${esc(p.author_name)} · ${readingMinutes(p.words)} min</p></div>`).join('')}
<p style="font:12px sans-serif;color:#57514a">You're getting this because you turned on The Brief with your reader key. Turn it off any time at ${BASE}/commonplace.</p>
</body></html>`;
  return { subject: `The Brief: ${picks.length} pieces, ${minutes} minutes`, html, picks };
}

function run() {
  const h = helpers(open(process.env.MARGIN_DB || path.join(__dirname, '..', 'data', 'margin.db')));
  const readers = h.all('SELECT * FROM readers WHERE digest = 1 AND email IS NOT NULL');
  const dir = path.join(__dirname, '..', 'data', 'outbox');
  fs.mkdirSync(dir, { recursive: true });
  for (const r of readers) {
    const b = buildBrief(h, r);
    h.run('INSERT INTO outbox (reader_id, email, subject, html, created_at) VALUES (?,?,?,?,?)', r.id, r.email, b.subject, b.html, Date.now());
    fs.writeFileSync(path.join(dir, `brief-${r.id}-${Date.now()}.html`), b.html);
  }
  console.log(`Built ${readers.length} Brief${readers.length === 1 ? '' : 's'} into data/outbox/.`);
}

if (require.main === module) run();
module.exports = { buildBrief };
