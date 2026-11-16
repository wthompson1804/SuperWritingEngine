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
