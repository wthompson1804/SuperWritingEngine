# Resolving pending listings in the three thin years (batch 18, 2026-11-15/16)

Script: `scripts/resolve_pending_thin_years.py` (steps `select`, `fetch`, `sites`, `crawl-sites`, `secondary`, `fetch-urls`, `write`).
Outputs are in **`data/evidence_pending/`**, not `data/evidence/`, so the running repair agent does not pick them up
before the coordinator decides. Nothing existing was edited and the pipeline was not run.

## What was asked
Pending listings (a gate fact is simply not stated) in neighborhoods of The Walk-Everywhere Year, The Quiet-Street Year
and The Fresh-Start Year: find the ones that pass once the missing fact is settled from a page we may read.

## Selection funnel (`funnel.json`)

| Step | Listings | Buildings |
|---|---|---|
| All harvested listings | 20,464 | |
| Pending | 13,595 | |
| Studio or 1BR | 13,595 | |
| Listed rent ≤ $2,800 | 12,514 | |
| Available by Dec 15 or date unstated | 12,514 | |
| One or two unstated must-confirm facts (movein, dog, elevator, proof), none failed | 4,448 | 2,504 |
| In a thin-year neighborhood (before the crime cut) | 633 | |
| ...of which in crime-cut neighborhoods, dropped: New Haven 112, FiDi-Battery Park City 3, Watchung 1 | 116 | |
| In a thin-year neighborhood that passes the safety rule | 517 | 204 |
| Taken (ranked by candidate units, then lower rent; cap 150 buildings) | 463 | 150 |

By year before the cap: Fresh-Start 235 listings / 100 buildings, Quiet-Street 220 / 46, Walk-Everywhere 62 / 58.
The cap of 150 kept 82 Fresh-Start, 31 Quiet-Street and 37 Walk-Everywhere buildings; the 54 left out are single-unit
buildings with the highest rents.

"Unstated facts" counts the facts `gates.py` requires (`pending_reasons`). An unknown floor is allowed by the gate
(asterisk) and is not counted, but a ground-floor reading still fails a unit here.

**Neighborhood** is derived the way `scripts/build_neighborhoods.py` does it (NYC 2020 NTA polygon inside the city, else
Census incorporated place, else county subdivision, from the listing's coordinates): 147 of the 150 buildings. Three
buildings without coordinates (Vermella Harrison's own-site rows, two Fairfield Properties communities in Smithtown) use
the fallback ZIP → neighborhood of passing units; `hood_basis` in `candidates.csv` says which. To keep the Census
geocoder to about 1,900 calls, buildings more than 10 km from any thin-year passing unit whose city name is not a
thin-year neighborhood name were not geocoded (615 buildings).
Safety: neighborhoods with `safety_cut = True` in `data/lifestyle_groups.csv` (rule in `docs/SAFETY_BASIS.md`) were dropped.

## What was read
- 179 listing pages re-read (Apartment List 98, Zumper 32, management sites 49). No Trulia request was made: Trulia
  candidates (29 units) rest on their cached page and are marked `blocked` in the live check.
- Own sites of 66 buildings (robots.txt first; home page plus up to four amenity / pet / FAQ / floor-plan pages).
- 89 cross-look-ups: Zumper address pages (24 found, 49 not on Zumper) and guessed Apartment List pages (1 real, 15 soft-404).
  They settled nothing new: only one address page named an elevator (600 Hudson St, Hoboken, whose unit still lacks a dog policy).
- Other rows of the same building already in `data/listings.csv` (their cached pages), `data/master_units.csv` for the
  all-in overhead, and the PLUTO columns already in `listings.csv`.

## Refusals (rule: one refusal ends the host, persisted in `data/evidence_pending/refused_hosts.json`)
14 hosts answered 403 on the first request and were not asked again (the ledger is read at every start, so a restart
does not retry them): 1harrison.com, akelius-properties.us, brimcrown.com, chathamhillnj.com, confluencenorwalk.com,
deyandbergen.com, goldberg-realty.com, harboursidesono.com, ironstate.com, ironworkssono.com, livecreeklineapts.com,
moderaberkeleyheights.com, therailnorthbergen.com, vermellaharrison.com (the 403 came from its `tours.` subdomain after
the main site had answered; the whole domain was closed anyway). These are RentCafe/Yardi-hosted building sites behind
Cloudflare, as `docs/SOURCES.md` already says for RentCafe. Apartment List, Zumper, AvalonBay, Greystar, Fairfield,
Garden Communities and Propertyware did not refuse. Three connection errors (not refusals): oxfordrealtygroup.com (http),
sonometroliving.com, one Propertyware page. `lib.cached_get` was called with `retries=1`, so a 429 is never retried.

## Result (`resolved_candidates.csv`, `summary.json`)

| Verdict | Units | Buildings |
|---|---|---|
| now_passes | 65 | 3 |
| still_open | 393 | about 145 |
| fails | 5 | 5 |

**now_passes, by year and neighborhood**
- Fresh-Start / Harrison NJ: **Vermella Harrison**, 2 units (VH-236 $2,176 from Dec 5; VH-302 $2,221 from Dec 4). Elevator
  is an amenity tag on the Zumper page of the same building. Price and date are the harvester's reading of the site's
  own unit feed at 2026-11-15 18:48 UTC; they could not be re-read because the domain then refused.
- Quiet-Street / Berkeley Heights NJ: **RT 500**, 59 units ($2,622–$2,770). Dogs: Apartment List page of the same
  community ("allowed_pets=dogs/cats", no weight limit stated). Elevator: **inferred, asterisk** — Greystar's page lists
  units on floors up to 10 (the page's floor field, not a unit-label guess), which the plan treats as an elevator
  building. **All 59 carry an all-in warning:** the three RT 500 units already judged carry about $477 a month on top of
  rent and fail the all-in cap at rents of $2,572–$2,632, so none of these is likely to be shown.
- Quiet-Street / Teaneck NJ: **Avalon Teaneck**, 4 units, all duplicates of units that already pass from Apartment List
  (`duplicate_of`). No new inventory.
- Walk-Everywhere: none.

So the pass adds **two units in one building that can actually reach the page** (Vermella Harrison), plus 59 units that
clear the listing gates but will almost certainly fail the money gate.

**fails (5):** 910 Park Pl 1D and 266 Main Ave Norwalk (page says first floor), Fairfield Manor at Nesconset studio
(site describes the plan as first floor), 39 Throop Ave #201 and one Chatham Hill unit (no longer on the page).

**still_open with a single question: 289 units in 82 buildings** (`open_questions_by_building.csv` is the call sheet).
- "Is there an elevator?" 185 units / 40 buildings. The elevator is not named on Apartment List, Zumper, the cached
  Trulia page or the building's own site (or the own site refused). Largest: Avalon W Squared at Princeton Junction
  (65 units), The Beacon Norwalk (10), The Gardens at Raritan (10), Brookside Wilton (10), 330 Harrison Station (8),
  Chatham Hill (8), Harrison Station (6), Avalon Princeton Circle (4), Riverview Terrace (4).
- "Which unit, and when is it available?" 78 units / 17 buildings: Zumper floor-plan rows with a "from" price and no
  date. Most of these buildings already have passing numbered units from another source (Waypointe, Harbourside,
  Confluence, The Brunswick, The Wyldes, Raritan Heights, Avalon Teaneck), so they are not new inventory. New
  buildings in this group: Brim and Crown (10 plans), Iron Works SoNo (4), The Vue (3), 805 St. Marks Ave (2).
- "Are dogs allowed, and what is the weight limit?" 26 units / 25 buildings, nearly all single NYC and Hudson County
  units listed through Apartment List whose page says only "Pet friendly"; the agent's Propertyware page leaves "Pets:" blank.
The other 104 open units need two or three answers (mostly elevator + dogs on single MLS listings).

## Things the coordinator should know
1. **Avalon W Squared (65 units) may not belong to Princeton.** Its two sources give different coordinates and the
   address is 500 Avalon Square, West Windsor 08550 (Princeton Junction). The pipeline method put it in `nj:princeton`
   from the first row's coordinates. Check before using it.
2. **Brookside Wilton's eight passing units rest on unit labels.** They pass through `inferred_6plus_floors` from labels
   601–716; the ten pending units have labels 2xx–5xx. If the first digit is a building number rather than a floor, the
   eight are not evidence of height. Nothing on brooksidewilton.com names an elevator or a storey count.
3. **Skyline Tower, New Brunswick:** the cached Trulia building page names an elevator but says dogs are not allowed;
   Apartment List says cats and dogs are allowed. Left open as a contradictory dog policy.
4. **357 Grove St, 1512 Park Pl (Brooklyn):** Apartment List names an elevator but PLUTO classes them C2 / C1 (walk-up)
   on an exact address match. Left open with that conflict stated.
5. For NYC rows where the PLUTO elevator class came from a `nearest_lot` match rather than the exact address, the
   elevator is treated as still open (rule in the brief).
6. Dog policy taken from another listing of the same building counts only for a managed community (five or more rows
   of it, or a building-level page). For single co-op / condo units it is left open with the other listing quoted.
7. Search-card rows are never used as evidence for a fact.
8. `items_batch_18.csv` has only its header: no tenant or public-record evidence was looked for in this pass.
9. DOB elevator-device records (NYC Open Data) could settle the seven NYC buildings with PLUTO class RM; that source was
   outside this brief's list and was not used.

## Files
`data/evidence_pending/`: `confirm_batch_18.csv`, `facts_batch_18.csv`, `live_check_batch_18.csv`, `items_batch_18.csv`
(same columns as batches 1–17), `resolved_candidates.csv`, `open_questions_by_building.csv`, `summary.json`,
`funnel.json`, `candidates.csv`, `candidate_buildings.csv`, `building_sites.csv`, `site_pages.jsonl`,
`secondary_urls.csv`, `fetch_log.jsonl`, `request_log.jsonl`, `refused_hosts.json`, `hood_cache.json`, run logs.
Raw pages: `raw/resolve_pending_b18/`.

## Contacts for the call list (2026-11-16, `scripts/thin_call_contacts.py`)

Adds a phone, office hours and the building's own leasing URL to the 82 one-question buildings. Outputs:
`data/evidence_pending/open_questions_contacts.csv` (all 82) and `out/call_sheet_thin_experiences.md` (78: the four
buildings with an all-in warning are left out and named in the sheet's last line). Both are rebuilt whole on each run.
**No request was made**: everything was read from pages already cached under `raw/`. No new refusal; neither ledger changed.

How it works. The parsers are imported read-only from `scripts/building_contacts.py`, so a number means the same thing
as in `data/reference/building_contacts.csv`. For each building the script reads: the cached pages of its candidate
listings (`raw_path`) and their re-reads in `raw/resolve_pending_b18/`; other `data/listings.csv` rows at the same
address or with the same name and ZIP (building-level pages only); the own-site pages the resolve pass crawled
(`site_pages.jsonl`, minus a portfolio site's home page); and any cached page whose last path segment is the building's
name (an Apartment List page in the same state, or a page on a manager's site, e.g. `livebh.com/apartments/harbourside-sono/`).
Preference: own site > Apartment List `original_phone` > Zumper building page > Trulia building page (tracking) >
brokerage number on the unit's own listing.

| Experience | Buildings | Own office | Property-supplied | Tracking only | Brokerage | No phone |
|---|---|---|---|---|---|---|
| Fresh-Start | 50 | 14 | 10 | 9 | 0 | 17 (11 broker-listed, 5 individual owner, 1 managed: Iron Works SoNo) |
| Quiet-Street | 15 | 5 | 5 | 4 | 0 | 1 (individual owner) |
| Walk-Everywhere | 17 | 0 | 0 | 1 | 1 | 15 (9 broker-listed, 6 individual owner) |
| All | 82 | 19 | 15 | 14 | 1 | 33 |

Office hours are filled for 40 buildings and an own-site URL for 37.

Three rules this script adds to `building_contacts.py`'s behaviour:
1. **Single-unit Apartment List listings carry no phone here.** A listing whose `contract` is `free` (feeds:
   Propertyware unit, ListHub, Avail, Tenant Turner, Listanza, long-tail; no unit count, no management company, no office
   hours) shows the number of whoever posted the unit: a private landlord or an individual agent. Nothing on the page
   says it is a brokerage's office line (`office_phone` is empty on all of them), several have area codes far from the
   unit (213, 310, 409, 607, 678, 838), and the brokerage attribution on these pages sometimes points at a different
   unit. 19 such numbers were on the cached pages and were **not recorded**; the rows are `broker` (a brokerage is named)
   or `individual owner`, with the listing link. This is why Walk-Everywhere has no real office number: 15 of its 17
   buildings are single units of this kind. `building_contacts.py` does not have this rule, so some "supplied" numbers
   in `data/reference/building_contacts.csv` for single-unit Apartment List rows may be a poster's own number.
2. A broker or owner of **another** unit at the same address is not used as this unit's contact.
3. An own-site number outside the NY/NJ/CT area codes (and not toll-free) gives way to a local number the property
   supplied. One case: Modera Berkeley Heights, where `millcreekplaces.com` shows a 561 (Florida) head-office number and
   Apartment List carries (908) 944-9200.

Caveats.
- The 14 tracking numbers are 11 Trulia building-page forwarding lines and 3 Zumper `(844) ... ext.` proxy lines (The Vue,
  Brim and Crown, 805 St. Marks Ave). They can stop working when the listing ends. Ten of the 14 (Norwalk, Wilton,
  Fairfield CT, Crown Heights) have no known own site; (203) 900-4467 serves three buildings of one owner (8 Union Ave, 31 Ferris,
  Three Hubbard Rd).
- The Beacon, Norwalk: the own site shows (203) 826-8490 and Apartment List carries (203) 826-8726. The own-site number
  is used; an own-site number can itself be a marketing vendor's call-tracking line.
- 12 of the 34 real numbers are toll-free leasing lines (RentCafe / Avalon), which is how those properties publish them.
- Fairfield at Hauppauge and at Smithtown: the manager's pages are cached but show several numbers and none in JSON-LD,
  so the Trulia tracking line stands; the leasing URL points at the manager's page.
- Iron Works SoNo is the only managed building with no number: its Zumper page has hours but no phone, the cached
  Apartment List page for it is an empty (soft-404) page, and `ironworkssono.com` refused earlier. No other allowed page
  existed to fetch, so the one-request-per-building step had no target. The same holds for the 32 broker / owner units
  (their Apartment List or Zumper page is already cached; no phone is wanted for them).
- `--fetch` is implemented (one Apartment List or Zumper page per building with no phone, never an own site or Trulia;
  ledgers `data/evidence_pending/refused_hosts.json` and `raw/_host_kill_shared.json` read first and written on a
  refusal) and was run: 0 requests.
