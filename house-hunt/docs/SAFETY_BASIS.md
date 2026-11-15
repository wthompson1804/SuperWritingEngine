# Safety basis (draft for Will's approval, 2026-11-15)

Built by `scripts/crime_benchmarks.py` → `data/reference/crime_benchmarks.csv`, `data/neighborhood_safety.csv`.

## Yardsticks (violent crime per 1,000 residents per year)

| Yardstick | 2023 | 2024 | 2025 | Source |
|---|---|---|---|---|
| United States | 3.86 | 3.63 | 3.30 | FBI Crime Data Explorer, national monthly rates summed |
| NY metro: every FBI-reporting agency in the 2-hour search area, population-weighted | 3.54 | 3.67 | 3.43 | FBI CDE agency data |
| New York City, all precincts (NYPD complaint categories) | 5.33 | 5.46 | 5.37 | NYPD complaint data |
| Local: the neighborhood's own county (or NYC for precincts) | varies | | | same sources |

Motor vehicle theft per 1,000: US 3.26 / 2.57 / 2.00; metro 1.82 / 1.64 / 1.43; NYC 1.81 / 1.61 / 1.54.

Each neighborhood gets three ratios for violent crime and for vehicle theft: vs US, vs metro, vs local.
Caveats: rates describe the police agency or NYPD precinct, not the block; NYPD categories are NY Penal Law
(felony assault is not exactly FBI aggravated assault); FBI years with silent gaps are skipped.

## Distribution of the 103 neighborhoods with passing units (violent rate vs US average)

| Band | Neighborhoods | Units | Examples (rate per 1,000) |
|---|---|---|---|
| Under half the US average | 34 | 157 | New Rochelle 1.6, White Plains 1.1, Maplewood 0.5, Westport 0.3, Teaneck 1.3 |
| Half to the US average | 26 | 186 | Bayonne 2.8, Hackensack 2.4, Flushing 2.6, Forest Hills 2.1, Kew Gardens 3.1 |
| 1 to 1.5 times | 16 | 167 | Jersey City 4.9, Yonkers 3.9, Jackson Heights 4.8, Astoria 3.7, Sunnyside 3.9 |
| 1.5 to 2 times | 11 | 51 | Newark 5.2, Elmhurst 6.1, New Brunswick 5.1, Washington Heights 5.3-6.0, Hempstead 5.6 |
| 2 times or more | 16 | 49 | Jamaica 9.8, Mott Haven 17.2, East Harlem 11.2, East New York 8.4, Ocean Hill 12.1 |

## Proposed rule (not yet approved)

Safety gate: a neighborhood is excluded when its violent-crime rate is 1.5 times the US average or more.
That removes 27 neighborhoods and 100 units, and keeps 75 neighborhoods and 509 units.
