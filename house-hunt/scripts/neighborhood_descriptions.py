"""Outside descriptions of each neighborhood, as short attributed quotes.

Source used: the lead (intro) section of English Wikipedia articles, read from the public
database dump on dumps.wikimedia.org (the bulk channel Wikimedia offers for automated use),
NOT from the live site: en.wikipedia.org answered the first API request of the session with a
rate-limit refusal, which ends that host for the session (see HOST_KILL / _host_kill.json).

Stages (each is resumable and idempotent; run them in order, or `all`):
  index       download the multistream index once (raw/big/, not committed), resolve our titles
              (and redirects) to byte ranges in the dump
  fetch       one HTTP Range request per needed bz2 stream (about 0.2 to 2 MB each), extract the
              page, keep its lead section + revision id in raw/neighborhood_descriptions/leads/
  candidates  clean the wikitext to plain text, split into sentences, flag the ones we may not
              use (templates dropped, demographics, crime, population...), write candidates.json
  write       read the hand curation (raw/neighborhood_descriptions/curation.json: which sentence
              per article, plain_summary, landmarks), re-verify every quote verbatim against the
              cached lead, and write the two CSVs

Outputs: data/reference/neighborhood_descriptions.csv, data/reference/neighborhood_summaries.csv
"""
from __future__ import annotations

import bz2
import csv
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote as urlquote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from lib import RAW, ROOT, USER_AGENT, now_iso  # noqa: E402

SRC = "neighborhood_descriptions"
D = RAW / SRC
BIG = RAW / "big" / SRC
LEADS = D / "leads"
KILL_PATH = D / "_host_kill.json"
RESOLVED = D / "resolved_titles.json"
CAND = D / "candidates.json"
CURATION = D / "curation.json"
OUT_Q = ROOT / "data" / "reference" / "neighborhood_descriptions.csv"
OUT_S = ROOT / "data" / "reference" / "neighborhood_summaries.csv"

DUMP_DATE = "20261101"
DUMP_HOST = "dumps.wikimedia.org"
DUMP_BASE = f"https://{DUMP_HOST}/enwiki/{DUMP_DATE}/enwiki-{DUMP_DATE}-pages-articles-multistream"
INDEX_URL = DUMP_BASE + "-index.txt.bz2"
DUMP_URL = DUMP_BASE + ".xml.bz2"
LICENCE = ("Wikipedia, CC BY-SA 4.0; text of revision {rev} ({ts}) as published in the enwiki "
           "database dump of 2026-11-01; the live article may have changed since")

MAX_WORDS = 35

# ---------------------------------------------------------------- host kill flags (on disk)


def load_kill() -> dict:
    return json.loads(KILL_PATH.read_text()) if KILL_PATH.exists() else {}


def kill_host(host: str, why: str) -> None:
    k = load_kill()
    if host not in k:
        k[host] = {"reason": why, "at": now_iso()}
        D.mkdir(parents=True, exist_ok=True)
        KILL_PATH.write_text(json.dumps(k, indent=1))


def check_host(host: str) -> None:
    if host in load_kill():
        raise SystemExit(f"host {host} is ended for this session: {load_kill()[host]['reason']}")


def log_index(meta: dict) -> None:
    D.mkdir(parents=True, exist_ok=True)
    with open(D / "_index.jsonl", "a") as f:
        f.write(json.dumps(meta) + "\n")


# ---------------------------------------------------------------- neighborhood -> articles
# (wikipedia title, about_area, scope). scope = exact when the article is about the place named
# in the neighborhood's name (or one of the places a combined name lists); enclosing when the
# article covers a larger area that contains it.



CT = "Connecticut"
NJ = "New Jersey"
NY = "New York"


def town(name: str, st: str, title: str | None = None):
    return [(title or f"{name}, {st}", name, "exact")]


HOODS: dict[str, list[tuple[str, str, str]]] = {
    # Connecticut
    "ct:oxford": town("Oxford", CT), "ct:shelton": town("Shelton", CT),
    "ct:west-haven": town("West Haven", CT), "ct:westport": town("Westport", CT),
    "ct:bridgeport": town("Bridgeport", CT), "ct:fairfield": town("Fairfield", CT),
    "ct:stratford": town("Stratford", CT), "ct:trumbull": town("Trumbull", CT),
    "ct:beacon-falls": town("Beacon Falls", CT), "ct:seymour": town("Seymour", CT),
    "ct:hamden": town("Hamden", CT), "ct:milford-city-balance-": town("Milford", CT),
    "ct:brookfield": town("Brookfield", CT), "ct:danbury": town("Danbury", CT),
    "ct:norwalk": town("Norwalk", CT), "ct:stamford": town("Stamford", CT),
    # New Jersey
    "nj:bordentown": [("Bordentown, New Jersey", "Bordentown (city)", "exact"),
                      ("Bordentown Township, New Jersey", "Bordentown Township", "exact")],
    "nj:edgewater": town("Edgewater", NJ), "nj:fort-lee": town("Fort Lee", NJ),
    "nj:franklin": town("Franklin Township (Somerset County)", NJ,
                        "Franklin Township, Somerset County, New Jersey"),
    "nj:garwood": town("Garwood", NJ), "nj:long-branch": town("Long Branch", NJ),
    "nj:maplewood": town("Maplewood", NJ), "nj:mount-arlington": town("Mount Arlington", NJ),
    "nj:north-bergen": town("North Bergen", NJ),
    "nj:old-bridge": town("Old Bridge Township", NJ, "Old Bridge Township, New Jersey"),
    "nj:rahway": town("Rahway", NJ), "nj:red-bank": town("Red Bank", NJ),
    "nj:somerville": town("Somerville", NJ),
    "nj:springfield": town("Springfield Township (Union County)", NJ,
                           "Springfield Township, Union County, New Jersey"),
    "nj:weehawken": town("Weehawken", NJ), "nj:east-rutherford": town("East Rutherford", NJ),
    "nj:englewood": town("Englewood", NJ), "nj:hackensack": town("Hackensack", NJ),
    "nj:montvale": town("Montvale", NJ), "nj:ridgewood": town("Ridgewood", NJ),
    "nj:teaneck": town("Teaneck", NJ), "nj:belleville": town("Belleville", NJ),
    "nj:bloomfield": town("Bloomfield", NJ),
    "nj:city-of-orange": town("Orange", NJ), "nj:east-orange": town("East Orange", NJ),
    "nj:montclair": town("Montclair", NJ), "nj:newark": town("Newark", NJ),
    "nj:south-orange": town("South Orange", NJ), "nj:bayonne": town("Bayonne", NJ),
    "nj:harrison": town("Harrison", NJ), "nj:jersey-city": town("Jersey City", NJ),
    "nj:princeton": town("Princeton", NJ), "nj:carteret": town("Carteret", NJ),
    "nj:east-brunswick": town("East Brunswick", NJ), "nj:new-brunswick": town("New Brunswick", NJ),
    "nj:atlantic-highlands": town("Atlantic Highlands", NJ), "nj:dover": town("Dover", NJ),
    "nj:morris-plains": town("Morris Plains", NJ),
    "nj:parsippany-troy-hills": town("Parsippany-Troy Hills", NJ, "Parsippany–Troy Hills, New Jersey"),
    "nj:riverdale": town("Riverdale", NJ),
    "nj:roxbury": town("Roxbury Township", NJ, "Roxbury Township, New Jersey"),
    "nj:clifton": town("Clifton", NJ), "nj:hawthorne": town("Hawthorne", NJ),
    "nj:wayne": town("Wayne", NJ), "nj:bound-brook": town("Bound Brook", NJ),
    "nj:elizabeth": town("Elizabeth", NJ), "nj:plainfield": town("Plainfield", NJ),
    # New York outside the city
    "ny:glen-cove": town("Glen Cove", NY), "ny:lagrange": town("LaGrange", NY),
    "ny:long-beach": town("Long Beach", NY),
    "ny:middletown": town("Middletown", NY, "Middletown, Orange County, New York"),
    "ny:new-paltz": [("New Paltz (village), New York", "New Paltz (village)", "exact"),
                     ("New Paltz, New York", "New Paltz (town)", "exact")],
    "ny:wallkill": town("Wallkill (town)", NY, "Wallkill, Orange County, New York"),
    "ny:hempstead": town("Hempstead (village)", NY, "Hempstead (village), New York"),
    "ny:valley-stream": town("Valley Stream", NY),
    "ny:haverstraw": [("Haverstraw (village), New York", "Haverstraw (village)", "exact"),
                      ("Haverstraw, New York", "Haverstraw (town)", "enclosing")],
    "ny:patchogue": town("Patchogue", NY), "ny:new-rochelle": town("New Rochelle", NY),
    "ny:peekskill": town("Peekskill", NY), "ny:port-chester": town("Port Chester", NY),
    "ny:white-plains": town("White Plains", NY), "ny:yonkers": town("Yonkers", NY),
    # New York City
    "ny:astoria-central-": [("Astoria, Queens", "Astoria", "enclosing")],
    "ny:astoria-east-woodside-north-": [("Astoria, Queens", "Astoria", "enclosing"),
                                        ("Woodside, Queens", "Woodside", "enclosing")],
    "ny:old-astoria-hallets-point": [("Astoria, Queens", "Astoria", "enclosing"),
                                     ("Hallets Point", "Hallets Point", "exact")],
    "ny:bedford-stuyvesant-east-": [("Bedford–Stuyvesant, Brooklyn", "Bedford-Stuyvesant", "enclosing")],
    "ny:bedford-stuyvesant-west-": [("Bedford–Stuyvesant, Brooklyn", "Bedford-Stuyvesant", "enclosing")],
    "ny:flatbush": [("Flatbush, Brooklyn", "Flatbush", "exact")],
    "ny:gravesend-south-": [("Gravesend, Brooklyn", "Gravesend", "enclosing")],
    "ny:gravesend-west-": [("Gravesend, Brooklyn", "Gravesend", "enclosing")],
    "ny:gravesend-east-homecrest": [("Gravesend, Brooklyn", "Gravesend", "enclosing"),
                                    ("Homecrest, Brooklyn", "Homecrest", "exact")],
    "ny:new-springville-willowbrook-bulls-head-travis": [
        ("New Springville, Staten Island", "New Springville", "exact"),
        ("Willowbrook, Staten Island", "Willowbrook", "exact"),
        ("Bulls Head, Staten Island", "Bulls Head", "exact"),
        ("Travis, Staten Island", "Travis", "exact")],
    "ny:pelham-bay-country-club-city-island": [
        ("Pelham Bay (neighborhood), Bronx", "Pelham Bay", "exact"),
        ("Country Club, Bronx", "Country Club", "exact"),
        ("City Island, Bronx", "City Island", "exact")],
    "ny:pomonok-electchester-hillcrest": [("Pomonok, Queens", "Pomonok", "exact"),
                                          ("Electchester", "Electchester", "exact"),
                                          ("Hillcrest, Queens", "Hillcrest", "exact")],
    "ny:tompkinsville-stapleton-clifton-fox-hills": [
        ("Tompkinsville, Staten Island", "Tompkinsville", "exact"),
        ("Stapleton, Staten Island", "Stapleton", "exact"),
        ("Clifton, Staten Island", "Clifton", "exact")],
    "ny:upper-east-side-lenox-hill-roosevelt-island": [
        ("Upper East Side", "Upper East Side", "exact"), ("Lenox Hill", "Lenox Hill", "exact"),
        ("Roosevelt Island", "Roosevelt Island", "exact")],
    "ny:upper-west-side-manhattan-valley": [("Upper West Side", "Upper West Side", "exact"),
                                            ("Manhattan Valley", "Manhattan Valley", "exact")],
    "ny:kingsbridge-heights-van-cortlandt-village": [
        ("Kingsbridge Heights, Bronx", "Kingsbridge Heights", "exact"),
        ("Van Cortlandt Village", "Van Cortlandt Village", "exact")],
    "ny:riverdale-spuyten-duyvil": [("Riverdale, Bronx", "Riverdale", "exact"),
                                    ("Spuyten Duyvil, Bronx", "Spuyten Duyvil", "exact")],
    "ny:williamsbridge-olinville": [("Williamsbridge, Bronx", "Williamsbridge", "exact"),
                                    ("Olinville, Bronx", "Olinville", "exact")],
    "ny:bath-beach": [("Bath Beach, Brooklyn", "Bath Beach", "exact")],
    "ny:bay-ridge": [("Bay Ridge, Brooklyn", "Bay Ridge", "exact")],
    "ny:bensonhurst": [("Bensonhurst, Brooklyn", "Bensonhurst", "exact")],
    "ny:brighton-beach": [("Brighton Beach", "Brighton Beach", "exact")],
    "ny:east-flatbush-erasmus": [("East Flatbush, Brooklyn", "East Flatbush", "enclosing")],
    "ny:east-flatbush-farragut": [("East Flatbush, Brooklyn", "East Flatbush", "enclosing"),
                                  ("Farragut, Brooklyn", "Farragut", "exact")],
    "ny:east-new-york-north-": [("East New York, Brooklyn", "East New York", "enclosing")],
    "ny:flatbush-west-ditmas-park-parkville": [("Ditmas Park, Brooklyn", "Ditmas Park", "exact"),
                                               ("Parkville, Brooklyn", "Parkville", "exact"),
                                               ("Flatbush, Brooklyn", "Flatbush", "enclosing")],
    "ny:flatlands": [("Flatlands, Brooklyn", "Flatlands", "exact")],
    "ny:madison": [("Madison, Brooklyn", "Madison", "exact")],
    "ny:midwood": [("Midwood, Brooklyn", "Midwood", "exact")],
    "ny:prospect-lefferts-gardens-wingate": [
        ("Prospect Lefferts Gardens", "Prospect Lefferts Gardens", "exact"),
        ("Wingate, Brooklyn", "Wingate", "exact")],
    "ny:sheepshead-bay-manhattan-beach-gerritsen-beach": [
        ("Sheepshead Bay, Brooklyn", "Sheepshead Bay", "exact"),
        ("Manhattan Beach, Brooklyn", "Manhattan Beach", "exact"),
        ("Gerritsen Beach, Brooklyn", "Gerritsen Beach", "exact")],
    "ny:windsor-terrace-south-slope": [("Windsor Terrace, Brooklyn", "Windsor Terrace", "exact"),
                                       ("South Slope, Brooklyn", "South Slope", "exact")],
    "ny:east-harlem-south-": [("East Harlem", "East Harlem", "enclosing")],
    "ny:hamilton-heights-sugar-hill": [("Hamilton Heights, Manhattan", "Hamilton Heights", "exact"),
                                       ("Sugar Hill, Manhattan", "Sugar Hill", "exact")],
    "ny:harlem-north-": [("Harlem", "Harlem", "enclosing")],
    "ny:inwood": [("Inwood, Manhattan", "Inwood", "exact")],
    "ny:manhattanville-west-harlem": [("Manhattanville, Manhattan", "Manhattanville", "exact")],
    "ny:washington-heights-north-": [("Washington Heights, Manhattan", "Washington Heights", "enclosing"),
                                     ("Hudson Heights, Manhattan", "Hudson Heights", "exact")],
    "ny:washington-heights-south-": [("Washington Heights, Manhattan", "Washington Heights", "enclosing")],
    "ny:elmhurst": [("Elmhurst, Queens", "Elmhurst", "exact")],
    "ny:flushing-willets-point": [("Flushing, Queens", "Flushing", "exact"),
                                  ("Willets Point, Queens", "Willets Point", "exact")],
    "ny:forest-hills": [("Forest Hills, Queens", "Forest Hills", "exact")],
    "ny:jamaica": [("Jamaica, Queens", "Jamaica", "exact")],
    "ny:jamaica-hills-briarwood": [("Jamaica Hills, Queens", "Jamaica Hills", "exact"),
                                   ("Briarwood, Queens", "Briarwood", "exact")],
    "ny:kew-gardens": [("Kew Gardens, Queens", "Kew Gardens", "exact")],
    "ny:kew-gardens-hills": [("Kew Gardens Hills, Queens", "Kew Gardens Hills", "exact")],
    "ny:murray-hill-broadway-flushing": [("Murray Hill, Queens", "Murray Hill", "exact"),
                                         ("Broadway–Flushing, Queens", "Broadway-Flushing", "exact"),
                                         ("Flushing, Queens", "Flushing", "enclosing")],
    "ny:north-corona": [("Corona, Queens", "Corona", "enclosing")],
    "ny:rockaway-beach-arverne-edgemere": [("Rockaway Beach, Queens", "Rockaway Beach", "exact"),
                                           ("Arverne, Queens", "Arverne", "exact"),
                                           ("Edgemere, Queens", "Edgemere", "exact")],
    "ny:sunnyside": [("Sunnyside, Queens", "Sunnyside", "exact")],
    "ny:st-george-new-brighton": [("St. George, Staten Island", "St. George", "exact"),
                                  ("New Brighton, Staten Island", "New Brighton", "exact")],
}


def hood_list() -> dict[str, str]:
    """Union of site/data.json neighborhoods and the scene-text CSV: hood_id -> name."""
    u: dict[str, str] = {}
    shown: dict[str, int] = {}
    for n in json.loads((ROOT / "site" / "data.json").read_text())["neighborhoods"]:
        u[n["id"]] = n["name"]
        shown[n["id"]] = n.get("counts", {}).get("shown", 0)
    with open(ROOT / "data" / "reference" / "scene_text_neighborhoods.csv") as f:
        for r in csv.DictReader(f):
            u.setdefault(r["hood_id"], r["hood_name"])
    # The list shifts while the data is being repaired: remember every neighborhood ever seen,
    # so a place that drops out of one build and comes back still has its rows.
    seen_path = D / "hood_names.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}
    seen.update(u)
    D.mkdir(parents=True, exist_ok=True)
    seen_path.write_text(json.dumps(seen, indent=1, ensure_ascii=False, sort_keys=True))
    return dict(sorted(seen.items(), key=lambda kv: (-shown.get(kv[0], 0), kv[0])))


# ---------------------------------------------------------------- stage: index

def download_index() -> Path:
    BIG.mkdir(parents=True, exist_ok=True)
    p = BIG / f"enwiki-{DUMP_DATE}-multistream-index.txt.bz2"
    if p.exists():
        return p
    check_host(DUMP_HOST)
    lib._throttle(DUMP_HOST)
    tmp = p.with_suffix(".part")
    with requests.get(INDEX_URL, headers={"User-Agent": USER_AGENT}, stream=True, timeout=120) as r:
        meta = {"url": INDEX_URL, "retrieved_at": now_iso(), "status": r.status_code,
                "path": str(p.relative_to(ROOT)), "source": SRC}
        log_index(meta)
        if r.status_code in (401, 403, 429):
            kill_host(DUMP_HOST, f"HTTP {r.status_code} on the index download")
            raise SystemExit(f"refused: HTTP {r.status_code}")
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.rename(p)
    return p


def scan_index(wanted: set[str]) -> dict[str, dict]:
    """title -> {offset, end, page_id}. end is the next stream's offset."""
    p = download_index()
    found: dict[str, dict] = {}
    need_end: dict[int, list[str]] = {}
    prev = None
    with bz2.open(p, "rt", encoding="utf-8") as f:
        for line in f:
            off_s, pid, title = line.rstrip("\n").split(":", 2)
            off = int(off_s)
            if off != prev:
                if prev in need_end:
                    for t in need_end.pop(prev):
                        found[t]["end"] = off
                prev = off
            title = html.unescape(title)
            if title in wanted:
                found[title] = {"offset": off, "end": None, "page_id": int(pid)}
                need_end.setdefault(off, []).append(title)
    return found


def all_titles() -> list[str]:
    seen = []
    for arts in HOODS.values():
        for t, _, _ in arts:
            if t not in seen:
                seen.append(t)
    return seen


def stage_index() -> None:
    D.mkdir(parents=True, exist_ok=True)
    res = json.loads(RESOLVED.read_text()) if RESOLVED.exists() else {}
    todo = {t for t in all_titles() if t not in res}
    todo |= {v["redirect_to"] for v in res.values() if v.get("redirect_to") and v["redirect_to"] not in res}
    if not todo:
        print("index: nothing to resolve")
        return
    found = scan_index(todo)
    for t in todo:
        res[t] = found.get(t) or {"missing": True}
    RESOLVED.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(f"index: resolved {len(found)} of {len(todo)}; missing: {sorted(t for t in todo if t not in found)}")


# ---------------------------------------------------------------- stage: fetch

def fetch_stream(offset: int, end: int) -> bytes:
    BIG.mkdir(parents=True, exist_ok=True)
    p = BIG / f"stream_{offset}.bz2"
    if p.exists():
        return p.read_bytes()
    check_host(DUMP_HOST)
    lib.HOST_DELAY.setdefault(DUMP_HOST, 2.0)
    lib._throttle(DUMP_HOST)
    rng = f"bytes={offset}-{end - 1}"
    r = requests.get(DUMP_URL, headers={"User-Agent": USER_AGENT, "Range": rng}, timeout=180)
    log_index({"url": DUMP_URL, "range": rng, "retrieved_at": now_iso(), "status": r.status_code,
               "path": str(p.relative_to(ROOT)), "source": SRC})
    if r.status_code in (401, 403, 429):
        kill_host(DUMP_HOST, f"HTTP {r.status_code} on a range request")
        raise SystemExit(f"refused: HTTP {r.status_code}")
    if r.status_code != 206:
        raise RuntimeError(f"expected 206, got {r.status_code}")
    p.write_bytes(r.content)
    return r.content


PAGE_RE = re.compile(r"<page>(.*?)</page>", re.S)


def lead_path(title: str) -> Path:
    return LEADS / (re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_") + ".json")


def extract_page(xml: str, title: str) -> dict | None:
    for m in PAGE_RE.finditer(xml):
        pg = m.group(1)
        t = html.unescape(re.search(r"<title>(.*?)</title>", pg, re.S).group(1))
        if t != title:
            continue
        rev = re.search(r"<revision>\s*<id>(\d+)</id>", pg).group(1)
        ts = re.search(r"<timestamp>(.*?)</timestamp>", pg).group(1)
        tm = re.search(r"<text[^>]*>(.*?)</text>", pg, re.S)
        text = html.unescape(tm.group(1)) if tm else ""
        red = re.search(r'<redirect title="(.*?)"', pg)
        return {"title": t, "rev": rev, "ts": ts, "text": text,
                "redirect_to": html.unescape(red.group(1)) if red else None}
    return None


def stage_fetch() -> bool:
    """Returns True when another `index` pass is needed (redirect targets to resolve)."""
    LEADS.mkdir(parents=True, exist_ok=True)
    res = json.loads(RESOLVED.read_text())
    again = False
    for title, info in list(res.items()):
        if info.get("missing") or lead_path(title).exists() or info.get("redirect_to"):
            continue
        raw = fetch_stream(info["offset"], info["end"])
        xml = bz2.decompress(raw).decode("utf-8")
        pg = extract_page(xml, title)
        if pg is None:
            info["missing"] = True
        elif pg["redirect_to"]:
            info["redirect_to"] = pg["redirect_to"]
            again = again or pg["redirect_to"] not in res
        else:
            lead = re.split(r"^==[^=].*?==\s*$", pg["text"], maxsplit=1, flags=re.M)[0]
            lead_path(title).write_text(json.dumps({
                "title": title, "revision_id": pg["rev"], "revision_timestamp": pg["ts"],
                "dump": DUMP_DATE, "dump_url": DUMP_URL, "byte_range": [info["offset"], info["end"] - 1],
                "retrieved_at": now_iso(), "lead_wikitext": lead}, indent=1, ensure_ascii=False))
            print("lead:", title, len(lead))
        RESOLVED.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return again


def final_title(title: str, res: dict) -> str | None:
    for _ in range(4):
        info = res.get(title)
        if not info or info.get("missing"):
            return None
        if info.get("redirect_to"):
            title = info["redirect_to"]
            continue
        return title
    return None


# ---------------------------------------------------------------- wikitext -> plain sentences

MARK = "⁣"  # stands for a dropped template / reference with content we cannot render
SAFE_TPL = {"nbsp": " ", "snd": " – ", "spnd": " – ", "spaced ndash": " – ", "ndash": "–",
            "mdash": "—", "emdash": "—", "'": "'", "'s": "'s"}
SILENT_TPL = re.compile(r"^(short description|use mdy dates|use dmy dates|use american english|"
                        r"infobox|about|for|other uses|redirect|distinguish|more citations|refimprove|"
                        r"citation needed|cn|fact|update|as of\b.*lc|pp-|coord|hatnote|multiple issues|"
                        r"unreferenced|original research|lead too|expand|cleanup|efn|sfn|r\b|rp\b|"
                        r"clarify|when|by whom|dubious|better source|failed verification|which|"
                        r"see also|main|pp|good article|featured article|italic title|"
                        r"nrhp|wide image|multiple image|toc|clear|-|portal|update inline|"
                        r"citation|cite|dead link|webarchive|page needed|full citation|"
                        r"additional citations|more footnotes|no footnotes|primary sources|tone|"
                        r"advert|peacock|weasel|globalize|short desc|defaultsort|authority control|"
                        r"external media|image frame|location map|maplink|commons|wiktionary)", re.I)


def clean_wikitext(w: str) -> str:
    w = re.sub(r"<!--.*?-->", "", w, flags=re.S)
    w = re.sub(r"<ref[^>]*?/>", "", w, flags=re.S)
    w = re.sub(r"<ref[^>]*?>.*?</ref>", "", w, flags=re.S)
    w = re.sub(r"<(gallery|imagemap|timeline|math|score)[^>]*?>.*?</\1>", MARK, w, flags=re.S)
    # tables
    for _ in range(5):
        w2 = re.sub(r"\{\|(?:(?!\{\||\|\}).)*\|\}", "", w, flags=re.S)
        if w2 == w:
            break
        w = w2
    # innermost templates first
    def tpl(m: re.Match) -> str:
        body = m.group(1)
        name = body.split("|", 1)[0].strip().lower()
        if name in SAFE_TPL:
            return SAFE_TPL[name]
        if SILENT_TPL.match(name):
            return ""
        return MARK
    for _ in range(30):
        w2 = re.sub(r"\{\{((?:(?!\{\{|\}\}).)*)\}\}", tpl, w, flags=re.S)
        if w2 == w:
            break
        w = w2
    # files / images (may nest links)
    for _ in range(10):
        w2 = re.sub(r"\[\[(?:File|Image|Category):(?:(?!\[\[|\]\]).|\[\[(?:(?!\[\[|\]\]).)*\]\])*\]\]", "", w,
                    flags=re.S | re.I)
        if w2 == w:
            break
        w = w2
    w = re.sub(r"\[\[(?:[^\[\]|]*\|)?([^\[\]|]*)\]\]", r"\1", w)
    w = re.sub(r"\[https?://\S+\s+([^\]]*)\]", r"\1", w)
    w = re.sub(r"\[https?://\S+\]", "", w)
    w = re.sub(r"'{2,5}", "", w)
    w = re.sub(r"<br\s*/?>", " ", w, flags=re.I)
    w = re.sub(r"</?[a-zA-Z][^>]*>", "", w)
    w = html.unescape(w).replace(" ", " ")
    paras = []
    for line in w.split("\n"):
        s = line.strip()
        if not s or s.strip(MARK + " ") == "" or s[0] in "*#:;|!{}":
            continue
        paras.append(re.sub(r"[ \t]+", " ", s))
    return "\n".join(paras)


ABBR = re.compile(r"(?:\b(?:St|Mt|Dr|Mr|Mrs|Ms|Jr|Sr|No|Ave|Blvd|Rd|Ft|Co|Inc|Corp|Gen|Gov|Rev|Col|Capt|"
                  r"approx|est|c|ca|vs|etc|U\.S|N\.J|N\.Y|i\.e|e\.g)|\b[A-Z])\.$")


def sentences(par: str) -> list[str]:
    out, buf = [], ""
    for piece in re.split(r"(?<=[.!?])\s+(?=[\"“A-Z0-9])", par):
        buf = (buf + " " + piece).strip() if buf else piece
        if ABBR.search(buf):
            continue
        out.append(buf)
        buf = ""
    if buf:
        out.append(buf)
    return out


# Sentences we never quote: who lives there by race / ethnicity / religion, crime, and the
# dry administrative ones (census counts, districts, ZIP codes).
BAN = re.compile(
    r"\b(african[- ]american|black|white|hispanic|latino|latina|latinx|asian|chinese|korean|indian|"
    r"jewish|jews|orthodox|hasidic|muslim|christian|catholic|italian|irish|greek|russian|polish|"
    r"dominican|puerto ric|caribbean|west indian|haitian|jamaican-|guyanese|bangladeshi|pakistani|"
    r"arab|egyptian|ukrainian|soviet|immigra|ethnic|enclave|diverse|diversity|minority|minorities|"
    r"racial|race|segregat|demograph|non-hispanic|latin american|south asian|filipino|colombian|"
    r"ecuadorian|mexican|albanian|german|scandinavian|norwegian|syrian|sephardic|turkish|"
    r"crime|crimes|murder|homicide|violent|violence|riot|gang|drug|shooting|poverty|poor|"
    r"low-income|income|wealth|affluent|richest|poorest|"
    r"population|census|residents as of|zip code|community district|community board|precinct|"
    r"city council|congressional|state senate|assembly district|politically|patrolled|"
    r"per capita|ranked|ranking|rated|best places|money magazine|niche)\b", re.I)


def stage_candidates() -> None:
    res = json.loads(RESOLVED.read_text())
    out = {}
    for title in all_titles():
        ft = final_title(title, res)
        if not ft or not lead_path(ft).exists():
            out[title] = {"missing": True}
            continue
        lead = json.loads(lead_path(ft).read_text())
        text = clean_wikitext(lead["lead_wikitext"])
        sents = []
        for par in text.split("\n"):
            for s in sentences(par):
                n = len(s.split())
                flag = ("template" if MARK in s else "banned_topic" if BAN.search(s)
                        else "long" if n > MAX_WORDS else "short" if n < 6 else "")
                sents.append({"i": len(sents), "words": n, "flag": flag, "text": s})
        out[title] = {"article": ft, "revision_id": lead["revision_id"], "sentences": sents}
    CAND.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    ok = sum(1 for v in out.values() if not v.get("missing"))
    print(f"candidates: {ok} articles with a lead, {len(out) - ok} missing")


# ---------------------------------------------------------------- stage: write

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def verify(quote: str, article: str) -> bool:
    """Re-read the cached lead and confirm the quote is there word for word, as whole sentences."""
    lead = json.loads(lead_path(article).read_text())
    text = clean_wikitext(lead["lead_wikitext"])
    all_s = [norm(s) for par in text.split("\n") for s in sentences(par)]
    q = norm(quote)
    if q in all_s:
        return True
    for a, b in zip(all_s, all_s[1:]):  # two consecutive sentences
        if q == a + " " + b:
            return True
    return False


WEB_SRC = "neighborhood_descriptions_web"


def page_text(raw: bytes) -> str:
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    return norm(html.unescape(re.sub(r"<[^>]+>", " ", t)).replace("\u00a0", " "))


def web_row(hid: str, name: str, pick: dict) -> dict:
    """A quote from an official page (tier 2). The page is fetched once with lib.cached_get after
    its robots.txt was read by hand (see the harvest notes); here it is re-read from the cache."""
    host = requests.utils.urlparse(pick["web_url"]).netloc
    check_host(host)
    raw, meta = lib.cached_get(pick["web_url"], WEB_SRC, ext="html", retries=1, timeout=40)
    if meta["status"] in (401, 403, 429):
        kill_host(host, f"HTTP {meta['status']}")
        raise SystemExit(f"refused by {host}")
    q = norm(pick["quote"])
    ok = meta["status"] == 200 and q in page_text(raw)
    if len(q.split()) > MAX_WORDS or BAN.search(q):
        raise SystemExit(f"{hid}: web quote not usable")
    return {"hood_id": hid, "hood_name": name, "quote": q, "source_name": pick["source_name"],
            "source_url": pick["web_url"], "about_area": pick["about_area"], "scope": pick["scope"],
            "licence_note": pick["licence_note"], "retrieved_at": meta["retrieved_at"],
            "verified": "yes" if ok else "no"}


def stage_write() -> None:
    res = json.loads(RESOLVED.read_text())
    cand = json.loads(CAND.read_text())
    cur = json.loads(CURATION.read_text())
    hoods = hood_list()
    rows, srows, nothing = [], [], []
    for hid, name in hoods.items():
        c = cur.get(hid, {})
        n_before = len(rows)
        for pick in c.get("quotes", []):
            if "web_url" in pick:
                rows.append(web_row(hid, name, pick))
                continue
            title, idx = pick["title"], pick["i"]
            entry = next((e for e in HOODS.get(hid, []) if e[0] == title), None)
            if entry is None:
                raise SystemExit(f"{hid}: {title} is not in HOODS")
            cd = cand[title]
            idxs = idx if isinstance(idx, list) else [idx]
            ss = [cd["sentences"][i] for i in idxs]
            quote = " ".join(s["text"] for s in ss)
            # "force": a human read the sentence and the topic filter was a false positive
            # (e.g. "White Plains Road", "bicycle race"). Template-damaged sentences are never used.
            banned = ("template",) if pick.get("force") else ("template", "banned_topic")
            bad = [s["flag"] for s in ss if s["flag"] in banned]
            if bad or len(quote.split()) > MAX_WORDS or MARK in quote:
                raise SystemExit(f"{hid}: pick {title}#{idx} not usable ({bad}, {len(quote.split())} words)")
            art = cd["article"]
            lead = json.loads(lead_path(art).read_text())
            ok = verify(quote, art)
            rows.append({
                "hood_id": hid, "hood_name": name, "quote": quote, "source_name": "Wikipedia",
                "source_url": "https://en.wikipedia.org/wiki/" + urlquote(art.replace(" ", "_"), safe=",()_-.'"),
                "about_area": pick.get("about_area", entry[1]), "scope": pick.get("scope", entry[2]),
                "licence_note": LICENCE.format(rev=lead["revision_id"], ts=lead["revision_timestamp"]),
                "retrieved_at": lead["retrieved_at"], "verified": "yes" if ok else "no"})
        if len(rows) == n_before:
            nothing.append(hid)
        if c.get("plain_summary"):
            if len(c["plain_summary"].split()) > 25:
                raise SystemExit(f"{hid}: plain_summary over 25 words")
            marks = []
            mine = rows[n_before:]
            for lm in c.get("landmarks", [])[:4]:
                src = next((r for r in mine if lm.lower() in r["quote"].lower()), None)
                if src is None:
                    raise SystemExit(f"{hid}: landmark {lm!r} is not named in any of its quotes")
                marks.append({"name": lm, "named_by": src["source_name"], "source_url": src["source_url"]})
            srows.append({"hood_id": hid, "plain_summary": c["plain_summary"],
                          "landmarks_json": json.dumps(marks, ensure_ascii=False)})
    unverified = [r for r in rows if r["verified"] != "yes"]
    if unverified:
        raise SystemExit(f"unverified quotes: {[(r['hood_id'], r['quote'][:40]) for r in unverified]}")
    for path, rr in ((OUT_Q, rows), (OUT_S, srows)):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rr[0].keys()))
            w.writeheader()
            w.writerows(rr)
    print(f"write: {len(rows)} quotes for {len(hoods) - len(nothing)} of {len(hoods)} neighborhoods; "
          f"{len(srows)} summaries; nothing for: {nothing}")


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    # The session's first Wikipedia API request was refused; never call that host from here.
    kill_host("en.wikipedia.org", "HTTP 429 'You are making too many requests to the API' on the "
              "first REST summary request of the session (2026-11-16)")
    if stage in ("index", "all"):
        stage_index()
    if stage in ("fetch", "all"):
        for _ in range(3):
            if not stage_fetch():
                break
            stage_index()
    if stage in ("candidates", "all"):
        stage_candidates()
    if stage in ("write", "all") and CURATION.exists():
        stage_write()


if __name__ == "__main__":
    main()
