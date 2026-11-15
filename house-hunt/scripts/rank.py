"""Ranking v2 (Will, 2026-11-15: "use many more variables; drop anything sketchy"). See docs/RANKING.md.

Listing confidence (before ranking):
  sketchy       -> excluded: stale 60+ days, no unit and no building name, thin syndicated feed, conflicting dog policy,
                   all-in under 60% of the neighborhood median, or two or more inferred gate facts
  one_inferred  -> kept, lower certainty; the open fact (elevator inferred from 6+ floors, floor not stated, or dog
                   size given only as "small") must be confirmed in the evidence pass before the unit is shown
  clean         -> every gate fact stated on the page
Universal value, 0-100 (weights sum to 100): safety 22, building 16, cost 12, car 12, space 12, distance 10,
dog 8, daily life 8. Each part blends several variables as percentiles across all kept units; an unknown variable
scores at the 25th percentile.
Rank score = 0.7 x universal + 0.3 x the year's promise + pool bump (+3 pool, +6 indoor), times a certainty factor
(1.00 clean, 0.97 one inferred fact).
Selection per neighborhood: top by rank score, at most 2 per building, dominated units last; top 15 are candidates
for the evidence pass, the best 10 that survive are shown.
Outputs: data/ranked_units.csv, data/group_exchange.csv, data/reference/queens_spectrum_definition.csv
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "tools"))
from lib import DATA  # noqa: E402

W = {"safety": 22, "building": 16, "cost": 12, "car": 12, "space": 12, "distance": 10, "dog": 8, "daily": 8}
UNIVERSAL_SHARE, PROMISE_SHARE = 0.7, 0.3
POOL_BUMP, INDOOR_POOL_BUMP = 3, 6
UNKNOWN_PCT = 25
CERTAINTY = {"clean": 1.0, "one_inferred": 0.97}
MAX_PER_BUILDING, SHOWN, CANDIDATES = 2, 10, 15
COLOR_DIR = DATA / "enriched_color"


def pct(s, higher_is_better=True):
    """Percentile 0-100 across all units; unknown -> UNKNOWN_PCT."""
    x = pd.to_numeric(s, errors="coerce")
    r = x.rank(pct=True, method="average") * 100
    if not higher_is_better:
        r = 100 - r + (100 / max(x.notna().sum(), 1))
    return r.fillna(UNKNOWN_PCT).clip(0, 100)


def blend(*pairs):
    """Weighted mean of percentile series: blend((series, weight), ...)."""
    tot = sum(w for _, w in pairs)
    return sum(s * w for s, w in pairs) / tot


def parking_rank(t):
    t = str(t).lower()
    if not t or t in ("nan", "unknown", "?", "no_mention", "parking_type_unknown"):
        return np.nan
    if "garage" in t or "gated" in t:
        return 4
    if "covered" in t or "carport" in t:
        return 3
    if "lot" in t or "surface" in t or "off-street" in t or "off street" in t or "assigned" in t:
        return 2
    if "street" in t:
        return 1
    return np.nan


def color_table(u):
    """places.color() per building, cached on disk; returns a flat frame indexed by addr_key."""
    import places
    COLOR_DIR.mkdir(exist_ok=True)
    rows = []
    for key, g in u.groupby("addr_key"):
        f = COLOR_DIR / (hashlib.sha1(key.encode()).hexdigest()[:14] + ".json")
        if f.exists():
            c = json.loads(f.read_text())
        else:
            c = places.color(float(g.lat.iloc[0]), float(g.lon.iloc[0]))
            f.write_text(json.dumps(c, default=str))
        r = {"addr_key": key}
        for sec, d in c.items():
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, dict) and "value" in v and not k.endswith("examples"):
                        try:
                            r[k] = float(v["value"])
                        except (TypeError, ValueError):
                            pass
        rows.append(r)
    return pd.DataFrame(rows).set_index("addr_key")


def main():
    u = pd.read_csv(DATA / "units.csv", low_memory=False)
    u = u[u.unit_status == "pass"].copy()
    G = pd.read_csv(DATA / "lifestyle_groups.csv").set_index("hood_id")
    gcols = ["group_key", "group_label", "group_subhead", "safety_cut", "safety_cut_reason", "newcomer_share", "age_25_34_share",
             "detached_house_share", "violent", "property", "motor_vehicle_theft", "violent_vs_jamaica", "property_vs_jamaica",
             "violent_vs_us", "violent_vs_metro", "violent_vs_local"]
    u = u.join(G[gcols], on="hood_id")
    n_cut = int(u.safety_cut.fillna(False).sum())
    u = u[~u.safety_cut.fillna(False)].copy()

    # ---- listing confidence
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)
    age = pd.to_numeric(u.get("listing_age_days"), errors="coerce")
    med = u.groupby("hood_id").all_in.transform("median")
    reasons = pd.Series("", index=u.index)
    for cond, why in [(age >= 60, "listing 60+ days old"), ((s("unit") == "") & (s("building_name") == ""), "no unit or building named"),
                      (s("notes").str.contains("listhub|propertyware", case=False), "thin syndicated feed"),
                      (s("notes").str.contains("CONFLICT"), "conflicting dog policy"), (u.all_in < 0.6 * med, "price far below the neighborhood")]:
        reasons = np.where(cond, reasons + why + "; ", reasons); reasons = pd.Series(reasons, index=u.index)
    inf_e = s("elevator_basis").str.startswith("inferred")
    inf_f = s("floor_asterisk").eq("yes")
    dog_small = s("dog_policy_text").str.contains(r"Size allowed: Small\)", case=False) & pd.to_numeric(u.get("dog_weight_limit_lb"), errors="coerce").isna()
    n_inf = inf_e.astype(int) + inf_f.astype(int) + dog_small.astype(int)
    u["to_confirm"] = (np.where(inf_e, "elevator (inferred from floor count); ", "") + pd.Series(np.where(inf_f, "which floor; ", ""), index=u.index)
                       + pd.Series(np.where(dog_small, "dog weight limit (page says small dogs); ", ""), index=u.index))
    u["confidence"] = np.where(reasons != "", "sketchy", np.where(n_inf == 0, "clean", np.where(n_inf == 1, "one_inferred", "sketchy")))
    u["sketchy_reason"] = np.where(reasons != "", reasons, np.where(n_inf >= 2, "two or more inferred gate facts", ""))
    u[u.confidence == "sketchy"].to_csv(DATA / "excluded_sketchy.csv", index=False)
    n_sk = int((u.confidence == "sketchy").sum())
    u = u[u.confidence != "sketchy"].copy()

    am = DATA / "reference" / "building_amenities.csv"
    A = pd.read_csv(am, dtype=str, keep_default_na=False).drop_duplicates("addr_key").set_index("addr_key") if am.exists() else pd.DataFrame()
    a = lambda col: (u.addr_key.map(A[col]) if col in A else pd.Series("", index=u.index)).fillna("").astype(str).str.lower()
    has = lambda col: ~a(col).isin(["", "no_mention", "nan", "unknown"])
    cm = lambda col: s("community_" + col).str.lower().str.contains("yes")
    C = color_table(u)
    u = u.join(C, on="addr_key", rsuffix="_color")
    n = lambda c: pd.to_numeric(u[c], errors="coerce") if c in u else pd.Series(np.nan, index=u.index)

    pool, cp = a("pool"), s("community_pool").str.lower()
    u["pool"] = np.where(pool.isin(["indoor", "both"]) | cp.str.contains("indoor"), "indoor",
                         np.where(pool.isin(["outdoor", "yes_type_unknown"]) | cp.str.contains("yes|outdoor"), "pool", ""))
    pr = u.parking_type.map(parking_rank).fillna(a("gated_or_garage_parking").map(parking_rank))
    u["parking_rank"] = pr
    doorman = a("doorman_or_concierge")
    laundry = (s("laundry") + " " + a("in_unit_laundry")).str.lower()
    near_car = n("near_veh_theft_24m") + n("near_theft_from_veh_24m").fillna(0)

    # points for building features (unknown = a quarter of the points)
    def pts(yes, known, w):
        return np.where(yes, w, np.where(known, 0.0, 0.25 * w))
    security = (pts(doorman.eq("24h"), has("doorman_or_concierge"), 3) + pts(doorman.isin(["yes", "part_time"]), has("doorman_or_concierge"), 2)
                + pts(has("controlled_access") | cm("controlled_access"), False, 2.5) + pts(has("package_room") | cm("package_room"), False, 1))
    comfort = (pts(laundry.str.contains("in unit|in_unit|in-unit|yes"), laundry.str.strip().ne(""), 2.5)
               + pts(has("gym") | cm("gym"), False, 1) + pts(has("roof_deck_or_outdoor_space"), False, 1) + pts(has("balcony_some_units"), False, 0.5)
               + pts(has("coworking_or_lounge"), False, 1.5) + pts(s("elevator_basis").eq("stated") | a("elevator_stated").eq("yes"), True, 1))
    year = pd.to_numeric(a("year_built").replace("", np.nan), errors="coerce").fillna(n("pluto_year"))
    u["building_security_pts"], u["building_comfort_pts"] = security, comfort

    # ---- parts
    u["p_safety"] = blend((pct(u.violent, False), 35), (pct(u.property, False), 15), (pct(u.motor_vehicle_theft, False), 15),
                          (pct(near_car, False), 15), (pct(pd.Series(security, index=u.index)), 20))
    u["p_building"] = blend((pct(pd.Series(security, index=u.index)), 40), (pct(pd.Series(comfort, index=u.index)), 45), (pct(year), 15))
    lines_known = s("all_in_lines").str.count('"found"')
    u["p_cost"] = blend((pct(u.all_in, False), 85), (pct(lines_known), 15))
    u["p_car"] = blend((pct(pr), 50), (pct(u.motor_vehicle_theft, False), 15), (pct(near_car, False), 15),
                       (pct(n("parking_fee"), False), 10), (pct(n("surface_parking_ha_within_800m")), 10))
    one_bed = (pd.to_numeric(u.beds, errors="coerce") >= 1).astype(float) * 100
    u["p_space"] = blend((pct(u.sqft), 75), (one_bed, 25))
    u["p_distance"] = blend((pct(u.drive_min_to, False), 60), (pct(u.transit_sat_median, False), 25), (pct(u.toll_rt_ezpass, False), 15))
    dog_small = dog_small.reindex(u.index).fillna(False)
    dogam = has("dog_amenities") | cm("dog_park_pet_spa")
    weight_ok = pd.to_numeric(u.get("dog_weight_limit_lb"), errors="coerce") >= 40
    u["p_dog"] = blend((pct(u.park_walk_min, False), 25), (pct(u.park_ha_800m), 15), (pct(u.dog_park_m, False), 15),
                       (pct(n("woods_ha_within_800m")), 5), (pct(n("vet_count_1600m")), 10), (pct(n("pet_count_1600m")), 5),
                       (pd.Series(np.where(dogam, 100, UNKNOWN_PCT), index=u.index), 10), (pct(u.pet_rent, False), 5),
                       (pd.Series(np.where(weight_ok, 100, np.where(dog_small, 10, UNKNOWN_PCT)), index=u.index), 10))
    u["p_daily"] = blend((pct(u.cafes_800m), 20), (pct(n("supermarket_m_c") if "supermarket_m_c" in u else n("supermarket_m"), False), 25),
                         (pct(n("gym_count_800m")), 15), (pct(n("library_count_1600m")), 5), (pct(n("market_count_1600m")), 10),
                         (pct(n("convenience_count_800m")), 10), (pct(u.motorway_m), 15))
    u["universal"] = sum(u[f"p_{k}"] * w for k, w in W.items()) / 100

    # ---- the year's promise (five to seven signature variables each)
    P = {
        "pre_car": blend((pct(u.restaurants_800m), 20), (pct(u.bars_800m), 15), (pct(u.cafes_800m), 15), (pct(n("shop_any_count_800m")), 15),
                         (pct(n("intersections_within_800m")), 15), (pct(n("cinema_theatre_count_1600m")), 10), (pct(n("bookshop_count_1600m")), 10)),
        "settled": blend((pct(n("convenience_count_800m")), 20), (pct(n("hair_beauty_count_800m")), 15), (pct(u.restaurants_800m), 15),
                         (pct(n("laundry_count_800m")), 10), (pct(n("library_count_1600m")), 10), (pct(u.transit_sat_median, False), 20),
                         (pct(n("playground_count_800m")), 10)),
        "new_water": blend((pct(pd.Series(comfort + security, index=u.index)), 25), (pct(u.open_water_m, False), 20), (pct(u.newcomer_share), 15),
                           (pct(u.age_25_34_share), 15), (pct(year), 10), (pct(n("gym_count_800m")), 5), (pct(u.bars_1600m), 10)),
        "middle": blend((pct(u.restaurants_800m), 25), (pct(n("train_station_m"), False), 20), (pct(n("cinema_theatre_count_1600m")), 15),
                        (pct(n("shop_any_count_800m")), 15), (pct(n("market_count_1600m")), 10), (pct(u.bars_1600m), 15)),
        "space": blend((pct(n("sqft") / n("all_in")), 40), (one_bed, 15), (pct(u.park_ha_800m), 15), (pct(pr), 15), (pct(n("woods_ha_within_800m")), 15)),
        "enclave": blend((pct(u.violent, False), 25), (pct(u.property, False), 15), (pct(u.motorway_m), 20), (pct(pr), 15),
                         (pct(n("woods_ha_within_800m")), 10), (pct(u.detached_house_share), 15)),
    }
    u["promise"] = 0.0
    for k, sc in P.items():
        m = u.group_key == k
        u.loc[m, "promise"] = sc[m]
    u["pool_bump"] = u.pool.map({"indoor": INDOOR_POOL_BUMP, "pool": POOL_BUMP}).fillna(0)
    u["certainty"] = u.confidence.map(CERTAINTY)
    u["rank_score"] = ((UNIVERSAL_SHARE * u.universal + PROMISE_SHARE * u.promise + u.pool_bump) * u.certainty).round(1)
    u = u.copy()

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
    #      1-2 = worse for her, 4-5 = better for her. Closer to her parents counts as better (Will, 2026-11-15).
    home = u[u.hood_area.astype(str).eq("Queens")]
    SPEC = {  # column, kind, small band, big band, higher_is_better (None = neutral: 1 much closer .. 5 much farther)
        "all_in": ("all_in", "abs", 75, 250, False), "sqft": ("sqft", "abs", 50, 150, True),
        "drive_min": ("drive_min_to", "abs", 5, 20, False), "transit_min": ("transit_sat_median", "abs", 10, 30, False),  # Will: closer to her parents is better
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
    home = u[u.hood_area.astype(str).eq("Queens")]
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
    print(f"kept {len(u)} units ({n_cut} cut by the Jamaica safety rule, {n_sk} dropped as sketchy); candidates {int(u.candidate.sum())}; shown {int(u.shown_pre_evidence.sum())}; pools: {u.pool.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
