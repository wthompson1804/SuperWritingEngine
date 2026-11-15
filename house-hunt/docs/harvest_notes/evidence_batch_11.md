# Evidence pass, batch 11 (2026-11-15, 21:13–21:40 UTC)

25 rows in `data/reference/evidence_batches/batch_11.csv` = 24 buildings (12 Brooklyn Ave, Valley Stream appears twice).
All 25 were worked. **None is in New York City** (New Rochelle 2, Peekskill 3, Port Chester 3, Valley Stream 1,
Middletown/Wallkill 3, Garnerville 1, White Plains 5, Yonkers/Bronxville 6), so Openigloo did not apply.

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_11.csv`. Raw pages: `raw/evidence_b11/`.
Scripts: `scripts/ev11_fetch.py` (refetch), `ev11_site.py` (robots check incl. Claude groups, then fetch),
`ev11_trulia_parse.py`, `ev11_zumper_reviews.py`, `ev11_text.py`, and `ev11_write.py`, which rebuilds all five CSVs from
the cached pages with no network. The two parse scripts and the writer read a fetch log in the session scratch folder;
if that folder is gone, refetch with `ev11_fetch.py` first.

## 1. Live check (31 unit rows: 30 live, 1 changed, 0 gone, 0 blocked)

- 25 named units are live at the stored price and inside the window. Latest dates: Boulder Pointe 0801 on Dec 14 (one day
  inside), Regency Club 0708 on Nov 30, Apex 01-202 on Nov 23.
- Changed: Park Place Towers' second row (stored $2,425, no unit). Nothing is at that price now; the nearest 1BR is 3I at $2,438.
- **Five buildings are marked live at floor-plan level only**: The Lombardi, The Atelier, Willett Point, The Azzure and
  1180 Midland. Trulia shows a plan price marked "Available Now" but 0 available units, so no unit, floor or date could be
  checked. Treat these as "call to confirm", not as verified units.
- Nothing repriced above $3,000.
- The two Zillow links in the batch (The Park at Main, The Regency Club) were not fetched; the Trulia copies were read.
- Own site read and in agreement: The Mitchell 207 ($2,781, floor 2), Fort Hill plan B4 ($2,675).

### Listings that need a human look
- **1180 Midland (Bronxville): the Trulia page was last modified 2025-10-14**, 13 months ago. Price and availability unverified.
- **1 Martine:** GDC's own site lists Line 17 at $2,675 available now; Trulia lists unit 617 at $2,775 (and 417 at $2,675
  from Jan 25). One of them is out of date.
- **The Park at Main:** own site says Floorplan D "Starting at $2400"; Trulia has unit 63 (Floorplan D) at $2,450.
- **The Azzure:** its own website is an unfinished template (placeholder Latin text, "Bali, Indonesia", 0% counters).
  Required flat electric charge of $165 a month for a 1BR on top of rent (Trulia text).
- **Hamilton Crossing:** mandatory $80 monthly amenities fee, $50 dog rent, $170 + tax parking: unit 440-0915 at $2,761
  goes over $3,000 all-in with a dog and a car.
- **The Atelier** is described as an affordable development; income rules probably apply.
- **Chateau Rive:** the description still advertises a July 26 open house for a two-bedroom. Page last modified 2026-09-29.
- Park Place Towers' page was last modified 2026-04-13 and Hudson 44's 2026-05-06.

## 2. Gate facts (108 rows: 53 confirmed, 55 unconfirmed)

- **Dog weight limit in pounds for 6 buildings**: Lombardi 50, Port & Main 75, Willett Point 50, Apex 75 (Trulia and
  Zumper), The Mitchell 100 combined for two pets, **Boulder Pointe 30** (passes the 25 lb gate narrowly).
- "Small dogs" only, no number: **Chateau Rive, 30 Broad, 12 Brooklyn Ave**. Likely below 25 lb; needs a call.
- The other 15 buildings say "Small, large" with no number: unconfirmed.
- Dogs allowed: stated for all 25 rows.
- Elevator listed for 20 rows. **Not listed for Boulder Pointe, Tor View Village and The Regency Club** (Regency Club is
  described as townhome-style; all three look like garden complexes and probably fail the elevator gate), nor for
  Hamilton Crossing and The Mitchell (both high-rises, but no page read says "elevator"). 12 Brooklyn Ave: Zumper lists
  an elevator, the Trulia unit page does not. The Park at Main: own site lists "Elevator".
- Floor: confirmed only for The Mitchell 207 (floor 2). 18 are inferred from the unit number. No floor can be read from
  Park at Main 63, Boulder Pointe 0801, Regency Club 0708, Tor View 14D and 21H, or the five plan-level rows.

## 3. Ratings (25 rows: 2 with a rating, 23 `none_found`)

- Google rating shown on Zumper: **The Regency Club 4.3/5 from 47 reviews** (pulled 2025-02-06) and **One DeKalb 4.6/5
  from 22** (pulled 2024-12-08). Zumper shows only its eight highest-rated reviews, all 5-star, the newest from late
  2024. So: 0 reviews in the last 6 months, 0 negative read, and the sample is biased. Weak evidence.
- Nothing readable for the other 22 buildings. Zumper has a building page with an empty review block for 8 and no page for
  the rest; Apartment List has two pages, both "collecting reviews"; Trulia pages carry no ratings.
- This batch cannot be judged statistically from allowed sources. Search results suggest ratings exist on RentCafe and
  Apartments.com (for example Fort Hill, Apex, Park at Main), but those sites are blocked or off limits.

## 4. Evidence items (36 rows)

none_found 21, positive 6, management 4, other 3, safety_incident 2. No car_crime, elevator or noise item was found.

### Most serious: Park Place Towers, 1108 Brown St, Peekskill (ranked 1 in its neighborhood)
- **News 12, 2026-04-07:** heat and hot water problems since January 2026, a temporary boiler, garage doors left open for
  weeks at a time, and the city manager says the property was cited with violations. Tenants held meetings.
- **Peekskill Herald, 2025-10-06:** a tenant arrested twice for package theft in September 2025; tenants counted 21
  stolen packages across 11 apartments; garage door open for about a month, front door not always locking, heat out in
  winter. The owner is named as Alma Realty, which New York City sued in 2023 over code violations in 13 buildings.
- The newest report is 7 months old and the 2025 one 13 months, but the same complaints recur across both, and the
  building only opened in spring 2024. This looks like an avoid candidate.

### Others
- Tor View Village: 2020 fair-housing suit over refusing emotional support animals and not waiving breed limits and pet
  fees; a 2010 Justice Department settlement is mentioned in the same article. Old.
- Regency Club and One DeKalb: three positive Google excerpts each via Zumper (2023–2024).

## 5. Blocked or not done

- Peekskill Herald "Park Place Tower tenants report ongoing problems": HTTP 403, not read.
- `willettpoint.com`: 403. `hudson44.com`: disallowed by robots.txt for us. `portandmain.com`, `30broad.com`,
  `boulderpointeapts.com`, `torviewvillage.com`, `regencyonhudson.com`: guessed addresses that did not resolve.
  `hudsonparkny.com` is a different building and was discarded. No own leasing site was found for the remaining buildings,
  which is why most dog limits are unconfirmed.
- Apex: a resident post on HamletHub about break-ins and car vandalism came up in search; the page is JavaScript-only
  (as batch 6 found) and nothing from it is recorded.
- Not used: Better Business Bureau and Patch (disallowed for us), Zillow, Apartments.com, RentCafe, ForRent, HotPads.
- News coverage was checked with one web search per building. Only Park Place Towers and Tor View returned anything about
  the building itself. No court or code-enforcement record was looked up.
- Management start dates were not found for any building.
- A deviation from the usual status labels: plan-level rows are `live` with a note, because the page still shows the
  price as available; they are not verified units.
