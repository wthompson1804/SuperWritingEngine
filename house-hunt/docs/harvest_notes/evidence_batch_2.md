# Evidence pass, batch 2 (2026-11-15, about 20:35–21:00 UTC)

35 batch rows = 34 buildings (Avalon Old Bridge has two rows), 52 stored units. All 35 rows were worked.

Outputs: `data/evidence/live_check_batch_2.csv` (52 rows), `confirm_batch_2.csv` (140), `items_batch_2.csv` (44),
`facts_batch_2.csv` (275). Scripts: `scripts/ev_batch2_*.py` (rerunnable; rows are de-duplicated). Raw pages:
`raw/evidence_batch2/`.

The dog-weight gate was read as **≥ 25 lb** (CLAUDE.md changed during the run; the brief still says 40).

## 1. Live check

- **51 live, 1 gone, 0 repriced above $3,000.** Every Apartment List page was re-fetched with `refresh=True`; the
  Garden Communities, BLT (SightMap), Greystar, AvalonBay and Zumper pages too.
- **Gone:** Prospect Place 02-122 (Hackensack). 02-229 is still listed at $2,470.
- **Price drift between copies:** Avalon Maplewood. AvalonBay's own page has 324 at $2,590 and 436 at $2,710 (as
  stored); Apartment List shows $2,600 and $2,715. The own-site rows are the ones written. Both prices are long
  lease terms (18 and 19 months); totals with required fees are $2,679 and $2,799.
- **Lease-term traps:** Avalon Old Bridge 9204 is $2,290 only on a 14-month term; the 12-month term is $2,700
  (total $2,809). 9206 is $2,265 (14 months) or $2,275 (12 months); both carry a required $109 technology fee.
- **Stale-looking feeds:** Hedges at Hawthorne 409 (available_on 2025-09-24, feed has no last-checked time) and
  The Mercer 8F (available_on 2025-12-01). Both are still shown as available; confirm by phone.
- **No availability date on the page:** Clinton Flats (two floor plans) and 9060 Palisade Ave #D710 (Zumper).
- **Floor-plan level only (no unit):** The Jefferson, Pondview Estates, Clinton Flats.
- **Possible scam:** 9060 Palisade Ave #D710 at $1,699 for an 815 sq ft condo in a doorman and pool building; the
  same Zumper page gives a North Bergen 1-bed median of $2,500. Verify the lister (FBPH Rentals) before contact.
- Own leasing sites found for every Apartment List building except The Mercer; most could not be read (below).

## 2. Gate facts (34 buildings + 1 duplicate row)

| fact | confirmed | unconfirmed |
|---|---|---|
| dogs allowed | 35 | 0 |
| elevator | 23 | 12 |
| floor | 8 | 27 |
| dog weight limit | 7 | 28 |

- **Weight limits stated:** Jefferson 100 lb combined; Prospect Place "Under 40 lbs"; Clinton Flats 40 lb; no limit at
  Harrison Yards, 3 Journal Square, West Side Square, The Harper. Four more say a weight limit exists without the
  number (Grand Imperial, Imperial, Valley and Bloom, Riverview Terrace).
- **Floors confirmed from the manager's own data:** The Beacon (4, 12), The Quincy (2, 4), The Grand (2, 6), 500 PARQ
  (5, 6), Avalon Maplewood (3, 4), Avalon Old Bridge (2, 2), 9060 Palisade (7). The other floors are derived from
  unit numbers and left `unconfirmed`.
- **Elevator not stated anywhere readable:** The Beacon, The Quincy, The Grand, 500 PARQ (tall or mid-rise, so
  probably fine), West Side Square, The Ballantine, The Harper, 218 Millburn Avenue.

## Alarming or gate-threatening

- **Steel Works 1142 and 1119:** unit numbers start with 1 where the building's units run 1xxx to 5xxx. They may be
  ground-floor units. Ask before touring.
- **Likely no elevator:** Avalon Old Bridge (both units are on floor 2; the feature list has no elevator and mentions
  townhomes), Pondview Estates ("two-story apartment residences", townhomes), Riverview Terrace (1952 garden
  complex), 218 Millburn Avenue (search results describe a 2-storey 1950 building; not verified from a page).
- **Portside Towers (Equity Residential):** long rent-control fight. Jersey Digs, 2025-04-01: tenants' class action
  seeking over $400 million; increases "of up to 50 percent" at 155 Washington Street. Hudson Reporter, 2022-12-07:
  increases over 30 percent. Articles on floods and faulty elevators at Equity's Jersey City buildings exist
  (The Real Deal 2022, Patch, Hudson County View) but those sites block us, so nothing was taken from them.
- **The Beacon:** three critical resident reviews in Oct–Nov 2026 on the building's own page (garage fees rising
  every six months and guest parking taken over; conditions not fixed "months and months"; rude concierge). Three
  different complaints, so not three of the same problem.
- **The Harper:** search results show a Patch article about a Secaucus town meeting with the owner over crime at the
  building. Patch disallows Claude agents; it was not read and nothing is recorded from it. Worth a human look.

## 3. Evidence items

12 items on 3 buildings (management 6, other 3, positive 3); `none_found` for the other 32 rows.
Tenant reviews are almost unreachable for this batch: Apartment List, Trulia and Zumper building pages carry no
review text, and the only reviews readable were the Google-review widget on The Beacon's own page (dated by the
widget's timestamps).

## Blocked (stopped, not worked around)

- **403:** prospectplaceapts.com, goldberg-realty.com (six buildings), onetenjc.com, equityapartments.com,
  valleyandbloom.com, theballantine.com, hedgesathawthorne.com, bbb.org (profile pages), therealdeal.com (robots.txt).
- **robots.txt disallows Claude agents:** cobaltlofts.com, steelworksapts.com, patch.com, nj.com, tapinto.net,
  re-nj.com, hudsoncountyview.com, jcitytimes.com, njbiz.com, northjersey.com.
- **bozzuto.com:** its robots.txt disallows ClaudeBot and anthropic-ai but allows Claude-User and Claude-SearchBot.
  The shared helper requires every Claude group to allow, so its review pages (The Wyldes, Cobalt Lofts, Birch
  House) were not read. Coordinator's call whether Claude-User applies.
- **Not fetched by design:** securecafe.com unit lists; Apartments.com-network review pages (forrent.com and a
  university housing page) that surfaced for Clinton Flats and Grand Imperial.
- cpo.soar.com (a council-meeting summary on Portside security): connection failed.
- One slip: after bbb.org returned 403 on the first profile, the loop made four more requests to it before I
  stopped. No retries after that.
- JavaScript-only sites that returned shells with little text: thewyldes.com, atlasjc.com, thehazeljc.com,
  westsidesquare.com.

## Other notes

- Management per own site: Harrison Yards, 3 Journal Square and The Harper link to Greystar; The Wyldes and Birch
  House to Bozzuto. No take-over dates were found for any manager.
- Solaris Lofts and Atlas say their rents are net-effective (concessions already taken out), so the contract rent
  is higher than the listed price.
- Atlas lists extra monthly charges on Apartment List: amenity $75, trash $20, internet $65.
