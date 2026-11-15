"""Region inventory, building-first: Suffolk County, NY (docs/REGION_AGENT_BRIEF.md).

Stages (each idempotent; all fetches go through lib.cached_get, >= 2 s per host, robots checked):
  python3 scripts/h_region_suffolk.py trulia   # fetch the Trulia /building/ page of every Suffolk community that the
                                               # Trulia ZIP search already found (cards in data/listings_raw/trulia.csv)
                                               # -> raw/region_suffolk/trulia_buildings.jsonl (facts + unit rows)
  python3 scripts/h_region_suffolk.py build    # (h_region_suffolk_build.py) merge the Trulia stage output with the
                                               # hand-read facts in scripts/h_region_suffolk_facts.py and rows other
                                               # harvesters already read -> data/listings_raw/region_suffolk.csv,
                                               #                            data/reference/region_buildings_suffolk.csv
Helper scripts used to read pages by hand (all cached, robots-checked, >= 2 s per host):
  h_region_suffolk_greystar.py  Greystar property pages of the 11 Suffolk communities -> raw/region_suffolk/greystar_buildings.jsonl
  h_region_suffolk_al.py        Apartment List property pages -> raw/region_suffolk/al_buildings.jsonl
  h_region_suffolk_alcity.py    Apartment List town pages (property enumeration) -> raw/region_suffolk/al_city_props.json
  h_region_suffolk_zumper.py    Zumper building pages -> raw/region_suffolk/zumper_buildings.jsonl
  h_region_suffolk_zcity.py     Zumper town pages (building enumeration) -> raw/region_suffolk/zumper_city_buildings.json
  h_region_suffolk_probe.py     any leasing-site page: keyword contexts
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from h_mgmt_common import COLS, upsert, polite_get, BotWall, weight_limit, dog_status, jdump  # noqa: E402

ROOT = lib.ROOT
RAWD = ROOT / "raw" / "region_suffolk"
RAWD.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "data" / "listings_raw" / "region_suffolk.csv"
BLD = ROOT / "data" / "reference" / "region_buildings_suffolk.csv"
T_OUT = RAWD / "trulia_buildings.jsonl"
G_OUT = RAWD / "greystar_buildings.jsonl"

# Nassau ZIPs inside the 117xx range (everything else in 117xx / 119xx is Suffolk); 11735 Farmingdale straddles the line.
NASSAU_117 = {"11709", "11710", "11714", "11732", "11753", "11756", "11758", "11762", "11765", "11771", "11783",
              "11791", "11793", "11797", "11801", "11802", "11803", "11804"}


def is_suffolk_zip(z: str) -> bool:
    z = (z or "")[:5]
    return (z.startswith("117") or z.startswith("119")) and z not in NASSAU_117


def load_jsonl(p: Path) -> dict:
    d = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                o = json.loads(line)
                d[o["url"]] = o
    return d


def save_jsonl(p: Path, d: dict) -> None:
    tmp = p.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(o, ensure_ascii=False) + "\n" for o in d.values()))
    tmp.replace(p)


# ------------------------------------------------------------------ Trulia building pages
def stage_trulia(extra_urls: list[str]) -> None:
    import h_trulia as T
    T.DELAY = 6.0  # another harvester may be on the same host; stay well under one request / 2 s combined
    csv.field_size_limit(10 ** 9)
    urls: dict[str, str] = {}
    with open(ROOT / "data" / "listings_raw" / "trulia.csv", newline="") as f:
        for r in csv.DictReader(f):
            u = r["building_url"] or r["url"]
            if "/building/" in u and is_suffolk_zip(r["zip"]):
                urls.setdefault(u, r["building_name"])
    for u in extra_urls:
        urls.setdefault(u, "")
    done = load_jsonl(T_OUT)
    print("trulia building urls:", len(urls), "already summarised:", len(done), flush=True)
    for i, (u, name) in enumerate(sorted(urls.items())):
        if u in done:
            continue
        try:
            nd, meta = T.fetch(u, refresh_hours=48)
        except T.Blocked as e:
            print("BLOCKED, stopping:", e, flush=True)
            break
        if nd is None:
            done[u] = {"url": u, "name": name, "status": meta.get("status"), "gone": True}
            save_jsonl(T_OUT, done)
            continue
        hd = (nd.get("props") or {}).get("homeDetails") or {}
        if not hd:
            done[u] = {"url": u, "name": name, "status": meta.get("status"), "no_details": True}
            save_jsonl(T_OUT, done)
            continue
        feats, hl = T.flat_features(hd.get("features")), T.highlighted(hd.get("features"))
        desc = ((hd.get("description") or {}).get("value") or "")
        afr = hd.get("activeForRentListing") or {}
        pets = T.pet_fields(afr.get("petPolicy"), feats, hl)
        summ = (hd.get("petPolicy") or {}).get("formattedPetsAllowed")
        bf = T.building_feature_fields(feats, hl, desc)
        try:
            rows, why = T.parse_building(hd, meta) if (hd.get("floorPlans") or (hd.get("url") or "").startswith("/building/")) else ([], "not a building page")
        except Exception as e:  # keep going; record the parse problem
            rows, why = [], f"parse error {e!r}"
        loc = hd.get("location") or {}
        co = loc.get("coordinates") or {}
        ud = hd.get("unitDetails") or {}
        allplans = []
        for g in ((hd.get("floorPlans") or {}).get("floorPlanGroups") or []):
            for plan in g.get("plans") or []:
                for it in (plan.get("units") or [plan]):
                    pr = (it.get("priceRange") or {}).get("min")
                    bmin, _ = T.beds_of(it.get("bedrooms"))
                    allplans.append([bmin, pr, it.get("name") or plan.get("name"), it.get("availabilityText"), it.get("availabilityDate")])
        keyfeat = [f"{sn + ': ' if sn else ''}{n}{': ' + v if v else ''}" for cn, sn, n, v in feats
                   if re.search(r"(?i)elevator|stor(y|ies)|floors|levels|year built|gated|controlled|doorman|pool|dog|pet|"
                                r"package|fitness|parking|garage|senior|55|age|income|affordable|laundry|washer", f"{sn} {n} {v}")]
        done[u] = {
            "url": u, "name": hd.get("name") or name, "address": loc.get("streetAddress"), "city": loc.get("city"),
            "zip": loc.get("zipCode"), "lat": co.get("latitude"), "lon": co.get("longitude"),
            "retrieved_at": meta["retrieved_at"], "raw_path": meta.get("path", ""), "status": meta.get("status"),
            "elevator": bf["elevator"], "building_floors": bf["building_floors"], "bf_notes": bf["_notes"],
            "desc_elevator": [desc[max(0, m.start() - 80):m.end() + 80] for m in re.finditer(r"(?i)elevator|walk[- ]?up|stor(y|ies)\b", desc)][:4],
            "desc_age": bool(re.search(r"(?i)\b55\s?\+|\b62\s?\+|senior|active adult|age[- ]restricted", (hd.get("name") or "") + " " + desc)),
            "dogs": pets["dogs"], "dog_policy_text": pets["dog_policy_text"], "pets_summary": summ,
            "dog_weight_limit_lb": pets["dog_weight_limit_lb"], "pet_rent": pets["pet_rent"],
            "parking_type": bf["parking_type"], "utilities_included": bf["utilities_included"], "laundry": bf["laundry"],
            "key_features": keyfeat[:60], "units_total": ud.get("totalUnitsInBuilding"),
            "units_available": ud.get("availableRentalUnits"),
            "manager": (((hd.get("planVisit") or {}).get("propertyManagementCompany") or {}).get("name") or ""),
            "plans": allplans[:80], "rows": rows, "rows_why": why,
        }
        save_jsonl(T_OUT, done)
        if i % 10 == 0:
            print(i, hd.get("name"), "| elev", bf["elevator"], "| dogs", pets["dogs"], pets["dog_weight_limit_lb"], "| rows", len(rows), flush=True)
    print("summarised:", len(done), flush=True)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "trulia":
        stage_trulia(sys.argv[2:])
    elif stage == "build":
        from h_region_suffolk_build import main as build_main
        build_main()
    else:
        print(__doc__)
