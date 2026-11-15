# Independent check of the master tables (plan v4, Part 8)

Checked 2026-11-15, 21:20–22:10 UTC, by an agent that did not write the pipeline. Nothing in the pipeline was
changed. Raw comparisons: `data/evidence/independent_check_units.csv` (780 rows). Live pages fetched for this check
are cached in `raw/independent_check/` (29 listing pages, 28 Census geocoder calls, 14 NYC Open Data polygon lookups).

**Verdict: the shown list should not go to Will as it stands.** Listed rent, beds, sq ft, unit, address and
availability are faithful to the source pages. The gate facts and the all-in cost are not: several defects below
each put units on the shown list that fail a gate, or show an all-in figure that is too low.

The pipeline was re-run while this check was in progress (commit `7c10bf6`, 21:56). The 30 sampled units were still
shown afterwards and their checked fields were unchanged; counts below were taken from the files as of 21:56.

## Part A. 30-unit truth check

Sample: 30 of the 207 rows with `shown = True` in `data/ranked_units.csv`, stratified by `group_label`
(8 Little-City, 7 Old-Neighborhood, 6 Room-to-Breathe, 4 Fresh-Start, 3 Quiet-Street, 2 Walk-Everywhere), drawn
with `numpy.random.RandomState(20261115)` from rows sorted by `listing_id`. Sources: 17 Trulia, 11 Apartment List,
1 Zumper, 1 Zillow. The Zillow unit (Lagrange Farms, Poughkeepsie) could not be checked: Zillow listing pages are
off limits. robots.txt for trulia.com, apartmentlist.com and zumper.com was read first (no group names Claude; the
paths used are allowed); requests were spaced 2.5 s per host; no bot wall was met.

### Summary

| Field | Checked | Match | Mismatch | Page does not say | Not checkable |
|---|---|---|---|---|---|
| Listed rent | 30 | 28 | 1 | 0 | 1 |
| Special offer and rent basis | 30 | 21 | 8 | 0 | 1 |
| Availability date | 30 | 29 | 0 | 0 | 1 |
| Beds | 30 | 29 | 0 | 0 | 1 |
| Sq ft | 30 | 22 | 0 | 7 | 1 |
| Unit | 30 | 29 | 0 | 0 | 1 |
| Unit floor | 30 | 0 | 2 | 27 | 1 |
| Elevator (and basis) | 30 | 26 | 1 | 2 | 1 |
| Dogs allowed | 30 | 29 | 0 | 0 | 1 |
| Dog weight limit | 30 | 5 | 0 | 24 | 1 |
| Pet rent | 30 | 7 | 0 | 22 | 1 |
| Parking type | 30 | 17 | 0 | 12 | 1 |
| Parking fee | 30 | 5 | 5 | 19 | 1 |
| Required fees and all-in lines | 30 | 8 | 2 | 19 | 1 |
| Utilities included | 30 | 6 | 1 | 22 | 1 |
| Pool | 30 | 15 | 0 | 14 | 1 |
| Doorman | 30 | 7 | 0 | 22 | 1 |
| Year built | 30 | 8 | 0 | 21 | 1 |
| Building name | 30 | 20 | 1 | 8 | 1 |
| Address | 30 | 29 | 0 | 0 | 1 |
| Lat/lon | 30 | 28 | 1 | 0 | 1 |
| Drive time (plausibility) | 30 | 29 | 1 | 0 | 0 |
| Transit time (plausibility) | 30 | 26 | 1 | 0 | 3 |
| Park walk (plausibility) | 30 | 29 | 1 | 0 | 0 |
| Neighborhood | 30 | 30 | 0 | 0 | 0 |
| Police agency | 30 | 29 | 0 | 0 | 1 |
| **Total** | **780** | **511** | **25** | **219** | **25** |

How to read it: "match" means the page states what the master holds. "Page does not say" is not a pass. For unit
floor it means the master number is a guess from the unit label (27 of 29 checkable units); for dog weight limit it
includes 8 units whose page says "small dogs" with no number.

16 of the 29 checkable units carry at least one mismatch. The plan's own verification line ("the independent
agent's 30-unit check finds no field that disagrees with its source") is not met.

### Every mismatch

Severity: **S** changes what is shown, **N** changes a number on the page, **C** cosmetic.

| # | Unit | Field | Master | Page says | Sev. | Cause |
|---|---|---|---|---|---|---|
| A1 | One City Place 204, White Plains (`trulia:b2751108472:Unit_204:449015099`) | parking fee | blank, all-in parking $0, all-in $2,948 | "Garage Parking: $175 parking fee" | **S** (all-in $3,123) | Trulia fee line never parsed into `parking_fee` |
| A2 | The Jefferson 462, Hackensack (`trulia:b2751899081:Unit_462:466228717`) | parking fee | blank, $0 | "Parking Policy: Up to 3 spots: 1st $100, 2nd $75, 3rd $200" | **S** | W4 (fact `parking` unmapped) |
| A3 | same | utilities | text "gas/electric and water/sewer paid by resident"; lines "electricity (included in rent) $0", "gas (included in rent) $0" | resident pays | **S** (all-in $2,965 becomes about $3,145 with A2) | W5 |
| A4 | same | fee note | "no amenity fee" → note "fee exists, amount not published" | no amenity fee | C | W9 |
| A5 | The Agnes 203, Jersey City (`trulia:b2748217177:Unit_203:351142317`) | lat/lon | 40.7147972, -74.0362844 | page 40.718608, -74.092653; Census geocoder agrees with the page; master is 4.6 km east | **N** | W7 |
| A6–A8 | same | drive, transit, park walk | 35.8 min; 64 min; "Morris Canal Peninsula Park" 5.2 min | computed from the wrong point; that park is downtown | **N** | W7 |
| A9 | same | building name | "The Agnes Co-Living" | "The Agnes" | C | name from the Apartment List row |
| A10 | Parkside at the Harbors 2307, Haverstraw (`trulia:b1002377678:Unit_2307:2079744089`) | unit floor | 23 | no floor on page; evidence pass wrote "3 (inferred from unit number 2307)"; low-rise | **N** | W1 |
| A11 | Harrison Yards H2-316 (`apartmentlist:p54243080-58-198`) | unit floor | 23 | label is building H2, unit 316 | **N** | W1 |
| A12 | The Brompton 7B, Larchmont (`trulia:b2739683824:Unit_7B:2098486382`) | elevator | yes, basis "stated" | no elevator line on the page; harvest note "elevator: 6+ floors (unit numbers reach floor 7)"; evidence pass "unconfirmed"; harvest note also says "BUILDING_FAILS: small dogs only" | **S** | W3, W2 |
| A13 | The Botanic 444, Carteret (`apartmentlist:p63921201-1A-444`) | listed rent | 2,134 | base price 2,142 (total 2,240) | N | not live-checked |
| A14 | Regency on Hudson 313, Yonkers | parking fee | blank, $0 | "Covered parking fee ($150)" | N | as A1 |
| A15 | The Highlands 1200, Morris Plains | parking fee | blank, $0 | covered $135, garage $100, surface $85 | N | W4 |
| A16 | The Edge at Raritan Heights 329 | parking fee | $50 | "1 free surface spot per 1-bedroom ... Additional spots available at $50/mo" | N (all-in $50 too high) | fee taken from the first dollar figure in the sentence |
| A17 | Avalon Teaneck 001-215 | required fees | text "Technology Connect: 66"; all-in fee line $0 "unknown" | (own-site figure) | N (all-in $66 too low) | W9 |
| A18–A25 | Halstead Parsippany 2182; The Botanic 444; Harrison Yards H2-316; The Wyldes 439; Avalon Teaneck 001-215; 1177 Greens Farms 231; The Brick of Hackensack 0718; The Landings at Port Imperial 1109 | special offer | empty; `rent_listed_price_is = gross`, `rent_needs_call = no`, computed_how "no concession language on the listing" | "Up to 3 Months FREE + 1 Year Free Parking"; "$2,000 off your second month's rent"; "Up to 1 Month Free on base rent"; "Up to 1 months FREE base rent"; "Apply by 11-30 for 1 month off"; "1 Month free when moving in before the end of 2026"; "$500 Look and lease" (free month is 2-bed only); "$1,000 Security Deposit Special" | **N** (asterisk, gross/net, first-payment date; last two cosmetic) | W6 |

Other things seen in the sample, not counted as mismatches:

- **Small dogs, no number.** 8 sampled units (2165 Clarendon Rd 2E, 1634 Flatbush Ave 667, 61-57 84th St 3C,
  2920 Brighton 4th St 4CD, 143-25 84th Ave 3J, 83-83 118th St 3F, The Brompton 7B, and 4545 46th St 5F which does
  state "25lbs max") have a pet card reading "Dogs: Allowed, Size allowed: Small". See W2.
- **Floors that look wrong but cannot be proved from the page:** Halstead Parsippany 2182 → 21, The Highlands 1200
  → 12 (evidence pass: "unit 1200: unknown"), Cobalt Lofts 1147 → 11, The Landings 1109 → 11. See W1.
- **Hudson 44, unit 1013:** the page's special ("waived amenity fee for 12 months on select units") shows a monthly
  amenity fee exists; the all-in fee line is $0 with an empty note.
- **Parking fee choice.** Where a page gives several prices the master takes one without saying which: Halstead
  ($100 of $100/$150/$175), Cobalt Lofts ($175 of $150/$175/$225), Harrison Yards ($250 covered, not $225 surface).
- **Label.** 19 sampled units with no offer at all show the rent line as "rent (net-effective)", basis "computed
  from stated terms" (`all_in.py:76`: any rent-terms row sets it). Cosmetic, but it reads as if a concession exists.
- **ZIP codes** for New Jersey and Connecticut lose the leading zero (`zip5 = 7601`). Cosmetic.
- NYC precinct and neighborhood were right for all 7 NYC units (checked against the city's precinct and NTA
  polygons). Drive times are consistent with straight-line distance for all 30 (route/straight 1.13–1.58).
- Lagrange Farms (Poughkeepsie) and both New Paltz units have no police agency and no crime figures, and pass the
  Jamaica safety gate by default.

## Part B. Wiring defects

Counts are across all 207 shown units unless stated.

### Changes what is shown

**W1. Unit floor guessed from the unit label is treated as a confirmed gate fact.**
`rank.py:138` flags only `unit_floor_basis` "unknown" or blank, so "inferred" passes as clean. 164 of 207 shown
units have an inferred floor, and 17 of the 23 "stated" ones carry the harvest note "floor derived from unit
number" (the Trulia harvester wrote its guess into `floor`; `build_master.py:338` then labels it stated). Only 20
shown units have a confirmed floor. The guess is `gates.py:55` (`^[a-z]?(\d{3,4})[a-z]?$` → drop the last two
digits) after `norm_unit` strips punctuation, so:
- "H2-316" → 23, "158-2L" → 15, "5-204" → 52, "3-117" → 31, "1-219" → 12, "9114" → 91, "7012" → 70 in a 13-floor
  building, "3203" → 32 in a 3-floor building, "2204" → 22 in a 14-floor building.
- 43 shown units have a floor inferred from a 4-digit-or-longer label; 39 of them show floor 10 or higher.
- Building-floor-unit numbering is real in this data: at Avalon Boonton the building's own site gives unit 1177 as
  floor 1 (`confirm` row "unit 1177: 1"), while the master says 11 for 1177 and 1119, 21 for 2154 and 2182.
  By the same pattern these shown units may be on the ground floor: Royce at Trumbull 9114, Reserve at Riverdale
  3-117, Halstead Parsippany 1103, Cobalt Lofts 1147, Steel Works 1142 and 1119, Woodmont West 1109, The Landings
  1109, The Atwater 2106.
- Fix: treat `inferred` floor as an open gate fact (plan Part 5), never infer from labels longer than three
  characters or containing a separator, cap at `building_floors`, and carry the harvester's "derived" note into the basis.

**W2. "Small dogs" with no weight number is shown as clean.**
`rank.py:139` drops the small-dog question whenever `dogs_allowed_basis = confirmed`. The evidence pass confirms
"dogs allowed" on almost every building (193 of 207 shown), including rows whose value is "yes (small dogs)" and
whose weight-limit row is "unconfirmed". Result: 60 shown units (28 Queens, 17 Brooklyn; 44 in The Old-Neighborhood
Year) have a small-dogs-only policy and no weight limit. Three carry the harvester's own "BUILDING_FAILS: small
dogs only" note (The Brompton 7B; `trulia:b2739941135:Unit_304`, Peekskill; `trulia:b2785857715:Unit_705`, Port
Chester). Three buildings whose weight-limit row is "contradicts: small dogs only, large dogs not permitted" (127
Talmage Ave, 110 Washington St, 691 Anderson Ave) are not excluded either (`avoid.py:64` needs a number); 110
Washington has 2 units shown. Fix: key the question on the weight-limit confirmation, not on dogs-allowed.

**W3. A harvester's inference becomes "stated".**
`gates.py:108` labels any `elevator = yes` in a listing row "stated". 5 shown units have the harvest note "elevator:
6+ floors" yet basis stated or confirmed. 18 shown units are in buildings where the evidence pass could not confirm
an elevator (3 stated, 8 amenities page, 6 PLUTO class, 1 confirmed), for example The Brompton and 42 Broad St W,
Mount Vernon. Fix: harvesters write the basis in a column; `gates.py` reads it.

**W4. Evidence fact `parking` is never mapped (211 rows, 68 with a dollar amount).**
`build_master.py:226` maps `parking_fee`, `parking_type` and `garage`; the evidence agents mostly wrote the fact as
`parking`. Also unmapped: `special_offer` (29), `fee:monthlyrequiredfees`, `fees_and_utilities`,
`dog:monthly_dog_rent`, `optional_monthly_fee_items`, `building_type` (919 of 2,213 fact rows match no prefix).
The parking line is "unknown = $0" for 174 of 207 shown units; 22 of those have a fee on file. Adding the cheapest
stated option puts 7 over $3,000: One DeKalb 307 (3,148), Skylar Lofts JC 418 (3,117), Hudson Park 306F and 606F
(3,062), 19 Rock 505 (3,052), The Jefferson 462 (3,040), Skyline New Rochelle 02A (3,003). One City Place 204
(A1) is an eighth. Fix: map `parking`, take the cheapest monthly figure, keep the text.

**W5. "Utilities included" matches text that says the tenant pays.**
`all_in.py:122-125` searches the field for `electric`, `gas`, `heat`, `all utilities`. The field holds sentences
such as "gas/electric and water/sewer paid by resident", "resident pays electric, gas, trash, water, sewer",
"tenant pays electricity and cooking gas", "all utilities except cooking gas and electricity". 13 ranked units, 1
shown (The Jefferson 462); plus 44-10 Ketcham St (`trulia:79738215`, shown), where "all utilities except cooking
gas and electricity" zeroes electricity, gas and internet. "Heat and hot water" also zeroes the whole gas estimate.
Fix: parse included and tenant-paid lists separately; never match inside "pays", "paid by", "except", "=Resident".

**W8. The same unit shown twice, and three units from one building.**
479 Front St 2F, Hempstead, is shown as `apartmentlist:p6296923-2F` and `zumper-65691353` (same rent, sq ft).
The Zumper `addr_key` contains the unit and city, so `gates.py:148` does not dedupe it, and `rank.py:281` counts
"2 per building" by `addr_key`, not `building_id`. With unit 2A, building `b_b19425751b` has 3 shown. Fix: dedupe
and cap on `building_id` + normalized unit.

**W10. Ordinary income screening is treated as income-restricted housing.**
`rank.py:120` drops any unit with a non-empty `income_requirement`. The three units dropped say "40x rent and 700+
credit" (948 New York Ave #2), "3x the rent in household income" (2925 W 5th St 7A) and "$130,000 a year" (8267
Austin St 916). None is an income-restricted unit. Fix: drop only on a maximum-income or lottery statement.

**W11. Ground-floor guess from a letter drops listings at the first gate.**
`gates.py:50` reads "B2", "C4", "B10", "L3" as basement or lobby level. 1,269 listings fail on the floor gate alone;
198 of them only because the unit label is B, L or C plus digits (170 from Trulia), where the letter is more often
a line or building. Fix: fail only on G, GR, LOBBY, BSMT; send the rest to "floor unknown".

**W12. Shown before the evidence pass.** 21 shown units have no live check (`evidence_checked = False`), and 5 are
"blocked". `RANKING.md` says the best 10 that survive the evidence pass are shown.

### Changes a number on the page

**W6. Apartment List special offers are still lost.**
`rent_terms.py:152-164` reads `specials` from the longest copy of the listing object, which is the copy whose
`specials` is always empty (the harvester's own comment at `h_apartmentlist.py:245` explains this). 228 ranked
Apartment List units, 46 of them shown (65 buildings), have a special in their cached page while `rent_terms.csv`
says `offer_type = none`, "no concession language", confidence "stated_on_page", needs_call "no". Examples: 75
Tresser ("up to 6 weeks free"), Summer House ("2 months free"), The Walcott ("up to 2 months free + free parking"),
Stella, The Leaf, Alexander Crossing ("up to 1.5 months free"). Fix: collect specials from every copy, as
`parse_listing` does.

**W7. A building takes the coordinates and all lookups of its first listing row.**
`build_master.py:256` (`drop_duplicates("building_id")`) copies lat/lon, drive, tolls, transit, crime, parks and
places from one row. 36 units differ from their own row by more than 50 m, 9 by more than 500 m. The Agnes (2
shown units) sits 4.6 km from its address. Fix: prefer the geocoded address or the own-site coordinate; flag
disagreement over 100 m in `master_conflicts.csv`.

**W9. Fee text parser.** `all_in.py:44` sums only amounts written with "$": "Technology Connect: 66", "Community
Lifestyle Fee: 75", "Trash Services - Hauling: 15" count as nothing. `all_in.py:49` reports "fee exists" for any
text containing "fee", including "no amenity fee". Amounts over $400 are skipped silently.

**W13. Live price changes are not applied when a rent-terms row exists.** `all_in.py:70-74`: `net` from
`rent_terms.csv` (built on the old price) wins over the live price. 4 of 6 "changed" units keep the old rent, 2
shown (`apartmentlist:p11856-A6X-2318` 2,626 vs 2,634; The Botanic 430 2,169 vs 2,178).

**W14. Pool and doorman "has" tests accept negatives and near-misses.** `rank.py:179` excludes only the exact
words "no" and "none". Counted as a pool (+3 rank points, and presumably a pool on the page): "Pool table" (28
ranked units, 2 shown), "none listed" and "none listed (own site amenities, Trulia)" (5 ranked, 3 shown), "none
listed (pool table only)" (4), "see quote" (2). Counted as a doorman: "live-in super; no doorman stated" (1 shown),
"none listed; Trulia lists 'Night Patrol'" (2 shown), "virtual doorman" (3 shown). The indoor test itself now
behaves: only "indoor, with hot tub" and "... and indoor saltwater" classify as indoor.

**W15. Pet rent takes the first number.** `money()` (`build_master.py:65`) on "one-time $500 per pet; $50 per pet
monthly" gives 500 and on "$350 one-time; pet rent $40 or $50" gives 350. The George New Brunswick and Parc at
Roxbury hold `pet_rent_monthly = 350`; `all_in.py:108` then treats it as unknown ($0). `money()` also reads only
the first three digits of an unformatted number ("1500" → 150); no current row is affected.

**W16. Dog weight.** `build_master.py:210-215`: "no upper limit stated; dogs over 40 lb cost extra" becomes a
40 lb limit (743 Passaic Ave). `rank.py:231`: "no limit" is not a number, so the 22 buildings with a confirmed
no-limit policy score as unknown on the weight variable instead of best.

**W17. Confirmed floors that never land.** 39 of 115 confirmed or contradicted floor rows do not match either
pattern at `build_master.py:219-224` ("3 (from unit number 317)", "unit 231: 2nd Floor", "1 (ground floor)", "unit
1177: 1"). Unit keys also fail to join: confirm row "unit 5106: floor 1 (ground floor)" against master unit
"005-5106" (Avalon Piscataway) leaves a confirmed ground-floor unit as "floor unknown".

**W18. `avoid.py:62` ground-floor regex captures the word "unit".** "unit 5106: floor 1" yields the exclusion pair
`(7000 avalon way, "unit")`, which matches nothing. "unit 1177: 1" has no match, so the whole building (5 units) is
dropped instead of one.

**W19. Avoid reasons that overstate the evidence** (the avoid decision still stands on another reason in each case):
- Mesa Verde, Jackson Heights (5 address keys, e.g. `34-19 90th st|11372`): "elevator: 4 tenant reports of outages
  in 24 months". The 4 rows are two excerpts of one 2025-12-18 article, one 2026-02-24 excerpt about leaks and
  pests, and "Elevator only in 2 of the buildings" (2025-03-16). `avoid.py:111` counts rows, not independent
  sources, for everything except car crime, though the rule says "independent".
- `20 beacon way|07304`: "management: 3 tenant reports of serious problems in the last 6 months" — rude concierge
  staff, an unspecific complaint, and garage fee increases (tagged `garage_or_lot`).
- `1000 pacific st|06902` is avoid on 3 management rows from a single reviews page; that is its only reason.
- Year-only dates are placed at June 15 (`avoid.py:43`), so a "2026" item counts as inside the last six months.

**W20. Conflicting dog policy drops whole buildings on the weaker source.** Rule-compliant ("conflicting between
sources" is an approved drop), but the evidence does not say "no dogs": 19 E 19th St, Bayonne (12 units; own site
and Apartment List say pet-friendly, a Zumper record "may be stale"), 100 Avenue G (16 units; Bozzuto feed yes,
Trulia no), 467 West Ave, Norwalk (14 units), 8 Norden Pl (4). In `Merge.resolve` two "confirmed" values are
settled by file order (`build_master.py:91-93`).

### Cosmetic or dead code

- `rank.py:217`: `lines_known` counts the string `"found"`, which never occurs in `all_in_lines`. The "cost lines
  stated" variable (15% of the cost part) is a constant.
- `build_master.py:96`: values are compared as strings, so "6" vs "6.0" and "50" vs "50.0" are logged as conflicts.
  61 of the 212 rows in `master_conflicts.csv` are of this kind (36 pet rent, 25 building floors) and bury the real ones.
- Excluded-unit label "no elevator (confirmed on the building's page)" is used for Mesa Verde, where the evidence
  says "CONFLICTING ... which buildings have an elevator is not established".
- `rank.py:180-181`: the `cm()` and `community_pool` shims are always false or empty.

### Checked and found sound

- All-in arithmetic: `all_in` and `all_in_gross` equal the sum of their lines for all 1,524 master units.
- Crosswalk joins: every row of the confirm (1,529), facts (2,213), live-check (505), items (754), NYC records
  (12,672), NYC flags (193), amenities (577), avoid (455) and exclusion (57) files maps to a `building_id`.
- Lifestyle groups: every master unit has a group; 129 cost-passing units are cut by the Jamaica rule.
- Hard gates on the shown list as the master states them: no rent or all-in over $3,000, no floor under 2, no
  "dogs no", no weight limit under 25, no elevator "no" or "inferred", nothing after Dec 15, no safety-cut
  neighborhood, no avoid building, no listing 60+ days old. The problem is the inputs (W1–W5), not the comparison.
- The 23 merged building groups all share a street name.
- 15 sampled exclusions: 4 "dogs not allowed" (supported: "no dogs unless service or emotional support"), 1
  ground-floor (supported: Avalon's own floor number), 4 sketchy (supported), 3 dog-policy conflicts (see W20), and
  the 3 income rows (W10, not supported).

## Suggested order of repair

1. W1, W2, W3: make inferred floor, small-dogs-only and harvester-inferred elevator open gate facts. Expect the
   shown list to shrink sharply (at most 20 shown units have a confirmed floor today).
2. W4, W5, W9: parking and fee mapping, utilities parsing; re-apply the $3,000 gate.
3. W6: Apartment List specials; rebuild rent terms.
4. W7, W8: coordinates and duplicates.
5. W10, W11: units wrongly dropped upstream.
6. Re-run this check on a fresh sample.
