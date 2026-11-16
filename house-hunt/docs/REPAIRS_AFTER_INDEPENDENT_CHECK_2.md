# Repairs after the second independent check

Written 2026-11-16 (UTC), after `docs/INDEPENDENT_CHECK_2.md` (D1–D21). No listing page was fetched and no harvest
script was run. No file under `data/listings_raw/` and no `data/evidence/*_batch_<n>.csv` file was changed. One evidence
file was added from readings the checker had already made (`live_check_batch_ic2.csv`, 2 rows, see D15).

The check's diagnosis was that evidence agents wrote their doubts in plain words and the rules read only a short list of
phrases. Two things were done about it: a reviewed verdict table that a shown unit cannot do without, and a fix for each
of the 21 defects at the cause the report names.

## Where it stands now (after the owner's three changes of 2026-11-16)

The repairs were first finished under the strict rule in the brief ("every asterisk counts as an open fact"): 210 shown.
The owner then changed three things, applied in this order. Each newly shown unit was read and given a verdict before
it could be shown.

| Stage | Rule | Ranked | Shown | Of them inside the old cap of 10 per neighborhood |
|---|---|---|---|---|
| A | Strict: every asterisk is an open fact; two or more is out; 10 per neighborhood | 621 | **210** | 210 |
| B | **Disclosures do not count.** Lease term, cost near the cap, condo rented by its owner and net-effective rent are listed on the unit (`disclosures`) and never remove it. **The cap of 10 is lifted** (`SHOWN`), 2 per building kept, `more_in_building` recorded. New rule of mine: a building with no evidence rows at all cannot be shown (86 ranked units wait for that reason) | 740 | **260** | 250 |
| C | **An unpublished floor does not count.** It is the disclosure and tour question "Floor not published: confirm it is above the ground floor". Still out: floor 1 or ground, a reading that the unit is probably or possibly on the ground floor, a verdict saying so | 855 | **326** | 304 |

So the disclosure change is worth +40 at the old cap (210 → 250) and the lifted cap +10 more; the floor change is worth
+54 at the old cap (250 → 304) and +66 in all (260 → 326).

**Final: 326 shown in 233 buildings, 107 neighborhoods (36 with three or more; the largest has 22).** 35 avoid cards, 26
held, 28 waiting for a live check. Open gate facts that count now: elevator, dogs allowed, and whether the listing is
real and available (availability, listing, eligibility); a missing live check is its own item as before; at most one in all.

| | Count among the 326 shown |
|---|---|
| Nothing open | 208 |
| One open item (asterisk) | 118: live check 42, listing (stale or doubtful) 27, dogs allowed 17, elevator 16, availability (floor-plan row) 14, eligibility 2 |
| Disclosure: floor not published | 295 (163 read from the unit number, 132 unknown); 31 floors are confirmed or stated |
| Disclosure: cost near the cap | 50 (of 63 shown units at $2,900 or more) |
| Disclosure: lease term over 13 months | 39 |
| Disclosure: net-effective rent | 26 |
| Disclosure: condo rented by its owner | 4 |
| No asterisk and no disclosure at all | 8 |

| Year | CT | NJ | NY | Total |
|---|---|---|---|---|
| Little-City | 38 | 59 | 35 | 132 |
| Room-to-Breathe | 24 | 44 | 8 | 76 |
| Old-Neighborhood | 0 | 13 | 62 | 75 |
| Fresh-Start | 11 | 16 | 0 | 27 |
| Quiet-Street | 5 | 5 | 0 | 10 |
| Walk-Everywhere | 0 | 0 | 6 | 6 |
| **All** | **78** | **137** | **111** | **326** |

**Verdicts now: 507** (remove 160, asterisk 83, ok 264); the 326 shown hold 252 ok and 74 asterisk. Review rounds in
all: 4 under the strict rule (209, 11, 6, 0 units), the 23 seeded units, then 71, 1, 1 after stage B and 54, 9, 2 after
stage C. 26 of my earlier removes rested on "a second thing, the floor" and were turned into single asterisks. 49
removes are now for a unit number that reads as a first-floor unit under the building's own numbering (for example
Kennedy Flats 2132, Steel Works 1127, Avalon Teaneck 003-163): most are siblings of units the checker had flagged.

**Seven units the checker marked "must remove" are shown again, each with one asterisk**, because the checker's second
reason was the floor and the floor no longer counts: The Grove Somerset 2205 and Spinnaker Wharf 5-02E (elevator in
select buildings only), 99 Bridge 232 (elevator on a listing tag only), The District at 15Fifteen 1-219 and 1-234 (one of
three communities is 55+), 25 West Broadway 204 and 7914 Rockaway Beach Blvd 2F (condo units, pets "case by case").
That follows the new rule to the letter; the owner should look at these seven.

A fault of mine found and repaired during stage C: `verdicts.py add` mis-read an empty field written "| |", so 79 remove
rows had their reason stored in the wrong column (the removal itself worked; the reason shown was a row tag). The parser
and the 79 rows are fixed. One more fix in stage C: a floor-plan row matched to a live check by its plan name no longer
takes that check's price when the price belongs to another plan (3333 Broadway, Willett Point, Woodmere).

The sections below describe stage A. The per-defect table still holds; its "after" counts are stage A counts.

## Final counts under the strict rule (stage A)

| | Before (run the check froze, 23:16 UTC) | Now |
|---|---|---|
| Costed in the master table | 2,575 | 2,573 (2 more duplicates merged) |
| Within the $3,000 all-in cap | 1,653 | 1,655 |
| Ranked | 980 | 621 |
| **Shown** | **332** in 251 buildings | **210** in 163 buildings |
| Shown with nothing to confirm | 142 | 80 |
| Shown with an asterisk | 190 | 130 |
| Avoid cards | 35 | 33 |
| Held for one confirmation | 61 | 53 |
| Waiting for a live check, not shown | 59 | 53 |
| Removed by a reviewed verdict | did not exist | 109 (of 111 remove verdicts; the other 2 fail an earlier stage) |
| Dropped as sketchy (two or more things open) | not recorded | 453 |
| Neighborhoods with a shown place / with 3 or more | – / 38 | 84 / 26 |

Asterisks on the 130 shown units, by what is open: floor 60, live check 16, lease term 14, listing 12 (availability or
identity of the listing), cost near the cap 12, elevator 8, dogs allowed 6, condo rules 2.

Shown by year and state:

| Year | CT | NJ | NY | Total |
|---|---|---|---|---|
| Little-City | 17 | 35 | 26 | 78 |
| Old-Neighborhood | 0 | 9 | 48 | 57 |
| Room-to-Breathe | 15 | 30 | 4 | 49 |
| Fresh-Start | 6 | 9 | 0 | 15 |
| Quiet-Street | 1 | 5 | 0 | 6 |
| Walk-Everywhere | 0 | 0 | 5 | 5 |
| **All** | **39** | **88** | **83** | **210** |

Of the 332 units shown before: 197 are still shown, 69 are dropped by the rules as sketchy (two or more things open),
55 are removed by a verdict, 9 are ranked but wait for a live check or fall outside their neighborhood's ten, and 2 were
merged as duplicates. 13 units are newly shown. Every "must remove" unit in the report is gone.

## The reviewed verdict table

`data/evidence/review_verdicts.csv`: one row per unit whose evidence has been read. Columns: `listing_id, building_id,
addr_key, unit, verdict` (remove / asterisk / ok), `kind, what_to_confirm, why, evidence_quote, evidence_file,
reviewed_at, evidence_hash`.

- `scripts/rank.py` applies it. `remove`: the unit is excluded before ranking, with the reason
  (`data/excluded_by_review.csv`). `asterisk`: the unit counts as having that open fact, so it is shown with an asterisk
  that says what and why, or dropped as sketchy when that makes two. `ok`: nothing added. A verdict never closes a
  fact the rules leave open.
- `scripts/check_registry.py` fails the run when a shown unit has no `ok` or `asterisk` verdict, or when the verdict
  was written against older evidence. `evidence_hash` is a fingerprint of every live-check, confirm, facts and items row
  of the building (all its address keys, through `building_crosswalk.csv`) plus its NYC lot and elevator-device rows.
  Add or change an evidence row and the building's units must be read again before they can be shown.
- `scripts/verdicts.py` is the reviewer's tool: `pending`, `digest` (the reading file), `add` (verdict lines).

**What was read.** For each shown unit: every live-check row, every confirm row and the NYC lot and device rows of its
building, in full or cut at 560 / 280 characters; every facts row except routine cost and amenity lines that contain
no caution word; review items that mention an elevator, stairs, dogs, an age or income limit, a co-op or a ground
floor. Not read line by line: other review items, and the police and inspection rows outside NYC (no gate fact in
them). The 85 seed rows came from the report's tables; the 23 seeded units that ended up shown were then read the same way.

**Rounds.** Round 1: 209 shown units read. Round 2: 11 newly promoted. Round 3: 6. Round 4: none left. The 23 seeded
units were then read, 4 of them changed to remove, and the next run promoted nobody unreviewed. Stable at 210.

**Verdicts written: 352.** remove 111, asterisk 59, ok 182. Of the removes, 41 are unread siblings in four buildings
whose listing page is months old (80East 35, Hudson 44 4, Park Place Towers 1, Sono Pearl 1): the building's evidence
had been read and the same reason applies to every unit not seen live. By kind, remove: unverified 77, not available
12, dogs 6, elevator 6, wrong building 4, floor 2, restricted 2, co-op 1, lease term 1. Asterisk: unverified 17, lease
term 14, not available 11, elevator 6, dogs 4, condo 4, wrong building 2, floor 1.

**How I judged, where the owner's rules leave room** (all of this is in the `why` column, unit by unit):

- A listing page last changed more than 60 days before the check, with no date for the unit in the last 60 days and no
  second source: one open item ("is it still available"). The same for an availability date more than six months old,
  and wherever the checker wrote "confirm by phone" or "may be stale". With another open item: removed.
- A row that is a floor plan (no unit number): removed. Its floor and its availability are both unknown.
- A unit in a condominium building rented by its owner: asterisk "confirm the building's rental rules" (4 units; 2 are
  shown, 2 have a second open item).
- An elevator that appears only in a listing site's amenity list while the owner's own feature list omits it: open
  (Avalon Maplewood, as the checker ruled for Avalon Princeton).
- "Weight restrictions apply" with no pound figure: passes, like "small dogs" (Grand Imperial, Imperial, Continuum, The
  Leaf, 66 Main). These carry no asterisk and no tour question yet.
- The five D18 units the checker called "fine (asterisk present)" are out: a floor asterisk plus "listing last modified
  in August: confirm by phone" is two things to confirm.

## Defect by defect

"Before" and "after" count the units the report names unless stated otherwise.

| | Status | What changed, and where | Rows before → after |
|---|---|---|---|
| D1 unverified, stale and floor-plan listings | **Fixed** by verdicts and one rule | `rank.py`: a row with no unit label on a building page is a floor plan and carries the open item "availability" beside its unknown floor, so it is always sketchy. Staleness has no rule (see "weak"): it is caught by the verdict review. | 28 shown → 1 shown with an asterisk (Arcade 302, which the manager's own page lists as available); 14 removed by verdict, 11 sketchy, 2 merged. No floor-plan row is shown (29 before). |
| D2 units nobody read on an allowed page | **Fixed** | `build_master.py` (evidence loop): an evidence row marked `unconfirmed`, with no confirmed row for the same fact in the building, now opens the fact (`elevator_evidence_open`, `dogs_evidence_open`) instead of leaving the harvester's value. 381 units in 111 buildings have the elevator opened this way, 60 units in 49 buildings the dog policy. | 6 shown → 0 (all removed by verdict; each also has two or more facts open by rule) |
| D3 "dogs explicitly allowed" | **Fixed** | `parsers.dogs_not_explicit`, used in `build_master.py` on every dog row whatever its status: "upon approval", "case by case", "dogs not named", "species not stated", "no policy text", and an aggregator's policy block whose only text is "contact for more information on pet policy" (unless another page names dogs). `rank.py`: `dogs_evidence_open` is an open fact. | 11 shown → 1 shown with the dogs asterisk (Third & Valley 344); 7 removed, 3 sketchy |
| D4 accessibility lift counted as an elevator; "confirmed" from the city's class alone | **Fixed** | `build_master.py`: a confirm row whose only evidence is the PLUTO class becomes `official_record`, and an elevator may rest on the official record only when the lot is the listing's own address and the city's device list does not show zero active passenger elevators (`dob_active_elevators`). `nyc_building_records.py:589` now counts only active elevators (takes effect on its next run; the output file was not regenerated). `check_registry.py` asserts it. | 2561 Bedford Ave 3B: shown, nothing to confirm → removed. 7 buildings have zero active elevators on record. |
| D5 dead `\\b` in the co-op pattern; condos | **Fixed** | `avoid.py`: `COOP` uses real word boundaries; `NOT_COOP` keeps out "Co-op City" and a harvester's "condo/co-op or owner-rented" note. The other patterns added that night were checked: none has the slip, and `test_rules.py` asserts that no pattern in the file contains a doubled backslash and that each matches its own example. Condos: by verdict (owner's rule). | 8300 Boulevard E 4D: shown → removed (rule and verdict). Co-op exclusion rows 40 → 56, buildings 24 → 25. |
| D6 wrong-building and "verify the lister" warnings | **Fixed** | `build_master.py`: `address_mismatch`, `listing_address_mismatch`, `address_note` now reach `listing_warning`; `rank.py` reads the column: an open item "listing" (38 units carry one). | 4 shown → 0 (3 removed, 1 sketchy) |
| D7 elevator "in select buildings"; 55+ community | **Fixed** | D2's rule opens the elevator; the 55+ note is a verdict (`restricted`). | 5 shown → 0 |
| D8 price valid only on a 15 to 24-month lease | **Fixed** | `parsers.lease_term_from_text`; `build_master.py` reads the term from the unit's live-check note, then the building's lease-term facts (`lease_term_of_listed_price`, `lease_term_priced`, `price_basis`: now mapped), then the listing's own price basis ("15-month lease"). New unit columns `price_lease_months`, `price_12_month`, `price_lease_quote`, `price_lowest_of_terms`. `all_in.py`: where the 12-month price is known the cost, and so the cap, uses it. `rank.py`: a term over 13 months is the open item "lease term", with the term and the 12-month price in the sentence. | 15 shown with no notice → 11 shown with the asterisk, 3 sketchy, 1 removed. In the whole master 317 units are priced for 14 months or more; the page gives the 12-month price for 2. Avalon Somerville 022-265: cost now on $2,430, all-in $2,696 → $2,786. |
| D9 elevator not established | **Fixed** | D2's rule, D16's rule and verdicts. | 8 shown with no asterisk → 3 shown with the elevator asterisk, 3 sketchy, 2 removed |
| D10 floors labelled "stated" or "confirmed" that are neither | **Fixed** | `parsers.floor_from_description` (a phrase about an amenity is not the unit's floor; two unit phrases that disagree give none); `build_master.py` re-reads the cached page for every floor the harvester took from a description; `h_trulia.py:297` uses the same function on the next harvest. "Inferred from the unit number" is now read in the quote as well as the value. A floor row with no unit label lands on the unit its quote names. An evidence row that says the floor is unknown now beats a reading of the label (100 W 139th St 27A: six-floor building). | Confirmed floors in the master 80 → 68, stated 146 → 138. Shown: 26 confirmed, 1 stated, 132 read from the unit number, 51 unknown. Avalon Somerville 022-265 now floor 2, confirmed. |
| D11 no-unit rows sharing one live check | **Fixed** | `build_master.py`: a row with no unit number takes a live-check row only when that row names its plan, its stored label or its price, or is the building's only such row and only such check. | Park Place Towers' $2,683 plan no longer carries $2,438; Glen Cove, The Mark and The Riverhouse plans carry their own check or none. |
| D12 unknown cost lines near the cap | **Fixed as instructed; no number invented** | `all_in.py`: `all_in_unknown_count` (how many of pet rent, parking, required fees are unknown) and `cap_margin` (3,000 − all-in). `rank.py`: all-in of $2,900 or more with any of the three unknown is the open item "cost near the cap". | Of the report's 19 units: 2 shown with the asterisk, 13 sketchy, 3 removed, 1 not shown. Among all 210 shown: 21 are at $2,900 or more; 12 have an unknown line and carry the asterisk; 9 have all three lines stated. 109 units in the whole master are sketchy partly for this reason. Unknown and counted as $0 among the 210 shown: pet rent 117, parking 165, required fees 144, all three 85. Smallest margin shown: $2. |
| D13 required fees double counted | **Fixed, one case left** | `parsers.monthly_fees_from_text`: a total followed by its own breakdown in brackets counts once; a range counts once, at its high end. `all_in.py`: a fee line that prices internet removes the internet estimate. | Fee line changed on 45 units, all downward. Scribe and The Asher $200 → $100, Quarry Walk $80 → $45, Atlas all-in −$75. **Left:** The Botanic stays at $295 (Zumper's "flat utilities fee") against $97.55 (Apartment List): two sources differ and the higher is kept on purpose. |
| D14 net-effective rents invented | **Fixed, wider than reported** | `rent_terms.py`: a sentence saying the page does *not* say whether the price is net-effective was being read as a net-effective statement. `NET_NEG` now covers those sentences, and a negation is no longer overridden. | 159 units lose the label (404 → 244 net-effective in the master), 13 of them shown. All-in is unchanged for them; the gross figure no longer carries an invented mark-up (Scribe 508 gross $3,340 → $2,755). |
| D15 individual wrong numbers | **Fixed** | 2072 20th Ln 6E: a price quoted from another listing in brackets no longer sets the fee (`parsers.parse_parking`); parking is unknown again. Avalon Maplewood: the live price is used whenever the check saw the listing, not only for status "changed". Avalon Teaneck: `scripts/ev_ic2_live.py` writes the checker's own 23:21 UTC reading ($2,521) as a live-check row. Metrovue, Metro Point: a "total price" already holds the required fees, so the fee line is a stated $0. | Rent line from a live check: 9 → 20 units. |
| D16 neighbouring tax lots | **Fixed** | `parsers.lot_address_agrees`; `build_master.py` writes `pluto_lot_ok` and uses the city's elevator class, floor count, year and unit count only when the lot's address is the listing's (same number, or inside the lot's range, same street). | 63 of 202 matched buildings are on another lot's record. 9 units lose a PLUTO-only elevator. 11 shown units sit on such a lot; each has its elevator from the listing. |
| D17 the same apartment twice | **Fixed** | `parsers.unit_label_key`: "1 bed, 1 bath, $1675" is a plan description, not a unit label, so the duplicate rule sees it. | Arcade's unnamed twin and The Cove's second row are merged (25 duplicates in all). |
| D18 stale availability dates | **Fixed by verdicts only** | No rule. | 8 → 3 shown with the asterisk (Hedges 409, Mercer 8F, Chateau Rive 304), 5 sketchy |
| D19 selection not stable | **Fixed** | `rank.py`: stable sort on neighborhood, dominated, score, seen live first, `listing_id`. Two consecutive runs give a byte-identical `ranked_units.csv`; `test_rules.py --data` checks the order. | – |
| D20 resident quotes | **Fixed** | `build_page_data.py` keeps `source_area` and adds `about` where the quote's area is wider than or different from the neighborhood (197 quotes say "about Flushing", "about Harlem" and so on; the page shows it). `data/voices/quote_exclusions.csv` drops the North Plainfield quote and the one naming its writer by office. | 2 quotes dropped |
| D21 street parking at $0 | **No defect found by the checker; note added** | The $0 line now says why ("street parking only, per a listing for this building"). | 14 units |
| 62 Treat St exclusion too broad | **Fixed** | `avoid.py`: when a ground-floor reading names no unit, the rule excludes the floor-plan row the text names, or the building's only row; otherwise nothing, and the reading goes to `data/reference/ground_reading_unassigned.csv`. `unit_exclusions.csv` has a `listing_id` column for this. | Plan "103" excluded; plan "208" no longer excluded with it |

## Tests

`scripts/test_rules.py`: 78 checks on the rules and parsers (first step of `run_all.py`, with the 259 parser tests) and
88 checks on the output (`--data`, after ranking), using the report's rows. `check_registry.py` gained the review rule,
the lot and device rule, and the new open items. `run_all.py --fast`, `build_page_data.py` and `build_site.py` pass.
The page's script was syntax-checked with Node; it was **not** opened in a browser in this pass.

## What is still weak

1. **Staleness has no rule.** `listing_age_days` is blank for building-page rows, and the page's "last modified" date
   lives only in checkers' notes. Every stale listing caught here was caught by reading. The hash forces a new reading
   when evidence changes, but a new unit promoted in a building whose evidence has not changed is only blocked, not
   judged, until someone reads it.
2. **The same evidence is "confirmed" in some batches and "unconfirmed" in others.** "Elevator in a listing site's
   amenity list" (mostly Apartment List, whose lists come from the manager's feed) is marked confirmed by batches 1, 2,
   8 and 9 and unconfirmed by batches 10 and 15. So the elevator is settled on that evidence alone for **33 shown
   buildings (47 shown units)**, among them Bay One, Cobalt Lofts, Atlas, Portside Towers, Solaris Lofts, The Wyldes,
   Stella, The Brick, Vivian and Two Clinton Park, and open for Avalon Wayne and Grandville Towers on the same kind of
   evidence. I did not re-grade other agents' statuses, except Avalon Maplewood, where the note itself says the
   owner's list omits it. This is the largest remaining soft spot in the shown list.
3. **132 of 210 shown floors are read from the unit number** and accepted because they come out at 3 or higher; 51 more
   are unknown (the floor asterisk). Only 27 are confirmed or stated.
4. **Trulia could not be re-checked** (blocking since the evening of Nov 15): 119 of the 210 shown units are Trulia
   rows; their prices and dates are as last read on Nov 15.
5. **Costs:** 85 shown units have pet rent, parking and fees all unknown and counted as $0. Below $2,900 they carry no
   asterisk for it.
6. **Avoid cards (33), held units (53) and units waiting for a live check (53) were not reviewed.** They appear on the
   page; none is a "place".
7. **1 shown unit has no evidence rows at all** (525 Riverdale Ave 5U, Yonkers): it is shown with the live-check asterisk
   on the harvester's facts alone.
8. The Botanic's fee (D13) and the lease-term asterisk on 6-, 10- and 11-month prices (not flagged; only terms over 13
   months are).
9. My verdicts are one reader's judgement made from a digest. The thresholds I used (60 days, six months) are mine.

## For the owner to decide

1. (Decided 2026-11-16: lease term and cost near the cap are disclosures.)
2. **The seven "must remove" units that are back** (see the top of this file), and floor-plan rows in general: 14 rows with
   no unit number are shown with the asterisk "availability" where the page shows units available; rows on a page with
   0 units available are removed.
3. **Staleness thresholds**: a page unchanged for more than 60 days, or an availability date more than six months old, is one open item; a page unchanged for more than six months is removed. Stricter or looser?
4. **Condo units rented by their owner** are kept with an asterisk; two are shown (623 Avenue H 6C, 2781 Ocean Ave 6E).
5. **"Weight restrictions apply", no number**: treated like "small dogs" (passes). Say if it should be an asterisk.
6. **Elevator known only from a listing site's amenity list** (point 2 above): accept, or open it everywhere? (The
   count of 33 buildings and 47 units was taken at stage A; it is higher among the 326.)
7. **Buildings the evidence pass never touched** (86 ranked units, many in Stamford): not shown, by a rule I added,
   because there is nothing to read. They need an evidence batch, or a decision to show them on the harvester's facts.
8. **First-floor readings by pattern**: I removed 49 units whose number reads as floor 1 under the building's numbering.
   Where the pattern is my inference from sibling units (Halstead Parsippany, TGM Anchor Point), some may be upper floors.
