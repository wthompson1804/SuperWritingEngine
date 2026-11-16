# Evidence batch 19: buildings that had no evidence rows (2026-11-16)

Source list: `data/reference/evidence_batches/batch_19.csv`, read once from `data/ranked_units.csv` (`no_evidence == True`) at the start:
**86 units in 31 buildings** (Stamford 42 units / 21 buildings, Jersey City 38 / 6, Manhattan 3, Bronx 2, Yonkers 1). 73 units came from
Trulia, 13 from Apartment List. Outputs: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_19.csv` (each written to a temp
name and renamed). Raw pages: `raw/evidence_b19/`. Nothing else was edited; the pipeline was not run; nothing was committed.

## Counts

- Live check (86 units): **33 live, 12 changed, 15 gone, 26 blocked.**
- Gate facts (31 buildings): elevator 17 confirmed / 14 open; dogs allowed 28 confirmed / 3 open; dog weight limit in pounds
  8 confirmed (50, 50, 50, 50, 50, 55, 75, 100) / 23 open; floor 3 buildings confirmed from a page (121 Towne, 460 Summer, Lafayette) / 28 open.
- Evidence items: 12 management, 1 safety incident, 1 positive, 4 other (city-record summaries), 26 `none_found` rows (with where I looked).
- Ratings: 2 Openigloo scores (66 St Nicholas Pl 2.74 / 3 reviews; 612 W 137th St 3.32 / 3 reviews, all older than 6 months); 29 `none_found`.

## How "blocked" came about

trulia.com was not requested at all. For the 73 Trulia units I used the cached Trulia page (fetched 2026-11-15) for facts, and looked for
the unit on another allowed page. That worked through: Garden Homes' own availability page (5 buildings), 121 Towne's and the Lafayette's
own SightMap availability maps, 3 Acres' manager listing page on AppFolio, Harmony West's own floorplans page, and Zumper building or
address pages (187 Culver, 504 Glenbrook, 460 Summer, Valeur Lofts, Bedford Creative). Where no other page shows the unit the status is
`blocked`, not `live`.

## Grading rules applied (stricter than earlier batches)

- **Elevator `confirmed`** only from (a) the building's or manager's own page for that building, (b) a sentence written by the manager or
  lister in the listing's description ("This elevator building...", "Elevator building with laundry and a live in super"), or (c) for one
  NYC building with no such sentence (2828 University Ave), the city's record of active elevator devices on the lot (worded so the pipeline
  treats it as an official record). A feature-list tag on Trulia or Apartment List alone is `unconfirmed` with the value
  "listing-site amenity tag only" (14 buildings). The Stanley is in that group on purpose: Garden Homes' pages list an elevator for its
  other four buildings here and not for The Stanley.
- **Dogs `confirmed`** when a page names dogs as allowed: own-site text, a manager's sentence, or the listing site's structured pet card
  "Dogs: Allowed". Not confirmed: 121 Towne ("Pets Welcome Upon Approval"), 509 MLK Dr ("Pets on a case-by-case basis"), Atlantic Station
  West (amenity tag, empty policy block). Stamford Commons names 1 dog as permitted but says "larger dogs may be considered case by case":
  dogs confirmed, weight open (the pipeline will read the case-by-case wording as open).
- **Weight** is a number only where a page gives pounds. "Small dogs" with no number is recorded as size-only (7 buildings, all single
  broker listings plus The Morgan).
- **Floor** is `confirmed` only where a page states it. Everything else is "unit: n (reading from the unit label)", `unconfirmed`.
  Harbor Landing G09 and G05 are written as "1 (reading: possible ground floor; the unit label begins with G)".

## Buildings

| Building | Units | Live check | Elevator | Dogs | Weight lb | Floor stated |
|---|---|---|---|---|---|---|
| 66 Saint Nicholas Pl (66 saint nicholas pl) | 1 | 1 blocked | yes | yes | open | open |
| 612 W  137th St (612 w 137th st) | 1 | 1 blocked | yes | yes | open | open |
| 644 W  185th St (644 w 185th st) | 1 | 1 blocked | yes | yes | open | open |
| 3560 Olinville Ave (3560 olinville ave) | 1 | 1 blocked | yes | yes | open | open |
| 2828 University Ave (2828 university ave) | 1 | 1 blocked | yes | yes | open | open |
| 525 Riverdale Ave (525 riverdale ave) | 1 | 1 blocked | yes | yes | open | open |
| 509 Martin Luther King Jr Dr (509 martin luther king jr dr) | 1 | 1 blocked | yes | open | open | open |
| City Line East (15 carbon pl) | 7 | 7 live | open | yes | open | open |
| Harbor Landing Apartments (28 southfield ave) | 5 | 4 live, 1 changed | open | yes | open | open |
| Atlantic Station West (405 atlantic st) | 1 | 1 live | open | open | open | open |
| 111 Prospect St (111 prospect st) | 5 | 2 live, 2 gone, 1 changed | yes | yes | 50 | open |
| 25 THIRD STREET (25 3rd st) | 1 | 1 live | yes | yes | 50 | open |
| Summer Street (800 summer st) | 2 | 2 live | yes | yes | 50 | open |
| The Stanley (1315 washington blvd) | 2 | 1 gone, 1 live | open | yes | 50 | open |
| 1032 Hope Street Apartments (1032 hope st) | 1 | 1 gone | yes | yes | 50 | open |
| Arrive Stamford (100 morgan st) | 2 | 2 blocked | yes | yes | 75 | open |
| 100 Prospect (100 prospect st) | 1 | 1 blocked | open | yes | open | open |
| Park Square West (101 summer st) | 1 | 1 blocked | open | yes | 100 | open |
| Stamford Commons (112-120 strawberry hill ave) | 1 | 1 blocked | open | yes | open | open |
| 121 Towne Apartments (119-121 towne st) | 3 | 2 live, 1 changed | yes | open | open | yes |
| Valeur Lofts (400 main st) | 6 | 5 blocked, 1 live | open | yes | open | open |
| 460 Summer (460 summer st) | 1 | 1 live | open | yes | open | yes |
| 504 Glenbrook (504 glenbrook rd) | 2 | 2 live | yes | yes | 55 | open |
| Bedford Creative (589 bedford st) | 4 | 3 blocked, 1 live | open | yes | open | open |
| Lafayette Stamford (821 e main st) | 1 | 1 live | yes | yes | open | yes |
| The Morgan (83-95 morgan st) | 2 | 2 blocked | open | yes | open | open |
| The Davenport (84 w park pl) | 1 | 1 blocked | yes | yes | open | open |
| 187 Culver Avenue (187 culver ave) | 3 | 2 blocked, 1 changed | open | yes | open | open |
| The Ashton (2 ash st) | 1 | 1 blocked | open | yes | open | open |
| 3 Acres (400 claremont ave) | 21 | 11 gone, 7 live, 3 changed | open | yes | open | open |
| Harmony West (176 w side ave) | 5 | 5 changed | yes | yes | open | open |

## Not open-market, not available, or stale (tags are also in the live-check notes and in `facts`)

- **1032 Hope Street Apartments (Stamford): NO UNITS AVAILABLE.** Manager's page: "Availability: No available units". Status `gone`.
- **111 Prospect St (Stamford): INCOME-RESTRICTED per Trulia's tag** ("INCOME RESTRICTED"); the manager's page states no income limit.
  Studios at $1,675 are far under the Stamford market, which fits a restricted programme. 5 rows: 2 live, 1 changed (511: $1,715 to $1,675), 2 gone.
- **25 Third Street (Stamford): INCOME-RESTRICTED per Trulia's tag**, same caveat. Unit 401 is live at $1,890.
  For both, one phone call to Garden Homes (203-653-2474) settles who qualifies. The tag will exclude both buildings under the current rules.
- **STALE PAGE** (Trulia building page not modified for over two months, and the unit not visible anywhere else):
  100 Prospect (STALE PAGE 2026-07-28), Park Square West (STALE PAGE 2026-09-03), Stamford Commons (STALE PAGE 2026-09-07),
  The Morgan (STALE PAGE 2026-09-09). Recorded as `listing_warning`.
- Park Square West: a web search result (not read on a page) describes it as mixed-income with some below-market apartments. Trulia does
  not tag it. Not recorded as an eligibility fact; ask when calling.
- No building was found to be age-restricted, a co-op, or a different building from its address. 509 MLK Dr's own text gives ZIP 07305
  while the page address says 07304 (noted in the live check only).

## Gate problems found

- **Harbor Landing G09 ($2,388) and G05 ($2,492): possible ground-floor units** (label begins with G; the building also has 1xx units).
- **Price is not a 12-month price:** City Line East (13 to 15-month leases on every stored unit), Harbor Landing (13 months),
  Harmony West (stored prices are net of 1 month free on 13 months; real monthly rent is $2,250 to $2,775), 3 Acres (offer tied to 13 months).
- **Required fees:** Lafayette $180/month (unit 208: $2,075 base, $2,255 total); Harbor Landing $100.37; Atlantic Station West $107.14
  (16A: $2,707 base, $2,815 total); 460 Summer $75 already inside the advertised price; City Line East "$500 Amenity Fee" (frequency not stated);
  Valeur Lofts and The Morgan list required fees without amounts.
- **3 Acres:** 11 of the 21 stored units are no longer on the manager's own listing page (13 apartments listed on 2026-11-16).
  10 remain; 3 of those were repriced by $10 to $20.
- **The Stanley:** unit 222 is gone; 504 is live. Elevator is not on the manager's page for this building.

## Most serious evidence

- **66 St Nicholas Place (Manhattan, 85 units):** city records for 2025-11-16 to 2026-11-16: 105 housing-code violations
  (36 class C, immediately hazardous) and 77 heat or hot-water complaint problems (30 of them since May 2026). Openigloo 2.74 from 3 old
  reviews: "Unresponsive property managers with a history of fraud", package theft by outsiders.
- **3560 Olinville Ave (Bronx, 85 units):** 80 violations in 12 months (38 class C); complaints since May 2026: electric 31,
  unsanitary 26, heat or hot water 22.
- 644 W 185th St: few complaints, but its HPD registration lapsed on 2026-09-01. 612 W 137th St and 2828 University Ave: clean records.
- Outside NYC nothing dated was found for any building (own sites carry undated praise only; Zumper shows no reviews for these addresses;
  Apartment List pages show no reviews; web searches for complaints, lawsuits, break-ins returned other buildings).

## Hosts

- Refused during this batch (added to `raw/evidence_b19/_host_kill.json` and `raw/_host_kill_shared.json`; no further requests):
  `www.stamfordcommons.com` (403 on robots.txt), `www.citylineeast.com` (403, Cloudflare challenge).
- Not requested because already off limits or already refused to another agent: trulia.com, RentCafe / securecafe, Entrata
  prospectportal (Arrive Stamford's availability), `www.504glenbrook.com`.
- Closed by robots.txt to Claude crawlers (honoured): Bozzuto's Atlantic Station page; AppFolio listing detail pages (the listings index is allowed).
- `arrivestamford.com/floorplans` returned one HTTP 504 (server error, not a refusal); not retried.
- Worked: apartmentlist.com, zumper.com, gardenhomesmanagement.com, greystar.com, sightmap.com, waterfrontmgmtllc.appfolio.com (index),
  openigloo.com, data.cityofnewyork.us, and the own sites of Arrive Stamford, 121 Towne, Harmony West, 3 Acres, 460 Summer, Lafayette, Valeur Lofts
  (Valeur's site has no readable text without scripts).

## Limits of this batch

- Apartment List has pages for only 4 of the 31 buildings; Zumper has no reviews or ratings for any of them. So the "ratings" file is
  almost all `none_found`; outside NYC there is no statistical evidence here, only gate facts and listing checks.
- Unit numbers are missing on Zumper for 504 Glenbrook and 460 Summer; the match is by plan, price and size, and is said so in the notes.
- Web search was used only to find page addresses; no fact was taken from a search snippet.
