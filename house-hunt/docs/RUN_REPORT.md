# Run report (2026-11-16T03:09:28+00:00)

## Steps

| Step | Script | Result |
|---|---|---|
| parser tests (every example in docs/INDEPENDENT_CHECK.md) | `test_parsers.py` | ok |
| rule tests (every repaired defect and rule, pure) | `test_rules.py` | ok |
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
| rule tests on the output | `test_rules.py --data` | ok |
| field registry, wiring check, shown-list assertions and the review rule | `check_registry.py` | ok |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20468 | 20468 | +0 |
| pass every listing gate | 2505 | 2505 | +0 |
|   pending: a gate fact is unstated | 14019 | 14019 | +0 |
|   fail a gate | 3944 | 3944 | +0 |
| costed in the master table | 2451 | 2451 | +0 |
| within the $3,000 all-in cap | 1480 | 1480 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 760 | 760 | +0 |
| shown (real apartments, at most one open item, up to 8 per building, after the thin-neighborhood rule) | 446 | 446 | +0 |
|   neighborhoods shown | 68 | 68 | +0 |
|   buildings shown | 191 | 191 | +0 |
| not an apartment: floor plan, building price or co-living room (data/excluded_not_an_apartment.csv) | 71 | 71 | +0 |
| thin neighborhoods cut (one apartment, not both well attested and promising) | 35 | 35 | +0 |
| avoid cards | 35 | 35 | +0 |
|   shown with an asterisk (one thing to confirm) | 265 | 265 | +0 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 107 | 107 | +0 |
| held back for one confirmation | 50 | 50 | +0 |
| clean, waiting for a live check (not shown) | 41 | 41 | +0 |
| neighborhoods with 3+ shown places | 41 | 41 | +0 |
| buildings in the master table | 578 | 578 | +0 |

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

- listing 60+ days old: 23
- two or more things unconfirmed: elevator: 13
- dogs allowed: 10
- elevator not stated on any page and the building's height is not known (it was guessed from the unit label): 8
- listing: 7
- no unit or building named: 5
- two or more things unconfirmed: dogs allowed: 4
- live check judged the listing doubtful: 3

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               6 |       92 |      62 |             0 |
| The Little-City Year      |              29 |      303 |     195 |             5 |
| The Old-Neighborhood Year |              39 |      132 |      73 |            26 |
| The Quiet-Street Year     |               7 |       10 |       6 |             0 |
| The Room-to-Breathe Year  |              32 |      203 |     108 |             0 |
| The Walk-Everywhere Year  |               6 |       20 |       2 |             4 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 92 |
| unit_floor | 62 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 20 |
| parking_type | 86 |
| parking_fee | 25 |
| pet_rent | 60 |
| pool | 45 |
| doorman | 39 |
| year_built | 45 |
| toll_rt_ezpass | 100 |
| transit_sat_median | 97 |
| near_violent_250m_24m | 11 |
| live_status | 63 |
| rent_first_full_payment_date | 56 |
| ev_pause_notes | 28 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every repaired defect and rule, pure)**
```
test_rules (rules): 421 checks, 0 failed
```

**gates (merge, dedupe, gate each listing)**
```
| movein | 7841 | 932 | 11695 |
| dog | 10298 | 1171 | 8999 |
| elevator | 5328 | 845 | 14295 |
| floor | 5461 | 1163 | 13844 |
| place | 20438 | 0 | 30 |
| proof | 10376 | 7 | 10085 |
```

**NYC building class (PLUTO)**
```
3033 NYC buildings; {'house_number+location': 1486, 'nearest_lot': 837, 'no_lot_within_40m': 710}
{'no': 1154, 'yes': 947, nan: 710, 'unknown': 222}
```

**gates again with PLUTO**
```
| movein | 7841 | 932 | 11695 |
| dog | 10298 | 1171 | 8999 |
| elevator | 5328 | 845 | 14295 |
| floor | 5461 | 1163 | 13844 |
| place | 20438 | 0 | 30 |
| proof | 10376 | 7 | 10085 |
```

**lookup tools per building**
```
525 608
550 608
575 608
600 608
{'pass': 2505} buildings: 608
coordinates: {'listing rows agree': 573, 'census_geocoder': 4, 'listing majority, unverified': 1}; lookups redone at a corrected coordinate: 0 address keys
```

**neighborhood assignment**
```
# Checkpoint A: neighborhoods and proposed years
Passing units: 2505 in 608 buildings, across 197 neighborhoods; 101 neighborhoods have 3+ passing places.
Cluster quality (silhouette; higher is cleaner): {5: 0.118, 6: 0.126}. Using k=6.
```

**lifestyle features**
```
197 neighborhoods; {'people_per_km2': 0.0, 'age_25_34_share': 0.0, 'median_age': 0.0, 'living_alone_share': 0.0, 'renter_share': 0.0, 'big_building_share': 0.0, 'detached_house_share': 0.0, 'median_year_built': 0.01, 'no_car_share': 0.0, 'transit_commute_share': 0.0, 'walk_commute_share': 0.0, 'wfh_share': 0.0, 'median_hh_income': 0.01, 'newcomer_share': 0.0, 'restaurants_800m': 0.0, 'bars_800m': 0.0, 'cafes_800m': 0.0, 'music_1600m': 0.0, 'park_ha_800m': 0.0, 'park_walk_min': 0.0, 'open_water_m': 0.0, 'beach_m': 0.0, 'supermarket_m': 0.0, 'train_station_m': 0.08, 'motorway_m': 0.0, 'violent_per_1000': 0.02, 'vehicle_theft_per_1000': 0.02, 'sqft': 0.2, 'bfloors': 0.93, 'garage': 0.0, 'sqft_per_1000usd': 0.2}
```

**lifestyle colour**
```
197 {'college_degree_share': 0.0, 'households_with_kids_share': 0.0, 'age_65plus_share': 0.0, 'commute_60min_plus_share': 0.0, 'built_since_2010_share': 0.0, 'built_before_1940_share': 0.0, 'tract_median_rent': 0.02, 'rent_burden_pct': 0.01, 'supermarket_m': 0.0, 'trader_joes_m': 0.19, 'whole_foods_m': 0.25, 'target_m': 0.04, 'vet_m': 0.0, 'dog_park_m': 0.0, 'train_station_m': 0.08, 'breweries_1600m': 0.0, 'restaurants_1600m': 0.0, 'transit_to_parents_min': 0.1, 'pool': 0.0, 'garage_or_gated': 0.0, 'street_parking': 0.0, 'building_floors': 0.55, 'building_year': 0.62, 'unit_sqft': 0.2, 'all_in': 0.0}
```

**crime benchmarks**
```
std       3.15           0.95              0.92              0.98                       0.59
min       0.00           0.00              0.00              0.00                       0.00
25%       0.96           0.26              0.28              0.45                       0.27
50%       2.35           0.71              0.69              0.85                       0.56
75%       4.74           1.44              1.38              1.55                       0.92
max      17.21           5.22              5.02              7.26                       3.44
```

**lifestyle groups (saved centres)**
```
enclave :: Berkeley Heights[60]; Harrison[23]; Teaneck[8]; Westport[5]; Montgomery[4]; Fairfield[2]; Watchung[2]; Roxbury[2]; Atlantic Highlands[1]; Montvale[1]
middle :: Stamford[161]; Parsippany-Troy Hills[114]; Jersey City – Journal Square[112]; New Rochelle[85]; Yonkers[69]; Port Chester[59]; White Plains[58]; Jersey City – West Side[50]; Hackensack[41]; Danbury[23]
new_water :: Jersey City – Bergen-Lafayette[135]; Norwalk[96]; Harrison[45]; New Brunswick[23]; North Bergen[12]; Jersey City – Downtown[7]; Weehawken[6]; West New York[4]; Jersey City – Newport[4]; Edgewater[2]
pre_car :: New Haven[303]; Jersey City – McGinley Square[25]; Kew Gardens[6]; Astoria (Central)[2]; Bedford-Stuyvesant (West)[2]; Bay Ridge[2]; Sunnyside[2]; Upper West Side-Manhattan Valley[2]; Brooklyn Heights[1]; Astoria (East)-Woodside (North)[1]
settled :: Newark[46]; Flushing-Willets Point[19]; Hempstead[11]; Jamaica[11]; Jamaica Hills-Briarwood[11]; Mott Haven-Port Morris[9]; East Flatbush-Erasmus[8]; Harlem (North)[7]; Washington Heights (North)[6]; East Harlem (North)[5]
space :: Bridgeport[108]; Bayonne[51]; Dover[41]; Bogota[31]; Clifton[22]; Burlington[21]; Trumbull[19]; Flemington[18]; East Brunswick[18]; Haverstraw[16]
```

**building amenities (cached pages)**
```
passing buildings: 608; already in csv: 754; to process: 0
```

**master tables**
```
  unit floor basis {'unknown': 1258, 'inferred': 941, 'stated': 187, 'confirmed': 65} | label kind of inferred {'simple': 926, 'complex': 15}
  confirmed floor values: 75 read, 10 matched no unit in the master (most are units that left the list), 3 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1752, 'live': 592, 'blocked': 63, 'changed': 28, 'gone': 16} | coordinates {'listing rows agree': 573, 'census_geocoder': 4, 'listing majority, unverified': 1}
  phone answers: 0 listing rows in 0 buildings (data/evidence/call_answers.csv is absent or empty)
  page modification date known: 493 | stale: {'no': 2255, 'open': 163, 'remove': 33} | elevator on a listing site's page alone: 384 buildings | overnight parking rule: {'none': 458, 'permit': 80, 'ban': 24, 'seasonal': 16}
  evidence facts not mapped to a field: {'building_size': 121, 'listing_broker': 60, 'building_site': 54, 'deposit': 26, 'application_fee': 23, 'owner_of_record': 22, 'listing_date': 21, 'openigloo_summary': 16, 'building': 15, 'move_in_fees': 15, 'building_name': 13, 'available_units_listed': 13, 'pet_count_limit': 12, 'openigloo_summary_counts': 10, 'building_size_openigloo': 9, 'dog': 8, 'broker_fee': 7, 'own_site': 7, 'listing_type': 7, 'landlord': 6, 'ownership_change': 6, 'amenities': 5, 'one_time_fee': 5, 'former_or_other_name': 5, 'other_fees': 4}
```

**rent terms**
```
2505 rows -> data/rent_terms.csv
offer_type: {'months_free': 1329, 'none': 817, 'other': 211, 'reduced_deposit_or_fee': 69, 'dollar_credit': 29, 'weeks_free': 35, 'look_and_lease': 15}
listed_price_is: {'net_effective': 152, 'gross': 949, 'unknown': 1404}
needs_call: {'yes': 1587, 'no': 918}
```

**all-in cost**
```
  unknown building fees: 1323
  unknown pet rent: 0
  unknown parking fee: 1510
  unknown gas: 457
  pet rent estimated: 925 | within the cap but likely over once parking and fees are known: 273
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
evidence: 43 units excluded, shown 446, avoid cards 35, of them with an asterisk 265 ({'live check': 176, 'listing': 35, 'elevator': 33, 'dogs allowed': 15, 'eligibility': 5, 'availability': 1}), held for a confirmation 50, waiting for a live check 41
stages: 2451 costed -> -971 over the all-in cap -> -332 Jamaica safety rule -> -108 failed a gate on confirmed facts -> -71 not an apartment (floor plan, building price, co-living room) -> -107 removed by a reviewed verdict -> -1 sibling floor rule -> -58 sketchy -> -43 evidence exclusions -> 760 ranked
shown buildings 191; disclosures: {'floor not published': 396, 'special offer': 234, 'lease term': 92, 'could pass $3,000': 92, 'dog weight limit not published': 22, 'overnight street parking': 19, 'net-effective rent': 15, 'condo rented by its owner': 4}
(kept 760 units; candidates 364; shown 392; pools: {'': 407, 'pool': 340, 'indoor': 13}
```

**rule tests on the output**
```
test_rules (data): 316 checks, 0 failed
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 511, 'display': 309, 'provenance': 193, 'not_used': 17}
shown-list assertions: all pass
```

