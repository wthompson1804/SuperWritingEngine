"""Evidence batch 8: Zumper building/address pages -> rating sources and review texts. Writes raw/evidence_b8/zumper_bld.json."""
import sys, re, json, csv
sys.path.insert(0, "scripts")
import ev8_fetch as f, h_zumper as z
from lib import cached_get
KNOWN = {
 "740-748 washington ave|07109": "https://www.zumper.com/apartment-buildings/2170986/740-748-washington-ave-llc-belleville-nj",
 "36 washington ave|07008": "https://www.zumper.com/apartment-buildings/1821404/36-washington-avenue-carteret-nj",
 "500 n ave|07027": "https://www.zumper.com/apartment-buildings/p473756/the-lofts-at-garwood-garwood-nj",
 "51 okner pkwy|07039": "https://www.zumper.com/apartment-buildings/p1386101/canterly-place-livingston-nj",
 "2 river rd|07928": "https://www.zumper.com/apartment-buildings/p1014428/the-ivy-chatham-nj",
 "1 avalon way|07005": "https://www.zumper.com/apartment-buildings/p363565/avalon-boonton-boonton-nj",
}
CITY = {}
P = "raw/evidence_b8/zumper_bld.json"
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_8.csv")))
try: out = json.load(open(P))
except Exception: out = {}
for r in rows:
    k = r["addr_key"]
    if k in out and out[k].get("status") == 200: continue
    if k in KNOWN: u = KNOWN[k]
    else:
        a = re.sub(r"[#,].*", "", r["address"]).strip().lower()
        for x, y in [("avenue", "ave"), ("street", "st"), ("boulevard", "blvd"), ("road", "rd"), ("drive", "dr"), ("place", "pl"), ("us highway", "us hwy"), ("south ", "s "), ("east ", "e "), ("north ", "n "), ("lane", "ln"), ("parkway", "pkwy")]:
            a = a.replace(x, y)
        u = "https://www.zumper.com/address/" + re.sub(r"[^a-z0-9]+", "-", f"{a} {CITY.get(r['city'], r['city'])} {r['state']} {r['zip'].zfill(5)} usa".lower()).strip("-")
    try:
        c, m = cached_get(u, "evidence_b8", ext="html", refresh=True, retries=1)
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
