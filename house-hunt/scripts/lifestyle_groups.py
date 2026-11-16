"""Lifestyle groups ("years" / experiences), approved in outline by Will on 2026-11-15.

Fit (only with --refit, on purpose): Ward clustering (k=6) on 9 lifestyle indices, using neighborhoods whose
violent-crime rate is under 1.5x the US average (so high-crime precincts don't shape the groups).

ASSIGNMENT IS A PURE FUNCTION OF SAVED FILES (pipeline consistency pass, 2026-11-16). A neighborhood's group depends
only on its own saved area profile and the saved parameters; adding or removing listings never changes it:
  data/reference/lifestyle_area_features.csv  the area profile of each neighborhood (the raw inputs of the indices),
                                              FROZEN. A neighborhood is profiled once, when it first appears, and
                                              the row is never recomputed in a normal run (--refreeze-area to redo).
  data/reference/lifestyle_scaling.csv        per raw feature: log or not, the value that fills a blank, mean and SD
  data/reference/lifestyle_index_scale.csv    SD of each index over the fit set
  data/reference/lifestyle_group_centres.csv  the six centres
  data/reference/lifestyle_group_overrides.csv  reviewed exceptions (hood_id, group_key, why): applied last
Before this pass the indices were computed from data/lifestyle_color.csv, whose every value is a median over the
buildings that CURRENTLY pass the gates; East Rutherford and Patchogue changed group when each went from two passing
buildings to one. Those per-run medians are still written to data/lifestyle_groups.csv (the ranking reads a few of
them), but they no longer decide the group.
Two crime filters are stored as flags, not applied (Will decides later):
  crime_filter_a: violent rate < 1.5x US average     crime_filter_b: violent rate < 2.0x US average
Outputs: data/lifestyle_groups.csv (one row per neighborhood), data/lifestyle_group_distances.csv (distance of every
neighborhood to every centre, nearest and second nearest, and whether the two are within 10 percent).
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


LOGGED = ["people_per_km2", "restaurants_800m", "bars_800m", "cafes_800m", "music_1600m", "park_ha_800m", "park_walk_min", "dog_park_m", "open_water_m", "median_hh_income"]
PLAIN = ["no_car_share", "transit_commute_share", "detached_house_share", "newcomer_share", "wfh_share", "age_25_34_share", "living_alone_share",
         "built_since_2010_share", "built_before_1940_share", "median_year_built", "households_with_kids_share", "college_degree_share", "sqft_per_1000usd"]
RAW = PLAIN + LOGGED          # the 23 raw features the nine indices are built from
REF = DATA / "reference"
BOUNDARY = 0.90               # nearest / second-nearest distance at or above this: a boundary case (within 10 percent)


def scaling_from(ref):
    """Scaling parameters from the fit set (a frame of raw features): per feature the fill value for a blank (the fit
    set's median) and the mean and SD the z-score uses (of log1p(value) for the LOGGED features). Saved at --refit."""
    f = ref[RAW].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    f = f.fillna(f.median())
    rows = []
    for c in RAW:
        x = np.log1p(f[c].clip(lower=0)) if c in LOGGED else f[c]
        rows.append({"feature": c, "log1p": c in LOGGED, "fill": float(ref[c].replace([np.inf, -np.inf], np.nan).median()), "mean": float(x.mean()), "sd": float(x.std(ddof=0) or 1)})
    return pd.DataFrame(rows).set_index("feature")


def indices(H, scaling):
    """The nine lifestyle indices of each row of H (raw features), z-scored with SAVED parameters. Nothing here looks at
    the other rows of H: a neighborhood's indices depend on its own features only."""
    f = H.reindex(columns=RAW).apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    f = f.fillna(scaling.fill)
    def z(c, log=False):
        assert log == bool(scaling.at[c, "log1p"]), c
        x = np.log1p(f[c].clip(lower=0)) if log else f[c]
        return (x - scaling.at[c, "mean"]) / scaling.at[c, "sd"]
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


def assign(area, scaling, scale, centres, overrides=None):
    """Group of each neighborhood from its frozen area profile and the saved parameters. Returns a frame indexed like
    `area`: d_<group> (Euclidean distance to each centre), nearest, second, ratio (nearest / second distance),
    boundary (ratio >= 0.90), computed_group, override, group_key. Pure: one row in, one row out."""
    I = indices(area, scaling) / scale
    d = np.sqrt(((I[IDX].values[:, None, :] - centres[IDX].values[None]) ** 2).sum(axis=2))
    order = np.argsort(d, axis=1, kind="stable")
    D = pd.DataFrame(d, index=area.index, columns=["d_" + k for k in centres.index])
    D["nearest"] = centres.index[order[:, 0]]
    D["second"] = centres.index[order[:, 1]]
    D["ratio"] = d[np.arange(len(d)), order[:, 0]] / d[np.arange(len(d)), order[:, 1]]
    D["boundary"] = D.ratio >= BOUNDARY
    D["computed_group"] = D.nearest
    ov = overrides if overrides is not None else {}
    D["override"] = [ov.get(h, "") for h in D.index]
    D["group_key"] = np.where(D.override != "", D.override, D.computed_group)
    return D, I


def load_overrides(path=None):
    f = Path(path) if path else REF / "lifestyle_group_overrides.csv"
    if not f.exists():
        return {}
    O = pd.read_csv(f, dtype=str, keep_default_na=False)
    bad = set(O.group_key) - set(LABELS)
    assert not bad, f"lifestyle_group_overrides.csv: unknown group_key {bad}"
    return dict(zip(O.hood_id, O.group_key))


def freeze_area(H, path=None, refreeze=False, today=None):
    """The frozen area profile. Rows already in the file are returned unchanged whatever H holds now; a neighborhood not
    in the file yet is profiled from H (its buildings as they stand) and appended. Returns (area frame, new ids)."""
    f = Path(path) if path else REF / "lifestyle_area_features.csv"
    A = pd.read_csv(f).set_index("hood_id") if f.exists() and not refreeze else pd.DataFrame(columns=["hood", "n_buildings", "basis"] + RAW)
    new = [h for h in H.index if h not in A.index]
    if new:
        add = H.loc[new].reindex(columns=["hood", "buildings"] + RAW).rename(columns={"buildings": "n_buildings"})
        add.insert(2, "basis", f"profiled when first seen ({today or pd.Timestamp.now(tz='UTC').date()}): medians over the buildings passing then")
        A = pd.concat([A, add]) if len(A) else add
        A.index.name = "hood_id"
        A.sort_index().to_csv(f)
        A = pd.read_csv(f).set_index("hood_id")
    return A, new


def main(refit=False, refreeze_area=False):
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
    cf, rf, sf = REF / "lifestyle_group_centres.csv", REF / "lifestyle_fit_reference.csv", REF / "lifestyle_scaling.csv"
    if refit or not cf.exists():
        from scipy.cluster.hierarchy import linkage, fcluster
        fit = H[H.crime_filter_a & (H.units > 0) & (H.sqft_per_1000usd.fillna(0) < 500)]
        fit.to_csv(rf)
        scaling = scaling_from(fit)
        scaling.to_csv(sf)
        scale = indices(fit, scaling).std(ddof=0)
        I = indices(fit, scaling) / scale
        lab = fcluster(linkage(I.values, "ward"), 6, "maxclust")
        C = I.groupby(lab).mean()
        # match clusters to labels by signature
        sig = {"pre_car": C.street_life, "new_water": C.new_build + C.water, "enclave": C.families + C.means - C.street_life,
               "space": C.space_for_money + C.families * 0.5, "settled": C.car_free - C.means - C.street_life * 0.5}
        names, left = {}, set(C.index)
        for k in ["pre_car", "new_water", "enclave", "space", "settled"]:
            best = sig[k].loc[list(left)].idxmax(); names[best] = k; left.discard(best)
        names[left.pop()] = "middle"
        C.index = [names[i] for i in C.index]
        C.to_csv(cf); scale.to_csv(REF / "lifestyle_index_scale.csv")
    if not sf.exists():          # parameters saved beside the centres (derived once from the saved fit set)
        scaling_from(pd.read_csv(rf).set_index("hood_id")).to_csv(sf)
    C = pd.read_csv(cf, index_col=0)
    scale = pd.read_csv(REF / "lifestyle_index_scale.csv", index_col=0).iloc[:, 0]
    scaling = pd.read_csv(sf).set_index("feature")
    area, new = freeze_area(H, refreeze=refreeze_area or refit)
    if new:
        print(f"area profile frozen for {len(new)} neighborhood(s) seen for the first time: {', '.join(new[:12])}")
    D, I = assign(area.loc[H.index], scaling, scale, C, load_overrides())
    H["group_key"] = D.group_key
    H["group_computed"], H["group_override"], H["group_boundary"] = D.computed_group, D.override, D.boundary
    H["group_label"] = H.group_key.map(lambda k: LABELS[k][0]); H["group_subhead"] = H.group_key.map(lambda k: LABELS[k][1])
    H.join(I.add_prefix("ix_")).to_csv(DATA / "lifestyle_groups.csv")
    out = D.copy()
    out.insert(0, "hood", H.hood)
    out.insert(1, "n_buildings_in_profile", area.n_buildings.reindex(H.index))
    out.round(4).sort_index().to_csv(DATA / "lifestyle_group_distances.csv")
    print(f"boundary cases (nearest and second-nearest centre within 10 percent): {int(D.boundary.sum())} of {len(D)}; overrides applied: {int((D.override != '').sum())}")
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
    main("--refit" in sys.argv, "--refreeze-area" in sys.argv)
