"""Evidence batch 7: Zumper building/address pages -> ratings and reviews shown on the page, building facts. Output raw/evidence_b7/zumper_bld.json"""
import sys, re, json, csv
sys.path.insert(0, "scripts")
import ev7_site as f, h_zumper as z
KNOWN = {
 "100 reserve rd|06810": "https://www.zumper.com/apartment-buildings/p1132071/residences-at-the-summit-danbury-ct",
 "50 derby ave|06418": "https://www.zumper.com/apartment-buildings/p866862/franklin-school-lofts-derby-ct",
 "515 w ave|06850": "https://www.zumper.com/apartment-buildings/p13629/the-waypointe-central-norwalk-norwalk-ct",
 "26 belden ave|06850": "https://www.zumper.com/apartment-buildings/p18796/avalon-norwalk-central-norwalk-norwalk-ct",
}
OUT = "raw/evidence_b7/zumper_bld.json"
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_7.csv")))
import os
out = json.load(open(OUT)) if os.path.exists(OUT) else {}
for a in sys.argv[1:]:
    k, u = a.split("=", 1); KNOWN[k] = u; out.pop(k, None)
for r in rows:
    k = r["addr_key"]
    if k in out and out[k].get("status") == 200: continue
    if k in KNOWN: u = KNOWN[k]
    else:
        a = re.sub(r"[#,].*", "", r["address"]).strip().lower()
        for x, y in [("avenue", "ave"), ("street", "st"), ("boulevard", "blvd"), ("road", "rd"), ("drive", "dr"), ("place", "pl"), ("lane", "ln"), ("west ", "w ")]:
            a = a.replace(x, y)
        city = "Milford" if r["city"].startswith("Milford") else r["city"]
        u = "https://www.zumper.com/address/" + re.sub(r"[^a-z0-9]+", "-", f"{a} {city} {r['state']} {r['zip'].zfill(5)} usa".lower()).strip("-")
    m = f.get(u, refresh=True)
    if m.get("status") != 200:
        out[k] = {"url": u, "status": m.get("status"), "why": m.get("why")}; print("FAIL", k, u, m.get("status"), m.get("why")); json.dump(out, open(OUT, "w")); continue
    t = open(m["path"], encoding="utf8", errors="replace").read(); st = z.parse_state(t) or {}
    det = st.get("detail", {}); d = (det.get("entity") or {}).get("data") or {}
    br = ((det.get("buildingReviews") or {}).get("data") or {})
    out[k] = {"url": u, "status": 200, "at": m["retrieved_at"], "path": m["path"], "name": d.get("name") or d.get("address"), "address": d.get("address"), "floors": d.get("floors"), "year_built": d.get("year_built"),
              "pet_policy": d.get("pet_policy"), "parking_data": d.get("parking_data"), "parking": d.get("parking"), "fees": d.get("fees"), "rating": d.get("rating"), "building_rating": d.get("building_rating"),
              "summary": (d.get("supplemental_content") or {}).get("reviews_summary"), "reviews": br, "title": (re.search(r"<title>(.*?)</title>", t) or [None, ""])[1],
              "dkeys": sorted(d.keys())}
    n = sum(len(v.get("reviews") or []) for v in (br.get("sources") or {}).values())
    print("ok", k, "|", out[k]["title"][:60], "| floors", d.get("floors"), "| yr", d.get("year_built"), "| reviews", n, "| summary", bool(out[k]["summary"]), flush=True)
    json.dump(out, open(OUT, "w"))
