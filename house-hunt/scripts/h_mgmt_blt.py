"""Building and Land Technology (bltliveworkplay.com; harborpt.com redirects there). Stamford Harbor Point,
Norwalk, Jersey City. Community page: pet / parking / fee policy ("Know Before You Apply" + FAQ).
Units: the availability page embeds SightMap; see h_mgmt_sightmap.py.
"""
from __future__ import annotations

import json
import re
import sys

from h_mgmt_common import OUT_DIR, BotWall, grid, jdump, polite_get, strip_tags, upsert, fill_rates, weight_limit, dog_status
import h_mgmt_sightmap as sm

SRC = "mgmt_blt"
BASE = "https://bltliveworkplay.com"
OUT = OUT_DIR / "mgmt_blt.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000


def between(text: str, a: str, b: str, maxlen: int = 500) -> str:
    m = re.search(re.escape(a) + r"\s+(.{5," + str(maxlen) + r"}?)\s+" + b, text)
    return m.group(1).strip() if m else ""


def main() -> None:
    g = grid()
    stats = {"communities": 0, "no_embed": [], "units_seen": 0, "kept": 0, "out_of_grid": 0, "errors": []}
    idx, _ = polite_get(BASE + "/apartments/", SRC, refresh=REFRESH)
    urls = sorted(set(re.findall(r'href="(https://bltliveworkplay\.com/apartments/[a-z-]+/[a-z0-9-]+/)"', idx)))
    for url in urls:
        try:
            html, m = polite_get(url, SRC, refresh=REFRESH)
            if m["status"] != 200:
                stats["errors"].append(f"{m['status']} {url}")
                continue
            embed = sm.find_embed(html)
            if not embed:
                ah, am = polite_get(url + "availability/", SRC, refresh=REFRESH)
                embed = sm.find_embed(ah) if am["status"] == 200 else ""
            if not embed:
                stats["no_embed"].append(url)
                continue
            us, info = sm.units(embed, SRC, refresh=REFRESH)
        except BotWall as e:
            stats["errors"].append(str(e))
            break
        stats["communities"] += 1
        text = strip_tags(html)
        name = re.search(r"<title>\s*([^<|:]+)", html)
        title = name.group(1).strip() if name else url
        asset = info.get("asset_name") or ""
        name = title if not asset or asset.lower() in title.lower() else f"{title} ({asset})"
        addr = info.get("address", {})
        z = (addr.get("zip") or "")[:5]
        if z and z not in g:
            stats["out_of_grid"] += 1
            continue
        pets = between(text, "Pets", "Parking")
        parking = between(text, "Parking", "Fees & Deposit")
        feesd = between(text, "Fees & Deposit", "Questions & Answers")
        faq_pet = re.search(r"What are the pet policies and fees\?\s+(?:Is the community pet-friendly\? What are the pet policies and fees\?\s+)?(.{10,500}?)\s+What ", text)
        faq_park = re.search(r"What are the parking options and costs\?\s+(?:What are the parking options and costs\?\s+)?(.{10,400}?)\s+What ", text)
        faq_util = re.search(r"what will I pay for separately\?\s+(?:Are utilities included, and what will I pay for separately\?\s+)?(.{10,500}?)\s+What ", text)
        strip_admin = lambda s: re.sub(r"JetHog Admin \S+\s*", "", s)
        pet_txt = " || ".join(x for x in (pets, strip_admin(faq_pet.group(1)) if faq_pet else "") if x)
        park_txt = " || ".join(x for x in (parking, strip_admin(faq_park.group(1)) if faq_park else "") if x)
        util_txt = strip_admin(faq_util.group(1)) if faq_util else ""
        if re.search(r"(?i)no (pets|dogs)", pet_txt):
            dogs = "no"
        elif re.search(r"(?i)\bdogs?\b", pet_txt):
            dogs = "yes"
        else:
            dogs = "unknown"
        pr = re.search(r"\$(\d+)\s*(?:per month|/month|monthly)?\s*pet rent|pet rent[^$]{0,30}\$(\d+)", pet_txt)
        pet_rent = (pr.group(1) or pr.group(2)) if pr else ""
        pf = re.findall(r"\$(\d+)", park_txt)
        dogs = dog_status(pet_txt)
        elev = "yes" if re.search(r"(?i)elevator", text) else "unknown"
        elev_note = "elevator is mentioned on the community page (amenity, FAQ or on-page resident review text)" if elev == "yes" else "elevator not stated on page"
        nums = [int(x) for x in info.get("floor_labels", []) if str(x).isdigit()]
        laundry = "in_unit" if re.search(r"(?i)in-(unit|home) (washer|laundry)|washer\s*(and|&|/)\s*dryer", text) else "unknown"
        rows = []
        for u in us:
            stats["units_seen"] += 1
            if u["beds"] not in (0, 1) or not u["price"] or u["price"] > CAP:
                continue
            avail = "now" if re.search(r"(?i)now", u["available_text"]) else u["available_on"]
            rows.append({
                "listing_id": f"blt:{u['sightmap_unit_id']}", "source_site": "bltliveworkplay.com (SightMap embed)",
                "url": url + "availability/", "detail_level": "detail", "first_seen": u["seen"], "last_seen": u["seen"],
                "building_name": name, "address": addr.get("street", ""), "city": addr.get("city", ""),
                "state": addr.get("state", ""), "zip": z, "lat": info.get("lat"), "lon": info.get("lon"),
                "unit": u["unit"], "beds": u["beds"], "baths": u["baths"], "sqft": u["sqft"], "listed_rent": u["price"],
                "price_basis": f"unit price shown in SightMap; total with required monthly fees {u['total_min']}"
                               + (f"-{u['total_max']}" if u["total_max"] != u["total_min"] else "") + (f"; {feesd}" if feesd else ""),
                "concession_text": u["specials"], "available_date_text": u["available_text"] or u["available_on"],
                "available_date": avail, "dogs": dogs, "dog_policy_text": pet_txt[:700],
                "dog_weight_limit_lb": weight_limit(pet_txt), "elevator": elev, "floor": u["floor"] or "unknown",
                "building_floors": max(nums) if nums else "unknown", "parking_type": park_txt[:400],
                "parking_fee": "; ".join("$" + x for x in pf), "pet_rent": pet_rent,
                "other_monthly_fees_json": jdump(u["required_fees"]) if u["required_fees"] else "",
                "utilities_included": util_txt[:400], "laundry": laundry, "listing_type": "managed_building",
                "manager": "Building and Land Technology (BLT)", "listing_age_days": "", "photo_url": u["image"],
                "building_url": url, "raw_path": u["raw_path"],
                "notes": "; ".join(x for x in (f"plan {u['plan']}", f"building {u['building']}" if u["building"] else "",
                                               "income-restricted unit" if u["affordable"] else "", elev_note,
                                               "building_floors = highest floor label in SightMap floor list",
                                               f"policy text from {m['path']}") if x),
            })
        if rows:
            n = upsert(OUT, rows)
            stats["kept"] += len(rows)
        print(f"{name}: units {len(us)}, kept {len(rows)}", flush=True)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
