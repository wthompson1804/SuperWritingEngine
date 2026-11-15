"""Lifestyle features per neighborhood (no location features: no drive time, no state, no county).

Sources: ACS 2019-2023 5-year by census tract (Census API), OSM counts (places tool, already in buildings_enriched),
crime agency rates, building facts. Each building's tract describes the blocks around it; a neighborhood's value
is the median over its passing buildings.
Then: correlation matrix, principal components (to see which traits move together), and clustering.
Outputs: data/lifestyle_features.csv, data/lifestyle_loadings.csv, docs/LIFESTYLE_ANALYSIS.md
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT, get_json, census_key
from build_areas import census_geo, first

ACS = "https://api.census.gov/data/2023/acs/acs5"
VARS = {
    "B01003_001E": "pop", "B01002_001E": "median_age",
    "B01001_011E": "m25_29", "B01001_012E": "m30_34", "B01001_035E": "f25_29", "B01001_036E": "f30_34",
    "B11001_001E": "hh", "B11001_008E": "hh_alone",
    "B25003_001E": "occ", "B25003_003E": "renter",
    "B25024_001E": "units", "B25024_002E": "u_detached", "B25024_008E": "u_20_49", "B25024_009E": "u_50plus",
    "B25035_001E": "median_year_built",
    "B25044_001E": "veh_hh", "B25044_003E": "own_noveh", "B25044_010E": "rent_noveh",
    "B08301_001E": "workers", "B08301_010E": "by_transit", "B08301_019E": "by_walk", "B08301_021E": "wfh",
    "B19013_001E": "median_hh_income", "B25064_001E": "median_gross_rent",
    "B07003_001E": "mob_total", "B07003_004E": "same_house",
}


def acs_county(state, county):
    js, meta = get_json(ACS, "census_acs_api", params={"get": ",".join(VARS), "for": "tract:*",
                        "in": f"state:{state} county:{county}", "key": census_key()}, timeout=120)
    df = pd.DataFrame(js[1:], columns=js[0])
    df["tract_geoid"] = df.state + df.county + df.tract
    return df.rename(columns=VARS)


def main():
    u = pd.read_csv(DATA / "units.csv", low_memory=False)
    u = u[u.unit_status == "pass"]
    B = u.drop_duplicates("addr_key")[["addr_key", "lat", "lon", "hood_id", "hood", "hood_area", "state"]].copy()
    tr, land = [], []
    for r in B.itertuples():
        g, _ = census_geo(float(r.lat), float(r.lon))
        t = (g.get("Census Tracts") or [{}])[0]
        tr.append(t.get("GEOID", "")); land.append(float(t.get("AREALAND", 0) or 0))
    B["tract_geoid"], B["tract_land_m2"] = tr, land
    frames = [acs_county(k[:2], k[2:]) for k in sorted({t[:5] for t in tr if t})]
    A = pd.concat(frames).set_index("tract_geoid")
    A = A[list(VARS.values())].apply(pd.to_numeric, errors="coerce").where(lambda x: x > -1e8)
    B = B.join(A, on="tract_geoid")
    f = pd.DataFrame({"addr_key": B.addr_key, "hood_id": B.hood_id})
    f["people_per_km2"] = B["pop"] / (B.tract_land_m2 / 1e6)
    f["age_25_34_share"] = (B.m25_29 + B.m30_34 + B.f25_29 + B.f30_34) / B["pop"]
    f["median_age"] = B.median_age
    f["living_alone_share"] = B.hh_alone / B.hh
    f["renter_share"] = B.renter / B.occ
    f["big_building_share"] = (B.u_20_49 + B.u_50plus) / B.units
    f["detached_house_share"] = B.u_detached / B.units
    f["median_year_built"] = B.median_year_built
    f["no_car_share"] = (B.own_noveh + B.rent_noveh) / B.veh_hh
    f["transit_commute_share"] = B.by_transit / B.workers
    f["walk_commute_share"] = B.by_walk / B.workers
    f["wfh_share"] = B.wfh / B.workers
    f["median_hh_income"] = B.median_hh_income
    f["newcomer_share"] = 1 - B.same_house / B.mob_total
    be = pd.read_csv(DATA / "buildings_enriched.csv")
    def cr(s, k):
        try:
            return json.loads(s).get(k)
        except Exception:
            return np.nan
    be["violent_per_1000"] = be.crime_latest.map(lambda s: cr(s, "violent_per_1000"))
    be["vehicle_theft_per_1000"] = be.crime_latest.map(lambda s: cr(s, "motor_vehicle_theft_per_1000"))
    keep = ["addr_key", "restaurants_800m", "bars_800m", "cafes_800m", "music_1600m", "park_ha_800m", "park_walk_min",
            "open_water_m", "beach_m", "supermarket_m", "train_station_m", "motorway_m", "violent_per_1000", "vehicle_theft_per_1000"]
    f = f.merge(be[keep], on="addr_key", how="left")
    ub = u.groupby("addr_key").agg(sqft=("sqft", "median"), all_in=("all_in", "median"),
                                   bfloors=("building_floors", lambda s: pd.to_numeric(s, errors="coerce").median()),
                                   garage=("parking_type", lambda s: float(s.fillna("").str.contains("garage|covered|gated", case=False).any())))
    ub["sqft_per_1000usd"] = ub.sqft / ub.all_in * 1000
    f = f.merge(ub[["sqft", "bfloors", "garage", "sqft_per_1000usd"]], on="addr_key", how="left")
    feats = [c for c in f.columns if c not in ("addr_key", "hood_id")]
    H = f.groupby("hood_id")[feats].median()
    meta = u.groupby("hood_id").agg(hood=("hood", "first"), area=("hood_area", "first"), state=("state", "first"),
                                    units=("listing_id", "count"), buildings=("addr_key", "nunique"),
                                    drive_min=("drive_min_to", "median"))
    H = meta.join(H)
    H.to_csv(DATA / "lifestyle_features.csv")
    print(len(H), "neighborhoods;", H[feats].isna().mean().round(2).to_dict())


if __name__ == "__main__":
    main()
