"""Phase 1, domain `walkability`.

EPA National Walkability Index (Smart Location Database v3, block-group level, 2010 block groups)
joined to Census TIGER/Line 2019 block groups (2010-vintage boundaries, same GEOIDs as SLD v3).

Per area:
  * epa_nwi_containing_bg      NWI of the block group containing the centroid (found)
  * epa_nwi_mean_800m_popw     population-weighted mean NWI of block groups whose TIGER internal
                               point lies within 800 m of the centroid (estimate; weights = SLD TotPop)
  * epa_nwi_mean_800m_simple   simple mean of the same block groups (estimate)
  * walk_score                 not_found (needs a Walk Score API key)

Idempotent: bulk files are downloaded to raw/big/<source>/ only if missing; output is rewritten.
Run: python3 -I scripts/p1_walkability.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import ROOT, USER_AGENT, now_iso  # noqa: E402

DOMAIN = "walkability"
OUT = ROOT / "data" / "metrics" / "walkability.csv"
COLS = ["area_id", "domain", "metric", "value", "unit", "geography", "period", "source", "source_url",
        "retrieved_at", "raw_path", "value_type", "method", "population_used", "notes"]

SLD_URL = "https://edg.epa.gov/EPADataCommons/public/OA/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv"
SLD_FILE = "EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv"
TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2019/BG/tl_2019_{st}_bg.zip"
STATES = ["36", "34", "09", "42"]  # NY, NJ, CT, PA
SLD_PERIOD = "SLD v3 (2021-01; inputs 2017-2019)"
RADIUS_M = 800


def big_download(url: str, source: str, filename: str) -> tuple[Path, dict]:
    """Stream a bulk file to raw/big/<source>/<filename> if missing; log to that folder's _index.jsonl."""
    d = ROOT / "raw" / "big" / source
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    idx = d / "_index.jsonl"
    entries = []
    if idx.exists():
        entries = [json.loads(l) for l in idx.read_text().splitlines() if l.strip()]
    prior = [e for e in entries if e.get("url") == url and e.get("status") == 200]
    if path.exists() and path.stat().st_size > 0:
        if prior:
            return path, prior[-1]
        # File was fetched by hand earlier; record it now, using its mtime as retrieval time.
        from datetime import datetime, timezone
        ts = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()
        meta = {"url": url, "retrieved_at": ts, "status": 200, "path": str(path.relative_to(ROOT)),
                "source": source, "bytes": path.stat().st_size}
    else:
        tmp = path.with_suffix(path.suffix + ".part")
        with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        tmp.rename(path)
        meta = {"url": url, "retrieved_at": now_iso(), "status": 200, "path": str(path.relative_to(ROOT)),
                "source": source, "bytes": path.stat().st_size}
    with open(idx, "a") as f:
        f.write(json.dumps(meta) + "\n")
    return path, meta


def hav_m(lat1, lon1, lat2, lon2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_sld(path: Path) -> dict[str, dict]:
    """GEOID10 in the CSV is in scientific notation (lossy), so rebuild it from the FIPS parts."""
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["STATEFP"].zfill(2) not in STATES:
                continue
            geoid = (row["STATEFP"].zfill(2) + row["COUNTYFP"].zfill(3) + row["TRACTCE"].zfill(6)
                     + row["BLKGRPCE"].strip())
            out[geoid] = {"nwi": float(row["NatWalkInd"]), "pop": float(row["TotPop"] or 0)}
    return out


def main():
    import geopandas as gpd
    from shapely.geometry import Point

    sld_path, sld_meta = big_download(SLD_URL, "epa_sld", SLD_FILE)
    sld = load_sld(sld_path)
    print(f"SLD rows in NY/NJ/CT/PA: {len(sld)}")

    frames, tmetas = [], {}
    for st in STATES:
        url = TIGER_URL.format(st=st)
        p, m = big_download(url, "tiger_bg", f"tl_2019_{st}_bg.zip")
        tmetas[st] = m
        frames.append(gpd.read_file(f"zip://{p}"))
    bg = gpd.GeoDataFrame(__import__("pandas").concat(frames, ignore_index=True), crs=frames[0].crs)
    bg["ilat"] = bg["INTPTLAT"].astype(float)
    bg["ilon"] = bg["INTPTLON"].astype(float)
    sidx = bg.sindex
    print(f"TIGER 2019 block groups: {len(bg)}")

    areas = list(csv.DictReader(open(ROOT / "data" / "areas.csv")))
    rows = []

    def row(a, metric, value, unit, geography, value_type, method="", notes="", population_used="",
            source="epa_sld_v3", source_url=SLD_URL, retrieved_at=None, raw_path=None, period=SLD_PERIOD):
        rows.append({"area_id": a["id"], "domain": DOMAIN, "metric": metric, "value": value, "unit": unit,
                     "geography": geography, "period": period, "source": source, "source_url": source_url,
                     "retrieved_at": retrieved_at if retrieved_at is not None else sld_meta["retrieved_at"],
                     "raw_path": raw_path if raw_path is not None else sld_meta["path"],
                     "value_type": value_type, "method": method, "population_used": population_used,
                     "notes": notes})

    for a in areas:
        lat, lon = float(a["centroid_lat"]), float(a["centroid_lon"])
        st = a["tract_geoid"][:2] if a.get("tract_geoid") else ""
        tm = tmetas.get(st, tmetas["36"])
        tiger_note = f"BG geometry: {tm['url']}"
        pt = Point(lon, lat)
        cand = bg.iloc[list(sidx.query(pt, predicate="intersects"))]
        if len(cand):
            g = cand.iloc[0]["GEOID"]
            rec = sld.get(g)
            if rec is not None and rec["nwi"] > 0:
                row(a, "epa_nwi_containing_bg", round(rec["nwi"], 3), "index_1_20", f"bg:{g}", "found",
                    method="point-in-polygon of area centroid in TIGER/Line 2019 block groups; NatWalkInd joined on GEOID rebuilt from STATEFP+COUNTYFP+TRACTCE+BLKGRPCE",
                    notes=f"{tiger_note}; BG TotPop (SLD, ACS 2018 5-yr) = {int(rec['pop'])}")
            else:
                row(a, "epa_nwi_containing_bg", "", "index_1_20", f"bg:{g}", "not_found",
                    notes=f"Centroid falls in BG {g} which has no NatWalkInd in SLD v3 CSV; {tiger_note}")
        else:
            row(a, "epa_nwi_containing_bg", "", "index_1_20", "", "not_found",
                notes=f"Centroid not inside any TIGER 2019 block group (water?); {tiger_note}")

        # Block groups whose internal point lies within 800 m.
        dlat = RADIUS_M / 111000 * 1.2
        dlon = dlat / math.cos(math.radians(lat))
        near = bg[(bg.ilat.between(lat - dlat, lat + dlat)) & (bg.ilon.between(lon - dlon, lon + dlon))]
        sel = []
        for _, r in near.iterrows():
            if hav_m(lat, lon, r.ilat, r.ilon) <= RADIUS_M:
                rec = sld.get(r["GEOID"])
                if rec is not None and rec["nwi"] > 0:
                    sel.append((r["GEOID"], rec["nwi"], rec["pop"]))
        if sel:
            simple = sum(s[1] for s in sel) / len(sel)
            tot = sum(s[2] for s in sel)
            meth = (f"block groups with TIGER 2019 INTPTLAT/INTPTLON within {RADIUS_M} m (haversine) of area "
                    f"centroid: n={len(sel)}")
            row(a, "epa_nwi_mean_800m_simple", round(simple, 3), "index_1_20", "radius_800m", "estimate",
                method=meth + "; unweighted mean of NatWalkInd", notes=tiger_note)
            if tot > 0:
                pw = sum(s[1] * s[2] for s in sel) / tot
                row(a, "epa_nwi_mean_800m_popw", round(pw, 3), "index_1_20", "radius_800m", "estimate",
                    method=meth + "; mean of NatWalkInd weighted by SLD TotPop",
                    population_used=f"SLD v3 TotPop (ACS 2014-2018), sum={int(tot)}", notes=tiger_note)
            else:
                row(a, "epa_nwi_mean_800m_popw", "", "index_1_20", "radius_800m", "not_found",
                    notes=f"{len(sel)} BGs within 800 m but all have TotPop 0; {tiger_note}")
        else:
            for m in ("epa_nwi_mean_800m_simple", "epa_nwi_mean_800m_popw"):
                row(a, m, "", "index_1_20", "radius_800m", "not_found",
                    notes=f"No block group internal point with an SLD NatWalkInd within {RADIUS_M} m; {tiger_note}")

        row(a, "walk_score", "", "score_0_100", "point:centroid", "not_found", source="walkscore",
            source_url="https://www.walkscore.com/professional/api.php", retrieved_at="", raw_path="",
            period="", notes="needs a Walk Score API key")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f"wrote {len(rows)} rows to {OUT}")
    print(Counter((r["metric"], r["value_type"]) for r in rows))


if __name__ == "__main__":
    main()
