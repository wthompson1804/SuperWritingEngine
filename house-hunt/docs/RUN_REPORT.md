# Run report (2026-11-15T23:36:34+00:00)

## Steps

| Step | Script | Result |
|---|---|---|
| parser tests (every example in docs/INDEPENDENT_CHECK.md) | `test_parsers.py` | ok |
| building amenities (cached pages) | `building_amenities.py --no-fetch` | ok |
| master tables | `build_master.py` | ok |
| rent terms | `rent_terms.py` | ok |
| all-in cost | `all_in.py` | ok |
| evidence rules (avoid, exclusions) | `avoid.py` | ok |
| ranking and selection | `rank.py` | ok |
| field registry, wiring check and shown-list assertions | `check_registry.py` | ok |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20464 | 20464 | +0 |
| pass every listing gate | 2598 | 2598 | +0 |
|   pending: a gate fact is unstated | 13595 | 13595 | +0 |
|   fail a gate | 4271 | 4271 | +0 |
| costed in the master table | 2575 | 2575 | +0 |
| within the $3,000 all-in cap | 1653 | 1653 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 980 | 980 | +0 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 332 | 332 | +0 |
| avoid cards | 35 | 35 | +0 |
|   shown with an asterisk (one thing to confirm) | 190 | 190 | +0 |
| held back for one confirmation | 61 | 61 | +0 |
| clean, waiting for a live check (not shown) | 59 | 59 | +0 |
| neighborhoods with 3+ shown places | 38 | 38 | +0 |
| buildings in the master table | 665 | 665 | +0 |

## Why units left

**excluded_by_confirmed_facts.csv**

- income-restricted unit: 40
- dogs not allowed (confirmed): 15
- elevator not established: the sources conflict on which buildings have one: 6
- no elevator (contradicted in the evidence pass): 4
- ground-floor unit: 3
- listing gone at live check: 2
- harvest note: BUILDING_FAILS: income-restricted lottery building with a waitlist (page says so), 0 units available: 1
- small dogs only. Trulia: 1

**excluded_sketchy.csv**

- elevator not stated on any page and the building's height is not known (it was guessed from the unit label): 108
- listing 60+ days old: 26
- two or more unconfirmed gate facts: 19
- conflicting dog policy: 13
- no unit or building named: 5
- live check judged the listing doubtful: 4
- thin syndicated feed: 3
- price far below the neighborhood: 2

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               7 |       57 |      24 |             0 |
| The Little-City Year      |              31 |      465 |     117 |             8 |
| The Old-Neighborhood Year |              42 |      150 |      85 |            24 |
| The Quiet-Street Year     |               8 |       14 |       9 |             0 |
| The Room-to-Breathe Year  |              36 |      282 |      88 |             0 |
| The Walk-Everywhere Year  |               8 |       12 |       9 |             3 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 81 |
| unit_floor | 61 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 16 |
| parking_type | 79 |
| parking_fee | 21 |
| pet_rent | 44 |
| pool | 31 |
| doorman | 27 |
| year_built | 55 |
| toll_rt_ezpass | 34 |
| transit_sat_median | 90 |
| near_violent_250m_24m | 25 |
| live_status | 95 |
| rent_first_full_payment_date | 70 |
| ev_pause_notes | 31 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**building amenities (cached pages)**
```
passing buildings: 692; already in csv: 750; to process: 0
```

**master tables**
```
  manager                {'stated': 285, 'confirmed': 229, 'unknown': 123, 'amenities_page': 28}
  utilities_included     {'unknown': 517, 'confirmed': 109, 'community_page': 23, 'stated': 16}
  unit floor basis {'unknown': 1285, 'inferred': 1064, 'stated': 146, 'confirmed': 80} | label kind of inferred {'simple': 1057, 'complex': 7}
  confirmed floor values: 114 read, 34 matched no unit in the master (most are units that left the list), 3 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1951, 'live': 559, 'blocked': 47, 'changed': 16, 'gone': 2} | coordinates {'listing rows agree': 662, 'census_geocoder': 3}
  evidence facts not mapped to a field: {'building_size': 133, 'building_site': 59, 'listing_broker': 56, 'listing_last_modified': 37, 'deposit': 24, 'owner_of_record': 24, 'listing_date': 21, 'application_fee': 19, 'building': 16, 'openigloo_summary': 16, 'move_in_fees': 16, 'available_units_listed': 16, 'pet_count_limit': 14, 'building_name': 13, 'dog': 12, 'deposit_and_fees': 10, 'one_time_fees': 10, 'openigloo_summary_counts': 10, 'listing_agent': 9, 'building_size_openigloo': 9, 'broker_fee': 8, 'listing_updated_at': 8, 'own_site': 7, 'price_basis': 6, 'amenities': 6}
```

**rent terms**
```
2598 rows -> data/rent_terms.csv
offer_type: {'months_free': 1387, 'none': 822, 'other': 234, 'reduced_deposit_or_fee': 72, 'dollar_credit': 28, 'weeks_free': 35, 'look_and_lease': 20}
listed_price_is: {'net_effective': 396, 'gross': 933, 'unknown': 1269}
needs_call: {'yes': 1685, 'no': 913}
```

**all-in cost**
```
units 2575; cost gate {'pass': 1653, 'fail': 922}; rent asterisk 1765; rent terms file present
  unknown building fees: 1517
  unknown pet rent: 1010
  unknown parking fee: 1652
  unknown gas: 486
  gross above cap while basis passes: 46
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
evidence: 60 units excluded, shown 332, avoid cards 35, of them with an asterisk 190 ({'floor': 154, 'live check': 30, 'elevator': 4, 'dogs allowed': 2}), held for a confirmation 61, waiting for a live check 59
stages: 2575 costed -> -922 over the all-in cap -> -363 Jamaica safety rule -> -72 failed a gate on confirmed facts -> -178 sketchy -> -60 evidence exclusions -> 980 ranked
(kept 980 units; candidates 427; shown 397; pools: {'': 549, 'pool': 412, 'indoor': 19}
```

**field registry, wiring check and shown-list assertions**
```
field registry: {'used': 447, 'display': 304, 'provenance': 153, 'not_used': 18}
shown-list assertions: all pass
```

