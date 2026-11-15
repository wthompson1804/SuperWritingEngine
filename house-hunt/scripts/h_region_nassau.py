"""Region pass, building-first: Nassau County, NY (docs/REGION_AGENT_BRIEF.md).

Input: scripts/h_region_nassau_buildings.json, a hand-curated list of the elevator / mid-rise rental buildings
examined, one record per building, with the facts read from the building's own leasing page (or the manager's
page, or an allowed aggregator copy) and the URL each fact came from.

Record fields
  name, address, town, zip, url (leasing site), source_url (page the building facts came from),
  floors, elevator (yes/no/unknown), dogs (yes/no/unknown), weight (number, "none", "small_only" or ""),
  verdict   pass | fails:<reason> | unconfirmed:<fact> | blocked   (pass is split into pass_with_units /
            pass_no_availability here, from the unit rows found)
  note      free text: what the pages say, what blocked
  agg       list of Trulia building / Apartment List property URLs; unit rows are read from them with the
            existing parsers (h_trulia.parse_detail, h_apartmentlist.build_rows), so every price and date
            comes from that page, fetched through the shared cache
  units     optional list of hand-read unit rows (dicts of CSV columns) from a page with no parser; each
            carries its own url and first_seen
  row       optional dict of column overrides applied to every row of the building (facts confirmed on the
            leasing site that the aggregator page lacks, e.g. elevator, building_floors, dog_weight_limit_lb)
  min_rent / min_rent_url / min_rent_seen: lowest studio/1BR price stated on a page, for stub rows

Output
  data/listings_raw/region_nassau.csv           (HARVEST_AGENT_BRIEF columns)
  data/reference/region_buildings_nassau.csv    (one row per building examined)

Idempotent: rows are rebuilt from the cache on every run; first_seen is kept from the previous CSV.
Run with --refresh-hours N to refetch aggregator pages older than N hours (default 48).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from h_mgmt_common import COLS, upsert  # noqa: E402

ROOT = lib.ROOT
SRC = "region_nassau"
BJSON = ROOT / "scripts" / "h_region_nassau_buildings.json"
OUT = ROOT / "data" / "listings_raw" / "region_nassau.csv"
BOUT = ROOT / "data" / "reference" / "region_buildings_nassau.csv"
BCOLS = ["name", "address", "town", "zip", "url", "floors", "elevator", "dogs", "weight_limit", "verdict",
         "units_le_3000", "units_in_window", "min_rent_seen", "source_url", "notes"]
WINDOW_END = "2026-12-15"
CAP = 3000


def census_geo(addr: str):
    try:
        d, _ = lib.get_json("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress", SRC + "_geo",
                            params={"address": addr, "benchmark": "Public_AR_Current", "format": "json"})
        m = d["result"]["addressMatches"]
        if m:
            return round(m[0]["coordinates"]["y"], 6), round(m[0]["coordinates"]["x"], 6)
    except Exception as e:  # geocoder hiccup: leave blank
        print("  geocode failed", addr, str(e)[:80])
    return "", ""


def agg_rows(url: str, refresh_hours: float):
    """Rows (studio/1BR <= $3,000) from an aggregator building page, with the existing parsers."""
    if "trulia.com" in url:
        import h_trulia as T
        nd, meta = T.fetch(url, refresh_hours)
        if nd is None:
            return [], f"gone ({meta.get('status')})"
        return T.parse_detail(nd, meta)
    if "apartmentlist.com" in url:
        import h_apartmentlist as A
        path = url.split("apartmentlist.com")[1]
        html, meta = A.fetch(path)
        if meta["status"] != 200:
            return [], f"HTTP {meta['status']}"
        L = A.parse_listing(html)
        if not L:
            return [], "no listing JSON"
        g = A.load_grid()
        return A.build_rows(L, path, meta, {z[0]: z[3] for z in g}, g)
    raise ValueError("no parser for " + url)


def in_window(r: dict) -> bool:
    d = (r.get("available_date") or "").strip()
    return d == "now" or (bool(re.match(r"\d{4}-\d\d-\d\d$", d)) and d <= WINDOW_END)


def rent(r: dict) -> float:
    try:
        return float(r.get("listed_rent") or 0)
    except ValueError:
        return 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-hours", type=float, default=48)
    a = ap.parse_args()
    blds = json.loads(BJSON.read_text())
    out_rows, brows = [], []
    for b in blds:
        rows, whys = [], []
        for u in b.get("agg", []):
            try:
                rr, why = agg_rows(u, a.refresh_hours)
            except Exception as e:  # bot wall or parser failure: record, keep going
                rr, why = [], f"{type(e).__name__}: {str(e)[:120]}"
            if why:
                whys.append(f"{u.split('/')[2]}: {why}")
            rows += [dict(r) for r in rr]
        for u in b.get("units", []):
            r = {k: "" for k in COLS}
            r.update(u)
            rows.append(r)
        rows = [r for r in rows if 0 < rent(r) <= CAP and str(r.get("beds")) in ("0", "1", "0.0", "1.0")]
        # one row per (unit or plan, beds, rent, date): the same unit can appear on two aggregators
        seen, uniq = set(), []
        for r in sorted(rows, key=lambda r: (0 if r.get("unit") else 1, rent(r))):
            k = (r.get("unit") or r.get("listing_id"), str(r.get("beds")), r.get("listed_rent"))
            if k in seen:
                continue
            seen.add(k)
            uniq.append(r)
        rows = uniq
        nwin = sum(in_window(r) for r in rows)
        v = b["verdict"]
        if v == "pass":
            v = "pass_with_units" if nwin else "pass_no_availability"
        slug = re.sub(r"[^a-z0-9]+", "-", (b["name"] + "-" + b["town"]).lower()).strip("-")
        lat, lon = b.get("lat", ""), b.get("lon", "")
        if rows and not lat:
            lat, lon = rows[0].get("lat", ""), rows[0].get("lon", "")
        if not lat and b.get("address"):
            lat, lon = census_geo(f"{b['address']}, {b['town']}, NY {b.get('zip', '')}")
        base_note = b.get("note", "")
        over = dict(b.get("row", {}))
        over.setdefault("elevator", b.get("elevator", "unknown"))
        over.setdefault("dogs", b.get("dogs", "unknown"))
        if b.get("floors"):
            over.setdefault("building_floors", str(b["floors"]))
        if str(b.get("weight", "")).isdigit():
            over.setdefault("dog_weight_limit_lb", str(b["weight"]))
        elif b.get("weight") == "none":
            over.setdefault("dog_weight_limit_lb", "none")

        def finish(r: dict, prefix: str) -> dict:
            r = dict(r)
            for k, val in over.items():
                if val not in ("", None, "unknown") or not r.get(k):
                    r[k] = val
            r["listing_id"] = "rn:" + slug + ":" + re.sub(r"^.*?:", "", str(r.get("listing_id") or r.get("unit") or "bldg"))
            r["building_name"] = b["name"]
            r["address"] = r.get("address") or b.get("address", "")
            r["city"] = r.get("city") or b["town"]
            r["state"] = "NY"
            r["zip"] = r.get("zip") or b.get("zip", "")
            r["lat"], r["lon"] = r.get("lat") or lat, r.get("lon") or lon
            r["building_url"] = b.get("url") or r.get("building_url", "")
            r["listing_type"] = r.get("listing_type") or "managed_building"
            src = f"building facts from {b.get('source_url', '')}"
            r["notes"] = "; ".join(x for x in (prefix + base_note, src, r.get("notes", "")) if x)
            return r

        def stub(prefix: str) -> dict:
            r = {k: "" for k in COLS}
            r.update(listing_id="bldg", source_site=re.sub(r"^www\.", "", (b.get("min_rent_url") or b.get("source_url") or b.get("url") or "//none").split("/")[2]),
                     url=b.get("min_rent_url") or b.get("source_url") or b.get("url", ""), detail_level="building",
                     first_seen=b.get("min_rent_seen") or b.get("seen", ""), last_seen=b.get("min_rent_seen") or b.get("seen", ""),
                     listed_rent=b.get("min_rent", ""), price_basis=b.get("min_rent_basis", ""),
                     dogs="unknown", elevator="unknown", floor="unknown")
            return finish(r, prefix)

        if v.startswith("fails"):
            pick = sorted(rows, key=lambda r: (not in_window(r), rent(r)))[:1]
            pre = f"BUILDING_FAILS: {v[6:]}. "
            out_rows.append(finish(pick[0], pre) if pick else stub(pre))
        elif v == "blocked":
            out_rows.append(stub("BLOCKED: "))
        elif v.startswith("unconfirmed"):
            pre = f"UNCONFIRMED: {v[12:]}. "
            out_rows += [finish(r, pre) for r in rows] or [stub(pre)]
        elif rows:
            pre = "" if nwin else "NO_AVAILABILITY: units listed but none available by 2026-12-15. "
            out_rows += [finish(r, pre) for r in rows]
        else:
            out_rows.append(stub("NO_AVAILABILITY: "))
        brows.append({"name": b["name"], "address": b.get("address", ""), "town": b["town"], "zip": b.get("zip", ""),
                      "url": b.get("url", ""), "floors": b.get("floors", ""), "elevator": b.get("elevator", "unknown"),
                      "dogs": b.get("dogs", "unknown"), "weight_limit": b.get("weight", ""), "verdict": v,
                      "units_le_3000": len(rows), "units_in_window": nwin,
                      "min_rent_seen": min([rent(r) for r in rows], default=b.get("min_rent", "")),
                      "source_url": b.get("source_url", ""),
                      "notes": "; ".join([base_note] + whys)})
    # rebuild the CSV from scratch but keep first_seen of rows that were already there
    old = {}
    if OUT.exists():
        with open(OUT, newline="") as f:
            old = {r["listing_id"]: r.get("first_seen", "") for r in csv.DictReader(f)}
        OUT.unlink()
    for r in out_rows:
        if old.get(r["listing_id"]):
            r["first_seen"] = old[r["listing_id"]]
    n = upsert(OUT, out_rows)
    with open(BOUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BCOLS)
        w.writeheader()
        w.writerows(brows)
    from collections import Counter
    c = Counter(re.sub(r":.*", "", b["verdict"]) for b in brows)
    print(f"buildings {len(brows)} {dict(c)}; rows written {n}; "
          f"rows in window from passing buildings "
          f"{sum(b['units_in_window'] for b in brows if b['verdict'] == 'pass_with_units')}")


if __name__ == "__main__":
    main()
