"""building_contacts: one leasing contact row per ranked building.

    python3 scripts/building_contacts.py                 # offline: parse the pages already cached under raw/
    python3 scripts/building_contacts.py --fetch         # then one fetch per building that still has no phone
    python3 scripts/building_contacts.py --fetch --limit 20
    python3 scripts/building_contacts.py --fetch --upgrade-tracking   # also fetch the own site of tracking-only rows

Reads (never writes) data/ranked_units.csv, data/needs_confirmation.csv, data/evidence/facts_batch_*.csv,
data/reference/community_facts.csv and the raw/ caches. Writes data/reference/building_contacts.csv (rebuilt whole
on every run, so re-running never duplicates rows), raw/building_contacts/ (fetched pages, `_state.json`,
`_refused_hosts.json`) and nothing else.

What counts as a contact
  * A business leasing number published on a listing or building page. Never a private person's number or name:
    a unit listed by a person with no brokerage gets contact_kind = individual owner, a blank phone and the
    listing URL. Individual agents' names are not stored; a brokerage's name and its published number are.
  * Apartment List shows a tracking number on the page (`phone`) and also carries the number the property supplied
    (`original_phone`); the supplied number is used. Trulia building pages and Zumper `(844) ... ext.` numbers are
    listing-site tracking numbers and are flagged in `note`.
  * Preference order: the building's own site > Apartment List supplied number > Zumper building page >
    Trulia / Zillow building page (tracking) > brokerage number on a single-unit listing > Zumper proxy number.

Fetch rules (CLAUDE.md rule 3 and the standing instruction)
  * robots.txt is read first for every new host; groups naming Claude apply and override `*`.
  * One refusal (401/403/429, CAPTCHA or bot wall, on robots.txt or on the page) ends all requests to that host.
    It is written to raw/building_contacts/_refused_hosts.json at once and honoured on every later run. Hosts
    that other harvests recorded as blocked (raw/*/_blocked_hosts.json, 403/429 lines in raw/*/_index.jsonl)
    are never requested either.
  * Never requested: trulia.com, zillow.com, streeteasy.com, apartments.com, craigslist.org, yelp.com.
  * One page per building (its own site's home or contact page, else its Apartment List / Zumper page).
"""
from __future__ import annotations

import argparse
import csv
import glob
import html as htmllib
import json
import re
import sys
import urllib.robotparser
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse, urlunparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import DATA, RAW, ROOT, USER_AGENT, cached_get, now_iso  # noqa: E402

csv.field_size_limit(10 ** 9)

OUT = DATA / "reference" / "building_contacts.csv"
SRC = "building_contacts"
STATE_F = RAW / SRC / "_state.json"
REFUSED_F = RAW / SRC / "_refused_hosts.json"
COLS = ["building_id", "addr_key", "building_name", "address", "leasing_phone", "leasing_phone_source_url",
        "leasing_url", "office_hours", "manager_name", "contact_kind", "retrieved_at", "basis", "note"]

NEVER = ("trulia.com", "zillow.com", "streeteasy.com", "apartments.com", "craigslist.org", "yelp.com",
         "hotpads.com", "realtor.com", "rent.com", "renthop.com")
# Hosts that are not a building's own leasing site (aggregators, record sources, news, application portals).
NOT_OWN = re.compile(
    r"trulia|apartmentlist|zumper|zillow|streeteasy|apartments\.com|hotpads|craigslist|yelp|openigloo|sightmap|"
    r"\.gov$|\.gov\.|cityofnewyork|census|appfolio|managebuilding|jerseydigs|newyorkyimby|hartfordbusiness|"
    r"change\.org|connectcre|google\.|facebook|instagram|youtube|linkedin|niche\.com|city-data|wikipedia|"
    r"patch\.com|nj\.com|bisnow|therealdeal|rentcafe\.com$|bbb\.org|twitter|x\.com|loopnet|costar|\.us$|"
    r"propertyshark|emporis|skyscraper|multihousingnews|globest|businesswire|prnewswire|rew-online|roi-nj|"
    r"tapinto|northjersey|lohud|ctinsider|ctpost|stamfordadvocate|newsday|nytimes|commercialobserver", re.I)
BUSINESS = re.compile(r"\b(llc|l\.l\.c|inc|corp|co\b|company|realty|management|mgmt|properties|property|group|"
                      r"associates|assoc|partners|residential|communities|apartments|holdings|development|"
                      r"capital|equities|trust|lp|living|homes|rentals|real estate|enterprises|urby|"
                      r"bozzuto|greystar|avalon|windsor|veris|lefrak)\b", re.I)
TRACK = "listing-site tracking number"
LOCAL_CODES = set("212 315 332 347 363 516 518 585 607 631 646 680 716 718 838 845 914 917 929 934 "
                  "201 551 609 640 732 848 856 862 908 973 203 475 860 959".split())
DEC = json.JSONDecoder()


# ------------------------------------------------------------------------------------------------- helpers
def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def norm_phone(s) -> str:
    """'(xxx) xxx-xxxx' with an optional ' ext. N'; '' when it is not a plausible US number."""
    if not s:
        return ""
    s = str(s)
    ext = ""
    m = re.search(r"(?:ext\.?|x)\s*(\d{1,6})\s*$", s, re.I)
    if m:
        ext, s = m.group(1), s[:m.start()]
    d = re.sub(r"\D", "", s)
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    elif len(d) > 10 and not ext:       # Apartment List stores "<10 digits><extension>"
        d, ext = d[:10], d[10:]
    if len(d) != 10 or d[0] in "01" or d[3] in "01" or len(set(d)) < 3:
        return ""
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" + (f" ext. {ext}" if ext else "")


def is_tollfree(p: str) -> bool:
    return p[1:4] in ("800", "833", "844", "855", "866", "877", "888")


def host_of(u: str) -> str:
    return urlparse(u.strip()).netloc.lower()


def norm_url(u: str) -> str:
    """Index key: no scheme, no www, no query, no trailing slash."""
    p = urlparse(u.strip())
    return (p.netloc.lower().removeprefix("www.") + p.path.rstrip("/")).lower()


def clean_url(u: str) -> str:
    """Drop the tracking query string that aggregators append to a property's site link."""
    u = htmllib.unescape(u.strip().replace("\\u0026", "&").replace(" ", ""))
    p = urlparse(u)
    if not p.scheme or not p.netloc:
        return ""
    return urlunparse((p.scheme, p.netloc, p.path or "/", "", "", ""))


def is_own(u: str) -> bool:
    h = host_of(u)
    return bool(h) and not NOT_OWN.search(h)


def urls_in(s: str) -> list[str]:
    return [u.rstrip(".,;)") for u in re.findall(r"https?://[^\s;|,\"'<>]+", s or "")]


def day_range(days: list[str]) -> str:
    return days[0] if len(days) == 1 else f"{days[0]}-{days[-1]}"


def compress_hours(items: list[tuple[str, str]]) -> str:
    """[(day, 'open-close')] -> 'Mon-Fri 9am-5pm; Sat 10am-4pm' (consecutive days with equal hours are merged)."""
    out, run, cur = [], [], None
    for d, h in items:
        if h == cur:
            run.append(d)
        else:
            if run:
                out.append(f"{day_range(run)} {cur}")
            run, cur = [d], h
    if run:
        out.append(f"{day_range(run)} {cur}")
    return "; ".join(out)


# ------------------------------------------------------------------------------------------------- cache index
def build_index():
    """norm_url -> (path, url, retrieved_at) for every cached 200; plus hosts that refused someone before."""
    idx, refused = {}, {}
    for f in sorted(glob.glob(str(RAW / "*" / "_index.jsonl"))) + sorted(glob.glob(str(RAW / "*" / "*" / "_index.jsonl"))):
        with open(f, errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                u, st = d.get("url") or "", d.get("status")
                if st in (403, 429) and u:
                    refused.setdefault(host_of(u), f"HTTP {st} recorded in {Path(f).parent.name}/_index.jsonl")
                if st == 200 and d.get("path") and (ROOT / d["path"]).exists():
                    k = norm_url(u)
                    if k not in idx or (d.get("retrieved_at") or "") > idx[k][2]:
                        idx[k] = (d["path"], u, d.get("retrieved_at") or "")
    for f in glob.glob(str(RAW / "*" / "_blocked_hosts.json")):
        try:
            for h, why in json.loads(Path(f).read_text()).items():
                refused.setdefault(h.lower(), f"{why} ({Path(f).parent.name})")
        except (json.JSONDecodeError, AttributeError):
            pass
    return idx, refused


def meta_of(path: str) -> dict:
    mp = ROOT / (path.rsplit(".", 1)[0] + ".meta.json")
    if mp.exists():
        try:
            return json.loads(mp.read_text())
        except json.JSONDecodeError:
            pass
    return {}


# ------------------------------------------------------------------------------------------------- parsers
# Every parser returns a list of candidate dicts:
#   rank (lower wins), phone, src (page URL), site (own-site link found on the page), hours, manager, kind, note
def cand(rank, page_url, **kw):
    c = {"rank": rank, "phone": "", "src": page_url, "site": "", "hours": "", "manager": "", "kind": "", "note": ""}
    c.update(kw)
    return c


def al_flight(text: str) -> str:
    out = []
    for c in re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', text):
        try:
            out.append(json.loads(c))
        except json.JSONDecodeError:
            pass
    return "".join(out)


def single_lister_listing(listing: dict) -> bool:
    """An Apartment List listing that is one lister's own unit(s), not a property with a leasing office: the page gives
    no unit count for the building, no website, at most three units, and a title that is a street address."""
    tu = listing.get("total_units_count")
    try:
        many = tu is not None and float(tu) > 4
    except (TypeError, ValueError):
        many = False
    few = len(listing.get("available_units") or []) <= 3
    by_address = bool(re.match(r"\s*\d", str(listing.get("display_name") or listing.get("street_address") or "")))   # titled by its street address, not a property name
    return not many and few and by_address and not str(listing.get("website_url") or "").strip()


def parse_apartmentlist(text: str, url: str):
    fl = al_flight(text)
    best = None
    for m in re.finditer(r'"listing":\{"rental_id"', fl):
        try:
            o, _ = DEC.raw_decode(fl, m.start() + 10)
        except json.JSONDecodeError:
            continue
        if "available_units" in o and (best is None or len(o) > len(best)):
            best = o
    if best is None:
        return []
    shown, orig = norm_phone(best.get("phone")), norm_phone(best.get("original_phone"))
    site = clean_url(best.get("website_url") or "")
    hours = ""
    oh = best.get("office_hours_this_week")
    if isinstance(oh, dict) and oh:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz, items = ZoneInfo("America/New_York"), []
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            v = oh.get(day)
            if isinstance(v, list) and len(v) == 2 and v[0] and v[1]:
                try:
                    a, b = (datetime.fromisoformat(x.replace("Z", "+00:00")).astimezone(tz) for x in v)
                except ValueError:
                    continue
                fmt = lambda t: (t.strftime("%-I:%M%p") if t.minute else t.strftime("%-I%p")).lower()
                items.append((day[:3].title(), f"{fmt(a)}-{fmt(b)}"))
        hours = compress_hours(items)
    # Re-grade (docs/PENDING_FIXES.md, contacts agent): "the number the property supplied" is true only of a property with
    # a leasing office. A page with no unit count for the building and no website is a small lister's own listing (feeds
    # such as reallyo, rentalutions): its original_phone is the LISTER's number. Such a page is graded like a
    # single-unit listing elsewhere: a named brokerage -> kind broker with the brokerage's number; nobody named ->
    # kind individual owner with a blank phone (contact through the listing). Never "leasing office".
    if single_lister_listing(best):
        brokerage = next((str(best.get(k) or "").strip() for k in ("brokerage_name", "pmc_display_name", "office_name")
                          if str(best.get(k) or "").strip() and BUSINESS.search(str(best.get(k)))), "")
        if brokerage:
            return [cand(60 if (orig or shown) else 92, url, phone=orig or shown, manager=brokerage, kind="broker",
                         note="number on a small lister's Apartment List listing, by this brokerage (not a leasing office)" if (orig or shown)
                         else "brokerage named on the Apartment List listing; no phone on the page")]
        return [cand(95, url, kind="individual owner",
                     note="Apartment List listing by a small lister with no company named (no unit count or website for the building); contact through the listing")]
    out = []
    if orig:
        note = "number the property supplied to Apartment List (original_phone)"
        if shown and shown != orig:
            note += f"; the page displays an Apartment List tracking number {shown}"
        if is_tollfree(orig):
            note += "; toll-free line"
        out.append(cand(20, url, phone=orig, site=site, hours=hours, kind="leasing office", note=note))
    elif shown:
        out.append(cand(45, url, phone=shown, site=site, hours=hours, kind="leasing office",
                        note=f"{TRACK} (Apartment List); no property-supplied number on the page"))
    else:
        out.append(cand(90, url, site=site, hours=hours, kind="leasing office"))
    return out


def parse_zumper(text: str, url: str):
    i = text.find("window.__PRELOADED_STATE__ = ")
    if i < 0:
        return []
    try:
        st, _ = DEC.raw_decode(text[i + len("window.__PRELOADED_STATE__ = "):])
    except json.JSONDecodeError:
        return []
    e = (((st or {}).get("detail") or {}).get("entity") or {}).get("data") or {}
    if not e:
        return []
    phone = norm_phone(e.get("phone"))
    proxy = bool(phone) and is_tollfree(phone) and "ext." in phone
    brokerage = (e.get("brokerage_name") or "").strip()
    hours = ""
    if isinstance(e.get("hours"), list):
        try:
            hours = compress_hours([(d.title(), f"{a.replace(' ', '')}-{b.replace(' ', '')}") for d, a, b in e["hours"]])
        except (ValueError, TypeError):
            hours = ""
    if "/apartment-buildings/" in url or e.get("pb_id"):
        name = (e.get("agent_name") or "").strip()
        if not brokerage and not BUSINESS.search(name):
            # a building page posted by a person with no company: treat as an individual lister
            return [cand(95, url, kind="individual owner",
                         note="Zumper page posted by an individual with no company named; contact through the listing")]
        note = f"{TRACK} (Zumper proxy line)" if proxy else "as shown on the Zumper building page; not checked against the building's own site"
        return [cand(70 if proxy else 30, url, phone=phone, hours=hours, manager=brokerage, kind="leasing office", note=note)]
    agents = e.get("listing_agents") or []
    ag = agents[0] if agents and isinstance(agents[0], dict) else {}
    brokerage = brokerage or (ag.get("brokerage_name") or "").strip()
    if not brokerage:
        return [cand(95, url, kind="individual owner",
                     note="single-unit Zumper listing with no brokerage or company named; contact through the listing")]
    if phone:
        note = (f"{TRACK} (Zumper proxy line) for the brokerage listing this unit" if proxy
                else "number shown on a single-unit Zumper listing by this brokerage")
        return [cand(75 if proxy else 60, url, phone=phone, manager=brokerage, kind="broker", note=note)]
    return [cand(92, url, manager=brokerage, kind="broker", note="brokerage named on the Zumper listing; no phone on the page")]


def next_data(text: str):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def parse_trulia(text: str, url: str):
    d = next_data(text)
    h = ((d or {}).get("props") or {}).get("homeDetails") or {}
    if not h:
        return []
    desc = h.get("description") or {}
    pv = h.get("planVisit") or {}
    pm = pv.get("propertyManagementCompany") or {}
    if "/building/" in url or pm:
        phone = norm_phone(desc.get("contactPhoneNumber")) or norm_phone(pm.get("phoneNumber"))
        hours = ""
        items = ((pv.get("officeHours") or {}).get("scheduleItems")) or []
        if items:
            hours = compress_hours([(re.sub(r"\s*-\s*", "-", it["formattedDaysOfWeek"]), f"{it.get('startTime')}-{it.get('endTime')}")
                                    for it in items if it.get("formattedDaysOfWeek") and it.get("startTime")])
        mgr = (pm.get("name") or "").strip()
        return [cand(40 if phone else 91, url, phone=phone, hours=hours, manager=mgr, kind="leasing office",
                     note=f"{TRACK} (Trulia / Zillow Rentals forwarding line)" if phone
                     else "no phone number on the cached Trulia building page")]
    prov = (h.get("activeListing") or {}).get("provider") or (h.get("activeForRentListing") or {}).get("provider") or {}
    br = prov.get("broker") or {}
    name = (br.get("name") or "").strip()
    if name:
        phone = norm_phone(br.get("phone"))
        if phone:
            return [cand(55, url, phone=phone, manager=name, kind="broker",
                         note="brokerage's number from the listing attribution on a single-unit listing")]
        return [cand(92, url, manager=name, kind="broker",
                     note="brokerage named in the listing attribution; no phone on the page")]
    return [cand(95, url, kind="individual owner",
                 note="single-unit listing by a person with no brokerage named; contact through the listing")]


def parse_zillow(text: str, url: str):
    m = re.search(r'"buildingPhoneNumber":"([^"]+)"', text)
    phone = norm_phone(m.group(1)) if m else ""
    if phone:
        return [cand(42, url, phone=phone, kind="leasing office", note=f"{TRACK} (Zillow Rentals forwarding line)")]
    return []


PHONE_TXT = re.compile(r"(?<![\d.])(?:\+?1[\s.-]?)?\(?([2-9]\d{2})\)?[\s.-]{1,2}([2-9]\d{2})[\s.-]([0-9]{4})(?![\d.])")
BOTWALL = re.compile(r"captcha|px-captcha|cf-challenge|Just a moment\.\.\.|Access Denied|are you a robot|"
                     r"Attention Required|unusual traffic|Request unsuccessful\. Incapsula", re.I)


def jsonld_objects(text: str):
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.S | re.I):
        try:
            d = json.loads(htmllib.unescape(m.group(1)).strip())
        except json.JSONDecodeError:
            continue
        stack = [d]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                yield o
                stack.extend(o.values())
            elif isinstance(o, list):
                stack.extend(o)


def parse_own_site(text: str, url: str, rank: int = 10):
    """Phone from a building's or manager's own page: JSON-LD telephone, then tel: links, then visible text."""
    if not text or BOTWALL.search(text[:20000]) and len(text) < 60000:
        return []
    ld, hours = [], ""
    for o in jsonld_objects(text):
        t = o.get("telephone")
        if isinstance(t, str) and norm_phone(t):
            ld.append(norm_phone(t))
        if not hours:
            oh = o.get("openingHours")
            if isinstance(oh, list):
                oh = "; ".join(str(x) for x in oh)
            if isinstance(oh, str) and oh.strip():
                hours = oh.strip()[:160]
            spec = o.get("openingHoursSpecification")
            if not hours and isinstance(spec, list):
                items = []
                for s in spec:
                    if not isinstance(s, dict) or not s.get("opens"):
                        continue
                    days = s.get("dayOfWeek")
                    days = days if isinstance(days, list) else [days]
                    for dname in days:
                        items.append((str(dname).rsplit("/", 1)[-1][:3], f"{s.get('opens')}-{s.get('closes')}"))
                hours = compress_hours(items)[:160]
    tels = [norm_phone(htmllib.unescape(t).replace("%20", "")) for t in re.findall(r'href=["\']tel:([^"\']+)["\']', text, re.I)]
    tels = [t for t in tels if t]
    how = ""
    if ld:
        phone, how = Counter(ld).most_common(1)[0][0], "JSON-LD telephone"
    elif tels:
        phone, how = Counter(tels).most_common(1)[0][0], "tel: link"
        if len(set(tels)) > 1:
            how += f" (most frequent of {len(set(tels))} numbers on the page)"
    else:
        vis = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", text)
        vis = htmllib.unescape(re.sub(r"<[^>]+>", " ", vis))
        found = list(dict.fromkeys(norm_phone("".join(m.groups())) for m in PHONE_TXT.finditer(vis)))
        found = [f for f in found if f]
        if len(found) != 1:
            return [cand(89, url, site=url, hours=hours, kind="leasing office")] if hours else []
        phone, how = found[0], "the only phone number in the page text"
    return [cand(rank, url, phone=phone, site=url, hours=hours, kind="leasing office",
                 note=f"building / manager site ({how})")]


def parse_page(path: str, url: str):
    try:
        text = (ROOT / path).read_text(errors="replace")
    except OSError:
        return []
    h = host_of(url)
    if "apartmentlist.com" in h:
        return parse_apartmentlist(text, url)
    if "zumper.com" in h:
        return parse_zumper(text, url)
    if "trulia.com" in h:
        return parse_trulia(text, url)
    if "zillow.com" in h:
        return parse_zillow(text, url)
    if is_own(url) and not path.endswith(".json"):
        return parse_own_site(text, url)
    return []


# ------------------------------------------------------------------------------------------------- buildings
def load_buildings():
    b = {}
    ranked = read_csv(DATA / "ranked_units.csv")
    for x in ranked:
        bid = x.get("building_id") or ""
        if not bid:
            continue
        e = b.setdefault(bid, {"building_id": bid, "addr_key": x.get("addr_key", ""), "addr_keys": set(), "name": "",
                               "address": "", "pages": [], "urls": [], "own": [], "manager": "", "listing_urls": []})
        for k in [x.get("addr_key", "")] + re.split(r"\s*[;]\s*", x.get("addr_keys", "") or ""):
            if k.strip():
                e["addr_keys"].add(k.strip())
        e["name"] = e["name"] or (x.get("building_name") or "").strip()
        if not e["address"] and x.get("address"):
            street = x["address"].strip()
            if re.search(r"\b\d{5}\b", street):                 # the field already holds a full address
                e["address"] = re.sub(r",\s*(US|USA)\s*$", "", street)
            else:
                tail = " ".join(v for v in ((x.get("state") or "").strip(), (x.get("zip5") or "").strip()) if v)
                e["address"] = ", ".join(v for v in (street, (x.get("city") or "").strip(), tail) if v)
        e["manager"] = e["manager"] or (x.get("manager") or "").strip()
        if x.get("raw_path") and x.get("url"):
            e["pages"].append((x["raw_path"], x["url"]))
        if x.get("url"):
            e["listing_urls"].append(x["url"])
        for col in ("url", "building_url", "also_seen_at"):
            e["urls"] += urls_in(x.get(col, ""))
        for col, v in x.items():
            # year_built_source often cites a news article, so it is not a lead to the building's own site
            if col.endswith("_source") and col != "year_built_source" and v and "http" in v:
                e["own"] += [u for u in urls_in(v) if is_own(u)]
        e["own"] += [u for u in urls_in(x.get("building_url", "")) + urls_in(x.get("url", "")) if is_own(u)]
    for x in read_csv(DATA / "needs_confirmation.csv"):
        bid = x.get("building_id") or ""
        if not bid:
            continue
        e = b.setdefault(bid, {"building_id": bid, "addr_key": "", "addr_keys": set(), "name": "", "address": "",
                               "pages": [], "urls": [], "own": [], "manager": "", "listing_urls": []})
        e["name"] = e["name"] or (x.get("building_name") or "").strip()
        e["address"] = e["address"] or (x.get("address") or "").strip()
        if x.get("url"):
            e["urls"] += urls_in(x["url"])
            e["listing_urls"].append(x["url"])
    return b


def load_facts():
    """addr_key -> {'sites': [...], 'manager': str, 'pages': [aggregator page urls]}"""
    f = defaultdict(lambda: {"sites": [], "manager": "", "pages": []})
    for p in sorted(glob.glob(str(DATA / "evidence" / "facts_batch_*.csv"))):
        for x in read_csv(p):
            k = (x.get("addr_key") or "").strip()
            if not k:
                continue
            fact, val, src = (x.get("fact") or "").strip(), (x.get("value") or "").strip(), (x.get("source_url") or "").strip()
            if fact == "building_site":
                f[k]["sites"] += [u for u in urls_in(val) if is_own(u)]
            elif fact == "management_company" and val and not f[k]["manager"]:
                f[k]["manager"] = val
            if src.startswith("http") and re.search(r"apartmentlist\.com|zumper\.com", host_of(src)):
                f[k]["pages"].append(src)
    return f


def community_sites():
    """(normalised street, zip) -> own-site URL from data/reference/community_facts.csv."""
    out = {}
    for x in read_csv(DATA / "reference" / "community_facts.csv"):
        key = (re.sub(r"\s+", " ", (x.get("address") or "").lower().strip()), (x.get("zip") or "").strip()[:5])
        for col in ("community_website", "community_url"):
            u = (x.get(col) or "").strip()
            if u.startswith("http") and is_own(u):
                out.setdefault(key, u)
    return out


# ------------------------------------------------------------------------------------------------- fetching
def load_json(p, default):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, json.JSONDecodeError):
        return default


def save_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True))
    tmp.replace(p)


class Fetcher:
    def __init__(self, prior_refused: dict):
        self.state = load_json(STATE_F, {})            # url -> {status, path, retrieved_at, why}
        self.refused = load_json(REFUSED_F, {})        # host -> reason (this script's own refusals)
        self.prior = prior_refused
        self.robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.requests = 0

    def refuse(self, host: str, why: str):
        self.refused[host] = f"{now_iso()}: {why}"
        save_json(REFUSED_F, self.refused)
        print(f"  REFUSED {host}: {why} -> no more requests to this host", flush=True)

    def blocked(self, host: str) -> str:
        bare = host.removeprefix("www.")
        if any(bare == n or bare.endswith("." + n) for n in NEVER):
            return "host is on the never-request list"
        for h in (host, bare, "www." + bare):
            if h in self.refused:
                return "refused earlier: " + self.refused[h]
            if h in self.prior:
                return "blocked in an earlier harvest: " + self.prior[h]
        return ""

    def _get(self, url: str, ext: str):
        """(text or None, status, meta). Any refusal is persisted before returning."""
        host = host_of(url)
        self.requests += 1
        try:
            content, meta = cached_get(url, SRC, ext=ext, retries=1, timeout=30,
                                       headers={"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"})
        except RuntimeError as e:
            msg = str(e)
            if "HTTP 429" in msg:
                self.refuse(host, "HTTP 429")
                return None, 429, {}
            return None, 0, {"why": msg[-160:]}
        st = meta.get("status")
        text = content.decode("utf-8", errors="replace") if content else ""
        if st in (401, 403, 429):
            self.refuse(host, f"HTTP {st}")
            return None, st, meta
        if st == 200 and ext == "html" and BOTWALL.search(text[:20000]) and len(text) < 60000:
            self.refuse(host, "bot wall / CAPTCHA page")
            return None, 403, meta
        return (text if st == 200 else None), st, meta

    def robots_ok(self, url: str) -> tuple[bool, str]:
        p = urlparse(url)
        host = p.netloc.lower()
        if host not in self.robots:
            rurl = f"{p.scheme}://{p.netloc}/robots.txt"
            rec = self.state.get(rurl)
            text = None
            if rec and rec.get("status") == 200 and rec.get("path") and (ROOT / rec["path"]).exists():
                text = (ROOT / rec["path"]).read_text(errors="replace")
            elif rec:
                text = "" if rec.get("status") in (404, 410) else None
                if rec.get("status") not in (404, 410):
                    self.robots[host] = None
                    return False, f"robots.txt not readable (status {rec.get('status')})"
            else:
                text, st, meta = self._get(rurl, "txt")
                self.state[rurl] = {"status": st, "path": meta.get("path", ""), "retrieved_at": meta.get("retrieved_at", now_iso()),
                                    "why": meta.get("why", "")}
                save_json(STATE_F, self.state)
                if st in (404, 410):
                    text = ""
                elif text is None:
                    self.robots[host] = None
                    return False, f"robots.txt not readable (status {st})"
            if text and re.search(r"<html|<!doctype", text[:300], re.I):
                text = ""                       # an HTML page served for robots.txt carries no rules
            rp = urllib.robotparser.RobotFileParser()
            rp.parse((text or "").splitlines())
            self.robots[host] = rp
        rp = self.robots[host]
        if rp is None:
            return False, "robots.txt not readable"
        named = [a for a in ("ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai")
                 if any(a.lower() in (e_ua.lower() for e_ua in ent.useragents) for ent in rp.entries)]
        agents = named or [USER_AGENT.split("/")[0], "*"]
        for a in agents:
            if not rp.can_fetch(a, url):
                return False, f"robots.txt disallows this path for {a}"
        return True, ""

    def page(self, url: str):
        """(path, retrieved_at) of the fetched page, or (None, reason)."""
        host = host_of(url)
        why = self.blocked(host)
        if why:
            return None, why
        rec = self.state.get(url)
        if rec:
            if rec.get("status") == 200 and rec.get("path") and (ROOT / rec["path"]).exists():
                return rec["path"], rec.get("retrieved_at", "")
            return None, f"tried before: status {rec.get('status')} {rec.get('why', '')}".strip()
        ok, why = self.robots_ok(url)
        if not ok:
            self.state[url] = {"status": -1, "why": why, "retrieved_at": now_iso()}
            save_json(STATE_F, self.state)
            return None, why
        why = self.blocked(host)                # robots.txt itself may have been refused
        if why:
            return None, why
        text, st, meta = self._get(url, "html")
        self.state[url] = {"status": st, "path": meta.get("path", ""), "retrieved_at": meta.get("retrieved_at", now_iso()),
                           "why": meta.get("why", "")}
        save_json(STATE_F, self.state)
        if text is None:
            return None, f"status {st} {meta.get('why', '')}".strip()
        return meta["path"], meta.get("retrieved_at", "")


# ------------------------------------------------------------------------------------------------- assemble
def offline_candidates(e, idx, facts, comm):
    """All candidates for one building from pages already on disk, plus its own-site URL leads."""
    pages, seen = [], set()

    def add(path, url, when=""):
        if path and path not in seen and (ROOT / path).exists():
            seen.add(path)
            pages.append((path, url, when or meta_of(path).get("retrieved_at", "")))

    for path, url in e["pages"]:
        add(path, url)
    fact_pages, fact_sites, fact_mgr = [], [], ""
    for k in sorted(e["addr_keys"]):
        if k in facts:
            fact_pages += facts[k]["pages"]
            fact_sites += facts[k]["sites"]
            fact_mgr = fact_mgr or facts[k]["manager"]
    for u in list(dict.fromkeys(e["urls"] + fact_pages)):
        hit = idx.get(norm_url(u))
        if hit:
            add(hit[0], u, hit[2])
    cands = []
    for path, url, when in pages:
        for c in parse_page(path, url):
            c["when"], c["basis"] = when, "cached_page"
            cands.append(c)
    own = [clean_url(c["site"]) for c in cands if c.get("site")]
    own += [clean_url(u) for u in fact_sites + e["own"]]
    street = re.sub(r"\s+", " ", e["address"].split(",")[0].lower().strip())
    zipm = re.search(r"(\d{5})\s*$", e["address"])
    cu = comm.get((street, zipm.group(1) if zipm else ""))
    if cu:
        own.append(clean_url(cu))
    own = [u for u in dict.fromkeys(own) if u and is_own(u)]
    for u in own:                                # own-site pages that an earlier harvest already cached
        hit = idx.get(norm_url(u))
        if hit and hit[0] not in seen and not hit[0].endswith(".json"):
            seen.add(hit[0])
            for c in parse_own_site((ROOT / hit[0]).read_text(errors="replace"), hit[1]):
                c["when"], c["basis"] = hit[2], "cached_page"
                cands.append(c)
    return cands, own, fact_mgr


def business_name(s: str) -> str:
    """A manager string from the pipeline, kept only when it names a business (never a private person)."""
    s = re.sub(r"\s*\((?!.*\bLLC\b)[^)]*\)\s*$", "", (s or "").strip())
    return s if s and BUSINESS.search(s) else ""


def build_row(e, cands, own, fact_mgr, fetch_note=""):
    cands = sorted(cands, key=lambda c: (c["rank"], -len(c.get("hours") or "")))
    with_phone = [c for c in cands if c["phone"]]
    best = with_phone[0] if with_phone else (cands[0] if cands else None)
    listing = next((u for u in e["listing_urls"] if u), "")
    row = {k: "" for k in COLS}
    row.update(building_id=e["building_id"], addr_key=e["addr_key"] or (sorted(e["addr_keys"])[0] if e["addr_keys"] else ""),
               building_name=e["name"], address=e["address"])
    notes = []
    if best:
        row["leasing_phone"] = best["phone"]
        row["leasing_phone_source_url"] = best["src"] if best["phone"] else ""
        row["contact_kind"] = best["kind"]
        row["retrieved_at"] = best.get("when", "")
        row["basis"] = best.get("basis", "")
        if best["note"]:
            notes.append(best["note"])
    kinds = {c["kind"] for c in cands}
    building_level = bool(kinds & {"leasing office"})
    if best and best["kind"] in ("broker", "individual owner") and building_level:
        row["contact_kind"] = "leasing office"
    # leasing URL: own site first, then the building's listing page; for owner / broker units the listing URL
    if row["contact_kind"] in ("individual owner", "broker"):
        row["leasing_url"] = (best["src"] if best else "") or listing
        own_for_row = []
    else:
        own_for_row = own
        row["leasing_url"] = own[0] if own else ((best["src"] if best else "") or listing)
    hours = next((c["hours"] for c in cands if c.get("hours") and c["kind"] == "leasing office"), "")
    if row["contact_kind"] in ("leasing office", "management company", ""):
        row["office_hours"] = hours
    mgr = ""
    if row["contact_kind"] == "broker":
        mgr = best["manager"]
        others = sorted({c["manager"] for c in cands if c["kind"] == "broker" and c["manager"] and c["manager"] != mgr})
        if others:
            notes.append("other units here are listed by: " + ", ".join(others[:4]))
    elif row["contact_kind"] == "individual owner":
        mgr = business_name(e["manager"]) or business_name(fact_mgr)
        if mgr:
            row["contact_kind"] = "management company"
            notes = [f"listing posted by a person with no brokerage named; the pipeline's records name {mgr} as owner or "
                     "manager but no business phone is on any cached page; contact through the listing"]
    else:
        mgr = next((c["manager"] for c in cands if c["manager"] and c["kind"] == "leasing office"), "") \
            or business_name(fact_mgr) or business_name(e["manager"])
    row["manager_name"] = mgr
    # alternates worth knowing about
    if best and best["phone"]:
        alts = {}
        for c in with_phone[1:]:
            if c["phone"] != best["phone"] and c["phone"] not in alts and c["kind"] == "leasing office" and len(alts) < 2:
                alts[c["phone"]] = c["phone"] + (" (tracking)" if TRACK in c["note"] else "")
        if alts:
            notes.append("also seen: " + ", ".join(alts.values()))
    if not row["leasing_phone"]:
        if not best:
            row["retrieved_at"], row["basis"] = "", ""
            notes.append("no cached page for this building could be parsed for a contact")
        if own_for_row and row["contact_kind"] not in ("individual owner", "broker"):
            row["contact_kind"] = row["contact_kind"] or "leasing office"
    if fetch_note:
        notes.append(fetch_note)
    row["note"] = "; ".join(dict.fromkeys(n for n in notes if n))
    return row


def fetch_targets(e, cands, own):
    """One URL to try for a building: its own site, else an uncached Apartment List / Zumper page."""
    out = list(own)
    for u in dict.fromkeys(e["urls"]):
        if re.search(r"apartmentlist\.com|zumper\.com", host_of(u)):
            out.append(u)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fetch", action="store_true", help="fetch one page for each building that still has no phone")
    ap.add_argument("--upgrade-tracking", action="store_true",
                    help="with --fetch: also fetch the own site of buildings whose only number is a tracking number")
    ap.add_argument("--limit", type=int, default=0, help="stop after this many buildings were attempted (0 = no limit)")
    a = ap.parse_args(argv)

    buildings = load_buildings()
    idx, prior_refused = build_index()
    facts, comm = load_facts(), community_sites()
    fx = Fetcher(prior_refused)
    print(f"buildings {len(buildings)}; cached pages indexed {len(idx)}; hosts blocked in earlier harvests {len(prior_refused)}")

    rows, attempted, stats = [], 0, Counter()
    for bid in sorted(buildings):
        e = buildings[bid]
        cands, own, fact_mgr = offline_candidates(e, idx, facts, comm)
        fetch_note = ""
        has_phone = any(c["phone"] for c in cands)
        only_tracking = has_phone and all(TRACK in c["note"] for c in cands if c["phone"])
        kinds = {c["kind"] for c in cands}
        person_or_broker = bool(cands) and not (kinds & {"leasing office"})
        # pages this script fetched on an earlier run count without --fetch (resumable, no new requests)
        want = (not has_phone) or (only_tracking and (a.upgrade_tracking or any(u in fx.state for u in own)))
        if want and not (person_or_broker and not own):
            targets = fetch_targets(e, cands, own) if not has_phone else list(own)
            tried = []
            for u in targets:
                known = u in fx.state
                if not known and (not a.fetch or (a.limit and attempted >= a.limit)):
                    continue
                if not known:
                    attempted += 1
                path, info = fx.page(u)
                if path:
                    text = (ROOT / path).read_text(errors="replace")
                    got = parse_own_site(text, u) if is_own(u) else parse_page(path, u)
                    for c in got:
                        c["when"], c["basis"] = info, "fetched_page"
                    cands += got
                    if any(c["phone"] for c in got):
                        break
                    tried.append(f"{u} fetched, no phone found in the page")
                else:
                    tried.append(f"{u} not fetched ({info})")
                break                            # one page per building
            if tried and not any(c.get("basis") == "fetched_page" and c["phone"] for c in cands):
                fetch_note = "; ".join(tried)
        row = build_row(e, cands, own, fact_mgr, fetch_note)
        rows.append(row)
        stats["phone" if row["leasing_phone"] else ("url only" if row["leasing_url"] else "nothing"), row["basis"] or "none"] += 1

    # Second pass over the finished rows: flags that need the whole table.
    by_phone = Counter(r["leasing_phone"] for r in rows if r["leasing_phone"] and r["note"].startswith("building / manager site"))
    for r in rows:
        p = r["leasing_phone"]
        if not p:
            continue
        extra = []
        if by_phone.get(p, 0) > 1:
            r["contact_kind"] = "management company"
            extra.append(f"same number on {by_phone[p]} buildings' pages: the manager's shared leasing line, not one building's office")
        if p[1:4] not in LOCAL_CODES and not is_tollfree(p):
            extra.append(f"area code {p[1:4]} is outside NY/NJ/CT; may be a call-tracking line placed by the site's marketing vendor")
        if extra:
            head, sep, tail = r["note"].partition("; also seen")
            r["note"] = "; ".join([head] + extra) + sep + tail

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(OUT)

    n = len(rows)
    ph = [r for r in rows if r["leasing_phone"]]
    trk = [r for r in ph if TRACK in r["note"].split("; also seen")[0]]
    print(f"wrote {OUT.relative_to(ROOT)}: {n} buildings")
    for k, v in sorted(stats.items()):
        print(f"  {k[0]:9s} basis={k[1]:12s} {v}")
    print(f"  with a phone {len(ph)} ({len(trk)} are listing-site tracking numbers); kinds {dict(Counter(r['contact_kind'] or 'none' for r in rows))}")
    print(f"  new fetch attempts this run {attempted}; requests {fx.requests}; hosts refused by this script: {sorted(fx.refused)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
