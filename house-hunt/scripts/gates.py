"""Merge data/listings_raw/*.csv, dedupe, and apply the approved gates (docs/PLAN_V3_APPROVED_2026-11-15.md).

Each gate yields pass / fail / unknown. Overall status:
  pass      every gate passes (floor may be unknown -> flagged with an asterisk, per the plan)
  pending   nothing fails, but a gate that must be confirmed is unknown (dogs, elevator, availability, proof)
  fail      at least one gate fails
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
RENT_MAX = 3000
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


INFER_ELEVATOR_FLOORS = 6  # Will, 2026-11-15: a building of 6+ floors is treated as having an elevator (asterisk)
# The harvester wrote elevator "yes" from unit labels on the page ("elevator: 6+ floors (unit numbers on the page reach
# floor 37)"): a height guessed from labels, which does not support an elevator.
HARVESTER_LABEL_HEIGHT = re.compile(r"elevator: \d+\+ floors\W{0,3}unit numbers", re.I)
EXACT_LOT = "house_number+location"   # nyc_building_facts.match_basis when the tax lot is the listing's own address
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


def gate_elevator(r):
    """Returns (result, basis). The elevator gate passes only on:
      'stated'                   a page lists an elevator (a listing site's amenity list counts)
      'inferred_harvester'       the harvester wrote yes from a height a page gives (a SightMap floor list, the floor
                                 field of a page; independent check W3)
      'inferred_6plus_floors'    a page or record gives the building 6+ floors (page_height; PLUTO floors in main())
      'inferred_high_rise_label' the management's own page calls the building a high-rise
    plus, in main(): 'nyc_pluto_building_class' (the city's elevator class on the listing's own lot) and
    'evidence_confirmed' / 'evidence_stated' / 'amenities_page' (elevator_evidence). Anything inferred stays an open
    gate fact until the evidence pass confirms it. A floor read from a unit label NEVER supports the elevator
    (owner's rule, CLAUDE.md): such a listing is 'unknown' (pending). The floor gate still reads labels (gate_floor)."""
    e = str(r.elevator).strip().lower()
    notes = str(getattr(r, "notes", ""))
    if e == "no":
        return "fail", "stated"
    if e == "yes":
        if not HARVESTER_INFERRED_ELEVATOR.search(notes):
            return "pass", "stated"
        if not HARVESTER_LABEL_HEIGHT.search(notes):
            return "pass", "inferred_harvester"
        # the harvester's yes rests on unit labels: it counts only if a page or record gives the height (below)
    tallest = page_height(r)
    if tallest is not None and tallest >= INFER_ELEVATOR_FLOORS:
        return "pass", "inferred_6plus_floors"
    if "high-rise" in str(getattr(r, "community_building_type", "")).lower().replace(" ", "-"):
        return "pass", "inferred_high_rise_label"
    return "unknown", ""


def elevator_from_pluto_floors(pluto_floors, match_basis, elevator_from_class=""):
    """True when the city's record gives 6+ floors for the listing's own lot (an exact lot match) and its building
    class does not say walk-up. A neighbouring lot's height says nothing about this building."""
    v = to_num(pluto_floors)
    return v is not None and v >= INFER_ELEVATOR_FLOORS and match_basis == EXACT_LOT and elevator_from_class != "no"


def elevator_evidence(folder=None, amenities=None) -> dict:
    """addr_key -> (basis, source): buildings where a page that was read states an elevator although the listing row
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
    return {k: v for k, v in out.items() if k not in against}


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

    grid = pd.read_csv(DATA / "reference" / "search_grid.csv", dtype={"zcta": str})
    drive = dict(zip(grid.zcta, grid.drive_min))
    df["zip5"] = df.zip.str.extract(r"(\d{5})", expand=False).fillna("")
    df["drive_min_zip"] = df.zip5.map(drive)

    df["addr_key"] = df.address.map(norm_addr) + "|" + df.zip5
    df["unit_key"] = df.unit.map(norm_unit)
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
    el = df.apply(gate_elevator, axis=1)
    df["g_elevator"] = [x[0] for x in el]
    df["elevator_basis"] = [x[1] for x in el]
    # a page that was read states an elevator where the listing row leaves it open (evidence pass, amenities pages)
    ev = elevator_evidence()
    hit = (df.g_elevator == "unknown") & df.addr_key.isin(ev.keys())
    df["elevator_evidence_source"] = ""
    df.loc[hit, "g_elevator"] = "pass"
    df.loc[hit, "elevator_basis"] = df.loc[hit, "addr_key"].map(lambda k: ev[k][0])
    df.loc[hit, "elevator_evidence_source"] = df.loc[hit, "addr_key"].map(lambda k: ev[k][1])
    # NYC: official building class from PLUTO (scripts/enrich_nyc_pluto.py) settles what the listing leaves unstated
    pf = DATA / "reference" / "nyc_building_facts.csv"
    if pf.exists():
        pl = pd.read_csv(pf, dtype=str, keep_default_na=False).set_index("addr_key")
        for col in ("elevator_from_class", "pluto_class", "pluto_floors", "pluto_units", "pluto_year", "pluto_bbl", "match_basis"):
            df[col] = df.addr_key.map(pl[col]) if col in pl else ""
        df[["elevator_from_class", "pluto_class", "pluto_floors", "pluto_units", "pluto_year", "pluto_bbl", "match_basis"]] = \
            df[["elevator_from_class", "pluto_class", "pluto_floors", "pluto_units", "pluto_year", "pluto_bbl", "match_basis"]].fillna("")
        unstated = df.elevator_basis != "stated"
        # the city's elevator class passes the gate only on the listing's own lot (build_master.py applies the same test)
        yes = unstated & (df.elevator_from_class == "yes") & (df.match_basis == EXACT_LOT)
        no = unstated & (df.elevator_from_class == "no") & (df.elevator_basis == "")
        df.loc[yes, ["g_elevator", "elevator_basis"]] = ["pass", "nyc_pluto_building_class"]
        df.loc[no, ["g_elevator", "elevator_basis"]] = ["fail", "nyc_pluto_building_class"]
        # a real height from the city's record: 6+ floors on the listing's own lot
        tall = (df.g_elevator == "unknown") & pd.Series([elevator_from_pluto_floors(a, b, c) for a, b, c in zip(df.pluto_floors, df.match_basis, df.elevator_from_class)], index=df.index)
        df.loc[tall, ["g_elevator", "elevator_basis"]] = ["pass", "inferred_6plus_floors"]
    fl = df.apply(gate_floor, axis=1)
    df["g_floor"] = [x[0] for x in fl]
    df["floor_used"] = [x[1] for x in fl]
    df["floor_basis"] = [x[2] for x in fl]
    df["floor_label_kind"] = [x[3] for x in fl]
    df["g_place"] = df.drive_min_zip.map(lambda v: "unknown" if pd.isna(v) else ("pass" if v <= MAX_DRIVE_MIN else "fail"))
    df["g_proof"] = df.apply(gate_proof, axis=1)
    age = df.listing_age_days.map(to_num)
    df["stale_listing"] = age.map(lambda v: "yes" if v is not None and v >= STALE_DAYS else "")

    gates = ["g_type", "g_rent", "g_movein", "g_dog", "g_elevator", "g_floor", "g_place", "g_proof"]
    must_confirm = ["g_rent", "g_movein", "g_dog", "g_elevator", "g_place", "g_proof"]  # floor unknown is allowed (asterisk)

    def status(r):
        if any(r[g] == "fail" for g in gates):
            return "fail"
        if any(r[g] == "unknown" for g in must_confirm):
            return "pending"
        return "pass"

    df["gate_status"] = df.apply(status, axis=1)
    df["fail_reasons"] = df.apply(lambda r: ";".join(g[2:] for g in gates if r[g] == "fail"), axis=1)
    df["pending_reasons"] = df.apply(lambda r: ";".join(g[2:] for g in must_confirm if r[g] == "unknown"), axis=1)
    df["floor_asterisk"] = (df.g_floor == "unknown").map({True: "yes", False: ""})

    df.drop(columns=["_fill", "_detail"]).to_csv(DATA / "listings.csv", index=False)

    lines = ["# Gate summary", "", f"Raw rows: {n_raw}. After dedupe: {n_dedup}.", "",
             "| status | listings | buildings |", "|---|---|---|"]
    for s_, g in df.groupby("gate_status"):
        lines.append(f"| {s_} | {len(g)} | {g.addr_key.nunique()} |")
    lines += ["", "## Each gate (after dedupe)", "", "| gate | pass | fail | unknown |", "|---|---|---|---|"]
    for g in gates:
        c = df[g].value_counts()
        lines.append(f"| {g[2:]} | {c.get('pass', 0)} | {c.get('fail', 0)} | {c.get('unknown', 0)} |")
    lines += ["", "## By source", "", df.groupby(["source_site", "gate_status"]).size().unstack(fill_value=0).to_markdown(),
              "", "## Pending reasons (what would need confirming)", "",
              df[df.gate_status == "pending"].pending_reasons.value_counts().head(15).to_markdown(),
              "", "## Passing listings by state and city (top 40)", "",
              df[df.gate_status == "pass"].groupby(["state", "city"]).size().sort_values(ascending=False).head(40).to_markdown()]
    (DATA / "gate_summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:22]))


if __name__ == "__main__":
    main()
