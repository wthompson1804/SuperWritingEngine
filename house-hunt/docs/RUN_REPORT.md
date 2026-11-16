# Run report (2026-11-16T00:58:34+00:00)

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
| pass every listing gate | 2659 | 2659 | +0 |
|   pending: a gate fact is unstated | 13534 | 13534 | +0 |
|   fail a gate | 4271 | 4271 | +0 |
| costed in the master table | 2634 | 2634 | +0 |
| within the $3,000 all-in cap | 1653 | 1653 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 821 | 822 | -1 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 347 | 348 | -1 |
| avoid cards | 36 | 36 | +0 |
|   shown with an asterisk (one thing to confirm) | 133 | 134 | -1 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 125 | 124 | +1 |
| held back for one confirmation | 28 | 28 | +0 |
| clean, waiting for a live check (not shown) | 28 | 28 | +0 |
| neighborhoods with 3+ shown places | 37 | 37 | +0 |
| buildings in the master table | 665 | 665 | +0 |

## Why units left

**excluded_by_confirmed_facts.csv**

- income-restricted unit: 38
- listing gone at live check: 17
- dogs not allowed (confirmed): 15
- stale listing: the listing page was last changed on 2026-04-13, 216 days before it was read (2026-11-15): more than six months unchanged: 7
- elevator not established: the sources conflict on which buildings have one: 6
- ground-floor unit: 5
- stale listing: the listing page was last changed on 2026-05-06, 193 days before it was read (2026-11-15): more than six months unchanged: 5
- no elevator (contradicted in the evidence pass): 3

**excluded_sketchy.csv**

- elevator not stated on any page and the building's height is not known (it was guessed from the unit label): 112
- listing 60+ days old: 26
- two or more things unconfirmed: elevator: 14
- conflicting dog policy: 13
- dogs allowed: 8
- availability: 7
- listing: 5
- no unit or building named: 5

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               7 |       99 |      38 |             0 |
| The Little-City Year      |              30 |      330 |     143 |             5 |
| The Old-Neighborhood Year |              43 |      164 |      75 |            29 |
| The Quiet-Street Year     |               7 |       11 |       9 |             0 |
| The Room-to-Breathe Year  |              32 |      209 |      76 |             0 |
| The Walk-Everywhere Year  |               6 |        8 |       6 |             2 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 85 |
| unit_floor | 60 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 20 |
| parking_type | 81 |
| parking_fee | 28 |
| pet_rent | 52 |
| pool | 39 |
| doorman | 31 |
| year_built | 50 |
| toll_rt_ezpass | 100 |
| transit_sat_median | 92 |
| near_violent_250m_24m | 20 |
| live_status | 90 |
| rent_first_full_payment_date | 65 |
| ev_pause_notes | 28 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every defect in docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (rules): 199 checks, 0 failed
```

**building amenities (cached pages)**
```
passing buildings: 693; already in csv: 751; to process: 0
```

**master tables**
```
  unit floor basis {'unknown': 1280, 'inferred': 1090, 'stated': 191, 'confirmed': 73} | label kind of inferred {'simple': 1076, 'complex': 14}
  confirmed floor values: 82 read, 9 matched no unit in the master (most are units that left the list), 3 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1855, 'live': 659, 'blocked': 73, 'changed': 30, 'gone': 17} | coordinates {'listing rows agree': 662, 'census_geocoder': 3}
  phone answers: 0 listing rows in 0 buildings (data/evidence/call_answers.csv is absent or empty)
  page modification date known: 384 | stale: {'no': 2487, 'open': 115, 'remove': 32} | elevator on a listing site's page alone: 377 buildings | overnight parking rule: {'none': 522, 'permit': 98, 'ban': 28, 'seasonal': 17}
  evidence facts not mapped to a field: {'building_size': 136, 'listing_broker': 61, 'building_site': 59, 'deposit': 28, 'application_fee': 25, 'owner_of_record': 24, 'listing_date': 21, 'building': 16, 'openigloo_summary': 16, 'move_in_fees': 16, 'available_units_listed': 16, 'building_name': 14, 'pet_count_limit': 14, 'dog': 12, 'listing_agent': 11, 'broker_fee': 10, 'deposit_and_fees': 10, 'one_time_fees': 10, 'openigloo_summary_counts': 10, 'building_size_openigloo': 9, 'listing_type': 9, 'own_site': 7, 'landlord': 6, 'amenities': 6, 'ownership_change': 6}
```

**rent terms**
```
2659 rows -> data/rent_terms.csv
offer_type: {'months_free': 1393, 'none': 875, 'other': 234, 'reduced_deposit_or_fee': 72, 'dollar_credit': 30, 'weeks_free': 35, 'look_and_lease': 20}
listed_price_is: {'net_effective': 236, 'gross': 1000, 'unknown': 1423}
needs_call: {'yes': 1685, 'no': 974}
```

**all-in cost**
```
units 2634; cost gate {'pass': 1653, 'fail': 981}; rent asterisk 1771; rent terms file present
  unknown building fees: 1430
  unknown pet rent: 995
  unknown parking fee: 1651
  unknown gas: 485
  gross above cap while basis passes: 35
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
evidence: 47 units excluded, shown 347, avoid cards 36, of them with an asterisk 133 ({'live check': 46, 'listing': 29, 'elevator': 19, 'dogs allowed': 19, 'availability': 15, 'eligibility': 5}), held for a confirmation 28, waiting for a live check 28
stages: 2634 costed -> -981 over the all-in cap -> -363 Jamaica safety rule -> -116 failed a gate on confirmed facts -> -125 removed by a reviewed verdict -> -181 sketchy -> -47 evidence exclusions -> 821 ranked
(kept 821 units; candidates 386; shown 416; pools: {'': 425, 'pool': 375, 'indoor': 21}
```

**rule tests on the output (docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (data): 218 checks, 0 failed
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 492, 'display': 310, 'provenance': 185, 'not_used': 18}
shown-list assertions: all pass
```

