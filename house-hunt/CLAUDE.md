# Lamia House Hunt: instructions for agents

Restructured 2026-11-16 from the earlier chronological file. Nothing the owner (Will) decided was dropped: where two
decisions conflict the later one is the rule, and the earlier one is in the decision log at the end.

## What this is now

A data pipeline plus a published single-file decision page for one apartment search. The pipeline gathers sourced
listings and facts, applies Will's gates, costs and ranks what passes, and writes `site/data.json`. The page
(`site/index.html`, built to `site/dist/index.html`) walks Lamia through six "experiences", their neighborhoods, the
buildings and the apartments, and lets her keep a list and compare. **The job is the finished decision page.**

Start every session with `PROGRESS.md` (current state and counts). Then, as needed: `README.md` (quick start),
`docs/README.md` (index of documents and their authority order), `docs/ARCHITECTURE.md` (how the stages fit),
`scripts/README.md` (every script). The original brief, `docs/HANDOFF_2026-11-15.md`, is history: it still describes
who Lamia is, but its "data only" scope, tiers and caps are superseded.

**Authority, newest first** (a later document wins where two disagree): this file's rules and decision log →
`docs/RANKING.md` (its last sections are current) → `docs/PLAN_V4_MASTER_MODEL_2026-11-15.md` → `docs/SAFETY_BASIS.md`
→ `docs/PLAN_V3_APPROVED_2026-11-15.md` (gates, avoid thresholds) → UX brief and mock-up 4 (layout only).

## Working rules

1. **Never invent.** Every record carries a source URL and a retrieval time (UTC ISO 8601). Missing means `not_found`,
   plus where you looked (`notes` or `search_log`). Estimates are labelled (`value_type = estimate`, or basis
   `estimate`) with the method.
2. **Never take a price or a date from a search-result snippet.** Prices and availability come from the listing page
   itself, with its URL and the time it was seen.
3. **Respect terms and robots rules** (next section). Check `docs/SOURCES.md` before touching a source; record new
   findings there.
4. **Cache raw responses** in `raw/<source>/` (`scripts/lib.py: cached_get`) so normalization can be rerun without
   refetching. Raw captures above about 50 MB are not committed (see `.gitignore`); their download script must be able
   to recreate them.
5. **Scripts are idempotent and resumable.** Re-running a script must not duplicate rows. Write to disk as you go.
6. **Short excerpts only** from reviews and posts (one or two sentences), always with a permalink. Do not store usernames.
7. **Facts and opinions stay in separate fields.**
8. **Keep sources separate.** Never blend, for example, Zillow ZORI and HUD SAFMR into one number.
9. **Do not collect or score racial, ethnic or religious composition.** Resident quotes that mention diversity in
   general stay on the page; only quotes that single out residents by a named race, ethnicity, religion or national
   origin are left out (Will, 2026-11-16).
10. **Keep listings with unknown attributes.** A listing fails a gate only on a stated fact. An unstated gate fact
    makes it `pending`, and it stays in the data. Log the counts dropped at each gate (`data/gate_summary.md`).
11. **Collect nothing above $3,000 listed rent.** (The earlier "collect above the cap up to a stretch ceiling and tag
    the tier" no longer applies: cap and ceiling are both $3,000.)
12. **Stop and ask** when a key, a paid service or a scope judgment is needed. **Tell Will plainly** when a source is
    blocked or a target will not be met.
13. **Keep bulk data out of the agent's context.** Write to disk and read back summaries. Use one subagent per area or
    per source for parallel work.
14. Each phase ends with a commit, an updated `PROGRESS.md` and a coverage summary. Sub-agents do not commit: the
    coordinator sweeps their files.

## Robots and source rules

- **One refusal ends a host.** A 401, 403, 429, CAPTCHA or bot wall from a host ends every request to that host for the
  session, also after a restart. Persist it (`raw/_host_kill_shared.json`, or the script's own refused-hosts file) and
  say so in every agent brief. Never get around logins, CAPTCHAs, 403s or bot walls. Two lapses happened and were told
  to Will (the voices agent restarted after a Niche 403; evidence batch 13 sent six more Trulia requests).
- **Throttle**: default 1 request per second per host in `scripts/lib.py`; 2 s or more for listing and building sites;
  honour `Crawl-delay`. Prefer official APIs, bulk downloads, sitemaps and RSS.
- **robots.txt groups that name Claude apply to us and override `*`.** Bulk scripted harvests follow the ClaudeBot /
  anthropic-ai / Claude-Web groups. Low-volume lookups made for Will about a building or neighborhood already on the
  shortlist follow the site's Claude-User group if it has one, otherwise `*` (3 s or more apart, honest user agent).
- **Trulia is blocking us** (403 / CAPTCHA since the evening of 2026-11-15). Send no Trulia requests. Rows harvested
  from Trulia before the block stay, and cannot be re-read.
- **Off limits**: Yelp, Reddit (API key only; none yet), Nextdoor, Zillow listing and building pages, StreetEasy,
  Apartments.com, ApartmentRatings, RentHop, Realtor.com, Rent.com, HotPads, RentCafe and other Cloudflare-walled
  building sites, Google Maps, Craigslist by script (its terms prohibit it; pasted links are fine), municipal code
  hosts that bar Claude (ecode360, Municode, American Legal), the live Wikipedia API (use the dump). AppFolio listing pages and RealtyMX broker sites are off limits from 2026-11-17: their terms forbid automated collection (found in the trawl-2 probe; earlier reads of them stand as recorded, nothing more is fetched). Niche and
  City-Data are usable only for the targeted lookups above. The full list with reasons is in `docs/SOURCES.md`.
- Browser automation (headless Playwright) is allowed within these rules.

## Fixed parameters and gates, as they stand

- **Travel anchor**: Jamaica LIRR station, GTFS LIRR stop_id 102 (40.699608, -73.808530). Drive times are OSRM
  free-flow estimates, labelled as such. Closer to her parents is better.
- **Unit**: studio or one bedroom. Elevator buildings only; no detached houses are collected.
- **Money**: listed rent ≤ $3,000 **and** all-in ≤ $3,000. All-in = rent + required fees + pet rent + parking +
  estimated electric, gas and internet. Estimates are marked.
  - **Pet rent is always counted.** Where a building does not publish it, the line is an estimate: the median of the
    known pet rents in the same state.
  - Parking and required fees that are not published add nothing to all-in and are named on the receipt.
    `all_in_likely` adds the median known parking fee and required fees for those lines. It is shown beside the all-in
    figure and never used for the cap; where it passes $3,000 the unit carries the disclosure "Could pass $3,000 once
    parking and fees are known".
  - Where the listed price belongs to a lease longer than 13 months and the page gives the 12-month price, cost and cap
    use the 12-month price. A price is called net-effective only where the evidence says so; other offers carry the
    "special offer" disclosure.
- **Move-in**: available now through **December 15, 2026**. Tours start November 22.
- **Dogs**: explicitly allowed, with any weight limit ≥ 25 lb. "Small dogs" or "weight restrictions apply" with no
  number passes with the tour question "Confirm the dog weight limit in pounds". A stated limit under 25 lb, no dogs,
  or service animals only fails.
- **Elevator**: settled when confirmed on the building's own or its manager's page, stated on a listing page or a
  listing site's amenity list, on an official record, or by phone. "Inferred from height" is an open fact and needs a
  real building height of 6+ floors. An elevator named only on a listing site is marked `elevator_aggregator_only`.
  It becomes an open gate fact ("Confirm an elevator serves this apartment") for buildings in the reviewed doubt table
  `data/reference/elevator_doubt.csv`, and by rule for multi-building garden-style complexes (several building numbers
  in the unit labels and no height of 4+ floors on any page or record).
- **Floor**: no ground-floor units. A floor stated or confirmed as ground or 1, or a checker's reading that the unit is
  probably or possibly ground-level, excludes the unit. **An unpublished floor is not a strike**: it is a standing
  disclosure and tour question, "Floor not published: confirm it is above the ground floor".
- **Co-op rentals are out** (board approval may not fit the move-in date). A condo rented by its owner stays, as a disclosure.
- **Distance**: under 2 hours free-flow drive to Jamaica. Queens is included. Philadelphia is a benchmark only.
- **Safety**: a neighborhood is cut when its violent or its property crime rate is above Jamaica's precinct
  (9.8 / 25.0 per 1,000); lower ranks higher (`docs/SAFETY_BASIS.md`).
- **Staleness**: a listing page unchanged more than 60 days (and on no second site), or an availability date more than
  six months old, is one open item; unchanged more than six months (183 days), the unit is removed.
- **Open gate facts and disclosures.** Open gate facts are only: elevator; dogs allowed; whether the listing is real
  and available (availability, listing, eligibility). A missing live check is its own item. A unit is shown with at
  most one open item in all, marked with an asterisk that says what and why; two or more and it is not shown.
  Disclosures never count and never remove a unit: floor not published, lease term over 13 months, could pass $3,000,
  special offer, net-effective rent, condo rented by its owner, dog weight limit not published, overnight street parking.
- **Reviewed verdicts are required.** A unit is shown only if `data/evidence/review_verdicts.csv` holds an `ok`,
  `asterisk` or `disclose` verdict written against its evidence as it stands (`scripts/verdicts.py`); `remove` takes
  it out. `scripts/check_registry.py` fails the run otherwise. A building with no evidence rows is not shown.
- **Avoid cards**: up to 5 "looks good, but avoid" cards per neighborhood; thresholds are in plan v3 and
  `scripts/avoid.py` (management is judged on the last 6 months).
- **Selection**: every showable, reviewed unit is shown in rank order; up to 8 per building; candidate and phone-call
  lists stay at 2 per building. Ranking is v2 (`docs/RANKING.md`). Anything that passes the gates stays in the data.
- **Phone answers** (`data/evidence/call_answers.csv`, when present) outrank every other source.
- Experiences (six lifestyle groups, not locations), their names, neighborhoods and all wording come from the data.
  Nothing from the mock's text carries over. Jersey City is split into its neighborhoods; Newark is not.
- Publish as a **new private artifact**; never replace the mock.

## Presentation rules, as they stand

- **Experiences.** "Years" are called "experiences" in the interface; internal keys are unchanged.
- **Top three, then more.** Show the top three neighborhoods of an experience and the top three places of a
  neighborhood first, the rest on "show more" in descending rank.
- **Headlines first.** Every section collapses to a headline that states its conclusion; expanding is the reader's
  choice. Target: any one place, neighborhood or experience fits in about 1.5 phone screens when collapsed.
- **A consumer experience, not B2B software.** Voice: a great realtor walking her through, as on an HGTV show. Do not
  explain the logic in running text; anything explanatory sits behind a tap ("See how we got this", collapsed).
  Promises say what life is like. Calculations stay in the background.
- **About text.** No "Your host says" label anywhere. The text is "About this experience / About <neighborhood> /
  About the building", fully shown, scannable (icon points), never repeated lower on the page. A "See the
  neighborhoods" / "See the places" button sits near the top.
- **Buildings group apartments.** Units sit under their building; "Next" moves to the next building.
- **A day here** is a vertical stack of collapsible moments with green / yellow / soft red chips.
- **My list and compare.** Saving is unlimited ("My list"); compare any two or three ticked from the list; Save sits at
  the top and bottom of a building page.
- **No crime in the open.** Everything shown is already safe, so no crime rates or "low crime" wording in open text;
  only a brief "among the safest on the list" for the few that earn it.
- **Medians with the range beneath.** At experience level the headline figure is the median, with the range in small
  text under it; never an average. Figures are computed over the places shown.
- **Compared to staying in Queens** ("compared to", not "against"): five points with Queens in the centre.
- **What it costs you**: one plain line saying what all-in includes.
- **Illustrations.** Each experience has an original illustration (`docs/ILLUSTRATIONS.md`).
- **Photos are a link** out to the building's own site or the listing; listing photos are not copied.
- **Ratings are information.** Review-site ratings and counts are shown as they are; buildings never searched say "Not
  looked up yet"; no drop rule is applied until Will chooses one. There is no Google Places key, so the ratings census
  stays partial.
- Each neighborhood carries short attributed outside descriptions and resident quotes (rule 9 applies).
- Lamia will not be asked to react to the experiences before the page is finished.

## Standing instructions

- **Run everything that can run in parallel, at the same time, without being asked.** When only a couple of things are
  in flight, look for more independent work and start it. The aim is to wrap up. Parallel work must not edit files
  another running agent owns; give each agent its own output files.
- **Fix what does not land.** When something is visibly weak (an illustration, a line of text, a layout, a number that
  does not hold up), revise it without asking, then say what was changed. This does not cover Will's rules (gates,
  cap, safety rule, what is shown or dropped): those still go to him.
- **Keys never go in chat, code, data or logs.** The Census key lives outside the repo
  (`/root/.config/house-hunt/census_api_key`, read by `lib.census_key()`; `lib.redact()` strips it from logged URLs).
  The api.data.gov key is an environment network secret injected by the proxy. Ask Will when a new key is needed.
- **Push only to the session branch** (`claude/lamia-house-hunt-data-fdrkrs`).
- "Get what you can, say what's missing." Thorough over fast.

## Layout

- `seeds/`: hand-entered inputs. `raw/`: timestamped captures per source, each with `_index.jsonl`.
- `data/`: normalized CSVs (`docs/DATA_DICTIONARY.md`); `data/evidence/`: the evidence pass; `data/reference/`: lookup
  and reviewed tables; `data/voices/`: resident quotes.
- `scripts/`: pipeline, harvesters, tests (`scripts/README.md`). `site/`: page template, data, built page, screenshots.
- `docs/`: rules, notes, checks and repairs (`docs/README.md`). `out/`: call sheet, tour days, re-check outputs.

## Decision log

Decisions by Will that changed or replaced an earlier one. Dates are UTC days of the session; "brief" is the handoff brief.

| Date | Decision | Replaces |
|---|---|---|
| 2026-11-15 | Stretch ceiling is $3,000 listed rent; collect nothing above it | Brief: $2,800 cap, $3,200 ceiling, tiers |
| 2026-11-15 | Move-in by December 1 | "December only", which replaced the brief's "December preferred, January latest" |
| 2026-11-15 | Move-in window: now through December 15; tours from November 22 | Move-in by December 1 |
| 2026-11-15 | All-in cap $3,000 including estimated utilities | Listed-rent cap only |
| 2026-11-15 | Dogs must be explicitly allowed, limit ≥ 40 lb | Brief: keep unknown, drop only "no dogs" |
| 2026-11-15 | Dog limit lowered to 25 lb; "small dogs" with no number passes with a tour question | Limit ≥ 40 lb |
| 2026-11-15 | Elevator buildings only, no ground-floor units | Brief: drop only walk-ups above one flight |
| 2026-11-15 | Queens excluded, then re-included | Queens excluded |
| 2026-11-15 | The job is the finished decision page (plan v3) | Brief and old CLAUDE.md: "data only; do not build UI, rank or recommend" |
| 2026-11-15 | Years group by lifestyle, not location | Grouping by drive band and setting (rejected at checkpoint A) |
| 2026-11-15 | Safety: violent crime above Jamaica's precinct cuts; property above it is a flag | No rule |
| 2026-11-15 | Safety, final: neither violent nor property crime may exceed Jamaica's precinct | Property as a flag only |
| 2026-11-15 | Ranking v2: many more variables, drop anything sketchy; 70% universal + 30% promise | Ranking v1 (six parts) |
| 2026-11-15 | Elevator may be inferred for 6+ floors, with an asterisk | — |
| 2026-11-15 | Shown: not an avoid building and at most one thing still open | Shown with "every gate fact stated" |
| 2026-11-15 | Co-op rentals are out | — |
| 2026-11-15 | Closer to her parents is better, coloured like any other measure | UX brief: no red or green on distance |
| 2026-11-15 | Up to 10 places and up to 5 avoid cards per neighborhood | — |
| 2026-11-15 | Robots groups naming Claude apply to us; targeted lookups follow Claude-User or `*` | Following `*` only; then "every Claude group binds everything" |
| 2026-11-15 | One refusal ends a host for the session | — |
| 2026-11-15 | Browser automation allowed; Philadelphia benchmark only; no Google key (drive times stay free-flow estimates); a Reddit app is the only further key planned | — |
| 2026-11-16 | Open gate facts are only elevator, dogs, listing real and available; the rest are disclosures | Check-2 list that counted floor, lease term, cost near the cap and condo as open items |
| 2026-11-16 | An unpublished floor is a tour question, not a strike | Unknown floor as an open fact |
| 2026-11-16 | No cap of 10 per neighborhood: every showable, reviewed unit is shown | Up to 10 places per neighborhood |
| 2026-11-16 | Up to 8 units per building, grouped under the building | At most 2 per building |
| 2026-11-16 | Pet rent always counted, estimated where unpublished; `all_in_likely` shown, never used for the cap | Unknown pet rent adding nothing; "cost near the cap" disclosure |
| 2026-11-16 | Elevator doubt table and garden-style rule | Tag-only elevator always "stated" |
| 2026-11-16 | Staleness is a rule (60 days: open item; six months: removed) | Caught only by the verdict review |
| 2026-11-16 | "Years" are "experiences"; top three first, then "show more" | "Years"; flat lists of ten |
| 2026-11-16 | Experience figures: median as the headline, range in small text beneath | "Medians, never ranges or averages" (earlier the same day) |
| 2026-11-16 | No "Your host says" label; "About ..." text | A host voice labelled on the page |
| 2026-11-16 | Saving is unlimited ("My list"); compare two or three from it | Hold up to three (plan v3, mock-up 4) |
| 2026-11-16 | Ratings shown as information; no drop rule; no Google Places key | Idea of dropping buildings with too few reviews |
| 2026-11-16 | Diversity quotes stay; only quotes singling out a named group are left out | Filter that dropped any quote characterising residents by group |
| 2026-11-16 | Fix what does not land without asking (not the owner's rules) | — |

- **Thin neighborhoods (Will, 2026-11-16):** a neighborhood that would show exactly one apartment is cut unless that
  apartment is well attested (a real apartment with no open gate fact) and promising (rank score at or above its experience's median).
  Implemented in `scripts/rank.py`; reason `thin_neighborhood`.
- **Real apartments only (Will, 2026-11-16):** a floor plan, a "from $X" building offer, a row with no individual unit,
  or a room in a shared suite is not an apartment and is never shown or counted (status `not_an_apartment`).

- **No "not re-checked" flag (Will, 2026-11-16):** a listing that was simply never re-read is not an open item, carries
  no asterisk for it, and does not count against an apartment in any rule. A re-read that found a problem still counts.
  The fourth independent check was cancelled at the owner's request.

- **Overnight accuracy pass (Will, 2026-11-16):** the owner asked that the published page be accurate, re-authorised the
  independent check that had been cancelled, said data that needs updating should be updated, and that work may run as
  long as needed. The front tutorial is restored. The "not re-checked" flag stays removed. Trulia stays untouched.

- **Rent versus total, and filters (Will, 2026-11-16):** wherever a price appears, show both the base rent and the total
  with utilities and fees, clearly labelled. Filters (price and others) are a visible, first-class control on the first
  screen, experience and neighborhood pages and My list. Updating the publicly shared page needs the owner's go-ahead
  (an automated publish to a page shared by link was blocked while he was away).

- **12-month price (2026-11-16, after the live re-read):** the $3,000 total is tested on the 12-month price whenever the
  page gives one and it differs from the listed price, whatever lease the listed price is quoted on (this replaces any
  earlier wording about "a lease longer than 13 months"). Where a sibling apartment's 12-month price is more than 15%
  above its listed price and a unit has no 12-month price of its own, the unit carries one open "listing" fact.

- **Publishing (Will, 2026-11-16):** "You can go ahead and overwrite what's already been published." Republishing the
  shared page to the same link is approved; check the build loads cleanly first.

- **The concierge draft (Will, 2026-11-17):** a second, separate page ("the short version") is built on the same data
  and published as its own artifact; the first page, its link, its template and its data are not changed by that
  work. On the new page only: nothing above **$2,000 listed base rent** is shown (the pipeline and the first page keep
  $3,000); a neighborhood with exactly one apartment is shown but is never its own stop, it is parked under the
  nearest larger neighborhood in the same experience. The experiences stay the front door ("what kind of life do I
  want next year?"); the page recommends five buildings to tour and she keeps or swaps. Design and data contract:
  `docs/CONCIERGE_DESIGN.md`.

- **The short version, version 2 (Will, 2026-11-17):** questions first, asked about her life (visits, longest drive,
  room to work, Saturday night, the dog's walk, the car, a comfortable monthly total, the two that matter most), then
  straight to the places that fit; each place names its experience and says what life there is like, with sourced
  local detail; saved places and Compare sit in a bar on every screen. The stories stay reachable but no longer stand
  in front of the matches. Spec: "Version 2" in `docs/CONCIERGE_DESIGN.md`.

- **Second trawl (Will, 2026-11-17):** collect nothing above **$2,200 listed base rent** (the $3,000 total test is
  unchanged). The short version still **shows up to $2,000**. Priority areas: New Jersey, Brooklyn, Connecticut,
  Long Island (Nassau/Suffolk), Long Island City. **Floor and elevator, replacing "elevator buildings only":** a
  building without an elevator is allowed when the apartment is on floor 2 (one flight up); the ground floor stays
  out; floor 3 and above need an elevator; with no elevator stated and no floor stated, that is one open gate fact
  ("Confirm the floor, and whether there is an elevator"). Trulia stays closed: a person solving its CAPTCHA for our
  tools would be getting around a bot wall. Listings Will or Lamia find by hand go in `inbox/` (any site, saved by
  them). Plan: `/root/.claude/plans/linear-hatching-swan.md` (copied in `docs/TRAWL_2_PLAN.md`).
