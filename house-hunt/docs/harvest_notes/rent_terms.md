# Rent terms (scripts/rent_terms.py -> data/rent_terms.csv)

Rebuilt from data/units.csv, each unit's cached page (`raw_path`) and data/evidence/*.csv. No network requests. Every passing unit was checked and has one row.

- Units checked: **2598** (one row each; `offer_type = none` for units with no such language).
- Units with any concession, special-offer or price-basis language: **1776**.
- Units whose price or offer is for a lease term other than 12 months: **586**.
- Units that need a call (`needs_call = yes`): **1677** in 237 buildings.

## Counts by offer_type

| offer_type | units |
|---|---|
| months_free | 1387 |
| none | 822 |
| other | 234 |
| reduced_deposit_or_fee | 72 |
| weeks_free | 35 |
| dollar_credit | 28 |
| look_and_lease | 20 |

## Listed price basis

| listed_price_is | units |
|---|---|
| unknown | 1417 |
| gross | 945 |
| net_effective | 236 |

## Confidence

| confidence | units |
|---|---|
| assumed_terms | 1647 |
| stated_on_page | 915 |
| computed_from_stated_terms | 36 |

## Free-period timing

| timing | units |
|---|---|
| unknown | 1362 |
| (no free period) | 1176 |
| upfront | 42 |
| end_of_lease | 12 |
| specific_months | 5 |
| spread_monthly | 1 |

## Gross rent above the listed price (stated or computed from stated terms)

**30** units have a determined gross rent above the listed price.

| unit | listed | gross | gap | free months / lease | confidence |
|---|---|---|---|---|---|
| The Riverhouse | 2263 | 2716 | 453 | 3 / 18 | computed_from_stated_terms |
| Alvista Rise #2410 | 2365 | 2800 | 435 | 2.5 / 18 | stated_on_page |
| The Riverhouse | 2025 | 2430 | 405 | 3 / 18 | computed_from_stated_terms |
| Harbor Pointe #B9-309 | 2223 | 2627 | 404 | 2 / 13 | computed_from_stated_terms |
| The Riverhouse | 1975 | 2370 | 395 | 3 / 18 | computed_from_stated_terms |
| Alvista Rise #1922 | 2435 | 2825 | 390 | 2.5 / 18 | stated_on_page |
| Harbor Pointe #B3-244 | 2850 | 3206 | 356 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B9-433 | 2829 | 3183 | 354 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B9-113 | 2824 | 3177 | 353 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B3-449 | 2774 | 3121 | 347 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B3-403 | 2779 | 3126 | 347 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B9-457 | 2650 | 2981 | 331 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B9-449 | 2612 | 2938 | 326 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B3-348 | 2495 | 2807 | 312 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B3-127 | 2352 | 2646 | 294 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B9-258 | 2314 | 2603 | 289 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B9-334 | 2292 | 2578 | 286 | 2 / 18 | computed_from_stated_terms |
| Harbor Pointe #B9-240 | 2195 | 2469 | 274 | 2 / 18 | computed_from_stated_terms |
| Arc House | 2875 | 3115 | 240 | 1 / 13 | computed_from_stated_terms |
| Arc House | 2855 | 3093 | 238 | 1 / 13 | computed_from_stated_terms |
| Arc House | 2830 | 3066 | 236 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2562 | 2776 | 214 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2492 | 2700 | 208 | 1 / 13 | computed_from_stated_terms |
| Arc House | 2500 | 2708 | 208 | 1 / 13 | computed_from_stated_terms |
| Harmony West | 2423 | 2625 | 202 | 1 / 13 | computed_from_stated_terms |

## Largest possible gaps where the basis is unknown (scenario: listed price is net-effective)

1392 units carry a scenario figure. These are **not** stated rents: they show what the monthly rent would be if the advertised price already has the free months spread in. Top 25:

| unit | listed | gross if listed is net | gap | free months / lease | basis |
|---|---|---|---|---|---|
| Axis 201 #0308 | 2856 | 5712 | 2856 | 3 / 6 | unknown |
| Axis 201 #0508 | 2856 | 5712 | 2856 | 3 / 6 | unknown |
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

## Gross rent over $3,000 (rent only, all-in aside)

- Determined gross over $3,000: **8** units: Harbor Pointe #B3-449 ($3121); Harbor Pointe #B9-113 ($3177); Harbor Pointe #B3-403 ($3126); Harbor Pointe #B9-433 ($3183); Harbor Pointe #B3-244 ($3206); Arc House ($3066); Arc House ($3093); Arc House ($3115)
- Scenario gross over $3,000 (upper end, if the listed price is net-effective): **655** units in 99 buildings.

| building | units | listed range | scenario gross (max) | free months / lease |
|---|---|---|---|---|
| Axis 201 | 46 | 1805-2856 | 5712 | 3 / 6 |
| Halstead Parsippany | 23 | 2384-2999 | 3999 | 3 / 12 |
| The Jefferson | 6 | 2740-2990 | 3987 | 3 / 12 assumed |
| Brookside Wilton | 8 | 2650-2650 | 3975 | 2 / 6 |
| The Alary | 9 | 2538-2975 | 3967 | 3 / 12 assumed |
| Twenty Fair | 6 | 2400-2925 | 3900 | 1-3 / 12 assumed |
| The Winston | 26 | 2350-2850 | 3800 | 3 / 12 |
| Piper | 34 | 2499-3000 | 3789 | 2.5 / 12 |
| West Side Square | 72 | 2439-2998 | 3787 | 2.5 / 12 |
| Berkeley House | 1 | 2838-2838 | 3784 | 3 / 12 assumed |
| The Taft Apartments | 3 | 2160-2435 | 3652 | 3 / 9 |
| Twenty50 | 5 | 2850-3000 | 3600 | 1 / 6 |
| EDGE | 16 | 2513-2995 | 3594 | 2 / 12 |
| 1 Lyon Place | 2 | 2830-2995 | 3594 | 1-2 / 12 assumed |
| Clifton & Co. | 18 | 2533-2978 | 3574 | 2 / 12 |
| 500 PARQ | 11 | 2560-2960 | 3552 | 2 / 12 |
| Skyline New Rochelle | 10 | 2640-2955 | 3546 | 2 / 12 assumed |
| Aviva | 96 | 2541-2994 | 3538 | 2 / 13 |
| Julius | 3 | 2880-2940 | 3528 | 2 / 12 |
| Scribe | 17 | 2509-2936 | 3523 | 2 / 12 assumed |
| 51 South | 5 | 2808-2932 | 3518 | 2 / 12 |
| Hudson 44 | 5 | 2595-2900 | 3480 | 2 / 12 assumed |
| Aura 240 | 1 | 2595-2595 | 3460 | 3 / 12 assumed |
| The Current on River | 6 | 2595-2875 | 3450 | 2 / 12 |
| Port & Main | 5 | 2750-2850 | 3420 | 2 / 12 assumed |
| 42 Broad | 2 | 2873-2964 | 3387 | 1.5 / 12 assumed |
| Noble' | 1 | 2900-2900 | 3383 | 1-2 / 12 assumed |
| Summer House | 13 | 2575-2921 | 3370 | 2 / 13 |
| Riello Edgewater | 1 | 2800-2800 | 3360 | 2 / 12 assumed |
| Avalon Somerville Station | 1 | 2940-2940 | 3360 | 1.5 / 12 |
| 75 Tresser | 7 | 2665-2957 | 3343 | 1.38 / 12 |
| Stella | 3 | 2758-2893 | 3338 | 2 / 15 |
| Avalon Yonkers | 3 | 2675-2920 | 3337 | 1.5 / 12 |
| Hedges at Hawthorne | 2 | 2800-2850 | 3325 | 2 / 14 |
| Starling | 1 | 3000-3000 | 3284 | 1.38 / 16 |
| Bedford Hall Apartments | 5 | 2635-2735 | 3282 | 2 / 12 assumed |
| The Walcott Hackensack | 4 | 2610-2831 | 3267 | 2 / 15 |
| The Magnolia | 11 | 2825-2995 | 3267 | 1 / 12 assumed |
| Fairfield The Wel at Lindenhurst | 1 | 2995-2995 | 3267 | 1 / 12 assumed |
| Carraway | 4 | 2700-2858 | 3266 | 1.5 / 12 assumed |
| Hudson Lights | 3 | 2936-2994 | 3266 | 1 / 12 |
| Harbourside SoNo | 4 | 2918-2992 | 3264 | 1 / 12 assumed |
| 360 State Street | 19 | 2454-2646 | 3257 | 3 / 16 |
| The Wyldes | 6 | 2861-2982 | 3253 | 1 / 12 |
| TGM Anchor Point | 6 | 2825-2980 | 3251 | 1 / 12 |
| The Confluence at Norwalk | 3 | 2761-3000 | 3250 | 1 / 12 |
| The Metro | 3 | 2795-2975 | 3245 | 1 / 12 assumed |
| Admirals Cove | 4 | 2795-2975 | 3245 | 1 / 12 assumed |
| Alexander Crossing | 1 | 2838-2838 | 3243 | 1.5 / 12 |
| The Asher | 7 | 2812-2968 | 3238 | 1 / 12 assumed |
| The Hazel | 1 | 2989-2989 | 3238 | 1 / 13 |
| 66 Summer Street | 7 | 2817-2962 | 3231 | 1 / 12 assumed |
| The Smyth | 1 | 2953-2953 | 3221 | 1 / 12 |
| Parkside at the Harbors | 2 | 2850-2950 | 3218 | 1 / 12 assumed |
| Overlook Flats | 1 | 2950-2950 | 3218 | 1 / 12 assumed |
| J Centra Burlington | 3 | 2699-2844 | 3215 | 1.38 / 12 |
| Newport Rentals | 4 | 2912-2942 | 3209 | 0.5-1 / 12 |
| The Enclave | 2 | 2975-2990 | 3204 | 1 / 15 |
| Sawyer | 1 | 2999-2999 | 3199 | 1 / 16 |
| The Audubon New Haven | 6 | 2640-2797 | 3197 | 1.5 / 12 assumed |
| Atlantic Station | 2 | 2881-2931 | 3197 | 1 / 12 |
| The Arbor | 2 | 2818-2928 | 3194 | 1 / 12 |
| Solaris Lofts | 1 | 2948-2948 | 3194 | 1 / 13 |
| Metrovue | 9 | 2825-2925 | 3191 | 1 / 12 |
| Modera New Rochelle | 2 | 2855-2924 | 3190 | 1 / 12 |
| City Crossing | 2 | 2892-2917 | 3182 | 1 / 12 assumed |
| Atlas | 2 | 2573-2651 | 3181 | 2 / 12 |
| 111 Harbor Point | 2 | 2752-2914 | 3179 | 1 / 12 assumed |
| The Hazel Jersey City | 2 | 2776-2898 | 3178 | 1-1.5 / 17 |
| Avalon Wayne | 1 | 2645-2645 | 3174 | 2 / 12 |
| Woodmont Station at Cranford | 1 | 2955-2955 | 3166 | 1 / 15 |
| Willett Point | 1 | 2900-2900 | 3164 | 1-2 / 12 assumed |
| The Reserve at Clarkstown | 1 | 2900-2900 | 3164 | 1 / 12 assumed |
| Glenview House | 1 | 2899-2899 | 3163 | 1 / 12 |
| 25 North Lex | 4 | 2806-2948 | 3159 | 1 / 12 |
| 1 Martine at City Square | 2 | 2775-2895 | 3158 | 1 / 12 assumed |
| Harrison Yards | 4 | 2815-2895 | 3158 | 1 / 12 |
| Fort Hill Peekskill | 4 | 2775-2895 | 3158 | 1 / 12 assumed |
| The Residences at Courthouse Square | 3 | 2650-2700 | 3150 | 2 / 14 |
| Valley and Bloom | 5 | 2803-2905 | 3147 | 1 / 13 |
| Miroza Tower III | 2 | 2850-2950 | 3124 | 1 / 18 |
| Parc at Glenbrook Apartments | 1 | 2598-2598 | 3118 | 1.5-2 / 12 assumed |
| AVE Clifton | 1 | 2872-2872 | 3111 | 1 / 13 |
| The Waypointe Apartments | 3 | 2781-2836 | 3094 | 1 / 12 assumed |
| Harbor Landing Apartments | 1 | 2958-2958 | 3087 | 0.5 / 12 |
| The Duchess | 1 | 2828-2828 | 3085 | 1 / 12 |
| Pier Village | 1 | 2931-2931 | 3085 | 1 / 20 |
| Encore | 1 | 2888-2888 | 3081 | 0.5-1 / 16 |
| Kensington Place | 2 | 2525-2554 | 3065 | 2 / 12 |
| Reserve at Riverdale | 1 | 2753-2753 | 3059 | 1 / 10 |
| The Pointe at Neptune | 2 | 2801-2801 | 3056 | 1 / 12 |
| The Liberty Building | 1 | 2477-2477 | 3049 | 2-3 / 12 assumed |
| Riverside | 1 | 2795-2795 | 3049 | 1 / 12 assumed |
| 1177 Greens Farms | 1 | 2735-2735 | 3039 | 1 / 10 |
| The Mitchell | 1 | 2781-2781 | 3034 | 1 / 12 assumed |
| Avalon Teaneck | 2 | 2760-2780 | 3033 | 1 / 12 |
| The Atwater | 2 | 2785-2800 | 3033 | 1-2 / 12 assumed |
| 30 Broad Street | 1 | 2775-2775 | 3027 | 1 / 12 assumed |
| 80East / Luxury Apartments / Dover, NJ | 2 | 2800-2800 | 3015 | 1 / 14 |

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
