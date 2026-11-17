# Life here: Connecticut and New York buildings, round 2 (2026-11-17)

Output: `data/reference/life_here_facts_ctny.csv` (358 rows, 44 buildings, 23 neighborhoods). The header is the same as
`life_here_facts.csv`: `building_id, neighborhood_id, moment, place_name, place_kind, fact, schedule, lat, lon,
source_name, source_url, retrieved_at, confidence, notes`. The CSV is rebuilt from per-town row files by
`raw/life_here/ctny_build/build.py`. It upserts on (building_id, moment, place_name, fact), so re-running replaces rows
and never adds duplicates; two runs give byte-identical output. Raw pages are cached in `raw/life_here/pages/` (same
scheme as round 1) and robots files in `raw/life_here/robots/`.

**Candidates:** rows of `data/ranked_units.csv` with `shown` true, state CT or NY and `listed_rent` <= 2000, grouped by
building, minus buildings already in `life_here_facts.csv`. That leaves 44 buildings (not about 50), worked in
`shown_rank` order. The list is in `raw/life_here/ctny_build/cands.csv`.

**Rows by moment (high / medium):** neighborhood 28 (24 / 4), dog_walk 71 (33 / 38), weekday 95 (16 / 79),
saturday 86 (49 / 37), sunday 78 (27 / 51). Overall 149 high, 209 medium. 85 rows rest on OpenStreetMap alone (all
medium). 44 are OSRM route rows (medium). 34 rows were carried over unchanged from round 1 (same source and retrieval
time; their notes say so).

## Method

- Places come from the project's OSM-derived files, `data/enriched/<sha1(addr_key)[:14]>.json` (places) and
  `data/enriched_color/*.json` (examples), joined to buildings the same way as `scripts/concierge_data.py`
  `enriched_for`. lat/lon is filled only from the OSM places index (`raw/big/osm/places_index.pkl`, EPSG:32618 to
  4326) for OSM nodes, or carried from round 1. No distances or walk times appear anywhere.
- WebSearch was used only to find pages. Every fact comes from the page itself, fetched with curl (honest UA, 3.2 s or
  more apart per host). robots.txt was checked first: the Claude-User group when present, otherwise `*`. Off-limits
  hosts and hosts in `raw/_host_kill_shared.json` were never contacted. Any 401, 403, 429 or bot wall was written to the
  kill file at once.
- **Sunday route rows** (one per building) read the road sequence from `drive.to_jamaica.main_roads` in
  `data/enriched`. Nothing was re-measured. Road refs are tidied for reading (for example "New England Thruway (I 95)"
  folds into I-95, and OSM's "Rossevelt Street" is spelled Roosevelt), and the raw sequence is kept in `notes`.
- Confidence is high only where the place's own site or an official page (town or city, CT DEEP / ctparks.com, NYS
  Parks, NYS DEC, NYC DOT, the Visit Norwalk and Visit New Haven tourism offices, NYC Tourism, a downtown association)
  shows the place or event as current. Opening stories in the press, volunteer sites and OSM-only rows are medium.
- Nothing about racial, ethnic or religious makeup was kept. NYC Tourism text on who lives in Jackson Heights, Jamaica
  and Sunset Park was left out, and only its street, park and venue facts were used. No crime content.

## Per neighborhood

| Area (buildings) | Dog walk | Weekday | Saturday | Sunday (besides the route) | Gaps |
|---|---|---|---|---|---|
| East Haven (6) | Farm River State Park (DEEP: leashed pets, 8am to sunset) for Short Beach Rd; Fort Hale Dog Park, New Haven (OSM) | Sugar Bakery (CTvisit hours), town farmers market on the Green (Sundays, mid-June to mid-October), Stop & Shop or Big Y (OSM) | **none** | Town Green concerts (Sundays 6 to 8pm, June 7 to Aug 23, 2026) | No bar or going-out strip confirmed. Beach concerts only on Patch. The OSM "supermarket" for 510 Main and 90 Gerrish is a TJ Maxx, so it was not used |
| Naugatuck (4) | Borough dog park at Andrew Mountain Park (3 acres, small-dog area, dawn to dusk); Whittemore Glen State Park for Spring St | Loaded Goat Coffee (OSM), Big Y (OSM) | Harvest Moon Festival on the Green (Fri and Sat in September; 2025 dates) | Route only | No bar confirmed. Waterbury not researched |
| Norwalk (6) | Oyster Shell Park dog run (News 12, Jan 2025); Taylor Farm Dog Park; Mathews Park; Cranbury Park for 289 Main | Art Space Cafe (Wed to Sun), Pausa Caffè (2022 article), Key Food, Patel Brothers or Stop & Shop (OSM) | Brass & Bone (bands Fri and Sat), SoNo Saturday Market, River Street Sunset Bazaar, **Holiday Extravaganza Sat Dec 5, 2026** | Calf Pasture Beach | Oyster Shell dog-run hours not found. norwalkartspace.org and caskrepublic.com were unreachable |
| Hamden (5) | Round-1 rows (Farmington Canal trail, Town Center Park) for Town Walk and Mix Ave; Hamden Dog Park (OSM) for the south | Best Video coffee bar (own site); Bread & Chocolate (round 1); Trader Joe's, Aldi or Whitneyville Food Center (OSM) | Best Video events, Eli's, Glenwood Drive-In, Friday concerts (round 1) | Sleeping Giant State Park (Tower Trail, leashed dogs) | Playwright pub refused us (403) |
| West Haven (3) | Veterans Memorial Dog Park (two fenced areas; 2021 city notice); shoreline rules (6-ft leash, no dogs on beaches) | Starbucks (OSM), Stop & Shop or Bom Preço (OSM), Tony Inzero Farmers Market (Thu on the Green, Sat by the boardwalk) | West Haven Summer Concert Series (Fridays) | Acoustic Summer Mornings (Sundays) | No bar confirmed |
| Milford (2) | Eisenhower Dog Park (city rules, sunrise to sunset); Silver Sands boardwalk | Cafe Atlantique and Scratch Baking (OSM), ShopRite or Aldi (OSM) | Small Business Saturday Nov 28; Lamplight Stroll Fri Dec 4, 2026; Fridays After Five | Walnut Beach concerts (alternate Sundays) | Scratch Baking's site refused us; it may have moved to Broad St (unconfirmed) |
| Shelton (1) | Bushinsky Arboretum, Shelton Dog Park (OSM) | ShopRite (OSM) | Veterans Memorial Park downtown (city page) | Route only | Building is far from downtown. Farmers market and Downtown Sounds only in third-party listings |
| Seymour (1) | Keith Mitchell Forest (229 acres, town page), French Memorial Park | Stop & Shop (OSM) | Strand Theater (town page; undated showtimes) | Route only | No cafe mapped |
| Stratford (1) | Shakespeare Park (OSM); beaches closed to dogs April to September (Audubon) | Checkers (OSM) | Holiday Market and tree lighting, Fri Nov 27, 2026; Olde Stratford Ale House (OSM) | Route only | Town site renders by script; the Holiday Market text was read from the page's embedded data |
| Stamford, East Main (1) | Courtland Park dog park (Audubon list) | ShopRite (OSM) | Round-1 downtown rows (Barcelona, Palace Theatre, farmers market) | Mill River Park, Barcelona brunch (round 1) | stamfordct.gov is already closed to us |
| Bridgeport, Anton St (1) | Beardsley Park (city page) and city park rules (round 1) | Price Rite, Galaxy Diner (OSM) | Round-1 downtown rows (Berlinetta, Bijou, Stress Factory) | Gold Note Jazz (round 1) | No North End cafe confirmed |
| Jackson Heights and Elmhurst (2) | 34th Avenue Open Street (NYC DOT); Travers Park and Sherry Dog Run (OSM) | Mapped cafes and groceries (OSM) | Terraza 7 (live music nightly, own site), Jackson Diner (own site) | Route only | NYC Parks and GrowNYC refuse us: no park rules or Greenmarket |
| Rego Park (1) | Forest Park Barking Lot (rules via the volunteer site) | C-Town, Bagelette (OSM) | Forest Hills Stadium, Eddie's Sweet Shop (NYC Tourism) | Forest Park (Forest Park Trust) | Barking Lot hours not found |
| Jamaica and Briarwood (2) | Forest Park Barking Lot | Ideal Food Basket or Aftab, Coffee Cloud (OSM) | JCAL Thursday Night Jazz (Dec 10, 2026) | King Manor Museum (Thu to Sat, noon to 4pm), Forest Park | No Saturday bar strip confirmed |
| Sunset Park (1) | Sunset Park (the park; NYC Tourism) | FillUp Coffee, Jenny's Food Market (OSM) | Industry City (own site) | Green-Wood Cemetery (dog rule unchecked) | Greenwood Playground Dog Run only in OSM |
| Gravesend South (1) | Shore Parkway Greenway (round-1 NYC DOT row) | Food Bazaar, Café Dacha (OSM) | Coney Island Brewing, Coney Island events (NYC Tourism) | Boardwalk and NY Aquarium | Luna Park's site gives no current season |
| Goshen (2) | Heritage Trail (Orange County Tourism, 2021) | Goshen Farmers' Market (Fridays May to October, village page), Trailside Treats, mapped cafes | Kelly Jeans (OSM) | Route only | The track's Dec 5 Cookie Walk and tree lighting appear only in search results (not used) |
| Middletown (1) | Heritage Trail extension; Maple Hill Dog Park (OSM) | Mapped bakeries and grocery (OSM) | Clemson Bros. Brewery (own site) | Route only | |
| Maybrook (1) | Stewart State Forest (DEC; closed to non-hunters in regular big-game season) | ShopRite (OSM) | **none** | Great Swamp boardwalk loop | Nothing mapped near the building |
| Ossining (1) | Old Croton Aqueduct trail (NYS Parks); Ossining Dog Park (OSM) | First Village Coffee (own site), Las Americas (OSM) | Down to Earth farmers market (day not read, it loads by script), Here Coffee + Beer (OSM) | Route only | |
| Islip / Bay Shore (1) | **none** | Bay Shore Bean, Stop & Shop (OSM) | Boulton Center (own site: Fri and Sat 8pm, Sun 2:30pm), Destination Unknown (OSM) | Route only | islipny.gov refused us; Gardiner County Park dog rules only in directories |

**Buildings with a moment missing:** saturday for the six East Haven buildings and Maybrook (no going-out place
confirmed), dog_walk for Islip. There are no neighborhood rows for Elmhurst, Jamaica Hills-Briarwood, Islip, Maybrook
or Stamford (round 1 already has Stamford's).

## Refusals this session (recorded in `raw/_host_kill_shared.json`, `by: life_here_ctny`)

- `www.newhavenct.gov`: 403 on robots.txt (Fort Hale and Edgewood dog park rules)
- `ctvisit.com`: **403** on an event page, after earlier reads in this and round 1 had succeeded. The state tourism
  board is now closed for the session; the cached Sugar Bakery and Whittemore Glen pages and round-1 rows stand.
- `www.playwrightirishpub.com`: 403 on robots.txt
- `www.scratchbaking.com`: 403
- `www.grownyc.org`: 403 on robots.txt (Greenmarkets)
- `islipny.gov`: 403

Not contacted because they were already closed or off limits: www.nycgovparks.org (a mirror host,
php1-84.nycgovparks.org, showed up in search results and was deliberately not used), data.cityofnewyork.us,
www.stamfordct.gov, www.queenslibrary.org, www.toasttab.com, Patch, Yelp and the others. Unreachable (proxy or DNS),
not refusals: norwalkartspace.org, www.caskrepublic.com, www.destinationunknownbeer.com, www.kewgardenscinemas.com,
www.sheltonctfarmersmarket.com, www.cityofshelton.org (`cityofshelton.org` works).

## Doubtful or to check before display

- Several schedules are from the 2025 or 2026 season, which has ended: the East Haven market (June 15 to Oct 12 matches
  2025), the Naugatuck Harvest Moon Festival (2025 dates), the Visit New Haven concert list (2026), and West Haven's
  market dates (no year on the page).
- Under saturday but not on a Saturday: Milford Lamplight Stroll (Fri Dec 4), Stratford Holiday Market (Fri Nov 27),
  JCAL jazz (Thu), West Haven and Milford Friday concerts. The East Haven farmers market is a Sunday market filed under
  weekday (errands).
- Medium rows that rest on dated third-party stories: Oyster Shell dog run (News 12, Jan 2025), Art Space Cafe (News 12,
  Feb 2025), Pausa Caffè (CT Bites, 2022), West Haven dog park (city notice, 2021), Heritage Trail rows (county tourism,
  2021), Seymour French Memorial Park (2022 event page), Strand Theater showtimes (undated town text).
- The Forest Park Barking Lot rules come from the volunteer group's site quoting NYC Parks. They are not read from NYC
  Parks itself.
- `b_90a4ca82be` (East Haven) has only a town-level address and a town-centroid point. Its rows are the town-center ones.
- Coordinator: `life_here_facts_ctny.csv` was already committed once mid-run (commit 5e2e9e7, 324 rows). This version
  replaces it.
