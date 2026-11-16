# Splitting Jersey City (and Newark) into neighborhoods: prepared, not wired in

Prepared 2026-11-15/16 while the pipeline repair was running. **No existing script or data file was changed, the
pipeline was not run, nothing was committed.** Everything is in new files:

| File | What |
|---|---|
| `scripts/build_subcity_neighborhoods.py` | Builds all of the below. Idempotent; re-run after the repair to refresh the counts. |
| `data/reference/subcity_neighborhoods.geojson` | 13 polygons: 8 Jersey City, 5 Newark. `city, state, hood_area, hood_name, hood_label, hood_id, parent_hood_id, source, source_url, retrieved_at, method, tracts, pop_acs_2019_2023` |
| `data/reference/subcity_tracts.csv` | Jersey City: 77 census tracts → neighborhood, with the rule used, ward share, ACS population |
| `data/reference/subcity_assignment.csv` | 54 master buildings (38 Jersey City, 16 Newark) → neighborhood, distance to the nearest other neighborhood, `near_boundary` (≤ 150 m), `review_note` |
| `data/reference/subcity_counts.csv` | Buildings and currently ranked / shown units per new neighborhood |
| `data/reference/subcity_crime_jersey_city.csv`, `subcity_crime_note.md` | Sub-city crime: counts, labelled estimates, and why they should not drive the cut |
| `raw/subcity_split/` | Cached downloads (3 TIGER zips) and the OSM place nodes used |

## 1. Which cities, and why

| City | Master buildings | Spread | Decision |
|---|---|---|---|
| Jersey City | 38 | 4 km × 5 km, six ZIP codes, all six wards except the Heights well represented | **Split into 8** |
| Newark | 16 | 8 km × 6 km, eight ZIP codes, all five wards | **Prepared (5 wards), but adoption not recommended**: 7 buildings and 44 of the 45 ranked units are in the Central Ward. The split would rename "Newark" to "Newark – Central Ward" and add a one-unit South Ward. Adopt only if the repair brings more Newark buildings in. |
| Hoboken | 1 | n/a | Stays whole (as instructed) |
| Stamford | 44 | 39 of 44 within about 1.5 km of downtown (ZIP 06901 and the adjoining part of 06902) | Not split. One continuous downtown / South End core, no official sub-city polygons, and OSM offers only points. A Downtown / South End / Glenbrook split is possible later by the Jersey City method. |
| Yonkers | 18 | 13 in a 1.5 km strip of the downtown waterfront (10701); the other five are singletons or a pair (Ridge Hill) | Not split: one cluster plus outliers |
| New Rochelle | 17 | 1.9 km × 0.7 km | Not split: one downtown |
| White Plains | 17 | 0.9 km × 1.4 km | Not split: one downtown |
| New Haven | 25 | 3 km × 7 km | Not in the brief; not examined. Note that its agency property rate (31.2) is above the 25.0 line, so the city is cut today whatever its neighborhoods. |

## 2. Sources and method

**Hosts touched:** `www2.census.gov` only (three files; robots.txt has no rule for us, as already recorded in
`docs/SOURCES.md`; all three returned 200). OpenStreetMap came from the regional extract already on disk
(`raw/big/osm/region.osm.pbf`, OSM data of 2026-11-14); Overpass and Nominatim were not called.
`data.jerseycitynj.gov` was not touched. No refusals.

To add to `docs/SOURCES.md` when that file is free (I did not edit it):

| Source | Use | URL | Result |
|---|---|---|---|
| Census TIGER 2024 tracts, NJ | 2020 tract polygons | `https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_34_tract.zip` | 200, 7.1 MB |
| Census 2020 voting districts (VTD), Hudson and Essex | ward lines: VTD names read "Jersey City city ward A voting district 1", "Newark city ward Central voting district 1" | `https://www2.census.gov/geo/tiger/TIGER2020PL/LAYER/VTD/2020/tl_2020_34017_vtd20.zip`, `..._34013_vtd20.zip` | 200 |

**Why not OSM alone.** OSM has no neighborhood polygons for Jersey City and only a thin, uneven set of place nodes:
Downtown Jersey City, Hamilton Park, Newport, Colgate Center, The Heights, Journal Square, Hilltop, Indian Square,
Bergen Square, Croxton, Marion, McGinley Square, West Bergen, Communipaw, Greenville. There is no node for
Bergen-Lafayette, West Side or Paulus Hook. "Nearest named place" put most of the West Side and Bergen-Lafayette under
McGinley Square or West Bergen. So the backbone is the ward map, which is official and whose six wards carry the six
area names residents use.

**Jersey City method** (`source` = "derived from tracts + ward lines + OSM place points"):

1. Unit = 2020 census tract (77 tracts with more than half their area in the city), so that ACS populations and the
   tract-based lifestyle features line up with the neighborhood.
2. Each tract takes the 2020 ward holding most of its area. 67 of 77 tracts lie 70% or more in one ward.
3. Ward → name: A Greenville, B West Side, C Journal Square, D The Heights, E Downtown, F Bergen-Lafayette. I did not
   fetch a city page for these names (the city's sites were not tested). The check made instead: every OSM node that
   names one of these areas falls in the matching ward (Greenville in A, West Bergen in B, Journal Square in C, The
   Heights in D, Downtown Jersey City in E, Communipaw in F). The script prints "anchor/ward check: all agree".
4. Three refinements, because wards are equal-population political districts, not neighborhoods:
   - **Newport** = tracts 77.01, 77.02, 77.03 (the former tract 77, which holds the OSM node Newport), taken out of Downtown.
   - **McGinley Square** = tracts whose internal point is within 600 m of the OSM node McGinley Square and that hold no
     other neighborhood's node: 28, 29, 30, 31.01, 41.02, 41.04. Wards B, C and F meet at this corner and two of these
     tracts are split almost evenly between wards.
   - **Tract 13 → The Heights.** On paper ward C (Journal Square), but no Journal Square node is within 1.2 km of it and
     its nearest named place is The Heights; it holds New York Avenue (ZIP 07307, the Heights ZIP).
5. Dissolve, clip to the city boundary (TIGER 2024 place). The polygons cover the whole city (0.0 km² uncovered).

**Newark method** (`source` = "official: 2020 ward lines"): the 2020 voting districts dissolved by ward. Names are the
ward names only (Central, North, East, South, West); I added no neighborhood names such as Ironbound because none was
sourced.

**Quality, plainly.** The polygons are tract-edge approximations of how residents talk, good to a few blocks, not a
published neighborhood map. Ward lines are those in force at the 2020 Census; both cities redrew wards in 2022, which
does not matter for naming areas but means these are not today's council districts. Seven tracts straddle wards
(`weak_ward_majority` in `subcity_tracts.csv`). The 600 m radius and the tract 13 override are my judgment calls.

## 3. What lands where (today's files; counts will move after the repair)

Jersey City today: 38 master buildings; 94 ranked units in 17 buildings; 10 shown (the per-neighborhood cap).

| New neighborhood | `hood_id` | Master buildings | within 150 m of a boundary | Ranked units (buildings) | Shown now | Most that could show after the split |
|---|---|---|---|---|---|---|
| Bergen-Lafayette | `nj:jersey-city-bergen-lafayette` | 10 | 4 | 17 (7) | 2 | 10 |
| Journal Square | `nj:jersey-city-journal-square` | 9 | 4 | 24 (3) | 5 | 10 |
| Downtown | `nj:jersey-city-downtown` | 5 | 2 | 2 (2) | 1 | 2 |
| West Side | `nj:jersey-city-west-side` | 4 | 1 | 33 (4) | 2 | 10 |
| Greenville | `nj:jersey-city-greenville` | 4 | 1 | 0 | 0 | 0 |
| McGinley Square | `nj:jersey-city-mcginley-square` | 3 | 3 | 18 (1: 20 Beacon Way) | 0 (2 avoid cards) | 10, less the per-building cap |
| The Heights | `nj:jersey-city-the-heights` | 2 | 1 | 0 | 0 | 0 |
| Newport | `nj:jersey-city-newport` | 1 | 0 | 0 | 0 | 0 |
| **Jersey City total** | | **38** | **16** | **94 (17)** | **10** | **up to 42** |
| Newark – Central Ward | `nj:newark-central-ward` | 7 | 4 | 44 (7) | 9 | 10 |
| Newark – North Ward | `nj:newark-north-ward` | 4 | 0 | 0 | 0 | 0 |
| Newark – East Ward | `nj:newark-east-ward` | 2 | 0 | 0 | 0 | 0 |
| Newark – South Ward | `nj:newark-south-ward` | 2 | 0 | 1 (1) | 1 | 1 |
| Newark – West Ward | `nj:newark-west-ward` | 1 | 0 | 0 | 0 | 0 |

"Most that could show" is min(ranked units, 10); the real number will be lower where the per-building cap
(`MAX_PER_BUILDING` in `scripts/rank.py`) or open items bite.

Buildings to look at by hand before adopting (`review_note` / `near_boundary` in `subcity_assignment.csv`):

- **110 Hoboken Avenue** (One Ten at the Enclave): filed under The Heights with tract 13, but it stands at the foot of
  the cliff, 67 m from Downtown, ZIP 07310. A resident would say Downtown or "the Hoboken border".
- **15 Carbon Place** and **176 West Side Avenue**: filed under Greenville (ward A, tract 54), 21 m and about 200 m
  from the West Side line, next to the West Side Avenue light-rail stop. A resident would likely say West Side.
- **232 Bidwell Avenue**: Bergen-Lafayette by a 48% ward plurality, 94 m from Greenville.
- **104 Clifton Place**: Journal Square, 1 m from McGinley Square (it is beside The Beacon, which is McGinley Square).
- **20 Beacon Way, 55 Jordan Avenue, 821 Bergen Avenue**: McGinley Square, each within about 100 m of Journal Square.
- **1075 West Side Avenue, 161 Van Wagenen Avenue**: Journal Square (Marion section), 33 m and 41 m from West Side.
- **675 Monmouth Street**: Downtown, 56 m from The Heights (tract 13 again).
- Newark: the four downtown buildings east of Broad Street are 25–145 m from the East Ward line.

A small override file (`building_id → hood_id`, with a reason) would settle these; I did not create one because each
is a judgment for Will.

## 4. Exactly what to change

### 4.1 `scripts/build_neighborhoods.py` (the only required change)

- After `nta_polys()` (lines 20–22) add a loader:

```python
def subcity_polys():
    f = DATA / "reference" / "subcity_neighborhoods.geojson"
    if not f.exists():
        return []
    ADOPT = {"Jersey City"}          # add "Newark" only if wanted
    return [(p["city"], p["state"], p["hood_label"], shape(ft["geometry"]))
            for ft in json.loads(f.read_text())["features"] for p in [ft["properties"]] if p["city"] in ADOPT]
```

- In `main()`, line 28: `ntas = nta_polys()` → add `subs = subcity_polys()`.
- In the `else:` branch, lines 38–42, after the suffix-stripping loop (line 41) and before `area = county` (line 42):

```python
            p = Point(lon, lat)
            sub = [lab for c, st, lab, poly in subs if c == name and st == g.state.iloc[0] and poly.contains(p)]
            if not sub:   # point just outside every polygon of a split city: take the nearest
                cand = [(poly.distance(p), lab) for c, st, lab, poly in subs if c == name and st == g.state.iloc[0]]
                sub = [min(cand)[1]] if cand else []
            name = sub[0] if sub else name
```

- Line 45 needs **no change**: `hood_label` is "Jersey City – Journal Square", and the existing slug rule turns
  `nj` + that label into `nj:jersey-city-journal-square`, which is the `hood_id` in the GeoJSON (the build script
  derives its ids with the same expression).
- `hood_area` stays the county ("Hudson County"). Do not put the city there: `scripts/crime_benchmarks.py` line 68
  strips " County" from it to find the county benchmark.
- Point-in-polygon at run time (above) is better than joining `subcity_assignment.csv`: the CSV is keyed on today's
  `building_id` / coordinates, which the repair may change. Keep the CSV as the audit list.
- `MIN_UNITS = 3` (line 17, used at 75) then applies per new neighborhood. With today's units Downtown (2 ranked)
  would fall below it; Greenville, The Heights and Newport have none.

### 4.2 Scripts that need no change but will behave differently

| Script, lines | Effect |
|---|---|
| `scripts/lifestyle_features.py` 40–53, 84–86 | Features are medians of each building's own tract, grouped by `hood_id`: the new neighborhoods get their own values automatically. |
| `scripts/lifestyle_color.py` 28–36, 69–71 | Same. |
| `scripts/crime_benchmarks.py` 65–71 | Each new neighborhood inherits the Jersey City Police agency rate (4.87 / 18.32) from its units. `geography` still reads "serves Jersey City city", which is true. |
| `scripts/lifestyle_groups.py` 61, 86–89 | Safety cut unchanged (agency rate). Each new neighborhood is assigned to the nearest saved centre. **Do not pass `--refit`**: `data/reference/lifestyle_fit_reference.csv` holds one `nj:jersey-city` row, and refitting would move every group. Jersey City is "The Little-City Year" today; Downtown and Newport (if they get units) will probably land in "The Fresh-Start Year" and the Heights or Journal Square possibly in "Walk-Everywhere" or "Old-Neighborhood". That is the point of the split, but it moves units between years. |
| `scripts/rank.py` 150, 408–420, 436–442, 453 | Median all-in, dominance, `hood_rank`, the top-10 `shown` cut and the avoid cards are all per `hood_id`. See risks. |
| `scripts/build_master.py` 579 | Carries `hood`, `hood_id`, `hood_area` from units; no change. |

### 4.3 Things keyed on the old id `nj:jersey-city` that will silently go missing

These need a fallback from child to parent (`parent_hood_id` is in the GeoJSON), or re-keying:

| Where | What is keyed on `nj:jersey-city` | Fix |
|---|---|---|
| `scripts/build_page_data.py` 138–155 (voices, survey) | `data/voices/neighborhood_quotes.csv`: 11 Niche quotes ("Jersey City, NJ"); `neighborhood_survey.csv`: 2 Niche + 32 Trulia rows whose `source_area` is "Journal Square, Jersey City" or "McGinley Square, Jersey City" | Route the Trulia rows by `source_area` to the two matching new ids; show the citywide Niche quotes on every Jersey City neighborhood labelled "about Jersey City as a whole", or drop them. |
| `scripts/build_page_data.py` 128 (local rules) | `data/reference/local_rules.csv`: 10 Jersey City rows with `applies_to_hood_ids = nj:jersey-city` | City law applies to all eight: expand the id list (in `scripts/local_rules_build.py` 53/81 and `local_rules_round2.py` 130/167) or fall back to the parent id. |
| `scripts/build_scene_text.py` 77–92, 217–241; `data/reference/scene_text_neighborhoods.csv` | One scene text for Jersey City | Write new scene text per neighborhood (already an open item in `PROGRESS.md`). |
| `scripts/voices_fetch.py` 17, 92; `voices_build.py` 14; `voices_targets.py` 53, 90 | Slug maps keyed on `hood_id` | Re-key the two Trulia slugs to the new ids. Trulia and Niche both refused us on Nov 15, so no new fetch until they are cleared. |
| `data/reference/shown_neighborhoods.csv`, `scripts/avoid.py` 217–267 | Shown list; the Jersey City car-crime rule reads per-building rows, not `hood_id` | Regenerated by the run; `avoid.py` unaffected. |
| `scripts/resolve_pending_thin_years.py` 111–113 | Guesses `hood_id` from ZIP by majority | Will pick one neighborhood per Jersey City ZIP (07304 and 07306 each span three). Acceptable for a pending-list estimate; note it. |

For Newark the same table applies with `nj:newark` (13 Niche quotes, 32 Trulia survey rows for "Central Business
District" and "University Heights", 10 local-rule rows).

## 5. Risks

1. **More Jersey City on the page.** One neighborhood showing 10 places becomes up to five showing up to 42 (see the
   table), all of them in one city and, today, one year. Jersey City would go from about 3% of shown places to as much as
   11% without any new evidence about those places.
2. **Single-building neighborhoods.** McGinley Square's 18 ranked units are all at 20 Beacon Way, which currently has
   two avoid cards and no shown unit. As its own neighborhood it gets its own top-10 slot.
3. **Boundary sensitivity.** 16 of 38 Jersey City buildings are within 150 m of a line, and the lines are tract edges.
   A handful (section 3) are filed under a name a resident would dispute. Settle them before the names reach the page.
4. **Safety looks finer-grained than it is.** All eight neighborhoods carry the same citywide police rate. The page
   must not imply the rate is for Bergen-Lafayette or Downtown specifically. The only sub-city evidence is the
   10.5-month estimate in `subcity_crime_jersey_city.csv`: Bergen-Lafayette about 1.9 times the city's violent rate
   (scaled 9.25 against the 9.8 line), West Side property scaled 24.0 against 25.0, Newport property over the line
   because of mall shoplifting against a small resident count. If that estimate were used as the cut, results would
   hinge on a few percent and on one partial year. See `data/reference/subcity_crime_note.md`.
5. **Scores shift.** `rank.py` line 150 compares each unit's all-in cost with its neighborhood median; smaller
   neighborhoods mean different medians, and dominance (lines 408–412) is judged within the neighborhood. Units that
   were dominated citywide can surface.
6. **Year membership shifts** (section 4.2), which changes the per-year counts Will approved at checkpoint A.
7. **Names.** Ward-to-name mapping was verified only against OSM nodes, not a city publication. "The Heights" and
   "Newport" have 2 and 1 buildings and no ranked unit today; they exist so that later buildings land correctly.
8. **Newark.** Ward names are not how people describe downtown Newark, and the split changes almost nothing. Leave
   Newark whole unless the repair changes the picture (`ADOPT` in the snippet above).

## 6. To adopt after the repair

1. Re-run `python3 scripts/build_subcity_neighborhoods.py` (no network needed; everything is cached) and re-read
   `data/reference/subcity_counts.csv`.
2. Decide the disputed buildings (section 3) and whether Newark is in.
3. Apply 4.1, then the fallbacks in 4.3.
4. `python3 scripts/run_all.py` (full, not `--fast`; no `--refit`), then check the Jersey City rows of
   `data/lifestyle_groups.csv` and the shown counts per new neighborhood against risk 1.
