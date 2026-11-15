"""call_sheet: the phone questions for the top places in each year, one row per building.

    python3 scripts/call_sheet.py [--per-year 5] [--years "Little-City,Quiet"] [--hoods "Stamford,..."] [--include-held]
    python3 scripts/call_sheet.py --explode data/evidence/call_answers.csv   # filled sheet -> one row per listing

Reads data/ranked_units.csv (read-only) and writes out/call_sheet.csv and out/call_sheet.md. Nothing is fetched.

A question is asked only when the fact is open in the data: missing, inferred, conflicting, named in the row's
`confirm_what` / `to_confirm` / `tour_confirm`, or listed in `all_in_unknown_lines`. Facts with a value whose basis
is not one of OPEN_BASES are treated as settled and are not asked. Three things have no field in the data at all
and are therefore always asked: whether the unit is still available (a time-sensitive fact), whether a guarantor is
accepted, and the application turnaround. See docs/SHORTLIST_TOOLS.md.

Columns are used only when present, so the script keeps working while the pipeline adds or renames columns.
The helpers here (load_ranked, pick_buildings, haversine, ...) are shared by tour_days.py and recheck_shortlist.py.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
RANKED = DATA / "ranked_units.csv"
NEEDS_CONF = DATA / "needs_confirmation.csv"

MOVE_IN_DEADLINE = "2026-12-15"
MOVE_IN_DEADLINE_TEXT = "Dec 15, 2026"

# A value with one of these bases (or no value) is still open. Any other basis (confirmed, stated, official_record,
# amenities_page, community_page, ...) counts as settled.
OPEN_BASES = {"", "inferred", "unknown", "estimate", "estimated", "assumed", "conflicting", "guess", "not_found"}
BLANKS = {"", "nan", "none", "null", "not_found", "unknown", "not stated", "n/a"}

# Hosts that are listing aggregators or record sources, never a leasing office's own site.
NOT_LEASING_HOSTS = ("trulia.com", "zillow.com", "apartmentlist.com", "zumper.com", "padmapper.com", "apartments.com",
                     "streeteasy.com", "craigslist.org", "openigloo.com", "cityofnewyork.us", "nyc.gov", "jerseydigs.com",
                     "sightmap.com", "niche.com", "google.com", "yelp.com", "reddit.com", "rent.com", "hotpads.com",
                     "realtor.com", "census.gov", "openstreetmap.org", "wikipedia.org", "facebook.com")
PHONE_RE = re.compile(r"(?<![\d-])\(?\b[2-9]\d{2}\)?[-. ]\d{3}[-. ]\d{4}\b(?!-?\d)")

ANSWER_COLS = ["ans_floor", "ans_elevator", "ans_dog_weight_lb", "ans_pet_rent", "ans_parking_fee",
               "ans_required_fees", "ans_lease_term_months", "ans_12mo_price", "ans_available_date",
               "ans_income_multiple", "ans_notes", "called_at"]
# Answers that belong to one unit, not the building. In a building row with several units write "UNIT=value; UNIT=value".
PER_UNIT_ANSWERS = ["ans_floor", "ans_lease_term_months", "ans_12mo_price", "ans_available_date"]


# ------------------------------------------------------------------------------------------------- small helpers
def blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return str(v).strip().lower() in BLANKS


def val(row, *names, default: str = "") -> str:
    """First non-blank value among the named columns; a missing column is the same as a blank."""
    for n in names:
        if n in row and not blank(row[n]):
            return str(row[n]).strip()
    return default


def num(v):
    try:
        f = float(str(v).replace("$", "").replace(",", "").strip())
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def money(v) -> str:
    f = num(v)
    return "" if f is None else f"${f:,.0f}"


def truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "yes", "1", "y")


def settled(row, value_cols, basis_cols=()) -> bool:
    """True when the fact has a value and its basis (when the data gives one) is not an open basis."""
    if isinstance(value_cols, str):
        value_cols = (value_cols,)
    if isinstance(basis_cols, str):
        basis_cols = (basis_cols,)
    if not val(row, *value_cols):
        return False
    present = [b for b in basis_cols if b in row]
    if not present:
        return True
    basis = val(row, *present).lower()
    return basis not in OPEN_BASES


def mentions(row, word: str, cols=("confirm_what", "to_confirm", "tour_confirm")) -> bool:
    return any(word in val(row, c).lower() for c in cols)


def unknown_line(row, word: str) -> bool:
    return word in val(row, "all_in_unknown_lines").lower()


def unit_label(row) -> str:
    u = val(row, "unit")
    return u if u else "(no unit number on the listing)"


def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 3958.8 * 2 * math.asin(math.sqrt(a))


# ------------------------------------------------------------------------------------------------- loading
def load_ranked(path: Path = RANKED) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, low_memory=False, keep_default_na=False)
    return df.loc[:, ~df.columns.str.startswith(("nycrec_", "near250_", "agency_"))].copy()


def shown_rows(df: pd.DataFrame, include_held: bool = False) -> pd.DataFrame:
    keep = df["shown"].map(truthy) if "shown" in df else pd.Series(True, index=df.index)
    if include_held and "held_for_confirmation" in df:
        keep = keep | df["held_for_confirmation"].map(truthy)
    out = df[keep].copy()
    if include_held and NEEDS_CONF.exists() and "to_confirm" in out:
        # needs_confirmation.csv carries the question for held units; use it where the ranked row has none.
        nc = pd.read_csv(NEEDS_CONF, dtype=str, keep_default_na=False)
        if {"listing_id", "to_confirm"} <= set(nc.columns):
            q = dict(zip(nc["listing_id"], nc["to_confirm"]))
            empty = out["to_confirm"].map(blank)
            out.loc[empty, "to_confirm"] = out.loc[empty, "listing_id"].map(q).fillna("")
    return out


def _filter_contains(df, col, wanted: str | None):
    if not wanted or col not in df:
        return df
    pats = [w.strip().lower() for w in wanted.split(",") if w.strip()]
    return df[df[col].str.lower().map(lambda v: any(p in v for p in pats))]


def _rank_key(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_score"] = df["rank_score"].map(num).fillna(-1e9) if "rank_score" in df else 0.0
    df["_srank"] = df["shown_rank"].map(num).fillna(1e9) if "shown_rank" in df else 0.0
    return df.sort_values(["_score", "_srank", "listing_id"], ascending=[False, True, True], kind="mergesort")


def building_key(row) -> str:
    return val(row, "building_id") or val(row, "addr_key") or val(row, "address") or val(row, "listing_id")


def pick_buildings(df: pd.DataFrame, per_year: int = 5, years: str | None = None, hoods: str | None = None,
                   include_held: bool = False) -> list[dict]:
    """Top `per_year` buildings in each year, by the best rank_score of their shown units.

    Returns a list of {"year", "year_rank", "building_id", "units": [row dicts, best first]} in year, rank order.
    A building's candidate units are all of its selected (shown, or held with --include-held) units in that year.
    """
    s = shown_rows(df, include_held)
    s = _filter_contains(s, "group_label", years)
    s = _filter_contains(s, "hood", hoods)
    if s.empty:
        return []
    s = _rank_key(s)
    s["_bkey"] = [building_key(r) for _, r in s.iterrows()]
    if "group_label" not in s:
        s["group_label"] = ""
    picked = []
    for year in sorted(s["group_label"].unique()):
        g = s[s["group_label"] == year]
        order = list(dict.fromkeys(g["_bkey"]))[:max(0, per_year)]
        for i, b in enumerate(order, 1):
            rows = [r.drop(labels=["_score", "_srank", "_bkey"]).to_dict() for _, r in g[g["_bkey"] == b].iterrows()]
            picked.append({"year": year, "year_rank": i, "building_id": b, "units": rows})
    return picked


def buildings_for_ids(df: pd.DataFrame, ids: list[str]) -> tuple[list[dict], list[str]]:
    """Group the listed listing_ids by building, in the order given. Returns (buildings, ids not found)."""
    by_id = {r["listing_id"]: r.to_dict() for _, r in df.iterrows()}
    groups: dict[str, dict] = {}
    missing = []
    for i in dict.fromkeys(ids):
        r = by_id.get(i)
        if r is None:
            missing.append(i)
            continue
        b = building_key(r)
        g = groups.setdefault(b, {"year": val(r, "group_label"), "year_rank": "", "building_id": b, "units": []})
        g["units"].append(r)
    return list(groups.values()), missing


def read_ids(arg: str) -> list[str]:
    """--ids value: a file (one listing_id per line, or a CSV with a listing_id column) or a comma list."""
    p = Path(arg)
    if p.exists() and p.is_file():
        text = p.read_text(encoding="utf8")
        first = text.splitlines()[0] if text.strip() else ""
        if "listing_id" in [c.strip() for c in first.split(",")]:
            col = pd.read_csv(p, dtype=str, keep_default_na=False)["listing_id"]
            ids = []
            for v in col:  # a call-sheet row can hold several ids joined with "; "
                ids += [x.strip() for x in v.split(";")]
        else:
            ids = [ln.strip() for ln in text.splitlines()]
        return [i for i in ids if i and not i.startswith("#")]
    return [i.strip() for i in arg.split(",") if i.strip()]


# ------------------------------------------------------------------------------------------------- questions
def unit_questions(u) -> list[tuple[str, str]]:
    """Questions that belong to one unit: floor, the rent terms, availability."""
    qs = []
    label = unit_label(u)
    has_unit = bool(val(u, "unit"))
    rent = money(val(u, "listed_rent"))

    # floor
    floor = val(u, "unit_floor", "floor_used", "floor")
    floor_basis_cols = [c for c in ("unit_floor_basis", "floor_basis") if c in u]
    floor_open = (not settled(u, ("unit_floor", "floor_used", "floor"), floor_basis_cols[:1])
                  or mentions(u, "floor"))
    if floor_open:
        if not has_unit:
            qs.append(("floor", f"Which unit is the one advertised at {rent or 'the listed price'}, and which floor is it on? "
                                "(ground floor is not acceptable)"))
        elif floor:
            qs.append(("floor", f"Which floor is unit {label} on? (we have floor {num(floor):g} only as a reading of "
                                "the unit number, not from a page)" if num(floor) is not None
                       else f"Which floor is unit {label} on?"))
        else:
            qs.append(("floor", f"Which floor is unit {label} on? (ground floor is not acceptable)"))

    # price: gross or net, lease term, 12-month price
    price_is = val(u, "rent_listed_price_is").lower()
    offer = val(u, "rent_offer_text", "concession_text")
    net_open = (price_is in ("", "unknown") or truthy(val(u, "rent_needs_call"))
                or ("rent_listed_price_is" not in u and truthy(val(u, "rent_asterisk"))))
    if net_open:
        q = f"Is the listed {rent} for unit {label} the full monthly rent, or a net price after a concession?"
        if offer:
            q += f' (the listing shows an offer: "{offer[:110]}")'
        qs.append(("rent_gross_or_net", q))
    months = num(val(u, "rent_lease_months", "price_lease_months"))
    twelve = val(u, "price_12_month")
    if months is None:
        qs.append(("lease_term", f"Which lease term does the {rent} price for unit {label} apply to, and what is the "
                                 "monthly price on a 12-month lease?"))
    elif months != 12 and not twelve:
        qs.append(("lease_term", f"The {rent} price for unit {label} is for a {months:g}-month lease. What is the monthly "
                                 "price on a 12-month lease?"))

    # first full payment
    first = val(u, "rent_first_full_payment_date")
    note = val(u, "rent_first_full_payment_note").lower()
    free = num(val(u, "rent_free_months")) or 0
    if not first or "not stated" in note or free > 0 or price_is == "net_effective":
        why = "there is a free period" if (free > 0 or price_is == "net_effective") else "the listing does not say"
        qs.append(("first_payment", f"On what date is the first full rent payment due for unit {label}? ({why})"))

    # availability: time-sensitive, always asked
    avail = val(u, "available_date", "available_date_text")
    seen = val(u, "live_checked_at", "last_seen")[:10]
    known = f"the listing said {'available now' if avail.lower() == 'now' else avail}" if avail else "no date on the listing"
    if seen:
        known += f" when seen on {seen}"
    qs.append(("available", f"Is unit {label} still available, and for what move-in date? It must be on or before "
                            f"{MOVE_IN_DEADLINE_TEXT} ({known})."))
    return qs


def building_questions(units: list) -> list[tuple[str, str]]:
    """Questions that belong to the building. A fact is open when it is open on any of the building's rows."""
    qs = []
    u0 = units[0]

    def any_open(fn):
        return any(fn(u) for u in units)

    # elevator
    def elev_open(u):
        return (val(u, "elevator").lower() != "yes" or not settled(u, "elevator", "elevator_basis")
                or mentions(u, "elevator") or truthy(val(u, "elevator_evidence_open")))
    if any_open(elev_open):
        labels = ", ".join(dict.fromkeys(unit_label(u) for u in units if val(u, "unit")))
        which = f"unit {labels}" if labels else "the advertised unit"
        qs.append(("elevator", f"Is there an elevator in the building that {which} is in, and does it reach that floor? "
                               "(no page states one)"))

    # dogs allowed
    def dogs_open(u):
        return (val(u, "dogs_allowed").lower() != "yes" or not settled(u, "dogs_allowed", "dogs_allowed_basis")
                or mentions(u, "dogs allowed") or mentions(u, "are dogs") or truthy(val(u, "dogs_evidence_open")))
    if any_open(dogs_open):
        why = " (two sources disagree)" if val(u0, "dogs_allowed").lower() == "conflicting" else ""
        qs.append(("dogs_allowed", f"Are dogs allowed?{why}"))

    # weight limit
    def weight_open(u):
        return not settled(u, "dog_weight_limit_lb", "dog_weight_limit_lb_basis") or mentions(u, "weight")
    if any_open(weight_open):
        hint = val(u0, "dog_weight_text", "dog_size_only")
        hint = f' (the listing only says: "{hint[:80]}")' if hint else ""
        qs.append(("dog_weight", f"What is the dog weight limit in pounds?{hint} (we need 25 lb or more)"))

    # breeds: no field in the data records an explicit list, so this is asked unless a page says there are none
    policy = " ".join(val(u, c) for u in units for c in ("dog_policy_text", "dogs_allowed_note", "dog_weight_text"))
    if not re.search(r"no breed restriction", policy, re.I):
        hint = " (the listing mentions breed restrictions but does not list them)" if re.search(r"breed", policy, re.I) else ""
        qs.append(("dog_breeds", f"Are there breed restrictions, and which breeds?{hint}"))

    # pet rent and one-time fee
    pet_rent_open = any_open(lambda u: not settled(u, ("pet_rent", "pet_rent_monthly"), "pet_rent_monthly_basis")
                             or unknown_line(u, "pet rent"))
    pet_fee_open = any_open(lambda u: not val(u, "pet_one_time_fee_text"))
    if pet_rent_open and pet_fee_open:
        qs.append(("pet_rent", "What is the monthly pet rent for one dog, and the one-time pet fee or deposit?"))
    elif pet_rent_open:
        qs.append(("pet_rent", "What is the monthly pet rent for one dog?"))
    elif pet_fee_open:
        qs.append(("pet_fee", "Is there a one-time pet fee or pet deposit, and how much?"))

    # parking
    ptext = " ".join(val(u, c) for u in units for c in ("parking_text", "parking_fee_note", "parking_options"))
    fee_open = any_open(lambda u: not settled(u, ("parking_fee", "parking_fee_monthly"), "parking_fee_monthly_basis")
                        or unknown_line(u, "parking"))
    type_open = any_open(lambda u: not val(u, "parking_type"))
    wait_open = not re.search(r"wait\s?list", ptext, re.I)
    parts = []
    if fee_open:
        parts += ["is a spot included in the rent", "if not, what is the monthly fee"]
    if type_open:
        parts.append("is it a garage or an open lot")
    if wait_open:
        parts.append("is a spot available now or is there a waitlist")
    if parts:
        q = "Parking: " + "; ".join(parts) + "?"
        qs.append(("parking", q))

    # required monthly fees
    ftext = " ".join(val(u, "required_fees_text") for u in units)
    fees_open = (any_open(lambda u: unknown_line(u, "building fees")) or not ftext.strip()
                 or bool(re.search(r"not shown|not stated|amount unknown", ftext, re.I)))
    if fees_open:
        hint = f' (the listing mentions: "{ftext.strip()[:90]}")' if ftext.strip() else ""
        qs.append(("required_fees", "What are all the required monthly fees on top of rent (amenity, trash, pest, "
                                    f"technology or package fees, utility billing fee), each with its amount?{hint}"))

    # utilities
    if any_open(lambda u: not settled(u, "utilities_included", "utilities_included_basis")):
        qs.append(("utilities", "Which utilities are included in the rent (heat, hot water, water and sewer, gas, "
                                "electricity, trash), and which does the tenant pay?"))

    # income and guarantor (guarantor has no field: always asked)
    income = val(u0, "income_requirement")
    if any_open(lambda u: not val(u, "income_requirement")):
        qs.append(("income", "What is the income requirement as a multiple of the monthly rent, and is a guarantor accepted?"))
    else:
        qs.append(("guarantor", f'Is a guarantor accepted? (the listing states the income requirement: "{income[:80]}")'))

    # application turnaround (no field: always asked)
    qs.append(("turnaround", "How long does an application take from submission to approval, and can a lease start "
                             f"by {MOVE_IN_DEADLINE_TEXT}?"))
    return qs


def questions_for_building(units: list) -> list[tuple[str, str]]:
    """All questions for one building: per-unit questions for each candidate unit, then the building questions."""
    per_unit: dict[str, list[str]] = {}
    for u in units:
        for k, q in unit_questions(u):
            per_unit.setdefault(k, []).append(q)
    order = ["available", "floor", "rent_gross_or_net", "lease_term", "first_payment"]
    out = [(k, q) for k in order for q in per_unit.get(k, [])]
    b = building_questions(units)
    # elevator goes right after the floor questions; the rest follow the rent questions
    elev = [x for x in b if x[0] == "elevator"]
    rest = [x for x in b if x[0] != "elevator"]
    n_head = sum(1 for k, _ in out if k in ("available", "floor"))
    return out[:n_head] + elev + out[n_head:] + rest


# ------------------------------------------------------------------------------------------------- contact
def contact_for(units: list) -> tuple[str, str]:
    """(contact, basis). Only what is already in the data: a phone number in the notes, or a non-aggregator site."""
    phones, sites = [], []
    for u in units:
        for c in ("notes", "live_notes", "ev_pause_notes"):
            for m in PHONE_RE.finditer(val(u, c)):
                if m.group(0) not in phones:
                    phones.append(m.group(0))
        for c in ("building_url", "url"):
            link = val(u, c)
            host = urlparse(link).netloc.lower()
            if host and not any(host == h or host.endswith("." + h) for h in NOT_LEASING_HOSTS) and link not in sites:
                sites.append(link)
    parts, basis = [], []
    if phones:
        parts.append("phone " + ", ".join(phones))
        basis.append("phone number appears in the listing notes (check it is the leasing office)")
    if sites:
        parts.append("site " + " ".join(sites[:2]))
        basis.append("the building's own site, from the listing's url or building_url")
    return "; ".join(parts), "; ".join(basis)


def known_facts(units: list) -> str:
    """One line of what the data already holds, so the caller can check it rather than ask it."""
    u = units[0]
    bits = []
    if val(u, "elevator").lower() == "yes" and settled(u, "elevator", "elevator_basis"):
        bits.append(f"elevator: yes ({val(u, 'elevator_basis') or 'listing'})")
    if settled(u, "dog_weight_limit_lb", "dog_weight_limit_lb_basis"):
        w = val(u, "dog_weight_limit_lb")
        bits.append(f"dog weight limit: {w if not num(w) else f'{num(w):g} lb'}")
    if settled(u, ("pet_rent", "pet_rent_monthly"), "pet_rent_monthly_basis"):
        bits.append(f"pet rent: {money(val(u, 'pet_rent', 'pet_rent_monthly'))}/mo")
    if settled(u, ("parking_fee", "parking_fee_monthly"), "parking_fee_monthly_basis"):
        f = num(val(u, "parking_fee", "parking_fee_monthly"))
        bits.append("parking: a spot is included or free" if f == 0 else f"parking fee: {money(f)}/mo")
    if val(u, "utilities_included") and settled(u, "utilities_included", "utilities_included_basis"):
        bits.append(f"utilities included: {val(u, 'utilities_included')[:60]}")
    if val(u, "income_requirement"):
        bits.append(f"income: {val(u, 'income_requirement')[:60]}")
    return "; ".join(bits)


# ------------------------------------------------------------------------------------------------- output
def unit_summary(u) -> str:
    bits = [f"unit {unit_label(u)}"]
    if money(val(u, "listed_rent")):
        bits.append(f"listed {money(val(u, 'listed_rent'))}")
    if money(val(u, "all_in")):
        bits.append(f"all-in {money(val(u, 'all_in'))}" + ("*" if val(u, "all_in_unknown_lines") else ""))
    a = val(u, "available_date", "available_date_text")
    if a:
        bits.append(f"available {a}")
    if truthy(val(u, "held_for_confirmation")):
        bits.append("HELD (not on the page until confirmed)")
    return ", ".join(bits)


def sheet_rows(buildings: list[dict]) -> list[dict]:
    rows = []
    for b in buildings:
        units = b["units"]
        u0 = units[0]
        qs = questions_for_building(units)
        contact, cbasis = contact_for(units)
        rows.append({
            "year": b["year"], "year_rank": b["year_rank"], "hood": val(u0, "hood"),
            "building_id": val(u0, "building_id") or b["building_id"],
            "building_name": val(u0, "building_name"), "address": val(u0, "address"),
            "city": val(u0, "city"), "state": val(u0, "state"),
            "listing_ids": "; ".join(val(u, "listing_id") for u in units),
            "units": "; ".join(unit_label(u) for u in units),
            "candidates": " | ".join(unit_summary(u) for u in units),
            "listing_url": " ".join(dict.fromkeys(val(u, "url") for u in units if val(u, "url"))),
            "contact": contact, "contact_basis": cbasis,
            "already_known": known_facts(units),
            "n_questions": len(qs),
            "question_keys": "; ".join(dict.fromkeys(k for k, _ in qs)),
            "questions": " | ".join(f"{i}. {q}" for i, (_, q) in enumerate(qs, 1)),
            "_qs": qs,
            **{c: "" for c in ANSWER_COLS},
        })
    return rows


def write_outputs(rows: list[dict], out_dir: Path = OUT, note: str = "") -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    has_contact = any(r["contact"] for r in rows)
    cols = [c for c in (rows[0].keys() if rows else []) if c != "_qs"]
    if not has_contact:
        cols = [c for c in cols if c not in ("contact", "contact_basis")]
    csv_path, md_path = out_dir / "call_sheet.csv", out_dir / "call_sheet.md"
    pd.DataFrame([{c: r[c] for c in cols} for r in rows], columns=cols).to_csv(csv_path, index=False)

    n_contact = sum(1 for r in rows if r["contact"])
    md = ["# Call sheet", "",
          f"{len(rows)} buildings, {sum(len(r['listing_ids'].split('; ')) for r in rows)} candidate units. {note}".strip(),
          "", f"Move-in must be on or before {MOVE_IN_DEADLINE_TEXT}. Questions are only the facts still open in the data; "
          "\"Already known\" lists what not to ask. An asterisk on all-in means some cost lines are still unknown.",
          "", (f"Contact details are in the data for {n_contact} of {len(rows)} buildings; for the rest, use the listing link."
               if has_contact else "No phone number or leasing site is in the data for these buildings; use the listing link."),
          ""]
    year = None
    for r in rows:
        if r["year"] != year:
            year = r["year"]
            md += [f"## {year or 'No year'}", ""]
        name = r["building_name"] or r["address"]
        rank = f"{r['year_rank']}. " if r["year_rank"] != "" else ""
        md.append(f"### {rank}{name} ({r['hood']})")
        md.append(f"- Address: {r['address']}" + (f", {r['city']}" if r["city"] else "") + (f" {r['state']}" if r["state"] else ""))
        for c in r["candidates"].split(" | "):
            md.append(f"- Candidate: {c}")
        if r["contact"]:
            md.append(f"- Contact: {r['contact']}")
        md.append(f"- Listing: {r['listing_url']}")
        if r["already_known"]:
            md.append(f"- Already known (do not ask): {r['already_known']}")
        md.append("")
        md += [f"{i}. [ ] {q}" for i, (_, q) in enumerate(r["_qs"], 1)]
        md.append("")
    md_path.write_text("\n".join(md), encoding="utf8")
    return csv_path, md_path


# ------------------------------------------------------------------------------------------------- answers
def answers_by_listing(filled: pd.DataFrame) -> pd.DataFrame:
    """A filled call sheet (one row per building) -> one row per listing_id, ready to merge.

    Building answers are copied to each of the row's listings. Per-unit answers (PER_UNIT_ANSWERS) may be written
    as one value (applies to every unit in the row) or as "UNIT=value; UNIT=value".
    """
    out = []
    for _, r in filled.iterrows():
        ids = [x.strip() for x in str(r.get("listing_ids", "")).split(";") if x.strip()]
        units = [x.strip() for x in str(r.get("units", "")).split(";")]
        units += [""] * (len(ids) - len(units))
        for lid, unit in zip(ids, units):
            row = {"listing_id": lid, "building_id": r.get("building_id", ""), "unit": unit}
            for c in ANSWER_COLS:
                v = "" if blank(r.get(c, "")) else str(r.get(c, "")).strip()
                if c in PER_UNIT_ANSWERS and "=" in v:
                    pairs = dict((p.split("=", 1)[0].strip().lower(), p.split("=", 1)[1].strip())
                                 for p in v.split(";") if "=" in p)
                    v = pairs.get(unit.lower(), "")
                row[c] = v
            out.append(row)
    return pd.DataFrame(out, columns=["listing_id", "building_id", "unit"] + ANSWER_COLS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--per-year", type=int, default=5, help="buildings per year (default 5)")
    ap.add_argument("--years", help='comma list; a year is kept when its label contains one of these, e.g. "Quiet,Fresh"')
    ap.add_argument("--hoods", help="comma list of neighborhood names (substring match)")
    ap.add_argument("--include-held", action="store_true", help="also consider units held for confirmation")
    ap.add_argument("--ranked", default=str(RANKED), help="ranked units CSV (default data/ranked_units.csv)")
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--explode", metavar="FILLED_CSV", help="turn a filled call sheet into one row per listing")
    a = ap.parse_args(argv)

    out_dir = Path(a.out_dir)
    if a.explode:
        df = answers_by_listing(pd.read_csv(a.explode, dtype=str, keep_default_na=False))
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "call_answers_by_listing.csv"
        df.to_csv(p, index=False)
        print(f"{len(df)} listing rows -> {p}")
        return 0

    df = load_ranked(Path(a.ranked))
    buildings = pick_buildings(df, a.per_year, a.years, a.hoods, a.include_held)
    if not buildings:
        print("No buildings match.", file=sys.stderr)
        return 1
    rows = sheet_rows(buildings)
    note = f"Top {a.per_year} buildings per year by rank score" + (", held units included" if a.include_held else "") + "."
    csv_path, md_path = write_outputs(rows, out_dir, note)
    nq = sum(r["n_questions"] for r in rows)
    print(f"{len(rows)} buildings, {nq} questions -> {csv_path.relative_to(ROOT) if csv_path.is_relative_to(ROOT) else csv_path}, "
          f"{md_path.name}; contact present for {sum(1 for r in rows if r['contact'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
