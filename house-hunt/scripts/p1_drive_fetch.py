"""Phase 1, travel_drive: fetch OSRM free-flow routes area<->Jamaica LIRR (both directions).

Uses the public OSRM demo server (router.project-osrm.org), throttled to 1 req/s by lib.py,
every response cached in raw/osrm/. Each request asks for up to 3 alternatives, full GeoJSON
geometry and turn-by-turn steps. Idempotent: cached responses are reused.

Run: python3 scripts/p1_drive_fetch.py
"""
from __future__ import annotations

import csv
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from lib import DATA, get_json  # noqa: E402

JAMAICA = (40.699608, -73.808530)
OSRM = "https://router.project-osrm.org/route/v1/driving/{a};{b}"
PARAMS = {"overview": "full", "geometries": "geojson", "steps": "true", "alternatives": "3"}


def url_for(lat1, lon1, lat2, lon2):
    return OSRM.format(a=f"{lon1:.6f},{lat1:.6f}", b=f"{lon2:.6f},{lat2:.6f}")


def route(lat1, lon1, lat2, lon2):
    return get_json(url_for(lat1, lon1, lat2, lon2), "osrm", params=PARAMS, timeout=90)


def main():
    areas = list(csv.DictReader(open(DATA / "areas.csv")))
    for i, a in enumerate(areas):
        lat, lon = float(a["centroid_lat"]), float(a["centroid_lon"])
        for d, args in (("to", (lat, lon, *JAMAICA)), ("from", (*JAMAICA, lat, lon))):
            if a["id"] == "r1-jamaica":
                continue
            js, meta = route(*args)
            r0 = js["routes"][0] if js.get("routes") else None
            print(i, a["id"], d, js.get("code"), r0 and round(r0["distance"] / 1609.344, 1),
                  r0 and round(r0["duration"] / 60, 1), flush=True)


if __name__ == "__main__":
    main()
