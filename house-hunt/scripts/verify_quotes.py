"""Re-read each cached page and confirm every excerpt in data/voices/neighborhood_quotes.csv appears on it verbatim
(whitespace-normalized; HTML tags removed and entities decoded; for Trulia the review strings inside the page's
embedded JSON are decoded). Writes a `verified` column (yes / no:<reason>). `--drop` removes rows that fail.
Usage: python3 scripts/verify_quotes.py [--drop]
"""
import csv, json, re, html, sys, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
Q = ROOT / "data/voices/neighborhood_quotes.csv"

def norm(x): return re.sub(r"\s+", " ", x).strip()
def page_text(raw):
    texts = []
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw, re.S)
    if m:
        try:
            def walk(o):
                if isinstance(o, dict):
                    for v in o.values(): walk(v)
                elif isinstance(o, list):
                    for v in o: walk(v)
                elif isinstance(o, str) and len(o) > 20: texts.append(norm(o))
            walk(json.loads(m.group(1)))
        except Exception: pass
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
    texts.append(norm(html.unescape(re.sub(r"<[^>]+>", " ", body))))
    return texts

index = {}
for idx in glob.glob(str(ROOT / "raw/voices_*/_index.jsonl")):
    for l in open(idx):
        d = json.loads(l)
        if d.get("status") == 200: index[d["url"]] = d["path"]
cache = {}
rows = list(csv.DictReader(open(Q)))
fields = [f for f in rows[0].keys() if f != "verified"] + ["verified"] if rows else []
ok = bad = 0
for r in rows:
    url = r["permalink"].split("#")[0]
    path = index.get(url)
    if not path or not (ROOT / path).exists(): r["verified"] = "no:cached page missing"; bad += 1; continue
    if path not in cache: cache[path] = page_text((ROOT / path).read_text(encoding="utf-8", errors="ignore"))
    ex = norm(r["excerpt"])
    hit = any(ex in t for t in cache[path])
    if hit and "#post" in r["permalink"]:          # forum: the excerpt must sit on the page that carries that post id
        hit = ('id="post%s"' % r["permalink"].split("#post")[1]) in (ROOT / path).read_text(encoding="utf-8", errors="ignore")
    if not r["post_date"]: hit = False
    r["verified"] = "yes" if hit else "no:excerpt not found verbatim on cached page"
    ok += hit; bad += not hit
if "--drop" in sys.argv: rows = [r for r in rows if r["verified"] == "yes"]
with open(Q, "w", newline="") as f:
    w = csv.DictWriter(f, fields); w.writeheader(); w.writerows(rows)
print(f"verified {ok}, failed {bad}, rows written {len(rows)}")
for r in rows:
    if r["verified"] != "yes": print("FAIL", r["hood_id"], r["source_site"], r["excerpt"][:80])
