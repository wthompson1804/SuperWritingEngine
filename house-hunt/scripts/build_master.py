"""Build the two master tables every later step reads (docs/PLAN_V4_MASTER_MODEL_2026-11-15.md, Part 1).

  data/master_buildings.csv   one row per physical building (building_id)
  data/master_units.csv       one row per listed unit (listing_id), with its building's merged facts joined on
  data/master_conflicts.csv   where two sources disagree on a merged field
  data/reference/building_crosswalk.csv   every addr_key seen anywhere -> building_id

Merged building fields carry <field>, <field>_basis, <field>_source. Basis, in precedence order:
  confirmed_by_phone  an answer from a phone call (data/evidence/call_answers.csv; source "phone call <called_at>")
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

PREC = ["confirmed_by_phone", "confirmed", "community_page", "amenities_page", "official_record", "stated", "inferred"]
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
TEXT_APPEND = {"dog_weight_unstated", "required_fees_text", "utilities_included", "concession_text_evidence", "optional_fees_text", "parking_text",
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
    elif f.startswith("eligibility"):
        # batch 19: a listing site's INCOME RESTRICTED tag that the manager's own page does not bear out: one open fact
        M.add(b, "eligibility_open", v, C, url)
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
                       "address_mismatch", "listing_address_mismatch", "address_note", "eligibility")


# ---------------------------------------------------------------------- overnight street-parking rules (reviewed table)
def overnight_parking_rules(path=None):
    """hood_id -> {severity, town, rule, url} from data/reference/overnight_parking_towns.csv, a table filled by READING
    the local-rule rows (no free text is parsed at run time). Where two rows cover a neighborhood the stricter wins
    (ban > permit > seasonal). A missing file means no rules."""
    f = Path(path) if path else DATA / "reference" / "overnight_parking_towns.csv"
    if not f.exists():
        return {}
    order = {"ban": 0, "permit": 1, "seasonal": 2}
    out = {}
    for r in pd.read_csv(f, dtype=str, keep_default_na=False).itertuples():
        if r.severity not in order:
            continue
        for hid in [h.strip() for h in r.applies_to_hood_ids.split(";") if h.strip()]:
            if hid not in out or order[r.severity] < order[out[hid]["severity"]]:
                out[hid] = {"severity": r.severity, "town": r.municipality, "rule": r.rule_summary, "url": r.source_url}
    return out


def same_apartment_other_site(beds_a, sqft_a, rent_a, site_a, beds_b, sqft_b, rent_b, site_b) -> bool:
    """D19: a row with a unit label and a row with none are the same apartment when they come from two different sites
    and agree on bedrooms, on a published size, and on the rent to within 2 percent (sites round or lag each other)."""
    try:
        ra, rb, sa, sb = float(rent_a), float(rent_b), float(sqft_a), float(sqft_b)
    except (TypeError, ValueError):
        return False
    if not (sa > 0 and sa == sb) or str(beds_a) != str(beds_b) or url_site(site_a) == url_site(site_b):
        return False
    return abs(ra - rb) <= 0.02 * max(ra, rb)


def url_site(site) -> str:
    s_ = str(site).lower()
    return next((a for a in AGGREGATORS if a in s_), s_.strip())


def elevator_only_from_listing_sites(cands) -> bool:
    """cands: Merge candidates (precedence, value, basis, source) for 'elevator'. True when at least one says yes on
    something better than an inference and every such source is a listing site (Apartment List, Trulia, Zumper ...)."""
    yes = [c for c in cands if c[1] == "yes" and c[2] != "inferred"]
    return bool(yes) and all(is_aggregator(c[3]) for c in yes)


# ---------------------------------------------------------------------- independent check 3
def url_host(u_) -> str:
    return re.sub(r"^www\.", "", re.sub(r"^https?://([^/?#]+).*", r"\1", str(u_).strip().lower()))


def second_site(url, also_seen_at, duplicate_urls="") -> bool:
    """D11: a second SITE lists the unit only when one of the other links is on a different host from the unit's own
    listing. `also_seen_at` often holds the very building page the row came from (the same Trulia or Apartment List
    page), which is not a second source and must not switch the staleness rule off."""
    own = url_host(url)
    others = {url_host(x) for x in (str(also_seen_at) + " " + str(duplicate_urls)).split() if x.strip().startswith("http")}
    return bool(others - {own, ""})


def load_elevator_doubt(path=None) -> dict:
    """building_id -> {name, why, source} from the reviewed table data/reference/elevator_doubt.csv (owner, 2026-11-16):
    buildings whose elevator rests on a listing site's amenity list while the complex is low-rise, converted or
    multi-building, so that 'an elevator' does not say an elevator serves this apartment. Open gate fact."""
    f = Path(path) if path else DATA / "reference" / "elevator_doubt.csv"
    if not f.exists():
        return {}
    return {r.building_id: {"name": r.name, "why": r.why, "source": r.source} for r in pd.read_csv(f, dtype=str, keep_default_na=False).itertuples()}


def garden_style(unit_labels, heights) -> bool:
    """General rule beside the table (owner, 2026-11-16): the data shows a multi-building garden-style complex when the
    unit labels carry several building numbers AND no page or record gives any height of 4 floors or more.
    heights: every floor count a page or record states for the building (building floors, the city's count, a stated or
    confirmed unit floor); blanks and label readings are not heights."""
    hs = [h for h in (pd.to_numeric(pd.Series(list(heights), dtype=object), errors="coerce").dropna().tolist())]
    return parsers.multi_building_labels(unit_labels) and not any(h >= 4 for h in hs)


def load_overrides(path=None):
    """data/reference/address_overrides.csv: reviewed corrections to a building's name, address or city, or to one
    unit's address (scope building -> key is an addr_key; scope unit -> key is a listing_id). Each row says where the
    correction comes from. A building_name is entered only where the name is blank or just repeats the address."""
    f = Path(path) if path else DATA / "reference" / "address_overrides.csv"
    return pd.read_csv(f, dtype=str, keep_default_na=False) if f.exists() else pd.DataFrame(columns=["scope", "key", "field", "value", "basis", "source", "note"])


# ---------------------------------------------------------------------- phone answers (highest precedence)
CALL_ANSWERS = DATA / "evidence" / "call_answers.csv"
PHONE = "confirmed_by_phone"


def load_call_answers(path=None):
    """data/evidence/call_answers.csv (a filled call sheet, docs/SHORTLIST_TOOLS.md) -> one dict per listing, through
    call_sheet.answers_by_listing. No file, or an empty one: []. Rows with no called_at are refused (an answer must say
    when it was given)."""
    f = Path(path) if path else CALL_ANSWERS
    if not f.exists():
        return []
    import call_sheet
    filled = pd.read_csv(f, dtype=str, keep_default_na=False)
    if not len(filled):
        return []
    A = call_sheet.answers_by_listing(filled)
    return [r for r in A.to_dict("records") if str(r.get("called_at", "")).strip()]


def _num(v):
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def apply_call_answers_building(M, answers, building_of):
    """Building-level phone answers into the merge, as the highest-precedence basis. building_of: listing_id -> building_id
    (the answer row's own building_id is used when the listing is unknown). Returns {building_id: called_at}."""
    called = {}
    for a in answers:
        b = building_of.get(a["listing_id"]) or (a.get("building_id") or None)
        if not b:
            continue
        src = f"phone call {a['called_at']}"
        called[b] = max(called.get(b, ""), a["called_at"])
        el = yesno(a.get("ans_elevator", ""))
        if el:
            M.add(b, "elevator", el, PHONE, src)
        w = str(a.get("ans_dog_weight_lb", "")).strip().lower()
        if w:
            # a weight limit (or "no limit") given on the phone also says dogs are allowed
            if re.search(r"no (?:weight )?limit|none|unlimited", w):
                M.add(b, "dog_weight_limit_lb", "no limit", PHONE, src); M.add(b, "dogs_allowed", "yes", PHONE, src)
            elif _num(w) is not None:
                M.add(b, "dog_weight_limit_lb", f"{_num(w):g}", PHONE, src); M.add(b, "dogs_allowed", "yes", PHONE, src)
        for col, fld in (("ans_pet_rent", "pet_rent_monthly"), ("ans_parking_fee", "parking_fee_monthly"), ("ans_required_fees", "required_fees_phone")):
            n = _num(a.get(col, ""))
            if n is not None and str(a.get(col, "")).strip():
                M.add(b, fld, f"{n:g}", PHONE, src)
                if fld == "parking_fee_monthly":
                    M.add(b, "parking_fee_note", "a spot is included, by phone" if n == 0 else "by phone", PHONE, src)
        if str(a.get("ans_income_multiple", "")).strip():
            M.add(b, "call_income_multiple", a["ans_income_multiple"], PHONE, src)
        if str(a.get("ans_notes", "")).strip():
            M.add(b, "call_notes", a["ans_notes"], PHONE, src)
    return called


def phone_overrides_building(rows):
    """After the merge: a fact answered on the phone is no longer 'open in the evidence pass'."""
    for b, d in rows.items():
        if d.get("elevator_basis") == PHONE:
            d.pop("elevator_evidence_open", None)
        if d.get("dogs_allowed_basis") == PHONE:
            d.pop("dogs_evidence_open", None)
        if d.get("dog_weight_limit_lb_basis") == PHONE:
            d.pop("dog_weight_unstated", None); d.pop("dog_size_only", None)
    return rows


def apply_call_answers_units(MU, answers):
    """Per-unit phone answers onto the unit table (in place; returns it): floor, the lease term of the listed price,
    the 12-month price, the move-in date offered ('gone' ends the listing; a date or 'now' counts as seeing it live)."""
    for c in ("call_called_at", "call_available"):
        if c not in MU:
            MU[c] = ""
    by = {a["listing_id"]: a for a in answers}
    for i, lid in zip(MU.index, MU.listing_id):
        a = by.get(lid)
        if a is None:
            continue
        src = f"phone call {a['called_at']}"
        MU.at[i, "call_called_at"] = a["called_at"]
        f_ = _num(a.get("ans_floor", ""))
        if f_ is not None and str(a.get("ans_floor", "")).strip():
            MU.at[i, "unit_floor"], MU.at[i, "unit_floor_basis"], MU.at[i, "unit_floor_source"], MU.at[i, "unit_floor_label_kind"] = int(f_), PHONE, src, ""
        m_ = _num(a.get("ans_lease_term_months", ""))
        if m_ is not None and str(a.get("ans_lease_term_months", "")).strip():
            MU.at[i, "price_lease_months"], MU.at[i, "price_lease_source"], MU.at[i, "price_lowest_of_terms"] = int(m_), src, ""
            MU.at[i, "price_lease_quote"] = f"by phone: the listed price is for a {int(m_)}-month lease"
        p_ = _num(a.get("ans_12mo_price", ""))
        if p_ is not None and str(a.get("ans_12mo_price", "")).strip():
            MU.at[i, "price_12_month"], MU.at[i, "price_lease_source"] = p_, src
        av = str(a.get("ans_available_date", "")).strip().lower()
        if av:
            MU.at[i, "call_available"] = av
            MU.at[i, "live_checked_at"] = a["called_at"]
            MU.at[i, "live_notes"] = (f"by phone {a['called_at']}: " + ("no longer available" if av == "gone" else f"available {av}") + " | " + str(MU.at[i, "live_notes"])).rstrip(" |")
            if av == "gone":
                MU.at[i, "live_status"] = "gone"
            else:
                MU.at[i, "live_status"] = "live"
                MU.at[i, "available_date"] = av
    return MU


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
        if str(getattr(r, "pluto_class", "")).upper().startswith("C") and lot_ok.get(r.addr_key, False) and r.g_elevator == "pass":
            # the city classes this lot (an exact address match) as walk-up apartments while a listing names an elevator:
            # the official record contradicts the listing, so the elevator stays open (357 Grove St, 1512 Park Pl, Brooklyn)
            M.add(b, "elevator_evidence_open", f"the city's record for this lot (building class {r.pluto_class}, walk-up apartments, at the listing's own address) goes against the elevator a listing names",
                  "official_record", "NYC PLUTO building class " + r.pluto_class)
        if str(getattr(r, "pluto_class", "")).upper().startswith("D") and official_elevator_ok(r.addr_key):
            # the city classes this lot (the listing's own address) as an elevator apartment building, with no zero on the
            # device list: an official record beside whatever the listing says (so the elevator does not rest on a listing site alone)
            M.add(b, "elevator", "yes", "official_record", "NYC PLUTO building class " + getattr(r, "pluto_class", ""))
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
        if parsers.dog_weight_unstated(r.dog_policy_text):
            M.add(b, "dog_weight_unstated", "yes: " + r.dog_policy_text[:160], "stated", src)
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
    contact_only, dogs_named, floor_unknown = {}, set(), []
    PLUTO_ONLY = re.compile(r"pluto|bldgclass|building class|public record|class D\d|nyc_records_match|cityofnewyork", re.I)
    AGG_TEXT = re.compile(r"(?:apartment ?list|trulia|zumper)[^.;|]{0,40}(?:amenit|tag|feature)", re.I)
    OWN_TEXT = re.compile(r"own site|building(?:'s)? (?:own )?(?:site|page)|manager(?:'s)? (?:site|page)|community page", re.I)
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
                if r.status != "contradicts" and parsers.dog_weight_unstated(f"{val} | {r.quote}"):
                    # 4a: "weight restrictions apply" with no pound figure passes like "small dogs", with the tour question
                    M.add(b, "dog_weight_unstated", "yes: " + (val if parsers.dog_weight_unstated(val) else r.quote)[:160], "confirmed", r.source_url)
            # (dog_size_only is a display fact: "small dogs" passes the gate, owner 2026-11-15; rank.py adds note + tour question)
            gate_fact = "elevator" if fact.startswith("elevator") else ("dogs_allowed" if fact.startswith("dogs_allowed") else "")
            txt = f"{val} | {r.quote}"
            if gate_fact:
                st = seen.setdefault((b, gate_fact), {"confirmed": 0, "stated": 0, "contra": [], "unconfirmed": []})
                # 4c: one rule for every batch. An elevator in a listing site's amenity list or text is 'stated' (not
                # confirmed) whether the batch wrote the row as confirmed or unconfirmed; it settles the elevator unless
                # the building's own site or a checker's reading contradicts it.
                ekind = ""
                if gate_fact == "elevator" and r.status in ("confirmed", "unconfirmed") and not (r.status == "confirmed" and PLUTO_ONLY.search(txt + " " + r.source_url) and not PAGE_WORDS.search(re.sub(r"not on the listing", "", txt))):
                    agg_src = is_aggregator(r.source_url) or bool(AGG_TEXT.search(txt) and not OWN_TEXT.search(txt))
                    ekind = parsers.elevator_row_kind(val, r.quote, agg_src, r.status)
                    if ekind == "contra":
                        st["contra"].append((txt[:260], r.source_url))
                    elif ekind == "stated" and not re.search(r"inferred|implied|treated as|plan rule", val, re.I):
                        M.add(b, "elevator", "yes", "stated", r.source_url)
                        M.add(b, "elevator_note", "an elevator is in a listing site's amenity list or text (stated, not confirmed on the building's own page): " + txt[:120], "stated", r.source_url)
                        st["stated"] += 1
                        continue
                if r.status == "unconfirmed":
                    st["unconfirmed"].append((txt[:260], r.source_url))
            if (gate_fact == "dogs_allowed" or fact.startswith("dog_weight")) and r.status != "contradicts":
                ne = parsers.dogs_not_explicit(txt)
                if ne and re.search(r"contact for more information", ne, re.I):
                    # an aggregator's policy block that only says "contact for more information on pet policy": open unless
                    # another page for the building names dogs as allowed (settled after the loop)
                    contact_only.setdefault(b, (txt[:200], r.source_url))
                elif ne:                         # D3: "pets upon approval", "case by case", dogs not named: not explicit, any status
                    M.add(b, "dogs_evidence_open", f"dogs are not named as allowed ('{ne}'): {txt[:200]}", "confirmed", r.source_url)
            if gate_fact == "dogs_allowed" and r.status == "confirmed" and not re.search(r"zumper", r.source_url, re.I) \
                    and re.search(r"dogs? (?:are )?(?:allowed|ok|welcome)|small dogs|dogs: allowed|cats (?:and|&|,) (?:small )?dogs", txt, re.I):
                dogs_named.add(b)
            if fact.startswith("floor") and not fact.startswith("floors") and r.status == "unconfirmed" \
                    and re.match(r"\s*(?:unknown|unclear|cannot|not (?:stated|known))", val, re.I):
                # independent check 3, D15: this used to sit below the 'continue' and never ran, so 100 W 139th St 27A
                # kept floor 27 in a six-floor building. e.g. "Unit 27A cannot be floor 27: the building has 6 floors"
                floor_unknown.append((b, f"{val} | {r.quote}"))
            if r.status == "unconfirmed":        # an unconfirmed row never upgrades a basis (W3)
                continue
            if fact.startswith("elevator") and ekind == "contra":
                pass                                 # the row itself speaks against an elevator: nothing is entered, the fact is opened after the loop
            elif fact.startswith("elevator"):
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
                    # (a confirmed row read on a listing site was already entered above as 'stated'; this is the own page)
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
    for b, (t_, src_) in contact_only.items():
        if b not in dogs_named:
            M.add(b, "dogs_evidence_open", f"dogs are not named as allowed (the only policy text is 'contact for more information on pet policy'): {t_}", "confirmed", src_)
    for (b, gate_fact), st in seen.items():
        if st["contra"] and not st["confirmed"]:
            for t_, src_ in st["contra"][:2]:
                M.add(b, "elevator_evidence_open", "the building's own site or the checker's reading goes against it: " + t_, "confirmed", src_)
        elif st["unconfirmed"] and not st["confirmed"] and not st["stated"]:
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
    mod_facts = {}                                   # building -> [(date, source_url)] from listing_last_modified / listing_updated_at facts
    if len(F):
        for r in F.itertuples():
            b = bid_of(r.addr_key)
            if b is None:
                continue
            fl_ = r.fact.lower()
            if fl_.startswith(("listing_last_modified", "listing_updated_at", "listing_page_last_modified")) and re.match(r"20\d\d-\d\d-\d\d", r.value.strip()):
                mod_facts.setdefault(b, []).append((r.value.strip()[:10], r.source_url))
                continue
            if fl_.startswith(("dog_weight", "pet_limit", "pet_restrictions", "dog_restrictions", "pet_policy", "dog_policy")) and parsers.dog_weight_unstated(f"{r.value} | {getattr(r, 'quote', '')}"):
                M.add(b, "dog_weight_unstated", "yes: " + str(r.value)[:160], "confirmed", r.source_url)
            if not apply_fact(M, b, r.fact, r.value, getattr(r, "quote", ""), r.source_url):
                k = re.sub(r"[:(].*", "", r.fact.lower()).strip()
                unmapped[k] = unmapped.get(k, 0) + 1

    # phone answers: the highest-precedence source (basis confirmed_by_phone, source "phone call <called_at>")
    CALLS = load_call_answers()
    called_b = apply_call_answers_building(M, CALLS, dict(zip(U.listing_id, U.building_id))) if CALLS else {}

    # 4c: which elevators rest on listing sites alone: every source that says "yes" (other than an inference) is a
    # listing site's page; no own or manager's page, no city record, no phone call says so
    agg_only = {b for (b, f), cands in M.c.items() if f == "elevator" and elevator_only_from_listing_sites(cands)}
    rows, conflicts = M.resolve()
    rows = phone_overrides_building(rows)
    for b, when in called_b.items():
        rows.setdefault(b, {})["call_building_called_at"] = when
    for b, d in rows.items():
        # 4c: which elevators rest on a listing site's page alone (no own page, no record, no phone call)
        d["elevator_aggregator_only"] = "yes" if d.get("elevator") == "yes" and b in agg_only else ""
    # owner, 2026-11-16 (independent check 3, part B): a tag-only elevator is still 'stated', EXCEPT
    #  (1) buildings in the reviewed table data/reference/elevator_doubt.csv, and
    #  (2) by rule, a tag-only elevator in a complex the data shows to be multi-building garden-style: several building
    #      numbers in the unit labels and no height of 4+ floors on any page or record.
    # For those the elevator is an open gate fact: "confirm an elevator serves this apartment". A phone answer settles it.
    DOUBT = load_elevator_doubt()
    labels_by_b = U.groupby("building_id").unit.apply(lambda x: [u for u in x if parsers.unit_label_key(u)]).to_dict()
    stated_floor_by_b = U[U.floor_basis.eq("stated")].groupby("building_id").floor_used.apply(list).to_dict() if "floor_used" in U else {}
    pluto_fl_by_b = U.groupby("building_id").pluto_floors.apply(list).to_dict() if "pluto_floors" in U else {}
    for b, d in rows.items():
        if d.get("elevator") != "yes" or d.get("elevator_basis") == PHONE:
            continue
        if b in DOUBT:
            d["elevator_doubt"] = f"reviewed table: {DOUBT[b]['why']}"
            d["elevator_doubt_source"] = "data/reference/elevator_doubt.csv (" + DOUBT[b]["source"] + ")"
        elif d.get("elevator_aggregator_only") == "yes":
            heights = [d.get("building_floors", "") if d.get("building_floors_basis") != "inferred" else ""] + pluto_fl_by_b.get(b, []) + stated_floor_by_b.get(b, []) \
                + [f_ for (b_, lab, f_, basis, *_x) in floor_rows if b_ == b and basis == "confirmed"]
            if garden_style(labels_by_b.get(b, []), heights):
                prefs = sorted({parsers.building_prefix(u) for u in labels_by_b.get(b, []) if parsers.building_prefix(u)})
                d["elevator_doubt"] = ("rule: the elevator is named only in a listing site's amenity list, the unit labels carry several building numbers ("
                                       + ", ".join(prefs[:6]) + "), and no page or record gives a height of four floors or more")
                d["elevator_doubt_source"] = "rule (scripts/build_master.py: garden_style)"

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
    # D15 (Alexander Crossing): a floor count that only a listing row states, below what the building's own unit labels
    # read as ("2 floors" with a unit 0405), is not a height: it is dropped and logged as a conflict.
    if "building_floors" in B:
        for b in B.index[B.building_floors_basis.isin(["stated", "amenities_page"]).fillna(False)]:
            bf = parsers._bf(B.at[b, "building_floors"])
            tops = []
            for u_ in labels_by_b.get(b, []):
                t_ = parsers.unit_tail(u_) or parsers.unit_key(u_)
                m_ = re.fullmatch(r"0?([1-9])\d\d[a-z]?", t_) or re.fullmatch(r"([1-9]\d)\d\d[a-z]?", t_ if not parsers.building_prefix(u_) else "")
                if m_:
                    tops.append(int(m_.group(1)))
            if bf and tops and max(tops) > bf:
                conflicts.append({"building_id": b, "field": "building_floors", "chosen": "", "chosen_basis": "dropped",
                                  "others": f"{B.at[b, 'building_floors']} ({B.at[b, 'building_floors_basis']}) is below a unit label that reads as floor {max(tops)}"})
                B.at[b, "building_floors"], B.at[b, "building_floors_basis"] = "", ""
    # reviewed corrections to names and addresses (docs/PENDING_FIXES.md, independent check 3 D17)
    OV = load_overrides()
    for r in OV[OV.scope == "building"].itertuples():
        b = A2B.get(r.key)
        if b is None or b not in B.index or r.field not in ("building_name", "address", "city"):
            continue
        if r.field == "building_name":
            cur = str(B.at[b, "building_name"]) if "building_name" in B and not is_blank(B.at[b, "building_name"]) else ""
            if cur and street_key(cur, "") != street_key(str(B.at[b, "address"]), "") and not re.match(r"\d", cur):
                continue                             # a real name is already there
            B.at[b, "building_name"], B.at[b, "building_name_basis"], B.at[b, "building_name_source"] = r.value, r.basis, r.source
        else:
            B.at[b, r.field] = r.value
            B.at[b, r.field + "_override_source"] = r.source
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
    # how many evidence rows (live check, confirm, facts) the building has: a unit in a building the evidence pass never
    # touched cannot be shown (scripts/rank.py), because there is nothing a reviewer could have read
    ev_n = {}
    for D_ in (C, F, L):
        if len(D_):
            for k, n_ in D_.addr_key.map(A2B).dropna().value_counts().items():
                ev_n[k] = ev_n.get(k, 0) + int(n_)
    B["evidence_rows"] = pd.Series(ev_n).reindex(B.index).fillna(0).astype(int)
    # step 3: the town's overnight street-parking rule, from the reviewed table (the disclosure is decided in rank.py)
    OP = overnight_parking_rules()
    for col, k in (("street_overnight_severity", "severity"), ("street_overnight_town", "town"), ("street_overnight_rule", "rule"), ("street_overnight_url", "url")):
        B[col] = B.hood_id.map(lambda h: OP.get(h, {}).get(k, ""))
    B.index.name = "building_id"
    B.to_csv(DATA / "master_buildings.csv")
    pd.DataFrame(conflicts).to_csv(DATA / "master_conflicts.csv", index=False)
    xw.to_csv(DATA / "reference" / "building_crosswalk.csv", index=False)

    # ------------------------------------------------------------------ unit table
    unit_cols = ["listing_id", "building_id", "addr_key", "source_site", "url", "building_url", "also_seen_at", "detail_level", "first_seen",
                 "last_seen", "unit", "beds", "baths", "sqft", "listed_rent", "price_basis", "concession_text", "available_date_text",
                 "available_date", "floor", "floor_used", "floor_basis", "floor_label_kind", "g_floor", "listing_age_days", "stale_listing", "photo_url", "raw_path", "notes",
                 "other_monthly_fees_json", "listing_type", "gate_status", "resolved_by"]
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
                elif same_apartment_other_site(k[3], k[4], k[5], k[6], r.beds, r.sqft, r.listed_rent, r.source_site):
                    dup = k[0]                              # D19: 12 Brooklyn Ave 501 ($2,675, Trulia) and a Zumper row with no unit ($2,700)
                if dup:
                    break
            if dup:
                keep_of[r.listing_id] = dup
            else:
                kept.append((r.listing_id, r.ukey_, r.utail_, r.beds, r.sqft, r.listed_rent, r.source_site))
    dups = MU[MU.listing_id.isin(keep_of)]
    extra_links = dups.groupby(dups.listing_id.map(keep_of)).agg(url=("url", " ".join), ids=("listing_id", " ".join))
    MU = MU[~MU.listing_id.isin(keep_of)].copy()
    MU["also_seen_at"] = (MU.also_seen_at + " " + MU.listing_id.map(extra_links.url).fillna("")).str.strip()
    MU["duplicate_listing_ids"] = MU.listing_id.map(extra_links.ids).fillna("")
    dups.assign(kept_listing_id=dups.listing_id.map(keep_of))[["listing_id", "kept_listing_id", "building_id", "unit", "beds", "sqft", "listed_rent", "source_site", "url"]] \
        .to_csv(DATA / "duplicate_units.csv", index=False)
    MU = MU.drop(columns=["upri_"])

    # live check: status and price now. Unit labels are matched the same way on both sides (W17).
    live_cols = [("status", "live_status"), ("price_now", "live_price"), ("available_now_text", "live_available_text"), ("checked_at", "live_checked_at"), ("notes", "live_notes"),
                 ("listing_url", "live_url")]
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
                # a check matched to an unlabelled row by its plan name or a price in its note says the row was seen;
                # its price_now may belong to another plan on the same page, so it is taken only when it is this row's price
                if not parsers.unit_label_key(un) and str(hit.iloc[-1]["price_now"]).split(".")[0] != str(MU.at[i, "listed_rent"]).split(".")[0] \
                        and hit.iloc[-1]["status"] != "changed":
                    MU.at[i, "live_price"] = ""

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
        if parsers.unit_label_key(un) and any(b_ == b and re.search(r"(?<![\w-])" + re.escape(un) + r"(?![\w-])", t_, re.I) for b_, t_ in floor_unknown) \
                and not (got and got[1] == "confirmed") and gbasis != "stated":
            # the evidence pass looked at this unit and said its floor is unknown: a label reading does not stand
            label_floor, kind, got = None, "complex", None
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
    for r in OV[OV.scope == "unit"].itertuples():      # D17: EDGE 408 and 410 are in the building at 170 Avenue F
        hit = MU.listing_id == r.key
        if hit.any() and r.field in ("address", "city"):
            MU.loc[hit, r.field] = r.value
            MU.loc[hit, "address_override_source"] = r.source
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
    for c in ("unit_floor", "price_lease_months", "price_12_month"):
        MU[c] = MU[c].astype(object)
    MU = apply_call_answers_units(MU, CALLS)
    # 4b: staleness from modification dates where the data has them: the unit's own live-check note, else a
    # listing_last_modified / listing_updated_at fact read on the same site as the unit's listing
    host = url_host
    # independent check 3, D3 (Residences at The Summit K3-02): the modification date of a building PAGE belongs to
    # every unit listed on that page, not only to the unit whose live-check note happens to quote it. Dates are
    # collected per (building, page host) from every live-check note of the building that speaks of the page itself.
    page_dates = {}                                  # (building, host) -> latest "page last modified" date in any note of the building
    if len(L):
        for r in L.itertuples():
            if re.search(r"building page|page last modified|\(last modified", str(r.notes), re.I):
                d0 = parsers.page_modified_date(r.notes)
                if d0:
                    k0 = (r.building_id, host(r.listing_url))
                    page_dates[k0] = max(page_dates.get(k0, ""), d0)
    dup_urls = MU.duplicate_listing_ids.map(lambda ids: " ".join(dups[dups.listing_id.isin(ids.split())].url) if ids else "") if len(dups) else pd.Series("", index=MU.index)
    pm, pms, st_lvl, st_days, st_why = [], [], [], [], []
    for b, url_, note, lc, ls, av, also, dupu, called, lst, lurl in zip(MU.building_id, MU.url, MU.live_notes, MU.live_checked_at, MU.last_seen, MU.available_date, MU.also_seen_at,
                                                                       dup_urls, MU.call_called_at, MU.live_status, MU.live_url):
        d_, src_ = parsers.page_modified_date(note), "live-check note"
        read_on = str(lc)[:10] or str(ls)[:10]
        seen_live = lst in ("live", "changed")
        # a unit the evidence pass saw live on ANOTHER site (often the manager's own page) is not judged by the age of the
        # listing site's page. D11: but a unit seen "live" on that same listing-site page is (134 Baldwin Ave 301, 411).
        same_page_check = (not seen_live) or (not str(lurl).strip()) or host(lurl) == host(url_)
        if not d_ and same_page_check:
            same = [d for d, u_ in mod_facts.get(b, []) if host(u_) and host(u_) == host(url_)]
            sib = page_dates.get((b, host(url_)), "") if "/building/" in str(url_) or not parsers.unit_label_key("") else ""
            if same:
                d_, src_, read_on = max(same), "evidence fact (page data of the listing site)", str(ls)[:10] or str(lc)[:10]
            elif sib:
                d_, src_, read_on = sib, "live-check note of another unit on the same building page", str(lc)[:10] or str(ls)[:10]
            if d_ and read_on < d_:
                read_on = str(lc)[:10] or d_
        lvl, days, why = parsers.staleness(d_, read_on, av, second_source=second_site(url_, also, dupu)) if not str(called).strip() else ("", None, "")
        pm.append(d_); pms.append(src_ if d_ else ""); st_lvl.append(lvl); st_days.append("" if days is None else days); st_why.append(why)
    MU["page_modified_date"], MU["page_modified_source"], MU["listing_stale"], MU["listing_stale_days"], MU["listing_stale_why"] = pm, pms, st_lvl, st_days, st_why
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
    print(f"  phone answers: {len(CALLS)} listing rows in {len(called_b)} buildings" + ("" if CALLS else " (data/evidence/call_answers.csv is absent or empty)"))
    print("  page modification date known:", int((MU.page_modified_date != "").sum()), "| stale:", MU.listing_stale.replace("", "no").value_counts().to_dict(),
          "| elevator on a listing site's page alone:", int((B.get("elevator_aggregator_only", pd.Series(dtype=str)) == "yes").sum()), "buildings",
          "| overnight parking rule:", B.street_overnight_severity.replace("", "none").value_counts().to_dict())
    print("  evidence facts not mapped to a field:", dict(sorted(unmapped.items(), key=lambda kv: -kv[1])[:25]))


if __name__ == "__main__":
    main()
