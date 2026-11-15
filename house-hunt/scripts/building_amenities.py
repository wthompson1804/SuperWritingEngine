"""Building amenities, one row per building (addr_key) that has at least one unit_status == pass row in data/units.csv.

Output: data/reference/building_amenities.csv. Every value column has a `<col>_evidence` column holding a short
verbatim snippet from the page (prefixed with where on the page it sat, e.g. "[building amenity] Swimming Pool").
"no_mention" means the pages read do not list the thing; it never means "no".

Sources, in order:
  1. cached pages already on disk: the raw_path of every data/units.csv and data/listings.csv row with the same
     addr_key (all sources), the Zumper building page, URLs in also_seen_at when cached, and for management-site
     buildings the pages named in data/reference/community_facts.csv `pages_read`;
  2. data/reference/community_facts.csv values (pool, gym, controlled access, dog park / pet spa, package room,
     coworking, parking, manager) where the page parse found nothing;
  3. only if no cached page gave a single amenity: ONE fetch (building_url, else url) through lib.cached_get into
     raw/building_amenities/, robots-checked (Claude-named groups and `*`), at least 2 s per host.

Rerunnable and incremental: by default only addr_keys not yet in the CSV are processed (rows are kept for
buildings that stop passing). `--rebuild` reprocesses everything (cache only, cheap). `--no-fetch` never fetches.
"""
from __future__ import annotations

import argparse
import csv
import html as htmllib
import json
import re
import sys
import time
import urllib.robotparser
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ROOT = lib.ROOT
OUT = ROOT / "data" / "reference" / "building_amenities.csv"
SRC = "building_amenities"
DEC = json.JSONDecoder()
MIN_DELAY = 2.0
CLAUDE_UAS = ["ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai"]

VALUE_COLS = ["pool", "gym", "doorman_or_concierge", "controlled_access", "gated_or_garage_parking",
              "parking_fee_monthly", "dog_amenities", "in_unit_laundry", "roof_deck_or_outdoor_space",
              "balcony_some_units", "package_room", "coworking_or_lounge", "elevator_stated", "year_built",
              "year_renovated", "total_floors", "unit_count", "management_company"]
BLANK_WHEN_MISSING = {"parking_fee_monthly", "year_built", "year_renovated", "total_floors", "unit_count",
                      "management_company"}
COLS = (["addr_key", "building_name", "address", "city", "state", "zip", "pass_units", "source_sites"]
        + [c for v in VALUE_COLS for c in (v, v + "_evidence")]
        + ["source_url", "sources_json", "pages_parsed", "amenity_items_seen", "fetched_new_page", "notes",
           "retrieved_at"])

# ------------------------------------------------------------------ page -> segments
# A segment is (kind, label, text). kind: "list" (an amenity / feature list item or a structured field) or
# "desc" (a sentence of free description). Free text gets stricter vetoes than list items.


def flight(html: str) -> str:
    out = []
    for c in re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html):
        try:
            out.append(json.loads(c))
        except json.JSONDecodeError:
            pass
    return "".join(out)


def clean(v) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(str(v or ""))).replace("$$", "$").strip()


def sentences(text: str) -> list[str]:
    text = re.sub(r"<[^>]+>", " ", str(text or ""))
    out = []
    for part in re.split(r"[\r\n]+|(?<=[.!?])\s+|\s[*•·]\s|\s-\s", text):
        p = clean(part)
        if len(p) > 2:
            out.append(p[:400])
    return out


def seg_apartmentlist(html: str):
    fl = flight(html)
    best = None
    for m in re.finditer(r'"listing":\{"rental_id"', fl):
        try:
            o, _ = DEC.raw_decode(fl, m.start() + 10)
        except json.JSONDecodeError:
            continue
        if "available_units" in o and (best is None or len(o) > len(best)):
            best = o
    if not best:
        return None
    L, segs = best, []
    for key, label in (("community_amenities", "community amenity"), ("unit_amenities", "unit amenity"),
                       ("top_amenities", "top amenity")):
        for a in L.get(key) or []:
            if isinstance(a, dict) and a.get("display_name"):
                segs.append(("list", label, clean(a["display_name"])))
    for p in L.get("parking") or []:
        if not isinstance(p, dict):
            continue
        if p.get("category"):
            t = f"parking category: {p['category']}"
            if p.get("space_fee"):
                t += f"; space_fee: ${p['space_fee']}"
            segs.append(("list", "parking data", t))
        if p.get("comment"):
            segs.append(("list", "parking comment", "Parking: " + clean(p["comment"])))
    if L.get("parking_details_text"):
        segs.append(("list", "parking details", "Parking: " + clean(L["parking_details_text"])))
    for k in ("year_built", "year_remodeled", "total_units_count", "pmc_display_name"):
        if L.get(k):
            segs.append(("field", k, clean(L[k])))
    for k in ("description", "why_we_love_it", "long_highlight", "short_highlight"):
        for s in sentences(L.get(k)):
            segs.append(("desc", "description", s))
    return segs


def seg_zumper(html: str):
    i = html.find("window.__PRELOADED_STATE__ = ")
    if i < 0:
        return None
    try:
        st, _ = DEC.raw_decode(html[i + len("window.__PRELOADED_STATE__ = "):])
    except json.JSONDecodeError:
        return None
    e = (((st.get("detail") or {}).get("entity") or {}).get("data")) or {}
    if not e:
        return None
    segs = []
    for t in e.get("amenity_tags") or []:
        segs.append(("list", "unit amenity", clean(t)))
    for t in e.get("building_amenity_tags") or []:
        segs.append(("list", "building amenity", clean(t)))
    for k in ("year_built", "floors"):
        if e.get(k):
            segs.append(("field", k, clean(e[k])))
    for s in sentences(e.get("description")):
        segs.append(("desc", "description", s))
    return segs


NEXT_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', re.S)


def seg_trulia(html: str):
    m = NEXT_RE.search(html)
    if not m:
        return None
    try:
        hd = (json.loads(m.group(1)).get("props") or {}).get("homeDetails")
    except json.JSONDecodeError:
        return None
    if not hd:
        return None
    segs = []

    def attr(path, a):
        n, v = clean(a.get("formattedName")), clean(a.get("formattedValue"))
        if not (n or v):
            return
        segs.append(("list", "features: " + path, f"{n}: {v}" if n and v else (n or v)))
    for c in ((hd.get("features") or {}).get("categories")) or []:
        cn = clean(c.get("formattedName"))
        if re.search(r"(?i)days on market|rental terms", cn):
            continue
        for a in c.get("attributes") or []:
            attr(cn, a)
        for sc in c.get("categories") or []:
            for a in sc.get("attributes") or []:
                attr(cn + " > " + clean(sc.get("formattedName")), a)
    for s in sentences((hd.get("description") or {}).get("value")):
        segs.append(("desc", "description", s))
    return segs


def seg_greystar(html: str):
    s = flight(html)
    i = s.find('"property":{"id"')
    if i < 0:
        return None
    try:
        prop = DEC.raw_decode(s[i + len('"property":'):])[0]
    except json.JSONDecodeError:
        return None
    segs = []
    for x in prop.get("amenities") or []:
        if isinstance(x, str):
            segs.append(("list", "community amenity", clean(x)))
    for x in prop.get("features") or []:
        if isinstance(x, str):
            segs.append(("list", "unit feature", clean(x)))
    about = prop.get("about") or {}
    for s_ in sentences(about.get("longDescription")):
        segs.append(("desc", "description", s_))
    for f in prop.get("fees") or []:
        if f.get("isEnabled", True) and re.search(r"(?i)parking|garage|carport", str(f.get("label")) + str(f.get("group"))) \
                and f.get("frequency") == "monthly":
            amt = f.get("amount") if f.get("amount") is not None else f.get("minAmount")
            segs.append(("list", "fee table", f"{f.get('label')}: " + (f"${amt}/month" if amt is not None else "amount not stated")))
    return segs


def seg_avalon(html: str):
    i = html.find("Fusion.globalContent=")
    if i < 0:
        return None
    try:
        d = DEC.raw_decode(html[i + len("Fusion.globalContent="):])[0]
    except json.JSONDecodeError:
        return None
    segs = []
    for key, label in (("communityFeatures", "community feature"), ("features", "feature"), ("unitFeatures", "unit feature")):
        for f in d.get(key) or []:
            if isinstance(f, dict):
                t = clean((f.get("name") or "") + (": " + f["description"] if f.get("description") else ""))
                if t and not re.search(r"(?i)count: 0\b", t):
                    segs.append(("list", label, t))
    p = d.get("policies") or {}
    for s in sentences(p.get("residentPolicy")):
        if re.search(r"(?i)park|garage|spot|space", s):
            segs.append(("list", "parking policy", "Parking: " + s))
    for f in d.get("fees") or []:
        if isinstance(f, dict) and re.search(r"(?i)parking|garage|carport", str(f.get("name"))):
            a = f.get("amount") or {}
            if a.get("min") is not None:
                segs.append(("list", "fee table", f"{f.get('name')}: ${a.get('min')}" + (f"-${a.get('max')}" if a.get("max") != a.get("min") else "") + "/month"))
    return segs or None


AGO = re.compile(r"^(a|an|\d+) (day|week|month|year)s? ago$", re.I)


def seg_generic(html: str):
    from bs4 import BeautifulSoup
    s = BeautifulSoup(html, "lxml")
    for t in s(["script", "style", "noscript", "nav", "header", "footer", "select", "svg", "template"]):
        t.decompose()
    lines = []
    for ln in s.get_text("\n").split("\n"):
        ln = clean(ln.replace("​", ""))
        if len(ln) > 2:
            lines.append(ln)
    ago = [i for i, ln in enumerate(lines) if AGO.match(ln)]          # embedded resident reviews: not the manager's words
    if len(ago) >= 2:
        lines = lines[:max(0, ago[0] - 3)] + lines[ago[-1] + 8:]
    for i, ln in enumerate(lines):                                    # cross-community blocks
        if re.match(r"^(Nearby Properties|PROPERTIES IN THIS COMMUNITY|NAVIGATION|Nearby Communities|Similar Communities)$", ln):
            lines = lines[:i]
            break
    segs = []
    for ln in lines:
        if len(ln) <= 70:
            segs.append(("list", "page line", ln))
        else:
            for sent in sentences(ln):
                segs.append(("desc", "page text", sent))
    return segs


def page_segments(text: str):
    """(parser name, segments) for a cached page."""
    if "window.__PRELOADED_STATE__ = " in text:
        s = seg_zumper(text)
        if s is not None:
            return "zumper", s
    if "Fusion.globalContent=" in text:
        s = seg_avalon(text)
        if s is not None:
            return "avalon", s
    if "__NEXT_DATA__" in text and "homeDetails" in text:
        s = seg_trulia(text)
        if s is not None:
            return "trulia", s
    if "self.__next_f.push" in text:
        s = seg_apartmentlist(text)
        if s is not None:
            return "apartmentlist", s
        s = seg_greystar(text)
        if s is not None:
            return "greystar", s
    if "<" not in text[:2000]:
        return "not_html", []
    return "generic", seg_generic(text)


# ------------------------------------------------------------------ classification

NEG = re.compile(r"(?i)\b(no|not|without|non|isn'?t|aren'?t|lacks?)\b[^,.;]{0,25}$")
NEARBY = re.compile(r"(?i)\b(near(by)?|close to|walk(ing)? (to|distance)|blocks?|minutes?|mins?|across from|steps (from|to|away)|public|municipal|"
                    r"neighbou?rhood|around the corner|local|access to nearby|miles?)\b")


def find(segs, rx, *, veto=None, desc_nearby=False, allow_desc=True):
    """All (seg, match) hits. List items first. Free-text hits are dropped when negated, or (desc_nearby) when the
    sentence is about the surroundings rather than the building."""
    hits = []
    for seg in segs:
        kind, label, text = seg[:3]
        if kind == "field":
            continue
        if kind == "desc" and not allow_desc:
            continue
        for m in re.finditer(rx, text):
            if veto and re.search(veto, text[max(0, m.start() - 30):m.end() + 30]):
                continue
            if NEG.search(text[:m.start()]):
                continue
            if kind == "desc" and desc_nearby and NEARBY.search(text):
                continue
            hits.append((seg, m))
            break
    hits.sort(key=lambda h: 0 if h[0][0] == "list" else 1)
    return hits


def ev(seg, m=None, width=170) -> str:
    kind, label, text = seg[:3]
    if m is not None and len(text) > width:
        a = max(0, m.start() - width // 2)
        text = ("…" if a else "") + text[a:a + width] + ("…" if a + width < len(text) else "")
    return f"[{label}] {text[:width + 2]}"


RX = {
    "pool": r"(?i)\b(swimming |lap |plunge |saltwater |salt water |infinity )?pools?\b|\bpoolside\b",
    "pool_veto": r"(?i)pool table|car ?pool|whirlpool|pool view|billiard|pool hall|ping pong",
    "gym": r"(?i)\bgym(nasium)?\b|fitness (cent(er|re)|studio|room|club|facilit|area|space|gym)|exercise (room|facilit)|health club|work-?out (room|facilit|studio)|\bfitness\b",
    "doorman": r"(?i)\bdoor ?(man|men|person|people)\b|\bconcierge\b|attended lobby|lobby attendant|front desk (attendant|staff|service)|24[- ]?h(ou)?r front desk",
    "doorman_veto": r"(?i)virtual door|package concierge|concierge trash|trash concierge|valet trash|video door|virtual concierge|electronic door|cyber ?door|tele-?door",
    "h24": r"(?i)24[- /]?(h(ou)?rs?|/ ?7|x7)|twenty[- ]four hour|full[- ]time door|round[- ]the[- ]clock",
    "part": r"(?i)part[- ]time|evening door|daytime door|weekend door|limited hours",
    "access": r"(?i)key ?-?fob|\bfob\b|intercom|gated (entry|entrance|community|access|complex|property|building)|\bgated\b|secur(e|ed|ity) (entry|entrance|access|building|lobby|door)|"
              r"controlled[- ]access|access[- ]control|controlled entry|limited access|video (door|entry|security)|virtual door ?man|buzzer|keyless (building )?entry|butterfly ?mx|key ?card access|latch (access|entry)",
    "access_veto": r"(?i)gated (parking|lot|garage)",
    "dog_run": r"(?i)\bdog[- ]?run\b",
    "dog_park": r"(?i)\b(dog|bark|pet|pooch|paw)[- ]?park\b|off[- ]leash|pet (play )?area|dog (play )?area|pet relief|dog relief",
    "pet_spa": r"(?i)\b(pet|dog|paw)[- ]?(spa|salon)\b|grooming",
    "dog_wash": r"(?i)\b(dog|pet|paw)[- ]?wash|washing station|pet bath|dog bath",
    "laundry_in": r"(?i)in[- ]?(unit|home|suite|apartment) (laundry|washer|w/?d)|(washer|w/?d|laundry)[^.;|]{0,30}\bin[- ](every |each |the |your )?(unit|home|apartment|suite|residence)|in[- ]unit w/?d|"
                  r"washer ?(/|&|and) ?dryer in|full[- ]size(d)? washer|private (laundry|washer)|own (washer|laundry)|personal washer",
    "laundry_wd_list": r"(?i)^(washer|dryer|washer ?[/&,] ?dryer|washer and dryer|washer: |dryer: |stack(ed|able) washer.*|full[- ]size(d)? washer.*|front[- ]load.*washer.*)\s*$",
    "laundry_site": r"(?i)on[- ]?site laundry|laundry (room|facilit|cent(er|re)|lounge)|laundry in (the )?(building|basement)|shared laundry|common laundry|community laundry|coin[- ]?(op|laundry)|card[- ]operated laundry|"
                    r"laundry on (every|each|site|premises)|laundry (is )?on[- ]site|\blaundry\b",
    "laundry_veto": r"(?i)hook-?ups?|laundromat|laundry service|dry clean",
    "roof": r"(?i)roof[- ]?(top|deck|terrace|garden|lounge)|\brooftop\b|sun ?deck|court ?yard|outdoor (space|lounge|kitchen|dining|terrace|area|living|seating|grill|fire|entertain|amenit)|"
            r"\bbbq\b|barbe(c|q)ue|grill(s|ing)? (area|station)|\bbbq/grill\b|fire ?pit|community garden|\bgarden\b|common (terrace|patio)|shared (terrace|patio|yard|backyard|outdoor)|landscaped|picnic|pergola|cabana|green space",
    "roof_veto": r"(?i)garden[- ]style|garden apartment|garden level|garden city|garden state|gardens? (blvd|ave|rd|st|pkwy)|kew gardens|botanic|olive garden|garden tub",
    "balcony": r"(?i)\bbalcon(y|ies)\b|\bpatio\b|private (terrace|outdoor|deck|yard|backyard|roof)|\bterrace\b|juliet|\blanai\b",
    "balcony_veto": r"(?i)roof[- ]?(top)? terrace|common terrace|shared terrace|terrace (ave|st|rd|pl|blvd|court|ct)\b|sky terrace|amenity terrace|pool terrace|poolside terrace|community terrace|count: 0",
    "package": r"(?i)\bpackage|\bparcel|amazon (hub|locker)|\bluxer\b|mail ?room",
    "package_veto": r"(?i)technology package|tech package|cable package|package (deal|includes|of )|appliance package|finish package|amenity package|internet package|utility package|media package",
    "cowork": r"(?i)co-?work|business (cent(er|re)|lounge)|conference (room|cent)|work[- ]?(lounge|space|pods?|stations?)|work[- ]from[- ]home (lounge|space|suite)|\blounge\b|club ?(house|room)|community room|"
              r"media room|resident(s|'s|s')? (lounge|club)|internet cafe|cyber ?cafe|\blibrary\b|game ?room|screening room|party room|social (room|club|lounge)|coffee bar|private offices",
    "cowork_veto": r"(?i)lounge chair|public library|library (is|within)|outdoor lounge|pool lounge|chaise|lounge seating",
    "elevator": r"(?i)\belevators?\b|\belev\b|\blift\b",
    "elevator_veto": r"(?i)walk[- ]?up|ski lift",
}

PARK_RX = [
    ("garage", r"(?i)garage_lot|\bgarages?\b|underground parking|indoor parking|parking (deck|structure)|covered garage|subterranean"),
    ("gated_lot", r"(?i)gated (parking|lot|surface)|secur(e|ed) (parking )?lot|fenced (parking|lot)"),
    ("covered", r"(?i)covered_lot|covered parking|covered (spot|space)|car ?ports?|\bcovered\b"),
    ("open_lot", r"(?i)surface_lot|parking lot|surface (lot|parking)|off[- ]street|uncovered|outdoor parking|drive ?way|open lot|on[- ]site lot|open parking"),
    ("street_only", r"(?i)parking category: street|street parking|on[- ]street|street permit"),
]
PARK_ANY = r"(?i)\bparking\b|\bgarages?\b|car ?ports?|parking category"
PARK_VETO = r"(?i)garage door|bike garage|bicycle parking|bike parking|garage sale|no parking|parking category: (none|other)|guest parking|visitor parking|stroller parking"
PRANK = ["garage", "gated_lot", "covered", "open_lot", "street_only", "parking_type_unknown"]


def classify(segs_by_url: list[tuple[str, list]]):
    """segs_by_url: [(url, segs)] in priority order. Returns {col: (value, evidence, url)}."""
    flat = [(k, lab, t, u) for u, segs in segs_by_url for (k, lab, t) in segs]
    R: dict[str, tuple] = {}

    def simple(col, key, **kw):
        hs = find(flat, RX[key], veto=RX.get(key + "_veto"), **kw)
        if hs:
            seg, m = hs[0]
            R[col] = ("yes", ev(seg, m), seg[3])
        return hs

    # ---- pool
    hs = find(flat, RX["pool"], veto=RX["pool_veto"], desc_nearby=True)
    if hs:
        kinds, evs = set(), []
        for seg, m in hs:
            t = seg[2]
            w = t[max(0, m.start() - 60):m.end() + 40]
            k = set()
            if re.search(r"(?i)indoor\s*(/|&|and|or)\s*outdoor|outdoor\s*(/|&|and|or)\s*indoor", w):
                k = {"indoor", "outdoor"}
            else:
                if re.search(r"(?i)\bindoor\b", w):
                    k.add("indoor")
                if re.search(r"(?i)\boutdoor\b|roof[- ]?top|\broof\b|open[- ]air", w):
                    k.add("outdoor")
            if k - kinds or not evs:
                evs.append((ev(seg, m), seg[3]))
            kinds |= k
        val = "both" if kinds == {"indoor", "outdoor"} else (kinds.pop() if kinds else "yes_type_unknown")
        R["pool"] = (val, " || ".join(e for e, _ in evs[:2]), evs[0][1])

    simple("gym", "gym", desc_nearby=True)

    # ---- doorman / concierge
    hs = find(flat, RX["doorman"], veto=RX["doorman_veto"])
    if hs:
        val, pick = "yes", hs[0]
        for seg, m in hs:
            w = seg[2][max(0, m.start() - 45):m.end() + 45]
            if re.search(RX["h24"], w):
                val, pick = "24h", (seg, m)
                break
        if val == "yes":
            for seg, m in hs:
                if re.search(RX["part"], seg[2][max(0, m.start() - 45):m.end() + 45]):
                    val, pick = "part_time", (seg, m)
                    break
        R["doorman_or_concierge"] = (val, ev(*pick), pick[0][3])

    simple("controlled_access", "access")

    # ---- parking
    best, fee = None, None
    for seg in flat:
        kind, lab, t, u = seg
        if kind == "field" or not re.search(PARK_ANY, t) or re.search(PARK_VETO, t):
            continue
        if kind == "desc" and (NEARBY.search(t) or NEG.search(t[:re.search(PARK_ANY, t).start()])):
            continue
        typ, mm = "parking_type_unknown", re.search(PARK_ANY, t)
        for name, rx in PARK_RX:
            m = re.search(rx, t)
            if m:
                typ, mm = name, m
                break
        cand = (PRANK.index(typ), 0 if kind == "list" else 1)
        if best is None or cand < best[0]:
            best = (cand, typ, ev(seg, mm), u)
        if fee is None and not re.search(r"(?i)deposit|one[- ]time|per (day|night|hour)|daily|hourly|ev charging", t):
            amts = []
            for a in re.finditer(r"\$\s*([\d,]+(?:\.\d+)?)", t):
                tail = t[a.end():a.end() + 25]
                if re.search(r"(?i)^\s*(/|per|a|each)?\s*(mo\b|month)|monthly", tail) or re.search(r"(?i)monthly|/ ?mo|per month|space_fee|a month", t):
                    v = float(a.group(1).replace(",", ""))
                    if 10 <= v <= 900:
                        amts.append(v)
            if amts:
                lo = min(amts)
                fee = (str(int(lo)) if lo == int(lo) else f"{lo:.2f}", ev(seg, None, 230), u)
    if best:
        R["gated_or_garage_parking"] = (best[1], best[2], best[3])
    if fee:
        R["parking_fee_monthly"] = fee

    # ---- dog amenities
    dogs, devs, durl = [], [], ""
    for name, key in (("dog run", "dog_run"), ("dog park", "dog_park"), ("pet spa", "pet_spa"), ("dog wash", "dog_wash")):
        hs = find(flat, RX[key], desc_nearby=True)
        if hs:
            dogs.append(name)
            e = ev(*hs[0])
            if e not in devs:
                devs.append(e)
            durl = durl or hs[0][0][3]
    if dogs:
        R["dog_amenities"] = ("; ".join(dogs), " || ".join(devs[:3]), durl)

    # ---- laundry
    hs = find(flat, RX["laundry_in"], veto=r"(?i)hook-?ups?")
    if not hs:
        hs = [(s, re.search(RX["laundry_wd_list"], s[2])) for s in flat if s[0] == "list" and re.search(RX["laundry_wd_list"], s[2])
              and re.search(r"(?i)unit|appliance|feature|interior", s[1])]
    if hs:
        R["in_unit_laundry"] = ("yes", ev(*hs[0]), hs[0][0][3])
    else:
        hs = find(flat, RX["laundry_site"], veto=RX["laundry_veto"], desc_nearby=True)
        if hs:
            R["in_unit_laundry"] = ("on_site_only", ev(*hs[0]), hs[0][0][3])

    simple("roof_deck_or_outdoor_space", "roof", desc_nearby=True)
    simple("balcony_some_units", "balcony")
    simple("package_room", "package")
    simple("coworking_or_lounge", "cowork", desc_nearby=True)
    simple("elevator_stated", "elevator")

    # ---- numbers and names
    for seg in flat:
        kind, lab, t, u = seg
        if kind == "field":
            col = {"year_built": "year_built", "year_remodeled": "year_renovated", "total_units_count": "unit_count",
                   "floors": "total_floors", "pmc_display_name": "management_company"}.get(lab)
            if col and col not in R:
                R[col] = (t, f"[page data] {lab}: {t}", u)
            continue
        if "year_built" not in R:
            m = re.search(r"(?i)^year built: ((?:18|19|20)\d\d)$", t) or re.search(r"(?i)\b(?:built|constructed|completed|opened) in ((?:18|19|20)\d\d)\b", t)
            if m:
                R["year_built"] = (m.group(1), ev(seg, m), u)
        if "year_renovated" not in R:
            m = re.search(r"(?i)\b(?:renovated|remodeled|rehabbed|refurbished|updated) in ((?:19|20)\d\d)\b", t)
            if m:
                R["year_renovated"] = (m.group(1), ev(seg, m), u)
        if "total_floors" not in R:
            m = re.search(r"(?i)\b(\d{1,2})[- ]?stor(?:y|ey|ies)\b(?=[^.|]{0,25}(building|tower|high[- ]?rise|mid[- ]?rise|communit|elevator|complex|residen|luxury|rental|apartment))", t)
            if m and 2 <= int(m.group(1)) <= 90:
                R["total_floors"] = (m.group(1), ev(seg, m), u)
        if "unit_count" not in R:
            m = re.search(r"(?i)\b(\d{2,4})[- ]?(?:unit|apartment|residence|home)s?\b(?=[^.|]{0,12}(building|communit|complex|tower|propert|rental|luxury))", t) \
                or re.search(r"(?i)^(?:number of units|units|total units): (\d{1,4})$", t)
            if m and "$" not in t[max(0, m.start() - 2):m.start()]:
                R["unit_count"] = (m.group(1), ev(seg, m), u)
        if "management_company" not in R and kind == "desc":
            m = re.search(r"\b(?:[Mm]anaged|[Oo]perated) by ((?:[A-Z][\w&.'-]*)(?: (?:[A-Z&][\w&.'-]*|of|and)){0,5})", t)
            if m and not re.search(r"(?i)^(the|our|a|an|owner|landlord)\b", m.group(1)):
                R["management_company"] = (m.group(1).strip(" ."), ev(seg, m), u)
    return R


# ------------------------------------------------------------------ inputs

def url_index() -> dict[str, tuple[str, str]]:
    """url -> (cached path, retrieved_at) from every *.meta.json under the listing / management / own raw folders."""
    idx = {}
    for d in sorted(lib.RAW.iterdir()):
        if not d.is_dir() or not re.match(r"(apartmentlist|zumper|trulia|community_facts|building_amenities|mgmt_|region_)", d.name):
            continue
        for mp in d.glob("*.meta.json"):
            try:
                m = json.loads(mp.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if m.get("status") == 200 and m.get("url") and m.get("path"):
                idx[m["url"].rstrip("/")] = (m["path"], m.get("retrieved_at", ""))
    return idx


_rp: dict[str, object] = {}
_last: dict[str, float] = {}
_blocked: dict[str, str] = {}


def robots_ok(url: str) -> tuple[bool, float, str]:
    p = urlparse(url)
    host = p.netloc
    if host not in _rp:
        try:
            _wait(host, MIN_DELAY)
            body, meta = lib.cached_get(f"{p.scheme}://{host}/robots.txt", SRC, ext="txt", timeout=30)
        except Exception as e:  # noqa: BLE001
            _rp[host] = None
            return False, MIN_DELAY, f"robots.txt fetch error: {str(e)[:80]}"
        if meta["status"] in (401, 403, 429):
            _rp[host] = None
            return False, MIN_DELAY, f"robots.txt http {meta['status']}"
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.decode("utf8", "replace").splitlines() if meta["status"] == 200 else [])
        _rp[host] = rp
    rp = _rp[host]
    if rp is None:
        return False, MIN_DELAY, "robots.txt unavailable"
    delay = MIN_DELAY
    for ua in CLAUDE_UAS + ["*"]:
        if not rp.can_fetch(ua, url):
            return False, delay, f"robots.txt disallows for {ua}"
        cd = rp.crawl_delay(ua)
        if cd:
            delay = max(delay, float(cd))
    return True, delay, ""


def _wait(host: str, delay: float) -> None:
    w = _last.get(host, 0) + delay - time.time()
    if w > 0:
        time.sleep(w)
    _last[host] = time.time()


def fetch_one(url: str):
    """(text, meta) or (None, reason). One polite fetch, cached in raw/building_amenities/."""
    host = urlparse(url).netloc
    if host in _blocked:
        return None, _blocked[host]
    ok, delay, why = robots_ok(url)
    if not ok:
        return None, why
    _wait(host, delay)
    try:
        body, meta = lib.cached_get(url, SRC, ext="html", timeout=45, retries=1)
    except Exception as e:  # noqa: BLE001
        return None, f"fetch error: {str(e)[:100]}"
    if meta["status"] in (403, 429) or re.search(rb"(?i)captcha|px-captcha|are you a robot|access denied", body[:20000]) and len(body) < 30000:
        _blocked[host] = f"blocked: http {meta['status']} on {host}; host skipped for the rest of the run"
        return None, _blocked[host]
    if meta["status"] != 200:
        return None, f"http {meta['status']}"
    return body.decode("utf8", "replace"), meta


CF_MAP = {"pool": "pool", "gym": "gym", "controlled_access": "controlled_access", "dog_amenities": "dog_park_pet_spa",
          "package_room": "package_room", "coworking_or_lounge": "coworking", "management_company": "manager",
          "year_built": "year_built", "total_floors": "floors_total"}


def cf_value(col: str, v: str, snippet: str):
    v = v.strip()
    if not v or v.lower() in ("unknown", "none stated", "no"):
        return None
    if col == "pool":
        lv = v.lower()
        return ("both" if "indoor" in lv and "outdoor" in lv else "indoor" if lv.startswith("indoor")
                else "outdoor" if lv.startswith("outdoor") else "yes_type_unknown")
    if col == "dog_amenities":
        names = [n for n, k in (("dog run", "dog_run"), ("dog park", "dog_park"), ("pet spa", "pet_spa"), ("dog wash", "dog_wash"))
                 if re.search(RX[k], snippet)]
        return "; ".join(names) if names else None
    if col in ("management_company", "year_built", "total_floors"):
        return v
    return "yes" if v.lower().startswith("yes") else None


def process(key: str, urows: list[dict], lrows: list[dict], cf: dict, idx: dict, allow_fetch: bool) -> dict:
    first = urows[0]
    row = {c: "" for c in COLS}
    row.update(addr_key=key, building_name=next((r["building_name"] for r in urows if r["building_name"]), ""),
               address=first["address"], city=first["city"], state=first["state"], zip=first["zip5"] or first["zip"],
               pass_units=len(urows), source_sites="; ".join(dict.fromkeys(r["source_site"] for r in urows)))
    # pages, in priority order: building pages, pass rows' pages, sibling rows' pages, also_seen_at
    pages: list[tuple[str, str, str]] = []          # (url, path, retrieved_at)
    seen_paths = set()

    def add(url, path="", when=""):
        if not path and url:
            hit = idx.get(url.rstrip("/"))
            if hit:
                path, when = hit
        if path and path not in seen_paths and (ROOT / path).exists():
            seen_paths.add(path)
            if not when:
                mp = (ROOT / path).with_suffix(".meta.json")
                if mp.exists():
                    try:
                        mm = json.loads(mp.read_text())
                        when, url = mm.get("retrieved_at", ""), url or mm.get("url", "")
                    except json.JSONDecodeError:
                        pass
            pages.append((url, path, when))

    crow = None
    for r in urows:
        crow = crow or cf.get((r.get("building_url") or "").rstrip("/"))
    if crow:
        for u in (crow.get("pages_read") or "").split(" | "):
            add(u.strip())
    for r in urows + lrows:
        if r.get("building_url"):
            add(r["building_url"])
    for r in urows + lrows:
        # the page the row was read from; its url is in the cache meta (a unit row's url may be a deep link)
        add("", r.get("raw_path", ""), "")
    for r in urows + lrows:
        for u in re.split(r"\s*[|;]\s*|\s+", r.get("also_seen_at") or ""):
            if u.startswith("http"):
                add(u)

    notes, segs_by_url, parsers = [], [], []

    def parse(url, path):
        try:
            text = (ROOT / path).read_text(encoding="utf8", errors="replace")
        except OSError:
            return 0
        name, segs = page_segments(text)
        if name == "generic" and re.search(r"(trulia|zumper|apartmentlist)\.", url or ""):
            return 0                                 # an aggregator page without its data block: nav text only
        parsers.append(name)
        if segs:
            segs_by_url.append((url or path, segs))
        return sum(1 for s in segs if s[0] == "list")

    n_items = 0
    for url, path, when in pages:
        n_items += parse(url, path)
    R = classify(segs_by_url)

    fetched = ""
    if allow_fetch and not any(c in R for c in VALUE_COLS[:13]) and n_items == 0:
        cand = next((u for u in [first.get("building_url"), first.get("url")] if u and u.rstrip("/") not in idx), "")
        if cand:
            text, meta = fetch_one(cand)
            if text is None:
                notes.append(f"no cached page with amenities; fetch of {cand} not done: {meta}")
            else:
                fetched = cand
                pages.append((cand, meta["path"], meta["retrieved_at"]))
                idx[cand.rstrip("/")] = (meta["path"], meta["retrieved_at"])
                n_items += parse(cand, meta["path"])
                R = classify(segs_by_url)
        else:
            notes.append("cached page(s) carry no amenity list; no other page URL known for this building")

    # community_facts overlay (management-site communities)
    if crow:
        for col, fact in CF_MAP.items():
            if col in R:
                continue
            v = cf_value(col, crow.get(fact, ""), crow.get(fact + "_snippet", ""))
            if v:
                R[col] = (v, "[community_facts.csv] " + clean(crow.get(fact + "_snippet", ""))[:200], crow.get(fact + "_source_url") or crow.get("community_url"))
        if "gated_or_garage_parking" not in R and crow.get("parking_type", "").strip():
            pt = crow["parking_type"].lower()
            typ = ("garage" if "garage" in pt else "gated_lot" if "gated" in pt else "covered" if "covered" in pt
                   else "open_lot" if "open lot" in pt or "surface" in pt else "street_only" if "street" in pt else "parking_type_unknown")
            R["gated_or_garage_parking"] = (typ, "[community_facts.csv] " + clean(crow.get("parking_type_snippet", ""))[:200],
                                            crow.get("parking_type_source_url") or crow.get("community_url"))
        if "parking_fee_monthly" not in R and crow.get("parking_fee_monthly", "").strip():
            nums = [float(x) for x in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)", crow["parking_fee_monthly"]) if 10 <= float(x) <= 900]
            if nums:
                lo = min(nums)
                R["parking_fee_monthly"] = (str(int(lo)) if lo == int(lo) else f"{lo:.2f}",
                                            f"[community_facts.csv] parking_fee_monthly: {crow['parking_fee_monthly']} | " + clean(crow.get("parking_fee_monthly_snippet", ""))[:170],
                                            crow.get("parking_fee_monthly_source_url") or crow.get("community_url"))
    # harvest-row fallbacks (values the harvester read from the same listing page)
    if "total_floors" not in R:
        r = next((r for r in urows + lrows if (r.get("building_floors") or "").strip().isdigit()), None)
        if r:
            R["total_floors"] = (r["building_floors"].strip(), f"[harvest row {r['source_site']}] building_floors: {r['building_floors']}", r.get("building_url") or r["url"])

    used = {}
    for col in VALUE_COLS:
        if col in R:
            v, e, u = R[col]
            row[col], row[col + "_evidence"] = v, e
            used[col] = u
        else:
            row[col] = "" if col in BLANK_WHEN_MISSING else "no_mention"
    urls = list(dict.fromkeys(used.values()))
    all_pages = list(dict.fromkeys(u for u, _, _ in pages if u))
    main = max(urls, key=lambda u: sum(1 for x in used.values() if x == u)) if urls else (all_pages[0] if all_pages else first.get("building_url") or first["url"])
    row["source_url"] = main
    if len(urls) > 1 or len(all_pages) > 1:
        row["sources_json"] = json.dumps({"pages_read": all_pages, "by_column": {c: u for c, u in used.items() if u != main}}, ensure_ascii=False)
    row["pages_parsed"] = len(parsers)
    row["amenity_items_seen"] = n_items
    row["fetched_new_page"] = fetched
    if any(r["source_site"] == "trulia" for r in urows) and len({r["source_site"] for r in urows + lrows}) == 1:
        notes.append("Trulia unit listing only: features block is short, most values come from the description text")
    row["notes"] = " | ".join(notes)
    row["retrieved_at"] = max((w for _, _, w in pages if w), default="")
    return row


def write(rows: dict[str, dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])
    tmp.replace(OUT)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="reprocess every passing building (default: only new addr_keys)")
    ap.add_argument("--no-fetch", action="store_true", help="cache only")
    a = ap.parse_args()

    units = [r for r in csv.DictReader(open(ROOT / "data" / "units.csv", encoding="utf8")) if r["unit_status"] == "pass"]
    by_key = defaultdict(list)
    for r in units:
        by_key[r["addr_key"]].append(r)
    sib = defaultdict(list)
    lp = ROOT / "data" / "listings.csv"
    if lp.exists():
        for r in csv.DictReader(open(lp, encoding="utf8")):
            if r["addr_key"] in by_key:
                sib[r["addr_key"]].append(r)
    cf = {}
    cp = ROOT / "data" / "reference" / "community_facts.csv"
    if cp.exists():
        cf = {c["community_url"].rstrip("/"): c for c in csv.DictReader(open(cp, encoding="utf8")) if c["community_url"]}
    rows = {}
    if OUT.exists():
        rows = {r["addr_key"]: r for r in csv.DictReader(open(OUT, encoding="utf8"))}
    todo = [k for k in by_key if a.rebuild or k not in rows]
    print(f"passing buildings: {len(by_key)}; already in csv: {len(rows)}; to process: {len(todo)}")
    if not todo:
        return
    idx = url_index()
    for i, k in enumerate(todo, 1):
        upaths = {r["raw_path"] for r in by_key[k]}
        lrows = [r for r in sib.get(k, []) if r["raw_path"] not in upaths]
        seen, lr = set(), []
        for r in lrows:                                       # one sibling row per cached page
            if r["raw_path"] not in seen:
                seen.add(r["raw_path"])
                lr.append(r)
        rows[k] = process(k, by_key[k], lr[:12], cf, idx, not a.no_fetch)
        if i % 50 == 0:
            write(rows)
            print(f"  {i}/{len(todo)}")
    write(rows)
    cur = [rows[k] for k in by_key]
    print(f"written {len(rows)} rows ({len(cur)} currently passing) -> {OUT.relative_to(ROOT)}")
    for c in VALUE_COLS:
        n = sum(1 for r in cur if r[c] not in ("", "no_mention"))
        print(f"  {c:28s} {n:4d}  {100 * n / len(cur):5.1f}%")
    print("  fetched:", sum(1 for r in cur if r["fetched_new_page"]))


if __name__ == "__main__":
    main()
