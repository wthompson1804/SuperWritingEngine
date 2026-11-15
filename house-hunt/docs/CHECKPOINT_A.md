# Checkpoint A: neighborhoods and proposed years

Passing units: 610 in 271 buildings, across 103 neighborhoods; 40 neighborhoods have 3+ passing places.

Cluster quality (silhouette; higher is cleaner): {5: 0.206, 6: 0.213}. Using k=6.

## Group 1: 12 neighborhoods, 103 places

Distinguishing traits (standard deviations from the average): bars_800m +1.2, transit_min -1.1, drive_min -1.0, restaurants_800m +0.9

| hood                              | area         |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:----------------------------------|:-------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Jamaica                           | Queens       |      12 |          10 |         2.2 |          11.4 |       2636.5 |      600   |               27   |           3 |             5.2 |    2759   |      11   |                9.8 |            1.7 |
| Jamaica Hills-Briarwood           | Queens       |      10 |          10 |         4.1 |          18.7 |       2334   |      640   |                9.5 |           2 |             4.3 |    1801   |       6   |                2.4 |            2.2 |
| Kew Gardens                       | Queens       |       6 |           6 |         4.2 |          13.6 |       2755.5 |      750   |               24.5 |           3 |             4.4 |    1118.5 |       6   |                3.1 |            2.1 |
| Forest Hills                      | Queens       |       4 |           4 |         9.7 |          30.5 |       2418.5 |      708   |               45   |           1 |             7.6 |    1166   |       6.5 |                2.1 |            1.4 |
| Flushing-Willets Point            | Queens       |      19 |          19 |        11.8 |          44.6 |       2394   |      614.5 |               82   |           3 |             3.7 |     894   |       6   |                2.6 |            2.2 |
| East New York (North)             | Brooklyn     |       3 |           2 |        11.9 |          32.5 |       2750   |      nan   |                5   |           1 |             5.7 |    2543   |      14   |                8.4 |            2.4 |
| Jackson Heights                   | Queens       |       9 |           9 |        12.8 |          32   |       2178   |      639   |               61   |           3 |             4.8 |    1796   |       6   |                4.8 |            1.4 |
| Elmhurst                          | Queens       |       3 |           3 |        13.5 |          32   |       2494   |      850   |               69   |           4 |             3.4 |    2721   |       6   |                6.1 |            1.4 |
| Bedford-Stuyvesant (East)         | Brooklyn     |       3 |           3 |        18.7 |          38.5 |       2944   |      nan   |               21   |           6 |             3.3 |    3290   |       8   |                5.6 |            1.2 |
| Prospect Lefferts Gardens-Wingate | Brooklyn     |       3 |           3 |        21.1 |          50   |       2944   |      nan   |               17   |           6 |             6.6 |    1447   |       7   |                5.9 |            1   |
| East Flatbush-Erasmus             | Brooklyn     |       7 |           7 |        21.8 |          55   |       2794   |      600   |               19   |           6 |            11.7 |    1124   |       6   |                6.6 |            1.2 |
| Newark                            | Essex County |      24 |           5 |        46.9 |          68   |       2466   |      630   |               41   |           5 |             1.9 |     491   |     nan   |                5.2 |            6.9 |

## Group 2: 6 neighborhoods, 52 places

Distinguishing traits (standard deviations from the average): park_ha_800m +1.1, drive_min +1.0, transit_min +0.8, water_m +0.8

| hood          | area             |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:--------------|:-----------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Clifton       | Passaic County   |      13 |           2 |        46   |           107 |       2774   |        788 |                  2 |           1 |             3.7 |      2437 |       nan |                1.7 |            2.1 |
| Bloomfield    | Essex County     |      13 |           4 |        51.4 |            98 |       2506   |        760 |                 17 |           1 |             3   |      3842 |       nan |                0.8 |            1.3 |
| Maplewood     | Essex County     |       6 |           1 |        54.4 |           113 |       2712   |        779 |                 10 |           1 |            10.1 |      4451 |       nan |                0.5 |            1.4 |
| South Orange  | Essex County     |       7 |           1 |        57.3 |           107 |       2891   |        669 |                 16 |           0 |             3.1 |      2676 |       nan |                1   |            1.2 |
| Millburn      | Essex County     |       3 |           1 |        58.3 |           115 |       2347   |        635 |                  7 |           1 |             6.9 |      4113 |       nan |                0.1 |            0.3 |
| New Brunswick | Middlesex County |      10 |           1 |        75.1 |           122 |       2886.5 |        750 |                 30 |           4 |             3.9 |       365 |         2 |                5.1 |            1.6 |

## Group 3: 12 neighborhoods, 102 places

Distinguishing traits (standard deviations from the average): bars_800m -1.0, park_ha_800m -1.0, restaurants_800m -0.8, drive_min +0.6

| hood                   | area                                |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-----------------------|:------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Bay Terrace-Clearview  | Queens                              |       3 |           3 |        17.3 |          65   |       2753   |        800 |                  9 |           0 |            14.4 |       193 |         6 |                2.6 |            2.2 |
| East Flatbush-Farragut | Brooklyn                            |       5 |           5 |        22.7 |          60   |       2891   |        nan |                  5 |           0 |             7   |      2898 |         6 |                6.6 |            1.2 |
| Cliffside Park         | Bergen County                       |       3 |           1 |        32.9 |          91   |       2902   |        600 |                  7 |           0 |            17.4 |      1201 |       nan |                0.8 |            0.5 |
| Englewood              | Bergen County                       |      12 |           3 |        33.8 |          85   |       2887   |        766 |                  0 |           0 |            11.3 |       770 |       nan |                2.3 |            1.3 |
| North Bergen           | Hudson County                       |       3 |           2 |        34.8 |          71   |       2942   |        764 |                 11 |           0 |             5.1 |      1311 |       nan |                1.3 |            1.3 |
| Teaneck                | Bergen County                       |       7 |           1 |        37.9 |          93.5 |       2832   |        702 |                  1 |           0 |            13.8 |      1951 |       nan |                1.3 |            0.2 |
| Bayonne                | Hudson County                       |      44 |           7 |        45.1 |         100   |       2668.5 |        763 |                  6 |           0 |            20.5 |       853 |       nan |                2.8 |            1.1 |
| Cranford               | Union County                        |       3 |           1 |        61.2 |         158   |       2994   |        728 |                  6 |           0 |            15.3 |       394 |       nan |                0.4 |            0.2 |
| Woodbridge             | Middlesex County                    |       4 |           1 |        64.6 |         143   |       2739   |        701 |                  2 |           0 |             8.1 |      2018 |       nan |                1.4 |            0.8 |
| Parsippany-Troy Hills  | Morris County                       |      10 |           1 |        65.1 |         172   |       2897   |        748 |                  0 |           0 |            11.6 |       862 |         6 |                0.7 |            0.4 |
| Westport               | Western Connecticut Planning Region |       5 |           2 |        72.3 |         nan   |       2862   |        712 |                  0 |           0 |            13.2 |      2155 |       nan |                0.3 |            2.6 |
| West Windsor           | Mercer County                       |       3 |           3 |       101.7 |         nan   |       2349   |        825 |                  3 |           0 |            14.8 |      2812 |       nan |                0.5 |            0.3 |

## Group 4: 6 neighborhoods, 103 places

Distinguishing traits (standard deviations from the average): water_m -1.8, sqft_med -0.7, park_ha_800m +0.6, restaurants_800m -0.4

| hood                      | area               |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:--------------------------|:-------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Old Astoria-Hallets Point | Queens             |       4 |           4 |        18.2 |            55 |       2793   |      nan   |               12.5 |           1 |             6   |     200.5 |       7.5 |                3.7 |            1.7 |
| Bogota                    | Bergen County      |      15 |           2 |        35.6 |            92 |       2862   |      658   |                2   |           0 |             6.9 |     123   |     nan   |                0.7 |            0.1 |
| Hackensack                | Bergen County      |      27 |           9 |        37.1 |            97 |       2693   |      729   |                7   |           1 |             2.5 |     246   |     nan   |                2.4 |            1.3 |
| Yonkers                   | Westchester County |      11 |           6 |        38.1 |           109 |       2723   |      490   |                2   |           1 |             7   |      59   |     nan   |                3.9 |            1.5 |
| White Plains              | Westchester County |      18 |           6 |        44.5 |           115 |       2817   |      532.5 |                2   |           0 |             2.4 |     117   |       2   |                1.1 |            0.5 |
| Harrison                  | Hudson County      |      28 |          10 |        46.9 |            83 |       2652.5 |      547   |               14.5 |           1 |             2.4 |     119   |     nan   |                2.1 |            1.1 |

## Group 5: 3 neighborhoods, 135 places

Distinguishing traits (standard deviations from the average): violent_per_1000 +2.2, sqft_med -1.3, park_ha_800m +1.2, bfloors +0.7

| hood                   | area          |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-----------------------|:--------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| East Harlem (North)    | Manhattan     |       4 |           4 |        21.6 |          57.8 |       2870.5 |        400 |               39.5 |           1 |             4.8 |     517.5 |       7.5 |               11.2 |            1.3 |
| Mott Haven-Port Morris | Bronx         |       5 |           5 |        21.6 |          66.5 |       2598   |        734 |               13   |           0 |             2.6 |     250   |       7   |               17.2 |            2.6 |
| Jersey City            | Hudson County |     126 |          14 |        38.5 |          85   |       2714.5 |        514 |                3   |           0 |             0.6 |     947   |      14   |                4.9 |            2.9 |

## Group 6: 1 neighborhoods, 31 places

Distinguishing traits (standard deviations from the average): bfloors +5.1, sqft_med -1.8, park_ha_800m -1.2, transit_min +0.6

| hood         | area               |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------|:-------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| New Rochelle | Westchester County |      31 |           8 |        29.1 |           101 |         2767 |        499 |                  7 |           1 |              13 |       749 |        26 |                1.6 |            0.7 |

## Neighborhoods with fewer than 3 passing places (not shown on the page)

| hood                                           | area                                | state   |   units |   drive_min |   all_in_med |
|:-----------------------------------------------|:------------------------------------|:--------|--------:|------------:|-------------:|
| Jamaica Estates-Holliswood                     | Queens                              | NY      |       1 |         6.4 |       2394   |
| Kew Gardens Hills                              | Queens                              | NY      |       1 |         7.3 |       2378   |
| Pomonok-Electchester-Hillcrest                 | Queens                              | NY      |       1 |         7.9 |       2994   |
| North Corona                                   | Queens                              | NY      |       2 |        10.1 |       2641.5 |
| Rego Park                                      | Queens                              | NY      |       1 |        10.6 |       2529   |
| Middle Village                                 | Queens                              | NY      |       1 |        11.8 |       1979   |
| Murray Hill-Broadway Flushing                  | Queens                              | NY      |       1 |        11.9 |       2118   |
| Valley Stream                                  | Nassau County                       | NY      |       1 |        13.5 |       2871   |
| Ocean Hill                                     | Brooklyn                            | NY      |       2 |        13.6 |       2746.5 |
| Astoria (East)-Woodside (North)                | Queens                              | NY      |       1 |        14.9 |       2694   |
| Sunnyside                                      | Queens                              | NY      |       2 |        17.4 |       2361   |
| Astoria (Central)                              | Queens                              | NY      |       2 |        17.5 |       2478   |
| Long Island City-Hunters Point                 | Queens                              | NY      |       1 |        18.9 |       1577   |
| Bedford-Stuyvesant (West)                      | Brooklyn                            | NY      |       2 |        20.3 |       2661   |
| Crown Heights (North)                          | Brooklyn                            | NY      |       1 |        20.8 |       2979   |
| Morris Park                                    | Bronx                               | NY      |       1 |        21.2 |       2302   |
| Pelham Bay-Country Club-City Island            | Bronx                               | NY      |       1 |        21.4 |       2983   |
| East Midtown-Turtle Bay                        | Manhattan                           | NY      |       1 |        22.2 |       2393   |
| Upper East Side-Lenox Hill-Roosevelt Island    | Manhattan                           | NY      |       1 |        22.3 |       2988   |
| Flatlands                                      | Brooklyn                            | NY      |       2 |        22.6 |       2224.5 |
| Flatbush                                       | Brooklyn                            | NY      |       2 |        23   |       2601.5 |
| Hempstead                                      | Nassau County                       | NY      |       2 |        23   |       2821   |
| Harlem (South)                                 | Manhattan                           | NY      |       1 |        23.3 |       2908   |
| Harlem (North)                                 | Manhattan                           | NY      |       1 |        23.6 |       2798   |
| Madison                                        | Brooklyn                            | NY      |       2 |        24.2 |       2524   |
| Tremont                                        | Bronx                               | NY      |       1 |        24.4 |       2187   |
| Sheepshead Bay-Manhattan Beach-Gerritsen Beach | Brooklyn                            | NY      |       2 |        24.6 |       1979   |
| Manhattanville-West Harlem                     | Manhattan                           | NY      |       2 |        24.6 |       2895.5 |
| Brighton Beach                                 | Brooklyn                            | NY      |       2 |        24.9 |       2769.5 |
| Pelham Parkway-Van Nest                        | Bronx                               | NY      |       2 |        25   |       2403   |
| Flatbush (West)-Ditmas Park-Parkville          | Brooklyn                            | NY      |       1 |        25.1 |       2794   |
| Mount Hope                                     | Bronx                               | NY      |       1 |        25.1 |       1853   |
| Long Beach                                     | Nassau County                       | NY      |       1 |        25.8 |       2971   |
| Washington Heights (South)                     | Manhattan                           | NY      |       1 |        26.3 |       2493   |
| Upper West Side-Lincoln Square                 | Manhattan                           | NY      |       1 |        26.7 |       2938   |
| Washington Heights (North)                     | Manhattan                           | NY      |       1 |        27.1 |       2702   |
| Coney Island-Sea Gate                          | Brooklyn                            | NY      |       1 |        27.3 |       1970   |
| Norwood                                        | Bronx                               | NY      |       1 |        27.6 |       2202   |
| Fort Lee                                       | Bergen County                       | NJ      |       1 |        29.2 |       2982   |
| Weehawken                                      | Hudson County                       | NJ      |       2 |        31.2 |       2840.5 |
| Riverdale-Spuyten Duyvil                       | Bronx                               | NY      |       1 |        32.2 |       1383   |
| West New York                                  | Hudson County                       | NJ      |       1 |        33.2 |       2990   |
| Edgewater                                      | Bergen County                       | NJ      |       2 |        33.7 |       2942   |
| Secaucus                                       | Hudson County                       | NJ      |       1 |        34.3 |       2556   |
| Union City                                     | Hudson County                       | NJ      |       1 |        34.6 |       2252   |
| East Rutherford                                | Bergen County                       | NJ      |       2 |        42   |       2681   |
| Tompkinsville-Stapleton-Clifton-Fox Hills      | Staten Island                       | NY      |       1 |        42.1 |       2361   |
| Harrison                                       | Westchester County                  | NY      |       2 |        42.7 |       2935.5 |
| Hawthorne                                      | Passaic County                      | NJ      |       1 |        46.4 |       2575   |
| Belleville                                     | Essex County                        | NJ      |       2 |        46.8 |       2397   |
| Ridgewood                                      | Bergen County                       | NJ      |       1 |        49.3 |       2527   |
| Stamford                                       | Western Connecticut Planning Region | CT      |       1 |        53.2 |       2936   |
| East Orange                                    | Essex County                        | NJ      |       1 |        53.2 |       1901   |
| City of Orange                                 | Essex County                        | NJ      |       1 |        53.4 |       2583   |
| Montclair                                      | Essex County                        | NJ      |       1 |        53.9 |       2690   |
| Union                                          | Union County                        | NJ      |       2 |        55.5 |       2924   |
| Scotch Plains                                  | Union County                        | NJ      |       1 |        65.5 |       2409   |
| Boonton                                        | Morris County                       | NJ      |       2 |        68.2 |       2166.5 |
| Rockaway                                       | Morris County                       | NJ      |       1 |        77.1 |       2737   |
| Old Bridge                                     | Middlesex County                    | NJ      |       2 |        81   |       2472.5 |
| Bound Brook                                    | Somerset County                     | NJ      |       1 |        82.3 |       2352   |
| Flemington                                     | Hunterdon County                    | NJ      |       1 |       103.9 |       2187   |
| Bordentown                                     | Burlington County                   | NJ      |       1 |       107.2 |       2452   |
