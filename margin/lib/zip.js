'use strict';
// Minimal zip reader/writer on node:zlib. Reading handles "stored" and
// "deflate" entries, which covers Substack's export and anything a normal
// archiver makes. Writing uses deflate. No zip64 and no encryption.
const zlib = require('node:zlib');

const MAX_ENTRY = 64 * 1024 * 1024;
// Whole-archive limits, so a small zip can't expand into gigabytes (several
// directory entries pointing at one compressed blob was the trick).
const MAX_TOTAL = 256 * 1024 * 1024;
const MAX_ENTRIES = 20000;

function readZip(buf) {
  try { return readZipUnsafe(buf); } catch (e) {
    // Truncated or hand-crafted archives fail on out-of-range reads.
    if (e instanceof RangeError || e.code === 'ERR_OUT_OF_RANGE' || e.code === 'ERR_BUFFER_OUT_OF_BOUNDS') throw new Error('That zip file is damaged or incomplete.');
    throw e;
  }
}

function readZipUnsafe(buf) {
  if (!Buffer.isBuffer(buf) || buf.length < 22) throw new Error('Not a zip file.');
  // Find the end-of-central-directory record (it may be followed by a comment).
  let eocd = -1;
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 65557); i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error('Not a zip file.');
  const count = buf.readUInt16LE(eocd + 10);
  if (count > MAX_ENTRIES) throw new Error('That zip has too many files.');
  let p = buf.readUInt32LE(eocd + 16);
  const files = new Map();
  const seen = new Set();
  let total = 0;
  for (let n = 0; n < count; n++) {
    if (buf.readUInt32LE(p) !== 0x02014b50) throw new Error('Corrupt zip directory.');
    const method = buf.readUInt16LE(p + 10);
    const csize = buf.readUInt32LE(p + 20);
    const usize = buf.readUInt32LE(p + 24);
    const nameLen = buf.readUInt16LE(p + 28);
    const extraLen = buf.readUInt16LE(p + 30);
    const commentLen = buf.readUInt16LE(p + 32);
    const local = buf.readUInt32LE(p + 42);
    const name = buf.toString('utf8', p + 46, p + 46 + nameLen);
    p += 46 + nameLen + extraLen + commentLen;
    if (name.endsWith('/')) continue;
    if (usize > MAX_ENTRY) throw new Error(`${name} is too large.`);
    if (seen.has(local)) throw new Error('Corrupt zip: entries overlap.');
    seen.add(local);
    if (buf.readUInt32LE(local) !== 0x04034b50) throw new Error('Corrupt zip entry.');
    const start = local + 30 + buf.readUInt16LE(local + 26) + buf.readUInt16LE(local + 28);
    const raw = buf.subarray(start, start + csize);
    let data;
    if (method === 0) data = Buffer.from(raw);
    else if (method === 8) {
      // Cap by what's actually produced, not what the header claims.
      try { data = zlib.inflateRawSync(raw, { maxOutputLength: Math.max(1, Math.min(MAX_ENTRY, MAX_TOTAL - total)) }); } catch (e) {
        throw new Error(e instanceof RangeError ? 'That zip expands to more than 256 MB.' : `Couldn’t unpack ${name}.`);
      }
    } else throw new Error(`${name} uses an unsupported compression method.`);
    total += data.length;
    if (total > MAX_TOTAL) throw new Error('That zip expands to more than 256 MB.');
    files.set(name, data);
  }
  return files;
}

// files: array of [name, Buffer|string]
function writeZip(files) {
  const locals = [];
  const central = [];
  let offset = 0;
  for (const [name, content] of files) {
    const data = Buffer.isBuffer(content) ? content : Buffer.from(String(content), 'utf8');
    const comp = zlib.deflateRawSync(data);
    const nameBuf = Buffer.from(name, 'utf8');
    const crc = zlib.crc32(data);
    const lh = Buffer.alloc(30);
    lh.writeUInt32LE(0x04034b50, 0); lh.writeUInt16LE(20, 4); lh.writeUInt16LE(0x0800, 6); lh.writeUInt16LE(8, 8);
    lh.writeUInt32LE(crc, 14); lh.writeUInt32LE(comp.length, 18); lh.writeUInt32LE(data.length, 22);
    lh.writeUInt16LE(nameBuf.length, 26);
    locals.push(lh, nameBuf, comp);
    const ch = Buffer.alloc(46);
    ch.writeUInt32LE(0x02014b50, 0); ch.writeUInt16LE(20, 4); ch.writeUInt16LE(20, 6); ch.writeUInt16LE(0x0800, 8); ch.writeUInt16LE(8, 10);
    ch.writeUInt32LE(crc, 16); ch.writeUInt32LE(comp.length, 20); ch.writeUInt32LE(data.length, 24);
    ch.writeUInt16LE(nameBuf.length, 28); ch.writeUInt32LE(offset, 42);
    central.push(ch, nameBuf);
    offset += 30 + nameBuf.length + comp.length;
  }
  const cd = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(files.length, 8); end.writeUInt16LE(files.length, 10);
  end.writeUInt32LE(cd.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, cd, end]);
}

module.exports = { readZip, writeZip };
