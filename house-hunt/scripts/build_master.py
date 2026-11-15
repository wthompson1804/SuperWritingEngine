"""Build the two master tables every later step reads (docs/PLAN_V4_MASTER_MODEL_2026-11-15.md, Part 1).

  data/master_buildings.csv   one row per physical building (building_id)
  data/master_units.csv       one row per listed unit (listing_id), with its building's merged facts joined on
  data/master_conflicts.csv   where two sources disagree on a merged field
  data/reference/building_crosswalk.csv   every addr_key seen anywhere -> building_id

Merged building fields carry <field>, <field>_basis, <field>_source. Basis, in precedence order:
  confirmed        evidence pass, read on the building's own or its listing page (confirm_*, facts_*)
  community_page   management company's community page (community_facts.csv)
  amenities_page   amenities parsed from cached pages (building_amenities.csv)
  official_record  NYC PLUTO / city records
  stated           the listing row itself
  inferred         6+ floors -> elevator; floor from unit number; "high-rise" label
  unknown
Inputs: data/units.csv (listing rows that pass the gates, with lookup-tool columns), data/enriched*/ JSON,
data/reference/{building_amenities,community_facts,nyc_building_facts}.csv, data/evidence/*.
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA  # noqa: E402

PREC = ["confirmed", "community_page", "amenities_page", "official_record", "stated", "inferred"]
BLANK = {"", "nan", "none", "unknown", "no_mention", "?", "not_found", "unconfirmed", "none stated", "none_stated"}

ABBR = {"street": "st", "avenue": "ave", "boulevard": "blvd", "road": "rd", "drive": "dr", "place": "pl", "court": "ct",
        "lane": "ln", "terrace": "ter", "parkway": "pkwy", "highway": "hwy", "north": "n", "south": "s", "east": "e",
        "west": "w", "square": "sq", "plaza": "plz", "turnpike": "tpke"}


def is_blank(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip().lower() in BLANK


def street_key(address: str, zip5: str) -> str:
    """Normalized 'house-number street' + zip, with unit, city and state stripped."""
    a = str(address).lower()
    a = re.split(r",", a)[0]                                  # drop city/state after the first comma
    a = re.sub(r"(#|\bapt\.?|\bunit\b|\bste\b|\bsuite\b)\s*[\w-]+", " ", a)
    a = re.sub(r"[^\w\s-]", " ", a)
    toks = [ABBR.get(t, t) for t in a.split()]
    toks = [re.sub(r"(\d+)(st|nd|rd|th)$", r"\1", t) for t in toks]
    if toks and re.fullmatch(r"\d+-\d+", toks[0]):            # Queens-style 83-33 -> 8333
        toks[0] = toks[0].replace("-", "")
    return " ".join(toks) + "|" + str(zip5)[:5]


def house_no(key: str) -> str:
    m = re.match(r"(\d+)", key)
    return m.group(1) if m else ""


def money(text):
    m = re.search(r"\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", str(text))
    return float(m.group(1).replace(",", "")) if m else None


def cat(pattern):
    fs = glob.glob(str(DATA / "evidence" / pattern))
    if not fs:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False).assign(_file=Path(f).name) for f in fs], ignore_index=True)


class Merge:
    """Collects candidate values per (building, field) and resolves by precedence, logging conflicts."""

    def __init__(self):
        self.c: dict[tuple[str, str], list[tuple[int, str, str, str]]] = {}

    def add(self, bid, field, value, basis, source):
        if bid is None or is_blank(value):
            return
        self.c.setdefault((bid, field), []).append((PREC.index(basis), str(value).strip(), basis, str(source)[:300]))

    def resolve(self):
        rows, conflicts = {}, []
        for (bid, field), cands in self.c.items():
            cands.sort(key=lambda t: t[0])
            best = cands[0]
            rows.setdefault(bid, {})[field] = best[1]
            rows[bid][field + "_basis"] = best[2]
            rows[bid][field + "_source"] = best[3]
            vals = {t[1].lower() for t in cands}
            if len(vals) > 1 and field in CONFLICT_FIELDS:
                conflicts.append({"building_id": bid, "field": field, "chosen": best[1], "chosen_basis": best[2],
                                  "others": " | ".join(f"{t[1]} ({t[2]})" for t in cands[1:] if t[1].lower() != best[1].lower())})
        return rows, conflicts


CONFLICT_FIELDS = {"elevator", "dogs_allowed", "dog_weight_limit_lb", "parking_fee_monthly", "pet_rent_monthly",
                   "building_floors", "pool", "year_built"}


def yesno(v):
    s = str(v).strip().lower()
    if s.startswith(("yes", "true", "allowed")) or s in ("y", "24h", "24/7"):
        return "yes"
    if s.startswith(("no ", "no,", "not ")) or s in ("no", "n", "false", "none"):
        return "no"
    return ""


def main():
    U = pd.read_csv(DATA / "units.csv", dtype=str, keep_default_na=False, low_memory=False)

    # ------------------------------------------------------------------ building ids
    U["street_key"] = [street_key(a, z) for a, z in zip(U.address, U.zip5)]
    U["flat"], U["flon"] = pd.to_numeric(U.lat, errors="coerce"), pd.to_numeric(U.lon, errors="coerce")
    parent: dict[str, str] = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for k in U.street_key.unique():
        find(k)
    # same house number within ~30 m -> same building (aggregators spell the street differently)
    pts = U.dropna(subset=["flat"]).drop_duplicates("street_key")[["street_key", "flat", "flon"]]
    grid: dict[tuple[int, int], list[tuple[str, float, float]]] = {}
    for r in pts.itertuples():
        grid.setdefault((int(r.flat * 2500), int(r.flon * 2500)), []).append((r.street_key, r.flat, r.flon))
    for (gx, gy), items in grid.items():
        near = [it for dx in (-1, 0, 1) for dy in (-1, 0, 1) for it in grid.get((gx + dx, gy + dy), [])]
        for k, la, lo in items:
            for k2, la2, lo2 in near:
                if k2 <= k or house_no(k) != house_no(k2) or not house_no(k):
                    continue
                d = math.hypot((la - la2) * 111320, (lo - lo2) * 111320 * math.cos(math.radians(la)))
                if d <= 30:
                    parent[find(k2)] = find(k)
    U["building_id"] = ["b_" + hashlib.sha1(find(k).encode()).hexdigest()[:10] for k in U.street_key]
    xw = U[["addr_key", "building_id", "street_key"]].drop_duplicates("addr_key")
    A2B = dict(zip(xw.addr_key, xw.building_id))

    def bid_of(addr_key):
        return A2B.get(addr_key)

    M = Merge()
    # ------------------------------------------------------------------ 5/6. listing rows + inference
    for r in U.itertuples():
        b, src = r.building_id, r.url
        el_basis = getattr(r, "elevator_basis", "")
        if r.g_elevator == "pass":
            M.add(b, "elevator", "yes", "inferred" if el_basis.startswith("inferred") else ("official_record" if el_basis.startswith("nyc") else "stated"),
                  src if not el_basis.startswith("nyc") else "NYC PLUTO building class " + getattr(r, "pluto_class", ""))
        M.add(b, "dogs_allowed", yesno(r.dogs), "stated", src)
        M.add(b, "dog_policy_text", r.dog_policy_text, "stated", src)
        M.add(b, "dog_weight_limit_lb", r.dog_weight_limit_lb if re.fullmatch(r"[\d.]+", r.dog_weight_limit_lb or "") else "", "stated", src)
        M.add(b, "pet_rent_monthly", r.pet_rent if re.fullmatch(r"[\d.]+", r.pet_rent or "") else "", "stated", src)
        M.add(b, "parking_type", r.parking_type, "stated", src)
        M.add(b, "parking_fee_monthly", r.parking_fee if re.fullmatch(r"[\d.]+", r.parking_fee or "") else "", "stated", src)
        M.add(b, "building_floors", r.building_floors if re.fullmatch(r"[\d.]+", r.building_floors or "") else "", "stated", src)
        M.add(b, "laundry", r.laundry, "stated", src)
        M.add(b, "manager", r.manager, "stated", src)
        M.add(b, "utilities_included", r.utilities_included if r.utilities_included.lower() != "none listed as included" else "", "stated", src)
        M.add(b, "building_name", r.building_name, "stated", src)
        for col, fld in [("pluto_floors", "building_floors"), ("pluto_year", "year_built"), ("pluto_units", "unit_count")]:
            v = getattr(r, col, "")
            if re.fullmatch(r"[\d.]+", v or "") and float(v) > 0:
                M.add(b, fld, str(int(float(v))), "official_record", "NYC PLUTO (64uk-42ks)")
        for col, fld in [("community_pool", "pool"), ("community_gym", "gym"), ("community_controlled_access", "controlled_access"),
                         ("community_package_room", "package_room"), ("community_dog_park_pet_spa", "dog_amenities"),
                         ("community_required_fees", "required_fees_text"), ("community_building_type", "building_type")]:
            M.add(b, fld, getattr(r, col, ""), "community_page", "data/reference/community_facts.csv")

    # ------------------------------------------------------------------ 3. amenities parsed from cached pages
    af = DATA / "reference" / "building_amenities.csv"
    if af.exists():
        A = pd.read_csv(af, dtype=str, keep_default_na=False)
        amap = {"pool": "pool", "gym": "gym", "doorman_or_concierge": "doorman", "controlled_access": "controlled_access",
                "gated_or_garage_parking": "parking_type", "parking_fee_monthly": "parking_fee_monthly", "dog_amenities": "dog_amenities",
                "in_unit_laundry": "in_unit_laundry", "roof_deck_or_outdoor_space": "outdoor_space", "balcony_some_units": "balconies",
                "package_room": "package_room", "coworking_or_lounge": "lounge_or_coworking", "elevator_stated": "elevator",
                "year_built": "year_built", "total_floors": "building_floors", "unit_count": "unit_count", "management_company": "manager"}
        for r in A.to_dict("records"):
            b = bid_of(r["addr_key"])
            for col, fld in amap.items():
                v = r.get(col, "")
                if fld == "parking_type" and v == "parking_type_unknown":
                    v = ""
                M.add(b, fld, v, "amenities_page", r.get("source_url", ""))

    # ------------------------------------------------------------------ 1. evidence pass
    C, F, L = cat("confirm_batch_*.csv"), cat("facts_batch_*.csv"), cat("live_check_batch_*.csv")
    unit_floor, unit_floor_src = {}, {}
    if len(C):
        for r in C.itertuples():
            b, fact, val = bid_of(r.addr_key), r.fact.lower(), r.value
            if b is None or r.status == "unconfirmed":
                continue
            if fact.startswith("elevator"):
                M.add(b, "elevator", yesno(val) or ("no" if r.status == "contradicts" else ""), "confirmed", r.source_url)
            elif fact.startswith("dogs_allowed"):
                M.add(b, "dogs_allowed", "no" if r.status == "contradicts" else (yesno(val) or "yes"), "confirmed", r.source_url)
            elif fact.startswith("dog_weight"):
                if "no weight limit" in val.lower() or "no limit" in val.lower():
                    M.add(b, "dog_weight_limit_lb", "no limit", "confirmed", r.source_url)
                else:
                    m = re.search(r"(\d{2,3})", val)
                    if m and r.status == "confirmed":
                        M.add(b, "dog_weight_limit_lb", m.group(1), "confirmed", r.source_url)
            elif fact.startswith("building_floors"):
                M.add(b, "building_floors", money(val), "confirmed", r.source_url)
            elif fact.startswith("floor"):
                pairs = re.findall(r"([\w-]+)\s*:\s*floor\s*(\d+)", val)
                if pairs:
                    for un, fl in pairs:
                        unit_floor[(b, un.lower())] = int(fl); unit_floor_src[(b, un.lower())] = r.source_url
                elif re.fullmatch(r"\d+", val.strip()):
                    unit_floor[(b, "*")] = int(val); unit_floor_src[(b, "*")] = r.source_url
    if len(F):
        fmap = [("parking_fee", "parking_fee_monthly", "money"), ("pet_rent", "pet_rent_monthly", "money"),
                ("required_monthly_fee", "required_fees_text", "text"), ("required_fees", "required_fees_text", "text"),
                ("amenity_fee", "required_fees_text", "text"), ("additional_fees", "required_fees_text", "text"),
                ("utilities", "utilities_included", "text"), ("pool", "pool", "text"), ("doorman", "doorman", "text"),
                ("concierge", "doorman", "text"), ("year_built", "year_built", "year"), ("total_units", "unit_count", "money"),
                ("units_in_building", "unit_count", "money"), ("units", "unit_count", "money"), ("building_floors", "building_floors", "money"),
                ("management_company", "manager", "text"), ("registered_manager", "manager", "text"), ("parking_type", "parking_type", "text"),
                ("garage", "parking_type", "text"), ("pet_fee", "pet_one_time_fee_text", "text"), ("laundry", "laundry", "text"),
                ("concession", "concession_text_evidence", "text"), ("lease_terms", "lease_terms_text", "text"),
                ("rent_regulation", "rent_regulation", "text"), ("income_requirement", "income_requirement", "text"),
                ("listing_warning", "listing_warning", "text")]
        for r in F.itertuples():
            b, fact = bid_of(r.addr_key), r.fact.lower().strip()
            if b is None:
                continue
            for prefix, fld, kind in fmap:
                if fact.startswith(prefix):
                    v = r.value
                    if kind == "money":
                        v = money(v) if not is_blank(v) and money(v) is not None else ""
                        if fld in ("parking_fee_monthly", "pet_rent_monthly") and v != "" and not (0 < v <= 1000):
                            v = ""
                    elif kind == "year":
                        m = re.search(r"(18|19|20)\d{2}", str(v)); v = m.group(0) if m else ""
                    M.add(b, fld, v, "confirmed", r.source_url)
                    break

    rows, conflicts = M.resolve()

    # ------------------------------------------------------------------ building table
    bfirst = U.drop_duplicates("building_id").set_index("building_id")
    keep_from_units = ["address", "city", "state", "zip5", "lat", "lon", "hood", "hood_id", "hood_area"] + \
        [c for c in U.columns if c.startswith(("drive_", "toll_", "transit_", "police_", "crime_", "near_", "park_", "dog_park_", "restaurants_",
                                               "bars_", "cafes_", "music_", "supermarket", "coast_", "beach_", "open_water_", "train_station",
                                               "motorway_", "util_", "last_sat", "pluto_"))]
    B = bfirst[[c for c in keep_from_units if c in bfirst.columns]].copy()
    B = B.join(pd.DataFrame.from_dict(rows, orient="index"))
    B["addr_keys"] = U.groupby("building_id").addr_key.agg(lambda s: " || ".join(sorted(set(s))))
    B["n_listed_units"] = U.groupby("building_id").listing_id.count()

    # lookup-tool fields not yet flattened: violent crime near the building, evening share, transit extras
    extra = {}
    for f in glob.glob(str(DATA / "enriched" / "*.json")):
        e = json.load(open(f)); b = bid_of(e.get("addr_key"))
        if b is None:
            continue
        cn = (e.get("crime_near") or {}).get("counts") or {}
        vb = ((e.get("crime_near") or {}).get("vs_baseline") or {}).get("comparison") or {}
        d = {}
        for k in ("robbery", "felony_assault", "burglary", "grand_larceny_motor_vehicle", "theft_from_vehicle", "vehicle_parts_theft", "vehicle_criminal_mischief"):
            if k in cn:
                d[f"near250_{k}_24m"] = cn[k].get("last_24_months")
                d[f"near250_{k}_evening_share"] = cn[k].get("share_19_to_24_24m")
                d[f"near250_{k}_2023"], d[f"near250_{k}_2025"] = cn[k].get("2023"), cn[k].get("2025")
            if k in vb:
                d[f"near250_{k}_borough_median"] = vb[k].get("borough_median")
                d[f"near250_{k}_above_borough_p80"] = vb[k].get("above_borough_p80")
        ts, tr = e.get("transit_sat") or {}, e.get("transit_sun_return") or {}
        g = lambda o, k: (o.get(k) or {}).get("value") if isinstance(o.get(k), dict) else o.get(k)
        d["transit_sat_transfers"] = g(ts, "transfers"); d["transit_sat_summary"] = g(ts, "leg_summary")
        d["transit_last_sat_departure_from_jamaica"] = g(ts, "last_departure_from_jamaica_sat")
        d["transit_sun_return_fastest"], d["transit_sun_return_median"] = g(tr, "fastest_minutes"), g(tr, "median_minutes")
        yrs = (e.get("crime_agency") or {}).get("years") or []
        for y in yrs:
            if y.get("violent_per_1000") is not None:
                d[f"agency_violent_per_1000_{y.get('year')}"] = y.get("violent_per_1000")
                d[f"agency_property_per_1000_{y.get('year')}"] = y.get("property_per_1000")
                d[f"agency_burglary_per_1000_{y.get('year')}"] = y.get("burglary_per_1000")
        extra[b] = d
    E = pd.DataFrame.from_dict(extra, orient="index")
    B = B.drop(columns=[c for c in E.columns if c in B.columns]).join(E)
    # NYC records and avoid inputs, keyed through the crosswalk
    nf = DATA / "evidence" / "nyc_records.csv"
    if nf.exists():
        N = pd.read_csv(nf, dtype=str, keep_default_na=False)
        N["building_id"] = N.addr_key.map(A2B)
        N = N.dropna(subset=["building_id"])
        N["k"] = "nycrec_" + N.record_type.str.lower().str.replace(r"[^a-z0-9]+", "_", regex=True).str.strip("_") + "__" + N.period
        piv = N.drop_duplicates(["building_id", "k"]).pivot(index="building_id", columns="k", values="count")
        B = B.join(piv)
    ff = DATA / "evidence" / "nyc_records_flags.csv"
    if ff.exists():
        NF = pd.read_csv(ff, dtype=str, keep_default_na=False); NF["building_id"] = NF.addr_key.map(A2B)
        B["nyc_record_flags"] = NF[NF.flag != "none"].groupby("building_id").flag.agg(lambda s: ";".join(sorted(set(s))))
    B.index.name = "building_id"
    B.to_csv(DATA / "master_buildings.csv")
    pd.DataFrame(conflicts).to_csv(DATA / "master_conflicts.csv", index=False)
    xw.to_csv(DATA / "reference" / "building_crosswalk.csv", index=False)

    # ------------------------------------------------------------------ unit table
    unit_cols = ["listing_id", "building_id", "addr_key", "source_site", "url", "building_url", "also_seen_at", "detail_level", "first_seen",
                 "last_seen", "unit", "beds", "baths", "sqft", "listed_rent", "price_basis", "concession_text", "available_date_text",
                 "available_date", "floor", "floor_used", "g_floor", "listing_age_days", "stale_listing", "photo_url", "raw_path", "notes",
                 "other_monthly_fees_json", "listing_type", "gate_status"]
    MU = U[[c for c in unit_cols if c in U.columns]].copy()
    # live check: status and price now
    if len(L):
        L["building_id"] = L.addr_key.map(A2B)
        L["u"] = L.unit.str.strip().str.lower()
        Lk = L.dropna(subset=["building_id"]).drop_duplicates(["building_id", "u"]).set_index(["building_id", "u"])
        key = list(zip(MU.building_id, MU.unit.str.strip().str.lower()))
        for col, new in [("status", "live_status"), ("price_now", "live_price"), ("available_now_text", "live_available_text"), ("checked_at", "live_checked_at"), ("notes", "live_notes")]:
            MU[new] = [Lk[col].get(k, "") if k in Lk.index else "" for k in key]
    else:
        MU["live_status"] = ""
    # floor: confirmed per unit > stated/inferred from the listing
    fl, flb, fls = [], [], []
    for b, un, stated, used, gf in zip(MU.building_id, MU.unit.str.strip().str.lower(), MU.floor, MU.floor_used, MU.g_floor):
        if (b, un) in unit_floor:
            fl.append(unit_floor[(b, un)]); flb.append("confirmed"); fls.append(unit_floor_src[(b, un)])
        elif (b, "*") in unit_floor and MU.building_id.eq(b).sum() == 1:
            fl.append(unit_floor[(b, "*")]); flb.append("confirmed"); fls.append(unit_floor_src[(b, "*")])
        elif re.fullmatch(r"[\d.]+", str(stated)):
            fl.append(int(float(stated))); flb.append("stated"); fls.append("")
        elif re.fullmatch(r"[\d.]+", str(used)):
            fl.append(int(float(used))); flb.append("inferred"); fls.append("unit number")
        else:
            fl.append(""); flb.append("unknown"); fls.append("")
    MU["unit_floor"], MU["unit_floor_basis"], MU["unit_floor_source"] = fl, flb, fls
    bcols = [c for c in B.columns if c not in MU.columns]
    MU = MU.join(B[bcols], on="building_id")
    MU.to_csv(DATA / "master_units.csv", index=False)

    print(f"buildings: {len(B)} (from {U.addr_key.nunique()} addr_keys); units: {len(MU)}; conflicts: {len(conflicts)}")
    for f in ["elevator", "dogs_allowed", "dog_weight_limit_lb", "parking_type", "parking_fee_monthly", "pet_rent_monthly", "pool", "doorman", "year_built", "manager", "utilities_included"]:
        if f + "_basis" in B:
            print(f"  {f:22s}", B[f + "_basis"].fillna("unknown").value_counts().to_dict())
    print("  unit floor basis", MU.unit_floor_basis.value_counts().to_dict(), "| live status", MU.live_status.replace("", "not checked").value_counts().to_dict())


if __name__ == "__main__":
    main()
