# Life here: local detail per building (2026-11-17)

Output: `data/reference/life_here_facts.csv` (218 rows). Header is fixed:
`building_id, neighborhood_id, moment, place_name, place_kind, fact, schedule, lat, lon, source_name, source_url,
retrieved_at, confidence, notes`. The CSV is written from `rows.json` in the agent scratchpad by an upsert keyed on
(building_id, moment, place_name, fact), so re-running replaces rows and never duplicates them. Raw pages are cached in
`raw/life_here/pages/` (`<sha1(url)[:16]>.html` + `.meta.json` with url, status, retrieved_at). The robots files checked
are in `raw/life_here/robots/`.

Rows per moment: neighborhood 25, dog_walk 39, weekday 58, saturday 54, sunday 42. Confidence: high 117, medium 101.

## Method

- Nearby places came from the project's OpenStreetMap index (`raw/big/osm/places_index.pkl`, read only, data
  2026-11-14): the nearest named cafes, bars, restaurants, supermarkets, dog parks and parks within about 1.6 to 2 km of
  each building. These names were then looked up on the web. lat/lon is filled only from OSM (`notes` gives the OSM
  object) or from an official page. Distances and walking minutes are left out everywhere.
- Each robots.txt was checked before fetching. The Claude-User group was used when there was one, otherwise `*`. Fetches
  went through curl with an honest UA, 3 s or more apart, and 10 s for colorfulbridgeport.com (Crawl-delay 10). WebFetch
  could not resolve hosts in this sandbox, so pages were read from the local cache.
- **Sunday route rows** (22, one per building) take the road sequence from our own OSRM results in `data/enriched/*.json`
  (`drive.to_jamaica.main_roads`). Nothing was re-measured. Confidence is medium because the roads come from a free-flow
  route.
- Rows whose source is OpenStreetMap alone (mostly the nearest supermarket, plus mapped cafe names in Flushing and
  Sheepshead Bay) are marked medium. Their notes say the place was not checked on its own page.

## Per building

| Building | Dog walk | Weekday | Saturday | Sunday (besides the route) | Gaps |
|---|---|---|---|---|---|
| Stamford: Summer Street, The Stanley, 111 Prospect | Mill River Park (free, open all year, dogs on leash; carousel, rink) | Lorca, Winfield Street Coffee (hours), Tiernan's trivia on Wednesdays, Target (OSM) | Farmers market at Veterans Memorial Park (Saturdays, mid-June to mid-October), Barcelona Wine Bar, Palace Theatre | Barcelona weekend brunch | Courtland Dog Park: only directories (stamfordct.gov refuses us). Tigin and Avon Theatre refuse us |
| Bridgeport: City Trust 955 and 991 Main, 333 State, Soundview 855 Main | Seaside Park (325 acres, Olmsted and Vaux); city rules: 6-ft leash, no dogs on the beach, 8am to 8pm | NY Caffeine (in the Soundview building, opened April 2025), URSA roaster cafe, Downtown Market on Thursdays, Save-A-Lot (OSM) | Stress Factory comedy, Bijou Theatre, Berlinetta Brewing | Gold Note Jazz at Berlinetta on Sunday afternoons, Recollective vintage market | The downtown market's McLevy Green location and its season come only from search results (medium). No fenced dog run downtown |
| Danbury: Brookview Commons II and East | Tarrywile Park (722 acres, 21 miles of trails, leash required by ordinance, sunrise to sunset) | Mothership on Main (communal work tables, 2019 article), ChowDown food trucks on Thursdays, Price Rite (OSM) | CityCenter farmers market (Saturdays from June 20 in 2026), Summer in the City concerts, the Main Street festival in June | Route only | Mothership's own site is unreachable and Toast refused us, so current operation is unconfirmed. No bar confirmed |
| Hamden: Whitney Towers | Farmington Canal trail (dogs on leash, SCRCOG brochure), Town Center Park | Bread & Chocolate (2022 TV story), Trader Joe's (OSM) | Eli's on Whitney, Glenwood Drive-In, Friday concerts in July | Route only | No official rules page for Town Center Park. No farmers market found |
| Yonkers: Regency on Hudson | Van der Donck Park (the uncovered Saw Mill River), Halloween pet parade | Mon Amour cafe (2024 report), ShopRite (OSM) | Yonkers Brewing Co., Waterfront Live concerts on Fridays in summer, Riverfest | Tree lighting in Getty Square (it is a Friday; placed under sunday, move if needed) | City site refuses us (no rules for the city parks or the esplanade) |
| Yonkers: 525 Riverdale Ave | Tibbetts Brook Park (161 acres; county leash rule), Fay Park (OSM) | Key Food (OSM) | Downtown Yonkers events, shared with Regency | Tree lighting | No cafe found. The nearest strip is in Riverdale (Bronx), not researched |
| Belleville: Ethos Kelsey | Riverside County Park across the river (85 acres, over 7 miles of paths), Branch Brook Dog Park | ShopRite next door (OSM) | Cherry Blossom Festival in Branch Brook (April) | Route only | No named going-out strip found with a usable source. The Bergen County dog-run page was unreachable |
| Bloomfield: 64 Park Avenue | Watsessing Park and its fenced dog area | Dinner Under the Stars on Fridays in summer, Super Foodtown (OSM) | Six Points Pub (NJ Monthly, 2024) | Brookdale Park (has a dog park) | No cafe confirmed (Pink Moon Coffee: aggregators only) |
| East Orange: Harclay House | Monte Irvin Orange Park next door, Watsessing Dog Park | ShopRite (OSM) | Free summer concerts in Orange Park | Edison National Historical Park | No cafe, bar or strip found |
| Orange: LIA by Vermella | Monte Irvin Orange Park, Watsessing Dog Park | Orange station next door, ShopRite (OSM) | Free summer concerts in Orange Park | Edison National Historical Park | Four City Brewing (mapped nearby in OSM) **closed in June 2025**: kept only as a warning row |
| Newark: Symphony | Lincoln Park across the street; Military Park (leashed dogs, not on the lawns; older page) | Newark Symphony Hall next door, Whole Foods (OSM) | Ironbound and Ferry Street restaurants, Lincoln Park Music Festival | Route only | No current cafe confirmed (the Halsey St sources are from 2016). The Common Greens market's 2026 schedule was not found |
| Flushing: 4110 Bowne, 13324 Sanford; Murray Hill: 3625 Parsons | Flushing Meadows Corona Park (has dog runs, per NYC Tourism) | Mapped tea and bakery cafes (OSM only), Tian Jin dumplings, H Mart or Great Wall (OSM) | Queens Night Market (Saturdays, mid-April to October), Tangram food hall, Flushing Town Hall | Queens Museum | NYC Parks (nycgovparks.org) was already refused, so there are no off-leash hours or park rules. No laptop cafe confirmed |
| Sheepshead Bay: 2781 Ocean Ave | Manhattan Beach Dog Run (NYC Open Data: Active) | NetCost Market and Stop & Shop, Pep Bakehouse and Mouette (all OSM) | Randazzo's Clam Bar | Randazzo's on the way back from the beach | Marine Park and the Emmons Ave piers have no new official source (the piers are already in the round-2 descriptions) |
| Bath Beach: 1483 Shore Pkwy | Shore Parkway Greenway (NYC DOT), Dyker Beach Park Dog Run (Active) | Target, Kohl's, BJ's, Key Food (OSM) | 86th Street strip, Liu's Shanghai (The Infatuation) | Route only | Brooklyn Eagle refuses us; Brooklyn Paper disallows Claude-User |

Neighborhood facts: 2 each, except East Orange, City of Orange (only the Four City warning row) and Bath Beach, which have
1 each. Where the existing `neighborhood_descriptions*.csv` already said something (such as Mill River as a "mini
Central Park", Bedford Street nightlife, the Ironbound, the World's Fairs), it was not repeated.

## Refusals this session (recorded in `raw/_host_kill_shared.json`, `by: life_here`)

- `www.queenslibrary.org`: 403 on robots.txt
- `www.stamfordct.gov`: 403 on robots.txt (an earlier session had noted it in SOURCES but not in the shared file)
- `tiginirishpub.com`: 403 bot wall
- `avontheatre.org`: 403 on robots.txt
- `www.toasttab.com`: 403 bot wall
- **`data.cityofnewyork.us`: 403** on the second Socrata request (`ipbu-mtcs`). The first (`hxx3-bwgv`, Dog Runs)
  returned 200. This host is used by other NYC records scripts, so the coordinator should know that it is now closed for
  the session.
- `brooklyneagle.com`: 403 on robots.txt

Also not usable, but not refusals: `www.brooklynpaper.com` (robots disallows Claude-User),
`scrcog.org` (bars ClaudeBot and Claude-Web, but its `*` group allowed the brochure). These hosts were unreachable:
mothershipbakeryandcafe.com, www.downtownnewark.com, www.co.bergen.nj.us, www.fmcpalliance.org. The www.fourcitybrewing.com
domain now serves an unrelated gambling page.

## Doubtful or to check before display

- The Four City Brewing row is a warning only. OpenStreetMap still maps a closed brewery near both Oranges buildings,
  so the data agent should not name it as a place to go.
- These rows rest on old or third-party write-ups, and the place's own page was not reached: Mothership (2019), Bread &
  Chocolate (2022), Mon Amour (2024), URSA (one directory says it is closed), Eli's on Whitney (CTvisit), Six Points
  (2024), Tian Jin (an itinerary from about 2021), and Military Park dog rules (an older page). All are marked medium.
- Queens Night Market FAQ: its season wording mixes years (2025 preview dates alongside a 2026 season). The schedule
  is given only in general terms.
- CityCenter Danbury's events page still says the market runs on Fridays; the 2026 calendar entry says Saturday. The row
  uses Saturday.
- The Yonkers tree lighting is on a Friday, but it was filed under sunday.
- Lincoln Park Music Festival dates come from the 2022 Foundation article; the 2026 main dates were not confirmed.
