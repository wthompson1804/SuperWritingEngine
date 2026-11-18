# Neighborhood ranking notes (Version 7, 2026-11-18)

Built by `scripts/neighborhood_rank.py` (no web requests; re-running overwrites the two outputs). Checked by
`scripts/test_neighborhood_rank.py`. Outputs: `data/neighborhood_rank.csv` (every neighborhood considered, with its
status) and `site/neighborhoods_data.json` (the ranked ones with their buildings). Spec: "Version 7" in
`docs/CONCIERGE_DESIGN.md`. Every count below is also in the JSON under `meta`.

## What went in

- 21,095 listing rows read; 16,927 are individual apartments; 16,922 used (5 are stated failures of type).
  Studios and one-bedrooms only. 6,886 are at $2,000 or less.
- Neighborhood of each listing: `data/listings.csv` carries no `hood_id`, and only 2,318 of the 16,922 rows sit at an
  address the pipeline already placed (`data/units.csv`). The rest were placed with the same geography, from caches
  only: a cached Census geocode of the same point (3,823 rows), the NYC neighborhood polygons (3,177), the Jersey City
  polygons (866), the majority neighborhood of the ZIP among already-placed addresses (241), and last the city the
  listing wrote (6,439; dropped when the point is more than 15 km from that neighborhood's centre, 10 rows). 48 rows
  have no coordinates. The listed city is a mailing city, so some of those 6,439 may sit in the next town.
- 514 listings at $2,000 or less have no house number in their address. They count as listings (rent, dogs, size)
  but not as buildings, and no building card is made from them.

## Who was ranked

| Step | Neighborhoods |
|---|---|
| With at least one listing at $2,000 or less | 633 |
| No neighborhood record on disk (`data/neighborhoods.csv` holds 211) | 437 (82 of them have 5+ buildings) |
| Drive of 2 hours or more | 3 |
| Cut by the Jamaica rule (kept as written) | 17 (10 of them have 5+ buildings) |
| Fewer than 5 buildings at $2,000 or less | 60 |
| **Ranked** | **116** |

The largest gap is the first cut. A place without a row in `data/neighborhoods.csv` has no drive time, places, parks
or records figure, so the Jamaica rule cannot be applied and it is not ranked. The biggest by supply: Newton NJ (42
buildings), Passaic (41), Annadale-Huguenot (31), Lodi (27), Great Kills-Eltingville (25), Lyndhurst (21),
Phillipsburg (19), Palisades Park (17), Roselle (16), Perth Amboy (15). `data/reference/crime_agencies.csv` and the OSM
extract could supply those rows; that is pipeline work outside this script.

Jamaica rule cuts with real supply: New Haven (199 buildings), Irvington (83), Newburgh (47), Kearny (26), Asbury
Park (21), Neptune (21), Norwood (10), Mount Hope (8), Flemington (5), Morris Park (5).

## Measures, weights and coverage (116 ranked)

| Measure | Weight | Parts | Coverage |
|---|---|---|---|
| Near Mom and Dad | 22 | drive minutes 70%, round-trip toll 30% | 116 |
| Cost | 18 | median listed rent at $2,200 or less 60%, apartments at $2,000 or less 40% | 116 |
| Going out | 16 | restaurants + bars + cafés within 800 m | 116 |
| Green and the dog | 14 | park walk 40%, park area within 800 m 30%, dog run distance 30% | 116 |
| Supply she can use | 12 | listings saying dogs allowed 40%, dogs or pets allowed 20%, elevator or floor 2 stated 40% | 116 |
| Space | 8 | median stated size (5+ listings must state one) | 101 |
| Driving life | 6 | off-street share among buildings that describe parking (5+ must) 60%, overnight rule 40% | 55 (share 46, rule 21) |
| Records | 4 | half each of the two rates against Jamaica's; never shown as text | 115 |

Each part is scaled 0 to 1 across the ranked list between its 5th and 95th percentile; a measure is the weighted mean
of its known parts; the score is the weighted mean of the known measures. A missing measure earns nothing and costs
nothing. No "confirmed today" multiplier.

Limits to know:
- **Driving life is thin**: fewer than half the neighborhoods have it. It was kept (weight 6) because the rule for
  missing measures handles it, but it should not be read as a ranked fact for most places. The overnight rule is known
  only for the 26 towns whose rules were read; a town not in that table is unknown, not free.
- **Going out and green are not measured over all listed buildings.** They are the neighborhood record's medians,
  taken at the buildings that passed the earlier checks (a median of 2 buildings per neighborhood across the table).
  Each neighborhood's JSON carries `buildings_measured`.
- **Dog shares are over all listings in the pool**, including search-result cards that can say nothing about pets, so
  the share also reflects which site the listings came from. "Dogs allowed" and "pets allowed without naming dogs"
  are counted separately; "cats allowed" is not counted as pets allowed.
- **Template text is not tested**: listing descriptions are not in the listings table. "Looks fake" rests on the
  reviewers' "unverified" verdicts and on a rent under 55% of the neighborhood's median for the same size (10+
  comparables).
- Official violation records enter only through `data/avoid_buildings.csv`. One building is on that list for a reason
  this page does not put in words; it is kept out of the top three and not shown under Avoid (`held_back`).

## Sensitivity

18 runs: the stated weights, each weight x1.5 and x0.5 in turn, and equal weights. `rank_range` is the lowest and
highest rank over these. The top of the list is stable to the single-weight changes; equal weights move the Queens
neighborhoods most (Jamaica 3 to 33, Elmhurst 4 to 43, Forest Hills 7 to 56) because they score low on cost and space.

## Buildings

- Top three: buildings with a house number and at least one studio or one-bedroom at $2,000 or less that has no
  stated failure (no dogs, ground floor, floor 3+ without an elevator, move-in after December 15). Points: verified
  on the page 100; dogs stated 20 (pets only 12); elevator or second floor 15; rating with 10+ reviews (rating - 3.5)
  x 8, between -12 and 12; record held and clean 4; one per apartment up to 10; own-site contact 5.
- Avoid, in this order, up to two: the avoid list, a low rating by `data/evidence/rating_standard.csv`, a reviewer's
  "unverified" verdict, rent far below the neighborhood, stated no dogs, ground floor only. Across the 116: 189
  avoid cards (no dogs 122, ground floor only 42, rent far below 14, unverified 6, avoid list 5).
- Contacts: only leasing offices and management companies; an individual owner's or a broker's number is never
  written. Names: the building name, or the address; a company name ending in LLC and the like is replaced by the
  address.

## The Zumper "no pets" block (audit item 6)

499 rows (421 individual apartments) carry "Pets | Dog | Policy | Not allowed | Cat | Policy | Not allowed | No pets
allowed." All 489 cached pages were read by script and 20 by eye. It is a real statement, not a default:
- The block is rendered when the page data holds an explicit empty pets list (`"pets":[]`). On Zumper pages where the
  lister said nothing the value is `null` and no block appears at all (269 of 500 other Zumper pages sampled).
- On about 285 of the 489 pages the lister's own description also says no pets ("No pets", "Is not pet friendly",
  "pets are not permitted"); on other Zumper pages that happens on 7 of 500.
- Three descriptions contradict the block ("Pets okay case by case", "Pets considered", "the building is
  pet-friendly"), and a few rows carry page pet codes that include dogs.
Treatment: the rows stay "no dogs"; the contradictory ones (8 apartments in the rows used) are set to unknown inside
this script only. `scripts/gates.py` is untouched.
