"""Craigslist harvest: studios and 1BRs at or under $3,000, dogs-OK filter, NYC metro sites.

STATUS 2026-11-15: NOT RUN IN BULK. Craigslist's Terms of Use (www.craigslist.org/about/terms.of.use)
say "You agree not to copy/collect CL content via robots, spiders, scripts, scrapers, crawlers, or any
automated or manual equivalent" and forbid collecting user information. robots.txt allows the paths, but
CLAUDE.md rule 3 says to respect terms, so this script refuses to fetch unless Will has approved it and
it is started with --approved-by-will. See docs/harvest_notes/craigslist.md.

Parsing was tested only against one cached search page and one cached posting page (--selftest).

Usage:
  python3 scripts/h_craigslist.py --selftest SEARCH.html POST.html   # offline parser check
  python3 scripts/h_craigslist.py --approved-by-will [--max-requests 1400] [--refresh-search]

Idempotent and resumable: posting pages are cached in raw/craigslist/, rows are keyed by post id,
first_seen is kept and last_seen updated on re-runs. No phone numbers, emails or poster names are stored;
phone numbers are only hashed in memory to count repeats.
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import lib

SOURCE = "craigslist"
HOST = "https://www.craigslist.org"
OUT = lib.DATA / "listings_raw" / "craigslist.csv"
COLS = ("listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,"
        "unit,beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,"
        "dog_policy_text,dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,"
        "other_monthly_fees_json,utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,"
        "building_url,raw_path,notes").split(",")

# Nearest to Jamaica first. newyork.craigslist.org/search/<sub>/apa redirects to these www URLs.
AREAS = [("que", "/search/subarea/que"), ("brk", "/search/subarea/brk"), ("lgi", "/search/subarea/lgi"),
         ("brx", "/search/subarea/brx"), ("stn", "/search/subarea/stn"), ("wch", "/search/subarea/wch"),
         ("jsy", "/search/subarea/jsy"), ("fct", "/search/subarea/fct"), ("newjersey", "/search/area/newjersey"),
         ("cnj", "/search/area/cnj"), ("hudsonvalley", "/search/area/hudsonvalley"),
         ("newhaven", "/search/area/newhaven"), ("jerseyshore", "/search/area/jerseyshore")]
STATIC_CAP = 270          # the no-JS result list seems to stop near 300; at or above this, split by price
PRICE_BANDS = [(None, 1500), (1501, 2000), (2001, 2300), (2301, 2600), (2601, 2800), (2801, 3000)]
MAX_POST_AGE_DAYS = 14    # older posts are kept but tagged in notes

lib.HOST_DELAY["www.craigslist.org"] = 3.2   # coordinator's limit: at most 1 request every 3 s


class Stop(Exception):
    pass


class Budget:
    def __init__(self, n):
        self.left, self.start = n, lib.now_iso()

    def fetch(self, url, refresh=False):
        if self.left <= 0:
            raise Stop("request budget used up")
        try:
            content, meta = lib.cached_get(url, SOURCE, ext="html", refresh=refresh, retries=1)
        except RuntimeError as e:   # lib raises on 429/5xx: treat as a wall, do not retry
            raise Stop(f"stopped: {e}")
        if meta["retrieved_at"] >= self.start:
            self.left -= 1
        if meta["status"] in (403, 429):
            raise Stop(f"HTTP {meta['status']} at {url}: stopping, not working around it")
        text = content.decode("utf-8", "replace")
        if meta["status"] == 200 and re.search(r"captcha|request has been blocked", text[:5000], re.I):
            raise Stop(f"block or CAPTCHA page at {url}")
        return text, meta


# ---------- parsing ----------

def parse_search(s: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r'<a href="(https://www\.craigslist\.org/view/d/[^"]+)"', s)))


def _txt(fragment: str) -> str:
    t = re.sub(r"<br\s*/?>|</p>|</li>|</div>|</h\d>", "\n", fragment, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t\xa0]+", " ", t).strip()


WORDNUM = {"ground": 1, "first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4,
           "fifth": 5, "5th": 5, "sixth": 6, "6th": 6, "seventh": 7, "7th": 7, "eighth": 8, "8th": 8,
           "ninth": 9, "9th": 9, "tenth": 10, "10th": 10}
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


def elevator_from(text: str) -> str:
    t = text.lower()
    if re.search(r"\b(no|without|non)[- ]elevator|\bwalk[- ]?up\b|\bno lift\b", t):
        return "no"
    if re.search(r"\belevators?\b|\belev\.? (bldg|building)", t):
        return "yes"
    return "unknown"


def floor_from(text: str) -> str:
    t = text.lower()
    m = re.search(r"\bfloor\s*[:#]\s*(\d{1,2})\b", t)
    if m:
        return m.group(1)
    if re.search(r"\bbasement (apartment|apt|unit|studio)\b|\b(apartment|apt|unit|studio) in (the )?basement\b", t):
        return "0"
    m = re.search(r"\b(\d{1,2}(?:st|nd|rd|th)|ground|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)"
                  r"[- ]fl(?:oo)?r?\b(?! plan)", t)
    if m:
        w = m.group(1)
        return str(WORDNUM.get(w) or int(re.match(r"\d+", w).group(0)))
    return ""


def parse_post(s: str, url: str, fetched_at: str, raw_path: str) -> dict | None:
    r = dict.fromkeys(COLS, "")
    notes = []
    m = re.search(r"post id: (\d+)", s)
    pm = re.search(r'<span class="price">\$([\d,]+(?:\.\d+)?)</span>', s)
    if not m or not pm:
        return None   # removed, expired or not a normal posting
    r.update(listing_id=f"cl_{m.group(1)}", source_site="craigslist", url=url, detail_level="detail",
             first_seen=fetched_at, last_seen=fetched_at, raw_path=raw_path,
             listed_rent=str(int(float(pm.group(1).replace(",", "")))), price_basis="monthly_as_posted")
    title = _txt((re.search(r'id="titletextonly">(.*?)</span>', s, re.S) or [0, ""])[1])
    body = ""
    bm = re.search(r'<section id="postingbody">(.*?)</section>', s, re.S)
    if bm:
        body = _txt(re.sub(r'<div class="print-information.*?</div>\s*</div>', "", bm.group(1), flags=re.S))
    text = title + "\n" + body

    # location
    m = re.search(r'data-latitude="([-\d.]+)" data-longitude="([-\d.]+)"(?: data-accuracy="(\d+)")?', s)
    if m:
        r["lat"], r["lon"] = m.group(1), m.group(2)
        if m.group(3):
            notes.append(f"map_accuracy={m.group(3)}")
    for jm in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', s, re.S):
        try:
            j = json.loads(jm.group(1))
        except ValueError:
            continue
        if isinstance(j, dict) and isinstance(j.get("address"), dict):
            a = j["address"]
            r["address"] = (a.get("streetAddress") or "").strip()
            r["city"], r["state"], r["zip"] = a.get("addressLocality", ""), a.get("addressRegion", ""), a.get("postalCode", "")
    m = re.search(r'class="(?:mapaddress|street-address)"[^>]*>([^<]{3,120})<', s)
    if m and not r["address"] and "google map" not in m.group(1):
        r["address"] = html.unescape(m.group(1)).strip()
    if r["zip"]:
        notes.append("zip_from_craigslist_geo")   # derived by CL from the map pin, not typed by the poster

    # attributes
    attrs = [_txt(a).lower() for a in re.findall(r'<(?:span|div) class="attr[^"]*"[^>]*>(.*?)</(?:span|div)>\s*(?=<(?:span|div) class="attr|</div>)', s, re.S)]
    attrs = [re.sub(r"\s+", " ", a) for a in attrs if a]
    at = " | ".join(attrs)
    m = re.search(r"(\d+)\s*br\s*/\s*([\d.]+|shared|split)\s*ba", at)
    if m:
        r["beds"] = m.group(1)
        r["baths"] = m.group(2) if re.match(r"[\d.]+$", m.group(2)) else ""
    m = re.search(r"(\d{3,5})\s*ft", at)
    if m:
        r["sqft"] = m.group(1)
    m = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', s)
    am = re.search(r"available (now|[a-z]{3} \d{1,2})", at)
    if am:
        r["available_date_text"] = "available " + am.group(1)
    if m:
        r["available_date"] = m.group(1)
    elif am and am.group(1) == "now":
        r["available_date"] = "now"
    if r["available_date"] and r["available_date"] != "now" and r["available_date"] <= fetched_at[:10]:
        r["available_date"] = "now"
    r["dogs"] = "yes" if "dogs are ok" in at else "unknown"
    pol = ["dogs are OK (craigslist attribute)"] if r["dogs"] == "yes" else []
    for m in re.finditer(r"[^.\n]*\b(dogs?|pets?|breed)\b[^.\n]*", body, re.I):
        pol.append(m.group(0).strip()[:160])
        if len(pol) >= 3:
            break
    r["dog_policy_text"] = " / ".join(pol)
    if re.search(r"\bno (dogs|pets)\b|\bcats only\b", body, re.I):
        notes.append("body_says_no_dogs_or_pets_conflict_check")
    m = re.search(r"(\d{2,3})\s*(?:lbs?|pounds?)\b", " ".join(pol), re.I)
    if m:
        r["dog_weight_limit_lb"] = m.group(1)
    m = re.search(r"(w/d in unit|w/d hookups|laundry in bldg|laundry on site|no laundry on site)", at)
    r["laundry"] = m.group(1) if m else ""
    m = re.search(r"(carport|attached garage|detached garage|off-street parking|street parking|valet parking|no parking)", at)
    r["parking_type"] = m.group(1) if m else ""
    m = re.search(r"\b(apartment|condo|cottage/cabin|duplex|flat|house|in-law|loft|townhouse|manufactured)\b", at)
    htype = m.group(1) if m else ""
    if htype in ("house", "duplex", "in-law", "townhouse", "cottage/cabin") or re.search(
            r"\b(private|2|two|3|three|multi)[- ]family (house|home)\b|\bprivate (house|home)\b", text, re.I):
        r["listing_type"] = "unit_in_house"
    elif htype == "condo" or re.search(r"\bco-?op\b|\bcondo\b", text, re.I):
        r["listing_type"] = "condo_coop"
    else:
        r["listing_type"] = "unknown"
    if htype:
        notes.append(f"cl_housing_type={htype}")
    m = re.search(r"broker fee details: ?([^|]{1,80})", at)
    if m:
        notes.append("broker_fee=" + m.group(1).strip())

    # body-derived gate facts
    r["elevator"] = elevator_from(text)
    r["floor"] = floor_from(text)
    m = re.search(r"\b(\d{1,2})[- ]stor(?:y|ey|ies)\b", text, re.I)
    if m:
        r["building_floors"] = m.group(1)
    util = [u for u, p in (("heat", r"\bheat\b"), ("hot water", r"\bhot water\b"), ("gas", r"\bgas\b"),
                           ("electric", r"\belectric(ity)?\b"), ("water", r"(?<!hot )\bwater\b"))
            if re.search(r"[^.\n]*" + p + r"[^.\n]*\binclud", text, re.I) or re.search(r"includ[^.\n]*" + p, text, re.I)]
    if re.search(r"\ball utilities (are )?includ|utilities included", text, re.I):
        util = ["all utilities"]
    r["utilities_included"] = ";".join(util)
    m = re.search(r"pet (?:rent|fee)[^$\n]{0,25}\$\s?(\d{2,3})", text, re.I)
    if m:
        r["pet_rent"] = m.group(1)
    m = re.search(r"parking[^$\n.]{0,40}\$\s?(\d{2,3})\b", text, re.I)
    if m:
        r["parking_fee"] = m.group(1)
    m = re.search(r"[^.\n]*\b(\d+ months? free|free month|concession|net effective)\b[^.\n]*", text, re.I)
    if m:
        r["concession_text"] = m.group(0).strip()[:200]
        if re.search(r"net effective", m.group(0), re.I):
            notes.append("price_may_be_net_effective")
    m = re.search(r'<time class="date timeago" datetime="([^"]+)"', s)
    if m:
        posted = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S%z")
        age = (datetime.now(timezone.utc) - posted).days
        r["listing_age_days"] = str(age)
        if age > MAX_POST_AGE_DAYS:
            notes.append(f"posted_over_{MAX_POST_AGE_DAYS}d_ago")
    m = re.search(r'<meta property="og:image" content="([^"]+)"', s)
    if m:
        r["photo_url"] = m.group(1)
    if r["beds"] == "" and re.search(r"\bstudio\b", title, re.I):
        r["beds"] = "0"
        notes.append("beds_from_title")
    # in-memory only: fingerprints for the duplicate / scam pass (never written out)
    norm = re.sub(r"[^a-z]+", " ", body.lower()).strip()
    r["_body"] = hashlib.sha1(norm.encode()).hexdigest()[:10] if len(norm) > 80 else ""
    ph = re.search(r"\(?\b(\d{3})\)?[-. ]?(\d{3})[-. ]?(\d{4})\b", body)
    r["_phone"] = hashlib.sha1("".join(ph.groups()).encode()).hexdigest()[:10] if ph else ""
    r["_notes"] = notes
    return r


def flag_pass(rows: list[dict]) -> None:
    """Tag likely duplicates and outlier prices. Nothing is dropped."""
    from collections import Counter
    bc = Counter(r["_body"] for r in rows if r.get("_body"))
    pc = Counter(r["_phone"] for r in rows if r.get("_phone"))
    groups: dict = {}
    for r in rows:
        if r.get("_area") and r["beds"] in ("0", "1"):
            groups.setdefault((r["_area"], r["beds"]), []).append(float(r["listed_rent"]))
    for r in rows:
        n = r["_notes"]
        if r.get("_body") and bc[r["_body"]] >= 3:
            n.append(f"same_text_x{bc[r['_body']]}_dupgroup_{r['_body']}")
        if r.get("_phone") and pc[r["_phone"]] >= 8:
            n.append(f"same_phone_x{pc[r['_phone']]}")
        g = groups.get((r.get("_area"), r["beds"]), [])
        if len(g) >= 8 and float(r["listed_rent"]) < 0.55 * median(g):
            n.append(f"price_far_below_area_median_{int(median(g))}_possible_scam")
        if float(r["listed_rent"]) < 500:
            n.append("price_under_500_placeholder_or_scam")
        r["notes"] = ";".join(dict.fromkeys(n))


# ---------- run ----------

def search_urls(path: str, beds: int, band=(None, 3000)) -> str:
    q = f"cat=apa&max_bedrooms={beds}&max_price={band[1]}&min_bedrooms={beds}&pets_dog=1"
    if band[0]:
        q += f"&min_price={band[0]}"
    return f"{HOST}{path}?{q}"


def write_csv(rows: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows.values():
            w.writerow(r)
    tmp.replace(OUT)


def main(argv):
    if len(argv) >= 3 and argv[0] == "--selftest":
        print("search links:", len(parse_search(Path(argv[1]).read_text())))
        r = parse_post(Path(argv[2]).read_text(), "selftest", lib.now_iso(), argv[2])
        r["_area"] = "t"
        flag_pass([r])
        print({k: v for k, v in r.items() if v and not k.startswith("_")})
        return
    if "--approved-by-will" not in argv:
        sys.exit("Not run: Craigslist's Terms of Use prohibit automated collection. See docs/harvest_notes/"
                 "craigslist.md. Run with --approved-by-will only after Will has decided.")
    budget = Budget(int(argv[argv.index("--max-requests") + 1]) if "--max-requests" in argv else 1400)
    old = {}
    if OUT.exists():
        with open(OUT, newline="") as f:
            old = {r["listing_id"]: r for r in csv.DictReader(f)}
    rows, parsed, log = dict(old), [], []
    try:
        for area, path in AREAS:
            links: dict = {}
            for beds in (0, 1):
                text, _ = budget.fetch(search_urls(path, beds), refresh="--refresh-search" in argv)
                got = parse_search(text)
                if len(got) >= STATIC_CAP:
                    got = []
                    for band in PRICE_BANDS:
                        text, _ = budget.fetch(search_urls(path, beds, band), refresh="--refresh-search" in argv)
                        part = parse_search(text)
                        if len(part) >= STATIC_CAP:
                            log.append(f"{area} beds={beds} band={band} still capped at {len(part)}")
                        got += part
                links.update(dict.fromkeys(got))
            n_ok = 0
            for url in links:
                text, meta = budget.fetch(url)
                if meta["status"] != 200:
                    continue
                r = parse_post(text, url, meta["retrieved_at"], meta["path"])
                if not r or r["beds"] not in ("0", "1") or float(r["listed_rent"]) > 3000:
                    continue
                r["_area"] = area
                r["_notes"].insert(0, f"cl_area={area}")
                parsed.append(r)
                n_ok += 1
                if n_ok % 25 == 0:
                    _merge(rows, old, parsed)
                    write_csv(rows)
            log.append(f"{area}: {len(links)} search links, {n_ok} rows")
            print(log[-1], f"(budget left {budget.left})", flush=True)
    except Stop as e:
        print("STOP:", e)
    _merge(rows, old, parsed)
    write_csv(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


def _merge(rows, old, parsed):
    flag_pass(parsed)
    for r in parsed:
        if r["listing_id"] in old:
            r["first_seen"] = old[r["listing_id"]]["first_seen"]
        rows[r["listing_id"]] = r


if __name__ == "__main__":
    main(sys.argv[1:])
