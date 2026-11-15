"""Evidence batch 1: upsert records into data/evidence/*_batch_1.csv. Reads JSON lines on stdin: {"t": live|confirm|item|fact, ...}.
Idempotent: a record with the same key replaces the old one."""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import lib
D = Path("data/evidence"); D.mkdir(parents=True, exist_ok=True)
SPEC = {
 "live": ("live_check_batch_1.csv", ["addr_key","listing_url","unit","status","price_now","available_now_text","matches_stored","building_site_url","checked_at","notes"], ("addr_key","listing_url","unit")),
 "confirm": ("confirm_batch_1.csv", ["addr_key","fact","value","quote","source_url","status"], ("addr_key","fact","source_url")),
 "item": ("items_batch_1.csv", ["addr_key","building_name","category","item_date","excerpt","source_site","source_url","about","retrieved_at"], ("addr_key","category","excerpt","source_url")),
 "fact": ("facts_batch_1.csv", ["addr_key","fact","value","quote","source_url"], ("addr_key","fact","source_url")),
}
def add(recs):
    by = {}
    for r in recs: by.setdefault(r.pop("t"), []).append(r)
    for t, rs in by.items():
        fn, cols, key = SPEC[t]; p = D / fn
        old = list(csv.DictReader(open(p))) if p.exists() else []
        idx = {tuple(o[k] for k in key): i for i, o in enumerate(old)}
        for r in rs:
            if t == "item": r.setdefault("retrieved_at", lib.now_iso())
            row = {c: str(r.get(c, "")) for c in cols}
            k = tuple(row[c] for c in key)
            if k in idx: old[idx[k]] = row
            else: idx[k] = len(old); old.append(row)
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(old)
        print(fn, len(old))
if __name__ == "__main__":
    add([json.loads(l) for l in sys.stdin if l.strip()])
