'use strict';
// Operational plumbing: structured request logs, SQLite backups, pruning of
// tables that would otherwise grow forever, and graceful shutdown.

const fs = require('node:fs');
const path = require('node:path');
const { backup } = require('node:sqlite');

const DAY = 86400000;

// One JSON line per request: what production log tools expect. Never logs
// cookies, bodies, query strings or client addresses (readers are anonymous).
function requestLogger(out = process.stdout) {
  return (req, res, extra = {}) => {
    const t = process.hrtime.bigint();
    res.on('finish', () => {
      const ms = Number(process.hrtime.bigint() - t) / 1e6;
      const line = { t: new Date().toISOString(), m: req.method, p: new URL(req.url, 'http://x').pathname, s: res.statusCode, ms: Math.round(ms * 10) / 10, ...extra };
      out.write(JSON.stringify(line) + '\n');
    });
  };
}

// Online backup with SQLite's backup API: safe while the app is running.
// Keeps the last `keep` daily files.
async function backupDb(db, dbFile, { dir = path.join(path.dirname(dbFile), 'backups'), keep = 7 } = {}) {
  if (dbFile === ':memory:') return null;
  fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  const name = `margin-${new Date().toISOString().slice(0, 10)}.db`;
  const dest = path.join(dir, name);
  await backup(db, dest + '.tmp');
  fs.chmodSync(dest + '.tmp', 0o600); // password hashes, private keys, emails
  fs.renameSync(dest + '.tmp', dest);
  const files = fs.readdirSync(dir).filter((f) => /^margin-\d{4}-\d{2}-\d{2}\.db$/.test(f)).sort();
  for (const f of files.slice(0, Math.max(0, files.length - keep))) fs.unlinkSync(path.join(dir, f));
  return dest;
}

// Tables that grow without bound get trimmed on a schedule. Ranking looks
// back 90 days at most, so older page views are aggregated away; sent mail,
// finished deliveries and cached remote actors are kept for a month.
function prune(h, now = Date.now()) {
  const out = {};
  out.views = h.run('DELETE FROM views WHERE created_at < ?', now - 90 * DAY).changes;
  out.mail = h.run(`DELETE FROM mail WHERE status IN ('sent', 'failed') AND created_at < ?`, now - 30 * DAY).changes;
  // A confirmation nobody could send for a week is dead (its link has expired).
  out.unsent = h.run(`DELETE FROM mail WHERE status = 'pending' AND created_at < ?`, now - 7 * DAY).changes;
  out.outbox = h.run('DELETE FROM outbox WHERE created_at < ?', now - 30 * DAY).changes;
  // Reader keys that were made and never used for anything.
  out.readers = h.run(`DELETE FROM readers WHERE email IS NULL AND length(data) < 80 AND updated_at < ? AND id NOT IN (SELECT reader_id FROM reader_follows) AND id NOT IN (SELECT reader_id FROM notes) AND id NOT IN (SELECT reader_id FROM outbox)`, now - 90 * DAY).changes;
  // An inbox that has been failing for a month straight, with no success and
  // nothing still pending, belongs to a dead server: drop its followers.
  // (Decided before old deliveries are deleted, or the evidence is gone.)
  out.followers = h.run(`DELETE FROM ap_followers WHERE inbox IN (
    SELECT inbox FROM ap_deliveries GROUP BY inbox
    HAVING min(CASE WHEN status = 'failed' THEN created_at END) < ?
       AND sum(CASE WHEN status IN ('done', 'pending', 'sending') THEN 1 ELSE 0 END) = 0)`, now - 30 * DAY).changes;
  out.deliveries = h.run(`DELETE FROM ap_deliveries WHERE status IN ('done', 'failed') AND created_at < ?`, now - 30 * DAY).changes;
  out.actors = h.run('DELETE FROM ap_actors WHERE fetched_at < ? AND actor NOT IN (SELECT actor FROM ap_followers)', now - 30 * DAY).changes;
  out.sessions = h.run('DELETE FROM sessions WHERE created_at < ?', now - 30 * DAY).changes;
  out.pending = h.run(`DELETE FROM email_subs WHERE status = 'pending' AND created_at < ?`, now - 30 * DAY).changes;
  h.db.exec('PRAGMA wal_checkpoint(TRUNCATE)');
  return out;
}

// Stops taking connections, lets in-flight requests finish (up to a limit),
// then closes the database cleanly.
function gracefulShutdown(server, db, { timeoutMs = 10000, log = () => {} } = {}) {
  let closing = false;
  return (signal) => {
    if (closing) return;
    closing = true;
    log(`received ${signal}, shutting down`);
    const force = setTimeout(() => { log('forcing exit'); process.exit(1); }, timeoutMs);
    force.unref();
    server.close(() => {
      try { db.exec('PRAGMA wal_checkpoint(TRUNCATE)'); db.close(); } catch (e) { log(`close: ${e.message}`); }
      clearTimeout(force);
      process.exit(0);
    });
    if (server.closeIdleConnections) server.closeIdleConnections();
  };
}

module.exports = { requestLogger, backupDb, prune, gracefulShutdown };
