# Run report (2026-11-16T00:06:03+00:00)

## Steps

| Step | Script | Result |
|---|---|---|
| parser tests (every example in docs/INDEPENDENT_CHECK.md) | `test_parsers.py` | ok |
| rule tests (every defect in docs/INDEPENDENT_CHECK_2.md) | `test_rules.py` | ok |
| building amenities (cached pages) | `building_amenities.py --no-fetch` | ok |
| master tables | `build_master.py` | ok |
| rent terms | `rent_terms.py` | ok |
| all-in cost | `all_in.py` | ok |
| evidence rules (avoid, exclusions) | `avoid.py` | ok |
| ranking and selection | `rank.py` | ok |
| rule tests on the output (docs/INDEPENDENT_CHECK_2.md) | `test_rules.py --data` | ok |
| field registry, wiring check, shown-list assertions and the review rule | `check_registry.py` | ok |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20464 | 20464 | +0 |
| pass every listing gate | 2598 | 2598 | +0 |
|   pending: a gate fact is unstated | 13595 | 13595 | +0 |
|   fail a gate | 4271 | 4271 | +0 |
| costed in the master table | 2573 | 2573 | +0 |
| within the $3,000 all-in cap | 1655 | 1655 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 621 | 621 | +0 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 210 | 210 | +0 |
| avoid cards | 33 | 33 | +0 |
|   shown with an asterisk (one thing to confirm) | 130 | 130 | +0 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 109 | 109 | +0 |
| held back for one confirmation | 53 | 53 | +0 |
| clean, waiting for a live check (not shown) | 53 | 53 | +0 |
| neighborhoods with 3+ shown places | 26 | 26 | +0 |
| buildings in the master table | 665 | 665 | +0 |

## Why units left

**excluded_by_confirmed_facts.csv**

- income-restricted unit: 40
- dogs not allowed (confirmed): 15
- elevator not established: the sources conflict on which buildings have one: 6
- ground-floor unit: 5
- no elevator (contradicted in the evidence pass): 3
- listing gone at live check: 2
- harvest note: BUILDING_FAILS: income-restricted lottery building with a waitlist (page says so), 0 units available: 1
- small dogs only. Trulia: 1

**excluded_sketchy.csv**

- two or more things unconfirmed: floor: 218
- elevator not stated on any page and the building's height is not known (it was guessed from the unit label): 112
- cost near the cap: 109
- availability: 60
- two or more things unconfirmed: elevator: 59
- lease term: 57
- floor: 51
- dogs allowed: 35

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               3 |       44 |      15 |             0 |
| The Little-City Year      |              25 |      305 |      78 |             7 |
| The Old-Neighborhood Year |              36 |      116 |      57 |            24 |
| The Quiet-Street Year     |               6 |        8 |       6 |             0 |
| The Room-to-Breathe Year  |              23 |      141 |      49 |             0 |
| The Walk-Everywhere Year  |               5 |        7 |       5 |             2 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 81 |
| unit_floor | 76 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 20 |
| parking_type | 76 |
| parking_fee | 21 |
| pet_rent | 44 |
| pool | 26 |
| doorman | 28 |
| year_built | 50 |
| toll_rt_ezpass | 36 |
| transit_sat_median | 96 |
| near_violent_250m_24m | 25 |
| live_status | 95 |
| rent_first_full_payment_date | 67 |
| ev_pause_notes | 33 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every defect in docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (rules): 78 checks, 0 failed
```

**building amenities (cached pages)**
```
passing buildings: 692; already in csv: 750; to process: 0
```

**master tables**
```
  manager                {'stated': 285, 'confirmed': 229, 'unknown': 123, 'amenities_page': 28}
  utilities_included     {'unknown': 517, 'confirmed': 109, 'community_page': 23, 'stated': 16}
  unit floor basis {'unknown': 1277, 'inferred': 1090, 'stated': 138, 'confirmed': 68} | label kind of inferred {'simple': 1076, 'complex': 14}
  confirmed floor values: 77 read, 9 matched no unit in the master (most are units that left the list), 3 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1941, 'live': 565, 'blocked': 47, 'changed': 18, 'gone': 2} | coordinates {'listing rows agree': 662, 'census_geocoder': 3}
  evidence facts not mapped to a field: {'building_size': 133, 'building_site': 59, 'listing_broker': 56, 'listing_last_modified': 37, 'deposit': 24, 'owner_of_record': 24, 'listing_date': 21, 'application_fee': 19, 'building': 16, 'openigloo_summary': 16, 'move_in_fees': 16, 'available_units_listed': 16, 'pet_count_limit': 14, 'building_name': 13, 'dog': 12, 'deposit_and_fees': 10, 'one_time_fees': 10, 'openigloo_summary_counts': 10, 'listing_agent': 9, 'building_size_openigloo': 9, 'broker_fee': 8, 'listing_updated_at': 8, 'own_site': 7, 'amenities': 6, 'ownership_change': 6}
```

**rent terms**
```
2598 rows -> data/rent_terms.csv
offer_type: {'months_free': 1387, 'none': 822, 'other': 234, 'reduced_deposit_or_fee': 72, 'dollar_credit': 28, 'weeks_free': 35, 'look_and_lease': 20}
listed_price_is: {'net_effective': 236, 'gross': 945, 'unknown': 1417}
needs_call: {'yes': 1677, 'no': 921}
```

**all-in cost**
```
units 2573; cost gate {'pass': 1655, 'fail': 918}; rent asterisk 1763; rent terms file present
  unknown building fees: 1430
  unknown pet rent: 1009
  unknown parking fee: 1651
  unknown gas: 485
  gross above cap while basis passes: 32
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
evidence: 36 units excluded, shown 210, avoid cards 33, of them with an asterisk 130 ({'floor': 60, 'live check': 16, 'lease term': 14, 'listing': 12, 'cost near the cap': 12, 'elevator': 8, 'dogs allowed': 6, 'other': 2}), held for a confirmation 53, waiting for a live check 53
stages: 2573 costed -> -918 over the all-in cap -> -363 Jamaica safety rule -> -73 failed a gate on confirmed facts -> -109 removed by a reviewed verdict -> -453 sketchy -> -36 evidence exclusions -> 621 ranked
(kept 621 units; candidates 292; shown 279; pools: {'': 355, 'pool': 248, 'indoor': 18}
```

**rule tests on the output (docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (data): 84 checks, 0 failed
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 462, 'display': 309, 'provenance': 178, 'not_used': 18}
shown-list assertions: all pass
```

