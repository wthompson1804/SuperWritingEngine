# Run report (2026-11-16T02:17:06+00:00)

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
| rule tests on the output (docs/INDEPENDENT_CHECK_2.md) | `test_rules.py --data` | ok |
| field registry, wiring check, shown-list assertions and the review rule | `check_registry.py` | ok |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20464 | 20464 | +0 |
| pass every listing gate | 2503 | 2503 | +0 |
|   pending: a gate fact is unstated | 13680 | 13680 | +0 |
|   fail a gate | 4281 | 4281 | +0 |
| costed in the master table | 2462 | 2462 | +0 |
| within the $3,000 all-in cap | 1488 | 1488 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 769 | 769 | +0 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 491 | 491 | +0 |
| avoid cards | 35 | 35 | +0 |
|   shown with an asterisk (one thing to confirm) | 295 | 295 | +0 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 122 | 122 | +0 |
| held back for one confirmation | 33 | 33 | +0 |
| clean, waiting for a live check (not shown) | 37 | 37 | +0 |
| neighborhoods with 3+ shown places | 42 | 42 | +0 |
| buildings in the master table | 579 | 579 | +0 |

## Why units left

**excluded_by_confirmed_facts.csv**

- income-restricted unit: 38
- listing gone at live check: 16
- dogs not allowed (confirmed): 14
- stale listing: the listing page was last changed on 2026-04-13, 216 days before it was read (2026-11-15): more than six months unchanged: 7
- ground-floor unit: 5
- elevator not established: the sources conflict on which buildings have one: 4
- stale listing: the listing page was last changed on 2026-05-06, 193 days before it was read (2026-11-15): more than six months unchanged: 4
- stale listing: the listing page was last changed on 2026-01-27, 292 days before it was read (2026-11-15): more than six months unchanged: 2

**excluded_sketchy.csv**

- elevator not stated on any page and the building's height is not known (it was guessed from the unit label): 35
- listing 60+ days old: 23
- two or more things unconfirmed: elevator: 19
- conflicting dog policy: 12
- dogs allowed: 11
- listing: 9
- availability: 7
- no unit or building named: 5

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               6 |       94 |      65 |             0 |
| The Little-City Year      |              27 |      309 |     198 |             5 |
| The Old-Neighborhood Year |              40 |      135 |      85 |            26 |
| The Quiet-Street Year     |               7 |       10 |      10 |             0 |
| The Room-to-Breathe Year  |              34 |      212 |     128 |             0 |
| The Walk-Everywhere Year  |               6 |        9 |       5 |             4 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 90 |
| unit_floor | 60 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 20 |
| parking_type | 85 |
| parking_fee | 26 |
| pet_rent | 59 |
| pool | 44 |
| doorman | 36 |
| year_built | 46 |
| toll_rt_ezpass | 100 |
| transit_sat_median | 94 |
| near_violent_250m_24m | 13 |
| live_status | 66 |
| rent_first_full_payment_date | 57 |
| ev_pause_notes | 27 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every defect in docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (rules): 297 checks, 0 failed
```

**gates (merge, dedupe, gate each listing)**
```
| movein | 7842 | 932 | 11690 |
| dog | 10298 | 1171 | 8995 |
| elevator | 5291 | 1334 | 13839 |
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
| dog | 10298 | 1171 | 8995 |
| elevator | 5291 | 1334 | 13839 |
| floor | 5092 | 1076 | 14296 |
| place | 20434 | 0 | 30 |
| proof | 10376 | 7 | 10081 |
```

**lookup tools per building**
```
525 607
550 607
575 607
600 607
{'pass': 2503} buildings: 607
coordinates: {'listing rows agree': 574, 'census_geocoder': 4, 'listing majority, unverified': 1}; lookups redone at a corrected coordinate: 0 address keys
```

**neighborhood assignment**
```
# Checkpoint A: neighborhoods and proposed years
Passing units: 2503 in 607 buildings, across 196 neighborhoods; 101 neighborhoods have 3+ passing places.
Cluster quality (silhouette; higher is cleaner): {5: 0.125, 6: 0.128}. Using k=6.
```

**lifestyle features**
```
196 neighborhoods; {'people_per_km2': 0.0, 'age_25_34_share': 0.0, 'median_age': 0.0, 'living_alone_share': 0.0, 'renter_share': 0.0, 'big_building_share': 0.0, 'detached_house_share': 0.0, 'median_year_built': 0.01, 'no_car_share': 0.0, 'transit_commute_share': 0.0, 'walk_commute_share': 0.0, 'wfh_share': 0.0, 'median_hh_income': 0.01, 'newcomer_share': 0.0, 'restaurants_800m': 0.0, 'bars_800m': 0.0, 'cafes_800m': 0.0, 'music_1600m': 0.0, 'park_ha_800m': 0.0, 'park_walk_min': 0.0, 'open_water_m': 0.0, 'beach_m': 0.0, 'supermarket_m': 0.0, 'train_station_m': 0.08, 'motorway_m': 0.0, 'violent_per_1000': 0.02, 'vehicle_theft_per_1000': 0.02, 'sqft': 0.2, 'bfloors': 0.93, 'garage': 0.0, 'sqft_per_1000usd': 0.2}
```

**lifestyle colour**
```
196 {'college_degree_share': 0.0, 'households_with_kids_share': 0.0, 'age_65plus_share': 0.0, 'commute_60min_plus_share': 0.0, 'built_since_2010_share': 0.0, 'built_before_1940_share': 0.0, 'tract_median_rent': 0.02, 'rent_burden_pct': 0.01, 'supermarket_m': 0.0, 'trader_joes_m': 0.19, 'whole_foods_m': 0.26, 'target_m': 0.04, 'vet_m': 0.0, 'dog_park_m': 0.0, 'train_station_m': 0.08, 'breweries_1600m': 0.0, 'restaurants_1600m': 0.0, 'transit_to_parents_min': 0.1, 'pool': 0.0, 'garage_or_gated': 0.0, 'street_parking': 0.0, 'building_floors': 0.56, 'building_year': 0.62, 'unit_sqft': 0.2, 'all_in': 0.0}
```

**crime benchmarks**
```
std       3.15           0.95              0.92              0.98                       0.59
min       0.00           0.00              0.00              0.00                       0.00
25%       0.93           0.26              0.27              0.45                       0.27
50%       2.34           0.71              0.68              0.86                       0.56
75%       4.77           1.45              1.39              1.56                       0.92
max      17.21           5.22              5.02              7.26                       3.44
```

**lifestyle groups (saved centres)**
```
enclave :: Berkeley Heights[60]; Harrison[23]; Teaneck[8]; Westport[5]; Montgomery[4]; Fairfield[2]; Watchung[2]; Roxbury[2]; Atlantic Highlands[1]; Montvale[1]
middle :: Stamford[160]; Parsippany-Troy Hills[114]; Jersey City – Journal Square[112]; New Rochelle[85]; Yonkers[69]; Port Chester[59]; White Plains[58]; Jersey City – West Side[50]; Hackensack[41]; Danbury[23]
new_water :: Jersey City – Bergen-Lafayette[135]; Norwalk[96]; Harrison[45]; New Brunswick[23]; North Bergen[12]; Jersey City – Downtown[7]; Weehawken[6]; West New York[4]; Jersey City – Newport[4]; Edgewater[2]
pre_car :: New Haven[303]; Jersey City – McGinley Square[25]; Kew Gardens[6]; Bedford-Stuyvesant (West)[2]; Bay Ridge[2]; Sunnyside[2]; Upper West Side-Manhattan Valley[2]; Brooklyn Heights[1]; Astoria (East)-Woodside (North)[1]; East Midtown-Turtle Bay[1]
settled :: Newark[46]; Flushing-Willets Point[19]; Hempstead[11]; Jamaica[11]; Jamaica Hills-Briarwood[11]; East Flatbush-Erasmus[9]; Mott Haven-Port Morris[9]; Harlem (North)[7]; Washington Heights (North)[6]; East Harlem (North)[5]
space :: Bridgeport[108]; Bayonne[51]; Dover[41]; Bogota[31]; Clifton[22]; Burlington[21]; Trumbull[19]; East Brunswick[18]; Flemington[18]; Haverstraw[16]
```

**building amenities (cached pages)**
```
passing buildings: 607; already in csv: 754; to process: 0
```

**master tables**
```
  unit floor basis {'unknown': 1259, 'inferred': 940, 'stated': 195, 'confirmed': 68} | label kind of inferred {'simple': 925, 'complex': 15}
  confirmed floor values: 76 read, 9 matched no unit in the master (most are units that left the list), 3 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1761, 'live': 593, 'blocked': 63, 'changed': 29, 'gone': 16} | coordinates {'listing rows agree': 574, 'census_geocoder': 4, 'listing majority, unverified': 1}
  phone answers: 0 listing rows in 0 buildings (data/evidence/call_answers.csv is absent or empty)
  page modification date known: 494 | stale: {'no': 2266, 'open': 163, 'remove': 33} | elevator on a listing site's page alone: 384 buildings | overnight parking rule: {'none': 457, 'permit': 80, 'ban': 26, 'seasonal': 16}
  evidence facts not mapped to a field: {'building_size': 120, 'listing_broker': 60, 'building_site': 54, 'deposit': 26, 'application_fee': 23, 'listing_date': 21, 'owner_of_record': 21, 'building': 15, 'move_in_fees': 15, 'openigloo_summary': 14, 'building_name': 13, 'available_units_listed': 13, 'pet_count_limit': 12, 'openigloo_summary_counts': 10, 'dog': 8, 'broker_fee': 7, 'building_size_openigloo': 7, 'own_site': 7, 'listing_type': 7, 'landlord': 6, 'ownership_change': 6, 'amenities': 5, 'one_time_fee': 5, 'former_or_other_name': 5, 'other_fees': 4}
```

**rent terms**
```
2503 rows -> data/rent_terms.csv
offer_type: {'months_free': 1328, 'none': 816, 'other': 211, 'reduced_deposit_or_fee': 69, 'dollar_credit': 29, 'weeks_free': 35, 'look_and_lease': 15}
listed_price_is: {'net_effective': 152, 'gross': 948, 'unknown': 1403}
needs_call: {'yes': 1586, 'no': 917}
```

**all-in cost**
```
  unknown building fees: 1322
  unknown pet rent: 0
  unknown parking fee: 1521
  unknown gas: 457
  pet rent estimated: 924 | within the cap but likely over once parking and fees are known: 280
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
evidence: 47 units excluded, shown 491, avoid cards 35, of them with an asterisk 295 ({'live check': 178, 'elevator': 41, 'listing': 37, 'availability': 18, 'dogs allowed': 16, 'eligibility': 5}), held for a confirmation 33, waiting for a live check 37
stages: 2462 costed -> -974 over the all-in cap -> -332 Jamaica safety rule -> -108 failed a gate on confirmed facts -> -122 removed by a reviewed verdict -> -1 sibling floor rule -> -109 sketchy -> -47 evidence exclusions -> 769 ranked
shown buildings 233; disclosures: {'floor not published': 442, 'special offer': 253, 'could pass $3,000': 104, 'lease term': 98, 'dog weight limit not published': 22, 'overnight street parking': 19, 'net-effective rent': 18, 'condo rented by its owner': 9}
(kept 769 units; candidates 369; shown 402; pools: {'': 413, 'pool': 356}
```

**rule tests on the output (docs/INDEPENDENT_CHECK_2.md)**
```
test_rules (data): 312 checks, 0 failed
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 500, 'display': 311, 'provenance': 191, 'not_used': 17}
shown-list assertions: all pass
```

