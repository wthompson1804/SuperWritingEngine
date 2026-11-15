"""Utilities lookup tool: estimated monthly electric, gas and internet for any lat/lon.

    from scripts.tools.utilities import monthly_utilities
    monthly_utilities(40.699608, -73.808530, beds=1, sqft=None, heat_included=None)

Every line is an ESTIMATE (value_type = "estimate") with its method and sources, or
"not_found" with the reason. Nothing here is a quote for an address.

Electric = utility serving the point (HIFLD/ORNL "Electric Retail Service Territories" polygons,
           plus documented overrides) x that utility's EIA-861 average residential price
           x RECS 2020 kWh for Northeast apartments in 5+ unit buildings.
Gas      = cooking only: the gas utility's published minimum monthly charge where we hold its
           tariff, otherwise EIA state residential price x RECS cooking therms (flagged low);
           cooking + heat: EIA state residential price x RECS cooking + space-heating therms.
Internet = one flat published price (not address-specific).

Run `python3 scripts/tools/utilities.py` for the self-test, `--build` to rebuild the index
(raw/big/utilities/index.pkl) and data/reference/utility_rates.csv.
Rebuild needs pandas, openpyxl, xlrd, pyshp; lookups need only shapely.
"""
from __future__ import annotations

import csv
import io
import json
import pickle
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lib  # noqa: E402

from shapely import wkb  # noqa: E402
from shapely.geometry import Point, shape  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

BIG = lib.RAW / "big" / "utilities"
INDEX = BIG / "index.pkl"
RATES_CSV = lib.DATA / "reference" / "utility_rates.csv"
BBOX = "-76.2,39.2,-71.7,42.7"  # study area: NYC metro out to ~2 h drive, plus margin
STATES = {"36": "NY", "34": "NJ", "09": "CT", "42": "PA"}

# ---- sources -----------------------------------------------------------------------------
HIFLD_ELEC = ("https://services3.arcgis.com/OYP7N6mAJJCyH6hd/arcgis/rest/services/"
              "Electric_Retail_Service_Territories_HIFLD/FeatureServer/0")
HIFLD_GAS = ("https://services5.arcgis.com/HDRa0B57OVrv2E1q/arcgis/rest/services/"
             "Natural_Gas_Service_Territories/FeatureServer/0")
EIA861 = "https://www.eia.gov/electricity/data/eia861/zip/f8612025.zip"
EIA861M = "https://www.eia.gov/electricity/data/eia861m/xls/sales_revenue.xlsx"
RECS_MICRO = "https://www.eia.gov/consumption/residential/data/2020/csv/recs2020_public_v7.csv"
RECS_CE22 = "https://www.eia.gov/consumption/residential/data/2020/c&e/xls/ce2.2.xlsx"
RECS_CE42 = "https://www.eia.gov/consumption/residential/data/2020/c&e/xls/ce4.2.xlsx"
NG_PRICE = "https://www.eia.gov/dnav/ng/xls/NG_PRI_SUM_DCU_S{st}_A.xls"
NG_HEAT = "https://www.eia.gov/dnav/ng/xls/NG_CONS_HEAT_A_EPG0_VGTH_BTUCF_A.xls"
COUNTY_SHP = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
CT_COUSUB = "https://www2.census.gov/geo/tiger/TIGER2023/COUSUB/tl_2023_09_cousub.zip"
CT_RSIP = "https://data.ct.gov/resource/fvw8-89kt.json"  # CT Green Bank RSIP: utility by municipality
FCC_URS = "https://docs.fcc.gov/public/attachments/DA-25-1088A1.pdf"
FIOS_PAGE = "https://www.verizon.com/home/internet/fios-fastest-internet/"
OPTIMUM_PAGE = "https://www.optimum.com/internet"

# Gas tariff minimum monthly charges read from the utilities' own published rate sheets
# (first 3 therms or less, residential non-heating). Read by hand from the cached PDFs on 2026-11-15.
GAS_MIN_CHARGE = {
    "CONED": dict(utility="Con Edison (gas)", state="NY", price=33.23, included_therms=3,
                  period="rates effective 2026-01-01, sheet for 2026-11", tariff="SC 1 Residential and Religious Firm Sales Service",
                  source_url="https://www.coned.com/-/media/files/coned/documents/rates/gas/allrates.pdf"),
    "KEDNY": dict(utility="National Grid NY (KEDNY: Brooklyn, Queens, Staten Island)", state="NY", price=23.50,
                  included_therms=3, period="effective 2026-04-01", tariff="SC 1A Residential Non-Heating Service",
                  source_url="https://www.nationalgridus.com/media/pdfs/billing-payments/gas-rates/nym/kedny_gas_delivery_charges.pdf"),
    "KEDLI": dict(utility="National Grid Long Island (KEDLI)", state="NY", price=28.50, included_therms=3,
                  period="effective 2026-04-01", tariff="SC 1A Residential Non-Heating Service",
                  source_url="https://www.nationalgridus.com/media/pdfs/billing-payments/gas-rates/nyl/kedli-delivery-charges.pdf"),
    # PSE&G: the BPU notice gives whole winter bills by usage (25 therms $37.75, 50 therms $65.51).
    # A straight line through those two points gives $9.99 fixed + $1.1104 per therm.
    "PSEG": dict(utility="PSE&G (gas)", state="NJ", price=9.99, included_therms=0, per_therm=1.1104,
                 period="rates in effect 2026-06-01 (winter bill table)", tariff="RSG Residential Service",
                 source_url="https://www.nj.gov/bpu/pdf/publicnotice/GR26060274%20PSEG%20BGSS%20Public%20Hearing%20Notice%209.3.26.pdf"),
}
GAS_TARIFF_SOURCE = "gas_tariffs"

# Internet: flat published prices, read by hand from the cached pages on 2026-11-15.
INTERNET = dict(
    default=dict(provider="Verizon Fios", plan="500 Mbps (the middle of five tiers: 300 Mbps, 500 Mbps, 1 Gig, 2 Gig, 5 Gig)",
                 price=75.00, note="published monthly price before the $10 Auto Pay and paper-free discount; "
                 "the page says pricing includes taxes, fees and router", source_url=FIOS_PAGE),
    alternatives=[
        dict(provider="Verizon Fios", plan="300 Mbps (lowest tier)", price=40.00,
             note="before the $10 Auto Pay and paper-free discount", source_url=FIOS_PAGE),
        dict(provider="Optimum", plan="300 Mbps", price=35.00,
             note="new-customer price for 12 months with Auto Pay and paperless billing, plus taxes and fees; "
             "rises by up to $15/month per year after that", source_url=OPTIMUM_PAGE),
        dict(provider="FCC 2026 Urban Rate Survey", plan="100/20 Mbps, unlimited: reasonable comparability benchmark",
             price=96.46, note="a ceiling, not a typical price: the urban average plus two standard deviations",
             source_url=FCC_URS),
    ])

DISPLAY = {4226: "Con Edison", 11171: "PSEG Long Island (LIPA)", 3249: "Central Hudson", 13511: "NYSEG",
           14154: "Orange & Rockland", 16213: "Rockland Electric (O&R, NJ)", 4176: "Eversource CT (Connecticut Light & Power)",
           19497: "United Illuminating", 15477: "PSE&G", 9726: "JCP&L", 963: "Atlantic City Electric",
           16217: "Rockville Centre (village electric)", 6775: "Freeport Electric (village)",
           17569: "South Norwalk Electric & Water (SNEW)", 13825: "Norwalk Third Taxing District (TTD)",
           20038: "Wallingford Electric Division", 14940: "PECO", 14715: "PPL Electric", 13573: "National Grid (Niagara Mohawk)"}
GAS_DISPLAY = {"YANKEE GAS SERVICE CO.": "Eversource CT gas (Yankee Gas)", "CONNETICUT NATURAL GAS CORP": "Connecticut Natural Gas",
               "NYS ELECTRIC AND GAS": "NYSEG (gas)", "CENTRAL HUDSON GAS AND ELECTRIC": "Central Hudson (gas)",
               "ORANGE AND ROCKLAND UTILITIES": "Orange & Rockland (gas)", "ELIZABETHTOWN GAS CO.": "Elizabethtown Gas"}
CLP, UI, SNEW, TTD, FISHERS = 4176, 19497, 17569, 13825, 6369

_IDX = None


# ---- build -------------------------------------------------------------------------------
def _arcgis_layer(url: str, fields: str, page: int = 8) -> tuple[list, dict]:
    feats, off, meta = [], 0, {}
    while True:
        p = dict(where="1=1", geometry=BBOX, geometryType="esriGeometryEnvelope", inSR=4326,
                 spatialRel="esriSpatialRelIntersects", outFields=fields, returnGeometry="true", outSR=4326,
                 geometryPrecision=5, orderByFields="OBJECTID", resultOffset=off, resultRecordCount=page, f="geojson")
        d, meta = lib.get_json(url + "/query", "big/utilities", params=p, ext="geojson", timeout=300)
        feats += d["features"]
        if len(d["features"]) < page:
            return feats, meta
        off += page


def _polys(feats):
    out = []
    for f in feats:
        g = shape(f["geometry"])
        if not g.is_valid:
            g = g.buffer(0)
        out.append((f["properties"], g.wkb))
    return out


def _read_shp(zip_path: Path):
    import shapefile  # pyshp
    r = shapefile.Reader(str(zip_path))
    for sr in r.iterShapeRecords():
        yield sr.record.as_dict(), shape(sr.shape.__geo_interface__)


def _wmean(df, col):
    import numpy as np
    return float(np.average(df[col], weights=df["NWEIGHT"])) if len(df) else None


def build() -> dict:
    """Download (cached) every source, compute the tables, write index.pkl and utility_rates.csv."""
    import pandas as pd

    src = {}  # name -> {source_url, retrieved_at}

    def note(name, meta, url=None):
        src[name] = {"source_url": url or meta["url"], "retrieved_at": meta["retrieved_at"]}

    # 1. territories
    ef, m = _arcgis_layer(HIFLD_ELEC, "ID,NAME,STATE,TYPE,SOURCE,CUSTOMERS,YEAR", 10)
    note("electric_territory", m, HIFLD_ELEC)
    gf, m = _arcgis_layer(HIFLD_GAS, "SVCTERID,NAME,STATE,TYPE,SOURCE,SOURCEDATE,VAL_DATE,LDC_STATE,HOLDINGCO", 8)
    note("gas_territory", m, HIFLD_GAS)

    # 2. counties (state + county name) and CT towns
    _, m = lib.cached_get(COUNTY_SHP, "big/utilities", ext="zip", timeout=300)
    note("counties", m)
    counties = [(STATES[r["STATEFP"]], r["NAME"], g.wkb) for r, g in _read_shp(lib.ROOT / m["path"]) if r["STATEFP"] in STATES]
    _, m = lib.cached_get(CT_COUSUB, "big/utilities", ext="zip", timeout=300)
    note("ct_towns", m)
    ct_towns = [(r["NAME"], g.wkb) for r, g in _read_shp(lib.ROOT / m["path"])]
    rs, m = lib.get_json(CT_RSIP, "ct_utility_territory", params={
        "$select": "municipality,utility_company,count(*) as n", "$group": "municipality,utility_company", "$limit": 1000})
    note("ct_ui_towns", m)
    by = {}
    for r in rs:
        by.setdefault(r.get("municipality"), {})[r.get("utility_company")] = int(r["n"])
    ui_towns = sorted(t for t, v in by.items() if t and v.get("United Illuminating", 0) > 0.5 * sum(v.values()))

    # 3. electric prices: EIA-861 (2025)
    content, m = lib.cached_get(EIA861, "eia861", ext="zip", timeout=300)
    note("eia861", m)
    z = zipfile.ZipFile(io.BytesIO(content))
    s = pd.read_excel(io.BytesIO(z.read("Sales_Ult_Cust_2025.xlsx")), sheet_name="States", header=2).iloc[:, :12]
    s.columns = ["year", "num", "name", "part", "svc", "dtype", "state", "own", "ba", "rev", "mwh", "cust"]
    s = s[s.state.isin(STATES.values()) & (s.part == "A")].copy()
    for c in ("rev", "mwh", "cust"):
        s[c] = pd.to_numeric(s[c], errors="coerce")
    s = s.groupby(["num", "name", "state"], as_index=False)[["rev", "mwh", "cust"]].sum()
    prices = {}
    for r in s.itertuples():
        if r.mwh and r.mwh > 0:
            prices[(int(r.num), r.state)] = dict(
                name=r.name, cents_kwh=round(r.rev / r.mwh * 100, 2), basis="residential, bundled service (Part A)",
                period="2025", customers=int(r.cust), file="Sales_Ult_Cust_2025.xlsx")
    sf = pd.read_excel(io.BytesIO(z.read("Short_Form_2025.xlsx")), header=0).iloc[:, :9]
    sf.columns = ["year", "num", "name", "own", "state", "ba", "rev", "mwh", "cust"]
    sf = sf[sf.state.isin(STATES.values())]
    for r in sf.itertuples():
        rev, mwh = pd.to_numeric(r.rev, errors="coerce"), pd.to_numeric(r.mwh, errors="coerce")
        if mwh and mwh > 0 and (int(r.num), r.state) not in prices:
            prices[(int(r.num), r.state)] = dict(
                name=r.name, cents_kwh=round(rev / mwh * 100, 2),
                basis="all customer classes together (EIA-861S short form has no residential split)",
                period="2025", customers=int(r.cust), file="Short_Form_2025.xlsx")

    # 3b. EIA-861M: state residential average, latest 12 months (context only)
    _, m = lib.cached_get(EIA861M, "eia861m", ext="xlsx", timeout=300)
    note("eia861m", m)
    mm = pd.read_excel(lib.ROOT / m["path"], sheet_name="Monthly-States", header=2).iloc[:, :8]
    mm.columns = ["year", "month", "state", "status", "rev", "mwh", "cust", "price"]
    mm = mm[mm.state.isin(STATES.values())].copy()
    for c in ("year", "month", "rev", "mwh"):
        mm[c] = pd.to_numeric(mm[c], errors="coerce")
    mm = mm.dropna(subset=["year", "month"]).sort_values(["year", "month"])
    state_elec = {}
    for st, g in mm.groupby("state"):
        g = g.tail(12)
        state_elec[st] = dict(cents_kwh=round(g.rev.sum() / g.mwh.sum() * 100, 2),
                              period=f"{int(g.year.iloc[0])}-{int(g.month.iloc[0]):02d} to {int(g.year.iloc[-1])}-{int(g.month.iloc[-1]):02d}")

    # 4. RECS 2020 microdata: Northeast (Middle Atlantic + New England), apartments in 5+ unit buildings
    _, m = lib.cached_get(RECS_MICRO, "big/utilities", ext="csv", timeout=600)
    note("recs_micro", m)
    cols = ["DIVISION", "TYPEHUQ", "BEDROOMS", "TOTSQFT_EN", "NWEIGHT", "KWH", "FUELHEAT", "KWHSPH",
            "BTUNGSPH", "BTUNGWTH", "BTUNGCOK"]
    df = pd.read_csv(lib.ROOT / m["path"], usecols=cols)
    a = df[(df.TYPEHUQ == 5) & df.DIVISION.isin(["Middle Atlantic", "New England"])].copy()
    a["bed"] = a.BEDROOMS.clip(upper=3)
    ne = a[a.FUELHEAT != 5]  # main heating fuel is not electricity
    recs = dict(n_all=len(a), kwh_all=round(_wmean(a, "KWH")), kwh_by_bed={}, kwh_by_sqft=[], elec_heat_kwh_by_bed={},
                cook_therms_by_bed={}, sph_therms_by_bed={}, wth_therms_by_bed={})
    for b in range(4):
        g = ne[ne.bed == b]
        recs["kwh_by_bed"][b] = dict(kwh_year=round(_wmean(g, "KWH")), n=len(g))
        g = a[(a.bed == b) & (a.FUELHEAT == 5)]
        recs["elec_heat_kwh_by_bed"][b] = dict(kwh_year=round(_wmean(g, "KWHSPH")), n=len(g))
        g = a[(a.bed == b) & (a.BTUNGCOK > 0)]
        recs["cook_therms_by_bed"][b] = dict(therms_year=round(_wmean(g, "BTUNGCOK") / 100, 1), n=len(g))
        g = a[(a.bed == b) & (a.BTUNGSPH > 0)]
        recs["sph_therms_by_bed"][b] = dict(therms_year=round(_wmean(g, "BTUNGSPH") / 100, 1), n=len(g))
        g = a[(a.bed == b) & (a.BTUNGWTH > 0)]
        recs["wth_therms_by_bed"][b] = dict(therms_year=round(_wmean(g, "BTUNGWTH") / 100, 1), n=len(g))
    for lo, hi in ((0, 500), (500, 750), (750, 1000), (1000, 1500), (1500, 99999)):
        g = ne[(ne.TOTSQFT_EN > lo) & (ne.TOTSQFT_EN <= hi)]
        recs["kwh_by_sqft"].append(dict(lo=lo, hi=hi, kwh_year=round(_wmean(g, "KWH")), n=len(g)))
    for u in (RECS_CE22, RECS_CE42):
        _, m = lib.cached_get(u, "eia_recs", ext="xlsx")
    note("recs_ce22", m, RECS_CE22)

    # 5. gas: EIA state residential price (latest annual) and heat content
    _, m = lib.cached_get(NG_HEAT, "eia_ng", ext="xls")
    note("ng_heat", m)
    h = pd.read_excel(lib.ROOT / m["path"], sheet_name="Data 1", header=None)
    gas = {}
    for st in STATES.values():
        _, m = lib.cached_get(NG_PRICE.format(st=st), "eia_ng", ext="xls")
        note(f"ng_price_{st}", m)
        d = pd.read_excel(lib.ROOT / m["path"], sheet_name="Data 1", header=None)
        col = [i for i, v in enumerate(d.iloc[1]) if str(v) == f"N3010{st}3"][0]
        ser = d.iloc[3:, [0, col]].dropna()
        yr, mcf = ser.iloc[-1, 0].year, float(ser.iloc[-1, 1])
        hc = [i for i, v in enumerate(h.iloc[1]) if str(v) == f"NGA_EPG0_VGTH_S{st}_BTUCF"][0]
        hs = h.iloc[3:, [0, hc]].dropna()
        btu = float(hs.iloc[-1, 1])
        gas[st] = dict(usd_mcf=mcf, year=yr, btu_cf=btu, heat_year=hs.iloc[-1, 0].year,
                       usd_therm=round(mcf / (btu / 100.0), 4))  # 1 Mcf = btu_cf/100 therms

    # 6. hand-read sources: make sure the cached copies exist so retrieved_at is recorded
    for k, t in GAS_MIN_CHARGE.items():
        _, m = lib.cached_get(t["source_url"], GAS_TARIFF_SOURCE, ext="pdf")
        note(f"gas_tariff_{k}", m)
    _, m = lib.cached_get(FCC_URS, "fcc_urs", ext="pdf")
    note("fcc_urs", m)
    for name, u in (("fios", FIOS_PAGE), ("optimum", OPTIMUM_PAGE)):
        _, m = lib.cached_get(u, "isp_pricing", ext="html")
        note(name, m)

    idx = dict(built_at=lib.now_iso(), electric=_polys(ef), gas=_polys(gf), counties=counties, ct_towns=ct_towns,
               ui_towns=ui_towns, prices=prices, state_elec=state_elec, recs=recs, gas_price=gas, src=src)
    BIG.mkdir(parents=True, exist_ok=True)
    INDEX.write_bytes(pickle.dumps(idx))
    _write_rates_csv(idx)
    return idx


def _write_rates_csv(idx: dict) -> None:
    rows = []
    ids_in_area = {int(p["ID"]) for p, _ in idx["electric"] if str(p["ID"]).isdigit()}
    for (num, st), v in sorted(idx["prices"].items(), key=lambda kv: (kv[0][1], kv[1]["name"])):
        if num not in ids_in_area:
            continue
        typ = "electric_residential" if v["file"].startswith("Sales") else "electric_all_classes"
        rows.append([DISPLAY.get(num, v["name"]) + f" [EIA id {num}]", st, typ, v["cents_kwh"], "cents/kWh",
                     f"{v['period']} annual (EIA-861 {v['file']}: revenue / sales; {v['basis']})", EIA861])
    for st, v in sorted(idx["state_elec"].items()):
        rows.append([f"{st} statewide average", st, "electric_residential_state_avg", v["cents_kwh"], "cents/kWh",
                     f"{v['period']} (EIA-861M, 12 months; context only, not used in estimates)", EIA861M])
    for st, v in sorted(idx["gas_price"].items()):
        rows.append([f"{st} statewide average", st, "gas_residential", v["usd_mcf"], "$/Mcf", f"{v['year']} annual (EIA series N3010{st}3)",
                     NG_PRICE.format(st=st)])
        rows.append([f"{st} statewide average", st, "gas_residential", v["usd_therm"], "$/therm",
                     f"{v['year']} annual price / {v['heat_year']} heat content {v['btu_cf']:.0f} Btu per cubic foot", NG_HEAT])
    for t in GAS_MIN_CHARGE.values():
        unit = "$/month for the first 3 therms or less" if t["included_therms"] else "$/month fixed part (derived from bill table)"
        rows.append([t["utility"], t["state"], "gas_min_monthly_charge", t["price"], unit, f"{t['tariff']}; {t['period']}", t["source_url"]])
    d = INTERNET["default"]
    rows.append([f"{d['provider']} {d['plan']}", "all", "internet_flat_default", d["price"], "$/month", f"page read 2026-11-15; {d['note']}", d["source_url"]])
    for d in INTERNET["alternatives"]:
        rows.append([f"{d['provider']} {d['plan']}", "all", "internet_reference", d["price"], "$/month", f"read 2026-11-15; {d['note']}", d["source_url"]])
    r = idx["recs"]
    lab = {0: "studio", 1: "1 bedroom", 2: "2 bedrooms", 3: "3+ bedrooms"}
    for b, v in r["kwh_by_bed"].items():
        rows.append([f"RECS 2020 Northeast apartments in 5+ unit buildings, {lab[b]}, heat not electric (n={v['n']})", "Northeast",
                     "assumed_electric_use", round(v["kwh_year"] / 12), "kWh/month", "2020 (RECS microdata v7, weighted mean of KWH)", RECS_MICRO])
    rows.append(["RECS 2020 Table CE2.2, Northeast apartments in 5+ unit buildings, all (cross-check)", "Northeast",
                 "assumed_electric_use", round(4650 / 12), "kWh/month", "2020 (published 4,650 kWh/year per household)", RECS_CE22])
    for b, v in r["cook_therms_by_bed"].items():
        rows.append([f"RECS 2020 Northeast apartments 5+ units, {lab[b]}, gas cooking (n={v['n']})", "Northeast", "assumed_gas_use_cooking",
                     round(v["therms_year"] / 12, 2), "therms/month", "2020 (RECS microdata v7, BTUNGCOK)", RECS_MICRO])
    for b, v in r["sph_therms_by_bed"].items():
        rows.append([f"RECS 2020 Northeast apartments 5+ units, {lab[b]}, gas space heating (n={v['n']})", "Northeast", "assumed_gas_use_heating",
                     round(v["therms_year"] / 12, 2), "therms/month", "2020 (RECS microdata v7, BTUNGSPH)", RECS_MICRO])
    RATES_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(RATES_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utility", "state", "type", "price", "unit", "period", "source_url"])
        w.writerows(rows)


# ---- lookup ------------------------------------------------------------------------------
def _load() -> dict:
    global _IDX
    if _IDX is None:
        raw = pickle.loads(INDEX.read_bytes()) if INDEX.exists() else build()
        ix = dict(raw)
        for k in ("electric", "gas"):
            geoms = [wkb.loads(g) for _, g in raw[k]]
            ix[k] = dict(props=[p for p, _ in raw[k]], geoms=geoms, areas=[g.area for g in geoms], tree=STRtree(geoms))
        cg = [wkb.loads(g) for *_, g in raw["counties"]]
        ix["counties"] = dict(props=[(s, n) for s, n, _ in raw["counties"]], geoms=cg, tree=STRtree(cg))
        tg = [wkb.loads(g) for _, g in raw["ct_towns"]]
        ix["ct_towns"] = dict(props=[n for n, _ in raw["ct_towns"]], geoms=tg, tree=STRtree(tg))
        _IDX = ix
    return _IDX


def _hits(layer: dict, pt: Point, near_deg: float = 0.0) -> list[int]:
    out = [int(i) for i in layer["tree"].query(pt, predicate="intersects")]
    if not out and near_deg:
        i = layer["tree"].nearest(pt)
        if i is not None and layer["geoms"][int(i)].distance(pt) <= near_deg:
            out = [int(i)]
    return out


def _src(ix: dict, *names: str) -> list[dict]:
    return [dict(ix["src"][n]) for n in names if n in ix["src"]]


def locate(lat: float, lon: float) -> dict:
    """State, county and (in CT) town of the point. Points just offshore snap to the nearest county within ~1 km."""
    ix = _load()
    pt = Point(lon, lat)
    h = _hits(ix["counties"], pt, 0.012)
    state, county = ix["counties"]["props"][h[0]] if h else (None, None)
    town = None
    if state == "CT":
        t = _hits(ix["ct_towns"], pt, 0.012)
        town = ix["ct_towns"]["props"][t[0]] if t else None
    return dict(state=state, county=county, town=town)


def electric_utility(lat: float, lon: float) -> dict:
    """Electric utility serving the point: {value_type, utility_id, utility, state, method, notes, alternatives, sources}."""
    ix = _load()
    pt = Point(lon, lat)
    loc = locate(lat, lon)
    lay = ix["electric"]
    snapped = False
    h = _hits(lay, pt)
    if not h:
        h, snapped = _hits(lay, pt, 0.012), True
    cands = {}
    for i in h:
        try:
            cands[int(lay["props"][i]["ID"])] = lay["areas"][i]
        except (TypeError, ValueError):
            continue
    notes, alts = [], []
    # Override 1: the Fishers Island utility polygon is drawn as all of Suffolk County.
    if FISHERS in cands and not (lat > 41.22 and lon > -72.06):
        cands.pop(FISHERS)
    # Override 2: United Illuminating's polygon is drawn as all of Fairfield and New Haven counties.
    # UI serves 17 towns; the list comes from utility-by-municipality counts in CT Green Bank's RSIP data.
    if loc["state"] == "CT" and UI in cands:
        if loc["town"] in ix["ui_towns"]:
            cands.pop(CLP, None)
        else:
            cands.pop(UI)
        notes.append(f"CT town {loc['town']}: United Illuminating serves only {len(ix['ui_towns'])} towns; override applied")
    # Override 3: both Norwalk municipal polygons are drawn as the whole city. SNEW serves South Norwalk
    # (Second Taxing District), TTD serves East Norwalk (Third Taxing District); the rest is Eversource.
    if SNEW in cands or TTD in cands:
        alts = [k for k in (SNEW, TTD) if k in cands]
        for k in alts:
            cands.pop(k)
        notes.append("Norwalk: South Norwalk is served by SNEW and East Norwalk by the Third Taxing District; no district "
                     "boundary file was found, so Eversource is used and the two municipal utilities are listed as alternatives")
    if not cands:
        return dict(value_type="not_found", reason="no electric service territory polygon within about 1 km of the point",
                    location=loc, sources=_src(ix, "electric_territory"))
    uid = min(cands, key=cands.get)  # smallest polygon wins: a municipal utility inside a larger one
    if len(cands) > 1:
        notes.append("overlapping territories; the smallest polygon was taken: " + ", ".join(str(k) for k in sorted(cands, key=cands.get)))
    if snapped:
        notes.append("point is outside every polygon (water or pier); nearest territory within about 1 km used")
    name = next(p["NAME"] for p in lay["props"] if str(p["ID"]) == str(uid))
    eia_name = (_price(ix, uid, loc["state"]) or {}).get("name")
    return dict(value_type="estimate", utility_id=uid, utility=DISPLAY.get(uid, eia_name or name.title()), hifld_name=name,
                location=loc, alternatives=alts, notes=notes,
                method="point-in-polygon on HIFLD/ORNL Electric Retail Service Territories (2022 vintage), with documented overrides",
                sources=_src(ix, "electric_territory", "counties") + (_src(ix, "ct_towns", "ct_ui_towns") if loc["state"] == "CT" else []))


def _bed(beds) -> int:
    try:
        return max(0, min(3, int(beds)))
    except (TypeError, ValueError):
        return 1


def _price(ix, uid, state):
    return ix["prices"].get((uid, state)) or next((v for (n, _), v in ix["prices"].items() if n == uid), None)


def monthly_utilities(lat: float, lon: float, beds: int = 1, sqft: float | None = None,
                      heat_included: bool | None = None) -> dict:
    """Estimated monthly electric, gas and internet for an apartment at (lat, lon).

    beds: 0 = studio. sqft, when given, picks the electric use by size band instead of by bedrooms.
    heat_included: True = heat is in the rent; False = tenant pays heat; None = unknown (cooking-only gas is shown
    and flagged, with the cooking + heat figure alongside).
    """
    ix = _load()
    b = _bed(beds)
    recs = ix["recs"]
    eu = electric_utility(lat, lon)
    loc = eu.get("location") or locate(lat, lon)
    st = loc["state"]
    out = dict(lat=lat, lon=lon, beds=beds, sqft=sqft, heat_included=heat_included, location=loc, data_built_at=ix["built_at"])

    # ---- electric
    if sqft:
        band = next(x for x in recs["kwh_by_sqft"] if x["lo"] < sqft <= x["hi"] or (sqft <= 0 and x["lo"] == 0))
        kwh_y, n, basis = band["kwh_year"], band["n"], f"size band {band['lo']}-{band['hi'] if band['hi'] < 99999 else 'up'} sq ft"
    else:
        v = recs["kwh_by_bed"][b]
        kwh_y, n, basis = v["kwh_year"], v["n"], ("studio", "1 bedroom", "2 bedrooms", "3+ bedrooms")[b]
    kwh_m = round(kwh_y / 12)
    use_txt = (f"{kwh_m} kWh/month ({kwh_y} kWh/year): RECS 2020 microdata, Northeast (Middle Atlantic + New England) apartments in "
               f"5+ unit buildings whose main heat is not electric, {basis}, weighted mean, n={n}"
               + ("; small sample" if n < 30 else "")
               + f". Cross-check: published Table CE2.2 gives {recs['kwh_all']:,} kWh/year for all such apartments, electric heat included")
    if eu["value_type"] == "not_found":
        out["electric"] = dict(amount=None, value_type="not_found", reason=eu["reason"], sources=eu["sources"])
    else:
        p = _price(ix, eu["utility_id"], st)
        if not p:
            out["electric"] = dict(amount=None, value_type="not_found", utility=eu["utility"],
                                   reason=f"{eu['utility']} (EIA id {eu['utility_id']}) has no price row in EIA-861 2025 for NY, NJ, CT or PA",
                                   sources=eu["sources"] + _src(ix, "eia861"))
        else:
            eh = recs["elec_heat_kwh_by_bed"][b]
            line = dict(
                amount=round(p["cents_kwh"] / 100 * kwh_m), value_type="estimate", utility=eu["utility"], utility_eia_id=eu["utility_id"],
                price_cents_per_kwh=p["cents_kwh"], price_period=p["period"], price_basis=p["basis"], assumed_kwh_per_month=kwh_m,
                method=(f"{eu['utility']} average price {p['cents_kwh']} cents/kWh (EIA-861 {p['period']}, revenue / sales, {p['basis']}) "
                        f"x {use_txt}. Territory: {eu['method']}."),
                notes=list(eu["notes"]),
                state_average_context=ix["state_elec"].get(st),
                if_heat_is_electric_add=dict(
                    amount=round(p["cents_kwh"] / 100 * eh["kwh_year"] / 12), kwh_per_month=round(eh["kwh_year"] / 12),
                    note=f"RECS 2020 space-heating kWh in electrically heated Northeast apartments (5+ units), n={eh['n']}; "
                         "applies only if the tenant pays for electric heat. Not added to the amount."),
                sources=eu["sources"] + _src(ix, "eia861", "recs_micro", "recs_ce22"))
            if eu["alternatives"]:
                line["alternatives"] = []
                for k in eu["alternatives"]:
                    ap = _price(ix, k, st)
                    if ap:
                        line["alternatives"].append(dict(utility=DISPLAY.get(k, str(k)), price_cents_per_kwh=ap["cents_kwh"],
                                                         price_basis=ap["basis"], amount=round(ap["cents_kwh"] / 100 * kwh_m)))
            out["electric"] = line

    # ---- gas
    out["gas"] = _gas_line(ix, lat, lon, loc, b, heat_included, rockaways=eu.get("utility_id") == 11171 and loc["county"] == "Queens")

    # ---- internet
    d = INTERNET["default"]
    out["internet"] = dict(
        amount=d["price"], value_type="estimate", provider_basis=d["provider"], plan=d["plan"],
        method=(f"flat figure, the same for every address: {d['provider']} {d['plan']}, {d['note']}. Not address-specific; "
                "availability at the address was not checked. " + ("Fios is not sold in Connecticut; the figure is a stand-in there." if st == "CT" else "")).strip(),
        alternatives=INTERNET["alternatives"],
        sources=_src(ix, "fios", "optimum", "fcc_urs"))

    amts = [out[k].get("amount") for k in ("electric", "gas", "internet")]
    out["total"] = dict(amount=round(sum(a for a in amts if a is not None)), value_type="estimate",
                        complete=all(a is not None for a in amts),
                        method="sum of the electric, gas and internet amounts above (lines that are not_found count as 0)")
    return out


def _gas_utility(ix, pt: Point, loc: dict) -> dict:
    lay = ix["gas"]
    h = _hits(lay, pt, 0.03)
    if not h:
        return dict(name=None, key=None, notes=["no gas territory polygon within about 3 km (the building may have no gas service)"])
    i = min(h, key=lambda j: lay["areas"][j])
    name = lay["props"][i]["NAME"]
    notes, key = [], None
    if name.startswith("CONSOLIDATED"):
        name, key = "Con Edison (gas)", "CONED"
    elif name == "NATIONAL GRID" and loc["state"] == "NY":
        if loc["county"] in ("Nassau", "Suffolk"):
            key = "KEDLI"
        elif loc["county"] in ("Kings", "Queens", "Richmond"):
            key = "KEDNY"
            if loc["county"] == "Queens":
                notes.append("Queens is split: northern Queens (for example Astoria, Long Island City, Flushing) is Con Edison gas "
                             f"(minimum ${GAS_MIN_CHARGE['CONED']['price']:.2f}/month) and the Rockaways are National Grid Long Island "
                             f"(${GAS_MIN_CHARGE['KEDLI']['price']:.2f}); the territory layer is too coarse to tell, so National Grid NY is assumed")
        name = GAS_MIN_CHARGE[key]["utility"] if key else "National Grid"
    elif name.startswith("PUBLIC SERVICE"):
        name, key = "PSE&G (gas)", "PSEG"
    else:
        name = GAS_DISPLAY.get(name, name.title())
    return dict(name=name, key=key, notes=notes)


def _gas_line(ix, lat, lon, loc, b, heat_included, rockaways: bool = False) -> dict:
    st = loc["state"]
    recs = ix["recs"]
    gp = ix["gas_price"].get(st)
    if not gp:
        return dict(amount=None, value_type="not_found", reason="point is outside NY, NJ, CT and PA; no state gas price loaded", sources=[])
    gu = _gas_utility(ix, Point(lon, lat), loc)
    if rockaways:  # Queens point whose electric utility is LIPA = the Rockaway peninsula, which is National Grid Long Island for gas
        gu = dict(name=GAS_MIN_CHARGE["KEDLI"]["utility"], key="KEDLI",
                  notes=["Rockaway peninsula (Queens, electric service from LIPA): gas is taken as National Grid Long Island"])
    cook, sph, wth = recs["cook_therms_by_bed"][b], recs["sph_therms_by_bed"][b], recs["wth_therms_by_bed"][b]
    cook_m, heat_m = cook["therms_year"] / 12, sph["therms_year"] / 12
    price_txt = (f"{st} average residential gas price ${gp['usd_therm']:.3f}/therm (EIA {gp['year']} annual, ${gp['usd_mcf']:.2f}/Mcf "
                 f"at {gp['btu_cf']:.0f} Btu per cubic foot)")
    notes = list(gu["notes"])
    srcs = _src(ix, "gas_territory", f"ng_price_{st}", "ng_heat", "recs_micro")
    t = GAS_MIN_CHARGE.get(gu["key"])
    if t:
        extra = max(0.0, cook_m - t["included_therms"]) * t.get("per_therm", 0.0) if t["included_therms"] == 0 else 0.0
        cook_amt = round(t["price"] + extra)
        cook_method = (f"{t['utility']} {t['tariff']}: ${t['price']:.2f}/month "
                       + ("covers the first 3 therms or less" if t["included_therms"] else f"fixed part plus ${t['per_therm']:.4f}/therm, both derived from the utility's published bill table")
                       + f" ({t['period']}); assumed cooking use {cook_m:.1f} therms/month (RECS 2020 microdata, Northeast apartments in 5+ unit "
                       f"buildings with gas cooking, n={cook['n']}). "
                       + ("Gas supply cost for those therms, surcharges and taxes are not included (a few dollars)." if t["included_therms"] else ""))
        srcs = srcs + _src(ix, f"gas_tariff_{gu['key']}")
        understated = False
    else:
        cook_amt = round(gp["usd_therm"] * cook_m)
        cook_method = (f"{price_txt} x {cook_m:.1f} therms/month cooking use (RECS 2020 microdata, Northeast apartments in 5+ unit buildings "
                       f"with gas cooking, n={cook['n']}). No tariff is held for {gu['name'] or 'the gas utility here'}, so the fixed monthly "
                       "customer charge is missing and this figure is too low; utilities whose tariffs we hold charge $10 to $33 a month before any use.")
        understated = True
    heat_amt = cook_amt + round(gp["usd_therm"] * heat_m)
    heat_method = (f"cooking-only figure (${cook_amt}) + {price_txt} x {heat_m:.1f} therms/month of space heating (annual use / 12; "
                   f"RECS 2020 microdata, Northeast apartments in 5+ unit buildings heated with gas, n={sph['n']}). "
                   "An annual average: winter bills are several times higher and summer bills lower. Water heating is not included.")
    water = dict(amount=round(gp["usd_therm"] * wth["therms_year"] / 12), therms_per_month=round(wth["therms_year"] / 12, 1),
                 note=f"only if the unit has its own gas water heater; RECS 2020, n={wth['n']}. Not added to the amount.")
    line = dict(value_type="estimate", gas_utility=gu["name"], state_price_usd_per_therm=gp["usd_therm"], price_period=str(gp["year"]),
                cooking_only=dict(amount=cook_amt, therms_per_month=round(cook_m, 1), method=cook_method, likely_understated=understated),
                cooking_plus_heat=dict(amount=heat_amt, therms_per_month=round(cook_m + heat_m, 1), method=heat_method),
                if_gas_water_heater_add=water, notes=notes, sources=srcs)
    if heat_included is False:
        line.update(amount=heat_amt, basis="cooking_plus_heat", method=heat_method, heat_may_be_extra=False)
        notes.append("heat_included=False: gas heat is assumed. If the heat is electric, use the cooking-only figure here and "
                     "electric.if_heat_is_electric_add instead.")
    else:
        line.update(amount=cook_amt, basis="cooking_only", method=cook_method, heat_may_be_extra=heat_included is None)
        if heat_included is None:
            notes.append("whether heat is included is unknown: the cooking-only figure is shown; heat may be extra (see cooking_plus_heat)")
    if understated:
        notes.append("cooking-only figure excludes the utility's fixed monthly charge (no tariff held) and is too low")
    notes.append("assumes the unit has a gas stove; an all-electric unit has no gas bill")
    return line


# ---- self-test ---------------------------------------------------------------------------
TEST_POINTS = [("Jamaica station", 40.699608, -73.808530), ("Forest Hills", 40.7196, -73.8448),
               ("Long Beach NY", 40.5890, -73.6649), ("Stamford CT", 41.0469, -73.5419),
               ("Jersey City Grove St", 40.7196, -74.0431), ("Beacon NY", 41.5060, -73.9845)]

if __name__ == "__main__":
    if "--build" in sys.argv:
        t0 = time.time()
        _IDX = None
        build()
        print(f"built index and {RATES_CSV.relative_to(lib.ROOT)} in {time.time() - t0:.1f}s")
    t0 = time.time()
    _load()
    print(f"index load: {time.time() - t0:.2f}s")
    extra = [("Rockville Centre", 40.6587, -73.6412), ("South Norwalk", 41.0965, -73.4218), ("Bridgeport CT", 41.18, -73.19)] \
        if "--more" in sys.argv else []
    for name, la, lo in TEST_POINTS + extra:
        t0 = time.time()
        r = monthly_utilities(la, lo, beds=1)
        dt = time.time() - t0
        if "--json" in sys.argv:
            print(json.dumps({name: r}, indent=1))
            continue
        e, g, i = r["electric"], r["gas"], r["internet"]
        print(f"\n== {name} ({la}, {lo}) [{dt * 1000:.1f} ms] {r['location']}")
        print(f"  electric  ${e.get('amount')}* {e['value_type']}: {e.get('utility')} @ {e.get('price_cents_per_kwh')} c/kWh x {e.get('assumed_kwh_per_month')} kWh")
        print(f"  gas       ${g.get('amount')}* {g['value_type']} ({g.get('basis')}): {g.get('gas_utility')}; cooking+heat ${g.get('cooking_plus_heat', {}).get('amount')}"
              f"{' [cooking-only understated]' if g.get('cooking_only', {}).get('likely_understated') else ''}")
        print(f"  internet  ${i['amount']}* {i['value_type']}: {i['provider_basis']} {i['plan'][:8]}")
        print(f"  total     ${r['total']['amount']}* complete={r['total']['complete']}")
        for n in e.get("notes", []) + g.get("notes", []):
            print("    note:", n)
        if "--verbose" in sys.argv or name == TEST_POINTS[0][0]:
            for k in ("electric", "gas", "internet"):
                print(f"  {k} method:", r[k].get("method") or r[k].get("reason"))
                print(f"  {k} sources:", [(s["source_url"][:90], s["retrieved_at"]) for s in r[k].get("sources", [])])
