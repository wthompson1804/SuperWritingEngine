# Life here, New Jersey short version (2026-11-17)

Output: `data/reference/life_here_facts_nj.csv` (697 rows, 95 buildings). The header and columns are the same as
`life_here_facts.csv`: `building_id, neighborhood_id, moment, place_name, place_kind, fact, schedule, lat, lon,
source_name, source_url, retrieved_at, confidence, notes`. `life_here_facts.csv` was not touched.

**Candidates.** From `data/ranked_units.csv`: `shown` true, `state` NJ, `listed_rent` <= 2000, grouped by
`building_id`, minus the building_ids already in `life_here_facts.csv`. That gives 95 buildings in 28 neighborhoods. The
CSV is ordered by best `shown_rank` (neighborhoods in the order their best building appears), with neighborhood rows
first in each block.

**Rebuild.** The CSV is written from scratch on every run: `build.py` imports one rows file per area (`h_*.py`), adds
the route rows and writes the file sorted. The upsert key is (building_id, moment, place_name, fact), so a re-run never
duplicates rows and gives byte-identical output. The build sources are copied to `raw/life_here_nj/build_src/`. Pages
are cached in `raw/life_here_nj/pages/` (`sha1(url)[:16]` with `.html`, `.txt` and `.meta.json`; the meta file holds the
url, final url, status and retrieved_at). The robots files are in `raw/life_here_nj/robots/`. Rows that reuse a page from
the first round (Essex County parks, Bloomfield Center, NPS Edison, Newark Happening, NJ Monthly Six Points) read it
from `raw/life_here/pages/` and keep that page's original retrieval time.

| Moment | high | medium | total |
|---|---|---|---|
| neighborhood | 19 | 3 | 22 |
| dog_walk | 114 | 50 | 164 |
| weekday | 10 | 150 | 160 |
| saturday | 105 | 66 | 171 |
| sunday | 63 | 117 | 180 |
| **all** | **311** | **386** | **697** |

150 rows come from OpenStreetMap alone (nearest mapped supermarket, café or park) and are medium. 95 are route rows,
also medium.

## Method

- **Mapped places first.** The building's point and its join to `data/enriched/<hash>.json` follow
  `scripts/concierge_data.py: enriched_for`: the crosswalk keys, `sha1(key)[:14]`, and the nearest key. Named places
  near each building came from the project OSM index (`raw/big/osm/places_index.pkl`, read only, data of 2026-11-14):
  cafés, bars, restaurants and supermarkets within 1.6 to 2.5 km, dog parks within 4 km, and named parks over 0.5 ha
  within 1.6 km. lat/lon is filled only from OSM, and the OSM object is named in `notes`. **No distances or walking times
  are stated anywhere.** Where a row says "nearest", it means nearest in OSM, and the distance itself is left out.
- **Then the web, for the important places.** WebSearch was used only to find pages. Every fact was read on the page
  itself, fetched with curl through an honest UA, robots.txt checked first (the Claude-User group where there is one,
  otherwise `*`), 3.5 s or more apart per host, one attempt per URL, no retry on 4xx. A 401, 403 or 429, or a bot-wall
  page, ends the host. Hosts already in `raw/_host_kill_shared.json` and the off-limits list were never contacted.
- **Confidence.** high means an official page (county or city parks, NPS, township, tourism office) or the place's own
  site confirms the fact as current. medium covers OSM-only rows, press and magazine write-ups (NJ Monthly, Jersey
  Digs, local radio and news), directories (GetOutsideNJ), year-old or older articles, and route rows.
- **Sunday route rows** (one per building) give the road sequence from our own OSRM result
  (`drive.to_jamaica.main_roads` in `data/enriched`), with the OSRM URL and its original retrieval time. Nothing was
  re-measured.
- **Shared neighborhoods.** Each neighborhood was researched once. dog_walk and weekday rows are attached per building
  (by which park, dog run or café OSM puts nearest), and saturday and sunday rows go to every building in the area.
  Newark was split into North Ward/Branch Brook, Ironbound, Vailsburg, West Side and South Ward groups. Paterson rows
  for the Great Falls and Garret Mountain go only to the buildings that have those parks mapped nearby.
- **Not collected:** anything on racial, ethnic or religious makeup (cuisine and business descriptions only; the
  population figures in the NJ Monthly and Jackals pages were left out), crime, distances.

## What was found, by area

| Area (buildings) | Dog walk | Weekday | Saturday | Sunday |
|---|---|---|---|---|
| Paterson (17) | DeCando dog park on River St (Paterson Times, 2017); Great Falls NHP leash rules (NPS); Garret Mountain for 21st Ave | Silk Café by the falls (2025 report); OSM markets | Jackals at Hinchliffe ($10 seats, $5 Silk City Fridays); Palestine Way on Main St; Market St restaurants (NJ Monthly) | Great Falls grounds (NPS) |
| Newark (19) | Branch Brook Park and Dog Park; Independence Park and Riverfront Park (Ironbound); Vailsburg Park and its Dec 2023 dog park; West Side Park; Irvington Park | OSM cafés and markets | Cherry Blossom Festival (April); Ferry Street; Portugal Day (June); River Day (June) | Branch Brook; Weequahic Park; Portugal Day parade |
| Jersey City (10) | Lincoln Park enclosed dog run (Visit Hudson); otherwise nearest OSM park | Snapdragon Coffee (2019 feature); OSM | Loew's Jersey Theatre, reopening with shows from Nov 2026 | route |
| Bayonne (7) | Sirius and Oliva dog parks in Collins Park (city); Stephen R. Gregg Park | Tuesday farmers market at W 23rd and Broadway; Café Bello (city 2026 guide) | Broadway restaurants (city Dine Bayonne 2026) | Rutkowski Park; Union Grounds Coffee |
| West New York (4) | Donnelly Memorial Park dog park (Visit Hudson) | OSM | Bergenline Ave: La Pupusa Loca, Parriyas (NJ Monthly 2023) | Dulce de Leche bakery |
| Elizabeth (3) | Warinanco Dog Park, dawn to dusk (Union County) | OSM | Barcode; the Portugal Day Parade since 1978 (Visit Elizabeth) | Warinanco Park |
| Woodbridge (5) | Township dog park, Cliff Rd, Sewaren | OSM | Summerfest at Merrill Park (June); Wednesday concerts at Parker Press Park; Oak Tree Road (for Gill Lane) | Anchors Tiki Bar concerts; Oak Tree Rd buffets |
| Orange, East Orange, West Orange (7) | Monte Irvin Orange Park; Watsessing Dog Park | OSM | Hat City Kitchen live music (own site); Orange Park summer concerts | Edison NHP lab and Glenmont |
| Bloomfield (3) | Watsessing Park and Dog Park | Dinner Under the Stars (Fridays, late May to early Sept) | Six Points Pub | Brookdale Park and dog park |
| Burlington (1) | Riverfront Promenade (OSM) | **Evermore Coffee Roasters is in the building** (own site + city calendar); Food Truck Tuesdays | Wood Street Fair (Sept) | Carbs and Coffee, monthly Sundays |
| Long Branch (2) | City dog rules (beach Oct to Apr only, never the boardwalk); Seven Presidents (dogs Nov to Mar); Wolf Hill off-leash area | Cowabunga Coffee Roasters (Pier Village) | Pier Village restaurants | Seven Presidents off-season |
| New Brunswick (1) | Donaldson Park and its off-leash area (GetOutsideNJ) | Highland Park Friday market | Raritan Ave downtown; Harvest Moon on George St | route |
| Plainsboro (3), West Windsor (2) | Plainsboro dog park rules (township); the Preserve allows no pets | OSM | West Windsor Saturday farmers market (own site) | Plainsboro Preserve |
| Trenton (2), Lawrence (2) | Cadwalader Park (WHYY); D&R Canal (OSM) | OSM | Trenton Farmers Market, Wed to Sun (own site); Ellarslie museum events | Farmers market Sunday hours |
| Lopatcong (2) | OSM parks | none | Easton Farmers' Market across the river (Sat, May to Nov) | route |
| Boonton (1) | Grace Lord Park (Morris Canal) | three indie coffee shops on Main St (Jersey Digs 2024) | Main St galleries, Ombra | Grace Lord Park |
| Rahway (1) | **none** (the building's address is only "Rahway, NJ 07065") | none | UCPAC (own site); Rahway Is Happening | route |
| Hamilton, Hillsborough, Piscataway (1 each) | OSM; Sourland Mountain Preserve (Visit Somerset) | OSM | Piscataway: Harvest Moon; Hamilton and Hillsborough: none | Duke Farms (Hillsborough); otherwise route |

## Gaps

- **Buildings with a moment missing:** Rahway `b_bbae18b262` has no dog_walk or weekday rows, because its address is
  only the ZIP code and its point is not a real location. Plainsboro (3) and Lopatcong (2) have no weekday rows: no café
  or supermarket is mapped near them. Hamilton `b_7158f20e1b` and Hillsborough `b_f98b417aac` have no saturday rows.
- **Weekday is the weakest moment** (10 high out of 160). Most cafés and supermarkets are OSM-only. No laptop-friendly
  café was confirmed on its own page except Evermore (Burlington).
- **Dog rules that could not be read officially:** DeCando Dog Park, Paterson (no city page; county site refused us);
  Lincoln Park dog run hours; Berry Lane Park dog run (only directories; YIMBY refused us; Visit Hudson's `?p=` URL is
  disallowed by robots); Donaldson Park off-leash area (Middlesex County refused us); Sourland Mountain dog rules
  (Somerset County Parks refused us); Mercer County Park dog park (mercercounty.org refused us); Hamilton Veterans Park
  dog park (hamiltonnj.com refused us); the Lawrence Hopewell Trail (refused us).
- No events with confirmed 2026 dates for Monte Irvin Orange Park concerts or Weequahic Park (medium, "summer").

## Refusals this session (recorded in `raw/_host_kill_shared.json`, `by: life_here_nj`)

- `www.passaiccountynj.org`: 403 on robots.txt
- `www.nj.gov`: bot-challenge page on the Liberty State Park page (HTTP 200, small page matching the challenge pattern).
  The body was not saved for that one; later kills keep it in `raw/life_here_nj/pages/_killed_<host>.html`. **This host
  is shared with other scripts (state DEP, WIC lists).** A WIC PDF on the same host was read earlier in the session.
- `newyorkyimby.com`: 403
- `middlesexcountynj.gov`: 403 on robots.txt
- `thesunpapers.com`: 403
- `mercercounty.org`: 403 on robots.txt
- `www.hamiltonnj.com`: 403 on robots.txt
- `lhtrail.org`: 403 on robots.txt
- `www.somersetcountyparks.org`: 403

Not refusals, but not read: `www.visithudson.org/?p=…` (robots disallows query URLs; its path URLs were fine),
`goelizabethnj.com` without `www` and `hatcitykitchen.com/brunch` (DNS did not resolve).

## To check before display

- The Paterson dog park name "John DeCando Riverview Dog Park" is the OSM name. The Paterson Times calls it the John
  DeCando Dog Park (2017). It is not confirmed open on a city page.
- Silk Café (Paterson), Snapdragon (Jersey City), the Bergenline restaurants, La Tia Delia, Palestine Way and the Boonton
  businesses rest on articles from 2019 to 2026, not on the place's own page.
- The Bayonne farmers market season: Visit Hudson says June to November, the 2025 city notice says late May to late
  October. The row gives "late spring to fall".
- The Jackals row is a Friday deal and the Woodbridge Wednesday concerts are a weekday event. Both are filed under
  saturday as the going-out rows.
- The Newark Portugal Day rows rest on a magazine guide (medium). River Day 2026 was June 20, per the Newark City Parks
  listing.
- The Luna Stage and Hat City brunch rows were dropped: the pages read did not confirm the location or the hours.
