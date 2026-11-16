# Ratings census: brief for agents (2026-11-16)

Owner's request: for every building on the page, list how many reviews it has and its aggregate rating on each prominent
review platform, so we can see whether ratings exist at all, and later drop buildings with no reasonable number of reviews
anywhere. Counting and recording the aggregate (rating + number of reviews) is the job. Do NOT collect review text or names.

Targets: `data/reference/ratings_census_targets.csv` (building_id, building_name, address, city, state, zip5, hood, url,
building_url, source_site, part). You are given a `part` number (1, 2 or 3): work only the rows with that part.
101 of 295 buildings have no name (a single apartment listed at an address): search those by street address + city.

Platforms to record, one row per building per platform, whether found or not:
google (Google Maps / Business Profile), yelp, apartments_com, apartmentratings, zillow, apartment_list, zumper,
openigloo (NYC), facebook, rent_com, niche is NOT a building platform (skip). Add any other platform that shows a rating.

Method, in this order:
1. OFFLINE first. Existing files already hold some: `data/evidence/ratings_batch_*.csv`, `data/evidence/rating_standard.csv`
   (`all_sources`), evidence items mentioning "Google 3.6/145"-style figures, and cached listing pages under raw/
   (Apartment List and Zumper building pages embed a rating and review count in their page JSON; find the cached page via
   data/ranked_units.csv `raw_path` for that building_id; scripts/h_apartmentlist.py / h_zumper.py show the JSON shapes,
   read-only). Record with basis `cached_page` or `earlier_evidence` and the page URL.
2. Allowed pages: the building's own site (many embed a Google-reviews widget with rating and count), its Apartment List /
   Zumper page if not cached. Use scripts/lib.py `cached_get`; check robots; honour `raw/_host_kill_shared.json` (hosts
   that already refused) and add any new refusal; one refusal (403, 429, CAPTCHA, wall) ends that host for the session.
3. Web search: up to two searches per building, e.g. `"<building name>" <city> <state> apartments reviews` and
   `"<street address>" <city> reviews` for unnamed ones. Search results often display an aggregate rating and review
   count next to a result from Google, Yelp, ApartmentRatings, Apartments.com, Zillow, Facebook, Rent.com. Record exactly
   what the search result displays for a result that is clearly THIS building (name and address/city match), with basis
   `search_result_display`, the result's URL, and the search query. Do NOT open yelp.com, zillow.com, apartments.com,
   apartmentratings.com, streeteasy.com, trulia.com, reddit.com, nextdoor.com, facebook.com or google.com/maps pages
   yourself: their robots rules or walls exclude us. A figure seen only in a search result is lower-confidence (it may be
   stale or truncated): that is why the basis is recorded. Never guess; never carry a figure across to a different
   building with a similar name; if two results disagree for one platform, record both rows.
4. If nothing is displayed for a platform, write a row with status `not_seen` (which means "no rating was visible to us",
   not "has no reviews").

Output (write atomically, resumable): `data/evidence/ratings_census_part<N>.csv` with columns
building_id, building_name, address, city, state, platform, status [found / not_seen], rating (number, as displayed),
rating_scale (5 unless stated), review_count (integer; if displayed as "1.2K" store 1200 and note it), basis
[cached_page / earlier_evidence / own_site_widget / allowed_page / search_result_display], source_url, search_query,
match_confidence [high: name and address match / medium: name and city / low], retrieved_at, note.
Notes: `docs/harvest_notes/ratings_census_part<N>.md` (hosts that refused, how many searches, what could not be found).
Do not edit other files; do not run the pipeline; do not commit.

Report back: buildings worked; per platform, how many buildings have a displayed rating and the median review count;
how many buildings have no rating visible on ANY platform, split by named complexes vs unnamed single-address listings
and by state; anything that makes the counts unreliable.
