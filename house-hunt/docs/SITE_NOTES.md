# Site notes: `site/index.html` (written 2026-11-15)

The page is one file with inline CSS and JS. It reads `window.HOUSE_HUNT_DATA` when present and otherwise fetches
`data.json` from its own folder. `python3 scripts/build_site.py` writes `site/dist/index.html` with the data inlined
(it fills the `<!--HOUSE_HUNT_DATA_SLOT-->` marker). Nothing but `site/data.json` feeds the page.

Layout, CSS, interaction code and accessibility patterns come from `site/mock4_reference.html`. No place, person,
quote, hook, "flavor" sentence or scene text from the mock is in the page.

Routes: `#lives`, `#year-<id>`, `#hood-<id>`, `#unit-<id>`, `#compare`. State (limits, held places, tour seen) is in
`localStorage` under `lamia-house-hunt-v1`, inside try/catch.

Test: serve `site/` (`python3 -m http.server`) and run
`BASE=http://localhost:PORT OUT=site/screens node scripts/site_walkthrough_test.js` (add `W=360` for the narrow run,
which takes no screenshots). It walks the whole flow, asserts no console errors and no horizontal overflow, checks the
limit counts against the data, and opens every year, neighborhood and unit view once.

## Tint rules (the `TINT` table at the top of the script)

| Tile | Deciding inputs | Strong when | Not known yet when |
|---|---|---|---|
| Wake up | `moments.wake.park_walk_min` | walk to green space ≤ 5 minutes | the walk is null |
| Work | `moments.work.sqft`, `.separate_bedroom` | a separate bedroom and ≥ 650 sq ft (the Queens median) | sqft is null |
| After work | `moments.after.restaurants_800m` | ≥ 20 restaurants within 800 m | the count is null |
| Night | `moments.night.violent_vs_jamaica`, `parking.rank` | violent crime ≤ half of Jamaica's rate and parking rank ≥ 3 (covered, garage, gated) | the crime ratio is null |
| Saturday | `moments.sat.bars_1600m`, `.restaurants_1600m` | ≥ 5 bars and ≥ 25 restaurants within a mile | either count is null |
| Sunday | `vs_queens.drive_min` (five-point scale) | point ≥ 3: no more than 5 minutes farther than the typical Queens place | the point is null |

Everything else is Mixed. Unknown parking alone makes Night Mixed, not "Not known yet" (the sheet says the parking is
not known). Sunday follows Will's later ruling that closer is better. `TINT.SUNDAY_BY_SCALE = false` puts Sunday back to
"Your call" for every place, as in the mock; with it on, "Your call" is never used and the legend leaves it out.
`moments.work.fiber` is always null, so the Work sheet says "Internet (fiber or not): Not known yet" and fiber plays no
part in the tint.

Limits (four sliders): cost $1,600 to $3,000 (floor of the cheapest all-in to the cap), drive 5 to 120 minutes, safety
in four steps (violent crime no higher than Jamaica's rate, under 75%, under half, under a quarter), space 350 to 950 sq ft
(from the data). A place with an unknown size or crime ratio drops out as soon as that limit is moved off its start.

## Template sentences

All in the `SAY` object plus the small builders next to the views. `{…}` is a data field; a null gives the
"Not known yet" form shown after the slash.

- Size: "A {studio|one-bedroom} of {sqft} sq ft on floor {floor}." Adds "(floor worked out from the unit number)" when
  `floor_basis` is `inferred` / "A studio, size not known yet, on floor 6."
- Park: "{park} is a {n}-minute walk." / "Walk to green space: Not known yet."
- Dog park: "{dog_park} is {a n-minute walk | x miles away}." ("The nearest dog park" when unnamed.)
- Food: "{restaurants} restaurants and {bars} bars within a 10-minute walk." (800 m is called a 10-minute walk.)
- Drive: "{drive} minutes by car to Mom and Dad without traffic; {toll} in tolls a visit | no tolls | tolls not known yet."
- Crime: "Violent crime here runs at {x} times the rate around Mom and Dad's." ("at the same rate as" when x is 1.)
- Parking: "The car sleeps in {a garage | a gated lot | covered parking | an open lot | street parking}, {$fee} a month |
  fee not known yet." / "The listing mentions parking but not what kind." / "Where the car sleeps: Not known yet."
  The kind comes from `parking.rank` (4 garage or gated, 3 covered, 2 open lot, 1 street) because `parking.type` is free text.
- Supermarket: "{supermarket} is {distance}." Cafés: "{n} cafés within a 10-minute walk."
- Train: "{station} station is {distance}." Transit: "{n} minutes by train and bus on a Saturday, {k} transfers."
- Availability: "Available now." / "Available {date}."
- Year card and year page: "A typical place: {sqft} sq ft for {all_in} a month, all-in"; "A typical drive to Mom and Dad:
  {drive} minutes without traffic, {toll} in tolls a visit"; "Violent crime: {v} per 1,000 residents a year; around Mom
  and Dad's it is {jamaica}"; "{n} restaurants within a 10-minute walk; green space a {n}-minute walk" (year medians).
- Neighborhood card: the crime and food sentences from `neighborhood.safety` and `.traits`, plus "Green space is a
  {n}-minute walk". Neighborhood page: parking kinds counted over its places, car thefts per 1,000, park area, dog park
  distance, supermarket and water distance, and census shares (one-person households, children, ages 25 to 34, moved in
  within a year, work from home, no car). No income, race, ethnicity or religion.
- Tile captions: "Green space, {n} min walk"; "{sqft} sq ft, own bedroom | studio"; "{n} restaurants on foot";
  "{parking}, crime {pct} of Jamaica's"; "{n} bars, {n} restaurants in a mile"; "{n} min drive, {tolls}".
- Unit page paragraph: size, parking, park, food, drive and crime sentences joined.
- "You'll love": each five-point measure at 4 or 5 ("Space: better than staying in Queens (+106 sq ft)") and stated
  amenities, each linked to the listing, then `evidence.positive` as dated quotes with links.
- "Gives us pause": `evidence.pause_notes`, each measure at 1 or 2, unknown cost lines, a rent offer that needs a
  call, an unchecked building, a listing whose last check was not "live", then `evidence.items` as dated quotes.
- Compare, "The trade, in plain words": cost difference; square feet (when both known, 50 or more); parking kind;
  violent-crime ratio (a gap of 0.05 or more); minutes by car. "What that feels like": the monthly gap over 12 months;
  hours in the car for four visits a month; tolls for those visits (or "not known yet"); the space gap as a percentage
  of the smaller place. The mock's "about one extra room" was dropped as a guess.
- Five-point sheet: this place's value, the Queens median, the difference, the two band sizes and the direction, all
  from `meta.queens_spectrum`. Measure labels are a small lookup keyed on `measure`, with a fallback that tidies the key.

Every price shows "seen {date}" from `price_seen_at`. The receipt lists `all_in_lines` with each basis; `estimate` and
`unknown` lines carry an asterisk and a footnote; unknown lines read "not counted"; `all_in_unknown` is named.
The "Rent terms" box (when `rent.asterisk`) shows the offer text verbatim, the rent used, the gross rent, free months,
lease length, first full payment date and note, and "Needs a call". When `all_in_gross` is over $3,000 and `all_in` is
not, a red line says a paying month costs more than the cap.

## Still placeholder

- `years[].scenes` is null: the "A day in this year" section shows the four typical-figure sentences instead. The slot
  takes a string, a list of strings, or a list of `{text, url, date}`.
- `years[].catch` is null: the year card shows no catch line, and the third dark tile on the year page shows the
  typical violent-crime rate. A string (or `{text}`) turns both into "The catch".
- `neighborhoods[].local.parking_rules` and `.dog_rules` are null: shown as "Street-parking rules: Not known yet" and
  "Local dog rules: Not known yet". A string or `{text}` replaces them.
- `neighborhoods[].local.voices` is empty: the "The feel" section is left out. Items shaped like evidence
  (`excerpt`, `date`, `url`, `source`) render as dated quotes with a source link.
- Unit hooks ("The one with…") are gone; the size sentence stands in their place.

## Known gaps

- Source links exist only where the data has a URL: the listing, the building page and each evidence item. Map counts,
  travel times, tolls and crime rates carry no URL in `data.json`, and each tile sheet says so.
- 109 of the held places sit in neighborhoods that are not in `neighborhoods[]`. They appear on the year page under
  "Worth a phone call, in other towns", with a town name read from `hood_id` (for example `nj:woodbridge`).
- The map has no coastline or roads: pins from real coordinates, rings in straight-line miles. Year pins are numbered to
  match the list (names are drawn only with five or fewer); overlapping pins are nudged apart with a line to the true spot.
  Pins are smaller than 44 px; the list below each map is the full-size way in.
- Drawings are decoration. Height uses `amenities.building_floors` (known for 64 of 207 places) and is capped at five
  rows with the real count written above; otherwise a plain three-row building with no number. Parking unknown draws a "?" sign.
- Neighborhoods have no photo link, so only unit pages carry "Tap here for photos".
- `parking.type` is messy free text; one value is unrelated amenity text. Labels come from `parking.rank`; the raw text
  appears in the Night sheet only when it is between 12 and 180 characters.
- Evidence excerpts are shown verbatim and a few mention staff by first name. Excerpts that start with a digit
  (city-record counts) are shown as "On record:" and their dates are null in the data.
- `rent.basis_kind` is `net_effective` for most places with no offer; the rent box only appears when `rent.asterisk`.
- Fonts load from Google Fonts, as in the mock; offline the page falls back to system fonts.
- The wish-list chips from the mock were dropped (the UX brief drops them, and their thresholds were invented).
- Compare hides a day-part row when the tints match, as in the mock, even if the captions differ; the toggle shows all ten rows.
