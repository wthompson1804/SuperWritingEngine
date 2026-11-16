# Map component (prototype, written 2026-11-16)

A tap-and-zoom map of every neighborhood around Mom and Dad's, drawn as inline SVG with no tiles, no images and no
library. It is a prototype in its own files; `site/index.html` is untouched.

| File | What it is | Size |
|---|---|---|
| `site/map_base.json` | Land, the five boroughs, state and county lines, place-name points. Built, not hand-edited. | 52 KB |
| `site/map_component.html` | Standalone demo (opens from `file://`). Holds the component between `<!-- MAP COMPONENT START -->` and `<!-- MAP COMPONENT END -->` | block 35 KB; whole demo 113 KB with data embedded |
| `scripts/build_map_base.py` | Builds `map_base.json` from Census files (cached in `raw/census_cb/`, `raw/census_areawater/`) | |
| `scripts/build_map_demo.py` | Re-embeds a trimmed `site/data.json` and `map_base.json` into the demo | |
| `scripts/map_component_test.js` | Playwright walk-through, writes `site/screens/map_*.png` | |

Added weight for the page: base 52 KB + block 35 KB = **87 KB** (budget 250 KB).

Rebuild and test:

```
python3 scripts/build_map_base.py     # only when the frame, tolerance or labels change
python3 scripts/build_map_demo.py     # after site/data.json changes
node scripts/map_component_test.js    # 390x844 touch, 1280x900 mouse, reduced motion
```

## What it does

- Equirectangular projection with the true aspect at 40.8°N. The frame is fixed (74.95°W to 72.60°W, 39.98°N to
  41.95°N); the builder stops if a neighborhood in `data.json` falls within 0.08° of the edge or outside it.
- Base map: warm white land, pale blue-grey water, each borough in its own faint tint, dashed state lines, hairline
  county lines. Place names (states, boroughs, water) appear by zoom level and step aside when a mark would sit on them.
- A house on a short stem marks the anchor, labelled "Mom and Dad". At the widest view the label sits in open water
  with a dotted lead line so it does not cover marks.
- One mark per neighborhood. Shape and colour show the experience (year); size shows `counts.shown`; a hollow mark
  means no places are shown there.
- "Colour by drive time" recolours the marks in four bands of `drive_min` (30 or less, 31 to 60, 61 to 90, 91 to 120),
  with a legend that counts each band. Shapes stay, so the experience is still readable. No distance rings.
- Experience chips: tap one to dim the others; tap again to show all. Dimmed marks cannot be tapped or focused.
- Tap a mark: a card under the map with name, state, experience, places shown, minutes by car, round-trip tolls, the two
  crime rates as bars with Jamaica's 9.8 / 25.0 marked, and "See places", which calls `onSelectHood(id)`.
  - Toll `null` reads "Tolls not fully known"; `0` reads "No tolls" (the page's existing reading of 0); never "$0".
  - Missing crime rates read "Crime rates not known yet".
- Zoom: pinch, drag when zoomed, `+` / `−`, "Zoom to New York City", "Zoom to Hudson waterfront", "Whole map" (shown
  when zoomed), double-tap on empty map, Ctrl/Cmd + wheel or trackpad pinch. A tap picks the nearest mark within
  22 px (a 44 px target). A tap on a spot where marks overlap zooms in three times instead of guessing.
- Keyboard: the marks are one tab stop. Arrow keys move to the next mark in that direction, Home / End go to the
  shortest / longest drive, Enter or Space opens the card and moves focus to "See places", Escape closes it and returns
  to the mark, `+` `-` `0` zoom. A focused mark is brought into view and gets an ink ring.
- `prefers-reduced-motion`: zoom changes are immediate and the dimming has no transition.

## How to integrate

1. Copy everything between `<!-- MAP COMPONENT START -->` and `<!-- MAP COMPONENT END -->` in
   `site/map_component.html` into `site/index.html`: the `<style>` into the page's style block (all rules are prefixed
   `.hhm`), the `<script>` (one function, `initHouseHuntMap`) next to the page script. It reads the page tokens
   `--ink --muted --line --paper --white --berry-deep --display --body` and has fallbacks for each.
2. Make the base available the way `data.json` is: either fetch `map_base.json` beside the page, or have
   `scripts/build_site.py` inline it (for the published single file it must be inlined), for example
   `window.HOUSE_HUNT_MAP_BASE = {...}` in a second slot next to `<!--HOUSE_HUNT_DATA_SLOT-->`.
3. Call it where a map should appear:

```html
<div id="hood-map"></div>
<script>
var map = initHouseHuntMap(
  document.getElementById("hood-map"),
  DATA,                      // site/data.json as loaded by the page
  window.HOUSE_HUNT_MAP_BASE, // site/map_base.json
  {
    year: Y ? Y.id : null,   // start filtered on one experience; null shows all
    onSelectHood: function (id) { location.hash = "#hood-" + id; }
    // optional: mode: "drive", anchorLabel: "Mom and Dad", groupWord: "experience",
    //           yearStyle: { settled: { color: "#324BAE", shape: "circle" } }, onYearChange: function (idOrNull) {}
  });
// map.setYear(id|null), map.setMode("year"|"drive"), map.select(hoodId|null), map.zoomTo("nyc"|"hudson"|"all"),
// map.reset(), map.destroy()  (call destroy() when the view is replaced: it disconnects the resize observer)
</script>
```

The container needs a real width when `init` runs (it measures it); a `ResizeObserver` follows later changes. If the
view is built while hidden, call `init` after it is shown.

### Where it belongs in the flow

- **First screen (`#lives`)**: as the overview, `year: null`, in place of the current `mapSvg` overview with mile rings.
  `onYearChange` can scroll to or highlight the matching experience tile.
- **Inside an experience (`#year-<id>`)**: as an alternative to the neighborhood list, behind a "List / Map" switch,
  with `year: Y.id`. The other experiences stay as faint marks for context; "See places" goes to `#hood-<id>`.
  With the new "top three first" presentation, the list stays the default and the map is the way to see all of them.
- It does not apply the four limit sliders. To make it follow them, pass a `data` object whose `neighborhoods` are
  already filtered (or whose `counts.shown` are the counts within limits) and re-init; init takes a few milliseconds.

### Data fields read

- `meta.anchor.lat`, `meta.anchor.lon`; `meta.jamaica_yardstick.violent_per_1000`, `.property_per_1000`
- `years[].id`, `years[].label` (order of `years` fixes each experience's colour and shape)
- `neighborhoods[]`: `id`, `name`, `state`, `year`, `lat`, `lon` (or `clat`, `clon`), `counts.shown`, `drive_min`,
  `toll_round_trip`, `safety.violent_per_1000`, `safety.property_per_1000`, `safety.year`
- `map_base.json`: `proj` (`west`, `north`, `kx`, `scale`, `width`, `height`), `land`, `boroughs[].id/.d`,
  `state_lines[]`, `county_lines[]`, `labels[]` (`t`, `x`, `y`, `kind`, `min_zoom`)

## Colour

- Experience colours, in `years` order: `#4192C8` diamond, `#AA0E0E` square, `#F04288` triangle down, `#AA42F0` plus,
  `#324BAE` circle, `#AA8B0E` triangle up. Checked with the palette validator against the land colour: every pair
  separates under protan, deutan and tritan simulation (worst pair ΔE 10), worst normal-vision pair ΔE 19.7, all six
  at 3:1 or better against the land. Each also has its own shape and a chip filter.
- These are **not** the page's `YEAR_COLORS`. The page's six pastels fail the same check (blue and lilac are ΔE 0.8
  apart under protanopia; five of six are under 3:1 on white), so they cannot carry identity as small marks. Either
  keep the map's own set (the chips act as its legend), or pass `yearStyle` to force the page colours and rely on the
  shapes. This is a decision for Will.
- Drive bands: one hue, light to dark (`#FBE3EC`, `#EE9BBB`, `#BE4279`, `#5E1740`), each mark outlined in ink because
  the lightest step alone is too close to the land (1.2:1).

## Base geometry: source and method

- Counties: `https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip`, retrieved
  2026-11-16T00:04:30Z. That file is clipped only to the ocean and Sound shoreline; the Hudson, the East River and the
  bays are still land in it.
- Water: TIGER/Line 2023 AREAWATER, one file per county in the frame (39 counties),
  `https://www2.census.gov/geo/tiger/TIGER2023/AREAWATER/tl_2023_<FIPS>_areawater.zip`, retrieved 2026-11-16 00:06 to
  00:08Z. Water polygons of 150,000 m² or more are merged, bodies under about 3 km² dropped, and the rest cut out of the land.
- Simplification: Douglas-Peucker at 0.0008° (about 90 m) on longitude-scaled coordinates; islands under about
  0.07 km² dropped; coordinates stored as integers of 0.0005° in relative SVG path commands.
- The source URLs, retrieval times, county list and rules are inside `map_base.json` under `meta`.
- www2.census.gov answered every request with 200. `docs/SOURCES.md` has no row for these two products yet (it was not
  mine to edit); the facts for that row are in this section.
- Raw downloads: 12 MB + 19 MB under `raw/`, re-creatable by the builder.

## Known limits

- **Neighborhood coordinates are rounded to two decimals in `data.json`** (about 1 km), so a mark can sit a few blocks
  from the true centre and, at deep zoom, on the wrong side of a shoreline. Neighborhoods that share one coordinate
  are fanned out by 9 px. More decimals in `data.json` would fix both.
- At the widest phone view the city is one pile of marks under the house. That view answers "where is everything";
  picking a city neighborhood takes one tap on "New York City" or one tap on the pile first.
- Borough and place names are hidden wherever a mark would sit on them, so in the New York City view the borough names
  often do not show; the tints still separate the boroughs. Names of neighborhoods are drawn only from zoom 4.5 up, and
  only where they fit.
- While zoomed, a one-finger drag pans the map, so the page cannot be scrolled from inside the map (it can from
  anywhere else, and "Whole map" restores it). At the widest view a vertical drag scrolls the page as usual.
- Pinch was tested with synthetic touch events in Chromium only; no real phone and no Safari run yet.
- Six chips with the full experience names take three rows on a phone (about 150 px). Shorter labels in the data would
  cut that to two.
- Screen readers get each mark as a button with name, experience, places and minutes; there is no table view in the
  component, because the page's neighborhood list already is one.
- The component does not know about limits, held places or avoid cards.
- Place-name points in `map_base.json` are hand-placed for labelling and are not data.
- No dark theme: the page is light-only (`color-scheme: light`), and so is the map.
- The interface says "experience" for a year (Will's wording of 2026-11-16); the chip labels are `years[].label` as
  they stand in the data ("The … Year") until the data changes.
