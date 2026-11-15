# Evidence pass, batch 6 (2026-11-15, 20:39–20:51 UTC)

33 candidate rows in `data/reference/evidence_batches/batch_6.csv`: 21 New York City buildings and 12 Westchester rows
(White Plains, Yonkers). All 33 were worked. Output: `data/evidence/{live_check,confirm,items,facts}_batch_6.csv`.
Raw pages: `raw/evidence_b6/` (fetch log `_fetch_log.jsonl`, Openigloo parse `_igloo_reviewed.json`).
Scripts: `scripts/ev6_fetch.py` (refetch), `ev6_site.py` (robots check, then fetch), `ev6_igloo.py`, `ev6_trulia_parse.py`,
`ev6_al_parse.py`, `ev6_text.py`, and `ev6_write.py`, which rebuilds all four CSVs from the cached pages with no network.

The dog gate was lowered to 25 lb while this ran (CLAUDE.md). The confirm file records the stated limit, not a pass or fail.

## 1. Live check (40 unit rows)

- 39 live at the stored price, 1 changed (The Altos 410: $2,726 stored, $2,733 now), 0 gone, 0 blocked.
- Nothing repriced above $3,000. Every unit is available on or before 2026-12-15. Parluxe 615 is available on 2026-12-15
  exactly, the last day of the window.
- Sources: Trulia `/home/` pages (14), Zumper listing pages (4) and building pages (2), Apartment List (8 pages),
  Greystar (2 pages, unit table in the page payload), AvalonBay unit pages (3) plus the community page.

### Listings that need a human look before they are shown
- **3215 Netherland Ave 3A (Riverdale), $1,180 1BR, 898 sq ft.** Zumper itself says 57% below the area median. Listed
  2026-11-14, contact phone has a 570 area code, deposit equals one month. The page is live, but the price is not credible
  for the area. Treat as unverified.
- **3925 51st St 3E (Woodside), $1,699 studio** (26% below median, 239 area-code phone) and **53 W 72nd St 4C, $2,750
  studio** (29% below median, listed 13 hours before the check via TurboTenant, 612 area-code phone; a second active listing
  for the address shows $2,800; the text warns the unit may already be rented). Lower confidence than broker listings.
- **1890 Pelham Pkwy S:** the page title says unit 3G, the address line says 4G.
- **Avalon Yonkers 002-2130 ($2,430) is on floor 1** per AvalonBay's own data: fails the no-ground-floor gate.
- **Avalon Yonkers prices are the 14- or 15-month prices.** 12-month prices are $45 to $300 higher (3326: $2,975 for 12
  months against $2,675). Required monthly fees add $182 and dog rent $60, so 3326 is about $2,917 before utilities.
- **Parluxe 615:** Trulia says cats and small dogs allowed; the Zumper copy of the same unit says "No pets allowed."
- **4545 46th St 5F:** "Cats and small dogs (25lbs max)". On the market since 2026-09-27.
- **255 E 61st St 2A:** "four story building", no elevator mentioned anywhere: probably a walk-up.

## 2. Gate facts (141 rows: 83 confirmed, 56 unconfirmed, 2 contradicts)

- Dog weight limit confirmed in pounds for only four buildings: The Altos 40 lb (own site), Apex Hudson Riverfront 75 lb
  (Zumper and Trulia), 4545 46th St 25 lb (listing text), and Avalon Yonkers (no limit stated, breed list only, own site).
- Every Trulia NYC listing in the batch says "Cats, small dogs allowed" with no number. No building had its own leasing
  site that I could find (searches returned only listing sites), so these stay unconfirmed.
- Continuum's own FAQ says "Breed restrictions, weight limits, and pet fees apply" without the number. 25 North Lex, 51 South
  and Alexander Crossing publish no number; the Trulia building pages say "Small, large".
- Floors: confirmed from page data for the Greystar and AvalonBay units and two listings that state the floor. For the rest
  the floor is inferred from the unit number and marked unconfirmed. Unit "21" (720 W 181st) and unit "10" (630 W 163rd)
  give no floor at all.
- Elevator not confirmed: 63-45 Saunders St, 2750 E 12th St, 255 E 61st St, 720 W 181st St, and Continuum (high-rise, but
  no page says "elevator").

## 3. Evidence items (96 rows)

management 28, positive 17, none_found 18, noise 10, car_crime 8, other 8, elevator 4, safety_incident 3.

- Openigloo: found by matching the tax lot (BBL) against the four `sitemap_buildings__reviewed` sitemaps; the page URL is
  `/building/nyc/<BIN>-<BBL>/<slug>`. 13 buildings have a page with reviews or data; the page's JSON-LD carries the five
  most recent reviews, which is what was read. Six more have a BBL-keyed page with 0 reviews; three have no page.
  Three pages carry a different street address on the same tax lot (39-30 52 St for 39-25 51st St; 257 E 61st for 255;
  90 Fort Washington Ave for 630 W 163rd). The source_site column says so.
  Many Openigloo reviews are dated 2021-11-16; that looks like a bulk import date, so treat it as "2021 or earlier".
- Items for Avalon Yonkers are repeated under its four addr_keys, and the Continuum none_found row under its three, because
  the batch lists the same community several times. Count them once.
- Zumper building pages show a handful of Google reviews (Urby, Avalon Yonkers). Zumper's selection is all 5-star, so these
  are weak evidence; they are labelled.

### Most serious
- **720 W 181st St** (Openigloo 2.5/5): no cooking gas for 10 months or more (2025-04 review, same complaint in 2021), cold in
  winter, mice and roaches, "constant package theft" (2025-07), unpermitted construction.
- **630 W 163rd St** (2.2/5): elevator out of service repeatedly (2023-10, 2023-11, 2024-05: "over a week to fix"), leaks,
  ceilings caving in, roaches, unresponsive super. All older than six months.
- **26-02 4th St, View Astoria** (3.4/5): management unreachable, promised gym and roof deck unbuilt after four years, rain
  leaks, daily package theft, garage door left open (2023 to 2025-08). Openigloo counts 71 open violations.
- **1105 30th Rd**: repeated flooding and leaks (2021, 2024), management slow.
- **824 E New York Ave**: mold and roaches from the AC unit, management slow until 311 was involved (2024-09); a 2025-07
  review is positive.
- **Avalon Yonkers garage**: three arrests with 17 cut catalytic converters and a stolen BMW in the garage behind 80
  Alexander St on 2023-03-01 (Yonkers Times, News 12). Old, and the only car-crime item in the batch.
- **The Altos**: months of false fire alarms between midnight and 3 a.m. (News 12, 2023-08-16), when it was Avalon White
  Plains. The article gives no street address; the link to The Altos rests on the site's "Formerly Avalon White Plains".

## 4. Blocked or not done

- `www.51southwhiteplains.com`: HTTP 403 on the home page. `www.apexhudsonriverfront.com`: HTTP 403 on robots.txt. Not read.
- `bbb.org` search and `amny.com` article: disallowed by robots.txt for us. No Better Business Bureau pages were read.
- `news.hamlethub.com` "Yonkers Waterfront Woes" (a resident's post about car vandalism at Apex, per search results): the
  page text is JavaScript-only, so nothing from it is recorded.
- A 2018 fair-housing suit against Urby showed up in search results but no allowed page was read: not recorded.
- No news search was run for nine NYC addresses: 33-25 Junction Blvd, 103-14 Northern Blvd, 63-45 Saunders St, 3215
  Netherland Ave, 3925 51st St, 4545 46th St, 255 E 61st St, 53 W 72nd St and 630 W 163rd St. They were covered only
  through Openigloo and the listing page.
- NYC public records (HPD, DOB, 311) were left to the other agent. Openigloo's violation and litigation counts are stored in
  the facts file as Openigloo's own summary, not as records.
- The Altos' current manager and the date it stopped being an AvalonBay property were not found.
