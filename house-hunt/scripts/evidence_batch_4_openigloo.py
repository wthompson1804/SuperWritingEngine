"""Evidence pass, batch 4: fetch Openigloo building pages (matched by BBL via the reviewed-buildings sitemap)."""
import csv, json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
SRC = "openigloo"
urls = []
for i in range(1, 5):
    c, _ = lib.cached_get(f"https://www.openigloo.com/sitemap_buildings__reviewed_00{i}.xml", SRC, ext="xml")
    urls += re.findall(r"<loc>(.*?)</loc>", c.decode())
bybbl = {}
for u in urls:
    m = re.search(r"/nyc/(\d+)-(\d+)/", u)
    if m:
        bybbl.setdefault(m.group(2), []).append(u)
out = {}
for r in csv.DictReader(open(lib.DATA / "reference/evidence_batches/batch_4.csv")):
    bbl = r["pluto_bbl"].split(".")[0]
    for u in bybbl.get(bbl, []):
        out.setdefault(u, {"addr_keys": []})["addr_keys"].append(r["addr_key"])
for u, o in out.items():
    c, m = lib.cached_get(u, SRC, ext="html")
    o.update(status=m["status"], path=m.get("path"), retrieved_at=m["retrieved_at"], len=len(c))
    print(m["status"], len(c), u)
    time.sleep(2.5)
(lib.RAW / SRC / "batch4_pages.json").write_text(json.dumps(out, indent=1))
