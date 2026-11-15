"""Evidence batch 2: append rows to the four output CSVs (dedupe on whole row). Import and call add(kind, rows)."""
import csv, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import lib
D = lib.ROOT / "data" / "evidence"; D.mkdir(exist_ok=True)
COLS = {
 "live": "addr_key,listing_url,unit,status,price_now,available_now_text,matches_stored,building_site_url,checked_at,notes",
 "confirm": "addr_key,fact,value,quote,source_url,status",
 "items": "addr_key,building_name,category,item_date,excerpt,source_site,source_url,about,retrieved_at",
 "facts": "addr_key,fact,value,quote,source_url",
}
FILE = {"live": "live_check_batch_2.csv", "confirm": "confirm_batch_2.csv", "items": "items_batch_2.csv", "facts": "facts_batch_2.csv"}
def add(kind, rows):
    cols = COLS[kind].split(","); p = D / FILE[kind]
    old = list(csv.reader(open(p, newline=""))) if p.exists() else [cols]
    have = {tuple(r) for r in old[1:]}
    n = 0
    for r in rows:
        r = tuple("" if x is None else str(x) for x in r)
        assert len(r) == len(cols), (kind, len(r), r)
        if r not in have:
            old.append(list(r)); have.add(r); n += 1
    with open(p, "w", newline="") as f:
        csv.writer(f).writerows(old)
    print(kind, "+", n, "total", len(old) - 1)
