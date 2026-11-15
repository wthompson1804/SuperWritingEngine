"""Phase 1: ACS 5-year (2020-2024) people + housing + rent metrics per area.

Source: ACS table-based Summary File on www2.census.gov (no API needed).
  https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/
Each table is one national pipe-delimited .dat file (GEO_ID|<T>_E001|<T>_M001|...).
Bulk files are cached in raw/big/census_acs5_sf/ (git-ignored; re-downloaded if missing).
Rows for our geographies are written to small extracts in raw/census_acs5_sf/2024/
(committed) and every CSV row's raw_path points at its extract.

Geographies per area: every ZCTA in zcta_centroid + zctas_within_800m, the place
(or county subdivision when the area is a town/township with no place, or a NYC
borough as context), and the centroid tract.

Output: data/metrics/acs.csv (domains: people, rent). Idempotent: rewritten in full.
Not collected (by rule): race, ethnicity, ancestry, language, religion tables.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import DATA, ROOT, cached_get  # noqa: E402

YEAR = 2024
PERIOD = "2020-2024 ACS5"
SOURCE = "census_acs5_sf"
BASE = f"https://www2.census.gov/programs-surveys/acs/summary_file/{YEAR}/table-based-SF"
DATA_URL = BASE + "/data/5YRData/acsdt5y{y}-{t}.dat"
GEOS_URL = BASE + f"/documentation/Geos{YEAR}5YR.txt"
BIG_SOURCE = f"big/{SOURCE}"
EXTRACT_DIR = ROOT / "raw" / SOURCE / str(YEAR)
OUT = DATA / "metrics" / "acs.csv"
NYC_COUNTIES = {"36005", "36047", "36061", "36081", "36085"}

TABLES = ["b01001", "b01002", "b11001", "b25002", "b25003", "b25031",
          "b25034", "b25035", "b25036", "b25064"]

COLS = ["area_id", "domain", "metric", "value", "unit", "geography", "period", "source",
        "source_url", "retrieved_at", "raw_path", "value_type", "method", "population_used", "notes"]

# Census annotation codes used in place of a number.
EST_CODES = {
    -666666666: "estimate not computed: too few sample observations (code -666666666)",
    -999999999: "estimate not displayed: insufficient sample cases (code -999999999)",
    -888888888: "estimate not applicable (code -888888888)",
    -555555555: "estimate controlled (code -555555555)",
}
MOE_CODES = {
    -222222222: "MOE not computed: too few sample observations (code -222222222)",
    -333333333: "MOE not applicable: median falls in the lowest or highest open-ended interval, so the estimate is the interval boundary (code -333333333)",
    -555555555: "MOE not applicable: estimate is controlled, no sampling error (code -555555555)",
    -666666666: "MOE not computed (code -666666666)",
    -888888888: "MOE not applicable (code -888888888)",
    -999999999: "MOE not displayed: insufficient sample cases (code -999999999)",
}

YB_BUCKETS = ["2020_later", "2010_2019", "2000_2009", "1990_1999", "1980_1989",
              "1970_1979", "1960_1969", "1950_1959", "1940_1949", "1939_earlier"]
YB_LABEL = {"2020_later": "2020 or later", "1939_earlier": "1939 or earlier"}


def fetch_big(url: str, ext: str) -> tuple[Path, dict]:
    _, meta = cached_get(url, BIG_SOURCE, ext=ext, timeout=180, retries=4)
    if meta["status"] != 200:
        raise RuntimeError(f"HTTP {meta['status']} {url}")
    return ROOT / meta["path"], meta


def load_areas() -> list[dict]:
    return list(csv.DictReader(open(DATA / "areas.csv")))


def area_geos(a: dict) -> list[tuple[str, str, str]]:
    """Return [(label, GEO_ID, role)] for an area."""
    out = []
    zs = [a["zcta_centroid"]] + [z for z in a["zctas_within_800m"].split() if z != a["zcta_centroid"]]
    for z in zs:
        role = "centroid ZCTA" if z == a["zcta_centroid"] else "ZCTA within 800 m ring"
        out.append((f"zcta:{z}", f"860Z200US{z}", role))
    if a["county_fips"] in NYC_COUNTIES:
        out.append((f"cousub:{a['cousub_geoid']}", f"0600000US{a['cousub_geoid']}",
                    "NYC borough (county subdivision), context only: much larger than the area"))
    elif a["place_type"] == "county_subdivision" or not a["place_geoid"]:
        out.append((f"cousub:{a['cousub_geoid']}", f"0600000US{a['cousub_geoid']}",
                    "county subdivision (town/township; no separate place used)"))
    else:
        out.append((f"place:{a['place_geoid']}", f"1600000US{a['place_geoid']}",
                    f"place ({a['place_type']})"))
    out.append((f"tract:{a['tract_geoid']}", f"1400000US{a['tract_geoid']}", "centroid tract"))
    return out


def build_extracts(wanted: set[str]) -> dict:
    """Download (cached) each table, write small extracts, return {table: {geo: row}}, metas."""
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    tables, metas = {}, {}
    for t in TABLES + ["geos"]:
        ext_path = EXTRACT_DIR / f"{t}.psv"
        url = GEOS_URL if t == "geos" else DATA_URL.format(y=YEAR, t=t)
        if not ext_path.exists():
            big, meta = fetch_big(url, "txt" if t == "geos" else "dat")
            with open(big, encoding="latin-1") as f, open(ext_path, "w") as g:
                header = f.readline()
                g.write(header)
                gi = header.rstrip("\n").split("|").index("GEO_ID")
                for line in f:
                    if line.split("|", gi + 1)[gi] in wanted:
                        g.write(line)
            print(f"extracted {t} -> {ext_path.relative_to(ROOT)}")
        # metas: find the most recent index entry for the url
        metas[t] = index_meta(url)
        rows = {}
        with open(ext_path) as f:
            for r in csv.DictReader(f, delimiter="|"):
                rows[r["GEO_ID"]] = r
        tables[t] = rows
    return tables, metas


def index_meta(url: str) -> dict:
    idx = ROOT / "raw" / BIG_SOURCE / "_index.jsonl"
    import json
    best = None
    for line in open(idx):
        m = json.loads(line)
        if m["url"] == url and m["status"] == 200:
            best = m
    if best is None:  # extract exists but index lost: refetch to recover provenance
        _, best = fetch_big(url, "txt" if url == GEOS_URL else "dat")
    return best


def num(s: str | None):
    if s is None or s == "":
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return int(v) if v == int(v) else v


def fmt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


class Writer:
    def __init__(self, metas):
        self.rows = []
        self.metas = metas

    def base(self, area, domain, table, geo_label, role, name):
        m = self.metas[table]
        return {"area_id": area["id"], "domain": domain, "geography": geo_label, "period": PERIOD,
                "source": SOURCE, "source_url": m["url"], "retrieved_at": m["retrieved_at"],
                "raw_path": str((EXTRACT_DIR / f"{table}.psv").relative_to(ROOT)),
                "_ctx": f"{name}; {role}" if name else role}

    def add(self, b, metric, value, unit, value_type, method="", pop="", notes=""):
        r = {k: v for k, v in b.items() if k != "_ctx"}
        r.update(metric=metric, value=fmt(value), unit=unit, value_type=value_type, method=method,
                 population_used=pop, notes="; ".join(x for x in [b["_ctx"], notes] if x))
        self.rows.append(r)

    def direct(self, b, row, var, metric, unit, label):
        """A published estimate and its MOE."""
        if row is None:
            nf = f"GEO_ID not present in ACS {PERIOD} summary file table {var.split('_')[0]}"
            self.add(b, metric, None, unit, "not_found", notes=nf)
            self.add(b, metric + "_moe", None, unit, "not_found", notes=nf)
            return
        e, m = num(row.get(var.replace("_", "_E", 1))), num(row.get(var.replace("_", "_M", 1)))
        method = f"{var} ({label}) read directly"
        if e is None or e in EST_CODES:
            self.add(b, metric, None, unit, "not_found",
                     notes=EST_CODES.get(e, f"{var} empty"))
        else:
            note = ""
            if m == -333333333:
                if unit == "usd_month" and e == 3501:
                    e, note = 3500, ("TOP-CODED: Census publishes '3,500+' (file stores 3501); true median is "
                                     "$3,500 or more; value is the boundary, not the median")
                elif unit == "year" and e == 1938:
                    e, note = 1939, ("BOTTOM-CODED: Census publishes '1939 or earlier' (file stores 1938); "
                                     "value is the boundary, not the median")
                else:
                    note = (f"open-ended interval (file value {e}): true median is at or beyond this "
                            "boundary; value is the boundary, not the median")
            self.add(b, metric, e, unit, "found", method=method, notes=note)
        if m is None or m in MOE_CODES or (e is None or e in EST_CODES):
            self.add(b, metric + "_moe", None, unit, "not_found",
                     notes=MOE_CODES.get(m, "estimate not available") if m is not None else f"{var} MOE empty")
        else:
            self.add(b, metric + "_moe", m, unit, "found", method=method + " (90% MOE)")


def moe_val(m):
    """MOE as number; controlled (-555555555) => 0; other codes => None."""
    if m is None:
        return None
    if m == -555555555:
        return 0.0
    if m < 0:
        return None
    return float(m)


def share(b, w: Writer, row, num_vars, den_var, metric, desc, pop_desc):
    tbl = den_var.split("_")[0]
    if row is None:
        nf = f"GEO_ID not present in ACS {PERIOD} summary file table {tbl}"
        w.add(b, metric, None, "pct", "not_found", notes=nf)
        w.add(b, metric + "_moe", None, "pct", "not_found", notes=nf)
        return
    g = lambda v, k: num(row.get(v.replace("_", f"_{k}", 1)))
    ests = [g(v, "E") for v in num_vars]
    den = g(den_var, "E")
    method = (f"estimate = ({' + '.join(num_vars)}) / {den_var} x 100 from ACS {PERIOD}; "
              f"{desc}")
    if den is None or den in EST_CODES or any(x is None or x in EST_CODES for x in ests):
        w.add(b, metric, None, "pct", "not_found", notes="component estimate unavailable")
        w.add(b, metric + "_moe", None, "pct", "not_found", notes="component estimate unavailable")
        return
    pop = f"{den_var} = {den} ({pop_desc}), ACS {PERIOD}"
    if den == 0:
        w.add(b, metric, None, "pct", "not_found", pop=pop, notes="denominator is 0")
        w.add(b, metric + "_moe", None, "pct", "not_found", pop=pop, notes="denominator is 0")
        return
    numer = sum(ests)
    p = numer / den
    w.add(b, metric, round(100 * p, 2), "pct", "estimate", method=method, pop=pop)
    moes = [moe_val(g(v, "M")) for v in num_vars]
    mden = moe_val(g(den_var, "M"))
    if any(x is None for x in moes) or mden is None:
        w.add(b, metric + "_moe", None, "pct", "not_found", pop=pop,
              notes="a component MOE is unavailable, so no derived MOE")
        return
    mnum = math.sqrt(sum(x * x for x in moes))
    rad = mnum ** 2 - (p ** 2) * mden ** 2
    formula = "proportion"
    if rad < 0:
        rad = mnum ** 2 + (p ** 2) * mden ** 2
        formula = "ratio (proportion radicand negative)"
    mp = math.sqrt(rad) / den
    w.add(b, metric + "_moe", round(100 * mp, 2), "pct", "estimate", pop=pop,
          method=("derived 90% MOE per ACS General Handbook ch.8: MOE_num = sqrt(sum of squared "
                  f"component MOEs); MOE_p = sqrt(MOE_num^2 - p^2 x MOE_den^2)/den, {formula} formula used; "
                  "controlled MOEs treated as 0; approximation"))


def main():
    areas = load_areas()
    per_area = {a["id"]: area_geos(a) for a in areas}
    wanted = {gid for gs in per_area.values() for _, gid, _ in gs}
    print(f"{len(areas)} areas, {len(wanted)} distinct geographies")
    tables, metas = build_extracts(wanted)
    names = {gid: r.get("NAME", "") for gid, r in tables["geos"].items()}
    w = Writer(metas)

    for a in areas:
        for label, gid, role in per_area[a["id"]]:
            name = names.get(gid, "")
            if gid not in names:
                role += f"; GEO_ID {gid} not in Geos{YEAR}5YR.txt"
            T = {t: tables[t].get(gid) for t in TABLES}

            def B(domain, t):
                return w.base(a, domain, t, label, role, name)

            # --- rent
            b = B("rent", "b25031")
            w.direct(b, T["b25031"], "B25031_002", "acs_median_gross_rent_studio", "usd_month",
                     "median gross rent, no bedroom")
            w.direct(b, T["b25031"], "B25031_003", "acs_median_gross_rent_1br", "usd_month",
                     "median gross rent, 1 bedroom")
            w.direct(b, T["b25031"], "B25031_001", "acs_median_gross_rent_all_bedrooms", "usd_month",
                     "median gross rent, all bedroom counts (B25031 total)")
            w.direct(B("rent", "b25064"), T["b25064"], "B25064_001", "acs_median_gross_rent",
                     "usd_month", "median gross rent (B25064)")

            # --- people
            w.direct(B("people", "b01002"), T["b01002"], "B01002_001", "acs_median_age", "years",
                     "median age, total population")
            b = B("people", "b01001")
            w.direct(b, T["b01001"], "B01001_001", "acs_total_population", "count",
                     "total population")
            share(b, w, T["b01001"],
                  ["B01001_011", "B01001_012", "B01001_013", "B01001_035", "B01001_036", "B01001_037"],
                  "B01001_001", "acs_share_age_25_39",
                  "numerator = male + female 25-29, 30-34, 35-39", "total population")
            b = B("people", "b11001")
            w.direct(b, T["b11001"], "B11001_001", "acs_households", "count", "total households")
            share(b, w, T["b11001"], ["B11001_008"], "B11001_001", "acs_one_person_households_share",
                  "householder living alone / total households", "total households")
            b = B("people", "b25003")
            w.direct(b, T["b25003"], "B25003_001", "acs_occupied_units", "count",
                     "occupied housing units")
            share(b, w, T["b25003"], ["B25003_003"], "B25003_001", "acs_renter_share",
                  "renter-occupied / occupied housing units", "occupied housing units")
            b = B("people", "b25002")
            w.direct(b, T["b25002"], "B25002_001", "acs_housing_units", "count",
                     "total housing units (B25002)")
            share(b, w, T["b25002"], ["B25002_003"], "B25002_001", "acs_vacancy_rate",
                  "vacant / total housing units; includes seasonal and for-sale vacancies, not a rental vacancy rate",
                  "housing units")
            b = B("people", "b25034")
            for i, k in enumerate(YB_BUCKETS):
                lab = YB_LABEL.get(k, k.replace("_", " to "))
                share(b, w, T["b25034"], [f"B25034_{i + 2:03d}"], "B25034_001",
                      f"acs_units_built_{k}_share", f"housing units built {lab} / all housing units",
                      "housing units")
            w.direct(B("people", "b25035"), T["b25035"], "B25035_001", "acs_median_year_built",
                     "year", "median year structure built, all housing units")
            b = B("people", "b25036")
            w.direct(b, T["b25036"], "B25036_013", "acs_renter_occupied_units", "count",
                     "renter-occupied housing units (B25036)")
            for i, k in enumerate(YB_BUCKETS):
                lab = YB_LABEL.get(k, k.replace("_", " to "))
                share(b, w, T["b25036"], [f"B25036_{i + 14:03d}"], "B25036_013",
                      f"acs_renter_units_built_{k}_share",
                      f"renter-occupied units built {lab} / all renter-occupied units",
                      "renter-occupied housing units")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        cw = csv.DictWriter(f, fieldnames=COLS)
        cw.writeheader()
        cw.writerows(w.rows)
    from collections import Counter
    print(f"wrote {len(w.rows)} rows to {OUT.relative_to(ROOT)}")
    print(Counter((r["domain"], r["value_type"]) for r in w.rows))


if __name__ == "__main__":
    main()
