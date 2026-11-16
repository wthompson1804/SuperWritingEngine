# PROGRESS

Read this first every session. Newest entries at the top of the log.

## Current state (2026-11-16, after the repairs to independent check 4 and the pipeline clean-up that followed; details in `docs/REPAIRS_AFTER_INDEPENDENT_CHECK_4.md`)

**Authorities, newest first:** `CLAUDE.md` → `docs/RANKING.md` (one current statement; change log at its end) → plan v4 → `docs/SAFETY_BASIS.md` → plan v3.

**Run everything:** `python3 scripts/run_all.py` → `scripts/build_page_data.py` → `scripts/page_data_extras.py` → the text builders (`build_scene_text.py`,
`check_scene_text.py`, `realtor_lines.py`, `test_realtor_lines.py`) → `page_data_extras.py` → `build_site.py`. The page tests in `test_rules.py --data` need
`site/data.json` to be newer than `data/ranked_units.csv`, so run that suite again after `page_data_extras.py`.

**Counts now**: 20,468 listings → 2,505 pass the listing gates → 2,451 costed → 1,469 within the all-in cap → 664 ranked →
**523 apartments shown in 202 buildings, 77 neighborhoods** (50 with three or more). Before these repairs: 542 / 209 / 78.
By experience (apartments / buildings / neighborhoods): Little-City 217 / 80 / 23, Room-to-Breathe 154 / 38 / 23, Old-Neighborhood 72 / 55 / 21,
Fresh-Start 71 / 23 / 5, Quiet-Street 6 / 3 / 3, Walk-Everywhere 3 / 3 / 2. **218 shown apartments carry one open item** (elevator 118, listing 61,
dogs allowed 28, availability 8, eligibility 3); 305 carry none. 76 rows are `not_an_apartment`; 28 single-apartment neighborhoods are cut by the
thin-neighborhood rule and 10 kept. Verdicts: 924 rows for 922 units (ok 533, asterisk 167, disclose 31, remove 193). Two consecutive full runs give an
identical `data/ranked_units.csv` and `data/master_units.csv`; `check_registry.py` and all tests pass (`test_rules.py`: 617 pure checks; `--data`: 4,170
with the page data; `test_parsers.py`: 259). `verify_all.py`: 19 passed, 0 failed, 1 warning (`site/dist` is older than `site/data.json`: `build_site.py`
is the page agent's step).

**Pipeline clean-up after the text audit (2026-11-16, later; counts unchanged at 523 / 202 / 77):**
- `python3 scripts/check_published_text.py` (no flag) now exits 0: text 0, pipeline strings 0 (was 17). `verify_all.py`: 21 passed, 0 failed.
  Tests: `test_rules.py` 793 pure checks (`pure_cleanup`), `--data` 5,385 with the page data (`page_cleanup`), `test_parsers.py` 259.
- **Spelling.** American spelling in our own rule summaries: `data/reference/local_rules.csv` (39 summaries), `local_rules_round2.csv` (38),
  `overnight_parking_towns.csv` (2: the Jersey City "license" sentence printed in 10 disclosures, and Peekskill), and the same summaries in
  `scripts/local_rules_rows.jsonl` / `local_rules_round2_rows.jsonl` so a rebuild does not bring them back. No `quote` was touched.
- **`meta.notes` and `meta.moment_thresholds`** are plain reader sentences (`build_page_data.META_NOTES`): no field names, "total with utilities
  and fees", no "where the car sleeps", no "not read again".
- **Dog amenities are structured** (`parsers.dog_amenity_facts`, from every source's words; `build_master.structured_dog_and_laundry`):
  `amenities.dog_park_or_run`, `pet_spa_or_wash`, `dog_amenity_unspecified`. The bare "yes" on 11 shown buildings came from the management
  page's value outranking the listing site's tag; read with its own sentence, all 11 name what they have (Avalon Maplewood, Avalon Wayne, Liberty
  Bay Club, The Walcott, West Side Square: dog park and pet spa; Continuum: dog park, pet spa, dog wash; The Leaf: dog run, dog park, pet spa;
  Vermella Harrison: dog run and dog park; The Brownstones at Englewood South, Summer Street: dog park; 500 PARQ: pet spa only). No shown
  building is left unspecified. `shown_figures.buildings_with_own_dog_area` counts only a dog park or run (12 neighborhoods changed).
  `dog_amenities` stays as the label (`dog run; dog park; pet spa; dog wash`, or `yes`), so the text system reads it as before.
- **Laundry is structured** (`parsers.laundry_facts`): `in_unit_laundry` is `yes` only where a source says in the apartment and none says it is
  not; `washer_dryer_hookups`, `on_site_laundry`; `laundry` is a label written from the same facts. Changed flags: Beacon Mill Village (only
  "select apartments" have a washer: `select_apartments`; five apartments lose 1.5 to 1.6 rank points and keep their order) and 153-10 88th Ave
  (a checker read "LAUNDRY ROOM (not in unit)": `on_site_only`; the ranking already scored it so). Bay One and West Side Square keep `yes` (their
  own pages say in-unit); only the words beside the flag were another source's. The amenities parser no longer reads "Dishwasher In Every Unit"
  as a washer. **Shown list:** 3 Acres 6052 entered and 3 Acres 5066 left (the eighth place in the building; scores moved by 0.1 through the
  percentile shift; 6052 has a current `ok` verdict and was on the manager's own page at $2,245).
- **`shown_figures` are the median building's** (one vote per shown building), the same computation as the text and "At a glance"; 28
  neighborhoods changed a figure (Newark restaurants within a 10-minute walk: 35 → 14).
- Left for others: `at_a_glance[].unit` is the word "metres" (text system's `glance_json`); the internal `why_internal` notes still say
  "neighbouring lot" (never shown).

**What changed (independent check 4, pipeline side):**
- **Where buildings stand.** Every building's point is compared with its own address (ZIP area and municipality from the Census at the point). 14 points
  were outside their address's ZIP area: 9 are ZIP boundaries (kept), 4 were re-geocoded from the address (Harbor Pointe, Bayonne: 6.9 km off, in
  Elizabeth's port; Parkway Lofts, Bloomfield: 168 m, across the East Orange line; The Grand, West New York: 248 m; Reserve at Lakeside, Newburgh: 1.8 km),
  1 is flagged (Parc at Roxbury: the address could not be geocoded; not shown). The "Elizabeth" neighborhood is gone; Harbor Pointe is in Bayonne and
  Parkway Lofts in Bloomfield, each with its own drive, surroundings, local rules and police figures. `city` is now the municipality at the point
  (34 buildings changed, 10 of them shown: `data/reference/municipality_changes.csv`); the listed city is kept as `city_listed` / `postal_city`.
- **Left the page (26):** Residences at The Summit, all 8 (stale page plus an elevator named only for a complex of buildings K, L, M); The District at
  15Fifteen, all 8 (the same elevator rule plus an open eligibility question); 328 Pacific 705, Metropolis Towers 16F and 509 Martin Luther King Jr Dr 39E
  (dogs open plus "a second site lists the address and not this apartment"); BE `P`, `F` and Appletree Suites `C`, `E`, `F` (plan letters, not
  apartments); 630 West 163rd Street 10 (a sequential apartment number that reads as the first floor); Portside Towers 311 (Downtown Jersey City became a
  single-apartment neighborhood and the thin rule cut it).
- **Entered (7):** The Grove Somerset 2141, 2205, 3172, 4149, 4171 (four had been removed as "first floor" on a wrong reading of the number; with them
  Franklin is no longer a single-apartment neighborhood, so 2205 returns too; all carry the elevator asterisk); Appletree Suites 3A, 5A (moved up when the
  plan letters left; verdicts written from the evidence: ok).
- **New asterisks on apartments that stay (28):** elevator at Pier Village (8), The Brunswick (5), 1 Kennedy Flats (4), Admirals Cove (4), Halstead
  Parsippany (2), The Confluence (1), Fort Hill Peekskill (1), Valley and Bloom (1); availability at 525 Riverdale Ave 5U and 100 Prospect N311.
- **New disclosures:** lease term on every price quoted for a lease that is not 12 months (129, was 101); income requirement (9), credit-score
  requirement (3), furnished apartment (11).
- **Page data (`site/data.json`):** reader text from templates (`confirm.label / why / question`, disclosure `label / why / question`, cost-line `note`,
  tour questions; raw notes only in `*_internal`); `neighborhoods` holds the 77 with an apartment to show and `neighborhoods_avoid_only` the 11 with only
  an avoid card; `safety.status`; `amenities.doorman / concierge / front_desk` apart; `rent.offer_up_to` and `rent.free_text`; `parking.kinds`,
  `parking.fee_basis`; `amenities.building_floors_at_least`; building `city` / `postal_city`; `shown_figures` per neighborhood.
- **No crime figure published:** Beacon Falls, CT (5 apartments shown). No police agency reports a figure for the town alone (the Connecticut State Police
  report one statewide total). It is kept, with `safety.status = "not_published"`; the owner's safety rule could not be tested there. **For the owner.**
- **Experiences:** no neighborhood moved. Every shown neighborhood already sits in the group its frozen area profile is nearest to; none is nearer
  another group. The misfits the check names (Fairfield, Englewood, Kew Gardens Hills) come from the area profile describing a wider sample than the one
  building shown: a text matter (`shown_figures` is there for it), or a refit, which is the owner's call.

**For the owner:** `CLAUDE.md` still words the thin rule as "well attested (seen live, nothing open)" one paragraph above the rule that dropped "seen
live" (not edited here); Beacon Falls above; Metropolis Towers 16F is off the page now, and whether the building is a co-op is still unread.

## Previous state (2026-11-16, after evidence batch 20: the live re-read of 190 shown apartments; superseded by the section above)

**Authorities, newest first:** `CLAUDE.md` (rules and decision log) → `docs/RANKING.md` (rewritten as ONE current statement of the gates, the elevator rule,
duplicates, score and selection, with a change log) → `docs/PLAN_V4_MASTER_MODEL_2026-11-15.md` → `docs/SAFETY_BASIS.md` → `docs/PLAN_V3_APPROVED_2026-11-15.md` → UX brief and mock-up 4 (layout only).
The job is the finished decision page.

**Run everything:** `python3 scripts/run_all.py` (`--fast` after evidence-only changes; tests first, `check_registry.py` last) → `scripts/build_page_data.py` →
`scripts/page_data_extras.py` → `scripts/build_scene_text.py` → `scripts/check_scene_text.py` → `scripts/realtor_lines.py` → `scripts/test_realtor_lines.py` →
`scripts/page_data_extras.py` → `scripts/build_site.py` → `site/dist/index.html`. **The text check (`check_scene_text.py`) is a separate step after
`page_data_extras.py`; `run_all.py` does not run it.** Publish as a NEW private artifact (never replace the mock).

**Counts now**: 20,468 listings → 2,505 pass the listing gates → 2,451 costed → 1,469 within the all-in cap → 692 ranked →
**542 apartments shown in 209 buildings, 78 neighborhoods** (52 with three or more). Before batch 20 it was 568 / 212 / 78.
By experience (apartments / buildings / neighborhoods): Little-City 232 / 81 / 23, Room-to-Breathe 153 / 39 / 23, Old-Neighborhood 73 / 56 / 21,
Fresh-Start 75 / 27 / 6, Quiet-Street 6 / 3 / 3, Walk-Everywhere 3 / 3 / 2. **207 shown apartments carry one open item, every one a gate fact**
(elevator 87, listing 72, dogs allowed 31, eligibility 11, availability 6); 335 carry none. 71 rows are `not_an_apartment`; 28 single-apartment
neighborhoods are cut by the thin-neighborhood rule and 10 kept. Verdicts: 922 rows for 920 units (ok 526, asterisk 167, disclose 31, remove 198).
Two consecutive full runs give an identical `data/ranked_units.csv` and `data/master_units.csv`; `check_registry.py` and all tests pass (`test_rules.py`:
449 pure checks; `--data` on the output: 3,831 with the page data; `test_parsers.py`: 259). `verify_all.py`: 18 passed, 0 failed, 1 warning (`site/dist` is
older than `site/data.json`: `build_site.py` was not run in this pass, on purpose), 1 skipped (browser walk-through).

**Evidence batch 20 (2026-11-16; `docs/harvest_notes/evidence_batch_20.md`)**: 190 shown apartments re-read on Apartment List and the buildings' own
pages: 173 live, 8 small price decreases, 9 gone, and eleven own-site apartments whose listed price is a long-lease price with a far higher 12-month price.
What the pipeline now does with it:
- **32 apartments left the page, 6 entered** (net 568 → 542; no neighborhood entered or left; the buildings The Mercer, Motif and Harbor Landing left).
  - Gone (11): The Mercer 6E, 8F, 8H, 9E, 10E, 11E, 12F, 12E (the building's listing page is gone, so every unit on it is: all 19 Mercer rows of the
    master are `gone`, none is ranked, shown, held or on an avoid card); LIA by Vermella 307; Kensington Place 1315; Harbor Pointe B9-457.
  - Over $3,000 on the 12-month price (11): The Leaf 2318, 2418, 2505, 2518 (total about $4,336 to $4,367); The Asher 308, 610, 730, 830 ($3,461 to
    $3,572); Scribe 425 ($3,539); Motif 523 ($3,378); Harbor Landing 452 ($3,454; quoted on 13 months, $3,040 on 12).
  - Sibling long-lease rule plus an elevator already open, so two open facts (5): Motif 205, 632; Harbor Landing 208, 341, 404.
  - An availability date more than six months old read at the re-read, plus a fact already open (3): Piper 3059 (2026-02-10; dogs), J Centra Burlington
    9307 (2026-03-19; elevator), Kensington Place 1331 (2026-05-01; elevator).
  - Ninth in their building after the order changed (2): Clifton & Co. CCO-475 (now carries "listing"), Aviva E0918.
  - Entered as siblings moved up: Piper 6008, Scribe 540, Clifton & Co. CCO-571, Kensington Place 2319 and 2339, Aviva E0721 (verdicts written from
    their evidence: all `ok`; the rules already mark what is open).
- **The 12-month price rule is wider** (owner's intent, `docs/RANKING.md` section 1): used wherever the page gives one and it differs from the listed price,
  whatever the quoted term. Scribe 502, 507, 542, 544, 546 now show rent $2,395 (was $2,379) and total $2,711 (was $2,695), and say so in the lease-term
  disclosure. Eight small decreases applied: Avalon Maplewood 002-215, 002-347, 001-337, 001-243; The Walcott Hackensack 353, 417, 333, 631A.
- **Sibling long-lease rule** (new, `docs/RANKING.md` section 3): shown with the asterisk "listing" and "the 12-month price in this building is much higher
  than the price shown: ask for it": Scribe 446, 508, 540; The Asher 530, 536; The Leaf 1304. Ranked but not shown: Scribe 307.
- **Grandville Towers** 5F, 7C, 9C (and 7F, not ranked) are treated alike: page date 2026-07-30 from the reviewed table
  `data/evidence/page_date_corrections.csv`, 109 days, one open "listing" item each, all three still shown with the asterisk.
- **Reviewer's additions from reading batch 20** (251 verdict rows written against the new evidence for the 250 shown units of the 51 buildings whose
  evidence changed, three of them newly shown): `disclose | lease_term` for ten apartments priced on a lease under 12 months with no 12-month price (1177 Greens Farms 235, 220; Rail
  at Bound Brook 422, 605 on 6 months; Pier Village 1-412; Reserve at Riverdale 3-329; Shearwood Station 1603, 1803, 2202, 0302); `asterisk | unverified`
  for six availability dates over six months old (the three above that left, and Clifton & Co. CCO-577, CCO-475, Shearwood Station 0302), as earlier
  reviewers did for 110 Washington A413 and RiversEdge RSE-347.
- **Two bugs found and fixed on the way**: a 12-month price was being copied to other units of a building (Scribe 616 took unit 425's $3,210 because
  "$2,616" in the fact read as unit 616; Avalon Somerville 022-415 took 022-265's $2,430); both units were over the cap anyway.
- **Text**: `build_scene_text.py` and `check_scene_text.py` pass (0 problems, 0 failing). Two sentences are newly left out because the shown list no longer
  supports them: Old-Neighborhood "most of these buildings do not list a garage" (52 percent now do) and one "the apartment is large" line.
- **For the owner**: `CLAUDE.md` still words the money rule as "a lease longer than 13 months" (not edited here); 104 shown apartments are quoted on a
  13-to-24-month lease with no 12-month price read (Apartment List gives one term per unit): the 85 over 13 months carry the lease-term disclosure
  (6 of them the sibling asterisk); the 19 on exactly 13 months carry nothing, although Harbor Landing shows a 13-month price can sit 22 percent
  under the 12-month one; the page labels the rent used "as listed" even where it is the 12-month price (`site/index.html`).

**Owner's rule, 2026-11-16 ("Forget call check"): no "not re-checked" flag.** A listing that was simply never re-read in an evidence pass (live status
blank, not checked, blocked: for example the Trulia rows that cannot be re-read) is not an open item: no asterisk, and it counts in no rule (not in "two or
more open", not in the thin-neighborhood rule, not as the second open item beside an elevator doubt, not in the order among equal scores). What a re-read
FOUND still counts through the facts that already existed (gone → removed; price changed → updated; a stale page, a page for another building, a "verify the
price" note → "listing" / "availability"). Reviewed verdicts are still required. Effect: 124 apartments entered (114 had "no live check" as their second open
item beside one gate fact: elevator 57, listing 30, dogs 16, eligibility 6, availability 5; 9 sit in neighborhoods that are no longer single-apartment; 1 moved
up inside its building), 2 left (The Lofts at Garwood: its experience's median rose; Aviva E0721: now ninth in its building). 108 verdicts were written by
reading the evidence (79 ok, 4 asterisk, 25 remove: all 25 are unit numbers that read as first-floor units). `data/needs_live_check.csv` is no longer written;
`site/data.json` keeps `awaiting_live_check` as an empty array and `meta.counts.awaiting_live_check` = 0; each unit keeps `price_seen_at` and `live`
(status, checked_at) as information. At that time 292 shown apartments had never been re-read (266 blank, 26 blocked); after batch 20 it is 108.

**Open after this run:** `site/dist` is older than `site/data.json` (rebuild with `build_site.py`, then publish with the owner's go-ahead).

**What the consistency pass changed (2026-11-16):** one elevator rule for every stage (`parsers.elevator_rule`; a near-miss tax lot neither passes nor fails);
experiences assigned from frozen area profiles and saved parameters (East Rutherford and Patchogue are back in Little-City; four other neighborhoods are held
where they were by `data/reference/lifestyle_group_overrides.csv`, for the owner to decide); units moved out of addresses; duplicates across label spellings
(`215` = `001-215`); the Continuum is one building, not three; only real apartments (owner's rule); the thin-neighborhood rule (owner's rule); a conflicting dog
policy is one open fact, not "sketchy"; in-unit laundry no longer counts a shared laundry room; building names cleaned of listing titles; park names that are not
parks blanked; a third party's API key stripped from `photo_url` everywhere.

**Weak, plainly:** 108 of 542 shown apartments were never re-read after the first reading (82 blank, 26 blocked; by the owner's rule that is no longer flagged); 207 have a gate
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
| Evidence batch 20 applied (live re-read of 190 shown apartments) | Done: 542 shown in 209 buildings, 78 neighborhoods |
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
