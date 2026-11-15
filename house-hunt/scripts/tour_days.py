"""tour_days: group chosen places into tour days by geography and order the stops within each day.

    python3 scripts/tour_days.py --ids out/shortlist.txt [--days 3] [--start "40.699608,-73.808530"]
    python3 scripts/tour_days.py --ids "id1,id2,id3"
    python3 scripts/tour_days.py --per-year 3 [--years ...] [--hoods ...]

Writes out/tour_days.md and out/tour_days.csv. No network: reads data/ranked_units.csv only.

Method. One stop per building. Stops are split into K days with k-means on latitude/longitude (seeded
deterministically by farthest-point selection, so the same input always gives the same days). With --days K there
are exactly K days, whatever their size. Without it, K starts at ceil(stops / --max-per-day) and any day larger than
--max-per-day (default 5) is split again. Within a day the order is nearest-neighbour from the start point.

Distances are straight-line (great-circle) miles. Drive minutes are an ESTIMATE:
straight-line miles x ROAD_FACTOR (road distance is longer than the straight line) at AVG_MPH. scripts/tools/drive.py
was not used because every lookup there calls the public OSRM server. Where the start is the default Jamaica LIRR
station, the first and last legs instead use the pipeline's own OSRM free-flow minutes (`drive_min_from`,
`drive_min_to`), also an estimate (no traffic). A straight line across water (Long Island Sound, the Hudson, New
York Harbor) understates the drive badly; the output flags legs that cross between Long Island and the mainland.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import call_sheet as cs  # noqa: E402

JAMAICA = (40.699608, -73.808530)
ROAD_FACTOR = 1.4   # road miles per straight-line mile (stated assumption)
AVG_MPH = 30.0      # average speed over the road miles (stated assumption)
EST_LABEL = f"estimate: straight-line miles x {ROAD_FACTOR} at {AVG_MPH:g} mph"
OSRM_LABEL = "estimate: OSRM free-flow from the pipeline, no traffic"


def est_minutes(miles: float) -> float:
    return miles * ROAD_FACTOR / AVG_MPH * 60


def parse_start(text: str | None) -> tuple[float, float]:
    if not text:
        return JAMAICA
    parts = [p for p in text.replace(";", ",").replace(" ", ",").split(",") if p]
    if len(parts) != 2:
        raise SystemExit('--start must be "lat,lon"')
    return float(parts[0]), float(parts[1])


# ------------------------------------------------------------------------------------------------- stops
def stops_from_buildings(buildings: list[dict]) -> tuple[list[dict], list[dict]]:
    """(stops with coordinates, buildings without coordinates). Stops are sorted by id so input order never matters."""
    stops, nocoord = [], []
    for b in buildings:
        u0 = b["units"][0]
        lat, lon = cs.num(cs.val(u0, "lat")), cs.num(cs.val(u0, "lon"))
        stop = {"id": cs.val(u0, "building_id") or b["building_id"], "year": b["year"], "units": b["units"],
                "lat": lat, "lon": lon}
        (stops if lat is not None and lon is not None else nocoord).append(stop)
    stops.sort(key=lambda s: s["id"])
    return stops, nocoord


# ------------------------------------------------------------------------------------------------- clustering
def _xy(lat, lon, lat0):
    return (lon * math.cos(math.radians(lat0)) * 69.17, lat * 69.05)  # miles, local flat projection


def cluster_days(points: list[tuple[float, float]], k: int, iters: int = 50) -> list[int]:
    """Deterministic k-means. Returns a cluster index (0..k-1) for each point. No randomness anywhere."""
    n = len(points)
    if n == 0:
        return []
    k = max(1, min(k, n))
    lat0 = sum(p[0] for p in points) / n
    xy = [_xy(p[0], p[1], lat0) for p in points]

    def d2(a, b):
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

    # farthest-point seeding: start from the point farthest from the centroid (ties: lowest index)
    cx, cy = sum(p[0] for p in xy) / n, sum(p[1] for p in xy) / n
    first = max(range(n), key=lambda i: (round(d2(xy[i], (cx, cy)), 9), -i))
    centers = [xy[first]]
    while len(centers) < k:
        nxt = max(range(n), key=lambda i: (round(min(d2(xy[i], c) for c in centers), 9), -i))
        centers.append(xy[nxt])
    assign = [0] * n
    for _ in range(iters):
        new = [min(range(k), key=lambda c: (round(d2(xy[i], centers[c]), 9), c)) for i in range(n)]
        for c in range(k):
            members = [xy[i] for i in range(n) if new[i] == c]
            if members:
                centers[c] = (sum(m[0] for m in members) / len(members), sum(m[1] for m in members) / len(members))
        if new == assign:
            break
        assign = new
    return assign


def order_stops(stops: list[dict], start: tuple[float, float]) -> list[dict]:
    """Nearest-neighbour order from the start point (ties: lowest id)."""
    left = sorted(stops, key=lambda s: s["id"])
    here, out = start, []
    while left:
        nxt = min(left, key=lambda s: (round(cs.haversine_miles(here[0], here[1], s["lat"], s["lon"]), 6), s["id"]))
        left.remove(nxt)
        out.append(nxt)
        here = (nxt["lat"], nxt["lon"])
    return out


def _split(stops: list[dict], k: int) -> list[list[dict]]:
    assign = cluster_days([(s["lat"], s["lon"]) for s in stops], k)
    groups: dict[int, list[dict]] = {}
    for s, c in zip(stops, assign):
        groups.setdefault(c, []).append(s)
    return [groups[c] for c in sorted(groups)]


def plan_days(stops: list[dict], k: int, start: tuple[float, float], max_per_day: int | None = None) -> list[list[dict]]:
    """Days (each an ordered list of stops), nearest day to the start first.

    With max_per_day, a day that came out larger is split in two (again by k-means) until every day fits, so the
    number of days can end up above k. Without it, exactly min(k, stops) days are returned whatever their size.
    """
    stops = sorted(stops, key=lambda s: s["id"])
    groups = _split(stops, k)
    while max_per_day and any(len(g) > max_per_day for g in groups):
        nxt = []
        for g in groups:
            nxt += _split(g, 2) if len(g) > max_per_day else [g]
        groups = nxt
    ordered = [order_stops(d, start) for d in groups]
    ordered.sort(key=lambda d: (round(cs.haversine_miles(start[0], start[1], d[0]["lat"], d[0]["lon"]), 6), d[0]["id"]))
    return ordered


# ------------------------------------------------------------------------------------------------- legs
def _on_long_island(lat, lon) -> bool:
    """Rough test for Brooklyn, Queens, Nassau and Suffolk. Used only to flag legs that cross water."""
    if lon < -74.05 or lat < 40.54:                      # Staten Island, New Jersey
        return False
    if lat > 40.70 and lon < -73.97 + (lat - 40.70) * 0.4:   # Manhattan, west of the East River
        return False
    north_shore = min(41.17, 40.80 + 0.45 * max(0.0, lon + 73.80))
    return lat < north_shore


def leg(a: tuple[float, float], b: tuple[float, float], osrm_min: float | None = None) -> dict:
    miles = cs.haversine_miles(a[0], a[1], b[0], b[1])
    crossing = _on_long_island(*a) != _on_long_island(*b)
    if osrm_min is not None:
        return {"miles": miles, "minutes": osrm_min, "basis": OSRM_LABEL, "crossing": False}
    return {"miles": miles, "minutes": est_minutes(miles), "basis": EST_LABEL, "crossing": crossing}


def day_legs(day: list[dict], start: tuple[float, float]) -> tuple[list[dict], dict]:
    """(leg into each stop, leg back to the start)."""
    default_start = start == JAMAICA
    legs, here = [], start
    for i, s in enumerate(day):
        osrm = cs.num(cs.val(s["units"][0], "drive_min_from")) if (i == 0 and default_start) else None
        legs.append(leg(here, (s["lat"], s["lon"]), osrm))
        here = (s["lat"], s["lon"])
    osrm_back = cs.num(cs.val(day[-1]["units"][0], "drive_min_to")) if default_start else None
    return legs, leg(here, start, osrm_back)


# ------------------------------------------------------------------------------------------------- output
def stop_fields(s: dict) -> dict:
    units = s["units"]
    u0 = units[0]
    aster, tourq = [], []
    for u in units:
        what, why = cs.val(u, "confirm_what"), cs.val(u, "confirm_why")
        if what or why:
            aster.append(f"unit {cs.unit_label(u)}: confirm {what or 'see note'}" + (f" ({why})" if why else ""))
        if cs.truthy(cs.val(u, "rent_asterisk")):
            offer = cs.val(u, "rent_offer_text", "concession_text")
            aster.append(f"unit {cs.unit_label(u)}: rent terms open" + (f' ("{offer[:100]}")' if offer else ""))
        if cs.val(u, "all_in_unknown_lines"):
            aster.append(f"unit {cs.unit_label(u)}: all-in does not yet include {cs.val(u, 'all_in_unknown_lines')}")
        for c in ("tour_confirm", "to_confirm"):
            for q in cs.val(u, c).split(";"):
                q = q.strip()
                if q and q not in tourq:
                    tourq.append(q)
    return {
        "building_id": s["id"], "year": s["year"], "hood": cs.val(u0, "hood"),
        "building_name": cs.val(u0, "building_name"), "address": cs.val(u0, "address"),
        "city": cs.val(u0, "city"), "state": cs.val(u0, "state"),
        "listing_ids": "; ".join(cs.val(u, "listing_id") for u in units),
        "units": "; ".join(cs.unit_label(u) for u in units),
        "all_in": "; ".join(f"{cs.unit_label(u)}: {cs.money(cs.val(u, 'all_in')) or 'not computed'}"
                            + ("*" if cs.val(u, "all_in_unknown_lines") else "") for u in units),
        "listed_rent": "; ".join(f"{cs.unit_label(u)}: {cs.money(cs.val(u, 'listed_rent'))}" for u in units),
        "asterisk": " | ".join(dict.fromkeys(aster)),
        "tour_questions": " | ".join(tourq),
        "url": " ".join(dict.fromkeys(cs.val(u, "url") for u in units if cs.val(u, "url"))),
        "lat": s["lat"], "lon": s["lon"],
    }


def build_outputs(days: list[list[dict]], start: tuple[float, float], nocoord: list[dict], missing: list[str]):
    rows = []
    start_name = "Jamaica LIRR station" if start == JAMAICA else f"{start[0]:.5f}, {start[1]:.5f}"
    md = ["# Tour days", "",
          f"{sum(len(d) for d in days)} stops in {len(days)} days. Start and end of each day: {start_name}.", "",
          "Distances are straight-line miles. Drive minutes are **estimates**, not routed times: "
          f"straight-line miles x {ROAD_FACTOR} at {AVG_MPH:g} mph between stops"
          + ("; the first and last leg of each day use the pipeline's OSRM free-flow minutes (no traffic)."
             if start == JAMAICA else ".")
          + " Legs marked \"crosses water\" go between Long Island and the mainland, where the straight line "
          "understates the drive; check those on a map.", ""]
    for di, day in enumerate(days, 1):
        legs, back = day_legs(day, start)
        tot_mi = sum(x["miles"] for x in legs) + back["miles"]
        tot_min = sum(x["minutes"] for x in legs) + back["minutes"]
        hoods = ", ".join(dict.fromkeys(cs.val(s["units"][0], "hood") for s in day))
        md += [f"## Day {di}: {len(day)} stops ({hoods})", "",
               f"About {tot_mi:.0f} straight-line miles and {tot_min:.0f} minutes of driving in total (estimate), "
               "before time at each stop.", ""]
        for si, (s, lg) in enumerate(zip(day, legs), 1):
            f = stop_fields(s)
            flag = ", crosses water" if lg["crossing"] else ""
            md.append(f"### {di}.{si} {f['building_name'] or f['address']} ({f['hood']})")
            md.append(f"- From the previous point: {lg['miles']:.1f} straight-line miles, about {lg['minutes']:.0f} min "
                      f"({lg['basis']}{flag})")
            md.append(f"- Address: {f['address']}" + (f", {f['city']}" if f["city"] else "") + (f" {f['state']}" if f["state"] else ""))
            md.append(f"- Units and all-in monthly cost: {f['all_in']}" + (" (* = some cost lines still unknown)" if "*" in f["all_in"] else ""))
            md.append(f"- Year: {f['year']}")
            for a in (f["asterisk"].split(" | ") if f["asterisk"] else []):
                md.append(f"- Asterisk: {a}")
            for q in (f["tour_questions"].split(" | ") if f["tour_questions"] else []):
                md.append(f"- On the tour: {q}")
            md.append(f"- Listing: {f['url']}")
            md.append("")
            rows.append({"day": di, "stop": si, **f,
                         "leg_straight_miles": round(lg["miles"], 1), "leg_drive_min_estimate": round(lg["minutes"]),
                         "leg_estimate_basis": lg["basis"], "leg_crosses_water": "yes" if lg["crossing"] else "",
                         "return_straight_miles": round(back["miles"], 1) if si == len(day) else "",
                         "return_drive_min_estimate": round(back["minutes"]) if si == len(day) else "",
                         "return_estimate_basis": back["basis"] if si == len(day) else ""})
        md += [f"Back to the start: {back['miles']:.1f} straight-line miles, about {back['minutes']:.0f} min ({back['basis']}"
               + (", crosses water" if back["crossing"] else "") + ").", ""]
    if nocoord or missing:
        md += ["## Not placed", ""]
        md += [f"- {cs.val(s['units'][0], 'address') or s['id']}: no coordinates in the data" for s in nocoord]
        md += [f"- {m}: listing_id not found in ranked_units.csv" for m in missing]
        md.append("")
    return rows, "\n".join(md)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ids", help="file (one listing_id per line, or a CSV with a listing_id column) or a comma list")
    g.add_argument("--per-year", type=int, help="take the top N buildings of each year instead of a list")
    ap.add_argument("--years")
    ap.add_argument("--hoods")
    ap.add_argument("--days", type=int, help="number of tour days (default: ceil(stops / --max-per-day))")
    ap.add_argument("--max-per-day", type=int, default=5, help="largest day when --days is not given (default 5)")
    ap.add_argument("--start", help='"lat,lon" (default Jamaica LIRR station 40.699608,-73.808530)')
    ap.add_argument("--ranked", default=str(cs.RANKED))
    ap.add_argument("--out-dir", default=str(cs.OUT))
    a = ap.parse_args(argv)

    df = cs.load_ranked(Path(a.ranked))
    missing = []
    if a.ids:
        buildings, missing = cs.buildings_for_ids(df, cs.read_ids(a.ids))
    else:
        buildings = cs.pick_buildings(df, a.per_year, a.years, a.hoods)
    stops, nocoord = stops_from_buildings(buildings)
    if not stops:
        print("No stops with coordinates.", file=sys.stderr)
        return 1
    start = parse_start(a.start)
    if a.days:   # an explicit --days is kept exactly; days may then be larger than --max-per-day
        days = plan_days(stops, a.days, start)
    else:
        days = plan_days(stops, math.ceil(len(stops) / max(1, a.max_per_day)), start, max(1, a.max_per_day))
    rows, md = build_outputs(days, start, nocoord, missing)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_dir / "tour_days.csv", index=False)
    (out_dir / "tour_days.md").write_text(md, encoding="utf8")
    print(f"{len(stops)} stops in {len(days)} days (sizes {[len(d) for d in days]}) -> {out_dir / 'tour_days.md'}, tour_days.csv"
          + (f"; {len(missing)} ids not found" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
