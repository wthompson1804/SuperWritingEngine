# Repairs after independent check 4 (pipeline side)

Written 2026-11-16. The check is `docs/INDEPENDENT_CHECK_4.md` (30 defects, D1 to D30). It measured the page of 568
apartments; the live re-read had since taken it to 542. Every item below was checked against the data as it stood at 542
before anything was changed. This file covers the pipeline: gates, merge, cost, ranking, verdicts and `site/data.json`.
The page template (`site/index.html`) and the written text (scene text, apartment and building lines) belong to two
other agents; what they have to do because of these changes is in the last two sections.

## Result

| | Before (after the live re-read) | After |
|---|---|---|
| Ranked | 692 | 664 |
| Shown apartments | 542 | **523** |
| Buildings | 209 | **202** |
| Neighborhoods | 78 | **77** |
| Shown with one open item | 207 | 218 |
| Not an apartment | 71 | 76 |
| Neighborhoods carried in the page data with nothing to show | 11, mixed in with the others | 11, in their own array |

By experience (apartments / buildings / neighborhoods):

| Experience | Before | After |
|---|---|---|
| Little-City | 232 / 81 / 23 | 217 / 80 / 23 |
| Room-to-Breathe | 153 / 39 / 23 | 154 / 38 / 23 |
| Old-Neighborhood | 73 / 56 / 21 | 72 / 55 / 21 |
| Fresh-Start | 75 / 27 / 6 | 71 / 23 / 5 |
| Quiet-Street | 6 / 3 / 3 | 6 / 3 / 3 |
| Walk-Everywhere | 3 / 3 / 2 | 3 / 3 / 2 |

Two consecutive full runs give an identical `data/ranked_units.csv` and `data/master_units.csv`. `check_registry.py`
passes. Tests: `test_rules.py` 617 pure checks (was 449), `test_rules.py --data` 4,170 with the page data, `test_parsers.py`
259. `verify_all.py`: 19 passed, 0 failed, 1 warning (the built page is older than the data: the page agent's step).
Every shown apartment has a current reviewed verdict.

## What left, what entered, what moved

**Left (26)**

| Apartments | Why |
|---|---|
| Residences at The Summit K3-02, K3-23, K4-19, L3-03, M2-07, M4-10, M4-12, M4-22 (Danbury) | D3. Two open facts: the listing page is stale, and the elevator is named only in a listing site's list for a complex of buildings K, L and M with no height on any page |
| The District at 15Fifteen 1-219, 1-234, 1-241, 1-243, 1-261, 1-413, 1-431, 1-440 (Parsippany) | The same elevator rule now applies (labels name buildings 1 and 2, the elevator is on a listing site only, no page gives a height), beside the eligibility question these already carried: two open facts |
| 328 Pacific 705, Metropolis Towers 16F, 509 Martin Luther King Jr Dr 39E (Jersey City) | D2. Dogs open, plus "a second site lists the address and not this apartment": two open facts |
| BE `P`, `F` (Orange); Appletree Suites `C`, `E`, `F` (Jersey City) | D4. One-letter labels beside numbered apartments are plan letters, not apartments |
| 630 West 163rd Street 10 | D4. Apartment 10 of 65 on six floors, numbered in sequence, reads as the first floor |
| Portside Towers 311 (Downtown Jersey City) | A consequence: with Metropolis Towers 16F gone, Downtown Jersey City is a single-apartment neighborhood and the thin rule cuts it |

**Entered (7)**

| Apartments | Why |
|---|---|
| The Grove Somerset 2141, 3172, 4149, 4171 (Franklin) | D22. Removed as "first floor" on a wrong reading of the number; they read as floors 2, 3, 4 and 4. Fresh verdicts written from the evidence (ok); the rules mark the elevator ("elevator access in select buildings") |
| The Grove Somerset 2205 | Franklin is no longer a single-apartment neighborhood, so the thin rule no longer cuts it |
| Appletree Suites 3A, 5A | Moved up inside the building when the plan letters left. Verdicts written from the evidence: ok |

**Moved**

| What | From | To |
|---|---|---|
| Harbor Pointe, 302 Constitution Ave (6 apartments) | "Elizabeth" (Little-City) | Bayonne (Room-to-Breathe) |
| Parkway Lofts, 5 Lawrence St (3 apartments) | East Orange (Room-to-Breathe) | Bloomfield (Little-City) |

Neighborhoods: **Elizabeth** left (it was only Harbor Pointe). **Downtown Jersey City** left (thin rule). **Franklin**
entered. No neighborhood changed experience.

**New asterisks on apartments that stay (28).** Elevator: Pier Village (8), The Brunswick (5), 1 Kennedy Flats (4),
Admirals Cove (4), Halstead Parsippany (2), The Confluence (1), Fort Hill Peekskill (1), Valley and Bloom (1).
Availability: 525 Riverdale Ave 5U (had none), 100 Prospect N311 (was "listing"; the stale page and the second site are
one doubt and count once).

## Buildings whose coordinates or municipality changed

Every building's point was compared with its own address. 14 of 578 lay outside the ZIP area of their address
(`data/reference/building_coord_check.csv`):

| Building | Result |
|---|---|
| Harbor Pointe, 302 Constitution Ave, Bayonne 07002 | **Re-geocoded.** Apartment List's point (40.6710, -74.1798) is 6.9 km away, in ZIP 07201, Elizabeth. Now 40.6726, -74.0982 (Census geocoder). Drive 44.8 min (was 50.4), Bayonne police figures, park 3 minutes away (was 34) |
| Parkway Lofts, 5 Lawrence St, Bloomfield 07003 | **Re-geocoded**, 168 m. The listing's point is across the line in ZIP 07017, East Orange |
| The Grand, 508 51st St, West New York 07093 | **Re-geocoded**, 248 m (the point was in North Bergen). Not shown |
| Reserve at Lakeside (55+), 7 Lakeside Rd, Newburgh 12550 | **Re-geocoded**, 1.8 km (the point was in Montgomery). Senior housing, not shown |
| Parc at Roxbury, 400 Cardinal Ct, Ledgewood 07852 | **Flagged.** The point is in ZIP 07857, Roxbury; the address could not be geocoded. Its one ranked apartment carries the open item "listing" and is not shown |
| One Ten at the Enclave, The Enclave (Jersey City), AVE Clifton, Arrive Stamford, Alto Fairfield Metro, Harrison Somerset, Strouse Adler, 92-27 160th St, 66 Saint Nicholas Pl, 255 Nostrand Ave | ZIP boundary: the address geocodes within 150 m of the point, or the point is in the municipality the address names. Kept |

Cause of D1: the merge took the coordinates of the gate-passing listing rows as given when they agreed with each other;
nothing compared them with the address. Fix: `build_master.check_coords_against_address` runs for every building in
`enrich_units.py`; lookups for a moved point are redone automatically (drive, transit, police agency, places, utilities).

`city` is now the municipality at the building's point (Census place, else county subdivision), not the city a listing
wrote. 34 buildings changed (`data/reference/municipality_changes.csv`). Shown ones: Avalon Maplewood (was "Newark"),
Third & Valley ("East Orange" → South Orange), Avalon Wayne ("Lincoln Park" → Wayne), RiversEdge at Port Imperial and
RiverParc ("West New York" → Weehawken), 55 Monroe Place ("Belleville" → Bloomfield), Valley and Bloom ("Upper Montclair"
→ Montclair), LIA by Vermella and 416 Highland Avenue ("Orange" → City of Orange), Spinnaker Wharf ("Milford city" →
Milford). For those the neighborhood, local rules and police agency already followed the geography; only the `city`
field was wrong. Parkway Lofts and Harbor Pointe were wrong in both.

## Neighborhoods with no published crime figure

**Beacon Falls, Connecticut** (5 apartments shown, Beacon Mill Village). It is the only shown neighborhood without a
violent or a property rate. Looked: `data/reference/crime_agencies.csv`, `crime_place_agency.csv`, the cached FBI agency
list for Connecticut (108 agencies). No municipal police department is listed for Beacon Falls. The covering agency is
the Connecticut State Police, which appears in the FBI list as one statewide agency (`CTCSP0000`) and reports one total,
not a figure for the town. No figure can be sourced from what the project uses, so none is guessed. The neighborhood is
kept with `safety.status = "not_published"` and a plain `status_note`. **For the owner:** the safety rule could not be
tested there. (Connecticut's own annual crime report may list the town; it is not a source of this project and was not
fetched.) Not shown, same situation: Oxford CT, LaGrange NY, New Paltz NY.

## Per defect

| # | Status | What was done |
|---|---|---|
| D1 | **Fixed** | Coordinates checked against the address for every building (above). Harbor Pointe is in Bayonne. Tests: `parsers.coord_check`, the check with a stub geocoder, and on the output |
| D2 | **Fixed** | `parsers.second_site_omits`: "a second site lists the address and not this apartment", on a listing that could not be read again, is the open item "availability" wherever a checker recorded it. Three apartments left (two open facts); 525 Riverdale Ave 5U carries the asterisk. Every ranked apartment with the finding now carries it (7, all shown with the asterisk: Bedford Creative 204, 205, 301, The Tetris 211, 309, 100 Prospect N311, 525 Riverdale Ave 5U) |
| D3 | **Fixed** | `parsers.multi_building_labels`: a label that names its building (`K3-02`) counts whatever floor it reads as. The rule asks for a height on a page or record, as CLAUDE.md states it. Residences at The Summit: two open facts, not shown |
| D4 | **Fixed** | `parsers.plan_letter_label` (BE, Appletree Suites: five rows are `not_an_apartment`); `parsers.sequential_number_reads_ground` (630 West 163rd Street 10 removed). A single letter with no numbered sibling stays (1483 Shore Pkwy F, 3440 Guider Ave Z) |
| D5 | Page agent | Template lines. The data it needs is there: `confirm.what`, `confirm.label` |
| D6 | Text agent | Data added to help: `neighborhoods[].shown_figures.buildings_with_own_dog_area` |
| D7 | Text agent | See D14 |
| D8 | **Fixed** | `parsers.renter_conditions` over every evidence fact and checker's note. Disclosures: income requirement (9 apartments: 8267 Austin St 916, 948 New York Avenue 2, City Line East 7), credit-score requirement (3: 948 New York Avenue 2, 3310 Nostrand Ave 503, 3280-3310 Nostrand Ave 202), furnished apartment (11: Appletree Suites 7, Metrovue 3, 142-38 37th Ave 8E). All statements with income, credit, furnished, short-term, sublet, student, corporate in the evidence of shown buildings were read (28 buildings); deposit terms that depend on a credit score, a credit check fee and a "furnished roof deck" are not conditions. Nothing among the shown apartments says short-term, corporate or student-only; where it would, it is the open fact "eligibility" |
| D9 | **Fixed (data)** | `amenities.doorman`, `amenities.concierge`, `amenities.front_desk`, each only from a source that says so. Shown: doorman 19, concierge 179, front desk 3 (before: "doorman" on 191 apartments, most of them from a source that says only concierge). The score still counts a staffed front of any kind. The wording is the text agent's |
| D10 | **Fixed as far as the sources go** | No figure exists in the project's sources; `safety.status = "not_published"` (above) |
| D11, D12, D13 | Text / page agent | No pipeline change |
| D14 | **Checked, nothing moved** | See the next section |
| D15 | Text agent, partly here | The pipeline's own reader text now has a guard over the published data (`test_rules.py --data`, D24) |
| D16 | Text agent | Data added: `neighborhoods[].shown_figures` (medians over the shown apartments) beside `traits` (the area profile) |
| D17 | **Fixed** | `city` from geography (above). Parkway Lofts is in Bloomfield, with Bloomfield's parking rule and police figures |
| D18 | **Fixed** | Basis `resident_review` (below every page that states the fact). The Atwater's $75 now rests on Apartment List's fee line ("Unassigned and/or Reserved Parking Fee $75"), which states it; the review is no longer the source. `parking.fee_basis`, `parking.kinds`, `parking.garage_is_optional_extra` (J Centra Burlington: a lot with optional garages; 56 apartments in 24 buildings name a lot with a covered or garage space as an extra). The option name no longer carries the source or a date cut short |
| D19 | **Fixed** | Building floors = the largest stated count, never below a stated apartment floor. Continuum: 17 (was 2) |
| D20 | **Fixed (data)** | `rent.offer_up_to`, `rent.free_text` ("up to 2 months"), and the special-offer disclosure says "up to". 120 shown apartments carry an "up to" or a range offer |
| D21 | **Fixed** | `neighborhoods` holds only places with a shown apartment (77); `neighborhoods_avoid_only` holds the 11 others. Experience counts and `hood_ids` list shown neighborhoods only |
| D22 | **Fixed** | `data/reference/unit_numbering_conventions.csv` (16 complexes, each with how the convention was established). All 88 "reads as first floor" removals in 27 buildings were re-read against their complex's convention: 83 hold, 5 were wrong (The Grove Somerset 2141, 3172, 4149, 4171; Prospect Place 01-16C, which is over the cost cap anyway). No shown apartment reads as ground floor under its complex's convention |
| D23 | Not a defect in the rule | The thin rule recomputes. The Lofts at Garwood was cut because its experience's median rose: the rule as written. CLAUDE.md's wording ("seen live") is the owner's file |
| D24 | **Fixed** | Reader text from templates (below) |
| D25 | Partly | Pipeline side fixed: "Milford city (balance)" is Milford; "416 Highland Ave - 312" with the label "1 Bed" is apartment 312 with no building name. The sentences are the page and text agents' |
| D26, D27, D28 | Page / text agent | No pipeline change |
| D29 | Not fixed here | Ratings come from `scripts/page_data_extras.py` and its inputs (not this pass's files) |
| D30 | **Fixed** | Pier Village, The Brunswick and Fort Hill Peekskill are caught by the rule (labels name their buildings). 1 Kennedy Flats, Admirals Cove, Halstead Parsippany and The Confluence (bare four-digit labels that read as two to four buildings) were added to `data/reference/elevator_doubt.csv`. Prospect Place is left: two towers (`01-16C` is floor 16), where the doubt "which building has the elevator" does not arise |

**The lease-term gap.** The disclosure now covers any listed price quoted for a lease that is not 12 months with no
12-month price read: 129 apartments (was 101), among them the 19 priced on exactly 13 months. Text: "The price shown is
for a 13-month lease: ask for the 12-month price."

## D14: experiences

`data/reference/experience_fit_review.csv` lists all 88 places (77 shown, 11 avoid-card-only) with the assigned
experience, the nearest and second-nearest group and the ratio, from `data/lifestyle_group_distances.csv`.

**No neighborhood was moved.** Every shown neighborhood already sits in the group its frozen area profile is nearest
to. None is nearer another group, so the test "clearly wrong on its own features" has no case. Twelve are boundary cases
(second group within 10 percent) and are left: Norwalk, Danbury, Yonkers, Patchogue, Peekskill, Journal Square, Madison,
Bridgeport, Brookfield, and the avoid-only Kew Gardens Hills, Windsor Terrace and McGinley Square (the last by a reviewed
override, the owner's to decide).

Why the misfits the check names still read as misfits: the group comes from the neighborhood's area profile (the
largest building sample on record and the Census tracts around it), not from the one building shown today. Fairfield's
profile has 62 percent detached houses and 1 percent of households without a car, which is Quiet-Street (ratio 0.82
against Room-to-Breathe); the one apartment shown is beside the station with 8 restaurants within 800 m. Englewood's
shown building has no restaurant within 800 m; its profile is Little-City (0.76). These are for the text (describe the
shown buildings: `shown_figures`) or for a refit, which is the owner's decision. Kew Gardens Hills no longer has a page
as a neighborhood (D21).

## D24: how the reader text is made

`scripts/build_page_data.py` writes, from a reason code and structured fields:

- `confirm.what` (the stable key: elevator, dogs allowed, availability, listing, eligibility), `confirm.label`,
  `confirm.why`, `confirm.question`, `confirm.code`; the working note is in `confirm.why_internal`;
- each disclosure's `what` (stable key), `label`, `why`, `question`, `code`, and `why_internal`;
- each cost line's `line` (unchanged), `label`, `note`, `code`, and `note_internal`;
- every tour question;
- `evidence.avoid_points` and `evidence.pause_points` (plain sentences beside the old `avoid_reasons`, `pause_notes`).

A reviewer's sentence from the verdict table is used in place of a template only when it passes the same check after
"unit" is written as "apartment" and ISO dates are written out. 28 verdict sentences were reworded in
`data/evidence/review_verdicts.csv` so their detail survives (the Regency on Hudson occupancy-permit note without the
file path; "the site then refused us"; "the checker's note"; "re-read"). Verdicts themselves are unchanged.

Examples, before and after:

| Before | After |
|---|---|
| "The evidence pass could not confirm an elevator for this building: not stated on the building site or Apartment List (Zumper harvest row says elevator yes) \|" | "A listing names an elevator, but no page of the building's own confirms it." |
| "A Google review (seen in a search summary, docs/PENDING_FIXES.md) claims units here were advertised with no occupancy permit. Second-hand, so one open fact" | "A Google review, seen only in a search summary, claims apartments here were advertised with no occupancy permit. That is second-hand and not confirmed: ask to see the building's certificate of occupancy." |
| "Parking: confirmed; cheapest of the prices listed; prices listed: reserved $95; regular (first come) , per a resident review dated 2025-05-0 $75" | "The lowest of the published prices ($75 to $95)." Where a fee does come from a review: "From a resident's review dated May 1, 2025, not from the building: an estimate." |
| "Is this unit still available, and at this price?" | "Is this apartment still available, and at this price?" |
| "The listing may be stale: the listing page was last changed on 2026-08-22, 86 days before it was read (2026-11-16), and no second site lists the unit." | "The listing page was last changed on August 22, 2026, 86 days before we read it, and no second site lists this apartment." |

The test (`test_rules.py --data`, `page_ic4`) walks every string of `site/data.json` that the pipeline writes for the
reader and fails on "unit", "evidence pass", "harvest", "batch", a file path, "docs/", ".csv", "verdict", "gate",
"pipeline" or a date cut short. Exempt, by key: ids and enums, names and addresses, links, other people's words quoted
verbatim (resident quotes, a listing's own offer text, the wording of a local rule), raw source sentences kept for
reference, the `*_internal` fields, and the fields `scripts/page_data_extras.py` owns. The template-written fields also
pass a stricter list (no field names, no "checker", "live check", "re-read", status codes).

## What the page agent must do

1. **Neighborhoods.** Read `neighborhoods` (77) for everything that counts or lists neighborhoods, map chips included.
   Avoid cards of places with nothing to show are in `neighborhoods_avoid_only` (11): list the card, give the place no
   neighborhood page, no experience header, no count. `meta.counts.neighborhoods` and `neighborhoods_avoid_only` hold
   the two numbers.
2. **Safety.** Where `neighborhoods[].safety.status == "not_published"` (Beacon Falls), print `safety.status_note`
   behind "See how we got this", and do not print "among the safest" or any figure for it.
3. **Asterisk and disclosures.** Print `confirm.label`, `confirm.why`, `confirm.question` and each disclosure's
   `label`, `why`, `question` as they are. Never print `why_internal` or `note_internal`. `what` values are unchanged
   keys. New disclosure keys: `income requirement`, `credit score requirement`, `furnished apartment`.
   The disclosure label for `net-effective rent` is "average rent after free months"; for `lease term`, "lease length".
4. **Receipt.** `all_in_lines[].note` is now a reader sentence (or null); `line` is unchanged, `label` is the name to
   print (`rent (net-effective)` → "rent (average after free months)"). A fee read from a review is the line
   `parking (est.)` with basis `estimate`.
5. **Amenities.** `amenities.doorman` is now only a real doorman. Use `amenities.concierge` and `amenities.front_desk`
   for the others; "the building row" must not say doorman for a concierge. `moments.night` carries all three.
6. **Building.** `buildings[].city` is the municipality; `postal_city` (may be null) is the city the listing wrote.
   `amenities.building_floors_at_least` true means "at least N floors". `manager_name` is the name to print; `manager`
   is the note that says where it was read. A building may have `name: null` (416 Highland Avenue).
7. **Offers.** Use `rent.free_text` ("up to 2 months") and `rent.offer_up_to`; do not rebuild the phrase from
   `rent.free_months`.
8. **Worth knowing / avoid reasons.** `evidence.pause_points` and `evidence.avoid_points` are plain sentences; prefer
   them to `pause_notes` / `avoid_reasons`.
9. **Floor.** `floor_basis_note` now reads "read from the apartment number".
10. D5, D13, D25 to D28 as the check describes them.

## What the text agent must do

1. **Rebuild the text for 523 apartments in 202 buildings and 77 neighborhoods.** Ids that entered: The Grove Somerset
   2141, 2205, 3172, 4149, 4171; Appletree Suites 3A, 5A. 26 ids left (list above).
2. **Neighborhoods to rewrite:**
   - **Bayonne**: now also holds Harbor Pointe (6 apartments, by the water, Room-to-Breathe).
   - **Bloomfield**: now also holds Parkway Lofts (3 apartments).
   - **East Orange**: lost Parkway Lofts; two apartments in one building remain.
   - **Franklin** (The Grove Somerset, 5 apartments): new on the page; it needs scene text.
   - **Elizabeth** and **Downtown Jersey City**: gone; their text must not be published.
   - **Danbury** (lost Residences at The Summit), **Parsippany-Troy Hills** (lost The District at 15Fifteen),
     **Journal Square**, **City of Orange**, **Bergen-Lafayette**, **Washington Heights (South)**: apartment lists
     changed.
   - No neighborhood changed experience.
3. **Doorman and concierge (D9).** Write "doorman" only where `amenities.doorman` is set (19 apartments), "concierge"
   where `amenities.concierge` is set (179), "front desk" or "attended lobby" where `amenities.front_desk` is set (3).
4. **Dog parks (D6).** `neighborhoods[].shown_figures.buildings_with_own_dog_area` against `shown_figures.buildings`.
5. **Figures in neighborhood text (D16).** `shown_figures` holds the medians over the shown apartments.
6. **Offers (D20).** Use `rent.free_text` and `rent.offer_up_to`.
7. **Parking (D18).** `parking.kinds` and `parking.garage_is_optional_extra`: "a lot, with a garage as an optional
   extra", not "garage parking"; `parking.fee_basis` says whether a fee is published or an estimate from a review.
8. **New conditions to mention where useful:** `conditions.income_requirement`, `conditions.credit_score_requirement`,
   `conditions.furnished`.
9. **Beacon Falls**: no crime figure is published; no safety wording for it.
10. Building floors: `amenities.building_floors_at_least`.

## Left for the owner

- Beacon Falls: shown with no crime figure (5 apartments). Keep it, or drop it until a figure is found.
- The four experience overrides are still the owner's to decide; one of them (McGinley Square) is avoid-card-only.
- CLAUDE.md's thin-rule sentence still says "seen live".
- Four complexes were added to the elevator doubt table on the check's reading (D30). If the owner knows them to be
  elevator buildings, a phone answer settles each.
- Metropolis Towers 16F is off the page; whether the building is a co-op was never read.
