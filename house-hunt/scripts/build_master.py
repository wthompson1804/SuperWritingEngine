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
import parsers  # noqa: E402

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
    """First money figure ('1500' -> 1500, not 150: independent check W15)."""
    return parsers.money(text)


AGGREGATORS = ("trulia", "zumper", "apartmentlist", "zillow", "craigslist", "apartments.com", "rent.com")


def is_aggregator(site) -> bool:
    return any(a in str(site).lower() for a in AGGREGATORS)


def dist_m(la, lo, la2, lo2) -> float:
    return math.hypot((la - la2) * 111320, (lo - lo2) * 111320 * math.cos(math.radians(la)))


def assign_building_ids(U):
    """Adds street_key, flat, flon (the listing's own coordinates) and building_id. Buildings are matched on the
    normalized street address + ZIP, then on the same house number within about 30 m."""
    U["street_key"] = [street_key(a, z) for a, z in zip(U.address, U.zip5)]
    lat_col = "lat_listing" if "lat_listing" in U.columns else "lat"
    lon_col = "lon_listing" if "lon_listing" in U.columns else "lon"
    U["flat"], U["flon"] = pd.to_numeric(U[lat_col], errors="coerce"), pd.to_numeric(U[lon_col], errors="coerce")
    parent: dict[str, str] = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for k in U.street_key.unique():
        find(k)
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
                if dist_m(la, lo, la2, lo2) <= 30:
                    parent[find(k2)] = find(k)
    U["building_id"] = ["b_" + hashlib.sha1(find(k).encode()).hexdigest()[:10] for k in U.street_key]
    return U


COORD_DISAGREE_M = 150


def census_address(address, city, state, zip5):
    """Census geocoder, one-line address. Returns (lat, lon, matched address, url) or None. Cached in raw/census_geocoder."""
    from lib import get_json
    street = re.split(r",", str(address))[0]
    street = re.sub(r"(#|\bapt\.?|\bunit\b|\bste\b|\bsuite\b)\s*[\w-]+", " ", street, flags=re.I).strip()
    line = f"{street}, {city}, {state} {str(zip5).zfill(5)}"
    try:
        js, meta = get_json("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress", "census_geocoder",
                            params={"address": line, "benchmark": "Public_AR_Current", "format": "json"})
        ms = js["result"]["addressMatches"]
    except Exception:
        return None
    if not ms:
        return None
    c = ms[0]["coordinates"]
    return float(c["y"]), float(c["x"]), ms[0].get("matchedAddress", ""), meta.get("url", "")


def building_coords(U):
    """One coordinate per building (independent check W7), not the first listing row's.

    Listing rows of a building that agree within 150 m: the row nearest their median (a real source coordinate).
    Rows that disagree by more: the Census geocoder's point for the normalized address; if it finds no match, the
    largest group of agreeing rows, flagged 'unverified'. Needs assign_building_ids first.
    Returns a frame indexed by building_id: lat, lon, coord_basis, coord_spread_m, coord_note.
    """
    out = {}
    for b, g in U.groupby("building_id"):
        pts = g.dropna(subset=["flat", "flon"])
        if not len(pts):
            out[b] = {"lat": np.nan, "lon": np.nan, "coord_basis": "none", "coord_spread_m": np.nan, "coord_note": ""}
            continue
        P_ = list(zip(pts.flat, pts.flon))
        la0, lo0 = float(np.median(pts.flat)), float(np.median(pts.flon))
        spread = max((dist_m(a, o, a2, o2) for i, (a, o) in enumerate(P_) for a2, o2 in P_[i + 1:]), default=0.0)
        if spread <= COORD_DISAGREE_M:
            i = int(np.argmin([dist_m(a, o, la0, lo0) for a, o in P_]))
            out[b] = {"lat": P_[i][0], "lon": P_[i][1], "coord_basis": "listing rows agree", "coord_spread_m": round(spread), "coord_note": ""}
            continue
        r0 = g.iloc[0]
        hit = census_address(r0.address, r0.city, r0.state, r0.zip5)
        srcs = "; ".join(f"{s}: {a:.5f},{o:.5f}" for s, a, o in pts.drop_duplicates(["flat", "flon"])[["source_site", "flat", "flon"]].itertuples(index=False))[:300]
        if hit:
            out[b] = {"lat": hit[0], "lon": hit[1], "coord_basis": "census_geocoder", "coord_spread_m": round(spread),
                      "coord_note": f"listing rows disagree by {spread:.0f} m ({srcs}); Census geocoder matched '{hit[2]}'"}
        else:
            groups = []
            for a, o in P_:
                for gr in groups:
                    if dist_m(a, o, gr[0][0], gr[0][1]) <= COORD_DISAGREE_M:
                        gr.append((a, o)); break
                else:
                    groups.append([(a, o)])
            big = max(groups, key=len)
            out[b] = {"lat": big[0][0], "lon": big[0][1], "coord_basis": "listing majority, unverified", "coord_spread_m": round(spread),
                      "coord_note": f"listing rows disagree by {spread:.0f} m ({srcs}); the Census geocoder found no match"}
    return pd.DataFrame.from_dict(out, orient="index")


def cat(pattern):
    fs = glob.glob(str(DATA / "evidence" / pattern))
    if not fs:
        return pd.DataFrame()
    return pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False).assign(_file=Path(f).name) for f in fs], ignore_index=True)


class Merge:
    """Collects candidate values per (building, field) and resolves by precedence, logging conflicts.

    TEXT_APPEND fields keep every source's sentence (joined with ' || ', best basis first) because one sentence
    rarely says everything: all_in.py parses each part and never adds two parts together.
    """

    def __init__(self):
        self.c: dict[tuple[str, str], list[tuple[int, str, str, str]]] = {}

    def add(self, bid, field, value, basis, source):
        if bid is None or is_blank(value):
            return
        self.c.setdefault((bid, field), []).append((PREC.index(basis), str(value).strip(), basis, str(source)[:300]))

    def resolve(self):
        rows, conflicts = {}, []
        for (bid, field), cands in self.c.items():
            cands.sort(key=lambda t: t[0])                # stable: file order within one basis
            best = cands[0]
            if field in TEXT_APPEND:
                parts = list(dict.fromkeys(t[1] for t in cands))
                rows.setdefault(bid, {})[field] = " || ".join(parts)[:1500]
            else:
                rows.setdefault(bid, {})[field] = best[1]
            rows[bid][field + "_basis"] = best[2]
            rows[bid][field + "_source"] = best[3]
            # compare as numbers where both are numbers: "6" vs "6.0" is not a conflict (independent check, cosmetic)
            vals = {parsers.num_str(t[1]) for t in cands}
            if len(vals) > 1 and field in CONFLICT_FIELDS:
                conflicts.append({"building_id": bid, "field": field, "chosen": best[1], "chosen_basis": best[2],
                                  "others": " | ".join(dict.fromkeys(f"{t[1]} ({t[2]})" for t in cands[1:] if parsers.num_str(t[1]) != parsers.num_str(best[1])))})
        return rows, conflicts


CONFLICT_FIELDS = {"elevator", "dogs_allowed", "dog_weight_limit_lb", "parking_fee_monthly", "pet_rent_monthly",
                   "building_floors", "year_built"}
TEXT_APPEND = {"required_fees_text", "utilities_included", "concession_text_evidence", "optional_fees_text", "parking_text",
               "listing_warning", "price_term_text", "elevator_evidence_open", "dogs_evidence_open"}
GOOD_FLOORCOUNT = ("confirmed", "official_record", "community_page")     # floor counts trusted to bound a unit-label reading


def yesno(v):
    s = str(v).strip().lower()
    if s.startswith(("yes", "true", "allowed")) or s in ("y", "24h", "24/7"):
        return "yes"
    if s.startswith(("no ", "no,", "not ")) or s in ("no", "n", "false", "none"):
        return "no"
    return ""


def add_parking(M, b, text, basis, source, number=None):
    """Parking sentence -> parking_fee_monthly (+ note, options), keeping the sentence in parking_text (W4, A1-A16)."""
    if is_blank(text) and number is None:
        return
    pk = parsers.parse_parking(text) if not is_blank(text) else {"fee": None, "note": "", "options": "", "included": False}
    fee = pk["fee"] if pk["fee"] is not None else number
    if not is_blank(text) and (pk["fee"] is not None or "$" in str(text) or re.search(r"\d", str(text))):
        M.add(b, "parking_text", str(text)[:400], basis, source)
    if fee is not None and 0 <= fee <= 1000:
        M.add(b, "parking_fee_monthly", f"{fee:g}", basis, source)
        M.add(b, "parking_fee_note", pk["note"] or ("as given in the source's fee field" if pk["fee"] is None else "single price stated"), basis, source)
        if pk["options"]:
            M.add(b, "parking_options", pk["options"], basis, source)
    elif pk["note"] and pk["note"] != "fee not stated":
        M.add(b, "parking_fee_note", pk["note"], basis, source)
        if pk["options"]:
            M.add(b, "parking_options", pk["options"], basis, source)


def add_pet_rent(M, b, text, basis, source, default_monthly=True):
    v, note = parsers.parse_pet_rent(text, default_monthly)
    if v is not None:
        M.add(b, "pet_rent_monthly", f"{v:g}", basis, source)
        if note:
            M.add(b, "pet_rent_note", note, basis, source)


def apply_fact(M, b, fact, value, quote, url):
    """Route one evidence fact row (facts_batch_*.csv) to the master fields. Returns True when the fact was mapped."""
    f = fact.lower().strip()
    v = quote if str(value).strip().lower() == "see quote" and not is_blank(quote) else value
    if is_blank(v):
        return f.startswith(KNOWN_FACT_PREFIXES)
    C = "confirmed"
    if f.startswith(("parking", "garage")):
        # type: only when the sentence names a kind of parking, so "1 spaces available" does not hide a lower source
        kind = "garage" if f.startswith("garage") and yesno(v) == "yes" else parsers.parking_kind(v)
        if kind:
            M.add(b, "parking_type", kind if kind == str(v).strip().lower() or f.startswith("garage") else f"{kind}: {str(v)[:90]}", C, url)
        if not f.startswith("garage"):
            add_parking(M, b, v, C, url)
    elif f.startswith(("pet_rent", "dog:monthly_dog_rent", "dogs_rent", "dog_rent")):
        add_pet_rent(M, b, v, C, url, True)
    elif f.startswith("pet_fee"):
        add_pet_rent(M, b, v, C, url, False)
        M.add(b, "pet_one_time_fee_text", v, C, url)
    elif f.startswith("fee:"):
        kind = f.split(":", 1)[1]
        if re.search(r"park|garage|carport", str(v), re.I) and "monthly" in kind:
            add_parking(M, b, (str(v) if re.search(r"\$", str(v)) else str(v) + ": fee not stated"), C, url)
        elif re.search(r"\b(dog|pet)\b.*rent", str(v), re.I) and "monthly" in kind:
            add_pet_rent(M, b, v, C, url, True)
        elif kind.startswith("monthlyrequired") and not re.search(r"\bpet\b|\bdog\b|\bcat\b|base rent", str(v), re.I):
            M.add(b, "required_fees_text", v, C, url)
        elif kind.startswith("monthlyoptional") and not re.search(r"\bpet\b|\bdog\b|\bcat\b", str(v), re.I):
            M.add(b, "optional_fees_text", v, C, url)
    elif f.startswith(("required_monthly_fee", "required_fees", "amenity_fee", "additional_fees", "fees_and_utilities")):
        M.add(b, "required_fees_text", v, C, url)
        if f.startswith("fees_and_utilities") and re.search(r"utilities included", str(v), re.I):
            M.add(b, "utilities_included", re.search(r"utilities included.*", str(v), re.I).group(0), C, url)
    elif f.startswith("optional_monthly_fee"):
        M.add(b, "optional_fees_text", v, C, url)
    elif f.startswith("utilities"):
        M.add(b, "utilities_included", v, C, url)
    elif f.startswith("pool"):
        M.add(b, "pool", v, C, url)
        if "concierge" in f:
            M.add(b, "doorman", v, C, url)
    elif f.startswith(("doorman", "concierge")):
        M.add(b, "doorman", v, C, url)
    elif f.startswith("year_built"):
        m = re.search(r"(18|19|20)\d{2}", str(v))
        M.add(b, "year_built", m.group(0) if m else "", C, url)
    elif f.startswith(("total_units", "units_in_building", "units")):
        n = money(v)
        M.add(b, "unit_count", f"{n:g}" if n else "", C, url)
    elif f.startswith("building_floors"):
        n = money(v)
        M.add(b, "building_floors", f"{n:g}" if n else "", C, url)
    elif f.startswith(("management_company", "registered_manager")):
        M.add(b, "manager", v, C, url)
    elif f.startswith("laundry"):
        M.add(b, "laundry", v, C, url)
    elif f.startswith(("concession", "special")):
        M.add(b, "concession_text_evidence", v, C, url)
    elif f.startswith("lease_terms"):
        M.add(b, "lease_terms_text", v, C, url)
    elif f.startswith(("lease_term_of_listed_price", "lease_term_priced", "price_basis", "lease_and_deposit")):
        # the term the listed price belongs to (independent check 2, D8): kept as text, read per unit below
        M.add(b, "price_term_text", f"{v} | {quote}" if not is_blank(quote) and str(quote) != str(v) else v, C, url)
    elif f.startswith(("address_mismatch", "listing_address_mismatch", "address_note")):
        M.add(b, "listing_warning", "address: " + str(v), C, url)          # D6: was not mapped
    elif f.startswith("rent_regulation"):
        M.add(b, "rent_regulation", v, C, url)
    elif f.startswith(("income_requirement", "income_restrict")):
        M.add(b, "income_requirement", ("income-restricted: " if f.startswith("income_restrict") and not parsers.income_restricted(v) else "") + str(v), C, url)
    elif f.startswith("listing_warning"):
        M.add(b, "listing_warning", v, C, url)
    elif f.startswith("building_type"):
        M.add(b, "building_type", v, C, url)
    elif f.startswith(("dog_amenit", "dog_park", "dog_run")):
        M.add(b, "dog_amenities", v, C, url)
    elif f.startswith(("dog_weight_limit_lb", "pet_limit", "pet_restrictions")):
        kind, lb = parsers.parse_dog_weight(v)
        if kind == "limit" and f.startswith("dog_weight_limit_lb"):
            M.add(b, "dog_weight_limit_lb", f"{lb:g}", C, url)
        elif kind == "size_only":
            M.add(b, "dog_size_only", "yes: " + str(v)[:120], C, url)
    else:
        return False
    return True


KNOWN_FACT_PREFIXES = ("parking", "garage", "pet_rent", "dog", "pet_fee", "fee:", "required", "amenity_fee", "additional_fees", "fees_and",
                       "optional_monthly_fee", "utilities", "pool", "doorman", "concierge", "year_built", "total_units", "units", "building_floors",
                       "management_company", "registered_manager", "laundry", "concession", "special", "lease_terms", "rent_regulation",
                       "income", "listing_warning", "building_type", "pet_limit", "pet_restrictions", "lease_term", "price_basis", "lease_and",
                       "address_mismatch", "listing_address_mismatch", "address_note")


def main():
    U = pd.read_csv(DATA / "units.csv", dtype=str, keep_default_na=False, low_memory=False)
    U["zip5"] = U.zip5.map(lambda z: z.zfill(5) if re.fullmatch(r"\d{3,5}", z) else z)        # NJ / CT ZIPs keep their leading zero
    for c in ("floor_basis", "floor_label_kind", "community_parking_text", "community_utilities_included", "community_utilities_resident_pays"):
        if c not in U.columns:
            U[c] = ""

    # ------------------------------------------------------------------ building ids and coordinates
    U = assign_building_ids(U)
    xw = U[["addr_key", "building_id", "street_key"]].drop_duplicates("addr_key")
    A2B = dict(zip(xw.addr_key, xw.building_id))
    if "coord_basis" in U.columns:            # scripts/enrich_units.py already settled one coordinate per building
        G = U.drop_duplicates("building_id").set_index("building_id")[["lat", "lon", "coord_basis", "coord_spread_m", "coord_note"]]
    else:
        G = building_coords(U)

    def bid_of(addr_key):
        return A2B.get(addr_key)

    # NYC tax lot (independent check 2, D16): PLUTO facts are used only when the lot's address IS the listing's address.
    # A neighbouring lot within 40 m ('142-38' matched to '142-32', a corner lot filed under the cross street) gives
    # no elevator, floor count, year or unit count. D4: the city's device list must not show zero active elevators.
    lot_ok, lot_addr, dob_el = {}, {}, {}
    pf = DATA / "reference" / "nyc_building_facts.csv"
    if pf.exists():
        PF = pd.read_csv(pf, dtype=str, keep_default_na=False)
        a_of = U.drop_duplicates("addr_key").set_index("addr_key").address.to_dict()
        for r in PF.itertuples():
            if r.match_basis in ("house_number+location", "nearest_lot"):
                lot_addr[r.addr_key] = r.pluto_address
                lot_ok[r.addr_key] = parsers.lot_address_agrees(a_of.get(r.addr_key, r.addr_key.split("|")[0]), r.pluto_address)
    nrf = DATA / "evidence" / "nyc_records.csv"
    if nrf.exists():
        NR = pd.read_csv(nrf, dtype=str, keep_default_na=False)
        for r in NR[NR.record_type == "dob_elevator_devices_active"].itertuples():
            try:
                dob_el[r.addr_key] = (int(float(r.count)), r.detail[:160])
            except ValueError:
                pass

    def official_elevator_ok(addr_key):
        """An elevator may rest on the city's building class only on the listing's own lot, and not where the city's
        device list for that lot shows no active passenger elevator (an accessibility lift is not an elevator)."""
        return lot_ok.get(addr_key, False) and dob_el.get(addr_key, (1, ""))[0] > 0

    M = Merge()
    # ------------------------------------------------------------------ 5/6. listing rows + inference
    for r in U.itertuples():
        b, src = r.building_id, r.url
        el_basis = getattr(r, "elevator_basis", "")
        if r.g_elevator == "pass" and not (el_basis.startswith("nyc") and not official_elevator_ok(r.addr_key)):
            # 'stated' only when the page lists an elevator; a harvester's "6+ floors" note is an inference (W3)
            M.add(b, "elevator", "yes", "inferred" if el_basis.startswith("inferred") else ("official_record" if el_basis.startswith("nyc") else "stated"),
                  src if not el_basis.startswith("nyc") else "NYC PLUTO building class " + getattr(r, "pluto_class", ""))
        if r.addr_key in lot_addr:
            M.add(b, "pluto_lot_ok", "yes" if lot_ok.get(r.addr_key) else "no", "official_record", "data/reference/nyc_building_facts.csv")
            M.add(b, "pluto_lot_address", lot_addr[r.addr_key], "official_record", "data/reference/nyc_building_facts.csv")
        if r.addr_key in dob_el:
            M.add(b, "dob_active_elevators", str(dob_el[r.addr_key][0]), "official_record", "data/evidence/nyc_records.csv")
            if dob_el[r.addr_key][0] == 0:
                M.add(b, "elevator_note", "city device list for this lot shows no active passenger elevator: " + dob_el[r.addr_key][1], "official_record", "data/evidence/nyc_records.csv")
        M.add(b, "dogs_allowed", yesno(r.dogs), "stated", src)
        M.add(b, "dog_policy_text", r.dog_policy_text, "stated", src)
        M.add(b, "dog_weight_limit_lb", r.dog_weight_limit_lb if re.fullmatch(r"[\d.]+", r.dog_weight_limit_lb or "") else "", "stated", src)
        if parsers.dog_size_only(r.dog_policy_text) or re.search(r"small dogs only|Size allowed: Small[;)]", r.notes or ""):
            M.add(b, "dog_size_only", "yes: " + (r.dog_policy_text or r.notes)[:120], "stated", src)
        # pet rent: the harvester's number when plausible, else the monthly figure in the pet text or fee lines (W15)
        fj = parsers.fees_from_json(r.other_monthly_fees_json, r.unit)
        pr = float(r.pet_rent) if re.fullmatch(r"[\d.]+", r.pet_rent or "") else None
        if pr is not None and 0 < pr <= 150:
            M.add(b, "pet_rent_monthly", f"{pr:g}", "stated", src)
        else:
            add_pet_rent(M, b, r.dog_policy_text, "stated", src, False)
            add_pet_rent(M, b, fj["pet_text"], "stated", src, True)
        # parking: type text as listed; fee from the fee field, the parking sentence or the fee lines (W4, A1, A14, A15)
        M.add(b, "parking_type", r.parking_type, "stated", src)
        pf = float(r.parking_fee) if re.fullmatch(r"[\d.]+", r.parking_fee or "") else None
        add_parking(M, b, r.parking_type if "$" in (r.parking_type or "") or re.search(r"free|included", r.parking_type or "", re.I) else "", "stated", src, pf)
        add_parking(M, b, fj["parking_text"], "stated", src)
        add_parking(M, b, r.community_parking_text, "community_page", "data/reference/community_facts.csv")
        M.add(b, "building_floors", r.building_floors if re.fullmatch(r"[\d.]+", r.building_floors or "") else "", "stated", src)
        M.add(b, "laundry", r.laundry, "stated", src)
        M.add(b, "manager", r.manager, "stated", src)
        M.add(b, "utilities_included", r.utilities_included if r.utilities_included.lower() != "none listed as included" else "", "stated", src)
        cu = "; ".join(x for x in [("included: " + r.community_utilities_included) if not is_blank(r.community_utilities_included) else "",
                                   ("resident pays " + r.community_utilities_resident_pays) if not is_blank(r.community_utilities_resident_pays) else ""] if x)
        M.add(b, "utilities_included", cu, "community_page", "data/reference/community_facts.csv")
        M.add(b, "building_name", r.building_name, "stated", src)
        for col, fld in [("pluto_floors", "building_floors"), ("pluto_year", "year_built"), ("pluto_units", "unit_count")]:
            v = getattr(r, col, "")
            if re.fullmatch(r"[\d.]+", v or "") and float(v) > 0 and lot_ok.get(r.addr_key, False):
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
                "gated_or_garage_parking": "parking_type", "dog_amenities": "dog_amenities",
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
            # the stored number was "the first dollar figure in the sentence" (A16): re-read the sentence itself
            num = r.get("parking_fee_monthly", "")
            add_parking(M, b, r.get("parking_fee_monthly_evidence", ""), "amenities_page", r.get("source_url", ""),
                        float(num) if re.fullmatch(r"[\d.]+", num or "") and is_blank(r.get("parking_fee_monthly_evidence", "")) else None)

    # ------------------------------------------------------------------ 1. evidence pass
    C, F, L = cat("confirm_batch_*.csv"), cat("facts_batch_*.csv"), cat("live_check_batch_*.csv")
    floor_rows = []                              # (building, unit label or '*', floor, basis, source)
    dog_yes, dog_contra = {}, {}
    # independent check 2, D2: a fact the evidence pass looked for and could NOT confirm is open, whatever the
    # harvester stored. seen[(building, fact)] = {"confirmed": n, "unconfirmed": [text, ...]}
    seen = {}
    PLUTO_ONLY = re.compile(r"pluto|bldgclass|building class|public record|class D\d|nyc_records_match|cityofnewyork", re.I)
    PAGE_WORDS = re.compile(r"listing (?:says|states|lists)|on the listing|amenit|description|own site|building(?:'s)? (?:site|page)|floor ?plans? page", re.I)
    if len(C):
        for r in C.itertuples():
            b, fact, val = bid_of(r.addr_key), r.fact.lower(), r.value
            if b is None:
                continue
            if fact.startswith("dog_weight") or fact.startswith("dogs_allowed"):
                # a size word with no number is an open fact whatever the row's status (W2): it only ever adds caution
                kind, lb = parsers.parse_dog_weight(val) if fact.startswith("dog_weight") else ("size_only" if parsers.dog_size_only(val) else "", None)
                if kind == "size_only":
                    M.add(b, "dog_size_only", "yes: " + val[:120], "confirmed", r.source_url)
            # (dog_size_only is a display fact: "small dogs" passes the gate, owner 2026-11-15; rank.py adds note + tour question)
            gate_fact = "elevator" if fact.startswith("elevator") else ("dogs_allowed" if fact.startswith("dogs_allowed") else "")
            txt = f"{val} | {r.quote}"
            if gate_fact:
                st = seen.setdefault((b, gate_fact), {"confirmed": 0, "unconfirmed": []})
                if r.status == "unconfirmed":
                    st["unconfirmed"].append((txt[:260], r.source_url))
            if (gate_fact == "dogs_allowed" or fact.startswith("dog_weight")) and r.status != "contradicts":
                ne = parsers.dogs_not_explicit(txt)
                if ne:                           # D3: "pets upon approval", "case by case", dogs not named: not explicit, any status
                    M.add(b, "dogs_evidence_open", f"dogs are not named as allowed ('{ne}'): {txt[:200]}", "confirmed", r.source_url)
            if r.status == "unconfirmed":        # an unconfirmed row never upgrades a basis (W3)
                continue
            if fact.startswith("elevator"):
                if r.status == "contradicts":
                    M.add(b, "elevator", "conflicting" if re.search(r"conflict|not established", val, re.I) else "no", "confirmed", r.source_url)
                    M.add(b, "elevator_note", val[:200], "confirmed", r.source_url)
                elif PLUTO_ONLY.search(txt + " " + r.source_url) and not PAGE_WORDS.search(re.sub(r"not on the listing", "", txt)):
                    # D4: "confirmed" on the strength of the city's building class alone is an official record at best,
                    # and only on the listing's own lot with an active elevator device on file
                    if official_elevator_ok(r.addr_key):
                        M.add(b, "elevator", yesno(val) or "yes", "official_record", "NYC PLUTO building class (evidence pass): " + r.quote[:120])
                        st["confirmed"] += 1
                    else:
                        st["unconfirmed"].append(("the city's record for a neighbouring lot, or a lot with no active elevator on file: " + txt[:200], r.source_url))
                else:
                    # "yes (inferred from height)" written by the evidence agent is still an inference
                    inferred_ = bool(re.search(r"inferred|implied|treated as|plan rule", val, re.I))
                    M.add(b, "elevator", yesno(val), "inferred" if inferred_ else "confirmed", r.source_url)
                    if not inferred_:
                        st["confirmed"] += 1
            elif fact.startswith("dogs_allowed"):
                if r.status == "contradicts":
                    dog_contra.setdefault(b, []).append((val, r.source_url))
                else:
                    if not is_aggregator(r.source_url):      # only the building's own or its manager's page outranks an aggregator
                        dog_yes[b] = r.source_url
                    M.add(b, "dogs_allowed", yesno(val) or "yes", "confirmed", r.source_url)
                    st["confirmed"] += 1
            elif fact.startswith("dog_weight"):
                if kind == "no_limit" and r.status == "confirmed":
                    M.add(b, "dog_weight_limit_lb", "no limit", "confirmed", r.source_url)
                elif kind == "limit" and r.status == "confirmed":
                    M.add(b, "dog_weight_limit_lb", f"{lb:g}", "confirmed", r.source_url)
                if r.status == "confirmed":
                    M.add(b, "dog_weight_text", val[:200], "confirmed", r.source_url)
            elif fact.startswith("building_floors"):
                n = money(val)
                M.add(b, "building_floors", f"{n:g}" if n else "", "confirmed", r.source_url)
            elif fact.startswith("floor"):
                pairs, inferred = parsers.parse_floor_confirm(val)
                # D10: the checker often wrote "floor inferred from the unit number" in the quote, not the value
                inferred = inferred or bool(re.search(r"inferred|derived|from (?:the )?unit (?:number|label)s?|by unit numbering|implied|my reading", r.quote or "", re.I))
                for lab, fl_ in pairs:
                    # a floor the checker read off the unit number is an inference, whatever the row's status (W1)
                    floor_rows.append((b, lab, fl_, "inferred" if inferred else "confirmed", r.source_url, val[:120], r.quote or ""))
                if not pairs and not re.search(r"unknown|unconfirmed", val, re.I):
                    floor_rows.append((b, "?", None, "unparsed", r.source_url, val[:120], r.quote or ""))
    for (b, gate_fact), st in seen.items():
        if st["unconfirmed"] and not st["confirmed"]:
            for t_, src_ in st["unconfirmed"][:3]:
                M.add(b, gate_fact.split("_")[0] + "_evidence_open", "the evidence pass could not confirm it: " + t_, "confirmed", src_)
    # conflicting dog policy (W20): the building's own site or management feed wins over an aggregator; aggregator
    # against aggregator is an open fact ("Are dogs allowed?"), not a "no"
    for b, rows_ in dog_contra.items():
        verdict = parsers.dog_conflict("; ".join(v for v, _ in rows_))
        if re.search(r"may not|units? only|only in", " ".join(v for v, _ in rows_), re.I) and verdict == "yes":
            verdict = "conflicting"
        if verdict == "conflicting" and b in dog_yes:
            verdict = "yes"                       # a separate row confirmed yes on the building's own page
        key = (b, "dogs_allowed")
        M.c[key] = [t for t in M.c.get(key, []) if t[2] != "confirmed"]
        M.add(b, "dogs_allowed", verdict, "confirmed", rows_[0][1])
        M.add(b, "dogs_allowed_note", "sources disagree: " + " / ".join(v for v, _ in rows_)[:260], "confirmed", rows_[0][1])
    unmapped = {}
    if len(F):
        for r in F.itertuples():
            b = bid_of(r.addr_key)
            if b is None:
                continue
            if not apply_fact(M, b, r.fact, r.value, getattr(r, "quote", ""), r.source_url):
                k = re.sub(r"[:(].*", "", r.fact.lower()).strip()
                unmapped[k] = unmapped.get(k, 0) + 1

    rows, conflicts = M.resolve()

    # ------------------------------------------------------------------ building table
    bfirst = U.drop_duplicates("building_id").set_index("building_id")
    keep_from_units = ["address", "city", "state", "zip5", "hood", "hood_id", "hood_area"] + \
        [c for c in U.columns if c.startswith(("drive_", "toll_", "transit_", "police_", "crime_", "near_", "park_", "dog_park_", "restaurants_",
                                               "bars_", "cafes_", "music_", "supermarket", "coast_", "beach_", "open_water_", "train_station",
                                               "motorway_", "util_", "last_sat", "pluto_"))]
    B = bfirst[[c for c in keep_from_units if c in bfirst.columns]].copy()
    B = B.join(G)                                # one coordinate per building (W7)
    B = B.join(pd.DataFrame.from_dict(rows, orient="index"))
    B["addr_keys"] = U.groupby("building_id").addr_key.agg(lambda s: " || ".join(sorted(set(s))))
    B["n_listed_units"] = U.groupby("building_id").listing_id.count()
    for b, g in G[G.coord_basis.astype(str).ne("listing rows agree") & G.coord_basis.astype(str).ne("none")].iterrows():
        conflicts.append({"building_id": b, "field": "lat_lon", "chosen": f"{float(g.lat):.6f},{float(g.lon):.6f}", "chosen_basis": g.coord_basis, "others": g.coord_note})

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
                 "available_date", "floor", "floor_used", "floor_basis", "floor_label_kind", "g_floor", "listing_age_days", "stale_listing", "photo_url", "raw_path", "notes",
                 "other_monthly_fees_json", "listing_type", "gate_status"]
    MU = U[[c for c in unit_cols if c in U.columns]].copy()

    # the same unit listed twice inside one building (W8): same normalized label, or - with no label - the same beds,
    # sq ft and rent. Keep the building's own site over an aggregator, then the fuller row; remember the other links.
    MU["ukey_"] = MU.unit.map(parsers.unit_label_key)       # '1 bed, 1 bath, $1675' is a plan description, not a unit (D17)
    MU["utail_"] = MU.unit.map(parsers.unit_tail)
    MU["upri_"] = (~MU.source_site.map(is_aggregator)).astype(int) * 4 + (MU.detail_level.str.lower() != "card").astype(int) * 2 + (MU.ukey_ != "").astype(int)
    MU = MU.sort_values(["building_id", "upri_"], ascending=[True, False], kind="stable")
    keep_of = {}
    for b, g in MU.groupby("building_id", sort=False):
        kept = []                                           # (listing_id, key, tail, beds, sqft, rent)
        for r in g.itertuples():
            dup = None
            for k in kept:
                same_money = (k[3], k[5]) == (r.beds, r.listed_rent) and (k[4] == r.sqft or "" in (k[4], r.sqft))
                if r.ukey_ and k[1]:
                    if r.ukey_ == k[1] or (same_money and r.utail_ and r.utail_ == k[2]):
                        dup = k[0]
                elif same_money:                            # at least one of the two has no unit label
                    dup = k[0]
                if dup:
                    break
            if dup:
                keep_of[r.listing_id] = dup
            else:
                kept.append((r.listing_id, r.ukey_, r.utail_, r.beds, r.sqft, r.listed_rent))
    dups = MU[MU.listing_id.isin(keep_of)]
    extra_links = dups.groupby(dups.listing_id.map(keep_of)).agg(url=("url", " ".join), ids=("listing_id", " ".join))
    MU = MU[~MU.listing_id.isin(keep_of)].copy()
    MU["also_seen_at"] = (MU.also_seen_at + " " + MU.listing_id.map(extra_links.url).fillna("")).str.strip()
    MU["duplicate_listing_ids"] = MU.listing_id.map(extra_links.ids).fillna("")
    dups.assign(kept_listing_id=dups.listing_id.map(keep_of))[["listing_id", "kept_listing_id", "building_id", "unit", "beds", "sqft", "listed_rent", "source_site", "url"]] \
        .to_csv(DATA / "duplicate_units.csv", index=False)
    MU = MU.drop(columns=["upri_"])

    # live check: status and price now. Unit labels are matched the same way on both sides (W17).
    live_cols = [("status", "live_status"), ("price_now", "live_price"), ("available_now_text", "live_available_text"), ("checked_at", "live_checked_at"), ("notes", "live_notes")]
    for _, new in live_cols:
        MU[new] = ""
    if len(L):
        L["building_id"] = L.addr_key.map(A2B)
        L = L.dropna(subset=["building_id"]).sort_values("checked_at")
        by_b = {b: g for b, g in L.groupby("building_id")}
        for i, b, un in zip(MU.index, MU.building_id, MU.unit):
            g = by_b.get(b)
            if g is None:
                continue
            if parsers.unit_label_key(un):
                hit = g[[parsers.unit_key(x) == parsers.unit_key(un) for x in g.unit]]
                if not len(hit):
                    hit = g[[parsers.units_match(x, un) for x in g.unit]]
            else:
                # D11: a row with no unit number takes a live-check row only when that row is about it: the same
                # stored label, price or plan name, or the building's only unlabelled row and only unlabelled check.
                # (Before, blank matched blank and every floor plan of a building took the same check.)
                row = MU.loc[i]
                blank = g[[parsers.unit_label_key(x) == "" for x in g.unit]]
                plan = re.search(r":plan-([^:]+)", str(row.listing_id))
                plan_name = plan.group(1).replace("_", " ").strip().lower() if plan else ""
                price = str(row.listed_rent).split(".")[0]

                def about(lr):
                    n = str(lr.notes).lower().replace(",", "")
                    if str(un).strip() and parsers.unit_key(lr.unit) == parsers.unit_key(un):
                        return True
                    if plan_name and re.search(r"(?<![\w-])" + re.escape(plan_name) + r"(?![\w-])", n):
                        return True
                    return bool(price) and (str(lr.price_now).split(".")[0] == price or re.search(r"\$\s?" + re.escape(price) + r"(?!\d)", n) is not None)
                hit = blank[[about(lr) for lr in blank.itertuples()]]
                n_unlabelled = int((MU.building_id.eq(b) & MU.unit.map(parsers.unit_label_key).eq("")).sum())
                if not len(hit) and len(blank) == 1 and n_unlabelled == 1:
                    hit = blank
            if len(hit):
                for col, new in live_cols:
                    MU.at[i, new] = hit.iloc[-1][col]

    # floor: confirmed per unit > stated on the listing > inferred from the unit label (W1, W17)
    bf_good = {b: v for b, v, bs in zip(B.index, B.get("building_floors", pd.Series(dtype=str)), B.get("building_floors_basis", pd.Series(dtype=str))) if bs in GOOD_FLOORCOUNT}
    bf_any = B.get("building_floors", pd.Series(dtype=str)).to_dict()
    n_in_b = MU.groupby("building_id").size().to_dict()
    fr_by_b, used = {}, set()
    for j, fr in enumerate(floor_rows):
        fr_by_b.setdefault(fr[0], []).append((j,) + fr[1:])
    labels_in_b = MU.groupby("building_id").unit.apply(lambda x: [u for u in x if parsers.unit_label_key(u)]).to_dict()

    def star_unit(b, text):
        """The one unit of the building that a floor row without a unit label is about, read from its quote
        ('Unit 265 ... Floor 2'), or None (D10: Avalon Somerville 022-265 had two confirmed rows that never landed)."""
        named = [u for u in labels_in_b.get(b, []) if re.search(r"(?<![\w-])(?:" + re.escape(u) + "|" + re.escape(parsers.unit_tail(u) or u) + r")(?![\w-])", text, re.I)]
        return named[0] if len(set(named)) == 1 else None
    desc_floor_ok = {}

    def description_floor(raw_path, stated):
        """D10: a floor the harvester took from the first 'Nth floor' phrase of a description counts as stated only
        when a phrase with that floor is about the unit, not an amenity ('8th-floor sundeck')."""
        key = (raw_path, stated)
        if key not in desc_floor_ok:
            try:
                txt = Path(DATA.parent / raw_path).read_text(errors="ignore")
            except OSError:
                txt = ""
            txt = txt.replace("\\n", " ").replace("\\u2019", "'")
            ok = False
            for m in re.finditer(r"[^.!?\"<>]{0,80}\b" + str(int(float(stated))) + r"(?:st|nd|rd|th)[- ]floor\b[^.!?\"<>]{0,60}", txt, re.I):
                if parsers.floor_from_description(m.group(0)) == int(float(stated)):
                    ok = True
                    break
            desc_floor_ok[key] = ok
        return desc_floor_ok[key]
    fl, flb, fls, flk = [], [], [], []
    for b, un, stated, gbasis, hnote, rawp in zip(MU.building_id, MU.unit, MU.floor_used, MU.floor_basis, MU.notes, MU.raw_path):
        if gbasis == "stated" and "floor from description text" in str(hnote) and re.fullmatch(r"[\d.]+", str(stated)) and not description_floor(rawp, stated):
            gbasis = "description_amenity"           # the phrase was about an amenity: the floor is not stated
        got = None
        for want in ("confirmed", "inferred"):
            for j, lab, f_, basis, src, _, quote_ in fr_by_b.get(b, []):
                if basis != want:
                    continue
                if (lab != "*" and parsers.units_match(lab, un)) or (lab == "*" and (n_in_b.get(b) == 1 or (parsers.unit_label_key(un) and star_unit(b, quote_) == un))):
                    got = (f_, basis, src); used.add(j)
                    break
            if got:
                break
        label_floor, kind = parsers.floor_from_label(un, bf_good.get(b))
        cap = parsers._bf(bf_any.get(b))
        if got and got[1] == "confirmed":
            fl.append(got[0]); flb.append("confirmed"); fls.append(got[2]); flk.append("")
        elif gbasis == "stated" and re.fullmatch(r"[\d.]+", str(stated)):
            fl.append(int(float(stated))); flb.append("stated"); fls.append("listing page"); flk.append("")
        elif got:                                           # the evidence pass read it off the unit number: still inferred
            ok_simple = kind == "simple" and label_floor == got[0]
            fl.append(got[0]); flb.append("inferred"); fls.append("evidence pass, read from the unit number"); flk.append("simple" if ok_simple else "complex")
        elif label_floor is not None and not (cap and label_floor > cap):
            fl.append(label_floor); flb.append("inferred"); fls.append("unit number"); flk.append(kind)
        else:
            fl.append(""); flb.append("unknown"); fls.append(""); flk.append(kind)
    MU["unit_floor"], MU["unit_floor_basis"], MU["unit_floor_source"], MU["unit_floor_label_kind"] = fl, flb, fls, flk
    unmatched = [fr[:6] for j, fr in enumerate(floor_rows) if j not in used and fr[3] in ("confirmed", "unparsed")]
    pd.DataFrame(unmatched, columns=["building_id", "unit_label", "floor", "basis", "source_url", "value"]).to_csv(DATA / "reference" / "floor_confirm_unmatched.csv", index=False)
    MU = MU.drop(columns=["ukey_", "utail_"])
    bcols = [c for c in B.columns if c not in MU.columns]
    MU = MU.join(B[bcols], on="building_id")
    # D8: the lease term the listed price belongs to, from the unit's own live-check note, else the building's
    # lease-term fact, else the listing's own price basis ('12-month lease', 'lease term 24 Months').
    ltm, lt12, ltq, ltsrc, ltlow = [], [], [], [], []
    for note, fact_txt, pb, un in zip(MU.live_notes, MU.get("price_term_text", pd.Series("", index=MU.index)).fillna(""), MU.price_basis, MU.unit):
        got = None
        for src_, txt in (("live check", note), ("evidence fact", fact_txt), ("listing", pb)):
            if src_ == "evidence fact":
                # a building-level fact names its units when it is not about all of them
                parts = [x for x in str(txt).split(" || ") if x.strip()]
                txt = " ; ".join(x for x in parts if not re.search(r"\bunit\b", x, re.I) or (parsers.unit_label_key(un) and re.search(r"(?<![\w-])" + re.escape(parsers.unit_tail(un) or un) + r"(?![\w-])", x)))
                txt = re.sub(r"^\s*(\d{1,2}) months\b", r"price is for a \1-month lease", txt)
                txt = re.sub(r"term (\d{1,2}): price (\d{4})", lambda m: f"{m.group(1)}-month price ${m.group(2)}" if m.group(1) == "12" else m.group(0), txt)
            if src_ == "listing":
                txt = re.sub(r"lease term (\d{1,2}) Months|(?:per month, |lowest over lease terms \()(\d{1,2})-month(?: lease)?\)?",
                             lambda m: f"price is for a {m.group(1) or m.group(2)}-month lease", str(txt))
            lt = parsers.lease_term_from_text(txt)
            if lt["months"] or lt["lowest_of_terms"]:
                got = (lt, src_)
                break
        if got:
            lt, src_ = got
            ltm.append(lt["months"] or ""); lt12.append(lt["price_12"] or ""); ltq.append(lt["quote"][:200]); ltsrc.append(src_); ltlow.append("yes" if lt["lowest_of_terms"] and not lt["months"] else "")
        else:
            ltm.append(""); lt12.append(""); ltq.append(""); ltsrc.append(""); ltlow.append("")
    MU["price_lease_months"], MU["price_12_month"], MU["price_lease_quote"], MU["price_lease_source"], MU["price_lowest_of_terms"] = ltm, lt12, ltq, ltsrc, ltlow
    MU.to_csv(DATA / "master_units.csv", index=False)

    print(f"buildings: {len(B)} (from {U.addr_key.nunique()} addr_keys); units: {len(MU)} (+{len(dups)} duplicates of a unit in the same building, data/duplicate_units.csv); conflicts: {len(conflicts)}")
    for f in ["elevator", "dogs_allowed", "dog_weight_limit_lb", "parking_type", "parking_fee_monthly", "pet_rent_monthly", "pool", "doorman", "year_built", "manager", "utilities_included"]:
        if f + "_basis" in B:
            print(f"  {f:22s}", B[f + "_basis"].fillna("unknown").value_counts().to_dict())
    nconf = sum(1 for fr in floor_rows if fr[3] == "confirmed")
    print("  unit floor basis", MU.unit_floor_basis.value_counts().to_dict(), "| label kind of inferred", MU[MU.unit_floor_basis == "inferred"].unit_floor_label_kind.value_counts().to_dict())
    print(f"  confirmed floor values: {nconf} read, {sum(1 for fr in unmatched if fr[3] == 'confirmed')} matched no unit in the master (most are units that left the list), "
          f"{sum(1 for fr in unmatched if fr[3] == 'unparsed')} not parseable (data/reference/floor_confirm_unmatched.csv)")
    print("  live status", MU.live_status.replace("", "not checked").value_counts().to_dict(), "| coordinates", G.coord_basis.value_counts().to_dict())
    print("  evidence facts not mapped to a field:", dict(sorted(unmapped.items(), key=lambda kv: -kv[1])[:25]))


if __name__ == "__main__":
    main()
