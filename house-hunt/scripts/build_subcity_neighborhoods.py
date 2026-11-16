"""Prepare sub-city neighborhoods for cities that are one lump today (Jersey City, Newark). NEW FILES ONLY.

Nothing in the pipeline reads these outputs yet; docs/SUBCITY_SPLIT_PLAN.md says how to wire them in.
Reads (read-only): data/master_buildings.csv, data/ranked_units.csv, the cached ACS tract call for Hudson County
(raw/census_acs_api), the cached JC IMPACT incident bundle (raw/non_nyc_records), the regional OSM extract
(raw/big/osm/region.osm.pbf, only when the place-point cache is missing), TIGER place files (raw/big/crime/tiger).
Fetches (cached, www2.census.gov only, robots: no rules for us): TIGER 2024 tracts for NJ, 2020 voting districts
(VTD) for Hudson and Essex counties. One refusal ends the host: retries=1.

Method
  Jersey City: unit = 2020 census tract (so ACS populations and the lifestyle tract features line up).
    1. base   = the 2020 ward holding most of the tract's area (wards from Census 2020 VTD names, "ward A".."ward F").
    2. rename = ward -> customary area name, checked by which OSM place node falls in which ward (WARD_NAME / ANCHORS).
    3. refine = (a) Newport: the tracts numbered 77.xx (the 2010 tract 77, holding the OSM node "Newport");
                (b) McGinley Square: tracts whose internal point is within MCG_RADIUS_M of the OSM node "McGinley
                    Square" and that hold no other neighborhood's anchor node (three wards meet there);
                (c) tract 13: ward C on paper, but its nearest named place is "The Heights" (881 m) and no Journal
                    Square anchor is within 1.2 km -> The Heights. Listed in TRACT_OVERRIDES.
    4. dissolve tracts, clip to the city (TIGER 2024 place).
  Newark: the five 2020 wards themselves (dissolved VTDs). No tract step: there is no sub-city crime or other
    tract-keyed input for Newark that would need it.
Outputs
  data/reference/subcity_neighborhoods.geojson      polygons
  data/reference/subcity_tracts.csv                 Jersey City tract -> neighborhood crosswalk, with ACS population
  data/reference/subcity_assignment.csv             every master building in a split city -> neighborhood
  data/reference/subcity_counts.csv                 buildings and currently ranked / shown units per neighborhood
  data/reference/subcity_crime_jersey_city.csv      JC IMPACT incident counts per neighborhood + labelled estimates
"""
import json, re, subprocess, sys, tempfile
from datetime import date
from pathlib import Path
import geopandas as gpd, numpy as np, pandas as pd
from shapely.geometry import Point, mapping
from shapely.ops import unary_union
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, RAW, ROOT, cached_get, now_iso

SRC = "subcity_split"
REF = DATA / "reference"
UTM = 32618
NEAR_M = 150
MCG_RADIUS_M = 600
TRACT_URL = "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_34_tract.zip"
VTD_URL = "https://www2.census.gov/geo/tiger/TIGER2020PL/LAYER/VTD/2020/tl_2020_{fips}_vtd20.zip"
PLACE_ZIP = RAW / "big" / "crime" / "tiger" / "tl_2024_34_place.zip"
PLACE_URL = "https://www2.census.gov/geo/tiger/TIGER2024/PLACE/tl_2024_34_place.zip"
OSM_PBF = RAW / "big" / "osm" / "region.osm.pbf"
OSM_META = RAW / "big" / "osm" / "meta.json"
ACS_HUDSON = RAW / "census_acs_api" / "a9cffe855aa096b0.json"
JC_INCIDENTS = RAW / "non_nyc_records" / "jc_impact_incidents_extracted.json"

WARD_NAME = {"A": "Greenville", "B": "West Side", "C": "Journal Square", "D": "The Heights", "E": "Downtown", "F": "Bergen-Lafayette"}
# OSM place node -> the neighborhood it is evidence for. Used to check WARD_NAME and for the refinements.
ANCHORS = {"Greenville": "Greenville", "West Bergen": "West Side", "Journal Square": "Journal Square", "Bergen Square": "Journal Square",
           "Hilltop": "Journal Square", "Indian Square": "Journal Square", "Croxton": "Journal Square", "The Heights": "The Heights",
           "Downtown Jersey City": "Downtown", "Hamilton Park": "Downtown", "Colgate Center": "Downtown", "Communipaw": "Bergen-Lafayette",
           "Newport": "Newport", "McGinley Square": "McGinley Square"}
TRACT_OVERRIDES = {"13": ("The Heights", "ward C on paper; nearest OSM place node is The Heights and no Journal Square node is within 1.2 km; "
                                         "holds New York Ave (ZIP 07307, the Heights ZIP) and the foot of the cliff at Hoboken Ave (ZIP 07310)")}
ALSO = {  # smaller names a resident would file under each neighborhood; only names present as OSM nodes or in the brief
    "Downtown": "Paulus Hook (Colgate Center), Hamilton Park, Harsimus, Exchange Place, Liberty Harbor",
    "Newport": "", "The Heights": "", "Journal Square": "Bergen Square, Hilltop, India Square, Croxton, Marion",
    "McGinley Square": "Bergen Hill", "Bergen-Lafayette": "Communipaw, Liberty State Park", "West Side": "West Bergen, Lincoln Park, Droyers Point",
    "Greenville": "Caven Point"}
CITIES = {"Jersey City": dict(state="NJ", county="Hudson County", fips="34017", parent="nj:jersey-city"),
          "Newark": dict(state="NJ", county="Essex County", fips="34013", parent="nj:newark")}


def slug(state, label):
    """Exactly what scripts/build_neighborhoods.py line 45 does, so hood_id can be re-derived from the label."""
    return re.sub(r"[^a-z0-9:]+", "-", (state + ":" + label).lower())


def fetch(url):
    c, m = cached_get(url, SRC, ext="zip", retries=1, timeout=180)
    if m["status"] != 200:
        raise SystemExit(f"{url} -> HTTP {m['status']}; host ends for this session")
    return ROOT / m["path"], m


def osm_points():
    """Named place nodes inside the Jersey City box from the regional extract. Cached as a small JSON under raw/."""
    f = RAW / SRC / "jc_osm_place_nodes.json"
    if f.exists():
        return json.loads(f.read_text())
    with tempfile.TemporaryDirectory() as t:
        a, b, c = f"{t}/a.osm.pbf", f"{t}/b.osm.pbf", f"{t}/c.geojsonseq"
        subprocess.run(["osmium", "tags-filter", str(OSM_PBF), "n/place", "-o", a], check=True)
        subprocess.run(["osmium", "extract", "-b", "-74.125,40.66,-74.02,40.775", a, "-o", b], check=True)
        subprocess.run(["osmium", "export", b, "-f", "geojsonseq", "-a", "id", "-o", c], check=True)
        rows = []
        for line in open(c):
            ft = json.loads(line.strip("\x1e\n"))
            p = ft["properties"]
            if p.get("name"):
                rows.append({"osm_id": p["@id"], "place": p.get("place"), "name": p["name"],
                             "lat": ft["geometry"]["coordinates"][1], "lon": ft["geometry"]["coordinates"][0]})
    meta = json.loads(OSM_META.read_text())
    out = {"source_url": meta["source_url"], "osm_data_timestamp": meta["osm_data_timestamp"], "retrieved_at": meta["retrieved_at"],
           "license": "ODbL 1.0, (c) OpenStreetMap contributors", "nodes": rows}
    f.parent.mkdir(parents=True, exist_ok=True); f.write_text(json.dumps(out, indent=1))
    return out


def wards(fips, city):
    path, meta = fetch(VTD_URL.format(fips=fips))
    v = gpd.read_file(f"zip://{path}")
    v = v[v.NAME20.str.startswith(city + " ")].copy()
    v["ward"] = v.NAME20.str.extract(r"ward (\w+)")[0]
    return v.dissolve("ward")[["geometry"]].to_crs(UTM), meta


def jersey_city(city_poly):
    tpath, tmeta = fetch(TRACT_URL)
    t = gpd.read_file(f"zip://{tpath}"); t = t[t.COUNTYFP == "017"].to_crs(UTM)
    t = t[t.geometry.intersection(city_poly).area / t.geometry.area > 0.5].copy()
    W, vmeta = wards("34017", "Jersey City")
    for w in W.index:
        t["w" + w] = t.geometry.intersection(W.geometry[w]).area / t.geometry.area
    wc = ["w" + w for w in W.index]
    t["ward_2020"] = t[wc].idxmax(axis=1).str[1]; t["ward_share"] = t[wc].max(axis=1).round(3)
    osm = osm_points()
    P = gpd.GeoDataFrame(osm["nodes"], geometry=[Point(n["lon"], n["lat"]) for n in osm["nodes"]], crs=4326).to_crs(UTM)
    P = P[P.name.isin(ANCHORS)].copy(); P["evidence_for"] = P.name.map(ANCHORS)
    P["ward_2020"] = [next((w for w in W.index if W.geometry[w].contains(g)), "") for g in P.geometry]
    # check: every anchor of a ward-named neighborhood sits in that ward
    chk = P[P.evidence_for.isin(WARD_NAME.values())]
    bad = chk[chk.ward_2020.map(WARD_NAME) != chk.evidence_for]
    print("anchor/ward check:", "all agree" if bad.empty else bad[["name", "evidence_for", "ward_2020"]].to_dict("records"))
    ip = gpd.GeoSeries([Point(float(lo), float(la)) for la, lo in zip(t.INTPTLAT, t.INTPTLON)], crs=4326).to_crs(UTM)
    t["hood_name"] = t.ward_2020.map(WARD_NAME); t["rule"] = "ward majority"
    d_all = np.array([[c.distance(g) for g in P.geometry] for c in ip])
    t["nearest_osm_place"] = [P.name.iloc[i] for i in d_all.argmin(axis=1)]; t["nearest_osm_place_m"] = d_all.min(axis=1).round(0)
    mcg = P[P.name == "McGinley Square"].geometry.iloc[0]
    others = P[P.evidence_for != "McGinley Square"]
    t["mcginley_m"] = [round(c.distance(mcg)) for c in ip]
    holds_other = [any(g.contains(o) for o in others.geometry) for g in t.geometry]
    m = (t.mcginley_m <= MCG_RADIUS_M) & ~np.array(holds_other)
    t.loc[m, "hood_name"] = "McGinley Square"; t.loc[m, "rule"] = f"internal point within {MCG_RADIUS_M} m of OSM node McGinley Square"
    m = t.NAME.str.startswith("77.")
    t.loc[m, "hood_name"] = "Newport"; t.loc[m, "rule"] = "tracts 77.xx (2010 tract 77), which hold the OSM node Newport"
    for name, (hood, why) in TRACT_OVERRIDES.items():
        t.loc[t.NAME == name, ["hood_name", "rule"]] = [hood, "override: " + why]
    acs = json.loads(ACS_HUDSON.read_text()); A = pd.DataFrame(acs[1:], columns=acs[0])
    A["GEOID"] = A.state + A.county + A.tract
    t["pop_acs_2019_2023"] = t.GEOID.map(A.set_index("GEOID").B01003_001E.astype(float))
    return t, tmeta, vmeta, osm, P


def main():
    got = now_iso()
    places = gpd.read_file(f"zip://{PLACE_ZIP}").to_crs(UTM)
    place_meta = next(json.loads(l) for l in open(PLACE_ZIP.parent / "_index.jsonl") if "tl_2024_34_place" in l)
    feats, tract_rows = [], None

    # ---- Jersey City
    jc_poly = places[places.NAME == "Jersey City"].geometry.iloc[0]
    t, tmeta, vmeta, osm, P = jersey_city(jc_poly)
    src_jc = "derived from tracts + ward lines + OSM place points"
    url_jc = " ; ".join([tmeta["url"], vmeta["url"], osm["source_url"], PLACE_URL])
    for hood, g in t.groupby("hood_name"):
        geom = unary_union(list(g.geometry)).intersection(jc_poly).buffer(0)
        label = f"Jersey City – {hood}"
        feats.append(dict(city="Jersey City", state="NJ", hood_area="Hudson County", hood_name=hood, hood_label=label, hood_id=slug("NJ", label),
                          parent_hood_id="nj:jersey-city", also_known_as=ALSO.get(hood, ""), source=src_jc, source_url=url_jc,
                          retrieved_at=max(tmeta["retrieved_at"], vmeta["retrieved_at"]), osm_data_timestamp=osm["osm_data_timestamp"],
                          method="2020 census tracts grouped by 2020 ward majority, renamed and refined with OSM place nodes, dissolved, clipped to the city; see scripts/build_subcity_neighborhoods.py",
                          tracts=";".join(sorted(g.NAME, key=float)), n_tracts=len(g), pop_acs_2019_2023=int(g.pop_acs_2019_2023.sum()),
                          pop_source="ACS 2019-2023 5-year B01003_001E by tract, https://api.census.gov/data/2023/acs/acs5 (cached raw/census_acs_api/a9cffe855aa096b0.json)",
                          value_type="estimate", geometry=geom))
    tract_rows = t[["GEOID", "NAME", "ward_2020", "ward_share", "nearest_osm_place", "nearest_osm_place_m", "mcginley_m", "hood_name", "rule", "pop_acs_2019_2023", "ALAND"]].copy()
    tract_rows.insert(0, "city", "Jersey City")
    tract_rows["hood_id"] = tract_rows.hood_name.map(lambda h: slug("NJ", f"Jersey City – {h}"))
    tract_rows["weak_ward_majority"] = tract_rows.ward_share < 0.7
    tract_rows["source_url"] = url_jc; tract_rows["retrieved_at"] = got
    tract_rows.sort_values("NAME", key=lambda s: s.astype(float)).rename(columns={"GEOID": "tract_geoid", "NAME": "tract", "ALAND": "land_m2"}) \
        .to_csv(REF / "subcity_tracts.csv", index=False)

    # ---- Newark: the wards themselves
    nk_poly = places[places.NAME == "Newark"].geometry.iloc[0]
    NW, nmeta = wards("34013", "Newark")
    for w, geom in NW.geometry.items():
        label = f"Newark – {w} Ward"
        feats.append(dict(city="Newark", state="NJ", hood_area="Essex County", hood_name=f"{w} Ward", hood_label=label, hood_id=slug("NJ", label),
                          parent_hood_id="nj:newark", also_known_as="", source="official: 2020 ward lines (Census 2020 voting districts, dissolved by ward)",
                          source_url=nmeta["url"], retrieved_at=nmeta["retrieved_at"], osm_data_timestamp="",
                          method="2020 Census voting districts whose name starts 'Newark city ward <name>', dissolved by ward, clipped to the city",
                          tracts="", n_tracts=0, pop_acs_2019_2023=None, pop_source="", value_type="found", geometry=geom.intersection(nk_poly).buffer(0)))

    G = gpd.GeoDataFrame(feats, geometry="geometry", crs=UTM)
    assert G.hood_id.is_unique
    out = G.to_crs(4326)
    fc = {"type": "FeatureCollection", "name": "subcity_neighborhoods", "crs_note": "WGS84 lon/lat",
          "generated_at": got, "generator": "scripts/build_subcity_neighborhoods.py",
          "license_note": "Census TIGER: public domain. OSM place nodes: ODbL 1.0, (c) OpenStreetMap contributors.",
          "features": []}
    def rnd(o):
        return [rnd(x) for x in o] if isinstance(o[0], (list, tuple)) else [round(o[0], 6), round(o[1], 6)]
    for _, r in out.iterrows():
        gj = mapping(r.geometry); gj = {"type": gj["type"], "coordinates": rnd(gj["coordinates"])}
        props = {k: (None if isinstance(v, float) and np.isnan(v) else (int(v) if isinstance(v, (np.integer,)) else v)) for k, v in r.drop("geometry").items()}
        fc["features"].append({"type": "Feature", "properties": props, "geometry": gj})
    (REF / "subcity_neighborhoods.geojson").write_text(json.dumps(fc))

    # ---- assignment of every master building in a split city
    M = pd.read_csv(DATA / "master_buildings.csv", low_memory=False)
    M = M[M.hood_id.isin([c["parent"] for c in CITIES.values()])].copy()
    B = gpd.GeoDataFrame(M, geometry=gpd.points_from_xy(M.lon, M.lat), crs=4326).to_crs(UTM)
    JW, _ = wards("34017", "Jersey City")
    rows = []
    for _, b in B.iterrows():
        city = next(k for k, c in CITIES.items() if c["parent"] == b.hood_id)
        Gc = G[G.city == city]
        hit = Gc[Gc.contains(b.geometry)]
        if len(hit):
            h, method = hit.iloc[0], "point-in-polygon"
        else:
            h, method = Gc.loc[Gc.distance(b.geometry).idxmin()], "nearest polygon (point outside every polygon)"
        oth = Gc[Gc.hood_id != h.hood_id]; d = oth.distance(b.geometry)
        tr = t[t.contains(b.geometry)] if city == "Jersey City" else t.iloc[0:0]
        ward = next((w for w in JW.index if JW.geometry[w].contains(b.geometry)), "") if city == "Jersey City" else h.hood_name.replace(" Ward", "")
        notes = []
        if city == "Jersey City":
            if len(tr) and tr.ward_share.iloc[0] < 0.7:
                notes.append(f"tract {tr.NAME.iloc[0]} straddles wards (largest ward holds {tr.ward_share.iloc[0]:.0%})")
            if ward and WARD_NAME[ward] != h.hood_name:
                notes.append(f"point is in 2020 ward {ward} ({WARD_NAME[ward]}) but its tract is filed under {h.hood_name}")
            if len(tr) and tr.rule.iloc[0].startswith("override"):
                notes.append("tract assigned by a documented override")
        rows.append(dict(building_id=b.building_id, addr_keys=b.addr_keys, address=b.address, city=city, state=b.state, zip5=b.zip5,
                         lat=b.lat, lon=b.lon, coord_basis=b.coord_basis, current_hood_id=b.hood_id,
                         hood_id=h.hood_id, hood_name=h.hood_name, hood_label=h.hood_label, method=method,
                         tract=tr.NAME.iloc[0] if len(tr) else "", tract_geoid=tr.GEOID.iloc[0] if len(tr) else "", ward_2020=ward,
                         dist_to_other_hood_m=round(float(d.min())), nearest_other_hood_id=oth.loc[d.idxmin()].hood_id,
                         dist_to_own_edge_m=round(float(h.geometry.boundary.distance(b.geometry))),
                         near_boundary=bool(d.min() <= NEAR_M), review_note="; ".join(notes),
                         n_listed_units=b.n_listed_units, source_file="data/reference/subcity_neighborhoods.geojson", assigned_at=got))
    A = pd.DataFrame(rows).sort_values(["city", "hood_id", "address"])
    A.to_csv(REF / "subcity_assignment.csv", index=False)

    # ---- counts (buildings; currently ranked and shown units)
    R = pd.read_csv(DATA / "ranked_units.csv", low_memory=False, usecols=["listing_id", "building_id", "hood_id", "shown", "avoid_card", "held_for_confirmation", "group_label"])
    R = R.merge(A[["building_id", "hood_id"]].rename(columns={"hood_id": "new_hood_id"}), on="building_id", how="inner")
    tf = lambda s: s.astype(str).str.lower().eq("true")
    C = A.groupby(["city", "hood_id", "hood_name"]).agg(buildings=("building_id", "count"), buildings_near_boundary=("near_boundary", "sum"),
                                                        buildings_with_review_note=("review_note", lambda s: int((s != "").sum()))).reset_index()
    rc = R.groupby("new_hood_id").agg(ranked_units=("listing_id", "count"), ranked_buildings=("building_id", "nunique"), shown_now=("shown", lambda s: int(tf(s).sum())),
                                      avoid_cards_now=("avoid_card", lambda s: int(tf(s).sum())), held_now=("held_for_confirmation", lambda s: int(tf(s).sum())),
                                      current_year=("group_label", "first"))
    C = C.join(rc, on="hood_id").fillna({"ranked_units": 0, "ranked_buildings": 0, "shown_now": 0, "avoid_cards_now": 0, "held_now": 0})
    C["shown_if_split_upper_bound"] = C.ranked_units.clip(upper=10).astype(int)
    C["as_of"] = got
    C.to_csv(REF / "subcity_counts.csv", index=False)

    # ---- Jersey City incident counts per neighborhood (JC IMPACT bundle already cached by scripts/non_nyc_records.py)
    d = json.loads(JC_INCIDENTS.read_text()); inc = pd.DataFrame(d["incidents"])
    lo, hi = inc.date.min(), inc.date.max()
    days = (date.fromisoformat(hi) - date.fromisoformat(lo)).days + 1
    I = gpd.GeoDataFrame(inc, geometry=gpd.points_from_xy(inc.lng, inc.lat), crs=4326).to_crs(UTM)
    Gj = G[G.city == "Jersey City"][["hood_id", "hood_name", "pop_acs_2019_2023", "geometry"]]
    J = gpd.sjoin(I, Gj, how="left", predicate="within")
    J = J[~J.index.duplicated()]
    J["hood_id"] = J.hood_id.fillna("(outside every polygon)")
    VIOL = ["Homicide", "Rape", "Robbery", "Aggravated Assault"]
    PROP = ["Burglary", "Theft", "Theft from Auto", "Shoplifting", "Stolen Vehicle"]
    T = J.pivot_table(index="hood_id", columns="type", values="id", aggfunc="count", fill_value=0)
    T["violent_4_types"] = T[VIOL].sum(axis=1); T["property_5_types"] = T[PROP].sum(axis=1)
    T["all_incidents"] = J.groupby("hood_id").size()
    T = T.join(Gj.set_index("hood_id")[["hood_name", "pop_acs_2019_2023"]])
    city = T[T.index != "(outside every polygon)"]
    tot = dict(v=city.violent_4_types.sum(), p=city.property_5_types.sum(), pop=city.pop_acs_2019_2023.sum())
    fbi = pd.read_csv(REF / "crime_agencies.csv"); fbi = fbi[(fbi.ori == "NJ0090600")].sort_values("year").iloc[-1]
    ann = 365 / days
    for k, col, f in (("violent", "violent_4_types", fbi.violent_per_1000), ("property", "property_5_types", fbi.property_per_1000)):
        T[f"{k}_per_1000_residents_annualised_portal"] = (T[col] * ann / T.pop_acs_2019_2023 * 1000).round(2)
        cw = tot["v" if k == "violent" else "p"] * ann / tot["pop"] * 1000
        T[f"{k}_ratio_to_city_portal"] = (T[f"{k}_per_1000_residents_annualised_portal"] / cw).round(2)
        T[f"{k}_per_1000_scaled_to_fbi_{int(fbi.year)}"] = (T[f"{k}_ratio_to_city_portal"] * f).round(2)
        T[f"city_{k}_per_1000_portal"] = round(cw, 2); T[f"city_{k}_per_1000_fbi_{int(fbi.year)}"] = f
    T["window"] = f"{lo} to {hi} ({days} days)"; T["value_type"] = "estimate"
    T["method"] = ("JC IMPACT block-geocoded incident points counted inside each neighborhood polygon; annualised by 365/days; divided by ACS 2019-2023 "
                   "resident population of the neighborhood's tracts; 'scaled_to_fbi' = ratio to the citywide portal rate x the FBI agency rate. "
                   "NOT the FBI agency rate and not comparable with NYPD precinct rates without that scaling; see data/reference/subcity_crime_note.md")
    T["source_url"] = "https://impact.jcnj.org/"; T["incidents_raw_path"] = str(JC_INCIDENTS.relative_to(ROOT)); T["computed_at"] = got
    T.reset_index().to_csv(REF / "subcity_crime_jersey_city.csv", index=False)

    print(C.to_string(index=False))
    print(T[["hood_name", "pop_acs_2019_2023", "violent_4_types", "property_5_types", "violent_per_1000_residents_annualised_portal", "property_per_1000_residents_annualised_portal",
             f"violent_per_1000_scaled_to_fbi_{int(fbi.year)}", f"property_per_1000_scaled_to_fbi_{int(fbi.year)}"]].to_string())
    print("tracts by rule:", t.rule.str[:40].value_counts().to_dict())
    print("uncovered city area km2:", round(jc_poly.difference(unary_union(list(G[G.city == 'Jersey City'].geometry))).area / 1e6, 3))
    print("assignment methods:", A.method.value_counts().to_dict(), "| near boundary:", int(A.near_boundary.sum()), "| review notes:", int((A.review_note != "").sum()))


if __name__ == "__main__":
    main()
