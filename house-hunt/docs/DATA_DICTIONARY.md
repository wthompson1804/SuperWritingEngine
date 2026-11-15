# Data dictionary

All tables live in `data/` as CSV (UTF-8, comma, header row) and are loaded into
`data/house_hunt.sqlite` by `scripts/build_sqlite.py`. Times are UTC ISO 8601. Money is USD per month unless the field name says otherwise.

## Conventions used in every table

| Convention | Meaning |
|---|---|
| `source_url` | The page or API call the value came from. Required on every fact. |
| `retrieved_at` | When we fetched it (UTC). |
| `value_type` | `found` (read from source), `estimate` (computed or modelled; `method` says how), `not_found` (looked and nothing there; `notes` says where we looked). |
| `unknown` | Used for categorical fields (dogs, elevator) when the source doesn't say. Not the same as `not_found` for a whole metric. |
| `raw_path` | Path of the cached raw response under `raw/`, so any row can be re-derived. |
| Facts vs opinions | Opinions (reviews, quotes) never go in fact columns; they live in `quotes` or in `*_excerpt` fields with a link. |

## `areas` (`data/areas.csv`)

One row per area (town or neighbourhood). Built by `scripts/build_areas.py` from `seeds/areas_seed.csv`.

| Field | Description |
|---|---|
| id | Stable slug, `r<region>-<name>`. Never reuse. |
| region | R1–R8 (see handoff §7). |
| name, state | Display name and state code. |
| centroid_lat, centroid_lon | Point used for all radius metrics. See `centroid_method`. |
| centroid_method | `gtfs_station` (the anchor station, which sits in the downtown or main rental cluster) or `nominatim` (OSM geocode of the seed's `geocode_query`). |
| centroid_source | GTFS stop id, or the Nominatim query URL. |
| county, county_fips | From the Census Geocoder at the centroid. |
| county_subdivision, cousub_geoid | Town, city or borough (Census MCD). |
| municipality, place_type, place_geoid | Incorporated place if any, else CDP (hamlet), else county subdivision. |
| tract_geoid | Census tract at the centroid. |
| zcta_centroid | ZCTA containing the centroid. |
| zctas_within_800m | ZCTAs at the centroid plus 8 points on an 800 m ring. ZCTAs approximate USPS ZIPs. |
| anchor_station, anchor_system, anchor_line, anchor_stop_id, anchor_station_dist_m | The station we treat as the area's rail access (seeded by hand, matched to GTFS). Line names are hand-entered. |
| nearest_rail_station, nearest_rail_system, nearest_rail_dist_m | Nearest commuter-rail or PATH stop to the centroid (LIRR, MNR, NJT, PATH, SEPTA). Computed. |
| nearest_subway_station, nearest_subway_dist_m | Nearest NYC subway or SIR station, if within 5 km. |
| police_jurisdiction, police_jurisdiction_basis | NYPD precinct by point-in-polygon for NYC. Elsewhere it's an analyst assignment, marked UNVERIFIED until checked against the agency. |
| notes, retrieved_at | |

## `area_metrics` (`data/area_metrics.csv`), long format

One row per area × metric × source × period. Never blend sources into one row.

| Field | Description |
|---|---|
| area_id | → areas.id |
| domain | `rent`, `people`, `travel_transit`, `travel_drive`, `tolls`, `safety`, `daily_life`, `walkability`, `risk`, `broadband`, `money`, `supply`, `renter_protection`. |
| metric | e.g. `zori_all_homes`, `safmr_1br`, `acs_median_gross_rent_1br`, `rail_fastest_min_sat`, `drive_min_freeflow`, `nypd_auto_theft_0.5mi`, `osm_bars_800m`. The full list lives in `docs/METRICS.md` (written in Phase 1). |
| value | Number, or text for categorical metrics. |
| unit | `usd_month`, `minutes`, `count`, `per_1000`, `pct`, `usd_round_trip`, … |
| geography | What the value describes: `zcta:11375`, `tract:…`, `place:…`, `agency:…`, `radius_800m`, `route:area→jamaica`. |
| period | `2026-09` (month), `2024` (year), `2022-2026` (ACS 5-year), `2026-11-21 Sat` (schedule day). |
| source | Short source key (see `docs/SOURCES.md`). |
| source_url, retrieved_at, raw_path | Provenance. |
| value_type | found / estimate / not_found. |
| method | How an estimate was computed, or the filter used. |
| population_used | For rates: the denominator and its source. |
| notes | |

## `listings` (`data/listings.csv`)

One row per unit listing per source. Deduplicated by `dedupe_key`; the duplicate rows from other sources are kept in `listing_sources.csv`.

| Field | Description |
|---|---|
| listing_id | `<source>:<source's id>` or a hash of the URL. |
| area_id, building_id | → areas, buildings (`building_id` blank for a unit in a house with no building profile). |
| source_site, url | The page the facts were read from. Required. |
| first_seen, last_seen | UTC times we saw the listing live. |
| status | `active`, `gone` (404 or delisted), `unverified`. |
| address, unit, dedupe_key | Normalized address + unit → `dedupe_key`. |
| beds | 0 = studio, 1 = 1BR. |
| baths, sqft | |
| listed_rent | As the page states it. |
| price_basis | `base`, `total`, `net_effective`, `unknown`. |
| concession_text | Verbatim, short. |
| fees_monthly_known | JSON list of `{name, amount, required}` (amenity, pet rent, parking, trash, …). |
| all_in_estimate | listed_rent + required fees + pet rent + parking, where known. Blank if any required component is unknown; see `all_in_complete`. |
| all_in_complete | `yes` if every component was found, otherwise `partial`. |
| clears_cap | `yes` / `no` / `unknown` (all_in vs $2,800). |
| available_date | As the page states it (date or "now"). Never from a snippet. |
| lease_term | |
| dogs | `yes`, `no`, `unknown`. Rows with `no` are dropped (count logged). |
| dog_limits | Weight, breed, number, fees (text). |
| floor, elevator, stair_flights | elevator `yes` / `no` / `unknown`. Walk-ups above 1 flight are dropped (count logged). |
| parking_type, parking_fee | `garage`, `gated_lot`, `open_lot`, `street`, `none`, `unknown`. |
| laundry | `in_unit`, `in_building`, `none`, `unknown`. |
| listing_type | `managed_building`, `condo_coop`, `unit_in_house`, `unknown`. |
| tier | By listed rent: `comfortable` ≤ 2,400; `at_cap` 2,401–2,800; `stretch` 2,801–3,000. Listings above $3,000 are not collected. |
| move_in_fit | `ready_by_dec1` (available now or on/before 2026-12-01), `after_dec1`, `unknown` (no date stated). Target move-in is **December 1, 2026**. |
| flags | Semicolon list: `dogs_unknown`, `stairs_unknown`, `price_basis_unknown`, `stale_listing` … |
| link_status, link_checked_at | Result of the latest link check. |
| raw_path, notes | |

## `buildings` (`data/buildings.csv`)

| Field | Description |
|---|---|
| building_id | Slug from the normalized address. |
| area_id, name, address, lat, lon, bbl_or_parcel | NYC BBL / BIN where available. |
| year_built, year_renovated, floors, units, elevator | |
| owner, manager | With source. |
| amenities | JSON: pool (`indoor` / `outdoor` / `none` / `unknown`), gym, dog_run, coworking, package_room, … |
| entry_security, parking_type, parking_fee | |
| pet_policy_text, pet_fees, application_fee, amenity_fee | |
| ratings | JSON list `{site, rating, count, url, retrieved_at}`. |
| records_summary | JSON of public-record counts (HPD violations by class, DOB complaints, elevator, 311 heat/noise, bedbug filings, evictions), each with a query URL. |
| red_flags | Facts only, each with a link. |
| sources | JSON list of URLs used. |

## `building_reviews` (`data/building_reviews.csv`)

building_id, site, rating, review_date, excerpt (1–2 sentences, verbatim), keyword_hits, permalink, retrieved_at. No usernames.

## `quotes` (`data/quotes.csv`)

| Field | Description |
|---|---|
| quote_id | Hash of permalink + excerpt. |
| area_id | |
| excerpt | Verbatim, 1–2 sentences. |
| theme | `safety`, `parking`, `social_life`, `noise`, `value`, `management`, `travel`, `dogs`, `regret`, `surprise`. |
| speaker_context | Only what the post itself states, e.g. `moved_from_queens`, `woman_living_alone`, `dog_owner`, `remote_worker`, `renter`, `left_area`, `compares:<area_id>`. |
| source_site, post_date, permalink | No usernames. |
| verified, verified_at | The excerpt was re-found on the permalink page by `scripts/verify_quotes.py`. Unverified rows are dropped before handback. |

## Phase 5 tables (defined when built)

`developments`, `transport_projects`, `car_crime_news`, `parking_rules`, `dog_rules`. Same provenance conventions.
