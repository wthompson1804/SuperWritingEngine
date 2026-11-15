# Gate summary

Raw rows: 17628. After dedupe: 16462.

| status | listings | buildings |
|---|---|---|
| fail | 3189 | 2627 |
| pass | 879 | 337 |
| pending | 12394 | 9349 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 16462 | 0 | 0 |
| rent | 16462 | 0 | 0 |
| movein | 3640 | 352 | 12470 |
| dog | 6869 | 482 | 9111 |
| elevator | 3723 | 1292 | 11447 |
| floor | 4677 | 1392 | 10393 |
| place | 16435 | 0 | 27 |
| proof | 5036 | 0 | 11426 |

## By source

| source_site                          |   fail |   pass |   pending |
|:-------------------------------------|-------:|-------:|----------:|
| anninlofts.com                       |      0 |      0 |         1 |
| apartmentlist.com                    |    633 |    569 |      1087 |
| avaloncommunities.com                |     86 |     49 |        41 |
| bltliveworkplay.com (SightMap embed) |     28 |     23 |        26 |
| fairfieldproperties.com              |     57 |      0 |       253 |
| gardencommunities.com                |      8 |      2 |       116 |
| gardenhomesmanagement.com            |      4 |      0 |        16 |
| gdcrentals.com                       |      2 |      0 |        13 |
| greystar.com                         |     98 |     55 |       196 |
| newportrentals.com                   |      3 |      0 |         2 |
| solvermella.com                      |      2 |      0 |         3 |
| trulia                               |   1855 |    108 |      7575 |
| vermellacrossing.com                 |      1 |      0 |        12 |
| vermellaharrison.com                 |      8 |      0 |         2 |
| vermellalyndhurst.com                |      1 |      1 |         0 |
| vermellawest.com                     |      1 |      0 |         0 |
| vermellawoodbridge.com               |      1 |      0 |         3 |
| www.shoregateli.com (SightMap embed) |      0 |      0 |         2 |
| www.vermellaeast.com                 |      1 |      0 |         0 |
| zumper                               |    400 |     72 |      3046 |

## Pending reasons (what would need confirming)

| pending_reasons           |   count |
|:--------------------------|--------:|
| movein;dog;elevator;proof |    5132 |
| movein;elevator;proof     |    3032 |
| movein;proof              |     624 |
| dog                       |     537 |
| dog;elevator              |     519 |
| movein;dog;proof          |     469 |
| elevator                  |     428 |
| movein;dog;elevator       |     362 |
| movein                    |     308 |
| dog;elevator;proof        |     244 |
| movein;dog                |     242 |
| elevator;proof            |     238 |
| movein;elevator           |     233 |
| dog;elevator;place        |      18 |
| dog;proof                 |       3 |

## Passing listings by state and city (top 40)

|                           |   0 |
|:--------------------------|----:|
| ('NJ', 'Jersey City')     | 206 |
| ('NY', 'New York')        |  55 |
| ('NY', 'New Rochelle')    |  48 |
| ('NJ', 'Bayonne')         |  46 |
| ('NJ', 'Harrison')        |  42 |
| ('NJ', 'West Windsor')    |  39 |
| ('NJ', 'Newark')          |  38 |
| ('NY', 'White Plains')    |  36 |
| ('NY', 'Brooklyn')        |  33 |
| ('NJ', 'Hackensack')      |  32 |
| ('NJ', 'Clifton')         |  22 |
| ('NY', 'Jamaica')         |  20 |
| ('NJ', 'Parisppany')      |  17 |
| ('NJ', 'West New York')   |  17 |
| ('NJ', 'Bogota')          |  16 |
| ('NY', 'Yonkers')         |  16 |
| ('NY', 'Flushing')        |  14 |
| ('NJ', 'Englewood')       |  14 |
| ('NJ', 'Bloomfield')      |  12 |
| ('NY', 'Bronx')           |  12 |
| ('NJ', 'New Brunswick')   |  11 |
| ('NJ', 'Fort Lee')        |   9 |
| ('NJ', 'East Orange')     |   8 |
| ('NJ', 'Secaucus')        |   8 |
| ('NJ', 'Cliffside Park')  |   8 |
| ('NJ', 'Bergenfield')     |   7 |
| ('NJ', 'Upper Montclair') |   6 |
| ('NY', 'Harrison')        |   6 |
| ('CT', 'Westport')        |   5 |
| ('NY', 'Jackson Heights') |   5 |
| ('NJ', 'Cranford')        |   4 |
| ('NY', 'Astoria')         |   4 |
| ('NY', 'Queens')          |   4 |
| ('NY', 'New York City')   |   4 |
| ('NJ', 'Fords')           |   4 |
| ('NJ', 'Belleville')      |   3 |
| ('NY', 'Westbury')        |   3 |
| ('NJ', 'Hawthorne')       |   3 |
| ('CT', 'Stamford')        |   2 |
| ('NY', 'Hempstead')       |   2 |
