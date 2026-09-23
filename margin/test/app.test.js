'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { createApp } = require('../server');
const { render } = require('../lib/markdown');
const { checkOpening, checkDraft } = require('../lib/draftcheck');
const { newReaderKey, hashKey, normalizeKey } = require('../lib/auth');
const { buildBrief } = require('../scripts/digest');

let app, base;
test.before(async () => {
  app = createApp({ dbFile: ':memory:', demoSignals: true });
  await new Promise((r) => app.server.listen(0, r));
  base = `http://127.0.0.1:${app.server.address().port}`;
});
test.after(() => app.server.close());

const post = (p, body) => fetch(base + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const uuid = () => crypto.randomUUID();

test('markdown escapes HTML and indexes blocks', () => {
  const r = render('Hello <script>alert(1)</script> **bold**\n\n## Head\n\n> quote\n\n- a\n- b\n\n[x](javascript:alert(1)) [y](https://e.com)');
  assert.ok(!r.html.includes('<script>'));
  assert.ok(r.html.includes('<strong>bold</strong>'));
  assert.ok(!r.html.includes('javascript:'));
  assert.ok(r.html.includes('href="https://e.com"'));
  assert.deepEqual(r.blocks.map((b) => b.kind), ['p', 'h', 'quote', 'li', 'li', 'p']);
});

test('draft check flags weak openings and passes strong ones', () => {
  assert.ok(checkOpening('In recent years, many things have changed.').some((r) => r.level === 'warn'));
  assert.ok(checkOpening('What does it mean to be sovereign?').some((r) => r.level === 'warn'));
  assert.ok(checkOpening('When we think about business, we see change.').some((r) => r.level === 'warn'));
  assert.equal(checkOpening('The American-led world order is over.').filter((r) => r.level === 'warn').length, 0);
  const d = checkDraft('The order is over.\n\nPerhaps it seems that in order to win we must make a decision. This isn\'t about branding. It\'s about survival.');
  const rules = d.body.map((r) => r.rule);
  assert.ok(rules.includes('A.2'));
  assert.ok(rules.includes('A.3'));
});

test('reader keys normalize and hash', () => {
  const k = newReaderKey();
  assert.match(k, /^[a-z]+-[a-z]+-[a-z]+-[a-z]+-[A-Z2-9]{6}$/);
  assert.equal(hashKey(k.toUpperCase().replace(/-/g, ' ')), hashKey(k));
  assert.equal(normalizeKey('nope'), null);
});

test('front page and articles need no account and set no cookies', async () => {
  const res = await fetch(base + '/');
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('set-cookie'), null);
  const page = await res.text();
  assert.match(page, /Today's reading/);
  assert.match(page, /New voice/); // cold-start slot for the writer with no audience
  const cards = page.match(/class="card/g) || [];
  assert.ok(cards.length >= 1 && cards.length <= 7);

  const art = await fetch(base + '/p/the-bus-stop-is-the-city');
  assert.equal(art.status, 200);
  assert.equal(art.headers.get('set-cookie'), null);
  const html = await art.text();
  assert.match(html, /data-p="0"/);
  assert.ok(!/sign ?up|subscribe to (continue|read)/i.test(html.split('<main')[1].split('</main>')[0].replace(/Brief/g, '')));
});

test('reading signal: verified reads need depth and dwell', async () => {
  const pvA = uuid(), pvB = uuid();
  const before = app.h.get(`SELECT count(*) n FROM views v JOIN posts p ON p.id = v.post_id WHERE p.slug = 'finishing-is-a-feature'`).n;
  assert.equal((await post('/api/read', { slug: 'finishing-is-a-feature', pv: pvA, depth: 0.95, dwell: 999999 })).status, 200);
  await post('/api/read', { slug: 'finishing-is-a-feature', pv: pvB, depth: 1, dwell: 500 }); // skimmed
  await post('/api/read', { slug: 'finishing-is-a-feature', pv: pvA, depth: 0.2, dwell: 10 }); // never lowers
  const row = app.h.get('SELECT max_depth, dwell_ms FROM views WHERE pv = ?', pvA);
  assert.equal(row.max_depth, 0.95);
  const { frontPage } = require('../lib/signals');
  const june = frontPage(app.h).find((s) => s.slug === 'finishing-is-a-feature');
  assert.equal(june.views, before + 2);
  assert.equal(june.reads, 1);
  assert.equal((await post('/api/read', { slug: 'nope', pv: uuid(), depth: 1 })).status, 400);
});

test('keeps are deduped per page view', async () => {
  const pv = uuid();
  await post('/api/keep', { slug: 'finishing-is-a-feature', para: 2, pv });
  await post('/api/keep', { slug: 'finishing-is-a-feature', para: 2, pv });
  const n = app.h.get(`SELECT count(*) n FROM keeps k JOIN posts p ON p.id = k.post_id WHERE p.slug = 'finishing-is-a-feature' AND para = 2`).n;
  assert.equal(n, 1);
});

test('reader key: create, sync, merge, follows, prefs, notes', async () => {
  const local = { kept: { a: { slug: 'x', text: 'one', ts: 1 } }, follows: { theo: { on: true, ts: 5 } }, finished: {} };
  const created = await (await post('/api/key/new', { data: local })).json();
  assert.ok(created.key);
  const reader = app.h.get('SELECT * FROM readers WHERE key_hash = ?', hashKey(created.key));
  assert.ok(reader);
  assert.ok(!JSON.stringify(reader).includes(created.key), 'key stored only as hash');

  // Another device syncs a newer edit and a new passage.
  const other = { kept: { a: { slug: 'x', text: 'one', note: 'hi', ts: 9 }, b: { slug: 'y', text: 'two', ts: 3 } }, follows: {}, finished: {} };
  const synced = await (await post('/api/key/sync', { key: created.key, data: other })).json();
  assert.equal(synced.data.kept.a.note, 'hi');
  assert.ok(synced.data.kept.b);
  assert.equal(synced.data.follows.theo.on, true);
  assert.equal(app.h.get('SELECT count(*) n FROM reader_follows WHERE reader_id = ?', reader.id).n, 1);

  assert.equal((await post('/api/key/sync', { key: 'otter-otter-otter-otter-AAAAAA', data: {} })).status, 404);

  const bad = await post('/api/key/prefs', { key: created.key, email: 'nope' });
  assert.equal(bad.status, 400);
  const ok = await (await post('/api/key/prefs', { key: created.key, email: 'r@example.com', digest: true, share_email: true })).json();
  assert.deepEqual(ok.prefs, { email: 'r@example.com', digest: true, share_email: true });

  assert.equal((await post('/api/note', { slug: 'the-bus-stop-is-the-city', para: 1, body: 'x' })).status, 403);
  const note = await (await post('/api/note', { key: created.key, slug: 'the-bus-stop-is-the-city', para: 1, body: '<b>Good</b> point', quote: 'Look' })).json();
  assert.equal(note.ok, true);
  const art = await (await fetch(base + '/p/the-bus-stop-is-the-city')).text();
  assert.match(art, /&lt;b&gt;Good&lt;\/b&gt; point/);

  const brief = buildBrief(app.h, app.h.get('SELECT * FROM readers WHERE id = ?', reader.id));
  assert.ok(brief.picks.length >= 1 && brief.picks.length <= 5);
});

test('writer flow: signup, draft, check, publish, dashboard, CSV', async () => {
  const form = (p, obj, cookie) => fetch(base + p, { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...(cookie ? { Cookie: cookie } : {}) }, body: new URLSearchParams(obj) });
  assert.equal((await fetch(base + '/dashboard', { redirect: 'manual' })).status, 303);
  const su = await form('/signup', { name: 'Test Writer', handle: 'tester', password: 'long-enough-pw' });
  assert.equal(su.status, 303);
  const cookie = su.headers.get('set-cookie').split(';')[0];
  assert.match(su.headers.get('set-cookie'), /HttpOnly/);

  const draft = await form('/write/new', { title: 'A Test Piece', dek: 'd', body_md: 'The claim is simple.\n\nMore text here.', action: 'save' }, cookie);
  assert.equal(draft.status, 303);
  const id = draft.headers.get('location').split('/').pop();
  assert.equal((await fetch(base + '/p/a-test-piece')).status, 404, 'drafts are not public');

  const pub = await form(`/write/${id}`, { title: 'A Test Piece, Renamed', dek: 'd', body_md: 'The claim is simple.\n\nMore text.', action: 'publish' }, cookie);
  assert.equal(pub.headers.get('location'), '/p/a-test-piece-renamed');
  assert.equal((await fetch(base + '/p/a-test-piece-renamed')).status, 200);

  // Another writer can't edit it.
  const mara = await form('/login', { handle: 'mara', password: 'demo-password' });
  const maraCookie = mara.headers.get('set-cookie').split(';')[0];
  assert.equal((await fetch(`${base}/write/${id}`, { headers: { Cookie: maraCookie } })).status, 404);

  const dash = await (await fetch(base + '/dashboard', { headers: { Cookie: maraCookie } })).text();
  assert.match(dash, /Verified reads/);
  const detail = await fetch(base + '/dashboard/p/the-meeting-is-the-work-now', { headers: { Cookie: maraCookie } });
  assert.equal(detail.status, 200);
  const csv = await fetch(base + '/dashboard/list.csv', { headers: { Cookie: maraCookie } });
  assert.match(await csv.text(), /^email,following_since/);

  const check = await (await post('/api/check', { body_md: 'In recent years, things changed.' })).json();
  assert.ok(check.opening.some((r) => r.level === 'warn'));
});

test('rss feed lists published pieces', async () => {
  const xml = await (await fetch(base + '/feed.xml?author=theo')).text();
  assert.match(xml, /The Bus Stop Is the City/);
  assert.ok(!xml.includes('The Meeting Is the Work Now'));
});
