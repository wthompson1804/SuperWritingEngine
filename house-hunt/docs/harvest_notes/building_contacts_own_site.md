# Own-site leasing phones (`data/reference/building_contacts_own_site.csv`)

Built by `scripts/building_contacts_own_site.py` on 2026-11-16 (UTC). It covers the 91 rows of
`data/reference/building_contacts.csv` that had only a Trulia tracking number (58), no phone (26), or a number with
an out-of-region area code (7). `building_contacts.csv` itself is not edited; this file sits beside it and joins on
`building_id`.

```
python3 scripts/building_contacts_own_site.py            # offline: rebuild the CSV from the cache, no requests
python3 scripts/building_contacts_own_site.py --fetch    # fetch pages not cached yet (resumable; honours refusals)
```

## Method

1. **Search (by the agent, not the script).** One web search per building: name + address + "apartments". The first
   eight searches returned only aggregators, so they were repeated once with aggregator domains excluded, and every
   later search excluded them from the start. Newark Urby also took a second search, restricted to urby.com. The
   chosen own site (or "none found", with what the results held) is in
   `raw/building_contacts_own_site/search_seeds.jsonl`. No phone number was taken from a search result.
   The Current on River and 89-25 162nd St already had an own site in `building_contacts.csv` and were not searched.
   1483 Shore Pkwy reused the manager page found for 2072 20th Ln (same owner entity).
2. **Fetch.** robots.txt first (groups naming Claude override `*`), then at most two pages per building through
   `scripts/lib.py: cached_get` (1 request/second/host): the page from the search, then the property's link on a
   manager's index page, or the seed's second URL, or the page's own "contact" link.
3. **Read the phone from the page**: JSON-LD `telephone`, `tel:` links, then page text. On a page that lists several
   properties, the number printed right after this building's address is used. Otherwise a number with a NY/NJ/CT
   area code is preferred to a toll-free or out-of-region one; the other numbers on the page are listed in `note`.
4. **Confidence.** `high`: the building's name and its street address are both on the page that carries the phone
   (for a building named after its address: the address is on the page and the domain carries the house number).
   `medium`: only one of the two (rows with no building name in the data can reach `medium` at most).
   `low`: neither, typically a manager's general contact page.
5. **Stated facts** (`stated_*`): a verbatim fragment from the pages already fetched, no extra requests.

Owner-listed single units (8 rows, `contact_kind = individual owner`) are skipped: no search, no phone, no name.

## Result (91 rows)

| | tracking number (58) | no phone (26) | out-of-region (7) |
|---|---|---|---|
| Phone, high | 29 | 0 | 0 |
| Phone, medium | 4 | 3 | 3 |
| Phone, low | 0 | 2 | 1 |
| Own site found, no phone read | 11 | 3 | 0 |
| Own site not found | 14 | 10 | 3 |
| Skipped (individual owner) | 0 | 8 | 0 |

Among currently shown buildings: 15 high and 3 medium replacements for tracking numbers (of 36 shown).

83 buildings were searched or seeded (cap 110), 97 searches, 56 had an own site, 101 requests (robots.txt included).

## Why a found site gave no phone

- **Refused during this run (HTTP 403), no further requests:** `www.10oceanapts.com` (ELK Harbor View),
  `www.750summer.com` (750 Summer Street), `www.504glenbrook.com` (504 Glenbrook), `vanderbiltpm.com`
  (142-27 Barclay Ave). Persisted in `raw/building_contacts_own_site/_refused_hosts.json`.
- **Refused in an earlier harvest, not requested:** `www.5545park.com`, `www.loftsat335.com`, `www.163franklin.com`.
- **robots.txt disallows ClaudeBot:** `sonopearl.com`, `highlandsmorrisplains.com`, `www.harborgroupmanagement.com`
  (Skyline New Rochelle), `hudson44.com`, `www.jolionguider.com` (3440 Guider Ave).
- **Not reachable (not a refusal):** `rentashton.com` (expired TLS certificate; verification was not disabled),
  `www.metrovuejsq.com` (502; the building's other domain, metrovuejc.com, worked).
- **No number in the HTML:** `bedfordcreativeapts.com` (home and contact pages).

## Caveats

- A JSON-LD `telephone` is sometimes different from the number displayed (The George, Parc at Roxbury, The
  Brunswick, Harbourside SoNo): the displayed one is toll-free, the JSON-LD one local. The local one is recorded and
  the other is in `note`. Either may be a call-tracking line.
- The Current on River: the header number is still (971) 612-4298; the recorded (551) 363-0110 is printed in the
  site's specials banner ("Call 551-363-0110"). Medium.
- 89-25 162nd St (livejamaicacentral.com): the only number on the contact page is still (413) 459-5565.
- Residences at The Summit has only a toll-free number on its own site.
- Manager general lines, not a building's office: Harclay House (Shamco), Metro Star - Metro 121, 66 Saint Nicholas
  Pl (Rose Associates contact page, low), 2072 20th Ln and 1483 Shore Pkwy (Revona, low).
- 187 Culver Avenue: the site is the owner company's (John and Maryan LLC); the address is on it, the name
  "The Tetris" used by brokers was not checked. Medium.
- `office_hours` from JSON-LD can show `Sun 00:00-00:00` (The Current on River); read it as closed or unknown.
- `stated_*` quotes come from home and contact pages, which rarely state fees. Ten shown buildings have any, mostly "pet-friendly" or "elevator" with no figures.
- New hosts and their robots/refusal outcomes are listed above; `docs/SOURCES.md` was not edited (this task writes
  new files only).
