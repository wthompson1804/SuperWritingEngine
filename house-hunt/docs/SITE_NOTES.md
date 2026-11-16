# Site notes: `site/index.html` (written 2026-11-15, updated the same evening for confirmation asterisks, local rules, voices and sources)

The page is one file with inline CSS and JS. It reads `window.HOUSE_HUNT_DATA` when present and otherwise fetches
`data.json` from its own folder. `python3 scripts/build_site.py` writes `site/dist/index.html` with the data inlined
(it fills the `<!--HOUSE_HUNT_DATA_SLOT-->` marker). Nothing but `site/data.json` feeds the page.

Layout, CSS, interaction code and accessibility patterns come from `site/mock4_reference.html`. No place, person,
quote, hook, "flavor" sentence or scene text from the mock is in the page.

Routes: `#lives`, `#year-<id>`, `#hood-<id>`, `#unit-<id>`, `#compare`. State (limits, held places, tour seen) is in
`localStorage` under `lamia-house-hunt-v1`, inside try/catch.

Tables at the top of the script, each meant to be corrected in one place: `TINT` (tile colours), `SOURCES` ("How we got
this" wording), `RULE_WORD` / `PARK_RULE_ORDER` / `DOG_RULE_ORDER` / `SAT_RULES` / `WAKE_RULES` / `RULE_FLAG` (local
rules), `CONFIRM_WORD` / `CONFIRM_Q` (confirmation asterisk), and the fixed sentences `Q_PARKING`, `Q_EVIDENCE`,
`NO_EVIDENCE`, `SMALL_DOG`, `NO_PARK_RULES`, `NO_DOG_RULES`, `NO_VOICES`.

Test: serve `site/` (`python3 -m http.server`) and run
`BASE=http://localhost:PORT OUT=site/screens node scripts/site_walkthrough_test.js` (add `W=360` for the narrow run,
which takes no screenshots). It walks the whole flow, asserts no console errors and no horizontal overflow, checks the
limit counts against the data, and opens every year, neighborhood and unit view once. It also opens a unit with a
confirmation asterisk from its card, a neighborhood with local rules and its Saturday and wake-up sheets, a neighborhood
without rules, a street-or-unknown-parking unit under a flagged parking rule, a small-dog unit and a no-public-evidence
unit, and it turns on the "nothing left to confirm" limit and reloads to see it kept. Resident voices are empty in the
data, so the test feeds one neighborhood made-up quotes (through a route on `data.json`, in the test only) to check
grouping, balance, the fold and overflow.

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
A fifth control, the checkbox "Only places with nothing left to confirm", sets aside every place whose
`confirm.asterisk` is true (212 of 325 today); it is saved with the sliders and cleared by the reset link. A rent
asterisk alone does not count.

## What the update added (all from `data.json`)

- **Confirmation asterisk** (`unit.confirm`). A berry `*` after the name and a butter pill "* To confirm: the floor /
  the elevator / whether dogs are allowed / that the listing is still live" on the card and the unit page. The unit
  page has a dashed box "* Still to confirm" quoting `confirm.why`, then "What to ask:" with the matching line from
  `tour_questions` (found by `CONFIRM_Q`'s pattern; when the list has none, as for a live check, the fallback
  question in `CONFIRM_Q` is used and added to the tour questions). Home, year and neighborhood each say "N of the M
  places … carry an asterisk". The rent asterisk stays on the price; the pill's words tell the two apart.
- **Small dogs**. When `dog.weight_limit_lb` is null and `dog.size_note` is set (the pipeline's small-only test; the
  fallback is `policy_text` with "small" and without "large"), the unit page says "For the dog: The page says small dogs;
  no weight number given" under the opening paragraph, with the listing link. The wake-up sheet and the building facts
  use the same words. It is not put under "Gives us pause".
- **Local rules** (`neighborhood.local.parking_rules`, `.dog_rules`). On the neighborhood page, under "For the car"
  and "For the dog": label, summary and a link named after the municipality; the first three in `PARK_RULE_ORDER` /
  `DOG_RULE_ORDER` are shown and the rest sit in a "N more parking rules" fold. With none: "Local parking rules not
  found yet. On a tour, ask: Where do residents park overnight, and is a permit needed?" and "Local dog rules not found
  yet." Every unit in a neighborhood without parking rules gets that question in its tour list. The Saturday sheet
  quotes the overnight, permit, guest and city-lot rules; the wake-up sheet quotes leash, parks, dog-park and clean-up
  rules. A unit whose parking kind is street, unknown or "kind not stated" shows a box "Before the car sleeps on the
  street" when a rule matches `RULE_FLAG`: an `overnight_parking` summary that reads as a ban or permit requirement, or a
  `resident_permit` summary that ties the permit to registration. These are word patterns on the summary, so a new
  summary phrased differently can be missed or wrongly caught; check the box after each local-rules refresh.
- **What residents say** (`local.voices`, `local.survey`). Always present. Empty: "No resident comments found yet."
  Filled: one heading per theme; where a theme has both positive and negative quotes, the same number of each is shown
  (up to two, newest first, alternating) and the rest go in a "N more on this" fold; with one side only, up to three and
  a line saying only that side was found. Each quote shows Positive/Negative, date, context and a link named after the
  source; no names. Survey rows read "{measure}: {value}." with source, as-of date and link.
- **Evidence labels** (`evidence.public_evidence`, added to `build_page_data.py` from `data/avoid_buildings.csv`).
  "none readable" or "rating screen: not_enough_data" with no items, quotes or pause notes gives, under "Gives us
  pause", "No public records or readable reviews for this building; ask on the tour" (153 units today), plus the tour
  question in `Q_EVIDENCE`. Null (the building was not in the evidence pass) keeps "…have not been checked yet". The
  building facts name what was read (`EVIDENCE_WORD`).
- **Held and waiting lists**. `held[]` stays under "Worth a phone call" (intro now says two or more things to confirm;
  each item shows `confirm.why`). `awaiting_live_check[]` today is 190 rows, 189 of them the same places as `held[]`:
  those stay in "Worth a phone call" with a line "* Not re-checked yet …", so nothing is listed twice. A row that is not
  in `held[]`, `units[]` or `avoid[]` (one today, in Stamford) appears under "Not re-checked yet" on its neighborhood
  page, or in a year-page fold when its neighborhood is not listed. Without the list both pieces are skipped.
  `build_page_data.py` now also writes `year` and `price_seen_at` on those rows.
- **Sources**. Every URL in the data is linked: listing, building page, evidence items, each local rule, each voice
  and survey row, each waiting row. Figures with no URL carry a "How we got this" line built from `SOURCES`: on every
  tile sheet, the five-point sheet, the unit paragraph, the neighborhood "What's here" and "Feeling safe" sections, the
  year "What it costs you" section, under the home map, and as a list in the footer. Crime lines add the police agency
  and year from the data. The tolls and census wordings ("E-ZPass toll rates for the toll points on that route", "U.S.
  Census Bureau American Community Survey") are mine, not from the brief; correct them in `SOURCES` if wrong.

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
- `neighborhoods[].local.voices` and `.survey` are empty for all 132 neighborhoods: the section shows "No resident
  comments found yet." The filled layout has only been seen with the test's made-up quotes.
- Local rules exist for 62 (parking) and 57 (dog) of 132 neighborhoods; the rest show the "not found yet" lines.
- Unit hooks ("The one with…") are gone; the size sentence stands in their place.

## Known gaps

- Map counts, travel times, tolls and crime rates carry no URL in `data.json`; they are sourced in words only.
- A unit with both a rent offer and an open confirmation shows two asterisks (price and name). The words beside each
  say which is which, but the mark is the same character.
- New York City neighborhoods carry 12 or 13 parking rules each; three show and the rest are one tap away.
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

## UI pass 2

(2026-11-16. Scripted Playwright walk at 390×844, then 1280×900, 320×640 with reduced motion, and the built file with
its outer doctype/html/head/body tags stripped and re-wrapped, as publishing does. Before and after phone screenshots are
`site/screens/before-*.png` and `after-*.png`; `after-1x-test-data-*.png` use made-up test values for fields the data
does not carry yet. The "before" set was taken on the earlier data build.)

### Changed

- **Words.** "Years" are "experiences" in every interface string. The shown label is `display_label` when the data has
  it, else `label` with a trailing " Year" swapped for " Experience"; keys are untouched. Routes are `#lives`,
  `#exp-<slug>`, `#hood-<slug>`, `#unit-<slug>`, `#compare`, where a slug is the id in lower case with every run of
  other characters turned into a hyphen. The old forms (`#year-<id>`, `#unit-<encoded id>`) are still read.
- **Top three, then more.** An experience lists its first three neighborhoods (by `rank_in_experience` when present,
  else the given order), then "Show more neighborhoods" (six at a time) and "Show all N", with "3 of 22 neighborhoods
  shown". A neighborhood lists its first three places (the order of `unit_ids`), then "Show more places" (three at a
  time). The first card carries "Top pick", the next two "2" and "3" (neighborhoods say "Top pick" only when the data
  ranks them; the pin number serves for 2 and 3). The opened count is kept while the page is open, so Back returns to the
  same list. The map still shows every neighborhood. Avoid cards follow the places.
- **Host voice.** One speech style ("Your host says", rose bubble with a microphone) for `host.intro` and
  `host.walkthrough` on an experience, `host.intro` on a neighborhood, and `host.line` plus `host.catch` on a place (on
  its page, and on its card when it is one of the top three). Nothing in that bubble is written in the template.
- **Prose.** `prose.scene / promise / catch` on an experience and `prose.scene / good_for_her / watch_for` on a
  neighborhood are shown when present (flat fields of the same names are read too). With prose, the generated typical
  figures move into a fold; without it the page shows what it showed before. `described[]` on a neighborhood is shown
  under "How others describe it" as quoted lines with the source named and linked (three, then a fold).
- **Contact.** `contact` on a place gives a "Phone and hours" box: the number as selectable text with a "Copy number"
  button, hours, note, site link and where the number was found. No `tel:` link. It also appears on "Worth a phone call"
  items and in the copied tour list.
- **Asterisks.** Any `confirm.what` / `confirm.why` text is shown as given; `CONFIRM_WORD` only tidies the kinds it
  knows. `confirm` may be one object or a list; `confirms[]`, `asterisks[]` and flat `confirm_what` / `confirm_why` /
  `what_to_confirm` are read as well, and `question` is used for "What to ask". Every card that carries an asterisk now
  prints what is to confirm and why (place cards, avoid cards, phone-call items, a "Still to confirm" row in compare).
- **Rent.** A net-effective rent always shows its asterisk, the rent in a paying month and the first full payment date
  (or says each is not known) on the card, the place page, phone-call items and compare. Lease term and 12-month price
  show when present (`rent.lease_months`, `cost_check.lease_term_months`, `rent.price_12mo`, `cost_check.price_12_month`
  and a few spellings of each); a lease longer than 12 months with no 12-month price says "The 12-month price is not
  published". The rent terms box opens for any of these, not only for `rent.asterisk`.
- **Unknown is never zero.** Receipt lines with basis `unknown` (or a null amount) read "not published" and are named as
  left out of the total; a true zero reads "no charge" / "no monthly charge". The footer drops any `meta.notes` line
  that says "$0" and adds its own sentence; "(counted as $0)" is removed from `confirm.why` when shown.
- **Dates on prices.** Added to the bottom bar, the experience cards and tiles, neighborhood cards and leads, and the
  five-point sheet. Signs, receipts, compare and phone-call items already had them.
- **Navigation.** The page sets `history.scrollRestoration = "manual"`, so browser Back from a place returns to the
  same spot in the neighborhood (it used to land at the top). The breadcrumb on a place is experience › neighborhood.
- **Bottom bar.** The page measures the bar and keeps that much room under its last line (`--tray-h`), so the bar no
  longer depends on a fixed 150 px; toast and first-run card sit above it. Safe-area padding on the bar and the sheets.
- **Layout fixes.** Source links no longer stretch their line to 44 px (the tap area is kept with padding); survey
  figures drop repeats and fold after four; the limits strip has two columns on a phone so "Old-Neighborhood" is not
  broken mid-word; neighborhood card footers line up; long unbroken text wraps inside pills and boxes; the price sign and
  bar cope with an unknown price; "Unit 403" does not split across lines.
- **Empty and missing.** Records are normalised on load, so a place with a missing block renders as "Not known yet"
  instead of failing. An experience with no neighborhoods, an experience with no figures, a neighborhood with nothing,
  a place whose neighborhood is absent (not openable), no listing link, no price date and quotes with no date or source
  all render. Quotes strip `u/name` and `@name` handles.
- **Accessibility.** Focus ring is ink on light surfaces and butter on dark ones (the old butter ring was faint on
  white). Reduced motion turns off every animation and transition. "Show more" keeps focus on the control.
- **Copying.** When the clipboard is blocked the tour list appears in a read-only text box to select by hand.
- **Publishing.** `<meta name="claude:viewport-fit-sides" content="cover">` after the title; side gutters are
  `max(16px, env(safe-area-inset-left/right, 0px))`; no dialogs, print, downloads, `tel:` or `mailto:`; storage only
  in try/catch (the page was walked with storage throwing); fonts from Google Fonts only; no external scripts; the built
  file is about 3.2 MB.

### Fields the template now reads (beyond those listed above in this file)

- experience (`years[]`): `display_label`, `prose.scene`, `prose.promise`, `prose.catch`, `host.intro`,
  `host.walkthrough[]` (also flat `scene`, `scenes`, `promise`, `catch`).
- neighborhood: `rank_in_experience`, `experience_score_basis`, `prose.scene`, `prose.good_for_her`, `prose.watch_for`,
  `host.intro`, `described[] {quote, source, url, date}`.
- place: `confirm {asterisk, what, why, question}` (or a list), `host.line`, `host.catch`,
  `contact {phone, hours, site, kind, note, source}`, `rent.lease_months`, `rent.price_12mo`,
  `cost_check.lease_term_months`, `cost_check.price_12_month`, `rent.lease_term_text`.
- voices: `about` (added by another agent during this pass).

### Not fixed

- `meta.notes` still carries "Unknown cost lines count as $0 …" and twelve `confirm.why` texts say "(counted as $0)".
  The page hides both wordings; the builder should stop writing them.
- Neighborhoods without `rank_in_experience` are listed in the given order and the first is not called "Top pick".
- A very long neighborhood name is cut with an ellipsis in the breadcrumb (the full name is the page heading).
- Map pins are smaller than 44 px; the list under the map is the full-size way in. Checkboxes are 22 px inside a
  44 px label.
- `scripts/site_walkthrough_test.js` was not run or updated (not mine to edit). It will need the new routes, the
  "Show more" step and the new asterisk wording.
- The "Typical figures", tile captions and other template sentences listed above are still generated in the template.
- With storage blocked, the first-run "How this works" card shows on every load.
- Evidence quotes whose source gives only "4 weeks ago" show "date not known" beside the source's own words.

## Map integration

(2026-11-16. The map component of `docs/MAP_COMPONENT.md` is now part of `site/index.html`.)

### What changed

- **Build.** `scripts/build_site.py` fills a second marker, `<!--HOUSE_HUNT_MAP_BASE_SLOT-->`, with
  `window.HOUSE_HUNT_MAP_BASE` (`site/map_base.json`, 53 KB). Opened beside its files, the page fetches `map_base.json`
  once instead. If the base or the component is missing, the map's place shows "The map could not be drawn here".
- **Component.** The style and script between the two markers of `site/map_component.html` are pasted in. Lines that
  differ from the prototype carry a `page:` comment: a label hook (`yearLabels {id: {label, short}}`), short chip text on
  a phone and the full name from 520 px, three chips to a row (two rows of three at 390 px; three rows of two under
  360 px), `onSelect(id)`, the rank pill and "k of N fit your limits" on the card, the E-ZPass note, a "More" fold for
  the crime bars, and one short hint. The page also restates the font size of four buttons, because the component's own
  `.hhm button{font:inherit}` outranks them. `site/map_component.html` itself was not edited, so it and the page differ.
- **First screen.** The mile-ring `mapSvg` is gone. The six experience cards stay the way in; "See them on a map" jumps
  to the map under them, started with `year: null`.
- **Inside an experience.** A List / Map switch above the neighborhoods. List is the default and still shows three,
  then more. Map starts on that experience (other experiences faint) and zooms to its neighborhoods and Mom and Dad's.
  The choice is kept in `localStorage` (`lamia-house-hunt-v1-hoodview`) inside try/catch, and in memory when storage
  throws.
- **Life cycle.** One instance at a time. `renderView()` calls `destroy()` before it replaces the view and mounts after,
  only when the container has a width. "See places" goes to `#hood-<slug>`. Browser Back returns to the same scroll
  position with the same card open (the selection is remembered per page for the visit; the zoom is not).
- **One identity per experience.** `YEAR_MARKS` (the map's six colours and shapes, in `years[]` order) is passed to the
  map as `yearStyle` and drawn by `ymark()` on the experience cards, page titles, breadcrumbs, neighborhood cards and
  the limits strip. The pastel `YEAR_COLORS` remain only as fills for the drawings and the number pins.
- **Counts.** Marks are sized by the places that fit the viewer's limits; a hollow mark has none. Only neighborhoods a
  list shows are on the map, so chip counts match the lists.
- **Coordinates.** The page no longer replaces a neighborhood's `lat` / `lon` with the mean of its places (that was a
  workaround for two-decimal coordinates). The component's fan-out for marks that share a pixel is unchanged.
- **Card.** Experience, rank within it ("Top pick" / "#4 of 22", from `rank_in_experience` and the length of the
  experience's list), places shown, minutes by car, tolls, "See places" (or "See this neighborhood" when it has none).

### What is weak

- **The built page is over 4 MB.** `site/data.json` alone is 4.86 MB at the last build (it was 3.1 MB when this work
  started); the template is 244 KB and the map base 53 KB. The walkthrough prints the three figures and a warning. The
  fix is in the data (`neighborhoods[].local` is over 1 MB; `units[].scores` is never read by the page).
- A re-render (a limit moved, Back) rebuilds the map, so zoom and pan are lost; the open card is kept.
- A mark under the house or its label cannot be tapped until zoomed in. At 320 px the six chips take three rows.
- While zoomed, a one-finger drag pans the map, so the page cannot be scrolled from inside it.
- Tested in headless Chromium only (touch and mouse, 390, 1280 and 320 px, reduced motion, storage throwing, the built
  file re-wrapped). No Safari, no real phone, no screen reader.
- In strips and chips the toll note is shortened to "NY E-ZPass"; sentences say "with a New York E-ZPass".

## UI pass 3: headlines first

(2026-11-16, after Will walked the preview: "a consumer experience, not B2B software… everything should be collapsible
with the headline conclusion visible". Structure follows `docs/NAV_PATTERNS.md` except where noted.)

### The building blocks

- **Row** (`row()`): a native `<details>` with a small caps label, a headline built by a function in `HL` from the data,
  an optional written subhead (`<record>.headlines.<section>.subhead`, lighter, two lines at most), at most one chip
  ("Ask", "Offer", "Near the cap", "Lease term", "Street rules", "2 to know") and a caret. No row starts open. Rows are
  independent; "Open all / Close all" sits above them. What is open, and whether the host text is expanded, is
  remembered per page for the visit (`OPENED`), never stored.
- **Headline builders** (`HL.cost`, `trip`, `parking`, `dog`, `building`, `confirm`, `day`, `queens`, `voices`, `rules`,
  `hoodRules`, `described`, `here`, `out`, `yearCost`, `yearTrip`, `first`): pure functions, reachable for tests as
  `window.__houseHunt.HL`. Unknown reads "not published, ask" / "not stated, ask" / "tolls not fully known".
- **Key-facts strip**: four cells above the rows; the typical figure is the median, with the range small beneath.
- **Host voice**: `host.intro` / `host.line` + `host.catch`, clamped to two lines with "More".
- **Cards**: a neighborhood card is name, rank, one line, up to three facts and the "safest" badge; a place card is
  name, rank, one host line, three facts and one asterisk line. The whole place card is the link; Hold is on the page.
- **"See how we got this"**: every source and method note is a closed link (`howHtml()`), also inside sheets and the
  money box. The footer is one row of links; the gates, counts, build time and sources open under it.

### Collapsed heights at 390 × 844 (under the sticky top line, to the end of the footer)

| Page | Example | px | Screens |
|---|---|---|---|
| Experience | six of six | 1,609 to 1,688 | 1.91 to 2.00 |
| Neighborhood | rich (Stamford) | 1,778 | 2.11 |
| Neighborhood | sparse (Riverdale) | 1,371 | 1.62 |
| Neighborhood | with avoid cards (Jamaica) | 1,573 | 1.86 |
| Neighborhood | with asterisks (Danbury) | 1,660 | 1.97 |
| Neighborhood | tallest of all | 1,814 | 2.15 |
| Place | rich / sparse / asterisk / rent asterisk | 1,285 / 1,167 / 1,183 / 1,240 | 1.38 to 1.52 |
| Place | tallest of all | 1,321 | 1.57 |
| Compare | three places | 1,386 | 1.64 |
| First screen | six cards of 213 to 250 px, then the map | 2,787 | 3.3 |

The walkthrough asserts 2.2 screens (1,857 px) for every experience, neighborhood and place in the data, and for the
compare view of three.

### Removed from the open

- First screen: the gates paragraph, "A snapshot, not a live feed…", the asterisk count box, "6 ways your first 12
  months…", the "Tap an experience" tip, the drawings on the cards, price and drive ranges as the main figure, the
  limits sentence.
- Experience: the drawing, "Typical figures" list, the Safety tile, the two crime lines of the scale, the ranking and
  "first three are shown" sentences, the map note, the "Only warnings" lead.
- Neighborhood: the drawing, the rank's scoring basis, the "Feeling safe" section, car thefts, "typical of the places
  here", the places lead with its price span and dates, the asterisk count box, the "Tap Look inside" tip, the avoid
  lead, the long phone-call and not-re-checked introductions, the notes about how quotes were chosen.
- Place card: the size sentence, parking and move-in line, the why of the asterisk, the three-sentence rent line, the
  disclosure line, both buttons.
- Place: the drawing (now nowhere on the page), "The picture is a drawing…", the hold helper, the generated summary
  paragraph, the crime sentence, crime in "You'll love / Gives us pause", the crime figure on the Night tile.
- Compare: both tips, the "Feeling safe" row, crime in the plain-words trade, the why under each thing to confirm, the
  "finish line" sentence. "Against" is "compared to" everywhere, and pairs are "1 and 2".
- Footer: everything but the lease line (first screen only) and three links.

### Moved behind a tap

- Sources and methods everywhere; the scale's "how to read this"; the range's nearest and farthest neighborhood; the
  mail-rate toll; a neighborhood's scoring basis and its crime figures (under "What's here", then "See how we got
  this"); the map card's crime bars ("More"); the why of an asterisk ("See why"); the basis of each cost line.
- Rows: the day in an experience with the host's walkthrough, promise and catch in full; costs; going out and green
  space; the Queens comparison; good for you / watch for; what's here; what residents say; how others describe it;
  local rules; avoid cards; the phone-call and not-re-checked lists; still to confirm with the disclosures and tour
  questions; the money box and rent terms; the day tiles; the trip; the car; the dog; the building; in compare, the
  parts of the day, "what that feels like" and the Queens table.
- Sheet: the leasing office (phone and hours).

### Where this differs from docs/NAV_PATTERNS.md

- A place has eight rows when something is to confirm (the trip to Mom and Dad and the car are separate), not seven.
- Strip cells do not open sheets, except the count, which jumps to the list. "How we got this" opens in place.
- The place page keeps the price on its sign beside the name; the strip carries size, drive, parking and dogs.
- No sticky jump chips. The shared sheet is the existing one, not a `<dialog>`.
- Rows come before the list on experience and neighborhood pages, as the document draws them.

### Weak

- The crime filter drops whole sentences (clauses in a subhead) that match a word list; a sentence that mixes crime
  with something useful is lost, and wording outside the list would pass.
- The limits sheet still has a Safety slider, and "Outside your limits" can name the crime rate when she sets it.
- Resident quotes inside "What residents say" can mention crime; the row's headline skips the safety theme.
- `rent.offer_text` on some places is pipeline text ("term 12: price 2805, totalPrice…"); it shows in Rent terms.
- "Among the safest" is the lowest fifth by violent rate of neighborhoods with places: 21 of 108.
- Headlines longer than the row are cut with an ellipsis until the row is opened.
- The first-run "How this works" card still opens on the first visit.
- Old screenshots from earlier passes remain in `site/screens/`; this pass wrote `ux-*`, `map-int-*` and the numbered ones.

## UI pass 5: experience and neighborhood pages

(2026-11-16. Will: "go over as a UI/UX designer… especially the experience pages and the neighborhood pages… figure out
ways we can be clearer… better storytelling". Also applies `docs/A11Y_READABILITY_AUDIT.md` and the data-side changes of
the same day. Copy is not written in the template: every sentence on these two pages comes from `data.json`.)

### Story order

**Experience** (`vYear`, wrapper `.pg.pg-exp`): drawing (the *banner* crop, 96 px) → name and tagline → key facts →
"See the N neighborhoods ↓" (with "M places to see" on the button) → About this experience → A day in this experience →
the neighborhoods (List / Map, top three, Show more) → "More about this experience" rows (the promise and the catch;
what it costs you; going out and green space; compared to staying in Queens) → the other-places rows (looked good,
skipped; worth a phone call; not re-checked).

**Neighborhood** (`vHood`, `.pg.pg-hood`): experience marker + rank + experience name → name → where → key facts →
"See the N places ↓" ("in M buildings" on the button) → About <name> → At a glance → one pull quote → the buildings
(top three, Show more) → avoid / phone call / not re-checked rows (they are about places, so they sit under the list)
→ "More about <name>" rows (what residents say; how others describe it; the good and the catch; the area in detail;
local rules; reviews of the buildings; compared to staying in Queens).

### The pieces

- **Key facts** (`kfacts`, `#keyfacts`): three cells, not four. All-in, drive to Mom and Dad, tolls. A median carries a
  small "TYPICAL" tag above it and its range beneath, worded as a range ("from $1,810 to $2,990"). Sums are rounded to
  $10 here (`m10`), tolls to the dollar (`tollMoney`, "under $1" below that), minutes whole; exact figures stay inside
  the rows and sheets. A single-place neighborhood shows its exact price and no tag. The count cell is gone: the counts
  ride on the button under the strip, which is where the old underlined "N places" cell led anyway (audit 7).
  The all-in and toll cells are real buttons with an "i": all-in opens the one-line list of what it includes; tolls
  opens what a round trip costs with a New York E-ZPass, what the tag is, and the by-mail figure.
- **About** (`aboutBox`, `ptBody`, `catchBox`): lead, then the icon points. A point shows a bold lead-in when the data
  gives one (`about_points[].lead`) or when the text is "Lead: rest"; otherwise its first figure is set in bold
  ("about **72 minutes** away") so the list can be scanned. Points with `icon: "warning"` leave the list and go last in
  a butter box labelled "The catch": distinct, no border, no red.
- **A day in this experience** (`storyHtml`, `#sec-day`): three cards side by side in one sideways-scrolling strip
  (80% wide, scroll-snap, the next card peeking in; keyboard-focusable). Each: icon in a ring of the experience colour,
  "1 of 3", title, and when the text opens with a short sentence that sentence as a bold caption. Stacked cards were
  the alternative: at 390 px three stacked moments are about 520 px of prose and read as a text block (that is what
  the old row looked like when opened); the strip is about 250 px and reads as a storyboard. Chosen: the strip.
- **At a glance** (`glance`, `#sec-glance`): two columns of icon facts, always in the same order: restaurants and bars
  on foot; walk to a park; dog park; supermarket; Mom and Dad by train and bus; street parking in three words
  (`parkShort`: "No overnight parking", "Resident permits only", "Street-cleaning days", "Snow-day bans", "Metered
  streets", "N rules on record", "Ask the building"). The parking fact is a button that opens Local rules. Distances
  under a mile are minutes on foot (`distShort`).
- **Pull quote** (`pullPick`, `#pull`): one outside description, with its source link and "about <area>" when the data
  says the quote is about a wider or narrower place. Picked: `described[].featured` if the data sets it, else the first
  of 40 to 150 characters, else the shortest; never one with crime wording. The others stay in "How others describe
  it", and none is shown twice. Resident quotes are not put in the open (they can mention crime); inside their row the
  first quote is set larger, and safety themes are listed after daily-life themes.
- **Rows**: residents' headline is the balance plus the commonest topic ("8 positive, 1 negative · mostly dogs and
  green space"); "Reviews of the buildings" is new on the neighborhood (how many buildings have ratings, each linked);
  "Good for you, watch for" is "The good and the catch"; "What's here" is "The area in detail" (its summary is now At a
  glance); prose headlines are shown whole or replaced by a plain fallback (`wholeHead`), never cut with "…".
- **Cards**: a neighborhood card's price chip reads "typical all-in, from $X to $Y"; a neighborhood with
  `single_building` says "1 building, N apartments"; "Top pick" is withheld (card and page) when that one building still
  has something to confirm.
- **Type and spacing** on these two pages: 14 / 16 / 20 px plus the page title and 13 px caps labels; 26 px between
  sections, no box around a section; the strip's small text went from 10.5 to 14 px.

### Collapsed heights at 390 × 844 (under the sticky top line, to the end of the footer)

| Page | Before this pass | After | "See …" button ends at (page y) |
|---|---|---|---|
| Experience, six of six | 2,150 to 2,357 (2.55 to 2.79 screens) | 2,568 to 2,794 (3.04 to 3.31) | before 508 to 539, after 471 to 502 (0.56 to 0.59 of a screen) |
| Neighborhood, rich (Stamford) | 2,064 (2.45) | 2,677 (3.17) | 293 → 347 |
| Neighborhood, Newark / West Side / Bridgeport / Hackensack | 2,034 to 2,104 | 2,737 to 2,838 (3.24 to 3.36) | about 363 |
| Neighborhood, single building (Brookfield) | 1,558 (1.85) | 2,185 (2.59) | 281 → 331 |
| Neighborhood, nothing to tour (McGinley Square) | 1,273 (1.51) | 1,835 (2.17) | none |

The 2.5-screen aim is **not** met: the day (about 290 px), At a glance (about 200 px) and the pull quote (100 to 190 px)
moved from behind a tap into the open, and small text grew. What did improve is where things are: the way on is inside
0.6 of a screen on all six experiences, and the list starts after About and the story instead of after the rows. The
walkthrough's ceilings are 3.6 screens for both page kinds.

### Elsewhere (the brief's "obvious fixes", the audit, the data changes)

- **Save this place** saves one apartment, the building's best-ranked; the button says which ("Unit 508, the top pick
  of 8 here"), the toast names it, hearts on the rows save the others.
- **Rent terms**: `first_full_payment_note` is never printed raw (`payNote`): "Counting from a Dec 1, 2026 move-in; a
  first part-month is charged by the day." / "Ask when the free month applies." / nothing.
- **Apartment price with an offer**: "$X* a month, with the current offer", and one line "With the current offer; a
  normal month is $Y". "Net-effective" and "cap" are out of the open text ("your $3,000 limit").
- **Compare**: column heads are two lines ("Unit 606" over the building), never ellipsised; the sentence uses the same
  names, not "House 1"; × is 44 px; the best cell says "✓ Best".
- **My list**: facts wrap instead of overlapping; labels 12.5 px; with two or three saved they arrive ticked.
- **Sheets**: the page behind is `inert` while a sheet is open; the limits sheet has the scrim, `aria-modal`, focus on
  its heading, and returns focus on close.
- **Focus and history**: a route change focuses the `h1`; "See the … ↓" moves focus to the list heading; the trail's
  links go `history.back()` when that is where they lead, else replace, so browser Back agrees; `scroll-padding` keeps
  focus out from under the bar. First screen has an `h1`; cards are `h3`; headings and row labels have real spaces.
- **Small text and contrast**: floors raised (nothing under 12.5 px in the open); row and map-control borders #B58CA5;
  unselected map chips no longer faded; map labels darkened; the 31-to-60 drive band is further from its neighbours.
- **320 px**: the map's experience chips are one row that scrolls sideways.
- **Building-level data**: contact, About text and points, ratings and photos are read from `buildings[]` (`bView`),
  a unit's copy is the last resort. A listing site's forwarding number is labelled "Listing-site number (forwards to
  the office)", the button reads "Phone and hours", and the building's own site leads when there is one.
  `scripts/build_site.py` keeps only those fields of `buildings[]`, keeps `local.survey[].source_area` (now read) and
  drops `experience_score_basis` (the scoring sentence is no longer shown).
- **Publish step**: `python3 scripts/build_artifact.py` after `build_site.py`; the walkthrough's "stripped and
  re-wrapped" runs (phone and desktop) cover that shape and pass.

### Not done, and why

- **A one-apartment building does not open its apartment by default** (audit 16): it made the page 4,076 px tall
  collapsed, against the owner's rule that every section starts as a headline.
- **The map is still the List / Map switch**, not a collapsed row: it is a second view of the same list, one tap away.
- **"Only show what differs" is still on by default; the bar still reads "Saved · N"** (audit 26, 21): both are covered
  by existing walkthrough assertions and are the owner's earlier choices.
- **"floor not published", "parking rules not found, ask"** and other ask-phrases (audit 18) are unchanged.
- Compare row titles are still `h4`; the tray is still a `div`; font sizes are still px; fonts are still remote.
- The rent offer is still told in several places inside an open apartment (audit 22); only the wording changed.
- "Places" is still the umbrella word on buttons and counts ("See the 58 places · in 25 buildings").

### Weak

- **About points repeat the strip and At a glance** on most neighborhoods ("Your parents are about 53 minutes away",
  "About 24 restaurants…"): the points are numeric restatements. Nothing is hidden; the fix is in the copy.
- Bold figures in points come from a pattern (`QTY_RE`), not from the writer: a point with no number has no bold.
- The pull quote is chosen by length, so it can be the dullest description (an encyclopedia sentence).
- The story strip hides cards two and three until she swipes; only the peeking edge says there is more.
- At 320 px the strip's cells are tight ("a month, all-in" wraps to two lines).
- Data that would help: `about_points[].lead`; `described[].featured`; `traits.station_m` + station name; names of
  the nearest park and dog park; `day_moments[].caption`; a one-line `headlines.residents_say.headline`; a written
  three-word `local.street_parking_short`; `years[].counts` used for the strip so text and figures share one source.

### Wording fixed in the template after the copy edit (same pass)

- "A park is an 8-minute walk away" (`aWalk` picks "a" or "an"); never "green space a 8-minute walk".
- "A typical apartment is 788 sq ft"; "1 car theft" / "2 car thefts"; "A studio, size not published, floor not
  published." (no double comma).
- The crime lines of the Night moment (rates, incidents nearby) moved inside that moment's closed "See how we got
  this" (`momentBody`); opening the moment no longer shows them.
- The by-mail toll figure is shown nowhere on experience and neighborhood views: the sheet and "See how we got this"
  say only "with a New York E-ZPass" and that an out-of-state tag pays more at MTA crossings.
- A prose headline (`HL.first`) is the first sentence, whole, and wraps; the cut-at-a-comma logic is gone.
- The experience page shows `day_moments`; `scene` / `host.walkthrough` are used only when there are no moments, and
  never both.
- The all-in sheet opens with "A month, everything included."
- Still to align with the copy's vocabulary: "place(s)" on buttons, counts, My list and "Save this place".

## UI pass 6

(2026-11-16. Owner's review of the pass-5 phone screenshots, plus the copy editor's and the pipeline's notes of the same
evening. Files: `site/index.html`, `scripts/build_site.py`, `scripts/site_walkthrough_test.js`.)

### What changed

- **About points no longer repeat the page** (`ptRestates`, `aboutBox(..., mode)`). On a neighborhood a point whose icon
  is one "At a glance" or the key facts already carry (fork, cocktail, coffee, park, dog, train, home, bag; car and clock
  when the drive is shown) and whose text has a number is left out; a point with no number is a description and stays;
  the catch always stays. On an experience a point that gives the monthly cost, the drive or the tolls again is left out.
- **Stale counts** (`staleCount`): a sentence or point in About that gives a number of apartments, buildings or
  neighborhoods other than the one the page counts is left out. Every count shown is taken from the arrays at render
  time (`UNITS`, `BLDGS`, `H.units`, `H.bldgs`, `Y.hoods`); the footer no longer reads `meta.counts`.
- **Pull quote**: only `described[].featured === true` (`pullPick`); none marked, none shown; never chosen by length.
  Type is 17 px: a 35-word quote is six lines at most at 390 px (tested).
- **Vocabulary**: "apartments" and "buildings" everywhere ("See the 23 buildings ↓ / 55 apartments", "Save this
  apartment", "Apartment 508", My list, limits, the map's card and legend). "all-in" is gone from the interface: the key
  facts, the building strip and the cost box say "a month, everything included", cards and rows after that say "a month";
  the first screen says "Prices are for a month, everything included." once. "net-effective", "cap", "gate", "live
  check" are out of the open text (a receipt line "Rent (net-effective)" reads "Rent (with the offer)").
- **Prices in the open are rounded to $10** (`pm`), the way the written text rounds them; the exact figure is in the
  cost box of the apartment.
- **Experience and neighborhood layout**: tighter rhythm; the top-three cards show one sentence clamped to two lines;
  List / Map sits in the heading row of the list; "Show more" is one row; avoid / worth a call moved into the "More
  about…" group (on an experience they are one row, "Not on the list"). The owner then dropped the height limit: the
  walkthrough prints heights and no longer asserts them.
- **Storyboard** (`storyHtml`, `mountStory`): "1 of 3" under the heading, two 44 px arrow buttons, dots, left / right /
  Home / End keys, scroll-snap, the next card peeking; the page itself never scrolls sideways (tested).
- **One-apartment building**: the header carries the apartment's line (`#b-apt`: apartment, bedrooms, sq ft, floor or
  "floor not published", date). The row is not opened by default.
- **The rent offer is said once** on an apartment (`offerLine`): the normal-month figure when the data has it, else the
  written cost subhead when it is about the offer, else "A special offer applies; ask what a normal month costs." The
  full wording is behind "The offer in full". The second rent box, the warning line, the "Needs a call" chip, the
  "special offer" / "net-effective rent" items under Good to know and the duplicate tour question are gone
  (`discsShown`, `oneRentQ`, `noTwins`).
- **Apartment line and catch**: an open apartment starts with its `host.line` (two sentences at most) and its
  `host.catch` as "To ask"; the cost subhead sits under "What it costs". "About the building" shows only the building's
  own text, points and catch.
- **Row subheads** show only when they add an action or a fact the headline lacks (`subAdds`); on building rows only
  when every apartment of the building has the same one (`bSub`).
- **Floor plans / no identifier**: `isPlan`, `hasOwnId`: a floor plan or an apartment without a unit identifier is never
  listed, counted, linked or saved; a neighborhood left with nothing leaves the lists.
- **Small experiences**: tiles are ordered by number of apartments; under five a tile says "Only 2 apartments right
  now" in place of the ranges; no "typical" tag over one item; no "Top pick" among one neighborhood or one building.
- **Building names** are tidied at render time (`cleanName`); an unnamed building's title is its street address.
- **"Not re-checked"** rows and wording are removed (owner decision); `awaiting_live_check` is not read.
- "Before the car sleeps on the street" is "Street parking rules here". The bottom bar is a `nav`; "Open all" no longer
  carries `aria-pressed`. Dead code removed (30 unused functions, among them `unitCard`).

### Left for later

- Audit items not done: 19 (rounding of distances and differences inside rows), 20 (headlines that count), 24 (dates
  without a year), 25 (unknowns in compare), 26 ("Only show what differs" default), 28 (pipeline words behind "See how
  we got this"), 32 (scroll position on reload), 33 (rem font sizes), 36 (remote fonts); the bar still reads "Saved · N".
- The key-facts label "a month, everything included" wraps to three lines in its cell at 390 px.
- A card's sentence can be cut by the two-line clamp.
- `staleCount` drops a whole sentence when its count is stale; the copy should be regenerated after each cut instead.
- Stored medians and ranges (`years[].medians`, `all_in_range`) are still read for the experience strip and tiles; only
  counts are recomputed.
- The map's own chips keep the data's order of experiences, not the first screen's order by size.

## UI pass 7: tutorial

(2026-11-16. Owner: "restore the tutorial at the front of it, and make it descriptive enough that it makes sense."
Files: `site/index.html`, `scripts/site_walkthrough_test.js`, `site/screens/p7-tutorial-*.png`.)

- **What it is.** A six-step card, "How this works" (`#tut`, `TUT`, `openTut` / `closeTut` / `tutStep` / `tutDraw`), in
  the old first-run card's style: white card, ink border, berry shadow, the dog, dots. Each step has a drawing, "2 of 6",
  a title and one or two sentences (28 words at most). The steps: the six experiences; experience → neighborhood →
  building → apartment, with "Show more" and List / Map; the three numbers at the top of a page and the range beneath;
  rows open when tapped, and "See how we got this"; the star (*) and "Still to confirm"; Save, My list, Compare and
  "See photos".
- **Words and samples.** The sentences are written in the template (the one place the page explains itself). Nothing in
  them is a count of apartments; "six" is `YEARS.length` in words. The drawings are copies of the page's own parts
  filled from the data when the step is drawn: the experiences' markers and names, the first experience's key facts
  (`kfacts`, with the buttons turned into plain boxes), two of its row headlines, the first apartment with one thing to
  confirm and its question, and the bottom bar with the real saved count. They are `aria-hidden` and hold no control.
- **When it opens.** By itself once, on a first visit that lands on the first screen; never on a link to an experience,
  neighborhood, building or the list (and not later in that visit). Closing it any way (Skip, Done, Escape, a tap
  outside) stores `lamia-house-hunt-v1-tutorial = 1`. When storage throws it shows on each load and still closes at once.
  "How this works" under the title (`#how-top`) and in the footer reopen it from step 1; the three-line sheet is gone.
- **Controls.** Skip on every step; Back / Next, Done on the last; left / right arrows, Escape; a swipe left or right on
  the card (44 px or more, mostly sideways). Focus goes to Next on opening and back to where it was (the page's h1 on a
  first visit) on closing. The page behind is inert through the sheet's own `hold()`. The card's entrance animation is
  off with reduced motion (the page's global rule).
- **Layout.** A centered card, 552 px tall at 390×844 and 566 px at 320×640, the same height on every step so the
  buttons do not move; no scrolling inside it at either size. One h2 (the title); the step is an `aria-live="polite"`
  region; text is 14 px or more; buttons are 44 px or more.
- **Tests** (`tutorialTests()` in the walk-through, at every width, in fresh browser contexts): first visit opens it over
  the first screen; every step is measured (words, sizes, contrast, fit, drawing) and photographed at 390; Back, Done,
  no reopening on reload; the top button and the footer link; Skip; arrows and Escape; a tap outside; swipes; links to
  inner pages; storage that throws; reduced motion; no console errors. The main walk-through seeds the stored flag; the
  built-page runs dismiss the tutorial with Skip first.
- **Also changed in the test:** the ceiling for an experience tile's height at 390 px is 336 px, not 320: one tile is
  324 px with the current data, with the committed template as well.
- **Left as is:** the star on a price is the rent offer, a different mark from "* To confirm"; the tutorial describes
  only the second, in the footer's words. At 320 px the key-facts sample breaks "E-ZPass" over two lines, as the page does.

## UI pass 8: rent versus total, filters

(2026-11-16. Owner: "point out what the base rent is versus the base rent plus the estimated utilities … everywhere" and
"we used to have filters … restore them". The same pass took in the template items of independent check 4 and of
`docs/REPAIRS_AFTER_INDEPENDENT_CHECK_4.md`. Files: `site/index.html`, `scripts/build_site.py`,
`scripts/site_walkthrough_test.js`, `site/screens/p8-*.png`.)

### The two prices

- **Names, defined once** (`L_RENT`, `L_TOTAL`, `S_RENT`, `S_TOTAL`, `WITH_UF`, `PRICE_SENT`): "Rent" and "Total with
  utilities and fees"; short forms "rent" and "total"; the phrase "with utilities and fees"; and the one sentence "Rent
  is what the listing asks. The total adds fees, parking, pet rent and our estimate of electricity, gas and internet."
  "Everything included" and "a month" on a bare figure are gone from the template (data prose still says "everything
  included" in some About text and apartment lines).
- **Rent** is `rentOf(U)`: the amount of the rent line of `all_in_lines` (so the breakdown always starts with the figure
  shown), else `rent.basis`, else `rent.listed`. It is exact to the dollar wherever it is one apartment's rent (rows,
  building cards, the building header, My list, compare). **Total** is `all_in`, said with "about" and rounded to $10
  outside the breakdown, exact in it. Typical (median) rents and totals are to $10. The filters' "total", the budget and
  the ranking still use `all_in`.
- **Which rent** (`rentKind`, `rentTerm`, `rentNotes`), read from the rent line's name: "on a 12-month lease" when the
  page uses the 12-month price (with "The listing shows $X for a 24-month lease." beneath), "with the current offer"
  after an offer, "on a 15-month lease" when the listing's price is for another length, nothing otherwise. Where a lease
  disclosure says the 12-month price in the building can be much higher, that sentence sits under the rent on the row.
- **The pair** (`pp`, `ppUnit`, `ppTyp`, `ppFew`, `pairLine`): rent first and larger, the total beside it with "about"
  and "with utilities and fees". Where it is used: first-screen tiles; the key facts of an experience and a neighborhood
  (`kfacts`, now four cells in two rows: rent, total, drive, tolls; four in a row from 700 px); neighborhood cards;
  building cards and the building header ("Rent from", with a line saying both figures are one apartment's, the one
  with the lowest total: `bFromU`); apartment rows; the "What it costs" headline and breakdown; My list; compare (two
  rows, both in "only show what differs"; the column heads carry the rent, named); the map card; avoid cards and "worth
  a call" items; the tour list text; the tutorial step; the "What it costs you" row; the sheet behind the total.
- **Breakdown** (`receipt`): each line is marked "estimate" or "not published" as its basis says; a cost that is not
  published is never $0; the total line is named; "The total could pass $3,000 once … are known" (`couldPass`) sits
  under it and on the row. The offer star is on the rent, never on the total.
- **Medians** (`figsOf`, `yearNums`): the typical rent and total, their ranges, the drive and tolls of an experience are
  worked out from the apartments shown (those that pass the filters); stored medians are no longer read for them.
- **Under eight apartments** (`FEW = 8`) an experience has no "typical" figure: tile and strip give the lowest and the
  highest, and say how few there are.

### Filters

- **One sheet** (`#limsheet`, built by `buildFilterSheet`), opened by a "Filter" button (`fBtn`) on the first screen
  (beside "Pick an experience"), on every experience and neighborhood page (beside "See the N …" and again at the list),
  at "Apartments here" on a building, beside Sort on My list, and from the footer. Same dialog behaviour as before: page
  behind inert, focus in and back, Escape, scrim.
- **What can be filtered:** rent at most ($50 steps); total with utilities and fees at most (to the $3,000 limit);
  bedrooms; size at least (an unpublished size stays in unless "Hide when the size is not published" is ticked); drive
  to Mom and Dad at most; move-in (available now / by the 1st of the last month; a choice that would hide nothing or
  everything is not offered); parking (at the building / garage or covered); washer and dryer in the apartment; nothing
  left to confirm; reviews online; experience (on the first screen and My list). Every range comes from the data (`RNG`,
  `MOVE_OPTS`). **Dropped:** dog weight limit (no number published for 412 of 523 apartments; every apartment shown
  already takes her dog) and the Safety slider (owner's earlier decision).
- **How it applies** (`applyF`, `fits`, `shown`, `yHoods`, `hBldgs`): each apartment's filter fields are worked out once
  (`U._f`). While a slider moves only the sheet changes (its words and the live count, `role="status"`); the page is drawn
  again once, when the control is let go. Lists, counts, cards, strips, the map and Next links then show only what
  passes; a building shows when one of its apartments passes, with the count and "from" figures of those; a strip says
  "Typical figures are of the N of M apartments that match your filters"; a neighborhood or experience with nothing left
  keeps its page and says "Nothing here matches your filters" with "Clear filters"; hidden neighborhoods, buildings and
  apartments are counted in one line ("3 more apartments here do not match your filters. Show them"). An apartment
  opened by its own link is always shown.
- **The bar** (`#fbar`, `renderFbar`): pinned under the top line whenever a filter is on: "N of M", one removable chip
  per filter, "Clear all". `--top-h` keeps sticky things and jumps clear of it.
- **My list** is not filtered unless "Also apply these filters to My list" is on; a saved apartment outside the filters
  says why. Compare is never filtered.
- **Storage:** `f` in `lamia-house-hunt-v1` (try/catch; works for the visit without it); the old `lim` is read as
  filters once. Nothing goes in the address.

### From the independent check and the repairs note

- A fact that is the open question is not stated (`openFact`): "elevator not confirmed" in the building row and facts,
  "dog policy not confirmed, ask" in the dog row, "Ask" for dogs in the header, "availability to confirm" on the row.
- Avoid-only neighborhoods (`neighborhoods_avoid_only`, or any neighborhood left with no apartment) have no page, no map
  mark and no count; their avoid cards are under "Looked good, skipped".
- Only reader-facing text is printed: `label`, `why`, `question`; never `why_internal` / `note_internal` (also left out
  of the built page), and never a string naming our files or steps (`pub`, `ruleText`).
- `safety.status = "not_published"`: the note behind "See how we got this", no badge. Doorman / concierge desk / front
  desk (`deskOf`). `free_text` for offers. `pause_points` / `avoid_points`. "at least N floors". `manager_name`.
- "At a glance" prints `at_a_glance` (text, then label), then the train-and-bus time and the street-parking rule; cards
  and headlines take restaurants and the park walk from it (`glv`).
- "Compared to a typical Queens apartment" where the neighborhood is in Queens (`qWord`).
- Sentences: "A one-bedroom", "Garage parking; the fee is not published.", "No woods within a 10-minute walk."; the
  tutorial's first card no longer says every apartment fits; a seventh card names the Filter button.

### Tests added (`scripts/site_walkthrough_test.js`, at 390, 320 and 1280)

Both prices on tiles, strips, neighborhood and building cards, the building header, apartment rows, My list, compare
and the map card, each named, rent first and larger, "with utilities and fees" in two lines at most, nothing under
12.5 px; every apartment's breakdown adds up to its total, lines marked as the data marks them, no $0 for a cost not
published; the rent's basis and its notes; the filter sheet (labels, 44 px, live region, no re-render while a slider
moves, keyboard); each filter alone against the test's own reading of the data; counts on the first screen, an
experience, a neighborhood, a building with only some apartments passing; the empty state; chips and "Clear all";
persistence across pages and a reload; the old limits carried over; My list untouched by default; storage that throws;
no sideways scroll; the check-4 items above.

### Left

- Data prose still says "everything included" / "all-in" in places (About text, apartment lines); that is the text
  agent's.
- The compare column heads still break "Apartment" mid-word at three columns on a phone (as before this pass).
- `check_published_text.py --template` still lists one line: the constant that holds "staying in Queens" (used only
  for places outside Queens).
- The first-screen tiles are about 60 px taller (two prices): 360 to 395 px at 390.

## UI pass 9: fixes after independent check 5

(2026-11-16. Template side of `docs/INDEPENDENT_CHECK_5.md` (N1 to N29, the D items re-tested there) and of "What the page
agent must do" in `docs/REPAIRS_AFTER_INDEPENDENT_CHECK_5.md`. Files: `site/index.html`, `scripts/build_site.py`,
`scripts/site_walkthrough_test.js`, `site/screens/p9-*.png`.)

### One star, one meaning (N2)

- **The star (\*) means only "one thing to confirm before you sign"**: an open gate fact (`confirm.asterisk`: elevator,
  dogs, listing, availability, eligibility). `nToConfirm(U)` and `HL.confirm` count `confs(U)` and nothing else. The line
  at the top of a building ("See the 8 apartments · 1 with something to confirm"), the star on a building card (only when
  every apartment there has an open item), the star on an apartment row, "N\* to confirm" in My list, the sort "Fewest
  things to confirm", the compare row and the filter "Nothing left to confirm · no star (\*)" all use that count.
- **A rent with a special offer carries a small "offer" tag** (`offerTag`, class `otag`: a blue-grey outlined pill beside
  the rent figure, never a star). It appears wherever the rent does: building header and cards, apartment rows, My list,
  compare (head and cell), avoid cards, "worth a call". In running text the rent reads "Rent $1,650 (offer)". A rent
  already worded "with the current offer" (a price after free months) has no second mark. The line under a card or a
  row that says what the offer means starts "Offer:" (`.offl`), not "\*".
- A price for a lease that is not 12 months keeps its words beside the rent ("on a 15-month lease"), as before.
- Compare: the row is "\* Still to confirm" only when one of the apartments has an open item; with only things to ask it
  is "Good to know before you call", with no star, and a cell reads "Nothing to confirm".
- The tutorial's fifth card says both: "A star (\*) means one thing is still to confirm before you sign. … An offer tag
  just means a special offer.", and its drawing shows a real rent with the tag. The footer says the same; the data note
  "An asterisk on the rent means a special offer applies" is no longer printed (`renderFoot`).
- Screenshots: `p9-390-62-city-trust-star-and-offer.png`, `p9-390-63-city-trust-apartments.png` (and the `1280` pair),
  `p9-390-02-tutorial-star-and-offer.png`, `p9-390-40-my-list.png`, `p9-390-42-compare-three.png`.

### Lease wording (N7)

- Two lease lengths are kept apart: the lease the listed price is quoted for (`cost_check.lease_term_months`, or
  `rent.price_lease_months` if the data ever sends it: `leaseMonths`) and the lease an offer asks for
  (`rent.lease_months`: `offerLeaseMonths`, shown only in "The offer in full"). The words beside a rent read the first.
- Which price the rent is comes from the rent line's `code` (`rent_12_month`, `rent_net_effective`, `rent_listed`); the
  line's name is read only when there is no code. Nothing is worked out by arithmetic.
- Where the data gives no lease for the price (an offer "on an 18-month lease" and nothing about the price), the rent
  carries no lease words; the offer's own words are in "The offer in full".

### Parking (N1, D18)

- `parkInfo(U)` reads `parking.kind` (the space she would use), `kind_words`, `included_kind`, `optional_kinds[]`
  (`kind`, `fee`), `fee_kind`, `kinds` and `summary`. The rank and the stored type string never name a kind.
- The sentence (car row, "Night", "Coming home") is `parking.summary` as the data words it. Without a summary it is built
  from the fields: "Free open lot; garage spaces are extra, price not published", "Garage, $150 a month", "Open lot,
  included", "Street parking only", "Parking not published, ask". With only the old fields (`kinds`, `fee`,
  `garage_is_optional_extra`, `fee_note`) the same builder runs; "garage" needs a garage among the kinds.
- Chip, card, compare cell: the short word of `parking.kind` (`PK_SHORT`: Garage, Covered, Open lot, Off-street, Assigned
  space, Off-site, Street, Parking unclear) and "included" / "$100 a month" / "price: ask", plus "; garage extra".
- The night rating, the compare order and the filters use the kind she would use (`parkRank`). "Garage or covered" keeps
  an apartment whose `parking.kind` is a garage, a gated lot or covered; "Parking at the building" leaves out the street
  and an off-site deck.
- "The listing says: …" prints `parking.type` without our own "kind:" head, and not at all when it reads like a note of ours.

### The other items

| Item | What changed |
|---|---|
| N10 | "Available now" is a listing that says so or one dated on or before the day the data was built (`AS_OF` from `meta.as_of` or the date of `meta.built_at`; `availNow`). Filter, row, My list, sort and the building facts use it |
| N12 | The Queens scale said "All in" because the label map was built before the name existed. `mLabel` now returns "Total with utilities and fees". No "all in" label is left in the template |
| N3 | "At a glance": an item that names its kind is printed as sent; otherwise the nearest station comes from `shown_figures.train_station_kind` / `train_station` / `train_station_m` ("8 min walk · to PATH (Journal Square) from most buildings here"); with neither, the words are "a commuter train station". Building rows: "PATH (Journal Square) is a 2-minute walk away." (`SAY.train`) |
| N17 | `nOf()` and `agree()`: "1 of the 4 buildings here has its own dog area". Used for the template's own count sentences and applied to at-a-glance labels |
| N19 | Evidence: a record (`kind: "record"`) is printed as our sentence ("On record: 23 elevator complaints …"), without quotation marks, with `window_words`; a raw figure ("per 100 units", "percentile") is never printed (only the link stays). "Why to avoid it" prints `avoid_points` only, never `avoid_reasons`; "Gives us pause" prints `pause_points` only. A quote dated to a month reads "Oct 2026" |
| N4, N6, one-time costs | They arrive as disclosures and are listed under "Good to know before you call" like the others. A washer and dryer known only from a listing site's feature list (`in_unit_laundry_basis`) read "washer-dryer listed, to confirm"; a washer with no dryer named reads "washer in the apartment". The filter "A washer and dryer in the apartment" needs both and says how many rest on a listing site |
| Toll range | `toll_round_trip_range` sits small beneath a neighborhood's toll; an experience shows the range of its apartments |
| N14 | A floor read from the apartment number is "likely floor 7" on the row and "likely on floor 7 (read from the apartment number)" in the sentence |
| N18 | "(see Connecticut statewide row)" is cut from a rule's text |
| N20 | A question followed by a short remark is the same question: it is listed once |
| N21 | Compare, three columns on a phone: "Apartment" sits whole on its own line above the number; names wrap at spaces |
| N22 | "A lease is usually a year. Where a rent is for a longer or shorter lease, it says so." (first screen, tour list) |
| N23 | A rating read on another site names the review site in plain text and links "as shown on apartmenthomeliving.com" |
| D25 | "none on record for this town: ask the building" in place of "not found, ask" |
| D27 | Prose sentences with "safest" are left out of the open text: the badge "Among the safest on the list" says it once |
| D28 | A card's sentence is shown whole (up to six lines) and no longer cut after two |
| Tolls | A crossing used both ways is listed once: "Bronx-Whitestone Bridge (both ways)" |

`scripts/build_site.py`: `parking.fee_note` is kept (read by the fallback); `evidence.items[].excerpt_internal`,
`parking.included_words_internal`, `parking.kinds_basis`, `parking.included_basis` and `parking.reviewed_note` are left out
of the built page; `HOUSE_HUNT_SITE_DIR` builds from a frozen copy of `site/` (used while the pipeline rewrote `data.json`).

### Tests added (`scripts/site_walkthrough_test.js`, at 390, 320 and 1280)

All 202 building pages: the header count, each row's star, "To confirm" line, "Still to confirm" box and offer tag against
`confirm.asterisk` and the rent fields; no star on any price; "likely floor"; "available now" against the build date;
"Garage" in the header only when `parking.kind` is a garage; the car row equals `parking.summary`; the Queens scale names
the total. All 83 neighborhood and experience pages: building-card stars and offer lines, at-a-glance grammar and station,
avoid cards and records, toll ranges, the footer. Lease wording on every apartment against `code` and
`cost_check.lease_term_months`, and the four apartments of N7. The filters "Nothing left to confirm", "Available now",
"Garage or covered" and "washer and dryer" against the test's own reading. My list and compare counts. Parking sentences
for the new and the old field shapes; toll range, station wording, agreement, laundry basis; no question twice in any
tour list.

### Left

- Text that comes from the data and still reads wrong is the text agent's: N9 (Newark tolls), N15, N16, N27, the "Car
  crime: …" sentences in `avoid_points` (N13), and the two lines `check_published_text.py` lists.
- The `train_station` item of `at_a_glance` had no kind when this pass ended; the page fills it from `shown_figures`.
- `pause_points` about a safety incident or car crime sit in "Gives us pause", inside the closed row "Compared to …".
- "What that feels like" in compare still multiplies a monthly difference by 12 whatever the lease length.
- N24, N25, N26, N28, N29, D29 are data.
