#!/usr/bin/env python3
"""The drop box: listings Will or Lamia found by hand, from any site (docs/TRAWL_2_PLAN.md, step 5).

They put files in inbox/ (see inbox/README.md):
  - a saved web page (.html / .htm, or .mhtml "single file"): read from what they saved; nothing is fetched from the site.
    Order of trust: application/ld+json, then embedded page state (__NEXT_DATA__, Apollo / preloaded / initial state,
    other application/json blobs; JSON held in a string, such as Zillow's gdpClientCache, is opened too), then the
    visible text. The listing URL comes from the page's canonical link, og:url or the browser's "saved from url" line.
  - a PDF (printed page): text from pdftotext (or pypdf); then the visible-text reader.
  - a screenshot (.png/.jpg/.jpeg/.webp/.gif/.heic/.bmp/.tif): OCR with the tesseract binary when it is installed;
    otherwise the file is listed as "needs reading" in inbox/STATUS.txt and no row is written.
  - inbox/links.txt, one link per line: fetched ONLY on hosts we may read. Trulia, Zillow and StreetEasy links are never
    fetched ("save the page instead"); other off-limits hosts (scripts/lib.py OFF_LIMITS, CLAUDE.md, and
    raw/_host_kill_shared.json) are not fetched either. A Craigslist link pasted by a person may be fetched (CLAUDE.md:
    pasted links are fine). robots.txt (Claude-User group, else *) is honoured; 3 s between requests to a host; a
    401/403/429 or CAPTCHA ends that host (raw/inbox_links/_refused_hosts.json). Fetched pages cache in raw/inbox_links/.

Writes data/listings_raw/manual_inbox.csv (the harvest column contract, docs/HARVEST_AGENT_BRIEF.md) and
inbox/STATUS.txt (what was read from each file). Only what the page states is recorded; unknown stays empty/unknown.
Collection limits (CLAUDE.md, "Second trawl"): studios and 1-bedrooms, listed base rent <= $2,200; the rest are named in
STATUS.txt and not written. Idempotent: listing_id = inbox:<sha1 of the file>:<unit or position>; first_seen is kept;
rows whose raw file is no longer in inbox/ (raw files are git-ignored) are kept as they were.

Run: python3 scripts/h_inbox.py   (also run by scripts/h_manual.py; `h_manual.py --inbox` runs only this)
"""
from __future__ import annotations

import csv
import email
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib import robotparser

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
import parsers  # noqa: E402

ROOT = lib.ROOT
INBOX = ROOT / "inbox"
OUT = lib.DATA / "listings_raw" / "manual_inbox.csv"
LINK_SRC = "inbox_links"
RENT_MAX = 2200
LINK_DELAY = 3.0

COLS = ("listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,unit,"
        "beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,dog_policy_text,"
        "dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,other_monthly_fees_json,"
        "utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,building_url,raw_path,notes").split(",")

SKIP_NAMES = {"readme.md", "links.txt", "status.txt"}
HTML_EXT = {".html", ".htm", ".xhtml"}
MHTML_EXT = {".mhtml", ".mht"}
PDF_EXT = {".pdf"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic", ".bmp", ".tif", ".tiff"}
TEXT_EXT = {".txt"}

# Sites whose pages we never open by script. The first group gets the "save the page instead" answer by name.
SAVE_INSTEAD = {"trulia.com": "Trulia", "zillow.com": "Zillow", "streeteasy.com": "StreetEasy"}
EXTRA_OFF = ("trulia.com", "hotpads.com", "renthop.com", "realtor.com", "rent.com", "rentcafe.com", "securecafe.com",
             "google.com", "goo.gl", "facebook.com", "nextdoor.com")
PASTED_OK = ("craigslist.org",)  # off limits by script, but a single link pasted by a person may be opened

SITE_NAMES = (("trulia.com", "trulia"), ("zillow.com", "zillow.com"), ("streeteasy.com", "streeteasy.com"),
              ("zumper.com", "zumper"), ("apartmentlist.com", "apartmentlist.com"), ("apartments.com", "apartments.com"),
              ("craigslist.org", "craigslist"), ("hotpads.com", "hotpads.com"), ("rent.com", "rent.com"),
              ("realtor.com", "realtor.com"), ("renthop.com", "renthop.com"))
TITLE_SITES = (("trulia", "trulia"), ("zillow", "zillow.com"), ("streeteasy", "streeteasy.com"), ("zumper", "zumper"),
               ("apartment list", "apartmentlist.com"), ("apartments.com", "apartments.com"), ("craigslist", "craigslist"))


# ----------------------------------------------------------------------------------------------------------------------
# small readers
# ----------------------------------------------------------------------------------------------------------------------
def iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).replace(microsecond=0).isoformat()


def bare(host: str) -> str:
    return lib._bare_host(host)


def site_of(url: str, title: str = "") -> str:
    h = bare(urlparse(url).netloc) if url else ""
    for dom, name in SITE_NAMES:
        if h == dom or h.endswith("." + dom):
            return name
    if h:
        return h
    t = (title or "").lower()
    for word, name in TITLE_SITES:
        if word in t:
            return name
    return "unknown site"


def to_money(v):
    """A rent figure from a JSON value or text: 1850, '1850', '$1,850/mo', '$1,800 - $2,000' (low end). None if not a rent."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        x = float(v)
    else:
        m = re.search(r"\$?\s*(\d{1,2},\d{3}|\d{3,5})(?:\.\d{1,2})?", str(v))
        if not m:
            return None
        x = float(m.group(1).replace(",", ""))
    if not 300 <= x <= 20000:
        return None
    return int(x) if x == int(x) else x


def to_beds(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, dict):
        for k in ("formattedValue", "value", "min", "max", "text"):
            if k in v:
                return to_beds(v[k])
        return None
    if isinstance(v, (int, float)):
        return int(v) if 0 <= v <= 9 and v == int(v) else None
    s = str(v).strip().lower()
    if re.search(r"\bstudio\b|\bjr\.? ?1\b|^0\b|\b0 ?(?:bd|br|bed)", s):
        return 0
    m = re.search(r"(\d)\s*(?:bd|bds|br|bed|beds|bedroom|bedrooms)?\b", s)
    return int(m.group(1)) if m else None


def to_sqft(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, dict):
        for k in ("max", "value", "min", "formattedDimension", "formattedValue"):
            if k in v and to_sqft(v[k]):
                return to_sqft(v[k])
        return None
    if isinstance(v, (int, float)):
        return int(v) if 100 <= v <= 6000 else None
    m = re.search(r"(\d{1,2},\d{3}|\d{3,4})", str(v))
    x = int(m.group(1).replace(",", "")) if m else None
    return x if x and 100 <= x <= 6000 else None


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def to_date(s, ref: date | None = None) -> str:
    """ISO date from '2026-12-01', '12/01/2026', '12/1', 'December 1, 2026', 'Dec 1' (year inferred from the save date:
    the next such date on or after 30 days before it). '' when no date can be read."""
    s = str(s or "").strip()
    ref = ref or date.today()
    m = re.search(r"(20\d\d)-(\d\d)-(\d\d)", s)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", s)
        if m:
            mo, d = int(m.group(1)), int(m.group(2))
            y = int(m.group(3)) if m.group(3) else None
            if y is not None and y < 100:
                y += 2000
        else:
            m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d\d))?", s, re.I)
            if not m:
                return ""
            mo, d = MONTHS[m.group(1).lower()], int(m.group(2))
            y = int(m.group(3)) if m.group(3) else None
        if y is None:
            y = ref.year
            try:
                if (date(y, mo, d) - ref).days < -30:
                    y += 1
            except ValueError:
                return ""
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return ""


def clip(s, n=300) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


# ----------------------------------------------------------------------------------------------------------------------
# address
# ----------------------------------------------------------------------------------------------------------------------
_STREET = (r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Place|Pl|Drive|Dr|Lane|Ln|Court|Ct|Terrace|Ter|Parkway|Pkwy|"
           r"Way|Highway|Hwy|Square|Sq|Turnpike|Tpke|Circle|Cir|Plaza|Plz|Broadway|Row|Walk|Loop)")
ADDR_RE = re.compile(
    r"(\d{1,6}(?:-\d{1,4})?\s+(?:[A-Za-z0-9.'-]+\s+){0,5}?" + _STREET + r"\b\.?(?:\s+(?:N|S|E|W|North|South|East|West)\b)?)"
    r"(?:\s*,?\s*(?:#|Apt\.?|Apartment|Unit|Ste\.?)\s*([A-Za-z0-9-]{1,6}))?"
    r",\s*([A-Za-z .'-]{2,30}?),\s*(NY|NJ|CT|PA|New York|New Jersey|Connecticut)\.?\s+(\d{5})\b")
STATE_ABBR = {"new york": "NY", "new jersey": "NJ", "connecticut": "CT"}


def addr_from_text(s):
    m = ADDR_RE.search(str(s or ""))
    if not m:
        return None
    st = m.group(4)
    return {"address": re.sub(r"\s+", " ", m.group(1)).strip(), "unit": m.group(2) or "", "city": m.group(3).strip(),
            "state": STATE_ABBR.get(st.lower(), st), "zip": m.group(5)}


def addr_from_dict(d):
    """An address dict in schema.org or site JSON. None unless it has a street with a house number."""
    if not isinstance(d, dict):
        return None
    g = lambda *ks: next((str(d[k]).strip() for k in ks if isinstance(d.get(k), (str, int)) and str(d.get(k)).strip()), "")
    street = g("streetAddress", "street", "addressLine1", "line1", "address1", "street1", "streetLine")
    if not street or not re.match(r"\d", street):
        return None
    out = {"address": street, "unit": g("unit", "unitNumber", "aptNumber", "addressLine2", "line2"),
           "city": g("addressLocality", "city", "cityName", "locality"),
           "state": g("addressRegion", "state", "stateCode", "region"),
           "zip": (re.search(r"\d{5}", g("postalCode", "zip", "zipcode", "zipCode", "postal_code")) or [""])[0]}
    out["state"] = STATE_ABBR.get(out["state"].lower(), out["state"])
    a, u = parsers.split_address_unit(street)
    if u and not out["unit"]:
        out["address"], out["unit"] = a, u
    out["unit"] = re.sub(r"^(?:apt\.?|unit|#)\s*", "", out["unit"], flags=re.I).strip()
    return out


def same_street(a, b) -> bool:
    n = lambda x: re.sub(r"[^a-z0-9]", "", (x or "").lower().split(",")[0])[:10]
    return n(a) == n(b)


# ----------------------------------------------------------------------------------------------------------------------
# JSON in the page
# ----------------------------------------------------------------------------------------------------------------------
SKIP_KEY = re.compile(r"similar|nearby|recommend|related|comparable|sponsor|neighbo|otherlisting|promoted|seo|footer|"
                      r"breadcrumb|search|carousel|alsoviewed|surrounding|^ads?$|advert|popular|trending|recentlyviewed", re.I)
PRICE_KEYS = ("price", "rent", "listPrice", "listingPrice", "monthlyRent", "rentAmount", "askingPrice", "netEffectivePrice",
              "unformattedPrice", "formattedPrice", "pricePeriodRange", "priceRange", "minPrice", "maxPrice", "lowPrice",
              "rentPrice", "baseRent")
BEDS_KEYS = ("beds", "bedrooms", "bedroomCount", "numBedrooms", "bedroomsCount", "numberOfBedrooms", "bedroom", "numberOfRooms")
BATH_KEYS = ("baths", "bathrooms", "bathroomCount", "numBathrooms", "fullBathrooms", "numberOfBathroomsTotal", "bathroomsFull")
SQFT_KEYS = ("sqft", "squareFeet", "livingArea", "livingAreaSize", "floorSpace", "squareFootage", "sqFt", "floorSize", "area_sqft")
UNIT_KEYS = ("unitNumber", "unit", "unitName", "aptNumber", "apartmentNumber")
AVAIL_KEYS = ("availableDate", "availabilityDate", "dateAvailable", "availableFrom", "availableAt", "moveInDate",
              "availableOn", "availability", "availabilityText", "formattedAvailability")
FLOOR_KEYS = ("floor", "floorNumber", "floorLevel", "unitFloor")
TEXT_KEY = re.compile(r"amenit|feature|highlight|pet|dog|parking|laundry|fee|utilit|description|remarks|policy|special|"
                      r"concession|elevator|building|lease", re.I)
STATE_BLOB = re.compile(r"(?:window\.)?(__APOLLO_STATE__|__PRELOADED_STATE__|__INITIAL_STATE__|__REDUX_STATE__|"
                        r"__INITIAL_DATA__|__NUXT__|__APP_STATE__)\s*=\s*", re.S)


def _first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, "", [], {}):
            return k, d[k]
    return None, None


def _price_of(v):
    if isinstance(v, dict):
        for k in ("formattedPrice", "value", "amount", "min", "low", "max", "price"):
            if k in v and to_money(v[k]) is not None:
                return to_money(v[k])
        return None
    return to_money(v)


def _decode_json(s):
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return None


def _balanced(s, start):
    """The JSON object or array text that begins at s[start]."""
    if start >= len(s) or s[start] not in "{[":
        return None
    depth, inq, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if inq:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                inq = False
        elif c == '"':
            inq = True
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return None


def embedded_blobs(html: str, soup):
    """(label, data) for every JSON state blob in the page (not ld+json)."""
    out = []
    for tag in soup.find_all("script"):
        typ = (tag.get("type") or "").lower()
        txt = tag.string or tag.get_text() or ""
        if "ld+json" in typ:
            continue
        if tag.get("id") == "__NEXT_DATA__" or typ == "application/json":
            d = _decode_json(txt)
            if d is not None:
                out.append((tag.get("id") or "application/json", d))
            continue
        for m in STATE_BLOB.finditer(txt):
            js = _balanced(txt, m.end())
            d = _decode_json(js) if js else None
            if d is not None:
                out.append((m.group(1), d))
    return out


def jsonld_items(soup):
    items = []
    for tag in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        d = _decode_json(tag.string or tag.get_text() or "")
        stack = [d]
        while stack:
            x = stack.pop()
            if isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, dict):
                items.append(x)
                for k in ("@graph", "mainEntity", "itemOffered", "containsPlace", "about"):
                    if k in x:
                        stack.append(x[k])
    return items


def _types(x):
    t = x.get("@type")
    return {str(v).lower() for v in (t if isinstance(t, list) else [t]) if v}


def read_jsonld(items):
    """Page-level facts from schema.org items: address, geo, beds, baths, sqft, price, pets, url, image, name."""
    f = {}
    for x in items:
        ty = _types(x)
        if not ty & {"apartment", "singlefamilyresidence", "house", "residence", "accommodation", "product", "offer",
                     "realestatelisting", "apartmentcomplex", "place", "residentialbuilding", "aggregateoffer",
                     "suite", "room"}:
            continue
        a = addr_from_dict(x.get("address")) if isinstance(x.get("address"), dict) else addr_from_text(x.get("address"))
        if a and "addr" not in f:
            f["addr"] = a
        geo = x.get("geo") or {}
        if isinstance(geo, dict) and geo.get("latitude") and "lat" not in f:
            f["lat"], f["lon"] = geo.get("latitude"), geo.get("longitude")
        for key, conv, name in ((("numberOfBedrooms", "numberOfRooms"), to_beds, "beds"),
                                (("numberOfBathroomsTotal", "numberOfFullBathrooms"), lambda v: v if isinstance(v, (int, float)) else to_money(v), "baths"),
                                (("floorSize",), to_sqft, "sqft")):
            k, v = _first(x, key)
            if k and name not in f and conv(v) is not None:
                f[name] = conv(v)
        offers = x.get("offers") or ({"price": x.get("price")} if "offer" in ty and x.get("price") else None)
        for o in offers if isinstance(offers, list) else [offers]:
            if isinstance(o, dict) and "rent" not in f:
                p = to_money(o.get("price")) or to_money(o.get("lowPrice"))
                if p is not None:
                    f["rent"] = p
                    if o.get("availabilityStarts"):
                        f["avail_raw"] = o.get("availabilityStarts")
        if x.get("petsAllowed") is not None and "pets" not in f:
            f["pets"] = f"petsAllowed: {x.get('petsAllowed')}"
        if x.get("floorLevel") and "floor" not in f:
            f["floor"] = str(x.get("floorLevel"))
        am = x.get("amenityFeature")
        if am:
            f.setdefault("text", []).extend(str(a.get("name") if isinstance(a, dict) else a) for a in (am if isinstance(am, list) else [am]))
        for k in ("url", "image", "name", "description"):
            v = x.get(k)
            if isinstance(v, list):
                v = v[0] if v else None
            if isinstance(v, dict):
                v = v.get("url") or v.get("contentUrl")
            if isinstance(v, str) and v and k not in f:
                f[k] = v
        if f.get("description"):
            f.setdefault("text", []).append(f["description"])
    return f


def walk_state(blobs):
    """Walk embedded state. Returns (page_addr, units, texts, geo). A unit is a dict with a price key and a beds key (or a
    'Unit X' name and a price); a unit that contains other units (a floor plan holding its units) is dropped for them.
    Subtrees named like other listings (similar, nearby, recommended, search ...) are skipped. Apollo __ref links are
    followed. JSON held in a string is opened."""
    refs = {}
    for _, d in blobs:
        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict) and ":" in str(k):
                    refs[k] = v
    cands, addrs, texts, geo = [], [], [], {}
    queue = [(d, (label,), 0) for label, d in blobs]
    seen = set()
    while queue:  # breadth first: the page's own listing sits shallower than anything else
        node, path, depth = queue.pop(0)
        if depth > 40:
            continue
        if isinstance(node, str):
            s = node.strip()
            if len(s) > 50 and s[:1] in "{[":
                d = _decode_json(s)
                if d is not None:
                    queue.append((d, path + ("<json>",), depth + 1))
            continue
        if isinstance(node, list):
            for i, v in enumerate(node):
                queue.append((v, path + (i,), depth + 1))
            continue
        if not isinstance(node, dict):
            continue
        if set(node) == {"__ref"} or (len(node) <= 2 and "__ref" in node):
            r = node.get("__ref")
            if r in refs and r not in seen:
                seen.add(r)
                queue.append((refs[r], path + (r,), depth + 1))
            continue
        a = addr_from_dict(node)
        if a:
            addrs.append((path, a))
        for k in ("address", "location", "fullLocation", "formattedAddress", "fullAddress", "addressString"):
            v = node.get(k)
            if isinstance(v, str):
                a2 = addr_from_text(v)
                if a2:
                    addrs.append((path + (k,), a2))
        if node.get("latitude") and node.get("longitude") and not geo:
            geo = {"lat": node["latitude"], "lon": node["longitude"]}
        pk, pv = _first(node, PRICE_KEYS)
        bk, bv = _first(node, BEDS_KEYS)
        name = str(node.get("name") or "")
        price = _price_of(pv) if pk else None
        if price is not None and (bk or re.match(r"(?:unit|apt|apartment)\s+\S+", name, re.I)):
            cands.append((path, node, price))
        for k, v in node.items():
            if SKIP_KEY.search(str(k)):
                continue
            if TEXT_KEY.search(str(k)):
                if isinstance(v, str) and 2 < len(v) < 3000:
                    texts.append(f"{k}: {v}")
                elif isinstance(v, bool):
                    texts.append(f"{k}: {'yes' if v else 'no'}")
                elif isinstance(v, (int, float)):
                    texts.append(f"{k}: {v}")
                elif isinstance(v, list) and v and all(isinstance(x, str) for x in v):
                    texts.extend(f"{k}: {x}" for x in v[:60])
                elif isinstance(v, dict):
                    leaves = [x for x in v.values() if isinstance(x, str) and 2 < len(x) < 3000]
                    texts.extend(f"{k}: {x}" for x in leaves[:20])
            queue.append((v, path + (k,), depth + 1))
    paths = [c[0] for c in cands]
    units = []
    for path, node, price in cands:
        if any(len(p) > len(path) and p[: len(path)] == path for p in paths):
            continue
        units.append((path, node, price))
    page_addr = addrs[0][1] if addrs else None
    return page_addr, units, addrs, texts, geo


def unit_fields(path, node, price, addrs):
    """Fields of one unit dict, plus the address found inside it (if any)."""
    f = {"rent": price}
    for keys, conv, name in ((BEDS_KEYS, to_beds, "beds"), (SQFT_KEYS, to_sqft, "sqft")):
        k, v = _first(node, keys)
        if k and conv(v) is not None:
            f[name] = conv(v)
    k, v = _first(node, BATH_KEYS)
    if k:
        b = v.get("formattedValue") if isinstance(v, dict) else v
        m = re.search(r"\d+(?:\.\d)?", str(b))
        if m:
            f["baths"] = float(m.group()) if "." in m.group() else int(m.group())
    k, v = _first(node, UNIT_KEYS)
    if k and isinstance(v, (str, int)):
        f["unit"] = re.sub(r"^(?:unit|apt\.?|#)\s*", "", str(v), flags=re.I).strip()
    elif re.match(r"(?:unit|apt|apartment)\s+\S+", str(node.get("name") or ""), re.I):
        f["unit"] = str(node["name"]).split(None, 1)[1].lstrip("#")
    if node.get("isAvailableNow") is True or node.get("availableNow") is True:
        f["avail_raw"] = "now"
    else:
        k, v = _first(node, AVAIL_KEYS)
        if k and isinstance(v, (str, int)):
            f["avail_raw"] = str(v)
    k, v = _first(node, FLOOR_KEYS)
    if k and isinstance(v, (str, int)) and re.search(r"\d", str(v)):
        f["floor"] = str(v)
    own = [a for p, a in addrs if p[: len(path)] == path]
    if own:
        f["addr"] = own[0]
    for k in ("url", "hdpUrl", "detailUrl", "listingUrl"):
        if isinstance(node.get(k), str) and node[k].startswith(("http", "/")):
            f["url"] = node[k]
            break
    return f


# ----------------------------------------------------------------------------------------------------------------------
# visible text
# ----------------------------------------------------------------------------------------------------------------------
RENT_RE = re.compile(r"\$\s?(\d{1,2},\d{3}|\d{3,5})(?:\.\d\d)?\s*(?:[-–]\s*\$?\s?(?:\d{1,2},\d{3}|\d{3,5}))?\s*"
                     r"(?:/\s*mo(?:nth)?\b|per\s+month|a\s+month|monthly|/\s*month)", re.I)
RENT_LABEL_RE = re.compile(r"\b(?:rent|price|monthly rent)\s*[:\-]?\s*\$\s?(\d{1,2},\d{3}|\d{3,5})", re.I)
RENT_CL_RE = re.compile(r"\$\s?(\d{1,2},\d{3}|\d{3,5})\s*/\s*(?:studio|\d\s*br)\b", re.I)  # Craigslist: '$1,650 / 1br'

BEDS_RE = re.compile(r"\bstudio\b|\b(\d)\s*(?:bd|bds|br|bed|beds|bedroom|bedrooms)\b", re.I)
BATH_RE = re.compile(r"\b(\d(?:\.5)?)\s*(?:ba|bath|baths|bathroom|bathrooms)\b", re.I)
SQFT_RE = re.compile(r"\b(\d{1,2},\d{3}|\d{3,4})\s*(?:sq\.?\s*ft\.?|sqft|square\s+feet|ft²|ft2)", re.I)
AVAIL_NOW_RE = re.compile(r"\bavailable\s+(?:now|immediately|today)\b|\bmove[- ]in\s*(?:date)?\s*[:\-]?\s*(?:now|immediately)\b", re.I)
AVAIL_RE = re.compile(r"\b(?:available|availability|move[- ]in(?: date)?|date available)\s*(?:on|from|date|starting)?\s*[:\-]?\s*"
                      r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+20\d\d)?"
                      r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?|20\d\d-\d\d-\d\d)", re.I)
UNIT_RE = re.compile(r"\b(?:unit|apt\.?|apartment)\s*#?\s*([A-Za-z]?\d{1,4}[A-Za-z]?)\b", re.I)
FLOOR_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s+floor\b|\bfloor\s*(?:level|number)?\s*[:#]\s*(\d{1,2})\b", re.I)
BFLOORS_RE = re.compile(r"\b(\d{1,2})[- ](?:story|stories|storey|floor)\s+(?:building|walk-?up|elevator)|\b(\d{1,2})\s+stories\b", re.I)
AGE_RE = re.compile(r"\blisted\s+(\d{1,3})\s+days?\s+ago\b|\b(\d{1,3})\s+days?\s+on\s+(?:zillow|trulia|streeteasy|market|site)\b", re.I)


def lines_of(text):
    out = []
    for ln in re.split(r"[\r\n]+", str(text or "")):
        ln = re.sub(r"[ \t\xa0]+", " ", ln).strip()
        if ln:
            out.extend(x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", ln) if x.strip())
    return out


def read_text(text, ref: date):
    """Facts stated in plain text (the visible page, a PDF, OCR output, or text found in page JSON)."""
    f = {}
    t = str(text or "")
    a = addr_from_text(t)
    if a:
        f["addr"] = a
    m = RENT_RE.search(t) or RENT_LABEL_RE.search(t) or RENT_CL_RE.search(t)
    if m:
        f["rent"] = to_money(m.group(1))
        if re.search(r"[-–]\s*\$?\s?\d", m.group(0)):
            f["rent_note"] = f"text shows a range '{clip(m.group(0), 40)}'; low end recorded"
    m = BEDS_RE.search(t)
    if m:
        f["beds"] = 0 if m.group(0).lower() == "studio" else int(m.group(1))
    m = BATH_RE.search(t)
    if m:
        f["baths"] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
    m = SQFT_RE.search(t)
    if m:
        f["sqft"] = to_sqft(m.group(1))
    if AVAIL_NOW_RE.search(t):
        f["avail_raw"] = "now"
        f["avail_text"] = clip(AVAIL_NOW_RE.search(t).group(0), 80)
    else:
        m = AVAIL_RE.search(t)
        if m:
            f["avail_raw"], f["avail_text"] = m.group(1), clip(m.group(0), 80)
    m = UNIT_RE.search(t)
    if m and "unit" not in (a or {}):
        f["unit"] = m.group(1)
    m = FLOOR_RE.search(t)
    if m:
        f["floor"] = m.group(1) or m.group(2)
    m = BFLOORS_RE.search(t)
    if m:
        f["building_floors"] = m.group(1) or m.group(2)
    m = AGE_RE.search(t)
    if m:
        f["age"] = m.group(1) or m.group(2)
    L = lines_of(t)
    tl = t.lower()
    dog_lines = [x for x in L if re.search(r"\bdogs?|\bpets?\b|\bpets?allowed|haspets|pet[- ]friendly|cats? only", x, re.I)
                 and not re.search(r"pet (?:spa|wash)|dog (?:park|run|wash)", x, re.I)]
    if dog_lines:
        f["dog_text"] = clip(" | ".join(dog_lines[:4]), 300)
        dt = " ".join(dog_lines).lower()
        if re.search(r"no dogs|dogs? (?:are )?not (?:allowed|permitted|accepted)|no pets|pets? not allowed|cats? only|dogs?: no\b|dogs?allowed: no\b", dt):
            f["dogs"] = "no"
        elif re.search(r"dogs? (?:are )?(?:allowed|ok|okay|welcome|permitted|accepted)|dogs?: (?:yes|allowed)|dog[- ]friendly|"
                       r"dogs allowed|large dogs|small dogs|dogs?allowed: yes\b", dt):
            f["dogs"] = "yes"
        kind, lb = parsers.parse_dog_weight(dt)
        if kind == "limit":
            f["dog_lb"] = int(lb)
    if re.search(r"\bno elevator\b|\bwalk[- ]?up\b|\bnon[- ]elevator\b|elevator\s*:\s*no\b", tl):
        f["elevator"] = "no"
    elif re.search(r"\belevators?\b", tl):
        f["elevator"] = "yes"
    park = [x for x in L if re.search(r"\bparking\b|\bgarage\b", x, re.I)]
    if park:
        f["parking_text"] = clip(" | ".join(park[:3]), 250)
        pp = parsers.parse_parking(" ".join(park[:3]))
        if pp.get("fee") is not None:
            f["parking_fee"] = pp["fee"]
    pet = [x for x in L if re.search(r"pet rent|monthly pet|pet fee|dog rent", x, re.I)]
    if pet:
        clauses = [c for c in re.split(r"[,;|]", " ; ".join(pet[:3])) if re.search(r"pet rent|monthly pet|pet fee|dog rent|\$", c, re.I)]
        v, _ = parsers.parse_pet_rent(" ; ".join(clauses), default_monthly=False)
        if v is not None:
            f["pet_rent"] = v
        f["pet_text"] = clip(" | ".join(pet[:3]), 250)
    fee = [x for x in L if re.search(r"\bfees?\b|\bdeposit\b", x, re.I) and not re.search(r"pet|parking|broker|\bno fee\b", x, re.I)]
    if fee:
        f["fee_text"] = [clip(x, 200) for x in fee[:6]]
        tot, note = parsers.monthly_fees_from_text(" ; ".join(fee[:6]))
        if tot is not None:
            f["fee_total"], f["fee_note"] = tot, note
    if re.search(r"in[- ]unit (?:washer|laundry|w/d)|washer\s*(?:/|and|&)\s*dryer in (?:the )?unit|w/d in unit", tl):
        f["laundry"] = "in_unit"
    elif re.search(r"laundry (?:room|in (?:the )?building|on[- ]site|facilities)|shared laundry|on-site laundry", tl):
        f["laundry"] = "in_building"
    ut = [x for x in L if re.search(r"utilit|heat (?:and|&) hot water|heat included", x, re.I)]
    if ut:
        f["utilities"] = clip(" | ".join(ut[:2]), 200)
    conc = [x for x in L if re.search(r"months? free|weeks? free|net[- ]effective|concession", x, re.I)]
    if conc:
        f["concession"] = clip(" | ".join(conc[:2]), 200)
    if re.search(r"broker fee|no fee", tl):
        bf = [x for x in L if re.search(r"broker fee|\bno fee\b", x, re.I)]
        f["broker"] = clip(bf[0], 150) if bf else ""
    return f


# ----------------------------------------------------------------------------------------------------------------------
# files
# ----------------------------------------------------------------------------------------------------------------------
def html_of_mhtml(raw: bytes) -> tuple[str, str]:
    msg = email.message_from_bytes(raw)
    loc = msg.get("Snapshot-Content-Location", "")
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            body = part.get_payload(decode=True) or b""
            return body.decode(part.get_content_charset() or "utf-8", "ignore"), loc or part.get("Content-Location", "")
    return "", loc


def page_url(html, soup):
    for sel, attr in (("link[rel=canonical]", "href"), ("meta[property='og:url']", "content"), ("meta[name='og:url']", "content")):
        el = soup.select_one(sel)
        if el and (el.get(attr) or "").startswith("http"):
            return el.get(attr).strip(), sel.split("[")[0] + " " + sel.split("[")[1].rstrip("]")
    m = re.search(r"<!--\s*saved from url=\(\d+\)(https?://[^\s>]+)\s*-->", html[:3000], re.I)
    if m:
        return m.group(1), "browser 'saved from url' line"
    return "", ""


def parse_html(html: str, ref: date, url_hint: str = ""):
    """(page, units) from one saved page. page: page-level facts with 'src' notes; units: list of per-unit dicts."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    url, url_from = page_url(html, soup)
    if not url and url_hint:
        url, url_from = url_hint, "the link pasted in links.txt / MHTML snapshot location"
    title = clip(soup.title.get_text() if soup.title else "", 200)
    og_img = soup.select_one("meta[property='og:image']")
    ld = read_jsonld(jsonld_items(soup))
    blobs = embedded_blobs(html, soup)
    page_addr, units, addrs, jtexts, geo = walk_state(blobs)
    for t in soup(["script", "style", "noscript", "svg", "template"]):
        t.decompose()
    vis = soup.get_text("\n")
    txt = read_text(vis, ref)
    jtx = read_text("\n".join(jtexts + ld.get("text", [])), ref)
    page = {"url": url, "url_from": url_from or "not in the saved page", "title": title, "src": {},
            "photo": (og_img.get("content") if og_img else "") or ld.get("image", ""), "blobs": [b[0] for b in blobs],
            "ld": bool(ld), "name": ld.get("name", "")}
    # address: JSON-LD, the page title, the embedded state, the visible text
    for how, a in (("JSON-LD", ld.get("addr")), ("page title", addr_from_text(title)), ("embedded page data", page_addr),
                   ("visible text", txt.get("addr"))):
        if a:
            page["addr"], page["src"]["address"] = a, how
            break
    if ld.get("lat"):
        page["lat"], page["lon"] = ld["lat"], ld["lon"]
    elif geo:
        page["lat"], page["lon"] = geo["lat"], geo["lon"]
    # page-level facts (shared by every unit): JSON-LD, then text from the page data, then visible text
    for k in ("dogs", "dog_text", "dog_lb", "elevator", "building_floors", "parking_text", "parking_fee", "pet_rent",
              "pet_text", "fee_text", "fee_total", "fee_note", "laundry", "utilities", "concession", "broker", "age"):
        for how, src in (("embedded page data / JSON-LD", jtx), ("visible text", txt)):
            if src.get(k) not in (None, "", []):
                page[k], page["src"][k] = src[k], how
                break
    if ld.get("pets") and "dog_text" not in page:
        page["dog_text"], page["src"]["dog_text"] = ld["pets"], "JSON-LD"
    rows = []
    for path, node, price in units:
        u = unit_fields(path, node, price, addrs)
        if u.get("addr") and page.get("addr") and not same_street(u["addr"]["address"], page["addr"]["address"]):
            continue  # another listing carried in the page data
        u["how"] = "embedded page data (" + str(path[0]) + ")"
        rows.append(u)
    if not rows:
        u = {}
        for k in ("rent", "beds", "baths", "sqft", "avail_raw", "floor"):
            for how, src in (("JSON-LD", ld), ("visible text", txt)):
                if src.get(k) not in (None, ""):
                    u[k] = src[k]
                    page["src"][k] = how
                    break
        if txt.get("rent_note") and page["src"].get("rent") == "visible text":
            u["rent_note"] = txt["rent_note"]
        u["how"] = "page-level"
        rows.append(u)
    # unit, availability text and floor from the page when the unit dict did not carry them
    for u in rows:
        if not u.get("unit"):
            a = u.get("addr") or page.get("addr") or {}
            if a.get("unit"):
                u["unit"] = a["unit"]
            elif len(rows) == 1 and txt.get("unit"):
                u["unit"], page["src"]["unit"] = txt["unit"], "visible text"
        if len(rows) == 1:
            if not u.get("avail_raw") and txt.get("avail_raw"):
                u["avail_raw"], page["src"]["available"] = txt["avail_raw"], "visible text"
            if not u.get("floor") and txt.get("floor"):
                u["floor"], page["src"]["floor"] = txt["floor"], "visible text"
            if txt.get("avail_text"):
                u.setdefault("avail_text", txt["avail_text"])
    return page, rows


def pdf_text(path: Path) -> tuple[str, str]:
    """(text, creation time ISO or '')."""
    text, created = "", ""
    if shutil.which("pdftotext"):
        r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, timeout=120)
        text = r.stdout.decode("utf8", "ignore")
    if not text.strip():
        try:
            from pypdf import PdfReader
            text = "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
        except Exception:  # noqa: BLE001 - an unreadable PDF is reported as "needs reading"
            text = ""
    if shutil.which("pdfinfo"):
        r = subprocess.run(["pdfinfo", "-isodates", str(path)], capture_output=True, timeout=60)
        m = re.search(r"^CreationDate:\s*(\S+)", r.stdout.decode("utf8", "ignore"), re.M)
        if m:
            try:
                created = datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).astimezone(timezone.utc).replace(microsecond=0).isoformat()
            except ValueError:
                created = ""
    return text, created


def ocr_text(path: Path) -> str | None:
    """OCR text, or None when no OCR engine is installed (the tesseract binary; nothing is installed by this script)."""
    if not shutil.which("tesseract"):
        return None
    r = subprocess.run(["tesseract", str(path), "stdout"], capture_output=True, timeout=300)
    return r.stdout.decode("utf8", "ignore") if r.returncode == 0 else ""


def parse_plain(text: str, ref: date):
    """(page, rows) from text without page structure (PDF, OCR, .txt)."""
    t = read_text(text, ref)
    url = ""
    for m in re.finditer(r"https?://[^\s<>\"')]+", text):
        url = m.group(0)
        if site_of(url) != bare(urlparse(url).netloc) or re.search(r"/(?:homedetails|rental|building|apartments?|p|b|listing|for-rent)", url):
            break
    page = {"url": url, "url_from": "a link printed in the file" if url else "not in the file", "title": "", "src": {}, "photo": "",
            "blobs": [], "ld": False, "name": ""}
    if t.get("addr"):
        page["addr"], page["src"]["address"] = t["addr"], "text"
    for k in ("dogs", "dog_text", "dog_lb", "elevator", "building_floors", "parking_text", "parking_fee", "pet_rent",
              "pet_text", "fee_text", "fee_total", "fee_note", "laundry", "utilities", "concession", "broker", "age"):
        if t.get(k) not in (None, "", []):
            page[k], page["src"][k] = t[k], "text"
    u = {k: t[k] for k in ("rent", "beds", "baths", "sqft", "avail_raw", "avail_text", "floor", "unit", "rent_note") if t.get(k) not in (None, "")}
    for k in ("rent", "beds", "baths", "sqft", "avail_raw", "floor", "unit"):
        if k in u:
            page["src"][k] = "text"
    if not u.get("unit") and (t.get("addr") or {}).get("unit"):
        u["unit"] = t["addr"]["unit"]
    u["how"] = "page-level"
    return page, [u]


# ----------------------------------------------------------------------------------------------------------------------
# rows
# ----------------------------------------------------------------------------------------------------------------------
def floor_of(f):
    s = str(f or "").strip().lower()
    if not s:
        return ""
    if s in ("ground", "g", "ground floor", "lobby"):
        return "0"
    m = re.search(r"\d{1,2}", s)
    return m.group() if m else ""


FIELD_NAMES = {"avail_raw": "available date", "available": "available date", "dog_lb": "dog weight limit",
               "dog_text": "dog policy", "rent": "rent", "parking_text": "parking", "parking_fee": "parking fee",
               "pet_text": "pet fees", "fee_text": "fees", "fee_total": "monthly fee total", "fee_note": "fee note",
               "building_floors": "building floors", "age": "listing age", "broker": "broker fee"}


def _num(v):
    return int(v) if isinstance(v, float) and v == int(v) else v


def make_rows(page, units, *, fid, filename, kind, seen_at, raw_path, ref: date, note_head):
    """Contract rows for one file, and status lines for what was left out."""
    rows, left = [], []
    site = site_of(page["url"], page["title"])
    a0 = page.get("addr") or {}
    for i, u in enumerate(units):
        a = u.get("addr") or a0
        beds, rent = u.get("beds"), u.get("rent")
        if beds is not None and beds > 1:
            left.append(f"{beds}-bedroom at ${rent or '?'}: outside the search (studios and 1-bedrooms only)")
            continue
        if rent is not None and rent > RENT_MAX:
            left.append(f"{'studio' if beds == 0 else (str(beds) + '-bed' if beds is not None else 'unit')} "
                        f"{u.get('unit', '')} at ${rent:,}: above the ${RENT_MAX:,} collection limit".replace("  ", " "))
            continue
        if not a.get("address") and rent is None:
            continue
        unit = str(u.get("unit") or a.get("unit") or "").strip()
        avail_raw = str(u.get("avail_raw") or "")
        avail = "now" if re.search(r"\bnow\b|immediate|today", avail_raw, re.I) else to_date(avail_raw, ref)
        src = dict(page["src"])
        notes = [note_head]
        if u["how"] != "page-level":
            notes.append(f"unit read from {u['how']}")
        fields_from = ", ".join(f"{FIELD_NAMES.get(k, k)} from {v}" for k, v in sorted(src.items()))
        if fields_from:
            notes.append("fields read: " + fields_from)
        notes.append(f"listing URL: {page['url_from']}")
        if u.get("rent_note"):
            notes.append(u["rent_note"])
        if kind == "screenshot":
            notes.append("read by OCR from a screenshot: check the figures against the image")
        if page.get("broker"):
            notes.append(f"broker: '{page['broker']}'")
        fees = {}
        if page.get("fee_total") is not None:
            fees["required_monthly_total"] = page["fee_total"]
            if page.get("fee_note"):
                fees["note"] = page["fee_note"]
        if page.get("fee_text"):
            fees["fee_text"] = page["fee_text"]
        unit_url = u.get("url") or ""
        if unit_url.startswith("/") and page["url"]:
            p = urlparse(page["url"])
            unit_url = f"{p.scheme}://{p.netloc}{unit_url}"
        lid = f"inbox:{fid}:{re.sub(r'[^A-Za-z0-9-]', '', unit) or 'p' + str(i)}"
        if any(r["listing_id"] == lid for r in rows):
            lid += f"-{i}"
        rows.append(dict(
            listing_id=lid, source_site=site, url=unit_url or page["url"], detail_level="detail",
            first_seen=seen_at, last_seen=seen_at, building_name=page.get("name", "") if page.get("ld") else "",
            address=a.get("address", ""), city=a.get("city", ""), state=a.get("state", ""), zip=a.get("zip", ""),
            lat=page.get("lat", ""), lon=page.get("lon", ""), unit=unit,
            beds="" if beds is None else beds, baths=u.get("baths", ""), sqft=u.get("sqft", ""),
            listed_rent="" if rent is None else rent,
            price_basis="as shown on the page the owner saved; whether it is net of a concession is not stated" if rent is not None else "",
            concession_text=page.get("concession", ""),
            available_date_text=u.get("avail_text") or (avail_raw if avail_raw else ""), available_date=avail,
            dogs=page.get("dogs", "unknown"), dog_policy_text=page.get("dog_text", ""), dog_weight_limit_lb=page.get("dog_lb", ""),
            elevator=page.get("elevator", "unknown"), floor=floor_of(u.get("floor")) or "unknown",
            building_floors=page.get("building_floors", ""), parking_type=page.get("parking_text", ""),
            parking_fee=page.get("parking_fee", ""), pet_rent=page.get("pet_rent", ""),
            other_monthly_fees_json=json.dumps(fees) if fees else "", utilities_included=page.get("utilities", ""),
            laundry=page.get("laundry", ""), listing_type="unknown", manager="", listing_age_days=page.get("age", ""),
            photo_url=parsers.strip_url_secrets(page.get("photo", "")), building_url="", raw_path=raw_path,
            notes="; ".join(notes)))
        rows[-1] = {k: _num(v) for k, v in rows[-1].items()}
    return rows, left


def file_id(raw: bytes) -> str:
    return hashlib.sha1(raw).hexdigest()[:10]


def read_file(path: Path, rel: str, ref_override: date | None = None):
    """(rows, status line) for one dropped file."""
    raw = path.read_bytes()
    fid = file_id(raw)
    ext = path.suffix.lower()
    saved = iso_utc(path.stat().st_mtime)
    ref = ref_override or datetime.fromisoformat(saved).date()
    if ext in HTML_EXT | MHTML_EXT:
        if ext in MHTML_EXT:
            html, hint = html_of_mhtml(raw)
        else:
            html, hint = raw.decode("utf8", "ignore"), ""
        page, units = parse_html(html, ref, hint)
        kind, head = "page", f"provided by the owner (saved page {path.name})"
    elif ext in PDF_EXT:
        text, created = pdf_text(path)
        if not text.strip():
            return [], f"{path.name}: needs reading (no text could be taken from this PDF; it may be an image)"
        saved = created or saved
        page, units = parse_plain(text, ref)
        kind, head = "pdf", f"provided by the owner (PDF {path.name})"
    elif ext in IMG_EXT:
        text = ocr_text(path)
        if text is None:
            return [], f"{path.name}: needs reading (screenshot; no text reader (OCR) is installed here, so it is read by hand)"
        if not text.strip():
            return [], f"{path.name}: needs reading (the text reader found no words in this screenshot)"
        page, units = parse_plain(text, ref)
        kind, head = "screenshot", f"provided by the owner (screenshot {path.name})"
    elif ext in TEXT_EXT:
        page, units = parse_plain(raw.decode("utf8", "ignore"), ref)
        kind, head = "text", f"provided by the owner (text file {path.name})"
    else:
        return [], f"{path.name}: needs reading (file type {ext or 'unknown'} is not read automatically)"
    head += f"; saved {saved}"
    rows, left = make_rows(page, units, fid=fid, filename=path.name, kind=kind, seen_at=saved, raw_path=rel, ref=ref, note_head=head)
    return rows, status_line(path.name, page, rows, left)


def status_line(name, page, rows, left):
    if not rows and not left:
        return f"{name}: needs reading (no address or rent could be read from it)"
    site = site_of(page["url"], page["title"])
    bits = [f"{name}: {len(rows)} listing(s) added from {site}"]
    for r in rows[:6]:
        b = {"": "beds ?", "0": "studio", "1": "1 bed"}.get(str(r["beds"]), f"{r['beds']} bed")
        bits.append(f"  - {r['address'] or 'address not shown'} {('#' + r['unit']) if r['unit'] else ''} {b}, "
                    f"${r['listed_rent'] or '?'}, available {r['available_date'] or 'not stated'}".replace("  ,", ","))
    if len(rows) > 6:
        bits.append(f"  - and {len(rows) - 6} more")
    for x in left:
        bits.append(f"  - left out: {x}")
    return "\n".join(bits)


# ----------------------------------------------------------------------------------------------------------------------
# links.txt
# ----------------------------------------------------------------------------------------------------------------------
REFUSED_FILE = lib.RAW / LINK_SRC / "_refused_hosts.json"


def _refused():
    try:
        return json.loads(REFUSED_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _refuse(host, why):
    d = _refused()
    d[bare(host)] = {"reason": why, "at": lib.now_iso(), "by": "scripts/h_inbox.py"}
    REFUSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    REFUSED_FILE.write_text(json.dumps(d, indent=1))


def link_verdict(url: str):
    """None when the link may be fetched, else the reason it is not (shown in STATUS.txt)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        return "not a web link"
    host = bare(p.netloc)
    for dom, name in SAVE_INSTEAD.items():
        if host == dom or host.endswith("." + dom):
            return f"{name} pages are never opened by our tools: save the page instead (File > Save Page As) and drop it in inbox/"
    for dom in EXTRA_OFF:
        if host == dom or host.endswith("." + dom):
            return f"{dom} is off limits to our tools (CLAUDE.md): save the page instead"
    if host in _refused():
        return f"{host} refused us earlier ({_refused()[host].get('reason')}): save the page instead"
    why = lib.host_refusal(host)
    if why and not any(host == d or host.endswith("." + d) for d in PASTED_OK):
        return f"{why}: save the page instead"
    if why and any(host == d or host.endswith("." + d) for d in PASTED_OK):
        # a link a person pasted: only the kill file can still stop it
        os.environ["HOUSE_HUNT_ALLOW_HOST"] = host
        try:
            why2 = lib.host_refusal(host)
        finally:
            os.environ.pop("HOUSE_HUNT_ALLOW_HOST", None)
        kill = lib.RAW / lib.KILL_FILE_NAME
        try:
            killed = any(lib._covers(e, host) for e in json.loads(kill.read_text()))
        except (OSError, ValueError):
            killed = False
        if why2 or killed:
            return f"{host} refused us earlier: save the page instead"
    return None


def _get(url, ext):
    host = bare(urlparse(url).netloc)
    lib.HOST_DELAY[urlparse(url).netloc] = max(LINK_DELAY, lib.HOST_DELAY.get(urlparse(url).netloc, 0))
    allow = any(host == d or host.endswith("." + d) for d in PASTED_OK)
    if allow:
        os.environ["HOUSE_HUNT_ALLOW_HOST"] = host
    try:
        return lib.cached_get(url, LINK_SRC, ext=ext, retries=1, headers={"User-Agent": lib.USER_AGENT + " Claude-User"})
    finally:
        if allow:
            os.environ.pop("HOUSE_HUNT_ALLOW_HOST", None)


def robots_ok(url, fetch=None) -> tuple[bool, str]:
    fetch = fetch or _get
    p = urlparse(url)
    try:
        body, meta = fetch(f"{p.scheme}://{p.netloc}/robots.txt", "txt")
    except Exception as e:  # noqa: BLE001
        return False, f"robots.txt could not be read ({clip(e, 80)})"
    if meta["status"] in (401, 403, 429):
        _refuse(p.netloc, f"HTTP {meta['status']} on robots.txt")
        return False, f"robots.txt refused (HTTP {meta['status']}); host recorded as refused"
    if meta["status"] != 200:
        return True, f"no robots.txt (HTTP {meta['status']})"
    rp = robotparser.RobotFileParser()
    rp.parse(body.decode("utf8", "ignore").splitlines())
    if not rp.can_fetch("Claude-User", url):
        return False, "robots.txt does not allow this page for us"
    return True, ""


def read_links(path: Path, fetch=None, ref_override: date | None = None):
    """(rows, status lines) for inbox/links.txt. fetch(url, ext) -> (bytes, meta) is lib.cached_get by default."""
    fetch = fetch or _get
    rows, status = [], []
    if not path.exists():
        return rows, status
    seen = set()
    for line in path.read_text(encoding="utf8", errors="ignore").splitlines():
        url = line.strip()
        if not url or url.startswith("#") or url in seen:
            continue
        seen.add(url)
        why = link_verdict(url)
        if why:
            status.append(f"link {url}: not opened. {why}")
            continue
        ok, rwhy = robots_ok(url, fetch)
        if not ok:
            status.append(f"link {url}: not opened. {rwhy}: save the page instead")
            continue
        try:
            body, meta = fetch(url, "html")
        except lib.HostRefused as e:
            status.append(f"link {url}: not opened. {e}")
            continue
        except Exception as e:  # noqa: BLE001
            status.append(f"link {url}: could not be opened ({clip(e, 100)}); save the page instead")
            continue
        html = body.decode("utf8", "ignore")
        if meta["status"] in (401, 403, 429) or re.search(r"captcha|are you a robot|access denied|cf-chl", html[:20000], re.I):
            _refuse(urlparse(url).netloc, f"HTTP {meta['status']}" + (" / bot check" if meta["status"] == 200 else ""))
            status.append(f"link {url}: the site refused us (HTTP {meta['status']}); host recorded, no more requests: save the page instead")
            continue
        if meta["status"] != 200:
            status.append(f"link {url}: HTTP {meta['status']} (gone or moved?)")
            continue
        seen_at = meta["retrieved_at"]
        ref = ref_override or datetime.fromisoformat(seen_at).date()
        page, units = parse_html(html, ref, url)
        if not page["url"]:
            page["url"] = url
        fid = hashlib.sha1(url.encode()).hexdigest()[:10]
        r, left = make_rows(page, units, fid=fid, filename="links.txt", kind="link", seen_at=seen_at, raw_path=meta["path"], ref=ref,
                            note_head=f"provided by the owner (link in inbox/links.txt; page opened {seen_at})")
        rows += r
        status.append(status_line(f"link {url}", page, r, left))
    return rows, status


# ----------------------------------------------------------------------------------------------------------------------
def run(inbox: Path = INBOX, out: Path = OUT, fetch=None, status_path: Path | None = None, ref_override: date | None = None):
    inbox.mkdir(parents=True, exist_ok=True)
    old = {}
    if out.exists():
        old = {r["listing_id"]: r for r in csv.DictReader(open(out, newline="", encoding="utf8"))}
    rows, status = [], []
    present_fids = set()
    for p in sorted(inbox.iterdir()):
        if p.is_dir() or p.name.lower() in SKIP_NAMES or p.name.startswith((".", "~")):
            continue  # "Webpage, complete" also writes a <name>_files/ folder: images and scripts, not read
        rel = os.path.relpath(p, ROOT) if p.is_relative_to(ROOT) else str(p)
        present_fids.add(file_id(p.read_bytes()))
        r, s = read_file(p, rel, ref_override)
        rows += r
        status.append(s)
    lr, ls = read_links(inbox / "links.txt", fetch, ref_override)
    rows += lr
    status += ls
    new_ids = {r["listing_id"] for r in rows}
    for r in rows:
        if r["listing_id"] in old and old[r["listing_id"]].get("first_seen"):
            r["first_seen"] = min(old[r["listing_id"]]["first_seen"], r["first_seen"])
    kept = []
    for lid, r in old.items():
        if lid in new_ids:
            continue
        fid = lid.split(":")[1] if lid.count(":") >= 2 else ""
        from_file = not str(r.get("raw_path", "")).startswith("raw/")
        if from_file and fid not in present_fids:
            kept.append(r)  # its file is not here (raw files are not committed): the row stays as recorded
    allrows = sorted(rows + kept, key=lambda r: r["listing_id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(allrows)
    sp = status_path or (inbox / "STATUS.txt")
    head = ("What was read from the inbox (rewritten each time the inbox is read; newest run only).\n"
            "\"needs reading\" means a person has to look at the file; \"save the page instead\" means we may not open that "
            "site, so please save the page from your browser and drop the file here.\n\n")
    body = "\n".join(status) if status else "The inbox is empty."
    if kept:
        body += f"\n\n{len(kept)} listing(s) from files no longer in the inbox are kept as recorded."
    sp.write_text(head + body + "\n", encoding="utf8")
    print(f"manual_inbox.csv: {len(allrows)} rows ({len(rows)} from files and links now in inbox/, {len(kept)} kept)")
    for s in status:
        print(" ", s.splitlines()[0])
    return allrows, status


if __name__ == "__main__":
    run()
