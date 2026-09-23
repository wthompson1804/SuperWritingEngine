'use strict';
// Everything the platform knows about reading comes from anonymous signals:
// how far a page view got, how long it stayed, which paragraphs were kept,
// whether someone followed or tipped. This module turns those into the front
// page ranking and the writer dashboard.

const { render } = require('./markdown');

const DAY = 86400000;
// A "verified read" needs depth >= 90% and at least a third of normal reading
// time (230 wpm). 60000 / (230 * 3) is about 87 ms per word.
const MS_PER_WORD_FLOOR = 87;
const NEW_VOICE_VIEWS = 150;
const PAGE_SIZE = 7;

function readingMinutes(words) {
  return Math.max(1, Math.round(words / 230));
}

function postStats(h, where = '1=1', ...args) {
  return h.all(`
    SELECT p.id, p.slug, p.title, p.dek, p.words, p.published_at, p.author_id,
           a.handle, a.name AS author_name,
           (SELECT count(*) FROM views v WHERE v.post_id = p.id) AS views,
           (SELECT count(*) FROM views v WHERE v.post_id = p.id AND v.max_depth >= 0.9
              AND v.dwell_ms >= p.words * ${MS_PER_WORD_FLOOR}) AS reads,
           (SELECT count(*) FROM keeps k WHERE k.post_id = p.id) AS keeps,
           (SELECT count(*) FROM tips t WHERE t.post_id = p.id) AS tips,
           (SELECT coalesce(sum(amount_cents), 0) FROM tips t WHERE t.post_id = p.id) AS tip_cents,
           (SELECT coalesce(sum(delta), 0) FROM follow_events f WHERE f.post_id = p.id) AS follows,
           (SELECT count(*) FROM notes n WHERE n.post_id = p.id) AS notes
    FROM posts p JOIN authors a ON a.id = p.author_id
    WHERE p.status = 'published' AND ${where}
    ORDER BY p.published_at DESC`, ...args);
}

// Quality is a smoothed completion rate with a prior of 50%, nudged up by
// keeps and tips. The prior means a piece with 2 views isn't judged on them.
function quality(s) {
  return (s.reads + 0.5 * s.keeps + 2 * s.tips + 2) / (s.views + 4);
}

function authorViews(h) {
  const rows = h.all(`SELECT p.author_id, count(v.pv) AS n FROM posts p LEFT JOIN views v ON v.post_id = p.id GROUP BY p.author_id`);
  return new Map(rows.map((r) => [r.author_id, r.n]));
}

// The front page is finite on purpose: at most seven pieces, two of which are
// reserved for writers who don't have an audience yet (the cold-start answer).
function frontPage(h, now = Date.now()) {
  const stats = postStats(h);
  const av = authorViews(h);
  for (const s of stats) {
    const age = Math.max(0, (now - s.published_at) / DAY);
    s.q = quality(s);
    s.score = s.q * (0.35 + 0.65 * Math.exp(-age / 14));
    s.newVoice = (av.get(s.author_id) || 0) < NEW_VOICE_VIEWS;
    s.minutes = readingMinutes(s.words);
  }
  const perAuthor = new Map();
  const take = (s) => { perAuthor.set(s.author_id, (perAuthor.get(s.author_id) || 0) + 1); };
  const allowed = (s, cap) => (perAuthor.get(s.author_id) || 0) < cap;

  const established = stats.filter((s) => !s.newVoice).sort((a, b) => b.score - a.score);
  const fresh = stats.filter((s) => s.newVoice).sort((a, b) => b.q - a.q);

  const main = [];
  for (const s of established) {
    if (main.length >= PAGE_SIZE - Math.min(2, fresh.length)) break;
    if (allowed(s, 2)) { main.push(s); take(s); }
  }
  const newcomers = [];
  for (const s of fresh) {
    if (newcomers.length >= PAGE_SIZE - main.length) break;
    if (allowed(s, 1)) { newcomers.push(s); take(s); }
  }
  // Fill any leftover room (e.g. every writer is new) without breaking caps.
  for (const s of [...established, ...fresh]) {
    if (main.length + newcomers.length >= PAGE_SIZE) break;
    if (!main.includes(s) && !newcomers.includes(s) && allowed(s, 2)) { main.push(s); take(s); }
  }
  // Newcomers sit in slots 3 and 6, not buried at the bottom.
  const out = [...main];
  newcomers.forEach((s, i) => out.splice(Math.min(out.length, 2 + i * 3), 0, s));
  for (const s of out) s.reason = reason(s);
  return out;
}

function reason(s) {
  if (s.newVoice) return 'New voice. Here so it gets a fair read.';
  if (s.views >= 10) return `Finished by ${Math.round((100 * s.reads) / s.views)}% of people who opened it.`;
  return 'Just published.';
}

function nextReads(h, post) {
  const same = h.get(`SELECT slug, title, dek, words FROM posts WHERE author_id = ? AND id != ? AND status = 'published' ORDER BY published_at DESC LIMIT 1`, post.author_id, post.id);
  const other = frontPage(h).find((s) => s.author_id !== post.author_id);
  return { same, other };
}

function median(xs) {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function authorDashboard(h, authorId) {
  const posts = postStats(h, 'p.author_id = ?', authorId);
  for (const p of posts) {
    const depths = h.all('SELECT max_depth FROM views WHERE post_id = ?', p.id).map((r) => r.max_depth);
    p.medianDepth = median(depths);
    p.completion = p.views ? p.reads / p.views : 0;
    p.minutes = readingMinutes(p.words);
  }
  const followers = h.get('SELECT coalesce(sum(delta),0) AS n FROM follow_events WHERE author_id = ?', authorId).n;
  const keyedFollowers = h.get('SELECT count(*) AS n FROM reader_follows WHERE author_id = ?', authorId).n;
  const list = h.all(`SELECT r.email, rf.created_at FROM reader_follows rf JOIN readers r ON r.id = rf.reader_id
                      WHERE rf.author_id = ? AND r.share_email = 1 AND r.email IS NOT NULL ORDER BY rf.created_at DESC`, authorId);
  const asks = h.all(`SELECT a.kind, a.event, count(*) AS n FROM asks a JOIN posts p ON p.id = a.post_id
                      WHERE p.author_id = ? GROUP BY a.kind, a.event`, authorId);
  const funnel = {};
  for (const r of asks) (funnel[r.kind] ||= { shown: 0, accepted: 0 })[r.event] = r.n;
  const drafts = h.all(`SELECT id, slug, title, updated_at FROM posts WHERE author_id = ? AND status = 'draft' ORDER BY updated_at DESC`, authorId);
  return { posts, followers, keyedFollowers, list, funnel, drafts };
}

// Per-paragraph view of one piece: how many readers reached it and how many kept it.
function paragraphMap(h, post) {
  const { blocks, words } = render(post.body_md);
  const depths = h.all('SELECT max_depth FROM views WHERE post_id = ?', post.id).map((r) => r.max_depth);
  const keeps = new Map(h.all('SELECT para, count(*) AS n FROM keeps WHERE post_id = ? GROUP BY para', post.id).map((r) => [r.para, r.n]));
  const notes = new Map(h.all('SELECT para, count(*) AS n FROM notes WHERE post_id = ? GROUP BY para', post.id).map((r) => [r.para, r.n]));
  let cum = 0;
  const maxKeep = Math.max(1, ...keeps.values());
  return blocks.map((b) => {
    const start = words ? cum / words : 0;
    cum += b.words;
    const reached = depths.length ? depths.filter((d) => d >= start).length / depths.length : 0;
    const k = keeps.get(b.i) || 0;
    return { ...b, reached, keeps: k, keepShare: k / maxKeep, notes: notes.get(b.i) || 0 };
  });
}

module.exports = { frontPage, nextReads, authorDashboard, paragraphMap, readingMinutes, quality, MS_PER_WORD_FLOOR, NEW_VOICE_VIEWS };
