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

WINDOW_END = date(2026, 12, 15)
RENT_MAX = 3000
MIN_DOG_LIMIT_LB = 40
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


def floor_from_unit(unit: str):
    """Infer floor from a unit label: '4F' -> 4, '1203' -> 12, '305' -> 3, 'PH2' -> None, 'G1'/'L3' -> 0."""
    u = norm_unit(unit)
    if not u:
        return None
    if re.match(r"^(g|gr|grd|lobby|l|b|bsmt|c)\d*$", u):
        return 0
    m = re.match(r"^(\d{1,2})[a-z]{1,2}$", u)          # 4f, 12b
    if m:
        return int(m.group(1))
    m = re.match(r"^[a-z]?(\d{3,4})[a-z]?$", u)        # 305, 1203, a305
    if m:
        return int(m.group(1)[:-2])
    return None


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
    d = str(r.dogs).strip().lower()
    if d == "no":
        return "fail"
    if d != "yes":
        return "unknown"
    lim = to_num(r.dog_weight_limit_lb)
    if lim is not None and lim < MIN_DOG_LIMIT_LB:
        return "fail"
    return "pass"


def gate_elevator(r):
    e = str(r.elevator).strip().lower()
    return {"yes": "pass", "no": "fail"}.get(e, "unknown")


def gate_floor(r):
    f = to_num(r.floor)
    if f is None:
        f = floor_from_unit(r.unit)
    if f is None:
        return "unknown", ""
    return ("pass" if f >= 2 else "fail"), int(f)


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

    df["g_type"] = df.apply(gate_type, axis=1)
    df["g_rent"] = df.apply(gate_rent, axis=1)
    df["g_movein"] = df.apply(gate_movein, axis=1)
    df["g_dog"] = df.apply(gate_dog, axis=1)
    df["g_elevator"] = df.apply(gate_elevator, axis=1)
    fl = df.apply(gate_floor, axis=1)
    df["g_floor"] = [x[0] for x in fl]
    df["floor_used"] = [x[1] for x in fl]
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
