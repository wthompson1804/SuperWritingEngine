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
    elif cmd == "zb":  # compact view of a Zumper building/listing page
        try:
            t, m = fetch(sys.argv[2])
        except (C.BotWall, RuntimeError) as e:
            print("BLOCKED/ERR:", str(e)[:200])
            return
        s = C.strip_tags(t)
        print("status", m["status"], "| retrieved", m["retrieved_at"], "| raw", m["path"])
        i = s.find("Updated ")
        print("HEAD:", s[i:i + 420] if i > 0 else s[:300])
        a = s.find("Floor plans", i)
        c = s.find("Building details", a)
        body = s[a:c if c > 0 else a + 6000]
        # keep unit header lines (name, beds, baths, sqft, price), drop the long marketing paragraphs
        units = re.findall(r"((?:[^.]{0,70}?)(?:Studio|\d bed)s? [\d.]+ baths? (?:[\d,]+ sqft )?\$[\d,]+ /mo)", body)
        print("UNITS:", " || ".join(u.strip()[-110:] for u in units)[:2500])
        d = body.find("Amenities for")
        print("AMEN/POLICY:", body[d:][:1800] if d > 0 else body[-1500:])
        end = s.find("Nearby", c if c > 0 else 0)
        for x in snippets(s[i:end if end > 0 else len(s)], r"(?i)\bdogs?\b|\bpets? (policy|rent|fee|deposit)|\blbs?\b|stories|year built|available (now|\w+ \d)|walk-?up", 100, 14):
            if "dogs and cats ok" not in x and "Pet friendly " not in x and "Pet-friendly Ap" not in x:
                print(" -", x)
    elif cmd == "zl":  # compact view of a Zillow building page
        try:
            t, m = fetch(sys.argv[2])
        except (C.BotWall, RuntimeError) as e:
            print("BLOCKED/ERR:", str(e)[:200])
            return
        s = C.strip_tags(t)
        tt = re.search(r"(?is)<title[^>]*>(.*?)</title>", t)
        print("status", m["status"], "| retrieved", m["retrieved_at"], "| raw", m["path"], "|", tt.group(1)[:120] if tt else "")
        a = s.find("Back to search")
        b = s.find("Nearby apartments for rent", a)
        b = b if b > 0 else s.find("What&#x27;s special", a)
        w0 = s.find("What&#x27;s special", a); print("PRICING:", s[a:min(b, w0) if w0 > 0 else b][:1500])
        c = s.find("Facts, features & policies")
        d = s.find("Neighborhood:", c)
        print("FACTS:", s[c:d][:1500])
        w = s.find("What&#x27;s special")
        if w > 0: print("SPECIAL:", s[w:w+1200][-800:])
    elif cmd == "zs":  # Zillow city/zip rentals search page -> buildings and listings (enumeration only)
        try:
            t, m = fetch(sys.argv[2])
        except (C.BotWall, RuntimeError) as e:
            print("BLOCKED/ERR:", str(e)[:200])
            return
        mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
        tt = re.search(r"(?is)<title[^>]*>(.*?)</title>", t)
        print("status", m["status"], m["retrieved_at"], tt.group(1)[:100] if tt else "")
        d = json.loads(mm.group(1)) if mm else {}
        def walk(o):
            if isinstance(o, dict):
                if "detailUrl" in o and ("address" in o or "buildingName" in o):
                    yield o
                for v in o.values():
                    yield from walk(v)
            elif isinstance(o, list):
                for v in o:
                    yield from walk(v)
        seen = set()
        only_b = len(sys.argv) > 3
        for o in walk(d):
            u = o["detailUrl"]
            if u in seen:
                continue
            seen.add(u)
            if only_b and "homedetails" in u:
                continue
            pr = o.get("price") or ";".join(f"{x.get('beds')}bd {x.get('price')}" for x in (o.get("units") or []))
            print(o.get("buildingName") or "-", "|", o.get("address"), "|", pr, "|", u.replace("https://www.zillow.com", ""))
        print("total listed:", len(seen))
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
