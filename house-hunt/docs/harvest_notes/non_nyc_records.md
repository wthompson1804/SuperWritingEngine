# Official records and police-located incidents outside NYC (harvest notes)

Run of 2026-11-15. Scripts: `scripts/non_nyc_records.py` (idempotent; rewrites the output whole; `--no-fetch` reruns
from cache), `scripts/non_nyc_probe.py` (robots check including groups that name Claude, 2.5 s per host, cache in
`raw/non_nyc_records/`). Outputs: `data/reference/non_nyc_record_sources.csv` (21 sources checked),
`data/evidence/non_nyc_records.csv` (837 rows). Buildings covered: round 1 and round 2 candidates.
`docs/SOURCES.md` was not edited (shared file); the findings are in the sources CSV.

## What is usable

Two sources. Everything else was blocked, unreachable, login-only, or not address-level.

### 1. New Jersey housing inspections (all NJ candidates)
NJ Department of Community Affairs, Bureau of Housing Inspection, public property search on the DCA Service Portal
(`serviceportal.dca.nj.gov`, no login, no robots.txt). Per building: the portal's own search query, the public
"View Property Details" page, and the inspection report PDFs linked from it (read with `pdftotext`).

- 148 NJ candidate buildings searched; **107 matched** a registered property at the same house number and
  municipality; **60 have at least one inspection report since 2021-11-15 that could be read** (112 reports).
- Each report row gives: inspection type and date, violations open at that inspection, how many are life-safety,
  violations listed as abated, units, and keyword mentions in the open violations (elevator, heat or hot water,
  pests, mold or leaks, fire safety).
- Summary rows per building: `bhi_latest_report_open_violations` and `bhi_cyclical_violations_per_100_units`
  (with the median over NJ candidates, 21.5 per 100 units, and a "double the median" test: 20 of 57 buildings).
- Inspected within the last 12 months with violations still open at the latest report: Avalon Boonton (58, June 2026),
  The Current on River, Hackensack (54, Sept 2026), Bay One, Bayonne (25, June 2026), One Ten at the Enclave, Jersey
  City (23, Dec 2025), The Mint, Rahway (15), ELK Harbor View, Atlantic Highlands (210, July 2026).

Limits, plainly:
- The state inspects about every five years. A report shows the building on the inspection day; it is not a running
  complaint log like NYC's. A building last inspected in 2022 says little about the last 6 months.
- "Open" means open on that date. Abatement shows only in a later reinspection report.
- Most violations are fire-safety items (smoke detectors, door closers). Counts are not comparable to NYC HPD classes.
- Matching is by house number plus a street word within the municipality or ZIP. `match_note` names the BHI record
  matched; a few may be a different building at the same number (check the name), and complexes registered under
  another address are `not_found`. `not_found` does not mean unregistered.
- Keyword counts are mentions in the report text, not violation counts.

### 2. Jersey City police incidents (17 Jersey City candidates)
JC IMPACT crime data portal (`impact.jcnj.org`, Jersey City Police Department). Block-level incidents with
coordinates, read from the page's own JavaScript bundle, which robots.txt allows. The `.json` and `.pdf` files that
robots.txt disallows were not fetched. Use approved by Will through the coordinator.

- **Window: 2025-12-28 to 2026-11-11, about 10.5 months, not 24.** Every row states it.
- Stolen vehicles + thefts from autos within 250 m: median over the 17 candidates is 5. At least double the median:
  Birch House, 49 Fisk St (24); The Beacon, 20 Beacon Way (14); 3 Journal Square (14); 55 Jordan Ave (11).
- Points are geocoded to the block, so the 250 m circle is approximate. Figures are preliminary per the portal.

## What is not usable, and why

| Place | Result |
|---|---|
| Jersey City open data (`data.jerseycitynj.gov`) | robots.txt disallows `/api/` and downloads; kept off limits |
| NJ elevator records (DCA Elevator Safety portal) | search page shows nothing without signing in; not attempted |
| Newark | open data portal returns 503; police and city sites answer robots.txt with 403 |
| Yonkers | city site answers robots.txt with 403; code-enforcement page unreachable |
| New Rochelle | city site unreachable from here |
| White Plains, Hackensack, Bayonne, Harrison (NJ) | home pages show no blotter, crime map or violation lookup; not searched page by page |
| Stamford | city site answers robots.txt with 403; nothing on data.ct.gov |
| CT and NY elevator records | no dataset on data.ct.gov or data.ny.gov (outside NYC) |
| CrimeMapping.com | terms prohibit harvesting; CityProtect and Community Crime Map are script-only |
| Other towns (Bloomfield, Englewood, Weehawken, Edgewater, West New York, Westport, Hempstead) | not checked site by site |

No usable source was found for New York (Westchester, Nassau) or Connecticut buildings: not for code violations,
elevators, or police incidents. Those buildings still rest on dated tenant and news reports only.

## For Will
- The NJ inspection reports are the nearest thing to NYC's HPD record. They are not yet wired into `avoid.py`;
  a rule would need his thresholds (for example: inspected in the last 12 months with elevator or heat violations
  open, or cyclical violations per 100 units at least double the NJ candidate median).
- The Jersey City car-crime test uses 10.5 months. Four buildings are at least double the median.
