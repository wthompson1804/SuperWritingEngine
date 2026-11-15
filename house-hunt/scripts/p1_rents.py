"""Phase 1, domain `rent`: Zillow ZORI (ZIP), Apartment List rent estimates (city, county),
HUD FY2026 Small Area FMRs (ZIP) and HUD FMRs (FMR area at the centroid).

Writes data/metrics/rents.csv. Idempotent: the CSV is rebuilt from the raw cache each run.
All HTTP goes through lib.cached_get, so a re-run refetches nothing unless the cache is gone.

Sources are kept separate: each metric name belongs to exactly one source.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import DATA, ROOT, cached_get, get_json  # noqa: E402

OUT = DATA / "metrics" / "rents.csv"
COLS = ["area_id", "domain", "metric", "value", "unit", "geography", "period", "source", "source_url",
        "retrieved_at", "raw_path", "value_type", "method", "population_used", "notes"]

ZORI_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv"
# Multifamily-only ZORI is published for Metro/US only; the ZIP-level file does not exist (HTTP 404).
ZORI_MFR_ZIP_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_mfr_sm_month.csv"
ZILLOW_RESEARCH = "https://www.zillow.com/research/data/"

AL_PAGE = "https://www.apartmentlist.com/research/category/data-rent-estimates"

ARCGIS = "https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services"
SAFMR_TABLE = f"{ARCGIS}/HUD_PDR_Small_Area_Fair_Market_Rents/FeatureServer/1/query"
FMR_LAYER = f"{ARCGIS}/Fair_Market_Rents/FeatureServer/0/query"
HUD_SAFMR_PAGE = "https://www.huduser.gov/portal/datasets/fmr/smallarea/index.html"
HUD_FY = "FY2026"


def rel(p: str) -> str:
    return p


def row(area_id, metric, value, unit, geography, period, source, source_url, meta, value_type,
        method="", population_used="", notes=""):
    return {"area_id": area_id, "domain": "rent", "metric": metric,
            "value": "" if value is None else value, "unit": unit, "geography": geography,
            "period": period, "source": source, "source_url": source_url,
            "retrieved_at": meta.get("retrieved_at", "") if meta else "",
            "raw_path": meta.get("path", "") if meta else "", "value_type": value_type,
            "method": method, "population_used": population_used, "notes": notes}


def load_areas():
    with open(DATA / "areas.csv") as f:
        return list(csv.DictReader(f))


def ring_zctas(a):
    zs = a["zctas_within_800m"].split()
    if a["zcta_centroid"] and a["zcta_centroid"] not in zs:
        zs.insert(0, a["zcta_centroid"])
    return zs


# ---------------------------------------------------------------- Zillow ZORI
def zori_rows(areas):
    content, meta = cached_get(ZORI_URL, "big/zillow", ext="csv", timeout=600)
    if meta["status"] != 200:
        raise RuntimeError(f"ZORI download failed: {meta}")
    # record the MFR-ZIP check (404 expected) and the research page in the cache/index
    for u in (ZORI_MFR_ZIP_URL, ZILLOW_RESEARCH):
        try:
            cached_get(u, "zillow", ext="csv" if u.endswith(".csv") else "html", timeout=120)
        except RuntimeError:
            pass
    rdr = csv.DictReader(io.StringIO(content.decode("utf-8")))
    date_cols = [c for c in rdr.fieldnames if re.fullmatch(r"\d{4}-\d{2}-\d{2}", c)]
    latest_col = date_cols[-1]
    y, m = int(latest_col[:4]), int(latest_col[5:7])
    prior_prefix = f"{y - 1}-{m:02d}"
    prior_col = next(c for c in date_cols if c.startswith(prior_prefix))
    latest_p, prior_p = latest_col[:7], prior_col[:7]
    data = {r["RegionName"].zfill(5): r for r in rdr}
    src = "zillow_zori"
    out = []

    def one(area_id, z, suffix):
        geo = f"zcta:{z}"
        r = data.get(z)
        m_lat, m_pri, m_yoy = f"zori_all_homes{suffix}", f"zori_all_homes_prior12m{suffix}", f"zori_all_homes_yoy_pct{suffix}"
        note_geo = "ZORI is by USPS ZIP; matched on the ZCTA code (ZCTAs approximate ZIPs)."
        if r is None:
            nf = f"ZIP {z} not in Zillow ZORI all-homes smoothed ZIP file ({latest_p} vintage). {note_geo}"
            return [row(area_id, m_lat, None, "usd_month", geo, latest_p, src, ZORI_URL, meta, "not_found", notes=nf),
                    row(area_id, m_pri, None, "usd_month", geo, prior_p, src, ZORI_URL, meta, "not_found", notes=nf),
                    row(area_id, m_yoy, None, "pct", geo, f"{prior_p}..{latest_p}", src, ZORI_URL, meta, "not_found", notes=nf)]
        lv, pv = r[latest_col].strip(), r[prior_col].strip()
        res = []
        if lv:
            res.append(row(area_id, m_lat, round(float(lv), 2), "usd_month", geo, latest_p, src, ZORI_URL, meta, "found",
                           notes=f"ZORI smoothed, all homes plus multifamily (SFR+condo+MFR). {note_geo}"))
        else:
            res.append(row(area_id, m_lat, None, "usd_month", geo, latest_p, src, ZORI_URL, meta, "not_found",
                           notes=f"ZIP {z} in ZORI file but blank for {latest_p}."))
        if pv:
            res.append(row(area_id, m_pri, round(float(pv), 2), "usd_month", geo, prior_p, src, ZORI_URL, meta, "found",
                           notes="ZORI smoothed, all homes plus multifamily; value 12 months before latest."))
        else:
            first = next((c[:7] for c in date_cols if r[c].strip()), None)
            res.append(row(area_id, m_pri, None, "usd_month", geo, prior_p, src, ZORI_URL, meta, "not_found",
                           notes=f"ZIP {z} has no ZORI value for {prior_p}; series starts {first}."))
        if lv and pv:
            yoy = (float(lv) / float(pv) - 1) * 100
            res.append(row(area_id, m_yoy, round(yoy, 2), "pct", geo, f"{prior_p}..{latest_p}", src, ZORI_URL, meta,
                           "estimate", method=f"(ZORI {latest_p} / ZORI {prior_p} - 1) * 100"))
        else:
            res.append(row(area_id, m_yoy, None, "pct", geo, f"{prior_p}..{latest_p}", src, ZORI_URL, meta, "not_found",
                           notes=f"Needs both {latest_p} and {prior_p} ZORI values for ZIP {z}; at least one is missing."))
        return res

    for a in areas:
        out += one(a["id"], a["zcta_centroid"], "")          # area level: centroid ZCTA
        for z in ring_zctas(a):                               # each ZCTA within 800 m
            out += one(a["id"], z, "_zcta")
    return out, latest_p


# ---------------------------------------------------------------- Apartment List
def apartmentlist_rows(areas):
    page, pmeta = cached_get(AL_PAGE, "apartmentlist", ext="html")
    html = page.decode("utf-8", "replace")
    links = sorted(set(re.findall(r"https?://assets\.ctfassets\.net/[^\"'\\\s]+?\.csv", html)))
    if not links:
        links = ["https:" + l for l in sorted(set(re.findall(r"//assets\.ctfassets\.net/[^\"'\\\s]+?\.csv", html)))]
    est_url = next(l for l in links if re.search(r"/Apartment_List_Rent_Estimates_\d{4}_\d{2}\.csv$", l))
    sum_url = next(l for l in links if re.search(r"/Apartment_List_Rent_Estimates_Summary_\d{4}_\d{2}\.csv$", l))
    est, emeta = cached_get(est_url, "apartmentlist", ext="csv", timeout=300)
    summ, smeta = cached_get(sum_url, "apartmentlist", ext="csv", timeout=300)
    erows = list(csv.DictReader(io.StringIO(est.decode("utf-8"))))
    srows = list(csv.DictReader(io.StringIO(summ.decode("utf-8"))))
    month_cols = [c for c in erows[0].keys() if re.fullmatch(r"\d{4}_\d{2}", c)]
    latest = month_cols[-1]
    period = latest.replace("_", "-")
    beds = sorted({r["bed_size"] for r in erows})
    idx = {}
    for r in erows:
        idx[(r["location_type"], int(r["location_fips_code"]), r["bed_size"])] = r
    sidx = {(r["location_type"], int(r["location_fips_code"])): r for r in srows}
    src = "apartmentlist"
    out = []
    for a in areas:
        aid = a["id"]
        targets = [("City", a["place_geoid"], f"place:{a['place_geoid']}", "", f"{a['municipality']}, {a['state']}"),
                   ("County", a["county_fips"], f"county:{a['county_fips']}", "_county", a["county"])]
        for ltype, code, geo, suf, label in targets:
            code_i = int(code) if code and code.isdigit() else None
            for bed, metric in (("overall", f"apartmentlist_overall{suf}"), ("1br", f"apartmentlist_1br{suf}"),
                                ("studio", f"apartmentlist_studio{suf}")):
                r = idx.get((ltype, code_i, bed)) if code_i is not None else None
                if bed == "studio":
                    out.append(row(aid, metric, None, "usd_month", geo, period, src, est_url, emeta, "not_found",
                                   notes=f"Apartment List publishes only overall, 1br and 2br (bed_size values: {', '.join(beds)}); no studio series."))
                    continue
                if r is None:
                    if ltype == "City":
                        nf = (f"No Apartment List City row with location_fips_code = place GEOID {code} ({label}). "
                              f"Apartment List covers a limited set of cities; checked {est_url.rsplit('/',1)[-1]}.")
                    else:
                        nf = (f"No Apartment List County row with FIPS {code} ({label})."
                              + (" CT county FIPS here are 2022+ planning regions (091xx); Apartment List uses the old CT counties."
                                 if code.startswith("091") else ""))
                    out.append(row(aid, metric, None, "usd_month", geo, period, src, est_url, emeta, "not_found", notes=nf))
                    continue
                v = r[latest].strip()
                if not v or v.upper() == "NA":
                    out.append(row(aid, metric, None, "usd_month", geo, period, src, est_url, emeta, "not_found",
                                   notes=f"{r['location_name']} row present but blank for {period}."))
                else:
                    out.append(row(aid, metric, round(float(v), 2), "usd_month", geo, period, src, est_url, emeta, "found",
                                   notes=f"Apartment List rent estimate for '{r['location_name']}' ({ltype}), bed_size={bed}. "
                                         f"Matched on FIPS {code}." + (" Whole New York City, not the borough or neighbourhood."
                                                                         if code == "3651000" else "")))
            # YoY from the summary file (Apartment List's own figure, overall unit mix)
            s = sidx.get((ltype, code_i)) if code_i is not None else None
            metric = f"apartmentlist_yoy_pct{suf}"
            if s and s["rent_change_yoy"].strip() not in ("", "NA"):
                speriod = f"{s['year']}-{int(s['month']):02d}"
                out.append(row(aid, metric, round(float(s["rent_change_yoy"]) * 100, 2), "pct", geo, speriod, src, sum_url,
                               smeta, "found", notes=f"Apartment List rent_change_yoy for '{s['location_name']}', overall; "
                                                       "published as a fraction, multiplied by 100 here."))
            else:
                out.append(row(aid, metric, None, "pct", geo, period, src, sum_url, smeta, "not_found",
                               notes=f"No Apartment List summary row for {ltype} FIPS {code} ({label})."))
    return out, period, est_url, sum_url


# ---------------------------------------------------------------- HUD SAFMR / FMR
def hud_rows(areas):
    zips = sorted({z for a in areas for z in ring_zctas(a)})
    saf = {}
    smeta_by_zip = {}
    for i in range(0, len(zips), 50):
        chunk = zips[i:i + 50]
        params = {"where": "ID in (" + ",".join(f"'{z}'" for z in chunk) + ")",
                  "outFields": "HUD_CODE,FMR_NAME,SAFMR_0BR,SAFMR_1BR,ID", "returnGeometry": "false",
                  "orderByFields": "ID", "resultRecordCount": 2000, "f": "json"}
        d, meta = get_json(SAFMR_TABLE, "hud_arcgis", params=params)
        if "error" in d or d.get("exceededTransferLimit"):
            raise RuntimeError(f"SAFMR query problem: {d.get('error')}")
        for f in d["features"]:
            at = f["attributes"]
            saf.setdefault(at["ID"], []).append(at)
        for z in chunk:
            smeta_by_zip[z] = meta
    fmr = {}
    for a in areas:
        params = {"geometry": f"{a['centroid_lon']},{a['centroid_lat']}", "geometryType": "esriGeometryPoint",
                  "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
                  "outFields": "FMR_CODE,FMR_AREANAME,FMR_0BDR,FMR_1BDR", "returnGeometry": "false", "f": "json"}
        d, meta = get_json(FMR_LAYER, "hud_arcgis", params=params)
        fmr[a["id"]] = (d.get("features", []), meta)

    src_s, src_f = "hud_safmr", "hud_fmr"
    out = []
    for a in areas:
        aid = a["id"]
        ffeats, fmeta = fmr[aid]
        furl = fmeta["url"]
        fcode = ffeats[0]["attributes"]["FMR_CODE"] if len(ffeats) == 1 else None
        # FMR (FMR area containing the centroid) for every area
        if len(ffeats) == 1:
            at = ffeats[0]["attributes"]
            for b, fld in (("0br", "FMR_0BDR"), ("1br", "FMR_1BDR")):
                out.append(row(aid, f"fmr_{b}", at[fld], "usd_month", f"hud_fmr_area:{at['FMR_CODE']}", HUD_FY, src_f, furl,
                               fmeta, "found", method="FMR area polygon containing the area centroid (point-in-polygon on HUD's layer)",
                               notes=f"{at['FMR_AREANAME']}. HUD FMR = gross rent (rent + tenant-paid utilities), 40th percentile."))
        else:
            for b in ("0br", "1br"):
                out.append(row(aid, f"fmr_{b}", None, "usd_month", "", HUD_FY, src_f, furl, fmeta, "not_found",
                               notes=f"Point query on HUD Fair_Market_Rents layer returned {len(ffeats)} polygons."))

        def pick(z):
            recs = saf.get(z, [])
            if len(recs) <= 1:
                return (recs[0] if recs else None), ""
            vals = {(r["SAFMR_0BR"], r["SAFMR_1BR"]) for r in recs}
            match = [r for r in recs if r["HUD_CODE"] == fcode]
            chosen = match[0] if match else recs[0]
            others = "; ".join(f"{r['HUD_CODE']} ({r['FMR_NAME']})" for r in recs)
            note = (f"ZIP {z} appears under {len(recs)} HUD FMR areas: {others}. "
                    + ("Values identical across them. " if len(vals) == 1 else "Values differ; ")
                    + ("Used the row for the centroid's FMR area." if match else "Used the first row; centroid FMR area not among them."))
            return chosen, note

        for z, suf in [(a["zcta_centroid"], "")] + [(z, "_zcta") for z in ring_zctas(a)]:
            rec, mnote = pick(z)
            smeta = smeta_by_zip[z]
            surl = smeta["url"]
            for b, fld in (("0br", "SAFMR_0BR"), ("1br", "SAFMR_1BR")):
                if rec and rec.get(fld) is not None:
                    out.append(row(aid, f"safmr_{b}{suf}", rec[fld], "usd_month", f"zcta:{z}", HUD_FY, src_s, surl, smeta,
                                   "found", notes=(f"HUD SAFMR {HUD_FY}, ZIP {z}, {rec['FMR_NAME']} ({rec['HUD_CODE']}). "
                                                   "Gross rent incl. tenant-paid utilities. " + mnote).strip()))
                else:
                    fb = ""
                    if len(ffeats) == 1:
                        fb = (f" Fallback: see fmr_{b} for FMR area {fcode} "
                              f"({ffeats[0]['attributes']['FMR_AREANAME']}).")
                    out.append(row(aid, f"safmr_{b}{suf}", None, "usd_month", f"zcta:{z}", HUD_FY, src_s, surl, smeta,
                                   "not_found", notes=f"ZIP {z} not in HUD {HUD_FY} SAFMR table (HUD eGIS SAFMR_table, ID field).{fb}"))
    return out


def main():
    areas = load_areas()
    rows = []
    z, zp = zori_rows(areas)
    rows += z
    al, alp, _, _ = apartmentlist_rows(areas)
    rows += al
    rows += hud_rows(areas)
    # de-duplicate on the natural key, keep first
    seen, final = set(), []
    for r in rows:
        k = (r["area_id"], r["metric"], r["source"], r["period"], r["geography"])
        if k in seen:
            continue
        seen.add(k)
        final.append(r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(final)
    tmp.replace(OUT)
    from collections import Counter
    c = Counter((r["metric"], r["value_type"]) for r in final)
    print(f"wrote {len(final)} rows to {OUT.relative_to(ROOT)}; ZORI {zp}, Apartment List {alp}")
    for k in sorted(c):
        print(f"  {k[0]:32s} {k[1]:10s} {c[k]}")


if __name__ == "__main__":
    main()
