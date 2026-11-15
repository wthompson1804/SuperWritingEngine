"""Evidence batch 10: Zumper building/address pages -> rating, reviews shown on page, building facts. raw/evidence_b10/zumper_bld.json"""
import sys, re, json, csv
sys.path.insert(0, "scripts")
import ev10_get as f, h_zumper as z
KNOWN = {
 "35 penataquit ave|11706": "https://www.zumper.com/apartment-buildings/p14215/mid-island-apartments-bay-shore-ny",
 "1710 devonshire rd|11788": "https://www.zumper.com/apartment-buildings/p121272/renaissance-hills-hauppauge-ny",
 "1453 valley rd|07470": "https://www.zumper.com/apartment-buildings/p1281232/avalon-wayne-wayne-nj",
 "10 main st|07095": "https://www.zumper.com/apartment-buildings/p809941/modera-woodbridge-woodbridge-nj",
 "1300 cook ln|07080": "https://www.zumper.com/apartment-buildings/p12675/the-highlands-at-south-plainfield-south-plainfield-nj",
 "10 avalon ct|07764": "https://www.zumper.com/apartment-buildings/p27795/avalon-west-long-branch-west-long-branch-nj",
}
P = "raw/evidence_b10/zumper_bld.json"
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_10.csv")))
import os
out = json.load(open(P)) if os.path.exists(P) else {}
for a in sys.argv[1:]:
    if "=" in a: k, u = a.split("=", 1); KNOWN[k] = u; out.pop(k, None)
for r in rows:
    k = r["addr_key"]
    if k in out and out[k].get("status") == 200: continue
    if k in KNOWN: u = KNOWN[k]
    else:
        a = re.sub(r"[#,].*", "", r["address"]).strip().lower()
        for x, y in [("avenue","ave"),("street","st"),("boulevard","blvd"),("road","rd"),("drive","dr"),("terrace","ter"),("place","pl"),("lane","ln"),("north ","n "),("east ","e "),("west ","w "),("highway","hwy")]: a = a.replace(x, y)
        u = "https://www.zumper.com/address/" + re.sub(r"[^a-z0-9]+", "-", f"{a} {r['city']} {r['state']} {r['zip'].zfill(5)} usa".lower()).strip("-")
    c, m = f.get(u, refresh=True)
    if not c or m["status"] != 200:
        out[k] = {"url": u, "status": m.get("status"), "why": m.get("why")}; print("FAIL", k, u, m.get("status"), m.get("why")); continue
    t = c.decode("utf8", "replace"); st = z.parse_state(t) or {}
    det = st.get("detail", {}); d = (det.get("entity") or {}).get("data") or {}
    brd = (det.get("buildingReviews") or {}).get("data") or {}
    br = brd.get("sources") or {}
    out[k] = {"url": u, "status": 200, "at": m["retrieved_at"], "name": d.get("name") or d.get("address"), "floors": d.get("floors"), "year_built": d.get("year_built"),
              "pet_policy": d.get("pet_policy"), "parking_data": d.get("parking_data"), "parking": d.get("parking"), "fees": d.get("fees"),
              "rating": d.get("rating"), "brd_keys": {kk: vv for kk, vv in brd.items() if kk != "sources"},
              "summary": (d.get("supplemental_content") or {}).get("reviews_summary"), "reviews": br, "title": (re.search(r"<title>(.*?)</title>", t) or [None, ""])[1],
              "address": d.get("address"), "pm": d.get("pm_name") or d.get("brokerage_name"), "floorplans": [(fp.get("name"), fp.get("min_price"), fp.get("bedrooms")) for fp in (d.get("floorplan_listings") or [])][:40]}
    n = sum(len(v.get("reviews") or []) for v in br.values())
    print("ok", k, "|", out[k]["title"][:60], "| floors", d.get("floors"), "| yr", d.get("year_built"), "| reviews", n, "| src", {s: {x: v.get(x) for x in v if x != 'reviews'} for s, v in br.items()}, flush=True)
    json.dump(out, open(P, "w"))
json.dump(out, open(P, "w"))
