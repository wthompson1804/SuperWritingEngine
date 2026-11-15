# Independent check 2: the shown list after the repairs

Checked 2026-11-15, 23:05 to 23:40 UTC, by an agent that did not write the pipeline. No pipeline script or data file
was edited and nothing was committed. Per-field comparisons for the 30-unit field check are in
`data/evidence/independent_check_2_units.csv` (480 rows).

**Verdict: I would not trust the shown list as it stands.** Rent, beds, size, unit label and availability date are
faithful to the source pages. The gate facts are not: reading every evidence row for every shown building turns up
**37 shown units that should come off** (a probable walk-up, a co-op, listings nobody has read on an allowed page,
listings the checker itself called unverified, dog policies that are "case by case", wrong-building warnings) and
**45 more that need an asterisk they do not carry** (price only valid on a 15 to 24-month lease, elevator not
established, floor-plan rows with no unit available). That is 82 of 332 shown units, one in four. The cause is the
same in almost every case: the evidence agents wrote the doubt down in plain words, and the rules read only a short
list of exact phrases and only three kinds of open fact.

## What was checked, and against which files

The pipeline was edited and re-run twice while this check ran (shown went 346 → 332 when the co-op rule landed at
23:16 UTC). Everything below is measured on a frozen copy taken at 23:16:39 UTC:
`ranked_units.csv` md5 `bb4fc9678cc648e7c101c3681df55cfb` (980 ranked, **332 shown** in 251 buildings, 190 with an
asterisk), `unit_exclusions.csv` md5 `c5e43690b35339aed4160ff3d3d76206` (179 rows). At 23:31 UTC the live files still
matched that copy. `site/data.json` was built at 23:16:34 UTC from the same run and holds the same 332 units: it is
not stale.

## Counts

| | |
|---|---|
| Shown units read against their evidence | 332 (251 buildings; every `live_check`, `confirm`, `facts`, `items` row and the NYC and non-NYC records for each) |
| Verdict "must remove" | 37 units |
| Verdict "should carry an asterisk it lacks" | 45 units |
| Flagged but fine as shown | 5 units |
| Shown rows that are a floor plan or have no unit number | 29 (20 Trulia floor-plan rows, 9 others) |
| Exclusions spot-checked for false positives | 30 of 179: 29 justified, 1 too broad |
| Field check | 30 units × 16 fields = 480: 250 agree, 16 disagree, 214 not checkable; 8 units have at least one disagreement |
| Shown units whose all-in counts pet rent / parking / building fees as $0 because unknown | 185 / 259 / 247 (143 have all three unknown) |
| Shown units at $2,950 or more all-in with pet rent unknown | 19 |
| Defects | 21: 7 change what should be shown, 3 hide a condition, 6 give a wrong number, 5 minor |

## Defects, most serious first

Severity: **S1** a unit is shown that fails a gate or is not a verified, available listing. **S2** a shown unit hides a
condition the renter must know. **S3** a number on the page is wrong. **S4** minor.

### D1 (S1). Listings the checker called unverified, stale or without any available unit are shown (15 remove, 13 need an asterisk)

The live-check notes say "treat as unverified", "last modified seventeen months ago", "0 available units", "no unit at
that price now". None of those phrases is in `avoid.py:30-37` (`NOT_REAL`, `INELIGIBLE`), and `rank.py:137` judges age
only from `listing_age_days`, which is blank for every building-page row (all 28 units here). `rank.py:137` drops "no
unit or building named" only when both are blank, so a floor plan with a building name counts as a unit. The only
open item these rows carry is "floor".

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `rc:trulia:b2758091490:plan-1_bedroom_with_office:453577716` | brookview apts, Shelton CT | (none) | floor | 'Floor-plan level only ... THE PAGE WAS LAST MODIFIED 2025-06-09, seventeen months ago: treat as unverified. The description is a placeholder.' | live_check_batch_13 | **must remove** |
| `rc:trulia:b2737296301:plan-Kentfield:456056406` | Ten Trumbull, Trumbull CT | (none) | floor | 'Floor-plan level only ... THE TRULIA PAGE WAS LAST MODIFIED 2025-08-18, fifteen months ago: treat as unverified. The building's own floor-plans page shows no prices'. | live_check_batch_13 | **must remove** |
| `trulia:b2750793263:plan-1_bedroom_with_balcony:456579004` | 1180 Midland, Bronxville NY | (none) | floor | 'Floor-plan level only: the page lists plans and 0 available units'; 'Trulia page last modified 2025-10-14, 13 months before the check; treat price and availability as unverified'. | live_check_batch_11; facts_batch_11 (listing_stale) | **must remove** |
| `rc:trulia:b1037833154:plan-JR_1_BEDROOM:2079990608` | The Regency, West Haven CT | (none) | floor | 'Floor-plan level only ... THE PAGE WAS LAST MODIFIED 2025-12-19, eleven months ago: treat as unverified.' | live_check_batch_13 | **must remove** |
| `rc:trulia:b2766142177:Unit_200:459054138` | Vista Apartments, Shelton CT | 200 | floor | 'THE PAGE WAS LAST MODIFIED 2025-12-16, eleven months ago, so price and availability are not verified'; floor 2 is also only a guess. Two open items. | live_check_batch_13; confirm_batch_13 | **must remove** |
| `trulia:b1001477969:plan-Studios:442025671` | The Sterling, Fort Lee NJ | (none) | floor | 'Floor-plan level only and stale: the page shows $2,500/mo, one plan (no price or date of its own) and 0 available units of 128. Trulia page last modified 2026-05-15'. | live_check_batch_14 | **must remove** |
| `rc:trulia:b1002216379:plan-Birmingham_Brighton:2066684744` | Broadmoor Apartments, Hamden CT | (none) | floor | 'LISTING RECORD LAST MODIFIED 2026-01-27 (about 10 months ago): treat as unverified until the office confirms'; elevator 'listed for the complex; whether every building has one is not stated'; floor unknown. | live_check_batch_12; confirm_batch_12 | **must remove** |
| `rc:trulia:b1002216379:Unit_18:459993147` | Broadmoor Apartments, Hamden CT | 18 | floor | 'LISTING RECORD LAST MODIFIED 2026-01-27 (about 10 months ago): treat as unverified until the office confirms'; elevator 'listed for the complex; whether every building has one is not stated'; floor unknown. | live_check_batch_12; confirm_batch_12 | **must remove** |
| `apartmentlist:p33489-ignore-me-i-am-fake-4259777` | The Cove, Westfield NJ | 1 bed, 1 bath, $2575 | floor | 'Floor-plan level only, no unit number and no availability date. Apartment List last updated this entry on 2024-02-29 [2024-02-16]. Availability by Dec 15 cannot be confirmed from either page.' Two rows for one floor plan; one listing_id contains 'ignore-me-i-am-fake'. | live_check_batch_10 | **must remove** |
| `apartmentlist:p33489-u36308196` | The Cove, Westfield NJ | 1 Bed - 1 Bath | floor | 'Floor-plan level only, no unit number and no availability date. Apartment List last updated this entry on 2024-02-29 [2024-02-16]. Availability by Dec 15 cannot be confirmed from either page.' Two rows for one floor plan; one listing_id contains 'ignore-me-i-am-fake'. | live_check_batch_10 | **must remove** |
| `rn:fairfield-metro-at-glen-cove-glen-cove:b1045082049:plan-S7_North_FR_Studio:2066754063` | Fairfield Metro at Glen Cove, Glen Cove NY | (none) | floor | 'Floor-plan level only ... 0 available units of 367 ... The building's own page shows only One Bedroom from $2,950/mo and no studio price, so the studio price is not confirmed by the owner's site.' | live_check_batch_16 | **must remove** |
| `rn:fairfield-metro-at-glen-cove-glen-cove:b1045082049:plan-S3_South_Studio:465141354` | Fairfield Metro at Glen Cove, Glen Cove NY | (none) | floor | 'Floor-plan level only ... 0 available units of 367 ... The building's own page shows only One Bedroom from $2,950/mo and no studio price, so the studio price is not confirmed by the owner's site.' | live_check_batch_16 | **must remove** |
| `rc:trulia:b2750806649:plan-113:454188796` | 165 Richards Street, West Haven CT | (none) | floor | 'The stored row was $2,100 with no unit. Nothing is at $2,100 now: the nearest 1-bedrooms are Unit 112 at $2,095'; 'Unit 112: my reading is floor 1'; 'Trulia page last modified 2025-12-08'. | live_check_batch_13; confirm_batch_13 | **must remove** |
| `trulia:b2737454290:plan-1-2B:452657694` | Park Place Towers, Peekskill NY | (none) | floor | 'Stored row had no unit number ($2425). No unit at that price now; nearest is Unit 3I at $2438. Trulia page last modified 2026-04-13.' Both shown rows (stored $2,425 and $2,683) now carry $2,438. | live_check_batch_11 | **must remove** |
| `trulia:b2737454290:plan-1-8B:452657838` | Park Place Towers, Peekskill NY | (none) | floor | 'Stored row had no unit number ($2425). No unit at that price now; nearest is Unit 3I at $2438. Trulia page last modified 2026-04-13.' Both shown rows (stored $2,425 and $2,683) now carry $2,438. | live_check_batch_11 | **must remove** |

Floor-plan rows and stale rows that are probably real but cannot be shown as an available unit without saying so:

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `rc:trulia:b2798446905:plan-410:466473123` | 1269 Main Street, Bridgeport CT | (none) | floor | 'Floor-plan level only ... the page lists 0 available units, so no unit or date can be checked ... Confirm by phone.' Floor asterisk only. | live_check_batch_12 | **should carry asterisk it lacks (availability)** |
| `rc:trulia:b1005185522:plan-2J:464638908` | The Siena, Bridgeport CT | (none) | floor | 'Floor-plan level only ... 0 available units listed'; 'Free month is tied to an 18-month term'. | live_check_batch_12; facts_batch_12 | **should carry asterisk it lacks (availability, lease term)** |
| `rc:trulia:b2795130832:plan-1br:465130674` | 301 Bridgeport Ave, Shelton CT | (none) | floor | 'Floor-plan level only: the page lists a plan price marked Available Now and no unit ... Confirm by phone. Page last modified 2026-09-09.' | live_check_batch_13 | **should carry asterisk it lacks (availability)** |
| `rc:trulia:b2734028645:plan-Grand_Denali:456056380` | The Mark, Fairfield County ~ Resort-Inspired Luxury Living, Shelton CT | (none) | floor | 'Floor-plan level only: ... no unit, so no unit, floor or date can be checked. Confirm by phone.' Two plans shown as two units. | live_check_batch_13 | **should carry asterisk it lacks (availability)** |
| `rc:trulia:b2734028645:plan-Grand_Bryce:456056393` | The Mark, Fairfield County ~ Resort-Inspired Luxury Living, Shelton CT | (none) | floor | 'Floor-plan level only: ... no unit, so no unit, floor or date can be checked. Confirm by phone.' Two plans shown as two units. | live_check_batch_13 | **should carry asterisk it lacks (availability)** |
| `rc:trulia:b2773044312:plan-308:463098083` | The Riverhouse, Stamford CT | (none) | floor | Plan-level rows ('no unit listed'); 'THE LISTED PRICE IS NET-EFFECTIVE ... 3 months free on 18 month leases' (rent asterisk present). | live_check_batch_13 | **should carry asterisk it lacks (availability)** |
| `rc:trulia:b2773044312:plan-305:466542171` | The Riverhouse, Stamford CT | (none) | floor | Plan-level rows ('no unit listed'); 'THE LISTED PRICE IS NET-EFFECTIVE ... 3 months free on 18 month leases' (rent asterisk present). | live_check_batch_13 | **should carry asterisk it lacks (availability)** |
| `trulia:b2792481957:plan-Studio:464435588` | Willett Point, Port Chester NY | (none) | floor | 'Floor-plan level only: the page lists plans and 0 available units ... Confirm by phone.' The studio plan has no price of its own. | live_check_batch_11 | **should carry asterisk it lacks (availability)** |
| `rn:fairfield-estates-at-woodmere-woodmere:b1001489336:plan-The_Atlantic_I_Studio:448953886` | Fairfield Estates at Woodmere, Woodmere NY | (none) | floor | 'Floor-plan level only: ... 0 available units of 87'. | live_check_batch_16 | **should carry asterisk it lacks (availability)** |
| `apartmentlist:p263791-u49220319` | Harrison Somerset, Somerset NJ | B, H, K, R - Small-1 | floor | 'Floor-plan level: ... No unit number, floor or date.' | live_check_batch_14 | **should carry asterisk it lacks (availability)** |
| `apartmentlist:p263791-u49220292` | Harrison Somerset, Somerset NJ | G - Small-1 | floor | 'Floor-plan level: ... No unit number, floor or date.' | live_check_batch_14 | **should carry asterisk it lacks (availability)** |
| `apartmentlist:p7630984-4bec8063-f064-11ee-8ab6-12de4bf481cd` | City Trust Collection: Arcade Apartments., Bridgeport CT | 302 | nothing to confirm | 'Apartment List's availability date is stale (2025-06-01) and the description still says FIRST MONTH FREE -- sign by June 30'; second row: 'probably the same apartment as unit 302 advertised twice'. | live_check_batch_12 | **should carry asterisk it lacks (stale; duplicate)** |
| `apartmentlist:p7630984-8dc0ef5a-1dcf-425e-8486-1d575c05d1dc` | City Trust Collection: Arcade Apartments., Bridgeport CT | 1 bed, 1 bath, $1675 | floor | 'Apartment List's availability date is stale (2025-06-01) and the description still says FIRST MONTH FREE -- sign by June 30'; second row: 'probably the same apartment as unit 302 advertised twice'. | live_check_batch_12 | **should carry asterisk it lacks (stale; duplicate)** |

### D2 (S1). Units nobody has read on an allowed page are shown with only a "live check" asterisk (6 units)

For these the evidence pass confirmed nothing: elevator, dogs and weight limit are all "unconfirmed" and the listing
page was never opened. `build_master.py:447` skips `unconfirmed` rows, so the harvester's own values survive as
`amenities_page` (elevator) and `stated` (dogs); `rank.py:152` treats only basis `inferred` or blank as open. Three
unknown gate facts plus no live check are counted as one open item. Surfview Towers' price was taken from a search
card, which working rule 2 forbids. Five of the six come from Zillow pages, which are off limits, so they can never
be verified by this pipeline.

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `rn:surfview-towers-listing-address-withheld-long-beach:466385354` | Surfview Towers (listing, address withheld), Long Beach NY | (none) | live check | 'The harvest only ever read the search card for this listing (address withheld), so the price was never verified on the listing page'; elevator, floor, dogs, weight all 'unknown: listing page never read'. | live_check_batch_16; confirm_batch_16 | **must remove** |
| `region_mid_hudson:z:85bae615f1e7` | The North Court Apartments, Middletown NY | 406 | live check | 'Only link is a Zillow page (off limits). No own site found'; elevator, dogs, weight 'unconfirmed'; the evidence rows are for units 206/208, the shown units are 406/408. | live_check_batch_10; confirm_batch_10; facts_batch_10 (not_found) | **must remove** |
| `region_mid_hudson:z:1fc231c2ebaf` | The North Court Apartments, Middletown NY | 408 | live check | 'Only link is a Zillow page (off limits). No own site found'; elevator, dogs, weight 'unconfirmed'; the evidence rows are for units 206/208, the shown units are 406/408. | live_check_batch_10; confirm_batch_10; facts_batch_10 (not_found) | **must remove** |
| `region_mid_hudson:z:122e516bb694` | Trail Link Collective, New Paltz NY | 303 | live check | 'Only link is a Zillow page (off limits). Own site ... Cloudflare challenge (403)'; elevator, dogs, weight 'unconfirmed'; 'no allowed page read for this building'. | live_check_batch_10; confirm_batch_10; facts_batch_10 | **must remove** |
| `region_mid_hudson:z:9ec7a17b9ad4` | Trail Link Collective, New Paltz NY | 307 | live check | 'Only link is a Zillow page (off limits). Own site ... Cloudflare challenge (403)'; elevator, dogs, weight 'unconfirmed'; 'no allowed page read for this building'. | live_check_batch_10; confirm_batch_10; facts_batch_10 | **must remove** |
| `region_mid_hudson:z:dcd0e17e74e0` | Lagrange Farms, Poughkeepsie NY | 303 | live check | 'lagrangefarms.com says Launching Soon with no units ... No allowed copy of unit 303 found'; elevator 'unconfirmed'; dogs 'Zumper building data only'; building has 3 floors. | live_check_batch_10; confirm_batch_10 | **must remove** |

### D3 (S1). "Dogs explicitly allowed" is not enforced (6 remove, 5 need an asterisk)

"Pets upon approval", "case by case", "small pets with landlord approval; dogs not named" and "pets allowed, species
not stated" all end up as `dogs_allowed = yes`. The confirm rows carrying those words have status `unconfirmed` and
are skipped, leaving the listing site's structured pet card as the value; `rank.py:158` opens the dog fact only when
the value is not "yes".

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `trulia:2056687577` | 260 Beach 81st St, Far Rockaway NY | 4 | floor | 'Description: Pets upon approval (approval is case by case)'; elevator 'not stated on the listing'; floor 'unknown (unit is listed as 4)'. Three open items, shown with one. | confirm_batch_17 | **must remove** |
| `trulia:466197377` | 7914 Rockaway Beach Blvd, Far Rockaway NY | 2F | floor | 'Pets Considered Only on a Case by case basis' (condo unit, The Nautilus); floor 2 is a guess. Two open items. | confirm_batch_17; facts_batch_17 (dog_policy_condition) | **must remove** |
| `rn:25-west-broadway-condo-long-beach:2069636201` | 25 West Broadway (condo), Long Beach NY | 204 | floor | 'Condo unit; Pets considered on a case-by-case basis'; dogs_allowed 'case by case [unconfirmed]'; floor 2 is a guess. | live_check_batch_10; confirm_batch_10 | **must remove** |
| `trulia:31977450` | 63-60 102nd St, Rego Park NY | D-8 | nothing to confirm | 'small pets with landlord approval; dogs not named. Openigloo's building summary says it is not pet-friendly'. Shown with nothing to confirm. | confirm_batch_4 | **must remove** |
| `trulia:2068977818` | 142-38 37th Ave, Flushing NY | 8E | nothing to confirm | 'small pets only; dogs not named in the description' ('Small pets allowed.'). Shown with nothing to confirm. Also furnished, condo: '$300 building application fee + $150 background check'. | confirm_batch_4; live_check_batch_4 | **should carry asterisk it lacks (dogs)** |
| `zumper-65363335` | 3333 Broadway, New York NY | (none) | floor | 'yes (pets allowed; species and size not stated)' unconfirmed; 'building page, studio floor plan (no unit number) ... floor cannot be read'. Two open items. | confirm_batch_5; live_check_batch_5 | **must remove** |
| `zumper-65769041` | 9508 65th Rd #A3, Rego Park, NY 11374, USA, New York NY | A3 | floor | 'Galaxy Tower condo ... page data lists a $3,400 Moveinfee ... low price for a 1BR: verify'; dogs 'per Zumper policy block ... condo, owner's description silent' unconfirmed; floor not stated. | live_check_batch_4; confirm_batch_4 | **must remove** |

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `apartmentlist:p473818-344` | Third & Valley, East Orange NJ | 344 | nothing to confirm | 'yes on Apartment List (Bozzuto feed)' against 'no on Trulia's building page' ('Dogs: Not allowed'); own site not readable. Unit 222 also has a guessed floor. | confirm_batch_3 | **should carry asterisk it lacks (dogs)** |
| `apartmentlist:p473818-222` | Third & Valley, East Orange NJ | 222 | floor | 'yes on Apartment List (Bozzuto feed)' against 'no on Trulia's building page' ('Dogs: Not allowed'); own site not readable. Unit 222 also has a guessed floor. | confirm_batch_3 | **should carry asterisk it lacks (dogs)** |
| `apartmentlist:p10919258-2M` | 98-76 Queens Blvd, Queens NY | 2M | floor | dogs 'yes per Apartment List pet data; no policy text' unconfirmed; floor 2 is a guess. Two open items; rent $1,663 is also low for the area. | confirm_batch_4 | **should carry asterisk it lacks (dogs)** |
| `trulia:2084734385` | 13324 Sanford Ave, Flushing NY | 2D | floor | dogs 'yes per Zumper policy block; nothing in the owner's description' ('Contact for more information on pet policy'); elevator not stated on either listing; floor 2 guess. | confirm_batch_4 | **should carry asterisk it lacks (dogs)** |

### D4 (S1). A probable walk-up is shown with the elevator "confirmed" (1 unit)

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `trulia:2069115016` | 2561 Bedford Ave, Brooklyn NY | 3B | nothing to confirm | DOB device list for the lot: 'Accessibility Lift/Active=1', active elevators 0; PLUTO: 4 floors, 8 units, built 1910; checker: 'the listing never mentions an elevator'. Third-floor unit in a probable walk-up. | nyc_records.csv (dob_elevator_devices_active); facts_batch_3 (building_note); confirm_batch_3 (elevator 'confirmed' from the PLUTO class alone) | **must remove** |

Two causes. `confirm_batch_3` marked the elevator `confirmed` on the strength of the PLUTO class alone, and
`build_master.py` takes the row's status at face value (a class code is an official record at best).
`nyc_building_records.py:589` sets `has_dob_elevator_device` when the lot has any device row, so an accessibility
lift counts; the correct figure, active passenger elevators = 0 (`nyc_building_records.py:479`), is computed and never
used by a gate. Three other shown NYC units have no active elevator on record, but their listings state one and the
record is missing or belongs to another lot (405 W 206th St 713E, 5 Stuyvesant Pl 4F, 12333 83rd Ave 3203).

### D5 (S1). The co-op rule added tonight has a dead pattern (1 unit, and condos are not covered)

`avoid.py:48`: `COOP = re.compile(r"\\bco-?op\\b|board approval|...")`. Inside a raw string `\\b` is a literal
backslash followed by "b", not a word boundary, so the first alternative can never match. The rule works only when
the text also says "board approval", "tenants corp" or "owners corp", or the lot is class D4.

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `apartmentlist:p127519823-4D` | 8300 Boulevard E, North Bergen NJ | 4D | nothing to confirm | 'This is a single co-op unit in Woodcliff Gardens offered by an individual lister, not a managed rental: a co-op board normally has to approve a tenant and sets the pet rules. The price is low for the description ... verify the listing'; dogs 'yes (listing tag only)' unconfirmed. Live page tonight: 'This oversized 1 bedroom co-op'. | live_check_batch_15; confirm_batch_15; facts_batch_15 | **must remove** |

Condo units rented by their owners are not covered by the rule at all: 11 shown units sit in lots of class R4 or RM,
and the evidence for several mentions a building application ("$300 building application fee + $150 background
check" at 142-38 37th Ave 8E; "$3,400 Moveinfee" at 9508 65th Rd A3). The one condo that was removed (142 Main St,
Mineola) went only because its text said "approval by board".

### D6 (S1). Wrong-building, ownership and "verify the lister" warnings are ignored (3 remove, 1 asterisk)

`listing_warning` reaches the master table (241 W 101st St has it) but `rank.py` never reads the column;
`address_mismatch` is not mapped; "ask which building", "Housing Authority" and "verify the lister" are not in
`NOT_REAL`. 50 Washington St's elevator is "confirmed" from a different listing at an address the description
contradicts.

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `trulia:466593980` | 50 Washington St, East Orange NJ | 11E | nothing to confirm | 'The description opens Welcome to 55 Washington Street in East Orange! while the listing address is 50 Washington St: ask which building'; elevator 'not mentioned on the Trulia unit page'; floor unknown. Shown with nothing to confirm. | live_check_batch_14; confirm_batch_14; facts_batch_14 (address_mismatch) | **must remove** |
| `trulia:466390285` | 241 W  101st St, New York NY | 2S | floor | 'City lot data lists the owner of 241 West 101 Street as NYC Housing Authority: check that this market-rate listing is at this address'; elevator 'not stated on the listing'; floor 2 is a guess. | live_check_batch_17; confirm_batch_17; facts_batch_17 (listing_warning) | **must remove** |
| `zumper-65701406` | 9060 Palisade Ave #D710, North Bergen, NJ 07047, USA, North Bergen NJ | D710 | nothing to confirm | 'CAUTION: $1,699 is far below the same page's North Bergen 1-bed median ($2,500) for a doorman/pool building: verify the lister before contact'. Condo unit. Shown with nothing to confirm. | live_check_batch_2 | **should carry asterisk it lacks (listing real?)** |
| `apartmentlist:p75976018-1-1` | 145 Goldsborough Dr, Bayonne NJ | 1-1 | floor | 'private lister via Avail feed ... page data leasing_fee = 2795 (a fee equal to one month's rent)'; floor 'not stated (unit label 1-1; sibling units are 1-2, 2-1, 2-2 ...)' which reads as floor 1. | live_check_batch_1; confirm_batch_1; facts_batch_1 | **must remove** |

### D7 (S1). Two open facts shown as one: elevator only in some buildings, or an age-restricted community not ruled out (5 units)

`rank.py:152` accepts basis `amenities_page` as settled even where the confirm row says "select buildings only" or
"amenity tag only"; the 55+ note at 1515 Route 10 does not match `INELIGIBLE` (`avoid.py:35`), which needs "55+
community", "55+ only" or similar.

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `apartmentlist:p72935-A2839-5-02E` | Spinnaker Wharf Apartments, Milford city CT | 5-02E | floor | elevator 'select buildings only [unconfirmed]' ('*Elevator Access ... Additional features vary by unit'); floor unknown. Two open items. | confirm_batch_7 | **must remove** |
| `apartmentlist:p372060-50-123` | The Grove Somerset, Somerset NJ | 2205 | floor | elevator 'only in some buildings [unconfirmed]' ('Elevator access in select buildings'); floor unknown ('4-digit numbers look like building-floor-unit'). | confirm_batch_14 | **must remove** |
| `apartmentlist:p46969315-OLD-A5-232` | 99 Bridge, Old Bridge NJ | 232 | floor | elevator 'yes (Apartment List amenity tag only) [unconfirmed]'; floor 'My reading: floor 2 ... own site is blocked'. Two open items. | confirm_batch_15 | **must remove** |
| `apartmentlist:p37450248-1-219` | The District at 15Fifteen, Parsippany-Troy Hills NJ | 1-219 | floor | 'One of the three communities here (Mason East) is 55+: confirm which community this unit is in'; floor unknown. Two open items. | live_check_batch_9; facts_batch_9 (age_restriction) | **must remove** |
| `apartmentlist:p37450248-1-234` | The District at 15Fifteen, Parsippany-Troy Hills NJ | 1-234 | floor | 'One of the three communities here (Mason East) is 55+: confirm which community this unit is in'; floor unknown. Two open items. | live_check_batch_9; facts_batch_9 (age_restriction) | **must remove** |

### D8 (S2). The price is only valid on a 15 to 24-month lease, and the page does not say so (15 units)

No rule looks at the lease term. `build_master.py:318` maps only facts named `lease_terms*`, so
`lease_term_of_listed_price`, `lease_term_priced` and `price_basis` are dropped, and `rent_terms.py` does not read the
live-check notes. `rent_lease_months` is blank for Scribe, The Asher and The Leaf and says 12 for both Avalon units.
Avalon Somerville is the measurable case: $2,340 is the 20-month price, the 12-month price is $2,430.

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `rc:sightmap:scribe:508` | Scribe, Norwalk CT | 508 | nothing to confirm | 'Price is for a 24 Months lease'; fact lease_term_of_listed_price = 24 months. | live_check_batch_12; facts_batch_12 | **should carry asterisk it lacks (lease term)** |
| `rc:sightmap:scribe:446` | Scribe, Norwalk CT | 446 | nothing to confirm | 'Price is for a 24 Months lease'; fact lease_term_of_listed_price = 24 months. | live_check_batch_12; facts_batch_12 | **should carry asterisk it lacks (lease term)** |
| `rc:sightmap:the-asher:530` | The Asher, Stamford CT | 530 | nothing to confirm | 'The price shown is for a 21-month lease'; fact lease_term_priced = 21 months. | live_check_batch_13; facts_batch_13 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p9506-mr1x1lsm-4083` | Merion Riverwalk, Shelton CT | 4083 | floor | 'The price shown is for a 20-month lease (lease_length 20 in page data)'. | live_check_batch_13 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p9506-mr1x1sm-2096` | Merion Riverwalk, Shelton CT | 2096 | floor | 'The price shown is for a 20-month lease (lease_length 20 in page data)'. | live_check_batch_13 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p58610350-022-265` | Avalon Somerville Station, Somerville NJ | 022-265 | floor | '$2,340 IS THE 20-MONTH LEASE PRICE ... 12-month price $2,430 ($2,519 with the required $89 fee)'; elevator 'not listed on AvalonBay's own pages'; floor 2 confirmed in the evidence but shown as unknown. | live_check_batch_15; confirm_batch_15; facts_batch_15 | **should carry asterisk it lacks (lease term, elevator)** |
| `apartmentlist:p970072-001-324` | Avalon Maplewood, Newark NJ | 001-324 | nothing to confirm | 'AvalonBay's own page (preferred): $2,590 is the 18-month term'. | live_check_batch_2 | **should carry asterisk it lacks (lease term)** |
| `region_wr:leaf_nr:1304` | The Leaf, New Rochelle NY | 1304 | nothing to confirm | 'unit 1304 lease term shown is 24 months'. | live_check_batch_5 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p54753443-selS4-14A` | Stella, New Rochelle NY | 14A | nothing to confirm | 'lease 15 mo' on both units. | live_check_batch_5 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p54753443-selS4-6A` | Stella, New Rochelle NY | 6A | nothing to confirm | 'lease 15 mo' on both units. | live_check_batch_5 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p113205989-lia-a2-333` | LIA by Vermella, Orange NJ | 333 | nothing to confirm | '15-month lease price'. | live_check_batch_8 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p113205989-lia-s1-423` | LIA by Vermella, Orange NJ | 423 | nothing to confirm | '15-month lease price'. | live_check_batch_8 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p37448175-wtha10x-312` | The Walcott Hackensack, Hackensack NJ | 312 | nothing to confirm | 'lowest price over lease terms (range to $3,068)' / '(range to $2,998)'; Apartment List lease_length 15. | live_check_batch_1 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p37448175-wtha10m-528` | The Walcott Hackensack, Hackensack NJ | 528 | nothing to confirm | 'lowest price over lease terms (range to $3,068)' / '(range to $2,998)'; Apartment List lease_length 15. | live_check_batch_1 | **should carry asterisk it lacks (lease term)** |
| `apartmentlist:p17832-45-343` | The Brownstones at Englewood South, Englewood NJ | 09-426 | nothing to confirm | '$2,168 is the lowest price over lease terms (range to $3,343)'. | live_check_batch_1 | **should carry asterisk it lacks (lease term)** |

### D9 (S2). Elevator not established, shown with no asterisk (8 units)

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `apartmentlist:p98932510-00B-308` | Avalon Wayne, Lincoln Park NJ | 00B-308 | nothing to confirm | elevator 'yes (Apartment List amenity tag only) [unconfirmed]'; master building_type 'townhome'. | confirm_batch_10 | **should carry asterisk it lacks (elevator)** |
| `apartmentlist:p98932510-00B-224` | Avalon Wayne, Lincoln Park NJ | 00B-224 | nothing to confirm | elevator 'yes (Apartment List amenity tag only) [unconfirmed]'; master building_type 'townhome'. | confirm_batch_10 | **should carry asterisk it lacks (elevator)** |
| `apartmentlist:p90606231-431` | Avalon Princeton on Harrison, Princeton NJ | 431 | nothing to confirm | elevator 'not listed on AvalonBay's own pages' (21 community features, 14 unit features, no elevator); Apartment List tag only. | confirm_batch_15 | **should carry asterisk it lacks (elevator)** |
| `apartmentlist:p846470-u48002209` | Grandville Towers, Red Bank NJ | 5F | nothing to confirm | elevator 'Apartment List amenity tag only [unconfirmed]'; 'unit records ... last updated 2026-07-30 ... the unit rows may be stale'. | confirm_batch_15; live_check_batch_15 | **should carry asterisk it lacks (elevator, stale)** |
| `apartmentlist:p846470-u48002210` | Grandville Towers, Red Bank NJ | 7C | nothing to confirm | elevator 'Apartment List amenity tag only [unconfirmed]'; 'unit records ... last updated 2026-07-30 ... the unit rows may be stale'. | confirm_batch_15; live_check_batch_15 | **should carry asterisk it lacks (elevator, stale)** |
| `trulia:2111411099` | 255 E  61st St, New York NY | 2a | nothing to confirm | 'unknown; four-story building, no elevator mentioned' ('2nd floor of a well-maintained four story building'). PLUTO lot is 1161 2 Avenue: 2 buildings, 1 elevator, built 1900. | confirm_batch_6; nyc_records.csv | **should carry asterisk it lacks (elevator)** |
| `trulia:466620083` | 2165 Clarendon Rd, Brooklyn NY | 2E | floor | elevator 'not stated on listing'; the official record used is the lot at 1127 Flatbush Avenue (nearest lot, 12 m). Floor 2 is also a guess: two open items. | confirm_batch_4; nyc_building_facts.csv | **should carry asterisk it lacks (elevator)** |
| `trulia:2104601160` | 2750 E  12th St, Brooklyn NY | 3I | nothing to confirm | elevator 'unknown: the page lists no elevator attribute'; the official record used is the lot at 1133 Banner Avenue (nearest lot, 13 m). | confirm_batch_6; nyc_building_facts.csv | **should carry asterisk it lacks (elevator)** |

### D10 (S2). Floors labelled "stated" or "confirmed" that are neither

- `h_trulia.py:297` takes the first "Nth floor" phrase in a description as the unit's floor and `build_master.py`
  labels it `stated`. Three of the eight shown "stated" floors come from an amenity sentence: 623 Avenue H 6C → 8
  ("8th-floor sundeck"), 405 W 206th St 713E → 11 ("11th floor Terraces"), 71-82 Parsons Blvd 615 → 7 ("7th Floor
  Resident's Lounge"). A fourth, Surfview Towers → 4, comes from a search card. None is a ground-floor unit, but the
  same mechanism would settle a ground-floor unit as an upper floor.
- `parsers.py:147` looks for "inferred / from unit number" in the value only. `confirm_batch_5` wrote it in the quote
  ("unit 1003 (floor inferred from the unit number)"), so 10 of the 39 shown "confirmed" floors are unit-number
  readings: 89-25 162nd St 1003, 89-61 162nd St 805, 92-29 Guy R Brewer Blvd 1307, 8625 Van Wyck Expy 329, 84-18
  143rd St 3L, 143-25 84th Ave 3J, 141-24 84th Dr 4F, 8267 Austin St 916, 1775 E 18th St 5N, 3625 Parsons Blvd 5H.
  All read as floor 3 or higher, so none is shown wrongly; the basis shown to the renter is.
- The reverse also happens: Avalon Somerville 022-265 has two confirmed "Floor 2" rows and is shown as floor unknown
  (`build_master.py:640`: a row with no unit label is applied only when the building has one unit in the master).

### D11 (S3). Rows with no unit number all receive the same live-check row

`build_master.py:618` matches `unit_key(x) == unit_key(un)`; blank equals blank, so every no-unit row of a building
takes the last blank live-check row. Park Place Towers: the rows stored at $2,425 and $2,683 both now show rent
$2,438 and all-in $2,641 (the $2,438 belongs to unit 3I, which is neither). The Mark's $2,590 plan carries live price
$2,545, The Riverhouse's $2,263 plan carries $2,025, Fairfield Metro at Glen Cove's $2,820 plan carries $2,650; those
three count as "live" on the strength of another plan's check.

### D12 (S3). Unknown cost lines are counted as $0, so the $3,000 all-in gate is not established near the cap

Pet rent is unknown, and counted as $0, on 185 of 332 shown units; parking on 259; building fees on 247. She has a
dog: where pet rent is stated for a shown unit it runs $25 to $100 a month, median $50. These 19 units are within $50 of the cap with
pet rent at $0, so a typical pet rent alone puts them over:

| listing_id | Building | Unit | All-in | Lines at $0 because unknown |
|---|---|---|---|---|
| `rc:trulia:b2750903232:Unit_219:2057730888` | The Residences at Quarry Walk, Oxford | 219 | 2984 | pet rent |
| `trulia:b1001443934:Unit_1612:2080830579` | Riello Edgewater, Edgewater | 1612 | 2952 | required building fees, pet rent, parking |
| `apartmentlist:p37451645-0718` | The Brick of Hackensack, Hackensack | 0718 | 2979 | pet rent, parking |
| `apartmentlist:p2194888-2117` | Cobalt Lofts, Harrison | 2117 | 2988 | pet rent |
| `trulia:b2734146684:Unit_608:374907376` | Metrovue, Jersey City | 608 | 2977 | required building fees, pet rent, parking |
| `trulia:466311584` | 109-10 Queens Blvd, Forest Hills | 12C | 2965 | required building fees, pet rent, parking |
| `rn:fairfield-metro-at-glen-cove-glen-cove:b1045082049:plan-S3_South_Studio:465141354` | Fairfield Metro at Glen Cove, Glen Cove | (none) | 2980 | required building fees, pet rent, parking |
| `trulia:b2751292880:Unit_1410:2056840837` | Admirals Cove, Haverstraw | 1410 | 2960 | required building fees, pet rent, parking |
| `trulia:466228957` | 92-29 Guy R Brewer Blvd, Jamaica | 1307 | 2979 | required building fees, pet rent, parking |
| `rn:25-west-broadway-condo-long-beach:2069636201` | 25 West Broadway (condo), Long Beach | 204 | 2971 | required building fees, pet rent, parking |
| `apartmentlist:p78543100-2311` | Two Clinton Park, New Rochelle | 2311 | 2972 | pet rent, parking |
| `trulia:463846279` | 26-25 4th St, Astoria | 1020 | 2988 | required building fees, pet rent, parking |
| `zumper-64694093` | 1890 Pelham Parkway South #4G, 1890 Pelham Pkwy S, Bronx, NY 10461, US, New York | 3G | 2983 | required building fees, pet rent, parking |
| `trulia:457456755` | 71-82 Parsons Blvd, Fresh Meadows | 615 | 2994 | required building fees, pet rent, parking |
| `trulia:339926856` | 61 Clarkson Ave, Brooklyn | 2B | 2994 | required building fees, pet rent, parking |
| `trulia:466197377` | 7914 Rockaway Beach Blvd, Far Rockaway | 2F | 2996 | required building fees, pet rent, parking |
| `trulia:2111411099` | 255 E  61st St, New York | 2a | 2988 | required building fees, pet rent, parking |
| `trulia:2106139475` | 949 W  End Ave, New York | D | 2983 | required building fees, pet rent, parking |
| `trulia:b2750788606:Unit_617:2056495787` | 1 Martine at City Square, White Plains | 617 | 2978 | required building fees, pet rent, parking |

### D13 (S3). Required fees double counted (overstates all-in; the safe direction)

`parsers.monthly_fees_from_text` / `all_in.py`: a stated total is added to its own breakdown again, and both ends of
a range are summed. Scribe 508 and 446: $200, evidence "$100/mo (trash $25 + amenity $75)". The Asher 530: $200,
evidence $100. The Botanic 430: $295, evidence $97.55. Quarry Walk 219: $80, page "Water and sewage $35-$45". Atlas
0308: the fee line includes "Internet: $65" and the $75 internet estimate is added as well.

### D14 (S3). Net-effective rents invented from offers that do not apply

- Beacon Mill Village PA-405 and PA-202: the offer is "application fee waived and 50% off move-in costs"; the rent
  line reads "rent (net-effective), computed from stated terms" and carries a rent asterisk.
- Arcade Apartments 302: the "first month free, sign by June 30" offer expired five months ago; gross is shown as
  $1,815 against a listed $1,675.
- Scribe 508 and 446: the 24-month price is treated as net of "up to 2 months free" and a gross of $2,911 / $2,831 is
  derived from it. Avalon Somerville 022-265: the 20-month price is treated as net of 1.5 months, gross $2,674; the
  owner's data says net-effective equals price.

### D15 (S3). Individual wrong numbers found in the field check

- 2072 20th Ln 6E: parking $200 "confirmed" in the all-in. The listing says "Garage parking available for additional
  fee" with no amount; the $200 was taken from another building's listing in the same complex.
- Avalon Maplewood 001-324: the live check read $2,590 (so did tonight's fetch); the rent line still uses $2,600
  because the live row's status is "live", not "changed" (`all_in.py:61` applies the live price only for "changed").
- Avalon Teaneck 001-215: $2,521 on the page at 23:21 UTC, master $2,516 (changed after the evidence pass).
- Metrovue 201 and Metro Point 1-2R: Trulia's unit price is a "total price" that already contains $75 and $67 of
  required monthly fees; the master treats it as base rent with fees "unknown". The all-in total is right by accident.

### D16 (S3). NYC lot matches that are a neighbouring lot (audit C2)

25 of the 79 shown NYC buildings with a lot were matched as `nearest_lot`; in 21 the lot's address differs from the
listing's. Two are certainly the wrong building, and their floors, year, class and city-record counts come from it:

| Listing address | Matched lot | Distance | What the lot says | Effect |
|---|---|---|---|---|
| 12333 83rd Ave 3203, Kew Gardens | 123-10 83 Avenue | 25 m | class C3 (walk-up), 3 floors, 4 units, 1991 | wrong side of the street (odd/even). Elevator comes from the listing, so the gate is not affected; `building_floors = 3` and the records are another building's |
| 3333 Broadway, Manhattan | 614 West 135 Street | 30 m | class C1 (walk-up), 5 floors, 187 units, 1926 | same: listing says "New Elevators"; floors and records are wrong |

Units whose elevator rests only on a lot with a different address (no elevator on the listing):

| Listing | Matched lot | Basis shown | Note |
|---|---|---|---|
| 255 E 61st St 2a | 1161 2 Avenue, 9 m, 2 buildings on the lot, 1 elevator, 4 floors, 1900 | official_record | owner name on the lot is "255-257 East 61st St", so the lot is probably right, but the elevator may be in the other building; the listing says "four story building" and no elevator (see D9) |
| 2165 Clarendon Rd 2E | 1127 Flatbush Avenue, 12 m | official_record | probably a corner lot; unverified |
| 2750 E 12th St 3I | 1133 Banner Avenue, 13 m | official_record | probably a corner lot; unverified |
| 1875 Atlantic Ave 601A | 1885 Atlantic Avenue, 32 m, floors blank | confirmed (the quote is the PLUTO class) | should read official_record at most |

House number differs but the listing states an elevator, so only the building facts are at risk: 9949 Shore Rd →
9937 Shore Road (18 m); 142-38 37th Ave → 142-32 (16 m); 84-18 143rd St → 84-14 (14 m); 3310 Nostrand Ave → 3280
(16 m); 1802 Ocean Ave → 1800 (13 m); 103-14 Northern Blvd → 103-12 (18 m); 5 Stuyvesant Pl → 160 Richmond Terrace
(39 m, a different street); 375 Lefferts Ave → "Lefferts Avenue" with no number (25 m); six corner lots filed under the
cross street (100 W 139th St, 92-29 Guy R Brewer Blvd, 1105 30th Rd, 1890 Pelham Pkwy S, 630 W 163rd St, 545
Edgecombe Ave); and 1010 Rogers Ave → 1010-1012, which is the same lot. `enrich_nyc_pluto.py:82-90` prefers a
house-number match but otherwise accepts the nearest lot within 40 m and only labels it `nearest_lot`;
`nyc_records_match.csv` already carries `house_number_agrees = no` for these. Nothing downstream reads either.

### D17 (S4). The same apartment shown twice

Arcade Apartments, Bridgeport: unit 302 and an unnamed row at the same price and size ("probably the same apartment
as unit 302 advertised twice", `live_check_batch_12`). The Cove, Westfield: two rows for one floor plan (also in D1).
`build_master.py` removes duplicates only when unit labels match.

### D18 (S4). Stale availability dates shown with nothing to confirm

| listing_id | Building | Unit | Shown with | Evidence | File | Verdict |
|---|---|---|---|---|---|---|
| `apartmentlist:p70186829--409` | Hedges at Hawthorne, Hawthorne NJ | 409 | nothing to confirm | 'available_on date is over 10 months old: the unit data may be stale, confirm by phone'. Shown with nothing to confirm. | live_check_batch_2 | **should carry asterisk it lacks (stale)** |
| `apartmentlist:p107328890-8fad7c00-bff6-11f0-8ab6-12de4bf481cd` | The Mercer – 10 Commerce Court, Newark, NJ, Newark NJ | 8F | nothing to confirm | 'available_on 2025-12-01 ... over 10 months old: the unit data may be stale, confirm by phone'. | live_check_batch_2 | **should carry asterisk it lacks (stale)** |
| `trulia:b2739941135:Unit_304:460609693` | Chateau Rive, Peekskill NY | 304 | nothing to confirm | 'description still advertises a July 26 open house and a two-bedroom; unit 304 is listed as a 1BR'. | facts_batch_11 (listing_text_stale) | **should carry asterisk it lacks (stale)** |
| `rc:trulia:b2752176221:Unit_208:2055684979` | The Residences at the Kestrel, Seymour CT | 208 | floor | 'Page last modified 2026-09-22 ... PLEASE CALL FOR CURRENT AVAILABLE UNITS'. | live_check_batch_13 | **fine (asterisk present; add the call)** |
| `rc:trulia:b1001440881:Unit_1-2K:463214851` | Metro Star - Metro Point, Milford CT | 1-2K | floor | 'Listing last modified in August 2026: confirm by phone.' | live_check_batch_12 | **fine (asterisk present)** |
| `rc:trulia:b1001440881:Unit_1-2R:455232584` | Metro Star - Metro Point, Milford CT | 1-2R | floor | 'Listing last modified in August 2026: confirm by phone.' | live_check_batch_12 | **fine (asterisk present)** |
| `rc:trulia:b2754103631:Unit_131-2F:450633635` | Metro Star - Metro on Broad, Milford CT | 131-2F | floor | 'Listing last modified in August 2026: confirm by phone.' | live_check_batch_12 | **fine (asterisk present)** |
| `rc:trulia:b2754103631:Unit_127-2R:452918510` | Metro Star - Metro on Broad, Milford CT | 127-2R | floor | 'Listing last modified in August 2026: confirm by phone.' | live_check_batch_12 | **fine (asterisk present)** |

Also seen: 110 Washington A413 and A421 (available_on May and June 2026), Halstead Parsippany 2182 ("available since
2026-05-14 (six months): ask why it has sat"), Hudson 44 (Trulia page last modified 2026-05-06), Sono Pearl
(2026-07-13), 80East (2026-07-08).

### D19 (S4). Selection is not stable between runs

Between the 23:11 and 23:16 runs The Asher's unit 536 (live-checked, nothing open) was replaced by unit 308 (never
live-checked) at the same `rank_score` of 59.9, and The Leaf's 2505 by 2318. `rank.py` sorts on
`hood_id, dominated, rank_score` with no tie-break, so equal scores fall in file order; a verified unit should win a
tie.

### D20 (S4). Resident quotes (audit C3)

800 quotes are attached to 71 neighborhoods; every one is in `neighborhood_quotes.csv` under the same `hood_id`, and
none contains a username, handle or profile link. Of 25 sampled (seed 20261116), 24 are about the place they are
filed under at the level of the source's own area. Problems:

- `build_page_data.py:133` drops `source_area`. Quotes about a wider or different area are shown under a narrower
  name with no label: North Corona ← Corona; Astoria (East)-Woodside (North) ← Woodside; East New York (North) ← East
  New York; Harlem (North) ← Harlem; East Flatbush-Farragut ← East Flatbush; Flushing-Willets Point ← Flushing;
  Jamaica Hills-Briarwood ← two separate pages.
- `nj:plainfield`: "North Plainfield is a beautiful subset of Somerset County..." is about a different municipality
  in a different county.
- `ny:jamaica-hills-briarwood`: "As the President of Jamaica Hill Community Association, I observed..." identifies
  the writer by office. Not a username, but it names one person; rule 6's intent says drop it.
- Quality: `nj:belleville` "give your gf a shining diamond!"; `ny:sheepshead-bay...` names Bryant Park, which is in
  Manhattan.

### D21 (S4). Street parking at $0 (audit C1)

Two shown units carry "parking (street) $0": 13324 Sanford Ave 6G and 2D, Flushing. The Trulia listing for 2D says
"Parking: Street Parking" and neither page mentions a garage or lot, so the line is right; 6G inherits it from 2D's
listing (its own Zumper page is silent). Across the master, 14 units in 12 buildings carry the line; every one has a
sentence that says street parking and none mentions a paid garage or lot. Two are weaker than "street only": 96 Hart
St ("Plenty of Street Parking") and 60 W Madison Ave ("Special Features: Street Parking"). No missed garage found.

## Exclusions that look like false positives

30 of the 179 rows in `data/unit_exclusions.csv` were read (seed 20261116, spread over the reason types: 9 possible
ground floor, 6 elevator reading, 6 not open to her, 7 co-op, 2 doubtful listing). 29 are supported by the evidence
text. One is too broad: `62 treat st|06516` is excluded as a whole building because one floor plan named "103" reads
as floor 1; the rule at `avoid.py:157-158` falls back to the whole building when it cannot name a unit. The 21
"co-op building (city record, class D4)" rows are correct by the owner's rule; note that the rule removes sponsor
rentals in co-op buildings too, which do not need board approval.

## Field check of 30 shown units

Sample: 12 New York, 12 New Jersey, 6 Connecticut, drawn with `numpy.random.RandomState(20261116)` from shown rows
sorted by `listing_id`. Sources: 20 Trulia, 8 Apartment List, 2 Zumper. **Trulia was not requested**: the 20 Trulia
units were compared with the cached copy named in `raw_path` (captured 19:31 to 21:50 UTC today), so for them this
is a check of parsing, not of whether the listing is still live. The 8 Apartment List and 2 Zumper pages were
fetched at 23:21 UTC through `lib.cached_get` after reading both robots.txt files (no group names Claude; the paths
are allowed); all returned 200.

| Field | Agree | Disagree | Not checkable |
|---|---|---|---|
| rent | 26 | 2 | 2 |
| availability_date | 28 | 1 | 1 |
| unit | 27 | 0 | 3 |
| beds | 30 | 0 | 0 |
| sqft | 25 | 0 | 5 |
| floor | 1 | 0 | 29 |
| elevator | 27 | 0 | 3 |
| dogs_allowed | 30 | 0 | 0 |
| dog_weight_limit | 10 | 0 | 20 |
| required_fees | 3 | 3 | 24 |
| pet_rent | 7 | 0 | 23 |
| parking_fee | 3 | 1 | 26 |
| utilities_included | 2 | 1 | 27 |
| concession | 30 | 0 | 0 |
| price_basis_gross_or_net | 1 | 4 | 25 |
| all_in | 0 | 4 | 26 |

"Not checkable" means the page gives no value. It is the normal case for floor (29 of 30: the master's floor is a
reading of the unit label), required fees, parking price, utilities and whether the price is gross or net.

| Unit | Field | Master | Page | Note |
|---|---|---|---|---|
| 2072 20th Ln 6E | parking_fee | 200.0 (confirmed); type: garage: garage, extra fee (amount not stated here; the 1483 Shore | 'Garage parking available for additional fee' (no amount) | master $200 'confirmed' is not on this listing; it was taken from another building's listing in the same complex |
| 2072 20th Ln 6E | all_in | 2644 | parking amount unsupported | all-in includes $200 parking that this page does not state |
| Avalon Maplewood 001-324 | rent | 2600 | 2590.0 | live fetch: unit now $2,590 (the evidence pass also read $2,590); master rent line still uses $2,600 |
| Avalon Maplewood 001-324 | all_in | 2959 | $10 too high | rent line not updated to the live price |
| Metrovue 201 | required_fees | 0 (unknown) | Amenity fee listed as required; price note: total price includes base rent ($2,375-$2,850) and monthly fees ($ | a required $75/month fee exists and is folded into the unit price; master fee line is $0 'unknown' |
| Metrovue 201 | price_basis_gross_or_net | listed price is unknown; rent line 2575.0 (listed); gross 2575.0; lease months 12.0 | 'Total price': base rent plus $75 required monthly fees | master treats $2,575 as base rent; all-in total is unaffected because the fee is inside the price |
| Avalon Teaneck 001-215 | rent | 2516 | 2521.0 | live fetch: unit now $2,521; master $2,516 (changed since the evidence pass) |
| Avalon Teaneck 001-215 | availability_date | 2026-11-16 | 2026-11-15 | page available_on 2026-11-15; master 2026-11-16 (one day) |
| Avalon Teaneck 001-215 | all_in | 2917 | $5 too low | rent changed after the live check |
| City Trust Collection: Arcade Apartments. 302 | price_basis_gross_or_net | listed price is net_effective; rent line 1675.0 (net_effective); gross 1815.0; lease month | no current offer; available_on 2025-06-01 | master treats $1,675 as net-effective of an expired offer (gross $1,815) |
| The Residences at Quarry Walk 219 | required_fees | 80 (confirmed) | Water and sewage $35-$45 (required monthly) | master adds both ends of the range ($35 + $45 = $80) |
| The Residences at Quarry Walk 219 | all_in | 2984 | about $40 too high | fee line double counts the range |
| Metro Star - Metro Point 1-2R | required_fees | 0 (unknown) | price note: total price includes base rent ($2,395-$2,695) and monthly fees ($67) | required fees of $67 are folded into the unit price; master fee line is $0 'unknown' |
| Metro Star - Metro Point 1-2R | price_basis_gross_or_net | listed price is gross; rent line 2562.0 (listed); gross 2562.0; lease months  | 'Total price': base rent plus $67 required monthly fees | master treats $2,562 as base rent; all-in total is unaffected because the fee is inside the price |
| Beacon Mill Village PA-405 | utilities_included |  | cold water, sewer, rear-lot parking, pool and gym included in rent | master utilities_included is blank |
| Beacon Mill Village PA-405 | price_basis_gross_or_net | listed price is net_effective; rent line 1805.0 (net_effective); gross 1805.0; lease month | offer is 'Application fee waived and 50% off move-in costs' (not a rent discount) | master labels the rent 'net-effective (computed from stated terms)' and sets a rent asterisk; the offer does not touch the rent |

Other things the field check showed:

- 8300 Boulevard E 4D: tonight's page says "This oversized 1 bedroom co-op" (D5).
- Vista Apartments 200: page last modified 2025-12-16. Sono Pearl 313: 2026-07-13. Fairfield Estates at Woodmere
  and Willett Point: floor-plan rows, "availableRentalUnits: 0"; the studio plan at Willett Point has no price of its
  own, the $2,350 is the low end of the building's range.
- Hedges at Hawthorne 409 and Arcade 302: `available_on` 2025-09-24 and 2025-06-01.
- Skyline New Rochelle 14N and 630 West 163rd St 10: the listing page has no elevator line; the master's "confirmed"
  rests on a residents' petition and on tenant reviews.

## What I could not check

- Whether any Trulia listing (180 of the 332 shown units, 20 of my 30) is still live or still at its price:
  Trulia is returning 403 and was not requested.
- Zillow-sourced units (6 shown): off limits. Five of them are in D2.
- Buildings' own leasing sites, pet policies in pounds, parking prices and fee schedules: not fetched; most of the
  214 "not checkable" cells would need them or a phone call.
- The true tax lot for the near-miss matches in D16: judged from the two addresses, the distance and the lot's size,
  not re-queried against the city's address service.
- Evidence text: for the first 22 buildings every row was read in full. For the rest, every live-check row that was
  not a plain "live, matches" line, every confirm row except routine "elevator yes / dogs yes [confirmed]" rows
  (those were screened for qualifiers), every fact row touching a gate, and review items mentioning an elevator,
  stairs, dogs, age or income limits were read; fee, parking and pet-rent facts were compared by script. Building
  inspection and police records outside NYC carry no gate fact and were not read line by line.
- The 61 held units, 59 awaiting a live check and 35 avoid cards were not audited.
- Anything about ranking, scores, travel times or crime figures.

## Files this check wrote

`docs/INDEPENDENT_CHECK_2.md`, `data/evidence/independent_check_2_units.csv`, and, as a side effect of using
`lib.cached_get`, the 12 fetched pages and their index under `raw/independent_check_2/` (2 robots.txt, 8 Apartment
List pages, 2 Zumper pages). Nothing else was touched.
