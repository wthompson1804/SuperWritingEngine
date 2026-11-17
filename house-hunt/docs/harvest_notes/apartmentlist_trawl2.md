# Apartment List, second trawl (2026-11-17)

Script: `scripts/h_apartmentlist.py --trawl2 --max-age-hours 24 --fetch-max-low 2200 --max-drive 120`.
Output: `data/listings_raw/apartmentlist.csv` (same 41-column contract). Gone units: `raw/apartmentlist_trawl2/gone_units.csv`.
Snapshot of the CSV before the run: `raw/apartmentlist_trawl2/apartmentlist_before.csv`. Run log, per-page check state,
stats and the summary behind the numbers below: `raw/apartmentlist_trawl2/` (`run.log`, `_checked.json`, `stats_pass1.json`,
`summary.txt`) and `raw/apartmentlist/_harvest_stats_trawl2.json` (pass 2). Earlier run stats kept as `_harvest_stats_run4.json`.

## Access

- robots.txt re-read 2026-11-17 16:49 UTC (copy: `raw/apartmentlist_trawl2/robots_2026-11-17.txt`): unchanged, one `*` group,
  `Allow: /`, the same eight Disallow lines, no group naming Claude, no Crawl-delay.
- Throttle unchanged: 2.5 s between requests, plain fetch. 2,754 requests 16:49–18:48 UTC (1,326 search pages, 1,428 property
  pages) plus the robots.txt read. **Every response HTTP 200; no 401/403/429/CAPTCHA; nothing written to `raw/_host_kill_shared.json`.**
  One connection error (ChunkedEncodingError on the first Manhattan search page) was not retried in pass 1; pass 2 read Manhattan.
- Stop at first refusal: `fetch()` now calls `cached_get(..., retries=1)` (lib would retry a 429 three times), raises on
  401/403/429/challenge pages or a host already in the kill file, and writes the host into `raw/_host_kill_shared.json` before stopping.

## What changed in the script

- `MAX_RENT = 2200`: no new unit above $2,200 listed base rent is added. `HELD_MAX = 3000`: units already held (the first page
  keeps $3,000) are refreshed at their current price when their property is re-read.
- `--max-age-hours 24`: a cached search or property page older than 24 h is refetched, so `last_seen`, prices and dates are today's.
- Order: priority areas first (New Jersey 208 cities, Brooklyn, Connecticut 26, Long Island 95, Long Island City), then the rest of
  the grid (57 cities). Apartment List has no Long Island City city page in its sitemap; LIC properties sit under `ny/queens`, so
  LIC was covered by re-reading every held LIC property in priority order and by the Queens search (first city of the rest).
- After each group's cities, every held property with a unit at or under $2,200 that no search page led to is re-read too
  (NJ 16, Brooklyn 5, CT 5, LIC 8, rest 80), so a unit is never assumed gone just because search stopped showing it.
- A property is skipped without a detail fetch only when its search-page low price is above $2,200 **and** it holds no unit at or
  under $2,200 (1,133 skipped). Their held $2,201–3,000 rows (2,208) were not re-read and keep `last_seen` 2026-11-15.
- Changed rent or date is noted on the row: `trawl2: listed_rent was X on 2026-11-15`, `trawl2: available_date was ...`.
- Unit labels are written exactly as the page gives them (`unit`); `floor` stays `unknown` (the page has no floor field), and
  elevator is still read only from the amenity list or description, never from a unit label.

## Gone units (the Zumper convention: removed from the CSV, counted, kept in a ledger)

A held unit is gone when its property page, re-read today, no longer lists it. It is removed from `apartmentlist.csv`, so the
merged listings drop it, and written with `gone_at`, `gone_reason`, `gone_page_status`, `rent_on_page_now` to
`raw/apartmentlist_trawl2/gone_units.csv` (kept outside `data/listings_raw/` because `gates.py` merges every CSV there).

| reason | units |
|---|---|
| unit no longer listed on its property page | 127 |
| property page says "404: This page could not be found" (Next.js soft 404, served with HTTP 200) | 18 |
| rent on the page is now above $3,000 | 1 |
| **total** | **146** (88 were at or under $2,200, 58 at $2,201–3,000) |

The soft 404 was found during the run: the property page answers 200 with `NEXT_HTTP_ERROR_FALLBACK;404`. The parser now treats
that marker as "page gone"; pass 2 re-read those pages from the fresh cache (no new request). One possible id change: unit "1A"
at `p12508` left as id `-4-625` and a new id `-4-246` with the same label and rent appeared; both are kept as the page gives them.

## Result (rows at or under $2,200, all seen 2026-11-17)

| area | ≤ $2,000 new | ≤ $2,000 held | $2,001–2,200 new | $2,001–2,200 held | total |
|---|---|---|---|---|---|
| New Jersey | 43 | 730 | 15 | 298 | 1,086 |
| Brooklyn | 3 | 82 | 0 | 14 | 99 |
| Connecticut | 9 | 291 | 2 | 59 | 361 |
| Long Island (Nassau, Suffolk) | 1 | 24 | 0 | 16 | 41 |
| Long Island City | 1 | 7 | 0 | 0 | 8 |
| Bronx | 1 | 71 | 0 | 21 | 93 |
| Manhattan | 3 | 55 | 0 | 10 | 68 |
| Queens (other) | 1 | 29 | 0 | 10 | 40 |
| Staten Island | 1 | 19 | 0 | 3 | 23 |
| New York (other: Westchester, Rockland, Hudson) | 2 | 63 | 2 | 21 | 88 |
| Pennsylvania | 1 | 5 | 2 | 6 | 14 |
| **total** | **66** | **1,376** | **21** | **458** | **1,921** |

- Rows in the CSV: 4,885 (before 4,944; −146 gone, +87 new). 2,677 rows seen today; 1,764 of the ≤ $2,200 rows are available
  now or by 2026-12-15.
- Price changes on held units re-read today: 125 down, 58 up; 5 held units fell from above $2,200 to at or under it; 40 dates changed.
- Area is by ZIP (Brooklyn 112xx; LIC 11101/11109/11120; Long Island 110xx except 11004/11005, 115xx, 117–119xx).

Brooklyn and LIC stay thin on Apartment List at this price, as the plan expected; the gain is mostly NJ and CT.
