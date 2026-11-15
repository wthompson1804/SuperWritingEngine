# NYC official building records (harvest notes)

Script: `scripts/nyc_building_records.py` (idempotent; raw responses cached in `raw/nyc_records/`).
Run of 2026-11-15, about 20:49 to 20:50 UTC. As-of date 2026-11-15.
Source: NYC Open Data (Socrata SODA API, `data.cityofnewyork.us/resource/<id>.json`). robots.txt has
`Crawl-delay: 1` for `*` and no group naming Claude; the script forces 1 request per second for this host
(lib.py's default for the host is 0.3 s, overridden at run time, lib.py itself not edited). The whole run is 26 requests.

## Outputs

| File | What |
|---|---|
| `data/evidence/nyc_records.csv` | 12,672 rows: 99 addr_keys (89 distinct BBLs) x 27 record types x periods |
| `data/evidence/nyc_records_baseline.csv` | citywide yardstick, 6 metrics x 2 periods x 5 size bands |
| `data/evidence/nyc_records_flags.csv` | one row per flag per building (`flag = none` when a building has no flag) |
| `data/evidence/nyc_records_match.csv` | per building: PLUTO address, class, units, BINs, which datasets know the lot |
| `data/evidence/nyc_records_summary.json` | the numbers quoted here |

Periods: `last_6_months` 2026-05-15 to 2026-11-15, `last_24_months` 2024-11-15 to 2026-11-15, `2023`, `2024`,
`2025`, `2026_ytd`. Extra period labels where a time window makes no sense: `current` (open violations, devices,
registration, PLUTO), `latest_filing` (bedbugs), `2024_to_date` (evictions), `all_years_in_dataset` (DOB complaints).

`query_url` on each row is the single-building count query that reproduces the number. The fetch itself was one
batched query per dataset (`bbl in (...)`), cached. `--verify 16` re-ran 16 of those URLs live: 16 of 16 agreed.

## Datasets

| Id | Name | Used for | Match key |
|---|---|---|---|
| 64uk-42ks | PLUTO (version 26v2) | residential units, class, lot address | BBL |
| wvxf-dwi5 | Housing Maintenance Code Violations | class A/B/C opened in period (by `inspectiondate`); class C currently open | BBL |
| ygpa-z7cr | Housing Maintenance Code Complaints and Problems | heat/hot water, pests, mold, elevator, door/window + intercom, all | BBL |
| kj4p-ruqc | Buildings Subject to HPD Jurisdiction | does HPD know the lot | boro/block/lot |
| tesw-yqqr + feu5-w2e2 | Multiple Dwelling Registrations + Registration Contacts | owner, head officer, managing agent, site manager | boro/block/lot, then registrationid |
| wz6d-d3jb | Bedbug Reporting | latest annual filing: infested units | BBL |
| erm2-nwe9 | 311 Service Requests 2020 to present | heat/hot water, Elevator (DOB), ELEVATOR (HPD), Noise - Residential, UNSANITARY CONDITION, Illegal Parking, Blocked Driveway, Derelict/Abandoned Vehicle | BBL |
| eabe-havv | DOB Complaints Received | elevator categories | BIN |
| e5aq-a4j2 | DOB NOW Elevator Safety Compliance | device list: active elevators, last periodic inspection, last CAT1 filing | BBL |
| 855j-jady | DOB Safety Violations, `device_type = 'Elevators'` | elevator violations issued in period; active now | BBL |
| 6z8x-wfk4 | Evictions (city marshals) | residential evictions executed 2024 to date | BBL; address fallback for rows with no BBL (none matched) |

Also seen, not used: `juyv-2jek` DOB NOW: Build Elevator Device Details and `kfp4-dz4h` Elevator Permit Applications
(permit filings, not condition).

BIN comes from whichever of the HPD, DOB and bedbug datasets carry one for the lot (PLUTO has no BIN). All 89 lots got at least one.

## What failed or is weaker than asked

1. **DOB Complaints Received (eabe-havv) has no usable recent data.** As retrieved it holds 866,335 rows and the latest
   `date_entered` year is 2022 (1,224 rows; 2021: 673; 2020: 555). Nothing falls in any reporting period, so every
   `dob_elevator_complaints` period row is 0 **because the dataset is empty there, not because the building is clean**.
   The `all_years_in_dataset` row keeps the older history. The replacement is 311 `complaint_type = 'Elevator'`,
   agency DOB (`sr311_elevator_dob`), which is the public intake channel for the same complaints; complaints entered
   directly by DOB staff are not in it.
2. **DOB elevator category codes.** The category list attached to the dataset
   (`DOBComplaints_complaint_category_list.pdf`) confirms 13 (elevator in FDNY readiness), 62 and 63 (elevator danger
   condition / shaft open), 80 (not inspected / illegal / no permit), 81 (accident). 6S, 6M and 7G occur in the data
   (latest 2022) but are **not in that PDF**; the 311 descriptors "Elevator - Single Device On Property/No Alternate
   Service" and "Elevator - Multiple Devices On Property" appear to be the same things, which is an inference.
3. **Car break-ins and thefts are not in these datasets.** Only the street-parking stress signals asked for (311
   Illegal Parking, Blocked Driveway, Derelict/Abandoned Vehicle) are here. Vehicle crime needs NYPD complaint data.
4. `docs/SOURCES.md` was not edited (shared file); the new dataset ids are in the table above.

## Counting rules

- HPD complaints are counted at **problem** level (a complaint can hold several problems). `detail` gives distinct
  complaints and distinct apartments.
- "Elevator complaints" in the baseline and flags = 311 Elevator requests routed to DOB. HPD's ELEVATOR category is kept
  as its own record type and never added in: citywide its top problem codes are "dirty or unsanitary", "light fixture
  broken", "glass or mirror broken", not outages.
- 311 HEAT/HOT WATER, UNSANITARY CONDITION and ELEVATOR (HPD) are the same reports HPD receives. Do not add them to
  the HPD complaint counts.
- DOB elevator violations (855j-jady) are almost all paperwork types: failure to file or to correct the annual CAT1 or
  periodic inspection (`FTF-…`, `FTC-…`). They show neglected compliance, not a recorded outage.
- Bedbug counts are self-reported by the owner once a year.
- `hpd_registration` detail holds names from the public HPD registry (owner corporation, head officer, managing agent,
  site manager).

## Matching and match rates (89 distinct BBLs)

| Check | Lots |
|---|---|
| in PLUTO | 89/89 |
| in HPD building list | 89/89 |
| HPD registration found | 88/89 (missing: 3051900053, 2561 Bedford Ave, PLUTO says 8 units) |
| any HPD complaint row since 2023 | 83/89 |
| any HPD violation row | 87/89 |
| any 311 row of the chosen types since 2023 | 88/89 |
| DOB elevator device record | 86/89 (missing: 4096810095 class C1 10 units; 4096310222 class C3 4 units; 4096487501 condo lot) |
| bedbug filing | 86/89 |
| any residential eviction since 2024 | 43/89 |

Things that limit the match:

- **The BBL was assigned upstream by nearest lot** (`enrich_nyc_pluto.py`). For 26 of 99 addr_keys the candidate's house
  number differs from the PLUTO lot address. Most are multi-building or address-range lots (for example the Jackson
  Heights lots 4014510012 and 4014510047, 162 units each), a few may be the wrong lot. They are listed in
  `nyc_records_summary.json` (`house_number_disagrees`) and carry a `caution` in the flags file. Check before using a flag from those rows.
- **Counts are for the whole tax lot.** On a lot with several buildings the numbers and the unit count both cover
  all of them, so the rate is consistent but not specific to one entrance.
- **Condo lots (75xx) and non-D classes**: 11 lots are not class D (8 condo RM/R4, 3 class C walk-up classes, including
  1020010038 with 187 units). HPD and 311 may file condo records under unit lots, so zeros there are weaker. A missing
  elevator device record on a C-class lot may mean no elevator.
- 10 addr_keys share a lot with another candidate (unit-level listings or neighbouring entrances), so 99 addr_keys reduce to 89 lots.

## Baseline (the yardstick)

Population: every PLUTO lot with `unitsres >= 20` and `bldgclass like 'D%'` (elevator apartment classes): **13,370 lots**.
No sampling was needed: one grouped query per metric returns counts by BBL for the whole city, so the brief's
"random sample of at least 1,500" is replaced by the full population (no sampling error). Lots with no record count as
zero. Rate = records / PLUTO residential units x 100.

| metric | period | share with zero | median | p80 | p90 | p95 |
|---|---|---|---|---|---|---|
| heat/hot water complaints | 24 months | 30% | 5.48 | 38.75 | 80.56 | 138.60 |
| heat/hot water complaints | 6 months | 66% | 0 | 2.70 | 6.82 | 13.64 |
| pest complaints | 24 months | 52% | 0 | 8.16 | 17.86 | 31.46 |
| pest complaints | 6 months | 70% | 0 | 2.27 | 5.66 | 10.43 |
| mold complaints | 24 months | 56% | 0 | 4.76 | 10.10 | 16.67 |
| mold complaints | 6 months | 75% | 0 | 1.28 | 3.12 | 5.46 |
| elevator complaints (311 to DOB) | 24 months | 59% | 0 | 4.09 | 10.42 | 19.40 |
| elevator complaints (311 to DOB) | 6 months | 78% | 0 | 0.62 | 2.90 | 6.25 |
| class C violations | 24 months | 37% | 4.23 | 32.98 | 67.19 | 111.11 |
| class C violations | 6 months | 60% | 0 | 6.45 | 15.79 | 28.26 |

The file also has HPD elevator-category complaints and size bands (20-49, 50-99, 100-199, 200+). Rates fall with size:
the 24-month elevator p90 is 12.5 per 100 units for 20 to 49 units and 2.93 for 200+. Flags use the all-sizes
line, so it is lenient on very large buildings and strict on small ones.

## Flags

Rules: building rate above the all-sizes p90 for the same period (heat/hot water, pests, mold, elevator, class C
violations; 6 and 24 months), plus `elevator_complaints_24m_ge_3` and `elevator_complaints_6m_ge_1` on raw counts. Each
row has the count, rate, median, p80, p90, p95 and `above_p95`.

38 of 89 lots (44 of 99 addr_keys) carry at least one flag. Lots with the most flags:

| BBL | PLUTO address | units | flags |
|---|---|---|---|
| 4014510012 | 34-18 91 St, Jackson Heights | 162 | 10: heat 24m 228 (140.7/100), class C 24m 351, elevator 24m 36, pests, mold |
| 4097120161 | 142-02 84 Dr | 90 | 8: pests 24m 131 (145.6/100), class C, mold, elevator |
| 4014510047 | 34-19 90 St, Jackson Heights | 162 | 6: class C 24m 272, pests, mold, elevator 24m 18 |
| 4096810095 | 148-09 90 Ave | 10 (class C1) | 6, small-building caution |
| 3017710016 | 96 Hart St | 20 | 6: heat 24m 20, elevator |
| 1019370001 | 273 W 131 St | 44 | elevator 24m 33 (75/100) |
| 4068090001 | 75-25 153 St | 388 | elevator 24m 77 (19.9/100), mold 6m |
| 4050490038 | 143-45 Sanford Ave | 61 | elevator 24m 16 (26.2/100) |

## Caveats for anyone reading the numbers

- **Complaints are reports, not findings.** One tenant can file many; a building with organised tenants looks worse
  than a building where nobody calls. Violations are an inspector's finding and are the firmer signal.
- **Large buildings have more of everything**; use `per_100_units`, and mind the size effect above.
- **The 6-month window (15 May to 15 Nov) holds only about six weeks of heat season** (from 1 Oct). The 6-month heat
  baseline covers the same window, so the comparison is fair, but low counts there do not show a warm winter.
- **Small buildings**: one complaint in a 10-unit building is 10 per 100 units. The flags file marks lots under 20 units.
- The two raw-count elevator flags are wide: 30 addr_keys meet "3 or more in 24 months" and 24 meet "1 or more in
  6 months". A single 311 elevator call in a 605-unit building trips the second one. Read them with the rate and p90 columns.
- A zero is only as good as the match: see the cautions on house-number disagreement and condo lots.

## Reuse

`python3 scripts/nyc_building_records.py` rebuilds everything for the candidate file.
`--buildings other.csv` (columns addr_key, address, zip, pluto_bbl) or `--bbl 4006060029 --bbl ...` for new lots
(note: this rewrites the same output files for that set). `--as-of YYYY-MM-DD`, `--refresh`, `--verify N`.
