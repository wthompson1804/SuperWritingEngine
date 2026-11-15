# Apartment List harvest notes (2026-11-15)

Script: `scripts/h_apartmentlist.py`. Output: `data/listings_raw/apartmentlist.csv`. Raw pages: `raw/apartmentlist/`
(run stats in `raw/apartmentlist/_harvest_stats.json`; first-run stats in `_harvest_stats_run1.json`).

## Access

- `robots.txt` re-read 2026-11-15 18:10 UTC: one group only (`User-agent: *`), `Allow: /`; disallowed: `/users/login`,
  `/experiments`, `/light_cycle`, `/shortlist`, `/signup`, `/base-price-lock`, `/all-in-price-lock`, `/app/open`.
  **No group names Claude agents. No Crawl-delay.** We used 2.5 s per request, plain fetch only (no browser needed).
- No 403 / 429 / CAPTCHA at any point (about 2,300 requests). Nothing was blocked.

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
- **Cities completed: 195, every in-grid sitemap city up to drive_min 64.8 (last: nj/iselin).** Includes all five NYC
  boroughs, Nassau, western Suffolk, southern Westchester, Hudson/Bergen/Essex/Union/Passaic and nearer Middlesex NJ,
  Stamford/Greenwich area. **Not reached: 76 cities from 65.4 to 90 min** (first: ny/suffern, nj/fords; list in the stats
  file under `not_reached_time_budget`), plus everything 90–120 min.
- Gazetteer-miss cities done after the ≤ 50 min group (NJ townships such as Edison, Montclair, North Bergen, West Orange,
  Bloomfield, Irvington; CT Darien, Westport). Excluded as beyond 90 min or outside grid: ct/hamden, ct/milford-city,
  ct/stratford, ct/trumbull, nj/hamilton-township, ct/bloomfield, nj/riverside, 3 PA.
- Search pages read: 766. Properties discovered: 2,377. Skipped on search-page low price: 851. Property pages read: 1,526
  (1,517 produced rows; 8 had no studio/1BR ≤ $3,000; 1 unparseable).
- **Rows: 3,166 units in 1,583 properties** (NJ 1,897, NY 1,007, CT 262; 1BR 2,410, studio 756).
  Some rows have drive_min above 64.8 (max 105.5) because city pages include properties in neighbouring ZIPs.

Coordinator condition (b) (multi-unit only, skip pets-not-allowed) could not be applied before fetching: search cards
carry no property type or pet flag. It can be applied afterwards from `listing_type`, `dogs` and `notes` (`rental_type=`,
`total_units_count=`). Properties whose card had no price were fetched (the card gives no basis to skip them).

## Fill rates (3,166 rows)

| field | filled | detail |
|---|---|---|
| available_date | 100% | now 2,469; dated ≤ 2026-12-15 368; later 329 |
| dogs | 60% | yes 1,785; no 114; unknown 1,267 |
| dog_weight_limit_lb | 3.2% | 90 rows with a limit ≥ 40 lb; most pages give no weight |
| elevator | 37% | yes 1,134; no 35 (description says walk-up); unknown 1,997 |
| floor | 0% | the page has no floor field; unit numbers are in `unit` and not interpreted |
| building_floors | 0.6% | only when the description says "N-story" |
| sqft 80%, laundry 77%, parking_type 84%, parking_fee 9%, pet_rent 31%, utilities_included 9%, fees JSON 53%, manager 53%, photo 99% | | |
| listing_type | 65% | managed_building 1,741; condo_coop 282; unit_in_house 25; unknown 1,118 |
| listing_age_days, concession_text | 0% | no listing date on the page; `specials` was empty on every page read |

Rows with dogs = yes, elevator = yes and available by Dec 15: 752.

## Field rules and oddities

- `listed_rent` = unit `base_price` (else `price`); `price_basis` says base rent and the lease length. Required-fee totals,
  when the page has them, go to `other_monthly_fees_json`.
- `available_date` = `now` when the page flags `available_now` or `available_on` is on/before the fetch date.
- `dogs = yes` only if dogs are named (`allowed_pets` or a "Dogs allowed" amenity). "Pet friendly" alone, or
  `allowed=true` with no species (the default on MLS-fed rows), is `unknown`. Cats-only or `allowed=false` is `no`.
- `elevator = yes` from the Elevator amenity or the description; absence is `unknown`, not `no`.
- Feeds: yardi_rentcafe 874 rows, listhub (MLS) 677, bozzuto 388, propertyware 262, listanza 171, RealPage 159,
  rentalutions 133, entrata 114. MLS/listhub and propertyware rows are thin (few gate facts) and **some look stale**:
  `available_on` months in the past with an old `unit_updated_at` (both are kept in `available_date_text` / `notes`).
  Check `availability_last_checked_at` and `unit_updated_at` in `notes` before trusting those.
- Managed rows carry the building's own site in `notes` (`website_url=`); useful for confirming price and pet weight.
- `url` and `building_url` are both the property page (units have no page of their own).
- A re-run reuses the cache; `--refresh` refetches and updates `last_seen`. To finish coverage:
  `python3 scripts/h_apartmentlist.py --max-drive 120 --fetch-max-low 2850` (done cities replay from cache in seconds).
