# PROGRESS

Read this first every session. Newest entries at the top of the log.

## Current state (2026-11-15, end of day)

**Authorities, newest first:** `docs/PLAN_V4_MASTER_MODEL_2026-11-15.md` → `docs/RANKING.md` (v2) → `docs/SAFETY_BASIS.md`
→ `docs/PLAN_V3_APPROVED_2026-11-15.md` (gates; dog limit 25 lb; size-only "small dogs" passes) → UX brief and mock-up 4 (layout only).
The "data only, no UI, no ranking" lines in `CLAUDE.md` and the handoff brief are superseded: the job is now the finished decision page.

**Run everything:** `python3 scripts/run_all.py` (`--fast` after evidence-only changes) → `scripts/build_page_data.py` →
`scripts/build_site.py` → `site/dist/index.html`. Publish as a NEW private artifact (never replace the mock).

**Latest run:** 20,464 listings → 2,598 pass listing gates → 1,653 within the all-in cap → 995 ranked → **344 shown**
(194 with an asterisk: floor 159, live check 31, elevator 4, dogs 2), 36 avoid cards, 63 held. 132 neighborhoods on the page.
By year: Little-City ~119, Old-Neighborhood ~93, Room-to-Breathe ~91, Fresh-Start 24, Walk-Everywhere 10, Quiet-Street 9.

| Piece | Status |
|---|---|
| Master tables, rent terms, all-in cost, ranking v2, avoid rules, registry check | Done |
| Evidence rounds 1–3 (batches 1–17), NYC records, non-NYC records, rating standard | Done |
| Checker findings reach the list (`scripts/avoid.py`): age/income-restricted, waitlist, rented, dead listing, pet-free, "probably no elevator" readings, confirmed or probable ground-floor units | Added after round 3 showed they were being missed |
| Elevator "inferred from height" needs a real building height (page or record, 6+ floors); a height guessed from a unit label ("36D") no longer counts (`scripts/rank.py`) | Done |
| First independent check + repairs (`docs/INDEPENDENT_CHECK.md`, `docs/REPAIRS_AFTER_INDEPENDENT_CHECK.md`) | Done |
| Second independent check (`docs/INDEPENDENT_CHECK_2.md`) | Running; fix what it finds, then publish the draft |
| Neighborhood voices: 890 verified quotes, 79 neighborhoods, 873 from Niche | Done; 53 later neighborhoods have none |
| Local rules (parking, dogs) for 34 of 56 municipalities | Done |
| Trulia | Blocking us (403/CAPTCHA) since the evening of Nov 15. No Trulia requests until a single test on Nov 16. About 100 NYC shown units cannot be re-checked until then |
| Jersey City split into neighborhoods; written scene text; photos; MTA toll rates (Will); Reddit key (Will) | Open |

**Robots lapses to remember (told to Will):** the voices agent restarted after a Niche 403 (21 neighborhoods; quotes kept pending Will's call);
evidence batch 13 sent six more Trulia requests after the first refusals. Agent briefs must say: one refusal ends that host for the session.

## Answers from Will (2026-11-15), which override the handoff brief

| Question | Answer | Effect |
|---|---|---|
| Stretch ceiling | **$3,000 listed rent** (the brief had $3,200) | Tiers: `comfortable` ≤ 2,400; `at_cap` 2,401–2,800; `stretch` 2,801–3,000. Collect nothing above $3,000. |
| Move-in | **December 1, 2026** (Will, 2026-11-15, second answer; it replaced "December only", which replaced the brief's "Dec preferred, Jan latest") | Inventory must be available on or before Dec 1. `move_in_fit` = `ready_by_dec1` / `after_dec1` / `unknown`. |
| Browser automation | **Allowed** (Playwright, headless) within robots rules, throttled, no getting around logins or CAPTCHAs | |
| Philadelphia | **Benchmark only** | R8 gets area metrics only; no inventory or quotes unless Will says otherwise. |
| API keys | Will didn't know how to get them and said to get them if I could. I can't sign up on his behalf, so he signed up for an **api.data.gov key**, which is saved as an environment network secret for `api.usa.gov` (FBI Crime Data Explorer; header injected by the proxy, never in code or env vars). Will then pasted a **Census API key** in chat. It's stored outside the repo at `/root/.config/house-hunt/census_api_key` (re-create it in a new container; ask Will), read via `lib.census_key()`, and `lib.redact()` strips it from every logged URL. | Routing with traffic, Reddit, YouTube and Walk Score: **no keys**. Drive times are OSRM free-flow, labelled `estimate`. Reddit's JSON API returns 403 without auth; see SOURCES.md. |
| Visit frequency | Not asked; still **assumed weekly** | Only matters for travel-cost rollups. |

## Environment

- This work lives in `house-hunt/` inside the `wthompson1804/SuperWritingEngine` repo, on branch
  `claude/lamia-house-hunt-data-fdrkrs` (the session's assigned branch; there was no separate data repo).
- Cloud environment **"SuperWritingEngine house-hunt data"** (personal) with **unrestricted network**,
  created 2026-11-15 because the Default environment blocked every data source. The Default environment was left unchanged.
- Python 3.13 with pandas, requests, bs4, lxml, pdfplumber; `shapely` and `pyproj` were pip-installed (no setup
  script yet; re-run `pip install shapely pyproj` in a fresh container). Playwright Chromium is preinstalled.

## Known gaps and caveats

- `si-inventory.csv`, referenced in the brief, is **not in the repo**. The Staten Island seed facts exist
  only as text in `docs/HANDOFF_2026-11-15.md` §10. Ask Will to upload the CSV.
- NJ Transit rail GTFS: the official feed needs a developer login, so we use the MobilityData mirror, whose calendar
  **ended 2026-11-08**. Its station coordinates are fine; its schedules are stale and must be labelled as such or replaced.
- Police jurisdiction outside NYC is an analyst assignment marked UNVERIFIED in `areas.csv`.
- CT rows: Census now uses planning regions instead of counties (for example "Western Connecticut").

## Open questions for Will

1. Upload `si-inventory.csv` (the Staten Island inventory verified Nov 15).
2. Is weekly still the right visit frequency?

## Log

### 2026-11-15, session 1 (after midnight UTC-side): ranking v2 and evidence pass
- **Safety rule final:** neither violent nor property crime may exceed Jamaica's precinct (9.8 / 25.0 per 1,000); lower ranks higher.
- **Ranking v2 approved and implemented** (`scripts/rank.py`, `docs/RANKING.md`): sketchy listings dropped; eight parts
  (safety 22, building 16, cost 12, car 12, space 12, distance 10, dog 8, daily life 8); 70% universal + 30% the year's promise;
  pool bump +3 / indoor +6; closer to her parents is better; five-point spectrum against staying in Queens for the compare screen
  (calculations stay in the background, shown on a click). Building amenities: `data/reference/building_amenities.csv`.
- **Evidence pass running** on the 264 candidate units / 208 buildings (top 15 per neighborhood): 6 batch agents
  (`docs/EVIDENCE_AGENT_BRIEF.md` → `data/evidence/*_batch_<n>.csv`), one NYC public-records agent (`data/evidence/nyc_records*.csv`),
  and one agent adding **Envy by Gomes, 58 Norfolk St, Newark** at Will's request (`data/listings_raw/manual.csv`).
- After evidence lands: write `scripts/avoid.py` (apply thresholds to dated evidence; management judged on last 6 months), drop units
  that are gone or unconfirmed, then rerun everything once the 5 region agents and Apartment List's outer ring finish
  (Will: "we'll run another pass once the remainder comes in").

### 2026-11-15, session 1 (late night): groups and safety rule settled
- **Lifestyle groups approved** (6 groups; `scripts/lifestyle_groups.py`, centres saved in `data/reference/lifestyle_group_centres.csv`
  so later runs assign new neighborhoods to the same groups; `--refit` only on purpose). Labels + subheads are in that script's `LABELS`
  (Will wants evocative labels with a plain subhead; current set is a proposal awaiting his reaction).
- **Safety rule (Will):** violent crime above Jamaica's precinct rate (9.8 per 1,000) = cut; property crime above Jamaica's = flag only.
  See `docs/SAFETY_BASIS.md`. Benchmarks vs US / metro / local: `scripts/crime_benchmarks.py`.
- We do **not** collect detached houses: all passing units are in elevator buildings; "detached share" describes the surrounding tract.
- Trulia "Small dogs only" listings pass the dog gate with a tour question about the weight limit (Will has not objected).
- Pipeline order now: `gates.py` → `enrich_nyc_pluto.py` → `gates.py` → `enrich_units.py` → `build_neighborhoods.py` →
  `lifestyle_features.py` → `lifestyle_color.py` → `crime_benchmarks.py` → `lifestyle_groups.py`.
- Still to do: fold `places.color()` into portraits; split Jersey City into its neighborhoods; rerun everything when the 5 region agents,
  Apartment List outer ring and remaining Trulia targets finish; selection algorithm (design proposed to Will, not yet approved);
  avoid list; evidence table and text; page build.

### 2026-11-15, session 1 (night): checkpoint A feedback from Will
- **Rejected** grouping years by drive band and setting. Years must group by **lifestyle, not location** ("places that rhyme").
  Interim analysis in `docs/LIFESTYLE_ANALYSIS.md`; rerun after the regional agents finish, then bring names to Will.
- **Anything that passes the gates stays** in the data. A separate **selection algorithm** must cut each neighborhood to the
  best-value 10 (optimizing the trade-offs). Not written yet: design it, get Will's approval, implement.
- **Thorough over fast**: pull Long Island, Hudson Valley and Connecticut inventory. Five building-first region agents launched
  (`docs/REGION_AGENT_BRIEF.md`; outputs `data/listings_raw/region_*.csv`, `data/reference/region_buildings_*.csv`).
- Elevator may be inferred for buildings of 6+ floors (asterisk). NYC elevator status comes from PLUTO building class.
- Pipeline order to rerun after new listings: `gates.py` → `enrich_nyc_pluto.py` → `gates.py` → `enrich_units.py` →
  `build_neighborhoods.py` → `lifestyle_features.py`.
- State at this point: 610 units in 271 buildings pass every gate incl. all-in ≤ $3,000; 103 neighborhoods, 40 with 3+ places.
- Still open: MTA toll rates (Will to paste), Reddit API key (Will), Craigslist is manual-only.

### 2026-11-15, session 1 (later)
- Will's later decisions: move-in window now through **Dec 15**; tours from **Nov 22**; all-in cap **$3,000** incl. estimated utilities;
  dogs must be explicitly allowed (limit ≥ 40 lb); **elevator buildings only, no ground-floor units**; Queens first excluded, then **re-included**;
  up to 10 places + up to 5 avoids per neighborhood; years and all wording data-driven; publish as a new private artifact;
  keys: Will will get a **Reddit API app** only (no Google key → drive times stay free-flow estimates). "Get what you can, say what's missing."
- Source-access results in `docs/SOURCES.md`; Claude-specific robots rules apply to us (Niche, City-Data, Yelp, Zillow listings off limits).
- First round of Phase 1 agents was interrupted; ACS finished. Relaunched as lookup tools + harvest agents.

### 2026-11-15, session 1
- Network: Default environment blocked all sources. Created a personal environment, moved the session onto it, set it to unrestricted (Will approved).
- Asked Will the §6 questions (answers above).
- Scaffolded `house-hunt/`: `CLAUDE.md`, `docs/HANDOFF_2026-11-15.md` (brief verbatim), `docs/DATA_DICTIONARY.md`, `scripts/lib.py` (cached, throttled fetch with an index log).
- Built `data/areas.csv` (98 areas, 0 build problems) from `seeds/areas_seed.csv` with `scripts/build_areas.py`:
  centroid from the GTFS anchor station or a Nominatim geocode; Census Geocoder admin geography; ZCTAs at the centroid and on an 800 m ring;
  NYPD precinct by point-in-polygon. Fixed: Huntington, Shelton and Downtown Brooklyn centroids, non-revenue stops, NJ/CT municipality names.
- GTFS cached in `raw/gtfs/`: LIRR, MNR, subway (incl. SIR) from MTA; NJT rail, PATH and SEPTA rail from the MobilityData mirror.
- Source-access tests are running in a subagent, writing `docs/SOURCES.md`.
