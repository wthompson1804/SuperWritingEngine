# Independent check 4: the shown list, the page text and the page itself

**Verdict: I would not call the list accurate, and I would not call the page text accurate.**

- **The list.** By the pipeline's own fields all 568 shown apartments pass every rule, and the gate facts are handled
  consistently in most of the 353 apartments whose evidence I read. But 18 of those 353 should not be shown or lack an
  asterisk, a whole neighborhood ("Elizabeth", 7 apartments) is a Bayonne building filed in the wrong city, and a re-read
  made by another agent while I worked found 9 shown apartments gone. That is too many for "accurate".
- **The text.** The sentences written per apartment and per building are in good shape: every count, price, size,
  comparison and superlative I recomputed holds. The neighborhood and experience text is not: 12 neighborhoods say the
  nearest dog park is miles away while their only building has its own, the "At a glance" figures describe a wider
  sample than the apartments on the page, the two tiny experiences overclaim, and the page template itself states
  "elevator" for 96 apartments whose elevator is the open question.

Checked 2026-11-16, 03:42 to about 04:15 UTC, by an agent that did not write the pipeline. No script or data file was
edited, nothing was committed, no web request was made. Files written: this report,
`data/evidence/independent_check_4_units.csv` (353 rows) and `site/screens/check4_01` to `check4_08` `.png`.

## What was measured

Frozen at 2026-11-16 03:42:40 UTC (copies in the checker's scratch area):

| File | md5 |
|---|---|
| `data/ranked_units.csv` | `01cb36557d2d389db38fa1fb6866b955` (733 ranked, 568 shown, 212 buildings, 78 neighborhoods) |
| `data/evidence/review_verdicts.csv` | `5fdc0bea737e18ae6b41b687978d2391` (916 rows) |
| `data/unit_exclusions.csv` | `0c6f43b48e1b8f9323cb3f17455f6301` (205 rows) |
| `site/data.json` | `16240b2d898611c438c0e0d342a7bb97` (built 03:25:38 UTC) |
| `data/reference/realtor_lines.csv` | `20d53c2480a7776fa052d383b0518949` |
| `data/reference/building_about.csv` | `f0d6c25a58215c014c5af45f36217d57` |
| `data/reference/scene_text_years.csv` | `a9d50daf36aec46383e6712dbb6d41be` |
| `data/reference/scene_text_neighborhoods.csv` | `d776f47d116cab97dc347ffdc03448fd` |

`data/evidence/*.csv`, `building_crosswalk.csv`, `elevator_doubt.csv` and `master_units.csv` were copied at the same
moment. The page was walked from a copy of `site/dist/artifact.html` taken at 03:52 UTC (md5 `5cfdda1f…`, built by the
page agent with the tutorial; its embedded data is the frozen `data.json`).

**The repo moved under the freeze.** At 04:04 UTC `data/ranked_units.csv`, `review_verdicts.csv` and
`unit_exclusions.csv` had been rewritten by another agent's pipeline run (692 ranked, 542 shown); `site/data.json` had
not. `data/evidence/live_check_batch_20.csv` (written 03:53) re-read 190 listings: 173 live, 8 changed price, **9 gone**
(The Mercer 8H, 9E, 10E, 11E, 12E, 12F: "This page could not be found"; Kensington Place 1315; Harbor Pointe B9-457;
LIA by Vermella 307). All nine are on the page as published. In the new ranked file 32 of the page's 568 apartments are
no longer shown (all 8 at The Mercer, 4 each at The Asher, The Leaf and Harbor Landing, 3 at Motif, and others), and 6
are shown that are not on the page. Everything below is measured against the frozen files.

## Counts

| | |
|---|---|
| A1. Rule check, all 568 shown apartments | 0 violations by the pipeline's own fields (real apartment, studio or 1BR, total ≤ $3,000 with pet rent, available by Dec 15, not excluded, current verdict, at most one open gate fact, no co-op class, no cut neighborhood) |
| A2. Evidence read row by row | 353 apartments in 117 buildings: all 34 buildings that hold the 124 newly entered apartments (118 of the 124 are in the CSV), all 9 shown buildings of the elevator doubt table, the ten named complexes, all Quiet-Street and Walk-Everywhere apartments, all 10 kept single-apartment neighborhoods, 52 further buildings stratified by experience and state (the last 28 with floor and weight rows trimmed) |
| Of those: should be removed / lack an asterisk / agree | 14 / 4 / 335 (6 of the 335 lack a disclosure: D8) |
| Unit numbering, all complexes with removed "first-floor" siblings (29 buildings) | no shown apartment reads as ground floor under its complex's convention; one sequentially numbered apartment elsewhere does (D4); 5 removals rest on a wrong reading (D22) |
| A3. Thin rule | recomputes exactly: 38 single-apartment neighborhoods, 10 kept, 28 cut |
| A4. Duplicates | none found across 568 (labels normalised; address, price, size, beds, coordinates) |
| A6. Apartments that left in the last three runs | all 66 read (27 thin, 16 floor plans or building offers, 18 "first-floor number", 2 two-open-items, 2 ninth in their building, 1 merged duplicate): 62 justified, 4 not (D22) |
| B. Text | 6 experiences in full; 47 neighborhoods read in full, number checks over all 78 (378 number claims); all 212 buildings and all 568 apartments by recomputation (every comparison and superlative), 60 buildings read |
| C. Structure | medians and ranges, neighborhood ranking, counts, ids, day ratings, cost sums, `all_in_likely` (40 recomputed), pet rent, tolls, drive minutes, contacts, ratings, photos: all consistent, except D19 |
| D. Page walk at 390 × 844 | 38 pages: first screen, 6 experiences, 13 neighborhoods, 18 buildings with every row opened. No console error (one blocked web font), no "undefined", "NaN", "null" or "[object Object]", no horizontal scroll |
| E. Tests | see the last section: at the freeze state the suites pass; at 04:04 UTC `verify_all.py` fails 4 steps |
| Defects | 30: S1 6, S2 9, S3 8, S4 7 |

What held: no shown apartment is over $3,000, outside studio or one bedroom, late, on a stated floor 1, under a 25 lb
limit, or in a neighborhood above the crime yardstick. Every cost line sums. Every "lowest-priced of N", "largest",
"only building with a pool", "closest to a park" and "only apartment available now" recomputes true (568 apartment
lines, 212 building texts, 0 false). No apartment line states a floor that is only read from a label. Experience medians
and ranges equal the shown apartments (check 3's D12 is fixed). No text says "dogs are allowed" in a building whose dog
policy is open, in the written text (the template does: D5). No "not checked again" wording, no "year" for an
experience, no group named by race, ethnicity or religion in pipeline text. Broker and owner listings show no phone.

## Defects

Severity: **S1** an apartment shown that should not be, or a false statement on the page. **S2** a hidden condition or a
misleading line. **S3** a wrong number. **S4** minor.

### S1

**D1. The "Elizabeth" neighborhood is a Bayonne building in the wrong place.** Harbor Pointe, 302 Constitution Ave,
Bayonne NJ 07002 (`b_5c4193202c`, 7 apartments: B3-348, B9-240, B9-258, B9-309, B9-334, B9-449, B9-457) carries the
coordinates 40.6710, -74.1798, about five miles west of Bayonne, in Elizabeth's port. `hood_id = nj:elizabeth`; it is
the only building there. Everything the page says about it is measured at the wrong point: "In Elizabeth you would drive
for everything: nothing to eat is within a 10-minute walk", "The waterfront is 0.1 miles from the door", "34 min walk to
a park", the 50-minute drive, Elizabeth's police figures (property 24.1, just under the 25.0 limit) and Elizabeth
residents' quotes. Cause: the listing's coordinates were taken as given (`coord_basis = "listing rows agree"`); nothing
compares a coordinate with the listing's own city and ZIP. Fix: geocode from the address, refile under `nj:bayonne`,
rebuild its measures; add a check that a building's point lies in its stated municipality.

**D2. Four blocked apartments whose second site does not show them.** For Bedford Creative 204, 205, 301 and The
Tetris 211, 309 the finding "Zumper lists this address but not this apartment" is the open item "availability". The same
finding is ignored for:

| Apartment | id | What the live-check row says | Already open |
|---|---|---|---|
| 328 Pacific 705 | `trulia:b2798350681:Unit_705:466534192` | "the Zumper address page shows only 2-bedrooms ($2,900 to $4,900). Unit 705 not verified today" | dogs |
| Metropolis Towers 16F | `trulia:466347523` | "Unit 16F is not on the Zumper address page (it shows 2 units, 0 available)" | dogs |
| 509 Martin Luther King Jr Dr 39E | `trulia:466489487` | "Zumper's address page shows only an inactive 2022 listing for another unit"; ZIP differs between text and address | dogs |
| 525 Riverdale Ave 5U | `trulia:466334272` | "Zumper's address page … shows a different apartment here (a 1-bedroom at $2,400), not this studio" | nothing |

The first three have two open items and should not be shown; 5U should carry the asterisk. Cause: the availability item
exists only as a hand-written `asterisk / not_available` verdict; these four got `ok`, and no rule reads "not on the
… page" from a blocked row. Fix: one rule in `rank.py` for "a second site covers the address and omits the unit".

**D3. Residences at The Summit, Danbury: 8 apartments on a stale page with an unproven elevator.**
`b_450dac94fa`: K3-02, K3-23, K4-19, L3-03, M2-07, M4-10, M4-12, M4-22. The Trulia building page was "last modified
2026-08-22" (the open item "listing"). The elevator is "Elevator (Interior Features …)" on that same page only, for a
180-unit complex whose labels name buildings K, L and M; no page gives a height. Beacon Mill Village, Harbor Pointe and
TGM Anchor Point carry the elevator item on the same evidence. With it these are two open items. Cause:
`parsers.multi_building_labels` (`scripts/parsers.py:1185-1201`) fires only when "no label reads above floor 3", so a
complex with fourth-floor labels escapes, although the rule as written in CLAUDE.md asks for "no height of 4+ floors on
any page or record" and a label is elsewhere never a height. Fix: use page and record heights only, or add the building
to `elevator_doubt.csv`.

**D4. Six "apartments" whose label does not identify a real, above-ground apartment.**
- BE, 448 Scotland Rd, Orange: P and F (`trulia:b2783565719:Unit_P:463921266`, `…Unit_F:463921276`). The live-check row
  reads "Unit P (1Bed)", "Unit F (1 Bed with Den)": plan letters, no size, no floor, page 122 days stale. Check 3 (D26)
  named them; they are still shown.
- Appletree Suites, 76 Cottage St, Jersey City: C, E, F (`…Unit_C:2054218531`, `…Unit_E:449348518`,
  `…Unit_F:439160407`) beside 2B, 3B, 4B, 5D, 6D. A letter with no floor digit is a plan row or a ground-level unit;
  none was seen live; shown with no asterisk.
- 630 West 163rd Street 10 (`apartmentlist:p127424223-10`): apartment "10" of 65 in a six-floor building numbered in
  sequence reads as the first floor. No page states the floor; "floor not published" is its only caution.
Cause: `parsers.listing_kind` accepts any short label as a unit; the sibling floor rule needs a removed sibling.

**D5. The page states "elevator" and "Dogs allowed" where they are the open question.**
`site/index.html:2348`: `if(U.elevator&&U.elevator.value==="yes")o.push("elevator")` builds the building row "THE
BUILDING: elevator, washer-dryer in the apartment, gym". It prints for all 96 apartments in 25 buildings whose open
item is the elevator (The Atwater, J Centra Burlington, Kensington Place, Beacon Mill Village, Harbor Pointe and 20
more), a few lines above "* To confirm: the elevator". `site/index.html:2052` prints "Dogs allowed; weight limit not
known yet." in the day row for the 31 apartments in 17 buildings whose dog policy is open (seen on Halstead Norwalk,
under "It is not confirmed that dogs are allowed"). Fix: both lines must read the open item first.

**D6. Twelve neighborhoods say the dog park is far away while their only building has its own.**
Text and "At a glance" against the building's own point "The building has its own dog park":

| Neighborhood | The page says |
|---|---|
| Bogota (The Atwater) | "The nearest dog park is 2.2 miles away."; strip "2.2 miles to the dog park" |
| Burlington (J Centra) | "the dog park 5.7 miles, so both need the car"; "The nearest dog park is a drive, so weekday walks are on the leash." |
| Beacon Falls | "No dog run is nearby, so keep it for weekends." |
| Long Branch | "the dog park is 6.0 miles away"; "No dog run is nearby, so keep it for weekends." |
| Mount Arlington, Dover | "The nearest dog park is a drive, so weekday walks are on the leash." |
| Trumbull, Belleville, Teaneck, Elizabeth, East Rutherford, Weehawken | "The nearest dog park is 2.3 / 1.2 / 2.1 / 2.8 miles away", "A dog run is 0.6 / 0.1 miles from the door" |

Also Maplewood ("The dog park is 2.2 miles away, so you would drive the dog there"; Avalon Maplewood has a pet park),
and in part Danbury, New Rochelle, Orange, Hackensack, Bayonne. Piper's own text says both: "this is the closest to a
dog park, 0.4 miles away" and "The building has its own dog park." Cause: `scripts/build_scene_text.py:57,132` take
`dog_park_m` (the nearest public dog park) and never read `amenities.dog_amenities`. Fix: where every shown building has
its own, say so; otherwise say "some buildings have their own".

### S2

**D7. The Quiet-Street experience contradicts one of its three neighborhoods.** Tagline "A quiet street of houses and
lawns, where you drive to everything"; catch "Almost no restaurants are within a 10-minute walk". Its second
neighborhood card reads "Fairfield has a small center you can walk to, with 5 restaurants and 3 bars within a 10-minute
walk." The one apartment there, Alto Fairfield Metro 402A (1401 Kings Hwy), has 8 restaurants, 5 bars and 36 shops
within 800 m, the train station 0.1 miles away and the motorway 371 m away. With 6 apartments, "100 percent of the
apartments list a garage or covered parking" and "Every building here has a gym" are true and read as statistics of
three buildings.

**D8. Conditions the renter must know that are in the data and not on the page.**
- 8267 Austin St 916, Kew Gardens (`trulia:2098501053`): "Income requirement for this apartment $130,000 yearly
  income." (`facts_batch_5`). Not a disclosure, not a tour question. It is one of the three Walk-Everywhere apartments.
- 948 New York Avenue 2 (`zumper-65782421`): "household income of $104,000+ and 700+ credit".
- Appletree Suites (8 apartments) and Metrovue (201, 7012, 1102): Trulia tags the building "Furnished"
  (`facts_batch_8`). Nothing on the page says so.
Cause: `income_requirement` is carried in `ranked_units.csv` and dropped by `build_page_data.py`; "furnished" is not a
field. Fix: two disclosures.

**D9. "A doorman is at the front door" from a "Concierge" amenity tag.** 87 apartments in 20 buildings (75 Tresser,
Parallel 41, TGM Anchor Point, The Royce at Trumbull, Kensington Place, The Brownstones at Englewood South, Pier
Village, The Walcott and others) have `doorman_text` "Concierge" / "concierge service" and the text "There is a
doorman, which helps with packages", "A doorman is at the front door", "The building has a doorman", "No other building
listed in this neighborhood has a doorman". Several are multi-building garden complexes. Cause: `rank.py:545`,
`build_master.py:330-332` fold `doorman_or_concierge` into `doorman`. Fix: say "concierge" or "front desk" unless the
source says doorman.

**D10. Beacon Falls is shown with no crime figure at all.** `ct:beacon-falls` (5 apartments): every safety field is
null. "Everything shown is already safe" is not established for it. Fix: find the resident-trooper or state police
figure, or say plainly that none exists.

**D11. Walk-Everywhere (3 apartments) overclaims.** "Your parents are about 5 minutes away by car, with no tolls" and
the tagline "your parents are close": true of the two Kew Gardens apartments, false of Bay Ridge (31 minutes; its own
page says "Far enough to plan ahead"). "The typical apartment is about 830 square feet": one apartment publishes a
size. "Only 33 percent of the listings mention parking": one of three. "most households in these neighborhoods do
without a car": the shares are 43 and 49 percent. Cause: medians and percentages of three rows written as tendencies
(`scene_text_years.csv`). Fix: for an experience under about ten apartments, name the apartments instead.

**D12. Old-Neighborhood: "close to your parents" covers Newark.** 29 of its 81 apartments are in Newark, 47 minutes
and a $24 toll away. "Your parents are about 25 minutes away by car, usually with no tolls": 53 percent of the
apartments have no toll. "From Jamaica, the closest neighborhood, the drive is about 3 minutes. The train and bus take
about 65 minutes, so the car is easier." The 65 is the experience's median and reads as Jamaica's (12 minutes).

**D13. "Every apartment here fits what you need."** First tutorial card (`site/index.html:2962`). 209 of 568 have an
open elevator, dog or availability question, and 511 do not publish the floor.

**D14. Experiences that do not fit their neighborhoods, to a lay reader.** Little-City promises "A small downtown to
walk to": Englewood has 0 restaurants within 800 m, Danbury 1, Riverdale 1, Yonkers 2, East Rutherford and Parsippany 3;
its own cards say "Nothing to eat or drink is within a 10-minute walk" (Englewood). Room-to-Breathe ("Bigger apartments
in towns farther out") holds Valley Stream (14 minutes), Bridgeport and East Orange (650 and 705 sq ft against 635 in
Queens). The cut neighborhood Kew Gardens Hills, 7 minutes from her parents, has a page headed "THE LITTLE-CITY
EXPERIENCE". The four override rows in `lifestyle_group_overrides.csv` (Fort Lee, West New York, McGinley Square,
Harlem South) touch no shown neighborhood today.

**D15. The text guards do not read what is published.** See "Guards" below: a conceit, jargon and a false number
written into `site/data.json`, `realtor_lines.csv` or `building_about.csv` pass every checker.

### S3

**D16. "At a glance" and the neighborhood text describe a wider sample than the apartments on the page.** Of 378
number claims in the 78 neighborhood texts, 34 in 21 neighborhoods differ materially from the shown apartments; 12 of
them are in single-building neighborhoods, where "from the door" can only mean that building. Examples: Fairfield "The
supermarket is 0.9 miles away" (0.3); Downtown Jersey City "about 30 restaurants and 2 bars" (66 and 8) and "8 cafés"
(21); White Plains "About 12 restaurants" (2); Bay Ridge "About 29 restaurants" (14); Shelton "The nearest park is about
14 minutes" (6); East Orange "The nearest dog run is 1.8 miles away" (0.5). Bogota's page gives the park as "8 min walk"
and the building as "about 7 minutes". Cause: `check_scene_text.py:22,135,213` requires the neighborhood's frozen area
profile (`traits`), because the strip prints it; `docs/RANKING.md` section 8 says neighborhood figures are over the
shown units. Fix: compute the strip and the text from the shown apartments.

**D17. Parkway Lofts is in Bloomfield and is filed under East Orange** (`b_cbc9a7d36b`, 417, 617, 736). The page tells
her "In East Orange every car parked on the street overnight … needs a permit that costs $150 a year. So look for a
building with its own garage" (both buildings shown there have lots) and shows East Orange's police figures. The `city`
field is wrong on seven more buildings: Avalon Maplewood "Newark", Third & Valley "East Orange", Avalon Wayne "Lincoln
Park", RiversEdge and RiverParc "West New York", 55 Monroe Place "Belleville", Harbor Pointe (D1).

**D18. Parking stated more firmly than the evidence.** J Centra Burlington: "Garage parking, with the fee not
published." The evidence: "In addition to the surface parking, there is optional garage parking". The Atwater: "A space
in the building's lot costs $75 a month", receipt "Parking: confirmed"; the source is "a resident review dated
2025-05-01", and the receipt prints it as "regular (first come) , per a resident review dated 2025-05-0 $75". The
experience points "N percent of the apartments list a garage or covered parking" count such rows.

**D19. Continuum, White Plains: "Floors in the building: 2".** `b_144b021ca5`, `amenities.building_floors = 2`, basis
"amenities_page"; its shown apartments are on floors 3 to 16 (`site/index.html:2393` prints the field).

**D20. "Up to" dropped from nine offers.** Among them: "The listing offers 2 months free." where the page says "up to 2 months free
off base rent" (EDGE 224, 322G, 410, 522G), "The listing advertises 1 month of free rent." for "Up to 1 MONTH FREE"
(Residences at The Summit L3-03, M4-12), and Bay One BAY-0803. Check 3's D18, still open.

**D21. The map counts 89 neighborhoods, the page 78.** Chips "Little-City 24, Old-Neighborhood 29, Walk-Everywhere 4"
against 23, 21 and 2 on the experience pages. The 11 extra are cut neighborhoods that keep full pages ("None to tour",
"Nothing to tour here yet.") with About text, strip and an avoid card.

**D22. Five removals rest on a wrong reading of the unit number.** The Grove Somerset 2141, 3172, 4149, 4171 were
removed as "first-floor" under a building-floor-unit reading. The complex has 384 units and labels 1116 to 4186: floor
then a three-digit unit (four floors of 96) fits, and `scripts/parsers.py:1191` itself says "The Grove Somerset 4186 is
floor 4". Only 1116, 1118 and 1174 read as floor 1. With these back, Franklin is not a single-apartment neighborhood
and unit 2205 is not cut as thin. Prospect Place 01-16C was removed as first-floor; "01-16C" beside "02-229" reads as
tower 01, floor 16.

**D23. Thin rule.** It recomputes. Two of the ten kept apartments were never re-read (Bay Ridge 9949 Shore Rd 502;
East Harlem 315 E 108th St 6G); CLAUDE.md still says "well attested (seen live, nothing open)" one paragraph above the
rule that removed "seen live". The Lofts at Garwood GAR2R-08 (clean, seen live, score 55.1) was cut only because the 124
new entries raised its experience's median to 56.4. The other eight kept apartments hold on their evidence.

### S4

**D24. Internal language behind "See why" and in questions.** `confirm.why` is printed verbatim: "The evidence pass
could not confirm an elevator for this building: not stated on the building site or Apartment List (Zumper harvest row
says elevator yes) |" (The Atwater, 8), "A Google review (seen in a search summary, docs/PENDING_FIXES.md) claims
units here were advertised with no occupancy permit. Second-hand, so one open fact" (Regency on Hudson, 7), "Listing
page blocked today; stored value (dogs yes) not re-read" (Metropolis Towers 16F), "the site then refused us" (Vermella
Harrison), "(unit prefixes BM, PA, PU, SH)". "unit" is in 81 questions ("Is this unit still available, and at this
price?") and 521 disclosure lines; "net-effective rent" labels 15 disclosures; "Listing sites disagree" 15 lines.

**D25. Template sentences that read as errors or as cute.** "An one-bedroom of 784 sq ft" (`index.html:2002`); "The
car sleeps in a garage, fee not known yet." and "Where the car sleeps" (`2015-2017`, a construction the scene checker
bans); "0 hectares of woods within a 10-minute walk." (`2050`); "Asian Food is a 9-minute walk." (a shop's name);
"LOCAL RULES Ask / not found, ask"; the neighborhood name "Milford city (balance)"; the building "416 Highland Ave -
312" with the apartment label "1 Bed". In the written text: "The nearest dog park is a drive, so weekday walks are on
the leash." (5 neighborhoods), "Dogs are allowed up to a weight limit, so choose the breed with care." (39) and "Ask
for the dog weight limit in pounds before you choose a puppy." (30), which assume she has no dog yet. Five neighborhood leads still speak of one apartment where several are shown: "The
apartment in East Brunswick is large, about 850 square feet." (8 shown), Trumbull (5), Mount Arlington (3), Madison
(3), Brookfield (2). Parsippany's "good for you" line is "3 restaurants are within a 10-minute walk." under the catch
"Almost nothing to eat or drink is within a 10-minute walk."

**D26. "Compared to staying in Queens" on Queens neighborhoods.** Kew Gardens: "Compared to staying in Queens, the
monthly cost goes up." Old-Neighborhood: "Compared to staying in Queens, the typical apartment is bigger."

**D27. Two safety wordings.** The prose uses "one of the safest spots on the whole list" (14 neighborhoods, exactly the
14 lowest violent rates). The badge says "Among the safest on the list" (`index.html:1655, 2144`).

**D28. Neighborhood cards cut mid-sentence.** The two-line clamp cuts about 60 of the 78 cards at 390 px: "In
Bloomfield the daily things are close: a dog park, the supermarket and the train are al…". Listed in SITE_NOTES "Left
for later"; still there.

**D29. Ratings.** 26 buildings have `searched: false` and a rating. 66 ratings are labelled "Apartments.com", 23
"Google", 2 "Yelp", `seen_via: "search result display"`: figures read from search results for sites the project may
not open.

**D30. Elevator on a listing-site tag in other multi-building complexes, treated as settled.** 1 Kennedy Flats, Pier
Village, Admirals Cove, Fort Hill Peekskill, Halstead Parsippany, The Confluence, The Brunswick, Prospect Place. Most
read as four- or five-floor buildings; none has a page that says so. Same question as D3, lower risk.

## A5. Experience assignment

Fits: Walk-Everywhere (Kew Gardens, Bay Ridge), Fresh-Start (all six: new buildings near water), most of
Old-Neighborhood except Newark, most of Room-to-Breathe. Misfits: D7 (Fairfield in Quiet-Street), D14. Journal Square,
where 47 percent of households have no car, sits in Little-City ("a garage for the car").

## Guards: what the checkers reject and what slips through

In a shadow copy of the project (scripts copied, data linked, the four text inputs and `site/data.json` copied):

| Injected | Where | Result |
|---|---|---|
| "The dog walks you to the river each morning." | neighborhood `host_intro` | rejected ("a thing acting on 'you'") |
| "Every unit here passed the gate, and the all-in is under the cap." | neighborhood `host_intro` | rejected ('unit', 'all-in', 'gate') |
| "About 99 restaurants are within a 10-minute walk." | neighborhood `host_intro` | rejected ("number '99' has no evidence item") |
| jargon, wrong number, "Year", crime, "Mostly Hispanic families live here", "Ninety-nine" | scene CSVs | all rejected |
| "The lawns keep their own counsel." (a conceit not on the list) | experience `catch` | **passes** |
| "The river tucks the town in at night." | neighborhood `host_intro` | fails only on the word count |
| "Every building here has a doorman and a pool." | neighborhood `scene` | fails only on the word count |
| "These listings were not checked again this year." | neighborhood `scene` | **passes** |
| "No building here has a dog park." (Bogota, whose building has one) | neighborhood `scene` | **passes** |
| conceit / "This unit passed every gate, and the all-in is under the cap." / "about 1,400 square feet … $1,200 a month" | `realtor_lines.csv` `host_line` | **all three pass** `test_realtor_lines.py`, `check_scene_text.py` and `verify_all.py --quick` |
| conceit / "Verified by a live check on the scorecard." / "a doorman, and garage parking costs $20 a month" | `building_about.csv` | **all three pass** |
| the same three kinds written straight into `site/data.json` (apartment line, neighborhood lead, experience tagline, building text) | the published data | **all pass** every checker |

`check_scene_text.py` reads the two scene CSVs only. `test_realtor_lines.py` regenerates text and tests the generator;
it never reads the text on disk or in `site/data.json`. `verify_all.py` compares ids. Nothing checks the sentences the
template writes (D5, D25). Fix: one checker that walks every prose field of `site/data.json` (and the template's
sentence table) through `check_plain` and the number rule.

## Tests

At 04:04 UTC, on the repo as another agent had left it: `test_parsers.py` 259 pass; `test_rules.py` 449 pass;
`test_page_data_extras.py`, `test_realtor_lines.py`, `test_shortlist_tools.py`, `test_lib_guard.py`,
`test_verify_all.py` pass; `check_scene_text.py` passes (141 rows). `verify_all.py`: 15 passed, **4 failed**:
`test_rules.py --data` (3 units with an asterisk verdict shown without one: Clifton & Co. CCO-475, CCO-577 and
`p9991-741s01R-0302`), `check_registry.py` (3 shown units with no verdict: Piper 6008, Clifton & Co. CCO-571,
Kensington Place 2339), "shown ids: ranked_units.csv = site/data.json" (6 and 32 ids differ), "every shown unit has a
current verdict". These come from the run in progress, not from the frozen state.

## What I could not check

- Whether any listing is live now, beyond what `live_check_batch_20.csv` records. 292 shown apartments were never
  re-read at the freeze.
- Whether Metropolis Towers (270 Luis M Marin Blvd, 16F) is a co-op. No evidence row addresses it; the listing type is
  "unknown" and the page was blocked. It needs one look before it is shown again.
- The true floor of the 511 apartments with no published floor; every numbering convention above is a reading.
- Harbor Pointe's real measures (D1): no geocoder was used.
- Resident quotes line by line (894 on the page), the outside descriptions, local-rule dollar figures against
  `local_rules*.csv`, the avoid cards (35) and held apartments (14).
- The map, My list and compare, the tutorial beyond its first card, and any page width other than 390 px.
- The 215 apartments outside the evidence sample were covered by scans (blocked rows, changed prices, unit labels,
  dog size wording, cost lines), not read in full.
