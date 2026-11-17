# Zumper, second trawl (2026-11-17)

Scripts: `scripts/h_zumper.py` (new stage `trawl2`; `build` now merges the opened rows) and
`scripts/zumper_open_pending.py` (fetch order and caps). Output: `data/listings_raw/zumper.csv`. The pipeline was not
run (another agent owns `gates.py` and the rules).

## What changed in the scripts

- **Limit $2,200** (`h_zumper.MAX_RENT`; `zumper_open_pending.RENT_SELECT`). Nothing new above $2,200 is collected.
  Rows held before the trawl keep the earlier $3,000 limit so nothing already held is dropped: `rent_cap()` gives
  $3,000 to a listing id in `raw/zumper/trawl2_held_ids.json` (snapshot of `zumper.csv` and `zumper_opened.csv`, 4,066
  ids, taken before any rebuild) or to a page or card read before `TRAWL2_START` (2026-11-17 16:45 UTC). The gates cut
  above $2,200.
- **Merge.** `h_zumper.py build` reads `data/listings_pending/zumper_opened.csv` (its first 41 columns) after
  normalising its own caches: one row per listing id; an opened row replaces the card row of the same id, or of the
  earlier id its page now shows the unit under; where both hold a detail row, the one read last wins. A card row whose
  opened page no longer shows the unit (summary status `gone`) is dropped, unless a search card in this trawl saw it
  again. Address-level fact sharing (dogs from building pages, elevator, building floors) then runs over the merged rows.
- **Requests.** `zumper_open_pending.CAP` 900 → 1,700 (cumulative). Its throttle is unchanged (4 s after the previous
  response, plus 0.5–2.5 s). `trawl2` uses 3 s between request starts plus 0.5–1.5 s of jitter. The first 324 trawl
  requests ran at 2.2 s plus jitter, before a cut-off transfer (below). `retries=1` everywhere: nothing is retried. A
  401/403/429, a bot-wall page, or a 200 without page data that looks like a wall writes `zumper.com` to
  `raw/_host_kill_shared.json` and `raw/zumper/BLOCKED.txt` and stops the run (`h_zumper.record_refusal`). Three
  network errors also stop a run, without counting as a refusal.
- **Facts stated on the page** (`h_zumper.page_text_facts`, `floor_from_text`, `elevator_from_page`,
  `dogs_from_desc`, `avail_from_desc`; both scripts use them; each value's source is quoted in `notes`):
  - floor: every floor statement about the apartment in its own description or title ("2nd Fl", "third-floor
    walk-up", "first floor of a three-family", "basement apartment" → 0, "ground-level unit" → 1, "top floor of a
    two-family" → 2). It is written only when all such mentions agree. Mentions about something else (laundry, office,
    storage, parking, a duplex's other level, square feet) are skipped, judged on the clause around the mention.
    Disagreements are noted and left blank.
  - elevator: `yes` when the page states it: an amenity tag (as before), the page's server-rendered
    "Amenities for <address> / Building: Elevator" list (`data-testid="building-amenity-Elevator"`, which the old
    parser did not read; Zumper says some units at the address have these amenities), or the listing description
    ("elevator building", "Elevator access"). Any negative wording (walk-up, no elevator) blocks a `yes`. Zumper's
    "Things you'll love" and "Highlights" chips are its own analysis and are not used. **No elevator, floor or building
    height is ever taken from a unit label.**
  - dogs: from the description only when no policy block or code settled it ("dogs welcome", "small dogs allowed" →
    yes, the quote kept in `dog_policy_text`; "no pets", "cats only" → no; both kinds of wording → left unknown and
    noted). Weight limit: also from the page-data `pet_policy.max_wt_in_lbs`.
  - move-in: Zumper's `date_available` as before. When it is empty: an explicit date, or "available
    now/immediately", stated in the listing's own description (`available_date_text` starts with `description:`).
    "Now" is judged against the day the page was read. A month with no day is not used.
  - The card square-foot sentinel (9223372036854776000) is no longer copied into notes.

## Elevator re-check (the 15 "pass" rows of 2026-11-16)

The CSV never carried an elevator taken from a unit label: all 15 had `elevator=unknown`. The inference came from
the previous `gates.gate_elevator`, which has since been changed so that labels never count. The rebuilt preview
(`zumper_opened_summary.csv`) has no label-based elevator left. Its 3 remaining `inferred_6plus_floors` previews rest
on a stated floor in the description (12th, 6th) or a "Six Floors" building tag, which is the gate's height rule.

## Runs

| step | requests | result |
|---|---|---|
| robots.txt re-read, 16:50 UTC | 1 | identical to 2026-11-15; no Claude group; `*` has no Crawl-delay |
| terms page `/terms-and-conditions` | 1 | no clause on robots, spiders or scraping; use allowed "only in reasonable limited quantities for your personal, non-commercial use". This project is personal and non-commercial, so the volume was kept modest |
| step 2: selected-but-unfetched URLs with card rent ≤ $2,200, 16:51–18:12 | 762 | 745 pages, 16 with no listing (removed), 1 HTTP 410. Priority areas first (NJ 539, CT 90, Long Island 30, Brooklyn 3), then 100 elsewhere |
| trawl2 priority searches, 18:13–18:39 | 2 test + 524 | 377 cities searched (NJ 217, Long Island 120, CT 39, `new-york-ny` for Brooklyn/LIC), 250 skipped (fresh counts show no studios or 1BRs), 1 network error |
| trawl2 priority details, 18:39–18:56 | 307 | new cards ≤ $2,200 with no detail row and no cached page |
| trawl2 rest of grid | 194 | 126 searches + 68 detail pages |

Total about **1,773 requests**, all HTTP 200 except one 410. **No refusal** (no 401/403/429, CAPTCHA or bot wall), so
nothing was written to the kill file. One transfer was cut off at 18:25
(`/apartments-for-rent/wilton-ct/1-beds/under-2200`, IncompleteRead after 4 KB of a 5.9 KB body; the proxy logged
nothing). It was not retried. The pace was then slowed to 3 s plus jitter after a 5-minute pause, and Wilton CT was left
unsearched (`raw/zumper/trawl2_errors.jsonl`).

Search path: `/apartments-for-rent/<city>/<1-beds|studios>/under-2200` (+ `?page=N`). The page's query confirms
`price.max = 2200`. Per-city status: `raw/zumper/trawl2_cities.json`. Cards: `raw/zumper/cards.jsonl` (`"trawl": 2`).

## Result (`data/listings_raw/zumper.csv`, against the file before the trawl)

3,692 → **4,161 rows**; detail rows 1,314 → **3,594**. Added detail rows (new listing id, or a card row now read from
its page): 2,281, of which **1,830 at or under $2,200**.

| area | ≤ $2,000 | $2,001–2,200 | total ≤ $2,200 |
|---|---|---|---|
| NJ | 994 | 219 | 1,213 |
| CT | 271 | 36 | 307 |
| Long Island | 52 | 20 | 72 |
| Brooklyn | 3 | 5 | 8 |
| LIC | 0 | 0 | 0 |
| rest of grid | 182 | 48 | 230 |
| **all** | **1,502** | **328** | **1,830** |

Fill on those 1,830 rows: floor stated 26% (1 or ground 185, basement 16, floor 2 181, floor 3+ 92); dogs stated 49%
(yes 503, no 394), weight limit 2%; move-in date 27% (84 of them from the description); elevator stated 4% (yes 43,
no 29). Zumper pages rarely say whether there is an elevator. With the floor-2 rule, floor 2 settles 181 of them
without one.

Left as cards at or under $2,200: 137 (NJ 88, CT 18, Long Island 4, Brooklyn 1, elsewhere 26), mostly cards from
before the trawl whose card is still live.

Brooklyn and LIC are thin on Zumper at this price (NYC under $2,200: 8 Brooklyn units, no LIC unit), as the plan
expected.
