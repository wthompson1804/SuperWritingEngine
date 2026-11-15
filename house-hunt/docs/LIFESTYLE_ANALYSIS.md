# Lifestyle analysis (interim, 2026-11-15 evening)

Will rejected grouping by drive band and setting. Years must group neighborhoods by **lifestyle, not location**
("they rhyme"): no drive time, state or county in the features. Interim run on 103 neighborhoods with passing
units; to be rerun when the Long Island, Hudson Valley and Connecticut building-first agents finish.

Features (`scripts/lifestyle_features.py` → `data/lifestyle_features.csv`): ACS 2019-2023 tract data around each
passing building (density, age 25-34 share, living alone, renters, big-building share, detached-house share, year
built, no-car households, transit / walk commute, work-from-home share, income, moved-in-last-year share), OSM
counts (restaurants, bars, cafés, music venues, park area, park walk, water and beach distance, motorway distance),
police-agency crime rates, and square feet per $1,000 of all-in rent.

## What moves together (principal components; first four explain 63%)

1. **Car-free density vs house-and-car** (32%): no-car households, transit commuting, density and renting rise
   together and fall with detached houses. Violent-crime rate rises with it (r = +0.77 with no-car share).
2. **New arrivals vs settled** (13%): moved-in-last-year share, work-from-home share, age 25-34 share, newer
   buildings and income rise together.
3. **Street life** (10%): cafés, bars and restaurants move as one (r = 0.72 to 0.82).
4. **Water and youth vs older, parks, big buildings** (8%).

Composite indices built from these (`data/lifestyle_indices.csv`): car_free, new_arrivals, street_life, green,
water, calm, space_for_money. Ward clustering on the indices, k = 6 (silhouette 0.19-0.20 for k = 4 to 7: groups
overlap, as lifestyles do; raw 26-feature clustering scored 0.11-0.12).

## Interim groups (names not final; traits are medians)

| Group | Neighborhoods / units | Measured character | Examples |
|---|---|---|---|
| Busy old-city streets | 27 / 90 | 63% of households car-free; 34 restaurants and 5 bars within 800 m; buildings from about 1953 | Flushing, Jackson Heights, Jamaica, Kew Gardens, Astoria, Sunnyside |
| Big parks, rougher edges | 11 / 43 | 31 ha of park within 800 m; water 560 m; highest violent-crime rate (5.3 per 1,000); income $50k | Newark, Mott Haven, Hallets Point, Washington Heights |
| Quiet city blocks, more room | 19 / 43 | 8 restaurants, 1 bar; 323 sq ft per $1,000 (most space for the money); half of households have a car | Briarwood, Forest Hills, Elmhurst, East Flatbush-Farragut, Rego Park |
| New waterfront district | 11 / 227 | Buildings from about 1995; 21% moved in last year; 26% aged 25-34; water 140 m; income $114k | Jersey City, Harrison NJ, Hackensack, White Plains, Yonkers, Edgewater, Stamford |
| Car-and-calm suburb | 34 / 206 | 9% car-free; lowest violent crime (0.8 per 1,000); 4 restaurants, 0 bars within 800 m | Bayonne, New Rochelle, Bloomfield, Maplewood, Teaneck, Westport, Cranford |
| (single outlier) | 1 / 1 | Riverdale: one very large unit | |

Open: the suburb group is broad (main-street train towns vs highway-side complexes) and should split once more
neighborhoods are in; beach and river towns are not yet in the data.

## Second pass (2026-11-15 night): more colour variables

Will asked for the next tier of variables to be added "for colour": the aim is a data-informed picture of the kind
of life in each group, not maximum explained variance. Added (`scripts/lifestyle_color.py` → `data/lifestyle_color.csv`):
college-degree share, households with children, age 65+, hour-plus commutes, housing built since 2010 and before
1940, tract median rent, distances to supermarket, Trader Joe's, Target, vet, dog park and train station, breweries
and restaurants within 1.6 km, her unit's median size and all-in cost. New indices: new_build, families_and_elders,
degrees, errands_on_foot (11 indices in all, `data/lifestyle_indices.csv`, column `group` = 7-group Ward clustering).
Silhouette falls to 0.14 at k = 7 (more dimensions, more overlap); the groups are read as portraits, not hard classes.
A further OSM pass (gyms, bookshops, cinemas, markets, playgrounds, big-box, parking area, footpaths) is being added
to the places tool as `color()`.
