'use strict';
const { DatabaseSync } = require('node:sqlite');
const fs = require('node:fs');
const path = require('node:path');

const SCHEMA = `
CREATE TABLE IF NOT EXISTS authors (
  id INTEGER PRIMARY KEY,
  handle TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  bio TEXT NOT NULL DEFAULT '',
  pw_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  author_id INTEGER NOT NULL REFERENCES authors(id),
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  author_id INTEGER NOT NULL REFERENCES authors(id),
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  dek TEXT NOT NULL DEFAULT '',
  body_md TEXT NOT NULL DEFAULT '',
  words INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'draft',
  published_at INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
-- One row per page view. pv is a random id minted in the page; no cookie, no IP.
CREATE TABLE IF NOT EXISTS views (
  pv TEXT PRIMARY KEY,
  post_id INTEGER NOT NULL REFERENCES posts(id),
  max_depth REAL NOT NULL DEFAULT 0,
  dwell_ms INTEGER NOT NULL DEFAULT 0,
  source TEXT NOT NULL DEFAULT 'direct',
  keyed INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS views_post ON views(post_id);
-- Anonymous: which paragraph was kept, nothing about who kept it.
CREATE TABLE IF NOT EXISTS keeps (
  id INTEGER PRIMARY KEY,
  post_id INTEGER NOT NULL REFERENCES posts(id),
  pv TEXT,
  para INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  UNIQUE (post_id, pv, para)
);
CREATE INDEX IF NOT EXISTS keeps_post ON keeps(post_id);
CREATE TABLE IF NOT EXISTS follow_events (
  id INTEGER PRIMARY KEY,
  author_id INTEGER NOT NULL REFERENCES authors(id),
  post_id INTEGER REFERENCES posts(id),
  delta INTEGER NOT NULL,
  keyed INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS asks (
  id INTEGER PRIMARY KEY,
  post_id INTEGER REFERENCES posts(id),
  kind TEXT NOT NULL,
  event TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tips (
  id INTEGER PRIMARY KEY,
  post_id INTEGER NOT NULL REFERENCES posts(id),
  amount_cents INTEGER NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL
);
-- A reader key is the only reader credential. We store its hash, never the key.
CREATE TABLE IF NOT EXISTS readers (
  id INTEGER PRIMARY KEY,
  key_hash TEXT UNIQUE NOT NULL,
  email TEXT,
  digest INTEGER NOT NULL DEFAULT 0,
  share_email INTEGER NOT NULL DEFAULT 0,
  data TEXT NOT NULL DEFAULT '{}',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reader_follows (
  reader_id INTEGER NOT NULL REFERENCES readers(id),
  author_id INTEGER NOT NULL REFERENCES authors(id),
  created_at INTEGER NOT NULL,
  PRIMARY KEY (reader_id, author_id)
);
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY,
  post_id INTEGER NOT NULL REFERENCES posts(id),
  para INTEGER NOT NULL,
  reader_id INTEGER NOT NULL REFERENCES readers(id),
  display_name TEXT NOT NULL,
  quote TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS notes_post ON notes(post_id);
CREATE TABLE IF NOT EXISTS outbox (
  id INTEGER PRIMARY KEY,
  reader_id INTEGER NOT NULL REFERENCES readers(id),
  email TEXT NOT NULL,
  subject TEXT NOT NULL,
  html TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
`;

function open(file) {
  if (file !== ':memory:') fs.mkdirSync(path.dirname(file), { recursive: true });
  const db = new DatabaseSync(file);
  db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;');
  db.exec(SCHEMA);
  return db;
}

// Tiny helpers so call sites read cleanly.
function helpers(db) {
  const cache = new Map();
  const stmt = (sql) => {
    let s = cache.get(sql);
    if (!s) { s = db.prepare(sql); cache.set(sql, s); }
    return s;
  };
  return {
    db,
    get: (sql, ...a) => stmt(sql).get(...a),
    all: (sql, ...a) => stmt(sql).all(...a),
    run: (sql, ...a) => stmt(sql).run(...a),
    tx(fn) {
      db.exec('BEGIN');
      try { const r = fn(); db.exec('COMMIT'); return r; } catch (e) { db.exec('ROLLBACK'); throw e; }
    },
  };
}

module.exports = { open, helpers };
