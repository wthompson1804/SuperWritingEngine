# Apartment List harvest notes (2026-11-15)

Script: `scripts/h_apartmentlist.py`. Output: `data/listings_raw/apartmentlist.csv`. Raw pages: `raw/apartmentlist/`
(run stats in `raw/apartmentlist/_harvest_stats.json`, final full pass; earlier: `_harvest_stats_run1.json`, `_harvest_stats_run3.json`).

## Access

- `robots.txt` re-read 2026-11-15 18:10 UTC: one group only (`User-agent: *`), `Allow: /`; disallowed: `/users/login`,
  `/experiments`, `/light_cycle`, `/shortlist`, `/signup`, `/base-price-lock`, `/all-in-price-lock`, `/app/open`.
  **No group names Claude agents. No Crawl-delay.** We used 2.5 s per request, plain fetch only (no browser needed).
- robots.txt re-checked 2026-11-15 21:44 UTC before run 4: unchanged (single `*` group, same eight Disallow lines).
- No 403 / 429 / CAPTCHA at any point (4,698 logged responses across all runs, all HTTP 200). Nothing was blocked.

## URL patterns

- Sitemap index `/sitemap.xml` → `sitemap-cities.xml` (4,946 cities; 743 in NY/NJ/CT/PA), `sitemap-properties.xml`
  (31,607; only 333 NY / 478 NJ / 182 CT, so it is partial: Queens alone lists 407 properties), `sitemap-homes-for-rent*.xml`
  (single units), `sitemap-1-bedroom.xml`, `sitemap-studio.xml`, `sitemap-pets.xml`, `sitemap-price-range.xml`.
- City search page: `/<st>/<city>`, pages `/<st>/<city>/page-N` (16 per page).
- **Path filters exist, with a `/c/` segment:** `/<st>/<city>/c/1-bedroom-apartments-for-rent`,
  `/c/studio-apartments-for-rent`, `/c/pet-friendly-apartments-for-rent`, `/c/apartments-for-rent-under-2000` (price
  paths exist only for a few cities in the sitemap; `-under-3000` on Queens silently returns the unfiltered page).
  Filters paginate (`.../page-2`). Filters do **not** work on county pages (`/ny/queens-county/c/...` returns 0).
  `/ny/queens/1-bedroom-apartments` style (no `/c/`) does not exist.
- Neighbourhood pages are `/<st>/<city>/neighborhoods/<slug>` (not `/ny/forest-hills`). Not used.
- Property page: `/<st>/<city>/<property-slug>`. Data is in the Next.js flight payload (`self.__next_f.push`), as a
  full `listing` object: address, zip, lat/lon, `available_units` (floor plans → units with price, base_price,
  available_on, available_now, sqft, lease_length), `pet_policies`, amenities, parking, fee texts, utilities, source feed.

## Method

1. Cities from `sitemap-cities.xml` in NY/NJ/CT/PA, located with the Census 2024 places gazetteer; a city is in scope
   when a grid ZIP centroid is within 8 km. 365 matched in-grid cities + 27 gazetteer misses (located from their own page).
2. Nearest-first by drive_min. For each city, the 1-bedroom and studio filter pages are read **for discovery only**.
3. A property page is fetched unless the search page's JSON-LD `lowPrice` (property-wide lowest price) is above the
   threshold. Price, date and all gate facts come from the property page (`detail_level=detail` on every row).
4. One row per available studio/1BR unit with rent ≤ $3,000 (or per floor plan if no unit list). Row kept only if the
   property ZIP is in the grid (or lat/lon within 2.5 km of a grid centroid).

The search-page "unit summary" blob (one unit per bed type) is **not** the cheapest unit (Avalon Riverview: summary studio
$3,838 vs page low $3,555), so it was not used for filtering.

## Coverage

- Run 1 (18:21–19:10 UTC): threshold `lowPrice ≤ $3,000`, cities up to 39.3 min.
- Run 2 (19:10–19:54 UTC, coordinator change): threshold `lowPrice ≤ $2,850`, max drive 90, time budget 44 min;
  stopped by the 19:55 hard deadline.
- Run 3 (from 19:56 UTC): same threshold, max drive 120; stopped by the coordinator at 78.3 min (nj/mount-arlington).
- Run 4 (21:45–22:19 UTC): `--reparse --max-drive 120 --fetch-max-low 2850`. Replayed the done cities from cache and
  harvested the remaining 150 cities, 78.4 min (nj/south-river) to 119.6 min (pa/levittown, pa/fairless-hills).
- **Cities completed: 387 = every in-grid sitemap city out to the 2-hour grid edge (last drive_min 119.6).** Nothing is
  left unreached. Beyond 64.8 min (nj/iselin): 197 cities, 654 properties discovered, 43 cities with none. Adds central
  NJ (Middlesex, Monmouth, Mercer, Somerset, Morris, Warren), New Haven area CT, Orange/Dutchess/Putnam NY, Bucks PA.
- Gazetteer-miss cities (27) were placed from their own page; 5 are outside the grid (ct/bloomfield, nj/riverside,
  3 PA) and were not harvested.
- Pet-friendly path filter (`/c/pet-friendly-apartments-for-rent`): not used. It cannot be combined with a bedroom
  filter in one path, so it would add at least one search request per city to save detail fetches only for the
  pets-not-allowed properties (4% of rows). Outer cities average 3 properties, so it would cost more than it saves.
  The 1-bedroom and studio filters remain the discovery pages (they do cut requests: no 2BR+ only properties fetched).
- Search pages read: 1,349. Properties discovered: 3,015. Skipped on search-page low price > $2,850: 905. Property
  pages read in run 4's pass: 2,110 (2,049 produced rows; 48 outside the grid; 11 no studio/1BR ≤ $3,000; 1 price
  hidden; 1 unparseable).
- **Rows: 4,944 units in 2,115 properties** (NJ 2,942, NY 1,099, CT 888, PA 15; 1BR 3,911, studio 1,033).
  1,918 rows have drive_min above 64.8; row drive_min is the property ZIP's, max 119.6.

Coordinator condition (b) (multi-unit only, skip pets-not-allowed) could not be applied before fetching: search cards
carry no property type or pet flag. It can be applied afterwards from `listing_type`, `dogs` and `notes` (`rental_type=`,
`total_units_count=`). Properties whose card had no price were fetched (the card gives no basis to skip them).

## Fill rates (4,944 rows)

| field | filled | detail |
|---|---|---|
| available_date | 100% | now 3,702; dated ≤ 2026-12-15 662; later 579; empty 1 |
| dogs | 66% | yes 3,070; no 209; unknown 1,665 |
| dog_weight_limit_lb | 4.9% | 244 rows state a limit, all ≥ 25 lb (the current dog gate); most pages give no weight |
| elevator | 36% | yes 1,726; no 45 (description says walk-up); unknown 3,173 |
| floor | 0% | the page has no floor field; unit numbers are in `unit` and not interpreted |
| building_floors | 0.7% | only when the description says "N-story" |
| concession_text | 45% | 2,237 rows in 247 properties (see the fix below) |
| sqft 83%, laundry 80%, parking_type 84%, parking_fee 12%, pet_rent 37%, utilities_included 14%, fees JSON 57%, manager 53%, photo 99% | | |
| listing_type | 68% | managed_building 2,966; condo_coop 355; unit_in_house 38; unknown 1,585 |
| listing_age_days | 0% | no listing date on the page |

Rows with dogs = yes, elevator = yes and available by Dec 15: 1,213.

## Fixes in run 4 (re-parsed from cache, no refetch)

- **concession_text.** The property page carries the listing object twice. The first copy (the one parsed) always has
  `specials: []`; the second copy (big fields replaced by `$ref` pointers) holds the real `specials[]`, with the offer in
  `raw_text`. The parser now collects specials from every copy of the same `rental_id` and writes `raw_text`
  (plus `(expires YYYY-MM-DD)` when `expires_at` is set; several offers joined with ` | `). `--reparse` rebuilds every
  existing row from its cached page: 1,694 pages, 3,552 rows rebuilt, 1,497 of the earlier 3,553 rows gained text.
  Concession wording is the property-wide offer, not unit-specific; `listed_rent` is still the base rent, not net-effective.
- **Long descriptions.** About 15% of pages store the description as a flight text row referenced as `$87`; it was
  read as the literal pointer. Now resolved, which changed elevator unknown → no (walk-up) on 5 rows and filled
  building_floors on 15.
- The re-parse also brought 568 earlier rows in line with their cached page (`last_seen`; 14 rents and 7 dates
  differed): the CSV held values from a fetch that a later run had already replaced in the cache.
- One earlier row was not regenerated from its cached page and is kept unchanged.

## Field rules and oddities

- `listed_rent` = unit `base_price` (else `price`); `price_basis` says base rent and the lease length. Required-fee totals,
  when the page has them, go to `other_monthly_fees_json`.
- `available_date` = `now` when the page flags `available_now` or `available_on` is on/before the fetch date.
- `dogs = yes` only if dogs are named (`allowed_pets` or a "Dogs allowed" amenity). "Pet friendly" alone, or
  `allowed=true` with no species (the default on MLS-fed rows), is `unknown`. Cats-only or `allowed=false` is `no`.
- `elevator = yes` from the Elevator amenity or the description; absence is `unknown`, not `no`.
- Feeds: yardi_rentcafe 1,443 rows, listhub (MLS) 966, bozzuto 466, RealPage 438, propertyware 266, entrata 184,
  listanza 172, avalon_bay 160. MLS/listhub and propertyware rows are thin (few gate facts) and **some look stale**:
  `available_on` months in the past with an old `unit_updated_at` (both are kept in `available_date_text` / `notes`).
  Check `availability_last_checked_at` and `unit_updated_at` in `notes` before trusting those.
- Managed rows carry the building's own site in `notes` (`website_url=`); useful for confirming price and pet weight.
- `url` and `building_url` are both the property page (units have no page of their own).
- A re-run reuses the cache; `--refresh` refetches and updates `last_seen`. Full replay:
  `python3 scripts/h_apartmentlist.py --reparse --max-drive 120 --fetch-max-low 2850` (all cities replay from cache; `--reparse`
  first rebuilds every existing row from its cached page; `--min-drive N` skips nearer cities).
