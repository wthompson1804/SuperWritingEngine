# Region pass: Nassau County, NY (building-first)

Last run 2026-11-15 (two agents; the second continued the first's work, same files and columns).

- Script: `scripts/h_region_nassau.py`, driven by the hand-curated `scripts/h_region_nassau_buildings.json`
  (one record per building: facts, source URL, verdict, and where its unit rows come from).
  Re-run rebuilds both CSVs from cache; aggregator pages older than 48 h are refetched.
- Output: `data/listings_raw/region_nassau.csv` (126 rows), `data/reference/region_buildings_nassau.csv` (102 buildings).
- Raw pages: `raw/region_nassau/` (leasing sites, robots.txt), `raw/trulia/`, `raw/apartmentlist/`, `raw/zumper/`,
  `raw/mgmt_fairfield/`, `raw/mgmt_greystar/`, `raw/mgmt_avalon/` (reused caches).

Gates applied when writing verdicts: dog weight limit 25 lb or more, listed rent ≤ $3,000, available by 2026-12-15,
elevator building. All-in cost and ground-floor checks are left to the gate script; the facts are in the rows.

## Result

| Verdict | Buildings |
|---|---|
| pass_with_units | 4 |
| unconfirmed (one gate fact not on any allowed page) | 35 |
| fails (reason recorded) | 60 |
| blocked | 3 |

Passing with units in the window (10 rows):

- **Fairfield Estates at Woodmere**, 37 Woodmere Blvd: elevator stated on Fairfield's page, dogs $35/month with a
  **30 lb** limit (was a fail at 40 lb, passes at 25), gas heat and hot water included. Studio from $2,235,
  1BR from $2,845 / $2,900 / $2,980. Floor-plan rows only (Fairfield publishes no unit numbers, floors or dates;
  Trulia marks them available now).
- The Promenade at Lynbrook (2 rows), The Promenade at Valley Stream (1), Village Lofts, Hempstead (2): from the
  first agent; Trulia building pages, no weight number stated ("large dogs allowed").

Best unconfirmed leads (one phone call each would settle them):

- **Cornerstone Westbury**, 461 Railroad Ave (Greystar, built 2023, 4 storeys): studios 1306, 1307 (floor 3) and
  1206 (floor 2), base rent $2,825 to $2,995, about $90 required monthly fees, dogs with **no weight limit**
  ($75 per pet), special "1 month free on base rent" (prices shown are gross). Elevator is not stated on the leasing
  site, Greystar, Apartment List or Trulia. All-in is likely over $3,000 before the concession.
- **233 Shore Rd, Long Beach** (40 units, outdoor pool, one free parking spot, no fee): studios $2,100 to $2,150,
  1BR $2,400, available now. Trulia says small dogs, no number; elevator not stated.
- **315 West Broadway, Long Beach** (on the boardwalk, 3 storeys, 1927): studio 3C $2,000, 1BRs 1L $2,500 and
  1H $3,000 (first floor). Large dogs allowed, "$500 off monthly during first lease term" (unclear whether listed
  prices are before or after). Elevator not stated.
- **25 Franklin Blvd #4P, Long Beach**: 1BR $2,400, "Pets Welcome (Up To 35 Lbs)", heat, gas and water included.
  Elevator and date not stated.
- **Boardwalk Apartments, 210 Shore Rd** (East Gold): studio $2,450 available 2026-12-07 on Apartment List; leasing
  site returns 403, so dog policy and elevator are unknown.
- **Surfview Towers** listing (address withheld): 4th-floor 1BR $2,544, elevator stated, small dogs, no number.
- Seven more Long Beach boardwalk-area unit listings with the address withheld ($2,260 to $2,700; "small dogs" or
  "case by case"; several mention a pool and laundry on every floor, one says "high rise"); elevator not stated.
- **Fairfield Estates at Lynbrook Village**, 140 Broadway: dogs 30 lb, 1BR from $2,650, heat and hot water included;
  elevator not stated (1924 building, may be a walk-up).
- Fairfield Metro at Glen Cove (studios from $2,650) and Fairfield Metro at Mineola (studio $2,955): elevator yes;
  Trulia says small dogs, Fairfield's pages give no pet policy or weight number.
- Fairfield Estates at Rockville Centre, 555 Merrick Rd (3 storeys with elevator, 1BR from $2,675 on Fairfield's
  page): Trulia says no pets, Fairfield's page is silent.
- 12 Brooklyn Ave, Valley Stream (this is Sun Valley Towers) and The Vantage at Valley Stream: from the first agent.

## Method

1. Leads file and the earlier aggregator CSVs (Trulia, Zumper, Apartment List, Greystar, Avalon, Fairfield) filtered
   to Nassau ZIPs.
2. **Trulia detail sweep**: every Nassau Trulia card at or under $3,000 (307 pages) was fetched and parsed for
   elevator, dog policy and description text; anything with an elevator hint and dogs not refused became a record.
   Tally of the 307: 217 say no dogs; 74 say dogs allowed; an elevator is stated on 31.
3. **Trulia ZIP enumeration with no price cap** (`/for_rent/<zip>_zip/0-1_beds/`, 55 Nassau ZIPs) to list every
   managed building Trulia carries, including those above the cap. Each new building's own Trulia page was then
   read for its lowest studio/1BR price, elevator, pet policy and specials (so price failures are from the
   building page, not the search card).
4. Apartment List city pages for 47 Nassau towns (cached): only 16 named communities, all already recorded.
5. Fairfield Properties: all 63 Nassau community pages (cached) were scanned for "elevator", pet policy and prices.
6. Leasing sites read directly where they exist and allow it (robots.txt checked for `*` and the Claude groups).
   Web search was used only to find buildings and site addresses.

## Towns covered

Valley Stream, Lynbrook, Rockville Centre, Floral Park, Mineola, Garden City (incl. Stewart Manor), Hempstead,
West Hempstead, Great Neck / Great Neck Plaza, Long Beach, Lido Beach, Island Park, Oceanside, East Rockaway,
Freeport, Baldwin, Hewlett, Woodmere, Cedarhurst, Lawrence, Westbury, Carle Place, Hicksville, Farmingdale,
Port Washington, Roslyn, Manhasset, Glen Cove, Uniondale, East Meadow, Plainview, Bethpage, plus Massapequa, Merrick,
Bellmore, Wantagh, Levittown, New Hyde Park, Elmont, Franklin Square, Syosset, Jericho, Woodbury (ZIP enumeration).

Towns where the enumeration found no elevator rental building with a studio/1BR listed at any price:
Oceanside, East Rockaway, Port Washington, Manhasset, Uniondale, Plainview, Baldwin (two $1,850 studios at
938/940 Atlantic Ave are on a Trulia URL form that robots.txt disallows, not fetched), Merrick, Bellmore, Wantagh,
New Hyde Park, Elmont, Franklin Square, Syosset, Jericho.

## Fairfield Properties in Nassau (weight gate re-check)

Pages that state an elevator: Estates at Woodmere (pass), Estates at Rockville Centre (unconfirmed, see above),
Metro at Floral Park (1BR from $3,125: fails price), 365 Stewart at Garden City (studio from $3,055: fails price),
Metro at Farmingdale Village (75 lb, 1BR from $3,400: fails price), The Plaza 360 Lawrence (elevator per Trulia,
from $3,140: fails price), plus Metro at Mineola and Metro at Glen Cove (elevator per Trulia).

Fairfield communities with a 25 to 39 lb dog limit and prices under the cap, but **no elevator stated** on the page
(garden or pre-war walk-up style): Estates at Lynbrook Village (30 lb, recorded as unconfirmed), Courtyard at
Farmingdale (30 lb, from $2,815), Courtyard North at Farmingdale (25 lb, no styles listed). Limits of 20 lb
(Courtyard at Hewlett, Estates at Farmingdale Village, Estates West at Farmingdale) still fail.
Other Nassau Fairfield communities (Cedarhurst, Hewlett, Woodmere Courtyard, West Hempstead, East Meadow, Mineola
Gables, Levittown, Massapequa, Sea Cliff, Greenvale) state no elevator and were not carried as buildings; their
floor-plan rows remain in `mgmt_fairfield.csv`. Fairfield publishes no unit numbers, floors or availability dates
(its unit list is on RentCafe / securecafe, bot-walled).

Eagle Rock (Mineola, Hicksville, Woodbury; Carle Place is cats only) are garden communities with no elevator
stated: not carried.

## Blocked or unresolved

- **eastgoldlongisland.com** (Boardwalk Apartments, 210 Shore Rd): HTTP 403 on the property page.
- **Executive Towers at Lido** (854 E Broadway) and **Crystal House** (630 Shore Rd): no leasing site found; listed
  only on apartments.com / forrent.com / homes.com / Zillow, none of which this pipeline may read. Search snippets
  suggest both are no-pets buildings, but that is unverified and not recorded as a fact. Phone needed.
- **Morgan Parc** (Mineola): availability loads by JavaScript; no prices in the HTML.
- metro303.com, west130.com, thealluremineola.com: 403 (first agent); facts taken from Apartment List / Trulia.
- thelangdonli.com: robots.txt disallows Claude agents; Apartment List / Trulia used.
- Zillow building pages: robots.txt has a Claude group that leaves building pages off limits. Not used.
- The Grand at Baldwin: site says "Launching Soon", nothing to read.
- Guessed domains for Sun Valley Towers, Carman Place (Hempstead), Cornerstone Yorkshire (Lynbrook), Cornerstone
  Farmingdale, The Gallery at Westbury Plaza did not resolve and they are not on Trulia or Apartment List; not examined.
- Dog weight numbers are rare: of 102 buildings, a number or an explicit "no weight limit" is on record for 9. "Small dogs" with no number is
  recorded as `small_only` and left unconfirmed, never guessed.
- Trulia's Fairfield feed shows "Dogs: Not allowed" for communities whose Fairfield page has no pet line; where
  Fairfield's own page is silent the record says so instead of treating Trulia's field as final.

## Field notes

- `price_basis` / `concession_text` carry the special-offer wording verbatim where a page had one. Net-effective
  pricing was stated only at 300 Edwards St, Roslyn ("1 free month on 11-month lease, net effective rent advertised",
  which fails on pets anyway). Avalon Great Neck: "Advertised rates include 1.5 months off".
- Pool is recorded as the page words it: outdoor at 233 Shore Rd, Avalon Rockville Centre, Fairfield Metro at
  Glen Cove, Surfview Towers ("oceanfront swimming pool"); rooftop at Morgan Parc. No page says indoor.
- Rows from Fairfield and several Trulia building pages are floor plans, not units (`unit` blank, floor unknown).
- Address-withheld Trulia listings carry approximate coordinates from the page.
