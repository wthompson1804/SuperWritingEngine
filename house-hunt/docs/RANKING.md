# Ranking (approved by Will, 2026-11-15) — implemented in `scripts/rank.py`

**Layer 1, universal value (0-100).** Six parts, each the unit's percentile across all kept units:
safety 25 (violent, property and vehicle-theft rates; car crime within 250 m where published), cost 15 (all-in),
building 20 (elevator stated, in-unit laundry, doorman, controlled access, gym, package room, outdoor space, age),
car 15 (garage or gated > covered > lot > street), space 15 (sq ft), dog 10 (walk to green, dog park, pet rent,
dog amenities). An unknown fact scores at the 25th percentile and becomes a tour question.

**Layer 2, the year's promise.** Walk-Everywhere: restaurants, bars, cafés, grocery on foot. Old-Neighborhood:
grocery on foot, transit to her parents. Fresh-Start: building amenities, water distance, newcomer share.
Little-City: restaurants nearby, train station distance. Room-to-Breathe: sq ft per dollar. Quiet-Street: low
violent crime, distance from the motorway, parking.
**Rank score = 0.7 × universal + 0.3 × promise + pool bump (+3 any pool, +6 indoor pool).**

**Selection per neighborhood.** Highest rank score first; at most 2 units per building; units beaten or tied on all
six parts by another unit in the neighborhood go last. Top 15 are candidates for the evidence pass; avoid cards
(up to 5) come out of those; the best 10 of the rest are shown.

**Layer 3, comparing lives.** No single cross-life score. Each unit carries two standings per part (within its year;
against everything). `data/group_exchange.csv` holds each year's medians and its difference from "near home"
(units within a 15-minute drive of Jamaica). These run in the background; the page shows them only on demand.

**Safety gate before ranking:** neighborhoods with violent or property crime above Jamaica's precinct are cut.

## Five-point spectrum against staying in Queens (Will, 2026-11-15)

The compare stage must be easy to read: every measure is placed on five points with **Queens in the centre**
(3 = about the same as the median passing unit in Queens; 1-2 = worse for her; 4-5 = better for her; distance follows the same rule:
**closer to her parents is better**, per Will; this replaces the UX brief's "no red or green on distance"). Bands are in real units and are
stored in `data/reference/queens_spectrum_definition.csv`; per-unit values are the `vsq_*` columns of
`data/ranked_units.csv` (with `vsq_*_diff` holding the plain difference, e.g. +120 sq ft). The underlying
calculations stay in the background and are shown only when she asks how a point was reached.

## Version 2 (Will, 2026-11-15: "use many more variables; drop anything sketchy") — current

Supersedes the weights and part definitions above; the 70/30 split, pool bump, selection rule and Queens spectrum stay.

**Listing confidence, applied before ranking.** `sketchy` listings are excluded (`data/excluded_sketchy.csv`):
60+ days old, no unit and no building named, thin syndicated feed, conflicting dog policy, all-in under 60% of the
neighborhood median, or two or more inferred gate facts. `one_inferred` listings stay with a 0.97 certainty factor
and a `to_confirm` note; that fact must be confirmed in the evidence pass before the unit is shown. `clean` = every
gate fact stated on the page.

**Universal value (weights sum to 100).** Distance and daily life were added; the original six keep their proportions.

| Part | Weight | Variables (percentiles across all kept units; unknown = 25th percentile) |
|---|---|---|
| Safety | 22 | violent rate 35, property rate 15, vehicle-theft rate 15, car crime within 250 m (NYC) 15, building security features 20 |
| Building | 16 | security features (24h doorman 3, doorman 2, controlled entry 2.5, package room 1) 40; comfort (in-unit laundry 2.5, lounge or coworking 1.5, gym 1, outdoor space 1, elevator stated 1, balconies 0.5) 45; year built 15 |
| Cost | 12 | all-in 85, how many cost lines are stated rather than estimated 15 |
| Car | 12 | parking type 50, vehicle-theft rate 15, car crime nearby 15, parking fee 10, surface parking nearby 10 |
| Space | 12 | sq ft 75, a separate bedroom 25 |
| Distance | 10 | drive to her parents 60, transit 25, tolls 15 (closer is better) |
| Dog | 8 | walk to green 25, park area 15, dog park 15, vets 10, dog amenities in the building 10, weight limit stated ≥ 40 lb 10, woods 5, pet shops 5, pet rent 5 |
| Daily life | 8 | supermarket distance 25, cafés in walking distance 20, gyms 15, distance from the motorway 15, farmers' market 10, corner stores 10, library 5 |

**The year's promise (30%).**
- Walk-Everywhere: restaurants, bars, cafés, shops of any kind, street-grid density, cinemas and theatres, bookshops.
- Old-Neighborhood: corner stores, hair and beauty shops (main-street signal), restaurants, laundromats, library, playgrounds, transit to her parents.
- Fresh-Start: building amenities, distance to water, newcomer share, age 25-34 share, building year, gyms, bars within a mile.
- Little-City: restaurants, train station distance, cinemas and theatres, shops, farmers' market, bars within a mile.
- Room-to-Breathe: sq ft per dollar, a separate bedroom, park area, parking, woods.
- Quiet-Street: violent and property rates, distance from the motorway, parking, woods, detached-house share.

`scripts/rank_v1_backup.py` keeps version 1.

## After the independent check (2026-11-15) — see `docs/REPAIRS_AFTER_INDEPENDENT_CHECK.md`

**Gate facts and what counts as settled.**
- Elevator: confirmed in the evidence pass, stated on the listing or amenities page, or an official record. A harvester's or checker's
  inference ("6+ floors") is `inferred` and is an open fact.
- Floor: confirmed, or stated on the page. A floor read from a simple unit label ("4F", "305") that comes out at 3 or higher is accepted,
  marked "read from the unit number", with the tour question "Confirm the floor". Any other inferred floor (floor 2, or a label with a
  separator, a building prefix or four digits) and an unknown floor are open facts.
- Dogs: allowed must be stated or confirmed. A size word ("small dogs") with no pound figure is an open fact. A policy that conflicts between
  two aggregators is an open fact; the building's own site or its manager's page outranks an aggregator.
- One open fact: ranked, held in `data/needs_confirmation.csv` with the question. Two or more: sketchy, excluded.

**Shown.** Clean on every gate fact, not an avoid building, **seen live in the evidence pass** (live status `live` or `changed`), at most 2 per
building (counted on `building_id`, duplicates of a unit removed first), best 10 per neighborhood. Clean candidates without a live check go to
`data/needs_live_check.csv` and are not shown. `scripts/check_registry.py` fails the run if a shown unit breaks any of these rules.

**Scoring changes.** Pool, doorman and the other amenity tests reject negatives and near-misses ("Pool table", "none listed", "no doorman
stated"; a virtual doorman counts as controlled access only). A confirmed "no weight limit" scores as the best weight policy. The
"cost lines stated" variable now counts the lines of the cost receipt that are stated rather than estimated or unknown.
