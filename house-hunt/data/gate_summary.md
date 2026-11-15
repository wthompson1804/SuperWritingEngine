# Gate summary

Raw rows: 13715. After dedupe: 13000.

| status | listings | buildings |
|---|---|---|
| fail | 1237 | 1034 |
| pass | 192 | 117 |
| pending | 11571 | 8993 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 13000 | 0 | 0 |
| rent | 13000 | 0 | 0 |
| movein | 2279 | 183 | 10538 |
| dog | 4635 | 81 | 8284 |
| elevator | 1871 | 35 | 11094 |
| floor | 3324 | 980 | 8696 |
| place | 12975 | 0 | 25 |
| proof | 2374 | 0 | 10626 |

## By source

| source_site                          |   fail |   pass |   pending |
|:-------------------------------------|-------:|-------:|----------:|
| anninlofts.com                       |      0 |      0 |         1 |
| apartmentlist.com                    |    117 |     77 |       650 |
| avaloncommunities.com                |     86 |     49 |        41 |
| bltliveworkplay.com (SightMap embed) |     28 |      2 |        47 |
| fairfieldproperties.com              |      3 |      0 |       309 |
| gardencommunities.com                |      8 |      2 |       116 |
| gardenhomesmanagement.com            |      4 |      0 |        16 |
| gdcrentals.com                       |      2 |      0 |        13 |
| greystar.com                         |    109 |     28 |       326 |
| newportrentals.com                   |      3 |      0 |         2 |
| solvermella.com                      |      2 |      0 |         3 |
| trulia                               |    802 |     11 |      6640 |
| vermellacrossing.com                 |      1 |      0 |        12 |
| vermellaharrison.com                 |      8 |      0 |         2 |
| vermellalyndhurst.com                |      1 |      1 |         0 |
| vermellawest.com                     |      1 |      0 |         0 |
| vermellawoodbridge.com               |      1 |      0 |         3 |
| www.shoregateli.com (SightMap embed) |      0 |      0 |         2 |
| www.vermellaeast.com                 |      1 |      0 |         0 |
| zumper                               |     60 |     22 |      3388 |

## Pending reasons (what would need confirming)

| pending_reasons           |   count |
|:--------------------------|--------:|
| movein;dog;elevator;proof |    5300 |
| movein;elevator;proof     |    2837 |
| dog;elevator              |     675 |
| movein;proof              |     540 |
| movein;dog;proof          |     499 |
| movein;dog;elevator       |     419 |
| dog                       |     352 |
| dog;elevator;proof        |     291 |
| elevator;proof            |     282 |
| elevator                  |     153 |
| proof                     |      54 |
| movein;elevator           |      53 |
| movein;dog                |      42 |
| dog;proof                 |      32 |
| movein                    |      22 |

## Passing listings by state and city (top 40)

|                                      |   0 |
|:-------------------------------------|----:|
| ('NY', 'New Rochelle')               |  45 |
| ('NJ', 'West Windsor')               |  39 |
| ('NY', 'New York')                   |  21 |
| ('NY', 'White Plains')               |  13 |
| ('NY', 'Jamaica')                    |  11 |
| ('NJ', 'Fort Lee')                   |   9 |
| ('NJ', 'Cliffside Park')             |   8 |
| ('NJ', 'West New York')              |   6 |
| ('NJ', 'Cranford')                   |   4 |
| ('NY', 'Brooklyn')                   |   4 |
| ('NY', 'Westbury')                   |   3 |
| ('NJ', 'New Brunswick')              |   3 |
| ('NY', 'Yonkers')                    |   3 |
| ('NJ', 'Boonton')                    |   2 |
| ('CT', 'Stamford')                   |   2 |
| ('NY', 'New York City')              |   2 |
| ('NJ', 'Old Bridge')                 |   2 |
| ('NJ', 'Edgewater')                  |   2 |
| ('NJ', 'Union')                      |   2 |
| ('NJ', 'Jersey City')                |   1 |
| ('NJ', 'Princeton')                  |   1 |
| ('NJ', 'Hackensack')                 |   1 |
| ('NJ', 'Wayne')                      |   1 |
| ('NJ', 'Union City')                 |   1 |
| ('NJ', 'Wharton, Rockaway Township') |   1 |
| ('NJ', 'Wy Lyndhurst')               |   1 |
| ('NY', 'Long Beach')                 |   1 |
| ('NY', 'Hempstead')                  |   1 |
| ('NY', 'Queens')                     |   1 |
| ('NY', 'Valley Stream')              |   1 |
