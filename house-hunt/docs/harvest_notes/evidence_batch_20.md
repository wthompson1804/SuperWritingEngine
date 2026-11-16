# Evidence batch 20: re-read of shown apartments never re-read since collection (2026-11-16)

Source list: `data/reference/evidence_batches/batch_20.csv`, read once from `data/ranked_units.csv` at the start
(`shown == True`, `live_status` not live/changed, source not Trulia): **190 apartments in 54 buildings**: 170 on Apartment List
(48 building pages), 20 on buildings' own pages (Scribe 6, The Asher 4, The Leaf 4, Motif 3, Continuum 2, Harbor Landing on Greystar 1).
Outputs: `data/evidence/live_check_batch_20.csv` (190 rows), `facts_batch_20.csv` (18 rows), and header-only
`confirm_batch_20.csv`, `items_batch_20.csv`, `ratings_batch_20.csv`. Each was written to a temp name and renamed.
Raw pages as read tonight: `raw/evidence_b20/` (a new folder, so nothing came from yesterday's cache and the harvest cache was not
overwritten); the one repeat read is in `raw/evidence_b20_retry/`. Nothing else was edited; the pipeline was not run; nothing was committed.

## Counts

- **173 live, 8 changed, 9 gone, 0 blocked.** No host refused.
- Apartment List: 153 live, 8 changed, 9 gone. Own pages: 20 live.
- Price changes: 8, all down, all small. Studios: 3 down ($5 each). One-bedrooms: 5 down ($5 to $10). None up. Largest: $10
  (Avalon Maplewood 002-347 $2,560 to $2,550; 001-337 $2,580 to $2,570). The others: Avalon Maplewood 002-215 $2,240 to $2,235,
  001-243 $2,450 to $2,445; The Walcott Hackensack 353 $2,244 to $2,239, 417 and 333 $2,301 to $2,296, 631A $2,522 to $2,517.
- No availability date moved in a way that matters. On vacant units the site's `available_on` field moves by a day (10 units: 100 avalon gates|06611, 150 southfield ave|06902, 200 boyden ave|07040); those are `live` with the movement said in the note. No unit is now later than 2026-12-15.

## Gone (9)

| Building | Unit | Stored price | What the page shows tonight |
|---|---|---|---|
| The Mercer, 10 Commerce Ct, Newark | 8H, 9E, 10E, 11E, 12F, 12E | $2,185 to $2,528 | Apartment List answers "This page could not be found" for the building's page (read twice; a normal answer, not a refusal). The listing has been taken down. Not searched for under another page address. |
| LIA by Vermella, 51 Lincoln Ave, Orange | 307 | $2,560 | Not in the unit list; plan A1 now lists no individual units. |
| Kensington Place, 527 Old Bridge Tpke | 1315 | $2,575 | Not in the unit list; plan 1E still lists 1331, 2315, 1108. |
| Harbor Pointe, 302 Constitution Ave, Bayonne | B9-457 | $2,650 | Not in the unit list; plan Compass 2 now lists no individual units. |

## The important finding: 12-month prices on the buildings' own maps

The listed price on four own-site buildings belongs to a long lease. The availability map's own price calculator (the JSON the map
loads when a unit is opened; `sightmap.com/app/api/v1/leasing/...`, allowed by robots) gives the price for every term, move-in 2026-11-16.
The data had no 12-month price for any of these. Recorded in each unit's live-check note ("Price is for a N-month lease; 12-month price $X")
and as one `lease_term_of_listed_price` fact per unit.

| Building | Unit | Listed (term) | 12-month price | 13-month | All-in today | All-in at the 12-month price |
|---|---|---|---|---|---|---|
| The Leaf, New Rochelle | 2318 | $2,563 (24; same for 14 to 24) | $3,973 | $2,694 | $2,926 | about $4,336 |
| The Leaf | 2418 | $2,573 | $3,988 | $2,705 | $2,936 | about $4,351 |
| The Leaf | 2505 | $2,583 | $4,004 | $2,715 | $2,946 | about $4,367 |
| The Leaf | 2518 | $2,583 | $4,004 | $2,715 | $2,946 | about $4,367 |
| The Asher, Stamford | 308 | $2,342 (21; same for 17 to 21) | $3,145 | $3,087 | $2,658 | about $3,461 |
| The Asher | 610 | $2,402 | $3,225 | $3,166 | $2,718 | about $3,541 |
| The Asher | 730 | $2,385 | $3,203 | $3,143 | $2,714 | about $3,532 |
| The Asher | 830 | $2,415 | $3,243 | $3,183 | $2,744 | about $3,572 |
| Scribe, Norwalk | 425 | $2,606 (24; same for 17 to 24) | $3,210 | $2,621 | $2,935 | about $3,539 |
| Scribe | 502, 507, 542, 544, 546 | $2,379 (24; same for 17 to 22 and 24) | $2,395 | $2,391 | $2,695 | about $2,711 (stays under) |
| Motif, New Rochelle | 523 | $2,375 (16) | $2,819 | not offered | $2,934 | about $3,378 |
| Harbor Landing, Stamford (Greystar) | 452 | $2,487 (13) | $3,040 | (listed) | $2,901 | about $3,454 |

"All-in at the 12-month price" is my arithmetic (stored all-in minus listed rent plus the 12-month price), not a pipeline figure.
Under the rule "listed price for a lease longer than 13 months and the page gives the 12-month price: cost and cap use the 12-month
price", ten apartments would pass $3,000: The Leaf 4, The Asher 4, Scribe 425, Motif 523. Harbor Landing 452 is on a 13-month price, so
the rule does not switch it, but its 12-month price ($3,040) is itself above the cap. The Leaf's price at 14 months equals the listed price.
Motif 205 and 632 (available Dec 6 and Dec 8, 16-month price): the calculator returns no terms before the unit is vacant; no 12-month price read.
Continuum S1016 and S1617: 12-month prices, unchanged, one flat price.
Apartment List gives one lease length per unit and no 12-month price; where the unit's price is for 13 to 20 months the note says so.

## Tags used

- **STALE PAGE 2026-07-30**: Grandville Towers 9C (19 Morford Pl, Red Bank), $2,690, still listed. Every unit row on that page was
  last updated 2026-07-30 with `available_on` 2026-07-29, and the page gives no availability-check date; only the building-level record
  has a newer timestamp. The same is true of units 5F and 7C, which batch 15 graded `live` with this said in plain words but without the tag.
  The coordinator should treat the three alike.
- NO UNITS AVAILABLE, DIFFERENT BUILDING, WAITLIST: none found. Every page's name, street address and ZIP matched the stored building;
  the five own sites still carry the same SightMap embed as when collected, and the map's asset name matches.

## Gate facts and cost lines

- Compared with yesterday's cached copy of each Apartment List page: pet policy, parking, fee texts, lease-terms text, offers and the
  elevator tag are identical on all 47 pages that still exist. Nothing new to confirm, so `confirm_batch_20.csv` is header-only.
- **No gate fact tonight contradicts the data.** Two notes, neither a contradiction: Apartment List's amenity list has no "Elevator" tag
  for Liberty Bay Club (190 W 54th St, Bayonne) or West Side Square (1075 West Side Ave, Jersey City); the data's elevator for those
  comes from other sources (confirmed / inferred). Piper and Halstead Norwalk carry `dogs_allowed = conflicting` in the data; tonight's
  Apartment List pet card still says dogs are allowed on both.
- Offers on the own sites tonight (facts `special_offer`): The Asher now says "New Residents Can Enjoy 1-Month free! *For a limited time on
  select units and lease terms" (the $500 look-and-lease saving in the stored text is gone); Scribe says "New residents can receive up to
  2 months free!". Neither says which units or terms, nor whether the map's prices already include it.
- Floors on the own maps (Scribe, Asher, Leaf, Motif, Continuum, Harbor Landing 452 = Floor 4) equal the stored floors.

## Matching

Apartment List: by the site's own unit id inside the listing id (`unit_rental_id`); Grandville Towers 9C has no such id and was matched by
the site's numeric unit id plus the exact label. SightMap: exact unit number within the same map. Greystar: the site's unit id. No floor
plan was matched to an apartment; where the plan remains and the unit does not, the status is `gone`.

## Hosts and requests

87 requests in all, one at a time, 3.5 s apart per host: apartmentlist.com 48 building pages + 1 repeat + robots; sightmap.com 5 maps +
19 unit price-calculator reads + robots; greystar.com 1 page + robots; the five own sites 1 page + robots each. robots.txt was re-read
for every host tonight and allows these paths. **No 403, 429, CAPTCHA or wall; `raw/_host_kill_shared.json` was not changed.**
Trulia was not requested. The maps' "apply" links lead to securecafe (off limits) and were not followed.

## Limits

- The 12-month figures are the calculator's prices for a move-in on 2026-11-16; they are revenue-managed and can move daily.
- The Mercer may be listed elsewhere; only its Apartment List page was read.
- Own-site pages were read for the embed and the offer banner; their text has no pet weight limit or elevator sentence beyond what the data holds.
