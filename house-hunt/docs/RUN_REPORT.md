# Run report (2026-11-15T22:46:27+00:00)

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
| listings harvested (after dedupe) | 20464 | 20464 | +0 |
| pass every listing gate | 2598 | 2598 | +0 |
|   pending: a gate fact is unstated | 13595 | 13595 | +0 |
|   fail a gate | 4271 | 4271 | +0 |
| costed in the master table | 2575 | 2020 | +555 |
| within the $3,000 all-in cap | 1664 | 1664 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 1185 | 1185 | +0 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 325 | 324 | +1 |
| avoid cards | 29 | 30 | -1 |
|   shown with an asterisk (one thing to confirm) | 212 | 211 | +1 |
| held back for one confirmation | 189 | 189 | +0 |
| clean, waiting for a live check (not shown) | 190 | 190 | +0 |
| neighborhoods with 3+ shown places | 36 | 36 | +0 |
| buildings in the master table | 665 | 608 | +57 |

## Why units left

**excluded_by_confirmed_facts.csv**

- dogs not allowed (confirmed): 14
- elevator not established: the sources conflict on which buildings have one: 6
- income-restricted unit: 3
- ground-floor unit: 2
- listing gone at live check: 2
- harvest note: BUILDING_FAILS: income-restricted lottery building with a waitlist (page says so), 0 units available: 1
- small dogs only. Trulia: 1
- harvest note: BUILDING_FAILS: age-restricted community (55+/senior) per the Trulia building page. Auto record from the Trulia building page: 1

**excluded_sketchy.csv**

- two or more unconfirmed gate facts: 33
- listing 60+ days old: 26
- conflicting dog policy: 13
- no unit or building named: 5
- live check judged the listing doubtful: 4
- thin syndicated feed: 3
- price far below the neighborhood: 1

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               7 |       68 |      25 |             0 |
| The Little-City Year      |              34 |      521 |     110 |             7 |
| The Old-Neighborhood Year |              50 |      183 |      93 |            20 |
| The Quiet-Street Year     |              14 |       26 |      15 |             0 |
| The Room-to-Breathe Year  |              52 |      373 |      74 |             0 |
| The Walk-Everywhere Year  |               9 |       14 |       8 |             2 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 78 |
| unit_floor | 74 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 18 |
| parking_type | 74 |
| parking_fee | 18 |
| pet_rent | 44 |
| pool | 28 |
| doorman | 27 |
| year_built | 58 |
| toll_rt_ezpass | 40 |
| transit_sat_median | 92 |
| near_violent_250m_24m | 28 |
| live_status | 77 |
| rent_first_full_payment_date | 73 |
| ev_pause_notes | 28 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
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
Passing units: 2598 in 692 buildings, across 214 neighborhoods; 109 neighborhoods have 3+ passing places.
Cluster quality (silhouette; higher is cleaner): {5: 0.152, 6: 0.157}. Using k=6.
```

**lifestyle features**
```
214 neighborhoods; {'people_per_km2': 0.0, 'age_25_34_share': 0.0, 'median_age': 0.0, 'living_alone_share': 0.0, 'renter_share': 0.0, 'big_building_share': 0.0, 'detached_house_share': 0.0, 'median_year_built': 0.0, 'no_car_share': 0.0, 'transit_commute_share': 0.0, 'walk_commute_share': 0.0, 'wfh_share': 0.0, 'median_hh_income': 0.0, 'newcomer_share': 0.0, 'restaurants_800m': 0.0, 'bars_800m': 0.0, 'cafes_800m': 0.0, 'music_1600m': 0.0, 'park_ha_800m': 0.0, 'park_walk_min': 0.0, 'open_water_m': 0.0, 'beach_m': 0.0, 'supermarket_m': 0.0, 'train_station_m': 0.07, 'motorway_m': 0.0, 'violent_per_1000': 0.02, 'vehicle_theft_per_1000': 0.02, 'sqft': 0.21, 'bfloors': 0.93, 'garage': 0.0, 'sqft_per_1000usd': 0.21}
```

**lifestyle colour**
```
214 {'college_degree_share': 0.0, 'households_with_kids_share': 0.0, 'age_65plus_share': 0.0, 'commute_60min_plus_share': 0.0, 'built_since_2010_share': 0.0, 'built_before_1940_share': 0.0, 'tract_median_rent': 0.01, 'rent_burden_pct': 0.0, 'supermarket_m': 0.0, 'trader_joes_m': 0.2, 'whole_foods_m': 0.25, 'target_m': 0.04, 'vet_m': 0.0, 'dog_park_m': 0.0, 'train_station_m': 0.07, 'breweries_1600m': 0.0, 'restaurants_1600m': 0.0, 'transit_to_parents_min': 0.12, 'pool': 0.0, 'garage_or_gated': 0.0, 'street_parking': 0.0, 'building_floors': 0.58, 'building_year': 0.64, 'unit_sqft': 0.21, 'all_in': 0.0}
```

**crime benchmarks**
```
std       3.05           0.92              0.89              0.97                       0.63
min       0.00           0.00              0.00              0.00                       0.00
25%       0.78           0.23              0.22              0.42                       0.23
50%       1.99           0.60              0.57              0.73                       0.50
75%       4.00           1.20              1.15              1.45                       0.85
max      17.21           5.22              5.02              7.26                       4.56
```

**lifestyle groups (saved centres)**
```
enclave :: Harrison[23]; Wilton[8]; Teaneck[7]; Westport[5]; Berkeley Heights[4]; Montgomery[4]; Millburn[3]; Chatham[3]; Watchung[2]; Fairfield[2]
middle :: Jersey City[335]; Stamford[166]; Parsippany-Troy Hills[114]; New Rochelle[93]; Yonkers[76]; White Plains[66]; Port Chester[59]; Hackensack[43]; Danbury[24]; Franklin[17]
new_water :: Norwalk[97]; Harrison[42]; New Brunswick[21]; North Bergen[12]; Fort Lee[9]; Weehawken[6]; Edgewater[2]; Long Island City-Hunters Point[1]
pre_car :: New Haven[330]; Kew Gardens[6]; Astoria (Central)[2]; Bedford-Stuyvesant (West)[2]; Bay Ridge[2]; Sunnyside[2]; Upper West Side-Manhattan Valley[2]; Astoria (East)-Woodside (North)[1]; Hoboken[1]; East Midtown-Turtle Bay[1]
settled :: Newark[54]; Flushing-Willets Point[19]; Jamaica Hills-Briarwood[12]; Jamaica[11]; Hempstead[11]; East Flatbush-Erasmus[9]; Mott Haven-Port Morris[9]; Jackson Heights[8]; West New York[8]; Mount Vernon[8]
space :: Bridgeport[108]; Bayonne[54]; Dover[41]; Clifton[22]; Burlington[21]; Trumbull[19]; East Brunswick[19]; Flemington[18]; East Orange[17]; Bogota[16]
```

**building amenities (cached pages)**
```
  year_built                    130   18.8%
  year_renovated                 16    2.3%
  total_floors                   32    4.6%
  unit_count                    185   26.7%
  management_company            105   15.2%
  fetched: 0
```

**master tables**
```
  manager                {'stated': 332, 'confirmed': 154, 'unknown': 139, 'amenities_page': 40}
  utilities_included     {'unknown': 566, 'confirmed': 53, 'community_page': 26, 'stated': 20}
  unit floor basis {'unknown': 1288, 'inferred': 1065, 'stated': 155, 'confirmed': 67} | label kind of inferred {'simple': 1058, 'complex': 7}
  confirmed floor values: 93 read, 26 matched no unit in the master (most are units that left the list), 2 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 2175, 'live': 384, 'changed': 9, 'blocked': 5, 'gone': 2} | coordinates {'listing rows agree': 662, 'census_geocoder': 3}
  evidence facts not mapped to a field: {'building_size': 81, 'building_site': 59, 'listing_last_modified': 37, 'owner_of_record': 24, 'listing_broker': 22, 'listing_date': 21, 'openigloo_summary': 16, 'available_units_listed': 16, 'pet_count_limit': 14, 'move_in_fees': 14, 'dog': 12, 'building_size_openigloo': 9, 'application_fee': 8, 'listing_updated_at': 8, 'deposit': 8, 'one_time_fee': 5, 'ownership_change': 5, 'building_name': 5, 'deposit_fee': 5, 'former_or_other_name': 5, 'open_violations_note': 5, 'ownership': 4, 'price_history': 4, 'storage': 4, 'own_site_price': 3}
```

**rent terms**
```
2598 rows -> data/rent_terms.csv
offer_type: {'months_free': 1384, 'none': 867, 'other': 196, 'reduced_deposit_or_fee': 68, 'dollar_credit': 28, 'weeks_free': 35, 'look_and_lease': 20}
listed_price_is: {'net_effective': 153, 'gross': 1090, 'unknown': 1355}
needs_call: {'yes': 1539, 'no': 1059}
```

**all-in cost**
```
units 2575; cost gate {'pass': 1664, 'fail': 911}; rent asterisk 1720; rent terms file present
  unknown building fees: 1569
  unknown pet rent: 1011
  unknown parking fee: 1664
  unknown gas: 489
  gross above cap while basis passes: 26
```

**evidence rules (avoid, exclusions)**
```
                                              13523 82nd ave|11435                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                               14202 84th dr|11435                                                                                                              management: city records in the last 6 months above the 90th percentile on class_c_violations, mold_complaints, pest_complaints
                                           14345 sanford ave|11355                                                                                                                                            elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                              14725 94th ave|11435                                                                     car crime: 46 vehicle thefts and thefts from vehicles within 250 m in 24 months (police data), at least double the median of 21 for candidate buildings in New York City
                                             148-33 90th ave|11435                                                                                                    management: city records in the last 6 months above the 90th percentile on class_c_violations, heat_hot_water_complaints, pest_complaints
                                             148-37 88th ave|11435                                                                                          
```

**ranking and selection**
```
evidence: 4 units excluded, shown 325, avoid cards 29, of them with an asterisk 212 ({'floor': 103, 'live check': 78, 'elevator': 29, 'dogs allowed': 2}), held for a confirmation 189, waiting for a live check 190
stages: 2575 costed -> -911 over the all-in cap -> -363 Jamaica safety rule -> -29 failed a gate on confirmed facts -> -83 sketchy -> -4 evidence exclusions -> 1185 ranked
(kept 1185 units; candidates 533; shown 491; pools: {'': 820, 'pool': 341, 'indoor': 24}
```

**field registry, wiring check and shown-list assertions**
```
field registry: {'used': 445, 'display': 304, 'provenance': 155, 'not_used': 18}
shown-list assertions: all pass
```

