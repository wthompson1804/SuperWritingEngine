# Accessibility, readability and flow audit of the page

Audited 2026-11-16 on a frozen build: `python3 scripts/page_data_extras.py && python3 scripts/build_site.py` run once
(513 places, 231 buildings, 103 neighborhoods, 6 experiences; data built 2026-11-16T01:40:59Z), then
`site/dist/index.html` copied aside and driven with Playwright (Chromium) at 390×844 (primary), 320×640 and 1280×900,
plus 640×450 (the 1280 window at 200% zoom). The template was being rewritten during the audit, so re-check each item
against the current `site/index.html` before fixing; selectors are from the frozen build.

Screenshots are in `site/screens/audit_<width>_<view>.png`. In full-page shots the fixed "Saved" bar is painted in the
middle of the image; that is the capture, not the page.

**Counts: 7 blockers, 21 should fix, 11 polish.**

## What already passes (do not spend time here)

- `lang="en"`; the viewport meta allows pinch zoom; no horizontal scroll at 320, 390, 640 or 1280.
- Every one of the visible controls has an accessible name (0 unnamed across 18 view states), including map marks
  ("Hempstead, NY. The Old-Neighborhood Experience. 1 place. 23 minutes…"), hearts ("Save Avalon Princeton on Harrison,
  unit 431"), list checkboxes ("Compare …, unit 606"), list × ("Take … off my list"), zoom +/−.
- Focus ring: 3 px solid #3A1630 on every stop tested (14.6:1 on the page background; butter #FFD86B on the dark bar, 11.4:1).
- Collapsible rows are native `details/summary`; Enter opens them. Save buttons carry `aria-pressed`. List/Map and the
  map's colour switch are `role="group"` with `aria-pressed`. Sort is a labelled `<select>`.
- Map by keyboard: one mark in the tab order, arrow keys move between marks, Enter opens the card and moves focus to
  "See places", Escape returns focus to the mark.
- Body, muted, chip and link text all clear 4.5:1 (table below); the Strong / Mixed / Weak chips carry the word, and
  experience marks differ by shape as well as colour.
- `prefers-reduced-motion: reduce`: 0 running animations, `scroll-behavior:auto`.
- Browser Back restores the scroll position (left a neighborhood at y=1200, came back to y=1200).
- Crime in the open: across 30 collapsed views the only wording found is "Among the safest on the list". The limits
  sheet has no safety slider in this build. Rates sit two taps down ("What's here" then "See how we got this").
- No `net-effective`, `verdict`, `disclosure`, `basis`, `live check`, `PLUTO`, `hood`, "year" for an experience, raw ISO
  dates or `null`/`undefined` in the open (collapsed) text. They do appear behind taps: see items 26 to 28.

---

## Blockers

### 1. Numbers on the same screen contradict each other
The written "About" text and the figures above it are computed from different sets, and the reader sees both at once.

| Where | Figure strip / card says | Text right under it says |
|---|---|---|
| `#exp-middle` | 224 places · 27 neighborhoods · $2,719 | "143 places across 28 small cities and inner suburbs." · "All-in runs about $2,700 a month." |
| `#exp-enclave` | 10 places · $2,930 · 72 min | "Choice is thin, with only 9 places." · "About $2,900 a month all in." |
| `#exp-settled` | 26 min typical drive | "The typical place is about 24 minutes from your parents." |
| `#hood-ct-stamford` | 58 places; card "from $2,695*" | "this ranks first of the 38 places here … at about $2,715 a month all in" |
| `#bldg-ct-beacon-falls-b-8cb8bf6346` | "$2,044* from, all-in" | "It runs about $1,994 a month all in" |
| `#hood-nj-princeton` | "$38.91 tolls" | "Tolls run about $39 round trip" |

Evidence: `audit_390_02_experience.png`, `audit_390_03_neighborhood.png`, `audit_390_building_top_viewport.png`.
Fix: never bake a count or a dollar figure into stored prose. Either fill them at render time from the same variables
the strip uses (`{n_places}`, `{median_all_in}`), or strip any sentence whose number differs from the strip's by more
than rounding (a check in `build_site.py`: for each prose number that names places / all-in / minutes, assert it equals
the strip value, else drop the sentence and log it).

### 2. Compare cannot tell two apartments in one building apart
`.cmp-head .colh a b` shows the building name only, at 12.5 px, `white-space:nowrap; text-overflow:ellipsis`. With
three columns at 390 px it renders "City…", "City…", "City…" (66 px wide link); the full name is nowhere on the view and
the unit number is never shown. The sentence above says "House 2 costs $264 less a month than House 1".
Evidence: `audit_390_06b_compare_three.png`, `audit_390_compare_three_distinct.png`.
Fix: header = two lines, no ellipsis: `<b>Unit 606</b><small>City Trust Apartments</small>` with
`white-space:normal; overflow-wrap:anywhere` and `-webkit-line-clamp:2` on the small line only. Replace "House 1 / House
2" with the same labels ("Unit 511 costs $264 less a month than Unit 606", or the building name when they differ).

### 3. "Save this place · 8 apartments" saves eight things
`button.savb` on a building page pushes every apartment into My list: one tap on City Trust Apartments took the bar
from 0 to 8 and the toast read "Saved. 11 places in My list, below." after three buildings. My list then shows eight
near-identical rows she never chose (`audit_390_05b_list_saved.png`), each needing its own × (8 taps to undo from the
list). The label says "place" (singular) and the count says "apartments".
Fix: either save the building as one row ("City Trust Apartments · 8 apartments, from $1,703") that expands, or keep
per-apartment saving only (hearts) and make the big button "Save the cheapest apartment here" / remove it. Whichever is
chosen, the toast must say what happened: "Saved 8 apartments at City Trust."

### 4. The price in an apartment's headline is not what she pays, and the truth is one line of jargon
`details.aptd > summary` for Avalon Princeton Unit 431 reads "$2,919* all-in". Opened, the first sentence is "A paying
month costs $3,153 all-in, over the $3,000 cap." and the receipt's first line is "Rent (net-effective) $2,571". The
same offer is then explained four more times (item 22). A consumer reads $2,919, the cheque is $3,153.
Evidence: `audit_390_apt_open_viewport.png`.
Fix (wording only; the rule that these stay on the page is Will's): headline "$3,153 a month · $2,919 averaged over the
lease with 1 month free". Receipt line "Rent, averaged with the free month". Never the words "net-effective" or "cap".

### 5. My list's fact row overlaps itself
`.lfacts` is five fixed columns (50 px each at 390, 36 px at 320). Values overflow into their neighbours: "109 min740"
at 390 px; at 320 px "$2,044" runs through "109 min" which runs through "740" (`audit_320_list_viewport.png`,
`audit_390_05c_list_two_ticked.png`). Labels are 10.5 px and wrap to four lines ("to / Mom / and / Dad").
Fix: `.lfacts{display:flex;flex-wrap:wrap;gap:4px 14px}` with `.lfacts span{flex:0 0 auto;white-space:nowrap}`,
labels 12.5 px, and shorten the label to "min drive".

### 6. Sheets are announced as modal but do not hold focus; the limits sheet is worse
- `#sheet` has `role="dialog" aria-modal="true"`, focus moves to `#shClose` and Escape returns it to the opener (good).
  But the next Tab leaves the sheet: measured stops after `#shClose` were `body`, then six `a.life` cards behind the
  sheet, `#see-map`, the map controls. Background is not `inert`, body still scrolls.
- `#limsheet` has `role="dialog"` with no `aria-modal` and no scrim. Focus lands on `#lim-cost`, skipping the "Done"
  button before it; four Tabs later focus is behind the sheet; Escape closes it and leaves focus wherever it wandered
  (measured: `#see-map`), not on "My limits".
Fix: in `openSheet`/`openLimits` set `view.inert=foot.inert=tray.inert=trail.inert=true` (clear on close); add
`aria-modal="true"` and the scrim to `#limsheet`; store `lastFocus` in `openLimits` and restore it in the close path;
focus the sheet's `h2` (`tabindex="-1"`) or "Done" first. Better: use `<dialog>.showModal()` for both and delete the
hand-rolled code.

### 7. The "224 places" figure is a fake button that the keyboard cannot press
`.kstrip > div[role="button"][tabindex="0"]` listens for `click` only. Measured: Enter does nothing (scrollY 0 → 0);
Space scrolls the page by a screenful (0 → 738) instead of activating. Tap works (→ 1238). It is also underlined like a
link, says "places", and lands on the list of neighborhoods.
Fix: render it as `<button type="button" class="kcell" data-act="scrollto" …>`; label it "27 neighborhoods" on the
experience page, or drop the affordance since "See the 27 neighborhoods ↓" sits directly below it.

---

## Should fix

### 8. Focused controls disappear under the fixed "Saved" bar
Tabbing through `#exp-middle` at 390×844: `.viewsw button` focused with 39 of its 44 px under `#tray`;
`#r-warn > summary` 46 of 46 px hidden; `a.hood.card` 54 px hidden. (WCAG 2.4.11.)
Fix: `html{scroll-padding-bottom:calc(var(--tray-h,54px) + 16px);scroll-padding-top:76px}`.

### 9. Heading outline
| View | Outline found | Problem |
|---|---|---|
| First screen | h2 "Pick an experience" → h3 ×6 → h2 "The whole map" | No h1: the title is `div.logo[role=img]` |
| Experience | h1 → h2 → h2 → h4 (cards) | h3 skipped |
| Neighborhood | h1 → h2 → h2 → h4 (cards) | h3 skipped |
| Building, apartment open | h1 → h2 → h2 → h4 "What it costs", "* Rent terms"… | h3 skipped |
| My list | h1 → h3 "Go see them" | h2 skipped |
| Compare | h1 → h4 "Monthly, all-in"… | h2, h3 skipped |

Also, headings built from adjacent spans have no space in the DOM text: "Pickan experience", "Thewhole map",
"58 placesin 25 buildings", "Apartments here8", and row labels "For the dogAsk the limit", "Local rulesAsk",
"The eveningWeak". A screen reader says "Pickan".
Fix: wrap the logo in `<h1 class="logo">` (keep the visual; drop `role="img"`); cards and inner sections become h3;
My list "Go see them" h2; compare row titles h2. Put a real space (or `<span class="sr"> </span>`) between the spans.

### 10. A route change puts focus on `<main>`, not the heading
After every navigation `document.activeElement` is `main#view` (`tabindex="-1"`, `outline:none`), whose accessible
content is the whole page. `document.title` does change ("The Little-City Experience · Lamia's House Hunt").
Fix: `var h=view.querySelector("h1");if(h){h.tabIndex=-1;h.focus({preventScroll:true})}` in `go()`.
Same for in-page jumps: after "See the 27 neighborhoods ↓" the page scrolls but focus stays on the button, now at
y = −776; move focus to the target section's heading in the `scrollto` handler.

### 11. The page's Back and the browser's Back disagree
`#trail a.bk` is a plain link, so it pushes a history entry. Measured: experience → neighborhood → building; page Back
(→ neighborhood, history length 5 → 6); browser Back → the building again; browser Back again → neighborhood. On a
phone the system back gesture bounces her forward.
Fix: in the click handler, when the link is `.bk` (or a trail crumb) and the previous history entry is that route, call
`history.back()`; otherwise `location.replace("#"+route)`. Keep a small stack of visited routes in `go()` to know.

### 12. Text under 14 px (390 px viewport)
| Size | Where (selector) | Example |
|---|---|---|
| 10.5 | `.kstrip small.rng` | "$1,806 to $2,998" |
| 10.5 | `.lfacts span` (labels), `.lfacts .warn` | "all-in", "to confirm" |
| 11 | `.hood.card .chip small`, `.cardl .chip small` | "to Mom and Dad", "sq ft" |
| 11 | `.hhm-chip small`; map labels `.hhm-lab.state/.water` | "7"; "Connecticut" |
| 11 | `em.lvl` (Strong / Mixed / Weak chips) | "Weak" |
| 11.5 | `summary .rl` (every row's caps label), `em.st.ask` | "WHAT IT COSTS YOU", "Ask" |
| 11.5 | `.kstrip span`, `.life .rng`, `.aptd .ap small`, `#see-photos small` | "typical, all-in" |
| 12 | `.ylist .cell small`, compare `.cell small`, `.savb small`, `#lstrip span` | "Much better · −$664", "seen Nov 15" |
| 12.09 | `.hhm-short` | "Quiet-Street" |
| 12.5 | `.life .figs span`, `#hood-rank`, `.lmain small`, `.colh a b`, `.rent-terms dd small` | "typical all-in" |
| 13 | `.hd small`, `.pick`, `.nextl small`, `.heartb span`, `.receipt .fn`, `.rent-terms dt`, map legend and hint | "CT · 58 places · 1 to avoid" |
| 13.5 | `.rs` (row subheads), `.am`, `.ac`, `.confl`, footer links, "Open all" | "* To confirm: the elevator" |

Fix: one floor. Nothing under 13 px; anything she must read to decide (range beneath a median, "to confirm", row
subheads, apartment meta, the asterisk line) at 14 px; caps labels 12.5 px. In CSS: raise `.rng` to 13, `.lfacts span`
12.5, `.chip small` 12.5, `.rl` 12.5, `.rs/.am/.ac/.confl` 14, `em.lvl` 12.5.

### 13. Contrast failures (full table below)
- `.life small.rng` (the range beneath the median): #7A5670 at `opacity:.85` → #8E6F85 on white, **4.39:1** at 11.5 px.
  Drop the opacity.
- Map chips when one experience is selected: `.hhm-chips.has-on .hhm-chip[aria-pressed=false]{opacity:.62}` → count
  **2.73:1**, name 4.61:1. These are still live buttons. Use `opacity:1` and a lighter border instead, or ≥ .8.
- Map labels: `.hhm-lab.state` #A58E9B on water #D7E4EA **2.33:1**; `.hhm-lab.water` #5B7C8C **3.44:1**, both 11 px.
  Darken to #6B5562 and #3F5F6E.
- Row and chip borders: #F3CADA on white **1.47:1**, on the page background **1.37:1**. This is the only edge of
  `details.rowd`, `.hhm-chip`, the "Zoom to" buttons and the disabled Compare button. Use #B58CA5 (3.2:1) for controls.
- `.hhm-zoom button[disabled]` at `opacity:.4`: **2.44:1** (disabled, exempt; still looks broken beside the live one).

### 14. Things said by colour alone
- Compare: the best cell in a row is `.cell.edge` (mint fill and border) and nothing else. In
  `audit_390_06b_compare_three.png` "$1,703*" is green twice and "751 sq ft" once with no word or mark.
  Fix: `.cell.edge::before{content:"Best";…}` or a ✓ with `<span class="sr">best of these</span>`.
- Map, "Colour by drive time": four pinks from #FBE3EC to #5E1740. Adjacent bands differ by 1.72, 2.37 and 2.54:1 and
  the palest is 1.17:1 against the land; only the ink outline holds it. The minutes are in the mark's name and card, so
  this is not a blocker. Fix: print the band on the selected card ("31 to 60 min") and widen the steps
  (#FBE3EC, #F2A7C3, #C12C62, #3A1630).
- Experience marks pass on shape + colour; three of the six colours are only just over 3:1 on white (#AA8B0E 3.28,
  #4192C8 3.40, #F04288 3.60). Leave, or darken the yellow to #8A7000.

### 15. Touch targets under 44 × 44 (measured, 390 px)
| Control | Size | Fix |
|---|---|---|
| My list name link `.lmain a` | 266 × 24 | `display:block;padding:10px 0` (make the whole `.lmain` the link) |
| My list × `.lx` | 40 × 44, touching the name link (0 px gap) | `width:44px` |
| Compare × `.colh .x` | 32 × 44 | 44 wide, or move removal to My list |
| Compare header link `.colh a` | 66 × 26 (three columns), 127 × 26 (two) | `min-height:44px` |
| Map marks `.hhm-dot` | 7.4 to 26 px drawn; 114 marks, many overlapping over NYC | the code's 22 px tap radius helps; keep "Zoom to New York City" first in the row |

Checkboxes are fine: `.ltick` is a 44 × 48 label around a 24 px box; `#ties` and `#lim-clear` sit inside labels.

### 16. A one-apartment building still makes her tap to open the apartment
139 of 231 buildings have a single apartment ("The apartment"), yet `details.aptd` starts closed, so the cost
breakdown is a fourth tap and 1,077 px down.
Fix: `open` when `B.units.length===1`, and drop "See the 1 apartment ↓".

### 17. Collapsed pages are well over the 1.5-screen target
See the height table at the end. Every experience (2,284 to 2,485 px), every neighborhood (1,568 to 2,416, median
1,738) and 230 of 231 buildings (median 1,546) exceed 1,266 px. The list she came for starts at y ≈ 1,300 on an
experience, ≈ 1,180 on a neighborhood, ≈ 1,090 on a building. On the first screen one experience card fits (cards are
273 to 298 px; the first starts at y = 315); the page is 3.7 screens.
Fix, biggest wins first: put the list directly under the "About" block and the rows after it; cap "About" bullets at
three; make the experience illustration 120 px, not 200; on the first screen shrink the title card (it takes 315 px)
and drop the banner art to 96 px so two cards show.

### 18. Jargon and internal words in the open
| Text (verbatim) | Where | Say instead |
|---|---|---|
| "Just 1 place here, and it has a gate question still open." | `#hood-nj-princeton` About | "Just 1 place here, and one thing about it is still to confirm." |
| "On our scorecard this ranks first of the 38 places here." / "First of 3 in this neighborhood on the scorecard." | building cards | "Our top pick here." (the badge already says it: delete the sentence) |
| "Rent (net-effective)", "Net-effective rent." | receipt, "Good to know" | "Rent, averaged with the free month" |
| "over the $3,000 cap", "leaves about $473 under your cap" | apartment, cards | "over your $3,000 limit" (the sheet is called "My limits") |
| "typical tolls, NY E-ZPass" | strips | "tolls, round trip" (E-ZPass detail behind the tap) |
| "all in" and "all-in", unexplained outside the cost row | everywhere (145 lines in 30 views) | one spelling; first use on each view "all-in (rent, fees, parking, utilities)" or a tap on the strip cell |
| "before traffic" / "without traffic" | "The catch", limits | "with clear roads" |
| "floor not published", "weight limit not stated", "parking rules not found, ask" | apartment meta, rows | "ask which floor", "ask the weight limit", "ask about street parking" |
| "listing", "the listing is still live", "the listing is genuine and for this building" | asterisk lines | "that it is still available", "that the ad is real" |
| "Good for you, watch for"; "Only warnings here"; "Worth a phone call, in other towns · 1 place, two or more things each" | row labels | "The good and the catch"; "Looked good, skipped"; "1 more place, if a call clears up two questions" |

### 19. False precision; rounding rules
Found: tolls "$38.91", "$23.20", "$16.66", "$14.92", "$66.64 a month"; distances "0.1 miles", "4.0 miles", "0.9
miles"; differences "−3.2 min", "+0.5 min", "+7.8 min", "−0.3 min"; "Niche overall rating: 3.78"; "569 square feet"
beside "about".
Rules: dollars per month to the dollar; tolls to the dollar ("$39"), "under $1" below that; minutes whole, and above 60
to the nearest 5 ("about 1 h 40"); differences in minutes whole, under 2 → "about the same"; distances under 0.2 mi →
"a block away", under 1 mi → minutes on foot, otherwise one decimal only below 3 mi and whole above; ratings one
decimal; percentages whole. Apply in one `fmt` module so prose and strips agree.

### 20. Headlines that count instead of concluding
| Row | Headline now | A conclusion |
|---|---|---|
| A day here | "6 moments: 2 strong, 2 mixed, 2 weak" | "Great mornings and parking; evenings are thin" |
| What residents say | "8 positive, 1 negative" / "6 positive" | "They love the parks; they warn about parking" |
| How others describe it | "3 descriptions" / "2 descriptions, from Wikipedia" | first description's gist, or fold into About |
| Local rules | "4 rules on record" | "No street parking overnight without a permit" |
| Reviews of the building | "4.4 on Google · 7 reviews, and 1 more site" | "Well reviewed (4.4 of 5, 7 reviews)" |
| Looks good, but avoid | "1 place we would skip, and why" | name it: "Skip 100 Prospect: no elevator" |
| Compare: the day | "they differ on 1 of 5 parts" | "Unit 606 wins the work day; the rest is level" |
| Compared to staying in Queens | "farther, pricier, smaller" | fine as is |

### 21. One thing, several names
- The thing she rents: "place" (strips, My list, counts), "apartment" (building page), "unit" ("Unit 606", "this unit",
  "washer in the unit"), "home" ("permit goes only to homes"), "House 1 / House 2" (compare), "listing" (asterisks).
  Rule: **building** and **apartment** only; "place" only where it means either ("513 places to see"); "Unit 606" only
  as the door number.
- Her parents: "Mom and Dad" (strips, map, rows), "your parents" (About text, 24 lines in 17 views), "Home is about 99
  minutes off by car" (Princeton), "the family orbit", "distance from family". Rule: "Mom and Dad" everywhere.
- "My list" / "Saved" / "Hold": the bar says "Saved · 0" and "My list" side by side; pick "My list · 3".
- Spelling: "neighborhood" (US) beside "Colour by experience", "licence", "service centre" (UK). Use US throughout.

### 22. The same passage repeated on one view
- Apartment open (Avalon Princeton 431): the rent offer is told five times: the line under "What it costs", "* Rent
  terms" (six fields), "Still to confirm → * Rent: $2,571 is the average…", "Good to know before you call →
  Net-effective rent", and tour questions 2 and 3, which are the same question twice. "Still to confirm" appears as a
  heading and again as "* Still to confirm". Fix: one "Rent offer" block; one question.
- Row headline repeated as its first body line: "garage, $50 a month" → "The car sleeps in a garage, $50 a month."
  "Reviews of the building" label then "Reviews of the building" h4. "6 moments…" then "6 moments".
- Compare: "$175 a month is $2,100 over a 12-month lease." is the row headline and the row's first line. "Not known
  yet" twice in each Parking cell.
- Neighborhood card + building About: the card's host line and the building's "About" are the same sentence.

### 23. Hedging and explaining still in the open (verbatim)
- "Only about 45 percent of listings say anything about parking, so ask." (`#exp-settled`, About)
- "There is an open question about whether this unit is still available at this price, so call before you plan a
  visit." (building, The catch)
- "We have not re-checked this listing live yet, so the price and the date are as first collected." (building, The catch)
- "* An estimate, or a cost the building has not published. Estimates are in the total. Costs that are not published
  are left out of it; they are not zero." (apartment, under the receipt, outside "See how we got this")
- "Needs a call: the listing does not settle what you pay each month." and "free-period timing not stated on the page
  (upfront, end of lease or spread): ask" (rent terms)
- "The middle mark is a typical Queens place. Left is worse for you, right is better. Tap a line to see how it was
  reached." (compare)
- "about" in front of every median ("about $2,719 a month all-in", "about 52 min"): the strip already says "typical".
Fix: each becomes a three-word ask ("Call first: may be gone", "Ask about parking") or moves under "See how we got this".

### 24. Dates
"seen Nov 15", "from Nov 21", "Nov 20 move-in" (no year) beside "Jan 1, 2027", "Dec 15, 2026", and raw
"move-in 2026-12-01 assumed", "as of 2026-11-15", and "Price seen Nov 15 (Nov 15, 2026, 5:01 PM New York time)".
Rule: "Nov 15" when the year is the current one and the date is within 60 days, otherwise "Jan 1, 2027"; never ISO;
never the same date twice in one line. Run rent-term notes through `dayStr()`.

### 25. Unknowns shown as a value
- "By mail they are typically $0 a visit." (`#exp-pre-car`, `#exp-settled`): say "No tolls either way".
- "By mail they are typically $27.10 a visit." appears with the same figure on `#exp-enclave` ($23.20 E-ZPass) and
  `#exp-middle` ($16.70): check the mail-rate median is per experience.
- Compare → Queens → Parking: "Not known yet / Not known yet" in all three columns, and Train and bus "Not known yet":
  hide a row that is unknown for every column.
- "No reviews found online" (searched, none) and "Not looked up yet" (never searched) must stay distinct; the first was
  seen on City Trust; confirm it was searched.

### 26. "Only show what differs" is on by default and hides rows silently
`#ties` is checked on arrival; "2 rows where they tie are hidden" sits in muted text beside it. Two apartments at the
same drive time lose the "To Mom and Dad" row entirely, so she cannot confirm they tie.
Fix: default off, or keep tied rows as one grey line: "Same for all: 82 min to Mom and Dad".

### 27. My list does not pre-tick
With exactly two or three saved, arriving at My list shows "Tick two or three to compare" (a live link styled dead,
`aria-disabled="true"`, which answers with a toast). Two extra taps every time.
Fix: when `S.saved.length<=3 && !S.pick.length`, pre-tick all; the button reads "Compare these 2".

### 28. Field names and pipeline text behind the taps
Behind "See how we got this", so lower priority, but she can reach all of it:
- Footer: "all_in_likely adds the median known parking fee…", "An elevator marked 'listing_site_only'…",
  "Disclosures are things to know that never remove a place…", "OSRM free-flow routing without traffic".
- Scale sheet: "the median of the Queens places that passed every gate", "point 1 of 5", "The bands: within $75…".
- Neighborhood: "Its place in the experience: mean rank score of its top 1 shown place(s), minus 4 for having fewer
  than three."
- Receipt: "Rent (as listed): live check; price changed at the live check: $2455 -> $2440"; "confirmed; parsed from
  the fee text"; "1 month(s) free from move-in; rent assumed due on the 1st".
Fix: a word map applied in `howHtml()` (gate → "must-have", net-effective → "averaged with free months", live check →
"checked again on <date>", listing_site_only → "only the ad says so"), and delete the scoring sentence.

---

## Polish

29. **Experience card link name** starts with the illustration's 150-character description ("A quiet street at dusk: a
    small apartment building tucked between two…") before the experience name. Inside `a.life` set the art
    `aria-hidden="true"`; keep the description on the experience page only.
30. **`#tray`** is a `div` with `aria-label` and no role, so the label is ignored. Make it `<nav aria-label="My list">`.
31. **"Open all"** changes its label to "Close all" and also flips `aria-pressed`; a screen reader hears "Close all,
    pressed". Drop `aria-pressed`.
32. **Browser Forward and reload** land at the top (forward to a building: y = 0; reload at y = 800 → 0). Store
    `scrolls` in `sessionStorage` keyed by route.
33. **Font sizes are all px** (249 declarations, 0 rem). Browser zoom works (no overflow at 640 or 320), but a larger
    default font size in the browser changes nothing: with `html{font-size:200%}` body text stayed 16 px. Move the
    scale to rem.
34. **Line length** is fine: 36 to 45 characters at 390, at most 78 at 1280 (the column is capped near 500 px).
    Line-height 1.35 on body; raise multi-line 13.5 px subheads to 1.4.
35. **Toast** "Saved. 11 places in My list, below." floats over the list for 3.2 s
    (`audit_390_05c_list_two_ticked.png`); on My list itself it is noise. Skip it there.
36. **External fonts**: the "single file" pulls Yellowtail, Bricolage Grotesque and Figtree from fonts.googleapis.com.
    Offline or blocked, headings fall back and heights change. Inline a subset or accept the fallback knowingly.
37. **"Back to where I was"** as the crumb on My list is clear; on a fresh load it reads "Experiences". Fine, once
    item 11 is fixed.
38. **Decorative "$" inside the compare row icon** is SVG `<text>` #FFD86B on white at 1.37:1 by computation (it sits
    on a dark disc; the row title carries the meaning). Confirm the SVG is `aria-hidden`.
39. **Empty and one-tick compare** are not dead ends ("Tick two or three places in My list. Open My list";
    "Nothing saved yet… Back to where I was"), but the empty My list is a full blank screen
    (`audit_390_list_empty_viewport.png`): add "Start with the top picks" linking to the first experience.

---

## Contrast table (computed from the rendered page, WCAG 2 ratios)

Text. "Need" is 4.5:1, or 3:1 for large text (≥ 24 px, or ≥ 18.66 px bold).

| Pair (text on background) | Ratio | Smallest size | Used for | Result |
|---|---|---|---|---|
| #3A1630 on #FFFFFF | 15.70 | 12 px | body text on cards, headlines | pass |
| #3A1630 on #FFF4F7 | 14.61 | 12 px | body text on the page background | pass |
| #FFFFFF on #3A1630 | 15.70 | 12 px | dark strip, selected switch, "My list" | pass |
| #F3DDE8 on #3A1630 | 12.20 | 11 px | labels on the dark strip, "· 0" | pass |
| #D7BFCC on #3A1630 | 9.15 | 10.5 px | range beneath the median, dark strip | pass (too small: item 12) |
| #7A5670 on #FFFFFF | 6.19 | 10.5 px | muted text, range on light strips, list labels | pass |
| #7A5670 on #FFF4F7 | 5.76 | 11 px | map legend, footer links, "Zoom to" | pass |
| #7A5670 on #FFFBEA | 5.97 | 10.5 px | ticked My list row | pass |
| #7A5670 on #DDF3E8 / #FFF3C9 / #FBE6E3 | 5.32 / 5.58 / 5.17 | 12 px | small text in green / yellow / soft-red compare cells | pass |
| **#8E6F85 on #FFFFFF** (#7A5670 at .85) | **4.39** | 11.5 px | range beneath the median on first-screen cards | **fail** |
| #C12C62 on #FFFFFF | 5.52 | 11.5 px | row caps labels, asterisks | pass |
| #C12C62 on #FFF4F7 | 5.14 | 11.5 px | "Top pick in this experience", moment labels | pass |
| #C12C62 on #FFE7EF | 4.71 | 13 px | "Next experience" | pass (thin) |
| #C12C62 on #FFFBEA | 5.32 | 14 px | "1* to confirm" in a ticked row | pass |
| #FFFFFF on #C12C62 | 5.52 | 13 px | "See the 27 neighborhoods", "Top pick" badge | pass |
| #14573E on #DDF3E8 | 7.33 | 11 px | "Strong" chip (green) | pass |
| #6B4A00 on #FFF3C9 | 7.26 | 11 px | "Mixed" chip (yellow) | pass |
| #8A3A32 on #FBE6E3 | 6.42 | 11 px | "Weak" chip (soft red) | pass |
| #3A1630 on #FFD86B | 11.43 | 11.5 px | "Ask" chips, rent-terms heading, compare heads | pass |
| #3A1630 on #FFF3C9 | 14.14 | 13.5 px | the asterisk line ("* To confirm…") | pass |
| #3A1630 on #DDF3E8 / #FBE6E3 / #E7F7EF / #FFE9E7 | 13.5 / 13.1 / 14.2 / 13.5 | 14 px | tinted cells and panels | pass |
| #FFFFFF on #1B6F50 | 6.11 | 13 px | "Saved" button | pass |
| #D6F0E4 on #1B6F50 | 5.08 | 12 px | "Tap to take it off your list" | pass |
| #FF9EC0 on #3A1630 | 8.15 | 23 px | "Saved" script in the bar | pass |
| #E0457B on #FFF4F7 | 3.68 | 34 px | script words "Pick", "The" | pass as large text only |
| #E0457B on #FFFFFF | 3.96 | 62 px | "Lamia's" | pass as large text only |
| **#856F7F on #FFFFFF** (chip at .62) | 4.61 | 12 px | unselected map chip name | pass (thin) |
| **#AD96A6 on #FFFFFF** (chip at .62) | **2.73** | 11 px | unselected map chip count | **fail** |
| **#A58E9B on #D7E4EA** | **2.33** | 11 px | map labels "Connecticut", "Hudson Valley", "Long Island" | **fail** |
| **#5B7C8C on #D7E4EA** | **3.44** | 11 px | map label "Atlantic Ocean" | **fail** |
| #B0A2AC on #FFFFFF (button at .4) | 2.44 | 22 px | disabled zoom "−" | exempt (disabled) |
| "Tick two or three to compare" (#7A5670 on #FFFFFF) | 6.19 | 16 px | disabled-looking Compare link | pass |

Marks and edges. Need 3:1.

| Pair | Ratio | Used for | Result |
|---|---|---|---|
| #3A1630 on #FFF4F7 | 14.61 | focus ring; card and button borders | pass |
| #FFD86B on #3A1630 | 11.43 | focus ring on the dark bar | pass |
| **#F3CADA on #FFFFFF / #FFF4F7** | **1.47 / 1.37** | border of rows, map chips, "Zoom to", disabled Compare | **fail** |
| #AA0E0E / #324BAE on #FFFFFF | 7.56 / 7.63 | Little-City square, Old-Neighborhood circle | pass |
| #AA42F0 on #FFFFFF | 4.42 | Walk-Everywhere plus | pass |
| #F04288 on #FFFFFF | 3.60 | Fresh-Start triangle | pass (thin) |
| #4192C8 on #FFFFFF / map land #FFFAF6 | 3.40 / 3.28 | Quiet-Street diamond | pass (thin) |
| #AA8B0E on #FFFFFF / map land | 3.28 / 3.16 | Room-to-Breathe triangle | pass (thin) |
| #E0457B on #FFE7EF | 3.38 | dashed "Next" border | pass |
| #FBE3EC on #FFFAF6 | 1.17 | drive band "30 min or less" fill against land (ink outline carries it) | fail without outline |
| #EE9BBB vs #FBE3EC, #BE4279 vs #EE9BBB, #5E1740 vs #BE4279 | 1.72, 2.37, 2.54 | adjacent drive-time bands | fail as a colour-only code (item 14) |
| #6FA8DC on #FFFFFF | 2.53 | rank pin fill (has an ink border and a number) | pass by border |

---

## Tap counts (real taps at 390 × 844, fresh visit, nothing saved)

| Goal | Taps | Path | Notes |
|---|---|---|---|
| First screen → one apartment's cost breakdown | **4** | experience card → neighborhood card → building card → apartment row | Plus scrolling: neighborhoods start at y ≈ 1,320, buildings at ≈ 1,295, apartments at ≈ 1,077. "See the … ↓" buttons trade each scroll for a tap (7 taps, no scroll). With item 16 fixed: 3 for a one-apartment building. |
| … → that apartment saved | **5** | + heart on the apartment row | 4 if she hearts without opening. The big "Save this place" is also 4, but saves every apartment (item 3). |
| … → comparing two saved apartments in different buildings | **12** | + Next (lands on the next neighborhood when the building is the last in its list) → building card → heart → "Saved" bar → tick → tick → "Compare selected (2)" | With item 27 (pre-tick): 10. |
| … → comparing two apartments in the same building | **9** | 3 to the building → heart → heart → bar → tick → tick → Compare | The compare heads then read the same for both (item 2). |
| Compare → back to an apartment | 1 | column head link | opens the building with that apartment open |
| Any page → My list | 1 | bar | always visible |

Dead ends and surprises found: page Back vs browser Back (item 11); "Save this place" saving many (item 3); "224 places"
jumping to neighborhoods (item 7); "Only show what differs" pre-checked (item 26); disabled-looking Compare that is a
live link (item 27); "Next building" silently becoming "Next neighborhood" at the end of a list (the label does change;
the destination is a list, not a building: say "Next: Princeton's buildings"). No keyboard trap was found; no view is
without a way out.

## Collapsed heights (390 × 844, whole document: sticky trail 60 px, footer 44 px and 54 px for the bar included)

| View | px | Screens | Target 1.5 (1,266 px) |
|---|---|---|---|
| First screen | 3,145 | 3.73 | one card in the first viewport; map starts at 2,159 |
| Experience (all 6) | 2,284 to 2,485 | 2.71 to 2.94 | 6 of 6 over |
| Neighborhood (all 103) | 1,568 to 2,416, median 1,738 | 1.86 to 2.86 | 103 of 103 over; 39 over 2.2 screens |
| Building (all 231) | 1,258 to 2,466, median 1,546 | 1.49 to 2.92 | 230 of 231 over; 38 over 2.2 screens |
| Building with one apartment (139) | 1,258 to 1,601, median 1,495 | 1.49 to 1.90 | 138 of 139 over |
| My list, empty | 844 | 1.00 | fills one screen with two lines of text |
| My list, 11 saved | 1,877 | 2.22 | about 128 px a row |
| Compare, two | 1,078 | 1.28 | under |
| Compare, three | 1,200 | 1.42 | under |
| At 320 × 640: experience / neighborhood / building | 2,684 / 2,534 / 2,691 | 4.2 / 4.0 / 4.2 | |
