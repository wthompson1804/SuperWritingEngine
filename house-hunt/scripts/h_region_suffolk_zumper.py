"""Suffolk region pass: Zumper building / listing pages (robots-allowed paths, cached via h_zumper.fetch) summarised.
usage: h_region_suffolk_zumper.py [-v] /apartment-buildings/p123/slug ..."""
import json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib, h_zumper as Z
OUT = lib.ROOT / "raw" / "region_suffolk" / "zumper_buildings.jsonl"
def main():
    a = sys.argv[1:]; verbose = False
    if a and a[0] == "-v": verbose = True; a = a[1:]
    done = {}
    if OUT.exists():
        for l in OUT.read_text().splitlines():
            o = json.loads(l); done[o["path"]] = o
    for p in a:
        p = p.replace("https://www.zumper.com", "")
        try:
            st, meta, text = Z.fetch(p); time.sleep(2.2)
        except Z.Blocked as e:
            print("## BLOCKED", p, e); break
        except Exception as e:
            print("## ERR", p, repr(e)[:150]); continue
        if meta["status"] != 200 or not st:
            print("##", meta["status"], p, "no state" if not st else ""); continue
        e = ((st.get("detail") or {}).get("entity") or {}).get("data") or {}
        vt = Z.visible_text(text)
        f = Z.facts_from(e, vt, None, "")
        fps = e.get("floorplan_listings") or e.get("floorplans") or []
        units = []
        for u in fps:
            units.append({"id": u.get("listing_id"), "beds": u.get("bedrooms"), "baths": u.get("bathrooms"), "price": u.get("price") or u.get("min_price"),
                          "sqft": u.get("square_feet"), "title": u.get("title"), "avail": u.get("date_available"), "status": u.get("listing_status"),
                          "unit": (u.get("listing_location") or {}).get("unit"), "floor": (u.get("listing_location") or {}).get("floor"), "url": u.get("url")})
        tags = sorted(set((e.get("amenity_tags") or []) + (e.get("building_amenity_tags") or [])))
        o = {"path": p, "retrieved_at": meta["retrieved_at"], "raw_path": meta.get("path"), "name": e.get("name") or e.get("building_name"),
             "address": e.get("address") or e.get("formatted_address"), "city": e.get("city"), "zip": e.get("zipcode"), "lat": e.get("lat"), "lon": e.get("lng"),
             "tags": tags, "facts": {k: v for k, v in f.items()}, "units": units, "min_price": e.get("min_price"), "max_price": e.get("max_price"),
             "floors": e.get("floors") or e.get("num_floors"), "year_built": e.get("year_built"), "keys": sorted(e.keys())[:200]}
        done[p] = o
        print(f"## {o['name']} | {o['address']}, {o['city']} {o['zip']} | {meta['retrieved_at']} | price {o['min_price']}-{o['max_price']} | floors={o['floors']} yr={o['year_built']}")
        print("   dogs:", f.get("dogs"), "w:", f.get("dog_weight_limit_lb"), "| elev:", f.get("elevator"), "| bf:", f.get("building_floors"), "| park:", f.get("parking_type"), "| util:", f.get("utilities_included"))
        print("   policy:", (f.get("dog_policy_text") or "")[:500])
        print("   tags:", tags)
        print("   notes:", f.get("_notes"), "| conc:", f.get("_conc"))
        print("   units:", [(u["beds"], u["price"], u["unit"], u["floor"], u["avail"], u["status"], u["sqft"]) for u in units if u["beds"] in (0, 1)][:20])
        if verbose:
            for m in re.finditer(r"(?i)elevator|stor(y|ies)\b|\d+\s?lbs?\b|pound|special|free", vt):
                print("    ..", vt[max(0, m.start()-100):m.end()+100].replace("\n", " | "))
    OUT.write_text("".join(json.dumps(o, ensure_ascii=False, default=str) + "\n" for o in done.values()))
main()
