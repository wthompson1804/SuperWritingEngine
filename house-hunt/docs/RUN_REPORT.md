# Run report (2026-11-16T01:00:29+00:00)

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
| pass every listing gate | 2659 | 2659 | +0 |
|   pending: a gate fact is unstated | 13534 | 13534 | +0 |
|   fail a gate | 4271 | 4271 | +0 |
| costed in the master table | 2634 | 2634 | +0 |
| within the $3,000 all-in cap | 1653 | 1653 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 821 | 821 | +0 |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 347 | 347 | +0 |
| avoid cards | 36 | 36 | +0 |
|   shown with an asterisk (one thing to confirm) | 133 | 133 | +0 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 125 | 125 | +0 |
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

**gates (merge, dedupe, gate each listing)**
```
| movein | 7842 | 932 | 11690 |
| dog | 10298 | 1171 | 8995 |
| elevator | 5811 | 1317 | 13336 |
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
| elevator | 5811 | 1317 | 13336 |
| floor | 5092 | 1076 | 14296 |
| place | 20434 | 0 | 30 |
| proof | 10376 | 7 | 10081 |
```

**lookup tools per building**
```
600 693
625 693
650 693
675 693
{'pass': 2659} buildings: 693
coordinates: {'listing rows agree': 662, 'census_geocoder': 3}; lookups redone at a corrected coordinate: 0 address keys
```

**neighborhood assignment**
```
# Checkpoint A: neighborhoods and proposed years
Passing units: 2659 in 693 buildings, across 221 neighborhoods; 114 neighborhoods have 3+ passing places.
Cluster quality (silhouette; higher is cleaner): {5: 0.141, 6: 0.145}. Using k=6.
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
enclave :: Berkeley Heights[63]; Harrison[23]; Wilton[8]; Teaneck[7]; Westport[5]; Montgomery[4]; Millburn[3]; Chatham[3]; Watchung[2]; Fairfield[2]
middle :: Stamford[166]; Parsippany-Troy Hills[114]; Jersey City – Journal Square[112]; New Rochelle[93]; Yonkers[76]; White Plains[66]; Port Chester[59]; Jersey City – West Side[45]; Hackensack[43]; Danbury[24]
new_water :: Jersey City – Bergen-Lafayette[136]; Norwalk[97]; Harrison[44]; New Brunswick[21]; North Bergen[12]; Jersey City – Downtown[9]; Fort Lee[9]; Weehawken[6]; Jersey City – Newport[4]; Edgewater[2]
pre_car :: New Haven[330]; Kew Gardens[6]; Astoria (Central)[2]; Bedford-Stuyvesant (West)[2]; Bay Ridge[2]; Sunnyside[2]; Upper West Side-Manhattan Valley[2]; Astoria (East)-Woodside (North)[1]; Hoboken[1]; East Midtown-Turtle Bay[1]
settled :: Newark[54]; Jersey City – McGinley Square[26]; Flushing-Willets Point[19]; Jamaica Hills-Briarwood[12]; Jamaica[11]; Hempstead[11]; East Flatbush-Erasmus[9]; Mott Haven-Port Morris[9]; Jackson Heights[8]; West New York[8]
space :: Bridgeport[108]; Bayonne[54]; Dover[41]; Clifton[22]; Burlington[21]; Trumbull[19]; East Brunswick[19]; Flemington[18]; East Orange[17]; Haverstraw[16]
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

