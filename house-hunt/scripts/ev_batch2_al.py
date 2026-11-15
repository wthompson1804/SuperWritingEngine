"""Evidence batch 2: re-fetch Apartment List property pages (refresh) and dump the listing objects."""
import csv, json, sys, time
sys.path.insert(0, "scripts")
import lib, h_apartmentlist as al
OUT = lib.ROOT / "raw" / "evidence_batch2"
OUT.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_2.csv")))
seen = set()
for r in rows:
    u = r["urls"].split(" | ")[0].strip()
    if "apartmentlist.com" not in u or u in seen:
        continue
    seen.add(u)
    slug = u.rsplit("/", 1)[1]
    p = OUT / f"al_{slug}.json"
    if p.exists():
        continue
    time.sleep(2.0)
    try:
        html, meta = al.fetch(u.replace(al.BASE, ""), refresh=True)
    except al.Blocked as e:
        print("BLOCKED", u, e); break
    L = al.parse_listing(html)
    p.write_text(json.dumps({"meta": meta, "listing": L}))
    print(meta["status"], slug, "parsed" if L else "NO LISTING", len(html))
