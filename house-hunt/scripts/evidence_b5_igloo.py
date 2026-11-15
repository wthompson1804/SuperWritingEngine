"""Evidence batch 5: Openigloo building pages by BBL (robots: Claude-User allowed except /api,/_nuxt,/internal). Cached."""
import csv, json, re, sys, html as H
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
lib.HOST_DELAY["www.openigloo.com"] = 2.5
E = lib.RAW / "evidence_b5"
rows = list(csv.DictReader(open(lib.DATA / "reference/evidence_batches/batch_5.csv")))
EXTRA_BBL = json.loads((E / "_extra_bbl.json").read_text()) if (E / "_extra_bbl.json").exists() else {}
out = {}
RES = json.loads((E / "_igloo_resolve.json").read_text()) if (E / "_igloo_resolve.json").exists() else {}
for r in rows:
    if r["zip"] == "10801": continue
    bbl = (r["pluto_bbl"] or "").split(".")[0] or EXTRA_BBL.get(r["addr_key"], "")
    if not bbl:
        out[r["addr_key"]] = {"error": "no BBL"}; continue
    u = EXTRA_BBL.get(r["addr_key"] + "#url") or f"https://www.openigloo.com/building/nyc/{bbl}-{bbl}/x"
    cp = E / ("igloo_" + re.sub(r"\W+", "_", r["addr_key"]) + ".html"); mp = cp.with_suffix(".meta.json")
    if not mp.exists():
        import requests, time
        cur = u; m = None
        for hop in range(6):  # the site 308s between slug spellings; follow by hand, throttled
            time.sleep(2.5)
            rr = requests.get(cur, headers={"User-Agent": lib.USER_AGENT}, allow_redirects=False, timeout=60)
            if rr.status_code in (301, 302, 307, 308) and rr.headers.get("location"):
                cur = "https://www.openigloo.com" + rr.headers["location"] if rr.headers["location"].startswith("/") else rr.headers["location"]
                continue
            break
        m = {"url": cur, "status": rr.status_code, "retrieved_at": lib.now_iso(), "path": str(cp.relative_to(lib.ROOT)), "hops": hop}
        if rr.status_code == 200: cp.write_bytes(rr.content)
        mp.write_text(json.dumps(m))
        with open(E / "_index.jsonl", "a") as f: f.write(json.dumps(m) + "\n")
        if rr.status_code in (403, 429): print("BLOCKED", m); sys.exit(1)
    m = json.loads(mp.read_text()); u = m["url"]
    c = cp.read_bytes() if cp.exists() else b""
    t = c.decode(errors="replace")
    o = {"status": m["status"], "retrieved_at": m["retrieved_at"], "fetched": u}
    if m["status"] == 200:
        o["title"] = H.unescape((re.findall(r"<title>(.*?)</title>", t) or [""])[0])
        o["canonical"] = (re.findall(r'rel="canonical" href="([^"]+)"', t) or [""])[0]
        vt = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
        vt = H.unescape(re.sub(r"\n\s*\n+", "\n", re.sub(r"<[^>]+>", "\n", vt)))
        mm = re.search(r"\n([\d.]+)\n(\d+) reviews?\n", vt); o["rating"], o["n_reviews"] = (mm.group(1), mm.group(2)) if mm else ("", "0")
        mm = re.search(r"Review summary\n.*?\n(.*?)\n", vt, re.S); o["summary"] = mm.group(1).strip() if mm else ""
        mm = re.search(r"About [^\n]+\n(.*?)\n", vt); o["about"] = mm.group(1).strip() if mm else ""
        revs = []
        for j in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', t, re.S):
            try: d = json.loads(j)
            except Exception: continue
            def walk(x):
                if isinstance(x, dict):
                    if x.get("@type") == "Review":
                        revs.append({"date": x.get("datePublished"), "body": x.get("reviewBody"), "name": x.get("name"),
                                     "rating": (x.get("reviewRating") or {}).get("ratingValue")})
                    for v in x.values(): walk(v)
                elif isinstance(x, list):
                    for v in x: walk(v)
            walk(d)
        o["reviews"] = revs
    out[r["addr_key"]] = o
    print(r["addr_key"][:28], "|", o.get("status"), o.get("title", "")[:60], "|", o.get("rating"), o.get("n_reviews"), len(o.get("reviews", [])), flush=True)
(E / "_igloo.json").write_text(json.dumps(out, indent=1))
