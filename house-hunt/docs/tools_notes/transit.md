# Transit lookup tool (`scripts/tools/transit.py`)

`route(lat, lon, when)` gives door-to-door public transit between any point and **Jamaica LIRR station**
(LIRR GTFS stop_id 102, 40.699608, -73.808530). Written 2026-11-15.

```python
import sys; sys.path.insert(0, "scripts")
from tools.transit import route
r = route(40.7196, -73.8448, "sat_midday")
```

| `when` | Direction | Departures sampled (every 15 min) | Service date |
|---|---|---|---|
| `sat_midday` | point → Jamaica | leave the door 10:00–13:00 (13) | Sat 2026-12-05 |
| `sun_evening_return` | Jamaica → point | leave Jamaica 17:00–20:00 (13) | Sun 2026-12-06 |
| `weekday_evening_return` | Jamaica → point | leave Jamaica 18:00–19:00 (5) | Wed 2026-12-02 |

Self-test: `python3 scripts/tools/transit.py` (add `--json` for full dicts, `--rebuild` to rebuild the network).

## What comes back

- `status`: `ok` or `not_found`.
- `fastest_minutes`, `median_minutes` (over the sampled departures that have a journey; waiting for the first
  vehicle counts), `minutes_by_departure`, `departures_sampled`, `departures_with_route`.
- For the fastest journey: `transfers`, `systems`, `lines`, `legs` (walks and rides with stop names, times and
  per-leg `fare_one_way`), `leg_summary`, `fare_one_way_total`.
- `last_departure_from_jamaica_sat`: latest time to leave Jamaica station on Saturday night (21:00 or later) and
  still reach the door by 05:00 Sunday, with the journey. `effectively_all_night` is true when that time is 03:00
  or later (the search stops at 05:00, so a value near 04:00 means service does not really end).
- `not_found` when no stop with service in that window lies within 1.5 km straight-line of the point (and the
  point is not within 1.5 km of Jamaica). It then carries `nearest_stop` and `nearest_rail_or_ferry_station`
  with their distance in km. Park-and-ride is out of scope.
- Every value carries `value_type`, `source_url` (the GTFS feeds the journey uses), `retrieved_at` and `method`.
  `value_type` is `found` for values read from current published timetables and `estimate` (with
  `estimate_reason`) when a journey uses a feed whose calendar had to be substituted. Walking minutes inside
  every door-to-door figure are modelled (see below); the `method` text says so each time.

## Sources

`data/reference/transit_feeds.csv` lists every feed with URL, retrieval time, the dates used and whether the
calendar was substituted. It is rewritten at each build. Feeds are downloaded by `scripts/p1_transit_feeds.py`
(manifest in `raw/transit/feeds_manifest.json`) or by `transit.py` itself through `lib.cached_get`, into
`raw/big/gtfs_transit/` (git-ignored).

Used, all with service on the three dates: LIRR, Metro-North, NYC Subway (with Staten Island Railway), NJ Transit
rail (with Hudson-Bergen Light Rail, Newark Light Rail, River Line), NJ Transit bus, PATH, SEPTA Regional Rail,
Staten Island Ferry, NYC Ferry, NY Waterway, NYC buses (NYCT Queens, Brooklyn, Bronx, Manhattan, Staten Island
feeds and MTA Bus Company), NICE (Nassau), City of Long Beach bus, Suffolk County Transit, Hudson Link, CTtransit.

- **NJ Transit**: `https://www.njtransit.com/rail_data.zip` and `bus_data.zip` downloaded without any login and
  cover 2026-09-15 to 2027-03-13 (rail) and to 2027-04-17 (bus), so the expired MobilityData mirror in `raw/gtfs/`
  is not used and no NJ Transit result is an estimate. Nothing was worked around.
- **Westchester Bee-Line**: the published feed's calendar ends 2025-08-31. The router uses its last Saturday,
  Sunday and Wednesday (2025-08-30, -31, -27) and marks every result that rides Bee-Line as `estimate`.
- **Norwalk Transit District**: HTTP 403 on the feed URL; left out.

Not included (no feed fetched): Amtrak, Transport of Rockland, Rockland/Orange/Dutchess/Putnam/Ulster county
buses, Huntington HART, Greater Bridgeport Transit, private commuter coaches (Coach USA, Academy, Lakeland,
DeCamp, Trans-Bridge), Seastreak, SEPTA city transit, AirTrain JFK and Newark, Roosevelt Island Tram.

## Method

1. **Merge.** Platforms collapse to their parent station. Trips are those active on the service date
   (`calendar.txt` plus `calendar_dates.txt`). `pickup_type` / `drop_off_type` = 1 are honoured. Stops without a
   time are skipped.
2. **Walking.** 4.8 km/h over straight-line distance × 1.3 (street detour; our assumption). Door ↔ stop: up to
   1.5 km straight-line, one stop only (no second walk to a neighbouring station). Station ↔ station transfers:
   up to 400 m straight-line, time = walk + 1 min, at least 3 min. Floors we set for deep terminals: Grand Central
   Madison 10 min, Penn Station (LIRR) 6 min, Grand Central Terminal 5 min. One pair beyond 400 m is linked on
   purpose: PATH 33rd Street ↔ LIRR Penn Station (about 480 m, 9 min); without it the router took a one-block
   bus. Changing vehicles at the same stop takes the feed's `min_transfer_time` when given (subway: mostly
   3 min; LIRR Jamaica 5 min), else 2 min. Trip-specific timed connections in `transfers.txt` are ignored.
3. **Search.** One end is always Jamaica, so everything is precomputed:
   - `sat_midday`: a profile connection scan backwards in time gives, for every stop and departure second, the
     best arrival at Jamaica;
   - the two return windows: one forward connection scan from Jamaica per sampled departure, with a separate
     label per number of rides (up to 6 rides), so the time-versus-transfers trade-off is exact;
   - Saturday night: a time-mirrored profile from Jamaica, 21:00 Saturday to 05:00 Sunday (Sunday's early-morning
     trips are appended after midnight).
   Journeys minimise **arrival time + 2 minutes per transfer**; reported minutes are the real minutes of that
   journey. A journey up to 2 minutes faster per extra transfer can therefore exist. The Saturday-night search
   uses no penalty.
4. **Lookup.** Stops within 1.5 km, then array look-ups. The Jamaica end includes the 3-minute walk to Sutphin
   Blvd–Archer Av subway and to bus stops within 400 m.
5. **Check.** `sat_midday` profile results were compared with an independent forward search from 60 random stops
   at three departure times (180 cases, 0 mismatches). Saturday-night latest departures were checked for 40
   stops: each one works and leaving one second later does not (80 cases, 0 failures).

## Fares

Per ride, from the feed's own fare tables only:

- found: SEPTA (GTFS Fares v2, contactless adult price, weekday or weekend rule), NYC Ferry, Suffolk County
  Transit (`FULL_FARE`), and any other feed with one unambiguous `fare_attributes` fare.
- `not_found`: LIRR, Metro-North, NYC Subway and buses, NJ Transit, PATH, NICE, CTtransit, Staten Island Ferry
  (their GTFS carries no fare table). `fare_one_way_total` is `not_found` unless every ride has a fare.
  Free transfers between rides are not modelled.

## Performance

- Build: about 1 minute on 4 cores (pure Python + numpy), 226 MB pickle at
  `raw/big/transit/network_v4.pkl`, rebuilt automatically when missing.
- Load: about 0.5 s once per process. Lookup: about 4 ms per call (600 random points measured).
- Network: about 47,000 stops, 238,000 walking-transfer pairs, 0.4–1.3 million vehicle hops per window.

## Caveats

- Scheduled times only: no delays, no planned-work changes beyond what the feed holds for that date.
- One date stands for each day type. Weekday is Wed 2026-12-02.
- Walking is straight-line × 1.3, not a street route; rivers, highways and station layouts are not seen. A stop
  1.4 km away across a highway counts as reachable.
- Buses are included, so a point can be `ok` on a slow or infrequent bus. Check `departures_with_route`,
  `median_minutes` and the legs before treating a place as transit-served.
- With no penalty in the Saturday-night search, the last-departure journey can include very short hops.
- The return windows cap journeys at 6 rides and 6 hours; `sat_midday` journeys must reach Jamaica by 19:30.
- Line names are what each feed publishes (LIRR trains are named by branch, PATH by colour code, Bee-Line by
  zero-padded number).
