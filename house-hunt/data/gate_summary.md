# Gate summary

Raw rows: 18121. After dedupe: 16827.

| status | listings | buildings |
|---|---|---|
| fail | 3377 | 2753 |
| pass | 1091 | 416 |
| pending | 12359 | 9258 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 16827 | 0 | 0 |
| rent | 16827 | 0 | 0 |
| movein | 4124 | 406 | 12297 |
| dog | 7145 | 584 | 9098 |
| elevator | 3924 | 1293 | 11610 |
| floor | 4930 | 1444 | 10453 |
| place | 16800 | 0 | 27 |
| proof | 5628 | 0 | 11199 |

## By source

| source_site                          |   fail |   pass |   pending |
|:-------------------------------------|-------:|-------:|----------:|
| anninlofts.com                       |      0 |      0 |         1 |
| apartmentlist.com                    |    743 |    717 |      1236 |
| avaloncommunities.com                |     86 |     49 |        41 |
| bltliveworkplay.com (SightMap embed) |     28 |     23 |        26 |
| fairfieldproperties.com              |     57 |      0 |       253 |
| gardencommunities.com                |      8 |      2 |       116 |
| gardenhomesmanagement.com            |      4 |      0 |        16 |
| gdcrentals.com                       |      2 |      0 |        13 |
| greystar.com                         |     92 |     45 |       196 |
| newportrentals.com                   |      3 |      0 |         2 |
| solvermella.com                      |      2 |      0 |         3 |
| trulia                               |   1939 |    182 |      7391 |
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
| movein;dog;elevator;proof |    5108 |
| movein;elevator;proof     |    3012 |
| dog;elevator              |     573 |
| dog                       |     572 |
| movein;proof              |     538 |
| elevator                  |     501 |
| movein;dog;proof          |     378 |
| movein;dog;elevator       |     362 |
| movein                    |     327 |
| movein;dog                |     246 |
| dog;elevator;proof        |     244 |
| elevator;proof            |     238 |
| movein;elevator           |     234 |
| dog;elevator;place        |      18 |
| dog;proof                 |       3 |

## Passing listings by state and city (top 40)

|                                 |   0 |
|:--------------------------------|----:|
| ('NJ', 'Jersey City')           | 206 |
| ('NJ', 'Parsippany-Troy Hills') |  98 |
| ('NY', 'New York')              |  80 |
| ('NY', 'New Rochelle')          |  58 |
| ('NY', 'Brooklyn')              |  54 |
| ('NJ', 'Bayonne')               |  46 |
| ('NJ', 'Harrison')              |  42 |
| ('NJ', 'West Windsor')          |  39 |
| ('NJ', 'Newark')                |  38 |
| ('NY', 'White Plains')          |  36 |
| ('NJ', 'Hackensack')            |  32 |
| ('NY', 'Bronx')                 |  25 |
| ('NJ', 'Clifton')               |  22 |
| ('NY', 'Jamaica')               |  20 |
| ('NJ', 'West New York')         |  17 |
| ('NJ', 'Bogota')                |  16 |
| ('NY', 'Yonkers')               |  16 |
| ('NY', 'Flushing')              |  14 |
| ('NJ', 'Englewood')             |  14 |
| ('NJ', 'Bloomfield')            |  12 |
| ('NJ', 'New Brunswick')         |  11 |
| ('NJ', 'Livingston')            |  11 |
| ('NJ', 'Fort Lee')              |  10 |
| ('NJ', 'Orange')                |   9 |
| ('NJ', 'North Bergen')          |   8 |
| ('NJ', 'Secaucus')              |   8 |
| ('NJ', 'East Orange')           |   8 |
| ('NJ', 'Cliffside Park')        |   8 |
| ('NJ', 'Parisppany')            |   7 |
| ('NJ', 'Bergenfield')           |   7 |
| ('NJ', 'Upper Montclair')       |   6 |
| ('NJ', 'Piscataway')            |   6 |
| ('NY', 'Harrison')              |   6 |
| ('CT', 'Westport')              |   5 |
| ('NY', 'Jackson Heights')       |   5 |
| ('NJ', 'Montclair')             |   5 |
| ('NY', 'Astoria')               |   4 |
| ('NY', 'New York City')         |   4 |
| ('NJ', 'North Haledon')         |   4 |
| ('NY', 'Queens')                |   4 |
