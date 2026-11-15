# Evidence pass agent brief (shared contract)

Read `CLAUDE.md`, `docs/PLAN_V3_APPROVED_2026-11-15.md` (gates and avoid rules) and `docs/HARVEST_AGENT_BRIEF.md`
(hard rules: robots.txt incl. groups naming Claude, crawl delays, ≥2 s per host, stop at bot walls, never invent,
never take facts from search-result snippets, use `scripts/lib.py` `cached_get`, don't commit, don't edit other
agents' files). Off limits for us: Yelp, Niche, City-Data, Reddit, Nextdoor, Zillow listing pages, StreetEasy,
Apartments.com, ApartmentRatings (bot wall), Google Maps. Project root: `/home/user/SuperWritingEngine/house-hunt`.

You get a batch file `data/reference/evidence_batches/batch_<n>.csv`: candidate buildings that rank in the top 15 of
their neighborhood (name, address, units, listing URLs, `to_confirm`). For EACH building do four things.

## 1. Is the listing real and still live? (highest priority)
Re-fetch each listing URL (bypass the cache: `cached_get(..., refresh=True)`). Record per unit: still listed?
current price, availability date, and whether they match what we stored (`rents` column). If the unit is gone,
repriced above $3,000, or not available by 2026-12-15, say so. Find the building's own leasing site if we only have
an aggregator link, and prefer its numbers.

## 2. Confirm the open gate facts in `to_confirm`
From the building's own site or its building page: does it have an elevator (and how many floors)? Which floor is
the unit on (unit numbering or floor-plan data)? Dog policy: are dogs allowed, and what is the weight limit in
pounds (must be ≥ 40 lb, or no limit)? Quote the sentence. If it can't be confirmed, say `unconfirmed`.

## 3. Tenant and public evidence, dated
Search for what residents and records say about the building, its parking and its management company. Sources that
are allowed: the building's reviews as shown on Apartment List, Zumper or Trulia pages; Openigloo (NYC buildings);
Better Business Bureau pages for the management company (check robots first); local news sites and police press
releases (Patch, News 12, NJ.com, lohud, CT Insider, amNY, QNS, local papers) for incidents at the address; court or
code-enforcement records if online; the manager's own site for who manages it and since when.
Record each item separately with its date. Categories: `car_crime` (break-ins, thefts, catalytic converters, towing
disputes at the building or its garage or lot), `elevator` (outages), `management` (no heat or hot water, pests,
mold, withheld deposits, unresponsive, illegal fees, sudden rent hikes), `safety_incident` (assaults, shootings,
package theft at the address), `noise`, `positive` (specific praise), `other`.
Excerpts: one or two sentences, verbatim, no usernames. Each item needs the page URL where the text appears and the
date of the review or article (not today's date). Nothing found is a valid result: record
`category=none_found` with where you looked. Do not pad.

## 4. Useful facts you come across
Parking type and monthly fee, pet rent and fees, required monthly fees, pool (indoor or outdoor), doorman, year
built, management company and when it took over (management changes matter: complaints older than 6 months count
less).

## Output (write as you go; one batch = one set of files)
- `data/evidence/live_check_batch_<n>.csv`: addr_key, listing_url, unit, status (live / gone / changed / blocked),
  price_now, available_now_text, matches_stored (yes/no), building_site_url, checked_at, notes
- `data/evidence/confirm_batch_<n>.csv`: addr_key, fact (elevator / floor / dog_weight_limit / dogs_allowed),
  value, quote, source_url, status (confirmed / unconfirmed / contradicts)
- `data/evidence/items_batch_<n>.csv`: addr_key, building_name, category, item_date (ISO, or year-month), excerpt,
  source_site, source_url, about (building / garage_or_lot / management_company / street), retrieved_at
- `data/evidence/facts_batch_<n>.csv`: addr_key, fact, value, quote, source_url
- `docs/harvest_notes/evidence_batch_<n>.md`: buildings done, what was blocked, anything alarming.

Final reply to the coordinator, under 200 words: buildings done; units live / gone / changed; facts confirmed vs
unconfirmed; evidence items by category; the buildings with the most serious evidence.
