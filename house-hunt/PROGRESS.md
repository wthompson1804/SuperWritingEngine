# PROGRESS

Read this first every session. Newest entries at the top of the log.

## Current state (2026-11-16, after the owner's "no not-re-checked flag" rule)

**Authorities, newest first:** `CLAUDE.md` (rules and decision log) → `docs/RANKING.md` (rewritten as ONE current statement of the gates, the elevator rule,
duplicates, score and selection, with a change log) → `docs/PLAN_V4_MASTER_MODEL_2026-11-15.md` → `docs/SAFETY_BASIS.md` → `docs/PLAN_V3_APPROVED_2026-11-15.md` → UX brief and mock-up 4 (layout only).
The job is the finished decision page.

**Run everything:** `python3 scripts/run_all.py` (`--fast` after evidence-only changes; tests first, `check_registry.py` last) → `scripts/build_page_data.py` →
`scripts/page_data_extras.py` → `scripts/build_scene_text.py` → `scripts/check_scene_text.py` → `scripts/realtor_lines.py` → `scripts/test_realtor_lines.py` →
`scripts/page_data_extras.py` → `scripts/build_site.py` → `site/dist/index.html`. **The text check (`check_scene_text.py`) is a separate step after
`page_data_extras.py`; `run_all.py` does not run it.** Publish as a NEW private artifact (never replace the mock).

**Counts now**: 20,468 listings → 2,505 pass the listing gates → 2,451 costed → 1,480 within the all-in cap → 733 ranked →
**568 apartments shown in 212 buildings, 78 neighborhoods** (52 with three or more). Before the rule below it was 446 / 191 / 68.
By experience (apartments / buildings / neighborhoods): Little-City 248 / 83 / 23, Room-to-Breathe 155 / 39 / 23, Old-Neighborhood 81 / 57 / 21,
Fresh-Start 75 / 27 / 6, Quiet-Street 6 / 3 / 3, Walk-Everywhere 3 / 3 / 2. **209 shown apartments carry one open item, every one a gate fact**
(elevator 96, listing 65, dogs allowed 31, eligibility 11, availability 6); 359 carry none. 71 rows are `not_an_apartment`; 28 single-apartment
neighborhoods are cut by the thin-neighborhood rule and 10 kept. Verdicts: 916 rows for 915 units (ok 536, asterisk 161, disclose 21, remove 198).
Two consecutive runs give an identical `data/ranked_units.csv`; `check_registry.py` and all tests pass (`test_rules.py`: 428 pure checks; `--data` on the
output: 3,868 with the page data; `test_parsers.py`: 259).

**Owner's rule, 2026-11-16 ("Forget call check"): no "not re-checked" flag.** A listing that was simply never re-read in an evidence pass (live status
blank, not checked, blocked: for example the Trulia rows that cannot be re-read) is not an open item: no asterisk, and it counts in no rule (not in "two or
more open", not in the thin-neighborhood rule, not as the second open item beside an elevator doubt, not in the order among equal scores). What a re-read
FOUND still counts through the facts that already existed (gone → removed; price changed → updated; a stale page, a page for another building, a "verify the
price" note → "listing" / "availability"). Reviewed verdicts are still required. Effect: 124 apartments entered (114 had "no live check" as their second open
item beside one gate fact: elevator 57, listing 30, dogs 16, eligibility 6, availability 5; 9 sit in neighborhoods that are no longer single-apartment; 1 moved
up inside its building), 2 left (The Lofts at Garwood: its experience's median rose; Aviva E0721: now ninth in its building). 108 verdicts were written by
reading the evidence (79 ok, 4 asterisk, 25 remove: all 25 are unit numbers that read as first-floor units). `data/needs_live_check.csv` is no longer written;
`site/data.json` keeps `awaiting_live_check` as an empty array and `meta.counts.awaiting_live_check` = 0; each unit keeps `price_seen_at` and `live`
(status, checked_at) as information. 292 shown apartments were never re-read (266 blank, 26 blocked); nothing on them says so.

**Open after this run:** `scripts/build_scene_text.py` still exits 1 on three neighborhoods that are not on the page (Franklin, Seymour, Gravesend South;
it was six before); `verify_all.py --quick` fails one check: the two newly shown neighborhoods **Bogota and Burlington have no scene text** in
`data/reference/scene_text_source.txt`. `site/dist` is older than `site/data.json` (rebuild with `build_site.py`).

**What the consistency pass changed (2026-11-16):** one elevator rule for every stage (`parsers.elevator_rule`; a near-miss tax lot neither passes nor fails);
experiences assigned from frozen area profiles and saved parameters (East Rutherford and Patchogue are back in Little-City; four other neighborhoods are held
where they were by `data/reference/lifestyle_group_overrides.csv`, for the owner to decide); units moved out of addresses; duplicates across label spellings
(`215` = `001-215`); the Continuum is one building, not three; only real apartments (owner's rule); the thin-neighborhood rule (owner's rule); a conflicting dog
policy is one open fact, not "sketchy"; in-unit laundry no longer counts a shared laundry room; building names cleaned of listing titles; park names that are not
parks blanked; a third party's API key stripped from `photo_url` everywhere.

**Weak, plainly:** 292 of 568 shown apartments were never re-read after the first reading (by the owner's rule that is no longer flagged); 209 have a gate
fact open. Most shown elevators rest on listing sites only. Most shown floors are not published. Parking and required fees are unpublished for most shown units.
The experience profile of a neighborhood is the median over the buildings sampled there (frozen at the largest sample on record), not a census of the whole
area; 33 of 197 neighborhoods sit within 10 percent of a second experience (`data/lifestyle_group_distances.csv`). `scripts/h_trulia.py` now refuses to fetch while `trulia.com` is in `raw/_host_kill_shared.json` (it is) or without `--i-know`.

**Trulia:** blocking us (403 / CAPTCHA) since the evening of 2026-11-15. The single test on 2026-11-16 ran and Trulia still returned a CAPTCHA. **No Trulia
requests are to be sent.** Rows harvested before the block stay and cannot be re-read.

**Zumper opened pages (not merged, on purpose):** 900 pages opened; on stated facts no unit passes every gate; 168 are one fact short, 164 on the elevator
(`data/listings_pending/zumper_opened*.csv`, `docs/harvest_notes/zumper_open_pending.md`).

**Open, for the owner:** the four experience overrides (Fort Lee, West New York, Harlem South, Jersey City – McGinley Square); whether a single-home listing page
with no unit number counts as a real apartment (it does today; none is shown); Avalon W Squared (West Windsor) must not be filed under Princeton if it ever
passes; the Manhattan congestion-zone mail rate; photos; Reddit key.

**The review rule:** a unit is shown only if `data/evidence/review_verdicts.csv` holds an `ok`, `asterisk` or `disclose` verdict written against its evidence as
it stands (`scripts/verdicts.py pending / digest / add`; `check_registry.py` fails the run otherwise).

| Piece | Status |
|---|---|
| Master tables, rent terms, all-in cost, ranking v2, avoid rules, registry check | Done; rules in one statement in `docs/RANKING.md` |
| Evidence rounds 1–3 (batches 1–19), NYC and non-NYC records, rating standard | Done |
| Independent checks 1–3 and their repairs | Done (`docs/REPAIRS_AFTER_INDEPENDENT_CHECK*.md`) |
| Pipeline consistency pass (`docs/PIPELINE_CONSISTENCY_PASS.md`) | Done 2026-11-16 |
| Only real apartments; thin-neighborhood rule (owner, 2026-11-16) | Done |
| No "not re-checked" flag (owner, 2026-11-16) | Done: 568 shown in 212 buildings, 78 neighborhoods |
| Neighborhood voices, local rules, Jersey City split, MTA tolls | Done |
| Trulia | Blocked; no requests. About 100 NYC shown units cannot be re-checked |
| Photos; Reddit key; Zumper opened-listings merge | Open |

**Robots lapses to remember (told to Will):** the voices agent restarted after a Niche 403; evidence batch 13 sent six more Trulia requests after the first
refusals. Agent briefs must say: one refusal ends that host for the session.

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

## History: superseded answers and earlier states

Kept for the record; none of this is current. The decision log in `CLAUDE.md` says what replaced what.

### Answers from Will on 2026-11-15, as first recorded (several since replaced)

Superseded: the tiers (`comfortable` / `at_cap` / `stretch`) are gone (cap and ceiling are both $3,000); "move-in by December 1" became "now through
December 15, 2026". Still true: browser automation allowed within robots rules; Philadelphia is a benchmark only; the api.data.gov key is an environment secret.

| Question | Answer | Effect |
|---|---|---|
| Stretch ceiling | **$3,000 listed rent** (the brief had $3,200) | Tiers: `comfortable` ≤ 2,400; `at_cap` 2,401–2,800; `stretch` 2,801–3,000. Collect nothing above $3,000. |
| Move-in | **December 1, 2026** (Will, 2026-11-15, second answer; it replaced "December only", which replaced the brief's "Dec preferred, Jan latest") | Inventory must be available on or before Dec 1. `move_in_fit` = `ready_by_dec1` / `after_dec1` / `unknown`. |
| Browser automation | **Allowed** (Playwright, headless) within robots rules, throttled, no getting around logins or CAPTCHAs | |
| Philadelphia | **Benchmark only** | R8 gets area metrics only; no inventory or quotes unless Will says otherwise. |
| API keys | Will didn't know how to get them and said to get them if I could. I can't sign up on his behalf, so he signed up for an **api.data.gov key**, which is saved as an environment network secret for `api.usa.gov` (FBI Crime Data Explorer; header injected by the proxy, never in code or env vars). Will then pasted a **Census API key** in chat. It's stored outside the repo at `/root/.config/house-hunt/census_api_key` (re-create it in a new container; ask Will), read via `lib.census_key()`, and `lib.redact()` strips it from every logged URL. | Routing with traffic, Reddit, YouTube and Walk Score: **no keys**. Drive times are OSRM free-flow, labelled `estimate`. Reddit's JSON API returns 403 without auth; see SOURCES.md. |
| Visit frequency | Not asked; still **assumed weekly** | Only matters for travel-cost rollups. |


### State before the consistency pass (2026-11-16, after the third independent check and the elevator gate fix)

**Authorities, newest first:** `docs/PLAN_V4_MASTER_MODEL_2026-11-15.md` → `docs/RANKING.md` (v2, with the sections added after each check; the last one is current) → `docs/SAFETY_BASIS.md`
→ `docs/PLAN_V3_APPROVED_2026-11-15.md` (gates; dog limit 25 lb; size-only "small dogs" passes) → UX brief and mock-up 4 (layout only).
The "data only, no UI, no ranking" lines in `CLAUDE.md` and the handoff brief are superseded: the job is now the finished decision page.

**Run everything:** `python3 scripts/run_all.py` (`--fast` after evidence-only changes) → `scripts/build_page_data.py` →
`scripts/page_data_extras.py` (prose, round 2 quotes and rules, contacts) → `scripts/build_site.py` → `site/dist/index.html`. Publish as a NEW private artifact (never replace the mock).

**Elevator gate fix (2026-11-16, later; supersedes the counts in the next paragraph):** `gates.gate_elevator` no longer reads a unit label as a
building height ("42M" is not floor 42; "69B" at 69 N Broadway is not floor 69). The gate passes only on an elevator stated on a page, the city's elevator
class on the listing's own lot, an evidence row or amenities page that states one (`gates.elevator_evidence`), or a height of 6+ floors from a page or record
(`docs/RANKING.md`, last section). Run now: 20,464 listings → **2,503 pass listing gates** (was 2,659: 200 label-only passes are now pending, 44 pending
listings pass on an evidence row, an amenities page or the city's floor count) → 2,462 costed → 1,488 within the cap → 769 ranked → **491 shown in 233 buildings**,
104 neighborhoods (42 with three or more). No shown unit left. Two entered (Skyline Tower, 60 Paterson St, New Brunswick: two floor-plan rows with the
availability asterisk); two more that would have entered have a `remove` verdict (The Agnes Co-Living 448-3 is a private room with a shared bath;
`avalon:AVB-NJ030-001-215` is the same apartment as the Apartment List row already shown). East Rutherford and Patchogue moved from Little-City to
Room-to-Breathe (the lifestyle indices are standardised over the neighborhoods that have a passing unit, and that set changed). By experience
(units / buildings): Little-City 198 / 85, Room-to-Breathe 128 / 48, Old-Neighborhood 85 / 63, Fresh-Start 65 / 25, Quiet-Street 10 / 7, Walk-Everywhere 5 / 5.
Verdicts: 796 rows for 795 units. Two consecutive runs give an identical ranked file; `check_registry.py` and all tests pass.

**Zumper opened pages (not merged, on purpose):** 900 Zumper pages were opened; on stated facts zero units pass every gate (the 15 the old gate passed
all rested on a unit label read as a floor). 168 units are one fact short, 164 of them on the elevator, which Zumper pages almost never state. Files:
`data/listings_pending/zumper_opened.csv`, `zumper_opened_summary.csv`, `zumper_opened_pass_or_one_open.csv`; notes in `docs/harvest_notes/zumper_open_pending.md`.

**Latest run (2026-11-16, repairs after `docs/INDEPENDENT_CHECK_3.md`; details in `docs/REPAIRS_AFTER_INDEPENDENT_CHECK_3.md`):** 20,464 listings →
2,659 pass listing gates → 2,632 costed (27 duplicates merged) → 1,613 within the all-in cap (pet rent now estimated where unpublished) → 763 ranked → **489 shown in 232 buildings**,
104 neighborhoods (42 with three or more). Up to 8 per building (139 buildings show one unit, 11 show eight). 293 carry one open item: live check 178, elevator 41, listing 37,
dogs 16, availability 16, eligibility 5. Disclosures: floor not published 440, special offer 253, lease term 98, could pass $3,000 once parking and fees are known 97,
dog weight limit not published 22, overnight street parking 19, net-effective rent 18, condo 9. 34 avoid cards, 35 held, 35 waiting for a live check.
By experience (units / buildings): Little-City 202 / 87, Room-to-Breathe 124 / 46, Old-Neighborhood 85 / 63, Fresh-Start 63 / 24, Quiet-Street 10 / 7, Walk-Everywhere 5 / 5.
By state: NJ 244 units in 90 buildings, CT 135 in 57, NY 110 in 85. Reviewed verdicts: 792 rows for 791 units (ok 445, asterisk 155, disclose 20, remove 172).
Two consecutive runs give an identical `data/ranked_units.csv`; `check_registry.py` and all tests pass.

**Changed in this pass:** verdicts carry several kinds per unit; net-effective only where the evidence says so (other offers are the "special offer" disclosure, no invented gross);
staleness no longer switched off by a "second site" that is the same page, and a building page's date applies to every unit on it; the elevator doubt table
(`data/reference/elevator_doubt.csv`, 15 buildings) and the garden-style rule; pet rent estimated, `all_in_likely` and its disclosure; 8 per building with a `buildings` array;
experience and neighborhood figures computed over the shown units; day-moment ratings on absolute thresholds; fees not counted twice; names and addresses corrected
(`data/reference/address_overrides.csv`); 30 Broad Street removed; contacts re-graded.

**Weak, plainly:** 178 of the 489 shown units have never been seen live (most are the third to eighth unit of a building whose first two were checked); 217 are Trulia rows
that cannot be re-read. 377 shown units in 164 buildings have their elevator from listing sites only. 440 shown floors are not published. Parking is not published for 359
shown units and required fees for 306; 97 units would pass $3,000 at typical parking and fees, and 201 use an estimated pet rent. The garden-style rule catches only two
buildings beyond the reviewed table, because unit labels are ambiguous. 13 shown rows are floor plans, not named apartments. The estimates' medians come from the master table,
not the ranked set. `docs/harvest_notes/zumper_open_pending.md` did not exist when this pass ended, so the Zumper opened-listings file is still not merged.

**Open:** the Zumper opened-listings harvest (`data/listings_pending/zumper_opened.csv`) was not finished when this pass ended and is not
merged; Avalon W Squared (West Windsor, 65 pending units) must not be filed under Princeton if it ever passes; the Manhattan congestion-zone
mail rate; photos; Reddit key.

**The review rule (new):** a unit is shown only if `data/evidence/review_verdicts.csv` holds an `ok`, `asterisk` or `disclose` verdict (several rows per unit, one per kind) for
it, written against the evidence as it stands (`scripts/verdicts.py`; `check_registry.py` fails the run otherwise). When
evidence is added or a new unit is promoted: `python3 scripts/verdicts.py digest`, read it, `python3 scripts/verdicts.py add
<file>`, rerun. See `docs/REPAIRS_AFTER_INDEPENDENT_CHECK_2.md` (per-defect status, what is still weak, six decisions for Will).

| Piece | Status |
|---|---|
| Master tables, rent terms, all-in cost, ranking v2, avoid rules, registry check | Done |
| Evidence rounds 1–3 (batches 1–17), NYC records, non-NYC records, rating standard | Done |
| Checker findings reach the list (`scripts/avoid.py`): age/income-restricted, waitlist, rented, dead listing, pet-free, "probably no elevator" readings, confirmed or probable ground-floor units | Added after round 3 showed they were being missed |
| Elevator "inferred from height" needs a real building height (page or record, 6+ floors); a height guessed from a unit label ("36D") no longer counts (`scripts/rank.py`) | Done |
| First independent check + repairs (`docs/INDEPENDENT_CHECK.md`, `docs/REPAIRS_AFTER_INDEPENDENT_CHECK.md`) | Done |
| Second independent check (`docs/INDEPENDENT_CHECK_2.md`) and repairs (`docs/REPAIRS_AFTER_INDEPENDENT_CHECK_2.md`) | Done: 21 defects, 19 fixed, D13 one case left, D18 by review only; 507 reviewed verdicts |
| Neighborhood voices: 890 verified quotes, 79 neighborhoods, 873 from Niche | Done; 53 later neighborhoods have none |
| Local rules (parking, dogs) for 34 of 56 municipalities | Done |
| Trulia | Blocking us (403/CAPTCHA) since the evening of Nov 15. No Trulia requests until a single test on Nov 16. About 100 NYC shown units cannot be re-checked until then |
| Jersey City split into neighborhoods; MTA toll rates | Done 2026-11-16 |
| Photos; Reddit key (Will); Zumper opened-listings merge | Open |

**Robots lapses to remember (told to Will):** the voices agent restarted after a Niche 403 (21 neighborhoods; quotes kept pending Will's call);
evidence batch 13 sent six more Trulia requests after the first refusals. Agent briefs must say: one refusal ends that host for the session.

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
