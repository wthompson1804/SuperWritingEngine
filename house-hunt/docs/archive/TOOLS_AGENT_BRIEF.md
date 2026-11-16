# Lookup-tool agent brief (shared contract)

The page now compares individual buildings, so each data domain must be a **lookup tool that answers for any
address (lat/lon)**, not a table for 98 fixed areas. Read `CLAUDE.md` and `docs/PLAN_V3_APPROVED_2026-11-15.md`.
Project root: `/home/user/SuperWritingEngine/house-hunt`. An earlier agent in your domain was interrupted: reuse
its partial script(s) and the caches under `raw/` (listed in your task) instead of starting over.

## Output contract

1. `scripts/tools/<domain>.py`: an importable module with the function(s) named in your task, plus a
   `__main__` self-test that runs the function for these points and prints the results:
   Jamaica station (40.699608,-73.808530), Forest Hills (40.7196,-73.8448), Long Beach NY (40.5890,-73.6649),
   Stamford CT (41.0469,-73.5419), Jersey City Grove St (40.7196,-74.0431), Beacon NY (41.5060,-73.9845).
   Every function returns a dict of values **plus provenance**: for each value a `source_url`, `retrieved_at`
   (or data vintage), `value_type` (found / estimate / not_found) and `method` for estimates. Never invent;
   unknown is not_found with the reason.
2. Any reference tables in `data/reference/<name>.csv` with a `source_url` column.
3. Prebuilt indexes or big downloads in `raw/big/<domain>/` (git-ignored), rebuilt by the script if missing.
   Lookups must be fast (well under 2 s per point after the index is built), since they'll run for ~1,000 buildings.
4. `docs/tools_notes/<domain>.md`: sources, methods, coverage and gaps, caveats, run time per lookup.
5. Use `scripts/lib.py` `cached_get` / `get_json` for HTTP. Respect robots.txt (groups naming Claude apply to us)
   and crawl delays. Don't edit `lib.py`, `CLAUDE.md`, `PROGRESS.md`, `SOURCES.md` or other agents' files. Don't commit.
   The Census API key is available via `lib.census_key()` (logs are redacted; never write the key anywhere).
   The FBI CDE API at api.usa.gov gets its key injected by the proxy: send none.
6. Final reply to the coordinator, under 200 words: what works, what's missing, anything needing Will's decision.
