# Plan: a new trawl so the short version has enough to show

## Context

The short version works, but it has only 38 apartments in 22 buildings, and Brooklyn, Long Island City and Long
Island are almost absent. Will wants another trawl: nothing over **$2,200 base rent collected**, the short version
still **shows up to $2,000** (Will, 2026-11-17), priority on **New Jersey, Brooklyn, Connecticut, Long Island
(Nassau/Suffolk) and Long Island City**.

What the inventory found (read-only check today):

- **The bottleneck is confirming facts, not finding listings.** We already hold 6,809 listings at or under $2,200 in
  the priority areas (5,595 at or under $2,000), but they sit as `pending`: 6,611 have no elevator stated, most
  have no move-in date, and about 5,000 are search-result cards only (mostly Trulia, which we cannot open).
  Only 1,128 of the ≤$2,000 ones have a detail page; 883 of those state a floor.
- **The elevator-only rule was the biggest filter.** Will's decision today: **a walk-up is allowed if the apartment
  is one flight up (floor 2)**; the ground floor stays out; floor 3 and above still need an elevator.
- 1,197 Zumper detail pages were opened earlier and never merged (748 at or under $2,200), and 1,012 selected
  Zumper URLs were never fetched (the request budget ran out).
- Brooklyn and LIC at or under $2,000 are genuinely scarce on the reachable sites (that stock is mostly on
  StreetEasy and broker sites). Expect the gains to come mainly from NJ, CT and Long Island.

**Trulia:** not reopened. A person solving the CAPTCHA so our tools can continue is getting around a bot wall, which
the project rules forbid; Trulia has no public API. Instead, Will or Lamia can browse any site themselves and hand
over the listing (step 5).

## The work, in parallel where the files allow

### 1. The new floor/elevator rule (pipeline; one agent, owns the gate and rule code)
- `scripts/gates.py`, `scripts/parsers.py: elevator_rule`, `scripts/rank.py`, `scripts/avoid.py` wherever elevator
  or floor is decided: elevator stated or confirmed → as now (unpublished floor is a disclosure). No elevator, or
  elevator unknown: passes only when the floor is stated or confirmed as 2; floor 1/ground fails; floor 3+ fails
  without an elevator; floor unknown is **one** open gate fact ("Confirm the floor, and whether there is an
  elevator"). Floor read from a unit label (e.g. "2B") counts as "read from the apartment number" and carries the
  existing disclosure.
- `RENT_MAX` 3000 → 2200 for **collection** (gates and every harvester's `MAX_RENT`/`CAP`); the $3,000 total test is
  unchanged. Rows already held above $2,200 stay in `data/` but are excluded from the pages by the new limit.
  (Assumption: the first page also drops to $2,200 base rent; say if it should keep $3,000.)
- Tests in `scripts/test_rules.py`; decision recorded in `CLAUDE.md` and `docs/RANKING.md`.

### 2. Open what we already have (harvest; one agent per source, own output files)
- **Zumper**: merge the 1,197 opened rows (`data/listings_pending/zumper_opened*.csv`) through `h_zumper.py build`
  after re-checking the elevator heights the note says look wrong; fetch the 1,012 unfetched URLs that are at or
  under $2,200 in the priority areas; new searches with the `under-2200` path for each priority city/town.
  Same throttle and robots rules; Zumper has never refused us.
- **Apartment List**: a fresh run over the priority-area ZIPs of `data/reference/search_grid.csv` with
  `--fetch-max-low 2200` (it is the cleanest source: price and date on every row; it never states the floor, so the
  floor comes from unit labels or the step 3 records).
- **Trulia cards**: never fetched. For each card at or under $2,000, look for the same building (address match) on
  Zumper, Apartment List or the building's own site; a match replaces the card.

### 3. Confirm floor, elevator, dogs and move-in at scale (one agent per family, evidence batches 22+)
- Building height from official records: NYC PLUTO (already held, `data/reference/nyc_building_facts.csv`) for
  Brooklyn, Queens and LIC; New Jersey MOD-IV tax-list building descriptions (stories) for NJ; OpenStreetMap
  `building:levels` as a weaker source elsewhere. A 1–2-storey building settles "no elevator", which with floor 2
  now passes. (data.cityofnewyork.us refused us today, so no new NYC open-data calls this session.)
- Floor from unit-label conventions (`data/reference/unit_numbering_conventions.csv`).
- Dogs and move-in from the detail page or the building's own site; one refusal ends a host.
- Every apartment that could be shown gets a reviewed verdict (`scripts/verdicts.py`), as now.

### 4. New sources for the priority areas (probe first, one agent)
- Probe, one request each, robots and terms read first, stop at any refusal, write findings to `docs/SOURCES.md`:
  brokerage sites that carry MLS rentals (Long Island OneKey MLS, Connecticut SmartMLS, New Jersey GSMLS/NJMLS
  members), broker feeds used by Brooklyn/Queens brokers (RealtyMX-style sites like the one used on 2026-11-17),
  and regional management companies with stock at or under $2,200 in NJ, Long Island and CT.
- Harvest only the sources that pass, with a new `scripts/h_<source>.py` each writing `data/listings_raw/<source>.csv`
  in the 37-column contract (`docs/HARVEST_AGENT_BRIEF.md`).

### 5. A drop box for listings found by hand
- `inbox/` (git-ignored for raw files): Will or Lamia save a listing page (HTML, PDF or screenshot) from any site,
  Trulia, Zillow and StreetEasy included, or paste links into `inbox/links.txt`. `scripts/h_manual.py` is extended
  to read saved pages and screenshots (text and price read from what they saved; nothing fetched from those sites),
  and to fetch pasted links only from sites we are allowed to read. Each row is marked `source: owner`.

### 6. Rebuild, check, publish
- `scripts/run_all.py`, evidence and verdicts, then both pages' data; the short version at ≤$2,000 with parking of
  one-apartment neighborhoods as now.
- "Life here" research (same method as today) for every new building on the short version.
- An independent check of 30 random newly shown apartments against their pages before publishing.
- Republish the first page and the short version to their links.

## Assumptions (say if wrong)
- The first page also moves to $2,200 base rent; its $3,000 total test stays.
- No phone calls are part of this round.
- Long Island City and Brooklyn will likely stay thin at ≤$2,000; the page will say so plainly rather than pad.

## Verification
- `scripts/test_rules.py` covers every floor/elevator combination; `scripts/verify_all.py --with-browser` and
  `scripts/verify_concierge.py --with-browser` pass.
- A per-area table before → after (listings held, passing, shown on each page) in `PROGRESS.md`.
- The independent check finds no apartment whose price, floor or elevator disagrees with its page.
- No request to Trulia, nothing on the off-limits list, every refusal recorded in `raw/_host_kill_shared.json`.
