"""Ginsburg Development Companies (gdcrentals.com): Westchester / Rockland river-town buildings.
robots.txt: Crawl-delay 10 (honoured). Community pages list floor-plan cards ("Unit B3", beds, baths, sq ft,
rent, "Available (Now)" / date) in plain HTML. Unit-level leasing is on RentCafe (walled: not fetched), so rows
are floor-plan level. No ZIP on the pages.
"""
from __future__ import annotations

import json
import re
import sys

from h_mgmt_common import OUT_DIR, BotWall, polite_get, strip_tags, upsert, fill_rates, weight_limit, dog_status
from h_mgmt_gardencommunities import snips

SRC = "mgmt_gdc"
BASE = "https://gdcrentals.com"
OUT = OUT_DIR / "mgmt_gdc.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000
SKIP = {"about-gdc", "large-luxury-apartments", "privacy-policy", "qa", "wp-json"}


def main() -> None:
    stats = {"pages": 0, "plans_seen": 0, "kept": 0, "errors": []}
    home, _ = polite_get(BASE + "/", SRC, refresh=REFRESH)
    urls = [u for u in sorted(set(re.findall(r'href="(https://gdcrentals\.com/[a-z0-9-]+/)"', home)))
            if u.rstrip("/").split("/")[-1] not in SKIP]
    for url in urls:
        try:
            html, m = polite_get(url, SRC, refresh=REFRESH)
        except BotWall as e:
            stats["errors"].append(str(e))
            break
        if m["status"] != 200:
            stats["errors"].append(f"{m['status']} {url}")
            continue
        stats["pages"] += 1
        text = strip_tags(html)
        tm = re.search(r"<title>\s*([^<|]+?)\s*(?:-[^<|]*)?\|\s*([A-Za-z .'-]+),\s*([A-Z]{2})", html)
        name = tm.group(1).strip() if tm else url.rstrip("/").split("/")[-1]
        city, state = (tm.group(2).strip(), tm.group(3)) if tm else ("", "NY")
        am = re.search(re.escape(name) + r"\s+(\d[^,]{3,60}),\s*" + re.escape(city) + r",\s*" + state, text) if city else None
        address = am.group(1).strip() if am else ""
        zm = re.search(re.escape(city) + r",\s*" + state + r"\s+(\d{5})\b", text) if city else None
        pet_txt = snips(text, r"(?i)\b(pets?|dogs?|cats?|breed)\b")
        elev_txt = snips(text, r"(?i)elevator|mid-rise|high-rise|stor(y|ies)\b|walk[- ]up|townho", 4)
        park_txt = snips(text, r"(?i)\b(parking|garages?)\b", 3, 50)
        util_txt = snips(text, r"(?i)(heat|hot water|gas|water|electric|utilities)[^.|]{0,30}included|included[^.|]{0,30}(heat|hot water)", 3, 50)
        dogs = "no" if re.search(r"(?i)no (pets|dogs)", pet_txt) else ("yes" if re.search(r"(?i)\bdogs?\b", pet_txt) else "unknown")
        dogs = dog_status(pet_txt)
        elev = "yes" if re.search(r"(?i)\belevators?\b", text) else "unknown"
        laundry = "in_unit" if re.search(r"(?i)washers? (and|&) dryers?|washer/dryer|in-unit laundry", text) else ("on_site" if re.search(r"(?i)laundry", text) else "unknown")
        seen, rows = set(), []
        for b in html.split('<div class="slider-content">')[1:]:
            nm = re.search(r'floor-plan-name">([^<]+)<', b)
            if not nm or nm.group(1) in seen:
                continue
            seen.add(nm.group(1))
            stats["plans_seen"] += 1
            bed = re.search(r'class="beds">\s*Beds?:\s*([\w.]+)', b)
            bath = re.search(r'class="bath">\s*Baths?:\s*([\d.]+)', b)
            sq = re.search(r'class="sqft">\s*([\d,]+)', b)
            rent = re.search(r'rent-price">\s*\$([\d,]+)', b)
            st = re.search(r"class='status-[a-z-]+'>([^<]+)<", b)
            beds = None
            if bed:
                beds = 0 if bed.group(1).lower().startswith(("s", "0")) else (int(float(bed.group(1))) if re.match(r"[\d.]+$", bed.group(1)) else None)
            if beds not in (0, 1) or not rent or int(rent.group(1).replace(",", "")) > CAP:
                continue
            status = st.group(1).strip() if st else ""
            avail = ""
            if re.search(r"(?i)available \(now\)", status):
                avail = "now"
            else:
                dm = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", status)
                if dm:
                    avail = f"{dm.group(3)}-{int(dm.group(1)):02d}-{int(dm.group(2)):02d}"
            img = re.search(r'<img[^>]+src="([^"]+)"', b)
            ids = re.search(r"lightboxDetails\('(\d+)','(\d+)'", b)
            pid = (ids.group(1) + "-" + ids.group(2)) if ids else re.sub(r"[^a-z0-9]+", "-", (name + "-" + nm.group(1)).lower())
            rows.append({
                "listing_id": "gdc:" + pid, "source_site": "gdcrentals.com", "url": url, "detail_level": "detail",
                "first_seen": m["retrieved_at"], "last_seen": m["retrieved_at"], "building_name": name,
                "address": address, "city": city, "state": state, "zip": zm.group(1) if zm else "", "lat": "", "lon": "",
                "unit": "", "beds": beds, "baths": bath.group(1) if bath else "", "sqft": sq.group(1).replace(",", "") if sq else "",
                "listed_rent": int(rent.group(1).replace(",", "")),
                "price_basis": "floor-plan card rent (plan-level, not a numbered unit)", "concession_text": snips(text, r"(?i)months? free|special offer", 2, 80),
                "available_date_text": status, "available_date": avail, "dogs": dogs, "dog_policy_text": pet_txt[:500],
                "dog_weight_limit_lb": weight_limit(pet_txt), "elevator": elev, "floor": "unknown", "building_floors": "unknown",
                "parking_type": park_txt[:300], "parking_fee": "", "pet_rent": "", "other_monthly_fees_json": "",
                "utilities_included": util_txt[:300], "laundry": laundry, "listing_type": "managed_building",
                "manager": "Ginsburg Development Companies (GDC)", "listing_age_days": "", "photo_url": img.group(1) if img else "",
                "building_url": url, "raw_path": m["path"],
                "notes": f"floor plan '{nm.group(1)}'; unit numbers only on RentCafe (not fetched); building-type text: {elev_txt[:250]}; zip not on page",
            })
        if rows:
            upsert(OUT, rows)
            stats["kept"] += len(rows)
        print(f"{name} ({city}): plans {len(seen)}, kept {len(rows)}", flush=True)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
