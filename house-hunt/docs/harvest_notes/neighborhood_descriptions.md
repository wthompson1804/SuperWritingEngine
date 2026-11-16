# Harvest notes: outside descriptions of each neighborhood (`neighborhood_descriptions`)

Run: 2026-11-16, about 00:15 to 01:00 UTC. Script `scripts/neighborhood_descriptions.py`.
Outputs: `data/reference/neighborhood_descriptions.csv` (one row per quote) and
`data/reference/neighborhood_summaries.csv` (one row per neighborhood).

## What happened with Wikipedia (read this first)

- The brief's first choice was the Wikipedia lead through the MediaWiki API. **The first request of the session to
  `en.wikipedia.org` (REST summary for Kew Gardens) was refused: "You are making too many requests to the API"
  (rate limit, HTTP 429).** Under the one-refusal rule that host was ended for the session. No second request was sent.
  The likely cause is the shared outbound address plus our User-Agent, which carries no contact address (Wikimedia
  gives unidentified clients a very low limit). A contact address in the User-Agent would be Will's decision.
- The same text was instead read from **Wikimedia's public database dump** (`dumps.wikimedia.org`, enwiki dump of
  2026-11-01), which is the channel Wikimedia offers for automated bulk use. It has no robots.txt (404) and never
  refused. This is a different host and a different service from the one that refused; it is not the live API under
  another name. **If Will reads the rule as covering every Wikimedia host, delete the two CSVs**: 272 of 274 quotes
  depend on this choice.
- Consequence: each quote is the wording of a specific revision (id and timestamp are in `licence_note`), up to a few months old (the dump labelled 2026-11-01 holds revisions as late as 2026-11-04). The live article may read differently today. The page should say "Wikipedia" and link the
  article; the licence is CC BY-SA 4.0.
- DBpedia was tried as another openly licensed copy: its current release has no English abstracts (3 requests, no
  refusal, nothing used).

## Method

1. One download of the dump's title index (286 MB, kept in `raw/big/neighborhood_descriptions/`, not committed).
2. 157 article titles (151 distinct articles after redirects) were located in the index; one HTTP Range request per
   compressed block (115 requests, at least 1 s apart, 38 MB in total). Only the lead section of each article is kept, in
   `raw/neighborhood_descriptions/leads/*.json`, with revision id, revision time, byte range and retrieval time.
3. The lead's wikitext is turned into plain text. **A sentence that contained a template we cannot render (unit
   conversions, pronunciation, subway-line icons) is marked and never quoted**, because our text would differ from
   what a reader sees. Sentences over 35 words are never quoted (no trimming inside a sentence).
4. A topic filter drops sentences about who lives there by race, ethnicity or religion, immigration, crime, income
   and class, population counts, rankings, and the administrative lines (community district, precinct, ZIP code).
   Four sentences the filter caught by accident ("White Plains" as a place name twice, "bicycle race", "an enclave
   of Victorian-era homes") were allowed by hand; they are marked `force` in the curation file.
5. Quotes were chosen by hand from what was left (`raw/neighborhood_descriptions/curation.json`), preferring
   character, history, main street, parks and waterfront over plain location lines. Class labels such as "middle
   class" or "working class" and "wealthiest" were skipped by hand as well.
6. `write` re-reads each cached lead, rebuilds the text and accepts a quote only if it equals one whole sentence (or
   two consecutive ones) word for word. All 274 rows passed (`verified = yes`).
7. `plain_summary` (25 words or fewer) and `landmarks_json` were written by hand and restate only what the quotes
   say. The script rejects any landmark whose name does not appear in one of that neighborhood's quotes.

## Coverage

- Neighborhood list: union of `site/data.json` and `scene_text_neighborhoods.csv`. It moved between 126 and 129 during
  the run; the script now remembers every id it has seen (`raw/neighborhood_descriptions/hood_names.json`). **129 ids.**
- **128 of 129 have at least one quote; 274 quotes** (23 neighborhoods have one, 64 have two, 41 have three).
- **112 neighborhoods have at least one quote about the place itself (`scope = exact`); 16 have only a quote about a
  larger area (`enclosing`)**: the three Astoria pieces, both Bedford-Stuyvesant halves, both East Flatbush pieces,
  East Harlem (South), East New York (North), Gravesend (South) and (West), Harlem (North), Washington Heights
  (South), North Corona, Madison (Wikipedia redirects it to Sheepshead Bay) and Haverstraw (the town article; the
  village lead had no usable sentence).
- By source: Wikipedia 272, City of New Rochelle official website 2.
- **Nothing: Patchogue.** Every descriptive sentence in its Wikipedia lead carries a distance conversion, and the
  village website (`patchoguevillage.org`) failed TLS certificate verification, so it was not read.

## Honest limits

- **Many quotes are plain.** A Wikipedia lead for a small municipality is often one location sentence plus census
  and incorporation history. About 20 neighborhoods have only a line such as "Garwood is a borough in Union County".
  They are real and attributed, but they carry no character: Shelton, Westport, Garwood, Long Branch, Montvale,
  Ridgewood, Belleville, East Orange, Carteret, East Brunswick, Dover, Roxbury, Elizabeth, Glen Cove, Englewood,
  both East Flatbush pieces, Bound Brook, West Haven, Brighton Beach (name origin only), LaGrange (name origin only),
  Parsippany-Troy Hills (name trivia only).
- Richer text sits in the body of the same articles (History, Geography) and on municipal sites. Neither was
  harvested: the brief named the lead, and the official-site pass was done for one place only (below).
- Combined neighborhoods use the articles of the places in their name. A redirect was followed where Wikipedia has
  no separate article: South Slope → Park Slope, Parkville → Kensington, Madison → Sheepshead Bay (`about_area` says so).
  Olinville, Electchester, Farragut, Hallets Point and Murray Hill (Queens) redirect to an article already used.
  Hillcrest (→ Fresh Meadows), Sugar Hill, Jamaica Hills, Willowbrook, Lenox Hill beyond one line, and Fox Hills
  have no quote of their own.
- Jamaica Hills-Briarwood has a Briarwood boundary line only; the Jamaica Hills lead is a single class-label sentence.

## Hosts

| Host | Result |
|---|---|
| `en.wikipedia.org` | **Refused** (rate limit on the first request). Ended; flag persisted in `raw/neighborhood_descriptions/_host_kill.json`. |
| `dumps.wikimedia.org` | No robots.txt (404 = no rules). 115 Range requests and one index download, all 200/206. |
| `dbpedia.org` | robots allows `/data/`. 3 requests, 200. No English abstracts in the current release; not used. |
| `www.newrochelleny.gov` | robots.txt names ClaudeBot and Claude-SearchBot in a group that carries the site-wide rules (admin, search, login paths disallowed; `/120/...` allowed). One page read, 200. |
| `www.newrochelleny.com` | Redirects to the `.gov` host over plain HTTP; connection failed. Not a refusal. |
| `www.patchoguevillage.org`, `patchoguevillage.org` | TLS certificate verification failed. Not read (verification is never disabled). |

No 403, CAPTCHA or wall was met. Web search was used twice, only to find the New Rochelle page and to look for a
Patchogue page; no quote comes from a search result.

## For `docs/SOURCES.md` (not edited here: this pass writes new files only)

- Wikipedia text: use the dump (`dumps.wikimedia.org/enwiki/<date>/…-multistream.xml.bz2` with its index and Range
  requests). The live API refuses our client at the first request.
- CivicPlus municipal sites (New Rochelle is one) serve plain HTML and allow us under the site-wide rules.

## Rerun

`python3 scripts/neighborhood_descriptions.py` runs every stage and refetches nothing that is cached.
`index` needs the 286 MB index again only if new titles are added to `HOODS`. `write` alone rebuilds both CSVs from
the caches and `curation.json`; it stops with a message if a pick is over 35 words, template-damaged, on a filtered
topic without `force`, or fails the verbatim check.
