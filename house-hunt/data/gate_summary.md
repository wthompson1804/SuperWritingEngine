# Gate summary

Raw rows: 16102. After dedupe: 15082.

| status | listings | buildings |
|---|---|---|
| fail | 2656 | 2243 |
| pass | 504 | 180 |
| pending | 11922 | 9191 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 15082 | 0 | 0 |
| rent | 15082 | 0 | 0 |
| movein | 2725 | 244 | 12113 |
| dog | 5790 | 175 | 9117 |
| elevator | 3175 | 1269 | 10638 |
| floor | 4074 | 1251 | 9757 |
| place | 15057 | 0 | 25 |
| proof | 3349 | 0 | 11733 |

## By source

| source_site                          |   fail |   pass |   pending |
|:-------------------------------------|-------:|-------:|----------:|
| anninlofts.com                       |      0 |      0 |         1 |
| apartmentlist.com                    |    422 |    363 |       684 |
| avaloncommunities.com                |     86 |     49 |        41 |
| bltliveworkplay.com (SightMap embed) |     28 |      2 |        47 |
| fairfieldproperties.com              |      3 |      0 |       309 |
| gardencommunities.com                |      8 |      2 |       116 |
| gardenhomesmanagement.com            |      4 |      0 |        16 |
| gdcrentals.com                       |      2 |      0 |        13 |
| greystar.com                         |     99 |     27 |       233 |
| newportrentals.com                   |      3 |      0 |         2 |
| solvermella.com                      |      2 |      0 |         3 |
| trulia                               |   1660 |     12 |      7444 |
| vermellacrossing.com                 |      1 |      0 |        12 |
| vermellaharrison.com                 |      8 |      0 |         2 |
| vermellalyndhurst.com                |      1 |      1 |         0 |
| vermellawest.com                     |      1 |      0 |         0 |
| vermellawoodbridge.com               |      1 |      0 |         3 |
| www.shoregateli.com (SightMap embed) |      0 |      0 |         2 |
| www.vermellaeast.com                 |      1 |      0 |         0 |
| zumper                               |    326 |     48 |      2994 |

## Pending reasons (what would need confirming)

| pending_reasons           |   count |
|:--------------------------|--------:|
| movein;dog;elevator;proof |    5050 |
| movein;elevator;proof     |    2875 |
| movein;proof              |     843 |
| movein;dog;proof          |     762 |
| dog                       |     458 |
| movein;dog;elevator       |     443 |
| dog;elevator              |     422 |
| dog;elevator;proof        |     249 |
| elevator;proof            |     242 |
| elevator                  |     228 |
| movein;dog                |     135 |
| movein                    |      73 |
| movein;elevator           |      61 |
| proof                     |      37 |
| dog;proof                 |      24 |

## Passing listings by state and city (top 40)

|                                      |   0 |
|:-------------------------------------|----:|
| ('NJ', 'Jersey City')                | 184 |
| ('NY', 'New Rochelle')               |  47 |
| ('NY', 'New York')                   |  44 |
| ('NJ', 'West Windsor')               |  39 |
| ('NJ', 'Hackensack')                 |  30 |
| ('NJ', 'West New York')              |  16 |
| ('NY', 'Yonkers')                    |  15 |
| ('NJ', 'Bogota')                     |  15 |
| ('NJ', 'Englewood')                  |  14 |
| ('NY', 'White Plains')               |  13 |
| ('NY', 'Jamaica')                    |  12 |
| ('NJ', 'Fort Lee')                   |   9 |
| ('NJ', 'Secaucus')                   |   8 |
| ('NJ', 'Cliffside Park')             |   8 |
| ('NJ', 'Bergenfield')                |   7 |
| ('NY', 'Brooklyn')                   |   4 |
| ('NY', 'New York City')              |   4 |
| ('NJ', 'Cranford')                   |   4 |
| ('NY', 'Westbury')                   |   3 |
| ('NJ', 'New Brunswick')              |   3 |
| ('NJ', 'Boonton')                    |   2 |
| ('CT', 'Stamford')                   |   2 |
| ('NY', 'Queens')                     |   2 |
| ('NY', 'Bronx')                      |   2 |
| ('NJ', 'Old Bridge')                 |   2 |
| ('NJ', 'East Rutherford')            |   2 |
| ('NJ', 'Edgewater')                  |   2 |
| ('NJ', 'Union')                      |   2 |
| ('NY', 'Hempstead')                  |   2 |
| ('NJ', 'Wayne')                      |   1 |
| ('NJ', 'Princeton')                  |   1 |
| ('NJ', 'Union City')                 |   1 |
| ('NY', 'Long Beach')                 |   1 |
| ('NJ', 'Wy Lyndhurst')               |   1 |
| ('NJ', 'Wharton, Rockaway Township') |   1 |
| ('NY', 'Valley Stream')              |   1 |
