# Neighborhood voices, round 2 (2026-11-15, 23:49 to 23:58 UTC)

Round 1 (`voices.md`) covered 79 of an earlier 85-neighborhood list. The decision page now lists 127
(`site/data.json` → `neighborhoods`). This pass looked up the **56** page neighborhoods that had no row in
`data/voices/neighborhood_quotes.csv`, most shown units first.

Result: **52 of 56 now have quotes** (507 rows; 484 distinct excerpts, because the three Gravesend rows share one
page and two Harlem-area rows share another). 4 still have none (see "Still nothing").

Everything is in one script, `scripts/voices_round2.py` (`targets`, `niche`, `citydata`, `build`). Outputs, all new
files: `data/voices/neighborhood_quotes_round2.csv`, `neighborhood_survey_round2.csv`, `coverage_round2.csv` (same
columns as round 1). Raw: `raw/voices_round2_niche/`, `raw/voices_round2_citydata/`, `raw/voices_round2_robots/`,
and `raw/voices_round2/` (`_status.jsonl` request log, `pool.jsonl` parsed reviews, `_host_kill.json`).
Round 1 files, other scripts, master data and `site/` were not touched. Nothing committed by this pass (a
coordinator snapshot commit picked the files up while the work was in progress).

## Rules as enforced in code

- User agent `house-hunt-research/0.1 (personal research for one renter; user-requested lookups)`; all requests via
  `scripts/lib.py: cached_get`; 4 s per host (more if robots gives a crawl delay; neither site gives one for our group).
- robots: read fresh at the start (copies in `raw/voices_round2_robots/`). Neither niche.com nor city-data.com has a
  `Claude-User` group, so `*` applied, as in round 1. Every URL is checked against it before the request.
- Host allow-list: only `www.niche.com` and `www.city-data.com` can be requested; trulia.com and the other
  off-limits sites cannot be requested by this script at all.
- **Kill flag**: any 401/403/429/503, CAPTCHA or bot-wall page, or a connection reset, writes the host into
  `raw/voices_round2/_host_kill.json`. The fetch function refuses that host from then on, in that process and in
  every later run; nothing clears the file. URLs already tried (including 404s) are never requested twice.

## What happened at each source

**Niche** (`/places-to-live/<slug>/reviews/`): 56 requests, 49 pages returned 200, 7 returned 404 (guessed
slugs that do not exist: manhattan-valley, hillcrest, pomonok, homecrest, manhattanville, west-harlem, ditmas-park).
**No refusal.** One or two requests per neighborhood. Each page gives the overall rating, the review count and the
newest ~19 reviews; only "Current Resident" and "Former Resident" reviews are used.
- **New Brunswick's Niche page was not requested**: it is the one URL that answered 403 in round 1.
- Pages cached by round 1 were re-read with no new request for: Washington Heights (South) ← "Washington Heights
  (whole)"; Old Astoria-Hallets Point ← "Astoria (enclosing area)"; Murray Hill-Broadway Flushing ← "Flushing
  (enclosing area)"; Hamilton Heights-Sugar Hill and Manhattanville-West Harlem ← "Harlem (enclosing area)";
  Flatbush (West)-Ditmas Park-Parkville ← "Flatbush (whole)". These are the same city and the enclosing named
  neighborhood, not the exact sub-area: `source_area` says so on every row (62 rows). Filter on "enclosing" or
  "whole" in `source_area` to leave them out. Their excerpts repeat ones round 1 already shows for the neighboring row.
- **Wallkill dropped**: the Niche page `wallkill-orange-ny` returned 200, but its reviews talk about New Paltz and
  the Shawangunk ridge, which is the hamlet of Wallkill in Ulster County, not the Town of Wallkill by Middletown
  where the listing is. Different municipality, so no rows and no rating were kept.
- Willowbrook's URL returned the place page with no reviews; not used. Spuyten Duyvil (9 reviews), St. George (8),
  New Brighton (6), South Slope (2) and Garwood (11) have few reviews, so few quotes.

**City-Data forum**: used only where Niche gave nothing. Thread URLs came from four web searches (forum search is
disallowed and was not used). 5 requests: 4 thread pages returned 200 (two New Brunswick threads, two
Ditmas Park / Flatbush threads); the **5th request (a Manhattanville thread) ended in "connection reset by peer"**.
That is not a 403 or a CAPTCHA, but it was treated as a refusal to be safe: the host is in the kill file and was
not requested again, so the Manhattanville and Electchester/Pomonok threads were never read. 9 forum excerpts were
hand-picked (New Brunswick 6, Ditmas Park 3). They are old (2014 to 2020; the date is on each row), and most posters
do not say whether they live there (`speaker_context` says what the post states). Usernames were removed from the
cached thread pages.

**Trulia**: not requested.

## How excerpts were chosen, labelled and checked

- Same method and limits as round 1: one sentence or two adjacent sentences, verbatim; at most 2 per review, 14 per
  neighborhood, 3 per theme. Keyword rules (copied from round 1's `voices_build.py`) propose theme and sentiment.
- **Read by hand**: every safety, car-crime and parking row, and then every other row once. 80 drop patterns were added
  (off-topic, about schools only, garbled, about the writer rather than the place, or about a different
  place) and 23 themes and 59 sentiments were corrected. The lists are `DROP`, `THEME_FIX`, `SENT_FIX` in the
  script. Rows picked to replace dropped ones were read too. The non-safety themes are still partly keyword
  labels; expect a few loose fits, mostly in `people` and `social_life`.
- Composition: the word filter from round 1 was widened (it now also drops excerpts using "diverse", "culture",
  "background", "church" and similar), and rows that described who lives there by origin or language were dropped by hand.
- No usernames (Niche shows none). Excerpts that revealed much about the writer (age and household, job) were dropped.
- **Verification** is part of `build`: for every row the cached page is re-read and the excerpt must be on it
  verbatim after whitespace normalization, with a date; forum excerpts must sit inside the cited post's own message
  block. Rows that fail are not written. Last run: 507 written, 0 failed, all `verified = yes`.
- Permalinks: the Niche review page (Niche has no per-review link); for the forum, the thread page plus `#post<id>`.

## Counts

By theme: safety 88, people 85, social_life 82, dogs_green 66, travel 58, value 51, noise 44, parking 14,
regret 12, surprise 4, car_crime 3. By source: niche.com 498, city-data.com/forum 9.
Survey file: 110 rows (Niche overall rating and review count for 55 place pages).

## Gaps

- **Still nothing**: Madison (Brooklyn) (no Niche page; no thread looked for), Pomonok-Electchester-Hillcrest
  (no Niche page; the City-Data threads found were not read because the host was stopped), Riverdale NJ (Niche has
  one review from 2020), Wallkill (Niche page is about a different Wallkill).
- **Thin**: St. George-New Brighton (2 quotes), New Brunswick (6, forum only, 2016 and 2020), Flatbush
  (West)-Ditmas Park (3 forum quotes about Ditmas Park from 2014-2015, the rest is all of Flatbush).
- Car crime is again nearly absent (3 rows: Maplewood, Oxford, Ditmas Park). Parking has 14 rows.
- "Moved from Queens/NYC": only incidental (a South Orange reviewer who lived in NYC 17 years; a New Brunswick
  forum poster who moved out of Manhattan). No row carries a "moved from" tag in `speaker_context`.
- Niche reviews skew young and positive (many are written for a scholarship entry), as noted in round 1.

## For docs/SOURCES.md (not edited by this pass)

- Niche: 56 more review-page requests at 4 s spacing, no refusal. NYC sub-neighborhood slugs often do not exist (404).
- City-Data: connection reset on the 5th thread page of this pass (round 1 also saw one reset on an index page).
  Treated as a stop for the host.
