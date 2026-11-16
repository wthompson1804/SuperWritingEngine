# Plan v2: what the UI needs from the data (2026-11-15)

Inputs: `docs/UX_BRIEF_2026-11-15.md` (three floors and a table, four moments, four limit sliders, snapshot)
and the **December 1, 2026 move-in**. This file supersedes the phase priorities in the handoff brief where the two conflict.
Items marked **[decision]** wait on Will.

## 1. The biggest change: from area-level to unit-level facts

The original plan measured everything at an area centroid. The side-by-side table and the sliders compare
**held units**, and its sentences use real units ("30 more minutes each way to your parents"). So every moment
needs values **per building**, not per area. Area centroid values stay as the Neighborhoods-floor context.

New per-building fields, computed from the building's geocoded address:

| Need | Field(s) | Source / method |
|---|---|---|
| Sunday at parents' | `drive_min_sun_eve_to_parents`, `drive_min_sat_to_parents`, `drive_miles`, `tolls_round_trip`, `transit_min_door_to_door`, `transit_transfers`, `transit_last_train_back` | Routing from the building to the parents' point; tolls from the official tables (the Phase 1 drive agent builds the lookup); transit router from the Phase 1 transit agent |
| 9pm dog walk | `park_nearest_m`, `dog_park_nearest_m`, `green_area_400m_ha`; `crime_evening_250m` (NYC and Philadelphia only: incidents 19:00–24:00 within 250 m, 3 years); `streetlight_complaints_250m` (NYC 311) | OSM extract (Phase 1 OSM agent); NYPD / OPD point data |
| Saturday night + parking | `bars_restaurants_800m`, `music_venues_1600m`; `parking_type`, `parking_fee`, `parking_gated`; `veh_theft_250m`, `theft_from_vehicle_250m` (NYC, Philadelphia); `overnight_street_parking_rule` (municipal code) | OSM; listing and building page; NYPD; municipal codes (Phase 5 parking rules move up to Phase 2) |
| Workday at home | `sqft`, `laundry`, `fiber_available`, `road_noise_db`, `cafes_coworking_800m` | Listing; FCC (login wall; see §5); OSM |
| Money row | `listed_rent`, `all_in_estimate`, `price_seen_at`, plus area-level `local_income_tax`, `electric_est` | Listing; Phase 1 money |
| Space row and slider | `sqft` (often missing), `beds` | Listing. Fill rate is a risk; show "sq ft not listed" rather than guess |

## 2. The sliders need comparable numbers

| Slider | Proposed definition | Problem |
|---|---|---|
| Monthly cost | `all_in_estimate` where complete, else listed rent with a "+ fees unknown" badge | All-in is often incomplete |
| Minutes to Mom and Dad | **Sunday-evening drive, door to door**, one way. Transit as a secondary label. **[decision]** drive or transit as the slider | Needs a **traffic-aware routing key**. OSRM free-flow understates Sunday-evening LIE, Belt and Van Wyck times. Without a key the slider runs on estimates |
| Safety | Rate per 1,000 residents of violent crime, plus motor-vehicle theft, at the **finest common geography**: NYPD precinct, municipal PD, Philadelphia district | Geographies aren't comparable: Nassau and Suffolk County PD cover over a million people each, versus village PDs of 20k. Point-level data exists only for NYC and Philadelphia. Any cross-state safety slider has to show its geography. **[decision]** accept a coarse safety slider, or make safety a label rather than a slider |
| Space | sq ft | Missing on many small-landlord listings |

## 3. Lives (portals)

New table `lives.csv`: life_id, title, member area_ids, the defining facts (with metric references), the honest catch
(sourced), and per-moment fact pointers. Every life must have **the same four scenes filled from the same fields**
(the brief's narrative-fairness rule), so coverage is checked **per life × moment**, not just per area.
Grouping areas into 5–6 lives is a judgment call. I'd draft it from the Phase 1 data with the rule for each life
stated, for Will and Lamia to approve. **[decision]**

## 4. Neighborhoods floor

- "What $2,400 buys here": per area, from listings at $2,200–2,600 **of any move-in date** (so `after_dec1`
  listings are kept for this statistic): median sq ft, share with parking, share with in-unit laundry, share with elevator, and the count behind each.
- "You'll love / Gives us pause": built from facts plus voices. **Voices will be thin:** Reddit, Yelp, Niche, City-Data
  and Nextdoor are off limits by robots rules, and YouTube is walled. Openigloo covers NYC buildings only. Expect
  mostly fact-based bullets and few quotes outside NYC.
- Map with the parents pinned: needs the parents' point. **[decision]** Use Jamaica station (current) or a nearby
  intersection. I'd store an intersection, not their address, since this repo holds the data.

## 5. Units floor and the Dec 1 constraint

- Harvest: studio and 1BR, listed rent ≤ $3,000, dogs not prohibited, from the sources that permit it (SOURCES.md:
  Zumper, Trulia, Craigslist HTML, Apartment List, AvalonBay, Fairfield, Greystar via browser and sitemap).
  StreetEasy, Zillow listings, Apartments.com and RentHop are **off limits**: there's no automated access to much of NYC's small-landlord stock.
- Tag `move_in_fit`. The Units floor shows `ready_by_dec1` and `unknown` (the tour question becomes "can I move in Dec 1?").
- Order: by drive distance to Jamaica (Queens, Nassau, Brooklyn and SI, Bronx and lower Westchester, then the rest), so the most
  useful inventory exists first.
- Tour questions per unit, generated from unknowns and red flags (dogs unknown, fees unknown, parking unknown, car-crime facts).
- **Snapshot rule:** every price carries `price_seen_at`. Re-check links and prices just before the page goes to Lamia.

## 6. What drops or shrinks

| Item | Change | Why |
|---|---|---|
| Phase 4 voices at 30 per area | Cut to whatever the permitted sources give | Sources are blocked; no UI element needs volume |
| Phase 5 development pipeline, transport projects | Drop for now | No moment uses them |
| Phase 5 parking rules, dog rules, car-crime news | **Move up** into Phase 2 for areas with Dec 1 inventory | Directly feed the dog walk and parking moments |
| Phase 1 new supply (permits) | Keep what the agent delivers, but don't extend it | Not used by any moment |
| Phase 3 full profiles of 300 buildings | Red flags and public records for buildings with Dec 1 units only | Time |
| Philadelphia | Benchmark metrics only (already decided). Not a life, no units | About 2 hours away; Will chose benchmark only |
| Rankings | None. Only factual labels computed from data ("most space for the money") | The brief's "exploratory, not recommender" reading |

## 7. Timeline reality

The finish line is "two or three places to go see". To sign for Dec 1, she likely needs to tour by about **Nov 22–23**
and apply right after. Working back: units harvested and checked by about Nov 19, the tool usable by about Nov 20. The UI build is on the critical path, not only the data.
