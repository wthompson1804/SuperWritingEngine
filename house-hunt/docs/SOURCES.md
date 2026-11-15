# Data source access test (2026-11-15)

Low-volume access test for the Jamaica / Forest Hills (Queens) and Stamford, CT apartment search. Every row below is something observed on 2026-11-15. No data was collected at scale.

**Method.** `scripts/source_tests/probe.py` fetched each host's `/robots.txt` once. It checked each test path against the `User-agent: *` group, using longest match with Allow winning ties. A path was fetched only if allowed. Plain fetches used the UA `house-hunt-research/0.1 (personal non-commercial research; low volume)`, at most 1 request per 2.1 s per host, and bodies were capped at 2 MB.

**Browser tests.** `scripts/source_tests/browser.py` with `render.js` ran headless Google Chrome through **Node** Playwright 1.63. Python Playwright is not installed here, and nothing was installed. Browser tests ran only on robots-allowed URLs that returned a JavaScript shell to a plain fetch. They never ran on a URL that had returned a bot wall.

**Where the evidence is.** Raw responses are in `raw/source_tests/<host>/`: `robots.txt`, `<test>.html/.json/.xml/.bin`, and `<test>.browser.html`. Logs are in `raw/source_tests/_robots.jsonl`, `_results.jsonl` and `_browser.jsonl`. The target lists are `scripts/source_tests/targets_*.json`.

**How robots.txt was handled.**
- A robots.txt that returned 401, 403 or 429, or an HTML bot wall, was recorded as **blocked**, and nothing else on that host was requested.
- A 404, or SPA HTML with no wall, was treated as "no rules".
- A network error or 5xx was treated as **unreachable** (full disallow).
- Two documented machine APIs whose robots.txt path did not return a robots file were tested anyway with 1 to 3 calls: Census and EIA. This is marked "override" below.

**Legend for "method that works":**
- API: documented JSON/REST endpoint.
- bulk file: downloadable CSV/ZIP/PDF.
- sitemap: XML sitemap usable for URL discovery.
- plain fetch: server-rendered HTML contains the data.
- browser: data only appears after JavaScript.
- none: blocked, disallowed or login.

## 1. Listing sites

| source | what we need from it | method that works | robots.txt summary for the paths we need | auth or key needed | test URL(s) and HTTP result | notes |
|---|---|---|---|---|---|---|
| StreetEasy | NYC rental listings, building pages | none | `*`: `/for-rent/...` allowed; `/rental/*` (listing detail) and `*/rentals/rss` **disallowed**; `/building/*` allowed except `/documents`, `/floorplans` | n/a | `streeteasy.com/for-rent/forest-hills` → **403 PerimeterX "Press & Hold" CAPTCHA**. `/sitemap.xml` → 404. `/neighborhoods/sitemap_index.xml` → 200 (574 B) | Blocked by bot wall on the first request. Listing detail pages are robots-disallowed anyway. |
| RentHop | NYC listings | none | robots.txt itself → **403 Cloudflare** | n/a | nothing else requested | Blocked at robots.txt. |
| Apartment List | listings and city rent pages | plain fetch | `*`: `Allow: /`; only login, signup and shortlist paths disallowed. Sitemap at `/sitemap.xml` | none | `/ny/forest-hills` → 200 but a soft 404 (the browser shows "404: This page could not be found"). `/ny/queens` → 200, "480 Apartments for Rent in Queens, NY". `/ct/stamford` → 200, "585 Apartments…". `/sitemap.xml` → 200 | No Forest Hills neighborhood page exists; city and borough pages do. Prices are in server HTML and in JSON-LD (`Product` / `AggregateOffer`; 40 price fields on the Stamford page). The page also carries the monthly rent-report median in HTML ("median rent … $2,656" for Stamford). |
| Apartments.com | listings | none | robots.txt itself → **403 Akamai** | n/a | nothing else requested | Blocked at robots.txt. |
| Zillow | rentals search, building pages | plain fetch (search and `/b/` building pages only) | `*`: long allow/deny list; `/<area>/rentals/` and `/b/...` matched no disallow; `/rentals/` (root) disallowed; `/homedetails/` not disallowed. `Crawl-delay: 1` for `*`. There is a separate group for Claude-User / ClaudeBot / Claude-SearchBot (same result for these paths) | none | `/forest-hills-queens-new-york-ny/rentals/` → 200, "88 Rentals", 646 KB, JSON-LD `ItemList`/`Offer`/`Apartment` (84 price fields), `__NEXT_DATA__`, prices in card HTML. `/b/104-40-queens-blvd-forest-hills-ny-CgH9Z2/` → 200, prices in HTML ("1 bed $3,389+") and JSON-LD `ApartmentComplex`. `/homedetails/...2074816545_zpid/` → **403 PerimeterX CAPTCHA** | Search and building pages worked; unit detail pages hit a bot wall. The robots.txt comment says use is governed by the Zillow Terms of Use (not reviewed). Treat it as fragile and ToS-sensitive. |
| HotPads (Zillow) | listings | sitemap only | `*`: `/api/`, `/node/...api`, `/mapdata/`, `?lat=`/`?lon=`/`?z=` disallowed; search paths allowed. Sitemaps: building, multi-family and rentals indexes | none | `/forest-hills-new-york-ny/apartments-for-rent` → 404 (wrong slug). `/11375/apartments-for-rent` → 200, but a JS shell with no listings or prices in HTML. Browser on the same URL → **403 PerimeterX "Press & Hold"**. `/sitemap-building-index.xml` → 200 | Listing data needs JS, and the browser gets a bot wall, so treat it as blocked. Sitemaps are fetchable. Its robots.txt says use is governed by the Zillow Terms of Use. |
| Trulia | listings | plain fetch | `*`: search paths not disallowed (`/rss2/`, `/nearby/`, `/account/` and others are disallowed) | none | `/for_rent/Forest_Hills,NY/` → 200, but "doesn't match any homes" (wrong slug). `/for_rent/11375_zip/` → 200, "80 Rentals", 1.1 MB, JSON-LD `RealEstateListing` (43 price fields), `__NEXT_DATA__`, prices in HTML (`data-testid="property-price"`) | ZIP-code URLs work. Detail pages were not tested. |
| Craigslist | by-owner and no-fee listings | plain fetch (HTML) | newyork.craigslist.org and www.craigslist.org `*`: only `/reply`, `/fb/`, `/suggest`, `/flag`, `/mf`, `/mailflag`, `/eaf` (and `/sitemap/` on newyork) disallowed. Posting sitemaps are listed on www | none | `newyork.craigslist.org/search/que/apa?query=forest hills` → 200 after a redirect to `www.craigslist.org/search/subarea/que?cat=apa&query=forest hills`; prices in plain HTML (`<div class="price">`) plus JSON-LD `Apartment`. `www.craigslist.org/view/d/…` → 200 (price in title and HTML). **RSS `&format=rss` → 403 "Your request has been blocked"** on both hosts | HTML search and detail pages work. RSS is blocked even though robots.txt does not disallow it. |
| Realtor.com | rentals | none | `*`: `/apartments/<area>` not disallowed (pagination, `/*-rentals` and pet-friendly variants are disallowed). The robots.txt LEGAL NOTICE says scraping is unauthorized without written permission | n/a | `/apartments/Forest-Hills_Queens_NY` → **429 bot page** ("This is taking longer than usual… contact unblockrequest@realtor.com") | Blocked, and the robots.txt notice forbids scraping. |
| Rent.com | listings | none | robots.txt → **429, redirected to `ratelimited.rent.com`** | n/a | `/new-york/forest-hills-apartments` → **429 "Are You a Robot?"** | Blocked. |
| Zumper | listings, building pages | plain fetch | `*`: `/api`, `/json`, `/listing-feed`, `/map`, `?box=`, `?bedrooms=`, `?listingId=` and others disallowed; `/apartments-for-rent/<city>` and `/apartment-buildings/<id>/<slug>` allowed | none | `/apartments-for-rent/forest-hills-ny` → 200 (85 KB; a few prices plus `dilBuildings` links). `/apartments-for-rent/stamford-ct` → 200, "337 Rentals", 297 prices. `/apartment-buildings/67606/71st-rd-forest-hills-ny` → 200, prices in HTML ("$2,696–$2,829") | Prices are in card HTML, JSON-LD and a `__PRELOADED_STATE__`-style JSON blob. The listing JSON exposes `feed_name` (for example `"entrata"`), which hints at the property-management software. |
| PadMapper (Zumper) | listings | browser | `*`: `/api`, `?box=`, `&box=` disallowed; `/apartments/<city>` allowed | none | Plain fetch of `/apartments/forest-hills-ny` → 200, a JS shell with no listings. Browser → 200 with 24 prices, but the page redirects itself to `/apartments/new-york-ny?box=…` and calls `/api/t/1/...` | The rendered page ends up on a `?box=` URL that robots.txt disallows, and it uses disallowed `/api/` calls. Not a clean source. Use Zumper (same company) instead. |

## 2. Management and platform sites

| source | what we need from it | method that works | robots.txt summary for the paths we need | auth or key needed | test URL(s) and HTTP result | notes |
|---|---|---|---|---|---|---|
| AvalonBay (avaloncommunities.com) | communities, unit prices | plain fetch (embedded JSON) | `*`: only `*/contact-us`, `*/reset-password` and online application paths disallowed | none | `/sitemap.xml` → 200 (index of 3). `/sitemap-communities.xml` and `/sitemap-markets.xml` → 200 but **empty (71 B)**. `/connecticut/stamford-apartments/` → 404. `/new-york/nyc-metro-apartments` → 200, 990 KB | Unit-level prices are in an embedded JSON (`Fusion.globalContent`, Arc XP) in plain HTML: `"prices":{"price":1945,"totalPrice":2003…}`, `leaseTerm`, and about 940 price hits. The sitemaps are empty, so discover URLs from market pages. |
| Fairfield Properties | Long Island and Queens communities | plain fetch | `*`: `Disallow:` (nothing disallowed). The www host redirects to the apex | none | `fairfieldproperties.com/wp-sitemap.xml` (WordPress) → 200. `/fairfield-at-far-rockaway/` → 200 with "Studio - from $2,195/mo." in plain HTML and `listing-detail/?lid=` links | Starting prices are in plain HTML. The tenant portal is on securecafe3.com (Yardi). |
| Greystar | property pages, prices | sitemap + browser | `*`: `Allow: *`; `/api/*` and `/example-pages/*` disallowed. Sitemaps `sitemap-pdp.xml` and others | none | `/sitemap.xml` → 200. `/sitemap-pdp.xml` → 200 (676 KB; includes `/harbor-landing-stamford-ct/p_20829`). `/homes-to-rent/us/ct/stamford` → 404. `/harbor-landing-stamford-ct/p_20829` plain → 200 (790 KB) with **no prices in HTML**; browser → 58 prices (for example $2,489) | Prices appear only after JS. Discover URLs from sitemap-pdp. |
| Equity Residential | NYC-area property prices | none | `*`: only `/roommates/*`, `/guestcard` disallowed | n/a | `/sitemap.xml` and `/new-york-city-apartments` → **403 Cloudflare "Just a moment…"** | Blocked by a Cloudflare challenge. |
| Bozzuto | property and floor-plan prices | browser (data via robots-disallowed API) | `*`: `Allow: /`; **`/api/` and `/search` disallowed**; `Content-Signal: ai-train=no, search=yes, ai-input=yes` | none | `/sitemap.xml` and `/sitemap/properties_sitemap.xml` → 200. `/apartments-for-rent/ny/new-york/88-leonard` → 200 with no prices (plain or browser). `/apartments-for-rent/ct/stamford/stamford-corners/floor-plans` plain → 200 with no prices; browser → 3 prices ($2,883…), loaded from `/api/properties/stamford-corners/floorplans` | Prices come only from `/api/`, which robots.txt disallows. A scripted harvest should not call it. Use the browser sparingly, or get prices elsewhere. |
| Veris Residential (Roseland) | NJ/NY properties | plain fetch + sitemap | `*`: `Disallow:` (nothing). A `Crawl-delay: 10` line appears before the first User-agent line. The www host redirects to the apex | none | `/sitemap.xml` → `sitemap_index.xml` 200. `/properties-sitemap.xml` → 200 (3.9 KB). `/community-sitemap.xml` → redirected to the home page. Home → 200 | The prices found on the home page are search-filter options ($2,300, $2,800…), not units. Property pages were not tested. Honor the 10 s crawl delay. |
| Kushner | NJ/NY properties | plain fetch + sitemap (directory only) | `*`: only `/wp-admin/` disallowed; **`Crawl-delay: 10`** | none | `kushner.com/sitemaps.xml` → 200. `/page-sitemap1.xml` → 200. Home → 200. `/properties/` → 200 with no prices | A corporate directory; buildings have their own sites. Our 2.1 s spacing was shorter than the 10 s crawl delay on these 4 requests, so future runs must use at least 10 s. |
| BNE Real Estate | NJ/NY communities | plain fetch (directory only) | bnerealestate.com robots.txt → 404 (no rules). lifebybne.com → 404 (no rules) | none | `bnerealestate.com/sitemap.xml` → 404. Home → 200. `lifebybne.com/communities/` → 200 with links to per-building sites (`1harrison.com`, `rentatthegreen.com`, …) and a `*.securecafe.com` (Yardi) leasing link | Per-building sites are separate. One of them, `1harrison.com/floorplans` and `/sitemap.xml`, → **403 Cloudflare**. |
| Urby | Stamford building | none | `*`: `Disallow:` (nothing) | n/a | `/sitemap.xml` → 200 (75 KB). `/stamford` → redirected to `thepointstamford.com` → **403 Cloudflare challenge** | The Stamford property site is blocked. |
| RentCafe (rentcafe.com, Yardi) | aggregated property pages | none | `*`: 466 rules, including `Disallow: *floorplans.aspx`, `/*FloorPlanID` and `/apartmentsforrent/searchlisting.aspx` | n/a | `/sitemap.xml` and `/apartments-for-rent/us/ct/stamford/` → **403 Cloudflare "Attention Required!" CAPTCHA** | Blocked. A RentCafe-style per-building site (1harrison.com) was also behind Cloudflare. |
| Entrata-hosted site (`sunrisemanagementandconsulting.prospectportal.com`) | property pages | none | robots.txt → **403 Cloudflare** | n/a | nothing else requested | Blocked at robots.txt. Zumper's feed shows Entrata-fed buildings in Stamford, but no Entrata-hosted Stamford or Queens site was identified. |

**Where unit prices live:**
- Plain HTML: Zillow, Trulia, Zumper, Craigslist, Apartment List, Fairfield.
- Embedded JSON in the HTML: AvalonBay (`Fusion.globalContent`).
- JavaScript only: Greystar.
- Robots-disallowed API only: Bozzuto, PadMapper.

## 3. Reviews and voices

| source | what we need from it | method that works | robots.txt summary for the paths we need | auth or key needed | test URL(s) and HTTP result | notes |
|---|---|---|---|---|---|---|
| Openigloo | NYC landlord and building reviews | plain fetch + sitemap | `*`: `Allow: /`; `/api`, `/_nuxt`, `/internal` disallowed. It has explicit Claude-User/ClaudeBot groups with the same rules | none | Home → 200. `/sitemap.xml` → 200 (index of verified, non-verified and apartments sitemaps). `/sitemap_verified__001.xml` → 200 (739 KB of `/unit/nyc/...` URLs). `/unit/nyc/1040158-…-913/...` → 200, 608 KB, links to `/building/nyc/<id>/...` | Review text and prices (22) are in plain HTML. |
| ApartmentRatings | reviews | none | robots.txt → **403 Cloudflare** | n/a | nothing else requested | Blocked. |
| Yelp | reviews | none | `*`: **`Disallow: /`**. The comments say automated access is prohibited without permission | n/a | `/search?...` not fetched (**disallowed by robots.txt**) | Off limits. |
| Google Maps | reviews, places | none (not fetched) | `*`: `/maps/` disallowed with specific allows (`/maps/@`, `/maps/?q=` and others); `/maps/search/...` matched an allow rule | n/a | robots.txt only, as instructed | Not tested. Use the official Places API (key and billing) if needed. |
| Niche | neighborhood grades | plain fetch | `*`: our path allowed. **ClaudeBot and Claude-Web groups are `Disallow: /`** (the comment says the block is for AI training crawlers) | none | `/places-to-live/n/forest-hills-new-york-city-ny/` → 200, 341 KB; "Overall Niche Grade" and "Median Rent" (`"value":2238`) in HTML and embedded JSON | Works for `*`. The AI-crawler block does not name our UA, but note the site's intent. |
| City-Data forum | resident discussion | plain fetch | `*`: `/forum/search.php*` and `/forum/members` disallowed; forum and thread pages allowed. **ClaudeBot is fully disallowed** | none | `/forum/new-york-city/` → 200. A thread page → 200. `/neighborhood/Forest-Hills-Queens-NY.html` and `...-New-York-NY.html` → 404 (wrong slugs) | Forum search is disallowed, so threads must be found by browsing forum index pages. |
| Reddit (old. and www.) | resident discussion | none | **Both hosts: `User-agent: *` / `Disallow: /`**. The comments point to the Reddit Public Content Policy and r/reddit4researchers | n/a | `old.reddit.com/r/Queens/search.json`, `old.reddit.com/r/Queens/search`, `www.reddit.com/r/Queens/search.json` and `/top.json` were not fetched (**disallowed by robots.txt**) | The `.json` endpoints and HTML are off limits for `*`. The only route is Reddit's official API under its terms (not tested). |
| Nextdoor | neighborhood posts | none | `*`: **`Disallow: /`** (only named search bots get path-level rules) | n/a | `/neighborhood/foresthills--queens--ny/` not fetched (**disallowed**) | Off limits. |
| YouTube | "living in Forest Hills" videos | none | `*`: `/results` **disallowed**; `/watch` not disallowed | n/a | `/results?search_query=…` not fetched (disallowed). `/watch?v=pXaTxGgsc3w` ("Inside NYC's Most Interesting Looking Neighborhood", found through web search) → **429, redirected to `google.com/sorry` CAPTCHA** | Blocked on the first watch-page request. The YouTube Data API (key) was not tested. |

## 4. Records, data and costs

| source | what we need from it | method that works | robots.txt summary for the paths we need | auth or key needed | test URL(s) and HTTP result | notes |
|---|---|---|---|---|---|---|
| NYC Open Data, NYPD complaints current year `5uac-w243` | precinct crime | API (Socrata SODA) | data.cityofnewyork.us: `/resource/` not disallowed | none (an app token is optional) | `/resource/5uac-w243.json?$limit=3&addr_pct_cd=112` → 200, 3 rows | Last-Modified 2026-11-05. |
| NYC Open Data, NYPD historic `qgea-i56i` | multi-year crime | API | same | none | `/resource/qgea-i56i.json?$limit=3&addr_pct_cd=112` → 200, 3 rows | Last-Modified 2026-04-28. |
| NYC Open Data, HPD violations `wvxf-dwi5` | building condition | API | same | none | `/resource/wvxf-dwi5.json?$limit=3&zip=11375` → 200, 3 rows | Last-Modified 2026-11-14. |
| NYC Open Data, 311 `erm2-nwe9` | noise and heat complaints | API | same | none | `/resource/erm2-nwe9.json?$limit=3&incident_zip=11375` → 200, 3 rows | Last-Modified 2026-11-15. |
| NYC Open Data, DOB complaints `eabe-havv` | building complaints | API | same | none | `/resource/eabe-havv.json?$limit=3` → 200, 3 rows (fields include `zip_code`, `bin`) | Last-Modified 2026-11-14. |
| NYPD CompStat | precinct weekly stats | bulk file (PDF) | www.nyc.gov: 1 rule, not affecting these paths | none | `/site/nypd/stats/crime-statistics/compstat.page` → 200 (links to CompStat 2.0, no PDF links in its HTML). `/assets/nypd/downloads/pdf/crime_statistics/cs-en-us-112pct.pdf` → 200, application/pdf, 159 KB. `compstat.nypdonline.org/` → 200 (JS app; no robots rules) | The precinct PDF URL pattern works (112 = Forest Hills). CompStat 2.0 is an interactive app. |
| data.ny.gov (DCJS) | index crimes by county and agency | API | not disallowed | none | Socrata catalog `api.us.socrata.com/api/catalog/v1?domains=data.ny.gov&q=index crimes county agency` → 200. **Dataset id `ca8h-8gjq`** ("Index Crimes by County and Agency: Beginning 1990"). `/api/views/ca8h-8gjq.json` → 200. `/resource/ca8h-8gjq.json?$limit=3&county=Queens` → 200 (fields include agency, year, total_index_crimes, violent…) | Related rates dataset: `34dd-6g2j`. Last-Modified 2025-11-25. |
| NJ State Police UCR | NJ municipal crime | plain fetch (report pages) | www.nj.gov: 12 rules, not affecting `/njsp/ucr/` | none | `www.nj.gov/njsp/ucr/` → 200. `/njsp/ucr/crime-reports.shtml` → 200. `www.njsp.gov/ucr/` → redirected to `njsp.njoag.gov/ucr-forms/` → 200 | Pages load an Incapsula (Imperva) script but served real content. The report files themselves were not tested. |
| Connecticut crime data | town crime | partial (catalog API; press-release PDFs) | portal.ct.gov allows; data.ct.gov has `Crawl-delay: 1`; **ctdata.org robots.txt → 403** | none | data.ct.gov catalog search `q=crime` → 200; found `7t99-gbjg` "CT Crime Incidents: NIBRS" (updated 2023-05-24). `/resource/7t99-gbjg.json?$limit=3` → **403 "no row or column access to non-tabular tables"** (it is a link or file record, not a table). `portal.ct.gov/despp` → 200 with links to "Crime in CT" press-release PDFs | No tabular CT town-level crime API was found. The FBI CDE covers CT agencies (below). ctdata.org is blocked. |
| FBI Crime Data Explorer API | agency crime (NY, NJ, CT) | API | api.usa.gov robots.txt → 404 (no rules) | `API_KEY=DEMO_KEY` works (rate-limited; a personal api.data.gov key is free) | `/crime/fbi/cde/agency/byStateAbbr/CT?API_KEY=DEMO_KEY` → 200 (agency list; Stamford PD ORI `CT0013500`). `/crime/fbi/cde/summarized/agency/CT0013500/V?from=01-2023&to=12-2023&API_KEY=DEMO_KEY` → 200, monthly rates for Stamford PD, CT and US | Works with DEMO_KEY. |
| Census API (api.census.gov) | ACS rents and income by tract | API, with a key only (metadata without a key) | robots.txt → 200 HTML "Request Rejected" page (WAF); override applied | **Key required.** No key → redirected to `missing_key.html`. `key=DEMO_KEY` → redirected to `invalid_key.html` | `/data/2023/acs/acs5?get=NAME,B25064_001E&for=county:081&in=state:36` → missing_key. Same with `&key=DEMO_KEY` → invalid_key. `/data/2023/acs/acs5.json` (metadata) → 200 JSON, no key | Data queries need a free Census key; DEMO_KEY is rejected. The metadata endpoint works without a key. |
| Census ACS table-based summary files (www2.census.gov) | bulk ACS tables | bulk file | www2.census.gov robots.txt: no rules for `*` | none | `/programs-surveys/acs/summary_file/2023/table-based-SF/` → 200, Apache directory listing (`data/` 2024-12-12, `documentation/`) | A no-key alternative to the API. |
| HUD Small Area FMR (huduser.gov) | SAFMR by ZIP | none (scripted) | robots.txt → **202 with an empty body** (no rules) | n/a | `/portal/datasets/fmr/smallarea/index.html` → **202, empty body**. HEAD `/portal/datasets/fmr/fmr2026/fy2026_safmrs.xlsx` → **202, empty** | Every request returns 202 with an empty body, which looks like a JavaScript bot challenge. A browser was not attempted, to avoid bypassing it. Download manually, or use the HUD API (token required; not tested). |
| Zillow Research CSVs (files.zillowstatic.com) | ZORI rent index by ZIP | bulk file | files.zillowstatic.com: no rules for `*` (comment: governed by Zillow ToU). `www.zillow.com/research/` explicitly allowed | none | `zillow.com/research/data/` → 200 (10 CSV links). `public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv` → 200, Content-Length 10.1 MB (truncated to 2 MB locally), Last-Modified 2026-10-16; columns RegionName (ZIP)… and monthly values from 2015-01 | Direct CSV with no key. 11375 is present. |
| Apartment List rent estimates | city and county rent estimates | page only (CSV URL not found) | `/research/*` allowed | none | `/research/category/data-rent-estimates` → 200 (plain and browser). `/research/national-rent-data` → 200 (says "data download options are available on our data download page") | No `.csv` or `.xlsx` link appeared in plain or rendered HTML on 2026-11-15; downloads seem to be behind an interactive control. City-page HTML carries the median rent (see section 1). |
| EPA National Walkability Index | walkability by block group | bulk file | www.epa.gov allows the page; edg.epa.gov robots.txt → 404 (no rules); **geodata.epa.gov: `Disallow: /arcgis/`** | none | `epa.gov/smartgrowth/smart-location-mapping` → 200 (links to the WalkabilityIndex.zip, SLD v3 zip and MapServer). HEAD `edg.epa.gov/EPADataCommons/public/OA/WalkabilityIndex.zip` → 200, 425 MB, Last-Modified 2021-06-08. `geodata.epa.gov/arcgis/rest/services/OA/WalkabilityIndex/MapServer` → not fetched (**disallowed**) | Use the zip. The REST service is robots-disallowed. |
| FEMA NFHL (hazards.fema.gov) | flood zone by point | none (on this host) | **`*`: `Disallow: /*?*` and `Disallow: /arcgis`** | n/a | `/arcgis/rest/services/public/NFHL/MapServer?f=json` and `/gis/nfhl/rest/services/...?f=json` not fetched (**disallowed by robots.txt**) | Point queries need a query string, which robots.txt disallows. Look for another NFHL distribution (bulk download or another host); not tested. |
| FCC National Broadband Map | broadband availability | none observed | robots.txt returns the SPA HTML (no rules) | **API: 401 without credentials** | `/data-download` plain → 200 (SPA shell, no file links). `/api/public/map/listAsOfDates` → **401 `{"message":"Unauthorized"}`**. Browser on `/data-download/nationwide-data` → **403 Akamai "Access Denied"** | The public API needs account credentials. The bulk-download page was blocked for headless Chrome. |
| BTS National Transportation Noise Map | road and aviation noise | tiles only (no point query) | geo.dot.gov robots.txt → 404 (no rules) | none | `geo.dot.gov/server/rest/services?f=json` → 200. `/Hosted/NTAD_Noise_2020_CONUS_Aviation_Road/MapServer?f=json` → 200 (`capabilities: "TilesOnly,Tilemap"`). `/identify?...` at Forest Hills → 200 with `{"error":{"code":500,"message":"Error performing identify"}}` | A cached raster tile service, so attributes cannot be queried by point. Noise must be read from tile pixels, or from BTS bulk rasters (not tested). |
| EIA API | residential electricity price | API | api.eia.gov robots.txt path → 403 JSON `API_KEY_MISSING` (no robots file; override applied) | `api_key=DEMO_KEY` works; a free key is available | `/v2/electricity/retail-sales/data/?api_key=DEMO_KEY&...stateid=NY&sectorid=RES...` → 200; latest NY residential price 2026-08 = 28.65 ¢/kWh | DEMO_KEY works. |
| Overpass API | OSM amenities | none observed | overpass-api.de robots.txt → **connection reset** (unreachable; the proxy logs `ws_closed_mid_exchange`). overpass.kumi.systems and overpass.private.coffee robots.txt → 404 (no rules) | none | kumi and private.coffee `/api/status` and a tiny POST `/api/interpreter` (one bbox of about 150 m, `out 5`) → **read timeout at 40 s** on both | None of the three answered on 2026-11-15. Retry later, or use a Geofabrik extract. |
| OSRM public demo | drive times | API | router.project-osrm.org robots.txt → 400 (treated as no rules) | none | `/route/v1/driving/-73.8448,40.7181;-73.8073,40.7023?overview=false` → 200 JSON | Works. The demo server is for light use only. |
| Walk Score | walk and transit scores | none (not tested) | www.walkscore.com robots.txt → **504**, then **408** on retry (unreachable). api.walkscore.com robots.txt → 404 | API key (`wsapikey`) | robots.txt only, as instructed | Needs a key. The website's robots.txt was unreachable. |
| MTA (new.mta.info) | fares, bridge and tunnel tolls | none (scripted) | robots.txt → **403 Akamai "Access Denied"** | n/a | `/fares` and `/fares-and-tolls/...` not requested | Blocked at robots.txt. Enter fares by hand. |
| Port Authority NY/NJ | bridge and tunnel tolls | browser | panynj.gov: path allowed (rule length 16, allow) | none | `/bridges-tunnels/en/tolls.html` plain → 200 but 2.6 KB with no rates. Browser → 200 with toll rates in text ($14.79, $16.79, $19.55…) | Rates appear only after JS. |
| NJ Turnpike Authority | toll calculator | plain fetch (page); calculator not tested | www.njta.gov: 2 rules, path allowed | none | `/toll-calculator/` → 404. `/travel-resources/toll-calculator/` → 200 (473 KB) | Toll amounts come from the interactive calculator, which was not exercised. |
| NY Thruway | toll schedules | bulk file (PDF) | `www.thruway.ny.gov` robots.txt → redirected to `http://thruway.ny.gov` → **DNS failure** in this environment. `https://thruway.ny.gov/robots.txt` → 200 (Drupal default rules; paths allowed) | none | `https://thruway.ny.gov/` → 200. `/travelers/toll-schedules` → 200, "Downloadable Toll Schedules", with PDF links (for example `/sites/default/files/2025-07/2024-ny-e-zpass-cpm.pdf`) | Use the apex `https://thruway.ny.gov/`. |

## Off limits

These were not used because they are blocked, disallowed, or need a login or key that we do not have:

- **Bot wall, CAPTCHA or 403:**
  - StreetEasy (PerimeterX)
  - Zillow `/homedetails/` (PerimeterX)
  - HotPads in a browser (PerimeterX)
  - Realtor.com (429 bot page)
  - Rent.com (429 "Are You a Robot?")
  - Craigslist RSS (403 "blocked")
  - Equity Residential, RentCafe, Urby Stamford (thepointstamford.com) and 1harrison.com (Cloudflare)
  - YouTube watch page (google.com/sorry CAPTCHA)
  - FCC data-download in a browser (Akamai)
- **robots.txt itself blocked:**
  - RentHop, Apartments.com, ApartmentRatings and the Entrata prospectportal site (403 Cloudflare or Akamai)
  - ctdata.org (403)
  - MTA new.mta.info (Akamai 403)
  - HUD huduser.gov (202 challenge on every path)
- **Disallowed by robots.txt for `*`:**
  - Reddit, both old. and www., including the `.json` endpoints (`Disallow: /`)
  - Yelp (`Disallow: /`)
  - Nextdoor (`Disallow: /`)
  - YouTube `/results`
  - StreetEasy `/rental/*` detail pages
  - FEMA hazards.fema.gov `/arcgis` and any `?` query
  - EPA geodata `/arcgis/`
  - Bozzuto `/api/` (where its prices live)
  - PadMapper `?box=` and `/api` (where its rendered page goes)
- **Key or login required:**
  - Census API (DEMO_KEY rejected)
  - FCC broadband API (401)
  - Walk Score API (key)
  - HUD API (token; not tested)
  - Google Maps (robots.txt only; use the Places API)
- **Unreachable on 2026-11-15:**
  - Overpass: main host reset; kumi and private.coffee timed out
  - www.walkscore.com robots.txt (504 and 408)
  - www.thruway.ny.gov (redirects to a host that does not resolve; use `https://thruway.ny.gov`)

## Implications for the pipeline

- **Scripted listing harvest.** Zumper, Trulia (ZIP URLs), Craigslist HTML and Apartment List city or borough pages are practical: server-rendered prices, JSON-LD, robots-allowed. Zillow search and `/b/` building pages also work, but detail pages hit PerimeterX and robots.txt cites the Terms of Use, so keep Zillow to occasional manual-scale use.
- **StreetEasy, Apartments.com, RentHop, Realtor.com, Rent.com and HotPads are not available to a script.** Treat any NYC inventory that exists only there as a manual-check step.
- **Craigslist has no RSS** (blocked). Poll the HTML search page at low frequency and parse `div.price` plus JSON-LD.
- **Management sites split three ways:**
  - Fairfield (plain HTML "from $X") and AvalonBay (unit prices in embedded `Fusion.globalContent` JSON) can be fetched directly.
  - Greystar needs a browser; use sitemap-pdp for URL discovery.
  - Bozzuto's prices come only from its robots-disallowed `/api/`, and Equity, RentCafe, Urby and Entrata-hosted sites are behind Cloudflare. For those, use the aggregator copy (for example Zumper's feed) instead.
- **Crawl delays.** Honor per-host crawl delays in the shared fetch helper: Kushner and Veris 10 s, Zillow 1 s, data.ct.gov 1 s. Today's 2.1 s spacing was below Kushner's 10 s for 4 requests. Also re-check robots.txt on the final host after redirects (www to apex, `newyork.` to `www.craigslist`).
- **Records are solid:**
  - NYC Open Data (all 5 datasets), data.ny.gov `ca8h-8gjq`, FBI CDE (DEMO_KEY), EIA (DEMO_KEY), OSRM, Zillow ZORI CSV, the EPA Walkability zip, NYPD precinct PDFs (`cs-en-us-<pct>pct.pdf`) and Thruway PDFs all worked with no key.
  - The Census API needs a real key; until we have one, use the www2 table-based summary files.
- **Gaps that need another route or manual entry:**
  - Flood zones: FEMA REST is robots-disallowed.
  - Broadband: the FCC API needs credentials.
  - Noise: BTS is tile-only, with no point attributes.
  - SAFMR: HUD returns a challenge.
  - MTA fares: Akamai blocks the site.
  - Apartment List rent CSV: no URL found.
  - CT town-level crime as a table: only via FBI CDE.
- **Resident voices:** Openigloo (sitemaps plus plain HTML), City-Data threads (browse; forum search is disallowed) and Niche are usable. Reddit, Nextdoor, Yelp and YouTube are not, unless we use their official APIs under their terms.
- **Overpass was unavailable from here.** Plan for a local OSM extract, for example Geofabrik's New York and Connecticut files, rather than live Overpass queries.
- **AI-specific robots rules.** Several robots.txt files have them: Niche and City-Data fully disallow ClaudeBot; Yelp and Bozzuto have explicit Claude-User rules; Zillow and Openigloo have Claude groups with the same effect as `*` for our paths. We followed the `*` group with our own UA as instructed. Re-check these groups if the pipeline's user agent or operator changes.

## Coordinator addendum (2026-11-15): robots.txt groups that name Claude

The access tests followed the generic `User-agent: *` rules. This pipeline is run by a Claude agent on a
user's behalf, so **rules that name Claude agents (ClaudeBot, Claude-User, Claude-SearchBot, anthropic-ai,
Claude-Web) apply to us and override the generic group.** Effect on the sources:

| Source | Claude-specific rule | Status for this pipeline |
|---|---|---|
| Niche | ClaudeBot and anthropic-ai: `Disallow: /` | **Off limits** |
| City-Data | ClaudeBot and Claude-Web: `Disallow: /` | **Off limits** |
| Yelp | Claude-User and Claude-SearchBot: allowed only `/article` | **Off limits** for reviews |
| Zillow | Claude-User, ClaudeBot and Claude-SearchBot: allow-list of 13 landing paths only (e.g. `/homes/for_rent/$`), no listing or building pages | **Effectively off limits** for inventory. ZORI CSVs on files.zillowstatic.com are unaffected |
| Bozzuto | Claude-User: same as `*` (`/api/` and `/search` disallowed) | Prices are only at `/api/`, so **no prices** |
| Openigloo | Claude-User: allowed except `/api`, `/_nuxt`, `/internal` | Usable for HTML pages |

The test run made about 4 requests to Kushner 2.1 s apart, against its 10 s crawl-delay. Future harvests must honour `Crawl-delay`.

## Coordinator addendum (2026-11-15, evening): Craigslist is off limits for scripts

Craigslist's robots.txt allows the search and posting pages, but its Terms of Use prohibit collecting content
"via robots, spiders, scripts, scrapers, crawlers, or any automated or manual equivalent". Working rule 3 says to
respect terms, so **no automated Craigslist harvest**. The harvest agent stopped after 20 test requests and wrote
0 listings. Search-card counts seen: Queens studio + 1BR ≤ $3,000 with dogs OK, 106 results; Hudson Valley, 63.
Craigslist stays a manual-browsing source: Will or Lamia can paste links, which go through `gates.py` like any other.
`scripts/h_craigslist.py` exists but must not be run.
