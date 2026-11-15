"""Evidence batch 1: re-fetch Apartment List property pages (refresh) and dump the listing object."""
import csv, json, sys, time
sys.path.insert(0, "scripts")
import lib, h_apartmentlist as al
lib.DEFAULT_DELAY = 2.5
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_1.csv")))
out = {}
for r in rows:
    for u in dict.fromkeys(x.strip() for x in r["urls"].split("|")):
        if "apartmentlist.com" not in u: continue
        path = u.replace("https://www.apartmentlist.com", "")
        try:
            html, meta = al.fetch(path, refresh=True)
        except al.Blocked as e:
            out[r["addr_key"]] = {"error": str(e), "url": u}; print("BLOCKED", u, e); continue
        L = al.parse_listing(html)
        out[r["addr_key"]] = {"url": u, "status": meta["status"], "retrieved_at": meta["retrieved_at"], "raw_path": meta["path"], "listing": L}
        print(meta["status"], u, "units:", sum(len(fp.get("units") or []) for fp in (L or {}).get("available_units") or []) if L else None, flush=True)
json.dump(out, open("raw/evidence_b1/al_listings.json", "w"))
