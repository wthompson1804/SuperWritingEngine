# Independent check 6: 30 of the new apartments (trawl 2), read against their pages

**Verdict: usable, but not yet trustworthy without one more repair pass.** No apartment in the sample breaks the
money, move-in or dog rules, and every price and total recomputes. 26 of 30 carry the single "floor and elevator"
asterisk the new rule requires. But 6 of 30 are wrong in a way that matters: 2 should not be shown (a listing last
changed in May, and a complex its own manager calls townhomes), and 4 show something false or leave out something a
renter must know (two furnished apartments with no furnished line, a utilities fee described both as "inside the price"
and "on top of rent", an apartment number that is not the apartment's). A further 14 have minor faults, most of them
one of five repeatable patterns (below). At this rate (6 / 30 = 20%, Wilson 95% interval about 10% to 38%), I would
expect somewhere between 24 and 94 of the 249 new apartments to carry a wrong item of this kind.

Checked 2026-11-17 from 20:45 UTC by an agent that did not write the pipeline, the evidence batches, the verdicts or the
page. The reviewers' verdict reasoning was not read. No data, verdict, script or page file was edited, nothing was
committed, and **no web request was made**: every page below was read from the cached raw copies of 2026-11-15 to
2026-11-17 (Trulia from its 2026-11-15 cache; no AppFolio, RentCafe, Zillow or other off-limits host was touched).
File written: this report only.

## What was measured

| File | md5 | Written (UTC) |
|---|---|---|
| `data/ranked_units.csv` | `d22b2353893eadc22bd21e830cfa1d05` | 2026-11-17 20:07 (456 rows, 387 shown) |
| `site/data.json` | `67b0284beefceabc471486e28c1f58f0` | 2026-11-17 20:42 (387 apartments, 218 buildings) |
| `data/units.csv` | `7d9edc2cd7f47e30bb3e139a5a55fb9c` | (building crosswalk) |
| `data/evidence/confirm_batch_22/23/24.csv` | `5de2c85a…` / `14d00972…` / `c4757ac4…` | 2026-11-17 |
| `data/evidence/facts_batch_22/23/24.csv` | `5305fa97…` / `52bbd0ce…` / `27ffdfb9…` | 2026-11-17 |
| `data/evidence/live_check_batch_22/23/24.csv` | `1b29c049…` / `a12f7df0…` / `84f4ff8c…` | 2026-11-17 |

**Population.** Shown apartments (`shown == True`, 387) whose building's evidence rows (confirm, facts and live-check
files, mapped to buildings through `data/units.csv` `addr_key → building_id` and `master_buildings.addr_keys`, the same
crosswalk `build_master.py` uses) all lie in `*_batch_22/23/24.csv`: **249 apartments in 145 buildings** (NJ 169, CT 58,
NY 22). No shown apartment has zero evidence rows.

**Draw.** Candidates sorted by `listing_id`; `random.Random(6)`; `sample(NJ, 15)`, then `sample(CT, 10)`, then
`sample(NY, 5)`, in that order from the one generator. The draw put three apartments of Encore 99 (East Haven) in the
CT stratum; they were kept as drawn.

**Each apartment** was checked against the cached listing page (and the building's or manager's own page where one is
cached) for: base rent ≤ $2,200 and the shown figure; available by 2026-12-15; dogs allowed with a limit ≥ 25 lb or
unstated; floor and elevator under the second-trawl rule; a real individual apartment (not a floor plan, 55+,
income-restricted or co-op); address and neighborhood; the total with utilities and fees; and what `site/data.json`
says (open item wording, disclosures, parking, dog text, building "about" lines).

**Mechanical checks, all 30:** the total equals the sum of its lines to the dollar (30 / 30); base rent ≤ $2,200
(max $2,200, 255 Franklin Ave); available now or by Dec 12 (30 / 30); dogs allowed, stated limits 30 to 80 lb, none
under 25 (30 / 30); at most one open item (30 / 30: floor and elevator 26, availability 1, listing 1, none 2); no
55+, income-restricted or co-op wording on any cached page.

## Results

**pass 10 · minor 14 · wrong 6**

| # | Apartment | Result | What and why | Source |
|---|---|---|---|---|
| 1 | 911 Sanhican Dr A8, Trenton NJ (zumper-65470052), studio $1,300 | minor | Price, date (Oct 21 → now), dogs, 2-storey MOD-IV record, open item all right. The listing states "$50 pet fee per month"; the page calls pet rent "not published … typical pet rent" (the amount happens to be the same $50) | https://www.zumper.com/listings/29722887p/studio-berkeley-square-and-parkside-trenton-nj |
| 2 | 96 16th Ave "3", Paterson NJ (apartmentlist:p127128151-3), studio $1,750 | minor | Rent correctly taken as $1,750 from "Monthly Rent: $1,750" (the $1,590 is a prepay option) and disclosed. But the listing names no apartment: "3" is Apartment List's index, and the page prints "Apartment 3". Same agent and same template text as #6 and #7 ("All credit types welcome · No security deposit · reduced monthly rent options"); this one says "Conveniently located in Newark" for a Paterson address | https://www.apartmentlist.com/nj/paterson/96-16th-ave |
| 3 | 280 Verona Ave V5, Newark NJ (trulia:460669961), 1BR $1,650 | **wrong** | Stale by the pipeline's own rule. The cached page: `"lastDateModified":"2026-05-07"`, price history "Listed For Rent Feb 24, 2026", "Decreased by $100 on May 7, 2026". 199 days unchanged at the first tour day (183 is the removal line). Batch 22 recorded no modification date for it, so `page_modified_date` is blank and the rule never ran. Earlier batches recorded Trulia's `lastDateModified` as `listing_page_last_modified` | https://www.trulia.com/home/280-verona-ave-v5-newark-nj-07104-460669961 (raw/trulia/da17c2de30b480cc.html) |
| 4 | Kings Gardens 039, Avenel/Woodbridge NJ (apartmentlist:p40059-1B194-039), 1BR $1,895 | minor | Price, date, 70 lb limit, pet rent $50 right. The special-offer star and "Special offer" line come from "$500 rent credit … (APT 41 & 36 ONLY)": this apartment is 039, so the offer does not apply to it. Parking counted as the $150 garage although the listing also names a lot (cost errs high). "Must have 2.5x the rent in total household income" is not disclosed | https://www.apartmentlist.com/nj/woodbridge/kings-gardens-apartments |
| 5 | Queens Gardens 040, Colonia/Woodbridge NJ (apartmentlist:p1263841-1B200-040), 1BR $1,990 | minor | Price, date, dogs, pet rent, lot right; the offer ("APT 96, 33 & 111 only") is correctly worded "selected apartments only", though 040 is not one of them. "Confirm the dog weight limit in pounds" appears twice in the tour list | https://www.apartmentlist.com/nj/colonia/queens-gardens-apartments |
| 6 | 146 Hamilton Ave "3", Paterson NJ (apartmentlist:p11166981-3), 1BR $2,100 | **wrong** | Rent $2,100 right (as #2). The page says "Apartment 3"; the listing text says "146 Hamilton · 1BED #204". The real number would also read as floor 2, which under the new rule turns the open item into a disclosure. The "garage, fee not published" line comes from a Trulia record of the building that publishes "Garage parking fee $150/mo" (optional) | https://www.apartmentlist.com/nj/paterson/146-hamilton-ave ; https://www.trulia.com/home/146-hamilton-ave-paterson-nj-07501-163470803 |
| 7 | 100 Carroll St "3", Paterson NJ (apartmentlist:p25428225-3), 1BR $2,100 | minor | As #2: rent right, but no apartment number on the listing ("100 Carroll · 1 BED"); "Apartment 3" is the site's index | https://www.apartmentlist.com/nj/paterson/100-carroll-st |
| 8 | 65 Atlantic St 3M, Jersey City (Bergen-Lafayette) (zumper-65573175), 1BR $1,850 | minor | Price, date, small dogs (tour question present), permit-street disclosure right. The building is shown with two apartments, this "3M" (800 sq ft, Zumper) and Trulia's "#3" (650 sq ft): same agent, same $1,850, and Zumper says "There is currently 1 unit listed" at the address, so they may be one apartment. "3M" reads as a third floor in a building the tax list gives 2 storeys (the pipeline's own first reading was floor 3); the open question covers it, but one of the two is wrong | https://www.zumper.com/listings/29846342p/1-bedroom-bergen-lafayette-jersey-city-nj ; https://www.trulia.com/home/65-atlantic-st-3-jersey-city-nj-07304-345148193 |
| 9 | 1010 Cricket Ln, Woodbridge NJ (trulia:2086711654), 1BR $1,900 | pass | $1,900 (cut from $2,025 on Nov 13), available now, small dogs with tour question, page changed Nov 13, washer-dryer flagged "to confirm" | https://www.trulia.com/home/1010-cricket-ln-1010-woodbridge-nj-07095-2086711654 |
| 10 | 263 Bloomfield Ave 43, Bloomfield NJ (apartmentlist:p847102-1B132-43), 1BR $1,950 | minor | Price, date, dogs, address (Apartment List files it under Belleville; ZIP 07003 and the manager's URL say Bloomfield) right. Pet rent published as "$35 - $50"; the total uses $35. "Garage parking" while the listing also names an open lot (the N1 pattern of check 5) | https://www.apartmentlist.com/nj/belleville/263-bloomfield-avenue-apartments |
| 11 | Barclay Village 3341A, Hamilton NJ (apartmentlist:p781837--3341A), 1BR $1,895 | pass | Price, Nov 30, dogs, pet rent $25 right; own site: "Garden Style Community Homes", 2 storeys; floor unknown, one open item | https://www.apartmentlist.com/nj/white-horse/barclay-village ; https://barclayvillage.com/ |
| 12 | The Kislak 404, Newark NJ (apartmentlist:p119939081-…), studio $2,014 | **wrong** | Price right; elevator from the listing's amenity list; floor 4 read from the number (disclosed); one open item (available since Feb 1) right. But the plan is "Studio D-Line (Furnished)" (every apartment listed is furnished) and the page has no furnished line (`conditions` empty). The listing's "2 Months free on a 14-month lease! 3 Months free on a 27-month lease!" is not mentioned | https://www.apartmentlist.com/nj/newark/the-kislak |
| 13 | Crossings at Raritan Station CRS-2228, Raritan NJ (apartmentlist:p44435601-…), 1BR $2,123 | pass | 13-month price, "ask for the 12-month price", "up to 1 month free" offer, dog park, all as on the page | https://www.apartmentlist.com/nj/raritan/crossings-at-raritan-station |
| 14 | 255 Franklin Ave 1, Belleville NJ (trulia:464204348), 1BR $2,200 | **wrong** | $2,200 (cut from $2,800 on Nov 3), at the limit; dogs small; pet rent $50 right. The description: "furnished 1-bedroom … Move-in ready and fully furnished": no furnished line on the page. "Dedicated off-street parking space included" shows as "Off-street parking, with the fee not published" | https://www.trulia.com/home/255-franklin-ave-1-belleville-nj-07109-464204348 |
| 15 | Addison at Princeton Meadows 1906, Plainsboro NJ (apartmentlist:p33289-…), 1BR $1,929 | minor | Price, Dec 12, $6 fee, dog park right. The star and "Special offer" line rest on "move in by 11/15/2026 to receive your second full month's rent free": the offer had expired before the check and cannot meet a Dec 12 move-in | https://www.apartmentlist.com/nj/princeton-meadows/addison-at-princeton-meadows--1 |
| 16 | West Hill Apartments 5-08, Naugatuck CT (rc:trulia:b2749337052:…5-08), 1BR $1,525 | **wrong** | Price, dogs ("one dog under 50 lbs") right. The manager's own page: "these beautiful, spacious **Townhomes**"; the pipeline holds `building_type = townhome` from it. A townhome's door and living floor are at ground level, so "it must be floor 2 (a single flight up)" cannot be met | https://gardenhomesmanagement.com/Property?pid=107 (raw/mgmt_gardenhomes/7d0f8b14c8b1d510.html) |
| 17 | 65 Winfield St 12, Norwalk CT (zumper-55298963), 1BR $2,150 | pass | Price, Nov 1, dogs, on-site laundry, lot right; relisted Nov 2 (the TurboTenant record dates from 2023) | https://www.zumper.com/listings/29991580p/1-bedroom-east-norwalk-norwalk-ct |
| 18 | Autumn Ridge 6, East Haven CT (apartmentlist:p865-s1-auri-6), studio $1,365 | minor | 17-month price disclosed; pet rent $35 right. Required fees on the page: "Trash: $15/month; Community Fee: $10/month" and renter's insurance required; the total adds $15 only | https://www.apartmentlist.com/ct/east-haven/autumn-ridge--1 |
| 19 | Encore 99 97D3, East Haven CT (rc:trulia:b1001599283:…97D3), 1BR $1,870 | pass | Price, 40 lb limit, $35 pet rent, offer, page changed Oct 6. The offer appears twice in the disclosures (a reviewer line and the automatic one) | https://www.trulia.com/building/encore-99-99-hemingway-ave-east-haven-ct-06512-1001599283 |
| 20 | 405 Main St O4, West Haven CT (trulia:466331961), 1BR $1,500 | **wrong** | The listing: "Utilities are Included for a Flat Fee of $150/mo" (Trulia files it as a $150 monthly utilities fee). The page says "required building fees: Already inside the price shown" and also "Utilities are a required flat fee of $150 a month on top of rent", and still adds an electricity estimate; the $150 is in no line (total $1,692; with the fee and no electricity estimate about $1,750). "The listing shows a washer and dryer in the apartment" while the description says "Shared laundry in the building". "Tenants must have an income 3x the rent" not disclosed | https://www.trulia.com/home/405-main-st-o4-west-haven-ct-06516-466331961 |
| 21 | Bay Shore Apartments 164-A4, East Haven CT (rc:trulia:b2005344318:…), 1BR $1,850 | pass | Price, Dec 5, 80 lb limit, $35 pet rent right. Page last changed Sep 24: 59 days at the first tour day, so no open item, but it crosses 60 on Nov 24 | https://www.trulia.com/building/bay-shore-apartments-164-coe-ave-east-haven-ct-06512-2005344318 |
| 22 | 1349 Dixwell Ave, Hamden CT (apartmentlist:p124426133-1_bed_…), 1BR $1,450 | minor | Price, dogs right; on Zumper too, so the Sep 9 record is not stale. No apartment number on either site; the page prints "Apartment 1 Bed" | https://www.apartmentlist.com/ct/hamden/1349-dixwell-avenue-24--37 |
| 23 | Town Walk at Hamden Hills 08223, Hamden CT (apartmentlist:p14807-A2-08223), 1BR $1,988 | minor | 14-month price disclosed; $75 fee, 50 lb limit right. Batch 23 established the numbering (building 08, floor 2, apartment 23), which makes this a floor-2 walk-up with a "floor read from the number" disclosure rather than an open item. Parking counted as the $42 carport while an open lot is the free choice | https://www.apartmentlist.com/ct/hamden/town-walk-at-hamden-hills |
| 24 | Encore 99 99C4 (rc:trulia:b1001599283:…99C4), 1BR $1,870 | pass | As #19 | as #19 |
| 25 | Encore 99 97D4 (rc:trulia:b1001599283:…97D4), 1BR $1,800 | pass | As #19, $1,800 on the page | as #19 |
| 26 | Pinewood Village 0203B, Coram (Brookhaven) NY (rs:pinewood-village-coram:…), studio $2,132 | pass | Price on Trulia and on Heatherwood's page ("$2,132+/month"); 30 lb limit; not 55+. Pet rent: $75 dog rent used, though the policy text also says "$25-50/mo" (errs high) | https://www.heatherwood.com/our-properties/pinewood-village |
| 27 | 301 Tower Ave 4, Maybrook NY (zumper-65723749), 1BR $1,650 | minor | "second floor of a private house", heat and hot water included, all right. "Parking included with rent" shows as "Not published. Ask what a space costs." (An apartment in a private house is not a detached house, but say so if Will reads "no detached houses" more widely) | https://www.zumper.com/listings/24529383p/1-bedroom-maybrook-ny |
| 28 | 76-17 47th Ave 2B, Elmhurst NY (zumper-65719911), studio $1,650 | minor | Floor 2 from "2B", PLUTO C1 walk-up, the "listing" asterisk (description reused for another building) all right. "The only building of the 2 listed in this neighborhood with laundry in the apartment" rests on Zumper's "In-Unit Laundry" tag; the description and the highlighted chip say "Washer and dryer nearby". The tour list repeats the floor question and splits it into two half-sentences | https://www.zumper.com/listings/30021869p/studio-elmhurst-new-york-ny |
| 29 | 233 Shore Rd 20, Long Beach NY (rn:233-shore-rd-long-beach:…), studio $2,150 | minor | Price, no fee, small dogs right; "Includes 1 free parking spot" shows as "An open lot, with the fee not published" | https://www.trulia.com/building/233-shore-rd-233-shore-rd-long-beach-ny-11561-2750784396 |
| 30 | Cortlandt Living 22, Ossining NY (trulia:b2738391140:Unit_22:…), studio $2,000 | pass | Price, dogs, "1 space is included" shown as a free lot, page changed Oct 7, washer-dryer "to confirm" | https://www.trulia.com/building/cortlandt-living-24-claremont-gdns-ossining-ny-10562-2738391140 |

## Every wrong item, with the fix I recommend

| # | Wrong item | Fix |
|---|---|---|
| 3 | 280 Verona Ave V5 shown although the cached page was last changed 2026-05-07 (199 days at the first tour day) | Add a `listing_page_last_modified` fact (2026-05-07, from the cached page) so `staleness()` removes it. Then read `lastDateModified` from every cached Trulia page of a trawl-2 apartment (batches 22 to 24 recorded it only in some live-check notes) and rerun |
| 6 | "Apartment 3" for 146 Hamilton Ave; the listing says "#204" | Take the apartment number from the description where Apartment List's own `unit` is an index; for #204 the floor then reads as 2, a disclosure, not an open item. Add the optional $150 garage fee from the Trulia record to the parking line |
| 12 | The Kislak 404 is furnished and the page does not say so; the 14- and 27-month free-rent incentives are not mentioned | Read "(Furnished)" in Apartment List plan names into `furnished`; disclose the long-lease incentives as a special offer on the 12-month price |
| 14 | 255 Franklin Ave 1 is "fully furnished" with no furnished line; the included parking space shows as "fee not published" | Furnished disclosure from the description; parking "1 off-street space included, no charge" |
| 16 | West Hill Apartments (Naugatuck) is a townhome community by its manager's page; the floor-2 question cannot be satisfied | Remove under the ground-floor rule, or ask Will whether a two-level townhome counts as ground floor; until then, do not show it with a floor-2 question |
| 20 | 405 Main St O4: the cost breakdown says the fee is "already inside the price" and the disclosure says it is "on top of rent"; the $150 utilities fee is in no line; "washer and dryer in the apartment" is contradicted by "Shared laundry in the building"; the 3x income rule is missing | Count a $150 "utilities (flat fee)" line and drop the electricity estimate it covers (total about $1,750); laundry "shared in the building"; add the income disclosure |

## Patterns behind the minor items (worth one repair each)

1. **Apartment List index used as the apartment number** (#2, #6, #7, #22): "Apartment 3" or "Apartment 1 Bed" where the
   listing names no apartment, or a different one. Print no number when the label is the site's index, and read one from
   the description where it is given.
2. **Included parking shown as "fee not published"** (#14, #27, #29; #30 is parsed right): phrases such as "parking
   included with rent", "1 free parking spot", "dedicated off-street space included" are missed.
3. **Offers that do not apply to the apartment** (#4: "APT 41 & 36 ONLY" on 039; #5 likewise but worded "selected
   apartments"; #15: expired before the check). An offer naming other apartments, or a move-in date already past,
   should not set the offer star.
4. **A listing site's in-unit laundry tag against the listing's own words** (#20, #28): the description should win, as
   check 5's N6 asked for the tag alone.
5. **The free parking choice ignored** (#4, #10, #23): where a free lot and a paid garage or carport are both listed,
   the cost and the words use the paid one (check 5's N1, still open for these).

Smaller: required fees partly counted (#18), the low end of a pet-rent range (#10), a published pet fee called an
estimate (#1), a possible duplicate across two sites (#8), duplicated tour questions (#5, #28) and offer lines (#19,
#24, #25), a floor readable from a checker's own numbering convention left as an open item (#23).

## Notes on trust

- **Most of the new apartments rest on one phone call.** 26 of 30 carry the open item "the floor, and whether there is
  an elevator". That is the rule, but it means one more open fact removes them, and the staleness, furnished and
  townhome findings above are exactly such facts.
- **The three Paterson listings (#2, #6, #7)** share one agent, one 750 sq ft size, one template ("All credit types
  welcome · No security deposit required · Multiple rent options") and a "pay months up front for a lower rent"
  scheme; two give no apartment number and one places itself in Newark. Nothing here breaks a rule, but I would ask
  for proof the apartment exists (a number and a showing) before Lamia drives to one.
- **Bay Shore (#21)** passes the 60-day line only because the pipeline judges staleness on Nov 22; from Nov 24 it would
  carry a second open item.
- **What I could not check:** whether any listing is live today (no fresh request was made; Trulia cannot be re-read);
  floors and elevators beyond what the cached pages say; the RentCafe-hosted own sites (Goldberg, Crossings at Raritan
  Station, Town Walk), which are off limits.
