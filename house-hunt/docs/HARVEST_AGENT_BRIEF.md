# Inventory harvest agent brief (shared contract)

You are one of several parallel agents harvesting **live rental listings** for one renter, Lamia. Read
`CLAUDE.md` (working rules), `docs/PLAN_V3_APPROVED_2026-11-15.md` (gates) and the row for your source in
`docs/SOURCES.md` (what access works, robots rules, crawl delays) before fetching anything.
Project root: `/home/user/SuperWritingEngine/house-hunt`.

## What to collect

Studios and 1-bedrooms with **listed rent ≤ $3,000**, anywhere in `data/reference/search_grid.csv`
(ZIPs within a 2-hour free-flow drive of Jamaica, Queens; columns zcta, lat, lon, state, drive_min, drive_miles).
Work nearest-first (sort by drive_min) so the closest inventory exists first, and write output as you go.
Collect everything that meets type and price; **do not apply the other gates yourself**. Record what the page
says so a later script can. But do record the facts the gates need, from the listing page and, where the source
has one, the building page:

- availability date or "now" (target window: now through 2026-12-15)
- dog policy text and any weight limit (dogs must be explicitly allowed, limit ≥ 40 lb)
- elevator (yes / no / unknown), floor of the unit (number, or unknown), building floors
- fees: pet rent, parking type and fee, amenity or other required monthly fees, which utilities are included
- square feet, beds, baths, unit, address, building name, manager, laundry, listing age if shown, photo URL of the first photo

## Hard rules

- **Never take a price or date from a search-result snippet or card alone if a detail page exists and is allowed.**
  If only the card is accessible, record `detail_level=card` so the gate script knows.
- Respect robots.txt, including groups that name Claude (ClaudeBot, Claude-User, Claude-SearchBot,
  anthropic-ai): those apply to us. Honour Crawl-delay. Minimum 2 s between requests to a host. Stop on 403/429/CAPTCHA;
  never work around a bot wall. Log it.
- Use `scripts/lib.py` `cached_get` for plain fetches (caches to `raw/<source>/`). Raw HTML is git-ignored; that's fine.
  For pages that need JavaScript use Playwright (Node `playwright` with the system Chromium at
  `/opt/pw-browsers/chromium`, or Python if importable), headless, same throttle, robots-allowed paths only.
- Never invent a value. Unknown is `unknown` or empty.
- Don't edit `lib.py`, `PROGRESS.md`, `SOURCES.md`, `CLAUDE.md` or other agents' files. Don't commit.
- Keep bulk output out of your context: write to disk, print counts.

## Output

1. `scripts/h_<source>.py` (idempotent, resumable; re-running updates `last_seen`).
2. `data/listings_raw/<source>.csv`, exactly these columns:
   `listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,unit,beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,dog_policy_text,dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,other_monthly_fees_json,utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,building_url,raw_path,notes`
   - `beds`: 0 for studio, 1 for 1BR. `listed_rent`: number. `available_date`: ISO date, or `now`, or empty.
   - `dogs`: yes / no / unknown. `elevator`: yes / no / unknown. `listing_type`: managed_building / condo_coop / unit_in_house / unknown.
   - `first_seen` / `last_seen`: UTC ISO time you fetched the page that the price came from.
3. `docs/harvest_notes/<source>.md`: URLs patterns used, coverage (ZIPs or cities done, listings found), fill rate of
   each gate field, what was blocked, anything odd.

## Final reply to the coordinator

Under 200 words: listings written, coverage, fill rates for dogs / elevator / floor / available date, blocks hit.
