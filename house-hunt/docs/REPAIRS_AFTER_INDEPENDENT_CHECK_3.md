# Repairs after the third independent check

Written 2026-11-16 (UTC), after `docs/INDEPENDENT_CHECK_3.md` (D1 to D27) and `docs/PENDING_FIXES.md`. No listing page was
fetched and no evidence batch file was changed. Rules changed are in `docs/RANKING.md` (last section). Every fix has a
test in `scripts/test_rules.py` (`pure_4`: 77 rule checks; `data_4` and `page_3` on the output).

## Counts before and after

| | Before (check 3 snapshot) | After |
|---|---|---|
| Ranked | 821 | 763 |
| Shown units | 347 | **489** |
| Buildings with a shown unit | 246 | 232 |
| Neighborhoods with a shown unit (three or more) | 110 (37) | 104 (42) |
| Shown with one open item | 133 | 293 (live check 178, elevator 41, listing 37, dogs 16, availability 16, eligibility 5) |
| Within the all-in cap (master) | 1,653 | 1,613 |
| Verdict table | 539 rows, one per unit | 792 rows for 791 units (ok 445, asterisk 155, disclose 20, remove 172) |
| Avoid cards / held / waiting for a live check | 36 / 28 / 28 | 34 / 35 / 35 |

Of the 347 units shown before, 310 are still shown and 37 are not: 19 are over $3,000 once pet rent is estimated; 9 are
in buildings of the elevator doubt table and were never seen live (two open items); 2 are 30 Broad Street; 2 are Regency
on Hudson; 98-76 Queens Blvd 2M, Halstead Parsippany 2182 and Residences at The Summit K3-02 (the three S1 units); 25 Third
Street 401 (eligibility plus a stale page); and the duplicate 12 Brooklyn Ave row.

## The effect of the three owner decisions, each by itself

Measured by switching one rule off and rerunning (`HH_MAX_PER_BUILDING`, `HH_NO_ELEVATOR_DOUBT`, `HH_NO_PET_ESTIMATE`;
never set in a normal run). The counterfactual counts are by rule: some of those units have no reviewed verdict.

| Decision | With it | Without it | Effect |
|---|---|---|---|
| Step 3, elevator doubt table and garden-style rule | 489 shown, 41 elevator asterisks | 522 shown, 24 elevator asterisks | 33 units not shown (the doubt plus a second open item, nearly always no live check); 17 more shown units carry the elevator asterisk. 15 buildings in the table; the rule adds 2 (Central and Oak, Avalon Union) |
| Step 4a, pet rent estimated ($50 in every state) | 489 shown; 1,613 within the cap | 516 shown; 1,662 within the cap | **28 shown units leave** (27 over the cap, 1 by knock-on); 49 units of the master table leave the cap. 201 shown units use the estimate |
| Step 4b, `all_in_likely` | **97 shown units carry "Could pass $3,000 once parking and fees are known"** | 51 carried "cost near the cap" | removes nothing |
| Step 5, 8 per building instead of 2 | 489 shown in 232 buildings | 325 shown in 232 buildings | +164 units, no new building. 164 of the additional units were read and given verdicts (242 verdict rows written in the loop, three rounds until stable) |

Medians used (`data/reference/cost_estimates.csv`): pet rent $50 (CT 81 buildings, NJ 117, NY 51); parking CT garage $100,
covered $75, lot $0, any $80; NJ garage $135, lot $100, any $130; NY garage $150, lot $75, any $150; required fees CT $46,
NJ $65, NY $103.

## Per defect

| Defect | Status | What was done |
|---|---|---|
| D1 98-76 Queens Blvd 2M | **Fixed, by rule** | `parsers.price_doubt`: a checker's note that the price must be verified is the open item "listing" (`rank.py`). With the open dog policy that is two: not shown. Condo disclosure by rule (D8). |
| D2 Halstead Parsippany 2182 | **Fixed, by rule** | Sibling rule (`parsers.reads_as_ground_like_siblings`, `rank.py`, asserted in `check_registry.py`): a unit with the label shape of siblings a reviewer removed as first-floor units is removed (`data/excluded_by_sibling_rule.csv`). Only 2182 is caught today. Where the removed labels are ambiguous (Steel Works 1119, 1127, 1142) a sibling must match in both places, so 4114 stays. |
| D3 Residences at The Summit K3-02 | **Fixed, by rule** | `build_master.py`: the modification date in any live-check note of a building page applies to every unit listed on that page. K3-02 gets 2026-08-22 (85 days): open "listing" plus no live check, not shown. |
| D4 false dog-warning sentence | Not mine | `scripts/realtor_lines.py` (writing agent). |
| D5 net-effective stated as fact on 13 units | **Fixed** | `rent_terms.NET_NEG` now matches every wording the checker used; a piece that is only the checker's negation is not offer language; `all_in.py` calls a rent net-effective only when `listed_price_is = net_effective`. All 13 are costed on the listed price with no gross figure. Harrison Somerset has no offer at all; the others carry "special offer". Shown net-effective units: 26 → 18. |
| D6 Avalon Somerville 022-265 | **Fixed** | `_ELEV_CONTRA` reads "not listed on AvalonBay's own pages"; the unit shows the elevator asterisk and the lease-term disclosure (two verdict kinds). |
| D7 cap not established | **Changed as the owner decided** | Pet rent estimated; `all_in_likely`; the new disclosure on 97 units. Parking is still not published for 359 shown units and fees for 306. |
| D8 four condos without the disclosure | **Fixed** | Rule: city class R on the listing's own lot and not a managed rental, or a listing typed condo. 142-38 37th Ave 8E (lot not an exact match) has a `disclose / coop_condo` verdict from its own evidence. 9 shown units carry it. |
| D9 The Riverhouse lease term | **Fixed** | A lease term named in the offer of a net-effective price is the lease-term disclosure. |
| D10 30 Broad Street parking | **Fixed in the data** | `parsers.parking_kind` returns `offsite`; it ranks as a lot, never as covered; `parking.offsite` is in the page data. The building is now removed (pending fixes). The host sentence is the writing agent's. |
| D11 staleness switched off | **Fixed** | `build_master.second_site`: a second site is a different host. A unit seen live only on the same stale page takes the page's date. Sono Pearl 401, 134 Baldwin 301 and 411 carry the item; Wakefield Station 401 left on cost. Stale by rule: 16 ranked units before, 165 open and 33 removed in the master now. |
| D12 experience medians | **Fixed** | `build_page_data.py`: medians and ranges over the shown units, with the nearest and farthest neighborhood by drive; neighborhood figures likewise; the Queens baseline is the shown Queens units. |
| D13 neighborhood text against shown places | Not mine | Scene text (writing agent). The page data now holds the shown-unit figures the text should quote. |
| D14 fees counted twice | **Fixed** | A total price never has fees added; a fee named beside its total is a part of it. Parc at Glenbrook 2328 and Summit M2-07 fee line $0; 1 Kennedy Flats $90. |
| D15 wrong floor and height | **Fixed** | The "floor unknown" rows were read below a `continue` and never applied: 27A now has no floor. A floor count stated only by a listing row and below a unit label's reading is dropped (Alexander Crossing). |
| D16 offers that are not rent discounts | **Fixed** | Credits and gift cards no longer lower the rent or the cap test (Spinnaker Wharf, The Botanic). The nine units whose gross bill passes $3,000 are unchanged: the owner's rule allows it and each is disclosed. |
| D17 EDGE 408 / 410 address | **Partly** | Address is 170 Avenue F (`data/reference/address_overrides.csv`, from the building's own unit map in the evidence). The catch sentence is the writing agent's. |
| D18 offer sentences overstated | **Partly** | The data now separates `rent.offer_kind` (net_effective / special_offer / deposit_or_fee) and `rent.offer_text` holds the page's own words. The sentences are the writing agent's. "Up to" is in `rent_terms.csv: conditions`, not in the page data. |
| D19 12 Brooklyn Ave twice | **Fixed** | `build_master.same_apartment_other_site`: an unlabelled row on another site with the same bedrooms, the same published size and a rent within 2 percent is the same apartment. |
| D20 removes too strict | **Fixed** | Grandville Towers 5F and 7C: one open item, shown with the listing asterisk. Bedford Creative, 187 Culver and seven Avalon Maplewood units: the remove verdicts became asterisks, so a live check releases them. |
| D21 elevator asterisks not needed, uneven tag rule | **Partly** | 4110 Bowne St and 80 Richmond Hill Rd: settled by the city's record. 99 Bridge: its asterisk now rests on the doubt table (150 units, three floors by the labels, surface parking). Continuum is unchanged: the owner's rule keeps an elevator inferred from height open. |
| D22 one kind per unit | **Fixed** | Several rows per unit; `disclose` is its own verdict; no asterisk row on a disclosure kind. |
| D23 neighborhoods ranked on one place | Not fixed | The neighborhood score is in `scripts/page_data_extras.py`. Owner's decision (below). |
| D24 safety wording; the Dover quote | **Partly** | The Dover quote is excluded and `parsers.characterises_residents_by_group` screens round-1 quotes. Safety wording is the writing agent's. |
| D25 Jersey City split | No change | 134 Baldwin Ave is borderline; nothing was wrong. |
| D26 floor-plan rows shown as places | Not fixed | 13 shown rows are floor plans with the availability asterisk. Harrison Somerset's six further plan rows got `not_available` verdicts. `parsers.unit_label_key` still reads plan names such as "A - Large-1" as unit labels. |
| D27 small text faults | Not mine | Writing agent. |

Fixed 18, partly 5 (the remainder is in files I do not own, or an owner's rule), not fixed 2 (D23, D26), not mine 4 (D4, D13, D27, and the text half of several).

## `docs/PENDING_FIXES.md`, settled by reading

- **30 Broad Street**: no page shows the building occupied; the listing speaks of "founding residents". All six units have a remove verdict.
- **1244 New York Ave 3A, 61 Clarkson Ave 2B**: both lots match the listing address exactly (BBL 3049490021, class D1, built 2022, 6 floors, 1 active elevator; BBL 3050550081, class D3, built 2021, 6 floors, 1 active elevator). The search summaries describe older buildings on the lots. The city's record stands; nothing changed.
- **Regency on Hudson**: `asterisk / unverified` on every unit. 318 and 417 were never seen live, so they are not shown.
- **Kensington Place**: the neighborhood was already East Brunswick; the city field is corrected.
- **Seven building names** and **Vermella Harrison's address**: `data/reference/address_overrides.csv` (basis and source per row).
- **"counted as $0"**: gone from `meta.notes`, `confirm.why` and the disclosures ("not published").
- **`rent.offer_text`**: the page's own words only (`rent_terms.csv: offer_text_page`).
- **`scripts/building_contacts.py`**: an Apartment List page with no unit count, no website, at most three units and an address for a title is a small lister's listing: kind broker (a named brokerage) or individual owner with a blank phone. 630 West 163rd Street and 1775 E 18th St changed.

## What is still weak

1. 178 of 489 shown units were never seen live. Raising the limit to 8 per building added mostly such units: the first two of a building were checked, the rest were not.
2. The verdicts for the added units are one reader's reading of a digest; most are `ok`, because the rules already mark what is open.
3. The elevator still rests on listing sites alone for 164 of 232 shown buildings. The garden-style rule is narrow; the table is 15 buildings.
4. `all_in_likely` uses medians of small groups (NY lots: 7 buildings) and counts free parking as $0.
5. The pet-rent median is over the master table, not the ranked buildings as the decision says: among ranked buildings New York's median is $55 against $50 used.
6. Page modification dates exist for 529 of 2,632 units; elsewhere the staleness rule says nothing.
7. Step 9 (Zumper opened listings) was not done: `docs/harvest_notes/zumper_open_pending.md` does not exist.
