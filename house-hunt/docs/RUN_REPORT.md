# Run report (2026-11-17T21:50:49+00:00)

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
| listings harvested (after dedupe) | 21095 | 21095 | +0 |
| pass every listing gate | 1179 | 1179 | +0 |
|   pending: a gate fact is unstated | 7512 | 7512 | +0 |
|   fail a gate | 12404 | 12404 | +0 |
| costed in the master table | 1097 | 1097 | +0 |
| within the $3,000 all-in cap | 1097 | 1097 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 429 | 436 | -7 |
| shown (real apartments, at most one open item, up to 8 per building, after the thin-neighborhood rule) | 359 | 365 | -6 |
|   neighborhoods shown | 65 | 66 | -1 |
|   buildings shown | 191 | 196 | -5 |
| not an apartment: floor plan, building price or co-living room (data/excluded_not_an_apartment.csv) | 80 | 80 | +0 |
| no apartment number from any source (data/excluded_no_apartment_number.csv) | 59 |  |  |
| thin neighborhoods cut (one apartment, not both well attested and promising) | 37 | 38 | -1 |
| avoid cards | 17 | 17 | +0 |
|   shown with an asterisk (one thing to confirm) | 240 | 246 | -6 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 32 | 32 | +0 |
| held back for one confirmation | 32 | 33 | -1 |
| neighborhoods with 3+ shown places | 39 | 40 | -1 |
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

- two or more things unconfirmed: floor and elevator: 48
- listing: 28
- listing 60+ days old: 21
- availability: 20
- floor 3 or above (inferred) and no elevator stated on any page or record, and the building's height is not known (owner, 2026-11-17: floor 3 and above need an elevator): 11
- dogs allowed: 8
- two or more things unconfirmed: dogs allowed: 4
- floor 3 or above (confirmed) and no elevator stated on any page or record, and the building's height is not known (owner, 2026-11-17: floor 3 and above need an elevator): 4

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               5 |       31 |      30 |             0 |
| The Little-City Year      |              24 |      102 |      82 |             4 |
| The Old-Neighborhood Year |              16 |       66 |      54 |            10 |
| The Quiet-Street Year     |               7 |        9 |       3 |             0 |
| The Room-to-Breathe Year  |              53 |      215 |     188 |             0 |
| The Walk-Everywhere Year  |               2 |        6 |       2 |             3 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 89 |
| unit_floor | 40 |
| elevator_basis | 30 |
| dog_weight_limit_lb | 16 |
| parking_type | 74 |
| parking_fee | 25 |
| pet_rent | 49 |
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

**gates (merge, dedupe, gate each listing)**
```
| movein | 7987 | 961 | 12147 |
| dog | 10655 | 1593 | 8847 |
| floor_elevator | 17579 | 1703 | 1813 |
| place | 21065 | 0 | 30 |
| proof | 12569 | 7 | 8519 |
| elevator | 5441 | 876 | 14778 |
```

**NYC building class (PLUTO)**
```
3043 NYC buildings; {'house_number+location': 1495, 'nearest_lot': 831, 'no_lot_within_40m': 717}
{'no': 1151, 'yes': 954, nan: 717, 'unknown': 221}
```

**gates again with PLUTO**
```
| movein | 7987 | 961 | 12147 |
| dog | 10655 | 1593 | 8847 |
| floor_elevator | 17579 | 1703 | 1813 |
| place | 21065 | 0 | 30 |
| proof | 12569 | 7 | 8519 |
| elevator | 5441 | 876 | 14778 |
```

**lookup tools per building**
```
600 680
625 680
650 680
675 680
{'pass': 1179} buildings: 680
coordinates: {'listing rows agree': 611, 'census_geocoder (address check)': 4, 'census_geocoder': 1, 'listing majority, unverified': 1}; lookups redone at a corrected coordinate: 0 address keys
```

**neighborhood assignment**
```
municipality from geography differs from the listed city for 82 address keys (data/reference/municipality_changes.csv)
# Checkpoint A: neighborhoods and proposed years
Passing units: 1179 in 680 buildings, across 211 neighborhoods; 84 neighborhoods have 3+ passing places.
Cluster quality (silhouette; higher is cleaner): {5: 0.138, 6: 0.152}. Using k=6.
```

**lifestyle features**
```
211 neighborhoods; {'people_per_km2': 0.0, 'age_25_34_share': 0.0, 'median_age': 0.0, 'living_alone_share': 0.0, 'renter_share': 0.0, 'big_building_share': 0.0, 'detached_house_share': 0.0, 'median_year_built': 0.0, 'no_car_share': 0.0, 'transit_commute_share': 0.0, 'walk_commute_share': 0.0, 'wfh_share': 0.0, 'median_hh_income': 0.0, 'newcomer_share': 0.0, 'restaurants_800m': 0.0, 'bars_800m': 0.0, 'cafes_800m': 0.0, 'music_1600m': 0.0, 'park_ha_800m': 0.0, 'park_walk_min': 0.0, 'open_water_m': 0.0, 'beach_m': 0.0, 'supermarket_m': 0.0, 'train_station_m': 0.0, 'motorway_m': 0.0, 'violent_per_1000': 0.04, 'vehicle_theft_per_1000': 0.04, 'sqft': 0.19, 'bfloors': 0.98, 'garage': 0.0, 'sqft_per_1000usd': 0.19}
```

**lifestyle colour**
```
211 {'college_degree_share': 0.0, 'households_with_kids_share': 0.0, 'age_65plus_share': 0.0, 'commute_60min_plus_share': 0.0, 'built_since_2010_share': 0.0, 'built_before_1940_share': 0.0, 'tract_median_rent': 0.01, 'rent_burden_pct': 0.0, 'supermarket_m': 0.0, 'trader_joes_m': 0.32, 'whole_foods_m': 0.35, 'target_m': 0.12, 'vet_m': 0.0, 'dog_park_m': 0.0, 'train_station_m': 0.05, 'breweries_1600m': 0.0, 'restaurants_1600m': 0.0, 'transit_to_parents_min': 0.18, 'pool': 0.0, 'garage_or_gated': 0.0, 'street_parking': 0.0, 'building_floors': 0.78, 'building_year': 0.8, 'unit_sqft': 0.19, 'all_in': 0.0}
```

**crime benchmarks**
```
std       2.87           0.87              0.84              1.04                       0.70
min       0.00           0.00              0.00              0.00                       0.00
25%       0.71           0.21              0.21              0.45                       0.22
50%       1.65           0.50              0.48              0.84                       0.50
75%       3.43           1.02              0.98              1.78                       0.92
max      17.21           5.22              5.02              7.26                       4.56
```

**lifestyle groups (saved centres)**
```
enclave :: Mount Olive[6]; South Brunswick[6]; Millburn[3]; Fairfield[2]; East Fishkill[2]; Wilton[1]; Howell[1]; Independence[1]; Verona[1]; Brightwaters[1]
middle :: Plainsboro[34]; Stamford[27]; Franklin[20]; Milford[16]; Bloomfield[13]; Danbury[12]; Jersey City – West Side[12]; Yonkers[11]; Long Branch[9]; Elizabeth[7]
new_water :: Norwalk[22]; New Brunswick[16]; West New York[8]; Jersey City – Bergen-Lafayette[5]; North Bergen[4]; Harrison[2]; Long Island City-Hunters Point[1]
pre_car :: New Haven[189]; Jersey City – McGinley Square[11]; Astoria (Central)[3]; Bay Ridge[1]; Brooklyn Heights[1]; Crown Heights (North)[1]; East Williamsburg[1]; Kew Gardens[1]; Sunnyside[1]; Woodside[1]
settled :: Newark[57]; Flushing-Willets Point[10]; Jackson Heights[10]; Jamaica Hills-Briarwood[8]; Hempstead[5]; Forest Hills[3]; Norwood[3]; Union City[2]; Tremont[2]; Bensonhurst[2]
space :: Bridgeport[41]; Paterson[41]; Hamden[40]; East Haven[25]; Bayonne[21]; Woodbridge[21]; West Haven[17]; West Windsor[14]; Lawrence[14]; Newburgh[13]
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
evidence: 20 units excluded, shown 359, avoid cards 17, of them with an asterisk 240 ({'floor and elevator': 204, 'listing': 15, 'elevator': 10, 'availability': 5, 'dogs allowed': 3, 'eligibility': 3}), held for a confirmation 32; shown and never re-read (information only, not an open item) 48
stages: 1097 costed -> -0 over the all-in cap -> -235 Jamaica safety rule -> -143 failed a gate on confirmed facts -> -80 not an apartment (floor plan, building price, co-living room) -> -59 no apartment number -> -32 removed by a reviewed verdict -> -0 sibling floor rule -> -99 sketchy -> -20 evidence exclusions -> 429 ranked
shown buildings 191; disclosures: {'income requirement': 186, 'floor not published': 136, 'special offer': 132, 'lease term': 55, 'one-time costs': 52, 'no broker fee': 33, 'washer and dryer to confirm': 31, 'overnight street parking': 30, 'something else to know': 19, 'dog weight limit not published': 12, 'broker fee': 7, 'furnished apartment': 6, 'condo rented by its owner': 4, 'credit score requirement': 4, 'net-effective rent': 1}
(kept 429 units; candidates 302; shown 317; pools: {'': 384, 'pool': 42, 'indoor': 3}
```

**rule tests on the output**
```
test_rules (data): 719 checks, 0 failed
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 576, 'display': 345, 'provenance': 212, 'not_used': 14}
shown-list assertions: all pass
```

