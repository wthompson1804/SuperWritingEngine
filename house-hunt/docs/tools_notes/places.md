# places: what is around an address (OpenStreetMap)

Module: `scripts/tools/places.py`. Functions: `near(lat, lon)`, `area_profile(lat, lon, radius_m=1200)` and `color(lat, lon)` (last section).
Self-test: `python3 -m scripts.tools.places` (add `--json` for the full dicts). Rebuild: `python3 -m scripts.tools.places --build`.

## Source and vintage

| | |
|---|---|
| Data | OpenStreetMap, Geofabrik extract. (c) OpenStreetMap contributors, ODbL 1.0: credit OSM wherever these values are shown. |
| File used | `north-america-latest.osm.pbf` (19.55 GB, md5 `b2e8fd858854f3f69334a092f1200c5e`, Geofabrik name `north-america-261114`) |
| URL | https://ftp5.gwdg.de/pub/misc/openstreetmap/download.geofabrik.de/north-america-latest.osm.pbf |
| OSM data timestamp | 2026-11-14T21:20:41Z (from the file header) |
| Downloaded | 2026-11-15T18:32Z |
| Recorded in | `data/reference/osm_extract_meta.csv`, `raw/big/osm/meta.json`, `raw/big/osm/_index.jsonl` |

**Not the three state files that were asked for.** `download.geofabrik.de` reset every connection from this
machine on 2026-11-15 (TLS handshake reset, repeated over 40 minutes; `overpass-api.de` does the same, which is
what the earlier "Overpass timeouts" were). The GWDG server is an official mirror of download.geofabrik.de
(robots.txt allows all) but carries only continent files, so the North America file was downloaded and cut to the
box. It is the same Geofabrik product and the same day's data. One consequence is helpful: Pennsylvania is covered
(8 grid points are in Philadelphia). The script still tries the NY, NJ, CT and PA state files first and falls back
to the mirror. The 19.5 GB file was deleted after the cut to free disk (the machine had 7 GB left); the build
re-downloads it only if `region.osm.pbf` is missing.

## Coverage

Box (west, south, east, north): **-75.2971, 39.86, -72.2786, 41.914** = bounding box of
`data/reference/search_grid.csv` plus 0.15 degrees (about 17 km north-south, 12.6 km east-west, more than the 10 km
anchor radius). A point outside the box returns only `coverage: not_found`.

## Build (about 20 minutes plus the download)

1. `osmium extract -b <box> -s smart` on the big file: `raw/big/osm/region.osm.pbf` (628 MB). About 10 minutes.
2. `osmium tags-filter` down to the tags below: `region_filtered.osm.pbf` (319 MB).
3. pyosmium `FileProcessor(...).with_areas()`: nodes as points; closed ways and multipolygon relations as polygons
   (centroid and area via shapely); coastline, motorway and river centre lines as lines. About 8.5 minutes.
4. Everything projected to UTM 18N (EPSG:32618) metres. Output: `places_index.pkl` (207 MB: scipy cKDTrees for
   points and densified lines, park polygons) and `buildings/*.npy` (594 MB, memory-mapped: 5.41 million building
   outlines in a 250 m grid index).

Needs `pip install osmium scipy shapely pyproj` and `apt-get install osmium-tool` (build only).

**Run time: index load 0.8 s once per process, then about 1.3 ms per `near()` and 2 ms per `area_profile()`**
(1,048 grid points in 1.4 s).

## Return format

Each value is a dict: `value`, `value_type` (found / estimate / not_found), `source_url`, `data_vintage` (OSM data
timestamp), `retrieved_at`, `method`, and `reason` when not_found. Named features also carry `name`, `osm_url`
(link to the exact OSM object, for citing or checking) and `osm_tags` (the definition used). Distances are
straight-line metres. Groups: `green_space`, `going_out`, `errands`, `working_from_home`, `setting`, `building`.

## Tag definitions and methods

| Value | OSM tags | Method |
|---|---|---|
| `nearest_park`, `nearest_named_park` | `leisure=park`, `leisure=nature_reserve`, `natural=beach`, areas of 0.5 ha or more | Metres to the outline (0 if inside), not to the centroid. `nearest_named_park` skips unnamed outlines. |
| `..._walk_min` | | estimate: metres x 1.3 / 80 m per minute |
| `park_area_ha_within_800m` | same tags, any size | Area of the outlines inside the circle, overlaps counted once; `share_of_circle` included |
| `nearest_dog_park` | `leisure=dog_park` | Point or centroid |
| restaurant counts | `amenity=restaurant` | Count within 800 m and 1,600 m |
| bar counts | `amenity=bar`, `amenity=pub` | |
| cafe counts | `amenity=cafe` | |
| brewery counts | `craft=brewery`, `microbrewery=yes`, `industrial=brewery` | |
| music counts | `amenity=nightclub`, `amenity=music_venue` | |
| `nearest_cafes`, `nearest_bakeries` (`shop=bakery`), `nearest_bars` | | Up to 5 nearest **named** places within 1,600 m, each with metres and OSM link |
| `nearest_supermarket` | `shop=supermarket` | Nearest in the index |
| `nearest_pharmacy` | `amenity=pharmacy` | |
| `nearest_veterinary` | `amenity=veterinary` | |
| anchors (`nearest_trader_joes`, `_whole_foods`, `_wegmans`, `_h_mart`, `_target`, `_costco`) | `shop` in supermarket, grocery, convenience, greengrocer, department_store, wholesale, general, variety_store, health_food, organic, with `name` or `brand` matching | Nearest within 10 km, else not_found. Excludes fuel stations, opticians, wine shops. |
| `cafes_within_800m_walk` | `amenity=cafe` | estimate: within 615 m straight-line (800 m / 1.3) |
| `coworking_within_1600m` | `amenity=coworking_space`, `office=coworking` | Count plus the places |
| `coastline_m` | `natural=coastline` | Nearest point on the line (vertices at most 25 m apart) |
| `river_or_lake_shore_m` | `natural=water` or `waterway=riverbank` areas: river or canal pieces of 2 ha or more, lakes, reservoirs and ponds of 5 ha or more | Nearest point on the outline. Unnamed river outlines take the name of the nearest `waterway=river` centre line within 1.5 km (`name_method` says so). |
| `nearest_open_water_m` | | The smaller of the two above |
| `beach_m` | `natural=beach` | Outline or node |
| `nearest_rail_station` | `railway=station` | Any kind; `kind` = train / subway / light_rail / other |
| `nearest_train_station` | `railway=station` not tagged subway or light rail | Commuter and intercity rail (LIRR, Metro-North, NJ Transit, Amtrak). PATH is tagged subway. |
| `motorway_m` | `highway=motorway` (no links, no trunk roads) | Nearest point on the line, with ref and name |
| `streetlamps_within_150m` | `highway=street_lamp` | Only when 150 or more lamps are mapped within 500 m; otherwise not_found with the counts |
| `building`, `building_type`, `building_levels`, `building_height_m`, `building_flats` | `building=*`, `building:levels`, `height`, `building:flats` | Outline containing the point = found. Otherwise the nearest outline within 40 m = estimate (geocoded points often sit at the kerb). Otherwise not_found. |

A place mapped twice (a node and its building outline with the same name within 60 m) is counted once.

`area_profile` returns counts within the radius (with `per_km2`) for restaurant, bar, cafe, brewery, music, bakery,
supermarket, pharmacy, vet, coworking, dog park, station and the six anchors; up to 5 nearest named cafes, bakeries,
bars, restaurants, breweries and music venues; park area within the radius; and the same setting distances.

## What is in the index

restaurants 20,037; cafes 4,744; bars and pubs 3,292; bakeries 1,454; breweries 299; music venues and nightclubs 192;
supermarkets 3,026; pharmacies 2,194; vets 591; coworking 86; dog parks 504 (247 named); stations 1,157 (516 train,
557 subway, 77 light rail); Trader Joe's 65; Whole Foods 77; Wegmans 16; H Mart 30; Target 159; Costco 45; parks
16,696; beaches 1,633; water bodies kept 2,601; buildings 5,409,995; street lamps 42,310.

## Gaps and caveats

- **OSM is volunteer-mapped: counts are floors, not censuses.** Coverage is strong in NYC, Jersey City and Hoboken
  and thinner in suburbs and exurbs. Compare like with like, and cite named places rather than leaning on small
  differences in counts. A place may also have closed since it was mapped (one Long Beach "cafe" is literally named
  "VACANT LB").
- **Street lamps: not meaningful.** Only 13 of 1,048 grid points have 150 or more lamps mapped within 500 m (lower
  Manhattan, downtown Brooklyn, Hoboken, a few towns such as Beacon). Elsewhere the value is not_found. Do not use
  it to compare places.
- **`building:levels` is tagged on only 98,440 of 5.41 million buildings (1.8%).** `height` is tagged on 1.91
  million (35%, mostly the NYC footprint import), so height is returned too. 65% of buildings have type `yes`
  (no type recorded). Expect levels to be not_found for most addresses. Courtyards are ignored (only outer rings).
  The match depends on the geocode: check `metres_from_point` and the `osm_url`.
- **Coworking is badly under-mapped** (86 in the whole box; none within 1,600 m of Grove Street, Jersey City, which
  is not believable). Treat zero as unknown.
- **Coastline** in OSM runs up the Hudson only to about the Tappan Zee; further north the Hudson is a river
  (Beacon: coastline 61.8 km, Hudson shore 78 m). Use `nearest_open_water_m` for "near water". The coastline also
  includes harbours and tidal bays (Jamaica Bay, Newark Bay), not only open ocean or sound.
- **Parks:** spec tags only. Land tagged only `boundary=protected_area`, `landuse=recreation_ground`,
  `leisure=garden`, `leisure=playground` or `landuse=forest` is not counted. Nature reserves can include water
  (Jamaica Bay refuge). The nearest park of 0.5 ha or more can be a playground or an unnamed beach: `kind`,
  `area_ha` and `nearest_named_park` are there to judge it.
- **Cafes** are `amenity=cafe` only: chains tagged `fast_food` (some Dunkin') are missed; bakery-cafes appear in
  whichever list their tag puts them.
- **Supermarket** includes small grocers tagged `shop=supermarket` in NYC; a Target tagged as a supermarket can be
  the "nearest supermarket" (Stamford).
- **Anchors** depend on name or brand tags; a store mapped without either is missed. not_found means none mapped
  within 10 km, not proof of absence.
- **Motorway distance is a noise proxy only**: no traffic volume, elevation or barriers; parkways tagged
  `highway=trunk` are not included.
- **Walk minutes are estimates** from straight-line distance, not routed (a river or rail line in the way is ignored).
- Straight-line distances use UTM 18N; scale error is under 0.1% across the box.
- `lib.cached_get` was not used for the 19.5 GB file because it holds the body in memory; the script streams it with
  the same User-Agent and logs it in `raw/big/osm/_index.jsonl`.

## Self-test results (2026-11-15)

| Point | Nearest park (0.5 ha+) | Cafes 800 m | Restaurants 800 m | Nearest supermarket | Open water | Train station | Motorway |
|---|---|---|---|---|---|---|---|
| Jamaica station | Howard Von Dohlen Playground, 335 m | 2 | 27 | Shop Fair, 165 m | Baisley Pond, 2,802 m | Jamaica, 74 m | I 678, 499 m |
| Forest Hills | MacDonald Park, 246 m | 12 | 58 | Key Food, 251 m | Willow Lake, 906 m | Forest Hills, 5 m | Grand Central Pkwy, 803 m |
| Long Beach NY | unnamed beach, 571 m | 5 | 10 | Stop & Shop, 251 m | coastline, 527 m | Long Beach, 24 m | Loop Pkwy, 6,584 m |
| Stamford CT | Gateway Park, 111 m | 2 | 13 | Target, 916 m | coastline, 510 m | Stamford, 10 m | I 95, 69 m |
| Jersey City Grove St | Van Vorst Park, 316 m | 31 | 92 | Salman Grocery, 320 m | Morris Canal Basin, 660 m | Hoboken Terminal, 2,160 m (PATH Grove Street 93 m) | I 78, 1,015 m |
| Beacon NY | Long Dock Park, 136 m | 2 | 5 | Key Food, 1,097 m | Hudson River, 78 m | Beacon, 17 m | I 84, 1,349 m |

## color(lat, lon): the kind of life around a building (added 2026-11-15)

Second index, built from the same regional cut (`region.osm.pbf`, same vintage and source as above; nothing was
re-downloaded). Files: `raw/big/osm/region_color.osm.pbf` (152 MB) and `color_index.pkl` (365 MB). Build:
`python3 -m scripts.tools.places --build-color` (about 3 minutes). **Load 1.4 s once, then about 3 ms per call**
(1,048 grid points in 3.1 s). Same value format as `near()`.

For each category: `<cat>_count_800m`, `<cat>_count_1600m` and `<cat>_examples` (up to 3 nearest **named** places
within 1,600 m, with metres and OSM link). `shop_any` has counts only.

| Group | Key prefix | OSM tags | In index |
|---|---|---|---|
| culture | `bookshop` | `shop=books` | 417 |
| | `library` | `amenity=library` | 1,369 |
| | `cinema_theatre` | `amenity=cinema`, `theatre`, `arts_centre` | 1,387 |
| | `gallery_museum` | `tourism=gallery`, `museum` | 1,389 |
| fitness_and_play | `gym` | `leisure=fitness_centre`, `amenity=gym`, or `sport` including yoga or pilates | 2,023 |
| | `playground` | `leisure=playground` | 10,412 |
| | `pitch` | `leisure=pitch`, `sports_centre` | 50,807 |
| | `tennis` | the same with `sport` including tennis | 17,027 |
| | `community_garden` | `leisure=garden` + `garden:type=community`, or `landuse=allotments` | 708 |
| food | `market` | `amenity=marketplace` | 279 |
| | `fast_food` | `amenity=fast_food` | 11,247 |
| | `diner_ice_cream` | `amenity=ice_cream`, or `cuisine` including diner | 1,419 |
| pets | `pet` | `shop=pet`, `pet_grooming` | 776 |
| | `vet` | `amenity=veterinary` (from the main index) | 591 |
| main_street | `hair_beauty` | `shop=hairdresser`, `beauty` | 8,410 |
| | `shop_any` | `shop=*` except no / vacant | 65,426 |
| | `convenience` | `shop=convenience` | 6,322 |
| | `laundry` | `shop=laundry` | 1,704 |
| car_oriented | `fuel` | `amenity=fuel` | 5,104 |
| | `drive_through` | `drive_through=yes` on any place | 3,072 |
| | `big_box` | `shop=department_store`, `wholesale`, `doityourself`; or `shop=mall` or `building=retail` with an outline over 5,000 m2 | 2,317 |
| | `surface_parking_ha_within_800m` | `amenity=parking` areas, excluding `parking=underground`, `multi-storey`, `rooftop`, `street_side`, `lane` | 82,747 outlines, 21,666 ha |
| street_pattern | `intersections_within_800m` (with `per_km2`) | nodes where 3 or more street segments meet; streets = `highway` residential, living_street, unclassified, tertiary, secondary, primary, trunk, pedestrian | 518,178 |
| | `footway_km_within_800m` | `highway=footway`, `pedestrian`, `path` | 75,249 km |
| | `cycleway_km_within_800m` | `highway=cycleway` | 2,868 km |
| | `bike_lane_street_km_within_800m` | streets with `cycleway`, `cycleway:left`, `:right` or `:both` = lane or track | 2,608 km |
| trees | `tree_row_km_within_800m` | `natural=tree_row` | 501 km |
| | `woods_ha_within_800m` | `natural=wood`, `landuse=forest` areas | 58,609 outlines |

Methods: counts are straight-line; outlines count once at their centroid; same-name duplicates within 60 m are
merged. Areas are the mapped outlines clipped to an 800 m circle with overlaps counted once (`share_of_circle`
included). Lengths are estimates: ways are cut into pieces of at most 25 m and pieces whose midpoint is inside the
circle are summed.

### color() caveats

- **Footway length mostly measures mapping style, not walkability.** Where sidewalks and crossings are drawn as
  separate ways (NYC, Jersey City, Stamford) it is 30 to 70 km within 800 m; where they are not, it is near zero on
  equally walkable streets. **Use `intersections_within_800m` as the street-pattern signal**; it depends only on
  the road network, which is complete everywhere. Divided roads add a few extra nodes.
- **Pitches count each court or field separately.** Forest Hills shows 45 tennis courts within 800 m because of the
  West Side Tennis Club; this is not 45 public courts. Access (private club, school) is not checked. Most pitches
  and playgrounds are unnamed, so examples are sparse.
- **Gyms, bookshops, pet shops, laundromats, hairdressers and convenience stores are under-mapped outside the urban
  core.** Zero means "none mapped". `shop_any` is the most robust retail signal but is still a floor.
- **Markets**: `amenity=marketplace` covers farmers' markets, greenmarkets and other markets alike; only 279 mapped.
  Seasonal markets are often missing.
- **Community gardens**: 708 mapped, mostly NYC (GreenThumb gardens). Many are tagged only `leisure=garden` without
  the type and are missed.
- **Drive-through** depends on a tag mappers often omit; treat as a floor. **Fuel stations** are well mapped.
- **Big box** by outline picks up enclosed malls and large retail buildings in cities too (9 within 1,600 m of
  Grove Street, Jersey City: Newport Centre and neighbours), so read it with surface parking, not alone.
- **Surface parking**: lots are well mapped in cities and commercial strips; small private lots and driveways are
  not. Untagged structures (a garage with no `parking=multi-storey`) count as surface.
- **Woods**: outlines only; street trees are not counted, and `natural=tree_row` is rarely mapped (501 km in the
  whole box), so the tree-row value is near zero almost everywhere and should not be compared. Wooded parks tagged
  only `leisure=park` are not woods here (see `park_area_ha_within_800m` in `near()`).
- **Bike lanes**: on-street lanes are reported separately from off-street cycleways; older `cycleway=shared_lane`
  (sharrows) is excluded.

### color() self-test (800 m unless stated)

| Point | Shops | Gyms | Fast food | Big box (1,600 m) | Surface parking ha | Intersections | Woods ha |
|---|---|---|---|---|---|---|---|
| Jamaica station | 155 | 0 | 37 | 6 | 2.34 | 201 | 0.0 |
| Forest Hills | 148 | 6 | 30 | 1 | 0.86 | 213 | 0.28 |
| Long Beach NY | 23 | 3 | 5 | 0 | 7.99 | 167 | 0.0 |
| Stamford CT | 11 | 0 | 1 | 3 | 11.49 | 156 | 0.0 |
| Jersey City Grove St | 84 | 4 | 12 | 9 | 14.32 | 186 | 2.21 |
| Beacon NY | 20 | 0 | 0 | 0 | 8.9 | 61 | 14.59 |
