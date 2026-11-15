"""Lifestyle groups ("years"), approved in outline by Will on 2026-11-15.

Fit: Ward clustering (k=6) on 9 lifestyle indices, using neighborhoods whose violent-crime rate is under 1.5x the
US average (so high-crime precincts don't shape the groups). Every other neighborhood is then assigned to the
nearest group centre. Centres are saved (data/reference/lifestyle_group_centres.csv); later runs with more
neighborhoods assign to the saved centres unless --refit is given, so group meanings stay stable.
Two crime filters are stored as flags, not applied (Will decides later):
  crime_filter_a: violent rate < 1.5x US average     crime_filter_b: violent rate < 2.0x US average
Output: data/lifestyle_groups.csv (one row per neighborhood).
"""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA

LABELS = {  # key = signature trait used to match a fitted cluster to its label
    "pre_car":   ("The Walk-Everywhere Year", "Old city blocks built before cars, where dinner, coffee and friends are a walk away and the car mostly sits."),
    "settled":   ("The Old-Neighborhood Year", "Long-settled apartment districts where the avenue feeds everyone and the neighbors have been there for years."),
    "new_water": ("The Fresh-Start Year", "New towers beside the water, where one neighbor in five moved in this year and everyone is looking to meet people."),
    "middle":    ("The Little-City Year", "Small cities and inner suburbs with a real downtown: a car for errands, a main street for Friday night."),
    "space":     ("The Room-to-Breathe Year", "Older suburbs where the money buys the most space, families live next door and most things are a drive."),
    "enclave":   ("The Quiet-Street Year", "An apartment tucked among houses and lawns: the lowest crime on the list and almost nothing on foot."),
}
IDX = ["car_free", "new_arrivals", "street_life", "green", "water", "new_build", "families", "means", "space_for_money"]


def indices(H, ref=None):
    f = H.select_dtypes("number").replace([np.inf, -np.inf], np.nan)
    f = f.fillna((ref if ref is not None else f).median(numeric_only=True))
    R = f if ref is None else ref.select_dtypes("number").replace([np.inf, -np.inf], np.nan).pipe(lambda r: r.fillna(r.median()))
    lg = lambda c: np.log1p(f[c].clip(lower=0)); lgR = lambda c: np.log1p(R[c].clip(lower=0))
    def z(c, log=False):
        a, b = (lg(c), lgR(c)) if log else (f[c], R[c])
        return (a - b.mean()) / (b.std(ddof=0) or 1)
    I = pd.DataFrame(index=H.index)
    I["car_free"] = (z("no_car_share") + z("transit_commute_share") + z("people_per_km2", True) - z("detached_house_share")) / 4
    I["new_arrivals"] = (z("newcomer_share") + z("wfh_share") + z("age_25_34_share") + z("living_alone_share")) / 4
    I["street_life"] = (z("restaurants_800m", True) + z("bars_800m", True) + z("cafes_800m", True) + z("music_1600m", True)) / 4
    I["green"] = (z("park_ha_800m", True) - z("park_walk_min", True) - z("dog_park_m", True)) / 3
    I["water"] = -z("open_water_m", True)
    I["new_build"] = (z("built_since_2010_share") - z("built_before_1940_share") + z("median_year_built")) / 3
    I["families"] = (z("households_with_kids_share") + z("detached_house_share")) / 2
    I["means"] = (z("college_degree_share") + z("median_hh_income", True)) / 2
    I["space_for_money"] = z("sqft_per_1000usd")
    return I


def main(refit=False):
    H = pd.read_csv(DATA / "lifestyle_color.csv").set_index("hood_id")
    S = pd.read_csv(DATA / "neighborhood_safety.csv").set_index("hood_id")
    H = H.join(S[["violent", "violent_vs_us", "violent_vs_metro", "violent_vs_local", "motor_vehicle_theft", "property", "property_vs_us",
                  "motor_vehicle_theft_vs_us", "motor_vehicle_theft_vs_local", "police", "geography", "crime_year"]], rsuffix="_s")
    # Will's safety rule (2026-11-15, final): Jamaica (NYPD 103rd Precinct, where her parents live) is the yardstick.
    # Violent OR property crime above Jamaica's rate = cut. Lower is preferred (used in ranking).
    jam = S[S.police.astype(str).str.contains("103")].iloc[0]
    H["jamaica_violent"] = jam.violent; H["jamaica_property"] = jam.property
    H["violent_vs_jamaica"] = (H.violent / jam.violent).round(2)
    H["property_vs_jamaica"] = (H.property / jam.property).round(2)
    H["safety_cut"] = (H.violent > jam.violent) | (H.property > jam.property)   # Will, final: neither may exceed Jamaica
    H["safety_cut_reason"] = np.where(H.violent > jam.violent, "violent above Jamaica", np.where(H.property > jam.property, "property above Jamaica", ""))
    H["property_flag"] = False
    H["crime_filter_a"] = H.violent_vs_us < 1.5   # kept only to hold the group fit stable; not a gate
    cf = DATA / "reference" / "lifestyle_group_centres.csv"
    rf = DATA / "reference" / "lifestyle_fit_reference.csv"
    if refit or not cf.exists():
        from scipy.cluster.hierarchy import linkage, fcluster
        fit = H[H.crime_filter_a & (H.units > 0) & (H.sqft_per_1000usd.fillna(0) < 500)]
        fit.to_csv(rf)
        I = indices(fit); I = I / I.std(ddof=0)
        lab = fcluster(linkage(I.values, "ward"), 6, "maxclust")
        C = I.groupby(lab).mean()
        scale = indices(fit).std(ddof=0)
        # match clusters to labels by signature
        sig = {"pre_car": C.street_life, "new_water": C.new_build + C.water, "enclave": C.families + C.means - C.street_life,
               "space": C.space_for_money + C.families * 0.5, "settled": C.car_free - C.means - C.street_life * 0.5}
        names, left = {}, set(C.index)
        for k in ["pre_car", "new_water", "enclave", "space", "settled"]:
            best = sig[k].loc[list(left)].idxmax(); names[best] = k; left.discard(best)
        names[left.pop()] = "middle"
        C.index = [names[i] for i in C.index]
        C.to_csv(cf); scale.to_csv(DATA / "reference" / "lifestyle_index_scale.csv")
    C = pd.read_csv(cf, index_col=0)
    scale = pd.read_csv(DATA / "reference" / "lifestyle_index_scale.csv", index_col=0).iloc[:, 0]
    ref = pd.read_csv(rf).set_index("hood_id")
    I = indices(H, ref) / scale
    d = ((I.values[:, None, :] - C[IDX].values[None]) ** 2).sum(axis=2)
    H["group_key"] = C.index[d.argmin(axis=1)]
    H["group_label"] = H.group_key.map(lambda k: LABELS[k][0]); H["group_subhead"] = H.group_key.map(lambda k: LABELS[k][1])
    H.join(I.add_prefix("ix_")).to_csv(DATA / "lifestyle_groups.csv")
    K = H[~H.safety_cut]
    t = H.groupby("group_label").agg(hoods=("hood", "count"), units=("units", "sum"))
    t["hoods_kept"] = K.groupby("group_label").hood.count(); t["units_kept"] = K.groupby("group_label").units.sum()
    t["property_flagged_hoods"] = K[K.property_flag].groupby("group_label").hood.count()
    print(f"Jamaica yardstick: violent {jam.violent} per 1,000, property {jam.property} per 1,000")
    print(t.fillna(0).astype(int).to_string())
    print("CUT:", "; ".join(f"{r.hood} ({r.violent:.1f}, {int(r.units)}u)" for r in H[H.safety_cut].sort_values("violent", ascending=False).itertuples()))
    print("PROPERTY FLAG:", "; ".join(f"{r.hood} ({r.property:.1f})" for r in K[K.property_flag].sort_values("property", ascending=False).itertuples()))
    for k, g in H.groupby("group_key"):
        print(k, "::", "; ".join(f"{r.hood}[{int(r.units)}]" for r in g.sort_values("units", ascending=False).head(10).itertuples()))


if __name__ == "__main__":
    main("--refit" in sys.argv)
