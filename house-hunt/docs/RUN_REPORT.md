# Run report (2026-11-16T04:43:01+00:00)

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
| rule tests on the output | `test_rules.py --data` | FAILED |
| field registry, wiring check, shown-list assertions and the review rule | `check_registry.py` | FAILED |

## Stage counts

| Stage | Now | Previous run | Change |
|---|---|---|---|
| listings harvested (after dedupe) | 20468 | 20468 | +0 |
| pass every listing gate | 2505 | 2505 | +0 |
|   pending: a gate fact is unstated | 14019 | 14019 | +0 |
|   fail a gate | 3944 | 3944 | +0 |
| costed in the master table | 2451 | 2451 | +0 |
| within the $3,000 all-in cap | 1469 | 1469 | +0 |
| ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions) | 656 | 656 | +0 |
| shown (real apartments, at most one open item, up to 8 per building, after the thin-neighborhood rule) | 523 | 523 | +0 |
|   neighborhoods shown | 77 | 77 | +0 |
|   buildings shown | 202 | 202 | +0 |
| not an apartment: floor plan, building price or co-living room (data/excluded_not_an_apartment.csv) | 76 | 76 | +0 |
| thin neighborhoods cut (one apartment, not both well attested and promising) | 28 | 28 | +0 |
| avoid cards | 35 | 35 | +0 |
|   shown with an asterisk (one thing to confirm) | 218 | 218 | +0 |
| removed by a reviewed verdict (data/evidence/review_verdicts.csv) | 88 | 88 | +0 |
| held back for one confirmation | 14 | 14 | +0 |
| neighborhoods with 3+ shown places | 50 | 50 | +0 |
| buildings in the master table | 578 | 578 | +0 |

## Why units left

**excluded_by_confirmed_facts.csv**

- listing gone at live check: 38
- income-restricted unit: 38
- ground-floor unit: the unit number reads as floor 1 under this complex's numbering (numbering convention of this complex: building_floor_unit): 33
- dogs not allowed (confirmed): 14
- ground-floor unit: the unit number reads as floor 1 under this complex's numbering (numbering convention of this complex: floor_first): 9
- stale listing: the listing page was last changed on 2026-04-13, 216 days before it was read (2026-11-15): more than six months unchanged: 7
- ground-floor unit: 5
- ground-floor unit: a bare apartment number in a building numbered in sequence, at most the average number of apartments per floor, reads as the first floor: 4

**excluded_sketchy.csv**

- two or more things unconfirmed: elevator: 54
- listing: 30
- eligibility: 26
- listing 60+ days old: 23
- dogs allowed: 10
- two or more things unconfirmed: dogs allowed: 9
- elevator not stated on any page and the building's height is not known (it was guessed from the unit label): 8
- availability: 6

## Shown units by year

| group_label               |   neighborhoods |   ranked |   shown |   avoid_cards |
|:--------------------------|----------------:|---------:|--------:|--------------:|
| The Fresh-Start Year      |               6 |       86 |      71 |             0 |
| The Little-City Year      |              28 |      244 |     217 |             5 |
| The Old-Neighborhood Year |              39 |      111 |      72 |            26 |
| The Quiet-Street Year     |               7 |       10 |       6 |             0 |
| The Room-to-Breathe Year  |              33 |      185 |     154 |             0 |
| The Walk-Everywhere Year  |               6 |       20 |       3 |             4 |

## Fill rate among shown units (percent with a value)

| Field | % |
|---|---|
| sqft | 93 |
| unit_floor | 57 |
| elevator_basis | 100 |
| dog_weight_limit_lb | 21 |
| parking_type | 88 |
| parking_fee | 31 |
| pet_rent | 60 |
| pool | 48 |
| doorman | 36 |
| year_built | 50 |
| toll_rt_ezpass | 100 |
| transit_sat_median | 95 |
| near_violent_250m_24m | 10 |
| live_status | 85 |
| rent_first_full_payment_date | 55 |
| ev_pause_notes | 25 |

## Last lines of each step

**parser tests (every example in docs/INDEPENDENT_CHECK.md)**
```
test_parsers: 259 assertions passed
```

**rule tests (every repaired defect and rule, pure)**
```
test_rules (rules): 481 checks, 0 failed
```

**building amenities (cached pages)**
```
passing buildings: 608; already in csv: 754; to process: 0
```

**master tables**
```
  unit floor basis {'unknown': 1258, 'inferred': 941, 'stated': 187, 'confirmed': 65} | label kind of inferred {'simple': 926, 'complex': 15}
  confirmed floor values: 75 read, 10 matched no unit in the master (most are units that left the list), 3 not parseable (data/reference/floor_confirm_unmatched.csv)
  live status {'not checked': 1551, 'live': 763, 'blocked': 63, 'gone': 38, 'changed': 36} | coordinates {'listing rows agree': 569, 'census_geocoder': 4, 'census_geocoder (address check)': 4, 'listing majority, unverified': 1}
  phone answers: 0 listing rows in 0 buildings (data/evidence/call_answers.csv is absent or empty)
  page modification date known: 1118 | stale: {'no': 2251, 'open': 167, 'remove': 33} | elevator on a listing site's page alone: 384 buildings | overnight parking rule: {'none': 458, 'permit': 80, 'ban': 24, 'seasonal': 16}
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
  pet rent estimated: 925 | within the cap but likely over once parking and fees are known: 267
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
evidence: 36 units excluded, shown 523, avoid cards 35, of them with an asterisk 218 ({'elevator': 118, 'listing': 61, 'dogs allowed': 28, 'availability': 8, 'eligibility': 3}), held for a confirmation 14; shown and never re-read (information only, not an open item) 102
stages: 2451 costed -> -982 over the all-in cap -> -330 Jamaica safety rule -> -177 failed a gate on confirmed facts -> -76 not an apartment (floor plan, building price, co-living room) -> -88 removed by a reviewed verdict -> -1 sibling floor rule -> -105 sketchy -> -36 evidence exclusions -> 656 ranked
shown buildings 202; disclosures: {'floor not published': 478, 'special offer': 302, 'lease term': 129, 'could pass $3,000': 108, 'dog weight limit not published': 29, 'overnight street parking': 18, 'net-effective rent': 15, 'furnished apartment': 11, 'income requirement': 9, 'condo rented by its owner': 4, 'credit score requirement': 3}
(kept 656 units; candidates 349; shown 374; pools: {'': 363, 'pool': 280, 'indoor': 13}
```

**rule tests on the output**
```
test_rules (data): 423 checks, 1 failed
  FAIL verdicts: a shown unit has no ok / asterisk / disclose verdict
```

**field registry, wiring check, shown-list assertions and the review rule**
```
field registry: {'used': 530, 'display': 308, 'provenance': 201, 'not_used': 17}
SHOWN-LIST ASSERTIONS FAILED: 2 violation(s)
   trulia:b2750786817:Unit_3A:2055428529 (Appletree Suites 3A): no reviewed verdict: nobody has read this unit's evidence
   trulia:b2750786817:Unit_5A:2062657819 (Appletree Suites 5A): no reviewed verdict: nobody has read this unit's evidence
```

