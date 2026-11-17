# Ranking, gates and selection: the rules as they stand

One current statement (rewritten 2026-11-16 in the pipeline consistency pass). It replaces the older file, which was
only right when read from the bottom up. The change log at the end says where each rule came from. Code:
`scripts/gates.py` (listing gate), `scripts/build_master.py` (merge), `scripts/all_in.py` (cost), `scripts/avoid.py`
(evidence rules), `scripts/rank.py` (ranking and selection), `scripts/check_registry.py` (assertions on the shown list),
`scripts/parsers.py` (every shared rule as a pure function). Tests: `scripts/test_rules.py`, `scripts/test_parsers.py`.

## 1. What is ranked at all

A listing goes through these steps in order. Counts of each step are in `docs/RUN_REPORT.md`.

1. **Listing gate** (`gates.py`). Studio or one bedroom; listed base rent at most **$2,200** (owner, 2026-11-17; rows
   above stay in `data/listings.csv` and fail with the reason `over_2200`); available now through 2026-12-15; dogs allowed
   (a stated limit under 25 lb fails; "small dogs" with no number passes); **floor and elevator** (section 2); within a
   2-hour drive. A gate fails only on a stated fact; an unstated fact makes the listing
   `pending`, and it stays in `data/listings.csv`.
2. **Cost** (`all_in.py`). All-in = rent + required fees + pet rent + parking + estimated utilities, at most $3,000
   (tested on the unrounded sum). Pet rent is always counted (the state's median where unpublished). Unpublished parking
   and fees add nothing; `all_in_likely` adds their medians and is never used for the cap. **The 12-month price is used
   wherever the page gives one and it differs from the listed price, whatever lease term the listed price is quoted for**
   (`parsers.use_12_month_price`; owner, 2026-11-16: Harbor Landing 452 is $2,487 on 13 months and $3,040 on 12). Rent,
   total and the $3,000 test then all use the 12-month price, and the receipt's rent line reads "rent (12-month lease
   price)". A 12-month price belongs to the unit it was read on: a building-level fact that names another unit, or no
   unit, is not applied to its neighbours. A price is net-effective only where the evidence says so.
3. **Safety.** A neighborhood whose violent or property crime rate is above Jamaica's precinct is cut.
4. **Confirmed facts** (`rank.py`). Removed: listed base rent over $2,200 (the price the live check read, else the
   listing's: `over_2200`); no elevator (stated, contradicted, a checker's reading, a reviewer's `remove | elevator`) or
   conflicting elevator sources **on floor 3 or above** (section 2: a floor-2 apartment stays); dogs not allowed on the
   building's own page; a weight limit under 25 lb; floor 1 or ground; gone at the live check (where the check found the
   building's whole listing page gone, "page could not be found", every unit listed on that page is gone, not only the
   units the check asked about: `parsers.listing_page_gone`, The Mercer); a page unchanged more than six months; available after the window; income-restricted or senior housing; a harvester's BUILDING_FAILS note.
   Also floor 1 by a **reading**: the unit number reads as floor 1 under its complex's reviewed numbering convention
   (section 3), or a bare apartment number in a building numbered in sequence is at most the average number of
   apartments per floor (`parsers.sequential_number_reads_ground`: 630 West 163rd Street 10, of 65 on six floors).
5. **Only real apartments** (owner, 2026-11-16). `parsers.listing_kind` classifies every row from the source's
   structure first and the label's shape second:
   - `unit`: its own identifier for one specific home (`5D`, `PH2`, `B9-309`, `022-265`, `T526`), or a single-home
     listing page of its own with no unit number, or a property whose own title names the unit (`416 Highland Ave - 312`);
   - `floor_plan`: a floor-plan row of a building page (Trulia `building_floorplan` / `:plan-` rows carry no unit
     number), or a label that names a plan (`1 Bed - 1 Bath`, `A - Large-1`, `B, H, K, R - Small-1`);
   - `building_offer`: a managed building's page price with no unit at all;
   - `private_room`: a room of a co-living suite (`448-3` at The Agnes Co-Living).
   - also `floor_plan`: a one-letter label beside numbered apartments of the same street address (`parsers.plan_letter_label`:
     BE `P` and `F` beside `3Pb`, `4OA`; Appletree Suites `C`, `E`, `F` beside `2B` to `6D`). A lone letter with no numbered
     sibling stays an apartment.
   Everything but `unit` gets the status `not_an_apartment` (`data/excluded_not_an_apartment.csv`): never ranked, shown,
   counted, or put on an avoid or held card. A building with only such rows does not appear.
6. **Reviewed verdicts** (`data/evidence/review_verdicts.csv`, several rows per unit, keyed on listing and kind):
   `remove` takes the unit out; `asterisk` (kinds elevator, dogs, not_available, unverified, wrong_building, restricted)
   is an open gate fact; `disclose` (lease_term, coop_condo, other, floor) is a disclosure; `ok` adds nothing. A verdict
   never closes a fact the rules leave open. Sibling rule: where a reviewer removed units of a building because their
   numbers read as first-floor units, a unit with the same label shape and digit is removed too.
7. **Open gate facts.** They are only: elevator; dogs allowed; whether the listing is real and available (availability,
   listing, eligibility). Two or more: "sketchy", excluded (`data/excluded_sketchy.csv`). One: kept with a certainty
   factor of 0.97. Also sketchy: a listing 60+ days old by its age field, no unit and no building named, a thin
   syndicated feed, an all-in under 60 percent of the neighborhood median, a live check that judged the listing doubtful.
   **A listing that was simply never re-read is not an open item** (owner, 2026-11-16; section 7).
8. **Evidence rules** (`avoid.py`): unit exclusions and avoid buildings (up to 5 avoid cards per neighborhood).

Phone answers (`data/evidence/call_answers.csv`, when present) outrank every other source and settle the fact they answer.

## 2. Floor and elevator: one rule for every stage

**The rule as it stands (owner, 2026-11-17, second trawl; it replaces "elevator buildings only").** An apartment with an
elevator established is judged as before: floor 1 or ground fails, any other floor passes, and an unpublished floor is a
disclosure, not a strike. Without an established elevator (no elevator, an elevator unknown, or one in doubt: the doubt
table, the garden-style rule, a contradicting row, a reviewer's asterisk, an inference from height) the apartment passes
only on **floor 2** (one flight up), stated, confirmed or read from the apartment number; the ground floor fails; floor 3
and above fail without an elevator (an elevator in doubt there stays the one open fact "Confirm an elevator serves this
apartment"; an elevator never stated is not shown); an **unknown floor is ONE open gate fact**, `floor_or_elevator`,
"Confirm the floor, and whether there is an elevator" (or the elevator fact where an elevator is named but in doubt).
`parsers.floor_elevator_rule` decides, on top of `parsers.elevator_rule` (below), in the listing gate
(`g_floor_elevator`), the ranking, the shown-list assertions and the verdict digest:

| floor as the rule counts it | elevator established | open (in doubt, or from height) | no / conflicting | unknown |
|---|---|---|---|---|
| 1 or ground | fail | fail | fail | fail |
| 2 | settled | settled (`floor_2`) | settled (`floor_2`) | settled (`floor_2`) |
| 3 and above | settled | open: `elevator` | fail | not shown (gate: pending) |
| not known | settled (disclosure) | open: `elevator` | open: `floor_or_elevator` | open: `floor_or_elevator` |

- **What counts as the floor** (`parsers.floor_how`): stated or confirmed on a page or by phone; or read from the apartment
  number: a simple label (`2B`, `305`), a ground word (`G`, `LOBBY`), the complex's reviewed numbering convention
  (`data/reference/unit_numbering_conventions.csv`) or a tower label. A floor read from the number carries the disclosure
  "read from the apartment number" (code `floor_read_from_number`), and on a walk-up its tour question adds "it must be
  floor 2 (one flight up): no elevator is confirmed here". A reading that needed the building's floor count to choose
  among several (`complex`) can fail a unit (floor 1) and never passes one.
- **Building height** (`data/reference/building_stories.csv`, `build_master.BuildingStories`; joined by `addr_key`, then by
  building through `building_crosswalk.csv`, then by coordinates within 30 m; the file may be absent or partial). An
  official record outranks a listing, which outranks OpenStreetMap. An official record of **one storey** puts every
  apartment on the ground floor (fail) unless a page states another floor. A building of **1–2 storeys** (any basis) has no
  floor 3: a label reading above its height is not a floor, and an elevator in doubt there is asked as `floor_or_elevator`;
  with floor 2 no elevator is needed. An official record or a listing enters `building_floors` (an official 6+ infers an
  elevator, as PLUTO does); OpenStreetMap never infers an elevator.
- **"No elevator" evidence** (`avoid.py` exclusions of kind `elevator`: contradicted, or the checker's reading; a reviewer's
  `remove | elevator`) is read as elevator "no": it removes floor 3+ and ground-floor units and keeps a floor-2 apartment.
  The doubt table and the garden-style rule no longer remove or hold back a floor-2 apartment.
- A floor-2 walk-up and a `floor_or_elevator` apartment are new kinds of shown apartment: each needs a reviewed verdict as
  every shown apartment does; with `floor_or_elevator` open the floor is not listed a second time as a disclosure.

**The elevator by itself.** `parsers.elevator_rule` is called by the listing gate, the merge and the ranking (it used to
be three slightly different rules). First matching row wins:

| # | What is known | Result |
|---|---|---|
| 1 | a phone answer | established, or no |
| 2 | a page says there is no elevator | no |
| 3a | a positive source, and something speaks against it (an evidence row contradicts; the city classes the listing's own lot as walk-up; the building is in `data/reference/elevator_doubt.csv` or caught by the garden-style rule; a reviewer's verdict) | **open** |
| 3b | a positive source and nothing against it | **established** |
| 4 | no positive source; the city classes the listing's own lot as walk-up; no page height of 6+ | no |
| 5 | no positive source; a real height of 6+ floors | **open** ("inferred from height") |
| 6 | anything else | unknown |

Positive sources: stated on a page (the listing, a listing site's amenity list, the building's or its manager's page);
the city's elevator class on the listing's **own** lot with the device list not showing zero active elevators; an
evidence row graded confirmed or stated; a parsed amenities page. A real height: a page's floor count or floor list, a
floor a page states for a unit, the city's floor count on the listing's own lot, a harvester's or checker's "6+ floors"
read from a page's floor list or floor field, or "high-rise" on the building's own or its manager's page.
**Never used, to pass or to fail:** a floor read from a unit label (`42M`, `1804`); a neighbouring tax lot (the lot counts
only when its address agrees with the listing's: `parsers.lot_is_exact`).

What the stages do with the elevator's status is now the floor-and-elevator table above (before 2026-11-17: the gate
passed established or open, failed no, and held unknown as pending; the ranking did not show unknown). An elevator named only on listing sites is marked
`elevator_aggregator_only`. Garden-style rule: the elevator rests on listing sites only, the unit labels name several
buildings, and no page or record gives four floors or more. A label that names its building (`K3-02`, `B9-309`, `09-426`,
`A207`: `parsers.explicit_building_label`) counts whatever floor it reads as, because a floor read from a label is not a
height (Residences at The Summit, buildings K, L, M, used to escape on `K4-19`). Bare four-digit labels (`5201`) count
only when no label reads above floor 3, the floor digit varies and no unit-on-floor number exceeds 40; complexes of that
shape that a reviewer has read as several buildings are in `data/reference/elevator_doubt.csv` (1 Kennedy Flats, Admirals
Cove, Halstead Parsippany, The Confluence were added after independent check 4).

## 3. Floor, dogs, staleness, disclosures

- **Floor.** Floor 1 or ground (confirmed, stated, or read from the unit number), or a checker's reading that the unit
  is probably ground-level, excludes. With an elevator established, an unpublished floor is a disclosure and tour
  question, never a strike; without one, the floor decides (section 2: floor 2 passes, an unknown floor is one open fact).
  **One numbering convention per complex** (`data/reference/unit_numbering_conventions.csv`, each row with how it was
  established): `floor_first` (`4186` is floor 4: The Grove Somerset, Steel Works, Cobalt Lofts, Piper, 3 Acres) or
  `building_floor_unit` (`3104` is building 3, floor 1: Kensington Place, J Centra Burlington and nine more). The master
  carries the reading (`unit_floor_reading`); it removes a unit that reads as floor 1 and, since 2026-11-17, settles floor 2
  for a building with no established elevator (section 2); it is used for nothing else. Where
  a convention is on file the "same shape as removed siblings" rule is not used. A tower label `01-16C` is floor 16.
- **Availability on a second site.** A checker's finding that another listing site covers the address and does not show
  the apartment (`parsers.second_site_omits`), on a listing that could not be read again, is the open item
  "availability" wherever it was recorded. The page's staleness, or a warning that only repeats it, is the same doubt
  and is not counted a second time.
- **Where the building stands.** Every building's point is compared with its own address
  (`build_master.check_coords_against_address`, `parsers.coord_check`): the Census ZIP area and municipality at the
  point against the ZIP and city of the listing rows. Outside the ZIP area, the address is geocoded (Census): within
  150 m the point is kept (a ZIP boundary), otherwise the geocoder's point replaces it when that lies where the address
  says; if neither can be trusted the building is flagged and its apartments carry one open "listing" fact. The
  building's `city` is the municipality at its point (Census place, else county subdivision); the city a listing wrote is
  kept in `city_listed`. Results: `data/reference/building_coord_check.csv`, `data/reference/municipality_changes.csv`.
- **Dogs.** Allowed must be stated or confirmed, with dogs named ("pets upon approval" leaves it open). A policy that
  **conflicts between sources is one open gate fact (dogs)**; the building's own or its manager's page settles it; only
  a clear "no dogs" there removes. "Small dogs" or "weight restrictions apply" with no number passes with the tour
  question "Confirm the dog weight limit in pounds". **A weight limit is a number only where a source's own words state
  it** (`parsers.dog_weight_traced`, over the listing's pet text, the building's page and every checker's quote): a
  stored figure no page states is removed and kept aside as `dog_weight_limit_untraced` (Brookview Commons East: "small
  dogs" had been stored as 25 lb, the gate's threshold). A checker's note that no page gives a number is never read as
  the number it mentions.
- **Staleness.** A page unchanged more than 60 days with no second site (a different host), or an availability date
  more than 183 days old: the open item "listing". Unchanged more than 183 days: removed. **The days are counted to the
  first tour day, 2026-11-22** (`parsers.TOUR_START`), or to the day the page was read when that is later
  (`parsers.staleness(..., as_of=)`; independent check 5, N28): a page read on November 15 at 58 days unchanged is 65
  days unchanged when tours start, and carries the open item now. Nothing is assumed about the page after it was read
  except that it did not change. The page date comes from the
  unit's own live-check note, a page fact, or a sibling's note about the same page; where a later batch establishes the
  date for the whole page and an earlier note gives a newer building-level date, the reviewed table
  `data/evidence/page_date_corrections.csv` sets it for every unit on that page (Grandville Towers: 2026-07-30 for 5F,
  7C, 9C and 7F alike; 109 days, one open item, not removed). An old availability date that only the live check read
  (`available_on` in the live text, the stored date being "now") is written up by the reviewer as `asterisk |
  unverified`, the same open item.
- **Long-lease prices with no 12-month price read (sibling rule; owner, 2026-11-16).** A unit whose listed price is
  quoted for a lease over 12 months (or is "the lowest over the lease terms"), whose own 12-month price was not read,
  in a building where another unit's 12-month price is more than 15 percent above that unit's listed price
  (`parsers.sibling_12_month_gap`, `price_12_sibling_gap`): no price is guessed. The unit keeps its listed price and its
  lease-term disclosure, the disclosure adds "the 12-month price in this building is much higher than the price shown:
  ask for it" with the sibling's two prices, and the unit carries **one open "listing" fact** (asterisk; with another
  open gate fact it is not shown). A sibling that is only slightly dearer on 12 months (Scribe 502: $2,379 against
  $2,395) does not trigger it.
- **Disclosures** never count and never remove: floor not published; lease term (**any** listed price quoted for a
  lease that is not 12 months with no 12-month price read: "The price shown is for a 13-month lease: ask for the 12-month
  price"; or the 12-month price is used in its place); income requirement, credit-score requirement and furnished
  apartment, read from the evidence (`parsers.renter_conditions`; a statement that the apartment is not a normal lease,
  short-term only, corporate or student housing, a sublet, is the open fact "eligibility" instead); **broker fee** ("the
  listing says a broker fee applies; ask how much") or "no broker fee, per the listing", and **one-time costs** the
  listing states (application, administrative, holding and move-in fees; a security deposit only when it is more than
  one month's rent), read from the listing's own description on the cached page and from the checkers' facts
  (`parsers.broker_fee_statement`, `parsers.one_time_costs`, `scripts/tools/listing_fees.py`): never part of the monthly
  total; **washer and dryer to confirm**, where in-unit laundry rests only on a listing site's appliance list
  (`in_unit_laundry_source_kind = appliance_list`); could pass $3,000 once the unpublished cost lines are known (parking,
  required fees, **and a utility with no estimate**: where the utilities tool has no gas figure, `all_in_likely` adds the
  median of the gas estimates that do exist, by state and bedroom count); special offer; net-effective rent; condo rented by its owner; dog weight limit not
  published; overnight street parking restricted (`data/reference/overnight_parking_towns.csv`).

## 4. One apartment, one row; one building, one id

- A unit written into the address (`1775 Windsor Road #215`, `20 Gill Lane, Apt. 1E`) is moved to the unit field and the
  address is cleaned. `addr_key` is still built from the address as listed: evidence is filed under it.
- Two labelled rows of one building are the same apartment when the labels are equal, or one is the other with a
  building prefix (`215`, `001-215`) and bedrooms, rent (2 percent) and size (3 percent, or one unpublished) agree.
  `001-215` and `002-215` are two apartments. An unlabelled row merges on equal beds, rent and size, or across two sites
  on beds, size and rent within 2 percent.
- A unit is never merged into a floor plan. A plan row that only repeats a named unit's beds, rent and size is dropped.
- A complex listed under a range of house numbers (`55-57 Bank Street`) is the same building as listings filed under
  either end of the range on the same street and ZIP within 400 m (not Queens-style numbers).
- The building's own site outranks an aggregator; then the fuller row. Other links are kept in `also_seen_at`.
- A building's name is its name: marketing tails are cut and an address used as a name is dropped (`parsers.clean_building_name`).
- A building's floor count is the largest count a page or record states, and never below the highest floor a page states
  for one of its apartments (basis `at_least`; the Continuum showed "2 floors" with apartments on floors 3 to 16).
- A fact taken from a resident's review has the basis `resident_review`: below every page or record that states it,
  above a bare inference. A parking fee is "published" only from the building's own page or a listing; from a review it
  is an estimate with the review named.

## 5. Score

**Universal value (0-100).** Percentiles across all ranked units; an unknown variable scores at the 25th percentile.

| Part | Weight | Variables |
|---|---|---|
| Safety | 22 | violent rate, property rate, vehicle-theft rate, car and violent crime within 250 m (NYC), evening share, three-year trend, building security features |
| Building | 16 | security features (24h doorman 3, doorman 2, controlled entry 2.5, package room 1) 40; comfort (in-unit laundry 2.5, lounge or coworking 1.5, gym 1, outdoor space 1, elevator stated 1, balconies 0.5) 45; year built 15 |
| Cost | 12 | all-in 85; cost lines stated rather than estimated 15 |
| Car | 12 | parking type 50 (garage or gated > covered > lot or off-site > street), **of the space she would actually park in** (see "Parking" below); vehicle-theft rate 15; car crime nearby 15; parking fee 10; surface parking nearby 10 |
| Space | 12 | sq ft 75; a separate bedroom 25 |
| Distance | 10 | drive to her parents 60; transit 25; tolls 15 (closer is better; a toll counts only when every crossing has a rate) |
| Dog | 8 | walk to green, park area, dog park, vets, dog amenities, **a weight limit of 25 lb or more, or no limit** (10), woods, pet shops, pet rent |
| Daily life | 8 | supermarket distance, cafés on foot, gyms, distance from the motorway, farmers' market, corner stores, library |

In-unit laundry counts only where the master says `in_unit_laundry = yes`: a source says the washer / dryer or the
laundry is IN the apartment, and no source says it is not (`parsers.laundry_facts`, applied in `build_master.py` to every
source's own words: the listing's laundry field, the amenities page with the sentence it was read from, a checker's
fact). A checker's "not in unit" settles it against a listing site's appliance tags (153-10 88th Ave). Hookups alone are
`washer_dryer_hookups`; a shared room is `on_site_laundry` (`in_unit_laundry = on_site_only` when nothing is in the
apartment); "select apartments have a washer" is `select_apartments` and does not score (Beacon Mill Village). The
`laundry` label beside the flag is written from the same facts, so the two cannot disagree.

Dog amenities are structured the same way (`parsers.dog_amenity_facts`, every source's words): `dog_park_or_run` only
where a source names a dog park, dog run, bark park, pet park or fenced dog area on the property; `pet_spa_or_wash`
for a pet spa, grooming room or dog wash; `dog_amenity_unspecified` where a source says only "yes". The Dog part's
"dog amenities" variable still counts any of the three. `dog_amenities` stays as the label (`dog run; dog park; pet spa;
dog wash`, or `yes` when unspecified).
The security points count a staffed front of any kind, as before. The AMENITY shown is separate: `doorman` only where a
source says doorman, `concierge` only where a source says concierge, `front_desk` for an attended lobby or desk called
neither (`parsers.staff_from_sources`).

**Parking** (after independent check 5; `parsers.parking_facts`, `build_master.structured_parking`). Every source's own
words about parking are collected per building (the listing's parking field and fee lines, the community page's three
parking columns with their sentences, the amenities page, every evidence fact about parking, a phone answer) and read
together. The result:

- `parking_kinds`: every kind a source names: `garage`, `gated_lot`, `covered`, `assigned_lot`, `open_lot`, `off_street`
  (off-street parking of unnamed kind), `assigned` (an assigned space, place not said), `offsite`, `street`.
- `parking_included_kind`: which kind the free or included space is (only where the cost counts parking at $0;
  `unspecified` when a space is included and no source says of which kind).
- `parking_optional`: the other kinds offered for a fee, each with its fee, or with none when it is not published.
- `parking_fee_kind`: the kind the counted fee pays for.
- `parking_kind`, the **primary kind**: the included kind where a space is free; the kind the counted fee pays for;
  otherwise the best kind named, leaving out a garage or covered space that is only an optional extra beside a plain lot.

The score's "parking type", the night moment and the page's word for the parking all read the primary kind: garage or
gated lot 4, covered 3, an open or assigned lot, off-street, assigned or off-site space 2, street 1, unnamed kind
unknown. **A free open lot is not a garage**, whatever garage the same sentence offers for a fee ("Open lot: included in
lease; Underground parking garage: $50/month" is an open lot with a $50 garage as an extra). `parking_type` is stored as
`<head>: <the source's words>`, the head being the primary kind in the older vocabulary (`garage`, `covered`, `lot`,
`assigned`, `street_only`, `offsite`, `parking`). "Covered parking fee" on a listing site's fee line is that site's label
for a garage fee too: it adds no second kind beside a garage. A section heading ("Parking & Garage"), "Gated Entry" in a
feature list and "Street" in an address are not parking. Buildings the sentence parser cannot settle are in the reviewed
table `data/reference/parking_reviewed.csv` (each row with the quote and why).

**The experience's promise (30 percent).** Walk-Everywhere: restaurants, bars, cafés, shops, street-grid density,
cinemas and theatres, bookshops. Old-Neighborhood: corner stores, hair and beauty shops, restaurants, laundromats,
library, playgrounds, transit to her parents. Fresh-Start: building amenities, distance to water, newcomer share, age
25-34 share, building year, gyms, bars within a mile. Little-City: restaurants, train station distance, cinemas and
theatres, shops, farmers' market, bars within a mile. Room-to-Breathe: sq ft per dollar, a separate bedroom, park area,
parking, woods. Quiet-Street: violent and property rates, distance from the motorway, parking, woods, detached-house share.

**Rank score = (0.7 × universal + 0.3 × promise + pool bump) × certainty.** Pool +3, indoor pool +6. Certainty 1.00
with nothing open, 0.97 with one open gate fact.

## 6. Experiences (lifestyle groups)

Six groups fitted once (`scripts/lifestyle_groups.py --refit`, on purpose only). A neighborhood's group is a pure
function of saved files: its frozen area profile (`data/reference/lifestyle_area_features.csv`), the scaling parameters
(`lifestyle_scaling.csv`, `lifestyle_index_scale.csv`), the centres (`lifestyle_group_centres.csv`) and the reviewed
overrides (`lifestyle_group_overrides.csv`). Adding or removing listings never changes it. Distances to every centre and
the boundary cases (nearest and second-nearest within 10 percent) are in `data/lifestyle_group_distances.csv`.

## 7. Selection: what is shown

In each neighborhood, in this order: dominated units last (beaten or tied on all eight parts by another unit there),
then rank score, then `listing_id`.

- **Shown**: not an avoid building; at most **one** open item, and the open items are the open gate facts only
  (elevator; dogs allowed; eligibility; whether the listing is real and available); the building has evidence rows; a
  current `ok`, `asterisk` or `disclose` verdict. One open item is shown with an asterisk (`confirm_asterisk`,
  `confirm_what`, `confirm_why`); two or more open gate facts and the unit is not shown.
- **No "not re-checked" flag** (owner, 2026-11-16: "Forget call check"). A unit that was never re-read in an evidence
  pass (live status blank, not checked, or blocked, such as the Trulia rows that cannot be re-read) carries no open
  item and no asterisk for that, and it counts against the unit in no rule: not in "two or more open", not in the
  thin-neighborhood rule, not as a second open item beside an elevator doubt, not in the certainty factor, not in the
  order among equal scores. `rank.open_item_count` ignores the live status on purpose. **What a re-read found still
  counts**, through the facts that already existed: gone → removed; a changed price → the price is updated; a page that
  shows no units, is stale beyond the thresholds or describes a different building, or a checker's "verify the price"
  note → the open item "listing" or "availability". Reviewed verdicts stay required for every shown unit. Each unit
  keeps the date its price was read (`last_seen`, `price_seen_at` in the page data) and its `live_status` as
  information. `data/needs_live_check.csv` is no longer written; the page data keeps `awaiting_live_check` as an empty
  array.
- **Up to 8 per building**, in rank order; no cap per neighborhood; `more_in_building` on each shown unit.
- **Thin neighborhoods** (owner, 2026-11-16). A neighborhood whose shown list is exactly one apartment keeps it only
  if it is (a) well attested: a real apartment with no open gate fact (no asterisk; disclosures and a listing never
  re-read do not count), and (b) promising:
  its rank score is at or above the median rank score of the apartments shown in its experience, the median taken before
  this rule. Otherwise the apartment stays in `data/ranked_units.csv` with `shown = False` and
  `not_shown_reason = thin_neighborhood`, and the neighborhood is not on the page. Applied once; a neighborhood with two
  shown apartments is not touched.
- Candidate and phone-call lists (`hood_rank`, `data/needs_confirmation.csv`) take two per building.
- Neighborhood order inside an experience (`scripts/page_data_extras.py`): the mean rank score of the three best shown
  places, minus 2 points per missing place; the top three first, the rest on "show more".

`scripts/check_registry.py` fails the run when a shown unit breaks any of these rules.

## 8. Reading the page data

- **Neighborhoods.** `neighborhoods` holds only places with at least one shown apartment; a place with only an avoid card
  is in `neighborhoods_avoid_only` and is not counted anywhere. `safety.status` is `published` or `not_published` (no
  agency publishes a rate for the town alone: the safety rule could not be tested there; `status_note` says why).
  `shown_figures` are the median BUILDING's figures (one vote per shown building, then the median over the buildings:
  the same computation as the written text and "At a glance"), and `buildings_with_own_dog_area` counts only
  `dog_park_or_run`; `traits` describe the wider area profile. `meta.notes` and `meta.moment_thresholds` are plain
  sentences for the reader (no field names).
- **The train station** (independent check 5, N3). `train_station` / `train_station_m` are the nearest rail station **of
  any kind**: commuter rail, subway, PATH or light rail, from the station table `data/reference/rail_stations.csv`
  (built once from the six cached GTFS feeds under `raw/gtfs/`: LIRR, Metro-North, the NYC subway with the Staten Island
  Railway, NJ Transit rail with the Hudson-Bergen, Newark and River Line light rail, PATH, SEPTA). `train_station_kind` is
  the reader's word for it (`train`, `subway`, `PATH`, `light rail`) and `train_station_system` its operator.
  `commuter_station` / `_m` / `_system` are the nearest commuter-rail station; where that is the same place as the map's
  station used before, its name and distance are unchanged. Distances are straight lines. The Little-City promise's
  "train station distance" reads the nearest station of any kind. `shown_figures.train_station_kind` is the kind at the
  neighborhood's median building; `train_station_kinds` counts the kinds over its shown buildings.
- **Tolls.** `toll_round_trip` of a neighborhood is the median over its shown apartments; `toll_round_trip_range` is the
  lowest and highest (Newark: $24 at most buildings, $33 and $43 at two).
- **Evidence on avoid and pause cards.** A city-record count is a sentence that starts with the count ("23 pest
  complaints recorded by the city here in the last six months, far more for its size than at nine in ten buildings in the
  city."); the raw count string is in `excerpt_internal` and `kind` is `record`. The car-crime reason of an avoid card is
  "Police recorded N car break-ins or thefts within about 250 meters (a few blocks) in two years, about twice what is
  typical for the buildings we looked at in <borough>." It appears only on avoid cards.
- **Reader text.** `confirm.label / why / question`, each disclosure's `label / why / question`, each cost line's `note`
  and every tour question are written in `scripts/build_page_data.py` from a reason code and structured fields
  (apartment, never unit; dates in full; no file paths or working vocabulary). The working note is kept in
  `why_internal` / `note_internal`, which the page does not show. A reviewer's sentence replaces a template only when it
  passes the same check. `scripts/test_rules.py --data` walks every reader text field of `site/data.json`.

- **Compared to staying in Queens**: every measure on five points with Queens in the centre
  (`data/reference/queens_spectrum_definition.csv`, `vsq_*` columns). Closer to her parents is better.
- **Standings**: each unit carries its standing per part within its experience and against everything;
  `data/group_exchange.csv` holds each experience's medians.
- **Experience and neighborhood figures** are medians and ranges over the shown units.
- **Day moments** (`moments.<key>.rating`: strong / mixed / weak, or null), on absolute thresholds:

| Moment | Measure | Strong | Mixed | Weak |
|---|---|---|---|---|
| Morning with the dog (`wake`) | minutes on foot to the nearest green space | 3 or less | up to 10 | more than 10 |
| Work day at home (`work`) | size and a separate bedroom | a separate bedroom and 700 sq ft or more | between | under 550 sq ft, or a studio under 600 |
| Evening out (`after`) | restaurants and bars within 800 m | 15+ restaurants and a bar | 4+ restaurants | fewer than 4 |
| The car at night (`night`) | where you would park overnight | garage or gated parking and a front desk or controlled entry | garage with neither, covered, lot, off-site, unknown | street only, or the town restricts overnight parking and no space is confirmed |
| Saturday (`sat`) | bars and restaurants within 1,600 m | 5+ bars and 30+ restaurants | between | at most 1 bar and fewer than 15 restaurants |
| Sunday with her parents (`sun`) | drive one way | 30 minutes or less | 31 to 60 | more than 60 |

## Change log

| When | Change |
|---|---|
| 2026-11-15 | Ranking v1 (six parts), then v2 (eight parts, "drop anything sketchy"); 70/30 split; pool bump; Queens spectrum |
| 2026-11-15 | After check 1: what counts as settled for elevator, floor, dogs; "small dogs" passes; shown with at most one open thing |
| 2026-11-16 | After check 2: reviewed verdicts required; 12-month price for long leases; deterministic selection order |
| 2026-11-16 | Open gate facts are only elevator, dogs, listing real and available; everything else is a disclosure; an unpublished floor is a tour question; no cap of 10 per neighborhood |
| 2026-11-16 | Staleness rule; listing-site elevator is "stated"; dog weight limit with no number; overnight parking; phone answers; tolls |
| 2026-11-16 | After check 3: elevator doubt table and garden-style rule; pet rent estimated, `all_in_likely`; 8 per building (was 2); several verdict rows per unit; day moments on absolute thresholds |
| 2026-11-16 | Elevator gate never rests on a unit label |
| 2026-11-16 | Consistency pass: one elevator rule for every stage (a near-miss lot neither passes nor fails; "high-rise" on the manager's page and a page-stated unit floor count as real height everywhere); frozen area profiles for the experiences; unit moved out of the address; duplicate rule across label spellings; a ranged address is one building; conflicting dog policy is one open fact, not "sketchy"; the dog part rewards a limit of 25 lb or more (the text said 40); in-unit laundry no longer counts a shared laundry room; cap tested on the unrounded sum |
| 2026-11-16 | Owner: only real apartments (floor plans, building prices and co-living rooms are `not_an_apartment`); thin-neighborhood rule |
| 2026-11-16 | Evidence batch 20 (190 shown apartments re-read): the 12-month price is used wherever the page gives one and it differs, whatever the quoted term (was: only for leases over 13 months, and only when higher); a 12-month price is never taken from a fact about another unit (a dollar amount such as "$2,616" no longer reads as unit 616); sibling long-lease rule (one open "listing" fact, nothing guessed); a listing page that is gone takes every unit on it; reviewed page-date corrections (Grandville Towers) |
| 2026-11-16 | Owner ("Forget call check"): the "not re-checked live" flag is dropped. A listing never re-read is not an open item in any rule; the thin rule's "well attested" is "no open gate fact"; ties are broken by `listing_id` only; `needs_live_check.csv` and the "awaiting live check" list are gone. A problem a re-read found still counts |
| 2026-11-16 | After independent check 4: every building's point checked against its address (Harbor Pointe is in Bayonne, Parkway Lofts in Bloomfield) and `city` from geography; second-site rule for availability; garden-style rule no longer escaped by a label that reads as floor 4; plan letters are not apartments; a sequential apartment number that reads as floor 1; numbering conventions per complex (The Grove Somerset 2141, 3172, 4149, 4171 restored); income, credit and furnished disclosures; lease-term disclosure for any term that is not 12 months; doorman and concierge apart; `resident_review` basis; building floors from the largest stated count; "up to" kept on offers; avoid-only neighborhoods in their own array; `safety.status`; reader text from templates |
| 2026-11-16 | Pipeline clean-up: laundry and dog amenities derived from every source's words (structured fields; the label beside a flag agrees with it); `buildings_with_own_dog_area` counts only a dog park or run; `shown_figures` over buildings, not apartments; `meta.notes` and `meta.moment_thresholds` as reader sentences; American spelling in our own rule summaries (quotes untouched) |
| 2026-11-16 | After independent check 5: structured parking from every source's words, and the score, the night moment and the page read the space she would actually park in (a free open lot is not a garage; 16 shown buildings changed rank); the "train station" is the nearest rail station of any kind, with its kind and system; broker fee, one-time costs and "washer and dryer to confirm" disclosures; a dog weight limit only where a source's words state it; a utility with no estimate feeds `all_in_likely`; staleness counted to the first tour day (2026-11-22); record counts and car crime on avoid cards as sentences; toll range per neighborhood |
| 2026-11-17 | Owner, second trawl: listed base rent at most $2,200 (gate and ranking; `over_2200`; the $3,000 total unchanged). Floor and elevator together (`parsers.floor_elevator_rule`): a walk-up is allowed on floor 2; the ground floor stays out; floor 3+ needs an elevator; no elevator stated and no floor stated is one open gate fact, `floor_or_elevator`; a floor read from the apartment number counts, with its disclosure; building heights from `data/reference/building_stories.csv` (official record over listing over OpenStreetMap; OSM never infers an elevator); "no elevator" exclusions and a reviewer's `remove | elevator` no longer remove a floor-2 apartment; the doubt table and garden-style rule no longer hold one back |
| 2026-11-17 | Live-check batch 21 (the 45 apartments at or under $2,000 listed rent re-read): the status `not_read` means nothing was learned (`parsers.live_row_learned`): such a row never replaces an earlier live / changed / gone row, sets no live status, date, price or note, is not a re-read and is not an open item; it stays in the evidence files and in the verdict fingerprint, and anything its note found is written by the reviewer as a verdict (333 State St 604: `asterisk, not_available`; Regency on Hudson 606: its one open "listing" item now carries the own-site finding) |

Superseded and no longer true anywhere: "elevator buildings only", "no elevator removes the unit", "listed rent at most $3,000" (the $3,000 all-in cap stands), "staleness is counted to the day the page was read", "parking type is the best kind the sentence names", "train station = nearest commuter-rail station", "the lease-term disclosure starts above 13 months", "no label reads above floor 3" as a condition of the garden-style rule for labels that name their building, `doorman` as "doorman or concierge", "the 12-month price only for leases longer than 13 months", "at most 2 per building" for the shown list, "best 10 per neighborhood", "top 15
candidates then the best 10", a floor-plan row shown with an availability asterisk, "weight limit stated ≥ 40 lb",
conflicting dog policy as sketchy or as a drop, "a missing live check is its own open item", "units seen live first"
among equal scores, the "waiting for a live check" list. `scripts/rank_v1_backup.py` keeps version 1.
