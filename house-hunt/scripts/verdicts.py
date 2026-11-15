"""Reviewed verdicts: the table that says a person (or reviewing agent) has READ the evidence for a unit.

Why this exists (docs/INDEPENDENT_CHECK_2.md): evidence agents wrote their doubts in plain words, and the rules read
only a short list of phrases. No list of phrases will ever be complete. So a unit is shown only when its evidence has
been read and a verdict written:

  data/evidence/review_verdicts.csv
    listing_id, building_id, addr_key, unit,
    verdict        remove | asterisk | ok
    kind           elevator | floor | dogs | not_available | unverified | wrong_building | lease_term | restricted |
                   coop_condo | other          (blank for ok)
    what_to_confirm, why (plain words for the page), evidence_quote, evidence_file, reviewed_at,
    evidence_hash  fingerprint of every evidence row of the building when the verdict was written

  remove    -> scripts/rank.py excludes the unit before ranking, with the reason (data/excluded_by_review.csv)
  asterisk  -> the unit counts as having that open fact: shown with an asterisk that says what and why, or dropped as
               sketchy when that makes two or more open facts
  ok        -> nothing added; the rules' own asterisks still apply. A verdict never closes a fact the rules leave open.

scripts/check_registry.py fails the run when a shown unit has no verdict of ok / asterisk, or when its verdict was
written against older evidence (the fingerprint no longer matches): new evidence must be read before the unit is shown.

Commands
  python3 scripts/verdicts.py pending              shown units with no current verdict (count and list)
  python3 scripts/verdicts.py digest [--out F]     every evidence row for those units, numbered, for the reviewer
  python3 scripts/verdicts.py add FILE             add verdict lines written by the reviewer (format below)
  python3 scripts/verdicts.py restamp-check        list verdicts whose evidence has changed since they were written

Verdict line (one per unit, fields separated by ' | '):
  <listing_id or #n from the digest> | ok
  <id> | asterisk | <kind> | <what to confirm> | <why> | <row tag from the digest, e.g. L2, or a literal quote> [| file]
  <id> | remove   | <kind> | | <why> | <row tag or literal quote> [| file]
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA  # noqa: E402

VERDICTS = DATA / "evidence" / "review_verdicts.csv"
COLS = ["listing_id", "building_id", "addr_key", "unit", "verdict", "kind", "what_to_confirm", "why", "evidence_quote", "evidence_file",
        "reviewed_at", "evidence_hash"]
KINDS = {"elevator", "floor", "dogs", "not_available", "unverified", "wrong_building", "lease_term", "restricted", "coop_condo", "other"}
FAMILIES = ("live_check", "confirm", "facts", "items")
BORING_FACT = re.compile(r"^(?:building_size|building_site|listing_broker|listing_agent|listing_contact|deposit|application_fee|management|registered|"
                         r"total_units|units|year_built|parking|garage|pet_rent|pet_fee|pet_deposit|pet_count|pool|gym|laundry|doorman|concierge|utilities|"
                         r"amenities|storage|move_in_fees|one_time_fees|broker_fee|required|amenity_fee|additional_fees|fee:|optional|dog:|security|in_unit|"
                         r"package|building_floors|building_name|own_site$|openigloo_summary|special|concession|rent_regulation|fees_and|dog_amenit|dog_park|"
                         r"dog_run|owner_of_record|building$|listing_date|listing_updated|floors|unit_count|building_age|open_violations)", re.I)
CAUTION = re.compile(r"co-?op|condo|55\+|senior|age[- ]restrict|income|afford|lottery|wait ?list|stale|last modified|walk-?up|no elevator|stairs|approval|"
                     r"case by case|not allowed|no dogs|no pets|unverified|verify|scam|caution|different building|mismatch|ground|first floor|basement|"
                     r"\b0 available|not available|rented|leased|housing authority|sublet|furnished|short[- ]term|month-to-month", re.I)
ITEM_WORDS = re.compile(r"elevator|stairs|walk-?up|\bdogs?\b|\bpets?\b|55\+|senior|income|section 8|afford|co-?op|condo|ground floor|first floor|basement", re.I)

_cache: dict = {}


def _load():
    if _cache:
        return _cache
    xw = pd.read_csv(DATA / "reference" / "building_crosswalk.csv", dtype=str, keep_default_na=False)
    _cache["a2b"] = dict(zip(xw.addr_key, xw.building_id))
    for fam in FAMILIES:
        fs = sorted(glob.glob(str(DATA / "evidence" / f"{fam}_batch_*.csv")))
        D = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False).assign(src_file=Path(f).name) for f in fs], ignore_index=True) if fs else pd.DataFrame()
        if len(D):
            D["building_id"] = D.addr_key.map(_cache["a2b"]).fillna("")
        _cache[fam] = D
    for name, f in (("nyc", "nyc_records.csv"), ("non_nyc", "non_nyc_records.csv")):
        p = DATA / "evidence" / f
        D = pd.read_csv(p, dtype=str, keep_default_na=False).assign(src_file=f) if p.exists() else pd.DataFrame()
        if len(D):
            D["building_id"] = D.addr_key.map(_cache["a2b"]).fillna("")
        _cache[name] = D
    return _cache


def evidence(building_id: str) -> dict:
    """Every evidence row of a building, across all of its address keys (data/reference/building_crosswalk.csv)."""
    c = _load()
    key = ("ev", building_id)
    if key not in c:
        c[key] = {k: (c[k][c[k].building_id == building_id] if len(c[k]) else c[k]) for k in FAMILIES + ("nyc", "non_nyc")}
    return c[key]


def evidence_hash(building_id: str) -> str:
    """Fingerprint of the building's evidence: live-check, confirm, facts and items rows, and the NYC lot and elevator
    device rows. It changes when any of those rows is added, removed or edited."""
    c = _load()
    key = ("hash", building_id)
    if key in c:
        return c[key]
    ev = evidence(building_id)
    h = hashlib.sha1()
    for fam in FAMILIES:
        D = ev[fam]
        if len(D):
            cols = [x for x in D.columns if x not in ("src_file", "building_id", "retrieved_at")]
            for line in sorted("\x1f".join(str(v) for v in row) for row in D[cols].itertuples(index=False)):
                h.update(line.encode("utf-8", "ignore") + b"\n")
    N = ev["nyc"]
    if len(N):
        N = N[N.record_type.isin(["pluto_lot", "dob_elevator_devices_active"])]
        for line in sorted("\x1f".join([r.addr_key, r.record_type, r.count, r.detail]) for r in N.itertuples()):
            h.update(line.encode("utf-8", "ignore") + b"\n")
    c[key] = h.hexdigest()[:16]
    return c[key]


def load_verdicts() -> pd.DataFrame:
    if not VERDICTS.exists():
        return pd.DataFrame(columns=COLS)
    V = pd.read_csv(VERDICTS, dtype=str, keep_default_na=False)
    for col in COLS:
        if col not in V:
            V[col] = ""
    return V[COLS]


def shown_units() -> pd.DataFrame:
    R = pd.read_csv(DATA / "ranked_units.csv", dtype=str, keep_default_na=False, low_memory=False)
    return R[R.shown == "True"].copy()


def unreviewed(S: pd.DataFrame | None = None):
    """(listing_id, why) for every shown unit without a current ok / asterisk verdict."""
    S = shown_units() if S is None else S
    V = load_verdicts().drop_duplicates("listing_id", keep="last").set_index("listing_id")
    out = []
    for lid, b in zip(S.listing_id, S.building_id):
        if lid not in V.index:
            out.append((lid, "no reviewed verdict: nobody has read this unit's evidence"))
        elif V.at[lid, "verdict"] not in ("ok", "asterisk"):
            out.append((lid, f"verdict is '{V.at[lid, 'verdict']}', so the unit must not be shown"))
        elif V.at[lid, "evidence_hash"] != evidence_hash(b):
            out.append((lid, "the verdict was written against older evidence: the building's evidence rows have changed since the review"))
    return out


def _tagged(building_id: str):
    """[(tag, family, file, text, row)] for a building, in a fixed order, with the tags the digest prints."""
    ev = evidence(building_id)
    rows = []
    L = ev["live_check"]
    if len(L):
        for i, r in enumerate(L.sort_values(["src_file", "unit", "checked_at"]).itertuples(), 1):
            rows.append((f"L{i}", "live_check", r.src_file, f"unit '{r.unit}' {r.status} price {r.price_now} avail '{r.available_now_text}' matches={r.matches_stored} | {r.notes}", r))
    C = ev["confirm"]
    if len(C):
        for i, r in enumerate(C.sort_values(["src_file", "fact"]).itertuples(), 1):
            rows.append((f"C{i}", "confirm", r.src_file, f"{r.fact} [{r.status}] {r.value} | {r.quote}", r))
    F = ev["facts"]
    if len(F):
        for i, r in enumerate(F.sort_values(["src_file", "fact"]).itertuples(), 1):
            rows.append((f"F{i}", "facts", r.src_file, f"{r.fact}: {r.value} | {r.quote}", r))
    I = ev["items"]
    if len(I):
        for i, r in enumerate(I.sort_values(["src_file", "item_date"]).itertuples(), 1):
            rows.append((f"I{i}", "items", r.src_file, f"({r.category}, {r.item_date}, about {r.about}) {r.excerpt}", r))
    N = ev["nyc"]
    if len(N):
        for i, r in enumerate(N[N.record_type.isin(["pluto_lot", "dob_elevator_devices_active"])].sort_values("record_type").itertuples(), 1):
            rows.append((f"N{i}", "nyc", r.src_file, f"{r.record_type}: count {r.count}; {r.detail} (match {r.match_basis})", r))
    return rows


def digest(S: pd.DataFrame, numbered: dict, full=False) -> str:
    """The reviewer's reading file. Every live-check, confirm and NYC lot / device row is printed. Facts are printed
    unless they are routine cost or amenity lines with no caution word; review items are printed when they mention an
    elevator, stairs, dogs, an age or income limit, a co-op or a ground floor. The header counts what was left out."""
    out = []
    g = lambda r, c: str(r.get(c, "") or "")
    for b, grp in S.groupby("building_id", sort=False):
        rows = _tagged(b)
        r0 = grp.iloc[0]
        out.append(f"\n=== {g(r0, 'building_name')} | {g(r0, 'address')}, {g(r0, 'city')} {g(r0, 'state')} | lot: class {g(r0, 'pluto_class')} lot_ok={g(r0, 'pluto_lot_ok')} lot_addr={g(r0, 'pluto_lot_address')} "
                   f"dob_el={g(r0, 'dob_active_elevators')} | floors {g(r0, 'building_floors')}({g(r0, 'building_floors_basis')}) type={g(r0, 'building_type')[:40]}")
        for _, r in grp.iterrows():
            out.append(f"#{numbered[r.listing_id]} unit '{g(r, 'unit')}' {g(r, 'source_site')} rent {g(r, 'listed_rent')} all-in {g(r, 'all_in')} avail {g(r, 'available_date')} | rules: {g(r, 'confirm_what') or 'nothing open'} | "
                       f"elev={g(r, 'elevator')}({g(r, 'elevator_basis')}) floor={g(r, 'unit_floor')}({g(r, 'unit_floor_basis')}/{g(r, 'unit_floor_label_kind')}) dogs={g(r, 'dogs_allowed')}({g(r, 'dogs_allowed_basis')}) "
                       f"wl={g(r, 'dog_weight_limit_lb')} small={'y' if g(r, 'dog_size_only') else ''} live={g(r, 'live_status')} lease={g(r, 'price_lease_months')} age={g(r, 'listing_age_days')} "
                       f"policy='{g(r, 'dog_policy_text')[:110]}' notes='{g(r, 'notes')[:160]}'")
        skipped = {"facts": 0, "items": 0}
        for tag, fam, file, text, r in rows:
            text = re.sub(r"\s+", " ", text)
            if fam == "facts" and not full and BORING_FACT.search(r.fact) and not CAUTION.search(text):
                skipped["facts"] += 1
                continue
            if fam == "items" and not full and not ITEM_WORDS.search(text):
                skipped["items"] += 1
                continue
            lim = {"live_check": 700, "confirm": 380, "facts": 300, "items": 220, "nyc": 260}[fam]
            out.append(f"  {tag} {file.replace('_batch_', ':').replace('.csv', '')} {text[:lim]}")
        nn = evidence(b)["non_nyc"]
        out.append(f"  (not printed: {skipped['facts']} routine cost / amenity facts with no caution word, {skipped['items']} review items that do not mention an elevator, stairs, dogs, age, income, co-op or ground floor"
                   + (f", {len(nn)} non-NYC police / inspection record rows" if len(nn) else "") + ")")
    return "\n".join(out)


def add_lines(lines, numbered=None):
    """Append verdict lines; a later line for the same listing replaces the earlier one."""
    M = pd.read_csv(DATA / "master_units.csv", dtype=str, keep_default_na=False, low_memory=False,
                    usecols=["listing_id", "building_id", "addr_key", "unit", "live_notes"]).set_index("listing_id")
    V = load_verdicts()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    new, bad = [], []
    for raw in lines:
        raw = raw.strip()
        if not raw or raw.startswith("//"):
            continue
        p = [x.strip() for x in raw.split(" | ")]
        lid = p[0]
        if lid.startswith("#") and numbered:
            lid = numbered.get(lid[1:], lid)
        if lid not in M.index:
            bad.append(f"unknown listing: {raw[:80]}")
            continue
        verdict = p[1] if len(p) > 1 else ""
        kind = p[2] if len(p) > 2 else ""
        what = p[3] if len(p) > 3 else ""
        why = p[4] if len(p) > 4 else ""
        quote = p[5] if len(p) > 5 else ""
        file = p[6] if len(p) > 6 else ""
        if verdict not in ("ok", "asterisk", "remove") or (verdict != "ok" and (kind not in KINDS or not why)):
            bad.append(f"bad verdict line: {raw[:100]}")
            continue
        b = M.at[lid, "building_id"]
        tags = {t: (f, txt) for t, _, f, txt, _ in _tagged(b)}
        if re.fullmatch(r"[LCFIN]\d+", quote) and quote in tags:
            file, quote = tags[quote][0], re.sub(r"\s+", " ", tags[quote][1])[:400]
        elif re.fullmatch(r"[LCFIN]\d+", quote):
            bad.append(f"row tag {quote} not found for {lid}")
            continue
        if verdict == "ok" and not quote:
            ev = evidence(b)
            files = sorted({f for fam in FAMILIES for f in (ev[fam].src_file.unique() if len(ev[fam]) else [])})
            quote = "every evidence row for this building was read; nothing in them fails a gate or adds a doubt beyond what the rules already mark"
            file = "; ".join(files) or "no evidence rows on file for this building"
        new.append({"listing_id": lid, "building_id": b, "addr_key": M.at[lid, "addr_key"], "unit": M.at[lid, "unit"], "verdict": verdict, "kind": kind if verdict != "ok" else "",
                    "what_to_confirm": what, "why": why, "evidence_quote": quote, "evidence_file": file, "reviewed_at": now, "evidence_hash": evidence_hash(b)})
    if bad:
        print("\n".join(bad))
        raise SystemExit(f"{len(bad)} verdict line(s) rejected; nothing written")
    V = pd.concat([V, pd.DataFrame(new, columns=COLS)], ignore_index=True).drop_duplicates("listing_id", keep="last")
    V.sort_values(["verdict", "building_id", "listing_id"]).to_csv(VERDICTS, index=False)
    print(f"verdicts written: {len(new)}; table now {len(V)} rows {V.verdict.value_counts().to_dict()}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pending"
    num_file = DATA / "reference" / "review_pending_numbers.json"
    if cmd in ("pending", "digest"):
        S = shown_units()
        pend = unreviewed(S)
        ids = [l for l, _ in pend]
        P = S[S.listing_id.isin(ids)].sort_values(["state", "city", "building_name", "unit"])
        numbered = {lid: str(i) for i, lid in enumerate(P.listing_id, 1)}
        num_file.write_text(json.dumps({v: k for k, v in numbered.items()}, indent=0))
        print(f"shown units: {len(S)}; without a current verdict: {len(pend)}")
        if cmd == "digest":
            txt = digest(P, numbered, full="--full" in sys.argv)
            if "--out" in sys.argv:
                Path(sys.argv[sys.argv.index("--out") + 1]).write_text(txt)
                print(f"digest written: {len(txt)} characters")
            else:
                print(txt)
    elif cmd == "add":
        numbered = json.loads(num_file.read_text()) if num_file.exists() else {}
        add_lines(Path(sys.argv[2]).read_text().splitlines(), numbered)
    elif cmd == "restamp-check":
        V = load_verdicts()
        stale = [(r.listing_id, r.verdict) for r in V.itertuples() if r.evidence_hash != evidence_hash(r.building_id)]
        print(f"{len(stale)} of {len(V)} verdicts were written against evidence that has since changed")
        for lid, vd in stale[:50]:
            print("  ", vd, lid)


if __name__ == "__main__":
    main()
