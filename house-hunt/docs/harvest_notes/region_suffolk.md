# Region pass: Suffolk County, NY (building-first)

Run 2026-11-15 (UTC), resumed from a stopped earlier agent (its cached pages in `raw/region_suffolk/` and the
partly-run Trulia stage were reused). Gates applied: studio/1BR, listed rent <= $3,000, available now to 2026-12-15,
elevator building, dogs named with any weight limit >= 25 lb.

## Outputs

- `data/listings_raw/region_suffolk.csv`: 193 rows (HARVEST columns). 8 rows are in-window units in 5 buildings that
  pass on the pages read; the rest are `UNCONFIRMED:` (candidate units whose building lacks one stated fact),
  `BUILDING_FAILS:`, `NO_AVAILABILITY:` or `BLOCKED:` rows (one per building unless the building is a real candidate).
- `data/reference/region_buildings_suffolk.csv`: 179 buildings / communities examined: 51 hand-read, 128 automatic
  records from Trulia building pages. Verdicts: 5 pass_with_units, 1 pass_no_availability, 120 unconfirmed, 48 fails
  (25 no dogs, 12 age-restricted, 10 nothing <= $3,000, 1 no elevator), 5 blocked.
- Scripts: `scripts/h_region_suffolk.py` (`trulia`, `build`), `h_region_suffolk_build.py`, `h_region_suffolk_facts.py`
  (hand-read facts with the page each came from) and the reading helpers `h_region_suffolk_{greystar,al,alcity,zumper,zcity,probe}.py`.
  Rebuild: `python3 scripts/h_region_suffolk.py build` (idempotent, cache only).

## Buildings that pass on the pages read (units in window)

| Building | Town | Units <= $3,000 in window | What is still open |
|---|---|---|---|
| Patchogue Village at Terry (Eagle Rock) | Patchogue | T526 $2,265, T220 $2,540, T121 $2,540 (all now) | 5-storey, elevator stated. No weight figure (breed list only). T121 looks like a ground-floor unit. Dog rent $50. |
| Shoregate (TRITEC / Greystar) | Bay Shore | studio 3057 $2,688 (Nov 28), 1BR 3130 $2,719 (Nov 21), both floor 3 | Base rent; + $115 required monthly fees, pet rent $75, parking $50-65 (garage $200). All-in will be near or over $3,000. No weight figure published. |
| Fairfield The Wel at Lindenhurst | Lindenhurst | 1BR plan A1 $2,995 (now) | Floor-plan row (unit, floor unknown). Special quoted verbatim in the row. Pet rent, parking fee, weight limit not published. |
| The Lofts at Maple & Main | Smithtown | 1BR plan $2,995 (now) | Floor-plan row. "Elevators in every building", free parking for 2 cars, pet rent $45. |
| Village By The Bay | Amityville | 1BR plan $3,000 (now) | Exactly at the cap; any fee or pet rent takes all-in over $3,000. No fees published. |

Pass on policy, nothing available: The Shipyard at Port Jefferson Harbor (elevator, no weight restriction, garage $100;
no studio/1BR listed today, recent 1BRs above $3,000).

Best unconfirmed candidates (one stated fact missing):
- **Alston at Station Yards, Ronkonkoma**: nine 1BRs $2,838-$2,988 base (Greystar page, floors 1-3), dogs allowed with a
  breed list, pet rent $50, required fees $107/mo. No page states an elevator (4-storey buildings). Cheapest all-in
  before utilities and parking: $2,995.
- **Gateway Plaza, Huntington Station**: elevator, 1BR #304 $2,975 (now), #227 $2,990 (Dec 7); one parking spot included.
  Trulia says "small dogs" with no weight number.
- **Cornerstone Kings Park**: 1BR #310 $2,466 (floor 3), one month free on base rent; elevator not stated; this one unit
  is far below the other 21 ($3,130+), so confirm it is a market unit.
- **1 East Main, Bay Shore**: elevator, "No additional fees", free parking, 1BR from $2,450, studio from $2,050; no pet
  policy or availability on the site (call 631-339-1492). Close to the Fire Island ferries.
- **Wyandanch Village**: elevator, small dog up to 45 lb; $1,443-$1,465 rents look income-restricted; site returned 403.
- **North District Lofts / Eleven Maple / Greymore Flats / Village Place (Greenview, Bay Shore)**: studios and 1BRs
  $2,150-$2,700 on Zumper; neither elevator nor dog policy stated anywhere.
- **Fieldstone at Commack**: 1BRs $2,710-$2,780, dog allowed; elevator not stated.
- **116 Waverly Ave, Patchogue** ($2,895) and **840 Montauk Hwy, Copiague** ($2,410): elevator stated, dog policy not.

## Towns covered and how

Enumeration: Apartment List town pages for 59 Suffolk towns (249 property slugs), Zumper town pages for 28 towns
(84 building links), the Greystar sitemap (11 Suffolk communities), the Trulia building page of all 143 Suffolk
communities found by the Trulia ZIP search, web search per town cluster, and the leads file.

- Amityville / North Amityville: Village By The Bay (pass), Avalon Amityville (elevator, nothing <= $3,000),
  Greybarn (blocked), Fairfield and Zen/Bunt 55+ communities (auto records).
- Copiague, Lindenhurst, Babylon, West/North Babylon, Deer Park: The Wel (pass); 840 Montauk Hwy; otherwise
  Fairfield garden communities and 55+ complexes. No elevator rental building found in Babylon village or West Babylon.
- Wyandanch: Wyandanch Village (unconfirmed, site 403).
- Huntington / Huntington Station / Melville: Gateway Plaza; Avalon Huntington Station and Avalon Melville (over cap).
  Huntington village has only small elevator buildings (415 and 356 New York Ave, 17 Green St, 2 Elm St) marketed as
  single MLS listings; the Apartment List pages read for village addresses state neither elevator nor dogs.
- Bay Shore / Islip / East Islip / Brightwaters: Shoregate (pass), 1 East Main, seven Greenview buildings, Mid Island.
- Central Islip / Brentwood: Belmont at Eastview and Ballpark Terrace (elevator, no pets), Villas on Eastview (over cap).
  Nothing found in Brentwood.
- Sayville / West Sayville / Oakdale / Bohemia / Holbrook / Bayport: Fairfield, Greenview and Heatherwood garden
  communities only (auto records). Greybarn Sayville: no leasing page found.
- Patchogue / East Patchogue: Patchogue Village at Terry (pass), at Maple and at Rider, New Village (1BR from $3,045 +
  fees: fails price; no weight limit), Revella on Main (no units published yet), 116 Waverly Ave.
- Ronkonkoma: Alston (unconfirmed elevator), The Core (nothing <= $3,000 in the window).
- Hauppauge / Smithtown / Nesconset / Kings Park / Commack: Lofts at Maple & Main (pass), Cornerstone Kings Park,
  Fieldstone at Commack, Carlow Wind Watch and Avalon Commons (over cap), Cornerstone at Hauppauge (active adult).
- Port Jefferson (harbor): Shipyard (pass, nothing available), The Brookport and The Hills (elevator; cats only),
  The Barnum House (elevator; no pet policy or prices published), Overbay and One North (blocked: only on
  Apartments.com / Zillow / MLS). Port Jefferson Station: Vistas (active adult), Fairfield/Heatherwood gardens.
- Coram / Yaphank / Farmingville / Middle Island / Selden: Brio at the Boulevard (over cap), Reserve at the Boulevard,
  Point at Pine Ridge, Fairfield communities.
- Riverhead: The Shipyard, 331 E Main (elevator; 1BRs $3,300 and $4,200), Fairfield Town Centre; the workforce /
  mixed-income Main Street buildings (Riverview Lofts, Summerwind, Peconic Crossing, Woolworth) have no readable
  price page.

## What blocked

- Apartments.com, RentCafe, ForRent, HotPads (bot walls / not permitted): the only copies of Greybarn Amityville,
  Overbay, One North, the Riverhead workforce buildings and most Huntington village listings.
- wyandanchvillage.com and stationyardsli.com: HTTP 403 on the first request; not retried.
- TRITEC sites (alstonli.com, thecoreli.com, shoregateli.com) publish no pet policy or elevator statement; their unit
  data sits behind securecafe / SightMap. Greystar pages give units, fees and pet rent but no weight limit or elevator.
- Greenview Properties pages have no prices, pet policy or availability (they point to Apartments.com).
- Zumper pages rarely carry an availability date; Zumper rows therefore have a blank `available_date`.

## Gaps and cautions

- "Elevator not stated" is the commonest gap: 120 unconfirmed records, most of them garden-style two-storey
  communities (Fairfield, Heatherwood, Eagle Rock) where the Trulia page says nothing either way. They are recorded as
  unconfirmed, not failed, because no page states "no elevator".
- No page read gives a dog weight number for any passing building; "large dogs allowed" (Trulia) or a breed list is the
  evidence. Fairfield's own pages state 30-40 lb limits at other communities, so The Wel's limit should be asked.
- Trulia prices for Alston and Shoregate are "total monthly" (base + mandatory fees); the rows written use the
  manager-site base rent and carry the fees separately.
- Floor-plan rows (The Wel, Lofts at Maple & Main, Village By The Bay) have no unit number or floor.
- Indoor pool: no Suffolk building page read describes an indoor pool. Doorman: none; concierge at Alston, The Core,
  New Village; "virtual doorman" at The Shipyard Riverhead.
- Not covered: single-unit MLS rentals in elevator condo buildings; Avalon's own site (earlier harvest returned no
  Suffolk rows; Apartment List copies used); anything east of Riverhead.
