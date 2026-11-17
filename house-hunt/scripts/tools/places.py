"""places: what is around an address, from a local OpenStreetMap index.

    from scripts.tools.places import near, area_profile
    near(40.7196, -73.8448)            # one building / address
    color(40.7196, -73.8448)           # the kind of life around it (gyms, bookshops, parking, street pattern ...)
    area_profile(40.7196, -73.8448)    # counts for a neighbourhood centre (radius 1,200 m)

Data: Geofabrik OpenStreetMap extract(s), cut to the bounding box of data/reference/search_grid.csv plus
a margin, reduced to the tags listed in docs/tools_notes/places.md and indexed in UTM 18N metres.
Everything big lives in raw/big/osm/ (git-ignored) and is rebuilt by `python -m scripts.tools.places --build`
(needs `pip install osmium scipy shapely pyproj` and the `osmium` command: `apt-get install osmium-tool`).

Every value is a dict: value, value_type (found / estimate / not_found), source_url, data_vintage,
retrieved_at, method (and reason when not_found). Distances are straight-line metres unless the key says walk.
"""
from __future__ import annotations

import csv
import json
import math
import pickle
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import lib  # noqa: E402

BIG = ROOT / "raw" / "big" / "osm"
GRID = ROOT / "data" / "reference" / "search_grid.csv"
META_CSV = ROOT / "data" / "reference" / "osm_extract_meta.csv"
REGION = BIG / "region.osm.pbf"          # bbox cut, all tags
FILTERED = BIG / "region_filtered.osm.pbf"  # bbox cut, only the tags we index
INDEX = BIG / "places_index.pkl"
BLD = BIG / "buildings"  # directory of .npy arrays, memory-mapped at lookup
META = BIG / "meta.json"

MARGIN_DEG = 0.15  # about 17 km north-south, 12.6 km east-west: more than the 10 km anchor radius
GEOFABRIK = "https://download.geofabrik.de/north-america/us/{}-latest.osm.pbf"
STATES = ["new-york", "new-jersey", "connecticut", "pennsylvania"]  # PA: 8 grid points are in Philadelphia
# Official mirror of download.geofabrik.de (robots.txt allows all). It carries only continent files.
MIRROR_NA = "https://ftp5.gwdg.de/pub/misc/openstreetmap/download.geofabrik.de/north-america-latest.osm.pbf"
OSM_URL = "https://www.openstreetmap.org/"

WALK_DETOUR = 1.3      # street-network distance / straight-line distance
WALK_M_PER_MIN = 80.0  # 4.8 km/h
PARK_MIN_M2 = 5000.0   # 0.5 ha
LAKE_MIN_M2 = 50000.0  # 5 ha
RIVER_MIN_M2 = 20000.0  # 2 ha per mapped polygon piece (rivers are mapped in pieces)
ANCHOR_RADIUS_M = 10000.0
LAMP_RADIUS_M = 150.0
LAMP_COVERAGE_RADIUS_M = 500.0
LAMP_COVERAGE_MIN = 150  # lamps within 500 m needed before the 150 m count is treated as real
X0, Y0 = 600000.0, 4500000.0  # offsets so building coordinates fit float32 at centimetre precision
CELL = 250.0

TAG_FILTER = [
    "nwr/leisure=park,nature_reserve,dog_park",
    "nwr/natural=beach,water", "w/natural=coastline", "wr/waterway=riverbank", "w/waterway=river",
    "nwr/amenity=restaurant,bar,pub,cafe,nightclub,music_venue,pharmacy,veterinary,coworking_space",
    "nwr/craft=brewery", "nwr/microbrewery=yes", "nwr/industrial=brewery",
    "nwr/shop", "nwr/office=coworking", "nwr/railway=station",
    "w/highway=motorway", "n/highway=street_lamp", "wr/building",
]

TAG_DEFS = {
    "park": "leisure=park or leisure=nature_reserve or natural=beach, mapped as an area",
    "dog_park": "leisure=dog_park",
    "restaurant": "amenity=restaurant",
    "bar": "amenity=bar or amenity=pub",
    "cafe": "amenity=cafe",
    "brewery": "craft=brewery or microbrewery=yes or industrial=brewery",
    "music": "amenity=nightclub or amenity=music_venue",
    "bakery": "shop=bakery",
    "supermarket": "shop=supermarket",
    "pharmacy": "amenity=pharmacy",
    "vet": "amenity=veterinary",
    "coworking": "amenity=coworking_space or office=coworking",
    "station": "railway=station (subway, light rail and mainline; the kind is reported)",
    "lamp": "highway=street_lamp (nodes)",
    "coastline": "natural=coastline (ways)",
    "motorway": "highway=motorway (ways; links excluded)",
    "beach": "natural=beach (area outline or node)",
    "water": "natural=water or waterway=riverbank areas: rivers/canals (water=river|canal) of 2 ha or more "
             "per mapped piece, lakes/reservoirs/ponds of 5 ha or more",
    "building": "building=* (ways and multipolygons)",
}
ANCHORS = {
    "trader_joes": "Trader Joe's", "whole_foods": "Whole Foods", "wegmans": "Wegmans",
    "h_mart": "H Mart", "target": "Target", "costco": "Costco",
}
ANCHOR_SHOPS = {"supermarket", "grocery", "convenience", "greengrocer", "department_store", "wholesale",
                "general", "variety_store", "health_food", "organic"}
COUNT_CATS = ["restaurant", "bar", "cafe", "brewery", "music"]


# ----------------------------------------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------------------------------------

def bbox() -> tuple[float, float, float, float]:
    """(west, south, east, north) of the search grid plus the margin."""
    with open(GRID) as f:
        rows = list(csv.DictReader(f))
    la = [float(r["lat"]) for r in rows]
    lo = [float(r["lon"]) for r in rows]
    return (round(min(lo) - MARGIN_DEG, 4), round(min(la) - MARGIN_DEG, 4),
            round(max(lo) + MARGIN_DEG, 4), round(max(la) + MARGIN_DEG, 4))


def _download(url: str, dest: Path) -> dict:
    """Streamed download (lib.cached_get holds the body in memory, which a multi-GB file cannot afford)."""
    import requests
    lib.check_host(url)                 # refused / off-limits hosts are never requested (CLAUDE.md)
    BIG.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, headers={"User-Agent": lib.USER_AGENT}, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 22):
                f.write(chunk)
    tmp.rename(dest)
    meta = {"url": url, "retrieved_at": lib.now_iso(), "status": 200,
            "path": str(dest.relative_to(ROOT)), "source": "big/osm", "bytes": dest.stat().st_size}
    with open(BIG / "_index.jsonl", "a") as f:
        f.write(json.dumps(meta) + "\n")
    return meta


def _file_date(path: Path) -> str:
    import osmium
    r = osmium.io.Reader(str(path))
    try:
        return r.header().get("osmosis_replication_timestamp") or ""
    finally:
        r.close()


def _osmium(*args: str) -> None:
    if not shutil.which("osmium"):
        raise RuntimeError("the osmium command is needed to cut the extract: apt-get install osmium-tool")
    subprocess.run(["osmium", *args], check=True)


def fetch_region() -> list[dict]:
    """Make REGION (bbox cut). Tries the Geofabrik state files, then the mirror's North America file."""
    if REGION.exists() and META.exists():
        return json.loads(META.read_text())["files"]
    w, s, e, n = bbox()
    b = f"{w},{s},{e},{n}"
    files, cuts = [], []
    try:
        for st in STATES:
            dest = BIG / f"{st}-latest.osm.pbf"
            m = _download(GEOFABRIK.format(st), dest) if not dest.exists() else \
                {"url": GEOFABRIK.format(st), "retrieved_at": _mtime_iso(dest), "bytes": dest.stat().st_size}
            m["osm_data_timestamp"] = _file_date(dest)
            files.append(m)
            cut = BIG / f"cut_{st}.osm.pbf"
            _osmium("extract", "-b", b, "-s", "smart", "-O", "-o", str(cut), str(dest))
            cuts.append(cut)
        _osmium("merge", "-O", "-o", str(REGION), *map(str, cuts))
        for c in cuts:
            c.unlink()
    except Exception as err:  # download.geofabrik.de reset every connection from this host on 2026-11-15
        print(f"state files failed ({err!r}); using the mirror's North America file", flush=True)
        files = []
        dest = BIG / "north-america-latest.osm.pbf"
        m = _download(MIRROR_NA, dest) if not dest.exists() else \
            {"url": MIRROR_NA, "retrieved_at": _mtime_iso(dest), "bytes": dest.stat().st_size}
        m["osm_data_timestamp"] = _file_date(dest)
        files.append(m)
        _osmium("extract", "-b", b, "-s", "smart", "-O", "-o", str(REGION), str(dest))
    META.write_text(json.dumps({"bbox_wsen": [w, s, e, n], "files": files}, indent=1))
    return files


def _mtime_iso(p: Path) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(p.stat().st_mtime))


def _norm(s: str | None) -> str:
    return (s or "").lower().replace("’", "'").strip()


def _anchor(t: dict) -> str | None:
    shop = t.get("shop")
    if shop not in ANCHOR_SHOPS:
        return None
    name, brand = _norm(t.get("name")), _norm(t.get("brand"))
    s = brand + "|" + name
    if "trader joe" in s:
        return "trader_joes"
    if "whole foods" in s:
        return "whole_foods"
    if "wegmans" in s:
        return "wegmans"
    if re.search(r"\bh[ -]?mart\b", s):
        return "h_mart"
    if "costco" in s:
        return "costco"
    if brand == "target" or re.fullmatch(r"(super ?)?target", name):
        return "target"
    return None


def _point_cats(t: dict) -> list[str]:
    c = []
    a, s = t.get("amenity"), t.get("shop")
    if a == "restaurant":
        c.append("restaurant")
    elif a in ("bar", "pub"):
        c.append("bar")
    elif a == "cafe":
        c.append("cafe")
    elif a in ("nightclub", "music_venue"):
        c.append("music")
    elif a == "pharmacy":
        c.append("pharmacy")
    elif a == "veterinary":
        c.append("vet")
    if t.get("craft") == "brewery" or t.get("microbrewery") == "yes" or t.get("industrial") == "brewery":
        c.append("brewery")
    if a == "coworking_space" or t.get("office") == "coworking":
        c.append("coworking")
    if s == "bakery":
        c.append("bakery")
    elif s == "supermarket":
        c.append("supermarket")
    if s:
        k = _anchor(t)
        if k:
            c.append(k)
    if t.get("leisure") == "dog_park":
        c.append("dog_park")
    if t.get("railway") == "station":
        c.append("station")
    return c


def _station_kind(t: dict) -> str:
    st = t.get("station")
    if st == "subway" or t.get("subway") == "yes":
        return "subway"
    if st == "light_rail" or t.get("light_rail") == "yes":
        return "light_rail"
    if st in ("monorail", "funicular", "miniature") or t.get("monorail") == "yes" or t.get("tourism"):
        return "other"
    return "train"


def _water_kind(t: dict) -> str | None:
    w = t.get("water")
    if t.get("waterway") == "riverbank" or w == "river":
        return "river"
    if w == "canal":
        return "canal"
    if t.get("natural") == "water" and w in (None, "lake", "reservoir", "pond", "lagoon", "oxbow"):
        return "reservoir" if w == "reservoir" else "lake"
    return None


def _num(v: str | None) -> float:
    try:
        return float(str(v).split(";")[0].replace("m", "").strip())
    except (TypeError, ValueError):
        return float("nan")


def build_index() -> None:
    import osmium
    import pyproj
    import shapely
    from scipy.spatial import cKDTree

    files = fetch_region()
    if not FILTERED.exists():
        tmp = BIG / "region_filtered.tmp.osm.pbf"
        _osmium("tags-filter", "-O", "-o", str(tmp), str(REGION), *TAG_FILTER)
        tmp.rename(FILTERED)
    tr = pyproj.Transformer.from_crs(4326, 32618, always_xy=True)

    def proj(geoms):
        return shapely.transform(geoms, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))

    wkbf = osmium.geom.WKBFactory()
    pts = defaultdict(lambda: {"lon": [], "lat": [], "name": [], "ref": [], "extra": []})
    area_pts = []   # (wkb, cats, name, ref, extra): centroid goes into pts
    parks = []      # (wkb, name, ref, kind)
    waters = []     # (wkb, name, ref, kind)
    beaches = []    # (wkb, name, ref)
    lines = defaultdict(list)  # kind -> (wkb, name, ref)
    b_wkb, b_type, b_lev, b_h, b_id, b_names, b_flats = [], [], [], [], [], {}, {}
    bchunks = []
    bad = 0

    def flush_buildings():
        if not b_wkb:
            return
        g = proj(shapely.from_wkb(np.array(b_wkb, dtype=object)))
        parts, pidx = shapely.get_parts(g, return_index=True)
        ext = shapely.get_exterior_ring(parts)
        coords, ridx = shapely.get_coordinates(ext, return_index=True)
        counts = np.bincount(ridx, minlength=len(ext))
        bchunks.append((coords - [X0, Y0], counts, pidx + flush_buildings.base))
        flush_buildings.base += len(b_wkb)
        b_wkb.clear()
    flush_buildings.base = 0

    t0 = time.time()
    for o in osmium.FileProcessor(str(FILTERED)).with_areas():
        tags = o.tags
        if o.is_node():
            if tags.get("highway") == "street_lamp":
                d = pts["lamp"]
                d["lon"].append(o.location.lon); d["lat"].append(o.location.lat)
                continue
            t = {x.k: x.v for x in tags}
            if not t:
                continue
            cats = _point_cats(t)
            if t.get("natural") == "beach":
                cats.append("beach_node")
            for c in cats:
                d = pts[c]
                d["lon"].append(o.location.lon); d["lat"].append(o.location.lat)
                d["name"].append(t.get("name")); d["ref"].append(f"node/{o.id}")
                d["extra"].append(_station_kind(t) if c == "station" else None)
        elif o.is_way():
            hw, nat, ww = tags.get("highway"), tags.get("natural"), tags.get("waterway")
            kind = "motorway" if hw == "motorway" else "coastline" if nat == "coastline" else \
                "river_line" if ww == "river" else None
            if kind:
                try:
                    nm = tags.get("name")
                    if kind == "motorway":
                        nm = " / ".join(x for x in (tags.get("ref"), nm) if x) or None
                    lines[kind].append((wkbf.create_linestring(o), nm, f"way/{o.id}"))
                except Exception:
                    bad += 1
        elif o.is_area():
            ref = f"{'way' if o.from_way() else 'relation'}/{o.orig_id()}"
            bt = tags.get("building")
            try:
                w = wkbf.create_multipolygon(o)
            except Exception:
                bad += 1
                continue
            if bt:
                i = flush_buildings.base + len(b_wkb)
                b_wkb.append(w); b_type.append(bt); b_id.append(ref)
                b_lev.append(_num(tags.get("building:levels"))); b_h.append(_num(tags.get("height")))
                nm = tags.get("name")
                if nm:
                    b_names[i] = nm
                fl = tags.get("building:flats")
                if fl:
                    b_flats[i] = fl
                if len(b_wkb) >= 200000:
                    flush_buildings()
                    print(f"  buildings {flush_buildings.base:,} ({time.time() - t0:.0f}s)", flush=True)
                if len(tags) <= 2:
                    continue
            t = {x.k: x.v for x in tags}
            name = t.get("name")
            cats = _point_cats(t)
            if cats:
                area_pts.append((w, cats, name, ref, _station_kind(t) if "station" in cats else None))
            if t.get("leisure") in ("park", "nature_reserve") or t.get("natural") == "beach":
                parks.append((w, name, ref, t.get("leisure") if t.get("leisure") in ("park", "nature_reserve")
                              else "beach"))
            if t.get("natural") == "beach":
                beaches.append((w, name, ref))
            wk = _water_kind(t)
            if wk:
                waters.append((w, name, ref, wk))
    flush_buildings()
    print(f"read done in {time.time() - t0:.0f}s; invalid geometries skipped: {bad}", flush=True)

    # ---- points -----------------------------------------------------------------------------------------
    if area_pts:
        cen = shapely.centroid(shapely.from_wkb(np.array([a[0] for a in area_pts], dtype=object)))
        cx, cy = shapely.get_x(cen), shapely.get_y(cen)
        for (w, cats, name, ref, extra), lon, lat in zip(area_pts, cx, cy):
            for c in cats:
                d = pts[c]
                d["lon"].append(lon); d["lat"].append(lat); d["name"].append(name); d["ref"].append(ref)
                d["extra"].append(extra)
    out_pts = {}
    for c, d in pts.items():
        x, y = tr.transform(np.array(d["lon"]), np.array(d["lat"]))
        xy = np.column_stack([x, y])
        if c == "lamp":
            out_pts[c] = {"xy": xy, "tree": cKDTree(xy)}
            continue
        keep = np.ones(len(xy), bool)
        names = [_norm(nm) for nm in d["name"]]
        # the same place mapped twice (a node and its building outline): same name within 60 m
        for i, j in sorted(cKDTree(xy).query_pairs(60.0)):
            if keep[i] and keep[j] and names[i] and names[i] == names[j]:
                keep[j] = False
        ix = np.flatnonzero(keep)
        out_pts[c] = {"xy": xy[ix], "tree": cKDTree(xy[ix]), "name": [d["name"][i] for i in ix],
                      "ref": [d["ref"][i] for i in ix], "extra": [d["extra"][i] for i in ix],
                      "dropped_duplicates": int((~keep).sum())}

    # ---- lines and outlines, densified to points ---------------------------------------------------------
    def densify(recs, step, boundary=False, min_area=None):
        if not recs:
            return None
        g = proj(shapely.from_wkb(np.array([r[0] for r in recs], dtype=object)))
        ok = np.ones(len(g), bool)
        if min_area is not None:
            ok = shapely.area(g) >= np.array(min_area)
        if boundary:
            g = shapely.boundary(g)
        g = shapely.segmentize(g, step)
        ix = np.flatnonzero(ok)
        coords, fid = shapely.get_coordinates(g[ix], return_index=True)
        return {"xy": coords, "tree": cKDTree(coords), "fid": fid.astype(np.int32),
                "name": [recs[i][1] for i in ix], "ref": [recs[i][2] for i in ix],
                "kind": [recs[i][3] if len(recs[i]) > 3 else None for i in ix]}

    out_lines = {
        "coastline": densify(lines["coastline"], 25.0),
        "motorway": densify(lines["motorway"], 25.0),
        "river_line": densify(lines["river_line"], 100.0),
        "beach": densify(beaches, 20.0, boundary=True),
        "water": densify(waters, 30.0, boundary=True,
                         min_area=[RIVER_MIN_M2 if r[3] in ("river", "canal") else LAKE_MIN_M2 for r in waters]),
    }
    bn = out_pts.pop("beach_node", None)
    if bn is not None and out_lines["beach"] is not None:  # beaches mapped only as a node
        bl = out_lines["beach"]
        n0 = len(bl["name"])
        bl["xy"] = np.vstack([bl["xy"], bn["xy"]])
        bl["fid"] = np.concatenate([bl["fid"], np.arange(n0, n0 + len(bn["xy"]), dtype=np.int32)])
        bl["name"] += bn["name"]; bl["ref"] += bn["ref"]; bl["kind"] += [None] * len(bn["name"])
        bl["tree"] = cKDTree(bl["xy"])

    # ---- parks (polygons kept) ---------------------------------------------------------------------------
    pg = proj(shapely.from_wkb(np.array([p[0] for p in parks], dtype=object)))
    pg = shapely.make_valid(shapely.simplify(pg, 2.0))
    out_parks = {"geom": pg, "area_m2": shapely.area(pg), "name": [p[1] for p in parks],
                 "ref": [p[2] for p in parks], "kind": [p[3] for p in parks]}

    # ---- buildings: rings sorted by 250 m grid cell, in a memory-mapped npz --------------------------------
    coords = np.vstack([b[0] for b in bchunks]).astype(np.float32)
    counts = np.concatenate([b[1] for b in bchunks])
    ring_bld = np.concatenate([b[2] for b in bchunks]).astype(np.int32)
    start = np.concatenate([[0], np.cumsum(counts)]).astype(np.int64)
    c64 = coords.astype(np.float64)
    seg = np.repeat(np.arange(len(counts)), counts)
    cen = np.column_stack([np.bincount(seg, c64[:, 0]) / counts, np.bincount(seg, c64[:, 1]) / counts])
    d = np.hypot(c64[:, 0] - cen[seg, 0], c64[:, 1] - cen[seg, 1])
    rad = np.zeros(len(counts)); np.maximum.at(rad, seg, d)
    cell = (np.floor(cen[:, 0] / CELL).astype(np.int64) + 100000) * 1000000 + \
           (np.floor(cen[:, 1] / CELL).astype(np.int64) + 100000)
    order = np.argsort(cell, kind="stable")
    types, tcode = np.unique(np.array(b_type, dtype=object).astype(str), return_inverse=True)
    BLD.mkdir(exist_ok=True)
    for k, v in dict(coords=coords, start=start, ring_bld=ring_bld, cen=cen.astype(np.float32),
                     rad=rad.astype(np.float32), cell_sorted=cell[order], order=order.astype(np.int32),
                     huge=np.flatnonzero(rad > 400).astype(np.int32), tcode=tcode.astype(np.uint16),
                     levels=np.array(b_lev, np.float32), height=np.array(b_h, np.float32)).items():
        np.save(BLD / f"{k}.npy", v)

    w, s, e, n = bbox()
    meta = {"built_at": lib.now_iso(), "bbox_wsen": [w, s, e, n], "margin_deg": MARGIN_DEG, "files": files,
            "source_url": files[0]["url"] if len(files) == 1 else "https://download.geofabrik.de/north-america/us.html",
            "osm_data_timestamp": min(f["osm_data_timestamp"] for f in files),
            "retrieved_at": max(f["retrieved_at"] for f in files),
            "counts": {**{c: len(v["xy"]) for c, v in out_pts.items()},
                       **{k: len(v["name"]) for k, v in out_lines.items() if v},
                       "park": len(parks), "building": len(b_type), "building_with_levels":
                           int(np.isfinite(np.array(b_lev)).sum())}}
    with open(INDEX, "wb") as f:
        pickle.dump({"meta": meta, "pts": out_pts, "lines": out_lines, "parks": out_parks,
                     "bld": {"types": list(types), "ref": np.array(b_id, dtype=object), "names": b_names,
                             "flats": b_flats}}, f, protocol=pickle.HIGHEST_PROTOCOL)
    META.write_text(json.dumps(meta, indent=1))
    with open(META_CSV, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["file", "source_url", "retrieved_at", "osm_data_timestamp", "bytes", "bbox_wsen", "license"])
        for fl in files:
            wr.writerow([fl["url"].rsplit("/", 1)[1], fl["url"], fl["retrieved_at"], fl["osm_data_timestamp"],
                         fl.get("bytes", ""), f"{w},{s},{e},{n}", "ODbL 1.0, (c) OpenStreetMap contributors"])
    print(json.dumps(meta["counts"], indent=1))


# ----------------------------------------------------------------------------------------------------------
# Lookup
# ----------------------------------------------------------------------------------------------------------

_IDX = None


def _load():
    global _IDX
    if _IDX is None:
        if not (INDEX.exists() and (BLD / "height.npy").exists()):
            build_index()
        import pyproj
        import shapely
        with open(INDEX, "rb") as f:
            idx = pickle.load(f)
        p = idx["parks"]
        big = np.flatnonzero(p["area_m2"] >= PARK_MIN_M2)
        named = np.array([i for i in big if p["name"][i]], dtype=int)
        p["big"], p["named"] = big, named
        p["tree_all"] = shapely.STRtree(p["geom"])
        p["tree_big"] = shapely.STRtree(p["geom"][big])
        p["tree_named"] = shapely.STRtree(p["geom"][named])
        idx["bldz"] = {f.stem: np.load(f, mmap_mode="r") for f in BLD.glob("*.npy")}
        idx["tr"] = pyproj.Transformer.from_crs(4326, 32618, always_xy=True)
        _IDX = idx
    return _IDX


def _prov(idx) -> dict:
    m = idx["meta"]
    return {"source_url": m["source_url"], "data_vintage": m["osm_data_timestamp"], "retrieved_at": m["retrieved_at"]}


def _val(idx, value, value_type="found", method=None, **extra) -> dict:
    d = {"value": value, "value_type": value_type, **_prov(idx), "method": method}
    d.update(extra)
    return d


def _missing(idx, reason: str, **extra) -> dict:
    return _val(idx, None, "not_found", None, reason=reason, **extra)


def _walk_min(m: float) -> float:
    return round(m * WALK_DETOUR / WALK_M_PER_MIN, 1)


def _in_coverage(idx, lat, lon) -> bool:
    w, s, e, n = idx["meta"]["bbox_wsen"]
    return w <= lon <= e and s <= lat <= n


def _count(idx, cat, xy, r) -> int:
    d = idx["pts"].get(cat)
    return 0 if d is None else len(d["tree"].query_ball_point(xy, r))


def _nearest_pts(idx, cat, xy, k=1, max_m=np.inf, named_only=False) -> list[dict]:
    d = idx["pts"].get(cat)
    if d is None or not len(d["xy"]):
        return []
    kk = min(len(d["xy"]), k * 4 if named_only else k)
    dist, ix = d["tree"].query(xy, k=kk, distance_upper_bound=max_m)
    out = []
    for dd, i in zip(np.atleast_1d(dist), np.atleast_1d(ix)):
        if not np.isfinite(dd) or (named_only and not d["name"][i]):
            continue
        rec = {"name": d["name"][i], "metres": int(round(dd)), "osm_url": OSM_URL + d["ref"][i]}
        if d["extra"][i]:
            rec["kind"] = d["extra"][i]
        out.append(rec)
        if len(out) == k:
            break
    return out


def _nearest_feature(idx, cat, xy, label, max_m=np.inf, **kw) -> dict:
    r = _nearest_pts(idx, cat, xy, 1, max_m, **kw)
    tags = TAG_DEFS.get(cat, f"shop in {sorted(ANCHOR_SHOPS)} with name or brand matching {label}")
    if not r:
        lim = f" within {int(max_m):,} m" if np.isfinite(max_m) else " in the indexed area"
        return _missing(idx, f"no {label} mapped in OpenStreetMap{lim}", osm_tags=tags)
    r = r[0]
    return _val(idx, r["metres"], "found", "straight-line metres to the mapped point (centroid for outlines)",
                name=r["name"], osm_url=r["osm_url"], osm_tags=tags, **({"kind": r["kind"]} if "kind" in r else {}))


def _nearest_line(idx, kind, xy, label) -> dict:
    d = idx["lines"].get(kind)
    if d is None:
        return _missing(idx, f"no {label} in the index", osm_tags=TAG_DEFS[kind])
    dist, i = d["tree"].query(xy)
    f = d["fid"][i]
    out = _val(idx, int(round(dist)), "found",
               "straight-line metres to the nearest point on the mapped line or outline (vertices at most 30 m apart)",
               name=d["name"][f], osm_url=OSM_URL + d["ref"][f], osm_tags=TAG_DEFS[kind])
    if d["kind"][f]:
        out["kind"] = d["kind"][f]
    if kind == "water" and not out["name"]:
        rl = idx["lines"].get("river_line")
        if rl is not None and out.get("kind") in ("river", "canal"):
            dd, j = rl["tree"].query(d["xy"][i], distance_upper_bound=1500.0)
            if np.isfinite(dd) and rl["name"][rl["fid"][j]]:
                out["name"] = rl["name"][rl["fid"][j]]
                out["name_method"] = "outline is unnamed; name taken from the nearest waterway=river centre line"
    return out


def _parks(idx, xy, radius) -> dict:
    import shapely
    p = idx["parks"]
    pt = shapely.Point(xy)
    out = {}
    for key, tree, sub in (("nearest_park", p["tree_big"], p["big"]), ("nearest_named_park", p["tree_named"], p["named"])):
        j, dist = tree.query_nearest(pt, return_distance=True, all_matches=False)
        if not len(j):
            out[key] = _missing(idx, "no park of 0.5 ha or more in the index", osm_tags=TAG_DEFS["park"])
            continue
        i, m = int(sub[j[0]]), float(dist[0])
        out[key] = _val(idx, int(round(m)), "found",
                        "straight-line metres to the park outline (0 = the point is inside it); parks under 0.5 ha ignored",
                        name=p["name"][i], kind=p["kind"][i], area_ha=round(float(p["area_m2"][i]) / 1e4, 1),
                        osm_url=OSM_URL + p["ref"][i], osm_tags=TAG_DEFS["park"])
        out[key + "_walk_min"] = _val(idx, _walk_min(m), "estimate",
                                      f"straight-line metres x {WALK_DETOUR} detour / {WALK_M_PER_MIN:.0f} m per minute")
    buf = pt.buffer(radius, 32)
    hits = p["tree_all"].query(buf, predicate="intersects")
    area = shapely.union_all(shapely.intersection(p["geom"][hits], buf)).area if len(hits) else 0.0
    out[f"park_area_ha_within_{int(radius)}m"] = _val(
        idx, round(area / 1e4, 2), "found",
        f"area of mapped parks, nature reserves and beaches (any size, overlaps counted once) inside a {int(radius)} m circle",
        share_of_circle=round(area / buf.area, 3), osm_tags=TAG_DEFS["park"])
    return out


def _building(idx, xy) -> dict:
    import shapely
    z, b = idx["bldz"], idx["bld"]
    px, py = xy[0] - X0, xy[1] - Y0
    cx, cy = int(math.floor(px / CELL)), int(math.floor(py / CELL))
    cand = [np.asarray(z["huge"])]
    cs = z["cell_sorted"]
    for dx in range(-2, 3):
        lo = (cx + dx + 100000) * 1000000 + (cy - 2 + 100000)
        a, e = np.searchsorted(cs, lo, side="left"), np.searchsorted(cs, lo + 4, side="right")
        cand.append(np.asarray(z["order"][a:e]))
    cand = np.sort(np.concatenate(cand))
    if not len(cand):
        return {"building": _missing(idx, "no building outline mapped within 500 m", osm_tags=TAG_DEFS["building"])}
    cen, rad = z["cen"][cand], z["rad"][cand]
    near_ = cand[np.hypot(cen[:, 0] - px, cen[:, 1] - py) <= rad + 40.0]
    best, best_d = None, 1e9
    pt = shapely.Point(px, py)
    for r in near_:
        ring = np.asarray(z["coords"][z["start"][r]:z["start"][r + 1]], dtype=np.float64)
        if len(ring) < 4:
            continue
        dd = shapely.Polygon(ring).distance(pt)
        if dd < best_d:
            best, best_d = int(r), dd
            if dd == 0:
                break
    if best is None or best_d > 40.0:
        return {"building": _missing(idx, "no building outline mapped within 40 m of the point",
                                     osm_tags=TAG_DEFS["building"])}
    bi = int(z["ring_bld"][best])
    inside = best_d == 0
    vt = "found" if inside else "estimate"
    how = "the point is inside this building outline" if inside else \
        f"the point is not inside any outline; nearest outline is {best_d:.0f} m away (geocoded points often sit at the kerb)"
    url = OSM_URL + b["ref"][bi]
    btype = str(b["types"][int(z["tcode"][bi])])
    lev, h = float(z["levels"][bi]), float(z["height"][bi])
    out = {
        "building": _val(idx, url, vt, how, metres_from_point=int(round(best_d)), name=b["names"].get(bi),
                         osm_tags=TAG_DEFS["building"]),
        "building_type": _val(idx, btype, vt, how, osm_tags="building=*", osm_url=url,
                              note="'yes' means a building with no type recorded" if btype == "yes" else None),
        "building_levels": _val(idx, int(lev) if lev == int(lev) else lev, vt, how, osm_tags="building:levels",
                                osm_url=url) if np.isfinite(lev) else
        _missing(idx, "building:levels is not tagged on this building", osm_url=url),
        "building_height_m": _val(idx, round(h, 1), vt, how, osm_tags="height", osm_url=url) if np.isfinite(h) else
        _missing(idx, "height is not tagged on this building", osm_url=url),
    }
    if bi in b["flats"]:
        out["building_flats"] = _val(idx, b["flats"][bi], vt, how, osm_tags="building:flats", osm_url=url)
    return out


def _lamps(idx, xy) -> dict:
    d = idx["pts"].get("lamp")
    n150 = len(d["tree"].query_ball_point(xy, LAMP_RADIUS_M)) if d else 0
    ncov = len(d["tree"].query_ball_point(xy, LAMP_COVERAGE_RADIUS_M)) if d else 0
    if ncov < LAMP_COVERAGE_MIN:
        return _missing(idx, f"street lamps are not mapped meaningfully here: {ncov} within "
                             f"{int(LAMP_COVERAGE_RADIUS_M)} m (threshold {LAMP_COVERAGE_MIN}); "
                             "an absence of mapped lamps says nothing about real lighting",
                        mapped_within_150m=n150, mapped_within_500m=ncov, osm_tags=TAG_DEFS["lamp"])
    return _val(idx, n150, "found",
                f"count of mapped lamps within {int(LAMP_RADIUS_M)} m; reported only because {ncov} lamps are mapped "
                f"within {int(LAMP_COVERAGE_RADIUS_M)} m. Mapping is still partial: compare only with caution",
                mapped_within_500m=ncov, osm_tags=TAG_DEFS["lamp"])


def _counts(idx, xy, radii) -> dict:
    out = {}
    for c in COUNT_CATS:
        for r in radii:
            out[f"{c}_count_{int(r)}m"] = _val(idx, _count(idx, c, xy, r), "found",
                                               f"mapped places within {int(r)} m straight-line", osm_tags=TAG_DEFS[c])
    return out


def _outside(idx, lat, lon) -> dict:
    return {"point": {"lat": lat, "lon": lon},
            "coverage": _missing(idx, f"point is outside the indexed box (west, south, east, north) "
                                      f"{idx['meta']['bbox_wsen']}")}


def near(lat: float, lon: float) -> dict:
    """Everything around one address. See the module docstring for the value format."""
    idx = _load()
    if not _in_coverage(idx, lat, lon):
        return _outside(idx, lat, lon)
    xy = np.array(idx["tr"].transform(lon, lat))
    names_m = "nearest named places within 1,600 m straight-line, nearest first"

    green = _parks(idx, xy, 800.0)
    green["nearest_dog_park"] = _nearest_feature(idx, "dog_park", xy, "dog park")

    out_ = _counts(idx, xy, (800.0, 1600.0))
    for c, plural in (("cafe", "cafes"), ("bakery", "bakeries"), ("bar", "bars")):
        lst = _nearest_pts(idx, c, xy, 5, 1600.0, named_only=True)
        out_[f"nearest_{plural}"] = _val(idx, lst, "found", names_m, osm_tags=TAG_DEFS[c]) if lst else \
            _missing(idx, f"no named {c} mapped within 1,600 m", osm_tags=TAG_DEFS[c])

    errands = {"nearest_supermarket": _nearest_feature(idx, "supermarket", xy, "supermarket"),
               "nearest_pharmacy": _nearest_feature(idx, "pharmacy", xy, "pharmacy"),
               "nearest_veterinary": _nearest_feature(idx, "vet", xy, "veterinary clinic")}
    for k, label in ANCHORS.items():
        errands[f"nearest_{k}"] = _nearest_feature(idx, k, xy, label, ANCHOR_RADIUS_M)

    walk_r = 800.0 / WALK_DETOUR
    wfh = {
        "cafes_within_800m_walk": _val(idx, _count(idx, "cafe", xy, walk_r), "estimate",
                                       f"cafes within {walk_r:.0f} m straight-line, which is an 800 m walk at a "
                                       f"{WALK_DETOUR} detour factor (about 10 minutes)", osm_tags=TAG_DEFS["cafe"]),
        "coworking_within_1600m": _val(idx, _count(idx, "coworking", xy, 1600.0), "found",
                                       "mapped places within 1,600 m straight-line",
                                       places=_nearest_pts(idx, "coworking", xy, 5, 1600.0),
                                       osm_tags=TAG_DEFS["coworking"]),
    }

    setting = {
        "coastline_m": _nearest_line(idx, "coastline", xy, "coastline"),
        "river_or_lake_shore_m": _nearest_line(idx, "water", xy, "river or lake"),
        "beach_m": _nearest_line(idx, "beach", xy, "beach"),
        "nearest_rail_station": _nearest_feature(idx, "station", xy, "rail station"),
        "motorway_m": _nearest_line(idx, "motorway", xy, "motorway"),
        "streetlamps_within_150m": _lamps(idx, xy),
    }
    cw, rw = setting["coastline_m"], setting["river_or_lake_shore_m"]
    if cw["value"] is not None and rw["value"] is not None:
        nw = cw if cw["value"] <= rw["value"] else rw
        setting["nearest_open_water_m"] = _val(
            idx, nw["value"], "found", "the smaller of coastline_m and river_or_lake_shore_m",
            name=nw.get("name"), kind=nw.get("kind") or "coastline", osm_url=nw.get("osm_url"))
    st = idx["pts"].get("station")
    if st is not None:  # nearest station that is not subway or light rail (commuter or intercity rail)
        dist, ix = st["tree"].query(xy, k=min(60, len(st["xy"])))
        for dd, i in zip(dist, ix):
            if st["extra"][i] == "train":
                setting["nearest_train_station"] = _val(
                    idx, int(round(dd)), "found", "nearest railway=station not tagged as subway or light rail",
                    name=st["name"][i], osm_url=OSM_URL + st["ref"][i], osm_tags=TAG_DEFS["station"])
                break
        else:
            setting["nearest_train_station"] = _missing(idx, "none among the 60 nearest stations")

    return {"point": {"lat": lat, "lon": lon}, "green_space": green, "going_out": out_, "errands": errands,
            "working_from_home": wfh, "setting": setting, "building": _building(idx, xy),
            "license": "(c) OpenStreetMap contributors, ODbL 1.0"}


def area_profile(lat: float, lon: float, radius_m: float = 1200) -> dict:
    """The same counts for a neighbourhood centre: everything mapped within radius_m straight-line."""
    idx = _load()
    if not _in_coverage(idx, lat, lon):
        return _outside(idx, lat, lon)
    xy = np.array(idx["tr"].transform(lon, lat))
    r = float(radius_m)
    km2 = math.pi * r * r / 1e6
    how = f"mapped places within {int(r)} m straight-line of the centre"
    counts = {}
    for c in COUNT_CATS + ["bakery", "supermarket", "pharmacy", "vet", "coworking", "dog_park", "station"]:
        n = _count(idx, c, xy, r)
        counts[f"{c}_count"] = _val(idx, n, "found", how, per_km2=round(n / km2, 1), osm_tags=TAG_DEFS[c])
    for k, label in ANCHORS.items():
        counts[f"{k}_count"] = _val(idx, _count(idx, k, xy, r), "found", how,
                                    osm_tags=f"shop in {sorted(ANCHOR_SHOPS)} with name or brand matching {label}")
    names = {}
    for c, plural in (("cafe", "cafes"), ("bakery", "bakeries"), ("bar", "bars"), ("restaurant", "restaurants"),
                      ("brewery", "breweries"), ("music", "music_venues")):
        lst = _nearest_pts(idx, c, xy, 5, r, named_only=True)
        names[f"nearest_{plural}"] = _val(idx, lst, "found", f"nearest named places within {int(r)} m, nearest first",
                                      osm_tags=TAG_DEFS[c]) if lst else \
            _missing(idx, f"no named {c} mapped within {int(r)} m", osm_tags=TAG_DEFS[c])
    green = _parks(idx, xy, r)
    setting = {"coastline_m": _nearest_line(idx, "coastline", xy, "coastline"),
               "river_or_lake_shore_m": _nearest_line(idx, "water", xy, "river or lake"),
               "beach_m": _nearest_line(idx, "beach", xy, "beach"),
               "nearest_rail_station": _nearest_feature(idx, "station", xy, "rail station"),
               "motorway_m": _nearest_line(idx, "motorway", xy, "motorway")}
    return {"point": {"lat": lat, "lon": lon}, "radius_m": r, "circle_km2": round(km2, 2), "counts": counts,
            "names": names, "green_space": green, "setting": setting,
            "license": "(c) OpenStreetMap contributors, ODbL 1.0"}


# ----------------------------------------------------------------------------------------------------------
# color(): the kind of life around a building (second index, built from the same regional cut)
# ----------------------------------------------------------------------------------------------------------

COLOR_FILTERED = BIG / "region_color.osm.pbf"
COLOR_INDEX = BIG / "color_index.pkl"
STREETS = {"residential", "living_street", "unclassified", "tertiary", "secondary", "primary", "trunk", "pedestrian"}
BIG_BOX_M2 = 5000.0
SEG_M = 25.0  # line features are cut into pieces no longer than this; lengths are summed over piece midpoints

COLOR_FILTER = [
    "nwr/leisure=fitness_centre,playground,pitch,sports_centre,garden", "nwr/sport",
    "nwr/amenity=gym,library,cinema,theatre,arts_centre,marketplace,fast_food,ice_cream,fuel,parking",
    "nwr/cuisine", "nwr/tourism=gallery,museum", "nwr/shop", "nwr/landuse=allotments,forest",
    "nwr/natural=wood", "w/natural=tree_row", "nwr/drive_through=yes", "wr/building=retail",
    "w/highway=footway,pedestrian,path,cycleway," + ",".join(sorted(STREETS)),
    "w/cycleway=lane,track", "w/cycleway:left=lane,track", "w/cycleway:right=lane,track",
    "w/cycleway:both=lane,track",
]

COLOR_DEFS = {
    "gym": "leisure=fitness_centre, or amenity=gym, or sport including yoga or pilates",
    "bookshop": "shop=books",
    "library": "amenity=library",
    "cinema_theatre": "amenity=cinema or amenity=theatre or amenity=arts_centre",
    "gallery_museum": "tourism=gallery or tourism=museum",
    "market": "amenity=marketplace",
    "playground": "leisure=playground",
    "pitch": "leisure=pitch or leisure=sports_centre (each mapped court or field counts once)",
    "tennis": "leisure=pitch or leisure=sports_centre with sport including tennis (each mapped court counts once)",
    "community_garden": "leisure=garden with garden:type=community, or landuse=allotments",
    "fast_food": "amenity=fast_food",
    "diner_ice_cream": "amenity=ice_cream, or cuisine including diner",
    "pet": "shop=pet or shop=pet_grooming",
    "vet": TAG_DEFS["vet"],
    "hair_beauty": "shop=hairdresser or shop=beauty",
    "shop_any": "shop=* (any value except no/vacant)",
    "convenience": "shop=convenience",
    "laundry": "shop=laundry",
    "fuel": "amenity=fuel",
    "drive_through": "drive_through=yes on any place",
    "big_box": f"shop=department_store, wholesale or doityourself; or shop=mall or building=retail with an outline "
               f"over {BIG_BOX_M2:,.0f} m2",
    "parking": "amenity=parking mapped as an area, excluding parking=underground, multi-storey, rooftop, "
               "street_side and lane",
    "wood": "natural=wood or landuse=forest areas",
    "tree_row": "natural=tree_row (ways)",
    "footway": "highway=footway, highway=pedestrian or highway=path (ways; includes separately mapped sidewalks "
               "and crossings)",
    "cycleway": "highway=cycleway (ways)",
    "bike_lane": "streets with cycleway, cycleway:left, cycleway:right or cycleway:both = lane or track",
    "intersection": "nodes where 3 or more street segments meet; streets = highway in " + ", ".join(sorted(STREETS)),
}
COLOR_GROUPS = {
    "culture": ["bookshop", "library", "cinema_theatre", "gallery_museum"],
    "fitness_and_play": ["gym", "playground", "pitch", "tennis", "community_garden"],
    "food": ["market", "fast_food", "diner_ice_cream"],
    "pets": ["pet", "vet"],
    "main_street": ["hair_beauty", "shop_any", "convenience", "laundry"],
    "car_oriented": ["fuel", "drive_through", "big_box"],
}


def _color_cats(t: dict) -> list[str]:
    c = []
    a, s, l, sp = t.get("amenity"), t.get("shop"), t.get("leisure"), t.get("sport") or ""
    sports = {x.strip() for x in sp.split(";")}
    if l == "fitness_centre" or a == "gym" or sports & {"yoga", "pilates"}:
        c.append("gym")
    if l in ("pitch", "sports_centre"):
        c.append("pitch")
        if "tennis" in sports:
            c.append("tennis")
    elif l == "playground":
        c.append("playground")
    if (l == "garden" and t.get("garden:type") == "community") or t.get("landuse") == "allotments":
        c.append("community_garden")
    if a == "library":
        c.append("library")
    elif a in ("cinema", "theatre", "arts_centre"):
        c.append("cinema_theatre")
    elif a == "marketplace":
        c.append("market")
    elif a == "fast_food":
        c.append("fast_food")
    elif a == "fuel":
        c.append("fuel")
    if t.get("tourism") in ("gallery", "museum"):
        c.append("gallery_museum")
    if a == "ice_cream" or "diner" in {x.strip() for x in (t.get("cuisine") or "").split(";")}:
        c.append("diner_ice_cream")
    if s and s not in ("no", "vacant"):
        c.append("shop_any")
        if s == "books":
            c.append("bookshop")
        elif s in ("pet", "pet_grooming"):
            c.append("pet")
        elif s in ("hairdresser", "beauty"):
            c.append("hair_beauty")
        elif s == "convenience":
            c.append("convenience")
        elif s == "laundry":
            c.append("laundry")
        elif s in ("department_store", "wholesale", "doityourself"):
            c.append("big_box")
    if t.get("drive_through") == "yes":
        c.append("drive_through")
    return c


def build_color_index() -> None:
    import osmium
    import pyproj
    import shapely
    from scipy.spatial import cKDTree

    files = fetch_region()
    if not COLOR_FILTERED.exists():
        tmp = BIG / "region_color.tmp.osm.pbf"
        _osmium("tags-filter", "-O", "-o", str(tmp), str(REGION), *COLOR_FILTER)
        tmp.rename(COLOR_FILTERED)
    tr = pyproj.Transformer.from_crs(4326, 32618, always_xy=True)

    def proj(geoms):
        return shapely.transform(geoms, lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))

    wkbf = osmium.geom.WKBFactory()
    pts = defaultdict(lambda: {"lon": [], "lat": [], "name": [], "ref": []})
    area_pts, bigbox_cand = [], []
    polys = {"parking": [], "wood": []}
    line_kinds = ["footway", "cycleway", "bike_lane", "tree_row"]
    l_lon, l_lat, l_n, l_kind = [], [], [], []
    s_ref, s_lon, s_lat, s_n = [], [], [], []
    bad = 0
    t0 = time.time()
    for o in osmium.FileProcessor(str(COLOR_FILTERED)).with_areas():
        tags = o.tags
        if o.is_node():
            if not len(tags):
                continue
            t = {x.k: x.v for x in tags}
            for c in _color_cats(t):
                d = pts[c]
                d["lon"].append(o.location.lon); d["lat"].append(o.location.lat)
                d["name"].append(t.get("name")); d["ref"].append(f"node/{o.id}")
        elif o.is_way():
            hw = tags.get("highway")
            kinds = []
            if hw in ("footway", "pedestrian", "path"):
                kinds.append(0)
            elif hw == "cycleway":
                kinds.append(1)
            if hw != "cycleway" and any(tags.get(k) in ("lane", "track") for k in
                                        ("cycleway", "cycleway:left", "cycleway:right", "cycleway:both")):
                kinds.append(2)
            if tags.get("natural") == "tree_row":
                kinds.append(3)
            street = hw in STREETS
            if not kinds and not street:
                continue
            try:
                lon = [n.lon for n in o.nodes]
                lat = [n.lat for n in o.nodes]
            except Exception:
                bad += 1
                continue
            if len(lon) < 2:
                continue
            for k in kinds:
                l_lon.append(lon); l_lat.append(lat); l_n.append(len(lon)); l_kind.append(k)
            if street:
                s_ref.append([n.ref for n in o.nodes]); s_lon.append(lon); s_lat.append(lat); s_n.append(len(lon))
        elif o.is_area():
            t = {x.k: x.v for x in tags}
            cats = _color_cats(t)
            is_parking = t.get("amenity") == "parking" and t.get("parking") not in (
                "underground", "multi-storey", "rooftop", "street_side", "lane")
            is_wood = t.get("natural") == "wood" or t.get("landuse") == "forest"
            cand = "big_box" not in cats and (t.get("shop") == "mall" or t.get("building") == "retail")
            if not (cats or is_parking or is_wood or cand):
                continue
            ref = f"{'way' if o.from_way() else 'relation'}/{o.orig_id()}"
            try:
                w = wkbf.create_multipolygon(o)
            except Exception:
                bad += 1
                continue
            if cats:
                area_pts.append((w, cats, t.get("name"), ref))
            if cand:
                bigbox_cand.append((w, t.get("name"), ref))
            if is_parking:
                polys["parking"].append(w)
            if is_wood:
                polys["wood"].append(w)
    print(f"color read done in {time.time() - t0:.0f}s; invalid skipped: {bad}", flush=True)

    recs = [(a[0], a[1], a[2], a[3]) for a in area_pts]
    if bigbox_cand:
        g = proj(shapely.from_wkb(np.array([b[0] for b in bigbox_cand], dtype=object)))
        for (w, name, ref), ar in zip(bigbox_cand, shapely.area(g)):
            if ar >= BIG_BOX_M2:
                recs.append((w, ["big_box"], name, ref))
    cen = shapely.centroid(shapely.from_wkb(np.array([r[0] for r in recs], dtype=object)))
    for (w, cats, name, ref), lon, lat in zip(recs, shapely.get_x(cen), shapely.get_y(cen)):
        for c in cats:
            d = pts[c]
            d["lon"].append(lon); d["lat"].append(lat); d["name"].append(name); d["ref"].append(ref)
    out_pts = {}
    for c, d in pts.items():
        x, y = tr.transform(np.array(d["lon"]), np.array(d["lat"]))
        xy = np.column_stack([x, y])
        keep = np.ones(len(xy), bool)
        names = [_norm(nm) for nm in d["name"]]
        for i, j in sorted(cKDTree(xy).query_pairs(60.0)):
            if keep[i] and keep[j] and names[i] and names[i] == names[j]:
                keep[j] = False
        ix = np.flatnonzero(keep)
        out_pts[c] = {"xy": xy[ix], "tree": cKDTree(xy[ix]), "name": [d["name"][i] for i in ix],
                      "ref": [d["ref"][i] for i in ix], "extra": [None] * len(ix)}

    # ---- lines: pieces of at most SEG_M, stored as midpoint + length ---------------------------------------
    def flat(lists):
        return np.fromiter((v for l in lists for v in l), dtype=np.float64)

    n = np.array(l_n)
    x, y = tr.transform(flat(l_lon), flat(l_lat))
    way = np.repeat(np.arange(len(n)), n)
    same = way[1:] == way[:-1]
    x0, y0, x1, y1 = x[:-1][same], y[:-1][same], x[1:][same], y[1:][same]
    kind = np.array(l_kind)[way[:-1][same]]
    ln = np.hypot(x1 - x0, y1 - y0)
    k = np.maximum(1, np.ceil(ln / SEG_M).astype(int))
    rep = np.repeat(np.arange(len(ln)), k)
    j = np.arange(len(rep)) - np.repeat(np.cumsum(k) - k, k)
    f = (j + 0.5) / k[rep]
    mx, my = x0[rep] + f * (x1 - x0)[rep], y0[rep] + f * (y1 - y0)[rep]
    piece, pk = (ln / k)[rep], kind[rep]
    out_lines = {}
    for code, nm in enumerate(line_kinds):
        m = pk == code
        xy = np.column_stack([mx[m], my[m]])
        out_lines[nm] = {"tree": cKDTree(xy), "len": piece[m].astype(np.float32), "total_km": float(piece[m].sum() / 1000)}

    # ---- intersections: nodes where 3+ street segments meet -------------------------------------------------
    sn = np.array(s_n)
    refs = np.fromiter((v for l in s_ref for v in l), dtype=np.int64)
    sx, sy = tr.transform(flat(s_lon), flat(s_lat))
    ends = np.zeros(len(refs), bool)
    st = np.cumsum(sn) - sn
    ends[st] = True; ends[st + sn - 1] = True
    u, first, inv = np.unique(refs, return_index=True, return_inverse=True)
    deg = np.bincount(inv, weights=np.where(ends, 1, 2))
    ii = first[deg >= 3]
    ixy = np.column_stack([sx[ii], sy[ii]])
    out_pts["intersection"] = {"xy": ixy, "tree": cKDTree(ixy)}

    # ---- polygons -----------------------------------------------------------------------------------------
    out_polys = {}
    for nm, lst in polys.items():
        g = shapely.make_valid(shapely.simplify(proj(shapely.from_wkb(np.array(lst, dtype=object))), 2.0))
        out_polys[nm] = {"geom": g, "total_ha": float(shapely.area(g).sum() / 1e4)}

    main = json.loads(META.read_text())
    meta = {"built_at": lib.now_iso(), "bbox_wsen": list(bbox()), "files": files,
            "source_url": main.get("source_url", files[0]["url"]),
            "osm_data_timestamp": min(f["osm_data_timestamp"] for f in files),
            "retrieved_at": max(f["retrieved_at"] for f in files),
            "counts": {**{c: len(v["xy"]) for c, v in out_pts.items()},
                       **{f"{k}_km": round(v["total_km"]) for k, v in out_lines.items()},
                       **{f"{k}_polygons": len(v["geom"]) for k, v in out_polys.items()},
                       **{f"{k}_ha": round(v["total_ha"]) for k, v in out_polys.items()}}}
    with open(COLOR_INDEX, "wb") as fh:
        pickle.dump({"meta": meta, "pts": out_pts, "lines": out_lines, "polys": out_polys}, fh,
                    protocol=pickle.HIGHEST_PROTOCOL)
    print(json.dumps(meta["counts"], indent=1))


_CIDX = None


def _load_color():
    global _CIDX
    if _CIDX is None:
        if not COLOR_INDEX.exists():
            build_color_index()
        import shapely
        with open(COLOR_INDEX, "rb") as f:
            c = pickle.load(f)
        for v in c["polys"].values():
            v["tree"] = shapely.STRtree(v["geom"])
        c["pts"]["vet"] = _load()["pts"]["vet"]
        c["tr"] = _load()["tr"]
        _CIDX = c
    return _CIDX


def _poly_area(c, kind, pt, radius) -> float:
    import shapely
    v = c["polys"][kind]
    buf = pt.buffer(radius, 32)
    hits = v["tree"].query(buf, predicate="intersects")
    return shapely.union_all(shapely.intersection(v["geom"][hits], buf)).area if len(hits) else 0.0


def color(lat: float, lon: float) -> dict:
    """The kind of life around a point: counts within 800 m and 1,600 m plus up to 3 nearest named examples per
    category, and car-oriented, street-pattern and tree-cover signals within 800 m. Same value format as near()."""
    import shapely
    c = _load_color()
    if not _in_coverage(c, lat, lon):
        return _outside(c, lat, lon)
    xy = np.array(c["tr"].transform(lon, lat))
    out = {"point": {"lat": lat, "lon": lon}}
    for group, cats in COLOR_GROUPS.items():
        g = out[group] = {}
        for cat in cats:
            for r in (800.0, 1600.0):
                g[f"{cat}_count_{int(r)}m"] = _val(c, _count(c, cat, xy, r), "found",
                                                   f"mapped places within {int(r)} m straight-line",
                                                   osm_tags=COLOR_DEFS[cat])
            if cat == "shop_any":
                continue
            ex = _nearest_pts(c, cat, xy, 3, 1600.0, named_only=True)
            g[f"{cat}_examples"] = _val(c, ex, "found", "up to 3 nearest named places within 1,600 m, nearest first",
                                        osm_tags=COLOR_DEFS[cat]) if ex else \
                _missing(c, "no named place of this kind mapped within 1,600 m", osm_tags=COLOR_DEFS[cat])
    pt = shapely.Point(xy)
    circle_ha = math.pi * 800.0 ** 2 / 1e4
    pa = _poly_area(c, "parking", pt, 800.0) / 1e4
    out["car_oriented"]["surface_parking_ha_within_800m"] = _val(
        c, round(pa, 2), "found", "area of mapped parking outlines inside an 800 m circle, overlaps counted once",
        share_of_circle=round(pa / circle_ha, 3), osm_tags=COLOR_DEFS["parking"])
    sp = out["street_pattern"] = {}
    n_int = _count(c, "intersection", xy, 800.0)
    sp["intersections_within_800m"] = _val(c, n_int, "found", "count of street nodes with 3 or more legs within 800 m",
                                           per_km2=round(n_int / (circle_ha / 100), 1),
                                           osm_tags=COLOR_DEFS["intersection"])
    for kind, key in (("footway", "footway_km_within_800m"), ("cycleway", "cycleway_km_within_800m"),
                      ("bike_lane", "bike_lane_street_km_within_800m"), ("tree_row", "tree_row_km_within_800m")):
        d = c["lines"][kind]
        ix = d["tree"].query_ball_point(xy, 800.0)
        km = float(d["len"][ix].sum()) / 1000 if ix else 0.0
        tgt = out.setdefault("trees", {}) if kind == "tree_row" else sp
        tgt[key] = _val(c, round(km, 2), "estimate",
                        f"mapped ways cut into pieces of at most {SEG_M:.0f} m; lengths of pieces whose midpoint is "
                        "within 800 m are summed", osm_tags=COLOR_DEFS[kind])
    wa = _poly_area(c, "wood", pt, 800.0) / 1e4
    out["trees"]["woods_ha_within_800m"] = _val(
        c, round(wa, 2), "found", "area of mapped wood and forest outlines inside an 800 m circle, overlaps counted once",
        share_of_circle=round(wa / circle_ha, 3), osm_tags=COLOR_DEFS["wood"])
    out["license"] = "(c) OpenStreetMap contributors, ODbL 1.0"
    return out


# ----------------------------------------------------------------------------------------------------------

TEST_POINTS = [("Jamaica station", 40.699608, -73.808530), ("Forest Hills", 40.7196, -73.8448),
               ("Long Beach NY", 40.5890, -73.6649), ("Stamford CT", 41.0469, -73.5419),
               ("Jersey City Grove St", 40.7196, -74.0431), ("Beacon NY", 41.5060, -73.9845)]


def _short(d, depth=0):
    """Compact print: value plus name/kind, without the repeated provenance."""
    for k, v in d.items():
        if isinstance(v, dict) and "value_type" in v:
            bits = [repr(v["value"]) if not isinstance(v["value"], list) else
                    "; ".join(f"{x['name']} ({x['metres']} m)" for x in v["value"])]
            for kk in ("name", "kind", "area_ha", "per_km2", "metres_from_point"):
                if v.get(kk) is not None:
                    bits.append(f"{kk}={v[kk]}")
            if v["value_type"] != "found":
                bits.append(f"[{v['value_type']}{': ' + v['reason'] if v.get('reason') else ''}]")
            print("  " * depth + f"{k}: " + " | ".join(bits))
        elif isinstance(v, dict):
            print("  " * depth + f"{k}:")
            _short(v, depth + 1)
        else:
            print("  " * depth + f"{k}: {v}")


if __name__ == "__main__":
    if "--build" in sys.argv:
        build_index()
        build_color_index()
        sys.exit()
    if "--build-color" in sys.argv:
        build_color_index()
        sys.exit()
    t = time.time()
    ix_ = _load()
    print(f"index loaded in {time.time() - t:.1f}s; OSM data as of {ix_['meta']['osm_data_timestamp']}, "
          f"from {ix_['meta']['source_url']}")
    for nm_, la_, lo_ in TEST_POINTS:
        t = time.time()
        res = near(la_, lo_)
        dt = time.time() - t
        t = time.time()
        prof = area_profile(la_, lo_)
        print(f"\n=== {nm_}: near() {dt * 1000:.0f} ms, area_profile() {(time.time() - t) * 1000:.0f} ms ===")
        if "--json" in sys.argv:
            print(json.dumps({"near": res, "area_profile": prof}, indent=1, default=str))
        else:
            _short(res)
            print("-- area_profile(radius 1200) counts --")
            _short(prof["counts"], 1)
            _short({k: v for k, v in prof["green_space"].items() if k.startswith("park_area")}, 1)
        t = time.time()
        col = color(la_, lo_)
        print(f"-- color() {(time.time() - t) * 1000:.0f} ms --")
        if "--json" in sys.argv:
            print(json.dumps(col, indent=1, default=str))
        else:
            _short({k: v for k, v in col.items() if k not in ("point", "license")}, 1)
