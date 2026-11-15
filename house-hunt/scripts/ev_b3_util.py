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
