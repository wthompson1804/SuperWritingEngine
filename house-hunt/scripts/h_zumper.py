#!/usr/bin/env python3
"""Zumper harvest: studios and 1BRs with listed rent <= $3,000 inside data/reference/search_grid.csv.

Stages (each idempotent and resumable; pages are cached under raw/zumper/ by lib.cached_get):

  python3 scripts/h_zumper.py search    # city search pages, nearest-first, discovers cities via nearby_cities
  python3 scripts/h_zumper.py details   # listing and building detail pages for every qualifying card
  python3 scripts/h_zumper.py build     # normalise caches -> data/listings_raw/zumper.csv
  python3 scripts/h_zumper.py all
  python3 scripts/h_zumper.py targets FILE.csv   # fetch only the pages in FILE.csv (column `url`, optional
                                                 # `building_url`; one request per building), then rebuild

Options: --max-min N (seconds budget for a fetching stage), --refresh (refetch cached pages; updates last_seen).

robots.txt (group `*`, there is no Claude-specific group, no Crawl-delay; read 2026-11-15): only path-based
URLs are used: /apartments-for-rent/<city>/<studios|1-beds>/under-3000 (+ ?page=N, which `*` does not
disallow), /listings/<id>p/<slug>, /apartment-buildings/p<id>/<slug>. Nothing under /api, /json, /map, and no
?box= / ?bedrooms= / ?listingId= parameters. 2.2 s between requests. Any 403 / 429 / CAPTCHA stops the run.
"""
from __future__ import annotations

import csv
import heapq
import html as htmllib
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import lib

SRC = "zumper"
BASE = "https://www.zumper.com"
lib.HOST_DELAY["www.zumper.com"] = 2.2
RAWD = lib.RAW / SRC
CITIES_F = RAWD / "cities.json"          # discovered cities and search status
TARGETS_F = RAWD / "targets_map.json"    # written by `targets`: listing path -> building path, page list
CARDS_F = RAWD / "cards.jsonl"           # one line per (search page, card)
BLOCK_F = RAWD / "BLOCKED.txt"
OUT = lib.DATA / "listings_raw" / "zumper.csv"
GRID = lib.DATA / "reference" / "search_grid.csv"
MAX_RENT = 3000
SEEDS = ["new-york-ny", "queens-ny", "stamford-ct", "jersey-city-nj", "hempstead-ny", "white-plains-ny",
         "newark-nj", "new-haven-ct", "poughkeepsie-ny", "trenton-nj", "riverhead-ny", "morristown-nj",
         "bridgeport-ct", "nyack-ny", "toms-river-nj", "allentown-pa", "danbury-ct", "middletown-ny"]
COLS = ("listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,"
        "unit,beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,"
        "dog_policy_text,dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,"
        "other_monthly_fees_json,utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,"
        "building_url,raw_path,notes").split(",")


class Blocked(Exception):
    pass


# ---------------------------------------------------------------- fetch
def fetch(path: str, refresh: bool = False):
    """Return (state_dict | None, meta, html_text). Raises Blocked on 403/429/CAPTCHA."""
    if BLOCK_F.exists():
        raise Blocked(BLOCK_F.read_text())
    url = BASE + path
    try:
        content, meta = lib.cached_get(url, SRC, ext="html", refresh=refresh, retries=2)
    except RuntimeError as e:
        if "429" in str(e):
            BLOCK_F.write_text(f"{lib.now_iso()} 429 {url}\n")
            raise Blocked(str(e))
        raise
    text = content.decode("utf8", "replace")
    if meta["status"] in (403, 429) or (meta["status"] == 200 and "__PRELOADED_STATE__" not in text
                                        and re.search(r"captcha|are you a robot|access denied", text, re.I)):
        BLOCK_F.write_text(f"{lib.now_iso()} {meta['status']} {url}\n")
        raise Blocked(f"HTTP {meta['status']} {url}")
    return parse_state(text), meta, text


def parse_state(text: str):
    i = text.find("window.__PRELOADED_STATE__ = ")
    if i < 0:
        return None
    try:
        st, _ = json.JSONDecoder().raw_decode(text[i + len("window.__PRELOADED_STATE__ = "):])
        return st
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------- grid
def load_grid():
    rows = []
    for r in csv.DictReader(open(GRID)):
        try:
            rows.append((r["zcta"].zfill(5), float(r["lat"]), float(r["lon"]), float(r["drive_min"])))
        except ValueError:
            pass
    return rows


def hav_km(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


def nearest_grid(grid, lat, lng):
    best = (1e9, None, None)
    for z, la, lo, dm in grid:
        if abs(la - lat) > 0.25 or abs(lo - lng) > 0.3:
            continue
        d = hav_km(lat, lng, la, lo)
        if d < best[0]:
            best = (d, z, dm)
    return best


# ---------------------------------------------------------------- search stage
def b01(city: dict):
    """(studio count, 1BR count) from a nearby_cities record, or (None, None)."""
    inv = city.get("inventory_counts") or {}
    if not inv:
        return None, None
    s = o = 0
    for v in inv.values():
        b = (v or {}).get("bedrooms") or {}
        s += b.get("0", 0) or 0
        o += b.get("1", 0) or 0
    return s, o


def slim_card(x: dict) -> dict:
    drop = {"short_description", "image_ids", "amenity_groups", "__typename"}
    y = {k: v for k, v in x.items() if k not in drop}
    y["image_id0"] = (x.get("image_ids") or [None])[0]
    return y


def search(max_min: float, refresh: bool):
    grid = load_grid()
    cities = json.loads(CITIES_F.read_text()) if CITIES_F.exists() else {}
    t0 = time.time()

    def note_city(c: dict):
        slug = c.get("url")
        if not slug or slug in cities:
            return
        lat, lng = c.get("lat"), c.get("lng")
        if lat is None or lng is None:
            return
        d, z, dm = nearest_grid(grid, lat, lng)
        s, o = b01(c)
        cities[slug] = {"name": c.get("name"), "state": c.get("state"), "lat": lat, "lng": lng,
                        "listing_count": c.get("listing_count"), "studios": s, "onebeds": o,
                        "grid_km": round(d, 2) if z else None, "grid_zcta": z, "drive_min": dm,
                        "in_area": bool(z) and d <= 8.0, "status": "new"}

    for s in SEEDS:
        cities.setdefault(s, {"name": s, "state": s[-2:].upper(), "lat": None, "lng": None, "listing_count": None,
                              "studios": None, "onebeds": None, "grid_km": 0, "grid_zcta": None,
                              "drive_min": 0 if s in ("new-york-ny", "queens-ny") else 60, "in_area": True,
                              "status": "new"})
    if refresh:
        for c in cities.values():
            if c["status"] == "done":
                c["status"] = "new"

    cards_out = open(CARDS_F, "a")
    n_pages = n_cards = 0

    def run_search(slug: str, bed: str):
        """Fetch all pages of one city/bed search. Returns state of page 1."""
        nonlocal n_pages, n_cards
        first = None
        page = 1
        while True:
            path = f"/apartments-for-rent/{slug}/{bed}/under-{MAX_RENT}" + (f"?page={page}" if page > 1 else "")
            st, meta, _ = fetch(path, refresh)
            n_pages += 1
            if st is None:
                return first
            if first is None:
                first = st
            cs = st.get("currentSearch") or {}
            L = cs.get("listables") or {}
            q = L.get("query") or {}
            # guard: the bed filter must have been understood as a filter, not as a neighbourhood slug
            if "bedrooms" not in q or q.get("neighborhood"):
                return first
            items = [(x, "match") for x in (L.get("listables") or [])]
            nb = ((L.get("nearby") or {}).get("matches") or {}).get("listables") or []
            items += [(x, "nearby") for x in nb]
            for x, kind in items:
                cards_out.write(json.dumps({"seen": meta["retrieved_at"], "search": path, "kind": kind,
                                            "raw_path": meta["path"], "card": slim_card(x)}) + "\n")
                n_cards += 1
            cards_out.flush()
            if not cs.get("hasMoreListables") or not L.get("listables") or page >= 40:
                return first
            page += 1

    try:
        while True:
            todo = [(c["drive_min"] if c["drive_min"] is not None else 999, s) for s, c in cities.items()
                    if c["status"] == "new" and c["in_area"]]
            if not todo:
                break
            if max_min and time.time() - t0 > max_min * 60:
                print("time budget reached")
                break
            _, slug = heapq.nsmallest(1, todo)[0]
            c = cities[slug]
            s, o = c["studios"], c["onebeds"]
            if c["listing_count"] == 0 or (s == 0 and o == 0):
                c["status"] = "skipped_no_inventory"
                continue
            # 1-beds first (it also carries the nearby_cities list), studios unless the city shows none.
            st = run_search(slug, "1-beds")
            if st is None:
                c["status"] = "no_state"
                CITIES_F.write_text(json.dumps(cities, indent=0))
                continue
            for nc in ((st.get("geo") or {}).get("nearby_cities") or []):
                note_city(nc)
            cc = (st.get("currentSearch") or {}).get("city") or {}
            if c["lat"] is None and cc.get("lat") is not None:
                c["lat"], c["lng"], c["name"] = cc["lat"], cc["lng"], cc.get("name")
                c["listing_count"] = cc.get("listing_count")
                d, z, dm = nearest_grid(grid, cc["lat"], cc["lng"])
                if z:
                    c["grid_km"], c["grid_zcta"], c["drive_min"] = round(d, 2), z, dm
            if s != 0:
                run_search(slug, "studios")
            c["status"] = "done"
            c["searched_at"] = lib.now_iso()
            CITIES_F.write_text(json.dumps(cities, indent=0))
            if sum(1 for x in cities.values() if x["status"] == "done") % 25 == 0:
                print(f"cities done {sum(1 for x in cities.values() if x['status']=='done')} "
                      f"known {len(cities)} pages {n_pages} cards {n_cards} last {slug}", flush=True)
    except Blocked as e:
        print("BLOCKED:", e)
    finally:
        CITIES_F.write_text(json.dumps(cities, indent=0))
        cards_out.close()
    from collections import Counter
    print("search stage:", dict(Counter(c["status"] for c in cities.values() if c["in_area"])),
          "out_of_area", sum(1 for c in cities.values() if not c["in_area"]), "pages", n_pages, "cards", n_cards)


# ---------------------------------------------------------------- cards -> targets
def load_cards():
    """Latest card per listing_id, restricted to grid ZIPs, beds <= 1, min_price <= cap."""
    grid = {z: dm for z, _, _, dm in load_grid()}
    best = {}
    stats = {"lines": 0, "zip_not_in_grid": 0, "beds_gt1": 0, "over_cap": 0}
    if not CARDS_F.exists():
        return {}, stats
    for line in open(CARDS_F):
        stats["lines"] += 1
        r = json.loads(line)
        c = r["card"]
        lid = c.get("listing_id")
        if lid is None:
            continue
        prev = best.get(lid)
        if prev is None:
            r["first_seen"] = r["seen"]
            best[lid] = r
        else:
            r["first_seen"] = min(prev["first_seen"], r["seen"])
            if r["seen"] >= prev["seen"]:
                best[lid] = r
            else:
                prev["first_seen"] = r["first_seen"]
    out = {}
    for lid, r in best.items():
        c = r["card"]
        z = (c.get("zipcode") or "").zfill(5)[:5]
        if z not in grid:
            stats["zip_not_in_grid"] += 1
            continue
        if (c.get("min_bedrooms") or 0) > 1:
            stats["beds_gt1"] += 1
            continue
        if c.get("min_price") is None or c["min_price"] > MAX_RENT:
            stats["over_cap"] += 1
            continue
        r["drive_min"] = grid[z]
        out[lid] = r
    return out, stats


def details(max_min: float, refresh: bool):
    cards, stats = load_cards()
    print("cards:", stats, "qualifying", len(cards))
    urls = {}
    for r in cards.values():
        u = r["card"].get("url")
        if u and (u.startswith("/listings/") or u.startswith("/apartment-buildings/")):
            urls[u] = min(urls.get(u, 1e9), r["drive_min"])
    order = sorted(urls, key=lambda u: (urls[u], u))
    print("detail urls", len(order))
    t0 = time.time()
    n = fetched = 0
    try:
        for u in order:
            if max_min and time.time() - t0 > max_min * 60:
                print("time budget reached")
                break
            st, meta, _ = fetch(u, refresh)
            n += 1
            # a /listings/ page that belongs to a building: fetch the building page too
            if st and u.startswith("/listings/"):
                e = ((st.get("detail") or {}).get("entity") or {}).get("data") or {}
                if e.get("pb_id") and e.get("pb_url"):
                    fetch(f"/apartment-buildings/p{e['pb_id']}/{e['pb_url']}", refresh)
            if n % 100 == 0:
                print(f"details {n}/{len(order)} elapsed {int(time.time()-t0)}s", flush=True)
    except Blocked as e:
        print("BLOCKED:", e)
    print("details stage: visited", n, "of", len(order))


def to_path(u: str) -> str:
    """Zumper URL or path -> robots-allowed path, or '' (query strings are dropped, never sent)."""
    u = (u or "").strip()
    u = re.sub(r"^https?://(www\.)?zumper\.com", "", u).split("?")[0].split("#")[0]
    return u if re.match(r"^/(listings|apartment-buildings)/[^/]+/[^/]+$", u) else ""


def targets(csv_path: str, refresh: bool, max_age_h: float, follow: bool = True):
    """Fetch only the pages named in a CSV (column `url`, optional `building_url`), then rebuild the output CSV.

    One request per building: a row whose `url` or `building_url` is a Zumper building page costs one fetch of
    that page however many units point at it. A /listings/ row is fetched itself only when it has no building
    page, or when the building page does not list it. Cached copies younger than --max-age-h (default 12) are
    reused unless --refresh is given. The price in the output always comes from the page fetched here.
    """
    cards, _ = load_cards()
    lid_by_url = {c["card"].get("url"): lid for lid, c in cards.items()}
    tmap = json.loads(TARGETS_F.read_text()) if TARGETS_F.exists() else {"listing_to_building": {}, "pages": []}
    pages = set(tmap["pages"])
    fetched_now = set()
    stat = {"rows": 0, "skipped_not_zumper": 0, "building_pages": 0, "listing_pages": 0, "reused_cache": 0,
            "non_200": 0}

    def get(path):
        if path in fetched_now:
            return cache_lookup(path)[0]
        st, meta, _ = cache_lookup(path)
        fresh = False
        if st and not refresh:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(meta["retrieved_at"])).total_seconds() / 3600
            fresh = age <= max_age_h
        if fresh:
            stat["reused_cache"] += 1
        else:
            st, meta, _ = fetch(path, refresh=True)
            if meta["status"] != 200:
                stat["non_200"] += 1
                print("  HTTP", meta["status"], path)
            stat["building_pages" if path.startswith("/apartment-buildings/") else "listing_pages"] += 1
        fetched_now.add(path)
        pages.add(path)
        return st

    def ent_of(st):
        return (((st or {}).get("detail") or {}).get("entity") or {}).get("data") or {}

    try:
        for row in csv.DictReader(open(csv_path)):
            stat["rows"] += 1
            u, b = to_path(row.get("url", "")), to_path(row.get("building_url", ""))
            if b and not b.startswith("/apartment-buildings/"):
                b = ""
            if not u and not b:
                stat["skipped_not_zumper"] += 1
                continue
            if u.startswith("/apartment-buildings/"):
                get(u)
                continue
            if u and b:
                e = ent_of(get(b))
                lid = lid_by_url.get(u)
                m = re.match(r"zumper-(\d+)$", row.get("listing_id", "") or "")
                if lid is None and m:
                    lid = int(m.group(1))
                ids = {L.get("listing_id") for L in e.get("floorplan_listings") or []}
                if lid is not None and lid in ids:
                    tmap["listing_to_building"][u] = b
                    continue
                get(u)                      # building page does not list this unit: read the unit page itself
                continue
            if u:
                e = ent_of(get(u))
                if follow and e.get("pb_id") and e.get("pb_url"):
                    get(f"/apartment-buildings/p{e['pb_id']}/{e['pb_url']}")
            else:
                get(b)
            if stat["rows"] % 50 == 0:
                print("targets", stat, flush=True)
    except Blocked as e:
        print("BLOCKED:", e)
    tmap["pages"] = sorted(pages)
    TARGETS_F.write_text(json.dumps(tmap, indent=0))
    print("targets stage:", stat)


# ---------------------------------------------------------------- normalise
def cache_lookup(path: str):
    """(state, meta, text) from cache only, or (None, None, None)."""
    import hashlib
    key = hashlib.sha1(("GET " + BASE + path + " ").encode()).hexdigest()[:16]
    p, mp = RAWD / f"{key}.html", RAWD / f"{key}.meta.json"
    if not (p.exists() and mp.exists()):
        return None, None, None
    text = p.read_text("utf8", "replace")
    return parse_state(text), json.loads(mp.read_text()), text


def visible_text(text: str) -> str:
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.S)
    t = re.sub(r"<[^>]+>", "|", t)
    t = htmllib.unescape(t)
    return re.sub(r"\|[\s|]*", "|", t)


def section(vt: str, start: str, stops: tuple, maxlen: int = 700) -> str:
    """Text of a visible-page block that starts with `|start|` and ends at the first stop marker."""
    i = vt.find("|" + start + "|")
    if i < 0:
        return ""
    s = vt[i + 1:i + 1 + maxlen]
    cut = len(s)
    for st in stops:
        j = s.find("|" + st, len(start))
        if j >= 0:
            cut = min(cut, j)
    return s[:cut].strip("|")


def money(cents):
    if cents is None:
        return None
    v = cents / 100
    return int(v) if v == int(v) else round(v, 2)


def fee_amount(f: dict):
    lo, hi, amt = f.get("min_in_cents"), f.get("max_in_cents"), f.get("amount_in_cents")
    if amt is not None:
        return money(amt), money(amt)
    return money(lo), money(hi if hi is not None else lo)


WORDNUM = {w: i + 1 for i, w in enumerate("one two three four five six seven eight nine ten eleven twelve".split())}
LAUNDRY_UNIT = ("In Unit Laundry", "Washer/Dryer", "Washer Dryer", "In-Unit Laundry", "Washer/Dryer In Unit")
PARK_WORDS = ("Parking", "Garage", "Carport")
UTIL_TAGS = {"Utilities Included": "all utilities", "Heat Included": "heat", "Gas Included": "gas",
             "Water Included": "water", "Electricity Included": "electricity", "Hot Water Included": "hot water",
             "Trash Included": "trash", "Sewer Included": "sewer", "Internet Included": "internet",
             "Cable Included": "cable", "Air Conditioning Included": "air conditioning"}


def facts_from(entity: dict, vt: str, bld: dict | None, bvt: str):
    """Gate facts that are shared by every unit on a detail page (entity = Listing or Building)."""
    f = {}
    tags = set((entity.get("amenity_tags") or []) + (entity.get("building_amenity_tags") or []))
    btags = set()
    if bld:
        btags = set((bld.get("amenity_tags") or []) + (bld.get("building_amenity_tags") or []))
    alltags = tags | btags
    notes = []

    # ---- dogs: the visible "Pets" policy block ("Dog|Policy|Allowed") and the "Dogs OK" amenity chip
    pol = ""
    for src_vt in (vt, bvt):
        if not src_vt:
            continue
        m = re.search(r"\|Pets\|(.{0,900})", src_vt)
        if m:
            seg = m.group(1)
            for stop in ("|Questions about", "|Utilities|", "|Location|", "|Similar", "|Nearby", "|Explore",
                         "|Report this", "|Frequently"):
                j = seg.find(stop)
                if j >= 0:
                    seg = seg[:j]
            pol = "Pets|" + seg.strip("|")
            break
    dogs = "unknown"
    dm = re.search(r"Dog\|Policy\|([^|]+)", pol)
    if re.search(r"Small Dog\|Policy\|Allowed", pol) and not re.search(r"(?<!Small )Dog\|Policy\|Allowed", pol):
        notes.append("policy block lists 'Small Dog' only")
    if dm:
        v = dm.group(1).strip().lower()
        if v.startswith("allowed"):
            dogs = "yes"
        elif v.startswith("not allowed") or v.startswith("no"):
            dogs = "no"
    chips_ok = "|Dogs OK|" in vt or "|Dogs OK|" in (bvt or "")
    if dogs == "unknown" and chips_ok:
        dogs = "yes"
    if dogs == "unknown" and (re.search(r"\|No (Pets|Dogs)( Allowed)?\|", vt) or "No Pets Allowed" in alltags):
        dogs = "no"
        pol = pol or "No Pets"
    txt_parts = []
    if pol:
        txt_parts.append(pol.replace("|", " | "))
    if chips_ok:
        txt_parts.append("amenity chip: Dogs OK")
    # `pets` codes in the page data. Observed against the visible policy block: 1 = cats, 2 = dogs;
    # 3 always appears with 2 (meaning not shown on the page, possibly large dogs).
    codes = sorted(set(entity.get("pets") or []) | set((bld or {}).get("pets") or []))
    if codes:
        txt_parts.append(f"page data pets codes {codes} (1=cat, 2=dog, 3=unlabelled; mapping inferred from pages that show both)")
        if dogs == "unknown" and (2 in codes or 3 in codes):
            dogs = "yes"
            txt_parts.append("dogs=yes rests on the code only; no visible policy block")
        elif dogs == "no" and (2 in codes or 3 in codes):
            notes.append("CONFLICT: policy block says dogs not allowed but page data pets codes include dogs")
        elif dogs == "yes" and dm and 2 not in codes and 3 not in codes:
            notes.append("policy block says dogs allowed; pets codes lack the dog code")
    if dogs == "no" and (chips_ok or re.search(r"\|Dogs Ok\|", vt + (bvt or ""), re.I)):
        notes.append("CONFLICT: 'Dogs OK' amenity shown but policy block says dogs not allowed")
    pp = entity.get("pet_policy") or (bld or {}).get("pet_policy")
    if pp:
        txt_parts.append("pet_policy: " + json.dumps(pp)[:600])
    f["dogs"] = dogs
    f["dog_policy_text"] = " ; ".join(txt_parts)[:1200]
    wl = ""
    wsrc = pol + " " + (json.dumps(pp) if pp else "")
    wm = re.search(r"(\d{2,3})\s*(?:lbs?|pounds?)\b", wsrc, re.I)
    if wm:
        wl = wm.group(1)
    f["dog_weight_limit_lb"] = wl

    # ---- elevator: only a positive tag is evidence; absence of the tag is unknown
    f["elevator"] = "yes" if any("elevator" in t.lower() for t in alltags) else "unknown"
    fl = entity.get("floors") or (bld or {}).get("floors")
    if not fl:
        groups = dict((bld or {}).get("amenity_groups") or {})
        groups.update(entity.get("amenity_groups") or {})
        for t in alltags:
            m = re.fullmatch(r"(\w+) Floors?", t)
            if m and (groups.get(t) or {}).get("group") == 3:      # group 3 = building-level amenity
                w = m.group(1).lower()
                n = int(w) if w.isdigit() else WORDNUM.get(w)
                if n:
                    fl = n
            elif m and (m.group(1).isdigit() or m.group(1).lower() in WORDNUM):
                notes.append(f"tag '{t}' at unit level (unit spans floors?)")
    f["building_floors"] = fl if fl else ""

    # ---- parking
    ptags = sorted(t for t in alltags if any(w in t for w in PARK_WORDS))
    f["parking_type"] = "; ".join(ptags)

    # ---- fees
    fees = entity.get("fees") or (bld or {}).get("fees") or []
    pet_rent, park_fee, other = "", "", []
    for fe in fees:
        name = (fe.get("name") or "").strip()
        lo, hi = fee_amount(fe)
        rec = {"name": name, "min": lo, "max": hi, "cadence": fe.get("cadence"), "type": fe.get("type"),
               "required": fe.get("is_required"), "species": fe.get("species"),
               "desc": (fe.get("description") or "")[:140] or None}
        other.append({k: v for k, v in rec.items() if v is not None})
    f["_fees"] = other
    f["_pet_rent"], f["_park_fee"] = pet_rent, park_fee

    # ---- utilities / laundry
    util = sorted({v for k, v in UTIL_TAGS.items() if k in alltags})
    f["utilities_included"] = "; ".join(util)
    f["_ambig_util"] = sorted(t for t in alltags if t in ("Water", "Gas", "Electricity", "Heat", "Hot Water", "Sewage",
                                                         "Garbage", "Internet", "Cable", "Electric", "Gas Utilities"))
    low = {t.lower() for t in alltags}
    if (any(t in alltags for t in LAUNDRY_UNIT) or any("in-unit laundry" in t or "in unit laundry" in t for t in low)
            or ("washer" in low and "dryer" in low)):
        f["laundry"] = "in_unit"
    elif any("laundry" in t for t in low):
        f["laundry"] = "on_site"
    elif any("hookup" in t for t in low):
        f["laundry"] = "hookups"
    else:
        f["laundry"] = ""
    f["_conc"] = sorted(t for t in alltags if t in ("Free Rent", "No Fee", "Move-in Special", "Move In Special"))
    f["_notes"] = notes
    return f


def fees_block(vt: str) -> str:
    i = vt.find("|Policies and fees|")
    if i < 0:
        return ""
    s = vt[i + 1:i + 2500]
    for stop in ("|Questions about", "|Location|", "|Similar", "|Explore the", "|Report this", "|Frequently",
                 "|Nearby", "|Schools", "|About ", "|Building details|", "|Property details|"):
        j = s.find(stop)
        if j >= 0:
            s = s[:j]
    return s.strip("|")


CADENCE = re.compile(r"^(Monthly|One-time|Per-applicant|Annual|Yearly|Weekly|Situational|Per )", re.I)
AMOUNT = re.compile(r"^(\$[\d,]+(?:\.\d\d)?(?:\s*-\s*\$[\d,]+(?:\.\d\d)?)?|Contact Property|Included|Free|Varies.*)$", re.I)


def parse_fee_text(block: str):
    """Parse the visible 'Policies and fees' block into fee lines.

    The block is a token stream: section headers (REQUIRED FEES, OPTIONAL FEES, Parking, Pets, Dog, Cat ...)
    and triples `name | cadence sentence | amount`. Returns (fees, pet_rent, parking_fee).
    """
    toks = [t.strip() for t in block.split("|") if t.strip()]
    fees = []
    req = ""
    sect = ""
    species = ""
    for i, t in enumerate(toks):
        if t in ("REQUIRED FEES", "OPTIONAL FEES"):
            req = "required" if t.startswith("REQ") else "optional"
            sect = species = ""
        elif t in ("Parking", "Pets", "Storage", "Utilities & Services", "Move-In Fees", "Applicants", "Other",
                   "Other Fees", "Amenities", "Services"):
            sect = t
            species = ""
        elif re.fullmatch(r"(Small |Large )?(Dog|Cat)s?|Other Pets?|Birds?|Fish", t):
            species = t
        if i + 2 < len(toks) and CADENCE.match(toks[i + 1]) and AMOUNT.match(toks[i + 2]):
            fees.append({"name": t, "cadence": CADENCE.match(toks[i + 1]).group(1).strip().lower(),
                         "terms": toks[i + 1], "amount": toks[i + 2], "section": sect, "species": species,
                         "requirement": req})
    def num(a):
        m = re.match(r"\$([\d,]+(?:\.\d\d)?)", a)
        return m.group(1).replace(",", "") if m else ""
    pet = park = ""
    monthly = [f for f in fees if f["cadence"] == "monthly"]
    dogm = [f for f in monthly if "dog" in (f["species"] + " " + f["name"] + " " + f["terms"]).lower() and num(f["amount"])]
    anym = [f for f in monthly if (f["section"] == "Pets" or re.search(r"\bpet\b", f["name"], re.I))
            and "cat" not in f["species"].lower() and num(f["amount"])]
    if dogm:
        pet = num(dogm[0]["amount"])
    elif anym:
        pet = num(anym[0]["amount"])
    pk = [f for f in monthly if (f["section"] == "Parking" or re.search(r"parking|garage|carport", f["name"], re.I))
          and num(f["amount"])]
    if pk:
        park = num(pk[0]["amount"])
        if len(pk) > 1:
            park = "-".join(sorted({num(f["amount"]) for f in pk}, key=float)) if len({num(f["amount"]) for f in pk}) > 1 else park
    return fees, pet, park


def iso_avail(v, today):
    if not v:
        return "", ""
    try:
        d = datetime.strptime(str(v)[:10].replace("/", "-"), "%Y-%m-%d").date()
    except ValueError:
        return str(v), ""
    return str(v), ("now" if d <= today else d.isoformat())


def photo(media_or_id):
    if not media_or_id:
        return ""
    mid = media_or_id
    if isinstance(mid, list):
        mid = (mid[0] or {}).get("media_id") if isinstance(mid[0], dict) else mid[0]
    return f"https://img.zumpercdn.com/{mid}/1280x960" if mid else ""


def ltype(entity_kind: str, prop_type, feed, active_units_hint):
    # Zumper property_type codes seen on pages: 4 apartment (unit in a building), 2 house, 9 condo, 13 townhouse,
    # 1 room. Only clear cases are labelled.
    if entity_kind == "building":
        return "managed_building"
    if prop_type == 9:
        return "condo_coop"
    if prop_type in (2, 13):
        return "unit_in_house"
    return "unknown"


def build():
    cards, stats = load_cards()
    today = datetime.now(timezone.utc).date()
    prev_first = {}
    if OUT.exists():
        for r in csv.DictReader(open(OUT)):
            prev_first[r["listing_id"]] = r["first_seen"]
    rows = {}
    counts = {"cards": len(cards), "detail_rows": 0, "card_rows": 0, "dropped_detail_over_cap": 0,
              "dropped_detail_beds": 0, "dropped_inactive": 0, "extra_units_from_building": 0}
    done_pages = set()

    def base_row(lid, url, level, seen, raw_path):
        r = {c: "" for c in COLS}
        r.update(listing_id=f"zumper-{lid}", source_site="zumper", url=BASE + url, detail_level=level,
                 first_seen=seen, last_seen=seen, raw_path=raw_path, dogs="unknown", elevator="unknown",
                 listing_type="unknown", price_basis="base_rent_monthly")
        return r

    def fill_common(r, f, block):
        for k in ("dogs", "dog_policy_text", "dog_weight_limit_lb", "elevator", "building_floors", "parking_type",
                  "utilities_included", "laundry"):
            r[k] = f[k]
        lines, pet, park = parse_fee_text(block)
        r["pet_rent"], r["parking_fee"] = pet, park
        blob = {}
        mon = [x for x in lines if x["cadence"] == "monthly"]
        if mon:
            blob["monthly"] = [{k: v for k, v in x.items() if v and k != "cadence"} for x in mon]
        oth = [x for x in lines if x["cadence"] != "monthly"]
        if oth:
            blob["non_monthly"] = [{"name": x["name"], "amount": x["amount"], "cadence": x["cadence"],
                                    "requirement": x["requirement"]} for x in oth]
        if f["_fees"]:
            blob["page_data_fees"] = f["_fees"]   # cadence code: 30 monthly, 0 one-time, -1 situational
        if f.get("_ambig_util"):
            blob["utility_tags_unclear_if_included"] = f["_ambig_util"]
        r["other_monthly_fees_json"] = json.dumps(blob, ensure_ascii=False) if blob else ""

    def unit_row(L, url, level, seen, raw_path, bld, f, block, vt, kind):
        loc = L.get("listing_location") or {}
        r = base_row(L["listing_id"], url, level, seen, raw_path)
        fill_common(r, f, block)
        notes = list(f.get("_notes") or [])
        r["building_name"] = (bld or {}).get("name") or L.get("building_name") or ""
        addr = loc.get("formatted_address") or L.get("address") or (bld or {}).get("formatted_address") or ""
        r["address"] = addr
        r["city"] = loc.get("city") or (bld or {}).get("city") or ""
        r["state"] = loc.get("state") or (bld or {}).get("state") or ""
        r["zip"] = loc.get("zipcode") or (bld or {}).get("zipcode") or ""
        r["lat"] = loc.get("lat") or (bld or {}).get("lat") or ""
        r["lon"] = loc.get("lng") or (bld or {}).get("lng") or ""
        unit = loc.get("unit") or ""
        title = L.get("title") or ""
        if not unit:
            m = re.search(r"(?:#|\b(?:Unit|Apt\.?|APT|Apartment)\s*#?\s*)([A-Za-z]?\d+[A-Za-z]?|\d*[A-Za-z]{1,2}\d*)\b",
                          (L.get("address") or "") + " | " + title)
            if m:
                unit = m.group(1)
                notes.append("unit parsed from title/address")
        unit = re.sub(r"^(?:#|\s|unit|apt\.?|apartment)+", "", str(unit), flags=re.I).strip(" #")
        r["unit"] = unit
        r["floor"] = loc.get("floor") if loc.get("floor") is not None else ""
        if r["floor"] == "":
            ORD = (r"(ground|first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|sixth|6th|seventh|7th|"
                   r"eighth|8th|ninth|9th|tenth|10th|\d{1,2}(?:st|nd|rd|th))")
            own = (L.get("description") or "") + " " + (L.get("short_description") or "") + " " + title
            m = re.search(r"\b(?:located|situated|unit|apartment|apt|studio|bedroom|home|residence|is) (?:is )?"
                          r"(?:conveniently )?(?:located |situated )?on the " + ORD + r"[- ]floor\b", own, re.I) or \
                re.search(r"\b" + ORD + r"[- ]floor (?:unit|apartment|apt|studio|one[- ]bedroom|1[- ]?(?:br|bed(?:room)?)|"
                          r"walk[- ]?up|corner|rear|front)\b", own, re.I)
            if m:
                w = m.group(1).lower()
                n = {"ground": 1, "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
                     "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}.get(w)
                if n is None and w[0].isdigit():
                    n = int(re.match(r"\d+", w).group(0))
                if n:
                    r["floor"] = n
                    notes.append(f"floor from description text: '{m.group(0)}'" + (" (ground)" if w == "ground" else ""))
            else:
                m = re.search(r"\b" + ORD + r"[- ]floor\b", own, re.I)
                if m:
                    notes.append(f"floor text in description (not used): '{m.group(0)}'")
        r["beds"] = L.get("bedrooms") if L.get("bedrooms") is not None else ""
        hb = L.get("half_bathrooms") or 0
        ba = L.get("bathrooms")
        r["baths"] = (ba + 0.5 * hb) if ba is not None else ""
        r["sqft"] = L.get("square_feet") or (L.get("unit_data") or {}).get("min_square_feet") or ""
        if r["sqft"] == "":
            cs = (cards.get(L.get("listing_id")) or {}).get("card", {}).get("min_square_feet")
            if cs:
                notes.append(f"sqft absent on detail page; search card showed {cs}")
        price = L.get("min_price") if L.get("min_price") is not None else L.get("price")
        r["listed_rent"] = price
        if L.get("max_price") and L.get("max_price") != price:
            notes.append(f"price range {price}-{L['max_price']}")
        if L.get("fee_uplift"):
            notes.append(f"fee_uplift={L['fee_uplift']}")
        if L.get("base_min_price") is not None and L.get("base_min_price") != price:
            notes.append(f"base_min_price={L['base_min_price']}")
        sp = (bld or {}).get("specials") or L.get("specials")
        conc = []
        if sp:
            conc.append(json.dumps(sp, ensure_ascii=False)[:400])
        if f.get("_conc"):
            conc.append("tags: " + ", ".join(f["_conc"]))
        r["concession_text"] = " ; ".join(conc)
        r["available_date_text"], r["available_date"] = iso_avail(L.get("date_available"), today)
        mgr = L.get("brokerage_name") or (bld or {}).get("brokerage_name") or ""
        ag = (L.get("listing_agents") or (bld or {}).get("agents") or [{}])[0]
        r["manager"] = mgr or ag.get("company_name") or ag.get("long_name") or (bld or {}).get("agent_name") or ""
        lo = L.get("listed_on") or L.get("created_on")
        if lo:
            r["listing_age_days"] = max(0, (today - datetime.fromtimestamp(lo, timezone.utc).date()).days)
        if L.get("created_on") and L.get("listed_on") and L["created_on"] != L["listed_on"]:
            notes.append("created_on=" + datetime.fromtimestamp(L["created_on"], timezone.utc).date().isoformat())
        r["photo_url"] = photo(L.get("media")) or photo((bld or {}).get("media"))
        if bld and bld.get("pb_id"):
            r["building_url"] = f"{BASE}/apartment-buildings/p{bld['pb_id']}/{bld.get('pb_url')}"
        r["listing_type"] = ltype(kind, L.get("property_type"), L.get("feed_name"), None)
        if L.get("feed_name") or (bld or {}).get("feed_name"):
            notes.append("feed=" + str(L.get("feed_name") or bld.get("feed_name")))
        if L.get("provider_url"):
            notes.append("provider_url=" + L["provider_url"])
        if L.get("lease_terms"):
            notes.append("lease_terms=" + str(L["lease_terms"])[:80])
        if L.get("active_units"):
            notes.append(f"active_units={L['active_units']}")
        if L.get("income_restrictions_json") or (bld or {}).get("income_restrictions"):
            notes.append("income_restricted")
        desc = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", L.get("description") or "")))
        if not desc and bld:
            desc = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", bld.get("description") or "")))
        keys = re.compile(r"\b(fees?|pets?|dogs?|cats?|lbs?|pounds|floor|elevator|walk[- ]?up|utilit\w+|included|"
                          r"available|parking|garage|heat|hot water|move[- ]in)\b", re.I)
        sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\s[•*-]\s", desc) if keys.search(x)]
        if sents:
            notes.append("desc: " + " / ".join(sents)[:500])
        if r["elevator"] == "unknown" and re.search(r"walk[- ]?up|no elevator", desc, re.I):
            r["elevator"] = "no"
            notes.append("elevator=no from description (walk-up / no elevator)")
        if r["elevator"] == "unknown" and re.search(r"\belevator\b", desc, re.I) and not re.search(r"no elevator", desc, re.I):
            notes.append("description mentions elevator (not an amenity tag)")
        if r["dogs"] == "unknown" and re.search(r"\bno (pets|dogs)\b|pets? (are )?not (allowed|permitted)", desc, re.I):
            r["dogs"] = "no"
            r["dog_policy_text"] = (r["dog_policy_text"] + " ; description says no pets/dogs").strip(" ;")
        if not r["dog_weight_limit_lb"]:
            for x in sents:
                wm = re.search(r"(\d{2,3})\s*(?:lbs?|pounds?)\b", x, re.I)
                if wm and re.search(r"pet|dog|weight|breed", x, re.I):
                    r["dog_weight_limit_lb"] = wm.group(1)
                    notes.append("weight limit from description")
                    break
        r["notes"] = "; ".join(notes)
        return r

    tmap = json.loads(TARGETS_F.read_text()) if TARGETS_F.exists() else {"listing_to_building": {}, "pages": []}
    l2b = tmap["listing_to_building"]
    card_urls = {c["card"].get("url") for c in cards.values()}
    items = sorted(cards.items(), key=lambda kv: kv[1]["drive_min"])
    # target pages that no search card points at (still normalised if they are cached)
    items += [(None, {"card": {"url": u}}) for u in tmap["pages"] if u not in card_urls]
    for lid, c in items:
        card = c["card"]
        own_url = card.get("url") or ""
        url = own_url
        st, meta, text = cache_lookup(url) if url else (None, None, None)
        alt = l2b.get(own_url)
        if alt:
            ast, ameta, atext = cache_lookup(alt)
            # targets mode read the building page instead of (or after) the listing page: use the newer one
            if ast and (st is None or ameta["retrieved_at"] > meta["retrieved_at"]):
                if alt in done_pages:
                    if lid is not None and f"zumper-{lid}" in rows:
                        rows[f"zumper-{lid}"]["url"] = BASE + own_url
                    else:
                        counts["target_listing_not_active_on_building_page"] = counts.get(
                            "target_listing_not_active_on_building_page", 0) + 1
                    continue
                url, st, meta, text = alt, ast, ameta, atext
        if url in done_pages:
            continue
        ent = (((st or {}).get("detail") or {}).get("entity") or {}).get("data") if st else None
        if not ent and lid is None:
            continue
        if not ent:
            # ---- card only (detail page not fetched yet or not parseable)
            r = base_row(lid, url, "card", c["seen"], c["raw_path"])
            r["first_seen"] = c.get("first_seen", c["seen"])
            r["building_name"] = card.get("building_name") or ""
            r["address"] = card.get("address") or ""
            r["city"], r["state"], r["zip"] = card.get("city") or "", card.get("state") or "", card.get("zipcode") or ""
            r["lat"], r["lon"] = card.get("lat") or "", card.get("lng") or ""
            r["beds"] = card.get("min_bedrooms")
            r["baths"] = card.get("min_bathrooms") if card.get("min_bathrooms") is not None else ""
            r["sqft"] = card.get("min_square_feet") or ""
            r["listed_rent"] = card.get("min_price")
            r["available_date_text"], r["available_date"] = iso_avail(card.get("date_available"), today)
            pets = card.get("pets")
            tags = set((card.get("amenity_tags") or []) + (card.get("building_amenity_tags") or []))
            r["elevator"] = "yes" if any("elevator" in t.lower() for t in tags) else "unknown"
            r["manager"] = card.get("brokerage_name") or card.get("agent_name") or ""
            r["photo_url"] = photo(card.get("image_id0"))
            if pets and (2 in pets or 3 in pets):
                r["dogs"] = "yes"
                r["dog_policy_text"] = (f"card data pets codes {sorted(pets)} (1=cat, 2=dog, 3=unlabelled; mapping "
                                        "inferred from detail pages); detail page not read")
            tl = [t for t in tags if any(w in t for w in PARK_WORDS)]
            r["parking_type"] = "; ".join(sorted(tl))
            n = [f"card only; pets_codes={pets}"]
            if card.get("max_price") != card.get("min_price") or (card.get("floorplan_count") or 1) > 1:
                n.append(f"card price range {card.get('min_price')}-{card.get('max_price')}, "
                         f"floorplans={card.get('floorplan_count')}, beds {card.get('min_bedrooms')}-{card.get('max_bedrooms')}")
            r["notes"] = "; ".join(n)
            rows[r["listing_id"]] = r
            counts["card_rows"] += 1
            continue
        done_pages.add(url)
        vt = visible_text(text)
        seen = meta["retrieved_at"]
        if ent.get("__typename") == "Building" or url.startswith("/apartment-buildings/"):
            f = facts_from(ent, vt, None, "")
            block = fees_block(vt)
            for L in ent.get("floorplan_listings") or []:
                if L.get("listing_status") != 1:
                    counts["dropped_inactive"] += 1
                    continue
                if L.get("bedrooms") is None or L["bedrooms"] > 1:
                    counts["dropped_detail_beds"] += 1
                    continue
                p = L.get("min_price") if L.get("min_price") is not None else L.get("price")
                if p is None or p > MAX_RENT:
                    counts["dropped_detail_over_cap"] += 1
                    continue
                fu = facts_from(L, vt, ent, "")
                for k in ("dogs", "dog_policy_text", "dog_weight_limit_lb", "elevator", "building_floors"):
                    fu[k] = f[k]
                fu["_notes"] = f["_notes"]
                r = unit_row(L, url, "detail", seen, meta["path"], ent, fu, block, vt, "building")
                if r["listing_id"] not in {f"zumper-{x}" for x in cards}:
                    counts["extra_units_from_building"] += 1
                rows[r["listing_id"]] = r
                counts["detail_rows"] += 1
            if url != own_url and lid is not None:
                if f"zumper-{lid}" in rows:
                    rows[f"zumper-{lid}"]["url"] = BASE + own_url
                else:
                    counts["target_listing_not_active_on_building_page"] = counts.get(
                        "target_listing_not_active_on_building_page", 0) + 1
        else:
            bld, bvt, bblock = None, "", ""
            if ent.get("pb_id") and ent.get("pb_url"):
                bst, bmeta, btext = cache_lookup(f"/apartment-buildings/p{ent['pb_id']}/{ent['pb_url']}")
                if bst:
                    bld = (((bst.get("detail") or {}).get("entity") or {}).get("data")) or None
                    bvt = visible_text(btext)
                    bblock = fees_block(bvt)
            if ent.get("listing_status") not in (1, None):
                counts["dropped_inactive"] += 1
                continue
            if ent.get("bedrooms") is None or ent["bedrooms"] > 1:
                counts["dropped_detail_beds"] += 1
                continue
            p = ent.get("min_price") if ent.get("min_price") is not None else ent.get("price")
            if p is None or p > MAX_RENT:
                counts["dropped_detail_over_cap"] += 1
                continue
            f = facts_from(ent, vt, bld, bvt)
            r = unit_row(ent, url, "detail", seen, meta["path"], bld, f, fees_block(vt) or bblock, vt, "listing")
            rows[r["listing_id"]] = r
            counts["detail_rows"] += 1

    # first_seen: earliest of previous CSV, card sighting, this fetch
    for lid_s, r in rows.items():
        cands = [r["first_seen"]]
        if lid_s in prev_first and prev_first[lid_s]:
            cands.append(prev_first[lid_s])
        n = lid_s.split("-")[1]
        if n.isdigit() and int(n) in cards:
            cands.append(cards[int(n)].get("first_seen", cards[int(n)]["seen"]))
        r["first_seen"] = min(cands)
    # ---- building facts settled on a detail page apply to every row at the same street address:
    # dogs only from a building page (a unit page speaks for one landlord's unit), elevator from any detail page.
    def akey(r):
        a = re.split(r",", str(r["address"]))[0].lower()
        a = re.sub(r"\s*(#|\b(?:apt|unit|apartment|ste|suite|fl|floor)\b\.?).*$", "", a)
        a = re.sub(r"[^a-z0-9 ]", "", a)
        a = re.sub(r"\s+", " ", a).strip()
        return (a, str(r["zip"]).zfill(5)[:5]) if a and re.match(r"\d", a) else None
    settled = {}
    for r in rows.values():
        k = akey(r)
        if not k or r["detail_level"] != "detail":
            continue
        d = settled.setdefault(k, {})
        is_bld = "/apartment-buildings/" in r["url"] or "/apartment-buildings/" in r["building_url"]
        if is_bld and r["dogs"] in ("yes", "no") and "rests on the code only" not in r["dog_policy_text"]:
            d.setdefault("dogs", (r["dogs"], r["dog_policy_text"], r["dog_weight_limit_lb"], r["url"]))
        if r["elevator"] == "yes":
            d.setdefault("elevator", r["url"])
        if r["building_floors"] != "":
            d.setdefault("floors", (r["building_floors"], r["url"]))
    counts["propagated_dogs"] = counts["propagated_elevator"] = counts["propagated_floors"] = 0
    for r in rows.values():
        d = settled.get(akey(r) or ())
        if not d:
            continue
        add = []
        if "dogs" in d and d["dogs"][3] != r["url"] and (r["dogs"] == "unknown" or r["detail_level"] == "card"
                                                         or "rests on the code only" in r["dog_policy_text"]):
            if r["dogs"] != d["dogs"][0] or r["detail_level"] == "card":
                prev = r["dogs"]
                r["dogs"], r["dog_weight_limit_lb"] = d["dogs"][0], d["dogs"][2] or r["dog_weight_limit_lb"]
                r["dog_policy_text"] = f"from building page {d['dogs'][3]}: {d['dogs'][1]}"[:1200]
                add.append(f"dogs applied from building page at same address (was {prev})")
                counts["propagated_dogs"] += 1
        if "elevator" in d and r["elevator"] == "unknown":
            r["elevator"] = "yes"
            add.append(f"elevator=yes applied from {d['elevator']} (same address)")
            counts["propagated_elevator"] += 1
        if "floors" in d and r["building_floors"] == "":
            r["building_floors"] = d["floors"][0]
            add.append(f"building_floors applied from {d['floors'][1]}")
            counts["propagated_floors"] += 1
        if add:
            r["notes"] = "; ".join(x for x in [r["notes"]] + add if x)
    # final grid check on detail rows (building units share the building ZIP)
    grid = {z for z, _, _, _ in load_grid()}
    out_rows = [r for r in rows.values() if str(r["zip"]).zfill(5)[:5] in grid]
    counts["dropped_zip_not_in_grid_after_detail"] = len(rows) - len(out_rows)
    dm = {z: d for z, _, _, d in load_grid()}
    out_rows.sort(key=lambda r: (dm.get(str(r["zip"]).zfill(5)[:5], 999), r["listing_id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out_rows)
    counts["rows_written"] = len(out_rows)
    print("card filter:", stats)
    print("build:", counts)
    n = len(out_rows) or 1
    for k in ("available_date", "dogs", "elevator", "floor", "building_floors", "sqft", "unit", "pet_rent",
              "parking_type", "parking_fee", "laundry", "utilities_included", "dog_weight_limit_lb", "manager",
              "photo_url", "other_monthly_fees_json"):
        if k in ("dogs", "elevator"):
            from collections import Counter
            print(" ", k, dict(Counter(r[k] for r in out_rows)))
        else:
            filled = sum(1 for r in out_rows if str(r[k]) != "")
            print(f"  {k}: {filled}/{len(out_rows)} ({100*filled//n}%)")
    from collections import Counter
    print("  detail_level", dict(Counter(r["detail_level"] for r in out_rows)))
    print("  state", dict(Counter(r["state"] for r in out_rows)))


def main():
    a = sys.argv[1:]
    stage = a[0] if a else "all"
    refresh = "--refresh" in a
    max_min = float(a[a.index("--max-min") + 1]) if "--max-min" in a else 0
    RAWD.mkdir(parents=True, exist_ok=True)
    if stage in ("search", "all"):
        search(max_min, refresh)
    if stage in ("details", "all"):
        details(max_min, refresh)
    if stage == "targets":
        # python3 scripts/h_zumper.py targets <file.csv> [--refresh] [--max-age-h 12]
        # --no-follow: exactly one fetch per row (do not also read the building page of a /listings/ row)
        targets(a[1], refresh, float(a[a.index("--max-age-h") + 1]) if "--max-age-h" in a else 12.0,
                follow="--no-follow" not in a)
    if stage in ("build", "all", "targets"):
        build()


if __name__ == "__main__":
    main()
