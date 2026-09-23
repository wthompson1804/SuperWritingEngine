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
  assert.match(page, /Today’s reading/);
  assert.match(page, /new voice/); // cold-start slot for the writer with no audience
  const cards = page.match(/<li class="card/g) || [];
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
  assert.match(dash, /verified reads/);
  const detail = await fetch(base + '/dashboard/p/the-meeting-is-the-work-now', { headers: { Cookie: maraCookie } });
  assert.equal(detail.status, 200);
  const csv = await fetch(base + '/dashboard/list.csv', { headers: { Cookie: maraCookie } });
  assert.match(await csv.text(), /^email,source,since\n/);

  const check = await (await post('/api/check', { body_md: 'In recent years, things changed.' })).json();
  assert.ok(check.opening.some((r) => r.level === 'warn'));
});

test('rss feed lists published pieces', async () => {
  const xml = await (await fetch(base + '/feed.xml?author=theo')).text();
  assert.match(xml, /The Bus Stop Is the City/);
  assert.ok(!xml.includes('The Meeting Is the Work Now'));
});

test('the ring: directory, next/prev/random, blogrolls and "read by"', async () => {
  const ringPage = await (await fetch(base + '/ring')).text();
  for (const n of ['Mara Okafor', 'Theo Lindqvist', 'June Hale', 'Ravi Menon']) assert.match(ringPage, new RegExp(n));
  const next = await fetch(base + '/ring/next?from=mara', { redirect: 'manual' });
  assert.equal(next.status, 303);
  assert.equal(next.headers.get('location'), '/@theo?via=ring');
  const prev = await fetch(base + '/ring/prev?from=mara', { redirect: 'manual' });
  assert.match(prev.headers.get('location'), /^\/@\w+\?via=ring$/);
  const rnd = await fetch(base + '/ring/random?from=mara', { redirect: 'manual' });
  assert.ok(!rnd.headers.get('location').startsWith('/@mara'));
  const june = await (await fetch(base + '/@june')).text();
  assert.match(june, /read by/);          // Mara lists June
  assert.match(june, /Mara Okafor/);
  assert.match(june, /acc-plum/);
  const art = await (await fetch(base + '/p/the-bus-stop-is-the-city')).text();
  assert.match(art, /theo reads/);
  assert.match(art, /the margin ring/);
});

test('pass it on and presence', async () => {
  const r = await (await post('/api/pass', { slug: 'the-screw-you-cant-turn', para: 2 })).json();
  assert.equal(r.url, '/p/the-screw-you-cant-turn?via=passed&p=2');
  const pv = uuid();
  const beat = await (await post('/api/read', { slug: 'the-screw-you-cant-turn', pv, depth: 0.3, dwell: 5000, source: 'passed' })).json();
  assert.ok(beat.now >= 1);
  const pres = await (await fetch(base + '/api/presence?slug=the-screw-you-cant-turn')).json();
  assert.ok(pres.now >= 1);
  await post('/api/read', { slug: 'the-screw-you-cant-turn', pv, depth: 0.3, dwell: 6000, visible: false });
  const after = await (await fetch(base + '/api/presence?slug=the-screw-you-cant-turn')).json();
  assert.equal(after.now, pres.now - 1, 'hiding the tab stops counting as reading now');
  assert.equal(app.h.get(`SELECT source FROM views WHERE pv = ?`, pv).source, 'passed');
});

test('writer homepage settings validate accent and blogroll', async () => {
  const login = await fetch(base + '/login', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ handle: 'ravi', password: 'demo-password' }) });
  const cookie = login.headers.get('set-cookie').split(';')[0];
  const save = await fetch(base + '/desk/profile', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded', Cookie: cookie },
    body: new URLSearchParams({ name: 'Ravi M.', bio: 'b', now_line: 'Now: gears', accent: 'hotpink', blogroll: '@june\njavascript:alert(1)\nhttps://example.com Example\nnot a link' }) });
  assert.equal(save.status, 303);
  const row = app.h.get(`SELECT name, accent, blogroll, now_line FROM authors WHERE handle = 'ravi'`);
  assert.equal(row.accent, 'cobalt');
  assert.equal(row.blogroll, '@june\nhttps://example.com Example');
  assert.equal(row.now_line, 'Now: gears');
  const page = await (await fetch(base + '/@ravi')).text();
  assert.match(page, /href="https:\/\/example.com"/);
  assert.ok(!page.includes('javascript:'));
  const dash = await (await fetch(base + '/dashboard', { headers: { Cookie: cookie } })).text();
  assert.match(dash, /Where readers came from/);
  assert.match(dash, /Theo Lindqvist<\/a> lists you/);
});

test('declaration and fonts are served locally', async () => {
  const d = await fetch(base + '/declaration');
  assert.equal(d.status, 200);
  assert.match(await d.text(), /We would like the web back/);
  const f = await fetch(base + '/static/fonts/newsreader-latin-wght-normal.woff2');
  assert.equal(f.status, 200);
  assert.equal(f.headers.get('content-type'), 'font/woff2');
  assert.equal((await fetch(base + '/static/../server.js')).status, 404);
  assert.match(d.headers.get('content-security-policy'), /font-src 'self'/);
});

// ---------------- v3 ----------------
const { writeZip, readZip } = require('../lib/zip');
const { parseCsv, toCsv } = require('../lib/csv');
const { htmlToMarkdown } = require('../lib/htmlmd');
const { expectedCompletion, quality } = require('../lib/signals');

const formPost = (p, obj, cookie) => fetch(base + p, { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...(cookie ? { Cookie: cookie } : {}) }, body: new URLSearchParams(obj) });
async function loginAs(handle) {
  const r = await formPost('/login', { handle, password: 'demo-password' });
  return r.headers.get('set-cookie').split(';')[0];
}

test('csv round-trips quotes/newlines and neutralizes formulas', () => {
  const rows = parseCsv('a,b\n"x, ""y""","line1\nline2"\n');
  assert.deepEqual(rows, [{ a: 'x, "y"', b: 'line1\nline2' }]);
  assert.match(toCsv(['e'], [{ e: '=HYPERLINK("x")' }]), /"'=HYPERLINK/);
});

test('html to markdown keeps structure and drops Substack widgets', () => {
  const md = htmlToMarkdown(`<div class="body"><h2>Why</h2><p>It is <strong>bold</strong> and <em>odd</em> &amp; <a href="https://x.com/a">linked</a>.</p>
    <div class="subscription-widget-wrap"><div class="subscription-widget"><button>Subscribe</button></div></div>
    <blockquote><p>A quote.</p></blockquote><ul><li>one</li><li>two</li></ul>
    <figure><img src="https://cdn.example/i.png" alt="x"><figcaption>A chart</figcaption></figure><script>alert(1)</script></div>`);
  assert.match(md, /^# Why/m);
  assert.match(md, /It is \*\*bold\*\* and \*odd\* & \[linked\]\(https:\/\/x.com\/a\)\./);
  assert.match(md, /^> A quote\.$/m);
  assert.match(md, /^- one$/m);
  assert.match(md, /\[Image: A chart\]\(https:\/\/cdn.example\/i.png\)/);
  assert.ok(!/Subscribe|alert/.test(md));
});

test('ranking compares finish rate against length', () => {
  assert.ok(expectedCompletion(3000) < expectedCompletion(600));
  const short = { words: 500, views: 100, reads: 60, keeps: 0, passes: 0, tips: 0 };
  const long = { words: 4000, views: 100, reads: 45, keeps: 0, passes: 0, tips: 0 };
  assert.ok(quality(long) > quality(short), 'a long piece finished by 45% beats a short one finished by 60%');
});

test('substack import: posts, drafts, subscribers, idempotent; export re-imports', async () => {
  const zip = writeZip([
    ['posts.csv', 'post_id,post_date,is_published,email_sent_at,type,audience,title,subtitle,podcast_url\n'
      + '101.hello-world,2024-03-01T10:00:00.000Z,true,,newsletter,everyone,Hello World,"A first post, with comma",\n'
      + '102.paid-thing,2024-04-01T10:00:00.000Z,true,,newsletter,only_paid,Paid Thing,,\n'
      + '103.a-draft,,false,,newsletter,everyone,A Draft,,\n'
      + '104.thread,2024-05-01T10:00:00.000Z,true,,thread,everyone,A Thread,,\n'],
    ['posts/101.hello-world.html', '<p>The first claim is the point.</p><p>Second <em>paragraph</em>.</p>'],
    ['posts/102.paid-thing.html', '<p>Paid words.</p>'],
    ['posts/103.a-draft.html', '<p>Unfinished.</p>'],
    ['email_list.hello.csv', 'email,active_subscription,expiry,email_disabled,prefer_digests,created_at\n'
      + 'A@Example.com,false,,false,false,2024-01-01T00:00:00.000Z\n'
      + 'paid@example.com,true,2025-01-01,false,false,2024-01-02T00:00:00.000Z\n'
      + 'gone@example.com,false,,true,false,2024-01-03T00:00:00.000Z\n'
      + 'not-an-email,false,,false,false,\n'],
  ]);
  const su = await formPost('/signup', { name: 'Importer', handle: 'importer', password: 'long-enough-pw' });
  const cookie = su.headers.get('set-cookie').split(';')[0];
  const up = (buf) => fetch(base + '/desk/import', { method: 'POST', headers: { 'Content-Type': 'application/zip', Cookie: cookie }, body: buf });
  const r = await (await up(zip)).json();
  assert.equal(r.ok, true);
  assert.deepEqual([r.report.posts.published, r.report.posts.drafts, r.report.posts.skipped], [1, 2, 1]);
  assert.deepEqual([r.report.subscribers.imported, r.report.subscribers.paid, r.report.subscribers.skipped], [2, 1, 2]);
  assert.ok(r.report.warnings.some((w) => /paid-only/.test(w)));
  const art = await fetch(base + '/p/hello-world');
  assert.equal(art.status, 200);
  assert.match(await art.text(), /Second <em>paragraph<\/em>/);
  assert.equal((await fetch(base + '/p/paid-thing')).status, 404, 'paid posts are drafts');
  const again = await (await up(zip)).json();
  assert.equal(again.report.posts.already, 3);
  assert.equal(again.report.subscribers.already, 2);
  assert.equal((await (await up(Buffer.from('nope'))).json()).ok, false);
  assert.equal((await fetch(base + '/desk/import', { method: 'POST', redirect: 'manual', body: zip })).status, 303, 'writers only');

  // Export, then import that export as a different writer.
  const ex = await fetch(base + '/desk/export.zip', { headers: { Cookie: cookie } });
  assert.equal(ex.headers.get('content-type'), 'application/zip');
  const files = readZip(Buffer.from(await ex.arrayBuffer()));
  assert.ok(files.has('posts.csv') && files.has('email_list.importer.csv') && files.has('README.txt'));
  assert.equal(parseCsv(files.get('email_list.importer.csv').toString()).length, 2);
  const su2 = await formPost('/signup', { name: 'Second', handle: 'second', password: 'long-enough-pw' });
  const c2 = su2.headers.get('set-cookie').split(';')[0];
  const re = await (await fetch(base + '/desk/import', { method: 'POST', headers: { 'Content-Type': 'application/zip', Cookie: c2 }, body: Buffer.from(await (await fetch(base + '/desk/export.zip', { headers: { Cookie: cookie } })).arrayBuffer()) })).json();
  assert.equal(re.report.posts.published, 1);
  assert.equal(re.report.posts.drafts, 2);
  assert.equal(re.report.subscribers.imported, 2);
});

test('email follow: double opt-in, new-post mail, unsubscribe, no duplicate', async () => {
  const bad = await post('/api/subscribe', { handle: 'june', email: 'nope' });
  assert.equal(bad.status, 400);
  const r = await (await post('/api/subscribe', { handle: 'june', email: 'Reader@Example.org', via: 'mara' })).json();
  assert.equal(r.pending, true);
  assert.match(r.previewLink, /^\/confirm\//);
  const row = app.h.get(`SELECT * FROM email_subs WHERE email = 'reader@example.org'`);
  assert.equal(row.status, 'pending');
  assert.ok(row.via_author_id, 'credited to the recommending writer');
  assert.ok(app.h.get(`SELECT id FROM mail WHERE to_email = 'reader@example.org' AND kind = 'confirm'`));
  const conf = await fetch(base + r.previewLink);
  assert.match(await conf.text(), /on June Hale’s list/);
  assert.equal((await (await post('/api/subscribe', { handle: 'june', email: 'reader@example.org' })).json()).already, true);

  const cookie = await loginAs('june');
  await formPost('/write/new', { title: 'June Writes Again', dek: 'd', body_md: 'A claim.', action: 'publish' }, cookie);
  const mail = app.h.get(`SELECT * FROM mail WHERE to_email = 'reader@example.org' AND kind = 'new-post'`);
  assert.match(mail.subject, /June Writes Again/);
  const unsub = mail.body.match(/\/unsubscribe\/[\w-]+/)[0];
  assert.equal((await fetch(base + unsub)).status, 200);
  assert.equal(app.h.get(`SELECT status FROM email_subs WHERE email = 'reader@example.org'`).status, 'unsubscribed');
  const csv = await (await fetch(base + '/dashboard/list.csv', { headers: { Cookie: cookie } })).text();
  assert.ok(!csv.includes('reader@example.org'), 'unsubscribed addresses leave the list');
});

test('recommendations after a follow, credited in the ledger', async () => {
  const recs = await (await fetch(base + '/api/recs?handle=theo')).json();
  assert.deepEqual(recs.recs.map((x) => x.handle), ['ravi', 'mara']);
  await post('/api/follow', { handle: 'ravi', delta: 1, via: 'theo' });
  const cookie = await loginAs('theo');
  const dash = await (await fetch(base + '/dashboard', { headers: { Cookie: cookie } })).text();
  assert.match(dash, /followers you sent others/);
});

test('note moderation: flags dedupe per visitor, writer can hide and show', async () => {
  const key = (await (await post('/api/key/new', {})).json()).key;
  const n = await (await post('/api/note', { key, slug: 'nobody-owns-the-sidewalk', para: 0, body: 'spammy spam' })).json();
  await post('/api/note/flag', { id: n.note.id });
  await post('/api/note/flag', { id: n.note.id });
  assert.equal(app.h.get('SELECT flags FROM notes WHERE id = ?', n.note.id).flags, 1);
  const cookie = await loginAs('theo');
  const hide = await formPost(`/desk/notes/${n.note.id}/hide`, {}, cookie);
  assert.equal(hide.status, 303);
  assert.ok(!(await (await fetch(base + '/p/nobody-owns-the-sidewalk')).text()).includes('spammy spam'));
  const mara = await loginAs('mara');
  assert.equal((await formPost(`/desk/notes/${n.note.id}/show`, {}, mara)).status, 404, 'only the piece’s writer moderates');
  await formPost(`/desk/notes/${n.note.id}/show`, {}, cookie);
  assert.ok((await (await fetch(base + '/p/nobody-owns-the-sidewalk')).text()).includes('spammy spam'));
});

test('passed-on links preview the passage; brief has RSS', async () => {
  const page = await (await fetch(base + '/p/the-bus-stop-is-the-city?via=passed&p=0')).text();
  assert.match(page, /<meta property="og:title" content="“A city&#39;s real priorities/);
  assert.match(page, /<link rel="canonical" href="http:\/\/127.0.0.1:\d+\/p\/the-bus-stop-is-the-city">/);
  const rss = await fetch(base + '/brief.xml');
  assert.match(rss.headers.get('content-type'), /rss/);
  const items = (await rss.text()).match(/<item>/g) || [];
  assert.ok(items.length >= 1 && items.length <= 5);
});
