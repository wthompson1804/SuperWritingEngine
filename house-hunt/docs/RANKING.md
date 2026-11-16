# Ranking (approved by Will, 2026-11-15) — implemented in `scripts/rank.py`

**Layer 1, universal value (0-100).** Six parts, each the unit's percentile across all kept units:
safety 25 (violent, property and vehicle-theft rates; car crime within 250 m where published), cost 15 (all-in),
building 20 (elevator stated, in-unit laundry, doorman, controlled access, gym, package room, outdoor space, age),
car 15 (garage or gated > covered > lot > street), space 15 (sq ft), dog 10 (walk to green, dog park, pet rent,
dog amenities). An unknown fact scores at the 25th percentile and becomes a tour question.

**Layer 2, the year's promise.** Walk-Everywhere: restaurants, bars, cafés, grocery on foot. Old-Neighborhood:
grocery on foot, transit to her parents. Fresh-Start: building amenities, water distance, newcomer share.
Little-City: restaurants nearby, train station distance. Room-to-Breathe: sq ft per dollar. Quiet-Street: low
violent crime, distance from the motorway, parking.
**Rank score = 0.7 × universal + 0.3 × promise + pool bump (+3 any pool, +6 indoor pool).**

**Selection per neighborhood.** Highest rank score first; at most 2 units per building; units beaten or tied on all
six parts by another unit in the neighborhood go last. Top 15 are candidates for the evidence pass; avoid cards
(up to 5) come out of those; the best 10 of the rest are shown.

**Layer 3, comparing lives.** No single cross-life score. Each unit carries two standings per part (within its year;
against everything). `data/group_exchange.csv` holds each year's medians and its difference from "near home"
(units within a 15-minute drive of Jamaica). These run in the background; the page shows them only on demand.

**Safety gate before ranking:** neighborhoods with violent or property crime above Jamaica's precinct are cut.

## Five-point spectrum against staying in Queens (Will, 2026-11-15)

The compare stage must be easy to read: every measure is placed on five points with **Queens in the centre**
(3 = about the same as the median passing unit in Queens; 1-2 = worse for her; 4-5 = better for her; distance follows the same rule:
**closer to her parents is better**, per Will; this replaces the UX brief's "no red or green on distance"). Bands are in real units and are
stored in `data/reference/queens_spectrum_definition.csv`; per-unit values are the `vsq_*` columns of
`data/ranked_units.csv` (with `vsq_*_diff` holding the plain difference, e.g. +120 sq ft). The underlying
calculations stay in the background and are shown only when she asks how a point was reached.

## Version 2 (Will, 2026-11-15: "use many more variables; drop anything sketchy") — current

Supersedes the weights and part definitions above; the 70/30 split, pool bump, selection rule and Queens spectrum stay.

**Listing confidence, applied before ranking.** `sketchy` listings are excluded (`data/excluded_sketchy.csv`):
60+ days old, no unit and no building named, thin syndicated feed, conflicting dog policy, all-in under 60% of the
neighborhood median, or two or more inferred gate facts. `one_inferred` listings stay with a 0.97 certainty factor
and a `to_confirm` note; that fact must be confirmed in the evidence pass before the unit is shown. `clean` = every
gate fact stated on the page.

**Universal value (weights sum to 100).** Distance and daily life were added; the original six keep their proportions.

| Part | Weight | Variables (percentiles across all kept units; unknown = 25th percentile) |
|---|---|---|
| Safety | 22 | violent rate 35, property rate 15, vehicle-theft rate 15, car crime within 250 m (NYC) 15, building security features 20 |
| Building | 16 | security features (24h doorman 3, doorman 2, controlled entry 2.5, package room 1) 40; comfort (in-unit laundry 2.5, lounge or coworking 1.5, gym 1, outdoor space 1, elevator stated 1, balconies 0.5) 45; year built 15 |
| Cost | 12 | all-in 85, how many cost lines are stated rather than estimated 15 |
| Car | 12 | parking type 50, vehicle-theft rate 15, car crime nearby 15, parking fee 10, surface parking nearby 10 |
| Space | 12 | sq ft 75, a separate bedroom 25 |
| Distance | 10 | drive to her parents 60, transit 25, tolls 15 (closer is better) |
| Dog | 8 | walk to green 25, park area 15, dog park 15, vets 10, dog amenities in the building 10, weight limit stated ≥ 40 lb 10, woods 5, pet shops 5, pet rent 5 |
| Daily life | 8 | supermarket distance 25, cafés in walking distance 20, gyms 15, distance from the motorway 15, farmers' market 10, corner stores 10, library 5 |

**The year's promise (30%).**
- Walk-Everywhere: restaurants, bars, cafés, shops of any kind, street-grid density, cinemas and theatres, bookshops.
- Old-Neighborhood: corner stores, hair and beauty shops (main-street signal), restaurants, laundromats, library, playgrounds, transit to her parents.
- Fresh-Start: building amenities, distance to water, newcomer share, age 25-34 share, building year, gyms, bars within a mile.
- Little-City: restaurants, train station distance, cinemas and theatres, shops, farmers' market, bars within a mile.
- Room-to-Breathe: sq ft per dollar, a separate bedroom, park area, parking, woods.
- Quiet-Street: violent and property rates, distance from the motorway, parking, woods, detached-house share.

`scripts/rank_v1_backup.py` keeps version 1.

## After the independent check (2026-11-15) — see `docs/REPAIRS_AFTER_INDEPENDENT_CHECK.md`

**Gate facts and what counts as settled.**
- Elevator: confirmed in the evidence pass, stated on the listing or amenities page, or an official record. A harvester's or checker's
  inference ("6+ floors") is `inferred` and is an open fact.
- Floor: confirmed, or stated on the page. A floor read from a simple unit label ("4F", "305") that comes out at 3 or higher is accepted,
  marked "read from the unit number", with the tour question "Confirm the floor". Any other inferred floor (floor 2, or a label with a
  separator, a building prefix or four digits) and an unknown floor are open facts.
- Dogs: allowed must be stated or confirmed. A size word ("small dogs", or "small" in a size field) with no pound figure **passes** (owner,
  2026-11-15: her dog is at most 25 lb): the unit carries the note "page says small dogs; no weight number" and the tour question "Confirm the
  dog weight limit in pounds". A stated limit under 25 lb, no dogs, and service animals only still exclude. A policy that conflicts between
  two aggregators is an open fact; the building's own site or its manager's page outranks an aggregator.
- One open fact: ranked with the 0.97 certainty factor and listed in `data/needs_confirmation.csv` with the question. Two or more: sketchy, excluded.

**Shown (owner, 2026-11-15).** Not an avoid building, and at most **one** thing still open, counting the three gate facts and a missing live
check alike. A unit with one open item is shown with an asterisk (`confirm_asterisk`, `confirm_what`, `confirm_why`). A unit with one open gate
fact and no live check waits in `data/needs_live_check.csv`. At most 2 per building (counted on `building_id`, duplicates of a unit removed
first), best 10 per neighborhood. `data/needs_confirmation.csv` is the phone-call list. `scripts/check_registry.py` fails the run if a shown
unit breaks any of these rules.

**Scoring changes.** Pool, doorman and the other amenity tests reject negatives and near-misses ("Pool table", "none listed", "no doorman
stated"; a virtual doorman counts as controlled access only). A confirmed "no weight limit" scores as the best weight policy. The
"cost lines stated" variable now counts the lines of the cost receipt that are stated rather than estimated or unknown.

## Neighborhood order inside an experience (2026-11-16)

Owner: show the top three neighborhoods of each experience first, the rest on "show more" in descending order; the same for
places inside a neighborhood (top three, then more). "Years" are called "experiences" in the interface; internal keys are unchanged.

Neighborhood score = mean rank score of the neighborhood's three best shown places. A neighborhood with fewer than three
shown places loses 2 points per missing place. Ties break on the neighborhood id. Computed in `scripts/page_data_extras.py`
(`experience_score`, `rank_in_experience`), after the unit ranking, so it uses the same weights as the places.

## After the second independent check (2026-11-16) — see `docs/REPAIRS_AFTER_INDEPENDENT_CHECK_2.md`

**Reviewed verdicts.** `data/evidence/review_verdicts.csv` (remove / asterisk / ok per unit, with the reason and the evidence
quote). `remove` excludes the unit before ranking; `asterisk` adds that open item; `ok` adds nothing. A unit with no current
`ok` or `asterisk` verdict cannot be shown (`scripts/check_registry.py`). A verdict never closes a fact the rules leave open.

**Open items now counted** (one is an asterisk, two or more is sketchy): elevator; floor; dogs allowed; lease term (the listed
price is for more than 13 months, or only "the lowest over the lease terms"); cost near the cap (all-in of $2,900 or more with
pet rent, parking or required fees unknown); availability (a floor-plan row, or a reviewer's finding); listing (an evidence
warning about the listing, or a reviewer's finding); eligibility; condo rules; other. A missing live check is still the
separate item it was.

**What opens a gate fact that used to stand.** An evidence row marked `unconfirmed` with no confirmed row beside it (elevator,
dogs); a dog policy that does not name dogs as allowed ("upon approval", "case by case", small pets only); an elevator resting
on the city's record for a lot at another address, or one with no active elevator on file; a floor the evidence pass called
unknown, whatever the unit label reads as.

**Cost.** Where the listed price belongs to a lease longer than 13 months and the page gives the 12-month price, the all-in
cost and the cap use the 12-month price. `all_in_unknown_count` and `cap_margin` are on every unit.

**Selection order** is deterministic: neighborhood, dominated last, score, units seen live first, `listing_id`.

**Owner's changes later on 2026-11-16 (these replace the "open items" paragraph above).**
- Open gate facts that count toward "at most one": elevator; dogs allowed; whether the listing is real and available
  (availability, listing, eligibility). A missing live check is still its own item; a shown unit has at most one in all.
- Disclosures never count and never remove a unit: floor not published (unknown, or only read from the unit number: tour
  question "Floor not published: confirm it is above the ground floor"), lease term over 13 months, cost near the cap,
  condo rented by its owner, net-effective rent. They are listed per unit in `disclosures` (what, why, question) in
  `ranked_units.csv` and `site/data.json`.
- Still excluded on the floor: floor 1 or ground (confirmed, stated or read from the unit number), a checker's reading that
  the unit is probably or possibly on the ground floor, and a reviewer's verdict saying so.
- No cap of 10 per neighborhood: every showable, reviewed unit is shown in rank order, at most 2 per building, with
  `more_in_building` on each. A building with no evidence rows at all is not shown.

## Rules added 2026-11-16 (after the repair report's open decisions) — `scripts/build_master.py`, `scripts/rank.py`, tests in `scripts/test_rules.py`

**Staleness (rule; before this it was caught only by the verdict review).** `build_master.py` reads a page's modification date
where the data has one: the unit's own live-check note ("page last modified 2026-09-03", "unit record updated ..."), else a
`listing_last_modified` / `listing_updated_at` evidence fact read on the same site as the unit's listing (`page_modified_date`,
`page_modified_source`). Days are counted to the day the page was read (`parsers.staleness`).
- Page unchanged **more than 60 days** and no second site lists the unit, or an availability date **more than six months
  (183 days) old**: one open item, "listing" (`listing_stale = open`). Where a reviewer already wrote the same doubt up as
  "availability" it counts once.
- Page unchanged **more than six months (183 days)**: removed before ranking (`listing_stale = remove`,
  `excluded_by_confirmed_facts.csv`), second site or not.
- The latest date in the unit's own note wins, so a fresh unit record on an old building page is not stale. Where no date exists
  (most building-page rows) the rule says nothing and the verdict review remains the only check. A phone answer about
  availability clears it.

**Elevator stated on a listing site (one grading for all batches).** An elevator in a listing site's amenity list, tag or text is
basis `stated`, not `confirmed`, whether the evidence batch wrote the row as confirmed (batches 1, 2, 8, 9 ...) or unconfirmed
("amenity tag only", batches 10, 15). It settles the elevator unless a row says the building's own site omits it, that it is
"in select buildings", or the checker's reading goes against it; a reviewer's elevator asterisk also still stands. `confirmed` is
kept for the building's own or its manager's page. `elevator_aggregator_only = yes` marks every building whose only "yes"
sources are listing sites (no own page, no city record, no phone call). In New York City a lot classed D (elevator apartments) at
the listing's own address, with no zero on the device list, is entered as an official record beside the listing.

**Dog weight limit with no number.** "Weight restrictions apply", "a limit exists, pounds not published" and the like
(`parsers.dog_weight_unstated`) pass like "small dogs" and carry the disclosure "dog weight limit not published" with the tour
question "Confirm the dog weight limit in pounds".

**Overnight street parking (disclosure, never removes).** `data/reference/overnight_parking_towns.csv` is a reviewed table
(municipality, rule summary, hood ids, source URL, severity ban / permit / seasonal) filled by reading the local-rule rows; no
free text is parsed at run time. Where the unit's neighborhood is in it and the unit's parking is not confirmed at the building
(parking type street, or type unknown and no fee known), the unit carries the disclosure "Overnight street parking is restricted
here: confirm the building has a space, and its cost", with the rule's one-line summary and URL.

**Phone answers.** `data/evidence/call_answers.csv` (format in `docs/SHORTLIST_TOOLS.md`), when present, is the highest-precedence
source: basis `confirmed_by_phone`, source "phone call <called_at>". Elevator, dog weight limit (which also says dogs are
allowed), pet rent, parking fee and the total of required fees per building; floor, lease term, 12-month price and the move-in
date per unit ("gone" removes the unit; a date or "now" counts as seeing it live; a date after Dec 15 removes it). A fact
answered on the phone is no longer open, whatever an older evidence row or reviewer's asterisk said.

**Tolls.** A toll counts in the distance part only when every crossing on the route has a rate (`toll_complete`); all 792
buildings now do. Figures are New York E-ZPass, weekend off-peak; the Tolls by Mail figure (what an out-of-state tag pays at MTA
crossings) is carried beside it, and is "at least" where the route enters the Manhattan congestion zone (no mail rate found).

**Jersey City** is split into its neighborhoods (`docs/SUBCITY_SPLIT_PLAN.md`); the safety rule still uses the citywide police rate.

## After the third independent check (2026-11-16) — see `docs/REPAIRS_AFTER_INDEPENDENT_CHECK_3.md`

These replace the rules above where they differ. Tests: `scripts/test_rules.py` (`pure_4`, `data_4`, `page_3`).

**Elevator (owner's decision from the check's finding).** An elevator named in a listing site's amenity list is still
`stated`. Two exceptions make it an OPEN gate fact, with the asterisk "Confirm an elevator serves this apartment":
1. the building is in the reviewed table `data/reference/elevator_doubt.csv` (building_id, name, why, source): 15 rows, the
   14 doubtful low-rise or multi-building complexes the check named and 99 Bridge (added in the repair pass, from its own
   evidence rows);
2. by rule (`build_master.py: garden_style`, `parsers.multi_building_labels`): the elevator rests on listing sites only AND
   the unit labels read as a multi-building low complex AND no page or record gives a height of four floors or more. The
   labels count only when every labelled unit has a building part (`09-326`, `B9-309`, `K3-02`, `5201`), two or more
   buildings appear and no label reads above floor 3; for bare four-digit labels the floor digit must vary and no
   unit-on-floor number may exceed 40 (this keeps towers such as `1206` and floor-plus-three-digit labels such as `5158` out).
With a second open item (most often no live check) the unit is not shown. A phone answer settles it. Also: an unconfirmed
"the listing does not state an elevator" no longer keeps the elevator open where the city's record settles it (the listing's
own lot, an elevator class, an active passenger elevator on the device list).

**Cost (owner's decision; the cap stays on `all_in`).**
- Pet rent is certain (she is getting a dog). Where it is not published the line is an estimate, "pet rent (est.)": the
  median of the known pet rents, one value per building, of the buildings in the same state. Today $50 in all three states.
  It counts toward `all_in` and the $3,000 cap. The medians are taken over the buildings of the master table (those with a
  unit that passes the listing gates), not over the ranked buildings, because the ranked set depends on the cost gate; the
  two agree to within $10 in every state (a test checks it).
- Parking and required building fees stay unknown: nothing is estimated into `all_in`. `all_in_likely` = `all_in` + the
  median known parking fee (same state and same kind of parking where five or more buildings have a known fee, else the
  state, else all states; fees of $0 count) + the median known required fees of the state, for the lines that are not
  published. Figures and counts: `data/reference/cost_estimates.csv`.
- Where `all_in` ≤ $3,000 < `all_in_likely` the unit carries the disclosure "Could pass $3,000 once parking and fees are
  known", with both figures. This replaces "cost near the cap".
- A listed price that is a page's "total price" already contains the required fees: the fee line is $0 whatever fee text
  was parsed beside it. A fee named beside a total it is part of ("$90/mo (total price minus base price); $50 amenity fee
  named") is not added to it.
- Net-effective: the rent used is always the listed price (or the 12-month price of a longer lease). It is called
  net-effective only where a page or evidence row says the listed price is net-effective; a gross figure is given only then.
  Any other offer that could change what a month costs (free months not tied to the price, a credit, a gift card) is the
  disclosure "special offer" with the question "Special offer: ask what a normal month costs", and no gross is computed.

**Buildings.** Up to 8 shown units per building (`MAX_PER_BUILDING`; it was 2), in rank order by the same score. Candidate
and phone-call lists still take two per building. `site/data.json` has a `buildings` array and `building_ids` per
neighborhood, ordered by each building's best unit.

**Reviewed verdicts hold several rows per unit**, keyed on (listing_id, kind): `asterisk` for a gate kind (elevator, dogs,
not_available, unverified, wrong_building, restricted), `disclose` for a disclosure kind (lease_term, coop_condo, other,
floor), `remove`, or `ok`. Each gate row counts as an open gate fact (two: not shown); every disclosure row is listed.

**New rule-made open items and removals.** A checker's note that the price itself must be verified ("far below the area's
other listings") is the open item "listing". A condominium lot (city class R at the listing's own address, not a managed
rental building) or a listing typed condo carries the condo disclosure. A lease term named in the offer of a
net-effective price ("3 months free on 18 month leases") carries the lease-term disclosure. Sibling rule: where a reviewer
removed units of a building because their numbers read as first-floor units, every unit of that building with the same
label shape and the same digit in that place is removed. Staleness: a second site is a different host; the modification date
of a building page applies to every unit listed on that page; a unit seen "live" only on that same stale page is stale too.

**Experience and neighborhood figures** are computed over the shown units (medians and ranges over the same set); each
experience names its nearest and farthest neighborhood by drive time.

**Day moments: three levels, absolute thresholds (owner, 2026-11-16).** `moments.<key>.rating` is strong / mixed / weak, or
null where the data cannot say. No level holds more than about 60 percent of the shown places for any moment (tested).

| Moment (key) | Measure | Strong | Mixed | Weak |
|---|---|---|---|---|
| Morning with the dog (`wake`) | minutes on foot to the nearest green space | 3 or less | over 3, up to 10 | more than 10 |
| Work day at home (`work`) | size and a separate bedroom (null when the size is not published) | a separate bedroom and 700 sq ft or more | everything between | under 550 sq ft, or a studio under 600 sq ft |
| Evening out (`after`) | restaurants and bars within a 10-minute walk (800 m) | 15 or more restaurants and at least one bar | 4 or more restaurants | fewer than 4 restaurants |
| The car at night (`night`) | where the car sleeps | garage or gated parking at the building and a front desk or controlled entry stated | garage with neither stated, covered, lot, off-site, or parking not known | street only, or the town restricts overnight street parking and no space is confirmed |
| Saturday (`sat`) | bars and restaurants within 1,600 m | 5 or more bars and 30 or more restaurants | everything between | at most 1 bar and fewer than 15 restaurants |
| Sunday with her parents (`sun`) | drive one way, free-flow estimate | 30 minutes or less | 31 to 60 | more than 60 |

Shares among the 489 shown (strong / mixed / weak): wake 27 / 45 / 28; work 36 / 22 / 31 (10 percent null); after 28 / 47 / 25;
night 54 / 41 / 4; sat 32 / 41 / 27; sun 16 / 57 / 27.
