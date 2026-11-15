# Evidence pass, batch 16 (2026-11-15, 22:47–23:00 UTC)

29 buildings in `data/reference/evidence_batches/batch_16.csv`, 30 unit rows (Fairfield Metro at Glen Cove has two).
25 are in New York City (Brooklyn 13, Manhattan 9, Queens 2, Bronx 1); 4 are in Nassau County (Glen Cove, Woodmere,
Hempstead, Long Beach). All 29 were worked.

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_16.csv`. Raw pages: `raw/evidence_b16/`.
Scripts: `scripts/ev16_fetch.py` (refetch), `ev16_site.py` (robots check incl. Claude groups, then fetch),
`ev16_trulia_parse.py`, `ev16_igloo.py` (Openigloo by tax lot through the reviewed-buildings sitemaps),
`ev16_zumper_reviews.py`, and `ev16_write.py`, which rebuilds all five CSVs from cached pages with no network. The
writer reads parse output in the session scratch folder; if that is gone, rerun the fetch and parse scripts first.

## 1. Live check (30 rows: 18 live, 12 blocked, 0 gone, 0 changed)

**Trulia started refusing requests (HTTP 403) after the 17th page.** Two single retries, 6 and 10 minutes later, were
also refused. I stopped there and did not work around it. So:

- **15 units re-read and live at the stored price**, all inside the window: 1710 Newkirk 4, 1256 Ocean Ave 5D,
  623 Ave H 6C, 770 Ocean Pkwy 2O, 1941 Coney Island Ave 402 (available **Dec 15**, the last day), 2611 W 2nd St 5,
  2121 Shore Pkwy 201, 8700 25th Ave 6G, 137 W 137th 3D, 100 W 139th 27A, 2419 ACP Blvd 5R, 10 Wendell St 20,
  405 W 206th 713E, 204 Sherman 4 (Nov 20), 121 Seaman 5B.
- **3 Fairfield rows are live at floor-plan level only** (Glen Cove studios $2,650 and $2,820; Woodmere studio $2,235):
  Trulia shows the plan price as "Available Now" with 0 available units, so there is no unit, floor or date.
  Woodmere's own site agrees on $2,235. **Glen Cove's own site shows only a one-bedroom from $2,950 and no studio
  price**, so the two studio prices rest on Trulia alone.
- **12 units blocked** (not re-read tonight): 4778 Broadway 6G, 10 Park Ter E 6G, 3250 93rd St A3, 139-05 85th Dr 1,
  490 Ocean Pkwy 64, 3660 Waldo J2, the Long Beach listing, 3310 Nostrand 503, 2900 Nostrand 2M, 3280-3310 Nostrand
  202, 408 W 130th 61, 1802 Ocean Ave 7F. Their gate facts below come from the harvest capture about three hours
  earlier and are marked unconfirmed. The Long Beach listing was only ever read as a search card.
- Two of the blocked units could be checked another way:
  - **10 Park Ter E:** Apartment List shows a one-bedroom at $2,692, available now, feed updated this morning. Agrees.
  - **2900 Nostrand 2M: probably gone.** The building's own site (29 Hundred) lists 24 units and 2M is not one of
    them; the cheapest one-bedroom is 3A at $2,700.
- Nothing was repriced above $3,000. Price moves shown on the pages: 1710 Newkirk down $150 (Nov 4), 10 Wendell down
  $350 (Nov 9), 204 Sherman down $25 (Nov 10), 8700 25th Ave up $100 (Nov 13), 3310 Nostrand 503 down $100 (Nov 11).

### Special offers
- Glen Cove, verbatim from Trulia (the page cuts it off): "NOVEMBER-2026 FREE* Metro South Apts S1117, S1319, S1401,
  S1466* PLUS $150 OFF Monthly-months 2-11* Other Units GET $1000 OFF 1-TIME W/Move In By 11/24/26*. Metro North
  Special Apt N2322 $3550 and NOV-2026 FREE* LEASE 18 MTH NO INCREASE*$99 SEC.* *Restric", good until Nov 29. The page
  does not say whether listed prices are gross or net. The owner's site still carries October's version.
- Woodmere: "Inflation Buster Move-In Special Lease Choice Of 18 Months With No Increase* $99 Security* *Restrictions
  Apply.", good until Nov 30. No rent discount, so gross equals net.
- No broker listing states an offer or a net-effective price. All say "Price shown is base rent."

## 2. Gate facts (116 rows: 43 confirmed, 70 unconfirmed, 3 contradicting)

### Three contradictions (each would fail a gate)
- **3250 93rd St, East Elmhurst: a walk-up, not an elevator building.** City lot data for 32-50 93 Street: class C1
  (walk-up), 4 floors, 39 units, 1925. Our reference file had matched the neighbouring lot (32-30 93 St, 6 floors,
  elevator). Older listings for the address on Zumper say "Walk-up".
- **770 Ocean Pkwy 2O (co-op): probably no dogs.** Trulia's field says small dogs allowed, but the same listing's
  description says only "Cats allowed." Older listings for the building say "Sorry: no dogs." and "No pets allowed."
- **10 Park Ter E 6G: dog policy contradictory.** Trulia's field says small dogs; Apartment List (same broker phone,
  same day) says "not pet-friendly"; an older listing says "Cats allowed; sorry, no dogs."

### Dog weight limit
- **One number: Fairfield Estates at Woodmere, 30 lb** (owner's site; $35 a month per dog, $400 deposit). Passes.
- Every other listing gives the size-only wording **"Cats, small dogs allowed"** with no number (25 buildings; passes the
  size-only rule, needs a tour question). The two contradictory buildings give no number either. Long Beach: unknown.
- Leads not usable as facts: Miramar (405 W 206th) is said to have a 40 lb limit on CityRealty, and Manton House
  (139-05 85th Dr, co-op) is said to bar pets on several sale listings. Both came from search summaries of pages that
  refuse our requests, so both are recorded as unconfirmed with the caution in the quote column.

### Elevator
Confirmed from a page for 25 buildings (10 of them from the earlier capture, since tonight's refetch was blocked). Not stated: 1256 Ocean Ave (8 floors) and 139-05 85th Dr (6 floors), where the
6-floor asterisk rule applies; Long Beach unknown; 3250 93rd St contradicts.

### Floor
**Confirmed for one unit only: 204 Sherman 4 ("4th floor").** Everything else is `unconfirmed` with a reading and the
reason. Units whose number says nothing about the floor, where a ground-floor unit is possible: 1710 Newkirk 4,
2611 W 2nd St 5, 10 Wendell St 20, 139-05 85th Dr 1, 100 W 139th 27A (6-floor building, so not floor 27),
3250 93rd A3, 490 Ocean Pkwy 64, 3660 Waldo J2, 408 W 130th 61, and the three plan-level rows.

## 3. Ratings (29 rows: 16 with an Openigloo rating, 13 `none_found`)

Openigloo embeds only the five newest reviews per building, so `reviews_read` is at most 5. Window for "last 6
months": 2026-05-15 onward.

| Building | Rating | Reviews | In last 6 months | Negative, last 6 months |
|---|---|---|---|---|
| 2419 Adam Clayton Powell Jr Blvd | 1.81 | 2 | 0 | 0 |
| 490 Ocean Pkwy | 2.12 | 1 | 0 | 0 |
| 137 W 137th St | 2.40 | 6 | 0 | 0 |
| 3660 Waldo Ave | 2.53 | 9 | 1 | 1 |
| 204 Sherman Ave | 2.62 | 1 | 0 | 0 |
| 408 W 130th St | 2.75 | 13 | 0 | 0 |
| 1256 Ocean Ave | 2.91 | 10 | 1 | 1 |
| 100 W 139th St | 3.16 | 10 | 0 | 0 |
| 2611 W 2nd St | 3.25 | 1 | 0 | 0 |
| 1710 Newkirk Ave | 3.47 | 5 | 0 | 0 |
| 2121 Shore Pkwy | 3.75 | 1 | 0 | 0 |
| 3280 / 3310 Nostrand Ave (one page, two rows) | 3.83 | 3 | 0 | 0 |
| 121 Seaman Ave | 3.91 | 3 | 0 | 0 |
| 8700 25th Ave | 4.38 | 1 | 0 | 0 |
| 623 Avenue H | 4.62 | 1 | 0 | 0 |

No rating anywhere for the four Nassau buildings (Zumper and Apartment List pages are empty or missing; Trulia carries
none), nor for 770 Ocean Pkwy, 1941 Coney Island Ave, 405 W 206th, 4778 Broadway, 10 Park Ter E, 3250 93rd St,
139-05 85th Dr, 2900 Nostrand, 1802 Ocean Ave. **The non-NYC buildings in this batch cannot be judged statistically.**

## 4. Evidence items (73 rows)

management 26, none_found 11, safety_incident 10, positive 9, other 7, elevator 6, noise 3, car_crime 1. Every excerpt
was checked by script against the cached page text.

### Most serious
- **1256 Ocean Ave (rank 2, Ditmas Park):** mice or pests in all five reviews read, 2022 to Sept 2026. The newest
  (2026-09-26) also reports going without heat and water shutting off. Only one review falls in the 6-month window,
  so by the plan's rule this is "gives us pause", not an avoid.
- **408 W 130th St (rank 1, Manhattanville):** elevator breakdowns in two separate reviews (2026-01 "would not be
  repaired for weeks"; 2025-06 "breaks down occasionally"), bed bugs in two (2023, 2025), unreachable management.
  Two elevator reports, one short of the three the avoid rule asks for.
- **1710 Newkirk Ave (rank 1, Ditmas Park):** elevator outages in two reviews (2025-11, 2024-09), squatters and
  package theft (2025-09), weak heating. Sold in 2026 per a search result not read, so management may have changed.
- **3660 Waldo Ave (rank 1, Kingsbridge):** 2.53 from 9; mold, roaches, a year to return a deposit (2025–2026), noise
  with no response (2026-08). Reviewers credit a new super. Older press: a 2012 city suit over violations and 680
  violations cited in 2013 (both recorded with their dates; old).
- **137 W 137th St:** no heat or hot water for months, rats, assaults between tenants. All from 2022 or earlier.
- **100 W 139th St:** package theft weekly, pests, refused repairs (mid to late 2025); two reviews praise the
  manager's responsiveness.

Car crime: one item only, "Car vandalism nearby" at 121 Seaman Ave (2025-09), about the street.

## 5. Blocked or not done

- Trulia: 12 listing pages refused (403), as above.
- CityRealty (403 Cloudflare), Corcoran (403), Brown Harris Stevens (403) and Exit Realty (robots) were not read.
- Not used: Better Business Bureau, Patch, QNS, Yelp, StreetEasy, RentHop, Birdeye. A search suggests Birdeye has 103
  reviews for Beach Haven Apartments (2611 W 2nd St); it is not on the allowed list, so nothing was taken from it.
- City complaint and violation records were left to the separate pull, as instructed. The one exception is the
  tax-lot lookup for 32-50 93 Street and 4778 Broadway, needed because the reference file had the wrong lot or none.
- News: one web search per building (two buildings shared one). Only 3660 Waldo returned press about the building.
- Management start dates: none found. Building names learned: Miramar (405 W 206th), The Posh (1941 Coney Island
  Ave), H7 Condominium (623 Ave H), 29 Hundred (2900 Nostrand), Lawrence Towers (3280–3310 Nostrand), Beach Haven
  (2611 W 2nd St), Manton House (139-05 85th Dr).
- Other things to know: 10 Wendell St 20 has been listed since Sept 24 and reaches 60 days on Nov 23; it is a co-op
  rental with board approval and a one-month broker fee. 770 Ocean Pkwy 2O is a co-op sublet with a $350 board
  application. 3660 Waldo J2 and 408 W 130th 61 were at 39 and 37 days on market.
- Deviation from the usual status labels: plan-level rows are `live` with a note, as in batch 11.
