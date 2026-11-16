# Pipeline consistency pass (2026-11-16)

A debugging and consistency pass over the pipeline scripts, plus two owner rules that arrived during it (only real
apartments; thin neighborhoods). Work was done on a copy, the shown set was diffed against the list of 491 after every
step, and every fix has a test (`scripts/test_rules.py`: `pure_6`, `data_6`, `lifestyle_assignment_checks`). No listing
page was fetched. The rules are stated once in `docs/RANKING.md`.

## Shown set, before and after

| | Before | After the fixes, before the thin rule | Final |
|---|---|---|---|
| Apartments shown | 491 | 481 | **446** |
| Buildings | 233 | 226 | **191** |
| Neighborhoods | 104 | 103 | **68** |
| Ranked | 769 | 760 | 760 |

54 shown rows left: 35 by the thin-neighborhood rule, 16 are not apartments, 3 by knock-on (Aviva E0918 and 3 Acres 6052
lost the eighth place in their building to a sibling when scores moved by a tenth; Avalon Teaneck's Apartment List row
`001-215` was replaced by the building's own row for the same apartment, `215`). 9 entered. 4 moved experience.

```
ranked 769 -> 760; shown 491 -> 446; buildings 233 -> 191
LEFT 54
                                                   listing_id                                              building_name                 unit                                          hood group_key  rank_score
                    rc:trulia:b2780964658:Unit_5204:465685674                              Brookfield Village Apartments                 5204                                    Brookfield     space        52.9
                    rc:trulia:b2750903232:Unit_219:2057730888                              The Residences at Quarry Walk                  219                                        Oxford     space        45.4
                    rc:trulia:b2750819801:Unit_M306:466308014              Lopresti School Apartments at 29 Maple Street                 M306                                       Seymour     space        50.7
            rc:trulia:b2734028645:plan-Grand_Denali:456056380 The Mark, Fairfield County ~ Resort-Inspired Luxury Living                  NaN                                       Shelton     space        58.4
             rc:trulia:b2734028645:plan-Grand_Bryce:456056393 The Mark, Fairfield County ~ Resort-Inspired Luxury Living                  NaN                                       Shelton     space        57.8
                   rc:trulia:b2734028645:plan-Bryce:456056389 The Mark, Fairfield County ~ Resort-Inspired Luxury Living                  NaN                                       Shelton     space        56.1
                     rc:trulia:b2795130832:plan-1br:465130674                                         301 Bridgeport Ave                  NaN                                       Shelton     space        51.9
                  rc:trulia:b2734028645:plan-Denali:456056378 The Mark, Fairfield County ~ Resort-Inspired Luxury Living                  NaN                                       Shelton     space        55.3
                     rc:trulia:b2773044312:plan-308:463098083                                             The Riverhouse                  NaN                                      Stamford    middle        59.8
                     rc:trulia:b2773044312:plan-305:466542171                                             The Riverhouse                  NaN                                      Stamford    middle        59.6
                 rc:trulia:b2795181153:plan-204-804:465940494                                               Valeur Lofts                  NaN                                      Stamford    middle        52.7
                                apartmentlist:p10015-15572337                                      The Royce at Trumbull                 4234                                      Trumbull     space        60.3
                        trulia:b1001443078:Unit_7C:2069024272                                        ELK Harbor View LLC                   7C                            Atlantic Highlands   enclave        53.0
                                apartmentlist:p1068704-13-172                                           Kensington Place                 4222                                East Brunswick     space        61.8
                              apartmentlist:p263791-u49220319                                          Harrison Somerset B, H, K, R - Small-1                                      Franklin    middle        42.3
                              apartmentlist:p263791-u49220292                                          Harrison Somerset          G - Small-1                                      Franklin    middle        40.4
                                 apartmentlist:p372060-50-123                                         The Grove Somerset                 2205                                      Franklin    middle        38.8
                                 apartmentlist:p70186829--409                                        Hedges at Hawthorne                  409                                     Hawthorne     space        47.7
                      apartmentlist:p122576232-S2E_AVIV-E0918                                                      Aviva                E0918                Jersey City – Bergen-Lafayette new_water        53.2
                                 apartmentlist:p10296-002-311                                            Portside Towers                  311                        Jersey City – Downtown new_water        51.3
                      trulia:b2750805471:Unit_6052:2058332518                                                    3 Acres                 6052                       Jersey City – West Side    middle        42.5
                                apartmentlist:p970072-001-324                                           Avalon Maplewood              001-324                                     Maplewood     space        58.4
                           apartmentlist:p82905455-AR11A1-217                                            Woodland Square                  217                                      Montvale   enclave        54.0
                       trulia:b1001488769:Unit_1200:466337359                                              The Highlands                 1200                                 Morris Plains     space        62.6
                          apartmentlist:p909378-wwlaguna-5201                                              Woodmont West                 5201                               Mount Arlington     space        65.7
                                 apartmentlist:p693-u36624909                                              Skyline Tower      1 Bedroom Large                                 New Brunswick new_water        48.5
                                 apartmentlist:p693-u36308136                                              Skyline Tower       1 Bed - 1 Bath                                 New Brunswick new_water        45.2
                                              zumper-65278838                                              Clinton Flats                  NaN                                        Newark   settled        54.4
                                              zumper-65278784                                              Clinton Flats                  NaN                                        Newark   settled        53.7
                           apartmentlist:p46969315-OLD-A5-232                                                  99 Bridge                  232                                    Old Bridge     space        47.2
apartmentlist:p121523419-c3706e3d-3331-11eb-a866-0a77b09e5ae8                                    Centurion Sleepy Hollow                  403                                    Plainfield     space        52.7
                                  apartmentlist:p90606231-431                               Avalon Princeton on Harrison                  431                                     Princeton   enclave        62.2
                           apartmentlist:p15017-4030-1c-4-412                                       Reserve at Riverdale                4-412                                     Riverdale    middle        46.6
                   trulia:b2734023302:Unit_N_A-0715:449332512                                            Parc At Roxbury             N/A-0715                                       Roxbury   enclave        55.4
                              apartmentlist:p58610350-022-265                                  Avalon Somerville Station              022-265                                    Somerville    middle        57.7
                              apartmentlist:p11978175-001-215                                             Avalon Teaneck              001-215                                       Teaneck   enclave        65.0
                                              zumper-65756566                                                        NaN                  2fl               Astoria (East)-Woodside (North)   pre_car        56.8
                                            trulia:2100220346                                                        NaN                  502                                     Bay Ridge   pre_car        55.2
                                             trulia:466590573                                                        NaN                 601A                     Bedford-Stuyvesant (East)   settled        52.3
                                            trulia:2092277752                                                        NaN                   6G                           East Harlem (South)   settled        57.4
                                            trulia:2061051325                                                        NaN                   6C         Flatbush (West)-Ditmas Park-Parkville   settled        54.6
                                             trulia:466464245                                                        NaN                  667                                     Flatlands   settled        47.9
                                             trulia:466614467                                                        NaN                  201                             Gravesend (South)   settled        49.7
                                    apartmentlist:p6296923-2F                                              Village Lofts                   2F                                     Hempstead   settled        53.1
                        trulia:b2756501402:plan-14J:466162659                                                  The Alary                  NaN                                  New Rochelle    middle        51.7
                                              trulia:32314280                                                        NaN                   7O New Springville-Willowbrook-Bulls Head-Travis    middle        46.6
                                             trulia:350209733                                                        NaN                   6F                                  North Corona   settled        49.7
                       trulia:b2750798202:Unit_406:2060165760                                                Port & Main                  406                                  Port Chester    middle        48.3
                                            trulia:2084088580                                                        NaN                   6J                      Riverdale-Spuyten Duyvil    middle        45.2
                                             trulia:466009019                                                        NaN                   4F                       St. George-New Brighton   settled        47.9
                                            trulia:2093254023                                                        NaN                   5F                                     Sunnyside   pre_car        54.1
                                              zumper-52172071                                         Staten Island Urby                  NaN     Tompkinsville-Stapleton-Clifton-Fox Hills   settled        59.9
                             region_mid_hudson:z:1bd28b7ced85                                           The Park at Main                   63                                      Wallkill     space        61.2
                                            trulia:2110916843                                                        NaN                   4d                    Washington Heights (North)   settled        48.9
ENTERED 9
                             listing_id    building_name  unit                           hood group_key  rank_score
apartmentlist:p122576232-S3E_AVIV-E0721            Aviva E0721 Jersey City – Bergen-Lafayette new_water        53.4
trulia:b2750805471:Unit_5066:2059763444          3 Acres  5066        Jersey City – West Side    middle        42.6
                      trulia:2077753253              NaN  1210                         Rahway     space        58.0
               avalon:AVB-NJ030-001-215   Avalon Teaneck   215                        Teaneck   enclave        65.4
           region_wr:oneclinton_nr:2309 One Clinton Park  2309                   New Rochelle    middle        40.0
           region_wr:oneclinton_nr:2003 One Clinton Park  2003                   New Rochelle    middle        39.7
           region_wr:continuum_wp:N0311        Continuum N0311                   White Plains    middle        52.3
           region_wr:continuum_wp:S0515        Continuum S0515                   White Plains    middle        51.3
           region_wr:continuum_wp:N0419        Continuum N0419                   White Plains    middle        51.5
MOVED experience/hood 4
hood_id_a           group_key_a  hood_id_b           group_key_b
nj:east-rutherford  space        nj:east-rutherford  middle         2
ny:patchogue        space        ny:patchogue        middle         2
hoods with common units REORDERED 10 ['ct:norwalk', 'ct:shelton', 'ct:stamford', 'nj:bayonne', 'nj:hackensack', 'nj:harrison', 'nj:jersey-city-bergen-lafayette', 'nj:jersey-city-west-side', 'ny:jamaica', 'ny:yonkers']
rank_score changed for 422 max 5.800000000000004
shown id sequence identical: False

```

By experience, the single-apartment neighborhoods kept and cut, and the rows reclassified as not an apartment:

```
BASELINE 491 233 104
                           units  buildings  hoods
group_label                                       
The Fresh-Start Year          65         25      6
The Little-City Year         198         85     26
The Old-Neighborhood Year     85         63     30
The Quiet-Street Year         10          7      7
The Room-to-Breathe Year     128         48     31
The Walk-Everywhere Year       5          5      4
AFTER not-an-apartment + other fixes, BEFORE thin rule 481 226 103
                           units  buildings  hoods
group_label                                       
The Fresh-Start Year          63         24      6
The Little-City Year         201         84     28
The Old-Neighborhood Year     82         61     29
The Quiet-Street Year         10          7      7
The Room-to-Breathe Year     120         45     29
The Walk-Everywhere Year       5          5      4
FINAL 446 191 68
                           units  buildings  hoods
group_label                                       
The Fresh-Start Year          62         23      5
The Little-City Year         195         78     22
The Old-Neighborhood Year     73         52     20
The Quiet-Street Year          6          3      3
The Room-to-Breathe Year     108         33     17
The Walk-Everywhere Year       2          2      1
single-apartment hoods before thin rule: 46
medians {'enclave': 56.3, 'middle': 50.9, 'new_water': 57.9, 'pre_car': 55.5, 'settled': 55.4, 'space': 54.7}
KEPT 11
                                          hood        building_name     unit group_key  rank_score
                                     Fairfield Alto Fairfield Metro     402A   enclave        58.2
                                       Garwood The Lofts at Garwood GAR2R-08     space        55.0
                                     Ridgewood  263 Franklin Avenue       48    middle        56.2
                                       Teaneck       Avalon Teaneck      215   enclave        65.4
                    Gravesend (East)-Homecrest                  NaN      402   settled        60.0
                              Gravesend (West)                  NaN       6G   settled        60.9
                                       Madison       1775 E 18th St       5N   settled        62.1
                                       Midwood                  NaN       9G   settled        56.5
                 Murray Hill-Broadway Flushing                  NaN       5H   settled        56.6
Sheepshead Bay-Manhattan Beach-Gerritsen Beach                  NaN       6E   settled        59.5
                                 Valley Stream    Sun Valley Towers      501     space        58.3
CUT 35
                                         hood                                 building_name     unit group_key  rank_score                why
                                   Brookfield                 Brookfield Village Apartments     5204     space        53.4     open: elevator
                                       Oxford                 The Residences at Quarry Walk      219     space        45.7       below median
                                      Seymour Lopresti School Apartments at 29 Maple Street     M306     space        50.9     open: elevator
                                     Trumbull                         The Royce at Trumbull     4234     space        60.6     open: elevator
                           Atlantic Highlands                           ELK Harbor View LLC       7C   enclave        52.8       below median
                               East Brunswick                              Kensington Place     4222     space        61.8     open: elevator
                                     Franklin                            The Grove Somerset     2205    middle        38.8     open: elevator
                                    Hawthorne                           Hedges at Hawthorne      409     space        48.2      open: listing
                       Jersey City – Downtown                               Portside Towers      311 new_water        51.8       below median
                                    Maplewood                              Avalon Maplewood  001-324     space        58.9     open: elevator
                                     Montvale                               Woodland Square      217   enclave        54.4     open: elevator
                                Morris Plains                                 The Highlands     1200     space        63.1     open: elevator
                              Mount Arlington                                 Woodmont West     5201     space        65.8     open: elevator
                                   Old Bridge                                     99 Bridge      232     space        47.5     open: elevator
                                   Plainfield                       Centurion Sleepy Hollow      403     space        53.2       below median
                                    Princeton                  Avalon Princeton on Harrison      431   enclave        62.8     open: elevator
                                    Riverdale                          Reserve at Riverdale    4-412    middle        46.7     open: elevator
                                      Roxbury                               Parc At Roxbury N/A-0715   enclave        55.7       below median
                                   Somerville                     Avalon Somerville Station  022-265    middle        58.0     open: elevator
              Astoria (East)-Woodside (North)                                           NaN      2fl   pre_car        57.3 open: dogs allowed
                                    Bay Ridge                                           NaN      502   pre_car        55.5   open: live check
                    Bedford-Stuyvesant (East)                                           NaN     601A   settled        52.5     open: elevator
                          East Harlem (South)                                           NaN       6G   settled        57.6   open: live check
        Flatbush (West)-Ditmas Park-Parkville                                           NaN       6C   settled        54.7       below median
                                    Flatlands                                           NaN      667   settled        48.2       below median
                            Gravesend (South)                                           NaN      201   settled        49.6       below median
                                    Hempstead                                 Village Lofts       2F   settled        53.2       below median
New Springville-Willowbrook-Bulls Head-Travis                                           NaN       7O    middle        46.9       below median
                                 North Corona                                           NaN       6F   settled        50.0       below median
                                 Port Chester                                   Port & Main      406    middle        48.6       below median
                     Riverdale-Spuyten Duyvil                                           NaN       6J    middle        45.4       below median
                      St. George-New Brighton                                           NaN       4F   settled        47.6       below median
                                    Sunnyside                                           NaN       5F   pre_car        54.4       below median
                                     Wallkill                              The Park at Main       63     space        61.6      open: listing
                   Washington Heights (North)                                           NaN       4d   settled        49.1       below median
not_an_apartment rows 71 {'floor_plan': 63, 'building_offer': 5, 'private_room': 3}
of which shown in baseline 16
                                       listing_id              building_name                 unit   listing_kind                                      hood
                                  zumper-52172071         Staten Island Urby                  NaN building_offer Tompkinsville-Stapleton-Clifton-Fox Hills
            trulia:b2756501402:plan-14J:466162659                  The Alary                  NaN     floor_plan                              New Rochelle
     rc:trulia:b2795181153:plan-204-804:465940494               Valeur Lofts                  NaN     floor_plan                                  Stamford
                  apartmentlist:p263791-u49220292          Harrison Somerset          G - Small-1     floor_plan                                  Franklin
                  apartmentlist:p263791-u49220319          Harrison Somerset B, H, K, R - Small-1     floor_plan                                  Franklin
         rc:trulia:b2773044312:plan-305:466542171             The Riverhouse                  NaN     floor_plan                                  Stamford
         rc:trulia:b2773044312:plan-308:463098083             The Riverhouse                  NaN     floor_plan                                  Stamford
         rc:trulia:b2795130832:plan-1br:465130674                        NaN                  NaN     floor_plan                                   Shelton
       rc:trulia:b2734028645:plan-Bryce:456056389 The Mark, Fairfield County                  NaN     floor_plan                                   Shelton
rc:trulia:b2734028645:plan-Grand_Denali:456056380 The Mark, Fairfield County                  NaN     floor_plan                                   Shelton
 rc:trulia:b2734028645:plan-Grand_Bryce:456056393 The Mark, Fairfield County                  NaN     floor_plan                                   Shelton
      rc:trulia:b2734028645:plan-Denali:456056378 The Mark, Fairfield County                  NaN     floor_plan                                   Shelton
                     apartmentlist:p693-u36308136              Skyline Tower       1 Bed - 1 Bath     floor_plan                             New Brunswick
                     apartmentlist:p693-u36624909              Skyline Tower      1 Bedroom Large     floor_plan                             New Brunswick
                                  zumper-65278784              Clinton Flats                  NaN building_offer                                    Newark
                                  zumper-65278838              Clinton Flats                  NaN building_offer                                    Newark

```

Every unit that entered was read and given a verdict (`data/evidence/review_verdicts.csv`): Continuum N0311, N0419,
S0515 (and re-read S0904, N1119, whose building's evidence set grew), One Clinton Park 2003 and 2309, 3 Acres 5066,
Aviva E0721: `ok` (the rules already carry their elevator or live-check asterisk); 1423 Irving St 1210, Rahway:
`disclose / coop_condo` (an owner-rented condo); Avalon Teaneck 215 (own-site row): its `remove` ("duplicate of the
Apartment List row") became `ok`, because the two rows are now merged by rule and the own-site row is the one kept.

## Step 1. One elevator rule

`parsers.elevator_rule` (truth table in `scripts/parsers.py` and `docs/RANKING.md`) is now called by `gates.py`,
`build_master.py`, `rank.py` and `check_registry.py` (which had a fourth copy).

Listing gate, status before → after (all changes of this pass at the gate, including step 3's address fix):

```
before   after  
absent   pending        5
fail     fail        3857
         pending      424
pass     pass        2502
         pending        1
pending  absent         1
         fail          87
         pass           3
         pending    13589
```

- 489 listings no longer FAIL on the city's walk-up class: 465 rested on a neighbouring lot, 24 on a lot whose address
  does not agree with the listing's. They are `pending` unless something else fails. None reaches the shown list.
- 20 listings whose elevator evidence was contradicted went from unknown to open (pass, one open fact); 33 gained the
  city's elevator class on a "nearest" lot whose address is the listing's own; 17 lost it (the lot's address differs,
  or the city lists zero active elevators: 2561 Bedford Ave 3B left the master table).
- Ranking: "high-rise" on the manager's page and a page-stated floor of 6+ now count as real height, as they already
  did at the gate. 28 units moved from "not shown (height unknown)" to "one open fact": Continuum 55 / 57 (10), The
  Beacon tower (13), West Side Square (4), 1423 Irving St 1210. Six of them were seen live and entered the shown list.

## Step 2. Experience assignment

**Why East Rutherford and Patchogue moved.** The scaling was already saved (a fit reference set and index SDs). The
features were not stable: every input of the nine indices was a median over the buildings that currently pass the
gates. Both neighborhoods went from two passing buildings to one. East Rutherford's restaurants within 800 m went from
17 to 3 and its sq ft per $1,000 from 238 to 270; that carried it from Little-City to Room-to-Breathe. Four other
neighborhoods moved the same way earlier and nobody listed them.

**Fix.** `scripts/lifestyle_groups.py` now assigns from `data/reference/lifestyle_area_features.csv`, a frozen area
profile per neighborhood (237 rows): the largest building sample on record for it, taken from the nine committed
snapshots of `data/lifestyle_groups.csv` and this run; each row says which. A neighborhood seen for the first time is
profiled once and appended; nothing is recomputed in a normal run (`--refreeze-area` on purpose). The scaling
parameters are saved explicitly beside the centres (`lifestyle_scaling.csv`: fill value, mean and SD per raw feature);
they reproduce the old indices to 4e-16. `data/lifestyle_group_distances.csv` holds every distance. Tests: assigning
half the neighborhoods, or one alone, gives the same result; a saved profile does not change when the units do.

What it is not: a census of the whole area. The profile is still the median over sampled buildings, and "space for
money" is by nature a market figure. A true area profile (all tracts of the place, counts at a fixed centre) would
need a refit, which is the owner's call.

**The two.** East Rutherford is Little-City: nearest centre at 1.19 against 2.06 for Room-to-Breathe (ratio 0.58), not
close. Patchogue is Little-City: 2.31 against 2.48 (ratio 0.93), a boundary case, listed below; it is a village with a
main street and a railway station, which is what Little-City says. Both are back where they were before the listing
counts shifted, and they stay there because the profile is frozen. Two shown apartments each.

**Held, not moved (owner to decide).** `data/reference/lifestyle_group_overrides.csv`: delete a row to accept the computed group.

| Neighborhood | Kept (today) | Computed | Distance to kept | Distance to computed | Nearest / second |
|---|---|---|---|---|---|
| Fort Lee | middle | new_water | 3.155 | 2.132 | 0.676 |
| Jersey City – McGinley Square | pre_car | settled | 2.208 | 2.077 | 0.941 |
| West New York | new_water | settled | 4.284 | 0.916 | 0.394 |
| Harlem (South) | pre_car | settled | 3.151 | 3.134 | 0.994 |

Only McGinley Square has ranked units (15, none shown); the other three have none.

**Boundary cases** (nearest and second-nearest centre within 10 percent): 33 of 197.

| Neighborhood | Nearest | Second | Ratio | Assigned |
|---|---|---|---|---|
| Harlem (South) | settled | pre_car | 0.994 | pre_car |
| Montgomery | enclave | space | 0.992 | enclave |
| Beacon | space | middle | 0.989 | space |
| LaGrange | space | enclave | 0.989 | space |
| Newtown | space | enclave | 0.988 | space |
| Brookfield | space | enclave | 0.987 | space |
| Bridgeport | space | settled | 0.983 | space |
| Tompkinsville-Stapleton-Clifton-Fox Hills | settled | new_water | 0.982 | settled |
| West Windsor | space | enclave | 0.979 | space |
| Atlantic Highlands | enclave | middle | 0.978 | enclave |
| Jersey City – Journal Square | middle | settled | 0.974 | middle |
| Madison | settled | space | 0.968 | settled |
| Forest Hills | settled | space | 0.964 | settled |
| Morris Park | settled | space | 0.960 | settled |
| North Bergen | new_water | middle | 0.958 | new_water |
| Morris Plains | space | enclave | 0.953 | space |
| Elizabeth | middle | space | 0.950 | middle |
| Clarkstown | space | enclave | 0.946 | space |
| Roxbury | enclave | space | 0.946 | enclave |
| Peekskill | middle | space | 0.944 | middle |
| Jersey City – McGinley Square | settled | pre_car | 0.941 | pre_car |
| Windsor Terrace-South Slope | settled | middle | 0.940 | settled |
| Kew Gardens Hills | middle | settled | 0.938 | middle |
| Cranford | middle | space | 0.935 | middle |
| Patchogue | middle | space | 0.932 | middle |
| Norwalk | new_water | middle | 0.930 | new_water |
| Huntington | middle | enclave | 0.929 | middle |
| Yonkers | middle | new_water | 0.927 | middle |
| Oxford | space | enclave | 0.915 | space |
| Hempstead | settled | space | 0.914 | settled |
| Danbury | middle | space | 0.912 | middle |
| Port Chester | middle | settled | 0.906 | middle |
| Kensington | settled | middle | 0.905 | settled |

## Step 3. Duplicates

- Cause of Avalon Teaneck 215: the two sites publish 716 and 702 sq ft, and the old test required equal sizes. Now
  `parsers.same_listed_unit`: a prefixed label equals its plain form when bedrooms are equal, rents agree within 2
  percent and sizes within 3 percent (or one is not published). `001-215` and `002-215` stay two apartments.
- The unit is moved out of the address into the unit field (2,102 listings carried one; 1,306 had a blank unit field).
  87 pending listings now fail the floor gate, because the unit that was hidden in the address reads as ground floor.
  `addr_key` is unchanged on purpose: 55 passing listings have evidence filed under the key with the unit in it.
- Found on the way: the Continuum (White Plains) was three buildings (`55-57 Bank Street` on its own site, `55` and
  `57 Bank Street` on Greystar and Trulia). After step 1 unit S0904 would have been shown twice. A ranged address now
  joins the listings at either end; the own-site building id is kept.
- Duplicate pairs: master table 1 before (Avalon Teaneck 215, hidden only by a verdict), 0 after; ranked 0 and 0;
  shown 0 and 0 (the test now asserts it). Without the range fix the new elevator rule would have shown 1 pair.
- A unit is never merged into a floor plan (units are placed first). I did NOT implement "a plan row is never merged
  into a unit" literally: a plan row that only repeats a named unit's beds, rent and size (the Arcade's "1 bed, 1 bath,
  $1675" beside unit 302) would otherwise come back as a second card. It is dropped as redundant. Moot now that plan
  rows are not apartments at all.

## Step 4. Only real apartments (owner's rule)

`parsers.listing_kind`, decided at the listing gate (`listings.csv: listing_kind`) and carried to the page data
(`kind`, always `unit` for anything shown). 71 rows that would otherwise be ranked are `not_an_apartment`
(`data/excluded_not_an_apartment.csv`); 16 were shown (list above). Judgment calls, plainly:
- A single-home listing page with no unit number (a Zumper `/listings/` or Trulia `/home/` page of its own) counts as
  one real home. None is shown today. If the owner reads "its own unit identifier" strictly, that is one line.
- `416 Highland Ave - 312` (City of Orange): the row is labelled "1 Bed" but the property's own title names unit 312;
  kept as a real apartment.
- The Agnes Co-Living: the three suite rooms (`123-2`, `255-3`, `448-3`) are private rooms; the Trulia studio and
  one-bedroom rows (203, 311, 443) are whole apartments and stay.
- I did not open the raw Apartment List or Zumper JSON to read their own unit / floor-plan flag; the classification
  rests on `detail_level`, the id, `listing_type` and the label's shape.

## Thin neighborhoods (owner's rule)

46 neighborhoods had one shown apartment; 11 are kept and 35 cut, the same 11 the coordinator measured. Cut reasons:
19 have something open (elevator 14, listing 2, live check 2, dogs 1), 16 score below their
experience's median. Lists above.

## Step 5. Items left open by the check-3 repairs

- D26 (floor-plan rows): fixed, see step 4.
- D23 (neighborhoods ranked on one place): overtaken by the thin-neighborhood rule; the neighborhood score itself is in
  `page_data_extras.py`, which I do not own.
- D21 (Continuum's elevator): unchanged by decision; it is now consistently "open, inferred from height" at every stage.
- D17 / D18 / D4 / D13 / D24 / D27: text, not pipeline.
- "The pet-rent median is over the master table, not the ranked buildings": left. The ranked set depends on the cost
  gate, so the median cannot be taken over it without a loop; a test keeps the two within $10.
- "The city's walk-up class still fails a listing on a nearest-lot match": fixed (step 1). "97 listings pass on the
  high-rise label alone": kept, and now consistent (open fact, never settled).

## Step 6. Bugs found and fixed

| Bug | Effect |
|---|---|
| `rank.py` scored in-unit laundry on the word "yes" anywhere in two joined fields | "laundry: yes" with the amenities column saying `on_site_only` (77 master units), and "(not in unit)", scored as a washer in the apartment. Building part changed for 163 ranked units, by up to 3.1 points |
| `rank.py` dropped any unit whose harvest note said CONFLICT as "sketchy" | 54 master units; 44 of them were only a conflict about dog SIZE. Now one open fact (dogs), or the small-dog question. 12 units returned to the ranking, 2 to the shown list (One Clinton Park) |
| `all_in.py` tested the cap on `round()` | Python rounds $3,000.50 down to $3,000: such a unit passed. Tested on the exact sum now. No unit changed today |
| `gates.py` and `build_master.py` disagreed on "the listing's own lot" (`match_basis` against an address check) | 62 exact-basis matches at another address were used by the gate and ignored by the merge |
| `check_registry.py` had its own elevator logic and its own floor-plan test | Could pass a unit the ranking held open, or the reverse. It now calls the same functions |
| The same complex under three building ids (Continuum) | Units listed twice across "buildings"; up to 8 shown per id |
| A third party's Google key in 268 `photo_url` values (`listings_raw/trulia.csv`, 240 in `listings.csv`) | Stripped in place (only that column changed) and in `gates.py`; a test scans the data files |
| Docstrings and labels that disagreed with the code | `rank.py` ("at most 2 per building", "best 10"), `run_all.py` ("top 10 per neighborhood"), `check_registry.py` ("runs first"; it runs last), `avoid.py` (an output it never writes; "conflicting dog policy" as a drop) |
| `docs/RANKING.md` said the dog part rewards a limit of 40 lb or more | The code already used 25 lb or no limit; the document is corrected |
| Building names were listing titles; park names that are not parks | `parsers.clean_building_name` at the merge (57 shown apartments now have no name and show their address); `parsers.park_name` (28 shown apartments keep the distance and lose a wrong name). "8 Acre Woods" stays: "Woods" is a park word |

Looked at and left: availability dates parse as ISO or "now" only (no year-less dates reach the gate; 66 dates more
than six months old pass the move-in gate and are caught by the staleness rule); `avoid.py` judges "the last six
months" against a fixed 2026-11-15, which keeps runs reproducible but will age; no dead `\\b` escapes were found in
the owned scripts (the doubled backslashes that exist match a literal backslash in page JSON).

## For the owner

1. The four experience overrides above.
2. Whether a single-home listing page with no unit number is a real apartment.
3. `h_trulia.py` now refuses to fetch whenever `trulia.com` is in `raw/_host_kill_shared.json` (it was added during this
   pass, not by me) and without `--i-know`. The other old harvest helpers (voices_fetch, the ev*_fetch scripts) still do not read the file.
4. The experience profiles are frozen samples, not area statistics; a true area profile means a refit.
5. Raw page captures under `raw/` were not scanned for the key.
