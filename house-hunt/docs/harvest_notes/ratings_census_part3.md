# Ratings census, part 3 (2026-11-16)

Brief: `docs/RATINGS_CENSUS_BRIEF.md`. Targets: the 98 rows of `data/reference/ratings_census_targets.csv` with `part == 3`
(CT 20, NJ 34, NY 44; 64 named complexes, 34 unnamed single-address listings).
Output: `data/evidence/ratings_census_part3.csv` (992 rows: one per building per platform; 152 `found`, 840 `not_seen`).
Working files (rebuildable): `raw/ratings_census_part3/` (`offline.json`, `own_site_results.json`, `search_log.tsv`,
`search_findings.tsv`, `search_notes.tsv`, `add.py`, `assemble.py`). Re-running `assemble.py` rewrites the CSV without duplicates.

## NOT FINISHED: 24 buildings were never web-searched

The session's web-search budget (200 searches, shared by all agents in the session) ran out after 74 of my 98 buildings.
**24 buildings, all unnamed single-address NYC listings, got no web search.** Their rows come from offline sources only and
their `not_seen` rows say "WEB SEARCH NOT RUN" in `note`. They are:

20 Terrace Pl; 824 E New York Ave; 2781 Ocean Ave; 1429 Shore Pkwy; 2121 Shore Pkwy; 623 Avenue H (Brooklyn) ·
7914 Rockaway Beach Blvd; 101-19 Rockaway Beach Blvd (Rockaways) · 7525 153rd St; 142-38 37th Ave (Flushing) ·
109-10 Queens Blvd (Forest Hills) · 141-24 84th Dr; 8625 Van Wyck Expy; 153-10 88th Ave; 143-25 84th Ave; 135-23 82nd Ave (Jamaica / Briarwood) ·
12333 83rd Ave (Kew Gardens) · 66 Saint Nicholas Pl; 644 W 185th St; 273 W 131st St; 137 W 137th St; 408 W 130th St (Manhattan) ·
948 New York Ave (Brooklyn) · 31-20 54th St (Woodside).

14 of the 24 already have an Openigloo figure from earlier evidence; 10 have nothing. To finish: one search each
(`"<street address>" <city> reviews`), append with `add.py`, re-run `assemble.py`.
No building got a second search (74 searches used, one each).

## Method actually used

1. Offline: `ratings_round1.csv` + `ratings_batch_*.csv` (basis `earlier_evidence`), and the cached Apartment List / Zumper pages
   named in `ranked_units.csv` `raw_path` (basis `cached_page`: Apartment List JSON-LD `aggregateRating`; Zumper
   `buildingReviews.sources`). Every part-3 building already had an earlier ratings check, so the Zumper / Apartment List
   page step of the brief was already done by those batches and was not repeated.
2. Own sites: the 19 own-site URLs in `building_contacts_own_site.csv` (plus 4 home pages) were fetched once each with
   `cached_get`, robots checked. Only one aggregate was readable: The Brunswick's own JSON-LD (5.0 from 1, recorded as
   platform `own_site`). Whitney Towers (Birdeye) and 121 Towne (Google reviews plug-in) load their widgets by script, so no figure was in the HTML.
3. Web search, one per building, 74 buildings. The search tool returns a written summary of results plus a link list, not
   a raw results page. Figures were recorded only where the summary tied a rating and count to a named site for this building.

## Hosts that refused (added to `raw/_host_kill_shared.json`)

- `www.504glenbrook.com`: HTTP 403
- `www.loftsat335.com`: HTTP 403
- robots disallow (not fetched, not a refusal): `sonopearl.com`, `highlandsmorrisplains.com`

None of the excluded sites (yelp, zillow, apartments.com, apartmentratings, streeteasy, trulia, reddit, nextdoor, facebook, google maps) was opened.

## What makes the counts unreliable

- **Google, Yelp and Facebook are nearly invisible to this method.** The search tool does not show the Google Maps panel.
  Only one Google figure came from search (Regency on Hudson, 4.2 from 10). The other 14 Google figures are the ones Zumper
  republishes, most of them frozen in late 2024 or early 2025 (see `note`). No Yelp or Facebook rating was displayed for any building.
  `not_seen` for google / yelp / facebook therefore says very little about whether reviews exist.
- Birdeye (11 buildings) is mostly a mirror of Google, and is the best available stand-in for a current Google count. It is kept as its own platform.
- ForRent and Apartments.com share one review pool; a building with both is not two independent samples. Even so they sometimes display different scores.
- The same Apartments.com listing displayed two different scores for 3 buildings (Allure, Kensington Place, 66 Main) and Birdeye
  did for Whitney Towers: both rows are recorded, per the brief.
- RentCafe often shows a company-wide rating (Konover, Bozzuto, Denholtz, Westminster, Russo). Those were left out when the
  display said so (5 buildings). RentCafe figures that were recorded could still be company-wide where the display did not say.
- Three rows have a platform the display did not name (`unattributed_aggregator`, confidence low): Brownstones at Englewood South (2 rows), 270 Luis M Marin Blvd.
- Scales differ: VeryApt, atly and Lucid Rents use 10 (`rating_scale`). Zumper's own "expert" score and Apartments.com's
  "property rating" with zero reviews were not recorded as ratings.
- Openigloo counts are tiny (median 1.5) and 5 of the earlier rows (2072 20th Ln, 1429 Shore Pkwy) are for sibling buildings in the same complex, and one (3660 Waldo Ave) is an owner-page figure (all confidence medium).
- Many "no rating" named complexes are new buildings (opened 2024 to 2026): Bedford Creative, Lafayette, Riverhouse, 80East, Aviva, LIA, The Alary, 30 Broad.

## Side findings (not part of the census; not acted on)

- 1244 New York Ave, Brooklyn: a search result describes it as a 2-unit, 2-story building from 1910. 61 Clarkson Ave: described as a 3-story, 11-unit building. Both bear on the elevator gate.
- 30 Broad Street, Port Chester: an August 2026 article describes it as under construction with completion in early 2027.
- Regency on Hudson: a Google review claims the building had no occupancy permit while advertised.
- Kensington Place (listed as South River) is at an East Brunswick address.
- Unnamed addresses that turned out to have a building name: 475 Main St Orange = The Elks; 270 Luis M Marin Blvd = Metropolis Towers;
  26-25 4th St = The Winslow; 187 Culver Ave = The Tetris; 479 Front St = Village Lofts; 12 Brooklyn Ave = Sun Valley Towers; 5 Linden St = The Hampton.

## Per-building search notes (what was displayed but not recorded, or nothing)

- City Trust Apartments (Bridgeport, CT): search showed VeryApt "0 Reviews" and ApartmentFinder "0 Ratings & Reviews" for City Trust Apartments; Apartment List page (city-trust-apartments--1) "collecting reviews"; no rating displayed for any platform
- Brookfield Village Apartments (Brookfield, CT): RentCafe page shows only a company-wide rating 4.0 (146) for Konover Residential (not this building, not recorded); a separate "Brookfield Village (PDM)" listing at 802 Federal Rd shows 3.0 from 5 reviews (different address/listing, platform unclear, not recorded)
- Brookview Commons II (Danbury, CT): ForRent 4.9 from 14 displayed for Brookview Commons East at 30 Crosby St: a different building, not recorded
- Metro Star - Metro on Broad (Milford, CT): Apartments.com displayed "4.0" with no renter reviews (no count, not recorded); ApartmentFinder 0 reviews; Yext 4.4 is for the Metro Star brand, not this building
- Piper (Norwalk, CT): RentCafe displayed only a company rating 4.5 (about 1K reviews): company-wide, not recorded; Apartments.com "5.0 (0 reviews)" not recorded; Bozzuto reviews page exists but no figure displayed
- Lopresti School Apartments at 29 Maple Street (Seymour, CT): no rating displayed for this building on any result (Zillow, HotPads, Zumper, PadMapper listings only)
- 121 Towne Apartments (Stamford, CT): a Birdeye page titled "Lockworks Apartments" (4.1, 195 reviews) carries a review about this building's management; different profile name, scope unclear, not recorded
- 504 Glenbrook (Stamford, CT): one directory shows "0 Ratings & Reviews"; the Apartments.com 4.6 (5) shown belongs to The Parc at Glenbrook (66 Glenbrook Rd), not this building
- Allure Harbor Point (Allure at Harbor Point) (Stamford, CT): Zumper "8.9 out of 10" is Zumper's own expert score, not a resident rating: not recorded
- Bedford Creative (Stamford, CT): no rating displayed anywhere; new building (pre-leasing in 2026)
- Lafayette Stamford (Stamford, CT): no rating displayed; Apartment List "collecting reviews"; built 2024
- The Riverhouse (Stamford, CT): no rating displayed for the Stamford building (new, 2025); results for Riverhouse Westport and Mill River House are other buildings
- Lofts at 335 (Stratford, CT): CorporateHousing.com "17 ratings and reviews" and ApartmentFinder "11 ratings and reviews" displayed without a score: not recorded as ratings
- The Westporter (Westport, CT): no rating displayed (Apartment List collecting reviews; ApartmentFinder, VeryApt, RateMyApartments show none)
- Bay One (Bayonne, NJ): ApartmentFinder "11 ratings and reviews" displayed without a score
- EDGE (Bayonne, NJ): Bozzuto reviews page exists (individual reviews seen in snippets), no aggregate displayed
- Skyelofts North (Bayonne, NJ): Apartments.com says "Be the First to Rate & Review"; no rating displayed anywhere
- Avalon Teaneck (Bergenfield, NJ): Trulia "1 Review" (no score), VeryApt 0 reviews
- Rail at Bound Brook (Bound Brook, NJ): RentCafe 4.0 (182) is stated to be from other Denholtz properties (company-wide): not recorded; Apartment List collecting reviews; Meridia Main Station 1.3 (16) is a different building
- 80East | Luxury Apartments | Dover, NJ (Dover, NJ): Apartments.com "No Renter Ratings Yet"; ApartmentFinder "0 Ratings & Reviews"; new building
- The Brownstones at Englewood South (Englewood, NJ): a third result showed "223 ratings and reviews" without a score (likely ApartmentFinder); Apartment List collecting reviews; VeryApt none
- 5 Linden St (Hackensack, NJ): no rating displayed (condo building "The Hampton", 61 units); Apartment List collecting reviews
- Prospect Place (Hackensack, NJ): RentersVoice displays "78 out of 95 renters recommend" (82%), a recommend share, not a star rating: 95 reviews exist there
- 187 Culver Avenue (Jersey City, NJ): building marketed as "The Tetris"; Apartments.com "Be the First to Rate & Review"; no rating displayed
- 55 Jordan (Jersey City, NJ): LucidRents 0 reviews; Apartment List collecting reviews
- Aviva (Jersey City, NJ): no rating displayed; Apartments.com no renter ratings yet; building opened 2026
- Metrovue (Jersey City, NJ): RentCafe lists "11 Reviews" for 161 Van Wagenen Ave but the overall score displayed as "-1.0" (no usable rating): 11 reviews exist on RentCafe, score not shown; ApartmentFinder 0
- The Agnes (Jersey City, NJ): VeryApt has 1 review (no aggregate shown); Apartments.com "Be the First to Rate & Review"
- Pier Village (Long Branch, NJ): RentCafe 4.0 (445) is stated to be from other Westminster Management properties (company-wide): not recorded; a related RentCafe listing "Pier Village Urban Renewal Company LLC 2" shows 4.0 overall, count not displayed
- Avalon Maplewood (Newark, NJ): CorporateHousing "2 ratings" with no score displayed
- Newark Urby (Newark, NJ): a Yelp listing exists (seen via MapQuest, "a handful of ratings"), no figure displayed
- LIA by Vermella (Orange, NJ): Apartments.com zero renter reviews (a "4.0" property rating with no reviews, not recorded); RentCafe 4.5 (464) is company-wide for Russo Development: not recorded; opened 2025
- The District at 15Fifteen (Parsippany-Troy Hills, NJ): Bozzuto reviews page shows "64 Reviews" for this building but no overall score was displayed; RentCafe 4.5 (about 1K) is a company rating: not recorded; Apartment List collecting reviews
- RiversEdge at Port Imperial (West New York, NJ): Zumper "8 out of 10" is Zumper's own expert score, not recorded; VeryApt no reviews
- The Highland (Brooklyn, NY): ApartmentRatings page exists with zero reviews and no rating; Yelp has a single review (seen via MapQuest), no aggregate displayed
- 479 Front Street (Hempstead, NY): building is "Village Lofts Apartments" (29 units); no rating displayed on any result
- Shearwood Station (New Rochelle, NY): Zumper 9.3 is Zumper's own score, not recorded
- The Alary (New Rochelle, NY): Apartments.com shows "Property Rating 4.0" with "No Renter Reviews" (an editorial property rating, not a review aggregate: not recorded); opened 2025
- Staten Island Urby (New York, NY): LucidRents shows "19 reviews" for 7 Navy Pier Court (no aggregate score displayed); Openigloo building page exists (earlier evidence has its figure)
- Patchogue Village at Terry, an Eagle Rock Community (Patchogue, NY): Zumper 8.8 of 10 is Zumper's own score, not recorded
- 30 Broad Street (Port Chester, NY): no rating displayed; a 2026 YIMBY article describes the building as under construction (completion early 2027) while listings say available: worth a check
- 12 Brooklyn Ave (Valley Stream, NY): building is "Sun Valley Towers" (72 units, 2012); no rating displayed on any result
- 26-25 4th St (Astoria, NY): building is "The Winslow" (Hallets Point); no rating displayed; LucidRents/Openigloo results were for other addresses
- 3560 Olinville Ave (Bronx, NY): Openigloo building page displayed "No reviews yet" (85 units, 1931)
- 2072 20th Ln (Brooklyn, NY): Openigloo page for 2072 20 Lane displayed "No reviews yet" (Shore Haven complex; earlier evidence has sibling-building Openigloo figures)
- 61 Clarkson Ave (Brooklyn, NY): no rating displayed for 61 Clarkson Ave; listing sites describe a 3-story, 11-unit building (2019/2021): relevant to the elevator gate, not checked here
- 310 94th St (Brooklyn, NY): Openigloo page shows "Reviews (1)", a former tenant "Do not recommend"; no numeric rating displayed
- 1244 New York Ave (Brooklyn, NY): no rating displayed; StreetEasy result describes 1244 New York Avenue as a 2-unit, 2-story building built 1910: relevant to the elevator gate, not checked here
