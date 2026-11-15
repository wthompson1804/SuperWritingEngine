# Evidence pass, batch 5 (2026-11-15)

35 batch rows, 42 units: 27 New York City rows (Jamaica, Briarwood, Kew Gardens, Kew Gardens Hills, Long Island City,
Brooklyn, West Harlem, Middle Village, Flushing) and 8 New Rochelle buildings. All 35 done.

Scripts (all idempotent, cache in `raw/evidence_b5/`): `scripts/evidence_b5_fetch.py` (listing re-fetch, refresh),
`evidence_b5_parse.py`, `evidence_b5_live.py`, `evidence_b5_igloo.py` (Openigloo), `evidence_b5_get.py`
(robots-checked page reader), `evidence_b5_write.py` (confirm / items / facts; every review excerpt and hand-read
quote is checked to be a verbatim substring of the cached page, or the script stops).

Outputs: `data/evidence/live_check_batch_5.csv` (42 rows), `confirm_batch_5.csv` (156), `items_batch_5.csv` (70),
`facts_batch_5.csv` (188).

## 1. Live check

All 35 listing URLs re-fetched 20:39–20:41 UTC, all HTTP 200, no bot wall. **42 of 42 units still listed at the
stored price; 0 gone, 0 changed.** All available now or inside the Dec 15 window (latest: Two Clinton Park 811 on
Dec 14, One Clinton Park 2003 on Dec 8).

Things the live check turned up:

- **56-27 2nd St #1710 (Gotham Point, LIC, $1,389) is not an open-market unit.** The listing says it is income
  restricted (maximum $59,400 for one person, $67,850 for two) and "AT LEAST ONE MEMBER OF THE HOUSEHOLD MUST HAVE A
  MOBILITY IMPAIRMENT", with a waitlist. Should be dropped unless Lamia qualifies.
- **83-33 118th St #6M (Kew Gardens, $2,400) does not take pet dogs.** Listing text: "Dog is allowed only for service
  or emotional service dog." Fails the dog gate.
- **The Opal, 75-25 153rd St #315: contradictory dog policy.** The unit listing says small dogs allowed, two dog
  runs, no pet fees; Trulia's building page for The Opal says "Dogs Not allowed". This is the plan's "listing
  trouble" case.
- **Duplicate rows:** `138-28 queens blvd 5k…` (Zumper) is unit 6K at Le Tour, the same unit as `13828 queens blvd`
  (Trulia). `135-23 82nd ave 3e…` and `13523 82nd ave` are two units (3E, 3F) in one building.
- **147-14 84th Rd #2B ($1,532, 700 sq ft 1BR)** is described as a co-op unit with indoor parking on a wait list. The
  price is far under market; treat as doubtful until confirmed by phone.
- **Illustrator (600 North Ave) unit "600-605"** shows available since 2026-01-10 and the property record was last
  edited 2026-09-21: probably a stale or placeholder listing. The Leaf 2615 shows available since 2025-07-30.
- One Archer #2215: the listing text says "6th Floor with Open Views", which does not fit the unit number.
- 87-46 Chelsea St #7A: HPD registration lists the building as 6 stories, so the floor is unclear.
- 82-67 Austin St #916: listing states an income requirement of $130,000 a year.
- Oldest listings: 86-25 Van Wyck (listed Oct 7), 135-23 82nd Ave 3F (Oct 13), Gotham Point (Oct 15),
  89-61 162nd (Oct 18). None is past 60 days by Trulia's listed date. The Zumper record for 135-23 82nd Ave #3E was
  first created in Feb 2024 and re-listed.

## 2. Gate facts

- Elevator: confirmed for 29 of 35 rows (listing feature, listing text, building site or Apartment List amenity).
  Unconfirmed: 86-25 Van Wyck Expy (listing has no elevator mention; 6 stories), 83-33 118th St, 147-14 84th Rd,
  Motif, One Clinton Park, 25 Maple (the last three are towers with units on floors 6 to 23, so an elevator is
  implied but no page I read says it).
- Floor: read from unit numbers for 39 units; none is ground floor. Unknown for 3333 Broadway (floor plan only).
- **Dog weight limit: confirmed for only 2 buildings, both 75 lb (Shearwood Station, Motif).** Every Trulia listing
  in the batch says only "Cats, small dogs allowed" with no pounds. Nothing better was found for most:
  - The Monarch's own FAQ: "Specific breed restrictions or weight limits are determined by the leasing team."
  - Le Tour: "Pet-friendly case by case."
  - The Leaf's own FAQ: "Breed restrictions, weight limits, and pet fees apply" (number only in a Canva fee guide).
  - Stella and 25 Maple list restricted breeds and $75 dog rent but no weight limit.
  - Jamaica Central: a web search result pointed to a QNS article reporting a 25 lb limit. **Not verified**: qns.com
    disallows Claude agents, so the page was not read. Recorded in facts as a lead only.
  - Court Plaza (123-33 83rd Ave, Stellar): Stellar's site disallows ClaudeBot; not read.
  These need a phone call. Note the gate is now 25 lb (CLAUDE.md), which "small dogs" may or may not meet.

## 3. Tenant and public evidence

Openigloo building pages were reached for 22 of 24 NYC lots (URL pattern `/building/nyc/<BIN>-<BBL>/<slug>`; BINs
looked up from the HPD buildings dataset by block and lot; the site 308-redirects between slug spellings, followed
by hand). Only the five newest reviews per building are in the page's JSON-LD. Not reached: One Archer (redirect
loop), 123-33 83rd Ave (our BBL points at a different lot). No BBL: 143-25 84th Ave, 56-27 2nd St.

48 dated items: management 19, positive 14, other 8, safety_incident 3, elevator 2, noise 2. car_crime 0.
22 rows are `none_found`.

Most serious:

- **3333 Broadway (West Harlem): 2.8 from 60 Openigloo reviews.** Five reviews from Jan to Apr 2025 report pests
  ("PESTS EVERYWHERE - Rats, Roaches, Ants, MOLD"), unresponsive management, elevators that "sometimes don't work
  properly", and security that lets anyone in. All are older than 6 months, so under the plan they are "gives us
  pause", not an avoid, unless the public-records agent adds current data.
- **135-23 82nd Ave (Briarwood):** a Sept 2024 review says the building "has been burglarized a couple of times" with
  lobby packages stolen, and two reviews say the garage has no free spaces.
- **The Opal:** one 2023 review says "elevators often not working" (single, old report).
- **142-02 84th Dr:** one 2021 review of roof leaks into a top-floor unit; our unit 6M is on the top (6th) floor.
  Openigloo's summary line calls it a "poorly reviewed and troubled building".
- **83-33 118th St:** 1.9 from 3 reviews (smoking, trash, pests), 2022 to 2024.
- 164-20 Highland Ave: a 2022 review says the entrance is not step-free ("stairs on both sides").

No car-crime report naming any of the 35 buildings or their garages was found.

## 4. What was blocked or not possible

- **patch.com and qns.com: robots.txt disallows Claude agents** (anthropic-ai / ClaudeBot). Not read. This removes
  the two main local-news sources for Queens and New Rochelle; amNY is the same publisher as QNS and was not tried.
- stellarmanagement.com: disallows ClaudeBot. shearwoodstation.com: HTTP 403. rentcafe: known Cloudflare wall, not
  tried. parksidequeens.com and livejamaicacentral.com/faq: load, but the text is rendered by JavaScript.
- Fee guides for The Leaf, Motif, Stella and 25 Maple are Canva embeds (JavaScript only); the two Clinton Park
  guides are on communityfees.bozzuto.com (not tried: Bozzuto's API paths are disallowed).
- BBB pages for management companies were not checked (time). Web searches for news on each named building, on
  New Rochelle garage break-ins and on The Opal / A&E returned nothing that named a batch building.
- Checked and **not** supported: I looked for a link between Green Brick Realty (broker on four listings) and Zara
  Realty (sued by the NY Attorney General in 2019 and Aug 2025). Openigloo's registered contacts for those
  buildings show other owners (co-ops and Principal Management), so no such claim is recorded.
- HPD / DOB / 311 records were left to the public-records agent. The only HPD data used is the building-number and
  story count lookup.
