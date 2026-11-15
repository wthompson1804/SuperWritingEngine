# Phase 1 agent brief (shared contract)

You are one of several parallel agents collecting **structured public data** for 98 areas in the
NYC region. The data feeds a later decision tool for one renter, Lamia: about 30, works from home,
parents in Jamaica, Queens. **Collect facts only. Do not rank, score or recommend.**

Project root: `/home/user/SuperWritingEngine/house-hunt`. Read `CLAUDE.md` (working rules) and
`docs/DATA_DICTIONARY.md` (the `area_metrics` schema) first. Areas are in `data/areas.csv`
(id, centroid_lat/lon, county_fips, municipality, place_geoid, cousub_geoid, tract_geoid,
zcta_centroid, zctas_within_800m, anchor and nearest stations, police_jurisdiction). The travel anchor is
**Jamaica LIRR station, LIRR GTFS stop_id 102 (40.699608, -73.808530)**.

## Output contract

1. **Script(s):** `scripts/p1_<domain>.py`, idempotent and resumable. Use `scripts/lib.py`
   (`cached_get` / `get_json`) for every HTTP call, so responses are cached in `raw/<source>/`
   with an `_index.jsonl`. Big bulk files go in `raw/big/<source>/` (git-ignored); the script must
   re-download them if they're missing. Don't edit `lib.py`, `areas.csv`, `PROGRESS.md` or `SOURCES.md`.
   If you need a helper, put it in your own script.
2. **Data:** `data/metrics/<domain>.csv` with exactly these columns, in this order:
   `area_id,domain,metric,value,unit,geography,period,source,source_url,retrieved_at,raw_path,value_type,method,population_used,notes`
   * One row per area × metric × source × period. Never blend sources into one number.
   * **Every area gets every metric you own**: if you looked and found nothing, write a row with
     `value_type=not_found`, an empty value and `notes` saying where you looked. Computed or modelled
     numbers are `value_type=estimate`, with `method` filled in.
   * `source_url` must be a URL that leads to the data (an API call, a file download or a page).
     A file name alone isn't enough.
3. **Notes:** `docs/phase1_notes/<domain>.md`: sources and exact URLs, methods, what failed or was
   blocked and why, coverage (areas × metrics found / estimate / not_found), caveats, and anything
   surprising. Plain facts.
4. **Don't commit to git.** The coordinating session commits.

## Rules

* Never invent a value. Never take a number from a search-result snippet. Go to the source page or file.
* Respect robots.txt and terms. Throttle; prefer official APIs and bulk downloads. Don't get around logins or CAPTCHAs.
* Network is open through a proxy (curl and requests already work). The FBI CDE API at
  `api.usa.gov` has a key injected by the proxy as the `X-Api-Key` header, so send no key yourself.
  There's **no Census API key** (api.census.gov redirects to missing_key), so use Census bulk files on www2.census.gov.
  There's no Google, TomTom, HERE, Walk Score, Reddit or YouTube key.
* Don't collect racial, ethnic or religious composition.
* Disk is limited (about 25 GB free, shared). Delete intermediate extracts you no longer need.
* Keep bulk output out of your own context: write to disk and print summaries.
* If a source is blocked or a target can't be met, say so plainly in your notes and in your final reply.

## Final reply to the coordinator

Under 250 words: files written, rows by value_type, which metrics are weak or missing and why, and anything
that needs a decision from Will.
