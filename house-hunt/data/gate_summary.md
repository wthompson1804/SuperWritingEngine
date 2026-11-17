# Gate summary

Raw rows: 24748. After dedupe: 21095.

| status | listings | buildings |
|---|---|---|
| fail | 12404 | 6929 |
| pass | 1179 | 680 |
| pending | 7512 | 6129 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 20872 | 223 | 0 |
| rent | 10743 | 10182 | 170 |
| movein | 7987 | 961 | 12147 |
| dog | 10655 | 1593 | 8847 |
| floor_elevator | 17579 | 1703 | 1813 |
| place | 21065 | 0 | 30 |
| proof | 12569 | 7 | 8519 |
| elevator | 5441 | 876 | 14778 |
| floor | 5722 | 1374 | 13999 |

## Floor and elevator (owner, 2026-11-17)

| result | listings |
|---|---|
| pass floor_or_elevator | 11214 |
| pass - | 4634 |
| unknown - | 1813 |
| fail ground_floor | 1374 |
| pass floor_2 | 1198 |
| pass elevator | 533 |
| fail no_elevator_above_floor_2 | 191 |
| fail one_storey_building | 138 |

## By source

| source_site                               |   fail |   pass |   pending |
|:------------------------------------------|-------:|-------:|----------:|
| 18dock.com (SightMap embed)               |      1 |      0 |         0 |
| 1eastmainstreet.com                       |      1 |      0 |         0 |
| 360huguenot.com                           |      5 |      0 |         0 |
| anninlofts.com                            |      1 |      0 |         0 |
| apartmentlist.com                         |   3295 |    509 |       998 |
| arrivestamford.com                        |      1 |      0 |         0 |
| avaloncommunities.com                     |    169 |      5 |         2 |
| bltliveworkplay.com (SightMap embed)      |     69 |      3 |         5 |
| bottiniproperties.com                     |      1 |      0 |         1 |
| bygomes.com                               |      4 |      0 |         0 |
| continuumwhiteplains.com                  |     13 |      0 |         0 |
| eastdalevillage.com                       |      1 |      0 |         0 |
| fairfieldproperties.com                   |    228 |      0 |        24 |
| gardencommunities.com                     |     67 |      0 |        59 |
| gardenhomesmanagement.com                 |      1 |      0 |         8 |
| gdcrentals.com                            |     15 |      0 |         0 |
| greystar.com                              |    225 |      0 |         3 |
| livecarraway.com                          |      4 |      0 |         0 |
| livemotifapts.com                         |      8 |      0 |         0 |
| livethemitchell.com                       |      2 |      0 |         0 |
| morganparc.com                            |      1 |      0 |         0 |
| newportrentals.com                        |      5 |      0 |         0 |
| none                                      |      7 |      0 |         0 |
| one.clintonpark.com                       |      7 |      0 |         0 |
| onewebbave.com                            |     18 |      0 |         0 |
| openigloo                                 |     20 |      0 |         7 |
| paredimcommunities.com                    |      3 |      0 |         0 |
| sawyerplaceny.com                         |      3 |      0 |         0 |
| scenicbeaconproperties.com                |      2 |      0 |         1 |
| scribenorwalk.com (SightMap embed)        |     25 |      0 |         0 |
| solvermella.com                           |      5 |      0 |         0 |
| soundviewlanding.com                      |      1 |      0 |         0 |
| thebarnumhouse.com                        |      1 |      0 |         0 |
| thebrookport.com                          |      1 |      0 |         0 |
| thedanforthapts.com                       |      4 |      0 |         0 |
| thehalden.com                             |      3 |      0 |         0 |
| theleafnewrochelle.com                    |      9 |      0 |         0 |
| thesheldonatsuffern.com                   |      1 |      0 |         0 |
| theshipyardriverhead.com                  |      1 |      0 |         0 |
| trademarkfairfield.com                    |      1 |      0 |         0 |
| trulia                                    |   5472 |    453 |      4964 |
| trulia.com                                |     16 |      0 |         0 |
| vermellacrossing.com                      |     13 |      0 |         0 |
| vermellaharrison.com                      |      9 |      1 |         0 |
| vermellalyndhurst.com                     |      2 |      0 |         0 |
| vermellawest.com                          |      1 |      0 |         0 |
| vermellawoodbridge.com                    |      4 |      0 |         0 |
| villageplaceatgoshen.com                  |      1 |      0 |         0 |
| wallstreetplace.com                       |      1 |      0 |         0 |
| www.101parkplace.com                      |      1 |      0 |         0 |
| www.apartmentlist.com                     |     33 |      0 |         0 |
| www.eastsidecommons.com                   |      1 |      0 |         0 |
| www.infinityharborpoint.com               |      3 |      0 |         0 |
| www.merrittriver.com                      |      1 |      0 |         0 |
| www.metrostarproperties.com               |      7 |      0 |         0 |
| www.shoregateli.com (SightMap embed)      |      2 |      0 |         0 |
| www.theasherstamford.com (SightMap embed) |     16 |      0 |         0 |
| www.thebeaconnorwalk.com (SightMap embed) |     15 |      0 |         0 |
| www.thelafayettestamford.com              |      1 |      0 |         0 |
| www.thewescottapts.com                    |      1 |      0 |         0 |
| www.trulia.com                            |     70 |      0 |         0 |
| www.vermellaeast.com                      |      1 |      0 |         0 |
| www.zumper.com                            |      2 |      0 |         0 |
| zillow.com                                |     35 |     21 |         8 |
| zumper                                    |   2457 |    187 |      1429 |
| zumper.com                                |     10 |      0 |         3 |

## Pending reasons (what would need confirming)

| pending_reasons                 |   count |
|:--------------------------------|--------:|
| movein;dog;proof                |    2941 |
| movein;proof                    |    1515 |
| dog                             |    1131 |
| movein;dog                      |     760 |
| movein                          |     443 |
| movein;dog;floor_elevator;proof |     201 |
| movein;floor_elevator;proof     |     163 |
| floor_elevator                  |     140 |
| movein;dog;floor_elevator       |      76 |
| dog;floor_elevator              |      57 |
| movein;floor_elevator           |      42 |
| proof                           |      19 |
| dog;proof                       |      11 |
| floor_elevator;proof            |       8 |
| dog;place                       |       3 |

## Passing listings by state and city (top 40)

|                             |   0 |
|:----------------------------|----:|
| ('CT', 'New Haven')         | 192 |
| ('NJ', 'Newark')            |  61 |
| ('NJ', 'Jersey City')       |  41 |
| ('CT', 'Bridgeport')        |  41 |
| ('NJ', 'Paterson')          |  41 |
| ('NY', 'New York')          |  38 |
| ('CT', 'Hamden')            |  37 |
| ('CT', 'Stamford')          |  27 |
| ('NJ', 'New Brunswick')     |  27 |
| ('CT', 'East Haven')        |  25 |
| ('NJ', 'Plainsboro Center') |  22 |
| ('CT', 'Norwalk')           |  22 |
| ('NJ', 'Bayonne')           |  21 |
| ('NY', 'Bronx')             |  17 |
| ('CT', 'West Haven')        |  17 |
| ('NJ', 'Somerset')          |  16 |
| ('NJ', 'Trenton')           |  15 |
| ('NJ', 'Woodbridge')        |  15 |
| ('NJ', 'Lawrenceville')     |  14 |
| ('NY', 'Newburgh')          |  13 |
| ('NJ', 'Belleville')        |  12 |
| ('CT', 'Danbury')           |  12 |
| ('CT', 'Stratford')         |  11 |
| ('NY', 'Brooklyn')          |  11 |
| ('NY', 'Yonkers')           |  10 |
| ('NJ', 'Princeton Meadows') |  10 |
| ('NY', 'Middletown')        |  10 |
| ('CT', 'Milford')           |  10 |
| ('NJ', 'Piscataway')        |   9 |
| ('NY', 'Jamaica')           |   9 |
| ('NJ', 'Long Branch')       |   9 |
| ('NJ', 'Burlington')        |   8 |
| ('NY', 'Flushing')          |   8 |
| ('NJ', 'Bloomfield')        |   8 |
| ('CT', 'Beacon Falls')      |   8 |
| ('NJ', 'West New York')     |   8 |
| ('NJ', 'Irvington')         |   7 |
| ('NJ', 'Orange')            |   7 |
| ('NJ', 'Phillipsburg')      |   7 |
| ('CT', 'Naugatuck')         |   7 |
