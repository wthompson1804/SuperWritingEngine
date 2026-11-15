# Rent terms (scripts/rent_terms.py -> data/rent_terms.csv)

Rebuilt from data/units.csv, each unit's cached page (`raw_path`) and data/evidence/*.csv. No network requests. Every passing unit was checked and has one row.

- Units checked: **2042** (one row each; `offer_type = none` for units with no such language).
- Units with any concession, special-offer or price-basis language: **1300**.
- Units whose price or offer is for a lease term other than 12 months: **464**.
- Units that need a call (`needs_call = yes`): **1175** in 189 buildings.

## Counts by offer_type

| offer_type | units |
|---|---|
| months_free | 1050 |
| none | 742 |
| other | 127 |
| reduced_deposit_or_fee | 51 |
| weeks_free | 29 |
| dollar_credit | 27 |
| look_and_lease | 16 |

## Listed price basis

| listed_price_is | units |
|---|---|
| unknown | 1058 |
| gross | 893 |
| net_effective | 91 |

## Confidence

| confidence | units |
|---|---|
| assumed_terms | 1163 |
| stated_on_page | 852 |
| computed_from_stated_terms | 27 |

## Free-period timing

| timing | units |
|---|---|
| unknown | 1026 |
| (no free period) | 963 |
| upfront | 40 |
| end_of_lease | 7 |
| specific_months | 5 |
| spread_monthly | 1 |

## Gross rent above the listed price (stated or computed from stated terms)

**12** units have a determined gross rent above the listed price.

| unit | listed | gross | gap | free months / lease | confidence |
|---|---|---|---|---|---|
| The Riverhouse | 2263 | 2716 | 453 | 3 / 18 | computed_from_stated_terms |
| Alvista Rise #2410 | 2365 | 2800 | 435 | 2.5 / 18 | stated_on_page |
| The Riverhouse | 2025 | 2430 | 405 | 3 / 18 | computed_from_stated_terms |
| The Riverhouse | 1975 | 2370 | 395 | 3 / 18 | computed_from_stated_terms |
| Alvista Rise #1922 | 2435 | 2825 | 390 | 2.5 / 18 | stated_on_page |
| Harmony West | 2562 | 2776 | 214 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2492 | 2700 | 208 | 1 / 13 | computed_from_stated_terms |
| Arc House | 2500 | 2708 | 208 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2423 | 2625 | 202 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2377 | 2575 | 198 | 1 / 13 | computed_from_stated_terms |
| Arc House | 2300 | 2492 | 192 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2077 | 2250 | 173 | 1 / 13 | computed_from_stated_terms |

## Largest possible gaps where the basis is unknown (scenario: listed price is net-effective)

1067 units carry a scenario figure. These are **not** stated rents: they show what the monthly rent would be if the advertised price already has the free months spread in. Top 25:

| unit | listed | gross if listed is net | gap | free months / lease | basis |
|---|---|---|---|---|---|
| Axis 201 #0259 | 2762 | 5524 | 2762 | 3 / 6 | unknown |
| Axis 201 #0209 | 2732 | 5464 | 2732 | 3 / 6 | unknown |
| Axis 201 #0213 | 2670 | 5340 | 2670 | 3 / 6 | unknown |
| Axis 201 #0317 | 2670 | 5340 | 2670 | 3 / 6 | unknown |
| Axis 201 #0417 | 2670 | 5340 | 2670 | 3 / 6 | unknown |
| Axis 201 #0418 | 2670 | 5340 | 2670 | 3 / 6 | unknown |
| Axis 201 #0432 | 2670 | 5340 | 2670 | 3 / 6 | unknown |
| Axis 201 #0532 | 2670 | 5340 | 2670 | 3 / 6 | unknown |
| Axis 201 #0332 | 2655 | 5310 | 2655 | 3 / 6 | unknown |
| Axis 201 #0225 | 2620 | 5240 | 2620 | 3 / 6 | unknown |
| Axis 201 #0214 | 2586 | 5172 | 2586 | 3 / 6 | unknown |
| Axis 201 #0309 | 2548 | 5096 | 2548 | 3 / 6 | unknown |
| Axis 201 #0509 | 2548 | 5096 | 2548 | 3 / 6 | unknown |
| Axis 201 #0205 | 2545 | 5090 | 2545 | 3 / 6 | unknown |
| Axis 201 #0206 | 2545 | 5090 | 2545 | 3 / 6 | unknown |
| Axis 201 #0216 | 2545 | 5090 | 2545 | 3 / 6 | unknown |
| Axis 201 #0221 | 2545 | 5090 | 2545 | 3 / 6 | unknown |
| Axis 201 #0222 | 2545 | 5090 | 2545 | 3 / 6 | unknown |
| Axis 201 #0223 | 2545 | 5090 | 2545 | 3 / 6 | unknown |
| Axis 201 #0412 | 2537 | 5074 | 2537 | 3 / 6 | unknown |
| Axis 201 #0247 | 2535 | 5070 | 2535 | 3 / 6 | unknown |
| Axis 201 #0355 | 2525 | 5050 | 2525 | 3 / 6 | unknown |
| Axis 201 #0310 | 2498 | 4996 | 2498 | 3 / 6 | unknown |
| Axis 201 #0466 | 2498 | 4996 | 2498 | 3 / 6 | unknown |
| Axis 201 #0261 | 2495 | 4990 | 2495 | 3 / 6 | unknown |

## Gross rent over $3,000 (rent only, all-in aside)

- Determined gross over $3,000: **0** units.
- Scenario gross over $3,000 (upper end, if the listed price is net-effective): **323** units in 50 buildings.

| building | units | listed range | scenario gross (max) | free months / lease |
|---|---|---|---|---|
| Axis 201 | 44 | 1805-2762 | 5524 | 3 / 6 |
| Brookside Wilton | 8 | 2650-2650 | 3975 | 2 / 6 |
| The Jefferson | 3 | 2740-2840 | 3787 | 3 / 12 assumed |
| The Alary | 8 | 2538-2773 | 3697 | 3 / 12 assumed |
| Halstead Parsippany | 19 | 2384-2757 | 3676 | 3 / 12 |
| The Taft Apartments | 3 | 2160-2435 | 3652 | 3 / 9 |
| The Winston | 25 | 2350-2630 | 3507 | 3 / 12 |
| West Side Square | 35 | 2439-2747 | 3470 | 2.5 / 12 |
| Aura 240 | 1 | 2595-2595 | 3460 | 3 / 12 assumed |
| Piper | 14 | 2499-2700 | 3411 | 2.5 / 12 |
| EDGE | 14 | 2513-2837 | 3404 | 2 / 12 |
| The Current on River | 5 | 2595-2825 | 3390 | 2 / 12 |
| 51 South | 2 | 2808-2808 | 3370 | 2 / 12 |
| Riello Edgewater | 1 | 2800-2800 | 3360 | 2 / 12 assumed |
| Skyline New Rochelle | 7 | 2640-2795 | 3354 | 2 / 12 assumed |
| Aviva | 40 | 2541-2797 | 3306 | 2 / 13 |
| Hudson 44 | 3 | 2595-2750 | 3300 | 2 / 12 assumed |
| Bedford Hall Apartments | 5 | 2635-2735 | 3282 | 2 / 12 assumed |
| 500 PARQ | 5 | 2560-2733 | 3280 | 2 / 12 |
| Clifton & Co. | 10 | 2533-2724 | 3269 | 2 / 12 |
| 360 State Street | 19 | 2454-2646 | 3257 | 3 / 16 |
| Twenty Fair | 1 | 2400-2400 | 3200 | 1-3 / 12 assumed |
| The Walcott Hackensack | 3 | 2610-2763 | 3188 | 2 / 15 |
| Harbor Pointe | 4 | 2774-2829 | 3183 | 2 / 18 |
| Atlas | 2 | 2573-2651 | 3181 | 2 / 12 |
| The Audubon New Haven | 5 | 2640-2778 | 3175 | 1.5 / 12 assumed |
| Avalon Wayne | 1 | 2645-2645 | 3174 | 2 / 12 |
| The Residences at Courthouse Square | 3 | 2650-2700 | 3150 | 2 / 14 |
| Scribe | 2 | 2509-2606 | 3127 | 2 / 12 assumed |
| 75 Tresser | 3 | 2665-2765 | 3126 | 1.38 / 12 |
| Parc at Glenbrook Apartments | 1 | 2598-2598 | 3118 | 1.5-2 / 12 assumed |
| Carraway | 1 | 2700-2700 | 3086 | 1.5 / 12 assumed |
| Metrovue | 4 | 2825-2825 | 3082 | 1 / 12 |
| Reserve at Riverdale | 1 | 2753-2753 | 3059 | 1 / 10 |
| Avalon Yonkers | 1 | 2675-2675 | 3057 | 1.5 / 12 |
| The Pointe at Neptune | 2 | 2801-2801 | 3056 | 1 / 12 |
| J Centra Burlington | 2 | 2699-2699 | 3051 | 1.38 / 12 |
| The Liberty Building | 1 | 2477-2477 | 3049 | 2-3 / 12 assumed |
| Admirals Cove | 1 | 2795-2795 | 3049 | 1 / 12 assumed |
| The Hazel Jersey City | 1 | 2776-2776 | 3045 | 1-1.5 / 17 |
| 1177 Greens Farms | 1 | 2735-2735 | 3039 | 1 / 10 |
| The Mitchell | 1 | 2781-2781 | 3034 | 1 / 12 assumed |
| Avalon Teaneck | 2 | 2760-2780 | 3033 | 1 / 12 |
| Summer House | 2 | 2575-2599 | 3032 | 2 / 14 |
| 30 Broad Street | 1 | 2775-2775 | 3027 | 1 / 12 assumed |
| 1 Martine at City Square | 1 | 2775-2775 | 3027 | 1 / 12 assumed |
| The Atwater | 1 | 2785-2785 | 3017 | 1-2 / 12 assumed |
| 80East / Luxury Apartments / Dover, NJ | 2 | 2800-2800 | 3015 | 1 / 14 |
| The Confluence at Norwalk | 1 | 2761-2761 | 3012 | 1 / 12 |
| 111 Harbor Point | 1 | 2752-2752 | 3002 | 1 / 12 assumed |

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
