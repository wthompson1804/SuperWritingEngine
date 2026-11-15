"""Suffolk region pass: Apartment List property pages (robots-allowed, cached via h_apartmentlist.fetch) summarised:
pet policy, elevator amenity, specials, fees, studio/1BR units.  usage: h_region_suffolk_al.py /ny/<city>/<slug> ..."""
import json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib, h_apartmentlist as A
OUT = lib.ROOT / "raw" / "region_suffolk" / "al_buildings.jsonl"
def main():
    done = {}
    if OUT.exists():
        for l in OUT.read_text().splitlines():
            o = json.loads(l); done[o["path"]] = o
    g = A.load_grid()
    for p in sys.argv[1:]:
        try:
            html, meta = A.fetch(p)
            time.sleep(2.2)
        except A.Blocked as e:
            print("## BLOCKED", p, e); break
        if meta["status"] != 200:
            print("##", meta["status"], p); done[p] = {"path": p, "status": meta["status"]}; continue
        L = A.parse_listing(html)
        if not L:
            print("## no listing JSON", p); done[p] = {"path": p, "status": 200, "nolisting": True}; continue
        dogs, policy, wl, pet_rent = A.pet_facts(L)
        am = A.amen_names(L, "community_amenities") + A.amen_names(L, "unit_amenities") + A.amen_names(L, "top_amenities")
        am = list(dict.fromkeys(am))
        rows, why = A.build_rows(L, p, meta, {z[0]: z[3] for z in g}, g)
        units = [(u.get("bed"), u.get("price"), u.get("name") or u.get("unit_name"), u.get("availability") or u.get("available_on"), u.get("sqft")) for u in (L.get("available_units") or [])]
        desc = A.txt(L.get("description"))
        o = {"path": p, "status": 200, "retrieved_at": meta["retrieved_at"], "raw_path": meta.get("path"), "name": L.get("name") or L.get("display_name"),
             "address": L.get("street_address") or L.get("address"), "city": L.get("city"), "zip": L.get("zip"),
             "lat": L.get("lat"), "lon": L.get("lon"), "dogs": dogs, "policy": policy, "weight": wl, "pet_rent": pet_rent,
             "amenities": am, "specials": L.get("specials"), "desc": desc[:2500], "year_built": L.get("year_built"),
             "stories": L.get("stories") or L.get("num_stories"), "units_n": len(units), "units": units[:80],
             "keys": sorted(L.keys()), "rows": rows, "rows_why": why,
             "fees": L.get("fees") or L.get("fee_details") or L.get("rental_fees")}
        done[p] = o
        print(f"## {o['name']} | {o['address']}, {o['city']} {o['zip']} | dogs={dogs} w={wl} petrent={pet_rent} | yr={o['year_built']} st={o['stories']}")
        print("   policy:", policy[:600])
        print("   amen:", [a for a in am if re.search(r"(?i)elevator|pool|door|concierge|garage|parking|dog|pet|gated|access", a)])
        print("   desc-kw:", [desc[max(0, m.start()-70):m.end()+70] for m in re.finditer(r"(?i)elevator|stor(y|ies)\b|\d+\s?lbs?|pound|breed", desc)][:5])
        print("   specials:", json.dumps(o["specials"])[:500])
        print("   units 0/1BR:", sorted([u for u in units if u[0] in (0, 1)], key=lambda u: u[1] or 0)[:14], "| rows", len(rows), why)
    OUT.write_text("".join(json.dumps(o, ensure_ascii=False, default=str) + "\n" for o in done.values()))
main()
