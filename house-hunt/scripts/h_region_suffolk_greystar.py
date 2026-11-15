"""Suffolk region pass: re-read the cached Greystar property pages of the Suffolk communities (plain HTML flight
payload, same parse as h_mgmt_greystar.py) -> raw/region_suffolk/greystar_buildings.jsonl (facts + unit rows)."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
from h_mgmt_common import polite_get, jdump, weight_limit, dog_status
from h_mgmt_greystar import flight, grab, amt, DEC

URLS = """alston-at-station-yards-ronkonkoma-ny/p_22417 the-core-ronkonkoma-ny/p_22418 shoregate-bay-shore-ny/p_20649
new-village-at-patchogue-patchogue-ny/p_22419 revella-on-main-patchogue-ny/p_23705
the-shipyard-at-port-jefferson-harbor-apartments-port-jefferson-ny/p_14839 the-cornerstone-at-hauppauge-hauppauge-ny/p_16285
cornerstone-kings-park-kings-park-ny/p_23536 the-brio-at-the-boulevard-yaphank-ny/p_16953
the-reserve-at-the-boulevard-apartments-yaphank-ny/p_13704 the-vistas-of-port-jefferson-port-jefferson-station-ny/p_18342""".split()
OUT = lib.ROOT / "raw" / "region_suffolk" / "greystar_buildings.jsonl"


def one(url: str) -> dict:
    html, m = polite_get(url, "mgmt_greystar")
    s = flight(html)
    prop = grab(s, "property", '{"id"')
    units = grab(s, "propertyUnits", "[") or []
    loc = prop.get("location", {})
    fps = {str(f["id"]): f for f in prop.get("floorplans") or []}
    about = prop.get("about") or {}
    amen, feats = prop.get("amenities") or [], prop.get("features") or []
    fees = [f for f in (prop.get("fees") or []) if f.get("isEnabled", True)]
    monthly = [f for f in fees if f.get("frequency") == "monthly"]
    petf = [f for f in fees if f.get("category") == "pets" or "pet" in f.get("label", "").lower()]
    park = [f for f in fees if "parking" in (f.get("group") or "") or re.search(r"(?i)parking|garage", f.get("label", ""))]
    req = {f["label"]: amt(f) for f in monthly if f.get("isRequired") and not f.get("isIncluded")}
    incl = [f["label"] for f in monthly if f.get("isIncluded")]
    pet_bits = [x for x in amen + feats if re.search(r"(?i)\b(pet|dog|cat|breed)", x)]
    pet_txt = "; ".join(pet_bits + [f"{f['label']}: {amt(f)} ({f.get('frequency')})" + (f" - {f['disclaimer']}" if f.get("disclaimer") else "") for f in petf])
    blob = " | ".join(amen + feats) + " | " + (about.get("longDescription") or "")
    rmin, rmax = prop.get("requiredMonthlyFeesMin"), prop.get("requiredMonthlyFeesMax")
    us = []
    for u in units:
        fp = fps.get(str(u.get("floorPlanId")), {})
        us.append({"unit": u.get("unitNumber"), "unit_id": u.get("unitId"), "beds": fp.get("bedroomCount"), "baths": fp.get("bathroomCount"),
                   "sqft": u.get("area"), "min_price": u.get("minPrice"), "min_term": u.get("minBaseRentLeaseTerm"),
                   "p12": (u.get("rentMatrix") or {}).get("00-12"), "available": u.get("availableOn"),
                   "floor": u.get("floorShortLabel"), "bldg": u.get("buildingLabel"), "plan": fp.get("name")})
    return {"url": url, "retrieved_at": m["retrieved_at"], "raw_path": m["path"], "id": prop.get("id"), "name": prop.get("name"),
            "address": loc.get("address"), "city": loc.get("city"), "zip": str(loc.get("postalCode") or "")[:5],
            "lat": loc.get("latitude"), "lon": loc.get("longitude"), "building_type": about.get("buildingType"),
            "year_built": about.get("yearBuilt"), "about_keys": sorted(about.keys()),
            "desc": (about.get("longDescription") or "")[:1500], "banner": prop.get("imageBannerText"),
            "specials": prop.get("specials") or prop.get("promotions") or prop.get("concessions"),
            "amenities": amen, "features": feats, "pet_txt": pet_txt, "dogs": dog_status(pet_txt), "weight": weight_limit(pet_txt),
            "elevator": "yes" if re.search(r"(?i)elevator", blob) else "unknown",
            "fees": [{"label": f.get("label"), "amt": amt(f), "freq": f.get("frequency"), "req": f.get("isRequired"), "incl": f.get("isIncluded"),
                      "cat": f.get("category"), "group": f.get("group"), "disc": f.get("disclaimer")} for f in fees],
            "parking_fees": "; ".join(f"{f['label']}: {amt(f)} ({f.get('frequency')})" for f in park),
            "required_min": rmin, "required_max": rmax, "required_items": req, "included": incl,
            "photo": (prop.get("image") or {}).get("url", ""), "prop_keys": sorted(prop.keys()), "units": us}


if __name__ == "__main__":
    with open(OUT, "w") as f:
        for p in URLS:
            try:
                o = one("https://www.greystar.com/" + p)
            except Exception as e:
                print("ERR", p, repr(e)[:200]); continue
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
            small = [u for u in o["units"] if u["beds"] in (0, 1)]
            print(f"\n## {o['name']} | {o['address']}, {o['city']} {o['zip']} | type={o['building_type']} yr={o['year_built']} | elev={o['elevator']} dogs={o['dogs']} w={o['weight']} | req {o['required_min']}-{o['required_max']} {o['required_items']} | incl {o['included']}")
            print("  banner:", o["banner"], "| specials:", str(o["specials"])[:300])
            print("  pets:", o["pet_txt"][:500])
            print("  parking:", o["parking_fees"][:300], "|", [x for x in o["amenities"] + o["features"] if re.search(r"(?i)parking|garage|elevator|pool|doorman|concierge|stor(y|ies)", x)])
            print(f"  units total {len(o['units'])}, studio/1BR {len(small)}:", sorted((u['min_price'], u['beds'], u['unit'], u['floor'], u['available']) for u in small if u['min_price'])[:12])
