# Scene text notes

The words on the experience pages and the neighborhood pages: how they are written, built and checked.
Rewritten 2026-11-16 after the copy edit. It describes the system as it stands; the earlier history is in git
(`git log -- docs/SCENE_TEXT_NOTES.md`).

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
| `data/reference/scene_text_neighborhoods.csv` | One row per neighborhood drafted that is still in `data/lifestyle_groups.csv` (133 today; 115 are in `site/data.json`, 104 of them with apartments shown). |

`scripts/realtor_lines.py` and `data/reference/realtor_lines.csv` (the building and apartment lines) are a separate
system with a separate owner. They were not touched by the copy edit; see "Out of scope" below.

After any data rerun:

    python3 scripts/page_data_extras.py && python3 scripts/build_scene_text.py && python3 scripts/check_scene_text.py

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
| `{rest}` `{bars}` `{cafes}` `{parkwalk}` `{parkha}` `{dogpark}` `{super}` `{water}` (neighborhood) | `neighborhoods[].traits` | the page's "At a glance" row prints the traits |
| `{u_garage}` `{u_laundry}` `{u_pool}` `{u_gym}` `{u_bars}` `{u_cafes}` `{u_rest1600}` `{u_dogpark}` `{u_super}` | medians or shares over the experience's shown units | nothing else on the page states these |
| census shares, `{station}`, `{beach}`, `{tj}`, `{vet}` | `data/lifestyle_groups.csv` or the shown units | not on the strip |
| tolls | always worded "about $N round trip with a New York E-ZPass" | fixed wording |

Prices in sentences are rounded to the nearest $10 with "about"; minutes are whole. For a neighborhood with nothing
shown, every token falls back to `data/lifestyle_groups.csv`.

Before 2026-11-16 the restaurant, park and dog-park figures of a neighborhood were medians over its shown units. They
then differed from "At a glance" on the same page (Bay Ridge: 14 restaurants in the text, 29 beside it). They now read
the traits, and the checker refuses the old source.

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

- `data/reference/realtor_lines.csv` (building and apartment lines) still carries what this edit removed here: "under
  your cap", "all in" unexplained, "net-effective", "we" as narrator, "unit", "Where the car sleeps", and template
  seams ("Then the practical side:", "Then there is 554 square feet.", "Count on about …"). It also had 489 rows
  against 491 apartments on the page at the time of writing.
- Page template wording: "green space a 8-minute walk", "A typical place is 788 sq ft", "1 car thefts per 1,000",
  "A studio, size not known yet,, floor not known yet."
- "By mail they are typically $27.10 a round trip" is the same figure on three experiences because
  `toll_round_trip_mail` is missing for many units (27 of 63 have it in Fresh-Start), so the median is taken over a
  different, smaller set than the E-ZPass median beside it; in Room-to-Breathe it comes out below the E-ZPass figure.
