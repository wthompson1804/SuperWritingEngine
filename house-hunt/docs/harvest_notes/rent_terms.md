# Rent terms (scripts/rent_terms.py -> data/rent_terms.csv)

Rebuilt from data/units.csv, each unit's cached page (`raw_path`) and data/evidence/*.csv. No network requests. Every passing unit was checked and has one row.

- Units checked: **1179** (one row each; `offer_type = none` for units with no such language).
- Units with any concession, special-offer or price-basis language: **544**.
- Units whose price or offer is for a lease term other than 12 months: **148**.
- Units that need a call (`needs_call = yes`): **411** in 136 buildings.

## Counts by offer_type

| offer_type | units |
|---|---|
| none | 635 |
| months_free | 312 |
| other | 115 |
| dollar_credit | 47 |
| reduced_deposit_or_fee | 44 |
| look_and_lease | 22 |
| weeks_free | 4 |

## Listed price basis

| listed_price_is | units |
|---|---|
| gross | 815 |
| unknown | 352 |
| net_effective | 12 |

## Confidence

| confidence | units |
|---|---|
| stated_on_page | 760 |
| assumed_terms | 408 |
| computed_from_stated_terms | 11 |

## Free-period timing

| timing | units |
|---|---|
| (no free period) | 863 |
| unknown | 286 |
| upfront | 22 |
| specific_months | 8 |

## Gross rent above the listed price (stated or computed from stated terms)

**3** units have a determined gross rent above the listed price.

| unit | listed | gross | gap | free months / lease | confidence |
|---|---|---|---|---|---|
| The Riverhouse | 2025 | 2430 | 405 | 3 / 18 | computed_from_stated_terms |
| The Riverhouse | 1975 | 2370 | 395 | 3 / 18 | computed_from_stated_terms |
| Harmony West | 2077 | 2250 | 173 | 1 / 13 | computed_from_stated_terms |

## Largest possible gaps where the basis is unknown (scenario: listed price is net-effective)

313 units carry a scenario figure. These are **not** stated rents: they show what the monthly rent would be if the advertised price already has the free months spread in. Top 25:

| unit | listed | gross if listed is net | gap | free months / lease | basis |
|---|---|---|---|---|---|
| Axis 201 #0361 | 2017 | 4034 | 2017 | 3 / 6 | unknown |
| Axis 201 #0551 | 2007 | 4014 | 2007 | 3 / 6 | unknown |
| Axis 201 #0340 | 1977 | 3954 | 1977 | 3 / 6 | unknown |
| Axis 201 #0649 | 1964 | 3928 | 1964 | 3 / 6 | unknown |
| Axis 201 #0656 | 1867 | 3734 | 1867 | 3 / 6 | unknown |
| Axis 201 #0460 | 1862 | 3724 | 1862 | 3 / 6 | unknown |
| Axis 201 #1083 | 1822 | 3644 | 1822 | 3 / 6 | unknown |
| Axis 201 #0249 | 1805 | 3610 | 1805 | 3 / 6 | unknown |
| The Taft Apartments #12K | 2160 | 3240 | 1080 | 3 / 9 | unknown |
| The Taft Apartments #11A | 1960 | 2940 | 980 | 3 / 9 | unknown |
| The Taft Apartments #14A | 1950 | 2925 | 975 | 3 / 9 | unknown |
| The Taft Apartments #04A | 1945 | 2918 | 973 | 3 / 9 | unknown |
| The Taft Apartments #04R | 1945 | 2918 | 973 | 3 / 9 | unknown |
| The Taft Apartments #08A | 1905 | 2721 | 816 | 3 / 10 | unknown |
| Halstead Parsippany #1106 | 2200 | 2933 | 733 | 3 / 12 | unknown |
| The Winston #457 | 2200 | 2933 | 733 | 3 / 12 | unknown |
| The Whit #673-208 | 2190 | 2920 | 730 | 3 / 12 assumed | unknown |
| The Winston #504 | 2120 | 2827 | 707 | 3 / 12 | unknown |
| The Winston #357 | 2100 | 2800 | 700 | 3 / 12 | unknown |
| The Winston #257 | 2090 | 2787 | 697 | 3 / 12 | unknown |
| Acme Timber Lofts #5D | 2020 | 2693 | 673 | 3 / 12 | unknown |
| The Winston #231 | 1980 | 2640 | 660 | 3 / 12 | unknown |
| The Winston #217 | 1950 | 2600 | 650 | 3 / 12 | unknown |
| The Winston #240 | 1950 | 2600 | 650 | 3 / 12 | unknown |
| The Winston #317 | 1950 | 2600 | 650 | 3 / 12 | unknown |

## Gross rent over $3,000 (rent only, all-in aside)

- Determined gross over $3,000: **0** units.
- Scenario gross over $3,000 (upper end, if the listed price is net-effective): **9** units in 2 buildings.

| building | units | listed range | scenario gross (max) | free months / lease |
|---|---|---|---|---|
| Axis 201 | 8 | 1805-2017 | 4034 | 3 / 6 |
| The Taft Apartments | 1 | 2160-2160 | 3240 | 3 / 9 |

## Method and limits

- Offer text is verbatim from the cached listing page (Apartment List `specials[].raw_text`, Trulia / Zillow `specialOffers`, Zumper description and tags, Garden Communities special block), the stored `concession_text`, and evidence rows. Text marked `[live check]` or `[evidence]` is an earlier agent's note, not page wording.
- All 693 Apartment List rows had an empty `concession_text` in units.csv (the harvester read the wrong field); this script reads the offers from the cached pages instead.
- `listed_price_is` is `net_effective` only where a page or evidence row says so, `gross` where a gross rent is stated, confirmed, or there is no free-rent offer, and `unknown` for every other free-rent offer. Trulia's 'prices shown are base rent' label is not treated as proof of gross (Envy by Gomes shows net prices under it).
- Gross is never guessed. Net stated plus definite free months and lease term gives gross = net x lease / (lease - free). 'Up to', ranges and 'select units' are recorded as ranges with `assumed_terms` and a call.
- Scenario columns use a 12-month lease when neither the offer nor the price states a term; `computed_how` says so.
- First full payment assumes move-in on the available date (2026-12-01 when 'now') and rent due on the 1st. It is filled only when the timing is stated; otherwise `first_full_payment_note` gives the reason.
- Weeks free are converted at 12/52 months per week.
- Offers worded for other unit types (for example two-bedroom specials) are not applied to studios and one-bedrooms; the text is kept in `conditions`.
- Deadlines are copied from the offer; several fall on or before 2026-11-30 and may lapse before a tour.
