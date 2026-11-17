# Trulia cards: the same building on a source we can read (trawl 2, step 2)

Run 2026-11-17 (UTC). No Trulia request was sent. The pipeline was not run.

## What was considered

Trulia rows in `data/listings.csv` with `detail_level = card` and listed rent at or under $2,000: **4,213**. In the
priority areas (New Jersey, Connecticut, Brooklyn = ZIP 112xx, Long Island = Nassau/Suffolk ZIPs, Long Island City =
11101/11109/11120): **3,509** (NJ 2,577, CT 723, Long Island 137, Brooklyn 72, **Long Island City 0**: no LIC card is at
or under $2,000). 191 of them have no street address ("address not disclosed") and cannot be matched.

## Step 1: offline match (no network) — `scripts/match_trulia_cards.py`

Readable pool: every non-Trulia row in `data/listings.csv`, `data/listings_raw/*.csv` and
`data/listings_pending/zumper_opened.csv`, minus Zillow, Craigslist and the other off-limits sites (11,755 rows).
Cards and pool were keyed with `build_master.street_key` (house number + street + ZIP, unit stripped) and
`build_master.assign_building_ids` (same key, or same house number within 30 m, or a house-number range); then
`data/reference/building_crosswalk.csv` (it added no match beyond the first two).

| Area | Cards | With a readable sibling in the building | Same unit label and beds | Buildings |
|---|---:|---:|---:|---:|
| New Jersey | 2,577 | 686 | 150 | 530 |
| Connecticut | 723 | 177 | 34 | 147 |
| Long Island | 137 | 18 | 1 | 18 |
| Brooklyn | 72 | 6 | 1 | 5 |
| **All** | **3,509** | **887** (25%) | **186** | **700** |

877 of the 887 have a readable sibling that is itself a studio/1BR at or under $2,000 (1,217 such sibling rows, almost
all Zumper and Apartment List detail rows, a few Garden Communities, Garden Homes, Avalon). Those buildings already
have real listings in the data; the card adds nothing a reader cannot get from the sibling. `matched_listing_ids` holds
up to 20 sibling ids per card (the same-unit row first where there is one); `method` is `street_key`, `building_id`,
or either with `_same_unit`.

## Step 2: building search for unmatched cards

Ranked list: `data/reference/trulia_card_unmatched_priority.csv` (2,081 addressed buildings; studio/1BR cards first,
then most cards per building, then cheapest). Also searched first: the 112 cards whose Trulia URL is a `/building/`
page with a community name (Colonial Gardens, Tivoli Gardens, Treetops ...), as the likeliest to have their own site.

- **46 buildings searched** (WebSearch), 26 NJ, 14 CT, 4 Long Island, 2 Brooklyn; 160 cards covered.
- **Own or manager site found and read: 1** (livewillows.com, The Willows at Saddle Brook: affordable 20-60% AMI,
  1 and 2 bedrooms wait-listed, only 3BR leasing; nothing to capture).
- **Apartment List property pages read: 11** (8 buildings). None listed an available studio/1BR with a price: 4 had
  floor plans with no price (nothing available), 5 were soft 404s (listing removed).
- **3 buildings** have only RentCafe pages (Treetops/Oxford Realty, Birchwood at Cranbury, Willows at Spruce Run):
  off limits, not fetched.
- Everything else: only Apartments.com, Zillow, HotPads, RentHop, ForRent, ApartmentFinder, Redfin or Rentable
  pages (all off limits or terms-barred), or no page at all.
- **New apartment rows: 0.** `data/listings_raw/trulia_matches.csv` is written with the 41-column header and no rows.

Why so little: the cards at or under $2,000 are mostly small landlord buildings (2-30 units) and older garden
complexes that advertise through syndication feeds (Apartments.com/Zillow/Trulia/HotPads), not their own sites. The
web search was stopped after 46 buildings because the yield was nil; 104 of the 150-site cap remains unused.

Leads not followed (other agents' sources): Zumper building pages turned up for 405 Main St, West Haven
(`/apartment-buildings/p1609101/405-main-street-west-haven-ct`) and 112 16th Ave, Paterson (a neighbour, not a match).
Broker MLS pages (William Raveis, Brown Harris Stevens, OneKey MLS) carry some of these units; their terms were not
checked, so nothing was read.

## Outcome codes in `data/reference/trulia_card_matches.csv`

`street_key`, `building_id` (+`_same_unit`): offline match. `unmatched_offline`: no readable row, not searched.
`no_site_found`, `site_no_units`, `site_offlimits`: searched, with what was found in `notes` and the page read in
`building_site_url`. `apartmentlist_building_page` / `building_site`: rows captured (none this run).

## Requests and refusals

- Requests sent: livewillows.com 2 (robots.txt, one page); www.apartmentlist.com 11 property pages. **No refusals**,
  no host added to `raw/_host_kill_shared.json`.
- **Throttle lapse, told plainly:** the first five Apartment List pages went out about 1 s apart (separate processes
  did not share the in-process throttle). A cross-process 3 s throttle (`raw/trulia_matches/_last_hit.json`) was then
  added and every later request respected it. Apartment List's robots.txt has no Crawl-delay and nothing refused.

## Scripts

- `scripts/match_trulia_cards.py`: offline match; rewrites offline rows, keeps search outcomes. Idempotent.
- `scripts/trulia_match_fetch.py <url>`: one-page reader (robots Claude-User/`*`, off-limits list, 3 s per host across
  processes, no retry on refusal, refusal persisted to the shared kill file). Pages in `raw/trulia_matches/`.
- `scripts/trulia_match_rows.py al|site|none ...`: records each building's outcome and writes captured rows.
