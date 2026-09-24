'use strict';
// ActivityPub: every writer is followable from Mastodon, Threads, Ghost 6,
// WordPress and the rest of the fediverse, as @handle@your-domain. A reader
// following from Mastodon needs no Margin account, which is the whole point.
//
// What's implemented:
//   WebFinger, Person actors with RSA keys, an outbox of Articles, a followers
//   count, and an inbox that accepts Follow / Undo(Follow) / Delete. Inbox
//   requests must carry a valid HTTP Signature (draft-cavage, rsa-sha256) and
//   a matching Digest. Outbound requests (Accept, Create on publish, and
//   key fetches) are signed with the writer's key, so servers running
//   Mastodon's "secure mode" accept them. Deliveries are queued and retried
//   with backoff.
// Not implemented: replies, likes and boosts (they arrive and are ignored),
// Update on edit, and Delete on unpublish.

const crypto = require('node:crypto');
const net = require('node:net');
const dns = require('node:dns').promises;
const { render } = require('./markdown');

const AS = 'https://www.w3.org/ns/activitystreams';
const PUBLIC = `${AS}#Public`;
const AP_TYPES = /application\/(activity\+json|ld\+json)/i;
const MAX_ATTEMPTS = 8;

function wantsActivityJson(req) {
  return AP_TYPES.test(String(req.headers.accept || ''));
}

function ensureKeys(h, authorId) {
  const a = h.get('SELECT ap_public_key, ap_private_key FROM authors WHERE id = ?', authorId);
  if (a && a.ap_public_key) return { publicKey: a.ap_public_key, privateKey: a.ap_private_key };
  const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
    modulusLength: 2048,
    publicKeyEncoding: { type: 'spki', format: 'pem' },
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
  });
  h.run('UPDATE authors SET ap_public_key = ?, ap_private_key = ? WHERE id = ?', publicKey, privateKey, authorId);
  return { publicKey, privateKey };
}

const ids = (base, handle) => {
  const actor = `${base}/ap/users/${handle}`;
  return { actor, key: `${actor}#main-key`, inbox: `${actor}/inbox`, outbox: `${actor}/outbox`, followers: `${actor}/followers`, shared: `${base}/ap/inbox` };
};

function actorJson(h, base, author) {
  const k = ensureKeys(h, author.id);
  const u = ids(base, author.handle);
  const esc = (s) => String(s || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  return {
    '@context': [AS, 'https://w3id.org/security/v1'],
    id: u.actor, type: 'Person', preferredUsername: author.handle, name: author.name,
    summary: `<p>${esc(author.bio)}</p>${author.now_line ? `<p><em>${esc(author.now_line)}</em></p>` : ''}`,
    url: `${base}/@${author.handle}`, inbox: u.inbox, outbox: u.outbox, followers: u.followers,
    manuallyApprovesFollowers: false, discoverable: true, published: new Date(author.created_at).toISOString(),
    endpoints: { sharedInbox: u.shared },
    publicKey: { id: u.key, owner: u.actor, publicKeyPem: k.publicKey },
  };
}

function articleJson(base, author, post) {
  const u = ids(base, author.handle);
  return {
    id: `${base}/ap/posts/${post.id}`, type: 'Article', attributedTo: u.actor,
    name: post.title, summary: post.dek || null,
    content: render(post.body_md).html.replace(/ data-p="\d+"/g, ''), mediaType: 'text/html',
    url: `${base}/p/${post.slug}`, published: new Date(post.published_at).toISOString(),
    to: [PUBLIC], cc: [u.followers],
  };
}

function createActivity(base, author, post) {
  const art = articleJson(base, author, post);
  return { '@context': AS, id: `${art.id}#create`, type: 'Create', actor: art.attributedTo, published: art.published, to: art.to, cc: art.cc, object: art };
}

function outboxJson(h, base, author) {
  const u = ids(base, author.handle);
  const posts = h.all(`SELECT * FROM posts WHERE author_id = ? AND status = 'published' ORDER BY published_at DESC LIMIT 20`, author.id);
  const total = h.get(`SELECT count(*) AS n FROM posts WHERE author_id = ? AND status = 'published'`, author.id).n;
  return { '@context': AS, id: u.outbox, type: 'OrderedCollection', totalItems: total, orderedItems: posts.map((p) => createActivity(base, author, p)) };
}

function followersJson(h, base, author) {
  const u = ids(base, author.handle);
  // Count only: who follows a writer is not public.
  return { '@context': AS, id: u.followers, type: 'OrderedCollection', totalItems: h.get('SELECT count(*) AS n FROM ap_followers WHERE author_id = ?', author.id).n };
}

function webfinger(h, base, resource) {
  const m = String(resource || '').match(/^acct:@?([a-z0-9_]{2,24})@(.+)$/i);
  if (!m) return null;
  const host = new URL(base).host;
  if (m[2].toLowerCase() !== host.toLowerCase()) return null;
  const a = h.get('SELECT handle FROM authors WHERE handle = ?', m[1].toLowerCase());
  if (!a) return null;
  const u = ids(base, a.handle);
  return {
    subject: `acct:${a.handle}@${host}`,
    aliases: [u.actor, `${base}/@${a.handle}`],
    links: [
      { rel: 'self', type: 'application/activity+json', href: u.actor },
      { rel: 'http://webfinger.net/rel/profile-page', type: 'text/html', href: `${base}/@${a.handle}` },
    ],
  };
}

// ---------- HTTP signatures ----------

function digestOf(body) {
  return 'SHA-256=' + crypto.createHash('sha256').update(body).digest('base64');
}

function signHeaders({ method, url, body, keyId, privateKey }) {
  const u = new URL(url);
  const date = new Date().toUTCString();
  const headers = { host: u.host, date };
  const names = ['(request-target)', 'host', 'date'];
  if (body != null) { headers.digest = digestOf(body); names.push('digest'); }
  const str = names.map((n) => (n === '(request-target)' ? `(request-target): ${method.toLowerCase()} ${u.pathname}${u.search}` : `${n}: ${headers[n]}`)).join('\n');
  const signature = crypto.sign('sha256', Buffer.from(str), privateKey).toString('base64');
  headers.signature = `keyId="${keyId}",algorithm="rsa-sha256",headers="${names.join(' ')}",signature="${signature}"`;
  return headers;
}

function parseSignature(header) {
  const out = {};
  for (const m of String(header || '').matchAll(/(\w+)="([^"]*)"/g)) out[m[1]] = m[2];
  return out.keyId && out.signature ? out : null;
}

// Outbound requests go only to public addresses. Private, loopback,
// link-local, CGNAT, documentation, multicast and IPv6 transition ranges
// (NAT64, 6to4, Teredo) are all refused, and hostnames are resolved and
// checked before connecting. A DNS answer that changes between the check and
// the connection (rebinding) is still possible, so production should also sit
// behind an egress firewall.
const BLOCKED = new net.BlockList();
for (const [a, p] of [['0.0.0.0', 8], ['10.0.0.0', 8], ['100.64.0.0', 10], ['127.0.0.0', 8], ['169.254.0.0', 16], ['172.16.0.0', 12],
  ['192.0.0.0', 24], ['192.0.2.0', 24], ['192.88.99.0', 24], ['192.168.0.0', 16], ['198.18.0.0', 15], ['198.51.100.0', 24],
  ['203.0.113.0', 24], ['224.0.0.0', 4], ['240.0.0.0', 4]]) BLOCKED.addSubnet(a, p, 'ipv4');
for (const [a, p] of [['::', 128], ['::1', 128], ['64:ff9b::', 96], ['64:ff9b:1::', 48], ['100::', 64], ['2001::', 32], ['2001:db8::', 32],
  ['2002::', 16], ['fc00::', 7], ['fe80::', 10], ['fec0::', 10], ['ff00::', 8]]) BLOCKED.addSubnet(a, p, 'ipv6');

function blockedIp(ip) {
  const v = net.isIP(ip);
  if (!v) return true;
  if (v === 6) {
    const mapped = ip.match(/^::ffff:(\d+\.\d+\.\d+\.\d+)$/i);
    if (mapped) return BLOCKED.check(mapped[1], 'ipv4');
    // Also catch hex-form mapped addresses like ::ffff:7f00:1.
    const hex = ip.match(/^::ffff:([0-9a-f]{1,4}):([0-9a-f]{1,4})$/i);
    if (hex) { const a = parseInt(hex[1], 16), b = parseInt(hex[2], 16); return BLOCKED.check(`${a >> 8}.${a & 255}.${b >> 8}.${b & 255}`, 'ipv4'); }
    return BLOCKED.check(ip, 'ipv6');
  }
  return BLOCKED.check(ip, 'ipv4');
}

// Synchronous screen: scheme, and literal hosts. Returns a URL or null.
function allowedUrl(raw, { allowHttp = false, allowPrivate = false } = {}) {
  let u;
  try { u = new URL(raw); } catch { return null; }
  if (u.protocol !== 'https:' && !(allowHttp && u.protocol === 'http:')) return null;
  if (u.username || u.password) return null;
  if (!allowPrivate) {
    const host = u.hostname.replace(/^\[|\]$/g, '').replace(/\.+$/, '').toLowerCase();
    if (!host || /(^|\.)(localhost|local|internal|localdomain|home\.arpa)$/.test(host)) return null;
    if (net.isIP(host) ? blockedIp(host) : !host.includes('.')) return null;
  }
  return u;
}

// Full check: also resolves the hostname and screens every address.
async function publicUrl(raw, guard) {
  const u = allowedUrl(raw, guard);
  if (!u) return null;
  if (guard.allowPrivate) return u;
  const host = u.hostname.replace(/^\[|\]$/g, '');
  if (net.isIP(host)) return u;
  try {
    const addrs = await dns.lookup(host.replace(/\.+$/, ''), { all: true, verbatim: true });
    if (!addrs.length || addrs.some((x) => blockedIp(x.address))) return null;
  } catch { return null; }
  return u;
}

// Reads a response body, giving up past a size limit instead of buffering it all.
async function readCapped(res, limit) {
  const reader = res.body && res.body.getReader();
  if (!reader) return '';
  const chunks = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.length;
    if (size > limit) { reader.cancel().catch(() => {}); throw new Error('Response too large'); }
    chunks.push(value);
  }
  return Buffer.concat(chunks).toString('utf8');
}

function createFederation(h, { allowHttp = false, allowPrivate = false, fetchImpl = fetch, log = () => {} } = {}) {
  const guard = { allowHttp, allowPrivate };

  async function signedGet(url, signer) {
    const u = await publicUrl(url, guard);
    if (!u) throw new Error('URL not allowed');
    const headers = { accept: 'application/activity+json, application/ld+json' };
    if (signer) Object.assign(headers, signHeaders({ method: 'GET', url: u.href, body: null, ...signer }));
    const res = await fetchImpl(u.href, { headers, signal: AbortSignal.timeout(10000), redirect: 'error' });
    if (!res.ok) throw Object.assign(new Error(`GET ${u.href} → ${res.status}`), { gone: res.status === 410 });
    return JSON.parse(await readCapped(res, 1_000_000));
  }

  // Fetch (or reuse) the remote actor behind a keyId.
  async function remoteActor(keyId, signer, { refresh = false } = {}) {
    const actorUrl = keyId.split('#')[0];
    const cached = h.get('SELECT * FROM ap_actors WHERE key_id = ?', keyId);
    if (cached && !refresh && Date.now() - cached.fetched_at < 24 * 3600 * 1000) return JSON.parse(cached.doc);
    let doc;
    try { doc = await signedGet(actorUrl, signer); } catch (e) {
      // A deleted account (410) still signs its own Delete with its old key;
      // the cached copy of that key, however old, is what verifies it.
      if (e.gone && cached) return JSON.parse(cached.doc);
      throw e;
    }
    // Some servers put the key on a separate document that points at its owner.
    if (!doc.inbox && doc.owner) doc = await signedGet(doc.owner, signer);
    if (!doc.publicKey || !doc.publicKey.publicKeyPem) throw new Error('Actor has no public key');
    // The actor must live on the same origin as the key that signed, or a
    // server could claim to speak for someone else's account.
    if (!doc.id || new URL(doc.id).origin !== new URL(keyId).origin) throw new Error('Key and actor origins differ');
    h.run(`INSERT INTO ap_actors (key_id, actor, doc, fetched_at) VALUES (?,?,?,?)
           ON CONFLICT(key_id) DO UPDATE SET actor = excluded.actor, doc = excluded.doc, fetched_at = excluded.fetched_at`, keyId, doc.id, JSON.stringify(doc), Date.now());
    return doc;
  }

  // Verifies an inbox POST. Returns the signing actor document, or throws.
  async function verifyInbox(req, rawBody, signer) {
    const sig = parseSignature(req.headers.signature);
    if (!sig) throw new Error('Missing signature');
    if ((sig.algorithm || 'rsa-sha256').toLowerCase() !== 'rsa-sha256' && sig.algorithm !== 'hs2019') throw new Error('Unsupported algorithm');
    const names = (sig.headers || 'date').toLowerCase().split(/\s+/);
    for (const need of ['(request-target)', 'host', 'date', 'digest']) if (!names.includes(need)) throw new Error(`Signature must cover ${need}`);
    if (req.headers.digest !== digestOf(rawBody)) throw new Error('Digest mismatch');
    const date = Date.parse(req.headers.date);
    if (!Number.isFinite(date) || Math.abs(Date.now() - date) > 12 * 3600 * 1000) throw new Error('Date too far off');
    const path = new URL(req.url, 'http://x');
    const str = names.map((n) => (n === '(request-target)' ? `(request-target): ${req.method.toLowerCase()} ${path.pathname}${path.search}` : `${n}: ${req.headers[n] ?? ''}`)).join('\n');
    const check = (doc) => crypto.verify('sha256', Buffer.from(str), doc.publicKey.publicKeyPem, Buffer.from(sig.signature, 'base64'));
    let doc = await remoteActor(sig.keyId, signer);
    // Keys rotate: one retry with a fresh fetch before rejecting.
    if (!check(doc)) { doc = await remoteActor(sig.keyId, signer, { refresh: true }); if (!check(doc)) throw new Error('Bad signature'); }
    return doc;
  }

  function enqueue(authorId, inbox, activity) {
    if (!allowedUrl(inbox, guard)) return;
    h.run('INSERT INTO ap_deliveries (author_id, inbox, body, attempts, next_at, status, created_at) VALUES (?,?,?,0,?,\'pending\',?)',
      authorId, inbox, JSON.stringify(activity), Date.now(), Date.now());
    setImmediate(drain);
  }

  let draining = false;
  async function drain() {
    if (draining) return;
    draining = true;
    try {
      const due = h.all(`SELECT * FROM ap_deliveries WHERE status = 'pending' AND next_at <= ? ORDER BY id LIMIT 20`, Date.now());
      for (const d of due) {
        const a = h.get('SELECT id, handle FROM authors WHERE id = ?', d.author_id);
        const k = ensureKeys(h, a.id);
        const base = JSON.parse(d.body).actor.replace(/\/ap\/users\/.*$/, '');
        try {
          if (!(await publicUrl(d.inbox, guard))) throw new Error('inbox address not allowed');
          const headers = signHeaders({ method: 'POST', url: d.inbox, body: d.body, keyId: ids(base, a.handle).key, privateKey: k.privateKey });
          const res = await fetchImpl(d.inbox, { method: 'POST', headers: { ...headers, 'content-type': 'application/activity+json' }, body: d.body, signal: AbortSignal.timeout(15000), redirect: 'error' });
          if (res.ok) { h.run(`UPDATE ap_deliveries SET status = 'done', attempts = attempts + 1 WHERE id = ?`, d.id); continue; }
          throw new Error(`HTTP ${res.status}`);
        } catch (e) {
          const attempts = d.attempts + 1;
          h.run(`UPDATE ap_deliveries SET attempts = ?, next_at = ?, last_error = ?, status = ? WHERE id = ?`,
            attempts, Date.now() + 30000 * 2 ** attempts, String(e.message).slice(0, 200), attempts >= MAX_ATTEMPTS ? 'failed' : 'pending', d.id);
          log(`delivery to ${d.inbox} failed: ${e.message}`);
        }
      }
    } finally { draining = false; }
  }
  const timer = setInterval(drain, 15000);
  timer.unref();

  // Handles a verified activity addressed to one of our writers.
  function receive(base, activity, signerDoc) {
    if (!activity || typeof activity !== 'object') return 'ignored';
    if (activity.actor && activity.actor !== signerDoc.id) throw new Error('Actor does not match signature');
    const type = activity.type;
    const targetAuthor = (obj) => {
      const m = String(typeof obj === 'string' ? obj : obj && obj.id || '').match(/\/ap\/users\/([a-z0-9_]+)$/);
      return m ? h.get('SELECT id, handle, name FROM authors WHERE handle = ?', m[1]) : null;
    };
    if (type === 'Follow') {
      const a = targetAuthor(activity.object);
      if (!a) return 'unknown-target';
      const inbox = (signerDoc.endpoints && signerDoc.endpoints.sharedInbox) || signerDoc.inbox;
      h.run(`INSERT INTO ap_followers (author_id, actor, inbox, created_at) VALUES (?,?,?,?)
             ON CONFLICT(author_id, actor) DO UPDATE SET inbox = excluded.inbox`, a.id, signerDoc.id, inbox, Date.now());
      const u = ids(base, a.handle);
      enqueue(a.id, signerDoc.inbox, { '@context': AS, id: `${u.actor}#accept-${crypto.randomBytes(8).toString('hex')}`, type: 'Accept', actor: u.actor, object: activity });
      return 'followed';
    }
    if (type === 'Undo' && activity.object && activity.object.type === 'Follow') {
      const a = targetAuthor(activity.object.object);
      if (a) h.run('DELETE FROM ap_followers WHERE author_id = ? AND actor = ?', a.id, signerDoc.id);
      return 'unfollowed';
    }
    if (type === 'Delete' && (activity.object === signerDoc.id || (activity.object && activity.object.id === signerDoc.id))) {
      h.run('DELETE FROM ap_followers WHERE actor = ?', signerDoc.id);
      return 'deleted';
    }
    return 'ignored';
  }

  function publish(base, author, post) {
    const activity = createActivity(base, author, post);
    const inboxes = [...new Set(h.all('SELECT inbox FROM ap_followers WHERE author_id = ?', author.id).map((r) => r.inbox))];
    for (const inbox of inboxes) enqueue(author.id, inbox, activity);
    return inboxes.length;
  }

  return { verifyInbox, receive, publish, drain, signerFor: (base, author) => ({ keyId: ids(base, author.handle).key, privateKey: ensureKeys(h, author.id).privateKey }) };
}

module.exports = { createFederation, actorJson, articleJson, outboxJson, followersJson, webfinger, wantsActivityJson, signHeaders, digestOf, allowedUrl, ids };
