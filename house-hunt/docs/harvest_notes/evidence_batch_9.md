# Evidence pass, batch 9 (2026-11-15, 21:13–21:35 UTC)

29 New Jersey buildings in `data/reference/evidence_batches/batch_9.csv` (Montvale to Sayreville). All 29 were worked.
Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_9.csv`. Raw pages: `raw/evidence_b9/`
(`_index.jsonl`, `zumper_bld.json`, `_al_reviews.json`, `_sites.jsonl`).
Scripts: `scripts/ev9_fetch.py` (refetch listing URLs), `ev9_zumper.py`, `ev9_sites.py` and `ev9_site.py` (robots check, then
fetch), `ev9_al_reviews.py`, and `ev9_write.py`, which rebuilds all five CSVs from the cached pages with no network. Every
excerpt is sliced out of the cached page by start and end markers, so it is verbatim.

## 1. Live check (48 unit rows)

- 46 live at the stored price, 2 changed, 0 gone, 0 blocked. Nothing is above $3,000. Every unit is available by 2026-12-15.
- Changed: Molly Brook on Belmont 1-306 ($2,543 → $2,538) and 2-102 ($2,638 → $2,633).
- Sources: Apartment List building pages (16 buildings), Trulia building pages (12), AvalonBay's own page (1).
  Only AvalonBay's own site gave unit prices. The other own sites either returned HTTP 403 or show no prices in their HTML.

### Units that need a human look before they are shown
- **Avalon Piscataway 005-5106 is on floor 1** (AvalonBay's own unit record: `floorNumber` 1). It fails the no-ground-floor
  gate. Its $2,520 is the 20-month price; with required monthly fees it is $2,628.
- **Likely ground floor from the unit number (not confirmed):** Woodmont West 1109, The Rail 4102, Molly Brook 2-102,
  Halstead Parsippany 1103, Reserve at Riverdale 3-117, The Gardens at Raritan 97-1C.
- **No elevator listed anywhere:** The Gardens at Raritan (1948 garden complex), Quail Ridge (garden community, 1,032
  units), Alister Morristown (1950s complex), Morgan's Bluff ("garden-style"), Molly Brook, The Villas at Fairway, The Park,
  The Rail, Renaissance Plaza Square and Park Square (five floors). The last two are probably elevator buildings whose
  listing just omits it; the garden complexes probably are not.
- **Noble' (7711 River Rd):** no unit number. Trulia shows a plan-level price ("Alcove Studios $2,550, Available Now") and
  zero available units. New building: the own site says "coming October 15, 2026". Homes are on floors 3 to 12.
- **Symphony (1009 Broad St):** the Trulia page is titled Symphony but its description is for "ENCORE", a 63-home building.
  It allows small dogs only, with no number. Confirm the building and the limit.
- **The District at 15Fifteen:** three communities share the address and one (Mason East) is 55+. Confirm which one units
  1-219 and 1-234 are in. 1-219 has been shown as available since 2026-08-17.
- **Sitting a long time:** Halstead Parsippany 2182 (available since 2026-05-14), 1103 (2026-09-07), Premiere Residences
  1804 (2026-09-13). These are availability dates, not listing ages, but they point the same way.
- **Name changes:** Zumper lists Halstead Parsippany as Modera Parsippany, Reserve at Riverdale as Alexan Riverdale, and
  The Rail as Solo at North Bergen (renamed by its new owner). Old reviews sit under the old names.

## 2. Gate facts (116 rows: 60 confirmed, 55 unconfirmed, 1 contradicts)

Dog weight limit (gate is 25 lb or more):
- Confirmed and passing: Highlands at Morris Plains (no breed or weight restrictions), Woodmont West (no weight limit, own
  site), Parc at Roxbury (AION: no weight restrictions), Avalon Piscataway (breed list only), Park Square 80 lb,
  Renaissance Plaza Square 75 lb (Apartment List; Zumper's data says 150), The George 60 lb, Premiere Residences 50 lb,
  The Edge at Raritan Heights under 40 lb, The Villas at Fairway under 40 lb, Eleven80 35 lb, The Gardens at Raritan 30 lb.
- "Small dogs" with no number: Symphony, Centurion Sleepy Hollow (Trulia: "Large dogs are not permitted").
- No number found: Woodland Square, Alister, The Brunswick, Cosmo 440, Newark Urby, The Rail, Noble', Molly Brook,
  Halstead, District 15Fifteen (fees apply "regardless of pet size"), Quail Ridge, The Mint, Reserve at Riverdale, The Park
  (own site: "breed and weight restrictions may apply"), Morgan's Bluff.
- Floors: one confirmed from page data (Avalon, floor 1) and one from the own site (Noble', floors 3 to 12). All others are
  inferred from the unit number and marked unconfirmed.

## 3. Evidence items (58 rows)

management 13, positive 10, other 8, noise 4, safety_incident 4, elevator 1, car_crime 0, none_found 18.

### Most serious
- **Eleven80, 1180 Raymond Blvd, Newark (Cushman & Wakefield).** Jersey Digs, 2026-01-16 and 2026-04-22: a security guard
  attacked twice on 2025-09-17, the second time with a knife; front doors that "remain unlocked at all times"; strangers
  getting in, one found in the women's locker room; a tenant lawsuit alleging years of neglect and rent increases above the
  city limit; the tenant-union leader given an eviction notice 11 days after threatening to sue. All of this is older than
  six months, so by the plan it is "gives us pause" unless newer reports turn up. A TAPinto article on the lawsuit could not
  be read (robots.txt). Zumper's 2024 Google score (4.3 from 146) predates all of it.
- **The Brunswick, 100 Hiram Sq, New Brunswick (AION).** Lowest scores in the batch: Google 2.8 from 69 (as shown by Zumper,
  pulled 2024-12), Birdeye 3.1 from 80. No dated negative text could be read from an allowed source.
- **Parc at Roxbury (AION).** Two Birdeye reviews from about 2025: intercoms broken for years, building doors that may not
  lock, repairs with no reply from management. Score is still 4.3 from 108.
- **Woodmont West.** Parking shortage and towing threats, thin walls (2021 to 2022), monthly administrative fees (2024).
- **Avalon Piscataway.** Fire on 2024-08-01 displaced about 20 families (News 12); a resident mentions false fire alarms.
- Minor: The George (people sleeping in hallways, 2022), The Mint (elevator down "once in a while", 2022), Renaissance
  Plaza Square (AC broken for a month, 2024), The Rail (missing package, 2024).

No car break-in, theft or catalytic converter report was found for any of the 29 buildings.

## 4. Ratings (34 rows; 17 of 29 buildings have a score, 12 are none_found)

- Sources: Google score as shown on Zumper building pages (7 buildings; Zumper shows only eight reviews, all 5-star, pulled
  between 2024-11 and 2025-03), Birdeye profile pages (10 buildings; a current aggregate score and count, mostly from
  Google, with few or no review texts), Apartment List (6 buildings, 1 to 4 reviews each).
- No source gave a readable review from the last six months, so `reviews_last_6_months` and `negative_last_6_months` are 0
  everywhere. That is a limit of the sources, not a clean bill.
- Lowest: The Brunswick 2.8 and 3.1; The Park 3.6 (380); Quail Ridge 3.6 (317); The George 3.6 (26); Woodmont West 3.8
  (170); Morgan's Bluff 3.8 (87).

## 5. Blocked or not done

- HTTP 403 on the building's own site: alistermorristown.com, rentpremiere.com, eleven80rentals.com,
  therailnorthbergen.com, themintrahway.com, liveatriverdale.com, morgansbluff.com, parksquareapt.com,
  map.liveatwoodlandsquare.com. Also bbb.org (403) and redfin.com (403).
- Closed to us by robots.txt: highlandsmorrisplains.com, tapinto.net (names anthropic-ai), bozzuto.com review pages.
- morristowngreen.com asks for a 600-second crawl delay; it was honoured (one page fetched).
- Zumper has no building page for 8 addresses (HTTP 404), and its address pages for Cosmo 440, The Villas at Fairway and
  The Park are single unrelated units.
- Birdeye shows some old reviews imported from Apartments.com (The Brunswick, The Gardens at Raritan, Avalon Piscataway).
  Apartments.com is off limits, so those were not recorded.
- Web search (one per building) pointed to review aggregators (wheree, wanderlog, veryapt, safebutler, brightplace,
  Point2Homes, RentCafe). They were not read and nothing from the search summaries is recorded. Leads worth a manual look:
  Halstead Parsippany (elevator outages, false fire alarms), Quail Ridge (mold), Morgan's Bluff (package thefts), The Park
  (parking shortage, lost packages), Reserve at Riverdale (management), Woodland Square (a 65 lb dog limit on Redfin).
- A review snippet about a broken elevator appears in the Woodland Square page data, but it belongs to a neighbouring
  listing (The District, Montvale), so it is not recorded.
- No police press releases, court or code-enforcement records were found online for any address.

## 6. Management

- Alister Morristown: Mill Creek Residential bought it in 2017 (formerly Jacob Ford Village); 2018 tenant complaints to the
  town council about eviction notices and fees (Morristown Green).
- The Brunswick: AION took over after 2020 (formerly Riverwatch Commons).
- Eleven80: Cushman & Wakefield manages; the owner put the building up for sale in 2025 (Jersey Digs).
- The Rail at North Bergen: formerly Solo at North Bergen.
