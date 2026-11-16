# Experience illustrations

Six original scene drawings, one per experience, as inline SVG. Built by `scripts/build_illustrations.py`
(no network, no dependencies, idempotent) from `site/data.json` `years[]`.

- `site/illustrations.json`: the drawings.
- `site/illustrations_preview.html`: review page with all twelve (not linked from the page).
- `site/screens/illustrations_preview.png`: that page at 390 px wide.
- `site/screens/illustration_tile_<n>.png` (n = 1 to 6, in `years[]` order): each banner alone at 330 by 120 CSS px
  on the page background. `site/screens/illustrations_six_tiles.png`: the six side by side, for telling them apart.

## How they are keyed

`illustrations.json` is one object. For each experience:

- `years[].label` (for example `"The Quiet-Street Year"`) holds the entry:
  `{"alt": "...", "banner": "<svg ...>", "tall": "<svg ...>"}`.
- `years[].display_label` and `years[].id` are also keys, but their value is a **string**: the `label` key that holds
  the entry. Full copies under three keys would triple the file (about 270 KB against a 110 KB budget).

Lookup:

```js
function illustration(IL, key) {            // key: label, display_label or id
  var e = IL[key];
  if (typeof e === "string") e = IL[e];
  return e || null;                        // {alt, banner, tall}
}
```

- `banner`: viewBox `0 0 360 130`, for the experience tile.
- `tall`: viewBox `0 0 360 200`, for the top of the experience page. Same scene moved down 44 units, with more sky
  above and a 26-unit foreground strip below.
- `alt`: the plain description. It is also each SVG's `aria-label` (`role="img"`), so do not repeat it next to the art.

Insert with `innerHTML` into a block container and size the SVG with CSS (`width:100%; height:auto; display:block`).
The art is square-cornered and runs edge to edge: round it with `overflow:hidden` on the container. Each SVG has
`preserveAspectRatio="xMidYMid slice"`, so a container with a different ratio crops the edges and does not letterbox;
the subjects sit inside the middle 340 by 110.

## Style rules

- Flat shapes only. Outlines are 2 px ink (`#3A1630`) with round joins; small parts use 1.5 px; texture (bricks,
  paving, grass, waves) is small unstroked marks. No gradients, no filters, no text or lettering, no logos, no real
  buildings. The one use of opacity is the porch-light halo in the dusk scene. Brick courses and paving joints are
  dashed lines (`S.tex`, `stroke-dasharray`), which costs far fewer bytes than one mark per brick.
- Colours are literal hex. They are the page tokens (`--paper`, `--ink`, `--muted`, `--berry`, `--berry-deep`,
  `--rose`, `--blush`, `--butter`, `--butter-deep`, `--mint`, `--mint-ink`, `--plum2`, `--coral-ink`, `--line`,
  white), tints made by mixing two of them (`mix()` in the script), and the experience's identifying colour from
  `docs/MAP_COMPONENT.md` (in `years[]` order: `#4192C8`, `#AA0E0E`, `#F04288`, `#AA42F0`, `#324BAE`, `#AA8B0E`) with
  its tints. The sky is always a light tint of the identifying colour, which gives each tile its own cast (the two
  evening scenes, Quiet-Street and Walk-Everywhere, deepen it with `--plum2`).
  If the page changes the experience colours, change `ACCENT` in the script and rebuild.
- **One exception to the palette: water.** The tokens have no blue, and water drawn in mint read as lawn. `WATER`
  (`#7FC4CF`, a soft blue-teal) and `WATER_L` (`#BFE3E8`, its lighter tint) are used for water and its reflections
  only (the Fresh-Start scene). Do not use them for glass, sky or anything else.
- The six must stay different at tile size. Each has its own dominant shape and horizon: Quiet-Street = gabled houses
  at dusk; Little-City = clock tower, theatre blade sign and marquee; Fresh-Start = towers left, open water right;
  Walk-Everywhere = wall-to-wall narrow fronts in the evening, string lights, cafe tables, no road;
  Old-Neighborhood = two big brick blocks by day with the elevated train over a bus stop and a road in front;
  Room-to-Breathe = one low building with a bay window, lawn and wide sky. Striped awnings belong to the Little-City
  bakery only.
- Her car is berry (`--berry`) wherever it appears.
- The dog is the same in every scene (`dog()`): small, white, caramel ear and patch, berry collar, drawn at 0.85 to
  0.9 scale on the nearest ground.
- Pure inline SVG: no `<style>`, `<image>`, `<foreignObject>`, `<script>`, external references or `id` attributes
  (so nothing can collide when six sit on one page). Every shape has an explicit `fill`. Strokes come from the
  enclosing `<g>`.
- Budget: each SVG under 9 KB, the JSON under 110 KB. The script prints the sizes.

## How to add or change a scene

1. Write a function `scene(A, tall)` in `scripts/build_illustrations.py` that returns `(sky colour, S)`. Draw in
   banner coordinates (x 0 to 360, y 0 to 130) with the `S` helpers (`r`, `c`, `e`, `p`, `line`) and the shared
   parts (`grid`, `dots`, `bricks` with `S.tex`, `awning`, `tree`, `cloud`, `lamp`, `car`, `dog`). The last argument of the helpers is the
   stroke width (0 for none).
2. When `tall` is true, also draw sky extras between y = -44 and 0 and a foreground strip between y = 130 and 156,
   and let the lowest ground band run down to 156. Keep buildings below y = 4 so the banner does not cut them.
3. Add it to `SCENES` under the experience `id` with its description, and add the id to `ACCENT`.
4. Run `python3 scripts/build_illustrations.py` (it writes both files atomically), then look at the preview at 390 px
   wide and at each banner at 330 by 120 px (Playwright screenshots, see the files listed at the top) and check: the
   scene reads without its label at the small size, it cannot be mistaken for another of the six, the dog is visible,
   nothing is cut off in either crop, and the sizes are inside the budget.
