# Harvest notes: property-management company sites (`mgmt_*`)

Run: 2026-11-15 (UTC evening). One script and one CSV per company; shared helpers in
`scripts/h_mgmt_common.py` (CSV contract, robots check where Claude-named groups override `*`, crawl-delay,
bot-wall stop, `dog_status`), `scripts/h_mgmt_sightmap.py` (SightMap embed reader) and
`scripts/h_mgmt_render.js` (headless render, used for Russo only). All scripts are idempotent
(`upsert` by `listing_id`, `first_seen` kept) and read from the `raw/mgmt_<company>/` cache; pass `--refresh` to refetch.

**Total: 1,446 rows in 10 CSVs. 865 are numbered units; 581 are floor-plan rows (no unit number).
557 rows have an availability date of now through 2026-12-15.**

## What each company gave

| CSV | Rows | Buildings | Row level | In window | Access | Script |
|---|---|---|---|---|---|---|
| `mgmt_avalon.csv` | 176 | 23 | unit | 136 | plain fetch, embedded JSON | `h_mgmt_avalon.py` |
| `mgmt_greystar.csv` | 512 | 39 | unit | 227 | plain fetch, Next.js flight payload | `h_mgmt_greystar.py` |
| `mgmt_blt.csv` | 113 | 5 | unit | 78 | plain fetch + SightMap | `h_mgmt_blt.py` |
| `mgmt_russo.csv` | 37 | 8 | unit | 23 | headless render of `/floorplans` | `h_mgmt_russo.py` |
| `mgmt_gardenhomes.csv` | 20 | 11 | unit | 0 (no dates published) | plain fetch | `h_mgmt_gardenhomes.py` |
| `mgmt_newport.csv` | 5 | 2 | unit | 4 | plain fetch | `h_mgmt_newport.py` |
| `mgmt_sightmap_sites.csv` | 2 | 1 | unit | 2 | plain fetch + SightMap | `h_mgmt_sightmap_sites.py` |
| `mgmt_fairfield.csv` | 422 | 122 | floor plan | 0 (no dates published) | plain fetch | `h_mgmt_fairfield.py` |
| `mgmt_gardencommunities.csv` | 137 | 71 | floor plan | 68 | plain fetch | `h_mgmt_gardencommunities.py` |
| `mgmt_gdc.csv` | 22 | 8 | floor plan | 19 | plain fetch, 10 s delay | `h_mgmt_gdc.py` |

No CSV (nothing at or under $3,000, or blocked): Windsor (`h_mgmt_windsor.py` runs, 0 rows), Veris, Kushner, BNE,
Mill Creek, Related, Rose, RXR, Rockrose, LeFrak City, and the others listed under "Blocked or empty".

## Gate-field fill rates (share of rows with a value other than blank / unknown)

| CSV | dogs | dog weight limit | elevator | floor | building floors | available date | parking fee | pet rent |
|---|---|---|---|---|---|---|---|---|
| avalon | 100% (all yes) | 100% = `none_stated` (see below) | 3% | 100% | 0% | 100% | 99% | 100% |
| greystar | 18% | 0% | 0% | 100% | 0% | 100% | 94% | 97% |
| blt | 2% | 0% | 4% | 100% | 100% | 100% | 2% | 2% |
| russo | 76% | 0% | 0% | 65% | 0% | 100% | 0% | 0% |
| gardenhomes | 20% | 0% | 35% | 0% | 0% | 0% | 0% | 0% |
| newport | 0% | 0% | 0% | 100% | 0% | 100% | 0% | 0% |
| sightmap_sites | 0% | 0% | 0% | 100% | 100% | 100% | 0% | 0% |
| fairfield | 10% | 4% | 4% | 0% | 0% | 0% | 0% | 0% |
| gardencommunities | 13% | 1% | 15% | 0% | 0% | 50% | 0% | 0% |
| gdc | 9% | 0% | 0% | 0% | 0% | 100% | 0% | 0% |
| **all 1,446 rows** | **25%** (353 yes, 8 no) | **13%** | **4%** (51 yes, 3 no) | **58%** | 8% | **65%** | | |

Read these before using the data:

- **Elevator is almost never stated on these sites** (4%). It is `yes` only where the page text has the word
  "elevator". For Greystar the page gives a building type instead, kept in `notes` as `buildingType=High-Rise`
  (228 rows), `Mid-Rise` (245), `Garden` (23), `Active Adult` (16). For Avalon and Greystar `notes` also carries
  "highest floor among available units"; for BLT and SightMap sites `building_floors` is the highest floor label in
  the SightMap floor list. None of these was converted into `elevator=yes`; that is the gate script's call.
- **Dog weight limit is published by almost nobody.** Avalon's JSON has `maximumPetWeight = 0` for every community
  here, with dogs explicitly welcome and a restricted-breed list; I wrote `none_stated`, not "no limit". The 16
  numeric values are 15 Fairfield rows in three communities (Centereach Gardens 40 lb, Lake Grove 40 lb, Courtyard
  at Coram 70 lb; "$35 per dog" monthly fee is in `dog_policy_text`) and 1 Garden Communities row (Linwood Village,
  "pet friendly if the pet is under 40 lbs"). Greystar, BLT, Russo, GDC and Newport publish no limit.
- **`dogs=yes` is strict**: the page must name dogs as allowed or list a dog amenity (dog run, dog wash, "cats and
  dogs welcome"). "Pet-friendly" alone, or a pet-rent fee alone, stays `unknown` with the wording kept in
  `dog_policy_text`. Greystar: 97% of rows have a monthly pet rent but only 18% name dogs.
- **`listed_rent` is base rent**, lowest advertised lease term, which for Avalon and Greystar is often a 13- to
  22-month term. The 12-month price is in `notes` where the page has it. Required monthly fees are in
  `other_monthly_fees_json` and the total is quoted in `price_basis`; some rows at or under $3,000 base are over
  $3,000 with required fees.
- **Floor-plan rows (Fairfield, Garden Communities, GDC) are not units**: `unit` is blank, `floor` unknown, and the
  price is a "from" price. Fairfield publishes no availability date at all. Their unit lists sit on RentCafe
  (`*.securecafe.com`), which is bot-walled and was not fetched.
- `floor` for Newport and Russo is **derived from the unit number** (904 → 9) and says so in `notes`; Russo units
  with five-digit numbers (VC-30304) are left unknown.

## URL patterns and method

- **AvalonBay**: `/new-york/nyc-metro-apartments` (tri-state market page) plus the Arc sitemap named in robots.txt
  (`/arc/outboundfeeds/avb-sitemap/?outputType=xml…`), taking six-segment NY / NJ / CT URLs: 47 community pages.
  Community page → `Fusion.globalContent.units`, `policies`, `utilities`. Each qualifying unit's own page
  (`…/apartment/<id>`) → `fees` (parking, dog fee, required fees) and per-lease-term prices. 971 units seen.
  The market page also lists 34 Equity Residential buildings that link to equityapartments.com (Cloudflare): skipped.
  No Avalon community in Queens, Long Island or Westchester had a studio or 1BR at or under $3,000 except
  Avalon Rockville Centre (1) and Avalon Yonkers (8). No Connecticut community pages exist in the sitemap.
- **Greystar**: `sitemap-pdp.xml`, URLs ending `-ny|-nj|-ct|-pa/p_<id>`: 197 pages, 77 outside the grid.
  **Correction to `docs/SOURCES.md`: no browser is needed.** The unit table is in the plain HTML inside the
  `self.__next_f.push` chunks (`property`, `propertyUnits`, `fees`). The earlier test searched for "$2,489"-style
  strings; the payload stores bare numbers. No `/api/` call is made. 1,764 units seen.
- **BLT** (harborpt.com redirects to bltliveworkplay.com): `/apartments/<city>/<community>/` for policy text,
  `/availability/` for the SightMap embed. 7 communities with an embed; 5 pages without one
  (beaconjc, north-seven, oneglover, harbor-point, penthouse-suites are hub or marketing pages).
  Only the Allure page carries a written pet / parking / fee policy.
- **SightMap** (`sightmap.com/embed/<id>` → `window.__APP_CONFIG__` → `/app/api/v1/<key>/sightmaps/<id>`):
  sightmap.com robots.txt disallows only `/manage` and `/auth`. This is the JSON the embed itself loads.
- **Russo**: building sites found from `russodevelopment.com/property-sitemap.xml` (17 sites). Each `/floorplans`
  page was rendered headless and the unit feed the page itself requests (`yardi.nwgapi.com/units2.php`, a host
  with no robots.txt) was saved from the browser. 9 sites gave a feed. No feed: kingslandmeadowlands,
  vermellahackettstown, vermellaunion, waldwickstation, revbyvermella, theraye (different page layout, not pursued).
- **Garden Communities**: `/sitemap.xml` → 101 `/Properties/<state>/<county>/<name>.aspx` pages, 94 with floor plans.
- **Fairfield**: `/wp-sitemap-posts-page-1.xml` → 264 pages, 167 with "Apartment Styles"; each style's
  `listing-detail/?lid=N` page was fetched and the price re-read there.
- **GDC**: gdcrentals.com, 13 community pages, 10 s between requests.
- **Garden Homes Management**: `/apartments/` (one page lists every available unit) plus `/Property?pid=N`.
- **Newport (LeFrak)**: `/apartments-jersey-city-for-rent/` (250 units in plain HTML) plus each unit's residence page.
- **Windsor**: `/properties/<slug>/floorplans/` embeds the unit list as JSON in plain HTML. Lowest studio or 1BR base
  rent: Windsor at Mariners $3,167, Liberty House $3,815, Warren at York $3,833, The Ashley $4,738, The Aldyn $7,166.

## Blocked or empty

| Company | Result |
|---|---|
| **Veris Residential** | Property pages load (10 s crawl-delay honoured), but units come from `wp-admin/admin-ajax.php`, which returned **HTTP 429 with a Cloudflare "Just a moment…" challenge** in the browser. Stopped. No prices. Its FAQ says dogs "of all breeds and sizes" are welcome, which is useful if prices come from another source. Only 9 NJ properties (Jersey City, Port Imperial). |
| **BNE** (lifebybne.com) | All 22 per-building sites tried returned **403** (RentCafe-hosted, Cloudflare). |
| **Mill Creek (Modera)** | 10 NJ / NY building sites found; all **403** on robots.txt or home. |
| **Value Companies** | robots.txt **403**. |
| **Equity Residential** | Cloudflare, as already recorded. 34 buildings visible only as cards on Avalon's page (not recorded). |
| **Bozzuto** | Not touched (prices only at robots-disallowed `/api/`). |
| **Kushner** | Directory only; property list is script-loaded at a 10 s crawl-delay. Not pursued. |
| **Related Rentals** | Reachable; Manhattan only. Not harvested (no unit under the cap expected; this was not verified unit by unit). |
| **Rose Associates** | 97 building sites; of 48 checked, 9 walled, 3 had a SightMap embed and all 3 are outside the grid (Albany, Saratoga). The Mill Greenwich lists from $3,970. Not harvested. |
| **RXR, Ironstate, TF Cornerstone** | Listings are script-loaded; not pursued. |
| **Rockrose** | Reachable; lowest listed price $3,431. Nothing to record. |
| **LeFrak City (Queens)** | Rendered once: 4 units available, all 2BR or 3BR. Nothing to record. |
| **UDR** | Manhattan only. Not harvested. |
| **Toll Brothers Apartment Living, Kamson, Wilder Balter, Zara Realty** | Connection failed at robots.txt (reset or DNS). |
| **AMLI, Spinnaker, Ginsburg's gdcllc.com, Tritec home, Beechwood** | Corporate sites without rental listings in the grid, or not explored beyond the home page. Tritec's two building sites are in `mgmt_sightmap_sites.csv`. |
| Building sites tried by guessed domain | 9 did not resolve; 5 resolved without a SightMap embed; alluremineola.com returned 403. Listed in `h_mgmt_sightmap_sites_seeds.txt` where they resolved. |

## Oddities

- Windsor's floorplans page makes its own `/wp-json/` calls in a browser, which robots.txt disallows; the harvest
  uses only the plain HTML, where the same unit JSON is embedded. One headless render of the Mariners page was
  made during testing before this was noticed.
- Veris: one headless render of the Liberty Towers page made two admin-ajax calls that drew the 429.
- An early discovery pass (`mgmt_probe` cache) fetched the home pages of two unrelated sites linked from Mill Creek
  pages (ceoaction.com, a photographer's site). It was stopped; nothing was recorded from them.
- BLT community pages embed resident reviews. `elevator=yes` on 4% of BLT rows comes from the word "elevator" in
  that on-page text, including review text; `notes` says so.
- GDC and Garden Communities pages often lack a ZIP; Garden Communities rows without one name the nearest grid ZCTA
  centroid in `notes`. GDC "70 Pier Street" rows have no city parsed.
- Greystar includes income-restricted and "Active Adult" (age-restricted) communities; `notes` carries the building type.
- Avalon "W Squared at Princeton Junction" alone is 53 rows; Princeton-area ZIPs are inside the 2-hour grid.
