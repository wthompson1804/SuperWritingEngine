"""Evidence batch 9: Zumper building/address pages -> rating sources and review texts. Writes raw/evidence_b9/zumper_bld.json."""
import sys, re, json, csv
sys.path.insert(0, "scripts")
import ev9_fetch as f, h_zumper as z
from lib import cached_get
KNOWN = {
 "11 us hwy 1|08901": "https://www.zumper.com/apartment-buildings/p446109/the-edge-at-raritan-heights-new-brunswick-nj",
 "1 richmond st|08901": "https://www.zumper.com/apartment-buildings/p8642/plaza-square-apartments-new-brunswick-nj",
 "285 george st|08901": "https://www.zumper.com/apartment-buildings/p32449/the-george-new-brunswick-new-brunswick-nj",
 "one chester circle|08901": "https://www.zumper.com/apartment-buildings/p23245/gardens-at-raritan-new-brunswick-nj",
 "1180 raymond blvd|07102": "https://www.zumper.com/apartment-buildings/p10324/eleven80-newark-central-business-district-newark-nj",
 "4828 tonnelle ave|07047": "https://www.zumper.com/apartment-buildings/p599936/solo-at-north-bergen-north-bergen-nj",
 "7711 river rd|07047": "https://www.zumper.com/apartment-buildings/p883493/noble-on-hudson-north-bergen-nj",
 "7000 avalon way|08854": "https://www.zumper.com/apartment-buildings/p311339/avalon-piscataway-piscataway-nj",
 "1222 s ave|07062": "https://www.zumper.com/apartment-buildings/p1644307/centurion-sleepy-hollow-plainfield-nj",
 "2005 quail ridge dr|08536": "https://www.zumper.com/apartment-buildings/p406328/quail-ridge-plainsboro-nj",
 "81 monroe st|07065": "https://www.zumper.com/apartment-buildings/p436332/the-mint-rahway-nj",
}
CITY = {"Parsippany-Troy Hills": "Parsippany", "Dunellen": "Piscataway"}
P = "raw/evidence_b9/zumper_bld.json"
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_9.csv")))
try: out = json.load(open(P))
except Exception: out = {}
for r in rows:
    k = r["addr_key"]
    if k in out and out[k].get("status") == 200: continue
    if k in KNOWN: u = KNOWN[k]
    else:
        a = r["address"].strip().lower()
        for x, y in [("avenue", "ave"), ("street", "st"), ("boulevard", "blvd"), ("road", "rd"), ("drive", "dr"), ("place", "pl"), ("us highway", "us hwy"), ("south ", "s "), ("east ", "e ")]:
            a = a.replace(x, y)
        u = "https://www.zumper.com/address/" + re.sub(r"[^a-z0-9]+", "-", f"{a} {CITY.get(r['city'], r['city'])} {r['state']} {r['zip'].zfill(5)} usa".lower()).strip("-")
    try:
        c, m = cached_get(u, "evidence_b9", ext="html", refresh=True, retries=1)
    except Exception as e:
        out[k] = {"url": u, "status": "ERR", "why": repr(e)[:100]}; print("ERR", k, u); continue
    if m["status"] != 200:
        out[k] = {"url": u, "status": m["status"]}; print("FAIL", k, u, m["status"]); continue
    t = c.decode("utf8", "replace"); st = z.parse_state(t) or {}
    det = st.get("detail", {}); d = (det.get("entity") or {}).get("data") or {}
    br = ((det.get("buildingReviews") or {}).get("data") or {})
    out[k] = {"url": u, "status": 200, "at": m["retrieved_at"], "path": m["path"], "name": d.get("name") or d.get("address"), "address": d.get("address"), "floors": d.get("floors"), "year_built": d.get("year_built"),
              "pet_policy": d.get("pet_policy"), "parking_data": d.get("parking_data"), "fees": d.get("fees"),
              "summary": (d.get("supplemental_content") or {}).get("reviews_summary"), "reviews": br, "title": (re.search(r"<title>(.*?)</title>", t) or [None, ""])[1]}
    srcs = br.get("sources") or {}
    print("ok", k, "|", out[k]["title"][:70], "| floors", d.get("floors"), "| yr", d.get("year_built"), "| src", {s: (v.get("rating"), v.get("review_count") or v.get("count"), len(v.get("reviews") or [])) for s, v in srcs.items()} if isinstance(srcs, dict) else str(srcs)[:200], flush=True)
    json.dump(out, open(P, "w"))
json.dump(out, open(P, "w"))
