"""Region pass, building-first: Suffolk County, NY - build stage (docs/REGION_AGENT_BRIEF.md).

Inputs
  scripts/h_region_suffolk_facts.py            hand-read building facts (BUILDINGS)
  raw/region_suffolk/trulia_buildings.jsonl    Trulia building pages of every Suffolk community found by the Trulia
                                               ZIP search (written by `h_region_suffolk.py trulia`): facts + unit rows
  data/listings_raw/{mgmt_greystar,mgmt_sightmap_sites,zumper,apartmentlist}.csv   rows other harvesters already read
Trulia communities with no hand record get an automatic record (verdict from the page: no dogs / age-restricted /
weight limit under 25 lb / elevator not stated) and a single row.
Outputs
  data/listings_raw/region_suffolk.csv, data/reference/region_buildings_suffolk.csv
Idempotent: rebuilt from caches each run; first_seen kept from the previous CSV.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from h_mgmt_common import COLS, upsert  # noqa: E402
from h_region_suffolk_facts import BUILDINGS  # noqa: E402

ROOT = lib.ROOT
SRC = "region_suffolk"
OUT = ROOT / "data" / "listings_raw" / "region_suffolk.csv"
BOUT = ROOT / "data" / "reference" / "region_buildings_suffolk.csv"
TJ = ROOT / "raw" / SRC / "trulia_buildings.jsonl"
BCOLS = ["name", "address", "town", "zip", "url", "floors", "elevator", "dogs", "weight_limit", "verdict",
         "units_le_3000", "units_in_window", "min_rent_seen", "source_url", "notes"]
WINDOW_END = "2026-12-15"
CAP = 3000
MIN_WEIGHT = 25
csv.field_size_limit(10 ** 9)


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


def page_index() -> dict:
    """url -> (retrieved_at, lat, lon) for pages already read by this pass or by the harvesters it reuses."""
    idx: dict[str, list] = {}
    for src in (SRC, "mgmt_greystar", "apartmentlist", "zumper"):
        p = ROOT / "raw" / src / "_index.jsonl"
        if p.exists():
            for line in p.read_text().splitlines():
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("status") == 200:
                    idx[d["url"].replace("//apartmentlist.com", "//www.apartmentlist.com")] = [d["retrieved_at"], "", ""]
    for fn, key, pre in (("greystar_buildings.jsonl", "url", ""), ("al_buildings.jsonl", "path", "https://www.apartmentlist.com"),
                         ("zumper_buildings.jsonl", "path", "https://www.zumper.com")):
        p = ROOT / "raw" / SRC / fn
        if p.exists():
            for line in p.read_text().splitlines():
                o = json.loads(line)
                if o.get("lat"):
                    e = idx.setdefault(pre + o[key], [o.get("retrieved_at", ""), "", ""])
                    e[1], e[2] = o["lat"], o["lon"]
    return idx


def al_rows(url: str):
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


def in_window(r: dict) -> bool:
    d = (r.get("available_date") or "").strip()
    return d == "now" or (bool(re.match(r"\d{4}-\d\d-\d\d$", d)) and d <= WINDOW_END)


def rent(r: dict) -> float:
    try:
        return float(r.get("listed_rent") or 0)
    except ValueError:
        return 0.0


def auto_record(o: dict) -> dict:
    """A Trulia community with no hand record: verdict from what the Trulia building page states."""
    name = o.get("name") or ""
    w = str(o.get("dog_weight_limit_lb") or "")
    pol = (o.get("dog_policy_text") or "")[:260]
    small = bool(re.search(r"Dogs: Allowed \([^)]*Size allowed: Small[;)]", pol))
    age = o.get("desc_age") or re.search(r"(?i)55\s?\+|58\s?\+|62\s?\+|senior", name)
    if o.get("dogs") == "no":
        v = "fails:no dogs (Trulia building page: dogs not allowed)"
    elif age:
        v = "fails:age-restricted community (55+/senior) per the Trulia building page"
    elif w.isdigit() and int(w) < MIN_WEIGHT:
        v = f"fails:dog weight limit {w} lb (under {MIN_WEIGHT} lb)"
    elif o.get("elevator") == "yes":
        v = "pass"
    else:
        v = ("unconfirmed:elevator not stated on the Trulia building page (garden-style community; these are mostly "
             "two-storey walk-up layouts)" + ("; dogs: small only, no weight number" if small and not w else ""))
    note = (f"Auto record from the Trulia building page ({o.get('units_total') or '?'} units; manager "
            f"{o.get('manager') or 'not stated'}). Pets: {pol}"
            + (f" Weight limit {w} lb." if w else "") + (f" Pet rent {o['pet_rent']}." if o.get("pet_rent") else ""))
    return {"name": name, "address": o.get("address") or "", "town": o.get("city") or "", "zip": o.get("zip") or "",
            "url": "", "source_url": o["url"], "elevator": o.get("elevator") or "unknown", "dogs": o.get("dogs") or "unknown",
            "weight": w if w else ("small_only" if small else ""), "verdict": v, "note": note, "_t": o, "one_row": True,
            "lat": o.get("lat") or "", "lon": o.get("lon") or "", "floors": o.get("building_floors") or "", "seen": o.get("retrieved_at", "")}


def main() -> None:
    tj = {}
    for line in TJ.read_text().splitlines():
        o = json.loads(line)
        if not o.get("gone") and not o.get("no_details"):
            tj[o["url"]] = o
    used = set()
    blds = []
    pidx = page_index()
    for b in BUILDINGS:
        b = dict(b)
        if b.get("trulia"):
            hit = [o for o in tj.values() if (o.get("name") or "").startswith(b["trulia"])]
            if len(hit) != 1:
                raise SystemExit(f"trulia prefix {b['trulia']!r} matches {len(hit)} records")
            b["_t"] = hit[0]
            used.add(hit[0]["url"])
            b.setdefault("source_url", hit[0]["url"])
            b.setdefault("lat", hit[0].get("lat") or "")
            b.setdefault("lon", hit[0].get("lon") or "")
        pi = pidx.get(b.get("min_rent_url") or b.get("source_url") or "") or pidx.get(b.get("source_url") or "")
        if pi:
            b.setdefault("seen", pi[0])
            if pi[1] and not b.get("lat"):
                b["lat"], b["lon"] = pi[1], pi[2]
        blds.append(b)
    hand_n = len(blds)
    blds += [auto_record(o) for u, o in sorted(tj.items(), key=lambda kv: (kv[1].get("city") or "", kv[1].get("name") or "")) if u not in used]
    print("hand records", hand_n, "auto Trulia records", len(blds) - hand_n)

    out_rows, brows = [], []
    for b in blds:
        rows, whys = [], []
        if b.get("_t"):
            rows += [dict(r) for r in b["_t"].get("rows") or []]
            if b["_t"].get("rows_why"):
                whys.append("trulia: " + b["_t"]["rows_why"])
        for u in b.get("agg", []):
            try:
                rr, why = al_rows(u)
            except Exception as e:
                rr, why = [], f"{type(e).__name__}: {str(e)[:120]}"
            if why and why != "ok":
                whys.append(f"{u.split('/')[2]}: {why}")
            rows += [dict(r) for r in rr]
        for fc in b.get("from_csv", []):
            with open(ROOT / "data" / "listings_raw" / fc["file"], newline="") as f:
                rows += [dict(r) for r in csv.DictReader(f)
                         if (fc.get("building_name") and r["building_name"] == fc["building_name"])
                         or (fc.get("url_contains") and fc["url_contains"] in r["url"])]
        for u in b.get("units", []):
            r = {k: "" for k in COLS}
            r.update(u)
            rows.append(r)
        rows = [r for r in rows if 0 < rent(r) <= CAP and str(r.get("beds")) in ("0", "1", "0.0", "1.0")]
        # the same unit can come from two sources (manager site and Trulia): keep the first, manager rows first
        seen, uniq = set(), []
        for r in sorted(rows, key=lambda r: (0 if "trulia" not in r.get("source_site", "") else 1, 0 if r.get("unit") else 1, rent(r))):
            k = (r.get("unit"), str(r.get("beds"))) if r.get("unit") else (r.get("listing_id"), str(r.get("beds")), r.get("listed_rent"))
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
        if not lat and b.get("address") and re.match(r"\d", b["address"]):
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
                if k == "concession_text" and r.get(k) and val and val not in r[k]:
                    r[k] = val + " | " + r[k]
                elif val not in ("", None, "unknown") or not r.get(k):
                    r[k] = val
            r["listing_id"] = "rs:" + slug + ":" + re.sub(r"^.*?:", "", str(r.get("listing_id") or r.get("unit") or "bldg"))
            r["building_name"] = b["name"]
            r["address"] = r.get("address") or b.get("address", "")
            r["city"] = r.get("city") or b["town"]
            r["state"] = "NY"
            r["zip"] = r.get("zip") or b.get("zip", "")
            r["lat"], r["lon"] = r.get("lat") or lat, r.get("lon") or lon
            r["building_url"] = b.get("url") or r.get("building_url", "")
            r["listing_type"] = r.get("listing_type") if r.get("listing_type") not in ("", None, "unknown") else "managed_building"
            src = f"building facts from {b.get('source_url', '')}" if b.get("source_url") else ""
            r["notes"] = "; ".join(x for x in (prefix + base_note, src, r.get("notes", "")) if x)
            return r

        def stub(prefix: str) -> dict:
            r = {k: "" for k in COLS}
            u = b.get("min_rent_url") or b.get("source_url") or b.get("url") or ""
            r.update(listing_id="bldg", source_site=re.sub(r"^www\.", "", u.split("/")[2]) if u else "none",
                     url=u, detail_level="building",
                     first_seen=b.get("min_rent_seen") or b.get("seen", ""), last_seen=b.get("min_rent_seen") or b.get("seen", ""),
                     listed_rent=b.get("min_rent", ""), price_basis=b.get("min_rent_basis", ""),
                     dogs="unknown", elevator="unknown", floor="unknown")
            return finish(r, prefix)

        best = sorted(rows, key=lambda r: (not in_window(r), rent(r)))
        if b.get("one_row"):
            best = best[:1]
        if v.startswith("fails"):
            pre = f"BUILDING_FAILS: {v[6:]}. "
            out_rows.append(finish(best[0], pre) if best else stub(pre))
        elif v == "blocked":
            out_rows.append(stub("BLOCKED: "))
        elif v.startswith("unconfirmed"):
            pre = f"UNCONFIRMED: {v[12:]}. "
            out_rows += [finish(r, pre) for r in best] or [stub(pre)]
        elif rows:
            pre = "" if nwin else "NO_AVAILABILITY: units listed but none available by 2026-12-15. "
            out_rows += [finish(r, pre) for r in best]
        else:
            out_rows.append(stub("NO_AVAILABILITY: "))
        brows.append({"name": b["name"], "address": b.get("address", ""), "town": b["town"], "zip": b.get("zip", ""),
                      "url": b.get("url", ""), "floors": b.get("floors", ""), "elevator": b.get("elevator", "unknown"),
                      "dogs": b.get("dogs", "unknown"), "weight_limit": b.get("weight", ""), "verdict": v,
                      "units_le_3000": len(rows), "units_in_window": nwin,
                      "min_rent_seen": min([rent(r) for r in rows], default=b.get("min_rent", "")),
                      "source_url": b.get("source_url", ""),
                      "notes": "; ".join([base_note] + whys)})
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
    c = Counter(re.sub(r":.*", "", b["verdict"]) for b in brows)
    print(f"buildings {len(brows)} {dict(c)}; rows written {n}; rows in window from passing buildings "
          f"{sum(b['units_in_window'] for b in brows if b['verdict'] == 'pass_with_units')}")
    for b in brows:
        if b["verdict"].startswith("pass"):
            print("  ", b["verdict"], b["name"], b["town"], b["units_le_3000"], b["units_in_window"], b["min_rent_seen"])


if __name__ == "__main__":
    main()
