# Craigslist harvest notes (2026-11-15)

## Status: stopped before the bulk harvest. 0 listings written. Needs Will's decision.

Craigslist is technically open (robots-allowed, plain HTML, no bot wall), but its **Terms of Use prohibit
automated collection**. CLAUDE.md rule 3 says to respect terms, and SOURCES.md already treats Realtor.com as
off limits for a similar notice, so I did not run the harvest. `data/listings_raw/craigslist.csv` has the
header only.

Terms of Use, https://www.craigslist.org/about/terms.of.use (footer link "terms"), read 2026-11-15:

- USE: "You agree not to copy/collect CL content via robots, spiders, scripts, scrapers, crawlers, or any
  automated or manual equivalent (e.g., by hand)."
- USE: no software or services that "interact or interoperate with CL, e.g. for downloading ... searching",
  other than their app and general-purpose browsers, unless licensed.
- "You agree not to collect CL user information." Liquidated damages are listed for harvesting users'
  information and for other breaches.
- LICENSE: no displaying, framing, derivative works or distribution of CL content.

Options for Will:
1. Leave Craigslist out of the scripted pipeline; a person browses it by hand with the search URLs below
   and adds finds manually. (Note the terms' "manual equivalent" wording covers copying, not reading.)
2. Approve a one-off low-volume run anyway: `python3 scripts/h_craigslist.py --approved-by-will`
   (about 1,400 requests at 1 per 3.2 s, roughly 75 minutes).

## What was fetched (20 requests in total, at least 3 s apart, project User-Agent)

- robots.txt on www, newyork, hudsonvalley, newhaven, cnj, jerseyshore, newjersey: all 200. `User-agent: *`
  only; **no group names Claude or any other agent**; no Crawl-delay. Disallowed: `/reply`, `/fb/`,
  `/suggest`, `/flag`, `/mf`, `/mailflag`, `/eaf` (and `/sitemap/` on the city hosts). Search and
  `/view/d/` posting pages are allowed.
- 7 search pages (Queens variants, one Hudson Valley), 1 posting page, the terms page. No 403, 429 or CAPTCHA.
- These test pages are in the session scratchpad, not in `raw/`. No listing data was saved to the repo.

## URL patterns (verified)

- `https://newyork.craigslist.org/search/que/apa?...` → 301 →
  `https://www.craigslist.org/search/subarea/que?cat=apa&...`
- `https://hudsonvalley.craigslist.org/search/apa?...` → `https://www.craigslist.org/search/area/hudsonvalley?cat=apa&...`
- Filters that work in the no-JavaScript HTML: `max_price=3000`, `min_price`, `min_bedrooms`, `max_bedrooms`
  (0 = studio), `pets_dog=1`. There is no "posted within N days" parameter (only `postedToday=1`) and no
  elevator filter; post age comes from the posting page.
- Posting: `https://www.craigslist.org/view/d/<slug>/<token>`.
- The no-JS search page lists results as `li.cl-static-search-result` (title, price, locality, link) plus
  JSON-LD. **It has no pagination (`s=` is ignored) and seems to stop near 300 results** (unfiltered Queens
  gave 295; studio+1BR ≤ $3,000 without the dog filter gave 280). The script therefore queries studio and 1BR
  separately and splits into price bands when a query returns 270 or more.

## Counts seen on search pages (card level only, not verified on posting pages)

| query (≤ $3,000, dogs OK) | results |
|---|---|
| Queens, studio | 24 |
| Queens, 1BR | 82 |
| Queens, studio + 1BR | 106 |
| Queens, studio + 1BR, **no dog filter** | 280 (probably capped) |
| Hudson Valley, studio + 1BR | 63 |

So the dog filter removes well over half of Queens posts; posts that simply left the box unticked are lost
with it. One Queens search result was priced at $1, a placeholder price.

## What a posting page gives (from the one page fetched)

- Price (`span.price`), title, posted time, post id, first photo (`og:image`).
- Map pin lat/lon with `data-accuracy`; JSON-LD locality, state and a ZIP that Craigslist derives from the
  pin. Street address was empty on the sample; expect it to be missing often.
- Attributes: `0BR / 1Ba`, dogs OK, cats OK, housing type, laundry, broker-fee line. Square feet, parking and
  available date appear only when the poster filled them in (not on the sample, so those regexes are untested).
- Elevator and floor only in free text. On the sample both were present ("Elevator Building", "Floor: 5"),
  because it was a broker feed post (RealtyMX). Dog text there said "Pets: Case By Case" despite the dogs-OK
  box, with no weight limit, so the attribute alone does not meet the "explicitly allowed, ≥ 40 lb" gate.

## Fill rates

Not measurable: no harvest was run. Dogs, elevator, floor, available date: 0 of 0.

## Script

`scripts/h_craigslist.py` refuses to fetch without `--approved-by-will`. `--selftest SEARCH.html POST.html`
checks the parsers offline (passed on the two sample pages). It stops on 403, 429 or a block page, keeps a
request budget, stores no phone numbers, emails or poster names (phones are hashed in memory only to count
repeats), and tags rather than drops: same text in 3 or more posts, same phone in 8 or more, price under 55%
of the area median for that bedroom count, price under $500, posts older than 14 days, body text that
contradicts the dogs-OK box.
