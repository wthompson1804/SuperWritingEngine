# Region pass: Westchester and Rockland counties, NY (building-first), 2026-11-15

Two agents worked this region on the same day. The first was stopped at about 20:08 UTC; the second continued from its
files (about 21:40 to 22:10 UTC) and did not restart anything. All pages are cached; the outputs are rebuilt from the
caches by one script.

## Gates used (as changed after the brief)

Studio or 1BR, listed rent ≤ $3,000; available now through 2026-12-15; elevator building, no ground-floor units; dogs
explicitly allowed with any weight limit ≥ **25 lb** (was 40). The script constant is `MIN_WL = 25`.

Effect of the 25 lb change: Parkside at the Harbors and Riverside (Haverstraw, 30 lb on the Trulia pet card) moved from
fail to pass with units. Boulder Pointe (Middletown, 30 lb) no longer fails on weight (elevator still unconfirmed).
The Altos (White Plains) has a 40 lb limit on its own site and passes. Sutton Hill (20 lb) and 158 Willow St, Yonkers
(10 lb) still fail. Buildings whose Trulia pet card says only "Size allowed: Small" (no number) were recorded as fails
under the 40 lb gate; they are now `unconfirmed:dog size` and keep all their unit rows, each flagged
`DOG SIZE UNCONFIRMED` in `notes` (The Magnolia, 30 Broad Street, 66 Main, Miroza Tower III, The Brompton, The Reserve at
Clarkstown, 20 S Broadway Nyack, Chateau Rive and about 20 garden complexes).

## Files

- `data/listings_raw/region_westchester_rockland.csv`: 810 rows (contract columns). 91 of them are one-per-building
  `BUILDING_FAILS:` rows.
- `data/reference/region_buildings_westchester_rockland.csv`: 223 building records (58 pass with units, 86 unconfirmed,
  77 fails, 2 blocked). Same 19 columns as before.
- Scripts (all `scripts/h_region_westchester_rockland*.py`):
  - `.py`: the builder. Rebuilds both CSVs from caches. `--refresh-sightmap` refetches the own-site unit feeds.
  - `_data.py`: hand-recorded building facts (`CURATED`, 47 buildings) and buildings with no unit rows (`MANUAL_BUILDINGS`, 7).
  - `_trulia.py`, `_trulia_zip.py`: Trulia lead pages and the per-ZIP building list (52 ZIPs, any price, studio/1BR filter).
  - `_al.py` (new): Apartment List town pages for 51 town slugs, then every property page found (135 properties).
  - `_zumper.py`, `_zb.py` (new): Zumper town pages (36 towns, discovery only) and 26 Zumper building pages (facts only).
  - `_probe.py`, `_grep.py`: own-site readers used by hand.
- Raw: `raw/region_westchester_rockland/` (`trulia_detail.jsonl`, `trulia_zip_buildings.json`, `al_props.jsonl`,
  `zumper_town_buildings.json`, `zumper_buildings.jsonl`, own-site pages and SightMap feeds).

## Method

1. Trulia: every lead page, then every building card in 52 ZIPs (157 buildings), each building page read.
2. Apartment List: 1BR and studio filter pages of each town for discovery; each property page read (pet policy,
   amenities incl. "Elevator", year built, manager, own-site URL, units).
3. Own leasing sites: about 60 probed. Where the site embeds a SightMap unit feed, units, floors, dates and required monthly
   fees come from that feed (One Webb Ave, Sawyer Place, The Mitchell, The Halden, 360 Huguenot, The Leaf, Motif,
   One Clinton Park, Two Clinton Park, Continuum, Carraway, The Sheldon).
4. Facts are merged per building. Hand-recorded facts win, then own site, then Trulia, then Apartment List. Each merged
   fact names its page in `notes`. Trulia and Apartment List records are matched by building name or normalised address.
5. Elevator = yes only when a page lists an elevator, or the building has 6+ floors (own-site floor list, a storey count
   in page text, or unit numbers read as floor + unit; the basis is in `notes` and in `elevator_basis`).
6. Dogs = yes only when a page names dogs (pet card, policy text, or a dog park / dog run amenity).

## Towns covered

| Town | Buildings examined | Pass with units | Unconfirmed | Fails | Blocked | Rows |
|---|---|---|---|---|---|---|
| Mount Vernon (incl. Fleetwood) | 5 | 1 | 2 | 2 | 0 | 22 |
| Pelham | 2 | 0 | 1 | 1 | 0 | 4 |
| New Rochelle | 28 | 17 | 4 | 7 | 0 | 135 |
| Yonkers | 40 | 9 | 18 | 13 | 0 | 152 |
| Bronxville | 5 | 1 | 2 | 2 | 0 | 7 |
| Tuckahoe | 2 | 0 | 1 | 1 | 0 | 10 |
| Eastchester | 2 | 0 | 1 | 1 | 0 | 4 |
| Scarsdale | 0 | 0 | 0 | 0 | 0 | 0 |
| Hartsdale | 1 | 1 | 0 | 0 | 0 | 1 |
| White Plains | 30 | 14 | 8 | 8 | 0 | 109 |
| Harrison, West Harrison, Purchase | 5 | 3 | 2 | 0 | 0 | 31 |
| Mamaroneck | 5 | 0 | 1 | 4 | 0 | 8 |
| Larchmont | 2 | 0 | 1 | 1 | 0 | 4 |
| Rye | 1 | 0 | 1 | 0 | 0 | 1 |
| Port Chester | 12 | 3 | 6 | 3 | 0 | 76 |
| Tarrytown | 1 | 0 | 0 | 1 | 0 | 6 |
| Sleepy Hollow | 3 | 0 | 0 | 3 | 0 | 2 |
| Dobbs Ferry | 1 | 1 | 0 | 0 | 0 | 9 |
| Hastings-on-Hudson | 0 | 0 | 0 | 0 | 0 | 0 |
| Irvington | 1 | 0 | 0 | 1 | 0 | 2 |
| Elmsford | 5 | 0 | 3 | 2 | 0 | 35 |
| Ossining | 9 | 0 | 4 | 5 | 0 | 14 |
| Croton-on-Hudson | 3 | 0 | 2 | 1 | 0 | 4 |
| Peekskill | 10 | 2 | 7 | 0 | 1 | 27 |
| Mount Kisco | 3 | 0 | 2 | 1 | 0 | 8 |
| Pleasantville | 1 | 0 | 0 | 1 | 0 | 3 |
| Nyack, West Nyack | 11 | 0 | 5 | 5 | 1 | 20 |
| Piermont | 0 | 0 | 0 | 0 | 0 | 0 |
| Pearl River | 1 | 0 | 0 | 1 | 0 | 5 |
| Nanuet | 3 | 0 | 2 | 1 | 0 | 10 |
| Spring Valley | 1 | 0 | 0 | 1 | 0 | 2 |
| Suffern | 4 | 0 | 2 | 2 | 0 | 8 |
| Haverstraw, Garnerville | 6 | 3 | 2 | 1 | 0 | 26 |
| New City, Pomona | 3 | 1 | 0 | 2 | 0 | 4 |

Rows for Middletown, Brewster, Central Valley, Baldwin Place and Buchanan are in the file because the leads file held
them; they belong to the Mid-Hudson region and were not worked further here.

## Hudson river towns (asked to be exhaustive)

Every building that Trulia (ZIP lists), Apartment List (town pages and sitemap) and Zumper (town pages) show for these
towns was read. Results:

- **Yonkers waterfront**: pass with units: Hudson Park, Apex Hudson Riverfront, Alexander Crossing, Avalon Yonkers,
  Hudson Piers, Sawyer Place, Hudson 44, Regency on Hudson. Unconfirmed: River Tides and 70 Pier (GDC; the building site
  says pet friendly, the Trulia pet card says no dogs), 66 Main (dog size). Above the cap: Stratus on Hudson (from $3,495),
  Trolley Lofts (from $3,445), 1177 @Greystone (from $3,795, no dogs).
- **Dobbs Ferry**: The Danforth. Its own floor-plan page lists 1BR plans at $2,750 to $3,000 (five rows written,
  `detail_level=floorplan`, no unit numbers or dates). Trulia shows 1BRs from $3,605 and Apartment List from $3,429 the same
  day. The rows carry a `PRICE CONFLICT` note. Needs a call before it is shown as available.
- **Hastings-on-Hudson, Irvington, Piermont**: no elevator rental building with a studio or 1BR listing found. Irvington:
  47 Main Street (no dogs). Zumper lists two Dobbs Ferry elevator buildings with 2BRs only (185 Ashford Ave, 78 Main St).
- **Tarrytown**: Everbend Tarrytown (formerly Talleyrand / Halstead Tarrytown), one 1BR at $2,979 dated after Dec 15;
  elevator not stated on any page read; own site not reachable. Hudson Harbor is condominiums (single units only).
- **Sleepy Hollow (Edge-on-Hudson)**: NorthLight (studio/1BR from $3,783; Trulia pet card says no dogs; bozzuto.com
  robots.txt disallows the page for us) and Emerson (1BR from $3,577; own-site SightMap feed: 12 units, none ≤ $3,000;
  pet rent $50, parking $75 to $300). Both fail on price.
- **Ossining**: Harbor Square (GDC; own site lowest price $3,075; elevator, dogs allowed, rooftop pool, reserved indoor and
  outdoor parking) and Terraces on the Hudson (Avalon Ossining, from $3,077) fail on price. The rest are garden
  complexes with no elevator evidence, or no dogs.
- **Croton-on-Hudson**: garden complexes only (no elevator evidence); Half Moon Bay is condominiums from $3,400.
- **Peekskill**: pass with units: Fort Hill (GDC, 7 units in window) and Park Place Towers (7). Chateau Rive (elevator;
  dog size unconfirmed), 150 Overlook Ave (elevator; dogs not stated). East Point on Hudson: own site 403, no allowed copy.
- **Nyack**: no passing unit. Riverview at Nyack ($2,600 to $2,975, dogs $60/mo, elevator not stated). 20 S Broadway
  (elevator; dog size "Small"). 7 South Highland (Gateway Lofts): Trulia says no dogs. West Shore Towers: from $3,100.
  Pavion: no current listing on Trulia; own site not reachable. River Edge at Nyack: 2BRs only. Montclare (6 N Midland):
  found by search only, on blocked sources: manual check.
- **Haverstraw (Harbors at Haverstraw, GDC)**: Admirals Cove (8 units in window), Riverside (5), Parkside (3). Riverside and
  Parkside show a 30 lb dog limit on Trulia; Admirals Cove states none (check). New: Asteri Hudson / Hudson Rise, 16 Dowd
  St: 2BRs only at $3,250.

## What blocked

- Own sites answering 403 or a challenge: moderanewrochelle.com, thegramercywhiteplains.com, encore325.com,
  rentthemason.com, 66main.com, parkplacetowers.com, harborgroupmanagement.com (Skyline), 3thirty3apts.com,
  shearwoodstation.com, 51southwhiteplains.com, trilogylofts.com, hudsonpiers.com, 15bankapartments.com,
  thestandardnr.com, thehenrypomona.com, eastpointonhudson.com, vistaattowngreen.com (robots.txt itself 403),
  equityapartments.com (Alexan Harrison).
- robots.txt disallows: bozzuto.com property pages (NorthLight), hudson44.com, hudsonriseapartments.com.
- Not reachable (no DNS or connection): pavionnyack.com and several guessed domains (logged in the cache index).
- Apartments.com, RentCafe, Zillow detail pages: not used (blocked sources per `docs/SOURCES.md`).
- No Trulia, Apartment List or Zumper block occurred.

## Known gaps and cautions

1. **Elevator not confirmed for 5-storey buildings.** Rockwell, Abendroth, Alexan Harrison, The Halden, The Castle,
   Avalon Harrison, The Huguenot, 15 Bank, Riverview at Nyack, Vista at Town Green, Highlands Nanuet, Crestwood Lake and
   others have dogs allowed and units in the window, but no page read states an elevator and the unit numbers do not
   reach floor 6. They are `unconfirmed:elevator`, with their unit rows kept. A phone call would likely clear most.
2. **Dog policy conflicts.** One Clinton Park, Two Clinton Park and Carraway: Trulia says dogs not allowed; the building's
   own site (dog park, pet spa, pet rent) and Apartment List say allowed. Recorded as dogs = yes with `CONFLICT` in the
   policy text. The Gramercy (White Plains): Trulia says no dogs, Apartment List says dogs allowed, own site blocked:
   `unconfirmed:dogs`, rows kept. River Tides and 70 Pier: `unconfirmed`.
3. **Weight limit exists but the number is not published**: 360 Huguenot, The Leaf, Motif (Trulia says 75 lb),
   Continuum, The Sheldon. Flagged in `notes`.
4. **Unit floor** is filled on 277 of 810 rows (SightMap floor labels, or unit numbers where the numbering was checked).
   Rows without a floor cannot be screened for ground-floor units.
5. **Price basis.** Trulia and Apartment List prices are the listed figures; whether they are net-effective is stated only
   where the page says so (`concession_text`, filled on 328 rows, verbatim). SightMap rows carry base rent plus the total
   with required monthly fees in `price_basis` and the fee list in `other_monthly_fees_json`.
6. **Parking fee, pool, doorman, year built, manager** are recorded where a page shows them (parking type on 609 rows,
   pet rent on 198). "Indoor pool" was not stated on any page read; pools seen are rooftop or outdoor and are worded so.
7. **Leads not followed one by one**: about 250 Zumper leads and 70 Apartment List leads are single units in small
   buildings or houses (no building page). Those with an Apartment List property page were read (rows written, mostly
   `unconfirmed:dogs`); the Zumper single-unit leads were not re-read in this pass.
8. Scarsdale, Hastings-on-Hudson and Piermont produced no building record: the three sources list only houses,
   small walk-ups or condominium units there.
9. Coordinates: 4 `BUILDING_FAILS` rows have no lat/lon (the geocoder did not match the address).

Strict screen of the rows (dogs yes, elevator yes, rent ≤ $3,000, dated now to Dec 15, no failing weight limit, not a
ground-floor unit where the floor is known, dog size not in doubt): 288 unit rows in 59 buildings.
