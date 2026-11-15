"""Ranking, as approved by Will on 2026-11-15 (docs/RANKING.md).

Layer 1  universal value score, 0-100: weighted mean of six parts, each a percentile across ALL kept units
         safety 25, cost 15, building 20, car 15, space 15, dog 10.  Unknown facts score at the 25th percentile.
Layer 2  promise score: how well the place delivers what its year (lifestyle group) is chosen for.
         rank score = 0.7 * universal + 0.3 * promise + pool bump (+3 any pool, +6 indoor pool).
Layer 3  two standings per measure (within its year, and against everything) and each year's "exchange rate"
         against staying near home (medians, real units). Computed in the background; shown on demand.
Selection per neighborhood: highest rank score first, at most 2 units per building; units that another unit in the
same neighborhood beats or ties on all six parts go last. Top 15 = candidates for the evidence pass (avoid cards);
top 10 after that pass are shown.
Outputs: data/ranked_units.csv, data/group_exchange.csv
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA  # noqa: E402

W = {"safety": 25, "cost": 15, "building": 20, "car": 15, "space": 15, "dog": 10}
UNIVERSAL_SHARE, PROMISE_SHARE = 0.7, 0.3
POOL_BUMP, INDOOR_POOL_BUMP = 3, 6
UNKNOWN_PCT = 25
MAX_PER_BUILDING, SHOWN, CANDIDATES = 2, 10, 15
NEAR_HOME_DRIVE_MIN = 15


def pct(s: pd.Series, higher_is_better=True) -> pd.Series:
    """Percentile 0-100 across all units; NaN -> UNKNOWN_PCT."""
    x = pd.to_numeric(s, errors="coerce")
    r = x.rank(pct=True, method="average") * 100
    if not higher_is_better:
        r = 100 - r + (100 / max(x.notna().sum(), 1))
    return r.fillna(UNKNOWN_PCT).clip(0, 100)


def cr(s, k):
    try:
        return json.loads(s).get(k)
    except Exception:
        return np.nan


def parking_rank(t: str) -> float:
    t = str(t).lower()
    if not t or t in ("nan", "unknown", "?", "no_mention"):
        return np.nan
    if "garage" in t or "gated" in t:
        return 4
    if "covered" in t or "carport" in t:
        return 3
    if "lot" in t or "surface" in t or "off-street" in t or "off street" in t or "assigned" in t:
        return 2
    if "street" in t:
        return 1
    return 2 if "parking" in t else np.nan


def main():
    u = pd.read_csv(DATA / "units.csv", low_memory=False)
    u = u[u.unit_status == "pass"].copy()
    G = pd.read_csv(DATA / "lifestyle_groups.csv").set_index("hood_id")
    for c in ["group_key", "group_label", "safety_cut", "safety_cut_reason", "newcomer_share", "violent", "property",
              "motor_vehicle_theft", "violent_vs_jamaica", "property_vs_jamaica", "violent_vs_us"]:
        u[c] = u.hood_id.map(G[c])
    cut = u[u.safety_cut.fillna(False)]
    u = u[~u.safety_cut.fillna(False)].copy()

    am = DATA / "reference" / "building_amenities.csv"
    A = pd.read_csv(am, dtype=str, keep_default_na=False).drop_duplicates("addr_key").set_index("addr_key") if am.exists() else pd.DataFrame()

    def a(col, default=""):
        return u.addr_key.map(A[col]) if col in A else pd.Series(default, index=u.index)
    known = lambda s: s.fillna("").astype(str).str.lower().isin(["", "no_mention", "nan", "unknown"]) == False  # noqa: E712
    pool = a("pool").fillna("").astype(str).str.lower()
    cp = u.get("community_pool", pd.Series("", index=u.index)).fillna("").astype(str).str.lower()
    u["pool"] = np.where(pool.isin(["indoor", "both"]) | cp.str.contains("indoor"), "indoor",
                         np.where(pool.isin(["outdoor", "yes_type_unknown"]) | cp.str.contains("yes|outdoor|pool"), "pool", ""))

    # ---- parts (each 0-100 across all kept units)
    near = pd.to_numeric(u.near_veh_theft_24m, errors="coerce") + pd.to_numeric(u.near_theft_from_veh_24m, errors="coerce").fillna(0)
    saf = pd.concat([pct(u.violent, False), pct(u.property, False), pct(u.motor_vehicle_theft, False)], axis=1).mean(axis=1)
    near_p = pct(near, False)
    u["p_safety"] = np.where(near.notna(), saf * 0.7 + near_p * 0.3, saf)
    u["p_cost"] = pct(u.all_in, False)
    u["p_space"] = pct(u.sqft)

    def ind(cond_yes, is_known):
        return np.where(cond_yes, 1.0, np.where(is_known, 0.0, 0.25))
    laundry = (u.laundry.fillna("").astype(str) + " " + a("in_unit_laundry").fillna("").astype(str)).str.lower()
    b = (ind(u.elevator_basis.eq("stated") | a("elevator_stated").eq("yes"), True)
         + ind(laundry.str.contains("in unit|in_unit|in-unit|yes"), laundry.str.strip().ne(""))
         + ind(known(a("doorman_or_concierge")), False)
         + ind(known(a("controlled_access")) | u.get("community_controlled_access", pd.Series("", index=u.index)).fillna("").astype(str).str.contains("yes", case=False), False)
         + ind(known(a("gym")) | u.get("community_gym", pd.Series("", index=u.index)).fillna("").astype(str).str.contains("yes", case=False), False)
         + ind(known(a("package_room")), False)
         + ind(known(a("roof_deck_or_outdoor_space")), False))
    yr = pd.to_numeric(a("year_built"), errors="coerce").fillna(pd.to_numeric(u.get("pluto_year"), errors="coerce"))
    u["building_points"] = b
    u["p_building"] = pct(pd.Series(b, index=u.index)) * 0.8 + pct(yr) * 0.2
    pr = u.parking_type.map(parking_rank)
    pr = pr.fillna(a("gated_or_garage_parking").map(parking_rank))
    u["parking_rank"] = pr
    u["p_car"] = pct(pr)
    dogam = known(a("dog_amenities")) | u.get("community_dog_park_pet_spa", pd.Series("", index=u.index)).fillna("").astype(str).str.contains("yes", case=False)
    u["p_dog"] = (pct(u.park_walk_min, False) * 0.4 + pct(u.dog_park_m, False) * 0.3 + pct(u.pet_rent, False) * 0.15
                  + np.where(dogam, 100, UNKNOWN_PCT) * 0.15)
    u["universal"] = sum(u[f"p_{k}"] * w for k, w in W.items()) / 100

    # ---- promise of the year
    def col(name):
        return pd.to_numeric(u.get(name), errors="coerce")
    be = pd.read_csv(DATA / "lifestyle_color.csv").set_index("hood_id")
    P = {
        "pre_car": (pct(u.restaurants_800m) + pct(u.bars_800m) + pct(u.cafes_800m) + pct(col("supermarket_m"), False)) / 4,
        "settled": (pct(col("supermarket_m"), False) + pct(u.transit_sat_median, False)) / 2,
        "new_water": (pct(pd.Series(b, index=u.index)) + pct(u.open_water_m, False) + pct(u.newcomer_share)) / 3,
        "middle": (pct(u.restaurants_800m) + pct(col("train_station_m"), False)) / 2,
        "space": pct(col("sqft") / col("all_in")),
        "enclave": (pct(u.violent, False) + pct(col("motorway_m")) + pct(pr)) / 3,
    }
    u["promise"] = 0.0
    for k, s in P.items():
        m = u.group_key == k
        u.loc[m, "promise"] = s[m]
    u["pool_bump"] = u.pool.map({"indoor": INDOOR_POOL_BUMP, "pool": POOL_BUMP}).fillna(0)
    u["rank_score"] = (UNIVERSAL_SHARE * u.universal + PROMISE_SHARE * u.promise + u.pool_bump).round(1)

    # ---- standings: within the year, and against everything
    for k in list(W) + ["universal", "rank_score"]:
        c = f"p_{k}" if k in W else k
        u[f"{k}_in_year"] = u.groupby("group_key")[c].rank(pct=True).mul(100).round(0)
        u[f"{k}_overall"] = u[c].rank(pct=True).mul(100).round(0)

    # ---- selection per neighborhood
    parts = [f"p_{k}" for k in W]
    u["dominated"] = False
    for hid, g in u.groupby("hood_id"):
        v = g[parts].values
        for i in range(len(g)):
            d = (v >= v[i]).all(axis=1) & (v > v[i]).any(axis=1)
            if d.any():
                u.loc[g.index[i], "dominated"] = True
    u = u.sort_values(["hood_id", "dominated", "rank_score"], ascending=[True, True, False])
    u["nth_in_building"] = u.groupby(["hood_id", "addr_key"]).cumcount() + 1
    elig = u.nth_in_building <= MAX_PER_BUILDING
    u["hood_rank"] = np.nan
    u.loc[elig, "hood_rank"] = u[elig].groupby("hood_id").cumcount() + 1
    u["candidate"] = u.hood_rank <= CANDIDATES
    u["shown_pre_evidence"] = u.hood_rank <= SHOWN
    u.to_csv(DATA / "ranked_units.csv", index=False)

    # ---- five-point spectrum against staying in Queens (Will, 2026-11-15): 3 = about the same as Queens,
    #      1-2 = worse for her, 4-5 = better for her. Distance is "closer / farther", not better / worse.
    home = u[u.hood_area.astype(str).eq("Queens")]
    SPEC = {  # column, kind, small band, big band, higher_is_better (None = neutral: 1 much closer .. 5 much farther)
        "all_in": ("all_in", "abs", 75, 250, False), "sqft": ("sqft", "abs", 50, 150, True),
        "drive_min": ("drive_min_to", "abs", 5, 20, None), "transit_min": ("transit_sat_median", "abs", 10, 30, None),
        "violent_crime": ("violent", "ratio", 0.2, 0.5, False), "property_crime": ("property", "ratio", 0.2, 0.5, False),
        "food_and_drink_nearby": ("restaurants_800m", "ratio", 0.25, 0.6, True),
        "walk_to_green": ("park_walk_min", "abs", 2, 6, False), "parking": ("parking_rank", "abs", 0.5, 1.5, True),
    }
    spec_rows = []
    for name, (c, kind, small, big, hib) in SPEC.items():
        base = pd.to_numeric(home[c], errors="coerce").median()
        x = pd.to_numeric(u[c], errors="coerce")
        d = (x - base) if kind == "abs" else (x - base) / base
        step = np.where(d.abs() <= small, 0, np.where(d.abs() <= big, 1, 2)) * np.sign(d)
        if hib is False:
            step = -step
        u[f"vsq_{name}"] = np.where(x.isna(), np.nan, 3 + step)
        u[f"vsq_{name}_diff"] = (x - base).round(1)
        spec_rows.append({"measure": name, "column": c, "queens_median": round(base, 2), "kind": kind, "same_band": small,
                          "big_band": big, "direction": "higher is better" if hib else ("lower is better" if hib is False else "neutral: 1 closer, 5 farther")})
    pd.DataFrame(spec_rows).to_csv(DATA / "reference" / "queens_spectrum_definition.csv", index=False)
    u.to_csv(DATA / "ranked_units.csv", index=False)

    # ---- exchange rates against staying in Queens
    meas = {"all_in": "all_in", "sqft": "sqft", "drive_min": "drive_min_to", "transit_min": "transit_sat_median",
            "toll_round_trip": "toll_rt_ezpass", "violent_per_1000": "violent", "property_per_1000": "property",
            "restaurants_800m": "restaurants_800m", "park_walk_min": "park_walk_min", "parking_rank": "parking_rank"}
    rows = []
    for k, g in list(u.groupby("group_label")) + [("STAYING IN QUEENS (baseline)", home)]:
        r = {"group": k, "units": len(g), "neighborhoods": g.hood_id.nunique()}
        for name in SPEC:
            r["vsq_" + name] = round(g[f"vsq_{name}"].median(), 0)
        for name, c in meas.items():
            r[name] = round(pd.to_numeric(g[c], errors="coerce").median(), 1)
            r[name + "_vs_home"] = round(r[name] - pd.to_numeric(home[c], errors="coerce").median(), 1)
        rows.append(r)
    pd.DataFrame(rows).to_csv(DATA / "group_exchange.csv", index=False)
    print(f"kept {len(u)} units ({len(cut)} cut by the Jamaica safety rule); candidates {int(u.candidate.sum())}; shown {int(u.shown_pre_evidence.sum())}; pools: {u.pool.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
