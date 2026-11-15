"""Connecticut region pass, stage 1: enumerate rental buildings from Apartment List city pages (discovery) and read
every property page (facts: pet policy, elevator amenity, website_url, unit availability). No price filter here, so
buildings that fail on price are still on record. Reuses h_apartmentlist's fetch / parsers and its raw cache.
Output: raw/region_connecticut/al_buildings.jsonl (one JSON per property; rows = studio/1BR units <= $3,000).
Usage: python3 h_region_connecticut_al.py [city-slug ...]
"""
import json, re, sys, csv
import h_apartmentlist as al
import lib

CITIES = ["greenwich", "byram", "cos-cob", "stamford", "darien", "norwalk", "westport", "bridgeport", "stratford", "trumbull",
          "milford-city", "shelton", "derby", "ansonia", "west-haven", "new-haven", "hamden", "east-haven", "orange",
          "danbury", "bethel", "ridgefield", "naugatuck", "waterbury"]
OUT = lib.RAW / "region_connecticut" / "al_buildings.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)

def discover(slug):
    found = {}
    for flt in ("", "c/1-bedroom-apartments-for-rent", "c/studio-apartments-for-rent"):
        page, seen = 1, set()
        while page <= 60:
            path = f"/ct/{slug}" + (f"/{flt}" if flt else "") + (f"/page-{page}" if page > 1 else "")
            html, meta = al.fetch(path)
            if meta["status"] != 200: break
            props, low, tc, _ = al.parse_srp(html)
            new = set(props) - seen
            if not props or not new: break
            seen |= set(props)
            for rid, ps in props.items(): found[ps] = rid
            page += 1
    return found

def main():
    grid_zips = {}
    grid = al.load_grid()
    with open(lib.DATA / "reference" / "search_grid.csv") as f:
        for r in csv.DictReader(f): grid_zips[r["zcta"].zfill(5)] = float(r["drive_min"])
    done = {}
    if OUT.exists():
        for l in open(OUT):
            d = json.loads(l); done[d["slug"]] = d
    cities = sys.argv[1:] or CITIES
    for c in cities:
        try:
            found = discover(c)
        except al.Blocked as e:
            print("BLOCKED discover", c, e); break
        n = 0
        for ps in sorted(found):
            if ps in done: continue
            try:
                html, meta = al.fetch(ps)
            except al.Blocked as e:
                print("BLOCKED", ps, e); return
            if meta["status"] != 200: continue
            L = al.parse_listing(html)
            if not L: continue
            dogs, policy, wl, pet_rent = al.pet_facts(L)
            am = al.amen_names(L, "community_amenities") + al.amen_names(L, "unit_amenities") + al.amen_names(L, "top_amenities")
            try:
                rows, reason = al.build_rows(L, ps, meta, grid_zips, grid)
            except Exception as e:
                rows, reason = [], "err " + str(e)[:80]
            low = [fp.get("price") for fp in (L.get("available_units") or []) if fp.get("bed") in (0, 1) and isinstance(fp.get("price"), (int, float)) and fp.get("price") > 0]
            d = {"slug": ps, "city_page": c, "name": al.txt(L.get("display_name")), "address": al.txt(L.get("street_address") or L.get("street")),
                 "city": al.txt(L.get("city")), "zip": al.txt(L.get("zip"))[:5], "lat": L.get("lat"), "lon": L.get("lon"),
                 "rental_type": al.txt(L.get("rental_type")), "units_count": L.get("total_units_count"), "year_built": L.get("year_built"),
                 "website": al.txt(L.get("website_url")), "pmc": al.txt(L.get("pmc_display_name")), "dogs": dogs, "policy": policy, "wl": wl,
                 "pet_rent": pet_rent, "elevator_amenity": any(a.lower() == "elevator" for a in am),
                 "desc": al.txt(L.get("description"))[:1500], "amenities": sorted(set(am)), "low_0_1": min(low) if low else None,
                 "reason": reason, "seen": meta["retrieved_at"], "raw": meta["path"], "rows": rows}
            done[ps] = d
            with open(OUT, "a") as f: f.write(json.dumps(d) + "\n")
            n += 1
        print(c, "props", len(found), "new", n, flush=True)
main()
