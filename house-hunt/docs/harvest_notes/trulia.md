# Trulia harvest notes (2026-11-15)

Script: `scripts/h_trulia.py`. Output: `data/listings_raw/trulia.csv`. State: `raw/trulia/_state.json`
(ZIPs done, every card, every detail page fetched). Blocks would be logged to `raw/trulia/_blocks.log`; none occurred.

## robots.txt (read 18:10 UTC, cached in `raw/trulia/`)

- Only a `User-agent: *` group applies to us. There is no group naming ClaudeBot, Claude-User, Claude-SearchBot or
  anthropic-ai, and no `Crawl-delay`. Throttle used: 2.2 s between requests, one process.
- Not disallowed, and used: `/for_rent/<zip>_zip/`, the `<a>-<b>_beds/` and `<a>-<b>_price/` segments, `<n>_p/`
  pagination, `/home/<slug>-<id>` listing pages, `/building/<slug>-<id>` building pages.
- Disallowed, and not used: `/building/*_li`, `/r/*`, `/*_xy/`, `*_amenities*`, `/*_movein/` (the move-in date filter),
  `/*_label/`, `/*_poi/`, `/api/`, `/graphql`, `/_next`, `/json/search`, `/search`, `/pictures/` (except the
  `thumbs_*/zillowstatic/fp/` photo paths; photo URLs are recorded but never fetched), `/n/pr/`, `/voices`, `/sitemap/`.

## URL patterns

- Search: `https://www.trulia.com/for_rent/<zip>_zip/0-1_beds/0-3000_price/` then `.../2_p/`, `.../3_p/` (40 per page).
  Confirmed against the page's own `searchData.details.filters` (price max 3000, bedrooms max 1).
  `STUDIO,1_beds` is **not** valid syntax: the site silently drops it. Segment order doesn't matter.
- Data is read from the `__NEXT_DATA__` JSON (`props.searchData.homes`; `props.homeDetails` on detail pages).
  `nearByHomes` (other ZIPs) is ignored. Room-for-rent cards are skipped.
- To save disk the cached file keeps only the `__NEXT_DATA__` script tag, not the page layout.

## Coverage

- Search: **all 1,048 ZIPs** in `search_grid.csv`, 1,113 requests, every one HTTP 200. 806 ZIPs had at least one
  result; the largest had 203 (6 pages), so no result cap was hit.
- 10,189 cards (8,022 single-unit `/home/` listings, 2,167 `/building/` communities).
- Detail pages: detail and building pages are allowed by robots.txt and fetch cleanly as plain HTML (no bot wall in
  812 requests). By the coordinator's instruction only a target list was fetched, not everything:
  `data/reference/detail_targets_trulia.csv`, nearest-first. **774 of its 1,260 pages were reached** (rows 1–774 of
  the file) before the 19:55 UTC stop; 45 more nearest-ZIP pages had been fetched earlier while testing. All were 200,
  none gone, none dropped. The remaining 486 targets are still `detail_level=card`.
  Resume with `python3 scripts/h_trulia.py --targets data/reference/detail_targets_trulia.csv` (already-fetched pages
  are reused from cache for 20 hours; about 3 s per remaining page, roughly 25 minutes).
- Rows in the CSV: **10,565** = 9,362 `card` + 716 `detail` + 461 `building_unit` + 26 `building_floorplan`.

## detail_level values

- `card`: search-results card only. Price, beds, address, coordinates, photo, and a pet hint come from the card.
  **Price and facts are not verified on the listing page**; the note column says so. For a building card the rent is
  the low end of the filtered range. `dogs=yes` on a card comes from the card's "Dogs & Cats"/"dogs allowed" tracking
  text; no card ever gives a weight limit, elevator, floor or date.
- `detail`: a `/home/` page was fetched; price and date are from that page.
- `building_unit`: a `/building/` page was fetched; one row per unit that is studio/1BR at ≤ $3,000, with the unit's
  own price and availability date. `building_floorplan`: the page listed floor plans without units.
  A building card becomes several unit rows, which is why the row count grew.

## Fill rates

| field | all rows before targets (10,175) | all rows after (10,565) | target rows before (1,260) | target rows after (1,650) | fetched pages only (1,203 rows) |
|---|---|---|---|---|---|
| dogs yes/no | 42.6% | 47.9% | 53.2% | 84.5% | 96% (767 yes, 384 no, 52 unknown) |
| dog weight limit | 0% | 0.6% | 0% | 3.7% | 5% |
| elevator = yes | 0.2% | 6.9% | 0.2% | 30.3% | 43% |
| unit floor | 0% | 1.0% | 0% | 6.3% | 9% |
| building floors | 0% | 0% | 0% | 0% | 0% |
| available date | 0.3% | 9.1% | 0.2% | 56.5% | 80% (708 "now") |
| parking type | 0.1% | 4.9% | 0.2% | 30.4% | 43% |
| parking fee | 0% | 2.1% | 0% | 13.2% | 18% |
| pet rent | 0% | 2.3% | 0% | 14.5% | 20% |
| other fees JSON | 0.2% | 6.2% | 0.3% | 38.7% | — |
| utilities included | 0% | 0% | 0% | 0% | 0% |
| laundry | 0.2% | 5.7% | 0.4% | 36.0% | 50% |
| listing age | 78.8% | 75.9% | 79.4% | 60.7% | 60% (building pages give no list date) |

"Target rows after" includes the 486 unreached targets, which is why those figures sit below the fetched-pages column.

## What the fields mean, and limits

- **Dogs.** From the page's structured pet cards (`DOGS: ALLOWED / NOT_ALLOWED`). A page that lists only cats
  ("Cats allowed") is left `unknown`, with the text kept. Trulia mostly states dog size as "Small" or "Small, large",
  not pounds, so `dog_weight_limit_lb` is rarely filled; the size wording is in `dog_policy_text`.
- **Elevator.** `yes` only when the page's feature list says "Elevator". Trulia never states "no elevator", so the
  column is `yes` or `unknown`, never `no`. When only the free-text description mentions an elevator or a walk-up,
  that is flagged in `notes` and the column stays `unknown`.
- **Floor.** Trulia has no floor field. It is filled only when the description says "3rd floor" and so on
  (flagged "floor from description text"). Unit numbers are not interpreted.
- **Building floors.** Trulia doesn't publish it. Always empty.
- **Utilities included.** No structured field; where the description mentions it, `notes` says
  "description mentions utilities included". Always empty otherwise.
- **Price basis.** Pages say "Price shown is base rent. Additional costs and fees may apply" → `base rent`. A few
  buildings carry a total-monthly flag. Concessions (for example net-effective rent) are in `concession_text`.
- **Availability.** `now`, or an ISO date. Year-less dates ("Dec 1") are given the next occurrence. Building floor plans
  marked "Available Soon" have no date (noted).
- **Copied building facts** (223 fields, each flagged in `notes` with the source URL): `elevator=yes` is copied to
  other rows at the same street address and ZIP; a dog policy is copied only from a `/building/` page, never from
  another single unit's listing.
- `listing_type`: `/building/` pages → `managed_building`; Condo/Coop → `condo_coop`; house types → `unit_in_house`;
  a plain "Apartment" single listing → `unknown`.
- Listings are Zillow-network rentals (price history cites "Zillow Rentals" and "StreetEasy"), so expect heavy overlap
  with Zillow and, in NYC, StreetEasy.

## Odd things

- Some cards have "Address Not Disclosed"; they are kept, and never used for same-address copying.
- A listing can appear under several ZIP searches; rows are keyed by listing ID, so there are no duplicates.
- The grid's ZCTA and the listing's own ZIP can differ; `zip` is the listing's.
- 26 rows have no photo.

## "What Locals Say" (not collected)

- `/home/` and `/building/` pages embed only the neighborhood survey summary (`homeDetails.surroundings.localUGC`:
  lines such as "91% of users say it's dog friendly"), plus a link to the neighborhood page
  (`surroundings.ndpUrl`, pattern `/n/<state>/<city>/<neighborhood>/<id>/`). No resident review text is in the
  listing page's server HTML.
- robots.txt does not disallow `/n/<state>/...` (only `/n/pr/` is disallowed), nor `/home/` and `/building/`.
  The neighborhood page itself was **not fetched**, so whether the review text is server-rendered there is untested.

## Modes

```
python3 scripts/h_trulia.py                      # search all ZIPs (cards); refetches pages older than 20 h
python3 scripts/h_trulia.py --targets FILE.csv   # column url, optional building_url; one fetch per page
python3 scripts/h_trulia.py --phase detail       # every card's detail page, nearest-first (about 9 hours)
python3 scripts/h_trulia.py --reparse            # rebuild the CSV from cache, no network
```

`--reparse` does not re-apply the same-address copying; run `--targets` (cached, no refetch within 20 h) to do that.
Stops with exit code 3 on 403, 429, a CAPTCHA page or a page without `__NEXT_DATA__`.
