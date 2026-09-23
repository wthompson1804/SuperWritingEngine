# Margin

A long-form publishing platform where **readers never need an account to read**. Readers get a finite front page, a commonplace book for passages they keep, and follows without email. Writers get verified-read analytics, a paragraph-level map of where readers leave and what they keep, an earned-ask funnel, and a list they can export.

Why it's shaped this way (persona, problem statement, value categorization, cold start, open questions): **[DESIGN.md](DESIGN.md)**.

## Run it

Requires Node 22.13+ and has no dependencies. It uses the built-in `node:sqlite` and `node:test`.

```bash
cd margin
npm start            # http://localhost:3000  (PORT=... to change)
npm test             # 9 tests: markdown safety, draft check, keys, reading signals, writer flow, RSS
npm run digest       # build this week's Brief for opted-in readers into data/outbox/
npm run reset        # delete the local database; it re-seeds on next start
```

A fresh database seeds three fictional writers and five pieces. Writer sign-in for the demo: handle `mara` or `theo` (or `june`), password `demo-password`.

**The seeded reading numbers are synthetic**, generated so the dashboards have something to show. Start with `MARGIN_DEMO_SIGNALS=0` (after `npm run reset`) to seed the pieces without them. `june` is deliberately left without signals so you can see the new-voice slot at work.

## What to try

1. Open **Today**, then any piece. Nothing asks you for anything.
2. Select a sentence and choose **Keep**. Finish the piece. After the verified-read threshold you'll get one ask: follow the writer.
3. Select another sentence and choose **Note in margin**. Getting a reader key takes one click and no email.
4. Open **Commonplace**, add a note to a passage, and export it as Markdown.
5. In a private window, open Commonplace, choose "I already have a key", paste your key, and everything comes back.
6. Sign in as `theo`, open the **Desk**, then click a piece to see the per-paragraph reach and keep map.
7. Start a **New piece** and open with "In recent years, it seems…" to watch the draft check react.

## Layout

```
server.js            HTTP server + routes (no framework)
lib/db.js            SQLite schema
lib/signals.js       verified reads, front-page ranking with new-voice slots, dashboards
lib/draftcheck.js    advisory draft check from the SuperWritingEngine voice spec (A.1–A.3)
lib/markdown.js      escape-first Markdown with paragraph indexes
lib/auth.js          writer passwords (scrypt), sessions, reader keys (hashed)
lib/views.js         server-rendered HTML
lib/seed.js          demo writers, pieces and optional synthetic signals
public/              CSS and small vanilla-JS files (local state, reading, commonplace, editor)
scripts/digest.js    The Brief builder
test/app.test.js     end-to-end tests against an in-memory database
```

## What is simulated

- **Tips** are recorded but no money moves. Plug in a payment provider in `POST /api/tip`.
- **The Brief** is built and stored in the outbox, but not emailed. Plug in a mail provider in `scripts/digest.js`.
- Set `MARGIN_SECURE_COOKIES=1` behind HTTPS.
