# Gate summary

Raw rows: 13611. After dedupe: 12913.

| status | listings | buildings |
|---|---|---|
| fail | 1228 | 1025 |
| pass | 74 | 46 |
| pending | 11611 | 8994 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 12913 | 0 | 0 |
| rent | 12913 | 0 | 0 |
| movein | 2261 | 183 | 10469 |
| dog | 4593 | 81 | 8239 |
| elevator | 757 | 34 | 12122 |
| floor | 3305 | 972 | 8636 |
| place | 12888 | 0 | 25 |
| proof | 2356 | 0 | 10557 |

## By source

| source_site                          |   fail |   pass |   pending |
|:-------------------------------------|-------:|-------:|----------:|
| anninlofts.com                       |      0 |      0 |         1 |
| apartmentlist.com                    |    116 |     42 |       668 |
| avaloncommunities.com                |     86 |      0 |        90 |
| bltliveworkplay.com (SightMap embed) |     28 |      2 |        47 |
| fairfieldproperties.com              |      3 |      0 |       309 |
| gardencommunities.com                |      8 |      2 |       116 |
| gardenhomesmanagement.com            |      4 |      0 |        16 |
| gdcrentals.com                       |      2 |      0 |        13 |
| greystar.com                         |    109 |      0 |       354 |
| newportrentals.com                   |      3 |      0 |         2 |
| solvermella.com                      |      2 |      0 |         3 |
| trulia                               |    794 |     11 |      6576 |
| vermellacrossing.com                 |      1 |      0 |        12 |
| vermellaharrison.com                 |      8 |      0 |         2 |
| vermellalyndhurst.com                |      1 |      0 |         1 |
| vermellawest.com                     |      1 |      0 |         0 |
| vermellawoodbridge.com               |      1 |      0 |         3 |
| www.shoregateli.com (SightMap embed) |      0 |      0 |         2 |
| www.vermellaeast.com                 |      1 |      0 |         0 |
| zumper                               |     60 |     17 |      3396 |

## Pending reasons (what would need confirming)

| pending_reasons           |   count |
|:--------------------------|--------:|
| movein;dog;elevator;proof |    5539 |
| movein;elevator;proof     |    3220 |
| dog;elevator              |     867 |
| movein;dog;elevator       |     427 |
| dog;elevator;proof        |     291 |
| elevator;proof            |     282 |
| elevator                  |     261 |
| movein;dog;proof          |     227 |
| dog                       |     153 |
| movein;proof              |     129 |
| movein;elevator           |      55 |
| proof                     |      54 |
| movein;dog                |      34 |
| dog;proof                 |      32 |
| movein                    |      20 |

## Passing listings by state and city (top 40)

|                                      |   0 |
|:-------------------------------------|----:|
| ('NY', 'New Rochelle')               |  29 |
| ('NY', 'New York')                   |  16 |
| ('NY', 'Jamaica')                    |  11 |
| ('NY', 'Brooklyn')                   |   3 |
| ('NJ', 'Fort Lee')                   |   3 |
| ('NY', 'New York City')              |   2 |
| ('CT', 'Stamford')                   |   2 |
| ('NJ', 'Wharton, Rockaway Township') |   1 |
| ('NJ', 'Union City')                 |   1 |
| ('NJ', 'Hackensack')                 |   1 |
| ('NJ', 'Edgewater')                  |   1 |
| ('NY', 'Long Beach')                 |   1 |
| ('NY', 'Hempstead')                  |   1 |
| ('NY', 'Queens')                     |   1 |
| ('NY', 'Valley Stream')              |   1 |
