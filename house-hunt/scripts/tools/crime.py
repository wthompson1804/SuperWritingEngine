"""Lookup tool, domain `crime`.

Public functions (each returns a dict of values plus provenance; unknown is `not_found` with a reason):

  agency_rates(lat, lon)            police agency covering the point + 3 years of counts and rates per 1,000
  incidents_near(lat, lon, radius_m=250)   NYPD complaint counts around a point (NYC only)
  nyc_baseline(radius_m=250)        median / 80th percentile of the same counts over a grid of residential points

Sources are kept separate (never blended into one number):
  ny_dcjs         NY DCJS "Index Crimes by County and Agency" (data.ny.gov ca8h-8gjq), county population from
                  DCJS "Index, Violent, Property and Firearm Rates by County" (34dd-6g2j)
  fbi_cde         FBI Crime Data Explorer API, summarized agency data (counts and the population the FBI uses)
  nypd_complaints NYPD Complaint Data Historic (NYC Open Data qgea-i56i) aggregated by precinct, with precinct
                  population from 2020 Census blocks (PL 94-171) inside the precinct polygon (y76i-bdw7)

Build steps (idempotent, cached, resumable):
  python3 scripts/tools/crime.py --build            everything that is missing
  python3 scripts/tools/crime.py --build-agencies   data/reference/crime_agencies.csv + crime_place_agency.csv
  python3 scripts/tools/crime.py --build-incidents  raw/big/crime/nypd_incidents.npz
  python3 scripts/tools/crime.py --build-baseline   raw/big/crime/nyc_baseline_r250.json + data/reference csv
  python3 scripts/tools/crime.py                    self-test for the six contract points
"""
from __future__ import annotations

import csv
import io
import json
import math
import pickle
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lib  # noqa: E402
from lib import DATA, RAW, ROOT, USER_AGENT, cached_get, get_json, now_iso  # noqa: E402

# robots.txt: data.cityofnewyork.us and data.ny.gov set Crawl-delay: 1. api.usa.gov has no robots.txt and
# answers with X-Ratelimit-Limit: 10; we stay at about 3 requests/second.
lib.HOST_DELAY["data.cityofnewyork.us"] = 1.0
lib.HOST_DELAY["data.ny.gov"] = 1.0
lib.HOST_DELAY["api.usa.gov"] = 0.3
lib.HOST_DELAY["www2.census.gov"] = 1.0

BIG = RAW / "big" / "crime"
REF = DATA / "reference"
AGENCIES_CSV = REF / "crime_agencies.csv"
MAP_CSV = REF / "crime_place_agency.csv"
BASELINE_CSV = REF / "crime_nyc_baseline.csv"
GRID_CSV = REF / "search_grid.csv"
GEO_PKL = BIG / "geo_index.pkl"
INC_NPZ = BIG / "nypd_incidents.npz"
INC_META = BIG / "nypd_incidents.meta.json"

SODA_NYC = "https://data.cityofnewyork.us/resource"
HIST, CURR = "qgea-i56i", "5uac-w243"
HIST_PAGE = "https://data.cityofnewyork.us/Public-Safety/NYPD-Complaint-Data-Historic/qgea-i56i"
CURR_PAGE = "https://data.cityofnewyork.us/Public-Safety/NYPD-Complaint-Data-Current-Year-To-Date-/5uac-w243"
PRECINCTS_URL = "https://data.cityofnewyork.us/resource/y76i-bdw7.geojson"
DCJS_URL = "https://data.ny.gov/resource/ca8h-8gjq.json"
DCJS_PAGE = "https://data.ny.gov/Public-Safety/Index-Crimes-by-County-and-Agency-Beginning-1990/ca8h-8gjq"
DCJS_RATES_URL = "https://data.ny.gov/resource/34dd-6g2j.json"
FBI = "https://api.usa.gov/crime/fbi/cde"
FBI_PAGE = "https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/explorer/crime/crime-trend"
TIGER = "https://www2.census.gov/geo/tiger/TIGER2024/{kind}/tl_2024_{st}_{k}.zip"
PL_URL = ("https://www2.census.gov/programs-surveys/decennial/2020/data/"
          "01-Redistricting_File--PL_94-171/New_York/ny2020.pl.zip")
BLOCKS_CACHE = RAW / "census_pl2020" / "nyc_blocks_pop.csv"

STATES = {"36": "NY", "34": "NJ", "09": "CT", "42": "PA"}
NYC_COUNTIES = {"36005": "Bronx", "36047": "Kings", "36061": "New York", "36081": "Queens", "36085": "Richmond"}
# County (or CT planning region) names for the FIPS codes the search grid can touch. Static Census facts.
COUNTY_NAMES = {
    "36005": "Bronx", "36027": "Dutchess", "36047": "Kings", "36059": "Nassau", "36061": "New York",
    "36071": "Orange", "36079": "Putnam", "36081": "Queens", "36085": "Richmond", "36087": "Rockland",
    "36103": "Suffolk", "36105": "Sullivan", "36111": "Ulster", "36119": "Westchester", "36021": "Columbia",
    "36039": "Greene", "36025": "Delaware",
    "34001": "Atlantic", "34003": "Bergen", "34005": "Burlington", "34007": "Camden", "34013": "Essex",
    "34017": "Hudson", "34019": "Hunterdon", "34021": "Mercer", "34023": "Middlesex", "34025": "Monmouth",
    "34027": "Morris", "34029": "Ocean", "34031": "Passaic", "34035": "Somerset", "34037": "Sussex",
    "34039": "Union", "34041": "Warren",
    "42017": "Bucks", "42089": "Monroe", "42095": "Northampton", "42077": "Lehigh", "42091": "Montgomery",
    "42101": "Philadelphia", "42103": "Pike",
    "09110": "Capitol", "09120": "Greater Bridgeport", "09130": "Lower Connecticut River Valley",
    "09140": "Naugatuck Valley", "09150": "Northeastern Connecticut", "09160": "Northwest Hills",
    "09170": "South Central Connecticut", "09180": "Southeastern Connecticut", "09190": "Western Connecticut",
}

OFFENSES = ["violent", "property", "motor_vehicle_theft", "burglary", "larceny"]
FBI_CODES = {"violent": "V", "property": "P", "motor_vehicle_theft": "motor-vehicle-theft",
             "burglary": "burglary", "larceny": "larceny"}

AG_COLS = ["agency_id", "ori", "state", "county", "agency_name", "agency_type", "geography", "source", "year",
           "months_reported", "violent", "property", "motor_vehicle_theft", "burglary", "larceny",
           "population", "population_source", "population_value_type",
           "violent_per_1000", "property_per_1000", "motor_vehicle_theft_per_1000", "burglary_per_1000",
           "larceny_per_1000", "rate_value_type", "rate_method", "source_url", "retrieved_at", "notes"]
MAP_COLS = ["state", "county_fips", "county", "geo_type", "geoid", "geo_name", "agency_name", "dcjs_agency",
            "ori", "mapping_basis", "mapping_note", "source_url"]

# ------------------------------------------------------------------ NYPD complaint categories
# Exact values in the NYPD complaint datasets (ky_cd / ofns_desc, pd_cd / pd_desc), checked 2026-11-15.
INCIDENT_CATS = {
    "grand_larceny_motor_vehicle": {
        "field": "ky_cd", "codes": [110],
        "desc": "ofns_desc 'GRAND LARCENY OF MOTOR VEHICLE' (ky_cd 110): pd_desc 'LARCENY,GRAND OF AUTO' (441), "
                "'LARCENY, GRAND OF AUTO - ATTEM' (442), 'LARCENY, GRAND OF MOPED' (450), "
                "'LARCENY,GRAND OF MOTORCYCLE' (451), 'LARCENY,GRAND OF TRUCK' (455)"},
    "glmv_car_or_truck_only": {
        "field": "pd_cd", "codes": [441, 442, 455],
        "desc": "subset of grand larceny of motor vehicle without mopeds and motorcycles: pd_cd 441, 442, 455"},
    "theft_from_vehicle": {
        "field": "pd_cd", "codes": [321, 421],
        "desc": "pd_desc 'LARCENY,PETIT FROM AUTO' (pd_cd 321, ofns_desc PETIT LARCENY) and "
                "'LARCENY,GRAND FROM VEHICLE/MOTORCYCLE' (pd_cd 421, ofns_desc GRAND LARCENY)"},
    "vehicle_parts_theft": {
        "field": "pd_cd", "codes": [357, 457],
        "desc": "pd_desc 'LARCENY,PETIT OF VEHICLE ACCES' (357) and "
                "'LARCENY,GRAND OF VEHICULAR/MOTORCYCLE ACCESSORIES' (457): wheels, catalytic converters, plates"},
    "vehicle_criminal_mischief": {
        "field": "pd_cd", "codes": [254],
        "desc": "pd_desc 'MISCHIEF, CRIMINAL 4, OF MOTOR' (254, ofns_desc CRIMINAL MISCHIEF & RELATED OF): "
                "damage to a vehicle, includes break-in damage with nothing taken"},
    "robbery": {"field": "ky_cd", "codes": [105], "desc": "ofns_desc 'ROBBERY' (ky_cd 105)"},
    "felony_assault": {"field": "ky_cd", "codes": [106], "desc": "ofns_desc 'FELONY ASSAULT' (ky_cd 106)"},
    "burglary": {"field": "ky_cd", "codes": [107], "desc": "ofns_desc 'BURGLARY' (ky_cd 107), all premises"},
}
SLICE_KY = [105, 106, 107, 110]
SLICE_PD = [254, 321, 357, 421, 457]
SLICE_START = "2023-01-01"
EPOCH = date(1970, 1, 1)


def rel(p) -> str:
    p = Path(p)
    return str(p.relative_to(ROOT)) if p.is_absolute() else str(p)


def _num(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


# ================================================================== geography index
def _download(url: str, path: Path) -> None:
    import requests
    path.parent.mkdir(parents=True, exist_ok=True)
    lib._throttle(url.split("/")[2])
    with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=300) as r:
        r.raise_for_status()
        tmp = path.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(path)
    with open(path.parent / "_index.jsonl", "a") as f:
        f.write(json.dumps({"url": url, "retrieved_at": now_iso(), "status": 200, "path": rel(path)}) + "\n")


def build_geo(force: bool = False) -> None:
    """Census TIGER/Line 2024 places and county subdivisions for the counties that hold a search-grid ZIP,
    plus NYPD precinct polygons, saved as one pickle of WKB geometries."""
    if GEO_PKL.exists() and not force:
        return
    import geopandas as gpd
    import pandas as pd
    tdir = BIG / "tiger"
    frames = {"place": [], "cousub": []}
    for st in STATES:
        for k in ("place", "cousub"):
            p = tdir / f"tl_2024_{st}_{k}.zip"
            if not p.exists():
                _download(TIGER.format(kind=k.upper(), st=st, k=k), p)
            frames[k].append(gpd.read_file(p))
    cs = pd.concat(frames["cousub"], ignore_index=True)
    pl = pd.concat(frames["place"], ignore_index=True)
    cs["cty"] = cs.STATEFP + cs.COUNTYFP
    g = pd.read_csv(GRID_CSV, dtype={"zcta": str})
    pts = gpd.GeoDataFrame(g, geometry=gpd.points_from_xy(g.lon, g.lat), crs=cs.crs)
    j = gpd.sjoin(pts, cs[["cty", "geometry"]], predicate="within", how="left")
    counties = sorted(set(j.cty.dropna()) | set(NYC_COUNTIES))
    missing = [c for c in counties if c not in COUNTY_NAMES]
    if missing:
        raise RuntimeError(f"add county names for FIPS {missing} to COUNTY_NAMES")
    cs = cs[cs.cty.isin(counties) & (cs.ALAND > 0)].reset_index(drop=True)
    # county of each place = county of the county subdivision holding its representative point
    reps = gpd.GeoDataFrame(pl[["GEOID"]], geometry=pl.geometry.representative_point(), crs=pl.crs)
    pj = gpd.sjoin(reps, cs[["cty", "geometry"]], predicate="within", how="inner")
    pl = pl.merge(pj[["GEOID", "cty"]].drop_duplicates("GEOID"), on="GEOID", how="inner").reset_index(drop=True)
    gj, pmeta = get_json(PRECINCTS_URL, "nyc_open_data", params={"$limit": 200})
    from shapely.geometry import shape
    out = {
        "built_at": now_iso(), "counties": counties,
        "tiger_url": "https://www2.census.gov/geo/tiger/TIGER2024/",
        "precinct_url": pmeta["url"], "precinct_retrieved_at": pmeta["retrieved_at"],
        "cousub": [dict(geoid=r.GEOID, name=r.NAME, namelsad=r.NAMELSAD, cty=r.cty, wkb=r.geometry.wkb)
                   for r in cs.itertuples()],
        "place": [dict(geoid=r.GEOID, name=r.NAME, namelsad=r.NAMELSAD, cty=r.cty, classfp=r.CLASSFP,
                       wkb=r.geometry.wkb) for r in pl.itertuples()],
        "precinct": [dict(precinct=int(float(ft["properties"]["precinct"])), wkb=shape(ft["geometry"]).wkb)
                     for ft in gj["features"]],
    }
    GEO_PKL.parent.mkdir(parents=True, exist_ok=True)
    with open(GEO_PKL, "wb") as f:
        pickle.dump(out, f)
    print(f"geo index: {len(out['cousub'])} county subdivisions, {len(out['place'])} places, "
          f"{len(out['precinct'])} precincts, {len(counties)} counties")


class _Geo:
    def __init__(self):
        build_geo()
        import shapely
        from shapely.strtree import STRtree
        with open(GEO_PKL, "rb") as f:
            d = pickle.load(f)
        self.meta = {k: d[k] for k in ("built_at", "counties", "tiger_url", "precinct_url", "precinct_retrieved_at")}
        self.layers = {}
        for k in ("cousub", "place", "precinct"):
            geoms = shapely.from_wkb([r["wkb"] for r in d[k]])
            for r in d[k]:
                r.pop("wkb")
            self.layers[k] = (STRtree(geoms), geoms, d[k])

    def find(self, layer: str, lat: float, lon: float):
        import shapely
        tree, geoms, recs = self.layers[layer]
        pt = shapely.Point(lon, lat)
        hits = tree.query(pt, predicate="intersects")
        return recs[int(hits[0])] if len(hits) else None


@lru_cache(maxsize=1)
def _geo() -> _Geo:
    return _Geo()


def locate(lat: float, lon: float) -> dict:
    """Census place / county subdivision / NYPD precinct of a point (TIGER 2024, y76i-bdw7)."""
    g = _geo()
    cs = g.find("cousub", lat, lon)
    pl = g.find("place", lat, lon)
    pc = g.find("precinct", lat, lon)
    cty = cs["cty"] if cs else None
    return {"state": STATES.get(cty[:2]) if cty else None, "county_fips": cty,
            "county": COUNTY_NAMES.get(cty) if cty else None,
            "cousub": cs, "place": pl, "precinct": pc["precinct"] if pc else None}


# ================================================================== name normalisation
_TYPE_WORDS = {"township": "township", "twp": "township", "borough": "borough", "boro": "borough",
               "city": "city", "town": "town", "village": "village", "vg": "village",
               "municipality": "municipality"}


def _base(s: str) -> str:
    s = s.lower().replace("&", " and ").replace("-", " ")
    s = re.sub(r"[.'’]", "", s)
    s = re.sub(r"\bst\b", "saint", s)
    s = re.sub(r"\bmt\b", "mount", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_census(namelsad: str) -> tuple[str, str | None]:
    """'Lynbrook village' -> ('lynbrook', 'village'); 'Princeton' -> ('princeton', None)."""
    t = namelsad.strip().split()
    typ = _TYPE_WORDS.get(t[-1].lower()) if len(t) > 1 else None
    if typ:
        t = t[:-1]
    b = _base(" ".join(t))
    b = re.sub(r"^(city|township|town|village|borough) of ", "", b)
    b = re.sub(r" (village|town)$", "", b) if typ == "township" else b  # 'South Orange Village township'
    return b, typ


def norm_fbi(name: str) -> tuple[str, str | None]:
    """'Springfield Township Police Department, Union County' -> ('springfield', 'township')."""
    n = re.sub(r",.*$", "", name)
    n = re.sub(r"\s+(Police Department|Department of Police|Police|Public Safety Department|"
               r"Department of Public Safety|Police District)$", "", n.strip(), flags=re.I)
    t = n.split()
    typ = _TYPE_WORDS.get(t[-1].lower()) if len(t) > 1 else None
    if typ:
        t = t[:-1]
    return _base(" ".join(t)), typ


def norm_dcjs(name: str) -> tuple[str, str | None]:
    """'Lynbrook Vg PD' -> ('lynbrook', 'village'); 'Nassau County PD' -> ('nassau', 'county')."""
    n = re.sub(r"\s+(PD|Police District)$", "", name.strip())
    t = n.split()
    low = t[-1].lower() if t else ""
    typ = _TYPE_WORDS.get(low) or ("county" if low == "county" else None)
    if typ and len(t) > 1:
        t = t[:-1]
    else:
        typ = None
    return _base(" ".join(t)), typ


# ================================================================== source pulls for the agency table
def _precinct_name(p: int) -> str:
    special = {14: "Midtown South Precinct", 18: "Midtown North Precinct", 22: "Central Park Precinct"}
    if p in special:
        return f"NYPD {special[p]} ({p})"
    suf = "th" if 10 <= p % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(p % 10, "th")
    return f"NYPD {p}{suf} Precinct"


def _boro_of_precinct(p: int) -> str:
    return ("Manhattan" if p <= 34 else "Bronx" if p <= 52 else "Brooklyn" if p <= 94
            else "Queens" if p <= 115 else "Staten Island")


def load_blocks():
    """[(geoid, lat, lon, pop)] for NYC 2020 Census blocks (cache built by scripts/p1_safety_nyc.py)."""
    if not BLOCKS_CACHE.exists():
        sys.path.insert(0, str(ROOT / "scripts"))
        import p1_safety_nyc
        p1_safety_nyc.load_blocks()
    with open(BLOCKS_CACHE) as f:
        return [(r["geoid"], float(r["lat"]), float(r["lon"]), int(r["pop"])) for r in csv.DictReader(f)]


def precinct_pops() -> dict[int, int]:
    import shapely
    g = _geo()
    tree, geoms, recs = g.layers["precinct"]
    blocks = load_blocks()
    pts = shapely.points([b[2] for b in blocks], [b[1] for b in blocks])
    pi, gi = tree.query(pts, predicate="intersects")
    pops, seen = defaultdict(int), set()
    for a, b in zip(pi.tolist(), gi.tolist()):
        if a in seen:
            continue
        seen.add(a)
        pops[recs[b]["precinct"]] += blocks[a][3]
    return pops


def nypd_precinct_rows() -> list[dict]:
    """NYPD complaints (historic, by report year) aggregated by precinct into UCR-like groups."""
    kys = "'101','104','105','106','107','109','110','341'"
    params = {"$select": "addr_pct_cd, date_extract_y(rpt_dt) as y, ky_cd, count(*) as n",
              "$where": f"rpt_dt >= '2023-01-01T00:00:00' and rpt_dt <= '2025-12-31T23:59:59' and ky_cd in ({kys})",
              "$group": "addr_pct_cd, y, ky_cd", "$limit": 50000}
    data, meta = get_json(f"{SODA_NYC}/{HIST}.json", "nyc_open_data", params=params)
    agg = defaultdict(lambda: defaultdict(int))
    for r in data:
        p = _num(r.get("addr_pct_cd"))
        if p is None or p <= 0:
            continue
        agg[(p, int(r["y"]))][r["ky_cd"]] += int(r["n"])
    pops = precinct_pops()
    rows = []
    for (p, y), k in sorted(agg.items()):
        if p not in pops and p not in {r["precinct"] for r in _geo().layers["precinct"][2]}:
            continue
        pop = pops.get(p, 0)
        c = {"violent": k["101"] + k["104"] + k["105"] + k["106"],
             "property": k["107"] + k["109"] + k["341"] + k["110"],
             "motor_vehicle_theft": k["110"], "burglary": k["107"], "larceny": k["109"] + k["341"]}
        row = dict(agency_id=f"NYPD:{p}", ori="", state="NY", county=_boro_of_precinct(p),
                   agency_name=_precinct_name(p), agency_type="NYPD precinct",
                   geography=f"{_precinct_name(p)}, {_boro_of_precinct(p)}: one of 78 NYPD precincts",
                   source="nypd_complaints", year=y, months_reported=12, **c,
                   population=pop if pop >= 1000 else "",
                   population_source=("2020 Census PL 94-171 block population (P1_001N) of blocks whose internal "
                                      "point lies inside the precinct polygon (NYC Open Data y76i-bdw7); " + PL_URL),
                   population_value_type="estimate" if pop >= 1000 else "not_found",
                   rate_value_type="estimate" if pop >= 1000 else "not_found",
                   rate_method="count / precinct residents (2020 Census) * 1000",
                   source_url=meta["url"], retrieved_at=meta["retrieved_at"],
                   notes=("Complaints by report year (rpt_dt). violent = ky_cd 101 murder + 104 rape + 105 robbery + "
                          "106 felony assault; property = 107 burglary + 109 grand larceny + 341 petit larceny + "
                          "110 grand larceny of motor vehicle; larceny = 109 + 341. NY Penal Law categories, close "
                          "to but not identical with FBI UCR definitions."
                          + ("" if pop >= 1000 else f" Precinct has {pop} residents: no residential rate.")))
        for o in OFFENSES:
            row[f"{o}_per_1000"] = round(c[o] / pop * 1000, 2) if pop >= 1000 else ""
        rows.append(row)
    return rows


def dcjs_rows(county_names: list[str]) -> tuple[list[dict], list[int]]:
    """DCJS index crimes for the given counties, latest three years in the dataset."""
    mx, _ = get_json(DCJS_URL, "ny_dcjs", params={"$select": "max(year) as y"})
    y1 = int(mx[0]["y"])
    years = [y1 - 2, y1 - 1, y1]
    inlist = ",".join("'" + c + "'" for c in county_names)
    data, meta = get_json(DCJS_URL, "ny_dcjs", params={
        "$where": f"year >= {years[0]} and county in ({inlist})", "$limit": 50000, "$order": "county,agency,year"})
    pops, pmeta = get_json(DCJS_RATES_URL, "ny_dcjs", params={
        "$where": f"year >= {years[0]} and county in ({inlist})", "$limit": 5000})
    cpop = {(r["county"], int(r["year"])): _num(r.get("population")) for r in pops}
    rows = []
    for r in data:
        y = int(r["year"])
        is_total = r["agency"] == "County Total"
        pop = cpop.get((r["county"], y)) if is_total else None
        c = {"violent": _num(r.get("violent")), "property": _num(r.get("property")),
             "motor_vehicle_theft": _num(r.get("motor_vehicle_theft")), "burglary": _num(r.get("burglary")),
             "larceny": _num(r.get("larceny"))}
        row = dict(agency_id=f"DCJS:{r['county']}:{r['agency']}", ori="", state="NY", county=r["county"],
                   agency_name=r["agency"] if not is_total else f"{r['county']} County, all agencies",
                   agency_type="county total" if is_total else "agency", geography="",
                   source="ny_dcjs", year=y, months_reported=r.get("months_reported", ""), **c,
                   population=pop or "",
                   population_source=(f"DCJS county population, {DCJS_RATES_URL}" if pop else ""),
                   population_value_type="found" if pop else "not_found",
                   rate_value_type="estimate" if pop else "not_found",
                   rate_method="DCJS count / DCJS county population * 1000" if pop else "",
                   source_url=f"{DCJS_URL}?county={r['county'].replace(' ', '%20')}&year={y}",
                   retrieved_at=meta["retrieved_at"], notes="")
        for o in OFFENSES:
            row[f"{o}_per_1000"] = round(c[o] / pop * 1000, 2) if pop and c[o] is not None else ""
        rows.append(row)
    return rows, years


def fbi_agency_lists() -> dict[str, list[dict]]:
    out = {}
    for st in STATES.values():
        d, meta = get_json(f"{FBI}/agency/byStateAbbr/{st}", "fbi_cde")
        out[st] = [dict(a, county_key=k, _retrieved_at=meta["retrieved_at"]) for k, v in d.items() for a in v]
    return out


def fbi_latest_full_year() -> int:
    d, _ = get_json(f"{FBI}/summarized/agency/NY0290000/burglary", "fbi_cde",
                    params={"from": "01-2025", "to": "12-2025"})
    mm, yy = d["cde_properties"]["max_data_date"]["UCR"].split("/")
    return int(yy) if int(mm) == 12 else int(yy) - 1


def fbi_agency_years(ori: str, years: list[int]) -> tuple[dict, dict]:
    """{year: {offense: count, 'population': n, 'months': n}} for one agency, from five summarized calls."""
    res = {y: {} for y in years}
    meta_last = {}
    for off, code in FBI_CODES.items():
        url = f"{FBI}/summarized/agency/{ori}/{code}"
        try:
            d, meta = get_json(url, "fbi_cde", params={"from": f"01-{years[0]}", "to": f"12-{years[-1]}"})
        except RuntimeError as e:
            for y in years:
                res[y][off] = None
            meta_last = {"url": url, "retrieved_at": now_iso(), "error": str(e)[:120]}
            continue
        meta_last = meta
        act = (d.get("offenses") or {}).get("actuals") or {}
        series = next((v for k, v in act.items() if k.endswith(" Offenses")), None)
        popd = ((d.get("populations") or {}).get("population") or {})
        pser = next((v for k, v in popd.items() if (k + " Offenses") in act), None)
        for y in years:
            months = {k: v for k, v in (series or {}).items() if k.endswith(f"-{y}") and v is not None}
            res[y][off] = sum(months.values()) if months else None
            if off == "property":
                res[y]["zero_property_months"] = sum(1 for v in months.values() if v == 0)
            res[y]["months"] = max(res[y].get("months", 0), len(months))
            if pser:
                pv = [v for k, v in pser.items() if k.endswith(f"-{y}") and v]
                if pv:
                    res[y]["population"] = int(pv[0])
    return res, meta_last


def fbi_population(ori: str, year: int) -> int | None:
    """Agency population the FBI CDE lists for one year (one summarized call)."""
    try:
        d, _ = get_json(f"{FBI}/summarized/agency/{ori}/burglary", "fbi_cde",
                        params={"from": f"01-{year}", "to": f"12-{year}"})
    except RuntimeError:
        return None
    act = (d.get("offenses") or {}).get("actuals") or {}
    popd = ((d.get("populations") or {}).get("population") or {})
    pser = next((v for k, v in popd.items() if (k + " Offenses") in act), None)
    pv = [v for v in (pser or {}).values() if v]
    return int(pv[0]) if pv else None


def fbi_rows(agencies: list[dict], years: list[int], progress: bool = True) -> list[dict]:
    rows = []
    t0 = time.time()
    for i, a in enumerate(agencies):
        res, meta = fbi_agency_years(a["ori"], years)
        for y in years:
            r = res[y]
            pop = r.get("population")
            months = r.get("months", 0)
            c = {o: r.get(o) for o in OFFENSES}
            have = any(v is not None for v in c.values())
            all_zero = have and months == 12 and bool(pop) and pop > 3000 and all(v == 0 for v in c.values())
            zpm = r.get("zero_property_months", 0)
            ok_rate = bool(pop) and have and months == 12 and not all_zero
            note = ""
            if not have:
                note = "No monthly data returned by the FBI CDE for this agency and year."
            elif months < 12:
                note = f"Only {months} months of data in the FBI CDE for this year: counts are partial, no rate."
            elif not pop:
                note = "FBI CDE lists no population for this agency (zero-population or overlapping agency)."
            elif all_zero:
                note = ("FBI CDE shows zero for every offence in all 12 months for a population of "
                        f"{pop:,}: treated as not reported to the FBI, no rate.")
            elif zpm >= 3 and pop > 10000:
                note = (f"{zpm} of 12 months show zero property crimes for a population of {pop:,}: "
                        "possibly incomplete reporting to the FBI for this year.")
            row = dict(agency_id=a["ori"], ori=a["ori"], state=a["state_abbr"], county=a["county_key"].title(),
                       agency_name=a["agency_name"], agency_type=a["agency_type_name"], geography="",
                       source="fbi_cde", year=y, months_reported=months,
                       **{o: ("" if c[o] is None else c[o]) for o in OFFENSES},
                       population=pop or "", population_source="FBI CDE agency population" if pop else "",
                       population_value_type="found" if pop else "not_found",
                       rate_value_type="estimate" if ok_rate else "not_found",
                       rate_method="FBI CDE count / FBI CDE agency population * 1000" if ok_rate else "",
                       source_url=f"{FBI}/summarized/agency/{a['ori']}/{{V|P|motor-vehicle-theft|burglary|larceny}}"
                                  f"?from=01-{years[0]}&to=12-{years[-1]}",
                       retrieved_at=meta.get("retrieved_at", ""), notes=note)
            for o in OFFENSES:
                row[f"{o}_per_1000"] = round(c[o] / pop * 1000, 2) if ok_rate and c[o] is not None else ""
            rows.append(row)
        if progress and (i + 1) % 50 == 0:
            print(f"  fbi {i + 1}/{len(agencies)} agencies, {time.time() - t0:.0f}s", flush=True)
    return rows


# ================================================================== place -> agency mapping
# Hand-entered links where names do not line up. Each is my inference (see docs/tools_notes/crime.md).
DCJS_FBI_ALIASES = {  # (county, DCJS agency) -> FBI agency name
    ("Nassau", "Port Washington Police District"): "Port Washington Police Department",
    ("Westchester", "Westchester Co Dept Pub Safety"): "Westchester Public Safety County Sheriff's Office",
}
# Census place (NAMELSAD, county) -> DCJS agency, where the police agency is a special district.
NY_PLACE_OVERRIDES = {
    ("Port Washington CDP", "Nassau"): "Port Washington Police District",
    ("Baxter Estates village", "Nassau"): "Port Washington Police District",
    ("Manorhaven village", "Nassau"): "Port Washington Police District",
    ("Port Washington North village", "Nassau"): "Port Washington Police District",
}
NY_OVERRIDE_NOTE = ("Inference, not from a fetched table: the Port Washington Police District is a special district "
                    "covering unincorporated Port Washington and the villages of Baxter Estates, Manorhaven and "
                    "Port Washington North. Verify before relying on it.")
NY_COUNTY_PD = {"Nassau": "Nassau County PD", "Suffolk": "Suffolk County PD"}
# Suffolk County PD's police district is the five western towns; the east-end towns have town departments.
SUFFOLK_PD_TOWNS = {"babylon", "brookhaven", "huntington", "islip", "smithtown"}


def build_mapping(geo: _Geo, dcjs: list[dict], fbi_list: dict[str, list[dict]]) -> tuple[list[dict], dict]:
    """Rows of crime_place_agency.csv and {(county, dcjs_agency): ori} for NY."""
    counties = geo.meta["counties"]
    _, _, cousubs = geo.layers["cousub"]
    _, _, places = geo.layers["place"]
    rows = []

    # ---- FBI agencies by (state, county, base, type)
    fbi_idx = defaultdict(list)
    for st, lst in fbi_list.items():
        for a in lst:
            if a["agency_type_name"] not in ("City", "County"):
                continue
            b, t = norm_fbi(a["agency_name"])
            for ck in a["county_key"].split(","):
                fbi_idx[(st, ck.strip().title())].append((b, t, a))

    def fbi_county_key(st, cty):
        name = COUNTY_NAMES[cty]
        return (st, name + " Planning Region") if st == "CT" else (st, name)

    # ---- NY: DCJS agency -> FBI ORI
    dcjs_ori = {}
    dcjs_agencies = sorted({(r["county"], r["agency_name"]) for r in dcjs if r["agency_type"] == "agency"})
    for county, ag in dcjs_agencies:
        cands = fbi_idx.get(("NY", county), [])
        alias = DCJS_FBI_ALIASES.get((county, ag))
        hit = None
        if alias:
            hit = next((a for _, _, a in cands if a["agency_name"] == alias), None)
        else:
            b, t = norm_dcjs(ag)
            if t == "county":
                hit = next((a for _, _, a in cands if a["agency_name"] == f"{county} County Police Department"), None)
            elif t:
                ex = [a for fb, ft, a in cands if fb == b and ft == t]
                nt = [a for fb, ft, a in cands if fb == b and ft is None]
                hit = ex[0] if len(ex) == 1 else (nt[0] if len(nt) == 1 and t == "city" else None)
                if hit is None and len(nt) == 1 and not ex:
                    hit = nt[0]
            elif ag.endswith("Sheriff"):
                hit = next((a for _, _, a in cands if a["agency_name"] == f"{county} County Sheriff's Office"), None)
        if hit:
            dcjs_ori[(county, ag)] = hit["ori"]

    # ---- NY outside NYC
    dc_idx = defaultdict(dict)
    for county, ag in dcjs_agencies:
        b, t = norm_dcjs(ag)
        if t in ("village", "city", "town"):
            dc_idx[county][(b, t)] = ag

    def ny_row(cty, geo_type, rec, ag, basis, note):
        county = COUNTY_NAMES[cty]
        rows.append(dict(state="NY", county_fips=cty, county=county, geo_type=geo_type, geoid=rec["geoid"],
                         geo_name=rec["namelsad"], agency_name=ag or "", dcjs_agency=ag or "",
                         ori=dcjs_ori.get((county, ag), "") if ag else "", mapping_basis=basis,
                         mapping_note=note, source_url=DCJS_PAGE))

    for rec in places:
        cty = rec["cty"]
        if not cty.startswith("36") or cty in NYC_COUNTIES:
            continue
        county = COUNTY_NAMES[cty]
        ov = NY_PLACE_OVERRIDES.get((rec["namelsad"], county))
        if ov:
            ny_row(cty, "place", rec, ov, "inference_manual", NY_OVERRIDE_NOTE)
            continue
        b, t = norm_census(rec["namelsad"])
        ag = dc_idx[county].get((b, t))
        if ag:
            ny_row(cty, "place", rec, ag, "name_match",
                   f"Census place '{rec['namelsad']}' matches DCJS agency '{ag}' in {county} County by name and type.")
    for rec in cousubs:
        cty = rec["cty"]
        if not cty.startswith("36") or cty in NYC_COUNTIES:
            continue
        county = COUNTY_NAMES[cty]
        b, t = norm_census(rec["namelsad"])
        ag = dc_idx[county].get((b, t))
        if ag and t == "city":
            ny_row(cty, "cousub", rec, ag, "name_match", f"City matches DCJS agency '{ag}' by name.")
        elif ag:
            ny_row(cty, "cousub", rec, ag, "inference_rule",
                   f"Inference: the point is in the Town of {rec['name']}, outside any village or city that has its "
                   f"own department in the DCJS list, so the town department '{ag}' is assumed. Some villages "
                   "without a department are instead patrolled by the county or State Police.")
        elif county in NY_COUNTY_PD and (county != "Suffolk" or b in SUFFOLK_PD_TOWNS):
            ny_row(cty, "cousub", rec, NY_COUNTY_PD[county], "inference_rule",
                   f"Inference: {rec['namelsad']} has no town department in the DCJS list and the point is outside "
                   f"any village or city with its own department, so {NY_COUNTY_PD[county]} is assumed. A few small "
                   "villages contract with a neighbouring village department instead.")
        else:
            ny_row(cty, "cousub", rec, None, "no_single_agency",
                   f"No town, village or county police department for {rec['namelsad']} in the DCJS list: patrolled "
                   f"by the {county} County Sheriff and/or New York State Police, which report county-wide totals "
                   "with no population. Use the county total.")

    # ---- NJ, CT, PA: county subdivision -> FBI agency by name
    for st_fips, st in (("34", "NJ"), ("09", "CT"), ("42", "PA")):
        by_cty = defaultdict(list)
        for rec in cousubs:
            if rec["cty"].startswith(st_fips):
                by_cty[rec["cty"]].append(rec)
        for cty, recs in by_cty.items():
            if st == "CT":   # town names are unique in Connecticut; FBI region keys can lag the Census ones
                cands = [x for (s, _), v in fbi_idx.items() if s == "CT" for x in v]
            else:
                cands = [x for (s, ck), v in fbi_idx.items() if s == st
                         and COUNTY_NAMES[cty] in [p.strip() for p in ck.split(",")] for x in v]
            cands = [x for x in cands if x[2]["agency_type_name"] == "City"]
            used = set()
            norm = {rec["geoid"]: norm_census(rec["namelsad"]) for rec in recs}
            assign = {}
            # pass 1: base and type both match
            for rec in recs:
                b, t = norm[rec["geoid"]]
                ex = [x for x in cands if x[0] == b and x[1] == t and x[1] is not None and x[2]["ori"] not in used]
                if len(ex) == 1:
                    assign[rec["geoid"]] = (ex[0][2], "name_match",
                                            f"FBI agency '{ex[0][2]['agency_name']}' matches the Census county "
                                            f"subdivision '{rec['namelsad']}' by name and type.")
                    used.add(ex[0][2]["ori"])
            # pass 2: base matches; FBI name carries no type (or a different one)
            for prefer_non_township in (True, False):
                for rec in recs:
                    if rec["geoid"] in assign:
                        continue
                    b, t = norm[rec["geoid"]]
                    if prefer_non_township and t == "township":
                        continue
                    ex = [x for x in cands if x[2]["ori"] not in used
                          and (x[0] == b or (x[1] and f"{x[0]} {x[1]}" == b))]
                    untyped = [x for x in ex if x[1] is None]
                    pick = untyped[0] if len(untyped) == 1 else (ex[0] if len(ex) == 1 else None)
                    if pick:
                        shared = sum(1 for v in norm.values() if v[0] == b) > 1
                        if shared:
                            assign[rec["geoid"]] = (pick[2], "name_match_base",
                                                    f"Inference: FBI agency '{pick[2]['agency_name']}' matched to "
                                                    f"'{rec['namelsad']}' on the base name; another municipality in "
                                                    "the county shares the name and the FBI name does not state "
                                                    "the municipal type.")
                        else:
                            assign[rec["geoid"]] = (pick[2], "name_match",
                                                    f"FBI agency '{pick[2]['agency_name']}' matches the only Census "
                                                    f"county subdivision of that name in the county "
                                                    f"('{rec['namelsad']}').")
                        used.add(pick[2]["ori"])
            for rec in recs:
                a = assign.get(rec["geoid"])
                rows.append(dict(
                    state=st, county_fips=cty, county=COUNTY_NAMES[cty], geo_type="cousub", geoid=rec["geoid"],
                    geo_name=rec["namelsad"], agency_name=a[0]["agency_name"] if a else "", dcjs_agency="",
                    ori=a[0]["ori"] if a else "", mapping_basis=a[1] if a else "no_agency_matched",
                    mapping_note=a[2] if a else (
                        f"No municipal police department named for '{rec['namelsad']}' in the FBI CDE agency list "
                        f"for {COUNTY_NAMES[cty]}: likely State Police, a regional department or a contract with a "
                        "neighbouring town. Not resolved."),
                    source_url=f"{FBI}/agency/byStateAbbr/{st}"))
    return rows, dcjs_ori


def build_agencies(force_fetch: bool = False) -> None:
    geo = _geo()
    counties = geo.meta["counties"]
    ny_counties = [COUNTY_NAMES[c] for c in counties if c.startswith("36")]
    print("NYPD precinct rows ...", flush=True)
    nypd = nypd_precinct_rows()
    print("DCJS rows ...", flush=True)
    dcjs, dcjs_years = dcjs_rows(ny_counties)
    fbi_list = fbi_agency_lists()
    map_rows, dcjs_ori = build_mapping(geo, dcjs, fbi_list)
    for r in dcjs:
        if r["agency_type"] == "agency":
            r["ori"] = dcjs_ori.get((r["county"], r["agency_name"]), "")

    # FBI agencies to pull: municipal and county agencies in the grid counties, plus NYPD citywide
    want = {}
    cnames = {st: set() for st in STATES.values()}
    for c in counties:
        st = STATES[c[:2]]
        cnames[st].add(COUNTY_NAMES[c].upper() + (" PLANNING REGION" if st == "CT" else ""))
    mapped = {r["ori"] for r in map_rows if r["ori"]} | set(dcjs_ori.values())
    for st, lst in fbi_list.items():
        for a in lst:
            keys = {k.strip() for k in a["county_key"].split(",")}
            in_cty = bool(keys & cnames[st])
            if a["ori"] in mapped or (in_cty and a["agency_type_name"] in ("City", "County")) \
                    or a["ori"] == "NY0303000":
                want[a["ori"]] = a
    y1 = fbi_latest_full_year()
    fyears = [y1 - 2, y1 - 1, y1]
    print(f"FBI CDE: {len(want)} agencies x 5 offences, years {fyears} ...", flush=True)
    fbi = fbi_rows(sorted(want.values(), key=lambda a: a["ori"]), fyears)

    # FBI year far below the same agency's prior year: flag as possibly incomplete (the API has no flag)
    prev = {(r["ori"], r["year"]): r for r in fbi}
    for r in fbi:
        q = prev.get((r["ori"], r["year"] - 1))
        if q and r["property"] != "" and q["property"] != "" and r["months_reported"] == 12 \
                and q["months_reported"] == 12 and q["property"] >= 30 and r["property"] < 0.5 * q["property"] \
                and "incomplete" not in r["notes"] and "not reported" not in r["notes"]:
            r["notes"] = (r["notes"] + f" Property count {r['property']} is less than half of the prior year's "
                          f"{q['property']}: possibly incomplete reporting to the FBI for this year.").strip()

    # geography text
    fbi_pop = {}
    for r in fbi:
        if r["population"]:
            fbi_pop[r["ori"]] = max(fbi_pop.get(r["ori"], (0, 0)), (r["year"], r["population"]))
    served = defaultdict(list)
    for m in map_rows:
        key = m["ori"] or (f"DCJS:{m['county']}:{m['dcjs_agency']}" if m["dcjs_agency"] else "")
        if key:
            served[key].append(m["geo_name"])
    for r in fbi + dcjs:
        if r["agency_type"] == "county total":
            r["geography"] = f"All police agencies in {r['county']} County combined (DCJS county total)"
            continue
        names = served.get(r["ori"]) or served.get(r["agency_id"]) or []
        if r["agency_type"] in ("County", "State Police") or "County" in r["agency_name"]:
            g = "county-level agency"
        elif names:
            g = "covers " + ("; ".join(sorted(set(names))[:4]) + (" and others" if len(set(names)) > 4 else ""))
        else:
            g = "agency not linked to a Census place in the mapping table"
        r["geography"] = g
    # DCJS agency rows: rate with the FBI population (stated as such), only when linked to an ORI
    fbi_by = {(r["ori"], r["year"]): r for r in fbi}
    for r in dcjs:
        if r["agency_type"] != "agency" or not r["ori"]:
            continue
        f = fbi_by.get((r["ori"], r["year"]))
        pop = f["population"] if f and f["population"] else None
        if pop is None and r["year"] not in fyears:
            pop = fbi_population(r["ori"], r["year"])
        if pop and str(r["months_reported"]) == "12":
            r["population"] = pop
            r["population_source"] = f"FBI CDE agency population for ORI {r['ori']}, same year (DCJS publishes none)"
            r["population_value_type"] = "found"
            r["rate_value_type"] = "estimate"
            r["rate_method"] = "DCJS count / FBI CDE agency population * 1000 (two sources: count DCJS, population FBI)"
            for o in OFFENSES:
                r[f"{o}_per_1000"] = round(r[o] / pop * 1000, 2) if r[o] is not None else ""
        else:
            if pop:
                r["population"] = pop
                r["population_source"] = f"FBI CDE agency population for ORI {r['ori']}, same year"
                r["population_value_type"] = "found"
            r["notes"] = (r["notes"] + " No rate: " + (
                f"DCJS lists {r['months_reported'] or 'no'} months reported for this year, so the count may be "
                "partial or the months field may be wrong." if pop else
                "no FBI CDE population for this agency and year.")).strip()

    REF.mkdir(parents=True, exist_ok=True)
    allrows = nypd + dcjs + fbi
    allrows.sort(key=lambda r: (r["state"], r["county"], r["agency_name"], r["source"], r["year"]))
    with open(AGENCIES_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=AG_COLS)
        w.writeheader()
        w.writerows(allrows)
    for p in sorted({r["precinct"] for r in geo.layers["precinct"][2]}):
        map_rows.append(dict(state="NY", county_fips="", county=_boro_of_precinct(p), geo_type="nypd_precinct",
                             geoid=str(p), geo_name=_precinct_name(p), agency_name=_precinct_name(p),
                             dcjs_agency="", ori="", mapping_basis="polygon",
                             mapping_note="Point-in-polygon on NYPD precinct boundaries.",
                             source_url="https://data.cityofnewyork.us/d/y76i-bdw7"))
    map_rows.sort(key=lambda r: (r["state"], r["county"], r["geo_type"], r["geo_name"]))
    with open(MAP_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MAP_COLS)
        w.writeheader()
        w.writerows(map_rows)
    by = defaultdict(int)
    for m in map_rows:
        by[(m["state"], m["mapping_basis"])] += 1
    print(f"wrote {rel(AGENCIES_CSV)} ({len(allrows)} rows) and {rel(MAP_CSV)} ({len(map_rows)} rows)")
    print("mapping:", dict(sorted(by.items())))
    _tables.cache_clear()


# ================================================================== agency_rates
@lru_cache(maxsize=1)
def _tables():
    if not AGENCIES_CSV.exists() or not MAP_CSV.exists():
        build_agencies()
    ag = defaultdict(list)
    with open(AGENCIES_CSV) as f:
        for r in csv.DictReader(f):
            ag[(r["source"], r["agency_id"])].append(r)
            if r["source"] == "ny_dcjs" and r["ori"]:
                ag[("ny_dcjs_by_ori", r["ori"])].append(r)
    mp = {}
    with open(MAP_CSV) as f:
        for r in csv.DictReader(f):
            mp[(r["geo_type"], r["geoid"])] = r
    return ag, mp


def _fmt_pop(n) -> str:
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1e6:.1f} million"
    return f"{round(n, -3):,}" if n >= 10_000 else f"{round(n, -2):,}"


def _years(rows: list[dict], n: int = 3) -> list[dict]:
    out = []
    for r in sorted(rows, key=lambda r: int(r["year"]), reverse=True)[:n]:
        e = {"year": int(r["year"]), "months_reported": _num(r["months_reported"]),
             "population": _num(r["population"]), "population_source": r["population_source"] or None,
             "population_value_type": r["population_value_type"],
             "counts_value_type": "found" if any(r[o] != "" for o in OFFENSES) else "not_found",
             "rates_value_type": r["rate_value_type"], "rate_method": r["rate_method"] or None,
             "source": r["source"], "source_url": r["source_url"], "retrieved_at": r["retrieved_at"],
             "notes": r["notes"] or None,
             "quality_flag": bool(re.search(r"incomplete|not reported|partial|No rate", r["notes"] or ""))}
        for o in OFFENSES:
            e[o] = _num(r[o])
            e[f"{o}_per_1000"] = float(r[f"{o}_per_1000"]) if r[f"{o}_per_1000"] != "" else None
        out.append(e)
    return out


def _not_found(lat, lon, reason, **extra) -> dict:
    return {"query": {"lat": lat, "lon": lon}, "value_type": "not_found", "reason": reason,
            "retrieved_at": now_iso(), **extra}


def agency_rates(lat: float, lon: float) -> dict:
    """Police agency covering the point and its counts / rates per 1,000 for the latest three full years."""
    ag, mp = _tables()
    loc = locate(lat, lon)
    geo_src = {"place_and_county_subdivision": "Census TIGER/Line 2024 (https://www2.census.gov/geo/tiger/TIGER2024/)",
               "nypd_precinct": "NYC Open Data y76i-bdw7 (https://data.cityofnewyork.us/d/y76i-bdw7)"}
    where = {"state": loc["state"], "county": loc["county"], "county_fips": loc["county_fips"],
             "county_subdivision": loc["cousub"]["namelsad"] if loc["cousub"] else None,
             "place": loc["place"]["namelsad"] if loc["place"] else None, "nypd_precinct": loc["precinct"],
             "source": geo_src}
    if not loc["cousub"]:
        return _not_found(lat, lon, "Point is outside the counties covered by data/reference/search_grid.csv "
                                    "(no county subdivision in the local index).", location=where)
    out = {"query": {"lat": lat, "lon": lon}, "location": where}

    # ---------- NYC
    if loc["precinct"] is not None:
        p = loc["precinct"]
        rows = ag.get(("nypd_complaints", f"NYPD:{p}"), [])
        if not rows:
            return _not_found(lat, lon, f"No complaint rows for NYPD precinct {p}.", location=where)
        yrs = _years(rows)
        pop = yrs[0]["population"]
        out.update({
            "value_type": "found", "primary_source": "nypd_complaints",
            "agency": {"name": rows[0]["agency_name"], "agency_id": f"NYPD:{p}", "type": "NYPD precinct"},
            "geography": (f"{rows[0]['agency_name']} ({_boro_of_precinct(p)}), "
                          + (f"about {_fmt_pop(pop)} residents (2020 Census blocks inside the precinct, estimate)"
                             if pop else "almost no residents, so no rate per resident")),
            "mapping": {"basis": "polygon", "note": "Point-in-polygon on NYPD precinct boundaries.",
                        "source_url": "https://data.cityofnewyork.us/d/y76i-bdw7"},
            "years": yrs,
            "latest_year_with_rates": next((y["year"] for y in yrs if y["property_per_1000"] is not None), None),
            "context": {
                "borough_dcjs": {"what": f"{_boro_of_precinct(p)}: DCJS county total (FBI UCR definitions), "
                                         "separate source, not comparable line by line with NYPD categories",
                                 "years": _years(ag.get(("ny_dcjs", f"DCJS:{loc['county']}:County Total"), []))},
                "nypd_citywide_fbi": {"what": "New York City Police Department, whole city, FBI CDE",
                                      "years": _years(ag.get(("fbi_cde", "NY0303000"), []))}},
            "caveats": ["NYPD counts are complaints by report year under NY Penal Law categories (felony assault, "
                        "grand + petit larceny), close to but not the same as FBI UCR definitions used elsewhere.",
                        "Rates use residents only; precincts with many workers or visitors look worse per resident."],
        })
        return out
    if loc["county_fips"] in NYC_COUNTIES:
        return _not_found(lat, lon, "Point is in a New York City county but outside every NYPD precinct polygon "
                                    "(water or boundary sliver).", location=where)

    # ---------- everywhere else: place first, then county subdivision
    m = None
    if loc["place"]:
        m = mp.get(("place", loc["place"]["geoid"]))
    if m is None:
        m = mp.get(("cousub", loc["cousub"]["geoid"]))
    if m is None:
        return _not_found(lat, lon, "No row for this place in data/reference/crime_place_agency.csv.", location=where)
    out["mapping"] = {"basis": m["mapping_basis"], "note": m["mapping_note"], "matched_geography": m["geo_name"],
                      "source_url": m["source_url"], "table": rel(MAP_CSV)}
    county_ctx = None
    if loc["state"] == "NY":
        county_ctx = {"what": f"{loc['county']} County, all agencies combined (DCJS county total and population)",
                      "years": _years(ag.get(("ny_dcjs", f"DCJS:{loc['county']}:County Total"), []))}
    if not m["agency_name"]:
        out.update({"value_type": "not_found", "reason": m["mapping_note"], "retrieved_at": now_iso()})
        if county_ctx:
            out["context"] = {"county_dcjs": county_ctx}
        return out
    ori = m["ori"]
    fbi = _years(ag.get(("fbi_cde", ori), [])) if ori else []
    if loc["state"] == "NY":
        dc = _years(ag.get(("ny_dcjs", f"DCJS:{m['county']}:{m['dcjs_agency']}"), []))
        primary, psrc, cross = dc, "ny_dcjs", fbi
    else:
        primary, psrc, cross = fbi, "fbi_cde", []
    if not primary:
        out.update({"value_type": "not_found", "retrieved_at": now_iso(),
                    "reason": f"Agency '{m['agency_name']}' is mapped but has no rows in {rel(AGENCIES_CSV)}."})
        return out
    pop = next((y["population"] for y in primary + cross if y["population"]), None)
    name = m["agency_name"]
    is_county = name in NY_COUNTY_PD.values()
    if is_county:
        desc = f"{name}: the county-police jurisdiction (the county minus places with their own department)"
    else:
        desc = f"{name}: serves {m['geo_name']}"
    out.update({
        "value_type": "found", "primary_source": psrc,
        "agency": {"name": name, "agency_id": ori or f"DCJS:{m['county']}:{m['dcjs_agency']}", "ori": ori or None,
                   "type": "county police" if is_county else "municipal police"},
        "geography": desc + (f", population {_fmt_pop(pop)}" if pop else ", population not published"),
        "years": primary,
        "latest_year_with_rates": next((y["year"] for y in primary if y["property_per_1000"] is not None), None),
        "latest_unflagged_year": next((y["year"] for y in primary
                                       if y["property_per_1000"] is not None and not y["quality_flag"]), None),
    })
    if cross:
        out["cross_check"] = {"source": "fbi_cde", "what": "Same agency in the FBI Crime Data Explorer (separate "
                              "source; its latest year can be newer than DCJS)", "years": cross}
    if county_ctx:
        out["context"] = {"county_dcjs": county_ctx}
    caveats = []
    if m["mapping_basis"].startswith("inference") or m["mapping_basis"] == "name_match_base":
        caveats.append("The place-to-agency link is an inference: " + m["mapping_note"])
    yr = next((y for y in primary if y["property_per_1000"] is not None), None)
    if yr is None:
        caveats.append("No year in the primary source has both a complete count and a population, so no rate: "
                       "see the notes on each year and the cross-check.")
    elif yr["population"] and yr["population"] > 15000 and yr["property_per_1000"] < 2:
        caveats.append(f"Property crime of {yr['property_per_1000']} per 1,000 in {yr['year']} is unusually low for "
                       "a place this size; it may reflect incomplete reporting by the agency rather than safety.")
    for y in primary + cross:
        if y["notes"] and ("incomplete" in y["notes"] or "not reported" in y["notes"]):
            caveats.append(f"{y['source']} {y['year']}: {y['notes']}")
    if pop and pop < 10000:
        caveats.append("Small population: one or two incidents move the rate a lot.")
    if is_county:
        caveats.append("A county-police figure averages many very different neighbourhoods; it says little about "
                       "one block.")
    out["caveats"] = caveats
    return out


# ================================================================== NYPD incident slice
def _slice_where(lo: str, hi: str | None) -> str:
    ky = ",".join(f"'{k}'" for k in SLICE_KY)
    pd_ = ",".join(f"'{p}'" for p in SLICE_PD)
    w = f"rpt_dt >= '{lo}T00:00:00' and (ky_cd in ({ky}) or pd_cd in ({pd_}))"
    return w + (f" and rpt_dt <= '{hi}T23:59:59'" if hi else "")


def build_incidents(force: bool = False) -> None:
    """Download the complaint slice once (paged CSV, cached in raw/big/crime/) and pack it into an .npz."""
    if INC_NPZ.exists() and not force:
        return
    import numpy as np
    sel = "cmplnt_num,rpt_dt,cmplnt_fr_dt,cmplnt_fr_tm,ky_cd,pd_cd,addr_pct_cd,latitude,longitude"
    cols = defaultdict(list)
    info = {"datasets": [], "built_at": now_iso()}
    seen = set()
    n_nocoord = defaultdict(int)
    n_all = defaultdict(int)
    for ds, lo, hi in ((HIST, SLICE_START, "2025-12-31"), (CURR, "2026-01-01", None)):
        mx, mm = get_json(f"{SODA_NYC}/{ds}.json", "nyc_open_data",
                          params={"$select": "max(rpt_dt) as mx", "$where": _slice_where(lo, hi)}, refresh=force)
        through = mx[0]["mx"][:10]
        off, page, n = 0, 50000, 0
        while True:
            params = {"$select": sel, "$where": _slice_where(lo, through), "$order": "cmplnt_num",
                      "$limit": page, "$offset": off}
            content, meta = cached_get(f"{SODA_NYC}/{ds}.csv", "big/crime", params=params, ext="csv",
                                       timeout=300, refresh=force)
            if meta["status"] != 200:
                raise RuntimeError(f"HTTP {meta['status']} for {meta['url']}")
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
            for r in rows:
                if r["cmplnt_num"] in seen:
                    continue
                seen.add(r["cmplnt_num"])
                ky, pd_ = _num(r["ky_cd"]) or 0, _num(r["pd_cd"]) or 0
                y = int(r["rpt_dt"][:4])
                n_all[y] += 1
                try:
                    la, lo_ = float(r["latitude"]), float(r["longitude"])
                except ValueError:
                    la = lo_ = 0.0
                if not (40.4 < la < 41.0 and -74.3 < lo_ < -73.6):
                    n_nocoord[y] += 1
                    continue
                d = date.fromisoformat(r["rpt_dt"][:10])
                tm = r.get("cmplnt_fr_tm") or ""
                hr = int(tm[:2]) if re.match(r"^\d\d:", tm) else -1
                cols["lat"].append(la)
                cols["lon"].append(lo_)
                cols["ky"].append(ky)
                cols["pd"].append(pd_)
                cols["day"].append((d - EPOCH).days)
                cols["hour"].append(hr)
            n += len(rows)
            print(f"  {ds} offset {off}: {len(rows)} rows", flush=True)
            if len(rows) < page:
                break
            off += page
        info["datasets"].append({"id": ds, "rpt_dt_from": lo, "rpt_dt_through": through, "rows": n,
                                 "url": f"{SODA_NYC}/{ds}.csv?$where=" + _slice_where(lo, through),
                                 "retrieved_at": meta["retrieved_at"]})
    lat = np.array(cols["lat"], dtype="f8")
    order = np.argsort(lat, kind="stable")
    np.savez_compressed(INC_NPZ, lat=lat[order], lon=np.array(cols["lon"], dtype="f8")[order],
                        ky=np.array(cols["ky"], dtype="i2")[order], pd=np.array(cols["pd"], dtype="i2")[order],
                        day=np.array(cols["day"], dtype="i4")[order], hour=np.array(cols["hour"], dtype="i1")[order])
    info["rows_with_coordinates"] = int(len(lat))
    info["rows_by_report_year"] = dict(sorted(n_all.items()))
    info["rows_without_coordinates_by_report_year"] = dict(sorted(n_nocoord.items()))
    info["data_through"] = info["datasets"][-1]["rpt_dt_through"]
    INC_META.write_text(json.dumps(info, indent=1))
    print(f"incident slice: {len(lat)} located rows, through {info['data_through']}; "
          f"no coordinates: {dict(n_nocoord)}")
    _incidents.cache_clear()


@lru_cache(maxsize=1)
def _incidents():
    import numpy as np
    build_incidents()
    z = np.load(INC_NPZ)
    arr = {k: z[k] for k in z.files}
    meta = json.loads(INC_META.read_text())
    end = date.fromisoformat(meta["data_through"])
    # 24 months ending on the data-through date
    start = date(end.year - 2, end.month, end.day) if not (end.month == 2 and end.day == 29) \
        else date(end.year - 2, 2, 28)
    arr["_end_day"] = (end - EPOCH).days
    arr["_start24_day"] = (start - EPOCH).days  # exclusive
    arr["_year"] = (arr["day"].astype("datetime64[D]").astype("datetime64[Y]").astype(int) + 1970).astype("i2")
    masks = {}
    for cat, spec in INCIDENT_CATS.items():
        col = arr["ky"] if spec["field"] == "ky_cd" else arr["pd"]
        masks[cat] = np.isin(col, spec["codes"])
    arr["_masks"] = masks
    arr["_meta"] = meta
    arr["_window"] = (start.isoformat(), end.isoformat())
    return arr


def _near_idx(arr, lat, lon, radius_m):
    import numpy as np
    dlat = radius_m / 111_320.0
    i0, i1 = np.searchsorted(arr["lat"], [lat - dlat, lat + dlat])
    la = arr["lat"][i0:i1]
    lo = arr["lon"][i0:i1]
    x = (lo - lon) * 111_320.0 * math.cos(math.radians(lat))
    y = (la - lat) * 111_132.0
    keep = x * x + y * y <= radius_m * radius_m
    return i0 + np.nonzero(keep)[0]


def _counts_at(arr, lat, lon, radius_m) -> dict:
    import numpy as np
    idx = _near_idx(arr, lat, lon, radius_m)
    day, yr, hr = arr["day"][idx], arr["_year"][idx], arr["hour"][idx]
    in24 = (day > arr["_start24_day"]) & (day <= arr["_end_day"])
    out = {}
    for cat, mask in arr["_masks"].items():
        m = mask[idx]
        c24 = m & in24
        timed = c24 & (hr >= 0)
        nt = int(timed.sum())
        eve = int((timed & (hr >= 19)).sum())
        out[cat] = {"last_24_months": int(c24.sum()),
                    "2023": int((m & (yr == 2023)).sum()), "2024": int((m & (yr == 2024)).sum()),
                    "2025": int((m & (yr == 2025)).sum()), "2026_ytd": int((m & (yr == 2026)).sum()),
                    "evening_19_to_24_count_24m": eve, "with_time_24m": nt,
                    "share_19_to_24_24m": round(eve / nt, 3) if nt else None}
    return out


def incidents_near(lat: float, lon: float, radius_m: float = 250, with_baseline: bool = True) -> dict:
    """NYPD complaint counts within radius_m of a point (NYC only). Years are report years (rpt_dt)."""
    loc = locate(lat, lon)
    if loc["precinct"] is None:
        return _not_found(
            lat, lon,
            "incidents_near covers New York City only (NYPD complaint data). This point is in "
            f"{(loc['place'] or loc['cousub'] or {}).get('namelsad', 'an area outside the index')}"
            + (f", {loc['county']}{' County' if loc['state'] != 'CT' else ' planning region'}, {loc['state']}"
               if loc['county'] else "")
            + ": no incident-level source with coordinates is wired in for it (see docs/tools_notes/crime.md).",
            radius_m=radius_m)
    arr = _incidents()
    meta = arr["_meta"]
    counts = _counts_at(arr, lat, lon, radius_m)
    boro = _boro_of_precinct(loc["precinct"])
    out = {
        "query": {"lat": lat, "lon": lon, "radius_m": radius_m},
        "value_type": "found",
        "nypd_precinct": loc["precinct"], "borough": boro,
        "periods": {"last_24_months": f"report dates {arr['_window'][0]} (exclusive) to {arr['_window'][1]}",
                    "2023": "full report year", "2024": "full report year", "2025": "full report year",
                    "2026_ytd": f"2026-01-01 to {meta['data_through']}"},
        "counts": counts,
        "categories": {k: v["desc"] for k, v in INCIDENT_CATS.items()},
        "evening_share_method": "share of last-24-month complaints with a recorded start time (cmplnt_fr_tm) whose "
                                "start hour is 19 to 23. For thefts found later, the start time is the beginning of "
                                "the window in which it could have happened.",
        "provenance": {
            "source": "NYPD Complaint Data Historic (qgea-i56i) and Current Year To Date (5uac-w243), NYC Open Data",
            "source_url": [HIST_PAGE, CURR_PAGE],
            "query_urls": [d["url"] for d in meta["datasets"]],
            "retrieved_at": meta["built_at"], "data_through": meta["data_through"],
            "local_copy": rel(INC_NPZ), "value_type": "found",
            "method": f"count of complaints whose published latitude/longitude is within {radius_m:g} m "
                      "(planar distance) of the point"},
        "caveats": [
            "NYPD publishes the midpoint of the street segment or the nearest intersection, not the exact address, "
            "so a count at a small radius is approximate.",
            "Complaints with no coordinates are left out: "
            + ", ".join(f"{y}: {meta['rows_without_coordinates_by_report_year'].get(y, 0)} of {n}"
                        for y, n in meta["rows_by_report_year"].items()) + " rows in the slice.",
            "Counts are not divided by population: busy commercial streets and transit hubs collect more complaints.",
        ],
    }
    if with_baseline:
        try:
            b = nyc_baseline(radius_m)
            comp = {}
            for cat in INCIDENT_CATS:
                v = counts[cat]["last_24_months"]
                bb, bc = b["areas"][boro][cat]["last_24_months"], b["areas"]["citywide"][cat]["last_24_months"]
                comp[cat] = {"count_last_24_months": v, "borough_median": bb["median"], "borough_p80": bb["p80"],
                             "citywide_median": bc["median"], "citywide_p80": bc["p80"],
                             "above_borough_p80": v > bb["p80"], "above_citywide_p80": v > bc["p80"]}
            out["vs_baseline"] = {"comparison": comp, "value_type": "estimate", "method": b["method"],
                                  "grid_points": {k: v["n_points"] for k, v in b["areas"].items()}}
        except Exception as e:  # baseline is optional
            out["vs_baseline"] = {"value_type": "not_found", "reason": f"baseline not available: {e}"}
    return out


# ================================================================== citywide baseline
BASE_STEP_M = 300.0
BASE_POP_RADIUS_M = 250.0
BASE_MIN_POP = 500


def _baseline_path(radius_m: float) -> Path:
    return BIG / f"nyc_baseline_r{int(round(radius_m))}.json"


def nyc_baseline(radius_m: float = 250, force: bool = False) -> dict:
    """Median and 80th percentile of the incidents_near counts over a regular grid of residential points."""
    p = _baseline_path(radius_m)
    if p.exists() and not force:
        return json.loads(p.read_text())
    import numpy as np
    import shapely
    arr = _incidents()
    g = _geo()
    tree, geoms, recs = g.layers["precinct"]
    blocks = load_blocks()
    blat = np.array([b[1] for b in blocks])
    blon = np.array([b[2] for b in blocks])
    bpop = np.array([b[3] for b in blocks])
    o = np.argsort(blat)
    blat, blon, bpop = blat[o], blon[o], bpop[o]
    minx, miny, maxx, maxy = shapely.total_bounds(geoms)
    dlat = BASE_STEP_M / 111_132.0
    dlon = BASE_STEP_M / (111_320.0 * math.cos(math.radians(40.7)))
    lats = np.arange(miny + dlat / 2, maxy, dlat)
    lons = np.arange(minx + dlon / 2, maxx, dlon)
    LA, LO = np.meshgrid(lats, lons, indexing="ij")
    LA, LO = LA.ravel(), LO.ravel()
    pi, gi = tree.query(shapely.points(LO, LA), predicate="intersects")
    pct = {}
    for a, b in zip(pi.tolist(), gi.tolist()):
        pct.setdefault(a, recs[b]["precinct"])
    vals = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    n_pts = defaultdict(int)
    r_lat = BASE_POP_RADIUS_M / 111_132.0
    for i, pc in pct.items():
        la, lo = float(LA[i]), float(LO[i])
        j0, j1 = np.searchsorted(blat, [la - r_lat, la + r_lat])
        x = (blon[j0:j1] - lo) * 111_320.0 * math.cos(math.radians(la))
        y = (blat[j0:j1] - la) * 111_132.0
        pop = int(bpop[j0:j1][x * x + y * y <= BASE_POP_RADIUS_M ** 2].sum())
        if pop < BASE_MIN_POP:
            continue
        c = _counts_at(arr, la, lo, radius_m)
        for area in ("citywide", _boro_of_precinct(pc)):
            n_pts[area] += 1
            for cat, v in c.items():
                for per in ("last_24_months", "2025"):
                    vals[area][cat][per].append(v[per])
    areas = {}
    for area, cats in vals.items():
        areas[area] = {"n_points": n_pts[area]}
        for cat, pers in cats.items():
            areas[area][cat] = {per: {"median": round(float(np.percentile(v, 50)), 1),
                                      "p80": round(float(np.percentile(v, 80)), 1),
                                      "p90": round(float(np.percentile(v, 90)), 1),
                                      "mean": round(float(np.mean(v)), 2)}
                                for per, v in pers.items()}
    meta = arr["_meta"]
    out = {
        "radius_m": radius_m, "value_type": "estimate",
        "method": (f"Regular {BASE_STEP_M:g} m grid over the NYPD precinct polygons; a grid point counts as "
                   f"residential when 2020 Census blocks with their internal point within {BASE_POP_RADIUS_M:g} m "
                   f"hold at least {BASE_MIN_POP} residents; the incidents_near counts (radius {radius_m:g} m) are "
                   "computed at every such point and summarised by median, 80th and 90th percentile."),
        "periods": {"last_24_months": f"{arr['_window'][0]} (exclusive) to {arr['_window'][1]}", "2025": "report year"},
        "areas": areas,
        "provenance": {"source_url": [HIST_PAGE, CURR_PAGE, PL_URL, "https://data.cityofnewyork.us/d/y76i-bdw7"],
                       "data_through": meta["data_through"], "retrieved_at": meta["built_at"],
                       "computed_at": now_iso(), "local_copy": rel(p)},
    }
    p.write_text(json.dumps(out, indent=1))
    if int(round(radius_m)) == 250:
        with open(BASELINE_CSV, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["radius_m", "area", "n_grid_points", "category", "period", "median", "p80", "p90", "mean",
                        "value_type", "method", "data_through", "source_url"])
            for area, d in areas.items():
                for cat in INCIDENT_CATS:
                    for per, s in d[cat].items():
                        w.writerow([radius_m, area, d["n_points"], cat, per, s["median"], s["p80"], s["p90"],
                                    s["mean"], "estimate", out["method"], meta["data_through"],
                                    f"{HIST_PAGE} ; {CURR_PAGE}"])
    return out


# ================================================================== CLI / self-test
TEST_POINTS = [("Jamaica station", 40.699608, -73.808530), ("Forest Hills", 40.7196, -73.8448),
               ("Long Beach NY", 40.5890, -73.6649), ("Stamford CT", 41.0469, -73.5419),
               ("Jersey City Grove St", 40.7196, -74.0431), ("Beacon NY", 41.5060, -73.9845)]


def _brief_year(y: dict) -> str:
    def f(o):
        c, r = y[o], y[f"{o}_per_1000"]
        return f"{c if c is not None else '-'}" + (f" ({r}/1k)" if r is not None else "")
    return (f"{y['year']} [{y['source']}] pop {y['population']}: violent {f('violent')}, property {f('property')}, "
            f"MVT {f('motor_vehicle_theft')}, burglary {f('burglary')}, larceny {f('larceny')}")


def selftest() -> None:
    for name, lat, lon in TEST_POINTS:
        print(f"\n=== {name} ({lat}, {lon})")
        t0 = time.time()
        a = agency_rates(lat, lon)
        t1 = time.time()
        print(f"agency_rates [{(t1 - t0) * 1000:.0f} ms] value_type={a['value_type']}")
        if a["value_type"] == "found":
            print("  ", a["geography"])
            print("   mapping:", a["mapping"]["basis"], "|", a["mapping"]["note"][:110])
            for y in a["years"]:
                print("   ", _brief_year(y))
            for y in (a.get("cross_check") or {}).get("years", []):
                print("    x-check", _brief_year(y))
            print("   source_url:", a["years"][0]["source_url"][:120], "| retrieved", a["years"][0]["retrieved_at"])
        else:
            print("   reason:", a["reason"])
        t0 = time.time()
        inc = incidents_near(lat, lon, 250)
        t1 = time.time()
        print(f"incidents_near r=250 [{(t1 - t0) * 1000:.0f} ms] value_type={inc['value_type']}")
        if inc["value_type"] == "found":
            for cat, v in inc["counts"].items():
                b = (inc.get("vs_baseline", {}).get("comparison") or {}).get(cat, {})
                print(f"   {cat:30s} 24m {v['last_24_months']:4d} | 2023 {v['2023']:3d} 2024 {v['2024']:3d} "
                      f"2025 {v['2025']:3d} | 19-24h share {v['share_19_to_24_24m']} | boro median "
                      f"{b.get('borough_median')} p80 {b.get('borough_p80')}")
            print("   data through", inc["provenance"]["data_through"], "| retrieved", inc["provenance"]["retrieved_at"])
        else:
            print("   reason:", inc["reason"])
    b = nyc_baseline(250)
    print("\n=== nyc_baseline(250), last 24 months: median / p80")
    for area, d in b["areas"].items():
        print(f"   {area:14s} n={d['n_points']:5d} " + ", ".join(
            f"{c.split('_')[0]}:{d[c]['last_24_months']['median']:g}/{d[c]['last_24_months']['p80']:g}"
            for c in INCIDENT_CATS))


if __name__ == "__main__":
    args = set(sys.argv[1:])
    if args & {"--build", "--build-geo"}:
        build_geo(force="--force" in args)
    if args & {"--build", "--build-agencies"}:
        build_agencies()
    if args & {"--build", "--build-incidents"}:
        build_incidents(force="--force" in args)
    if args & {"--build", "--build-baseline"}:
        nyc_baseline(250, force=True)
    if not args or "--selftest" in args:
        selftest()
