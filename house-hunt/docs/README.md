# Index of documents

Written 2026-11-16. Start with `../CLAUDE.md` (rules for agents) and `../PROGRESS.md` (current state). This index says
which document answers which question, and which ones are history. Run `python3 scripts/check_repo.py` to find
documents that name files which no longer exist.

## 1. Current rules, in authority order

A later document wins where two disagree. Inside `RANKING.md`, later sections replace earlier ones.

| Order | Document | What it decides |
|---|---|---|
| 1 | `../CLAUDE.md` | The owner's decisions as they stand today: working rules, source rules, gates, presentation, standing instructions, and a log of what replaced what |
| 2 | `RANKING.md` | Gate facts and what settles them, open items and disclosures, scoring (v2), selection, staleness, elevator grading, phone answers, tolls. Its sections are chronological; read from the bottom up |
| 3 | `PLAN_V4_MASTER_MODEL_2026-11-15.md` | The master-table model: one connected data model, the field registry, the run report |
| 4 | `SAFETY_BASIS.md` | The crime yardsticks and the Jamaica safety rule (its header still says "draft"; the rule was made final on 2026-11-15, see `../PROGRESS.md`) |
| 5 | `PLAN_V3_APPROVED_2026-11-15.md` | The gates and the avoid thresholds as first approved. Amended since: dog limit 25 lb, no cap of 10, "hold three" replaced by My list (see the decision log in `../CLAUDE.md`). It names files that were never created (`data/buildings.csv`, `scripts/build_page.py`, `scripts/validate.py`, …) |
| 6 | `UX_BRIEF_2026-11-15.md` | Who the page is for and how it should feel. Layout authority only, with mock-up 4; its "no red or green on distance" was replaced |
| — | `SOURCES.md` | Which sources may be used and how. The addenda at the end are newer than the tables at the top |
| — | `../PROGRESS.md` | Current counts, what is weak, what is open |

## 2. How it works

| Document | What it covers |
|---|---|
| `../README.md` | What this is, quick start, tests, environment, what is not automated |
| `ARCHITECTURE.md` | Data flow, one paragraph per stage, the evidence-batch method, the review-verdict loop, the scene-text system, the page, what guards each stage |
| `DATA_DICTIONARY.md` | Every data file: what a row is, its key, who writes and reads it; the shape of `site/data.json` |
| `../scripts/README.md` | Every script: purpose, stage, inputs, outputs, tests, status |
| `RUN_REPORT.md` | Written by `scripts/run_all.py` on every run: stage counts, why units left, fill rates. Do not edit |
| `CHECKPOINT_A.md` | Written by `scripts/build_neighborhoods.py` on every full run: neighborhoods and cluster traits. Do not edit |
| `SITE_NOTES.md` | The page template: structure, data it reads, what each pass changed |
| `NAV_PATTERNS.md` | Navigation patterns behind the collapse-to-headlines page, with a tested demo |
| `MAP_COMPONENT.md` | The inline-SVG map: files, API, base geometry sources, limits |
| `ILLUSTRATIONS.md` | The six experience drawings and how they are built |
| `SCENE_TEXT_NOTES.md` | How the written text is tied to the data: drafts, tokens, checker, house style |
| `SHORTLIST_TOOLS.md` | Call sheet, tour days, re-check; the format of `data/evidence/call_answers.csv` |
| `SUBCITY_SPLIT_PLAN.md` | How Jersey City was split into neighborhoods (adopted 2026-11-16; Newark prepared, not adopted) |
| `RATING_STANDARD.md` | The rating screen for buildings outside New York City. Written by `scripts/rating_standard.py` |
| `tools_notes/` | One note per lookup tool: `crime.md`, `drive.md`, `mta_tolls.md`, `places.md`, `transit.md`, `utilities.md` |

Briefs given to agents (still the contract if that kind of work is run again):
`HARVEST_AGENT_BRIEF.md` (listing harvests), `REGION_AGENT_BRIEF.md` (building-first region passes),
`EVIDENCE_AGENT_BRIEF.md` (evidence batches; its "≥ 40 lb" line is corrected to 25 lb in its own addendum),
`RATINGS_CENSUS_BRIEF.md` (ratings census).

## 3. Checks and repairs, in order

| When (UTC) | Document | What happened |
|---|---|---|
| 2026-11-15 | `DATA_USE_AUDIT_2026-11-15.md` | Audit of data collected and not used. Led to plan v4 |
| 2026-11-15, 21:20 | `INDEPENDENT_CHECK.md` | First independent check of the master tables (W1–W20, A1–A25) |
| 2026-11-15, 22:44 | `REPAIRS_AFTER_INDEPENDENT_CHECK.md` | Repairs: `parsers.py`, `test_parsers.py`, shown-list assertions |
| 2026-11-15, 23:05 | `INDEPENDENT_CHECK_2.md` | Second check of the shown list (D1–D21) |
| 2026-11-16 | `REPAIRS_AFTER_INDEPENDENT_CHECK_2.md` | Repairs: reviewed verdicts, `test_rules.py`; open decisions that later became rules |
| 2026-11-16 | `INDEPENDENT_CHECK_3.md` | Third check: the shown list and the page text (D1–D27) |
| 2026-11-16 | `PENDING_FIXES.md` | Fixes queued while check 3 was running |
| 2026-11-16 | `REPAIRS_AFTER_INDEPENDENT_CHECK_3.md` | Repairs: several verdict kinds per unit, pet-rent estimate, elevator doubt table, 8 per building, figures over shown units |
| 2026-11-16 | `A11Y_READABILITY_AUDIT.md` | Accessibility, readability and flow audit of the page |
| 2026-11-16 | `CLEANUP_REPORT.md` | This clean-up pass: what moved, what to untrack, contradictions between documents, dead code |

## 4. Harvest notes (`harvest_notes/`)

One note per harvest or evidence agent: what was fetched, what was blocked, what is weak. Written once; not updated.

| Group | Notes |
|---|---|
| Listing harvests | `zumper.md`, `trulia.md`, `apartmentlist.md`, `craigslist.md` (not run: terms of use), `mgmt.md`, `manual.md`, `zumper_open_pending.md` (not merged) |
| Region passes | `region_connecticut.md`, `region_mid_hudson.md`, `region_nassau.md`, `region_suffolk.md`, `region_westchester_rockland.md` |
| Evidence batches | `evidence_batch_1.md` … `evidence_batch_17.md`, `evidence_batch_19.md`; batch 18 is `resolve_pending_thin_years.md` |
| Records and ratings | `nyc_records.md`, `non_nyc_records.md`, `ratings_census_part1.md` … `part3.md` |
| Building facts and contacts | `building_amenities.md`, `community_facts.md`, `building_contacts.md`, `building_contacts_own_site.md`, `rent_terms.md` (rewritten by `scripts/rent_terms.py` on every run) |
| Neighborhood text | `local_rules.md`, `local_rules_round2.md`, `neighborhood_descriptions.md`, `neighborhood_descriptions_round2.md`, `voices.md`, `voices_round2.md` |

Source findings from these notes are collected in `SOURCES.md` (addendum of 2026-11-16).

## 5. Superseded and historical

Kept in place because a current document or a script still names them:

| Document | Status |
|---|---|
| `HANDOFF_2026-11-15.md` | The original brief, verbatim. Still the description of who Lamia is and of the Staten Island seed facts (§10). Its scope ("data collection only; do not build UI, rank or recommend"), tiers, $2,800 cap, 98-area list and phases are superseded |
| `PHASE1_AGENT_BRIEF.md`, `phase1_notes/acs.md` | Phase 1 measured 98 fixed areas. Replaced by per-building lookup tools (plan v3) |
| `LIFESTYLE_ANALYSIS.md` | Interim grouping analysis of 2026-11-15. The approved groups are in `scripts/lifestyle_groups.py` |
| `DATA_USE_AUDIT_2026-11-15.md` | Answered by plan v4; kept as the reason for it |

Moved to `archive/` on 2026-11-16 (no current document or script names them):

| Document | Why |
|---|---|
| `archive/PLAN_V2_UI_DATA_REQUIREMENTS.md` | Plan v2 (December 1 move-in, three floors and a table, four sliders). Replaced by plan v3 |
| `archive/TOOLS_AGENT_BRIEF.md` | Brief for the agents that built the lookup tools. The tools are built; their notes are in `tools_notes/` |
