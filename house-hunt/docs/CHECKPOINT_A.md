# Checkpoint A: neighborhoods and proposed years

Passing units: 1179 in 680 buildings, across 211 neighborhoods; 84 neighborhoods have 3+ passing places.

Cluster quality (silhouette; higher is cleaner): {5: 0.138, 6: 0.152}. Using k=6.

## Group 1: 11 neighborhoods, 101 places

Distinguishing traits (standard deviations from the average): sqft_med -1.4, park_ha_800m -0.9, restaurants_800m -0.8, all_in_med -0.8

| hood            | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:----------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Islip           | Suffolk County                            |       6 |           5 |        54.6 |         103.5 |         2245 |        400 |                0.5 |           0 |            20.5 |       949 |       nan |                1   |            1.1 |
| Edison          | Middlesex County                          |       7 |           3 |        66.8 |         158   |         2121 |        300 |                1   |           0 |            15.2 |      1550 |       nan |                1.8 |            0.9 |
| Piscataway      | Middlesex County                          |       9 |           2 |        75   |         nan   |         2061 |        300 |                0   |           0 |            21.7 |      1587 |       nan |                1.1 |            0.8 |
| Franklin        | Somerset County                           |      20 |           5 |        81.7 |         nan   |         1997 |        300 |                1   |           0 |             9.4 |      1130 |       nan |                0.3 |            0.4 |
| Brookhaven      | Suffolk County                            |      11 |          11 |        83.4 |         168.5 |         2135 |        465 |                0   |           0 |             5.9 |      1420 |       nan |                1   |            1.1 |
| Mount Olive     | Morris County                             |       6 |           1 |        83.8 |         nan   |         1748 |        300 |                4   |           0 |            16.1 |       571 |       nan |                0.4 |            0.2 |
| South Brunswick | Middlesex County                          |       6 |           2 |        88.6 |         nan   |         2091 |        300 |                0   |           0 |            18.4 |      2771 |       nan |                1.2 |            0.6 |
| Hackettstown    | Warren County                             |       4 |           1 |        97   |         nan   |         1893 |        580 |                0   |           0 |            24.4 |      1622 |       nan |                0.4 |            0.2 |
| New Milford     | Western Connecticut Planning Region       |       3 |           2 |       106.2 |         nan   |         1704 |        700 |                1   |           0 |            15   |       980 |       nan |                0.4 |            0.6 |
| East Haven      | South Central Connecticut Planning Region |      25 |           6 |       111.8 |         220   |         1672 |        425 |                2   |           0 |             5   |      1414 |       nan |                0.9 |            2.1 |
| Morrisville     | Bucks County                              |       4 |           3 |       113.9 |         nan   |         1644 |        715 |                2   |           0 |            12.2 |      1116 |       nan |                1.6 |            1.8 |

## Group 2: 28 neighborhoods, 263 places

Distinguishing traits (standard deviations from the average): sqft_med +0.7, drive_min +0.5, violent_per_1000 -0.5, all_in_med +0.5

| hood            | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:----------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Hackensack      | Bergen County                             |       3 |           3 |        37.6 |         100   |       2152   |      787.5 |                1   |           0 |             4.2 |     926   |       nan |                2.4 |            1.3 |
| Babylon         | Suffolk County                            |       4 |           4 |        40   |          75   |       2298   |      605   |                1.5 |           0 |            12.4 |    1990   |       nan |                1   |            1.1 |
| Linden          | Union County                              |       3 |           1 |        53.7 |          98   |       2373   |      701   |                1   |           0 |             9.5 |     861   |       nan |                1.9 |            2   |
| Carteret        | Middlesex County                          |       4 |           1 |        58.5 |         108.5 |       2296.5 |      801.5 |                0   |           0 |             9.6 |     692   |       nan |                2   |            1.2 |
| Woodbridge      | Middlesex County                          |      21 |           6 |        62.9 |         123.5 |       2234   |      719   |                0   |           0 |             7.4 |    2234   |       nan |                1.4 |            0.8 |
| Ossining        | Westchester County                        |       3 |           1 |        63.3 |         145   |       2188   |      700   |                1   |           0 |             5.9 |     943   |       nan |                0.7 |            0.3 |
| Boonton         | Morris County                             |       4 |           3 |        68.2 |         182   |       2136.5 |      523   |                3   |           0 |            17.6 |    1440   |       nan |                0.6 |            0.4 |
| Aberdeen        | Monmouth County                           |       3 |           2 |        75.4 |         nan   |       2262   |      811   |                1   |           0 |            13.5 |    1396   |       nan |                1.6 |            0.4 |
| Mount Arlington | Morris County                             |       4 |           1 |        78.7 |         nan   |       2236.5 |      751.5 |                2   |           0 |            23.4 |    1837   |       nan |                0   |            0   |
| Raritan         | Somerset County                           |       3 |           1 |        86.5 |         151   |       2325   |      770   |               10   |           1 |             9.6 |     625   |       nan |                1.2 |            0.2 |
| Stratford       | Greater Bridgeport Planning Region        |      11 |           4 |        87.4 |         164   |       2367   |      720   |                6   |           0 |             7.5 |     404   |       nan |                0.5 |            1.7 |
| Trumbull        | Greater Bridgeport Planning Region        |       5 |           1 |        87.8 |         nan   |       2247   |      713   |                0   |           0 |             8.7 |    1269   |       nan |                0.8 |            0.8 |
| Danbury         | Western Connecticut Planning Region       |      12 |           5 |        90.8 |         265   |       2248.5 |      746   |                1   |           0 |            11   |    2408.5 |       nan |                1.4 |            0.6 |
| Milford         | South Central Connecticut Planning Region |      16 |           9 |        91.9 |         193   |       2067   |      579   |                3.5 |           1 |            11.9 |    1318   |       nan |                0.7 |            2.1 |
| Plainsboro      | Middlesex County                          |      34 |           3 |        92.1 |         211   |       2075.5 |      647   |                0   |           0 |            11.9 |    1566   |       nan |                0.4 |            0.4 |
| Goshen          | Orange County                             |       3 |           3 |        96.2 |         nan   |       1843   |      800   |                8   |           1 |             1.2 |    2326   |       nan |                0.9 |            0   |
| Hillsborough    | Somerset County                           |       6 |           1 |        96.5 |         nan   |       2097   |      882.5 |                4   |           0 |             9.5 |    3621   |       nan |                1   |            0.1 |
| New Windsor     | Orange County                             |       3 |           3 |        99.4 |         nan   |       2122   |      835.5 |                2   |           0 |             1.4 |    1772   |       nan |                1   |            0.1 |
| Lawrence        | Mercer County                             |      14 |           3 |       101.3 |         182   |       2311   |      742.5 |                4   |           0 |            14.7 |    2463   |       nan |                0.4 |            1   |
| West Windsor    | Mercer County                             |      14 |           5 |       101.7 |         197   |       2264   |      825   |                3   |           0 |            14.2 |    2872   |       nan |                0.5 |            0.3 |
| West Haven      | South Central Connecticut Planning Region |      17 |          10 |       102.9 |         181   |       2052   |      898   |                2   |           0 |             5.7 |     986   |       nan |                0.6 |            1.6 |
| Middletown      | Orange County                             |       3 |           2 |       103.9 |         nan   |       2360   |      763.5 |               10   |           2 |             6.9 |    2063   |       nan |                3.6 |            0.6 |
| Hamilton        | Mercer County                             |       6 |           1 |       103.9 |         182   |       2072   |      768   |                0   |           0 |            11.5 |     462   |       nan |                1.6 |            1.6 |
| Wallkill        | Orange County                             |       7 |           6 |       104.3 |         nan   |       2090   |      655   |                2   |           0 |            12.6 |    1701   |       nan |                0.5 |            0.1 |
| Flemington      | Hunterdon County                          |       6 |           5 |       104.7 |         nan   |       2265.5 |      672.5 |                8   |           0 |             9.7 |    2517   |       nan |                3   |            0.4 |
| Hamden          | South Central Connecticut Planning Region |      40 |          14 |       112.7 |         226   |       2008.5 |      713   |                0   |           0 |            16.2 |    1238.5 |       nan |                1.7 |            3.9 |
| Lopatcong       | Warren County                             |       7 |           2 |       114.4 |         nan   |       2087   |      816   |                2   |           0 |            15.8 |    2876   |       nan |                0.6 |            0.4 |
| Burlington      | Burlington County                         |       7 |           2 |       118.2 |         247   |       2371   |      705   |                2   |           0 |            59.4 |    3406   |       nan |                1.6 |            1.1 |

## Group 3: 11 neighborhoods, 138 places

Distinguishing traits (standard deviations from the average): water_m -1.5, transit_min +1.2, drive_min +0.6, bars_800m -0.5

| hood            | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:----------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Bayonne         | Hudson County                             |      21 |          18 |        45.6 |           101 |         1952 |        600 |                  2 |           0 |             6.2 |       274 |       nan |                2.8 |            1.1 |
| Norwalk         | Western Connecticut Planning Region       |      22 |          12 |        63.9 |           149 |         2129 |        559 |                  9 |           0 |             7.3 |       620 |         3 |                0.5 |            1.2 |
| Patchogue       | Suffolk County                            |       3 |           3 |        68.5 |           105 |         2345 |        485 |                  2 |           0 |            15.3 |        96 |       nan |                1   |            1.1 |
| New Brunswick   | Middlesex County                          |      16 |           3 |        73.7 |           136 |         2017 |        620 |                  2 |           0 |             5.5 |       172 |       nan |                5.1 |            1.6 |
| Bridgeport      | Greater Bridgeport Planning Region        |      41 |          15 |        82.7 |           151 |         2017 |        491 |                  4 |           0 |             9.9 |       267 |       nan |                2.5 |            3.4 |
| Long Branch     | Monmouth County                           |       9 |           3 |        99.9 |           190 |         1977 |        500 |                  4 |           0 |             4.9 |       498 |       nan |                2.3 |            0.5 |
| Seymour         | Naugatuck Valley Planning Region          |       3 |           2 |       104.3 |           271 |         2179 |        850 |                  7 |           0 |            15   |       277 |       nan |                0.5 |            0.9 |
| Beacon Falls    | Naugatuck Valley Planning Region          |       8 |           1 |       108.8 |           310 |         1984 |        650 |                  2 |           1 |            11.3 |       108 |       nan |              nan   |          nan   |
| Naugatuck       | Naugatuck Valley Planning Region          |       7 |           4 |       114.8 |           325 |         2012 |        850 |                  0 |           0 |             8.2 |       709 |       nan |                0.6 |            0.9 |
| North Haven     | South Central Connecticut Planning Region |       3 |           2 |       115.9 |           286 |         1848 |        nan |                  0 |           0 |             7   |       990 |       nan |                0.4 |            3.1 |
| Lower Makefield | Bucks County                              |       5 |           2 |       118   |           257 |         2307 |        775 |                  2 |           0 |             0.4 |       389 |       nan |                0.3 |            0.4 |

## Group 4: 19 neighborhoods, 316 places

Distinguishing traits (standard deviations from the average): bars_800m +1.3, restaurants_800m +1.2, drive_min -1.0, park_ha_800m +0.7

| hood                     | area                                      |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------------------|:------------------------------------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Jamaica Hills-Briarwood  | Queens                                    |       8 |           8 |         4   |          17.2 |       2244   |      525   |                8   |         1.5 |             4.9 |    1749   |       6   |                2.4 |            2.2 |
| Forest Hills             | Queens                                    |       3 |           3 |         6.3 |          27.5 |       1779   |      500   |               38   |         1   |             7.3 |    1295   |       6.5 |                2.1 |            1.4 |
| Flushing-Willets Point   | Queens                                    |      10 |          10 |        11.6 |          41.6 |       2308.5 |      590   |               86.5 |         3   |             4   |     746   |       6   |                2.6 |            2.2 |
| Jackson Heights          | Queens                                    |      10 |          10 |        12.8 |          32   |       2235.5 |      639   |               61   |         3   |             4.9 |    1802   |       6   |                4.8 |            1.4 |
| Astoria (Central)        | Queens                                    |       3 |           3 |        16.8 |          42.5 |       2203   |      700   |              122   |        30   |            11.3 |    1378   |       2   |                3.7 |            1.7 |
| Hempstead                | Nassau County                             |       5 |           4 |        23   |          57   |       2160   |      nan   |               22   |         5   |             1.3 |    2167   |     nan   |                5.6 |            2.3 |
| Long Beach               | Nassau County                             |       4 |           2 |        27.9 |          74   |       2285   |      nan   |                6   |         2   |            29.6 |     194   |     nan   |                0.8 |            0   |
| Riverdale-Spuyten Duyvil | Bronx                                     |       3 |           3 |        32.2 |          85   |       2283   |      898   |                5   |         0   |             2   |     660   |       6   |                3.4 |            2.6 |
| Tuckahoe                 | Westchester County                        |       3 |           2 |        33.6 |         101   |       2278   |      650   |                3   |         1   |             1.9 |     248   |     nan   |                0.3 |            0.2 |
| North Bergen             | Hudson County                             |       4 |           4 |        35.5 |          76.5 |       2208   |      626   |                9.5 |         0   |             4.2 |     488.5 |     nan   |                1.3 |            1.3 |
| Yonkers                  | Westchester County                        |      11 |           9 |        36.7 |         106   |       2183   |      500   |                3   |         1   |             3.2 |     607   |     nan   |                3.9 |            1.5 |
| Belleville               | Essex County                              |       8 |           5 |        44.8 |         103   |       2302   |      636   |                5   |         1   |             7   |     540.5 |     nan   |                2.4 |            2.9 |
| Kearny                   | Hudson County                             |       5 |           4 |        46.4 |         100   |       2027   |      547.5 |               11   |         1   |             7.8 |     851   |     nan   |                2.2 |            1.8 |
| Bloomfield               | Essex County                              |      13 |           9 |        51.8 |         107   |       2265   |      587   |               14   |         1   |             3.3 |    3453   |     nan   |                0.8 |            1.3 |
| Stamford                 | Western Connecticut Planning Region       |      27 |          16 |        53.6 |         130   |       2074   |      500   |               15   |         3   |             7.4 |    1222   |     nan   |                1.5 |            1.2 |
| Millburn                 | Essex County                              |       3 |           2 |        58.3 |         115   |       2205   |      480   |                7   |         1   |             6.9 |    4113   |     nan   |                0.1 |            0.3 |
| Morristown               | Morris County                             |       3 |           2 |        72.2 |         143   |       2345   |      488   |               53   |         5   |             7.5 |     451   |     nan   |                0.7 |            0.2 |
| Dover                    | Morris County                             |       4 |           1 |        74.8 |         172   |       2304   |      613   |               27   |         7   |             2.2 |    2682   |     nan   |                0.8 |            0.6 |
| New Haven                | South Central Connecticut Planning Region |     189 |          43 |       108.4 |         181   |       2067   |      537   |               55   |        17   |             4.1 |    1177   |     nan   |                4   |            6.1 |

## Group 5: 14 neighborhoods, 185 places

Distinguishing traits (standard deviations from the average): violent_per_1000 +1.6, all_in_med -0.9, drive_min -0.6, transit_min -0.5

| hood                           | area           |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:-------------------------------|:---------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Norwood                        | Bronx          |       3 |           3 |        27.6 |          82.6 |         2202 |      750   |                3   |           0 |             3   |       811 |         8 |               10.3 |            2.2 |
| West New York                  | Hudson County  |       8 |           8 |        34.8 |          73.5 |         1947 |      550   |               18   |           0 |             8.5 |       939 |       nan |                2.4 |            1.1 |
| Jersey City – Journal Square   | Hudson County  |       4 |           4 |        35.6 |          70   |         2097 |      570   |               25.5 |           1 |            15.7 |      1255 |       nan |                4.9 |            2.9 |
| Jersey City – Bergen-Lafayette | Hudson County  |       5 |           5 |        39.2 |          85   |         2002 |      680   |                6   |           0 |             2.6 |      1753 |       nan |                4.9 |            2.9 |
| Jersey City – West Side        | Hudson County  |      12 |           7 |        40.7 |          85   |         2223 |      443   |                5   |           0 |             8.4 |       819 |       nan |                4.9 |            2.9 |
| Jersey City – Greenville       | Hudson County  |       8 |           8 |        41.4 |          91   |         2002 |      650   |                4   |           0 |             2.2 |      1029 |       nan |                4.9 |            2.9 |
| Paterson                       | Passaic County |      41 |          38 |        46.4 |         122   |         1870 |      750   |                5   |           1 |             6.2 |       642 |       nan |                8.8 |            4.7 |
| Newark                         | Essex County   |      57 |          46 |        47.7 |          85   |         1952 |      609   |                8   |           1 |             4.4 |      1105 |         6 |                5.2 |            6.9 |
| Elizabeth                      | Union County   |       7 |           7 |        51.5 |          98   |         1839 |      600   |                7   |           0 |             8   |       697 |       nan |                3.4 |            4.8 |
| East Orange                    | Essex County   |       7 |           6 |        51.7 |          98   |         1901 |      806   |                0   |           0 |             3.9 |      3515 |       nan |                4.2 |            4.7 |
| Irvington                      | Essex County   |       7 |           7 |        52.1 |         107   |         1352 |      550   |                2   |           0 |            14.1 |      3538 |       nan |                4   |            9.1 |
| City of Orange                 | Essex County   |       7 |           5 |        53.2 |          98   |         2127 |      500   |                0   |           1 |            15.7 |      3903 |       nan |                4.2 |            5.6 |
| Newburgh                       | Orange County  |      13 |          12 |       102.4 |         nan   |         1697 |      635.5 |                2   |           1 |             5.8 |       556 |       nan |                9.8 |            1.8 |
| Trenton                        | Mercer County  |       6 |           6 |       114.6 |         169.5 |         1442 |      600   |                2   |           0 |             1.6 |       381 |       nan |                8.1 |            5.3 |

## Group 6: 1 neighborhoods, 11 places

Distinguishing traits (standard deviations from the average): bfloors +7.6, violent_per_1000 +1.2, restaurants_800m +1.1, bars_800m +1.1

| hood                          | area          |   units |   buildings |   drive_min |   transit_min |   all_in_med |   sqft_med |   restaurants_800m |   bars_800m |   park_walk_min |   water_m |   bfloors |   violent_per_1000 |   mvt_per_1000 |
|:------------------------------|:--------------|--------:|------------:|------------:|--------------:|-------------:|-----------:|-------------------:|------------:|----------------:|----------:|----------:|-------------------:|---------------:|
| Jersey City – McGinley Square | Hudson County |      11 |           9 |        37.6 |            77 |         2002 |        474 |                 15 |           2 |             7.8 |      1804 |        14 |                4.9 |            2.9 |

## Neighborhoods with fewer than 3 passing places (not shown on the page)

| hood                                           | area                                | state   |   units |   drive_min |   all_in_med |
|:-----------------------------------------------|:------------------------------------|:--------|--------:|------------:|-------------:|
| Jamaica                                        | Queens                              | NY      |       2 |         2.7 |       1900   |
| Kew Gardens                                    | Queens                              | NY      |       1 |         4.9 |       2294   |
| Jamaica Estates-Holliswood                     | Queens                              | NY      |       1 |         6.4 |       2394   |
| Kew Gardens Hills                              | Queens                              | NY      |       1 |         7.3 |       2378   |
| St. Albans                                     | Queens                              | NY      |       1 |         7.8 |       1649   |
| Fresh Meadows-Utopia                           | Queens                              | NY      |       1 |         8.7 |       1094   |
| Glendale                                       | Queens                              | NY      |       2 |         8.7 |       2051.5 |
| Queens Village                                 | Queens                              | NY      |       1 |        10.4 |       2194   |
| Rego Park                                      | Queens                              | NY      |       1 |        10.5 |       2179   |
| Middle Village                                 | Queens                              | NY      |       1 |        11.8 |       1979   |
| Murray Hill-Broadway Flushing                  | Queens                              | NY      |       2 |        12.4 |       2210.5 |
| Elmhurst                                       | Queens                              | NY      |       2 |        13.8 |       2053.5 |
| Woodside                                       | Queens                              | NY      |       1 |        14.9 |       2394   |
| Bayside                                        | Queens                              | NY      |       1 |        15.1 |       2198   |
| Sunnyside                                      | Queens                              | NY      |       1 |        18.3 |       1878   |
| East Williamsburg                              | Brooklyn                            | NY      |       1 |        18.9 |       1994   |
| Long Island City-Hunters Point                 | Queens                              | NY      |       1 |        18.9 |       1577   |
| Throgs Neck-Schuylerville                      | Bronx                               | NY      |       1 |        20.2 |       2303   |
| Mott Haven-Port Morris                         | Bronx                               | NY      |       2 |        21.8 |       2262.5 |
| Crown Heights (North)                          | Brooklyn                            | NY      |       1 |        21.8 |       2379   |
| Morris Park                                    | Bronx                               | NY      |       2 |        22   |       2252.5 |
| Flatlands                                      | Brooklyn                            | NY      |       1 |        22.4 |       1928   |
| Crotona Park East                              | Bronx                               | NY      |       1 |        23.7 |       1583   |
| Tremont                                        | Bronx                               | NY      |       2 |        24.6 |       2137   |
| Eastchester-Edenwald-Baychester                | Bronx                               | NY      |       1 |        24.7 |       1503   |
| Brooklyn Heights                               | Brooklyn                            | NY      |       1 |        24.9 |       1744   |
| Pelham Parkway-Van Nest                        | Bronx                               | NY      |       2 |        25   |       2403   |
| Harlem (North)                                 | Manhattan                           | NY      |       2 |        25   |       2343   |
| Mount Hope                                     | Bronx                               | NY      |       2 |        25.1 |       1975.5 |
| Sheepshead Bay-Manhattan Beach-Gerritsen Beach | Brooklyn                            | NY      |       2 |        25.4 |       1904   |
| Gravesend (South)                              | Brooklyn                            | NY      |       1 |        26.2 |       2079   |
| Gravesend (East)-Homecrest                     | Brooklyn                            | NY      |       1 |        27   |       2394   |
| Williamsbridge-Olinville                       | Bronx                               | NY      |       1 |        27   |       2108   |
| Sunset Park (East)-Borough Park (West)         | Brooklyn                            | NY      |       1 |        27.6 |       2094   |
| University Heights (South)-Morris Heights      | Bronx                               | NY      |       1 |        27.8 |       1880   |
| Flatbush (West)-Ditmas Park-Parkville          | Brooklyn                            | NY      |       1 |        28.3 |       2294   |
| Bensonhurst                                    | Brooklyn                            | NY      |       2 |        28.4 |       2186.5 |
| Bath Beach                                     | Brooklyn                            | NY      |       1 |        28.7 |       2004   |
| New Rochelle                                   | Westchester County                  | NY      |       2 |        28.8 |       2287.5 |
| Fort Lee                                       | Bergen County                       | NJ      |       1 |        29.4 |       2197   |
| Wakefield-Woodlawn                             | Bronx                               | NY      |       1 |        29.7 |       1688   |
| Kingsbridge Heights-Van Cortlandt Village      | Bronx                               | NY      |       2 |        30   |       1920.5 |
| Mount Vernon                                   | Westchester County                  | NY      |       2 |        30.6 |       2189.5 |
| Bay Ridge                                      | Brooklyn                            | NY      |       1 |        32.5 |       1839   |
| Union City                                     | Hudson County                       | NJ      |       2 |        32.8 |       2049.5 |
| Eastchester                                    | Westchester County                  | NY      |       1 |        32.8 |       2398   |
| Cliffside Park                                 | Bergen County                       | NJ      |       1 |        33.2 |       2252   |
| Mamaroneck                                     | Westchester County                  | NY      |       1 |        34.8 |       2328   |
| Englewood                                      | Bergen County                       | NJ      |       2 |        35   |       2400   |
| Fairview                                       | Bergen County                       | NJ      |       2 |        35.2 |       2052   |
| Jersey City – The Heights                      | Hudson County                       | NJ      |       1 |        36.9 |       1947   |
| Port Chester                                   | Westchester County                  | NY      |       1 |        41.9 |       2303   |
| Tompkinsville-Stapleton-Clifton-Fox Hills      | Staten Island                       | NY      |       1 |        42.1 |       2361   |
| Garfield                                       | Bergen County                       | NJ      |       1 |        42.8 |       2247   |
| Dobbs Ferry                                    | Westchester County                  | NY      |       2 |        43.2 |       2352.5 |
| New Dorp-Midland Beach                         | Staten Island                       | NY      |       2 |        43.7 |       1579   |
| Nutley                                         | Essex County                        | NJ      |       2 |        45.4 |       1882   |
| Clifton                                        | Passaic County                      | NJ      |       1 |        46   |       2275   |
| Hawthorne                                      | Passaic County                      | NJ      |       1 |        46.4 |       2252   |
| Harrison                                       | Hudson County                       | NJ      |       2 |        46.4 |       2342.5 |
| Brightwaters                                   | Suffolk County                      | NY      |       1 |        47.8 |       2160   |
| Huntington                                     | Suffolk County                      | NY      |       2 |        47.9 |       1895.5 |
| New Springville-Willowbrook-Bulls Head-Travis  | Staten Island                       | NY      |       1 |        48.3 |       1579   |
| Montclair                                      | Essex County                        | NJ      |       2 |        52.2 |       2299   |
| Orangetown                                     | Rockland County                     | NY      |       1 |        54.3 |       2265   |
| Maplewood                                      | Essex County                        | NJ      |       1 |        54.4 |       2342   |
| Verona                                         | Essex County                        | NJ      |       1 |        56.2 |       2042   |
| West Orange                                    | Essex County                        | NJ      |       2 |        56.4 |       2074.5 |
| Mahwah                                         | Bergen County                       | NJ      |       1 |        57   |       2246   |
| South Orange                                   | Essex County                        | NJ      |       1 |        57.5 |       2242   |
| Rahway                                         | Union County                        | NJ      |       2 |        58   |       2254   |
| Smithtown                                      | Suffolk County                      | NY      |       1 |        59.9 |       2350   |
| Cranford                                       | Union County                        | NJ      |       1 |        61.3 |       2399   |
| Parsippany-Troy Hills                          | Morris County                       | NJ      |       1 |        63.6 |       2429   |
| Mount Kisco                                    | Westchester County                  | NY      |       2 |        63.7 |       2095.5 |
| Croton-on-Hudson                               | Westchester County                  | NY      |       1 |        67.2 |       1897   |
| Bedford                                        | Westchester County                  | NY      |       2 |        67.8 |       2115.5 |
| Sayreville                                     | Middlesex County                    | NJ      |       1 |        70.8 |       2333   |
| Cortlandt                                      | Westchester County                  | NY      |       1 |        71.4 |       1623   |
| North Plainfield                               | Somerset County                     | NJ      |       2 |        72   |       1767   |
| Pound Ridge                                    | Westchester County                  | NY      |       1 |        73.2 |       2263   |
| Wilton                                         | Western Connecticut Planning Region | CT      |       1 |        74   |       2129   |
| Plainfield                                     | Union County                        | NJ      |       2 |        74.7 |       1769.5 |
| Peekskill                                      | Westchester County                  | NY      |       1 |        77.1 |       2298   |
| Brewster                                       | Putnam County                       | NY      |       1 |        78.2 |       1984   |
| Fairfield                                      | Greater Bridgeport Planning Region  | CT      |       2 |        78.8 |       1760   |
| North Brunswick                                | Middlesex County                    | NJ      |       1 |        79.1 |       2047   |
| Middlesex                                      | Middlesex County                    | NJ      |       1 |        79.5 |       2147   |
| North Salem                                    | Westchester County                  | NY      |       1 |        80.4 |       2263   |
| Bound Brook                                    | Somerset County                     | NJ      |       2 |        81.9 |       2250.5 |
| Bridgewater                                    | Somerset County                     | NJ      |       1 |        83.6 |       1951   |
| Putnam Valley                                  | Putnam County                       | NY      |       1 |        83.8 |       2367   |
| Keansburg                                      | Monmouth County                     | NJ      |       1 |        84.2 |       1887   |
| Greenwood Lake                                 | Orange County                       | NY      |       1 |        84.5 |       1854   |
| Netcong                                        | Morris County                       | NJ      |       1 |        84.7 |       2327   |
| Somerville                                     | Somerset County                     | NJ      |       1 |        86.2 |       2347   |
| Manville                                       | Somerset County                     | NJ      |       1 |        87.7 |       2102   |
| Shelton                                        | Naugatuck Valley Planning Region    | CT      |       2 |        89.5 |       2024   |
| Red Bank                                       | Monmouth County                     | NJ      |       1 |        89.8 |       1737   |
| Freehold                                       | Monmouth County                     | NJ      |       1 |        93.6 |       2202   |
| Eatontown                                      | Monmouth County                     | NJ      |       1 |        93.6 |       2212   |
| Florida                                        | Orange County                       | NY      |       1 |        95.3 |       1965   |
| Independence                                   | Warren County                       | NJ      |       1 |        96.4 |       1624   |
| Derby                                          | Naugatuck Valley Planning Region    | CT      |       1 |        97.2 |       1696   |
| Warwick                                        | Orange County                       | NY      |       1 |        97.3 |       1965   |
| Riverhead                                      | Suffolk County                      | NY      |       1 |        98.6 |       2250   |
| Brookfield                                     | Western Connecticut Planning Region | CT      |       1 |        98.7 |       2328   |
| Neptune City                                   | Monmouth County                     | NJ      |       1 |        99.5 |       2142   |
| Ocean                                          | Monmouth County                     | NJ      |       1 |       100.4 |       2032   |
| East Fishkill                                  | Dutchess County                     | NY      |       2 |       100.5 |       1947   |
| Asbury Park                                    | Monmouth County                     | NJ      |       2 |       100.6 |       1959.5 |
| Neptune                                        | Monmouth County                     | NJ      |       1 |       102.6 |       1729   |
| Maybrook                                       | Orange County                       | NY      |       1 |       104.2 |       1797   |
| Howell                                         | Monmouth County                     | NJ      |       1 |       104.3 |       1937   |
| Fishkill                                       | Dutchess County                     | NY      |       1 |       104.4 |       1786   |
| Beacon                                         | Dutchess County                     | NY      |       1 |       106.4 |       2147   |
| Bordentown                                     | Burlington County                   | NJ      |       1 |       108.5 |       2018   |
| Wappinger                                      | Dutchess County                     | NY      |       1 |       109.7 |       1917   |
| White                                          | Warren County                       | NJ      |       1 |       111.2 |       1787   |
| Shawangunk                                     | Ulster County                       | NY      |       1 |       114.8 |       1847   |
| Florence                                       | Burlington County                   | NJ      |       1 |       115.2 |       1877   |
| Woodbury                                       | Naugatuck Valley Planning Region    | CT      |       1 |       116.4 |       1875   |
| Waterbury                                      | Naugatuck Valley Planning Region    | CT      |       2 |       118.8 |       1660   |
| New Paltz                                      | Ulster County                       | NY      |       2 |       119.2 |       1641   |
| Poughkeepsie                                   | Dutchess County                     | NY      |       2 |       120.2 |       2072   |
| Mount Holly                                    | Burlington County                   | NJ      |       1 |       120.5 |       1807   |
| Falls                                          | Bucks County                        | PA      |       1 |       122.1 |       2057   |
