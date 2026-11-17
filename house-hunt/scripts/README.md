# scripts/

Inventory of every script in this folder as of 2026-11-16, with the concierge-page scripts and live-check batch 21 added on
2026-11-17 (see "Added 2026-11-17" under the inventory heading) (268 Python and JavaScript files on 2026-11-16, plus this README;
the hidden `.p5_*.js` files are scratch screenshot helpers of a page agent that was still working, and are not counted).
How the stages fit together is in `docs/ARCHITECTURE.md`; the rules they enforce are in `docs/RANKING.md` and the plan documents.

## How to read the tables

- **Run by `run_all`**: `scripts/run_all.py` runs the tests, then (full run only) gates → PLUTO → gates → lookup tools → neighborhoods → lifestyle → crime benchmarks → groups, then always amenities → master → rent terms → all-in → evidence rules → rank → output tests → registry check. `--fast` skips the full-run block. The three page steps (`build_page_data.py`, `page_data_extras.py`, `build_site.py`) are run by hand after it. `build_artifact.py` is the publish step (`site/dist/artifact.html`).
- **Status**
  - **active**: part of the pipeline, a library it imports, a test, or a tool meant to be rerun.
  - **one-off harvest (done)**: fetched or assembled a data file once. The data file is the product. Most need the network; check `docs/SOURCES.md` and the one-refusal rule before rerunning any of them.
  - **superseded**: replaced by a later script or a later model; kept for history.
  - **dead**: must not be run.
- "Referenced by nothing" means no other script imports or names it and no document names it (found by `scripts/check_repo.py`, check 3).

## Run by hand

```
python3 scripts/run_all.py              # full pipeline, writes docs/RUN_REPORT.md
python3 scripts/run_all.py --fast       # after evidence-only changes
python3 scripts/build_page_data.py      # site/data.json
python3 scripts/page_data_extras.py     # adds text, contacts, ratings, links
python3 scripts/build_site.py           # site/dist/index.html
python3 scripts/build_artifact.py       # site/dist/artifact.html, the file that is published

python3 scripts/test_parsers.py
python3 scripts/test_rules.py           # add --data to check the pipeline's output
python3 scripts/test_realtor_lines.py
python3 scripts/test_shortlist_tools.py
python3 scripts/test_page_data_extras.py
python3 scripts/check_scene_text.py
python3 scripts/check_repo.py           # read-only hygiene report

python3 scripts/verify_all.py           # before publishing: every test and check above plus cross-file checks, read-only
                                        #   --quick skips the slow suites; --with-browser adds the page walk-through

# the second page ("the concierge draft", docs/CONCIERGE_DESIGN.md); site/data.json is only read
python3 scripts/concierge_data.py       # site/_concierge_base.json, the *_u2000 text tables, site/concierge_data.json
                                        #   --no-text reuses the *_u2000 tables on disk; --self-check tests the recomputation
python3 scripts/test_concierge_data.py
python3 scripts/verify_concierge.py     # the concierge page's own publishable check (--with-browser adds its walk-through)
```

Page tests need Node Playwright; see the header of `site_walkthrough_test.js` and `map_component_test.js`.

## Dead, superseded and unreferenced scripts (nothing was deleted)

| Script | Why |
|---|---|
| `h_craigslist.py` | Dead. Craigslist's terms prohibit automated collection (`docs/SOURCES.md`); never run in bulk. |
| `rank_v1_backup.py` | Superseded by `rank.py` (ranking v2). Kept on purpose (`docs/RANKING.md`). |
| `build_area_metrics.py`, `p1_rents.py`, `p1_walkability.py`, `p1_protections_fetch.py`, `p1_acs.py`, `p1_drive_fetch.py` | Phase 1 measured 98 fixed areas. Plan v3 replaced that with per-building lookup tools. `data/area_metrics.csv` was never built. |
| `build_targets.py` | Referenced by nothing; its 16 `data/reference/detail_targets_*.csv` files are read by no script. |
| `build_sqlite.py` | Dormant: `data/house_hunt.sqlite` does not exist and nothing reads it. |
| `tools/taxes_reference.py` | One-off; `data/reference/taxes.csv` is read by no script. |
| `h_mgmt_windsor.py` | Left no harvest file (`data/listings_raw/mgmt_windsor.csv` does not exist). |
| 19 evidence-batch helpers and 8 region helpers | Scratch helpers named nowhere (marked "referenced by nothing" in the tables below). Their batches' CSVs exist, so they are finished, not broken. |
| `zumper_open_pending.py` | Not dead: unfinished. Its output under `data/listings_pending/` is not merged (see `PROGRESS.md`). |

Not scripts, but they live here: `ev_b3_live_notes.json`, `h_mgmt_sightmap_sites_seeds.txt`, `h_region_connecticut_manual.json`, `h_region_nassau_buildings.json`, `local_rules_*.json` / `*.jsonl`, `voices_manual.json`, `source_tests/targets_*.json` are hand-entered inputs to the script of the same prefix. Do not delete them: the harvest scripts cannot be rerun without them.

## Inventory

### Pipeline, in run order

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `run_all.py` | Runs the pipeline in a fixed order and writes the stage report | driver | all of `data/` | `docs/RUN_REPORT.md`, `data/reference/run_history.csv` | is the driver | runs the tests first | active |
| `lib.py` | Shared helpers: cached, throttled fetch with a provenance log; paths; `census_key()`; `redact()`; the refused-host guard (`HostRefused`: no request to a host in `raw/_host_kill_shared.json` or on `OFF_LIMITS`; a cache hit is still served; `HOUSE_HUNT_ALLOW_HOST=<host>` lets one host through) | all | network, `raw/_host_kill_shared.json` | `raw/<source>/` + `_index.jsonl` | imported | `test_lib_guard.py` | active |
| `parsers.py` | Every text parser used by the rules (floors, dogs, fees, offers, staleness, tolls); pure functions | all rule stages | strings | values | imported | `test_parsers.py`, `test_rules.py` | active |
| `gates.py` | Merge the harvest files, dedupe, apply the listing gates | 1 gates | `data/listings_raw/*.csv`, `data/reference/nyc_building_facts.csv`, `community_facts.csv`, `data/evidence/resolved_pending_batch_*.csv` | `data/listings.csv`, `data/gate_summary.md` | yes (full, twice) | `test_rules.py` | active |
| `enrich_nyc_pluto.py` | NYC lot facts (class, floors, units, year) matched to listings by location | 2 enrich | `data/listings.csv`, NYC Open Data PLUTO (cached) | `data/reference/nyc_building_facts.csv` | yes (full) | none | active |
| `enrich_units.py` | Run every lookup tool per passing building; first all-in pass | 2 enrich | `data/listings.csv`, `scripts/tools/*` | `data/enriched/*.json`, `data/buildings_enriched.csv`, `data/units.csv` | yes (full) | none | active |
| `build_neighborhoods.py` | Assign buildings to neighborhoods (incl. the Jersey City split), profile them, propose groupings | 3 neighborhoods | `data/units.csv`, `data/buildings_enriched.csv`, `data/reference/subcity_*` | `data/neighborhoods.csv`, hood columns on `data/units.csv`, `docs/CHECKPOINT_A.md` | yes (full) | none | active |
| `lifestyle_features.py` | ACS and OpenStreetMap lifestyle features per neighborhood (no location features) | 3 neighborhoods | `data/neighborhoods.csv`, ACS (Census key), `tools/places.py` | `data/lifestyle_features.csv` | yes (full) | none | active |
| `lifestyle_color.py` | Extra descriptive variables per neighborhood, beyond the clustering ones | 3 neighborhoods | `data/lifestyle_features.csv`, ACS, places | `data/lifestyle_color.csv` | yes (full) | none | active |
| `crime_benchmarks.py` | Crime yardsticks (US, metro, county) and the per-neighborhood safety table | 3 neighborhoods | FBI CDE (cached), `data/reference/crime_agencies.csv` | `data/reference/crime_benchmarks.csv`, `data/neighborhood_safety.csv` | yes (full) | none | active |
| `lifestyle_groups.py` | Assign each neighborhood to one of the six experiences from saved centres (`--refit` only on purpose) | 3 neighborhoods | `data/lifestyle_color.csv`, `data/neighborhood_safety.csv`, `data/reference/lifestyle_group_centres.csv` | `data/lifestyle_groups.csv` (on `--refit` also the saved centres, scale and fit reference under `data/reference/`) | yes (full) | none | active |
| `building_amenities.py` | Amenities per building parsed from cached pages (run_all passes `--no-fetch`) | 4 master inputs | `data/units.csv`, cached pages under `raw/` | `data/reference/building_amenities.csv` | yes (always, offline) | none | active |
| `build_master.py` | Build the two master tables with basis and source per merged fact; staleness, elevator doubt, overnight parking, phone answers | 5 master | `data/units.csv`, `data/enriched*/`, `data/reference/*`, `data/evidence/*` | `data/master_units.csv`, `data/master_buildings.csv`, `data/master_conflicts.csv`, `data/duplicate_units.csv`, `data/reference/building_crosswalk.csv` | yes | `test_rules.py` | active |
| `rent_terms.py` | Structured rent terms (offer, free months, gross and net, first full payment) for every passing unit | 6 rent terms | `data/units.csv`, cached pages, `data/evidence/*` | `data/rent_terms.csv`, `docs/harvest_notes/rent_terms.md` | yes | `test_rules.py` | active |
| `all_in.py` | All-in monthly cost and the $3,000 cap; pet-rent estimate; `all_in_likely` | 7 all-in | `data/master_units.csv`, `data/rent_terms.csv` | adds columns to `data/master_units.csv`; `data/reference/cost_estimates.csv` | yes | `test_rules.py` | active |
| `avoid.py` | Evidence rules: unit exclusions, avoid buildings, pause notes; co-ops out | 8 evidence rules | `data/evidence/{live_check,confirm,items,facts}_batch_*.csv`, `nyc_records_flags.csv`, `non_nyc_records.csv`, `rating_standard.csv` | `data/unit_exclusions.csv`, `data/avoid_buildings.csv`, `data/reference/ground_reading_unassigned.csv` | yes | `test_rules.py` | active |
| `verdicts.py` | Reviewed-verdict table: `digest` prints what needs reading, `add` records verdicts; library for `rank.py` | 8 evidence rules | `data/evidence/*`, `data/master_units.csv` | `data/evidence/review_verdicts.csv` | imported by `rank.py`, `check_registry.py` | `test_rules.py` | active |
| `rank.py` | Ranking v2, open-item and disclosure rules, selection of shown units, Queens spectrum | 9 rank | master tables, `lifestyle_groups.csv`, `unit_exclusions.csv`, `avoid_buildings.csv`, `rent_terms.csv`, `review_verdicts.csv` | `data/ranked_units.csv`, `data/group_exchange.csv`, `data/excluded_*.csv`, `data/needs_confirmation.csv`, `data/needs_live_check.csv`, `data/reference/queens_spectrum_definition.csv` | yes | `test_rules.py --data`, `check_registry.py` | active |
| `check_registry.py` | Field registry, wiring check, shown-list assertions, review rule | 10 check | master tables, `ranked_units.csv`, scripts (by grep) | `data/reference/field_registry.csv` | yes (last) | is a check | active |
| `build_page_data.py` | Export the page data contract | 11 page data | `data/ranked_units.csv`, `lifestyle_groups.csv`, `group_exchange.csv`, `avoid_buildings.csv`, `needs_*.csv`, `local_rules.csv`, `data/voices/*`, `subcity_crime_jersey_city.csv` | `site/data.json` | no (run after) | `test_rules.py --data` (page checks) | active |
| `page_data_extras.py` | Add prose, round-2 quotes and rules, contacts, About text, ratings, descriptions, photo links, neighborhood order | 12 extras | `site/data.json`, `data/reference/scene_text_*.csv`, `building_about.csv`, `realtor_lines.csv`, `building_contacts*.csv`, `neighborhood_descriptions*.csv`, `local_rules_round2.csv`, `data/voices/*_round2.csv`, `data/evidence/ratings_census.csv` | `site/data.json` (in place) | no (run after) | `test_page_data_extras.py`, `site_walkthrough_test.js` | active |
| `build_site.py` | Inline the data, map base and illustrations into the single-file page | 13 site | `site/index.html`, `site/data.json`, `site/map_base.json`, `site/illustrations.json` | `site/dist/index.html` | no (run after) | `site_walkthrough_test.js` | active |
| `build_artifact.py` | Strip the outer document shell from the built page so the artifact host can wrap it; optional banner; size and title checks | 14 publish | `site/dist/index.html` | `site/dist/artifact.html` | no (run after) | `test_page_data_extras.py` | active |

### Text, page assets and page tests

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `build_illustrations.py` | Draw the six experience illustrations as inline SVG | site assets | `site/data.json` `years[]` | `site/illustrations.json`, `site/illustrations_preview.html` | no | none (preview page and screenshots) | active |
| `build_map_base.py` | Build the map base geometry from Census boundary and water files | site assets | www2.census.gov files (cached under `raw/census_cb`, `raw/census_areawater`) | `site/map_base.json` | no | `map_component_test.js` | active |
| `build_map_demo.py` | Embed trimmed data into the standalone map demo | site assets | `site/data.json`, `site/map_base.json` | `site/map_component.html` | no | `map_component_test.js` | active (prototype demo only) |
| `build_scene_text.py` | Fill the hand-written scene drafts with numbers from the data and write their evidence | text | `data/reference/scene_text_source.txt`, data tables, `site/data.json` | `data/reference/scene_text_years.csv`, `scene_text_neighborhoods.csv` | no | `check_scene_text.py` | active |
| `check_scene_text.py` | Re-test every number and claim in the scene text against the current data; house style | text check | `scene_text_*.csv`, data tables, `site/data.json` | report on stdout, exit code | no | is a check | active |
| `map_component_test.js` | Playwright walk-through of the standalone map demo | site test | `site/map_component.html` | `site/screens/map_*.png` | no | is a test | active |
| `realtor_lines.py` | Compose "About the building" and the per-unit line, catch and section subheads from the data | text | `site/data.json` | `data/reference/building_about.csv`, `data/reference/realtor_lines.csv` | no | `test_realtor_lines.py` | active |
| `site_walkthrough_test.js` | Playwright walk-through of the page at one width: heights, flows, no crime wording in the open, built file equals served file | site test | `site/` served locally, `site/dist/index.html` | `site/screens/*.png` at 390 px | no | is a test | active |

### Tests and checks

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `test_parsers.py` | Plain asserts for `parsers.py`: every example quoted in the first independent check | test | none | exit code | yes (first) | is a test | active |
| `test_realtor_lines.py` | Tests for `realtor_lines.py` | test | synthetic rows, `site/data.json` when present | exit code | no | is a test | active |
| `test_rules.py` | Rule tests for every defect of checks 2 and 3; `--data` checks the output | test | none; `--data`: `data/`, `site/data.json` | exit code | yes (first, and `--data` after rank) | is a test | active |
| `test_shortlist_tools.py` | Tests for the three shortlist tools; synthetic rows, no network | test | none | exit code | no | is a test | active |
| `test_page_data_extras.py` | Tests for `page_data_extras.py` and `build_artifact.py`: each block on a made-up page, idempotence, the quote screen, contacts, ratings; one run on the real data | test | temp folder; `site/data.json` copy | exit code | no | is a test | active |
| `verify_all.py` | One read-only command before publishing: runs every `test_*.py`, `check_registry.py` (its table write switched off), `check_scene_text.py`, `page_data_extras.py --dry-run --strict`, then its own checks (shown ids = page ids, current verdicts, `realtor_lines.csv` / `building_about.csv` ids = page ids, scene text for every neighborhood, no floor-plan rows, no `key=` values, `site/dist` fresh); `--quick`, `--with-browser` | publish check | `data/`, `site/`, the tests and checkers | report and table on stdout, exit code; writes nothing | no | `test_verify_all.py` | active |
| `test_verify_all.py` | Tests for the consistency helpers of `verify_all.py`; synthetic inputs | test | none | exit code | no | is a test | active |
| `test_lib_guard.py` | Tests for the refused-host guard in `lib.py` (`HostRefused`): cache hit still served, killed and off-limits hosts stopped before a request, one-host override, malformed kill file; temp raw folder, fake network | test | none | exit code | no | is a test | active |
| `check_repo.py` | Read-only repository hygiene check (big files, orphan CSVs and scripts, broken doc references, key-like strings) | hygiene | the working tree | report on stdout | no | none | active |

### Shortlist tools and contacts

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `building_contacts.py` | One leasing contact per ranked building, from cached pages | contacts | `data/ranked_units.csv`, cached pages | `data/reference/building_contacts.csv` | no | none | active (rerun by hand, offline by default) |
| `building_contacts_own_site.py` | Leasing phone from the building's own site where only a tracking number was known | contacts | `building_contacts.csv`, own sites | `data/reference/building_contacts_own_site.csv` | no | none | one-off harvest (done) |
| `call_sheet.py` | Phone questions for the top places per experience; reads answers back | shortlist tool | `data/ranked_units.csv`, `needs_confirmation.csv`, contacts | `out/call_sheet.csv`, `out/call_sheet.md`; answers go to `data/evidence/call_answers.csv` | no | `test_shortlist_tools.py` | active |
| `recheck_shortlist.py` | Re-read each short-listed listing page once (network; honours refusals) | shortlist tool | `--ids` file, listing pages | `out/recheck_<date>.csv`, `raw/recheck/<date>/` | no | `test_shortlist_tools.py` | active |
| `thin_call_contacts.py` | Phone, hours and URL for the one-question buildings of the three thin experiences | contacts | `data/evidence_pending/open_questions_by_building.csv` | `data/evidence_pending/open_questions_contacts.csv`, `out/call_sheet_thin_experiences.md` | no | none | one-off harvest (done) |
| `tour_days.py` | Group chosen places into tour days and order the stops | shortlist tool | `--ids` file, `data/ranked_units.csv` | `out/tour_days.csv`, `out/tour_days.md` | no | `test_shortlist_tools.py` | active |

### Lookup tools (`scripts/tools/`)

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `tools/__init__.py` | Package marker | — | — | — | — | — | active |
| `tools/crime.py` | Lookup tool: police-agency rates and nearby incidents for any point | lookup tool | FBI CDE, NYPD data, agency tables | values with provenance | via `enrich_units.py` | none | active |
| `tools/drive.py` | Lookup tool: free-flow drive time, distance and tolls to Jamaica | lookup tool | OSRM (cached), `data/reference/tolls.csv`, `njta_tolls.csv` | values with provenance | via `enrich_units.py` | none | active |
| `tools/places.py` | Lookup tool: what is around an address, from a local OpenStreetMap index | lookup tool | `raw/big/osm/region.osm.pbf` | values with provenance | via `enrich_units.py` | none | active |
| `tools/taxes_reference.py` | Write the hand-read tax reference table | reference | hand-read rules | `data/reference/taxes.csv` | no | none | one-off (done); the CSV is read by no script |
| `tools/transit.py` | Lookup tool: door-to-door public transit to Jamaica from GTFS | lookup tool | GTFS feeds | values with provenance | via `enrich_units.py` | none | active |
| `tools/utilities.py` | Lookup tool: estimated electric, gas and internet per month | lookup tool | `data/reference/utility_rates.csv` | values with provenance | via `enrich_units.py` | none | active |

### Evidence: records, ratings, pending listings

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `ev_ic2_live.py` | Live-check rows from the second independent check's own page reads | evidence | checker's cached pages | `data/evidence/live_check_batch_ic2.csv` | no | none | one-off harvest (done) |
| `non_nyc_probe.py` | Polite probe helper for the non-NYC record sources | evidence (records) | URLs | `raw/non_nyc_records/` | no | none | one-off harvest (done) |
| `non_nyc_records.py` | NJ housing-inspection reports and Jersey City police incidents for non-NYC candidates | evidence (records) | candidate lists, NJ DCA portal, JC IMPACT | `data/evidence/non_nyc_records.csv`, `data/reference/non_nyc_record_sources.csv` | no | none | one-off harvest (done) |
| `nyc_building_records.py` | Official NYC records per candidate building, with citywide baselines and flags | evidence (records) | `data/reference/evidence_batches/*.csv`, NYC Open Data | `data/evidence/nyc_records*.csv`, `nyc_records_summary.json` | no | `--verify` re-runs sample queries | active (rerun when candidates change; network) |
| `rating_standard.py` | Rating-based screen for buildings outside NYC, calibrated on NYC records | evidence (ratings) | `data/evidence/ratings_*.csv`, `nyc_records_flags.csv` | `data/evidence/rating_standard.csv`, `docs/RATING_STANDARD.md` | no | none | active (rerun by hand when ratings change) |
| `ratings_round1.py` | Structured ratings for round-1 candidate buildings | evidence (ratings) | `evidence_batches/batch_*.csv`, cached pages | `data/evidence/ratings_round1.csv` | no | none | one-off harvest (done) |
| `resolve_pending_thin_years.py` | Evidence batch 18: resolve pending listings in the three thin experiences | evidence | `data/listings.csv`, listing and own-site pages | `data/evidence_pending/*` | no | none | one-off harvest (done) |
| `zumper_open_pending.py` | Open Zumper listings seen only as search cards | harvest (pending) | `data/listings_raw/zumper.csv`, zumper.com | `data/listings_pending/*`, `raw/zumper_open_pending/` | no | none | in progress: output not merged (see PROGRESS.md) |

### Listing harvesters

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `build_targets.py` | Funnel: pick listings worth a detail-page fetch | harvest | `data/listings.csv` | `data/reference/detail_targets_<source>.csv` | no | none | superseded: referenced by nothing; its 16 output files are read by no script |
| `community_facts.py` | Building facts for management-company communities (elevator, floors, pets, fees) | harvest (facts) | `data/listings_raw/mgmt_*.csv`, community pages | `data/reference/community_facts.csv` | no (its CSV is read by `gates.py` and `build_master.py`) | none | one-off harvest (done) |
| `h_apartmentlist.py` | Apartment List harvest | harvest | search grid, apartmentlist.com | `data/listings_raw/apartmentlist.csv`, `raw/apartmentlist/` | no | none | one-off harvest (done); parsers imported by later scripts |
| `h_craigslist.py` | Craigslist harvest: never run in bulk (terms of use prohibit it) | harvest | — | `data/listings_raw/craigslist.csv` (header only) | no | none | dead: must not be run (docs/SOURCES.md) |
| `h_manual.py` | Manual addition: Envy by Gomes, Newark (owner request) | harvest | cached pages in `raw/manual_envy/` | `data/listings_raw/manual.csv`, `data/reference/manual_buildings.csv`, `data/evidence/*_batch_manual.csv` | no | none | one-off harvest (done) |
| `h_inbox.py` | The inbox drop box: listings Will or Lamia save by hand (HTML, MHTML, PDF, screenshot, `inbox/links.txt`) from any site; reads JSON-LD, embedded page state and visible text; opens pasted links only on hosts we may read (never Trulia, Zillow, StreetEasy) | harvest | `inbox/` (raw files git-ignored), allowed pasted links | `data/listings_raw/manual_inbox.csv`, `inbox/STATUS.txt`, `raw/inbox_links/` | no (run by `h_manual.py`; `h_manual.py --inbox` runs only this) | `test_inbox.py` (fixtures in `fixtures/inbox/`) | active (rerun whenever files are dropped) |
| `h_mgmt_avalon.py` | Harvest: AvalonBay | harvest | AvalonBay site | `data/listings_raw/mgmt_avalon.csv` | no | none | one-off harvest (done) |
| `h_mgmt_blt.py` | Harvest: Building and Land Technology | harvest | Building and Land Technology site | `data/listings_raw/mgmt_blt.csv` | no | none | one-off harvest (done) |
| `h_mgmt_common.py` | Shared helpers and the harvest column contract for management-site harvesters | harvest | — | — | imported | none | active (library) |
| `h_mgmt_fairfield.py` | Harvest: Fairfield Properties | harvest | Fairfield Properties site | `data/listings_raw/mgmt_fairfield.csv` | no | none | one-off harvest (done) |
| `h_mgmt_gardencommunities.py` | Harvest: Garden Communities | harvest | Garden Communities site | `data/listings_raw/mgmt_gardencommunities.csv` | no | none | one-off harvest (done) |
| `h_mgmt_gardenhomes.py` | Harvest: Garden Homes Management | harvest | Garden Homes Management site | `data/listings_raw/mgmt_gardenhomes.csv` | no | none | one-off harvest (done) |
| `h_mgmt_gdc.py` | Harvest: Ginsburg Development | harvest | Ginsburg Development site | `data/listings_raw/mgmt_gdc.csv` | no | none | one-off harvest (done) |
| `h_mgmt_greystar.py` | Harvest: Greystar | harvest | Greystar site | `data/listings_raw/mgmt_greystar.csv` | no | none | one-off harvest (done) |
| `h_mgmt_newport.py` | Harvest: Newport Rentals | harvest | Newport Rentals site | `data/listings_raw/mgmt_newport.csv` | no | none | one-off harvest (done) |
| `h_mgmt_render.js` | Headless render helper for JS-only price pages | harvest | jobs JSON | rendered HTML under `raw/` | no | none | one-off harvest (done) |
| `h_mgmt_russo.py` | Harvest: Russo Development | harvest | Russo Development site | `data/listings_raw/mgmt_russo.csv` | no | none | one-off harvest (done) |
| `h_mgmt_sightmap.py` | SightMap embed reader shared by management-site harvesters | harvest | sightmap.com embeds | rows for callers | imported | none | active (library) |
| `h_mgmt_sightmap_sites.py` | Harvest: per-building sites with a SightMap embed | harvest | per-building sites with a SightMap embed site | `data/listings_raw/mgmt_sightmap_sites.csv` | no | none | one-off harvest (done) |
| `h_mgmt_windsor.py` | Harvest: Windsor Communities | harvest | Windsor Communities site | `data/listings_raw/mgmt_windsor.csv` | no | none | one-off harvest (done); wrote no rows that survive (no `mgmt_windsor.csv`) |
| `h_trulia.py` | Trulia harvest by ZIP | harvest | search grid, trulia.com | `data/listings_raw/trulia.csv`, `raw/trulia/` | no | none | one-off harvest (done); Trulia now refuses us, do not run; parsers imported by evidence scripts |
| `h_zumper.py` | Zumper harvest inside the search grid | harvest | `data/reference/search_grid.csv`, zumper.com | `data/listings_raw/zumper.csv`, `raw/zumper/` | no | none | one-off harvest (done); parsers imported by later scripts |

### Local rules, neighborhood text and voices

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `local_rules_build.py` | Build local rules and dog parks from hand-entered rows; every quote is checked against the cached page | harvest (local rules) | `local_rules_rows.jsonl`, `local_rules_dogparks.jsonl` | `data/reference/local_rules.csv`, `dog_parks.csv` | no | verbatim-quote check built in | active (rerun by hand, offline) |
| `local_rules_fetch.py` | Fetch official municipal pages for the local-rules pass | harvest (local rules) | `local_rules_munis.json` | `raw/local_rules/` | no | none | one-off harvest (done) |
| `local_rules_round2.py` | Local rules round 2 for municipalities added later | harvest (local rules) | `local_rules_round2_rows.jsonl`, municipal pages | `data/reference/local_rules_round2.csv` | no | verbatim-quote check built in | one-off harvest (done) |
| `neighborhood_descriptions.py` | Short attributed outside descriptions per neighborhood (Wikipedia dump leads) | harvest (text) | Wikimedia dump | `data/reference/neighborhood_descriptions.csv`, `neighborhood_summaries.csv` | no | none | one-off harvest (done) |
| `neighborhood_descriptions_round2.py` | Round 2: character quotes from Wikipedia bodies and tourism sites | harvest (text) | Wikimedia dump, tourism sites | `data/reference/neighborhood_descriptions_round2.csv`, `neighborhood_summaries_round2.csv` | no | none | one-off harvest (done) |
| `verify_quotes.py` | Confirm every stored excerpt appears verbatim on its cached page | harvest (voices) check | `data/voices/neighborhood_quotes.csv`, cached pages | sets `verified` | no | is a check | active (rerun by hand, offline) |
| `voices_build.py` | Build the quotes, survey and coverage files from the pooled pages | harvest (voices) | `raw/voices_pool/*.jsonl` | `data/voices/{neighborhood_quotes,neighborhood_survey,coverage}.csv` | no | `verify_quotes.py` | active (rerun by hand, offline) |
| `voices_citydata.py` | City-Data forum threads for shown neighborhoods | harvest (voices) | targets | `raw/voices_pool/` | no | none | one-off harvest (done) |
| `voices_fetch.py` | Fetch Trulia neighborhood pages and Niche review pages | harvest (voices) | targets | `raw/voices_*` | no | none | one-off harvest (done); do not rerun against Trulia |
| `voices_lib.py` | Fetch helper for the voices lookups | harvest (voices) | — | — | imported | none | one-off harvest (done) |
| `voices_round2.py` | Voices round 2 for neighborhoods with no round-1 row | harvest (voices) | `site/data.json`, Niche, City-Data | `data/voices/*_round2.csv` | no | none | one-off harvest (done) |
| `voices_targets.py` | Hand-checked lookup targets for the neighborhood-voices pass | harvest (voices) | — | — | imported | none | one-off harvest (done) |

### Setup, phase 1 and leftovers

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `build_area_metrics.py` | Merge per-domain area metrics and validate | phase 1 | `data/metrics/*.csv` | `data/area_metrics.csv` (does not exist) | no | none | superseded (area-level model replaced by per-building lookups); referenced by nothing |
| `build_areas.py` | Build the 98 phase-1 areas from the seed list | phase 1 | `seeds/areas_seed.csv`, GTFS, Census geocoder | `data/areas.csv` | no | none | one-off (done); helper functions still imported by `build_neighborhoods.py` and others |
| `build_search_grid.py` | Search grid: every ZCTA within a 2-hour free-flow drive of Jamaica | setup | Census Gazetteer, OSRM | `data/reference/search_grid.csv` | no | none | one-off (done); the CSV is read by the harvesters |
| `build_sqlite.py` | Load top-level CSVs into one SQLite file | convenience | `data/*.csv` | `data/house_hunt.sqlite` (not present) | no | none | dormant: nothing reads the database; safe to run by hand |
| `build_subcity_neighborhoods.py` | Prepare sub-city neighborhoods for Jersey City and Newark | setup | Census tracts and voting districts, OSM extract | `data/reference/subcity_*` | no | none | one-off (done); outputs read by `build_neighborhoods.py` |
| `p1_acs.py` | Phase 1 ACS metrics per area | phase 1 | Census summary files | `data/metrics/acs.csv` | no | none | superseded (phase-1 area model) |
| `p1_drive_fetch.py` | Phase 1 OSRM routes area to Jamaica | phase 1 | OSRM | `raw/osrm/` | no | none | superseded by `tools/drive.py` |
| `p1_protections_fetch.py` | Helper: fetch an official renter-protection page and grep it | phase 1 | URL | stdout | no | none | superseded; referenced by nothing |
| `p1_rents.py` | Phase 1 rent benchmarks (ZORI, Apartment List, HUD) | phase 1 | public CSVs | `data/metrics/rent.csv` (not present) | no | none | superseded; referenced by nothing |
| `p1_safety_nyc.py` | Phase 1 NYC safety metrics; its NYPD loaders are imported by `tools/crime.py` | phase 1 / library | NYPD complaint data | `data/metrics/safety_nyc.csv` | no | none | active as a library; the area table is superseded |
| `p1_transit_feeds.py` | GTFS feed download and calendar check; imported by `tools/transit.py` | setup / library | GTFS feeds | `raw/big/gtfs_transit/` and its manifest | no | none | active as a library |
| `p1_walkability.py` | Phase 1 EPA walkability per area | phase 1 | EPA zip, TIGER | `data/metrics/walkability.csv` | no | none | superseded; referenced by nothing |
| `rank_v1_backup.py` | Ranking version 1, kept for reference | — | — | — | no | none | superseded by `rank.py` (v2) |
| `source_tests/browser.py` | Robots-checked headless-browser probe | setup | URLs | `raw/source_tests/` | no | none | one-off (done) |
| `source_tests/probe.py` | Low-volume source access probe (robots, test paths) | setup | targets JSON | `raw/source_tests/` | no | none | one-off (done); basis of docs/SOURCES.md |
| `source_tests/render.js` | Render one URL in headless Chrome | setup | URL | HTML file | no | none | one-off (done); also called by `h_mgmt_russo.py` |

### Evidence batch helpers (batches 1 to 17)

One small family of scripts per batch, written by that batch's agent. All are finished one-off work: the CSVs they wrote under `data/evidence/` are the product, and `scripts/avoid.py` and `scripts/build_master.py` read those, never these scripts. The `*_fetch`, `*_get`, `*_site`, `*_zumper`, `*_igloo` scripts need the network and must not be rerun against a host that has refused us (Trulia).

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `ev_b1_add.py` | upsert records into data/evidence/*_batch_1.csv | evidence batch 1 | `data/reference/evidence_batches/batch_1.csv`, `raw/evidence_b1*/` | `data/evidence/*_batch_1.csv` | no | none | one-off harvest (done) |
| `ev_b1_al.py` | re-fetch Apartment List property pages (refresh) and dump the listing object. | evidence batch 1 | listing, building-site and review pages | `raw/evidence_b1*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_b1_al_write.py` | Write live-check rows and Apartment List-derived confirm/fact rows from the refreshed pages. | evidence batch 1 | `data/reference/evidence_batches/batch_1.csv`, `raw/evidence_b1*/` | `data/evidence/*_batch_1.csv` | no | none | one-off harvest (done); referenced by nothing |
| `ev_b1_art.py` | Fetch an article (robots-checked) and print title, dates and sentences matching a regex. | evidence batch 1 | listing, building-site and review pages | `raw/evidence_b1*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_b1_fetch.py` | robots-checked, throttled fetch of a page; prints keyword context | evidence batch 1 | listing, building-site and review pages | `raw/evidence_b1*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev_b1_probe.py` | (no docstring) | evidence batch 1 | listing, building-site and review pages | `raw/evidence_b1*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_b1_summ.py` | (no docstring) | evidence batch 1 | listing, building-site and review pages | `raw/evidence_b1*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_b1_trulia.py` | (no docstring) | evidence batch 1 | listing, building-site and review pages | `raw/evidence_b1*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_b1_zumper.py` | Zumper building/address pages -> reviews shown on the page, building facts. | evidence batch 1 | listing, building-site and review pages | `raw/evidence_b1*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_batch2_add.py` | append rows to the four output CSVs (dedupe on whole row) | evidence batch 2 | `data/reference/evidence_batches/batch_2.csv`, `raw/evidence_b2*/` | `data/evidence/*_batch_2.csv` | no | none | one-off harvest (done) |
| `ev_batch2_al.py` | re-fetch Apartment List property pages (refresh) and dump the listing objects. | evidence batch 2 | listing, building-site and review pages | `raw/evidence_b2*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_batch2_confirm.py` | confirm_batch_2.csv rows (gate facts) | evidence batch 2 | `data/reference/evidence_batches/batch_2.csv`, `raw/evidence_b2*/` | `data/evidence/*_batch_2.csv` | no | none | one-off harvest (done); referenced by nothing |
| `ev_batch2_facts.py` | facts_batch_2.csv rows from the refreshed Apartment List listing objects plus hand-read pages. | evidence batch 2 | `data/reference/evidence_batches/batch_2.csv`, `raw/evidence_b2*/` | `data/evidence/*_batch_2.csv` | no | none | one-off harvest (done); referenced by nothing |
| `ev_batch2_grab.py` | robots-checked fetch of one URL, saved under raw/evidence_batch2/, keyword contexts printed | evidence batch 2 | listing, building-site and review pages | `raw/evidence_b2*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev_batch2_items.py` | items_batch_2.csv | evidence batch 2 | `data/reference/evidence_batches/batch_2.csv`, `raw/evidence_b2*/` | `data/evidence/*_batch_2.csv` | no | none | one-off harvest (done); referenced by nothing |
| `ev_batch2_live.py` | write live_check rows from the refreshed pages in raw/evidence_batch2/. | evidence batch 2 | `data/reference/evidence_batches/batch_2.csv`, `raw/evidence_b2*/` | `data/evidence/*_batch_2.csv` | no | none | one-off harvest (done); referenced by nothing |
| `ev_batch2_other.py` | refresh the non-Apartment-List listing pages; save text dumps to raw/evidence_batch2/. | evidence batch 2 | listing, building-site and review pages | `raw/evidence_b2*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_batch2_sites.py` | fetch building-site pages (robots-checked) and print gate-fact sentences | evidence batch 2 | listing, building-site and review pages | `raw/evidence_b2*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev_b3_confirm_facts.py` | gate confirmations, facts and the remaining evidence items, read from cached pages (raw/evidence_b3) and typed in from the | evidence batch 3 | `data/reference/evidence_batches/batch_3.csv`, `raw/evidence_b3*/` | `data/evidence/*_batch_3.csv` | no | none | one-off harvest (done) |
| `ev_b3_fetch.py` | polite fetch helper | evidence batch 3 | listing, building-site and review pages | `raw/evidence_b3*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev_b3_live.py` | Evidence batch 3, step 1: parse the re-fetched listing pages (raw/evidence_b3) and write live_check_batch_3.csv | evidence batch 3 | `data/reference/evidence_batches/batch_3.csv`, `raw/evidence_b3*/` | `data/evidence/*_batch_3.csv` | no | none | one-off harvest (done) |
| `ev_b3_nyc.py` | NYC official records per building (PLUTO facts already in data/reference/nyc_building_facts.csv; here: 311 service request | evidence batch 3 | listing, building-site and review pages | `raw/evidence_b3*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev_b3_nyc_items.py` | turn raw/evidence_b3_nyc/_summary.json (311 + HPD by BBL, last 24 months) into item rows. | evidence batch 3 | `data/reference/evidence_batches/batch_3.csv`, `raw/evidence_b3*/` | `data/evidence/*_batch_3.csv` | no | none | one-off harvest (done) |
| `ev_b3_openigloo_items.py` | Openigloo review excerpts (verbatim, hand-selected from the cached building pages) and building facts | evidence batch 3 | `data/reference/evidence_batches/batch_3.csv`, `raw/evidence_b3*/` | `data/evidence/*_batch_3.csv` | no | none | one-off harvest (done) |
| `ev_b3_util.py` | Evidence batch 3 helpers: latest cached path/meta for a URL from raw/evidence_b3/_index.jsonl. | evidence batch 3 | listing, building-site and review pages | `raw/evidence_b3*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `evidence_batch_4_build.py` | assemble the four output CSVs from pages already fetched by evidence_batch_4_fetch.py / _openigloo.py / _get.py | evidence batch 4 | `data/reference/evidence_batches/batch_4.csv`, `raw/evidence_b4*/` | `data/evidence/*_batch_4.csv` | no | none | one-off harvest (done) |
| `evidence_batch_4_fetch.py` | re-fetch every listing URL (cache bypassed) and dump a per-URL summary JSON | evidence batch 4 | listing, building-site and review pages | `raw/evidence_b4*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `evidence_batch_4_get.py` | robots-checked fetch of one page; prints visible text (or greps it) | evidence batch 4 | listing, building-site and review pages | `raw/evidence_b4*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `evidence_batch_4_openigloo.py` | fetch Openigloo building pages (matched by BBL via the reviewed-buildings sitemap). | evidence batch 4 | listing, building-site and review pages | `raw/evidence_b4*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `evidence_b5_fetch.py` | re-fetch every listing URL (refresh) into raw/evidence_b5/ | evidence batch 5 | listing, building-site and review pages | `raw/evidence_b5*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `evidence_b5_get.py` | robots-checked, cached, throttled page fetch -> visible text | evidence batch 5 | listing, building-site and review pages | `raw/evidence_b5*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `evidence_b5_igloo.py` | Openigloo building pages by BBL (robots: Claude-User allowed except /api,/_nuxt,/internal) | evidence batch 5 | listing, building-site and review pages | `raw/evidence_b5*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `evidence_b5_live.py` | write data/evidence/live_check_batch_5.csv from the re-fetched listing pages (no network). | evidence batch 5 | `data/reference/evidence_batches/batch_5.csv`, `raw/evidence_b5*/` | `data/evidence/*_batch_5.csv` | no | none | one-off harvest (done) |
| `evidence_b5_parse.py` | parse the re-fetched Trulia pages into a summary JSON (no network). | evidence batch 5 | listing, building-site and review pages | `raw/evidence_b5*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `evidence_b5_write.py` | write confirm / items / facts CSVs from cached pages (no network) | evidence batch 5 | `data/reference/evidence_batches/batch_5.csv`, `raw/evidence_b5*/` | `data/evidence/*_batch_5.csv` | no | none | one-off harvest (done) |
| `ev6_al_parse.py` | (no docstring) | evidence batch 6 | listing, building-site and review pages | `raw/evidence_b6*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev6_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b6/ | evidence batch 6 | listing, building-site and review pages | `raw/evidence_b6*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev6_igloo.py` | Openigloo building pages by BBL (robots: Claude-User allowed except /api,/_nuxt,/internal) | evidence batch 6 | listing, building-site and review pages | `raw/evidence_b6*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev6_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 6 | listing, building-site and review pages | `raw/evidence_b6*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev6_text.py` | Dump visible text of a cached html file (evidence batch 6 helper). | evidence batch 6 | listing, building-site and review pages | `raw/evidence_b6*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev6_trulia_parse.py` | (no docstring) | evidence batch 6 | listing, building-site and review pages | `raw/evidence_b6*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev6_write.py` | write the four output CSVs from the cached, parsed pages (no network) | evidence batch 6 | `data/reference/evidence_batches/batch_6.csv`, `raw/evidence_b6*/` | `data/evidence/*_batch_6.csv` | no | none | one-off harvest (done) |
| `ev7_al_parse.py` | parse cached Apartment List property pages -> scratch al_parsed.json (listing objects). | evidence batch 7 | listing, building-site and review pages | `raw/evidence_b7*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev7_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b7/ | evidence batch 7 | listing, building-site and review pages | `raw/evidence_b7*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev7_lines.py` | print visible-text lines of a cached page that match a regex (deduped) | evidence batch 7 | listing, building-site and review pages | `raw/evidence_b7*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev7_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 7 | listing, building-site and review pages | `raw/evidence_b7*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev7_trulia_parse.py` | parse cached Trulia building pages -> scratch trulia_parsed.json | evidence batch 7 | listing, building-site and review pages | `raw/evidence_b7*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev7_write.py` | rebuild data/evidence/{live_check,confirm,items,facts,ratings}_batch_7.csv from the cached pages in raw/evidence_b7/ (no n | evidence batch 7 | `data/reference/evidence_batches/batch_7.csv`, `raw/evidence_b7*/` | `data/evidence/*_batch_7.csv` | no | none | one-off harvest (done) |
| `ev7_zumper.py` | Zumper building/address pages -> ratings and reviews shown on the page, building facts | evidence batch 7 | listing, building-site and review pages | `raw/evidence_b7*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev8_al_parse.py` | (no docstring) | evidence batch 8 | listing, building-site and review pages | `raw/evidence_b8*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev8_crawl.py` | polite look at a building's own site: home page + up to 4 same-host pages whose link mentions pets/faq/amenities/fees/park | evidence batch 8 | listing, building-site and review pages | `raw/evidence_b8*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev8_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b8/ | evidence batch 8 | listing, building-site and review pages | `raw/evidence_b8*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev8_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 8 | listing, building-site and review pages | `raw/evidence_b8*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev8_text.py` | Dump visible text of a cached html file (evidence batch 6 helper). | evidence batch 8 | listing, building-site and review pages | `raw/evidence_b8*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev8_trulia_parse.py` | parse refetched Trulia building pages -> scratch JSON + compact print. | evidence batch 8 | listing, building-site and review pages | `raw/evidence_b8*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev8_write.py` | rebuild live_check / confirm / items / facts / ratings CSVs from cached pages (no network) | evidence batch 8 | `data/reference/evidence_batches/batch_8.csv`, `raw/evidence_b8*/` | `data/evidence/*_batch_8.csv` | no | none | one-off harvest (done) |
| `ev8_zumper.py` | Zumper building/address pages -> rating sources and review texts | evidence batch 8 | listing, building-site and review pages | `raw/evidence_b8*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev9_al_parse.py` | (no docstring) | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev9_al_reviews.py` | Apartment List building pages -> aggregate rating + review objects | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev9_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b9/ | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev9_grep.py` | grep visible text of cached own-site pages | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev9_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev9_sites.py` | building own sites | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev9_text.py` | Dump visible text of a cached html file (evidence batch 9 helper). | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev9_trulia_parse.py` | (no docstring) | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev9_write.py` | build data/evidence/{live_check,confirm,items,facts,ratings}_batch_9.csv from cached pages | evidence batch 9 | `data/reference/evidence_batches/batch_9.csv`, `raw/evidence_b9*/` | `data/evidence/*_batch_9.csv` | no | none | one-off harvest (done) |
| `ev9_zumper.py` | Zumper building/address pages -> rating sources and review texts | evidence batch 9 | listing, building-site and review pages | `raw/evidence_b9*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev10_al_parse.py` | parse refetched Apartment List pages -> scratch al_parsed.json, print compact summary. | evidence batch 10 | listing, building-site and review pages | `raw/evidence_b10*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev10_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b10/ | evidence batch 10 | listing, building-site and review pages | `raw/evidence_b10*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev10_get.py` | robots-checked, throttled fetch of a page; prints keyword context | evidence batch 10 | listing, building-site and review pages | `raw/evidence_b10*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev10_links.py` | list links in a cached page whose href or text matches a regex | evidence batch 10 | listing, building-site and review pages | `raw/evidence_b10*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev10_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 10 | listing, building-site and review pages | `raw/evidence_b10*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev10_trulia_parse.py` | parse refetched Trulia /building/ and /home/ pages -> scratch trulia_parsed.json + compact print. | evidence batch 10 | listing, building-site and review pages | `raw/evidence_b10*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev10_write.py` | rebuild data/evidence/{live_check,confirm,items,facts,ratings}_batch_10.csv from the pages cached in raw/evidence_b10/ | evidence batch 10 | `data/reference/evidence_batches/batch_10.csv`, `raw/evidence_b10*/` | `data/evidence/*_batch_10.csv` | no | none | one-off harvest (done) |
| `ev10_zumper.py` | Zumper building/address pages -> rating, reviews shown on page, building facts | evidence batch 10 | listing, building-site and review pages | `raw/evidence_b10*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev11_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b11/ | evidence batch 11 | listing, building-site and review pages | `raw/evidence_b11*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev11_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 11 | listing, building-site and review pages | `raw/evidence_b11*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev11_text.py` | turn cached pages listed in the scratch fetch log into plain text files for reading (no network). | evidence batch 11 | listing, building-site and review pages | `raw/evidence_b11*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev11_trulia_parse.py` | dump the gate-relevant parts of the refetched Trulia pages to scratch JSON (no network). | evidence batch 11 | listing, building-site and review pages | `raw/evidence_b11*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev11_write.py` | build the five output CSVs from cached pages | evidence batch 11 | `data/reference/evidence_batches/batch_11.csv`, `raw/evidence_b11*/` | `data/evidence/*_batch_11.csv` | no | none | one-off harvest (done) |
| `ev11_zumper_reviews.py` | read the Google rating block (buildingReviews) that Zumper building pages embed | evidence batch 11 | listing, building-site and review pages | `raw/evidence_b11*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_al_parse.py` | parse refetched Apartment List pages -> scratch al_parsed.json, print compact summary. | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b12/ | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_grep.py` | print keyword sentences and internal links from cached pages (no network) | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_text.py` | turn cached pages listed in the scratch fetch log into plain text files for reading (no network). | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_trulia_cached.py` | read Trulia building pages captured earlier today by the harvest (raw/trulia, raw/region_connecticut); no network | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_trulia_parse.py` | dump the gate-relevant parts of the refetched Trulia pages to scratch JSON (no network). | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_write.py` | build the five output CSVs from cached pages and the scratch parse files | evidence batch 12 | `data/reference/evidence_batches/batch_12.csv`, `raw/evidence_b12*/` | `data/evidence/*_batch_12.csv` | no | none | one-off harvest (done) |
| `ev12_zumper.py` | Zumper building/address pages -> rating, reviews shown on page, building facts | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev12_zumper_reviews.py` | read the Google rating block (buildingReviews) that Zumper building pages embed | evidence batch 12 | listing, building-site and review pages | `raw/evidence_b12*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev13_al_parse.py` | parse refetched Apartment List pages -> scratch al_parsed.json, print compact summary. | evidence batch 13 | listing, building-site and review pages | `raw/evidence_b13*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev13_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b13/ | evidence batch 13 | listing, building-site and review pages | `raw/evidence_b13*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev13_grep.py` | print title, keyword lines and internal links of cached pages from a scratch log (no network) | evidence batch 13 | listing, building-site and review pages | `raw/evidence_b13*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev13_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 13 | listing, building-site and review pages | `raw/evidence_b13*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev13_text.py` | turn cached pages listed in the scratch fetch log into plain text files for reading (no network). | evidence batch 13 | listing, building-site and review pages | `raw/evidence_b13*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev13_trulia_parse.py` | dump the gate-relevant parts of the refetched Trulia pages to scratch JSON (no network). | evidence batch 13 | listing, building-site and review pages | `raw/evidence_b13*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev13_write.py` | write the five evidence CSVs from what was read on the cached pages (no network) | evidence batch 13 | `data/reference/evidence_batches/batch_13.csv`, `raw/evidence_b13*/` | `data/evidence/*_batch_13.csv` | no | none | one-off harvest (done) |
| `ev13_zumper.py` | Zumper address/building pages -> rating, reviews shown on page, building facts | evidence batch 13 | listing, building-site and review pages | `raw/evidence_b13*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev13_zumper_reviews.py` | read the Google rating block (buildingReviews) that Zumper building pages embed | evidence batch 13 | listing, building-site and review pages | `raw/evidence_b13*/` cache, scratch files or stdout | no | none | one-off harvest (done); referenced by nothing |
| `ev14_al_parse.py` | parse refetched Apartment List pages (no network) into scratch JSON. | evidence batch 14 | listing, building-site and review pages | `raw/evidence_b14*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev14_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b14/ | evidence batch 14 | listing, building-site and review pages | `raw/evidence_b14*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev14_show.py` | show a cached page as text (keyword lines or head) plus its internal links | evidence batch 14 | listing, building-site and review pages | `raw/evidence_b14*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev14_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 14 | listing, building-site and review pages | `raw/evidence_b14*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev14_text.py` | turn cached pages listed in the scratch fetch log into plain text files for reading (no network). | evidence batch 14 | listing, building-site and review pages | `raw/evidence_b14*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev14_trulia_parse.py` | dump the gate-relevant parts of the refetched Trulia pages to scratch JSON (no network). | evidence batch 14 | listing, building-site and review pages | `raw/evidence_b14*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev14_write.py` | build the five output CSVs from the cached pages (no network) | evidence batch 14 | `data/reference/evidence_batches/batch_14.csv`, `raw/evidence_b14*/` | `data/evidence/*_batch_14.csv` | no | none | one-off harvest (done) |
| `ev14_zumper_reviews.py` | read the Google rating block (buildingReviews) that Zumper building pages embed | evidence batch 14 | listing, building-site and review pages | `raw/evidence_b14*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev15_al_parse.py` | parse refetched Apartment List pages -> scratch al_parsed.json, print compact summary. | evidence batch 15 | listing, building-site and review pages | `raw/evidence_b15*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev15_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b15/ | evidence batch 15 | listing, building-site and review pages | `raw/evidence_b15*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev15_get.py` | robots-checked, throttled fetch of a page; prints keyword context | evidence batch 15 | listing, building-site and review pages | `raw/evidence_b15*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev15_igloo.py` | Openigloo building pages matched by BBL through the reviewed-buildings sitemaps (cached in raw/openigloo), then the BBL-k | evidence batch 15 | listing, building-site and review pages | `raw/evidence_b15*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev15_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 15 | listing, building-site and review pages | `raw/evidence_b15*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev15_trulia_parse.py` | dump the gate-relevant parts of the refetched Trulia pages to scratch JSON (no network). | evidence batch 15 | listing, building-site and review pages | `raw/evidence_b15*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev15_write.py` | build the five CSVs from what was read (no network) | evidence batch 15 | `data/reference/evidence_batches/batch_15.csv`, `raw/evidence_b15*/` | `data/evidence/*_batch_15.csv` | no | none | one-off harvest (done) |
| `ev15_zumper.py` | Zumper building/address pages -> rating, reviews shown on page, building facts | evidence batch 15 | listing, building-site and review pages | `raw/evidence_b15*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev16_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b16/ | evidence batch 16 | listing, building-site and review pages | `raw/evidence_b16*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev16_igloo.py` | Openigloo building pages matched by BBL through the reviewed-buildings sitemaps (cached in raw/openigloo), then the BBL-k | evidence batch 16 | listing, building-site and review pages | `raw/evidence_b16*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev16_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 16 | listing, building-site and review pages | `raw/evidence_b16*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev16_trulia_parse.py` | dump the gate-relevant parts of the refetched Trulia pages to scratch JSON (no network). | evidence batch 16 | listing, building-site and review pages | `raw/evidence_b16*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev16_write.py` | rebuild the five CSVs in data/evidence from cached pages (no network) | evidence batch 16 | `data/reference/evidence_batches/batch_16.csv`, `raw/evidence_b16*/` | `data/evidence/*_batch_16.csv` | no | none | one-off harvest (done) |
| `ev16_zumper_reviews.py` | read the Google rating block (buildingReviews) that Zumper building pages embed | evidence batch 16 | listing, building-site and review pages | `raw/evidence_b16*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev17_al_parse.py` | parse refetched Apartment List pages -> scratch al_parsed.json, print compact summary. | evidence batch 17 | listing, building-site and review pages | `raw/evidence_b17*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev17_fetch.py` | refetch listing URLs (refresh) into raw/evidence_b17/ | evidence batch 17 | listing, building-site and review pages | `raw/evidence_b17*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev17_get.py` | robots-checked, throttled fetch of a page; prints keyword context | evidence batch 17 | listing, building-site and review pages | `raw/evidence_b17*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev17_igloo.py` | Openigloo building pages matched by BBL through the reviewed-buildings sitemaps (cached in raw/openigloo), then the BBL-k | evidence batch 17 | listing, building-site and review pages | `raw/evidence_b17*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev17_site.py` | polite fetch of a building's own site: robots check (incl | evidence batch 17 | listing, building-site and review pages | `raw/evidence_b17*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev17_text.py` | fetch (robots-checked, cached) a page and print keyword context from its plain text | evidence batch 17 | listing, building-site and review pages | `raw/evidence_b17*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev17_trulia_parse.py` | dump the gate-relevant parts of the refetched Trulia pages to scratch JSON (no network). | evidence batch 17 | listing, building-site and review pages | `raw/evidence_b17*/` cache, scratch files or stdout | no | none | one-off harvest (done) |
| `ev17_write.py` | write the five CSVs from what was read (no network) | evidence batch 17 | `data/reference/evidence_batches/batch_17.csv`, `raw/evidence_b17*/` | `data/evidence/*_batch_17.csv` | no | none | one-off harvest (done) |
| `ev17_zumper.py` | Zumper building/address pages -> rating, reviews shown on page, building facts | evidence batch 17 | listing, building-site and review pages | `raw/evidence_b17*/` cache, scratch files or stdout | no | none | one-off harvest (done) |

### Region harvest helpers

Building-first passes for the five outer regions (`docs/REGION_AGENT_BRIEF.md`). Finished one-off work.

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `h_region_connecticut.py` | Connecticut region pass (building-first): merge what was read per building and write the three outputs | region harvest (connecticut) | building and listing-site pages; `data/reference/leads/connecticut.csv` | `data/listings_raw/region_connecticut.csv`, `data/reference/region_buildings_connecticut.csv` | no | none | one-off harvest (done) |
| `h_region_connecticut_al.py` | Connecticut region pass, stage 1: enumerate rental buildings from Apartment List city pages (discovery) and read every property page (facts: | region harvest (connecticut) | building and listing-site pages; `data/reference/leads/connecticut.csv` | `raw/region_connecticut/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_connecticut_fp.py` | Floor-plan pages of one website template used by several CT buildings ("Name | region harvest (connecticut) | building and listing-site pages; `data/reference/leads/connecticut.csv` | `raw/region_connecticut/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_connecticut_probe.py` | Probe helper for the Connecticut region pass: polite fetch (robots, >=2 s/host, bot-wall stop) of building pages into raw/region_connecticut | region harvest (connecticut) | building and listing-site pages; `data/reference/leads/connecticut.csv` | `raw/region_connecticut/` cache or stdout | no | none | one-off harvest (done); referenced by nothing |
| `h_region_connecticut_sites.py` | Connecticut region pass, stage 2: read each building's own leasing site (URL from Apartment List's website_url or from the hand list EXTRA b | region harvest (connecticut) | building and listing-site pages; `data/reference/leads/connecticut.csv` | `raw/region_connecticut/` cache or stdout | no | none | one-off harvest (done); referenced by nothing |
| `h_region_connecticut_sm.py` | Connecticut region pass: read SightMap embeds on building leasing sites (unit number, floor, price, date) | region harvest (connecticut) | building and listing-site pages; `data/reference/leads/connecticut.csv` | `raw/region_connecticut/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_connecticut_text.py` | Print the visible text of a page (polite fetch into raw/region_connecticut/), optionally only windows around a regex | region harvest (connecticut) | building and listing-site pages; `data/reference/leads/connecticut.csv` | `raw/region_connecticut/` cache or stdout | no | none | one-off harvest (done); referenced by nothing |
| `h_region_connecticut_trulia.py` | read the Trulia detail page of every Trulia lead in data/reference/leads/connecticut.csv (building pages first, t | region harvest (connecticut) | building and listing-site pages; `data/reference/leads/connecticut.csv` | `raw/region_connecticut/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_mid_hudson.py` | Putnam, Dutchess, Orange, southern Ulster | region harvest (mid_hudson) | building and listing-site pages; `data/reference/leads/mid_hudson.csv` | `data/listings_raw/region_mid_hudson.csv`, `data/reference/region_buildings_mid_hudson.csv` | no | none | one-off harvest (done) |
| `h_region_mid_hudson_add.py` | Second pass for mid_hudson (2026-11-15): buildings read from their own leasing sites, manager portfolios (Bottini Properties, Eastdale Villa | region harvest (mid_hudson) | building and listing-site pages; `data/reference/leads/mid_hudson.csv` | `data/listings_raw/region_mid_hudson.csv`, `data/reference/region_buildings_mid_hudson.csv` | no | none | one-off harvest (done) |
| `h_region_mid_hudson_recheck.py` | Re-label mid_hudson rows after the dog weight gate moved from 40 lb to 25 lb (2026-11-15) | region harvest (mid_hudson) | building and listing-site pages; `data/reference/leads/mid_hudson.csv` | `raw/region_mid_hudson/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_nassau.py` | Nassau County, NY (docs/REGION_AGENT_BRIEF.md) | region harvest (nassau) | building and listing-site pages; `data/reference/leads/nassau.csv` | `data/listings_raw/region_nassau.csv`, `data/reference/region_buildings_nassau.csv` | no | none | one-off harvest (done) |
| `h_region_suffolk.py` | Region inventory, building-first: Suffolk County, NY (docs/REGION_AGENT_BRIEF.md) | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `data/listings_raw/region_suffolk.csv`, `data/reference/region_buildings_suffolk.csv` | no | none | one-off harvest (done) |
| `h_region_suffolk_al.py` | Suffolk region pass: Apartment List property pages (robots-allowed, cached via h_apartmentlist.fetch) summarised: pet policy, elevator ameni | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `raw/region_suffolk/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_suffolk_alcity.py` | Suffolk region pass: enumerate Apartment List property slugs per town (city SRP pages, robots-allowed). | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `raw/region_suffolk/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_suffolk_build.py` | Suffolk County, NY - build stage (docs/REGION_AGENT_BRIEF.md) | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `data/listings_raw/region_suffolk.csv`, `data/reference/region_buildings_suffolk.csv` | no | none | one-off harvest (done) |
| `h_region_suffolk_facts.py` | Hand-read building facts for the Suffolk region pass (docs/REGION_AGENT_BRIEF.md) | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `raw/region_suffolk/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_suffolk_greystar.py` | Suffolk region pass: re-read the cached Greystar property pages of the Suffolk communities (plain HTML flight payload, same parse as h_mgmt_ | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `raw/region_suffolk/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_suffolk_probe.py` | Suffolk region pass: polite fetch (robots checked, >= 2 s/host, cached in raw/region_suffolk) of leasing-site pages, printing keyword contex | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `raw/region_suffolk/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_suffolk_zcity.py` | Suffolk region pass: Zumper city pages (allowed path /apartments-for-rent/<city>) -> building-page links found. | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `raw/region_suffolk/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_suffolk_zumper.py` | Suffolk region pass: Zumper building / listing pages (robots-allowed paths, cached via h_zumper.fetch) summarised | region harvest (suffolk) | building and listing-site pages; `data/reference/leads/suffolk.csv` | `raw/region_suffolk/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_westchester_rockland.py` | Westchester and Rockland counties, NY | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `data/listings_raw/region_westchester_rockland.csv`, `data/reference/region_buildings_westchester_rockland.csv` | no | none | one-off harvest (done) |
| `h_region_westchester_rockland_al.py` | building enumeration through Apartment List town pages | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `raw/region_westchester_rockland/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_westchester_rockland_data.py` | Hand-recorded building facts for the westchester_rockland region pass | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `raw/region_westchester_rockland/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_westchester_rockland_grep.py` | Ad-hoc reader for the region pass: fetch one page through polite_get (cache raw/region_westchester_rockland/) and print the text around a re | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `raw/region_westchester_rockland/` cache or stdout | no | none | one-off harvest (done); referenced by nothing |
| `h_region_westchester_rockland_probe.py` | probe a building's own leasing site | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `raw/region_westchester_rockland/` cache or stdout | no | none | one-off harvest (done); referenced by nothing |
| `h_region_westchester_rockland_trulia.py` | read the Trulia detail page of every Trulia lead in data/reference/leads/westchester_rockland.csv (build | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `raw/region_westchester_rockland/` cache or stdout | no | none | one-off harvest (done) |
| `h_region_westchester_rockland_trulia_zip.py` | list every Trulia rental BUILDING card (any price, studio/1BR filter) in the region's ZIPs, so buildings | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `raw/region_westchester_rockland/` cache or stdout | no | none | one-off harvest (done); referenced by nothing |
| `h_region_westchester_rockland_zb.py` | read Zumper building pages for named buildings (facts only: pets block, amenity tags, floors, units, des | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `raw/region_westchester_rockland/` cache or stdout | no | none | one-off harvest (done); referenced by nothing |
| `h_region_westchester_rockland_zumper.py` | building enumeration through Zumper town pages (discovery only) | region harvest (westchester_rockland) | building and listing-site pages; `data/reference/leads/westchester_rockland.csv` | `raw/region_westchester_rockland/` cache or stdout | no | none | one-off harvest (done); referenced by nothing |

### Added 2026-11-17: the concierge page and live-check batch 21

| Script | Purpose | Stage | Inputs | Outputs | Run by `run_all` | Tests | Status |
|---|---|---|---|---|---|---|---|
| `concierge_data.py` | Data of the second page: keeps apartments whose listed rent as it now stands is at or under $2,000, recomputes every figure over them, runs the text builders and guards over that set (`--data`, `--out-suffix _u2000`), and writes the data contract. Added 2026-11-17: `apartments[].checked` and `buildings[].checked_summary` from the live-check rows (a `not_read` row is not a re-read), `parked_distance_km` / `parked_label` ("Also nearby" within 10 km, otherwise "Also in this kind of life"), `why` chosen from her priorities before any amenity, with `why_topic`. Options: `--no-text` (reuse the `_u2000` tables), `--self-check` (the recomputation against `site/data.json` over all apartments) | concierge | `site/data.json`, `data/evidence/live_check_batch_*.csv`, `data/reference/building_crosswalk.csv`, `data/reference/scene_text_source.txt`, `scene_text_source_u2000.csv` | `site/_concierge_base.json`, `data/reference/*_u2000.csv`, `site/concierge_data.json` | no | `test_concierge_data.py` | active |
| `test_concierge_data.py` | Tests for `concierge_data.py` and its output: rent limit, figures against a recomputation, parking of one-apartment neighborhoods and its distance label, `checked` against the live-check rows, `why` on her priorities, guarded sentences, banned words, contract shape | test | `site/data.json`, `site/_concierge_base.json`, `site/concierge_data.json`, `data/evidence/live_check_batch_*.csv` | exit code | no (run by `verify_all.py` and `verify_concierge.py`) | is a test | active |
| `verify_concierge.py` | One command for the concierge page: data build, its tests, the text check, the pick-logic tests, the page build and (`--with-browser`) the phone walk-through. It rewrites the concierge outputs; it never touches the first page | concierge check | everything above | the concierge outputs, verdict on stdout | no | none | active |
| `build_concierge.py` | Build `site/dist/concierge.html` and `concierge_artifact.html` from the template, the data, the drawings and the map (`--data` for a stand-in file) | concierge page | `site/concierge.html`, `site/concierge_data.json`, `site/illustrations.json`, map files | `site/dist/concierge.html`, `site/dist/concierge_artifact.html` | no | `test_concierge_pick.js`, `concierge_walkthrough_test.js` | active |
| `concierge_fixture.py` | A stand-in for `site/concierge_data.json` used before the real file existed (made-up sentences; never published) | concierge page test | `site/data.json` | `site/_concierge_fixture.json` | no | none | active (test fixture) |
| `test_concierge_pick.js` | Tests for the page's pick logic, read out of `site/concierge.html`; on made-up buildings and on the data file | test | `site/concierge.html`, `site/concierge_data.json` | exit code | no | is a test | active |
| `concierge_walkthrough_test.js` | Phone walk-through of the built concierge page (Playwright, no network) with screenshots | test | `site/dist/concierge.html` | `site/screens/concierge-*.png` | no | is a test | active |
| `live_check_batch_21.py` | Live-check batch 21 (2026-11-17): the 45 apartments at or under $2,000 re-read on each building's own, its manager's or an allowed listing site; `get` fetches (cached, robots-checked), `text` prints a cached page, `write` rebuilds the CSV with no network. Introduced the status `not_read` (the page could not be read: nothing learned; `parsers.live_row_learned`) | evidence batch 21 | the sites named in `docs/harvest_notes/live_check_batch_21.md`, `site/data.json` | `raw/live_check_b21/` (its `render/` folder is git-ignored), `data/evidence/live_check_batch_21.csv` | no | none | one-off harvest (done) |

Options and rules added to existing scripts on 2026-11-17:

- `realtor_lines.py --data <page data> --out <csv> --out-buildings <csv>`, `build_scene_text.py --data <page data> --out-suffix <suffix>`,
  `check_scene_text.py --data ... --out-suffix ...`, `check_published_text.py --data ... --out-suffix ... --text-only`: run the same drafts
  and guards over another page-shaped file (the concierge base) and write to suffixed tables; draft fields for that set are replaced from
  `data/reference/scene_text_source<suffix>.csv` (kind, id, field, draft, why). Without the options the scripts behave as before.
- `parsers.live_row_learned`, `live_rows_learned`, `latest_live_row`: a live-check row with status `not_read` learned nothing. `build_master.py`,
  `avoid.py` and `rent_terms.py` drop such rows, so one never replaces an earlier `live` / `changed` / `gone` row, sets no date, and is not an
  open item. The row stays in the evidence files and in the verdict fingerprint (`verdicts.py`), so a reviewer reads its note and writes
  anything it found as a verdict. Tests: `test_rules.py` `pure_b21`, `data_b21`.
- `build_scene_text.py`: `{stationkind}` is missing (its tests fail, inside `[[ ]]`) for a neighborhood with nothing shown.
