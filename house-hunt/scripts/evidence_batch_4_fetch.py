"""Evidence pass, batch 4: re-fetch every listing URL (cache bypassed) and dump a per-URL summary JSON.
Idempotent: re-running refetches and overwrites raw/evidence_b4/live_summary.json."""
import csv, json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
SRC = "evidence_b4"
OUT = lib.RAW / SRC / "live_summary.json"
NEXT_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
last = {}
def get(url):
    host = url.split("/")[2]
    w = last.get(host, 0) + 2.5 - time.time()
    if w > 0: time.sleep(w)
    try:
        c, m = lib.cached_get(url, SRC, ext="html", refresh=True, retries=2, timeout=45)
    except RuntimeError as e:
        last[host] = time.time(); return None, {"status": "error", "err": str(e)[-150:], "retrieved_at": lib.now_iso()}
    last[host] = time.time()
    return c.decode("utf8", "replace"), m
rows = list(csv.DictReader(open(lib.DATA / "reference/evidence_batches/batch_4.csv")))
res = json.loads(OUT.read_text()) if OUT.exists() and "--resume" in sys.argv else {}
for r in rows:
    for u in dict.fromkeys(x.strip() for x in r["urls"].split("|")):
        if u in res: continue
        text, m = get(u)
        s = {"addr_key": r["addr_key"], "status": m.get("status"), "retrieved_at": m.get("retrieved_at"), "path": m.get("path"), "len": len(text or "")}
        if text and "trulia.com" in u:
            mm = NEXT_RE.search(text)
            if mm:
                hd = json.loads(mm.group(1)).get("props", {}).get("homeDetails") or {}
                (lib.RAW / SRC / (re.sub(r"\W+", "_", u[-60:]) + ".hd.json")).write_text(json.dumps(hd))
                s["hd_file"] = re.sub(r"\W+", "_", u[-60:]) + ".hd.json"
                s["status_label"] = hd.get("currentStatus")
                s["price"] = (hd.get("price") or {}).get("price")
                s["avail"] = hd.get("formattedAvailableDate")
                s["addr"] = (hd.get("location") or {}).get("streetAddress")
            else:
                s["note"] = "no __NEXT_DATA__"
        res[u] = s
        OUT.write_text(json.dumps(res, indent=1))
        print(u[-70:], s.get("status"), s.get("len"), s.get("price"), s.get("avail"), (s.get("status_label") or {}).get("label") if isinstance(s.get("status_label"), dict) else s.get("note"))
