# Building storeys and floors from unit labels (2026-11-17)

Script: `scripts/building_stories.py` (`download`, `build`; no argument runs both). Outputs, read by `build_master.py`:
`data/reference/building_stories.csv` and `data/reference/unit_floor_reads.csv` (headers fixed; see the script docstring).

Why: from 2026-11-17 a walk-up is allowed when the apartment is on floor 2; floor 3 and above need an elevator
(CLAUDE.md, "Second trawl"). That needs each building's storeys from a record, and each apartment's floor.

## Candidates

Every distinct `addr_key` in `data/listings.csv` with `listed_rent` <= 2200 and `gate_status` pending or pass:
6,656 buildings when built (the file is rebuilt by other agents during the day; a rerun follows it). County from the
Census 2023 county boundaries already held (`raw/census_cb/`). Rows are ordered New Jersey, Brooklyn, Connecticut,
Long Island (Nassau, Suffolk), Long Island City (ZIPs 11101, 11109, 11120), then the rest.

## How each source is joined

- **NYC PLUTO** (official_record): the held 4+-unit lot file only. A lot is taken when its house number (digits only,
  so `142-38` = `14238`) and street name match the listing address and the lot point is within 150 m. Street names
  are normalised (ordinals `37th` = `37`, `Avenue` = `AVE`, `West` = `W`); type and direction must agree when both
  sides give one (`37 AVE` is not `37 ST`). A `house_number+location` row of `nyc_building_facts.csv` is the fallback;
  its `nearest_lot` rows are **not** used (they can be a neighbour) and are named in notes.
- **NJ MOD-IV** (official_record): tax-list rows of the county, each placed at a point inside its parcel (condo and
  other qualified rows take their base lot). A row is taken when it lies within 400 m, its street matches and its house
  number equals or falls inside the other's range on the same side of the street (`71-79` does not hold `76`).
  Garage, vacant and exempt rows at the same address give way to residential classes 2, 4A, 4C. Several rows (condo
  units) give the most common value; other values are listed in notes. A large apartment lot (class 4C, 8,000 m2 or
  more) whose tax address has another house number is taken only when the point is well inside it; a neighbouring
  house is never taken. Storeys are read from the start of `BLDG_DESC`: `<n>S` (`3S-B-D-6U-H`, `2.5SF`, `3 SF 6 FAM`),
  `<n><material>-<units>U` (`4B-8U-H`), material then `<n>S` (`F2S`), `<n>STR` inside (`257APT/3STR/OFF`), and ranges
  (`4&5S` -> 5, noted). Descriptions such as `2  F`, `2 FAMILY`, `CONDO`, `1BR/1BA`, `32 UNITS` state no storeys and
  are not read. Half storeys stay as given (`2.5`). For a complex, one description covers the lot, so single buildings
  can differ (said in notes).
- **listing** (12 buildings): a numeric `building_floors` on a detail page we hold (never a search card, never Trulia
  or Zillow rows). Used only where no record exists; a different listing figure is noted as CONFLICT.
- **osm**: `building:levels` of the outline containing the point, or the nearest within 20 m, through
  `scripts/tools/places.py` and the held extract. Used where neither a record nor a listing gives the figure; a
  different OSM figure beside a record is noted.

No storeys found: `stories` and `stories_basis` empty, notes start `not_found` and say where we looked.

## Results (build of 2026-11-17)

| Area | Buildings | official_record | listing | osm | not found |
|---|---|---|---|---|---|
| New Jersey | 3,893 | 1,527 | 5 | 102 | 2,259 |
| Brooklyn | 207 | 104 | 2 | 14 | 87 |
| Connecticut | 903 | 0 | 2 | 18 | 883 |
| Long Island | 272 | 0 | 1 | 3 | 268 |
| Long Island City | 9 | 7 | 0 | 1 | 1 |
| Other (Bronx, Manhattan, Queens, Staten Island, Westchester, Hudson Valley, PA) | 1,372 | 305 | 2 | 17 | 1,048 |
| **All** | **6,656** | **1,943** | **12** | **155** | **4,546** |

Of the 2,110 with storeys: 879 have 1 to 2 storeys, 902 have 3 to 5, 329 have 6 or more. NJ alone: 842 / 702 / 90
(many NJ candidates are two-family houses, class 2).

NJ misses: 1,178 buildings matched a tax record whose description states no storeys; 1,187 found no tax record at the
address within 400 m (unusual listing addresses, a building name instead of a street address, or a different number
on the tax list). NYC misses are mostly lots with fewer than 4 residential units (never downloaded) or condo lots
filed under another address. CT and Long Island rest on OSM, which tags levels on very few outlines.

Checks written into the notes: 26 buildings carry `CHECK:` where three-digit unit labels read above the recorded
storeys (a record older than the building, another lot, or another numbering); 41 where OSM disagrees with the
record; 3 where a listing page disagrees.

## Floors from unit labels

1,447 candidate listings read (NJ 715, CT 415, NY 315, PA 2). Floors: 37 on floor 1, 566 on 2, 363 on 3, 217 on 4,
134 on 5, 130 on 6 or higher. Conventions: `floor_then_letter` ('2B', '#2R'), `floor_then_two_digits` ('205'),
building letters or number then floor and two digits ('JCE-205', 'B305', '09-326', 'BAY-B508'), street number then
floor and letter ('158-2H'), the reviewed complex conventions (`floor_first`, `building_floor_unit`), and `ground_word`.
Not read: 'A', 'PH', 'G107' (G may be garden), '1-12', bare four-digit numbers without a reviewed convention,
three-digit labels in a building-floor-unit complex, two-digit floors with a letter ('43L') unless the building's
height is known to reach them (in Hudson County walk-ups '43L' is floor 4), and any reading above the recorded storeys
(197). Notes say whether the reading agrees with a floor the listing states (29) or not (2, marked CONFLICT).

## Not done / for later

- CT town assessor sites (Vision, etc.) show storeys per parcel, but only as one page per parcel: not a bulk source,
  not used. Nassau has no public bulk parcel file that we found.
- NYC lots under 4 units: a bulk PLUTO from another official host was not available in the project; no request was
  made to data.cityofnewyork.us.
