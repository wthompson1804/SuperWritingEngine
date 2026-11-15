"""Region pass (building-first) for mid_hudson: Putnam, Dutchess, Orange, southern Ulster.

Manual page-by-page collection helper. Subcommands:
  fetch URL [regex]     polite, robots-checked, cached fetch (raw/region_mid_hudson/); prints status, raw path,
                        retrieved_at and text snippets around gate keywords (or the given regex)
  text URL              same fetch; prints the whole stripped text (use with head/cut)
  unit k=v ...          upsert one unit/building row into data/listings_raw/region_mid_hudson.csv
  bldg k=v ...          upsert one building into data/reference/region_buildings_mid_hudson.csv (key: name+address)
  geo "address"         Census geocoder -> lat lon zip
Idempotent: rows are keyed (listing_id / name|address), re-running updates them.
"""
import csv, hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
import h_mgmt_common as C

SRC = "region_mid_hudson"
OUT = C.OUT_DIR / "region_mid_hudson.csv"
BOUT = lib.ROOT / "data" / "reference" / "region_buildings_mid_hudson.csv"
BCOLS = "name,address,town,url,floors,elevator,dogs,weight_limit,verdict,source_url,notes".split(",")
KEY = r"(?i)elevator|walk-?up|stor(y|ies)|floors?\b|\bdogs?\b|\bpets?\b|breed|\blbs?\b|pound|parking|garage|\$\s?\d[\d,]{2,}|availab|studio|1 bed|one bed"


def fetch(url):
    """polite_get plus a cross-process throttle (each CLI call is a new process): >= 2.5 s or Crawl-delay per host."""
    import time
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    st = lib.RAW / SRC / "_last_hit.json"
    st.parent.mkdir(parents=True, exist_ok=True)
    hits = json.loads(st.read_text()) if st.exists() else {}
    try:
        cd = C.crawl_delay(host, SRC)
    except Exception:
        cd = 0
    wait = hits.get(host, 0) + max(2.5, cd) - time.time()
    if wait > 0:
        time.sleep(wait)
    try:
        return C.polite_get(url, SRC)
    finally:
        hits[host] = time.time()
        st.write_text(json.dumps(hits))


def snippets(text, pat, width=110, cap=60):
    out, last = [], -10**9
    for mm in re.finditer(pat, text):
        if mm.start() - last < width:
            continue
        last = mm.start()
        out.append(text[max(0, mm.start() - width): mm.end() + width].strip())
        if len(out) >= cap:
            break
    return out


def geo(addr):
    j, m = lib.get_json("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress", "census_geocoder",
                        params={"address": addr, "benchmark": "Public_AR_Current", "format": "json"})
    ms = j["result"]["addressMatches"]
    if not ms:
        return None
    a = ms[0]
    return a["coordinates"]["y"], a["coordinates"]["x"], a["addressComponents"].get("zip", ""), a["matchedAddress"]


def kv(args):
    d = {}
    for a in args:
        k, v = a.split("=", 1)
        d[k] = v
    return d


def bldg_upsert(d):
    old = {}
    if BOUT.exists():
        with open(BOUT, newline="") as f:
            for r in csv.DictReader(f):
                old[(r["name"], r["address"])] = r
    old[(d.get("name", ""), d.get("address", ""))] = {k: d.get(k, "") for k in BCOLS}
    with open(BOUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BCOLS)
        w.writeheader()
        for r in old.values():
            w.writerow(r)
    return len(old)


def main():
    cmd = sys.argv[1]
    if cmd in ("fetch", "text"):
        url = sys.argv[2]
        try:
            t, m = fetch(url)
        except C.BotWall as e:
            print("BLOCKED:", e)
            return
        except RuntimeError as e:
            print("FETCH_ERROR:", str(e)[:300])
            return
        print("status", m["status"], "| retrieved", m["retrieved_at"], "| raw", m["path"], "| bytes", len(t))
        tt = re.search(r"(?is)<title[^>]*>(.*?)</title>", t)
        print("title:", tt.group(1).strip()[:150] if tt else "")
        s = C.strip_tags(t)
        if cmd == "text":
            print(s)
            return
        pat = sys.argv[3] if len(sys.argv) > 3 else KEY
        for x in snippets(s, pat):
            print(" -", x)
    elif cmd == "geo":
        print(geo(sys.argv[2]))
    elif cmd == "unit":
        d = kv(sys.argv[2:])
        d.setdefault("source_site", re.sub(r"^www\.", "", re.sub(r"https?://([^/]+).*", r"\1", d["url"])))
        d.setdefault("listing_id", SRC + ":" + hashlib.sha1((d["url"] + "|" + d.get("unit", "") + "|" + d.get("building_name", "") + "|" + d.get("beds", "")).encode()).hexdigest()[:12])
        d.setdefault("first_seen", lib.now_iso())
        d.setdefault("last_seen", d["first_seen"])
        d.setdefault("state", "NY")
        if not d.get("lat") and d.get("address"):
            g = geo(f'{d["address"]}, {d.get("city","")}, NY {d.get("zip","")}')
            if g:
                d["lat"], d["lon"] = g[0], g[1]
                d.setdefault("zip", g[2])
        print("rows:", C.upsert(OUT, [d]), d["listing_id"], d.get("lat"), d.get("lon"))
    elif cmd == "bldg":
        print("buildings:", bldg_upsert(kv(sys.argv[2:])))


if __name__ == "__main__":
    main()
