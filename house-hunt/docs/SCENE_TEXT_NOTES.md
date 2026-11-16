# Scene text notes

The words on the experience pages and the neighborhood pages: how they are written, built and checked.
Rewritten 2026-11-16 after the copy edit, and extended the same day after independent check 4
(`docs/INDEPENDENT_CHECK_4.md`; the section "After independent check 4" below says what changed and why). It
describes the system as it stands; the earlier history is in git (`git log -- docs/SCENE_TEXT_NOTES.md`).

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
`scripts/test_realtor_lines.py` and run over every building and apartment text.

After any data rerun (the order matters: the text is built from the page data, attached to it, then audited there):

    python3 scripts/page_data_extras.py && python3 scripts/build_scene_text.py && python3 scripts/check_scene_text.py \
      && python3 scripts/realtor_lines.py && python3 scripts/test_realtor_lines.py \
      && python3 scripts/page_data_extras.py && python3 scripts/check_published_text.py

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
"building", "neighborhood", "experience". "All-in" is written "a month, everything included". Residents are
paraphrased as "Residents say / like / praise / call / wish …", never quoted, and the block then needs a `voices:`
line naming the themes. A number quoted from a local rule needs a `rules:` line.

## Draft syntax

- `{alias}` prints a measured value; `{alias:how}` rounds it another way. A number is never typed.
- `{!alias OP value}` prints nothing; the sentence is recorded as resting on that test, and the checker re-runs it.
  Every adjective that the data could contradict carries one ("a large park{!parkha>=20}").
- `[[ … ]]` is optional text, dropped whole when a value inside is missing or a test inside fails. Two in a row give
  either/or wording.
- `{w10}` and `{mile}` are the fixed wordings for the 800 m and 1,600 m radii.
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
| tolls | always worded "about $N round trip with a New York E-ZPass" | fixed wording |

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
  - Vocabulary: no "Mom and Dad" in a sentence, no "unit", no "place" for an apartment, no "… Year", no bare "all-in",
    no project terms (ranked, scorecard, verified, live check, net-effective, gate, asterisk, cap, ceiling), no "we",
    American spelling.
  - Headline fit: `promise` and `good_for_her` fit whole in 64 characters.
- **Leads** (`check_leads`). A neighborhood's first sentence may not open on a statistic that more than a third of the
  neighborhoods in its experience also open on.
- **House style, unchanged.** Word limits, one-sentence fields, no question marks, no dashes, no "not … but", no
  spelled-out quantities, nothing about race, ethnicity or religion, no listing-ad hype words, and no crime wording
  except "one of the safest spots on the whole list", which needs a test (lowest fifth by violent rate on the page).

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
- "up to 2 months free" stays "up to" (D20). "Before you choose a puppy" and "choose the breed with care" are gone
  (D25).

### What the data still cannot support

1. `dog_amenities` is the bare word "yes" for 11 shown buildings (Avalon Maplewood, Avalon Wayne, The Leaf, Continuum
   and others). The text cannot say what the amenity is, so it says "The building lists a dog amenity, so ask what
   it is" and does not complain about the distance to a dog park.
2. A building's own measures of water, beach and park area are not in `site/data.json`; they are read from
   `data/master_buildings.csv` by building id.
3. "A newer building" (Fresh-Start) rests on the census median year built of the area, because `year_built` is
   published for about half of the shown buildings.
4. "From most buildings here" is the median building. Where the buildings of a neighborhood differ a great deal
   (Stamford: 1 to 30 restaurants), the range is in `glance_json` and is not said in the text.
5. A doorman known only "per tenant reviews" (1 building) and a doorman flag whose source text is the bare word "yes"
   (11 buildings) are still called a doorman.
6. Sizes are published for about half of the Old-Neighborhood apartments, so nothing there is claimed about size.
