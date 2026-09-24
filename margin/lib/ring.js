'use strict';
// The web used to be held together by people pointing at each other: webrings,
// blogrolls, link pages. This module is that layer. Every writer is in the
// ring, and every writer keeps a short list of who they read, on Margin or off it.

const ACCENTS = ['cobalt', 'vermilion', 'moss', 'teal', 'plum', 'ochre', 'ink'];
const LIVE_MS = 90_000;

function ringOrder(h) {
  return h.all(`SELECT a.id, a.handle, a.name, a.now_line, a.accent,
      (SELECT count(*) FROM posts p WHERE p.author_id = a.id AND p.status = 'published') AS pieces,
      (SELECT max(published_at) FROM posts p WHERE p.author_id = a.id AND p.status = 'published') AS last_at
    FROM authors a ORDER BY a.created_at, a.id`).filter((a) => a.pieces > 0);
}

function ringStep(h, fromHandle, dir) {
  const ring = ringOrder(h);
  if (!ring.length) return null;
  const i = ring.findIndex((a) => a.handle === fromHandle);
  if (dir === 'random') {
    const others = ring.filter((a) => a.handle !== fromHandle);
    return (others.length ? others : ring)[Math.floor(Math.random() * (others.length || ring.length))];
  }
  // From outside the ring (a writer with nothing published yet), "next" is
  // the first writer and "prev" the last.
  if (i < 0) return dir === 'prev' ? ring[ring.length - 1] : ring[0];
  const step = dir === 'prev' ? -1 : 1;
  return ring[(i + step + ring.length) % ring.length];
}

// Blogroll lines are either "@handle" or "https://url Optional title".
function parseBlogroll(h, text) {
  const out = [];
  for (const raw of String(text || '').split('\n').map((l) => l.trim()).filter(Boolean).slice(0, 12)) {
    let m;
    if ((m = raw.match(/^@([a-z0-9_]{2,24})$/i))) {
      const a = h.get('SELECT handle, name, now_line FROM authors WHERE handle = ?', m[1].toLowerCase());
      if (a) out.push({ kind: 'writer', href: `/@${a.handle}`, title: a.name, note: a.now_line });
    } else if ((m = raw.match(/^(https?:\/\/\S+)(?:\s+(.+))?$/i))) {
      let host = '';
      try { host = new URL(m[1]).hostname.replace(/^www\./, ''); } catch { continue; }
      out.push({ kind: 'web', href: m[1], title: (m[2] || host).slice(0, 80), note: host });
    }
  }
  return out;
}

function normalizeBlogroll(text) {
  return String(text || '').split('\n').map((l) => l.trim()).filter((l) => /^@[a-z0-9_]{2,24}$/i.test(l) || /^https?:\/\/\S+/i.test(l)).slice(0, 12).join('\n');
}

function readingNow(h, postId) {
  const since = Date.now() - LIVE_MS;
  return postId == null
    ? h.get('SELECT count(*) AS n FROM views WHERE seen_at > ?', since).n
    : h.get('SELECT count(*) AS n FROM views WHERE post_id = ? AND seen_at > ?', postId, since).n;
}

function spotlight(h, excludeIds = []) {
  // Prefer writers with the fewest opens: the ring should lift the quiet ones.
  const rows = h.all(`SELECT a.handle, a.name, a.now_line, a.accent, count(v.pv) AS opens,
      (SELECT slug FROM posts p2 WHERE p2.author_id = a.id AND p2.status = 'published' ORDER BY published_at DESC LIMIT 1) AS latest_slug,
      (SELECT title FROM posts p2 WHERE p2.author_id = a.id AND p2.status = 'published' ORDER BY published_at DESC LIMIT 1) AS latest_title
    FROM authors a JOIN posts p ON p.author_id = a.id AND p.status = 'published'
    LEFT JOIN views v ON v.post_id = p.id GROUP BY a.id ORDER BY opens ASC`).filter((r) => !excludeIds.includes(r.handle));
  const pool = rows.slice(0, Math.max(1, Math.ceil(rows.length / 2)));
  return pool.length ? pool[Math.floor(Math.random() * pool.length)] : null;
}

module.exports = { ACCENTS, ringOrder, ringStep, parseBlogroll, normalizeBlogroll, readingNow, spotlight, LIVE_MS };
