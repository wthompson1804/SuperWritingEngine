# Opening the card-only Zumper listings (2026-11-16)

Script: `scripts/zumper_open_pending.py` (`select`, `fetch`, `build`, `report`). It edits no existing script or data
file and does not run the pipeline. Everything it writes is new:

| file | what |
|---|---|
| `data/listings_pending/zumper_opened.csv` | 1,197 unit rows read from the listing or building page. Columns = `data/listings_raw/zumper.csv` exactly, then extras at the end: `leasing_phone, listing_updated, listed_on, office_hours, building_year_built, building_units, card_listed_rent, page_kind, selected_card_row, hood_id, hood_basis, listings_csv_id`. `detail_level=detail`, as the harvester sets for opened pages. |
| `data/listings_pending/zumper_opened_summary.csv` | one line per selected card row (2,004) plus one per extra unit found on a page: `status` (opened / gone / not_requested; no row is blocked or unparsed), each gate, and the same gates after the pipeline's fills (`pf_*`). |
| `data/listings_pending/zumper_opened_pass_or_one_open.csv` | the rows that pass or have one fact open, with neighborhood and lifestyle group. |
| `data/listings_pending/zumper_open_selection.csv`, `zumper_open_funnel.json` | the selection, the fetch order, the funnel. |
| `data/listings_pending/zumper_open_requests.jsonl`, `zumper_open_fetch.log` | one line per request (URL, time, status, cache path). |
| `raw/zumper_open_pending/` | page cache from `lib.cached_get` (HTML is git-ignored, 581 MB; `_index.jsonl` is kept). File names use the same hash as `raw/zumper/`, so a page can be copied there if `h_zumper.py build` should see it. |

## Result in one paragraph

900 pages requested, 900 answered HTTP 200, **no refusal** (no 403, 429, CAPTCHA or challenge page), 00:31–01:59 UTC.
Of the 2,004 selected card rows: **833 opened, 159 gone, 1,012 not requested** (the 900 cap). The pages also showed
380 studio/1BR units at or under $3,000 that no selected card row covered. Opening settles price and proof, and it
settles dogs for most rows, but **Zumper pages almost never say whether there is an elevator and two thirds give no
available date**, so few rows pass: 15 by the gate functions as written, and all 15 rest on a floor and an elevator
inferred from the unit label (see "Read this before using the 15").

## Selection funnel

| step | rows |
|---|---|
| `data/listings.csv` | 20,464 |
| `source_site == zumper` | 3,600 |
| unopened (`g_proof == unknown`, `gate_status == pending`) | 2,236 |
| studio or 1BR | 2,236 |
| card rent ≤ $2,800 | 2,130 |
| no gate failing | 2,130 (1,909 buildings) |
| not in a safety-cut neighborhood | 2,004 (126 removed: New Haven 65, Irvington 21, Neptune 18, Newburgh 17, Kearny 3, Flemington 1, Watchung 1) |
| distinct detail URLs | 1,961 (426 building pages, 1,535 listing pages) |
| already cached under `raw/` (any folder) | 49, used from cache |
| to request | 1,912 (NJ 1,285, NY 393, CT 224, PA 10) |
| requested (cap 900) | 900 (NJ 612, NY 176, CT 107, PA 5; 243 building pages, 657 listing pages) |

**Neighborhood for the safety cut: the pipeline's method**, imported read-only (`build_neighborhoods.nta_polys`,
`build_areas.census_geo`): NYC 2020 NTA polygon from the coordinates inside the city (44 rows), Census place from the
coordinates elsewhere (754 rows). To spare the Census geocoder, a building outside NYC was geocoded only if it lies
within 10 km of a passing unit of a safety-cut neighborhood or its city name equals one; the other 1,206 rows are
marked "not geocoded" and cannot be in a cut neighborhood by distance. No row needed the ZIP fallback. For the report,
every building that passes or has one fact open was geocoded the pipeline way, and none is in a cut neighborhood.

**Order.** Per URL: most candidate units first (rows at the address; for a building page also Zumper's floor-plan
count), then fewest gate facts the card leaves open (move-in, dogs, elevator), then building pages before single
listings, then lower rent. States are interleaved so each advances at the same share of its own queue; when the cap
hit, every state was 45–50% done. The "facts the card leaves open" tie-break is my addition to the brief's order.

Every `/listings/` card row has its own page (no card carries a building-page link), so "one fetch per building"
applied only to `/apartment-buildings/` pages.

## How pages were read

- robots.txt re-read 2026-11-16 00:31 UTC (one request, on top of the 900 pages): identical to the 2026-11-15 copy. No group names Claude; group `*` has no
  Crawl-delay; `/listings/<id>p/<slug>` and `/apartment-buildings/<id>/<slug>` are allowed. No query strings sent.
- `lib.cached_get`, user agent as in `lib.py`, one connection, `retries=1` (nothing is retried). The first 155 requests
  were 4 s apart start to start; I then changed the wait to 4 s after the previous response plus 0.5–2.5 s of jitter
  (about 6 s per request) for the remaining 745.
- Kill file: `raw/_host_kill_shared.json` is read before every request, together with the other agent's
  `data/evidence_pending/refused_hosts.json`. Zumper is in neither. A 401/403/429, a bot-wall page, or three 200 pages
  in a row without page data would have written `zumper.com` there and stopped; none occurred.
- Parsers are h_zumper's, imported: `parse_state`, `visible_text`, `facts_from`, `fees_block`, `parse_fee_text`,
  `iso_avail`, `photo`, `ltype`, `load_cards`, `to_path`. `unit_row` is a copy of the closure inside
  `h_zumper.build()`. Differences from the harvester, each marked `DIFF` or commented in the script:
  1. "now" for an available date is judged against the day the page was read, not the build day.
  2. A dog weight limit is also taken from the page data's `pet_policy.max_wt_in_lbs` when the harvester's "NN lb"
     text pattern finds none (the harvester misses these; 53 opened rows have a limit).
  3. A `/listings/` URL that now resolves to a page showing a different unit is not attached to the card row (below).
- Building facts are applied across opened rows at the same street address the way `h_zumper.build()` does it:
  elevator from any page, dogs only from a building page with a visible policy block.

## What "gone" means here (159 rows)

- **151: the card's URL now resolves to Zumper's address page, which shows one listing at that address, and it is a
  different unit** (for example the card for 165 Barclay St #403 now shows #402). The card's own unit, price and date
  are no longer shown, so nothing was written for it. Six of the units shown instead were new to us and are in the CSV.
- 5: the page shows the unit as inactive. 3: a building page no longer lists the card's floor plan.
- By state: NJ 106, NY 40, CT 13.

## Fill rates on the 1,197 opened rows (683 from building pages, 514 from listing pages)

price 1,197; `available_date` 391; unit label 477; sqft 964; stated floor 93; `building_floors` 6; dogs yes 750 /
no 162 / unknown 285 (yes rests on a visible policy block for 744, on the page-data code alone for 4); dog weight
limit 53; pet rent 141; parking type 360; parking fee 85; utilities included 104; concession text 169; fee lines
1,120; leasing phone 1,172; last-updated date 1,197; elevator yes 5 / no 6 / **unknown 1,186**.

Price against the card, for the 817 selected rows written: 51 are higher on the page, none lower; 5 are now over
$2,800. Another 15 selected rows show a page price over $3,000 and 1 shows 2+ bedrooms; these are in the summary as
opened with that gate failing and are not in the CSV (the harvester drops them too).

## Gate preview

Gate functions are **imported from `scripts/gates.py`** and applied per row (`gate_type`, `gate_rent`, `gate_movein`,
`gate_dog`, `gate_elevator`, `gate_floor`; place = the ZIP's drive time ≤ 120 min as in `gates.main`). The fills that
`gates.main()` applies before gating (community facts by address+ZIP then name, NYC PLUTO building class) sit inside
`main()` and cannot be imported; they are **re-implemented** for the `pf_*` columns. "Pass" = no gate fails and
rent, move-in, dogs, elevator and place are all known; floor may be unknown (floor rule of 2026-11-16).

1,213 opened rows (833 selected card rows that are still live + 380 extra units):

| | page alone | with pipeline fills |
|---|---|---|
| pass | 15 units, 13 buildings | 15 units, 13 buildings |
| pending | 973 (571 buildings) | 973 |
| fail | 225 | 225 |

- Fails: dogs not allowed or limit under 25 lb 162 (30 of them also ground floor), ground floor 37, page rent over
  $3,000 15, stated walk-up 6, available after Dec 15 4, 2+ beds 1.
- Pending by open facts: move-in + elevator 541, move-in + dogs + elevator 181, **elevator only 164**, dogs + elevator
  80, move-in + dogs 3, dogs only 2, move-in only 2.
- The pipeline fills add a dog policy for 12 rows and an elevator for 3; no row changes status, and the
  one-fact-open count moves from 168 to 171.

**Pass, 15 units in 13 buildings**: NJ 14 units / 12 buildings, NY 1 / 1. By lifestyle group: The Room-to-Breathe
Year 10 / 8 (all Bayonne), The Little-City Year 1 / 1 (Yonkers), The Old-Neighborhood Year 1 / 1 (West New York),
no group yet 3 / 3 (Jersey City 2, North Plainfield 1). All 15 are selected card rows at or under $2,800.

### Read this before using the 15

Every one of the 15 passes the elevator gate through `inferred_6plus_floors`, and that inference comes from the unit
label: `gates.gate_elevator` reads "42M" as floor 42 and "69B" as floor 69. Most of these labels are a landlord's
numbering, not a floor: `1204 John F Kennedy Blvd #35M / #32M / #42M` (Bayonne), `69 N Broadway #69B` and
`6 Duer St #6C` (the label repeats the house number). No page among the 15 lists an elevator. Only
`6050 Kennedy Blvd E #19D` (West New York) looks like a real high floor. **On stated facts, none of the 15 passes;
treat them as "elevator unknown" until checked.** The gate's label rule deserves a look by whoever owns `gates.py`.

**One fact open, 168 units in 142 buildings** (page alone; 171 / 143 with fills): elevator 164, dogs 2, move-in 2.
By state: NJ 120 / 105, NY 26 / 20, CT 18 / 14, PA 4 / 3. By group: The Old-Neighborhood Year 44 / 44,
The Room-to-Breathe Year 29 / 25, The Little-City Year 27 / 19, The Fresh-Start Year 7 / 4, no group yet 61 / 50
(Jersey City 17, Trenton 7, Morristown 5, Morrisville PA 4, Montville 4, others). 164 of the 168 are at or under
$2,800; 149 are selected card rows. Their floor is unknown for 125 and passes for 43.

## Not done

- 1,012 selected URLs were not requested (cap): NJ 673, NY 217, CT 117, PA 5; 141 building pages, 871 listing pages.
  They are the lower-value half of each state's queue (single listings whose card leaves two or three facts open).
  `python3 scripts/zumper_open_pending.py fetch` would continue from the log, but the script's cap is spent; raising
  `CAP` is the owner's call.
- Zumper will not settle the elevator question: 1,186 of 1,197 opened rows have no elevator statement. That fact has
  to come from the building's own site, PLUTO (NYC) or a call.
- 14 opened rows mention an elevator in the unit's or building's own description without an amenity tag
  (`notes` says "description mentions elevator"); following the harvester's rule these stay unknown. They are the
  cheapest elevator leads in the file.
