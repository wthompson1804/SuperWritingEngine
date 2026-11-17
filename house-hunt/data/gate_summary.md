# Gate summary

Raw rows: 24311. After dedupe: 20468.

| status | listings | buildings |
|---|---|---|
| fail | 11569 | 6247 |
| pass | 1026 | 537 |
| pending | 7873 | 6389 |

## Each gate (after dedupe)

| gate | pass | fail | unknown |
|---|---|---|---|
| type | 20245 | 223 | 0 |
| rent | 10270 | 10028 | 170 |
| movein | 7841 | 932 | 11695 |
| dog | 10297 | 1171 | 9000 |
| floor_elevator | 17164 | 1335 | 1969 |
| place | 20438 | 0 | 30 |
| proof | 10376 | 7 | 10085 |
| elevator | 5327 | 845 | 14296 |
| floor | 5462 | 1163 | 13843 |

## Floor and elevator (owner, 2026-11-17)

| result | listings |
|---|---|
| pass floor_or_elevator | 11065 |
| pass - | 4540 |
| unknown - | 1969 |
| fail ground_floor | 1163 |
| pass floor_2 | 1027 |
| pass elevator | 532 |
| fail no_elevator_above_floor_2 | 172 |

## By source

| source_site                               |   fail |   pass |   pending |
|:------------------------------------------|-------:|-------:|----------:|
| 18dock.com (SightMap embed)               |      1 |      0 |         0 |
| 1eastmainstreet.com                       |      1 |      0 |         0 |
| 360huguenot.com                           |      5 |      0 |         0 |
| anninlofts.com                            |      1 |      0 |         0 |
| apartmentlist.com                         |   3311 |    509 |      1013 |
| arrivestamford.com                        |      1 |      0 |         0 |
| avaloncommunities.com                     |    169 |      5 |         2 |
| bltliveworkplay.com (SightMap embed)      |     69 |      3 |         5 |
| bottiniproperties.com                     |      1 |      0 |         1 |
| bygomes.com                               |      4 |      0 |         0 |
| continuumwhiteplains.com                  |     13 |      0 |         0 |
| eastdalevillage.com                       |      1 |      0 |         0 |
| fairfieldproperties.com                   |    228 |      0 |        24 |
| gardencommunities.com                     |     65 |      0 |        61 |
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
| trulia                                    |   5382 |    442 |      4904 |
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
| zumper                                    |   1718 |     45 |      1840 |
| zumper.com                                |     10 |      0 |         3 |

## Pending reasons (what would need confirming)

| pending_reasons                 |   count |
|:--------------------------------|--------:|
| movein;dog;proof                |    3690 |
| movein;proof                    |    1639 |
| dog                             |    1002 |
| movein;dog;floor_elevator;proof |     304 |
| movein;dog                      |     212 |
| movein;floor_elevator;proof     |     202 |
| dog;proof                       |     185 |
| movein                          |     178 |
| proof                           |     145 |
| floor_elevator                  |     120 |
| dog;floor_elevator              |      59 |
| movein;floor_elevator           |      52 |
| floor_elevator;proof            |      46 |
| movein;dog;floor_elevator       |      17 |
| dog;floor_elevator;proof        |      17 |

## Passing listings by state and city (top 40)

|                             |   0 |
|:----------------------------|----:|
| ('CT', 'New Haven')         | 186 |
| ('CT', 'Bridgeport')        |  38 |
| ('NY', 'New York')          |  35 |
| ('CT', 'Hamden')            |  34 |
| ('NJ', 'Newark')            |  33 |
| ('NJ', 'Paterson')          |  26 |
| ('CT', 'East Haven')        |  24 |
| ('NJ', 'Jersey City')       |  23 |
| ('CT', 'Stamford')          |  23 |
| ('NJ', 'New Brunswick')     |  21 |
| ('NJ', 'Plainsboro Center') |  21 |
| ('CT', 'Norwalk')           |  19 |
| ('NY', 'Bronx')             |  17 |
| ('CT', 'West Haven')        |  17 |
| ('NJ', 'Somerset')          |  16 |
| ('NJ', 'Woodbridge')        |  16 |
| ('NJ', 'Lawrenceville')     |  14 |
| ('CT', 'Danbury')           |  13 |
| ('NJ', 'Belleville')        |  12 |
| ('CT', 'Stratford')         |  11 |
| ('NY', 'Brooklyn')          |  11 |
| ('NJ', 'Princeton Meadows') |  10 |
| ('NY', 'Middletown')        |  10 |
| ('NJ', 'Somerville')        |  10 |
| ('NY', 'Yonkers')           |  10 |
| ('CT', 'Milford')           |  10 |
| ('NJ', 'Bayonne')           |   9 |
| ('NJ', 'Long Branch')       |   9 |
| ('NY', 'Jamaica')           |   9 |
| ('NJ', 'Piscataway')        |   9 |
| ('CT', 'Beacon Falls')      |   8 |
| ('NY', 'Flushing')          |   8 |
| ('NY', 'Newburgh')          |   8 |
| ('NJ', 'Edison')            |   8 |
| ('NJ', 'Burlington')        |   8 |
| ('NJ', 'Trenton')           |   8 |
| ('NJ', 'Bloomfield')        |   7 |
| ('NJ', 'Phillipsburg')      |   7 |
| ('NJ', 'Orange')            |   7 |
| ('NJ', 'Budd Lake')         |   6 |
