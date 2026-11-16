# Checkpoint A: neighborhoods and proposed years

Passing units: 2659 in 693 buildings, across 221 neighborhoods; 114 neighborhoods have 3+ passing places.

Cluster quality (silhouette; higher is cleaner): {5: 0.141, 6: 0.145}. Using k=6.

## Group 1: 8 neighborhoods, 84 places

Distinguishing traits (standard deviations from the average): transit_min +2.5, drive_min +1.8, all_in_med -1.8, park_ha_800m -1.0

| hood         | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Danbury      | Western Connecticut Planning Region       |      24 |           5 |        88.7 |         265   |       2570   |        716 |                1   |           3 |            12.9 |    2252   |       nan |                1.4 |            0.6 |
| Neptune      | Monmouth County                           |       6 |           2 |        97.7 |         227.5 |       2742.5 |        850 |                0.5 |           0 |            17.3 |    2203.5 |       nan |                2.9 |            0.5 |
| West Haven   | South Central Connecticut Planning Region |       9 |           5 |       103.9 |         181   |       2052   |        900 |                2   |           0 |            16.6 |    1178   |       nan |                0.6 |            1.6 |
| Seymour      | Naugatuck Valley Planning Region          |       3 |           2 |       104.3 |         271   |       2179   |        850 |                7   |           0 |            15   |     277   |       nan |                0.5 |            0.9 |
| Beacon Falls | Naugatuck Valley Planning Region          |       8 |           1 |       108.8 |         310   |       1984   |        650 |                2   |           1 |            11.3 |     108   |       nan |              nan   |          nan   |
| Hamden       | South Central Connecticut Planning Region |       5 |           2 |       111.8 |         226   |       2032   |        730 |               11   |           0 |             9.2 |     391   |       nan |                1.7 |            3.9 |
| Burlington   | Burlington County                         |      21 |           1 |       118.2 |         247   |       2551   |        824 |                2   |           0 |            59.4 |    3406   |       nan |                1.6 |            1.1 |
| Mount Holly  | Burlington County                         |       8 |           2 |       120.5 |         257   |       1837   |        700 |                0   |           0 |             6.5 |     824   |       nan |                4.1 |            1.2 |

## Group 2: 36 neighborhoods, 546 places

Distinguishing traits (standard deviations from the average): restaurants_800m -0.8, water_m +0.6, violent_per_1000 -0.6, bars_800m -0.6

| hood                   | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-----------------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Madison                | Brooklyn                                  |       5 |           5 |        23.9 |          70   |       2544   |      800   |                8   |         0   |             7.4 |    1559   |         6 |                2.7 |            1.4 |
| Englewood              | Bergen County                             |      14 |           3 |        32.6 |          85   |       2902   |      766   |                0   |         0   |            11.3 |     623   |       nan |                2.3 |            1.3 |
| Teaneck                | Bergen County                             |       7 |           1 |        37.9 |          93.5 |       2892   |      702   |                1   |         0   |            13.8 |    1951   |       nan |                1.3 |            0.2 |
| East Rutherford        | Bergen County                             |       3 |           2 |        42   |          82   |       2658   |      724   |                3   |         0   |            14.2 |    1516   |       nan |                0.2 |            0.5 |
| Harrison               | Westchester County                        |      23 |           3 |        43.2 |         131   |       3213   |      570   |                0   |         0   |            13.1 |    2799   |         6 |                0.1 |            0.1 |
| Bayonne                | Hudson County                             |      54 |          13 |        45.1 |         100   |       2613   |      763   |                6   |         0   |            17.6 |     853   |       nan |                2.8 |            1.1 |
| Clifton                | Passaic County                            |      22 |           2 |        46   |         107   |       2854   |      858   |                2   |         1   |             3.7 |    2437   |       nan |                1.7 |            2.1 |
| Bloomfield             | Essex County                              |      13 |           4 |        51.4 |          98   |       2506   |      760   |               17   |         1   |             3   |    3842   |       nan |                0.8 |            1.3 |
| Islip                  | Suffolk County                            |       4 |           2 |        51.9 |          99.5 |       2869.5 |      656.5 |                4.5 |         2   |            22.7 |    1958   |         4 |                1   |            1.1 |
| East Orange            | Essex County                              |      17 |          10 |        52   |          98   |       2402   |      805   |                0   |         0   |             5.3 |    3574   |       nan |                4.2 |            4.7 |
| City of Orange         | Essex County                              |      13 |           5 |        53.2 |          83   |       2502   |      770   |                0   |         1   |            15.7 |    4149   |       nan |                4.2 |            5.6 |
| Maplewood              | Essex County                              |       9 |           1 |        54.4 |         113   |       2752   |      815   |               10   |         1   |            10.1 |    4451   |       nan |                0.5 |            1.4 |
| Millburn               | Essex County                              |       3 |           1 |        58.3 |         115   |       2347   |      635   |                7   |         1   |             6.9 |    4113   |       nan |                0.1 |            0.3 |
| Carteret               | Middlesex County                          |       5 |           1 |        58.5 |         108.5 |       2323   |      807   |                0   |         0   |             9.6 |     692   |       nan |                2   |            1.2 |
| Riverdale              | Morris County                             |       4 |           1 |        61.1 |         130   |       2750.5 |      744   |                1   |         0   |             6.5 |     361   |       nan |                0.5 |            1   |
| Chatham                | Morris County                             |       3 |           3 |        63.4 |         128   |       2684   |      850   |                6   |         0   |             9.7 |    2367   |       nan |                0   |            0.2 |
| Woodbridge             | Middlesex County                          |      11 |           3 |        63.7 |         128   |       2906   |      763   |                2   |         0   |             8.1 |    2018   |       nan |                1.4 |            0.8 |
| Berkeley Heights       | Union County                              |      63 |           2 |        65.9 |         143   |       2920   |      718   |                0   |         0   |            19.9 |    4020   |       nan |                0.3 |            0.1 |
| West Haverstraw        | Rockland County                           |       4 |           1 |        67.2 |         nan   |       2622.5 |      750   |                1   |         0   |             7.6 |    1894   |       nan |                2.1 |            0.5 |
| Patchogue              | Suffolk County                            |       3 |           2 |        67.3 |         105   |       2674   |      700   |                8   |         2   |            15.8 |     908   |         5 |                1   |            1.1 |
| Brookhaven             | Suffolk County                            |       4 |           2 |        68.3 |         147   |       2708.5 |      830   |                0   |         0   |             5.9 |    2246   |       nan |                1   |            1.1 |
| Wilton                 | Western Connecticut Planning Region       |       8 |           1 |        68.6 |         nan   |       2904   |      707   |                0   |         0   |             9.6 |    2640   |       nan |                0.1 |            0.8 |
| Parsippany-Troy Hills  | Morris County                             |     114 |           3 |        69.2 |         187   |       2865   |      730   |                3   |         0   |            13.1 |    1061   |         6 |                0.7 |            0.4 |
| Westport               | Western Connecticut Planning Region       |       5 |           2 |        72.3 |         nan   |       2862   |      712   |                0   |         0   |            13.2 |    2155   |       nan |                0.3 |            2.6 |
| East Brunswick         | Middlesex County                          |      19 |           2 |        73.4 |         143   |       2777   |      817   |               17   |         1   |            15.9 |     720   |       nan |                1.2 |            0.5 |
| Peekskill              | Westchester County                        |      16 |           4 |        77.1 |         148   |       2919.5 |      766   |                1.5 |         0.5 |             3.8 |     696.5 |       nan |                2.3 |            0.6 |
| Mount Arlington        | Morris County                             |      10 |           2 |        80.4 |         nan   |       2567   |      890   |                2   |         0   |            28.5 |    1855   |       nan |                0   |            0   |
| Franklin               | Somerset County                           |      17 |           2 |        81.9 |         nan   |       2779   |      746   |                0   |         0   |             6.9 |     435   |       nan |                0.3 |            0.4 |
| Stratford              | Greater Bridgeport Planning Region        |       4 |           1 |        87.6 |         164   |       2367   |      720   |                6   |         0   |             7.5 |     404   |       nan |                0.5 |            1.7 |
| Trumbull               | Greater Bridgeport Planning Region        |      19 |           2 |        87.8 |         nan   |       2492   |      853   |                0   |         0   |             8.7 |    1269   |       nan |                0.8 |            0.8 |
| Milford city (balance) | South Central Connecticut Planning Region |      16 |           6 |        92.9 |         160   |       2452   |      593   |               10   |         0.5 |             6.5 |     535   |       nan |                0.7 |            2.1 |
| Brookfield             | Western Connecticut Planning Region       |       3 |           1 |        97.9 |         nan   |       2769   |      863   |                8   |         0   |            15.1 |     483   |       nan |                0.3 |            0.3 |
| West Windsor           | Mercer County                             |       3 |           1 |        99.2 |         167   |       2812   |      860   |                7   |         0   |             9.8 |    2376   |       nan |                0.5 |            0.3 |
| Montgomery             | Orange County                             |       4 |           1 |       100.8 |         nan   |       2512.5 |      700   |                2   |         0   |            25.9 |    2705   |       nan |                0.3 |            0.2 |
| Middletown             | Orange County                             |       6 |           1 |       103.9 |         nan   |       2482.5 |      763.5 |               10   |         2   |             6.9 |    2063   |       nan |                3.6 |            0.6 |
| Flemington             | Hunterdon County                          |      18 |           4 |       104.7 |         nan   |       2564   |      690   |                8   |         0   |             9.7 |    2441   |       nan |                3   |            0.4 |

## Group 3: 30 neighborhoods, 346 places

Distinguishing traits (standard deviations from the average): violent_per_1000 +1.1, drive_min -1.0, transit_min -0.9, restaurants_800m +0.7

| hood                                  | area          |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:--------------------------------------|:--------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Jamaica                               | Queens        |      11 |           9 |         2.2 |          11.4 |       2629   |      600   |               27   |         2   |             5.5 |    2687   |      11   |                9.8 |            1.7 |
| Jamaica Hills-Briarwood               | Queens        |      12 |          11 |         3.9 |          17.6 |       2431.5 |      620   |               10   |         2   |             4.2 |    1793   |       6   |                2.4 |            2.2 |
| Kew Gardens                           | Queens        |       6 |           6 |         4.2 |          13.6 |       2755.5 |      750   |               24.5 |         3   |             4.4 |    1118.5 |       6   |                3.1 |            2.1 |
| Forest Hills                          | Queens        |       4 |           4 |         9.7 |          30.5 |       2418.5 |      708   |               45   |         1   |             7.6 |    1166   |       6.5 |                2.1 |            1.4 |
| Flushing-Willets Point                | Queens        |      19 |          19 |        11.8 |          44.6 |       2394   |      614.5 |               82   |         3   |             3.7 |     894   |       6   |                2.6 |            2.2 |
| Jackson Heights                       | Queens        |       8 |           8 |        12.8 |          32   |       2161   |      639   |               60.5 |         3   |             4.8 |    1791.5 |       6   |                4.8 |            1.4 |
| Elmhurst                              | Queens        |       3 |           3 |        13.5 |          32   |       2494   |      850   |               69   |         4   |             3.4 |    2721   |       6   |                6.1 |            1.4 |
| Old Astoria-Hallets Point             | Queens        |       4 |           4 |        18.2 |          55   |       2793   |      nan   |               12.5 |         1   |             6   |     200.5 |       7.5 |                3.7 |            1.7 |
| Bedford-Stuyvesant (East)             | Brooklyn      |       3 |           3 |        18.7 |          38.5 |       2944   |      nan   |               21   |         6   |             3.3 |    3290   |       8   |                5.6 |            1.2 |
| Prospect Lefferts Gardens-Wingate     | Brooklyn      |       3 |           3 |        21.1 |          50   |       2944   |      nan   |               17   |         6   |             6.6 |    1447   |       7   |                5.9 |            1   |
| East Flatbush-Erasmus                 | Brooklyn      |       9 |           9 |        21.8 |          55   |       2893   |      600   |               14   |         3   |            11.7 |    1384   |       7   |                6.6 |            1.2 |
| East Harlem (North)                   | Manhattan     |       5 |           5 |        22   |          57.5 |       2903   |      400   |               41   |         1   |             5.4 |     572   |       6   |               11.2 |            1.3 |
| Hempstead                             | Nassau County |      11 |           6 |        22.4 |          50   |       2821   |      820   |                8   |         1   |             9   |    1922   |     nan   |                5.6 |            2.3 |
| Mott Haven-Port Morris                | Bronx         |       9 |           9 |        22.6 |          60.5 |       2575   |      734   |               13   |         0   |             3.2 |     250   |      12   |               17.2 |            2.6 |
| East Flatbush-Farragut                | Brooklyn      |       5 |           5 |        22.7 |          60   |       2891   |      nan   |                5   |         0   |             7   |    2898   |       6   |                6.6 |            1.2 |
| Flatbush                              | Brooklyn      |       4 |           4 |        23   |          50   |       2831.5 |      700   |               25   |         4.5 |             9   |     823   |       7   |                4.1 |            0.8 |
| Harlem (North)                        | Manhattan     |       7 |           7 |        24.5 |          55   |       2798   |      466   |               21   |         2   |             3   |     543   |       7   |                8.9 |            0.8 |
| Midwood                               | Brooklyn      |       4 |           4 |        24.7 |          60   |       2881   |      650   |                5   |         0   |             7.9 |    2719   |       8   |                4.1 |            0.8 |
| Manhattanville-West Harlem            | Manhattan     |       4 |           3 |        25.1 |          58   |       2925.5 |      nan   |               29   |         4   |             2.2 |     261.5 |       5.5 |                4.6 |            1.3 |
| Hamilton Heights-Sugar Hill           | Manhattan     |       3 |           3 |        25.5 |          56   |       2636   |      nan   |               31   |         2   |             1.2 |     494   |      10   |                4.6 |            1.3 |
| Rockaway Beach-Arverne-Edgemere       | Queens        |       4 |           4 |        25.8 |          62.8 |       2881   |      650   |                4   |         2.5 |             4.6 |     269   |       7   |                3.2 |            0.6 |
| Washington Heights (South)            | Manhattan     |       3 |           3 |        26.3 |          56   |       2683   |      nan   |               13   |         2   |             4.2 |     442   |       6   |                6   |            1.9 |
| Flatbush (West)-Ditmas Park-Parkville | Brooklyn      |       4 |           4 |        26.4 |          62.5 |       2786.5 |      650   |                7.5 |         1   |            17.8 |    2552.5 |       7   |                4.1 |            0.8 |
| Norwood                               | Bronx         |       3 |           3 |        27.6 |          82.6 |       2202   |      750   |                3   |         0   |             3   |     811   |       8   |               10.3 |            2.2 |
| Washington Heights (North)            | Manhattan     |       6 |           5 |        28.4 |          64   |       2852   |      700   |               18   |         6.5 |             2.3 |     543   |       6   |                5.3 |            1.8 |
| Inwood                                | Manhattan     |       5 |           5 |        28.9 |          70   |       2838   |      nan   |               23   |         7   |             2.1 |     475   |       6   |                5.3 |            1.8 |
| Jersey City – Newport                 | Hudson County |       4 |           1 |        35.2 |          55   |       3129   |      443.5 |               22   |         1   |             8   |      68   |     nan   |                4.9 |            2.9 |
| Jersey City – McGinley Square         | Hudson County |      26 |           4 |        36.7 |          79   |       2596   |      621   |               15   |         2   |            10.1 |    1402   |      14   |                4.9 |            2.9 |
| Jersey City – Journal Square          | Hudson County |     112 |           8 |        37   |          71   |       2908   |      530   |               12   |         1   |            20.3 |     766   |     nan   |                4.9 |            2.9 |
| Jersey City – West Side               | Hudson County |      45 |           6 |        40.2 |          85   |       2602   |      615   |                5   |         0   |            10.7 |     858   |     nan   |                4.9 |            2.9 |

## Group 4: 2 neighborhoods, 169 places

Distinguishing traits (standard deviations from the average): bfloors +6.5, water_m -0.9, all_in_med +0.8, drive_min -0.6

| hood         | area               |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------|:-------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| New Rochelle | Westchester County |      93 |          18 |        28.9 |           101 |       2921   |      648   |                  7 |           1 |            13.9 |       844 |        26 |                1.6 |            0.7 |
| Yonkers      | Westchester County |      76 |          19 |        37.9 |           100 |       2882.5 |      671.5 |                  2 |           1 |             5   |        75 |        25 |                3.9 |            1.5 |

## Group 5: 24 neighborhoods, 584 places

Distinguishing traits (standard deviations from the average): water_m -0.8, bars_800m -0.5, all_in_med +0.5, park_ha_800m +0.5

| hood                           | area                                |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------------------------|:------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Valley Stream                  | Nassau County                       |       3 |           3 |        13.5 |          43   |       2871   |      806   |               17   |           1 |             6   |     773   |       nan |                1.6 |            0.3 |
| Bay Terrace-Clearview          | Queens                              |       3 |           3 |        17.3 |          65   |       2753   |      800   |                9   |           0 |            14.4 |     193   |         6 |                2.6 |            2.2 |
| Long Beach                     | Nassau County                       |       5 |           3 |        25.8 |          64   |       2771   |      715.5 |                8   |           1 |            26.5 |     596   |       nan |                0.8 |            0   |
| Fort Lee                       | Bergen County                       |       9 |           3 |        28.3 |          76   |       3114   |      766   |               34   |           1 |             4.8 |     434   |       nan |                1.1 |            1   |
| Bath Beach                     | Brooklyn                            |       4 |           4 |        28.8 |          80   |       2224   |      650   |                8   |           0 |             0.8 |     140.5 |         6 |                2   |            0.9 |
| Mount Vernon                   | Westchester County                  |       8 |           2 |        30   |         100   |       2676.5 |      567.5 |                8   |           1 |             8.7 |     248   |       nan |                5.5 |            2.7 |
| Weehawken                      | Hudson County                       |       6 |           2 |        31.3 |          62   |       3090   |      802   |               11   |           0 |             3.2 |      82   |       nan |                1.3 |            1.1 |
| Riverdale-Spuyten Duyvil       | Bronx                               |       7 |           6 |        32   |          85   |       2803   |      875.5 |               11   |           0 |             2.8 |     688   |         7 |                3.4 |            2.6 |
| Glen Cove                      | Nassau County                       |       3 |           1 |        32.7 |         106   |       2900   |      570   |               20   |           1 |             4.5 |     421   |       nan |                1.1 |            0.2 |
| West New York                  | Hudson County                       |       8 |           5 |        33.2 |          67.5 |       2468.5 |      694.5 |                9.5 |           0 |             4.2 |     421   |       nan |                2.4 |            1.1 |
| North Bergen                   | Hudson County                       |      12 |           5 |        34.8 |          71   |       3022   |      722   |               11   |           0 |             5.1 |    1311   |       nan |                1.3 |            1.3 |
| Bogota                         | Bergen County                       |      16 |           2 |        35.6 |          92   |       2871   |      658   |                2   |           0 |             6.9 |     123   |       nan |                0.7 |            0.1 |
| Hackensack                     | Bergen County                       |      43 |          12 |        37.1 |         100   |       2827   |      735   |                7   |           1 |             4.6 |     498   |       nan |                2.4 |            1.3 |
| Jersey City – Bergen-Lafayette | Hudson County                       |     136 |          10 |        38.5 |          85   |       2955   |      532   |                3   |           0 |             0.6 |     947   |       nan |                4.9 |            2.9 |
| Port Chester                   | Westchester County                  |      59 |           5 |        41.5 |         106   |       2903   |      567   |               10   |           0 |            11.3 |     300   |       nan |                0.8 |            0.4 |
| Belleville                     | Essex County                        |       9 |           2 |        44.1 |         100   |       2402   |      791   |                5   |           1 |             6.6 |     450   |       nan |                2.4 |            2.9 |
| White Plains                   | Westchester County                  |      66 |          17 |        44.5 |         115   |       3000.5 |      632   |               10   |           0 |             3.1 |     240   |        15 |                1.1 |            0.5 |
| Hawthorne                      | Passaic County                      |       3 |           1 |        46.4 |         122   |       3002   |      815   |                3   |           0 |             9.3 |     237   |       nan |                0.1 |            0.6 |
| Harrison                       | Hudson County                       |      44 |          11 |        46.9 |          77   |       2746.5 |      603   |               10   |           1 |             2.4 |     180   |       nan |                2.1 |            1.1 |
| Elizabeth                      | Union County                        |      13 |           1 |        50.4 |         116   |       2766   |      772   |                0   |           0 |            34.2 |      16   |       nan |                3.4 |            4.8 |
| Wayne                          | Passaic County                      |       4 |           2 |        54.5 |         107   |       2712   |      600   |                8   |           1 |             3.6 |     180   |       nan |                1   |            0.5 |
| South Orange                   | Essex County                        |      10 |           1 |        57.3 |         107   |       2862.5 |      669   |               16   |           0 |             3.1 |    2676   |       nan |                1   |            1.2 |
| Norwalk                        | Western Connecticut Planning Region |      97 |          11 |        63.1 |         149   |       2916   |      787   |               15   |           0 |             1.3 |     327   |         7 |                0.5 |            1.2 |
| Haverstraw                     | Rockland County                     |      16 |           3 |        67   |         nan   |       2910   |      755   |                1   |           0 |            10.2 |      57   |       nan |                2.1 |            0.5 |

## Group 6: 14 neighborhoods, 789 places

Distinguishing traits (standard deviations from the average): bars_800m +1.2, restaurants_800m +0.9, drive_min +0.7, transit_min +0.6

| hood                   | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-----------------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Jersey City – Downtown | Hudson County                             |       9 |           6 |        34.9 |          70   |       2895   |      540   |                 41 |         4   |             2.4 |     531   |       nan |                4.9 |            2.9 |
| Newark                 | Essex County                              |      54 |          17 |        46.9 |          68   |       2442   |      634   |                 40 |         5   |             1.9 |     520   |         6 |                5.2 |            6.9 |
| Stamford               | Western Connecticut Planning Region       |     166 |          44 |        52.8 |         115   |       2831.5 |      705   |                 27 |         5   |             3   |     804   |         8 |                1.5 |            1.2 |
| Montclair              | Essex County                              |      12 |           3 |        53   |         112.5 |       2750   |      545   |                 64 |         3   |             6.6 |    4317   |       nan |                0.8 |            0.9 |
| Rahway                 | Union County                              |       7 |           3 |        57.4 |          98   |       2568   |      665   |                  9 |         4   |             9.2 |      81   |       nan |                1.9 |            0.8 |
| Dover                  | Morris County                             |      41 |           1 |        74.8 |         172   |       2562   |      787   |                 27 |         7   |             2.2 |    2682   |       nan |                0.8 |            0.6 |
| New Brunswick          | Middlesex County                          |      21 |           5 |        75.1 |         122   |       2911   |      750   |                 30 |         4   |             3.9 |     365   |         2 |                5.1 |            1.6 |
| Bound Brook            | Somerset County                           |       5 |           2 |        81.6 |         136   |       2605   |      789   |                 13 |         2   |             4.4 |     283   |       nan |                1.2 |            0.7 |
| Bridgeport             | Greater Bridgeport Planning Region        |     108 |           7 |        82.7 |         151   |       2904   |      725   |                  3 |         0   |            12.5 |      75   |       nan |                2.5 |            3.4 |
| Somerville             | Somerset County                           |       7 |           2 |        86.2 |         151   |       3008   |      928   |                 19 |         4   |             6.1 |     475   |       nan |                1.3 |            0.9 |
| Red Bank               | Monmouth County                           |       4 |           1 |        90.4 |         157   |       2867   |      740   |                 18 |         1   |             5.5 |     231   |       nan |                2.3 |            1   |
| Shelton                | Naugatuck Valley Planning Region          |      14 |           5 |        97.6 |         241   |       2582.5 |      801.5 |                  8 |         1.5 |             5.9 |      88.5 |       nan |                0.3 |            1.1 |
| Long Branch            | Monmouth County                           |      11 |           1 |       101.5 |         175   |       2569   |      645   |                 13 |         2   |             8.2 |     335   |       nan |                2.3 |            0.5 |
| New Haven              | South Central Connecticut Planning Region |     330 |          26 |       108.4 |         181   |       2427   |      653   |                 55 |        17   |             4.4 |    1130   |       nan |                4   |            6.1 |

## Neighborhoods with fewer than 3 passing places (not shown on the page)

| hood                                           | area                                      | state   |   units |   drive_min |   all_in_med |
|:-----------------------------------------------|:------------------------------------------|:--------|--------:|------------:|-------------:|
| Jamaica Estates-Holliswood                     | Queens                                    | NY      |       1 |         6.4 |       2394   |
| Kew Gardens Hills                              | Queens                                    | NY      |       1 |         7.3 |       2378   |
| Pomonok-Electchester-Hillcrest                 | Queens                                    | NY      |       1 |         7.9 |       2994   |
| North Corona                                   | Queens                                    | NY      |       2 |        10.1 |       2641.5 |
| Rego Park                                      | Queens                                    | NY      |       1 |        10.6 |       2529   |
| Middle Village                                 | Queens                                    | NY      |       1 |        11.8 |       1979   |
| East New York (North)                          | Brooklyn                                  | NY      |       2 |        11.9 |       2814.5 |
| Murray Hill-Broadway Flushing                  | Queens                                    | NY      |       1 |        11.9 |       2118   |
| Ocean Hill                                     | Brooklyn                                  | NY      |       2 |        13.6 |       2746.5 |
| Astoria (East)-Woodside (North)                | Queens                                    | NY      |       1 |        14.9 |       2694   |
| Lynbrook                                       | Nassau County                             | NY      |       2 |        15   |       3005   |
| Bushwick (West)                                | Brooklyn                                  | NY      |       1 |        17.3 |       3044   |
| Sunnyside                                      | Queens                                    | NY      |       2 |        17.4 |       2361   |
| Astoria (Central)                              | Queens                                    | NY      |       2 |        17.5 |       2478   |
| Long Island City-Hunters Point                 | Queens                                    | NY      |       1 |        18.9 |       1577   |
| Bedford-Stuyvesant (West)                      | Brooklyn                                  | NY      |       2 |        20.3 |       2661   |
| Mineola                                        | Nassau County                             | NY      |       2 |        20.8 |       2993   |
| Crown Heights (North)                          | Brooklyn                                  | NY      |       1 |        20.8 |       2979   |
| Morris Park                                    | Bronx                                     | NY      |       1 |        21.2 |       2302   |
| Pelham Bay-Country Club-City Island            | Bronx                                     | NY      |       1 |        21.4 |       2983   |
| Murray Hill-Kips Bay                           | Manhattan                                 | NY      |       1 |        21.6 |       3188   |
| East Midtown-Turtle Bay                        | Manhattan                                 | NY      |       1 |        22.2 |       2393   |
| Upper East Side-Lenox Hill-Roosevelt Island    | Manhattan                                 | NY      |       1 |        22.3 |       2988   |
| Flatlands                                      | Brooklyn                                  | NY      |       2 |        22.6 |       2224.5 |
| Concourse-Concourse Village                    | Bronx                                     | NY      |       1 |        22.6 |       2438   |
| East Harlem (South)                            | Manhattan                                 | NY      |       1 |        23.8 |       2578   |
| Harlem (South)                                 | Manhattan                                 | NY      |       2 |        23.8 |       2955.5 |
| Tremont                                        | Bronx                                     | NY      |       1 |        24.4 |       2187   |
| Sheepshead Bay-Manhattan Beach-Gerritsen Beach | Brooklyn                                  | NY      |       2 |        24.6 |       1979   |
| Brighton Beach                                 | Brooklyn                                  | NY      |       2 |        24.9 |       2769.5 |
| Pelham Parkway-Van Nest                        | Bronx                                     | NY      |       2 |        25   |       2403   |
| Mount Hope                                     | Bronx                                     | NY      |       2 |        25.1 |       1975.5 |
| Gravesend (East)-Homecrest                     | Brooklyn                                  | NY      |       2 |        25.6 |       2536.5 |
| Gravesend (South)                              | Brooklyn                                  | NY      |       2 |        26.2 |       2286.5 |
| Windsor Terrace-South Slope                    | Brooklyn                                  | NY      |       1 |        26.2 |       2779   |
| Kensington                                     | Brooklyn                                  | NY      |       1 |        26.3 |       2844   |
| Upper West Side-Lincoln Square                 | Manhattan                                 | NY      |       1 |        26.7 |       2938   |
| Williamsbridge-Olinville                       | Bronx                                     | NY      |       1 |        27   |       2108   |
| Upper West Side-Manhattan Valley               | Manhattan                                 | NY      |       2 |        27   |       2960.5 |
| Coney Island-Sea Gate                          | Brooklyn                                  | NY      |       1 |        27.3 |       1970   |
| Upper West Side (Central)                      | Manhattan                                 | NY      |       1 |        27.4 |       3038   |
| University Heights (South)-Morris Heights      | Bronx                                     | NY      |       1 |        27.8 |       1880   |
| Financial District-Battery Park City           | Manhattan                                 | NY      |       1 |        28.1 |       3103   |
| Bensonhurst                                    | Brooklyn                                  | NY      |       2 |        28.4 |       2186.5 |
| Gravesend (West)                               | Brooklyn                                  | NY      |       1 |        29   |       2494   |
| Kingsbridge Heights-Van Cortlandt Village      | Bronx                                     | NY      |       1 |        29.1 |       2238   |
| Bedford Park                                   | Bronx                                     | NY      |       1 |        29.1 |       2698   |
| Kingsbridge-Marble Hill                        | Bronx                                     | NY      |       1 |        30.9 |       2478   |
| Bay Ridge                                      | Brooklyn                                  | NY      |       2 |        31.8 |       2314   |
| Larchmont                                      | Westchester County                        | NY      |       1 |        31.9 |       2803   |
| Union City                                     | Hudson County                             | NJ      |       2 |        32.8 |       2049.5 |
| Cliffside Park                                 | Bergen County                             | NJ      |       2 |        32.9 |       3089.5 |
| Amityville                                     | Suffolk County                            | NY      |       1 |        33.1 |       3171   |
| Edgewater                                      | Bergen County                             | NJ      |       2 |        33.4 |       2944.5 |
| Jersey City – The Heights                      | Hudson County                             | NJ      |       1 |        35.2 |       3141   |
| Hoboken                                        | Hudson County                             | NJ      |       1 |        35.6 |       2602   |
| Lindenhurst                                    | Suffolk County                            | NY      |       1 |        38.8 |       3166   |
| Dumont                                         | Bergen County                             | NJ      |       1 |        39.7 |       2147   |
| Jersey City – Greenville                       | Hudson County                             | NJ      |       2 |        41   |       1924.5 |
| Tompkinsville-Stapleton-Clifton-Fox Hills      | Staten Island                             | NY      |       1 |        42.1 |       2361   |
| Greenburgh                                     | Westchester County                        | NY      |       1 |        45   |       3203   |
| St. George-New Brighton                        | Staten Island                             | NY      |       1 |        45.8 |       2944   |
| Kearny                                         | Hudson County                             | NJ      |       1 |        46.1 |       2002   |
| Paterson                                       | Passaic County                            | NJ      |       1 |        46.3 |       1788   |
| Huntington                                     | Suffolk County                            | NY      |       2 |        47.3 |       3153.5 |
| New Springville-Willowbrook-Bulls Head-Travis  | Staten Island                             | NY      |       1 |        47.8 |       2579   |
| Ridgewood                                      | Bergen County                             | NJ      |       1 |        49.3 |       2527   |
| Tarrytown                                      | Westchester County                        | NY      |       1 |        49.3 |       2003   |
| Haledon                                        | Passaic County                            | NJ      |       1 |        49.9 |       2224   |
| Irvington                                      | Essex County                              | NJ      |       2 |        53.7 |       1342   |
| Union                                          | Union County                              | NJ      |       2 |        55.5 |       2959   |
| Nyack                                          | Rockland County                           | NY      |       2 |        55.9 |       2940   |
| Montvale                                       | Bergen County                             | NJ      |       1 |        56.6 |       2847   |
| Smithtown                                      | Suffolk County                            | NY      |       1 |        58.8 |       3211   |
| Springfield                                    | Union County                              | NJ      |       2 |        59   |       2767   |
| Clarkstown                                     | Rockland County                           | NY      |       1 |        59.3 |       3065   |
| Cranford                                       | Union County                              | NJ      |       1 |        59.9 |       3109   |
| Summit                                         | Union County                              | NJ      |       2 |        62.2 |       2547.5 |
| Mount Kisco                                    | Westchester County                        | NY      |       1 |        63.3 |       2698   |
| Garwood                                        | Union County                              | NJ      |       1 |        63.9 |       2949   |
| Scotch Plains                                  | Union County                              | NJ      |       1 |        65.5 |       2409   |
| Madison                                        | Morris County                             | NJ      |       1 |        68.3 |       2316   |
| Watchung                                       | Somerset County                           | NJ      |       2 |        70.8 |       2869   |
| Morris Plains                                  | Morris County                             | NJ      |       1 |        71.5 |       2637   |
| Plainfield                                     | Union County                              | NJ      |       1 |        71.5 |       2432   |
| South Plainfield                               | Middlesex County                          | NJ      |       1 |        72.2 |       2393   |
| Aberdeen                                       | Monmouth County                           | NJ      |       1 |        75.4 |       2392   |
| Piscataway                                     | Middlesex County                          | NJ      |       1 |        76.4 |       2672   |
| Rockaway                                       | Morris County                             | NJ      |       1 |        77.1 |       2737   |
| Old Bridge                                     | Middlesex County                          | NJ      |       1 |        79.2 |       2770   |
| North Brunswick                                | Middlesex County                          | NJ      |       1 |        80.3 |       2347   |
| Fairfield                                      | Greater Bridgeport Planning Region        | CT      |       2 |        81.2 |       2712.5 |
| Roxbury                                        | Morris County                             | NJ      |       2 |        83.2 |       2812.5 |
| Atlantic Highlands                             | Monmouth County                           | NJ      |       1 |        92.2 |       2837   |
| Newtown                                        | Western Connecticut Planning Region       | CT      |       1 |        97.3 |       2479   |
| Ansonia                                        | Naugatuck Valley Planning Region          | CT      |       1 |        99.1 |       1696   |
| Princeton                                      | Mercer County                             | NJ      |       1 |        99.4 |       2773   |
| Orange                                         | South Central Connecticut Planning Region | CT      |       1 |        99.8 |       2692   |
| Wallkill                                       | Orange County                             | NY      |       1 |       101.3 |       2615   |
| Newburgh                                       | Orange County                             | NY      |       2 |       103.3 |       1444   |
| Beacon                                         | Dutchess County                           | NY      |       1 |       106.6 |       3097   |
| Bordentown                                     | Burlington County                         | NJ      |       1 |       107.2 |       2452   |
| Oxford                                         | Naugatuck Valley Planning Region          | CT      |       1 |       109.9 |       2804   |
| LaGrange                                       | Dutchess County                           | NY      |       1 |       117.2 |       2597   |
| North Haven                                    | South Central Connecticut Planning Region | CT      |       1 |       118.2 |       1482   |
| Waterbury                                      | Naugatuck Valley Planning Region          | CT      |       1 |       118.7 |       1666   |
| New Paltz                                      | Ulster County                             | NY      |       2 |       119.3 |       2669.5 |
