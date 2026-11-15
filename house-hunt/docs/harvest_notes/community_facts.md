# Harvest notes: building-facts pass for management-site communities (`community_facts`)

Run: 2026-11-15, about 19:15 to 19:30 UTC. Script `scripts/community_facts.py`; output
`data/reference/community_facts.csv` (one row per community, nearest first by `drive_min`).

## Coverage

- 11 communities (GDC and some Garden Communities rows) have no ZIP in the harvest CSV, so `drive_min` is blank and they sort last.
- **271 communities**, every one with at least one studio or 1BR row at `listed_rent` ≤ $2,850 in
  `data/listings_raw/mgmt_*.csv`. All 271 had at least one page read. **132 are within a 60-minute drive.**
- By site: Fairfield 115, Garden Communities 66, Greystar 36, AvalonBay 22, Garden Homes 11, GDC 8, BLT 4,
  Russo / Vermella 8, Shoregate (Tritec) 1. Newport has no row at or under $2,850, so no community.
- 513 page reads in total. Most came from the cache the unit harvest had already filled. New fetches: 138 pages
  on 46 hosts (the Greystar communities' own websites, plus amenities / FAQ pages), cached in `raw/community_facts/`.
- Coordinator's limit applied: beyond the page already cached, at most two more pages per community
  (the community's own home page and one or two of amenities / FAQ / features / pet pages, pet and FAQ first).

## Pages read, by site

| Site | Pages |
|---|---|
| Fairfield | the community page, plus the first qualifying floor-plan page (`listing-detail/?lid=N`), which repeats the policy block. Some community pages carry no text at all. |
| Garden Communities | the community page only (overview, amenities, "Utilities Included"). The site has no pet or fee page per community. |
| Greystar | the greystar.com property page (structured data: building type, amenities, fee table), the community's own website home page, and up to two of its amenities / FAQ / features pages. |
| AvalonBay | the community page and one unit page (structured data: pet policy, restricted breeds, fee table, utilities, parking policy). |
| Garden Homes | `Property?pid=N` (a short amenity list). |
| GDC | the one page per community. |
| BLT | the community page (embedded resident reviews are cut out before reading). |
| Russo / Vermella, Shoregate | home page plus `/amenities`. |

## Fill rates (share of communities with a value other than blank / `unknown` / `none stated`)

| Fact | All 271 | Within 60 min (132) |
|---|---|---|
| elevator | 8% (23 yes, 0 no) | 13% (17) |
| building type words | 35% (94) | 30% (40) |
| total floors stated | 1% | |
| dogs | 44% (112 yes, 6 no, 153 unknown) | 50% (66) |
| dog weight limit (a number, or "no limit" stated) | 18% (39 numbers, 10 "no limit") | 21% (28) |
| pet rent per month | 42% (113) | 50% (66) |
| one-time pet fee or deposit | 39% | |
| breed restrictions | 20% | |
| max pets | 13% | |
| parking type | 70% (189) | 70% (93) |
| parking fee per month | 21% (56) | 25% (33) |
| required monthly fees | 21% (57) | 26% (34) |
| utilities included | 37% (101) | 39% (52) |
| pool / gym / package room / controlled access / coworking | 39% / 46% / 18% / 27% / 19% | |
| dog park or pet spa | 21% | |
| manager | 100% (the site operator) | |
| year built | 0% (no page states it) | |

By site (communities with a value):

| Site | n | elevator | dogs | weight limit | parking fee | required fees | building type |
|---|---|---|---|---|---|---|---|
| Fairfield | 115 | 4 | 53 | 35 | 1 | 0 | 9 |
| Garden Communities | 66 | 5 | 9 | 1 | 0 | 0 | 33 |
| Greystar | 36 | 8 | 21 | 6 | 32 | 35 | 36 |
| AvalonBay | 22 | 2 | 22 | 0 | 22 | 22 | 8 |
| Garden Homes | 11 | 4 | 4 | 0 | 0 | 0 | 2 |
| GDC | 8 | 0 | 1 | 0 | 0 | 0 | 5 |
| BLT | 4 | 0 | 2 | 0 | 1 | 0 | 0 |
| Russo / Vermella | 8 | 0 | 6 | 7 | 0 | 0 | 1 |
| Shoregate | 1 | 0 | 0 | 0 | 0 | 0 | 0 |

## What the gate script should know

- **Elevator stays the weak field: 23 of 271.** These sites rarely print the word. Nothing was inferred from
  building type. `building_type` (Greystar: 13 high-rise, 21 mid-rise) and `highest_floor_mentioned` (for example
  "17th floor sky deck", "26th floor rooftop pool") are there for the plan's "6+ floors" rule; `highest_floor_mentioned`
  is a floor named on the page, not the building's total. Four Greystar "yes" values come from an FAQ sentence
  about "reserving elevator access" for move-in; one Avalon value reads "Elevator access (for select apartments)".
- **Dog weight limits: 21 communities state a limit under 40 lb** (20 to 35 lb, all Fairfield); 18 state 40 lb or
  more (Fairfield 40 to 70, Greystar 65 to 75, Garden Communities' Linwood Village "under 40 lbs": read that
  one by hand); 10 say no weight limit (Vermella sites "two pets per home of any size", three Greystar sites
  "No Breed or Weight Restrictions"). So 28 communities state a limit of 40 lb or more, or no limit; in a few of them dogs are still `unknown` or rest on a dog amenity only.
  AvalonBay's data has `maximumPetWeight: 0` everywhere: written as `none stated`, not as "no limit".
- `dog_weight_limit_lb = none stated` means a pet policy was found and gives no number. Blank means no pet text at all.
- **`dogs_basis`** separates a policy sentence that names dogs (86) from a dog amenity only, such as a dog run
  or dog park with no policy sentence (26). "Pet-friendly" alone leaves dogs `unknown`; the wording is in
  `pet_policy_text`. Six communities state no dogs or no pets (five Garden Communities, Fairfield At Garfield Estates).
- Many Fairfield pet lines end "Restrictions apply" without saying which; `breed_restrictions` is then blank.
- **Fees.** Greystar and AvalonBay values come from the page's fee table and are marked `[page data]` in the
  snippet: the snippet quotes the field (label, amount, frequency, required flag), not a sentence. Greystar
  `required_monthly_fees` lists every fee flagged required, including utilities with no amount, and the site's own
  total of the priced ones. Fairfield, Garden Communities, Garden Homes, GDC and the Vermella sites publish no
  required-fee or parking-fee amounts.
- `parking_included = no (fee stated)` is set only where a parking fee is printed.
- Greystar pet rent sometimes shows two amounts (for example "75; 25"): the table has two pet lines and does not
  always say which is the dog.
- `manager` is the operator of the site the page is on. `manager_snippet` quotes the name where the page body has it.

## Blocks and gaps

- **No bot wall, 403 or 429 was met.** robots.txt was read for every host; none had a rule against these pages.
- `rt500residences.com` (Greystar's RT 500): connection failed three times. That row uses the greystar.com page only.
- `fiathouse.com` has no robots.txt (404); pages read normally.
- Not read, by the page limit: third and later sub-pages on community websites, PDFs, and third-party pet
  screening links (petscreening.com, ourpetpolicy.com), where some Greystar communities keep their full pet rules.
- RentCafe / securecafe.com pages (Fairfield and Garden Communities unit lists) were not touched; they are bot-walled.

## Method and limits

- Text is split into lines (list items, sentences). Navigation, headers, footers, other communities' blurbs
  ("Nearby Properties") and embedded reviews are removed before matching, so facts do not leak between communities.
- Each fact is a pattern match on one line (or a heading plus the next line); the snippet is that line.
  Patterns can misread. The most likely slips: `building_type = townhome` from a community that has both
  apartments and townhomes; `controlled_access`, `coworking` and `package_room` from loose wording; a dog park
  that is in the neighbourhood rather than on site. Check the snippet before relying on a single value.
- The script recomputes every row from the cache on each run and rewrites the CSV, so re-running never
  duplicates rows. Failed fetches are remembered in `raw/community_facts/_fetch_state.json` (`--retry` tries
  them again, `--refresh` refetches, `--stop-at <UTC time>` stops starting new communities).
