# Gate summary

Raw rows: 24311. After dedupe: 20468.

| status | listings | buildings |
|---|---|---|
| fail | 3944 | 2975 |
| pass | 2505 | 608 |
| pending | 14019 | 9711 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 20245 | 223 | 0 |
| rent | 20243 | 55 | 170 |
| movein | 7841 | 932 | 11695 |
| dog | 10298 | 1171 | 8999 |
| elevator | 5328 | 845 | 14295 |
| floor | 5461 | 1163 | 13844 |
| place | 20438 | 0 | 30 |
| proof | 10376 | 7 | 10085 |

## By source

| source_site                               |   fail |   pass |   pending |
|:------------------------------------------|-------:|-------:|----------:|
| 18dock.com (SightMap embed)               |      0 |      1 |         0 |
| 1eastmainstreet.com                       |      1 |      0 |         0 |
| 360huguenot.com                           |      1 |      4 |         0 |
| anninlofts.com                            |      0 |      0 |         1 |
| apartmentlist.com                         |   1089 |   1309 |      2435 |
| arrivestamford.com                        |      1 |      0 |         0 |
| avaloncommunities.com                     |     86 |      4 |        86 |
| bltliveworkplay.com (SightMap embed)      |     28 |     23 |        26 |
| bottiniproperties.com                     |      0 |      0 |         2 |
| bygomes.com                               |      4 |      0 |         0 |
| continuumwhiteplains.com                  |      3 |     10 |         0 |
| eastdalevillage.com                       |      1 |      0 |         0 |
| fairfieldproperties.com                   |     11 |      0 |       241 |
| gardencommunities.com                     |      9 |      2 |       115 |
| gardenhomesmanagement.com                 |      1 |      0 |         8 |
| gdcrentals.com                            |      2 |      0 |        13 |
| greystar.com                              |     49 |     84 |        95 |
| livecarraway.com                          |      0 |      4 |         0 |
| livemotifapts.com                         |      1 |      7 |         0 |
| livethemitchell.com                       |      1 |      1 |         0 |
| morganparc.com                            |      1 |      0 |         0 |
| newportrentals.com                        |      3 |      0 |         2 |
| none                                      |      7 |      0 |         0 |
| one.clintonpark.com                       |      3 |      4 |         0 |
| onewebbave.com                            |      0 |     18 |         0 |
| paredimcommunities.com                    |      3 |      0 |         0 |
| sawyerplaceny.com                         |      0 |      3 |         0 |
| scenicbeaconproperties.com                |      1 |      0 |         2 |
| scribenorwalk.com (SightMap embed)        |      0 |     25 |         0 |
| solvermella.com                           |      2 |      0 |         3 |
| soundviewlanding.com                      |      1 |      0 |         0 |
| thebarnumhouse.com                        |      1 |      0 |         0 |
| thebrookport.com                          |      1 |      0 |         0 |
| thedanforthapts.com                       |      0 |      0 |         4 |
| thehalden.com                             |      1 |      0 |         2 |
| theleafnewrochelle.com                    |      0 |      9 |         0 |
| thesheldonatsuffern.com                   |      1 |      0 |         0 |
| theshipyardriverhead.com                  |      1 |      0 |         0 |
| trademarkfairfield.com                    |      1 |      0 |         0 |
| trulia                                    |   2027 |    896 |      7805 |
| trulia.com                                |     16 |      0 |         0 |
| vermellacrossing.com                      |      1 |      0 |        12 |
| vermellaharrison.com                      |      7 |      3 |         0 |
| vermellalyndhurst.com                     |      1 |      0 |         1 |
| vermellawest.com                          |      1 |      0 |         0 |
| vermellawoodbridge.com                    |      1 |      0 |         3 |
| villageplaceatgoshen.com                  |      1 |      0 |         0 |
| wallstreetplace.com                       |      1 |      0 |         0 |
| www.101parkplace.com                      |      0 |      0 |         1 |
| www.apartmentlist.com                     |     33 |      0 |         0 |
| www.eastsidecommons.com                   |      1 |      0 |         0 |
| www.infinityharborpoint.com               |      0 |      0 |         3 |
| www.merrittriver.com                      |      0 |      0 |         1 |
| www.metrostarproperties.com               |      7 |      0 |         0 |
| www.shoregateli.com (SightMap embed)      |      0 |      2 |         0 |
| www.theasherstamford.com (SightMap embed) |      1 |     15 |         0 |
| www.thebeaconnorwalk.com (SightMap embed) |      5 |      0 |        10 |
| www.thelafayettestamford.com              |      1 |      0 |         0 |
| www.thewescottapts.com                    |      0 |      0 |         1 |
| www.trulia.com                            |     70 |      0 |         0 |
| www.vermellaeast.com                      |      1 |      0 |         0 |
| www.zumper.com                            |      2 |      0 |         0 |
| zillow.com                                |     22 |     12 |        30 |
| zumper                                    |    426 |     69 |      3108 |
| zumper.com                                |      4 |      0 |         9 |

## Pending reasons (what would need confirming)

| pending_reasons           |   count |
|:--------------------------|--------:|
| movein;dog;elevator;proof |    5230 |
| movein;elevator;proof     |    2687 |
| elevator                  |    1993 |
| dog;elevator              |    1108 |
| dog                       |     477 |
| movein;proof              |     438 |
| movein;dog;elevator       |     419 |
| movein                    |     404 |
| movein;elevator           |     401 |
| dog;elevator;proof        |     235 |
| movein;dog                |     232 |
| elevator;proof            |     227 |
| movein;dog;proof          |     138 |
| dog;elevator;place        |      21 |
| dog;proof                 |       3 |

## Passing listings by state and city (top 40)

|                                 |   0 |
|:--------------------------------|----:|
| ('NJ', 'Jersey City')           | 334 |
| ('CT', 'New Haven')             | 303 |
| ('CT', 'Stamford')              | 161 |
| ('CT', 'Bridgeport')            | 108 |
| ('NJ', 'Parsippany-Troy Hills') | 107 |
| ('CT', 'Norwalk')               |  96 |
| ('NY', 'New Rochelle')          |  85 |
| ('NY', 'New York')              |  75 |
| ('NY', 'Yonkers')               |  68 |
| ('NJ', 'Bayonne')               |  64 |
| ('NY', 'Port Chester')          |  59 |
| ('NY', 'White Plains')          |  58 |
| ('NJ', 'Newark')                |  57 |
| ('NJ', 'Berkeley Heights')      |  54 |
| ('NY', 'Brooklyn')              |  51 |
| ('NJ', 'Harrison')              |  42 |
| ('NJ', 'Dover')                 |  41 |
| ('NJ', 'Hackensack')            |  41 |
| ('NJ', 'Bogota')                |  31 |
| ('NY', 'Bronx')                 |  29 |
| ('CT', 'Danbury')               |  23 |
| ('NJ', 'New Brunswick')         |  23 |
| ('NJ', 'Burlington')            |  22 |
| ('NJ', 'Clifton')               |  22 |
| ('NY', 'Jamaica')               |  21 |
| ('CT', 'Trumbull')              |  19 |
| ('NJ', 'East Orange')           |  19 |
| ('NJ', 'Englewood')             |  19 |
| ('NJ', 'South River')           |  18 |
| ('NJ', 'Flemington')            |  18 |
| ('NY', 'Purchase')              |  18 |
| ('NJ', 'West New York')         |  17 |
| ('NJ', 'Somerset')              |  17 |
| ('NY', 'Peekskill')             |  16 |
| ('NY', 'Haverstraw')            |  16 |
| ('CT', 'Shelton')               |  14 |
| ('NY', 'Flushing')              |  14 |
| ('CT', 'Milford')               |  13 |
| ('NJ', 'Long Branch')           |  11 |
| ('NJ', 'Orange')                |  11 |
