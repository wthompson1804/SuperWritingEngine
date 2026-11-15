# Evidence pass, batch 12 (2026-11-15, 22:47–23:05 UTC)

29 Connecticut buildings in `data/reference/evidence_batches/batch_12.csv` (Ansonia, Beacon Falls, Bridgeport 6, Brookfield,
Danbury 4, Fairfield 2, Hamden 2, Milford 4, Newtown, North Haven, Norwalk 6). All 29 were worked. None is in New York City.

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_12.csv`. Raw pages: `raw/evidence_b12/`.
Scripts: `scripts/ev12_fetch.py` (refetch), `ev12_site.py` (robots check incl. Claude groups, then fetch), `ev12_trulia_parse.py`,
`ev12_trulia_cached.py`, `ev12_al_parse.py`, `ev12_zumper.py`, `ev12_grep.py`, `ev12_text.py`, and `ev12_write.py`, which rebuilds
all five CSVs with no network. The parse scripts and the writer read files in the session scratch folder; if it is gone, rerun the
fetch and parse scripts first.

## Findings that change what can be shown

1. **The August (55 E Main St, Bridgeport): both stored units are income-restricted and on floor 1.** The building's own site lists
   #1031 on plan "Stern Watch - B1.A -100" and #1054 on "Soft Shore - S1.C -80", each under "Floor 1" with "Income Limits Apply. Build
   for Connecticut Income Qualification required." The program page reserves these for renters earning 80% to 120% of area median
   income (studio at 80%: one occupant up to $87,808). Market-rate 1BRs start at $2,860 base plus $104 in required fees. The unit data
   shows floors 1 to 4 only.
2. **Ansonia On Main: the address is wrong and "66C" is not a sixth-floor unit.** The manager's own listing (Blue Brook Properties)
   shows the $1,500 unit as "66 Main St - Apt C". No page lists an elevator; the height inference came from misreading the unit label.
3. **Trulia blocked this batch after 17 requests (HTTP 403).** Seven unit rows in six buildings could not be re-verified: Carmen Romano,
   SoNo 19 Day, Wall Street Place (2), 93 Richards, Harbourside SoNo, Soundview Norwalk. Each `blocked` row cites the harvest's capture
   from about an hour earlier (21:47–21:59 UTC), when every one of these units was listed at the stored price. Gate facts for these six
   come from those captures and say so.
4. **Carmen Romano Apartments (North Haven): possible 55+ and income-restricted community. Not verified.** Search results describe it
   that way; the town's page failed to load and After55 is blocked, so nothing is recorded as fact. Needs a phone call before it is shown.
5. **Wall Street Place (Norwalk): stored units look income-tiered.** Both are on plan "A1-70"; the same plan as "A1-80" costs $2,479.
   News 12 (2024-10-18) describes "155 apartments at all income levels". Not confirmed on a leasing page (Trulia blocked).
6. **Possible first-floor units:** Brookfield Village 6108 and 1 Kennedy Flats 2117 and 2119 (four-digit numbers that read as building,
   floor 1, unit). Unconfirmed either way.
7. **Elevator not confirmed** for Ridgeway Place (1973, unit labels like 71A; no page lists one) and Soundview Norwalk (not listed), as
   well as Ansonia.
8. **Broadmoor (Hamden): the listing record was last modified 2026-01-27**, and only one studio is listed in a 498-unit complex. Its dog
   limit is exactly 25 lb. 5545 Park's record dates from April 2026; Metro Point and Metro on Broad from August 2026.
9. **Covered Bridge (Newtown): owner in Chapter 11, property being sold** (sale broker's page). Seven 3-storey buildings. Floor-plan
   level listing only.

## 1. Live check (45 unit rows: 37 live, 1 changed, 7 blocked, 0 gone)

- Changed: Alto Fairfield Metro 402A, $2,335 to $2,343.
- Floor-plan level only (price shown as available, 0 units listed, no date): 1269 Main Street, The Siena, Covered Bridge, and
  Broadmoor's 1BR row. These are `live` with a note, as in batch 11; they are not verified units.
- Last day of the window (Dec 15): Brookview East BC-406, Whitney Towers 306, Metro 121 121-2T.
- Confirmed on the manager's own page: Scribe 508 and 446 (SightMap), The August 1031 and 1054, Brookview BC-603W, BC-519W, BC-524
  and BC-406 (BRT's AppFolio list), Arcade 302 (Felner's list), Ansonia 66C (Blue Brook's list).
- Scribe's prices are quoted for a **24-month lease**; required fees add $100 a month.
- The Arcade's second row has no unit number and is probably unit 302 advertised twice (Trulia counts 1 available unit of 23).
- Nothing repriced above $3,000.

## 2. Gate facts (136 rows: 79 confirmed, 57 unconfirmed)

- **Floor confirmed for 5 units only:** The August 1031 and 1054 (floor 1), Scribe 508 (5) and 446 (4), Brookview II BC-603W (6, from
  its floor-plan name "BCW-A1-6th"). The other 40 rows are `unconfirmed` with the reading and why.
- **Dog weight in pounds:** The August 100 (combined, two pets; own FAQ), Scribe 50, Alto 75, Ridgeway 80, Broadmoor 25, 1 Kennedy
  Flats 50 (Apartment List) or 80 (Trulia). Scribe, Alto and Ridgeway figures come from Trulia captures made at 21:48–21:51 UTC.
- **"Small dogs" only, no number (passes under the current rule):** City Trust, 1269 Main, Soundview Bridgeport, The Siena, Arcade,
  Brookview II, Brookview East, 5545 Park, Soundview Norwalk. The 25 lb stored for Brookview East could not be traced to any page.
- **No limit stated (14 buildings):** see `confirm_batch_12.csv`. Metro on Broad's own page says "breed and size restrictions" while
  Trulia says none.
- Dogs allowed: stated for all 29.

## 3. Ratings (29 rows: 5 with a rating, 24 `none_found`)

Google ratings as copied by Zumper: Harbourside SoNo 4.9 (90 reviews), Whitney Towers 4.8 (14), Brookview II 4.3 (14), Brookview
East 3.6 (18). Apartment List: 1 Kennedy Flats 5.0 from 1 review, no text. Zumper pulled the Google figures in late 2024 and shows
only top-rated reviews, so there are 0 reviews from the last 6 months and 0 negatives read. Weak, biased evidence; this batch cannot
be judged statistically from allowed sources.

## 4. Evidence items (36 rows)

none_found 22, positive 7, other 6, management 1. No car_crime, elevator, safety_incident or noise item was found. Nothing alarming
about tenant conditions surfaced for any building.

## 5. Blocked or not done

- Trulia: 403 from the 18th request on; one retry also 403; stopped.
- Own sites returning 403 (bot wall): 1kennedyflats.com, ridgewaydanbury.com, altofairfieldmetro.com, brookfieldvillageapts.com,
  5545park.com, harboursidesono.com, broadmoorapts.com. AppFolio detail pages are disallowed by robots.txt (list pages were read).
- 93richards.com now serves unrelated spam and was discarded. Zumper's page for 32 Prospect Ave is a different property and was discarded.
- Not used: Better Business Bureau, Patch, Zillow, Apartments.com, RentCafe, HotPads.
- News was checked with one web search per building or small group; Ansonia had none of its own. No court or code-enforcement lookup.
- Management start dates were not found for any building. Batch-file managers differ from page data for Ridgeway Place and Alto
  (pages say Jones Street Residential).
