"""Tests for the repairs after docs/INDEPENDENT_CHECK_2.md (D1-D21), using the report's own rows as cases.

  python3 scripts/test_rules.py           pure rules and parsers (first step of scripts/run_all.py)
  python3 scripts/test_rules.py --data    the same defects checked on the pipeline's output (after rank.py)
Plain asserts; exits 1 on the first failure list.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import parsers as P  # noqa: E402
from lib import DATA, ROOT  # noqa: E402

FAILS = []
N = [0]


def eq(got, want, what):
    N[0] += 1
    if got != want:
        FAILS.append(f"{what}: got {got!r}, want {want!r}")


def ok(cond, what):
    N[0] += 1
    if not cond:
        FAILS.append(what)


def pure():
    import avoid
    # ---- D5: the co-op pattern had a dead word boundary; the patterns added beside it must not have the same slip
    for name in ("NOT_REAL", "INELIGIBLE", "BUILDING_WIDE", "NO_LIFT_READING", "GROUND_READING", "GROUND_LIKELY", "COOP", "NOT_COOP", "OUTAGE"):
        ok("\\\\" not in getattr(avoid, name).pattern, f"D5: avoid.{name} contains a doubled backslash (a literal backslash, not an escape)")
    ok(avoid.COOP.search("This oversized 1 bedroom co-op"), "D5: 'This oversized 1 bedroom co-op' (8300 Boulevard E 4D) must match COOP")
    ok(avoid.COOP.search("This is a single co-op unit in Woodcliff Gardens offered by an individual lister"), "D5: checker's co-op note must match")
    ok(avoid.COOP.search("Corner Line One Bedroom Coop"), "D5: 'Coop' must match")
    ok(not avoid.COOP.search("cooperative staff and a scoop of ice cream"), "D5: 'scoop' / 'cooperative staff' must not match")
    ok(avoid.NOT_COOP.search("Co-op City, Bronx"), "D5: the place name Co-op City is not a co-op finding")
    ok(avoid.NOT_COOP.search("Condo/co-op or owner-rented units; facts from the Trulia unit listing pages"), "D5: a harvester's 'condo/co-op or owner-rented' note is not a co-op finding")
    for name, example in [("INELIGIBLE", "this as a 55+ community"), ("INELIGIBLE", "No Units currently available"), ("BUILDING_WIDE", "55+"),
                          ("NO_LIFT_READING", "probably a walk-up"), ("NO_LIFT_READING", "My reading: unlikely"), ("GROUND_READING", "floor 1"),
                          ("GROUND_READING", ": 1"), ("GROUND_LIKELY", "probably the ground floor"), ("GROUND_LIKELY", "floor 1, if the plan name is the unit number")]:
        ok(getattr(avoid, name).search(example), f"D5: avoid.{name} must match its own example {example!r}")
    ok(not avoid.GROUND_READING.search("floor 12"), "GROUND_READING must not match floor 12")

    # ---- D3: "dogs explicitly allowed" means dogs named as allowed
    for t in ["Description: Pets upon approval (approval is case by case)", "Pets Considered Only on a Case by case basis",
              "small pets with landlord approval; dogs not named", "yes (pets allowed; species and size not stated)",
              "yes per Apartment List pet data; no policy text", "Contact for more information on pet policy"]:
        ok(P.dogs_not_explicit(t), f"D3: not an explicit dog policy: {t!r}")
    for t in ["Dogs allowed, 2 pets, 75 lb limit", "Dogs: Allowed (Size allowed: Small)", "small dogs only"]:
        ok(not P.dogs_not_explicit(t), f"D3: an explicit dog policy must pass: {t!r}")

    # ---- D8: lease term of the listed price
    for t, months, p12 in [("Price is for a 24 Months lease; total with required fees 2526", 24, None),
                           ("The price shown is for a 21-month lease", 21, None),
                           ("The price shown is for a 20-month lease (lease_length 20 in page data)", 20, None),
                           ("$2,340 IS THE 20-MONTH LEASE PRICE. AvalonBay's own unit data for 265: 12-month price $2,430 ($2,519 with the required $89 fee)", 20, 2430.0),
                           ("AvalonBay's own page (preferred): $2,590 is the 18-month term", 18, None),
                           ("unit 1304 lease term shown is 24 months", 24, None), ("updated 2026-11-14; lease 15 mo; page updated_at", 15, None),
                           ("Apartment List unit table, 15-month lease price", 15, None),
                           ("$2,010 is the 20-month-lease base rent; 12-month base is $2,105", 20, 2105.0),
                           ("1 month free when you sign an 18 month lease", None, None), ("Special: 2 months free on an 18-month lease", None, None),
                           ("promotion: free parking and amenities first year, 1 month free on 14-month lease", None, None)]:
        r = P.lease_term_from_text(t)
        eq((r["months"], r["price_12"]), (months, p12), f"D8 lease term in {t[:50]!r}")
    ok(P.lease_term_from_text("$2,168 is the lowest price over lease terms (range to $3,343)")["lowest_of_terms"], "D8: 'lowest price over lease terms' (Brownstones 09-426)")

    # ---- D10: a floor in a description counts only when it is about the unit
    for t in ["Soak up panoramic views from the 8th-floor sundeck or host friends", "Two landscaped 11th floor Terraces with an outdoor mister",
              "- 7th Floor Resident's Lounge and Furnished Terrace", "Outdoor Spaces on the Roof Deck and 10th Floor Terrace"]:
        eq(P.floor_from_description(t), None, f"D10: amenity floor in {t[:40]!r}")
    eq(P.floor_from_description("** Unit is located on 6th floor"), 6, "D10: unit floor")
    eq(P.floor_from_description("studio apartment on the 2nd floor of a well-maintained four story building"), 2, "D10: 255 E 61st St 2a")
    eq(P.floor_from_description("on the 3rd floor ... a bright fourth-floor unit"), None, "D10: two unit phrases that disagree")

    # ---- D13: required fees counted once
    eq(P.monthly_fees_from_text("$100/mo (trash $25 + amenity $75); electricity separate")[0], 100.0, "D13 Scribe 508: total and its own breakdown")
    eq(P.monthly_fees_from_text("$100 (amenity $75 + trash $25); electricity extra")[0], 100.0, "D13 The Asher 530")
    eq(P.monthly_fees_from_text("water and sewage $35-$45")[0], 45.0, "D13 Quarry Walk 219: a range is one fee (high end), not a sum")
    eq(P.monthly_fees_from_text("$182: A $90 + B $92")[0], 182.0, "W9 regression: stated total with colon")
    eq(P.monthly_fees_from_text("trash $25 + amenity $75")[0], 100.0, "W9 regression: plain sum")
    eq(P.monthly_fees_from_text("$50 (unit 12A)", "12A")[0], 50.0, "W9 regression: per-unit fee")

    # ---- D15: a price quoted from another listing never sets the parking fee
    eq(P.parse_parking("garage, extra fee (amount not stated here; the 1483 Shore Pkwy listing in the same complex says $200/month)")["fee"], None, "D15 2072 20th Ln 6E")
    eq(P.parse_parking("detached garage on site, $200/month")["fee"], 200.0, "D15 regression: the listing that does state $200")

    # ---- D16: a neighbouring tax lot is not the listing's lot
    for a, b, want in [("142-38 37th Ave", "142-32 37 AVENUE", False), ("255 E 61st St", "1161 2 AVENUE", False), ("12333 83rd Ave", "123-10 83 AVENUE", False),
                       ("3333 Broadway", "614 WEST 135 STREET", False), ("2165 Clarendon Rd", "1127 FLATBUSH AVENUE", False), ("5 Stuyvesant Pl", "160 RICHMOND TERRACE", False),
                       ("1010 Rogers Ave", "1010-1012 ROGERS AVENUE", True), ("35-16 34th St #5E", "35-16 34 STREET", True), ("3516 34th St", "35-16 34 STREET", True),
                       ("405 W 206th St", "405 WEST 206 STREET", True)]:
        eq(P.lot_address_agrees(a, b), want, f"D16 lot {a} vs {b}")

    # ---- D17: a label that describes a floor plan is not a unit label
    for u in ["1 bed, 1 bath, $1675", "1 Bed - 1 Bath", "907 (floor plan)", "floor plan One Bedroom (no unit number published)", ""]:
        eq(P.unit_label_key(u), "", f"D17: plan label {u!r}")
    eq(P.unit_label_key("302"), "302", "D17: a real unit label")


def data():
    import pandas as pd
    M = pd.read_csv(DATA / "master_units.csv", dtype=str, keep_default_na=False, low_memory=False).set_index("listing_id")
    R = pd.read_csv(DATA / "ranked_units.csv", dtype=str, keep_default_na=False, low_memory=False).set_index("listing_id")
    S = R[R.shown == "True"]
    m = lambda lid, c: M.at[lid, c] if lid in M.index else None

    # D2: unconfirmed evidence rows open the fact
    for lid in ["region_mid_hudson:z:85bae615f1e7", "region_mid_hudson:z:122e516bb694", "region_mid_hudson:z:dcd0e17e74e0"]:
        if lid in M.index:
            ok(m(lid, "elevator_evidence_open") != "", f"D2: {lid} elevator must be open (evidence row unconfirmed)")
    # D7 / D9: "select buildings", "amenity tag only"
    for lid in ["apartmentlist:p72935-A2839-5-02E", "apartmentlist:p372060-50-123", "apartmentlist:p98932510-00B-308", "apartmentlist:p90606231-431"]:
        if lid in M.index:
            ok(m(lid, "elevator_evidence_open") != "", f"D7/D9: {lid} elevator must be open")
    # D3
    for lid in ["trulia:2056687577", "trulia:466197377", "trulia:31977450", "trulia:2068977818"]:
        if lid in M.index:
            ok(m(lid, "dogs_evidence_open") != "", f"D3: {lid} dogs must be open")
    # D4: 2561 Bedford Ave: accessibility lift only -> no elevator on the city's record
    lid = "trulia:2069115016"
    if lid in M.index:
        ok(not (m(lid, "elevator") == "yes" and m(lid, "elevator_basis") in ("confirmed", "official_record")), "D4: 2561 Bedford Ave 3B elevator must not be confirmed / official record")
        eq(m(lid, "dob_active_elevators"), "0", "D4: 2561 Bedford Ave active elevators on record")
    ok(not ((M.elevator_basis == "official_record") & (M.pluto_lot_ok != "yes")).any(), "D16: no elevator may rest on the record of a lot at another address")
    # D8
    for lid, months in [("rc:sightmap:scribe:508", "24"), ("rc:sightmap:the-asher:530", "21"), ("apartmentlist:p9506-mr1x1lsm-4083", "20"),
                        ("apartmentlist:p58610350-022-265", "20"), ("apartmentlist:p970072-001-324", "18"), ("region_wr:leaf_nr:1304", "24"),
                        ("apartmentlist:p54753443-selS4-14A", "15"), ("apartmentlist:p113205989-lia-a2-333", "15"), ("apartmentlist:p37448175-wtha10x-312", "15")]:
        if lid in M.index:
            eq(m(lid, "price_lease_months"), months, f"D8: lease term of {lid}")
    lid = "apartmentlist:p58610350-022-265"
    if lid in M.index:
        eq(m(lid, "price_12_month"), "2430.0", "D8: Avalon Somerville 12-month price")
        ok('"rent (12-month lease price)", "amount": 2430' in m(lid, "all_in_lines"), "D8: Avalon Somerville cost uses the 12-month price")
        eq((m(lid, "unit_floor"), m(lid, "unit_floor_basis")), ("2", "confirmed"), "D10: Avalon Somerville 022-265 confirmed floor 2 must land")
    for lid in S.index:
        if (S.at[lid, "price_lease_months"] or "0").isdigit() and int(S.at[lid, "price_lease_months"] or 0) > 13:
            ok('"what": "lease term"' in S.at[lid, "disclosures"], f"D8: shown unit {lid} on a {S.at[lid, 'price_lease_months']}-month price must carry the lease-term disclosure")
            ok("lease term" not in S.at[lid, "confirm_what"], f"D8: lease term is a disclosure, not an open gate fact ({lid})")
    # D10: floors read from the unit number are not "confirmed"; amenity floors are not "stated"
    for addr, unit in [("89-25 162nd", "1003"), ("92-29 guy r brewer", "1307"), ("8267 austin", "916")]:
        x = M[M.addr_key.str.contains(addr) & (M.unit == unit)]
        ok(not (x.unit_floor_basis == "confirmed").any(), f"D10: {addr} {unit} floor is a unit-number reading, not confirmed")
    for addr, unit in [("623 ave h", "6C"), ("405 w 206th", "713E"), ("71-82 parsons", "615")]:
        x = M[M.addr_key.str.contains(addr) & (M.unit == unit)]
        ok(not (x.unit_floor_basis == "stated").any(), f"D10: {addr} {unit} floor came from an amenity sentence, not stated")
    # D11: rows with no unit number do not share one live-check row
    pp = M[M.index.str.contains("b2737454290:plan-")]
    if len(pp) >= 2:
        ok(m("trulia:b2737454290:plan-1-8B:452657838", "live_price") != "2438", "D11: Park Place Towers $2,683 plan must not carry the $2,438 check")
    gc = M[M.index.str.contains("b1045082049:plan-S3")]
    for lid in gc.index:
        ok(m(lid, "live_price") in ("2820", ""), "D11: Glen Cove S3 plan carries its own check ($2,820) or none")
    # D12
    for c in ("all_in_unknown_count", "cap_margin"):
        ok(c in M.columns, f"D12: column {c}")
    ok((pd.to_numeric(M.cap_margin) == 3000 - pd.to_numeric(M.all_in)).all(), "D12: cap_margin = 3000 - all_in")
    near = S[(pd.to_numeric(S.all_in) >= 2900) & (pd.to_numeric(S.all_in_unknown_count) >= 1)]
    ok(near.disclosures.str.contains('"what": "cost near the cap"', regex=False).all(), "D12: every shown unit at $2,900+ with an unknown cost line carries the disclosure")
    ok(not S.confirm_what.str.contains("cost near the cap|lease term|condo").any(), "disclosures never count as the open gate fact")
    ok((S.open_gate_facts.astype(float) <= 1).all(), "a shown unit has at most one open gate fact")
    sk_ = pd.read_csv(DATA / "excluded_sketchy.csv", dtype=str, keep_default_na=False, low_memory=False)
    ok(not sk_.sketchy_reason.str.contains("cost near the cap|lease term").any(), "no unit is dropped as sketchy because of a disclosure")
    ok("more_in_building" in S.columns and (S.groupby("building_id").size() <= 2).all(), "at most 2 shown per building, with more_in_building recorded")
    # D13 / D14 / D15
    for lid, c, want in [("rc:sightmap:scribe:508", "required building fees\", \"amount\": 100", True), ("rc:sightmap:the-asher:530", "required building fees\", \"amount\": 100", True)]:
        if lid in M.index:
            ok((c in m(lid, "all_in_lines")) == want, f"D13: {lid} fee line")
    for name, unit in [("Beacon Mill Village", "PA-405"), ("City Trust Collection: Arcade Apartments.", "302"), ("Avalon Somerville Station", "022-265"), ("Scribe", "508")]:
        x = M[(M.building_name == name) & (M.unit == unit)]
        ok(len(x) == 0 or (x.rent_basis_kind == "listed").all(), f"D14: {name} {unit} must not be costed as net-effective")
    x = M[M.addr_key.str.contains("2072 20th") & (M.unit == "6E")]
    ok(len(x) == 0 or (x.parking_fee_monthly == "").all(), "D15: 2072 20th Ln 6E parking fee is not stated on its listing")
    x = M[(M.building_name == "Avalon Maplewood") & (M.unit == "001-324")]
    ok(len(x) == 0 or '"amount": 2590' in x.all_in_lines.iloc[0], "D15: Avalon Maplewood 001-324 rent line uses the live $2,590")
    x = M[(M.building_name == "Avalon Teaneck") & (M.unit == "001-215")]
    ok(len(x) == 0 or '"amount": 2521' in x.all_in_lines.iloc[0], "D15: Avalon Teaneck 001-215 rent line uses the $2,521 read by the independent check")
    x = M[M.building_name.str.contains("Metrovue") & (M.unit == "201")]
    ok(len(x) == 0 or "building fees" not in x.all_in_unknown_lines.iloc[0], "D15: Metrovue 201 total price already includes the required fees")
    # D17
    D = pd.read_csv(DATA / "duplicate_units.csv", dtype=str, keep_default_na=False)
    ok("apartmentlist:p7630984-8dc0ef5a-1dcf-425e-8486-1d575c05d1dc" in set(D.listing_id) or "apartmentlist:p7630984-4bec8063-f064-11ee-8ab6-12de4bf481cd" in set(D.listing_id),
       "D17: Arcade Apartments 302 and its unnamed twin are merged")
    # D19: ties in the selection order are broken by live check, then listing_id
    Rr = R.reset_index()
    Rr["live_ok_"] = Rr.live_status.isin(["live", "changed"])
    exp = Rr.sort_values(["hood_id", "dominated", "rank_score_num", "live_ok_", "listing_id"], ascending=[True, True, False, False, True], kind="mergesort") \
        if "rank_score_num" in Rr else None
    Rr["rank_score_num"] = pd.to_numeric(Rr.rank_score)
    exp = Rr.sort_values(["hood_id", "dominated", "rank_score_num", "live_ok_", "listing_id"], ascending=[True, True, False, False, True], kind="mergesort")
    ok(list(exp.listing_id) == list(Rr.listing_id), "D19: ranked_units.csv is not in the deterministic order (hood, dominated, score, live-checked first, listing_id)")
    # verdict table is applied
    V = pd.read_csv(DATA / "evidence" / "review_verdicts.csv", dtype=str, keep_default_na=False)
    ok(not set(V[V.verdict == "remove"].listing_id) & set(R.index), "verdicts: a unit with verdict remove is still ranked")
    for r in V[V.verdict == "asterisk"].itertuples():
        if r.listing_id in S.index:
            ok(S.at[r.listing_id, "confirm_asterisk"] == "yes" or (r.kind in ("lease_term", "coop_condo", "other") and S.at[r.listing_id, "disclosures"] != ""),
               f"verdicts: {r.listing_id} has an asterisk verdict but is shown without an asterisk or a disclosure")
    ok(set(S.index) <= set(V[V.verdict.isin(["ok", "asterisk"])].listing_id), "verdicts: a shown unit has no ok / asterisk verdict")
    # 62 Treat St: plan "103" reads as floor 1; plan "208" must not be excluded with it
    X = pd.read_csv(DATA / "unit_exclusions.csv", dtype=str, keep_default_na=False)
    t = X[X.addr_key == "62 treat st|06516"]
    ok(not ((t.unit == "") & (t.listing_id == "")).any(), "62 Treat St must not be excluded as a whole building")
    ok(t.listing_id.str.contains("plan-103").any(), "62 Treat St plan 103 (reads as floor 1) is excluded by its listing id")
    # D20 (only when the page data is newer than the ranking)
    pj = ROOT / "site" / "data.json"
    if pj.exists() and pj.stat().st_mtime >= (DATA / "ranked_units.csv").stat().st_mtime:
        J = json.loads(pj.read_text())
        txt = json.dumps(J)
        ok("North Plainfield is a beautiful subset of Somerset County" not in txt, "D20: the North Plainfield quote must not be on the page")
        ok("As the President of Jamaica Hill Community Association" not in txt, "D20: the quote naming its writer by office must not be on the page")
        vs = [v for h in J["neighborhoods"] for v in ((h.get("local") or {}).get("voices") or []) if isinstance(v, dict)]
        ok(not vs or any(v.get("about") for v in vs), "D20: quotes about a wider area carry 'about'")
        ok(not vs or all("source_area" in v for v in vs), "D20: source_area is kept on every quote")


if __name__ == "__main__":
    (data if "--data" in sys.argv else pure)()
    print(f"test_rules {'(data)' if '--data' in sys.argv else '(rules)'}: {N[0]} checks, {len(FAILS)} failed")
    for f in FAILS:
        print("  FAIL", f)
    sys.exit(1 if FAILS else 0)
