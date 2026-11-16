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

    # ---- tolls: an incomplete sum is not a toll, and unknown is never 0
    eq(P.toll_known(16.66, True), 16.66, "toll: complete")
    eq(P.toll_known("16.66", "True"), 16.66, "toll: complete, strings")
    eq(P.toll_known(0.0, True), 0.0, "toll: a complete route with no tolled crossing is a real $0")
    eq(P.toll_known(0.0, False), None, "toll: an incomplete sum of $0 is unknown, not $0")
    eq(P.toll_known(float("nan"), True), None, "toll: missing value")
    eq(P.toll_known(None, None), None, "toll: nothing known")
    ok("New York E-ZPass" in P.TOLL_NOTE and "mail" in P.TOLL_NOTE.lower(), "toll note names the New York E-ZPass assumption and the mail rate")
    pure_more()


def pure_more():
    # ---- Jersey City split (docs/SUBCITY_SPLIT_PLAN.md): Jersey City only, point-in-polygon, overrides, parent fallback
    import tempfile
    import build_neighborhoods as BN
    subs = BN.subcity_polys()
    eq({c for c, *_ in subs}, {"Jersey City"}, "split: only Jersey City is adopted (not Newark)")
    eq(len(subs), 8, "split: eight Jersey City neighborhoods")
    eq(BN.subcity_name("Jersey City", "NJ", 40.7220882, -74.0648094, subs), "Jersey City – McGinley Square", "split: 20 Beacon Way is McGinley Square")
    eq(BN.subcity_name("Jersey City", "NJ", 40.7358924, -74.0475323, subs), "Jersey City – The Heights", "split: 110 Hoboken Ave falls in the Heights polygon before the override")
    eq(BN.subcity_name("Newark", "NJ", 40.7357, -74.1724, subs), "Newark", "split: Newark stays whole")
    eq(BN.subcity_name("Hoboken", "NJ", 40.744, -74.032, subs), "Hoboken", "split: other towns are untouched")
    eq(BN.subcity_name("Jersey City", "NY", 40.72, -74.06, subs), "Jersey City", "split: the state must match")
    ov = BN.subcity_overrides()
    for key, lat, lon, want in [("110 hoboken ave|07310", 40.7358924, -74.0475323, "Jersey City – Downtown"), ("15 carbon pl|07305", 40.7124275, -74.0934336, "Jersey City – West Side"),
                                ("176 w side ave|07305", 40.7100727, -74.0939888, "Jersey City – West Side"), ("104 clifton pl|07304", 40.7209244, -74.064888, "Jersey City – McGinley Square")]:
        eq(BN.subcity_name("Jersey City", "NJ", lat, lon, subs, ov, keys=(key,)), want, f"split: override for {key}")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "o.csv"
        f.write_text("addr_key,building_id,hood_label,reason\n1 test st|07302,b_x,Jersey City – Newport,test\n")
        o2 = BN.subcity_overrides(f)
        eq(BN.subcity_name("Jersey City", "NJ", 40.7220882, -74.0648094, subs, o2, keys=("zzz", "b_x")), "Jersey City – Newport", "split: an override may be keyed on the building id")
        eq(BN.subcity_overrides(Path(td) / "missing.csv"), {}, "split: a missing override file is no overrides")
    eq(BN.hood_id_of("NJ", "Jersey City – Journal Square"), "nj:jersey-city-journal-square", "split: hood_id from the label")
    par = BN.subcity_parents()
    eq(par["nj:jersey-city-west-side"]["parent_id"], "nj:jersey-city", "split: parent id")
    eq(BN.route_to_children("nj:hoboken", "", par), [("nj:hoboken", None)], "fallback: a town that is not split keeps its id")
    eq(BN.route_to_children("nj:newark", "", par), [("nj:newark", None)], "fallback: Newark is not split")
    eq(BN.route_to_children("nj:jersey-city", "Journal Square, Jersey City", par), [("nj:jersey-city-journal-square", None)], "fallback: a Journal Square survey row goes to Journal Square only")
    eq(BN.route_to_children("nj:jersey-city", "McGinley Square, Jersey City", par), [("nj:jersey-city-mcginley-square", None)], "fallback: McGinley Square row")
    r = BN.route_to_children("nj:jersey-city", "Jersey City, NJ", par)
    eq((len(r), {a for _, a in r}), (8, {"Jersey City as a whole"}), "fallback: citywide content goes to all eight, labelled as about Jersey City as a whole")
    pure_3()


def pure_3():
    import tempfile
    import pandas as pd
    import build_master as BM
    import rank
    # ---- step 3: overnight street-parking rule -> disclosure (a reviewed table, never free text at run time)
    for sev, ptype, fee, want in [("ban", "", "", True), ("ban", "street", "0", True), ("permit", "street parking only", "", True), ("seasonal", "unknown", "", True),
                                  ("ban", "garage", "", False), ("ban", "open_lot", "", False), ("ban", "covered: assigned parking", "150", False),
                                  ("permit", "", "175", False), ("permit", "", "0", False), ("", "", "", False), ("none", "street", "", False)]:
        eq(rank.needs_parking_disclosure(sev, ptype, fee), want, f"parking disclosure: severity {sev!r}, type {ptype!r}, fee {fee!r}")
    OP = BM.overnight_parking_rules()
    for hid, sev in [("nj:south-orange", "ban"), ("nj:ridgewood", "ban"), ("nj:springfield", "ban"), ("ny:white-plains", "ban"), ("nj:east-orange", "permit"), ("nj:princeton", "permit"),
                     ("nj:fort-lee", "permit"), ("nj:bayonne", "permit"), ("nj:north-bergen", "permit"), ("nj:jersey-city-journal-square", "permit"), ("nj:jersey-city-west-side", "permit"),
                     ("nj:red-bank", "seasonal")]:
        eq(OP.get(hid, {}).get("severity"), sev, f"overnight parking table: {hid}")
    ok("ny:middle-village" not in OP and "nj:hoboken" not in OP and "ny:hempstead" not in OP, "overnight parking table: towns with no such rule (or only a pending one) are not in it")
    ok(all(v["rule"] and v["url"].startswith("http") and v["town"] for v in OP.values()), "overnight parking table: every row has a summary, a town and a source URL")
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "t.csv"
        f.write_text("municipality,state,rule_summary,applies_to_hood_ids,source_url,severity\nA,NJ,snow rule,nj:a;nj:b,http://x/1,seasonal\nA,NJ,ban rule,nj:a,http://x/2,ban\nC,NJ,odd,nj:c,http://x/3,maybe\n")
        t = BM.overnight_parking_rules(f)
        eq((t["nj:a"]["severity"], t["nj:b"]["severity"], "nj:c" in t), ("ban", "seasonal", False), "overnight parking table: the stricter row wins; an unknown severity is ignored")
        eq(BM.overnight_parking_rules(Path(td) / "none.csv"), {}, "overnight parking table: a missing file is no rules")
    # ---- step 4a: a dog weight limit with no number
    for t, want in [("Weight and breed restrictions apply", True), ("Breed and Weight Restrictions", True), ("Call for breed and weight restrictions", True),
                    ("limit exists, pounds not published", True), ("size limit exists, number not given", True), ("not stated (weight limits 'may apply')", True),
                    ("A pound maximum weight limit per pet will be strictly enforced", True), ("Breed restrictions, weight limits, and pet fees apply", True),
                    ("Breed restrictions apply", False), ("no weight limit stated (breed list only)", False), ("Dogs allowed, 2 pets, 75 lb limit", False),
                    ("company policy lists restricted breeds and a two-pet maximum, no weight limit", False), ("Size allowed: Small", False), ("", False)]:
        eq(P.dog_weight_unstated(t), want, f"4a: dog weight limit with no number in {t!r}")
    eq(P.DOG_WEIGHT_QUESTION, "Confirm the dog weight limit in pounds", "4a: the tour question")
    # ---- step 4b: staleness thresholds (60 days / six months), from modification dates
    eq(P.page_modified_date("Trulia's header says 0 available units and the page was last modified 2026-09-03"), "2026-09-03", "4b: last modified date in a note")
    eq(P.page_modified_date("Page last modified 2026-01-26; unit record updated 2026-11-15T10:04:49Z"), "2026-11-15", "4b: the latest date wins (the unit's own record is fresh)")
    eq(P.page_modified_date("16 days on Trulia; listed 2026-10-23"), "", "4b: a listing date is not a modification date")
    eq(P.staleness("2026-09-03", "2026-11-15")[0], "open", "4b: 73 days unchanged -> one open item")
    eq(P.staleness("2026-09-16", "2026-11-15")[0], "", "4b: exactly 60 days is not stale")
    eq(P.staleness("2026-09-03", "2026-11-15", second_source=True)[0], "", "4b: a second site listing the unit clears the 60-day item")
    eq(P.staleness("2026-05-15", "2026-11-15")[0], "remove", "4b: 184 days unchanged -> removed")
    eq(P.staleness("2026-05-16", "2026-11-15")[0], "open", "4b: 183 days is still one open item")
    eq(P.staleness("2026-04-28", "2026-11-15", second_source=True)[0], "remove", "4b: over six months is removed even with a second site")
    eq(P.staleness("", "2026-11-15", available_date="2026-04-01")[0], "open", "4b: an availability date over six months old -> one open item")
    eq(P.staleness("", "2026-11-15", available_date="now")[0], "", "4b: no dates, nothing flagged")
    eq(P.staleness("2026-11-10", "2026-11-15", available_date="2026-12-01")[0], "", "4b: a fresh page")
    # ---- step 4c: one grading for an elevator in a listing site's amenity list, whatever the batch called the row
    eq(P.elevator_row_kind("yes", "amenity: Elevator", True, "confirmed"), "stated", "4c: batches 1, 2, 8, 9 ('confirmed' on Apartment List) -> stated")
    eq(P.elevator_row_kind("yes (Apartment List amenity tag only)", "Elevator", True, "unconfirmed"), "stated", "4c: batches 10, 15 ('unconfirmed', tag only) -> stated")
    eq(P.elevator_row_kind("yes", "Elevator access to all floors", False, "confirmed"), "own", "4c: the building's own page -> confirmed")
    eq(P.elevator_row_kind("unconfirmed: Apartment List tags 'Elevator'; AvalonBay's own pages never mention one", "amenity: Elevator", True, "unconfirmed"), "contra", "4c: the owner's own pages omit it -> stays open")
    eq(P.elevator_row_kind("my reading: probably a walk-up", "", True, "unconfirmed"), "contra", "4c: a checker's reading against it -> stays open")
    eq(P.elevator_row_kind("select buildings only", "an elevator. Additional features vary by building", True, "unconfirmed"), "contra", "4c: select buildings only -> stays open")
    eq(P.elevator_row_kind("unconfirmed", "no elevator in the feature list on this page", True, "unconfirmed"), "none", "4c: no elevator listed -> stays open")
    A, O = "https://www.apartmentlist.com/nj/x/y", "https://www.thebuilding.com/amenities"
    eq(BM.elevator_only_from_listing_sites([(5, "yes", "stated", A), (3, "yes", "amenities_page", "https://www.trulia.com/b/1")]), True, "4c: only listing sites say yes")
    eq(BM.elevator_only_from_listing_sites([(5, "yes", "stated", A), (1, "yes", "confirmed", O)]), False, "4c: the building's own page also says yes")
    eq(BM.elevator_only_from_listing_sites([(5, "yes", "stated", A), (4, "yes", "official_record", "NYC PLUTO building class D1")]), False, "4c: a city record also says yes")
    eq(BM.elevator_only_from_listing_sites([(6, "yes", "inferred", A)]), False, "4c: an inference is not a statement")
    # ---- step 5: phone answers are the highest-precedence source; the file may be absent
    with tempfile.TemporaryDirectory() as td:
        eq(BM.load_call_answers(Path(td) / "call_answers.csv"), [], "calls: an absent file is no answers")
        f = Path(td) / "call_answers.csv"
        pd.DataFrame([{"building_id": "b_1", "listing_ids": "x:439; x:477", "units": "439; 477", "ans_floor": "439=4; 477=1", "ans_elevator": "yes", "ans_dog_weight_lb": "50",
                       "ans_pet_rent": "35", "ans_parking_fee": "0", "ans_required_fees": "89", "ans_lease_term_months": "12", "ans_12mo_price": "439=2500",
                       "ans_available_date": "439=2026-12-01; 477=gone", "ans_income_multiple": "40", "ans_notes": "spoke to the leasing office", "called_at": "2026-11-18T15:10:00-05:00"},
                      {"building_id": "b_2", "listing_ids": "y:1", "units": "2B", "ans_elevator": "no", "called_at": "2026-11-18T16:00:00-05:00"},
                      {"building_id": "b_3", "listing_ids": "z:1", "units": "1A", "ans_elevator": "yes", "called_at": ""}]).to_csv(f, index=False)
        ans = BM.load_call_answers(f)
        eq(len(ans), 3, "calls: one row per listing; a row with no called_at is refused")
        M = BM.Merge()
        M.add("b_1", "elevator", "yes", "inferred", "harvester")
        M.add("b_1", "elevator_evidence_open", "the evidence pass could not confirm it: x", "confirmed", "u")
        M.add("b_1", "dog_weight_unstated", "yes: weight restrictions apply", "stated", "u")
        M.add("b_1", "parking_fee_monthly", "150", "confirmed", "https://own.site/fees")
        M.add("b_2", "elevator", "yes", "confirmed", "https://own.site")
        called = BM.apply_call_answers_building(M, ans, {"x:439": "b_1", "x:477": "b_1", "y:1": "b_2"})
        rows, _ = M.resolve()
        rows = BM.phone_overrides_building(rows)
        eq((rows["b_1"]["elevator"], rows["b_1"]["elevator_basis"], rows["b_1"]["elevator_source"]), ("yes", "confirmed_by_phone", "phone call 2026-11-18T15:10:00-05:00"), "calls: elevator by phone, with called_at in the source")
        ok("elevator_evidence_open" not in rows["b_1"] and "dog_weight_unstated" not in rows["b_1"], "calls: a fact answered on the phone is no longer open")
        eq((rows["b_1"]["dog_weight_limit_lb"], rows["b_1"]["dogs_allowed"], rows["b_1"]["dogs_allowed_basis"]), ("50", "yes", "confirmed_by_phone"), "calls: dog weight limit by phone")
        eq((rows["b_1"]["parking_fee_monthly"], rows["b_1"]["parking_fee_monthly_basis"]), ("0", "confirmed_by_phone"), "calls: a phone answer outranks a confirmed page")
        eq((rows["b_1"]["pet_rent_monthly"], rows["b_1"]["required_fees_phone"]), ("35", "89"), "calls: pet rent and required fees by phone")
        eq((rows["b_2"]["elevator"], rows["b_2"]["elevator_basis"]), ("no", "confirmed_by_phone"), "calls: 'no elevator' on the phone outranks a confirmed yes")
        eq(called["b_1"], "2026-11-18T15:10:00-05:00", "calls: called_at kept per building")
        MU = pd.DataFrame({"listing_id": ["x:439", "x:477", "q:9"], "unit": ["439", "477", "9"], "unit_floor": ["", "4", "3"], "unit_floor_basis": ["unknown", "inferred", "stated"],
                           "unit_floor_source": ["", "unit number", "listing page"], "unit_floor_label_kind": ["complex", "simple", ""], "price_lease_months": ["15", "", ""],
                           "price_12_month": ["", "", ""], "price_lease_quote": ["", "", ""], "price_lease_source": ["", "", ""], "price_lowest_of_terms": ["", "yes", ""],
                           "live_status": ["", "live", "live"], "live_checked_at": ["", "t", "t"], "live_notes": ["", "seen", "seen"], "available_date": ["now", "now", "now"]}).astype(object)
        MU = BM.apply_call_answers_units(MU, ans).set_index("listing_id")
        eq((MU.at["x:439", "unit_floor"], MU.at["x:439", "unit_floor_basis"], MU.at["x:439", "unit_floor_source"]), (4, "confirmed_by_phone", "phone call 2026-11-18T15:10:00-05:00"), "calls: per-unit floor")
        eq((MU.at["x:477", "unit_floor"], MU.at["x:477", "unit_floor_basis"]), (1, "confirmed_by_phone"), "calls: a ground floor told on the phone lands (and rank.py then excludes it)")
        eq((MU.at["x:439", "price_lease_months"], MU.at["x:439", "price_12_month"], MU.at["x:477", "price_lowest_of_terms"]), (12, 2500.0, ""), "calls: lease term and 12-month price")
        eq((MU.at["x:439", "live_status"], MU.at["x:439", "available_date"], MU.at["x:477", "live_status"]), ("live", "2026-12-01", "gone"), "calls: move-in date offered, and 'gone'")
        eq((MU.at["q:9", "unit_floor_basis"], MU.at["q:9", "call_called_at"]), ("stated", ""), "calls: a unit nobody called about is untouched")
    ok(BM.PREC[0] == "confirmed_by_phone", "calls: confirmed_by_phone is first in the precedence order")
    # ---- step 6: a pending listing settled by a later evidence batch is gated on the settled fact
    import gates
    with tempfile.TemporaryDirectory() as td:
        pd.DataFrame([{"listing_id": "a:1", "verdict": "now_passes", "duplicate_of": "", "source_url": "https://www.zumper.com/x",
                       "how_settled": "elevator: Zumper amenity tag: Elevator [stated on the zumper page of the same building (cached harvest page)]"},
                      {"listing_id": "a:2", "verdict": "now_passes", "duplicate_of": "", "source_url": "u",
                       "how_settled": "elevator (asterisk, inferred): unit 1003 is listed on floor 10 [plan rule] ; dogs: allowed=true; allowed_pets=dogs/cats [dog policy on the apartmentlist.com page]; no weight limit stated"},
                      {"listing_id": "a:3", "verdict": "now_passes", "duplicate_of": "b:9", "source_url": "u", "how_settled": "elevator: Apartment List amenity list: Elevator"},
                      {"listing_id": "a:4", "verdict": "still_open (Is there a passenger elevator?)", "duplicate_of": "", "source_url": "u", "how_settled": ""}]).to_csv(Path(td) / "resolved_pending_batch_99.csv", index=False)
        L = pd.DataFrame({"listing_id": ["a:1", "a:2", "a:3", "a:4", "a:5"], "elevator": ["unknown"] * 5, "dogs": ["yes", "unknown", "yes", "yes", "yes"],
                          "dog_policy_text": [""] * 5, "notes": [""] * 5, "building_floors": [""] * 5, "floor": [""] * 5, "unit": ["VH-236", "305", "215", "2", "3"],
                          "dog_weight_limit_lb": [""] * 5})
        L = gates.apply_resolved_pending(L, folder=Path(td)).set_index("listing_id")
        eq((L.at["a:1", "elevator"], gates.gate_elevator(L.loc["a:1"])), ("yes", ("pass", "stated")), "pending: an elevator stated on a listing site's page of the building passes as stated")
        eq(gates.gate_elevator(L.loc["a:2"]), ("pass", "inferred_harvester"), "pending: an elevator inferred from height passes only as an inference (an open fact)")
        eq((L.at["a:2", "dogs"], gates.gate_dog(L.loc["a:2"])), ("yes", "pass"), "pending: a dog policy read on another page of the building")
        ok("allowed_pets=dogs/cats" in L.at["a:2", "dog_policy_text"], "pending: the dog policy text is kept")
        eq((L.at["a:3", "elevator"], L.at["a:4", "elevator"], L.at["a:5", "elevator"]), ("unknown", "unknown", "unknown"), "pending: duplicates, still-open rows and other listings are untouched")
        ok(L.at["a:1", "resolved_by"].startswith("resolved_pending_batch_99") and L.at["a:5", "resolved_by"] == "", "pending: resolved_by says which batch settled it")


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
    for lid in ["apartmentlist:p72935-A2839-5-02E", "apartmentlist:p372060-50-123"]:
        if lid in M.index:
            ok(m(lid, "elevator_evidence_open") != "", f"D7/D9: {lid} elevator must be open (elevators in select buildings only)")
    # 4c (owner, after the repair report): an elevator on a listing site's amenity tag alone is stated, not confirmed, and
    # settles the fact by rule; the reviewer's asterisk (townhomes; the owner's own list omits it) still keeps these two open
    for lid in ["apartmentlist:p98932510-00B-308", "apartmentlist:p90606231-431"]:
        if lid in M.index:
            ok(m(lid, "elevator_basis") in ("stated", "amenities_page") and m(lid, "elevator_aggregator_only") == "yes", f"4c: {lid} elevator is stated on a listing site only")
        if lid in R.index:
            ok("elevator" in R.at[lid, "confirm_what"], f"4c: {lid} keeps the reviewer's elevator asterisk")
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
    ok(not S.confirm_what.str.contains("cost near the cap|lease term|condo|floor").any(), "disclosures never count as the open gate fact")
    npub = S[~S.unit_floor_basis.isin(["confirmed", "stated"])]
    ok(npub.disclosures.str.contains('"what": "floor not published"', regex=False).all() and npub.tour_confirm.str.contains("above the ground floor").all(),
       "a shown unit whose floor is not published carries the disclosure and the tour question")
    ok(not (pd.to_numeric(S.unit_floor, errors="coerce") < 2).any(), "no shown unit on floor 1 or the ground floor")
    ok((S.open_gate_facts.astype(float) <= 1).all(), "a shown unit has at most one open gate fact")
    sk_ = pd.read_csv(DATA / "excluded_sketchy.csv", dtype=str, keep_default_na=False, low_memory=False)
    ok(not sk_.sketchy_reason.str.contains("cost near the cap|lease term|floor(?! plan)").any() or not sk_.sketchy_reason.str.contains("unconfirmed: [^;]*floor").any(), "no unit is dropped as sketchy because of a disclosure")
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
            ok(S.at[r.listing_id, "confirm_asterisk"] == "yes" or (r.kind in ("lease_term", "coop_condo", "other", "floor") and S.at[r.listing_id, "disclosures"] != ""),
               f"verdicts: {r.listing_id} has an asterisk verdict but is shown without an asterisk or a disclosure")
    ok(set(S.index) <= set(V[V.verdict.isin(["ok", "asterisk"])].listing_id), "verdicts: a shown unit has no ok / asterisk verdict")
    # 62 Treat St: plan "103" reads as floor 1; plan "208" must not be excluded with it
    X = pd.read_csv(DATA / "unit_exclusions.csv", dtype=str, keep_default_na=False)
    t = X[X.addr_key == "62 treat st|06516"]
    ok(not ((t.unit == "") & (t.listing_id == "")).any(), "62 Treat St must not be excluded as a whole building")
    ok(t.listing_id.str.contains("plan-103").any(), "62 Treat St plan 103 (reads as floor 1) is excluded by its listing id")
    # tolls (MTA rates filled): complete everywhere, the mail-rate figure beside the NY E-ZPass figure
    ok((M.toll_complete == "True").all(), f"tolls: toll_complete must be true on every unit ({(M.toll_complete != 'True').sum()} are not)")
    mail_, ez_ = pd.to_numeric(M.toll_rt_mail, errors="coerce"), pd.to_numeric(M.toll_rt_ezpass, errors="coerce")
    ok((mail_.isna() | (mail_ >= ez_)).all(), "tolls: a mail-rate figure is never below the NY E-ZPass figure")
    ok((mail_.notna() | ((M.toll_rt_mail_note != "") & (M.toll_rt_mail_subtotal != ""))).all(), "tolls: a missing mail-rate figure carries the reason and the subtotal of the known crossings")
    ok(pd.to_numeric(R.toll_rt_known, errors="coerce").notna().all(), "tolls: every ranked unit's toll is known to the distance score")
    data_more(M, R, S)
    # D20 (only when the page data is newer than the ranking)
    pj = ROOT / "site" / "data.json"
    if pj.exists() and pj.stat().st_mtime >= (DATA / "ranked_units.csv").stat().st_mtime:
        J = json.loads(pj.read_text())
        ok(any("New York E-ZPass" in n for n in J["meta"]["notes"]), "tolls: meta.notes must state the New York E-ZPass assumption")
        for u_ in J["units"]:
            sun = u_["moments"]["sun"]
            ok(sun["toll_complete"] or sun["toll_round_trip"] is None, f"tolls: {u_['id']} shows a toll figure for an incomplete route")
            ok(not sun["toll_complete"] or (sun["toll_round_trip"] is not None and (sun["toll_round_trip_mail"] is not None or sun["toll_round_trip_mail_at_least"] is not None)), f"tolls: {u_['id']} lacks the E-ZPass or mail figure")
            ok(sun["toll_round_trip_mail"] != 0 or sun["toll_round_trip"] == 0, f"tolls: {u_['id']} mail figure 0 while the E-ZPass figure is not")
        for h_ in J["neighborhoods"]:
            ok(h_["toll_complete"] or h_["toll_round_trip"] is None, f"tolls: neighborhood {h_['id']} shows a toll figure though a route is incomplete")
        page_more(J, M, R, S)
        txt = json.dumps(J)
        ok("North Plainfield is a beautiful subset of Somerset County" not in txt, "D20: the North Plainfield quote must not be on the page")
        ok("As the President of Jamaica Hill Community Association" not in txt, "D20: the quote naming its writer by office must not be on the page")
        vs = [v for h in J["neighborhoods"] for v in ((h.get("local") or {}).get("voices") or []) if isinstance(v, dict)]
        ok(not vs or any(v.get("about") for v in vs), "D20: quotes about a wider area carry 'about'")
        ok(not vs or all("source_area" in v for v in vs), "D20: source_area is kept on every quote")


def data_more(M, R, S):
    import pandas as pd
    # ---- Jersey City split
    jc = M[(M.city.str.lower() == "jersey city") & (M.state == "NJ")]
    ok(len(jc) > 0 and not (M.hood_id == "nj:jersey-city").any(), "split: no unit is left under the old id nj:jersey-city")
    ok(jc.hood_id.str.startswith("nj:jersey-city-").all() and jc.hood.str.startswith("Jersey City – ").all(), "split: every Jersey City unit has a neighborhood")
    ok((jc.hood_area == "Hudson County").all(), "split: hood_area stays the county")
    ok((M.hood_id == "nj:newark").any() and not M.hood_id.str.startswith("nj:newark-").any(), "split: Newark is not split")
    for key, want in [("110 hoboken ave|07310", "nj:jersey-city-downtown"), ("15 carbon pl|07305", "nj:jersey-city-west-side"),
                      ("176 w side ave|07305", "nj:jersey-city-west-side"), ("104 clifton pl|07304", "nj:jersey-city-mcginley-square")]:
        x = M[M.addr_key == key]
        ok(len(x) == 0 or (x.hood_id == want).all(), f"split: override {key} -> {want}")
    G = pd.read_csv(DATA / "lifestyle_groups.csv", dtype=str, keep_default_na=False)
    gj = G[G.hood_id.str.startswith("nj:jersey-city")]
    ok(len(gj) >= 5 and gj.violent.nunique() == 1 and gj.property.nunique() == 1, "split: every Jersey City neighborhood carries the one citywide police rate")
    ok((gj.safety_cut.str.lower() == "false").all(), "split: the safety rule uses the citywide rate (Jersey City passes), never the sub-city estimate")
    ok((gj.group_key != "").all(), "split: each Jersey City neighborhood is assigned to a lifestyle group")
    ref = pd.read_csv(DATA / "reference" / "lifestyle_fit_reference.csv", dtype=str, keep_default_na=False)
    ok((ref.hood_id == "nj:jersey-city").any() and not ref.hood_id.str.startswith("nj:jersey-city-").any(), "split: the lifestyle groups were not refitted (the fit reference still holds the one Jersey City row)")
    data_3(M, R, S)


def data_3(M, R, S):
    import pandas as pd
    import build_master as BM
    import rank
    # step 3: every restricted-town unit whose parking is not confirmed carries the disclosure; a disclosure never removes
    need = pd.Series([rank.needs_parking_disclosure(a, b, c) for a, b, c in zip(R.street_overnight_severity, R.parking_type, R.parking_fee)], index=R.index)
    has = R.disclosures.str.contains('"what": "overnight street parking"', regex=False)
    ok((need == has).all(), f"parking disclosure: on exactly the units that need it ({int((need != has).sum())} differ)")
    ok(R[has].disclosures.str.contains("Overnight street parking is restricted here: confirm the building has a space, and its cost", regex=False).all()
       and R[has].disclosures.str.contains('"url": "http', regex=False).all(), "parking disclosure: carries the question and the rule's source URL")
    ok("overnight street parking" not in " ".join(R.confirm_what), "parking disclosure: never an open gate fact")
    OP = pd.read_csv(DATA / "reference" / "overnight_parking_towns.csv", dtype=str, keep_default_na=False)
    LR = pd.concat([pd.read_csv(DATA / "reference" / f, dtype=str, keep_default_na=False) for f in ("local_rules.csv", "local_rules_round2.csv")])
    for r in OP.itertuples():
        ok(r.source_url in set(LR[LR.municipality == r.municipality].source_url), f"overnight parking table: {r.municipality}'s source URL is one of its rule rows' URLs")
        ok(r.severity in ("ban", "permit", "seasonal"), f"overnight parking table: {r.municipality} severity")
    # step 4a
    wl = pd.to_numeric(R.dog_weight_limit_lb, errors="coerce")
    un = (R.dog_weight_unstated != "") & wl.isna() & (R.dog_weight_limit_lb.str.lower() != "no limit")
    ok(R[un].tour_confirm.str.contains("Confirm the dog weight limit in pounds", regex=False).all(), "4a: a weight limit with no number carries the tour question")
    ok(R[un & (R.dog_size_only == "")].disclosures.str.contains('"what": "dog weight limit not published"', regex=False).all(), "4a: ... and the disclosure")
    # step 4b
    ok(not (R.listing_stale == "remove").any(), "4b: a listing page unchanged for more than six months is not ranked")
    st = S[S.listing_stale == "open"]
    ok(st.confirm_what.isin(["listing", "availability"]).all(), "4b: a shown unit whose page is over 60 days unchanged carries that as its one open item")
    # step 4c
    ok(not ((M.elevator_aggregator_only == "yes") & M.elevator_basis.isin(["confirmed", "official_record", "confirmed_by_phone", "community_page"])).any(),
       "4c: an elevator known only from listing sites is never 'confirmed'")
    # step 5: with no call file, nothing claims a phone basis
    if not BM.CALL_ANSWERS.exists():
        ok(not M.elevator_basis.eq("confirmed_by_phone").any() and not M.unit_floor_basis.eq("confirmed_by_phone").any() and (M.call_called_at == "").all(),
           "calls: no call file, so no fact may claim a phone basis")
    data_4(M, R, S)


def data_4(M, R, S):
    pass


def page_more(J, M, R, S):
    hs = [h for h in J["neighborhoods"] if h["id"].startswith("nj:jersey-city")]
    ok(hs and all(h.get("parent_id") == "nj:jersey-city" and h["area"] == "Hudson County" for h in hs), "split: Jersey City neighborhoods carry parent_id and the county")
    for h in hs:
        sf = h["safety"]
        ok("citywide police rate" in (sf.get("basis") or ""), f"split: {h['id']} safety must say it is the citywide rate")
        est = sf.get("subcity_estimate")
        ok(est is not None and est["used_for_safety_rule"] is False and "estimate" in est["label"] and est["value_type"] == "estimate", f"split: {h['id']} sub-city crime is a labelled estimate, context only")
        vs = (h.get("local") or {}).get("voices") or []
        ok(all(v_.get("about") for v_ in vs if "Jersey City" in (v_.get("source_area") or "") and h["short_name"] not in (v_.get("source_area") or "")), f"split: citywide quotes on {h['id']} are labelled")
        ok((h.get("local") or {}).get("parking_rules"), f"split: {h['id']} inherits Jersey City's parking rules")
        ok(all(r_.get("about") == "Jersey City as a whole" for r_ in h["local"]["parking_rules"] if r_.get("municipality") == "Jersey City"), f"split: inherited rules on {h['id']} are labelled")
        for sv in (h.get("local") or {}).get("survey") or []:
            sa = sv.get("source_area") or ""
            ok(not ("Square" in sa and h["short_name"] not in sa), f"split: a survey row for {sa} must not sit on {h['id']}")
        if h.get("prose") and h["prose"].get("inherited_from"):
            ok(h["prose"].get("about") == "Jersey City as a whole", f"split: inherited scene text on {h['id']} is labelled")
    page_3(J, M, R, S)


def page_3(J, M, R, S):
    pass


if __name__ == "__main__":
    (data if "--data" in sys.argv else pure)()
    print(f"test_rules {'(data)' if '--data' in sys.argv else '(rules)'}: {N[0]} checks, {len(FAILS)} failed")
    for f in FAILS:
        print("  FAIL", f)
    sys.exit(1 if FAILS else 0)
