"""Run every lookup tool for each building that has a listing passing the gates, then compute all-in cost.

Outputs:
  data/enriched/<addr_key hash>.json   full tool results with provenance (one per building)
  data/buildings_enriched.csv          flat facts per building
  data/units.csv                       passing listings + all-in lines; all-in > $3,000 are marked fail_all_in
Usage: python3 scripts/enrich_units.py [--include-pending-near]   (default: gate_status == pass only)
"""
import hashlib, json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).parent / "tools"))
from lib import DATA
import drive, transit, crime, places, utilities
import build_master

CAP = 3000
OUT = DATA / "enriched"; OUT.mkdir(exist_ok=True)


def v(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    if isinstance(d, dict) and "value" in d:
        return d["value"]
    return d


def num(x):
    try:
        return float(str(x).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None


STALE_M = 150   # a cached lookup made more than this far from the building's settled coordinate is redone
REDONE = []


def enrich_building(key, lat, lon):
    """Lookups at the building's coordinate (build_master.building_coords: independent check W7). A cached result
    computed from a different point (the first listing row's, when rows disagreed) is deleted and redone, together
    with its data/enriched_color/ file, which scripts/rank.py then recomputes."""
    name = hashlib.sha1(key.encode()).hexdigest()[:14] + ".json"
    f = OUT / name
    if f.exists():
        r = json.loads(f.read_text())
        try:
            far = build_master.dist_m(float(r["lat"]), float(r["lon"]), lat, lon) > STALE_M
        except (TypeError, ValueError, KeyError):
            far = True
        if not far:
            return r
        f.unlink()
        (DATA / "enriched_color" / name).unlink(missing_ok=True)
        REDONE.append(key)
    r = {"addr_key": key, "lat": lat, "lon": lon}
    for name, fn in [("drive", lambda: drive.drive(lat, lon)),
                     ("transit_sat", lambda: transit.route(lat, lon, "sat_midday")),
                     ("transit_sun_return", lambda: transit.route(lat, lon, "sun_evening_return")),
                     ("crime_agency", lambda: crime.agency_rates(lat, lon)),
                     ("crime_near", lambda: crime.incidents_near(lat, lon)),
                     ("places", lambda: places.near(lat, lon)),
                     ("utilities_1br", lambda: utilities.monthly_utilities(lat, lon, beds=1)),
                     ("utilities_studio", lambda: utilities.monthly_utilities(lat, lon, beds=0))]:
        try:
            r[name] = fn()
        except Exception as e:  # keep going; record the failure
            r[name] = {"error": repr(e)[:300]}
    f.write_text(json.dumps(r, default=str))
    return r


def flat(r):
    d, p, a, c = r.get("drive", {}), r.get("places", {}), r.get("crime_agency", {}), r.get("crime_near", {})
    yrs = a.get("years") or []
    latest = next((y for y in yrs if str(y.get("year")) == str(a.get("latest_year_with_rates"))), yrs[0] if yrs else {})
    tr = d.get("toll_round_trip_ezpass", {})
    cn = c.get("counts", {}) if isinstance(c, dict) else {}
    g, go, er, st = (p.get(k, {}) for k in ("green_space", "going_out", "errands", "setting"))
    return {
        "addr_key": r["addr_key"], "lat": r["lat"], "lon": r["lon"],
        "drive_min_to": v(d, "minutes_to_jamaica"), "drive_min_from": v(d, "minutes_from_jamaica"),
        "drive_miles": v(d, "miles_to_jamaica"),
        "toll_rt_ezpass": tr.get("value"), "toll_complete": tr.get("complete"),
        "toll_known_subtotal": tr.get("known_subtotal"),
        # the same crossings at the Tolls by Mail rate, which is also what an E-ZPass tag issued outside New York pays
        # at MTA bridges and tunnels (docs/tools_notes/mta_tolls.md)
        "toll_rt_mail": (d.get("toll_round_trip_mail") or {}).get("value"),
        "toll_items": "; ".join(str(i.get("facility", i)) for i in (tr.get("items") or [])),
        "transit_sat_fastest": v(r.get("transit_sat", {}), "fastest_minutes"),
        "transit_sat_median": v(r.get("transit_sat", {}), "median_minutes"),
        "transit_transfers": v(r.get("transit_sat", {}), "transfers"),
        "transit_summary": v(r.get("transit_sat", {}), "leg_summary"),
        "transit_status": r.get("transit_sat", {}).get("status"),
        "transit_sun_return_median": v(r.get("transit_sun_return", {}), "median_minutes"),
        "last_sat_departure": v(r.get("transit_sat", {}), "last_departure_from_jamaica_sat"),
        "police_agency": v(a, "agency", "name"), "police_geography": a.get("geography"),
        "crime_source": a.get("primary_source"), "crime_year": a.get("latest_year_with_rates"),
        "crime_latest": json.dumps(latest, default=str),
        "near_veh_theft_24m": v(cn, "grand_larceny_motor_vehicle", "last_24_months"),
        "near_theft_from_veh_24m": v(cn, "theft_from_vehicle", "last_24_months"),
        "near_vs_baseline": json.dumps(c.get("vs_baseline"), default=str) if isinstance(c, dict) else "",
        "park_name": (g.get("nearest_named_park") or {}).get("name") or (g.get("nearest_park") or {}).get("name"),
        "park_walk_min": v(g, "nearest_named_park_walk_min") or v(g, "nearest_park_walk_min"),
        "park_ha_800m": v(g, "park_area_ha_within_800m"),
        "dog_park_name": (g.get("nearest_dog_park") or {}).get("name"),
        "dog_park_m": (g.get("nearest_dog_park") or {}).get("metres") or v(g, "nearest_dog_park"),
        "restaurants_800m": v(go, "restaurant_count_800m"), "bars_800m": v(go, "bar_count_800m"),
        "cafes_800m": v(go, "cafe_count_800m"), "bars_1600m": v(go, "bar_count_1600m"),
        "restaurants_1600m": v(go, "restaurant_count_1600m"), "music_1600m": v(go, "music_count_1600m"),
        "supermarket": (er.get("nearest_supermarket") or {}).get("name"),
        "supermarket_m": v(er, "nearest_supermarket"),
        "coast_m": v(st, "coastline_m"), "beach_m": v(st, "beach_m"), "open_water_m": v(st, "nearest_open_water_m"),
        "train_station": (st.get("nearest_train_station") or {}).get("name"),
        "train_station_m": v(st, "nearest_train_station"),
        "motorway_m": v(st, "motorway_m"),
        "util_1br": v(r.get("utilities_1br", {}), "total", "amount"),
        "util_1br_complete": v(r.get("utilities_1br", {}), "total", "complete"),
        "util_studio": v(r.get("utilities_studio", {}), "total", "amount"),
    }


def main():
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    P = L[(L.gate_status == "pass") & (L.lat != "")].copy()
    # one coordinate per building: the listing's own point is kept in lat_listing / lon_listing
    P["zip5"] = P.zip5.map(lambda z: z.zfill(5) if z.isdigit() else z)
    P = build_master.assign_building_ids(P)
    G = build_master.building_coords(P)
    P["lat_listing"], P["lon_listing"] = P.lat, P.lon
    for c in ("lat", "lon", "coord_basis", "coord_spread_m", "coord_note"):
        P[c] = P.building_id.map(G[c])
    P = P.drop(columns=["flat", "flon", "street_key"])
    G[G.coord_basis != "listing rows agree"].to_csv(DATA / "reference" / "building_geocode_changes.csv")
    B = P.drop_duplicates("addr_key")
    rows = []
    for i, (_, r) in enumerate(B.iterrows()):
        rows.append(flat(enrich_building(r.addr_key, float(r.lat), float(r.lon))))
        if i % 25 == 0:
            print(i, len(B), flush=True)
    bf = pd.DataFrame(rows)
    bf.to_csv(DATA / "buildings_enriched.csv", index=False)

    P = P.merge(bf, on="addr_key", how="left", suffixes=("", "_b"))
    lines, allin, star = [], [], []
    for _, r in P.iterrows():
        rent = num(r.listed_rent) or 0
        util = num(r.util_studio if str(r.beds).startswith("0") else r.util_1br)
        items = [("rent", rent, "found")]
        s = False
        pet = num(r.pet_rent)
        items.append(("pet rent", pet if pet is not None else 0, "found" if pet is not None else "not_found")); s |= pet is None
        park = num(r.parking_fee)
        items.append(("parking", park if park is not None else 0, "found" if park is not None else "not_found")); s |= park is None
        other = 0
        try:
            for it in json.loads(r.other_monthly_fees_json or "[]"):
                a = num(it.get("amount")) if isinstance(it, dict) else None
                other += a or 0
        except (ValueError, TypeError):
            pass
        items.append(("building fees", other, "found" if r.other_monthly_fees_json not in ("", "[]") else "not_found"))
        s |= r.other_monthly_fees_json in ("", "[]")
        items.append(("utilities (est.)", util or 0, "estimate" if util else "not_found")); s = True
        total = sum(x[1] for x in items)
        lines.append(json.dumps([{"line": a, "amount": round(b), "basis": c} for a, b, c in items]))
        allin.append(round(total)); star.append("yes" if s else "")
    P["all_in"] = allin; P["all_in_lines"] = lines; P["all_in_asterisk"] = star
    # The cost gate is decided later by scripts/all_in.py on the master tables (known fees, stated utilities,
    # net-effective rent). Every gate-passing unit goes forward; the rough figure here is kept only as `all_in_rough`.
    P["all_in_rough"] = P.all_in
    P["unit_status"] = "pass"
    P.to_csv(DATA / "units.csv", index=False)
    print(P.unit_status.value_counts().to_dict(), "buildings:", P[P.unit_status == "pass"].addr_key.nunique())
    print(f"coordinates: {G.coord_basis.value_counts().to_dict()}; lookups redone at a corrected coordinate: {len(REDONE)} address keys")


if __name__ == "__main__":
    main()
