# Evidence pass, batch 14 (2026-11-15, 22:47–23:00 UTC)

29 buildings in `data/reference/evidence_batches/batch_14.csv`, all in New Jersey (Orange 2, Dumont 1, East Brunswick /
South River 2, East Orange 6, East Rutherford 1, Bayonne 1, Fort Lee 1, Somerset 2, Hackensack 3, Hoboken 1, Jersey City 3,
Long Branch 1, Montclair 1, Mount Arlington 1, Mount Holly 2, Newark 1). All 29 were worked. Openigloo does not apply.

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_14.csv`. Raw pages: `raw/evidence_b14/`.
Scripts: `scripts/ev14_fetch.py` (refetch), `ev14_site.py` (robots check incl. Claude groups, then fetch),
`ev14_trulia_parse.py`, `ev14_al_parse.py`, `ev14_zumper_reviews.py`, `ev14_text.py`, `ev14_show.py`, and `ev14_write.py`,
which rebuilds all five CSVs with no network. The parsers and the writer read fetch logs in the session scratch folder; if
that folder is gone, refetch with `ev14_fetch.py` first.

## 1. Live check (38 unit rows: 30 live, 4 changed, 4 blocked, 0 gone)

- **Blocked (4):** Trulia started returning HTTP 403 after 21 good fetches. Not read today: 270 Luis M Marin 16F,
  328 Pacific 705, 99 Pine St 8A, 479 Roseville Ave 34A. One retry eight minutes later also got 403; stopped there.
  None of the four units could be verified on another allowed page.
- **Changed (4):** Pier Village 4-408 is $2,363 (stored $2,371) and 1-347 is $2,708 (stored $2,716): both $8 cheaper.
  Allure 258's two stored prices ($2,250, $2,500, no unit) cannot be found: Trulia now shows only a range, four plans
  with no prices and 0 available units.
- **Live at floor-plan level only (not verified units):** The Sterling (page last modified 2026-05-15, 0 units listed),
  Harrison Somerset (two plan prices, no unit numbers), Northampton Crossing (one row labelled unit "1").
- Latest dates: Harbor Pointe B9-309 on Dec 4; Carriage Club B208, 9 Lake Ave 6A, 5 Linden 6F and 111 Washington 11C on
  Dec 1. Nothing is above $3,000 or after Dec 15.

### Special offers (verbatim text is in live_check notes and facts; no page says whether the listed price is gross or net)
- BE (448 Scotland): "New Construction Lease Up Special 1 Month Free On 14 Month Lease Term"; "Indoor Parking Fee Waived
  For 6 Months With Same Day Applications"; "Waived Amenity Fee".
- Kensington Place (own site): "2 months free on a 13+ lease and an additional $500 credit if you apply within 24 hours
  of your tour."
- Allure 258: "LIMITED TIME SPECIAL: RECEIVE UP TO 1 MONTH FREE RENT & 1 YEAR OF FREE PARKING", good until Nov 30.
- Harbor Pointe: "2 Months Free & Waived Amenity Fee - Must Move In By 12/31/26 Reduced Security Deposit (with fully
  approved credit) PLUS 2 Months of Free Parking! *Only applicable on leases 13 months or longer."
- Harrison Somerset (own site): "1 Month Free with One Year Lease".
- The Grove Somerset (own site): "Apply By 11/30 and Receive 50% Off Base Rent for Your First 4 Months Plus 6 Months of
  Complimentary Parking. Other Costs and Fees Excluded."
- Pier Village: "1-month free rent on select apartments with an executed lease by 11/30. Restrictions apply."

### Listings that need a human look
- **Carriage Club at Mt Arlington is a 55+ senior community** ("designed exclusively for those aged 55+"). Both units
  are live, but the building is age-restricted.
- **434 Scotland Rd 45N:** the description is the marketing text for Be 448 (448 Scotland Rd). Either the address or
  the text is wrong. Same agent ("Abe rosen") as 50 Washington 11E and 720 Park Ave 91C.
- **50 Washington St 11E:** the description opens "Welcome to 55 Washington Street".
- **324 Monroe St 6AA:** listed as a 1-bedroom, described as "a true 2 bedroom", unit "#6"; price cut $100 on Nov 12.
- **479 Roseville Ave:** Zumper's listing for another unit at the address says "No Pets Allowed"; the stored Trulia
  value was dogs yes and could not be re-read. Recorded as `contradicts`.
- **The Grove Somerset:** required monthly fees exist but the fee guide is a Canva page that could not be read; an
  unlabelled "$86" appears on Apartment List. Unit 1116 reads as a ground-floor unit (see below).
- 140 N Walnut 7A carries a broker fee and has been listed 27 days; 280 Luis M Marin 15F carries a one-month broker fee,
  $200 parking and an extra gym charge.

## 2. Gate facts (118 rows: 45 confirmed, 72 unconfirmed, 1 contradicts)

**The "elevator inferred from height" flags in this batch came from unit labels (45N, 9A, 91C, 34A), not from building
height. Those labels are not floors.** What the pages support:

- **Elevator confirmed (12):** BE, Kensington Place ("Elevator access"), Allure 258 (17 stories), 50 Washington St (from
  another listing at the address on Zumper), Harbor Pointe, The Sterling, Harrison Somerset, 5 Linden St, 270 Luis M
  Marin (Zumper), 328 Pacific / Lafayette House ("first floor elevator bank"), Pier Village, Carriage Club.
- **Elevator probably absent (my reading, unconfirmed):** 60 W Madison Ave ("private entrance", 22 units), 9 Lake Ave
  (Lake Estates garden condo, 1970), 145 Park Ave ("yard access"), 5 Elm Ave ("private entrance"), 51 1st St (8 units in
  the building, so "8A" is not a floor), 324 Monroe St ("#6", basement laundry), Village Square (plans named "1st Floor"
  and "2nd Floor", built 1946, no elevator listed), Northampton Crossing (Apartment List lists one, its own site does not).
- **The Grove Somerset:** "Elevator access in select buildings" only.
- **Not stated at all:** 434 Scotland, 140 N Walnut, 111 Washington, 720 Park Ave, 57 Washington, 280 Luis M Marin
  (likely yes: concierge tower), 99 Pine and 479 Roseville (blocked).
- **Floor confirmed for 2 buildings only:** 5 Linden St 6F ("located on the 6th floor") and Village Square 7D and 45D
  (floor plan "1BR 2nd Floor"). Everything else is `unconfirmed` with my reading in the quote column, for example
  Kensington 4222 = building 4 floor 2, Harbor Pointe B9-309 = floor 3, Pier Village 4-408 = floor 4, Carriage Club B208
  = floor 2, **Grove 1116 = building 1, floor 1 (ground)**.
- **Dog weight limit in pounds (4):** Harbor Pointe 50, Village Square 65, Carriage Club 40, 5 Elm Ave 40.
- **Size-only "small dogs", no number (16):** every Trulia listing read except 5 Elm Ave, including BE (1 dog), Allure 258 (2), The
  Sterling (1). These pass under the current rule; the wording is recorded.
- **No limit published:** Kensington Place, Harrison Somerset, The Grove ("Contact our leasing team to confirm breed and
  weight restrictions"), Pier Village (breed restrictions only), Northampton Crossing, 328 Pacific.

## 3. Ratings (31 rows: 5 with a score, 24 `none_found`, 2 "collecting reviews" rows beside a Zumper score)

- Apartment List: **Harbor Pointe 3.8/5 from 5** (3 texts read, all dated 2024-08-15; 2 negative, none in the last 6
  months); Harrison Somerset 5/5 from 1 (2025-04-25); Pier Village 5/5 from 1 (no text).
- Google rating shown on Zumper: **The Grove Somerset 4.5/5 from 240** (pulled 2024-12-07) and **Village Square 3.5/5
  from 50** (pulled 2025-02-12). Zumper shows only the eight highest-rated reviews, all 5-star, none newer than December
  2024. For The Grove they also predate the June 2026 sale.
- No review in this batch is from the last 6 months, so the 6-month columns are 0 or empty everywhere.
- Kensington Place's own reviews page is hand-picked, undated testimonials; not counted.

## 4. Evidence items (41 rows)

none_found 24, positive 7, other 3, management 2, safety_incident 2, car_crime 2, noise 1. No elevator-outage item.

### Most serious: Harbor Pointe, Bayonne (ranked 1 in its neighborhood)
- **Tenant petition, 2023-05-19 (Change.org):** "Car break-ins on community property and in parking garages", stolen
  mail and packages, broken or unlocked building entrances, frequent false fire alarms, and ticketing of a lot tenants
  used. It names a management change from Greystar to Pontis.
- **Apartment List reviews, 2024-08-15:** water bills "about ten times more" with no resolution, lost mail, management
  not responding.
- All of this is 15 to 30 months old, so by the plan it is "gives us pause, older", not an avoid.

### Others
- The Grove Somerset was sold in June 2026 to TruAmerica, which plans to renovate every unit (Jersey Digs, 2026-07-08).
  Older praise may not describe the current management.
- News 12 stories about East Orange elevator outages and lawsuits were read and are about other buildings (The
  Pavilion, The Castle at 75 Prospect), so nothing was recorded against the six East Orange addresses here.

## 5. Blocked or not done

- Trulia: 403 on four listing pages (above). `livingatharborpointe.com` and `wm-piervillage.com`: 403.
  `villagesquarefmg.com` and `metropolistowers.com`: did not connect. `estately.com`: 403.
- `re-nj.com` (Grove sale, Sterling sale, Allure leasing) and `nj.com`, `tapinto.net`: disallowed by robots.txt for us.
  `renthop.com`: 403. Grove fee guide (`communityfeeguide.info`): a Canva page that needs a browser.
- Not used: Patch, Better Business Bureau, Zillow, Apartments.com, RentCafe, StreetEasy, ForRent, HotPads. Search results
  pointed to reviews on Apartments.com for Kensington, Allure 258, Pier Village, Village Square and Northampton Crossing;
  none was read.
- News was checked with one web search per managed building and one grouped search per city for the single-unit
  listings. No court or code-enforcement record was looked up. Management start dates were not found except the
  Harbor Pointe and Grove changes above.
- The 17 single-landlord Trulia listings have no building page, so their gate facts rest on the listing text alone.
