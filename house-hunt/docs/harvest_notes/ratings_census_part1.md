# Ratings census, part 1 (2026-11-16)

Output: `data/evidence/ratings_census_part1.csv` (1,065 rows; 99 buildings; 148 `found`, 917 `not_seen`).
One row per building per platform for the ten core platforms (google, yelp, apartments_com, apartmentratings, zillow,
apartment_list, zumper, openigloo, facebook, rent_com), plus a row for any other platform that displayed a rating
(forrent, rentcafe, birdeye, lucidrents, uhomes, apartmentfinder, a manager's own ratings page, zumper_score).

## Not finished: 30 buildings got no web search

The web-search tool has a session limit of 200 calls shared by all agents in the session. It ran out after my 69th
search. Every named complex (63) was searched once. Of the 36 unnamed single-address listings, 6 were searched and
**30 were not** (all New York City addresses, list below). For those 30 the CSV holds only what the offline files and
allowed pages show (Openigloo for 12 of them); every other platform row says "web search NOT run".
No building got a second search.

Not searched: 1634 Flatbush Ave, 1875 Atlantic Ave, 2920 Brighton 4th St, 1483 Shore Pkwy, 96 Hart St,
3280-3310 Nostrand Ave, 2900 Nostrand Ave, 250 Clarkson Ave, 1010 Rogers Ave (Brooklyn); 103-14 Northern Blvd (Corona);
3625 Parsons Blvd, 14345 Sanford Ave, 4110 Bowne St (Flushing); 71-82 Parsons Blvd (Fresh Meadows);
33-25 Junction Blvd (Jackson Heights); 89-25 162nd St, 148-33 90th Ave, 14202 84th Dr, 89-61 162nd St (Jamaica);
8267 Austin St (Kew Gardens); 612 W 137th St, 100 W 139th St, 10 Park Ter E, 204 Sherman Ave, 949 W End Ave,
610 W 196th St, 315 E 108th St, 4778 Broadway (Manhattan); 5 Stuyvesant Pl (Staten Island); 4545 46th St (Woodside).

The six address searches that did run returned nothing new beyond Openigloo and Lucid Rents, so the expected yield
of the missing 30 is low, but it is not zero.

## What was done

1. Offline: `data/evidence/ratings_batch_*.csv`, `ratings_round1.csv`, facts/items batches, and cached Apartment List
   and Zumper pages (matched by the building's own URLs and by Zumper address slugs with matching number, street and
   ZIP). Apartment List rating read from `reviewSummary.overall` + `rating_count`; Google figure read from Zumper's
   `buildingReviews.sources.google`. 32 buildings had at least one figure offline.
2. Allowed pages: 27 Zumper address pages not checked before (10 returned 200, 17 returned 404; one new figure:
   Vermella Harrison, Google 4.5 from 419, pulled by Zumper 2024-12-07). Four own sites read (scribenorwalk.com,
   theasherstamford.com, vermellaharrison.com, theleafnewrochelle.com): no rating widget in the page source of any.
   Raw captures in `raw/ratings_census_p1/`.
3. Web search: 69 searches, one per building, 69 buildings. Bozzuto review pages (Halstead Norwalk, The Brick,
   Cobalt Lofts, The Wyldes, Birch House, Two South Willow) appeared in results and were not fetched.

## Hosts that refused

None in this part. No 403, 429, CAPTCHA or wall was met; nothing was added to `raw/_host_kill_shared.json`.
None of the excluded sites (yelp, zillow, apartments.com, apartmentratings, streeteasy, trulia, reddit, nextdoor,
facebook, google maps) was opened.

## What makes the counts unreliable

- **Search figures come from the search tool's written summary of its results**, not from a visible result card.
  The tool returns a list of links plus a prose summary that quotes figures ("4.7 (41 reviews)"). 112 of the 148
  found rows have this basis. I matched each figure to the result URL of the same site; the summary could be
  misattributing or stale.
- **Google is almost never displayed.** The search never showed a Google Business rating. All 9 Google figures come
  from Zumper's embedded copy, pulled by Zumper in Dec 2024 to Feb 2025, so they are about two years old. Yelp,
  Facebook, ApartmentRatings and Rent.com were essentially never displayed either (Yelp twice, via MapQuest). "not_seen"
  on these platforms says nothing about whether reviews exist.
- **Apartments.com shows two different numbers for one listing**: a "blended score" (renter reviews mixed with the
  site's own building rating) and a "renter rating". They can differ a lot: The Royce at Trumbull 4.4 vs 2.6,
  Prospect Park 4.7 vs 4.0, Valley and Bloom 1.3 renter rating vs 4.4 on ForRent for the same 9 reviews. Both rows
  are recorded where both were shown. Where only the blended score was shown it overstates tenant opinion.
  Where Apartments.com showed a rating with zero renter reviews (6 buildings), the row is `not_seen` with a note.
- **ForRent, ApartmentFinder and ApartmentHomeLiving are Apartments.com network sites** and repeat the same reviews.
  They are separate rows but not independent evidence.
- **RentCafe** sometimes shows a manager's company-wide rating; those were left out when the summary said so (Scribe,
  AVE Clifton, Port & Main), but an unflagged one may have been recorded as a building rating.
- **Birdeye** aggregates other sites (mostly Google). It is the nearest thing to a current Google count for 8 buildings.
- **Zumper's 0-10 score** (3 buildings) is generated by the site, not by reviews; it is under `zumper_score`, scale 10,
  and is not counted as a rating in the summary numbers.
- **Name mismatches recorded at low confidence**: 163 Franklin Street's Birdeye profile is under "The Moderne";
  Beacon Mill Village's Apartments.com profile is titled "A Place To Call Home"; Life Time Living's RentCafe row has a
  count (87) but no single overall score; The Ashton's two network figures (4.5 and 4.9) could not be told apart.
- **Stale displays**: Openigloo for 26-02 4th St shows 3.5 from 6 in search and 3.4 from 8 on the page read earlier.
- Target file quirk: Vermella Harrison's address is split across the address and city columns
  ("1100 Frank" / "E Rodgers Blvd. S Harrison"); copied as given.

## Summary numbers

Buildings with a displayed rating, and median review count among them:
apartments_com 35 (median 6); forrent 30 (6.5); rentcafe 23 (19); openigloo 15 (3); apartment_list 11 (1.5);
google 9 (149); birdeye 8 (139); yelp 2 (17.5); zillow 1 (2); apartmentratings 0; facebook 0; rent_com 0;
zumper 0 of its own.

No rating visible on any platform: 35 of 99.
- Named complexes: 13 (CT 3, NJ 7, NY 3): City Trust Collection Arcade Apartments, Metro Star Metro 121, Scribe (CT);
  Appletree Suites, Birch House, Two South Willow, Symphony, 416 Highland Ave, 500 PARQ, Centurion Sleepy Hollow (NJ);
  Arc House, Alexander Crossing, Wakefield Station Apartments (NY).
- Unnamed single-address listings: 22 (NJ 1, NY 21). 18 of these 22 are among the 30 that were never searched.

Largest review count on any platform: 34 buildings have 10 or more; 30 have 1 to 9; 35 have none.
