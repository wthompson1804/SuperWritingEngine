# Checkpoint A: neighborhoods and proposed years

Passing units: 2042 in 633 buildings, across 201 neighborhoods; 101 neighborhoods have 3+ passing places.

Cluster quality (silhouette; higher is cleaner): {5: 0.178, 6: 0.18}. Using k=6.

## Group 1: 8 neighborhoods, 83 places

Distinguishing traits (standard deviations from the average): transit_min +2.4, drive_min +1.7, all_in_med -1.6, park_ha_800m -1.0

| hood         | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Danbury      | Western Connecticut Planning Region       |      24 |           5 |        88.7 |         265   |       2570   |        716 |                1   |           3 |            12.9 |    2252   |       nan |                1.4 |            0.6 |
| Neptune      | Monmouth County                           |       6 |           2 |        97.7 |         227.5 |       2742.5 |        850 |                0.5 |           0 |            17.3 |    2203.5 |       nan |                2.9 |            0.5 |
| West Haven   | South Central Connecticut Planning Region |       9 |           5 |       103.9 |         181   |       2052   |        900 |                2   |           0 |            16.6 |    1178   |       nan |                0.6 |            1.6 |
| Seymour      | Naugatuck Valley Planning Region          |       3 |           2 |       104.3 |         271   |       2179   |        850 |                7   |           0 |            15   |     277   |       nan |                0.5 |            0.9 |
| Beacon Falls | Naugatuck Valley Planning Region          |       8 |           1 |       108.8 |         310   |       1984   |        650 |                2   |           1 |            11.3 |     108   |       nan |              nan   |          nan   |
| Hamden       | South Central Connecticut Planning Region |       5 |           2 |       111.8 |         226   |       2032   |        730 |               11   |           0 |             9.2 |     391   |       nan |                1.7 |            3.9 |
| Burlington   | Burlington County                         |      20 |           1 |       118.2 |         247   |       2543.5 |        824 |                2   |           0 |            59.4 |    3406   |       nan |                1.6 |            1.1 |
| Mount Holly  | Burlington County                         |       8 |           2 |       120.5 |         257   |       1837   |        700 |                0   |           0 |             6.5 |     824   |       nan |                4.1 |            1.2 |

## Group 2: 37 neighborhoods, 416 places

Distinguishing traits (standard deviations from the average): water_m +0.7, restaurants_800m -0.6, bars_800m -0.6, violent_per_1000 -0.4

| hood                                  | area                                |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:--------------------------------------|:------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Bay Terrace-Clearview                 | Queens                              |       3 |           3 |        17.3 |          65   |       2753   |      800   |                9   |           0 |            14.4 |     193   |         6 |                2.6 |            2.2 |
| East Flatbush-Farragut                | Brooklyn                            |       5 |           5 |        22.7 |          60   |       2891   |      nan   |                5   |           0 |             7   |    2898   |         6 |                6.6 |            1.2 |
| Madison                               | Brooklyn                            |       5 |           5 |        23.9 |          70   |       2544   |      800   |                8   |           0 |             7.4 |    1559   |         6 |                2.7 |            1.4 |
| Flatbush (West)-Ditmas Park-Parkville | Brooklyn                            |       4 |           4 |        26.4 |          62.5 |       2786.5 |      650   |                7.5 |           1 |            17.8 |    2552.5 |         7 |                4.1 |            0.8 |
| Englewood                             | Bergen County                       |      12 |           3 |        33.8 |          85   |       2887   |      766   |                0   |           0 |            11.3 |     770   |       nan |                2.3 |            1.3 |
| Teaneck                               | Bergen County                       |       7 |           1 |        37.9 |          93.5 |       2892   |      702   |                1   |           0 |            13.8 |    1951   |       nan |                1.3 |            0.2 |
| East Rutherford                       | Bergen County                       |       3 |           2 |        42   |          82   |       2658   |      724   |                3   |           0 |            14.2 |    1516   |       nan |                0.2 |            0.5 |
| Bayonne                               | Hudson County                       |      52 |          13 |        45.1 |         100   |       2613   |      763   |                6   |           0 |            17   |     853   |       nan |                2.8 |            1.1 |
| Clifton                               | Passaic County                      |      13 |           2 |        46   |         107   |       2774   |      788   |                2   |           1 |             3.7 |    2437   |       nan |                1.7 |            2.1 |
| Bloomfield                            | Essex County                        |      13 |           4 |        51.4 |          98   |       2506   |      760   |               17   |           1 |             3   |    3842   |       nan |                0.8 |            1.3 |
| Islip                                 | Suffolk County                      |       4 |           2 |        51.9 |          99.5 |       2869.5 |      656.5 |                4.5 |           2 |            22.7 |    1958   |         4 |                1   |            1.1 |
| East Orange                           | Essex County                        |      16 |          10 |        51.9 |          98   |       2397   |      764   |                0   |           0 |             4.7 |    3610.5 |       nan |                4.2 |            4.7 |
| City of Orange                        | Essex County                        |      13 |           5 |        53.2 |          83   |       2502   |      770   |                0   |           1 |            15.7 |    4149   |       nan |                4.2 |            5.6 |
| Maplewood                             | Essex County                        |       6 |           1 |        54.4 |         113   |       2722   |      779   |               10   |           1 |            10.1 |    4451   |       nan |                0.5 |            1.4 |
| South Orange                          | Essex County                        |       9 |           1 |        57.3 |         107   |       2834   |      669   |               16   |           0 |             3.1 |    2676   |       nan |                1   |            1.2 |
| Millburn                              | Essex County                        |       3 |           1 |        58.3 |         115   |       2347   |      635   |                7   |           1 |             6.9 |    4113   |       nan |                0.1 |            0.3 |
| Carteret                              | Middlesex County                    |       5 |           1 |        58.5 |         108.5 |       2323   |      807   |                0   |           0 |             9.6 |     692   |       nan |                2   |            1.2 |
| Riverdale                             | Morris County                       |       4 |           1 |        61.1 |         130   |       2750.5 |      744   |                1   |           0 |             6.5 |     361   |       nan |                0.5 |            1   |
| Chatham                               | Morris County                       |       3 |           3 |        63.4 |         128   |       2684   |      850   |                6   |           0 |             9.7 |    2367   |       nan |                0   |            0.2 |
| Woodbridge                            | Middlesex County                    |      10 |           3 |        63.7 |         128   |       2876.5 |      745.5 |                2   |           0 |             8.1 |    2018   |       nan |                1.4 |            0.8 |
| Berkeley Heights                      | Union County                        |       3 |           1 |        65.9 |         nan   |       2814   |      580   |                0   |           0 |            19.9 |    4020   |       nan |                0.3 |            0.1 |
| West Haverstraw                       | Rockland County                     |       4 |           1 |        67.2 |         nan   |       2622.5 |      750   |                1   |           0 |             7.6 |    1894   |       nan |                2.1 |            0.5 |
| Patchogue                             | Suffolk County                      |       3 |           2 |        67.3 |         105   |       2674   |      700   |                8   |           2 |            15.8 |     908   |         5 |                1   |            1.1 |
| Brookhaven                            | Suffolk County                      |       4 |           2 |        68.3 |         147   |       2708.5 |      830   |                0   |           0 |             5.9 |    2246   |       nan |                1   |            1.1 |
| Wilton                                | Western Connecticut Planning Region |       8 |           1 |        68.6 |         nan   |       2904   |      707   |                0   |           0 |             9.6 |    2640   |       nan |                0.1 |            0.8 |
| Parsippany-Troy Hills                 | Morris County                       |      93 |           3 |        69.2 |         187   |       2835   |      730   |                3   |           0 |            13.1 |    1061   |         6 |                0.7 |            0.4 |
| Westport                              | Western Connecticut Planning Region |       5 |           2 |        72.3 |         nan   |       2862   |      712   |                0   |           0 |            13.2 |    2155   |       nan |                0.3 |            2.6 |
| East Brunswick                        | Middlesex County                    |      17 |           2 |        73.4 |         143   |       2775   |      817   |               17   |           1 |            15.9 |     720   |       nan |                1.2 |            0.5 |
| Peekskill                             | Westchester County                  |       9 |           3 |        77.1 |         148   |       2654   |      800   |                2   |           0 |             4.4 |    1259   |       nan |                2.3 |            0.6 |
| Mount Arlington                       | Morris County                       |      10 |           2 |        80.4 |         nan   |       2567   |      890   |                2   |           0 |            28.5 |    1855   |       nan |                0   |            0   |
| Franklin                              | Somerset County                     |      17 |           2 |        81.9 |         nan   |       2779   |      746   |                0   |           0 |             6.9 |     435   |       nan |                0.3 |            0.4 |
| Trumbull                              | Greater Bridgeport Planning Region  |      19 |           2 |        87.8 |         nan   |       2492   |      853   |                0   |           0 |             8.7 |    1269   |       nan |                0.8 |            0.8 |
| Brookfield                            | Western Connecticut Planning Region |       3 |           1 |        97.9 |         nan   |       2769   |      863   |                8   |           0 |            15.1 |     483   |       nan |                0.3 |            0.3 |
| West Windsor                          | Mercer County                       |       3 |           1 |        99.2 |         167   |       2812   |      860   |                7   |           0 |             9.8 |    2376   |       nan |                0.5 |            0.3 |
| Montgomery                            | Orange County                       |       4 |           1 |       100.8 |         nan   |       2512.5 |      700   |                2   |           0 |            25.9 |    2705   |       nan |                0.3 |            0.2 |
| Middletown                            | Orange County                       |       6 |           1 |       103.9 |         nan   |       2482.5 |      763.5 |               10   |           2 |             6.9 |    2063   |       nan |                3.6 |            0.6 |
| Flemington                            | Hunterdon County                    |      18 |           4 |       104.7 |         nan   |       2564   |      690   |                8   |           0 |             9.7 |    2441   |       nan |                3   |            0.4 |

## Group 3: 19 neighborhoods, 170 places

Distinguishing traits (standard deviations from the average): violent_per_1000 +1.3, drive_min -1.2, restaurants_800m +1.1, transit_min -1.1

| hood                              | area          |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:----------------------------------|:--------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Jamaica                           | Queens        |      11 |           9 |         2.2 |          11.4 |       2629   |      600   |               27   |         2   |             5.5 |    2687   |      11   |                9.8 |            1.7 |
| Jamaica Hills-Briarwood           | Queens        |      12 |          11 |         3.9 |          17.6 |       2431.5 |      620   |               10   |         2   |             4.2 |    1793   |       6   |                2.4 |            2.2 |
| Kew Gardens                       | Queens        |       6 |           6 |         4.2 |          13.6 |       2755.5 |      750   |               24.5 |         3   |             4.4 |    1118.5 |       6   |                3.1 |            2.1 |
| Forest Hills                      | Queens        |       4 |           4 |         9.7 |          30.5 |       2418.5 |      708   |               45   |         1   |             7.6 |    1166   |       6.5 |                2.1 |            1.4 |
| Flushing-Willets Point            | Queens        |      19 |          19 |        11.8 |          44.6 |       2394   |      614.5 |               82   |         3   |             3.7 |     894   |       6   |                2.6 |            2.2 |
| Jackson Heights                   | Queens        |       8 |           8 |        12.8 |          32   |       2161   |      639   |               60.5 |         3   |             4.8 |    1791.5 |       6   |                4.8 |            1.4 |
| Elmhurst                          | Queens        |       3 |           3 |        13.5 |          32   |       2494   |      850   |               69   |         4   |             3.4 |    2721   |       6   |                6.1 |            1.4 |
| Bedford-Stuyvesant (East)         | Brooklyn      |       3 |           3 |        18.7 |          38.5 |       2944   |      nan   |               21   |         6   |             3.3 |    3290   |       8   |                5.6 |            1.2 |
| Prospect Lefferts Gardens-Wingate | Brooklyn      |       3 |           3 |        21.1 |          50   |       2944   |      nan   |               17   |         6   |             6.6 |    1447   |       7   |                5.9 |            1   |
| East Flatbush-Erasmus             | Brooklyn      |       7 |           7 |        21.8 |          55   |       2794   |      600   |               19   |         6   |            11.7 |    1124   |       6   |                6.6 |            1.2 |
| East Harlem (North)               | Manhattan     |       5 |           5 |        22   |          57.5 |       2903   |      400   |               41   |         1   |             5.4 |     572   |       6   |               11.2 |            1.3 |
| Mott Haven-Port Morris            | Bronx         |       9 |           9 |        22.6 |          60.5 |       2575   |      734   |               13   |         0   |             3.2 |     250   |      12   |               17.2 |            2.6 |
| Hempstead                         | Nassau County |       8 |           6 |        23   |          57   |       2400.5 |      820   |                8.5 |         1.5 |             7.2 |    2235.5 |     nan   |                5.6 |            2.3 |
| Harlem (North)                    | Manhattan     |       4 |           4 |        24.7 |          55   |       2493   |      nan   |               22.5 |         2   |             3.8 |     596   |       6   |                8.9 |            0.8 |
| Manhattanville-West Harlem        | Manhattan     |       3 |           3 |        25.1 |          55   |       2898   |      nan   |               29   |         4   |             1.9 |     265   |       6   |                4.6 |            1.3 |
| Washington Heights (South)        | Manhattan     |       3 |           3 |        26.3 |          56   |       2683   |      nan   |               13   |         2   |             4.2 |     442   |       6   |                6   |            1.9 |
| Washington Heights (North)        | Manhattan     |       3 |           3 |        27.1 |          64   |       2698   |      nan   |               47   |         3   |             3.6 |     593   |       6   |                5.3 |            1.8 |
| Inwood                            | Manhattan     |       5 |           5 |        28.9 |          70   |       2838   |      nan   |               23   |         7   |             2.1 |     475   |       6   |                5.3 |            1.8 |
| Newark                            | Essex County  |      54 |          17 |        46.9 |          68   |       2442   |      634   |               40   |         5   |             1.9 |     520   |       6   |                5.2 |            6.9 |

## Group 4: 4 neighborhoods, 371 places

Distinguishing traits (standard deviations from the average): bfloors +4.3, sqft_med -1.7, water_m -0.8, all_in_med +0.6

| hood         | area               |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------|:-------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| New Rochelle | Westchester County |      60 |          14 |        28.9 |           101 |         2804 |      515   |                  7 |           1 |            13.9 |       844 |        26 |                1.6 |            0.7 |
| Yonkers      | Westchester County |      55 |          17 |        37.9 |           104 |         2738 |      582   |                  2 |           1 |             5.2 |        75 |        25 |                3.9 |            1.5 |
| Jersey City  | Hudson County      |     223 |          33 |        38.5 |            85 |         2693 |      523.5 |                  6 |           0 |            10.1 |       947 |        14 |                4.9 |            2.9 |
| White Plains | Westchester County |      33 |          14 |        44.5 |           115 |         2831 |      543.5 |                  8 |           0 |             2.6 |       165 |        15 |                1.1 |            0.5 |

## Group 5: 11 neighborhoods, 591 places

Distinguishing traits (standard deviations from the average): bars_800m +1.1, restaurants_800m +0.9, drive_min +0.8, transit_min +0.8

| hood          | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:--------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Montclair     | Essex County                              |       7 |           3 |        52.2 |           112 |       2477   |      479   |                 72 |         3   |             9.2 |    4542   |       nan |                0.8 |            0.9 |
| Stamford      | Western Connecticut Planning Region       |     118 |          39 |        52.9 |           119 |       2760   |      637.5 |                 24 |         5   |             3.9 |     804   |         8 |                1.5 |            1.2 |
| Norwalk       | Western Connecticut Planning Region       |      53 |          11 |        63.1 |           149 |       2679   |      725   |                 15 |         0   |             2.8 |     327   |         7 |                0.5 |            1.2 |
| Dover         | Morris County                             |      41 |           1 |        74.8 |           172 |       2562   |      787   |                 27 |         7   |             2.2 |    2682   |       nan |                0.8 |            0.6 |
| New Brunswick | Middlesex County                          |      17 |           5 |        75.1 |           122 |       2850   |      750   |                 30 |         4   |             3.9 |     365   |         2 |                5.1 |            1.6 |
| Bound Brook   | Somerset County                           |       5 |           2 |        81.6 |           136 |       2605   |      789   |                 13 |         2   |             4.4 |     283   |       nan |                1.2 |            0.7 |
| Somerville    | Somerset County                           |       3 |           2 |        86.2 |           151 |       2891   |      928   |                 19 |         4   |             6.1 |     475   |       nan |                1.3 |            0.9 |
| Red Bank      | Monmouth County                           |       4 |           1 |        90.4 |           157 |       2867   |      740   |                 18 |         1   |             5.5 |     231   |       nan |                2.3 |            1   |
| Shelton       | Naugatuck Valley Planning Region          |      14 |           5 |        97.6 |           241 |       2582.5 |      801.5 |                  8 |         1.5 |             5.9 |      88.5 |       nan |                0.3 |            1.1 |
| Long Branch   | Monmouth County                           |      10 |           1 |       101.5 |           175 |       2566   |      645   |                 13 |         2   |             8.2 |     335   |       nan |                2.3 |            0.5 |
| New Haven     | South Central Connecticut Planning Region |     319 |          26 |       109.2 |           181 |       2392   |      653   |                 55 |        17   |             4.1 |    1130   |       nan |                4   |            6.1 |

## Group 6: 22 neighborhoods, 280 places

Distinguishing traits (standard deviations from the average): water_m -1.0, park_ha_800m +0.5, sqft_med -0.4, drive_min -0.3

| hood                            | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:--------------------------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Old Astoria-Hallets Point       | Queens                                    |       4 |           4 |        18.2 |          55   |       2793   |      nan   |               12.5 |         1   |             6   |     200.5 |       7.5 |                3.7 |            1.7 |
| Rockaway Beach-Arverne-Edgemere | Queens                                    |       3 |           3 |        25.4 |          65   |       2766   |      655   |                4   |         3   |             4   |     251   |       7   |                3.2 |            0.6 |
| Long Beach                      | Nassau County                             |       5 |           3 |        25.8 |          64   |       2771   |      715.5 |                8   |         1   |            26.5 |     596   |     nan   |                0.8 |            0   |
| Norwood                         | Bronx                                     |       3 |           3 |        27.6 |          82.6 |       2202   |      750   |                3   |         0   |             3   |     811   |       8   |               10.3 |            2.2 |
| Bath Beach                      | Brooklyn                                  |       4 |           4 |        28.8 |          80   |       2224   |      650   |                8   |         0   |             0.8 |     140.5 |       6   |                2   |            0.9 |
| Mount Vernon                    | Westchester County                        |       6 |           2 |        30   |         100   |       2571   |      545   |                8   |         1   |             8.7 |     248   |     nan   |                5.5 |            2.7 |
| Riverdale-Spuyten Duyvil        | Bronx                                     |       4 |           4 |        31.8 |          85   |       2288   |      898   |                8   |         0   |             2.3 |     736.5 |       6   |                3.4 |            2.6 |
| Glen Cove                       | Nassau County                             |       3 |           1 |        32.7 |         106   |       2900   |      570   |               20   |         1   |             4.5 |     421   |     nan   |                1.1 |            0.2 |
| West New York                   | Hudson County                             |       5 |           5 |        33.4 |          71   |       1947   |      550   |               18   |         0   |             8.6 |     838   |     nan   |                2.4 |            1.1 |
| North Bergen                    | Hudson County                             |       5 |           4 |        34.8 |          71   |       2692   |      730.5 |               11   |         0   |             3.5 |     336   |     nan   |                1.3 |            1.3 |
| Bogota                          | Bergen County                             |      15 |           2 |        35.6 |          92   |       2862   |      658   |                2   |         0   |             6.9 |     123   |     nan   |                0.7 |            0.1 |
| Hackensack                      | Bergen County                             |      34 |          12 |        37.1 |          97   |       2738   |      730   |                7   |         1   |             2.5 |     342.5 |     nan   |                2.4 |            1.3 |
| Port Chester                    | Westchester County                        |      41 |           4 |        41.5 |         106   |       2888   |      567   |               10   |         0   |            11.3 |     300   |     nan   |                0.8 |            0.4 |
| Belleville                      | Essex County                              |       9 |           2 |        44.1 |         100   |       2402   |      791   |                5   |         1   |             6.6 |     450   |     nan   |                2.4 |            2.9 |
| Harrison                        | Hudson County                             |      28 |          10 |        46.9 |          83   |       2652.5 |      547   |               14.5 |         1   |             2.4 |     119   |     nan   |                2.1 |            1.1 |
| Elizabeth                       | Union County                              |      12 |           1 |        50.4 |         116   |       2707.5 |      772   |                0   |         0   |            34.2 |      16   |     nan   |                3.4 |            4.8 |
| Wayne                           | Passaic County                            |       3 |           1 |        54.5 |         107   |       2517   |      546   |                8   |         1   |             3.6 |     180   |     nan   |                1   |            0.5 |
| Rahway                          | Union County                              |       7 |           3 |        57.4 |          98   |       2568   |      665   |                9   |         4   |             9.2 |      81   |     nan   |                1.9 |            0.8 |
| Haverstraw                      | Rockland County                           |      10 |           3 |        67   |         nan   |       2802.5 |      698   |                1   |         0   |            10.2 |      57   |     nan   |                2.1 |            0.5 |
| Bridgeport                      | Greater Bridgeport Planning Region        |      59 |           7 |        82.7 |         151   |       2427   |      650   |                3   |         0   |            12.5 |      75   |     nan   |                2.5 |            3.4 |
| Stratford                       | Greater Bridgeport Planning Region        |       4 |           1 |        87.6 |         164   |       2367   |      720   |                6   |         0   |             7.5 |     404   |     nan   |                0.5 |            1.7 |
| Milford city (balance)          | South Central Connecticut Planning Region |      16 |           6 |        92.9 |         160   |       2452   |      593   |               10   |         0.5 |             6.5 |     535   |     nan   |                0.7 |            2.1 |

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
| Valley Stream                                  | Nassau County                             | NY      |       2 |        13.5 |       2858.5 |
| Ocean Hill                                     | Brooklyn                                  | NY      |       2 |        13.6 |       2746.5 |
| Astoria (East)-Woodside (North)                | Queens                                    | NY      |       1 |        14.9 |       2694   |
| Lynbrook                                       | Nassau County                             | NY      |       1 |        15   |       2955   |
| Sunnyside                                      | Queens                                    | NY      |       2 |        17.4 |       2361   |
| Astoria (Central)                              | Queens                                    | NY      |       2 |        17.5 |       2478   |
| Long Island City-Hunters Point                 | Queens                                    | NY      |       1 |        18.9 |       1577   |
| Bedford-Stuyvesant (West)                      | Brooklyn                                  | NY      |       2 |        20.3 |       2661   |
| Crown Heights (North)                          | Brooklyn                                  | NY      |       1 |        20.8 |       2979   |
| Mineola                                        | Nassau County                             | NY      |       1 |        20.8 |       2871   |
| Morris Park                                    | Bronx                                     | NY      |       1 |        21.2 |       2302   |
| Pelham Bay-Country Club-City Island            | Bronx                                     | NY      |       1 |        21.4 |       2983   |
| East Midtown-Turtle Bay                        | Manhattan                                 | NY      |       1 |        22.2 |       2393   |
| Upper East Side-Lenox Hill-Roosevelt Island    | Manhattan                                 | NY      |       1 |        22.3 |       2988   |
| Concourse-Concourse Village                    | Bronx                                     | NY      |       1 |        22.6 |       2438   |
| Flatlands                                      | Brooklyn                                  | NY      |       2 |        22.6 |       2224.5 |
| Flatbush                                       | Brooklyn                                  | NY      |       2 |        23   |       2601.5 |
| Harlem (South)                                 | Manhattan                                 | NY      |       1 |        23.3 |       2908   |
| East Harlem (South)                            | Manhattan                                 | NY      |       1 |        23.8 |       2578   |
| Midwood                                        | Brooklyn                                  | NY      |       2 |        24.4 |       2718   |
| Tremont                                        | Bronx                                     | NY      |       1 |        24.4 |       2187   |
| Sheepshead Bay-Manhattan Beach-Gerritsen Beach | Brooklyn                                  | NY      |       2 |        24.6 |       1979   |
| Brighton Beach                                 | Brooklyn                                  | NY      |       2 |        24.9 |       2769.5 |
| Hamilton Heights-Sugar Hill                    | Manhattan                                 | NY      |       2 |        25   |       2594.5 |
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
| University Heights (South)-Morris Heights      | Bronx                                     | NY      |       1 |        27.8 |       1880   |
| Bensonhurst                                    | Brooklyn                                  | NY      |       2 |        28.4 |       2186.5 |
| Fort Lee                                       | Bergen County                             | NJ      |       1 |        28.5 |       2642   |
| Gravesend (West)                               | Brooklyn                                  | NY      |       1 |        29   |       2494   |
| Bedford Park                                   | Bronx                                     | NY      |       1 |        29.1 |       2698   |
| Kingsbridge Heights-Van Cortlandt Village      | Bronx                                     | NY      |       1 |        29.1 |       2238   |
| Kingsbridge-Marble Hill                        | Bronx                                     | NY      |       1 |        30.9 |       2478   |
| Weehawken                                      | Hudson County                             | NJ      |       2 |        31.2 |       2840.5 |
| Bay Ridge                                      | Brooklyn                                  | NY      |       2 |        31.8 |       2314   |
| Larchmont                                      | Westchester County                        | NY      |       1 |        31.9 |       2803   |
| Union City                                     | Hudson County                             | NJ      |       2 |        32.8 |       2049.5 |
| Edgewater                                      | Bergen County                             | NJ      |       2 |        33.4 |       2944.5 |
| Hoboken                                        | Hudson County                             | NJ      |       1 |        35.6 |       2602   |
| Dumont                                         | Bergen County                             | NJ      |       1 |        39.7 |       2147   |
| Tompkinsville-Stapleton-Clifton-Fox Hills      | Staten Island                             | NY      |       1 |        42.1 |       2361   |
| Harrison                                       | Westchester County                        | NY      |       1 |        42.7 |       2938   |
| St. George-New Brighton                        | Staten Island                             | NY      |       1 |        45.8 |       2944   |
| Kearny                                         | Hudson County                             | NJ      |       1 |        46.1 |       2002   |
| Paterson                                       | Passaic County                            | NJ      |       1 |        46.3 |       1788   |
| Hawthorne                                      | Passaic County                            | NJ      |       1 |        46.4 |       2575   |
| New Springville-Willowbrook-Bulls Head-Travis  | Staten Island                             | NY      |       1 |        47.8 |       2579   |
| Ridgewood                                      | Bergen County                             | NJ      |       1 |        49.3 |       2527   |
| Tarrytown                                      | Westchester County                        | NY      |       1 |        49.3 |       2003   |
| Haledon                                        | Passaic County                            | NJ      |       1 |        49.9 |       2224   |
| Irvington                                      | Essex County                              | NJ      |       2 |        53.7 |       1342   |
| Union                                          | Union County                              | NJ      |       1 |        55.5 |       2894   |
| Nyack                                          | Rockland County                           | NY      |       1 |        55.9 |       2865   |
| Montvale                                       | Bergen County                             | NJ      |       1 |        56.6 |       2847   |
| Springfield                                    | Union County                              | NJ      |       2 |        59   |       2767   |
| Summit                                         | Union County                              | NJ      |       2 |        62.2 |       2547.5 |
| Mount Kisco                                    | Westchester County                        | NY      |       1 |        63.3 |       2698   |
| Garwood                                        | Union County                              | NJ      |       1 |        63.9 |       2949   |
| Scotch Plains                                  | Union County                              | NJ      |       1 |        65.5 |       2409   |
| Madison                                        | Morris County                             | NJ      |       1 |        68.3 |       2316   |
| Watchung                                       | Somerset County                           | NJ      |       2 |        70.8 |       2869   |
| Plainfield                                     | Union County                              | NJ      |       1 |        71.5 |       2432   |
| Morris Plains                                  | Morris County                             | NJ      |       1 |        71.5 |       2637   |
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
| Bordentown                                     | Burlington County                         | NJ      |       1 |       107.2 |       2452   |
| Oxford                                         | Naugatuck Valley Planning Region          | CT      |       1 |       109.9 |       2804   |
| LaGrange                                       | Dutchess County                           | NY      |       1 |       117.2 |       2597   |
| North Haven                                    | South Central Connecticut Planning Region | CT      |       1 |       118.2 |       1482   |
| Waterbury                                      | Naugatuck Valley Planning Region          | CT      |       1 |       118.7 |       1666   |
| New Paltz                                      | Ulster County                             | NY      |       2 |       119.3 |       2669.5 |
