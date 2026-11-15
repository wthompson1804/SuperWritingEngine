"""Region pass (westchester_rockland): building enumeration through Zumper town pages (discovery only).

/apartments-for-rent/<town>-ny is robots-allowed (see h_zumper.py). One page per town, 2.5 s apart, stops at a block.
Writes raw/region_westchester_rockland/zumper_town_buildings.json: {building_path: {name, address, city, zip,
min_price, max_price, beds, tags, town_page, seen_at}} for listables that are buildings (have a pb_id).
Prices here are search-card values and are used only to decide which building pages to read.
"""
import json, re, sys
import lib
import h_zumper as hz
SRC = "region_westchester_rockland"
lib.HOST_DELAY["www.zumper.com"] = 2.5
TOWNS = ["mount-vernon", "pelham", "new-rochelle", "yonkers", "bronxville", "tuckahoe", "eastchester", "scarsdale", "hartsdale", "white-plains",
         "harrison", "mamaroneck", "larchmont", "rye", "port-chester", "tarrytown", "sleepy-hollow", "dobbs-ferry", "hastings-on-hudson",
         "irvington", "elmsford", "ossining", "croton-on-hudson", "peekskill", "mount-kisco", "pleasantville", "nyack", "piermont",
         "pearl-river", "nanuet", "spring-valley", "suffern", "haverstraw", "west-haverstraw", "orangeburg", "nyack", "new-city"]
OUT = lib.RAW / SRC / "zumper_town_buildings.json"
found = json.loads(OUT.read_text()) if OUT.exists() else {}
for t in TOWNS:
    path = f"/apartments-for-rent/{t}-ny"
    try:
        c, m = lib.cached_get(hz.BASE + path, SRC, ext="html", retries=2)
    except RuntimeError as e:
        print("ERR", t, str(e)[-120:]); 
        if "429" in str(e): break
        continue
    if m["status"] in (403, 429): print("BLOCKED", t, m["status"]); break
    st = hz.parse_state(c.decode("utf8", "replace"))
    ls = (((st or {}).get("currentSearch") or {}).get("listables") or {}).get("listables") or []
    n = 0
    for x in ls:
        if not x.get("pb_id"): continue
        n += 1
        found[x["url"]] = {"name": x.get("building_name"), "address": x.get("address"), "city": x.get("city"), "zip": x.get("zipcode"), "min_price": x.get("min_price"),
                           "max_price": x.get("max_price"), "min_beds": x.get("min_bedrooms"), "max_beds": x.get("max_bedrooms"), "tags": x.get("building_amenity_tags"),
                           "pets": x.get("pets"), "town_page": hz.BASE + path, "seen_at": m["retrieved_at"]}
    print(t, m["status"], "listables", len(ls), "buildings", n, flush=True)
    OUT.write_text(json.dumps(found, indent=1))
print("buildings", len(found))
