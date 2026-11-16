"""Build site/map_base.json: simplified land, borough and state-line geometry for the page's inline SVG map.

Source: US Census cartographic boundary file, counties, 1:500,000 (cb_2023_us_county_500k), which is already
clipped to the shoreline, so "not a county" inside the frame is water (Atlantic, Long Island Sound, the harbor,
the lower Hudson). Fetched once through scripts/lib.py cached_get into raw/census_cb/ and reused after that.

Output coordinates are pre-projected to a flat pixel-like space so the page only has to drop the path strings
into an <svg>:  x = (lon - west) * cos(ref_lat) * scale,   y = (north - lat) * scale   (equirectangular, true
aspect at ref_lat). The same numbers are in the file under "proj" so the page can place points.

Idempotent: same input, same output (apart from "built_at"). Run:  python3 scripts/build_map_base.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import geopandas as gpd  # noqa: E402
import shapely  # noqa: E402
from shapely import affinity  # noqa: E402
from shapely.geometry import box  # noqa: E402
from shapely.ops import linemerge, unary_union  # noqa: E402

from lib import ROOT, cached_get, now_iso  # noqa: E402

URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_500k.zip"
OUT = ROOT / "site" / "map_base.json"
DATA = ROOT / "site" / "data.json"

REF_LAT = 40.8
KX = math.cos(math.radians(REF_LAT))
SCALE = 2000            # units per degree of latitude: 1 unit = 0.0005 degrees, about 55 m
MARGIN = 0.14           # degrees of margin around the neighborhoods
TOL = 0.0011            # Douglas-Peucker tolerance in degrees of latitude (about 120 m)
TOL_LINE = 0.002
MIN_AREA = 0.6e-5       # drop islands smaller than this (square degrees, x already scaled)

BOROUGHS = {"36061": "Manhattan", "36005": "The Bronx", "36081": "Queens", "36047": "Brooklyn",
            "36085": "Staten Island"}

# Place-name labels: neutral geography only. (text, lat, lon, kind, min_zoom)
LABELS = [
    ("Atlantic Ocean", 40.33, -73.45, "water", 1),
    ("Long Island Sound", 41.06, -73.12, "water", 1),
    ("Hudson River", 41.02, -73.895, "water", 5),
    ("Upper Bay", 40.665, -74.045, "water", 5),
    ("New Jersey", 40.62, -74.62, "state", 1),
    ("Connecticut", 41.62, -73.28, "state", 1),
    ("Hudson Valley", 41.52, -74.05, "state", 1),
    ("Long Island", 40.80, -73.28, "state", 1),
    ("Pennsylvania", 40.93, -75.02, "state", 2),
    ("Manhattan", 40.775, -73.968, "boro", 3.5),
    ("The Bronx", 40.853, -73.865, "boro", 3.5),
    ("Queens", 40.742, -73.80, "boro", 3.5),
    ("Brooklyn", 40.652, -73.925, "boro", 3.5),
    ("Staten Island", 40.585, -74.145, "boro", 3.5),
    ("Jersey City", 40.722, -74.085, "boro", 5),
]


def frame() -> tuple[float, float, float, float]:
    d = json.loads(DATA.read_text())
    pts = [(h["lon"], h["lat"]) for h in d["neighborhoods"] if h.get("lat") is not None]
    a = d["meta"]["anchor"]
    pts.append((a["lon"], a["lat"]))
    w = min(p[0] for p in pts) - MARGIN / KX
    e = max(p[0] for p in pts) + MARGIN / KX
    s = min(p[1] for p in pts) - MARGIN
    n = max(p[1] for p in pts) + MARGIN
    return (round(w, 2), round(s, 2), round(e, 2), round(n, 2))


def to_iso(g):
    """Scale longitude so one unit is the same ground length both ways; simplification is then even."""
    return affinity.scale(g, xfact=KX, yfact=1, origin=(0, 0))


def polys(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    if g.geom_type in ("MultiPolygon", "GeometryCollection"):
        return [p for x in g.geoms for p in polys(x)]
    return []


def lines(g):
    if g.is_empty:
        return []
    if g.geom_type == "LineString":
        return [g]
    if g.geom_type in ("MultiLineString", "GeometryCollection"):
        return [p for x in g.geoms for p in lines(x)]
    return []


class Proj:
    def __init__(self, w, n):
        self.w, self.n = w, n

    def xy(self, x_iso, lat):
        return (round((x_iso - self.w * KX) * SCALE), round((self.n - lat) * SCALE))


def ring_path(coords, pr, close=True):
    pts = []
    for x, y in coords:
        p = pr.xy(x, y)
        if not pts or p != pts[-1]:
            pts.append(p)
    if close and len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    if len(pts) < (3 if close else 2):
        return ""
    out = ["M%d %d" % pts[0], "l"]
    px, py = pts[0]
    seg = []
    for x, y in pts[1:]:
        seg.append("%d %d" % (x - px, y - py))
        px, py = x, y
    s = out[0] + "l" + " ".join(seg)
    s = s.replace(" -", "-")
    return s + ("z" if close else "")


def poly_path(geom, pr):
    parts = []
    for p in sorted(polys(geom), key=lambda q: -q.area):
        if p.area < MIN_AREA:
            continue
        parts.append(ring_path(p.exterior.coords, pr))
        for r in p.interiors:
            if shapely.Polygon(r).area >= MIN_AREA:
                parts.append(ring_path(r.coords, pr))
    return "".join(x for x in parts if x)


def main() -> None:
    content, meta = cached_get(URL, "census_cb", ext="zip", timeout=300)
    if meta["status"] != 200:
        raise SystemExit(f"HTTP {meta['status']} for {URL}; not retrying this host")
    zpath = ROOT / meta["path"]
    w, s, e, n = frame()
    bb = box(w, s, e, n)
    g = gpd.read_file(f"zip://{zpath}", bbox=(w, s, e, n))
    g = g[g.intersects(bb)].copy()
    g["geometry"] = g.geometry.intersection(bb)
    g = g[~g.geometry.is_empty]
    g["iso"] = g.geometry.apply(to_iso)
    pr = Proj(w, n)

    # Land: every county dissolved, simplified once so the coast is one clean edge.
    land = unary_union(list(g["iso"])).buffer(0)
    land_s = land.simplify(TOL, preserve_topology=True)

    # Boroughs: simplified as a coverage where the library allows, so shared edges stay shared.
    b = g[g["GEOID"].isin(BOROUGHS)].sort_values("GEOID")
    geoms = list(b["iso"])
    try:
        simp = list(shapely.coverage_simplify(geoms, TOL))
    except Exception:  # older shapely / GEOS: per-polygon simplify (tiny slivers show the land colour)
        simp = [x.simplify(TOL, preserve_topology=True) for x in geoms]
    boroughs = []
    for (_, row), sg in zip(b.iterrows(), simp):
        boroughs.append({"id": row["GEOID"], "name": BOROUGHS[row["GEOID"]], "d": poly_path(sg, pr)})

    # State lines: where two states' land touches (or nearly touches across a river).
    states = {st: unary_union(list(grp["iso"])) for st, grp in g.groupby("STUSPS")}
    border_parts = []
    names = sorted(states)
    for i, a in enumerate(names):
        for c in names[i + 1:]:
            shared = states[a].boundary.intersection(states[c].buffer(0.0005))
            border_parts.extend(lines(shared))
    merged = linemerge(border_parts) if border_parts else None
    borders = []
    for ln in lines(merged) if merged is not None else []:
        if ln.length < 0.01:
            continue
        d = ring_path(ln.simplify(TOL_LINE).coords, pr, close=False)
        if d:
            borders.append(d)

    # County lines outside the city: light context, heavily simplified.
    cl = []
    seen = list(g["iso"])
    for i in range(len(seen)):
        for j in range(i + 1, len(seen)):
            if seen[i].distance(seen[j]) > 0:
                continue
            sh = seen[i].boundary.intersection(seen[j].boundary)
            cl.extend(lines(sh))
    cm = linemerge(cl) if cl else None
    counties = []
    for ln in lines(cm) if cm is not None else []:
        if ln.length < 0.02:
            continue
        d = ring_path(ln.simplify(TOL_LINE * 2).coords, pr, close=False)
        if d:
            counties.append(d)

    labels = []
    for t, la, lo, kind, mz in LABELS:
        if not (w <= lo <= e and s <= la <= n):
            lo = min(max(lo, w + 0.12), e - 0.12)
        x, y = pr.xy(lo * KX, la)
        labels.append({"t": t, "x": x, "y": y, "kind": kind, "min_zoom": mz})

    out = {
        "meta": {
            "what": "Simplified base geometry for the inline SVG map: land, the five boroughs, state and county lines.",
            "source": "US Census Bureau, Cartographic Boundary Files 2023, counties, 1:500,000 (shoreline-clipped)",
            "source_url": meta["url"],
            "retrieved_at": meta["retrieved_at"],
            "built_at": now_iso(),
            "builder": "scripts/build_map_base.py",
            "simplification": f"Douglas-Peucker, tolerance {TOL} degrees of latitude on longitude-scaled coordinates; "
                              f"islands under {MIN_AREA} square degrees dropped; lines at {TOL_LINE} to {TOL_LINE * 2}",
            "label_note": "Label positions are hand-placed approximate points for place names, not measured data.",
        },
        "bbox": {"west": w, "south": s, "east": e, "north": n},
        "proj": {"type": "equirectangular", "ref_lat": REF_LAT, "kx": round(KX, 6), "scale": SCALE,
                 "west": w, "north": n,
                 "formula": "x=(lon-west)*kx*scale; y=(north-lat)*scale",
                 "width": round((e - w) * KX * SCALE), "height": round((n - s) * SCALE)},
        "land": poly_path(land_s, pr),
        "boroughs": boroughs,
        "state_lines": borders,
        "county_lines": counties,
        "labels": labels,
    }
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(ROOT)}: {kb:.1f} KB; frame {w},{s} to {e},{n}; "
          f"land {len(out['land'])} chars, boroughs {sum(len(x['d']) for x in boroughs)}, "
          f"state lines {sum(map(len, borders))}, county lines {sum(map(len, counties))}")
    if kb > 150:
        raise SystemExit("map_base.json is over the 150 KB target; raise TOL")


if __name__ == "__main__":
    main()
