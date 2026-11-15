# Run report (2026-11-15T21:45:29+00:00)

## Steps

| Step | Script | Result |
|---|---|---|
| building amenities (cached pages) | `building_amenities.py --no-fetch` | ok |
| master tables | `build_master.py` | ok |
| rent terms | `rent_terms.py` | ok |
| all-in cost | `all_in.py` | ok |
| evidence rules (avoid, exclusions) | `avoid.py` | ok |
| ranking and selection | `rank.py` | ok |
| field registry and wiring check | `check_registry.py` | ok |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 18290 |  |  |
| pass every listing gate | 2027 |  |  |
|   pending: a gate fact is unstated | 12069 |  |  |
|   fail a gate | 4194 |  |  |
| costed in the master table | 1524 |  |  |
| within the $3,000 all-in cap | 1313 |  |  |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 961 |  |  |
| shown (every gate fact confirmed or stated; top 10 per neighborhood) | 207 |  |  |
| avoid cards | 24 |  |  |
| held back for one confirmation | 201 |  |  |
| neighborhoods with 3+ shown places | 26 |  |  |
| buildings in the master table | 551 |  |  |

## Why units left

**excluded_by_confirmed_facts.csv**

- dogs not allowed (confirmed): 20
- no elevator (confirmed on the building's page): 7
- listing gone at live check: 4
- income-restricted unit: 3
- ground-floor unit: 1

**excluded_sketchy.csv**

- two or more unconfirmed gate facts: 87
- listing 60+ days old: 27
- no unit or building named: 5
- price far below the neighborhood: 5
- live check judged the listing doubtful: 3
- conflicting dog policy: 2
- thin syndicated feed: 2

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               5 |       50 |      15 |             0 |
| The Little-City Year      |              26 |      460 |      77 |             2 |
| The Old-Neighborhood Year |              46 |      163 |      62 |            20 |
| The Quiet-Street Year     |              14 |       36 |       6 |             0 |
| The Room-to-Breathe Year  |              46 |      242 |      42 |             0 |
| The Walk-Everywhere Year  |               8 |       10 |       5 |             2 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 81 |
| unit_floor | 100 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 19 |
| parking_type | 77 |
| parking_fee | 16 |
| pet_rent | 36 |
| pool | 40 |
| doorman | 36 |
| year_built | 53 |
| toll_rt_ezpass | 41 |
| transit_sat_median | 91 |
| near_violent_250m_24m | 26 |
| live_status | 90 |
| rent_first_full_payment_date | 80 |
| ev_pause_notes | 18 |

## Last lines of each step

**building amenities (cached pages)**
```
  year_built                    106   18.4%
  year_renovated                 15    2.6%
  total_floors                   22    3.8%
  unit_count                    143   24.8%
  management_company             95   16.5%
  fetched: 0
```

**master tables**
```
  pool                   {'unknown': 383, 'confirmed': 124, 'amenities_page': 40, 'community_page': 4}
  doorman                {'unknown': 409, 'confirmed': 98, 'amenities_page': 44}
  year_built             {'unknown': 251, 'official_record': 153, 'confirmed': 131, 'amenities_page': 16}
  manager                {'stated': 258, 'confirmed': 182, 'unknown': 105, 'amenities_page': 6}
  utilities_included     {'unknown': 481, 'confirmed': 59, 'stated': 11}
  unit floor basis {'inferred': 1122, 'unknown': 229, 'stated': 111, 'confirmed': 62} | live status {'not checked': 1054, 'live': 450, 'changed': 11, 'blocked': 5, 'gone': 4}
```

**rent terms**
```
1524 rows -> data/rent_terms.csv
offer_type: {'months_free': 438, 'none': 1006, 'other': 51, 'reduced_deposit_or_fee': 20, 'dollar_credit': 6, 'look_and_lease': 3}
listed_price_is: {'net_effective': 86, 'gross': 1045, 'unknown': 393}
needs_call: {'yes': 490, 'no': 1034}
```

**all-in cost**
```
units 1524; cost gate {'pass': 1313, 'fail': 211}; rent asterisk 518; rent terms file present
  unknown building fees: 1045
  unknown pet rent: 816
  unknown parking fee: 1245
  unknown gas: 118
  gross above cap while basis passes: 65
```

**evidence rules (avoid, exclusions)**
```
                                              120 e 144th st|10451                                                                                                                         car crime: 58 vehicle thefts and thefts from vehicles within 250 m in 24 months (police data), at least double the median of 20 for candidate buildings in New York City
                       135-23 82nd ave 3e queens ny 11435 us|11435                                                                                                                                                                                                elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                              13523 82nd ave|11435                                                                                                                                                                                                elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                               14202 84th dr|11435                                                                                                                                                                  management: city records in the last 6 months above the 90th percentile on class_c_violations, mold_complaints, pest_complaints
                                           14345 sanford ave|11355                                                                                                                                                                                                elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings
                                              14725 94th ave|11435                                                                                                                         car crime: 46 vehicle thefts and thefts from vehicles within 250 m in 24 months (police data), at least doubl
```

**ranking and selection**
```
evidence: 59 units excluded, shown 207, avoid cards 24, shown-but-not-yet-evidence-checked 21
stages: 1524 costed -> -211 over the all-in cap -> -129 Jamaica safety rule -> -35 failed a gate on confirmed facts -> -129 sketchy -> -59 evidence exclusions -> 961 ranked
(kept 961 units; candidates 438; shown 407; pools: {'pool': 494, '': 448, 'indoor': 19}
```

**field registry and wiring check**
```
field registry: {'used': 429, 'display': 293, 'provenance': 117, 'not_used': 18}
```

