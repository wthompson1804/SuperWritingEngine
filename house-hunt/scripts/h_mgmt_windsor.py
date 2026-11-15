"""Windsor Communities (windsorcommunities.com): the few properties inside the search grid (NJ Gold Coast, NYC).

robots.txt has Claude-named groups: "/" allowed; /wp-json/, /search/, /?s= disallowed. Only /properties/<slug>/
and /properties/<slug>/floorplans/ are fetched (plain HTML). The floorplans page embeds the unit list as JSON
(unit_number, floor_label, price, price_with_fees, available_on); the same page has a "Costs Overview" fee table.
"""
from __future__ import annotations

import json
import re
import sys

from h_mgmt_common import OUT_DIR, BotWall, grid, jdump, polite_get, strip_tags, upsert, fill_rates, weight_limit, dog_status
from h_mgmt_gardencommunities import snips

SRC = "mgmt_windsor"
BASE = "https://www.windsorcommunities.com/properties/"
OUT = OUT_DIR / "mgmt_windsor.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000
# Properties whose page title places them in NJ / NYC (checked 2026-11-15 from windsor_properties-sitemap.xml).
SLUGS = ["windsor-at-mariners", "windsor-at-liberty-house", "warren-at-york-by-windsor", "the-ashley", "the-aldyn"]
DEC = json.JSONDecoder()


def main() -> None:
    g = grid()
    stats = {"properties": 0, "units_seen": 0, "kept": 0, "errors": [], "lowest_studio_1br": {}}
    for slug in SLUGS:
        try:
            home, hm = polite_get(BASE + slug + "/", SRC, refresh=REFRESH)
            fp, fm = polite_get(BASE + slug + "/floorplans/", SRC, refresh=REFRESH)
        except BotWall as e:
            stats["errors"].append(str(e))
            break
        if hm["status"] != 200 or fm["status"] != 200:
            stats["errors"].append(f"{hm['status']}/{fm['status']} {slug}")
            continue
        stats["properties"] += 1
        units = {}
        for mm in re.finditer(r'\{"id":"\d+","wp_id":\d+,"engrain_asset_id"', fp):
            try:
                u = DEC.raw_decode(fp[mm.start():])[0]
                units[u["id"]] = u
            except json.JSONDecodeError:
                pass
        text = strip_tags(home)
        ftext = strip_tags(fp)
        tm = re.search(r"<title>\s*([^<|]+)", home)
        name = tm.group(1).strip() if tm else slug
        adm = re.search(r'"streetAddress":\s*"([^"]+)".{0,200}?"addressLocality":\s*"([^"]+)".{0,200}?"addressRegion":\s*"([^"]+)".{0,200}?"postalCode":\s*"(\d{5})', home, re.S)
        if not adm:
            a2 = re.search(r"(?<![\d-])(\d{1,5} [A-Za-z0-9 .'-]{3,40}?),?\s+([A-Z][A-Za-z .'-]{2,25}),\s*(NJ|NY)\s+(\d{5})", text)
            address, city, state, z = (a2.group(1), a2.group(2), a2.group(3), a2.group(4)) if a2 else ("", "", "", "")
        else:
            address, city, state, z = adm.group(1), adm.group(2), adm.group(3), adm.group(4)
        pet_txt = snips(text + " || " + ftext, r"(?i)\b(pets?|dogs?|breed)\b", 6, 110)
        park_txt = snips(text + " || " + ftext, r"(?i)\b(parking|garages?)\b", 4, 90)
        dogs = "no" if re.search(r"(?i)no (pets|dogs)", pet_txt) else ("yes" if re.search(r"(?i)\bdogs?\b", pet_txt) else "unknown")
        dogs = dog_status(pet_txt)
        elev = "yes" if re.search(r"(?i)\belevators?\b", text) else "unknown"
        laundry = "in_unit" if re.search(r"(?i)washers? (and|&) dryers?|washer/dryer|in-(home|unit) (laundry|washer)", text) else "unknown"
        pr = re.search(r"Pet Rent.{0,160}?\$([\d.]+)", ftext)
        pk = re.findall(r"((?:Garage |Reserved |Covered |Unreserved )?Parking[^$]{0,140}?\$[\d.,]+(?:\s*-\s*\$[\d.,]+)?\s*/\s*[A-Za-z ]+?Monthly)", ftext)
        floors = [int(u["floor_label"]) for u in units.values() if str(u.get("floor_label", "")).isdigit()]
        cands = [u["price"] for u in units.values() if str(u.get("bedroom_count")) in ("0", "1") and u.get("price")]
        stats["lowest_studio_1br"][slug] = min(cands) if cands else None
        rows = []
        for u in units.values():
            stats["units_seen"] += 1
            beds = str(u.get("bedroom_count"))
            if beds not in ("0", "1") or u.get("unavailable") or not u.get("price") or u["price"] > CAP or (z and z not in g):
                continue
            avail = "now" if str(u.get("available_on_string", "")).lower() == "now" else (u.get("available_on") or "")
            rows.append({
                "listing_id": f"windsor:{u['id']}", "source_site": "windsorcommunities.com",
                "url": BASE + slug + "/floorplans/" + (u.get("detail_link") or ""), "detail_level": "detail",
                "first_seen": fm["retrieved_at"], "last_seen": fm["retrieved_at"], "building_name": name,
                "address": address, "city": city, "state": state, "zip": z, "lat": "", "lon": "",
                "unit": u.get("unit_number"), "beds": beds, "baths": u.get("bathroom_count"), "sqft": u.get("area"),
                "listed_rent": u["price"],
                "price_basis": f"base rent, {u.get('price_lease_term')}-month term; with required fees {u.get('price_with_fees')}",
                "concession_text": json.dumps(u.get("specials"))[:200] if u.get("specials") else "",
                "available_date_text": f"{u.get('available_on_string')} ({u.get('available_on')})", "available_date": avail,
                "dogs": dogs, "dog_policy_text": pet_txt[:700], "dog_weight_limit_lb": weight_limit(pet_txt),
                "elevator": elev, "floor": u.get("floor_label") or "unknown", "building_floors": "unknown",
                "parking_type": park_txt[:300], "parking_fee": " | ".join(pk)[:300], "pet_rent": pr.group(1) if pr else "",
                "other_monthly_fees_json": jdump({"unit_fees (price_with_fees - price)": u.get("unit_fees")}),
                "utilities_included": "", "laundry": laundry, "listing_type": "managed_building", "manager": "Windsor Communities",
                "listing_age_days": "", "photo_url": "", "building_url": BASE + slug + "/", "raw_path": fm["path"],
                "notes": f"plan {u.get('plan_name')}; highest floor among listed units: {max(floors) if floors else 'n/a'}",
            })
        if rows:
            upsert(OUT, rows)
            stats["kept"] += len(rows)
        print(f"{name}: units {len(units)}, kept {len(rows)}", flush=True)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
