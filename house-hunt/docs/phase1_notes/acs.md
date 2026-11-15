# Phase 1 notes: ACS (domains `people` and `rent`)

Script: `scripts/p1_acs.py` · Output: `data/metrics/acs.csv` (26,880 rows, 98 of 98 areas) · Period: `2020-2024 ACS5`

## Source

The latest release is the 2020-2024 ACS 5-year **table-based Summary File** (files dated 2026-01-29). I used no API.
A Census API key arrived from the coordinator partway through. By then the bulk files were already working, so I kept them as the only source.

* Directory: https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/
* One national pipe-delimited file per table, e.g.
  https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25031.dat
  Tables used: b01001, b01002, b11001, b25002, b25003, b25031, b25034, b25035, b25036, b25064.
* Geography names: https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/documentation/Geos20245YR.txt
* Line labels: https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/documentation/ACS20245YR_Table_Shells.txt
* robots.txt on www2.census.gov has no Claude group and no `*` group, so these downloads are allowed. There were 11 downloads in all, through `lib.cached_get`.
* The bulk files (594 MB) are cached in `raw/big/census_acs5_sf/`, which is git-ignored. The script downloads them again if they are missing.
  The rows for our 332 geographies are kept in small extracts, `raw/census_acs5_sf/2024/<table>.psv` (420 KB, which can be committed).
  Every CSV row's `raw_path` points at its extract.
* `source_key` = `census_acs5_sf`. Each row's `source_url` is the national `.dat` file for its table.

## Geographies (each row's `geography` column)

* `zcta:` the centroid ZCTA plus every ZCTA in `zctas_within_800m`: 188 area×ZCTA pairs (157 distinct ZCTAs). The notes say whether a ZCTA is the "centroid ZCTA" or a "ZCTA within 800 m ring".
* `place:` the area's place_geoid (incorporated place or CDP): 73 areas.
* `cousub:` used for 25 areas:
  * the 19 NYC areas, at borough level, with the note "context only: much larger than the area". NYC city-wide `place:3651000` is not written.
  * 6 towns or townships with no separate place: Greenwich, Fairfield, Stratford (CT planning-region cousubs), Montclair, Bloomfield and Cranford.
* `tract:` the centroid tract: 98 areas.

Every GEO_ID was present in both the Geos file and every table. Each row's notes start with the Census NAME and the geography's role.

## Metrics (each has a matching `<metric>_moe` row, the 90% margin of error)

| metric | domain | source cells | value_type |
|---|---|---|---|
| acs_median_gross_rent_studio / _1br / _all_bedrooms | rent | B25031_002 / _003 / _001 | found |
| acs_median_gross_rent | rent | B25064_001 | found |
| acs_median_age | people | B01002_001 | found |
| acs_total_population | people | B01001_001 | found |
| acs_share_age_25_39 | people | (B01001_011+012+013+035+036+037) / B01001_001 | estimate |
| acs_households, acs_one_person_households_share | people | B11001_001; B11001_008 / B11001_001 | found; estimate |
| acs_occupied_units, acs_renter_share | people | B25003_001; B25003_003 / B25003_001 | found; estimate |
| acs_housing_units, acs_vacancy_rate | people | B25002_001; B25002_003 / B25002_001 | found; estimate |
| acs_units_built_<bucket>_share (10 buckets, 2020_later to 1939_earlier) | people | B25034_002..011 / B25034_001 | estimate |
| acs_median_year_built | people | B25035_001 | found |
| acs_renter_occupied_units, acs_renter_units_built_<bucket>_share (10 buckets) | people | B25036_013; B25036_014..023 / B25036_013 | found; estimate |

* **Shares** are percentages, computed by me and labelled `estimate`, with the formula in `method` and the denominator in `population_used`.
  Their MOEs are derived with the ACS General Handbook (ch. 8) approximation:
  * numerator MOE = the square root of the sum of the squared component MOEs;
  * MOE_p = sqrt(MOE_num² − p²·MOE_den²) / den;
  * if that radicand is negative, the ratio formula (+) is used;
  * controlled MOEs (code −555555555) are treated as 0.
* The vacancy rate covers **all** vacant units, including seasonal, for-sale and other vacant ones. It is not a rental vacancy rate.
* I did not collect race, ethnicity, ancestry, language or religion tables. The national directory contains B01001A–I race iterations; the script never downloads them.

## Coverage (rows)

people: 5,313 found, 18,336 estimate, 159 not_found · rent: 2,802 found, 270 not_found.

How often the published median is present:

| metric | ZCTA | place | cousub | tract |
|---|---|---|---|---|
| Studio median rent | 157/188 | 57/73 | 24/25 | 55/98 |
| 1BR median rent | 185/188 | 71/73 | 25/25 | 83/98 |
| B25064 median rent | 187/188 | 73/73 | 25/25 | 95/98 |

Reasons a value is `not_found`, with the Census code given in the notes:

* the estimate could not be computed because there were too few sample observations (−666666666), or its MOE could not be computed (−222222222);
* the denominator is 0;
* the MOE is controlled, which applies to total population for most cousubs and some places.

## Caveats and surprises

* **Top- and bottom-coding.** Rent medians are capped at "$3,500+": the file stores 3501, and I wrote 3500. Median year built is floored at "1939 or earlier": the file stores 1938, and I wrote 1939.
  Both keep `value_type=found`, but the notes say plainly that the value is the boundary, not the median. There are 65 such rows.
  * Top-coded 1BR medians: zcta:11249 (Williamsburg), zcta:07311 (Jersey City downtown), and the centroid tracts for Long Island City, Downtown Brooklyn, Garden City and Hoboken.
  * Top-coded studio medians: zcta:11003, zcta:11701, zcta:10543 and place:3644831 (Mamaroneck).
* No studio median exists at place level for 17 suburban areas, among them Garden City, Lynbrook, Valley Stream, Port Washington, Greenwich, Pelham and Red Bank. There are too few studios in the sample.
* **r1-briarwood:** the centroid tract 36081021603 and ZCTA 11424 both have zero population. Every rate there is not_found because the denominator is 0.
* `zctas_within_800m` sometimes crosses a state line. For example, r5-yonkers includes 07620 (NJ), whose 1BR median is not_found.
* ACS gross rent is what **sitting tenants** pay, rent plus utilities, over 2020–2024. It runs well below current asking rents, especially in rent-stabilised NYC stock. Treat it as context, not as an asking-rent benchmark.
* Small-area MOEs are wide. Tract 1BR MOEs of $300 or more are common, so read the `_moe` rows.
* Geographies are 2020 Census vintage. CT uses the 2022 planning-region county codes (09120, 09190, …), which match `areas.csv`.
