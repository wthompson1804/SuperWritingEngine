"""Greystar (greystar.com) harvest: NY / NJ / CT property pages from sitemap-pdp.xml.

Finding: the unit table that the browser shows is already in the plain HTML, inside the Next.js flight payload
(self.__next_f.push chunks): `property` (address, buildingType, amenities, fees) and `propertyUnits`
(unitNumber, floorShortLabel, area, availableOn, minPrice, rentMatrix). No /api/ call (robots-disallowed) is made.
Rows: studios and 1BRs with minPrice (lowest base rent over lease terms) <= $3,000.
"""
from __future__ import annotations

import json
import re
import sys

from h_mgmt_common import OUT_DIR, BotWall, grid, jdump, polite_get, upsert, fill_rates, weight_limit, dog_status

SRC = "mgmt_greystar"
OUT = OUT_DIR / "mgmt_greystar.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000
DEC = json.JSONDecoder()


def flight(html: str) -> str:
    chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html)
    out = []
    for c in chunks:
        try:
            out.append(json.loads(c))
        except json.JSONDecodeError:
            pass
    return "".join(out)


def grab(s: str, key: str, opener: str):
    i = s.find(f'"{key}":{opener}')
    if i < 0:
        return None
    try:
        return DEC.raw_decode(s[i + len(key) + 3:])[0]
    except json.JSONDecodeError:
        return None


def amt(f) -> str:
    if f.get("amount") is not None:
        return str(f["amount"])
    if f.get("minAmount") is not None or f.get("maxAmount") is not None:
        return f"{f.get('minAmount')}-{f.get('maxAmount')}"
    return "amount not stated"


def main() -> None:
    g = grid()
    stats = {"pages": 0, "no_data": 0, "out_of_grid": 0, "units_seen": 0, "kept": 0, "props_with_rows": 0, "errors": []}
    sm, _ = polite_get("https://www.greystar.com/sitemap-pdp.xml", SRC, ext="xml", refresh=REFRESH)
    urls = [u for u in re.findall(r"<loc>([^<]+)", sm) if re.search(r"-(ny|nj|ct|pa)/p_\d+$", u)]
    print("property pages:", len(urls), flush=True)
    for url in urls:
        try:
            html, m = polite_get(url, SRC, refresh=REFRESH)
        except BotWall as e:
            stats["errors"].append(str(e))
            break
        except RuntimeError as e:
            stats["errors"].append(str(e)[:150])
            continue
        if m["status"] != 200:
            stats["errors"].append(f"{m['status']} {url}")
            continue
        stats["pages"] += 1
        s = flight(html)
        prop = grab(s, "property", '{"id"')
        if prop is None:
            i = s.find('"property":{"id"')
            prop = DEC.raw_decode(s[i + 11:])[0] if i >= 0 else None
        units = grab(s, "propertyUnits", "[")
        if not prop:
            stats["no_data"] += 1
            continue
        loc = prop.get("location", {})
        z = str(loc.get("postalCode") or "")[:5]
        if z not in g:
            stats["out_of_grid"] += 1
            continue
        if not units:
            continue
        fps = {str(f["id"]): f for f in prop.get("floorplans") or []}
        about = prop.get("about") or {}
        amen = prop.get("amenities") or []
        feats = prop.get("features") or []
        blob = " | ".join(amen + feats) + " | " + (about.get("longDescription") or "")
        fees = [f for f in (prop.get("fees") or []) if f.get("isEnabled", True)]
        monthly = [f for f in fees if f.get("frequency") == "monthly"]
        petf = [f for f in fees if f.get("category") == "pets" or "pet" in f.get("label", "").lower()]
        pet_rent = [f for f in petf if f.get("frequency") == "monthly"]
        park = [f for f in monthly if "parking" in (f.get("group") or "") or "parking" in f.get("label", "").lower() or "garage" in f.get("label", "").lower()]
        req = {}
        for f in monthly:
            if f.get("isRequired") and not f.get("isIncluded"):
                req[f["label"]] = amt(f)
        incl = [f["label"] for f in monthly if f.get("isIncluded")]
        pet_bits = [x for x in amen + feats if re.search(r"(?i)\b(pet|dog|cat|breed)", x)]
        pet_txt = "; ".join(pet_bits + [f"{f['label']}: {amt(f)} ({f.get('frequency')})" + (f" - {f['disclaimer']}" if f.get("disclaimer") else "") for f in petf])
        if re.search(r"(?i)no (pets|dogs)", pet_txt):
            dogs = "no"
        elif re.search(r"(?i)\bdog", pet_txt):
            dogs = "yes"
        else:
            dogs = "unknown"  # "pet" wording only: dogs not named
        dogs = dog_status(pet_txt)
        elev = "yes" if re.search(r"(?i)elevator", blob) else "unknown"
        laundry = "in_unit" if re.search(r"(?i)(in-unit|in-home|in unit|full[- ]size)[^|]{0,25}(washer|laundry)|washer\s*(and|&|/)\s*dryer", blob) else ("on_site" if re.search(r"(?i)laundry", blob) else "unknown")
        floors_seen = [int(u["floorShortLabel"]) for u in units if str(u.get("floorShortLabel", "")).lstrip("-").isdigit()]
        rmin, rmax = prop.get("requiredMonthlyFeesMin"), prop.get("requiredMonthlyFeesMax")
        rows = []
        for u in units:
            stats["units_seen"] += 1
            fp = fps.get(str(u.get("floorPlanId")), {})
            beds = fp.get("bedroomCount")
            price = u.get("minPrice")
            if beds not in (0, 1) or not price or price > CAP:
                continue
            rm = u.get("rentMatrix") or {}
            p12 = rm.get("00-12")
            notes = [f"buildingType={about.get('buildingType')}"]
            if p12:
                notes.append(f"12-month base rent at earliest move-in {p12}")
            if floors_seen:
                notes.append(f"highest floor among available units: {max(floors_seen)}")
            if u.get("buildingLabel"):
                notes.append(f"building {u['buildingLabel']}")
            if prop.get("imageBannerText"):
                notes.append(f"banner: {prop['imageBannerText']}")
            notes.append("site has no pet-policy text; dog weight limit not published")
            rows.append({
                "listing_id": f"greystar:{prop['id']}:{u.get('unitId')}", "source_site": "greystar.com", "url": url,
                "detail_level": "detail", "first_seen": m["retrieved_at"], "last_seen": m["retrieved_at"],
                "building_name": prop.get("name"), "address": loc.get("address"), "city": loc.get("city"),
                "state": loc.get("state"), "zip": z, "lat": loc.get("latitude"), "lon": loc.get("longitude"),
                "unit": u.get("unitNumber"), "beds": beds, "baths": fp.get("bathroomCount"), "sqft": u.get("area"),
                "listed_rent": price,
                "price_basis": f"base rent, lowest over lease terms ({u.get('minBaseRentLeaseTerm')}-month); required monthly fees {rmin}"
                               + (f"-{rmax}" if rmax != rmin else "") + " extra",
                "concession_text": "", "available_date_text": u.get("availableOn"),
                "available_date": u.get("availableOn") or "",
                "dogs": dogs, "dog_policy_text": pet_txt[:600], "dog_weight_limit_lb": weight_limit(pet_txt),
                "elevator": elev, "floor": u.get("floorShortLabel") or "unknown", "building_floors": "unknown",
                "parking_type": "; ".join(x for x in amen + feats if re.search(r"(?i)parking|garage", x))[:300],
                "parking_fee": "; ".join(f"{f['label']}: {amt(f)}" for f in park),
                "pet_rent": "; ".join(amt(f) for f in pet_rent),
                "other_monthly_fees_json": jdump({"required_total_min": rmin, "required_total_max": rmax, "required_items": req}),
                "utilities_included": "; ".join(incl) if incl else ("none listed as included" if fees else ""),
                "laundry": laundry, "listing_type": "managed_building", "manager": "Greystar",
                "listing_age_days": "", "photo_url": (prop.get("image") or {}).get("url", ""), "building_url": url,
                "raw_path": m["path"], "notes": "; ".join(notes),
            })
        if rows:
            n = upsert(OUT, rows)
            stats["kept"] += len(rows)
            stats["props_with_rows"] += 1
            print(f"{prop.get('name')} ({loc.get('city')}): {len(rows)} kept; csv rows {n}", flush=True)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
