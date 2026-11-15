# Plan: Lamia's House Hunt, finished version

## Context

Lamia needs two or three places to tour from **Nov 22**, for a move-in between now and **Dec 15**. The mock-up
(artifact `45EsZ66YhUkf5fTWz3ZjU2`, "Mock-up 4") fixes the interface: pick a year, tour a neighborhood, look at
places, hold up to three, compare. Everything in the mock is invented. The finished version must be built
**entirely from collected data**: which years exist, what they're called, which neighborhoods and places appear,
and every sentence. No mock wording carries over.

State today: `house-hunt/` holds 98 seed areas, the Census data, a cached fetch library and source-access results.
Nine of ten Phase 1 agents were interrupted; their scripts and caches are partial. There are no listings yet.

## Rules Will approved (2026-11-15)

**Gates. A unit must pass all of these to appear:**

| Gate | Rule |
|---|---|
| Type | Studio or 1BR |
| Money | Listed rent ≤ $3,000 **and** all-in ≤ $3,000. All-in = rent + required fees + pet rent + parking + estimated electric, gas and internet where not included. Any estimated or missing line gets an asterisk |
| Move-in | Available now through Dec 15, 2026 |
| Dog | Dogs explicitly allowed, and any weight limit is **25 lb or more** (Will lowered it from 40 on 2026-11-15: the dog will not exceed 25 lb). A size-only policy of "small dogs" passes (Will, 2026-11-15), with a tour question to confirm the limit. "Not stated" fails until the building's pet policy confirms it |
| Building | Elevator building only. No walk-ups and **no ground-floor units**. Where a listing does not state it, a building of 6+ floors is treated as having an elevator, with an asterisk (Will, 2026-11-15) |
| Place | Free-flow drive to Jamaica station under 2 hours. **Queens is included** (Will reversed the earlier exclusion) |
| Proof | Live link; price and date read from the listing page itself, with the time seen |

**Per neighborhood:** up to **10 places**, plus up to **5 "looks good, but avoid"** cards.

**Avoid = passes every gate, but has a documented deal-breaker:**
- **Car crime:** 3 or more independent reports at the building or its parking in 24 months, or (where police publish locations) vehicle crime near the address at least double the median for candidate buildings in the same city. Some car crime everywhere is expected; the test is whether it's disproportionate.
- **Elevator:** 3 or more independent outage reports, or an official record.
- **Management:** judged on the **last 6 months**. Three or more tenants reporting the same serious problem in that window makes an avoid. Older complaints alone become "Gives us pause", marked as older.
- **Listing trouble:** contradictory dog policy, or a listing 60+ days old.

**Which 10 are shown when more pass:** cheapest all-in, biggest, best parking, closest to green space, then by completeness of information; at most two units per building.

**Neighborhoods** come from a broad net over the whole 2-hour area, not from the 98-area seed list.
**Years** (5 or 6) and their names come from grouping the qualifying neighborhoods by measured traits.

**Assumptions I'm making (say if wrong):**
- All five boroughs are in, Queens included.
- Where a listing doesn't state the floor and the unit number doesn't reveal it, the unit is kept with an asterisk and "which floor?" becomes a tour question.
- A neighborhood needs at least 3 passing places to appear. Where fewer than 10 pass, the page shows what there is.
- The budget slider's top moves from the mock's $3,200 to $3,000.

## Consequences of the key decisions (no Google key; Reddit only)

- **Drive times are free-flow estimates** (OSRM), shown with an asterisk. They understate Sunday-evening traffic.
- **Building reviews outside NYC will be thin.** Sources left: Reddit (once the key is approved), Trulia's on-page "What Locals Say", Openigloo (NYC), public tenant complaints (NYC 311 and HPD), Better Business Bureau complaints against managers (access untested), local news. Expect many quote slots to stay empty.
- **Fiber** is a tour question unless a public source turns up.

## Steps

### 1. Foundation rerun (day 1, parallel agents)
Restart the interrupted agents with the existing brief (`docs/PHASE1_AGENT_BRIEF.md`), resuming from `raw/` caches.
Scope each to what the page uses, and make routers callable for any address:
- Driving and tolls (`scripts/p1_drive_fetch.py` → importable `drive()`, `tolls_for_route()`, `data/reference/tolls.csv`)
- Transit router (`scripts/p1_transit_feeds.py` → importable `route()`)
- Crime: NYC point data (`scripts/p1_safety_nyc.py`), other states by police agency, FBI API (key saved)
- OpenStreetMap extract processed locally (parks, dog parks, food, bars, cafés, groceries, coastline, water)
- Electricity and gas prices by utility; renter protections; flood zone where reachable
- Dropped: building permits, noise, walkability extras

### 2. Broad-net inventory harvest (days 1–2)
- Build the search grid: every ZIP within the 2-hour drive, Queens included (ZCTA list + OSRM).
- Harvest by source, one agent each, honouring robots rules and crawl delays in `docs/SOURCES.md`:
  Trulia (by ZIP), Zumper (by city, plus building pages), Craigslist (HTML), Apartment List (city pages),
  AvalonBay, Fairfield, Greystar (browser + sitemap), Veris and other management sites that allow it.
- Normalize to `data/listings.csv` / `data/buildings.csv` (schema in `docs/DATA_DICTIONARY.md`, extended with
  `floor`, `gate_results`, `all_in_lines`, `price_seen_at`). Geocode buildings with the Census geocoder
  (`scripts/build_areas.py: census_geo`). Deduplicate by address + unit.
- Apply gates in `scripts/gates.py`; log the count dropped at each gate.
- Will or Lamia can paste StreetEasy or other links at any time; a `scripts/add_manual_listing.py` path checks them the same way.

### 3. Neighborhoods and years (day 3) — **approval checkpoint A**
- Group passing buildings into neighborhoods (municipality or NYC neighborhood area).
- Compute traits per neighborhood: drive and transit minutes, rent and space medians, building age and height,
  going-out density, green and water proximity, parking types, crime rate.
- Cluster into 5 and into 6 groups; pick the cleaner split; name each from its distinguishing traits.
- **Will approves:** the neighborhood table, the year groupings and names, and the score thresholds
  (safety fifths, tile tints) before anything is written.

### 4. Depth on the chosen places (days 3–4)
Per building: drive, tolls and transit from its address; nearest green space and dog park; cafés in a 10-minute walk;
crime near the address where published; parking type, fee and local street-parking rules; pet policy and fees;
utilities estimate; tenant voices and records with dates. Per neighborhood: food, errands, getting around, dog rules,
resident quotes (verbatim, dated, linked, no usernames; `scripts/verify_quotes.py` re-fetches each).

### 5. Avoid list — **approval checkpoint B**
`scripts/avoid.py` applies the thresholds to dated evidence and writes each avoid with its links. Will reviews the list.

### 6. Synthesis
- `data/evidence.csv`: one row per fact, with source link and date.
- Scores, tints, hooks, comparison sentences: rule-based from evidence, rules in `docs/SYNTHESIS_RULES.md`.
- Year and neighborhood text: written only from evidence rows; each sentence stores the row ids it rests on.
  A separate checking agent rejects any sentence without support. Every year gets the same scenes at the same length.
- Unknowns show as "Not known yet", never a guess.

### 7. Build and publish (day 5) — **approval checkpoint C**
- `scripts/build_page.py` emits `site/data.json` and the page, reusing the mock's layout and code with the
  invented data replaced; the ring map becomes a real inline map with town names; photo buttons open the listing;
  tile sheets link each line to its source; every price shows the date seen.
- Publish as a **new private artifact**. Will reviews a draft.

### 8. Final check (Nov 21)
Re-fetch every shown listing; drop or mark anything gone or repriced; republish.

## Verification
- `scripts/validate.py`: every shown unit passes all gates; every fact has a link and date; no sentence lacks evidence ids; no quote fails re-fetch; all-in arithmetic matches its lines.
- Link check on all listing URLs on the build day and again Nov 21.
- Open the built page in the headless browser at phone width; click through year → neighborhood → place → hold → compare; confirm sliders change the counts and the console is clean.
- Spot-check 10 random units by hand against their live listing pages.

## Risks to know now
- **Thin inventory.** Elevator-only, no ground floor, dogs explicitly allowed, all-in ≤ $3,000 and a 3-week window will cut hard. Some neighborhoods may show far fewer than 10, and some expected areas may not qualify at all.
- **StreetEasy, Apartments.com and Zillow listings are out of reach** for a script, which hurts Queens, Brooklyn and the Bronx most. Will's instruction: get what can be got, and say what's missing.
- **Five days is tight.** If time runs short, the order of sacrifice is: quotes, then transit times, then neighborhood prose. Units, gates, avoid cards and comparison stay.
