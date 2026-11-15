"""Connecticut region pass: read SightMap embeds on building leasing sites (unit number, floor, price, date).
Seeds: SEEDS below (name|site|address|town|zip). Tries the usual availability paths until an embed is found.
Output: raw/region_connecticut/sightmap_units.jsonl (one JSON per building, rewritten each run from cache).
Usage: python3 h_region_connecticut_sm.py [name-substring ...]
"""
import json, re, sys
from h_mgmt_common import polite_get, BotWall
import h_mgmt_sightmap as sm
import lib
SRC = "region_connecticut"
OUT = lib.RAW / SRC / "sightmap_units.jsonl"
PATHS = ["", "/floorplans", "/floor-plans", "/availability", "/sightmap", "/apartments", "/interactive-map", "/site-map"]
SEEDS = [l.split("|") for l in (lib.RAW / SRC / "sm_seeds.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
done = {}
if OUT.exists():
    for l in open(OUT):
        d = json.loads(l); done[d["name"]] = d
for name, site, addr, town, zp in SEEDS:
    if sys.argv[1:] and not any(a.lower() in name.lower() for a in sys.argv[1:]): continue
    if name in done and "--refresh" not in sys.argv: continue
    embed = page = ""
    try:
        for p in PATHS:
            h, m = polite_get(site.rstrip("/") + p, SRC)
            if m["status"] != 200: continue
            e = sm.find_embed(h)
            if e: embed, page = e, site.rstrip("/") + p; break
        if not embed:
            print(name, "no embed"); continue
        us, info = sm.units(embed, SRC)
    except BotWall as e:
        print(name, "BOTWALL", e); continue
    except Exception as e:
        print(name, "ERR", str(e)[:100]); continue
    d = {"name": name, "site": site, "page": page, "embed": embed, "address": addr, "town": town, "zip": zp, "slug": re.sub(r"[^a-z0-9]+", "-", name.lower()),
         "lat": info.get("lat"), "lon": info.get("lon"), "floor_labels": info.get("floor_labels", []), "sm_address": info.get("address"), "units": us}
    done[name] = d
    c = [u for u in us if u["beds"] in (0, 1) and u["price"] and u["price"] <= 3000]
    print(name, page, "units", len(us), "0/1BR<=3000:", len(c), "floors", info.get("floor_labels"), info.get("address"),
          "specials", sorted({u["specials"] for u in us if u["specials"]})[:3], "fees", [u["required_fees"] for u in c[:1]])
with open(OUT, "w") as f:
    for d in done.values(): f.write(json.dumps(d) + "\n")
