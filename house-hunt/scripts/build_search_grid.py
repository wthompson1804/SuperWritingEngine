"""Search grid: every ZCTA whose internal point is within a 2-hour free-flow drive of Jamaica station.

ZCTA points: Census 2024 Gazetteer. Drive: OSRM public table service (free-flow, no traffic) -> estimate.
Output: data/reference/search_grid.csv (zcta, lat, lon, state, drive_min, drive_miles), sorted nearest first.
"""
import csv, io, math, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, cached_get, get_json

JAM = (40.699608, -73.808530)
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_zcta_national.zip"
PREFIX_STATE = {"06": "CT", "07": "NJ", "08": "NJ", "10": "NY", "11": "NY", "12": "NY", "18": "PA", "19": "PA"}


def hav_mi(a, b):
    R = 3958.8
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def main():
    content, _ = cached_get(GAZ, "census_gazetteer", ext="zip", timeout=180)
    z = zipfile.ZipFile(io.BytesIO(content))
    rows = list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]), "utf-8"), delimiter="\t"))
    pts = []
    for r in rows:
        r = {k.strip(): v.strip() for k, v in r.items()}
        zc = r["GEOID"]
        if zc[:2] not in PREFIX_STATE:
            continue
        p = (float(r["INTPTLAT"]), float(r["INTPTLONG"]))
        if hav_mi(JAM, p) <= 110:  # 2 h at highway speed can't exceed this crow-fly
            pts.append((zc, p))
    print(len(pts), "ZCTAs within 110 mi", flush=True)
    out = []
    for i in range(0, len(pts), 80):
        chunk = pts[i:i + 80]
        coords = f"{JAM[1]},{JAM[0]};" + ";".join(f"{p[1]:.5f},{p[0]:.5f}" for _, p in chunk)
        js, _ = get_json(f"https://router.project-osrm.org/table/v1/driving/{coords}", "osrm_grid",
                         params={"sources": "0", "annotations": "duration,distance"}, timeout=120)
        for (zc, p), d, m in zip(chunk, js["durations"][0][1:], js["distances"][0][1:]):
            if d is not None and d <= 7200:
                out.append({"zcta": zc, "lat": p[0], "lon": p[1], "state": PREFIX_STATE[zc[:2]],
                            "drive_min": round(d / 60, 1), "drive_miles": round(m / 1609.34, 1)})
        print(i, len(out), flush=True)
    out.sort(key=lambda r: r["drive_min"])
    (DATA / "reference").mkdir(exist_ok=True)
    with open(DATA / "reference" / "search_grid.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print(len(out), "ZCTAs within 2 h")


if __name__ == "__main__":
    main()
