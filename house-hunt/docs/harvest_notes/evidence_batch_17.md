# Evidence pass, batch 17 (2026-11-15, 22:47–23:00 UTC)

26 buildings in `data/reference/evidence_batches/batch_17.csv`, 30 listed units. All 26 were worked. 16 are in New York
City (Brooklyn 3, Bronx 3, Queens 3, Staten Island 2, Manhattan 5); 10 are outside (Newburgh, Mount Kisco, Mount Vernon,
Patchogue 2, Tarrytown, White Plains, Yonkers 3).

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_17.csv`. Raw pages: `raw/evidence_b17/`.
Scripts: `scripts/ev17_fetch.py` (refetch), `ev17_site.py` / `ev17_text.py` / `ev17_get.py` (robots check incl. Claude
groups, then fetch), `ev17_trulia_parse.py`, `ev17_al_parse.py`, `ev17_igloo.py`, `ev17_zumper.py`, and `ev17_write.py`,
which rebuilds all five CSVs from cached pages with no network and checks every excerpt against its source page. The
parse scripts and the writer read logs in the session scratch folder; if that is gone, refetch first.

## 1. Live check (30 unit rows: 23 live, 7 blocked, 0 gone, 0 repriced)

**Trulia put up a bot wall (HTTP 403) after the 19th request.** One retry five minutes later was also 403, so I stopped.
Seven buildings (9 unit rows) could not be refetched from Trulia: 1224 Saint Nicholas Ave, 545 Edgecombe Ave, The Metro,
20 Terrace Pl, 66 Main, Hudson Blue, Point and Ravine. For those, gate facts come from the same day's harvest cache
(read 19:32–19:54 UTC) and are labelled that way in `source_url`.
- The Metro was checked on its own site instead (gdcrentals.com): plan A1 $2,595 and plan B3 $2,695, both "Available
  (Now)", matching stored units 816 and 802. The own site lists plans, not unit numbers. Marked live at plan level.
- The other six are `blocked`. Their last good read was three hours earlier at the stored prices.
- All 21 rows refetched from Trulia or Apartment List match the stored price and are inside the window.

### Listings that need a human look
- **Fleetwood Holdings, 80 W Grand St (Mount Vernon), D5:** still shown at $1,942 "Available Now", but the page
  description is "No Units currently available" and the page was last modified 2024-07-24. Probably dead.
- **The Gardens at Mt Kisco, 8A:** shown at $2,495, but the description opens "WAITLIST ... please call for other
  locations"; co-op approval and interview; page last modified 2026-08-11.
- **66 Main (Yonkers), unit 918:** a OneKey MLS record for this unit at $2,700 reads "Rented/Leased 10/26/2026". Trulia
  still showed it available at 19:53 UTC. Possibly gone.
- **Point and Ravine (Yonkers):** income-restricted (LIHTC) housing; 0 available units; page last modified 2025-08-27.
- **Reserve at Lakeside (Newburgh):** age-restricted 55+ community. Its "1 month off" offer required move-in by
  11/15/26. Unit 1101 reads as a ground-floor unit.
- **Hudson Blue (Yonkers):** plan-level only ($1,800, plan L), 0 available units listed; plan L exists on floors 1–7.
- **241 W 101st St 2S:** the description is generic and never names the building; city lot data lists NYC Housing
  Authority as the owner of that address. Check the listing is where it says.
- **Heatherwood House at Patchogue 10G:** the pet policy text says "no dogs on 2nd floor apts" and no page lists an
  elevator. A dog owner would be put on the ground floor of what looks like a garden complex: likely fails the building gate.
- **157 White Plains Rd 44A (Sleepy Hollow Gardens, Tarrytown):** garden complex, no elevator listed anywhere.
- **101-19 Rockaway Beach Blvd 3G:** field says available now, description says "Available 12/1". Price cut $55 on Nov 11.
- **4499 Henry Hudson Pkwy W E6:** price raised $100 on Nov 9 (stored price is the new one). 31 days on market.
- 260 Beach 81st St ("Pets upon approval") and 7914 Rockaway Beach Blvd ("Pets Considered Only on a Case by case
  basis") are condo units where the dog is at the owner's or board's discretion.

## 2. Gate facts (107 rows: 50 confirmed, 57 unconfirmed)

- **Dog weight limit in pounds: one building.** Heatherwood House at Patchogue, 30 lb (passes 25). Its page gives two
  versions of the rest of the policy (1 pet and $75 a month, or 2 pets and $50).
- **Size-only "Small" with no number: 21 buildings** (passes under the current rule; wording recorded). Patchogue
  Village at Terry and The Metro say small and large dogs, no number. Reserve at Lakeside: dogs allowed, breed
  restrictions, no number. 66 Main: the MLS record says "Dogs OK Size Limit".
- Dogs allowed: stated for all 26.
- Elevator stated on a page for 20. Not stated for The Gardens at Mt Kisco, Heatherwood House, 157 White Plains Rd (all
  three look like garden complexes), 80 Richmond Hill Rd, 260 Beach 81st St and 241 W 101st St (city data classes the
  last three as elevator buildings; that is the records agent's field, not repeated here).
- **Floor confirmed for 2 units only:** 2781 Ocean Ave 6E ("on the top 6th floor") and 949 West End Ave D ("top-floor
  studio", number not given). Every other floor is `unconfirmed` with my reading and the reason. Oddities: 1825 Ocean
  Ave 9G reads as floor 9 in a building city data lists at 8 floors; 260 Beach 81st St "4", Fleetwood D5, 4499 HHP E6,
  Gardens 8A, Heatherwood 10G and 157 White Plains Rd 44A cannot be read as floors with any confidence.

## 3. Special offers (verbatim in `facts`, fact = `special_offer`)

No page labels its listed price as gross or net-effective. Reserve at Lakeside (1 month off, expired today; page data
shows base price = total price), The Metro ("One Month Free On Select Residences!"), 66 Main ("Up to 2 Months Fee rent
plus free parking, leasing terms apply."), Heatherwood ($500 security deposit, not a rent concession), Hudson Blue (no
amenity or parking fees). All single-unit Trulia listings say "Price shown is base rent."

## 4. Ratings (27 rows; 9 buildings with a rating, 17 `none_found`)

- Openigloo (NYC): 1224 Saint Nicholas Ave **2.27/5 from 6**; 5550 Netherland Ave lot (other entrances) about 2.6 from
  5; 1825 Ocean Ave 3.13 from 2; 80 Richmond Hill Rd 3.84 from 3; 500 Kappock St 4.25 from 2; 545 Edgecombe Ave 4.5
  from 1; 949 West End Ave 4.81 from 2. **No Openigloo review is from the last 6 months** (newest 2025-09-29), so the
  6-month columns are all 0. Nine NYC buildings have no Openigloo page.
- Outside NYC: Reserve at Lakeside 4.5/5 from 90 on its resident-review page (25 read, 8 in the last 6 months, 1
  negative). Heatherwood House 4.5 from 301 on Birdeye, but only 9 reviews are visible, all 5-star from 2024.
- Nothing readable for the other 8 non-NYC buildings. Zumper has no review block for any of them; Trulia carries none.

## 5. Evidence items (55 rows)

management 20, none_found 16, positive 9, other 7, safety_incident 1, noise 1, elevator 1 (a description, not an outage).
No car_crime item.

### Most serious
- **157 White Plains Rd, Sleepy Hollow Gardens, Tarrytown (ranked 1 in its neighborhood).** News 12, 2026-04-21:
  residents describe "unlivable conditions, including rats, cockroaches, mice, leaks, burst pipes"; mold; Samson
  Management had not replied. Seven months old, so just outside the 6-month window, and one news report rather than
  three tenants in the avoid rule's terms. Also probably no elevator.
- **1224 Saint Nicholas Ave (ranked 1).** Five Openigloo reviews from 2021 to 2025-07 report roaches, no heat in
  winter, bed bugs and unreachable management. Consistent over four years; the newest is 16 months old.
- **5550 Netherland Ave (Riverdale Gardens, ranked 1).** Reviews of other entrances on the same lot: roaches, water
  damage and unresponsive management (2025-09), a 1-star review of the manager (2025-09), sewage in the garage (2021).
- 1825 Ocean Ave: package theft, management ignoring emails, new amenity fees (2024-04).
- Reserve at Lakeside: pool heater broken and opening delayed (2026-06/07), one 2-star review on garbage and
  communication (2026-07), new management in 2026.

## 6. Blocked or not done

- Trulia: 403 from the 20th request (see section 1).
- Own sites: `reserveatlakeside.com` and `66main.com` return 403 (bot wall). The Eagle Rock property page for Patchogue
  Village could not be reached (connection error); its company pet-policy page was read. No own site found for the
  Gardens at Mt Kisco, Fleetwood Holdings or Point and Ravine.
- Search results pointed to reviews I could not read and did not record: ApartmentRatings and RentCafe for The Metro
  (elevator outages, packages), Apple Maps for 66 Main (elevator, heat, garage door, new management), ApartmentRatings
  for Heatherwood (smashed car window, police in the lot), a Better Business Bureau noise complaint for Point and
  Ravine. These are leads only.
- News search: one web search each for 15 buildings (all 10 outside NYC, plus 1825 Ocean, 80 Richmond Hill, 5550
  Netherland, 1224 Saint Nicholas, 5 Stuyvesant). The other 11 NYC addresses had no news search; each `none_found` row
  says which. Patch, QNS and lohud were not fetched.
- NYC public records were not pulled (separate agent). Openigloo's own violation and eviction counts are stored in
  `facts` as `openigloo_summary_counts`, labelled as Openigloo's numbers.
- Management start dates: none found, except reviewers at Reserve at Lakeside mentioning new management in 2026.
- Label deviations: The Metro rows are `live` on a plan-level own-site match; Fleetwood and Gardens rows are `live`
  because the page still lists the unit, with the contradiction in the note.
