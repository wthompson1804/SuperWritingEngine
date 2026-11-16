# Sub-city crime data for the split cities (prepared 2026-11-15/16, not wired in)

The safety rule (`scripts/lifestyle_groups.py` line 61) cuts a neighborhood whose violent rate is above 9.8 per 1,000
or whose property rate is above 25.0 (NYPD 103rd Precinct, Jamaica). Outside NYC those rates are for the whole police
agency: Jersey City 4.87 violent / 18.32 property (FBI CDE 2025, `data/reference/crime_agencies.csv`, ORI NJ0090600),
Newark 5.17 / 17.89. Both cities pass as a whole. This note says what exists below the city level.

## Summary

| City | Sub-city crime data we hold | Population denominator | Per-neighborhood comparison possible? |
|---|---|---|---|
| Jersey City | Yes: 4,858 block-geocoded JCPD incidents, 2025-12-28 to 2026-11-11 (319 days), citywide, with type and police district | Yes: ACS 2019-2023 tract population (B01003), cached | Yes, as a labelled estimate. Not as an official rate. |
| Newark | None. Open data portal returned 503; police and city sites answer robots.txt with 403 (`docs/harvest_notes/non_nyc_records.md`) | Available (ACS tracts, Essex County cached) but nothing to divide | No |
| Hoboken, Yonkers, Stamford, New Rochelle, White Plains (not split) | None found | n/a | No |

## Jersey City: what the incident file is

- Source: JC IMPACT crime data portal, `https://impact.jcnj.org/` (Jersey City Police Department, "JCPD CompStat").
  The incidents were read from the page's own JavaScript bundle by `scripts/non_nyc_records.py` (robots.txt allows the
  bundle; the disallowed `.json` / `.pdf` files were not fetched; use approved by Will). Cached at
  `raw/non_nyc_records/jc_impact_incidents_extracted.json`, retrieved 2026-11-15T21:20Z. **No new request was made for
  this note.**
- It is the whole city, not only points near candidate buildings. `data/evidence/non_nyc_records.csv` holds only the
  250 m counts around 17 buildings, but the cached bundle has every published incident.
- Every incident has a date, a type, a block-level address ("100 block of ..."), coordinates and a police district
  (North 877, East 1,297, South 1,264, West 1,420).
- Types: Theft 1,920; Aggravated Assault 759; Stolen Vehicle 625; Theft from Auto 450; Burglary 385; Shoplifting 307;
  Robbery 272; Rape 74; Shots Fired 28; Shooting Hit 25; Homicide 9; Fatal Crash 4.
- The portal calls the figures preliminary. It publishes nothing before 2025-12-28, so there is no second year.

## How it compares with the FBI figure the safety rule uses

Counting the four FBI violent types (homicide, rape, robbery, aggravated assault) and five property types (burglary,
theft, theft from auto, shoplifting, stolen vehicle), annualising by 365/319 and dividing by the ACS population of
all Jersey City tracts (289,691):

| | Portal, annualised | FBI CDE 2025 (agency) | Portal as a share of FBI |
|---|---|---|---|
| Violent per 1,000 | 4.40 | 4.87 | 90% |
| Property per 1,000 | 14.56 | 18.32 | 79% |

So the portal runs below the FBI count (different population base, preliminary data, and the portal's "Theft" types may
not cover every larceny the FBI counts). A raw portal rate must not be compared with the 9.8 / 25.0 thresholds. The
defensible use is **relative**: each neighborhood's portal rate divided by the citywide portal rate, then multiplied
by the FBI agency rate. That is what `data/reference/subcity_crime_jersey_city.csv` holds, every row marked
`value_type = estimate` with the method.

## What the estimate says (not applied anywhere)

Neighborhoods as defined in `data/reference/subcity_neighborhoods.geojson`; population = sum of the neighborhood's
tracts; incidents counted by point-in-polygon.

| Neighborhood | Residents (ACS) | Violent incidents | Property incidents | Violent, scaled to FBI | Property, scaled to FBI | Against 9.8 / 25.0 |
|---|---|---|---|---|---|---|
| Bergen-Lafayette | 42,679 | 311 | 613 | 9.25 | 20.70 | under, violent within 6% of the line |
| West Side | 34,203 | 168 | 571 | 6.23 | 24.00 | under, property within 4% of the line |
| Greenville | 48,437 | 191 | 500 | 5.02 | 14.84 | under |
| McGinley Square | 22,716 | 86 | 301 | 4.77 | 19.05 | under |
| Journal Square | 36,764 | 127 | 512 | 4.38 | 19.97 | under |
| Newport | 10,200 | 33 | 294 | 4.09 | 41.40 | **property over** |
| The Heights | 40,228 | 96 | 356 | 3.02 | 12.82 | under |
| Downtown | 54,464 | 102 | 540 | 2.39 | 14.29 | under |

## Why these numbers should not drive the safety cut on their own

1. **Resident denominators mislead where people shop and commute.** Newport has 10,200 residents and a regional mall:
   107 of its 294 property incidents are shoplifting. Its "41 per 1,000" is a retail-district figure, not a risk to a
   resident. NYPD precinct rates have the same weakness, but precincts are far larger than a three-tract neighborhood.
2. **Small areas, one partial year.** 319 days, preliminary. Bergen-Lafayette sits 6% under the violent line and West
   Side 4% under the property line; a second year or a boundary moved by one tract could put either across.
3. **Block geocoding.** Points sit at the "hundred block", so an incident on a boundary street can fall on either side.
   Twenty of the 38 Jersey City buildings are within 150 m of a boundary (`subcity_assignment.csv`).
4. **Unequal yardsticks.** NYC neighborhoods are judged on a full-year precinct rate from NYPD complaints; the rest of
   the region on a whole-agency FBI rate. A scaled 10-month estimate for eight Jersey City areas would be a third
   method. Rule 8 (keep sources separate) argues for showing it beside the agency rate, not replacing it.
5. **Shootings** ("Shots Fired", "Shooting Hit") are listed as separate incident types and are left out of the violent
   count because the portal does not say whether each is also recorded as an assault or homicide.

## Recommendation

- Keep the safety cut on the agency rate for every Jersey City neighborhood (all inherit 4.87 / 18.32, no code
  change needed: `scripts/crime_benchmarks.py` lines 65-71 read each unit's agency rate).
- Show the sub-city estimate as context on the neighborhood card ("about twice the city's violent-crime rate" for
  Bergen-Lafayette; "about half" for Downtown), with the 10.5-month window and "estimate" stated.
- If Will wants it to count, the honest version is a flag, not a cut: `violent_ratio_to_city_portal >= 1.5`
  (today: Bergen-Lafayette, 1.90). Newport's property figure should be excluded from any rule or recomputed without
  shoplifting.
- The four JCPD districts are a second, official sub-city unit: the bundle carries district totals for 2026 and for
  2025 year-to-date (`byDistrict`). No district boundary file was found on a host we may read, so districts cannot be
  given a population and are not used.

## What does not exist

- No official neighborhood, ward or district **rates** for Jersey City. The city's open data host
  (`data.jerseycitynj.gov`) is robots-disallowed for us and stays off limits.
- No second year of incidents; no victim/offender detail; no time-of-day field beyond the report time.
- Nothing at all below the city for Newark or any other non-NYC city in scope.
