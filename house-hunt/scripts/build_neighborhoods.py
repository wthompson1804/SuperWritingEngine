"""Assign each passing building to a neighborhood, profile neighborhoods, and propose year groupings.

Neighborhood = NYC 2020 Neighborhood Tabulation Area (NYC Open Data 9nt8-h7nd) inside the city, else the Census
incorporated place, else county subdivision (Census geocoder). Traits are medians over passing units/buildings.
Clustering: standardized traits -> agglomerative (Ward) into k=5 and k=6; silhouette decides. Cluster names are NOT
assigned here; the script prints each cluster's distinguishing traits so names can be written from them.
Outputs: data/neighborhoods.csv, docs/CHECKPOINT_A.md
"""
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
from shapely.geometry import Point, shape
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT, get_json
from build_areas import census_geo, first
import parsers

MIN_UNITS = 3


def nta_polys():
    js, _ = get_json("https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson", "nyc_open_data", params={"$limit": 400}, timeout=120)
    return [(f["properties"].get("ntaname"), f["properties"].get("boroname"), shape(f["geometry"])) for f in js["features"]]


# Cities split into their neighborhoods (docs/SUBCITY_SPLIT_PLAN.md). Jersey City only: Newark's wards are prepared in
# the same file but not adopted (44 of its 45 ranked units are in one ward, and ward names are not how people describe it).
SUBCITY_ADOPT = {"Jersey City"}
SUBCITY_FILE = DATA / "reference" / "subcity_neighborhoods.geojson"
SUBCITY_OVERRIDES = DATA / "reference" / "subcity_overrides.csv"


def subcity_features(path=None):
    f = Path(path) if path else SUBCITY_FILE
    if not f.exists():
        return []
    return [ft for ft in json.loads(f.read_text())["features"] if ft["properties"]["city"] in SUBCITY_ADOPT]


def subcity_polys(path=None):
    """(city, state, hood_label, polygon) for every neighborhood of an adopted city."""
    return [(p["city"], p["state"], p["hood_label"], shape(ft["geometry"])) for ft in subcity_features(path) for p in [ft["properties"]]]


def subcity_parents(path=None):
    """child hood_id -> {"parent_id", "parent_name", "name", "label"} for the adopted cities. Content keyed on the parent
    (citywide quotes, survey rows, local rules, scene text) falls back to it, labelled as about the city as a whole."""
    return {p["hood_id"]: {"parent_id": p["parent_hood_id"], "parent_name": p["city"], "name": p["hood_name"], "label": p["hood_label"]}
            for ft in subcity_features(path) for p in [ft["properties"]]}


def subcity_overrides(path=None):
    """Hand decisions for buildings on a boundary whose polygon label a resident would dispute: addr_key or building_id
    -> hood_label. Each row carries its reason (data/reference/subcity_overrides.csv)."""
    f = Path(path) if path else SUBCITY_OVERRIDES
    if not f.exists():
        return {}
    O = pd.read_csv(f, dtype=str, keep_default_na=False)
    out = {}
    for r in O.itertuples():
        for k in (r.addr_key, r.building_id):
            if k:
                out[k] = r.hood_label
    return out


def subcity_name(name, state, lat, lon, subs, overrides=None, keys=()):
    """The neighborhood label inside a split city, or `name` unchanged elsewhere. An override wins; otherwise the
    polygon that contains the point, or the nearest polygon of that city when the point is just outside all of them."""
    mine = [(lab, poly) for c, st, lab, poly in subs if c == name and st == state]
    if not mine:
        return name
    for k in keys:
        if overrides and k in overrides:
            return overrides[k]
    p = Point(lon, lat)
    hit = [lab for lab, poly in mine if poly.contains(p)]
    return hit[0] if hit else min((poly.distance(p), lab) for lab, poly in mine)[1]


def _letters(t):
    return re.sub(r"[^a-z]", "", str(t).lower())


def route_to_children(hood_id, source_area="", parents=None):
    """Where content keyed on `hood_id` belongs once a city is split: [(target hood_id, about)].
    Not a split city's id: [(hood_id, None)]. A split city's id: the one child the source names ("Journal Square,
    Jersey City" -> Journal Square, about None), else every child, labelled "<City> as a whole"."""
    parents = subcity_parents() if parents is None else parents
    kids = [(c, v) for c, v in parents.items() if v["parent_id"] == hood_id]
    if not kids:
        return [(hood_id, None)]
    sa = _letters(source_area)
    named = [c for c, v in kids if _letters(v["name"]) in sa or (v["name"].lower().startswith("the ") and _letters(v["name"][4:]) in sa.replace(_letters(v["parent_name"]), ""))]
    if named:
        return [(c, None) for c in named]
    return [(c, f"{v['parent_name']} as a whole") for c, v in kids]


def hood_id_of(state, hood):
    return re.sub(r"[^a-z0-9:]+", "-", f"{state}:{hood}".lower())


def main():
    u = pd.read_csv(DATA / "units.csv", low_memory=False)
    u = u[u.unit_status == "pass"].copy()
    ntas = nta_polys()
    subs, overrides = subcity_polys(), subcity_overrides()
    hood, muni = {}, {}
    for key, g in u.groupby("addr_key"):
        lat, lon = float(g.lat.iloc[0]), float(g.lon.iloc[0])
        geo, _ = census_geo(lat, lon)
        county = first(geo, "Counties")
        if first(geo, "Incorporated Places") == "New York city":
            p = Point(lon, lat)
            hit = [(n, b) for n, b, poly in ntas if poly.contains(p)]
            name, area = (hit[0][0], hit[0][1]) if hit else ("New York city (unmatched)", "")
        else:
            # independent check 4, D25: "Milford city (balance)" is Milford (parsers.municipality_name cuts the legal suffix)
            name = first(geo, "Incorporated Places") or first(geo, "County Subdivisions")
            for suf in (" city", " village", " town", " borough", " township", " CDP"):
                name = name[:-len(suf)] if name.endswith(suf) else name
            # D17: the municipality comes from the geography at the building's point, never from a listing's mailing city
            # (independent check 4, D25: "Milford city (balance)" is Milford; the hood_id keeps its old spelling, a key of
            # the reviewed tables, and only the NAME is cleaned, below)
            muni[key] = parsers.municipality_name(first(geo, "Incorporated Places"), first(geo, "County Subdivisions"))
            # a split city: the neighborhood by point-in-polygon; hood_area stays the county (crime_benchmarks.py reads it)
            name = subcity_name(name, g.state.iloc[0], lat, lon, subs, overrides,
                                keys=(key,) + ((str(g.building_id.iloc[0]),) if "building_id" in g else ()))
            area = county
        hood[key] = (name, area, g.state.iloc[0])
    u["hood"] = u.addr_key.map(lambda k: hood[k][0]); u["hood_area"] = u.addr_key.map(lambda k: hood[k][1])
    u["hood_id"] = (u.state + ":" + u.hood).str.lower().str.replace(r"[^a-z0-9:]+", "-", regex=True)
    # D17 (Parkway Lofts, Avalon Maplewood "Newark", Third & Valley "East Orange", Avalon Wayne "Lincoln Park" ...): `city`
    # is the municipality the building stands in (Census place or county subdivision at its point); the city a listing
    # wrote (a mailing or market city) is kept in city_listed. Inside New York City the listed city (a borough or a
    # postal neighborhood name) stays: the neighborhood there is the NTA.
    u["hood"] = u.hood.map(lambda h: parsers.municipality_name(h) if str(h).endswith("(balance)") else h)
    u["city_listed"] = u.city
    m = u.addr_key.map(muni)
    u["city_basis"] = np.where(m.notna() & (m != ""), "census geography at the building's point", "as listed")
    u["city"] = m.where(m.notna() & (m != ""), u.city)
    ch = u[(u.city_basis != "as listed") & ~np.array([parsers.same_municipality(a, b) for a, b in zip(u.city, u.city_listed.fillna(""))], dtype=bool)].drop_duplicates("addr_key")
    ch[["addr_key", "building_name", "address", "city_listed", "city", "zip5", "hood_id"]].to_csv(DATA / "reference" / "municipality_changes.csv", index=False)
    print(f"municipality from geography differs from the listed city for {len(ch)} address keys (data/reference/municipality_changes.csv)")
    u.to_csv(DATA / "units.csv", index=False)

    def crime(row, k):
        try:
            return json.loads(row).get(k)
        except Exception:
            return np.nan
    u["violent_per_1000"] = u.crime_latest.map(lambda r: crime(r, "violent_per_1000"))
    u["mvt_per_1000"] = u.crime_latest.map(lambda r: crime(r, "motor_vehicle_theft_per_1000"))
    u["garage"] = u.parking_type.fillna("").str.contains("garage|covered|gated", case=False)
    u["bfloors"] = pd.to_numeric(u.building_floors, errors="coerce").fillna(pd.to_numeric(u.get("pluto_floors"), errors="coerce"))
    for c in ["drive_min_to", "transit_sat_median", "toll_rt_ezpass", "all_in", "sqft", "restaurants_800m", "bars_800m",
              "cafes_800m", "park_walk_min", "park_ha_800m", "coast_m", "beach_m", "open_water_m", "train_station_m", "lat", "lon"]:
        u[c] = pd.to_numeric(u[c], errors="coerce")
    u["toll_complete"] = u.toll_complete.astype(str).str.lower().eq("true").astype(float)
    g = u.groupby("hood_id")
    H = g.agg(hood=("hood", "first"), area=("hood_area", "first"), state=("state", "first"),
              units=("listing_id", "count"), buildings=("addr_key", "nunique"),
              drive_min=("drive_min_to", "median"), transit_min=("transit_sat_median", "median"),
              toll_rt=("toll_rt_ezpass", "median"), toll_known=("toll_complete", "mean"),
              all_in_med=("all_in", "median"), all_in_min=("all_in", "min"), sqft_med=("sqft", "median"),
              restaurants_800m=("restaurants_800m", "median"), bars_800m=("bars_800m", "median"),
              cafes_800m=("cafes_800m", "median"), park_walk_min=("park_walk_min", "median"),
              park_ha_800m=("park_ha_800m", "median"), coast_m=("coast_m", "median"), beach_m=("beach_m", "median"),
              water_m=("open_water_m", "median"), station_m=("train_station_m", "median"),
              bfloors=("bfloors", "median"), garage_share=("garage", "mean"),
              violent_per_1000=("violent_per_1000", "median"), mvt_per_1000=("mvt_per_1000", "median"),
              police=("police_agency", "first"), crime_source=("crime_source", "first"), crime_year=("crime_year", "first"),
              lat=("lat", "mean"), lon=("lon", "mean")).reset_index()
    H["qualifies"] = H.units >= MIN_UNITS
    Q = H[H.qualifies].copy()

    feats = ["drive_min", "all_in_med", "sqft_med", "restaurants_800m", "bars_800m", "park_ha_800m", "water_m",
             "bfloors", "violent_per_1000", "transit_min"]
    X = Q[feats].copy()
    for c in ("restaurants_800m", "bars_800m", "park_ha_800m", "water_m"):
        X[c] = np.log1p(X[c])
    X = X.fillna(X.median())
    Z = ((X - X.mean()) / X.std(ddof=0).replace(0, 1)).fillna(0)
    from scipy.cluster.hierarchy import linkage, fcluster
    link = linkage(Z.values, "ward")

    def sil(lab):
        D = np.linalg.norm(Z.values[:, None] - Z.values[None], axis=2); s = []
        for i in range(len(lab)):
            same = lab == lab[i]
            if same.sum() < 2:
                s.append(0); continue
            a = D[i, same].sum() / (same.sum() - 1)
            b = min(D[i, lab == o].mean() for o in set(lab) if o != lab[i])
            s.append((b - a) / max(a, b))
        return float(np.mean(s))
    res = {k: fcluster(link, k, "maxclust") for k in (5, 6)} if len(Q) >= 6 else {}
    sils = {k: round(sil(v), 3) for k, v in res.items()}
    best = max(sils, key=sils.get) if sils else None
    if best:
        Q["cluster"] = res[best]
        H = H.merge(Q[["hood_id", "cluster"]], on="hood_id", how="left")
    H.sort_values(["qualifies", "drive_min"], ascending=[False, True]).to_csv(DATA / "neighborhoods.csv", index=False)

    md = ["# Checkpoint A: neighborhoods and proposed years", "",
          f"Passing units: {len(u)} in {u.addr_key.nunique()} buildings, across {len(H)} neighborhoods; "
          f"{len(Q)} neighborhoods have {MIN_UNITS}+ passing places.", "",
          f"Cluster quality (silhouette; higher is cleaner): {sils}. Using k={best}.", ""]
    show = ["hood", "area", "units", "buildings", "drive_min", "transit_min", "all_in_med", "sqft_med", "restaurants_800m",
            "bars_800m", "park_walk_min", "water_m", "bfloors", "violent_per_1000", "mvt_per_1000"]
    if best:
        zc = Z.assign(cluster=Q.cluster.values).groupby("cluster").mean()
        for c, grp in Q.groupby("cluster"):
            top = zc.loc[c].sort_values(key=abs, ascending=False).head(4)
            md += [f"## Group {c}: {len(grp)} neighborhoods, {int(grp.units.sum())} places", "",
                   "Distinguishing traits (standard deviations from the average): " +
                   ", ".join(f"{k} {v:+.1f}" for k, v in top.items()), "",
                   grp.sort_values("drive_min")[show].round(1).to_markdown(index=False), ""]
    md += ["## Neighborhoods with fewer than 3 passing places (not shown on the page)", "",
           H[~H.qualifies].sort_values("drive_min")[["hood", "area", "state", "units", "drive_min", "all_in_med"]].round(1).to_markdown(index=False)]
    (ROOT / "docs" / "CHECKPOINT_A.md").write_text("\n".join(md) + "\n")
    print("\n".join(md[:6]))


if __name__ == "__main__":
    main()
