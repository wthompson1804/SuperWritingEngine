# Harvest notes: local rules, round 2 (`local_rules_round2`)

Run: 2026-11-15 23:45 UTC to 2026-11-16 about 01:00 UTC. Output: `data/reference/local_rules_round2.csv`
(138 rows: 92 `found`, 46 `not_found`; same columns as `local_rules.csv`). Nothing committed, pipeline not run,
`local_rules.csv` / `site/` / master files untouched.

## Scope

Municipalities were recomputed from `site/data.json` (`neighborhoods`, non-NYC), ordered by shown units, minus those
with at least one `found` row in round 1. That left **49** with nothing: the 22 round-1 failures still on the page
plus municipalities added to the page since round 1 (Shelton, Hamden, Franklin, Fairfield, Seymour, Stratford,
West Haven, Beacon Falls, Brookfield, Oxford, Bound Brook, East Brunswick, East Rutherford, Elizabeth, Long Branch,
Red Bank, South Orange, Springfield, Wayne, Weehawken, Fort Lee, Garwood, Maplewood, Old Bridge, Princeton, Ridgewood,
Roxbury, Somerville, Glen Cove, Long Beach, Patchogue, Wallkill). Hempstead Village (round 1: town rows only) was also
retried. `python3 scripts/local_rules_round2.py munis` prints the list.

Note: 11 NYC neighborhoods now on the page (Bath Beach, Bay Ridge, Midwood, Kew Gardens Hills, Gravesend x3, etc.) are
not in the `applies_to_hood_ids` of round 1's New York City rows; the NYC rules apply to them all the same.

## How

- `scripts/local_rules_round2.py` imports round 1's `local_rules_fetch.py` (not edited) and re-points it at
  `raw/local_rules_round2/` (`_pages.jsonl`, `text/`, `_blocked.jsonl`, `_blocked_hosts.json`). Robots per host; groups
  naming Claude override `*`; 2.2 s per host; one process per host when run in parallel.
- Hard rule in code: hosts refused in round 1 are pre-loaded as closed; any 401 / 403 / 429 / bot wall this round is
  written to `_blocked_hosts.json` and the host is never requested again. ecode360, Municode, American Legal, Reddit,
  Yelp, Nextdoor, Patch, Trulia, Zillow are refused before any request.
- Discovery: home-page links and `sitemap.xml` keyword filter, then (new in round 2) a web search restricted to the
  municipality's own domain to find the right page. **No fact was taken from a search result**: the page was fetched
  and the quote checked. Where a search result said something we could not read on the page, the row is `not_found`
  and says "unverified".
- Rows: `scripts/local_rules_round2_rows.jsonl` (hand-entered after reading cached text).
  `python3 scripts/local_rules_round2.py build` rewrites the CSV; every `found` quote must occur verbatim (whitespace
  and curly quotes normalised) in the cached text of its `source_url`, else the row is rejected. 0 rejected.

## Coverage

53 entries in the CSV (49 target municipalities + Hempstead Village + NJ, CT, NY statewide entries).

| Topic | Municipalities with at least one sourced rule |
|---|---|
| Street parking (20) | Jersey City, Bayonne, East Orange, Bloomfield, South Orange, Springfield, Fort Lee, Princeton, Ridgewood, Somerville, Red Bank, East Rutherford, Long Branch, Bound Brook, East Brunswick, Belleville, Hempstead Village, Hamden, West Haven, Stratford |
| Dogs (18 + 2 statewide) | Jersey City, Parsippany, Shelton, Hamden, Beacon Falls, Oxford, Fairfield, East Brunswick, South Orange, East Rutherford, Long Branch, Glen Cove, Princeton, Ridgewood, Somerville, Belleville, Old Bridge, Roxbury; New Jersey statewide (licence at 7 months, fee range); Connecticut statewide (licence at 6 months, $8 / $19, roaming statute) |

Found rows by rule: resident_permit 22, dog_license 20, snow_emergency 10, overnight_parking 9, leash_law 8,
alternate_side 6, municipal_garage_monthly 6, guest_parking 4, dog_park 4, others 3.
The two statewide dog rows mean every NJ and CT neighborhood now has at least the licence requirement.
**Limit on number of dogs: found nowhere** (it lives in the codes). Dog-park permit: only Parsippany (permit needed,
Cameron Dog Park) and Glen Cove (residents only, dog must be city-licensed).

## Rules that matter most for a car parked on the street overnight

- **South Orange**: no overnight parking 2-6 AM anywhere without a permit; **apartment residents cannot get an
  on-street permit**, only municipal-lot permits (night permit $25 a month / $150 a year).
- **Springfield (Union County)**: no parking on any public street 2-6 AM; police permission is night by night only.
- **Ridgewood**: no parking on any street or public lot 2-6 AM; overnight lot permits ($85 / 3 months) are **not sold
  to residents of the multi-family housing developments**.
- **East Orange**: every car on the street 2-6 AM needs an overnight permit ($150 a year, pro-rated; renters qualify
  with a lease), only on streets signed for permit parking; streets signed "No Parking 2AM-6AM" allow none.
- **Bayonne**: citywide weekday resident permit ($5), but **occupants of developments in Redevelopment Areas adopted
  on or after Jan 15, 2015 are excluded** from resident permits. Night lot permit $70 a month.
- **Fort Lee**: all residential streets are permit streets ($5 per car for 2 years); in **Zone A** street parking 2-6 AM
  is prohibited and residents with any off-street parking available cannot register.
- **Princeton**: no overnight parking 2-6 AM on former Borough streets; overnight on-street permit ($30 a quarter) only
  if the residence has no on-site parking; renters qualify with a signed lease.
- **Jersey City**: zone-permit streets limit non-permit cars to 2 hours; permit needs licence at the Jersey City
  address and valid registration; cars off snow emergency routes in a storm. Price and large-building eligibility not
  found (portal bot-walled, ordinance PDF is a scan).
- **Hempstead Village**: a permit requirement for overnight street parking (tentatively 2-6 AM) is being drafted
  (notice of Oct 13, 2026); not in force yet.
- **Bloomfield**: an overnight permit parking ordinance exists (penalty schedule); details not readable.
- **Red Bank**: when snow covers the street, no parking on any street 11 PM-7 AM; municipal lots free meanwhile.
- **Hamden / West Haven / Stratford**: storm parking bans are one-side-only (Hamden: no parking on the odd side; West
  Haven: none on the even side plus listed routes; Stratford: side changes by storm).
- **East Rutherford**: alternate-side enforced all year regardless of weather. **Belleville**: Alva Street permit-only 2-6 AM.

## Blocks and failures

| Host | Result |
|---|---|
| Round-1 refusals, not re-requested | yonkersny.gov, yonkersparkingauthority.com, newarknj.gov, stamfordct.gov, westportct.gov, montclairnjusa.org, morrisplainsboro.org, townofnewpaltz.org, nycgovparks.org, nysenate.gov |
| New 403 / bot wall this round (stopped at once) | franklintwpnj.org, waynetownship.com, weehawken-nj.us, brookfieldct.gov, maplewoodnj.gov, townofwallkill.com, agriculture.ny.gov, jcparking.cmrpay.com (Jersey City permit portal) |
| robots.txt group naming Claude disallows the site | vsvny.org (Valley Stream), longbeachny.gov, garwood.org |
| robots.txt Claude group disallows FAQ pages (CivicPlus) | bloomfieldtwpnj.com, eastrutherfordnj.net, elizabethnj.org, villageofhempstead.org. One Bloomfield FAQ URL spelled `Faq.aspx` passed the case-sensitive check and was fetched; it was **not used** for any row. |
| TLS failure from this environment (not a refusal) | patchoguevillage.org, www.cityofshelton.org (bare host works), www.cga.ct.gov (CT statutes) |
| Script-rendered pages, no readable text | montvale.org, riverdalenj.gov, ahnj.com, seymourct.org, most of stratfordct.gov and bayonnenj.org, cityofbordentown.com document folders |
| data.jerseycitynj.gov | `/api/` disallowed by robots; dataset pages render by script. Not used. |
| www.jerseycitynj.gov | `/robots.txt` redirects to a 404 page (that broke round 1); treated as "no robots file", pages read over https. |
| Wrong guesses | www.npanj.com is not the Newark Parking Authority (two pages fetched, discarded). |

## Still missing

- **Yonkers, Newark, Stamford** (10 shown units each): nothing; only their bot-walled official hosts carry the rules.
  A manual browser pass is the only route (Yonkers PVB pages; Newark Parking Authority; Stamford snow-emergency page).
- Montclair, Westport, Morris Plains, Valley Stream, Franklin (Somerset), Wayne, Weehawken, Brookfield, Maplewood,
  Wallkill, Long Beach, Garwood, Patchogue, Seymour, Montvale, Riverdale, Atlantic Highlands, Bordentown, Elizabeth: nothing.
- Jersey City: zone-permit price, large-building eligibility, dog runs. Bayonne, East Orange, Bloomfield, Springfield,
  West Haven, Stratford, Red Bank, Bound Brook, Fort Lee, Hempstead Village: dog rules. Parsippany, Shelton, Beacon
  Falls, Oxford, Fairfield, Glen Cove, Old Bridge, Roxbury: street-parking rules (none stated on pages read).
- Number-of-dogs limits and leash lengths outside Princeton (8 ft) and South Orange (under 6 ft).
- `not_found` means "not on the pages read", never "no such rule".
- `docs/SOURCES.md` was not edited (shared file); the host findings above should be copied there.
