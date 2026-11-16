"""Ranking v2 and selection. The rules, in one current statement, are in docs/RANKING.md.

Reads only the master tables (build_master.py, all_in.py) and data/lifestyle_groups.csv. In order:
  1. within the all-in cap; neighborhood not cut by the Jamaica safety rule
  2. removed on confirmed facts (no elevator, dogs not allowed, limit under 25 lb, ground floor, gone, stale 6+ months ...)
  3. not a real apartment (floor plan, building-page price, co-living room) -> data/excluded_not_an_apartment.csv
  4. removed by a reviewed verdict; sibling floor rule
  5. open gate facts counted (elevator by parsers.elevator_rule, dogs, listing / availability / eligibility):
     two or more -> "sketchy", excluded; one -> kept with certainty 0.97
  6. evidence exclusions and avoid buildings (avoid.py)
  7. scores: universal value 0-100 (safety 22, building 16, cost 12, car 12, space 12, distance 10, dog 8, daily life 8;
     percentiles across all ranked units, an unknown variable at the 25th percentile), the experience's promise,
     rank score = (0.7 x universal + 0.3 x promise + pool bump) x certainty
  8. selection per neighborhood in rank order: shown = not an avoid building, at most ONE open item (open gate facts
     plus a missing live check), the building has evidence rows; up to 8 per building; no cap per neighborhood
  9. thin neighborhoods: a neighborhood whose shown list is one apartment keeps it only if nothing is open and its
     score is at or above its experience's median (thin_neighborhood_cut)
Candidate and phone-call lists (hood_rank, needs_confirmation.csv, needs_live_check.csv) take two per building.
Outputs: data/ranked_units.csv, data/group_exchange.csv, data/reference/queens_spectrum_definition.csv, the excluded_*.csv files
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "tools"))
from lib import DATA  # noqa: E402
import parsers  # noqa: E402

W = {"safety": 22, "building": 16, "cost": 12, "car": 12, "space": 12, "distance": 10, "dog": 8, "daily": 8}
UNIVERSAL_SHARE, PROMISE_SHARE = 0.7, 0.3
POOL_BUMP, INDOOR_POOL_BUMP = 3, 6
UNKNOWN_PCT = 25
CERTAINTY = {"clean": 1.0, "one_inferred": 0.97}
import os  # noqa: E402
# Measurement switches (docs/REPAIRS_AFTER_INDEPENDENT_CHECK_3.md reports the effect of each rule by itself). They are
# never set in a normal run; scripts/check_registry.py asserts the shipped values on the output.
MAX_PER_BUILDING, SHOWN, CANDIDATES = int(os.environ.get("HH_MAX_PER_BUILDING", 8)), 10 ** 6, 15
NO_ELEVATOR_DOUBT = os.environ.get("HH_NO_ELEVATOR_DOUBT") == "1"
NO_THIN_RULE = os.environ.get("HH_NO_THIN_RULE") == "1"          # measurement only: the shown set before the thin-neighborhood rule
# MAX_PER_BUILDING (owner, 2026-11-16): the page now groups apartments under their building, so up to 8 units of a
# building are shown (it was 2), in rank order inside the building by the same score. CAND_PER_BUILDING keeps the
# candidate / phone-call lists (hood_rank, needs_confirmation, needs_live_check) at two per building, as before.
CAND_PER_BUILDING = 2
# SHOWN (owner, 2026-11-16): the page shows the top three first and the rest on "show more", so the old cap of 10 per
# neighborhood no longer hides a reviewed, showable unit. Order is still by rank; at most MAX_PER_BUILDING per building,
# and each shown unit records how many further showable units its building has (more_in_building).
# GATE facts count toward "two or more open -> not shown". DISCLOSURES never do, and never remove a unit by themselves
# (owner, 2026-11-16): a long-lease price, a cost near the cap with an unknown line, a condo rented by its owner, a
# net-effective rent. A unit may carry any number of disclosures plus at most one open gate fact.
# Owner, 2026-11-16 (later the same day): a floor that is simply not published (unknown, or only read from the unit
# number) is no longer an open gate fact. It is a standing disclosure and tour question, "Floor not published: confirm
# it is above the ground floor". Still excluded: a floor confirmed or stated as ground / 1, a checker's reading that the
# unit is probably or possibly on the ground floor (scripts/avoid.py), and a reviewer's verdict saying so.
GATE_KEYS = {"elevator", "dogs", "availability", "listing", "eligibility"}
DISCLOSURE_KEYS = {"floor", "lease", "cost", "condo", "other"}
ELEVATOR_DOUBT_Q = "Confirm an elevator serves this apartment"
COST_DISCLOSURE = "could pass $3,000"          # replaces "cost near the cap" (owner, 2026-11-16)
COST_DISCLOSURE_TEXT = "Could pass $3,000 once parking and fees are known"
OFFER_DISCLOSURE = "special offer"
OFFER_QUESTION = "Special offer: ask what a normal month costs"
FLOOR_DISCLOSURE = "Floor not published: confirm it is above the ground floor"
CAP, NEAR_CAP = 3000, 100          # D12: within $100 of the cap with an unknown cost line -> asterisk "cost near the cap"
COLOR_DIR = DATA / "enriched_color"


def pct(s, higher_is_better=True):
    """Percentile 0-100 across all units; unknown -> UNKNOWN_PCT."""
    x = pd.to_numeric(s, errors="coerce")
    r = x.rank(pct=True, method="average") * 100
    if not higher_is_better:
        r = 100 - r + (100 / max(x.notna().sum(), 1))
    return r.fillna(UNKNOWN_PCT).clip(0, 100)


def blend(*pairs):
    """Weighted mean of percentile series: blend((series, weight), ...)."""
    tot = sum(w for _, w in pairs)
    return sum(s * w for s, w in pairs) / tot


def parking_rank(t):
    t = str(t).lower()
    if not t or t in ("nan", "unknown", "?", "no_mention", "parking_type_unknown"):
        return np.nan
    if parsers.OFFSITE_PARKING.search(t):
        return 2                       # D10: off-site parking ("2 blocks away, covered") is off the street but not at the building
    if "garage" in t or "gated" in t:
        return 4
    if "covered" in t or "carport" in t:
        return 3
    if "lot" in t or "surface" in t or "off-street" in t or "off street" in t or "assigned" in t:
        return 2
    if "street" in t:
        return 1
    return np.nan


def thin_neighborhood_cut(hood_id, group_key, shown, rank_score, open_items):
    """True for the single shown apartment of a neighborhood that is NOT both well attested (open_items == 0) and
    promising (rank score at or above the median of the shown apartments of its experience). All arguments are
    aligned Series; the medians are taken over `shown` as given (before the rule)."""
    shown = shown.astype(bool)
    n = hood_id[shown].value_counts()
    single = shown & hood_id.map(n).eq(1)
    med = rank_score[shown].groupby(group_key[shown]).median()
    keep = (open_items == 0) & (rank_score >= group_key.map(med))
    return single & ~keep


def in_unit_laundry(laundry_text, in_unit_col):
    """In-unit laundry: the amenities column says yes, or the listing's laundry text says in unit. The old test looked for
    the word "yes" anywhere in the two fields joined, so "laundry: yes" with the amenities column saying on_site_only
    (a shared laundry room) scored as a washer in the apartment, as did "... (not in unit)"."""
    txt, col = laundry_text.fillna("").astype(str).str.lower(), in_unit_col.fillna("").astype(str).str.lower().str.strip()
    yes = col.str.startswith("yes") | txt.str.contains(r"in[ _-]unit|washer(?: and |/|, | & )dryer in")
    no = col.str.contains(r"on_site_only|^no\b") | txt.str.contains(r"not in[ _-]unit|no in[ _-]unit")
    return yes & ~no


SETTLED_BY_PHONE = "confirmed_by_phone"
WINDOW_END = "2026-12-15"
PARKING_DISCLOSURE = "Overnight street parking is restricted here: confirm the building has a space, and its cost"


def needs_parking_disclosure(severity, parking_type, parking_fee) -> bool:
    """Step 3. The town bans or permit-restricts overnight street parking (severity ban / permit / seasonal, from the
    reviewed table) and the unit's parking is not confirmed as included or available at the building: the parking
    type is street, or it is unknown and no fee is known either. A garage, lot or covered space, or an unknown type
    with a stated fee (a space is on offer at a price, or included at $0), needs no disclosure."""
    if str(severity or "").strip() not in ("ban", "permit", "seasonal"):
        return False
    pr = parking_rank(parking_type)
    if pr == 1:
        return True
    if pr == pr and pr is not None and pr >= 2:
        return False
    fee = pd.to_numeric(pd.Series([parking_fee]), errors="coerce").iloc[0]
    return bool(pd.isna(fee))


def color_table(u):
    """places.color() per building, cached on disk; returns a flat frame indexed by addr_key."""
    import places
    COLOR_DIR.mkdir(exist_ok=True)
    rows = []
    for key, g in u.groupby("addr_key"):
        f = COLOR_DIR / (hashlib.sha1(key.encode()).hexdigest()[:14] + ".json")
        if f.exists():
            c = json.loads(f.read_text())
        else:
            c = places.color(float(g.lat.iloc[0]), float(g.lon.iloc[0]))
            f.write_text(json.dumps(c, default=str))
        r = {"addr_key": key}
        for sec, d in c.items():
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, dict) and "value" in v and not k.endswith("examples"):
                        try:
                            r[k] = float(v["value"])
                        except (TypeError, ValueError):
                            pass
        rows.append(r)
    return pd.DataFrame(rows).set_index("addr_key")


def main():
    # Reads ONLY the master tables (scripts/build_master.py + scripts/all_in.py). No side files.
    u = pd.read_csv(DATA / "master_units.csv", low_memory=False, dtype={"zip5": str})
    n_in = len(u)
    u = u[u.cost_gate == "pass"].copy()
    n_cost = n_in - len(u)
    u = u.rename(columns={"parking_fee_monthly": "parking_fee", "pet_rent_monthly": "pet_rent"})
    G = pd.read_csv(DATA / "lifestyle_groups.csv").set_index("hood_id")
    gcols = ["group_key", "group_label", "group_subhead", "safety_cut", "safety_cut_reason", "newcomer_share", "age_25_34_share",
             "detached_house_share", "violent", "property", "motor_vehicle_theft", "violent_vs_jamaica", "property_vs_jamaica",
             "violent_vs_us", "violent_vs_metro", "violent_vs_local"]
    u = u.join(G[gcols], on="hood_id")
    n_cut = int(u.safety_cut.fillna(False).sum())
    u = u[~u.safety_cut.fillna(False)].copy()
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)

    # ---- gate facts re-applied on merged (confirmed-first) values
    wl = pd.to_numeric(u.get("dog_weight_limit_lb"), errors="coerce")
    fl = pd.to_numeric(u.get("unit_floor"), errors="coerce")
    hard = pd.Series("", index=u.index)
    el = s("elevator").str.lower()
    for cond, why in [(el.eq("no"), "no elevator (contradicted in the evidence pass)"),
                      (el.eq("conflicting"), "elevator not established: the sources conflict on which buildings have one"),
                      (s("dogs_allowed").str.lower().eq("no"), "dogs not allowed (confirmed)"),
                      (wl < 25, "dog weight limit under 25 lb"), (fl < 2, "ground-floor unit"),
                      (s("live_status").eq("gone"), "listing gone at live check"),
                      # 4b: a listing page unchanged for more than six months when it was read (build_master.py: listing_stale)
                      (s("listing_stale").eq("remove"), "stale listing: " + s("listing_stale_why")),
                      # a move-in date after the window (only a phone answer can put one here; the listing gate checks the page's date)
                      (s("available_date").str.match(r"\d{4}-\d\d-\d\d") & (s("available_date").str[:10] > WINDOW_END), "available after " + WINDOW_END),
                      # ordinary screening ("income 3x rent", "40x rent") is not income-restricted housing (W10)
                      (s("income_requirement").map(parsers.income_restricted), "income-restricted unit"),
                      (s("building_type").str.contains("senior|62\\+", case=False), "senior housing"),
                      # a harvester's BUILDING_FAILS flag excludes, except one that says only "small dogs only" (owner, 2026-11-15)
                      (s("notes").map(parsers.building_fails_reason).ne(""), "harvest note: BUILDING_FAILS: " + s("notes").map(parsers.building_fails_reason))]:
        hard = pd.Series(np.where(cond & (hard == ""), why, hard), index=u.index)
    u[hard != ""].assign(drop_reason=hard[hard != ""]).to_csv(DATA / "excluded_by_confirmed_facts.csv", index=False)
    n_hard = int((hard != "").sum()); u = u[hard == ""].copy()
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)

    # ---- owner, 2026-11-16: "if there's anything that's not a real apartment and just a floor plan, it shouldn't be in any
    # of this". Only rows that ARE an apartment go on (parsers.listing_kind: from the source's structure, then the label's
    # shape). Floor plans, building-page prices with no unit and co-living rooms stay in the data with the status
    # not_an_apartment (data/excluded_not_an_apartment.csv): never ranked, shown, counted or put on a card.
    # the kind was decided at the listing gate on the listing's own fields (gates.py); recomputed only for a table without it
    kind = s("listing_kind") if "listing_kind" in u and s("listing_kind").ne("").all() else \
        pd.Series([parsers.listing_kind(a_, b_, c_, d_, e_) for a_, b_, c_, d_, e_ in zip(s("unit"), s("detail_level"), s("listing_id"), s("listing_type"), s("building_name"))], index=u.index)
    u["listing_kind"] = kind
    na = kind.ne("unit")
    u[na].assign(status="not_an_apartment", drop_reason=kind[na].map(parsers.NOT_AN_APARTMENT_WHY)).to_csv(DATA / "excluded_not_an_apartment.csv", index=False)
    n_na = int(na.sum()); u = u[~na].copy()
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)

    # ---- reviewed verdicts (independent check 2): data/evidence/review_verdicts.csv holds one row per unit whose
    # evidence a reviewer has read. remove -> excluded here, before ranking, with the reviewer's reason.
    # asterisk -> the unit counts as having that open fact (below). ok -> nothing added. A verdict never closes a fact
    # the rules leave open; scripts/check_registry.py fails the run if a shown unit has no current ok / asterisk verdict.
    # Independent check 3, D22: the table holds SEVERAL rows per unit, one per kind (scripts/verdicts.py). Gate kinds
    # (verdict asterisk) each count as an open gate fact; disclosure kinds (verdict disclose) are all listed.
    import verdicts as VD
    VU = VD.by_unit()                    # reads data/evidence/review_verdicts.csv
    def vd(c):
        if c == "verdict":
            return u.listing_id.map(lambda l: VU[l]["verdict"] if l in VU else "")
        if c == "kind":
            return u.listing_id.map(lambda l: ";".join(r["kind"] for r in VU[l]["rows"] if r["kind"]) if l in VU else "")
        return u.listing_id.map(lambda l: next((r[c] for r in VU[l]["rows"] if r["verdict"] == VU[l]["verdict"]), "") if l in VU else "")
    rm = vd("verdict").eq("remove")
    u[rm].assign(drop_reason="reviewed: " + vd("why")[rm], review_kind=u.listing_id[rm].map(lambda l: ";".join(r["kind"] for r in VU[l]["rows"] if r["verdict"] == "remove"))) \
        .to_csv(DATA / "excluded_by_review.csv", index=False)
    n_rev = int(rm.sum()); u = u[~rm].copy()
    # D2 (Halstead Parsippany 2182): SIBLING CONSISTENCY. Where a reviewer removed units of a building because "the unit
    # number reads as floor 1", every other unit of that building whose label has the same shape and the same digit in
    # the place the reviewer read as the floor is removed too. The pattern is taken from the removed labels themselves.
    removed_floor = {}
    for l, d in VU.items():
        for r in d["rows"]:
            if r["verdict"] == "remove" and r["kind"] == "floor" and parsers.unit_label_key(r["unit"]) \
                    and __import__("re").search(r"first[- ]floor|floor 1\b|ground", r["why"], __import__("re").I):
                removed_floor.setdefault(r["building_id"], []).append(r["unit"])
    sib = pd.Series([b in removed_floor and parsers.reads_as_ground_like_siblings(un, removed_floor[b]) for b, un in zip(u.building_id, u.unit.fillna("").astype(str))], index=u.index)
    u[sib].assign(drop_reason=["sibling rule: the unit number has the same shape as units " + ", ".join(sorted(removed_floor[b])[:5])
                               + " of this building, which a reviewer removed because their numbers read as first-floor units" for b in u.building_id[sib]],
                  review_kind="floor").to_csv(DATA / "excluded_by_sibling_rule.csv", index=False)
    n_sib = int(sib.sum()); u = u[~sib].copy()
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)
    vhas = lambda *kinds: u.listing_id.map(lambda l: l in VU and any(r["kind"] in kinds and r["verdict"] in ("asterisk", "disclose") for r in VU[l]["rows"])).astype(bool)

    # ---- listing confidence
    age = pd.to_numeric(u.get("listing_age_days"), errors="coerce")
    med = u.groupby("hood_id").all_in.transform("median")
    reasons = pd.Series("", index=u.index)
    for cond, why in [(age >= 60, "listing 60+ days old"), ((s("unit") == "") & (s("building_name") == ""), "no unit or building named"),
                      (s("notes").str.contains("listhub|propertyware", case=False), "thin syndicated feed"),
                      (u.all_in < 0.6 * med, "price far below the neighborhood"),
                      (s("live_notes").str.contains("not an open-market|far under market|not genuine|scam|listing looks stale|duplicate candidate|out-of-state phone", case=False), "live check judged the listing doubtful")]:
        reasons = pd.Series(np.where(cond, reasons + why + "; ", reasons), index=u.index)
    # Open gate facts (plan Part 5; independent check W1-W3, W20). A unit with one is ranked but held back with the
    # question to ask; with two or more it is sketchy.
    #  elevator  anything not confirmed, stated on a page or in an official record
    #  floor     confirmed or stated on the page is settled. A floor read from a simple unit label ("4F", "305") that
    #            comes out at 3 or higher is accepted with a note and a tour question; any other inferred floor
    #            (2, or from a label with a separator, a building prefix or four digits) and an unknown floor are open
    #  dogs      a policy that conflicts between two aggregators is open. A size word ("small dogs", or "small" in a
    #            size field) with no pound figure PASSES (owner, 2026-11-15: her dog is at most 25 lb): the unit can be
    #            shown, with the note "page says small dogs; no weight number" and a tour question
    wl = wl.reindex(u.index); fl = fl.reindex(u.index)
    # elevator: no page or record states one (base), or the evidence pass looked and could not confirm it (D2, D7, D9),
    # or the reviewer's verdict says it is not established for this building
    # a fact answered on the phone is settled: neither an older evidence row nor an earlier reviewer's asterisk reopens it
    phone_e, phone_d = s("elevator_basis").eq(SETTLED_BY_PHONE), s("dogs_allowed_basis").eq(SETTLED_BY_PHONE)
    phone_av = s("call_available").ne("")
    # ONE ELEVATOR RULE (parsers.elevator_rule, the truth table the listing gate uses): established -> settled; open ->
    # one open gate fact; unknown -> not shown. A reviewer's elevator asterisk and the doubt table open it; a phone
    # answer settles it. owner, 2026-11-16: a building in the reviewed doubt table, or a tag-only elevator in a complex
    # the data shows to be multi-building garden-style (build_master.py), is "confirm an elevator serves this apartment".
    v_el = vhas("elevator")
    cols_e = ["elevator", "elevator_basis", "elevator_height_basis", "pluto_floors", "pluto_lot_ok", "elevator_evidence_open", "elevator_doubt",
              "building_floors", "building_floors_basis", "unit_floor", "unit_floor_basis", "building_type", "building_type_basis"]
    E_ = pd.DataFrame({c: s(c) for c in cols_e})
    E_["unit_floor"] = E_.unit_floor.str.replace(r"\.0$", "", regex=True)
    res_e = [parsers.elevator_rule_master(lambda c, r=r: r[c], reviewer_open=bool(v), use_doubt=not NO_ELEVATOR_DOUBT) for r, v in zip(E_.to_dict("records"), v_el)]
    st_e = pd.Series([x[0] for x in res_e], index=u.index)
    bs_e = pd.Series([x[1] for x in res_e], index=u.index)
    u["elevator_rule_status"], u["elevator_rule_basis"] = st_e, bs_e
    base_e = st_e.isin(["unknown", "no"]) | (st_e.eq("open") & bs_e.str.startswith("inferred"))    # no page or record states one
    doubt_e = s("elevator_doubt").ne("") & ~phone_e & (not NO_ELEVATOR_DOUBT)
    inf_e = st_e.ne("established")
    fb, fk = s("unit_floor_basis"), s("unit_floor_label_kind")
    floor_settled = fb.isin(["confirmed", "stated", SETTLED_BY_PHONE])
    floor_from_label_ok = fb.eq("inferred") & fk.eq("simple") & (fl >= 3)
    inf_f = ~floor_settled | vhas("floor")          # not published: unknown, or only read from the unit number
    u["floor_basis_note"] = np.where(floor_from_label_ok, "read from the unit number", "")
    # dogs: allowed must be stated or confirmed, and dogs must be NAMED as allowed (D2, D3): an unconfirmed evidence
    # row, "pets upon approval", "case by case" or small pets with dogs unnamed leave the fact open
    base_d = s("dogs_allowed").str.lower().ne("yes")
    # A dog policy that CONFLICTS between sources is ONE open gate fact (dogs), not a removal and not "sketchy" (owner's
    # latest rule; the harvester's "CONFLICT ..." note used to drop the unit as sketchy). It is settled where the
    # building's own or its manager's page, or a phone call, says dogs are allowed. Only a clear "no dogs" on the
    # building's own page removes (dogs_allowed = no, above). A conflict about the SIZE of dog only ("Size allowed:
    # Small") is not about whether dogs are allowed: it passes like "small dogs", with the weight question.
    note_conflict = s("notes").str.contains("CONFLICT")
    size_conflict = s("notes").str.contains("CONFLICT on dog size")
    dog_conflict_open = note_conflict & ~size_conflict & ~s("dogs_allowed_basis").isin([SETTLED_BY_PHONE, "confirmed", "community_page"])
    dog_open = base_d | ((s("dogs_evidence_open").ne("") | vhas("dogs") | dog_conflict_open) & ~phone_d)
    no_limit = s("dog_weight_limit_lb").str.lower().eq("no limit")
    dog_small = (s("dog_size_only").ne("") | size_conflict) & wl.isna() & ~no_limit
    # 4a: "weight restrictions apply" / a weight limit with no number passes like "small dogs", with the same tour question
    dog_wl_unstated = s("dog_weight_unstated").ne("") & wl.isna() & ~no_limit & ~dog_small
    # An elevator "inferred from height" counts as ONE open fact only when a page or record gives a real height (the rule's
    # status "open"). Where nothing but a unit label ("36D", "801") suggests the height, the status is "unknown": not shown.
    weak_e = st_e.isin(["unknown", "no"])
    # ---- the other things a renter must not find out later (independent check 2)
    #  lease      the listed price belongs to a lease longer than 13 months, or is only "the lowest over the lease terms" (D8)
    #  cost       all-in within $100 of the cap while pet rent, parking or required fees is unknown and counted as $0 (D12)
    #  listing    an evidence warning about the listing itself (wrong address, generic text, owner on record), D6
    #  availability  the row is a floor plan, not a named unit: no unit, floor or date could be checked (D1)
    #  plus whatever a reviewer's asterisk verdict names (availability, listing, eligibility, condo, other)
    lm = pd.to_numeric(s("price_lease_months"), errors="coerce")
    p12 = pd.to_numeric(s("price_12_month"), errors="coerce")
    # D9 (The Riverhouse): the offer itself says the advertised price is for a longer lease ("3 months free on 18 month
    # leases", rent_terms lease_months) although the price field gives no term
    olm = pd.to_numeric(s("rent_lease_months"), errors="coerce").where(s("rent_basis_kind").eq("net_effective"))
    lm = lm.where(lm.notna(), olm.where(olm > 13))
    lease_open = (lm > 13) | s("price_lowest_of_terms").eq("yes") | vhas("lease_term")
    # owner, 2026-11-16: within the cap on what is known, over it once the unknown parking and fee lines take their medians
    likely = pd.to_numeric(s("all_in_likely"), errors="coerce")
    cost_open = (u.all_in <= CAP) & (likely > CAP)
    # D26: a floor-plan row (parsers.listing_kind, from the source's structure and the label's shape), not a named apartment
    # (floor-plan rows were removed above as not_an_apartment; nothing here is a plan any more)
    plan_only = pd.Series(False, index=u.index)
    avail_open = (plan_only | vhas("not_available")) & ~phone_av
    # 4b: a page last changed more than 60 days before it was read (no second site), or an availability date over six
    # months old, is the open item "listing" by rule; it is not counted twice when a reviewer already wrote it up as availability
    stale_open = s("listing_stale").eq("open") & ~vhas("not_available") & ~phone_av
    # D1 (98-76 Queens Blvd 2M): a checker's note that the price itself must be verified ("far below the area's other listings")
    price_open = s("live_notes").map(parsers.price_doubt) & ~phone_av
    listing_open = (s("listing_warning").ne("") | vhas("unverified", "wrong_building") | stale_open | price_open) & ~(phone_av & s("listing_warning").eq(""))
    # eligibility: a reviewer's finding, or a listing site's income-restricted tag the manager's own page does not bear out
    # D8: a condo by RULE, not only by verdict: the city classes the listing's own lot as a condominium (class R*) and the
    # row is not a managed rental building, or the listing itself is typed condo / co-op
    condo_rule = (s("pluto_class").str.upper().str.startswith("R") & s("pluto_lot_ok").eq("yes") & s("listing_type").ne("managed_building")) | s("listing_type").str.contains("condo", case=False)
    elig_open, condo_open, other_open = vhas("restricted") | s("eligibility_open").ne(""), vhas("coop_condo") | condo_rule, vhas("other")
    unknown_lines = s("all_in_unknown_lines").str.replace("building fees (part)", "some required fees", regex=False).str.replace("building fees", "required fees").str.replace("parking fee", "parking") \
        .map(lambda t: " / ".join(x for x in t.split("; ") if x in ("pet rent", "parking", "required fees", "some required fees")))
    lease_why = np.where(lm > 13, "The listed price is for a " + lm.fillna(0).astype(int).astype(str) + "-month lease."
                         + pd.Series(np.where(p12.notna(), " The 12-month price is $" + p12.fillna(0).astype(int).astype(str) + ", which is what the cost here uses.", " The 12-month price is not published."), index=u.index),
                         np.where(s("price_lowest_of_terms").eq("yes"), "The listed price is the lowest over the lease terms offered; the term it belongs to and the 12-month price are not published.",
                                  "The listing's own terms tie this price to a lease longer than 13 months."))
    OPEN = [  # key, flag, label on the page, why, question
        ("elevator", inf_e, "elevator",
         np.where(base_e, "No page states an elevator; the building's height suggests one.",
                  np.where(s("elevator_evidence_open").ne(""), "The evidence pass could not confirm an elevator for this building: " + s("elevator_evidence_open").str.replace("the evidence pass could not confirm it: ", "", regex=False).str[:140],
                           "An elevator is named for this property, but it is a low-rise or multi-building complex, so that does not say an elevator serves this apartment: "
                           + s("elevator_doubt").str.replace(r"^(?:reviewed table|rule): ", "", regex=True).str[:220])),
         np.where(doubt_e & ~base_e & s("elevator_evidence_open").eq(""), ELEVATOR_DOUBT_Q + " (this building of the complex, this floor)", "Does this building have an elevator?")),
        ("floor", inf_f, "floor", None, None),
        ("dogs", dog_open, "dogs allowed",
         np.where(base_d, "Two listing sites disagree on whether dogs are allowed, and the building's own page does not settle it.",
                  np.where(s("dogs_evidence_open").ne(""), "Dogs are not confirmed as allowed here: " + s("dogs_evidence_open").str.replace("the evidence pass could not confirm it: ", "", regex=False).str[:140],
                           "Two sources disagree on whether dogs are allowed here, and no page of the building's own settles it.")),
         "Are dogs allowed? (dogs must be named as allowed, not 'pets on approval')"),
        ("lease", lease_open, "lease term", lease_why, "What is the rent on a 12-month lease?"),
        ("cost", cost_open, COST_DISCLOSURE, COST_DISCLOSURE_TEXT + ": $" + u.all_in.round().astype(int).astype(str) + " a month on what is published; about $"
         + likely.fillna(0).round().astype(int).astype(str) + " if " + unknown_lines.str.replace(" / ", " and ") + " cost what they typically do (" + s("all_in_likely_note").str[:260] + "). Not published for this building.",
         "What do parking and the required monthly fees cost here?"),
        ("availability", avail_open, "availability", "This is a floor-plan price, not a named unit: no unit, floor or date could be checked.", "Which unit is available at this price, on which floor, and from when?"),
        ("listing", listing_open, "listing", np.where(s("listing_warning").ne(""), "The evidence pass raised a warning about this listing: " + s("listing_warning").str[:160],
                                                      np.where(price_open, "The evidence pass flagged the price: " + s("live_notes").str[:200], "The listing may be stale: " + s("listing_stale_why") + ".")),
         np.where(s("listing_warning").ne(""), "Is this listing for this building, and is it genuine?",
                  np.where(price_open, "Is this price real? Verify it by phone before touring.", "Is this unit still available? The listing page has not changed in over two months."))),
        ("eligibility", elig_open, "eligibility", np.where(s("eligibility_open").ne(""), "Eligibility is not settled: " + s("eligibility_open").str[:200], ""),
         "Is this unit open to any renter, or is there an income limit?"),
        ("condo", condo_open, "condo rules", np.where(s("listing_type").str.contains("condo", case=False), "The listing is typed as a condo or co-op unit, rented out by its owner rather than by a leasing office.",
                                                      "The city records this building as a condominium (building class " + s("pluto_class") + "): the unit is rented out by its owner, not by a leasing office."),
         "What are the condominium's rules for renting this unit (application, fees, pets)?"),
        ("other", other_open, "other", "", ""),
    ]
    KIND_KEY = {"elevator": "elevator", "floor": "floor", "dogs": "dogs", "lease_term": "lease", "not_available": "availability", "unverified": "listing",
                "wrong_building": "listing", "restricted": "eligibility", "coop_condo": "condo", "other": "other"}
    n_inf = weak_e.astype(int)
    for key_, flag, *_rest in OPEN:
        if key_ in GATE_KEYS:
            n_inf = n_inf + flag.astype(int)
    u["dog_size_note"] = np.where(dog_small, parsers.SMALL_DOG_NOTE, "")
    floor_q = np.where(fb.eq("inferred"), "Which floor is the unit on? (" + s("unit_floor").str.replace(r"\.0$", "", regex=True) + " is only a guess from the unit number " + s("unit") + "); ",
                       "Which floor is the unit on?; ")
    fnum = s("unit_floor").str.replace(r"\.0$", "", regex=True)
    floor_why = np.where(inf_f & fb.eq("inferred"), "No page states the floor; " + fnum + " is only read from the unit number " + s("unit") + ".",
                         "The listing does not give the floor, and the unit number does not show it.")
    # the reviewer's own words per key: {key: (why, question)} for each unit
    v_text = [{KIND_KEY.get(r["kind"], ""): (r["why"], r["what_to_confirm"]) for r in VU[l]["rows"] if r["verdict"] in ("asterisk", "disclose")} if l in VU else {} for l in u.listing_id]
    what_l, why_l, q_l, keys_l, disc_l = [], [], [], [], []
    net_eff = s("rent_basis_kind").eq("net_effective").values
    offer_txt = s("rent_offer_text").str[:160].values
    special = (s("rent_offer_kind").eq("special_offer") & ~s("rent_basis_kind").eq("net_effective")).values
    offer_type = s("rent_offer_type").values
    cols_ = [(k, f.values, lab, np.asarray(floor_why if k == "floor" else (w if not isinstance(w, str) else np.full(len(u), w, dtype=object))),
              (None if k == "floor" else (q if isinstance(q, str) else np.asarray(q)))) for k, f, lab, w, q in OPEN]
    # step 3: overnight street-parking rule of the town, where the unit's parking is not confirmed at the building
    park_d = np.array([needs_parking_disclosure(sv, pt, pf) for sv, pt, pf in zip(s("street_overnight_severity"), s("parking_type"), s("parking_fee"))], dtype=bool)
    po_town, po_rule, po_url, po_sev = s("street_overnight_town").values, s("street_overnight_rule").values, s("street_overnight_url").values, s("street_overnight_severity").values
    wl_un, wl_txt = dog_wl_unstated.values, s("dog_weight_unstated").str.replace(r"^yes: ", "", regex=True).str.split(" || ", regex=False).str[0].str[:140].values
    fq = pd.Series(floor_q, index=u.index).str.rstrip("; ").values
    for i in range(len(u)):
        whats, whys, qs, keys, disc = [], [], [], [], []
        for k, f, lab, w, q in cols_:
            if f[i]:
                rv = v_text[i].get(k)
                why_ = rv[0] if rv and rv[0] else str(w[i])
                q_ = rv[1] if rv and rv[1] else (fq[i] if k == "floor" else (q if isinstance(q, str) else str(q[i])))
                if k in DISCLOSURE_KEYS:
                    is_condo = k == "condo" or (k == "other" and "condo" in why_.lower())
                    disc.append({"what": "condo rented by its owner" if is_condo else ("floor not published" if k == "floor" else ("something else to know" if k == "other" else lab)),
                                 "why": why_, "question": FLOOR_DISCLOSURE if k == "floor" else (q_ or "")})
                    continue
                keys.append(k); whats.append(lab); whys.append(why_); qs.append(q_)
        if net_eff[i]:
            disc.append({"what": "net-effective rent", "why": "The rent shown is the average after a special offer, not the monthly payment." + (" Offer: " + offer_txt[i] if offer_txt[i] else ""),
                         "question": "What is the full monthly rent, and when is the first full payment due?"})
        elif special[i]:
            # D5 / D16: an offer the page does not tie to the listed price is disclosed as an offer, never as "net-effective"
            kind_txt = {"dollar_credit": "a one-time credit or gift", "look_and_lease": "a one-time credit for applying quickly", "months_free": "free rent",
                        "weeks_free": "free rent"}.get(offer_type[i], "a special")
            disc.append({"what": OFFER_DISCLOSURE, "why": "The listing advertises " + kind_txt + ". The page does not say the price shown already includes it, so the price is treated as the normal monthly rent."
                         + (" Offer: " + offer_txt[i] if offer_txt[i] else ""), "question": OFFER_QUESTION})
        if wl_un[i]:
            disc.append({"what": "dog weight limit not published", "why": "The page says a weight limit or weight restrictions apply and gives no number: \"" + wl_txt[i] + "\".",
                         "question": parsers.DOG_WEIGHT_QUESTION})
        if park_d[i]:
            disc.append({"what": "overnight street parking", "why": f"{po_town[i]}: {po_rule[i]}", "question": PARKING_DISCLOSURE, "url": po_url[i], "severity": po_sev[i]})
        qs += [d["question"] for d in disc]
        disc_l.append(json.dumps(disc) if disc else "")
        what_l.append("; ".join(whats)); why_l.append(" ".join(whys)); q_l.append("; ".join(x for x in qs if x)); keys_l.append(";".join(keys))
    u["open_keys"] = keys_l
    u["disclosures"] = disc_l
    u["to_confirm"] = [q + "; " if q else "" for q in q_l]
    u["tour_confirm"] = (pd.Series(np.where(inf_f, FLOOR_DISCLOSURE + "; ", ""), index=u.index)
                         + pd.Series(np.where(dog_small | dog_wl_unstated, parsers.DOG_WEIGHT_QUESTION + "; ", ""), index=u.index)).str.rstrip("; ")
    u["phone_settled"] = (pd.Series(np.where(phone_e, "elevator;", ""), index=u.index) + np.where(phone_d, "dogs allowed;", "") + np.where(phone_av, "availability;listing;", "")).str.rstrip(";")
    # the one open fact, in plain words, for the asterisk on the page (owner, 2026-11-15: a unit with exactly one open
    # gate fact is shown with an asterisk instead of being held back)
    u["confirm_what"], u["confirm_why"] = what_l, why_l
    u["review_verdict"], u["review_kind"] = vd("verdict"), vd("kind")
    u["unknown_cost_lines"] = unknown_lines.str.replace(" / ", "; ")
    u["open_gate_facts"] = n_inf
    u["confidence"] = np.where(reasons != "", "sketchy", np.where(n_inf == 0, "clean", np.where(n_inf == 1, "one_inferred", "sketchy")))
    u["sketchy_reason"] = np.where(reasons != "", reasons, np.where(weak_e, "elevator not stated on any page and the building's height is not known (it was guessed from the unit label)", np.where(n_inf >= 2, "two or more things unconfirmed: " + u.confirm_what, "")))
    u[u.confidence == "sketchy"].to_csv(DATA / "excluded_sketchy.csv", index=False)
    n_sk = int((u.confidence == "sketchy").sum())
    u = u[u.confidence != "sketchy"].copy()
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)

    # ---- evidence rules (scripts/avoid.py writes these from the evidence families)
    xf, af = DATA / "unit_exclusions.csv", DATA / "avoid_buildings.csv"
    xw = pd.read_csv(DATA / "reference" / "building_crosswalk.csv", dtype=str).set_index("addr_key").building_id
    n_ex = 0
    if xf.exists():
        # exclusions apply to the building (every address key of it) and match unit labels the way the master does:
        # "5106" excludes "005-5106" (independent check W17, W18)
        X = pd.read_csv(xf, dtype=str, keep_default_na=False)
        X["building_id"] = X.addr_key.map(xw).fillna("")
        if "listing_id" not in X:
            X["listing_id"] = ""
        by_lid = set(X[X.listing_id != ""].listing_id)                      # a row that names one listing excludes only it
        X = X[X.listing_id == ""]
        whole_k, whole_b = set(X[X.unit == ""].addr_key), set(X[(X.unit == "") & (X.building_id != "")].building_id)
        pairs = {}
        for r in X[X.unit != ""].itertuples():
            for uu in r.unit.split(";"):
                pairs.setdefault(r.building_id or r.addr_key, []).append(uu.strip())
        hit = [any(parsers.units_match(x, str(un)) for x in pairs.get(b_, []) + pairs.get(a_, [])) for a_, b_, un in zip(u.addr_key, u.building_id, u.unit)]
        bad = u.addr_key.isin(whole_k) | u.building_id.isin(whole_b) | pd.Series(hit, index=u.index) | u.listing_id.isin(by_lid)
        u[bad].assign(drop_reason="evidence pass").to_csv(DATA / "excluded_by_evidence.csv", index=False)
        n_ex = int(bad.sum()); u = u[~bad].copy()
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)
    # a live check counts only when the evidence pass saw the listing itself: live, or live at a changed price (W12)
    u["live_ok"] = s("live_status").isin(["live", "changed"])
    if af.exists():
        AV = pd.read_csv(af, dtype=str, keep_default_na=False)
        AV["building_id"] = AV.addr_key.map(xw)
        AV = AV.dropna(subset=["building_id"]).sort_values("avoid", ascending=False).drop_duplicates("building_id").set_index("building_id")
        for c in ["avoid", "reasons", "pause_notes", "evidence_json", "positive_json"]:
            u["ev_" + c] = u.building_id.map(AV[c]).fillna("")
        u["evidence_checked"] = u.building_id.isin(AV.index) & u.live_ok
    else:
        u["ev_avoid"], u["evidence_checked"] = "", False
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)

    # amenity tests (scripts/parsers.py): negatives and near-misses are not a yes (W14): "Pool table", "none listed",
    # "no doorman stated"; a virtual doorman is controlled access, not a doorman
    AM = {"pool": "pool", "doorman_or_concierge": "doorman", "controlled_access": "controlled_access", "gym": "gym",
          "package_room": "package_room", "in_unit_laundry": "in_unit_laundry", "roof_deck_or_outdoor_space": "outdoor_space",
          "balcony_some_units": "balconies", "coworking_or_lounge": "lounge_or_coworking", "gated_or_garage_parking": "parking_type",
          "year_built": "year_built", "dog_amenities": "dog_amenities", "elevator_stated": "elevator"}
    a = lambda col: s(AM.get(col, col)).str.lower()
    has = lambda col: a(col).map(parsers.amenity_yes).astype(bool)
    C = color_table(u)
    u = u.join(C, on="addr_key", rsuffix="_color")
    n = lambda c: pd.to_numeric(u[c], errors="coerce") if c in u else pd.Series(np.nan, index=u.index)

    u["pool_text"] = s("pool")
    u["pool"] = a("pool").map(parsers.pool_state)
    pr = u.parking_type.map(parking_rank).fillna(a("gated_or_garage_parking").map(parking_rank))
    u["parking_rank"] = pr
    doorman = a("doorman_or_concierge").map(parsers.doorman_state)
    u["doorman_text"] = s("doorman")
    u["doorman"] = doorman
    has_doorman, doorman24 = doorman.ne(""), doorman.eq("24h")
    doorman_known = s("doorman_text").str.strip().ne("")
    controlled = has("controlled_access") | s("doorman_text").map(parsers.virtual_doorman).astype(bool)
    laundry = (s("laundry") + " " + a("in_unit_laundry")).str.lower()
    near_car = n("near_veh_theft_24m") + n("near_theft_from_veh_24m").fillna(0)

    # points for building features (unknown = a quarter of the points)
    def pts(yes, known, w):
        return np.where(yes, w, np.where(known, 0.0, 0.25 * w))
    security = (pts(doorman24, doorman_known, 3) + pts(has_doorman & ~doorman24, doorman_known, 2)
                + pts(controlled, False, 2.5) + pts(has("package_room"), False, 1))
    comfort = (pts(in_unit_laundry(s("laundry"), s("in_unit_laundry")), laundry.str.strip().ne(""), 2.5)
               + pts(has("gym"), False, 1) + pts(has("roof_deck_or_outdoor_space"), False, 1) + pts(has("balcony_some_units"), False, 0.5)
               + pts(has("coworking_or_lounge"), False, 1.5) + pts(s("elevator_basis").isin([SETTLED_BY_PHONE, "confirmed", "amenities_page", "official_record", "stated"]), True, 1))
    year = pd.to_numeric(a("year_built").replace("", np.nan), errors="coerce").fillna(n("pluto_year"))
    u["building_security_pts"], u["building_comfort_pts"] = security, comfort

    # ---- parts
    # police-located violent crime near the building and its evening share (NYC only; unknown elsewhere)
    near_viol = n("near250_robbery_24m") + n("near250_felony_assault_24m").fillna(0) + n("near250_burglary_24m").fillna(0)
    eve = (n("near250_robbery_24m") * n("near250_robbery_evening_share").fillna(0)
           + n("near250_felony_assault_24m").fillna(0) * n("near250_felony_assault_evening_share").fillna(0))
    # three-year direction of the area's violent rate (falling is better)
    trend = n("agency_violent_per_1000_2025").fillna(n("agency_violent_per_1000_2024")) - n("agency_violent_per_1000_2023").fillna(n("agency_violent_per_1000_2022"))
    u["near_violent_250m_24m"], u["near_violent_evening_250m_24m"], u["violent_trend"] = near_viol, eve.round(1), trend
    u["p_safety"] = blend((pct(u.violent, False), 28), (pct(u.property, False), 12), (pct(u.motor_vehicle_theft, False), 10),
                          (pct(near_viol, False), 10), (pct(eve, False), 8), (pct(near_car, False), 10), (pct(trend, False), 4),
                          (pct(pd.Series(security, index=u.index)), 18))
    u["p_building"] = blend((pct(pd.Series(security, index=u.index)), 40), (pct(pd.Series(comfort, index=u.index)), 45), (pct(year), 15))
    lines_known = n("all_in_stated_line_count")     # cost lines stated on a page rather than estimated or unknown
    u["p_cost"] = blend((pct(u.all_in, False), 85), (pct(lines_known), 15))
    u["p_car"] = blend((pct(pr), 50), (pct(u.motor_vehicle_theft, False), 15), (pct(near_car, False), 15),
                       (pct(n("parking_fee"), False), 10), (pct(n("surface_parking_ha_within_800m")), 10))
    one_bed = (pd.to_numeric(u.beds, errors="coerce") >= 1).astype(float) * 100
    u["p_space"] = blend((pct(u.sqft), 75), (one_bed, 25))
    def clock(t):   # "23:41" or "24:15" -> minutes after noon; later last train home is better
        m = __import__("re").match(r"(\d{1,2}):(\d{2})", str(t))
        return (int(m.group(1)) * 60 + int(m.group(2)) - 720) if m else np.nan
    last_train = u.get("transit_last_sat_departure_from_jamaica", pd.Series("", index=u.index)).map(clock)
    # a toll counts only when every crossing on the route has a rate; an incomplete sum scores as unknown, never as $0
    toll = pd.Series([parsers.toll_known(v_, c_) for v_, c_ in zip(u.toll_rt_ezpass, u.toll_complete)], index=u.index, dtype=float)
    u["toll_rt_known"] = toll
    u["p_distance"] = blend((pct(u.drive_min_to, False), 50), (pct(u.transit_sat_median, False), 20), (pct(toll, False), 12),
                            (pct(n("transit_sat_transfers"), False), 8), (pct(last_train), 5), (pct(n("transit_sun_return_median"), False), 5))
    dog_small = dog_small.reindex(u.index).fillna(False)
    dogam = has("dog_amenities")
    # a confirmed "no limit" is the best weight policy, not an unknown (W16)
    weight_ok = (pd.to_numeric(u.get("dog_weight_limit_lb"), errors="coerce") >= 25) | s("dog_weight_limit_lb").str.lower().eq("no limit")
    u["p_dog"] = blend((pct(u.park_walk_min, False), 25), (pct(u.park_ha_800m), 15), (pct(u.dog_park_m, False), 15),
                       (pct(n("woods_ha_within_800m")), 5), (pct(n("vet_count_1600m")), 10), (pct(n("pet_count_1600m")), 5),
                       (pd.Series(np.where(dogam, 100, UNKNOWN_PCT), index=u.index), 10), (pct(u.pet_rent, False), 5),
                       (pd.Series(np.where(weight_ok, 100, UNKNOWN_PCT), index=u.index), 10))
    u["p_daily"] = blend((pct(u.cafes_800m), 20), (pct(n("supermarket_m_c") if "supermarket_m_c" in u else n("supermarket_m"), False), 25),
                         (pct(n("gym_count_800m")), 15), (pct(n("library_count_1600m")), 5), (pct(n("market_count_1600m")), 10),
                         (pct(n("convenience_count_800m")), 10), (pct(u.motorway_m), 15))
    u["universal"] = sum(u[f"p_{k}"] * w for k, w in W.items()) / 100

    # ---- the year's promise (five to seven signature variables each)
    P = {
        "pre_car": blend((pct(u.restaurants_800m), 20), (pct(u.bars_800m), 15), (pct(u.cafes_800m), 15), (pct(n("shop_any_count_800m")), 15),
                         (pct(n("intersections_within_800m")), 15), (pct(n("cinema_theatre_count_1600m")), 10), (pct(n("bookshop_count_1600m")), 10)),
        "settled": blend((pct(n("convenience_count_800m")), 20), (pct(n("hair_beauty_count_800m")), 15), (pct(u.restaurants_800m), 15),
                         (pct(n("laundry_count_800m")), 10), (pct(n("library_count_1600m")), 10), (pct(u.transit_sat_median, False), 20),
                         (pct(n("playground_count_800m")), 10)),
        "new_water": blend((pct(pd.Series(comfort + security, index=u.index)), 25), (pct(u.open_water_m, False), 20), (pct(u.newcomer_share), 15),
                           (pct(u.age_25_34_share), 15), (pct(year), 10), (pct(n("gym_count_800m")), 5), (pct(u.bars_1600m), 10)),
        "middle": blend((pct(u.restaurants_800m), 25), (pct(n("train_station_m"), False), 20), (pct(n("cinema_theatre_count_1600m")), 15),
                        (pct(n("shop_any_count_800m")), 15), (pct(n("market_count_1600m")), 10), (pct(u.bars_1600m), 15)),
        "space": blend((pct(n("sqft") / n("all_in")), 40), (one_bed, 15), (pct(u.park_ha_800m), 15), (pct(pr), 15), (pct(n("woods_ha_within_800m")), 15)),
        "enclave": blend((pct(u.violent, False), 25), (pct(u.property, False), 15), (pct(u.motorway_m), 20), (pct(pr), 15),
                         (pct(n("woods_ha_within_800m")), 10), (pct(u.detached_house_share), 15)),
    }
    u["promise"] = 0.0
    for k, sc in P.items():
        m = u.group_key == k
        u.loc[m, "promise"] = sc[m]
    u["pool_bump"] = u.pool.map({"indoor": INDOOR_POOL_BUMP, "pool": POOL_BUMP}).fillna(0)
    u["certainty"] = u.confidence.map(CERTAINTY)
    u["rank_score"] = ((UNIVERSAL_SHARE * u.universal + PROMISE_SHARE * u.promise + u.pool_bump) * u.certainty).round(1)
    u = u.copy()

    # ---- standings: within the year, and against everything
    for k in list(W) + ["universal", "rank_score"]:
        c = f"p_{k}" if k in W else k
        u[f"{k}_in_year"] = u.groupby("group_key")[c].rank(pct=True).mul(100).round(0)
        u[f"{k}_overall"] = u[c].rank(pct=True).mul(100).round(0)

    # ---- selection per neighborhood
    parts = [f"p_{k}" for k in W]
    u["dominated"] = False
    for hid, g in u.groupby("hood_id"):
        v = g[parts].values
        for i in range(len(g)):
            d = (v >= v[i]).all(axis=1) & (v > v[i]).any(axis=1)
            if d.any():
                u.loc[g.index[i], "dominated"] = True
    # D19: selection must not depend on file order. Equal scores: a unit seen live in the evidence pass first, then listing_id.
    u = u.sort_values(["hood_id", "dominated", "rank_score", "live_ok", "listing_id"], ascending=[True, True, False, False, True], kind="mergesort")
    # candidates: at most 2 per building, counted on the building (not the address key: independent check W8)
    u["nth_in_building"] = u.groupby("building_id").cumcount() + 1
    elig = u.nth_in_building <= CAND_PER_BUILDING
    u["hood_rank"] = np.nan
    u.loc[elig, "hood_rank"] = u[elig].groupby("hood_id").cumcount() + 1
    u["candidate"] = u.hood_rank <= CANDIDATES
    u["shown_pre_evidence"] = u.hood_rank <= SHOWN
    # Shown (owner, 2026-11-15): not an avoid building, and at most ONE thing still open, counting the three gate facts
    # (elevator, floor, dogs) and a missing live check alike. A unit with one open item is shown with an asterisk:
    # confirm_asterisk = yes, confirm_what, confirm_why. Two or more open gate facts were already dropped as sketchy.
    #   one open gate fact AND no live check -> data/needs_live_check.csv, not shown (W12)
    #   data/needs_confirmation.csv           the phone-call list: every candidate with one open gate fact, shown or not
    is_avoid = u.ev_avoid.eq("yes")
    clean = u.confidence.eq("clean")
    no_live = ~u.live_ok
    u["open_items"] = u.open_gate_facts + no_live.astype(int)
    live_txt = np.where(u.live_status.fillna("").astype(str).eq("blocked"), "The listing page could not be opened in the evidence pass; price and availability are as first collected.",
                        "The listing has not been seen live in the evidence pass yet; price and availability are as first collected.")
    # D3: a unit that was never seen live on a building page whose date is stale has two things open (rule, not only verdict)
    u["confirm_what"] = np.where(clean & no_live, "live check", u.confirm_what)
    u["confirm_why"] = np.where(clean & no_live, live_txt, u.confirm_why)
    # a building the evidence pass never touched has nothing a reviewer could read: its units wait, they are not shown
    u["no_evidence"] = pd.to_numeric(u.get("evidence_rows"), errors="coerce").fillna(0) <= 0
    showable = ~is_avoid & (u.open_items <= 1) & ~u.no_evidence
    u["nth_shown_in_building"] = np.nan
    u.loc[showable, "nth_shown_in_building"] = u[showable].groupby("building_id").cumcount() + 1
    ok = showable & (u.nth_shown_in_building <= MAX_PER_BUILDING)
    u["shown_rank"] = np.nan
    u.loc[ok, "shown_rank"] = u[ok].groupby("hood_id").cumcount() + 1
    u["shown"] = u.shown_rank <= SHOWN
    # ---- THIN NEIGHBORHOODS (owner, 2026-11-16): "if 46 of the 104 neighborhoods show one apartment and you don't have
    # sufficient data on those, cut them, unless one is really promising and well attested". A neighborhood whose shown
    # list is exactly ONE apartment keeps it only if the apartment is
    #   (a) well attested: nothing open at all (no open gate fact and seen live in the evidence pass: open_items == 0);
    #       disclosures do not count against it; and
    #   (b) promising: its rank score is at or above the median rank score of the apartments shown in its experience,
    #       the median being taken BEFORE this rule so the rule does not feed back on itself.
    # Applied once: a neighborhood with two shown apartments is not touched. The cut apartment stays in this file with
    # shown = False and not_shown_reason = thin_neighborhood.
    u["shown_before_thin_rule"] = u.shown
    thin = thin_neighborhood_cut(u.hood_id, u.group_key, u.shown, u.rank_score, u.open_items) if not NO_THIN_RULE else pd.Series(False, index=u.index)
    u["thin_neighborhood"] = thin
    u["not_shown_reason"] = np.where(thin, "thin_neighborhood", "")
    u.loc[thin, "shown"] = False
    u.loc[thin, "shown_rank"] = np.nan
    n_showable_b = u[showable].groupby("building_id").size()
    u["more_in_building"] = np.where(u.shown, (u.building_id.map(n_showable_b).fillna(0) - MAX_PER_BUILDING).clip(lower=0), np.nan)
    u["confirm_asterisk"] = np.where(u.open_items >= 1, "yes", "")
    cols = ["listing_id", "building_id", "building_name", "address", "unit", "hood", "group_label", "hood_rank", "rank_score", "all_in", "to_confirm", "url"]
    nc = u[~is_avoid & ~clean & (u.shown | (elig & (u.hood_rank <= CANDIDATES)))]
    nc.assign(shown_with_asterisk=nc.shown)[cols + ["shown_with_asterisk", "confirm_what", "confirm_why"]].to_csv(DATA / "needs_confirmation.csv", index=False)
    nl = u[~is_avoid & no_live & ~u.shown & (u.open_items <= 2) & elig & (u.hood_rank <= CANDIDATES)]
    nl.assign(live_status=nl.live_status.fillna("").replace("", "not checked"))[cols[:8] + ["rank_score", "all_in", "live_status", "open_gate_facts", "to_confirm", "url"]].to_csv(DATA / "needs_live_check.csv", index=False)
    u["needs_live_check"] = u.listing_id.isin(set(nl.listing_id))
    u["held_for_confirmation"] = u.listing_id.isin(set(nc.listing_id)) & ~u.shown
    av = elig & is_avoid
    u["avoid_rank"] = np.nan
    u.loc[av, "avoid_rank"] = u[av].groupby("hood_id").cumcount() + 1
    u["avoid_card"] = u.avoid_rank <= 5
    u["needs_evidence"] = (u.shown | (u.hood_rank <= CANDIDATES)) & ~u.evidence_checked
    u.to_csv(DATA / "ranked_units.csv", index=False)

    # ---- five-point spectrum against staying in Queens (Will, 2026-11-15): 3 = about the same as Queens,
    #      1-2 = worse for her, 4-5 = better for her. Closer to her parents counts as better (Will, 2026-11-15).
    home = u[u.hood_area.astype(str).eq("Queens")]
    SPEC = {  # column, kind, small band, big band, higher_is_better (None = neutral: 1 much closer .. 5 much farther)
        "all_in": ("all_in", "abs", 75, 250, False), "sqft": ("sqft", "abs", 50, 150, True),
        "drive_min": ("drive_min_to", "abs", 5, 20, False), "transit_min": ("transit_sat_median", "abs", 10, 30, False),  # Will: closer to her parents is better
        "violent_crime": ("violent", "ratio", 0.2, 0.5, False), "property_crime": ("property", "ratio", 0.2, 0.5, False),
        "food_and_drink_nearby": ("restaurants_800m", "ratio", 0.25, 0.6, True),
        "walk_to_green": ("park_walk_min", "abs", 2, 6, False), "parking": ("parking_rank", "abs", 0.5, 1.5, True),
    }
    spec_rows = []
    for name, (c, kind, small, big, hib) in SPEC.items():
        base = pd.to_numeric(home[c], errors="coerce").median()
        x = pd.to_numeric(u[c], errors="coerce")
        d = (x - base) if kind == "abs" else (x - base) / base
        step = np.where(d.abs() <= small, 0, np.where(d.abs() <= big, 1, 2)) * np.sign(d)
        if hib is False:
            step = -step
        u[f"vsq_{name}"] = np.where(x.isna(), np.nan, 3 + step)
        u[f"vsq_{name}_diff"] = (x - base).round(1)
        spec_rows.append({"measure": name, "column": c, "queens_median": round(base, 2), "kind": kind, "same_band": small,
                          "big_band": big, "direction": "higher is better" if hib else ("lower is better" if hib is False else "neutral: 1 closer, 5 farther")})
    pd.DataFrame(spec_rows).to_csv(DATA / "reference" / "queens_spectrum_definition.csv", index=False)
    u.to_csv(DATA / "ranked_units.csv", index=False)

    # ---- exchange rates against staying in Queens
    home = u[u.hood_area.astype(str).eq("Queens")]
    meas = {"all_in": "all_in", "sqft": "sqft", "drive_min": "drive_min_to", "transit_min": "transit_sat_median",
            "toll_round_trip": "toll_rt_known", "toll_round_trip_mail": "toll_rt_mail", "violent_per_1000": "violent", "property_per_1000": "property",
            "restaurants_800m": "restaurants_800m", "park_walk_min": "park_walk_min", "parking_rank": "parking_rank"}
    rows = []
    for k, g in list(u.groupby("group_label")) + [("STAYING IN QUEENS (baseline)", home)]:
        r = {"group": k, "units": len(g), "neighborhoods": g.hood_id.nunique()}
        for name in SPEC:
            r["vsq_" + name] = round(g[f"vsq_{name}"].median(), 0)
        for name, c in meas.items():
            r[name] = round(pd.to_numeric(g[c], errors="coerce").median(), 1)
            r[name + "_vs_home"] = round(r[name] - pd.to_numeric(home[c], errors="coerce").median(), 1)
        rows.append(r)
    pd.DataFrame(rows).to_csv(DATA / "group_exchange.csv", index=False)
    print(f"evidence: {n_ex} units excluded, shown {int(u.shown.sum())}, avoid cards {int(u.avoid_card.sum())}, of them with an asterisk {int((u.shown & (u.confirm_asterisk == 'yes')).sum())} "
          f"({u[u.shown & (u.confirm_asterisk == 'yes')].confirm_what.value_counts().to_dict()}), held for a confirmation {int(u.held_for_confirmation.sum())}, "
          f"waiting for a live check {int(u.needs_live_check.sum())}")
    print(f"stages: {n_in} costed -> -{n_cost} over the all-in cap -> -{n_cut} Jamaica safety rule -> -{n_hard} failed a gate on confirmed facts -> -{n_na} not an apartment (floor plan, building price, co-living room) -> -{n_rev} removed by a reviewed verdict -> -{n_sib} sibling floor rule -> -{n_sk} sketchy -> -{n_ex} evidence exclusions -> {len(u)} ranked")
    print(f"shown buildings {u[u.shown].building_id.nunique()}; disclosures: " + str(pd.Series([d['what'] for x in u[u.shown].disclosures if x for d in json.loads(x)]).value_counts().to_dict()))
    print(f"(kept {len(u)} units; candidates {int(u.candidate.sum())}; shown {int(u.shown_pre_evidence.sum())}; pools: {u.pool.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
