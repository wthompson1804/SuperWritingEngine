import csv, re, sys, json
csv.field_size_limit(10**9)
sys.path.insert(0, "scripts")
import ev_b1_fetch as f
b = list(csv.DictReader(open("data/reference/evidence_batches/batch_1.csv")))
tr = list(csv.DictReader(open("data/listings_raw/trulia.csv")))
out = {}
for r in b:
    a = re.match(r"(\d+\s+\S+(?:\s+\S+)?)", r["address"].lower()).group(1)[:12]; z = r["zip"].zfill(5)
    urls = list(dict.fromkeys(x["url"] for x in tr if x["address"].lower().startswith(a) and x["zip"].zfill(5) == z))
    for u in urls[:2]:
        c, m = f.get(u, refresh=True)
        if not c or m["status"] != 200:
            out.setdefault(r["addr_key"], []).append({"url": u, "status": m.get("status"), "why": m.get("why")}); print("FAIL", u, m.get("status")); continue
        mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', c.decode("utf8", "replace"), re.S)
        hd = json.loads(mm.group(1))["props"].get("homeDetails") if mm else None
        out.setdefault(r["addr_key"], []).append({"url": u, "status": 200, "at": m["retrieved_at"], "hd": hd})
        print("ok", u[:90], bool(hd), flush=True)
json.dump(out, open("raw/evidence_b1/trulia_hd.json", "w"))
