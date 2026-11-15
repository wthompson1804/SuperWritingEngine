"""Round 2 of the neighborhood-voices pass: page neighborhoods (site/data.json) with no row in round 1's quotes file.

Sources (owner-approved targeted lookups): Niche place review pages, City-Data forum threads. Never trulia.com.
robots: the Claude-User group if a site has one, else `*`; Crawl-delay honoured; >= 4 s per host; every request goes
through scripts/lib.py cached_get.

HARD RULE, enforced here: one refusal (401/403/429/503, CAPTCHA, bot wall) from a host writes that host into
raw/voices_round2/_host_kill.json. guarded_get() refuses every later request to that host, in this process and in
every later run of this script. Nothing in this script ever clears the file.

Usage:
  python3 scripts/voices_round2.py targets    # print the uncovered set
  python3 scripts/voices_round2.py niche      # fetch Niche review pages (resumable; skips URLs already tried)
  python3 scripts/voices_round2.py citydata   # fetch the hand-listed City-Data threads (CITYDATA_THREADS)
  python3 scripts/voices_round2.py build      # write data/voices/*_round2.csv (rewrites them; verifies every excerpt)
Writes only: data/voices/{neighborhood_quotes,neighborhood_survey,coverage}_round2.csv and raw/voices_round2*/.
"""
from __future__ import annotations
import collections, csv, html, json, re, sys, urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse
import lib

UA = "house-hunt-research/0.1 (personal research for one renter; user-requested lookups)"
ROBOTS_AGENT = "Claude-User"            # robotparser falls back to the `*` group when a site has no such group
MIN_DELAY = 4.0
FORBIDDEN = ("trulia.com", "reddit.com", "yelp.com", "nextdoor.com", "zillow.com", "streeteasy.com", "apartments.com",
             "apartmentratings.com", "patch.com", "qns.com", "bbb.org")
ALLOWED_HOSTS = ("www.niche.com", "www.city-data.com")
SRC_NICHE, SRC_CD, SRC_ROBOTS = "voices_round2_niche", "voices_round2_citydata", "voices_round2_robots"
WORK = lib.RAW / "voices_round2"; WORK.mkdir(parents=True, exist_ok=True)
KILL = WORK / "_host_kill.json"
STATUS = WORK / "_status.jsonl"
POOL = WORK / "pool.jsonl"
OUT = lib.DATA / "voices"

# ------------------------------------------------------------------ uncovered set
def uncovered():
    d = json.load(open(lib.ROOT / "site/data.json"))
    have = {r["hood_id"] for r in csv.DictReader(open(OUT / "neighborhood_quotes.csv"))}
    un = [n for n in d["neighborhoods"] if n["id"] not in have]
    un.sort(key=lambda n: (-n["counts"]["shown"], n["drive_min"] or 999))
    return un

# ------------------------------------------------------------------ guarded fetch
def killed() -> dict:
    return json.loads(KILL.read_text()) if KILL.exists() else {}

def kill(host, url, why):
    k = killed(); k.setdefault(host, dict(url=url, why=why, at=lib.now_iso()))
    KILL.write_text(json.dumps(k, indent=1))
    print(f"KILL {host}: {why} at {url}. No further requests to this host, ever, from this script.", flush=True)

def log(**kw):
    with open(STATUS, "a") as f: f.write(json.dumps(kw) + "\n")

def tried():
    return {json.loads(l)["url"]: json.loads(l) for l in open(STATUS)} if STATUS.exists() else {}

def walled(status, text):
    t = text[:20000].lower()
    return (status in (401, 403, 429, 503) or "px-captcha" in t or "are you a robot" in t or "captcha" in t[:6000]
            or "access denied" in t[:3000] or "just a moment" in t[:2000] or "access to this page has been denied" in t)

_robots = {}; _soft_stop = set()
def robots(host):
    if host in _robots: return _robots[host]
    url = f"https://{host}/robots.txt"
    content, meta = _raw_get(url, SRC_ROBOTS, "txt")
    if content is None: _robots[host] = None; return None
    rp = urllib.robotparser.RobotFileParser(); rp.parse(content.decode("utf8", "ignore").splitlines())
    _robots[host] = rp
    lib.HOST_DELAY[host] = max(MIN_DELAY, float(rp.crawl_delay(ROBOTS_AGENT) or 0))
    return rp

def _raw_get(url, source, ext):
    host = urlparse(url).netloc
    if host not in ALLOWED_HOSTS or any(host.endswith(f) for f in FORBIDDEN): raise SystemExit(f"host not approved: {host}")
    if host in killed() or host in _soft_stop: return None, None
    lib.HOST_DELAY.setdefault(host, MIN_DELAY)
    try:
        content, meta = lib.cached_get(url, source, ext=ext, headers={"User-Agent": UA, "Accept": "text/html,*/*"}, retries=1, timeout=40)
    except RuntimeError as e:                      # cached_get raises on 429/502/503/504 and on network errors
        msg = str(e); m = re.search(r"HTTP (\d+)", msg)
        code = int(m.group(1)) if m else None
        log(url=url, status=code, note="fetch error: " + msg[-120:], at=lib.now_iso())
        if code in (429, 503): kill(host, url, f"HTTP {code}")
        else: _soft_stop.add(host); print("STOP (this run)", host, msg[-120:], flush=True)
        return None, None
    if walled(meta["status"], content.decode("utf8", "ignore")):
        log(url=url, status=meta["status"], note="refusal / bot wall: host killed", at=lib.now_iso())
        kill(host, url, f"HTTP {meta['status']} or bot wall")
        return None, None
    return content, meta

def guarded_get(url, source):
    """Returns (content, meta) or (None, None) when the host is killed/stopped or robots disallows the URL."""
    host = urlparse(url).netloc
    if host in killed(): return None, None
    rp = robots(host)
    if rp is None: return None, None
    if not rp.can_fetch(ROBOTS_AGENT, url):
        log(url=url, status=None, note="robots disallows", at=lib.now_iso()); return None, None
    return _raw_get(url, source, "html")

# ------------------------------------------------------------------ Niche targets
def _n(s): return f"n/{s}-new-york-city-ny"
def _ct(s, region): return f"{s}-{region}-planning-region-ct"
NV, SC, GB, WC = "naugatuck-valley", "south-central-connecticut", "greater-bridgeport", "western-connecticut"
# hood_id -> candidate slugs. At most two requests per hood (a 404 on a guessed slug counts as one).
NICHE = {
 "ct:shelton": [_ct("shelton", NV)], "ct:hamden": [_ct("hamden", SC)], "ct:beacon-falls": [_ct("beacon-falls", NV)],
 "ct:fairfield": [_ct("fairfield", GB)], "ct:seymour": [_ct("seymour", NV)], "ct:stratford": [_ct("stratford", GB)],
 "ct:west-haven": [_ct("west-haven", SC)], "ct:brookfield": [_ct("brookfield", WC)], "ct:oxford": [_ct("oxford", NV)],
 "nj:franklin": ["franklin-township-somerset-nj"], "nj:bound-brook": ["bound-brook-somerset-nj"],
 "nj:east-brunswick": ["east-brunswick-township-middlesex-nj", "east-brunswick-middlesex-nj"],
 "nj:east-rutherford": ["east-rutherford-bergen-nj"], "nj:elizabeth": ["elizabeth-union-nj"],
 "nj:long-branch": ["long-branch-monmouth-nj"], "nj:red-bank": ["red-bank-monmouth-nj"],
 "nj:south-orange": ["south-orange-village-township-essex-nj", "south-orange-essex-nj"],
 "nj:springfield": ["springfield-township-union-nj", "springfield-union-nj"],
 "nj:wayne": ["wayne-township-passaic-nj", "wayne-passaic-nj"],
 "nj:weehawken": ["weehawken-township-hudson-nj", "weehawken-hudson-nj"],
 "nj:fort-lee": ["fort-lee-bergen-nj"], "nj:garwood": ["garwood-union-nj"],
 "nj:maplewood": ["maplewood-township-essex-nj", "maplewood-essex-nj"],
 "nj:old-bridge": ["old-bridge-township-middlesex-nj", "old-bridge-middlesex-nj"],
 "nj:princeton": ["princeton-mercer-nj"], "nj:ridgewood": ["ridgewood-bergen-nj"],
 "nj:roxbury": ["roxbury-township-morris-nj", "roxbury-morris-nj"], "nj:somerville": ["somerville-somerset-nj"],
 "ny:glen-cove": ["glen-cove-nassau-ny"], "ny:long-beach": ["long-beach-nassau-ny"], "ny:patchogue": ["patchogue-suffolk-ny"],
 "ny:wallkill": ["wallkill-orange-ny"],
 "ny:bath-beach": [_n("bath-beach")], "ny:midwood": [_n("midwood")],
 "ny:rockaway-beach-arverne-edgemere": [_n("rockaway-beach"), _n("arverne")],
 "ny:upper-west-side-manhattan-valley": [_n("upper-west-side"), _n("manhattan-valley")],
 "ny:bay-ridge": [_n("bay-ridge")], "ny:east-harlem-south-": [_n("east-harlem")],
 "ny:flatbush-west-ditmas-park-parkville": [_n("ditmas-park")],
 "ny:gravesend-east-homecrest": [_n("gravesend"), _n("homecrest")], "ny:gravesend-south-": [_n("gravesend")], "ny:gravesend-west-": [_n("gravesend")],
 "ny:manhattanville-west-harlem": [_n("manhattanville"), _n("west-harlem")],
 "ny:new-springville-willowbrook-bulls-head-travis": [_n("new-springville"), _n("willowbrook")],
 "ny:pomonok-electchester-hillcrest": [_n("hillcrest"), _n("pomonok")],
 "ny:riverdale-spuyten-duyvil": [_n("riverdale"), _n("spuyten-duyvil")],
 "ny:st-george-new-brighton": [_n("st-george"), _n("new-brighton")],
 "ny:kew-gardens-hills": [_n("kew-gardens-hills")], "ny:windsor-terrace-south-slope": [_n("windsor-terrace"), _n("south-slope")],
}
# Hoods where both named parts are wanted when the first is found (still two requests at most).
BOTH = {"ny:rockaway-beach-arverne-edgemere", "ny:upper-west-side-manhattan-valley", "ny:riverdale-spuyten-duyvil",
        "ny:st-george-new-brighton", "ny:windsor-terrace-south-slope", "ny:pomonok-electchester-hillcrest",
        "ny:gravesend-east-homecrest", "ny:new-springville-willowbrook-bulls-head-travis"}
# Pages already cached by round 1 (raw/voices_niche): reused with NO new request. label = source_area to record.
CACHED_R1 = {
 "ny:washington-heights-south-": [("https://www.niche.com/places-to-live/n/washington-heights-new-york-city-ny/reviews/", "Washington Heights (whole)")],
 "ny:old-astoria-hallets-point": [("https://www.niche.com/places-to-live/n/astoria-new-york-city-ny/reviews/", "Astoria (enclosing area)")],
 "ny:murray-hill-broadway-flushing": [("https://www.niche.com/places-to-live/n/flushing-new-york-city-ny/reviews/", "Flushing (enclosing area)")],
 "ny:hamilton-heights-sugar-hill": [("https://www.niche.com/places-to-live/n/harlem-new-york-city-ny/reviews/", "Harlem (enclosing area)")],
}
# Never requested in round 2: the one Niche URL that answered 403 in round 1.
NICHE_NOT_RETRIED = {"nj:new-brunswick": "https://www.niche.com/places-to-live/new-brunswick-middlesex-nj/reviews/"}

def niche_url(slug): return f"https://www.niche.com/places-to-live/{slug}/reviews/"

def strip(x): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()

def parse_niche(s):
    """-> (title, rating, count, [review dicts]). No reviewer names exist on Niche pages; none are kept."""
    title = strip(re.search(r"<title[^>]*>(.*?)</title>", s, re.S).group(1))
    m2 = re.search(r"Rating ([\d.]+) out of 5 ([\d,]+) reviews", strip(s))
    revs = []
    for n, blk in enumerate(re.split(r'(?=<div class="review" data-testid="review")', s)[1:], 1):
        b = re.search(r'itemprop="reviewBody">(.*?)</div>', blk, re.S)
        dt = re.search(r'<meta content="([\d-]+)" itemprop="datePublished"', blk)
        rt = re.search(r'<meta content="(\d)" itemprop="ratingValue"', blk)
        who = re.search(r'itemprop="author".*?<span itemprop="name">(.*?)</span>', blk, re.S)
        pid = re.search(r'helpfulness-rating[^"]*" data-testid="([0-9a-f-]+)"', blk)
        if not b or not dt: continue
        paras = [strip(x) for x in re.split(r"<br\s*/?>", b.group(1))]
        revs.append(dict(post_id=pid.group(1) if pid else f"#{n}", text="\n".join(p for p in paras if p), date=dt.group(1),
                         who=strip(who.group(1)) if who else "", rating=int(rt.group(1)) if rt else None))
    return title, (m2.group(1) if m2 else None), (m2.group(2).replace(",", "") if m2 else None), revs

def fetch_niche():
    seen = tried(); memo = {}
    for h in uncovered():
        hid = h["id"]; got = 0; reqs = 0
        for slug in NICHE.get(hid, []):
            if got and hid not in BOTH: break
            url = niche_url(slug)
            if url in memo: got += memo[url]; continue
            if url in seen:
                ok = seen[url].get("status") == 200; memo[url] = ok; got += ok; reqs += 1; continue
            if reqs >= 2: break
            if "www.niche.com" in killed(): print("niche is killed; stopping"); return
            content, meta = guarded_get(url, SRC_NICHE); reqs += 1
            if content is None:
                if "www.niche.com" in killed() or "www.niche.com" in _soft_stop: return
                continue
            if meta["status"] != 200:
                log(url=url, status=meta["status"], hood_id=hid, note="not found", at=lib.now_iso()); memo[url] = False
                print(hid, slug, meta["status"], flush=True); continue
            title, rating, count, revs = parse_niche(content.decode("utf8", "ignore"))
            log(url=url, status=200, hood_id=hid, title=title, rating=rating, count=count, reviews=len(revs), path=meta["path"], at=meta["retrieved_at"])
            memo[url] = True; got += 1
            print(hid, slug, 200, title, rating, count, len(revs), flush=True)

# ------------------------------------------------------------------ City-Data threads (hand-listed after web searches)
# hood_id -> thread URLs. Forum search and member pages are never requested.
CITYDATA_THREADS: dict[str, list[str]] = {
 "nj:new-brunswick": ["https://www.city-data.com/forum/new-jersey/3216900-living-new-brunswick.html",
                      "https://www.city-data.com/forum/new-jersey/2589281-new-brunswick-nicest-areas-live-city-4.html"],
 "ny:flatbush-west-ditmas-park-parkville": ["https://www.city-data.com/forum/new-york-city/2451372-parking-ditmas-park-kensington-brooklyn.html",
                                            "https://www.city-data.com/forum/new-york-city/2113862-safety-flatbush-ditmas-park.html"],
 "ny:manhattanville-west-harlem": ["https://www.city-data.com/forum/new-york-city/2127281-west-harlem-morningside-manhattanville.html",
                                   "https://www.city-data.com/forum/new-york-city/1675040-135th-broadway-manhattanville-feedback.html"],
 "ny:pomonok-electchester-hillcrest": ["https://www.city-data.com/forum/new-york-city/3308658-tell-us-your-stories-about-electchester.html",
                                       "https://www.city-data.com/forum/new-york-city/2774633-electchester-not-what-use-3.html"],
}
# Hand-picked forum excerpts: dict(hood_id, url, post_id, date, excerpt, theme, sentiment, context)
CITYDATA_KEEP: list[dict] = []

def fetch_citydata():
    seen = tried()
    for hid, urls in CITYDATA_THREADS.items():
        for url in urls[:2]:
            if url in seen: continue
            content, meta = guarded_get(url, SRC_CD)
            if content is None:
                if "www.city-data.com" in killed() or "www.city-data.com" in _soft_stop: return
                continue
            s = content.decode("utf8", "ignore")
            if meta["status"] == 200:    # strip usernames from the cached copy (working rule 6)
                s2 = re.sub(r'(<a class="bigusername"[^>]*>).*?(</a>)', r"\1[member]\2", s, flags=re.S)
                s2 = re.sub(r"(Originally Posted by <strong>).*?(</strong>)", r"\1[member]\2", s2, flags=re.S)
                s2 = re.sub(r'(/forum/members/)[^"\']+', r"\1[member]", s2)
                (lib.ROOT / meta["path"]).write_text(s2, encoding="utf8")
            log(url=url, status=meta["status"], hood_id=hid, path=meta.get("path"), at=meta["retrieved_at"],
                title=strip(re.search(r"<title[^>]*>(.*?)</title>", s, re.S).group(1)) if meta["status"] == 200 else None)
            print(hid, meta["status"], url, flush=True)

# ------------------------------------------------------------------ classification (rules copied from round 1's voices_build.py)
TH = collections.OrderedDict([
 ("car_crime", r"car (break|theft|thefts|thieves|jack)|cars? (was|were|got|get|gets|been|being|is|are) (broken|stolen|vandal)|broke into (my|our|the|his|her) car|broken into|stolen car|car stolen|catalytic|car ?-?jack|cars? (can|could|might|will) (be|get) stolen|auto theft|vehicle theft|stole my car|vandaliz\w+ (my |our )?cars?|break-?ins"),
 ("safety", r"\bsafe\b|\bsafer\b|\bsafest\b|safety|unsafe|\bcrime|dangerous|at night|robber|mugg|police|shooting|sketchy|violen|gang|after dark|well[- ]lit|walk(ing)? alone|feel secure|drug"),
 ("parking", r"parking|\bpark (my|your|the|a) car|alternate side|find a spot|parking spot|garage"),
 ("dogs_green", r"\bdogs?\b|\bpets?\b|puppy|\bparks?\b(?!ing)|green space|greenery|\btrees?\b|tree-lined|trail|nature|garden|waterfront|\bbeach|hik(e|ing)|outdoor"),
 ("social_life", r"restaurant|\bbars?\b|nightlife|night life|caf[eé]|coffee shop|things to do|nothing to do|meet (new )?people|community events?|events|live music|social|going out|brewer|food scene|entertainment|boring|downtown"),
 ("noise", r"\bnois|\bloud|\bquiet|siren|peaceful|calm\b|music blasting|honking"),
 ("value", r"\brent\b|rents\b|expensive|afford|cost of living|pricey|overpriced|price|cheap|taxes|costly"),
 ("people", r"neighbors?\b|famil(y|ies)|young professionals|students|retirees|community|residents|friendly|welcoming|people (are|here)"),
 ("travel", r"commut|subway|\btrains?\b|\bbus(es)?\b|highway|lirr|metro-?north|nj transit|path\b|traffic|drive to|minutes (to|from)|transportation|transit|parkway|expressway"),
])
REGRET = r"can'?t wait to (leave|move)|moved (out|away)|i left\b|we left\b|would not recommend|wouldn'?t recommend|do not recommend|don'?t recommend|regret|not (move|live) here again|glad (i|we) (left|moved)|planning to (leave|move)|want to (leave|move out)|moving out"
SURPRISE = r"surpris|didn'?t expect|did not expect|hidden gem|underrated|pleasantly|to my surprise|never (thought|expected)"
FROM_NYC = r"moved (here )?from (queens|brooklyn|the bronx|bronx|manhattan|nyc|new york city|the city|astoria|flushing|jamaica|harlem)|coming from (queens|brooklyn|the bronx|manhattan|nyc|the city)"
POS = r"\blove|\bgreat|\bnice|beautiful|friendly|peaceful|\bclean\b|convenien|\bbest\b|\bgood\b|amazing|wonderful|enjoy|affordab|plenty|\beasy\b|vibrant|welcoming|excellent|perfect|favorite|well[- ]kept|well[- ]maintained|well[- ]lit|\bsafe\b|\bsafer\b|\bsafest\b|\bquiet\b|\bcalm\b|comfortable|lovely|charming|fantastic|awesome|pleasant|happy|recommend|walkable|lively|fun\b|gem\b"
NEG = r"unsafe|\bcrimes?\b|dangerous|expensive|\bdirty|nois[ye]|\bloud|crowded|homeless|break-?ins?|broken into|stolen|theft|robber|hard to find|difficult|\black\b|lacks|lacking|worst|\bbad\b|terrible|trash|garbage|litter|sketchy|violen|shooting|gang|drugs?\b|overpriced|traffic|pricey|congest|\brude|nightmare|limited|challeng\w+|\btough|nonexistent|\btight\b|hassle|frustrat\w+|\bsucks?\b|ticket(ed|ing|s)?\b|forbids|denied|lucky if|concern\w*|worr(y|ied|ies|isome)|careful|cautio\w+|\bwary|\bavoid|not the safest|no parking|struggle|impossible|problem|issues?\b|downside|\bpoor\b|horrible|awful|scary|afraid|vandal|rats?\b|nothing to do|boring|not recommend|decline|worse|unfortunately|disappoint|high (rent|taxes|cost|prices)|costly|run[- ]down|neglect|can'?t wait to leave|filthy|sirens"
NEGATE = r"(\bnot|n't|n’t|\bnever|\bno|\bisnt|\bdont|\bhardly|\bbarely|\blittle|\blow|\bless|\bfew|\bwithout|\bfree of|\brarely)\s+(\w+\s+){0,3}$"
# Working rule 9: nothing about racial, ethnic or religious composition (round 1's list, widened).
BLOCK = r"\b(white|black|blacks|whites|hispanic|latin[oax]s?|asian|asians|jewish|jews?|muslims?|christians?|catholics?|chinese|korean|indian|russian|ukrainian|uzbek|italian|irish|greek|polish|caribbean|african|haitian|jamaican|dominican|mexican|puerto rican|bangladeshi|pakistani|arabs?|ethnic\w*|racial\w*|race|races|racis\w+|religio\w+|orthodox|hasid\w+|dominicans?|bachata|bukharian|bengalis?|haitians?|brazilians?|portuguese|filipino|jamaicans?|immigrants?|minorit\w+|synagogues?|mosques?|church(es)?|kosher|halal|diverse|diversity|multicultural|cultures?|cultural\w*|nationalit\w+|backgrounds?|melting pot|heritage|spanish|gentrif\w+)\b"
CONTRAST = r"\b(but|however|although|though|except|could be better|wish|downside|unfortunately|yet)\b"
MAXQ = 14

def sentences(text):
    out = []
    for para in text.split("\n"):
        para = re.sub(r"\s+", " ", para).strip()
        if not para: continue
        out.append([p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z\"“'(])", para) if p])
    return out

def sentiment(x, rating):
    xl = x.lower(); p = n = 0
    xl, k = re.subn(r"crimes?( rates?)? (is|are|was|has been|have been|stays?|remains?) (very |relatively |pretty |quite |fairly |generally )?(low|rare|minimal|down|not (a|an) (big |major )?(issue|problem))|(low|little to no|little|minimal|no|hardly any) crime", " ", xl); p += k
    for m in re.finditer(POS, xl):
        if re.search(NEGATE, xl[max(0, m.start() - 30):m.start()]): n += 1
        else: p += 1
    for m in re.finditer(NEG, xl):
        if re.search(NEGATE, xl[max(0, m.start() - 30):m.start()]): p += 1
        else: n += 1
    if p and n: return "mixed"
    if p: return "positive"
    if n: return "negative"
    if rating: return "positive" if rating >= 4 else "negative" if rating <= 2 else "mixed"
    return None

def theme(x):
    xl = x.lower()
    if re.search(REGRET, xl): return "regret", 3
    for t, rx in TH.items():
        k = len(re.findall(rx, xl))
        if k:
            if t in ("people", "travel", "value", "noise") and re.search(SURPRISE, xl): return "surprise", 2
            return t, k
    if re.search(SURPRISE, xl): return "surprise", 2
    return None, 0

def context(r, full):
    bits = []
    w = (r.get("who") or "").strip()
    if w: bits.append(w.lower())
    fl = full.lower()
    m = re.search(r"(lived|living|been) (here|in [A-Z][\w ]{2,25}?) (for )?(over |about |almost |nearly |more than )?((\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty)\+? (years?|months?|decades?))", full)
    if m: bits.append("says lived there " + (m.group(4) or "") + m.group(5))
    elif re.search(r"my (whole|entire) life|all my life|born and raised|grew up here|grew up in", fl): bits.append("says grew up / lifelong there")
    if re.search(r"\bmy dogs?\b|\bour dogs?\b|i have a dog|we have a dog|dog owner|walk(ing)? my dog", fl): bits.append("dog owner")
    m = re.search(FROM_NYC, fl)
    if m: bits.append("moved from " + (m.group(2) or m.group(3)).title().replace("Nyc", "NYC"))
    if re.search(r"\bi rent\b|as a renter|my landlord|my apartment|our apartment", fl): bits.append("renter/apartment dweller")
    return "; ".join(dict.fromkeys(bits))

def arealess(x, names):
    """Blank the place name so that 'Glen Cove' or 'Windsor Terrace' does not count as a park or garden word."""
    ns = set(names)
    for n in list(ns):
        for part in re.split(r"[-()]|, ", n): ns.add(part.strip())
    for n in sorted((n for n in ns if len(n) > 4), key=len, reverse=True):
        x = re.sub(re.escape(n), "PLACE", x, flags=re.I)
    return x

def candidates(r, names):
    if r.get("who") not in ("Current Resident", "Former Resident"): return []
    full = r["text"]; year = int(r["date"][:4]); out = []
    for para in sentences(full):
        for i in range(len(para)):
            for ex in (para[i], " ".join(para[i:i + 2]) if i + 1 < len(para) else None):
                if not ex or not (55 <= len(ex) <= 330): continue
                if re.search(BLOCK, ex, re.I) or re.search(r"\bDR\b|[Ll]ittle [A-Z]", ex) or "http" in ex or ex.endswith("?"): continue
                exa = arealess(ex, names)
                t, k = theme(exa)
                if not t: continue
                s = sentiment(exa, r.get("rating"))
                if not s: continue
                st = r.get("rating")
                if s == "positive" and re.search(CONTRAST, exa.lower()): s = "mixed"
                if st and ((s == "negative" and st >= 4) or (s == "positive" and st <= 2)): s = "mixed"
                pair = ex is not para[i]
                if pair and (theme(arealess(para[i], names))[0] is None or theme(arealess(para[i + 1], names))[0] is None): k -= 2
                elif pair: k -= 0.5
                sc = k + (2 if year >= 2024 else 1 if year >= 2022 else -2 if year < 2019 else 0)
                sc += 1 if re.search(r"\b(I|my|we|our|I've|I'm)\b", ex) else 0
                sc += 1 if 90 <= len(ex) <= 260 else 0
                sc += 1 if t in ("car_crime", "safety", "parking", "dogs_green") else 0
                sc -= 1.5 if len(re.findall(r",", ex)) >= 5 else 0
                out.append(dict(ex=ex, theme=t, sent=s, score=sc, r=r, ctx=context(r, full)))
    return out

def pick(cands):
    chosen = []; per_post = collections.Counter(); per_theme = collections.Counter()
    def ok(c):
        if per_post[c["r"]["post_id"]] >= 2 or per_theme[c["theme"]] >= 3: return False
        return not any(c["ex"] in d["ex"] or d["ex"] in c["ex"] or (c["r"]["post_id"] == d["r"]["post_id"] and set(c["ex"].split(". ")) & set(d["ex"].split(". "))) for d in chosen)
    def take(c):
        chosen.append(c); per_post[c["r"]["post_id"]] += 1; per_theme[c["theme"]] += 1
    cands = sorted(cands, key=lambda c: -c["score"])
    themes = ["car_crime", "safety", "parking", "dogs_green", "social_life", "noise", "value", "people", "regret", "surprise", "travel"]
    for t in themes:
        for c in cands:
            if c["theme"] == t and ok(c): take(c); break
    for t in themes:
        if len(chosen) >= MAXQ: break
        have = {c["sent"] for c in chosen if c["theme"] == t}
        for c in cands:
            if c["theme"] == t and c["sent"] not in have and ok(c): take(c); break
    return chosen[:MAXQ]

# ------------------------------------------------------------------ hand edits made after reading the rows
# (DROP: any excerpt containing the text; THEME_FIX / SENT_FIX: excerpt prefixes; safety / car_crime / parking rows were all read by hand, see docs/harvest_notes/voices_round2.md)
DROP: list[str] = ["Even though neighbors on my street don't like it",
 'The magnet schools are far',
 'After numerous attempts over the years',
 'It was difficult attending Ridgewood High School',
 'Better investment in infrastructure and more affordable housing',
 'it has guided me along throughout these 17 chapters',
 'At the time when St.',
 'Here is what makes Roxbury High School',
 'Special education and transportation issues',
 "It's gone from a friendly place to one full of angry people",
 'There is mixture of taste',
 'I enjoy the community of my school',
 'The Police Department consists of about 25% brass',
 'If there was change that I would like to see, it would be for there to be new roads',
 'The public schools on the Upper West are very good',
 'Very quiet at night which can be a good thing. The highschool',
 'East Rutherford provided a temporary safe haven',
 'It bugs me how much of our resources',
 'Police say it is okay.',
 'The town is super supportive, and I feel safe here as',
 'You walk around the premise at night',
 'We have some good local food places, but I would stay at night',
 'If I could change anything, I would like to see continued improvements in traffic management',
 'I do not really like the safety in the public schools',
 'Only 3 Detectives',
 'Shelton has a lot of potential, but it is saddled',
 'I faced a lot of social anxiety',
 'As a 17 year old boy',
 'My family is not very close with many people',
 'Midwood is a pretty place to live in you will not regret',
 'THe nearest grocery store to me',
 'The advocation and growth',
 '- Construction/Repair',
 'The highschool is okay just like',
 'It looks like a third world country',
 'I used to bring my dog into the building',
 'College town with Seton Hall University nearby. So everyone',
 'The town focuses on building up apartments and hotels',
 'The schools have no AC',
 'Being able to spot the other side like a maze',
 "There haven't been any crazy stories",
 'As for potential changes, I would like to see improvements in roads',
 'Living in Stratford was a great experience love the town',
 'Which, in hindsight, is not a good idea',
 'I am also a CPA',
 'My experience In long branch is the community',
 'There are families from all over',
 'Whether exploring the scenic trails of East Rock Park',
 'West Haven High School is also nice',
 'First selection man or mayor',
 'Its not a bustling city where theres traffic',
 'The environment of Seymour schools',
 'When people ask about Flushing',
 'I somewhat live in Flushing',
 'As a parent, I wish the schools were more engaging',
 'I grew up in East Harlem on 104th Street',
 'In the morning and evening, you have the rush hours',
 'More affordable transportation options would make it easier',
 'I wonder why is this intentional',
 'Today , DPW was trimming',
 "As a teenager here, there's not much to do. Many families",
 'I would like to have more nightlife and more things for teens and young adults to do in the area. Would also',
 'We moved out of Ridgewood because',
 'There is a west-side and an east-side',
 'My family has lived in Westchester',
 "It's the sister town to South Orange and shares many events, orgs, schools, and more. The school district",
 'There is only one school, K thru 8',
 'Most of the residents want to leave and are being replaced',
 'I would like for there to be more post offices',
 'The houses are different sizes around the town',
 'The public school system is superb, especially',
 'Not a community to to live in',
 'This is no surprise, considering',
 'My partner and I are part of',
 'Huge bullying issues',
 'Living together and sharing our differences',
 'The residents of Harlem will visit the same stores',
 'My parents bought our house before I was born',
 'I think that the town itself has nice qualities',
 'The only thing I would change in my city is to have outdoor public pool']
THEME_FIX: dict[str, str] = {'A countless number of parking lots': 'value',
 'A great family town. Right by the highway': 'travel',
 'Affordable is the price we pay': 'regret',
 'For example, we recently just faced a hardship': 'people',
 "From family friendly restaurants like Alfonso's": 'social_life',
 "From walking on the path around Toby's Pond": 'dogs_green',
 'Growing up, I went through all of the public schools, and went to many of the town hosted': 'social_life',
 'However, I would say that the only negative part of living in this are is the traffic': 'travel',
 "I don't like that the high taxes go to cops": 'value',
 'I like how many restaurants and stores in Stratford': 'social_life',
 "I like that in Bay Ridge, it's quite at night": 'noise',
 'It is quite and affordable to rent area': 'social_life',
 "It isn't very fun being on the outs": 'social_life',
 "It's very difficult to make good friends in this town": 'people',
 'Lots of schools and playgrounds. It gets pretty quiet': 'noise',
 'Many young people moving out': 'people',
 'One thing that bothers me is how car dependent': 'travel',
 'Park avenue could be an amazing street': 'social_life',
 'People are always seem in a harry': 'regret',
 'Rockaway Beach is a beautiful to live, but the cost of living': 'value',
 'So not safe I would not recommend': 'safety',
 'Taxes are high vs surrounding areas but the services': 'value',
 'That being said, I do wish there was a little more of a social crowd': 'social_life'}
SENT_FIX: dict[str, str] = {'Only positive to EB is the safety': 'positive',
 '- Auto Insurance': 'negative',
 'A countless number of parking lots': 'negative',
 'Affordable is the price we pay': 'negative',
 'Although parking is tough': 'negative',
 'Although the town is small, there are many safe places': 'positive',
 'As Patchogue becomes increasingly popular': 'mixed',
 'As a native to NYC, I have truly never felt more safe': 'positive',
 'Before it had more trees': 'negative',
 "Despite these good qualities, it's safety varies": 'mixed',
 'Everyone knows everyone, and when problems arise': 'positive',
 "Fairfield is a very safe town. There haven't": 'positive',
 'For example, we recently just faced a hardship': 'positive',
 "From family friendly restaurants like Alfonso's": 'positive',
 'Have lived in Gravesend for the better part of 10 years': 'mixed',
 'However, I would say that the only negative part of living in this are is the traffic': 'negative',
 'I do, however, know that it is a super safe town': 'positive',
 "I don't like that the high taxes go to cops": 'negative',
 'I left Seymour and was the best decision': 'negative',
 "I like that in Bay Ridge, it's quite at night": 'positive',
 "I must say, it's been getting harder to afford": 'negative',
 'I think this area will continue to get better': 'mixed',
 'I would also like to see continued improvements in cleanliness, safety': 'mixed',
 'I would like to see cleaner streets, more affordable housing': 'negative',
 'I would like to see more entertainment business': 'negative',
 "I've never felt unsafe walking home alone at night": 'positive',
 'In this clean community, crime rates are extremely low': 'positive',
 'It feels just about as new york city can feel': 'positive',
 'It is a very nice community, where the town is very hardworking': 'positive',
 "It's also extremely safe so you don't have to worry": 'positive',
 "It's very difficult to make good friends in this town": 'negative',
 'It’s a cool neighborhood to live in, crime rate': 'positive',
 'Lots of schools and playgrounds. It gets pretty quiet': 'positive',
 'Love living in Garwood': 'positive',
 'Many families choose to retire here or raise young children here. Besides': 'mixed',
 'Many of the families who have lived here for multiple generations': 'positive',
 'Many young people moving out': 'mixed',
 'More restaurants to be built here': 'mixed',
 'One of the main things i would like to see change my neighborhood': 'negative',
 'One thing I would like to change, though, is not feeling genuinely safe': 'negative',
 'One thing I would like to see are more drug and rehabilitation': 'negative',
 'One thing that I would want to see change is more restaurants': 'mixed',
 'One thing that bothers me is how car dependent': 'negative',
 'Our community came together to help everyone': 'negative',
 'Park avenue could be an amazing street': 'negative',
 'People are always seem in a harry': 'negative',
 'Rockaway Beach is a beautiful to live, but the cost of living': 'negative',
 'Seymour is much safer and quieter': 'positive',
 'So not safe I would not recommend': 'negative',
 'Street parking is hard anywhere': 'negative',
 'The negatives about living in Elizabeth is parking': 'negative',
 'The only thing I would like to see change in is safety': 'negative',
 'The town continues to build more apartments that are unaffordable': 'negative',
 'The traffic and main road is difficult': 'negative',
 'There no crime/robbery': 'positive',
 'They also need to address the lack of parking': 'negative',
 'They have increased rent all around town': 'negative',
 'To enjoy night life you will need to travel': 'negative',
 'Would reccomend you carefely': 'mixed'}

# ------------------------------------------------------------------ build + verify
def norm(x): return re.sub(r"\s+", " ", x).strip()
def page_text(raw):
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    return norm(html.unescape(re.sub(r"<[^>]+>", " ", body)))

def right_place(h, title):
    """The page must be the hood's own place: its title carries one part of the hood name and, for towns, the state."""
    t = title.lower()
    parts = [p.strip().lower() for p in re.split(r"[-()]", h["name"]) if len(p.strip()) > 3]
    if not any(p in t for p in parts): return False
    return h["state"] == "NY" or f", {h['state'].lower()}" in t

def build():
    un = uncovered(); st = tried()
    r1_index = {}
    for l in open(lib.RAW / "voices_niche/_index.jsonl"):
        d = json.loads(l)
        if d.get("status") == 200: r1_index[d["url"]] = d
    qrows = []; srows = []; cov = []; pool = []
    themes = ["safety", "car_crime", "parking", "dogs_green", "social_life", "noise", "value", "people", "travel", "regret", "surprise", "other"]
    for h in un:
        hid = h["id"]; pages = []; worked = []; skipped = []
        for slug in NICHE.get(hid, []):
            s = st.get(niche_url(slug))
            if not s: continue
            if s.get("status") == 200: pages.append((niche_url(slug), s["path"], s["at"], None))
            elif s.get("status") == 404: skipped.append(f"niche: 404 for {slug}")
            else: skipped.append(f"niche: {s.get('note')} ({slug})")
        for url, label in CACHED_R1.get(hid, []):
            if url in r1_index: pages.append((url, r1_index[url]["path"], r1_index[url]["retrieved_at"], label))
        if hid in NICHE_NOT_RETRIED: skipped.append("niche: this place's review page answered HTTP 403 in round 1; not requested again")
        if not NICHE.get(hid) and hid not in CACHED_R1 and hid not in NICHE_NOT_RETRIED: skipped.append("niche: no place page (404 in round 1 or one unusable review)")
        if "www.niche.com" in killed() and not pages and NICHE.get(hid) and not any("niche" in x for x in skipped):
            skipped.append("niche: host refused earlier in this run (" + killed()["www.niche.com"]["why"] + "); not requested")
        cands = []
        for url, path, at, label in pages:
            raw = (lib.ROOT / path).read_text(encoding="utf8", errors="ignore")
            title, rating, count, revs = parse_niche(raw)
            area = label or re.sub(r" Reviews - Niche$", "", title)
            if not label and (not right_place(h, title) or "Reviews" not in title):
                skipped.append(f"niche: page '{title}' is not this place; dropped"); continue
            names = [h["name"], re.sub(r",.*| \(.*", "", area)]
            n0 = len(cands)
            for r in revs:
                r = dict(r, url=url, path=path, at=at, area=area)
                pool.append(dict(hood_id=hid, **r))
                cands += candidates(r, names)
            if rating:
                note = "" if not label else "enclosing/whole area page cached in round 1"
                srows.append(dict(hood_id=hid, neighborhood=h["name"], source_site="niche.com", measure="niche_overall_rating", value=rating, as_of=at[:10], source_url=url, source_area=area, note=note))
                srows.append(dict(hood_id=hid, neighborhood=h["name"], source_site="niche.com", measure="niche_review_count", value=count, as_of=at[:10], source_url=url, source_area=area, note=note))
            worked.append(f"niche ({area}: {len(revs)} reviews read" + ("; page cached in round 1, no new request" if label else "") + ")")
        cands = [c for c in cands if not any(d in c["ex"] for d in DROP)]
        for c in cands:
            for k, v in THEME_FIX.items():
                if c["ex"].startswith(k): c["theme"] = v
            for k, v in SENT_FIX.items():
                if c["ex"].startswith(k): c["sent"] = v
        mine = []
        for c in pick(cands):
            r = c["r"]
            mine.append(dict(hood_id=hid, neighborhood=h["name"], excerpt=c["ex"], theme=c["theme"], sentiment=c["sent"], speaker_context=c["ctx"],
                             source_site="niche.com", post_date=r["date"], permalink=r["url"], retrieved_at=r["at"], stars=r.get("rating") or "",
                             source_area=r["area"][:90], _path=r["path"], _post=None))
        for k in CITYDATA_KEEP:
            if k["hood_id"] != hid: continue
            s = st.get(k["url"])
            if not s or s.get("status") != 200: continue
            mine.append(dict(hood_id=hid, neighborhood=h["name"], excerpt=k["excerpt"], theme=k["theme"], sentiment=k["sentiment"], speaker_context=k["context"],
                             source_site="city-data.com/forum", post_date=k["date"], permalink=f"{k['url']}#post{k['post_id']}", retrieved_at=s["at"], stars="",
                             source_area=k.get("area", h["name"]), _path=s["path"], _post=k["post_id"]))
        # verify: re-read the cached page; the excerpt must be on it verbatim (whitespace-normalized), with a date
        kept = []
        for q in mine:
            raw = (lib.ROOT / q["_path"]).read_text(encoding="utf8", errors="ignore")
            hit = norm(q["excerpt"]) in page_text(raw) and bool(q["post_date"])
            if hit and q["_post"]: hit = f'id="post{q["_post"]}"' in raw or f'id="post_message_{q["_post"]}"' in raw
            if hit and re.search(BLOCK, q["excerpt"], re.I): hit = False
            if hit: q["verified"] = "yes"; kept.append(q)
            else: print("DROPPED (failed verification)", hid, q["excerpt"][:70])
        qrows += kept
        ncd = sum(1 for q in kept if q["source_site"].startswith("city-data"))
        if ncd: worked.append(f"city-data forum ({ncd} quotes, hand-picked)")
        else:
            cdt = [u for u in CITYDATA_THREADS.get(hid, []) if st.get(u, {}).get("status") == 200]
            if cdt: skipped.append(f"city-data: {len(cdt)} thread page(s) read, nothing usable about living there")
            elif "www.city-data.com" in killed() and CITYDATA_THREADS.get(hid): skipped.append("city-data: host refused in this run; stopped")
            else: skipped.append("city-data: no thread looked up (forum search is disallowed; threads were only looked for where Niche gave nothing)")
        skipped.append("trulia: not requested (blocking us)")
        c = collections.Counter(q["theme"] for q in kept)
        cov.append([hid, h["name"], h["drive_min"], len(kept)] + [c.get(t, 0) for t in themes] + [sum(1 for s in srows if s["hood_id"] == hid), " | ".join(worked), " | ".join(skipped)])
    QF = ["hood_id", "neighborhood", "excerpt", "theme", "sentiment", "speaker_context", "source_site", "post_date", "permalink", "retrieved_at", "stars", "source_area", "verified"]
    with open(OUT / "neighborhood_quotes_round2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, QF, extrasaction="ignore"); w.writeheader(); w.writerows(qrows)
    with open(OUT / "neighborhood_survey_round2.csv", "w", newline="") as f:
        w = csv.DictWriter(f, ["hood_id", "neighborhood", "source_site", "measure", "value", "as_of", "source_url", "source_area", "note"]); w.writeheader(); w.writerows(srows)
    with open(OUT / "coverage_round2.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["hood_id", "neighborhood", "drive_min", "quotes_total"] + [f"q_{t}" for t in themes] + ["survey_measures", "sources_worked", "sources_skipped"]); w.writerows(cov)
    with open(POOL, "w") as f:
        for r in pool: f.write(json.dumps(r) + "\n")
    got = {q["hood_id"] for q in qrows}
    print("uncovered", len(un), "| with quotes", len(got), "| quotes", len(qrows), "| survey rows", len(srows))
    print("themes", dict(collections.Counter(q["theme"] for q in qrows)))
    print("sources", dict(collections.Counter(q["source_site"] for q in qrows)))
    print("still none:", [h["id"] for h in un if h["id"] not in got])

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "targets"
    if cmd == "targets":
        for h in uncovered(): print(h["id"], "|", h["name"], "|", h["counts"]["shown"], "|", NICHE.get(h["id"]) or CACHED_R1.get(h["id"]) or "-")
    elif cmd == "niche": fetch_niche()
    elif cmd == "citydata": fetch_citydata()
    elif cmd == "build": build()
