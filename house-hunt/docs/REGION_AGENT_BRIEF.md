# Region inventory agent brief (building-first)

Read `CLAUDE.md`, `docs/PLAN_V3_APPROVED_2026-11-15.md` (the gates) and `docs/HARVEST_AGENT_BRIEF.md` (output
columns and hard rules: robots.txt incl. groups naming Claude, crawl delays, ≥2 s per host, stop at bot walls, never
invent, never take prices or dates from search snippets, use `scripts/lib.py` `cached_get`, don't commit, don't edit
other agents' files). Project root: `/home/user/SuperWritingEngine/house-hunt`.

## Why this pass exists

The renter needs an **elevator building** (no walk-ups, no ground-floor units), **dogs explicitly allowed with any
weight limit ≥ 40 lb**, a studio or 1BR with **listed rent ≤ $2,850** (all-in must stay ≤ $3,000), **available now
through 2026-12-15**. The aggregator crawl left your region almost empty because listings rarely state elevator and
dog policy. Sifting thousands of listings is slow; elevator rental buildings are few. So work **building-first**:

1. **Enumerate the elevator rental buildings** in each town of your region: mid-rise and high-rise apartment
   communities (4+ storeys with elevators): transit-oriented developments near stations, downtown towers, waterfront
   and boardwalk buildings, converted mills and lofts with elevators, older elevator co-op/rental buildings.
   Use web search (e.g. "<town> elevator apartments", "<town> luxury apartments pet friendly", "new apartments
   near <station>"), the town's known developments, management-company portfolios, and your leads file
   `data/reference/leads/<region>.csv` (pending listings from the earlier crawl; building names and addresses there
   are good leads, their facts are not confirmed). Search results are for finding buildings only.
2. **For each building, read its own leasing site** (or the manager's page for it): availability and prices for
   studios and 1BRs, pet policy (dogs named? weight limit? breed rules? pet rent and fees), elevator and number of
   floors, parking type and fee, required monthly fees, utilities included, amenities (pool, dog run, gym, gated or
   controlled access, package room), manager. If the leasing site is behind a bot wall, try an allowed aggregator
   copy of that building (Zumper building page, Apartment List property page, Trulia building page); if none, record
   the building with what is known and `notes` saying what blocked.
3. Record every available studio/1BR at ≤ $3,000 as a row. If a building clearly fails a gate (no dogs, weight limit
   under 40 lb, no elevator, nothing ≤ $3,000, nothing available by Dec 15), still write ONE row for the building
   with the failing fact filled in and `notes` starting `BUILDING_FAILS:` so the reason is on record.
   Buildings that pass on policy but show no current availability: one row with `notes` starting `NO_AVAILABILITY:`.

Be thorough over fast: cover every town listed in your task, nearest to Jamaica, Queens first. Write output as you go.

## Output

- `scripts/h_region_<region>.py` only if scripting helps (many buildings share a platform); manual page-by-page
  collection through `cached_get` is fine. Every row must have the page URL the facts came from.
- `data/listings_raw/region_<region>.csv` with exactly the columns in `docs/HARVEST_AGENT_BRIEF.md`.
  `source_site` = the site the price came from. Fill `lat`/`lon` (Census geocoder
  https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=...&benchmark=Public_AR_Current&format=json
  or the page's own coordinates). `elevator` yes only if the page says so or the building has 6+ floors (then say
  "6+ floors" in notes). `dogs` yes only if dogs are named.
- `data/reference/region_buildings_<region>.csv`: every building you examined: name, address, town, url, floors,
  elevator, dogs, weight limit, verdict (pass_with_units / pass_no_availability / fails:<reason> / blocked), source_url.
- `docs/harvest_notes/region_<region>.md`: towns covered, buildings found and examined, what blocked, gaps.

Final reply to the coordinator, under 200 words: towns covered, buildings examined, buildings passing with units,
unit rows written, main blocks.
