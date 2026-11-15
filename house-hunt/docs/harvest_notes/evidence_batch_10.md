# Evidence pass, batch 10 (2026-11-15, 21:13–21:45 UTC)

29 buildings in `data/reference/evidence_batches/batch_10.csv`: 8 in New Jersey, 21 in New York outside the city (Long
Island, Westchester, Rockland, Mid-Hudson). No New York City buildings, so Openigloo does not apply. All 29 were worked.

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_10.csv`. Raw pages: `raw/evidence_b10/`
(`zumper_bld.json` holds the Zumper building data). Scripts: `scripts/ev10_fetch.py` (refetch listing pages),
`ev10_get.py` and `ev10_site.py` (robots check, then fetch), `ev10_zumper.py`, `ev10_al_parse.py`,
`ev10_trulia_parse.py`, `ev10_links.py`, and `ev10_write.py`, which rebuilds all five CSVs from the cache with no network
and checks every quoted sentence against the cached page (0 misses on the last run).

This batch was started by one agent and finished by another. The listing pages were refetched at 21:13–21:14 UTC; own
sites and news pages between 21:19 and 21:38 UTC.

## 1. Live check (46 unit rows)

| Status | Rows | Which |
|---|---|---|
| live, price as stored | 39 | see file |
| changed | 1 | Modera Woodbridge 608: $2,406 stored, $2,400 now |
| gone | 1 | Renaissance Bay 17D (no longer in the unit table; 24H at $2,625 remains, as do 63C and 95D at $2,450) |
| blocked | 5 | Lagrange Farms 303, North Court 206 and 208, Trail Link Collective 303 and 307 |

- Nothing was repriced above $3,000. Every live unit with a date is available on or before 2026-12-15.
- **The five blocked rows** have a Zillow page as their only link, which the brief puts off limits. No allowed copy of
  the same unit was found: lagrangefarms.com is a "Launching Soon" placeholder, lagrangefarmshvny.com
  answers 403 on robots.txt, the Trail Link sites and RentCafe return a Cloudflare challenge, and
  Zumper's North Court page shows a different unit (#307). These five cannot be shown with a verified price and date.
- **Floor-plan level only, no unit number and no date (5 rows):** The Cove (2 rows; the Apartment List entries were
  last updated in February 2024, though the own site still shows "$2,575+"), The Promenade at Lynbrook (plan S01),
  The Alary (plan "14J"), Arc House (plan "907"). Trulia's unit counter reads 0 available units for Promenade and Arc
  House while the plans say "Available Now".
- **Net-effective pricing.** Arc House's own site says "Rents reflect net effective pricing" with one month free on a
  13-month lease, so the $2,300 studio is not the monthly payment. 42 Broad's listing says approvals use "the gross rent,
  not the net effective rent", which suggests the same. Both need the gross rent before the all-in test.
- Own-site confirmation of a unit and price: Avalon Wayne (both units, AvalonBay unit pages), Parkside 2307 and Riverside
  4401 (gdcrentals.com floor-plan rows at the same price, "Available (Now)"). Everything else rests on Apartment List or
  Trulia.
- Sofi Gaslight prices are 15-month lease prices.

## 2. Gate facts (117 rows: 42 confirmed, 71 unconfirmed, 4 contradicts)

### Dogs
- **Two listings say no dogs and fail the gate:** 316 Fulton Ave #4 (Hempstead) and 310 Riverside Blvd 6J (Long Beach).
  Both Trulia pages read "Pet policy: Dogs Not allowed, Cats Not allowed". Under rule 10 these should be dropped.
- Weight limit confirmed (7): Parkside 30 lb, Riverside 30 lb, Mid Island 35 lb, Manley Court 40 lb, Sterling Parc 50 lb,
  Modera Woodbridge 120 lb, Skyline New Rochelle "No breed restrictions or weight limits". All pass the 25 lb gate.
  Parkside and Riverside pass by only 5 lb.
- "Large dogs allowed" on Trulia but no number published (5): Village at West Long Branch, Promenade, 42 Broad, The
  Alary, Arc House (one dog per home). Recorded as unconfirmed because no figure is quoted.
- "Small dogs" with no number (3): The Brompton, 25 W Broadway ("Pets considered on a case-by-case basis"), 142 Main St
  (condo, board approval needed). These may sit under 25 lb.
- A limit exists but is not published: Georgian Arms ("Breed and Weight Restrictions"). Admirals Cove shows no limit on
  Trulia, but its two sister buildings next door publish 30 lb.
- No figure on any page read: Sofi Gaslight, Highlands, The Cove, Avalon Wayne, Point at Pine Ridge, Renaissance Bay,
  Renaissance Hills, and the three Zillow-only buildings.

### Elevator
- Confirmed (10): The Cove (own site), Parkside, Admirals Cove, Riverside, 25 W Broadway, Promenade, 142 Main St, The
  Alary, Arc House (Trulia feature list), Skyline (a residents' petition about the elevators). Avalon Wayne has only an
  Apartment List amenity tag and stays unconfirmed, although its two units are confirmed on floors 2 and 3.
- **Ten buildings whose "elevator" in the batch file was inferred from a floor count look like garden-style walk-ups,
  and none could be confirmed:** Sofi Gaslight Commons, The Highlands at South Plainfield, Manley Court, Georgian Arms,
  The Point at Pine Ridge, Renaissance Bay, Renaissance Hills, Mid Island Apartments, The Village at West Long Branch,
  Sterling Parc at Middletown. The reasoning for each is in the confirm file: built between 1945 and 2002, unit numbers
  in the building-plus-letter pattern of garden courts (16C, 42A, 24H, 0672D, 25-17), wording such as "garden style
  community" (Sofi's own site) or "expansive green courtyards" (Mid Island), and no elevator in any amenity list read.
  Search-result text (not read from a page, so not recorded as fact) described Manley Court, Georgian Arms, Mid Island,
  Renaissance Bay and Renaissance Hills as two storeys and the Village at West Long Branch as three. Sofi Gaslight may be
  the exception: its own site also says "mid-rise" and a search result mentioned elevator complaints. These ten need a
  phone call before they can stay in an elevator-only shortlist.
- Unconfirmed but very likely to have one: Modera Woodbridge (units to 7xx, built 2022), 42 Broad (249 units,
  concierge), The Brompton (unit 7B), 310 Riverside ("high floor").
- Floors: only Avalon Wayne is stated on a page. The rest are inferred from unit numbers and marked unconfirmed.

## 3. Evidence items (37 rows)

| Category | Rows |
|---|---|
| elevator | 1 |
| safety_incident | 1 |
| noise | 1 |
| management | 1 |
| other | 2 |
| positive | 5 |
| none_found | 26 |

- **Skyline New Rochelle, elevator (2023-12-06).** A Change.org petition by residents asks the owner to replace the
  elevators, citing "the regular service outages of our elevators - the only access residents have to their homes". It
  closed with 70 supporters. This is a tenant allegation on a petition site, not a news report, and Change.org is not
  on the brief's list of outlets, so drop the row if only listed outlets are wanted. Skyline also has the lowest rating
  in the batch (3.3 from 284 Google reviews as copied by Zumper). The stored units 02H and 02A appear to be on floor 2.
- **The Brompton, safety_incident (2024-12-28).** Larchmont Loop: police believe a man arrested for package thefts was
  also responsible for burglaries at three buildings, 1880 Palmer Avenue among them.
- Point at Pine Ridge: one verified Apartment List review (2025-05-01, 5 stars) mentions upstairs noise and unkept areas.
- Promenade at Lynbrook: LI Herald coverage is about the motel that stood on the site until 2020 and the building's
  sale in 2022; nothing about the current building.
- One news search was run for every building (Haverstraw, Middletown, Long Beach and New Rochelle buildings shared a
  search). No article named any other address. No car-crime item was found for any building.

## 4. Ratings (31 rows)

- A rating was readable for 7 of 29 buildings. Zumper's copy of Google: Modera Woodbridge 4.7 (141), Mid Island 4.6
  (205), Renaissance Hills 4.3 (336), Lagrange Farms 3.7 (15), Skyline 3.3 (284). Apartment List single verified
  ratings: Highlands 5, Point at Pine Ridge 5, Modera 2 (no text), Renaissance Hills 5 (no text).
- **These cannot support the "last 6 months" test.** Zumper pulled the Google figures between November 2024 and
  February 2025 and shows only its eight "highest rated" review texts (four for Lagrange Farms), all 4 or 5 stars and none later than
  January 2025. The
  recent and negative columns are therefore zero by construction, not because nothing negative exists.
- 22 buildings have a `none_found` row listing the pages checked.

## 5. Blocked or not used

- Cloudflare challenge (403), not worked around: equityapartments.com, goldberg-realty.com (Manley Court, Georgian
  Arms), thepointpineridge.com, traillink.baxterbuilt.com, traillinkcollective.com, rentcafe.com.
- robots.txt answers 403: moderawoodbridge.com, skylinenewrochelle.com, lagrangefarmshvny.com.
- robots.txt disallows ClaudeBot: thevillagewlb.com (the Village at West Long Branch's own site).
- talkofthesound.com asks for a 600-second crawl delay; not fetched.
- The search tool reports that nj.com, newsday.com, northjersey.com, app.com and mycentraljersey.com refuse our
  crawler, so the main New Jersey and Long Island papers could not be searched or read. Patch, QNS and BBB were not used.
- bozzutolistens.com (Bozzuto's review page for Point at Pine Ridge) returned a server error. sterlingparcny.com's
  review page is a submission form with no reviews.
- thealary.com is a different building in Fort Myers, Florida; it was read once and discarded.
- Leads seen only in search-result text and not recorded: resident reviews on the Modera Woodbridge and Equity sites
  (one about a motorcycle taken from the Modera garage), and review-site summaries for Mid Island and Renaissance Hills
  mentioning pests and police activity. All sit on sites we could not read.

## 6. Other things worth knowing

- Sofi Gaslight Commons: the batch file names Cushman & Wakefield as manager; Zumper names Bozzuto Management.
- Zumper still lists the Village at West Long Branch under its former name, Avalon West Long Branch.
- The Promenade at Lynbrook was The Cornerstone at Yorkshire until its sale to the Birch Group (reported October 2022).
  It opened in December 2021, has four storeys, and the ground floor is the garage, so no apartment is at ground level.
- Admirals Cove opened in July 2023 (245 apartments in four buildings).
- 316 Fulton Ave #4 was cut by $100 on November 11.
- The earlier plan note said 38 unit rows; the batch file holds 46.
