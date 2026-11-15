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


def gate_elevator(r):
    """Returns (result, basis). basis: 'stated' (the page lists an elevator), 'inferred_harvester' (the harvester wrote
    yes from the building's height: its note says 'elevator: 6+ floors'; independent check W3), 'inferred_6plus_floors'
    or 'inferred_high_rise_label'. Anything inferred stays an open gate fact until the evidence pass confirms it."""
    e = str(r.elevator).strip().lower()
    notes = str(getattr(r, "notes", ""))
    if e == "no":
        return "fail", "stated"
    if e == "yes":
        return "pass", ("inferred_harvester" if HARVESTER_INFERRED_ELEVATOR.search(notes) else "stated")
    bf = to_num(r.building_floors)
    stated_floor = None if HARVESTER_DERIVED_FLOOR.search(notes) else to_num(r.floor)
    label_floor, kind = parsers.floor_from_label(r.unit, bf)
    tallest = max([v for v in (bf, stated_floor, label_floor if kind == "simple" else None) if v is not None], default=None)
    if tallest is not None and tallest >= INFER_ELEVATOR_FLOORS:
        return "pass", "inferred_6plus_floors"
    if "high-rise" in str(getattr(r, "community_building_type", "")).lower().replace(" ", "-"):
        return "pass", "inferred_high_rise_label"
    return "unknown", ""


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

    df["g_type"] = df.apply(gate_type, axis=1)
    df["g_rent"] = df.apply(gate_rent, axis=1)
    df["g_movein"] = df.apply(gate_movein, axis=1)
    df["g_dog"] = df.apply(gate_dog, axis=1)
    el = df.apply(gate_elevator, axis=1)
    df["g_elevator"] = [x[0] for x in el]
    df["elevator_basis"] = [x[1] for x in el]
    # NYC: official building class from PLUTO (scripts/enrich_nyc_pluto.py) settles what the listing leaves unstated
    pf = DATA / "reference" / "nyc_building_facts.csv"
    if pf.exists():
        pl = pd.read_csv(pf, dtype=str, keep_default_na=False).set_index("addr_key")
        for col in ("elevator_from_class", "pluto_class", "pluto_floors", "pluto_units", "pluto_year", "pluto_bbl", "match_basis"):
            df[col] = df.addr_key.map(pl[col]) if col in pl else ""
        df[["elevator_from_class", "pluto_class", "pluto_floors", "pluto_units", "pluto_year", "pluto_bbl", "match_basis"]] = \
            df[["elevator_from_class", "pluto_class", "pluto_floors", "pluto_units", "pluto_year", "pluto_bbl", "match_basis"]].fillna("")
        unstated = df.elevator_basis != "stated"
        yes = unstated & (df.elevator_from_class == "yes")
        no = unstated & (df.elevator_from_class == "no") & (df.elevator_basis == "")
        df.loc[yes, ["g_elevator", "elevator_basis"]] = ["pass", "nyc_pluto_building_class"]
        df.loc[no, ["g_elevator", "elevator_basis"]] = ["fail", "nyc_pluto_building_class"]
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
