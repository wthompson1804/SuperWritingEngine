# Plan: one connected data model, then finish the analysis

## Context

A lot has been collected, but it sits in about 60 separate files written by different agents, and each analysis
script reads only the few files it was pointed at. Nothing forces new data to be connected. That caused real
misses: police car-crime counts near buildings were collected and not applied; parking and building fees found
later never reached the all-in cost; facts confirmed in the evidence pass were never written back, so 268 of 412
shown units still count as "one fact inferred". The audit is in `house-hunt/docs/DATA_USE_AUDIT_2026-11-15.md`.

This plan builds a single connected model (two master tables, a field registry with an automatic check, one
pipeline command), fixes the specific gaps from the audit, and then resumes the paused collection work.
Everything Will approved earlier stays as approved: gates, Jamaica safety rule, six years, ranking weights,
avoid thresholds, five-point Queens scale.

## Part 1. Two master tables

New script `scripts/build_master.py` writes `data/master_buildings.csv` and `data/master_units.csv`.
Every later step reads only these two tables.

- **Building key.** A canonical `building_id` per physical building. Today `addr_key` varies by source (unit
  numbers inside addresses, "st" vs "street", Avalon keys that include the unit). Buildings are matched on
  normalized street address + ZIP, then on coordinates within about 30 m with a similar house number; every
  original `addr_key` is kept in a crosswalk (`data/reference/building_crosswalk.csv`) so all side files still join.
- **Sources merged, with a fixed precedence per field** (highest first):
  1. evidence pass, confirmed on the building's own page (`data/evidence/confirm_*`, `facts_*`, `live_check_*`)
  2. management-company community pages (`data/reference/community_facts.csv`)
  3. amenities parsed from cached pages (`data/reference/building_amenities.csv`)
  4. official records (NYC PLUTO `nyc_building_facts.csv`, `data/evidence/nyc_records*.csv`)
  5. the listing row itself (`data/listings.csv`)
  6. inference (6+ floors implies elevator; floor from unit number)
- **Provenance per field:** for each merged field the table stores the value plus `<field>_basis`
  (confirmed / stated / official_record / inferred / estimated / unknown), `<field>_source` and a URL.
  Conflicts between sources are written to `data/master_conflicts.csv` instead of being silently resolved.
- **Lookup-tool results** (drive, tolls, transit, crime incl. incidents near the building, places, texture,
  utilities) are flattened in full from `data/enriched/*.json` and `data/enriched_color/*.json`, including the
  fields unused so far: robbery, assault and burglary within 250 m, the evening share, transfers, last train home,
  Sunday return, toll completeness.

## Part 2. Field registry and automatic check

`data/reference/field_registry.csv`: one row per field in the master tables and in every evidence family, with
`used_in` = gate / all-in / score part / promise / avoid / display, or `not_used` plus a reason.
`scripts/check_registry.py` fails when a collected field is missing from the registry, or when a script reads a
side file directly instead of the master. It runs as the first step of every pipeline run.

## Part 3. Rent terms (net-effective basis, with the real rent on record)

Per Will: the net-effective rent is the basis for the budget and ranking; the app shows an asterisk; the database
says what the actual monthly rent is and when it is first owed.

- Finish `scripts/rent_terms.py` → `data/rent_terms.csv` (agent was paused; its plan is ready). It re-reads cached
  pages, because all 693 Apartment List rows lost their special-offer text at harvest.
- Fields: offer text verbatim, free months and timing, lease months, `gross_monthly_rent`, `net_effective_monthly`,
  `first_full_payment_date`, conditions, `needs_call`.
- Approved additions the agent asked for: two scenario columns (`gross_if_listed_is_net`, `net_if_listed_is_gross`)
  and a note explaining an empty first-payment date. Nothing is guessed: where the page does not say whether the
  price is gross or net, the unit is marked "needs a call" and shown with the asterisk.

## Part 4. All-in cost rebuilt on the master

`scripts/all_in.py` replaces the cost block in `enrich_units.py`:
rent (net-effective where known) + every known required fee + pet rent + parking fee + utilities **not** stated as
included. Each line carries its basis. The $3,000 gate is re-applied. A second figure, `all_in_gross`, uses the
gross rent, so the page can show what a paying month really costs.

## Part 5. Confirmed before shown

Confirmed facts flow into the master through Part 1, and `confidence` is recomputed from field bases. A unit with
an unconfirmed gate fact (elevator, floor, dog policy) can be ranked but is **not shown**; it goes to a
"needs confirmation" list with the exact question to ask. Live-check price changes are applied.

## Part 6. Ranking and avoid, reading the master

`scripts/rank.py` and `scripts/avoid.py` switch to the master tables. Additions from the audit, within the approved
weights:
- Safety part: robbery, assault and burglary within 250 m and the evening share (NYC); three-year crime trend.
- Distance part: transfers and the last Saturday train home.
- Avoid and pause notes: bedbug filings, evictions, illegal-parking complaints (NYC records).
- Tolls stay "unknown" where MTA rates are missing, until Will supplies the MTA table.
- Outside NYC: the rating-based standard (agent paused mid-run; resumes) decides avoid / pause / ok /
  not enough data. Jersey City's police incident page is usable (about 10.5 months of data): apply
  "double the median" there, labelled with its shorter window.

## Part 7. One command, with a stage report

`scripts/run_all.py` runs, in order: registry check → gates → master → rent terms → all-in → neighborhoods →
lifestyle groups → evidence rules → ranking → report. `docs/RUN_REPORT.md` lists, per stage, units in, units out
and why, plus the fill rate of every field among shown units, and a diff against the previous run.

## Part 8. Independent check

A separate agent takes 30 random shown units and checks every master field against the live source pages, and
reviews the registry for wrong wiring. Its findings go to `docs/INDEPENDENT_CHECK.md`; errors are fixed before
anything is shown to Will.

## Part 9. Resume paused collection

Paused by plan mode with their work cached: evidence round 2 (batches 7, 8, 10, 11; batch 9 state to confirm),
the rating standard and non-NYC records, rent terms. Still to report: the five regional agents and Apartment
List's outer ring. All are resumed; none conflicts with Parts 1–8, since they write their own files and the
master picks them up on the next run.

## Assumptions (say if wrong)

- **Taxes:** not added to the all-in cost. Shown as a note per year (for example the NYC resident income tax),
  because adding it needs an assumed income.
- **Never-collected items:** collect street-parking rules, dog rules and neighborhood-level resident voices for the
  neighborhoods that end up shown. Flood zone, fiber and noise stay out unless asked for.
- Jersey City incident data is used, labelled with its 10.5-month window. Its robots-disallowed open-data API
  stays off limits.

## Files

New: `scripts/build_master.py`, `scripts/check_registry.py`, `scripts/all_in.py`, `scripts/rent_terms.py`,
`scripts/run_all.py`; `data/master_buildings.csv`, `data/master_units.csv`, `data/master_conflicts.csv`,
`data/rent_terms.csv`, `data/reference/building_crosswalk.csv`, `data/reference/field_registry.csv`;
`docs/RUN_REPORT.md`, `docs/INDEPENDENT_CHECK.md`.
Changed: `scripts/rank.py`, `scripts/avoid.py`, `scripts/build_neighborhoods.py`, `scripts/lifestyle_*.py`
(read the master), `scripts/enrich_units.py` (lookups only), `PROGRESS.md`, `CLAUDE.md`, `docs/RANKING.md`.
Reused as is: `scripts/lib.py`, `scripts/gates.py`, `scripts/tools/*`, `scripts/nyc_building_records.py`,
`scripts/building_amenities.py`, `scripts/crime_benchmarks.py`.

## Verification

- `check_registry.py` passes: no collected field unaccounted for; no script reads a side file directly.
- `RUN_REPORT.md` shows every stage's counts and the reasons units left.
- Spot checks: a unit with a known parking fee shows it in the all-in lines; Alvista Rise shows net and gross rent
  and a first-payment date; a unit with a confirmed elevator has `elevator_basis = confirmed`; no shown unit has an
  unconfirmed gate fact; NYC buildings carry nearby violent-crime counts in the safety part.
- The independent agent's 30-unit check finds no field that disagrees with its source.
