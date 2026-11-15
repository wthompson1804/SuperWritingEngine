"""Evidence batch 15: Openigloo building pages matched by BBL through the reviewed-buildings sitemaps (cached in raw/openigloo), then
the BBL-keyed fallback URL. Writes raw/evidence_b15/_igloo.json. Robots: Claude groups allow all but /api, /_nuxt, /internal."""
import csv, json, re, sys, time, html as H
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib, requests
lib.HOST_DELAY["www.openigloo.com"] = 2.5
E = lib.RAW / "evidence_b15"
urls = []
for i in range(1, 5):
    c, _ = lib.cached_get(f"https://www.openigloo.com/sitemap_buildings__reviewed_00{i}.xml", "openigloo", ext="xml")
    urls += re.findall(r"<loc>(.*?)</loc>", c.decode())
bybbl = {}
for u in urls:
    m = re.search(r"/nyc/(\d+)-(\d+)/", u)
    if m: bybbl.setdefault(m.group(2), []).append(u)
bbl = {r["addr_key"]: r for r in csv.DictReader(open(lib.DATA / "evidence/nyc_records_match.csv"))}
EXTRA = json.loads((E / "_extra_bbl.json").read_text()) if (E / "_extra_bbl.json").exists() else {}
P = E / "_igloo.json"; out = json.loads(P.read_text()) if P.exists() else {}
def parse(t):
    o = {}
    o["title"] = H.unescape((re.findall(r"<title>(.*?)</title>", t) or [""])[0])
    o["canonical"] = (re.findall(r'rel="canonical" href="([^"]+)"', t) or [""])[0]
    vt = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    vt = H.unescape(re.sub(r"\n\s*\n+", "\n", re.sub(r"<[^>]+>", "\n", vt)))
    o["vt"] = vt
    mm = re.search(r"\n([\d.]+)\n(\d+) reviews?\n", vt); o["rating"], o["n_reviews"] = (mm.group(1), mm.group(2)) if mm else ("", "0")
    revs = []
    for j in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', t, re.S):
        try: d = json.loads(j)
        except Exception: continue
        def walk(x):
            if isinstance(x, dict):
                if x.get("@type") == "Review":
                    revs.append({"date": x.get("datePublished"), "body": x.get("reviewBody"), "name": x.get("name"), "rating": (x.get("reviewRating") or {}).get("ratingValue")})
                if x.get("@type") == "AggregateRating": o["agg"] = {k: v for k, v in x.items() if k != "@type"}
                for v in x.values(): walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        walk(d)
    o["reviews"] = revs
    return o
for r in csv.DictReader(open(lib.DATA / "reference/evidence_batches/batch_15.csv")):
    k = r["addr_key"]
    if r["state"] != "NY" or k in out: continue
    b = (bbl.get(k) or {}).get("bbl") or EXTRA.get(k, "")
    if not b: out[k] = {"error": "no BBL"}; print(k, "no BBL"); continue
    cands = bybbl.get(b) or [f"https://www.openigloo.com/building/nyc/{b}-{b}/x"]
    res = []
    for u in cands[:12]:
        cur = u
        for hop in range(6):
            time.sleep(2.5)
            rr = requests.get(cur, headers={"User-Agent": lib.USER_AGENT}, allow_redirects=False, timeout=60)
            if rr.status_code in (301, 302, 307, 308) and rr.headers.get("location"):
                loc = rr.headers["location"]; cur = "https://www.openigloo.com" + loc if loc.startswith("/") else loc; continue
            break
        if rr.status_code in (403, 429): print("BLOCKED", cur, rr.status_code); P.write_text(json.dumps(out, indent=1)); sys.exit(1)
        o = {"status": rr.status_code, "retrieved_at": lib.now_iso(), "fetched": cur, "in_sitemap": u in urls}
        if rr.status_code == 200:
            fn = E / ("igloo_" + re.sub(r"\W+", "_", cur.split("/nyc/")[-1])[:80] + ".html"); fn.write_bytes(rr.content)
            o["path"] = str(fn.relative_to(lib.ROOT)); o.update(parse(rr.text))
        with open(E / "_index.jsonl", "a") as f: f.write(json.dumps({"url": cur, "status": rr.status_code, "retrieved_at": o["retrieved_at"], "path": o.get("path"), "source": "evidence_b15"}) + "\n")
        res.append(o)
        print(k[:26], "|", o["status"], o.get("title", "")[:60], "|", o.get("rating"), o.get("n_reviews"), len(o.get("reviews", [])), o.get("agg"), flush=True)
    out[k] = {"bbl": b, "n_sitemap": len(bybbl.get(b) or []), "pages": res}
    P.write_text(json.dumps(out, indent=1))
