# Repairs after the independent check

Written 2026-11-15, after `docs/INDEPENDENT_CHECK.md` (W1–W20, A1–A25). Nothing was committed by this pass. No file
under `data/listings_raw/`, no `data/evidence/*_batch_*` file and no harvest script was changed: the repairs change
how those files are **read**.

New files: `scripts/parsers.py` (every text parser, pure functions), `scripts/test_parsers.py` (259 plain asserts, one
for every example string quoted in the check; first step of `scripts/run_all.py`), `data/needs_live_check.csv`,
`data/duplicate_units.csv`, `data/reference/floor_confirm_unmatched.csv`, `data/reference/building_geocode_changes.csv`.

## Counts before and after

"Before" is the state the independent check saw (run of 21:56 UTC). **The two columns are not the same listing set:**
other agents added listings while this work ran (18,290 → 20,464 after dedupe), so the totals moved for that reason
too. The last table follows the 207 units shown before, which removes that effect.

| | Before | After |
|---|---|---|
| Listings after dedupe | 18,290 | 20,464 |
| Listings failing the floor gate / on the floor gate alone | 1,612 / 1,269 | 1,076 / 804 |
| Units costed in the master | 1,524 | 2,020 (22 duplicates of a unit in the same building removed) |
| Units over the $3,000 all-in cap | 211 | 356 |
| Ranked | 961 | 1,185 |
| **Shown** | **207** | **120** |
| Held for one confirmation (`needs_confirmation.csv`) | 200 | 317 |
| Clean, waiting for a live check (`needs_live_check.csv`) | did not exist (21 shown without one, 5 "blocked") | 93, none shown |
| Avoid cards | 27 | 30 |
| Avoid buildings | 48 | 48 (three reasons reworded or removed, see W19) |
| Neighborhoods with 3+ shown places | 26 | 13 |
| Rows in `master_conflicts.csv` | 212 | 53 |

Shown units by basis:

| Fact | Before (207) | After (120) |
|---|---|---|
| Floor: confirmed | 20 | 32 |
| Floor: stated on the page | 23 (17 of them really derived from the unit number) | 1 |
| Floor: inferred | 164 (any label) | 87, all from a simple label, floor 3 or higher, marked "read from the unit number" |
| Elevator: confirmed / amenities page / official record / stated | 182 / 14 / 6 / 5 | 112 / 2 / 6 / 0 |
| Dogs allowed: confirmed / stated | 193 / 14 | 116 / 4 |
| "Small dogs", no pound figure | 60, unmarked | 52, each with the note and tour question (owner's rule, below) |
| Live check: live / changed / blocked / none | 179 / 2 / 5 / 21 | 119 / 1 / 0 / 0 |
| Rent asterisk (special offer) | 52 | 45 |
| Most shown in one building | 3 | 2 |

What happened to the 207 units shown before:

| Outcome | Units |
|---|---|
| Still shown | 93 |
| Held: "Which floor is the unit on?" (floor 2 from a label, a complex label, or no reading) | 56 |
| Held: elevator only inferred | 2 |
| Ranked but not clean on another count, not selected | 15 |
| Over the $3,000 cap once parking, fees and utilities were read correctly | 14 |
| Waiting for a live check | 12 |
| No longer in the master (source row changed or gone since the check) | 10 |
| Merged as a duplicate of another listing of the same unit | 3 |
| Excluded (hard gate 1, sketchy 1) | 2 |

## Owner's change during the repair: "small dogs" passes

The coordinator's first instruction for W2 was to hold "small dogs, no number" units. The owner then changed the rule:
her dog is at most 25 lb, so a size word with no pound figure **passes** the dog gate. As implemented:

- `rank.py`: such a unit is not held on that ground and can be shown; it carries `dog_size_note` = "page says small
  dogs; no weight number" and the tour question "Confirm the dog weight limit in pounds".
- Still excluded: dogs not allowed, service or support animals only, a stated limit under 25 lb, and a harvester's
  `BUILDING_FAILS` note for any reason other than "small dogs only" (`parsers.building_fails_reason`).
- `check_registry.py` asserts that a shown size-only unit has its note and tour question.
- In the dog score the weight variable treats size-only as unknown (it was penalised before).

## Wiring defects

**W1. Floor guessed from the unit label.**
- `parsers.floor_from_label`: a floor is read only from 1–2 digits + letters ("4F" → 4) or exactly three digits
  ("305" → 3). Labels with a separator, a building prefix or four digits give a floor only when the building's floor
  count leaves exactly one reading ("7012" in 13 floors → 7; "3203" in 3 floors → unknown). A reading above the
  building's floor count is rejected, not clamped.
- `gates.py: gate_floor`: writes `floor_basis` and `floor_label_kind`. A harvester's `floor` whose note says "floor
  derived from unit number" is treated as inferred, not stated.
- `build_master.py` (unit table): `unit_floor_basis` is confirmed / stated / inferred / unknown, with
  `unit_floor_label_kind`. An evidence row that read the floor "from unit number" is inferred whatever its status.
- `rank.py`: clean on floor only if confirmed or stated; an inferred floor ≥ 3 from a simple label is accepted with
  `floor_basis_note` and the tour question "Confirm the floor"; everything else is held.

**W2. Small dogs.** See the owner's change above. Building-level flag `dog_size_only` is set from the listing's pet
card, the harvest note and any evidence row (whatever its status). The three "contradicts: small dogs only" buildings
are no longer mis-read as a number; they pass under the owner's rule with the note.

**W3. Harvester inference labelled "stated".** `gates.py: gate_elevator` returns `inferred_harvester` when the note
says "elevator: 6+ floors". `build_master.py`: an evidence row marked confirmed whose value says "inferred / implied"
is `inferred`; `unconfirmed` rows are skipped for every fact. Left as is: `amenities_page`, `official_record` and
`stated` remain acceptable bases even where the evidence pass could not separately confirm them.

**W4. Fact `parking` unmapped.** `build_master.py: apply_fact, add_parking` and `parsers.parse_parking`. Parking is now
read from the evidence facts `parking`, `parking_fee`, `parking_type`, `garage`, the listing's parking sentence, Trulia
fee lines, the community page text and the amenities page's sentence (the stored number there was "first dollar
figure"). New fields: `parking_fee_note`, `parking_options` (every price found), `parking_text`. Also mapped:
`special_offer`, `fee:*`, `fees_and_utilities`, `dog:monthly_dog_rent`, `optional_monthly_fee_items`, `building_type`,
`income_restricted`. The script prints the fact names still unmapped (building size, broker, dates: none feeds a gate).

**W5. Utilities.** `parsers.parse_utilities`, used in `all_in.py`. Included and tenant-paid lists are parsed
separately; tenant-paid wins. "All utilities" no longer removes the internet estimate. "Heat" no longer removes the
gas line (the gas estimate is cooking gas only).

**W6. Apartment List offers.** `rent_terms.py: read_apartmentlist` collects `specials` from every copy of the listing
object. Offers found: 518 → 874 of the units in `rent_terms.csv`. Of the 83 Apartment List units shown before, 9 had an
offer on file then and 51 do now.

**W7. Building coordinates.** `build_master.py: assign_building_ids, building_coords, census_address`;
`enrich_units.py` calls them, stores one coordinate per building (listing's own point kept in `lat_listing`,
`lon_listing`) and redoes any cached lookup made more than 150 m from it, deleting the matching `enriched_color` file.
Three buildings disagreed by more than 150 m and were geocoded with the Census geocoder (145 Goldsborough Dr, Bayonne;
55 Bank St, White Plains; 138-28 Queens Blvd, Jamaica: 1,023 m apart); 5 address keys were re-enriched. The Agnes now
sits at 40.7186, -74.0927 (its rows agree in the current data). Logged in `master_conflicts.csv` as field `lat_lon`.

**W8. Duplicates and three per building.** `build_master.py` (unit table) removes a second listing of the same unit
inside a building before selection and keeps its link in `also_seen_at`; `rank.py` caps at 2 on `building_id`.

**W9. Fee text.** `parsers.monthly_fees_from_text`, `parsers.fees_from_json`, used in `all_in.py`. Amounts without "$"
count; "no amenity fee" is a known $0; an amount over $400 with no monthly wording is not counted and is named in the
line's note; one-time charges, pet, parking and optional items are skipped; a stated total is not added to its own
breakdown; alternatives are never summed. Several sources' sentences are kept side by side and the largest reading is
used. A special that waives an amenity fee marks the fee line "exists, amount not published" (Hudson 44).

**W10. Income screening.** `parsers.income_restricted`, used in `rank.py`: only affordable-housing, lottery or
income-cap language excludes.

**W11. Letter-only ground-floor guess.** `gates.py`: only G, GR, LOBBY, BSMT read as ground. "B2", "C4", "L3" become
floor unknown. Listings failing on the floor gate alone: 1,269 → 804, on a larger listing set.

**W12. Shown before the evidence pass.** `rank.py`: shown requires live status `live` or `changed`. Clean candidates
without one go to `data/needs_live_check.csv` (93) and into `site/data.json` as `awaiting_live_check`, not as places.

**W13. Live price changes.** `all_in.py`: the live price is the rent, and rent-terms figures are re-based on it.

**W14. Pool and doorman tests.** `parsers.pool_state, doorman_state, virtual_doorman, amenity_yes`, used in `rank.py`.
The source text is kept in `pool_text` and `doorman_text`.

**W15. Pet rent.** `parsers.parse_pet_rent` returns the monthly figure. `parsers.money` reads "1500" as 1,500.

**W16. Dog weight.** `parsers.parse_dog_weight`: "no upper limit; dogs over 40 lb cost extra" is no limit. `rank.py`
scores a confirmed "no limit" as the best weight policy.

**W17. Confirmed floors that never land.** `parsers.parse_floor_confirm` and `parsers.units_match` ("5106" =
"005-5106"), used for floors, the live check and exclusions. Of 93 confirmed floor values, 25 match no unit in the
master (mostly units that have left the list) and 2 cannot be parsed; all 27 are in
`data/reference/floor_confirm_unmatched.csv`.

**W18. `avoid.py` regex.** Ground-floor exclusions now name the unit: 7000 Avalon Way → 5106, 1 Avalon Way → 1177
(one unit, not the whole building).

**W19. Avoid reasons.** `avoid.py`: counts distinct dated reports (one per source page and date), pooled per building;
elevator rows count only when the excerpt describes an outage; parking-price complaints are not management problems;
a year-only date no longer counts as inside six months. Mesa Verde and 20 Beacon Way lose the overstated reason and
stay avoid on the other; 1000 Pacific St stays avoid on its ratings verdict instead.

**W20. Conflicting dog policy.** `parsers.dog_conflict`, used in `build_master.py` and `avoid.py`. The building's own
or its manager's page wins (19 E 19th St, 100 Avenue G, Third & Valley → yes). Aggregator against aggregator is
`conflicting`: held with "Are dogs allowed?" (467 West Ave, 8 Norden Pl, 1455 Washington Blvd and others).

**Cosmetic.** `lines_known` now counts stated cost lines (`all_in_stated_line_count`); numeric values are compared as
numbers in `master_conflicts.csv`; the Mesa Verde exclusion reads "elevator not established: the sources conflict";
the `cm()` and `community_pool` shims are gone; ZIP codes keep their leading zero; "rent (net-effective)" appears only
where an offer changes the monthly figure.

## Per-unit mismatches

| Item | Result |
|---|---|
| A1 One City Place 204 | Parking $175 read from the listing sentence; all-in $3,123, over the cap |
| A2–A4 The Jefferson 462 | Parking $100 (first spot); utilities tenant-paid; "no amenity fee" = $0; all-in $3,142, over the cap |
| A5–A8 The Agnes | Coordinates, drive (40.1 min) and nearest park (Lincoln Park) now from the right point |
| A9 The Agnes name | **Left.** The name is the first listing row's; no source is clearly the better one |
| A10 Parkside 2307, A11 Harrison Yards H2-316 | Floor unknown; held |
| A12 The Brompton 7B | Elevator `inferred`; held |
| A13 The Botanic 444 rent | **Not fixable here**: needs a live check. It is no longer shown without one |
| A14 Regency on Hudson, A15 The Highlands | Parking read from the Trulia fee lines ($150; $100, the cheapest covered or garage option) |
| A16 The Edge at Raritan Heights 329 | Parking $0: one free surface spot |
| A17 Avalon Teaneck 001-215 | Fee $66 counted |
| A18–A25 special offers | Read from the cached page; asterisk and terms set |

## Left deliberately, or not possible

- Units are still pre-filtered by the old cost block in `enrich_units.py` (`unit_status`) before the master is built.
  The check did not list it and it is outside the named scripts' cost logic; worth a look.
- The "conflicting dog policy" rule on a listing's own `CONFLICT` note still excludes the unit as sketchy (approved in
  `docs/RANKING.md`); W20's softer rule was applied to evidence rows only.
- Avoid cards are not required to be clean on every gate fact, as before.
- Parking parse: one free-text description that mixes water, pet and parking prices reads $50 where $75 is right.
- Harvesters still do not write a basis column; `gates.py` reads the basis from their notes.
- The independent check should be re-run on a fresh sample (its own step 6).
