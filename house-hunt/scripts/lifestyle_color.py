"""Extra 'colour' variables per neighborhood, beyond the ones that drive the clustering.

ACS 2019-2023 tract: college degree share, households with children, age 65+, mean commute, housing built since
2010 / before 1940, median rent. From the enriched building files: distances to supermarket, Trader Joe's, Whole
Foods, Target, vet, dog park, train station; breweries and music venues within 1,600 m. From listings: building
floors, amenities, parking type, unit size.
Output: data/lifestyle_color.csv (one row per neighborhood, merged with lifestyle_features).
"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, get_json, census_key
from build_areas import census_geo

ACS = "https://api.census.gov/data/2023/acs/acs5"
V = {"B15003_001E": "edu_tot", "B15003_022E": "ba", "B15003_023E": "ma", "B15003_024E": "prof", "B15003_025E": "phd",
     "B11005_001E": "hh_tot", "B11005_002E": "hh_kids",
     "B01001_001E": "pop", "B01001_020E": "m65a", "B01001_021E": "m65b", "B01001_022E": "m70", "B01001_023E": "m75", "B01001_024E": "m80", "B01001_025E": "m85",
     "B01001_044E": "f65a", "B01001_045E": "f65b", "B01001_046E": "f70", "B01001_047E": "f75", "B01001_048E": "f80", "B01001_049E": "f85",
     "B08303_001E": "c_tot", "B08303_012E": "c60", "B08303_013E": "c90",
     "B25034_001E": "yb_tot", "B25034_002E": "yb2020", "B25034_003E": "yb2010", "B25034_011E": "yb_pre1940",
     "B25064_001E": "median_rent", "B25071_001E": "rent_burden_pct"}


def main():
    u = pd.read_csv(DATA / "units.csv", low_memory=False); u = u[u.unit_status == "pass"]
    B = u.drop_duplicates("addr_key")[["addr_key", "lat", "lon", "hood_id"]].copy()
    B["tract"] = [(census_geo(float(a), float(o))[0].get("Census Tracts") or [{}])[0].get("GEOID", "") for a, o in zip(B.lat, B.lon)]
    fr = []
    for k in sorted({t[:5] for t in B.tract if t}):
        js, _ = get_json(ACS, "census_acs_api", params={"get": ",".join(V), "for": "tract:*", "in": f"state:{k[:2]} county:{k[2:]}", "key": census_key()}, timeout=120)
        d = pd.DataFrame(js[1:], columns=js[0]); d["tract"] = d.state + d.county + d.tract; fr.append(d.rename(columns=V))
    A = pd.concat(fr).set_index("tract")[list(V.values())].apply(pd.to_numeric, errors="coerce").where(lambda x: x > -1e8)
    B = B.join(A, on="tract")
    c = pd.DataFrame({"addr_key": B.addr_key, "hood_id": B.hood_id})
    c["college_degree_share"] = (B.ba + B.ma + B.prof + B.phd) / B.edu_tot
    c["households_with_kids_share"] = B.hh_kids / B.hh_tot
    c["age_65plus_share"] = B[[x for x in B.columns if x[:2] in ("m6", "m7", "m8", "f6", "f7", "f8")]].sum(axis=1) / B["pop"]
    c["commute_60min_plus_share"] = (B.c60 + B.c90) / B.c_tot
    c["built_since_2010_share"] = (B.yb2020 + B.yb2010) / B.yb_tot
    c["built_before_1940_share"] = B.yb_pre1940 / B.yb_tot
    c["tract_median_rent"] = B.median_rent
    c["rent_burden_pct"] = B.rent_burden_pct
    rows = []
    for f in glob.glob(str(DATA / "enriched" / "*.json")):
        r = json.load(open(f)); p = r.get("places", {})
        def m(sec, k):
            try:
                return float(p[sec][k]["value"])
            except Exception:
                return np.nan
        rows.append({"addr_key": r["addr_key"], "supermarket_m": m("errands", "nearest_supermarket"),
                     "trader_joes_m": m("errands", "nearest_trader_joes"), "whole_foods_m": m("errands", "nearest_whole_foods"),
                     "target_m": m("errands", "nearest_target"), "vet_m": m("errands", "nearest_veterinary"),
                     "dog_park_m": m("green_space", "nearest_dog_park"), "train_station_m": m("setting", "nearest_train_station"),
                     "breweries_1600m": m("going_out", "brewery_count_1600m"), "restaurants_1600m": m("going_out", "restaurant_count_1600m"),
                     "transit_to_parents_min": (r.get("transit_sat", {}).get("median_minutes") or {}).get("value") if isinstance(r.get("transit_sat", {}).get("median_minutes"), dict) else np.nan})
    c = c.merge(pd.DataFrame(rows), on="addr_key", how="left")
    txt = (u.notes.fillna("") + " " + u.get("community_pool", pd.Series("", index=u.index)).fillna("").astype(str)).str.lower()
    ub = u.assign(pool=u.get("community_pool", pd.Series("", index=u.index)).fillna("").astype(str).str.lower().str.contains("yes|pool"),
                  gated=u.parking_type.fillna("").str.contains("garage|gated|covered", case=False),
                  street=u.parking_type.fillna("").str.contains("street", case=False),
                  bfl=pd.to_numeric(u.building_floors, errors="coerce").fillna(pd.to_numeric(u.get("pluto_floors"), errors="coerce")),
                  yr=pd.to_numeric(u.get("pluto_year"), errors="coerce")
                  ).groupby("addr_key").agg(pool=("pool", "max"), garage_or_gated=("gated", "max"), street_parking=("street", "max"),
                                            building_floors=("bfl", "median"), building_year=("yr", "median"), unit_sqft=("sqft", "median"), all_in=("all_in", "median"))
    c = c.merge(ub, on="addr_key", how="left")
    cols = [x for x in c.columns if x not in ("addr_key", "hood_id")]
    H = c.groupby("hood_id")[cols].agg(lambda s: pd.to_numeric(s, errors="coerce").astype(float).median())
    base = pd.read_csv(DATA / "lifestyle_features.csv").set_index("hood_id")
    base.join(H, rsuffix="_c").to_csv(DATA / "lifestyle_color.csv")
    print(len(H), H.isna().mean().round(2).to_dict())


if __name__ == "__main__":
    main()
