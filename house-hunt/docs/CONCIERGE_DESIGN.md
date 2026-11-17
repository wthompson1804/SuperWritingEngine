# The concierge draft: design and data contract

A second, separate page built on the same data as the first ("Lamia's House Hunt"). The first page, its template
(`site/index.html`), its data (`site/data.json`), its text CSVs and `scripts/verify_all.py` are **not changed** by
this work. Approved by Will on 2026-11-17.

## Why

The first page is a catalog (523 apartments, four levels deep). Lamia's question is "what kind of life do I want next
year?" and she wants someone to make the choice with her. This page behaves like a concierge across the table: three
stories, a couple of either/or questions, a recommendation of five buildings to tour, and a tour plan.

## Rules for this page (Will, 2026-11-16/17)

- Nothing above **$2,000 listed base rent** is shown. This is a rule for this page only; the pipeline and the first
  page keep $3,000.
- A neighborhood with exactly one apartment is shown but is never its own stop: it is parked under the nearest larger
  neighborhood in the same experience ("Also nearby").
- Everything in the first page's rules still holds: plain language (no "all-in", "cap", "unit", "gate", "we"), no
  crime wording in the open, rent and total always shown as a labelled pair, photos are a link, a star means one
  thing to confirm, private phone numbers never shown.
- No information is thrown away: "See everything" lists every building with a filter and the map.

## The four steps

1. **Three stories.** One tap-through story per experience, about five cards (illustration and promise; a weekday;
   Saturday night; Sunday with Mom and Dad; what it costs and the catch). She taps to advance. Answer:
   **That's me / Maybe / Not me**. Answers re-rank and never delete.
2. **Either/or questions**, at most three, only where the data trades off. Skippable.
3. **"Here is what I would do."** Five buildings, one at a time: one reason, one thing she gives up, the same five
   facts (rent; total with utilities and fees; drive to Mom and Dad; parking; dog) each with a marker showing where
   it sits among all the buildings on this page. "See photos". **Keep / Not this one** (the next best replaces it).
   Apartments are a detail inside the building card.
4. **Her tour plan.** Kept buildings grouped by area: address, public office contact, questions to ask.

Optional: **Ask the concierge** (the artifact `sample` capability). Hidden unless it resolves; answers only through
lookup functions over the page's data; says "not known" otherwise.

## Data contract: `site/concierge_data.json`

Written by `scripts/concierge_data.py` from `site/data.json`. The page reads only this file (plus
`site/illustrations.json` and the map files).

```
meta:        { built_at, rent_limit: 2000, counts: {apartments, buildings, neighborhoods, experiences},
               tour_start, move_in_by, anchor_label: "Mom and Dad" }
experiences: [ { id, label, tagline, illustration_id,
                 figures: { rent_median, rent_range:[lo,hi], total_median, total_range, drive_min_median,
                            drive_min_range, toll_round_trip_range, apartments, buildings },
                 story: [ { kind: "promise"|"weekday"|"saturday"|"sunday"|"cost"|"catch", title, text, icon } ],
                 neighborhood_ids: [...] } ]
neighborhoods: [ { id, name, state, experience_id, lat, lon, drive_min, toll_round_trip, about, points:[{icon,text}],
                   parked_under: <neighborhood id or null>, also_nearby: [ids], building_ids:[...] } ]
buildings:   [ { id, name, address, city, state, lat, lon, neighborhood_id, experience_id, rank_score,
                 why, give_up,                       # one sentence each, from the existing guarded text
                 facts: { rent_from, rent_to, total_from, total_to, drive_min, toll_round_trip,
                          parking: {summary, kind, fee}, dog: {summary, weight_limit_lb} },
                 scores: { parents, going_out, green, value, parking, home },   # 0..1, for re-weighting
                 confirm: [ {label, question} ], tour_questions: [...], disclosures: [...],
                 photos_url, listing_url, contact: {office_phone, site} | null, about, points:[{icon,text}],
                 day: [ {title, text, level} ],
                 apartments: [ { id, label, beds, sqft, floor_text, rent, total, available_text, offer, star,
                                 confirm_label, listing_url, source_site, last_read } ] } ]
either_or:   [ { id, question, a:{label, weight:{score_key: delta}}, b:{label, weight:{...}} } ]
```

Every figure in `experiences[].figures` and every number inside story text is computed over the apartments kept on
this page. A missing value is `null`, never a guess.

## Files

| File | Owner |
|---|---|
| `scripts/concierge_data.py`, `--data` / `--out-suffix` options on the text builders, `data/reference/*_u2000.csv` | data and text |
| `site/concierge.html`, `scripts/build_concierge.py`, `scripts/test_concierge_pick.js`, `scripts/concierge_walkthrough_test.js` | page |
| `data/evidence/live_check_batch_21.csv` | re-read |
| `scripts/verify_concierge.py`, this file, `CLAUDE.md`, `PROGRESS.md` | coordinator |

---

## Version 2 (Will, 2026-11-17): ask well, then go straight to what fits

Will's review of version 1: the interface is much better; now (1) ask the right questions the right way to learn
her preferences, (2) skip straight to the apartments that fit, (3) every place says which experience it belongs to
and what life would be like there, made meaningful with real, sourced local detail (there are few enough places
to research each one), (4) she picks and compares, (5) saved places and compare must be obvious and one tap away.

### Principles (from the research behind version 1)

- Ask about her life, not about attributes: "how often will you see Mom and Dad?" rather than "how important is
  distance?". Concrete situations, one question per screen, one tap per answer, no sliders, under two minutes.
- Separate must-haves (screens) from preferences (weights). A must-have answer moves places that fail it to a
  collapsed "Doesn't fit what you said" group with the reason; nothing is deleted.
- Show consequences while she answers: a live "N of 22 places fit" under every question, and an answer that would
  leave none says so before she taps it.
- End with an explicit priority pick ("Which two matter most?"): explicit values clarification beats inferred.
- After the questions, the experience is a label and a story on each place, not a gate in front of them.

### The flow

1. **Welcome**: one sentence, Start. A quiet link "First, see the three kinds of life" opens the version-1 stories.
2. **Questions** (from `questions` in the data; the page renders whatever is there, in order):
   visits (how often she will see Mom and Dad) → longest drive she would make for a visit (must-have) → room to
   work (separate bedroom needed / studio with room for a desk / either; the first is a must-have) → Saturday night
   (walk out / drive somewhere / stay in) → the dog's daily walk (park to walk to / dog area in the building /
   either) → where the car sleeps (garage even at a cost / any off-street spot / street is fine) → a comfortable
   monthly total with utilities and fees (must-have) → which two matter most.
3. **Your matches**: every place that fits, best first; the top three marked "Best fits". Each card: experience
   badge, name and neighborhood, "Fits you because" (two or three chips tied to her answers, each with the real
   figure), one amber chip for any preference it misses, rent and total as a labelled pair, the checked line,
   Save. Below, collapsed: "Doesn't fit what you said (N)" with the reason on each.
4. **A place**: experience badge and one line on what that experience means → **Life here** (A weekday, Saturday
   night, Sunday with Mom and Dad, The dog's walk: specific to this building, named places, sourced) → the five
   facts with position markers → the apartments → things to confirm → See photos. Save at top and bottom.
5. **My list**: a bar fixed at the bottom of every screen once anything is saved: "My list · 3" and "Compare".
   My list shows saved places with tick boxes; tick two or three, Compare.
6. **Compare**: two or three columns, one row per fact (rent, total, drive and tolls, monthly visit time and tolls
   at her visit frequency, room, parking, dog, going out, green, checked status, experience, life here in one
   line); the better value in each row marked; rows where all are the same collapse under "Same for all".
   "Choose this one" adds it to the tour plan.
7. **Tour plan**: as in version 1.

### Data contract additions (`site/concierge_data.json`), all added, none renamed

```
questions: [ { id, text, help, kind: "single"|"pick_two", must_have: bool,
               answers: [ { id, label, sublabel,
                            filter: {field, op, value} | null,      # must-have screens, on building fields below
                            weights: {score_key: number} } ] } ]
buildings[].fit:   { drive_min, toll_round_trip, has_one_bedroom, has_studio, studio_only,
                     min_total, max_total, parking_kind, garage_or_covered, off_street,
                     dog_area_in_building, park_walk_min, park_name,
                     restaurants_10min, bars_10min, cafes_10min }      # the fields filters and chips read
buildings[].fit_chips: { <answer id>: "11 minutes to Mom and Dad" , ... }  # the chip text per answer, real figures
buildings[].experience_line: "One plain line on what this experience means"
buildings[].life_here: [ { moment: "weekday"|"saturday"|"sunday"|"dog", title, text,
                           places: [{name, kind, walk_min|null, distance_mi|null}],
                           sources: [{name, url}] } ]
experiences[].line: same line as experience_line, for the badge sheet
```

Every number in `fit_chips` and `life_here` comes from the data; every named place comes from the mapped places
already in `data/enriched_color/` or from `data/reference/life_here_facts.csv` (sourced web research, each row with
URL and retrieval time). A moment with nothing true and specific to say is left out, never padded.

---

## Version 3 (Will, 2026-11-17): a recommender, asked by "this or that"

Will's direction: the experiences are no longer needed; cut the data by what matters to her. Ask only what is
diagnostic, as a few trade-offs between real places ("this or this"), not a list of questions. Then recommend the
**top three neighborhoods**, each with its **top three buildings**; under each, **two or three more like it** as small
thumbnails; everything else one tap away. (His message ended mid-sentence: "Maybe we do,". Anything he adds wins.)

### What the data says (22 buildings, 2026-11-17)
Close to Mom and Dad and room at home move strongly apart (correlation -0.74); going out and room apart (-0.64);
close to Mom and Dad and going out together (+0.55); money and parking mostly independent. So the main choice is
"city life near family, small studio" against "more room, farther out", with money and parking as side choices.

### The model (one implementation in Python as the reference, the same in the page's JS, tested to agree)
1. **Fixed rules** stay rules: rent at or under the page's limit, the dog, move-in, floor or elevator.
2. **Features per building**, each turned into a 0..1 value with a shape that behaves like life:
   - `family`: drive to Mom and Dad -> value falls slowly to 25 min, steeply from 35 to 90 min (hours a month matter);
   - `money`: dollars left under $2,300 total a month, linear;
   - `room`: log of square feet, plus a step for a separate bedroom;
   - `going_out`: restaurants and bars within a 10-minute walk, steep to about 20, flat after 60;
   - `green`: nearest park walk, full at 5 minutes or less, half at 12, low past 20; a dog area adds a little;
   - `parking`: garage or covered 1, off-street 0.7, unknown 0.4, street 0.2;
   - `sure`: confirmed today 1, last seen earlier 0.6, one thing to confirm 0.8 (multiplies, never adds).
   Missing values are the median of the set, flagged.
3. **What we already know is the prior**: 400 weight vectors over the six features, drawn once in Python with a fixed
   seed from a Dirichlet centred on her profile (family, going out, green and room weighted up a little; parking and
   money neutral) and shipped in the data, so the page and Python use the very same samples.
4. **"This or that"**: each question shows two real buildings side by side (name, place, five facts, one line of life
   here) and three answers: this one, that one, "either is fine". The likelihood is logistic in the utility gap
   (temperature in the data); "either" favours samples where the gap is small. Weights are re-weighted after each answer.
5. **Next pair**: among pairs drawn from the current top 30 buildings, the pair whose answer is expected to change the
   recommended top three most (expected reduction in uncertainty about the top-three neighborhoods). At least three
   pairs, at most six; stop early once the probability that her best neighborhood (per weight sample) is among the
   current three reaches 0.8 (changed 2026-11-17: on a set of ~57 neighborhoods an exact top-three set almost never
   reaches 0.8, so the old rule always asked six).
6. **Recommendation**: a building's score is expected utility under the re-weighted samples times `sure`. A
   neighborhood's score is the mean of its two best buildings. The three neighborhoods are picked greedily for score
   with a diversity term (maximal marginal relevance, lambda 0.7, distance between neighborhood feature centroids), so
   the three are real alternatives. Within each, the three best buildings. A one-apartment neighborhood counts as its
   host's, as now.
7. **More like this**: per building, the three nearest other buildings in feature space (standardised features,
   weighted by her current mean weights), excluding ones already on screen; shown as small thumbnails.
8. **Why, and what would change it**: for each recommended neighborhood, the two features that lift it most against
   the average, one thing it gives up against the other two, and one "if X mattered less/more, Y would come first"
   found by nudging one weight.
9. Tags in place of experiences: two plain words per neighborhood from its strongest features ("Lively, near family",
   "Quiet, more room").

### Data contract additions (all added, none renamed)
```
meta.recommender: {features:[...], value_functions:{...}, temperature, either_band, n_samples, seed,
                   min_pairs, max_pairs, stop_prob, mmr_lambda, pair_pool}
recommender_samples: [[w_family, w_money, w_room, w_going_out, w_green, w_parking], ...]   # 400 rows
buildings[].features: {family, money, room, going_out, green, parking, sure}   # 0..1
buildings[].features_raw: {drive_min, total, sqft, bedroom, restaurants_10min, park_walk_min, parking_kind, checked}
buildings[].similar: [ids]                     # unweighted nearest, for the page to re-rank with her weights
neighborhoods[].tags: ["Lively", "near family"]
meta.recommender_examples: [{answers:[{a,b,choice}], expected_pairs:[...], expected_top:[[hood,[b1,b2,b3]],...]}]
```

---

## Version 4 (Will, 2026-11-17): hypothetical trade-offs, and a results page you can read in order

Will's review of version 3: choosing between three real places is gimmicky and can't be predictive (real places
differ on everything at once, so a choice says little about why); and the results overwhelm, with no clear reading
order. Instead: **"this or that" between made-up apartments**, the way pricing studies in behavioral economics do it
(choice-based conjoint), and a results page that says plainly: these are the three neighborhoods, these are the three
places in each, and you can browse everything else.

### The choices (choice-based conjoint, partial profiles)
- Each choice shows two made-up apartments, "Apartment A" and "Apartment B", described only by attribute levels.
  To keep each choice easy, the two differ on **two or three attributes**; the rest read "Same for both" (partial
  profiles). Levels are drawn from the real spread of the places on the page, so every trade-off is a real one.
- Attributes and levels (plain words; each maps onto the recommender's features with the same value functions):
  - Monthly total with utilities and fees: four levels across the real range (about $1,700 to $2,300).
  - Drive to Mom and Dad: 15, 35, 60, 90 minutes.
  - Space: studio about 450 sq ft; studio about 600; one bedroom about 700; one bedroom about 900.
  - Going out: quiet (a couple of places on foot); some (about 15); lively (40+).
  - Parking: street only; a spot in a lot; garage.
  - A park for the dog: 2, 8, 15 minutes on foot.
- Answers: A, B, or "No real difference to me". No dominated pairs (one never better on everything).
- **Eight choices**, adaptive: each next pair is the one expected to teach most about her weights (largest expected
  reduction in posterior uncertainty over the weight samples, utility-balanced), with a fixed progress "3 of 8".
  The research on choice-based conjoint is that a handful of tasks gives usable individual weights only when the
  pairs are chosen adaptively and kept simple; eight is the floor we use, not a promise of precision.
- Then one confirmation screen: "Here's what you told me", her learned priorities in plain words, top first ("Space
  matters most to you, then being near Mom and Dad; parking matters least"), with "That's right" and "Not quite".
  "Not quite" lets her move one priority up or down (a small, explicit correction), then re-ranks.

### The results, in one reading order
1. One sentence: what she cares about.
2. **Three neighborhoods**, numbered 1 to 3. Each is a card: name, two tags, one line why, one line what you give
   up. The first is open; 2 and 3 are closed and open on tap.
3. Inside each neighborhood: **three places**, as compact rows: name, rent and total, one fact that matters to her,
   the checked line. Tap a row to open the place.
4. Below the three: "Browse everything" (filters, map), "Change my answers".
Nothing else on the results page: no "what would change it", no "more like this" row under every card (the place
sheet keeps "More like this" at its bottom).

### Validation (must be reported before publishing)
Simulated users with hidden weights answer the made-up pairs; report how often their true best neighborhood is in the
three, weight recovery, and how results move with each answer. Five personas as before.
