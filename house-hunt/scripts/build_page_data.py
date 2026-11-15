"""Export the page's data contract: site/data.json (read by the page; nothing else feeds the UI).

Shape: meta, years[], neighborhoods[], units[] (shown), avoid[] (avoid cards), held[] (good candidates waiting on one
confirmation). Every number that appears on the page comes from data/ranked_units.csv (which reads only the master
tables) and data/lifestyle_groups.csv. Unknown values are null; the page must show "Not known yet", never a guess.
"""
import json, sys, re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT


def v(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return round(float(x), 2)
    s = str(x)
    return None if s in ("", "nan", "NaN") else x


def j(x, default):
    try:
        return json.loads(x) if isinstance(x, str) and x else default
    except ValueError:
        return default


def unit(r):
    g = lambda c: v(r.get(c))
    qs = [q for q in str(g("to_confirm") or "").split("; ") if q]
    if g("tour_confirm"):
        qs.append(str(g("tour_confirm")) + f" (floor {int(float(g('unit_floor')))} is read from the unit number {g('unit')})")
    if g("rent_needs_call") == "yes":
        qs.append("Is the advertised rent the full monthly rent, or the average after free months? What is the first full payment and when is it due?")
    for line in str(g("all_in_unknown_lines") or "").split("; "):
        if line:
            qs.append({"parking fee": "What does a parking spot cost per month, and is one guaranteed in the lease?", "pet rent": "What is the monthly pet rent and any one-time pet fee?",
                       "building fees": "What required monthly fees are added to the rent (amenity, trash, technology)?",
                       "building fees (part)": "Which required monthly fees have no published amount (for example an amenity fee), and how much are they?", "gas": "Who pays for heat and cooking gas?"}.get(line, f"What is the {line}?"))
    return {
        "id": g("listing_id"), "building_id": g("building_id"), "hood_id": g("hood_id"), "year": g("group_key"),
        "building": g("building_name"), "address": g("address"), "unit": g("unit"), "beds": g("beds"), "sqft": g("sqft"),
        "floor": g("unit_floor"), "floor_basis": g("unit_floor_basis"), "floor_basis_note": g("floor_basis_note"), "zip": g("zip5"), "lat": g("lat"), "lon": g("lon"),
        "available": g("available_date"), "listing_age_days": g("listing_age_days"),
        "rent": {"listed": g("listed_rent"), "basis": g("rent_basis"), "basis_kind": g("rent_basis_kind"), "gross": g("rent_gross"),
                 "asterisk": g("rent_asterisk") == "yes", "offer_text": g("rent_offer_text"), "free_months": g("rent_free_months"),
                 "lease_months": g("rent_lease_months"), "first_full_payment_date": g("rent_first_full_payment_date"),
                 "first_full_payment_note": g("rent_first_full_payment_note"), "needs_call": g("rent_needs_call") == "yes"},
        "all_in": g("all_in"), "all_in_gross": g("all_in_gross"), "all_in_lines": j(r.get("all_in_lines"), []),
        "all_in_unknown": [x for x in str(g("all_in_unknown_lines") or "").split("; ") if x],
        "elevator": {"value": g("elevator"), "basis": g("elevator_basis")},
        "dog": {"allowed": g("dogs_allowed"), "basis": g("dogs_allowed_basis"), "weight_limit_lb": g("dog_weight_limit_lb"), "size_only_note": g("dog_size_only"), "policy_text": g("dog_policy_text"), "pet_rent": g("pet_rent")},
        "parking": {"type": g("parking_type"), "rank": g("parking_rank"), "fee": g("parking_fee"), "fee_note": g("parking_fee_note"), "options_text": g("parking_options")},
        "amenities": {"pool": g("pool") or None, "pool_text": g("pool_text"), "doorman": g("doorman") or None, "doorman_text": g("doorman_text"), "controlled_access": g("controlled_access"),
                      "gym": g("gym"), "in_unit_laundry": g("in_unit_laundry"), "laundry": g("laundry"), "package_room": g("package_room"),
                      "outdoor_space": g("outdoor_space"), "lounge_or_coworking": g("lounge_or_coworking"), "dog_amenities": g("dog_amenities"),
                      "year_built": g("year_built"), "building_floors": g("building_floors"), "manager": g("manager")},
        "moments": {
            "wake": {"park": g("park_name"), "park_walk_min": g("park_walk_min"), "dog_park": g("dog_park_name"), "dog_park_m": g("dog_park_m"), "woods_ha_800m": g("woods_ha_within_800m")},
            "work": {"sqft": g("sqft"), "separate_bedroom": (g("beds") or 0) >= 1, "cafes_800m": g("cafes_800m"), "gyms_800m": g("gym_count_800m"), "supermarket": g("supermarket"),
                     "supermarket_m": g("supermarket_m"), "library_1600m": g("library_count_1600m"), "motorway_m": g("motorway_m"), "fiber": None},
            "after": {"restaurants_800m": g("restaurants_800m"), "bars_800m": g("bars_800m"), "cafes_800m": g("cafes_800m"), "cinema_theatre_1600m": g("cinema_theatre_count_1600m"),
                      "bookshops_1600m": g("bookshop_count_1600m"), "markets_1600m": g("market_count_1600m"), "shops_800m": g("shop_any_count_800m")},
            "night": {"parking_type": g("parking_type"), "doorman": g("doorman"), "controlled_access": g("controlled_access"),
                      "violent_per_1000": g("violent"), "violent_vs_jamaica": g("violent_vs_jamaica"), "near_violent_250m_24m": g("near_violent_250m_24m"),
                      "near_violent_evening_250m_24m": g("near_violent_evening_250m_24m"), "car_crime_250m_24m": (g("near_veh_theft_24m") or 0) + (g("near_theft_from_veh_24m") or 0) if g("near_veh_theft_24m") is not None else None,
                      "vehicle_theft_per_1000": g("motor_vehicle_theft"), "police": g("police_agency"), "police_geography": g("police_geography")},
            "sat": {"bars_1600m": g("bars_1600m"), "music_1600m": g("music_1600m"), "restaurants_1600m": g("restaurants_1600m"), "parking_type": g("parking_type"), "train_station": g("train_station"), "train_station_m": g("train_station_m")},
            "sun": {"drive_min": g("drive_min_to"), "drive_miles": g("drive_miles"), "drive_basis": "free-flow estimate, no traffic", "toll_round_trip": g("toll_rt_ezpass"),
                    "toll_complete": str(g("toll_complete")) == "True", "toll_items": g("toll_items"), "transit_min": g("transit_sat_median"), "transit_transfers": g("transit_sat_transfers"),
                    "transit_summary": g("transit_sat_summary"), "last_train_home_sat": g("transit_last_sat_departure_from_jamaica"), "sunday_return_min": g("transit_sun_return_median")}},
        "scores": {"rank": g("rank_score"), "universal": g("universal"), "promise": g("promise"), "pool_bump": g("pool_bump"), "hood_rank": g("shown_rank") or g("hood_rank"),
                   "parts": {k: g("p_" + k) for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily"]},
                   "in_year": {k: g(k + "_in_year") for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily", "rank_score"]},
                   "overall": {k: g(k + "_overall") for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily", "rank_score"]}},
        "vs_queens": {k[4:]: g(k) for k in r.index if k.startswith("vsq_") and not k.endswith("_diff")},
        "vs_queens_diff": {k[4:-5]: g(k) for k in r.index if k.startswith("vsq_") and k.endswith("_diff")},
        "evidence": {"checked": bool(r.get("evidence_checked")), "avoid": g("ev_avoid") == "yes", "avoid_reasons": g("ev_reasons"), "pause_notes": g("ev_pause_notes"),
                     "items": j(r.get("ev_evidence_json"), []), "positive": j(r.get("ev_positive_json"), [])},
        "confidence": g("confidence"), "tour_questions": qs,
        "links": {"listing": g("url"), "building": g("building_url")}, "source_site": g("source_site"),
        "live": {"status": g("live_status"), "checked_at": g("live_checked_at")}, "price_seen_at": g("last_seen"),
    }


def main():
    R = pd.read_csv(DATA / "ranked_units.csv", low_memory=False, dtype={"zip5": str})
    G = pd.read_csv(DATA / "lifestyle_groups.csv").set_index("hood_id")
    E = pd.read_csv(DATA / "group_exchange.csv")
    held_ids = set(pd.read_csv(DATA / "needs_confirmation.csv").listing_id) if (DATA / "needs_confirmation.csv").exists() else set()
    shown, avoid, held = R[R.shown], R[R.avoid_card], R[R.listing_id.isin(held_ids)]
    # clean candidates that the evidence pass has not seen live yet: listed for the evidence agents, never shown as places
    live_ids = set(pd.read_csv(DATA / "needs_live_check.csv").listing_id) if (DATA / "needs_live_check.csv").exists() else set()
    awaiting = R[R.listing_id.isin(live_ids)]
    hoods = []
    for hid, g in R.groupby("hood_id"):
        s = g[g.shown]
        if not len(s) and not len(g[g.avoid_card]):
            continue
        h = G.loc[hid] if hid in G.index else {}
        num = lambda c: v(pd.to_numeric(g[c], errors="coerce").median()) if c in g else None
        hoods.append({"id": hid, "name": g.hood.iloc[0], "area": v(g.hood_area.iloc[0]), "state": v(g.state.iloc[0]) if "state" in g else None, "year": g.group_key.iloc[0],
                      "lat": v(pd.to_numeric(g.lat, errors="coerce").mean()), "lon": v(pd.to_numeric(g.lon, errors="coerce").mean()),
                      "counts": {"shown": int(len(s)), "avoid": int(g.avoid_card.sum()), "held": int(g.listing_id.isin(held_ids).sum()), "ranked": int(len(g))},
                      "all_in_range": [v(s.all_in.min()), v(s.all_in.max())] if len(s) else None, "sqft_median": num("sqft"),
                      "drive_min": num("drive_min_to"), "transit_min": num("transit_sat_median"), "toll_round_trip": num("toll_rt_ezpass"),
                      "safety": {"violent_per_1000": v(h.get("violent")), "property_per_1000": v(h.get("property")), "vehicle_theft_per_1000": v(h.get("motor_vehicle_theft")),
                                 "vs_jamaica": v(h.get("violent_vs_jamaica")), "property_vs_jamaica": v(h.get("property_vs_jamaica")), "vs_us": v(h.get("violent_vs_us")),
                                 "vs_metro": v(h.get("violent_vs_metro")), "vs_local": v(h.get("violent_vs_local")), "police": v(h.get("police")), "geography": v(h.get("geography")), "year": v(h.get("crime_year"))},
                      "traits": {k: v(h.get(k)) for k in ["no_car_share", "age_25_34_share", "living_alone_share", "households_with_kids_share", "college_degree_share", "newcomer_share",
                                                          "wfh_share", "median_hh_income", "detached_house_share", "built_since_2010_share", "built_before_1940_share", "restaurants_800m",
                                                          "bars_800m", "cafes_800m", "park_ha_800m", "park_walk_min", "open_water_m", "dog_park_m", "supermarket_m_c"]},
                      "vs_queens": {k[4:]: v(pd.to_numeric(g[k], errors="coerce").median()) for k in g.columns if k.startswith("vsq_") and not k.endswith("_diff")},
                      "unit_ids": list(s.sort_values("shown_rank").listing_id), "avoid_ids": list(g[g.avoid_card].listing_id),
                      "local": {"parking_rules": None, "dog_rules": None, "voices": []}})
    years = []
    for key, g in R.groupby("group_key"):
        s = g[g.shown]
        ex = E[E.group == g.group_label.iloc[0]]
        years.append({"id": key, "label": g.group_label.iloc[0], "subhead": g.group_subhead.iloc[0],
                      "counts": {"neighborhoods": int(s.hood_id.nunique()), "shown": int(len(s)), "avoid": int(g.avoid_card.sum())},
                      "all_in_range": [v(s.all_in.min()), v(s.all_in.max())] if len(s) else None,
                      "drive_min_range": [v(s.drive_min_to.min()), v(s.drive_min_to.max())] if len(s) else None,
                      "medians": {k: v(ex[k].iloc[0]) for k in ["all_in", "sqft", "drive_min", "transit_min", "toll_round_trip", "violent_per_1000", "property_per_1000", "restaurants_800m", "park_walk_min"] if len(ex) and k in ex},
                      "vs_queens": {k[4:]: v(ex[k].iloc[0]) for k in ex.columns if k.startswith("vsq_")} if len(ex) else {},
                      "vs_queens_diff": {k[:-8]: v(ex[k].iloc[0]) for k in ex.columns if k.endswith("_vs_home")} if len(ex) else {},
                      "hood_ids": [h["id"] for h in sorted([h for h in hoods if h["year"] == key and h["counts"]["shown"]], key=lambda h: h["drive_min"] or 999)],
                      "catch": None, "scenes": None})
    spec = pd.read_csv(DATA / "reference" / "queens_spectrum_definition.csv").to_dict("records")
    out = {"meta": {"built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "cap_all_in": 3000, "move_in_window": "now to 2026-12-15",
                    "anchor": {"name": "Mom and Dad (Jamaica station)", "lat": 40.699608, "lon": -73.808530},
                    "jamaica_yardstick": {"violent_per_1000": v(G.jamaica_violent.iloc[0]), "property_per_1000": v(G.jamaica_property.iloc[0])},
                    "queens_spectrum": spec, "weights": {"safety": 22, "building": 16, "cost": 12, "car": 12, "space": 12, "distance": 10, "dog": 8, "daily": 8},
                    "counts": {"shown": int(len(shown)), "avoid": int(len(avoid)), "held": int(len(held)), "awaiting_live_check": int(len(awaiting)), "ranked": int(len(R))},
                    "notes": ["Drive times are free-flow estimates without traffic.", "An asterisk on rent means a special offer applies; see the rent terms.",
                              "A floor marked 'read from the unit number' is not stated on the page; confirm it on the tour.",
                              "A place is shown only after its listing was seen live in the evidence pass.",
                              "Unknown cost lines count as $0 and are named on each receipt."]},
           "years": years, "neighborhoods": hoods, "units": [unit(r) for _, r in shown.iterrows()],
           "avoid": [unit(r) for _, r in avoid.iterrows()], "held": [unit(r) for _, r in held.iterrows()],
           "awaiting_live_check": [{"id": r.listing_id, "building": v(r.building_name), "address": v(r.address), "unit": v(r.unit), "hood_id": r.hood_id,
                                    "rank": v(r.rank_score), "all_in": v(r.all_in), "listing": v(r.url)} for r in awaiting.itertuples()]}
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site" / "data.json").write_text(json.dumps(out, default=str, allow_nan=False))
    print(f"site/data.json: {len(out['years'])} years, {len(hoods)} neighborhoods, {len(out['units'])} shown, {len(out['avoid'])} avoid, {len(out['held'])} held; {(ROOT / 'site' / 'data.json').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
