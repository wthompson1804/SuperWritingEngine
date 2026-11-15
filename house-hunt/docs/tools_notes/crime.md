# Lookup tool notes: `crime`

Module: `scripts/tools/crime.py`. Built 2026-11-15. Reference tables: `data/reference/crime_agencies.csv`,
`data/reference/crime_place_agency.csv`, `data/reference/crime_nyc_baseline.csv`. Big files: `raw/big/crime/`.

## What it answers

| Function | Answer | Coverage |
|---|---|---|
| `agency_rates(lat, lon)` | The police agency covering the point, with violent, property, motor vehicle theft, burglary and larceny counts, the population used and rates per 1,000 for the latest three years | 965 of the 1,048 search-grid ZIP centroids return an agency; 83 return `not_found` with the reason (State Police or regional-department areas) |
| `incidents_near(lat, lon, radius_m=250)` | NYPD complaint counts around the point: last 24 months, 2023, 2024, 2025, 2026 to date, and the share starting 19:00 to 24:00 | New York City only; `not_found` with the reason elsewhere |
| `nyc_baseline(radius_m=250)` | Median, 80th and 90th percentile of the same counts over a grid of residential points, citywide and per borough | New York City |

Run time after the indexes exist: about 0.1 s for the first call in a process (loads the indexes), then about
0.3 ms per point for both lookups together (1,048 grid points in 0.3 s).

Rebuild: `python3 scripts/tools/crime.py --build` (geography, agency tables, incident slice, baseline). The FBI
pull is about 3,500 cached calls and takes about 25 minutes the first time; everything else takes about 3 minutes.
Self-test: `python3 scripts/tools/crime.py`.

## Sources (kept separate, never blended into one count)

| `source` | What | URL | Latest full year |
|---|---|---|---|
| `ny_dcjs` | NY DCJS, Index Crimes by County and Agency | https://data.ny.gov/resource/ca8h-8gjq.json | 2024 (rows for 2022 to 2024) |
| `ny_dcjs` (county population) | NY DCJS, Index, Violent, Property and Firearm Rates by County | https://data.ny.gov/resource/34dd-6g2j.json | 2024 |
| `fbi_cde` | FBI Crime Data Explorer API, `/summarized/agency/{ORI}/{offense}` for V, P, motor-vehicle-theft, burglary, larceny, and `/agency/byStateAbbr/{state}` | https://api.usa.gov/crime/fbi/cde | 2025 (rows for 2023 to 2025) |
| `nypd_complaints` | NYPD Complaint Data Historic, grouped by precinct and report year | https://data.cityofnewyork.us/resource/qgea-i56i.json | 2025 (rows for 2023 to 2025) |
| incident slice | NYPD Complaint Data Historic plus Current Year To Date | qgea-i56i and 5uac-w243 | data through 2026-09-30 |
| geography | Census TIGER/Line 2024 places and county subdivisions (NY, NJ, CT, PA); NYPD precinct polygons | https://www2.census.gov/geo/tiger/TIGER2024/ ; NYC Open Data y76i-bdw7 | |
| precinct population | 2020 Census PL 94-171 block population (cache `raw/census_pl2020/nyc_blocks_pop.csv` from the earlier safety script) | www2.census.gov, `ny2020.pl.zip` | 2020 |

robots.txt: data.cityofnewyork.us and data.ny.gov ask for a 1 s crawl delay (honoured). api.usa.gov has no
robots.txt; the API answers `X-Ratelimit-Limit: 10` and the script stays near 3 requests per second. No key is sent.

## `crime_agencies.csv` (2,905 rows, 970 agency-source pairs)

One row per agency, source and year. Scope: every agency in the 37 counties (or Connecticut planning regions)
that hold a search-grid ZIP centroid, which is a superset of "agencies covering a grid ZIP".

- `nypd_complaints`: 78 precincts by 3 years. `violent` = ky_cd 101 murder + 104 rape + 105 robbery + 106 felony
  assault. `property` = 107 burglary + 109 grand larceny + 341 petit larceny + 110 grand larceny of motor vehicle.
  `larceny` = 109 + 341. These are NY Penal Law categories, close to FBI definitions but not identical (felony
  assault is not exactly aggravated assault). Population is an **estimate**: 2020 Census blocks whose internal
  point is inside the precinct polygon. Central Park precinct (22) has no residents, so no rate.
- `ny_dcjs`: every agency DCJS lists in the 14 New York counties, plus a "County Total" row with DCJS's own county
  population. DCJS publishes no agency population, so an agency rate uses the FBI's population for the same agency
  and year. That rate is labelled `estimate`, and `population_source` and `rate_method` say that it uses two sources.
  The count itself is DCJS only.
- `fbi_cde`: 685 agencies (municipal and county types in the grid counties, plus NYPD citywide), counts and the
  FBI's population. Rates are FBI count over FBI population.

Rates are missing (`rate_value_type = not_found`, reason in `notes`) when fewer than 12 months were reported, when
there is no population (sheriffs, State Police, park and transit police), or when the FBI shows zero for every
offence all year for a place of more than 3,000 people.

### Data-quality findings worth knowing

- **DCJS and FBI agree in 73% of comparable cells** (1,132 of 1,550 agency-year-offence values identical); 46 differ
  by more than 10%. Each stays in its own rows.
- **The FBI data has silent gaps.** The API gives no "incomplete" flag. Example: Suffolk County PD shows 643 violent
  crimes in the FBI data for 2023 against 1,371 in DCJS, and zero for all of 2025. The build adds a note when a year
  has three or more zero-property months (population above 10,000), is all zero, or is less than half the prior
  year. 62 FBI rows carry such a note; 32 New Jersey agencies have a 2025 property count below half of 2024.
  `agency_rates` exposes this as `quality_flag` per year and `latest_unflagged_year`.
- **Suffolk County PD 2024 in DCJS** lists 3 months reported although its counts are near a full year. No 2024 rate
  is computed; the latest year with a rate is 2023.
- **Long Beach City PD** reports 36 property crimes for 2024 for 35,000 people (it reported 199 in 2017). Both
  sources carry the same figure. `agency_rates` adds a caveat whenever property crime is under 2 per 1,000 for a
  population above 15,000.
- Jersey City stated in June 2026 that an audit found crimes missing from earlier years' figures (city press
  release, seen through a web search, not fetched by the script). Treat Jersey City trends with caution.

## `crime_place_agency.csv` (937 rows): how a point is mapped to an agency

1. Inside an NYPD precinct polygon: that precinct (`polygon`, 78 rows).
2. Otherwise find the Census place (village, city) and county subdivision (town, township, borough) of the point.
   A row for the place wins; if there is none, the row for the county subdivision is used.

`mapping_basis` values:

| Basis | Rows | Meaning |
|---|---|---|
| `name_match` | 591 | The agency name matches the place by name (and by type where the name states one). NY: Census place against the DCJS agency list for that county ("Lynbrook village" to "Lynbrook Vg PD"). NJ, CT, PA: county subdivision against the FBI agency list for that county |
| `name_match_base` | 16 | **Inference.** NJ or PA borough and township share a name and the FBI name does not say which; the untyped agency is given to the non-township |
| `inference_rule` | 61 | **Inference.** NY town outside any village or city with its own department: the town department if DCJS lists one, otherwise Nassau County PD (all of Nassau) or Suffolk County PD (towns of Babylon, Brookhaven, Huntington, Islip, Smithtown) |
| `inference_manual` | 4 | **Inference from general knowledge, not from a fetched table.** Port Washington Police District is assigned to Port Washington CDP and the villages of Baxter Estates, Manorhaven and Port Washington North |
| `no_single_agency` | 60 | NY town with no town, village or county department in DCJS (sheriff and State Police patrol). `agency_rates` returns `not_found` plus the DCJS county total as context |
| `no_agency_matched` | 127 | NJ, CT or PA municipality with no municipal department of that name in the FBI list (State Police, resident trooper or regional department). Not resolved |

Known limits of the Nassau and Suffolk mapping (the hard part):

- A village with no department in the DCJS list falls to Nassau County PD or the town department. That is right
  for most (Mineola, Great Neck Plaza, Valley Stream), but a few small North Shore villages contract with a
  neighbouring village department instead (for example the villages around Old Brookville). These are not
  modelled; they hold almost no elevator rentals.
- Suffolk villages with their own department that DCJS does not list (if any) fall to the county or town.
- In Rockland and Westchester a village without its own department is given the town department (Nyack to
  Orangetown Town PD). Where the town has none (Cortlandt), the answer is `not_found` with the county total.
- A county-police figure (Nassau 1.1 million people, Suffolk 1.4 million) is an average over very different
  places. The output says so in `geography` and `caveats`.

## `incidents_near`: categories and method

Slice downloaded once into `raw/big/crime/` (9 CSV pages, 373,034 complaints, report dates 2023-01-01 to
2026-09-30) and packed into `nypd_incidents.npz`, sorted by latitude for a binary-search band query. Two rows of
373,034 have no coordinates.

| Key | Exact values in the data |
|---|---|
| `grand_larceny_motor_vehicle` | `ofns_desc` GRAND LARCENY OF MOTOR VEHICLE (`ky_cd` 110): `pd_desc` LARCENY,GRAND OF AUTO (441); LARCENY, GRAND OF AUTO - ATTEM (442); LARCENY, GRAND OF MOPED (450); LARCENY,GRAND OF MOTORCYCLE (451); LARCENY,GRAND OF TRUCK (455) |
| `glmv_car_or_truck_only` | Subset of the above without mopeds and motorcycles: `pd_cd` 441, 442, 455. Mopeds and motorcycles are about a quarter of the category, more in some areas |
| `theft_from_vehicle` | `pd_desc` LARCENY,PETIT FROM AUTO (`pd_cd` 321) and LARCENY,GRAND FROM VEHICLE/MOTORCYCLE (421) |
| `vehicle_parts_theft` (extra) | LARCENY,PETIT OF VEHICLE ACCES (357) and LARCENY,GRAND OF VEHICULAR/MOTORCYCLE ACCESSORIES (457) |
| `vehicle_criminal_mischief` (extra) | MISCHIEF, CRIMINAL 4, OF MOTOR (254): damage to a vehicle |
| `robbery` | `ofns_desc` ROBBERY (`ky_cd` 105) |
| `felony_assault` | `ofns_desc` FELONY ASSAULT (`ky_cd` 106) |
| `burglary` | `ofns_desc` BURGLARY (`ky_cd` 107), homes and businesses together |

Not counted: `pd_cd` 270 INVOLVING PETIT LARC FRM AUTO (398 rows in 2026 only), unauthorized use of a vehicle
(461, 462), petit larceny of motor vehicle (`ky_cd` 342, about 180 a year).

- Years are **report years** (`rpt_dt`), as in NYPD's own statistics. "Last 24 months" is the 24 months ending on
  the latest report date in the current-year dataset (2024-10-01 to 2026-09-30). The current-year dataset is
  refreshed quarterly; rerun `--build-incidents --force` to update.
- Evening share: share of last-24-month complaints with a recorded start time (`cmplnt_fr_tm`) whose start hour is
  19 to 23. For a theft discovered the next morning the start time is the beginning of the possible window, so the
  share shows when the window opened, not exactly when it happened. With small counts the share is noisy; the
  output gives the numerator and denominator.
- NYPD publishes the midpoint of the block or the nearest intersection, not the address. A 250 m count is
  approximate, and incidents on a block all sit on one point.
- Counts are not per resident. Transit hubs and shopping streets collect far more robbery and assault complaints
  (Jamaica station: 79 robberies in 24 months against a Queens median of 2).

## `nyc_baseline`

A regular 300 m grid over the precinct polygons; a grid point is "residential" when 2020 Census blocks within
250 m hold at least 500 residents (6,119 points: Queens 2,108, Brooklyn 1,630, Staten Island 973, Bronx 860,
Manhattan 548). The `incidents_near` counts are computed at each point and summarised. `value_type = estimate`.
Results for other radii are computed on first use (about 2 s) and cached in `raw/big/crime/`.

Last 24 months, radius 250 m, median / 80th percentile:

| Area | Motor vehicle theft | Cars and trucks only | Theft from vehicle | Robbery | Felony assault | Burglary |
|---|---|---|---|---|---|---|
| Citywide | 7 / 14 | 5 / 10 | 5 / 11 | 4 / 16 | 9 / 32 | 4 / 12 |
| Queens | 8 / 13 | 5.5 / 9 | 4 / 7 | 2 / 8 | 6.5 / 17 | 4 / 8 |
| Brooklyn | 7 / 12 | 5 / 7 | 6 / 11 | 6 / 16 | 14 / 35 | 6 / 12 |
| Bronx | 18 / 26 | 14 / 20 | 10 / 23 | 15 / 37 | 29 / 75 | 9 / 23 |
| Manhattan | 7 / 13 | 4 / 8 | 9 / 17 | 20 / 36 | 31 / 68 | 20 / 35 |
| Staten Island | 1 / 3 | 1 / 2 | 2 / 4 | 1 / 2 | 2 / 7 | 1 / 2 |

`incidents_near` returns `vs_baseline` with the borough and citywide median and 80th percentile next to each count
and `above_borough_p80` / `above_citywide_p80` flags. The grid weights every residential point equally, so
low-density blocks count as much as apartment districts; a building in a dense area will sit above the median for
that reason alone.

## Incident-level open data outside New York City (checked 2026-11-15, not wired in)

| Place | Finding |
|---|---|
| Jersey City | `data.jerseycitynj.gov` lists a dataset `jcpd-calls-for-service` (calls, not confirmed crimes). The portal reset the connection from this environment, so its fields and coordinates were not checked. The city's JC IMPACT dashboard (impact.jcnj.org, launched June 2026) disallows its raw `.json` files in robots.txt |
| Newark | The CKAN portal `data.ci.newark.nj.us` did not answer. No official incident dataset with coordinates found by search |
| Yonkers | No Socrata domain; no official incident dataset found |
| Stamford | No Socrata domain. The city's portal (stamfordct.portaljs.com) has traffic-stop data with coordinates, not crime incidents |
| New Haven | Weekly CompStat PDFs on newhavenct.gov with reference addresses; no dataset or map service found |
| Connecticut statewide | data.ct.gov `7t99-gbjg` "CT Crime Incidents: NIBRS" is a link record, not a table (403 on `/resource/`) |
| Nassau County | Precinct-level "STRAT-COM" comparison PDFs on pdcn.org; no incident data with coordinates |
| Suffolk County | PDF reports only |

These were found through the Socrata catalog API and web searches; the search-result pages themselves were not
fetched or verified beyond what is stated.

## Gaps

- No address-level counts outside New York City.
- 83 grid ZIP centroids have no agency rate (rural NJ, CT and PA towns, and NY towns patrolled by sheriff or State
  Police). NY ones return the county total as context.
- Pennsylvania mapping is name-only; regional departments are unresolved (48 of 112 municipalities in the three
  grid counties).
- Years differ by source: DCJS ends at 2024, FBI and NYPD at 2025.
- NYPD precinct rates and agency rates elsewhere use different offence definitions (NY Penal Law against FBI UCR)
  and different population bases (2020 Census residents against FBI yearly estimates). For a like-for-like city
  figure, `context.nypd_citywide_fbi` and `context.borough_dcjs` are returned alongside.
- `raw/fbi_cde/` holds about 7,200 small cache files (57 MB) outside the git-ignored `raw/big/`.
