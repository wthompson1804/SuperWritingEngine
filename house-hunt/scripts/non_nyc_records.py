"""Official records and police-located incidents for candidate buildings OUTSIDE New York City.

Two sources turned out to be usable (see data/reference/non_nyc_record_sources.csv for everything that was checked):

1. NJ Department of Community Affairs, Bureau of Housing Inspection (BHI), DCA Service Portal property search
   (serviceportal.dca.nj.gov, no login, host has no robots.txt). For every New Jersey candidate building:
   the portal's own search query (/_odata/bhibuildings), the public "View Property Details" page, and the inspection
   report PDFs that page links (dcaultra.blob.core.windows.net). From each report: inspection type and date, number
   of OPEN and CLOSED violations, open life-safety violations, and keyword counts in the open violations.
2. Jersey City Police "JC IMPACT" crime data portal (impact.jcnj.org): block-level incidents bundled in the page's
   own JavaScript (robots.txt allows it; it disallows /*.json$ and /*.pdf$, which are not fetched). Window is
   2025-12-28 to 2026-11-11 (about 10.5 months), NOT 24 months. Stolen vehicles + thefts from autos within 250 m of
   each Jersey City candidate, the median over those candidates, and the "at least double the median" test.

Outputs: data/evidence/non_nyc_records.csv (rewritten whole; idempotent), raw cache in raw/non_nyc_records/.
Usage: python3 scripts/non_nyc_records.py [--no-fetch]
"""
import csv, glob, json, math, re, statistics, subprocess, sys
from pathlib import Path
from urllib.parse import quote, unquote
sys.path.insert(0, str(Path(__file__).parent))
import lib
import non_nyc_probe as P

NOFETCH = "--no-fetch" in sys.argv
OUT = lib.DATA / "evidence" / "non_nyc_records.csv"
COLS = ["addr_key", "building_name", "municipality", "state", "source", "record_type", "metric", "period", "value",
        "detail", "match_note", "query_url", "retrieved_at"]
PORTAL = "https://serviceportal.dca.nj.gov"
DIRS = {"n", "s", "e", "w", "north", "south", "east", "west"}
KEYS = {"elevator": r"elevator", "heat_hot_water": r"\bheat|hot water|boiler", "pests": r"infest|roach|rodent|mice|vermin|bed ?bug|insect",
        "mold_leaks": r"mold|mildew|leak|water damage", "fire_safety": r"smoke|fire|carbon monoxide|extinguish|egress|sprinkler"}


def cached(url, ext):
    """Return (bytes or None, meta). Uses the cache; fetches politely unless --no-fetch."""
    for f in glob.glob(str(lib.RAW / P.SRC / "*.meta.json")) if NOFETCH else []:
        m = json.loads(Path(f).read_text())
        if m["url"] == url:
            return (lib.ROOT / m["path"]).read_bytes(), m
    if NOFETCH:
        return None, {"status": "not_fetched", "url": url}
    return P.get(url, ext=ext)


SUFFIX = {"st", "street", "ave", "avenue", "blvd", "boulevard", "rd", "road", "dr", "drive", "ter", "terrace", "pl", "place", "ln", "lane",
          "ct", "court", "way", "pkwy", "parkway", "hwy", "highway", "tpke", "turnpike", "plz", "plaza", "sq", "cir"}


def street_tokens(address):
    """House number and the street words worth searching on (first word, then the last word before the suffix)."""
    a = re.sub(r"[#,].*", "", address).strip()
    m = re.match(r"(\d+)(?:-\d+)?\s+(.*)", a)
    if not m:
        return None, []
    words = [w.strip(".") for w in re.split(r"\s+", m.group(2)) if w.lower().strip(".") not in DIRS]
    words = [w for w in words if w.lower() not in SUFFIX and len(w) > 1 and (not re.fullmatch(r"\d+[a-z]?", w.lower()) or re.search(r"(st|nd|rd|th)$", w.lower()))]
    words = [w for w in words if w.lower() not in ("apt", "unit", "at", "of", "the")]
    toks = []
    for w in ([words[0], words[-1]] if words else []):
        if w.upper() not in toks:
            toks.append(w.upper())
    return m.group(1), toks


def bhi_search(r):
    no, toks = street_tokens(r["address"])
    if not no or not toks:
        return [], "", "address has no house number + street"
    city = re.sub(r"[^a-z]", "", r["city"].lower().replace("city of ", "").split(",")[0])
    tried, url, when = [], "", ""
    for tok in toks:
        flt = f"substringof('{no} ',ultra_addressline1) and substringof('{tok}',ultra_addressline1)"
        url = f"{PORTAL}/_odata/bhibuildings?$inlinecount=allpages&$filter=" + quote(flt)
        c, m = cached(url, "json")
        if not c:
            tried.append(f"'{no} {tok}': search not available ({m.get('status')})"); continue
        try:
            vals = json.loads(c).get("value", [])
        except Exception:
            tried.append(f"'{no} {tok}': non-JSON reply"); continue
        when = m.get("retrieved_at", "")
        keep = []
        for v in vals:
            muni = re.sub(r"[^a-z]", "", ((v.get("ultra_municipality") or {}).get("Name") or "").lower())
            addr = (v.get("ultra_addressline1") or "").upper()
            z = (v.get("ultra_zipcode") or "")[:5]
            if not addr.startswith(no + " "):
                continue
            if z == r["zip"].zfill(5) or (city and (city[:6] in muni or muni[:6] in city)):
                keep.append(v)
        tried.append(f"'{no}' + '{tok}': {len(vals)} search hits, {len(keep)} at this house number in this municipality or ZIP")
        if keep:
            return keep, url, ("; ".join(tried), when)
    return [], url, ("; ".join(tried) + "; not found under this street address (a complex may be registered under another address, or the building may not be a registered multiple dwelling yet)", when)


def report_date(url):
    m = re.search(r"bhi-printfile/(\d{4})%2F([A-Za-z]+)%2F(\d+)%2F", url)
    if not m:
        return ""
    mon = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"].index(m.group(2).lower()) + 1
    return f"{m.group(1)}-{mon:02d}-{int(m.group(3)):02d}"


def parse_report(path):
    txt = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
    g = lambda pat: (re.search(pat, txt) or [None, ""])[1].strip()
    typ, date = g(r"Inspection Type:\s*(.+)"), g(r"Inspection Date:\s*([\d/]+)")
    units = g(r"Total Units:\s*(\d+)")
    i, j = txt.find("OPEN VIOLATIONS"), txt.find("CLOSED VIOLATIONS")
    if i < 0:
        return None
    open_t = txt[i:j] if j > i else txt[i:]
    closed_t = txt[j:] if j > i else ""
    ids = lambda s: re.findall(r"(?m)^\s*(\d{7,9})\b(.*)$", s)
    o, c = ids(open_t), ids(closed_t)
    life = sum(1 for _, rest in o if re.search(r"\bYes\b", rest))
    kw = {k: len(re.findall(p, open_t, re.I)) for k, p in KEYS.items()}
    mm, dd, yy = (date.split("/") + ["", "", ""])[:3]
    iso = f"{yy}-{int(mm):02d}-{int(dd):02d}" if yy else ""
    return dict(type=typ, date=iso, units=units, open=len(o), closed=len(c), life_safety_open=life, kw=kw)


def nj_rows(rows):
    out = []
    for r in rows:
        base = dict(addr_key=r["addr_key"], building_name=r["building_name"], municipality=r["city"], state="NJ",
                    source="NJ DCA Bureau of Housing Inspection (DCA Service Portal property search)", record_type="housing_inspection")
        hits, qurl, note = bhi_search(r)
        when = ""
        if isinstance(note, tuple):
            note, when = note
        if not hits:
            out.append({**base, "metric": "bhi_registration", "period": "current", "value": "not_found", "detail": "",
                        "match_note": note, "query_url": qurl, "retrieved_at": when or lib.now_iso()})
            print("NJ", r["addr_key"][:40], "not found:", note, flush=True)
            continue
        pids = {}
        for v in hits:
            pi = v.get("ultra_propertyinterest") or {}
            if pi.get("Id"):
                pids.setdefault(pi["Id"], v)
        nrep = 0
        for pid, v in list(pids.items())[:3]:
            purl = f"{PORTAL}/ultra-bhi-home/ultra-bhi-propertysearch/ultra-bhi-propertyinterest?pid={pid}"
            c, m = cached(purl, "html")
            reg = (v.get("ultra_bhibuildingregistrationnum") or v.get("ultra_registrationnumber") or "")
            mnote = f"{note}; matched BHI record '{v.get('ultra_name')}', {v.get('ultra_addressline1')}, {(v.get('ultra_municipality') or {}).get('Name')}, status {(v.get('statuscode') or {}).get('Name')}"
            out.append({**base, "metric": "bhi_registration", "period": "current", "value": reg or "registered",
                        "detail": f"property name {v.get('ultra_name')}; block {v.get('ultra_block')} lot {v.get('ultra_lot')}; registration status {(v.get('statuscode') or {}).get('Name')}",
                        "match_note": mnote, "query_url": qurl, "retrieved_at": when})
            if not c:
                continue
            t = c.decode(errors="replace")
            links = list(dict.fromkeys(re.findall(r"inspectionLinkHashmap\.set\('[^']+','([^']+)'\)", t)))
            names = list(dict.fromkeys(re.findall(r"inspections3LinkHashmap\.set\('[^']+','([^']+)'\)", t)))
            out.append({**base, "metric": "bhi_inspections_on_file", "period": "all_years", "value": len(names),
                        "detail": "inspection names on the property page (registration-type-date; CY = cyclical, RI = reinspection, AD = addendum): " + "; ".join(names)[:900],
                        "match_note": mnote, "query_url": purl, "retrieved_at": m.get("retrieved_at", "")})
            dated = sorted(((report_date(u), u) for u in links if report_date(u)), reverse=True)
            for d, u in [x for x in dated if x[0] >= "2021-11-15"][:4]:
                pc, pm = cached(u, "pdf")
                if not pc:
                    out.append({**base, "metric": "bhi_inspection_report", "period": d, "value": "not_read", "detail": f"report PDF not available ({pm.get('status')})",
                                "match_note": mnote, "query_url": u, "retrieved_at": lib.now_iso()})
                    continue
                rep = parse_report(lib.ROOT / pm["path"])
                if not rep:
                    out.append({**base, "metric": "bhi_inspection_report", "period": d, "value": "not_parsed", "detail": "PDF text has no OPEN VIOLATIONS section",
                                "match_note": mnote, "query_url": u, "retrieved_at": pm.get("retrieved_at", "")})
                    continue
                nrep += 1
                kw = "; ".join(f"{k}={n}" for k, n in rep["kw"].items() if n)
                out.append({**base, "metric": "bhi_open_violations_at_inspection", "period": rep["date"] or d, "value": rep["open"],
                            "detail": f"inspection type: {rep['type']}; report issued {d}; open violations {rep['open']} (life-safety {rep['life_safety_open']}); "
                                      f"closed/abated listed {rep['closed']}; units {rep['units']}; keyword mentions in open violations: {kw or 'none'}",
                            "match_note": mnote, "query_url": u, "retrieved_at": pm.get("retrieved_at", "")})
            if not dated:
                out.append({**base, "metric": "bhi_inspection_report", "period": "since 2021-11-15", "value": "none_on_page",
                            "detail": f"{len(links)} older report links on the page carry no date in the URL; not read",
                            "match_note": mnote, "query_url": purl, "retrieved_at": m.get("retrieved_at", "")})
        print("NJ", r["addr_key"][:40], "records", len(pids), "reports parsed", nrep, flush=True)
        write(out_all + out)
    return out


def jc_incidents():
    f = lib.RAW / P.SRC / "jc_impact_incidents_extracted.json"
    if f.exists():
        return json.loads(f.read_text()), "https://impact.jcnj.org/"
    c, m = P.get("https://impact.jcnj.org/")
    t = c.decode(errors="replace")
    for j in sorted(set(re.findall(r'/_next/static/immutable/chunks/[^"]+\.js', t))):
        c2, _ = P.get("https://impact.jcnj.org" + j, ext="js")
        s = (c2 or b"").decode(errors="replace")
        i = s.find("JSON.parse('{\"meta\":{\"period\"")
        if i < 0:
            continue
        i += len("JSON.parse('")
        k = i
        while True:
            k = s.find("'", k)
            if s[k - 1] != "\\":
                break
            k += 1
        d = json.loads(s[i:k].replace("\\'", "'").replace("\\\\", "\\"))
        f.write_text(json.dumps(d))
        return d, "https://impact.jcnj.org/"
    raise RuntimeError("JC IMPACT incident bundle not found")


def dist_m(a, b, c, d):
    return math.hypot((a - c) * 111320, (b - d) * 111320 * math.cos(math.radians(a)))


def jc_rows(rows):
    d, url = jc_incidents()
    inc = d["incidents"]
    lo, hi = min(x["date"] for x in inc), max(x["date"] for x in inc)
    window = f"{lo} to {hi} (about 10.5 months; the portal publishes nothing earlier, so this is NOT a 24-month count)"
    got = next((json.loads(Path(f).read_text())["retrieved_at"] for f in glob.glob(str(lib.RAW / P.SRC / "*.meta.json"))
                if "impact.jcnj.org/_next" in Path(f).read_text() and "3em-" in Path(f).read_text()), lib.now_iso())
    res = []
    for r in rows:
        la, lo_ = float(r["lat"]), float(r["lon"])
        near = [x for x in inc if x.get("lat") and dist_m(la, lo_, x["lat"], x["lng"]) <= 250]
        sv = sum(1 for x in near if x["type"] == "Stolen Vehicle")
        tfa = sum(1 for x in near if x["type"] == "Theft from Auto")
        res.append((r, sv, tfa, len(near)))
    med = statistics.median(sv + tfa for _, sv, tfa, _ in res)
    out = []
    for r, sv, tfa, n in res:
        base = dict(addr_key=r["addr_key"], building_name=r["building_name"], municipality="Jersey City", state="NJ",
                    source="Jersey City Police Department, JC IMPACT crime data portal (block-level incidents)", record_type="police_incidents",
                    period=window, query_url=url, retrieved_at=got,
                    match_note="incident points are geocoded to the block ('100 block of ...'), so a 250 m circle is approximate; figures are preliminary per the portal")
        tot = sv + tfa
        out.append({**base, "metric": "vehicle_theft_250m", "value": sv, "detail": "type 'Stolen Vehicle' within 250 m of the building's coordinates"})
        out.append({**base, "metric": "theft_from_vehicle_250m", "value": tfa, "detail": "type 'Theft from Auto' within 250 m"})
        out.append({**base, "metric": "vehicle_crime_250m_total", "value": tot,
                    "detail": f"stolen vehicles + thefts from autos within 250 m; median over the {len(res)} Jersey City candidate buildings = {med:g}; "
                              f"ratio to median = {(tot / med if med else float('nan')):.2f}; at least double the median: {'yes' if med and tot >= 2 * med else 'no'}; "
                              f"all tracked incident types within 250 m: {n}"})
        out.append({**base, "metric": "city_candidate_median_vehicle_crime_250m", "value": f"{med:g}",
                    "detail": f"median of vehicle_crime_250m_total over {len(res)} Jersey City candidate buildings (same window)"})
        print("JC", r["addr_key"][:40], sv, tfa, "median", med, flush=True)
    return out


out_all = []


def write(rows):
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})


def main():
    global out_all
    cands = []
    for f in ["all_candidate_buildings.csv", "round2_candidate_buildings.csv"]:
        p = lib.DATA / "reference/evidence_batches" / f
        if p.exists():
            cands += list(csv.DictReader(open(p)))
    seen, rows = set(), []
    for r in cands:
        if r["addr_key"] not in seen:
            seen.add(r["addr_key"]); rows.append(r)
    jc = [r for r in rows if r["state"] == "NJ" and r["city"].strip().lower() == "jersey city"]
    out_all = jc_rows(jc)
    write(out_all)
    out_all += nj_rows([r for r in rows if r["state"] == "NJ"])
    write(out_all)
    print("rows", len(out_all))


if __name__ == "__main__":
    main()
