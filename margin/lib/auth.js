'use strict';
const crypto = require('node:crypto');

function hashPassword(pw) {
  const salt = crypto.randomBytes(16);
  const hash = crypto.scryptSync(String(pw), salt, 32);
  return `scrypt$${salt.toString('hex')}$${hash.toString('hex')}`;
}

function verifyPassword(pw, stored) {
  const [alg, saltHex, hashHex] = String(stored).split('$');
  if (alg !== 'scrypt' || !saltHex || !hashHex) return false;
  const want = Buffer.from(hashHex, 'hex');
  const got = crypto.scryptSync(String(pw), Buffer.from(saltHex, 'hex'), want.length);
  return crypto.timingSafeEqual(want, got);
}

function token(bytes = 24) {
  return crypto.randomBytes(bytes).toString('base64url');
}

// Reader keys: four words plus six base32 characters. Readable enough to write
// on paper, about 62 bits of entropy, and the server only ever sees its hash.
const WORDS = (
  'acorn alder amber anchor apple arbor aspen atlas autumn badger bamboo banner barley basin beacon beech ' +
  'berry birch bison bloom bluff bramble brass breeze brook bronze cabin cactus canyon cedar chalk cherry ' +
  'cinder citrus clay clover cobalt comet copper coral cotton cove crane creek crest crow cypress dahlia ' +
  'delta desert dune dusk eagle ember falcon fennel fern field finch fjord flint forest fox frost garnet ' +
  'glacier glade granite grove gull harbor hazel heath heron hickory hollow honey horizon island ivory ivy ' +
  'jade jasper juniper kelp kestrel lagoon larch lark laurel lava ledge lemon lichen linden lotus lumen ' +
  'magpie maple marble marsh meadow mesa midnight mint moss moth nectar nettle north oak oasis ocean olive ' +
  'onyx orchid osprey otter owl oyster paper pebble pepper pine plover plum pollen poppy prairie quail ' +
  'quarry quartz quiet rain raven reed ridge river robin rowan saffron sage salt sand sequoia shale shore ' +
  'sienna silver sky slate sparrow spruce stone storm summit swallow tamarack tern thistle thorn thrush ' +
  'thyme tide timber topaz tulip tundra umber valley velvet violet walnut wave willow wind wren yarrow zephyr'
).split(' ');
const B32 = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

function newReaderKey() {
  const words = [];
  for (let i = 0; i < 4; i++) words.push(WORDS[crypto.randomInt(WORDS.length)]);
  let tail = '';
  for (let i = 0; i < 6; i++) tail += B32[crypto.randomInt(B32.length)];
  return `${words.join('-')}-${tail}`;
}

function normalizeKey(k) {
  const parts = String(k || '').trim().toLowerCase().split(/[\s-]+/).filter(Boolean);
  if (parts.length !== 5) return null;
  return [...parts.slice(0, 4), parts[4].toUpperCase()].join('-');
}

function hashKey(k) {
  const n = normalizeKey(k);
  if (!n) return null;
  return crypto.createHash('sha256').update('margin-reader-key:' + n).digest('hex');
}

function parseCookies(header) {
  const out = {};
  for (const part of String(header || '').split(';')) {
    const i = part.indexOf('=');
    if (i <= 0) continue;
    const raw = part.slice(i + 1).trim();
    // A stray malformed cookie on the domain must not break every page.
    try { out[part.slice(0, i).trim()] = decodeURIComponent(raw); } catch { out[part.slice(0, i).trim()] = raw; }
  }
  return out;
}

module.exports = { hashPassword, verifyPassword, token, newReaderKey, normalizeKey, hashKey, parseCookies, WORDS };
