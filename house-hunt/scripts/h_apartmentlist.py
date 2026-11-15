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

MAX_RENT = 3000
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


class Blocked(Exception):
    pass


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
    try:
        content, meta = lib.cached_get(BASE + path, SRC, ext="html",
                                       refresh=REFRESH if refresh is None else refresh)
    except RuntimeError as e:  # lib retries 429/5xx three times, then raises
        raise Blocked(str(e))
    if meta["status"] in (403, 429):
        raise Blocked(f"HTTP {meta['status']} {path}")
    html = content.decode("utf8", "replace")
    if meta["status"] == 200 and re.search(r"captcha|px-captcha|cf-challenge|Just a moment", html[:20000], re.I):
        raise Blocked(f"challenge page {path}")
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
            cities.append((z[3], s))
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


def build_rows(L, pslug, meta, grid_zips, grid):
    """Return (rows, reason). rows = list of dicts for studio/1BR units <= MAX_RENT."""
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
        specials.append(txt(s.get("description") or s.get("title") or s) if isinstance(s, dict) else txt(s))
    concession = " | ".join(x for x in specials if x)[:600]

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
            if not isinstance(rent, (int, float)) or rent <= 0 or rent > MAX_RENT:
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
            if isinstance(price, (int, float)) and 0 < price <= MAX_RENT:
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


def main():
    global REFRESH
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--max-drive", type=float, default=120.0)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    REFRESH = a.refresh

    grid = load_grid()
    grid_zips = {z[0]: z[3] for z in grid}
    cities, unmatched, far, n_slugs = city_list(grid, a.max_drive)
    log(f"sitemap cities in {STATES}: {n_slugs}; in grid: {len(cities)}; far: {far}; unmatched by gazetteer: {len(unmatched)}")
    if a.only:
        only = set(a.only.split(","))
        cities = [c for c in cities if c[1] in only]
        unmatched = [u for u in unmatched if u in only]

    rows = load_existing()
    stats = {"started": lib.now_iso(), "srp_pages": 0, "detail_pages": 0, "cities_done": [], "cities_unmatched_far": [],
             "props_discovered": 0, "props_skipped_lowprice_gt_3000": 0, "reasons": {}, "blocked": None,
             "dogs_no_rows": 0}
    done_props: set = set()

    def do_city(slug, drive):
        found = discover_city(slug, stats)
        n_new = n_rows = 0
        for pslug, lp in sorted(found.items()):
            if pslug in done_props:
                continue
            done_props.add(pslug)
            stats["props_discovered"] += 1
            if isinstance(lp, (int, float)) and lp > MAX_RENT:
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
        for drive, slug in [c for c in cities if c[0] <= 50]:
            do_city(slug, drive)
        do_unmatched()  # mostly NJ townships 30-70 min out; done after the <= 50 min cities
        for drive, slug in [c for c in cities if c[0] > 50]:
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
