# Run report (2026-11-16T00:35:16+00:00)

## Steps

| Step | Script | Result |
|---|---|---|
| parser tests (every example in docs/INDEPENDENT_CHECK.md) | `test_parsers.py` | ok |
| rule tests (every defect in docs/INDEPENDENT_CHECK_2.md) | `test_rules.py` | ok |
| gates (merge, dedupe, gate each listing) | `gates.py` | ok |
| NYC building class (PLUTO) | `enrich_nyc_pluto.py` | ok |
| gates again with PLUTO | `gates.py` | ok |
| lookup tools per building | `enrich_units.py` | ok |
| neighborhood assignment | `build_neighborhoods.py` | ok |
| lifestyle features | `lifestyle_features.py` | ok |
| lifestyle colour | `lifestyle_color.py` | ok |
| crime benchmarks | `crime_benchmarks.py` | ok |
| lifestyle groups (saved centres) | `lifestyle_groups.py` | ok |
| building amenities (cached pages) | `building_amenities.py --no-fetch` | ok |
| master tables | `build_master.py` | ok |
| rent terms | `rent_terms.py` | ok |
| all-in cost | `all_in.py` | ok |
| evidence rules (avoid, exclusions) | `avoid.py` | ok |
| ranking and selection | `rank.py` | ok |
| rule tests on the output (docs/INDEPENDENT_CHECK_2.md) | `test_rules.py --data` | FAILED |
| field registry, wiring check, shown-list assertions and the review rule | `check_registry.py` | ok |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20464 | 20464 | +0 |
| pass every listing gate | 2598 | 2598 | +0 |
|   pending: a gate fact is unstated | 13595 | 13595 | +0 |
|   fail a gate | 4271 | 4271 | +0 |
| costed in the master table | 2573 | 2573 | +0 |
| within the $3,000 all-in cap | 1652 | 1652 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 855 | 855 | +0 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 326 | 326 | +0 |
| avoid cards | 36 | 35 | +1 |
|   shown with an asterisk (one thing to confirm) | 118 | 118 | +0 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 141 | 141 | +0 |
| held back for one confirmation | 29 | 26 | +3 |
| clean, waiting for a live check (not shown) | 39 | 28 | +11 |
| neighborhoods with 3+ shown places | 37 | 36 | +1 |
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

- elevator not stated on any page and the building's height is not known (it was guessed from the unit label): 112
- listing 60+ days old: 26
- conflicting dog policy: 13
- two or more things unconfirmed: elevator: 7
- dogs allowed: 7
- no unit or building named: 5
- two or more things unconfirmed: dogs allowed: 4
- live check judged the listing doubtful: 4

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               7 |       97 |      35 |             0 |
| The Little-City Year      |              31 |      365 |     124 |             5 |
| The Old-Neighborhood Year |              43 |      164 |      75 |            29 |
| The Quiet-Street Year     |               7 |       12 |      10 |             0 |
| The Room-to-Breathe Year  |              32 |      209 |      76 |             0 |
| The Walk-Everywhere Year  |               6 |        8 |       6 |             2 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 84 |
| unit_floor | 60 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 19 |
| parking_type | 80 |
| parking_fee | 27 |
| pet_rent | 50 |
| pool | 38 |
| doorman | 31 |
| year_built | 53 |
| toll_rt_ezpass | 100 |
| transit_sat_median | 91 |
| near_violent_250m_24m | 21 |
| live_status | 90 |
| rent_first_full_payment_date | 65 |
| ev_pause_notes | 30 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every defect in docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (rules): 105 checks, 0 failed
```

**gates (merge, dedupe, gate each listing)**
```
| movein | 7842 | 932 | 11690 |
| dog | 10245 | 1171 | 9048 |
| elevator | 5780 | 1317 | 13367 |
| floor | 5092 | 1076 | 14296 |
| place | 20434 | 0 | 30 |
| proof | 10376 | 7 | 10081 |
```

**NYC building class (PLUTO)**
```
3033 NYC buildings; {'house_number+location': 1486, 'nearest_lot': 837, 'no_lot_within_40m': 710}
{'no': 1154, 'yes': 947, nan: 710, 'unknown': 222}
```

**gates again with PLUTO**
```
| movein | 7842 | 932 | 11690 |
| dog | 10245 | 1171 | 9048 |
| elevator | 5780 | 1317 | 13367 |
| floor | 5092 | 1076 | 14296 |
| place | 20434 | 0 | 30 |
| proof | 10376 | 7 | 10081 |
```

**lookup tools per building**
```
600 692
625 692
650 692
675 692
{'pass': 2598} buildings: 692
coordinates: {'listing rows agree': 662, 'census_geocoder': 3}; lookups redone at a corrected coordinate: 0 address keys
```

**neighborhood assignment**
```
# Checkpoint A: neighborhoods and proposed years
Passing units: 2598 in 692 buildings, across 221 neighborhoods; 114 neighborhoods have 3+ passing places.
Cluster quality (silhouette; higher is cleaner): {5: 0.141, 6: 0.144}. Using k=6.
```

**lifestyle features**
```
221 neighborhoods; {'people_per_km2': 0.0, 'age_25_34_share': 0.0, 'median_age': 0.0, 'living_alone_share': 0.0, 'renter_share': 0.0, 'big_building_share': 0.0, 'detached_house_share': 0.0, 'median_year_built': 0.0, 'no_car_share': 0.0, 'transit_commute_share': 0.0, 'walk_commute_share': 0.0, 'wfh_share': 0.0, 'median_hh_income': 0.0, 'newcomer_share': 0.0, 'restaurants_800m': 0.0, 'bars_800m': 0.0, 'cafes_800m': 0.0, 'music_1600m': 0.0, 'park_ha_800m': 0.0, 'park_walk_min': 0.0, 'open_water_m': 0.0, 'beach_m': 0.0, 'supermarket_m': 0.0, 'train_station_m': 0.07, 'motorway_m': 0.0, 'violent_per_1000': 0.02, 'vehicle_theft_per_1000': 0.02, 'sqft': 0.2, 'bfloors': 0.94, 'garage': 0.0, 'sqft_per_1000usd': 0.2}
```

**lifestyle colour**
```
221 {'college_degree_share': 0.0, 'households_with_kids_share': 0.0, 'age_65plus_share': 0.0, 'commute_60min_plus_share': 0.0, 'built_since_2010_share': 0.0, 'built_before_1940_share': 0.0, 'tract_median_rent': 0.01, 'rent_burden_pct': 0.0, 'supermarket_m': 0.0, 'trader_joes_m': 0.19, 'whole_foods_m': 0.24, 'target_m': 0.04, 'vet_m': 0.0, 'dog_park_m': 0.0, 'train_station_m': 0.07, 'breweries_1600m': 0.0, 'restaurants_1600m': 0.0, 'transit_to_parents_min': 0.11, 'pool': 0.0, 'garage_or_gated': 0.0, 'street_parking': 0.0, 'building_floors': 0.59, 'building_year': 0.65, 'unit_sqft': 0.2, 'all_in': 0.0}
```

**crime benchmarks**
```
std       3.02           0.91              0.88              0.95                       0.63
min       0.00           0.00              0.00              0.00                       0.00
25%       0.81           0.25              0.24              0.43                       0.24
50%       2.09           0.63              0.60              0.76                       0.53
75%       4.13           1.25              1.20              1.51                       0.88
max      17.21           5.22              5.02              7.26                       4.56
```

**lifestyle groups (saved centres)**
```
enclave :: Harrison[23]; Wilton[8]; Teaneck[7]; Westport[5]; Berkeley Heights[4]; Montgomery[4]; Millburn[3]; Chatham[3]; Watchung[2]; Fairfield[2]
middle :: Stamford[166]; Parsippany-Troy Hills[114]; Jersey City – Journal Square[112]; New Rochelle[93]; Yonkers[76]; White Plains[66]; Port Chester[59]; Jersey City – West Side[45]; Hackensack[43]; Danbury[24]
new_water :: Jersey City – Bergen-Lafayette[136]; Norwalk[97]; Harrison[42]; New Brunswick[21]; North Bergen[12]; Jersey City – Downtown[9]; Fort Lee[9]; Weehawken[6]; Jersey City – Newport[4]; Edgewater[2]
pre_car :: New Haven[330]; Kew Gardens[6]; Astoria (Central)[2]; Bedford-Stuyvesant (West)[2]; Bay Ridge[2]; Sunnyside[2]; Upper West Side-Manhattan Valley[2]; Astoria (East)-Woodside (North)[1]; Hoboken[1]; East Midtown-Turtle Bay[1]
settled :: Newark[54]; Jersey City – McGinley Square[26]; Flushing-Willets Point[19]; Jamaica Hills-Briarwood[12]; Jamaica[11]; Hempstead[11]; East Flatbush-Erasmus[9]; Mott Haven-Port Morris[9]; Jackson Heights[8]; West New York[8]
space :: Bridgeport[108]; Bayonne[54]; Dover[41]; Clifton[22]; Burlington[21]; Trumbull[19]; East Brunswick[19]; Flemington[18]; East Orange[17]; Haverstraw[16]
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
units 2573; cost gate {'pass': 1652, 'fail': 921}; rent asterisk 1763; rent terms file present
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
evidence: 46 units excluded, shown 326, avoid cards 36, of them with an asterisk 118 ({'live check': 42, 'listing': 27, 'dogs allowed': 17, 'elevator': 16, 'availability': 14, 'eligibility': 2}), held for a confirmation 29, waiting for a live check 39
stages: 2573 costed -> -921 over the all-in cap -> -363 Jamaica safety rule -> -73 failed a gate on confirmed facts -> -141 removed by a reviewed verdict -> -174 sketchy -> -46 evidence exclusions -> 855 ranked
(kept 855 units; candidates 391; shown 428; pools: {'': 453, 'pool': 381, 'indoor': 21}
```

**rule tests on the output (docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (data): 150 checks, 1 failed
  FAIL split: Newark is not split
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 470, 'display': 309, 'provenance': 178, 'not_used': 18}
shown-list assertions: all pass
```

