# Region pass: mid_hudson (Putnam, Dutchess, Orange, southern Ulster)

Last updated 2026-11-15 (two agent passes on the same day; the second continued the first).

## Outputs

- `data/listings_raw/region_mid_hudson.csv`: 89 rows (harvest column contract; some cells hold line breaks, so the
  file has more lines than rows).
- `data/reference/region_buildings_mid_hudson.csv`: 117 buildings examined.
- `scripts/h_region_mid_hudson.py`: fetch helper and Zillow/Zumper page readers (pass 1; weight threshold now 25 lb).
- `scripts/h_region_mid_hudson_recheck.py`: relabels weight-limit failures under the 25 lb gate (idempotent).
- `scripts/h_region_mid_hudson_add.py`: pass 2 rows read from own leasing sites, manager portfolios and Zumper/PadMapper pages (idempotent).
- Raw pages: `raw/region_mid_hudson/` (index in `_index.jsonl`).

## Gates used

Listed rent ≤ $3,000 and all-in ≤ $3,000; available now through 2026-12-15; elevator building, no ground-floor unit;
dogs explicitly allowed with any weight limit ≥ 25 lb (lowered from 40).

## Search grid limits that shape this region

- **Poughkeepsie city (ZIP 12601) is outside the grid.** That is the whole waterfront and downtown (One Dutchess,
  40 Cannon, Fulton Landing, Country Club Apartments, etc.). Only the Town of Poughkeepsie / Arlington side (12603)
  is inside. Two 12601 buildings seen on Zumper are recorded as `out_of_grid`; none were harvested.
- **Kingston (12401) is outside the grid**, as are 12477, 12528 and 12538. Not covered.
- New Paltz (12561), Pawling (12564), Marlboro (12542) are inside and were covered where listings appeared.

## Sources and method

1. Zillow city search pages for every town (enumeration only), then each Zillow building page (`/apartments/...`,
   `/b/...`). robots check through `h_mgmt_common.robots_ok` passed for these paths; crawl delay honoured.
2. Zumper city pages and building pages; PadMapper building/address pages.
3. Own leasing sites and manager sites where one could be found: loftsatbeacon.com, edgewater-beacon.com,
   scenicbeaconproperties.com, westendloftsny.com, bottiniproperties.com (10 property pages), eastdalevillage.com
   (incl. the pet policy document), kirchhoffpm.appfolio.com/listings, villageplaceatgoshen.com,
   thehamletatcarmel.com, theparkatmain.com, northcourtapartments.com.
4. Leads file: every lead flagged elevator = yes was opened (Edgewater, 445 Main, Collegeview, Bluestone Ct Maybrook,
   two Pawling buildings).
5. Web search was used only to find buildings and URLs. No price, date or policy was taken from a search result.

## Towns covered

| Town | What was found |
|---|---|
| Beacon | 21 buildings. Elevator buildings: Edgewater (18/24/30 Edgewater Pl), The Beacon (445 Main / 35 Van Nydeck), 364 Main, 344 Main, The Arno, The Lofts at Beacon, 7 Creek Drive. See below. |
| Fishkill | Westgate (elevator, dogs, waitlist only), Eagle Rock at Fishkill, Mountainview Garden, Hudson Place, 115 Jackson (no pets), 3 Fishkill Glen. No elevator unit available. |
| Wappingers Falls | Garden communities only (Vista Point, Chelsea Ridge, RiverBend, RiverBend East, Oak Tree Garden, Toje). No elevator stated anywhere. |
| Poughkeepsie (12603 only) | Collegeview Tower (9 floors, dog policy unpublished), Lagrange Farms (pass), Eastdale Village (elevator buildings, 35 lb limit, no vacancies), Royal Pointe, garden communities. |
| Newburgh | 19 buildings. Lofts at the Foundry (elevator; cats and small dogs only, no number), two 55+ elevator buildings, otherwise walk-ups and garden communities. No East End or waterfront elevator rental with a 1BR in range was found. |
| New Windsor | Garden communities (Knox Village, Mountainview Village, Summit Terrace, Hawk's View, Farrell, Squire Village). No elevator building. |
| Cornwall, Cold Spring | Zillow and Zumper searches returned only houses and small walk-ups (Cold Spring: one 2BR building at $3,100+). No elevator rental building found. Butterfield in Cold Spring is condo/55+. |
| Brewster, Carmel, Mahopac | 6 Putnam Ave Brewster (small dogs only), The Hamlet at Carmel (income-restricted), small buildings. Mahopac search returned only houses and Avalon Somers (Westchester, from $3,175). No qualifying elevator building. |
| Middletown | The North Court (pass, 6 units), The Park at Main (pass; 2 of 3 units look ground floor), Residences at West Hills (pass, floor-plan prices, $159/mo required fee), Tower Ridge Grande (elevator, 20 lb limit: fails), 13 garden communities. |
| Goshen | Village Place at Goshen: elevator confirmed on own site, but all plans are 2BR (fails). Carriage Hill, Woodhill Fletcher, Briarwood House: garden style. |
| Monroe, Harriman, Warwick, Chester, Highland Mills, Florida | Only houses, small walk-ups and Knollcrest Village (no pets). No elevator rental building found. |
| Pawling, Patterson | Pawling Commons (71 E Main, elevator, 1BR $2,400, "one pet under 40 pounds") and 23 E Main St (elevator, 4th floor, 1BR $2,000, pet policy unstated). The Dutcher House: cats only. |
| New Paltz | Trail Link Collective (pass, 3 units in window). Others garden style or no dogs. |
| Maybrook, Wallkill, Hopewell Junction, Garrison, Highland Falls | Small or garden buildings; 306 Bluestone Ct Maybrook has an elevator but is 55+. |

## Buildings that pass with units (elevator stated, dogs named, rent ≤ $3,000)

| Building | Units in window | Things to confirm |
|---|---|---|
| Edgewater, Beacon | 30-208 studio $1,700 (2nd fl), 24-209 1BR $2,700 (2nd fl), 30-406 studio $1,950 (Zumper only); 24-107 1BR $2,900 is ground floor | Dogs only in 18/24/30 Edgewater Pl; pet fee and parking fee not published; offer banner "Fall Incentives" has no terms |
| 364 Main, Beacon | 203 1BR $2,950 | All-in likely over $3,000 with utilities; covered parking limited |
| The North Court, Middletown | six 1BRs $2,195 to $2,595, floors 2 and 4 | Zillow offer text says 2BR prices are net effective; own site says 1BR "Starting at $2,265", so ask whether the $2,195 units are net effective. Dog $50/mo, 1 max |
| The Park at Main, Middletown | 63 1BR $2,450; 103 and 110 look ground floor | $35/mo required fee on Zillow; pool (not stated indoor) |
| Residences at West Hills, Middletown | 1BR plans $2,556 to $2,958 | $159/mo required membership fee pushes the dearer plans over $3,000 all-in; no weight limit stated |
| Lagrange Farms, Poughkeepsie 12603 | 303 1BR $2,450 | Pet fees not published |
| Trail Link Collective, New Paltz | 307 $2,495 and 303 $2,550 (Dec 1); 122 is ground floor; 209 is Feb 2027 | Pet fees not published; own site returned 403 |

Elevator units in range where the **dog policy is not published** (call needed): The Beacon at 445 Main (308 studio
$2,400 Dec 1; 212 1BR $3,000 now; 106 looks ground floor), Collegeview Tower (707 $2,025, 810 $2,075),
Pawling Commons 203 ($2,400; "one pet under 40 pounds"), 23 E Main St Pawling 3A ($2,000).

## Re-check after the weight gate moved to 25 lb

Rows that had failed only on a 25 to 39 lb limit were relabelled. None became a pass, because none has a stated elevator:

- Boulder Pointe (30 lb), Country Manor (35), Stevens Manor (35), Mountainview Village (35), Village Crest (35),
  Hopewell Gardens (35): now `ELEVATOR_UNKNOWN` (garden-style communities; no elevator on the page).
- The Hamlet at Carmel (25 lb): weight would pass, but its own site shows it is income-restricted (AMI rent tiers), so it fails on eligibility.
- Still failing on weight: Tower Ridge Grande (20 lb, elevator) and Sutton Hill (20 lb).
- "Small dogs only" with no number (Lofts at the Foundry, Knox Village, Summit Terrace, Farrell Gardnertown, Southgate,
  6 Putnam Ave, Ridgefield, Dutchess Apartments and others) are unchanged: the pages give no weight, so the limit
  could be above or below 25 lb. Only Lofts at the Foundry has an elevator, and it lists no studio/1BR.
- New in pass 2: Eastdale Village (35 lb, elevator buildings) and Oak Tree Garden (35 lb, garden style).

## Special offers seen (verbatim, with basis where the page states it)

- The North Court: "1 Month free rent on select 2 bedroom units with 13 month lease. Prices advertised for 2 bedroom is net effective rent." / "2 Months free on Select 2 bedroom units with 24 + Month lease. Prices advertised are net effective rents." (2BR only as written.)
- The Park at Main: "Community Heroes Special: Qualified healthcare workers, hospital staff, first responders, law enforcement, firefighters, EMTs, teachers & military personnel receive 50% off the security deposit with verified employment."
- The Lofts at Beacon (over the cap): "Reduced security deposit ($500) plus 1/2 off first month's rent, lease by 12/31/26."
- Edgewater: site banner "Fall Incentives, Book a Tour Today" (no terms).
- Others are recorded in `concession_text` (Chelsea Ridge, Imperial Gardens, Sutton Hill, Reserve at Lakeside, the "Hometown Heroes" group).

## Blocks

- traillinkcollective.com: HTTP 403 (stopped).
- rentmanager.com widget behind loftsatbeacon.com: robots-disallowed (prices came from Zillow instead).
- Bottini availability search and the Village Place "request availability" form render by script; the static pages hold no units.
- baxterpm.com, hudsonviewpark.com, residencesatwesthills.com, collegeviewtower.com: guessed domains did not resolve; no own site located.
- Apartments.com, RentCafe, HotPads, Homes.com, ForRent: not fetched (blocked or off limits per `docs/SOURCES.md`).
- Apartment List unit page for 249 Main St Beacon returned an empty page.

## Gaps

- **Elevator status is unknown for 28 garden-style or small buildings.** Aggregator pages rarely state "no elevator";
  these are almost certainly walk-ups but were not marked `no` without a statement.
- **Dog policy unpublished** at The Beacon (445 Main), Collegeview Tower, West End Lofts II (also elevator unknown,
  1BR from $2,376), 23 E Main St Pawling, 315 Beacon (price on request).
- Beacon buildings without an accessible leasing page: 344 Main (only a commercial unit listed), 249 Main and
  226 Main (condominiums, individual owner rentals), 121 Rombout and 179 Main (over the cap on the search card).
- Floors are inferred from unit numbers in most rows (noted per row); building floor counts are mostly not published.
- Pool is recorded as stated; no page in this region says "indoor". No doorman was stated anywhere.
- Year built is filled only where a page gave it (RiverBend 2007, 344 Main 2018, Westgate 2022, Edgewater 2024 not confirmed on a fetched page).
- Zumper city pages show only the first page of buildings; Zillow searches list only buildings with a current
  listing. A fully leased elevator building with no listing and no website found by search would be missed.
