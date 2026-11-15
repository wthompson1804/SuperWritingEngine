"""Evidence batch 1: Zumper building/address pages -> reviews shown on the page, building facts."""
import sys, re, json, csv
sys.path.insert(0, "scripts")
import ev_b1_fetch as f, h_zumper as z
KNOWN = {
 "1000 pacific st|06902": "https://www.zumper.com/apartment-buildings/p435779/allure-harbor-point-harbor-point-stamford-ct",
 "1000 w fort lee rd|07603": "https://www.zumper.com/apartment-buildings/p1146135/atwater-bogota-nj",
 "100 river mews ln|07020": "https://www.zumper.com/apartment-buildings/p32606/avalon-at-edgewater-edgewater-nj",
 "100 sterling blvd|07631": "https://www.zumper.com/apartment-buildings/p35261/the-sheffield-englewood-nj",
 "1 avalon way 2154|07005": "https://www.zumper.com/apartment-buildings/p363565/avalon-boonton-boonton-nj",
 "691 anderson ave|07010": "https://www.zumper.com/apartment-buildings/p404587/the-centre-cliffside-park-nj",
 "18 e camden st|07601": "https://www.zumper.com/apartment-buildings/p423034/the-current-on-river-hackensack-nj",
 "127 talmage ave 307 bound brook nj 08805 us|08805": "https://www.zumper.com/apartment-buildings/p1352159/the-view-bound-brook-nj",
 "73 brownstone way|07631": "https://www.zumper.com/apartment-buildings/165047/the-brownstones-at-englewood-south-englewood-nj",
 "140 celia ter|07109": "https://www.zumper.com/apartment-buildings/p21438/belleview-gardens-belleville-nj",
}
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_1.csv")))
out = json.load(open("raw/evidence_b1/zumper_bld.json")) if "--resume" in sys.argv else {}
for r in rows:
    k = r["addr_key"]
    if k in out: continue
    if k in KNOWN: u = KNOWN[k]
    else:
        a = re.sub(r"[#,].*", "", r["address"]).strip().lower()
        a = a.replace("avenue", "ave").replace("street", "st").replace("boulevard", "blvd").replace("road", "rd").replace("drive", "dr").replace("terrace", "ter").replace("place", "pl").replace("lane", "ln").replace("north ", "n ").replace("east ", "e ").replace("west ", "w ")
        if k.startswith("19 e"): a = "19 e 19th st"
        u = "https://www.zumper.com/address/" + re.sub(r"[^a-z0-9]+", "-", f"{a} {r['city']} {r['state']} {r['zip'].zfill(5)} usa".lower()).strip("-")
    c, m = f.get(u, refresh=True)
    if not c or m["status"] != 200:
        out[k] = {"url": u, "status": m.get("status"), "why": m.get("why")}; print("FAIL", k, u, m.get("status"), m.get("why")); continue
    t = c.decode("utf8", "replace"); st = z.parse_state(t) or {}
    det = st.get("detail", {}); d = (det.get("entity") or {}).get("data") or {}
    br = ((det.get("buildingReviews") or {}).get("data") or {}).get("sources") or {}
    out[k] = {"url": u, "status": 200, "at": m["retrieved_at"], "name": d.get("name") or d.get("address"), "floors": d.get("floors"), "year_built": d.get("year_built"),
              "pet_policy": d.get("pet_policy"), "parking_data": d.get("parking_data"), "parking": d.get("parking"), "fees": d.get("fees"),
              "summary": (d.get("supplemental_content") or {}).get("reviews_summary"), "reviews": br, "title": (re.search(r"<title>(.*?)</title>", t) or [None, ""])[1]}
    n = sum(len(v.get("reviews") or []) for v in br.values())
    print("ok", k, "|", out[k]["title"][:60], "| floors", d.get("floors"), "| yr", d.get("year_built"), "| reviews", n, "| summary", bool(out[k]["summary"]), flush=True)
    json.dump(out, open("raw/evidence_b1/zumper_bld.json", "w"))
json.dump(out, open("raw/evidence_b1/zumper_bld.json", "w"))
