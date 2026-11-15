# Run report (2026-11-15T22:36:50+00:00)

## Steps

| Step | Script | Result |
|---|---|---|
| parser tests (every example in docs/INDEPENDENT_CHECK.md) | `test_parsers.py` | ok |
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
| field registry, wiring check and shown-list assertions | `check_registry.py` | ok |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20464 | 18290 | +2174 |
| pass every listing gate | 2598 | 2027 | +571 |
|   pending: a gate fact is unstated | 13595 | 12069 | +1526 |
|   fail a gate | 4271 | 4194 | +77 |
| costed in the master table | 2020 | 1524 | +496 |
| within the $3,000 all-in cap | 1664 | 1313 | +351 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 1039 | 961 | +78 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 68 | 207 | -139 |
| avoid cards | 24 | 27 | -3 |
| held back for one confirmation | 307 | 200 | +107 |
| clean, waiting for a live check (not shown) | 52 |  |  |
| neighborhoods with 3+ shown places | 8 | 26 | -18 |
| buildings in the master table | 608 | 551 | +57 |

## Why units left

**excluded_by_confirmed_facts.csv**

- dogs not allowed (confirmed): 14
- elevator not established: the sources conflict on which buildings have one: 6
- income-restricted unit: 3
- ground-floor unit: 2
- listing gone at live check: 2
- harvest note: BUILDING_FAILS: income-restricted lottery building with a waitlist (page says so), 0 units available: 1
- small do: 1
- harvest note: BUILDING_FAILS: age-restricted community (55+/senior) per the Trulia building page. Auto record from the Truli: 1

**excluded_sketchy.csv**

- two or more unconfirmed gate facts: 179
- listing 60+ days old: 26
- conflicting dog policy: 13
- no unit or building named: 5
- live check judged the listing doubtful: 4
- thin syndicated feed: 3
- price far below the neighborhood: 1

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               5 |       62 |       4 |             0 |
| The Little-City Year      |              32 |      491 |      32 |             7 |
| The Old-Neighborhood Year |              40 |      130 |      10 |            15 |
| The Quiet-Street Year     |              13 |       25 |       2 |             0 |
| The Room-to-Breathe Year  |              47 |      322 |      18 |             0 |
| The Walk-Everywhere Year  |               7 |        9 |       2 |             2 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 97 |
| unit_floor | 100 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 24 |
| parking_type | 88 |
| parking_fee | 26 |
| pet_rent | 60 |
| pool | 37 |
| doorman | 43 |
| year_built | 56 |
| toll_rt_ezpass | 34 |
| transit_sat_median | 100 |
| near_violent_250m_24m | 9 |
| live_status | 100 |
| rent_first_full_payment_date | 51 |
| ev_pause_notes | 32 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 243 assertions passed
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
{'pass': 2042, 'fail_all_in': 556} buildings: 633
coordinates: {'listing rows agree': 662, 'census_geocoder': 3}; lookups redone at a corrected coordinate: 0 address keys
```

**neighborhood assignment**
```
# Checkpoint A: neighborhoods and proposed years
Passing units: 2042 in 633 buildings, across 201 neighborhoods; 101 neighborhoods have 3+ passing places.
Cluster quality (silhouette; higher is cleaner): {5: 0.178, 6: 0.18}. Using k=6.
```

**lifestyle features**
```
201 neighborhoods; {'people_per_km2': 0.0, 'age_25_34_share': 0.0, 'median_age': 0.0, 'living_alone_share': 0.0, 'renter_share': 0.0, 'big_building_share': 0.0, 'detached_house_share': 0.0, 'median_year_built': 0.0, 'no_car_share': 0.0, 'transit_commute_share': 0.0, 'walk_commute_share': 0.0, 'wfh_share': 0.0, 'median_hh_income': 0.0, 'newcomer_share': 0.0, 'restaurants_800m': 0.0, 'bars_800m': 0.0, 'cafes_800m': 0.0, 'music_1600m': 0.0, 'park_ha_800m': 0.0, 'park_walk_min': 0.0, 'open_water_m': 0.0, 'beach_m': 0.0, 'supermarket_m': 0.0, 'train_station_m': 0.07, 'motorway_m': 0.0, 'violent_per_1000': 0.02, 'vehicle_theft_per_1000': 0.02, 'sqft': 0.22, 'bfloors': 0.94, 'garage': 0.0, 'sqft_per_1000usd': 0.22}
```

**lifestyle colour**
```
201 {'college_degree_share': 0.0, 'households_with_kids_share': 0.0, 'age_65plus_share': 0.0, 'commute_60min_plus_share': 0.0, 'built_since_2010_share': 0.0, 'built_before_1940_share': 0.0, 'tract_median_rent': 0.01, 'rent_burden_pct': 0.01, 'supermarket_m': 0.0, 'trader_joes_m': 0.19, 'whole_foods_m': 0.25, 'target_m': 0.04, 'vet_m': 0.0, 'dog_park_m': 0.0, 'train_station_m': 0.07, 'breweries_1600m': 0.0, 'restaurants_1600m': 0.0, 'transit_to_parents_min': 0.12, 'pool': 0.0, 'garage_or_gated': 0.0, 'street_parking': 0.0, 'building_floors': 0.58, 'building_year': 0.64, 'unit_sqft': 0.22, 'all_in': 0.0}
```

**crime benchmarks**
```
std       3.11           0.94              0.90              0.98                       0.64
min       0.00           0.00              0.00              0.00                       0.00
25%       0.78           0.23              0.22              0.43                       0.26
50%       2.09           0.63              0.60              0.72                       0.54
75%       4.07           1.23              1.19              1.46                       0.86
max      17.21           5.22              5.02              7.26                       4.56
```

**lifestyle groups (saved centres)**
```
enclave :: Wilton[8]; Teaneck[7]; Westport[5]; Montgomery[4]; Chatham[3]; Berkeley Heights[3]; Millburn[3]; Fairfield[2]; Roxbury[2]; Summit[2]
middle :: Jersey City[223]; Stamford[118]; Parsippany-Troy Hills[93]; New Rochelle[60]; Yonkers[55]; Port Chester[41]; Hackensack[34]; White Plains[33]; Danbury[24]; Franklin[17]
new_water :: Norwalk[53]; Harrison[28]; New Brunswick[17]; Edgewater[2]; Weehawken[2]; Long Island City-Hunters Point[1]
pre_car :: New Haven[319]; Kew Gardens[6]; Bedford-Stuyvesant (West)[2]; Bay Ridge[2]; Sunnyside[2]; Astoria (Central)[2]; Upper West Side-Manhattan Valley[2]; Hoboken[1]; Astoria (East)-Woodside (North)[1]; Crown Heights (North)[1]
settled :: Newark[54]; Flushing-Willets Point[19]; Jamaica Hills-Briarwood[12]; Jamaica[11]; Mott Haven-Port Morris[9]; Hempstead[8]; Jackson Heights[8]; East Flatbush-Erasmus[7]; Mount Vernon[6]; West New York[5]
space :: Bridgeport[59]; Bayonne[52]; Dover[41]; Burlington[20]; Trumbull[19]; Flemington[18]; East Brunswick[17]; East Orange[16]; Bogota[15]; Shelton[14]
```

**building amenities (cached pages)**
```
passing buildings: 633; already in csv: 692; to process: 0
```

**master tables**
```
  manager                {'stated': 300, 'confirmed': 154, 'unknown': 126, 'amenities_page': 28}
  utilities_included     {'unknown': 514, 'confirmed': 53, 'community_page': 24, 'stated': 17}
  unit floor basis {'unknown': 965, 'inferred': 902, 'stated': 85, 'confirmed': 68} | label kind of inferred {'simple': 896, 'complex': 6}
  confirmed floor values: 93 read, 25 matched no unit in the master (most are units that left the list), 2 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1626, 'live': 379, 'changed': 8, 'blocked': 5, 'gone': 2} | coordinates {'listing rows agree': 605, 'census_geocoder': 3}
  evidence facts not mapped to a field: {'building_size': 81, 'building_site': 59, 'listing_last_modified': 37, 'owner_of_record': 24, 'listing_broker': 22, 'listing_date': 21, 'openigloo_summary': 16, 'available_units_listed': 16, 'move_in_fees': 14, 'pet_count_limit': 13, 'dog': 12, 'building_size_openigloo': 9, 'application_fee': 8, 'listing_updated_at': 8, 'deposit': 8, 'one_time_fee': 5, 'ownership_change': 5, 'building_name': 5, 'deposit_fee': 5, 'former_or_other_name': 5, 'open_violations_note': 5, 'ownership': 4, 'price_history': 4, 'storage': 4, 'own_site_price': 3}
```

**rent terms**
```
2042 rows -> data/rent_terms.csv
offer_type: {'months_free': 1050, 'none': 742, 'other': 127, 'reduced_deposit_or_fee': 51, 'dollar_credit': 27, 'weeks_free': 29, 'look_and_lease': 16}
listed_price_is: {'net_effective': 91, 'gross': 893, 'unknown': 1058}
needs_call: {'yes': 1175, 'no': 867}
```

**all-in cost**
```
units 2020; cost gate {'pass': 1664, 'fail': 356}; rent asterisk 1289; rent terms file present
  unknown building fees: 1326
  unknown pet rent: 869
  unknown parking fee: 1378
  unknown gas: 428
  gross above cap while basis passes: 26
```

**evidence rules (avoid, exclusions)**
```
                                              13523 82nd ave|11435                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                               14202 84th dr|11435                                                                                                              management: city records in the last 6 months above the 90th percentile on class_c_violations, mold_complaints, pest_complaints
                                           14345 sanford ave|11355                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                              14725 94th ave|11435                                                                     car crime: 46 vehicle thefts and thefts from vehicles within 250 m in 24 months (police data), at least double the median of 20 for candidate buildings in New York City
                                             148-33 90th ave|11435                                                                                                    management: city records in the last 6 months above the 90th percentile on class_c_violations, heat_hot_water_complaints, pest_complaints
                                             148-37 88th ave|11435                                                                                          
```

**ranking and selection**
```
evidence: 4 units excluded, shown 68, avoid cards 24, held for a confirmation 307, clean but waiting for a live check 52, shown without a live check 0
stages: 2020 costed -> -356 over the all-in cap -> -363 Jamaica safety rule -> -29 failed a gate on confirmed facts -> -229 sketchy -> -4 evidence exclusions -> 1039 ranked
(kept 1039 units; candidates 431; shown 401; pools: {'': 682, 'pool': 334, 'indoor': 23}
```

**field registry, wiring check and shown-list assertions**
```
field registry: {'used': 445, 'display': 304, 'provenance': 155, 'not_used': 18}
shown-list assertions: all pass
```

