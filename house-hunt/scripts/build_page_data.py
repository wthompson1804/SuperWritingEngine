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
import parsers
import build_neighborhoods as BN

PARENTS = BN.subcity_parents()          # child hood_id -> its city (Jersey City is split into neighborhoods)
ROUTE = lambda hid, source_area="": BN.route_to_children(hid, source_area, PARENTS)


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


# Day moments: a three-level rating per moment (strong / mixed / weak; None = the data cannot say, no chip).
# Owner, 2026-11-16: the levels are ABSOLUTE thresholds on each moment's own measure, not a scale against staying in
# Queens (that scale made Sunday "weak" almost everywhere, which says nothing). They are set so that across the shown
# places no level holds more than about 60 percent for any moment; scripts/test_rules.py --data checks that.
MOMENT_THRESHOLDS = {
    "wake": {"measure": "minutes on foot to the nearest green space (park_walk_min)", "strong": "3 minutes or less", "mixed": "over 3 and up to 10 minutes", "weak": "more than 10 minutes"},
    "work": {"measure": "room for a work day at home: size and a separate bedroom", "strong": "a separate bedroom and 700 sq ft or more",
             "mixed": "everything between", "weak": "under 550 sq ft, or a studio under 600 sq ft", "null": "size not published"},
    "after": {"measure": "restaurants and bars within a 10-minute walk (800 m)", "strong": "15 or more restaurants and at least one bar", "mixed": "4 or more restaurants", "weak": "fewer than 4 restaurants"},
    "night": {"measure": "where the car sleeps", "strong": "a garage or gated parking at the building AND a front desk or controlled entry is stated",
              "mixed": "a garage with no stated front desk or controlled entry, covered parking, a lot, off-site parking, or parking not known",
              "weak": "street parking only, or the town restricts overnight street parking and no space at the building is confirmed"},
    "sat": {"measure": "bars and restaurants within 1,600 m", "strong": "5 or more bars and 30 or more restaurants", "mixed": "everything between", "weak": "at most 1 bar and fewer than 15 restaurants"},
    "sun": {"measure": "drive to her parents, one way, free-flow estimate (drive_min)", "strong": "30 minutes or less", "mixed": "31 to 60 minutes", "weak": "more than 60 minutes"},
}


def moment_ratings(m, parking_rank=None, offsite=False, secured=False, overnight_restricted=False, sqft=None, beds=None):
    f = lambda x: None if x is None or x != x else float(x)
    out = {}
    w = f(m["wake"].get("park_walk_min"))
    out["wake"] = None if w is None else ("strong" if w <= 3 else ("weak" if w > 10 else "mixed"))
    sq, bed = f(sqft), (f(beds) or 0) >= 1
    out["work"] = None if sq is None else ("strong" if bed and sq >= 700 else ("weak" if (sq < 550 or (not bed and sq < 600)) else "mixed"))
    r, b = f(m["after"].get("restaurants_800m")), f(m["after"].get("bars_800m"))
    out["after"] = None if r is None else ("strong" if (r >= 15 and (b or 0) >= 1) else ("weak" if r < 4 else "mixed"))
    pr = f(parking_rank)
    if pr == 1 or overnight_restricted:
        out["night"] = "weak"
    elif pr == 4 and not offsite and secured:
        out["night"] = "strong"
    else:
        out["night"] = "mixed"                    # parking unknown is "mixed" by the owner's rule, not null
    bs, rs = f(m["sat"].get("bars_1600m")), f(m["sat"].get("restaurants_1600m"))
    out["sat"] = None if bs is None or rs is None else ("strong" if (bs >= 5 and rs >= 30) else ("weak" if (bs <= 1 and rs < 15) else "mixed"))
    d = f(m["sun"].get("drive_min")) if "sun" in m else None
    out["sun"] = None if d is None else ("strong" if d <= 30 else ("weak" if d > 60 else "mixed"))
    return out


PUBLIC_EVIDENCE = {}  # building_id -> what the evidence pass could read (data/avoid_buildings.csv: public_evidence); filled in main()


def unit(r):
    g = lambda c: v(r.get(c))
    qs = [q for q in str(g("to_confirm") or "").split("; ") if q]
    for q in str(g("tour_confirm") or "").split("; "):
        if q.startswith("Confirm the floor"):
            qs.append(q + f" (floor {int(float(g('unit_floor')))} is read from the unit number {g('unit')})")
        elif q:
            qs.append(q + ((" (the page says small dogs and gives no number)" if g("dog_size_note") else " (the page says weight restrictions apply and gives no number)") if "dog weight" in q else ""))
    if g("rent_needs_call") == "yes":
        qs.append("Is the advertised rent the full monthly rent, or the average after free months? What is the first full payment and when is it due?")
    for line in str(g("all_in_unknown_lines") or "").split("; "):
        if line:
            qs.append({"parking fee": "What does a parking spot cost per month, and is one guaranteed in the lease?", "pet rent": "What is the monthly pet rent and any one-time pet fee?",
                       "building fees": "What required monthly fees are added to the rent (amenity, trash, technology)?",
                       "building fees (part)": "Which required monthly fees have no published amount (for example an amenity fee), and how much are they?", "gas": "Who pays for heat and cooking gas?"}.get(line, f"What is the {line}?"))
    if "pet rent" in str(g("all_in_estimated_lines") or ""):
        qs.append("What is the monthly pet rent and any one-time pet fee? (the figure in the cost is an estimate)")
    qs = list(dict.fromkeys(qs))
    out = unit_core(r, g, qs)
    am = out["amenities"]
    mr = moment_ratings(out["moments"], g("parking_rank"), out["parking"]["offsite"],
                        secured=bool(am["doorman"]) or str(am["controlled_access"] or "").strip().lower().startswith(("yes", "true")),
                        overnight_restricted=any(d["what"] == "overnight street parking" for d in out["disclosures"]), sqft=g("sqft"), beds=g("beds"))
    for k, val in mr.items():
        out["moments"][k]["rating"] = val
    return out


def unit_core(r, g, qs):
    return {
        "id": g("listing_id"), "building_id": g("building_id"), "hood_id": g("hood_id"), "year": g("group_key"),
        "building": g("building_name"), "address": g("address"), "unit": g("unit"), "kind": g("listing_kind") or "unit", "beds": g("beds"), "sqft": g("sqft"),
        "floor": g("unit_floor"), "floor_basis": g("unit_floor_basis"), "floor_basis_note": g("floor_basis_note"), "zip": g("zip5"), "lat": g("lat"), "lon": g("lon"),
        "available": g("available_date"), "listing_age_days": g("listing_age_days"),
        "rent": {"listed": g("listed_rent"), "basis": g("rent_basis"), "basis_kind": g("rent_basis_kind"), "gross": g("rent_gross"),
                 "asterisk": g("rent_asterisk") == "yes", "offer_text": g("rent_offer_text"), "offer_kind": g("rent_offer_kind"), "free_months": g("rent_free_months"),
                 "lease_months": g("rent_lease_months"), "first_full_payment_date": g("rent_first_full_payment_date"),
                 "first_full_payment_note": g("rent_first_full_payment_note"), "needs_call": g("rent_needs_call") == "yes"},
        "all_in": g("all_in"), "all_in_gross": g("all_in_gross"), "all_in_lines": j(r.get("all_in_lines"), []),
        "all_in_unknown": [x for x in str(g("all_in_unknown_lines") or "").split("; ") if x],
        # owner, 2026-11-16: all_in plus the median known parking fee and required fees for the lines not published here.
        # Never used for the cap. unknown_cost_lines names the parking / fee lines that are not published.
        "all_in_likely": g("all_in_likely"), "all_in_likely_note": g("all_in_likely_note"),
        "unknown_cost_lines": [{"parking fee": "parking", "building fees": "required fees", "building fees (part)": "some required fees"}.get(x, x)
                               for x in str(g("all_in_unknown_lines") or "").split("; ") if x],
        "estimated_cost_lines": [x for x in str(g("all_in_estimated_lines") or "").split("; ") if x],
        "elevator": {"value": g("elevator"), "basis": g("elevator_basis"), "listing_site_only": g("elevator_aggregator_only") == "yes"},
        "dog": {"allowed": g("dogs_allowed"), "basis": g("dogs_allowed_basis"), "weight_limit_lb": g("dog_weight_limit_lb"), "size_note": g("dog_size_note"), "size_only_source": g("dog_size_only"), "policy_text": g("dog_policy_text"), "pet_rent": g("pet_rent")},
        "parking": {"type": g("parking_type"), "rank": g("parking_rank"), "fee": g("parking_fee"), "fee_note": g("parking_fee_note"), "options_text": g("parking_options"),
                    # D10: parking that is not at the building ("2 blocks away") is never "covered parking" on the page
                    "offsite": bool(parsers.OFFSITE_PARKING.search(str(g("parking_type") or "")))},
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
            "sun": {"drive_min": g("drive_min_to"), "drive_miles": g("drive_miles"), "drive_basis": "free-flow estimate, no traffic",
                    # null when a crossing on the route has no rate (never 0 for unknown); NY E-ZPass, with the mail rate beside it
                    "toll_round_trip": parsers.toll_known(g("toll_rt_ezpass"), g("toll_complete")),
                    "toll_round_trip_mail": parsers.toll_known(g("toll_rt_mail"), g("toll_complete")), "toll_basis": "New York E-ZPass, weekend off-peak",
                    # where one crossing has no published mail rate the mail figure is null: the sum of the known crossings is a floor
                    "toll_round_trip_mail_at_least": g("toll_rt_mail_subtotal") if g("toll_rt_mail") is None else None, "toll_mail_note": g("toll_rt_mail_note"),
                    "toll_complete": str(g("toll_complete")) == "True", "toll_items": g("toll_items"), "transit_min": g("transit_sat_median"), "transit_transfers": g("transit_sat_transfers"),
                    "transit_summary": g("transit_sat_summary"), "last_train_home_sat": g("transit_last_sat_departure_from_jamaica"), "sunday_return_min": g("transit_sun_return_median")}},
        "scores": {"rank": g("rank_score"), "universal": g("universal"), "promise": g("promise"), "pool_bump": g("pool_bump"), "hood_rank": g("shown_rank") or g("hood_rank"),
                   "parts": {k: g("p_" + k) for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily"]},
                   "in_year": {k: g(k + "_in_year") for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily", "rank_score"]},
                   "overall": {k: g(k + "_overall") for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily", "rank_score"]}},
        "vs_queens": {k[4:]: g(k) for k in r.index if k.startswith("vsq_") and not k.endswith("_diff")},
        "vs_queens_diff": {k[4:-5]: g(k) for k in r.index if k.startswith("vsq_") and k.endswith("_diff")},
        "evidence": {"checked": bool(r.get("evidence_checked")), "avoid": g("ev_avoid") == "yes", "avoid_reasons": g("ev_reasons"), "pause_notes": g("ev_pause_notes"),
                     "items": j(r.get("ev_evidence_json"), []), "positive": j(r.get("ev_positive_json"), []),
                     # display field for the page: "NYC records", "rating screen: <verdict>", "none readable", or null when the building was not in the evidence pass
                     "public_evidence": PUBLIC_EVIDENCE.get(g("building_id"))},
        "confirm": {"asterisk": g("confirm_asterisk") == "yes", "what": g("confirm_what") if g("confirm_asterisk") == "yes" else None,
                    "why": g("confirm_why") if g("confirm_asterisk") == "yes" else None,
                    # the question to ask, in the reviewer's or the rule's words (independent check 2)
                    "question": (qs[0] if qs else None) if g("confirm_asterisk") == "yes" else None,
                    "reviewed": g("review_verdict")},
        # conditions to know that are not open gate facts (owner, 2026-11-16): lease term, cost near the cap, condo rented by
        # its owner, net-effective rent. Any number may sit beside at most one open gate fact (confirm).
        "disclosures": [{"what": d.get("what"), "why": d.get("why"), "question": d.get("question") or None, "url": d.get("url") or None, "severity": d.get("severity") or None}
                        for d in j(r.get("disclosures"), [])],
        "more_in_building": g("more_in_building"), "rank_in_building": g("nth_shown_in_building"),
        "cost_check": {"cap_margin": g("cap_margin"), "unknown_count": g("all_in_unknown_count"), "lease_term_months": g("rent_lease_term_months"), "price_12_month": g("rent_12_month_price")},
        "confidence": g("confidence"), "tour_questions": qs,
        "links": {"listing": g("url"), "building": g("building_url")}, "source_site": g("source_site"),
        "live": {"status": g("live_status"), "checked_at": g("live_checked_at")}, "price_seen_at": g("last_seen"),
    }


BUILDINGS = []


def buildings(shown):
    """One entry per building with a shown unit (owner, 2026-11-16: the page groups apartments under their building).
    unit_ids are in rank order (the same score as everywhere); rank_in_neighborhood orders buildings by their best unit.
    Shared facts are the building's merged facts (they are the same on every unit row); ratings stay on the units."""
    out = []
    for b, g in shown.sort_values(["hood_id", "shown_rank"]).groupby("building_id", sort=False):
        r0 = g.iloc[0]
        g0 = lambda c: v(r0.get(c))
        u0 = unit(r0)
        ex = pd.to_numeric(g.all_in, errors="coerce")
        likely = pd.to_numeric(g.all_in_likely, errors="coerce") if "all_in_likely" in g else ex
        out.append({"id": b, "name": g0("building_name"), "address": g0("address"), "city": g0("city"), "state": g0("state"), "zip": g0("zip5"),
                    "hood_id": g0("hood_id"), "experience": g0("group_key"), "lat": g0("lat"), "lon": g0("lon"),
                    "unit_ids": list(g.listing_id), "n_units": int(len(g)), "more_showable_not_shown": int(g0("more_in_building") or 0),
                    "from_all_in": v(ex.min()), "to_all_in": v(ex.max()), "from_all_in_likely": v(likely.min()),
                    "best_unit_id": r0.listing_id, "best_rank_score": g0("rank_score"), "best_shown_rank": int(r0.shown_rank),
                    # some units of one building can differ in address (EDGE: two buildings leased together)
                    "addresses": sorted(set(str(a) for a in g.address.dropna())),
                    "elevator": u0["elevator"], "dogs": u0["dog"], "parking": u0["parking"], "amenities": u0["amenities"],
                    "links": {"building": g0("building_url")}, "manager": g0("manager"),
                    "open_items": sorted(set(x for w in g.confirm_what.dropna().astype(str) for x in w.split("; ") if x and x != "nan")),
                    "units_with_asterisk": int((g.confirm_asterisk == "yes").sum())})
    by_h = {}
    for e in sorted(out, key=lambda e: (e["hood_id"], e["best_shown_rank"])):
        by_h[e["hood_id"]] = by_h.get(e["hood_id"], 0) + 1
        e["rank_in_neighborhood"] = by_h[e["hood_id"]]
    return out


def main():
    R = pd.read_csv(DATA / "ranked_units.csv", low_memory=False, dtype={"zip5": str})
    G = pd.read_csv(DATA / "lifestyle_groups.csv").set_index("hood_id")
    E = pd.read_csv(DATA / "group_exchange.csv")
    # same join as scripts/rank.py (address key -> building id, avoid rows first), carrying the one column rank.py leaves behind
    af, xwf = DATA / "avoid_buildings.csv", DATA / "reference" / "building_crosswalk.csv"
    if af.exists() and xwf.exists():
        AV = pd.read_csv(af, dtype=str, keep_default_na=False)
        if "public_evidence" in AV:
            AV["building_id"] = AV.addr_key.map(pd.read_csv(xwf, dtype=str).set_index("addr_key").building_id)
            AV = AV.dropna(subset=["building_id"]).sort_values("avoid", ascending=False).drop_duplicates("building_id")
            PUBLIC_EVIDENCE.update({b: (e or None) for b, e in zip(AV.building_id, AV.public_evidence)})
    held_ids = set(pd.read_csv(DATA / "needs_confirmation.csv").listing_id) if (DATA / "needs_confirmation.csv").exists() else set()
    shown, avoid, held = R[R.shown], R[R.avoid_card], R[R.listing_id.isin(held_ids) & ~R.shown]
    # Owner, 2026-11-16 ("Forget call check"): a listing never re-read is not an open item, so there is no "awaiting a live
    # check" list any more. The key stays in the page data as an EMPTY array (and the count as 0) so the page does not break.
    awaiting = R.iloc[0:0]
    # local rules (street parking, dogs) and resident voices, keyed by neighborhood
    local, voices, survey = {}, {}, {}
    lr = DATA / "reference" / "local_rules.csv"
    if lr.exists():
        LR = pd.read_csv(lr, dtype=str, keep_default_na=False)
        for r in LR[LR.value_type == "found"].itertuples():
            for hid0 in [h.strip() for h in r.applies_to_hood_ids.split(";") if h.strip()]:
                for hid, about in ROUTE(hid0):         # a city's law applies in each of its neighborhoods; it says so
                    local.setdefault(hid, {"street_parking": [], "dogs": []}).setdefault(r.topic, []).append(
                        {"rule": r.rule, "summary": r.summary, "quote": r.quote, "url": r.source_url, "municipality": r.municipality, "about": about})
    vq = DATA / "voices" / "neighborhood_quotes.csv"
    if vq.exists():
        VQ = pd.read_csv(vq, dtype=str, keep_default_na=False)
        if "verified" in VQ:
            VQ = VQ[VQ.verified.str.lower().isin(["true", "yes", "1"])]
        # independent check 2, D20: quotes dropped by decision (wrong municipality; a writer named by office)
        qx = DATA / "voices" / "quote_exclusions.csv"
        QX = [(r.hood_id, r.excerpt_starts_with) for r in pd.read_csv(qx, dtype=str, keep_default_na=False).itertuples()] if qx.exists() else []

        def area_key(t):
            t = re.sub(r",\s*[A-Z]{2}$", "", str(t).strip())
            return re.sub(r"\b(township|city of|city|town|village|borough)\b|\(.*?\)|[^a-z]", "", t.lower())
        for r in VQ.itertuples():
            if any(r.hood_id == h and r.excerpt.startswith(x) for h, x in QX) or parsers.characterises_residents_by_group(r.excerpt):
                continue                              # D24: also any quote that characterises residents by ethnicity, race or religion
            # D20: keep source_area. A quote about a wider or different area than the neighborhood it is filed under
            # says so ("about Corona" under North Corona). Thread titles used as an area name are not shown.
            sa = getattr(r, "source_area", "")
            about = re.sub(r",\s*[A-Z]{2}$", "", sa) if sa and len(sa) <= 40 and area_key(sa) != area_key(r.neighborhood) else None
            for hid, whole in ROUTE(r.hood_id, sa):    # a citywide quote is shown on each neighborhood of a split city, labelled
                voices.setdefault(hid, []).append({"excerpt": r.excerpt, "theme": r.theme, "sentiment": r.sentiment, "context": r.speaker_context,
                                                   "source": r.source_site, "date": r.post_date, "url": r.permalink, "source_area": sa or None, "about": whole or about})
    vs = DATA / "voices" / "neighborhood_survey.csv"
    if vs.exists():
        for r in pd.read_csv(vs, dtype=str, keep_default_na=False).itertuples():
            for hid, whole in ROUTE(r.hood_id, getattr(r, "source_area", "")):   # "Journal Square, Jersey City" rows go to Journal Square only
                survey.setdefault(hid, []).append({"measure": r.measure, "value": r.value, "source": r.source_site, "as_of": r.as_of, "url": r.source_url,
                                                   "source_area": getattr(r, "source_area", "") or None, "about": whole})
    # sub-city crime context for a split city: a labelled estimate, shown beside the citywide police rate, never used by the safety rule
    sub_crime = {}
    scf = DATA / "reference" / "subcity_crime_jersey_city.csv"
    if scf.exists():
        for r in pd.read_csv(scf).itertuples():
            sub_crime[r.hood_id] = {"label": "10-month estimate from the city's incident portal, not an official rate", "value_type": "estimate", "used_for_safety_rule": False,
                                    "violent_per_1000_scaled": v(r.violent_per_1000_scaled_to_fbi_2025), "property_per_1000_scaled": v(r.property_per_1000_scaled_to_fbi_2025),
                                    "violent_ratio_to_city": v(r.violent_ratio_to_city_portal), "property_ratio_to_city": v(r.property_ratio_to_city_portal),
                                    "window": r.window, "method": r.method, "source_url": r.source_url}
    MEAS = [("all_in", "all_in"), ("sqft", "sqft"), ("drive_min", "drive_min_to"), ("transit_min", "transit_sat_median"), ("toll_round_trip", "toll_rt_known"),
            ("toll_round_trip_mail", "toll_rt_mail"), ("violent_per_1000", "violent"), ("property_per_1000", "property"), ("restaurants_800m", "restaurants_800m"),
            ("park_walk_min", "park_walk_min"), ("parking_rank", "parking_rank")]
    HOME = shown[shown.hood_area.astype(str).eq("Queens")]
    BUILDINGS.clear()
    BUILDINGS.extend(buildings(shown))
    hoods = []
    for hid, g in R.groupby("hood_id"):
        s = g[g.shown]
        if not len(s) and not len(g[g.avoid_card]):
            continue
        if not len(s) and "thin_neighborhood" in g and g.thin_neighborhood.astype(str).eq("True").any():
            continue            # owner, 2026-11-16: a neighborhood cut by the thin-neighborhood rule does not appear on the page
        h = G.loc[hid] if hid in G.index else {}
        # independent check 3, D12: figures describe the SHOWN places (a neighborhood with only avoid cards uses its ranked units)
        g_all, g = g, (s if len(s) else g)
        num = lambda c: v(pd.to_numeric(g[c], errors="coerce").median()) if c in g else None
        # null unless every route in the neighborhood has a complete toll (never 0 for unknown)
        tollmed = lambda c: v(pd.Series([parsers.toll_known(a, b) for a, b in zip(g[c], g.toll_complete)], dtype=float).median()) \
            if c in g and g.toll_complete.astype(str).str.lower().eq("true").all() else None
        bl = [b_ for b_ in BUILDINGS if b_["hood_id"] == hid]
        hoods.append({"id": hid, "name": g.hood.iloc[0], "area": v(g.hood_area.iloc[0]), "state": v(g.state.iloc[0]) if "state" in g else None, "year": g.group_key.iloc[0],
                      "lat": v(pd.to_numeric(g.lat, errors="coerce").mean()), "lon": v(pd.to_numeric(g.lon, errors="coerce").mean()),
                      "counts": {"shown": int(len(s)), "buildings": len(bl), "avoid": int(g_all.avoid_card.sum()), "held": int((g_all.listing_id.isin(held_ids) & ~g_all.shown).sum()), "ranked": int(len(g_all))},
                      "figures_over": "shown places" if len(s) else "ranked units (nothing is shown here)",
                      "building_ids": [b_["id"] for b_ in sorted(bl, key=lambda b_: b_["rank_in_neighborhood"])],
                      "all_in_range": [v(s.all_in.min()), v(s.all_in.max())] if len(s) else None, "sqft_median": num("sqft"),
                      "drive_min": num("drive_min_to"), "transit_min": num("transit_sat_median"),
                      "toll_round_trip": tollmed("toll_rt_ezpass"),
                      "toll_round_trip_mail": tollmed("toll_rt_mail") if "toll_rt_mail" in g and pd.to_numeric(g.toll_rt_mail, errors="coerce").notna().all() else None,
                      "toll_round_trip_mail_at_least": (v(pd.to_numeric(g.toll_rt_mail_subtotal, errors="coerce").median()) if "toll_rt_mail_subtotal" in g and not pd.to_numeric(g.toll_rt_mail, errors="coerce").notna().all() else None), "toll_basis": "New York E-ZPass, weekend off-peak",
                      "toll_complete": bool(g.toll_complete.astype(str).str.lower().eq("true").all()),
                      "safety": {"violent_per_1000": v(h.get("violent")), "property_per_1000": v(h.get("property")), "vehicle_theft_per_1000": v(h.get("motor_vehicle_theft")),
                                 "vs_jamaica": v(h.get("violent_vs_jamaica")), "property_vs_jamaica": v(h.get("property_vs_jamaica")), "vs_us": v(h.get("violent_vs_us")),
                                 "vs_metro": v(h.get("violent_vs_metro")), "vs_local": v(h.get("violent_vs_local")), "police": v(h.get("police")), "geography": v(h.get("geography")), "year": v(h.get("crime_year")),
                                 # inside a split city every neighborhood carries the same citywide police rate: say so, and give the estimate as context
                                 "basis": (f"citywide police rate for {PARENTS[hid]['parent_name']}: the same figure for every {PARENTS[hid]['parent_name']} neighborhood, not a rate for {PARENTS[hid]['name']}" if hid in PARENTS else None),
                                 "subcity_estimate": sub_crime.get(hid) if hid in PARENTS else None},
                      "parent_id": PARENTS[hid]["parent_id"] if hid in PARENTS else None, "parent_name": PARENTS[hid]["parent_name"] if hid in PARENTS else None,
                      "short_name": PARENTS[hid]["name"] if hid in PARENTS else None,
                      "traits": {k: v(h.get(k)) for k in ["no_car_share", "age_25_34_share", "living_alone_share", "households_with_kids_share", "college_degree_share", "newcomer_share",
                                                          "wfh_share", "median_hh_income", "detached_house_share", "built_since_2010_share", "built_before_1940_share", "restaurants_800m",
                                                          "bars_800m", "cafes_800m", "park_ha_800m", "park_walk_min", "open_water_m", "dog_park_m", "supermarket_m_c"]},
                      "vs_queens": {k[4:]: v(pd.to_numeric(g[k], errors="coerce").median()) for k in g.columns if k.startswith("vsq_") and not k.endswith("_diff")},
                      "unit_ids": list(s.sort_values("shown_rank").listing_id), "avoid_ids": list(g_all[g_all.avoid_card].listing_id),
                      "local": {"parking_rules": local.get(hid, {}).get("street_parking") or None, "dog_rules": local.get(hid, {}).get("dogs") or None,
                                "voices": voices.get(hid, []), "survey": survey.get(hid, [])}})
    years = []
    for key, g in R.groupby("group_key"):
        s = g[g.shown]
        # independent check 3, D12: every experience figure is computed over the SHOWN units of the experience (it used
        # to come from data/group_exchange.csv, over all ranked units, more than half of them not on the page), and the
        # median and the range now describe the same set. Queens baseline: the shown units in Queens.
        col_of = dict(MEAS)
        sv = lambda k: pd.to_numeric(s[col_of[k]], errors="coerce").dropna()
        hv = lambda k: pd.to_numeric(HOME[col_of[k]], errors="coerce").dropna()
        med = {k: (v(round(float(sv(k).median()), 1)) if len(sv(k)) else None) for k in col_of}
        rng = {k: ([v(round(float(sv(k).min()), 1)), v(round(float(sv(k).max()), 1))] if len(sv(k)) else None) for k in col_of}
        dh = s.groupby("hood_id").drive_min_to.median().dropna() if len(s) else pd.Series(dtype=float)
        ends = None
        if len(dh):
            near, far = dh.idxmin(), dh.idxmax()
            ends = {"nearest": {"hood_id": near, "name": s[s.hood_id == near].hood.iloc[0], "drive_min": v(round(float(dh[near]), 1))},
                    "farthest": {"hood_id": far, "name": s[s.hood_id == far].hood.iloc[0], "drive_min": v(round(float(dh[far]), 1))}}
        years.append({"id": key, "label": g.group_label.iloc[0], "subhead": g.group_subhead.iloc[0],
                      "counts": {"neighborhoods": int(s.hood_id.nunique()), "buildings": int(s.building_id.nunique()), "shown": int(len(s)), "avoid": int(g.avoid_card.sum())},
                      "figures_over": "shown places",
                      "all_in_range": [v(s.all_in.min()), v(s.all_in.max())] if len(s) else None,
                      "drive_min_range": [v(s.drive_min_to.min()), v(s.drive_min_to.max())] if len(s) else None,
                      "drive_min_range_hoods": ends,
                      "medians": med, "ranges": rng,
                      "vs_queens": {k[4:]: v(pd.to_numeric(s[k], errors="coerce").median()) for k in s.columns if k.startswith("vsq_") and not k.endswith("_diff")} if len(s) else {},
                      "vs_queens_diff": {k: (v(round(float(sv(k).median() - hv(k).median()), 1)) if len(sv(k)) and len(hv(k)) else None) for k in col_of},
                      "hood_ids": [h["id"] for h in sorted([h for h in hoods if h["year"] == key and h["counts"]["shown"]], key=lambda h: h["drive_min"] or 999)],
                      "catch": None, "scenes": None})
    spec = pd.read_csv(DATA / "reference" / "queens_spectrum_definition.csv").to_dict("records")
    out = {"meta": {"built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "cap_all_in": 3000, "move_in_window": "now to 2026-12-15",
                    "anchor": {"name": "Mom and Dad (Jamaica station)", "lat": 40.699608, "lon": -73.808530},
                    "jamaica_yardstick": {"violent_per_1000": v(G.jamaica_violent.iloc[0]), "property_per_1000": v(G.jamaica_property.iloc[0])},
                    "queens_spectrum": spec, "weights": {"safety": 22, "building": 16, "cost": 12, "car": 12, "space": 12, "distance": 10, "dog": 8, "daily": 8},
                    "counts": {"shown": int(len(shown)), "shown_with_asterisk": int((shown.confirm_asterisk == "yes").sum()), "avoid": int(len(avoid)), "held": int(len(held)),
                               "awaiting_live_check": int(len(awaiting)), "ranked": int(len(R)), "buildings": len(BUILDINGS)},
                    "toll_basis": {"assumes": "New York E-ZPass", "rate_time": "weekend off-peak", "mail_rate_field": "toll_round_trip_mail", "note": parsers.TOLL_NOTE},
                    "notes": ["Drive times are free-flow estimates without traffic.", parsers.TOLL_NOTE, "An asterisk on rent means a special offer applies; see the rent terms.",
                              "A floor marked 'read from the unit number' is not stated on the page; confirm it on the tour.",
                              "A place with an asterisk has one thing still to confirm (elevator, dogs allowed, or whether the listing is real and available); the text beside it says what and why.",
                              "Disclosures are things to know that never remove a place: floor not published, lease term, a cost that could pass $3,000 once parking and fees are known, net-effective rent (only where the listing says the price is net-effective), a special offer (ask what a normal month costs), condo rented by its owner, a dog weight limit with no number, and a town rule restricting overnight street parking where the building's parking is not confirmed.",
                              "Pet rent is always counted: where a building does not publish it, the cost uses an estimate (the median of the known pet rents in the same state), marked as an estimate.",
                              "all_in_likely adds the median known parking fee and required fees for the lines a building does not publish; it is shown beside the all-in figure and is never used for the $3,000 limit.",
                              "Experience and neighborhood figures (medians and ranges) are computed over the places shown on the page.",
                              "An elevator marked 'listing_site_only' is stated in a listing site's amenity list or text and has not been confirmed on the building's own page.",
                              "Each place carries the date its price was read (price_seen_at). A listing that was not read again since is not marked for that.",
                              "Cost lines that are not published add nothing to the all-in figure and are named on each receipt as not published."],
                    "moment_thresholds": MOMENT_THRESHOLDS, "max_units_per_building": 8},
           "years": years, "neighborhoods": hoods, "buildings": BUILDINGS, "units": [unit(r) for _, r in shown.iterrows()],
           "avoid": [unit(r) for _, r in avoid.iterrows()], "held": [unit(r) for _, r in held.iterrows()],
           "awaiting_live_check": [{"id": r.listing_id, "building": v(r.building_name), "address": v(r.address), "unit": v(r.unit), "hood_id": r.hood_id, "year": v(r.group_key), "price_seen_at": v(r.last_seen),
                                    "rank": v(r.rank_score), "all_in": v(r.all_in), "listing": v(r.url)} for r in awaiting.itertuples()]}
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site" / "data.json").write_text(json.dumps(out, default=str, allow_nan=False))
    print(f"site/data.json: {len(out['years'])} years, {len(hoods)} neighborhoods, {len(out['units'])} shown, {len(out['avoid'])} avoid, {len(out['held'])} held; {(ROOT / 'site' / 'data.json').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
