# Building contacts, trawl 2 (`data/reference/building_contacts_trawl2.csv`)

Made 2026-11-17 (UTC) by a sub-agent. The scripts that made it live in a scratch folder, not in `scripts/`. This page
records every step so the file can be rebuilt. The columns are the same as `building_contacts.csv`.

## Scope

The scope is every building with at least one unit in `data/ranked_units.csv` with `shown = True` and
`listed_rent <= 2000`, and no row in `building_contacts.csv` or `building_contacts_own_site.csv`. That makes
**135 buildings: NJ 94, CT 30, NY 11.** NJ and CT were worked first. NY got the offline pass and two searches.

## Method

1. **Offline pass, no requests.** For each target building, `scripts/building_contacts.py` already has the
   functions `load_buildings`, `build_index`, `offline_candidates` and `build_row`. Running them reads every listing
   page and own-site page the pipeline already holds, with the same preference order as the main contacts file:
   own site, then Apartment List `original_phone`, then Zumper, then Trulia building page, then brokerage.
   The script's `main` was not run, because it would rewrite `building_contacts.csv`.
2. **Search, then read the page.** WebSearch was used only to find a building's or manager's own site. Every value
   in the file was read from the page itself. Values seen only in search snippets were not used: snippets quoted
   ForRent, Apartments.com and RentCafe numbers that disagree with each other.
3. **Fetch rules.** For each host, robots.txt is read first. The `Claude-User` group is used if the file has one,
   otherwise `*`. Then one GET is sent, with an honest user agent (`scripts/lib.py: USER_AGENT`) and at least
   3.2 s between requests to the same host. These hosts are never fetched: `lib.host_refusal` (OFF_LIMITS plus
   `raw/_host_kill_shared.json`), RentCafe, securecafe, Entrata, prospectportal, AppFolio, RealtyMX, Trulia, Zillow
   and the other off-limits listing sites. A 401, 403 or 429, or a bot wall, ends that host. It is written to
   `raw/contacts_trawl2/_refused_hosts.json` and to `raw/_host_kill_shared.json` (`by: contacts_trawl2`).
   No retries were made.
4. **The private rule (`contact.private`).** A row whose `contact_kind` is `broker` or `individual owner` carries
   no `leasing_phone`, no source URL and no hours. It has only the listing page in `leasing_url`, and its `note`
   starts with `private:`. A person's name is never stored in `manager_name`: a broker row keeps the name only when
   it is a business (`business_name()`), and an owner row keeps no name. `scripts/page_data_extras.py` hides these
   numbers anyway; this file just does not hold them.

Raw pages are cached in `raw/contacts_trawl2/` (`<sha1>.html` + `.meta.json`, `_index.jsonl`).

## Result

| State | Public phone | Site only, not private | Private (broker or owner): listing page only | Nothing |
|---|---|---|---|---|
| NJ | 26 | 18 | 50 | 0 |
| CT | 19 | 5 | 6 | 0 |
| NY | 2 | 2 | 7 | 0 |
| **All** | **47** | **25** | **63** | **0** |

Where the 47 public phones come from:

| Source | NJ | CT | NY |
|---|---|---|---|
| Own or manager site, read in this trawl (`basis = fetched_page`) | 3 | 9 | 0 |
| Own site, already cached by earlier harvests | 7 | 0 | 0 |
| Apartment List `original_phone`, the number the property supplied | 16 | 4 | 0 |
| Trulia building page: listing-site forwarding (tracking) line, flagged in `note` | 0 | 6 | 2 |

### Read from the building's or manager's own site in this trawl

| Building | Phone | Page | Hours |
|---|---|---|---|
| Golden Hill Apartments, Milford CT | (203) 653-2474 | gardenhomesmanagement.com property-detail pid=87 (the page gives the address as 27 Golden Hill St) | none on the page |
| Horizon Homes, Naugatuck CT | (203) 723-0690 | pid=91. This corrects the offline pick (203) 653-2474, which is Golden Hill's line on the manager's shared page | none |
| West Hill Apartments, Naugatuck CT | (203) 723-0690 | pid=107, the same office as Horizon Homes. Replaces a Trulia tracking line | none |
| Parkview (270 Spring St and the "270 N Spring St" duplicate), Naugatuck CT | (203) 439-5031 | parkviewapartmenthomes.com | Mon-Fri 9-12 and 13-18; Sat 10-17 (JSON-LD) |
| The Shelton Grove, Shelton CT | (475) 369-9588 | thesheltongrove.com (Apartment List had (475) 284-8585) | hours kept from Apartment List |
| 3 Bedford Ave, 31 Ferris Ave, 8 Union Ave (IVE Living), Norwalk CT | (203) 900-4467 | livingive.com. This is the manager's shared line (`management company`) | none |
| Artisan at Lawrenceville NJ | (609) 928-7211 | artisanlawrenceville.com | Mon/Wed/Fri 9-6, Tue/Thu 9-7 |
| Stewards Crossing, Lawrenceville NJ | (609) 928-8306 | rentstewardscrossing.com | Mon/Wed/Fri 9-6, Tue/Thu 10-7 |
| Brakeley Gardens, Phillipsburg NJ | (908) 651-9927 | harborgroupmanagement.com property page (the JSON-LD telephone there is (908) 544-9554, noted) | Mon-Fri 9-17 (JSON-LD) |

Other changes to the offline rows:
- **Quail Ridge:** `leasing_url` is set to www.quailridgenj.com, a link found on the manager's site wmapts.com. That
  host refused us, so the phone stays the Apartment List number.
- **Buena Vista:** the `leasing_url` was an OpenStreetMap link. It is now the Apartment List page.
- **226 Roseville Ave, Newark:** the lister is a private person, so the row is now `individual owner` and the
  number is withheld.
- **Mandy Management (2 buildings):** these are now `management company` with no phone. The manager's site,
  mandy-management.com, does not resolve, and the number in the Trulia attribution is not used.
- **Nextdoor Leasing (7 Bayonne and Jersey City buildings):** these are `management company` with no phone. No
  site or office line was found for this small leasing outfit.

### Site only, not private (25)

These are small management outfits or LLCs with no site of their own that we could find, plus a few buildings
with no listed number. The names are Swift Apt Rentals, NJ Leasing CO, Tunic Group, Reset Living, Rosa agency,
Vector Management, Stratford Gardens LP, Elm City Realty, Mandy Management and Nextdoor Leasing. Each row carries
the listing page we hold. Search found only aggregator pages (ForRent, Apartments.com, Rentler, RentCafe) for
these. Their numbers were not taken, because they come from snippets or off-limits hosts.

## Refusals (4, all HTTP 403, one request each, recorded)

`www.townwalkhamden.com`, `www.crestprinceton.com`, `www.addisonprinceton.com`, `www.quailridgenj.com`. On all three
of those buildings' rows (Town Walk, Crest, Addison) the Apartment List supplied number stands, with a note.
`www.510main.com` and `www.mandy-management.com` did not resolve (DNS). That is not a refusal.

## Not done

- No own site was found for Encore 99, Bay Shore Apartments (CS Management / CSRE), Kelsey's Landing, Brookside
  Gardens, Campbell Ave Apartments, 925 at North (Franklin Communities: its listings are on AppFolio, which is off
  limits), Cortlandt Living or Mid Island Apartments. Their rows keep the Trulia forwarding line, flagged as such.
- Goldberg Realty buildings (7) and Carlton Club: the own-site hosts were already on the kill list, so the
  Apartment List supplied numbers stand.
- NY got only light searching (lowest priority).

## Wiring

`scripts/page_data_extras.py` reads a fixed pair of files (`Paths.contacts`, `Paths.contacts_own`), so this file is
not used until one line is added in `contacts()`, right after `O, why_o = c.csv(c.P.contacts_own, ...)`:

```python
    C = None if C is None else C + (c.csv(c.P.contacts.with_name("building_contacts_trawl2.csv"), need=("building_id",))[0] or [])
```

The building ids do not overlap with `building_contacts.csv`, so nothing in that file is overridden.
