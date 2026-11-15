# Shortlist tools: call sheet, tour days, re-check

Three command-line tools that turn the shown list (`data/ranked_units.csv`, `shown == True`) into something Lamia
can phone, drive and re-check. They only read the pipeline's data and write under `out/` (the re-check also caches
pages under `raw/recheck/<date>/`). They use a column only when it exists, so they can be re-run at any time on
whatever the current files are. None of them is a pipeline stage and `run_all.py` does not call them.

Tests: `python3 scripts/test_shortlist_tools.py` (synthetic rows, no network, no data files).

## 1. `scripts/call_sheet.py`: what to ask on the phone

```
python3 scripts/call_sheet.py [--per-year 5] [--years "Quiet,Fresh"] [--hoods "Stamford,Harrison"] [--include-held]
```

Writes `out/call_sheet.csv` and `out/call_sheet.md`, one row per **building**. The buildings are the top N of each
year, ordered by the best `rank_score` among the building's shown units (ties: `shown_rank`, then `listing_id`).
A building's candidates are all of its shown units in that year. `--include-held` also considers units with
`held_for_confirmation == True` (their question comes from `to_confirm`, or from `data/needs_confirmation.csv` when
the ranked row has none). `--years` and `--hoods` are comma lists matched as substrings, case-insensitive.

### When a question is asked

A fact is **settled** when it has a value and its `*_basis` is not one of `inferred`, `unknown`, `estimate`,
`assumed`, `conflicting`, `guess`, `not_found` or blank. Settled facts are not asked; they are listed under
"Already known" so the caller can check them in passing. A building fact is asked once if it is open on any of the
building's units.

| Key | Asked when | Fields read |
|---|---|---|
| `available` | always (it goes stale in days); the text quotes the date the listing gave and when it was seen | `available_date`, `live_checked_at` |
| `floor` | floor missing, or basis inferred/unknown, or "floor" appears in `confirm_what`, `to_confirm` or `tour_confirm` | `unit_floor`, `unit_floor_basis` (or `floor_used`, `floor_basis`) |
| `elevator` | not `yes`, or basis open, or named in the confirm fields, or `elevator_evidence_open` | `elevator`, `elevator_basis` |
| `dogs_allowed` | not `yes` (for example `conflicting`), basis open, or named in the confirm fields | `dogs_allowed`, `dogs_allowed_basis` |
| `dog_weight` | no pound figure, basis open, or `tour_confirm` asks for it | `dog_weight_limit_lb`, `dog_weight_limit_lb_basis` |
| `dog_breeds` | unless a policy text says "no breed restrictions" (no field records a breed list) | `dog_policy_text`, `dogs_allowed_note` |
| `pet_rent` / `pet_fee` | pet rent missing or in `all_in_unknown_lines`; one-time fee text missing | `pet_rent` or `pet_rent_monthly`, `pet_one_time_fee_text` |
| `parking` | fee missing or in `all_in_unknown_lines`; type missing; waitlist unless the parking text mentions one | `parking_fee` or `parking_fee_monthly`, `parking_type`, `parking_text` |
| `required_fees` | "building fees" in `all_in_unknown_lines`, fee text missing, or it says the amount is not shown | `required_fees_text` |
| `utilities` | missing or basis open | `utilities_included`, `utilities_included_basis` |
| `rent_gross_or_net` | `rent_listed_price_is` is unknown or blank, or `rent_needs_call == yes` | plus `rent_offer_text` quoted in the question |
| `lease_term` | lease months missing; or not 12 and no `price_12_month` | `rent_lease_months` or `price_lease_months`, `price_12_month` |
| `first_payment` | date missing, the note says "not stated", or there is a free period or net-effective price | `rent_first_full_payment_date`, `rent_first_full_payment_note`, `rent_free_months` |
| `income` / `guarantor` | income multiple asked when `income_requirement` is blank; guarantor always (no field) | `income_requirement` |
| `turnaround` | always (no field) | none |

### Contact column

`contact` and `contact_basis` are written only when at least one building has something already in the data:
a phone number that appears in the unit's `notes`, `live_notes` or `ev_pause_notes`, or a `building_url` / `url`
whose host is not an aggregator or a record source (so a Trulia or Apartment List link is never called a contact).
Nothing is fetched or guessed. There is no phone or leasing-office column anywhere in `master_buildings.csv`,
`master_units.csv` or `listings.csv`, so for most buildings the only lead is the listing link.

### Answer columns and `data/evidence/call_answers.csv`

The CSV ends with blank answer columns. Fill in a copy and save it as **`data/evidence/call_answers.csv`**
(keep `building_id`, `listing_ids` and `units` as written; other columns may stay or go). The merge into the
pipeline is not wired yet.

| Column | Format | Meaning |
|---|---|---|
| `building_id` | as written | key for building-level answers |
| `listing_ids` | `id; id` as written | the units the row is about |
| `units` | `label; label`, same order as `listing_ids` | unit labels |
| `ans_floor` | integer; per unit | floor of the unit (1 = ground floor) |
| `ans_elevator` | `yes` / `no` | an elevator serves the unit's building and floor |
| `ans_dog_weight_lb` | number, or `no limit` | dog weight limit in pounds |
| `ans_pet_rent` | dollars per month (0 if none) | monthly pet rent for one dog |
| `ans_parking_fee` | dollars per month (0 if a spot is included) | monthly parking fee |
| `ans_required_fees` | dollars per month, total of all required fees | list the items in `ans_notes` |
| `ans_lease_term_months` | integer; per unit | the term the listed price applies to |
| `ans_12mo_price` | dollars per month; per unit | monthly price on a 12-month lease |
| `ans_available_date` | `YYYY-MM-DD`, `now`, or `gone`; per unit | move-in date offered |
| `ans_income_multiple` | number, for example `40` (annual) or `3` (monthly); say which in `ans_notes` | income requirement |
| `ans_notes` | free text | breed list, one-time pet fee, garage or lot, waitlist, utilities, gross or net, first full payment date, guarantor, turnaround, who answered |
| `called_at` | ISO 8601 with offset, for example `2026-11-18T15:10:00-05:00` | when the call was made |

Per-unit columns (`ans_floor`, `ans_lease_term_months`, `ans_12mo_price`, `ans_available_date`) take either one
value, which applies to every unit in the row, or `UNIT=value; UNIT=value` (for example `439=4; 477=4`). Blank
means not asked or not answered; never write a guess.

`python3 scripts/call_sheet.py --explode data/evidence/call_answers.csv` turns the filled sheet into one row per
`listing_id` (`out/call_answers_by_listing.csv`: `listing_id, building_id, unit`, then the answer columns, with
building answers repeated on each unit). `call_sheet.answers_by_listing(df)` is the same thing as a function, for
the merge to call. A phone answer should enter the master tables with a basis such as `confirmed` and source
`phone call <called_at>`.

## 2. `scripts/tour_days.py`: which places on which day

```
python3 scripts/tour_days.py --ids out/shortlist.txt [--days 3] [--start "40.75,-73.90"]
python3 scripts/tour_days.py --ids "listing_id_1,listing_id_2"
python3 scripts/tour_days.py --per-year 3 [--years ...] [--hoods ...] [--max-per-day 5]
```

`--ids` takes a file with one `listing_id` per line (lines starting with `#` are ignored), a CSV with a
`listing_id` or the call sheet's `listing_ids` column, or a comma list. Writes `out/tour_days.md` and
`out/tour_days.csv`. One stop per building; each stop lists address, units, all-in cost (an asterisk when cost lines
are unknown), what to confirm and why (`confirm_what`, `confirm_why`, rent terms, unknown cost lines), the tour
questions (`tour_confirm`, `to_confirm`) and the listing link.

- **Days:** k-means on latitude and longitude with deterministic seeding, so the same list always gives the same
  days whatever order it is given in. With `--days K` there are exactly K days. Without it, days start at
  ceil(stops / `--max-per-day`) and any day over `--max-per-day` (default 5) is split again.
- **Order within a day:** nearest-neighbour from the start point. Default start is Jamaica LIRR station
  (40.699608, -73.808530). Days are listed nearest first; assign them to dates by hand.
- **Distances** are straight-line miles. **Drive minutes are estimates, not routed times**: straight-line miles
  × 1.4 at 30 mph between stops (`ROAD_FACTOR`, `AVG_MPH` in the script). `scripts/tools/drive.py` was not used
  because each lookup calls the public OSRM server. With the default start, the first and last leg of a day use
  the pipeline's stored OSRM free-flow minutes (`drive_min_from`, `drive_min_to`), also an estimate (no traffic).
- **Water:** a leg between Long Island (Brooklyn, Queens, Nassau, Suffolk) and the mainland is marked "crosses
  water", because the straight line badly understates it. The test is a rough outline; the Hudson and other
  crossings are not flagged. Clustering is also by straight line, so check any day that mixes both sides.

## 3. `scripts/recheck_shortlist.py`: is it still there

```
python3 scripts/recheck_shortlist.py --ids out/shortlist.txt [--dry-run] [--allow-trulia] [--refresh]
```

Writes `out/recheck_<YYYY-MM-DD>.csv` (UTC date), one row per `listing_id`: `status`, `price_now`, `price_delta`,
`available_now_text`, `http_status`, `checked_at`, `detail`, `raw_path`.

| Status | Meaning |
|---|---|
| `still_listed` | the unit is on the page at the same price |
| `price_changed` | the unit is on the page at a different price |
| `gone` | HTTP 404/410, or the page parsed and the unit is not in its available list |
| `blocked` | 403, 429 or a challenge page; or the host refused earlier in the run and was not asked again |
| `skipped` | a host the tool never requests, or Trulia without `--allow-trulia` |
| `unparsed` | the page came back but no parser here can find the unit (read it by hand) |
| `error` | network error or 5xx |
| `not_in_data` | the id is not in `ranked_units.csv` |

Rules enforced in code:

- At most **40** listings per run. A longer list stops the run before anything is requested.
- **Never** requests Zillow, StreetEasy, Apartments.com or Craigslist. `--allow-trulia` does not open these.
- **Never** requests trulia.com unless `--allow-trulia` is passed.
- **One refusal** (403, 429, CAPTCHA or challenge page) from a host ends requests to that host for the run; its
  remaining listings are reported `blocked` with the reason. The tool does not remember refusals between runs, so
  after a refusal do not run it again against that host in the same session.
- One request per distinct URL (units of one building share a page), through `lib.cached_get` with `retries=1`
  and at least 2.5 seconds between requests to a host. Apartment List's robots-disallowed paths are refused.
- Pages are cached in `raw/recheck/<date>/`; a second run the same day reads the cache. `--refresh` refetches.
- `--dry-run` prints what would be requested and what would be skipped, with no network.

Parsers (existing ones, imported read-only): Apartment List via `h_apartmentlist.parse_listing`, Zumper listing
pages via `h_zumper.parse_state`, Trulia via its `__NEXT_DATA__` block. Zumper building pages and the buildings'
own sites (SightMap embeds and similar) come back `unparsed`, with a note on whether the old price still appears in
the page text. `listed_rent` is compared with the page's base rent, the same field the harvesters stored.
