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
           (SELECT count(*) FROM notes n WHERE n.post_id = p.id) AS notes,
           (SELECT count(*) FROM passes x WHERE x.post_id = p.id) AS passes,
           (SELECT count(*) FROM views v WHERE v.post_id = p.id AND v.source = 'passed') AS passed_in
    FROM posts p JOIN authors a ON a.id = p.author_id
    WHERE p.status = 'published' AND ${where}
    ORDER BY p.published_at DESC`, ...args);
}

// Finishing a long piece is harder than finishing a short one. Across the web,
// completion falls as length grows (Chartbeat, Medium read ratios), so raw
// finish rate would push the front page toward short posts. We compare each
// piece against a baseline for its length instead.
// ASSUMPTION: the curve (60% at 400 words, down about 9 points per doubling,
// floor 20%) is set by hand from public ranges (Medium read ratios of roughly
// 40–70%, Chartbeat's ~30s average engaged time). Recalibrate it from Margin's
// own views once there are a few thousand of them.
function expectedCompletion(words) {
  const w = Math.max(300, words || 0);
  return Math.min(0.65, Math.max(0.2, 0.6 - 0.09 * Math.log2(w / 400)));
}

// Quality is completion relative to that baseline, smoothed with a prior worth
// four ordinary views, and nudged up by keeps, passes and tips. A piece at the
// baseline scores 1.0; a piece with two views isn't judged on them.
function quality(s) {
  const e = expectedCompletion(s.words);
  const prior = 4;
  // Tips are left out while they're simulated: an unpaid tip costs nothing to
  // forge. Add them back (paid ones only) once real payments exist.
  return (s.reads + 0.5 * s.keeps + s.passes + prior * e) / (s.views * e + prior);
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
  if (s.views >= 10) {
    const got = s.reads / s.views;
    // Only show the comparison when it's good news; below-baseline numbers
    // on a front page read as warnings, not reasons.
    if (got > expectedCompletion(s.words) * 1.05) return `Finished by ${Math.round(100 * got)}% of readers, more than most pieces this long.`;
    return `Read to the end by ${s.reads} ${s.reads === 1 ? 'person' : 'people'}.`;
  }
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
    p.expected = expectedCompletion(p.words);
    p.medianMinutes = median(h.all('SELECT dwell_ms FROM views WHERE post_id = ? AND dwell_ms > 0', p.id).map((r) => r.dwell_ms)) / 60000;
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
  const drafts = h.all(`SELECT id, slug, title, status, publish_at, updated_at FROM posts WHERE author_id = ? AND status IN ('draft', 'scheduled') ORDER BY status DESC, updated_at DESC`, authorId);
  const sources = h.all(`SELECT v.source, count(*) AS n FROM views v JOIN posts p ON p.id = v.post_id
                         WHERE p.author_id = ? GROUP BY v.source ORDER BY n DESC`, authorId);
  const now = h.get(`SELECT count(*) AS n FROM views v JOIN posts p ON p.id = v.post_id WHERE p.author_id = ? AND v.seen_at > ?`, authorId, Date.now() - 90000).n;
  const me = '@' + h.get('SELECT handle FROM authors WHERE id = ?', authorId).handle;
  const recommendedBy = h.all('SELECT handle, name, blogroll FROM authors WHERE id != ?', authorId)
    .filter((a) => a.blogroll.split('\n').map((l) => l.trim().toLowerCase()).includes(me));
  const emailSubs = h.get(`SELECT count(*) AS n FROM email_subs WHERE author_id = ? AND status = 'active'`, authorId).n;
  const emailPending = h.get(`SELECT count(*) AS n FROM email_subs WHERE author_id = ? AND status = 'pending'`, authorId).n;
  // Recommendation ledger: followers you sent to other writers, and followers
  // other writers sent you. Substack's network runs on this; ours is visible.
  // Both sides count the same things: follows here, plus confirmed email follows.
  const sent = h.get(`SELECT count(*) AS n FROM follow_events WHERE via_author_id = ? AND delta > 0`, authorId).n
    + h.get(`SELECT count(*) AS n FROM email_subs WHERE via_author_id = ? AND status = 'active'`, authorId).n;
  const received = h.all(`SELECT a.handle, a.name, count(*) AS n FROM (
                            SELECT via_author_id AS v FROM follow_events WHERE author_id = ? AND delta > 0 AND via_author_id IS NOT NULL
                            UNION ALL SELECT via_author_id FROM email_subs WHERE author_id = ? AND status = 'active' AND via_author_id IS NOT NULL
                          ) x JOIN authors a ON a.id = x.v GROUP BY a.id ORDER BY n DESC`, authorId, authorId);
  const notesList = h.all(`SELECT n.id, n.body, n.quote, n.display_name, n.hidden, n.flags, n.created_at, p.slug, p.title
                           FROM notes n JOIN posts p ON p.id = n.post_id WHERE p.author_id = ? ORDER BY n.flags DESC, n.created_at DESC LIMIT 50`, authorId);
  const fedi = h.get('SELECT count(*) AS n FROM ap_followers WHERE author_id = ?', authorId).n;
  return { posts, followers, keyedFollowers, list, funnel, drafts, sources, now, recommendedBy, emailSubs, emailPending, sent, received, notesList, fedi };
}

// Per-paragraph view of one piece: how many readers reached it and how many kept it.
function paragraphMap(h, post) {
  const { blocks, words } = render(post.body_md);
  const depths = h.all('SELECT max_depth FROM views WHERE post_id = ?', post.id).map((r) => r.max_depth);
  const keeps = new Map(h.all('SELECT para, count(*) AS n FROM keeps WHERE post_id = ? GROUP BY para', post.id).map((r) => [r.para, r.n]));
  const notes = new Map(h.all('SELECT para, count(*) AS n FROM notes WHERE post_id = ? GROUP BY para', post.id).map((r) => [r.para, r.n]));
  const passes = new Map(h.all('SELECT para, count(*) AS n FROM passes WHERE post_id = ? GROUP BY para', post.id).map((r) => [r.para, r.n]));
  let cum = 0;
  const maxLove = Math.max(1, ...blocks.map((b) => (keeps.get(b.i) || 0) + (passes.get(b.i) || 0)));
  return blocks.map((b) => {
    const start = words ? cum / words : 0;
    cum += b.words;
    const reached = depths.length ? depths.filter((d) => d >= start).length / depths.length : 0;
    const k = keeps.get(b.i) || 0;
    const ps = passes.get(b.i) || 0;
    return { ...b, reached, keeps: k, passes: ps, keepShare: (k + ps) / maxLove, notes: notes.get(b.i) || 0 };
  });
}

module.exports = { frontPage, nextReads, authorDashboard, paragraphMap, readingMinutes, quality, expectedCompletion, MS_PER_WORD_FLOOR, NEW_VOICE_VIEWS };
