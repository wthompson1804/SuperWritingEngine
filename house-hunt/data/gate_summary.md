# Gate summary

Raw rows: 20721. After dedupe: 18290.

| status | listings | buildings |
|---|---|---|
| fail | 4192 | 3207 |
| pass | 1962 | 669 |
| pending | 12136 | 9002 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 18267 | 23 | 0 |
| rent | 18263 | 15 | 12 |
| movein | 5972 | 689 | 11629 |
| dog | 8547 | 970 | 8773 |
| elevator | 5035 | 1306 | 11949 |
| floor | 5944 | 1612 | 10734 |
| place | 18263 | 0 | 27 |
| proof | 8039 | 0 | 10251 |

## By source

| source_site                          |   fail |   pass |   pending |
|:-------------------------------------|-------:|-------:|----------:|
| anninlofts.com                       |      0 |      0 |         1 |
| apartmentlist.com                    |    990 |    976 |      1493 |
| avaloncommunities.com                |     86 |     49 |        41 |
| bltliveworkplay.com (SightMap embed) |     28 |     23 |        26 |
| bygomes.com                          |      4 |      0 |         0 |
| fairfieldproperties.com              |      8 |      0 |       291 |
| gardencommunities.com                |      8 |      2 |       116 |
| gardenhomesmanagement.com            |      4 |      0 |         8 |
| gdcrentals.com                       |      2 |      0 |        13 |
| greystar.com                         |     46 |     30 |       155 |
| livethemitchell.com                  |      1 |      1 |         0 |
| newportrentals.com                   |      3 |      0 |         2 |
| onewebbave.com                       |      0 |     18 |         0 |
| sawyerplaceny.com                    |      0 |      0 |         3 |
| scenicbeaconproperties.com           |      1 |      0 |         2 |
| solvermella.com                      |      2 |      0 |         3 |
| thehalden.com                        |      1 |      0 |         2 |
| trulia                               |   2570 |    775 |      6875 |
| trulia.com                           |      1 |      0 |         0 |
| vermellacrossing.com                 |      1 |      0 |        12 |
| vermellaharrison.com                 |      8 |      0 |         2 |
| vermellalyndhurst.com                |      1 |      1 |         0 |
| vermellawest.com                     |      1 |      0 |         0 |
| vermellawoodbridge.com               |      1 |      0 |         3 |
| www.vermellaeast.com                 |      1 |      0 |         0 |
| zillow.com                           |     23 |     15 |        30 |
| zumper                               |    398 |     72 |      3051 |
| zumper.com                           |      3 |      0 |         7 |

## Pending reasons (what would need confirming)

| pending_reasons           |   count |
|:--------------------------|--------:|
| movein;dog;elevator;proof |    4844 |
| movein;elevator;proof     |    2618 |
| elevator                  |     931 |
| dog;elevator              |     691 |
| dog                       |     544 |
| movein                    |     399 |
| movein;proof              |     391 |
| movein;dog;elevator       |     361 |
| movein;elevator           |     357 |
| movein;dog                |     251 |
| dog;elevator;proof        |     244 |
| movein;dog;proof          |     239 |
| elevator;proof            |     238 |
| dog;elevator;place        |      18 |
| dog;proof                 |       3 |

## Passing listings by state and city (top 40)

|                                 |   0 |
|:--------------------------------|----:|
| ('NJ', 'Jersey City')           | 293 |
| ('CT', 'Stamford')              | 104 |
| ('NJ', 'Parsippany-Troy Hills') |  98 |
| ('CT', 'New Haven')             |  92 |
| ('NY', 'New Rochelle')          |  82 |
| ('NY', 'New York')              |  80 |
| ('NJ', 'Newark')                |  71 |
| ('NY', 'Yonkers')               |  63 |
| ('NY', 'White Plains')          |  60 |
| ('NY', 'Brooklyn')              |  56 |
| ('CT', 'Norwalk')               |  54 |
| ('NJ', 'Bayonne')               |  53 |
| ('NJ', 'Harrison')              |  42 |
| ('NJ', 'Dover')                 |  41 |
| ('NJ', 'West Windsor')          |  39 |
| ('NJ', 'Hackensack')            |  37 |
| ('NJ', 'New Brunswick')         |  32 |
| ('NJ', 'Bogota')                |  31 |
| ('NY', 'Bronx')                 |  29 |
| ('NJ', 'Clifton')               |  22 |
| ('NJ', 'West New York')         |  21 |
| ('NY', 'Jamaica')               |  21 |
| ('NJ', 'East Orange')           |  20 |
| ('NY', 'Purchase')              |  18 |
| ('NJ', 'Bloomfield')            |  16 |
| ('NJ', 'Englewood')             |  14 |
| ('NY', 'Flushing')              |  14 |
| ('NJ', 'Plainsboro')            |  14 |
| ('CT', 'Trumbull')              |  12 |
| ('NY', 'Peekskill')             |  12 |
| ('NJ', 'Orange')                |  12 |
| ('NJ', 'Livingston')            |  11 |
| ('NJ', 'Belleville')            |  11 |
| ('NY', 'Port Chester')          |  11 |
| ('NY', 'Middletown')            |  11 |
| ('NJ', 'North Bergen')          |  10 |
| ('NY', 'Haverstraw')            |  10 |
| ('NJ', 'Fort Lee')              |  10 |
| ('CT', 'Danbury')               |   9 |
| ('CT', 'Milford city')          |   9 |
