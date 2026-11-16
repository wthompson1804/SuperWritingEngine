# Clean-up report (2026-11-16)

A documentation and hygiene pass made while five other agents were still working. Nothing was deleted, no data or
pipeline script was edited, the pipeline was not run, nothing was fetched, nothing was committed by this pass.

## 1. What changed

**New files**

| File | What it is |
|---|---|
| `README.md` | What this is, quick start, tests, where things live, counts as of 2026-11-16, environment, what is not automated |
| `docs/README.md` | Index of every document: current rules in authority order, how it works, checks and repairs in order, harvest notes, superseded |
| `docs/ARCHITECTURE.md` | Data flow diagram, one paragraph per stage, evidence batches, the verdict loop, scene text, the page, what guards each stage |
| `scripts/README.md` | Inventory of all 268 scripts: purpose, stage, inputs, outputs, run by `run_all`, tests, status |
| `scripts/check_repo.py` | Read-only hygiene check (output in section 7) |
| `docs/CLEANUP_REPORT.md` | This file |

**Rewritten**

| File | What changed |
|---|---|
| `CLAUDE.md` | Restructured from a chronological list into current rules (217 lines). The opening "data-collection pipeline, not an app … do not build UI, rank or recommend" is gone. Rules 1 to 14 kept; rules 9, 10, 11 and 14 reworded to today's state. Every owner decision is either a current rule or a row of the decision log at the end (35 rows: date, decision, what it replaces) |
| `docs/DATA_DICTIONARY.md` | Rewritten to the files that exist. The old version described `area_metrics.csv`, `buildings.csv`, `building_reviews.csv` and `quotes.csv`, none of which was ever built. Field-level detail points to `data/reference/field_registry.csv` |

**Appended**

| File | What changed |
|---|---|
| `docs/SOURCES.md` | One dated section at the end, "Collected addendum (2026-11-16)", with the source findings that agents' notes said they could not add (harvest notes, tool notes, the map and sub-city documents). Earlier sections untouched |
| `.gitignore` | Six patterns for new files only (section 3) |

**Moved with `git mv`**

| From | To | Why |
|---|---|---|
| `docs/PLAN_V2_UI_DATA_REQUIREMENTS.md` | `docs/archive/` | Plan v2, replaced by plan v3. Named by no document or script |
| `docs/TOOLS_AGENT_BRIEF.md` | `docs/archive/` | Brief for finished work. Named by no document or script |
| 43 screenshots: `site/screens/before-*.png` (19), `after-*.png` (22), `final_phone.png`, `final_desk.png` | `site/screens/archive/` | 15.1 MB. They show the design before the round-3 feedback (holding three, "Your host says", a ten-place list). No script writes them. Two documents this pass may not edit still mention the old location in passing: `docs/SITE_NOTES.md` line 180 and `docs/NAV_PATTERNS.md` line 13 |

Left in place although historical, because a current document or script names them: `docs/HANDOFF_2026-11-15.md`
(`PROGRESS.md`), `docs/PHASE1_AGENT_BRIEF.md` (plan v3), `docs/DATA_USE_AUDIT_2026-11-15.md` (plan v4),
`docs/LIFESTYLE_ANALYSIS.md` (`scripts/lifestyle_features.py`, `PROGRESS.md`). They are marked historical in `docs/README.md`.
`docs/CHECKPOINT_A.md` looks stale and is not: `scripts/build_neighborhoods.py` rewrites it on every full run.

## 2. Things that look like a secret

- **The Census API key is not in the repo.** Its exact value was searched for in every file under this folder,
  `raw/` included: no match.
- **A Google API key belonging to a third party is in two data files.** It is inside Street View image URLs that Trulia
  put in its own pages (column `photo_url`, host `maps.googleapis.com`), one distinct key:
  - `data/listings_raw/trulia.csv`: 268 lines, the first at lines 62, 92, 127, 128, 166, 227, 228, 229
  - `data/listings.csv`: 240 lines, the first at lines 11963, 12480, 12536, 12546, 12547, 12749, 12864, 12961
  It is Trulia's public browser key, not ours, and it is not in `site/data.json` or the built page. It is still a
  key-shaped string in a pushed repo, and a secret scanner will flag it. Fix when the data files are free: have
  `scripts/h_trulia.py` or `scripts/gates.py` drop the `key=` parameter from `photo_url` (the page links out for photos
  and does not use this column).
- Nothing else matched: no private key block, no AWS, GitHub, Slack or `sk-` style token, no token assigned in code.
- `.gitignore` already keeps raw HTML, JS and CSS captures out because third-party pages embed their own tokens.
  JSON, JSONL and XML captures under `raw/` are tracked (329 MB) and were **not** scanned for pattern matches, only for
  our own key: third-party tokens inside them are likely.

## 3. `.gitignore` additions, and what I would untrack

Added (they only keep new files out; nothing was untracked, `git rm` was not run):

```
data/house_hunt.sqlite          # optional database from scripts/build_sqlite.py
site/screens/archive/           # superseded review screenshots
raw/census_cb/*.zip             # re-created by scripts/build_map_base.py
raw/census_areawater/*.zip      # re-created by scripts/build_map_base.py
.DS_Store  *.swp  *.tmp  .pytest_cache/  node_modules/
```

The folder tracks 34,416 files, 812 MB on disk: `raw/` 513 MB, `data/` 220 MB, `site/` 68 MB. Candidates to untrack
with `git rm --cached` (files stay on disk), safest first:

| What | Files | Size | Safe because | Caution |
|---|---|---|---|---|
| `site/screens/archive/` | 43 | 15.1 MB | Superseded design; already ignored for new files | None |
| `raw/census_cb/`, `raw/census_areawater/` zips | 82 | 30.3 MB | `scripts/build_map_base.py` re-downloads them; www2.census.gov has never refused | Needs network to rebuild the map base |
| `raw/subcity_split/*.zip` | 3 | 7.6 MB | `scripts/build_subcity_neighborhoods.py` re-downloads them | Same |
| `site/dist/index.html`, `site/dist/artifact.html` | 2 | 12.4 MB | Rebuilt by `build_site.py` and `build_artifact.py` from tracked inputs | Each rebuild adds 12 MB to history; untrack only if the published copy is kept elsewhere |
| `site/screens/audit_*.png` | 23 | 17.3 MB | Review screenshots of one audit; one file alone is 8.1 MB | **In use today** by the accessibility audit. Untrack after that review closes |
| Other `site/screens/*.png` | 80 | 15.3 MB | Rewritten by `site_walkthrough_test.js`, `map_component_test.js`, `build_illustrations.py` | Several documents point at them; keep the ones named in `docs/ILLUSTRATIONS.md`, `MAP_COMPONENT.md`, `NAV_PATTERNS.md` |
| `data/excluded_*.csv` | 5 | 4.2 MB | Rewritten by `rank.py` on every run; each row repeats all 510 master columns | The run report reads two of them: keep on disk |
| `data/reference/detail_targets_*.csv` | 16 | 0.4 MB | No script reads them | Delete candidates, see section 5 |
| `raw/pluto_pages/` | 5 | 23.1 MB | NYC Open Data bulk pages; `enrich_nyc_pluto.py` can refetch | A full run without them needs network |
| `raw/zumper/cards.jsonl` | 1 | 38.2 MB | — | **Do not untrack**: the only copy of the Zumper search cards, and Zumper could refuse a second harvest |
| `data/enriched/`, `data/enriched_color/` | 1,362 | 74.5 MB | — | **Do not untrack**: scene text and the master tables read them, and rebuilding needs OSRM and the lookup caches |

Not safe to regenerate, so not proposed: `raw/nys_register/` (30.9 MB, the toll source that was hard to find),
`raw/gtfs/` (the NJ Transit mirror feed has ended), `raw/osrm/`, `raw/census_geocoder/`, every listing-site capture.

**History is the larger problem.** `.git` holds about 915 MB of loose objects after 233 commits, because every pipeline
run rewrites `data/master_units.csv` (19.9 MB), `data/units.csv` (10.8 MB), `data/ranked_units.csv` (7.6 MB),
`site/data.json` (7.2 MB) and `site/dist/*` (12.4 MB), and "work in progress" sweeps commit each version. Untracking
does not shrink history. Sweep less often, or commit generated tables only at checkpoints.

## 4. Contradictions between documents

Resolved in `CLAUDE.md` by "the later decision wins"; the stale statement is still in a file this pass may not edit.

| # | Statement A | Statement B | Current | Stale text is in |
|---|---|---|---|---|
| 1 | At most 2 units per building (`docs/RANKING.md` lines 15, 83 and 131; `scripts/rank.py` docstring line 14) | Up to 8 per building (`docs/RANKING.md`, last section, added during this pass; `rank.py` `MAX_PER_BUILDING = 8`; owner, 2026-11-16) | 8 shown; 2 in candidate and phone lists | Earlier sections of `docs/RANKING.md` (chronological by design), `rank.py` docstring |
| 2 | "Top 10 per neighborhood" (`rank.py` docstring; the stage label in `run_all.py`, so also `docs/RUN_REPORT.md` and the column name in `run_history.csv`; `CLAUDE.md` before this pass) | No cap of 10 (`docs/RANKING.md`, owner 2026-11-16) | No cap | `run_all.py` label, `rank.py` docstring |
| 3 | Move-in by December 1 (`PROGRESS.md`, "Answers from Will" table: "must be available on or before Dec 1") | Through December 15 (`PROGRESS.md` log, plan v3, `check_registry.py` `WINDOW_END`) | December 15 | `PROGRESS.md` answers table |
| 4 | Tiers comfortable / at_cap / stretch (`PROGRESS.md` answers table) | Tiers superseded (`CLAUDE.md` before this pass) | No tiers; nothing above $3,000 | `PROGRESS.md` answers table |
| 5 | Dog weight limit must be ≥ 40 lb (`docs/EVIDENCE_AGENT_BRIEF.md` section 2; `docs/RANKING.md` v2 dog part scores "weight limit stated ≥ 40 lb") | ≥ 25 lb (owner, 2026-11-15; the brief's own addendum) | Gate is 25 lb. Whether the **score** should still reward 40 lb is not stated anywhere | Brief section 2; see section 8 |
| 6 | Experience figures are "medians, never ranges or averages" (old `CLAUDE.md`, page voice) | "Median as the headline with the range in small text beneath" (old `CLAUDE.md`, next paragraph) | The second, as the later one | Was inside `CLAUDE.md`; logged |
| 7 | `scripts/page_data_extras.py` docstring: "the checker [`check_scene_text.py`] is run by run_all" | `run_all.py` does not run it | Not run by `run_all` | `page_data_extras.py` docstring |
| 8 | `scripts/check_registry.py` docstring: "Runs first in scripts/run_all.py" | It runs last | Last | `check_registry.py` docstring |
| 9 | `scripts/avoid.py` docstring lists the output `data/evidence_summary.csv` | The script does not write it and the file does not exist | Not written | `avoid.py` docstring |
| 10 | `docs/SOURCES.md` sections 2 and "Implications": Greystar needs a browser; Craigslist HTML is "practical" | Greystar is plain HTML (`harvest_notes/mgmt.md`); Craigslist is off limits for scripts (its own later addendum) | The later findings | Top of `docs/SOURCES.md`; corrected in the new addendum |
| 11 | `PROGRESS.md` log: Niche and City-Data are off limits | `docs/SOURCES.md` late addendum (approved by Will): usable for targeted lookups | Usable for targeted lookups only | `PROGRESS.md` log line |
| 12 | A dog policy that conflicts between sources is a **drop** (`avoid.py` docstring) / makes the listing **sketchy** (`RANKING.md` v2) | It is **one open fact**, and the building's own site outranks an aggregator (`RANKING.md`, "After the independent check") | Not clear which applies when; all three texts are live | See section 8 |
| 13 | `docs/SAFETY_BASIS.md` title says "draft for Will's approval", and its first rule block says property crime is "flagged, not cut" | The same file, further down, and `PROGRESS.md`: neither violent nor property crime may exceed Jamaica's | Final, both rates | Title and first rule block of `docs/SAFETY_BASIS.md` |
| 14 | `PROGRESS.md` status table: "Trulia: … about 100 NYC shown units cannot be re-checked"; "507 reviewed verdicts"; "890 quotes, 53 later neighborhoods have none" | `PROGRESS.md` current state: 217 Trulia rows; 792 verdict rows; round 2 added 507 quotes | The "Current state" paragraphs | `PROGRESS.md` status table |
| 15 | `docs/PLAN_V3_APPROVED_2026-11-15.md` names `scripts/build_page.py`, `scripts/validate.py`, `scripts/add_manual_listing.py`, `data/buildings.csv`, `data/evidence.csv`, `docs/SYNTHESIS_RULES.md` | None exists; the work was done under other names (`build_page_data.py`, `check_registry.py`, `h_manual.py`, `master_buildings.csv`, `data/evidence/`) | The names in `docs/ARCHITECTURE.md` | Plan v3 (kept as approved) |
| 16 | `PROGRESS.md` "Run everything" stops at `build_site.py` | The publish step is `scripts/build_artifact.py` (added today) | Five steps, as in `README.md` | `PROGRESS.md` |

## 5. Dead, superseded and orphaned code and data

Full table in `scripts/README.md` ("Dead, superseded and unreferenced scripts"). Nothing was deleted.

- **Dead**: `scripts/h_craigslist.py` (must not be run: terms of use).
- **Superseded**: `scripts/rank_v1_backup.py`; the phase-1 set `build_area_metrics.py`, `p1_acs.py`, `p1_rents.py`,
  `p1_walkability.py`, `p1_protections_fetch.py`, `p1_drive_fetch.py` (`p1_safety_nyc.py` and `p1_transit_feeds.py`
  are still imported by the lookup tools); `build_targets.py`.
- **Dormant**: `scripts/build_sqlite.py` (nothing reads the database), `scripts/tools/taxes_reference.py`
  (`data/reference/taxes.csv` is read by nothing).
- **Finished one-off helpers named nowhere**: 19 evidence-batch helpers (`ev_b1_*`, `ev_batch2_*`, `ev9_*`,
  `ev12_zumper_reviews.py`, `ev13_zumper_reviews.py`) and 8 region helpers. About 160 batch and region helpers in all
  are copies of one another with a batch number changed (several still say "Evidence batch 6" in the docstring of a
  later batch). Recommendation: after the search closes, move `ev*`, `evidence_b*` and `h_region_*` into
  `scripts/harvest_done/`. Not now: `ev11_text.py`, `ev6_fetch.py`, `h_trulia.py`, `h_zumper.py`, `h_apartmentlist.py`
  and `h_mgmt_common.py` are imported by other scripts, so a move needs the imports fixed.
- **Scratch**: `scripts/.p5_shoot.js`, `.p5_one.js`, `.p5_sizes.js` (hidden screenshot helpers of a page agent that was
  still working during this pass; named nowhere). Delete when that agent is done.
- **Orphaned data** (no script names it): `data/reference/detail_targets_*.csv` (16 files, 0.4 MB),
  `data/lifestyle_indices.csv`, `data/lifestyle_loadings.csv`, `data/reference/ratings_census_targets.csv` (an input
  the ratings agents read by hand: keep), `data/metrics/*.csv` and `data/areas.csv` (phase 1, 16 MB, read only by
  phase-1 scripts), `data/reference/neighborhood_summaries*.csv` (written, never read).
- **Stale site files**: `site/pattern_demo.html` and `site/illustrations_preview.html` are review pages, not linked
  from the page; `site/mock4_reference.html` is the layout reference. All small; keep.

Recommended deletions, once the owner agrees (total under 1 MB of code and data, 15 MB of screenshots):
`data/reference/detail_targets_*.csv`, `scripts/build_targets.py`, `scripts/.p5_*.js`,
`data/lifestyle_indices.csv`, `data/lifestyle_loadings.csv`, `site/screens/archive/`.

## 6. Risks

1. **Generated tables are committed on every sweep** (section 3). The repo grows by tens of megabytes per run.
2. **Two documents describe the same rules** now: `CLAUDE.md` (as they stand) and `docs/RANKING.md` (chronological).
   `RANKING.md` is correct only when read from the bottom up: three earlier sections still say 2 per building, and its
   first section still describes ranking v1. One line at its top saying "later sections replace earlier ones" would help.
3. **`PROGRESS.md` mixes current paragraphs with a stale status table and a stale answers table** (contradictions 3, 4,
   11, 14, 16). A reader who stops at the tables gets the wrong move-in date.
4. **`scripts/check_scene_text.py` is not part of `run_all.py`**, so scene text can drift from the data silently; the
   extras step attaches prose whenever the text is non-empty. `PROGRESS.md` recorded 5 failing rows at one point.
5. **The third-party Google key** in two tracked CSVs (section 2).
6. **`data/evidence/call_answers.csv` does not exist** but seven documents and the code treat it as the highest
   authority. The first file anyone creates there changes what is shown; its format is only in `docs/SHORTLIST_TOOLS.md`.
7. **Helper scripts can still send requests to refused hosts.** `h_trulia.py`, `voices_fetch.py` and the `ev*_fetch`,
   `ev*_trulia*` helpers have no shared kill list; only the later scripts read `raw/_host_kill_shared.json`.
   `scripts/README.md` marks them "do not rerun".
8. **This pass ran beside five agents.** Counts in `README.md` are from `PROGRESS.md` as it stood (489 shown); the
   run history moved from 347 to 513 to 489 shown while the pass was running. `docs/RUN_REPORT.md` is the live figure.
9. `scripts/check_repo.py` check 3 counts a script as "named" when any document mentions it, including the new
   inventories in `docs/DATA_DICTIONARY.md`. `scripts/README.md` is excluded from that test; the dictionary is not.

## 7. Output of `python3 scripts/check_repo.py --max 40` (2026-11-16)

```
check_repo: /home/user/SuperWritingEngine/house-hunt
tracked files under this folder: 34416; on disk 812 MB

== 1. Tracked files over 5 MB ==
  28 files, 283.8 MB in all
     38.2 MB  raw/zumper/cards.jsonl
     23.8 MB  data/listings.csv
     18.7 MB  data/master_units.csv
     14.1 MB  data/metrics/acs.csv
     12.1 MB  raw/pluto_pages/f4e54a6f0df52a4d.json
     12.0 MB  raw/neighborhood_descriptions_round2/candidates.json
     11.6 MB  raw/census_cb/a31400440e704704.zip
     11.0 MB  raw/pluto_pages/6a917c933cbba966.json
     10.2 MB  data/units.csv
      9.2 MB  raw/trulia/_state.json
      8.6 MB  data/listings_raw/trulia.csv
      8.4 MB  raw/nys_register/d93a373458ec6ef7.pdf
      8.3 MB  raw/gas_tariffs/5db8f28c52c4a9ce.pdf
      7.6 MB  site/data.json
      7.6 MB  data/ranked_units.csv
      7.6 MB  data/evidence/nyc_records.csv
      7.5 MB  raw/mgmt_greystar/render/p_21088.xhr.json
      7.1 MB  raw/subcity_split/6ad749b6aa70a7a0.zip
      6.8 MB  raw/apartmentlist/725aaa0cfc26e780.xml
      6.7 MB  raw/apartmentlist/07fedfac6e59d27a.xml
      6.5 MB  site/dist/index.html
      6.2 MB  site/dist/artifact.html
      6.2 MB  data/listings_raw/apartmentlist.csv
      5.8 MB  raw/nys_register/8ee4f186bd3e60ba.pdf
      5.6 MB  raw/gtfs/gtfs_subway.zip
      5.5 MB  raw/gtfs/njt_rail.zip
      5.5 MB  raw/local_rules/text/9fa6a7888c9ff096.txt
      5.3 MB  raw/nys_register/29d6cc332b9f0a76.pdf

== 2. CSVs under data/ that no script names (by file name, numbered family or folder) ==
  280 CSVs checked; 7 are named only through their folder; 18 are named nowhere in scripts/
        22 KB  data/lifestyle_indices.csv
         0 KB  data/reference/detail_targets_anninlofts_com.csv
        57 KB  data/reference/detail_targets_apartmentlist_com.csv
         6 KB  data/reference/detail_targets_avaloncommunities_com.csv
         1 KB  data/reference/detail_targets_bltliveworkplay_com__sightmap_embed_.csv
        23 KB  data/reference/detail_targets_fairfieldproperties_com.csv
        13 KB  data/reference/detail_targets_gardencommunities_com.csv
         1 KB  data/reference/detail_targets_gardenhomesmanagement_com.csv
         0 KB  data/reference/detail_targets_gdcrentals_com.csv
         4 KB  data/reference/detail_targets_greystar_com.csv
         0 KB  data/reference/detail_targets_solvermella_com.csv
       229 KB  data/reference/detail_targets_trulia.csv
         0 KB  data/reference/detail_targets_vermellacrossing_com.csv
         0 KB  data/reference/detail_targets_vermellaharrison_com.csv
         0 KB  data/reference/detail_targets_vermellawoodbridge_com.csv
         0 KB  data/reference/detail_targets_www_shoregateli_com__sightmap_embed_.csv
        69 KB  data/reference/detail_targets_zumper.csv
        64 KB  data/reference/ratings_census_targets.csv

== 3. Scripts no other file references ==
  271 scripts; 35 named by no script and no document (README inventories do not count); 108 named only by a document (run by hand)
  -- named nowhere:
  scripts/.p5_one.js
  scripts/.p5_shoot.js
  scripts/.p5_sizes.js
  scripts/build_area_metrics.py
  scripts/build_search_grid.py
  scripts/ev12_zumper_reviews.py
  scripts/ev13_zumper_reviews.py
  scripts/ev9_al_parse.py
  scripts/ev9_grep.py
  scripts/ev9_trulia_parse.py
  scripts/ev_b1_al.py
  scripts/ev_b1_al_write.py
  scripts/ev_b1_art.py
  scripts/ev_b1_probe.py
  scripts/ev_b1_summ.py
  scripts/ev_b1_trulia.py
  scripts/ev_b1_zumper.py
  scripts/ev_batch2_al.py
  scripts/ev_batch2_confirm.py
  scripts/ev_batch2_facts.py
  scripts/ev_batch2_items.py
  scripts/ev_batch2_live.py
  scripts/ev_batch2_other.py
  scripts/ev_batch2_sites.py
  scripts/h_region_connecticut_probe.py
  scripts/h_region_connecticut_sites.py
  scripts/h_region_connecticut_text.py
  scripts/h_region_westchester_rockland_grep.py
  scripts/h_region_westchester_rockland_probe.py
  scripts/h_region_westchester_rockland_trulia_zip.py
  scripts/h_region_westchester_rockland_zb.py
  scripts/h_region_westchester_rockland_zumper.py
  scripts/p1_protections_fetch.py
  scripts/p1_rents.py
  scripts/p1_walkability.py
  -- named only in documents:
  scripts/build_map_demo.py   <- ARCHITECTURE.md, MAP_COMPONENT.md
  scripts/build_sqlite.py   <- DATA_DICTIONARY.md
  scripts/build_subcity_neighborhoods.py   <- SOURCES.md, SUBCITY_SPLIT_PLAN.md
  scripts/build_targets.py   <- DATA_DICTIONARY.md
  scripts/ev10_al_parse.py   <- evidence_batch_10.md
  scripts/ev10_fetch.py   <- evidence_batch_10.md
  scripts/ev10_links.py   <- evidence_batch_10.md
  scripts/ev10_site.py   <- evidence_batch_10.md
  scripts/ev10_trulia_parse.py   <- evidence_batch_10.md
  scripts/ev10_write.py   <- evidence_batch_10.md
  scripts/ev10_zumper.py   <- evidence_batch_10.md
  scripts/ev11_fetch.py   <- evidence_batch_11.md
  scripts/ev11_site.py   <- evidence_batch_11.md
  scripts/ev11_write.py   <- evidence_batch_11.md
  scripts/ev12_grep.py   <- evidence_batch_12.md
  scripts/ev12_text.py   <- evidence_batch_12.md
  scripts/ev12_write.py   <- evidence_batch_12.md
  scripts/ev12_zumper.py   <- evidence_batch_12.md
  scripts/ev13_al_parse.py   <- evidence_batch_13.md
  scripts/ev13_fetch.py   <- evidence_batch_13.md
  scripts/ev13_grep.py   <- evidence_batch_13.md
  scripts/ev13_trulia_parse.py   <- evidence_batch_13.md
  scripts/ev13_write.py   <- evidence_batch_13.md
  scripts/ev13_zumper.py   <- evidence_batch_13.md
  scripts/ev14_show.py   <- evidence_batch_14.md
  scripts/ev14_site.py   <- evidence_batch_14.md
  scripts/ev14_write.py   <- evidence_batch_14.md
  scripts/ev15_al_parse.py   <- evidence_batch_15.md
  scripts/ev15_fetch.py   <- evidence_batch_15.md
  scripts/ev15_igloo.py   <- evidence_batch_15.md
  scripts/ev15_site.py   <- evidence_batch_15.md
  scripts/ev15_trulia_parse.py   <- evidence_batch_15.md
  scripts/ev15_write.py   <- evidence_batch_15.md
  scripts/ev15_zumper.py   <- evidence_batch_15.md
  scripts/ev16_fetch.py   <- evidence_batch_16.md
  scripts/ev16_igloo.py   <- evidence_batch_16.md
  scripts/ev16_site.py   <- evidence_batch_16.md
  scripts/ev16_trulia_parse.py   <- evidence_batch_16.md
  scripts/ev16_write.py   <- evidence_batch_16.md
  scripts/ev16_zumper_reviews.py   <- evidence_batch_16.md
  ... and 68 more (run with --max 0 for all)

== 4. Documents that name a file which does not exist ==
  29 missing references in 13 documents (first line of each shown)
  docs/DATA_DICTIONARY.md:63  ->  data/house_hunt.sqlite
  docs/HANDOFF_2026-11-15.md:158  ->  docs/COVERAGE.md
  docs/HANDOFF_2026-11-15.md:159  ->  docs/CONFLICTS.md
  docs/HANDOFF_2026-11-15.md:160  ->  docs/FINDINGS.md
  docs/PLAN_V3_APPROVED_2026-11-15.md:70  ->  data/buildings.csv
  docs/PLAN_V3_APPROVED_2026-11-15.md:74  ->  scripts/add_manual_listing.py
  docs/PLAN_V3_APPROVED_2026-11-15.md:94  ->  data/evidence.csv
  docs/PLAN_V3_APPROVED_2026-11-15.md:95  ->  docs/SYNTHESIS_RULES.md
  docs/PLAN_V3_APPROVED_2026-11-15.md:101  ->  scripts/build_page.py
  docs/PLAN_V3_APPROVED_2026-11-15.md:110  ->  scripts/validate.py
  docs/RANKING.md:167  ->  data/evidence/call_answers.csv
  docs/README.md:17  ->  data/buildings.csv
  docs/README.md:17  ->  scripts/build_page.py
  docs/README.md:17  ->  scripts/validate.py
  docs/README.md:37  ->  data/evidence/call_answers.csv
  docs/RUN_REPORT.md:198  ->  data/evidence/call_answers.csv
  docs/SHORTLIST_TOOLS.md:55  ->  data/evidence/call_answers.csv
  docs/SHORTLIST_TOOLS.md:84  ->  out/call_answers_by_listing.csv
  docs/SHORTLIST_TOOLS.md:92  ->  out/shortlist.txt
  docs/harvest_notes/building_contacts.md:85  ->  raw/building_contacts/_refused_hosts.json
  docs/harvest_notes/trulia.md:4  ->  raw/trulia/_blocks.log
  docs/harvest_notes/zumper.md:149  ->  raw/zumper/BLOCKED.txt
  README.md:111  ->  data/evidence/call_answers.csv
  CLAUDE.md:119  ->  data/evidence/call_answers.csv
  scripts/README.md:44  ->  data/area_metrics.csv
  scripts/README.md:46  ->  data/house_hunt.sqlite
  scripts/README.md:48  ->  data/listings_raw/mgmt_windsor.csv
  scripts/README.md:114  ->  data/evidence/call_answers.csv
  scripts/README.md:199  ->  data/metrics/rent.csv

== 5. Strings that look like an API key or token (outside raw/; values are never printed) ==
  local Census key file: present, its exact value is searched for
  2083 text files read
  -- the exact local Census key:
  none
  -- pattern matches (file: kind: line numbers; most are a third-party site's own public key inside a stored URL):
  data/listings.csv: Google API key: lines 11963, 12480, 12536, 12546, 12547, 12749, 12864, 12961 ... (240 lines)
  data/listings.csv: key or token in a URL: lines 11963, 12480, 12536, 12546, 12547, 12749, 12864, 12961 ... (240 lines)
  data/listings_raw/trulia.csv: Google API key: lines 62, 92, 127, 128, 166, 227, 228, 229 ... (268 lines)
  data/listings_raw/trulia.csv: key or token in a URL: lines 62, 92, 127, 128, 166, 227, 228, 229 ... (268 lines)
```

Reading the output: check 4's hits on `data/evidence/call_answers.csv`, `data/house_hunt.sqlite`,
`data/area_metrics.csv`, `data/metrics/rent.csv` and `data/listings_raw/mgmt_windsor.csv` are documents saying, on
purpose, that the file does not exist. The real broken references are those in plan v3, the handoff brief,
`docs/SHORTLIST_TOOLS.md` (`out/shortlist.txt`, `out/call_answers_by_listing.csv`: example names) and three harvest
notes that name block-marker files which were never written.

## 8. Could not resolve: for the owner

1. **Dog score at 40 lb.** The gate is 25 lb. Ranking v2's dog part still gives credit for "weight limit stated ≥ 40
   lb" (`docs/RANKING.md`). Intended (a roomier policy is better), or a leftover? Left as it is.
2. **Conflicting dog policy**: drop, sketchy, or one open fact (contradiction 12)? `CLAUDE.md` points to
   `docs/RANKING.md` and does not pick.
3. **Niche quotes after the 403.** `PROGRESS.md` says the 21 neighborhoods' quotes fetched after the voices agent
   restarted are "kept pending Will's call". No answer is recorded. They are on the page.
4. **Wikipedia text from the dump** after the live API refused us: `docs/harvest_notes/neighborhood_descriptions.md`
   asks whether the one-refusal rule covers every Wikimedia host. No answer is recorded. 272 of 274 round-1
   descriptions depend on it.
5. **Plan v3's checkpoints** B (avoid list) and C (draft page): no record that they happened, and the latest
   instruction says Lamia will not be asked to react before the page is finished. `CLAUDE.md` no longer lists the
   checkpoints as a rule; say if they should come back.
6. **Avoid cards**: "up to 5 per neighborhood" is still in the code (`rank.py`), while the cap of 10 places was
   lifted. Kept as a rule in `CLAUDE.md`; confirm it should stay.
7. **The Trulia test on November 16** that `PROGRESS.md` mentions ("no Trulia requests until a single test on Nov
   16"): no record of whether it ran. `CLAUDE.md` says: send no Trulia requests.
8. **Visit frequency** (weekly, assumed) and `si-inventory.csv` (never uploaded) are still open in `PROGRESS.md`.
9. `docs/SITE_NOTES.md` line 180 and `docs/NAV_PATTERNS.md` line 13 name the screenshots that moved to
   `site/screens/archive/`. Those files were outside this pass's fence.
