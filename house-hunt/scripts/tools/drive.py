"""drive: free-flow driving time, distance, main roads and tolls between any point and Jamaica LIRR station.

    from scripts.tools.drive import drive, tolls_for_route
    drive(40.7196, -73.8448)          # both directions, tolls itemised, toll-free alternative if OSRM returned one
    tolls_for_route(osrm_route_json)  # tolled facilities on one OSRM route (needs overview=full, geometries=geojson, steps=true)

Routing: the public OSRM demo server (router.project-osrm.org), at most 1 request/second (lib.py throttle), every
response cached. The demo server has no traffic data, so minutes are free-flow and labelled `estimate`.
Saturday/Sunday traffic times are `not_found` until a traffic-aware routing key exists.

Tolls: rates come only from data/reference/tolls.csv and data/reference/njta_tolls.csv, which
`python3 scripts/tools/drive.py --build-reference` writes from official agency pages and PDFs cached under raw/.
Facilities are detected from the route geometry (distance to tabulated facility points, direction of travel from
the route heading, point-in-polygon for the Manhattan congestion relief zone). Road names are used only to find the
stretch of route on the NJ Turnpike and Garden State Parkway; entry and exit interchanges are then matched by
coordinates.

Every value is a dict: value, value_type (found / estimate / not_found), source_url, retrieved_at, method
(and reason when not_found). See docs/tools_notes/drive.md.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import html as _html
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import lib  # noqa: E402

JAMAICA = (40.699608, -73.808530)
OSRM_HOST = "https://router.project-osrm.org"
OSRM_ROUTE = OSRM_HOST + "/route/v1/driving/{a};{b}"
OSRM_PARAMS = {"overview": "full", "geometries": "geojson", "steps": "true", "alternatives": "3"}
OSRM_METHOD = "OSRM free-flow, no traffic"
OSRM_LEGACY = "osrm"            # raw/osrm: the earlier 98-area fetch (committed)
OSRM_BIG = "big/drive/osrm"     # raw/big/drive/osrm: per-building lookups (git-ignored, re-fetched if missing)
# Tested 2026-11-15: GET /route/v1/driving/...?exclude=toll -> HTTP 400
# {"message":"Exclude flag combination is not supported.","code":"InvalidValue"}
EXCLUDE_TOLL_SUPPORTED = False
EXCLUDE_TOLL_NOTE = ("the OSRM demo server rejects exclude=toll (HTTP 400 'Exclude flag combination is not "
                     "supported', tested 2026-11-15)")

REF = ROOT / "data" / "reference"
TOLLS_CSV = REF / "tolls.csv"
NJTA_CSV = REF / "njta_tolls.csv"
NJTA_IC_CSV = REF / "njta_interchanges.csv"
CRZ_JSON = REF / "crz_geofence.json"

TOLL_COLS = ["facility", "agency", "direction_charged", "ezpass_rate", "ezpass_basis", "mail_rate",
             "effective_date", "lat", "lon", "source_url", "retrieved_at",
             "facility_id", "scenario", "value_type", "notes"]
NJTA_COLS = TOLL_COLS + ["road", "direction", "entrance", "exit"]

# Which E-ZPass row the round-trip sums use.
#   weekend_offpeak: Saturday or Sunday outside the Port Authority's weekend peak (11 a.m. to 9 p.m.).
#   weekend_peak:    Saturday or Sunday 11 a.m. to 9 p.m.
SCENARIOS = ("weekend_offpeak", "weekend_peak")

# ----------------------------------------------------------------------------------------------------------------
# Facility geometry. Points are on the roadway (checked with OSRM /nearest on 2026-11-15: the nearest road carries
# the facility's name, see docs/tools_notes/drive.md). A route "uses" a facility when it passes within radius_m of
# any point. charged_heading is the compass heading of the tolled direction at the facility (None = both ways).
# ----------------------------------------------------------------------------------------------------------------
F = dict  # readability
FACILITIES = [
    # MTA Bridges and Tunnels: tolled in both directions.
    F(id="mta_verrazzano", name="Verrazzano-Narrows Bridge", agency="MTA Bridges and Tunnels",
      pts=[(40.60664, -74.04472)], heading=None, direction="both directions"),
    F(id="mta_throgs_neck", name="Throgs Neck Bridge", agency="MTA Bridges and Tunnels",
      pts=[(40.80100, -73.79355), (40.79987, -73.79354)], heading=None, direction="both directions"),
    F(id="mta_whitestone", name="Bronx-Whitestone Bridge", agency="MTA Bridges and Tunnels",
      pts=[(40.80130, -73.82920), (40.80044, -73.82882)], heading=None, direction="both directions"),
    F(id="mta_rfk", name="Robert F. Kennedy (Triborough) Bridge", agency="MTA Bridges and Tunnels",
      pts=[(40.78024, -73.92703), (40.80041, -73.92812), (40.79898, -73.91885)], heading=None,
      direction="both directions (one toll per trip, whichever spans are used)"),
    F(id="mta_queens_midtown", name="Queens-Midtown Tunnel", agency="MTA Bridges and Tunnels",
      pts=[(40.74506, -73.96437), (40.74522, -73.96418), (40.7447, -73.9648)], heading=None,
      direction="both directions"),
    F(id="mta_hugh_carey", name="Hugh L. Carey (Brooklyn-Battery) Tunnel", agency="MTA Bridges and Tunnels",
      pts=[(40.69584, -74.01351), (40.69588, -74.01335)], heading=None, direction="both directions"),
    F(id="mta_henry_hudson", name="Henry Hudson Bridge", agency="MTA Bridges and Tunnels",
      pts=[(40.87773, -73.92223)], heading=None, direction="both directions"),
    F(id="mta_cross_bay", name="Cross Bay Veterans Memorial Bridge", agency="MTA Bridges and Tunnels",
      pts=[(40.59750, -73.82084)], heading=None, direction="both directions"),
    F(id="mta_marine_parkway", name="Marine Parkway-Gil Hodges Memorial Bridge", agency="MTA Bridges and Tunnels",
      pts=[(40.57350, -73.88499)], heading=None, direction="both directions"),
    # Port Authority: "Tolls are collected entering New York. No tolls are collected entering New Jersey."
    F(id="pa_gwb", name="George Washington Bridge", agency="Port Authority of NY & NJ",
      pts=[(40.85174, -73.95269), (40.85160, -73.95274)], heading=90, direction="entering New York (eastbound)"),
    F(id="pa_lincoln", name="Lincoln Tunnel", agency="Port Authority of NY & NJ",
      pts=[(40.76285, -74.01089), (40.76247, -74.00997), (40.76348, -74.01043), (40.76311, -74.00955)],
      heading=90, direction="entering New York (eastbound)"),
    F(id="pa_holland", name="Holland Tunnel", agency="Port Authority of NY & NJ",
      pts=[(40.72744, -74.02109), (40.72764, -74.02131)], heading=90, direction="entering New York (eastbound)"),
    F(id="pa_goethals", name="Goethals Bridge", agency="Port Authority of NY & NJ",
      pts=[(40.63535, -74.19745), (40.63558, -74.19724)], heading=90, direction="entering New York (eastbound)"),
    F(id="pa_bayonne", name="Bayonne Bridge", agency="Port Authority of NY & NJ",
      pts=[(40.64184, -74.14217), (40.64225, -74.14213)], heading=180,
      direction="entering New York (southbound into Staten Island)"),
    F(id="pa_outerbridge", name="Outerbridge Crossing", agency="Port Authority of NY & NJ",
      pts=[(40.52484, -74.24679), (40.52478, -74.24648)], heading=90, direction="entering New York (eastbound)"),
    # NYS Thruway fixed-rate points. Coordinates and tolled direction: data.ny.gov "Thruway Interchanges and Exits".
    F(id="thruway_cuomo", name="Gov. Mario M. Cuomo Bridge", agency="NYS Thruway Authority",
      pts=[(41.07091, -73.89109), (41.07092, -73.89163), (41.07090, -73.89048)], radius=120, heading=90,
      direction="Thruway southbound only (eastbound over the Hudson, Rockland to Westchester)"),
    F(id="thruway_yonkers", name="Yonkers Toll Barrier (I-87)", agency="NYS Thruway Authority",
      pts=[(40.97557, -73.85861)], heading=None, direction="both directions"),
    F(id="thruway_new_rochelle", name="New Rochelle Toll Barrier (I-95)", agency="NYS Thruway Authority",
      pts=[(40.92684, -73.76993)], heading=45, direction="northbound only"),
    F(id="thruway_harriman", name="Harriman Toll Barrier (Exit 16)", agency="NYS Thruway Authority",
      pts=[(41.31387, -74.12813)], heading=None, direction="both directions"),
    # NYS Bridge Authority.
    F(id="nysba_newburgh_beacon", name="Newburgh-Beacon Bridge", agency="NYS Bridge Authority",
      pts=[(41.51920, -73.98907), (41.51873, -73.98916)], heading=90, direction="eastbound only"),
    F(id="nysba_mid_hudson", name="Mid-Hudson Bridge", agency="NYS Bridge Authority",
      pts=[(41.70290, -73.94622)], heading=90, direction="eastbound only"),
    F(id="nysba_bear_mountain", name="Bear Mountain Bridge", agency="NYS Bridge Authority",
      pts=[(41.31997, -73.98370)], heading=90, direction="eastbound only"),
    F(id="nysba_kingston_rhinecliff", name="Kingston-Rhinecliff Bridge", agency="NYS Bridge Authority",
      pts=[(41.97883, -73.94953)], heading=90, direction="eastbound only"),
    F(id="nysba_rip_van_winkle", name="Rip Van Winkle Bridge", agency="NYS Bridge Authority",
      pts=[(42.22357, -73.85083)], heading=90, direction="eastbound only"),
    # Outside the agencies asked for, but on the fastest Long Beach route. OSM names the roadway "Nassau
    # Expressway", so this point was taken from the OSRM route geometry over Reynolds Channel.
    F(id="ncba_atlantic_beach", name="Atlantic Beach Bridge", agency="Nassau County Bridge Authority",
      pts=[(40.59410, -73.73710), (40.59730, -73.73678)], heading=None, direction="both directions"),
]
DEFAULT_RADIUS_M = 60.0
FAC_BY_ID = {f["id"]: f for f in FACILITIES}

# Thruway ticket system (north of the Woodbury barrier). Interchange coordinates: data.ny.gov 7jkf-259w.
# "15" stands for the Woodbury barrier, which the Thruway fare table lists as interchange 15.
THRUWAY_TICKET_PTS = {"15": (41.30912, -74.12521), "17": (41.50947, -74.07446), "18": (41.73551, -74.06570),
                      "19": (41.94764, -74.02749), "20": (42.08306, -73.97328), "21": (42.25013, -73.88444)}
THRUWAY_TICKET_ORDER = ["15", "17", "18", "19", "20", "21"]
THRUWAY_TICKET_RADIUS = {"15": 80.0}
THRUWAY_TICKET_RADIUS_DEFAULT = 700.0

CRZ_ID = "mta_crz"

# ----------------------------------------------------------------------------------------------------------------
# Small geometry helpers (equirectangular metres around the region; error well under 1% within 150 km).
# ----------------------------------------------------------------------------------------------------------------
_LAT0, _LON0 = 40.8, -73.9
_KX = 111320.0 * math.cos(math.radians(_LAT0))
_KY = 110540.0


def _xy(lonlat) -> np.ndarray:
    a = np.asarray(lonlat, dtype=float).reshape(-1, 2)
    return np.column_stack(((a[:, 0] - _LON0) * _KX, (a[:, 1] - _LAT0) * _KY))


def _pt(lat: float, lon: float) -> np.ndarray:
    return np.array([(lon - _LON0) * _KX, (lat - _LAT0) * _KY])


def _seg_dist(xy: np.ndarray, p: np.ndarray):
    """Distance from point p to every segment of polyline xy. Returns (distances, parameter t)."""
    a, b = xy[:-1], xy[1:]
    d = b - a
    L2 = (d * d).sum(1)
    L2s = np.where(L2 == 0, 1.0, L2)
    t = np.clip(((p - a) * d).sum(1) / L2s, 0.0, 1.0)
    c = a + d * t[:, None]
    return np.hypot(c[:, 0] - p[0], c[:, 1] - p[1]), t


def _heading(xy: np.ndarray, i: int) -> float:
    """Compass heading of travel around segment i (averaged over a few segments to ignore tiny kinks)."""
    lo, hi = max(0, i - 2), min(len(xy) - 1, i + 3)
    dx, dy = xy[hi] - xy[lo]
    return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0


def _ang_diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _pip(x: float, y: float, ring) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _densify(coords: np.ndarray, step_m: float = 40.0) -> np.ndarray:
    """Insert points so no gap exceeds step_m (coords are lon/lat)."""
    xy = _xy(coords)
    seg = np.hypot(*(xy[1:] - xy[:-1]).T)
    out = [coords[0]]
    for i, L in enumerate(seg):
        k = int(L // step_m)
        if k:
            f = (np.arange(1, k + 1) / (k + 1))[:, None]
            out.extend(coords[i] + (coords[i + 1] - coords[i]) * f)
        out.append(coords[i + 1])
    return np.asarray(out)


# ----------------------------------------------------------------------------------------------------------------
# Reference tables (read at first use).
# ----------------------------------------------------------------------------------------------------------------
_cache: dict = {}


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _rates() -> dict:
    """{facility_id: {scenario: row}} from tolls.csv. Rows with scenario 'all' serve every scenario."""
    if "rates" not in _cache:
        if not TOLLS_CSV.exists():
            build_reference()
        out: dict = {}
        for r in csv.DictReader(open(TOLLS_CSV, newline="")):
            for sc in (SCENARIOS if r["scenario"] == "all" else [s.strip() for s in r["scenario"].split("|")]):
                out.setdefault(r["facility_id"], {})[sc] = r
        _cache["rates"] = out
    return _cache["rates"]


def _crz_ring():
    if "crz" not in _cache:
        if not CRZ_JSON.exists():
            build_reference()
        j = json.loads(CRZ_JSON.read_text())
        ring = j["zone_polygon"]
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        _cache["crz"] = (ring, (min(xs), max(xs), min(ys), max(ys)), j)
    return _cache["crz"]


def _njta_ics() -> dict:
    """{'turnpike': [ic...], 'parkway': [ic...]} with id, lat, lon, kind (entrance/exit), directions, milemarker."""
    if "ics" not in _cache:
        if not NJTA_IC_CSV.exists():
            build_reference()
        out = {"turnpike": [], "parkway": []}
        for r in csv.DictReader(open(NJTA_IC_CSV, newline="")):
            r["lat"], r["lon"] = float(r["lat"]), float(r["lon"])
            r["xy"] = _pt(r["lat"], r["lon"])
            out[r["road"]].append(r)
        _cache["ics"] = out
    return _cache["ics"]


def _njta_rows() -> dict:
    if "njta" not in _cache:
        out = {}
        if NJTA_CSV.exists():
            for r in csv.DictReader(open(NJTA_CSV, newline="")):
                out[(r["road"], r["direction"], r["entrance"], r["exit"], r["scenario"])] = r
        _cache["njta"] = out
    return _cache["njta"]


# ----------------------------------------------------------------------------------------------------------------
# NJ Turnpike Authority toll calculator (official, robots-allowed JSON partial; one cached GET per pair).
# ----------------------------------------------------------------------------------------------------------------
NJTA_PAGE = "https://www.njta.gov/travel-resources/toll-calculator/"
NJTA_API = "https://www.njta.gov/wp-json/njta/v1/partials"


def _njta_params(tab: str, entrance: str, exit_: str, direction: str | None = None) -> dict:
    p = {"slug": "map/trip-details", "tab": tab, "vehicle-type": "1", "green-discount": "false",
         "senior-discount": "false"}
    if direction:
        p["direction"] = direction
    p["entrance"] = entrance
    p["exit"] = exit_
    return p


def _text(b: bytes | str) -> str:
    s = b.decode("utf8", "replace") if isinstance(b, bytes) else b
    s = re.sub(r"<(script|style)[\s\S]*?</\1>|<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", _html.unescape(s)).strip()


def _njta_parse(road: str, direction: str, ent: str, ex: str, content: bytes, meta: dict) -> list[dict]:
    t = _text(content)
    base = {"agency": "New Jersey Turnpike Authority", "effective_date": "not stated by the calculator",
            "source_url": meta["url"], "retrieved_at": meta["retrieved_at"], "road": road, "direction": direction,
            "entrance": ent, "exit": ex, "lat": "", "lon": ""}
    label = ("NJ Turnpike" if road == "turnpike" else "Garden State Parkway")
    base["facility"] = f"{label} {ent} to {ex}" + (f" ({direction})" if direction else "")
    base["facility_id"] = f"njta_{road}_{direction or 'x'}_{ent}_{ex}"
    base["direction_charged"] = "this entrance-to-exit trip" + (f", {direction}" if direction else "")
    cash = re.search(r"Cash \$([\d.]+)", t)
    mail = cash.group(1) if cash else "not_found"
    note = "mail_rate is the calculator's Cash rate"
    lead = re.match(r"^(.*?)(?:Peak/Weekends|\$)", t)
    if lead and lead.group(1).strip():
        note += "; calculator note: " + lead.group(1).strip()
    if "Cash Not Accepted" in t:
        note += "; cash not accepted"
    rows = []
    m = re.search(r"Peak/Weekends \$([\d.]+) Off Peak \$([\d.]+)", t)
    if m:
        rows.append({**base, "ezpass_rate": m.group(1), "ezpass_basis": "NJ E-ZPass Peak/Weekends, passenger car",
                     "mail_rate": mail, "scenario": "weekend_offpeak|weekend_peak", "value_type": "found",
                     "notes": note + "; the Turnpike charges its peak rate all weekend"})
        rows.append({**base, "ezpass_rate": m.group(2),
                     "ezpass_basis": "NJ E-ZPass Off Peak (weekdays only), passenger car", "mail_rate": mail,
                     "scenario": "weekday_offpeak", "value_type": "found", "notes": note})
        return rows
    m = re.match(r"^(?:.*?)\$([\d.]+) ", t)
    if m and "Cash" in t:
        return [{**base, "ezpass_rate": m.group(1), "ezpass_basis": "E-ZPass, passenger car (no peak pricing shown)",
                 "mail_rate": mail, "scenario": "all", "value_type": "found", "notes": note}]
    return [{**base, "ezpass_rate": "not_found", "ezpass_basis": "", "mail_rate": "not_found", "scenario": "all",
             "value_type": "not_found", "notes": "calculator returned no rate: " + t[:160]}]


def _njta_write(rows_by_key: dict) -> None:
    REF.mkdir(parents=True, exist_ok=True)
    with open(NJTA_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=NJTA_COLS)
        w.writeheader()
        for k in sorted(rows_by_key):
            w.writerow({c: rows_by_key[k].get(c, "") for c in NJTA_COLS})


def njta_toll(road: str, entrance: str, exit_: str, direction: str = "", fetch: bool = True) -> list[dict]:
    """Rows (one per scenario) for one NJ Turnpike or Parkway trip. Looks in njta_tolls.csv, then asks the
    official calculator once (cached in raw/njta/) and appends the answer to njta_tolls.csv."""
    rows = _njta_rows()
    hit = [r for k, r in rows.items() if k[:4] == (road, direction, entrance, exit_)]
    if hit or not fetch:
        return hit
    content, meta = lib.cached_get(NJTA_API, "njta", params=_njta_params(road, entrance, exit_, direction or None),
                                   ext="html", timeout=60)
    if meta["status"] != 200:
        return []
    new = _njta_parse(road, direction, entrance, exit_, content, meta)
    for r in new:
        rows[(road, direction, entrance, exit_, r["scenario"])] = r
    _njta_write(rows)
    return new


# ----------------------------------------------------------------------------------------------------------------
# Toll detection
# ----------------------------------------------------------------------------------------------------------------
def _route_of(osrm_json: dict) -> dict:
    if "routes" in osrm_json:
        if not osrm_json["routes"]:
            raise ValueError("OSRM response has no routes")
        return osrm_json["routes"][0]
    return osrm_json


def _item(fid: str, *, charged: bool, heading=None, detection: str = "", extra_note: str = "") -> dict:
    """One itemised toll entry with its rate rows from tolls.csv."""
    f = FAC_BY_ID.get(fid, {})
    rates = _rates().get(fid, {})
    it = {"facility_id": fid, "facility": f.get("name", fid), "agency": f.get("agency", ""),
          "direction_charged": f.get("direction", ""), "charged": charged,
          "travel_heading_deg": None if heading is None else round(heading), "detection": detection}
    _fill_rates(it, rates, charged, extra_note)
    return it


def _fill_rates(it: dict, rates: dict, charged: bool, extra_note: str = "") -> None:
    any_row = next(iter(rates.values()), None)
    for sc in SCENARIOS:
        r = rates.get(sc)
        key = "ezpass_rate" if sc == "weekend_offpeak" else "ezpass_rate_weekend_peak"
        if not charged:
            it[key] = 0.0
        else:
            it[key] = _num(r["ezpass_rate"]) if r else None
        if sc == "weekend_offpeak":
            it["ezpass_basis"] = r["ezpass_basis"] if r else ""
        else:
            it["ezpass_basis_weekend_peak"] = r["ezpass_basis"] if r else ""
    r = rates.get("weekend_offpeak") or any_row
    it["mail_rate"] = 0.0 if not charged else (_num(r["mail_rate"]) if r else None)
    it["effective_date"] = r["effective_date"] if r else ""
    it["source_url"] = r["source_url"] if r else ""
    it["retrieved_at"] = r["retrieved_at"] if r else ""
    if not charged:
        it["value_type"] = "found"
        it["notes"] = "crossed in the direction that is not tolled"
    elif it["ezpass_rate"] is None:
        it["value_type"] = "not_found"
        it["notes"] = (r["notes"] if r else "no row in tolls.csv for this facility")
    else:
        it["value_type"] = "found"
        it["notes"] = r["notes"] if r else ""
    if extra_note:
        it["notes"] = (it["notes"] + "; " if it["notes"] else "") + extra_note


_NJ_ROADS = {
    "turnpike": lambda name, ref: "NJTP" in ref or "New Jersey Turnpike" in name,
    "parkway": lambda name, ref: "GSP" in [x.strip() for x in ref.split(";")] or "Garden State Parkway" in name,
}


def _nj_trips(route: dict, road: str) -> list[np.ndarray]:
    """Contiguous stretches (lon/lat arrays) of the route on the given NJ toll road, found from step name/ref.
    Untagged gaps (ramps, service areas) shorter than 2.5 km do not split a stretch."""
    test = _NJ_ROADS[road]
    trips, cur, gap = [], [], 0.0
    for leg in route["legs"]:
        for s in leg["steps"]:
            c = s["geometry"]["coordinates"]
            if test(s.get("name") or "", s.get("ref") or ""):
                cur.extend(c)
                gap = 0.0
            elif cur:
                gap += s["distance"]
                if gap > 2500:
                    trips.append(np.asarray(cur))
                    cur, gap = [], 0.0
    if cur:
        trips.append(np.asarray(cur))
    return [t for t in trips if len(t) >= 2]


def _nj_endpoints(trip: np.ndarray, ics: list[dict], kind: str, direction: str | None):
    """Entry (kind='entrance') or exit interchange of a stretch, by coordinates.
    Rule 1: the interchange nearest the stretch's first/last point if within 2.5 km.
    Rule 2: otherwise the first/last interchange the stretch passes within 1.2 km."""
    cand = [i for i in ics if i["kind"] == kind and (not direction or direction in i["directions"].split("|"))]
    if not cand:
        return None, None
    xy = _xy(trip)
    end = xy[0] if kind == "entrance" else xy[-1]
    d = [float(np.hypot(*(i["xy"] - end))) for i in cand]
    k = int(np.argmin(d))
    if d[k] <= 2500:
        return cand[k], f"nearest {kind} interchange to the stretch's {'first' if kind == 'entrance' else 'last'} point ({round(d[k])} m)"
    passed = []
    for i in cand:
        dd, _ = _seg_dist(xy, i["xy"])
        j = int(np.argmin(dd))
        if dd[j] <= 1200:
            passed.append((j, i, float(dd[j])))
    if not passed:
        return None, None
    passed.sort(key=lambda x: x[0])
    j, i, dist = passed[0] if kind == "entrance" else passed[-1]
    return i, f"{'first' if kind == 'entrance' else 'last'} {kind} interchange the stretch passes ({round(dist)} m)"


def _nj_items(route: dict, fetch: bool = True) -> list[tuple[int, dict]]:
    out = []
    ics_all = _njta_ics()
    full = _xy(route["geometry"]["coordinates"])
    for road in ("turnpike", "parkway"):
        label = "NJ Turnpike" if road == "turnpike" else "Garden State Parkway"
        for trip in _nj_trips(route, road):
            direction = ""
            if road == "parkway":
                direction = "nb" if trip[-1][1] > trip[0][1] else "sb"
            ent, how_in = _nj_endpoints(trip, ics_all[road], "entrance", direction or None)
            ex, how_out = _nj_endpoints(trip, ics_all[road], "exit", direction or None)
            pos = int(np.argmin(np.hypot(*(full - _xy(trip[:1])[0]).T)))
            km = float(np.hypot(*(np.diff(_xy(trip), axis=0)).T).sum()) / 1000.0
            it = {"facility_id": f"njta_{road}", "facility": label, "agency": "New Jersey Turnpike Authority",
                  "direction_charged": "entrance-to-exit trip", "charged": True, "travel_heading_deg": None,
                  "km_on_road": round(km, 1)}
            if not ent and not ex:
                # No interchange anywhere near the stretch: it is outside the ticketed section (for example the
                # I-95 "Express Roadway" between US 46 and the George Washington Bridge, tagged NJTP in OSM).
                it.update(charged=False, ezpass_rate=0.0, ezpass_rate_weekend_peak=0.0, mail_rate=0.0,
                          value_type="estimate", ezpass_basis="", ezpass_basis_weekend_peak="", effective_date="",
                          source_url=NJTA_PAGE, retrieved_at="",
                          detection=f"{round(km, 1)} km of the route is tagged {label} (step name/ref) but passes "
                                    f"no toll-calculator interchange within 1.2 km",
                          notes="treated as outside the tolled section (no toll); method: no NJTA interchange "
                                "near the stretch")
                out.append((pos, it))
                continue
            if not ent or not ex:
                it.update(detection=f"{round(km, 1)} km of the route is on the {label} (step name/ref) but only "
                                    f"one end matched an interchange by coordinates",
                          ezpass_rate=None, ezpass_rate_weekend_peak=None, mail_rate=None, value_type="not_found",
                          notes="entry or exit interchange not identified", source_url=NJTA_PAGE, retrieved_at="",
                          ezpass_basis="", ezpass_basis_weekend_peak="", effective_date="")
                out.append((pos, it))
                continue
            it["entrance"], it["exit"] = ent["id"], ex["id"]
            it["facility"] = f"{label} {ent['id']} ({ent['name']}) to {ex['id']} ({ex['name']})" + (
                f", {direction}" if direction else "")
            it["detection"] = (f"{round(km, 1)} km of the route is on the {label} (step name/ref); entry = {how_in}; "
                               f"exit = {how_out}")
            if ent["id"] == ex["id"]:
                it.update(charged=False, ezpass_rate=0.0, ezpass_rate_weekend_peak=0.0, mail_rate=0.0,
                          value_type="estimate", ezpass_basis="", ezpass_basis_weekend_peak="", effective_date="",
                          source_url=NJTA_PAGE, retrieved_at="",
                          notes="entry and exit match the same interchange: the stretch is outside the tolled "
                                "section or too short to tell; treated as no toll")
                out.append((pos, it))
                continue
            try:
                rows = njta_toll(road, ent["id"], ex["id"], direction, fetch=fetch)
            except Exception as e:  # network trouble: report, never guess
                rows = []
                it["error"] = repr(e)[:200]
            rates = {}
            for r in rows:
                for sc in (SCENARIOS if r["scenario"] == "all" else r["scenario"].split("|")):
                    rates[sc] = r
            if not rates:
                it.update(ezpass_rate=None, ezpass_rate_weekend_peak=None, mail_rate=None, value_type="not_found",
                          notes="no rate for this pair in njta_tolls.csv and the NJTA calculator was not reachable",
                          source_url=NJTA_PAGE, retrieved_at="", ezpass_basis="", ezpass_basis_weekend_peak="",
                          effective_date="")
            else:
                _fill_rates(it, rates, True)
                if it["ezpass_rate"] == 0.0:
                    it["charged"] = False
            out.append((pos, it))
    return out


def _thruway_ticket_item(xy: np.ndarray):
    passed = {}
    for k, (la, lo) in THRUWAY_TICKET_PTS.items():
        d, _ = _seg_dist(xy, _pt(la, lo))
        i = int(np.argmin(d))
        if d[i] <= THRUWAY_TICKET_RADIUS.get(k, THRUWAY_TICKET_RADIUS_DEFAULT):
            passed[k] = (i, float(d[i]))
    if len(passed) < 2:
        return None
    ks = sorted(passed, key=THRUWAY_TICKET_ORDER.index)
    a, b = ks[0], ks[-1]
    fid = f"thruway_ticket_{a}_{b}"
    rates = _rates().get(fid, {})
    it = {"facility_id": fid, "agency": "NYS Thruway Authority",
          "facility": f"NYS Thruway ticket system, interchange {a}{' (Woodbury barrier)' if a == '15' else ''} "
                      f"to {b}",
          "direction_charged": "both directions", "charged": True, "travel_heading_deg": None,
          "detection": "route passes Thruway interchange points " + ", ".join(
              f"{k} ({round(passed[k][1])} m)" for k in ks)}
    _fill_rates(it, rates, True)
    return min(v[0] for v in passed.values()), it


def tolls_for_route(osrm_route_json: dict, fetch: bool = True) -> list[dict]:
    """Tolled facilities on one OSRM route, in travel order.

    `osrm_route_json` is one element of an OSRM response's `routes` (or a whole response: its first route), fetched
    with overview=full, geometries=geojson and steps=true. Detection is geometric: the route must pass within a few
    tens of metres of a tabulated point on the facility, the tolled direction is checked against the route's
    heading there, and the congestion relief zone is a point-in-polygon test against the MTA's published geofence.
    Each item carries the facility, whether this direction is charged, the weekend E-ZPass rates and the Tolls by
    Mail rate with their source. A facility whose rate is unknown has value_type not_found (never a guess).
    `fetch=False` stops the NJ Turnpike/Parkway lookup from calling the NJTA calculator for unseen pairs.
    """
    route = _route_of(osrm_route_json)
    coords = np.asarray(route["geometry"]["coordinates"], dtype=float)
    if len(coords) < 2:
        return []
    xy = _xy(coords)
    found: list[tuple[int, dict]] = []
    for f in FACILITIES:
        radius = f.get("radius", DEFAULT_RADIUS_M)
        best = None
        for la, lo in f["pts"]:
            if abs(la - coords[:, 1]).min() > 0.02 and abs(lo - coords[:, 0]).min() > 0.02:
                continue
            d, _ = _seg_dist(xy, _pt(la, lo))
            i = int(np.argmin(d))
            if d[i] <= radius and (best is None or d[i] < best[1]):
                best = (i, float(d[i]), la, lo)
        if best is None:
            continue
        i, dist, la, lo = best
        hd = _heading(xy, i)
        charged = f["heading"] is None or _ang_diff(hd, f["heading"]) < 90.0
        found.append((i, _item(f["id"], charged=charged, heading=hd,
                               detection=f"route passes {round(dist)} m from ({la:.5f}, {lo:.5f})")))
    tk = _thruway_ticket_item(xy)
    if tk:
        found.append(tk)
    found.extend(_nj_items(route, fetch=fetch))
    # Manhattan congestion relief zone: any (densified) route point inside the MTA geofence polygon.
    ring, (x0, x1, y0, y1), crzmeta = _crz_ring()
    m = (coords[:, 0] > x0 - 0.01) & (coords[:, 0] < x1 + 0.01) & (coords[:, 1] > y0 - 0.01) & (coords[:, 1] < y1 + 0.01)
    if m.any():
        idx = np.flatnonzero(m)
        sub = _densify(coords[max(0, idx[0] - 1): idx[-1] + 2], 30.0)
        inside = [(px, py) for px, py in sub if x0 <= px <= x1 and y0 <= py <= y1 and _pip(px, py, ring)]
        if inside:
            px, py = inside[0]
            it = {"facility_id": CRZ_ID, "facility": "Manhattan Congestion Relief Zone (south of and including 60th St)",
                  "agency": "MTA (Triborough Bridge and Tunnel Authority)",
                  "direction_charged": "on entering the zone, once per day", "charged": True,
                  "travel_heading_deg": None, "once_per_day": True,
                  "detection": f"{len(inside)} route points (30 m spacing) fall inside the MTA geofence polygon; "
                               f"first at ({py:.5f}, {px:.5f}). Geofence: {crzmeta['source_url']}"}
            _fill_rates(it, _rates().get(CRZ_ID, {}), True)
            pos = int(np.argmin(np.hypot(*(xy - _xy([(px, py)])[0]).T)))
            found.append((pos, it))
    found.sort(key=lambda x: x[0])
    return [it for _, it in found]


# ----------------------------------------------------------------------------------------------------------------
# OSRM
# ----------------------------------------------------------------------------------------------------------------
def osrm_url(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    return OSRM_ROUTE.format(a=f"{lon1:.6f},{lat1:.6f}", b=f"{lon2:.6f},{lat2:.6f}")


def _cache_key(url: str, params: dict) -> str:
    full = requests.Request("GET", url, params=params).prepare().url
    return hashlib.sha1(("GET " + full + " ").encode()).hexdigest()[:16]


def osrm_route(lat1: float, lon1: float, lat2: float, lon2: float):
    """(response json, meta). Reuses raw/osrm/ when the earlier area fetch has this exact request; new requests
    are cached in raw/big/drive/osrm/ (git-ignored; re-fetched on demand)."""
    url = osrm_url(lat1, lon1, lat2, lon2)
    key = _cache_key(url, OSRM_PARAMS)
    src = OSRM_LEGACY if (lib.RAW / OSRM_LEGACY / f"{key}.json").exists() else OSRM_BIG
    return lib.get_json(url, src, params=OSRM_PARAMS, timeout=90)


def _roads(route: dict, top: int = 6) -> list[dict]:
    """Named roads carrying the most distance, in travel order."""
    agg: dict = {}
    order = 0
    for leg in route["legs"]:
        for s in leg["steps"]:
            name, ref = (s.get("name") or "").strip(), (s.get("ref") or "").strip()
            if not name and not ref:
                continue
            label = f"{name} ({ref})" if name and ref else (name or ref)
            a = agg.setdefault(label, {"road": label, "miles": 0.0, "order": order})
            a["miles"] += s["distance"] / 1609.344
            order += 1
    keep = sorted(agg.values(), key=lambda a: -a["miles"])[:top]
    keep = [a for a in keep if a["miles"] >= 0.3] or keep[:1]
    return [{"road": a["road"], "miles": round(a["miles"], 1)} for a in sorted(keep, key=lambda a: a["order"])]


def _val(value, value_type, source_url, retrieved_at, method=None, **extra) -> dict:
    d = {"value": value, "value_type": value_type, "source_url": source_url, "retrieved_at": retrieved_at,
         "method": method}
    d.update(extra)
    return d


def _toll_sum(items: list[dict], key: str):
    charged = [i for i in items if i["charged"]]
    missing = [i["facility"] for i in charged if i.get(key) is None]
    known = round(sum(i[key] for i in charged if i.get(key) is not None), 2)
    return known, missing


def _direction(lat1, lon1, lat2, lon2, fetch: bool) -> dict:
    js, meta = osrm_route(lat1, lon1, lat2, lon2)
    if js.get("code") != "Ok" or not js.get("routes"):
        why = f"OSRM returned code {js.get('code')}"
        nf = _val(None, "not_found", meta["url"], meta["retrieved_at"], reason=why)
        return {"miles": nf, "minutes_free_flow": nf, "main_roads": nf, "tolled_facilities": [],
                "toll_ezpass": nf, "toll_free_alternative": nf, "alternatives_returned": 0}
    prov = (meta["url"], meta["retrieved_at"])
    routes = js["routes"]
    r0 = routes[0]
    items = tolls_for_route(r0, fetch=fetch)
    known, missing = _toll_sum(items, "ezpass_rate")
    out = {
        "miles": _val(round(r0["distance"] / 1609.344, 1), "estimate", *prov, OSRM_METHOD + "; fastest route"),
        "minutes_free_flow": _val(round(r0["duration"] / 60.0, 1), "estimate", *prov, OSRM_METHOD + "; fastest route"),
        "main_roads": _val(_roads(r0), "estimate", *prov,
                           "road names/refs of the OSRM steps carrying the most distance, in travel order"),
        "tolled_facilities": items,
        "toll_ezpass": _val(known if not missing else None, "estimate" if not missing else "not_found", *prov,
                            "sum of weekend off-peak E-ZPass rates (tolls.csv) for the charged facilities on this "
                            "route", known_subtotal=known, missing=missing,
                            **({"reason": "rate not_found for: " + "; ".join(missing)} if missing else {})),
        "alternatives_returned": len(routes),
    }
    # Toll-free alternative: only what OSRM itself returned (alternatives=3); exclude=toll is not available.
    free = []
    for k, r in enumerate(routes):
        its = items if k == 0 else tolls_for_route(r, fetch=False)
        if not any(i["charged"] for i in its):
            free.append((r["duration"], k, r))
    if free:
        dur, k, r = min(free)
        out["toll_free_alternative"] = _val(
            round(dur / 60.0, 1), "estimate", *prov,
            f"fastest of the {len(routes)} route(s) OSRM returned that uses no tabulated tolled facility "
            f"(route index {k}); {EXCLUDE_TOLL_NOTE}",
            miles=round(r["distance"] / 1609.344, 1), main_roads=_roads(r), is_fastest_route=(k == 0))
    else:
        out["toll_free_alternative"] = _val(
            None, "not_found", *prov,
            reason=f"{EXCLUDE_TOLL_NOTE}; all {len(routes)} route(s) it returned use a tolled facility. A "
                   f"toll-free route may still exist")
    return out


def drive(lat: float, lon: float, fetch: bool = True) -> dict:
    """Driving between (lat, lon) and Jamaica LIRR station, both directions, free-flow.

    Returns miles, free-flow minutes, main roads and itemised tolls for each direction, the round-trip E-ZPass
    toll for a weekend (off-peak and peak), the toll-free alternative's minutes when OSRM returned one, and
    not_found placeholders for Saturday/Sunday traffic times. Two OSRM requests on first call (about 1 s each,
    throttled), then cached. `fetch=False` uses caches only for the NJ Turnpike/Parkway calculator.
    """
    to = _direction(lat, lon, *JAMAICA, fetch)
    back = _direction(*JAMAICA, lat, lon, fetch)
    res = {
        "input": {"lat": lat, "lon": lon},
        "anchor": {"name": "Jamaica LIRR station", "lat": JAMAICA[0], "lon": JAMAICA[1]},
        "to_jamaica": to,
        "from_jamaica": back,
    }
    # Flat copies of the headline numbers.
    for k_out, k_in in (("miles", "miles"), ("minutes", "minutes_free_flow")):
        res[f"{k_out}_to_jamaica"] = to[k_in]
        res[f"{k_out}_from_jamaica"] = back[k_in]
    prov = (OSRM_HOST, max(to["miles"]["retrieved_at"], back["miles"]["retrieved_at"]))
    for key, rate_key, label in (("toll_round_trip_ezpass", "ezpass_rate",
                                  "weekend off-peak (Saturday/Sunday outside 11 a.m. to 9 p.m.)"),
                                 ("toll_round_trip_ezpass_weekend_peak", "ezpass_rate_weekend_peak",
                                  "weekend peak (Saturday/Sunday 11 a.m. to 9 p.m.)")):
        items, seen_daily = [], set()
        for leg_name, leg in (("to_jamaica", to), ("from_jamaica", back)):
            for it in leg["tolled_facilities"]:
                if not it["charged"]:
                    continue
                if it.get("once_per_day"):
                    if it["facility_id"] in seen_daily:
                        continue
                    seen_daily.add(it["facility_id"])
                basis_key = "ezpass_basis" if rate_key == "ezpass_rate" else "ezpass_basis_weekend_peak"
                items.append({"leg": leg_name, "facility": it["facility"], "agency": it["agency"],
                              "ezpass_rate": it.get(rate_key), "ezpass_basis": it.get(basis_key, ""),
                              "mail_rate": it.get("mail_rate"), "value_type": it["value_type"],
                              "effective_date": it.get("effective_date", ""), "source_url": it.get("source_url", ""),
                              "retrieved_at": it.get("retrieved_at", ""), "notes": it.get("notes", "")})
        missing = [i["facility"] for i in items if i["ezpass_rate"] is None]
        known = round(sum(i["ezpass_rate"] for i in items if i["ezpass_rate"] is not None), 2)
        method = (f"sum of official E-ZPass passenger-car rates, {label}, for every charged facility on the OSRM "
                  f"fastest free-flow route in each direction; a once-per-day charge is counted once; crossing "
                  f"credits and resident or commuter discounts are not applied")
        if missing:
            res[key] = _val(None, "not_found", TOLLS_CSV.relative_to(ROOT).as_posix(), prov[1], method,
                            reason="official rate not_found for: " + "; ".join(sorted(set(missing))),
                            known_subtotal=known, complete=False, items=items)
        else:
            res[key] = _val(known, "estimate" if items else "found", TOLLS_CSV.relative_to(ROOT).as_posix(), prov[1],
                            method, complete=True, items=items)
    mails = [i for leg in (to, back) for i in leg["tolled_facilities"] if i["charged"]]
    seen, mail_items = set(), []
    for i in mails:
        if i.get("once_per_day") and i["facility_id"] in seen:
            continue
        seen.add(i["facility_id"]) if i.get("once_per_day") else None
        mail_items.append(i)
    mm = [i["facility"] for i in mail_items if i.get("mail_rate") is None]
    mk = round(sum(i["mail_rate"] for i in mail_items if i.get("mail_rate") is not None), 2)
    res["toll_round_trip_mail"] = _val(
        None if mm else mk, "not_found" if mm else ("estimate" if mail_items else "found"),
        TOLLS_CSV.relative_to(ROOT).as_posix(), prov[1],
        "sum of Tolls by Mail (or cash) rates for the same facilities", known_subtotal=mk,
        **({"reason": "mail rate not_found for: " + "; ".join(sorted(set(mm)))} if mm else {}))
    res["toll_free_alternative"] = {
        "exclude_toll_supported": _val(EXCLUDE_TOLL_SUPPORTED, "found", OSRM_HOST, "2026-11-15",
                                       "one test request with exclude=toll", note=EXCLUDE_TOLL_NOTE),
        "minutes_to_jamaica": to["toll_free_alternative"],
        "minutes_from_jamaica": back["toll_free_alternative"],
    }
    why = "needs a traffic-aware routing key"
    for k in ("saturday_traffic_minutes_to_jamaica", "saturday_traffic_minutes_from_jamaica",
              "sunday_traffic_minutes_to_jamaica", "sunday_traffic_minutes_from_jamaica"):
        res[k] = _val(None, "not_found", None, None, reason=why)
    return res


# ----------------------------------------------------------------------------------------------------------------
# Reference builder: official pages and PDFs -> data/reference/*.csv. Idempotent; uses the caches under raw/.
# ----------------------------------------------------------------------------------------------------------------
SRC = {
    "mta": "https://www.mta.info/fares-tolls/tolls",
    "panynj_page": "https://www.panynj.gov/bridges-tunnels/en/tolls.html",
    "panynj_json": "https://www.panynj.gov/content/bridges-tunnels/en/tolls.model.json",
    "gmmcb": "https://thruway.ny.gov/sites/default/files/2025-07/gmmcb-toll-charts.pdf",
    "gantry": "https://thruway.ny.gov/sites/default/files/2025-07/gantry-rate-toll-charts.pdf",
    "ticket_ez": "https://thruway.ny.gov/sites/default/files/2025-07/2024-ny-e-zpass-cpm.pdf",
    "ticket_mail": "https://thruway.ny.gov/sites/default/files/2025-07/2024-non-ny-tbm-cpm.pdf",
    "thruway_ics": "https://data.ny.gov/resource/7jkf-259w.json",
    "nysba": "https://nysba.ny.gov/toll-rates",
    "crz_release": ("https://www.governor.ny.gov/news/putting-commuters-first-keeping-costs-down-governor-hochul-"
                    "unveils-plans-future-transit-and"),
    "crz_geofence": "https://data.ny.gov/resource/srxy-5nxn.json",
    "ncba": "https://www.ncbaabb.com/wp-content/uploads/2024-Toll-Rate-Schedule.pdf",
    "register": "https://dos.ny.gov/system/files/documents/2025/07/071625.pdf",
}


def _pdf_text(path: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=True).stdout


def _get(url: str, source: str, ext: str, **kw):
    content, meta = lib.cached_get(url, source, ext=ext, **kw)
    if meta["status"] != 200:
        raise RuntimeError(f"HTTP {meta['status']} for {url}")
    return content, meta


def _ticket_table(text: str, header: str) -> dict:
    """{('15','17'): 1.39, ...} from the first (Class 2L) page of a Thruway cost-per-mile fare table."""
    page = text[text.index(header):]
    out = {}
    cols = ["15", "16", "17", "18", "19", "20", "21", "21B"]
    for row in ("17", "18", "19", "20", "21", "21B"):
        m = re.search(rf"^\s*{row}\s+[A-Za-z].*?((?:\s+\d+\.\d\d)+)\s+{row}\b", page, re.M)
        vals = re.findall(r"\d+\.\d\d", m.group(1))
        for c, v in zip(cols, vals):
            out[(c, row)] = float(v)
    return out


def build_reference() -> dict:
    """Write tolls.csv, njta_tolls.csv, njta_interchanges.csv and crz_geofence.json from official sources."""
    REF.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    def add(fid, scenario, ez, basis, mail, eff, src, ret, vt="found", notes="", facility=None, agency=None,
            direction=None, lat=None, lon=None):
        f = FAC_BY_ID.get(fid, {})
        la, lo = (f["pts"][0] if f else (lat, lon))
        rows.append({"facility": facility or f["name"], "agency": agency or f["agency"],
                     "direction_charged": direction or f["direction"],
                     "ezpass_rate": ez if isinstance(ez, str) else f"{ez:.2f}", "ezpass_basis": basis,
                     "mail_rate": mail if isinstance(mail, str) else f"{mail:.2f}", "effective_date": eff,
                     "lat": la if lat is None else lat, "lon": lo if lon is None else lon, "source_url": src,
                     "retrieved_at": ret, "facility_id": fid, "scenario": scenario, "value_type": vt, "notes": notes})

    # Hand-entered rows survive a rebuild (value_type found_manual).
    manual = {}
    if TOLLS_CSV.exists():
        for r in csv.DictReader(open(TOLLS_CSV, newline="")):
            if r.get("value_type") == "found_manual":
                manual.setdefault(r["facility_id"], []).append(r)

    # --- MTA Bridges and Tunnels: site is behind an Akamai bot wall (403 on every path, robots.txt included). ----
    mta_ret = lib.now_iso()
    idx = lib.RAW / "mta_tolls" / "_index.jsonl"
    if idx.exists():
        for line in idx.read_text().splitlines():
            j = json.loads(line)
            if "mta.info" in j["url"] and j["status"] == 403:
                mta_ret = j["retrieved_at"]
    mta_note = ("not_found: mta.info returns HTTP 403 (Akamai bot wall) for the toll pages, its PDFs "
                "(/document/...) and robots.txt. The NYS Register of 2025-07-16 (" + SRC["register"] + ", "
                "appendix p. 87) prints only the PROPOSED ceiling schedule (I.D. TBA-28-25-00011-P), not the adopted "
                "rates, so it is not used. Read the rate on mta.info by hand and enter it with value_type "
                "found_manual")
    for f in FACILITIES:
        if f["id"].startswith("mta_"):
            if f["id"] in manual:
                rows.extend(manual[f["id"]])
            else:
                add(f["id"], "all", "not_found", "NY E-ZPass (NYCSC), passenger car", "not_found", "not_found",
                    SRC["mta"], mta_ret, "not_found", mta_note)

    # --- Port Authority: the tolls page is rendered from this JSON model. ----------------------------------------
    c, meta = _get(SRC["panynj_json"], "panynj", "json")
    s = c.decode("utf8", "replace").replace("\\u003C", "<").replace("\\u003E", ">").replace('\\"', '"')
    s = re.sub(r"\\[nrt]", " ", s)
    t = _text(s)
    m = re.search(r"VEHICLES WITH TWO AXLES & SINGLE REAR WHEELS.*? 2 \$([\d.]+) \$([\d.]+) \$([\d.]+) N/A \$([\d.]+)", t)
    off, peak, mid, mail = (float(x) for x in m.groups())
    hdr = re.search(r"OFF-PEAK HOURS\s+PEAK HOURS\s+MID-TIER", t)
    assert hdr and "TOLLS BY MAIL ALL HOURS OFF-PEAK HOURS" in t, "Port Authority table layout changed"
    cap = re.search(r"(\w+ 20\d\d) Toll Rates", t)
    hours = re.search(r"Peak Hours Weekdays: (.*?) Off-Peak Hours", t)
    pa_note = (f"class 1 (two axles, single rear wheels); table titled '{cap.group(1)} Toll Rates'; peak hours: "
               f"weekdays {hours.group(1).replace('Saturday', '; Saturday')}; mid-tier (tag not read) ${mid:.2f}; "
               f"E-ZPass discounts apply only to NY and NJ E-ZPass accounts. Read from the page's JSON model "
               f"({SRC['panynj_json']})")
    for f in FACILITIES:
        if f["id"].startswith("pa_"):
            eff = f"not stated for cars (table titled {cap.group(1)} Toll Rates)"
            add(f["id"], "weekend_offpeak", off, "NY/NJ E-ZPass off-peak", mail, eff, SRC["panynj_page"],
                meta["retrieved_at"], notes=pa_note)
            add(f["id"], "weekend_peak", peak, "NY/NJ E-ZPass peak (incl. Sat/Sun 11 a.m.-9 p.m.)", mail, eff,
                SRC["panynj_page"], meta["retrieved_at"], notes=pa_note)

    # --- NYS Thruway ------------------------------------------------------------------------------------------------
    c, meta = _get(SRC["gmmcb"], "thruway", "pdf")
    t = _pdf_text(ROOT / meta["path"])
    cur = t[t.index("Current Toll Rates 1/1/26"):t.index("Toll Rates 1/1/27")]
    m = re.search(r"^\s*2L\s+\$([\d.]+)\s+\$([\d.]+)\s+\$([\d.]+)", cur, re.M)
    ics_c, ics_meta = _get(SRC["thruway_ics"], "thruway", "json", params={"$limit": "2000"})
    tb = {r["description"]: r for r in json.loads(ics_c) if r["type"] == "Toll Barrier"}
    dir_note = "location and tolled direction from data.ny.gov 'Thruway Interchanges and Exits' (7jkf-259w): "
    add("thruway_cuomo", "all", float(m.group(2)), "NY E-ZPass (peak and off-peak are equal for class 2L)",
        float(m.group(3)), "2026-01-01", SRC["gmmcb"], meta["retrieved_at"],
        notes=dir_note + "'Tappan Zee Bridge Toll Barrier (Southbound Toll Only)'; mail_rate is the Non-NY "
                         "E-ZPass / Tolls by Mail rate; next change 2027-01-01 ($7.75 / $13.56)")
    c, meta = _get(SRC["gantry"], "thruway", "pdf")
    t = _pdf_text(ROOT / meta["path"])
    ny = t[t.index("Current rates New York E-ZPass customers"):t.index("Current rates Non New York")]
    non = t[t.index("Current rates Non New York"):t.index("Proposed rates New York E-ZPass")]
    a = [float(x) for x in re.findall(r"\$([\d.]+)", re.search(r"^\s*2L\s+(.*)$", ny, re.M).group(1))]
    b = [float(x) for x in re.findall(r"\$([\d.]+)", re.search(r"^\s*2L\s+(.*)$", non, re.M).group(1))]
    # columns: mainline per mile, Castleton, Grand Island, Harriman, Yonkers, New Rochelle, Spring Valley
    eff = "2024-01-01 (labelled 'Current rates'; next change 2027-01-01)"
    for fid, k, desc in (("thruway_harriman", 3, "Harriman Toll Barrier"), ("thruway_yonkers", 4, "Yonkers Toll Barrier"),
                         ("thruway_new_rochelle", 5, "New Rochelle Toll Barrier (Northbound Toll Only)")):
        assert desc in tb, desc
        add(fid, "all", a[k], "NY E-ZPass, class 2L", b[k], eff, SRC["gantry"], meta["retrieved_at"],
            notes=dir_note + f"'{desc}'; mail_rate is the Non-NY E-ZPass / Tolls by Mail rate")
    sv = tb["Spring Valley Toll Barrier (Northbound Toll For Commercial Vehicles Only)"]
    add("thruway_spring_valley", "all", a[6], "NY E-ZPass, class 2L", b[6], eff, SRC["gantry"], meta["retrieved_at"],
        notes=dir_note + "commercial vehicles only; cars pay nothing, so the tool does not look for it",
        facility="Spring Valley Toll Barrier (I-87)", agency="NYS Thruway Authority",
        direction="northbound, commercial vehicles only", lat=float(sv["latitude"]), lon=float(sv["longitude"]))
    c, m1 = _get(SRC["ticket_ez"], "thruway", "pdf")
    ez = _ticket_table(_pdf_text(ROOT / m1["path"]), "Class 2L New York E-ZPass")
    c, m2 = _get(SRC["ticket_mail"], "thruway", "pdf")
    ml = _ticket_table(_pdf_text(ROOT / m2["path"]), "Class 2L Non NY E-ZPass/Tolls by Mail")
    for i, x in enumerate(THRUWAY_TICKET_ORDER):
        for y in THRUWAY_TICKET_ORDER[i + 1:]:
            la, lo = THRUWAY_TICKET_PTS[y]
            add(f"thruway_ticket_{x}_{y}", "all", ez[(x, y)], "NY E-ZPass, class 2L", ml[(x, y)],
                "2024-01-01 ('Toll Schedule 2024'; next change 2027-01-01)", SRC["ticket_ez"], m1["retrieved_at"],
                notes="ticket-system fare between interchanges; '15' is the Woodbury barrier; mail_rate from "
                      + SRC["ticket_mail"] + "; lat/lon is the farther interchange (data.ny.gov 7jkf-259w)",
                facility=f"NYS Thruway ticket system, interchange {x} to {y}", agency="NYS Thruway Authority",
                direction="both directions", lat=la, lon=lo)

    # --- NYS Bridge Authority ---------------------------------------------------------------------------------------
    c, meta = _get(SRC["nysba"], "nysba", "html")
    t = _text(c)
    m = re.search(r"Class 1 \(Cars, Pick-ups, Motorcycles\).*?\$([\d.]+) \$([\d.]+)", t)
    for f in FACILITIES:
        if f["id"].startswith("nysba_"):
            add(f["id"], "all", float(m.group(1)), "E-ZPass, class 1 (any time)", float(m.group(2)),
                "not stated on the page", SRC["nysba"], meta["retrieved_at"],
                notes="one rate table for all NYSBA bridges; the page does not state the tolled direction: "
                      "'eastbound only' is general knowledge, not confirmed on an official page reached here")

    # --- Manhattan congestion relief zone ---------------------------------------------------------------------------
    c, meta = _get(SRC["crz_release"], "nygov", "html")
    t = _text(c)
    m = re.search(r"Daytime E-ZPass tolls Passenger vehicles \(once per day\): \$(\d+(?:\.\d+)?)", t)
    assert m and "starting at midnight on January 5" in t and "Nighttime discounts of 75 percent" in t
    if CRZ_ID in manual:
        rows.extend(manual[CRZ_ID])
    else:
        add(CRZ_ID, "all", float(m.group(1)), "E-ZPass daytime, passenger vehicle, once per day", "not_found",
            "2025-01-05", SRC["crz_release"], meta["retrieved_at"],
            notes="from the Governor's 2024-11-14 release of the plan (the MTA's own page is behind the bot wall): "
                  "'Daytime E-ZPass tolls, Passenger vehicles (once per day): $9', 'Nighttime discounts of 75 "
                  "percent', 'Tunnel crossing credits reduced by 40 percent of original plan', no increase before "
                  "2028. Daytime hours, the Tolls by Mail rate and the crossing-credit amounts are not in the "
                  "release: not_found. The tool applies no crossing credit, so a trip through the Lincoln, Holland, "
                  "Queens-Midtown or Hugh L. Carey tunnel may be overstated by the credit",
            facility="Manhattan Congestion Relief Zone (south of and including 60th St)",
            agency="MTA (Triborough Bridge and Tunnel Authority)",
            direction="on entering the zone, once per day", lat=40.7549, lon=-73.9840)
    gj, gmeta = lib.get_json(SRC["crz_geofence"], "mta_tolls", params={"$limit": "50"})
    polys = [ast.literal_eval(r["polygon"]) if isinstance(r["polygon"], str) else r["polygon"] for r in gj]
    rings = sorted((p["coordinates"][0] for p in polys), key=len, reverse=True)
    CRZ_JSON.write_text(json.dumps({
        "source_url": gmeta["url"], "retrieved_at": gmeta["retrieved_at"],
        "dataset": "MTA Central Business District Geofence: Beginning June 2024 (data.ny.gov srxy-5nxn)",
        "note": "zone_polygon is the largest of the dataset's 7 polygons (the tolled zone, which already leaves "
                "out the FDR Drive, West Side Highway/Route 9A, Battery Park Underpass and Carey Tunnel "
                "connections). other_polygons are the 6 small polygons covering those excluded roadways and the "
                "Queensboro Bridge approach; they do not overlap the zone.",
        "zone_polygon": rings[0], "other_polygons": rings[1:]}))

    # --- Not tabulated ----------------------------------------------------------------------------------------------
    c, meta = _get(SRC["ncba"], "ncba", "pdf")
    t = _pdf_text(ROOT / meta["path"])
    ez_ = re.search(r"Passenger Vehicles, Trailers & All Franchise Buses - \(EZ Pass\)\s+\$([\d.]+)", t)
    cash_ = re.search(r"Passenger Vehicles & All Buses - \(CASH\)\s+\$([\d.]+)", t)
    yr = re.search(r"(20\d\d) Toll Rate Schedule", t).group(1)
    add("ncba_atlantic_beach", "all", float(ez_.group(1)), "E-ZPass, passenger vehicle", float(cash_.group(1)),
        f"{yr} ('{yr} Toll Rate Schedule', the schedule linked from ncbaabb.com on the retrieval date)", SRC["ncba"],
        meta["retrieved_at"],
        notes="added because the fastest Long Beach route crosses it; mail_rate is the cash rate; the schedule "
              "does not state the tolled direction ('both directions' is general knowledge); barrier-island "
              "residents (ZIP 11509, 11561, 11569) can register for a $2.50 E-ZPass rate")

    # --- NJ Turnpike Authority: interchange coordinates from the calculator page, rates from njta_tolls.csv --------
    c, meta = _get(NJTA_PAGE, "njta", "html")
    pk, pmeta = _get(NJTA_API, "njta", "html", params={"slug": "map/mode/toll-calculator", "form_id": "njta-map-1",
                                                     "tab": "parkway", "method": "exits"})
    ic_rows = []
    for road, page, pm in (("turnpike", c.decode("utf8", "replace"), meta), ("parkway", pk.decode("utf8", "replace"), pmeta)):
        for kind, sel in (("entrance", "entrance"), ("exit", "exit")):
            body = re.search(rf'<select[^>]*name="{sel}"[^>]*>([\s\S]*?)</select>', page).group(1)
            for o in re.finditer(r"<option([^>]*)>\s*([^<]*?)\s*</option>", body):
                at = o.group(1)
                g = lambda k: (re.search(rf'{k}="?([^"\s>]*)"?', at) or [None, ""])[1]  # noqa: E731
                if not g("value") or not g("data-lat"):
                    continue
                ic_rows.append({"road": road, "kind": kind, "id": g("value"), "name": _html.unescape(o.group(2)).split(": ", 1)[-1],
                                "lat": g("data-lat"), "lon": g("data-lng"), "milemarker": g("data-milemarker"),
                                "directions": (g("data-direction") or "").replace(",", "|"),
                                "source_url": pm["url"], "retrieved_at": pm["retrieved_at"]})
    with open(NJTA_IC_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ic_rows[0]))
        w.writeheader()
        w.writerows(ic_rows)
    # Every calculator answer already cached under raw/njta/ goes into njta_tolls.csv.
    nj = dict(_njta_rows()) if NJTA_CSV.exists() else {}
    for mp in sorted((lib.RAW / "njta").glob("*.meta.json")):
        mj = json.loads(mp.read_text())
        if "trip-details" not in mj["url"]:
            continue
        q = dict(x.split("=", 1) for x in mj["url"].split("?", 1)[1].split("&"))
        hp = ROOT / mj["path"]
        if not hp.exists():
            continue
        for r in _njta_parse(q["tab"], q.get("direction", ""), q["entrance"], q["exit"], hp.read_bytes(), mj):
            nj[(r["road"], r["direction"], r["entrance"], r["exit"], r["scenario"])] = r
    _njta_write(nj)
    _cache.pop("njta", None)
    add("njta_turnpike", "all", "see njta_tolls.csv", "NJ E-ZPass; peak rate applies all weekend", "see njta_tolls.csv",
        "not stated by the calculator", NJTA_PAGE, meta["retrieved_at"], "found",
        "entrance-to-exit fares from the NJTA toll calculator, one row per pair and rate type in "
        "data/reference/njta_tolls.csv; typical pairs follow", facility="NJ Turnpike (all interchange pairs)",
        agency="New Jersey Turnpike Authority", direction="entrance-to-exit trip", lat="", lon="")
    add("njta_parkway", "all", "see njta_tolls.csv", "E-ZPass", "see njta_tolls.csv",
        "not stated by the calculator", NJTA_PAGE, pmeta["retrieved_at"], "found",
        "entrance-to-exit totals from the NJTA toll calculator, fetched for the pairs routes actually use and "
        "stored in data/reference/njta_tolls.csv", facility="Garden State Parkway (entrance-to-exit pairs)",
        agency="New Jersey Turnpike Authority", direction="entrance-to-exit trip, by direction", lat="", lon="")
    ics = {(r["road"], r["kind"], r["id"]): r for r in ic_rows}
    typical = [("turnpike", "", "10", "13"), ("turnpike", "", "11", "13"), ("turnpike", "", "09", "13"),
               ("turnpike", "", "11", "14C"), ("turnpike", "", "14", "14C"), ("turnpike", "", "13", "14C"),
               ("turnpike", "", "07A", "13"), ("turnpike", "", "14", "18W"), ("turnpike", "", "11", "18W")]
    typical += sorted({k[:4] for k in nj if k[0] == "parkway"})
    for key in typical:
        for sc_key, r in sorted(nj.items()):
            if sc_key[:4] == key and r["value_type"] == "found":
                e = ics.get((key[0], "exit", key[3]), {})
                rows.append({**{c_: r.get(c_, "") for c_ in TOLL_COLS}, "lat": e.get("lat", ""), "lon": e.get("lon", ""),
                             "notes": "documented typical pair (lat/lon = exit interchange); " + r["notes"]})

    with open(TOLLS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TOLL_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c_: r.get(c_, "") for c_ in TOLL_COLS})
    _cache.clear()
    return {"tolls_rows": len(rows), "njta_rows": len(nj), "njta_interchanges": len(ic_rows)}


# ----------------------------------------------------------------------------------------------------------------
TEST_POINTS = [("Jamaica station", 40.699608, -73.808530), ("Forest Hills", 40.7196, -73.8448),
               ("Long Beach NY", 40.5890, -73.6649), ("Stamford CT", 41.0469, -73.5419),
               ("Jersey City Grove St", 40.7196, -74.0431), ("Beacon NY", 41.5060, -73.9845)]


def _show(name: str, r: dict) -> None:
    print(f"\n=== {name} ({r['input']['lat']}, {r['input']['lon']}) ===")
    for leg in ("to_jamaica", "from_jamaica"):
        d = r[leg]
        print(f"  {leg}: {d['miles']['value']} mi, {d['minutes_free_flow']['value']} min free-flow "
              f"[{d['minutes_free_flow']['value_type']}; {d['minutes_free_flow']['method']}]")
        if d["main_roads"]["value"]:
            print("    roads: " + "; ".join(f"{x['road']} {x['miles']} mi" for x in d["main_roads"]["value"]))
        for it in d["tolled_facilities"]:
            rate = "not_found" if it["ezpass_rate"] is None else f"${it['ezpass_rate']:.2f}"
            print(f"    toll: {it['facility']} | charged={it['charged']} | E-ZPass {rate} ({it.get('ezpass_basis', '')}) "
                  f"| {it['value_type']}")
        tf = d["toll_free_alternative"]
        print(f"    toll-free alternative: {tf['value']} min [{tf['value_type']}]"
              + (f" {tf.get('reason', '')[:110]}" if tf["value"] is None else f", {tf.get('miles')} mi"))
    for k in ("toll_round_trip_ezpass", "toll_round_trip_ezpass_weekend_peak", "toll_round_trip_mail"):
        t = r[k]
        extra = "" if t["value"] is not None else f" (known subtotal ${t['known_subtotal']:.2f}; {t['reason']})"
        print(f"  {k}: {t['value']} [{t['value_type']}]{extra}")
    print(f"  saturday/sunday traffic minutes: {r['saturday_traffic_minutes_to_jamaica']['value_type']} "
          f"({r['saturday_traffic_minutes_to_jamaica']['reason']})")


if __name__ == "__main__":
    import time
    if "--build-reference" in sys.argv:
        print(build_reference())
        sys.exit(0)
    for name, la, lo in TEST_POINTS:
        t0 = time.time()
        res = drive(la, lo)
        _show(name, res)
        print(f"  lookup took {time.time() - t0:.2f} s")
    if "--json" in sys.argv:
        print(json.dumps(drive(*TEST_POINTS[4][1:]), indent=1, default=str))
