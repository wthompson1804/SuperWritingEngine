"""Merge data/listings_raw/*.csv, dedupe, and apply the approved gates (docs/PLAN_V3_APPROVED_2026-11-15.md).

Each gate yields pass / fail / unknown. Overall status:
  pass      every gate passes (an open fact such as floor_or_elevator passes here and is counted by rank.py)
  pending   nothing fails, but a gate that must be confirmed is unknown (dogs, floor and elevator, availability, proof)
  fail      at least one gate fails
Rent (owner, 2026-11-17, second trawl): listed base rent at most $2,200 (RENT_MAX); rows above stay in the data and fail
with the reason over_2200. Floor and elevator (owner, 2026-11-17): one gate, g_floor_elevator (parsers.floor_elevator_rule
over parsers.elevator_rule): elevator established -> pass; otherwise floor 2 passes, the ground floor fails, floor 3+
fails with no elevator and is pending with the elevator unknown, and an unknown floor is ONE open fact (pass, code
floor_or_elevator, or 'elevator' where an elevator is named but in doubt). g_elevator and g_floor stay as columns.
The all-in money gate needs parking, fees and utility estimates; it is applied by scripts/all_in.py after
the utilities tool exists. Here the money gate checks listed rent only.

Outputs: data/listings.csv (all rows with gate columns), data/gate_summary.md (counts dropped at each gate).
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT  # noqa: E402
import parsers  # noqa: E402

WINDOW_END = date(2026, 12, 15)
RENT_MAX = 2200     # Will, 2026-11-17 (second trawl): collect nothing above $2,200 listed base rent; the $3,000 total test is unchanged (all_in.py)
RENT_FAIL_REASON = f"over_{RENT_MAX}"
MIN_DOG_LIMIT_LB = 25  # Will, 2026-11-15: the dog will not exceed 25 lb (gate was 40, then 35)
MAX_DRIVE_MIN = 120
STALE_DAYS = 60

ABBR = {"street": "st", "avenue": "ave", "boulevard": "blvd", "road": "rd", "drive": "dr", "place": "pl",
        "court": "ct", "lane": "ln", "terrace": "ter", "parkway": "pkwy", "highway": "hwy", "north": "n",
        "south": "s", "east": "e", "west": "w", "apartment": "", "apt": "", "unit": "", "suite": ""}


def norm_addr(a: str) -> str:
    a = re.sub(r"[.,#]", " ", str(a).lower())
    toks = [ABBR.get(t, t) for t in a.split()]
    return " ".join(t for t in toks if t)


def norm_unit(u: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(u).lower())


def floor_from_unit(unit: str, building_floors=None):
    """Guess a floor from a unit label (scripts/parsers.py: floor_from_label). Always an inference.

    '4F' -> 4, '305' -> 3. Labels with a separator, a building prefix or four digits ('H2-316', '9114') give a floor
    only when the building's floor count leaves one reading. 'B2', 'C4', 'L3' are lines or buildings, not a level
    (independent check W11): only G, GR, LOBBY, BSMT read as ground (0)."""
    return parsers.floor_from_label(unit, building_floors)[0]


HARVESTER_INFERRED_ELEVATOR = re.compile(r"elevator: \d+\+ floors|elevator:? inferred|elevator inferred|elevator: implied", re.I)
HARVESTER_DERIVED_FLOOR = re.compile(r"floor (?:derived|inferred|guessed|taken) from (?:the )?unit", re.I)


def to_num(x):
    try:
        return float(str(x).replace(",", "").replace("$", ""))
    except ValueError:
        return None


def gate_type(r):
    return "pass" if str(r.beds).strip() in ("0", "1", "0.0", "1.0") else "fail"


def gate_rent(r):
    v = to_num(r.listed_rent)
    return "unknown" if v is None else ("pass" if v <= RENT_MAX else "fail")


def gate_movein(r):
    d = str(r.available_date).strip().lower()
    if d in ("now", "available now", "immediately"):
        return "pass"
    if not d or d == "nan":
        return "unknown"
    try:
        return "pass" if date.fromisoformat(d[:10]) <= WINDOW_END else "fail"
    except ValueError:
        return "unknown"


def gate_dog(r):
    """Dogs must be explicitly allowed; a stated limit under 25 lb fails. A size word with no number ("small dogs",
    "Size allowed: Small") passes (owner, 2026-11-15: her dog is at most 25 lb); scripts/rank.py adds the note and the
    tour question. "Pet friendly" or cats only, with no dogs named, stays unknown or fails as the harvester recorded it."""
    d = str(r.dogs).strip().lower()
    if d == "no":
        return "fail"
    if d != "yes":
        return "unknown"
    lim = to_num(r.dog_weight_limit_lb)
    if lim is not None and lim < MIN_DOG_LIMIT_LB:
        return "fail"
    return "pass"


INFER_ELEVATOR_FLOORS = parsers.ELEVATOR_MIN_FLOORS  # Will, 2026-11-15: a building of 6+ floors is treated as having an elevator (asterisk)
# The harvester wrote elevator "yes" from unit labels on the page ("elevator: 6+ floors (unit numbers on the page reach
# floor 37)"): a height guessed from labels, which does not support an elevator.
HARVESTER_LABEL_HEIGHT = re.compile(r"elevator: \d+\+ floors\W{0,3}unit numbers", re.I)
EXACT_LOT = parsers.EXACT_LOT           # nyc_building_facts.match_basis; the lot counts only when its address agrees too (parsers.lot_is_exact)
AGGREGATORS = ("trulia", "zumper", "apartmentlist", "zillow", "craigslist", "apartments.com", "rent.com")   # as build_master.py
_EV_INFERRED = re.compile(r"inferred|implied|treated as|plan rule", re.I)
_EV_PLUTO_ONLY = re.compile(r"pluto|bldgclass|building class|public record|class D\d|nyc_records_match|cityofnewyork", re.I)
_EV_PAGE_WORDS = re.compile(r"listing (?:says|states|lists)|on the listing|amenit|description|own site|building(?:'s)? (?:site|page)|floor ?plans? page", re.I)
_EV_AGG_TEXT = re.compile(r"(?:apartment ?list|trulia|zumper)[^.;|]{0,40}(?:amenit|tag|feature)", re.I)
_EV_OWN_TEXT = re.compile(r"own site|building(?:'s)? (?:own )?(?:site|page)|manager(?:'s)? (?:site|page)|community page", re.I)


def page_height(r):
    """The building's height in floors as a page or record gives it, or None: the building-floors field (a page's
    floor count or floor list), or a floor the page states for the unit (the building is at least that tall). A floor
    read from a unit label is never a height: '42M' at 1204 Kennedy Blvd and '69B' at 69 N Broadway are a landlord's
    numbering (docs/harvest_notes/zumper_open_pending.md)."""
    notes = str(getattr(r, "notes", ""))
    bf = to_num(r.building_floors)
    stated_floor = None if HARVESTER_DERIVED_FLOOR.search(notes) else to_num(r.floor)
    return max([v for v in (bf, stated_floor) if v is not None], default=None)


def elevator_facts(r, evidence="", contradicted=False, active_devices=None) -> dict:
    """What a listing row says about the elevator, as the arguments of parsers.elevator_rule (the one rule every stage
    uses). `evidence`, `contradicted` and `active_devices` come from the evidence files (main() looks them up by address);
    a caller that has only the row (scripts/zumper_open_pending.py) leaves them out."""
    e = str(r.elevator).strip().lower()
    notes = str(getattr(r, "notes", ""))
    harvester = e == "yes" and bool(HARVESTER_INFERRED_ELEVATOR.search(notes))
    return dict(
        page_no=e == "no",
        stated=e == "yes" and not harvester,
        # the harvester's yes read from a page's floor list or floor field; one read from unit labels counts for nothing
        page_height_claim=harvester and not HARVESTER_LABEL_HEIGHT.search(notes),
        height=page_height(r),
        high_rise_own_page=parsers.is_high_rise(getattr(r, "community_building_type", "")),   # community_facts.csv: management pages
        record_class=str(getattr(r, "elevator_from_class", "")),
        record_floors=getattr(r, "pluto_floors", ""),
        lot_exact=parsers.lot_is_exact(getattr(r, "match_basis", ""), getattr(r, "address", ""), getattr(r, "pluto_address", "")),
        active_devices=active_devices, evidence=evidence, contradicted=contradicted)


_GATE_OF = {"established": "pass", "open": "pass", "no": "fail", "unknown": "unknown"}


def gate_elevator(r, evidence="", contradicted=False, active_devices=None):
    """Returns (result, basis). The decision is parsers.elevator_rule (truth table in scripts/parsers.py):
    established or open -> pass, no -> fail, unknown -> pending. Bases: 'stated', 'nyc_pluto_building_class' (the
    listing's own lot only), 'evidence_confirmed' / 'evidence_stated' / 'amenities_page', and the open ones
    'inferred_harvester', 'inferred_6plus_floors', 'inferred_high_rise_label'. A floor read from a unit label and a
    neighbouring tax lot never count, to pass or to fail. The floor gate still reads labels (gate_floor)."""
    status, basis = parsers.elevator_rule(**elevator_facts(r, evidence, contradicted, active_devices))
    return _GATE_OF[status], basis


def elevator_from_pluto_floors(pluto_floors, lot_exact, elevator_from_class=""):
    """True when the city's record gives 6+ floors for the listing's own lot and its building class does not say
    walk-up (parsers.elevator_rule). A neighbouring lot's height says nothing about this building."""
    if lot_exact == EXACT_LOT:                     # older callers passed the match basis
        lot_exact = True
    return parsers.elevator_rule(record_class=elevator_from_class, record_floors=pluto_floors, lot_exact=lot_exact is True)[0] == "open"


def elevator_evidence(folder=None, amenities=None) -> dict:
    """addr_key -> (basis, source) for the buildings whose evidence states an elevator and nothing speaks against it
    (elevator_evidence_rows without the contradicted buildings)."""
    out, against = elevator_evidence_rows(folder, amenities)
    return {k: v for k, v in out.items() if k not in against}


def elevator_evidence_rows(folder=None, amenities=None):
    """({addr_key: (basis, source)}, {addr_key spoken against}): buildings where a page that was read states an elevator although the listing row
    does not. Rows of the evidence pass (data/evidence/confirm_batch_*.csv), graded as build_master.py grades them:
    'evidence_confirmed' (the building's own or another non-listing-site page), 'evidence_stated' (a listing site's
    amenity list or text); then 'amenities_page' (data/reference/building_amenities.csv, elevator_stated = yes).
    Not counted: a row that is itself an inference from height, a row resting on the city's building class alone
    (main() applies the class on an exact lot), and any building with a row that speaks against the elevator."""
    folder = Path(folder) if folder else DATA / "evidence"
    out, against = {}, set()
    for f in sorted(folder.glob("confirm_batch_*.csv")):
        C = pd.read_csv(f, dtype=str, keep_default_na=False)
        for r in C[C.fact.str.lower().str.startswith("elevator")].itertuples():
            txt = f"{r.value} | {r.quote}"
            if r.status == "contradicts":
                against.add(r.addr_key)
                continue
            if r.status not in ("confirmed", "unconfirmed"):
                continue
            if r.status == "confirmed" and _EV_PLUTO_ONLY.search(txt + " " + r.source_url) and not _EV_PAGE_WORDS.search(re.sub(r"not on the listing", "", txt)):
                continue
            agg = any(a in str(r.source_url).lower() for a in AGGREGATORS) or bool(_EV_AGG_TEXT.search(txt) and not _EV_OWN_TEXT.search(txt))
            kind = parsers.elevator_row_kind(r.value, r.quote, agg, r.status)
            if kind == "contra":
                against.add(r.addr_key)
            elif kind in ("own", "stated") and not _EV_INFERRED.search(r.value) and str(r.value).strip().lower().startswith(("yes", "true")):
                basis = "evidence_confirmed" if kind == "own" else "evidence_stated"
                if r.addr_key not in out or (basis == "evidence_confirmed" and out[r.addr_key][0] != basis):
                    out[r.addr_key] = (basis, r.source_url)
    af = Path(amenities) if amenities else DATA / "reference" / "building_amenities.csv"
    if af.exists():
        A = pd.read_csv(af, dtype=str, keep_default_na=False)
        for r in A[A.elevator_stated.str.lower() == "yes"].itertuples():
            out.setdefault(r.addr_key, ("amenities_page", r.source_url))
    return out, against


def gate_floor(r):
    """Returns (result, floor, basis, label kind). basis 'stated' only when the listing gives a floor and the
    harvester's note does not say it was derived from the unit number; otherwise 'inferred' from the label
    (independent check W1). A label that gives no safe reading is 'unknown' (an open fact), never a fail (W11)."""
    notes = str(getattr(r, "notes", ""))
    f = to_num(r.floor)
    if f is not None and not HARVESTER_DERIVED_FLOOR.search(notes):
        return ("pass" if f >= 2 else "fail"), int(f), "stated", ""
    bf = to_num(r.building_floors) or to_num(getattr(r, "pluto_floors", ""))
    g, kind = parsers.floor_from_label(r.unit, bf)
    if g is None:
        return "unknown", "", "", kind
    return ("pass" if g >= 2 else "fail"), int(g), "inferred", kind


def floor_elevator_gate(elevator_status, floor_result, floor, floor_basis, label_kind, stories=None, stories_basis=""):
    """The floor-and-elevator gate of a listing row (owner, 2026-11-17; parsers.floor_elevator_rule). Returns
    (gate, code): settled or open -> 'pass' (an open fact is counted by rank.py), fail -> 'fail', unknown -> 'unknown'
    (pending). The floor as gate_floor found it: a floor the listing states counts as 'page'; a reading from the unit
    label counts as 'label' for a simple label or a ground word, otherwise 'weak' (it can fail a unit, never pass one)."""
    how = "page" if floor_basis == "stated" else ("" if floor in ("", None) else ("label" if label_kind in ("simple", "ground_word") else "weak"))
    st, code = parsers.floor_elevator_rule(elevator_status, floor if floor != "" else None, how, stories, stories_basis)
    return {"settled": "pass", "open": "pass", "fail": "fail", "unknown": "unknown"}[st], code


def gate_proof(r):
    if not str(r.url).startswith("http"):
        return "fail"
    return "pass" if str(r.detail_level).strip().lower() != "card" else "unknown"


def apply_resolved_pending(df, pattern="resolved_pending_batch_*.csv", folder=None):
    """Pending listings whose missing gate fact a later evidence batch settled from a page we may read
    (data/evidence/resolved_pending_batch_<n>.csv, verdict now_passes; scripts/resolve_pending_thin_years.py).
    The settled fact is written onto the listing row, so the ordinary gates decide: an elevator stated on a listing
    site's page of the same building becomes 'yes'; an elevator inferred from the building's height becomes 'yes'
    with the note 'elevator: inferred', which the elevator gate reads as an inference (an open fact, asterisk); a
    dog policy read on another page of the same building becomes dogs 'yes' with the policy text. Rows that only
    duplicate a unit already passing from another source are left alone. Adds the column resolved_by."""
    folder = folder or (DATA / "evidence")
    df["resolved_by"] = ""
    for f in sorted(Path(folder).glob(pattern)):
        R = pd.read_csv(f, dtype=str, keep_default_na=False)
        R = R[R.verdict.str.startswith("now_passes") & (R.duplicate_of == "")].drop_duplicates("listing_id").set_index("listing_id")
        for i, lid in zip(df.index, df.listing_id):
            if lid not in R.index:
                continue
            r = R.loc[lid]
            how = r.how_settled
            for part in [x.strip() for x in how.split(" ; ")]:
                if part.lower().startswith("elevator"):
                    df.at[i, "elevator"] = "yes"
                    if re.match(r"elevator \((?:asterisk, )?inferred\)", part, re.I):
                        df.at[i, "notes"] = (str(df.at[i, "notes"]) + " | elevator: inferred from the building's height (" + f.stem + ")").strip(" |")
                elif part.lower().startswith("dogs"):
                    df.at[i, "dogs"] = "yes"
                    if not str(df.at[i, "dog_policy_text"]).strip():
                        df.at[i, "dog_policy_text"] = re.sub(r"^dogs:\s*", "", part)[:300]
            df.at[i, "resolved_by"] = f"{f.stem}: {how[:300]} ({r.source_url})"
    return df


def main():
    files = sorted((DATA / "listings_raw").glob("*.csv"))
    if not files:
        print("no raw listings yet")
        return
    df = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in files], ignore_index=True)
    n_raw = len(df)
    # no API key, token or signature in any URL we carry (Trulia's Street View photo links held Trulia's own Google key)
    for col in ("photo_url", "url", "building_url"):
        if col in df:
            df[col] = df[col].map(parsers.strip_url_secrets)

    grid = pd.read_csv(DATA / "reference" / "search_grid.csv", dtype={"zcta": str})
    drive = dict(zip(grid.zcta, grid.drive_min))
    df["zip5"] = df.zip.str.extract(r"(\d{5})", expand=False).fillna("")
    df["drive_min_zip"] = df.zip5.map(drive)

    # A unit written into the address ('1775 Windsor Road #215', '20 Gill Lane, Apt. 1E') belongs in the unit field: left in
    # the address it hides the unit from the floor gate and from the duplicate check. The address column is cleaned and
    # a blank unit field is filled from it. addr_key is still built from the address AS LISTED: it is the key every
    # evidence file is filed under, so it must not change.
    sp = df.address.map(parsers.split_address_unit)
    df["address_as_listed"] = df.address
    df["unit_in_address"] = [x[1] for x in sp]
    from_addr = (df.unit_in_address != "") & (df.unit.str.strip() == "")
    df.loc[from_addr, "unit"] = df.loc[from_addr, "unit_in_address"]
    df["unit_basis"] = from_addr.map({True: "from_address", False: ""})
    df["address"] = [parsers.street_address(x[0]) for x in sp]      # '219 Lenox Rd, Brooklyn, NY 11226, USA' -> '219 Lenox Rd'
    df["addr_key"] = df.address_as_listed.map(norm_addr) + "|" + df.zip5
    df["unit_key"] = df.unit.map(norm_unit)
    df["listing_kind"] = [parsers.listing_kind(u, d, l, lt, bn) for u, d, l, lt, bn in zip(df.unit, df.detail_level, df.listing_id, df.listing_type, df.building_name)]
    # independent check 4, D4: a one-letter label beside numbered apartments of the same address is a plan letter, not a
    # home (BE 'P' and 'F'; Appletree Suites 'C', 'E', 'F' beside 2B to 6D): not_an_apartment
    street = df.address.map(norm_addr) + "|" + df.zip5          # the cleaned street address: '448 Scotland Rd #4OA' is a sibling
    sibs = df.groupby(street).unit.agg(list).to_dict()
    letter = [k == "unit" and parsers.plan_letter_label(u, sibs[a]) for k, u, a in zip(df.listing_kind, df.unit, street)]
    df.loc[letter, "listing_kind"] = "floor_plan"
    df["dedupe_key"] = df.addr_key + "|" + df.unit_key + "|" + df.beds.astype(str)
    # units with no unit label can't be told apart; keep one per source+rent to avoid over-merging
    blank = df.unit_key == ""
    df.loc[blank, "dedupe_key"] += "|" + df.loc[blank, "listed_rent"].astype(str)
    # prefer rows with more gate facts, then detail pages
    facts = ["dogs", "elevator", "floor", "available_date", "sqft", "parking_type"]
    df["_fill"] = sum((df[c].astype(str).str.strip().str.lower().isin(["", "unknown", "nan"]) == False).astype(int) for c in facts)  # noqa: E712
    df["_detail"] = (df.detail_level.str.lower() != "card").astype(int)
    df = df.sort_values(["_detail", "_fill"], ascending=False)
    df["also_seen_at"] = df.groupby("dedupe_key").url.transform(lambda s: " ".join(s.iloc[1:6]))
    df = df.drop_duplicates("dedupe_key", keep="first").copy()
    n_dedup = len(df)

    # community-level facts read from management sites' own pages (scripts/community_facts.py) fill listing blanks
    cf = DATA / "reference" / "community_facts.csv"
    if cf.exists():
        c = pd.read_csv(cf, dtype=str, keep_default_na=False)
        # Join on normalized address + ZIP first (site + name matched only 14 of 271 communities), then on name.
        c["_ka"] = c.address.map(norm_addr) + "|" + c.zip.str.extract(r"(\d{5})", expand=False).fillna("")
        c["_kn"] = c.building_name.str.lower().str.strip()
        ca = c[c._ka.str.len() > 6].drop_duplicates("_ka").set_index("_ka")
        cn = c[c._kn != ""].drop_duplicates("_kn").set_index("_kn")
        ka, kn = df.addr_key, df.building_name.str.lower().str.strip()

        class _Both:
            def __getitem__(self, col):
                return (ca[col], cn[col])
        c = _Both()

        class _K:
            def map(self, pair):
                a, n = pair
                return ka.map(a).where(lambda x: x.notna() & (x != ""), kn.map(n))
        k = _K()
        blank = lambda col: df[col].astype(str).str.strip().str.lower().isin(["", "unknown", "nan"])

        def fill(col, src, ok=lambda v: v not in ("", "unknown")):
            v = k.map(c[src]).fillna("")
            m = blank(col) & v.map(ok)
            df.loc[m, col] = v[m]
        fill("dogs", "dogs")
        fill("dog_weight_limit_lb", "dog_weight_limit_lb", lambda v: v.replace(".", "").isdigit())
        fill("elevator", "elevator")
        fill("building_floors", "floors_total", lambda v: v.isdigit())
        fill("building_floors", "highest_floor_mentioned", lambda v: v.isdigit())
        fill("pet_rent", "pet_rent_monthly", lambda v: v.replace(".", "").isdigit())
        fill("parking_fee", "parking_fee_monthly", lambda v: v.replace(".", "").isdigit())
        fill("parking_type", "parking_type")
        df["community_building_type"] = k.map(c["building_type"]).fillna("")
        df["community_required_fees"] = k.map(c["required_monthly_fees"]).fillna("")
        df["community_parking_text"] = k.map(c["parking_fee_monthly"]).fillna("")       # text; parsed in build_master (W4)
        df["community_utilities_included"] = k.map(c["utilities_included"]).fillna("")
        df["community_utilities_resident_pays"] = k.map(c["utilities_resident_pays"]).fillna("")
        for col in ("pool", "dog_park_pet_spa", "gym", "controlled_access", "package_room"):
            df["community_" + col] = k.map(c[col]).fillna("")
    else:
        for col in ("community_building_type", "community_parking_text", "community_utilities_included", "community_utilities_resident_pays"):
            df[col] = ""

    df = apply_resolved_pending(df)

    df["g_type"] = df.apply(gate_type, axis=1)
    df["g_rent"] = df.apply(gate_rent, axis=1)
    df["g_movein"] = df.apply(gate_movein, axis=1)
    df["g_dog"] = df.apply(gate_dog, axis=1)
    # NYC: the city's building class and floor count from PLUTO (scripts/enrich_nyc_pluto.py), used only on the listing's own lot
    pcols = ["elevator_from_class", "pluto_class", "pluto_floors", "pluto_units", "pluto_year", "pluto_bbl", "match_basis", "pluto_address"]
    pf = DATA / "reference" / "nyc_building_facts.csv"
    pl = pd.read_csv(pf, dtype=str, keep_default_na=False).drop_duplicates("addr_key").set_index("addr_key") if pf.exists() else pd.DataFrame()
    for col in pcols:
        df[col] = df.addr_key.map(pl[col]).fillna("") if col in pl else ""
    # the city's device list: zero active passenger elevators on the lot cancels the elevator class
    devices = {}
    nrf = DATA / "evidence" / "nyc_records.csv"
    if nrf.exists():
        NR = pd.read_csv(nrf, dtype=str, keep_default_na=False)
        for r in NR[NR.record_type == "dob_elevator_devices_active"].itertuples():
            v = to_num(r.count)
            if v is not None:
                devices[r.addr_key] = int(v)
    # a page that was read states an elevator where the listing row leaves it open (evidence pass, amenities pages)
    ev, against = elevator_evidence_rows()
    el = [parsers.elevator_rule(**elevator_facts(r, ev.get(r.addr_key, ("", ""))[0], r.addr_key in against, devices.get(r.addr_key))) for r in df.itertuples()]
    df["g_elevator"] = [_GATE_OF[x[0]] for x in el]
    df["elevator_basis"] = [x[1] for x in el]
    df["elevator_rule_status"] = [x[0] for x in el]          # established / open / no / unknown (parsers.elevator_rule)
    by_ev = df.elevator_basis.isin(["evidence_confirmed", "evidence_stated", "amenities_page"])
    df["elevator_evidence_source"] = ""
    df.loc[by_ev, "elevator_evidence_source"] = df.loc[by_ev, "addr_key"].map(lambda k: ev[k][1])
    # the height finding by itself (whatever better basis the row also has): build_master.py and rank.py read it, so
    # "a real height of 6+ floors" means the same at every stage
    hb = [parsers.elevator_rule(**{**elevator_facts(r), "stated": False, "record_class": ""}) for r in df.itertuples()]
    df["elevator_height_basis"] = [b if s_ == "open" else "" for s_, b in hb]
    fl = df.apply(gate_floor, axis=1)
    df["g_floor"] = [x[0] for x in fl]
    df["floor_used"] = [x[1] for x in fl]
    df["floor_basis"] = [x[2] for x in fl]
    df["floor_label_kind"] = [x[3] for x in fl]
    # owner, 2026-11-17 (second trawl): floor and elevator together. A building without an elevator is allowed when the
    # apartment is on floor 2; the ground floor stays out; floor 3 and above need an elevator; no elevator stated and no
    # floor stated is ONE open gate fact (floor_or_elevator). The building's height comes from
    # data/reference/building_stories.csv (build_master.BuildingStories; absent or partial is fine).
    import build_master
    STO = build_master.BuildingStories()
    sto = [STO.lookup(k, "", la, lo) if len(STO) else None for k, la, lo in zip(df.addr_key, df.get("lat", pd.Series("", index=df.index)), df.get("lon", pd.Series("", index=df.index)))]
    df["building_stories"] = [x["stories"] if x else "" for x in sto]
    df["building_stories_basis"] = [x["basis"] if x else "" for x in sto]
    fe = [floor_elevator_gate(es, gf, fu, fb, fk, st_, sb_) for es, gf, fu, fb, fk, st_, sb_ in
          zip(df.elevator_rule_status, df.g_floor, df.floor_used, df.floor_basis, df.floor_label_kind, df.building_stories, df.building_stories_basis)]
    df["g_floor_elevator"] = [x[0] for x in fe]
    df["floor_elevator_code"] = [x[1] for x in fe]
    df["g_place"] = df.drive_min_zip.map(lambda v: "unknown" if pd.isna(v) else ("pass" if v <= MAX_DRIVE_MIN else "fail"))
    df["g_proof"] = df.apply(gate_proof, axis=1)
    age = df.listing_age_days.map(to_num)
    df["stale_listing"] = age.map(lambda v: "yes" if v is not None and v >= STALE_DAYS else "")

    # g_elevator and g_floor stay as columns (what the elevator rule and the floor reading found); the gate that decides is
    # g_floor_elevator (owner, 2026-11-17), which fails a ground-floor unit and a walk-up above floor 2
    gates = ["g_type", "g_rent", "g_movein", "g_dog", "g_floor_elevator", "g_place", "g_proof"]
    must_confirm = ["g_rent", "g_movein", "g_dog", "g_floor_elevator", "g_place", "g_proof"]
    REASON = {"g_rent": RENT_FAIL_REASON}

    def status(r):
        if any(r[g] == "fail" for g in gates):
            return "fail"
        if any(r[g] == "unknown" for g in must_confirm):
            return "pending"
        return "pass"

    df["gate_status"] = df.apply(status, axis=1)
    df["fail_reasons"] = df.apply(lambda r: ";".join((r.floor_elevator_code if g == "g_floor_elevator" else REASON.get(g, g[2:])) for g in gates if r[g] == "fail"), axis=1)
    df["pending_reasons"] = df.apply(lambda r: ";".join(g[2:] for g in must_confirm if r[g] == "unknown"), axis=1)
    df["floor_asterisk"] = (df.g_floor == "unknown").map({True: "yes", False: ""})
    df["floor_elevator_open"] = [c if g == "pass" and c in ("elevator", parsers.FLOOR_OR_ELEVATOR_CODE) else "" for g, c in zip(df.g_floor_elevator, df.floor_elevator_code)]

    df.drop(columns=["_fill", "_detail"]).to_csv(DATA / "listings.csv", index=False)

    lines = ["# Gate summary", "", f"Raw rows: {n_raw}. After dedupe: {n_dedup}.", "",
             "| status | listings | buildings |", "|---|---|---|"]
    for s_, g in df.groupby("gate_status"):
        lines.append(f"| {s_} | {len(g)} | {g.addr_key.nunique()} |")
    lines += ["", "## Each gate (after dedupe)", "", "| gate | pass | fail | unknown |", "|---|---|---|---|"]
    for g in gates + ["g_elevator", "g_floor"]:
        c = df[g].value_counts()
        lines.append(f"| {g[2:]} | {c.get('pass', 0)} | {c.get('fail', 0)} | {c.get('unknown', 0)} |")
    lines += ["", "## Floor and elevator (owner, 2026-11-17)", "", "| result | listings |", "|---|---|"]
    for k_, n_ in (df.g_floor_elevator + " " + df.floor_elevator_code.replace("", "-")).value_counts().items():
        lines.append(f"| {k_} | {n_} |")
    lines += ["", "## By source", "", df.groupby(["source_site", "gate_status"]).size().unstack(fill_value=0).to_markdown(),
              "", "## Pending reasons (what would need confirming)", "",
              df[df.gate_status == "pending"].pending_reasons.value_counts().head(15).to_markdown(),
              "", "## Passing listings by state and city (top 40)", "",
              df[df.gate_status == "pass"].groupby(["state", "city"]).size().sort_values(ascending=False).head(40).to_markdown()]
    (DATA / "gate_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:22]))


if __name__ == "__main__":
    main()
