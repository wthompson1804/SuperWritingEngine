'use strict';
// Federation tests against a stand-in Mastodon: a local server with its own
// RSA key that signs its requests and verifies Margin's signatures.
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const crypto = require('node:crypto');
const { createApp } = require('../server');
const { signHeaders, digestOf, allowedUrl } = require('../lib/activitypub');

let app, base, remote, remoteBase;
const received = [];
const keys = crypto.generateKeyPairSync('rsa', { modulusLength: 2048, publicKeyEncoding: { type: 'spki', format: 'pem' }, privateKeyEncoding: { type: 'pkcs8', format: 'pem' } });

function verifyIncoming(req, body, pem) {
  const sig = Object.fromEntries([...req.headers.signature.matchAll(/(\w+)="([^"]*)"/g)].map((m) => [m[1], m[2]]));
  const str = sig.headers.split(' ').map((n) => (n === '(request-target)' ? `(request-target): ${req.method.toLowerCase()} ${req.url}` : `${n}: ${req.headers[n]}`)).join('\n');
  return { ok: crypto.verify('sha256', Buffer.from(str), pem, Buffer.from(sig.signature, 'base64')), keyId: sig.keyId, digestOk: !body || req.headers.digest === digestOf(body) };
}

test.before(async () => {
  app = createApp({ dbFile: ':memory:', demoSignals: false, apInsecure: true });
  await new Promise((r) => app.server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${app.server.address().port}`;
  remote = http.createServer(async (req, res) => {
    const chunks = []; for await (const c of req) chunks.push(c);
    const body = Buffer.concat(chunks).toString();
    if (req.method === 'GET' && req.url === '/users/alice') {
      res.writeHead(200, { 'content-type': 'application/activity+json' });
      return res.end(JSON.stringify({ id: `${remoteBase}/users/alice`, type: 'Person', preferredUsername: 'alice', inbox: `${remoteBase}/users/alice/inbox`, endpoints: { sharedInbox: `${remoteBase}/inbox` }, publicKey: { id: `${remoteBase}/users/alice#main-key`, owner: `${remoteBase}/users/alice`, publicKeyPem: keys.publicKey } }));
    }
    if (req.method === 'POST') {
      // Verify Margin's signature the way Mastodon does: fetch the key, check it.
      const keyId = /keyId="([^"]+)"/.exec(req.headers.signature || '')[1];
      const actor = await (await fetch(keyId.split('#')[0], { headers: { accept: 'application/activity+json' } })).json();
      received.push({ url: req.url, activity: JSON.parse(body), check: verifyIncoming(req, body, actor.publicKey.publicKeyPem) });
      res.writeHead(202); return res.end();
    }
    res.writeHead(404); res.end();
  });
  await new Promise((r) => remote.listen(0, '127.0.0.1', r));
  remoteBase = `http://127.0.0.1:${remote.address().port}`;
});
test.after(() => { app.server.close(); remote.close(); });

async function signedPost(path, activity, { tamper = false, keyId } = {}) {
  const body = JSON.stringify(activity);
  const url = base + path;
  const headers = signHeaders({ method: 'POST', url, body, keyId: keyId || `${remoteBase}/users/alice#main-key`, privateKey: keys.privateKey });
  return fetch(url, { method: 'POST', headers: { ...headers, 'content-type': 'application/activity+json' }, body: tamper ? body.replace('Follow', 'Folloq') : body });
}
const waitFor = async (fn, ms = 5000) => { const end = Date.now() + ms; while (Date.now() < end) { const v = fn(); if (v) return v; await new Promise((r) => setTimeout(r, 50)); } return fn(); };

test('webfinger, actor, outbox and content negotiation', async () => {
  const host = new URL(base).host;
  const wf = await fetch(`${base}/.well-known/webfinger?resource=acct:theo@${host}`);
  assert.equal(wf.status, 200);
  const doc = await wf.json();
  const self = doc.links.find((l) => l.rel === 'self');
  assert.equal(self.href, `${base}/ap/users/theo`);
  assert.equal((await fetch(`${base}/.well-known/webfinger?resource=acct:theo@elsewhere.example`)).status, 404);

  const actor = await (await fetch(self.href)).json();
  assert.equal(actor.type, 'Person');
  assert.match(actor.publicKey.publicKeyPem, /BEGIN PUBLIC KEY/);
  assert.equal(actor.inbox, `${base}/ap/users/theo/inbox`);
  const again = await (await fetch(self.href)).json();
  assert.equal(again.publicKey.publicKeyPem, actor.publicKey.publicKeyPem, 'keys are stable');

  const out = await (await fetch(actor.outbox)).json();
  assert.equal(out.type, 'OrderedCollection');
  assert.equal(out.orderedItems[0].type, 'Create');
  assert.equal(out.orderedItems[0].object.type, 'Article');

  const neg = await fetch(`${base}/@theo`, { headers: { accept: 'application/activity+json' } });
  assert.match(neg.headers.get('content-type'), /activity\+json/);
  const art = await (await fetch(`${base}/p/the-bus-stop-is-the-city`, { headers: { accept: 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"' } })).json();
  assert.equal(art.type, 'Article');
  assert.equal(art.url, `${base}/p/the-bus-stop-is-the-city`);
  assert.match((await fetch(`${base}/@theo`)).headers.get('content-type'), /text\/html/, 'browsers still get HTML');
});

test('signed Follow is accepted and answered with a signed Accept', async () => {
  const follow = { '@context': 'https://www.w3.org/ns/activitystreams', id: `${remoteBase}/follows/1`, type: 'Follow', actor: `${remoteBase}/users/alice`, object: `${base}/ap/users/theo` };
  const r = await signedPost('/ap/users/theo/inbox', follow);
  assert.equal(r.status, 202);
  assert.equal((await r.json()).result, 'followed');
  const accept = await waitFor(() => received.find((x) => x.activity.type === 'Accept'));
  assert.ok(accept, 'Accept delivered');
  assert.equal(accept.url, '/users/alice/inbox');
  assert.equal(accept.activity.object.id, follow.id);
  assert.ok(accept.check.ok, 'Accept signature verifies against Margin’s published key');
  assert.ok(accept.check.digestOk);
  assert.equal(app.h.get('SELECT count(*) n FROM ap_followers').n, 1);
  assert.equal((await (await fetch(`${base}/ap/users/theo/followers`)).json()).totalItems, 1);
});

test('publishing delivers a signed Create(Article) to followers', async () => {
  const login = await fetch(base + '/login', { method: 'POST', redirect: 'manual', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ handle: 'theo', password: 'demo-password' }) });
  const cookie = login.headers.get('set-cookie').split(';')[0];
  await fetch(base + '/write/new', { method: 'POST', redirect: 'manual', headers: { 'content-type': 'application/x-www-form-urlencoded', cookie }, body: new URLSearchParams({ title: 'Federated Piece', dek: 'Out to the fediverse', body_md: 'The claim travels.', action: 'publish' }) });
  const create = await waitFor(() => received.find((x) => x.activity.type === 'Create'));
  assert.ok(create);
  assert.equal(create.url, '/inbox', 'shared inbox preferred');
  assert.equal(create.activity.object.name, 'Federated Piece');
  assert.ok(create.check.ok);
});

test('bad, missing or mismatched signatures are rejected', async () => {
  const follow = { id: `${remoteBase}/follows/2`, type: 'Follow', actor: `${remoteBase}/users/alice`, object: `${base}/ap/users/mara` };
  assert.equal((await signedPost('/ap/users/mara/inbox', follow, { tamper: true })).status, 401, 'digest mismatch');
  const unsigned = await fetch(base + '/ap/users/mara/inbox', { method: 'POST', headers: { 'content-type': 'application/activity+json' }, body: JSON.stringify(follow) });
  assert.equal(unsigned.status, 401);
  const spoof = { ...follow, actor: 'http://127.0.0.1:1/users/mallory' };
  assert.equal((await signedPost('/ap/users/mara/inbox', spoof)).status, 401, 'actor must match the signing key');
  assert.equal(app.h.get('SELECT count(*) n FROM ap_followers WHERE author_id = (SELECT id FROM authors WHERE handle = ?)', 'mara').n, 0);
});

test('Undo(Follow) removes the follower', async () => {
  const undo = { id: `${remoteBase}/undo/1`, type: 'Undo', actor: `${remoteBase}/users/alice`, object: { id: `${remoteBase}/follows/1`, type: 'Follow', actor: `${remoteBase}/users/alice`, object: `${base}/ap/users/theo` } };
  const r = await signedPost('/ap/inbox', undo);
  assert.equal(r.status, 202);
  assert.equal(app.h.get('SELECT count(*) n FROM ap_followers').n, 0);
});

test('outbound URL guard blocks private and non-https targets by default', () => {
  assert.equal(allowedUrl('http://example.com/x'), null);
  assert.equal(allowedUrl('https://127.0.0.1/x'), null);
  assert.equal(allowedUrl('https://10.0.0.5/x'), null);
  assert.equal(allowedUrl('https://localhost/x'), null);
  assert.equal(allowedUrl('https://[::1]/x'), null);
  assert.ok(allowedUrl('https://mastodon.social/users/x'));
});
