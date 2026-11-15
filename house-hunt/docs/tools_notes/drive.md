# drive: free-flow driving and tolls to Jamaica LIRR

Module: `scripts/tools/drive.py`. Written 2026-11-15.

```python
from scripts.tools.drive import drive, tolls_for_route
drive(40.7196, -74.0431)           # both directions, itemised tolls
tolls_for_route(osrm_route_json)   # one OSRM route (or a whole response: its first route)
```

- Self-test: `python3 scripts/tools/drive.py` (the six contract points; add `--json` for one full result).
- Rebuild the reference tables: `python3 scripts/tools/drive.py --build-reference`.

## What `drive(lat, lon)` returns

| Key | Content |
|---|---|
| `to_jamaica`, `from_jamaica` | `miles`, `minutes_free_flow`, `main_roads`, `tolled_facilities` (list), `toll_ezpass`, `toll_free_alternative`, `alternatives_returned` |
| `miles_to_jamaica`, `minutes_to_jamaica`, `..._from_jamaica` | flat copies of the headline numbers |
| `toll_round_trip_ezpass` | weekend off-peak sum, with `items`, `complete`, and `known_subtotal` + `reason` when a rate is missing |
| `toll_round_trip_ezpass_weekend_peak` | the same for Saturday/Sunday 11 a.m. to 9 p.m. |
| `toll_round_trip_mail` | Tolls by Mail (or cash) sum |
| `toll_free_alternative` | `exclude_toll_supported` (false) and the toll-free minutes each way when OSRM returned such a route |
| `saturday_traffic_minutes_*`, `sunday_traffic_minutes_*` | `not_found`, reason "needs a traffic-aware routing key" |

Every value is a dict with `value`, `value_type` (found / estimate / not_found), `source_url`, `retrieved_at`
and `method` (or `reason`). Times and miles are `estimate` with method "OSRM free-flow, no traffic".
A toll sum is `not_found` (value null) as soon as one charged facility has no official rate; the part that
is known is in `known_subtotal`. It is never filled with a guess.

## Routing

- Public OSRM demo server, `router.project-osrm.org`, `overview=full&geometries=geojson&steps=true&alternatives=3`.
  One request per direction, at most 1 request/second (`lib.py` throttle). Same URL form as
  `scripts/p1_drive_fetch.py`, so the 98-area cache in `raw/osrm/` is reused. New lookups are cached in
  `raw/big/drive/osrm/` (git-ignored, about 0.1 to 0.5 MB per request, re-fetched if missing).
- The fastest route (`routes[0]`) is the one reported. No traffic data: real weekend times will be longer.
- `exclude=toll` was tested on 2026-11-15 and **does not work on the demo server**: HTTP 400
  `{"message":"Exclude flag combination is not supported.","code":"InvalidValue"}`. The toll-free alternative is
  therefore only the fastest of the (up to 3) routes OSRM itself returned that uses no tabulated toll. When none
  qualifies the value is `not_found`; a toll-free route may still exist.
- The demo server does not return road classes, so OSRM cannot tell us which segments are tolled.

## Toll detection (`tolls_for_route`)

1. **Crossings and barriers:** each facility has one to four points on its roadway. A route uses the facility when
   it passes within 60 m of a point (120 m for the Cuomo Bridge's twin spans). Distances are point-to-segment, so
   sparse geometry on long straight spans is not a problem. The points were checked with OSRM `/nearest` on
   2026-11-15: the nearest road carries the facility's name in every case except three, where OSM uses another
   name (Henry Hudson Bridge = "Henry Hudson Parkway", Cross Bay Bridge = "Cross Bay Boulevard", Atlantic Beach
   Bridge = "Nassau Expressway") and the Harriman barrier (unnamed ramp; coordinates from the Thruway dataset).
2. **Direction:** for one-way tolls the route's compass heading at the facility is compared with the tolled
   heading (within 90 degrees). A crossing used in the free direction is listed with `charged: false`, rate 0.
3. **RFK Bridge:** three spans, one toll per trip.
4. **Thruway ticket system (north of Woodbury):** the route must pass at least two of the points Woodbury barrier
   ("15"), 17, 18, 19, 20, 21; the fare is the table value between the outermost two.
5. **NJ Turnpike and Garden State Parkway:** step name/ref (`NJTP`, `New Jersey Turnpike`, `GSP`,
   `Garden State Parkway`) finds the stretch on the road. Entry and exit are then matched by coordinates against
   the interchange list of the NJTA toll calculator (nearest interchange to the stretch's first/last point within
   2.5 km, else the first/last interchange passed within 1.2 km). The fare for that pair comes from
   `njta_tolls.csv`; an unseen pair is fetched once from the calculator, cached in `raw/njta/` and appended.
   A stretch tagged NJTP that passes no interchange (the I-95 roadway between US 46 and the George Washington
   Bridge) is treated as outside the tolled section: no toll, `value_type` estimate.
6. **Manhattan congestion relief zone:** the route is densified to 30 m and tested against the MTA's published
   geofence polygon (`data/reference/crz_geofence.json`). The polygon already leaves out the FDR Drive, West Side
   Highway/Route 9A, Battery Park Underpass and Carey Tunnel connections. Counted once per round trip.

## Reference tables

| File | Content |
|---|---|
| `data/reference/tolls.csv` | one row per facility and rate type (74 rows). Columns asked for, then `facility_id`, `scenario`, `value_type`, `notes` |
| `data/reference/njta_tolls.csv` | every NJ Turnpike interchange pair (435 pairs, two rate types) plus the Parkway pairs looked up so far |
| `data/reference/njta_interchanges.csv` | interchange coordinates from the NJTA calculator page |
| `data/reference/crz_geofence.json` | MTA geofence polygons from data.ny.gov |

`scenario` says which sum a row feeds: `weekend_offpeak`, `weekend_peak`, `all`, or `weekday_offpeak` (not summed).

### Sources and what was found

| Agency | Source used | Passenger car, E-ZPass / mail | Status |
|---|---|---|---|
| MTA Bridges and Tunnels (9 crossings) | none reachable | not_found | **Blocked.** mta.info returns 403 (Akamai) for the toll pages, its PDFs and robots.txt. e-zpassny.com (Incapsula) and the NYCRR site (Cloudflare) are also walled |
| Port Authority (6 crossings) | panynj.gov tolls page, read from its JSON model | $14.79 off-peak, $16.79 peak / $23.30 | found. Peak includes Saturday and Sunday 11 a.m. to 9 p.m. Collected entering New York only |
| Thruway: Cuomo Bridge | `gmmcb-toll-charts.pdf` | $7.25 / $12.69, from 2026-01-01 | found. Southbound only |
| Thruway: Yonkers, Harriman, New Rochelle | `gantry-rate-toll-charts.pdf` | $1.25, $1.25, $1.74 / $2.19, $2.19, $3.05 | found. New Rochelle northbound only |
| Thruway ticket system 15 to 21 | `2024-ny-e-zpass-cpm.pdf`, `2024-non-ny-tbm-cpm.pdf` | e.g. 15 to 17 $1.39 / $2.44 | found |
| Thruway barrier locations and tolled directions | data.ny.gov `7jkf-259w` | | found |
| NYS Bridge Authority (5 bridges) | nysba.ny.gov/toll-rates | $1.65 / $2.15 | found. The page does not state the direction |
| NJ Turnpike | NJTA toll calculator | per pair; "Peak/Weekends" and "Off Peak" | found. The peak rate applies all weekend |
| Garden State Parkway | NJTA toll calculator | per entrance, exit and direction | found for pairs looked up |
| Congestion relief zone | Governor's release of 2024-11-14; geofence data.ny.gov `srxy-5nxn` | $9 daytime, once per day / not_found | found (E-ZPass). Daytime hours, mail rate and crossing credits not_found |
| Atlantic Beach Bridge (extra) | ncbaabb.com `2024-Toll-Rate-Schedule.pdf` | $3.00 / $4.00 cash | found. Added because the fastest Long Beach route uses it |

### The MTA gap, and how to close it

Any route over the Whitestone, Throgs Neck, RFK, Verrazzano, Henry Hudson, Cross Bay or Marine Parkway bridges,
or through the Queens-Midtown or Carey tunnels, has `toll_round_trip_ezpass` = not_found with a `known_subtotal`.
That is most routes from the Bronx, Westchester, Connecticut, the Hudson Valley, Staten Island and New Jersey.

- The New York State Register of 2025-07-16 (dos.ny.gov, appendix page 87) prints a TBTA schedule ($7.63 major
  crossings, $3.50 Henry Hudson, $2.86 Rockaway bridges). It is the **proposed** schedule (I.D.
  TBA-28-25-00011-P), not the adopted one, so it is not used. No adoption notice with rates was found in the
  Register issues from October 2025 to January 2026.
- A Delaware River Joint Toll Bridge Commission comparison PDF lists "Proposed 2026" MTA rates. Another agency's
  proposal figure is not an official current rate, so it is not used either.
- To close the gap, read the rates on mta.info in a browser and edit the nine MTA rows in `tolls.csv`:
  set `ezpass_rate`, `mail_rate`, `effective_date`, `retrieved_at` and `value_type = found_manual`. Rows marked
  `found_manual` survive `--build-reference`. The same works for the congestion zone row.

## Weekend scenarios

- `toll_round_trip_ezpass` = Saturday or Sunday outside 11 a.m. to 9 p.m.: Port Authority off-peak rate, NJ Turnpike
  Peak/Weekends rate (it has no weekend off-peak), congestion zone daytime rate, flat rates elsewhere.
- `toll_round_trip_ezpass_weekend_peak` = Saturday or Sunday 11 a.m. to 9 p.m.: Port Authority peak rate.

## Caveats

- Free-flow only. Saturday and Sunday traffic times are not_found until a traffic-aware routing key exists.
- The fastest OSRM route is not always the one a driver would take to avoid tolls (it sends Jersey City through the
  Holland Tunnel and the congestion zone: $23.79 round trip).
- E-ZPass rates assume the home agency's tag: NY E-ZPass for the Thruway and MTA, NY or NJ E-ZPass for the Port
  Authority. Resident, commuter and carpool plans, mid-tier rates and congestion-zone crossing credits are not
  applied. A trip through the Lincoln, Holland, Queens-Midtown or Carey tunnel into the zone may be overstated by
  the credit.
- "Eastbound only" for the Bridge Authority bridges and "both directions" for the Atlantic Beach Bridge are general
  knowledge; no official page reached here states them.
- Port Authority car rates: the page's table is titled "July 2026 Toll Rates" and gives no start date for cars.
- Thruway fixed and ticket rates are the "current" 2024 schedule; the next change is 2027-01-01.
- Tolls outside the table are not detected (Pennsylvania Turnpike, Delaware River bridges, any other toll road).
  Connecticut has none.
- Congestion zone edge cases (Queensboro Bridge upper-level exits north of 60th Street, Brooklyn Bridge ramps
  straight onto the FDR) depend on OSRM's exact path through the geofence.
- Garden State Parkway lookups need the NJTA site the first time a pair is seen (one request). If it is
  unreachable the item is not_found.

## Run time

- First lookup of a point: two OSRM requests, about 2 seconds in total (throttled to 1 request/second).
  1,000 buildings take about 35 minutes once.
- Cached lookup: 0.01 to 0.08 seconds (six test points in 0.15 seconds).
- `--build-reference`: a few seconds from cache. From nothing it re-fetches about 15 pages and PDFs, and
  `njta_tolls.csv` (committed) keeps the 435 Turnpike pairs so they are not requested again.

## Test results (2026-11-15)

| Point | To Jamaica | From Jamaica | Round-trip E-ZPass, weekend off-peak |
|---|---|---|---|
| Jamaica station | 0 mi, 0 min | 0 min | $0 |
| Forest Hills | 3.0 mi, 7.5 min | 8.0 min | $0 |
| Long Beach NY | 13.9 mi, 25.3 min | 26.2 min | $6.00 (Atlantic Beach Bridge both ways); toll-free alternative 28.2 / 29.6 min |
| Stamford CT | 34.5 mi, 51.9 min | 49.6 min | not_found: Whitestone Bridge both ways; known part $1.74 (New Rochelle, northbound) |
| Jersey City Grove St | 16.3 mi, 34.1 min | 33.2 min | $23.79 (Holland Tunnel $14.79 + congestion zone $9); $25.79 at weekend peak |
| Beacon NY | 77.3 mi, 106.2 min | 103.0 min | not_found: Whitestone Bridge both ways; known part $19.22 (Thruway 15 to 17 twice, George Washington Bridge, Newburgh-Beacon Bridge eastbound) |

Another 44 points across New Jersey, Staten Island, Manhattan, the Bronx, Westchester and the Hudson Valley were
run to exercise every facility type except the Bayonne, Henry Hudson, Mid-Hudson and Bear Mountain bridges, the
Throgs Neck Bridge and the Carey Tunnel, which no test route used.
