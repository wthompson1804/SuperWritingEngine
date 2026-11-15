# Harvest notes: local rules for street parking and dogs (`local_rules`)

Run: 2026-11-15, about 21:45 to 22:40 UTC. Outputs: `data/reference/local_rules.csv` (600 rows: 150 `found`,
450 `not_found`), `data/reference/dog_parks.csv` (104 rows). Nothing committed.

## How it was done

- `scripts/local_rules_fetch.py`: robots check per host (a group naming ClaudeBot / Claude-User / Claude-SearchBot /
  Claude-Web / anthropic-ai overrides `*`; `Crawl-delay` honoured), 2.2 s per host, `lib.cached_get` into
  `raw/local_rules/`, page text in `raw/local_rules/text/`, page log `_pages.jsonl`, refusals in `_blocked.jsonl`.
  Discovery was the municipality's home page links, then its `sitemap.xml` filtered on parking / dog / snow words.
  No search engine was used, so no fact comes from a snippet.
- `scripts/local_rules_rows.jsonl` and `scripts/local_rules_dogparks.jsonl`: rows entered by hand after reading the page.
- `scripts/local_rules_build.py`: rewrites both CSVs. Every `found` row's quote must appear verbatim (whitespace and
  curly quotes normalised) in the cached text of its `source_url`, or the row is rejected. It also adds a `not_found`
  row for each municipality x core rule with nothing found, saying where we looked or why the source was blocked.
- `scripts/local_rules_munis.json`: municipality -> neighborhood ids and start URLs. `scripts/local_rules_blocks.json`: block reasons.

## The main block: municipal codes

`ecode360.com`, `library.municode.com` and `codelibrary.amlegal.com` each carry robots.txt groups for `ClaudeBot`,
`anthropic-ai` and `Claude-Web` with `Disallow: /`. Under the project rule these apply to us, so **no municipal code
was read on any of the three hosts** (this includes the NYC Administrative Code and Rules on American Legal). Code text
appears only where a municipality republished it on its own site (Hackensack's permit form quotes its ordinance;
Bridgeport publishes its winter alternate-side ordinance; NYC Health publishes Health Code Article 161 as a PDF).
This is why leash length, dog limits, waste rules and overnight-parking ordinances are mostly `not_found` outside NYC.
`docs/SOURCES.md` was not edited (shared file); these findings should be copied there.

Other blocks:

| Source | Result |
|---|---|
| www.nycgovparks.org | 403 bot wall on first request; stopped. NYC Parks rules, dog-run hours, beach and boardwalk dog rules not collected. Dog-run list taken from NYC Open Data `hxx3-bwgv` instead. |
| portal.311.nyc.gov | robots disallows `/knowledgebase/article/`; not used. |
| www.nysenate.gov (NY statutes) | 403 Cloudflare at robots.txt; no state statute rows. NJ and CT statute sites were not attempted (time). |
| Yonkers (city and parking authority), Newark, Stamford, Westport, Montclair, Morris Plains, Town of New Paltz | 403 bot wall at robots.txt or first page; nothing further requested. |
| Valley Stream (vsvny.org) | robots.txt group naming Claude agents, `Disallow: /`. |
| Jersey City, Village of Haverstraw | https redirects to plain http, which this environment cannot reach; not retried. |
| White Plains, Clifton, Norwalk (CivicPlus) | Claude group disallows `FAQ.aspx` / `CivicAlerts.aspx`; other pages allowed and read. |
| North Bergen township site, Bayonne, Belleville | no sitemap; only the home page (and for North Bergen the Parking Authority site) was read. |

## Coverage by municipality (found rows)

New York City 19 (DOT, DSNY, Health; applies to all 44 NYC neighborhoods, with a Jamaica-area garage row) ·
White Plains 10 · Larchmont 7 · Harrison 7 · West New York 7 · Rahway 7 · New Brunswick 7 · Mineola 6 ·
North Bergen 6 · Hackensack 6 · Middletown 6 · New Rochelle 5 · Bridgeport 5 · Mount Vernon 4 · City of Orange 4 ·
Hawthorne 4 · Norwalk 4 · Milford 4 · Town of Hempstead 3 · Teaneck 3 · Edgewater 3 · Dover 3 · Peekskill 2 ·
Englewood 2 · Clifton 2 · Danbury 2 · Trumbull 2 · Town of Haverstraw 2 · LaGrange 2 · Mount Arlington 2 ·
Port Chester 1 · Carteret 1 · Village of New Paltz 1 · Plainfield 1.

Nothing found (22): Yonkers, Newark, Jersey City, Stamford, Westport, Montclair, Morris Plains, Valley Stream,
Village of Haverstraw, Town of New Paltz (all blocked or unreachable, see above); Village of Hempstead, Bayonne,
Belleville, Bloomfield, East Orange, Bogota, Montvale, Parsippany-Troy Hills, Riverdale, Atlantic Highlands,
Bordentown City and Township (sites reachable, but the pages found carried no rule text; their parking and animal
rules live in the blocked code hosts or in PDFs / pages the keyword discovery did not reach).

Found rows by rule: resident_permit 25, dog_license 24, snow_emergency 23, municipal_garage_monthly 20,
overnight_parking 11, alternate_side 9, guest_parking 7, parks_and_beaches 6, dog_park 5, waste 5, meter_hours 4,
leash_law 4, meter_rates 3, dog_limit 1, plus NYC towing / hydrant / municipal-lot rows.

## Notable findings

- Overnight street parking banned 2 AM-6 AM citywide: **White Plains**, **Larchmont** (temporary permission from police).
- **North Bergen**: any car on the street 10 PM-7 AM needs a Parking Authority permit; $20 two-month new-resident permit.
- **Hackensack**: listed streets are resident-permit-only 2-6 AM; permit requires New Jersey registration.
- **Harrison**, **Rahway**, **Mineola**, **White Plains** resident permits need licence and registration at the local
  address; an out-of-state car does not qualify. **West New York** sells an out-of-state plate permit ($50 / 3 months)
  and gives new residents a free two-week permit.
- **City of Orange**: residential permit exists specifically for overnight street parking. **Dover**: on-street and
  lot overnight permits; lots closed 2-6 AM without one. **Peekskill**: Dec 1-Apr 15 no overnight parking unless signed.
- **Middletown**: overnight street parking now allowed year-round; banned only during a Snow Alert.
- **Danbury**: all cars off all city streets in a snow emergency; free garage. **Mineola**: no street parking after 2 in of snow, Dec-Mar.
- Monthly parking prices found: NYC DOT garages ($250-$600), Mineola garage ($120 resident / $250 non-resident overnight),
  Mount Vernon lots ($100 / $175), Orange ($40 / $60), New Brunswick decks ($200-$210), Middletown ($120 a year).
- NYC: leash at most six feet; off-leash in parks only inside a 9 PM-9 AM window set by Parks; licence $8.50 / $34.

## Gaps and cautions

- Hempstead: rows are split between the Village (nothing found) and the Town (dog licence, dog parks, sweeping). Whether
  village residents license through the Town was not confirmed. Auto `not_found` parking rows for "Hempstead (Town)",
  "Haverstraw (Town)", "Bordentown Township" and "New Paltz (Town)" only mean the second candidate jurisdiction was checked.
- Larchmont dog licences are issued by the Town of Mamaroneck (fee not collected).
- `not_found` means "not on the pages read", never "no such rule". Every town here very likely has leash, waste and
  licensing ordinances in its code.
- dog_parks.csv: the 95 NYC rows come from the Parks open-data polygons (lat/lon is a computed centroid; no hours or
  small-dog information). Other rows carry only what the municipal page says; hours were stated nowhere. The Town of
  Haverstraw dog parks' address is inferred from the facility heading above the amenity list and needs confirming.
- Meter hours, guest permits and garage price sheets were often on linked PDFs or portals that were not opened.
- Next steps that would close most gaps: permission to read ecode360 / Municode / American Legal, or a manual pass in
  a browser for Yonkers, Jersey City, Newark, Stamford and New Rochelle's rate sheet.
