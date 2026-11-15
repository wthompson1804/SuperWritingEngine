"""Garden Homes Management (gardenhomesmanagement.com): CT (Fairfield / New Haven / Litchfield) and NY.
/apartments/ lists every available unit in plain HTML (community, unit, bed/bath, sq ft, rent); the community's
own page (/Property?pid=N) is read for pet, parking, utilities and building-type wording.
Mostly low-rise garden buildings: elevator is recorded only when the page says so.
"""
from __future__ import annotations

import json
import re
import sys

from h_mgmt_common import OUT_DIR, BotWall, grid, polite_get, strip_tags, upsert, fill_rates, weight_limit
from h_mgmt_gardencommunities import snips

SRC = "mgmt_gardenhomes"
BASE = "https://gardenhomesmanagement.com"
OUT = OUT_DIR / "mgmt_gardenhomes.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000


def attr(b: str, k: str) -> str:
    m = re.search(k + r'="([^"]*)"', b)
    return m.group(1) if m else ""


def cell(b: str, cls: str) -> str:
    m = re.search(r'<div class="' + cls + r'">(.*?)</div>', b, re.S)
    return strip_tags(m.group(1)).strip() if m else ""


def main() -> None:
    g = grid()
    stats = {"units_seen": 0, "kept": 0, "out_of_grid": 0, "errors": []}
    html, m = polite_get(BASE + "/apartments/", SRC, refresh=REFRESH)
    props = {}
    for w in re.findall(r'<div class="map_listing-wrapper"[^>]+>', html):
        props[attr(w, "data-propname")] = {"street": attr(w, "data-street"), "csz": attr(w, "data-csz"), "pid": attr(w, "data-propid")}
    pcache: dict[str, dict] = {}
    rows = []
    for b in html.split('<div class="rmwb_listing-wrapper"')[1:]:
        stats["units_seen"] += 1
        bb = cell(b, "grid-bed-bath")
        beds = 0 if bb.lower().startswith("studio") else (int(bb.split("/")[0]) if re.match(r"\s*\d+\s*/", bb) else None)
        rent = int(attr(b, "data-rent") or 0)
        if attr(b, "data-unittype") != "Apartment" or beds not in (0, 1) or not rent or rent > CAP:
            continue
        comm = attr(b, "data-community").replace("&amp;", "&")
        p = props.get(comm, {})
        zm = re.search(r"(\d{5})\s*$", p.get("csz", ""))
        z = zm.group(1) if zm else ""
        if z and z not in g:
            stats["out_of_grid"] += 1
            continue
        pm = re.search(r'href="(/Property\?pid=\d+)"', b)
        purl = BASE + pm.group(1) if pm else ""
        if purl and purl not in pcache:
            try:
                ph, pmeta = polite_get(purl, SRC, refresh=REFRESH)
                pt = strip_tags(ph) if pmeta["status"] == 200 else ""
                pt = pt.split("Select Bedrooms")[0] if "Select Bedrooms" in pt else pt
                img = re.search(r'<img[^>]+src="([^"]+(?:jpe?g|png|webp))"[^>]*class="[^"]*(?:slide|gallery|property)', ph or "")
                pcache[purl] = {"text": pt, "path": pmeta.get("path", ""), "img": img.group(1) if img else ""}
            except BotWall as e:
                stats["errors"].append(str(e))
                pcache[purl] = {"text": "", "path": "", "img": ""}
        pt = pcache.get(purl, {}).get("text", "")
        pet_txt = snips(pt, r"(?i)\b(pets?|dogs?|cats?|breed)\b")
        elev_txt = snips(pt, r"(?i)elevator|mid-rise|high-rise|stor(y|ies)\b|walk[- ]up|garden[- ]style|townho", 4)
        park_txt = snips(pt, r"(?i)\b(parking|garages?|carports?)\b", 3, 50)
        util_txt = snips(pt, r"(?i)(heat|hot water|gas|water|electric|utilities)[^.|]{0,30}included|includ(ed|es)[^.|]{0,40}(heat|hot water)", 3, 50)
        if re.search(r"(?i)no (pets|dogs)|pets? (are )?not (allowed|permitted)|dogs? (are )?not (allowed|permitted)", pet_txt):
            dogs = "no"
        elif re.search(r"(?i)dogs? (are )?(welcome|allowed|permitted)|dog[- ]friendly|dog (park|run)", pet_txt):
            dogs = "yes"
        else:
            dogs = "unknown"
        ad = attr(b, "data-availabledate")
        dm = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", ad)
        city_state = re.match(r"(.+?),\s*([A-Z]{2})", p.get("csz", ""))
        unit = cell(b, "grid-unit")
        rows.append({
            "listing_id": f"gardenhomes:{attr(b, 'data-uid')}", "source_site": "gardenhomesmanagement.com",
            "url": BASE + "/apartments/", "detail_level": "detail", "first_seen": m["retrieved_at"], "last_seen": m["retrieved_at"],
            "building_name": comm, "address": p.get("street") or attr(b, "data-street"),
            "city": attr(b, "data-city"), "state": attr(b, "data-state"), "zip": z, "lat": "", "lon": "",
            "unit": unit, "beds": beds, "baths": attr(b, "data-bathrooms"), "sqft": cell(b, "grid-sqfeet"),
            "listed_rent": rent, "price_basis": "unit rent in the company's available-apartments list",
            "concession_text": "", "available_date_text": ad or attr(b, "data-availability") or "listed as available; no date given",
            "available_date": f"{dm.group(3)}-{int(dm.group(1)):02d}-{int(dm.group(2)):02d}" if dm else "",
            "dogs": dogs, "dog_policy_text": pet_txt[:500], "dog_weight_limit_lb": weight_limit(pet_txt),
            "elevator": "yes" if re.search(r"(?i)\belevators?\b", pt) else "unknown", "floor": "unknown", "building_floors": "unknown",
            "parking_type": park_txt[:300], "parking_fee": "", "pet_rent": "", "other_monthly_fees_json": "",
            "utilities_included": util_txt[:300], "laundry": "on_site" if re.search(r"(?i)laundry", pt) else "unknown",
            "listing_type": "managed_building", "manager": "Garden Homes Management", "listing_age_days": "",
            "photo_url": pcache.get(purl, {}).get("img", ""), "building_url": purl, "raw_path": m["path"],
            "notes": f"unit-street text: {attr(b, 'data-street')}; building-type text: {elev_txt[:250]}; community page cached at {pcache.get(purl, {}).get('path', '')}; floor not derivable from unit label",
        })
    if rows:
        upsert(OUT, rows)
        stats["kept"] = len(rows)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
