"""Round 2 of the outside descriptions: quotes that convey the CHARACTER of each neighborhood.

Round 1 (scripts/neighborhood_descriptions.py, not edited) quoted Wikipedia lead sentences. This
pass reads (1) the BODY of the same Wikipedia articles, from the same cached database-dump blocks
(raw/big/neighborhood_descriptions/stream_*.bz2; en.wikipedia.org itself is ended for the session
and is never called), plus a few articles about a town's downtown or a Jersey City neighborhood,
and (2) official pages (municipality, county, tourism board, parks department, improvement
district, transit agency), each read once through lib.cached_get after its robots.txt.

Stages (each resumable and idempotent; `all` runs them in order and refetches nothing cached):
  bodies      resolve extra titles in the cached dump index, Range-fetch any dump block not yet
              cached, write the full wikitext of every article to raw/.../bodies/*.json
  candidates  wikitext -> plain sentences per section, flagged (template-damaged, banned topic,
              long, short), with a keyword score; writes candidates.json and shortlist.txt
  web         fetch the pages in web_plan.json (robots.txt first; caps: 2 pages per neighborhood,
              220 in total; one refusal ends a host, persisted in _host_kill.json AND
              raw/_host_kill_shared.json), write their plain text to web_text/
  compile     hand files (picks_wiki.txt, picks_web.json, landmarks.txt, summaries.txt) -> curation.json
  write       read curation.json (quote, character 1-3, topic, landmarks, summary), re-verify every
              quote word for word against the cached text, write the CSVs

Outputs: data/reference/neighborhood_descriptions_round2.csv,
         data/reference/neighborhood_summaries_round2.csv
"""
from __future__ import annotations

import bz2
import csv
import hashlib
import html
import json
import os
import re
import sys
import urllib.robotparser
from pathlib import Path
from urllib.parse import quote as urlquote, urlparse

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
import neighborhood_descriptions as r1  # noqa: E402  (read-only reuse: HOODS, index scan, sentence split)
from lib import RAW, ROOT, USER_AGENT, now_iso  # noqa: E402

SRC = "neighborhood_descriptions_round2"
D = RAW / SRC
BODIES = D / "bodies"
WEBTEXT = D / "web_text"
KILL_PATH = D / "_host_kill.json"
SHARED_KILL = RAW / "_host_kill_shared.json"
RESOLVED = D / "resolved_titles.json"
CAND = D / "candidates.json"
SHORT = D / "shortlist.txt"
CURATION = D / "curation.json"
WEB_PLAN = D / "web_plan.json"
WEB_LOG = D / "web_fetches.jsonl"
ROBOTS = D / "robots"
OUT_Q = ROOT / "data" / "reference" / "neighborhood_descriptions_round2.csv"
OUT_S = ROOT / "data" / "reference" / "neighborhood_summaries_round2.csv"

MAX_WORDS = 35
MAX_PAGES_PER_HOOD = 2
MAX_PAGES_TOTAL = 220
MARK = r1.MARK
TOPICS = {"main street", "food and nightlife", "parks", "waterfront", "housing feel", "transit",
          "landmark", "event", "history"}
SCOPES = {"exact", "enclosing", "part"}
OFF_LIMITS = re.compile(r"(wikipedia\.org|reddit\.com|yelp\.com|nextdoor\.com|patch\.com|qns\.com|niche\.com|"
                        r"zillow\.com|trulia\.com|streeteasy\.com|apartments\.com)$", re.I)
CLAUDE_AGENTS = ("ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai")
WALL = re.compile(r"captcha|just a moment\.\.\.|cf-challenge|challenge-platform|access denied|are you a robot|"
                  r"unusual traffic|incapsula|attention required|verify you are human|px-captcha", re.I)

# ---------------------------------------------------------------- neighborhoods and their articles
JC = "https://en.wikipedia.org/wiki/Jersey_City,_New_Jersey"
JC_HOODS = {  # id -> (name, [(title, about_area, scope)])
    "nj:jersey-city-downtown": ("Jersey City – Downtown", [("Downtown Jersey City", "Downtown Jersey City", "exact")]),
    "nj:jersey-city-journal-square": ("Jersey City – Journal Square", [("Journal Square", "Journal Square", "exact")]),
    "nj:jersey-city-the-heights": ("Jersey City – The Heights",
                                   [("The Heights, Jersey City", "The Heights", "exact")]),
    "nj:jersey-city-bergen-lafayette": ("Jersey City – Bergen-Lafayette",
                                        [("Bergen-Lafayette, Jersey City", "Bergen-Lafayette", "exact")]),
    "nj:jersey-city-west-side": ("Jersey City – West Side", [("West Side, Jersey City", "West Side", "exact")]),
    "nj:jersey-city-greenville": ("Jersey City – Greenville",
                                  [("Greenville, Jersey City", "Greenville", "exact")]),
    "nj:jersey-city-mcginley-square": ("Jersey City – McGinley Square",
                                       [("McGinley Square", "McGinley Square", "exact")]),
    "nj:jersey-city-newport": ("Jersey City – Newport", [("Newport, Jersey City", "Newport", "exact")]),
}
# Articles about a district, park or station INSIDE a neighborhood (scope = part: the quote is
# about one part of the place, named in about_area). Only titles found in the dump are used.
EXTRA: dict[str, list[tuple[str, str, str]]] = {
    "ct:stamford": [("Downtown Stamford", "Downtown Stamford", "part"),
                    ("Harbor Point (Stamford)", "Harbor Point", "part"),
                    ("Mill River Park", "Mill River Park", "part")],
    "ct:norwalk": [("South Norwalk", "South Norwalk", "part")],
    "nj:newark": [("Downtown Newark", "Downtown Newark", "part"), ("Ironbound", "Ironbound", "part"),
                  ("Branch Brook Park", "Branch Brook Park", "part")],
    "nj:bayonne": [("Bergen Point", "Bergen Point", "part")],
    "ny:new-rochelle": [("Downtown New Rochelle", "Downtown New Rochelle", "part")],
    "ny:yonkers": [("Getty Square", "Getty Square", "part"), ("Downtown Yonkers", "Downtown Yonkers", "part")],
    "ct:danbury": [("Downtown Danbury", "Downtown Danbury", "part"),
                   ("Main Street Historic District (Danbury, Connecticut)", "Main Street, Danbury", "part")],
    "ct:bridgeport": [("Downtown Bridgeport", "Downtown Bridgeport", "part"),
                      ("Black Rock, Bridgeport", "Black Rock", "part"),
                      ("Seaside Park (Connecticut)", "Seaside Park", "part")],
    "ct:milford-city-balance-": [("Walnut Beach", "Walnut Beach", "part"),
                                 ("Silver Sands State Park", "Silver Sands State Park", "part")],
    "nj:jersey-city": [("Downtown Jersey City", "Downtown Jersey City", "part"),
                       ("Journal Square", "Journal Square", "part"),
                       ("Liberty State Park", "Liberty State Park", "part")],
    "nj:jersey-city-downtown": [("Paulus Hook", "Paulus Hook", "part"),
                                ("Hamilton Park, Jersey City", "Hamilton Park", "part"),
                                ("Van Vorst Park", "Van Vorst Park", "part"),
                                ("Exchange Place (Jersey City)", "Exchange Place", "part"),
                                ("Grove Street (Jersey City)", "Grove Street", "part")],
    "nj:jersey-city-bergen-lafayette": [("Bergen-Lafayette", "Bergen-Lafayette", "exact"),
                                        ("Liberty State Park", "Liberty State Park", "enclosing"),
                                        ("Berry Lane Park", "Berry Lane Park", "part")],
    "nj:jersey-city-west-side": [("Lincoln Park (Jersey City)", "Lincoln Park", "part"),
                                 ("West Side Avenue", "West Side Avenue", "part"),
                                 ("West Side (Jersey City)", "West Side", "exact")],
    "nj:jersey-city-the-heights": [("Jersey City Heights", "The Heights", "exact"),
                                   ("Riverview-Fisk Park", "Riverview-Fisk Park", "part"),
                                   ("Central Avenue (Hudson Palisades)", "Central Avenue", "part"),
                                   ("Pershing Field", "Pershing Field", "part")],
    "nj:jersey-city-greenville": [("Greenville (Jersey City)", "Greenville", "exact")],
    "nj:jersey-city-newport": [("Newport (Jersey City)", "Newport", "exact"),
                               ("Hudson River Waterfront Walkway", "Hudson River Waterfront Walkway", "enclosing")],
    "nj:jersey-city-mcginley-square": [("McGinley Square, Jersey City", "McGinley Square", "exact"),
                                       ("Bergen Square", "Bergen Square", "enclosing")],
    "nj:jersey-city-journal-square": [("Loew's Jersey Theatre", "Loew's Jersey Theatre", "part"),
                                      ("India Square", "India Square", "part")],
    "nj:hackensack": [("Main Street (Hackensack, New Jersey)", "Main Street, Hackensack", "part")],
    "nj:harrison": [("Harrison station (PATH)", "Harrison PATH station", "part")],
    "nj:new-brunswick": [("Downtown New Brunswick", "Downtown New Brunswick", "part")],
    "ny:white-plains": [("Downtown White Plains", "Downtown White Plains", "part")],
    "ny:jamaica": [("Downtown Jamaica", "Downtown Jamaica", "part")],
    "ny:jamaica-hills-briarwood": [("Jamaica Hills", "Jamaica Hills", "exact")],
    "ny:patchogue": [("Patchogue, New York", "Patchogue", "exact")],
    "ny:haverstraw": [("Haverstraw Bay", "Haverstraw Bay", "enclosing")],
    "ny:old-astoria-hallets-point": [("Astoria Park", "Astoria Park", "part")],
    "ny:east-flatbush-erasmus": [("Erasmus, Brooklyn", "Erasmus", "exact")],
    "ny:bath-beach": [("Bensonhurst Park", "Bensonhurst Park", "part")],
    "ny:prospect-lefferts-gardens-wingate": [("Prospect Park (Brooklyn)", "Prospect Park", "enclosing")],
    "ny:washington-heights-south-": [("Highbridge Park", "Highbridge Park", "part")],
    "ny:washington-heights-north-": [("Fort Tryon Park", "Fort Tryon Park", "part")],
    "ny:inwood": [("Inwood Hill Park", "Inwood Hill Park", "part")],
    "ny:forest-hills": [("Forest Hills Gardens, Queens", "Forest Hills Gardens", "part")],
    "ny:st-george-new-brighton": [("St. George Terminal", "St. George Terminal", "part")],
    "ny:long-beach": [("Long Beach Boardwalk", "Long Beach Boardwalk", "part")],
    "ct:shelton": [("Downtown Shelton", "Downtown Shelton", "part")],
    "nj:montclair": [("Upper Montclair, New Jersey", "Upper Montclair", "part")],
    "nj:city-of-orange": [("Orange station (NJ Transit)", "Orange station", "part")],
    "ny:port-chester": [("Capitol Theatre (Port Chester, New York)", "Capitol Theatre", "part")],
    "ny:peekskill": [("Paramount Hudson Valley Theater", "Paramount Hudson Valley Theater", "part")],
}


def articles() -> dict[str, list[tuple[str, str, str]]]:
    out = {k: list(v) for k, v in r1.HOODS.items()}
    for hid, (_, arts) in JC_HOODS.items():
        out[hid] = list(arts) + [("Jersey City, New Jersey", "Jersey City", "enclosing")]
    for hid, arts in EXTRA.items():
        out.setdefault(hid, [])
        out[hid] += [a for a in arts if a[0] not in {t for t, _, _ in out[hid]}]
    return out


def hood_list() -> dict[str, str]:
    """Union of site/data.json, round 1's remembered ids and the eight Jersey City pieces,
    most shown places first. Reads round 1's files; writes nothing there."""
    u, shown = {}, {}
    for n in json.loads((ROOT / "site" / "data.json").read_text())["neighborhoods"]:
        u[n["id"]] = n["name"]
        shown[n["id"]] = n.get("counts", {}).get("shown", 0)
    seen = json.loads((RAW / "neighborhood_descriptions" / "hood_names.json").read_text())
    for k, v in seen.items():
        u.setdefault(k, v)
    with open(ROOT / "data" / "reference" / "neighborhood_descriptions.csv") as f:
        for r in csv.DictReader(f):
            u.setdefault(r["hood_id"], r["hood_name"])
    for hid, (name, _) in JC_HOODS.items():
        u.setdefault(hid, name)
        shown.setdefault(hid, shown.get("nj:jersey-city", 0))
    mine = D / "hood_names.json"
    old = json.loads(mine.read_text()) if mine.exists() else {}
    old.update(u)
    D.mkdir(parents=True, exist_ok=True)
    mine.write_text(json.dumps(old, indent=1, ensure_ascii=False, sort_keys=True))
    return dict(sorted(old.items(), key=lambda kv: (-shown.get(kv[0], 0), kv[0])))


# ---------------------------------------------------------------- host kill flags (two files on disk)

def load_kill() -> dict:
    out = {}
    for p in (RAW / "neighborhood_descriptions" / "_host_kill.json", SHARED_KILL, KILL_PATH):
        try:
            d = json.loads(p.read_text() or "{}")
            if isinstance(d, dict):
                out.update(d)
        except (OSError, json.JSONDecodeError):
            pass
    return out


def killed(host: str) -> bool:
    host = host.lower()
    bare = host[4:] if host.startswith("www.") else host
    return any(k.lower() in (host, bare, "www." + bare) for k in load_kill())


def kill_host(host: str, why: str, url: str = "") -> None:
    rec = {"reason": why, "status": why, "at": now_iso(), "time": now_iso(), "url": url,
           "by": "scripts/neighborhood_descriptions_round2.py"}
    for p in (KILL_PATH, SHARED_KILL):
        try:
            d = json.loads(p.read_text() or "{}") if p.exists() else {}
        except json.JSONDecodeError:
            d = {}
        if host not in d:
            d[host] = rec
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".json.tmp%d" % os.getpid())
            tmp.write_text(json.dumps(d, indent=1) + "\n")
            os.replace(tmp, p)
    print(f"HOST ENDED: {host}: {why}")


def log(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- stage: bodies

def body_path(title: str) -> Path:
    return BODIES / (re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_") + ".json")


def fetch_stream(offset: int, end: int) -> bytes:
    """A dump block: from round 1's cache when present, else one Range request to the dump host."""
    p = r1.BIG / f"stream_{offset}.bz2"
    if p.exists():
        return p.read_bytes()
    if killed(r1.DUMP_HOST):
        raise SystemExit("dump host is ended for this session")
    lib.HOST_DELAY.setdefault(r1.DUMP_HOST, 2.0)
    lib._throttle(r1.DUMP_HOST)
    rng = f"bytes={offset}-{end - 1}"
    r = requests.get(r1.DUMP_URL, headers={"User-Agent": USER_AGENT, "Range": rng}, timeout=180)
    log(D / "_index.jsonl", {"url": r1.DUMP_URL, "range": rng, "retrieved_at": now_iso(),
                             "status": r.status_code, "path": str(p.relative_to(ROOT)), "source": SRC})
    if r.status_code in (401, 403, 429):
        kill_host(r1.DUMP_HOST, f"HTTP {r.status_code} on a range request", r1.DUMP_URL)
        raise SystemExit(f"refused: HTTP {r.status_code}")
    if r.status_code != 206:
        raise RuntimeError(f"expected 206, got {r.status_code}")
    p.write_bytes(r.content)
    return r.content


def all_titles() -> list[str]:
    seen = []
    for arts in articles().values():
        for t, _, _ in arts:
            if t not in seen:
                seen.append(t)
    return seen


def stage_bodies() -> None:
    BODIES.mkdir(parents=True, exist_ok=True)
    res = json.loads(RESOLVED.read_text()) if RESOLVED.exists() else \
        json.loads((RAW / "neighborhood_descriptions" / "resolved_titles.json").read_text())
    for _ in range(4):
        todo = {t for t in all_titles() if t not in res}
        todo |= {v["redirect_to"] for v in res.values() if v.get("redirect_to") and v["redirect_to"] not in res}
        if todo:
            found = r1.scan_index(todo)  # reads the cached 286 MB index; no network
            for t in todo:
                res[t] = found.get(t) or {"missing": True}
            RESOLVED.write_text(json.dumps(res, indent=1, ensure_ascii=False))
            print(f"index: resolved {len(found)} of {len(todo)}; missing {sorted(t for t in todo if t not in found)}")
        again = False
        for title, info in list(res.items()):
            if info.get("missing") or info.get("redirect_to") or body_path(title).exists():
                continue
            xml = bz2.decompress(fetch_stream(info["offset"], info["end"])).decode("utf-8")
            pg = r1.extract_page(xml, title)
            if pg is None:
                info["missing"] = True
            elif pg["redirect_to"]:
                info["redirect_to"] = pg["redirect_to"]
                again = again or pg["redirect_to"] not in res
            else:
                body_path(title).write_text(json.dumps({
                    "title": title, "revision_id": pg["rev"], "revision_timestamp": pg["ts"],
                    "dump": r1.DUMP_DATE, "dump_url": r1.DUMP_URL,
                    "byte_range": [info["offset"], info["end"] - 1], "retrieved_at": now_iso(),
                    "wikitext": pg["text"]}, indent=1, ensure_ascii=False))
            RESOLVED.write_text(json.dumps(res, indent=1, ensure_ascii=False))
        if not again and not ({t for t in all_titles() if t not in res}):
            break
    print(f"bodies: {len(list(BODIES.glob('*.json')))} articles cached")


def final_title(title: str, res: dict) -> str | None:
    return r1.final_title(title, res)


# ---------------------------------------------------------------- wikitext -> plain sentences
# Stricter than round 1: a template is rendered only when its visible output is exactly known
# (dash, space, nowrap text); dropped silently only when it shows nothing inline (references,
# maintenance tags, hatnotes on their own line). EVERYTHING else leaves a mark, and a marked
# sentence is never quoted.
SAFE_TPL = {"nbsp": " ", "snd": " – ", "spnd": " – ", "spaced ndash": " – ", "spaced en dash": " – ",
            "ndash": "–", "en dash": "–", "mdash": "—", "emdash": "—", "em dash": "—", "'": "'", "'s": "'s"}
SILENT_EXACT = {"citation needed", "cn", "fact", "clarify", "when", "by whom", "who", "which", "where",
                "dubious", "better source needed", "better source", "failed verification", "update inline",
                "page needed", "full citation needed", "dead link", "efn", "sfn", "sfnp", "r", "rp", "refn",
                "ref", "main", "see also", "further", "main article", "clear", "-", "clear left",
                "clear right", "toc limit", "reflist", "notelist", "authority control", "portal",
                "commons category", "commons", "wikivoyage", "wiktionary", "short description",
                "use mdy dates", "use dmy dates", "use american english", "good article", "featured article",
                "citation", "specify", "vague", "according to whom", "original research inline",
                "unreliable source?", "unreliable source", "additional citation needed", "obsolete source",
                "verify source", "self-published inline", "third-party inline", "primary source inline",
                "more citations needed section", "unreferenced section", "more citations needed",
                "refimprove section", "refimprove", "unreferenced", "update", "update section",
                "expand section", "empty section", "cleanup", "tone", "advert", "prose", "original research",
                "multiple issues", "coord", "anchor", "defaultsort", "stack", "stack begin", "stack end",
                "div col", "div col end", "col-begin", "col-end", "col-break", "listen", "external media"}
SILENT_PREFIX = re.compile(r"^(infobox|cite |cite\b|about$|for$|for-multi|other uses|redirect|distinguish|"
                           r"hatnote|pp-|pp$|webarchive|wide image|multiple image|image frame|location map|"
                           r"maplink|navbox|nrhp|weather box|us census population|historical populations|"
                           r"bar box|pie chart|climate chart|gallery|panorama|geographic location|"
                           r"attached kml|adjacent communities|routemap|s-|succession|start box|end box)", re.I)


def clean_wikitext(w: str) -> str:
    w = re.sub(r"<!--.*?-->", "", w, flags=re.S)
    w = re.sub(r"<ref[^>]*?/>", "", w, flags=re.S)
    w = re.sub(r"<ref[^>]*?>.*?</ref>", "", w, flags=re.S)
    w = re.sub(r"<(gallery|imagemap|timeline|math|score|mapframe|graph|chem)[^>]*?>.*?</\1>", MARK, w,
               flags=re.S | re.I)
    w = re.sub(r"<(nowiki|pre|code|syntaxhighlight|blockquote|poem)[^>]*?>.*?</\1>", MARK, w, flags=re.S | re.I)
    w = re.sub(r"<(sub|sup|small|big|s|del|ins)\b[^>]*>.*?</\1>", MARK, w, flags=re.S | re.I)
    for _ in range(6):  # tables (may hold templates)
        w2 = re.sub(r"\{\|(?:(?!\{\||\|\}).)*\|\}", "", w, flags=re.S)
        if w2 == w:
            break
        w = w2

    def tpl(m: re.Match) -> str:
        body = m.group(1)
        name = re.sub(r"\s+", " ", body.split("|", 1)[0].strip().lower().replace("_", " "))
        if name in SAFE_TPL:
            return SAFE_TPL[name]
        if name in ("nowrap", "nobr", "nobreak") and body.count("|") == 1 and "=" not in body:
            return body.split("|", 1)[1]
        if name in SILENT_EXACT or SILENT_PREFIX.match(name):
            return ""
        return MARK
    for _ in range(40):  # innermost templates first
        w2 = re.sub(r"\{\{((?:(?!\{\{|\}\}).)*)\}\}", tpl, w, flags=re.S)
        if w2 == w:
            break
        w = w2
    for _ in range(10):  # files / images / categories (may nest links)
        w2 = re.sub(r"\[\[(?:File|Image|Category):(?:(?!\[\[|\]\]).|\[\[(?:(?!\[\[|\]\]).)*\]\])*\]\]", "", w,
                    flags=re.S | re.I)
        if w2 == w:
            break
        w = w2
    w = re.sub(r"\[\[(?:[^\[\]|]*\|)?([^\[\]|]*)\]\]", r"\1", w)
    w = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", w)
    w = re.sub(r"\[https?://\S+\]", MARK, w)
    w = re.sub(r"'{2,5}", "", w)
    w = re.sub(r"<br\s*/?>", " ", w, flags=re.I)
    w = re.sub(r"</?[a-zA-Z][^>]*>", "", w)
    w = html.unescape(w).replace(" ", " ")
    # anything that still looks like markup is damage
    w = re.sub(r"\{\{|\}\}|\[\[|\]\]|\{\||\|\}|__[A-Z]+__", MARK, w)
    paras = []
    for line in w.split("\n"):
        s = line.strip()
        if s[:1] in "*#":  # a list item: kept as its own paragraph (quotable only if a whole sentence)
            s = s.lstrip("*#: ").strip()
        if not s or s.strip(MARK + " ") == "" or s[0] in ":;|!{}":
            continue
        paras.append(re.sub(r"[ \t]+", " ", s))
    return "\n".join(paras)


SKIP_SECTION = re.compile(r"demograph|census|government|politic|education|schools|notable|references|see also|"
                          r"external links|further reading|notes|crime|police|fire|public safety|climate|"
                          r"media|in popular culture|sister cit|representation|elections|religio|houses of "
                          r"worship|ethnic|population|emergency|health|post office|zip|librar|bibliography|"
                          r"sources|footnotes|citations", re.I)
HIST_SECTION = re.compile(r"histor|etymolog|name|founding|settlement|centur|colonial|early|development|"
                          r"origins|toponym", re.I)

BAN = re.compile(r1.BAN.pattern + r"|\b(hispanics?|latinos?|blacks|whites|asians|jewry|synagogue|mosque|church|"
                 r"churches|parish|congregation|temple|koreans?|italians?|irish|greeks?|russians?|poles|"
                 r"dominicans?|haitians?|filipinos?|indians?|portuguese|brazilian|peruvian|cuban|japanese|"
                 r"armenian|lebanese|working[- ]class|middle[- ]class|upper[- ]class|blue[- ]collar|upscale|"
                 r"wealthy|wealthiest|exclusive|gentrif|slum|blight|ghetto|homeless|arrest|robber|burglar|"
                 r"killed|shot|rape|prostitut|housing projects?|public housing|inhabitants|households|"
                 r"median|per square mile|density|percent|%)\b"
                 r"|\b(immigra|ethnic|gentrif|segregat|demograph|prostitut|robber|burglar|racial|divers|"
                 r"minorit|impoverish|affluen|mafia|murder|homicid)\w*", re.I)

KEY = [  # (weight, pattern) for the shortlist only: curation is by hand
    (3, r"\b(downtown|main street|shopping district|commercial (strip|corridor|district|center)|"
        r"restaurants?|bars?|nightlife|cafes?|cafés|shops|boutiques|dining|eateries|pubs?)\b"),
    (3, r"\b(parks?|beach(es)?|boardwalk|waterfront|promenade|marina|harbor|trails?|greenway|esplanade|"
        r"riverwalk|shore|pier|lake|gardens?|preserve|reservation|playground|dog run|dog park)\b"),
    (2, r"\b(known for|noted for|famous for|renowned|home to|features?|lined with|characterized|consists of|"
        r"popular|destination|vibrant|lively|bustling|quiet|tree-lined|leafy|suburban|walkable)\b"),
    (2, r"\b(victorian|brownstones?|row ?houses?|tudor|colonial revival|art deco|architecture|historic district|"
        r"apartment buildings?|high-rises?|single-family|bungalows?|mansions?|garden apartments?|cottages)\b"),
    (2, r"\b(station|ferry|ferries|path|metro-north|lirr|long island rail road|nj transit|light rail|subway|"
        r"express|terminal)\b"),
    (2, r"\b(festival|annual|annually|parade|farmers'? market|concerts?|theat(er|re)s?|museum|gallery|galleries|"
        r"arts|music|venue|landmark|lighthouse|zoo|aquarium|stadium|arena)\b"),
    (1, r"\b(is|are|has|have|offers?|includes?|runs|serves|hosts|contains|overlooks)\b"),
]
KEY = [(w, re.compile(p, re.I)) for w, p in KEY]
PAST = re.compile(r"\b(was|were|had|became|began|built in|opened in|established|founded|settled|purchased|"
                  r"incorporated|in 1[5-9]\d\d|in 20[01]\d|during the)\b", re.I)


def split_sections(text: str) -> list[tuple[str, str]]:
    """[(section path, paragraph)] with the lead called 'Lead'."""
    out, path = [], ["Lead"]
    for line in text.split("\n"):
        m = re.match(r"^(={2,6})\s*(.*?)\s*=+\s*$", line)
        if m:
            lvl = len(m.group(1)) - 1
            path = path[:lvl - 1] if lvl > 1 else []
            while len(path) < lvl - 1:
                path.append("")
            path.append(m.group(2).replace(MARK, "").strip())
            continue
        out.append((" > ".join(p for p in path if p) or "Lead", line))
    return out


def article_sentences(title: str) -> list[dict]:
    body = json.loads(body_path(title).read_text())
    sents = []
    for sec, par in split_sections(clean_wikitext(body["wikitext"])):
        skip = bool(SKIP_SECTION.search(sec))
        hist = bool(HIST_SECTION.search(sec))
        for s in r1.sentences(par):
            s = r1.norm(s)
            n = len(s.split())
            flag = ("template" if MARK in s else "banned_topic" if BAN.search(s) else "long" if n > MAX_WORDS
                    else "short" if n < 6 else "no_end" if not re.search(r"[.!?][\"”')]?$", s)
                    else "fragment" if not re.match(r"[\"“A-Z0-9]", s) else "")
            score = sum(w for w, p in KEY if p.search(s)) - (2 if PAST.search(s) else 0) - (2 if hist else 0)
            sents.append({"i": len(sents), "section": sec, "skip_section": skip, "history_section": hist,
                          "words": n, "flag": flag, "score": score, "text": s})
    return sents


def stage_candidates() -> None:
    res = json.loads(RESOLVED.read_text())
    out, lines = {}, []
    cache: dict[str, list] = {}
    for title in all_titles():
        ft = final_title(title, res)
        if not ft or not body_path(ft).exists():
            out[title] = {"missing": True}
            continue
        if ft not in cache:
            cache[ft] = article_sentences(ft)
        out[title] = {"article": ft, "revision_id": json.loads(body_path(ft).read_text())["revision_id"],
                      "sentences": cache[ft]}
    CAND.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    hoods, arts = hood_list(), articles()
    topn = int(os.environ.get("SHORTLIST_N", "12"))
    for hid, name in hoods.items():
        lines.append(f"\n### {hid} | {name}")
        done = set()
        for title, about, scope in arts.get(hid, []):
            c = out.get(title, {})
            if c.get("article") in done:
                continue
            done.add(c.get("article"))
            if c.get("missing"):
                lines.append(f"## {title}: MISSING")
                continue
            ok = [s for s in c["sentences"] if not s["flag"] and not s["skip_section"]]
            if scope == "enclosing" and hid in JC_HOODS:
                key = JC_HOODS[hid][0].split(" – ")[1].replace("The ", "")
                ok = [s for s in ok if key.lower() in s["text"].lower()]
            ok.sort(key=lambda s: -s["score"])
            n = topn if scope == "exact" else max(4, topn // 2)
            lines.append(f"## {title} [{scope}; {about}] usable={len(ok)}")
            for s in sorted(ok[:n], key=lambda s: s["i"]):
                lines.append(f"{s['i']}|{s['section'][:28]}| {s['text']}")
    SHORT.write_text("\n".join(lines))
    ok = sum(1 for v in out.values() if not v.get("missing"))
    print(f"candidates: {ok} articles, {len(out) - ok} missing; shortlist {SHORT}")


# ---------------------------------------------------------------- stage: web (official pages)

def robots_allows(url: str) -> tuple[bool, str, float]:
    """(allowed, which group decided, crawl delay). Groups naming Claude apply to us and override *."""
    u = urlparse(url)
    host = u.netloc
    ROBOTS.mkdir(parents=True, exist_ok=True)
    p = ROBOTS / (re.sub(r"[^A-Za-z0-9.-]", "_", host) + ".txt")
    sp = p.with_suffix(".status")
    if not p.exists():
        lib._throttle(host)
        try:
            r = requests.get(f"{u.scheme}://{host}/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=30)
        except requests.RequestException as e:
            log(WEB_LOG, {"kind": "robots", "host": host, "error": repr(e)[:200], "at": now_iso()})
            return False, f"robots.txt unreachable ({type(e).__name__})", 0
        log(WEB_LOG, {"kind": "robots", "host": host, "status": r.status_code, "at": now_iso(),
                      "final_url": r.url})
        if r.status_code in (401, 403, 429) or (r.status_code == 200 and WALL.search(r.text[:3000])
                                                 and "user-agent" not in r.text.lower()):
            kill_host(host, f"HTTP {r.status_code} on robots.txt", r.url)
            return False, "refused", 0
        if r.status_code >= 500:
            return False, f"robots.txt HTTP {r.status_code}", 0
        body = r.text if (r.status_code == 200 and "<html" not in r.text[:500].lower()) else ""
        p.write_text(body)
        sp.write_text(str(r.status_code))
    txt = p.read_text()
    named = [a for a in CLAUDE_AGENTS if re.search(r"(?im)^\s*user-agent\s*:\s*" + re.escape(a) + r"\s*$", txt)]
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(txt.splitlines())
    agents = named or ["*"]
    allowed = all(rp.can_fetch(a, url) for a in agents)
    delay = max([float(rp.crawl_delay(a) or 0) for a in agents] + [0.0])
    return allowed, ("groups naming " + ",".join(named)) if named else "group *", delay


def page_text(raw: bytes) -> str:
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"<(script|style|noscript|svg|template)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    t = re.sub(r"</(p|div|h[1-6]|li|section|article|td|th|tr|ul|ol|header|footer|nav|figcaption|blockquote)>|"
               r"<br\s*/?>", " ¶ ", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", t)).replace(" ", " ")
    t = t.replace("’", "’")
    return re.sub(r"(\s*¶\s*)+", " ¶ ", re.sub(r"[ \t\r\n]+", " ", t)).strip()


def web_text_path(url: str) -> Path:
    return WEBTEXT / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt")


def web_counts() -> tuple[int, dict[str, int]]:
    total, per = 0, {}
    if WEB_LOG.exists():
        for line in WEB_LOG.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "page" and r.get("sent"):
                total += 1
                per[r["hood_id"]] = per.get(r["hood_id"], 0) + 1
    return total, per


def fetch_page(hid: str, url: str) -> str:
    """Returns 'ok', or the reason nothing was read. Never retries, never works around a refusal."""
    host = urlparse(url).netloc
    if OFF_LIMITS.search(host):
        return "off-limits host"
    if web_text_path(url).exists():
        return "ok"
    if killed(host):
        return "host ended"
    total, per = web_counts()
    if total >= MAX_PAGES_TOTAL:
        return "total cap reached"
    if per.get(hid, 0) >= MAX_PAGES_PER_HOOD:
        return "per-neighborhood cap reached"
    allowed, group, delay = robots_allows(url)
    if not allowed:
        log(WEB_LOG, {"kind": "page", "sent": False, "hood_id": hid, "url": url, "why": f"robots: {group}",
                      "at": now_iso()})
        return f"robots: {group}"
    if delay:
        lib.HOST_DELAY[host] = max(lib.HOST_DELAY.get(host, lib.DEFAULT_DELAY), min(delay, 30))
    try:
        raw, meta = lib.cached_get(url, SRC, ext="html", retries=1, timeout=40)
    except RuntimeError as e:
        why = str(e)[-120:]
        log(WEB_LOG, {"kind": "page", "sent": True, "hood_id": hid, "url": url, "status": why, "at": now_iso()})
        if "HTTP 429" in why:
            kill_host(host, "HTTP 429", url)
            return "refused: HTTP 429"
        return "failed: " + why
    log(WEB_LOG, {"kind": "page", "sent": True, "hood_id": hid, "url": url, "status": meta["status"],
                  "at": meta["retrieved_at"], "robots": group})
    if meta["status"] in (401, 403, 429):
        kill_host(host, f"HTTP {meta['status']}", url)
        return f"refused: HTTP {meta['status']}"
    if meta["status"] != 200:
        return f"HTTP {meta['status']}"
    text = page_text(raw)
    if len(text) < 3000 and WALL.search(text):
        kill_host(host, "bot wall / CAPTCHA page", url)
        return "refused: wall"
    WEBTEXT.mkdir(parents=True, exist_ok=True)
    web_text_path(url).write_text(json.dumps({"url": url, "retrieved_at": meta["retrieved_at"],
                                              "raw_path": meta["path"], "text": text}, ensure_ascii=False))
    return "ok"


def stage_web(only: list[str] | None = None) -> None:
    plan = json.loads(WEB_PLAN.read_text()) if WEB_PLAN.exists() else []
    for item in plan:
        if only and item["url"] not in only and item["hood_id"] not in only:
            continue
        had = web_text_path(item["url"]).exists()
        res = fetch_page(item["hood_id"], item["url"])
        if not had or res != "ok":
            n = len(json.loads(web_text_path(item["url"]).read_text())["text"]) if res == "ok" else 0
            print(f"web: {item['hood_id']} {item['url']} -> {res} ({n} chars)")
    total, per = web_counts()
    print(f"web: {total} page requests sent so far (cap {MAX_PAGES_TOTAL})")


# ---------------------------------------------------------------- stage: compile (hand files -> curation.json)
# Hand inputs, all in raw/neighborhood_descriptions_round2/:
#   picks_wiki.txt   hood_id|article title|sentence index (a+b = two consecutive)|character|topic[|force]
#   picks_web.json   [{hood_id, web_url, quote, source_name, about_area, scope, character, topic}]
#   landmarks.txt    hood_id|name|kind
#   summaries.txt    hood_id|plain summary (25 words or fewer, restating only what the quotes say)

def stage_compile() -> None:
    cand = json.loads(CAND.read_text())
    cur: dict[str, dict] = {}
    for line in (D / "picks_wiki.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split("|")
        hid, title, idx, ch, topic = f[:5]
        ss = [cand[title]["sentences"][int(i)] for i in idx.split("+")]
        pick = {"title": title, "quote": " ".join(x["text"] for x in ss), "character": int(ch), "topic": topic}
        if len(f) > 5 and f[5] == "force":
            pick["force"] = True
        cur.setdefault(hid, {"quotes": [], "landmarks": []})["quotes"].append(pick)
    wp = D / "picks_web.json"
    for pick in (json.loads(wp.read_text()) if wp.exists() else []):
        pick = dict(pick)
        cur.setdefault(pick.pop("hood_id"), {"quotes": [], "landmarks": []})["quotes"].append(pick)
    for name, key in (("landmarks.txt", "landmarks"), ("summaries.txt", "plain_summary")):
        fp = D / name
        for line in (fp.read_text().splitlines() if fp.exists() else []):
            if not line.strip() or line.startswith("#"):
                continue
            f = line.split("|")
            c = cur.setdefault(f[0], {"quotes": [], "landmarks": []})
            if key == "landmarks":
                c["landmarks"].append({"name": f[1], "kind": f[2]})
            else:
                c[key] = f[1]
    CURATION.write_text(json.dumps(cur, indent=1, ensure_ascii=False))
    print(f"compile: {sum(len(c['quotes']) for c in cur.values())} picks for {len(cur)} neighborhoods")


# ---------------------------------------------------------------- stage: write

def wiki_url(art: str) -> str:
    return "https://en.wikipedia.org/wiki/" + urlquote(art.replace(" ", "_"), safe=",()_-.'")


def verify_wiki(quote: str, art: str, force: bool) -> str:
    """'' when the quote is one whole undamaged sentence (or two consecutive) of the cached article."""
    ss = article_sentences(art)
    q = r1.norm(quote)
    bad = ("template", "no_end", "fragment") if force else ("template", "banned_topic", "no_end", "fragment")
    for a in ss:
        if a["text"] == q:
            return "" if a["flag"] not in bad else f"flag {a['flag']}"
    for a, b in zip(ss, ss[1:]):
        if q == a["text"] + " " + b["text"] and a["section"] == b["section"]:
            fl = [x["flag"] for x in (a, b) if x["flag"] in bad]
            return "" if not fl else f"flag {fl}"
    return "not found as whole sentence(s)"


def verify_web(quote: str, url: str) -> tuple[str, str]:
    p = web_text_path(url)
    if not p.exists():
        return "page not cached", ""
    d = json.loads(p.read_text())
    text, q = d["text"], r1.norm(quote)
    i = text.find(q)
    if i < 0:
        return "not found on the cached page", d["retrieved_at"]
    before = text[:i].rstrip()
    if before and before[-1] not in ".!?¶:”\"…" and not before.endswith(("¶", ".)", "!)")):
        return f"does not start at a sentence boundary (…{before[-25:]!r})", d["retrieved_at"]
    if not re.search(r"[.!?][\"”')]?$", q):
        return "does not end a sentence", d["retrieved_at"]
    return "", d["retrieved_at"]


COLS = ["hood_id", "hood_name", "quote", "source_name", "source_url", "about_area", "scope", "licence_note",
        "retrieved_at", "verified", "character", "topic"]


def stage_write() -> None:
    res = json.loads(RESOLVED.read_text())
    cur = json.loads(CURATION.read_text())
    hoods, arts = hood_list(), articles()
    rows, srows, nothing, errs = [], [], [], []
    for hid, name in hoods.items():
        c = cur.get(hid, {})
        mine = []
        for pick in c.get("quotes", []):
            q = r1.norm(pick["quote"])
            ch, topic = pick.get("character"), pick.get("topic")
            if ch not in (1, 2, 3) or topic not in TOPICS:
                errs.append(f"{hid}: bad character/topic on {q[:40]!r}")
                continue
            if len(q.split()) > MAX_WORDS:
                errs.append(f"{hid}: over {MAX_WORDS} words: {q[:40]!r}")
                continue
            if BAN.search(q) and not pick.get("force"):
                errs.append(f"{hid}: banned topic word {BAN.search(q).group(0)!r} in {q[:50]!r}")
                continue
            if "web_url" in pick:
                why, at = verify_web(q, pick["web_url"])
                if pick.get("scope") not in SCOPES or OFF_LIMITS.search(urlparse(pick["web_url"]).netloc):
                    why = why or "bad scope or off-limits host"
                row = {"source_name": pick["source_name"], "source_url": pick["web_url"],
                       "about_area": pick["about_area"], "scope": pick.get("scope"),
                       "licence_note": pick.get("licence_note", "Short quotation from the publisher's own page; "
                                                "all rights remain with the publisher"),
                       "retrieved_at": at}
            else:
                entry = next((e for e in arts.get(hid, []) if e[0] == pick["title"]), None)
                art = final_title(pick["title"], res) if entry else None
                if not art:
                    errs.append(f"{hid}: {pick['title']} is not one of its articles")
                    continue
                why = verify_wiki(q, art, bool(pick.get("force")))
                body = json.loads(body_path(art).read_text())
                row = {"source_name": "Wikipedia", "source_url": wiki_url(art),
                       "about_area": pick.get("about_area", entry[1]), "scope": pick.get("scope", entry[2]),
                       "licence_note": r1.LICENCE.format(rev=body["revision_id"], ts=body["revision_timestamp"]),
                       "retrieved_at": body["retrieved_at"]}
            if why:
                errs.append(f"{hid}: {why}: {q[:60]!r}")
                continue
            mine.append({"hood_id": hid, "hood_name": name, "quote": q, **row, "verified": "yes",
                         "character": ch, "topic": topic})
        if sum(1 for r in mine if r["topic"] == "history") > 1:
            errs.append(f"{hid}: more than one history line")
        if len(mine) > 3:
            errs.append(f"{hid}: more than three quotes")
        if not mine:
            nothing.append(hid)
        rows += mine
        marks = []
        for lm in c.get("landmarks", []):
            src = next((r for r in mine if lm["name"].lower() in r["quote"].lower()), None)
            if src is None:
                errs.append(f"{hid}: landmark {lm['name']!r} is not named in any of its quotes")
                continue
            marks.append({"name": lm["name"], "kind": lm["kind"], "named_by": src["source_name"],
                          "source_url": src["source_url"]})
        if c.get("plain_summary") and len(c["plain_summary"].split()) > 25:
            errs.append(f"{hid}: plain_summary over 25 words")
        if mine:
            srows.append({"hood_id": hid, "hood_name": name, "plain_summary": c.get("plain_summary", ""),
                          "landmarks_json": json.dumps(marks, ensure_ascii=False),
                          "best_character": max(r["character"] for r in mine), "n_quotes": len(mine)})
    if errs:
        raise SystemExit("write stopped:\n  " + "\n  ".join(errs))
    for path, rr, cols in ((OUT_Q, rows, COLS), (OUT_S, srows, list(srows[0].keys()))):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rr)
    print(f"write: {len(rows)} quotes for {len(hoods) - len(nothing)} of {len(hoods)} neighborhoods; "
          f"nothing for: {nothing}")


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("bodies", "all"):
        stage_bodies()
    if stage in ("candidates", "all"):
        stage_candidates()
    if stage in ("web", "all"):
        stage_web(sys.argv[2:] or None)
    if stage in ("compile", "write", "all") and (D / "picks_wiki.txt").exists():
        stage_compile()
    if stage in ("write", "all") and CURATION.exists():
        stage_write()


if __name__ == "__main__":
    main()
