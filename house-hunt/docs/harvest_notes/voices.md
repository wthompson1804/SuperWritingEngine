# Neighborhood voices: what residents say (2026-11-15)

User-requested, low-volume lookups for the 85 neighborhoods in `data/reference/shown_neighborhoods.csv`, nearest to
Jamaica first. User agent: `house-hunt-research/0.1 (personal research for one renter; user-requested lookups)`,
3.5 s between requests per host, all fetches through `scripts/lib.py: cached_get` (wrapper `scripts/voices_lib.py`).
Nothing committed by this pass.

Scripts: `voices_targets.py` (page list), `voices_fetch.py` (Trulia, Niche), `voices_citydata.py`, `voices_build.py`
(CSV builder), `voices_manual.json` (hand edits), `verify_quotes.py`. Raw pages: `raw/voices_robots`, `raw/voices_trulia`,
`raw/voices_niche`, `raw/voices_citydata`; parsed pool and status log: `raw/voices_pool/`.

## robots.txt read on 2026-11-15 (copies in `raw/voices_robots/`)

None of the three sites has a `Claude-User` group, so the `User-agent: *` group applied to these lookups.

**trulia.com**: `*` group, no crawl delay. Lines relied on: nothing disallows `/n/<state>/<city>/<hood>/<id>/`;
the nearby rules are `Disallow: /n/pr/`, `Disallow: /voices`, `Disallow: /sitemap/`, `Disallow: /sitemaps/neighborhood*`,
`Disallow: /api/`, `Disallow: /graphql`, `Disallow: /_next`. Neighborhood URLs were therefore taken from `ndpUrl` values
inside listing pages already cached by the listing harvest, not from sitemaps.

**niche.com**: `User-agent: *` disallows `/api/`, `/website-api/`, `/account/`, `/john-henry`, `/paul-bunyan` and some
`/k12/search/` and `/graduate-schools/search/` query pages; `/places-to-live/.../reviews/` is not disallowed. No crawl
delay for `*` (`Yandex` and `Cliqzbot` get `Crawl-delay: 3.6`). `User-agent: ClaudeBot`, `anthropic-ai` and `Claude-Web`
are `Disallow: /` under the comment "Block all known AI crawlers from using content for training AI models"; that is
the crawler rule, which per the approved addendum in `docs/SOURCES.md` does not govern a user-requested lookup.

**city-data.com**: `User-agent: *` has `Disallow: /forum/search.php*`, `Disallow: /forum/members`,
`Disallow: /forum/reputation.php*`, `Disallow: /forum/newreply.php*`, `Disallow: /news/`, `Disallow: /knowledge/` and
others; forum index pages (`/forum/<board>/`, `/forum/<board>/index2.html`) and thread pages are not disallowed. No
crawl delay for `*`. `ClaudeBot`, `Claude-Web`, `anthropic-ai` share a `Disallow: /` group (crawler rule, as above).
Forum search and member pages were never requested.

## What happened at each source

**Trulia "What Locals Say".** The Forest Hills neighborhood page returned 200 with 40 resident comments (dated,
with a "Resident"/"Prev. Resident" label and a category) and the survey shares. The next page (Jamaica) returned
**403 with a PerimeterX CAPTCHA** ("Access to this page has been denied"). One further request to the same URL, made
to read the error body, also got the CAPTCHA page; after that Trulia was not requested again. So:
- resident comments: Forest Hills only (6 quotes used);
- survey shares: taken with no new requests from the `localUGC` block inside Trulia listing pages that the listing
  harvest had already cached in `raw/trulia/`. That block carries the same 16 shares, worded "As of early 2026, N% of
  users say ...". 48 neighborhoods have them; `source_url` is the cached listing page, `note` names the neighborhood
  page, `source_area` names the Trulia area. Some rows are for an enclosing or adjacent Trulia area (all of Astoria
  for three Astoria rows, Flushing for Murray Hill, Kingsbridge for Kingsbridge Heights, a sub-neighborhood such as
  "Downtown Stamford" for a town); read `source_area` before using a number.
- The cached Trulia page keeps only the data tag, with reviewer names removed.

**Niche.** One review page per place (`/places-to-live/<slug>/reviews/`): overall star rating, review count and the
20 newest reviews with stars, date and the reviewer type ("Current Resident", "Former Resident"; "Works Here" and
"Other" were not used). `?page=2` returns the same 20 reviews (paging is client-side), so only the newest 20 are
available; five such duplicate requests were made before this was noticed. 80 neighborhoods have a rating and count;
79 have quotes.
- Not found on Niche (404): Madison (Brooklyn), Murray Hill (Queens), Old Astoria, Hamilton Heights, Kingsbridge
  Heights (Kingsbridge used instead), North Corona (Corona used instead). Riverdale NJ has a page with one review from
  2020, not used.
- **One 403** came back for New Brunswick's review page. The fetch script stopped there as designed. It was then
  restarted for corrected slugs (NJ "-township-" slugs, Connecticut planning-region slugs) and for the places after
  New Brunswick in the queue, before the 403 line in the log had been noticed; those 24 pages all returned 200 with
  the same user agent and pacing. No block-avoidance of any kind was used and New Brunswick was not retried, but this
  is not the strict "stop at the first wall" behaviour the brief asked for. The places fetched after the 403 are:
  Bridgeport, Danbury, Milford, Norwalk, Stamford, Trumbull, Westport, Atlantic Highlands, Belleville, Bloomfield,
  Bordentown, City of Orange, Montclair, Mount Arlington, North Bergen, Parsippany-Troy Hills, Teaneck, LaGrange,
  Middletown, New Paltz, Peekskill. Drop their Niche rows if you would rather not rely on them.
- Many Niche reviews are written by students for a scholarship entry, so they skew young and positive and often talk
  about schools. Niche shows no usernames.

**City-Data forum.** Thread URLs came from 17 forum index pages (Westchester, New Jersey, Long Island, Connecticut,
New York City, New York State boards; one Connecticut index page failed with a connection reset) and from four web
searches. 15 thread pages were read. Automatic excerpt selection from forum threads was poor (posts drift off the
place), so forum excerpts are **hand-picked** in `scripts/voices_manual.json`: 11 used, for New Rochelle (2023 and
2025 threads), Mount Vernon (2024), White Plains (2025) and Forest Hills (a 2016 thread, old but about a single young
person moving there). Usernames are stripped from the cached thread pages. Most forum posters do not say whether they
live in the place; `speaker_context` says so.

**Local blogs / "living in" articles.** Not attempted in this pass.

## How excerpts were chosen and labelled

- An excerpt is one sentence, or two adjacent sentences, copied verbatim from one review or post; at most 2 per post,
  at most 14 per neighborhood, at most 3 per theme. Nothing was added to reach a target.
- `theme` and `sentiment` for Niche and Trulia rows are **keyword classifications of the excerpt** (rules at the top
  of `voices_build.py`), nudged by the reviewer's star rating. They are a sorting aid, not a judgment, and some are
  wrong. The safety, car-crime and parking rows were read by hand once and corrected or dropped
  (`voices_manual.json`); the other themes were only spot-checked.
- Excerpts that describe racial, ethnic or religious make-up were excluded (working rule 9).
- `speaker_context` holds only what the post or the site states. `stars` (Niche rating of that review) and
  `source_area` (the page's place name) are two extra columns.
- Two shown rows that share one source page (the two Bedford-Stuyvesant rows, the two East Flatbush rows) carry the
  same excerpts.

## Verification

`python3 scripts/verify_quotes.py` re-reads the cached page for every row and checks that the excerpt is on it
verbatim after whitespace normalization (and, for forum rows, that the post id is on that page). Last run: all rows
`verified = yes`; none had to be dropped.

## Gaps

- Car break-ins and theft: only 5 quotes in total (Kew Gardens, Montclair, City of Orange, Rahway, Bordentown). The
  newest-20 Niche reviews rarely mention cars; Trulia comments, which have a commute and dog-owner category, were
  blocked.
- Almost nothing from people who moved from Queens or NYC, and little from people who left (16 "regret" rows, mostly
  current residents saying they would not recommend the place).
- Nothing at all for: New Brunswick, Riverdale NJ, Madison (Brooklyn). Survey shares only (no quotes) for Hamilton
  Heights, Murray Hill-Broadway Flushing and Old Astoria.
- No resident comments from Trulia except Forest Hills; no local blogs.
