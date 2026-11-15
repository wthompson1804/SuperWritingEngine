"""Evidence batch 3 helpers: latest cached path/meta for a URL from raw/evidence_b3/_index.jsonl."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
def index():
    d = {}
    for l in open(lib.RAW / "evidence_b3" / "_index.jsonl"):
        m = json.loads(l)
        if m.get("status") == 200:
            d[m["url"]] = m
    return d
def page(url):
    m = index()[url]
    return open(lib.ROOT / m["path"], encoding="utf8", errors="ignore").read(), m

import csv
EV = lib.DATA / "evidence"
SCHEMA = {
    "live_check": ["addr_key", "listing_url", "unit", "status", "price_now", "available_now_text", "matches_stored",
                   "building_site_url", "checked_at", "notes"],
    "confirm": ["addr_key", "fact", "value", "quote", "source_url", "status"],
    "items": ["addr_key", "building_name", "category", "item_date", "excerpt", "source_site", "source_url", "about",
              "retrieved_at"],
    "facts": ["addr_key", "fact", "value", "quote", "source_url"],
}
KEYS = {"live_check": ("addr_key", "listing_url", "unit"), "confirm": ("addr_key", "fact", "source_url"),
        "items": ("addr_key", "category", "source_url", "excerpt"), "facts": ("addr_key", "fact", "source_url")}
def put(kind, rows, batch=3):
    """Idempotent upsert into data/evidence/<kind>_batch_<n>.csv (key per KEYS)."""
    p = EV / f"{kind}_batch_{batch}.csv"
    cols = SCHEMA[kind]
    cur = {}
    if p.exists():
        for r in csv.DictReader(open(p, encoding="utf8")):
            cur[tuple(r[k] for k in KEYS[kind])] = r
    for r in rows:
        r = {c: " ".join(str(r.get(c, "")).split()) for c in cols}
        cur[tuple(r[k] for k in KEYS[kind])] = r
    with open(p, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(cur.values())
    return len(cur)
