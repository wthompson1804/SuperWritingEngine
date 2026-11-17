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
