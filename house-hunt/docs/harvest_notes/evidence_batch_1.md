# Evidence pass, batch 1 (2026-11-15, 20:40–21:05 UTC)

35 rows in `data/reference/evidence_batches/batch_1.csv` (33 distinct buildings: Avalon Boonton and 145 Goldsborough Dr
each appear twice). All 35 were worked. Outputs: `data/evidence/{live_check,confirm,items,facts}_batch_1.csv`.
Scripts: `scripts/ev_b1_*.py` (fetch helper with robots check, Apartment List refresh, Trulia, Zumper, record upsert).
Raw pages: `raw/evidence_b1/` and `raw/apartmentlist/`.

## 1. Live check

- **Every stored unit is still listed at the stored price** (52 units; 67 rows because 12 units were checked on a second
  source). None gone, none repriced, none past Dec 15.
- Checked on the building's or manager's own site as well as the aggregator: Allure (BLT SightMap), EDGE, Royal
  Bloomfield, FIAT House, Walcott (SightMap), Atwater (own availability table), Avalon Boonton and Avalon at Edgewater
  (avaloncommunities.com), Fairways, Brownstones, Walcott (greystar.com). All agree with the aggregator.
- Only Apartment List was reachable for the rest (own sites are behind Cloudflare, closed by robots.txt, or show no
  unit table in plain HTML). Apartment List's "available_on" date is months old for several "available now" units
  (EDGE 410: 2026-03-31; 110 Washington: May/June; Belleview Gardens 681C: 2026-06-26; Clifton & Co 555: 2026-06-04).
  That means long vacancy or a stale feed date; noted per row.
- Cut close to the window: FIAT House 1000B (Dec 13), Avalon Boonton 2182 (Dec 11), Fairways 2206 (Dec 9), Central and
  Oak 30-308 (Dec 8), Sheffield SES-1121 (Dec 11), Team Campus #211 (Dec 5).
- Price basis to know: Avalon Boonton's stored rents are the 20-month-lease price (12-month is $95 higher, plus a
  required $85 fee). Atwater's own site shows net-effective prices ($2,515 and $2,472); gross matches what we stored.
- The View (Bound Brook) is a floor-plan listing only: no unit number, availability date 2025-08-01, page last
  modified 2026-09-15. Treat as weakly live.
- 145 Goldsborough Dr #1-1 is a private lister's ad (Avail feed) with a leasing fee of $2,795 in the page data.

## 2. Gate facts

- **Ground-floor units found (fail the gate):** Avalon at Edgewater 001-120 (floor 1, own site) and Brownstones 56-118
  (floor 1, Greystar). Likely ground floor by unit numbering, unconfirmed: Atwater 2106, Sheffield SES-1121.
- **Dog policy contradictions:** EDGE (own site "dog-friendly", Trulia "No pets allowed"); 19 East and The Westporter
  (Zumper "No pets allowed", Apartment List and own site say pets welcome); 5201 City Place (Trulia "No Pets");
  FIAT House (Zumper: dogs in non-furnished units only, and most studios are furnished); "small dogs only" on Trulia for
  110 Washington, The View, Team Campus and The Centre.
- **Weight limits confirmed:** 1177 Greens Farms 50 lb; Brownstones 65 lb; Bridgepoint 75 lb; 55 Monroe Pl and 64 Park
  Ave 75 lb (Trulia); Royal Bloomfield 200 lb (Trulia); Fairways no limit (Trulia); AVE Clifton no cap, extra charge
  over 40 lb. Avalon (both) state no weight limit, breed list only. All others: unconfirmed (sites say "contact us").
- **Elevator:** confirmed for 26 rows (amenity lists or site text). Not stated anywhere for Atwater, Royal Bloomfield,
  The Centre, FIAT House (all tall: inferred), Fairways (4 floors, "Mid-Rise"), Avalon Boonton, 5201 City Place, and
  Belleview Gardens (1952 garden apartments; no elevator listed, probably none).
- **Floors confirmed from site data:** Allure 303 (3), EDGE 408/410 (4), Royal 601/630 (6), FIAT 1000B (10),
  Walcott 312/528 (3, 5), Fairways 2206/2321 (2, 3), Brownstones 09-426 (4), Avalon Boonton (2). The rest are inferred
  from unit numbers and marked unconfirmed.
- Address notes: EDGE units 408 and 410 are in the Avenue F building (170 Avenue F), not 100 Avenue G. Allure is given
  as 850 Pacific St by Zumper and by 2022 news.

## 3. Evidence

32 dated items on 9 buildings; 26 rows are `none_found` with where I looked.

- **Allure Harbor Point (most serious):** on BLT's own page, in its Google-review widget: two separate reviewers in the
  last 3 months say elevators break down often; one reports repeated car damage in a tight garage with no cameras; mold;
  a 9% renewal increase; months of unanswered maintenance tickets; a safety complaint. Plus the Feb 1, 2022 terrace
  slab collapse into the garage (News 12; CT Examiner headline). Review dates are relative ("4 weeks ago"), so months
  are approximate.
- The Current on River: one Dec 2023 review about six months without a leasing manager. Vivian: one weak 2024 review.
  Atwater: 8 a.m. trash noise, parking $75/$95. AVE Clifton: garage beams scrape cars (2023).
- Zumper shows only each building's 8 highest-rated Google reviews, so its pages lean positive. Sheffield's overall
  Google score there is 3.7 from 94, but the low reviews aren't shown.

## Blocked or closed

- Cloudflare 403: 1177greenfarm.com, bridgepointbayonne.com, citylinebayonne.com, goldberg-realty.com,
  the-sheffield.com, thebrickofhackensack.com, **bbb.org** (no BBB data for any manager).
- robots.txt closes these to Claude agents: patch.com, re-nj.com, goleader.com, bozzuto.com, westporter.rentcafewebsite.com.
- Connection failures: bayonerentals.com, liveatcentralandoak.com, uchawk.com. CT Examiner articles are paywalled.
- Not used because off limits: Yelp (Avalon Boonton lead), Apartments.com (The View lead), Google Maps.
- Leads I couldn't read: a resident review on Bozzuto's page for The Brick (hallways, elevators out); Westfield Leader
  and Patch pieces on traffic around Fairways at Cranford.
- Trulia building pages carry no resident reviews. Apartment List shows at most one or two "verified" reviews.
- No police press releases or court or code records turned up for any address. One web search per building; this is
  not an exhaustive news check.

## Management changes

- The Westporter: sold by Lighthouse Living to Paredim in Aug–Sep 2024; our manager field is out of date.
- 19 East: sold by Ingerman to KABR Group in March 2022; Apartment List still names Ingerman.
