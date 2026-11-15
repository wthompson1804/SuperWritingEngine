"""Region pass (connecticut): read the Trulia detail page of every Trulia lead in
data/reference/leads/connecticut.csv (building pages first, then /home/ pages, nearest-first).
Uses h_trulia.fetch / parse_detail (same cache raw/trulia/, same robots notes) with a 3 s delay; never touches
trulia.csv or its state file. Parsed rows go to raw/region_connecticut/trulia_detail.jsonl (one line per
URL: url, at, rows, why). Stops at the first block. Resumable: URLs already in the jsonl are skipped.
"""
import csv, json, sys, time
from pathlib import Path
import h_trulia as T
T.DELAY = 3.0
ROOT = T.ROOT
OUT = ROOT / "raw" / "region_connecticut" / "trulia_detail.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)
done = set()
if OUT.exists():
    for l in OUT.read_text().splitlines():
        done.add(json.loads(l)["url"])
leads = list(csv.DictReader(open(ROOT / "data/reference/leads/connecticut.csv")))
extra = [l.strip() for l in open(sys.argv[1])] if len(sys.argv) > 1 else []
urls = {}
for x in leads:
    for u in (x["building_url"], x["url"]):
        if u.startswith("https://www.trulia.com/building/"):
            d = float(x["drive_min_zip"] or 999)
            pri = (0 if "/building/" in u else 1 if x["dogs"] == "yes" else 2, d)
            if u not in urls or pri < urls[u]: urls[u] = pri
for u in extra: urls.setdefault(u, (0, 0))
todo = [u for u, _ in sorted(urls.items(), key=lambda kv: kv[1]) if u not in done]
print("todo", len(todo), "done", len(done), flush=True)
n = 0
for u in todo:
    try:
        nd, meta = T.fetch(u, 48)
    except T.Blocked as e:
        print("BLOCKED", e, flush=True); break
    if nd is None:
        rec = {"url": u, "at": meta.get("retrieved_at"), "rows": [], "why": f"gone http {meta.get('status')}"}
    else:
        rows, why = T.parse_detail(nd, meta)
        hd = (nd.get("props") or {}).get("homeDetails") or {}
        rec = {"url": u, "at": meta.get("retrieved_at"), "rows": rows, "why": why, "raw_path": meta.get("path"),
               "desc": ((hd.get("description") or {}).get("value") if isinstance(hd.get("description"), dict) else hd.get("description")) or ""}
    with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
    n += 1
    if n % 25 == 0: print(n, "fetched", flush=True)
print("finished", n, flush=True)
