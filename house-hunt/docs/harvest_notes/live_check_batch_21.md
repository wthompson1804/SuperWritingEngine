# Live check batch 21: the 45 apartments at or under $2,000 listed rent (2026-11-17)

Source list: `site/data.json`, units with `rent.listed <= 2000`: **45 apartments in 25 buildings**, 38 of them collected from Trulia.
Output: `data/evidence/live_check_batch_21.csv` (45 rows, one per apartment, same columns as batch 20). Script:
`scripts/live_check_batch_21.py` (`get` fetches with cache, robots check and 3 s spacing; `write` rebuilds the CSV from the
findings table in the script, no network). Raw pages: `raw/live_check_b21/`; three script-filled pages opened once each with
`scripts/h_mgmt_render.js` are in `raw/live_check_b21/render/`. No Trulia request. The pipeline was not run. Nothing committed.

## Counts

| Status | All 45 | Trulia-sourced 38 |
|---|---|---|
| live (same price) | 12 | 6 |
| changed (price) | 5 | 5 (all lower) |
| gone | 7 | 6 |
| not_read | 21 | 21 |

- **live**: Arcade 302; Brookview West 519; Brookview East 524, 406; Summer St 320, 417; The Stanley 504; 111 Prospect 206, 306;
  64 Park Ave D10; LIA 423; 36-25 Parsons Blvd 5H (matched by broker, street, studio and price, not by apartment number).
- **changed**: Whitney Towers 306 $1,945 to $1,895, 409 $1,865 to $1,715, 607 $1,875 to $1,725 (manager's AppFolio board);
  Soundview 855-1015 $1,950 to $1,900 (Apartment List); 111 Prospect 511 $1,715 to $1,675 (already seen on 2026-11-16).
- **gone**: Beacon Mill Village PA-405, PA-202, PA-402, BM-322, PU-242 (the building's own list has ten other apartments);
  The Royce 4211 (out of the Apartment List unit list; nothing there at or under $2,000 now); 84-18 143rd St 3L (absent from the
  broker's full rental list, by absence only).
- **not_read** (21): City Trust 955 Main St (8), Symphony (3), Harclay House (2), 333 State St 604, Ethos Kelsey 301, Regency on
  Hudson 606, 1483 Shore Pkwy F, 4110 Bowne St 5W, 13324 Sanford Ave 2D, 2781 Ocean Ave 6E, 525 Riverdale Ave 5U.
  Two of these carry a finding that points against the listing: 333 State St (own availability page shows "No results found")
  and Regency on Hudson (own site: studios from $2,195, none marked available).

## Availability by 2026-12-15

Every live or changed apartment is available now or by the date: Brookview East 524 on 11-26, 406 on 12-15; Whitney Towers 409
on 12-01, 306 and 607 on 12-15. Garden Homes and the Hillel listing give no date.

## Hosts

- Refused today, written to `raw/_host_kill_shared.json`, not retried: `www.goldberg-realty.com` (403), `tours.liabyvermella.com` (403).
- `franklin.appfolio.com` and `felnercorptei.appfolio.com`: robots.txt allows only `/listings` (crawl-delay 10); only that page was read.
  The filtered iframe address on the Franklin page is disallowed and was not requested.
- Zumper address pages: seven read, five answered 404 (a normal answer). Apartment List: five building pages read; eight guessed
  addresses returned its generic "not found" shell and were not used.
- Web search was used only to find site addresses; no price or date was taken from a result.

## For whoever applies this

- `not_read` is a new status word in the live-check files. `build_master.py` takes the latest row per apartment, so these rows
  would replace an earlier `live` (read on Trulia 2026-11-15) for 955 Main St 606 and 511, 333 State St 604, Harclay House 3CW and
  5CE, and the New York single listings. Drop the `not_read` rows before the build if the earlier status should stand.
- The 525 Riverdale Ave 5U note matches `parsers.second_site_omits` (as its earlier row did).
- Mandatory monthly fees read today: Brookview $50 amenity fee (both buildings); The Royce $100.
- The Arcade's manager states "Small dogs allowed". 111 Prospect was tagged income-restricted in the live check of 2026-11-16; not re-examined here.
- Beacon Mill Village's own list has apartments not in our data at $1,545 to $1,895.
