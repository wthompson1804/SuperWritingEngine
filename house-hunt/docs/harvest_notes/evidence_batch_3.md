# Evidence pass, batch 3 (2026-11-15, 20:40–21:00 UTC)

Batch file: `data/reference/evidence_batches/batch_3.csv` (35 rows, 39 units; 12 New Jersey rows, 23 New York City rows).
All 35 rows were worked. Output: `data/evidence/{live_check,confirm,items,facts}_batch_3.csv`.

Scripts (all idempotent; the CSVs are upserted by key): `scripts/ev_b3_fetch.py` (polite fetch, robots check including
Claude-named groups, 2.5 s per host, cache in `raw/evidence_b3/`), `ev_b3_live.py` (+ `ev_b3_live_notes.json`),
`ev_b3_nyc.py` and `ev_b3_nyc_items.py` (311 and HPD records, cache in `raw/evidence_b3_nyc/`),
`ev_b3_openigloo_items.py`, `ev_b3_confirm_facts.py`, `ev_b3_util.py`.

## 1. Live check

All 39 units are still listed, at the stored price, and available by 2026-12-15 (39 live, 0 gone, 0 changed).
Own-site numbers were used where readable (AvalonBay, Greystar). Listed, but with a problem that the price check does
not show:

| Unit | Problem |
|---|---|
| Avalon Teaneck 002-129 | AvalonBay's own data puts it on **floor 1** (ground floor). Unit 001-215 is on floor 2. |
| 23-50 Waters Edge Dr 5F and 4T, 16-70 Bell Blvd 317 | Description says dogs only as service or emotional-support animals. The listing's "dogs allowed" field is wrong. An Openigloo review of 16-70 Bell says the same. |
| 2925 W 5th St 7A ($1,776) | Probably not a real rental. The source link is a realtor.com record for Apt 23B, the lot is the Trump Village Section 3 co-op, and the text says "Original condition - perfect to renovate to your taste". |
| eaves West Windsor (3 units) | No elevator is listed anywhere and every listed unit is on floors 1 to 3. The "elevator inferred from floor count" basis does not hold. |
| Avalon Union 5306 | Elevator rests on Apartment List's tag only. AvalonBay's pages never mention one, and a 2022 review describes a second-story resident moving out for a first-floor home for an old dog. |
| The Landings 1109 | Floor unknown; "1109" could be a ground-floor unit. Owner's site is blocked. |
| Third & Valley | Apartment List says dogs allowed; Trulia's building page says dogs and cats not allowed. Bozzuto's sites could not be read. |
| 867 Dekalb Ave 2B | Income-restricted unit (household income $90k to $154k). |
| 2561 Bedford Ave 3B | Listed 2026-09-23 (about 53 days), two price cuts. The listing never mentions an elevator; the elevator rests on the PLUTO class code for a 4-floor, 8-unit 1910 building. |
| 35-16 34th St 5E and 32-42 33rd St D3 | The two listings use the same description word for word (same broker), including "14 ft high ceilings". |

## 2. Gate facts (142 rows)

- Floor: 33 confirmed, 3 unconfirmed. Most NYC floors come from the unit number, and the quote says so. Unconfirmed:
  32-42 33rd St D3, Landings 1109, Third & Valley (numbering may start below floor 1).
- Elevator: 29 confirmed, 6 unconfirmed (eaves ×3, Avalon Union ×2, Fords Corner, which is six stories with units on
  floor 6 but states no elevator). NYC elevators are confirmed from the PLUTO building class (class D = elevator
  apartments); 1875 Atlantic Ave was matched to the neighbouring lot (1885 Atlantic).
- Dogs allowed: 31 confirmed, 5 contradicting rows (the three Bay Terrace units, and Third & Valley's two sources).
- Dog weight limit: 9 confirmed, 23 unconfirmed, 3 not applicable. Only one pound figure exists: **Fords Corner, 65 lb**.
  AvalonBay (Teaneck, Union, West Windsor) states a breed list and no weight limit. RiverParc and The Landings show
  "small, large" dogs on Trulia. **Every NYC broker listing is unconfirmed**: Trulia says "small dogs" with no pounds,
  and Zumper says "contact for more information". No building pet policy was found for any of them.

Note: `CLAUDE.md` now gives the dog limit as 25 lb. The files record what each page says, so nothing depends on the threshold.

## 3. Evidence items (144 rows; rows repeat where two batch rows are the same building)

By category: management 64, other 18, positive 15, elevator 12, noise 11, safety_incident 1, none_found 23. No car-crime
item was found for any building.

Sources that worked:
- **NYC 311 and HPD violations** (Open Data API, by tax lot, 2024-11-15 to 2026-11-15). These rows are count summaries,
  marked "Record summary (counts, not a quote)". A tax lot can hold more than one building (Trump Village, Bay Terrace).
- **Openigloo** building pages for 13 of the 22 NYC buildings (found by tax-lot number in the reviewed-buildings
  sitemaps). Only two reviews per building are in the page; "View all" is a script button. Openigloo shows relative
  ages only, so `item_date` is a month or "before YYYY-MM". Labels like "9 minutes ago" are treated as undated.
  Two pages sit under another address on the same lot (1889 Atlantic Ave; 199 Schenck Ave for The Highland).
- **Zumper building pages** show eight "highest rated" web reviews with dates (Landings, Avalon Teaneck, Avalon Union).
  They are almost all praise, and were pulled in late 2024 to early 2025.
- **Queens Ledger**, 2026-02-12: heating outages at 32-42 and 32-52 33rd Street (A&E Real Estate).

Most serious:
1. **32-42 33rd St (D3)**: 100 HPD violations in 24 months (29 class C), 10 heat and 20 pest or mold complaints, the
   February 2026 news report, and reviews about a months-long cooking-gas outage and 14% to 40% rent rises.
2. **35-16 34th St (5E)**: 129 HPD violations (43 class C, 9 open), 8 elevator complaints in April 2025, a review of a
   ceiling collapse.
3. **250 Clarkson Ave (422)**: 121 HPD violations (34 class C, 16 open), 15 heat and 15 pest or mold complaints;
   Openigloo shows 6 evictions and 14 litigation cases.
4. **3415 Farragut Rd (7K)**: reviews say the manager (New Day) withholds deposits, one dated October 2026; 11 heat and
   3 elevator complaints.
5. **The Highland, 2840 Atlantic Ave**: 7 elevator complaints in 2026 (latest 2026-09-18), 16 class C violations,
   47 noise complaints.
6. **16-70 Bell Blvd (317)**: 46 heat or hot water complaints. **219 Lenox Rd (5G)**: roach infestation review, July 2026.
   **96 Hart St (3E)**: 20 heat complaints, 3 elevator complaints, 3 open class C violations.

## 4. Blocked or not available

- thirdandvalleyapts.com and bozzuto.com: robots.txt disallows Claude agents. Not fetched.
- riversedgepi.com, riverparcpi.com, equityapartments.com: HTTP 403. Not retried.
- bbb.org: robots.txt allows profile pages, but they returned HTTP 403. Five profile URLs were requested in one run
  before the block was seen (the loop should have stopped at the first). No BBB data was used.
- re-nj.com: robots.txt disallows. Not fetched.
- Apartment List and Trulia pages carry no resident reviews.
- No Openigloo reviews for: 31-20 54th St, 2920 Brighton 4th St, 2925 W 5th St, 1010 Rogers Ave, 2561 Bedford Ave,
  1244 and 1644 New York Ave, 44-10 Ketcham St, 41-42 Elbertson St.
- News search (one query per named building or address group, results used only to find pages) found nothing at the
  address for the eight New Jersey buildings, The Highland, Trump Village or the Bay Terrace buildings. The other NYC
  street addresses were not searched one by one.
- Parking fees are missing for Third & Valley, RiversEdge, RiverParc, The Landings and every NYC building. Building
  floor counts are missing for the Port Imperial buildings and Third & Valley.
