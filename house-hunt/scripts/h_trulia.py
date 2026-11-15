#!/usr/bin/env python3
"""Trulia rental harvest: studios and 1BRs listed at <= $3,000, by ZIP, nearest-first.

Two phases, both resumable (state in raw/trulia/_state.json, pages cached by lib.cached_get):

  search  /for_rent/<zip>_zip/0-1_beds/0-3000_price/[<n>_p/]  -> card rows (detail_level=card)
  detail  /home/<slug>-<zpid>       -> one row (detail_level=detail)
          /building/<slug>-<id>     -> one row per qualifying unit (detail_level=building_unit)
                                       or per floor plan when the page lists no units (building_floorplan)

Usage:
  python3 scripts/h_trulia.py                       # search every ZIP, then details, nearest-first
  python3 scripts/h_trulia.py --phase search
  python3 scripts/h_trulia.py --phase detail --max-minutes 110
  python3 scripts/h_trulia.py --reparse             # rebuild the CSV from cached pages, no network

Re-running refetches pages older than --refresh-hours (default 20) and updates last_seen.
Stops (exit 3) on 403 / 429 / CAPTCHA and logs it to raw/trulia/_blocks.log. Never retries past a block.
robots.txt (read 2026-11-15): only `User-agent: *` applies (no Claude group, no Crawl-delay);
/for_rent/..._zip/, <n>_beds, <a>-<b>_price, <n>_p, /home/ and /building/ (except /building/*_li) are not disallowed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import ROOT, RAW, DATA, cached_get, now_iso  # noqa: E402

SRC = "trulia"
BASE = "https://www.trulia.com"
OUT = DATA / "listings_raw" / "trulia.csv"
STATE = RAW / SRC / "_state.json"
BLOCKS = RAW / SRC / "_blocks.log"
GRID = DATA / "reference" / "search_grid.csv"
MAX_RENT = 3000
PAGE_SIZE = 40

COLS = ("listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,"
        "unit,beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,"
        "dog_policy_text,dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,"
        "other_monthly_fees_json,utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,"
        "building_url,raw_path,notes").split(",")

NEXT_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
BOT_RE = re.compile(r"px-captcha|perimeterx|captcha-delivery|Access to this page has been denied|are you a human", re.I)


class Blocked(Exception):
    pass


# ---------------------------------------------------------------- fetch

_last_request = 0.0
DELAY = 2.2
N_FETCHED = 0


def _cache_paths(url: str) -> tuple[Path, Path]:
    key = hashlib.sha1(("GET " + url + " ").encode()).hexdigest()[:16]  # same key as lib.cached_get
    return RAW / SRC / f"{key}.html", RAW / SRC / f"{key}.meta.json"


def _age_hours(iso: str) -> float:
    return (datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds() / 3600


def log_block(url: str, what: str) -> None:
    BLOCKS.parent.mkdir(parents=True, exist_ok=True)
    with open(BLOCKS, "a") as f:
        f.write(json.dumps({"at": now_iso(), "url": url, "what": what}) + "\n")


def fetch(url: str, refresh_hours: float, offline: bool = False):
    """Return (next_data_dict | None, meta). None with status 404/410 means the page is gone."""
    global _last_request, N_FETCHED
    path, meta_path = _cache_paths(url)
    cached = path.exists() and meta_path.exists()
    refresh = False
    if cached:
        meta = json.loads(meta_path.read_text())
        if offline or _age_hours(meta["retrieved_at"]) < refresh_hours:
            m = NEXT_RE.search(path.read_text(encoding="utf8", errors="replace"))
            if m:
                return json.loads(m.group(1)), meta
        refresh = True
    if offline:
        return None, {"status": 0, "url": url, "retrieved_at": "", "path": ""}
    for attempt in range(3):
        wait = _last_request + DELAY - time.time()
        if wait > 0:
            time.sleep(wait)
        try:
            content, meta = cached_get(url, SRC, ext="html", refresh=refresh or attempt > 0, retries=1, timeout=45)
        except RuntimeError as e:  # lib raises on 429 / 5xx / network error
            _last_request = time.time()
            msg = str(e)
            if "HTTP 429" in msg:
                log_block(url, "HTTP 429")
                raise Blocked(f"429 at {url}")
            if attempt == 2:
                log_block(url, "gave up: " + msg[-200:])
                raise Blocked(f"repeated errors at {url}: {msg[-200:]}")
            time.sleep(30 * (attempt + 1))
            continue
        _last_request = time.time()
        N_FETCHED += 1
        st = meta["status"]
        if st in (404, 410):
            return None, meta
        if st != 200:
            log_block(url, f"HTTP {st}")
            raise Blocked(f"HTTP {st} at {url}")
        text = content.decode("utf8", errors="replace")
        m = NEXT_RE.search(text)
        if not m:
            what = "bot wall" if BOT_RE.search(text) else "no __NEXT_DATA__"
            path.unlink(missing_ok=True)
            meta_path.unlink(missing_ok=True)
            log_block(url, what)
            raise Blocked(f"{what} at {url}")
        # Keep only the embedded JSON on disk (the rest of the HTML is layout; saves about half the space).
        path.write_text('<!-- trimmed by h_trulia.py: __NEXT_DATA__ only -->\n<script id="__NEXT_DATA__" '
                        'type="application/json">' + m.group(1) + "</script>\n", encoding="utf8")
        return json.loads(m.group(1)), meta
    raise Blocked("unreachable")


# ---------------------------------------------------------------- small parsers

def num(s):
    if s is None:
        return ""
    if isinstance(s, (int, float)):
        return s
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(s))
    return float(m.group(0).replace(",", "")) if m else ""


def fmt(n):
    if n == "" or n is None:
        return ""
    return str(int(n)) if float(n) == int(n) else str(n)


def beds_of(b):
    """-> (min_beds, max_beds) or (None, None)."""
    if not b:
        return None, None
    t = b.get("__typename", "")
    if t == "HOME_StudioBedroom":
        return 0, 0
    if "min" in b or "max" in b:
        return b.get("min"), b.get("max")
    if b.get("value") is not None:
        return b["value"], b["value"]
    fv = (b.get("formattedValue") or b.get("fullValue") or "").lower()
    if fv.startswith("studio"):
        return 0, 0
    n = num(fv)
    return (n, n) if n != "" else (None, None)


def split_unit(street: str):
    m = re.match(r"^(.*?)(?:,)?\s+(?:#|APT\.?\s+|UNIT\s+|STE\s+)(\S.*)$", street or "", re.I)
    return (m.group(1).strip(), m.group(2).strip()) if m else ((street or "").strip(), "")


MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


def avail_iso(text: str, fetched_iso: str) -> str:
    """'now' / ISO date / '' from Trulia's availability text. Year-less dates take the next occurrence."""
    if not text:
        return ""
    t = text.strip().lower()
    if "now" in t:
        return "now"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return m.group(0)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"\b([a-z]{3})[a-z]*\.?\s+(\d{1,2})(?:,?\s+(\d{4}))?", t)
    if m and m.group(1) in MONTHS:
        mo, d = MONTHS[m.group(1)], int(m.group(2))
        if m.group(3):
            y = int(m.group(3))
        else:
            ref = datetime.fromisoformat(fetched_iso).date() if fetched_iso else date.today()
            y = ref.year if (mo, d) >= (ref.month, ref.day) or (ref.month - mo) <= 2 else ref.year + 1
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return ""
    return ""


def flat_features(features) -> list[tuple[str, str, str, str]]:
    """(category, subcategory, name, value) for every attribute on the page's details block."""
    out = []
    for c in (features or {}).get("categories") or []:
        cn = c.get("formattedName") or ""
        for a in c.get("attributes") or []:
            out.append((cn, "", a.get("formattedName") or "", a.get("formattedValue") or ""))
        for sc in c.get("categories") or []:
            sn = sc.get("formattedName") or ""
            for a in sc.get("attributes") or []:
                out.append((cn, sn, a.get("formattedName") or "", a.get("formattedValue") or ""))
    return out


def highlighted(features) -> dict:
    d = {}
    for hgl in (features or {}).get("highlightedInfoAttributes") or []:
        a = hgl.get("attribute") or {}
        if a.get("formattedName"):
            d[a["formattedName"]] = a.get("formattedValue") or ""
    return d


def pet_fields(pet_policy, feats, hl) -> dict:
    """dogs yes/no/unknown from the structured pet cards; text keeps everything the page says about pets."""
    cards = (pet_policy or {}).get("cards") or []
    texts, dogs, weight, pet_rent = [], "unknown", "", ""
    for c in cards:
        facts = "; ".join(f"{f.get('label')}: {f.get('value')}" for f in c.get("facts") or [])
        restr = c.get("restrictions")
        restr_t = json.dumps(restr) if restr and not isinstance(restr, str) else (restr or "")
        texts.append(f"{c.get('label')}: {c.get('statusLabel')}" + (f" ({facts})" if facts else "")
                     + (f" [restrictions: {restr_t}]" if restr_t else ""))
        if c.get("species") == "DOGS":
            st = (c.get("status") or "").upper()
            dogs = "yes" if st == "ALLOWED" else ("no" if st in ("NOT_ALLOWED", "PROHIBITED", "DISALLOWED") else "unknown")
            for f in c.get("facts") or []:
                lab, val = (f.get("label") or "").lower(), f.get("value") or ""
                if "weight" in lab and num(val) != "":
                    weight = fmt(num(val))
                if "monthly" in lab and "rent" in lab and num(val) != "":
                    pet_rent = fmt(num(val))
            mw = re.search(r"(\d{2,3})\s*(?:lbs?|pounds)", restr_t + " " + facts, re.I)
            if mw and not weight:
                weight = mw.group(1)
    extra = (pet_policy or {}).get("additionalDetails")
    if extra:
        texts.append("Details: " + (extra if isinstance(extra, str) else json.dumps(extra)))
    if hl.get("Pets"):
        texts.append("Summary: " + hl["Pets"])
    for cn, sn, n, v in feats:
        if re.search(r"\b(dogs?|cats?|pets?)\b", f"{sn} {n} {v}", re.I) and "Rental Terms" in cn:
            t = (f"{sn}: " if sn else "") + (f"{n}: " if n else "") + v
            if t not in texts:
                texts.append(t)
    alltext = " | ".join(texts)
    if dogs == "unknown":  # no dog card: use the page's own summary wording, nothing else
        if re.search(r"\bno pets\b|\bno dogs\b|pets not allowed|dogs not allowed", alltext, re.I):
            dogs = "no"
        elif re.search(r"(small|large)?\s*dogs?[^|]*\ballowed\b|Dogs & Cats|Dogs Allowed", alltext, re.I) and \
                not re.search(r"dogs?[^|]*not allowed", alltext, re.I):
            dogs = "yes"
    if not weight:
        mw = re.search(r"(\d{2,3})\s*(?:lbs?\b|pounds)", alltext, re.I)
        if mw:
            weight = mw.group(1)
    return {"dogs": dogs, "dog_policy_text": alltext[:900], "dog_weight_limit_lb": weight, "pet_rent": pet_rent}


def building_feature_fields(feats, hl, description: str) -> dict:
    vals = [(cn, sn, n, v) for cn, sn, n, v in feats]
    blob = " | ".join(f"{n} {v}" for _, _, n, v in vals)
    notes = []
    elevator = "yes" if re.search(r"\belevator", blob, re.I) else "unknown"
    d = description or ""
    if elevator == "unknown":
        if re.search(r"\bwalk[- ]?up\b|\bno elevator\b", d, re.I):
            notes.append("description mentions walk-up/no elevator")
        elif re.search(r"\belevator", d, re.I):
            notes.append("description mentions elevator")
    floor = ""
    mf = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)[- ]floor\b", d, re.I)
    words = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "top": None,
             "ground": 0}
    if mf:
        floor = mf.group(1)
        notes.append("floor from description text")
    else:
        mw = re.search(r"\b(first|second|third|fourth|fifth|sixth|seventh|ground)[- ]floor\b", d, re.I)
        if mw:
            floor = str(words[mw.group(1).lower()])
            notes.append("floor from description text")
    bfloors = ""
    for _, _, n, v in vals:
        if re.fullmatch(r"(stories|number of stories|levels|building floors|floors in building)", n.strip(), re.I) \
                and num(v) != "":
            bfloors = fmt(num(v))
    laundry = hl.get("Laundry", "")
    if not laundry:
        l = [v or n for _, _, n, v in vals if re.search(r"laundry|\bwasher|\bdryer", f"{n} {v}", re.I)]
        laundry = "; ".join(dict.fromkeys(l))
    park = [(f"{n}: " if n else "") + v for _, sn, n, v in vals if re.search(r"parking|garage|carport", f"{sn} {n} {v}", re.I)]
    if hl.get("Parking"):
        park.insert(0, hl["Parking"])
    util = [(f"{n}: " if n else "") + v for _, sn, n, v in vals
            if re.search(r"utilit|included in rent|landlord pays", n, re.I)]
    if not util and re.search(r"(heat|hot water|water|gas|electric\w*|utilities)[^.\n]{0,40}\bincluded\b", d, re.I):
        notes.append("description mentions utilities included")
    return {"elevator": elevator, "floor": floor, "building_floors": bfloors, "laundry": laundry[:200],
            "parking_type": "; ".join(dict.fromkeys(park))[:200], "utilities_included": "; ".join(dict.fromkeys(util))[:200],
            "_notes": notes}


def listing_type(prop_type: str, is_building: bool) -> str:
    p = (prop_type or "").upper().replace(" ", "_").replace("-", "_")
    if is_building:
        return "managed_building"
    if p in ("CONDO", "COOP", "CO_OP", "CONDOMINIUM"):
        return "condo_coop"
    if p in ("SINGLE_FAMILY_HOME", "TOWNHOUSE", "MULTI_FAMILY", "DUPLEX", "TRIPLEX", "MULTI_FAMILY_HOME", "HOUSE"):
        return "unit_in_house"
    return "unknown"


def age_days(date_listed: str, fetched_iso: str):
    if not date_listed:
        return ""
    try:
        return (datetime.fromisoformat(fetched_iso) - datetime.fromisoformat(date_listed)).days
    except ValueError:
        return ""


def listing_age(date_listed: str, fetched_iso: str, feats):
    a = age_days(date_listed, fetched_iso)
    if a == "":
        for _, _, n, v in feats:
            if n == "Days on Market" and num(v) != "":
                return fmt(num(v))
    return a


def photo_of(media) -> str:
    for p in (media or {}).get("photos") or []:
        u = p.get("url") or {}
        for k in ("medium", "mediumSrc", "small", "thumbnail"):
            if u.get(k):
                return u[k]
    h = ((media or {}).get("heroImage") or {}).get("url") or {}
    return h.get("medium") or h.get("small") or ""


def tracking_val(home, key):
    for t in home.get("tracking") or []:
        if t.get("key") == key:
            return t.get("value")
    return None


def blank() -> dict:
    r = {c: "" for c in COLS}
    r.update(source_site="trulia", dogs="unknown", elevator="unknown", listing_type="unknown")
    return r


# ---------------------------------------------------------------- card -> row

def card_summary(h: dict) -> dict | None:
    """Compact card kept in state. None when the card is not a studio/1BR at <= $3,000."""
    if h.get("__typename") == "HOME_RoomForRent":
        return None
    price = h.get("price") or {}
    p = price.get("price") if price.get("price") is not None else price.get("min")
    bmin, bmax = beds_of(h.get("bedrooms"))
    if p is None or bmin is None or bmin > 1 or p > MAX_RENT:
        return None
    loc = h.get("location") or {}
    co = loc.get("coordinates") or {}
    ba = h.get("bathrooms") or {}
    tags = [t.get("formattedName") for t in h.get("tags") or []]
    prov = ((h.get("activeListing") or {}).get("provider") or {})
    return {
        "url": h["url"], "kind": "building" if h["url"].startswith("/building/") else "home",
        "price": p, "price_max": price.get("max"), "price_text": price.get("formattedPrice"),
        "beds": bmin, "beds_max": bmax, "baths": ba.get("value", ba.get("min")),
        "sqft": ((h.get("floorSpace") or {}).get("formattedDimension") or ""),
        "street": loc.get("streetAddress"), "city": loc.get("city"), "state": loc.get("stateCode"),
        "zip": loc.get("zipCode"), "lat": co.get("latitude"), "lon": co.get("longitude"),
        "name": loc.get("communityLocation") or "", "tags": tags,
        "ptype": tracking_val(h, "propertyType") or "", "pets_item": tracking_val(h, "item") or "",
        "manager": "; ".join(prov.get("summary") or []) if prov.get("summary") else "",
        "date_listed": (h.get("activeListing") or {}).get("dateListed") or "",
        "photo": photo_of(h.get("media")), "id": (h.get("typedHomeId") or "").split("_")[0],
    }


def card_row(c: dict) -> dict:
    r = blank()
    addr, unit = split_unit(c.get("street") or "")
    is_b = c["kind"] == "building"
    notes = ["card only: price and facts are from the search-results card, not verified on the listing page"]
    if is_b and c.get("price_max") and c["price_max"] != c["price"]:
        notes.append("building card: rent is the low end of the filtered range")
    pets = ""
    m = re.search(r"rental:Pets:([^;]*)", c.get("pets_item") or "")
    if m:
        pets = m.group(1)
    if "PET FRIENDLY" in (c.get("tags") or []):
        pets = (pets + " | " if pets else "") + "tag: PET FRIENDLY"
    dogs = "unknown"
    if re.search(r"dogs? allowed|dogs & cats", pets, re.I):
        dogs = "yes"
    elif re.search(r"no pets", pets, re.I):
        dogs = "no"
    r.update(
        listing_id=f"trulia:{'b' if is_b else ''}{c['id']}", url=BASE + c["url"], detail_level="card",
        building_name=c.get("name") or "", address=addr, city=c.get("city") or "", state=c.get("state") or "",
        zip=c.get("zip") or "", lat=c.get("lat") or "", lon=c.get("lon") or "", unit=unit,
        beds=fmt(c["beds"]), baths=fmt(c.get("baths")) if c.get("baths") is not None else "",
        sqft=fmt(num(c.get("sqft"))) if c.get("sqft") and "-" not in c["sqft"] else "",
        listed_rent=fmt(c["price"]), price_basis="card price" + (f" ({c['price_text']})" if is_b else ""),
        concession_text="tag: SPECIAL OFFER" if "SPECIAL OFFER" in (c.get("tags") or []) else "",
        dogs=dogs, dog_policy_text=pets,
        listing_type=listing_type(c.get("ptype"), is_b), manager=c.get("manager") or "",
        listing_age_days=age_days(c.get("date_listed"), c.get("seen_at") or ""),
        photo_url=c.get("photo") or "", building_url=BASE + c["url"] if is_b else "",
        raw_path=c.get("raw_path") or "", notes="; ".join(notes),
        first_seen=c.get("seen_at") or "", last_seen=c.get("seen_at") or "",
    )
    return r


# ---------------------------------------------------------------- detail pages -> rows

def fees_home(rcf) -> tuple[dict, str, str]:
    """-> (other fees dict, parking_fee, basis) from a single-unit page's costs block."""
    out, parking, basis = {}, "", ""
    if not rcf:
        return out, parking, basis
    basis = ((rcf.get("disclaimer") or {}).get("text") or "")
    for sec in rcf.get("rentalFeeSections") or []:
        title = sec.get("sectionTitle") or ""
        items = [{"title": f.get("title"), "value": f.get("formattedValue")} for f in sec.get("rentalFees") or []
                 if (f.get("title") or "").lower() != "base rent"
                 and (f.get("formattedValue") or "").lower() != "contact for details"]
        for it in items:
            if re.search(r"parking|garage", it["title"] or "", re.I):
                parking = f"{it['title']}: {it['value']}"
        if items:
            out[title] = items
    return out, parking, basis


def fees_building(rcf) -> tuple[dict, str]:
    out, parking = {}, ""
    fees = (((rcf or {}).get("costAndFeeCalculator") or {}).get("fees") or {})
    for k, v in fees.items():
        if not isinstance(v, list):
            continue
        items = []
        for x in v:
            f = x.get("fee") or {}
            name = f.get("displayValue") or ""
            if k == "monthlyRequiredFees" and name.lower() == "rent":
                continue
            val = ""
            if f.get("amount"):
                a = f["amount"]
                val = a.get("displayText") or a.get("formattedValue") or a.get("value") or ""
            elif "min" in f or "max" in f:
                val = f"{f.get('min')}-{f.get('max')}"
            if str(val).lower() == "contact for details" and not re.search(r"\$\s*\d", name):
                continue
            items.append({"title": name, "value": val})
            if re.search(r"parking|garage", name, re.I):
                parking = (parking + "; " if parking else "") + (f"{name}" + (f": {val}" if val else ""))
        if items:
            out[k] = items
    return out, parking


def parse_home(hd: dict, meta: dict) -> tuple[list[dict], str]:
    """-> (rows, drop_reason)."""
    st = hd.get("currentStatus") or {}
    if not st.get("isActiveForRent"):
        return [], "not active for rent: " + str(st.get("label"))
    price = hd.get("price") or {}
    p = price.get("price")
    bmin, _ = beds_of(hd.get("bedrooms"))
    if p is None:
        return [], "no single price on page"
    if bmin is None or bmin > 1:
        return [], f"beds on page: {(hd.get('bedrooms') or {}).get('formattedValue')}"
    if p > MAX_RENT:
        return [], f"rent on page {p} > {MAX_RENT}"
    seen = meta["retrieved_at"]
    loc = hd.get("location") or {}
    co = loc.get("coordinates") or {}
    feats, hl = flat_features(hd.get("features")), highlighted(hd.get("features"))
    desc = ((hd.get("description") or {}).get("value") or "")
    afr = hd.get("activeForRentListing") or {}
    pets = pet_fields(afr.get("petPolicy"), feats, hl)
    bf = building_feature_fields(feats, hl, desc)
    fees, parking_fee, basis = fees_home(hd.get("rentalCostsAndFees"))
    addr, unit = split_unit(loc.get("streetAddress") or "")
    comm = hd.get("community") or {}
    prov = (afr.get("provider") or {})
    mgr = ((prov.get("broker") or {}).get("name") or "") or ((prov.get("listingAgent") or {}).get("name") or "")
    ptype = ((hd.get("propertyType") or {}).get("value") or "")
    avail_t = hd.get("formattedAvailableDate") or ""
    if not avail_t:
        for _, _, n, v in feats:
            if n == "Available":
                avail_t = v
    notes = list(bf["_notes"])
    notes.append(f"property type on page: {ptype}" if ptype else "")
    if hd.get("isVerifiedListing"):
        notes.append("Trulia 'verified listing'")
    if (hd.get("priceDisclaimer") or {}).get("markdown"):
        notes.append("page says: " + hd["priceDisclaimer"]["markdown"])
    ba = hd.get("bathrooms") or {}
    r = blank()
    zpid = (hd.get("typedHomeId") or "").split("_")[0]
    r.update(
        listing_id=f"trulia:{zpid}", url=BASE + hd["url"], detail_level="detail", first_seen=seen, last_seen=seen,
        building_name=(comm.get("name") or "") if isinstance(comm, dict) else "",
        address=addr, city=loc.get("city") or "", state=loc.get("stateCode") or "", zip=loc.get("zipCode") or "",
        lat=co.get("latitude") or "", lon=co.get("longitude") or "", unit=unit, beds=fmt(bmin),
        baths=fmt(ba.get("value")) if ba.get("value") is not None else "",
        sqft=fmt(num((hd.get("floorSpace") or {}).get("formattedDimension"))) if hd.get("floorSpace") else "",
        listed_rent=fmt(p),
        price_basis="total monthly (page flag isTotalMonthlyFeeIncluded)" if afr.get("isTotalMonthlyFeeIncluded")
        else ("base rent" if "base rent" in basis.lower() else "listed price"),
        concession_text=" | ".join(s.get("description") or "" for s in hd.get("specialOffers") or [])[:300],
        available_date_text=avail_t, available_date=avail_iso(avail_t, seen),
        dogs=pets["dogs"], dog_policy_text=pets["dog_policy_text"], dog_weight_limit_lb=pets["dog_weight_limit_lb"],
        elevator=bf["elevator"], floor=bf["floor"], building_floors=bf["building_floors"],
        parking_type=bf["parking_type"], parking_fee=parking_fee, pet_rent=pets["pet_rent"],
        other_monthly_fees_json=json.dumps(fees, separators=(",", ":")) if fees else "",
        utilities_included=bf["utilities_included"], laundry=bf["laundry"],
        listing_type=listing_type(ptype, False), manager=mgr,
        listing_age_days=listing_age(afr.get("dateListed") or "", seen, feats), photo_url=photo_of(hd.get("media")),
        building_url=(BASE + comm["url"]) if isinstance(comm, dict) and comm.get("url") else "",
        raw_path=meta.get("path", ""), notes="; ".join(n for n in notes if n),
    )
    return [r], ""


def parse_building(hd: dict, meta: dict) -> tuple[list[dict], str]:
    seen = meta["retrieved_at"]
    loc = hd.get("location") or {}
    co = loc.get("coordinates") or {}
    feats, hl = flat_features(hd.get("features")), highlighted(hd.get("features"))
    desc = ((hd.get("description") or {}).get("value") or "")
    afr = hd.get("activeForRentListing") or {}
    pets = pet_fields(afr.get("petPolicy"), feats, hl)
    summ = (hd.get("petPolicy") or {}).get("formattedPetsAllowed")
    if summ and summ not in pets["dog_policy_text"]:
        pets["dog_policy_text"] = (pets["dog_policy_text"] + " | " if pets["dog_policy_text"] else "") + "Summary: " + summ
    bf = building_feature_fields(feats, hl, desc)
    bf["floor"] = ""  # a building description cannot give a unit's floor
    bf["_notes"] = [n for n in bf["_notes"] if not n.startswith("floor")]
    fees, parking_fee = fees_building(hd.get("rentalCostsAndFees"))
    mgr = (((hd.get("planVisit") or {}).get("propertyManagementCompany") or {}).get("name") or "")
    bid = (hd.get("typedHomeId") or "").split("_")[0]
    ud = hd.get("unitDetails") or {}
    conc = " | ".join(s.get("description") or "" for s in hd.get("specialOffers") or [])[:300]
    base_notes = list(bf["_notes"])
    if ud.get("totalUnitsInBuilding"):
        base_notes.append(f"building has {ud['totalUnitsInBuilding']} units, {ud.get('availableRentalUnits')} available")
    fp_disc = ((hd.get("floorPlans") or {}).get("disclaimer") or {}).get("markdown") or ""
    basis = "base rent" if "base rent" in fp_disc.lower() else "listed price"
    if afr.get("isTotalMonthlyFeeIncluded"):
        basis = "total monthly (page flag isTotalMonthlyFeeIncluded)"
    photo = photo_of(hd.get("media"))
    rows, n_units, n_skip = [], 0, 0

    def mk(item, level, unit_name, plan_name, avail_text, avail_date, is_now):
        nonlocal n_skip
        pr = item.get("priceRange") or {}
        p = pr.get("min")
        bmin, _ = beds_of(item.get("bedrooms"))
        if p is None or bmin is None or bmin > 1 or p > MAX_RENT or item.get("isRoomForRent"):
            n_skip += 1
            return
        r = blank()
        notes = list(base_notes) + [f"floor plan: {plan_name}"]
        if pr.get("max") and pr["max"] != p:
            notes.append(f"rent range on page {pr.get('formattedPrice')}; listed_rent is the low end")
        ad = "now" if is_now else (avail_date[:10] if avail_date else avail_iso(avail_text, seen))
        if (avail_text or "").lower().strip() == "available soon" and not ad:
            notes.append("page says 'Available Soon' with no date")
        ba = item.get("bathrooms") or {}
        key = unit_name or f"plan-{plan_name}"
        r.update(
            listing_id=f"trulia:b{bid}:{re.sub(r'[^A-Za-z0-9._-]+', '_', key)}:{item.get('id') or ''}",
            url=BASE + hd["url"], detail_level=level, first_seen=seen, last_seen=seen,
            building_name=hd.get("name") or "", address=loc.get("streetAddress") or "", city=loc.get("city") or "",
            state=loc.get("stateCode") or "", zip=loc.get("zipCode") or "", lat=co.get("latitude") or "",
            lon=co.get("longitude") or "", unit=re.sub(r"^Unit\s+", "", unit_name or ""), beds=fmt(bmin),
            baths=fmt(ba.get("value")) if ba.get("value") is not None else "",
            sqft=fmt((item.get("floorSpace") or {}).get("max")) if (item.get("floorSpace") or {}).get("max") else "",
            listed_rent=fmt(p), price_basis=basis, concession_text=conc,
            available_date_text=avail_text or "", available_date=ad,
            dogs=pets["dogs"], dog_policy_text=pets["dog_policy_text"],
            dog_weight_limit_lb=pets["dog_weight_limit_lb"], elevator=bf["elevator"], floor="",
            building_floors=bf["building_floors"], parking_type=bf["parking_type"], parking_fee=parking_fee,
            pet_rent=pets["pet_rent"],
            other_monthly_fees_json=json.dumps(fees, separators=(",", ":")) if fees else "",
            utilities_included=bf["utilities_included"], laundry=bf["laundry"], listing_type="managed_building",
            manager=mgr, listing_age_days="", photo_url=photo, building_url=BASE + hd["url"],
            raw_path=meta.get("path", ""), notes="; ".join(n for n in notes if n),
        )
        rows.append(r)

    for g in ((hd.get("floorPlans") or {}).get("floorPlanGroups") or []):
        for plan in g.get("plans") or []:
            units = plan.get("units") or []
            if units:
                for u in units:
                    n_units += 1
                    mk(u, "building_unit", u.get("name") or "", plan.get("name") or "", u.get("availabilityText"),
                       u.get("availabilityDate"), bool(u.get("isAvailableNow")))
            else:
                n_units += 1
                mk(plan, "building_floorplan", "", plan.get("name") or "", plan.get("availabilityText"), None,
                   (plan.get("availabilityText") or "").lower().strip() == "available now")
    # the same unit can sit under two groups ("All", "Studio"): keep one row per listing_id
    uniq = {r["listing_id"]: r for r in rows}
    if not uniq:
        return [], f"no studio/1BR unit at <= {MAX_RENT} on building page ({n_units} units/plans listed)"
    return list(uniq.values()), ""


def parse_detail(nd: dict, meta: dict) -> tuple[list[dict], str]:
    hd = (nd.get("props") or {}).get("homeDetails")
    if not hd:
        return [], "no homeDetails in page"
    if (hd.get("url") or "").startswith("/building/") or hd.get("floorPlans"):
        return parse_building(hd, meta)
    return parse_home(hd, meta)


# ---------------------------------------------------------------- state and output

def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"zips": {}, "cards": {}, "details": {}}


READ_ONLY = False


def save_state(s: dict) -> None:
    if READ_ONLY:
        return
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, separators=(",", ":")))
    os.replace(tmp, STATE)


def load_rows() -> dict:
    if not OUT.exists():
        return {}
    with open(OUT, newline="", encoding="utf8") as f:
        return {r["listing_id"]: r for r in csv.DictReader(f)}


def save_rows(rows: dict, order: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: (order.get(r["url"], 9e9), r["url"], r["listing_id"])):
            w.writerow(r)
    os.replace(tmp, OUT)


def put_rows(rows: dict, new: list[dict]) -> None:
    for r in new:
        old = rows.get(r["listing_id"])
        if old and old.get("first_seen"):
            r["first_seen"] = min(old["first_seen"], r["first_seen"]) if r["first_seen"] else old["first_seen"]
        rows[r["listing_id"]] = r


def drop_url_rows(rows: dict, url: str, keep_ids: set, levels=None) -> None:
    for k in [k for k, r in rows.items() if r["url"] == url and k not in keep_ids
              and (levels is None or r["detail_level"] in levels)]:
        del rows[k]


# ---------------------------------------------------------------- phases

def grid() -> list[dict]:
    with open(GRID, newline="") as f:
        g = list(csv.DictReader(f))
    g.sort(key=lambda r: float(r["drive_min"]))
    return g


def search_zip(z: str, state: dict, rows: dict, a) -> None:
    base = f"{BASE}/for_rent/{z}_zip/0-1_beds/0-{MAX_RENT}_price/"
    page, got, total, kept, status = 1, 0, None, 0, "ok"
    while True:
        url = base if page == 1 else f"{base}{page}_p/"
        nd, meta = fetch(url, a.refresh_hours, a.reparse)
        if nd is None:
            if a.reparse and page == 1:
                return  # not cached: leave state alone
            status = f"http {meta['status']}" if page == 1 else status
            break
        sd = (nd.get("props") or {}).get("searchData") or {}
        loc_zip = z in (sd.get("currentUrl") or "") or z in json.dumps(sd.get("location") or {})
        if not loc_zip:
            status = "page is not for this ZIP: " + str(sd.get("currentUrl"))
            break
        f = ((sd.get("details") or {}).get("filters") or {})
        if page == 1 and ((f.get("price") or {}).get("max") != str(MAX_RENT) or (f.get("bedrooms") or {}).get("max") != "1"):
            status = "filters not applied by the site; filtered here instead"
        homes = sd.get("homes") or []
        total = sd.get("totalHomes") if total is None else total
        for h in homes:
            c = card_summary(h)
            if not c:
                continue
            kept += 1
            c["seen_at"], c["raw_path"] = meta["retrieved_at"], meta.get("path", "")
            old = state["cards"].get(c["url"])
            c["zips"] = sorted(set((old or {}).get("zips", [])) | {z})
            c["first_seen"] = (old or {}).get("first_seen") or c["seen_at"]
            state["cards"][c["url"]] = c
            det = state["details"].get(c["url"])
            if not det or det.get("status") not in ("ok", "dropped", "gone"):
                row = card_row(c)
                row["first_seen"] = c["first_seen"]
                put_rows(rows, [row])
        got += len(homes)
        if not homes or got >= (total or 0) or page >= 25:
            break
        page += 1
    if not a.reparse:
        state["zips"][z] = {"at": now_iso(), "total": total, "pages": page, "cards": kept, "status": status}


def run_search(state, rows, order, a, deadline) -> None:
    g = grid()
    todo = [r["zcta"] for r in g if a.reparse or r["zcta"] not in state["zips"]
            or _age_hours(state["zips"][r["zcta"]]["at"]) >= a.refresh_hours]
    if a.max_zips:
        todo = todo[: a.max_zips]
    print(f"search: {len(todo)} ZIPs to do ({len(state['zips'])} already in state)", flush=True)
    for i, z in enumerate(todo, 1):
        if time.time() > deadline:
            print("search: time budget reached", flush=True)
            return
        search_zip(z, state, rows, a)
        if (i % 10 == 0 or i == len(todo)) and not a.reparse:
            save_state(state)
            save_rows(rows, order_of(state))
            zs = state["zips"][z]
            print(f"search {i}/{len(todo)} zip {z}: total={zs['total']} cards={zs['cards']} "
                  f"all cards={len(state['cards'])} fetched={N_FETCHED}", flush=True)
    save_state(state)


def order_of(state) -> dict:
    dm = {r["zcta"]: float(r["drive_min"]) for r in grid()} if not hasattr(order_of, "dm") else order_of.dm
    order_of.dm = dm
    return {BASE + u: min([dm.get(z, 9e9) for z in c.get("zips", [])] or [9e9]) for u, c in state["cards"].items()}


def run_detail(state, rows, a, deadline) -> None:
    order = order_of(state)
    urls = sorted(state["cards"], key=lambda u: (order[BASE + u], u))
    todo = []
    for u in urls:
        d = state["details"].get(u)
        if a.reparse:
            if d:
                todo.append(u)
        elif not d or _age_hours(d["at"]) >= a.refresh_hours:
            todo.append(u)
    if a.max_details:
        todo = todo[: a.max_details]
    print(f"detail: {len(todo)} pages to do ({len(state['details'])} already in state, {len(urls)} cards)", flush=True)
    for i, u in enumerate(todo, 1):
        if time.time() > deadline:
            print("detail: time budget reached", flush=True)
            break
        nd, meta = fetch(BASE + u, a.refresh_hours, a.reparse)
        full = BASE + u
        if nd is None:
            if a.reparse:
                continue
            state["details"][u] = {"at": now_iso(), "status": "gone", "why": f"http {meta['status']}"}
            drop_url_rows(rows, full, set())
        else:
            new, why = parse_detail(nd, meta)
            c = state["cards"][u]
            for r in new:
                r["first_seen"] = min(c.get("first_seen") or r["first_seen"], r["first_seen"])
            put_rows(rows, new)
            drop_url_rows(rows, full, {r["listing_id"] for r in new})
            state["details"][u] = {"at": meta["retrieved_at"], "status": "ok" if new else "dropped", "why": why,
                                   "rows": len(new)}
        if i % 25 == 0 or i == len(todo):
            save_state(state)
            save_rows(rows, order)
            print(f"detail {i}/{len(todo)} rows={len(rows)} fetched={N_FETCHED} "
                  f"last={state['details'][u]['status']}", flush=True)
    save_state(state)
    save_rows(rows, order)


def main() -> int:
    global DELAY, READ_ONLY
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["search", "detail", "all"], default="all")
    ap.add_argument("--max-zips", type=int, default=0)
    ap.add_argument("--max-details", type=int, default=0)
    ap.add_argument("--max-minutes", type=float, default=0)
    ap.add_argument("--delay", type=float, default=2.2, help="seconds between requests (minimum 2)")
    ap.add_argument("--refresh-hours", type=float, default=20)
    ap.add_argument("--reparse", action="store_true", help="rebuild rows from cached pages only (no network)")
    a = ap.parse_args()
    DELAY = max(2.0, a.delay)
    READ_ONLY = a.reparse
    deadline = time.time() + a.max_minutes * 60 if a.max_minutes else float("inf")
    state = load_state()
    rows = {} if a.reparse else load_rows()
    code = 0
    try:
        if a.phase in ("search", "all"):
            run_search(state, rows, None, a, deadline)
        if a.phase in ("detail", "all") or a.reparse:
            run_detail(state, rows, a, deadline)
    except Blocked as e:
        print("STOPPED:", e, flush=True)
        code = 3
    finally:
        if not a.reparse:
            save_state(state)
        save_rows(rows, order_of(state))
    lv = {}
    for r in rows.values():
        lv[r["detail_level"]] = lv.get(r["detail_level"], 0) + 1
    print(f"done: {len(rows)} rows {lv}; zips in state {len(state['zips'])}; cards {len(state['cards'])}; "
          f"details {len(state['details'])}; network fetches {N_FETCHED}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
