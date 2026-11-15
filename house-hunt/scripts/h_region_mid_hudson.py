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


def zbuilding(url):
    """Fetch a Zillow building page and return (building dict, meta) from its __NEXT_DATA__ JSON."""
    t, m = fetch(url)
    mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
    if not mm:
        return None, m
    d = json.loads(mm.group(1))
    try:
        b = d["props"]["pageProps"]["componentProps"]["initialReduxState"]["gdp"]["building"]
    except (KeyError, TypeError):
        b = None
    return b, m


def zfacts(b):
    from datetime import datetime, timezone
    am = json.dumps(b.get("structuredAmenities") or {}) + json.dumps((b.get("buildingAttributes") or {}))
    summ = (b.get("amenitySummary") or {}).get("buildingDetails") or []
    stories = next((re.match(r"(\d+) stor", x).group(1) for x in summ if re.match(r"(\d+) stor", x)), "")
    elev = "yes" if re.search(r'"Elevator', am) else ("yes" if stories and int(stories) >= 6 else "unknown")
    pets = []
    dogs, wl, petrent, large = "unknown", "", "", None
    for pp in ((b.get("detailedPetPolicy") or {}).get("petPolicies") or []):
        typ = ((pp.get("petSize") or "") + " " + (pp.get("petType") or "")).strip()
        bits = [str(typ), "allowed" if pp.get("allowed") else "NOT allowed"]
        for k in ("maxWeightAllowed", "maxNumberAllowed", "monthlyFee", "oneTimeFee", "deposit", "restrictions", "comment", "description"):
            if pp.get(k) not in (None, "", []):
                bits.append(f"{k}={pp[k]}")
        pets.append(" ".join(bits))
        if "dog" in str(typ).lower():
            if "large" in str(typ).lower():
                large = bool(pp.get("allowed"))
            if pp.get("allowed"):
                dogs = "yes"
                if pp.get("maxWeightAllowed"):
                    wl = str(pp["maxWeightAllowed"])
                if pp.get("monthlyFee"):
                    petrent = str(pp["monthlyFee"])
            elif dogs != "yes":
                dogs = "no"
    dp = b.get("detailedPetPolicy") or {}
    def _txt(v):
        if isinstance(v, list):
            return " ".join(_txt(x) for x in v)
        if isinstance(v, dict):
            return " ".join(str(x) for x in v.values() if x)
        return str(v)
    gen = " ".join(_txt(dp.get(k)) for k in ("general", "restrictions", "comments", "descriptions") if dp.get(k)).strip()
    if gen:
        pets.insert(0, "general: " + gen)
        mw = re.findall(r"(\d{2,3})\s*(?:#|lbs?\b|pounds?|lb\.)", gen)
        if mw and not wl:
            wl = str(max(int(x) for x in mw))
        if dogs == "unknown" and re.search(r"(?i)\bdogs?\b", gen) and not C.DOG_NO.search(gen):
            dogs = "yes"
    if large is False and dogs == "yes":
        pets.append("LARGE DOGS NOT ALLOWED (Zillow size flag)")
    units = []
    for fp in b.get("floorPlans") or []:
        us = fp.get("units") or []
        if not us:
            us = [{"unitNumber": "floor plan " + str(fp.get("name") or ""), "beds": fp.get("beds"), "baths": fp.get("baths"),
                   "price": fp.get("minPrice") or fp.get("price"), "sqft": fp.get("sqft"), "availableFrom": fp.get("availableFrom"), "_fp": True}]
        for u in us:
            u = dict(u)
            u.setdefault("baths", fp.get("baths"))
            u["_plan"] = fp.get("name")
            af = str(u.get("availableFrom") or "")
            if af == "0":
                u["_avail"], u["_availtxt"] = "now", "Available now"
            elif af.isdigit() and len(af) > 9:
                dt = datetime.fromtimestamp(int(af) / 1000, tz=timezone.utc).date().isoformat()
                u["_avail"], u["_availtxt"] = dt, dt
            else:
                u["_avail"], u["_availtxt"] = "", af
            units.append(u)
    for u in b.get("ungroupedUnits") or []:
        u = dict(u)
        af = str(u.get("availableFrom") or "")
        if af == "0":
            u["_avail"], u["_availtxt"] = "now", "Available now"
        elif af.isdigit() and len(af) > 9:
            dt = datetime.fromtimestamp(int(af) / 1000, tz=timezone.utc).date().isoformat()
            u["_avail"], u["_availtxt"] = dt, dt
        else:
            u["_avail"], u["_availtxt"] = "", af
        units.append(u)
    today = datetime.now(timezone.utc).date().isoformat()
    for u in units:  # a listed date already in the past means available now; keep the page's date in the text
        if u["_avail"] and u["_avail"] != "now" and u["_avail"] <= today:
            u["_availtxt"] = f"available from {u['_avail']} (past date: now)"
            u["_avail"] = "now"
    park = (b.get("buildingAttributes") or {}).get("parkingTypes") or []
    return dict(stories=stories, elevator=elev, dogs=dogs, wl=wl, petrent=petrent, large=large, pets=pets, units=units, summ=summ,
                parking=", ".join(park), offers=[o.get("description") or o.get("title") or "" for o in (b.get("specialOffers") or [])])


def zj(url, write=None):
    b, m = zbuilding(url)
    if not b:
        print("NO BUILDING JSON", m.get("status"))
        return
    f = zfacts(b)
    name = b.get("buildingName") or b.get("streetAddress")
    print(f"## {name} | {b.get('fullAddress')} | {b.get('latitude')},{b.get('longitude')} | {m['retrieved_at']} | {m['path']}")
    print("   summary:", f["summ"], "| elevator:", f["elevator"], "| lowIncome:", b.get("isLowIncome"), "| senior:", b.get("isSeniorHousing"),
          "| parking:", f["parking"], "| offers:", f["offers"])
    print("   pets:", "; ".join(f["pets"]) or (b.get("amenityDetails") or {}).get("pets"))
    small = sorted([u for u in f["units"] if u.get("beds") in (0, 1)], key=lambda u: u.get("price") or 9e9)
    if write is not None:  # drop this building's earlier rows so a re-run replaces them
        if OUT.exists():
            with open(OUT, newline="") as fh:
                keep = [r for r in csv.DictReader(fh) if not (r["url"] == url and ":z:" in r["listing_id"])]
            with open(OUT, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=C.COLS)
                w.writeheader()
                w.writerows(keep)
    print("   studio/1BR:", " | ".join(f"{u.get('unitNumber')} {u.get('beds')}bd ${u.get('price')} {u.get('sqft')}sf {u['_availtxt']} fee{u.get('totalRequiredMonthlyMinFee')}" for u in small[:14]),
          f"(+{max(0, len(small) - 14)} more)", "| other beds:", sorted({str(u.get("beds")) for u in f["units"] if u.get("beds") not in (0, 1)}))
    desc = b.get("description") or ""
    for x in snippets(desc, r"(?i)elevator|walk-?up|\bdogs?\b|\bpets?\b|breed|\blbs?\b|pound|stor(y|ies)|floor\b|55|senior|income", 80, 6):
        print("   desc:", x)
    if write is None:
        return
    ov = kv(write)
    ok = [u for u in small if u.get("price") and u["price"] <= 3000]
    elev = ov.get("elevator", f["elevator"])
    dogs = ov.get("dogs", f["dogs"])
    policy = "; ".join(f["pets"]) or ("pets listed: " + ", ".join((b.get("amenityDetails") or {}).get("pets") or []))
    prefix = ov.get("prefix", "")
    if not prefix:
        if b.get("isSeniorHousing") or re.search(r"55\+|62\+|senior", name or "", re.I):
            prefix = "BUILDING_FAILS: age-restricted (55+/senior) community" + ("; income-restricted" if b.get("isLowIncome") else "") + "."
        elif b.get("isLowIncome"):
            prefix = "BUILDING_FAILS: income-restricted (affordable) housing; eligibility rules apply."
        elif dogs == "no":
            prefix = "BUILDING_FAILS: dogs not allowed."
        elif (f["wl"].isdigit() and int(f["wl"]) < 40) or (f["large"] is False and not f["wl"].isdigit()):
            prefix = "BUILDING_FAILS: large dogs not allowed / weight limit under 40 lb."
        elif elev == "no":
            prefix = "BUILDING_FAILS: no elevator."
        elif not small:
            prefix = "NO_AVAILABILITY: no studio or 1BR listed."
        elif not ok and not any(u.get("price") for u in small):
            prefix = "PRICE_NOT_LISTED: studio/1BR shown as available but rent is 'on request'."
        elif not ok:
            prefix = f"BUILDING_FAILS: nothing <= 3000 (cheapest studio/1BR {small[0].get('price')})."
        elif elev == "unknown":
            prefix = f"ELEVATOR_UNKNOWN: no elevator listed on the page ({f['stories'] or '?'} stories); likely garden-style walk-up, confirm."
    one = bool(prefix)
    rows = (ok or small)[:1] if one else ok
    base = dict(source_site="zillow.com", url=url, detail_level="building_page", first_seen=m["retrieved_at"], last_seen=m["retrieved_at"],
                building_name=name, address=b.get("streetAddress"), city=b.get("city"), state=b.get("state"), zip=b.get("zipcode"),
                lat=b.get("latitude"), lon=b.get("longitude"), dogs=dogs, dog_policy_text=policy[:500], dog_weight_limit_lb=f["wl"],
                elevator=elev, building_floors=f["stories"], parking_type=f["parking"], pet_rent=f["petrent"],
                concession_text="; ".join(f["offers"])[:300], listing_type="managed_building", building_url=ov.get("building_url", url),
                raw_path=m["path"], manager=ov.get("manager", (b.get("buildingPropertyRules") or {}).get("brokerNameIfRequired", "") or ""),
                laundry="; ".join((b.get("amenitySummary") or {}).get("laundry") or []), price_basis="base rent (Zillow building page)")
    base["manager"] = base["manager"].replace("Listings by: Listing by: ", "")
    out = []
    for u in rows or [None]:
        r = dict(base)
        if u:
            un = str(u.get("unitNumber") or "").replace("Unit ", "")
            fl = ""
            mfl = re.fullmatch(r"(\d)(\d\d)[A-Z]?", un)
            fees = u.get("totalRequiredMonthlyMinFee")
            r.update(unit=un, beds=u.get("beds"), baths=u.get("baths"), sqft=u.get("sqft") or "", listed_rent=u.get("price") or "",
                     available_date=u["_avail"], available_date_text=u["_availtxt"],
                     other_monthly_fees_json=C.jdump({"required_monthly_fees_min": fees}) if fees else "")
            if u.get("_fp"):
                r["price_basis"] = "floor plan 'from' price (Zillow building page)"
        r["listing_id"] = SRC + ":z:" + hashlib.sha1((url + "|" + str(r.get("unit", ""))).encode()).hexdigest()[:12]
        note = prefix
        if one and len(ok) > 1:
            note += f" {len(ok)} studio/1BR units <= 3000 on the page; only the cheapest recorded."
        r["notes"] = (note + " " + ov.get("notes", "")).strip()
        out.append(r)
    n = C.upsert(OUT, out)
    verdict = ov.get("verdict") or ("pass_with_units" if not prefix else prefix.split(":")[0].lower() + ":" + prefix.split(":", 1)[1].strip()[:90])
    bldg_upsert(dict(name=name, address=b.get("streetAddress"), town=b.get("city"), url=ov.get("building_url", url), floors=f["stories"],
                     elevator=elev, dogs=dogs + ("" if f["large"] is None else (" (large dogs ok)" if f["large"] else " (large dogs NOT allowed)")),
                     weight_limit=f["wl"] or "not_stated", verdict=verdict, source_url=url, notes=ov.get("notes", "")))
    print(f"   WROTE {len(out)} row(s); csv rows {n}; verdict {verdict}")


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
    elif cmd == "zj":
        try:
            zj(sys.argv[2])
        except (C.BotWall, RuntimeError) as e:
            print("BLOCKED/ERR:", str(e)[:200])
    elif cmd == "zw":
        try:
            zj(sys.argv[2], sys.argv[3:])
        except (C.BotWall, RuntimeError) as e:
            print("BLOCKED/ERR:", str(e)[:200])
    elif cmd == "show":
        with open(OUT, newline="") as fh:
            for r in csv.DictReader(fh):
                print(" | ".join(str(r[k])[:int(n)] for k, n in (("building_name", 28), ("city", 12), ("unit", 14), ("beds", 1), ("listed_rent", 5), ("available_date", 10), ("dogs", 7), ("dog_weight_limit_lb", 4), ("elevator", 7), ("floor", 2), ("notes", 70))))
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
