"""Phase 1, domain `safety`, NYC areas only (county_fips 36005/36047/36061/36081/36085).

Sources
  1. NYPD Complaint Data (NYC Open Data, Socrata)
       Historic  qgea-i56i  (rpt_dt 2006-01-01 .. 2025-12-31)
       Current   5uac-w243  (2026 YTD; max rpt_dt is read from the API)
     Counted with SoQL within_circle(lat_lon, lat, lon, 804.67) (0.5 mi) around each centroid,
     grouped by report-date year/month, ky_cd and pd_cd.
  2. NYPD CompStat weekly precinct PDFs (nyc.gov), parsed with pdfplumber.
  3. 2020 Decennial PL 94-171 (www2.census.gov bulk file, NY) block population, used as the
     denominator for rates (blocks whose internal point lies within 0.5 mi; precinct population
     = blocks whose internal point lies inside the NYPD precinct polygon).

Output: data/metrics/safety_nyc.csv. Idempotent: all HTTP calls are cached by lib.cached_get;
the CSV is rewritten from scratch each run.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from lib import DATA, RAW, ROOT, USER_AGENT, cached_get, get_json, now_iso  # noqa: E402

# data.cityofnewyork.us robots.txt sets Crawl-delay: 1 (lib default for this host is 0.3 s).
lib.HOST_DELAY["data.cityofnewyork.us"] = 1.0

NYC_FIPS = {"36005", "36047", "36061", "36081", "36085"}
RADIUS_M = 804.67
SODA = "https://data.cityofnewyork.us/resource"
HIST, CURR = "qgea-i56i", "5uac-w243"
OUT = DATA / "metrics" / "safety_nyc.csv"
COLS = ["area_id", "domain", "metric", "value", "unit", "geography", "period", "source", "source_url",
        "retrieved_at", "raw_path", "value_type", "method", "population_used", "notes"]

# Category mapping (NYPD key codes ky_cd / internal codes pd_cd). ofns_desc / pd_desc shown for the record.
CATS = {
    "murder":            ("ky", {"101"}),   # MURDER & NON-NEGL. MANSLAUGHTER
    "rape":              ("ky", {"104"}),   # RAPE
    "robbery":           ("ky", {"105"}),   # ROBBERY
    "felony_assault":    ("ky", {"106"}),   # FELONY ASSAULT
    "burglary":          ("ky", {"107"}),   # BURGLARY
    "grand_larceny":     ("ky", {"109"}),   # GRAND LARCENY (includes pd 421 from vehicle)
    "auto_theft":        ("ky", {"110"}),   # GRAND LARCENY OF MOTOR VEHICLE (auto, moped, motorcycle, truck, attempts)
    "theft_from_vehicle": ("pd", {"321", "421"}),  # LARCENY,PETIT FROM AUTO ; LARCENY,GRAND FROM VEHICLE/MOTORCYCLE
    "vehicle_accessory_theft": ("pd", {"357"}),  # LARCENY,PETIT OF VEHICLE ACCES (parts, e.g. catalytic converters)
}
MAJOR7 = {"101", "104", "105", "106", "107", "109", "110"}
CAT_ORDER = list(CATS) + ["major7_total"]
KY_LIST = sorted(MAJOR7)
PD_LIST = ["321", "357", "421"]

PL_URL = ("https://www2.census.gov/programs-surveys/decennial/2020/data/"
          "01-Redistricting_File--PL_94-171/New_York/ny2020.pl.zip")
PL_ZIP = RAW / "big" / "census_pl2020" / "ny2020.pl.zip"
BLOCKS_CACHE = RAW / "census_pl2020" / "nyc_blocks_pop.csv"
PRECINCTS_URL = "https://data.cityofnewyork.us/resource/y76i-bdw7.geojson"
CS_URL = "https://www.nyc.gov/assets/nypd/downloads/pdf/crime_statistics/cs-en-us-{p:03d}pct.pdf"
CS_PAGE = "https://www.nyc.gov/site/nypd/stats/crime-statistics/compstat.page"


def rel(p) -> str:
    return str(Path(p).relative_to(ROOT)) if Path(p).is_absolute() else str(p)


# ---------------------------------------------------------------- population (2020 PL 94-171)
def load_blocks() -> list[tuple[str, float, float, int]]:
    """Return [(block_geoid, lat, lon, pop)] for NYC blocks. Cached as a small CSV."""
    if BLOCKS_CACHE.exists():
        with open(BLOCKS_CACHE) as f:
            return [(r["geoid"], float(r["lat"]), float(r["lon"]), int(r["pop"])) for r in csv.DictReader(f)]
    if not PL_ZIP.exists():
        PL_ZIP.parent.mkdir(parents=True, exist_ok=True)
        print("downloading", PL_URL)
        with requests.get(PL_URL, headers={"User-Agent": USER_AGENT}, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(PL_ZIP, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        with open(RAW / "big" / "census_pl2020" / "_index.jsonl", "a") as f:
            f.write(json.dumps({"url": PL_URL, "retrieved_at": now_iso(), "status": 200,
                                "path": rel(PL_ZIP), "source": "census_pl2020"}) + "\n")
    z = zipfile.ZipFile(PL_ZIP)
    geo = {}
    with z.open("nygeo2020.pl") as f:
        for line in io.TextIOWrapper(f, encoding="latin-1"):
            t = line.rstrip("\n").split("|")
            # 2020 PL geo header: SUMLEV=t[2], LOGRECNO=t[7], STATE=t[12], COUNTY=t[14],
            # TRACT=t[32], BLKGRP=t[33], BLOCK=t[34], INTPTLAT=t[92], INTPTLON=t[93]
            if t[2] != "750" or ("36" + t[14]) not in NYC_FIPS:
                continue
            geo[t[7]] = ("36" + t[14] + t[32] + t[34], float(t[92]), float(t[93]))
    out = []
    with z.open("ny000012020.pl") as f:
        for line in io.TextIOWrapper(f, encoding="latin-1"):
            t = line.split("|", 6)
            if t[4] in geo:  # LOGRECNO, then P0010001 (total population)
                g = geo[t[4]]
                out.append((g[0], g[1], g[2], int(t[5])))
    BLOCKS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(BLOCKS_CACHE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["geoid", "lat", "lon", "pop"])
        w.writerows(out)
    print(f"NYC blocks: {len(out)}, pop {sum(b[3] for b in out)}")
    return out


def haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def precinct_pops(blocks) -> dict[int, int]:
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree
    gj, _ = get_json(PRECINCTS_URL, "nyc_open_data", params={"$limit": 200})
    polys, ids = [], []
    for ft in gj["features"]:
        polys.append(shape(ft["geometry"]))
        ids.append(int(float(ft["properties"]["precinct"])))
    tree = STRtree(polys)
    pops = defaultdict(int)
    for _, lat, lon, pop in blocks:
        pt = Point(lon, lat)
        for i in tree.query(pt, predicate="within"):
            pops[ids[int(i)]] += pop
            break
    return pops


# ---------------------------------------------------------------- complaint data
def soql(dataset, where, select, group):
    params = {"$select": select, "$where": where, "$group": group, "$limit": 50000}
    data, meta = get_json(f"{SODA}/{dataset}.json", "nyc_open_data", params=params)
    return data, meta


def area_counts(lat, lon, end_curr):
    ky = ",".join(f"'{k}'" for k in KY_LIST)
    pd = ",".join(f"'{p}'" for p in PD_LIST)
    circle = f"within_circle(lat_lon, {lat}, {lon}, {RADIUS_M})"
    sel = "date_extract_y(rpt_dt) as y, date_extract_m(rpt_dt) as m, ky_cd, pd_cd, count(*) as n"
    grp = "y, m, ky_cd, pd_cd"
    filt = f"(ky_cd in ({ky}) or pd_cd in ({pd}))"
    h, hm = soql(HIST, f"{circle} and rpt_dt >= '2023-01-01T00:00:00' and rpt_dt <= '2025-12-31T23:59:59' and {filt}", sel, grp)
    c, cm = soql(CURR, f"{circle} and rpt_dt >= '2026-01-01T00:00:00' and rpt_dt <= '{end_curr}T23:59:59' and {filt}", sel, grp)
    return h, hm, c, cm


def tally(rows, months=None):
    """rows -> {year: {cat: count}}; months limits to those report months."""
    out = defaultdict(lambda: defaultdict(int))
    for r in rows:
        y, m, k, p, n = int(r["y"]), int(r["m"]), r.get("ky_cd"), r.get("pd_cd"), int(r["n"])
        if months and m not in months:
            continue
        for cat, (kind, codes) in CATS.items():
            if (k if kind == "ky" else p) in codes:
                out[y][cat] += n
        if k in MAJOR7:
            out[y]["major7_total"] += n
    return out


def citywide_missing(end_curr):
    """Citywide major-7 + from-vehicle complaints with no usable coordinates, per report year."""
    ky = ",".join(f"'{k}'" for k in KY_LIST)
    res = {}
    for ds, lo, hi in [(HIST, "2023-01-01", "2025-12-31"), (CURR, "2026-01-01", end_curr)]:
        base = f"rpt_dt >= '{lo}T00:00:00' and rpt_dt <= '{hi}T23:59:59' and ky_cd in ({ky})"
        tot, m1 = soql(ds, base, "date_extract_y(rpt_dt) as y, ky_cd, count(*) as n", "y, ky_cd")
        mis, m2 = soql(ds, base + " and (latitude is null or latitude = 0)",
                       "date_extract_y(rpt_dt) as y, ky_cd, count(*) as n", "y, ky_cd")
        for r in tot:
            res.setdefault((r["y"], r["ky_cd"]), [0, 0])[0] += int(r["n"])
        for r in mis:
            res.setdefault((r["y"], r["ky_cd"]), [0, 0])[1] += int(r["n"])
        res.setdefault("_urls", []).extend([m1["url"], m2["url"]])
    return res


# ---------------------------------------------------------------- CompStat PDFs
CS_ROWS = {"Murder": "murder", "Rape": "rape", "Robbery": "robbery", "Fel. Assault": "felony_assault",
           "Burglary": "burglary", "Gr. Larceny": "grand_larceny", "G.L.A.": "auto_theft",
           "TOTAL": "major7_total", "Transit": "transit", "Housing": "housing"}
NUM = re.compile(r"\*\*\*\.\*|-?\d[\d,]*(?:\.\d+)?")


def to_num(s):
    return None if s.startswith("***") else float(s.replace(",", ""))


def parse_compstat(pdf_bytes):
    import pdfplumber
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    wk = re.search(r"Report Covering the Week\s+(\d+/\d+/\d{4}) Through (\d+/\d+/\d{4})", text)
    vol = re.search(r"Volume (\d+) Number (\d+)", text)
    crime_part, _, hist_part = text.partition("Historical Perspective")
    ytd, hist = {}, {}
    for line in crime_part.splitlines():
        for label, cat in CS_ROWS.items():
            if line.startswith(label + " "):
                nums = NUM.findall(line[len(label):])
                if len(nums) >= 9:
                    ytd[cat] = (to_num(nums[6]), to_num(nums[7]), to_num(nums[8]))
    yrs = re.search(r"\n(1990 1993 1998 2001 (\d{4}))", hist_part)
    for line in hist_part.splitlines():
        for label, cat in CS_ROWS.items():
            if line.startswith(label + " ") and cat not in ("transit", "housing"):
                nums = NUM.findall(line[len(label):])
                if len(nums) >= 5:
                    hist[cat] = to_num(nums[4])
    return {"week_start": wk.group(1) if wk else None, "week_end": wk.group(2) if wk else None,
            "volume": f"{vol.group(1)}-{vol.group(2)}" if vol else None, "ytd": ytd, "hist": hist,
            "hist_year": yrs.group(2) if yrs else None}


def mdy_to_iso(s):
    m, d, y = s.split("/")
    return f"{y}-{int(m):02d}-{int(d):02d}"


# ---------------------------------------------------------------- main
def main():
    areas = [r for r in csv.DictReader(open(DATA / "areas.csv")) if r["county_fips"] in NYC_FIPS]
    print(f"NYC areas: {len(areas)}")
    rows = []

    def add(area, metric, value, unit, geography, period, source, url, meta_or_rt, value_type,
            method="", population_used="", notes=""):
        rt, rp = (meta_or_rt["retrieved_at"], meta_or_rt["path"]) if isinstance(meta_or_rt, dict) else meta_or_rt
        rows.append(dict(area_id=area["id"], domain="safety", metric=metric,
                         value="" if value is None else value, unit=unit, geography=geography, period=period,
                         source=source, source_url=url, retrieved_at=rt, raw_path=rp, value_type=value_type,
                         method=method, population_used=population_used, notes=notes))

    # Current-dataset end date (data through)
    mx, mxm = get_json(f"{SODA}/{CURR}.json", "nyc_open_data",
                       params={"$select": "max(rpt_dt) as mx, min(rpt_dt) as mn"})
    end_curr = mx[0]["mx"][:10]
    print("current dataset rpt_dt through", end_curr)
    ytd_months = set(range(1, int(end_curr[5:7]) + 1))
    if end_curr[5:] not in ("01-31", "02-28", "02-29", "03-31", "04-30", "05-31", "06-30", "07-31",
                            "08-31", "09-30", "10-31", "11-30", "12-31"):
        print("WARNING: 2026 YTD does not end on a month end; 2025 comparison uses whole months")

    blocks = load_blocks()
    pl_meta = (now_iso(), rel(PL_ZIP))
    idx = RAW / "big" / "census_pl2020" / "_index.jsonl"
    if idx.exists():
        last = json.loads(idx.read_text().strip().splitlines()[-1])
        pl_meta = (last["retrieved_at"], last["path"])

    # ---- radius counts
    for a in areas:
        lat, lon = float(a["centroid_lat"]), float(a["centroid_lon"])
        pop = sum(b[3] for b in blocks if haversine(lat, lon, b[1], b[2]) <= RADIUS_M)
        nblk = sum(1 for b in blocks if haversine(lat, lon, b[1], b[2]) <= RADIUS_M)
        pop_desc = (f"{pop} residents: 2020 Census PL 94-171 P1_001N summed over {nblk} blocks whose internal "
                    f"point is within 0.5 mi of the centroid (estimate)")
        add(a, "census2020_pop_0.5mi", pop, "persons", "radius_0.5mi", "2020-04-01", "census_pl2020", PL_URL,
            pl_meta, "estimate", method="Sum of block P1_001N where block INTPTLAT/INTPTLON within 804.67 m "
            "(haversine) of centroid; blocks not split by the circle edge.")

        h, hm, c, cm = area_counts(lat, lon, end_curr)
        th, tc = tally(h), tally(c)
        th_ytd = tally(h, ytd_months)
        geo = "radius_0.5mi"
        meth = (f"SoQL within_circle(lat_lon, {lat}, {lon}, {RADIUS_M}); year = report date (rpt_dt); "
                "category by ky_cd/pd_cd (see notes md)")
        for cat in CAT_ORDER:
            m = f"nypd_{cat}_0.5mi"
            for y in (2023, 2024, 2025):
                add(a, m, th[y][cat], "count", geo, str(y), "nypd_complaints_historic", hm["url"], hm, "found", meth)
            add(a, m, th_ytd[2025][cat], "count", geo, f"2025-01-01/{'2025' + end_curr[4:]}",
                "nypd_complaints_historic", hm["url"], hm, "found", meth,
                notes="Same report-month span as 2026 YTD, for comparison")
            add(a, m, tc[2026][cat], "count", geo, f"2026-01-01/{end_curr}", "nypd_complaints_ytd", cm["url"], cm,
                "found", meth, notes=f"2026 YTD; dataset 5uac-w243 max rpt_dt {end_curr}")
            c23, c25 = th[2023][cat], th[2025][cat]
            pct = round((c25 - c23) / c23 * 100, 1) if c23 else None
            add(a, f"{m}_pct_change_2023_2025", pct, "pct", geo, "2023-2025", "nypd_complaints_historic",
                hm["url"], hm, "estimate" if pct is not None else "not_found",
                method=f"(count_2025 - count_2023) / count_2023 * 100 = ({c25} - {c23}) / {c23} * 100",
                notes="" if pct is not None else "2023 count is 0; pct change undefined")
            if pop:
                avg = (th[2023][cat] + th[2024][cat] + th[2025][cat]) / 3
                add(a, f"{m}_per1000", round(th[2025][cat] / pop * 1000, 2), "per_1000", geo, "2025",
                    "nypd_complaints_historic", hm["url"], hm, "estimate",
                    method=f"count_2025 {th[2025][cat]} / residents within 0.5 mi * 1000", population_used=pop_desc,
                    notes="Residential denominator; commercial/transit hubs inflate rates (daytime population not counted)")
                add(a, f"{m}_per1000_avg_2023_2025", round(avg / pop * 1000, 2), "per_1000", geo, "2023-2025",
                    "nypd_complaints_historic", hm["url"], hm, "estimate",
                    method=f"mean annual count 2023-2025 {avg:.1f} / residents within 0.5 mi * 1000",
                    population_used=pop_desc)
        print(a["id"], "pop", pop, "major7 2025", th[2025]["major7_total"], "gla", th[2025]["auto_theft"],
              "from_veh", th[2025]["theft_from_vehicle"])

    # ---- CompStat precinct PDFs
    ppops = precinct_pops(blocks)
    for a in areas:
        mm = re.search(r"(\d+)", a["police_jurisdiction"])
        p = int(mm.group(1))
        url = CS_URL.format(p=p)
        try:
            content, meta = cached_get(url, "nypd_compstat", ext="pdf")
            ok = meta["status"] == 200
        except RuntimeError as e:
            ok, meta = False, {"retrieved_at": now_iso(), "path": ""}
            print("compstat fetch failed", url, e)
        geo = f"precinct:{p}"
        if not ok:
            for cat in CS_ROWS.values():
                add(a, f"compstat_{cat}_ytd", None, "count", geo, "", "nypd_compstat", url, meta, "not_found",
                    notes=f"CompStat PDF fetch failed (HTTP {meta.get('status')})")
            continue
        cs = parse_compstat(content)
        ws, we = mdy_to_iso(cs["week_start"]), mdy_to_iso(cs["week_end"])
        note = f"CompStat Vol {cs['volume']}, report week {ws} to {we}; figures preliminary"
        yy = int(we[:4])
        for cat in CS_ROWS.values():
            v = cs["ytd"].get(cat)
            meth = "pdfplumber text parse of the precinct CompStat PDF, 'Year to Date' columns"
            if v is None:
                add(a, f"compstat_{cat}_ytd", None, "count", geo, f"{yy}-01-01/{we}", "nypd_compstat", url, meta,
                    "not_found", notes=f"Row not found in PDF. {note}")
                continue
            add(a, f"compstat_{cat}_ytd", v[0], "count", geo, f"{yy}-01-01/{we}", "nypd_compstat", url, meta,
                "found", meth, notes=note)
            add(a, f"compstat_{cat}_ytd_prior_year", v[1], "count", geo, f"{yy-1}-01-01/{yy-1}{we[4:]}",
                "nypd_compstat", url, meta, "found", meth, notes=note)
            add(a, f"compstat_{cat}_ytd_pct_change", v[2], "pct", geo, f"{yy}-YTD vs {yy-1}-YTD to {we[5:]}",
                "nypd_compstat", url, meta, "found" if v[2] is not None else "not_found", meth,
                notes=note + ("" if v[2] is not None else "; PDF shows ***.* (prior-year base 0)"))
        hy = cs["hist_year"]
        for cat, v in cs["hist"].items():
            add(a, f"compstat_{cat}_full_year", v, "count", geo, hy, "nypd_compstat", url, meta,
                "found" if v is not None else "not_found",
                "pdfplumber parse, 'Historical Perspective' table (complete calendar year)",
                notes=note + ("" if v is not None else "; PDF shows ***.* for this cell"))
            if v is None:
                continue
            pp = ppops.get(p)
            if pp:
                add(a, f"compstat_{cat}_per1000_precinct", round(v / pp * 1000, 2), "per_1000", geo, hy,
                    "nypd_compstat", url, meta, "estimate",
                    method=f"CompStat {hy} full-year count {v:g} / precinct residents * 1000",
                    population_used=(f"{pp} residents: 2020 Census PL 94-171 blocks whose internal point is inside "
                                     f"precinct {p} polygon (NYC Open Data y76i-bdw7) (estimate)"))
        print(a["id"], p, ws, we, "ytd total", cs["ytd"].get("major7_total"), "pop", ppops.get(p))

    # ---- citywide missing-coordinate counts (for notes)
    miss = citywide_missing(end_curr)
    (RAW / "nyc_open_data").mkdir(exist_ok=True)
    with open(ROOT / "raw" / "nyc_open_data" / "safety_nyc_missing_coords_summary.json", "w") as f:
        json.dump({"urls": miss.pop("_urls"),
                   "by_year_kycd": {f"{y}|{k}": v for (y, k), v in sorted(miss.items())}}, f, indent=1)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    vt = defaultdict(int)
    for r in rows:
        vt[r["value_type"]] += 1
    print("rows", len(rows), dict(vt))


if __name__ == "__main__":
    main()
