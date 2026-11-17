"""Harvest studio / 1BR listings <= $3,000 from Apartment List (apartmentlist.com).

Method (plain fetch only, robots-allowed paths, >= 2.5 s between requests):
  1. sitemap-cities.xml -> city slugs in NY / NJ / CT / PA.
  2. Locate each city with the Census places gazetteer (name + state); a city counts as in the
     search grid when a grid ZCTA centroid is within CITY_KM of it. Cities the gazetteer cannot
     match are located from their own Apartment List page (the page carries coordinates).
  3. Nearest-first (grid drive_min): read the city's search pages for the two path filters
     /c/1-bedroom-apartments-for-rent and /c/studio-apartments-for-rent (+ /page-N).
     Search pages are used ONLY to discover property URLs. A property is skipped without a
     detail fetch only when the search page's JSON-LD says its lowest price is > $3,000.
  4. Fetch each remaining property page; price, availability, pets, amenities and fees are
     read from the property page (detail_level=detail). One CSV row per available unit
     (or per floor plan when the property publishes floor-plan-level availability only).
  5. Keep rows whose ZIP is in the grid (or whose lat/lon is within PROP_KM of a grid centroid).

Idempotent and resumable: pages are cached in raw/apartmentlist/, rows are keyed by listing_id,
first_seen is kept, last_seen is the fetch time of the property page. The CSV is rewritten after
every city. `--refresh` refetches search and property pages (updates last_seen).

Usage: python3 scripts/h_apartmentlist.py [--refresh] [--max-drive 120] [--only ny/queens,ct/stamford]

Second trawl (2026-11-17, `--trawl2`): collection ceiling MAX_RENT = $2,200 listed base rent for NEW units; units
already held (<= HELD_MAX = $3,000, the pipeline cap) are refreshed at their current price. `--max-age-hours 24` refetches
any search or property page whose cached copy is older than that. Cities run priority areas first (NJ, Brooklyn, CT,
Long Island, Long Island City), then the rest of the grid; every held property with a row <= $2,200 is re-read even
when no search page lists it any more. A held unit that its re-read page no longer lists (unit absent, page inactive,
page 404/410) is GONE: removed from the CSV, as the Zumper harvester does, and written with the reason to
raw/apartmentlist_trawl2/gone_units.csv. A held unit whose rent rose above $3,000 is removed the same way
(reason price_above_3000). A refusal (401/403/429/CAPTCHA) stops the run at once, with no retry, and is written to
raw/_host_kill_shared.json. Unit labels are kept exactly as given; floor and elevator are never read from them.
Run: python3 scripts/h_apartmentlist.py --trawl2 --max-age-hours 24 --fetch-max-low 2200
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
import zipfile
from datetime import datetime, timezone

import lib

SRC = "apartmentlist"
HOST = "www.apartmentlist.com"
BASE = "https://" + HOST
lib.HOST_DELAY[HOST] = 2.5  # brief: minimum 2 s per host (robots.txt has no Crawl-delay)

MAX_RENT = 2200   # second trawl (Will, 2026-11-17): collect no new unit above $2,200 listed base rent
HELD_MAX = 3000   # pipeline cap: units already held are kept and refreshed up to this
CITY_KM = 8.0
PROP_KM = 2.5
STATES = ("ny", "nj", "ct", "pa")
FILTERS = ("c/1-bedroom-apartments-for-rent", "c/studio-apartments-for-rent")
DISALLOW = ("/users/login", "/experiments", "/light_cycle", "/shortlist", "/signup",
            "/base-price-lock", "/all-in-price-lock", "/app/open")  # robots.txt, read 2026-11-15

OUT = lib.DATA / "listings_raw" / "apartmentlist.csv"
STATS = lib.RAW / SRC / "_harvest_stats.json"
COLS = ("listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,"
        "unit,beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,"
        "dog_policy_text,dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,"
        "other_monthly_fees_json,utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,"
        "building_url,raw_path,notes").split(",")

BOROUGHS = {  # not Census places; coordinates are the borough page's own "coordinates" or a central point
    "ny/queens": (40.7075, -73.8185), "ny/brooklyn": (40.6500, -73.9500), "ny/bronx": (40.8500, -73.8660),
    "ny/staten-island": (40.5800, -74.1500), "ny/new-york": (40.7830, -73.9710), "ny/manhattan": (40.7830, -73.9710),
}

DEC = json.JSONDecoder()
REFRESH = False
MAX_AGE_H = 0.0   # >0: refetch a cached page older than this many hours
T2 = lib.RAW / "apartmentlist_trawl2"
GONE = T2 / "gone_units.csv"
STATE = T2 / "_checked.json"   # property path -> {at, status, reason}; makes the trawl resumable


class Blocked(Exception):
    def __init__(self, msg, url=""):
        super().__init__(msg)
        self.url = url


class Transient(Exception):
    """5xx or a network error on one page: that page is skipped, its held rows are left untouched."""


def _cache_age_h(url: str):
    import hashlib
    import requests
    full = requests.Request("GET", url).prepare().url
    key = hashlib.sha1(("GET " + full + " ").encode()).hexdigest()[:16]
    mp = lib.RAW / SRC / f"{key}.meta.json"
    if not mp.exists():
        return None
    try:
        at = datetime.fromisoformat(json.loads(mp.read_text())["retrieved_at"])
    except (ValueError, KeyError):
        return None
    return (datetime.now(timezone.utc) - at).total_seconds() / 3600


def record_refusal(reason: str, url: str):
    """One refusal ends the host for the session and after restarts (CLAUDE.md). Merge into the shared kill file."""
    kf = lib.RAW / lib.KILL_FILE_NAME
    try:
        kill = json.loads(kf.read_text())
    except (OSError, ValueError):
        kill = {}
    if HOST not in kill:
        kill[HOST] = {"reason": reason, "url": url, "at": lib.now_iso(), "by": "scripts/h_apartmentlist.py (trawl 2)"}
        kf.write_text(json.dumps(kill, indent=1))


def log(*a):
    print(datetime.now(timezone.utc).strftime("%H:%M:%S"), *a, flush=True)


def km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    x = (lon2 - lon1) * p * math.cos((lat1 + lat2) / 2 * p)
    y = (lat2 - lat1) * p
    return 6371 * math.hypot(x, y)


def fetch(path: str, refresh: bool | None = None):
    """Fetch a robots-allowed path. Returns (html, meta). Raises Blocked on 403/429/CAPTCHA."""
    assert not any(path.startswith(d) for d in DISALLOW), path
    rf = REFRESH if refresh is None else refresh
    if not rf and MAX_AGE_H > 0:
        age = _cache_age_h(BASE + path)
        rf = age is not None and age > MAX_AGE_H
    try:
        # retries=1: a 429 is never retried (lib would otherwise retry 429/5xx three times)
        content, meta = lib.cached_get(BASE + path, SRC, ext="html", refresh=rf, retries=1)
    except lib.HostRefused as e:
        raise Blocked(str(e), BASE + path)
    except RuntimeError as e:
        if "HTTP 429" in str(e):
            raise Blocked(f"HTTP 429 {path}", BASE + path)
        raise Transient(str(e))
    if meta["status"] in (401, 403, 429):
        raise Blocked(f"HTTP {meta['status']} {path}", BASE + path)
    html = content.decode("utf8", "replace")
    if meta["status"] == 200 and re.search(r"captcha|px-captcha|cf-challenge|Just a moment", html[:20000], re.I):
        raise Blocked(f"challenge page {path}", BASE + path)
    return html, meta


def flight(html: str) -> str:
    """Join the Next.js app-router flight chunks (self.__next_f.push([1,"..."]))."""
    out = []
    for c in re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html):
        try:
            out.append(json.loads(c))
        except json.JSONDecodeError:
            pass
    return "".join(out)


# ---------------------------------------------------------------- grid and cities
def load_grid():
    g = []
    with open(lib.DATA / "reference" / "search_grid.csv") as f:
        for r in csv.DictReader(f):
            try:
                g.append((r["zcta"].zfill(5), float(r["lat"]), float(r["lon"]), float(r["drive_min"])))
            except ValueError:
                continue
    return g


def nearest_grid(grid, lat, lon):
    best = min(grid, key=lambda z: km(lat, lon, z[1], z[2]))
    return best, km(lat, lon, best[1], best[2])


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_places():
    """Census 2024 places gazetteer -> {(state, slug): [(lat, lon), ...]}."""
    content, _ = lib.cached_get(
        "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip",
        SRC, ext="zip")
    z = zipfile.ZipFile(io.BytesIO(content))
    txt = z.read(z.namelist()[0]).decode("latin-1")
    out: dict = {}
    rows = csv.reader(io.StringIO(txt), delimiter="\t")
    hdr = [h.strip() for h in next(rows)]
    ix = {h: i for i, h in enumerate(hdr)}
    for r in rows:
        st = r[ix["USPS"]].strip().lower()
        if st not in STATES:
            continue
        name = re.sub(r"\s+(city|village|town|borough|CDP|township|municipality)(\s+\(.*\))?$", "", r[ix["NAME"]].strip())
        try:
            out.setdefault((st, slugify(name)), []).append((float(r[ix["INTPTLAT"]]), float(r[ix["INTPTLONG"]])))
        except ValueError:
            pass
    return out


def city_list(grid, max_drive):
    xml, _ = lib.cached_get(BASE + "/sitemap-cities.xml", SRC, ext="xml")
    slugs = sorted({m for m in re.findall(r"<loc>https://www\.apartmentlist\.com/([a-z]{2}/[a-z0-9-]+)</loc>",
                                          xml.decode()) if m[:2] in STATES})
    places = load_places()
    cities, unmatched, far = [], [], 0
    for s in slugs:
        st, name = s.split("/")
        pts = [BOROUGHS[s]] if s in BOROUGHS else places.get((st, name), [])
        if not pts:
            unmatched.append(s)
            continue
        cand = [nearest_grid(grid, la, lo) for la, lo in pts]
        cand = [(z, d) for z, d in cand if d <= CITY_KM and z[3] <= max_drive]
        if cand:
            z, d = min(cand, key=lambda c: c[0][3])
            cities.append((z[3], s, z[0]))
        else:
            far += 1
    cities.sort()
    return cities, unmatched, far, len(slugs)


def page_city_coords(fl: str, slug: str):
    m = re.search(r'"slug":"/' + re.escape(slug) + r'","type":"city".{0,600}?"coordinates":\{"lat":([-\d.]+),"lon":([-\d.]+)\}',
                  fl, re.S)
    return (float(m.group(1)), float(m.group(2))) if m else None


# ---------------------------------------------------------------- search pages (discovery only)
def parse_srp(html: str):
    fl = flight(html)
    props = dict(re.findall(r'"listing":\{"rental_id":"(\w+)","slug":"(/[a-z]{2}/[^"]+)"', fl))
    low = {}
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        for it in d if isinstance(d, list) else [d]:
            if isinstance(it, dict) and it.get("url", "").startswith(BASE + "/"):
                off = it.get("offers") or {}
                lp = off.get("lowPrice") or off.get("price")
                low[it["url"][len(BASE):]] = lp if isinstance(lp, (int, float)) else None
    tc = re.search(r'"total_count":(\d+),"total_unit_count":(\d+)', fl)
    return props, low, (int(tc.group(1)) if tc else None), fl


def discover_city(slug: str, stats: dict):
    """Return {property_slug: lowest JSON-LD price seen or None} for the 1BR and studio filters."""
    found: dict = {}
    for flt in FILTERS:
        page, seen_ids, total = 1, set(), None
        while True:
            path = f"/{slug}/{flt}" + (f"/page-{page}" if page > 1 else "")
            html, meta = fetch(path)
            stats["srp_pages"] += 1
            if meta["status"] != 200:
                break
            props, low, tc, _ = parse_srp(html)
            if page == 1:
                total = tc
            new = set(props) - seen_ids
            if not props or not new:
                break
            seen_ids |= set(props)
            for rid, pslug in props.items():
                lp = low.get(pslug, "absent")
                prev = found.get(pslug, "absent")
                if prev == "absent" or (isinstance(lp, (int, float)) and (not isinstance(prev, (int, float)) or lp < prev)):
                    found[pslug] = lp
            page += 1
            if total is not None and (page - 1) * 16 >= total + 16:
                break
            if page > 400:
                break
    return found


# ---------------------------------------------------------------- property page
def parse_listing(html: str):
    fl = flight(html)
    best = None
    for m in re.finditer(r'"listing":\{"rental_id"', fl):
        try:
            o, _ = DEC.raw_decode(fl, m.start() + 10)
        except json.JSONDecodeError:
            continue
        if "available_units" in o and (best is None or len(o) > len(best)):
            best = o
    if best is None:
        return None
    # The page carries the listing twice. The second copy replaces big fields with "$ref" pointers, but it is
    # the only copy whose `specials` list is filled (the first copy always has specials=[]). Collect specials
    # from every copy of the same rental_id.
    specials, seen = [], set()
    for m in re.finditer(r'"specials":\[\{', fl):
        try:
            arr, _ = DEC.raw_decode(fl, m.start() + 11)
        except json.JSONDecodeError:
            continue
        back = fl.rfind('"listing":{"rental_id":"', 0, m.start())
        if back < 0 or not fl.startswith(str(best.get("rental_id")), back + 24):
            continue
        for sp in arr:
            if isinstance(sp, dict) and sp.get("id") not in seen:
                seen.add(sp.get("id"))
                specials.append(sp)
    if specials:
        best["specials"] = specials
    # Long descriptions are stored as a flight text row ("87:T42c,<text>") and referenced as "$87".
    d = best.get("description")
    if isinstance(d, str) and re.fullmatch(r"\$[0-9a-f]+", d):
        m = re.search(r"(?:^|\n)" + d[1:] + r":T([0-9a-f]+),", fl)
        if m:
            t = fl[m.end():m.end() + int(m.group(1), 16)]
            t = re.split(r"\n?[0-9a-f]{1,4}:(?:\[|\{|\"|T[0-9a-f]+,|I\[)", t)[0]
            try:
                t = t.encode("latin-1").decode("utf8")  # flight text rows come out double-encoded
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
            best["description"] = t
        else:
            best["description"] = ""
    return best


def txt(v):
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).replace("$$", "$").strip()


def money(s):
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", s or "")
    return m.group(1).replace(",", "") if m else ""


def amen_names(L, key):
    return [a.get("display_name", "") for a in (L.get(key) or []) if isinstance(a, dict)]


def pet_facts(L):
    pp = L.get("pet_policies") or {}
    comm = amen_names(L, "community_amenities") + amen_names(L, "unit_amenities") + amen_names(L, "top_amenities")
    allowed_pets = [str(x).lower() for x in (pp.get("allowed_pets") or [])]
    if "dogs" in allowed_pets or "Dogs allowed" in comm:
        dogs = "yes"
    elif pp.get("allowed") is False:
        dogs = "no"
    elif allowed_pets and "dogs" not in allowed_pets:
        dogs = "no"  # page lists allowed pets and dogs are not among them (e.g. cats only)
    else:
        dogs = "unknown"  # "pet friendly" with no species, or no pet policy at all
    parts = []
    if pp:
        parts.append("allowed=" + str(pp.get("allowed")).lower() + "; allowed_pets=" + ("/".join(allowed_pets) or "not stated"))
        if txt(pp.get("details")):
            parts.append("details: " + txt(pp.get("details")))
        for grp in ("dogs", "general"):
            g = pp.get(grp) or {}
            bits = [f"{k}: {txt(g.get(k))}" for k in ("limit", "restrictions", "rent", "fee", "deposit") if txt(g.get(k))]
            if bits:
                parts.append(grp + " {" + "; ".join(bits) + "}")
    pet_am = [a for a in dict.fromkeys(comm) if re.search(r"\b(dogs?|cats?|pets?)\b", a, re.I)]
    if pet_am:
        parts.append("amenities: " + ", ".join(pet_am))
    policy = " | ".join(parts)
    # weight limit: only from dog / general policy text
    wsrc = " ".join(txt((pp.get(g) or {}).get(k)) for g in ("dogs", "general") for k in ("limit", "restrictions")) \
        + " " + txt(pp.get("details"))
    weights = [int(w) for w in re.findall(r"(\d{2,3})\s*(?:-\s*)?(?:lbs?\b|pounds?\b|#)", wsrc, re.I)]
    wl = ""
    if weights:
        wl = str(max(weights)) if re.search(r"dogs?\b", wsrc, re.I) and len(set(weights)) > 1 else str(weights[0])
        if len(set(weights)) > 1:
            policy += f" | weights mentioned: {sorted(set(weights))}"
    elif re.search(r"no weight (limit|restriction)", wsrc, re.I):
        policy += " | page says no weight limit"
    g_d, g_g = pp.get("dogs") or {}, pp.get("general") or {}
    pet_rent = txt(g_d.get("rent")) or txt(g_g.get("rent"))
    return dogs, policy[:900], wl, pet_rent


def build_rows(L, pslug, meta, grid_zips, grid, ceiling=HELD_MAX):
    """Return (rows, reason). rows = list of dicts for available studio/1BR units <= ceiling."""
    seen_at = meta["retrieved_at"]
    today = seen_at[:10]
    zipc = txt(L.get("zip"))[:5]
    lat, lon = L.get("lat"), L.get("lon")
    drive = None
    if zipc in grid_zips:
        drive = grid_zips[zipc]
    elif isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        z, d = nearest_grid(grid, lat, lon)
        if d <= PROP_KM:
            drive = z[3]
    if drive is None:
        return [], "outside_grid"
    if L.get("active") is False:
        return [], "inactive"
    if L.get("show_price") is False:
        return [], "price_hidden"

    amen_all = amen_names(L, "community_amenities") + amen_names(L, "unit_amenities") + amen_names(L, "top_amenities")
    dogs, policy, wl, pet_rent = pet_facts(L)
    elevator = "yes" if any(a.lower() == "elevator" for a in amen_all) else "unknown"
    desc = txt(L.get("description"))
    if elevator == "unknown" and re.search(r"\belevator", desc, re.I) and not re.search(r"no elevator|walk[- ]?up", desc, re.I):
        elevator = "yes"
    walkup = bool(re.search(r"walk[- ]?up|no elevator", desc, re.I))
    if walkup and elevator == "unknown":
        elevator = "no"
    bf = re.search(r"\b(\d{1,2})[- ]stor(?:y|ies)\b", desc, re.I)
    building_floors = bf.group(1) if bf else ""

    pk = [p for p in (L.get("parking") or []) if isinstance(p, dict)]
    ptypes = [txt(p.get("category")) for p in pk if txt(p.get("category"))]
    ptypes += [a for a in dict.fromkeys(amen_all) if re.search(r"garage|parking|carport", a, re.I)]
    pcomment = " / ".join(dict.fromkeys(filter(None, [txt(p.get("comment")) for p in pk] + [txt(L.get("parking_details_text"))])))
    parking_type = "; ".join(dict.fromkeys(ptypes))
    if pcomment:
        parking_type = (parking_type + " | " if parking_type else "") + pcomment
    parking_fee = ""
    for p in pk:
        if p.get("space_fee") not in (None, "", 0):
            parking_fee = txt(p.get("space_fee"))
    if not parking_fee and re.search(r"\$\s*\d", pcomment):
        parking_fee = pcomment
    laundry = "; ".join(dict.fromkeys(a.get("display_name", "") for k in ("unit_amenities", "community_amenities", "top_amenities")
                                      for a in (L.get(k) or []) if isinstance(a, dict) and
                                      (a.get("group") == "laundry" or re.search(r"laundry|(?<!dish)washer|w/d", a.get("display_name", ""), re.I))))
    fees = {}
    for k in ("additional_fees_text", "move_in_fees_text", "deposit_fee_text", "application_fee_text", "storage_details_text"):
        if txt(L.get(k)):
            fees[k.replace("_text", "")] = txt(L.get(k))
    if (L.get("fees") or {}).get("fee_url"):
        fees["fee_url"] = L["fees"]["fee_url"]
    specials = []
    for s in L.get("specials") or []:
        if not isinstance(s, dict):
            specials.append(txt(s))
            continue
        t = txt(s.get("raw_text") or s.get("description") or s.get("title"))
        if t and txt(s.get("expires_at")):
            t += f" (expires {txt(s.get('expires_at'))[:10]})"
        specials.append(t)
    concession = " | ".join(dict.fromkeys(x for x in specials if x))[:900]

    rtype = txt(L.get("rental_type")).lower()
    managed = bool(txt(L.get("pmc_display_name"))) or (L.get("total_units_count") or 0) >= 5
    if rtype in ("condo", "coop", "co-op"):
        ltype = "condo_coop"
    elif rtype in ("house", "townhouse", "duplex", "triplex", "single_family", "multi_family"):
        ltype = "unit_in_house"
    elif rtype == "apartment" and managed:
        ltype = "managed_building"
    else:
        ltype = "unknown"
    manager = txt(L.get("pmc_display_name")) or txt(L.get("brokerage_name")) or txt(L.get("office_name"))
    ph = L.get("first_photo") or L.get("all_photos") or []
    photo = f"https://cdn.apartmentlist.com/image/upload/f_auto,q_auto,t_web-base/{ph[0]['id']}.jpg" if ph and ph[0].get("id") else ""
    url = BASE + pslug
    notes_base = [f"drive_min={drive}", f"rental_type={rtype or 'unknown'}", f"source_name={txt(L.get('source_name')) or 'unknown'}"]
    for k in ("neighborhood", "year_built", "total_units_count", "lease_terms_text", "website_url", "mls_number",
              "availability_last_checked_at"):
        if txt(L.get(k)):
            notes_base.append(f"{k}={txt(L.get(k))}")
    if walkup:
        notes_base.append("description mentions walk-up/no elevator")

    def avail(on, now_flag):
        on = txt(on)[:10]
        t = f"available_on={on or 'not stated'}; available_now={str(now_flag).lower() if now_flag is not None else 'not stated'}"
        if now_flag is True or (on and on <= today):
            return t, "now"
        return t, on if re.fullmatch(r"\d{4}-\d{2}-\d{2}", on) else ""

    rows = []

    def add(lid, unit, bed, bath, sqft, rent, basis, on, now_flag, extra_fees, extra_notes):
        at, ad = avail(on, now_flag)
        f2 = dict(fees)
        f2.update(extra_fees)
        rows.append({
            "listing_id": "apartmentlist:" + lid, "source_site": "apartmentlist.com", "url": url, "detail_level": "detail",
            "first_seen": seen_at, "last_seen": seen_at, "building_name": txt(L.get("display_name")),
            "address": txt(L.get("street_address") or L.get("street")), "city": txt(L.get("city")),
            "state": txt(L.get("state")), "zip": zipc, "lat": lat if lat is not None else "", "lon": lon if lon is not None else "",
            "unit": unit, "beds": bed, "baths": bath if bath is not None else "", "sqft": sqft or "",
            "listed_rent": rent, "price_basis": basis, "concession_text": concession,
            "available_date_text": at, "available_date": ad, "dogs": dogs, "dog_policy_text": policy,
            "dog_weight_limit_lb": wl, "elevator": elevator, "floor": "unknown", "building_floors": building_floors,
            "parking_type": parking_type[:400], "parking_fee": parking_fee[:200], "pet_rent": pet_rent,
            "other_monthly_fees_json": json.dumps(f2, ensure_ascii=False) if f2 else "",
            "utilities_included": txt(L.get("utilities_included_text")), "laundry": laundry, "listing_type": ltype,
            "manager": manager, "listing_age_days": "", "photo_url": photo, "building_url": url,
            "raw_path": meta["path"], "notes": "; ".join(notes_base + extra_notes),
        })

    n_fp = 0
    for fp in L.get("available_units") or []:
        bed = fp.get("bed")
        if bed not in (0, 1):
            continue
        n_fp += 1
        units = fp.get("units") or []
        for u in units:
            if txt(u.get("availability")).lower() not in ("", "available"):
                continue
            base, price, total = u.get("base_price"), u.get("price"), u.get("total_price")
            rent = base if isinstance(base, (int, float)) and base > 0 else price
            if not isinstance(rent, (int, float)) or rent <= 0 or rent > ceiling:
                continue
            ll = u.get("lease_length")
            basis = "base rent per month" + (f", {ll}-month lease" if ll else "")
            ef, en = {}, [f"floorplan={txt(fp.get('name'))}"]
            if isinstance(total, (int, float)) and total > 0:
                ef["total_price_with_required_fees"] = total
            if u.get("required_fees"):
                ef["required_fees"] = u["required_fees"]
            if isinstance(price, (int, float)) and isinstance(base, (int, float)) and price != base and base > 0:
                en.append(f"unit price field={price} differs from base_price={base}")
            if u.get("price_max"):
                en.append(f"price_max={u['price_max']}")
            if txt(u.get("updated_at")):
                en.append(f"unit_updated_at={txt(u.get('updated_at'))}")
            lid = txt(u.get("unit_rental_id")) or f"{L['rental_id']}-u{u.get('id')}"
            add(lid, txt(u.get("display_name") or u.get("name")), bed, fp.get("bath"), u.get("sqft") or fp.get("sqft"),
                rent, basis, u.get("available_on"), u.get("available_now"), ef, en)
        if not units:
            price = fp.get("price")
            if isinstance(price, (int, float)) and 0 < price <= ceiling:
                en = [f"floorplan={txt(fp.get('name'))}", "floor-plan-level price (no unit list on page); 'from' price"]
                if fp.get("price_max"):
                    en.append(f"price_max={fp['price_max']}")
                add(f"{L['rental_id']}-fp{fp.get('id')}", "", bed, fp.get("bath"), fp.get("sqft"), price,
                    "floor plan starting rent per month", fp.get("available_on"), fp.get("available_now"), {}, en)
    if rows:
        return rows, "ok"
    return [], ("no_studio_1br" if n_fp == 0 else "no_unit_le_3000")


# ---------------------------------------------------------------- main
def load_existing():
    rows = {}
    if OUT.exists():
        with open(OUT, newline="", encoding="utf8") as f:
            for r in csv.DictReader(f):
                rows[r["listing_id"]] = r
    return rows


def save(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: (float(re.search(r"drive_min=([\d.]+)", r["notes"]).group(1))
                                                      if re.search(r"drive_min=([\d.]+)", r["notes"]) else 999,
                                                      r["listing_id"])):
            w.writerow({c: r.get(c, "") for c in COLS})
    tmp.replace(OUT)


# ---------------------------------------------------------------- second trawl (2026-11-17)
PRIORITY = ("New Jersey", "Brooklyn", "Connecticut", "Long Island", "Long Island City")
LIC_ZIPS = ("11101", "11109", "11120")


def area_of(state: str, zipc: str, slug: str = "") -> str:
    st, z = (state or "").lower(), (zipc or "")[:5]
    if st == "nj":
        return "New Jersey"
    if st == "ct":
        return "Connecticut"
    if st == "pa":
        return "Pennsylvania"
    if z in LIC_ZIPS or slug == "ny/long-island-city":
        return "Long Island City"
    if slug == "ny/brooklyn" or z[:3] == "112":
        return "Brooklyn"
    if slug == "ny/queens" or z[:3] in ("113", "114", "116") or z in ("11004", "11005"):
        return "Queens (other)"
    if z[:3] in ("115", "117", "118", "119") or z[:3] == "110":
        return "Long Island"
    if z[:3] in ("100", "101", "102"):
        return "Manhattan"
    if z[:3] == "104":
        return "Bronx"
    if z[:3] == "103":
        return "Staten Island"
    return "New York (other)"


def band(rent) -> str:
    v = float(rent)
    return "<=2000" if v <= 2000 else ("2001-2200" if v <= 2200 else "2201-3000" if v <= 3000 else ">3000")


def trawl2(a, grid, grid_zips, cities, unmatched):
    started = lib.now_iso()
    before = {}
    bp = T2 / "apartmentlist_before.csv"   # snapshot of the CSV taken before the first trawl-2 run
    with open(bp, newline="", encoding="utf8") as f:
        for r in csv.DictReader(f):
            before[r["listing_id"]] = r
    rows = load_existing()
    gone = {}
    if GONE.exists():
        with open(GONE, newline="", encoding="utf8") as f:
            for r in csv.DictReader(f):
                gone[r["listing_id"]] = r
    checked = json.loads(STATE.read_text()) if STATE.exists() else {}
    stats = {"started": started, "args": vars(a), "srp_pages": 0, "props_considered": 0, "props_skipped_lowprice": 0,
             "props_read": 0, "reasons": {}, "transient": [], "blocked": None, "unparsed_pages": [], "cities_done": [],
             "cities_unmatched_far": []}
    gcols = COLS + ["gone_at", "gone_reason", "gone_page_status", "rent_on_page_now"]

    def save_all():
        save(rows)
        with open(GONE.with_suffix(".tmp"), "w", newline="", encoding="utf8") as f:
            w = csv.DictWriter(f, fieldnames=gcols)
            w.writeheader()
            for r in sorted(gone.values(), key=lambda r: r["listing_id"]):
                w.writerow({c: r.get(c, "") for c in gcols})
        GONE.with_suffix(".tmp").replace(GONE)
        STATE.write_text(json.dumps(checked, indent=0))
        (lib.RAW / SRC / "_harvest_stats_trawl2.json").write_text(json.dumps(stats, indent=1))

    def held_by_prop():
        out: dict = {}
        for lid, r in rows.items():
            out.setdefault(r["url"][len(BASE):], []).append(lid)
        return out

    def mark_gone(lid, reason, at, status, rent_now=""):
        r = dict(rows.pop(lid))
        r.update({"gone_at": at, "gone_reason": reason, "gone_page_status": status, "rent_on_page_now": rent_now})
        gone[lid] = r

    def process_prop(pslug):
        hp = held_by_prop().get(pslug, [])
        try:
            html, meta = fetch(pslug)
        except Transient as e:
            stats["transient"].append(f"{pslug}: {str(e)[:120]}")
            return
        stats["props_read"] += 1
        at, status = meta["retrieved_at"], meta["status"]
        reason = f"http_{status}"
        if status in (404, 410):
            for lid in hp:
                mark_gone(lid, f"property page answers HTTP {status}", at, status)
            reason = f"gone_http_{status}"
        elif status == 200:
            L = parse_listing(html)
            if not L and "NEXT_HTTP_ERROR_FALLBACK;404" in html:
                # soft 404: HTTP 200 carrying Next.js' "404: This page could not be found." (the property was removed)
                for lid in hp:
                    mark_gone(lid, "property page says '404: This page could not be found' (served with HTTP 200)", at, status)
                reason = "gone_soft_404"
            elif not L:
                reason = "no_listing_object"
                stats["unparsed_pages"].append(pslug)
            else:
                rr, reason = build_rows(L, pslug, meta, grid_zips, grid, ceiling=10 ** 9)
                if reason == "inactive":
                    for lid in hp:
                        mark_gone(lid, "property page marks the listing inactive", at, status)
                elif reason in ("ok", "no_studio_1br", "no_unit_le_3000"):
                    on_page = set()
                    for r in rr:
                        lid, rent = r["listing_id"], float(r["listed_rent"])
                        on_page.add(lid)
                        if lid in rows:
                            if rent > HELD_MAX:
                                mark_gone(lid, "rent on the page is now above $3,000", at, status, r["listed_rent"])
                                continue
                        elif rent > MAX_RENT:
                            continue
                        old = before.get(lid) or rows.get(lid)
                        if old:
                            r["first_seen"] = min(old["first_seen"], r["first_seen"])
                            if old.get("listed_rent") and float(old["listed_rent"]) != rent:
                                r["notes"] += f"; trawl2: listed_rent was {old['listed_rent']} on {old['last_seen'][:10]}"
                            if old.get("available_date") != r["available_date"]:
                                r["notes"] += f"; trawl2: available_date was {old.get('available_date') or 'empty'} on {old['last_seen'][:10]}"
                        rows[lid] = r
                        gone.pop(lid, None)  # back on the page
                    for lid in hp:
                        if lid not in on_page and lid in rows:
                            mark_gone(lid, "unit no longer listed on its property page", at, status)
        stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1
        checked[pslug] = {"at": at, "status": status, "reason": reason}

    def fresh(pslug):
        c = checked.get(pslug)
        if not c or c.get("reason") == "no_listing_object":   # re-read (from the fresh cache) by the current parser
            return False
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(c["at"])).total_seconds() / 3600
        return age <= (MAX_AGE_H or 24)

    def run():
        # cities the gazetteer could not place: coordinates from their own first search page
        cl = list(cities)
        for slug in unmatched:
            try:
                html, meta = fetch(f"/{slug}/{FILTERS[0]}")
            except Transient as e:
                stats["transient"].append(f"{slug}: {e}")
                continue
            stats["srp_pages"] += 1
            c = page_city_coords(flight(html), slug) if meta["status"] == 200 else None
            if not c:
                stats["cities_unmatched_far"].append({"city": slug, "why": "no coordinates on page"})
                continue
            z, d = nearest_grid(grid, *c)
            if d <= CITY_KM and z[3] <= a.max_drive:
                cl.append((z[3], slug, z[0]))
            else:
                stats["cities_unmatched_far"].append({"city": slug, "km_to_grid": round(d, 1)})
        groups = {g: [] for g in PRIORITY + ("rest",)}
        for drive, slug, zc in cl:
            ar = area_of(slug[:2], zc, slug)
            groups[ar if ar in PRIORITY else "rest"].append((drive, slug, ar))
        for g in groups.values():
            g.sort()
        log("cities by group:", {g: len(v) for g, v in groups.items()})

        t0 = datetime.now(timezone.utc)
        for g in PRIORITY + ("rest",):
            for drive, slug, ar in groups[g]:
                if a.minutes and (datetime.now(timezone.utc) - t0).total_seconds() > a.minutes * 60:
                    stats.setdefault("not_reached_time_budget", []).append(slug)
                    continue
                try:
                    found = discover_city(slug, stats)
                except Transient as e:
                    stats["transient"].append(f"{slug} search: {str(e)[:120]}")
                    found = {}
                hp = held_by_prop()
                n = 0
                for pslug, lp in sorted(found.items()):
                    if fresh(pslug):
                        continue
                    stats["props_considered"] += 1
                    holds_le = any(float(rows[l]["listed_rent"]) <= MAX_RENT for l in hp.get(pslug, []))
                    if isinstance(lp, (int, float)) and lp > a.fetch_max_low and not holds_le:
                        stats["props_skipped_lowprice"] += 1
                        continue
                    process_prop(pslug)
                    n += 1
                stats["cities_done"].append({"city": slug, "group": g, "drive_min": drive, "props": len(found), "read": n})
                save_all()
                log(f"[{g}] {slug} drive={drive} props={len(found)} read={n} rows={len(rows)} gone={len(gone)} srp={stats['srp_pages']}")
            # held properties of this group with a unit <= MAX_RENT that no search page led to: re-read them too
            sweep = sorted({r["url"][len(BASE):] for r in rows.values() if float(r["listed_rent"]) <= MAX_RENT and
                            (area_of(r["state"], r["zip"]) if area_of(r["state"], r["zip"]) in PRIORITY else "rest") == g})
            sweep = [p for p in sweep if not fresh(p)]
            log(f"[{g}] sweep of held properties not reached by search: {len(sweep)}")
            for i, pslug in enumerate(sweep):
                process_prop(pslug)
                if i % 25 == 24:
                    save_all()
            stats.setdefault("sweeps", {})[g] = len(sweep)
            save_all()

    try:
        run()
    except Blocked as e:
        stats["blocked"] = str(e)
        stats["finished"] = lib.now_iso()
        save_all()
        raise
    stats["finished"] = lib.now_iso()
    stats["rows_total"] = len(rows)
    stats["gone_total"] = len(gone)
    save_all()


def main():
    global REFRESH, MAX_AGE_H
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--trawl2", action="store_true", help="second trawl (see the module docstring)")
    ap.add_argument("--max-age-hours", type=float, default=0, help="refetch cached pages older than this")
    ap.add_argument("--max-drive", type=float, default=120.0)
    ap.add_argument("--only", default="")
    ap.add_argument("--fetch-max-low", type=float, default=MAX_RENT,
                    help="skip the property page when the search page's lowest price is above this")
    ap.add_argument("--reparse", action="store_true",
                    help="first rebuild every existing row from its cached property page (no network)")
    ap.add_argument("--min-drive", type=float, default=0, help="skip cities nearer than this (already harvested)")
    ap.add_argument("--minutes", type=float, default=0, help="stop starting new cities after this many minutes")
    a = ap.parse_args()
    REFRESH = a.refresh
    MAX_AGE_H = a.max_age_hours

    grid = load_grid()
    grid_zips = {z[0]: z[3] for z in grid}
    cities, unmatched, far, n_slugs = city_list(grid, a.max_drive)
    log(f"sitemap cities in {STATES}: {n_slugs}; in grid: {len(cities)}; far: {far}; unmatched by gazetteer: {len(unmatched)}")
    if a.only:
        only = set(a.only.split(","))
        cities = [c for c in cities if c[1] in only]
        unmatched = [u for u in unmatched if u in only]
    if a.trawl2:
        T2.mkdir(parents=True, exist_ok=True)
        try:
            trawl2(a, grid, grid_zips, cities, unmatched)
        except Blocked as e:
            record_refusal(str(e), e.url)
            log("REFUSED, stopping; host written to raw/_host_kill_shared.json:", e)
            return 2
        return 0

    rows = load_existing()
    stats = {"started": lib.now_iso(), "args": vars(a), "srp_pages": 0, "detail_pages": 0, "cities_done": [], "cities_unmatched_far": [],
             "props_discovered": 0, "props_skipped_lowprice_gt_3000": 0, "reasons": {}, "blocked": None,
             "dogs_no_rows": 0}
    done_props: set = set()
    if a.reparse:
        n_pages = n_rows = n_gone = 0
        for rp in sorted({r["raw_path"] for r in rows.values() if r.get("raw_path")}):
            fp, mp = lib.ROOT / rp, lib.ROOT / (rp.rsplit(".", 1)[0] + ".meta.json")
            if not (fp.exists() and mp.exists()):
                continue
            meta = json.loads(mp.read_text())
            L = parse_listing(fp.read_bytes().decode("utf8", "replace"))
            if not L:
                continue
            rr, _ = build_rows(L, meta["url"][len(BASE):], meta, grid_zips, grid)
            new_ids = {r["listing_id"] for r in rr}
            for lid in [k for k, r in rows.items() if r.get("raw_path") == rp and k not in new_ids]:
                n_gone += 1  # kept as is: same cached page, should not happen
            for r in rr:
                old = rows.get(r["listing_id"])
                if old:
                    r["first_seen"] = min(old["first_seen"], r["first_seen"])
                rows[r["listing_id"]] = r
                n_rows += 1
            n_pages += 1
        save(rows)
        log(f"reparse: pages={n_pages} rows rebuilt={n_rows} rows not regenerated={n_gone} total={len(rows)} "
            f"with concession={sum(1 for r in rows.values() if r.get('concession_text'))}")

    import time as _t
    t0 = _t.time()

    def do_city(slug, drive):
        if a.minutes and _t.time() - t0 > a.minutes * 60:
            stats.setdefault("not_reached_time_budget", []).append({"city": slug, "drive_min": drive})
            return
        found = discover_city(slug, stats)
        n_new = n_rows = 0
        for pslug, lp in sorted(found.items()):
            if pslug in done_props:
                continue
            done_props.add(pslug)
            stats["props_discovered"] += 1
            if isinstance(lp, (int, float)) and lp > a.fetch_max_low:
                stats["props_skipped_lowprice_gt_3000"] += 1
                continue
            html, meta = fetch(pslug)
            stats["detail_pages"] += 1
            if meta["status"] != 200:
                reason, rr = f"http_{meta['status']}", []
            else:
                L = parse_listing(html)
                if not L:
                    reason, rr = "no_listing_object", []
                else:
                    rr, reason = build_rows(L, pslug, meta, grid_zips, grid)
            stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1
            for r in rr:
                old = rows.get(r["listing_id"])
                if old:
                    r["first_seen"] = min(old["first_seen"], r["first_seen"])
                rows[r["listing_id"]] = r
                n_rows += 1
            n_new += 1
        stats["cities_done"].append({"city": slug, "drive_min": drive, "props": len(found), "rows": n_rows})
        save(rows)
        STATS.write_text(json.dumps(stats, indent=1))
        log(f"{slug} drive={drive} props={len(found)} fetched={n_new} rows={n_rows} total_rows={len(rows)} "
            f"srp={stats['srp_pages']} detail={stats['detail_pages']}")

    def do_unmatched():
        # cities the gazetteer could not place: read coordinates from their own first search page
        for slug in unmatched:
            html, meta = fetch(f"/{slug}/{FILTERS[0]}")
            stats["srp_pages"] += 1
            c = page_city_coords(flight(html), slug) if meta["status"] == 200 else None
            if not c:
                stats["cities_unmatched_far"].append({"city": slug, "why": "no coordinates on page"})
                continue
            z, d = nearest_grid(grid, *c)
            if d <= CITY_KM and z[3] <= a.max_drive:
                do_city(slug, z[3])
            else:
                stats["cities_unmatched_far"].append({"city": slug, "km_to_grid": round(d, 1)})

    try:
        for drive, slug, *_ in [c for c in cities if a.min_drive <= c[0] <= 50]:
            do_city(slug, drive)
        if not a.min_drive:
            do_unmatched()  # mostly NJ townships 30-70 min out; done after the <= 50 min cities
        for drive, slug, *_ in [c for c in cities if c[0] > max(50, a.min_drive - 1e-9)]:
            do_city(slug, drive)
    except Blocked as e:
        stats["blocked"] = str(e)
        log("BLOCKED, stopping:", e)
    stats["finished"] = lib.now_iso()
    stats["rows_total"] = len(rows)
    save(rows)
    STATS.write_text(json.dumps(stats, indent=1))
    log("done", json.dumps({k: stats[k] for k in ("srp_pages", "detail_pages", "props_discovered",
                                                 "props_skipped_lowprice_gt_3000", "reasons", "blocked", "rows_total")}))
    return 0 if not stats["blocked"] else 2


if __name__ == "__main__":
    sys.exit(main())
