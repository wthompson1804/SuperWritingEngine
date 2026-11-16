# Building contacts (`data/reference/building_contacts.csv`)

Built by `scripts/building_contacts.py` on 2026-11-16 (UTC). One row per building in `data/ranked_units.csv`
(all rows, shown or not) plus any building that appears only in `data/needs_confirmation.csv` (none did on this run).
The file is rebuilt whole on every run, so it follows the ranked list as it changes. Re-run:

```
python3 scripts/building_contacts.py            # offline only, about 5 seconds, no requests
python3 scripts/building_contacts.py --fetch    # one page for each building that still has no phone
python3 scripts/building_contacts.py --fetch --upgrade-tracking   # not run: see "Not done"
```

## Result of this run (250 buildings, 697 ranked units)

| | buildings | basis |
|---|---|---|
| With a phone | 224 | all `cached_page` (offline) |
| Leasing or listing URL only | 26 | all `cached_page` |
| Nothing | 0 | |
| Fetched | 0 | no request was made (see below) |

Where the 224 numbers come from:

| Source | buildings | Flag |
|---|---|---|
| The building's or manager's own site, already cached by earlier harvests | 70 | none; 14 of them share a number with another building and are `management company` (manager's shared line) |
| Apartment List `original_phone` (the number the property supplied) | 35 | 21 are toll-free lines |
| Zumper building page | 2 | "not checked against the building's own site" |
| Brokerage number in a Trulia single-unit listing attribution | 59 | `contact_kind = broker` |
| Trulia building page | 58 | `listing-site tracking number` |

So 58 of 224 phones (26%) are listing-site tracking numbers, all from Trulia building pages. Among the 177 shown
buildings, 157 have a phone and 40 of those are tracking numbers.

The 26 rows without a phone: 8 `individual owner` and 9 `management company` (a person posted the listing with no
brokerage; the pipeline's records name an owner or manager company but no page gives its number), 8 `broker`
(brokerage named, no number on the page) and 1 leasing office (Bedford Creative, Stamford: the Trulia building
page has no number). Each carries the listing URL in `leasing_url`.

Other columns: `office_hours` filled for 122 buildings, `manager_name` for 194, an own-site `leasing_url` for 95.

## What each page gives

- **Apartment List** (flight JSON, `listing` object): `phone` is the number displayed and is an Apartment List
  tracking number; `original_phone` is what the property supplied (10 digits, sometimes followed by an extension
  digit); `website_url` is the property's site (query string dropped); `office_hours_this_week` gives hours (UTC,
  converted to Eastern).
- **Trulia building page** (`__NEXT_DATA__.props.homeDetails`): `description.contactPhoneNumber` and
  `planVisit.propertyManagementCompany.phoneNumber`. Compared on the 31 buildings that are cached on both Trulia
  and Apartment List, neither Trulia number ever equalled the property-supplied one, so both are treated as
  forwarding numbers. The "Property Website" link is a zillow.com redirect and was not followed.
  `planVisit.officeHours` and the management company name are used.
- **Trulia single-unit page**: `activeListing.provider.broker` name and phone (the "Listing by: ..." attribution).
  The agent's name is never stored. No broker named means a person posted it: `individual owner`, no phone, no name.
- **Zumper** (`__PRELOADED_STATE__.detail.entity.data`): `phone`, `brokerage_name`, `hours`. `(844) ... ext. N`
  numbers are Zumper proxy lines. A listing with no brokerage or company is `individual owner`.
- **Zillow building page** (one cached): `buildingPhoneNumber`, flagged as tracking.
- **Own sites** (cached under `raw/evidence_*`, `raw/mgmt_*`, `raw/community_facts` and others): JSON-LD
  `telephone`, then `tel:` links (most frequent), then the page text when it holds exactly one number. Own-site
  leads come from Apartment List `website_url`, `building_site` facts in `data/evidence/facts_batch_*.csv`,
  `community_facts.csv`, and non-aggregator URLs in the ranked row (`url`, `building_url`, `*_source` except
  `year_built_source`, which often cites a news article).

Preference: own site > Apartment List supplied number > Zumper building page > Trulia / Zillow building page >
brokerage number > Zumper proxy line. Other numbers seen for the building are listed after "also seen" in `note`.

## Caveats

- An own-site number can itself be a call-tracking line placed by the site's marketing vendor. Rows whose area code
  is outside NY/NJ/CT and not toll-free say so in `note` (7 rows, for example The Current on River, 971).
- `gardenhomesmanagement.com/apartments/` is one page for three Stamford buildings; the number is the manager's.
  The three GDC buildings in Beacon share one line as well.
- Trulia forwarding numbers can be retired when the listing ends. Check them against the building's own site
  before relying on them.
- A brokerage number in a single-unit listing reaches the brokerage, not the building.
- 87 rows have no `building_name` because the ranked list has none for that address.

## Requests and refusals

No request was made on this run. After the offline pass, every building without a phone was a person-listed or
broker-listed single unit, or a Trulia-only building with no known site, so step 2 had no allowed page to fetch
(trulia.com is on the never-request list). No host refused.

The fetch path is in place for later runs: robots.txt first (groups naming Claude override `*`), one page per
building, and any 401/403/429 or bot wall is written to `raw/building_contacts/_refused_hosts.json` at once and
honoured on every later run. Hosts recorded as blocked by earlier harvests (`raw/*/_blocked_hosts.json`, 403/429
lines in any `_index.jsonl`; 172 hosts) are skipped too. `raw/building_contacts/` does not exist yet because
nothing was fetched.

## Not done

- **Replacing the 58 Trulia tracking numbers.** None of those buildings has a known own-site URL in the data (the
  Trulia "Property Website" link goes through zillow.com), so `--upgrade-tracking` would find nothing to fetch
  today. Getting the real numbers needs the building sites to be found first (a search step, outside this brief).
- No phone lookups for person-listed units, by design.
