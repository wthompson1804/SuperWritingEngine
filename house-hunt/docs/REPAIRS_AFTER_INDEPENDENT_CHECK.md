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

Two owner decisions arrived during the repair (both described below): "small dogs" with no number passes the dog
gate, and a unit with exactly one thing still to confirm is shown with an asterisk instead of being held. The middle
column is the strict state after the W1–W20 repairs and the small-dogs rule, before the asterisk rule; the right column
is the final state on disk.

| | Before | Repairs, strict ("confirmed before shown") | Final (one open item shown with an asterisk) |
|---|---|---|---|
| Listings after dedupe | 18,290 | 20,464 | 20,464 |
| Listings failing the floor gate / on the floor gate alone | 1,612 / 1,269 | 1,076 / 804 | same |
| Units costed in the master | 1,524 | 2,020 (22 duplicate listings of a unit merged) | same |
| Units over the $3,000 all-in cap | 211 | 356 | 356 |
| Ranked | 961 | 1,185 | 1,185 |
| **Shown** | **207** | **120** | **324** (113 with nothing open, 211 with an asterisk) |
| Held for one confirmation, not shown | 200 | 317 | 189 |
| `needs_confirmation.csv` (phone-call list) | 200 | 317 | 323 (shown-with-asterisk units flagged) |
| Waiting for a live check, not shown (`needs_live_check.csv`) | did not exist; 26 shown without one | 93 | 190 (one open gate fact and no live check) |
| Avoid cards | 27 | 30 | 30 |
| Avoid buildings | 48 | 48 | 48 (three reasons reworded or removed, W19) |
| Neighborhoods with 3+ shown places | 26 | 13 | 36 |
| Rows in `master_conflicts.csv` | 212 | 53 | 53 |

Shown units by basis:

| Fact | Before (207) | Strict (120) | Final (324) |
|---|---|---|---|
| Floor: confirmed | 20 | 32 | 41 |
| Floor: stated on the page | 23 (17 really derived from the unit number) | 1 | 14 |
| Floor: inferred, accepted (simple label, floor 3+, "read from the unit number") | none marked; 164 inferred from any label | 87 | 166 |
| Floor: open, shown with an asterisk (unknown 84, inferred but not accepted 19) | 0 | 0 | 103 |
| Elevator: confirmed / amenities page / official record / stated | 182 / 14 / 6 / 5 | 112 / 2 / 6 / 0 | 218 / 65 / 11 / 1 |
| Elevator: inferred, shown with an asterisk | 0 (hidden as "stated") | 0 | 29 |
| Dogs allowed: confirmed / stated | 193 / 14 | 116 / 4 | 250 / 74 |
| Dogs conflicting between aggregators, asterisk | 0 | 0 | 2 |
| "Small dogs", no pound figure | 60, unmarked | 52, with note and tour question | 109, with note and tour question |
| Live check: live / changed / blocked / none | 179 / 2 / 5 / 21 | 119 / 1 / 0 / 0 | 242 / 5 / 3 / 74 (the 77 without one carry the asterisk) |
| Rent asterisk (special offer) | 52 | 45 | 140 |
| Most shown in one building | 3 | 2 | 2 |
| Highest all-in | 2,998 (understated) | 2,993 | 2,999 |

Of the 207 units shown before: 93 were still shown under the strict rule and 155 are shown in the final state (65 of
them with an asterisk). Of the rest, 14 are over the $3,000 cap once parking, fees and utilities are read correctly, 10
are no longer in the master (source row changed or gone), 3 were merged as duplicates, and the others have two open
items, wait for a live check, or fell outside the best 10 of their neighborhood.

## Owner's change during the repair: one open item is shown with an asterisk

This replaces "confirmed before shown" for the single-open-fact case. In `rank.py` (selection block):

- Open items are the three gate facts (elevator only inferred; floor unknown or inferred in a way the floor rule does
  not accept; dogs conflicting between aggregators) and a missing live check. A unit with **at most one** open item,
  not in an avoid building, enters the shown selection, ranked normally (0.97 certainty factor for an open gate fact).
- It carries `confirm_asterisk = yes`, `confirm_what` (elevator / floor / dogs allowed / live check) and `confirm_why`,
  one plain sentence. `build_page_data.py` exports them as `confirm {asterisk, what, why}` on every unit.
- Not shown: two or more open gate facts (sketchy), a gate failed on a confirmed or stated fact, sketchy listings,
  avoid buildings, and a unit with one open gate fact **and** no live check (it waits in `needs_live_check.csv`).
- `needs_confirmation.csv` is the phone-call list: every candidate with one open gate fact, with
  `shown_with_asterisk`, `confirm_what`, `confirm_why`.
- `check_registry.py` fails the run if a shown unit has more than one open item, has one without the three asterisk
  fields, or names the wrong fact in `confirm_what`.
- Wording: the coordinator's example for the floor read "ground-floor units are ruled out". The pipeline cannot
  establish that for a floor it does not know, so the sentence says only what is known ("The listing does not give
  the floor, and the unit number does not show it."). **84 shown units have an unknown floor; some may be on the
  ground floor.**

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
- `rank.py`: settled on floor only if confirmed or stated; an inferred floor ≥ 3 from a simple label is accepted with
  `floor_basis_note` and the tour question "Confirm the floor"; everything else is an open fact (held under the
  strict rule; shown with an asterisk under the owner's later rule if it is the unit's only open item).

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

**W12. Shown before the evidence pass.** `rank.py`: a live check means live status `live` or `changed`. Under the
owner's later rule a missing live check is one open item: a unit with nothing else open is shown with the asterisk
"live check" (77 units); a unit with an open gate fact as well goes to `data/needs_live_check.csv` (190) and into
`site/data.json` as `awaiting_live_check`, not as a place.

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
`conflicting`: an open fact with the question "Are dogs allowed?" (467 West Ave, 8 Norden Pl, 1455 Washington Blvd and others).

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
| A10 Parkside 2307, A11 Harrison Yards H2-316 | Floor unknown: an open fact (asterisk "floor" if nothing else is open) |
| A12 The Brompton 7B | Elevator `inferred`: an open fact |
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
- The stage label "shown (every gate fact confirmed or stated; ...)" in `run_all.py` / `RUN_REPORT.md` was kept so the
  run history still lines up; it now includes asterisked units (counted on the next row).
- Parking parse: one free-text description that mixes water, pet and parking prices reads $50 where $75 is right.
- Harvesters still do not write a basis column; `gates.py` reads the basis from their notes.
- The independent check should be re-run on a fresh sample (its own step 6).
