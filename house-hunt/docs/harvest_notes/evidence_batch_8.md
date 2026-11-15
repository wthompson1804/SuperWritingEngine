# Evidence pass, batch 8 (2026-11-15, 21:13–22:00 UTC)

29 candidate rows in `data/reference/evidence_batches/batch_8.csv`, all in New Jersey (Belleville, Berkeley Heights,
Boonton, Carteret, Chatham, Orange, Dover, East Orange, Bloomfield, Edgewater, Freehold, Garwood, Haledon, Jersey City,
Livingston, Madison, Montclair). Two rows are the same unit at Spring Brook at Chatham (540 Main St, unit 18A) from two
sources, so there are 28 buildings. All were worked.

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_8.csv`. Raw pages: `raw/evidence_b8/`.
Scripts: `scripts/ev8_fetch.py` (refetch), `ev8_site.py` (robots check including Claude groups, then fetch), `ev8_crawl.py`
(own-site pages), `ev8_zumper.py`, `ev8_trulia_parse.py`, `ev8_al_parse.py`, and `ev8_write.py`, which rebuilds all five CSVs
from the cached pages with no network.

## 1. Live check (45 unit rows)

- 43 live at the stored price, 2 changed, 0 gone, 0 blocked. The Botanic 430 and 245 are each $9 higher ($2,178, $2,369).
- Nothing is above $3,000 and every unit is available on or before 2026-12-15.
- Sources: 18 Trulia building pages, 11 Apartment List pages, plus the AvalonBay community page for Avalon Boonton.

### Needs a human look before it is shown
- **Avalon Boonton 1177 ($2,535) is on floor 1** per AvalonBay's own unit data: fails the no-ground-floor gate. 2154 is on floor 2.
  The prices shown are "starting at" prices for 10- and 20-month terms; the 12-month price was not read. Required fees add $85.
- **Cedar Street Commons is 62+ senior housing** (in the listing name; Apartment List occupancy type "senior").
- **Aura 240 and 55 Jordan** show prices by floor plan only, and Trulia counts 0 available units for each. The price matches,
  but no specific unit is confirmed.
- **416 Highland Ave**: the page lists "1 Bed" with no unit number (the title says 312), from a Buildium feed.
- **Metrovue and Appletree Suites** are tagged "Furnished" on Trulia.
- **Stale availability**: Canterly Place 2001 (available since 2026-04-02), The Ivy 621 (since 2026-07-17), Two South Willow
  547 and 508 (since July and August). These may be standing inventory or stale feed rows.
- **Required monthly fees on top of rent** (Apartment List unit data): RT 500 $110, The Botanic $97.55, The Ivy $64, Two South
  Willow $57.14. Zumper lists a $295 flat utilities fee for The Botanic; the two sources differ.
- RT 500 shows a 24-month lease length, The Ivy 18 months, LIA 15 months for the stored prices.

## 2. Gate facts (133 rows: 58 confirmed, 74 unconfirmed, 1 contradicts)

- **Dog weight limit in pounds, confirmed for 9 rows (8 buildings):** Aura 240 25 lb, Lofts at Garwood 25 lb (both exactly at
  the gate), General Wayne and Ridgedale Gardens 45, Haledon Estates 50 (one pet only), Parkway Lofts 65, Freehold In-Town
  Commons 75, Spring Brook at Chatham no limit, Avalon Boonton no limit stated (breed list includes German Shepherds).
- **Unconfirmed for 20 buildings.** Three say "small dogs" with no number: Ethos Kelsey, Appletree Suites, 19 Rock. Cedar
  Street Commons says "Breed and Weight Restrictions" with no number. The rest allow large dogs but publish no weight.
- **Dogs allowed:** confirmed for all 29 rows.
- **Elevator:** listed for 18 buildings. Not stated for 11 rows: RT 500, Avalon Boonton, The Ivy, Spring Brook (2 rows),
  Freehold In-Town Commons, Haledon Estates, Cedar Street Commons, Canterly Place, General Wayne, 83-87 Forest St. Several of
  those are garden-style or pre-war buildings and may be walk-ups; RT 500, The Ivy and Canterly Place are new mid-rises where
  the listing simply omits it.
- **Floor:** confirmed only for the two Avalon units. 29 are inferred from the unit number (marked unconfirmed); 14 unit labels
  give no floor (18A, 81-29, 36D, 26B, GAR2R-08, 8703, 7012, Cedar Street 1108 and 1314, and the plan-level listings).
- Metrovue is 13 storeys (listing text).

## 3. Ratings (30 rows)

Readable ratings for 6 buildings; 22 rows are `none_found`.

| building | source | rating | reviews | as of |
|---|---|---|---|---|
| The Ivy | Google rating shown on Zumper | 4.8 | 24 | 2024-12-07 |
| Riello Edgewater | Google rating shown on Zumper | 4.0 | 85 | 2024-12-07 |
| Lofts at Garwood | Google rating shown on Zumper | 3.3 | 6 | 2024-10-31 |
| The Agnes | Google rating shown on Zumper | 4.6 | 112 | 2024-12-06 |
| Avalon Boonton | AvalonBay page | 4.3 | 256 | 2026-11-15 |
| Avalon Boonton | Apartment List | 5 | 1 | 2024-08-20 |
| Spring Brook at Chatham | own-site widget | 5 | 2,900 | 2026-11-15 |

- **No building has a readable review from the last six months.** Zumper's Google pulls date from late 2024, and it shows 3 to
  8 review texts per building, mostly 5-star. `reviews_last_6_months` is 0 for those rows and blank where no text was readable.
- The Spring Brook figure (2,900 reviews for a small complex) is almost certainly company-wide. Treat it as not a building rating.
- The Riello rating sits on a Zumper page titled 100 Daibes Ct; the review texts name the Riello.
- Trulia building pages carry no ratings. Apartment List shows "collecting reviews" for 10 of its 11 pages.

## 4. Evidence items (39 rows)

none_found 29, positive 8, management 2.

- **Lofts at Garwood:** two 1-star Google reviews from 2023-09 about the leasing office (unresponsive, tours cancelled at the
  last minute, an application cancelled without notice). They are about leasing, not living there, and are over two years old.
  Zumper's own summary repeats them; it is undated and not recorded as an item.
- Positives for The Ivy, The Agnes, Riello and Avalon Boonton (2022 to 2024).
- A web news search was run for every building (name and address, with complaint, police, car, elevator and lawsuit terms).
  **None returned incident, lawsuit or complaint coverage of a batch building.** No car-crime, elevator-outage or safety items.
- Nothing in this batch meets an avoid threshold.

## 5. Blocked or not done

- HTTP 403 bot walls, not read: livethebotanic.com, theivychatham.com, garwoodlofts2.com, goldberg-realty.com, theagnes.com.
  liabyvermella.com returned a challenge page.
- Robots disallowed for us: communityfees.bozzuto.com (Two South Willow fee sheet), Patch, BBB.
- Sites with no policy text in their HTML: aura240.com, metrovuejc.com, 55jordan.com, 19rock.com, skylarloftsjc.com,
  canterlyplace.com, appletreesuites.com, twosouthwillow.com, ethoskelsey.com, kriegmanandsmith.com. No browser rendering was tried.
- No own site was found for Harclay House, 416 Highland Ave, 134 Baldwin Ave, Freehold In-Town Commons or 83-87 Forest St.
- Zumper returned 404 for seven addresses. Three Zumper address pages matched a different listing at the same address
  (134 Baldwin #3, 19 Rock 609, a house at 10 Ridgedale) and were not used.
- Search results mentioned ratings on Apartments.com (off limits), after55.com for Cedar Street Commons, and a Bozzuto reviews
  page for Two South Willow. None was read, and nothing from the snippets is recorded.
- Search results (not read on a page, so not recorded as facts) suggest: 416 Highland Ave is "The Highland" by PEEK Properties;
  Harclay House is managed by Shamco; 55 Jordan by Goose Property Management; a News 12 East Orange elevator story is about
  The Pavilion, a different building.
- Parkway Lofts' own site has two undated resident testimonials. They are chosen by the building and undated, so not recorded.
- Court and code-enforcement records were not searched: none of these towns has an address-searchable record online that I found.
