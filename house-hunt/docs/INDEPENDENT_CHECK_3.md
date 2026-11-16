# Independent check 3: the shown list and the page text after the second round of repairs

**Verdict: I would trust the shown list as a list of places to phone, and I would not yet trust the page text or the
cost figures.** The gate facts are in far better shape than at check 2: of 174 shown units whose evidence I read row by
row, 3 should come off and 1 lacks an asterisk (check 2 found 82 of 332). The reviewed-verdict table works. What is
still wrong is mostly in what the page says and counts: the dog warning is a false sentence on 12 units, "this is a
net-effective price" is stated as fact on 13 units where the evidence says the page does not say, the experience
medians are computed over 821 units of which 474 are not on the page, 23 neighborhoods quote a count or a size that
their shown places do not have, and the $3,000 cap holds for 98 of the 347 units only because unknown parking, pet
rent and fees are counted as $0.

Checked 2026-11-16, 01:03 to about 01:45 UTC, by an agent that did not write the pipeline. No script or data file was
edited, nothing was committed, and **no web request was made** (part B was done from files already in the repo).

## What was measured

Frozen at 2026-11-16 01:03:38 UTC into the checker's scratch area:

| File | md5 |
|---|---|
| `data/ranked_units.csv` | `6adc6b0381d985c78853d0132a5cd99c` (821 ranked, 347 shown, 246 buildings) |
| `data/evidence/review_verdicts.csv` | `e8915b4d6c1c4f2f0c4aca96af92769d` (539: ok 287, asterisk 85, remove 167) |
| `data/unit_exclusions.csv` | `f3ae41f0a9bc9b559e240306c5593ada` (213 rows) |
| `site/data.json` | `c48a945c9d45d3bdb74c11bb9441b0f6` (built 01:00:32 UTC, 347 units, 120 neighborhoods, 6 experiences) |

`data/evidence/` and `data/master_units.csv` were copied at the same moment. At 01:18 UTC the three CSVs were unchanged;
`site/data.json` had been rewritten (md5 `7b8fdd2a…`) with a new `ratings` key on every unit and a changed `contact` on
49 units, and nothing else. Every defect below that concerns `host` text was still present in the newer file.
`verdicts.py pending` and `restamp-check` (read-only) report 0 shown units without a current verdict and 0 stale
verdicts.

## Counts

| | |
|---|---|
| Shown units read against every evidence row of their building | 174 in 132 buildings: 97 stratified by state and source site, all 38 in Stamford, all 74 with an `asterisk` verdict (union) |
| Of those: should be removed / lack an asterisk / lack a disclosure / carry an asterisk they do not need | 3 / 1 / 6 / 5 |
| All 38 Stamford units | 38 agree on the gate facts; 2 lack the lease-term disclosure (The Riverhouse) |
| Pattern scans run over all 347 shown units | price or lister cautions, floor-1 readings and numbering patterns, stale sibling pages, elevator rows that are unconfirmed or contradicted, condo evidence, window, cap, beds, weight limit, duplicates |
| Remove verdicts read | 45 of 167 (every elevator, dogs, wrong-building and co-op remove, every "second site omits it" remove, 18 at random): 36 supported, 7 too strict or overtaken by a rule change, 2 depend on an ambiguous numbering pattern |
| The 49 removes for "unit number reads as floor 1" | all 19 buildings compared with their shown and ranked siblings: consistent in 18, inconsistent in 1 (Halstead Parsippany) |
| Exclusions read | 31 of 213, spread over the reason types: 31 supported |
| Elevator on a listing site's tag or text only | 257 units, 173 buildings. 40 buildings sampled; all 173 classified by the evidence in the repo |
| Field check | 30 units: `data.json` equals `ranked_units.csv` on every number for all 347 units (rent, all-in, each cost line, unknown lines, floor, availability, tolls, drive, disclosures, confirm). 9 of the 30 have a wrong fee line or a wrong sentence |
| Neighborhood text | 12 read in full; number checks and word scans run over all 120 |
| Defects | 27: S1 5, S2 6, S3 7, S4 9 |

Things that held: no shown unit is above $3,000 all-in or rent, outside studio/1BR, available after 2026-12-15, on a
stated floor 1, or under a 25 lb limit. No unknown cost line carries an amount; none is described as "no charge" or
"included". Tolls of $0 (59 units) are all Queens, Brooklyn, Nassau or Suffolk addresses with no toll crossing. No host
line contains a dollar figure, size, count or rank that differs from the unit's own fields. No page text written by the
pipeline states who lives somewhere by race, ethnicity or religion. "Year" appears for an experience only in the
`label` field, which the template rewrites to "Experience". Neighborhood ranks recompute exactly.

## Defects

Severity: **S1** a unit is shown that should not be, or the page says something false. **S2** a condition the renter
must know is hidden. **S3** a number is wrong. **S4** minor.

### S1

**D1. 98-76 Queens Blvd 2M (Rego Park) is shown with two open gate facts.** `apartmentlist:p10919258-2M`, $1,663 for a
900 sq ft one-bedroom. `live_check_batch_4`: "1BR 900 sqft at $1,663 is far below the area's other listings in this
batch: verify the price by phone before touring". `confirm_batch_4`: dogs "yes per Apartment List pet data ... no
policy text" (unconfirmed). The verdict records only the dogs. Cause: `review_verdicts.csv` holds one `kind` per unit,
and no rule reads "far below ... verify the price" (`avoid.py` phrase lists; `rank.py:238-278` builds open items from
the single verdict kind). The lot is class RM ("Managed by 98-76 Queens Blvd. Condo"), also not disclosed (D8).

**D2. Halstead Parsippany 2182 is shown although the reviewer's own pattern reads it as a first-floor unit.**
`apartmentlist:p1412214-2182`. The verdict table removes 2153, 2158, 2165, 2169 and 2178 in this building with "the
building's unit numbers carry the floor (building, then floor, then unit) ... reads as a first-floor unit". 2182 has the
same shape and is shown; the checker's row says "unit 2182: unclear". Either 2182 goes, or the five are false removals
(then 1205 and 1206, ranked, are the ground-floor ones). The pattern was inferred by hand, unit by unit, with no check
that siblings are treated alike.

**D3. Residences at The Summit K3-02 (Danbury) is shown on a page 85 days stale and never seen live.**
`rc:trulia:b2751605456:Unit_K3-02:351211069`. Same Trulia building page as M2-07: "page last modified 2026-08-22".
M2-07 carries the stale asterisk; K3-02 carries only "live check". Elsewhere 39 units were removed for exactly "the
listing page was last changed ... and this unit was not seen live". Cause: `build_master.py:1049-1052` reads the
modification date from the unit's own live-check note and skips units with no note; a sibling's date for the same page
is not applied.

**D4. The dog warning on the page is false for 12 of the 19 units that carry it.** Every unit whose open item is "dogs
allowed" gets the catch "Listing sites disagree on whether dogs are allowed here, so get the dog policy in writing."
(`scripts/realtor_lines.py:1093`; the three alternates say the same). Sites disagree on 7 (Piper, Halstead Norwalk
212 and 310, The Westporter, 71-82 Parsons Blvd, Third & Valley 222 and 344). On the other 12 nothing disagrees: the
policy is "upon approval" (121 Towne 376, 635), "case by case" (25 West Broadway 204, 7914 Rockaway Beach Blvd 2F),
"small pets" with dogs not named (142-38 37th Ave 8E), a Zumper block that says "contact for more information" (475
Main St 404, 6500 K Johnson Blvd 211, 31-20 54th St 2fl, 219 Lenox Rd 5G, 948 New York Ave 2, 41-42 Elbertson St 407)
or a pet field with no text (98-76 Queens Blvd 2M). On 142-38 37th Ave 8E and 25 West Broadway 204 the dog subhead
then says "Small dogs are welcome", which is the thing in doubt.

**D5. "This is a net-effective price" is stated as fact on 13 units where the evidence says the page does not say.**
`rent_listed_price_is = net_effective`, disclosure "net-effective rent", cost subhead "This is a net-effective number,
and the monthly bill will be higher" or "The price shown is after a discount":

| Units | What the evidence says |
|---|---|
| 1 Kennedy Flats 2303, 1315 | "Listed price is base rent (base_price field); not stated as net-effective." |
| Harbourside SoNo 225 | "not stated whether the listed price is gross or net-effective" |
| BE (448 Scotland Rd) P, F | "Gross or net-effective: not stated on the page" |
| Kensington Place 1236 | "Now offering great leasing specials. Gross or net-effective: not stated" |
| Harbor Pointe B9-309, B9-258 | "Gross or net-effective: not stated" |
| Harrison Somerset, both plan rows | the offer text is only "Gross or net-effective: not stated" |
| The Grove Somerset 2205 | "gross or net-effective listing price: not stated" |
| Pier Village 4-408, 1-347 | "Gross or net-effective: not stated" |

Check 2 reported this (D14) and the repair added `NET_NEG` (`scripts/rent_terms.py:82-84`). The pattern matches "gross
or net not stated" but not "Gross or net-effective: not stated" (colon), "not stated as net-effective" or "not stated
whether ... gross or net-effective", so the checker's own negation is read as a net-effective statement at
`rent_terms.py:727`. The cap test is not affected (the listed price is used either way); the sentence and the "gross"
all-in shown beside it (for example $3,141 at Harbourside SoNo) are invented. The 13 other net-effective units (Atlas,
Aviva, Solaris Lofts, The Riverhouse, Envy, Avalon Princeton, The Botanic, Spinnaker Wharf) are discussed in D16.

### S2

**D6. Avalon Somerville Station 022-265 lacks the elevator asterisk.** `confirm_batch_15`: elevator "yes (Apartment
List amenity tag only)" and "not listed on AvalonBay's own pages" [Community features on avaloncommunities.com do not
include an elevator]. The same evidence opens the elevator at Avalon Princeton 431 and Avalon Maplewood 001-324. Here
the verdict slot went to `lease_term`, and `_ELEV_CONTRA` (`scripts/parsers.py:999-1002`) wants "own pages ... do not
list", not "not listed on ... own pages".

**D7. The cap is not established for 98 shown units, and 48 of them carry no cost disclosure.** Unknown and counted as
$0: parking on 250 units, building fees on 220, pet rent on 168; all three on 121. Where these lines are known on
other shown units the medians are $125 parking, $88 fees, $50 pet rent. Filling each unknown line with that median
puts 98 units over $3,000 (53 on parking alone; she has a car). The "cost near the cap" disclosure starts at $2,900, so
48 of the 98 say nothing. The Westporter 304A is shown at exactly $3,000 with fees, pet rent, parking and gas unknown;
The Lofts at Garwood GAR2R-08 at $2,999 and The Ashton 609 at $2,998 (never re-read) with two and three unknown lines.
This follows the owner's rule to the letter; the owner should know the size of it.

**D8. Condo units rented by their owner: 4 of 8 carry no condo disclosure.** 7914 Rockaway Beach Blvd 2F ("A Beautiful
1 Bedroom Condo for Rent at The Nautilus", class R4), 142-38 37th Ave 8E (class RM, "furnished; $300 building
application fee + $150 background check"), 25 West Broadway 204 (`listing_type = condo_coop`), 98-76 Queens Blvd 2M
(class RM). Cause: the disclosure is produced only from a verdict of kind `other` or `coop_condo`
(`scripts/rank.py:250, 274, 308`); these four have their one verdict slot taken by `dogs`.

**D9. The Riverhouse (Stamford), both plan rows, lack the lease-term disclosure.** "Net effective Prices advertised
reflect 3 months free on 18 month leases! 12 month lease 1 month free + $2,000 sign on also ok." `price_lease_months`
is blank, so only "net-effective rent" is disclosed.

**D10. 30 Broad Street 703 and 904: "covered parking" is two blocks away.** `parking_type` reads "Offsite parking
available - 1st year FREE! 2 blocks away covered and permitted not assigned". The host line says "covered parking (fee
not published)" and the subhead "The car gets a roof".

**D11. The staleness rule is switched off for most Trulia building-page units; 4 shown units on stale pages carry
nothing.** Sono Pearl 401 (page last modified 2026-07-13, 125 days; its sibling 313 has the asterisk, by verdict),
Wakefield Station 401 (2026-07-21, 117 days), 134 Baldwin Ave 301 and 411 (2026-08-06, 101 days). Two causes in
`scripts/build_master.py`. Line 1057 treats a non-empty `also_seen_at` as "a second site also lists the unit", but for
these rows `also_seen_at` is the same Trulia building page the unit came from, so `listing_stale` stays blank although
`listing_stale_days` is 125 and 117. Line 1052 looks for a modification-date fact only when the unit was not seen
live, so a unit marked live whose date sits in `facts_batch_8` (`listing_last_modified = 2026-08-06`) never gets a date.
The rule itself raised the item on 8 shown units; the other stale asterisks on the page come from verdicts.

### S3

**D12. The experience medians are not medians of what is on the page.** `scripts/build_page_data.py:227` takes them
from the experience table, which is computed over all 821 ranked units; 474 of those are not shown. Published against
recomputed over the shown units:

| Experience | Field | Page | Shown units |
|---|---|---|---|
| Old-Neighborhood | toll round trip | $14.9 | $0.0 |
| Old-Neighborhood | drive / transit minutes | 28.3 / 68 | 23.6 / 56 |
| Little-City | size, all-in | 585 sq ft, $2,744 | 664 sq ft, $2,719 |
| Fresh-Start | size, all-in, park walk | 547 sq ft, $2,831, 1.4 min | 623 sq ft, $2,786, 2.5 min |
| Quiet-Street | toll round trip, all-in | $16.7, $2,937 | $29.7, $2,922 |
| Walk-Everywhere | all-in, drive, transit | $2,767, 18.2, 38 | $2,817, 15.7, 31 |
| Room-to-Breathe | size, mail-rate toll | 750 sq ft, $47.4 | 786 sq ft, $27.1 |

The ranges beside them are over the shown units, so median and range describe different sets. The experience text
quotes the same medians ("about 590 square feet", "$2,750"). Neighborhood `sqft_median` has the same fault (White Plains
567.5 against 632 for its five shown places; Jersey City West Side 581 against 644).

**D13. 23 of the 110 shown neighborhoods quote a count or a size their shown places do not have.** `host.intro` or
`prose.scene` against the median of the neighborhood's shown units:

| Neighborhood | Text says | Shown places have |
|---|---|---|
| East Rutherford | about 17 restaurants within a 10-minute walk | 3 |
| Wallkill (scene) | 27 | 1 |
| Newark (scene) | 14 | 35 |
| Belleville | 11; about 790 sq ft | 5; 894 sq ft |
| Midwood | about 5 restaurants, 4 cafés | 2 restaurants, 2 cafés |
| Bay Ridge | 29 | 14 |
| Jersey City Downtown | 59 | 41 |
| Riverdale-Spuyten Duyvil | 9 | 4 |
| Hawthorne | "the typical apartment we found is about 820 square feet" | one place, 661 sq ft |
| Rahway | about 810 sq ft | 667 |
| Haverstraw | about 860 sq ft | 755 |
| Mount Arlington | about 860 sq ft | 960 |
| Trumbull, Elmhurst, Roxbury, Somerville | 860, 850, 870, 910 sq ft | 781, 800, 815, 856 |

Also Fairfield, Wayne, Westport, Edgewater, Sheepshead Bay, Bedford-Stuyvesant (East), Gravesend (East). The text was
written against an earlier or wider set of units (`data/reference/scene_text_neighborhoods.csv`;
`check_scene_text.py` already fails on five rows). Counts ("38 places"), price ranges, drive minutes and tolls in the
intros do match.

**D14. Required fees counted twice on 4 units** (overstates; the safe direction). Parc at Glenbrook 2328: Trulia's
$2,598 is a total price that includes $123 of fees, and the fee line adds $123 again (all-in $2,960, should be about
$2,837). 1 Kennedy Flats 2303 and 1315: fee line $140 against "$90/mo (total_price minus base_price); $50 amenity fee
named" (the $50 is inside the $90). Residences at The Summit M2-07: $25 inside a total price, added again. Likely
cause: `parsers.monthly_fees_from_text` (`scripts/parsers.py:500`) adds a named fee to the total it is part of, and the
"total price already includes the fees" rule from check 2 (D15) is applied to 23 units but not where a fee text was
also parsed (both fee lines say "parsed from the fee text").

**D15. Wrong floor and height values.** 100 W 139th St 27A is shown as floor 27 "read from the unit number" in a
six-floor building (the repair note says an "unknown" evidence row now beats the label; `unit_floor` is still 27).
Alexander Crossing (Yonkers) shows `building_floors = 2`, basis "stated", with a shown unit read as floor 4.

**D16. Net-effective figures computed from offers that are not rent discounts.** Spinnaker Wharf 5-02E: "$500 Gift
Card! Select Units!" is spread over 12 months (rent basis $2,683, "The price shown is after a discount"). The Botanic
430 and 444: "$2,000 off your second month's rent when you move in by November 30" is spread over 12 months and the
all-in ($2,459, $2,416) is tested on that figure; the gross all-in is $2,627 and $2,583, so the gate is not affected.
For 9 shown units the monthly bill before the free months is over $3,000 all-in (Atlas 1708 $3,408, Aviva E0314
$3,392, Atlas 0308 $3,315, Aviva E0521 $3,276, Avalon Princeton 431 $3,153, Harbourside SoNo $3,141, Solaris Lofts
$3,135, The Riverhouse 308 $3,040, Pier Village 1-347 $3,024). The owner's rule allows it and each is disclosed.

**D17. EDGE 408 and 410 (Bayonne) are shown at the wrong address.** The building's own unit map puts both in "EDGE
Avenue F", 170 Avenue F; the page shows 100 Avenue G. For these two and for Symphony 206E and 207E (page titled
Symphony, description for ENCORE) the catch says "whether this unit is still available at this price", which is not
the open question.

**D18. Offer sentences overstated.** "The listing advertises 2 months free" where the page says "up to 2 months free"
(Stella 14A, Hedges at Hawthorne 409, others on the same template); "ask whether this price is before or after the
free period" where the offer is a $1,000 move-in bonus (Vermella Harrison), a reduced deposit (Halstead Norwalk), a
security-deposit special (Grand Imperial) or an open-house notice (Chateau Rive 304).

### S4

**D19. One apartment shown twice.** 12 Brooklyn Ave, Valley Stream: Trulia unit 501 at $2,675 and a Zumper row with no
unit at $2,700, both one-bedroom, both 806 sq ft, same building id. `build_master.py` merges duplicates only on unit
labels.

**D20. Removes that look too strict.** Grandville Towers 5F and 7C (Red Bank): removed for "elevator on a listing tag
only" plus a July date; under the current rule the tag is `stated`, which leaves one open item. Bedford Creative 204,
205, 301 and 187 Culver Ave 211, 309: removed because Trulia is blocked and Zumper lists other units of the building;
both are the same gate fact, and Arrive Stamford's blocked units with "no other allowed site shows this unit" are
shown. Halstead Parsippany 2153 to 2178: see D2. Seven Avalon Maplewood units are frozen by a remove verdict whose
second reason is "not seen live"; a live check should release them and the verdict will have to be rewritten.

**D21. Elevator asterisks that the evidence does not need, and the tag rule applied unevenly.** 4110 Bowne St 5W (own
lot, class D7, 3 active elevators on the city's list), 80 Richmond Hill Rd 7O (own lot, R4, 4 active), Continuum S0904
and N1119 (17 storeys), 99 Bridge 232 ("tag only, own site blocked", which the rule now accepts). Meanwhile
City Line East, 187 Culver Ave, The Ashton, Valeur Lofts and Bedford Creative carry the same batch-19 sentence
("listing-site amenity tag only") with no asterisk. Both treatments are defensible; they are not the same treatment.

**D22. The verdict table holds one kind per unit.** It is the cause of D1, D6 and D8. Scribe 508/446, The Asher 530,
Stella and others have `asterisk/lease_term` while The Asher 536 has `ok` for the same fact; `asterisk/floor` (100 W
139th St 27A) and `asterisk/other` produce no asterisk at all. The `verdict` column no longer says what the page does.

**D23. Neighborhoods ranked in the top three of an experience on a single place.** Quiet-Street: Princeton (first)
rests on Avalon Princeton 431 alone, whose elevator is the open item and whose rent is net-effective ($3,153 gross
all-in); Teaneck (second) rests on Avalon Teaneck 001-215 alone. Walk-Everywhere: Astoria (East)-Woodside (second) and
Upper West Side-Manhattan Valley (third) on one place each, Kew Gardens (first) on two. The penalty is 4 points for
one place, 2 for two. Those two experiences have 9 and 6 shown places in all.

**D24. Safety wording in open text.** `prose.good_for_her` ends "in one of the safest spots on the whole list" for 21
neighborhoods (the 22 lowest violent rates less one): a fifth of the list, not "the few". `prose.watch_for` says "sits
at (close to) the safety limit we set" for Jamaica, Williamsbridge-Olinville, East Harlem (South), Harlem (North) and
East New York (North). Resident quotes (`local.voices`) carry crime and safety words in several hundred places and
"diverse"/"diversity" in 56 quotes in shown neighborhoods; one Dover quote reads "Lots of hispanics". Whether quotes
count as "open text" depends on the template; the Dover quote should go either way.

**D25. Jersey City split.** 19 buildings checked against street names: 18 sit where they are filed. 134 Baldwin Ave is
filed under Journal Square and stands about 100 m north of Montgomery Street, beside buildings filed under McGinley
Square (The Beacon, 55 Jordan Ave); borderline. Citywide material is labelled: all 11 resident quotes say "about
Jersey City as a whole", the police rate says it is the citywide figure, parking and dog rules name Jersey City. One
thing to know: the pipeline's own 10-month estimate puts Bergen-Lafayette (8 shown) at 1.9 times the citywide violent
rate (9.25 per 1,000 scaled, against the Jamaica yardstick of 9.8); it is labelled an estimate and not used for the
safety rule.

**D26. Floor-plan rows shown as places.** 15 rows, including two "units" each for The Mark, The Riverhouse, Clinton
Flats and Harrison Somerset; BE (448 Scotland Rd) "units" P and F are plan letters ("1 Bed", "1 Bed with Den"). All
carry the availability or listing asterisk.

**D27. Small text faults.** "John H. Ryan Park is about 1 minutes on foot"; "The gym is an elevator ride away" on The
Stanley 504, whose elevator is the open item; "Dogs are welcome up to a weight limit, so choose the puppy accordingly"
where the limit is unpublished.

## B. The elevator question

257 shown units in 173 buildings have `elevator_aggregator_only = yes`. That flag is wider than "amenity tag": it
includes listings whose own description says "elevator building" or gives the height.

| Evidence already in the repo | Buildings | Units |
|---|---|---|
| Strong: unit labels or a stated height of 5 floors or more, a class-D city lot, or listing text that says "elevator building", "elevator access", "N-story" | 91 | 134 |
| Tag only, 4 floors or fewer by the labels, but a single mid-rise or a new podium building (for example Parallel 41, 163 Franklin, Merion Riverwalk, Third & Valley, Lofts at 335) | about 60 | about 90 |
| Tag only in a multi-building, low-rise or converted complex where the tag is doubtful | about 14 | about 22 |
| Already carrying the elevator asterisk | 8 | 11 |

In the random 40: 29 strong, 9 unproven but likely, 2 doubtful (Woodmont West; Parc at Roxbury, which a cached copy of
its own site then settled: "Controlled-Access Building Elevator"). My estimate: about 90 percent of the 173 are
genuine elevator buildings, and 12 to 15 buildings (20 to 25 shown units) are the ones to ask about first:

- **Woodmont West**, Mount Arlington (5201, 2303): buildings 1 to 7, floors 1 to 3.
- **The Royce at Trumbull** (4234, 4211): buildings 1, 4, 6, 9, floors 1 to 3.
- **Brookfield Village Apartments** (5204, 6207): buildings 5 and 6, floors 1 and 2 seen.
- **The Brownstones at Englewood South** (09-326, 09-426): buildings 09, 41, 56; a fourth-floor unit on a tag alone.
- **Reserve at Riverdale** (3-329, 4-412) and **Kensington Place**, South River (4222, 1236): building-floor-unit numbering.
- **The Highlands**, Morris Plains (1200); **Woodland Square**, Montvale (217); **6500 K Johnson Blvd**, Bordentown (211).
- **The Residences at the Kestrel**, Seymour (208); **Beacon Mill Village** (PA-405, PA-202; four converted mill buildings); **Lopresti School Apartments**, Seymour (M306).
- **Harbor Pointe**, Bayonne (B9-309, B9-258) and **TGM Anchor Point**, Stamford (1323, 2224): several buildings, floors 1 to 4.

The repo holds an own-site page for 50 of the 173 buildings (`raw/building_contacts_own_site/`); only 3 of them state
an elevator (Parc at Roxbury, 333 State St, Harbourside SoNo), and none says "walk-up" or "garden-style".

## What I could not check

- Whether any listing is still available or still at its price. 179 shown units are Trulia rows last read on Nov 15;
  46 were never seen live. No request was made in this check.
- The true floor of the 313 units whose floor is not published, and the numbering pattern of any complex.
- Any building's own site, pet policy in pounds, parking price or fee schedule beyond what is cached.
- The 173 shown units outside the row-by-row sample were covered by the pattern scans listed above, not read in full.
- "People who live here say ..." sentences against the quotes they summarise; resident quotes line by line.
- Parking-rule sentences were compared with `local.parking_rules` in the page data for the 12 neighborhoods read and
  agree; the dollar figures quoted elsewhere (Bound Brook $10, East Orange $150, Hawthorne $2, Bayonne $5, Orange $40)
  were not traced to `local_rules*.csv`.
- The page template, the map, the avoid cards (36), held units (28) and units awaiting a live check (28).
- Contact phones beyond consistency: 74 shown units have none; 30 are listing-site tracking numbers.

## Files this check wrote

`docs/INDEPENDENT_CHECK_3.md` and `data/evidence/independent_check_3_units.csv` (280 rows: 174 shown units with both
verdicts side by side, 45 remove verdicts, 31 exclusions, 30 field-check units). Nothing else was touched.
