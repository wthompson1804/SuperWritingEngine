# Run report (2026-11-17T16:58:25+00:00)

## Steps

| Step | Script | Result |
|---|---|---|
| parser tests (every example in docs/INDEPENDENT_CHECK.md) | `test_parsers.py` | ok |
| rule tests (every repaired defect and rule, pure) | `test_rules.py` | ok |
| building amenities (cached pages) | `building_amenities.py --no-fetch` | ok |
| master tables | `build_master.py` | ok |
| rent terms | `rent_terms.py` | ok |
| all-in cost | `all_in.py` | ok |
| evidence rules (avoid, exclusions) | `avoid.py` | ok |
| ranking and selection | `rank.py` | ok |
| rule tests on the output | `test_rules.py --data` | ok |
| field registry, wiring check, shown-list assertions and the review rule | `check_registry.py` | ok |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20468 | 20468 | +0 |
| pass every listing gate | 1026 | 1026 | +0 |
|   pending: a gate fact is unstated | 7873 | 7873 | +0 |
|   fail a gate | 11569 | 11569 | +0 |
| costed in the master table | 2451 | 2451 | +0 |
| within the $3,000 all-in cap | 1469 | 1469 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 119 | 119 | +0 |
| shown (real apartments, at most one open item, up to 8 per building, after the thin-neighborhood rule) | 89 | 89 | +0 |
|   neighborhoods shown | 25 | 25 | +0 |
|   buildings shown | 48 | 48 | +0 |
| not an apartment: floor plan, building price or co-living room (data/excluded_not_an_apartment.csv) | 30 | 30 | +0 |
| thin neighborhoods cut (one apartment, not both well attested and promising) | 12 | 12 | +0 |
| avoid cards | 14 | 14 | +0 |
|   shown with an asterisk (one thing to confirm) | 26 | 26 | +0 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 11 | 11 | +0 |
| held back for one confirmation | 6 | 6 | +0 |
| neighborhoods with 3+ shown places | 15 | 15 | +0 |
| buildings in the master table | 578 | 578 | +0 |

## Why units left

**excluded_by_confirmed_facts.csv**

- over_2200: listed base rent above $2,200 (owner, 2026-11-17): 888
- income-restricted unit: 17
- listing gone at live check: 13
- the page was read on 2026-11-15): more than six months unchanged: 10
- dogs not allowed (confirmed): 5
- stale listing: the listing page was last changed on 2026-01-27, 299 days by the first tour day (2026-11-22: 2
- stale listing: the listing page was last changed on 2025-12-08, 349 days by the first tour day (2026-11-22: 2
- ground-floor unit: a bare apartment number in a building numbered in sequence, at most the average number of apartments per floor, reads as the first floor: 1

**excluded_sketchy.csv**

- listing: 7
- listing 60+ days old: 6
- two or more things unconfirmed: dogs allowed: 5
- no unit or building named: 3
- two or more things unconfirmed: elevator: 3
- live check judged the listing doubtful: 1
- thin syndicated feed: 1
- availability: 1

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               2 |        2 |       0 |             0 |
| The Little-City Year      |              12 |       36 |      30 |             3 |
| The Old-Neighborhood Year |              13 |       29 |      18 |             8 |
| The Room-to-Breathe Year  |              17 |       48 |      41 |             0 |
| The Walk-Everywhere Year  |               2 |        4 |       0 |             3 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 93 |
| unit_floor | 69 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 19 |
| parking_type | 79 |
| parking_fee | 35 |
| pet_rent | 58 |
| pool | 22 |
| doorman | 2 |
| year_built | 29 |
| toll_rt_ezpass | 100 |
| transit_sat_median | 99 |
| near_violent_250m_24m | 11 |
| live_status | 78 |
| rent_first_full_payment_date | 67 |
| ev_pause_notes | 18 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every repaired defect and rule, pure)**
```
test_rules (rules): 1053 checks, 0 failed
```

**building amenities (cached pages)**
```
passing buildings: 608; already in csv: 754; to process: 0
```

**master tables**
```
  unit floor basis {'unknown': 1263, 'inferred': 936, 'stated': 187, 'confirmed': 65} | label kind of inferred {'simple': 921, 'complex': 15}
  confirmed floor values: 75 read, 10 matched no unit in the master (most are units that left the list), 3 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1547, 'live': 756, 'blocked': 63, 'gone': 45, 'changed': 40} | coordinates {'listing rows agree': 569, 'census_geocoder': 4, 'census_geocoder (address check)': 4, 'listing majority, unverified': 1}
  phone answers: 0 listing rows in 0 buildings (data/evidence/call_answers.csv is absent or empty)
  page modification date known: 1120 | stale: {'no': 2244, 'open': 174, 'remove': 33} | elevator on a listing site's page alone: 384 buildings | overnight parking rule: {'none': 458, 'permit': 80, 'ban': 24, 'seasonal': 16}
  evidence facts not mapped to a field: {'building_size': 121, 'listing_broker': 60, 'building_site': 54, 'deposit': 26, 'application_fee': 23, 'owner_of_record': 22, 'listing_date': 21, 'openigloo_summary': 16, 'building': 15, 'move_in_fees': 15, 'building_name': 13, 'available_units_listed': 13, 'pet_count_limit': 12, 'openigloo_summary_counts': 10, 'building_size_openigloo': 9, 'dog': 8, 'broker_fee': 7, 'own_site': 7, 'listing_type': 7, 'landlord': 6, 'ownership_change': 6, 'amenities': 5, 'one_time_fee': 5, 'former_or_other_name': 5, 'other_fees': 4}
```

**rent terms**
```
2505 rows -> data/rent_terms.csv
offer_type: {'months_free': 1329, 'none': 817, 'other': 211, 'reduced_deposit_or_fee': 69, 'dollar_credit': 29, 'weeks_free': 35, 'look_and_lease': 15}
listed_price_is: {'net_effective': 152, 'gross': 949, 'unknown': 1404}
needs_call: {'yes': 1587, 'no': 918}
```

**all-in cost**
```
  unknown building fees: 1323
  unknown pet rent: 0
  unknown parking fee: 1513
  unknown gas: 457
  pet rent estimated: 925 | within the cap but likely over once parking and fees are known: 262
  gross above cap while basis passes: 30
```

**evidence rules (avoid, exclusions)**
```
                                              121 seaman ave|10034                                                                                                                     management: city records in the last 6 months above the 90th percentile on class_c_violations, heat_hot_water_complaints
                                             123 linden blvd|11226                                                                                                                                       management: 3 separate dated tenant reports of problems in the last 6 months (all on one reviews page)
                                              1256 ocean ave|11230                                                                                                                               management: city records in the last 6 months above the 90th percentile on class_c_violations, pest_complaints
                       135-23 82nd ave 3e queens ny 11435 us|11435                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                              13523 82nd ave|11435                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                               14202 84th dr|11435                                                                                          
```

**ranking and selection**
```
evidence: 19 units excluded, shown 89, avoid cards 14, of them with an asterisk 26 ({'listing': 11, 'elevator': 9, 'eligibility': 3, 'availability': 2, 'dogs allowed': 1}), held for a confirmation 6; shown and never re-read (information only, not an open item) 21
stages: 2451 costed -> -982 over the all-in cap -> -330 Jamaica safety rule -> -941 failed a gate on confirmed facts -> -30 not an apartment (floor plan, building price, co-living room) -> -11 removed by a reviewed verdict -> -0 sibling floor rule -> -19 sketchy -> -19 evidence exclusions -> 119 ranked
shown buildings 48; disclosures: {'floor not published': 85, 'special offer': 51, 'one-time costs': 19, 'lease term': 11, 'washer and dryer to confirm': 11, 'overnight street parking': 6, 'broker fee': 4, 'income requirement': 2, 'dog weight limit not published': 1, 'net-effective rent': 1, 'something else to know': 1, 'condo rented by its owner': 1}
(kept 119 units; candidates 97; shown 97; pools: {'': 94, 'pool': 22, 'indoor': 3}
```

**rule tests on the output**
```
test_rules (data): 427 checks, 0 failed
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 570, 'display': 341, 'provenance': 212, 'not_used': 14}
shown-list assertions: all pass
```

