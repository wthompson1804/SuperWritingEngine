# Scene text notes

The words on the experience pages and the neighborhood pages: how they are written, built and checked.
Rewritten 2026-11-16 after the copy edit, and extended the same day after independent check 4
(`docs/INDEPENDENT_CHECK_4.md`) and independent check 5 (`docs/INDEPENDENT_CHECK_5.md`; the sections "After
independent check 4" and "After independent check 5" below say what changed and why). It describes the system as
it stands; the earlier history is in git (`git log -- docs/SCENE_TEXT_NOTES.md`).

## Why the copy edit happened

The owner read the page and said one line ("the dog walks you toward the water") looked like an error. The cause was
general: the earlier text aimed for a host's wit and for variety between rows, and both produced lines that needed
decoding ("the street has a bedtime", "the cost is the map", "you are buying square feet with miles", "where the car
sleeps"). A second problem came from a page audit: numbers in the text disagreed with the figure strip above them,
because the text recomputed counts and prices from a list that had since changed.

The rule now: **say the plain thing, and quote the page's own number.**

## Files

| File | What it is |
|---|---|
| `data/reference/scene_text_source.txt` | The hand-written drafts. Edit text here, never in the CSVs. |
| `scripts/build_scene_text.py` | Fills the numbers into the drafts, picks the icon points and section subheads, writes the evidence. Generates no wording. |
| `scripts/check_scene_text.py` | Re-checks every text against the data and against the plain-language rules. |
| `data/reference/scene_text_years.csv` | 6 rows, one per experience (the key column is still `year_label`, "... Year"). |
| `data/reference/scene_text_neighborhoods.csv` | One row per neighborhood drafted that is still in `data/lifestyle_groups.csv`. Its `glance_json` column holds the "At a glance" facts, computed from the buildings shown. |
| `scripts/check_published_text.py` | The final-text audit: reads `site/data.json`, every prose field the page shows, and checks it against its source, the plain-language rules, the numbers and a list of checkable claims. |
| `scripts/test_check_published_text.py` | Tests for the audit and for the conceit guard, with the examples independent check 4 planted. |

`scripts/realtor_lines.py`, `data/reference/realtor_lines.csv` and `data/reference/building_about.csv` (the building
and apartment lines) are a separate system. They were not part of this copy edit, and have since been rewritten to the
same plain standard by `scripts/realtor_lines.py`: the guards are the ones in `check_scene_text.py`, imported by
`scripts/test_realtor_lines.py` and run over every building and apartment text. `check_scene_text.py` in turn imports
`realtor_lines.parking_facts`, so the neighborhood text, the building text and "At a glance" read parking one way.

After any data rerun (the order matters: the text is built from the page data, attached to it, then audited there):

    python3 scripts/page_data_extras.py && python3 scripts/build_scene_text.py && python3 scripts/check_scene_text.py \
      && python3 scripts/realtor_lines.py && python3 scripts/test_realtor_lines.py \
      && python3 scripts/page_data_extras.py && python3 scripts/check_published_text.py \
      && python3 scripts/test_check_published_text.py

The builder refills every number. It stops on a row when a sentence's hidden test no longer holds; edit that block and
build again. It lists (and leaves out) a sentence about the shown apartments that stopped being true; rewrite those
too, so that the list is empty.

## What the page shows, and where each text goes

Experience page (`#exp-…`):

| Field | Where it appears |
|---|---|
| `tagline` | under the title, and on the experience's card on the first page |
| `host_intro` | "About this experience", 2 or 3 sentences |
| `about_points_json` | the icon points beside it; the one `warning` is shown as "The catch" |
| `day_moments_json` | "A day in this experience": a weekday, Saturday night, Sunday with Mom and Dad. The first sentence of each moment is set off as its headline |
| `promise`, `catch` | "The promise and the catch" row; the promise is also that row's headline |
| `sub_cost` … `sub_compared_to_queens` | one line under the headline of each section |
| `subhead` | replaces the pipeline's subhead (used where the tagline is missing) |
| `scene`, `host_walkthrough` | read by the page only when there are no day moments. They are no longer written by hand: the builder fills them with the three moments, so nothing unseen can drift |

Neighborhood page (`#hood-…`):

| Field | Where it appears |
|---|---|
| `host_intro` | "About <name>"; its first sentence or two is also the neighborhood's line on the experience page |
| `about_points_json` | the icon points; the `warning` is "The catch" |
| `scene`, `good_for_her`, `watch_for` | "The good and the catch" row. `good_for_her` is the row's headline |
| `sub_…` | one line under each section headline |

## How a text is written

Experience: who it suits, what a normal day is like, what Saturday night is like, Sunday with her parents, what she
gives up, in that order, with no fact said twice. Every `host_intro` opens "This suits you if …" on purpose, so the six
can be compared.

Neighborhood:

1. `host_intro` leads with the thing that is different about this place (a named park, the water, a parking rule, a
   very large or very cheap apartment, what residents say), then gives the catch. Not a statistic every neighbor shares.
2. `scene` is daily life: what is on foot, the dog's walk, groceries, the train.
3. `good` is one sentence of 64 characters at most (the page prints it as a headline and cuts anything longer at a
   comma). `watch` is one sentence: the honest catch.
4. Where the data gives nothing distinctive, the text is short. Two plain sentences are better than five padded ones.

Vocabulary: "your parents" in sentences ("Mom and Dad" only in the page's labels), "apartment" for a unit,
"building", "neighborhood", "experience". Prices follow the page, which shows two labelled prices everywhere, "Rent"
(what the listing asks) and "Total with utilities and fees": a monthly total is "about $X a month with utilities and
fees" on first mention in a text and "about $X a month" after; a price the listing quotes is "rent", exact to the
dollar for one apartment ("The rent is $2,345, about $2,670 a month with utilities and fees.") and "about" to $10
for a typical figure; the limit is "your $3,000 limit" and applies to the total. "Everything included" and "all-in" /
"all in" are not used (section "Rent and total" below). Residents are
paraphrased as "Residents say / like / praise / call / wish …", never quoted, and the block then needs a `voices:`
line naming the themes. A number quoted from a local rule needs a `rules:` line.

## Draft syntax

- `{alias}` prints a measured value; `{alias:how}` rounds it another way. A number is never typed.
- `{!alias OP value}` prints nothing; the sentence is recorded as resting on that test, and the checker re-runs it.
  Every adjective that the data could contradict carries one ("a large park{!parkha>=20}").
- `[[ … ]]` is optional text, dropped whole when a value inside is missing or a test inside fails. Two in a row give
  either/or wording.
- `{w10}` and `{mile}` are the fixed wordings for the 800 m and 1,600 m radii.
- Word tokens (independent check 5) print fixed words chosen by a field and record the test they rest on:
  `{thestation}` / `{astation}` / `{thetrain}` name the nearest station by its kind ("the train station", "the
  subway", "PATH", "the light rail stop"; "the nearest station" where the shown buildings differ);
  `{fewbars}` / `{fewcafes}` / `{fewrest}` print "few bars" or, where there are none, "no bars";
  `{tollcost}` prints "about $24 round trip with a New York E-ZPass" or, where the tolls of the buildings shown
  differ by more than $5, "about $24 to $43 round trip with a New York E-ZPass, depending on the building"
  (`{tollshort}` leaves the last clause off, for an icon point).
- A sentence that leans on the one before it ("too", "also", "as well", an opening "And" / "But") may not open a
  text, and may not follow an optional sentence that dropped: the builder stops and the draft is rewritten.
- `=== points: hood`: `topic | icon | conditions :: wording | wording`. The first `warning` line whose conditions hold
  is the catch; then the first matching line of each other topic, at most 5. A point is skipped when the lead already
  gives the same figure. Points are plain facts in the same words on every page; they are not varied for variety's sake.
- `=== sub: hood.<section>` / `year.<section>`: `conditions :: wording | wording | wording` (at least 3). The first
  line whose conditions hold is used; a wording already on 12% of the neighborhoods is passed over; no match means no
  subhead.

## Where the numbers come from

| Token | Source | Why |
|---|---|---|
| `{p_places}` `{p_bldgs}` `{p_hoods}` `{p_allin}` `{p_allin_lo/hi}` `{p_drive}` `{p_transit}` `{p_sqft}` `{p_rest}` `{p_parkwalk}` `{u_toll}` | `site/data.json` `years[]`: `counts.shown`, `counts.buildings`, `len(hood_ids)`, `medians`, `all_in_range` | the experience page's figure strip reads the same fields |
| `{pg_n}` `{pg_bldgs}` `{pg_mid}` `{pg_lo/hi}` `{drive}` `{transit}` `{b_toll}` `{sqft}` | `neighborhoods[]`: `counts`, the median `all_in` of its units, `all_in_range`, `drive_min`, `transit_min`, `toll_round_trip`, `sqft_median` | the neighborhood page's figure strip |
| `{rest}` `{bars}` `{cafes}` `{rest1600}` `{parkwalk}` `{parkha}` `{dogpark}` `{super}` `{station}` `{water}` `{beach}` (neighborhood) | the buildings SHOWN there (`site/data.json` `buildings[]` and their apartments' `moments`; water, beach and park area from `data/master_buildings.csv` by building id): the median building, which is the building itself when one is shown | door-distance facts must describe the buildings she would live in (D16). "At a glance" reads the same figures from `glance_json` |
| `{own_dog}` `{own_garage}` `{own_parking}` `{dog_any}`, `{owndog}`, `{owngarage}` | `buildings[].amenities.dog_amenities`, `buildings[].parking.type` | what the shown buildings supply themselves (D6) |
| `{sqft_lo}` `{sqft_hi}` | the smallest and largest shown apartment | a plural "the apartments are large" is tested on the smallest |
| `{close_areas}` `{far_names}` `{far_drive}` `{far_toll}` `{tollfree_areas}` `{by_hood}` `{hood_names}` ... (experience) | how the experience's shown apartments divide on the drive (30 minutes) and on tolls | an experience that splits is worded as a split (D12) |
| `{@nj:teaneck drive}` (experience) | that neighborhood's own figure | a small experience gives each neighborhood's figure, never a typical one (D11) |
| `{u_garage}` `{u_laundry}` `{u_pool}` `{u_gym}` `{u_bars}` `{u_cafes}` `{u_rest1600}` `{u_dogpark}` `{u_super}` | medians or shares over the experience's shown units | nothing else on the page states these |
| census shares, `{station}`, `{beach}`, `{tj}`, `{vet}` | `data/lifestyle_groups.csv` or the shown units | not on the strip |
| tolls | always worded "about $N round trip with a New York E-ZPass", or "about $A to $B round trip with a New York E-ZPass" where the tolls of the group spoken of differ by more than $5 (`toll_round_trip_range` for a neighborhood; the lowest and highest toll of the experience's apartments, or of each half of a split) | fixed wording |
| `{b_toll_lo}` `{b_toll_hi}` `{toll_spread}`, `{u_toll_lo}` `{u_toll_hi}` `{u_toll_spread}`, `{far_toll_lo}` ... `{close_toll_spread}` | `neighborhoods[].toll_round_trip_range`; the apartments of the experience | N9 |
| `{stationkind}`, `{pet_spa}` | the shown buildings: `moments.sat.train_station_kind` (the one kind they share, else "mixed"), `amenities.pet_spa_or_wash` | N3, N16 |

Prices in sentences are rounded to the nearest $10 with "about"; minutes are whole. For a neighborhood with nothing
shown, every token falls back to `data/lifestyle_groups.csv`.

History of the door-distance figures. First they were medians over a neighborhood's shown apartments. Then, to agree
with "At a glance" (Bay Ridge: 14 restaurants in the text, 29 beside it), they were changed to the neighborhood's
frozen area profile (`traits`), and the checker required that source. Independent check 4 (D16) showed that was the
wrong way round: the area profile describes a wider sample than the apartments on the page (34 of 378 number claims
were materially off, 12 of them in single-building neighborhoods). They are now the median over the shown BUILDINGS,
the checker refuses the area profile for them, and "At a glance" is made to agree by reading `glance_json`.

Area-wide facts stay area-wide and are worded so: the town's parking rule, what residents say, the census shares
("most homes around here are houses", "nearly every household around here has a car", "many of the buildings in this
area are new"), the drive, the tolls and the transit time (the neighborhood's own fields).

## What the checker enforces (see its docstring for the full list)

- **True.** Every number has an evidence item; every item is looked up again; every hidden test is re-run.
- **The figure strip** (`check_strip`). Any dollar amount of $1,000 or more, any "N apartments / buildings /
  neighborhoods", and any "N minutes" in a sentence about her parents must be the strip's own figure, recomputed from
  `site/data.json` at check time. An evidence item that computes one of these from the unit list fails.
- **Plain** (`check_plain`).
  - `CONCEITS`: the constructions that were removed, as patterns: a thing acting on "you" ("walks / sends / feeds /
    rewards you", "the street tells you"), "has a bedtime", "where the car sleeps", "the cost is the …", "the upside
    is", "the rest of the story", "count on about", "then there is", "on the table", "the curb", "green" or "sand" as a
    noun, "home" for her parents' house, "about 0", and the individual jokes that were cut. Add to it when a new one
    is cut.
  - Readability per text: sentences average at most 20 words, none over 32, at most one figure-of-speech marker.
  - Vocabulary: no "Mom and Dad" in a sentence, no "unit", no "place" for an apartment, no "… Year", no "all-in" / "all in", no
    "everything included", the first monthly price of $1,000 or more in a text says "with utilities and fees" and a
    later one does not repeat it (`monthly_price`), no project terms (ranked, scorecard, verified, live check, net-effective, gate, asterisk, cap, ceiling), no "we",
    American spelling.
  - Headline fit: `promise` and `good_for_her` fit whole in 64 characters.
- **Leads** (`check_leads`). A neighborhood's first sentence may not open on a statistic that more than a third of the
  neighborhoods in its experience also open on.
- **House style, unchanged.** Word limits, one-sentence fields, no question marks, no dashes, no "not … but", no
  spelled-out quantities, nothing about race, ethnicity or religion, no listing-ad hype words, and no crime wording
  except the icon point "Among the safest places on the list." (lowest tenth by violent rate among the neighborhoods
  shown, never in a paragraph, never where no rate is published; see "After independent check 5").

### What is not machine-checked

- A metaphor with no marker word ("a harbor of calm") passes. The figure-of-speech check only counts markers ("like
  a", "as if", "steps from", "around the corner").
- An unclear pronoun ("it", "that" with nothing to point to) passes. Subject clarity needs a human read.
- Whether a paraphrase of residents is fair. The checker proves the quotes exist and their positive / mixed / negative
  counts have not changed. The paraphrases were carried over from the previous writer's reading of the excerpts and
  reworded plainly; they were not re-read against the excerpts in the copy edit.
- Adjectives without a hidden test. Most "close", "large", "quiet", "few" carry one; a few general ones ("a practical
  choice", "a small harbor town") do not.

### Limits that were relaxed, and why

The earlier form-letter limits pushed the writing toward forced variety, which is where several of the odd lines came
from (five wordings were required for each subhead, four for each point). They are now: at most 8 leads opening with
the same three words (was 3); no run of six words in more than a quarter of the leads (was a tenth); 3 wordings per
subhead condition, each on at most 12% of the neighborhoods (was 5 and 6%); 1 wording per point (was 4); 3 to 6 points
(was 4 to 6). The `close:` tag on each neighborhood block is gone; the checker still limits leads that end on the
drive to a third.

## Weak spots today

1. **Thin neighborhoods.** 46 of the 104 neighborhoods with anything shown have a single apartment. Their text describes that apartment's
   surroundings, and their catch is usually "Only 1 apartment is listed here, and it needs a call to confirm."
   The data supports nothing more distinctive for many of them (Madison, Midwood, Flatlands, Plainfield, Trumbull,
   East New York (North), Flatbush (West)-Ditmas Park).
2. **The scene repeats the points.** A neighborhood's restaurant count and supermarket distance can appear both as an
   icon point and in the `scene`, which sits in a separate collapsed row. A point is skipped only when the lead gives
   the same figure.
3. **Section subheads still repeat** across neighborhoods (the commonest is on about 15 of 133). They are plain
   statements of what the headline means for her, so this reads as consistency, but they are not individual writing.
4. **Named parks** are used only where the commonest park name among a neighborhood's buildings is plainly a park
   (Forest Park, Shore Road Park, Liberty State Park, Freshkills Park, Fort Tryon Park, Highbridge Park, Harrison
   Riverfront Park, Barbour Pond Park, Watsessing Park, Flushing Meadows-Corona Park), each behind a test on the name.
5. **Census claims at experience level** ("most households in these neighborhoods do without a car", "houses and
   lawns") rest on the median neighborhood of the experience in `data/lifestyle_groups.csv`, which includes
   neighborhoods with nothing shown. They are hidden tests, never printed as numbers.
6. **"Residents say" is almost entirely one review site** (Niche).
7. **A rule's summary is quoted, not its legal text.**

## Out of scope, reported to the owner (not edited)

- Since fixed: `data/reference/realtor_lines.csv` (building and apartment lines) carried what this edit removed here
  ("under your cap", "all in" unexplained, "net-effective", "we" as narrator, "unit", "Where the car sleeps", template
  seams such as "Then the practical side:"). `scripts/realtor_lines.py` now composes those lines to the same standard,
  with the guards of `check_scene_text.py` (run by `scripts/test_realtor_lines.py`); `scripts/verify_all.py` checks that its two tables hold exactly the
  page's apartments and buildings.
- Page template wording: "green space a 8-minute walk", "A typical place is 788 sq ft", "1 car thefts per 1,000",
  "A studio, size not known yet,, floor not known yet."
- "By mail they are typically $27.10 a round trip" is the same figure on three experiences because
  `toll_round_trip_mail` is missing for many units (27 of 63 have it in Fresh-Start), so the median is taken over a
  different, smaller set than the E-ZPass median beside it; in Room-to-Breathe it comes out below the E-ZPass figure.


## After independent check 4 (2026-11-16)

What the check found in this text, the cause, and the rule that now stops it. Each rule is in
`scripts/check_scene_text.py` unless another file is named, and each has a test or a re-run condition.

| Defect | Cause | What changed | The guard |
|---|---|---|---|
| D6: 12 neighborhoods said the dog park was miles away while their only building has its own | the builder read `dog_park_m` (the public dog park) and never a building's `dog_amenities` | `{own_dog}`, `{dog_any}`, `{owndog}`; an icon point "The building has its own dog area" / "Every building here ..." / "Some buildings here have their own dog area"; every hand-written dog-park complaint is conditional on no shown building listing a dog amenity; the same for garages (`{own_garage}`, `{owngarage}`) | `check_shown`: every building has one -> the text says so and names a dog park only as the public one; some have one (or list a dog amenity of unnamed kind) -> the distance is never the catch; "No building here has a dog park" needs none to; every building has a garage -> street parking comes with "the building has its own garage", never with "look for a garage" |
| D16: text and "At a glance" described the area profile, not the shown apartments | the checker required the `traits` | door-distance tokens read the shown buildings; `glance_json`; scope words (`{door}`, the first `{w10}`): "from the door" for one building, "most buildings here" for several | `check_strip` refuses any other source for `DOOR_FIELDS`; `main()` recomputes `glance_json`; `check_shown` wants "most buildings here" where several buildings are shown and forbids it where one is |
| D11, D7: tiny experiences generalised ("typical" from one apartment, "33 percent", "5 minutes away" for an apartment 31 minutes away; "almost no restaurants" above a Fairfield card with 8) | medians and shares of three rows written as tendencies | an experience with fewer than 8 apartments uses its `@small` draft: it names its neighborhoods and gives each one's figures | `check_experience`: no "typical", "percent", "most", "usually", "many" under 8 apartments; every neighborhood named; every claim tested against every neighborhood shown |
| D12: "close to your parents" over an experience with 29 of 81 apartments in Newark; "usually no tolls" at 53% | one median for two groups | the split tokens; "Most of these apartments are in ..., within about 30 minutes; the Newark ones are about 47 minutes away, with a toll" | `EXP_CLAIMS`: a claim holds for 75% of the apartments and no neighborhood contradicts it, or it names the exceptions, or it is limited to named places ("From Brooklyn and Queens ..."), or it says "most" and holds for 60% |
| D12: "From Jamaica ... about 3 minutes. The train and bus take about 65 minutes" | a named neighborhood's figure beside the experience's median | the sentence is gone; each figure names whose it is | `check_experience` (pairs) |
| D25: "The apartment in East Brunswick is large" with 8 shown | drafts written when one apartment was shown | singular and plural alternatives on `{pg_n}`; the plural is tested on the smallest apartment | `check_shown`: "The apartment" needs 1 shown, "the apartments" 2, "typical" 3 |
| D26: "Compared to staying in Queens" on Queens neighborhoods | subhead wordings compared with a place | every wording now compares with "a typical Queens apartment" | `STALE` |
| D15: an unlisted conceit, "not checked again" and "No building here has a dog park" passed | the conceit guard was a list of cut phrases; nothing read the published text | `AGENCY`; `STALE`; `scripts/check_published_text.py` | `scripts/test_check_published_text.py` plants each example |

Two more rules of `check_shown`, added while the final data was read: with one building shown the text says "the
building", never "each building" or "look for a building with ..." (`{eachb}`, `{everyb}`); and "the apartments are
in new buildings" may not rest on the area's census profile (say "much of the housing around here is new").

`glance_json` is computed here from the shown BUILDINGS (one vote per building). The pipeline's
`neighborhoods[].shown_figures` are now medians over the shown buildings too (`figures_over`: "shown buildings (the
median building)"), so the two agree. A dog area in this text is a dog park or dog run only, read from the
pipeline's structured field `amenities.dog_park_or_run` (`own_dog_area` in `check_scene_text.py`; it falls back to the
words of `dog_amenities` only for page data written before the field existed). A pet spa or dog wash
(`amenities.pet_spa_or_wash`) is not a dog area, but any dog amenity keeps the distance to a public dog park from
being the catch (`dog_amenity_any`). The distances in `glance_json` carry the unit "meters".

### The conceit guard, and its limits

`AGENCY` flags a sentence in which a thing is the grammatical subject of a verb of intention or speech. It is a
noun list (`THING_NOUNS`: lawn, street, park, town, building, garage, river, price, rent, morning ...) followed, with
at most one adverb between, by a verb list (`INTENT_VERBS`: keep, tell, know, want, ask, reward, pay, greet, wait,
sleep, speak, promise, forgive, whisper, welcome, tuck ...), present or past. An imperative after the noun
("..., so ask the office") is let through.

It does not see: a noun that is not on the list; a verb that does not directly follow the noun ("a town that
welcomes dogs", "the town, people say, never sleeps"); verbs with an everyday use for a thing, which are left off on
purpose (has, is, offers, lists, costs, takes, needs, allows, bans, restricts); a metaphor with no such verb. Add a
noun or a verb when a new conceit is cut.

### What `check_published_text.py` does

It reads `site/data.json` only. For experiences and neighborhoods the published fields must equal their row in the
scene CSVs and pass `check_row` again as published. For apartments and buildings the published text must equal what
`realtor_lines.py` writes from the same data (regenerated in memory), pass the guards of `test_realtor_lines.py`,
contain no number that is not a field of the object, and pass a claims audit: a fixed list of patterns, each compared
with the exact field it rests on (pool, gym, garage, covered parking, lot, parking included, doorman, concierge,
staffed front desk, own dog area, washer and dryer, laundry in the apartment, lounge, dogs allowed, elevator, "the
only building of N with ...", "the lowest-priced / largest / highest of the N apartments", "N apartments are listed",
the distances and the year built). Neighborhood sentences are compared with the buildings shown (distances, "no
bars", "no restaurants", minutes to her parents, tolls, "every building here has ...") and with those buildings'
own published text. The pipeline's own strings (`confirm`, `disclosures`, `tour_questions`, receipt notes,
`meta.notes`) get the vocabulary and stale-wording rules only and are listed under the owner "pipeline";
`--template` lists banned constructions in `site/index.html`.

Limits: the claims audit sees only its patterns; a wrong figure that equals another field of the same object passes
the number rule; resident quotes, outside descriptions, rule summaries and listing offer text are other people's
words and are not read.

### The building and apartment lines (`scripts/realtor_lines.py`)

- `desk_kind`: "doorman" is said only when the doorman amenity is set and its source text does not name something
  else. A source that says "Concierge" gives "The building has a concierge desk."; "24hr concierge" gives "A
  concierge is available 24 hours a day."; "attended lobby" gives "The lobby is attended."; "virtual doorman" gives
  nothing. A separate `amenities.concierge` field, if the pipeline adds one, is read the same way.
- `laundry_kind`: "washer and dryer" only where the source names both; otherwise "laundry in the apartment"; nothing
  where the in-unit flag sits beside a text that says "On-site laundry", "W/D hookup" or "not in unit".
- `garage_mixed`: where a garage's own text also names a surface lot or outdoor spaces, the building "has a garage"
  and the text does not say "you would park in the garage".
- The catch leads with an income or credit-score requirement where the listing sets one, in the listing's own figure
  ("The listing sets an income requirement: $130,000 yearly."); a furnished apartment is a catch too (D8).
- The open item's reason is read from `confirm.code` where the page data has it.
- A parking fee whose basis is a resident's review is not stated as the building's price.
- "up to 2 months free" stays "up to" (D20; `rent.free_text`). "Before you choose a puppy" and "choose the breed with care" are gone
  (D25).

### What the data still cannot support

1. Resolved: `dog_amenities` used to be the bare word "yes" for 11 shown buildings. The pipeline now derives dog
   park / dog run / pet spa / dog wash from each source's words (`amenities.dog_park_or_run`, `pet_spa_or_wash`,
   `dog_amenity_unspecified`), and no shown building is unspecified. The wording "The building lists a dog amenity,
   so ask what it is" stays in the library for a building whose source names none of them, and is unused today.
2. A building's own measures of water, beach and park area are not in `site/data.json`; they are read from
   `data/master_buildings.csv` by building id.
3. "A newer building" (Fresh-Start) rests on the census median year built of the area, because `year_built` is
   published for about half of the shown buildings.
4. "From most buildings here" is the median building. Where the buildings of a neighborhood differ a great deal
   (Stamford: 1 to 30 restaurants), the range is in `glance_json` and is not said in the text.
5. A doorman known only "per tenant reviews" (1 building) and a doorman flag whose source text is the bare word "yes"
   (11 buildings) are still called a doorman.
6. Sizes are published for about half of the Old-Neighborhood apartments, so nothing there is claimed about size.

## Rent and total (2026-11-16, after the page's "rent versus total" change)

The page shows two labelled prices wherever a price appears: "Rent" (the rent line of an apartment's cost lines:
what the listing asks) and "Total with utilities and fees" (`all_in`: rent plus required fees, pet rent, parking where
known and estimated electricity, gas and internet). The text uses the same two names.

- A total is "about $X a month with utilities and fees" on first mention in a text, "about $X a month" after.
  Experience and neighborhood totals are the figure strip's (`{p_allin}`, `{pg_mid}`, `{pg_lo}`), to the nearest $10.
- An apartment's line gives both prices in its price sentence where the rent is plainly what the listing asks
  (`rent_asked` in `realtor_lines.py`: the rent line is the listed rent, not a 12-month or after-offer price, and no
  offer, asterisk or call hangs on it): "The rent is $2,345, about $2,670 a month with utilities and fees." The rent
  is exact to the dollar, as the page prints it. Otherwise the line gives the total alone, and the catch asks about
  the rent.
- "Everything included" and "all-in" / "all in" are banned in every published text (`VOCAB` in
  `check_scene_text.py`, `EXTRA` in `test_realtor_lines.py`, and through them `check_published_text.py`, which also
  applies them to the pipeline's own strings).
- `check_published_text.py` adds a PRICE check on apartments: a total said in the text must be `all_in` rounded to
  $10 with "about", and a rent said in the text must be the rent line to the dollar.
- No neighborhood or experience text states a typical rent today: the page data has no rent median on those objects
  (the page computes it in the browser). If one is added, word it "the typical rent is about $X".

## After independent check 5 (2026-11-16)

The check (`docs/INDEPENDENT_CHECK_5.md`) found every number right and a small set of statements resting on a field
that was wrong or narrower than the words. The pipeline corrected the fields (`docs/REPAIRS_AFTER_INDEPENDENT_CHECK_5.md`);
this is what the text system changed so that the words follow them, and the rule that now stops each fault.

| Finding | Cause | What changed | The guard |
|---|---|---|---|
| N1, D18: "garage" for an open lot; The George's off-site deck written as "the building's lot" | the text read the head of `parking.type` and knew four kinds | `realtor_lines.parking_facts` reads `parking.kind`, `included_kind`, `fee`, `fee_kind`, `optional_kinds`: the kind of the space she would park in (garage, covered, lot, off-street, assigned, off-site, street, unnamed), whether it is included, its own fee, and the other kind offered at a cost. `parking_point` writes the one sentence: "A free open lot; garage spaces are $125 a month.", "Parking is in an off-site deck, $185 a month.", "An assigned space is included; the listing does not say whether it is a garage or a lot.", "Free off-street parking.", "The listing mentions parking without saying what kind: ask." Subheads, About sentences, icon points and warnings each have a case per kind. A fee whose `fee_kind` is another kind is never attached | `check_published_text.parking_claims` reads every parking sentence clause by clause against the structured fields (kind, included, fee, the extra and its fee), also in sentences that say "not published"; `test_realtor_lines` reads every shown building |
| N8: garage counts | the same head | `check_scene_text.parking_head` calls `parking_facts`; "At a glance" counts the buildings whose space is a garage | `audit_glance` compares the count with the buildings and with `shown_figures.buildings_with_garage` |
| N3: "miles to a train station" beside a PATH, subway or light rail stop | one word for every station | `{thestation}`, `{astation}`, `{thetrain}`; building text "the Journal Square PATH station", "the Elmhurst Av subway station", "the Port Imperial light rail stop"; `glance_json` `train_station` carries `kind`, `kinds`, `station`, `stations`, the distance in miles, and the label "to PATH (Journal Square)" | `check_station_words` (neighborhoods), `station_claims` (buildings), `EXP_CLAIMS` "a train station" (experiences), `audit_glance` |
| N9: one toll figure where the buildings differ (Newark $24 to $43) | the median | `{tollcost}`, `{tollshort}`, the range tokens | `check_toll_range`, the toll rule of `check_experience`, the range check of `audit_hood_claims` |
| N15: "no bars" beside "few bars"; "nothing here is within walking distance" beside "2 cafés" | two wordings with different tests | `{fewbars}`; Westport's catch rewritten | `check_quantities`: "no X" needs 0, "almost no X" 0 or 1, "few X" 1 to 5, "nothing is within walking distance" no restaurants, bars or cafés, each against the median of the buildings shown; two sentences that disagree are named |
| N16: "9 cafés are close too, ..." opening a paragraph; "The building lists a dog amenity, so ask what it is." for a pet spa; "The listing could not be fully confirmed." | a sentence written to follow another field; the kind of amenity not read; a catch with no reason | rewritten; `{pet_spa}` points and subheads ("The building has a pet spa or dog wash, and no dog area."); catch family `confirm:listing permit` | `dangling()` in the checker and `CONTINUES` in the builder (also after a dropped optional sentence) |
| N17: "1 of the 4 buildings here have their own dog area" | a fixed plural | the label follows the count | `agreement()` on every text and every "At a glance" label |
| N6: "washer and dryer" on a listing site's tag, or where only a washer is named | `laundry_kind` read the label | `laundry_mode`: `in_unit_appliances` = washer gives "a washer in the apartment ... no dryer named"; `in_unit_laundry_basis` = listing_site_appliance_list gives "The listing shows a washer and dryer in the apartment." Experience points say "N percent list laundry in the apartment" | `laundry_claims` |
| N5: a dog weight limit no page states | field | the pipeline removed it; the text prints `dog.weight_limit_lb` only | `dog_weight_claims` |
| D27, N13: "This is also one of the safest spots on the whole list." in 15 paragraphs | lowest fifth, appended to the daily-life paragraph | the sentence is gone from every paragraph; the icon point "Among the safest places on the list." for `violent_pctile <= 0.1` (6 neighborhoods today) | `check_row`: the wording only as that icon point, only with the test, only where `safety.status` is published and the neighborhood is in the lowest tenth; any other "safe" wording fails as before |
| Guard gap: five edits planted in `realtor_lines.csv` and `building_about.csv` passed | the audit compared the generator with the page only | `audit_tables`: the two tables on disk must hold exactly the rows and words `realtor_lines.build()` / `build_buildings()` write from `site/data.json` | `test_check_published_text.RealtorTables` plants the five edits, an edited icon point, a missing row and an extra row |

### Parking wording, by what the fields say

| `parking.kind` (the included kind where a space is included) | included | fee published | fee not published |
|---|---|---|---|
| garage | A garage space is included in the rent. | Garage parking costs $150 a month. | Garage parking, with the fee not published. |
| covered | A covered parking space is included in the rent. | Covered parking costs $75 a month. | Covered parking, with the fee not published. |
| open_lot | A free open lot. | A space in the building's lot costs $75 a month. | A parking lot, with the fee not published. |
| assigned_lot, gated_lot | An assigned space in an open lot is included. | ... costs $65 a month. | ..., with the fee not published. |
| off_street | Free off-street parking. | Off-street parking costs $N a month. | Off-street parking, with the fee not published. |
| assigned | An assigned space is included; the listing does not say whether it is a garage or a lot. | An assigned space costs $N a month; the listing does not say where. | An assigned space, with its kind and fee not published. |
| offsite | | Parking is in an off-site deck, $185 a month. ("off-site, not at the building" where the source names no deck) | Parking is off-site, not at the building, with the fee not published. |
| street | The only parking named is on the street. | | |
| unspecified | A parking space is included; the listing does not say what kind. | Parking of an unnamed kind costs $N a month. | The listing mentions parking without saying what kind: ask. |

One other kind is named after a semicolon, a garage before covered parking before the lots: "; garage spaces are
$125 a month", or "; garage spaces cost extra" where its fee is not published (a subhead, which carries no numbers,
always says "cost extra"). The clause is left off when the point would pass 14 words. Off-site and street parking
name no other kind.

### What the page must do to print these fields

- `at_a_glance[]` item `train_station`: `kind` (train, subway, PATH, light rail, or mixed), `station` (null where
  the shown buildings measure to different stations), `text` in miles, `label` ready to print. The template's
  `stationLabel` already builds "to PATH (Journal Square)" from `kind` and `station`; for `kind: "mixed"` it must
  print the label as given ("to the nearest station ..."). Where the nearest station is not commuter rail the item
  also has `commuter_station_m`, `commuter_station_text`, `commuter_station_label`.
- The safety point is an ordinary icon point (`icon: "heart"`). The template's `calm()` removes any text that
  contains "safest", and its badge still marks the lowest fifth: the badge rule must become the lowest tenth (or
  the badge must give way to the point), and the point must be let through.
- A building's parking: the About sentence, the icon point and `headlines.parking.subhead` now say the kind. The
  template's own line ("Garage parking, no monthly charge") must come from `parking.summary` or the same fields.

### What the data still cannot support (independent check 5)

1. Whether an "assigned space", or parking of unnamed kind, is a garage or a lot (11 buildings): the text asks.
2. A walking time to a station. Only the distance is in the data, so the station is given in miles.
3. Which station matters for reaching her parents. The text names the nearest station of any kind; the commuter
   station's distance is in `glance_json` and is not put in a sentence.
4. Where the shown buildings of one neighborhood measure to stations of different kinds (Newark, Englewood,
   Flushing-Willets Point) the text says "the nearest station".
5. N27, the beach 0.3 miles from 9949 Shore Rd in Bay Ridge: `beach_m` is the map's nearest beach and no source
   confirms a usable beach there. The sentence is unchanged.
6. A dryer where only a washer is named, and any machine named only on a listing site's appliance list.
7. The toll range of an experience is the lowest and highest toll among its apartments; the text does not say how
   many apartments sit at each end.
