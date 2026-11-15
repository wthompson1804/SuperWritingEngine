"""Garden Communities (gardencommunities.com) harvest. NJ mostly, some NY.

Property pages (from /sitemap.xml) carry floor-plan rows in plain HTML: name, beds, baths, price range,
sq ft, "Available Now" / date. Unit numbers live on *.securecafe.com (RentCafe, bot-walled: not fetched), so
rows are floor-plan level (unit empty). Amenity lists state "Elevators", "Pet-Friendly", "Dog Run", parking.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from datetime import datetime

from h_mgmt_common import OUT_DIR, ROOT, BotWall, polite_get, strip_tags, upsert, fill_rates, weight_limit, dog_status

SRC = "mgmt_gardencommunities"
BASE = "https://www.gardencommunities.com"
OUT = OUT_DIR / "mgmt_gardencommunities.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000


def grid_pts():
    with open(ROOT / "data" / "reference" / "search_grid.csv") as f:
        return [(r["zcta"].zfill(5), float(r["lat"]), float(r["lon"])) for r in csv.DictReader(f)]


def nearest(pts, lat, lon):
    best = (1e9, "")
    for z, a, b in pts:
        d = math.hypot((a - lat) * 111.0, (b - lon) * 111.0 * math.cos(math.radians(lat)))
        if d < best[0]:
            best = (d, z)
    return best


def div(block: str, cls: str) -> str:
    m = re.search(r'<div class="' + cls + r'[^"]*"[^>]*>(.*?)</div>', block, re.S)
    return strip_tags(m.group(1)).strip() if m else ""


def snips(text: str, pat: str, n: int = 4, w: int = 70) -> str:
    out = []
    for m in re.finditer(pat, text):
        s = text[max(0, m.start() - w):m.end() + w].strip()
        if not any(s[:30] in o for o in out):
            out.append(s)
        if len(out) >= n:
            break
    return " | ".join(out)


def main() -> None:
    pts = grid_pts()
    stats = {"pages": 0, "with_plans": 0, "plans_seen": 0, "kept": 0, "out_of_grid": 0, "errors": []}
    sm, _ = polite_get(BASE + "/sitemap.xml", SRC, ext="xml", refresh=REFRESH)
    urls = [u for u in re.findall(r"<loc>([^<]+)", sm) if "/Properties/" in u and not u.endswith("-Apartments.aspx")]
    for url in urls:
        try:
            html, m = polite_get(url, SRC, refresh=REFRESH)
        except BotWall as e:
            stats["errors"].append(str(e))
            break
        except RuntimeError as e:
            stats["errors"].append(str(e)[:120])
            continue
        stats["pages"] += 1
        if m["status"] != 200 or '<div class="unit-details">' not in html:
            continue
        stats["with_plans"] += 1
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        addr = {}
        name = ""
        if ld:
            raw = ld.group(1)
            for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode"):
                mm = re.search(r'"' + k + r'":\s*"([^"]*)"', raw)
                addr[k] = mm.group(1) if mm else ""
            mm = re.search(r'"name":\s*"([^"]*)"', raw)
            name = mm.group(1) if mm else ""
        if not name:
            mm = re.search(r"<title>\s*([^<:|]+)", html)
            name = mm.group(1).strip() if mm else url
        cm = re.search(r"thisCoords\s*=\s*\{lat:\s*([-\d.]+),\s*lng:\s*([-\d.]+)\}", html)
        lat, lon = (float(cm.group(1)), float(cm.group(2))) if cm else (None, None)
        z = addr.get("postalCode", "")[:5]
        text = strip_tags(html)
        if not z:
            mm = re.search(re.escape(addr.get("addressLocality", "~~")) + r",?\s*(?:NJ|NY|New Jersey|New York)\.?\s+(\d{5})\b", text)
            z = mm.group(1) if mm else ""
        note_zip = ""
        if lat is not None:
            dkm, nz = nearest(pts, lat, lon)
            if dkm > 10:
                stats["out_of_grid"] += 1
                continue
            if not z:
                note_zip = f"zip not on page; nearest grid ZCTA centroid {nz} ({dkm:.1f} km)"
        pet_txt = snips(text, r"(?i)\b(pets?|dogs?|cats?|breed)\b")
        elev_txt = snips(text, r"(?i)elevator|mid-rise|high-rise|garden[- ]style|walk[- ]up|townho|stor(y|ies)\b", 4)
        park_txt = snips(text, r"(?i)\b(parking|garages?|carports?)\b", 3, 50)
        util_txt = snips(text, r"(?i)(heat|hot water|gas|water|electric|utilities)[^.|]{0,30}included|included[^.|]{0,30}(heat|hot water)", 3, 50)
        if re.search(r"(?i)no (pets|dogs)|pets? not (allowed|permitted)", pet_txt):
            dogs = "no"
        elif re.search(r"(?i)\bdogs?\b", pet_txt):
            dogs = "yes"
        else:
            dogs = "unknown"  # "pet-friendly" alone does not name dogs
        dogs = dog_status(pet_txt)
        elev = "yes" if re.search(r"(?i)\belevators?\b", text) else "unknown"
        laundry = "in_unit" if re.search(r"(?i)in-suite washer|washers? (and|&) dryers?|washer/dryer", text) else ("on_site" if re.search(r"(?i)laundry", text) else "unknown")
        pm = re.search(r'data-splide-lazy="([^"]+)"', html)
        photo = (BASE + pm.group(1)) if pm and pm.group(1).startswith("/") else (pm.group(1) if pm else "")
        seen_plans, rows = set(), []
        for b in html.split('<div class="unit-details">')[1:]:
            pname = div(b, "unit-name")
            if not pname or pname in seen_plans:
                continue
            seen_plans.add(pname)
            stats["plans_seen"] += 1
            bm = re.search(r'unit-beds[^>]*data-value="([\d.]+)"', b)
            beds = int(float(bm.group(1))) if bm else None
            if beds is None and re.search(r"(?i)studio", pname):
                beds = 0
            price_txt = ""
            pmm = re.search(r'<div class="unit-price[^"]*"[^>]*>\s*<span>(.*?)</span>', re.sub(r"<!--.*?-->", "", b, flags=re.S), re.S)
            if pmm:
                price_txt = strip_tags(pmm.group(1)).strip()
            nums = [int(x.replace(",", "")) for x in re.findall(r"\$([\d,]+)", price_txt)]
            if beds not in (0, 1) or not nums or min(nums) > CAP:
                continue
            avail_txt = div(b, "unit-avail")
            avail = ""
            if re.search(r"(?i)available now|\bnow\b", avail_txt):
                avail = "now"
            else:
                dm = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", avail_txt)
                if dm:
                    y = int(dm.group(3)) + (2000 if len(dm.group(3)) == 2 else 0)
                    avail = f"{y}-{int(dm.group(1)):02d}-{int(dm.group(2)):02d}"
                else:
                    for fmt in ("%B %d, %Y", "%b %d, %Y"):
                        try:
                            avail = datetime.strptime(avail_txt.replace("Available", "").strip(), fmt).date().isoformat()
                        except ValueError:
                            pass
            bath = re.search(r'unit-bath[^>]*data-value="([\d.]+)"', b)
            sq = re.search(r"([\d,]+)\s*sq", div(b, "unit-sqft"))
            apply = re.search(r'href="(https://[^"]*securecafe[^"]*)"', b)
            pid = re.sub(r"[^a-z0-9]+", "-", (url.split("/Properties/")[1].replace(".aspx", "") + "-" + pname).lower()).strip("-")
            rows.append({
                "listing_id": "gardencommunities:" + pid, "source_site": "gardencommunities.com", "url": url,
                "detail_level": "detail", "first_seen": m["retrieved_at"], "last_seen": m["retrieved_at"],
                "building_name": name, "address": addr.get("streetAddress", ""), "city": addr.get("addressLocality", ""),
                "state": addr.get("addressRegion", ""), "zip": z, "lat": lat, "lon": lon,
                "unit": "", "beds": beds, "baths": bath.group(1) if bath else "", "sqft": sq.group(1).replace(",", "") if sq else "",
                "listed_rent": min(nums), "price_basis": f"floor-plan price range '{price_txt}' (low end; not a specific unit)",
                "concession_text": snips(text, r"(?i)month(s)? free|special|concession", 2, 80),
                "available_date_text": avail_txt, "available_date": avail,
                "dogs": dogs, "dog_policy_text": pet_txt[:500], "dog_weight_limit_lb": weight_limit(pet_txt),
                "elevator": elev, "floor": "unknown", "building_floors": "unknown",
                "parking_type": park_txt[:300], "parking_fee": "", "pet_rent": "", "other_monthly_fees_json": "",
                "utilities_included": util_txt[:300], "laundry": laundry, "listing_type": "managed_building",
                "manager": "Garden Communities", "listing_age_days": "", "photo_url": photo, "building_url": url,
                "raw_path": m["path"],
                "notes": "; ".join(x for x in (f"floor plan {pname}", "unit list is on RentCafe (not fetched): " + (apply.group(1) if apply else ""),
                                               "building-type text: " + elev_txt[:250], note_zip) if x),
            })
        if rows:
            n = upsert(OUT, rows)
            stats["kept"] += len(rows)
            print(f"{name}: {len(rows)} kept; csv rows {n}", flush=True)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
