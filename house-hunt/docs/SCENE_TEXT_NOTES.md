# Scene text notes (written 2026-11-15/16; host voice, crime rule and section subheads added 2026-11-16)

Prose for the page's six experiences (formerly "years"), its neighborhoods and its places, written to Lamia in second
person and bound to the collected data. The first part of this file describes the system as it stands now. The earlier
notes are kept below under "First version", because their method still applies to the older fields.

## Files

| File | What it is |
|---|---|
| `data/reference/scene_text_years.csv` | 6 rows. `year_label` (the key, still "... Year"), `display_label` ("The Walk-Everywhere Experience"), `tagline`, `subhead`, `scene`, `promise`, `catch`, `host_intro`, `host_walkthrough` (3 paragraphs separated by a blank line), `sub_cost`, `sub_to_parents`, `sub_going_out`, `sub_green`, `sub_compared_to_queens`, `evidence_json` |
| `data/reference/scene_text_neighborhoods.csv` | One row per neighborhood drafted (136 today). `hood_id`, `hood_name`, `year_label`, `scene`, `good_for_her`, `watch_for`, `host_intro`, `sub_cost`, `sub_to_parents`, `sub_parking`, `sub_dog`, `sub_going_out`, `sub_green`, `sub_residents_say`, `sub_local_rules`, `sub_compared_to_queens`, `evidence_json` |
| `data/reference/realtor_lines.csv` | One row per unit on the page. `listing_id`, `host_line`, `host_catch`, `sub_cost`, `sub_parking`, `sub_dog`, `sub_building`, `facts_used_json` |
| `data/reference/scene_text_source.txt` | The hand-written drafts the two scene CSVs are built from. Edit text here, never in the CSVs. |
| `scripts/build_scene_text.py` | Fills the numbers into the drafts, picks the section subheads, writes the evidence. Generates no wording. |
| `scripts/check_scene_text.py` | Re-checks every text against the data. Run it after any data rerun. |
| `scripts/realtor_lines.py` | Composes the per-unit lines from each unit's own fields (reads `site/data.json`, read-only). |
| `scripts/test_realtor_lines.py` | 32 tests for the generator; also re-checks every unit on the page. |

After any data rerun: `python3 scripts/build_scene_text.py && python3 scripts/check_scene_text.py`, then
`python3 scripts/realtor_lines.py && python3 scripts/test_realtor_lines.py`. The builder refills every number, so most
changes need no editing. It stops on a row only when a sentence's test no longer holds; edit that block in the
drafts file and build again.

## What changed on 2026-11-16

1. **Experiences.** The page calls a year an experience. The key column is unchanged; `display_label` carries the new
   wording. New: `tagline` (one line), `subhead` (a replacement for the page's subhead, no crime clause),
   `host_intro` (110 to 160 words) and `host_walkthrough` (a weekday, a Saturday night, a Sunday with her parents;
   40 to 60 words each). `promise` and `catch` were rewritten to say what life is like and no longer say "year".
2. **Figures match the tiles.** Experience prose now quotes the page's own unit-weighted figures: `p_` tokens read
   `site/data.json` `years[].medians` and counts, `u_` tokens are medians or shares over the units shown. The old
   `scene` now uses them too for drive, transit, park walk and size. Experience prose gives typical figures only,
   never a range; where useful it names the nearest neighborhood (`{p_near}`, `{p_near_drive}`).
3. **Neighborhood `host_intro`** (60 to 90 words) for every neighborhood, in about ten shapes rotated by what is most
   distinctive (the green, the food, the drive home, the parking rule, the water, the price, the catch first, the
   dog's morning, the quiet, a residents' line). Local rules are folded in where they bite (overnight bans, permit
   rules, dog rules), and residents are paraphrased as "people who live here say".
4. **Tolls.** Every toll figure now comes from `data/enriched/*.json` (`drive.toll_round_trip_ezpass`, complete for
   every building), as the median over the neighborhood's buildings, through `building_crosswalk.csv` and
   `master_buildings.csv` (read-only). The wording is fixed: "about $X round trip with a New York E-ZPass". No text
   says "tolls not fully known" any more.
5. **No crime in the open prose** (owner's rule). No rates, no "per 1,000", no comparison with Jamaica, no "low crime"
   as a selling point, in any field. Two wordings are allowed, each tied to a test the checker re-runs:
   "one of the safest spots on the whole list" (only in `good_for_her`, only where the neighborhood is in the lowest
   fifth by violent rate among the neighborhoods on the page; 21 rows today) and "the safety limit we set" (only in
   `watch_for`, only where the violent rate is 8.0 or more against Jamaica's 9.8; 5 rows today). `watch_for` and
   `catch` are about living there: the drive, parking rules, thin nightlife, car dependence, cost, choice.
6. **Section subheads** (`sub_` columns): one optional line, at most 14 words, no numbers, under each section headline
   of the page. They are conditional drafts in the source file (`=== sub:` blocks): each line is
   `conditions :: wording | wording`, the first line whose conditions hold for a row is used, and the wording is
   picked by a hash of the row's id. Every condition is stored as evidence with its test. No match means an empty
   subhead, on purpose.
7. **Places.** `scripts/realtor_lines.py` writes `host_line` (1 or 2 sentences, at most 45 words), `host_catch`
   (1 sentence) and four section subheads per unit from the unit's fields, with 42 line patterns. See its docstring.
8. **Jersey City** is now eight neighborhoods in the data. The whole-city drafts were removed and eight new blocks
   written. The builder skips (and lists) any draft whose neighborhood has left `lifestyle_groups.csv`.

## Draft syntax added

- `[[ ... ]]` is optional text: dropped whole when a value inside is missing or a hidden test inside fails. Pairs of
  them give either/or wording (`[[no tolls{!u_toll==0}]][[tolls run about ${u_toll} ...{!u_toll>0}]]`), which keeps
  the experience prose true while the unit list changes.
- A block may appear twice in the file (the host voice has its own section); `rules:` and `voices:` lines add up.
- Tokens: `pg_lo`, `pg_hi`, `pg_n` (the page's all-in range and count for a neighborhood; use inside `[[ ]]`),
  `pg_safe` (violent-rate percentile among page neighborhoods), `q_cost`, `q_sqft`, `q_drive`, `q_food`, `q_green`
  (the page's 1 to 5 comparison with Queens), `p_...` and `u_...` for experiences, `b_toll` from the enriched files.
- Rules and residents' comments are read from both rounds (`local_rules*.csv`, `neighborhood_quotes*.csv`).

## What the checker adds

Word limits for the new fields; three paragraphs for the walkthrough; listing-ad hype words; the crime rule and its two
allowed wordings; subhead rules (14 words, one sentence, no digits, no hedging words); and a form-letter test across
rows: at most 3 `host_intro` texts may open with the same 3 words, and no run of 6 words may appear in more than a
tenth of them (the fixed toll wording and number units are exempt). The `scene` limit for neighborhoods went from 60
to 68 words because the fixed toll wording is longer than "tolls not fully known".

## Weak spots (current)

1. **`site/data.json` moved several times while this was written** (210, then 326, then 321 units; 94, then 120
   neighborhoods). The experience prose is built to survive that, but its adjectives are not all tested: "Start here
   if you like options" is tested, "a soft landing" is not. Reread the six experiences after the unit list settles.
2. **Neighborhood `host_intro` texts** (median 78 words) nearly all end on the drive and
   the toll. The form-letter test passes, but read in a row the closing sentence is recognisably the same move.
3. **Park and dog-park names** come from the most common name among the neighborhood's buildings, and the minutes
   from the median building, so a name and its distance can belong to different buildings. Three names that read
   wrongly (a playground, a dog daycare) were replaced with "a park" or "a dog park"; others may exist.
4. **Paraphrases of residents are not machine-checked for fairness.** The check proves the quotes exist and the
   counts have not changed. I read the excerpts for parking, dogs and green, and social life; safety and car-crime
   comments are no longer used anywhere. The quote exclusions file is not applied to the counts.
5. **Section subheads repeat.** There are 2 or 3 wordings per condition, so the commonest lines appear 15 to 20
   times across 136 neighborhoods, and the unit subheads more often (the commonest about 75 times in 321 units).
   They are short enough that this reads as a house style, but it is not unique writing.
6. **`sub_compared_to_queens`** rests on the page's 1 to 5 scale and also fires for neighborhoods that are in Queens.
7. **Unit lines:** two patterns carry most garage units (71 of 321), and the catch for 92 units is the same fact (a
   special whose effect on the price is not stated) in three wordings. "First of N on the scorecard" presents the
   pipeline's rank as the host's opinion.
8. **A rule's summary is quoted, not its legal text.** Where a summary says "many streets" the prose says so too.
9. The earlier weak spots 3 to 7 below still apply to `scene`, `good_for_her` and `watch_for`.

---

# First version (2026-11-15/16), kept for the method

Superseded points: the year figures now use the page's figures (old weak spot 1), tolls are complete (old method 4),
and crime rates are no longer written anywhere (old method 5, and the crime lines in "What I would not claim").

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
