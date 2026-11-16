# Lamia House Hunt

A data pipeline plus a published single-file decision page for one apartment search: a studio or one-bedroom for
Lamia and a dog, in an elevator building, at $3,000 a month all-in or less, within a two-hour drive of her parents
in Jamaica, Queens, available by December 15, 2026.

The pipeline harvests listings, applies the owner's gates, looks up facts for every passing building, costs and
ranks the units, checks them against collected evidence, and writes one JSON file. The page reads that file and
walks her through six "experiences", their neighborhoods, buildings and apartments, with a list and a compare view.

- Rules for anyone working here: `CLAUDE.md`. Current state and counts: `PROGRESS.md`.
- How the stages fit together: `docs/ARCHITECTURE.md`. Every document: `docs/README.md`.
- Every script: `scripts/README.md`. Every data file: `docs/DATA_DICTIONARY.md`.

## Quick start

Run from this folder (`house-hunt/`), in this order:

```
python3 scripts/run_all.py            # tests, gates, lookups, master tables, cost, evidence rules, ranking, checks
                                      #   --fast skips the neighborhood and lifestyle rebuild (after evidence-only changes)
python3 scripts/build_page_data.py    # data/ranked_units.csv and friends -> site/data.json
python3 scripts/page_data_extras.py   # adds text, quotes, local rules, contacts, ratings, photo links to site/data.json
python3 scripts/build_site.py         # site/index.html + data -> site/dist/index.html (one file, opens from disk)
python3 scripts/build_artifact.py     # publish step: site/dist/index.html -> site/dist/artifact.html (the file that is published)
```

`run_all.py` writes `docs/RUN_REPORT.md` (counts in and out of every stage, with reasons) and exits non-zero if a step
fails or a shown unit breaks a rule. Publish the built page as a **new private artifact**; never replace the mock.

A full run uses cached lookups; new buildings need the network (about 2 seconds each) and the Census key.
`--fast` and the three page steps need no network.

When evidence is added or a unit is newly promoted, the review rule applies before it can be shown:
`python3 scripts/verdicts.py digest`, read it, `python3 scripts/verdicts.py add <file>`, rerun.

## Tests

| Command | What it guards |
|---|---|
| `python3 scripts/test_parsers.py` | Every text parser, on the example strings from the first independent check. First step of `run_all.py`. |
| `python3 scripts/test_rules.py` | The rules, on the cases from the second and third checks. Second step of `run_all.py`. |
| `python3 scripts/test_rules.py --data` | The same defects, checked on the pipeline's output and on `site/data.json`. Run by `run_all.py` after ranking. |
| `python3 scripts/check_registry.py` | Every field accounted for; every shown unit obeys the gates and has a reviewed verdict. Last step of `run_all.py`. |
| `python3 scripts/check_scene_text.py` | Every number and claim in the written scene text still matches the data. Run by hand. |
| `python3 scripts/test_realtor_lines.py` | The composed "About the building" and per-unit lines. |
| `python3 scripts/test_page_data_extras.py` | The extras step and the publish step: each block, idempotence, the quote screen, contacts, ratings. |
| `python3 scripts/test_shortlist_tools.py` | Call sheet, tour days and re-check tools (synthetic rows, no network). |
| `node scripts/site_walkthrough_test.js` | The page itself at 390, 1280 and 320 px (usage in the file header; needs `site/` served locally). |
| `node scripts/map_component_test.js` | The standalone map demo. |
| `python3 scripts/check_repo.py` | Read-only hygiene report: big files, orphan CSVs and scripts, broken document references, key-like strings. |

## Where things live

| Path | What |
|---|---|
| `seeds/` | Hand-entered inputs (the phase-1 area list). |
| `raw/` | Cached responses, one folder per source, each with `_index.jsonl` (url, time, status). About 12 GB on disk; HTML and the largest downloads are not committed. |
| `data/listings_raw/` | One harvest file per source. `data/listings.csv`: all of them merged, deduped and gated. |
| `data/units.csv`, `data/master_units.csv`, `data/master_buildings.csv` | Passing units with lookups; the two master tables every later step reads. |
| `data/evidence/` | Evidence batches (live checks, confirmations, facts, dated items, ratings), city records, reviewed verdicts. |
| `data/ranked_units.csv` | The ranked list with every flag the page needs (`shown`, `avoid_card`, asterisks, disclosures). |
| `data/reference/` | Lookup tables, reviewed tables, written text, the field registry, run history. |
| `data/voices/` | Resident quotes and survey figures per neighborhood. |
| `scripts/` | Pipeline, harvesters, lookup tools (`scripts/tools/`), tests. |
| `site/` | `index.html` (template), `data.json`, `map_base.json`, `illustrations.json`, `dist/` (built page), `screens/` (review screenshots). |
| `out/` | Call sheet, tour days, re-check results. |
| `docs/` | Rules, plans, notes, independent checks and repairs. |

## Counts

As of 2026-11-16, after the repairs that followed the third independent check (`PROGRESS.md`; the run history is
`data/reference/run_history.csv`). Counts move with every run: `docs/RUN_REPORT.md` is the current figure.

| Stage | Count |
|---|---|
| Listings harvested, after dedupe | 20,464 |
| Pass every listing gate | 2,659 (13,534 pending on an unstated gate fact; 4,271 fail) |
| Costed in the master table | 2,632 (27 duplicates merged) |
| Within the $3,000 all-in cap | 1,613 |
| Ranked | 763 |
| **Shown** | **489 units in 232 buildings, 104 neighborhoods** (42 with three or more) |
| Shown with one open item (asterisk) | 293 |
| Avoid cards / held for one confirmation / waiting for a live check | 34 / 35 / 35 |
| Reviewed verdicts | 792 rows for 791 units (ok 445, asterisk 155, disclose 20, remove 172) |

By experience (units / buildings): Little-City 202 / 87, Room-to-Breathe 124 / 46, Old-Neighborhood 85 / 63,
Fresh-Start 63 / 24, Quiet-Street 10 / 7, Walk-Everywhere 5 / 5. By state: NJ 244, CT 135, NY 110.

## Environment

- Python 3.13. Packages the pipeline imports: `pandas`, `numpy`, `requests`, `scipy`, `shapely`, `pyproj`, `tabulate`
  (for `DataFrame.to_markdown`). Harvest and setup scripts also use `bs4`, `lxml`, `pdfplumber`, `geopandas`,
  `osmium`, `pyshp`. `shapely` and `pyproj` are not preinstalled: `pip install shapely pyproj` in a fresh container
  (there is no setup script yet).
- Node with Playwright and Chromium for the page tests and the few rendered harvests.
- **Census API key**: kept outside the repo at `/root/.config/house-hunt/census_api_key`, read by `lib.census_key()`,
  stripped from every logged URL by `lib.redact()`. Re-create the file in a new container (ask Will). Never put its
  value in chat, code, data or logs.
- **api.data.gov key** (FBI Crime Data Explorer): an environment network secret for `api.usa.gov`, injected by the
  proxy. It is not in code or in environment variables.
- **Cloud environment**: "SuperWritingEngine house-hunt data" (personal, unrestricted network). The Default
  environment blocks every data source.
- Branch: `claude/lamia-house-hunt-data-fdrkrs` in `wthompson1804/SuperWritingEngine`. This folder is the whole project.

## What is not automated

- **Trulia is blocking us** (403 / CAPTCHA since the evening of 2026-11-15). No Trulia requests are sent. 217 shown
  units are Trulia rows that cannot be re-read.
- **Phone calls.** 293 shown units carry one thing to confirm, and most disclosures are tour or phone questions.
  `scripts/call_sheet.py` writes the questions; answers typed into `data/evidence/call_answers.csv` (format in
  `docs/SHORTLIST_TOOLS.md`) outrank every other source on the next run. That file does not exist yet.
- **Live checks.** 178 shown units have never been seen live; `scripts/recheck_shortlist.py` re-reads a short list by hand.
- **The ratings census is partial.** There is no Google Places key; ratings come from what a web search showed, are
  shown as information only, and buildings never searched say "Not looked up yet".
- **Reviewed verdicts** are written by a person or a reviewing agent reading the evidence, not by a rule.
- **Harvests are not part of `run_all.py`.** Listing harvesters, evidence batches, local rules, voices and
  neighborhood descriptions were each run once by an agent (`scripts/README.md`). Craigslist is manual only.
- **The Zumper opened-listings file** (`data/listings_pending/`) is not merged.
- **Written text** (`data/reference/scene_text_source.txt`) is hand-written; `scripts/check_scene_text.py` only checks it.
- Also open: the Manhattan congestion-zone mail toll rate, a Reddit key, `si-inventory.csv` (never uploaded).
