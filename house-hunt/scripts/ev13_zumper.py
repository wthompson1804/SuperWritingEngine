"""Evidence batch 13: Zumper address/building pages -> rating, reviews shown on page, building facts. raw/evidence_b13/zumper_bld.json
usage: ev13_zumper.py [addr_key=url ...]"""
import sys, re, json, csv, os
sys.path.insert(0, "scripts")
import ev13_site as f, h_zumper as z
KNOWN = {}
P = "raw/evidence_b13/zumper_bld.json"
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_13.csv")))
out = json.load(open(P)) if os.path.exists(P) else {}
for a in sys.argv[1:]:
    if "=" in a: k, u = a.split("=", 1); KNOWN[k] = u; out.pop(k, None)
for r in rows:
    k = r["addr_key"]
    if k in out and out[k].get("status") == 200: continue
    if k in out and k not in KNOWN: continue
    if k in KNOWN: u = KNOWN[k]
    else:
        a = re.sub(r"[#,].*", "", r["address"]).strip().lower()
        for x, y in [("avenue","ave"),("street","st"),("boulevard","blvd"),("road","rd"),("drive","dr"),("terrace","ter"),("place","pl"),("lane","ln"),("north ","n "),("east ","e "),("west ","w "),("highway","hwy")]: a = re.sub(r"\b%s\b" % x.strip(), y.strip(), a)
        u = "https://www.zumper.com/address/" + re.sub(r"[^a-z0-9]+", "-", f"{a} {r['city']} {r['state']} {r['zip'].zfill(5)} usa".lower()).strip("-")
    m = f.get(u, refresh=True)
    if m.get("status") != 200:
        out[k] = {"url": u, "status": m.get("status"), "why": m.get("why")}; print("FAIL", k, u, m.get("status"), m.get("why")); json.dump(out, open(P, "w")); continue
    t = open(m["path"], encoding="utf8", errors="replace").read(); st = z.parse_state(t) or {}
    det = st.get("detail", {}); d = (det.get("entity") or {}).get("data") or {}
    brd = (det.get("buildingReviews") or {}).get("data") or {}
    br = brd.get("sources") or {}
    out[k] = {"url": u, "status": 200, "at": m["retrieved_at"], "name": d.get("name") or d.get("address"), "floors": d.get("floors"), "year_built": d.get("year_built"),
              "pet_policy": d.get("pet_policy"), "parking_data": d.get("parking_data"), "parking": d.get("parking"), "fees": d.get("fees"),
              "rating": d.get("rating"), "brd_keys": {kk: vv for kk, vv in brd.items() if kk != "sources"},
              "summary": (d.get("supplemental_content") or {}).get("reviews_summary"), "reviews": br, "title": (re.search(r"<title>(.*?)</title>", t) or [None, ""])[1],
              "address": d.get("address"), "pm": d.get("pm_name") or d.get("brokerage_name"), "amen": d.get("building_amenities"), "desc": (d.get("description") or "")[:1500],
              "floorplans": [(fp.get("name"), fp.get("min_price"), fp.get("bedrooms")) for fp in (d.get("floorplan_listings") or [])][:40]}
    n = sum(len(v.get("reviews") or []) for v in br.values())
    print("ok", k, "|", out[k]["title"][:60], "| floors", d.get("floors"), "| yr", d.get("year_built"), "| reviews", n, "| src", {s: {x: v.get(x) for x in v if x != 'reviews'} for s, v in br.items()}, flush=True)
    json.dump(out, open(P, "w"))
json.dump(out, open(P, "w"))
