# Data dictionary

Rewritten 2026-11-16 to match the files as they are. The earlier version described the phase-1 area model and four
tables that were never built (`area_metrics.csv`, `buildings.csv`, `building_reviews.csv`, `quotes.csv`); it is in git
history. Row counts below are from 2026-11-16 and move with every run.

**Per-field detail is not repeated here.** `data/reference/field_registry.csv` (written by
`scripts/check_registry.py` on every run) lists every column of the master tables, `rent_terms.csv` and the evidence
families with its status (`used`, `provenance`, `display`, `not_used`), the scripts that reference it and a note.
This file says what each file is, what one row is, its key, who writes it and who reads it.

## Conventions

| Convention | Meaning |
|---|---|
| Format | CSV, UTF-8, comma, header row. Times are UTC ISO 8601. Money is USD per month unless the name says otherwise. |
| `source_url`, `retrieved_at` | Where a value came from and when. Required on every collected fact. |
| `not_found`, blank | Looked for and not found, or not known. Never a guess. On the page an unknown is "Not known yet". |
| `<field>_basis` | How a merged fact is known, best first: `confirmed_by_phone`, `confirmed`, `community_page`, `amenities_page`, `official_record`, `stated`, `inferred`, `unknown`. Travels with `<field>_source`. |
| `value_type` | `found`, `estimate` (with a method), `not_found`. Used in reference and phase-1 tables. |
| `listing_id` | One listed unit on one source. Key of every unit table. |
| `addr_key` | Normalised address + ZIP, as written by a source. Key of the evidence files. Several can belong to one building. |
| `building_id` | One physical building (`b_…`). `data/reference/building_crosswalk.csv` maps every `addr_key` to it. |
| `hood_id` | Neighborhood. `group_key` / `group_label`: the experience (internally still "year"). |
| Gate columns | `g_type`, `g_rent`, `g_movein`, `g_dog`, `g_elevator`, `g_floor`, `g_place`, `g_proof`: `pass` / `fail` / `unknown`. |

## Pipeline tables (`data/`)

| File | One row is | Key | Rows | Written by | Read by |
|---|---|---|---|---|---|
| `listings_raw/<source>.csv` | A listed unit as harvested | `listing_id` | 20 files | the `h_*` harvesters | `gates.py` |
| `listings.csv` | Every harvested listing after merge and dedupe, with gate columns, `gate_status` (pass / pending / fail), `fail_reasons`, `pending_reasons`, `also_seen_at`, PLUTO and community facts | `listing_id` | 20,464 | `gates.py` | `enrich_units.py`, harvest follow-ups |
| `gate_summary.md` | Counts dropped at each gate | — | — | `gates.py` | people |
| `units.csv` | A listing that passes the listing gates, with its building's lookup results (drive, tolls, transit, police agency, nearby places, utilities), a first all-in figure and its neighborhood | `listing_id` | 2,659 | `enrich_units.py`, then `build_neighborhoods.py` adds `hood*` | `build_master.py`, `rent_terms.py`, `building_amenities.py` |
| `buildings_enriched.csv` | Lookup results per address | `addr_key` | 693 | `enrich_units.py` | `build_neighborhoods.py` |
| `enriched/<hash>.json` | Full lookup-tool output for one address, with provenance | `addr_key` hash | 793 files | `enrich_units.py` | `build_master.py`, `build_scene_text.py`, `check_scene_text.py` |
| `enriched_color/<hash>.json` | `places.color()` output per address (wider OpenStreetMap counts) | `addr_key` hash | 569 files | `lifestyle_color.py`, `rank.py` | `rank.py` |
| `master_buildings.csv` | One physical building with every merged fact and its basis and source; NYC record counts (`nycrec_*`), nearby crime (`near250_*`), agency rates | `building_id` | 665 | `build_master.py` | `all_in.py`, `rank.py`, `avoid.py` |
| `master_units.csv` | One listed unit with its own facts (floor, live status, staleness, phone answers) and its building's merged facts joined on; the all-in receipt and `cost_gate` are added by `all_in.py` | `listing_id` | 2,632 | `build_master.py`, `all_in.py` | `rank.py`, `avoid.py`, `verdicts.py`, `check_registry.py` |
| `master_conflicts.csv` | A merged field on which two sources disagree, with the value chosen | `building_id` + `field` | 68 | `build_master.py` | people |
| `duplicate_units.csv` | A listing merged into another listing of the same unit | `listing_id` → `kept_listing_id` | 27 | `build_master.py` | people |
| `rent_terms.csv` | Rent terms of one passing unit: `listed_price_is` (gross / net_effective / unknown), `offer_text` verbatim, `offer_type`, `free_months`, `lease_months`, `gross_monthly_rent`, `net_effective_monthly`, `first_full_payment_date`, `computed_how`, `confidence`, `needs_call` | `listing_id` | 2,659 | `rent_terms.py` | `all_in.py` |
| `unit_exclusions.csv` | A unit, or a whole building (`unit` blank), removed by the evidence rules: `reason`, `source` | `addr_key` + `unit` (+ `listing_id`) | 213 | `avoid.py` | `rank.py` |
| `avoid_buildings.csv` | One address the evidence pass covered: `avoid` (yes / no), `reasons`, `pause_notes`, `evidence_json`, `positive_json`, `public_evidence`, counts behind the thresholds | `addr_key` | 794 | `avoid.py` | `rank.py`, `build_page_data.py` |
| `ranked_units.csv` | A unit that survived the cap, the safety rule and every exclusion, with scores (`p_*`, `universal`, `promise`, `rank_score`, `*_in_year`, `*_overall`), the Queens spectrum (`vsq_*`, `vsq_*_diff`), open items (`open_keys`, `confirm_asterisk`, `confirm_what`, `confirm_why`), `disclosures` (JSON), `review_verdict`, evidence columns (`ev_*`), and the selection flags `candidate`, `shown`, `shown_rank`, `avoid_card`, `held_for_confirmation`, `needs_live_check`, `more_in_building` | `listing_id` | 763 | `rank.py` | `build_page_data.py`, `page_data_extras.py`, shortlist tools, `run_all.py` |
| `excluded_by_confirmed_facts.csv` | A unit removed on a confirmed fact (`drop_reason`) | `listing_id` | 114 | `rank.py` | `run_all.py` report |
| `excluded_by_review.csv` | A unit removed by a reviewed `remove` verdict | `listing_id` | 121 | `rank.py` | `run_all.py` report |
| `excluded_by_sibling_rule.csv` | A unit removed by the sibling floor rule | `listing_id` | 1 | `rank.py` | people |
| `excluded_sketchy.csv` | A unit removed for low listing confidence (`sketchy_reason`) | `listing_id` | 206 | `rank.py` | `run_all.py` report |
| `excluded_by_evidence.csv` | A unit removed by `unit_exclusions.csv` | `listing_id` | 47 | `rank.py` | people |
| `needs_confirmation.csv` | The phone list: a ranked unit with one open item, the question (`to_confirm`, `confirm_what`, `confirm_why`) and whether it is shown with an asterisk | `listing_id` | 150 | `rank.py` | `build_page_data.py` (`held`), `call_sheet.py` |
| `needs_live_check.csv` | A candidate with an open gate fact that has not been seen live; not shown | `listing_id` | 35 | `rank.py` | `build_page_data.py` (`awaiting_live_check`) |
| `group_exchange.csv` | Per experience, medians over ranked units and their difference from "near home". The page no longer uses it for its tiles (figures are over shown units) | `group` | 7 | `rank.py` | `build_page_data.py` (loaded) |
| `neighborhoods.csv` | A neighborhood with passing units: counts and medians | `hood_id` | 221 | `build_neighborhoods.py` | lifestyle scripts |
| `lifestyle_features.csv`, `lifestyle_color.csv` | Neighborhood features (ACS, OpenStreetMap), then the wider descriptive set | `hood_id` | 221 | `lifestyle_features.py`, `lifestyle_color.py` | `lifestyle_groups.py`, `rank.py` |
| `neighborhood_safety.csv` | Police agency, rates per 1,000 and ratios to the US, metro and county | `hood_id` | 221 | `crime_benchmarks.py` | `lifestyle_groups.py` |
| `lifestyle_groups.csv` | A neighborhood with its experience (`group`, label, subhead), indices (`ix_*`), safety columns and Jamaica yardsticks | `hood_id` | 221 | `lifestyle_groups.py` | `rank.py`, `build_page_data.py`, scene text |
| `lifestyle_indices.csv`, `lifestyle_loadings.csv` | Interim analysis output (`docs/LIFESTYLE_ANALYSIS.md`). No script names them today | `hood_id` | 102, 26 | an earlier version of the lifestyle scripts | nothing |
| `areas.csv`, `areas_build.log`, `areas_build_problems.txt`, `metrics/*.csv` | Phase 1: 98 fixed areas and their area-level metrics (`acs.csv`, `safety_nyc.csv`, `walkability.csv`). Superseded by per-building lookups; some lookup tools still read `areas.csv` helpers | `id` / `area_id` | 98 | `build_areas.py`, `p1_*.py` | history |
| `listings_pending/*` | The Zumper opened-listings harvest (`zumper_opened.csv` and its logs). **Not merged** | `listing_id` | — | `zumper_open_pending.py` | nothing yet |
| `evidence_pending/*` | Working files of evidence batch 18 (candidates, fetch logs, refused hosts, open questions and their contacts). Its results were copied into `data/evidence/*_batch_18.csv` | — | — | `resolve_pending_thin_years.py`, `thin_call_contacts.py` | people |

`data/house_hunt.sqlite` (from `scripts/build_sqlite.py`) is optional and is not in the repo.

## Evidence (`data/evidence/`)

Batch files are written once by their batch's agent and never edited; the rules change how they are read
(`docs/ARCHITECTURE.md`, "The evidence-batch method"). `<n>` is 1 to 19, `manual`, or `ic2`.

| Family | One row is | Key | Main fields |
|---|---|---|---|
| `live_check_batch_<n>.csv` | One re-read of a listing URL | `addr_key` + `unit` + `listing_url` | `status` (live / gone / changed / blocked), `price_now`, `available_now_text`, `matches_stored`, `building_site_url`, `checked_at`, `notes` |
| `confirm_batch_<n>.csv` | One gate fact checked on a page | `addr_key` + `fact` | `fact` (elevator, floor, dogs_allowed, dog_weight_limit), `value`, `quote`, `source_url`, `status` (confirmed / unconfirmed / contradicts) |
| `facts_batch_<n>.csv` | One useful fact (parking, fees, pet rent, pool, year built, manager, listing dates …) | `addr_key` + `fact` | `value`, `quote`, `source_url`. Fact names are free text; `build_master.py` maps the ones it knows and reports the rest |
| `items_batch_<n>.csv` | One dated piece of tenant or public evidence | `addr_key` + `source_url` + `excerpt` | `category` (car_crime, elevator, management, safety_incident, noise, positive, other, none_found), `item_date`, `excerpt`, `about`, `retrieved_at` |
| `ratings_batch_<n>.csv`, `ratings_round1.csv` | One rating source for one building | `addr_key` + `rating_source` | `rating_value`, `rating_scale`, `review_count`, `as_of_date`, recent and older negative counts, `serious_issue_tags_last_6_months` |
| `rating_standard.csv` | One building judged by the rating screen (`docs/RATING_STANDARD.md`) | `addr_key` | `rating_verdict`, why, sources. Read by `avoid.py` |
| `resolved_pending_batch_18.csv` | A pending listing whose missing gate fact batch 18 settled | `listing_id` | Read by `gates.py` |
| `review_verdicts.csv` | One reviewed verdict | `listing_id` + `kind` | `verdict` (ok / asterisk / disclose / remove), `kind`, `what_to_confirm`, `why`, `evidence_quote`, `evidence_file`, `reviewed_at`, `evidence_hash`. 792 rows. Written only through `scripts/verdicts.py add` |
| `ratings_census.csv` | One building on one review platform | `building_id` + `platform` | `status` (found / not_seen), `rating`, `rating_scale`, `review_count`, `basis` (how it was seen: search-result display, earlier evidence, cached page …), `match_confidence`, `search_query`, `note`. 3,044 rows, 431 found. Information only |
| `ratings_census_part_<1-3>.csv`, `ratings_census_summary.csv` | The three agents' parts; one summary row per building (`platforms`, `max_count`, `searched`) | `building_id` | `page_data_extras.py` reads `ratings_census.csv` only |
| `nyc_records.csv` | A count of one record type for one NYC building in one period | `addr_key` + `record_type` + `period` | `bbl`, `bin`, `count`, `per_100_units`, `query_url` |
| `nyc_records_baseline.csv` | The citywide yardstick per metric, period and size band | metric + period + band | medians and percentiles |
| `nyc_records_flags.csv` | One flag per building (`flag = none` when clean) | `addr_key` + `flag` | the metric, the count and the baseline it exceeded. Read by `avoid.py` |
| `nyc_records_match.csv`, `nyc_records_summary.json` | How each building matched a city lot; run totals | `addr_key` | |
| `non_nyc_records.csv` | NJ inspection reports and Jersey City police incidents per building | `addr_key` + `source` + `metric` + `period` | `value`, `detail`, `match_note`, `query_url` |
| `independent_check_units.csv`, `independent_check_2_units.csv`, `independent_check_3_units.csv` | Field-by-field comparisons made by the three independent checks | check row | `field`, `master_value`, `status`, `page_text_or_note` |
| `call_answers.csv` | Phone answers. **Does not exist yet.** Format in `docs/SHORTLIST_TOOLS.md`; when present it outranks every other source | `building_id` / `listing_ids` | `ans_*`, `called_at` |

## Reference (`data/reference/`)

**Reviewed and hand-decided tables (edit with care; they change what is shown)**

| File | What it is |
|---|---|
| `elevator_doubt.csv` | 15 buildings whose elevator rests on a listing site's amenity list while the complex is low-rise or multi-building: the elevator is an open gate fact. Key `building_id` |
| `address_overrides.csv` | Corrected names, addresses and cities, with basis and source |
| `subcity_overrides.csv` | Four Jersey City buildings assigned by hand across a boundary |
| `overnight_parking_towns.csv` | 26 municipalities with an overnight street-parking rule (ban / permit / seasonal), the summary and URL shown as a disclosure |
| `manual_buildings.csv` | Facts for the manually added building (Envy, Newark) |
| `lifestyle_group_centres.csv`, `lifestyle_index_scale.csv`, `lifestyle_fit_reference.csv` | The saved clustering centres, scale and fit set, so reruns keep the six experiences stable |
| `queens_spectrum_definition.csv` | The five-point bands against the Queens median, per measure (written by `rank.py`) |

**Built by the pipeline**

| File | What it is |
|---|---|
| `building_crosswalk.csv` | Every `addr_key` → `building_id`, `street_key` |
| `field_registry.csv` | Every field, its status and who references it (see the top of this file) |
| `run_history.csv` | One row of stage counts per run of `run_all.py` |
| `cost_estimates.csv` | The medians used for the pet-rent estimate and for `all_in_likely`, with building counts and method |
| `building_amenities.csv` | Amenities per address parsed from cached pages, each with an evidence snippet |
| `nyc_building_facts.csv` | PLUTO lot facts matched to NYC listings (class, floors, units, year, `elevator_from_class`) |
| `building_geocode_changes.csv`, `floor_confirm_unmatched.csv`, `ground_reading_unassigned.csv` | Small audit lists written by `build_master.py` and `avoid.py` |
| `evidence_batches/batch_<n>.csv`, `*_candidate_buildings.csv` | The batch assignment files for the evidence agents |
| `ratings_census_targets.csv` | The 295 buildings given to the ratings census, with their `part` |
| `shown_neighborhoods.csv`, `subcity_counts.csv` | Snapshots used when planning the voices pass and the Jersey City split |

**Written text and contacts for the page**

| File | What it is |
|---|---|
| `scene_text_source.txt` | The hand-written drafts. Edit text here, never in the CSVs |
| `scene_text_years.csv`, `scene_text_neighborhoods.csv` | The built scene text per experience (`year_label`) and per neighborhood (`hood_id`), with `evidence_json` |
| `building_about.csv`, `realtor_lines.csv` | Composed "About the building" (`building_id`) and per-unit line, catch and subheads (`listing_id`), with `facts_used_json` |
| `building_contacts.csv`, `building_contacts_own_site.csv` | Leasing phone, hours, URL and kind of contact per building; the own-site file outranks the first when its confidence is high or medium |
| `neighborhood_descriptions.csv`, `neighborhood_descriptions_round2.csv` | Short attributed outside descriptions per neighborhood (Wikipedia dump, tourism and municipal sites), with licence note and `verified` |
| `neighborhood_summaries.csv`, `neighborhood_summaries_round2.csv` | Plain summaries and landmarks from the same pass (not read by the page builder) |
| `local_rules.csv`, `local_rules_round2.csv` | Street-parking and dog rules per municipality, each with a verbatim quote and URL; `applies_to_hood_ids` |
| `dog_parks.csv` | Named dog parks with rules and source |

**Lookup-tool inputs**

| File | What it is |
|---|---|
| `search_grid.csv` | Every ZIP area within a two-hour free-flow drive of Jamaica |
| `tolls.csv`, `njta_tolls.csv`, `njta_interchanges.csv`, `crz_geofence.json` | Toll rates per crossing (E-ZPass and mail), New Jersey toll-road matrix, the Manhattan congestion-zone outline |
| `crime_agencies.csv`, `crime_place_agency.csv`, `crime_benchmarks.csv`, `crime_nyc_baseline.csv` | Police-agency rates, place → agency mapping, US / metro / county yardsticks, the NYC nearby-incident baseline |
| `utility_rates.csv`, `transit_feeds.csv`, `osm_extract_meta.csv`, `taxes.csv` | Utility prices, GTFS feed status, the OpenStreetMap extract used, the tax reference table |
| `subcity_neighborhoods.geojson`, `subcity_tracts.csv`, `subcity_assignment.csv`, `subcity_crime_jersey_city.csv`, `subcity_crime_note.md` | The Jersey City (and prepared Newark) split: polygons, tract rules, building assignment, the labelled crime estimate |
| `community_facts.csv` | Facts per management-company community read from its own pages; fills listing blanks in `gates.py` |
| `non_nyc_record_sources.csv` | Which record sources outside NYC were tried and why most are unusable |

**Harvest working files**

| File | What it is |
|---|---|
| `region_buildings_<region>.csv`, `leads/<region>.csv` | Every building the five region passes examined, with a verdict; their lead lists |
| `detail_targets_<source>.csv` (16 files) | Output of `build_targets.py`. No script reads them |
| `review_pending_numbers.json` | Git-ignored scratch file |

## Voices (`data/voices/`)

| File | One row is | Key |
|---|---|---|
| `neighborhood_quotes.csv`, `neighborhood_quotes_round2.csv` | One short resident excerpt: `theme`, `sentiment`, `speaker_context`, `source_site`, `post_date`, `permalink`, `source_area`, `verified`. No usernames. 890 + 507 rows | `hood_id` + `permalink` + `excerpt` |
| `neighborhood_survey.csv`, `neighborhood_survey_round2.csv` | One survey measure for an area (for example a share from Trulia's "What Locals Say"), with `as_of` and URL | `hood_id` + `measure` |
| `coverage.csv`, `coverage_round2.csv` | Quotes per theme and the sources that worked, per neighborhood | `hood_id` |
| `quote_exclusions.csv` | Quotes dropped by decision (`hood_id`, `excerpt_starts_with`, `reason`) | `hood_id` + prefix |

Round 1 is read by `build_page_data.py`, round 2 by `page_data_extras.py`. A quote that singles out residents by a
named race, ethnicity, religion or national origin is not shown; quotes about diversity in general are.

## `site/data.json`: the page's data contract

Written by `scripts/build_page_data.py`, completed in place by `scripts/page_data_extras.py`. Those two scripts are the
source of truth; `scripts/build_site.py` inlines a slimmed copy (fields the template does not read are dropped on the
way in; `data.json` itself is never changed). Unknown values are `null`. Fields marked (x) are added by the extras step.

**Top level**: `meta`, `years[]`, `neighborhoods[]`, `buildings[]`, `units[]`, `avoid[]`, `held[]`, `awaiting_live_check[]`.

**`meta`**: `built_at`, `cap_all_in`, `move_in_window`, `anchor` {name, lat, lon}, `jamaica_yardstick`
{violent_per_1000, property_per_1000}, `queens_spectrum[]` (the band definitions), `weights` (the eight ranking
parts), `counts` {shown, shown_with_asterisk, avoid, held, awaiting_live_check, ranked, buildings}, `toll_basis`,
`notes[]`, `moment_thresholds`, `max_units_per_building`, `extras` (x: the extras step's report).

**`years[]`** (the six experiences): `id` (group key), `label` ("The … Year"), `display_label` (x, "… Experience"),
`subhead`, `subhead_original` (x), `tagline` (x), `counts` {neighborhoods, buildings, shown, avoid}, `figures_over`,
`all_in_range`, `drive_min_range`, `drive_min_range_hoods` {nearest, farthest}, `medians` and `ranges` (keys: all_in,
sqft, drive_min, transit_min, toll_round_trip, toll_round_trip_mail, violent_per_1000, property_per_1000,
restaurants_800m, park_walk_min, parking_rank), `vs_queens`, `vs_queens_diff`, `hood_ids` (x: reordered by
`rank_in_experience`), `prose` (x) {scene, promise, catch}, `host` (x) {intro, walkthrough[]}, `about_points` (x),
`day_moments` (x), `headlines` (x) {section: {subhead}}, `catch`, `scenes` (both null; superseded by `prose`).

**`neighborhoods[]`**: `id`, `name`, `area`, `state`, `year`, `lat`, `lon` (x: refined), `counts` {shown, buildings,
avoid, held, ranked}, `figures_over`, `building_ids`, `unit_ids`, `avoid_ids`, `all_in_range`, `sqft_median`,
`drive_min`, `transit_min`, `toll_round_trip`, `toll_round_trip_mail`, `toll_round_trip_mail_at_least`, `toll_basis`,
`toll_complete`, `safety` {violent_per_1000, property_per_1000, vehicle_theft_per_1000, vs_jamaica,
property_vs_jamaica, vs_us, vs_metro, vs_local, police, geography, year, basis, subcity_estimate}, `parent_id`,
`parent_name`, `short_name` (set for the Jersey City neighborhoods), `traits` {…}, `vs_queens`, `local`
{parking_rules[], dog_rules[], voices[], survey[]} (round 2 rows are x), `prose` (x) {scene, good_for_her, watch_for,
about, inherited_from}, `host` (x), `about_points` (x), `headlines` (x), `described[]` (x: outside descriptions
{quote, source, url, about, topic, licence}), `experience_score`, `experience_score_basis`, `rank_in_experience` (x).

**`buildings[]`** (one per building with a shown unit): `id`, `name`, `address`, `addresses[]`, `city`, `state`, `zip`,
`hood_id`, `experience`, `lat`, `lon`, `unit_ids` (rank order), `n_units`, `more_showable_not_shown`, `from_all_in`,
`to_all_in`, `from_all_in_likely`, `best_unit_id`, `best_rank_score`, `best_shown_rank`, `rank_in_neighborhood`,
`elevator`, `dogs`, `parking`, `amenities` (the same objects as on a unit), `links` {building}, `manager`,
`open_items[]`, `units_with_asterisk`.

**`units[]`, `avoid[]`, `held[]`** (the same shape; the (x) fields are added to `units[]` only):
- identity: `id` (listing id), `building_id`, `hood_id`, `year`, `building`, `address`, `unit`, `beds`, `sqft`, `zip`,
  `lat`, `lon`, `source_site`, `links` {listing, building}, `price_seen_at`, `listing_age_days`, `available`
- floor: `floor`, `floor_basis`, `floor_basis_note`
- rent: `rent` {listed, basis, basis_kind, gross, asterisk, offer_text, offer_kind, free_months, lease_months,
  first_full_payment_date, first_full_payment_note, needs_call}
- cost: `all_in`, `all_in_gross`, `all_in_lines[]`, `all_in_unknown[]`, `unknown_cost_lines[]`,
  `estimated_cost_lines[]`, `all_in_likely`, `all_in_likely_note`, `cost_check` {cap_margin, unknown_count,
  lease_term_months, price_12_month}
- gate facts: `elevator` {value, basis, listing_site_only}, `dog` {allowed, basis, weight_limit_lb, size_note,
  size_only_source, policy_text, pet_rent}, `parking` {type, rank, fee, fee_note, options_text, offsite}
- `amenities` {pool, pool_text, doorman, doorman_text, controlled_access, gym, in_unit_laundry, laundry,
  package_room, outdoor_space, lounge_or_coworking, dog_amenities, year_built, building_floors, manager}
- `moments` {wake, work, after, night, sat, sun}: the measures behind "A day here", each with a `rating`
  (strong / mixed / weak, thresholds in `meta.moment_thresholds`); `sun` carries drive, tolls and transit
- `scores` {rank, universal, promise, pool_bump, hood_rank, parts, in_year, overall}, `vs_queens`, `vs_queens_diff`
- `confirm` {asterisk, what, why, question, reviewed}, `disclosures[]` {what, why, question, url, severity},
  `tour_questions[]`, `confidence`, `live` {status, checked_at}
- `evidence` {checked, avoid, avoid_reasons, pause_notes, items[], positive[], public_evidence}
- `more_in_building`, `rank_in_building`
- (x) `contact` {phone, hours, site, kind, note, source}, `about_building`, `about_points`, `ratings` {platforms[]
  {platform, rating, count, seen_via, url, as_of}, most_reviews, searched, found_any}, `host` {line, catch},
  `headlines`, `photos` {url, where, kind}

**`awaiting_live_check[]`**: `id`, `building`, `address`, `unit`, `hood_id`, `year`, `price_seen_at`, `rank`,
`all_in`, `listing`.

Other files in `site/`: `map_base.json` (map geometry, with its sources under `meta`), `illustrations.json` (the six
drawings keyed by experience), `dist/index.html` (the built page), `dist/artifact.html` (the publish copy).

## `out/`

`call_sheet.csv` / `.md`, `call_sheet_thin_experiences.md`, `tour_days.csv` / `.md`, `recheck_<date>.csv`,
`sample_shortlist.txt`: outputs of the shortlist tools (`docs/SHORTLIST_TOOLS.md`). Regenerated on demand.
