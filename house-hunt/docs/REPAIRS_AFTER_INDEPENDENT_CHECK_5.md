# Repairs after independent check 5: pipeline side

2026-11-16. Spec: `docs/INDEPENDENT_CHECK_5.md`. This file covers the pipeline (gates, master tables, cost, ranking,
page data). The page template and the text system were not edited here; what they must do is at the end.

**Shown list: unchanged.** 523 apartments, 202 buildings, 77 neighborhoods before and after; by experience Little-City
217, Room-to-Breathe 154, Old-Neighborhood 72, Fresh-Start 71, Quiet-Street 6, Walk-Everywhere 3. No apartment entered
or left. Apartments with one open item: 218 → 224 (the six of N28). Two consecutive full runs give identical
`ranked_units.csv`, `master_units.csv` and `master_buildings.csv`. Tests: `test_parsers.py` 259, `test_rules.py` 900 pure
checks (`pure_ic5`), `test_rules.py --data` 14,959 with the page data (`data_ic5`, `page_ic5`), `check_registry.py` passes.

`check_published_text.py`: failures: text 2, pipeline strings 0. `verify_all.py`: 18 passed, 2 failed, 1 warning, 1
skipped. The two failures are the same two sentences (below, for the text agent); the warning is `site/dist` being older
than `site/data.json` (`build_site.py` is the page agent's step).

## Item by item

| Item | Result | What was done |
|---|---|---|
| N1 parking kind (S1), D18 | **Fixed** in the data | Parking is structured from every source's words (`parsers.parking_facts`, `build_master.structured_parking`, reviewed table `data/reference/parking_reviewed.csv`). All 202 shown buildings were re-read from their source strings (163 have any parking words). The score, the night moment and `parking.type`'s head read the space she would actually park in. The six buildings of the check and J Centra Burlington are open lots or off-street parking with the garage as a paid extra. The page template must still switch to the new fields |
| N8 garage count | **Fixed** in the data | `shown_figures.buildings_with_garage`. Milford 2 of 4. With every building re-read Stamford is 14 of 24 (the check's 17 took out only TGM; Arrive Stamford, Parc at Glenbrook and Summer Street also include a space whose kind is not a garage) and New Brunswick 0 of 4 (The Edge is an open lot; The George has no parking at the building). The text recomputes from `parking.type`'s head and agrees |
| N3 train station (S2) | **Fixed** in the data | Nearest rail station of any kind, from `data/reference/rail_stations.csv` (1,131 station rows built from the six cached GTFS feeds; NJ Transit's rail feed carries the Hudson-Bergen, Newark and River Line light rail, so no other source was needed). 64 shown buildings (167 apartments) changed station. The label "to a train station" is the text system's |
| N4 broker fee (S2) | **Fixed** | Disclosures "broker fee" (8 apartments), "no broker fee" (19), "one-time costs" (59). The search of every listing's own description found a second case the check did not: **Regency on Hudson, Yonkers, all 7 shown apartments: "Broker Fee applies"** |
| N5 dog weight limit (S2) | **Fixed** | Brookview Commons East has no pound figure (small dogs, with the tour question). All 41 shown buildings with a limit were compared with their evidence rows; every other figure is in a source's own words. A stored limit no source states is now removed by rule |
| N6 washer and dryer (S2) | **Fixed** in the data | `amenities.in_unit_laundry_basis`; disclosure "washer and dryer to confirm" on 70 apartments in 27 buildings; Parkway Lofts and 121 Towne say "In-unit washer (no dryer named)" |
| N9 toll (S3) | **Fixed** in the data | `toll_round_trip_range` per neighborhood (Newark: median $23.79, range $23.79 to $43.05). The sentence is the text system's |
| N11 gas (S3) | **Fixed** | A utility with no estimate adds the median of the estimates that exist to `all_in_likely` (Connecticut gas: $28 to $29). 1177 Greens Farms 212 now carries "could pass $3,000" (likely $3,012). Spinnaker Wharf 5-02E is $2,998 with gas added and stays under |
| N28 stale before tours | **Fixed** | Staleness is counted to the first tour day, 2026-11-22. SoNo 19 Day 207 and Bedford Hall 303, 314, 516, 517, 617 now carry the "listing" item (65 days). One further unit, not shown, changed the same way. No unit crossed the six-month removal line |
| Avoid cards, N19, N13 (car crime) | **Fixed** in the data | Record counts and the car-crime reason are sentences (`build_page_data.record_sentence`, `car_crime_sentence`). They sit only on avoid cards |
| Guard gap (rent line renamed) | **Fixed** | `test_rules.py --data` (`page_ic5`): exactly one rent line, first, equal to the apartment's rent; exactly one pet-rent line; no two lines with one label; the lines sum to the total |
| N20 question twice | **Fixed** | `build_page_data.dedupe_questions` |
| N25 dog amenities | **Fixed** | A dog amenity named in a checker's dog row counts: Kensington Place (dog park), The Wyldes and 153-10 88th Ave (pet spa); also Harmony West (pet spa), 7525 153rd St (dog run), The Hazel Jersey City and Birch House (dog run beside the dog park) |
| N26 dog questions | **Fixed** | Where "are dogs allowed" is the open item, the separate weight question is folded into it ("Are dogs allowed, and up to what weight?"), and 142-38 37th Ave 8E no longer says "the page says small dogs" beside "does not name dogs" |
| N18 "see Connecticut statewide row" | **Fixed** | Hamden and Stamford summaries in `local_rules_round2.csv` and its source rows |
| D25 building named by its address | **Fixed** | "41-42 Elbertson Street, Elmhurst NY" is no longer a name. "LOCAL RULES Ask" and "not found, ask" are the page template's strings |
| D14 Franklin | **Not moved** | Its frozen profile is nearest Little-City at 1.94, second Room-to-Breathe at 2.85 (ratio 0.68; a boundary case is 0.9 or more). The distances do not support another group. The misfit comes from the profile describing two buildings and a wider area than The Grove Somerset; a refit is the owner's call |
| N24 one building as two | **Not fixed** | 3310 Nostrand Ave and 3280-3310 Nostrand Ave. The range rule joins a range of up to 20 house numbers; this one spans 30 and the listing calls it a garden complex, so the two apartments may be in different buildings. Joining them would pool their elevator and floor evidence |
| N29 `years[].label` | **Not fixed** | The label is a key `site/illustrations.json` is filed under and is not printed |
| D10 Beacon Falls | Unchanged | For the owner, as before |
| N2, N7, N10, N12, N14, N21, N22, N23, D27, D28, D29 | Not pipeline items | Page template or text system |
| N15, N16, N17, N27 | Not pipeline items | Text system |

## Parking: every building whose kind changed

24 shown buildings (68 apartments) changed the word for their parking; 16 of them (59 apartments) changed score rank.
The night moment changed on 49 apartments (42 from strong to mixed, 7 from mixed to strong).

| Building | Was | Now |
|---|---|---|
| Spinnaker Wharf, Milford | garage | Free off-street parking; covered and garage spaces are extra (fee not published) |
| TGM Anchor Point, Stamford | garage | A free open lot; assigned outdoor $65, gated lot $85, garage $150 |
| The Edge at Raritan Heights | garage | A free open lot |
| Kensington Place | garage | A free open lot; garage spaces are extra (fee not published) |
| Woodmont West | garage | A free open lot; garage $125 |
| Reserve at Riverdale | garage | A free open lot; garage $50 |
| J Centra Burlington | garage | An open lot, fee not published; garages are an optional extra |
| Arrive Stamford | garage | A free assigned space (the listing does not say where) |
| Parc at Glenbrook | garage | A free parking space of unnamed kind (scored as a lot) |
| Summer Street, Stamford | garage | Free off-street parking |
| The George New Brunswick | garage | Off-site: a permit at a nearby deck, $185 |
| The Walcott Hackensack | garage | Covered parking, $125 (the fee line says covered) |
| The Royce at Trumbull | covered | Free off-street parking; carports are extra |
| Parkway Lofts | lot | Garage parking, $150 ("Garage Parking: Assigned Parking") |
| Two South Willow | lot | Garage parking, $150 |
| The Brunswick | lot | Covered parking, $125 (the kind the counted fee pays for) |
| The Elks, 948 New York Ave, 12333 83rd Ave | lot | An assigned space (the listing does not say where) |
| 219 Lenox Rd, 1644 New York Ave, 1825 and 1802 Ocean Ave, One Clinton Park | nothing | Parking of a kind the listing does not name |

Also: The Hampton, Hackensack: the assigned rear-lot space is included (reviewed table; the fee was "not published").
Side effect on the cost: the median parking fee by kind is recomputed over the corrected kinds (New Jersey lots: $0), so
`all_in_likely` moved on a few apartments: "could pass $3,000" 108 → 106 (in: 1177 Greens Farms 212, Harbor Pointe
B9-449; out: The Botanic 245, Grandville Towers 5F and 9C, Alexander Crossing 0405).

## Nearest station: what changed

64 buildings, 167 apartments: 31 buildings now measure to a subway station, 22 to light rail, 9 to PATH, 2 to the same
commuter station at a corrected point (Peekskill). The other 138 buildings keep their station and distance.

| Neighborhood | Was (median) | Now |
|---|---|---|
| Jersey City – Journal Square | 1.8 miles (Hoboken) | PATH, Journal Square, 654 m |
| Jersey City – Bergen-Lafayette | 2.3 miles | light rail, Liberty State Park, about 270 m |
| Jersey City – West Side | 3.3 miles | light rail, West Side Avenue, about 400 m |
| Bayonne | 4.8 miles | light rail, 22nd / 45th Street, 353 m |
| Newark | 885 m | light rail, 202 m |
| Harrison | 902 m | PATH, Harrison, about 400 m |
| Weehawken | 1.8 miles | light rail, Port Imperial, 343 m |
| Elmhurst | 1.3 miles | subway, Elmhurst Av, about 240 m |
| East Flatbush (both), Prospect Lefferts Gardens, Jamaica, Briarwood, Inwood, Harlem, Washington Heights, East Harlem, Astoria | 0.5 to 2.9 miles | subway, 200 to 500 m (Astoria-Hallets Point 1.4 km) |
| Burlington | 4.9 miles | light rail (River Line), 3.4 miles |

## What the text agent must do

Two sentences fail `check_scene_text.py` / `check_published_text.py` and do not heal on a rebuild:

1. `nj:east-brunswick`, `sub_local_rules`: "Check the dog park's rules before you go." Kensington Place now has its own
   dog park (N25), so every building shown there has a dog area.
2. Apartment `trulia:b1001929374:Unit_N_A-0508:449127273` (The George New Brunswick), `headlines.parking.subhead`:
   "Parking is in the building's lot, with the fee published." The parking is off-site (`parking.kind = "offsite"`,
   `parking.type` head `offsite`). `realtor_lines.parking_kind` has no off-site case and falls back to "onsite".

Fields to use:

- **Parking.** `parking.summary` is a ready sentence ("A free open lot; garage spaces are $150 a month."). Structured:
  `parking.kind` (the space she would park in: `garage`, `gated_lot`, `covered`, `assigned_lot`, `open_lot`,
  `off_street`, `assigned`, `offsite`, `street`, `unspecified`), `parking.kind_words`, `parking.kinds` (**new
  vocabulary**, was `lot / garage / covered / street / offsite`), `parking.included_kind` (set only when `fee` is 0),
  `parking.included_basis`, `parking.optional_kinds[]` (`kind`, `kind_words`, `fee`, `fee_high`, `fee_basis`),
  `parking.fee_kind`, `parking.kinds_basis`, `parking.assigned`, `parking.garage_is_optional_extra` (now: a plain lot
  with a garage or covered space as a paid extra). `parking.type` is `<head>: <source words>` with head `garage`,
  `covered`, `lot`, `assigned`, `street_only`, `offsite` or `parking`; `realtor_lines.parking_kind` and
  `check_scene_text` read the head and so follow the correction. New heads to handle: `assigned`, `offsite`, `parking`.
- **Station.** `moments.sat.train_station` / `train_station_m` are now the nearest station of any kind;
  `train_station_kind` is `train`, `subway`, `PATH` or `light rail`; `train_station_system`; `commuter_station`,
  `commuter_station_m`, `commuter_station_system`. Per neighborhood: `shown_figures.train_station_kind`,
  `train_station`, `train_station_system`, `train_station_kinds` (counts), `commuter_station_m`. "At a glance" should
  say "to a PATH station", "to a subway station", "to a light rail stop" or "to a train station" from the kind.
- **Tolls.** `neighborhoods[].toll_round_trip_range` and `toll_round_trip_mail_range` ([low, high]). Newark is
  [23.79, 43.05]: "about $24 to $43".
- **Garage counts.** `shown_figures.buildings_with_garage`, `buildings_with_garage_or_covered`,
  `buildings_with_garage_as_paid_extra`.
- **Laundry.** `amenities.in_unit_laundry_basis` (`listing_site_appliance_list` or `page_says_in_apartment`),
  `amenities.in_unit_appliances` (`washer and dryer`, `washer`, `dryer`). Do not write "washer and dryer" where it is
  `washer`.
- **Disclosures** (new `what` / `code`): `broker fee` / `broker_fee`, `no broker fee` / `no_broker_fee` (no question),
  `one-time costs` / `one_time_costs`, `washer and dryer to confirm` / `laundry_appliance_list`. Also
  `units[].one_time` = `{broker_fee: "applies" | "none" | null, broker_fee_source, one_time_costs, in_monthly_total: false}`.
- "Could pass $3,000" may now name gas among the unpublished lines.

## What the page agent must do

- **N1.** Stop deriving "Garage" from `parking.rank` alone. Print `parking.summary`, or build the line from
  `parking.kind`, `included_kind` and `optional_kinds`. Use it in the header chip, "Coming home", the compare row and
  "At a glance". The "Garage or covered" filter should test `parking.kind` in (`garage`, `gated_lot`, `covered`).
  `parking.rank` now follows the kind (a free open lot is 2), so the old code already stops saying "Garage" for the 22
  apartments, but it cannot say "a free open lot; garage spaces are extra" without the new fields. The quoted source
  words are still in `parking.type` (after the head) and `parking.options_text`; `parking.included_quote` does not exist
  (the raw words are `included_words_internal`, not for display).
- **N3.** Label the station by `train_station_kind`.
- **N4 / N6.** New disclosures arrive in `disclosures[]` with `label`, `why`, `question` like the others; "no broker
  fee" has `question: null`. One-time costs must not be added to any total.
- **N6.** The filter "A washer and dryer in the apartment" can exclude or mark `in_unit_laundry_basis ==
  "listing_site_appliance_list"`.
- **Avoid cards.** `evidence.items[]` now carry `kind` (`record` or `quote`). A record's `excerpt` is a sentence that
  starts with the count, so the existing "On record: " prefix reads correctly; do not put it in quotation marks. Its
  `date` is still the window key (`last_6_months`): show `window_words` ("the last six months") or nothing, not "date
  not known". The raw count is in `excerpt_internal`.
- **No crime in the open.** `evidence.pause_points` on shown apartments still include lines such as "1 report of a safety
  incident at the address" and "1 mention of car crime at the building": keep them behind a tap.
- **N28.** Six more apartments carry a star ("listing"); their `confirm.why` counts the days to "the first tour day,
  November 22".
- `tour_questions` no longer repeat a question; where dogs are the open item the weight question is part of it.
