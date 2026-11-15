# Region pass: Connecticut (Fairfield and New Haven counties)

Run 2026-11-15 (UTC). Script: `scripts/h_region_connecticut.py` (merge + outputs), fed by
`h_region_connecticut_al.py` (Apartment List property pages), `h_region_connecticut_trulia.py` (Trulia building pages of
the leads), `h_region_connecticut_sm.py` (SightMap embeds on building sites), `h_region_connecticut_fp.py` (one floor-plan
site template), `h_region_connecticut_manual.json` (facts read by hand from leasing sites, each with its page URL), plus
the Zumper building-page rows already in `data/listings_raw/zumper.csv`. Raw pages: `raw/region_connecticut/`,
`raw/apartmentlist/`, `raw/trulia/`. A first agent cached the Apartment List pages and ~60 leasing-site home pages; they were reused.

Gates recorded (not applied to drop rows): elevator building, dogs named, weight limit >= 25 lb, rent <= $3,000,
available now..2026-12-15.

## Outputs

- `data/listings_raw/region_connecticut.csv`: 1,648 rows
  (unit / floor-plan rows for buildings that are not failed, one `BUILDING_FAILS:` / `NO_AVAILABILITY:` / `BLOCKED:` /
  `UNCONFIRMED:` row for the rest). Listing ids are prefixed `rc:`; many units also exist in `apartmentlist.csv`,
  `trulia.csv`, `zumper.csv` (same unit, here with the building-level gate facts merged across sites).
- `data/reference/region_buildings_connecticut.csv`: 363 buildings examined. Verdicts: {'unconfirmed': 139, 'pass_with_units': 129, 'fails': 89, 'pass_no_availability': 3, 'blocked': 3}.
  Extra columns beyond the brief: manager, year_built, unit_count, pet_rent, parking, special_offer, required_fees,
  utilities_included, pool, doorman, lat/lon, already_covered (BLT / Greystar / evidence batch 1 or 7), sources.
- `pass_with_units`: 129 buildings (1,038 unit or floor-plan rows <= $3,000, 840 of them available by 2026-12-15), of which 105 are not in the already-covered lists.
- Fail reasons: {'fails:nothing <= $3,000': 9, 'fails:no dogs': 78, 'fails:income-restricted': 1, 'fails:nothing available by 2026-12-15': 1}.

## Towns covered

Greenwich (incl. Byram, Cos Cob, Old Greenwich), Stamford, Darien, New Canaan, Norwalk, Westport, Wilton, Fairfield, Bridgeport,
Trumbull, Stratford, Milford, Orange, Shelton, Derby, Ansonia, Seymour, West Haven, New Haven, East Haven, North Haven, Hamden,
Danbury, Bethel, Brookfield, Ridgefield, Newtown, Naugatuck, Waterbury (only ZIPs inside the search grid).

| Town | examined | pass_with_units | pass_no_availability | unconfirmed | fails | blocked |
|---|---|---|---|---|---|---|
| New Haven | 83 | 25 | 0 | 29 | 29 | 0 |
| Stamford | 73 | 45 | 1 | 18 | 7 | 2 |
| Bridgeport | 36 | 8 | 0 | 12 | 16 | 0 |
| Norwalk | 30 | 13 | 0 | 13 | 3 | 1 |
| Milford | 22 | 6 | 1 | 12 | 3 | 0 |
| West Haven | 17 | 4 | 1 | 3 | 9 | 0 |
| Hamden | 11 | 2 | 0 | 8 | 1 | 0 |
| Danbury | 10 | 4 | 0 | 6 | 0 | 0 |
| Shelton | 10 | 5 | 0 | 4 | 1 | 0 |
| Stratford | 8 | 1 | 0 | 5 | 2 | 0 |
| Darien | 7 | 0 | 0 | 2 | 5 | 0 |
| Fairfield | 5 | 2 | 0 | 2 | 1 | 0 |
| Trumbull | 5 | 2 | 0 | 3 | 0 | 0 |
| Seymour | 5 | 2 | 0 | 0 | 3 | 0 |
| East Haven | 5 | 0 | 0 | 5 | 0 | 0 |
| Westport | 4 | 2 | 0 | 1 | 1 | 0 |
| Naugatuck | 4 | 0 | 0 | 4 | 0 | 0 |
| Wilton | 3 | 0 | 0 | 3 | 0 | 0 |
| Derby | 3 | 0 | 0 | 1 | 2 | 0 |
| North Haven | 3 | 1 | 0 | 1 | 1 | 0 |
| Waterbury | 3 | 1 | 0 | 1 | 1 | 0 |
| Ridgefield | 2 | 0 | 0 | 1 | 1 | 0 |
| Brookfield | 2 | 1 | 0 | 1 | 0 | 0 |
| Orange | 2 | 1 | 0 | 1 | 0 | 0 |
| Ansonia | 2 | 0 | 0 | 0 | 2 | 0 |
| Newtown | 2 | 1 | 0 | 1 | 0 | 0 |
| Greenwich | 1 | 0 | 0 | 1 | 0 | 0 |
| Old Greenwich | 1 | 0 | 0 | 1 | 0 | 0 |
| Bethel | 1 | 0 | 0 | 1 | 0 | 0 |
| Beacon Falls | 1 | 1 | 0 | 0 | 0 | 0 |
| New Milford | 1 | 0 | 0 | 1 | 0 | 0 |
| Woodbury | 1 | 0 | 0 | 0 | 1 | 0 |
| Oxford | 1 | 1 | 0 | 0 | 0 | 0 |

## How each gate fact was established

- **Elevator = yes** only when a page says so: Apartment List amenity "Elevator", Trulia building page feature, Zumper
  amenity, the building's own site, or 6+ floors shown by unit numbers on the listing page (111 Harbor Point, The One
  Atlantic, Curio 269, The Audubon: flagged "6+ floors" in notes, confirm on tour). The basis is in each row's notes.
- **Unconfirmed (elevator not stated, or dogs not named)**: 139 buildings, mostly garden complexes and small walk-ups, but
  also some large mid-rises whose pages simply do not list an elevator. Largest with units <= $3,000:
  Town Walk at Hamden Hills (Hamden, 764 units); THE POINT STAMFORD (Stamford, 641 units); Hillside Apartments (New Milford, 604 units); Sofi Parc Grove (Stamford, 473 units); Abbey Lane (Danbury, 470 units); Seramonte (Hamden, 450 units); Aspen Glen (Hamden, 443 units); Creekline at Fairfield (Bridgeport, 357 units); Bella Vista Phase III Apartments (New Haven, 326 units); Village Park II (New Haven, 324 units); Horizon Homes (Naugatuck, 310 units); Canfield Park (Bridgeport, 300 units); Olive & Wooster (New Haven, 299 units); Ashwood Valley (Danbury, 268 units); The Residences at Main (Trumbull, 260 units); Vault Apartments (Stamford, 252 units); Merion Milford (Milford, 246 units); The Point at Still River (Danbury, 234 units); The Whit (New Haven, 230 units); 925 at North (Hamden, 222 units); The Beacon Apartments (Norwalk, 219 units).
  These need a phone call or a look at the building.
- **Dogs / weight**: dog policy text is verbatim from the page. Weight limits found: 163 Franklin Street 75 lb; 66 Summer Street 75 lb; 750 Summer Street 75 lb; The Asher 50 lb; The Smyth 100 lb; Arrive Stamford 75 lb; Parallel 41 65 lb; Parc at Glenbrook Apartments 40 lb; 504 Glenbrook 55 lb; Darien Commons 100 lb; Soundview Landing 30 lb; The Sheffield SoNo 75 lb; Scribe 50 lb; The Waypointe Apartments 100 lb; 1177 Greens Farms 50 lb; Alto Fairfield Metro 75 lb; The August at Steelpointe Harbor 100 lb; 1 Kennedy Flats 50 lb; Brookview Commons East - Great Downtown Living 25 lb; Ridgeway Place 80 lb; The Residences at Main 100 lb; Spinnaker Brook 30 lb; Spinnaker Station 30 lb; 278 Main Street 25 lb; The Soundview at Savin Rock 35 lb; Taunton Residences at Deep Brook 75 lb; Axis 201 65 lb; The Audubon New Haven 50 lb; The Novella 40 lb; Acme Timber Lofts 50 lb; Cambridge Oxford 25 lb; The Taft Apartments 25 lb; The Whit 50 lb; BAY SHORE APARTMENTS 80 lb; Encore 99 40 lb; Village Park II 30 lb; Ardenwood Apartments 50 lb; Aspen Glen 100 lb; Town Walk at Hamden Hills 50 lb; Liberty Commons 25 lb.
  Most pages give breed restrictions only and no weight number (left blank = not stated).
  Trulia "Size allowed: Small" and Zumper "Small Dog" without a number are flagged in notes.
  Conflict: Atlantic Station West (Apartment List: dogs allowed; Trulia: no pets) is flagged in notes.
- **Prices and dates** come from the listing page (Apartment List unit table, Trulia building-unit table, SightMap, or the
  building site's floor-plan page). Zumper building pages show no move-in date: those rows have an empty `available_date`
  and a note. Floor-plan rows from own sites (Wescott, Infinity Harbor Point, 101 Park Place, Merritt River) carry a unit
  count ("N units available"), not a date. Trulia prices are flagged by the page as total monthly; where Trulia and
  Apartment List disagree for the same unit the other price is in the row's notes.
- **Floor of unit**: only SightMap rows (The Asher, Scribe, The Beacon Norwalk, 18 Dock) carry a floor. Elsewhere `floor` is
  unknown (unit numbers are recorded and usually encode the floor, but that was not asserted).
- **Special offers**: verbatim in `concession_text` / `special_offer`. Pages rarely say whether the listed price is gross or
  net-effective; where not stated it is left as written.
- **Pool**: recorded as stated; no page read said "indoor", so no building is marked indoor.

## Shoreline notes (waterfront interest)

- Stamford South End / Harbor Point: Infinity Harbor Point, 101 Park Place (own sites: elevator, dogs, no weight limit,
  parking fees read), 18 Dock Street (20 floors, SightMap), Harbor Landing, TGM Anchor Point, 121 Towne, 111 Harbor Point
  (6+ floors), The Key and Vault (elevator not stated), Beacon Harbor Point (21 storeys; nothing <= $3,000). BLT buildings
  (Allure, Escape, NV) were already covered. Opus and Postmark (BLT): not on the aggregators read; own sites not reached.
- SoNo: Harbourside SoNo, Ironworks, SoNo 19 Day, Sono Pearl pass on policy; The Sheffield SoNo and SONO One have units but no
  elevator statement (Sheffield's own site returns 403); Soundview Landing is income-restricted (and 30 lb limit).
- Milford downtown / harbor: Metro Star's Metro Point (harbor), Metro 121, Metro on Broad, Metro TOD, Metro View, Metro 188 all
  list an elevator on Metro Star's own pages; Spinnaker Walk and Wharf (Paredim) list an elevator (Wharf: "*Elevator
  Access", varies by unit); Spinnaker Station / Falls / Crest / Square do not mention one. Paredim pages give required
  monthly fees (trash, utility billing, amenity) but no prices.
- Bridgeport: The August at Steelpointe Harbor (many units), downtown City Trust / Arcade / 333 State / 1269 Main;
  Black Rock: Cypress Apartments (585 Ellsworth) has an elevator but no dogs; RockRidge Place (575 Ellsworth): elevator not stated.
- West Haven: The Soundview at Savin Rock (high-rise on the Sound, 35 lb limit, no availability shown), 278 Main, 165 Richards.
- Greenwich / Darien / Westport: almost nothing <= $3,000 in elevator buildings (Darien Commons and Everly Darien start
  above $3,000; The Westporter and 1177 Greens Farms in Westport were already covered; The Ezra in Westport is elevatored,
  "Now leasing Studios and 1BR", no prices published).

## Blocked / not read

- HTTP 403 or robots disallow on the building's own site (not worked around): 111harborpoint.com, thepointstamford.com,
  eastsidecommons.com, thesheffieldsono.com, ironworkssono.com, harboursidesono.com, altofairfieldmetro.com,
  confluencenorwalk.com, 1177greenfarm.com, stamfordcornersapts.com, southwoodbc.com, bedfordhallstamford.com,
  sonopearl.com (robots), elementoneapartments.com (robots), everlydarien.com (robots), rentcafe.com pages (robots).
  For most of these the Trulia / Zumper / Apartment List copy was used instead.
- JavaScript-only availability (not rendered): metrostarapartments.com availability widgets, trademarkfairfield.com
  availabilities, theplatformsono.com, wallstreetplace.com, sonoone.com; securecafe floor-plan pages (Lafayette).
- arrivestamford.com floor plans redirect to a host the proxy could not reach (Trulia copy used).
- Apartment List has no page for: The Sheffield SoNo, 111 Harbor Point, Urby / The Point, Eastside Commons, Postmark, Opus,
  the City Crossing buildings in New Haven (Trulia's "City Crossing" page covers them as one community).

## Gaps

- Elevator or dog policy unconfirmed for 139 buildings (see above); weight limit not published for most buildings.
- Eastside Commons (Stamford), Opus and Postmark (Harbor Point), The Lloyd / Sleepy Hollow / 91 Hope Street (RMS, Stamford),
  The Watershed (RMS, Norwalk, new), Mayfair Square (Danbury), 1188 Lofts and Cherry Street Lofts (Bridgeport): found by
  search or on owner sites, but no allowed page with prices was read. Not in the outputs except Eastside Commons (blocked).
- Trulia leads that are single units in houses (`/home/` pages, about 600) were not re-read: building-first pass only.
- Unit floor is unknown outside SightMap buildings, so the "no ground-floor unit" gate still needs the unit number checked.
