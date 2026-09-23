# Margin

A long-form publishing platform where **readers never need an account to read**, styled as the 1996 default web remade with care.

- **Readers** get a finite front page, a commonplace book for passages they keep, follows without email, and **pass it on**: share a passage as a link that opens right at it.
- **Writers** get a homepage (a "now" line, an accent color, and who they read), a place in **the ring** (prev · random · next, like a webring), verified-read analytics, a paragraph map of where readers leave and what they keep, a count of how often each piece is passed on, and a list they can export.

- **v3 (research-driven):** email follow per writer with double opt-in, recommendations shown right after a follow (credited to the recommending writer), length-normalized ranking, Substack import/export, text-fragment passage links with quote previews, spaced resurfacing, backup/export for the commonplace, and note moderation.

- **v4 (refinement):**
  - Every writer is followable from Mastodon and Threads via ActivityPub.
  - Keep, pass it on and note work by keyboard and screen reader.
  - A share sheet on phones, and a toolbar docked to the bottom on touch screens.
  - One ask at the end of a piece.
  - Reading settings (text size, light/dark).
  - For writers: autosave, image upload, footnotes, scheduled publishing, and a publish confirmation.

Why it's shaped this way: **[DESIGN.md](DESIGN.md)**. §0 has what changed in v4, §0b what changed in v3. Sources: **[RESEARCH.md](RESEARCH.md)**.

## Run it

Requires Node 22.13+ and has no dependencies. It uses the built-in `node:sqlite` and `node:test`.

```bash
cd margin
npm start            # http://localhost:3000  (PORT=... to change)
npm test             # 33 tests, including ActivityPub signatures both ways, Substack import/export, autosave, scheduling
npm run digest       # build this week's Brief for opted-in readers into data/outbox/
npm run reset        # delete the local database; it re-seeds on next start
```

A fresh database seeds four fictional writers and six pieces. Writer sign-in for the demo: handle `mara`, `theo`, `june` or `ravi`, password `demo-password`. **If you ran v1 before, run `npm run reset` first** to get the new demo content (the schema itself migrates automatically).

**The seeded reading numbers are synthetic**, generated so the dashboards have something to show. Start with `MARGIN_DEMO_SIGNALS=0` (after `npm run reset`) to seed the pieces without them. `june` and `ravi` are deliberately left without signals so you can see the new-voice slots at work.

## What to try

1. Open **Today**, then any piece. Nothing asks you for anything. Note the "reading now · finished by" counter.
2. Select a sentence and choose **keep**. Finish the piece. After the verified-read threshold you'll get one ask: follow the writer.
3. Select a sentence and choose **pass it on**. Open the copied link in another window: the passage is highlighted and the page says someone passed it to you.
4. At the bottom of a piece, try the ring: **← prev · random · next →**. Open **the ring** from the nav to see every writer.
5. Select another sentence and choose **note**. Getting a reader key takes one click and no email.
6. Open **Commonplace**, add a note to a passage, and export it as Markdown.
7. In a private window, open Commonplace, choose "I already have a key", paste your key, and everything comes back.
8. Sign in as `theo`, open the **Desk** to see where readers came from and who lists Theo, then click a piece to see the per-paragraph map.
9. **Edit homepage**: change the accent color, the now line, and the list of who you read.
10. **Import from Substack** on the desk (any Substack export zip), then **Export everything** to get it back out.
11. On a writer's homepage, try **Email me new pieces**. Email isn't sent in the prototype, so the confirmation link is shown on screen. After following, the writer's recommendations appear.
12. Start a **New piece** and open with "In recent years, it seems…" to watch the draft check react.

## Layout

```
server.js            HTTP server + routes (no framework)
lib/db.js            SQLite schema
lib/signals.js       verified reads, front-page ranking with new-voice slots, dashboards
lib/ring.js          the ring, blogrolls, "reading now", spotlight
lib/portability.js   Substack import (posts, drafts, email list) and export in Substack's layout
lib/zip.js, csv.js   dependency-free zip read/write and RFC 4180 CSV
lib/htmlmd.js        Substack HTML → Markdown
lib/draftcheck.js    advisory draft check from the SuperWritingEngine voice spec (A.1–A.3)
lib/markdown.js      escape-first Markdown with paragraph indexes
lib/auth.js          writer passwords (scrypt), sessions, reader keys (hashed)
lib/views.js         server-rendered HTML
lib/seed.js          demo writers, pieces and optional synthetic signals
public/              CSS and small vanilla-JS files (local state, reading, commonplace, editor)
public/fonts/        self-hosted Newsreader, Fraunces, IBM Plex Mono (SIL Open Font License)
scripts/digest.js    The Brief builder
test/app.test.js     end-to-end tests against an in-memory database
```

## Deploying federation

Set `MARGIN_PUBLIC_URL=https://your.domain` (fediverse ids must be stable and on HTTPS) and `MARGIN_SECURE_COOKIES=1`. Writers are then `@handle@your.domain`. Outbound fetches refuse private IPs and non-HTTPS URLs, but they don't resolve DNS, so put the server behind an egress firewall. `MARGIN_AP_INSECURE=1` exists only for local testing.

## What is simulated

- **Tips** are recorded but no money moves. Plug in a payment provider in `POST /api/tip`.
- **Email** (confirmations, new-post notices, The Brief) is written to the `mail` and `outbox` tables, not sent. The confirmation link is shown on screen (`MARGIN_SHOW_MAIL=0` hides it once a provider is wired up). The Brief is also available as RSS at `/brief.xml`.
- Set `MARGIN_SECURE_COOKIES=1` behind HTTPS.
