# Rent terms (scripts/rent_terms.py -> data/rent_terms.csv)

Rebuilt from data/units.csv, each unit's cached page (`raw_path`) and data/evidence/*.csv. No network requests. Every passing unit was checked and has one row.

- Units checked: **1524** (one row each; `offer_type = none` for units with no such language).
- Units with any concession, special-offer or price-basis language: **874**.
- Units whose price or offer is for a lease term other than 12 months: **328**.
- Units that need a call (`needs_call = yes`): **792** in 149 buildings.

## Counts by offer_type

| offer_type | units |
|---|---|
| months_free | 709 |
| none | 650 |
| other | 64 |
| reduced_deposit_or_fee | 58 |
| look_and_lease | 18 |
| dollar_credit | 16 |
| weeks_free | 9 |

## Listed price basis

| listed_price_is | units |
|---|---|
| gross | 753 |
| unknown | 683 |
| net_effective | 88 |

## Confidence

| confidence | units |
|---|---|
| assumed_terms | 781 |
| stated_on_page | 721 |
| computed_from_stated_terms | 22 |

## Free-period timing

| timing | units |
|---|---|
| (no free period) | 806 |
| unknown | 692 |
| upfront | 17 |
| end_of_lease | 7 |
| specific_months | 1 |
| spread_monthly | 1 |

## Gross rent above the listed price (stated or computed from stated terms)

**9** units have a determined gross rent above the listed price.

| unit | listed | gross | gap | free months / lease | confidence |
|---|---|---|---|---|---|
| Alvista Rise #2410 | 2365 | 2800 | 435 | 2.5 / 18 | stated_on_page |
| Alvista Rise #1922 | 2435 | 2825 | 390 | 2.5 / 18 | stated_on_page |
| Harmony West | 2562 | 2776 | 214 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2492 | 2700 | 208 | 1 / 13 | computed_from_stated_terms |
| Arc House | 2500 | 2708 | 208 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2423 | 2625 | 202 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2377 | 2575 | 198 | 1 / 13 | computed_from_stated_terms |
| Arc House | 2300 | 2492 | 192 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2077 | 2250 | 173 | 1 / 13 | computed_from_stated_terms |

## Largest possible gaps where the basis is unknown (scenario: listed price is net-effective)

707 units carry a scenario figure. These are **not** stated rents: they show what the monthly rent would be if the advertised price already has the free months spread in. Top 25:

| unit | listed | gross if listed is net | gap | free months / lease | basis |
|---|---|---|---|---|---|
| The Jefferson #462 | 2840 | 3787 | 947 | 3 / 12 assumed | unknown |
| The Jefferson #576 | 2840 | 3787 | 947 | 3 / 12 assumed | unknown |
| The Alary | 2773 | 3697 | 924 | 3 / 12 assumed | unknown |
| Halstead Parsippany #2453 | 2757 | 3676 | 919 | 3 / 12 | unknown |
| Halstead Parsippany #2459 | 2757 | 3676 | 919 | 3 / 12 | unknown |
| Halstead Parsippany #2463 | 2757 | 3676 | 919 | 3 / 12 | unknown |
| The Jefferson | 2740 | 3653 | 913 | 3 / 12 assumed | unknown |
| The Alary | 2723 | 3631 | 908 | 3 / 12 assumed | unknown |
| Halstead Parsippany #1425 | 2700 | 3600 | 900 | 3 / 12 | unknown |
| Halstead Parsippany #1317 | 2690 | 3587 | 897 | 3 / 12 | unknown |
| Halstead Parsippany #1223 | 2668 | 3557 | 889 | 3 / 12 | unknown |
| Halstead Parsippany #1323 | 2668 | 3557 | 889 | 3 / 12 | unknown |
| Halstead Parsippany #2158 | 2655 | 3540 | 885 | 3 / 12 | unknown |
| The Alary | 2655 | 3540 | 885 | 3 / 12 assumed | unknown |
| 360 State #2806 | 2646 | 3528 | 882 | 3 / 12 assumed | unknown |
| The Alary | 2625 | 3500 | 875 | 3 / 12 assumed | unknown |
| 360 State #2707 | 2615 | 3487 | 872 | 3 / 12 assumed | unknown |
| 360 State #2007 | 2609 | 3479 | 870 | 3 / 12 assumed | unknown |
| The Alary | 2608 | 3477 | 869 | 3 / 12 assumed | unknown |
| 360 State #1907 | 2604 | 3472 | 868 | 3 / 12 assumed | unknown |
| The Alary | 2600 | 3467 | 867 | 3 / 12 assumed | unknown |
| 360 State #1807 | 2599 | 3465 | 866 | 3 / 12 assumed | unknown |
| 360 State #2407 | 2599 | 3465 | 866 | 3 / 12 assumed | unknown |
| Aura 240 | 2595 | 3460 | 865 | 3 / 12 assumed | unknown |
| 360 State #2907 | 2593 | 3457 | 864 | 3 / 12 assumed | unknown |

## Gross rent over $3,000 (rent only, all-in aside)

- Determined gross over $3,000: **0** units.
- Scenario gross over $3,000 (upper end, if the listed price is net-effective): **261** units in 40 buildings.

| building | units | listed range | scenario gross (max) | free months / lease |
|---|---|---|---|---|
| The Jefferson | 3 | 2740-2840 | 3787 | 3 / 12 assumed |
| The Alary | 8 | 2538-2773 | 3697 | 3 / 12 assumed |
| Halstead Parsippany | 19 | 2384-2757 | 3676 | 3 / 12 |
| 360 State | 47 | 2257-2646 | 3528 | 3 / 12 assumed |
| West Side Square | 35 | 2439-2747 | 3470 | 2.5 / 12 |
| Aura 240 | 1 | 2595-2595 | 3460 | 3 / 12 assumed |
| Piper | 14 | 2499-2700 | 3411 | 2.5 / 12 |
| EDGE | 14 | 2513-2837 | 3404 | 2 / 12 |
| The Current on River | 4 | 2595-2825 | 3390 | 2 / 12 |
| 51 South | 2 | 2808-2808 | 3370 | 2 / 12 |
| Riello Edgewater | 1 | 2800-2800 | 3360 | 2 / 12 assumed |
| Skyline New Rochelle | 7 | 2640-2795 | 3354 | 2 / 12 assumed |
| FIAT House | 1 | 2765-2765 | 3318 | 1 / 6 |
| Aviva | 40 | 2541-2797 | 3306 | 2 / 13 |
| Hudson 44 | 3 | 2595-2750 | 3300 | 2 / 12 assumed |
| Bedford Hall Apartments | 5 | 2635-2735 | 3282 | 2 / 12 assumed |
| 500 PARQ | 5 | 2560-2733 | 3280 | 2 / 12 |
| Clifton & Co. | 10 | 2533-2724 | 3269 | 2 / 12 |
| The Leaf | 6 | 2573-2693 | 3232 | 2 / 12 |
| Carraway | 2 | 2700-2795 | 3194 | 1.5 / 12 |
| The Walcott Hackensack | 3 | 2610-2763 | 3188 | 2 / 15 |
| Atlas | 2 | 2573-2651 | 3181 | 2 / 12 |
| Avalon Wayne | 1 | 2645-2645 | 3174 | 2 / 12 |
| 75 Tresser | 3 | 2665-2765 | 3126 | 1.38 / 12 |
| Parc at Glenbrook Apartments | 1 | 2598-2598 | 3118 | 1.5-2 / 12 assumed |
| Metrovue | 4 | 2825-2825 | 3082 | 1 / 12 |
| The Rail at North Bergen | 3 | 2778-2813 | 3069 | 0.5 / 6 |
| Reserve at Riverdale | 1 | 2753-2753 | 3059 | 1 / 10 |
| Avalon Yonkers | 1 | 2675-2675 | 3057 | 1.5 / 12 |
| The Liberty Building | 1 | 2477-2477 | 3049 | 2-3 / 12 assumed |
| Admirals Cove | 1 | 2795-2795 | 3049 | 1 / 12 assumed |
| The Hazel Jersey City | 1 | 2776-2776 | 3045 | 1-1.5 / 17 |
| 1177 Greens Farms | 1 | 2735-2735 | 3039 | 1 / 10 |
| The Mitchell | 1 | 2781-2781 | 3034 | 1 / 12 assumed |
| Avalon Teaneck | 2 | 2760-2780 | 3033 | 1 / 12 |
| Summer House | 2 | 2575-2599 | 3032 | 2 / 14 |
| 1 Martine at City Square | 1 | 2775-2775 | 3027 | 1 / 12 assumed |
| The Atwater | 2 | 2785-2785 | 3017 | 1-2 / 12 assumed |
| 80East / Luxury Apartments / Dover, NJ | 2 | 2800-2800 | 3015 | 1 / 14 |
| The Confluence at Norwalk | 1 | 2761-2761 | 3012 | 1 / 12 |

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
