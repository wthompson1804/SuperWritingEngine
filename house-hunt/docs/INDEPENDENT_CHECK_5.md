# Independent check 5: the repairs after check 4, and what the repairs introduced

**Verdict: I would call the list accurate. I would not yet call the page text accurate. I would not yet call the page
itself correct.**

- **The list.** All 523 shown apartments pass every rule on the pipeline's own fields, and the evidence agrees: of 157
  apartments read row by row (148 that check 4 never read, in all 101 buildings it had not opened, plus the 9
  Quiet-Street and Walk-Everywhere apartments), none should be removed and none lacks an asterisk. The live re-read
  (batch 20) is applied exactly. No duplicates. The thin rule recomputes. All 59 removals since the 568-apartment page
  are justified by a rule. One condition a renter must know is missing from one apartment (a broker fee).
- **The text.** Every number in the six experience texts, the 77 neighborhood texts and the 725 building and apartment
  texts recomputes from the data (prices to the dollar and to $10, sizes, counts, minutes, tolls, superlatives). What
  is wrong is a small set of statements that rest on a field that is itself wrong or narrower than the words: a
  "garage" that is an open lot, "miles to a train station" beside a PATH or light-rail stop, a 25 lb dog limit no page
  supports, "one of the safest spots" still in 15 neighborhoods.
- **The page.** Navigation, the tutorial, the two prices, the cost breakdown, My list, compare and all filters behave
  as built and agree with the data in every case I measured (no console error, no "undefined", no sideways scroll at
  390 or 1280). But the template prints "Garage parking, no monthly charge" for 22 apartments whose free space is an
  open lot, uses one star for two different things and then offers a filter that promises "no star", and words the
  lease length wrongly on four apartments.

Checked 2026-11-16 from 06:04 UTC by an agent that did not write the pipeline, the text or the page. No script or data
file was edited, nothing was committed, no web request was made. Files written: this report,
`data/evidence/independent_check_5_units.csv` (157 rows), `site/screens/check5_*.png` (30).

## What was measured

Recorded at 2026-11-16 06:04:17 UTC and again at 06:50 UTC (unchanged; nothing else was running):

| File | md5 | Written |
|---|---|---|
| `data/ranked_units.csv` | `c3c93b4a200b4c005f06b47d7bcc0224` | 05:39:10 (664 ranked, 523 shown) |
| `data/evidence/review_verdicts.csv` | `6d91f9a201319aeb3b44c2598a90c823` | 05:01:31 (924 rows) |
| `site/data.json` | `cbb4bbcc90037f9c16aef5c5a485d462` | 05:53:27 (523 apartments, 202 buildings, 77 neighborhoods) |
| `site/dist/artifact.html` | `4522b36da0f5e51adfc7f92efa34f28b` | 05:59:38 |

| | |
|---|---|
| Rule check, all 523 | 0 violations: real apartment, studio or 1BR (189 / 334), total ≤ $3,000 (max $2,998) on the 12-month price where one is known, pet rent in every total, available by Dec 15, current verdict, at most one open gate fact (218 with one), not excluded, no co-op class, no cut neighborhood (Jamaica sits exactly on the yardstick, 9.8 / 25.0) |
| Evidence read row by row | 157 apartments in 106 buildings: 0 remove, 0 missing asterisk, 157 agree (38 asterisk, 119 fine). 3 carry a note (broker fee; 25 lb limit; "garage") |
| Keyword screen of all evidence rows of all 523 | co-op, income, credit, furnished, senior, restricted, student, short-term, walk-up, ground floor, no dogs, weight under 25 lb, gone, room, broker fee: one new finding (broker fee, N4) |
| Batch 20 | 190 rows: 9 gone (all off), 8 changed (all applied to the dollar), 173 live. 16 twelve-month prices: 11 over the limit (all off), 5 used as the rent (Scribe 502, 507, 542, 544, 546, "$2,395 on a 12-month lease"). Sibling rule: 6 shown apartments in The Asher, The Leaf and Scribe carry the "listing" asterisk; no shown sibling in Motif or Harbor Landing. 0 breaches |
| Rent against the cached listing | 67 apartments from every source: the listed price is in the cached page beside the apartment's label in 64, in the file in 3 (own-site formats); the 4 page rents that differ from the first capture are a later re-read (The Walcott 417, The Tetris 305) or the 12-month price (Scribe 502, 507). 0 wrong |
| Rent and total on the page | all 523 rows parsed from the built page: rent equals the rent line to the dollar (523), total is the sum rounded to $10 (523), the breakdown adds up (523), every line marked as the data marks it, no cost shown as $0, every unpublished cost named under the total, "could pass $3,000" present exactly where `all_in_likely` > 3,000. Lease wording wrong on 4 (N7) |
| Typical rent and total | all 6 experiences and all 77 neighborhoods recomputed from the shown apartments: equal |
| At a glance | 432 entries on 77 neighborhoods recomputed from the shown buildings: values and ranges equal; garage count off by one in 3 (N8) |
| Filters | 20 runs (16 single filters, 3 combinations, cleared), each driven through the sheet and compared on the first screen, 6 experience pages, 77 neighborhood pages and 202 building pages: 0 mismatches |
| Duplicates | none among 523 (label, building, price, size, coordinates) |
| Thin rule | recomputes: 38 single-apartment neighborhoods, 10 kept, 28 cut |
| Removals since the 568 page | 59 read: 59 justified, 0 wrongful |
| Page walk | 390×844 and 1280×900: first screen, 6 experiences, 18 neighborhoods, 26 buildings with every row and an apartment opened, My list (8 sorts), compare of two and three, filters on and off; plus the text of all 809 views at 390. No console error |
| Tests | `verify_all.py --with-browser`: 22 passed, 0 failed. 28 planted faults: 22 caught, 6 slip (below) |
| New defects | 29: S1 1, S2 5, S3 5, S4 18 |

## Check 4's defects, re-tested

| # | Now | Evidence |
|---|---|---|
| D1 Harbor Pointe in "Elizabeth" | **Fixed** | `b_5c4193202c` at 40.6726, -74.0982, `nj:bayonne`, 44.8 min, Bayonne Police, Bayonne's permit rule, park 3.4 min. "Elizabeth" is gone. All 33 rows of `municipality_changes.csv` read: each new municipality fits the address and ZIP; police agency and street rule follow the town for every shown building (only Beacon Falls has no agency). The 14 buildings of `building_coord_check.csv`: 4 re-geocoded, 9 ZIP boundaries, 1 flagged and not shown |
| D2 second site omits the apartment | **Fixed** | 328 Pacific 705, Metropolis Towers 16F, 509 MLK 39E are off; Bedford Creative 204, 205, 301, The Tetris 211, 309, 100 Prospect N311 and 525 Riverdale Ave 5U carry "availability". No other blocked row has the finding |
| D3 Residences at The Summit | **Fixed** | all 8 off ("elevator; listing") |
| D4 labels that are not apartments | **Fixed** | BE `P`, `F`, Appletree `C`, `E`, `F` are `not_an_apartment`; 630 W 163rd St 10 is off. Remaining odd labels read: 1483 Shore Pkwy `F` (asterisk), 3440 Guider Ave `Z` (floor 5 stated), 204 Sherman Ave `4` (4th floor stated), 948 New York Ave `2` (second floor stated), 263 Franklin Ave `48` (48 apartments on five floors: no floor readable; disclosed) |
| D5 "elevator" / "Dogs allowed" stated where open | **Fixed** | 0 of 118 open-elevator apartments list an elevator as a feature ("elevator not confirmed"); 0 of 28 open-dog apartments say dogs are allowed ("Ask"); building headers the same (32 and 14 buildings) |
| D6 dog park far while the building has its own | **Fixed** | no neighborhood complains of the dog park where a shown building has a dog park or run; 14 say "Own dog area" |
| D7 Quiet-Street contradicts Fairfield | **Fixed** | "You drive to dinner, except in Fairfield, where about 8 restaurants and 5 bars are within a 10-minute walk." |
| D8 income, credit, furnished | **Fixed** | 9 / 3 / 11 disclosures present and correct. My own search found no other income, credit or furnished statement. A different condition was missed: N4 |
| D9 doorman from "Concierge" | **Fixed** | "doorman" on 9 buildings, each with a source that says doorman or door person; 46 say concierge. Residue: 110 Washington (one source says doorman, the building's own list says "Live-In Superintendent"), 1105 30th Rd (from tenant reviews) |
| D10 Beacon Falls has no crime figure | **Partly** | still shown (5 apartments); no safety wording; "Crime, for the record: No violent or property crime rate is published for Beacon Falls…" sits behind a tap. The owner's rule is untested there |
| D11 Walk-Everywhere overclaims | **Fixed** | names Kew Gardens and Bay Ridge with each one's figures; all recompute |
| D12 Old-Neighborhood and Newark | **Fixed** | "close to your parents, except in Newark"; tolls split by borough. Residue: N9 |
| D13 "Every apartment here fits what you need" | **Fixed** | "These apartments were picked to fit what you need … A star marks any with one thing still to confirm." |
| D14 experiences that do not fit their neighborhoods | **Not fixed** | nothing moved (owner's decision). Franklin is now a second plain misfit in Little-City: "No restaurants or bars are within a 10-minute walk", 82 minutes away, under "often a small downtown nearby" |
| D15 guards do not read what is published | **Partly** | every fault written into the text of `site/data.json` is now caught. Not guarded: the template's own sentences against the data (N1, N2, N7), a cost line's label in `data.json`, and the two line CSVs against the published text |
| D16 text described a wider sample | **Fixed** | recomputes from the shown buildings in all 77. New: N3, N8 |
| D17 Parkway Lofts in East Orange | **Fixed** | in Bloomfield with Bloomfield's rule and police; `city` right on all shown buildings |
| D18 parking stated too firmly | **Partly** | The Atwater: "Parking in an open lot, $75 a month" from the listing's fee line. J Centra Burlington still reads "Garage parking, with the fee not published." beside its own quote "surface parking; optional garages". See N1 |
| D19 Continuum "Floors: 2" | **Fixed** | 17; no building's floor count is below one of its apartments' floors |
| D20 "up to" dropped | **Fixed** | 0 offers lose "up to" |
| D21 map counts 89 | **Fixed** | chips 23, 23, 21, 5, 3, 2 = 77 |
| D22 wrong reading of unit numbers | **Fixed** | The Grove Somerset 2141, 2205, 3172, 4149, 4171 shown as floors 2 to 4. All 16 complexes of `unit_numbering_conventions.csv` (the table holds 16, not 27): no shown apartment reads as ground floor, and no stated floor disagrees with a convention (few floors are stated, so the conventions stay readings) |
| D23 thin rule wording | **Fixed** | CLAUDE.md now says "a real apartment with no open gate fact" |
| D24 internal language | **Fixed** | 0 hits in confirm, disclosure and question text. Residue: N18, N19 |
| D25 template sentences | **Partly** | "A one-bedroom", "No woods…", no "car sleeps", no "puppy". Still there: "LOCAL RULES Ask" (Beacon Falls), "not found, ask" (9 buildings), a building named "41-42 Elbertson Street, Elmhurst NY" |
| D26 "staying in Queens" on Queens places | **Fixed** | Queens pages and Old-Neighborhood say "COMPARED TO A TYPICAL QUEENS APARTMENT" |
| D27 two safety wordings | **Not fixed** | "This is also one of the safest spots on the whole list." in 15 neighborhoods beside the badge "Among the safest on the list" |
| D28 cards cut mid-sentence | **Not fixed** | "In Bloomfield the daily things are close: a dog park, the supermarket and the train are all within 0.5 miles." is clamped to two lines at 390 |
| D29 ratings | **Not fixed** | 26 buildings `searched: false` with a rating; 64 "Apartments.com", 42 "RentCafe", 17 "Birdeye" ratings `seen_via: "search result display"` |
| D30 elevator on a tag in other complexes | **Fixed** | Pier Village, The Brunswick, 1 Kennedy Flats, Admirals Cove, Halstead Parsippany, The Confluence, Fort Hill Peekskill carry the asterisk |

**Tally: fixed 22, partly 4, not fixed 4, regressed 0.**

**The District at 15Fifteen (8 apartments removed).** Right by the rules: three communities share the address and one
(Mason East) is for residents 55 and older, so "which community" is an open eligibility fact; the elevator is named
only on a listing site and the labels name buildings 1 and 2 with no height on any page. Two open facts. Six of the
eight were re-read live on Nov 16 at the stored price, so one phone call would bring them back.

## New defects

Severity: **S1** an apartment shown that should not be, or a false statement on the page. **S2** a hidden condition or
a misleading line. **S3** a wrong number. **S4** minor.

### S1

**N1. "Garage parking, no monthly charge." where the free space is an open lot.** 22 apartments in 6 buildings:

| Building | Apartments | What the listing says |
|---|---|---|
| Spinnaker Wharf, Milford (`b_519bad81b0`) | 5-02E | "Unassigned off-street parking included" |
| TGM Anchor Point, Stamford (`b_80ba75dc8e`) | 1323, 2224, 2312, 2221, 1242 | "1 space of open parking included per apartment … Assigned garage spaces available for $150" |
| The Edge at Raritan Heights, New Brunswick (`b_71aaaa2555`) | 3 | "1 free surface spot per 1-bedroom" |
| Kensington Place, East Brunswick | 8 | "open lot included in lease" |
| Woodmont West | 3 | "Open parking: included in lease; Garage $125" |
| Reserve at Riverdale | 2 | "Open lot: included in lease; Underground parking garage $50" |

The page prints the contradiction itself: "Garage parking, no monthly charge. The listing says: "garage: 1 parking
space per lease holder, maximum of 2 spaces per apartment. Unassigned off-street"" (screenshot
`check5_390_garage_no_charge_spinnaker.png`). The same reading feeds the header chip "Garage parking", "Coming home:
garage parking, no monthly charge", the compare row "Garage · no monthly charge", the night rating, the "Garage or
covered" filter and "At a glance" (N8). J Centra Burlington (6 apartments) reads "Garage parking, with the fee not
published." for surface parking with optional garages (D18). Cause: `scripts/rank.py:91-98` gives rank 4 to any
parking text containing "garage", and the stored type string of these begins "garage:" although
`parking.kinds` is `["lot"]`; `site/index.html:1930-1933` (`parkKind`) and `:2061` then say "Garage" from the rank
alone and never read `parking.kinds`, `garage_is_optional_extra` or `fee_note`. Fix: name the free space from
`parking.kinds` and `fee_note` ("An open-lot space is included; a garage space is $150 a month"), and rank on the
space that is included.

### S2

**N2. One star, two meanings, and a filter that promises "no star".** A star on the rent marks a special offer (343
apartments); a star on the apartment marks the one thing to confirm (218). The tutorial explains only the second ("A
star (*) on an apartment means one thing is still to confirm before you sign"). The building header then counts both:
City Trust Apartments "See the 8 apartments · 8 with something to confirm" (one has an open item), Scribe "8 with
something to confirm" (three do); 67 buildings disagree with their asterisks. My list says "2* to confirm" for 110
Washington A413, which has one open item. The filter "Nothing left to confirm · no star (*)" returns 305 apartments, of
which 190 still show a star on the rent and a line such as "A special offer applies, so confirm the normal monthly
rent." Cause: `site/index.html:2966` (`nToConfirm` adds `rentStar`), `:3009`, and the filter's `star:!!conf(U)` at
`:2388`. Fix: a different mark for an offer ("offer"), and count only the open item.

**N3. "Miles to a train station" beside a PATH, light-rail or subway stop.** "At a glance" measures commuter-rail
stations only. Journal Square: "1.8 miles to a train station from most buildings here", while the same page's Sunday
row starts "walk 3 min to Journal Square; PATH" (`check5_390_train_station_journal_square.png`). Also Bergen-Lafayette
"2.3 miles" (Liberty State Park light rail, 2 to 5 minutes), Jersey City West Side "3 miles" (West Side Avenue light
rail, 3 to 9), Bayonne "5 miles" (22nd and 45th Street light rail, 4 to 12), Elmhurst "1.3 miles" (subway, 4), East
Flatbush-Farragut "2.9 miles" (subway, 9). 93 apartments. Eight Brooklyn neighborhoods simply have no train line.
Cause: `scripts/enrich_units.py:122-123` (`nearest_train_station` is the nearest rail station in the map data) feeding
`build_scene_text.py:137,153`. Fix: use the first rail boarding of the transit itinerary, or say "commuter train".

**N4. A broker fee is not disclosed.** 525 Riverdale Ave 5U, Yonkers (`trulia:466334272`): the listing says "Broker
fee." (`facts_batch_19`, `broker_fee`). The page has no word of it; it prints "Managed by: Steve Eisenstein -
Associate Real Estate Broker." Cause: `parsers.renter_conditions` reads income, credit and furnished only. Fix: a
"broker fee" disclosure.

**N5. "Dogs are allowed up to 25 pounds" that no page supports.** Brookview Commons East, Danbury (BC-524, BC-406).
The evidence row reads "small dogs only; no pound figure on any page read (the stored 25 lb could not be traced to a
page)". 25 lb is the gate's threshold; the sister building Brookview Commons II is shown as "small dogs, weight limit
not published". Cause: `dog_weight_limit_lb` from `community_facts` outranks the checker's later note. Fix: treat the
checker's "could not be traced" as "not published".

**N6. "Washer and dryer in the apartment" resting on a listing site's appliance tag.** Of 133 shown buildings with
in-unit laundry, 27 (70 apartments) have no source beyond Trulia's "Appliances & Utilities: Washer, Dryer" tag, among
them Regency on Hudson, Appletree Suites, 134 Baldwin Ave, Admirals Cove, Bedford Creative, Newark Urby. Parkway Lofts
and 121 Towne name a washer only. The page says "washer-dryer in the apartment" and the filter "A washer and dryer in
the apartment" passes them. No source contradicts any of them. Fix: "the listing names a washer and dryer; confirm
they are in the apartment", as is done for elevators.

### S3

**N7. Lease length worded wrongly on four apartments.** City Trust Collection: Arcade 302 and AVE Clifton 467: "RENT
$… on a 13-month lease"; the price "is for a 12-month lease" and 13 months is the offer's term. Valley and Bloom
36-305: "on a 13-month lease"; the price is the 14-month price. Avalon Maplewood 001-324 ($2,590, $51 under the
limit): no lease wording on the row; the price is the 18-month price (the disclosure further down says so). Cause:
`site/index.html:1834` (`leaseMonths`) reads `rent.lease_months` (the offer) before `cost_check.lease_term_months`
(the price). Fix: read the price's term first.

**N8. "Garage at N of the M buildings here" one too many.** Milford "3 of the 4" (2 garages, 1 covered), Stamford "18
of the 24" (17), New Brunswick "2 of the 4" (1): the three open lots of N1 counted as garages.

**N9. "From Newark each visit costs about $24 round trip."** True of 14 of the 21 Newark apartments; Newark Urby is
$33 and Envy by Gomes $43.

**N10. "Available now" hides 14 apartments available today.** The filter keeps only `available == "now"` (398); 14
apartments dated 2026-11-16 are left out (`site/index.html:2388`, `move`). As days pass the gap grows.

**N11. A total just under the limit with gas left out and no warning.** 32 Connecticut apartments have no gas
estimate ("Gas: not published"), and `all_in_likely` does not add one. 1177 Greens Farms 212 (likely $2,984) and
Spinnaker Wharf 5-02E ($2,969) would pass $3,000 with a usual gas bill ($12 to $33) and carry no "could pass" line.

### S4

- **N12.** "All in" as a label on the Queens scale ("All in · Much better · −$580"; "All in: much better than
  staying in Queens (−$580)"), on every experience, neighborhood and building view (`check5_390_all_in_label.png`).
- **N13.** Crime wording outside the allowed phrase: D27's sentence (15 neighborhoods) and, in the "Not on the list"
  rows, "Car crime: 14 vehicle thefts and thefts from vehicles within 250 m".
- **N14.** The row says "floor 7" for 251 apartments whose floor is only read from the number; the same apartment's
  detail says "Floor not published. Ask: Confirm it is above the ground floor".
- **N15.** Contradictions inside one neighborhood page. Jamaica: "There are no bars within a 10-minute walk." and
  "Few bars are within a 10-minute walk." Westport: "Almost no restaurants are within a 10-minute walk", "No
  restaurants or bars are within a 10-minute walk", "2 cafés are within a 10-minute walk" and "nothing here is
  within walking distance".
- **N16.** Unclear sentences. Ridgewood: "9 cafés are close too, and the supermarket is 0.1 miles away." (opens the
  paragraph). South Orange: "The building lists a dog amenity, so ask what it is." (the data says pet spa). Regency
  on Hudson: "The listing could not be fully confirmed." (the reason, a claim about an occupancy permit, is elsewhere).
  Bayonne, "Watch for": "The nearest park is about 8 minutes on foot."
- **N17.** Grammar: "1 of the 4 buildings here have their own dog area" (Bridgeport, Englewood, Jamaica, White Plains).
- **N18.** "Fee is the state fee (see Connecticut statewide row)" (Hamden dog licence).
- **N19.** Avoid cards: "On record: 23 (34.33 per 100 units; citywide 90th percentile 2.9)".
- **N20.** The same question twice in the tour list: "What is the rent on a 12-month lease? Ask before touring." and
  "What is the rent on a 12-month lease?" (Scribe 508 and the other sibling-rule apartments).
- **N21.** Compare with three columns at 390: "Apartme / nt 606", "City Trust Apartme…" (`check5_390_compare_two.png`).
- **N22.** "A lease is 12 months." in the footer; 123 apartments are priced on another term.
- **N23.** 110 Washington: reviews line ": 2.7 out of 5 · 3 reviews", labelled "Apartments.com", links to
  apartmenthomeliving.com.
- **N24.** One building shown as two: 3310 Nostrand Ave (503) and 3280-3310 Nostrand Ave (202), 16 m apart.
- **N25.** Dog amenities in the evidence and not in the structured field: Kensington Place ("Pet-Friendly with dog
  park"), The Wyldes and 153-10 88th Ave (pet spa). The 72 buildings that have a source string all agree with it.
- **N26.** 142-38 37th Ave 8E: "The page says small dogs; no weight number given." beside "The listing says small
  pets are allowed and does not name dogs." Two apartments with an open dog question whose "To ask" line is about
  something else (948 New York Ave 2, 3280-3310 Nostrand Ave 202).
- **N27.** Bay Ridge: "The beach is 0.3 miles from the door." 9949 Shore Rd faces the Narrows; I could not confirm a
  beach there, and it will read as an error to anyone who knows the street.
- **N28.** Six unstarred apartments sit on a page last changed 58 days before the build (SoNo 19 Day 207; Bedford
  Hall 303, 314, 516, 517, 617): they cross the 60-day line on Nov 18, before tours start.
- **N29.** `years[].label` still reads "The Quiet-Street Year" in `site/data.json` (not printed; `display_label` is).

## Sections of the brief not covered above

- **Dog and laundry fields (B2).** All 72 buildings with a dog source string and all 183 with a laundry string were
  compared with the flags: no flag contradicts its source (West Side Square has both "W/D hookup; On-site laundry"
  and its own page's "In-Home Washer and Dryer"; kept as in-unit). Findings: N6, N25.
- **Tutorial.** Seven cards. Opens once on a first visit to the first screen, not on a deep link; Done, Skip, Escape
  close it; it stays closed after a reload; "How this works" at the top and in the footer reopen it at card 1; it
  fits both sizes. Every statement holds except the star (N2). "See photos opens the listing's photos" is loose where
  the button says "opens the building's own site".
- **My list and compare.** Saving three from three buildings, eight sort orders, a filter that excludes all three
  ("Outside your filters: rent $2,354 is over $1,500."; all three stay), compare of two and three with "Rent" and
  "Total with utilities and fees" rows: correct. "Clear all" restores 523 and keeps the saved apartments.
- **Banned words in the open.** None of "year" for an experience, "unit" (outside quoted listing text and N19),
  "everything included", "cap", "net-effective", file paths. No price without "Rent" or "Total" beside it.

## Guards

`verify_all.py --with-browser`: 22 passed, 0 failed (test_parsers 259, test_rules 793, test_rules --data 5,385, the
walk-through at 390). In a shadow copy, 28 faults were planted one at a time; 22 are caught and 6 slip:

| Planted | Where | Result |
|---|---|---|
| conceit ("The river keeps its own hours."), wrong number ($2,040 → $1,540) | neighborhood CSV | caught: `check_scene_text`, `check_published_text` |
| false amenity ("Every building here has a garage.", Bloomfield) | neighborhood CSV only | caught by `check_published_text` (text differs from the page); `check_scene_text` alone passes it |
| conceit, jargon, wrong number, false pool, rent called the total | `realtor_lines.csv`, `building_about.csv` | **all five slip**: nothing compares these files with the published text |
| conceit, wrong number ($2,040 → $1,540; 740 → 940 sq ft; "Only 16 apartments"; "12 restaurants") | `site/data.json` text | all caught: `check_published_text` |
| jargon ("This unit cleared every gate, and the all-in is under the cap.") | `site/data.json` building text and `confirm.why` | caught: `check_published_text`, `test_rules --data` |
| false amenity (pool; "Every building here has a garage.") | `site/data.json` text, and `amenities.pool` itself | caught: `check_published_text` |
| rent figure called the total | `site/data.json` apartment line; `all_in` set to the rent | caught |
| the rent cost line renamed "pet rent" | `site/data.json` `all_in_lines` | **slips** every Python check |
| the same kinds written into the CSV and `data.json` together (unlisted conceit, false garage, a toll equal to the drive minutes, "typical rent" with the total's figure, "No building here has a dog park", "Crime is low here.") | both | all six caught |

What no guard sees is a true reading of a wrong or narrow field (N1, N3, N5) and the template's own sentences against
the data (N2, N7, N10).

## What I could not check

- Whether any listing is live now. 79 shown apartments were never re-read and 23 could not be (Trulia).
- The 12-month price of 104 shown apartments priced on a 13- to 24-month lease with none read (97 without an
  asterisk). In the five buildings where it was read, it was 19 to 55 percent above the listed price in four and
  1 percent in one. Each carries "on a 15-month lease" and "ask for the 12-month price", as the rule says.
- The true floor of 478 apartments (227 unknown, 251 read from the number).
- Whether Montclair, Maplewood or other towns outside `overnight_parking_towns.csv` restrict overnight parking.
- Whether Miramar, 405 W 206th St (713E), is a condo as recorded, not a co-op.
- Resident quotes, outside descriptions and rule summaries line by line; the map beyond its counts; widths other
  than 390 and 1280; the 320 px layout.
- Whether Beacon Mill Village's five apartments of 600 to 740 sq ft are each really $1,805 (the cached page shows
  that price beside each label).
