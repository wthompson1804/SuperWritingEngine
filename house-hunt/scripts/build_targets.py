"""Funnel: pick the few listings worth a detail-page fetch, instead of fetching everything.

A listing is a target when ALL hold:
  - no gate has failed, and it is not already a full pass
  - listed rent <= $2,850 (utilities, pet rent and fees add roughly $150+, and the all-in cap is $3,000)
  - not a unit in a house
  - the building plausibly has an elevator: elevator gate already passes (stated, NYC building class, or 6+ floors),
    or, outside NYC, OpenStreetMap shows the building at 6+ levels or 18+ m, or (aggregators) 3+ listings share the
    address; management-company communities are always kept
One fetch per building is enough for building-level facts (dogs, elevator), so targets are grouped by building and
ordered nearest-first. Output: data/reference/detail_targets_<source>.csv (url, building_url, addr_key, why).
"""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).parent / "tools"))
from lib import DATA

RENT_TARGET_MAX = 2850
NYC_ZIP3 = ("100", "101", "102", "103", "104", "110", "111", "112", "113", "114", "116")


def osm_tall(lat, lon, _cache={}):
    import places
    try:
        b = places.near(float(lat), float(lon)).get("building", {})
    except Exception:
        return ""
    def val(k):
        v = b.get(k) or {}
        try:
            return float(v.get("value"))
        except (TypeError, ValueError):
            return None
    lv, h = val("building_levels"), val("building_height_m") or val("height_m")
    if (lv and lv >= 6) or (h and h >= 18):
        return f"osm levels={lv} height={h}"
    return ""


def main():
    d = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    d["rent"] = pd.to_numeric(d.listed_rent, errors="coerce")
    d["drive"] = pd.to_numeric(d.drive_min_zip, errors="coerce")
    d["n_at_addr"] = d.groupby("addr_key").listing_id.transform("count")
    nyc = d.zip5.str[:3].isin(NYC_ZIP3) & (d.state == "NY")
    base = (d.gate_status == "pending") & (d.rent <= RENT_TARGET_MAX) & (d.listing_type != "unit_in_house")
    elev_ok = d.g_elevator == "pass"
    multi = (d.n_at_addr >= 2) | (d.building_name.str.strip() != "") & (d.building_name != d.address) | (d.building_url != "") | (d.listing_type == "managed_building")
    evidence = elev_ok | (d.n_at_addr >= 3)
    mgmt = ~d.source_site.isin(["trulia", "zumper", "apartmentlist.com"])
    cand = d[base & (evidence | mgmt | (~nyc & (d.lat != "")))].copy()
    cand["osm"] = ""
    lone = ~(evidence | mgmt).reindex(cand.index)
    # outside NYC, listings with no other elevator evidence only count if OSM shows a tall building
    cand.loc[lone, "osm"] = [osm_tall(a, o) for a, o in zip(cand.loc[lone, "lat"], cand.loc[lone, "lon"])]
    keep = cand[~lone | (cand.osm != "")].copy()
    keep["why"] = keep.pending_reasons + "|" + keep.elevator_basis.where(keep.elevator_basis != "", keep.osm.where(keep.osm != "", "multi_unit_building"))
    # one row per building per source (cheapest unit), nearest first
    keep = keep.sort_values(["drive", "rent"]).drop_duplicates(["source_site", "addr_key"])
    print("pending:", (d.gate_status == "pending").sum(), "-> candidates:", len(cand), "-> building targets:", len(keep))
    for src, g in keep.groupby("source_site"):
        name = "".join(c if c.isalnum() else "_" for c in src.lower())
        g[["url", "building_url", "addr_key", "city", "state", "drive", "rent", "why"]].to_csv(
            DATA / "reference" / f"detail_targets_{name}.csv", index=False)
        print(f"  {src}: {len(g)} (<=60 min: {(g.drive <= 60).sum()})")


if __name__ == "__main__":
    main()
