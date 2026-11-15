# Data-use audit (2026-11-15): what was collected but is not yet used

Prompted by Will after the car-crime miss (police-located car crime near NYC buildings had been collected but was
not applied in the avoid rule). Checked against `data/ranked_units.csv` (1,143 ranked units, 412 shown).

## A. Affects whether a unit should be shown at all
1. **All-in cost is incomplete.** `enrich_units.py` adds only the fees present in the listing row. Not merged:
   parking fees from `building_amenities.csv` (68 of 576 buildings) and from the evidence pass (`facts_batch_*`:
   90 parking facts, 29 required-fee facts, 51 pet-rent facts); `community_required_fees` (28 units).
   213 units carry concession or net-effective language: the gross rent may be higher than the listed figure.
   `utilities_included` is stated for 102 units but ignored, so utilities are double-counted there.
2. **Confirmations are not written back.** The evidence pass confirmed elevator (175 rows), floor (105) and dog
   weight (34), but `confidence` and `to_confirm` are unchanged: 268 of the 412 shown units are still
   `one_inferred`, and the rule "confirm before showing" is not enforced.
3. **Live-check price changes are not applied** (2 rows).

## B. Affects ranking
4. **Violent crime near the building and at night** (NYC: robbery, felony assault, burglary within 250 m; share
   between 19:00 and 24:00; comparison with borough median) is collected in `data/enriched/*.json` and unused.
5. **Tolls incomplete** for 262 of 412 shown units (MTA crossing rates never obtained); scored as unknown.
6. **Transit:** only the Saturday median is used. Transfers, last train home on Saturday night and the Sunday
   return are collected and unused.
7. **NYC records:** bedbug filings, evictions, noise and illegal-parking complaints are collected and unused.
8. **Crime trend** (three years) and burglary rate are collected and unused.
9. **Taxes** (`data/reference/taxes.csv`): the NYC resident income tax and other local differences are not in any
   cost figure.
10. **Lifestyle texture:** about 25 of the 40 `places.color()` variables are unused (many are thinly mapped).

## C. Planned but never collected
Street-parking rules by municipality; dog rules (leash, licensing, dog-park access); flood zone; broadband and
fiber; noise; renter protections (fetch started, never finished); Reddit (no API key); neighborhood-level resident
voices (only building-level evidence exists); photos; Jersey City split into neighborhoods; MTA toll rates.

## D. Collected and superseded
Phase 1 tables for the original 98 areas (`data/metrics/acs.csv`, partial `safety_nyc.csv`, `walkability.csv`).
