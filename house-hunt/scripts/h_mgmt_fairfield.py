"""Fairfield Properties (fairfieldproperties.com) harvest. Long Island and Queens.

The site publishes floor-plan "styles" with a "from $X/mo." price per community, each linking to
listing-detail/?lid=N. It publishes no unit numbers and no availability dates, so every row is a floor-plan
style (unit empty, available_date empty) and needs a call to confirm. Community pages state building type
("Elevator", "garden apartments", "two-story") and sometimes pets; both are recorded verbatim.
"""
from __future__ import annotations

import json
import re
import sys

from h_mgmt_common import OUT_DIR, BotWall, grid, polite_get, strip_tags, upsert, fill_rates, weight_limit, dog_status

SRC = "mgmt_fairfield"
BASE = "https://fairfieldproperties.com"
OUT = OUT_DIR / "mgmt_fairfield.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000
STYLE = re.compile(r"<strong>\s*([^<]*?)\s*-\s*from\s*\$([\d,]+)\s*/mo\.?\s*</strong>\s*<a href=\"([^\"]*listing-detail/\?lid=(\d+))\"", re.I)


def beds_of(label: str):
    l = label.lower()
    if "studio" in l or "efficiency" in l:
        return 0
    if re.search(r"\b(one|1)[ -]bed", l) or "junior" in l:
        return 1
    return None


def sentences(text: str, pat: str, n: int = 4) -> str:
    out = []
    for m in re.finditer(pat, text):
        s = text[max(0, m.start() - 90):m.end() + 110].strip()
        if not any(s[:40] in o for o in out):
            out.append(s)
        if len(out) >= n:
            break
    return " | ".join(out)


def main() -> None:
    g = grid()
    stats = {"pages": 0, "communities_with_styles": 0, "styles_seen": 0, "kept": 0, "out_of_grid": 0, "errors": []}
    sm, _ = polite_get(BASE + "/wp-sitemap-posts-page-1.xml", SRC, ext="xml", refresh=REFRESH)
    pages = [u for u in re.findall(r"<loc>([^<]+)", sm) if u.rstrip("/").count("/") == 3]
    for purl in pages:
        try:
            html, cm = polite_get(purl, SRC, refresh=REFRESH)
        except BotWall as e:
            stats["errors"].append(str(e))
            break
        stats["pages"] += 1
        if cm["status"] != 200 or "listing-detail/?lid=" not in html:
            continue
        styles = STYLE.findall(html)
        if not styles:
            continue
        stats["communities_with_styles"] += 1
        text = strip_tags(html)
        # community-specific text only: drop the site-wide menu (lists every community name)
        i = text.find("PROPERTY FEATURES")
        body = text[i:] if i > 0 else text
        body = body.split("Contact Us Fairfield Properties")[0]
        name = re.search(r"<title>\s*([^<|]+?)\s*(?:[|\-–][^<]*)?</title>", html)
        name = name.group(1).strip() if name else purl.rstrip("/").split("/")[-1]
        am = re.search(r"Property Information\s+(?:-->\s*Property Information\s+)?(.{5,120}?),\s*([A-Za-z .'-]+),\s*(NY)\s*,?\s*(\d{5})", text)
        address, city, state, z = (am.group(1).strip(), am.group(2).strip(), am.group(3), am.group(4)) if am else ("", "", "NY", "")
        if z and z not in g:
            stats["out_of_grid"] += 1
            continue
        pet_txt = sentences(body, r"(?i)\b(pets?|dogs?|cats?)\b(?![a-z])")
        elev_txt = sentences(body, r"(?i)elevator|high-rise|mid-rise|garden[- ]style|garden apartment|two[- ]story|2[- ]story|three[- ]story|townhouse|walk[- ]up|ranch[- ]style|second floor|upper|lower", 5)
        if re.search(r"(?i)\belevator", body):
            elev = "yes"
        elif re.search(r"(?i)walk[- ]up|garden[- ]style|garden apartment|townhouse", body):
            elev = "no"
        else:
            elev = "unknown"
        if re.search(r"(?i)no (pets|dogs)|pets? (are )?not (allowed|permitted)", pet_txt):
            dogs = "no"
        elif re.search(r"(?i)dog[- ]friendly|dogs? (are )?(welcome|allowed|permitted)|dog (park|run)", pet_txt):
            dogs = "yes"  # "Pet Friendly" alone does not name dogs: stays unknown, text kept in dog_policy_text
        else:
            dogs = "unknown"
        dogs = dog_status(pet_txt)
        park_txt = sentences(body, r"(?i)\b(parking|garage|carport)s?\b", 3)
        util_txt = sentences(body, r"(?i)\b(heat|hot water|gas|electric|utilities)\b[^.|]{0,40}\bincluded|included[^.|]{0,40}\b(heat|hot water|gas|electric)", 3)
        laundry = "in_unit" if re.search(r"(?i)washer\s*/?\s*(and\s*)?dryer", body) else ("on_site" if re.search(r"(?i)laundry", body) else "unknown")
        photos = [p for p in re.findall(r'<img[^>]+src="([^"]+)"', html) if "logo" not in p.lower() and "webdav" in p]
        rows = []
        for label, price, lurl, lid in styles:
            stats["styles_seen"] += 1
            beds = beds_of(label)
            rent = int(price.replace(",", ""))
            if beds is None or rent > CAP:
                continue
            detail, seen, raw_path, dnote, baths, dprice = "card", cm["retrieved_at"], cm["path"], "", "", rent
            try:
                dh, dm = polite_get(lurl, SRC, refresh=REFRESH)
                if dm["status"] == 200:
                    dt = strip_tags(dh)
                    pm = re.search(r"Prices starting from \$([\d,]+)\s*(.{0,160}?)\s*PROPERTY FEATURES", dt)
                    if pm:
                        dprice = int(pm.group(1).replace(",", ""))
                        dnote = pm.group(2).strip()
                        detail, seen, raw_path = "detail", dm["retrieved_at"], dm["path"]
            except BotWall as e:
                stats["errors"].append(str(e))
                raise
            if dprice > CAP:
                continue
            bm = re.search(r"(?i)(\d(?:\.\d)?|one|two)\s*bath", label + " " + dnote)
            if bm:
                baths = {"one": "1", "two": "2"}.get(bm.group(1).lower(), bm.group(1))
            sq = re.search(r"(?i)([\d,]{3,5})\s*(?:sq\.?\s*ft|square feet)", dnote)
            rows.append({
                "listing_id": f"fairfield:lid{lid}", "source_site": "fairfieldproperties.com", "url": lurl,
                "detail_level": detail, "first_seen": seen, "last_seen": seen, "building_name": name,
                "address": address, "city": city, "state": state, "zip": z, "lat": "", "lon": "",
                "unit": "", "beds": beds, "baths": baths, "sqft": sq.group(1).replace(",", "") if sq else "",
                "listed_rent": dprice, "price_basis": "floor-plan style 'prices starting from' (not a specific unit)",
                "concession_text": "", "available_date_text": "not stated on site", "available_date": "",
                "dogs": dogs, "dog_policy_text": pet_txt, "dog_weight_limit_lb": weight_limit(pet_txt),
                "elevator": elev, "floor": "unknown", "building_floors": "unknown",
                "parking_type": park_txt[:400], "parking_fee": "", "pet_rent": "",
                "other_monthly_fees_json": "", "utilities_included": util_txt[:300], "laundry": laundry,
                "listing_type": "managed_building", "manager": "Fairfield Properties", "listing_age_days": "",
                "photo_url": photos[0].replace(" ", "%20") if photos else "", "building_url": purl, "raw_path": raw_path,
                "notes": f"style: {label}; {dnote}; building-type text: {elev_txt[:300]}; no unit number or availability date published",
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
