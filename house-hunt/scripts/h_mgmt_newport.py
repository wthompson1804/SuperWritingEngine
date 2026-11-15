"""Newport Rentals (LeFrak, newportrentals.com), Jersey City high-rises.

The availability page lists every unit in plain HTML (data-* attributes). Rows: studio / 1BR with base rent
<= $3,000; price, date and building amenities are then re-read from each unit's own "residence" page.
"""
from __future__ import annotations

import json
import re
import sys

from h_mgmt_common import OUT_DIR, BotWall, jdump, polite_get, strip_tags, upsert, fill_rates, weight_limit

SRC = "mgmt_newport"
BASE = "https://www.newportrentals.com"
OUT = OUT_DIR / "mgmt_newport.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000


def attr(b: str, k: str) -> str:
    m = re.search(k + r'="([^"]*)"', b)
    return m.group(1) if m else ""


def iso(d: str) -> str:
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def main() -> None:
    stats = {"units_seen": 0, "kept": 0, "errors": []}
    html, m = polite_get(BASE + "/apartments-jersey-city-for-rent/", SRC, refresh=REFRESH)
    rows = []
    for b in re.findall(r'<button class="availabilitylistings__row availabilitylistings__row--unit[^>]+>', html):
        stats["units_seen"] += 1
        base = int(attr(b, "data-base-price") or 0)
        if attr(b, "data-bed") not in ("0", "1") or not base or base > CAP:
            continue
        url = BASE + attr(b, "data-link")
        try:
            d, dm = polite_get(url, SRC, refresh=REFRESH)
        except BotWall as e:
            stats["errors"].append(str(e))
            break
        if dm["status"] != 200:
            stats["errors"].append(f"{dm['status']} {url}")
            continue
        x = strip_tags(d)
        pm = re.search(r"Available:?\s*(Now|\d{1,2}/\d{1,2}/\d{4})\s*\$\s*([\d,]+)\s*/\s*mo\*\s*Base Rent:\s*\$\s*([\d,]+)\s*(.{0,60}?)\s*\{slides\}", x)
        if not pm:
            stats["errors"].append(f"no price block {url}")
            continue
        total, base_d = int(pm.group(2).replace(",", "")), int(pm.group(3).replace(",", ""))
        if base_d > CAP:
            continue
        hm = re.search(r"(Studio|\d Bedrooms?)\s*&bull;\s*([\d.]+) Bathrooms?\s*&bull;\s*([\d,]+) Square Feet\s+(.+?)\s*&bull;\s*(.+?)\s*&bull;\s*([A-Za-z ]+),\s*([A-Z]{2})\s*(\d{5})", x)
        offer = re.search(r"Special Offer:\s*(.{0,140}?)\s+Residence", x)
        am = re.search(r"Amenities\s+(.{20,600}?)\s+Just across the Hudson", x)
        amen = am.group(1) if am else ""
        amen = amen[:len(amen) // 2 + 1] if amen[:40] in amen[40:] else amen  # block is printed twice
        unit = re.search(r"residence-([A-Za-z0-9-]+)/", url).group(1).upper()
        floor = unit[:-2] if unit.isdigit() and len(unit) >= 3 else "unknown"
        pet_txt = "; ".join(s.strip() for s in re.findall(r"(?i)[^.;|]{0,60}\b(?:pets?|dogs?)\b[^.;|]{0,60}", amen))[:300]
        photo = re.search(r'property="og:image" content="([^"]+)"', d)
        rows.append({
            "listing_id": f"newport:{attr(b, 'data-unitid')}", "source_site": "newportrentals.com", "url": url,
            "detail_level": "detail", "first_seen": dm["retrieved_at"], "last_seen": dm["retrieved_at"],
            "building_name": hm.group(4) if hm else "", "address": hm.group(5) if hm else "",
            "city": hm.group(6).strip() if hm else "Jersey City", "state": hm.group(7) if hm else "NJ",
            "zip": hm.group(8) if hm else "", "lat": "", "lon": "", "unit": unit, "beds": attr(b, "data-bed"),
            "baths": hm.group(2) if hm else attr(b, "data-bath"), "sqft": (hm.group(3).replace(",", "") if hm else attr(b, "data-sqft")),
            "listed_rent": base_d,
            "price_basis": f"base rent (net effective where a special applies); total monthly leasing price {total} incl. required fees",
            "concession_text": (offer.group(1) if offer else pm.group(4)).strip(),
            "available_date_text": pm.group(1), "available_date": "now" if pm.group(1) == "Now" else iso(pm.group(1)),
            "dogs": "unknown", "dog_policy_text": pet_txt, "dog_weight_limit_lb": weight_limit(pet_txt),
            "elevator": "yes" if re.search(r"(?i)elevator", amen) else "unknown", "floor": floor, "building_floors": "unknown",
            "parking_type": "; ".join(s.strip() for s in re.findall(r"(?i)[^.;|]{0,40}\bparking\b[^.;|]{0,40}", amen))[:200],
            "parking_fee": "", "pet_rent": "", "other_monthly_fees_json": jdump({"required monthly fees (total - base)": total - base_d}),
            "utilities_included": "", "laundry": "on_site" if re.search(r"(?i)central laundry", amen) else ("in_unit" if re.search(r"(?i)washer", amen) else "unknown"),
            "listing_type": "managed_building", "manager": "LeFrak (Newport Rentals)", "listing_age_days": "",
            "photo_url": photo.group(1) if photo else "", "building_url": BASE + "/jersey-city-apartment-buildings/" + url.split("/")[4] + "/",
            "raw_path": dm["path"],
            "notes": f"floor derived from unit number; page says only 'Pet-friendly' (dogs not named); amenities: {amen[:300]}",
        })
    if rows:
        upsert(OUT, rows)
        stats["kept"] = len(rows)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
