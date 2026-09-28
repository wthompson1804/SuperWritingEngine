'use strict';
// Production plumbing: SMTP delivery, the mail queue, backups, pruning,
// password change, health, and the configuration guard.
const test = require('node:test');
const assert = require('node:assert/strict');
const net = require('node:net');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createApp } = require('../server');
const { smtpSend, createMailer } = require('../lib/mailer');
const { open, helpers } = require('../lib/db');
const { prune } = require('../lib/ops');

// Browsers send an Origin header on every POST; the CSRF check relies on it.
// Node's fetch doesn't, so add it here once for every test in this file.
const realFetch = globalThis.fetch;
globalThis.fetch = (url, init = {}) => {
  const method = (init.method || 'GET').toUpperCase();
  const headers = { ...(init.headers || {}) };
  if (method === 'POST' && !('Origin' in headers) && !('origin' in headers)) headers.Origin = new URL(String(url)).origin;
  return realFetch(url, { ...init, headers });
};

// A stand-in SMTP server that records what it receives. It speaks just
// enough of the protocol: EHLO, AUTH PLAIN, MAIL, RCPT, DATA, QUIT.
function fakeSmtp({ failAuth = false } = {}) {
  const got = [];
  const server = net.createServer((sock) => {
    let data = null, msg = { lines: [] };
    sock.write('220 fake ESMTP\r\n');
    sock.on('data', (chunk) => {
      for (const line of chunk.toString().split('\r\n')) {
        if (data) { if (line === '.') { data = false; got.push(msg); sock.write('250 queued\r\n'); } else msg.lines.push(line.replace(/^\.\./, '.')); continue; }
        if (line === '') continue;
        if (/^EHLO/i.test(line)) sock.write('250-fake\r\n250 AUTH PLAIN\r\n');
        else if (/^AUTH PLAIN/i.test(line)) { msg.auth = Buffer.from(line.split(' ')[2], 'base64').toString(); sock.write(failAuth ? '535 nope\r\n' : '235 ok\r\n'); }
        else if (/^MAIL FROM/i.test(line)) { msg.from = line; sock.write('250 ok\r\n'); }
        else if (/^RCPT TO/i.test(line)) { msg.to = line; sock.write('250 ok\r\n'); }
        else if (/^DATA/i.test(line)) { data = true; sock.write('354 go\r\n'); }
        else if (/^QUIT/i.test(line)) { sock.write('221 bye\r\n'); sock.end(); }
        else sock.write('500 what\r\n');
      }
    });
  });
  return new Promise((r) => server.listen(0, '127.0.0.1', () => r({ server, port: server.address().port, got })));
}

test('smtp client sends a message with auth, dot-stuffing and UTF-8 subject', async () => {
  const s = await fakeSmtp();
  await smtpSend({ host: '127.0.0.1', port: s.port, secure: false, starttls: false, user: 'u', pass: 'p' },
    { from: 'Margin <hello@margin.test>', to: 'r@example.org', subject: 'Confirm: Café', text: 'Line one\n.starts with a dot\nEnd', messageId: 'x@margin.test' });
  assert.equal(s.got.length, 1);
  const m = s.got[0];
  assert.equal(m.auth, '\0u\0p');
  assert.equal(m.from, 'MAIL FROM:<hello@margin.test>');
  assert.equal(m.to, 'RCPT TO:<r@example.org>');
  assert.ok(m.lines.includes('Subject: =?UTF-8?B?Q29uZmlybTogQ2Fmw6k=?='));
  assert.ok(m.lines.includes('.starts with a dot'), 'dot-stuffing undone by the server');
  assert.ok(m.lines.some((l) => /^Message-ID: <x@margin.test>/.test(l)));
  s.server.close();
});

test('smtp failures are reported, not swallowed', async () => {
  const s = await fakeSmtp({ failAuth: true });
  await assert.rejects(smtpSend({ host: '127.0.0.1', port: s.port, secure: false, starttls: false, user: 'u', pass: 'bad' },
    { from: 'a@b.c', to: 'd@e.f', subject: 's', text: 't', messageId: 'm@x' }), /SMTP 535/);
  s.server.close();
});

test('mail queue: sends, retries with backoff, gives up after 5, never double-sends', async () => {
  const h = helpers(open(':memory:'));
  let calls = 0, failUntil = 2;
  const mailer = createMailer(h, { from: 'a@b.c', send: async () => { calls++; if (calls <= failUntil) throw new Error('boom'); } });
  h.run(`INSERT INTO mail (to_email, subject, body, kind, created_at, next_at) VALUES ('x@y.z','s','b','t',?,?)`, Date.now(), Date.now());
  assert.equal(await mailer.drain(), 0);
  let row = h.get('SELECT * FROM mail');
  assert.equal(row.status, 'pending'); assert.equal(row.attempts, 1); assert.ok(row.next_at > Date.now() + 60000);
  h.run('UPDATE mail SET next_at = 0');
  await mailer.drain();
  h.run('UPDATE mail SET next_at = 0');
  assert.equal(await mailer.drain(), 1);
  row = h.get('SELECT * FROM mail');
  assert.equal(row.status, 'sent'); assert.equal(row.attempts, 3);
  assert.equal(await mailer.drain(), 0, 'sent mail is not sent again');
  failUntil = 99;
  h.run(`INSERT INTO mail (to_email, subject, body, kind, created_at, next_at) VALUES ('q@y.z','s','b','t',?,0)`, Date.now());
  for (let i = 0; i < 6; i++) { h.run(`UPDATE mail SET next_at = 0 WHERE to_email = 'q@y.z'`); await mailer.drain(); }
  assert.equal(h.get(`SELECT status, attempts FROM mail WHERE to_email = 'q@y.z'`).status, 'failed');
});

// Servers are closed in a finally, so a failing assertion can't hang the run.
async function withApp(opts, fn) {
  const app = createApp({ dbFile: ':memory:', demoSignals: false, ...opts });
  await new Promise((r) => app.server.listen(0, r));
  const base = `http://127.0.0.1:${app.server.address().port}`;
  try { await fn(app, base); } finally { app.close(); }
}

test('app with a mail sender delivers confirmations and hides the on-screen link', async () => {
  const sent = [];
  await withApp({ sendMail: async (m) => { sent.push(m); }, mailFrom: 'Margin <m@x.test>' }, async (app, base) => {
  const r = await (await fetch(base + '/api/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ handle: 'mara', email: 'real@example.org' }) })).json();
  assert.equal(r.previewLink, undefined, 'no on-screen confirm link once mail is real');
  await new Promise((r) => setTimeout(r, 50));
  await app.mailer.drain();
  assert.equal(sent.length, 1);
  assert.match(sent[0].subject, /Confirm/);
  assert.match(sent[0].text, /\/confirm\//);
  });
});

test('backup writes a readable copy and prune trims old rows', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'margin-ops-'));
  const app = createApp({ dbFile: path.join(dir, 'm.db'), demoSignals: true });
  const file = await app.backup();
  assert.ok(fs.existsSync(file));
  const copy = helpers(open(file));
  assert.equal(copy.get('SELECT count(*) n FROM authors').n, app.h.get('SELECT count(*) n FROM authors').n);
  copy.db.close();
  const old = Date.now() - 100 * 86400000;
  app.h.run(`INSERT INTO views (pv, post_id, created_at) VALUES ('old-view', 1, ?)`, old);
  app.h.run(`INSERT INTO mail (to_email, subject, body, kind, created_at, status) VALUES ('a@b.c','s','b','t',?, 'sent')`, old);
  const out = app.prune();
  assert.equal(out.views, 1); assert.equal(out.mail, 1);
  assert.equal(app.h.get(`SELECT count(*) n FROM views WHERE pv = 'old-view'`).n, 0);
  app.close();
  fs.rmSync(dir, { recursive: true, force: true });
});

test('password change requires the current one and signs other sessions out', async () => {
  await withApp({}, async (app, base) => {
  const form = (p, obj, cookie) => fetch(base + p, { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded', ...(cookie ? { Cookie: cookie } : {}) }, body: new URLSearchParams(obj) });
  const login = async () => (await form('/login', { handle: 'theo', password: 'demo-password' })).headers.get('set-cookie').split(';')[0];
  const a = await login(), b = await login();
  assert.equal((await form('/desk/password', { current: 'wrong', next: 'a-brand-new-password' }, a)).status, 401);
  const ok = await form('/desk/password', { current: 'demo-password', next: 'a-brand-new-password' }, a);
  assert.equal(ok.status, 303);
  const fresh = ok.headers.get('set-cookie').split(';')[0];
  assert.equal((await fetch(base + '/dashboard', { redirect: 'manual', headers: { Cookie: b } })).status, 303, 'other session signed out');
  assert.equal((await fetch(base + '/dashboard', { redirect: 'manual', headers: { Cookie: a } })).status, 303, 'old cookie of this browser is dead too');
  assert.equal((await fetch(base + '/dashboard', { redirect: 'manual', headers: { Cookie: fresh } })).status, 200, 'the new session works');
  assert.equal((await form('/login', { handle: 'theo', password: 'demo-password' })).status, 401);
  assert.equal((await form('/login', { handle: 'theo', password: 'a-brand-new-password' })).status, 303);
  });
});

test('health endpoint and security headers', async () => {
  await withApp({}, async (app, base) => {
  const hz = await fetch(base + '/healthz');
  assert.equal(hz.status, 200);
  assert.deepEqual(await hz.json(), { ok: true });
  const home = await fetch(base + '/');
  assert.equal(home.headers.get('x-frame-options'), 'DENY');
  assert.match(home.headers.get('permissions-policy'), /camera=\(\)/);
  assert.equal(home.headers.get('strict-transport-security'), null, 'no HSTS without https public URL');
  });
});

test('production configuration guard', async () => {
  assert.throws(() => createApp({ dbFile: ':memory:', publicUrl: 'https://margin.example', apInsecure: true }), /MARGIN_AP_INSECURE/);
  await withApp({ publicUrl: 'https://margin.example', demoSignals: true }, async (app, base) => {
  assert.equal(app.h.get('SELECT count(*) n FROM views').n, 0, 'no synthetic signals on a public site');
  const r = await fetch(base + '/');
  assert.match(r.headers.get('strict-transport-security'), /max-age=31536000/);
  const login = await fetch(base + '/login', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded', Origin: 'https://margin.example' }, body: 'handle=mara&password=demo-password' });
  assert.match(login.headers.get('set-cookie'), /; Secure/);
  const sub = await (await fetch(base + '/api/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ handle: 'mara', email: 'p@example.org' }) })).json();
  assert.equal(sub.previewLink, undefined, 'no on-screen confirm link in production');
  const mail = app.h.get(`SELECT body FROM mail WHERE to_email = 'p@example.org'`);
  assert.match(mail.body, /https:\/\/margin\.example\/confirm\//);
  });
});

// ---------------- second security review: regressions ----------------
test('a trusted proxy uses the last X-Forwarded-For hop; clients cannot pick their own address', async () => {
  await withApp({ trustProxy: true, demoSignals: true }, async (app, base) => {
    // 30 forged addresses, one real hop appended by "the proxy": all one bucket.
    let last;
    for (let i = 0; i < 25; i++) {
      last = await fetch(base + '/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Forwarded-For': `1.2.3.${i}, 203.0.113.9` }, body: 'handle=x&password=y' });
    }
    assert.equal(last.status, 429, 'rate limit keyed on the proxy-appended hop');
    // Garbage in the header falls back to the socket address rather than a free key.
    const junk = await fetch(base + '/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'X-Forwarded-For': 'not-an-ip' }, body: 'handle=x&password=y' });
    assert.ok([401, 429].includes(junk.status));
  });
});

test('confirmation mail cannot be used to flood an address', async () => {
  await withApp({}, async (app, base) => {
    for (let i = 0; i < 6; i++) await fetch(base + '/api/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ handle: 'mara', email: 'victim@example.org' }) });
    assert.equal(app.h.get(`SELECT count(*) n FROM mail WHERE to_email = 'victim@example.org'`).n, 1);
  });
});

test('an unverified reader-key email never reaches a writer’s list or the digest', async () => {
  await withApp({}, async (app, base) => {
    const j = (p, b) => fetch(base + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }).then((r) => r.json());
    const { key } = await j('/api/key/new', { data: { follows: { mara: { on: true, ts: 1 } } } });
    await j('/api/key/sync', { key, data: { follows: { mara: { on: true, ts: 2 } } } });
    await j('/api/key/prefs', { key, email: 'ceo@bigcorp.example', share_email: true, digest: true });
    const login = await fetch(base + '/login', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'handle=mara&password=demo-password' });
    const cookie = login.headers.get('set-cookie').split(';')[0];
    const csv = await (await fetch(base + '/dashboard/list.csv', { headers: { Cookie: cookie } })).text();
    assert.ok(!csv.includes('ceo@bigcorp.example'), 'unverified address is not in the export');
    assert.equal(app.h.get(`SELECT digest FROM readers WHERE email = 'ceo@bigcorp.example'`).digest, 0);
  });
});

test('one unresponsive fediverse inbox does not block deliveries to others', async () => {
  const net = require('node:net');
  const { createFederation } = require('../lib/activitypub');
  // A server that accepts connections and never replies.
  const tarpit = net.createServer(() => {});
  await new Promise((r) => tarpit.listen(0, '127.0.0.1', r));
  const hits = [];
  const good = require('node:http').createServer((req, res) => { hits.push(req.url); res.writeHead(202); res.end(); });
  await new Promise((r) => good.listen(0, '127.0.0.1', r));
  const h = helpers(open(':memory:'));
  require('../lib/seed').seed(h, { demoSignals: false });
  const fed = createFederation(h, { allowHttp: true, allowPrivate: true });
  const author = h.get('SELECT * FROM authors WHERE handle = ?', 'theo');
  const post = h.get('SELECT * FROM posts WHERE author_id = ? LIMIT 1', author.id);
  h.run('INSERT INTO ap_followers (author_id, actor, inbox, created_at) VALUES (?,?,?,?)', author.id, 'http://tarpit.test/u/a', `http://127.0.0.1:${tarpit.address().port}/inbox`, 1);
  h.run('INSERT INTO ap_followers (author_id, actor, inbox, created_at) VALUES (?,?,?,?)', author.id, 'http://good.test/u/b', `http://localhost:${good.address().port}/inbox`, 1);
  fed.publish('http://margin.test', author, post);
  const t = Date.now();
  while (!hits.length && Date.now() - t < 5000) await new Promise((r) => setTimeout(r, 50));
  assert.equal(hits.length, 1, 'the healthy inbox was reached while the tarpit was still hanging');
  assert.ok(Date.now() - t < 5000);
  tarpit.close(); good.close();
});

test('a signed-in browser that sends no origin information is refused', async () => {
  await withApp({}, async (app, base) => {
    const login = await fetch(base + '/login', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'handle=mara&password=demo-password' });
    const cookie = login.headers.get('set-cookie').split(';')[0];
    const bare = await realFetch(base + '/desk/profile', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded', Cookie: cookie }, body: 'name=pwned&accent=cobalt' });
    assert.equal(bare.status, 403);
    assert.equal(app.h.get(`SELECT name FROM authors WHERE handle = 'mara'`).name, 'Mara Okafor');
  });
});

test('control characters never reach the feeds; session tokens are stored hashed', async () => {
  await withApp({}, async (app, base) => {
    const login = await fetch(base + '/login', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'handle=theo&password=demo-password' });
    const cookie = login.headers.get('set-cookie').split(';')[0];
    const token = cookie.split('=')[1];
    assert.equal(app.h.get('SELECT count(*) n FROM sessions WHERE token = ?', token).n, 0, 'raw token is not in the database');
    assert.equal(app.h.get('SELECT count(*) n FROM sessions').n, 1);
    await fetch(base + '/write/new', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded', Cookie: cookie }, body: new URLSearchParams({ title: 'Bell \x07 title', dek: 'x\x01y', body_md: 'Body.', action: 'publish' }) });
    const xml = await (await fetch(base + '/feed.xml?author=theo')).text();
    assert.ok(!/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(xml), 'feed is well-formed');
    assert.match(xml, /Bell {2}title|Bell  title/);
  });
});

test('deeply nested or oversized sync payloads are flattened, not crashed on', async () => {
  await withApp({}, async (app, base) => {
    const j = (p, b) => fetch(base + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
    const { key } = await (await j('/api/key/new', {})).json();
    // Built as text: 100k nested arrays is more than JSON.stringify can take on
    // the client side, which is the point of sending it raw.
    const deep = '['.repeat(100000) + '"x"' + ']'.repeat(100000);
    const raw = `{"key":${JSON.stringify(key)},"data":{"kept":{"a":{"ts":1,"deep":${deep}},"b":{"ts":2,"text":"fine"}}}}`;
    const r = await fetch(base + '/api/key/sync', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: raw });
    assert.equal(r.status, 200);
    const d = (await r.json()).data;
    assert.equal(d.kept.a.deep, undefined, 'non-scalar fields dropped');
    assert.equal(d.kept.b.text, 'fine');
    const many = {}; for (let i = 0; i < 700; i++) many['h' + i] = { on: true, ts: i };
    const big = await (await j('/api/key/sync', { key, data: { follows: many } })).json();
    assert.equal(Object.keys(big.data.follows).length, 500, 'follows capped at 500, newest kept');
  });
});

// ---------------- third security review: regressions ----------------
// A fake server that can advertise STARTTLS. It records every command so a
// test can prove credentials never went over the wire in the clear.
function fakeSmtpStarttls({ offer }) {
  const lines = [];
  const server = net.createServer((sock) => {
    sock.write('220 fake ESMTP\r\n');
    sock.on('data', (chunk) => {
      if (sock.writableEnded) return; // the client's TLS hello after we hung up
      for (const line of chunk.toString().split('\r\n')) {
        if (line === '') continue;
        lines.push(line);
        if (/^EHLO/i.test(line)) sock.write(offer ? '250-fake\r\n250-STARTTLS\r\n250 AUTH PLAIN\r\n' : '250-fake\r\n250 AUTH PLAIN\r\n');
        else if (/^STARTTLS/i.test(line)) { sock.write('220 go ahead\r\n'); sock.end(); } // no cert here: the handshake is not the point
        else sock.write('250 ok\r\n');
      }
    });
  });
  return new Promise((r) => server.listen(0, '127.0.0.1', () => r({ server, port: server.address().port, lines })));
}

test('smtp client issues STARTTLS when offered and refuses to send credentials without it', async () => {
  const msg = { from: 'a@b.c', to: 'd@e.f', subject: 's', text: 't', messageId: 'm@x' };
  const offered = await fakeSmtpStarttls({ offer: true });
  await assert.rejects(smtpSend({ host: '127.0.0.1', port: offered.port, secure: false, starttls: true, user: 'u', pass: 'p' }, msg));
  assert.ok(offered.lines.some((l) => /^STARTTLS$/i.test(l)), 'STARTTLS was sent');
  assert.ok(!offered.lines.some((l) => /^AUTH/i.test(l)), 'no AUTH on the plaintext socket');
  offered.server.close();
  const bare = await fakeSmtpStarttls({ offer: false });
  await assert.rejects(smtpSend({ host: '127.0.0.1', port: bare.port, secure: false, starttls: true, user: 'u', pass: 'p' }, msg), /did not offer STARTTLS/);
  assert.ok(!bare.lines.some((l) => /^AUTH/i.test(l)), 'credentials withheld when the server has no TLS');
  bare.server.close();
});

test('mail rows left claimed by a crash are re-queued at startup', () => {
  const h = helpers(open(':memory:'));
  h.run(`INSERT INTO mail (to_email, subject, body, kind, created_at, next_at, status) VALUES ('x@y.z','s','b','t',?,0,'sending')`, Date.now());
  createMailer(h, { from: 'a@b.c', send: async () => {} });
  assert.equal(h.get('SELECT status FROM mail').status, 'pending');
});

test('followers are pruned only after a month of nothing but failures', () => {
  const h = helpers(open(':memory:'));
  require('../lib/seed').seed(h, { demoSignals: false });
  const author = h.get('SELECT id FROM authors LIMIT 1').id;
  const now = Date.now(), day = 86400000;
  const follower = (n, inbox) => h.run('INSERT INTO ap_followers (author_id, actor, inbox, created_at) VALUES (?,?,?,?)', author, `https://${n}/u/a`, inbox, now);
  const delivery = (inbox, status, at) => h.run('INSERT INTO ap_deliveries (author_id, inbox, body, next_at, status, created_at) VALUES (?,?,?,?,?,?)', author, inbox, '{}', at, status, at);
  follower('once.test', 'https://once.test/inbox'); delivery('https://once.test/inbox', 'failed', now - day);
  follower('mixed.test', 'https://mixed.test/inbox'); delivery('https://mixed.test/inbox', 'failed', now - 40 * day); delivery('https://mixed.test/inbox', 'done', now - 2 * day);
  follower('dead.test', 'https://dead.test/inbox'); delivery('https://dead.test/inbox', 'failed', now - 40 * day); delivery('https://dead.test/inbox', 'failed', now - 5 * day);
  const out = prune(h, now);
  assert.equal(out.followers, 1);
  assert.deepEqual(h.all('SELECT inbox FROM ap_followers ORDER BY inbox').map((r) => r.inbox), ['https://mixed.test/inbox', 'https://once.test/inbox']);
});

test('a Follow whose inbox is on another host is refused', () => {
  const { createFederation } = require('../lib/activitypub');
  const h = helpers(open(':memory:'));
  require('../lib/seed').seed(h, { demoSignals: false });
  const fed = createFederation(h, { allowHttp: true, allowPrivate: true });
  const follow = { type: 'Follow', actor: 'https://social.example/users/eve', object: 'http://margin.test/ap/users/theo' };
  const signer = { id: 'https://social.example/users/eve', inbox: 'https://social.example/users/eve/inbox', endpoints: { sharedInbox: 'https://victim.example/inbox' } };
  assert.equal(fed.receive('http://margin.test', follow, signer), 'bad-inbox');
  assert.equal(h.get('SELECT count(*) n FROM ap_followers').n, 0);
  assert.equal(h.get('SELECT count(*) n FROM ap_deliveries').n, 0, 'no signed Accept queued for the foreign host');
  assert.equal(fed.receive('http://margin.test', follow, { ...signer, endpoints: { sharedInbox: 'https://social.example/inbox' } }), 'followed');
  fed.stop();
});

test('reader-key email: verify link expires by send time, clearing the address forgets it, choices apply once verified', async () => {
  await withApp({}, async (app, base) => {
    const j = (p, b) => fetch(base + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }).then((r) => r.json());
    const { key } = await j('/api/key/new', {});
    const first = await j('/api/key/prefs', { key, email: 'r@example.org', digest: true });
    assert.ok(first.pending);
    const token = app.h.get(`SELECT verify_token FROM readers WHERE email = 'r@example.org'`).verify_token;
    // Keeping the key in use (updated_at bumps) must not extend the link's life.
    app.h.run(`UPDATE readers SET verify_sent_at = ?, updated_at = ? WHERE email = 'r@example.org'`, Date.now() - 8 * 86400000, Date.now());
    assert.equal((await fetch(base + '/verify/' + token)).status, 410);
    app.h.run(`UPDATE readers SET verify_sent_at = ? WHERE email = 'r@example.org'`, Date.now());
    assert.equal((await fetch(base + '/verify/' + token)).status, 200);
    let row = app.h.get(`SELECT * FROM readers WHERE email = 'r@example.org'`);
    assert.ok(row.email_verified_at); assert.equal(row.digest, 1, 'the wish recorded before verification is applied');
    // Same address, new choices: applied immediately because it is verified.
    const upd = await j('/api/key/prefs', { key, email: 'r@example.org', digest: false, share_email: true });
    assert.deepEqual([upd.prefs.digest, upd.prefs.share_email, upd.prefs.verified], [false, true, true]);
    row = app.h.get(`SELECT * FROM readers WHERE email = 'r@example.org'`);
    assert.deepEqual([row.want_digest, row.want_share], [0, 1]);
    // Clearing the address forgets everything, including the verification.
    const cleared = await j('/api/key/prefs', { key, email: '' });
    assert.deepEqual(cleared.prefs, { email: '', digest: false, share_email: false, verified: false, wantDigest: false, wantShare: false });
    assert.equal(app.h.get('SELECT count(*) n FROM readers WHERE email IS NOT NULL').n, 0);
    // Re-adding the same address starts over as unverified.
    const again = await j('/api/key/prefs', { key, email: 'r@example.org' });
    assert.ok(again.pending); assert.equal(again.prefs.verified, false);
  });
});

test('backups are private to the service user', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'margin-ops-'));
  const app = createApp({ dbFile: path.join(dir, 'm.db'), demoSignals: false });
  const file = await app.backup();
  assert.equal(fs.statSync(file).mode & 0o777, 0o600);
  assert.equal(fs.statSync(path.dirname(file)).mode & 0o777, 0o700);
  app.close();
  fs.rmSync(dir, { recursive: true, force: true });
});

test('the site cannot be turned into a spam cannon', async () => {
  await withApp({}, async (app, base) => {
    const sub = (handle, email) => fetch(base + '/api/subscribe', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ handle, email }) });
    const mailTo = (e) => app.h.get('SELECT count(*) n FROM mail WHERE to_email = ?', e).n;
    // Addresses with routing tricks are refused outright, not normalised away.
    for (const bad of ['x<victim@example.org>y', 'victim@example.org,other@example.org', 'a b@example.org', 'victim@localhost', '"quoted"@example.org']) {
      assert.equal((await sub('mara', bad)).status, 400, bad);
    }
    const j = (p, b) => fetch(base + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }).then((r) => r.json());
    const { key } = await j('/api/key/new', {});
    assert.equal((await j('/api/key/prefs', { key, email: 'x<victim@example.org>y' })).ok, false);
    // Case variants are one address.
    await sub('mara', 'Victim@Example.org');
    assert.equal(app.h.get(`SELECT count(*) n FROM email_subs WHERE email = 'victim@example.org'`).n, 1);
    // One address, every writer: at most three confirmation mails an hour in total.
    for (const w of ['theo', 'june', 'ravi']) await sub(w, 'victim@example.org');
    assert.equal(mailTo('victim@example.org'), 3);
    assert.equal(app.h.get(`SELECT count(*) n FROM email_subs WHERE email = 'victim@example.org' AND status = 'pending'`).n, 4, 'sign-ups still recorded; only the mail is held');
    // One client, many addresses: capped per hour.
    let last;
    for (let i = 0; i < 25; i++) last = await sub('mara', `r${i}@example.org`);
    assert.equal(last.status, 429);
  });
});

test('malformed sync entries and out-of-range note paragraphs are handled, not crashed on', async () => {
  await withApp({}, async (app, base) => {
    const j = (p, b) => fetch(base + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
    const { key } = await (await j('/api/key/new', {})).json();
    const r = await j('/api/key/sync', { key, data: { follows: { theo: null, mara: 'yes', june: { on: true, ts: 1 } } } });
    assert.equal(r.status, 200);
    assert.equal(app.h.get('SELECT count(*) n FROM reader_follows').n, 1, 'only the well-formed follow is recorded');
    const slug = app.h.get(`SELECT slug FROM posts WHERE status = 'published' LIMIT 1`).slug;
    assert.equal((await j('/api/note', { key, slug, para: 1e300, body: 'hello' })).status, 400);
    assert.equal((await j('/api/note', { key, slug, para: 1, body: 'hello' })).status, 200);
  });
});

// ---------- exhaustion review: regressions ----------
const png = (n) => Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), Buffer.from(`image number ${n}`)]);
const loginMara = async (base) => (await fetch(base + '/login', { method: 'POST', redirect: 'manual', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'handle=mara&password=demo-password' })).headers.get('set-cookie').split(';')[0];

test('a writer cannot fill the disk: media quota, uploads outside it refused', async () => {
  await withApp({ mediaQuota: { files: 3 } }, async (app, base) => {
    const cookie = await loginMara(base);
    const up = (buf) => fetch(base + '/desk/upload', { method: 'POST', headers: { 'Content-Type': 'image/png', Cookie: cookie }, body: buf });
    for (let i = 0; i < 3; i++) assert.equal((await up(png(i))).status, 200);
    const full = await up(png(99));
    assert.equal(full.status, 413);
    assert.match((await full.json()).error, /image space is full/);
    assert.equal((await up(png(1))).status, 200, 'an image already stored is always fine');
    assert.equal(app.h.get(`SELECT count(*) n FROM media`).n, 3);
  });
});

test('keeps, follows, asks and tips are rate-limited per address so ranking cannot be bought', async () => {
  await withApp({}, async (app, base) => {
    const j = (p, b) => fetch(base + p, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) });
    const slug = app.h.get(`SELECT slug FROM posts WHERE status = 'published' LIMIT 1`).slug;
    for (let i = 0; i < 30; i++) await j('/api/keep', { slug, para: i % 5, pv: require('node:crypto').randomUUID() });
    assert.equal(app.h.get('SELECT count(*) n FROM keeps').n, 10);
    for (let i = 0; i < 30; i++) await j('/api/follow', { handle: 'theo', delta: 1 });
    assert.equal(app.h.get('SELECT count(*) n FROM follow_events').n, 10);
    let last;
    for (let i = 0; i < 8; i++) last = await j('/api/tip', { slug, cents: 50000 });
    assert.equal(last.status, 429);
    assert.equal(app.h.get('SELECT count(*) n FROM tips').n, 5);
    // A JSON body that is not an object is a 400, not a crash.
    for (const body of ['null', '5', '[1]', '"x"']) {
      const r = await fetch(base + '/api/read', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
      assert.equal(r.status, 400, body);
    }
  });
});

test('import of thousands of colliding slugs stays linear and is capped', async () => {
  const { writeZip } = require('../lib/zip');
  await withApp({}, async (app, base) => {
    const cookie = await loginMara(base);
    const rows = ['post_id,post_date,is_published,type,title,subtitle,audience'];
    const files = [];
    for (let i = 1; i <= 2500; i++) { rows.push(`${i}.same-title,2024-01-01T00:00:00Z,true,newsletter,Same title,,everyone`); files.push([`posts/${i}.same-title.html`, Buffer.from(`<p>Body ${i}</p>`)]); }
    files.push(['posts.csv', Buffer.from(rows.join('\n') + '\n')]);
    const t = Date.now();
    const r = await (await fetch(base + '/desk/import', { method: 'POST', headers: { 'Content-Type': 'application/zip', Cookie: cookie }, body: writeZip(files) })).json();
    const ms = Date.now() - t;
    assert.equal(r.ok, true);
    assert.equal(r.report.posts.published, 2000, 'capped at 2000 per run');
    assert.equal(r.report.capped, 2000);
    assert.ok(ms < 4000, `import took ${ms} ms`);
    assert.equal(app.h.get(`SELECT count(DISTINCT slug) n FROM posts WHERE slug LIKE 'same-title%'`).n, 2000);
  });
});

test('health checks readiness; mail that could not be sent for a week is dropped', async () => {
  await withApp({}, async (app, base) => {
    assert.equal((await fetch(base + '/healthz')).status, 200);
    const old = Date.now() - 8 * 86400000;
    app.h.run(`INSERT INTO mail (to_email, subject, body, kind, created_at, next_at) VALUES ('a@b.co','s','b','confirm',?,0)`, old);
    app.h.run(`INSERT INTO mail (to_email, subject, body, kind, created_at, next_at) VALUES ('c@d.co','s','b','confirm',?,0)`, Date.now());
    assert.equal(app.prune().unsent, 1);
    app.h.run(`INSERT INTO mail (to_email, subject, body, kind, created_at, next_at) VALUES ('e@f.co','s','b','confirm',?,0)`, old);
    const sent = [];
    createMailer(app.h, { from: 'x@y.co', send: async (m) => sent.push(m) });
    assert.equal(app.h.get(`SELECT status FROM mail WHERE to_email = 'e@f.co'`).status, 'failed', 'a stale row is not sent when delivery is switched on');
  });
});
