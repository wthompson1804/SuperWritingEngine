# Evidence pass, batch 7 (2026-11-15, 21:13–21:35 UTC)

29 buildings in `data/reference/evidence_batches/batch_7.csv`: 25 in Connecticut (Bridgeport, Danbury, Derby, Milford,
Norwalk, Stamford, Stratford, Trumbull) and 4 in New Jersey (Aberdeen/Matawan, Atlantic Highlands, Bayonne). All 29 were
worked. Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_7.csv`.

Raw pages: `raw/evidence_b7/` (index `_index.jsonl`; Zumper parse `zumper_bld.json`).
Scripts: `scripts/ev7_fetch.py` (refetch), `ev7_site.py` (robots check incl. groups naming Claude, then fetch),
`ev7_zumper.py`, `ev7_al_parse.py`, `ev7_trulia_parse.py`, `ev7_lines.py`, and `ev7_write.py`, which rebuilds all five
CSVs from the cached pages with no network. Re-running it rewrites the files whole.

The work was done in two sittings. The first fetched the listing pages, Trulia second-source pages, Zumper pages and most
own sites. The second did the news searches, the remaining own sites and wrote the files. Nothing cached was refetched.

Dog gate used: 25 lb or more. The confirm file records the stated limit, not a pass or fail.

## 1. Live check (46 unit rows)

42 live at the stored price, 2 changed, 2 gone, 0 blocked. Nothing is priced above $3,000.

- **Changed:** The Confluence at Norwalk 2318 ($2,626 stored, $2,634 now) and 2140 ($2,761 stored, $2,770 now).
- **Gone:** The Link at Aberdeen Station 5102 and 1213. The studio/1BR units still listed are 1312 ($2,350, from
  2026-12-25, outside the window) and 4111 ($2,380, from 2026-12-08).

### Listings that need a human look before they are shown
- **Tree Haven 31B ($2,200): the feed is stale.** Apartment List shows `available_on 2024-02-05` and no "availability
  last checked" time; the Trulia page for the building shows 0 available units; the own site returns 403. The row is
  marked live because the unit is still on the page at the stored price, but treat it as unverified. A local radio report
  describes the Tree Haven III building as a "two-story brick building", and no page lists an elevator: it is probably a
  walk-up.
- **Skyelofts North (2 rows):** Trulia lists floor plans named S207 ($2,185) and 417 ($2,207), says 0 units are
  available, and was last modified 2026-09-03. The building's own availability page, read today, does list residences
  207 and 417 as one-bedrooms, with the price hidden. So the units look real, and the prices rest on Trulia alone.
- **Spinnaker Brook 158-2H** is available on 2026-12-15, the last day of the window.
- **Available later, but inside the window:** Piper 3012 and 1013 (12-01), Halstead Norwalk 212 (12-09) and 310 (11-26),
  Stamford Corners 341 (11-25), The Hazel 203 (12-07), Merion Stratford 4304 (11-30).
- **Probable ground-floor units, from the unit number only (not confirmed on any page):** Merion Milford 1133, Piper
  1013, Waypointe MB128, Confluence 2140, TGM Anchor Point 1109, Merion Stratford 1104, Royce 9114. Each would fail the
  no-ground-floor gate if the reading is right.
- **Stored prices are base rent for the Apartment List buildings.** Required monthly fees come on top: about $92 at
  Piper, $96 at The Confluence, $108 at Atlantic Station, $115 at Halstead Norwalk, $120 at 75 Tresser, $160 at The
  Waypointe, $230 at Woodside Trumbull (see the notes column and `facts_batch_7.csv`). Stamford Corners 341 is $2,805
  base and $2,883 with fees.
- **Stored prices for Residences at The Summit, Parc at Glenbrook and Bedford Hall are Trulia "total prices"**: base
  rent plus the required monthly fees the owner lists ($25, $123 and $140).
- **Franklin School Lofts 51-A:** "51" looks like the street number (the manager lists the property as 45-47 and 51
  Derby Ave), so the floor is unknown, and no page lists an elevator.

## 2. Gate facts (142 rows: 62 confirmed, 77 unconfirmed, 3 contradicts)

- **Dog weight limit confirmed for 7 buildings:** The Waypointe 100 lb, Tree Haven 80 lb (50 lb for greyhounds), 750
  Summer Street 75 lb, Parallel 41 65 lb, Parc at Glenbrook 40 lb (own site and Trulia agree), Spinnaker Brook 30 lb,
  The Royce at Trumbull no weight limit (own site). All seven clear 25 lb. The Waypointe figure comes from Trulia's
  policy text, whose fee amounts differ from the fee table on the same page, so the text may be old; the building's own
  FAQ gives no number.
- **A limit exists but the number is not published:** 75 Tresser and Woodside Trumbull (own FAQ: "Breed restrictions,
  weight limits, and pet fees apply"), TGM Anchor Point, and Spinnaker Wharf (Apartment List text has the number
  missing: "A pound maximum weight limit per pet"; its sister property Spinnaker Brook says 30 lb).
- **Sono Pearl:** one dog, "Size allowed: Small", no number. Own site not read (robots.txt).
- **Contradictions (3):** Trulia says dogs are not allowed at Piper, Halstead Norwalk and Stamford Corners; Apartment
  List lists dogs as allowed for all three, and the own sites of Piper and Halstead Norwalk describe pet amenities.
- **Elevator:** confirmed for 22 buildings. Not listed on any page read for Franklin School Lofts, Merion Milford,
  Merion Stratford, Woodside Trumbull, Tree Haven and The Link at Aberdeen Station. Spinnaker Wharf's own page marks
  "*Elevator Access" with an asterisk, meaning some buildings only.
- **Floor of the unit:** inferred from the unit number in all 46 rows and marked unconfirmed. No page states a floor.
- **Storeys:** ELK Harbor View 11, Canterbury Green 14, Tree Haven III 2.

## 3. Evidence items (41 rows)

none_found 26, positive 10, other 3, noise 1, elevator 1. No car crime, safety incident or management complaint could be
read for any building in this batch.

- **Tree Haven (2023-01-06, New Jersey 101.5):** a fire at the Tree Haven III complex killed one resident and displaced
  14. Recorded as `other`.
- **The Confluence at Norwalk:** a sprinkler-contained apartment fire on 2020-10-15 (1st Responder News). Zumper's
  machine-written summary of the building's Google reviews says "Some note occasional elevator outages"; no review text
  behind that line is shown, so it is recorded once as `elevator` with that caveat.
- **The Waypointe (2025-04-29):** one renter review on Apartment List names poor sound insulation.
- The rest are short positive reviews (Apartment List, and Google reviews shown on Zumper).

One web search per building (name, address, former name) returned listing sites almost everywhere.

### Leads that exist but could not be read (not recorded as evidence)
- **Atlantic Station:** a residents' site, atlanticstreetresidents.com, appears to log outages at 355 Atlantic St. Its
  robots.txt disallows Claude agents. This, plus the single 1-star rating on Apartment List, makes Atlantic Station the
  building most worth a manual check.
- **The Royce at Trumbull:** a town civic alert dated 2023-05-01 about an incident at the complex, and a CT Post article
  on police calls to the Trumbull apartment complexes. Neither host allows our fetch.
- **Halstead Norwalk:** a Nancy on Norwalk article about a cleanup order on Norden Place (HTTP 403). It may concern the
  neighbouring office property, not the apartments.
- **Merion Milford:** a CT Post article on the sale of the complex to Merion Realty Partners.

## 4. Ratings (29 rows, one or more per building)

- Google rating shown on Zumper: The Confluence at Norwalk 4.6 from 306 (figures pulled 2025-02-12), Residences at The
  Summit 4.3 from 10 (pulled 2024-12-07). Zumper shows only the highest-rated texts.
- Apartment List: 11 buildings, 1 to 3 ratings each. Low ones: **Atlantic Station 1.0 (1 rating), Merion Stratford 2.0
  (1), Halstead Norwalk 2.3 (3, two of them 1-star), The Hazel 3.0 (2, one 1-star).** The page gives no date or text for
  the low ratings, so `negative_last_6_months` and `negative_older` are left blank on those four rows and the count is
  in `notes`.
- none_found: 16 buildings. No review read in this batch is dated inside the last six months.
- The file carries two columns beyond the brief (`retrieved_at`, `notes`), matching `ratings_round1.csv`.

## 5. Facts (265 rows)

Parking type and fee, pet rent and fees, required and optional monthly fee items, move-in fees, pool, concierge, year
built, unit count, management company, current specials.

- Former names, which matter when reading old reviews: Merion Milford was Avalon Milford; Halstead Norwalk was Avalon
  East Norwalk; Parc at Glenbrook was eaves Stamford; TGM Anchor Point was Avalon on Stamford Harbor; Merion Stratford
  was Avalon Stratford; 750 Summer Street is listed on Zumper as Verano Moderne; ELK Harbor View is also listed as Harbor View Towers.
- Ownership changes: 333 State St was sold in October 2021; Canterbury Green was sold for $25M (article dated
  2026-02-27), so reviews older than that describe the previous owner.
- Canterbury Green's own fee guide: amenity fee $50 a month, parking $125 a month, pet rent $50 a month.
- Summer House: internet $60, amenity fee $85 and trash $25 a month on top of rent.

## 6. Blocked or not read

- HTTP 403 (bot wall): merionmilford.com, merionstratford.com, stamfordcornersapts.com, confluencenorwalk.com,
  treehavenapts.com, rentatthelink.com, nancyonnorwalk.com.
- robots.txt names Claude: sonopearl.com, atlanticstreetresidents.com, ctpost.com and the other Hearst Connecticut
  papers (Stamford Advocate, The Hour, Darien Times), bozzuto.com. trumbull-ct.gov disallows the page we wanted.
- Not fetched by rule: Patch, QNS, BBB.
- Zumper has no page for Spinnaker Wharf, Spinnaker Brook, Canterbury Green or Woodside Trumbull (404).
- No own leasing site found for 333 State St, 750 Summer Street (navarinoproperty.com building pages return 404) or ELK
  Harbor View.
