"""Reviewed verdicts: the table that says a person (or reviewing agent) has READ the evidence for a unit.

Why this exists (docs/INDEPENDENT_CHECK_2.md): evidence agents wrote their doubts in plain words, and the rules read
only a short list of phrases. No list of phrases will ever be complete. So a unit is shown only when its evidence has
been read and a verdict written:

  data/evidence/review_verdicts.csv
    listing_id, building_id, addr_key, unit,
    verdict        remove | asterisk | disclose | ok
    kind           elevator | floor | dogs | not_available | unverified | wrong_building | lease_term | restricted |
                   coop_condo | other          (blank for ok)

  SEVERAL ROWS PER UNIT (independent check 3, D22): the table is keyed on (listing_id, kind). A unit whose evidence
  shows two things carries two rows, for example 'asterisk | elevator' and 'disclose | lease_term'. One kind per unit
  hid the second issue (98-76 Queens Blvd 2M, Avalon Somerville 022-265, four owner-rented condos).
    what_to_confirm, why (plain words for the page), evidence_quote, evidence_file, reviewed_at,
    evidence_hash  fingerprint of every evidence row of the building when the verdict was written

  remove    -> scripts/rank.py excludes the unit before ranking, with the reason (data/excluded_by_review.csv)
  asterisk  -> an open GATE fact (kinds elevator, dogs, not_available, unverified, wrong_building, restricted): shown
               with an asterisk that says what and why, or dropped as sketchy when that makes two or more open facts
  disclose  -> a condition to know that never removes the unit (kinds lease_term, coop_condo, other, floor): listed
               among the unit's disclosures. Any number of them may sit beside at most one open gate fact.
  ok        -> nothing added; the rules' own asterisks still apply. A verdict never closes a fact the rules leave open.

  Floor and elevator (owner, 2026-11-17): the elevator is judged together with the floor (parsers.floor_elevator_rule).
  'asterisk | elevator' keeps the elevator in doubt: it is an open fact on floor 3+ or an unknown floor, and nothing on
  floor 2, where no elevator is needed. 'remove | elevator' alone is read as "no elevator" (scripts/rank.py): it removes
  a unit on floor 3 or above and leaves a floor-2 apartment. The digest prints the rule's result (floor+elevator=...).

scripts/check_registry.py fails the run when a shown unit has no verdict of ok / asterisk, or when its verdict was
written against older evidence (the fingerprint no longer matches): new evidence must be read before the unit is shown.

Commands
  python3 scripts/verdicts.py pending              shown units with no current verdict (count and list)
  python3 scripts/verdicts.py digest [--out F]     every evidence row for those units, numbered, for the reviewer
  python3 scripts/verdicts.py add FILE             add verdict lines written by the reviewer (format below)
  python3 scripts/verdicts.py restamp-check        list verdicts whose evidence has changed since they were written

Verdict line (fields separated by ' | '; several lines for one unit are allowed, one per kind; the lines given for a
unit in one 'add' replace every earlier row of that unit):
  <listing_id or #n from the digest> | ok
  <id> | asterisk | <gate kind> | <what to confirm> | <why> | <row tag from the digest, e.g. L2, or a literal quote> [| file]
  <id> | disclose | <disclosure kind> | <question> | <why> | <row tag or literal quote> [| file]
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
GATE_KINDS = {"elevator", "dogs", "not_available", "unverified", "wrong_building", "restricted"}     # an asterisk: one open gate fact
DISCLOSURE_KINDS = {"lease_term", "coop_condo", "other", "floor"}                                     # disclose: never removes
SHOWABLE = ("ok", "asterisk", "disclose")
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
    return normalise(V[COLS])


def normalise(V: pd.DataFrame) -> pd.DataFrame:
    """One row per (listing_id, kind), the later row winning. An asterisk on a disclosure kind (the old one-kind table
    wrote 'asterisk | lease_term') is a 'disclose' row: the verdict column then says what the page does (D22)."""
    V = V.copy()
    V.loc[(V.verdict == "asterisk") & V.kind.isin(DISCLOSURE_KINDS), "verdict"] = "disclose"
    V = V.drop_duplicates(["listing_id", "kind"], keep="last")
    # an 'ok' row beside another row of the same unit says nothing more: the other rows are the verdict
    multi = V.groupby("listing_id").verdict.transform("size") > 1
    return V[~(multi & (V.verdict == "ok"))].reset_index(drop=True)


def by_unit(V: pd.DataFrame | None = None) -> dict:
    """listing_id -> {"verdict": remove | asterisk | disclose | ok (the strongest of its rows), "rows": [row dicts],
    "gate": [gate kinds with an asterisk], "disclose": [disclosure kinds], "hashes": {evidence_hash, ...}}."""
    V = load_verdicts() if V is None else V
    out = {}
    order = {"remove": 0, "asterisk": 1, "disclose": 2, "ok": 3}
    for r in V.to_dict("records"):
        d = out.setdefault(r["listing_id"], {"verdict": "ok", "rows": [], "gate": [], "disclose": [], "hashes": set(), "building_id": r["building_id"]})
        d["rows"].append(r)
        d["hashes"].add(r["evidence_hash"])
        if order.get(r["verdict"], 9) < order[d["verdict"]]:
            d["verdict"] = r["verdict"]
        if r["verdict"] == "asterisk":
            d["gate"].append(r["kind"])
        elif r["verdict"] == "disclose":
            d["disclose"].append(r["kind"])
    return out


def shown_units() -> pd.DataFrame:
    R = pd.read_csv(DATA / "ranked_units.csv", dtype=str, keep_default_na=False, low_memory=False)
    return R[R.shown == "True"].copy()


def unreviewed(S: pd.DataFrame | None = None):
    """(listing_id, why) for every shown unit without a current ok / asterisk verdict."""
    S = shown_units() if S is None else S
    V = by_unit()
    out = []
    for lid, b in zip(S.listing_id, S.building_id):
        if lid not in V:
            out.append((lid, "no reviewed verdict: nobody has read this unit's evidence"))
        elif V[lid]["verdict"] not in SHOWABLE:
            out.append((lid, f"verdict is '{V[lid]['verdict']}', so the unit must not be shown"))
        elif V[lid]["hashes"] != {evidence_hash(b)}:
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
                       f"elev={g(r, 'elevator')}({g(r, 'elevator_basis')}) floor={g(r, 'unit_floor')}({g(r, 'unit_floor_basis')}/{g(r, 'unit_floor_label_kind')}) "
                       f"floor+elevator={g(r, 'floor_elevator_status')}/{g(r, 'floor_elevator_code') or '-'} storeys={g(r, 'building_stories')}({g(r, 'building_stories_basis')}) dogs={g(r, 'dogs_allowed')}({g(r, 'dogs_allowed_basis')}) "
                       f"wl={g(r, 'dog_weight_limit_lb')} small={'y' if g(r, 'dog_size_only') else ''} live={g(r, 'live_status')} lease={g(r, 'price_lease_months')} age={g(r, 'listing_age_days')} "
                       f""
                       + (f"notes='{g(r, 'notes')[:200]}'" if CAUTION.search(g(r, "notes")) else ""))
        skipped = {"facts": 0, "items": 0}
        mine = [str(u) for u in grp.unit]
        import parsers
        seen_notes = {}
        for tag, fam, file, text, r in rows:
            text = re.sub(r"\s+", " ", text)
            if fam == "live_check" and not full:
                # another unit's check is printed short; a note repeated word for word is printed once
                if r.notes in seen_notes and len(r.notes) > 80:
                    text = text.split(" | ")[0] + f" | (same note as {seen_notes[r.notes]})"
                seen_notes.setdefault(r.notes, tag)
                if parsers.unit_label_key(r.unit) and not any(parsers.units_match(r.unit, u) or parsers.unit_key(r.unit) == parsers.unit_key(u) for u in mine):
                    text = "(other unit) " + text[:230]
            if fam == "facts" and not full and BORING_FACT.search(r.fact) and not CAUTION.search(text):
                skipped["facts"] += 1
                continue
            if fam == "items" and not full and not ITEM_WORDS.search(text):
                skipped["items"] += 1
                continue
            lim = {"live_check": 560, "confirm": 280, "facts": 220, "items": 160, "nyc": 200}[fam]
            if fam == "confirm" and r.status == "confirmed" and not full:
                lim = 110 if r.fact.lower().startswith("dog_weight") else 170
            out.append(f"  {tag} {file.replace('_batch_', ':').replace('.csv', '')} {text[:lim]}")
        nn = evidence(b)["non_nyc"]
        out.append(f"  (not printed: {skipped['facts']} routine facts, {skipped['items']} review items" + (f", {len(nn)} non-NYC record rows" if len(nn) else "") + ")")
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
        # an empty field is written "| |": keep it as a field (it used to swallow the next one)
        p = [x.strip() for x in re.sub(r" \|(?= \|)", " | ", raw.replace(" | | ", " |  | ")).split(" | ")]
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
        if verdict == "asterisk" and kind in DISCLOSURE_KINDS:
            verdict = "disclose"
        if verdict not in ("ok", "asterisk", "disclose", "remove") or (verdict != "ok" and (kind not in KINDS or not why)) \
                or (verdict == "disclose" and kind not in DISCLOSURE_KINDS):
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
    N_ = pd.DataFrame(new, columns=COLS)
    # the lines given for a unit replace every earlier row of that unit (so a re-review can drop a kind)
    V = normalise(pd.concat([V[~V.listing_id.isin(set(N_.listing_id))], N_], ignore_index=True))
    V.sort_values(["verdict", "building_id", "listing_id", "kind"]).to_csv(VERDICTS, index=False)
    print(f"verdict rows written: {len(new)} for {N_.listing_id.nunique()} units; table now {len(V)} rows for {V.listing_id.nunique()} units {V.verdict.value_counts().to_dict()}")


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
        nf = Path(sys.argv[sys.argv.index("--numbers") + 1]) if "--numbers" in sys.argv else num_file
        numbered = json.loads(nf.read_text()) if nf.exists() else {}
        add_lines(Path(sys.argv[2]).read_text().splitlines(), numbered)
    elif cmd == "restamp-check":
        V = load_verdicts()
        stale = [(r.listing_id, r.verdict) for r in V.itertuples() if r.evidence_hash != evidence_hash(r.building_id)]
        print(f"{len(stale)} of {len(V)} verdict rows were written against evidence that has since changed")
        for lid, vd in stale[:50]:
            print("  ", vd, lid)


if __name__ == "__main__":
    main()
