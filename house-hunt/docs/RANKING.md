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
