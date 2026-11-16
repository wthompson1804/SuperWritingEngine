# Scene text notes (written 2026-11-15/16)

Prose for the page's six years and its neighborhoods, written to Lamia in second person and bound to the collected
data. Nothing here is wired into the page yet; `site/` and the pipeline were not touched.

## Files

| File | What it is |
|---|---|
| `data/reference/scene_text_years.csv` | 6 rows: `year_label, scene, promise, catch, evidence_json` |
| `data/reference/scene_text_neighborhoods.csv` | 129 rows: `hood_id, hood_name, year_label, scene, good_for_her, watch_for, evidence_json` |
| `data/reference/scene_text_source.txt` | The hand-written drafts the two CSVs are built from. Edit text here, not in the CSVs. |
| `scripts/build_scene_text.py` | Fills the numbers into the drafts and writes the evidence. Generates no wording. |
| `scripts/check_scene_text.py` | Re-checks every text against the data. Run it after any data rerun. |

129 neighborhoods = the 127 in `site/data.json` when this was written, plus Bensonhurst and
Tompkinsville-Stapleton-Clifton-Fox Hills, which appeared in `data/ranked_units.csv` during the repair run.
Seven of the 127 have only an avoid card today; they still get a text.

## Method

1. **Numbers are never typed.** In the drafts every number is a token naming a measured field (`{drive}`, `{viol}`,
   `{dogpark}`). The builder reads the value, rounds it, prints it, and records an evidence item
   `{claim, field, value, source_file, row, agg, transform, shown}`; `claim` is the finished sentence. A missing value
   stops the build, so the sentence has to be rewritten without the fact. Nothing is guessed.
2. **Claims without a number are tested too.** "No bars within a 10-minute walk", "most homes are detached houses",
   "tolls not fully known" each carry a hidden token with a test (`bars_800m == 0`, `detached_house_share >= 0.5`,
   `toll_complete all true == False`). The test is stored as `holds_if` and re-run by the checker.
3. **Sources.** Neighborhood figures: `data/lifestyle_groups.csv` (drive and transit minutes to Jamaica station, crime
   rates and the Jamaica yardstick, counts of restaurants, bars and cafés, park walk, distances to dog park,
   supermarket, vet, Trader Joe's, station, water and beach, and the census housing and household shares). Tolls:
   `data/master_buildings.csv`, all buildings in the neighborhood. Local rules: `data/reference/local_rules.csv`
   (`value_type = found` only). Residents' comments: `data/voices/neighborhood_quotes.csv`.
4. **Tolls.** A toll is stated only when `toll_complete` is true for every building in the neighborhood; then the
   median round trip is given to the dollar ("about $24"), or "no tolls" when it is zero. Otherwise the text says
   "tolls not fully known" and gives no figure (80 of 129 today). When the toll rerun lands, the checker fails these
   rows, which is the cue to rewrite them.
5. **Crime.** Rates are per 1,000 residents for the police agency or precinct, set against the Jamaica ceiling
   (violent 9.8, property 25.0), which is read from the data, not typed.
6. **Residents' voices.** Paraphrased as "residents on review sites say…", never quoted, never attributed. For each
   theme a text leans on, the evidence stores the positive / mixed / negative counts for that neighborhood and theme,
   and the checker fails the row if those counts change. I read the excerpts for parking, car crime, dogs and green,
   social life and safety; other themes are not used. The check proves the quotes exist and have not changed, not that
   my paraphrase is fair. That part needs a human read (56 rows cite voices).
7. **Local rules.** Only what a `found` summary says. Numbers quoted from a rule (hours, dates) must appear in the
   cited summary. 13 rows cite a rule.
8. **Wording conventions.** "A 10-minute walk" always means the 800 m radius of the place counts; "1 mile" means the
   1,600 m radius. Distances are from the buildings found in the neighborhood (the median building), in miles to one
   decimal. Drive times are free-flow estimates and are written "about N minutes".
9. **Years.** Each scene has the same four moments in the same order (workday at home, evening dog walk, Saturday
   night, Sunday at her parents') and 74 to 83 words, so no year wins on writing. Year figures are medians across the
   year's neighborhoods in `lifestyle_groups.csv`, leaving out safety-cut ones.
10. **Style.** Second person, short sentences. The checker rejects question marks, em and en dashes, "not … but",
    spelled-out quantities (so a number cannot slip past the evidence rule), wording about race, ethnicity or religion
    (including "diverse"), and dollar amounts of 1,000 or more. Word limits: year scene 60–90, neighborhood scene
    35–60; one sentence for `promise`, `good_for_her`, `watch_for`; one or two for `catch`.
11. **Mock-up.** `site/mock4_reference.html` was not read for wording. A six-word overlap test against it finds none.

## What the checker does and does not prove

It proves that every number in the prose has an evidence item, that each item still resolves in its source file, and
that the current value still rounds to the printed number or still passes its test. A value that moved without
changing the words is reported as `drift`, not failure. It does not judge tone, the fairness of a paraphrase, or
phrases with no token behind them. I kept those few and plain ("a quiet township", "a small harbor town"), but they
are my reading of the figures and the place name, not a measured field.

## What I would not claim, and why

- **Who lives there by race, ethnicity or religion.** Not collected, not written. Quotes that describe a place that
  way were not paraphrased.
- **Specific apartments, rents or all-in costs.** The unit list is being repaired. No building is named and no rent
  appears. The Room-to-Breathe scene gives a typical size in square feet and no price.
- **Where her car would sleep.** Parking type is a building fact and the buildings are changing, so the texts say
  only what the neighborhood shows: the share of car-free households, local street rules, and what residents say.
  "Parking is scarce" is always tied to one of those.
- **Toll figures where any building's toll is incomplete.** See Method 4.
- **Train stations and the last train home.** The nearest-station field sometimes points across a river (Fort Lee to
  a Bronx station, Edgewater to Harlem), and the NJ Transit schedule in use ended on 2026-11-08. Station distance is
  given only where the nearest station is in or beside the town itself; no last-train time appears anywhere.
- **"Best", "lowest", "closest on the page".** Rankings between places would go stale with every rerun and had no
  evidence item, so I removed them.
- **Dog rules on beaches, small-dog areas, park hours.** Stated only where a `found` rule says so (White Plains,
  Hempstead, Haverstraw, LaGrange). Long Beach's text tells her to check the beach rule; it does not state one.
- **Park size in hectares.** Used only as a hidden test for "a large park"; never printed.
- **Block-level safety.** Rates describe a police agency or precinct, as `docs/SAFETY_BASIS.md` says.

## Weak spots

1. **Year figures are not the page's year tiles.** The tiles in `site/data.json` come from `data/group_exchange.csv`,
   which is weighted by units and changed twice while I worked. The prose uses the median neighborhood. The gap is
   largest for the Fresh-Start Year: the typical neighborhood is about 34 minutes from Jamaica, the tile says about 63,
   because most of its units are in Harrison, Norwalk and New Brunswick. The scenes say "the typical neighborhood
   here" for that reason. Once the unit list settles, either switch the year drafts to the page's figures (the builder
   accepts `{x_drive_min}`, `{x_restaurants_800m}` and any other `group_exchange.csv` column) or let the tile and the
   sentence state their different bases.
2. **Year medians include neighborhoods that are not on the page** (for example 19 Quiet-Street neighborhoods in the
   data, 7 on the page). No data file lists the page's neighborhoods in a stable way.
3. **The texts are regular.** Most neighborhood scenes follow one order: what is around, the green, the drive. That
   is deliberate for fairness, but 129 in a row read alike.
4. **One building stands for the neighborhood in 45 places.** Distances there are that building's, not the area's.
5. **"Review sites" is almost entirely one site** (873 of 890 quotes are from Niche).
6. **Elizabeth.** The census figures around its one building are degenerate (0% car-free, 100% renters, 100% built
   before 1940), so no census trait is used there.
7. **Paraphrase words such as "a big park" or "low crime"** rest on thresholds I chose (10 or 20 hectares; no fixed
   crime cut-off). They are recorded in `holds_if` where a token exists.

## Neighborhoods with too little data for a real scene

**No crime figures** (the text says so and makes no safety claim): New Paltz, Beacon Falls, Oxford, LaGrange.

**One building, no resident comments** (32; the scene is that building's surroundings plus agency crime rates):
Upper East Side-Lenox Hill-Roosevelt Island, Roxbury, Princeton, Kew Gardens Hills, Glen Cove, New
Springville-Willowbrook-Bulls Head-Travis, Ridgewood, Elizabeth, South Orange, Riverdale (NJ), Red Bank, Long Branch,
Maplewood, Springfield, Garwood, Morris Plains, Plainfield, Dover, Old Bridge, Stratford, Brookfield, Wallkill, Beacon
Falls, Oxford, Pomonok-Electchester-Hillcrest, East New York (North), Murray Hill-Broadway Flushing, East Harlem
(South), Windsor Terrace-South Slope, Gravesend (West), Tompkinsville-Stapleton-Clifton-Fox Hills, St. George-New
Brighton.

**No resident comments at all:** 73 of 129. **No local rule cited:** 116 of 129. New York City's rules are in the file
but were not written into the NYC texts; they are the same for every NYC neighborhood and the page already shows them.

**Avoid card only today:** Bedford-Stuyvesant (West), East New York (North), Hamilton Heights-Sugar Hill, Kew Gardens
Hills, Kingsbridge Heights-Van Cortlandt Village, Williamsbridge-Olinville, Windsor Terrace-South Slope.

## After a data rerun

`python3 scripts/check_scene_text.py`. For each failing row, edit its block in
`data/reference/scene_text_source.txt`, then `python3 scripts/build_scene_text.py` and check again.
