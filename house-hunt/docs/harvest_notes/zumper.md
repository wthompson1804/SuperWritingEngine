# Zumper harvest notes (2026-11-15)

Script: `scripts/h_zumper.py`. Output: `data/listings_raw/zumper.csv`. Raw pages: `raw/zumper/` (HTML is git-ignored;
`_index.jsonl`, `cities.json`, `cards.jsonl`, `targets_map.json`, logs are kept).

## Targets run, 2026-11-15 19:06–19:26 UTC (latest state; supersedes the counts further down)

`python3 scripts/h_zumper.py targets data/reference/detail_targets_zumper.csv --no-follow`

- All 451 target rows processed, nearest-first, one fetch per row: 131 building pages and 224 unit pages
  fetched, 96 reused from cache (same day). All HTTP 200, **no bot wall**. Total requests to date about 1,765.
- CSV now has **3,692 rows** (749 studios, 2,943 one-bedrooms; NJ 1,975, NY 1,274, CT 431, PA 12):
  **1,314 detail**, 2,378 card. 282 new unit rows came from building pages (active studio/1BR floor plans
  ≤ $3,000 that search cards had not listed one by one); 78 rows were removed because the page showed the unit
  inactive, over $3,000 or 2+ beds.
- Building facts are applied across rows at the same street address + ZIP: dogs only from a building page with a
  visible policy block (2 rows), elevator from any detail page (20 rows); each is noted in `notes`.

Rows that the target file pointed at (508 before; 430 remain, 78 removed as above):

| field | before | after |
|---|---|---|
| detail_level=detail | 111 | 430 |
| dogs yes / no / unknown | 202 / 0 / 306 | 188 / 42 / 200 |
| elevator yes / unknown | 351 / 157 | 282 / 148 |
| unit floor | 15 | 41 |
| unit number | 68 | 195 |
| available_date | 70 | 53 |
| building_floors | 8 | 10 |
| dog weight limit | 1 | 12 |
| pet rent / parking fee | 3 / 1 | 51 / 23 |
| utilities_included | 4 | 29 |
| fee details (`other_monthly_fees_json`) | 104 | 396 |
| listing_age_days | 111 | 430 |
| dog-policy CONFLICT notes | 0 | 5 |

Whole file, before → after: dogs yes 972 → 1,177, no 111 → 160, unknown 2,405 → 2,355; elevator yes 482 → 592;
floor 82 → 119; available_date 733 → 724; weight limit 5 → 42; pet rent 9 → 169; fee details 652 → 1,226;
CONFLICT notes 20 → 27. 615 `dogs=yes` rows still rest on Zumper's pet code alone (see below).

Why some counts fell: the elevator and date counts drop because the 78 removed rows carried them. Among the 430
surviving rows, dates are unchanged (53) and elevator went 284 → 282 (two building cards had an Elevator tag
that the building page does not show). 200 target rows still have dogs unknown: their
pages show no pet policy block and no pet code.

## State at the first hand-off (before the targets run)

- **3,488 rows** (697 studios, 2,791 one-bedrooms), all with listed rent ≤ $3,000 and a ZIP in the search grid.
  NJ 1,815, NY 1,273 (New York City 650-odd), CT 388, PA 12. 658 distinct ZIPs.
- **709 rows are `detail_level=detail`** (price, date, policy read from the listing or building page).
  **2,779 rows are `detail_level=card`**: price comes from the search-result card only. The coordinator stopped the
  per-listing detail crawl part-way (it had read about 770 of 3,454 detail pages, nearest-first, so the detail
  rows are the ones closest to Jamaica: Queens, then the rest of NYC and nearby Nassau/Hudson County).
  Card rows must not be shown as verified until `targets` mode reads their page.
- City search is **complete** for the whole grid.

## robots.txt (read 2026-11-15, saved as `raw/zumper/robots.txt`)

- No group names ClaudeBot, Claude-User, Claude-SearchBot or anthropic-ai, so group `*` applies. No Crawl-delay
  for `*`. We used 2.2 s between requests.
- `*` disallows `/api`, `/json`, `/map`, `/listing-feed`, `/static`, `?box=`, `?bedrooms=`, `?bathrooms=`,
  `?listingId=`, `?loc=`, `?s=`, `/apartment-for-rent/` (singular), `/gallery`, `*/cost-calculator`,
  `*/schedule-tour` and others. None of these were requested.
- `?page=` is disallowed only in the googlebot group, not in `*`; it was used for pagination.

## URL patterns used

| purpose | pattern |
|---|---|
| search | `/apartments-for-rent/<city-slug>/1-beds/under-3000` and `/studios/under-3000`, plus `?page=N` (50 per page) |
| unit detail | `/listings/<id>p/<slug>` |
| building detail | `/apartment-buildings/p<id>/<slug>` |

- Path filters `/studios`, `/1-beds`, `/under-3000` exist and work (the page's embedded query shows
  `bedrooms {min,max}` and `price.max 3000`). A combined `/studios-1-beds` path does **not** work (it is read as a
  neighbourhood slug and returns 0), so each city takes two requests. ZIP pages (`/<city>/<zip>/...`) and
  neighbourhood pages also exist but were not needed.
- All data comes from the `window.__PRELOADED_STATE__` JSON in the HTML, plus the visible "Policies and fees"
  and amenities text of detail pages.

## Coverage

- Cities were discovered from Zumper itself: each search page carries 20 `nearby_cities` with coordinates and
  per-bedroom inventory counts. Starting from 18 seeds, the crawl walked outward nearest-first and kept every
  city within 8 km of a grid ZIP centroid. The sitemap was not needed.
- 898 cities seen; 768 in the area: **453 searched**, 315 skipped because Zumper's own counts showed no
  studios or 1BRs (or no listings); 130 outside the area. 636 search pages. No grid ZIP is more than 10 km from a
  searched city except NYC ZIPs, which the city-wide `new-york-ny` search covers.
- NYC: `new-york-ny` covers all five boroughs (435 one-bedrooms and 224 studios under $3,000). `queens-ny` was
  also searched and added nothing new, so borough and neighbourhood pages were not crawled separately.
  Zumper's NYC inventory under $3,000 is thin.
- Search cards: 15,943 card sightings → 3,551 unique qualifying listings (417 dropped for ZIP outside the grid,
  40 for card price over $3,000). When a city has under 25 matches Zumper adds "nearby" results; those were
  kept when their ZIP is in the grid.
- Detail stage drops (so far): 191 units no longer active on their page, 166 building floor plans with 2+ beds,
  118 over $3,000 on the page.

## Fill rates

| field | all 3,488 rows | the 709 detail rows |
|---|---|---|
| available_date | 733 (21%) | 171 (24%) |
| dogs yes / no / unknown | 972 / 111 / 2,405 | 203 / 111 / 395 |
| elevator yes / no / unknown | 482 / 31 / 2,975 | 181 / 31 / 497 |
| floor | 82 (2%) | 82 (12%) |
| unit | 501 (14%) | 501 (71%) |
| building_floors | 20 | 20 |
| dog_weight_limit_lb | 5 | 5 |
| pet_rent / parking_fee | 9 / 7 | 9 / 7 |
| sqft | 3,147 (90%) | about half |

How each gate field is derived (so the gate script can decide how much to trust it):

- **dogs.** `yes`/`no` from the visible policy block (`Pets | Dog | Policy | Allowed / Not allowed`) or the
  "Dogs OK" amenity. Where a page has no policy block, `yes` rests on the page-data `pets` codes
  (1 = cat, 2 = dog; 3 only ever appears with 2 and is unlabelled; the mapping was inferred by comparing codes with
  policy blocks, it is not documented by Zumper). `dog_policy_text` always says which basis was used. On **card
  rows** `dogs=yes` is code-only (769 rows). An empty code list is treated as unknown, not as "no".
- **Conflicts.** 20 rows have `CONFLICT` in `notes` (policy block says no dogs but the codes or a "Dogs Ok"
  amenity say yes). These matter for the "contradictory dog policy" avoid rule.
- **elevator.** `yes` only from an "Elevator" amenity tag; `no` only when the description says walk-up or no
  elevator; otherwise unknown. No tag does not mean no elevator.
- **floor.** Zumper's `listing_location.floor` was never filled. `floor` is set only from an explicit phrase in
  the unit's own description ("located on the 4th floor", "3rd-floor unit"); the phrase is quoted in `notes`.
  The unit number (for example 4B) is in `unit` and was not converted to a floor.
- **building_floors.** Only from building-level tags such as "Six Floors". Zumper's `floors` field was always empty.
- **available_date.** Zumper's `date_available`; a date on or before the fetch day is written as `now`, with the
  original in `available_date_text`. Most listings have none.
- **Fees.** `other_monthly_fees_json` holds the parsed "Policies and fees" lines (`monthly`, `non_monthly`),
  the page-data fee objects, and utility tags whose meaning is unclear (bare "Water", "Gas": may or may not mean
  included). `utilities_included` only uses explicit "… Included" tags. Fee sentences in descriptions (for example
  "$50 amenity fee + $25 trash fee") are quoted in `notes` after `desc:`. `price_basis` is base rent; Zumper says
  on most pages that fee information is incomplete.
- **listing_type.** `managed_building` for building pages; `condo_coop` / `unit_in_house` only from Zumper's
  property type; otherwise unknown. `notes` carries `feed=` (for example `listhub_api` = MLS, `realpage`, `entrata`)
  and `provider_url`.
- **listing_age_days** is from `listed_on`, which feeds refresh; when `created_on` is older it is in `notes`.

## Targets mode

`python3 scripts/h_zumper.py targets FILE.csv [--refresh] [--max-age-h 12]`

- `FILE.csv` needs column `url`; `building_url` and `listing_id` are optional. Non-Zumper URLs are skipped.
  Query strings are stripped and never sent.
- One request per building page however many rows point at it. A `/listings/` row with a Zumper
  `building_url` is read from the building page; the unit page is fetched only if the building page does not list
  it. A `/listings/` row without one is fetched, then its building page if it has one.
- Cached pages younger than 12 h are reused (change with `--max-age-h`, or force with `--refresh`).
  Same 2.2 s throttle; stops on 403/429/CAPTCHA and writes `raw/zumper/BLOCKED.txt` (delete it to resume).
- It then rebuilds the CSV: matching rows become `detail_level=detail` with `last_seen` = that fetch;
  `first_seen` is kept. Units that are inactive, over $3,000 or 2+ beds on the page are removed and counted.
- Tested on 2 uncached rows (1 building, 1 unit page) and 4 cached rows.

Other stages: `search` (resumable; `--refresh` refetches), `details` (the full crawl that was stopped; resumable
from cache), `build` (normalise only, no network).

## Blocks and oddities

- **No blocks.** About 1,410 requests, all HTTP 200. No 403, 429 or CAPTCHA.
- Search-card square footage is present on 97% of cards but on only about half of detail pages; where the detail
  page has none the card value is quoted in `notes`, not in `sqft`.
- A building card can qualify on its cheapest floor plan while the unit of interest is larger; only active
  studio/1BR floor plans ≤ $3,000 from the building page are written (18 extra units came from building pages
  that the search cards did not list individually).
- `listing_id` is `zumper-<Zumper listing_id>`; the number in a `/listings/<n>p/` URL is a different id.
- Photo URLs are built as `https://img.zumpercdn.com/<media_id>/1280x960` from the first media id; the pattern
  was taken from page markup and individual images were not fetched.
