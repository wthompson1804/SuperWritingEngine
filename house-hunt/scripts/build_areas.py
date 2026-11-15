"""Build data/areas.csv from seeds/areas_seed.csv.

Centroid method (recorded per row in centroid_method):
  * gtfs_station  - the area's anchor rail/subway station, coordinates from the
                    operator's GTFS stops.txt. Used where the station is the
                    downtown or main rental cluster.
  * nominatim     - OpenStreetMap Nominatim geocode of geocode_query (areas with
                    no station, or where the station is off-centre).
Admin geography comes from the US Census Geocoder (geographies/coordinates).
ZIPs = ZCTAs found at the centroid and at 8 points on an 800 m ring around it.
NYPD precinct = point-in-polygon against NYC Open Data "Police Precincts".
Nearest rail station = nearest stop across LIRR, MNR, NJT rail, PATH, SEPTA rail
(subway listed separately).
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import sys
import zipfile
from pathlib import Path

from shapely.geometry import Point, shape

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, RAW, SEEDS, get_json, now_iso  # noqa: E402

GTFS = {
    "LIRR": RAW / "gtfs/gtfslirr.zip",
    "MNR": RAW / "gtfs/gtfsmnr.zip",
    "NYCT": RAW / "gtfs/gtfs_subway.zip",
    "NJT": RAW / "gtfs/njt_rail.zip",
    "PATH": RAW / "gtfs/path.zip",
    "SEPTA": RAW / "gtfs/septa_rail.zip",
}
RAIL_SYSTEMS = ["LIRR", "MNR", "NJT", "PATH", "SEPTA"]


def norm(s: str) -> str:
    s = s.lower().replace("street", "st").replace("avenue", "av").replace("–", "-")
    s = re.sub(r"\b(station|terminal|rail|ave)\b", lambda m: {"ave": "av"}.get(m.group(1), ""), s)
    return re.sub(r"[^a-z0-9]", "", s)


def load_stops() -> dict[str, list[dict]]:
    out = {}
    for sysname, p in GTFS.items():
        z = zipfile.ZipFile(p)
        name = [n for n in z.namelist() if n == "stops.txt" or n.endswith("/stops.txt")][0]
        rows = list(csv.DictReader(io.TextIOWrapper(z.open(name), "utf-8-sig")))
        keep = []
        for r in rows:
            # subway: parent stations only (location_type 1); others: stops with no parent
            if sysname == "NYCT" and r.get("location_type") != "1":
                continue
            if sysname != "NYCT" and r.get("parent_station") and r.get("location_type") != "1":
                continue
            if sysname == "PATH" and r.get("location_type") not in ("1", "0", ""):
                continue
            if re.search(r"\b(facility|yard|shops)\b", r["stop_name"], re.I):
                continue  # non-revenue stops (e.g. LIRR Hillside Facility, MNR Highbridge Yard)
            try:
                lat, lon = float(r["stop_lat"]), float(r["stop_lon"])
            except (ValueError, KeyError):
                continue
            keep.append({"system": sysname, "stop_id": r["stop_id"], "name": r["stop_name"],
                         "lat": lat, "lon": lon})
        out[sysname] = keep
    return out


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def match_station(stops, system, name):
    cands = stops[system]
    if name.startswith("stop_id:"):
        sid = name.split(":", 1)[1]
        hit = [s for s in cands if s["stop_id"] == sid]
        return hit[0] if hit else None
    n = norm(name)
    exact = [s for s in cands if norm(s["name"]) == n]
    if exact:
        return exact[0]
    starts = [s for s in cands if norm(s["name"]).startswith(n) or n.startswith(norm(s["name"]))]
    if len(starts) == 1:
        return starts[0]
    contains = [s for s in cands if n in norm(s["name"])]
    if len(contains) == 1:
        return contains[0]
    return None


def nominatim(q):
    js, meta = get_json("https://nominatim.openstreetmap.org/search", "nominatim",
                        params={"q": q, "format": "json", "limit": 1, "countrycodes": "us"})
    if not js:
        return None, meta
    return (float(js[0]["lat"]), float(js[0]["lon"]), js[0].get("display_name")), meta


def census_geo(lat, lon):
    js, meta = get_json("https://geocoding.geo.census.gov/geocoder/geographies/coordinates", "census_geocoder",
                        params={"x": f"{lon:.6f}", "y": f"{lat:.6f}", "benchmark": "Public_AR_Current",
                                "vintage": "Current_Current", "format": "json", "layers": "all"})
    return js["result"]["geographies"], meta


def first(g, key, field="NAME"):
    v = g.get(key) or []
    return v[0].get(field) if v else ""


def ring(lat, lon, r_m=800, n=8):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        dlat = (r_m * math.cos(a)) / 111320
        dlon = (r_m * math.sin(a)) / (111320 * math.cos(math.radians(lat)))
        pts.append((lat + dlat, lon + dlon))
    return pts


def load_precincts():
    js, meta = get_json("https://data.cityofnewyork.us/resource/y76i-bdw7.geojson", "nyc_open_data",
                        params={"$limit": 200})
    return [(f["properties"].get("precinct"), shape(f["geometry"])) for f in js["features"]], meta


def main():
    stops = load_stops()
    precincts, pmeta = load_precincts()
    seeds = list(csv.DictReader(open(SEEDS / "areas_seed.csv")))
    out, problems = [], []
    for s in seeds:
        row = {k: s[k] for k in ("id", "region", "name", "state")}
        lat = lon = None
        method = src = ""
        st = None
        if s["anchor_station"]:
            st = match_station(stops, s["anchor_system"], s["anchor_station"])
            if not st:
                problems.append(f"{s['id']}: station '{s['anchor_station']}' not matched in {s['anchor_system']}")
        if s["geocode_query"]:
            res, meta = nominatim(s["geocode_query"])
            if res:
                lat, lon, disp = res
                method, src = "nominatim", meta["url"]
            else:
                problems.append(f"{s['id']}: nominatim no result for '{s['geocode_query']}'")
        if lat is None and st:
            lat, lon = st["lat"], st["lon"]
            method, src = "gtfs_station", f"GTFS {st['system']} stops.txt stop_id={st['stop_id']}"
        if lat is None:
            problems.append(f"{s['id']}: NO CENTROID")
            continue
        row.update({"centroid_lat": round(lat, 6), "centroid_lon": round(lon, 6),
                    "centroid_method": method, "centroid_source": src})

        g, gmeta = census_geo(lat, lon)
        row["county"] = first(g, "Counties")
        row["county_fips"] = first(g, "Counties", "GEOID")
        row["county_subdivision"] = first(g, "County Subdivisions")
        place = first(g, "Incorporated Places")
        cdp = first(g, "Census Designated Places")
        # In NJ and CT the county subdivisions are the real municipalities (townships, towns);
        # a CDP there is only a statistical sub-area, so prefer the municipality name.
        if place:
            row["municipality"], row["place_type"] = place, "incorporated_place"
        elif cdp and row["state"] not in ("NJ", "CT"):
            row["municipality"], row["place_type"] = cdp, "census_designated_place"
        else:
            row["municipality"], row["place_type"] = row["county_subdivision"], "county_subdivision"
        row["cdp"] = cdp
        row["place_geoid"] = first(g, "Incorporated Places", "GEOID") or first(g, "Census Designated Places", "GEOID")
        row["cousub_geoid"] = first(g, "County Subdivisions", "GEOID")
        row["tract_geoid"] = first(g, "Census Tracts", "GEOID")
        zc = [first(g, "2020 Census ZIP Code Tabulation Areas", "GEOID")]
        for plat, plon in ring(lat, lon):
            try:
                gg, _ = census_geo(plat, plon)
                z = first(gg, "2020 Census ZIP Code Tabulation Areas", "GEOID")
                if z and z not in zc:
                    zc.append(z)
            except Exception as e:  # keep going; note it
                problems.append(f"{s['id']}: ring geocode failed {e}")
        row["zcta_centroid"] = zc[0]
        row["zctas_within_800m"] = " ".join(z for z in zc if z)
        row["admin_source"] = "US Census Geocoder geographies/coordinates, Public_AR_Current / Current_Current"

        # stations
        row["anchor_station"] = st["name"] if st else ""
        row["anchor_system"] = s["anchor_system"]
        row["anchor_line"] = s["anchor_line"]
        row["anchor_stop_id"] = st["stop_id"] if st else ""
        row["anchor_station_dist_m"] = round(haversine_m(lat, lon, st["lat"], st["lon"])) if st else ""
        rail = [x for sy in RAIL_SYSTEMS for x in stops[sy]]
        nr = min(rail, key=lambda x: haversine_m(lat, lon, x["lat"], x["lon"]))
        row["nearest_rail_station"] = nr["name"]
        row["nearest_rail_system"] = nr["system"]
        row["nearest_rail_dist_m"] = round(haversine_m(lat, lon, nr["lat"], nr["lon"]))
        ns = min(stops["NYCT"], key=lambda x: haversine_m(lat, lon, x["lat"], x["lon"]))
        dsub = round(haversine_m(lat, lon, ns["lat"], ns["lon"]))
        row["nearest_subway_station"] = ns["name"] if dsub < 5000 else ""
        row["nearest_subway_dist_m"] = dsub if dsub < 5000 else ""

        # police
        pct = ""
        if row["county_fips"] in ("36005", "36047", "36061", "36081", "36085"):
            p = Point(lon, lat)
            hit = [pc for pc, geom in precincts if geom.contains(p)]
            pct = f"NYPD Precinct {hit[0]}" if hit else ""
        row["police_jurisdiction"] = pct or s["police_jurisdiction_seed"]
        row["police_jurisdiction_basis"] = ("NYC Open Data Police Precincts (y76i-bdw7) point-in-polygon"
                                            if pct else "analyst assignment from municipality; UNVERIFIED")
        row["notes"] = s["notes"]
        row["retrieved_at"] = now_iso()
        out.append(row)
        print(f"{row['id']:35s} {row['municipality'][:28]:28s} {row['county'][:20]:20s} {row['zctas_within_800m']:30s} {row['police_jurisdiction']}", flush=True)

    DATA.mkdir(exist_ok=True)
    with open(DATA / "areas.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    (DATA / "areas_build_problems.txt").write_text("\n".join(problems) + "\n")
    print(f"\n{len(out)} areas written; {len(problems)} problems")
    print("\n".join(problems))


if __name__ == "__main__":
    main()
