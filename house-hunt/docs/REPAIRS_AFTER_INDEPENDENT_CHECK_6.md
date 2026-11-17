# Repairs after independent check 6: pipeline side

2026-11-17. Spec: `docs/INDEPENDENT_CHECK_6.md` (6 wrong and 14 minor items in 30 sampled trawl-2 apartments, with
five repeatable patterns). Each pattern is fixed as a rule in code, run across every apartment of the master table
(not only the 30), with tests. No web request was made: every fact below comes from pages already cached in `raw/`.
Nothing was committed.

## Shown apartments, before and after

| | NJ | CT | NY | Total | Buildings | Neighborhoods |
|---|---|---|---|---|---|---|
| Before (`ranked_units.csv` of 20:07, the check's population) | 240 | 106 | 41 | 387 | 218 | 68 |
| After | 223 | 104 | 38 | **365** | 196 | 66 |

Why the 22 left (one swap inside Quail Ridge, 3103 out and 3611 in, under the 8-per-building cap):

| Reason | NJ | CT | NY |
|---|---|---|---|
| Template listing (sweep 10): "unverified" plus "floor and elevator" makes two open items | 15 | | |
| Staleness (sweep 1): 280 Verona Ave V5, removed (199 days) | 1 | | |
| Staleness (sweep 1): a second open item, "listing" (Brookwood at Ridge 1105B, 92 days; Eagle Rock at Patchogue 901-06, 65 days) | | | 2 |
| Townhome (sweep 2): West Hill Apartments 5-08, Campbell Ave Apartments 1002-9 | | 2 | |
| Thin-neighborhood rule, knock-on: Rail at Bound Brook 422 and a Gravesend apartment (201) were the only apartment in their neighborhood; with the experience medians recomputed over the new list they fall below the median | 1 | | 1 |

Apartments with one open item: 260 → 246. Disclosures on the shown list: income requirement 2 → 192, furnished 0 → 6,
credit score requirement 4 (new).

## The six wrong items

| # | Apartment | Status |
|---|---|---|
| 3 | 280 Verona Ave V5 | **Removed.** The cached Trulia page's `lastDateModified` (2026-05-07) is read; 199 days by the first tour day, past the 183-day line |
| 6 | 146 Hamilton Ave | **Fixed.** Printed as apartment **204** (the listing's "1BED #204", not Apartment List's index "3"); the floor reads as 2 from the number, so the floor is a disclosure, not an open item; the building's garage fee from another of its Trulia listings ("Garage parking fee: $150/mo") is now the parking line ($150, total $2,302 → $2,452). As a template listing it now carries the asterisk "Confirm this apartment exists and its number before a tour" (its one open item, so it stays shown) |
| 12 | The Kislak 404 (and 204, 501, 504) | **Fixed.** "Furnished apartment" disclosure from the plan name "Studio D-Line (Furnished)"; the "2 Months free on a 14-month lease! 3 Months free on a 27-month lease!" incentive is now read (special offer disclosure), see sweep 6 |
| 14 | 255 Franklin Ave 1 | **Fixed.** Furnished disclosure from "Move-in ready and fully furnished"; parking "Free off-street parking" ($0 line "a space is included") from "Dedicated off-street parking space included" |
| 16 | West Hill Apartments 5-08 | **Removed** (ground-floor home: our data types the community `townhome`, the manager's own page says "Townhomes") |
| 20 | 405 Main St O4 | **Fixed.** A $150 "utilities (fixed monthly fee)" line; electricity and gas say "covered by the monthly utilities fee" at $0; total $1,692 → $1,750. The fee line now reads "Already inside the price shown; the utilities fee below is not", so it no longer contradicts the "$150 on top of rent" disclosure. Laundry is shared in the building (the in-unit tag is dropped). "3x the rent" income disclosure |

## Sweep by sweep

All facts come from one new reader, `build_master.read_listing_page` (cached in `data/reference/listing_page_facts.csv`,
keyed on raw path, file size and listing): for one listing it returns the page's own description (Trulia
`description.value`, Apartment List's description including the long flight-text row, Zumper's listing object, never
other listings' cards), its last-modified date, its title, the site's unit label and how many unit rows the page lists,
and the site's structured requirement and fee sentences. `build_master.apply_listing_page_facts` writes the unit-level
results; each keeps the page's words in a `*_page_words` / `*_words` column (registered as display fields in
`check_registry.py`).

Counts are apartments of the 387 shown before (master table in brackets).

| # | Sweep | Rule (code) | Affected |
|---|---|---|---|
| 1 | Staleness | The cached page's own date (Trulia `lastDateModified`, the Apartment List unit record's `updated_at`, Zumper `modified_on`) fills `page_modified_date` where no note, fact or reviewed correction gave one, and goes through the existing `parsers.staleness` (60 days to Nov 22: one "listing" item; 183: removed). It never replaces a date a checker recorded: a feed's record date can be a sync time (Spinnaker Brook 158-2H: checker 2026-01-26, feed 2026-11-17). `build_master.py`, staleness loop | 73 shown apartments got their first page date (504 in the master): 1 removed (280 Verona Ave V5), 2 open (Brookwood at Ridge, Eagle Rock), 70 fresh |
| 2 | Townhomes | `parsers.townhome_home`: building type townhome / townhouse, a plan named Townhome / Home with Patio / two-level with a ground-floor entry, or a description that calls the homes townhomes ("spacious Townhomes", "townhouse features: main level", "multi-level townhouse living"); not "apartments and townhomes" (Encore 99, Cortlandt Living, J Centra, Modera 55 stay), not "townhouse-style stoops", never where the page states an upper-floor flat. `rank.py` removes it as a ground-floor home unless a page states floor 2+ | 2 (8) |
| 3 | Furnished | `parsers.furnished_statement` on the plan name and the description ("(Furnished)", "fully furnished", "furnished 1-bedroom"; "optional" kept); a furnished lounge or model is not the apartment. Feeds the existing furnished disclosure | 6 (19): The Kislak 204, 404, 501, 504; 255 Franklin Ave 1; 376 Broad St 2B (optional) |
| 4 | Apartment number | `parsers.shown_unit_number` / `site_index_label`: an Apartment List plan label ("1 Bed") or a bare one-digit label on a single-unit page that the listing's own words never use is the site's index; a number stated in the listing's words or title ("1BED #204", "1349 Dixwell Avenue - 24") is used, else none. New column `unit_shown` (the page's `unit`), `unit_number_basis`; `unit` keeps the site label for the evidence and verdict joins. The floor is read from `unit_shown` | 21 (58): 1 from the text (#204, floor now 2), 1 from the title (24), 19 print no number (16 Paterson/Newark template listings, 575 13th Ave, 83 Auburn St, 1078 East Main St, 809 Garden St, 157 Main St) |
| 5 | Parking | (a) `parsers.parking_included_statement`: the listing's own description including a space ("Dedicated off-street parking space included", "Includes 1 free parking spot", "Parking included with rent", "Free Parking in our lot") enters the building's parking words and sets the fee to $0. (b) `parsers.free_plain_lot_beside_paid`: a plain lot named with no price where every published price is for a garage, carport or covered space is the free choice; the paid kind is optional (not where a source says "included: no", where a price belongs to a lot or to parking of no named kind, or where the "lot" is a view). (c) Fee lines of another listing of the same building that did not pass the listing gates count for the building (146 Hamilton Ave) | 29 apartments in 9 buildings: included now $0 in 5 buildings (7 apartments; 255 Franklin Ave, 233 Shore Rd, 301 Tower Ave, 1078 East Main St, 1126 Stratford Ave); free lot beside a paid garage or carport in 3 (21 apartments: Kings Gardens $150 garage, Town Walk at Hamden Hills $42 carport, City Trust 955 Main St $100 garage pass; totals fall by $42 to $150); 146 Hamilton +$150 |
| 6 | Offers | `parsers.offer_applies`: an offer that names its apartments and not this one ("(APT 41 & 36 ONLY)" on 039; "033" = "33"), or whose move-in / signing deadline is before the first tour day ("move in by 11/15/2026"), sets no star, no special-offer disclosure (`all_in.py`: `rent_offer_kind` blank, `rent_offer_not_applied` says why). Also `rent_terms.read_apartmentlist` now reads Apartment List's long descriptions (a flight-text row), which it skipped | 19 lose an offer (Kings Gardens 3, Queens Gardens 5, Crossroads Gardens 2, Addison at Princeton Meadows 8 as shown before, 55 Monroe Place 506); 5 gain one (The Kislak 4, 376 Broad St "one month free") |
| 7 | Laundry | `parsers.shared_laundry_statement`: the listing's own words putting laundry in the building ("Shared Laundry in the Building", "washer and dryer nearby"), with no in-unit washer in the same words, drop a listing site's in-unit tag (not a checker's confirmed one): `in_unit_laundry = on_site_only` | 4 (20): 405 Main St O4, 403 Avenue C A3M, 122 Corbin Ave 401A, 76-17 47th Ave 2B |
| 8 | Flat utilities fee | `parsers.flat_utilities_fee`: "Utilities are Included for a Flat Fee of $150/mo" (checked against the site's "Monthly utilities fee" line when there is one; disagreeing sources leave the estimates) → a "utilities (fixed monthly fee)" line; the electricity and gas estimates become $0 "covered by the monthly utilities fee"; the fees line notes the fee is not inside the price | 1 (1): 405 Main St O4 |
| 9 | Income / credit | `parsers.income_requirement_statement` on Apartment List's requirement field and every description ("Must have 3x the rent in total household income", "Tenants must have an income 3x the rent", "double the monthly rent"; a guarantor's multiple is not the renter's; an income-capped program is left to the eligibility rule); credit from `renter_conditions` plus "620 or higher credit score". Feeds the existing disclosures | income: 192 of the 387 gain the disclosure (192 on the 365 shown after, 2 before); credit: 4 new |
| 10 | Template listings | `parsers.TEMPLATE_PATERSON` plus "All credit types welcome": every cached page of the master with that text (16 ranked apartments; 19 more on Zumper and Trulia never passed the gates). Lines in `data/evidence/verdict_lines_check6.txt`, added with `python3 scripts/verdicts.py add` (each keeps its earlier rows): `asterisk \| unverified \| Confirm this apartment exists and its number before a tour`, with the reason (same agent and text, rent lowered for months paid up front, no number, Newark named for a Paterson address on 6) | 16; 15 drop (two open items), 146 Hamilton Ave stays with this as its one open item |

## Text system (in the fence: `realtor_lines.py`)

With sweep 9 the income requirement is on about half the page. `realtor_lines.catch_options` put any income or credit
condition before the open item, so 192 apartments led with it and `test_realtor_lines.py` (no wording on more than 8%
of the page) failed at 26%. It is routine screening: the catch now follows the open item and the cost, offer, lease,
dog-weight and condo points, before the floor; two more wordings were added. Income now leads on 20 apartments.

`build_page_data.py`: `units[].unit` is `unit_shown` (None when the listing gives no number), `units[].unit_number_basis`
is new; receipt notes for the codes `utilities_flat_fee` and `utility_in_flat_fee`, and the fees-in-price note for a
separate utilities fee.

## Not changed

- 263 Bloomfield Ave (#10): a garage and a lot are both named and neither is priced, so which space she would get is
  not stated; the check-5 rule (the best named kind, garage) stands. No cost is involved.
- #1 (a published $50 pet fee called typical), #10 (low end of a pet-rent range), #18 (Autumn Ridge's $10 community fee
  not added), #8 (a possible duplicate across Zumper and Trulia), #5 / #28 (repeated tour questions), #19 / #24 / #25
  (the offer listed twice), #23 (a floor readable from a checker's numbering note): not part of this brief.

## Runs and checks

- `python3 scripts/run_all.py`: every step ok, clean end (365 shown). Then `build_page_data.py`, `page_data_extras.py`,
  `build_scene_text.py`, `check_scene_text.py` (116 rows, 0 failing), `realtor_lines.py`, `test_realtor_lines.py`
  (77 tests OK), `page_data_extras.py`, `check_published_text.py` (text 0, pipeline strings 0).
- `test_rules.py`: 1,128 pure checks (new `pure_ic6`: the check's own cases for all ten sweeps); `--data` with the
  fresh page data: 12,029 checks, 3 failures that were already failing before this work on the 20:42 page data
  (concierge on 15 apartments, under the 50 the IC4 test expects; Milford garage count 0 against 2; the night moment
  80% "mixed"): they follow from the $2,200 list, not from this repair. New `data_ic6` (the six wrong items, every
  shown template listing carries the asterisk, every income requirement disclosed, the cached-page reader) passes.
- `verify_all.py --quick`: 18 passed, 1 failed (`test_concierge_data.py`, rebuilt next by the coordinator), 1 warning
  (`site/dist` older than `site/data.json`: `build_site.py` is the page agent's step), 4 skipped.
