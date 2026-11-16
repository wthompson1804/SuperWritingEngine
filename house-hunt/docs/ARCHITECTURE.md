# Architecture

Written 2026-11-16 from the code as it stood. This file says how the pieces connect and which script owns each step.
It does not restate the rules: those are in `CLAUDE.md` (the owner's decisions as they stand), `docs/RANKING.md`
(gate facts, open items, scoring, selection), `docs/PLAN_V3_APPROVED_2026-11-15.md` (gates, avoid thresholds),
`docs/PLAN_V4_MASTER_MODEL_2026-11-15.md` (the master-table model) and `docs/SAFETY_BASIS.md`.
Per-file contents are in `docs/DATA_DICTIONARY.md`; per-script detail in `scripts/README.md`.

## Data flow

```
 sources (listing sites, management sites, records, OSM, GTFS, Census, FBI)        raw/<source>/  (cache + _index.jsonl)
   │  harvest scripts h_*.py, one agent per source, run once each
   ▼
 data/listings_raw/*.csv ──────────────────────────────────────────────┐
   │  gates.py  (merge, dedupe, gate; twice, around enrich_nyc_pluto.py)│  community_facts.csv, nyc_building_facts.csv,
   ▼                                                                    │  evidence/resolved_pending_batch_*.csv
 data/listings.csv   pass / pending / fail per listing  ◄───────────────┘
   │  enrich_units.py  (scripts/tools: drive, transit, crime, places, utilities)
   ▼
 data/units.csv + data/enriched/*.json + data/buildings_enriched.csv
   │  build_neighborhoods.py → lifestyle_features.py → lifestyle_color.py → crime_benchmarks.py → lifestyle_groups.py
   ▼
 data/neighborhoods.csv, data/neighborhood_safety.csv, data/lifestyle_groups.csv   (neighborhood, safety, experience)
   │  building_amenities.py --no-fetch
   │  build_master.py   ◄── data/evidence/*  data/reference/*  (basis and source per merged fact)
   ▼
 data/master_buildings.csv + data/master_units.csv        ← the only tables the analysis steps may read
   │  rent_terms.py  → data/rent_terms.csv
   │  all_in.py      → all-in columns on master_units.csv, cost_gate
   │  avoid.py       → data/unit_exclusions.csv, data/avoid_buildings.csv        (evidence rules)
   │  verdicts.py    → data/evidence/review_verdicts.csv   (written by a reviewer, read by rank.py)
   │  rank.py
   ▼
 data/ranked_units.csv  (+ excluded_*.csv, needs_confirmation.csv, needs_live_check.csv, group_exchange.csv)
   │  test_rules.py --data, check_registry.py                                   ── end of scripts/run_all.py ──
   │  build_page_data.py
   ▼
 site/data.json
   │  page_data_extras.py  ◄── scene text, About text, contacts, quotes, local rules, descriptions, ratings census
   ▼
 site/data.json (complete)
   │  build_site.py  ◄── site/index.html, site/map_base.json, site/illustrations.json
   ▼
 site/dist/index.html  ──  build_artifact.py (publish step)  ──►  site/dist/artifact.html  ──►  new private artifact
```

`scripts/run_all.py` runs everything from the tests to `check_registry.py` and writes `docs/RUN_REPORT.md` and one row
of `data/reference/run_history.csv`. `--fast` skips the block from `gates.py` to `lifestyle_groups.py`. The three page
steps and the publish step are run by hand afterwards. Harvests and evidence batches are never run by `run_all.py`.

## Stages

**0. Sources and harvest.** One harvester per source (`h_zumper.py`, `h_trulia.py`, `h_apartmentlist.py`,
`h_mgmt_*.py`, `h_region_*.py`, `h_manual.py`), each run once by its own agent under
`docs/HARVEST_AGENT_BRIEF.md` or `docs/REGION_AGENT_BRIEF.md`. Input: the search grid
(`data/reference/search_grid.csv`, every ZIP area within a two-hour free-flow drive) and the source's pages. Output:
`data/listings_raw/<source>.csv` in one column contract, pages cached under `raw/<source>/`. Rules enforced: robots
and the one-refusal rule (`docs/SOURCES.md`), prices and dates only from the listing page, nothing above $3,000.
Guard: each harvester stops on a 403, 429 or CAPTCHA; what happened is in `docs/harvest_notes/<source>.md`.

**1. Gates** (`scripts/gates.py`). Input: every file in `data/listings_raw/`, plus facts that fill listing blanks:
`data/reference/community_facts.csv` (management communities), `data/reference/nyc_building_facts.csv` (PLUTO, from
`enrich_nyc_pluto.py`, which is why gates runs twice), `data/evidence/resolved_pending_batch_*.csv` (pending listings
a later evidence batch settled). Output: `data/listings.csv` with a `g_*` column per gate and
`gate_status` = pass / pending / fail; `data/gate_summary.md`. Rules: plan v3 gates as amended (`CLAUDE.md`, "Fixed
parameters and gates"). Only listed rent is checked here; the all-in cap comes later. Guards: `test_parsers.py`,
`test_rules.py`.

**2. Enrich** (`scripts/enrich_nyc_pluto.py`, `scripts/enrich_units.py`, `scripts/tools/`). For each building with a
passing listing, run the lookup tools: `drive.py` (OSRM free-flow time, tolls from `data/reference/tolls.csv` and
`njta_tolls.csv`), `transit.py` (GTFS), `crime.py` (police-agency rates, nearby incidents in NYC), `places.py` (local
OpenStreetMap index), `utilities.py`. Output: one JSON per building in `data/enriched/` with provenance,
`data/buildings_enriched.csv`, `data/units.csv`. Every tool returns `not_found` with a reason instead of a guess.
Notes per tool: `docs/tools_notes/`.

**3. Neighborhoods, safety, experiences** (`build_neighborhoods.py`, `lifestyle_features.py`, `lifestyle_color.py`,
`crime_benchmarks.py`, `lifestyle_groups.py`). A neighborhood is the NYC Neighborhood Tabulation Area, else the
Census place, else the county subdivision; Jersey City is split by `data/reference/subcity_*`
(`docs/SUBCITY_SPLIT_PLAN.md`). Features are ACS tract data and OSM counts, with no location features. Groups are
assigned from saved centres (`data/reference/lifestyle_group_centres.csv`) so reruns do not reshuffle them; `--refit`
only on purpose. Output: `data/neighborhoods.csv`, `data/lifestyle_features.csv`, `data/lifestyle_color.csv`,
`data/neighborhood_safety.csv`, `data/lifestyle_groups.csv`. The safety rule itself (`docs/SAFETY_BASIS.md`) is
applied in `rank.py`.

**4. Master tables** (`scripts/building_amenities.py --no-fetch`, then `scripts/build_master.py`). Input:
`data/units.csv`, `data/enriched*/`, `data/reference/{building_amenities,community_facts,nyc_building_facts,
address_overrides,elevator_doubt,overnight_parking_towns,…}.csv`, every evidence family under `data/evidence/`.
Output: `data/master_buildings.csv` (one row per physical building), `data/master_units.csv` (one row per listed
unit with its building's merged facts), `data/master_conflicts.csv`, `data/duplicate_units.csv`,
`data/reference/building_crosswalk.csv` (every address key → building id). Each merged fact carries `<field>`,
`<field>_basis`, `<field>_source`; the basis order is in the script's docstring (phone answer first, inference last).
This is also where the elevator grading, the doubt table and garden-style rule, staleness dates and the
overnight-parking disclosure are computed (`docs/RANKING.md`, "Rules added 2026-11-16"). Model: plan v4, Part 1.

**5. Rent terms** (`scripts/rent_terms.py`). Reads each passing unit's cached page and the evidence rows; writes
`data/rent_terms.csv` (offer text verbatim, offer type, free months, gross and net where the page supports them,
first full payment, `needs_call`). Nothing is guessed: a price is net-effective only where a page or an evidence row
says so. No network.

**6. All-in cost** (`scripts/all_in.py`). Adds the cost receipt to `data/master_units.csv`: `all_in`,
`all_in_lines`, unknown and estimated lines, `all_in_likely`, `cap_margin`, `cost_gate`. Rules: the cap and the
pet-rent estimate in `CLAUDE.md`; medians used for estimates are written to `data/reference/cost_estimates.csv`.
`check_registry.py` enforces that this script and `rank.py` read only the master tables and a short allowed list.

**7. Evidence rules** (`scripts/avoid.py`). Reads the evidence families and city records and writes
`data/unit_exclusions.csv` (units that are gone, fail a gate on closer reading, are restricted, or are probably
ground-floor; whole buildings that are co-ops) and `data/avoid_buildings.csv` (avoid yes / no with reasons, pause
notes, the evidence shown on the card). Thresholds: plan v3 and the script's docstring.

**8. Rank and select** (`scripts/rank.py`, with `scripts/verdicts.py`). Applies, in order: the all-in cap, the
Jamaica safety rule, gates on confirmed facts, reviewed `remove` verdicts, the sibling floor rule, listing confidence
(sketchy), evidence exclusions; then scores (ranking v2), counts open items and disclosures, and selects what is
shown. Output: `data/ranked_units.csv`, the five `data/excluded_*.csv` files (one per reason a unit left),
`data/needs_confirmation.csv` (the phone list), `data/needs_live_check.csv`, `data/group_exchange.csv`,
`data/reference/queens_spectrum_definition.csv`. Rules: `docs/RANKING.md`, read from the bottom up.

**9. Checks** (`scripts/test_rules.py --data`, `scripts/check_registry.py`). The first re-tests every defect of
independent checks 2 and 3 on the output. The second builds `data/reference/field_registry.csv` (every column, who
uses it, and why any unused one is kept), fails on an unaccounted field or a side-file read, and asserts the shown
list: gates, cap, window, one open item at most, asterisk fields present, no avoid building, a current reviewed
verdict, at most 8 per building.

**10. Page data** (`scripts/build_page_data.py`). Reads `data/ranked_units.csv`, `data/lifestyle_groups.csv`,
`data/avoid_buildings.csv`, the two `needs_*.csv` files, round-1 local rules and voices, and writes `site/data.json`
(`meta`, `years`, `neighborhoods`, `buildings`, `units`, `avoid`, `held`, `awaiting_live_check`). Experience and
neighborhood figures are computed over the shown units. Unknown is `null`, never a guess.

**11. Extras** (`scripts/page_data_extras.py`). Adds to `site/data.json`, in place and idempotently: scene prose and
About points, round-2 quotes, survey rows and local rules, contacts, "About the building", the ratings census, per-unit
lines, outside descriptions, photo links, finer map coordinates, the neighborhood order inside each experience, and
the last screen for quotes that single out a named group. Its report is stored in `meta.extras`.

**12. Site** (`scripts/build_site.py`). Inlines a slimmed copy of the data, `site/map_base.json` and
`site/illustrations.json` into `site/index.html` at three marker comments and writes `site/dist/index.html`.
`scripts/build_artifact.py` then takes the outer document shell off the built page, because the artifact host wraps
the file in its own document, and writes `site/dist/artifact.html` (title within the first 8 KB, under 16 MB).

## The evidence-batch method

The gates run on what listing pages say. The evidence pass checks the candidates more closely, in batches so that
many agents can work at once without touching each other's files.

1. `rank.py` marks the candidates (top 15 per neighborhood, 2 per building). A batch file
   `data/reference/evidence_batches/batch_<n>.csv` lists buildings for one agent.
2. The agent follows `docs/EVIDENCE_AGENT_BRIEF.md`: re-fetch each listing (is it live, same price, same date);
   confirm open gate facts on the building's own page, quoting the sentence; collect dated tenant and public evidence;
   record useful facts and ratings.
3. It writes one set of files per batch under `data/evidence/`: `live_check_batch_<n>.csv`, `confirm_batch_<n>.csv`,
   `facts_batch_<n>.csv`, `items_batch_<n>.csv`, `ratings_batch_<n>.csv`, and notes in
   `docs/harvest_notes/evidence_batch_<n>.md`. Batch files are never edited afterwards: later repairs change how they
   are read, not what they say.
4. Beside the batches: `nyc_building_records.py` (city records with citywide baselines →
   `nyc_records_flags.csv`), `non_nyc_records.py`, `rating_standard.py` (`docs/RATING_STANDARD.md`), and the ratings
   census (`docs/RATINGS_CENSUS_BRIEF.md`, information only).
5. `build_master.py` folds confirmations and facts into the master tables with their basis; `avoid.py` turns live
   checks and items into exclusions and avoid cards.

Batches 1 to 17 are the three rounds; 18 is `resolve_pending_thin_years.py` (pending listings in the thin experiences);
19 covered buildings that had no evidence; `manual` and `ic2` are small hand-made sets.

## The review-verdict loop

Evidence agents wrote doubts in plain words; rules read only fixed phrases (`docs/INDEPENDENT_CHECK_2.md`). So no
unit is shown on rules alone.

1. `python3 scripts/verdicts.py digest` prints, per unit that could be shown, every evidence row of its building.
2. A reviewer (a person or an agent) reads it and writes verdict rows: `ok`, `asterisk` (an open gate fact, with what
   and why), `disclose` (a condition to know), or `remove`. Several rows per unit, one per kind.
3. `python3 scripts/verdicts.py add <file>` stores them in `data/evidence/review_verdicts.csv` with a hash of the
   building's evidence at that moment.
4. `rank.py` applies them. `check_registry.py` fails the run if a shown unit has no current `ok`, `asterisk` or
   `disclose` verdict, or if its evidence changed after the verdict was written. A verdict never closes a fact the
   rules leave open.

Independent checks (`docs/INDEPENDENT_CHECK*.md`) are the outer loop: an agent that did not write the pipeline
compares the shown list with live pages and evidence; each check is answered by a repairs document and new tests.

## The scene-text system

All prose is tied to data (`docs/SCENE_TEXT_NOTES.md`).

- **Experiences and neighborhoods.** Hand-written drafts live in `data/reference/scene_text_source.txt`. Numbers are
  never typed: each is a token naming a measured field. `scripts/build_scene_text.py` fills the tokens and writes
  `scene_text_years.csv` and `scene_text_neighborhoods.csv`, each row with an `evidence_json` that says where every
  number and claim comes from. `scripts/check_scene_text.py` re-tests each item against the current data and enforces
  house style, including no crime wording in open fields. A row whose numbers moved fails until the draft is rebuilt.
- **Buildings and units.** `scripts/realtor_lines.py` composes "About the building" and each unit's line, catch and
  section subheads from sentence libraries and the unit's own fields in `site/data.json`
  (`data/reference/building_about.csv`, `realtor_lines.csv`, each with `facts_used_json`).
  `scripts/test_realtor_lines.py` re-checks every unit on the page.
- **Outside voices.** Attributed quotes are stored verbatim with a permalink and checked against the cached page
  (`scripts/verify_quotes.py`; the local-rules builders do the same for rule quotes).
- Order after a data rerun: `build_page_data.py` → `build_scene_text.py` → `check_scene_text.py` →
  `realtor_lines.py` → `test_realtor_lines.py` → `page_data_extras.py` → `build_site.py`.

## The page

- **Template**: `site/index.html`, one file with inline CSS and JavaScript (`docs/SITE_NOTES.md`). Layout and
  interaction patterns come from `site/mock4_reference.html` and `docs/NAV_PATTERNS.md`; no mock text is used.
- **Data injection**: the page reads `window.HOUSE_HUNT_DATA` when present and otherwise fetches `data.json` from its
  own folder. `build_site.py` fills `<!--HOUSE_HUNT_DATA_SLOT-->`, `<!--HOUSE_HUNT_MAP_BASE_SLOT-->` and
  `<!--HOUSE_HUNT_ILLUS_SLOT-->`, so the built file opens from disk with no second request. Nothing but
  `site/data.json` feeds the page.
- **Map**: inline SVG with no tiles or library (`docs/MAP_COMPONENT.md`). `scripts/build_map_base.py` builds
  `site/map_base.json` from Census county boundaries and water files; `site/map_component.html` is the standalone
  demo (`scripts/build_map_demo.py`).
- **Illustrations**: six original inline-SVG drawings, one per experience, from `scripts/build_illustrations.py` →
  `site/illustrations.json` (`docs/ILLUSTRATIONS.md`).
- **Structure**: experience → neighborhood → building (its apartments) → My list → compare. Presentation rules are in
  `CLAUDE.md`.
- **Shortlist tools** beside the page: `call_sheet.py`, `tour_days.py`, `recheck_shortlist.py`
  (`docs/SHORTLIST_TOOLS.md`); they read the pipeline's data and write under `out/`.

## What guards each stage

| Stage | Guard | Run by `run_all.py` |
|---|---|---|
| Text parsing behind every rule | `scripts/test_parsers.py` | yes, first |
| Gates, master, rent terms, cost, evidence rules, ranking | `scripts/test_rules.py` (pure cases) | yes, second |
| The same, on real output and on `site/data.json` | `scripts/test_rules.py --data` | yes, after `rank.py` |
| Every field wired or explained; analysis reads only master tables | `scripts/check_registry.py` | yes, last |
| Shown list obeys the gates; one open item at most; reviewed verdict | `scripts/check_registry.py` | yes, last |
| Stage counts and their change from the last run | `docs/RUN_REPORT.md`, `data/reference/run_history.csv` | yes |
| Scene text against the data | `scripts/check_scene_text.py` | no |
| Composed building and unit text | `scripts/test_realtor_lines.py` | no |
| The extras step and the publish step | `scripts/test_page_data_extras.py` | no |
| Quotes are verbatim on their cached page | `scripts/verify_quotes.py`, `local_rules_build.py` | no |
| Page behaviour, heights, built file equals served file | `scripts/site_walkthrough_test.js` | no |
| Map demo | `scripts/map_component_test.js` | no |
| Shortlist tools | `scripts/test_shortlist_tools.py` | no |
| Repository hygiene | `scripts/check_repo.py` | no |
| The whole list against live pages | independent checks, `docs/INDEPENDENT_CHECK*.md` | no (an agent) |
