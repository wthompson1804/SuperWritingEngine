# Harvest notes: building amenities (`building_amenities`)

Run: 2026-11-15. Script `scripts/building_amenities.py`; output `data/reference/building_amenities.csv`
(one row per `addr_key` with at least one `unit_status == pass` row in `data/units.csv`).

## Coverage

- **271 buildings** (all passing `addr_key`s), 271 with at least one cached page parsed. 67 used more than one page.
- **No new page was fetched.** Every building had a cached page. Three Zumper listings carry no amenity list at
  all and have no other known URL (`notes` column says so); they are `no_mention` throughout.
- Rerun: `python3 scripts/building_amenities.py` processes only `addr_key`s not yet in the CSV (rows of buildings
  that stop passing are kept). `--rebuild` reparses everything from cache (about 8 s). `--no-fetch` forbids the
  one-page fallback fetch (robots-checked for the Claude-named groups and `*`, 2 s per host, cached in
  `raw/building_amenities/`).

## Pages read per building, in priority order

1. Management-site communities: the pages in `community_facts.csv` `pages_read` (community page, own website,
   amenities / FAQ pages), all from cache.
2. `building_url` if cached, then the `raw_path` of every passing unit row.
3. Sibling rows in `data/listings.csv` with the same `addr_key` (any source, up to 12 pages), then cached
   `also_seen_at` URLs.

Parsers: Apartment List (`community_amenities`, `unit_amenities`, `top_amenities`, `parking[]`,
`parking_details_text`, `year_built`, `year_remodeled`, `total_units_count`, `pmc_display_name`, description);
Zumper (`amenity_tags`, `building_amenity_tags`, `year_built`, `floors`, description); Trulia (`features`
categories, description); Greystar (`amenities`, `features`, monthly parking fees, long description); AvalonBay
(`communityFeatures`, `unitFeatures`, parking policy, parking fees); any other page as visible text lines.
`community_facts.csv` fills pool, gym, controlled access, dog amenities, package room, coworking, parking type and
fee, manager, year built and floors only where the page parse found nothing (evidence starts `[community_facts.csv]`).

## Fill rates (value other than `no_mention` / blank), by the source of the passing rows

| column | all (271) | apartmentlist (86) | trulia (100) | zumper (63) | mgmt sites (22) |
|---|---|---|---|---|---|
| pool | 76 (28%) | 41 (47%) | 4 (4%) | 12 (19%) | 19 (86%) |
| gym | 167 (61%) | 72 (83%) | 42 (42%) | 31 (49%) | 22 (100%) |
| doorman_or_concierge | 83 (30%) | 43 (50%) | 10 (10%) | 22 (34%) | 8 (36%) |
| controlled_access | 97 (35%) | 33 (38%) | 20 (20%) | 33 (52%) | 11 (50%) |
| gated_or_garage_parking | 178 (65%) | 76 (88%) | 51 (51%) | 31 (49%) | 20 (90%) |
| parking_fee_monthly | 38 (14%) | 21 (24%) | 0 (0%) | 1 (1%) | 16 (72%) |
| dog_amenities | 66 (24%) | 42 (48%) | 7 (7%) | 5 (7%) | 12 (54%) |
| in_unit_laundry | 215 (79%) | 81 (94%) | 61 (61%) | 52 (82%) | 21 (95%) |
| roof_deck_or_outdoor_space | 164 (60%) | 66 (76%) | 46 (46%) | 30 (47%) | 22 (100%) |
| balcony_some_units | 113 (41%) | 50 (58%) | 26 (26%) | 16 (25%) | 21 (95%) |
| package_room | 112 (41%) | 51 (59%) | 20 (20%) | 21 (33%) | 20 (90%) |
| coworking_or_lounge | 135 (49%) | 67 (77%) | 23 (23%) | 26 (41%) | 19 (86%) |
| elevator_stated | 202 (74%) | 67 (77%) | 84 (84%) | 48 (76%) | 3 (13%) |
| year_built | 54 (19%) | 47 (54%) | 3 (3%) | 3 (4%) | 1 (4%) |
| year_renovated | 4 (1%) | 4 (4%) | 0 | 0 | 0 |
| total_floors | 10 (3%) | 1 (1%) | 3 (3%) | 0 | 6 (27%) |
| unit_count | 75 (27%) | 72 (83%) | 1 (1%) | 0 | 2 (9%) |
| management_company | 56 (20%) | 34 (39%) | 0 | 0 | 22 (100%) |

Value breakdowns:

- pool: outdoor 35, yes_type_unknown 33, indoor 6, both 2, no_mention 195.
- doorman_or_concierge: 24h 27, yes 56, part_time 0, no_mention 188.
- gated_or_garage_parking: garage 120, parking_type_unknown 40, open_lot 8, covered 6, street_only 4, gated_lot 0,
  no_mention 93.
- in_unit_laundry: yes 143, on_site_only 72, no_mention 56.

## Caveats

- **`no_mention` is not "no".** Trulia unit listings (100 buildings) have a short features block; most of their
  values come from the broker's description, so their fill is low and absence means little. Rows carry a note.
- **`parking_type_unknown`** is an extra value in `gated_or_garage_parking`: the page lists parking ("Parking",
  "Assigned", "Valet") without a type. When several types are listed the best one wins
  (garage > gated_lot > covered > open_lot > street_only). Apartment List `parking category: none / other` is
  treated as no mention.
- **`parking_fee_monthly` is the lowest monthly amount stated.** AvalonBay fee tables give a range ("$15-$350");
  the low end may be a motorcycle or second-tier space. The full text is in the evidence column. Trulia and Zumper
  pages almost never state a fee.
- **Pool type** is set only by a word next to "pool": indoor / in-door, outdoor, rooftop, "on the roof".
  "Pool with sundeck" or "resort-style pool" stays `yes_type_unknown`. Two "both": 100 Julia Dr (indoor pool on
  one page, outdoor pool from `community_facts.csv`) and 123 Linden Blvd ("Rooftop and indoor swimming pools").
- **Description text** is used with vetoes: negations ("no", "without") and sentences about the surroundings
  ("near", "blocks", "minutes", "public") are skipped for pool, gym, dog park, laundry, outdoor space, lounge and
  parking. Evidence starting `[description]` or `[page text]` is free text and less sure than a list item. Some
  Apartment List descriptions summarise resident reviews ("Residents rave about ... indoor pool").
- **in_unit_laundry = yes** means at least one page for the building says in-unit (often one unit's listing; other
  units may differ). Trulia "Appliances: Washer / Dryer" counts as in-unit. `on_site_only` means only shared or
  unspecified "laundry" was mentioned. "W/D hookup" alone is no mention.
- **doorman_or_concierge** excludes "virtual doorman", "package concierge" and "valet trash"; a virtual doorman
  counts under `controlled_access`. `24h` needs "24-hour", "24/7" or "24hr" beside the word.
- **controlled_access** includes a bare "gated" or "fob" mention (for example a garage fob fee line).
- **roof_deck_or_outdoor_space** is shared space (roof deck, courtyard, sundeck, BBQ, fire pit, garden, shared
  terrace). A Zumper unit-level "Outdoor Space" tag also lands here because the tag does not say private.
  **balcony_some_units** needs balcony, patio or "private terrace / outdoor space".
- **elevator_stated** is low for management sites because their pages rarely say it; the elevator gate itself
  lives in `units.csv`.
- **total_floors**: page text ("26-story high-rise"), else the harvest row's `building_floors` (evidence says
  `[harvest row ...]`). **year_built / unit_count** are mostly Apartment List page data. PLUTO values are not copied
  in; join `units.csv` `pluto_*` for NYC.
- **management_company**: Apartment List `pmc_display_name`, the site operator for management sites, or "managed by
  X" in text. Trulia and Zumper brokers or agents are not treated as managers.
- AvalonBay `addr_key`s include the unit number, so one community appears as several rows with the same values.
- `source_url` is the page that supplied the most columns; `sources_json` lists every page read and the page for
  each column that came from a different one. `retrieved_at` is the newest fetch time among the pages read.
