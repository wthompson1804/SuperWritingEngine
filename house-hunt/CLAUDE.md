# Lamia House Hunt: data pipeline

This folder is a data-collection pipeline, not an app. It gathers sourced, structured data that a
later decision-support tool will use to help Lamia choose where to live. **Do not build UI, rank
places or recommend anything here.** Deliver files.

Start every session by reading `PROGRESS.md`, then `docs/HANDOFF_2026-11-15.md` if you need the
full brief (who Lamia is, her limits, scope, phases, decisions and rejected directions).

## Working rules

1. **Never invent.** Every record carries a source URL and a retrieval time (UTC ISO 8601). Missing
   means `not_found`, plus where you looked (`notes` or `search_log`). Estimates are labelled
   (`value_type = estimate`) with the method.
2. **Never take a price or a date from a search-result snippet.** Prices and availability come from
   the listing page itself, with its URL and the time it was seen.
3. **Respect terms and robots rules.** Do not get around logins, CAPTCHAs, 403s or bot walls.
   Throttle (see `scripts/lib.py`; default 1 request/second/host). Prefer official APIs, bulk
   downloads, sitemaps and RSS. Check `docs/SOURCES.md` before touching a source; record new findings there.
   **robots.txt groups that name Claude (ClaudeBot, Claude-User, Claude-SearchBot, anthropic-ai) apply to us and
   override `*`.** Honour `Crawl-delay`.
4. **Cache raw responses** in `raw/<source>/` (use `scripts/lib.py: cached_get`) so normalization can
   be rerun without refetching. Raw captures above about 50 MB are not committed (see `.gitignore`);
   their download script must be able to recreate them.
5. **Scripts are idempotent and resumable.** Re-running a script must not duplicate rows. Write
   to disk as you go.
6. **Short excerpts only** from reviews and posts (one or two sentences), always with a permalink.
   Do not store usernames.
7. **Facts and opinions stay in separate fields.**
8. **Keep sources separate.** Never blend, for example, Zillow ZORI and HUD SAFMR into one number.
9. **Do not collect or score racial, ethnic or religious composition.**
10. **Keep listings with unknown attributes** (dogs, stairs, elevator) and flag them. Drop only
    listings that state no dogs, or a walk-up above one flight, and log the drop counts.
11. **Collect above the cap on purpose**, up to the stretch ceiling, and tag the tier (see the data dictionary).
12. **Stop and ask** when a key, a paid service or a scope judgment is needed. **Tell Will plainly**
    when a source is blocked or a target will not be met.
13. **Keep bulk data out of the agent's context.** Write to disk and read back summaries. Use one
    subagent per area or per source for parallel work.
14. Each phase ends with a commit, an updated `PROGRESS.md` and a coverage summary.

## Layout

- `seeds/`: hand-entered inputs (area list with anchor stations). Edit here, then rebuild.
- `raw/`: timestamped captures, one folder per source, each with `_index.jsonl` (url, time, status).
- `data/`: normalized CSVs plus `house_hunt.sqlite` (built by `scripts/build_sqlite.py`).
- `scripts/`: fetchers and normalizers. `lib.py` holds the cached, throttled fetch.
- `docs/`: `DATA_DICTIONARY.md`, `SOURCES.md`, the handoff brief, then later `COVERAGE.md`, `CONFLICTS.md` and `FINDINGS.md`.

## Fixed parameters (plan v3, approved 2026-11-15: `docs/PLAN_V3_APPROVED_2026-11-15.md` is the authority)

- Travel anchor: **Jamaica LIRR station**, GTFS LIRR stop_id 102 (40.699608, -73.808530).
- Gates: studio or 1BR; listed rent ≤ $3,000 **and** all-in ≤ $3,000 (rent + required fees + pet rent + parking +
  estimated electric, gas, internet; estimates get an asterisk); available now through **Dec 15, 2026**; dogs explicitly
  allowed with any weight limit ≥ 25 lb (lowered from 40 by Will); **elevator building only, no ground-floor units**; under 2 h free-flow drive to
  Jamaica; **Queens included**; live link with price and date read from the listing page.
- Per neighborhood: up to 10 places plus up to 5 "looks good, but avoid" cards. Avoid thresholds are in the plan.
- Years (5 or 6), their names, neighborhoods and all wording come from the data. Nothing from the mock's text carries over.
- Tours start Nov 22. Three approval checkpoints with Will: (A) neighborhoods, year groupings, score thresholds;
  (B) avoid list; (C) draft page.
- The earlier brief's tiers, the 98-area seed list as the scope, "no ranking / data only", and the $2,800 cap are superseded.

## Standing instructions from Will (2026-11-15)

- **Run everything that can run in parallel, at the same time, without being asked.** When only a couple of things are
  in flight, look for more independent work and start it. The aim is to wrap up. (Parallel work must not edit files
  another running agent owns; give each agent its own output files.)
- The job is now the finished decision page, not data only: the "do not build UI, rank or recommend" line above is superseded.
- One refusal (403, 429, CAPTCHA) from a host ends requests to that host for the session. Say so in every agent brief.
- **Floor rule (Will, 2026-11-16):** an unpublished floor is not a strike. It is a standing tour question ("confirm it is
  above the ground floor"). A floor stated or confirmed as ground, or a checker's reading that the unit is probably or
  possibly ground-level, still excludes the unit. Open gate facts that count toward "two or more: not shown" are only
  elevator, dogs, and whether the listing is real and available; lease term, cost near the cap, condo-by-owner and
  net-effective rent are disclosures and never remove a unit.
- **Presentation (Will, 2026-11-16):** "years" are called "experiences". Show the top three of everything first (top three
  neighborhoods in an experience, top three places in a neighborhood) with "show more" in descending rank. Voice: an HGTV
  show, a great realtor walking her through. Each neighborhood carries short attributed outside descriptions. Co-op rentals are out.
- **Page voice (Will, 2026-11-16, after walking through the preview):** a consumer experience, not B2B software. Do not
  explain the logic in running text; anything explanatory sits behind a tap ("See how we got this", collapsed by default).
  Crime is not a selling point: everything shown is already safe, so no crime rates or "low crime" wording in the open;
  only a brief "among the safest on the list" for the few that earn it. Promises say what life is like. Experience-level
  figures are medians, never ranges or averages. "Compared to staying in Queens", not "against". Under "What it costs
  you", one plain line saying what all-in includes.
- **Collapse to headlines (Will, 2026-11-16):** every section collapses to a headline that states its conclusion; expanding
  is the reader's choice. Target: any one place, neighborhood or experience fits in about 1.5 phone screens when collapsed.
  At experience level show the median as the headline figure with the range in small text beneath it.
- **Page feedback round 3 (Will, 2026-11-16):** no "Your host says" label anywhere: the text is "About this experience /
  About <neighborhood> / About the building", fully shown, scannable (icon points), never repeated lower on the page.
  A "See the neighborhoods" / "See the places" button sits near the top. Units group under their building; "Next" moves
  to the next building. "A day here" is a vertical stack of collapsible moments with green / yellow / soft red chips.
  Saving is unlimited ("My list"); compare any two or three ticked from the list; Save sits at the top and bottom of a
  building page. Each experience gets an illustration. Ratings from review sites are shown as information; no drop rule
  is applied until the owner chooses one.
