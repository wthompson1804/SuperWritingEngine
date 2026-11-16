# Run report (2026-11-16T01:45:23+00:00)

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
| rule tests on the output (docs/INDEPENDENT_CHECK_2.md) | `test_rules.py --data` | FAILED |
| field registry, wiring check, shown-list assertions and the review rule | `check_registry.py` | FAILED |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20464 | 20464 | +0 |
| pass every listing gate | 2659 | 2659 | +0 |
|   pending: a gate fact is unstated | 13534 | 13534 | +0 |
|   fail a gate | 4271 | 4271 | +0 |
| costed in the master table | 2632 | 2632 | +0 |
| within the $3,000 all-in cap | 1613 | 1613 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 767 | 760 | +7 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 505 | 513 | -8 |
| avoid cards | 34 | 34 | +0 |
|   shown with an asterisk (one thing to confirm) | 312 | 317 | -5 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 115 | 122 | -7 |
| held back for one confirmation | 35 | 30 | +5 |
| clean, waiting for a live check (not shown) | 35 | 30 | +5 |
| neighborhoods with 3+ shown places | 43 | 44 | -1 |
| buildings in the master table | 665 | 665 | +0 |

## Why units left

**excluded_by_confirmed_facts.csv**

- income-restricted unit: 38
- listing gone at live check: 17
- dogs not allowed (confirmed): 14
- stale listing: the listing page was last changed on 2026-04-13, 216 days before it was read (2026-11-15): more than six months unchanged: 7
- elevator not established: the sources conflict on which buildings have one: 6
- ground-floor unit: 5
- stale listing: the listing page was last changed on 2026-05-06, 193 days before it was read (2026-11-15): more than six months unchanged: 4
- no elevator (contradicted in the evidence pass): 3

**excluded_sketchy.csv**

- elevator not stated on any page and the building's height is not known (it was guessed from the unit label): 135
- listing 60+ days old: 24
- two or more things unconfirmed: elevator: 17
- conflicting dog policy: 12
- listing: 11
- dogs allowed: 9
- availability: 7
- two or more things unconfirmed: dogs allowed: 5

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               6 |       92 |      63 |             0 |
| The Little-City Year      |              29 |      319 |     216 |             5 |
| The Old-Neighborhood Year |              40 |      133 |      86 |            27 |
| The Quiet-Street Year     |               7 |       10 |      10 |             0 |
| The Room-to-Breathe Year  |              31 |      206 |     125 |             0 |
| The Walk-Everywhere Year  |               5 |        7 |       5 |             2 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 89 |
| unit_floor | 59 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 20 |
| parking_type | 85 |
| parking_fee | 26 |
| pet_rent | 60 |
| pool | 46 |
| doorman | 37 |
| year_built | 47 |
| toll_rt_ezpass | 100 |
| transit_sat_median | 93 |
| near_violent_250m_24m | 12 |
| live_status | 63 |
| rent_first_full_payment_date | 58 |
| ev_pause_notes | 26 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every defect in docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (rules): 267 checks, 0 failed
```

**building amenities (cached pages)**
```
passing buildings: 693; already in csv: 751; to process: 0
```

**master tables**
```
  unit floor basis {'unknown': 1296, 'inferred': 1072, 'stated': 191, 'confirmed': 73} | label kind of inferred {'simple': 1058, 'complex': 14}
  confirmed floor values: 82 read, 9 matched no unit in the master (most are units that left the list), 3 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1855, 'live': 657, 'blocked': 73, 'changed': 30, 'gone': 17} | coordinates {'listing rows agree': 662, 'census_geocoder': 3}
  phone answers: 0 listing rows in 0 buildings (data/evidence/call_answers.csv is absent or empty)
  page modification date known: 529 | stale: {'no': 2434, 'open': 165, 'remove': 33} | elevator on a listing site's page alone: 377 buildings | overnight parking rule: {'none': 522, 'permit': 98, 'ban': 28, 'seasonal': 17}
  evidence facts not mapped to a field: {'building_size': 136, 'listing_broker': 61, 'building_site': 59, 'deposit': 28, 'application_fee': 25, 'owner_of_record': 24, 'listing_date': 21, 'building': 16, 'openigloo_summary': 16, 'move_in_fees': 16, 'available_units_listed': 16, 'building_name': 14, 'pet_count_limit': 14, 'dog': 12, 'listing_agent': 11, 'broker_fee': 10, 'deposit_and_fees': 10, 'one_time_fees': 10, 'openigloo_summary_counts': 10, 'building_size_openigloo': 9, 'listing_type': 9, 'own_site': 7, 'landlord': 6, 'amenities': 6, 'ownership_change': 6}
```

**rent terms**
```
2659 rows -> data/rent_terms.csv
offer_type: {'months_free': 1393, 'none': 891, 'other': 218, 'reduced_deposit_or_fee': 72, 'dollar_credit': 30, 'weeks_free': 35, 'look_and_lease': 20}
listed_price_is: {'net_effective': 152, 'gross': 1032, 'unknown': 1475}
needs_call: {'yes': 1660, 'no': 999}
```

**all-in cost**
```
  unknown building fees: 1429
  unknown pet rent: 0
  unknown parking fee: 1649
  unknown gas: 485
  pet rent estimated: 994 | within the cap but likely over once parking and fees are known: 285
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
evidence: 46 units excluded, shown 505, avoid cards 34, of them with an asterisk 312 ({'live check': 196, 'elevator': 44, 'listing': 37, 'availability': 16, 'dogs allowed': 14, 'eligibility': 5}), held for a confirmation 35, waiting for a live check 35
stages: 2632 costed -> -1019 over the all-in cap -> -361 Jamaica safety rule -> -114 failed a gate on confirmed facts -> -115 removed by a reviewed verdict -> -1 sibling floor rule -> -209 sketchy -> -46 evidence exclusions -> 767 ranked
shown buildings 231; disclosures: {'floor not published': 456, 'special offer': 257, 'could pass $3,000': 101, 'lease term': 98, 'dog weight limit not published': 28, 'overnight street parking': 19, 'net-effective rent': 18, 'condo rented by its owner': 9}
(kept 767 units; candidates 362; shown 395; pools: {'': 405, 'pool': 362}
```

**rule tests on the output (docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (data): 302 checks, 1 failed
  FAIL verdicts: a shown unit has no ok / asterisk / disclose verdict
```

**field registry, wiring check, shown-list assertions and the review rule**
```
   apartmentlist:p27690738-bay-s01-BAY-0708 (Bay One BAY-0708): no reviewed verdict: nobody has read this unit's evidence
   apartmentlist:p1932824-19e-a03-431 (19 East 431): no reviewed verdict: nobody has read this unit's evidence
   apartmentlist:p27690738-bay-a16-BAY-0803 (Bay One BAY-0803): no reviewed verdict: nobody has read this unit's evidence
   trulia:b2746633852:Unit_322:466166988 (Ethos Kelsey 322): no reviewed verdict: nobody has read this unit's evidence
   trulia:b2746633852:Unit_504:465853553 (Ethos Kelsey 504): no reviewed verdict: nobody has read this unit's evidence
   trulia:b2746633852:Unit_511:465853566 (Ethos Kelsey 511): no reviewed verdict: nobody has read this unit's evidence
```

