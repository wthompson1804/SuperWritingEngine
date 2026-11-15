# Checkpoint A: neighborhoods and proposed years

Passing units: 1524 in 577 buildings, across 191 neighborhoods; 92 neighborhoods have 3+ passing places.

Cluster quality (silhouette; higher is cleaner): {5: 0.165, 6: 0.138}. Using k=5.

## Group 1: 33 neighborhoods, 275 places

Distinguishing traits (standard deviations from the average): restaurants_800m -0.7, water_m +0.6, bars_800m -0.6, sqft_med +0.6

| hood                  | area                                |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:----------------------|:------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Bay Terrace-Clearview | Queens                              |       3 |           3 |        17.3 |          65   |       2753   |      800   |                  9 |           0 |            14.4 |     193   |         6 |                2.6 |            2.2 |
| Madison               | Brooklyn                            |       5 |           5 |        23.9 |          70   |       2544   |      800   |                  8 |           0 |             7.4 |    1559   |         6 |                2.7 |            1.4 |
| Cliffside Park        | Bergen County                       |       3 |           1 |        32.9 |          91   |       2902   |      600   |                  7 |           0 |            17.4 |    1201   |       nan |                0.8 |            0.5 |
| Englewood             | Bergen County                       |      12 |           3 |        33.8 |          85   |       2887   |      766   |                  0 |           0 |            11.3 |     770   |       nan |                2.3 |            1.3 |
| North Bergen          | Hudson County                       |       9 |           5 |        34.5 |          71   |       2930   |      763.5 |                  3 |           0 |             5.1 |     679   |       nan |                1.3 |            1.3 |
| Teaneck               | Bergen County                       |       7 |           1 |        37.9 |          93.5 |       2892   |      702   |                  1 |           0 |            13.8 |    1951   |       nan |                1.3 |            0.2 |
| East Rutherford       | Bergen County                       |       3 |           2 |        42   |          82   |       2658   |      724   |                  3 |           0 |            14.2 |    1516   |       nan |                0.2 |            0.5 |
| Bayonne               | Hudson County                       |      53 |          14 |        45.1 |         100   |       2613   |      763   |                  6 |           0 |            17   |     853   |       nan |                2.8 |            1.1 |
| Clifton               | Passaic County                      |      13 |           2 |        46   |         107   |       2774   |      788   |                  2 |           1 |             3.7 |    2437   |       nan |                1.7 |            2.1 |
| Bloomfield            | Essex County                        |      13 |           4 |        51.4 |          98   |       2506   |      760   |                 17 |           1 |             3   |    3842   |       nan |                0.8 |            1.3 |
| East Orange           | Essex County                        |      16 |          10 |        51.9 |          98   |       2397   |      764   |                  0 |           0 |             4.7 |    3610.5 |       nan |                4.2 |            4.7 |
| City of Orange        | Essex County                        |      13 |           5 |        53.2 |          83   |       2502   |      770   |                  0 |           1 |            15.7 |    4149   |       nan |                4.2 |            5.6 |
| Maplewood             | Essex County                        |       6 |           1 |        54.4 |         113   |       2712   |      779   |                 10 |           1 |            10.1 |    4451   |       nan |                0.5 |            1.4 |
| Islip                 | Suffolk County                      |       5 |           2 |        55.5 |         112   |       2816   |      665   |                  3 |           0 |            22.1 |    3305   |       nan |                1   |            1.1 |
| South Orange          | Essex County                        |       9 |           2 |        57.3 |         107   |       2801   |      676   |                 16 |           0 |             3.1 |    2676   |       nan |                1   |            1.2 |
| Millburn              | Essex County                        |       3 |           1 |        58.3 |         115   |       2347   |      635   |                  7 |           1 |             6.9 |    4113   |       nan |                0.1 |            0.3 |
| Carteret              | Middlesex County                    |       5 |           1 |        58.5 |         108.5 |       2323   |      807   |                  0 |           0 |             9.6 |     692   |       nan |                2   |            1.2 |
| Livingston            | Essex County                        |      10 |           2 |        62.5 |         143   |       2497   |      670   |                  0 |           0 |             6.8 |    2419   |       nan |                0.5 |            0.4 |
| Chatham               | Morris County                       |       3 |           3 |        63.4 |         128   |       2684   |      850   |                  6 |           0 |             9.7 |    2367   |       nan |                0   |            0.2 |
| Woodbridge            | Middlesex County                    |      11 |           4 |        63.7 |         128   |       2847   |      763   |                  2 |           0 |             8.1 |    2018   |       nan |                1.4 |            0.8 |
| Berkeley Heights      | Union County                        |       3 |           1 |        65.9 |         nan   |       2814   |      580   |                  0 |           0 |            19.9 |    4020   |       nan |                0.3 |            0.1 |
| West Haverstraw       | Rockland County                     |       4 |           1 |        67.2 |         nan   |       2622.5 |      750   |                  1 |           0 |             7.6 |    1894   |       nan |                2.1 |            0.5 |
| Westport              | Western Connecticut Planning Region |       5 |           2 |        72.3 |         nan   |       2862   |      712   |                  0 |           0 |            13.2 |    2155   |       nan |                0.3 |            2.6 |
| Brookhaven            | Suffolk County                      |       8 |           2 |        76.7 |         172   |       2871   |      830   |                  0 |           0 |             6.9 |    3433   |       nan |                1   |            1.1 |
| Peekskill             | Westchester County                  |       9 |           3 |        77.1 |         148   |       2654   |      800   |                  2 |           0 |             4.4 |    1259   |       nan |                2.3 |            0.6 |
| Aberdeen              | Monmouth County                     |       4 |           2 |        77.1 |         142   |       2439.5 |      747   |                  1 |           0 |            10.6 |     324   |       nan |                1.6 |            0.4 |
| Mount Arlington       | Morris County                       |       7 |           2 |        80.4 |         nan   |       2867   |      960   |                  2 |           0 |            28.5 |    1855   |       nan |                0   |            0   |
| Trumbull              | Greater Bridgeport Planning Region  |      11 |           2 |        87.8 |         nan   |       2647   |      849   |                  0 |           0 |             8.7 |    1269   |       nan |                0.8 |            0.8 |
| Stratford             | Greater Bridgeport Planning Region  |       5 |           1 |        93.2 |         nan   |       2700   |     1085   |                  0 |           0 |             7.4 |    1056   |       nan |                0.5 |            1.7 |
| West Windsor          | Mercer County                       |       3 |           3 |       101.7 |         nan   |       2349   |      825   |                  3 |           0 |            14.8 |    2812   |       nan |                0.5 |            0.3 |
| Wallkill              | Orange County                       |       3 |           3 |       102.9 |         nan   |       2615   |      898   |                  1 |           0 |             3.1 |    2231   |       nan |                0.5 |            0.1 |
| Middletown            | Orange County                       |       8 |           2 |       103.9 |         nan   |       2550.5 |      788.5 |                 10 |           2 |             6.9 |    2063   |       nan |                3.6 |            0.6 |
| Flemington            | Hunterdon County                    |       3 |           2 |       104.8 |         nan   |       2359   |      735   |                  8 |           0 |             9.6 |    2448   |       nan |                3   |            0.4 |

## Group 2: 9 neighborhoods, 278 places

Distinguishing traits (standard deviations from the average): transit_min +2.1, drive_min +1.3, park_ha_800m -0.7, all_in_med -0.7

| hood                   | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-----------------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Montclair              | Essex County                              |       8 |           4 |        52.2 |           112 |       2462   |      509.5 |                 72 |           3 |             9.2 |      4542 |       nan |                0.8 |            0.9 |
| Parsippany-Troy Hills  | Morris County                             |      93 |           3 |        69.2 |           187 |       2835   |      730   |                  3 |           0 |            13.1 |      1061 |         6 |                0.7 |            0.4 |
| Boonton                | Morris County                             |       7 |           3 |        73.4 |           182 |       2144   |      547   |                  0 |           0 |             8.2 |       906 |       nan |                0   |            0   |
| Dover                  | Morris County                             |      41 |           1 |        74.8 |           172 |       2562   |      787   |                 27 |           7 |             2.2 |      2682 |       nan |                0.8 |            0.6 |
| Piscataway             | Middlesex County                          |       7 |           2 |        75.7 |           286 |       2928   |      837   |                  4 |           0 |            18   |      1647 |       nan |                1.1 |            0.8 |
| Danbury                | Western Connecticut Planning Region       |       9 |           2 |        83.3 |           265 |       2504   |      675   |                  0 |           0 |            16.6 |      1051 |       nan |                1.4 |            0.6 |
| Plainsboro             | Middlesex County                          |      14 |           1 |        91.9 |           211 |       2066.5 |      647   |                  0 |           0 |             9.2 |      1472 |       nan |                0.4 |            0.4 |
| Milford city (balance) | South Central Connecticut Planning Region |       9 |           3 |        96   |           220 |       2425   |      755   |                  9 |           0 |            30.7 |      1085 |       nan |                0.7 |            2.1 |
| New Haven              | South Central Connecticut Planning Region |      90 |           7 |       107.3 |           181 |       2498.5 |      582   |                 74 |          19 |             6.3 |      1113 |       nan |                4   |            6.1 |

## Group 3: 30 neighborhoods, 337 places

Distinguishing traits (standard deviations from the average): water_m -1.0, park_ha_800m +0.7, restaurants_800m +0.3, drive_min -0.3

| hood                            | area                                |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:--------------------------------|:------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Kew Gardens                     | Queens                              |       6 |           6 |         4.2 |          13.6 |       2755.5 |      750   |               24.5 |           3 |             4.4 |    1118.5 |       6   |                3.1 |            2.1 |
| Old Astoria-Hallets Point       | Queens                              |       4 |           4 |        18.2 |          55   |       2793   |      nan   |               12.5 |           1 |             6   |     200.5 |       7.5 |                3.7 |            1.7 |
| Harlem (North)                  | Manhattan                           |       4 |           4 |        24.7 |          55   |       2493   |      nan   |               22.5 |           2 |             3.8 |     596   |       6   |                8.9 |            0.8 |
| Manhattanville-West Harlem      | Manhattan                           |       3 |           3 |        25.1 |          55   |       2898   |      nan   |               29   |           4 |             1.9 |     265   |       6   |                4.6 |            1.3 |
| Rockaway Beach-Arverne-Edgemere | Queens                              |       3 |           3 |        25.4 |          65   |       2766   |      655   |                4   |           3 |             4   |     251   |       7   |                3.2 |            0.6 |
| Long Beach                      | Nassau County                       |       4 |           2 |        25.8 |          64   |       2871   |      715.5 |                8   |           1 |            26.5 |     596   |     nan   |                0.8 |            0   |
| Washington Heights (South)      | Manhattan                           |       3 |           3 |        26.3 |          56   |       2683   |      nan   |               13   |           2 |             4.2 |     442   |       6   |                6   |            1.9 |
| Washington Heights (North)      | Manhattan                           |       3 |           3 |        27.1 |          64   |       2698   |      nan   |               47   |           3 |             3.6 |     593   |       6   |                5.3 |            1.8 |
| Bath Beach                      | Brooklyn                            |       4 |           4 |        28.8 |          80   |       2224   |      650   |                8   |           0 |             0.8 |     140.5 |       6   |                2   |            0.9 |
| Inwood                          | Manhattan                           |       5 |           5 |        28.9 |          70   |       2838   |      nan   |               23   |           7 |             2.1 |     475   |       6   |                5.3 |            1.8 |
| Mount Vernon                    | Westchester County                  |       6 |           2 |        30   |         100   |       2571   |      545   |                8   |           1 |             8.7 |     248   |     nan   |                5.5 |            2.7 |
| Riverdale-Spuyten Duyvil        | Bronx                               |       4 |           4 |        31.8 |          85   |       2288   |      898   |                8   |           0 |             2.3 |     736.5 |       6   |                3.4 |            2.6 |
| Glen Cove                       | Nassau County                       |       3 |           1 |        32.7 |         106   |       2900   |      570   |               20   |           1 |             4.5 |     421   |     nan   |                1.1 |            0.2 |
| West New York                   | Hudson County                       |       5 |           5 |        33.4 |          71   |       1947   |      550   |               18   |           0 |             8.6 |     838   |     nan   |                2.4 |            1.1 |
| Edgewater                       | Bergen County                       |       3 |           3 |        34.1 |          76   |       2947   |      780   |               14   |           1 |            14.5 |     258   |     nan   |                0.5 |            0.7 |
| Bogota                          | Bergen County                       |      29 |           2 |        35.6 |          92   |       2862   |      658   |                2   |           0 |             6.9 |     123   |     nan   |                0.7 |            0.1 |
| Hackensack                      | Bergen County                       |      32 |          13 |        37.1 |          97   |       2727   |      730   |                7   |           1 |             3.4 |     441.5 |     nan   |                2.4 |            1.3 |
| Port Chester                    | Westchester County                  |       4 |           4 |        41.6 |         106   |       2593   |      440.5 |               10   |           0 |            11.9 |     288.5 |     nan   |                0.8 |            0.4 |
| Belleville                      | Essex County                        |      10 |           3 |        44.1 |         100   |       2352   |      713.5 |                5   |           1 |             6.6 |     450   |     nan   |                2.4 |            2.9 |
| White Plains                    | Westchester County                  |      29 |          14 |        44.5 |         115   |       2853   |      553.5 |                7   |           0 |             2.6 |     165   |       2   |                1.1 |            0.5 |
| Harrison                        | Hudson County                       |      28 |          10 |        46.9 |          83   |       2652.5 |      547   |               14.5 |           1 |             2.4 |     119   |     nan   |                2.1 |            1.1 |
| Newark                          | Essex County                        |      57 |          18 |        46.9 |          68   |       2472   |      642   |               40   |           5 |             1.9 |     520   |       6   |                5.2 |            6.9 |
| North Haledon                   | Passaic County                      |       3 |           1 |        51.3 |         152   |       2915   |      769   |                1   |           0 |             3.7 |     776   |     nan   |                0.3 |            0   |
| Wayne                           | Passaic County                      |       3 |           1 |        54.5 |         107   |       2517   |      546   |                8   |           1 |             3.6 |     180   |     nan   |                1   |            0.5 |
| Rahway                          | Union County                        |       8 |           4 |        57.4 |          98   |       2576   |      667   |                9   |           4 |             9.2 |      81   |     nan   |                1.9 |            0.8 |
| Riverdale                       | Morris County                       |       4 |           1 |        61.1 |         130   |       2750.5 |      744   |                1   |           0 |             6.5 |     361   |     nan   |                0.5 |            1   |
| Cranford                        | Union County                        |       3 |           1 |        61.2 |         158   |       2994   |      728   |                6   |           0 |            15.3 |     394   |     nan   |                0.4 |            0.2 |
| Norwalk                         | Western Connecticut Planning Region |      32 |           5 |        63.1 |         149   |       2835   |      803   |               15   |           0 |             2.8 |     327   |     nan   |                0.5 |            1.2 |
| Haverstraw                      | Rockland County                     |       7 |           3 |        67.3 |         nan   |       2790   |      695   |                2   |           0 |            10.3 |      51   |     nan   |                2.1 |            0.5 |
| New Brunswick                   | Middlesex County                    |      28 |           7 |        75   |         122   |       2726   |      691   |               30   |           4 |             4.2 |     201   |       2   |                5.1 |            1.6 |

## Group 4: 3 neighborhoods, 164 places

Distinguishing traits (standard deviations from the average): bfloors +4.9, sqft_med -1.1, water_m -0.8, bars_800m +0.7

| hood         | area                                |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------|:------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| New Rochelle | Westchester County                  |      53 |          13 |        28.9 |           101 |         2807 |      521   |                  7 |           1 |            13.9 |       844 |        26 |                1.6 |            0.7 |
| Yonkers      | Westchester County                  |      45 |          20 |        37.9 |           104 |         2738 |      580   |                  2 |           1 |             5.2 |        73 |        25 |                3.9 |            1.5 |
| Stamford     | Western Connecticut Planning Region |      66 |          20 |        52.9 |           119 |         2795 |      656.5 |                 23 |           5 |             4.8 |       804 |        22 |                1.5 |            1.2 |

## Group 5: 17 neighborhoods, 336 places

Distinguishing traits (standard deviations from the average): violent_per_1000 +1.3, drive_min -1.1, transit_min -1.0, restaurants_800m +0.8

| hood                                  | area          |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:--------------------------------------|:--------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Jamaica                               | Queens        |      13 |          10 |         2.2 |          11.4 |       2644   |      600   |               27   |           4 |             4.8 |    2831   |      11   |                9.8 |            1.7 |
| Jamaica Hills-Briarwood               | Queens        |      10 |          10 |         4.1 |          18.7 |       2334   |      640   |                9.5 |           2 |             4.3 |    1801   |       6   |                2.4 |            2.2 |
| Forest Hills                          | Queens        |       4 |           4 |         9.7 |          30.5 |       2418.5 |      708   |               45   |           1 |             7.6 |    1166   |       6.5 |                2.1 |            1.4 |
| Flushing-Willets Point                | Queens        |      19 |          19 |        11.8 |          44.6 |       2394   |      614.5 |               82   |           3 |             3.7 |     894   |       6   |                2.6 |            2.2 |
| East New York (North)                 | Brooklyn      |       3 |           2 |        11.9 |          32.5 |       2750   |      nan   |                5   |           1 |             5.7 |    2543   |      14   |                8.4 |            2.4 |
| Jackson Heights                       | Queens        |       9 |           9 |        12.8 |          32   |       2178   |      639   |               61   |           3 |             4.8 |    1796   |       6   |                4.8 |            1.4 |
| Elmhurst                              | Queens        |       3 |           3 |        13.5 |          32   |       2494   |      850   |               69   |           4 |             3.4 |    2721   |       6   |                6.1 |            1.4 |
| Bedford-Stuyvesant (East)             | Brooklyn      |       3 |           3 |        18.7 |          38.5 |       2944   |      nan   |               21   |           6 |             3.3 |    3290   |       8   |                5.6 |            1.2 |
| Prospect Lefferts Gardens-Wingate     | Brooklyn      |       3 |           3 |        21.1 |          50   |       2944   |      nan   |               17   |           6 |             6.6 |    1447   |       7   |                5.9 |            1   |
| East Flatbush-Erasmus                 | Brooklyn      |       7 |           7 |        21.8 |          55   |       2794   |      600   |               19   |           6 |            11.7 |    1124   |       6   |                6.6 |            1.2 |
| East Harlem (North)                   | Manhattan     |       5 |           5 |        22   |          57.5 |       2903   |      400   |               41   |           1 |             5.4 |     572   |       6   |               11.2 |            1.3 |
| Mott Haven-Port Morris                | Bronx         |       9 |           9 |        22.6 |          60.5 |       2575   |      734   |               13   |           0 |             3.2 |     250   |      12   |               17.2 |            2.6 |
| East Flatbush-Farragut                | Brooklyn      |       5 |           5 |        22.7 |          60   |       2891   |      nan   |                5   |           0 |             7   |    2898   |       6   |                6.6 |            1.2 |
| Hempstead                             | Nassau County |       7 |           5 |        23   |          57   |       2371   |      820   |                9   |           2 |             5.3 |    2304   |     nan   |                5.6 |            2.3 |
| Flatbush (West)-Ditmas Park-Parkville | Brooklyn      |       4 |           4 |        26.4 |          62.5 |       2786.5 |      650   |                7.5 |           1 |            17.8 |    2552.5 |       7   |                4.1 |            0.8 |
| Norwood                               | Bronx         |       3 |           3 |        27.6 |          82.6 |       2202   |      750   |                3   |           0 |             3   |     811   |       8   |               10.3 |            2.2 |
| Jersey City                           | Hudson County |     229 |          36 |        37.8 |          79   |       2693   |      521   |                9   |           0 |             9.7 |     947   |      14   |                4.9 |            2.9 |

## Neighborhoods with fewer than 3 passing places (not shown on the page)

| hood                                           | area                                      | state   |   units |   drive_min |   all_in_med |
|:-----------------------------------------------|:------------------------------------------|:--------|--------:|------------:|-------------:|
| Jamaica Estates-Holliswood                     | Queens                                    | NY      |       1 |         6.4 |       2394   |
| Kew Gardens Hills                              | Queens                                    | NY      |       1 |         7.3 |       2378   |
| Pomonok-Electchester-Hillcrest                 | Queens                                    | NY      |       1 |         7.9 |       2994   |
| North Corona                                   | Queens                                    | NY      |       2 |        10.1 |       2641.5 |
| Rego Park                                      | Queens                                    | NY      |       1 |        10.6 |       2529   |
| Middle Village                                 | Queens                                    | NY      |       1 |        11.8 |       1979   |
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
| Flatlands                                      | Brooklyn                                  | NY      |       2 |        22.6 |       2224.5 |
| Concourse-Concourse Village                    | Bronx                                     | NY      |       1 |        22.6 |       2438   |
| Flatbush                                       | Brooklyn                                  | NY      |       2 |        23   |       2601.5 |
| Harlem (South)                                 | Manhattan                                 | NY      |       1 |        23.3 |       2908   |
| East Harlem (South)                            | Manhattan                                 | NY      |       1 |        23.8 |       2578   |
| Midwood                                        | Brooklyn                                  | NY      |       2 |        24.4 |       2718   |
| Tremont                                        | Bronx                                     | NY      |       1 |        24.4 |       2187   |
| Sheepshead Bay-Manhattan Beach-Gerritsen Beach | Brooklyn                                  | NY      |       2 |        24.6 |       1979   |
| Brighton Beach                                 | Brooklyn                                  | NY      |       2 |        24.9 |       2769.5 |
| Pelham Parkway-Van Nest                        | Bronx                                     | NY      |       2 |        25   |       2403   |
| Hamilton Heights-Sugar Hill                    | Manhattan                                 | NY      |       2 |        25   |       2594.5 |
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
| Fort Lee                                       | Bergen County                             | NJ      |       2 |        28.8 |       2812   |
| Gravesend (West)                               | Brooklyn                                  | NY      |       1 |        29   |       2494   |
| Bedford Park                                   | Bronx                                     | NY      |       1 |        29.1 |       2698   |
| Kingsbridge Heights-Van Cortlandt Village      | Bronx                                     | NY      |       1 |        29.1 |       2238   |
| Kingsbridge-Marble Hill                        | Bronx                                     | NY      |       1 |        30.9 |       2478   |
| Weehawken                                      | Hudson County                             | NJ      |       2 |        31.2 |       2840.5 |
| Bay Ridge                                      | Brooklyn                                  | NY      |       2 |        31.8 |       2314   |
| Larchmont                                      | Westchester County                        | NY      |       1 |        31.9 |       2803   |
| Union City                                     | Hudson County                             | NJ      |       2 |        32.8 |       2049.5 |
| Secaucus                                       | Hudson County                             | NJ      |       1 |        34.3 |       2556   |
| Mamaroneck                                     | Westchester County                        | NY      |       1 |        34.8 |       2328   |
| Hoboken                                        | Hudson County                             | NJ      |       1 |        35.6 |       2602   |
| Dumont                                         | Bergen County                             | NJ      |       1 |        39.7 |       2147   |
| Tompkinsville-Stapleton-Clifton-Fox Hills      | Staten Island                             | NY      |       1 |        42.1 |       2361   |
| Harrison                                       | Westchester County                        | NY      |       2 |        42.7 |       2935.5 |
| St. George-New Brighton                        | Staten Island                             | NY      |       1 |        45.8 |       2944   |
| Kearny                                         | Hudson County                             | NJ      |       1 |        46.1 |       2002   |
| Paterson                                       | Passaic County                            | NJ      |       1 |        46.3 |       1788   |
| Hawthorne                                      | Passaic County                            | NJ      |       1 |        46.4 |       2575   |
| New Springville-Willowbrook-Bulls Head-Travis  | Staten Island                             | NY      |       1 |        47.8 |       2579   |
| Ridgewood                                      | Bergen County                             | NJ      |       1 |        49.3 |       2527   |
| Tarrytown                                      | Westchester County                        | NY      |       1 |        49.3 |       2003   |
| Haledon                                        | Passaic County                            | NJ      |       1 |        49.9 |       2224   |
| Irvington                                      | Essex County                              | NJ      |       2 |        53.7 |       1342   |
| Union                                          | Union County                              | NJ      |       2 |        55.5 |       2924   |
| Montvale                                       | Bergen County                             | NJ      |       1 |        56.6 |       2847   |
| Roselle                                        | Union County                              | NJ      |       2 |        58.2 |       2689.5 |
| Springfield                                    | Union County                              | NJ      |       2 |        59   |       2767   |
| Summit                                         | Union County                              | NJ      |       2 |        62.2 |       2547.5 |
| Garwood                                        | Union County                              | NJ      |       1 |        63.9 |       2949   |
| Scotch Plains                                  | Union County                              | NJ      |       1 |        65.5 |       2409   |
| Madison                                        | Morris County                             | NJ      |       1 |        68.3 |       2316   |
| Morristown                                     | Morris County                             | NJ      |       2 |        70.2 |       2547.5 |
| Watchung                                       | Somerset County                           | NJ      |       2 |        70.8 |       2869   |
| Sayreville                                     | Middlesex County                          | NJ      |       1 |        70.8 |       2334   |
| Plainfield                                     | Union County                              | NJ      |       1 |        71.5 |       2432   |
| Morris Plains                                  | Morris County                             | NJ      |       1 |        71.5 |       2637   |
| South Plainfield                               | Middlesex County                          | NJ      |       1 |        72.2 |       2393   |
| East Brunswick                                 | Middlesex County                          | NJ      |       1 |        75.2 |       2352   |
| Rockaway                                       | Morris County                             | NJ      |       1 |        77.1 |       2737   |
| North Brunswick                                | Middlesex County                          | NJ      |       1 |        80.3 |       2347   |
| Old Bridge                                     | Middlesex County                          | NJ      |       2 |        81   |       2472.5 |
| Bridgeport                                     | Greater Bridgeport Planning Region        | CT      |       1 |        81.4 |       2017   |
| Bound Brook                                    | Somerset County                           | NJ      |       1 |        82.3 |       2352   |
| Roxbury                                        | Morris County                             | NJ      |       2 |        83.2 |       2812.5 |
| Netcong                                        | Morris County                             | NJ      |       1 |        84.7 |       2327   |
| Atlantic Highlands                             | Monmouth County                           | NJ      |       1 |        92.2 |       2837   |
| Freehold                                       | Monmouth County                           | NJ      |       1 |        93.6 |       2202   |
| West Long Branch                               | Monmouth County                           | NJ      |       2 |        95.5 |       2671.5 |
| Derby                                          | Naugatuck Valley Planning Region          | CT      |       1 |        97.2 |       1696   |
| Newburgh                                       | Orange County                             | NY      |       2 |       101.4 |       1940.5 |
| West Haven                                     | South Central Connecticut Planning Region | CT      |       1 |       103.4 |       1448   |
| Bordentown                                     | Burlington County                         | NJ      |       1 |       107.2 |       2452   |
| LaGrange                                       | Dutchess County                           | NY      |       1 |       117.2 |       2597   |
| New Paltz                                      | Ulster County                             | NY      |       2 |       119.3 |       2669.5 |
| Pennsauken                                     | Camden County                             | NJ      |       1 |       138.4 |       1952   |
