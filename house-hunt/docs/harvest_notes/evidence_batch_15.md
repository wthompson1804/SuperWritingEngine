# Evidence pass, batch 15 (2026-11-15, 22:47–23:05 UTC)

29 buildings in `data/reference/evidence_batches/batch_15.csv`, 32 unit rows. All 29 were worked: 19 in New Jersey
(Newark 5, North Bergen 1, North Brunswick 1, Old Bridge 1, Princeton 1, Rahway 1, Red Bank 1, Somerville 2, Union City 1,
West New York 4, West Windsor 1) and 10 in New York City (Brooklyn 9, East Harlem 1).

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_15.csv`. Raw pages: `raw/evidence_b15/`.
Scripts: `scripts/ev15_fetch.py` (refetch), `ev15_get.py` and `ev15_site.py` (robots check incl. Claude groups, then fetch),
`ev15_trulia_parse.py`, `ev15_al_parse.py`, `ev15_zumper.py`, `ev15_igloo.py`, and `ev15_write.py`, which rebuilds all
five CSVs from the cached pages with no network.

## 1. Live check (32 unit rows: 25 live, 7 blocked, 0 gone, 0 changed)

- 25 units are live at the stored price and inside the window. Latest dates: 99 Bridge 232 on **Dec 5**; Avalon Princeton
  431 on Nov 21; Rahway 1210 on Nov 18; Avalon Somerville 265 on Nov 16.
- **7 blocked.** Trulia began answering HTTP 403 after the sixteenth page and again on one retry six minutes later (other
  agents were hitting it at the same time). The seven New York units behind it could not be re-verified: 310 94th St F7,
  9949 Shore Rd 502, 8100 Bay Pkwy 211, 8635 21st Ave 4Q, 123 Linden Blvd I19Q, 3308 Glenwood Rd 14, 315 E 108th St 6G.
  All seven were read live by the harvest between 19:28 and 19:46 UTC today; gate facts for them come from that harvest
  copy and are labelled so. Only 315 E 108th St has a second source (Zumper shows an active 1-bedroom at $2,375, modified
  Nov 14, no unit number).

### Prices that are not what they look like
- **Avalon Princeton on Harrison 431: the stored $2,571 is net-effective.** AvalonBay's own unit data gives $2,805 for a
  12-month lease, $2,901 with the required $96 technology fee; $2,571 is that rent with one free month spread over the lease.
- **123 Linden Blvd I19Q: the stored $2,599 is net-effective.** The listing ends "* 2924, 1.5 ON 13.5 , 2599": gross $2,924,
  1.5 months free on 13.5 months.
- **Avalon Somerville Station 265: $2,340 is the 20-month price.** A 12-month lease is $2,430, or $2,519 with the required
  $89 fee. It is gross: net-effective equals price on every term. The "1.5 months off" offer ends Nov 16.
- Woodmont Way: its own FAQ lists $80 a month of required fees on top of rent (Apartment List shows none). One month free
  needs a 13-month lease and occupancy by Nov 24; gross or net is not stated.
- 99 Bridge 232: $2,635 base, $2,689 with required fees, 15-month lease; "1 Month Free on Select Apartments", basis not stated.
- Presidential Estates and Grandville Towers have offers (one month free; half off the first month) with no gross or net statement.
  All offer texts are verbatim in the live-check and facts files.

### Listings that need a human look
- **Grandville Towers:** Apartment List's unit rows were last updated on 2026-07-30. They may be stale. Own site is behind a bot wall.
- **8300 Boulevard East 4D:** a single co-op unit at $1,474 offered by an individual. A board will set the pet rules. Verify.
- **1483 Shore Pkwy "F"** and **1429 Shore Pkwy 2D** read as advertisements for a type of apartment in the complex, not one unit.
- **5 Beaumont Pl:** Trulia calls the unit 20B, Zumper calls the same listing 2B.
- Hoyt Tower's Trulia page was last modified Oct 16 and Presidential Estates' Sept 11. 310 94th St F7 was 38 days old at the harvest.
- 800 S 14th St 6D has no description at all beyond Trulia's boilerplate.

## 2. Gate facts (140 rows: 74 confirmed, 61 unconfirmed, 5 contradicts)

### Fails found
- **330 50th St 43L, West New York: "Fourth-Floor Walk-Up".** No elevator. Fails.
- **The Edge at Main 327 and 328, Somerville: the building's own site says "Pet-free community".** Pets are taken only in a
  few ground-floor homes in the new building (which would fail the ground-floor rule). Apartment List says dogs allowed.
  Contradictory dog policy.

### Elevator
- Confirmed from a page or record: 8300 Boulevard East, The Edge at Main (own site), and all ten New York buildings (listing
  text, Openigloo, or the city's building class and lift registration in `nyc_records_match.csv`).
- Amenity tag on Apartment List only, not repeated on the building's own site: 99 Bridge, Grandville Towers, Avalon
  Princeton, Avalon Somerville, **Woodmont Way** (its own amenity pages list no elevator).
- Implied by height but the word is on no page read: Hoyt Tower (15 stories), Rahway SkyView (unit on the 12th floor).
- **No evidence at all, and my reading is no elevator:** the three Forest Hill listings in Newark (5 Beaumont Pl, 85 Forest
  Hill Pkwy, 57 Branch Brook Pl), 800 S 14th St, Presidential Estates (garden complex with townhouse plans), 137-148 36th
  St Union City, 6122 Monroe Pl, 5801 and 5008 Palisade Ave. For these the batch file's "inferred from its height" appears
  to rest on unit numbers such as 20B and 32D, which are apartment codes, not floors.

### Floor (confirmed for 5 units only)
- Stated on a page or in the building's own unit data: Avalon Princeton 431 = **4**; Avalon Somerville 265 = **2**;
  Rahway 1210 = **12**; 8100 Bay Pkwy 211 = **2**; 330 50th St 43L = 4.
- Everything else is `unconfirmed`, with my reading and the reason in the confirm file. Two readings matter:
  **Woodmont Way 02107 reads as building 02, floor 1 (ground floor)**; and in the Hudson County broker listings the
  first digit seems to be the floor (43L is on the fourth), which would put **5801 Palisade 15C and 6122 Monroe 17R on floor 1**.
  3308 Glenwood Rd unit 14 could also be floor 1.

### Dogs
- Dogs allowed is stated for every building except The Edge at Main (above) and 8300 Boulevard East (tag only).
- A pound figure appears nowhere. **Woodmont Way states "we do not have a weight limit"** (own site). Avalon Somerville's
  site data has no maximum weight; both Avalons publish a breed list only.
- "Small dogs" with no number (passes the current gate): the 13 Trulia agent listings read live, Hoyt Tower (1 pet), Presidential
  Estates (1 pet, "Large dogs are not permitted"), and the seven blocked New York units. An older listing at 330 50th St
  said "Pet friendly 25 lbs", which suggests what "small" means to these brokers.
- No figure and no size word: 99 Bridge (Zumper: "Restrictions: None"), Grandville Towers ("see list").

## 3. Ratings (41 rows; 15 buildings `none_found`)

- Google rating as copied by Zumper: 99 Bridge 4.4 (41, pulled Oct 2024), Avalon Princeton 4.4 (7, Feb 2025), Avalon
  Somerville 4.2 (100, Feb 2025). Zumper shows about eight reviews each, nearly all 5-star, none from the last 6 months.
- Apartment List: one review each for the two Avalons and Woodmont Way. Woodmont's own site shows eight 5-star reviews it
  chose itself (newest Oct 2024).
- Openigloo for the ten New York buildings: 123 Linden Blvd 2.8 (28 reviews), 8635 21st Ave 2.1 (3), 310 94th St 2.0 (1),
  315 E 108th St 3.1 (7), 8100 Bay Pkwy 3.8 (2), 9949 Shore Rd 5.0 (1). The Shore Parkway complexes have no reviews on
  the exact buildings; reviews of sibling buildings on the same lot are recorded and labelled as such. 3308 Glenwood Rd has
  a page with no reviews. Only the five newest reviews per page are readable.
- Openigloo's "x days ago" labels are stale page text; dates were taken from the page's structured review data.
- **Only 123 Linden Blvd has any review from the last 6 months.** No New Jersey building can be judged on the 6-month test.

## 4. Evidence items (67 rows)

management 23, none_found 17, positive 9, noise 7, other 5, safety_incident 4, elevator 2, car_crime 0.

### Most serious: 123 Linden Blvd (PLG), Brooklyn (ranked 1 in its neighborhood)
- Five Openigloo reviews between 2026-06-01 and 2026-09-18, all with complaints. **Roaches in three of the five**, including
  "no pest control for approx 3 months this summer". **Elevators: "at least 1 is always out of use. Only 1 of 4 elevators
  in order at times"** and "run into issues often" (two reviews). Unresponsive management in three; "We are on our 4th
  management". Flooding in the basement and one apartment. Amenity charges ($80 a month, $700 pool pass).
- Openigloo's summary of city records: 53 evictions, 93 open violations (28 immediately hazardous), 8 court cases.
- This meets the management test (three or more tenants, same problem, last 6 months) for pests. Avoid candidate.

### Others
- **8635 21st Ave:** three reviews, all negative: no heat ever (2024 and 2025), roaches and mice, "scammy management &
  brokers". Newest is 17 months old, so "gives us pause", marked older. 32 open violations, 8 court cases (Openigloo).
- **315 E 108th St:** roaches, mice and rats, a building lockdown, noise (2022 to Feb 2025). Older.
- **310 94th St:** one 2023 review: "nonexistent maintenance, rampant theft, noise 24/7".
- Shore Parkway complexes: roaches and Belt Parkway noise in sibling buildings (2021 to 2024); one 2024 review says street
  parking is "impossible".
- New Jersey: nothing negative found anywhere. Positive Google excerpts for 99 Bridge and the two Avalons.

## 5. Blocked or not done

- Trulia: 403 from 22:48 UTC (see above). Building pages for the Apartment List buildings were therefore not read either.
- Own sites behind a bot wall: `rent99bridge.com` and `grandvilletowers.com` (403). Woodmont's RentCafe unit page: robots.txt 403.
  `re-nj.com` disallows our crawler. `hoyttower.com` redirects to an unrelated company; `plgbk.com` has a certificate error.
- Not used: Better Business Bureau, Patch, QNS, Zillow, Apartments.com, RentCafe, Google, LucidRents, homes.com.
- News: eleven web searches (address or building name plus tenants, police, fire, elevator). Nothing about any of the 29
  addresses came back. A News 12 story about a Linden Boulevard building (April 2026) is a different, four-story building
  and was discarded. Search-result text was not used as a fact anywhere.
- Three guessed Woodmont URLs returned 404 before the right paths were found on its home page.
