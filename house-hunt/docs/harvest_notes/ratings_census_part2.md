# Ratings census, part 2 (98 buildings) - harvest notes

Run 2026-11-16, about 00:55 to 01:20 UTC. Output: `data/evidence/ratings_census_part2.csv` (987 rows, 98 buildings).
Brief: `docs/RATINGS_CENSUS_BRIEF.md`. No review text or names collected.

## The main limit: only 57 of 98 buildings got a web search

The session's web-search allowance (200 calls, shared by all three census agents) ran out part-way. Part 2 got 57
searches, one per building, for target rows 1-54 (all CT and NJ buildings) plus Fairfield Metro at Glen Cove, Riverside
(Haverstraw) and Alvista Rise. **41 buildings, all in New York State, were not searched at all**: 30 unnamed single-address
listings and 11 named ones (1775 E 18th St, 25 West Broadway, Motif, Stella, Two Clinton Park, 41-42 Elbertson Street,
720 West 181st Street, Fort Hill Peekskill, 98-76 Queens Blvd, Continuum, Apex Hudson Riverfront). For those, the file holds
only earlier evidence and cached pages; every `not_seen` row for them starts with "NO WEB SEARCH RUN". No building got the
second search the brief allows. The limit was not worked around.

## What was done, in the brief's order

1. Offline. `data/evidence/ratings_batch_*.csv` and `ratings_round1.csv` matched by addr_key (39 found rows: 25 Openigloo,
   9 Google-as-shown-on-Zumper, 5 Apartment List). Cached Apartment List and Zumper pages for each building re-read for
   `aggregateRating` / `buildingReviews` (1 further Apartment List figure). All cached non-aggregator HTML under `raw/` scanned
   for Google-widget text ("Rating: x out of 5 ... Based on n reviews") and JSON-LD `aggregateRating`: four part-2 hits:
   The Beacon (Google widget 3.8 from 1,111, whole complex) and own-site JSON-LD figures for The George New Brunswick
   (4 from 1), Avalon Somerville Station (4.4 from 149) and Harbourside SoNo (4.9 from 11). The cached Avalon Wayne and
   Avalon Princeton on Harrison pages carry no such markup.
2. Allowed pages. No new HTTP requests were made: the earlier evidence batches had already fetched the Apartment List page,
   the Zumper building/address page and the building's own site (where one exists) for these buildings, and those cached
   copies were what step 1 read. The earlier "looked at" trail is copied into the `note` of the not_seen rows.
3. Web search, one per searched building (query in `search_query`). The search tool returns a written summary plus links,
   not a results page with star snippets, so what it "displays" is mostly Apartments.com, ForRent, RentCafe, Birdeye and
   Rentable figures. It almost never showed a Google, Yelp, Facebook, ApartmentRatings or Rent.com figure.

## Hosts

No host refused, because nothing new was fetched. Nothing added to `raw/_host_kill_shared.json`. None of the excluded sites
(yelp, zillow, apartments.com, apartmentratings, streeteasy, trulia, reddit, nextdoor, facebook, google maps) was opened;
their figures are recorded only as displayed by search, basis `search_result_display`.

## Reading the file

- Platforms written for every building: google, yelp, apartments_com, apartmentratings, zillow, apartment_list, zumper,
  facebook, rent_com; openigloo only for the 34 buildings with a five-borough ZIP. Extra platforms appear only where something
  was displayed: forrent, rentcafe, birdeye, rentable, apartmentfinder, corporatehousing, apartmentiq, uhomes, veryapt,
  own_site, manager_site_bozzuto.
- 15 `found` rows carry a review count but no star figure (note starts "COUNT ONLY"). They are not counted as a rating below.
- Two figures for one platform are two rows (Parallel 41, The George, Cosmo 440 on Apartments.com).
- Not recorded as ratings, but mentioned in notes: Apartments.com "property rating" shown with zero renter reviews (5
  buildings), RentCafe management-company ratings (Clifton & Co, Woodland Square), Zumper and Atly listing scores out of 10,
  and figures for a sister building (Brookview Commons West, Lofts at Garwood II, Metro Star at 41 Cherry St).
- `google` rows with basis `earlier_evidence` are the Google figure as embedded on a Zumper page; Zumper pulled them between
  Oct 2024 and Feb 2025, so they are 21 to 25 months old.
- No ApartmentRatings, Facebook, Rent.com or Zumper-own rating was seen for any building. That says more about the search
  tool than about those platforms.

## Counts (buildings with a displayed star rating; median of the review counts)

| platform | buildings | median reviews |
|---|---|---|
| openigloo | 25 | 2 |
| apartments_com | 23 | 5 |
| forrent | 16 | 5 |
| rentcafe | 16 | 14 |
| google | 10 | 51 |
| apartment_list | 6 | 1 |
| birdeye | 6 | 28 |
| rentable | 3 | 5 |
| zillow | 2 | 2 |
| own_site | 3 | 11 |
| yelp, uhomes, apartmentiq | 1 each | 3, 1, 4 |

67 buildings have a rating on at least one platform; 31 have none visible (1 of those has a bare review count: City Line East,
RentCafe "38 reviews"). Of the 67, the largest review count on any platform is 25 or more for 16, 10 or more for 27, under 5 for 26.

No rating visible on any platform (31):

| | CT | NJ | NY |
|---|---|---|---|
| named, searched | 5 | 8 | 0 |
| named, NOT searched | 0 | 0 | 8 |
| unnamed, searched | 0 | 1 | 0 |
| unnamed, NOT searched | 0 | 0 | 9 |

The 14 searched ones: SoNo 19 Day, 301 Bridgeport Ave, 25 Third Street, Summer Street (800 Summer St), Valeur Lofts (new),
City Line Bayonne, Ethos Kelsey (new), 6500 K Johnson Blvd (unnamed), Clifton & Co. (new), 328 Pacific (new), City Line East,
Avalon Wayne, The Mercer (new), BE / 448 Scotland Rd (new). The 17 unsearched ones are open, not confirmed empty.

## Reliability

- 41 buildings unsearched (above). 24 of them still show a rating, all from Openigloo with 1 to 10 reviews.
- Search figures come from the tool's summary of result pages: they can be stale, and twice the tool said "another listing"
  without naming the site (Liberty Bay Club 4.7/17 and Hoyt Tower 4.9/1 are filed under forrent at medium confidence).
- Match confidence: 114 high, 12 medium, 3 low (Atlas on Birdeye; Riello's Zumper page titled 100 Daibes Ct; 5550 Netherland
  Ave, whose Openigloo figure is an earlier agent's weighted mean over four neighbouring entrances).
- Static HTML only: a Google widget that loads by script would not show in a cached own-site page.
- The working scripts and the search log are in the session scratchpad, not in `scripts/` (the brief said to edit no other
  files); the CSV is the record.
