# Evidence pass, batch 4 (2026-11-15)

35 batch rows = 26 distinct buildings (Flushing has six duplicate rows: the same unit or building listed by two
brokers; Hempstead's 479 Front St appears twice; La Mesa Verde in Jackson Heights is five rows).
All 35 rows done. Fetches ran 20:30–20:50 UTC.

Scripts (all idempotent): `scripts/evidence_batch_4_fetch.py` (re-fetch of every listing URL, cache bypassed),
`evidence_batch_4_openigloo.py` (Openigloo building pages matched by BBL through the reviewed-buildings sitemap),
`evidence_batch_4_get.py` (robots-checked single-page fetch), `evidence_batch_4_build.py` (writes the four CSVs; it
refuses nothing but prints any quote that is not a verbatim substring of the cached page: 0 at the last run).
Raw pages: `raw/evidence_b4/`, `raw/openigloo/`.

## 1. Live check (38 unit rows)

- 37 live at the stored price, 1 changed, 0 gone, 0 blocked. All 36 listing URLs returned HTTP 200.
- Changed: Carraway unit 3078, base rent $2,795 → $2,805.
- **Carraway all-in is over the cap.** The building's own floor-plans page shows "Total Monthly Price" of $2,847.14
  (unit 3035's plan) and $2,952.14 (3078's plan): base rent plus $147.14 of required monthly fees. With pet rent
  ($50) and parking ($125) that is $3,022.14 and $3,127.14 before electricity.
- **Alvista Rise prices are net-effective.** Gross rent is $2,800 (2410) and $2,825 (1922); the $2,365 / $2,435 shown
  assume 2.5 months free on an 18-month lease.
- 273 W 131st St 4F shows "available now" but the description says the tenant leaves 11/30.
- 63-60 102nd St D-8 is available Dec 1. 9508 65th Rd A3 is available Nov 20.
- Two prices look too low to trust without a phone call: 98-76 Queens Blvd 2M (1BR, 900 sqft, $1,663) and
  9508 65th Rd A3 (1BR condo, $1,699, with a $3,400 "Moveinfee" in the page data).
- Unit labels differ from the stored ones on two La Mesa Verde rows: the page's unit field says E42 (address line
  says E12) and H53 (address line says H51).

## 2. Gate facts

- **Dogs not allowed (6 rows, 3 buildings):** Rose Terrace (139-81 35th Ave), The Bennington (140-16 34th Ave) and
  North Main Towers (137-02 Northern Blvd). Both brokers' descriptions say dogs only as service or emotional-support
  animals. The structured "dogs allowed" flags on Trulia and Zumper are wrong for these.
- **Elevator in doubt (5 rows):** La Mesa Verde. The complex has two elevators for six buildings; tenants and one of
  the manager's own listings ("Walk Up Building", unit 451) say some buildings are walk-ups.
- Elevator confirmed for 22 of 26 buildings. Not confirmed: 2165 Clarendon Rd, 4110 Bowne St, 133-24 Sanford Ave,
  La Mesa Verde.
- Floor stated on a page for 3 buildings only (139-81 35th Ave 6D = 6th, 142-38 37th Ave 8E = 8th, 63-60 102nd St
  D-8 = 4th). Everything else is inferred from the unit number and marked unconfirmed. None looks like a ground floor.
- **Dog weight limit: not one building states a number that applies today.** Trulia's "small dogs" line is identical
  on every broker listing in the batch, so it reads as a feed default, not a policy. Alvista Rise says large dogs are
  allowed (no number). La Mesa Verde: an older listing by the same agent says "Pet Friendly up to 30 Pounds" (passes
  the 25 lb gate if still true). 63-60 102nd St and 142-38 37th Ave say "small pets" only, without naming dogs.
- Note: the gate in `CLAUDE.md` changed to 25 lb while this ran. The CSV records what pages say; no row depends on
  the old 40 lb figure.

## 3. Evidence

62 distinct items (115 rows once repeated across duplicate batch rows, plus 9 none_found rows): management 27, positive 13, elevator 9,
safety 5, noise 4, other 4, none_found for 8 buildings. No `car_crime` item was found for any building.

Most serious:

1. **La Mesa Verde (5 rows).** Queens Ledger, 2025-12-18: both elevators out for more than six months in 2025; more
   than 100 tenants suing owner A&E Real Estate over 800+ HPD violations. PoliticsNY, 2026-02-24: residents report a
   month without heat and ask for elevator service to be restored. Current listings say "Now under new management"
   with no date, so who runs it now is unverified.
2. **139-55 35th Ave.** One detailed review dated 2026-02-06 (older than six months): elevator "constantly getting
   stuck", pests, inconsistent heat, package theft.
3. **The 88 (153-10 88th Ave).** Run by Zara Realty, which the NY Attorney General sued on 2025-08-06 for
   overcharging rent-stabilized tenants (other buildings). One review dated 2026-07-24, inside the six-month window:
   "Fishy fees, utility shams and constant power outages."
4. **The Bennington.** 2024 reviews: harassment by management, roaches, four months without gas. Moot: no dogs.
5. **273 W 131st St.** 2022 review: elevator out three weeks, hot water problems.

Only one review falls inside the plan's six-month window (The 88, Jul 2026; nothing else after mid-May 2026),
so no building reaches "three tenants, same problem, last six months" on this evidence alone. La Mesa Verde's case
rests on news reports from Dec 2025 and Feb 2026.

Openigloo's visible relative dates ("6 minutes ago") disagree with the page's own `datePublished` in one case
(85-05 Elmhurst Ave, 2025-04-04). The CSV uses `datePublished` throughout.

## 4. Blocked or not done

- **qns.com: robots.txt disallows ClaudeBot.** Two directly relevant Mesa Verde articles (Nov 2025 protest, Feb 2026
  rally) were not fetched. PoliticsNY carries the first two paragraphs of the February piece, which was used.
  amNY is the same publisher and was not tried.
- alvistarise.com: TLS certificate hostname mismatch, not fetched. Alvista Rise facts come from its Trulia building page.
- Archer House's own site has no unit list or pet policy ("For current availability, call"). The 88's site has no
  prices or pet policy. Carraway's site gives fees but no dog weight limit.
- Openigloo has no reviewed page for 6 NYC buildings (2165 Clarendon Rd, 3420 Avenue H, 142-38 37th Ave, 4110 Bowne
  St, 143-45 Sanford Ave, 95-08 65th Rd). 3310 and 3320 Avenue H share 3420's tax lot but are different co-op
  buildings under other managers; their reviews were read and left out.
- Not attempted: Better Business Bureau pages, court dockets, Apartment List / Zumper review blocks beyond the
  listing pages (all were empty in page data). HPD, DOB and 311 were left to the public-records agent.
- Web search was used only to find URLs. A search summary claimed Carraway has a 75 lb dog limit; that came from
  Zillow and HotPads snippets, was not verified on an allowed page, and is not in the CSVs.
