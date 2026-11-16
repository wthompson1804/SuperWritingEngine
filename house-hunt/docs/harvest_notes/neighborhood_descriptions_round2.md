# Harvest notes: outside descriptions, round 2 (character quotes)

Run: 2026-11-16. Script `scripts/neighborhood_descriptions_round2.py` (stages `bodies`, `candidates`, `web`, `compile`,
`write`; `all` runs them in order in about 11 seconds once everything is cached and sends no request).
Outputs: `data/reference/neighborhood_descriptions_round2.csv` (one row per quote: round 1's columns plus `character`
and `topic`) and `data/reference/neighborhood_summaries_round2.csv` (`hood_id, hood_name, plain_summary,
landmarks_json, best_character, n_quotes`). Round 1 files were not touched.

## Result

- **137 neighborhoods** (site/data.json, round 1's list, and the eight Jersey City pieces; `nj:jersey-city` is kept as
  well because round 1 has it). **All 137 have at least one quote; 345 quotes** (85 neighborhoods have three, 38 have
  two, 14 have one). All 345 pass the verbatim re-read (`verified = yes`).
- **95 neighborhoods have at least one `character = 3` quote; 37 top out at 2; 5 have only `character = 1`**
  (Princeton, Riverdale NJ, Roxbury, and the two East Flatbush pieces).
- By source: Wikipedia 294; CTvisit (Connecticut Office of Tourism) 25; NYC Tourism + Conventions 12; Visit Hudson
  (Hudson County tourism office) 5; Visit Westchester (county tourism) 4; Essex County Parks 4; City of Hackensack 1.
- By topic: parks 76, transit 58, main street 46, housing feel 46, waterfront 34, landmark 31, food and nightlife 25,
  event 20, history 9 (never more than one history line per neighborhood; the script enforces it).
- By scope: exact 282, enclosing 39, **part 24**. `part` is new in round 2: the quote is about one named place inside
  the neighborhood (a park, a downtown, a station), and `about_area` names it. The page should show `about_area`
  whenever it differs from the neighborhood's name, because some of these sentences say "the park" or "the stadium".
- Landmarks: 232 across 123 neighborhoods, each with `name, kind, named_by, source_url`. The script rejects a landmark
  that is neither named in one of the neighborhood's quotes nor the stated subject (`about_area`) of one.

## Method

1. **Wikipedia body text, from the dump only.** `en.wikipedia.org` stayed off (ended in round 1). The full wikitext of
   every round 1 article was re-extracted from the dump blocks already cached under
   `raw/big/neighborhood_descriptions/`. 71 extra titles (the Jersey City neighborhoods, and articles about a downtown,
   park or station inside a town) were looked up in the cached index; 60 resolved, and their blocks were fetched from
   `dumps.wikimedia.org` with Range requests (all 206, no refusal). 199 articles are cached in
   `raw/neighborhood_descriptions_round2/bodies/`. Not found in the dump: Downtown Bridgeport, Downtown Jamaica,
   Downtown New Rochelle, Downtown Shelton, Downtown White Plains, Long Beach Boardwalk, Main Street (Hackensack),
   Paramount Hudson Valley Theater, Riverview-Fisk Park and a few alternative spellings.
2. **Cleaning is stricter than round 1.** A template is rendered only when its visible output is known exactly (dashes,
   non-breaking space, `nowrap`). References and maintenance tags vanish. Every other template, any leftover markup,
   and any `<sub>/<sup>/<small>` leaves a mark, and a marked sentence is never quotable (1,738 sentences). Round 1's
   cleaner matched template names by prefix, so `{{formatnum}}` or `{{as of}}` could vanish silently; round 2 matches
   names exactly. Sentences must start with a capital, digit or quote mark and end with `.`, `!` or `?`.
   List items are kept as their own paragraphs and are quotable only when they are whole sentences.
3. **Topic filter.** Round 1's filter plus more terms (class labels, "upscale", religious buildings, percentages,
   density, housing projects), and a second pattern for word stems. Round 1's stems (`immigra`, `segregat`, `demograph`)
   sat inside a whole-word match and so never fired on "immigrants" or "segregation"; round 2 fixes that for its own
   output. Sections about demographics, government, education, crime, climate, media and notable people are skipped.
   Three sentences the filter caught on a place name were allowed by hand (`force`): "White Plains" twice and "Indian
   Wells State Park".
4. **Selection by hand** from a shortlist of the best-scoring sentences per article
   (`raw/neighborhood_descriptions_round2/shortlist.txt`) plus targeted searches of the candidates file. Picks are in
   `picks_wiki.txt` (article title, sentence number, character, topic) and `build_picks_web.py` → `picks_web.json`
   (first and last words of each web sentence; the exact text is copied from the cached page, never retyped).
5. **Official pages.** robots.txt first for every host (a group naming ClaudeBot, Claude-User, Claude-SearchBot or
   anthropic-ai is the one that applies; `Crawl-delay` honoured), then one request per page through `lib.cached_get`
   with no retry. A URL is never requested twice. **63 page requests in total** (cap 220), never more than 2 per
   neighborhood: 48 returned a page, 14 were 404 (guessed addresses on tourism sites), 1 was a 403. Web search was
   used 7 times to find addresses; no quote comes from a search result.
6. **`write` re-verifies everything**: a Wikipedia quote must equal one whole undamaged sentence (or two consecutive
   ones in the same section) of the re-cleaned cached article; a web quote must be found in the cached page text,
   start at a sentence boundary and end a sentence. Over 35 words, a filtered topic without `force`, more than three
   quotes or more than one history line per neighborhood, or a landmark with no support, stops the run.

## Hosts

| Host | Result |
|---|---|
| `en.wikipedia.org` | Not called (ended in round 1). |
| `dumps.wikimedia.org` | Range requests for the new articles' blocks, all 206. |
| `www.yonkersny.gov` | **Refused: HTTP 403 on robots.txt.** Ended. |
| `www.mta.info` | **Refused: HTTP 403 on robots.txt.** Ended. |
| `www.nycgovparks.org` | robots.txt allowed the page; **the page itself returned HTTP 403.** Ended after one request. This closes NYC Parks pages, the obvious official source for the city neighborhoods. |
| `visitnj.org` | robots.txt allowed the page; **an Incapsula bot-challenge page came back instead (HTTP 200, 212 bytes).** Treated as a wall. Ended after one request. This closes the state tourism source for New Jersey. |
| `parks.ny.gov` | robots.txt has groups naming ClaudeBot and anthropic-ai that disallow the page. Not requested. |
| `www.vsvny.org` (Valley Stream), `www.cityofnewbrunswick.org` | robots.txt disallows us. Not requested. |
| `ctvisit.com` | Allowed (`*`). 16 town pages read, all 200. |
| `www.nyctourism.com` | Allowed. 22 requests: 11 pages, 11 were 404 (no page for that neighborhood). |
| `www.visitwestchesterny.com` | Allowed, crawl delay 2 s. 8 requests, one 404. |
| `www.visithudson.org` | Allowed, crawl delay 3 s. 9 requests, one 404. |
| `www.essexcountyparks.org` | Allowed. 4 pages. |
| `www.hackensack.org` | Allowed, crawl delay 20 s. 1 page. |
| `www.visitprinceton.org` | 404 on the one address tried. |
| `www.cityofshelton.org`, `www.nycgo.com`, `www.stamford-downtown.com` | TLS certificate problems. Not read (verification is never disabled). |
| `www.cityofwhiteplains.com`, `www.princetonnj.gov`, `www.longbranch.org`, `www.cityofpeekskill.com`, `www.newbrunswick.com`, `jamaica.nyc` | Connection reset or proxy error before any HTTP answer. Not a refusal; not retried. |

Refusals are persisted in `raw/neighborhood_descriptions_round2/_host_kill.json` and in the shared
`raw/_host_kill_shared.json`; the script reads both (and round 1's file) before every request.

## Honest limits

- **Still thin:** Princeton, Riverdale (NJ), Roxbury and both East Flatbush pieces have only a bare line. Their
  Wikipedia articles have little usable body text (or it is all measurement templates), and the official hosts for
  them were closed, unreachable or not tried. 37 more top out at `character = 2` (listed by the script's output;
  mostly New Jersey suburbs and outer-borough neighborhoods without a tourism page).
- **New Jersey has no tourism-board quotes outside Hudson and Essex counties**, because `visitnj.org` served a bot
  wall. New York City has no parks-department quotes, because `nycgovparks.org` refused.
- **Tourism copy is promotional.** CTvisit, NYC Tourism, Visit Westchester and Visit Hudson write to sell a visit
  ("never a dull moment", "world-class antiquing"). The quotes are attributed, but the page should keep the source
  name visible. One Westport line says "high-end shops"; it describes shops, not residents, and was kept. CTvisit
  town pages may carry text supplied by the town itself.
- **Web quotes are quotations, not licensed text.** `licence_note` says so; they are one sentence each.
- **Wikipedia text is the revision in the dump of 2026-11-01**, as in round 1; the live article may differ. Some body
  sentences are older in tone than a lead ("a housewares store" on Hackensack's Main Street, Berry Lane Park is long
  finished but one article still says it is under construction, so that sentence was not used).
- **Context-dependent sentences.** A few picks say "the park", "the stadium", "this neighborhood" or "It". Where the
  subject is not the neighborhood itself, `about_area` names it (Sports Illustrated Stadium, Roosevelt Forest,
  St. George Terminal, Elmora, Presidential Estates, Delaware and Raritan Canal State Park, Monte Irvin Orange Park,
  Flushing Meadows Corona Park, Bensonhurst Park, Berry Lane Park). The White Plains nightlife line is about
  mid-county Westchester with White Plains at its centre and is marked `enclosing`.
- **Shared quotes.** The two Bedford-Stuyvesant halves carry the same three quotes; the Astoria pieces, the Gravesend
  pieces and the two East Flatbush pieces share theirs (all `enclosing`). Madison is quoted from Sheepshead Bay,
  Hillcrest from Fresh Meadows, Parkville from Kensington, South Slope from Park Slope, as Wikipedia redirects them.
- **Jersey City pieces.** Wikipedia has articles for all eight. McGinley Square's is short (two plain lines);
  Greenville's is plain; Newport's waterfront line comes from the county tourism page about the Waterfront Walkway.
  The site's names ("Jersey City – Downtown") are used.
- **Topic list.** Only the nine topics in the brief are used. Arts-scene lines were filed under `landmark` or
  `main street`, the nearest fit.
- `plain_summary` (25 words or fewer) was written by hand from the quotes; it is checked for length only.
- `retrieved_at` on Wikipedia rows is the time the article was extracted from the cached dump block.

## For `docs/SOURCES.md` (not edited here)

- `ctvisit.com/listings/city-<name>` or `town-<name>`: one page per Connecticut town, plain HTML, allowed.
- `www.nyctourism.com/new-york/<borough>/<neighborhood>/`: about half the neighborhoods tried have a page.
- `www.visitwestchesterny.com/about-westchester/communities-local-flair/<region>/<town>/`, `www.visithudson.org/neighborhoods/<town>/`,
  `www.essexcountyparks.org/parks/<park>`: allowed, plain HTML.
- `www.nycgovparks.org`, `visitnj.org`, `www.yonkersny.gov`, `www.mta.info`: refuse us. `parks.ny.gov` disallows Claude by name.

## Rerun

`python3 scripts/neighborhood_descriptions_round2.py` (or a single stage name). Hand inputs live in
`raw/neighborhood_descriptions_round2/`: `picks_wiki.txt`, `build_picks_web.py` → `picks_web.json`, `landmarks.txt`,
`summaries.txt`, `web_plan.json`. Adding an article title to `EXTRA` in the script makes `bodies` rescan the 286 MB
index (about 4 minutes) and fetch the new block from the dump host.
