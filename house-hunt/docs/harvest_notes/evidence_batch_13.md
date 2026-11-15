# Evidence pass, batch 13 (2026-11-15, 22:47–23:10 UTC)

29 buildings in `data/reference/evidence_batches/batch_13.csv`, 41 unit rows. All 29 were worked. None is in New York
City (Connecticut: Oxford 1, Seymour 2, Shelton 5, Stamford 6, Stratford 1, Trumbull 1, Waterbury 1, West Haven 6;
New Jersey: Bayonne 6, Bound Brook 1, Burlington 1), so Openigloo did not apply.

Output: `data/evidence/{live_check,confirm,items,facts,ratings}_batch_13.csv`. Raw pages: `raw/evidence_b13/`.
Scripts: `scripts/ev13_fetch.py` (refetch), `ev13_site.py` (robots check incl. Claude groups, then fetch),
`ev13_trulia_parse.py`, `ev13_al_parse.py`, `ev13_zumper.py`, `ev13_grep.py`, `ev13_text.py`, and `ev13_write.py`, which
rebuilds all five CSVs with no network. The values in `ev13_write.py` were typed in from the cached pages, not parsed
at run time; it reads only the fetch index for retrieval times.

Gates applied as given for this round: dog limit 25 lb or more; a size-only "small dogs" policy passes (wording recorded).

## 1. Live check (41 unit rows: 35 live, 1 changed, 5 blocked, 0 gone)

- **25 named units are live at the stored price and inside the window.** Latest dates: 278 Main G112 on Dec 8, Life Time
  Living 500 and Lofts at 335 #305 on Dec 7.
- **10 rows are live at floor-plan level only** (a plan price marked "Available Now", no unit, no date): The Mark (2),
  Riverhouse (2), Crestview (2), Brookview, 301 Bridgeport Ave, Ten Trumbull, The Regency. Call to confirm.
- **Changed (1):** Thompson Luxury Residences' unnumbered $2,100 row. Nothing is at $2,100; the nearest is unit 112 at $2,095.
- **Blocked (5):** the five single-unit Trulia `/home/` listings (308 Main St 8A in West Haven; 1202 Kennedy 44R,
  1204 Kennedy 32A, 35 W 25th 30G and 971 Broadway 708 in Bayonne). Trulia answered 403 "Access to this page has been
  denied". The harvester had read all five at about 20:00 UTC the same day, when each was "For Rent" at the stored
  price; that earlier reading is quoted in the notes column but the rows stay `blocked`.
- Nothing repriced above $3,000. Nothing falls after Dec 15.
- Own site read and in agreement: The Asher 530 and 536 (SightMap), Liberty Bay Club 457, J Centra 8102 and 11102,
  Lopresti 306 and 105 (manager's Buildium page). Quarry Walk 219 agrees on Trulia and Apartment List.

### Listings that need a human look
- **Riverhouse (Stamford): the listed prices are net-effective.** Page text: "Net effective Prices advertised reflect 3
  months free on 18 month leases! ... Tenants pay higher legal rent & take the credits throughout the lease. Extra Fees:
  Parking $95, Pets $50 and Amenity Fee". My estimate of the rent actually charged is about $2,716 for the $2,263 one-bedroom
  and $2,430 for the $2,025 studio (15 paid months of 18; an estimate, the page gives no gross figure). With $50 pet rent,
  $95 parking and an unstated amenity fee, the one-bedroom is at or over $3,000 all-in on the gross rent.
- **Stale Trulia pages** (last modified date on the page): Liberty Commons 2025-05-05, Brookview 2025-06-09, Ten Trumbull
  2025-08-18, Thompson 2025-12-08, Vista 2025-12-16, The Regency 2025-12-19. Their prices are unverified.
- **Vista:** the offer text on the page quotes $2,100 for a one-bedroom with office at this address; the unit is listed at $2,400.
- **Liberty Commons (Waterbury):** fails on several counts. Trulia says dogs are not allowed (Apartment List says allowed
  up to 25 lb: the sources disagree); the "studio" at $1,500 is a plan named "2 Bedroom" in a property that describes
  itself as two- and three-bedroom; "some income restrictions apply".
- **J Centra 8102 and 11102 are on floor 1** (the building's own unit data). They fail the no-ground-floor gate. The
  complex is 20 buildings of which only 3 have elevators; whether buildings 8 and 11 do is not stated. Both units have
  been listed as available since December 2025 and February 2026.
- **1202 Kennedy Blvd 44R** was advertised as a "4TH FLOOR WALKUP": no elevator. 1204 Kennedy next door is probably the same.
- **Thompson 007:** $1,885 on Trulia, $1,795 on Zumper (Zumper's row modified 2026-11-15). The unit number points to the
  lowest level of the building.
- **Lopresti M105:** Trulia says available now, the manager's own page says 12/1/2026. Probably a ground-floor unit.
- **The Asher:** the SightMap price is for a 21-month lease, and required fees add $100 a month (amenity $75, trash $25).
- **Merion Riverwalk:** prices shown are for a 20-month lease; both units have been vacant since September or October.
- Kestrel's page says "PLEASE CALL FOR CURRENT AVAILABLE UNITS".

### Special offers (verbatim text is in `live_check` notes and `facts`)
Quarry Walk (1 month free on 18 months, to Dec 31), Merion Riverwalk (1 month free if moved in by 12/15), Vista (first
month $1,100), The Asher (1 month free, select units), Riverhouse (3 months free on 18; **net-effective pricing stated**),
Hoyt Bedford (one month free + waived application fee), Life Time Living (1/2 month free), Lofts at 335 (December free
for the next 2 applications moving in by Nov 30), Crestview (deposit offer only), J Centra (up to 6 weeks free), 1202
Kennedy (1 month free on 18 months, to Nov 30). **Only Riverhouse says whether its price is gross or net.** For the
others the page does not say; recorded as "not stated". No offer: Liberty Bay Club, Rail at Bound Brook, 278 Main and the rest.

## 2. Gate facts (127 rows: 61 confirmed, 63 unconfirmed, 3 contradicts)

- **Unit floor: confirmed for 6 unit rows only.** The Asher 530 and 536 (floor 5, SightMap), Liberty Bay Club 457
  (floor 4, own unit data), J Centra 8102 and 11102 (floor 1, own unit data), 1202 Kennedy 44R (4th floor, listing text).
  The other 34 floor rows are `unconfirmed`, each with my reading and the reason. Readings that point to a ground or
  lowest-level unit: **Lopresti M105, 278 Main G112 and G107, Crestview plan "103", Thompson 007.**
- **Dog weight limit in pounds: 5 confirmed.** 163 Franklin 75; The Asher 50; **278 Main 25 (exactly the gate)**; J
  Centra 200 combined for two pets; Liberty Bay Club "no weight restrictions". Liberty Commons 25 on Apartment List but
  Trulia says no dogs (`contradicts`).
- **"Small dogs" only, no number (passes under the current rule):** Lopresti, Vista, Brookview, 301 Bridgeport, Prospect
  Park, Crestview, Thompson, The Regency, and the five blocked single units (as read at 20:00 UTC).
- **"Small, large" or large dogs allowed, no number:** Quarry Walk, Kestrel, The Mark, Riverhouse, Hoyt Bedford, Life Time
  Living, Lofts at 335, Ten Trumbull. Merion Riverwalk and Rail at Bound Brook state no size or weight at all.
- **Elevator:** stated for 23 buildings. Not stated for 308 Main St, 1204 Kennedy, 35 W 25th and 971 Broadway (the four
  that were "only inferred from height") and for J Centra's buildings 8 and 11. **1202 Kennedy is a walk-up** (`contradicts`).
- Dogs allowed: stated for 27; case by case at 1202 Kennedy; contradictory at Liberty Commons.

## 3. Ratings (29 rows: 4 with a rating, 25 `none_found`)

- Google rating as copied by Zumper: **Hoyt Bedford 3.6/5 from 145** (pulled 2024-12-07), Quarry Walk 4.3 from 16
  (2024-12-07), Kestrel 5.0 from 2 (2024-12-08). Apartment List: Merion Riverwalk 4.7 from 3.
- Zumper shows only its highest-rated review texts (all 5-star) and its copy is almost a year old, so **reviews in the
  last 6 months: 0 for every building**, and no negative text could be read. The 3.6 average for Hoyt Bedford implies
  many low ratings that are not visible from allowed sources.
- The other 25 have no readable rating: empty Zumper review blocks, Apartment List pages "collecting reviews" or absent,
  no widget on the own sites. This batch cannot be judged statistically from allowed sources.

## 4. Evidence items (34 rows)

none_found 25, positive 5, management 3, elevator 1. No car_crime, safety_incident or noise item was found.

### Most serious: Hoyt Bedford Apartments, 112 Hoyt St, Stamford
- **News 12, 2023-11-01:** roaches, overflowing trash, a parking garage that sometimes floods, three buildings without
  heat and hot water, "an elevator in one of the buildings that's been out of use for a year", and the city health
  department condemning the building at 98 Hoyt St until the boiler was fixed. Tenants said promised credits had not
  arrived. The manager then was Rushmore Management.
- This is three years old. The current listing says "Now under NEW MANAGEMENT!" but Trulia still names Rushmore and
  Zumper names Oakmark Management; the date of any change was not found. Google 3.6 from 145 (Dec 2024) fits a mixed
  record. The stored unit is in the building numbered 140, not 98.

### Others
- Quarry Walk, Kestrel, Merion Riverwalk: positive review excerpts only (2022–2025).
- Nothing was found about the remaining buildings in one news search each for the larger ones. The small West Haven,
  Shelton and Bayonne buildings got no news search.

## 5. Blocked or not done

- **Trulia put up a bot wall partway through.** The 18 building pages fetched at 22:47 returned 200; the five `/home/`
  pages returned 403. I re-requested one once to read the message ("Access to this page has been denied"), and later
  sent six building-page requests (The Asher, Rail, 278 Main, J Centra, Liberty Bay Club, 308 Main) that also returned
  403 before I stopped. Those six should not have been sent after the first refusals. No further Trulia requests were
  made. Where a Trulia page is cited with an earlier time (The Asher 21:45, 278 Main 21:54, Liberty Bay Club 20:01, the
  five single units about 20:00), it is the harvester's cached copy from the same day.
- Own sites that answered 403: merionriverwalk.com, therailboundbrook.com, loftsat335.com, 163franklin.com (a guess).
  Did not resolve or connect: themarkfairfieldcounty.com, thompsonluxuryresidences.com (guesses), carabetta.com,
  fountainheadpm1.com (certificate error). Wrong property, discarded: hoytbedford.com, lifetimeliving.com.
- westfaironline.com (The Asher's opening): honoured its 600-second crawl delay, then got a challenge page; not read.
  CT Examiner 2022 article on a Stamford "luxury" building: paywalled, building not named in the readable part; not used.
- Search results mentioned Apartments.com ratings (163 Franklin 2.0 from 3, Prospect Park, Merion, The Asher, Liberty
  Bay Club) and a RentCafe comment on Life Time Living. Those sites are off limits or blocked and snippets are not
  evidence; nothing from them is recorded.
- Not used: Better Business Bureau, Patch, Zillow, Apartments.com, RentCafe, HotPads, Yelp.
- Management start dates were not found for any building. Liberty Bay Club was Woodmont Bay Club under Woodmont
  Properties and is now Greystar; Hoyt Bedford claims new management. Neither change is dated.
- No court or code-enforcement record was looked up.
- Deviation from the usual labels, as in batch 11: plan-level rows are `live` with a note, because the page still shows
  the price as available; they are not verified units.
