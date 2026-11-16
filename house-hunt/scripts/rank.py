"""Ranking v2 (Will, 2026-11-15: "use many more variables; drop anything sketchy"). See docs/RANKING.md.

Listing confidence (before ranking):
  sketchy       -> excluded: stale 60+ days, no unit and no building name, thin syndicated feed, conflicting dog policy,
                   all-in under 60% of the neighborhood median, or two or more inferred gate facts
  one_inferred  -> kept, lower certainty; the open fact (elevator inferred from 6+ floors, floor not stated, or dog
                   size given only as "small") must be confirmed in the evidence pass before the unit is shown
  clean         -> every gate fact stated on the page
Universal value, 0-100 (weights sum to 100): safety 22, building 16, cost 12, car 12, space 12, distance 10,
dog 8, daily life 8. Each part blends several variables as percentiles across all kept units; an unknown variable
scores at the 25th percentile.
Rank score = 0.7 x universal + 0.3 x the year's promise + pool bump (+3 pool, +6 indoor), times a certainty factor
(1.00 clean, 0.97 one inferred fact).
Selection per neighborhood: top by rank score, at most 2 per building, dominated units last; top 15 are candidates
for the evidence pass, the best 10 that survive are shown.
Outputs: data/ranked_units.csv, data/group_exchange.csv, data/reference/queens_spectrum_definition.csv
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
MAX_PER_BUILDING, SHOWN, CANDIDATES = 2, 10 ** 6, 15
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
    if "garage" in t or "gated" in t:
        return 4
    if "covered" in t or "carport" in t:
        return 3
    if "lot" in t or "surface" in t or "off-street" in t or "off street" in t or "assigned" in t:
        return 2
    if "street" in t:
        return 1
    return np.nan


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

    # ---- reviewed verdicts (independent check 2): data/evidence/review_verdicts.csv holds one row per unit whose
    # evidence a reviewer has read. remove -> excluded here, before ranking, with the reviewer's reason.
    # asterisk -> the unit counts as having that open fact (below). ok -> nothing added. A verdict never closes a fact
    # the rules leave open; scripts/check_registry.py fails the run if a shown unit has no current ok / asterisk verdict.
    vf = DATA / "evidence" / "review_verdicts.csv"
    V = pd.read_csv(vf, dtype=str, keep_default_na=False).drop_duplicates("listing_id", keep="last").set_index("listing_id") if vf.exists() else \
        pd.DataFrame(columns=["verdict", "kind", "what_to_confirm", "why"])
    vd = lambda c: u.listing_id.map(V[c]).fillna("") if len(V) else pd.Series("", index=u.index)
    rm = vd("verdict").eq("remove")
    u[rm].assign(drop_reason="reviewed: " + vd("why")[rm], review_kind=vd("kind")[rm]).to_csv(DATA / "excluded_by_review.csv", index=False)
    n_rev = int(rm.sum()); u = u[~rm].copy()
    s = lambda c: u[c].fillna("").astype(str) if c in u else pd.Series("", index=u.index)
    vd = lambda c: u.listing_id.map(V[c]).fillna("") if len(V) else pd.Series("", index=u.index)

    # ---- listing confidence
    age = pd.to_numeric(u.get("listing_age_days"), errors="coerce")
    med = u.groupby("hood_id").all_in.transform("median")
    reasons = pd.Series("", index=u.index)
    for cond, why in [(age >= 60, "listing 60+ days old"), ((s("unit") == "") & (s("building_name") == ""), "no unit or building named"),
                      (s("notes").str.contains("listhub|propertyware", case=False), "thin syndicated feed"),
                      (s("notes").str.contains("CONFLICT"), "conflicting dog policy"), (u.all_in < 0.6 * med, "price far below the neighborhood"),
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
    v_ast = vd("verdict").eq("asterisk")
    vk = vd("kind").where(v_ast, "")
    # elevator: no page or record states one (base), or the evidence pass looked and could not confirm it (D2, D7, D9),
    # or the reviewer's verdict says it is not established for this building
    # a fact answered on the phone is settled: neither an older evidence row nor an earlier reviewer's asterisk reopens it
    phone_e, phone_d = s("elevator_basis").eq(SETTLED_BY_PHONE), s("dogs_allowed_basis").eq(SETTLED_BY_PHONE)
    phone_av = s("call_available").ne("")
    base_e = s("elevator_basis").isin(["inferred", "", "unknown"]) | s("elevator").str.lower().ne("yes")
    inf_e = base_e | ((s("elevator_evidence_open").ne("") | vk.eq("elevator")) & ~phone_e)
    fb, fk = s("unit_floor_basis"), s("unit_floor_label_kind")
    floor_settled = fb.isin(["confirmed", "stated", SETTLED_BY_PHONE])
    floor_from_label_ok = fb.eq("inferred") & fk.eq("simple") & (fl >= 3)
    inf_f = ~floor_settled | vk.eq("floor")          # not published: unknown, or only read from the unit number
    u["floor_basis_note"] = np.where(floor_from_label_ok, "read from the unit number", "")
    # dogs: allowed must be stated or confirmed, and dogs must be NAMED as allowed (D2, D3): an unconfirmed evidence
    # row, "pets upon approval", "case by case" or small pets with dogs unnamed leave the fact open
    base_d = s("dogs_allowed").str.lower().ne("yes")
    dog_open = base_d | ((s("dogs_evidence_open").ne("") | vk.eq("dogs")) & ~phone_d)
    no_limit = s("dog_weight_limit_lb").str.lower().eq("no limit")
    dog_small = s("dog_size_only").ne("") & wl.isna() & ~no_limit
    # 4a: "weight restrictions apply" / a weight limit with no number passes like "small dogs", with the same tour question
    dog_wl_unstated = s("dog_weight_unstated").ne("") & wl.isna() & ~no_limit & ~dog_small
    # An elevator "inferred from height" only counts as one open fact when a page or record gives the building 6+ floors.
    # Where the height itself was read off a unit label ("36D", "801"), the elevator is simply unknown: not shown.
    bfl = pd.to_numeric(s("building_floors"), errors="coerce").where(~s("building_floors_basis").isin(["inferred", ""]))
    # the city's floor count is used only when the tax lot is the listing's own address (D16)
    tall = (bfl.fillna(0) >= 6) | ((pd.to_numeric(s("pluto_floors"), errors="coerce").fillna(0) >= 6) & s("pluto_lot_ok").eq("yes"))
    weak_e = base_e & ~tall
    # ---- the other things a renter must not find out later (independent check 2)
    #  lease      the listed price belongs to a lease longer than 13 months, or is only "the lowest over the lease terms" (D8)
    #  cost       all-in within $100 of the cap while pet rent, parking or required fees is unknown and counted as $0 (D12)
    #  listing    an evidence warning about the listing itself (wrong address, generic text, owner on record), D6
    #  availability  the row is a floor plan, not a named unit: no unit, floor or date could be checked (D1)
    #  plus whatever a reviewer's asterisk verdict names (availability, listing, eligibility, condo, other)
    lm = pd.to_numeric(s("price_lease_months"), errors="coerce")
    p12 = pd.to_numeric(s("price_12_month"), errors="coerce")
    lease_open = (lm > 13) | s("price_lowest_of_terms").eq("yes") | vk.eq("lease_term")
    cost_open = (u.all_in >= CAP - NEAR_CAP) & (pd.to_numeric(s("all_in_unknown_count"), errors="coerce").fillna(0) >= 1)
    plan_only = s("unit").map(parsers.unit_label_key).eq("") & (s("detail_level").eq("building_floorplan") | s("listing_id").str.contains(":plan-") | s("unit").str.strip().ne(""))
    avail_open = (plan_only | vk.isin(["not_available"])) & ~phone_av
    # 4b: a page last changed more than 60 days before it was read (no second site), or an availability date over six
    # months old, is the open item "listing" by rule; it is not counted twice when a reviewer already wrote it up as availability
    stale_open = s("listing_stale").eq("open") & ~vk.isin(["not_available"]) & ~phone_av
    listing_open = (s("listing_warning").ne("") | vk.isin(["unverified", "wrong_building"]) | stale_open) & ~(phone_av & s("listing_warning").eq(""))
    elig_open, condo_open, other_open = vk.eq("restricted"), vk.eq("coop_condo"), vk.eq("other")
    unknown_lines = s("all_in_unknown_lines").str.replace("building fees (part)", "some required fees", regex=False).str.replace("building fees", "required fees").str.replace("parking fee", "parking") \
        .map(lambda t: " / ".join(x for x in t.split("; ") if x in ("pet rent", "parking", "required fees", "some required fees")))
    lease_why = np.where(lm > 13, "The listed price is for a " + lm.fillna(0).astype(int).astype(str) + "-month lease."
                         + pd.Series(np.where(p12.notna(), " The 12-month price is $" + p12.fillna(0).astype(int).astype(str) + ", which is what the cost here uses.", " The 12-month price is not published."), index=u.index),
                         "The listed price is the lowest over the lease terms offered; the term it belongs to and the 12-month price are not published.")
    OPEN = [  # key, flag, label on the page, why, question
        ("elevator", inf_e, "elevator",
         np.where(base_e, "No page states an elevator; the building's height suggests one.", "The evidence pass could not confirm an elevator for this building: " + s("elevator_evidence_open").str.replace("the evidence pass could not confirm it: ", "", regex=False).str[:140]),
         "Does this building have an elevator?"),
        ("floor", inf_f, "floor", None, None),
        ("dogs", dog_open, "dogs allowed",
         np.where(base_d, "Two listing sites disagree on whether dogs are allowed, and the building's own page does not settle it.",
                  "Dogs are not confirmed as allowed here: " + s("dogs_evidence_open").str.replace("the evidence pass could not confirm it: ", "", regex=False).str[:140]),
         "Are dogs allowed? (dogs must be named as allowed, not 'pets on approval')"),
        ("lease", lease_open, "lease term", lease_why, "What is the rent on a 12-month lease?"),
        ("cost", cost_open, "cost near the cap", "Cost near the cap: " + unknown_lines + " not published (counted as $0), and the all-in figure is within $" + str(NEAR_CAP) + " of $3,000.",
         "What are the pet rent, parking and required monthly fees?"),
        ("availability", avail_open, "availability", "This is a floor-plan price, not a named unit: no unit, floor or date could be checked.", "Which unit is available at this price, on which floor, and from when?"),
        ("listing", listing_open, "listing", np.where(s("listing_warning").ne(""), "The evidence pass raised a warning about this listing: " + s("listing_warning").str[:160],
                                                      "The listing may be stale: " + s("listing_stale_why") + "."),
         np.where(s("listing_warning").ne(""), "Is this listing for this building, and is it genuine?", "Is this unit still available? The listing page has not changed in over two months.")),
        ("eligibility", elig_open, "eligibility", "", "Is this unit open to any renter?"),
        ("condo", condo_open, "condo rules", "", "What are the building's rules for renting this unit?"),
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
    v_why, v_q, v_key = vd("why").where(v_ast, ""), vd("what_to_confirm").where(v_ast, ""), vk.map(KIND_KEY).fillna("")
    what_l, why_l, q_l, keys_l, disc_l = [], [], [], [], []
    net_eff = s("rent_basis_kind").eq("net_effective").values
    offer_txt = s("rent_offer_text").str[:160].values
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
                reviewed = v_key.iloc[i] == k
                why_ = v_why.iloc[i] if reviewed and v_why.iloc[i] else str(w[i])
                q_ = v_q.iloc[i] if reviewed and v_q.iloc[i] else (fq[i] if k == "floor" else (q if isinstance(q, str) else str(q[i])))
                if k in DISCLOSURE_KEYS:
                    disc.append({"what": "condo rented by its owner" if k in ("condo", "other") else ("floor not published" if k == "floor" else lab),
                                 "why": why_, "question": FLOOR_DISCLOSURE if k == "floor" else (q_ or "")})
                    continue
                keys.append(k); whats.append(lab); whys.append(why_); qs.append(q_)
        if net_eff[i]:
            disc.append({"what": "net-effective rent", "why": "The rent shown is the average after a special offer, not the monthly payment." + (" Offer: " + offer_txt[i] if offer_txt[i] else ""),
                         "question": "What is the full monthly rent, and when is the first full payment due?"})
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
    comfort = (pts(laundry.str.contains("in unit|in_unit|in-unit|yes"), laundry.str.strip().ne(""), 2.5)
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
    # at most 2 per building, counted on the building (not the address key: independent check W8)
    u["nth_in_building"] = u.groupby("building_id").cumcount() + 1
    elig = u.nth_in_building <= MAX_PER_BUILDING
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
    print(f"stages: {n_in} costed -> -{n_cost} over the all-in cap -> -{n_cut} Jamaica safety rule -> -{n_hard} failed a gate on confirmed facts -> -{n_rev} removed by a reviewed verdict -> -{n_sk} sketchy -> -{n_ex} evidence exclusions -> {len(u)} ranked")
    print(f"(kept {len(u)} units; candidates {int(u.candidate.sum())}; shown {int(u.shown_pre_evidence.sum())}; pools: {u.pool.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
