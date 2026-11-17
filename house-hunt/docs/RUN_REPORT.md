# Run report (2026-11-17T21:39:23+00:00)

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
| listings harvested (after dedupe) | 21095 | 21095 | +0 |
| pass every listing gate | 1179 | 1179 | +0 |
|   pending: a gate fact is unstated | 7512 | 7512 | +0 |
|   fail a gate | 12404 | 12404 | +0 |
| costed in the master table | 1097 | 1097 | +0 |
| within the $3,000 all-in cap | 1097 | 1097 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 436 | 436 | +0 |
| shown (real apartments, at most one open item, up to 8 per building, after the thin-neighborhood rule) | 365 | 365 | +0 |
|   neighborhoods shown | 66 | 66 | +0 |
|   buildings shown | 196 | 196 | +0 |
| not an apartment: floor plan, building price or co-living room (data/excluded_not_an_apartment.csv) | 80 | 80 | +0 |
| thin neighborhoods cut (one apartment, not both well attested and promising) | 38 | 38 | +0 |
| avoid cards | 17 | 17 | +0 |
|   shown with an asterisk (one thing to confirm) | 246 | 246 | +0 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 32 | 32 | +0 |
| held back for one confirmation | 33 | 33 | +0 |
| neighborhoods with 3+ shown places | 40 | 40 | +0 |
| buildings in the master table | 617 | 617 | +0 |

## Why units left

**excluded_by_confirmed_facts.csv**

- ground-floor unit: 29
- income-restricted unit: 29
- the page was read on 2026-11-15): more than six months unchanged: 26
- listing gone at live check: 17
- ground-floor unit: a bare apartment number in a building numbered in sequence, at most the average number of apartments per floor, reads as the first floor: 12
- the page was read on 2026-11-17): more than six months unchanged: 9
- dogs not allowed (confirmed): 5
- ground-floor home: a townhome (plan: The New "Ashcroft" - Fully Renovated One Bedroom Home with Patio): 3

**excluded_sketchy.csv**

- two or more things unconfirmed: floor and elevator: 62
- listing: 42
- no unit or building named: 37
- listing 60+ days old: 29
- availability: 21
- floor 3 or above (inferred) and no elevator stated on any page or record, and the building's height is not known (owner, 2026-11-17: floor 3 and above need an elevator): 11
- dogs allowed: 8
- thin syndicated feed: 7

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               5 |       31 |      30 |             0 |
| The Little-City Year      |              25 |      105 |      84 |             4 |
| The Old-Neighborhood Year |              16 |       67 |      55 |            10 |
| The Quiet-Street Year     |               7 |        9 |       3 |             0 |
| The Room-to-Breathe Year  |              54 |      218 |     191 |             0 |
| The Walk-Everywhere Year  |               2 |        6 |       2 |             3 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 89 |
| unit_floor | 39 |
| elevator_basis | 30 |
| dog_weight_limit_lb | 16 |
| parking_type | 73 |
| parking_fee | 25 |
| pet_rent | 48 |
| pool | 10 |
| doorman | 1 |
| year_built | 38 |
| toll_rt_ezpass | 100 |
| transit_sat_median | 91 |
| near_violent_250m_24m | 5 |
| live_status | 94 |
| rent_first_full_payment_date | 77 |
| ev_pause_notes | 8 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every repaired defect and rule, pure)**
```
test_rules (rules): 1128 checks, 0 failed
```

**building amenities (cached pages)**
```
passing buildings: 680; already in csv: 1205; to process: 0
```

**master tables**
```
  unit floor basis {'unknown': 688, 'inferred': 363, 'confirmed': 38, 'stated': 8} | label kind of inferred {'simple': 359, 'complex': 4}
  confirmed floor values: 56 read, 18 matched no unit in the master (most are units that left the list), 5 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'live': 523, 'not checked': 466, 'blocked': 58, 'changed': 33, 'gone': 17} | coordinates {'listing rows agree': 611, 'census_geocoder (address check)': 4, 'listing majority, unverified': 1, 'census_geocoder': 1}
  phone answers: 0 listing rows in 0 buildings (data/evidence/call_answers.csv is absent or empty)
  page modification date known: 1003 | stale: {'no': 953, 'open': 91, 'remove': 53} | elevator on a listing site's page alone: 135 buildings | overnight parking rule: {'none': 513, 'permit': 76, 'ban': 16, 'seasonal': 12}
  evidence facts not mapped to a field: {'building_size': 45, 'rent_stated_in_listing_text': 21, 'listing_broker': 18, 'building_site': 13, 'listing_type': 12, 'application_fee': 11, 'listing_date': 10, 'move_in_fees': 9, 'deposit': 8, 'available_units_listed': 8, 'dog': 6, 'building_site_url': 6, 'broker_fee': 5, 'listing_agent': 5, 'openigloo_summary_counts': 5, 'open_violations_note': 5, 'deposit_and_fees': 4, 'building': 4, 'landlord': 3, 'ownership': 3, 'building_name': 3, 'listing_kind': 3, 'own_site': 3, 'board_approval': 2, 'pet_deposit': 2}
```

**rent terms**
```
1179 rows -> data/rent_terms.csv
offer_type: {'months_free': 312, 'other': 115, 'none': 635, 'reduced_deposit_or_fee': 44, 'look_and_lease': 22, 'weeks_free': 4, 'dollar_credit': 47}
listed_price_is: {'net_effective': 12, 'unknown': 352, 'gross': 815}
needs_call: {'yes': 411, 'no': 768}
```

**all-in cost**
```
  unknown building fees: 862
  unknown pet rent: 0
  unknown parking fee: 884
  unknown gas: 346
  pet rent estimated: 620 | within the cap but likely over once parking and fees are known: 0
  gross above cap while basis passes: 0
```

**evidence rules (avoid, exclusions)**
```
                       135-23 82nd ave 3e queens ny 11435 us|11435                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                              13523 82nd ave|11435                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                               14202 84th dr|11435                                                                                                              management: city records in the last 6 months above the 90th percentile on class_c_violations, mold_complaints, pest_complaints
                                           14345 sanford ave|11355                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                             148-33 90th ave|11435                                                                                                    management: city records in the last 6 months above the 90th percentile on class_c_violations, heat_hot_water_complaints, pest_complaints
                                             148-37 88th ave|11435                                                                                          
```

**ranking and selection**
```
evidence: 20 units excluded, shown 365, avoid cards 17, of them with an asterisk 246 ({'floor and elevator': 209, 'listing': 16, 'elevator': 10, 'availability': 5, 'dogs allowed': 3, 'eligibility': 3}), held for a confirmation 33; shown and never re-read (information only, not an open item) 48
stages: 1097 costed -> -0 over the all-in cap -> -235 Jamaica safety rule -> -143 failed a gate on confirmed facts -> -80 not an apartment (floor plan, building price, co-living room) -> -32 removed by a reviewed verdict -> -0 sibling floor rule -> -151 sketchy -> -20 evidence exclusions -> 436 ranked
shown buildings 196; disclosures: {'income requirement': 192, 'floor not published': 137, 'special offer': 133, 'lease term': 55, 'one-time costs': 52, 'no broker fee': 35, 'washer and dryer to confirm': 31, 'overnight street parking': 30, 'something else to know': 21, 'dog weight limit not published': 12, 'broker fee': 7, 'furnished apartment': 6, 'condo rented by its owner': 4, 'credit score requirement': 4, 'net-effective rent': 1}
(kept 436 units; candidates 308; shown 324; pools: {'': 391, 'pool': 42, 'indoor': 3}
```

**rule tests on the output**
```
test_rules (data): 720 checks, 0 failed
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 575, 'display': 345, 'provenance': 213, 'not_used': 14}
shown-list assertions: all pass
```

