# Harvest notes: new sources, trawl 2 (2026-11-17)

Step 4 of `docs/TRAWL_2_PLAN.md`: probe new, permitted sources for studios and 1BRs at or under $2,200 listed base
rent in New Jersey, Brooklyn, Connecticut, Long Island and Long Island City, and harvest the ones that pass. The full
probe table (host, what it has, robots verdict, terms verdict, decision) is in `docs/SOURCES.md`, section
"Trawl 2 new-source probe (2026-11-17)".

## Probe summary

- 42 hosts probed (log: `raw/new_sources_probe/_probe.jsonl`, 52 entries; captures alongside; www.appfolio.com counted as a terms source).
- **Passed and harvested: 1** (Openigloo).
- **Failed on terms (automated collection prohibited): 12**: AppFolio listing terms, RealtyMX broker template
  (TriBro), Douglas Elliman, Nest Seekers, Highline Residential, Rent Own Sell, Rental Beast, Rentable, VeryApt,
  Redfin, Heatherwood, plus the IDX "not through automated or high-volume means" clause on Elliman and Highline.
- **Failed on robots (Claude groups disallow): 4**: Raveis, Bohemia Realty Group, Princeton Properties, Listings Project.
- **Refused (403), now in `raw/_host_kill_shared.json`: 8**: howardhanna.com, bhhsneproperties.com, danielgale.com,
  kw.com, signaturepremier.com (on the terms page), cityrealty.com, homes.com, prgrealestate.com (on the home page).
- **Terms not verified within the page budget, so not used: 6**: Compass, Coldwell Banker, Weichert, OneKey MLS,
  NJMLS, PropertyClub.
- **No unit-level data or leasing through walled platforms: 4**: Edgewood (floor plans only; RealPage), Sanzari and
  Carabetta (RentCafe), Kislak (commercial).
- **Not reached (network, not refusals): 4**: idealpropertiesgroup.com and midislandapartments.com (proxy 502),
  morganproperties.com (reset), eaglerockapts.com (redirects to unreachable plain http). 1898leasing.com is parked.

**For the coordinator:** AppFolio's listing terms (`https://www.appfolio.com/terms/listings`, linked from every
`*.appfolio.com/listings` page) forbid using "any robot, spider, or other automated device, process or means to
access, retrieve, scrape or index any portion of the Services". The working note that AppFolio `/listings` index pages
are allowed needs a decision from Will; nothing new was harvested from AppFolio here. The same applies to RealtyMX
broker sites (TriBro's terms forbid scraping), which the 2026-11-17 live check read once.

## Openigloo (`scripts/h_openigloo.py` → `data/listings_raw/openigloo.csv`)

- **Access.** robots.txt groups for ClaudeBot and Claude-User allow all but `/api`, `/_nuxt`, `/internal`. Terms of
  use have no clause on automated access; they bar copying or republishing content, so the CSV holds facts only
  (price, unit, date, pet policy, amenity flags, building height) and short floor excerpts; no descriptions or photos
  are copied (the first photo's URL is kept as a link, as in the contract). 3.5 s between requests, one try per URL.
  150 responses logged: 122 × 200 and 28 × 404 (see below); no 401/403/429 or wall.
- **URL patterns.** Search: `/apartments/brooklyn/{studio|1-bedroom}?page=N` (21 and 34 pages) and
  `/apartments/queens/long-island-city/{studio|1-bedroom}?page=N` (3 and 7 pages), 18 cards per page, cards in the
  Next.js flight payload. Unit page: `/unit/nyc/<slug>/<addressSlug>`.
  The JSON-LD item URLs on search pages (`/unit/brooklyn/<uuid>/...`) return 404; the first detail pass used them
  (28 wasted 404s) before switching to the site's own link form.
- **Price.** The JSON-LD `price` on search cards is the **net-effective** rent (after "2 months free" etc.). The CSV
  uses `activeListing.grossRent` from the unit page as `listed_rent`; `promotion` goes to `concession_text`, and the
  net figure is in `notes` where it differs. Selection for unit pages used gross ≤ $2,200.
- **Coverage.** 1,125 studio/1BR cards seen (Brooklyn 930, LIC 168, plus 27 without a gross rent, all net > $3,000).
  **27 rows at or under $2,200, all Brooklyn**; **0 in LIC** (cheapest LIC studio card is well above $2,200).
  Studios 24, 1BR 3. Rent bands: ≤ $2,000: 21 (all studios); $2,001–2,200: 6 (3 studios, 3 1BR).
  Neighborhoods: Bath Beach / Gravesend / Bensonhurst (Shore Haven complex, lister Revona: 17), Midwood,
  Prospect Lefferts Gardens, Flatbush, Kensington.
- **Fill rates (27 rows).**
  - available date: 27/27 (100%), but only **7 fall in the window** (now–2026-12-15); 20 are "future listings"
    with dates of 2027-01-01 or 2027-02-01 (Openigloo says "not available yet"), stated in `available_date_text`.
  - dogs: 0/27 stated. 8 rows have `petPolicy=allowed` (pets, not dogs) in `dog_policy_text`; `dogs=unknown`.
  - elevator: 11/27 yes (9 from the building-amenity flag, an aggregator statement; 2 also or only named in the listing
    text). A false amenity flag is not read as "no elevator". 0 rows say no elevator.
  - floor: 3/27 stated in the listing text (5th, 6th, and "First Floor Unit" at 160 Fenimore St #1K). The rest are
    blank; unit labels (6F, 3C, ...) are left to `gates.py` / the unit-numbering conventions.
  - building floors: 27/27, from Openigloo's building record (city open data; noted).
- **Oddities.** Shore Haven rows include near-duplicate addresses that look like feed typos for the same building
  ("2612 West 2 Street #6F", "2612 West Street #6F", "2611 West 2 Street #6F"); kept as separate rows, each with its own
  page. Several listing texts say "Photos may depict similar units" and list possible application, amenity or guarantor
  fees without amounts (noted).
- **Rerun.** `python3 scripts/h_openigloo.py all` (cached pages are reused; `list` rewrites `raw/openigloo/_cards.jsonl`
  from the cache; `build` writes the CSV, keeping `first_seen`).

## Files written

- `scripts/h_openigloo.py`, `data/listings_raw/openigloo.csv`, `raw/openigloo/`
- `raw/new_sources_probe/` (probe captures and log), `raw/h_edgewood/` (one Edgewood property page)
- `raw/_host_kill_shared.json` (8 hosts added), `docs/SOURCES.md` (appended section), this note
