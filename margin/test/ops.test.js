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
  try { await fn(app, base); } finally { app.server.close(); app.server.closeAllConnections && app.server.closeAllConnections(); }
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
  app.h.db.close();
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
