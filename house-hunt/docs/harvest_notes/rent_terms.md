# Rent terms (scripts/rent_terms.py -> data/rent_terms.csv)

Rebuilt from data/units.csv, each unit's cached page (`raw_path`) and data/evidence/*.csv. No network requests. Every passing unit was checked and has one row.

- Units checked: **1524** (one row each; `offer_type = none` for units with no such language).
- Units with any concession, special-offer or price-basis language: **516**.
- Units whose price or offer is for a lease term other than 12 months: **310**.
- Units that need a call (`needs_call = yes`): **487** in 86 buildings.

## Counts by offer_type

| offer_type | units |
|---|---|
| none | 1008 |
| months_free | 437 |
| other | 55 |
| reduced_deposit_or_fee | 17 |
| dollar_credit | 5 |
| look_and_lease | 2 |

## Listed price basis

| listed_price_is | units |
|---|---|
| gross | 1045 |
| unknown | 395 |
| net_effective | 84 |

## Confidence

| confidence | units |
|---|---|
| stated_on_page | 1039 |
| assumed_terms | 485 |

## Free-period timing

| timing | units |
|---|---|
| (no free period) | 1087 |
| unknown | 425 |
| end_of_lease | 7 |
| specific_months | 3 |
| upfront | 2 |

## Gross rent above the listed price (stated or computed from stated terms)

**2** units have a determined gross rent above the listed price.

| unit | listed | gross | gap | free months / lease | confidence |
|---|---|---|---|---|---|
| Alvista Rise #2410 | 2365 | 2800 | 435 | 2.5 / 18 | stated_on_page |
| Alvista Rise #1922 | 2435 | 2825 | 390 | 2.5 / 18 | stated_on_page |

## Largest possible gaps where the basis is unknown (scenario: listed price is net-effective)

433 units carry a scenario figure. These are **not** stated rents: they show what the monthly rent would be if the advertised price already has the free months spread in. Top 25:

| unit | listed | gross if listed is net | gap | free months / lease | basis |
|---|---|---|---|---|---|
| Aviva #E0809 | 2797 | 4040 | 1243 | 4 / 13 | net_effective |
| Aviva #E0710 | 2780 | 4016 | 1236 | 4 / 13 | net_effective |
| Aviva #E0708 | 2772 | 4004 | 1232 | 4 / 13 | net_effective |
| Aviva #E0808 | 2772 | 4004 | 1232 | 4 / 13 | net_effective |
| Aviva #E0410 | 2760 | 3987 | 1227 | 4 / 13 | net_effective |
| Aviva #E0709 | 2756 | 3981 | 1225 | 4 / 13 | net_effective |
| Aviva #E0510 | 2747 | 3968 | 1221 | 4 / 13 | net_effective |
| Aviva #W1009 | 2739 | 3956 | 1217 | 4 / 13 | net_effective |
| Aviva #E0508 | 2739 | 3956 | 1217 | 4 / 13 | net_effective |
| Aviva #E0509 | 2723 | 3933 | 1210 | 4 / 13 | net_effective |
| Aviva #W1122 | 2718 | 3926 | 1208 | 4 / 13 | net_effective |
| Aviva #W0809 | 2718 | 3926 | 1208 | 4 / 13 | net_effective |
| Aviva #W1109 | 2718 | 3926 | 1208 | 4 / 13 | net_effective |
| Aviva #E0310 | 2718 | 3926 | 1208 | 4 / 13 | net_effective |
| Aviva #E0308 | 2710 | 3914 | 1204 | 4 / 13 | net_effective |
| Aviva #E0408 | 2710 | 3914 | 1204 | 4 / 13 | net_effective |
| Aviva #W0922 | 2698 | 3897 | 1199 | 4 / 13 | net_effective |
| Aviva #W0909 | 2698 | 3897 | 1199 | 4 / 13 | net_effective |
| Aviva #E0309 | 2694 | 3891 | 1197 | 4 / 13 | net_effective |
| Aviva #W0609 | 2686 | 3880 | 1194 | 4 / 13 | net_effective |
| Aviva #W0722 | 2677 | 3867 | 1190 | 4 / 13 | net_effective |
| Aviva #W0709 | 2677 | 3867 | 1190 | 4 / 13 | net_effective |
| Aviva #W0522 | 2644 | 3819 | 1175 | 4 / 13 | net_effective |
| Aviva #W0509 | 2644 | 3819 | 1175 | 4 / 13 | net_effective |
| Aviva #W1022 | 2616 | 3779 | 1163 | 4 / 13 | net_effective |

## Gross rent over $3,000 (rent only, all-in aside)

- Determined gross over $3,000: **0** units.
- Scenario gross over $3,000 (upper end, if the listed price is net-effective): **201** units in 24 buildings.

| building | units | listed range | scenario gross (max) | free months / lease |
|---|---|---|---|---|
| Aviva | 62 | 2348-2797 | 4040 | 4 / 13 |
| The Jefferson | 3 | 2740-2840 | 3787 | 3 / 12 assumed |
| The Alary | 8 | 2538-2773 | 3697 | 3 / 12 assumed |
| 360 State | 47 | 2257-2646 | 3528 | 3 / 12 assumed |
| Aura 240 | 1 | 2595-2595 | 3460 | 3 / 12 assumed |
| EDGE | 14 | 2513-2837 | 3404 | 2 / 12 |
| The Current on River | 4 | 2595-2825 | 3390 | 2 / 12 |
| Riello Edgewater | 1 | 2800-2800 | 3360 | 2 / 12 assumed |
| Skyline New Rochelle | 7 | 2640-2795 | 3354 | 2 / 12 assumed |
| The Atwater | 26 | 2538-2785 | 3342 | 1-2 / 12 assumed |
| Arc House | 2 | 2300-2500 | 3333 | 3 / 12 assumed |
| West Side Square | 1 | 2636-2636 | 3330 | 2.5 / 12 assumed |
| The Liberty Building | 2 | 2277-2477 | 3303 | 2-3 / 12 assumed |
| Hudson 44 | 3 | 2595-2750 | 3300 | 2 / 12 assumed |
| Bedford Hall Apartments | 5 | 2635-2735 | 3282 | 2 / 12 assumed |
| Carraway | 2 | 2700-2795 | 3194 | 1.5 / 12 |
| Atlas | 2 | 2573-2651 | 3181 | 2 / 12 |
| Metrovue | 4 | 2825-2825 | 3082 | 1 / 12 |
| Fairfield Metro at Glen Cove | 1 | 2820-2820 | 3076 | 1 / 12 assumed |
| Noble' | 1 | 2550-2550 | 3060 | 0-2 / 12 assumed |
| Admirals Cove | 1 | 2795-2795 | 3049 | 1 / 12 assumed |
| The Mitchell | 1 | 2781-2781 | 3034 | 1 / 12 assumed |
| 1 Martine at City Square | 1 | 2775-2775 | 3027 | 1 / 12 assumed |
| 80East | Luxury Apartments | Dover, NJ | 2 | 2800-2800 | 3015 | 1 / 14 |

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
