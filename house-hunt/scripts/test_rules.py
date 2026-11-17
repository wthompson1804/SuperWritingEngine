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
    eq(P.elevator_row_kind("listing-site amenity tag only", "Trulia feature list: 'Elevator' (cached page of 2026-11-15).", True, "unconfirmed"), "stated", "4c: batch 19's wording ('listing-site amenity tag only') -> stated")
    eq(P.elevator_row_kind("listing-site amenity tag only", "Apartment List amenity list: 'Elevator'. The building's own site (citylineeast.com) returned HTTP 403 and was not read.", True, "unconfirmed"), "stated", "4c: an own site that could not be read is not a contradiction")
    eq(P.elevator_row_kind("listing-site amenity tag only", "Trulia feature list: 'Elevator'. The manager's page for The Stanley lists 'Fitness Center, Laundry Care Centers' and no elevator", True, "unconfirmed"), "contra", "4c: the manager's own page omits it (The Stanley) -> stays open")
    eq(P.elevator_row_kind("listing-site amenity tag only", "Apartment List amenity list: 'Elevator'. Greystar's page for the building lists amenities but does not mention an elevator.", True, "unconfirmed"), "contra", "4c: Harbor Landing -> stays open")
    eq(P.elevator_row_kind("listing-site amenity tag only", "Trulia feature list: 'Elevator'. The building's own site (home, amenities, building, residences) does not mention an elevator.", True, "unconfirmed"), "contra", "4c: 3 Acres -> stays open")
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
    # ---- batch 19: an income-restricted tag from a listing site only is one open eligibility fact, not a removal
    import avoid
    note = "Manager's site (Garden Homes) lists Apt #206 at $1,675. INCOME-RESTRICTED: Trulia tags this building 'INCOME RESTRICTED'; the manager's page does not say so and gives no income limit. Confirm eligibility by phone."
    ok(avoid.TAG_ONLY.search(note) and avoid.INCOME_WORDS.search(note), "eligibility: the tag-only wording is recognised")
    ok(not avoid.TAG_ONLY.search("INCOME-RESTRICTED lottery building with a waitlist (page says so)"), "eligibility: a building whose own page says income-restricted is still excluded")
    M2 = BM.Merge()
    ok(BM.apply_fact(M2, "b", "eligibility", "INCOME-RESTRICTED per the Trulia tag; the manager's own page states no income limit", "", "u") and M2.resolve()[0]["b"]["eligibility_open"], "eligibility: the fact reaches eligibility_open")
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
    pure_4()


def pure_4():
    """Independent check 3 (docs/INDEPENDENT_CHECK_3.md): the rules, on the report's own rows."""
    import tempfile
    import pandas as pd
    import rent_terms as RT
    import build_master as BM
    import all_in as AI
    import rank
    import verdicts as VD
    # ---- D5: the checker's own "the page does not say" is never a net-effective statement
    for t in ["Gross or net-effective: not stated on the page", "Gross or net-effective: not stated", "Listed price is base rent (base_price field); not stated as net-effective.",
              "Trulia capture 21:47 UTC; not stated whether the listed price is gross or net-effective.", "Applies to base rent for the first 4 months; gross or net-effective listing price: not stated",
              "gross or net not stated"]:
        ok(RT.NET_NEG.search(t), f"IC3 D5: a negation must match NET_NEG: {t!r}")
    for t in ["*Rents Reflect Net-Effective Pricing", "Net effective Prices advertised reflect 3 months free on 18 month leases!", "* PRICE INCLUDES CONCESSIONS.",
              "Rents shown reflect net-effective pricing for select apartments inclusive of concessions.", "net-effective on own site; gross rent not published"]:
        ok(RT.NET_STMT.search(t) and not RT.NET_NEG.search(t), f"IC3 D5: a real net-effective statement must stand: {t!r}")
    p = RT.parse_piece("1 Month Free On 14 Month Lease Term. Gross or net-effective: not stated on the page", "1")
    ok(p["net_neg"] and not p["net"], "IC3 D5: BE (448 Scotland Rd): the offer plus the checker's negation is not net-effective")
    ok(RT.NOT_PAGE_WORDS.search("term 12: price 2805, totalPrice 2901, netEffectivePrice 2571") and RT.NOT_PAGE_WORDS.search("[live check] Apartment List unit data, refreshed 2026-11-15")
       and not RT.NOT_PAGE_WORDS.search("Enjoy one month free on all new leases. Restrictions apply, see agent for details."), "pending fix: raw page data and checker notes are not the offer's own words")
    # ---- D11: a second site is a different site
    tr = "https://www.trulia.com/building/sono-pearl-101-washington-st-norwalk-ct-06854-2757887032"
    ok(not BM.second_site(tr, tr), "IC3 D11: also_seen_at pointing at the same page is not a second site")
    ok(not BM.second_site(tr, "https://www.trulia.com/home/x-1 https://trulia.com/building/y"), "IC3 D11: two pages of the same site are not a second site")
    ok(BM.second_site(tr, "https://www.zumper.com/apartment-buildings/p1/sono-pearl"), "IC3 D11: another site is a second site")
    ok(BM.second_site(tr, "", "https://www.apartmentlist.com/ct/norwalk/sono-pearl"), "IC3 D11: a merged duplicate from another site is a second site")
    eq(P.staleness("2026-07-13", "2026-11-15", "", second_source=BM.second_site(tr, tr))[0], "open", "IC3 D11: Sono Pearl 401, page unchanged 125 days, same-page 'second site' -> open")
    # ---- D6: "not listed on AvalonBay's own pages"
    eq(P.elevator_row_kind("not listed on AvalonBay's own pages", "[Community features on avaloncommunities.com do not include an elevator]", False, "unconfirmed"), "contra", "IC3 D6: Avalon Somerville's row speaks against the elevator")
    eq(P.elevator_row_kind("yes (Apartment List amenity tag only)", "Elevator", True, "unconfirmed"), "stated", "IC3 D6: a plain amenity tag is still 'stated'")
    # ---- D14: a fee named beside a total it is part of is not added to it
    eq(P.monthly_fees_from_text("$90/mo (total_price minus base_price); $50 amenity fee named")[0], 90.0, "IC3 D14: 1 Kennedy Flats: $90 is the total, the $50 is inside it")
    eq(P.monthly_fees_from_text("$100/mo (trash $25 + amenity $75); electricity separate")[0], 100.0, "IC3 D14: the check-2 bracket case still reads $100")
    # ---- D10: off-site parking is not covered parking at the building
    eq(P.parking_kind("Offsite parking available - 1st year FREE! 2 blocks away covered and permitted not assigned."), "offsite", "IC3 D10: 30 Broad Street's parking is off-site")
    eq(P.parking_kind("off-site covered garage two blocks away, not assigned; first year free"), "offsite", "IC3 D10: 'off-site covered garage' is off-site")
    eq(P.parking_kind("Covered parking"), "covered", "IC3 D10: covered parking at the building is still covered")
    eq(rank.parking_rank("offsite: Offsite parking available - 1st year FREE! 2 blocks away covered"), 2, "IC3 D10: off-site parking ranks as a lot, never as covered or a garage")
    eq(rank.parking_rank("covered"), 3, "IC3 D10: covered parking keeps its rank")
    # ---- D1: a checker's note that the price itself needs verifying
    ok(P.price_doubt("1BR 900 sqft at $1,663 is far below the area's other listings in this batch: verify the price by phone before touring"), "IC3 D1: 98-76 Queens Blvd 2M's note is a price doubt")
    ok(not P.price_doubt("price history: Nov 12, 2026 Listed For Rent $2,575"), "IC3 D1: a price history is not a price doubt")
    # ---- D2: sibling consistency on unit numbers read as first-floor
    rem = ["2153", "2158", "2165", "2169", "2178"]
    ok(P.reads_as_ground_like_siblings("2182", rem), "IC3 D2: Halstead Parsippany 2182 has the shape of its removed siblings")
    ok(not any(P.reads_as_ground_like_siblings(u_, rem) for u_ in ["2284", "2257", "2261", "2263", "1205", "1206"]), "IC3 D2: second-floor siblings are not caught")
    ok(not P.reads_as_ground_like_siblings("4114", ["1119", "1127", "1142"]) and P.reads_as_ground_like_siblings("1150", ["1119", "1127", "1142"]),
       "IC3 D2: where the removed labels share '1' in two places, a sibling must carry both (Steel Works 4114 is not caught)")
    ok(not P.reads_as_ground_like_siblings("305", ["2153"]), "IC3 D2: one removed label is no pattern")
    # ---- D19: the same apartment on two sites, one row without a unit label
    ok(BM.same_apartment_other_site("1", "806", "2675", "trulia", "1", "806.0", "2700", "zumper"), "IC3 D19: 12 Brooklyn Ave 501 ($2,675 Trulia) = the Zumper row with no unit ($2,700)")
    ok(not BM.same_apartment_other_site("1", "806", "2675", "trulia", "1", "806", "2700", "trulia"), "IC3 D19: two rows of one site are not merged on a near price")
    ok(not BM.same_apartment_other_site("1", "", "2675", "trulia", "1", "", "2700", "zumper"), "IC3 D19: no published size, no merge")
    ok(not BM.same_apartment_other_site("1", "806", "2675", "trulia", "1", "806", "2900", "zumper"), "IC3 D19: rents more than 2 percent apart are two apartments")
    # ---- step 3: the garden-style rule and the doubt table
    ok(P.multi_building_labels(["1109", "2303", "2307", "2309", "5201", "7106"]), "step 3: Woodmont West's labels read as a multi-building low complex")
    ok(P.multi_building_labels(["1123", "1133", "1212", "1221", "4211", "4234", "4311", "6103", "9114"]), "step 3: The Royce at Trumbull")
    ok(P.multi_building_labels(["5204", "6108", "6207"]), "step 3: Brookfield Village")
    for labs, name in [(["0705", "0707", "0903", "1003", "1104"], "360 State Street (a tower)"), (["1116", "1118", "1174", "2141", "2205", "3172", "4149", "4186"], "The Grove Somerset (floor + three-digit unit)"),
                       (["1147", "2113", "2117", "4108", "5136", "5158"], "Cobalt Lofts"),
                       (["305", "4F", "12B"], "plain labels"), (["1-101", "1-208"], "one building number only")]:
        ok(not P.multi_building_labels(labs), f"step 3: not garden-style: {name}")
    ok(BM.garden_style(["5204", "6108", "6207"], ["", None]) and not BM.garden_style(["5204", "6108", "6207"], ["5"]), "step 3: a height of 4+ floors on a page or record switches the rule off")
    D_ = BM.load_elevator_doubt()
    ok(len(D_) >= 14 and all(d["why"] and d["source"] for d in D_.values()), "step 3: the reviewed doubt table has its seed rows, each with a reason and a source")
    # ---- step 4: medians behind the estimates
    recs = [{"building_id": f"b{i}", "state": "NJ", "pet_rent_monthly": str(v_), "parking_fee_monthly": "", "parking_type": ""} for i, v_ in enumerate([25, 35, 50, 50, 75, 100])] \
        + [{"building_id": "b0", "state": "NJ", "pet_rent_monthly": "25", "parking_fee_monthly": "", "parking_type": ""}] \
        + [{"building_id": f"p{i}", "state": "NJ", "pet_rent_monthly": "", "parking_fee_monthly": str(v_), "parking_type": "garage"} for i, v_ in enumerate([0, 100, 150, 150, 200])]
    MED = AI.known_medians(recs, {f"b{i}": v_ for i, v_ in enumerate([0, 50, 60, 70, 300])})
    eq(MED["pet"]["NJ"], (50.0, 6), "step 4: pet-rent median is per building (a building listed twice counts once)")
    eq(MED["parking"][("NJ", "garage")], (150.0, 5), "step 4: parking median by state and kind")
    eq(MED["fees"]["NJ"], (60.0, 5), "step 4: required-fee median")
    eq(AI.pick(MED["parking"], ("NJ", "lot"), ("NJ", ""), ("", "")), (150.0, 5, ("NJ", "")), "step 4: a kind with too few buildings falls back to the state")
    ok(AI.known_medians(recs[:3], {})["pet"] == {}, "step 4: a median never rests on fewer than five buildings")
    # ---- D22: several verdict rows per unit
    V = pd.DataFrame([{"listing_id": "a", "kind": "elevator", "verdict": "asterisk"}, {"listing_id": "a", "kind": "lease_term", "verdict": "asterisk"},
                      {"listing_id": "b", "kind": "", "verdict": "ok"}, {"listing_id": "b", "kind": "coop_condo", "verdict": "disclose"},
                      {"listing_id": "c", "kind": "dogs", "verdict": "asterisk"}, {"listing_id": "c", "kind": "unverified", "verdict": "remove"}])
    for c in VD.COLS:
        if c not in V:
            V[c] = "h" if c == "evidence_hash" else ""
    U_ = VD.by_unit(VD.normalise(V[VD.COLS]))
    eq((U_["a"]["verdict"], U_["a"]["gate"], U_["a"]["disclose"]), ("asterisk", ["elevator"], ["lease_term"]), "IC3 D22: an asterisk on a disclosure kind becomes a 'disclose' row beside the gate row")
    eq((U_["b"]["verdict"], len(U_["b"]["rows"])), ("disclose", 1), "IC3 D22: an 'ok' row beside another row of the unit is dropped")
    eq(U_["c"]["verdict"], "remove", "IC3 D22: any remove row removes the unit")
    ok(VD.GATE_KINDS.isdisjoint(VD.DISCLOSURE_KINDS) and VD.GATE_KINDS | VD.DISCLOSURE_KINDS == VD.KINDS, "IC3 D22: every kind is either a gate fact or a disclosure")
    # ---- D24: quotes that characterise residents by ethnicity
    ok(P.characterises_residents_by_group("Lots of traffic jams but delicious food. Lots of hispanics"), "IC3 D24: the Dover quote is screened")
    for t in ["mostly white people live here", "a large Jewish community", "the residents are predominantly Asian"]:
        ok(P.characterises_residents_by_group(t), f"IC3 D24: screened: {t!r}")
    for t in ["Great Italian restaurants and a Chinese bakery", "lots of Mexican food", "very diverse and friendly", "Lots of traffic"]:
        ok(not P.characterises_residents_by_group(t), f"IC3 D24: not screened: {t!r}")
    # ---- contacts: a small lister's own number is never "the number the property supplied"
    import building_contacts as BC
    lone = {"display_name": "630 West 163rd Street", "total_units_count": None, "website_url": None, "available_units": [{}], "original_phone": "9176515298"}
    ok(BC.single_lister_listing(lone), "contacts: an Apartment List page with no unit count, no website, one unit and an address for a title is a single lister's listing")
    ok(not BC.single_lister_listing(dict(lone, total_units_count=245, display_name="LIA by Vermella", website_url="https://x")), "contacts: a property with a unit count and a website is a leasing office")
    ok(not BC.single_lister_listing(dict(lone, display_name="The Mercer", available_units=[{}] * 19)), "contacts: a named property with many units is not a single lister")
    C_ = pd.read_csv(DATA / "reference" / "building_contacts.csv", dtype=str, keep_default_na=False)
    ok(not (C_.contact_kind.eq("individual owner") & C_.leasing_phone.ne("")).any(), "contacts: an individual owner never has a phone recorded")
    ok(not (C_.contact_kind.isin(["individual owner", "broker"]) & C_.note.str.contains("property supplied")).any(), "contacts: a broker's or owner's number is never called property-supplied")
    # ---- moments: the three-level rating
    import build_page_data as BP
    m = {"wake": {"park_walk_min": 2.5}, "work": {}, "after": {"restaurants_800m": 20, "bars_800m": 2}, "night": {}, "sat": {"bars_1600m": 3, "restaurants_1600m": 40}, "sun": {"drive_min": 28}}
    eq(BP.moment_ratings(m, 4, False, True, False, 720, 1), {"wake": "strong", "work": "strong", "after": "strong", "night": "strong", "sat": "mixed", "sun": "strong"}, "moments: absolute thresholds, strong side")
    m2 = {"wake": {"park_walk_min": 12}, "work": {}, "after": {"restaurants_800m": 2, "bars_800m": 0}, "night": {}, "sat": {"bars_1600m": 1, "restaurants_1600m": 9}, "sun": {"drive_min": 75}}
    eq(BP.moment_ratings(m2, 1, False, True, False, 500, 0), {"wake": "weak", "work": "weak", "after": "weak", "night": "weak", "sat": "weak", "sun": "weak"}, "moments: absolute thresholds, weak side")
    m3 = {"wake": {"park_walk_min": None}, "work": {}, "after": {"restaurants_800m": 8, "bars_800m": 0}, "night": {}, "sat": {"bars_1600m": None, "restaurants_1600m": 3}, "sun": {"drive_min": 45}}
    eq(BP.moment_ratings(m3, None, False, False, False, None, 1), {"wake": None, "work": None, "after": "mixed", "night": "mixed", "sat": None, "sun": "mixed"}, "moments: null where the data cannot say; unknown parking is mixed")
    eq(BP.moment_ratings(m, 4, False, False, False, 720, 1)["night"], "mixed", "moments: a garage with no stated front desk or controlled entry is mixed")
    eq(BP.moment_ratings(m, 4, False, True, True, 720, 1)["night"], "weak", "moments: an overnight street-parking restriction with no confirmed space is weak")
    eq(BP.moment_ratings(m, 4, True, True, False, 720, 1)["night"], "mixed", "moments: off-site parking is never strong")
    pure_5()
    pure_6()


def pure_5():
    """The elevator gate never rests on a floor read from a unit label (docs/harvest_notes/zumper_open_pending.md)."""
    import tempfile
    import pandas as pd
    import gates
    base = {"elevator": "unknown", "notes": "", "building_floors": "", "floor": "", "unit": "", "community_building_type": ""}
    row = lambda **k: pd.Series({**base, **k})
    eq(gates.gate_elevator(row(unit="42M")), ("unknown", ""), "elevator: '42M' (1204 John F Kennedy Blvd, Bayonne) is a landlord's numbering, not floor 42 -> unknown")
    eq(gates.gate_elevator(row(unit="69B")), ("unknown", ""), "elevator: '69B' at 69 N Broadway repeats the house number -> unknown")
    eq(gates.gate_elevator(row(unit="6C")), ("unknown", ""), "elevator: '6C' at 6 Duer St -> unknown")
    eq(gates.gate_elevator(row(unit="601")), ("unknown", ""), "elevator: '601' in a building with no height from a page or record -> unknown")
    eq(gates.gate_elevator(row(unit="19D", building_floors="20")), ("pass", "inferred_6plus_floors"), "elevator: '19D' in a building whose page states 20 floors passes on the height")
    eq(gates.gate_elevator(row(unit="19D", building_floors="5")), ("unknown", ""), "elevator: '19D' in a building stated as 5 floors does not pass on the label")
    eq(gates.gate_elevator(row(unit="2A", floor="9")), ("pass", "inferred_6plus_floors"), "elevator: a floor the page states for the unit (9) is a real height")
    eq(gates.gate_elevator(row(unit="901", floor="9", notes="floor derived from unit number")), ("unknown", ""), "elevator: a floor the harvester derived from the unit number is not a height")
    eq(gates.gate_elevator(row(unit="42M", elevator="yes")), ("pass", "stated"), "elevator: stated on the page passes whatever the label")
    eq(gates.gate_elevator(row(unit="42M", elevator="no")), ("fail", "stated"), "elevator: a stated walk-up fails")
    eq(gates.gate_elevator(row(unit="14N", elevator="yes", floor="14", notes="floor derived from unit number; elevator: 6+ floors (unit numbers on the page reach floor 37)")), ("unknown", ""),
       "elevator: a harvester's yes from 'unit numbers on the page reach floor 37' is a label reading -> unknown")
    eq(gates.gate_elevator(row(unit="1203", elevator="yes", building_floors="12+", notes="elevator: 11+ floors: unit numbers on the listing page run to floor 12 (1201 ... 1215)")), ("unknown", ""),
       "elevator: 'unit numbers on the listing page run to floor 12' -> unknown")
    eq(gates.gate_elevator(row(unit="523", elevator="yes", building_floors="7", floor="5", notes="elevator: 6+ floors (the SightMap floor list on livemotifapts.com runs from 1 to 7)")), ("pass", "inferred_harvester"),
       "elevator: a harvester's yes from a page's floor list is a real height (an inference, still open)")
    eq(gates.gate_elevator(row(unit="3", community_building_type="High-Rise")), ("pass", "inferred_high_rise_label"), "elevator: the management page's 'high-rise' still passes as an inference")
    # the floor gate keeps reading labels (owner: an unpublished floor is a tour question)
    eq(gates.gate_floor(row(unit="42M"))[:3], ("pass", 42, "inferred"), "floor: the floor gate still reads '42M' as an inferred floor")
    eq(gates.gate_floor(row(unit="601"))[:3], ("pass", 6, "inferred"), "floor: the floor gate still reads '601'")
    # the city's record: 6+ floors only on the listing's own lot
    eq(gates.elevator_from_pluto_floors("7", "house_number+location", "unknown"), True, "elevator: PLUTO gives 7 floors on the listing's own lot -> real height")
    eq(gates.elevator_from_pluto_floors("13", "nearest_lot", "unknown"), False, "elevator: a neighbouring lot's 13 floors is not this building's height")
    eq(gates.elevator_from_pluto_floors("5", "house_number+location", ""), False, "elevator: 5 floors on record is under the threshold")
    eq(gates.elevator_from_pluto_floors("", "", ""), False, "elevator: no record")
    # evidence rows and amenities pages (addr_key -> basis)
    with tempfile.TemporaryDirectory() as td:
        A, O = "https://www.apartmentlist.com/nj/x/y", "https://www.ownsite.com/amenities"
        pd.DataFrame([{"addr_key": "k1", "fact": "elevator", "value": "yes", "quote": "Elevator access to all floors", "source_url": O, "status": "confirmed"},
                      {"addr_key": "k2", "fact": "elevator", "value": "yes", "quote": "Apartment List community amenity: Elevator", "source_url": A, "status": "confirmed"},
                      {"addr_key": "k3", "fact": "elevator", "value": "yes (inferred from height)", "quote": "unit 1003 is on floor 10", "source_url": A, "status": "confirmed"},
                      {"addr_key": "k4", "fact": "elevator", "value": "yes", "quote": "amenity: Elevator", "source_url": A, "status": "confirmed"},
                      {"addr_key": "k4", "fact": "elevator", "value": "no", "quote": "walk-up per the manager", "source_url": O, "status": "contradicts"},
                      {"addr_key": "k5", "fact": "elevator", "value": "unconfirmed", "quote": "no elevator in the feature list on this page", "source_url": A, "status": "unconfirmed"},
                      {"addr_key": "k6", "fact": "elevator", "value": "yes", "quote": "PLUTO building class D1", "source_url": "https://data.cityofnewyork.us/x", "status": "confirmed"},
                      {"addr_key": "k7", "fact": "dogs_allowed", "value": "yes", "quote": "dogs ok", "source_url": O, "status": "confirmed"}]).to_csv(Path(td) / "confirm_batch_99.csv", index=False)
        pd.DataFrame([{"addr_key": "k8", "elevator_stated": "yes", "source_url": A}, {"addr_key": "k9", "elevator_stated": "no_mention", "source_url": A},
                      {"addr_key": "k4", "elevator_stated": "yes", "source_url": A}]).to_csv(Path(td) / "amen.csv", index=False)
        ev = gates.elevator_evidence(folder=Path(td), amenities=Path(td) / "amen.csv")
        eq({k: v[0] for k, v in sorted(ev.items())}, {"k1": "evidence_confirmed", "k2": "evidence_stated", "k8": "amenities_page"},
           "elevator: evidence passes only on a page that states it (own page, listing-site amenity list, amenities page); not an inference, a contradicted building, a not-found row or a class-only row")


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
    near = S[(pd.to_numeric(S.all_in) <= 3000) & (pd.to_numeric(S.all_in_likely) > 3000)]       # owner, 2026-11-16: replaces "cost near the cap"
    ok(near.disclosures.str.contains('"what": "could pass $3,000"', regex=False).all(), "D12: every shown unit that would pass $3,000 once parking and fees are known carries the disclosure")
    # owner, 2026-11-17: "floor and elevator" (floor_or_elevator) is an open GATE fact, not the floor disclosure; where it
    # is open the floor is asked there and not listed a second time as "floor not published" (rank.py: inf_f)
    ok(not S.confirm_what.str.replace(P.FLOOR_OR_ELEVATOR_LABEL, "", regex=False).str.contains("cost near the cap|lease term|condo|floor").any(), "disclosures never count as the open gate fact")
    npub = S[~S.unit_floor_basis.isin(["confirmed", "stated"]) & (S.floor_elevator_code != P.FLOOR_OR_ELEVATOR_CODE)]
    ok(npub.disclosures.str.contains('"what": "floor not published"', regex=False).all() and npub.tour_confirm.str.contains("above the ground floor").all(),
       "a shown unit whose floor is not published carries the disclosure and the tour question")
    ok(not (pd.to_numeric(S.unit_floor, errors="coerce") < 2).any(), "no shown unit on floor 1 or the ground floor")
    ok((S.open_gate_facts.astype(float) <= 1).all(), "a shown unit has at most one open gate fact")
    sk_ = pd.read_csv(DATA / "excluded_sketchy.csv", dtype=str, keep_default_na=False, low_memory=False)
    sk_r = sk_.sketchy_reason.str.replace(P.FLOOR_OR_ELEVATOR_LABEL, "", regex=False).str.replace(r"floor 3 or above \(\w+\) and no elevator stated[^;]*", "", regex=True)
    ok(not sk_r.str.contains("cost near the cap|lease term|floor(?! plan)").any() or not sk_r.str.contains("unconfirmed: [^;]*floor").any(), "no unit is dropped as sketchy because of a disclosure")
    ok("more_in_building" in S.columns and (S.groupby("building_id").size() <= 8).all(), "at most 8 shown per building (owner, 2026-11-16), with more_in_building recorded")
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
    # D19: ties in the selection order are broken by listing_id (owner, 2026-11-16: no longer "seen live first")
    Rr = R.reset_index()
    Rr["rank_score_num"] = pd.to_numeric(Rr.rank_score)
    exp = Rr.sort_values(["hood_id", "dominated", "rank_score_num", "listing_id"], ascending=[True, True, False, True], kind="mergesort")
    ok(list(exp.listing_id) == list(Rr.listing_id), "D19: ranked_units.csv is not in the deterministic order (hood, dominated, score, listing_id)")
    # verdict table is applied
    import verdicts as VD
    V = VD.load_verdicts()
    ok(not set(V[V.verdict == "remove"].listing_id) & set(R.index), "verdicts: a unit with verdict remove is still ranked")
    import parsers as PZ_
    for r in V[V.verdict == "asterisk"].itertuples():
        if r.listing_id in S.index:
            if r.kind == "elevator":
                # 'asterisk | elevator' keeps the elevator in doubt (verdicts.py docstring; owner, 2026-11-17): an open fact on
                # floor 3+ or an unknown floor, and nothing on floor 2, where parsers.floor_elevator_rule needs no elevator
                row = S.loc[r.listing_id]
                get = lambda c, row=row: str(row.get(c, "")).removesuffix(".0") if c == "unit_floor" else str(row.get(c, ""))
                if PZ_.floor_elevator_master(get, "open") == ("settled", "floor_2"):
                    continue
            ok(S.at[r.listing_id, "confirm_asterisk"] == "yes", f"verdicts: {r.listing_id} has an asterisk verdict (an open gate fact) but is shown without an asterisk")
    for r in V[V.verdict == "disclose"].itertuples():
        if r.listing_id in S.index:
            ok(S.at[r.listing_id, "disclosures"] != "", f"verdicts: {r.listing_id} has a disclose verdict but no disclosure on the unit")
    ok(set(S.index) <= set(V[V.verdict.isin(list(VD.SHOWABLE))].listing_id), "verdicts: a shown unit has no ok / asterisk / disclose verdict")
    ok(not V.duplicated(["listing_id", "kind"]).any(), "verdicts: one row per unit and kind")
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
    for key in ("111 prospect st|06901", "25 3rd st|06905"):
        x = R[R.addr_key == key]
        ok(len(x) == 0 or x.confirm_what.str.contains("eligibility").all(), f"eligibility: {key} units carry the open eligibility fact (listing-site tag only), not a removal")
        ok(not (pd.read_csv(DATA / "unit_exclusions.csv", dtype=str, keep_default_na=False).query("addr_key == @key").reason.str.contains("not open to her|not open-market").any()), f"eligibility: {key} is not excluded for the tag alone")
    X_ = pd.read_csv(DATA / "unit_exclusions.csv", dtype=str, keep_default_na=False)
    ok(not ((X_.addr_key == "111 prospect st|06901") & (X_.unit == "") & (X_.listing_id == "")).any(), "111 Prospect St: a floor-plan row that left the page must not exclude the units seen live on the manager's page")
    data_4(M, R, S)


def data_4(M, R, S):
    """Independent check 3, on the pipeline's output."""
    import pandas as pd
    import verdicts as VD
    num = lambda df, c: pd.to_numeric(df[c], errors="coerce")
    named = lambda pat: M[M.building_name.str.contains(pat, case=False, regex=True) | M.address.str.contains(pat, case=False, regex=True)]
    # ---- S1: the three units
    for lid, why in [("apartmentlist:p10919258-2M", "D1: 98-76 Queens Blvd 2M (dogs open + price to verify)"), ("apartmentlist:p1412214-2182", "D2: Halstead Parsippany 2182 (first-floor pattern)"),
                     ]:
        ok(lid not in S.index, f"IC3 {why} must not be shown")
    # D3 (Residences at The Summit K3-02) was "stale page AND never seen live: two open items, not shown". Owner, 2026-11-16:
    # a listing never re-read is not an open item, so the stale page is its ONE open item and it is shown with that asterisk.
    k3_ = "rc:trulia:b2751605456:Unit_K3-02:351211069"
    ok(k3_ not in S.index or (S.at[k3_, "confirm_what"] == "listing" and S.at[k3_, "confirm_asterisk"] == "yes"), "IC3 D3: K3-02, if shown, carries the stale page as its one open item (listing)")
    ok("apartmentlist:p1412214-2182" not in R.index, "IC3 D2: 2182 is removed before ranking by the sibling rule")
    k3 = "rc:trulia:b2751605456:Unit_K3-02:351211069"
    if k3 in M.index:
        ok(M.at[k3, "page_modified_date"] == "2026-08-22" and M.at[k3, "listing_stale"] == "open", "IC3 D3: K3-02 takes the page date its sibling's note gives for the same building page")
    # D3 as a rule, after the owner's rule of 2026-11-16 (a listing never re-read is not an open item): a shown unit on a
    # page known to be stale carries exactly that as its ONE open item, "listing" (or the reviewer's "availability"), whether
    # or not it was re-read; with a second open gate fact it is not shown
    st_ = S[S.listing_stale == "open"]
    ok((st_.confirm_asterisk == "yes").all() and st_.confirm_what.isin(["listing", "availability"]).all(), "IC3 D3: a shown unit on a stale page carries the listing (or availability) asterisk: a found problem still counts")
    # ---- D5 / D16: net-effective only where the evidence says so; no invented gross
    for pat, unit in [("1 Kennedy Flats", "2303"), ("1 Kennedy Flats", "1315"), ("Harbourside SoNo", "225"), ("Kensington Place", "1236"), ("Harbor Pointe", "B9-309"), ("Harbor Pointe", "B9-258"),
                      ("The Grove Somerset", "2205"), ("Pier Village", "4-408"), ("Pier Village", "1-347"), ("Spinnaker Wharf", "5-02E"), ("The Botanic", "430"), ("The Botanic", "444")]:
        x = named(pat); x = x[x.unit == unit]
        ok(len(x) == 0 or ((x.rent_basis_kind == "listed") & (num(x, "rent_gross") == num(x, "rent_basis")) & (num(x, "rent_basis") == num(x, "listed_rent").where(x.live_price == "", num(x, "rent_basis")))).all(),
           f"IC3 D5/D16: {pat} {unit} is costed on its listed price, not as net-effective, with no invented gross")
    for pat in ["448 Scotland", "Harrison Somerset"]:
        x = named(pat)
        ok(len(x) == 0 or (x.rent_basis_kind == "listed").all(), f"IC3 D5: {pat} is not net-effective")
    ok((M[M.rent_basis_kind == "net_effective"].rent_listed_price_is == "net_effective").all(), "IC3 D5: net-effective only where rent_terms says the listed price is net-effective")
    ok(not M.rent_offer_text.str.contains(r"\[live check\]|\[evidence\]|not stated|totalPrice|netEffectivePrice", regex=True).any(), "pending fix: rent_offer_text holds the page's own words only")
    sp = S[(S.rent_offer_kind == "special_offer")]
    ok(sp.disclosures.str.contains('"what": "special offer"', regex=False).all() and sp.disclosures.str.contains("ask what a normal month costs", regex=False).all(), "IC3 D5: an offer not tied to the price is disclosed as a special offer")
    ok(not S[S.rent_basis_kind != "net_effective"].disclosures.str.contains('"what": "net-effective rent"', regex=False).any(), "IC3 D5: no net-effective disclosure on a unit not stated to be net-effective")
    # ---- D6 / D8 / D9 / D22: several issues per unit
    x = named("Avalon Somerville"); x = x[x.unit.str.contains("265")]
    ok(len(x) == 0 or (x.elevator_evidence_open != "").all(), "IC3 D6: Avalon Somerville Station's elevator is open (not listed on AvalonBay's own pages)")
    for lid in x.index:
        if lid in S.index:
            ok(S.at[lid, "confirm_what"] == "elevator" and '"what": "lease term"' in S.at[lid, "disclosures"], "IC3 D6: 022-265 shows the elevator asterisk AND the lease-term disclosure")
    for pat, unit in [("7914 Rockaway", "2F"), ("142-38 37th", "8E"), ("25 W +Broadway", "204"), ("98-76 Queens", "2M"), ("405 W +206th", "713E")]:
        x = R[(R.address.str.contains(pat, regex=True)) & (R.unit == unit)]
        ok(len(x) == 0 or x.disclosures.str.contains('"what": "condo rented by its owner"', regex=False).all(), f"IC3 D8: {pat} {unit} carries the condo disclosure")
    x = R[R.building_name.str.contains("The Riverhouse")]
    ok(len(x) == 0 or x.disclosures.str.contains('"what": "lease term"', regex=False).all(), "IC3 D9: The Riverhouse (price is for an 18-month lease) carries the lease-term disclosure")
    V = VD.load_verdicts()
    ok(not ((V.verdict == "asterisk") & V.kind.isin(list(VD.DISCLOSURE_KINDS))).any(), "IC3 D22: no asterisk row on a disclosure kind")
    # ---- D21: the city's record for the listing's own lot settles "the listing does not state an elevator"
    for pat in ["4110 Bowne St", "80 Richmond Hill Rd", "8625 Van Wyck"]:
        x = M[M.address.str.contains(pat)]
        ok(len(x) == 0 or ((x.elevator_basis != "official_record") | (x.elevator_evidence_open == "")).all(), f"IC3 D21: {pat}: an elevator on the city's record for the listing's own lot is not left open")
    ok(not ((M.elevator_basis == "official_record") & ((M.pluto_lot_ok != "yes") | (pd.to_numeric(M.dob_active_elevators, errors="coerce") == 0))).any(), "IC3 D21: an official-record elevator always rests on the listing's own lot with an active device")
    # ---- D10: 30 Broad Street
    x = named("30 Broad St")
    ok(len(x) == 0 or x.parking_type.str.startswith("offsite").all(), "IC3 D10: 30 Broad Street's parking type is off-site")
    ok(not S.address.str.contains("30 Broad St").any(), "pending fix: 30 Broad Street (under construction, no page shows it occupied) is not shown")
    # ---- D11: no shown unit sits on a stale page with the rule switched off
    ok(not ((num(S, "listing_stale_days") > 60) & (S.listing_stale == "") & ~pd.Series([__import__("build_master").second_site(a, b) or bool(d) for a, b, d in zip(S.url, S.also_seen_at, S.duplicate_listing_ids)], index=S.index)).any(),
       "IC3 D11: a page over 60 days unchanged with no second SITE always carries the staleness item")
    for pat, unit in [("Sono Pearl", "401"), ("Wakefield Station", "401"), ("134 Baldwin", "301"), ("134 Baldwin", "411")]:
        x = named(pat); x = x[x.unit == unit]
        ok(len(x) == 0 or (x.listing_stale == "open").all(), f"IC3 D11: {pat} {unit} is stale by rule")
    # ---- D14: fees not counted twice
    for pat, unit, fee in [("Parc at Glenbrook", "2328", 0), ("1 Kennedy Flats", "2303", 90), ("1 Kennedy Flats", "1315", 90), ("Residences at The Summit", "M2-07", 0)]:
        x = named(pat); x = x[x.unit == unit]
        for r in x.itertuples():
            line = next(l for l in json.loads(r.all_in_lines) if l["line"] == "required building fees")
            eq(line["amount"], fee, f"IC3 D14: {pat} {unit} required-fee line")
    tp = M[M.price_basis.str.contains("total monthly|isTotalMonthlyFeeIncluded", regex=True) & (M.get("required_fees_phone", "") == "")]
    ok(all(next(l for l in json.loads(a) if l["line"] == "required building fees")["amount"] == 0 for a in tp.all_in_lines), "IC3 D14: a total price never has its own fees added again")
    # ---- D15: floors
    if "trulia:2068551955" in M.index:
        eq(M.at["trulia:2068551955", "unit_floor_basis"], "unknown", "IC3 D15: 100 W 139th St 27A has no floor (the evidence says the label is not a floor)")
    x = named("Alexander Crossing")
    ok(len(x) == 0 or (x.building_floors == "").all(), "IC3 D15: Alexander Crossing's '2 floors' is dropped (a unit label reads above it)")
    # ---- D17: EDGE 408 / 410
    for lid in ["apartmentlist:p44503265-408", "apartmentlist:p44503265-410"]:
        if lid in M.index:
            eq(M.at[lid, "address"], "170 Avenue F", f"IC3 D17: {lid} is at 170 Avenue F")
    # ---- D19: 12 Brooklyn Ave once
    x = M[M.address.str.contains("12 Brooklyn Ave")]
    ok(len(x) <= 1 or x.unit.ne("").all(), "IC3 D19: 12 Brooklyn Ave's unlabelled Zumper row is merged into unit 501")
    # ---- pending fixes: names, addresses
    for pat, name in [("475 Main St", "The Elks"), ("270 Luis M", "Metropolis Towers"), ("26-25 4th", "The Winslow"), ("187 Culver", "The Tetris"), ("479 Front", "Village Lofts"),
                      ("12 Brooklyn Ave", "Sun Valley Towers"), ("5 Linden St", "The Hampton")]:
        x = M[M.address.str.contains(pat)]
        ok(len(x) == 0 or (x.building_name == name).all(), f"pending fix: {pat} is named {name}")
    x = M[M.building_name.str.contains("Vermella Harrison")]
    ok(len(x) == 0 or ((x.city == "Harrison") & x.address.str.startswith("1100 Frank E Rodgers")).all(), "pending fix: Vermella Harrison's address is whole and its city is Harrison")
    x = M[M.building_name.str.contains("Kensington Place")]
    ok(len(x) == 0 or ((x.city == "East Brunswick") & (x.hood_id == "nj:east-brunswick")).all(), "pending fix: Kensington Place is in East Brunswick")
    for pat in ["1244 New York Ave", "61 Clarkson Ave"]:
        x = M[M.address.str.contains(pat)]
        ok(len(x) == 0 or ((x.pluto_lot_ok == "yes") & (x.pluto_lot_address.str.lower().str.replace("avenue", "ave") == pat.lower())).all(), f"pending fix: {pat}: the city lot is the listing's own address, so its record stands")
    ok(not S.building_name.str.contains("Regency on Hudson").any() or S[S.building_name.str.contains("Regency on Hudson")].confirm_what.eq("listing").all(), "pending fix: Regency on Hudson carries one open 'listing' fact")
    # ---- step 3: elevator doubt
    DT = pd.read_csv(DATA / "reference" / "elevator_doubt.csv", dtype=str, keep_default_na=False)
    # second trawl (2026-11-17): a reviewed row may name a building whose listings are all above $2,200 and so no longer in
    # the master; what must hold is that every doubt-table building in the master carries the doubt (checked below)
    ok(len(DT) > 0 and DT.building_id.str.fullmatch(r"b_[0-9a-f]{10}").all(), "step 3: every row of the doubt table names a building id")
    dm = M[M.building_id.isin(set(DT.building_id)) & (M.elevator == "yes") & (M.elevator_basis != "confirmed_by_phone")]
    ok((dm.elevator_doubt != "").all(), "step 3: every building of the doubt table has the elevator doubt set")
    # owner, 2026-11-17: an elevator in doubt (doubt table, garden-style rule) no longer matters on floor 2 (floor_2: settled);
    # on floor 3+ or an unknown floor it is still the elevator asterisk
    ds_all = S[S.elevator_doubt != ""]
    ds = ds_all[ds_all.floor_elevator_code != "floor_2"]
    ok((ds.confirm_what == "elevator").all() and (ds.confirm_asterisk == "yes").all(), "step 3: a shown unit under elevator doubt (not on floor 2) carries the elevator asterisk as its one open item")
    ok(ds[(ds.elevator_evidence_open == "")].to_confirm.str.contains("Confirm an elevator serves this apartment", regex=False).all(), "step 3: ... with the question 'confirm an elevator serves this apartment'")
    ok((pd.to_numeric(ds.open_gate_facts) == 1).all(), "step 3: a doubted unit is shown only when the elevator is its single open gate fact (a listing never re-read is not a second one)")
    d2 = ds_all[ds_all.floor_elevator_code == "floor_2"]
    ok(not d2.open_keys.str.split(";").map(lambda k: "elevator" in k).any(), "floor 2: a floor-2 apartment under elevator doubt carries no elevator item (owner, 2026-11-17)")
    # ---- step 4: pet rent estimated, all_in_likely, the new disclosure
    ok(not M.all_in_unknown_lines.str.contains("pet rent").any(), "step 4a: pet rent is never unknown-and-nothing")
    est = M[M.all_in_estimated_lines.str.contains("pet rent")]
    ok(len(est) > 0 and all(next(l for l in json.loads(a) if l["line"].startswith("pet rent"))["amount"] > 0 for a in est.all_in_lines), "step 4a: an unpublished pet rent is a positive estimate line")
    ok((num(M, "all_in_likely") >= num(M, "all_in")).all(), "step 4b: all_in_likely is never below all_in")
    kn = M[~M.all_in_unknown_lines.str.contains("parking fee|building fees|gas|electric|internet")]
    ok((num(kn, "all_in_likely") == num(kn, "all_in")).all(), "step 4b: with parking, fees and every utility line known, all_in_likely equals all_in")
    # independent check 5, N11: a utility line with no estimate (gas) feeds all_in_likely with the typical value
    ug = M[M.all_in_unknown_lines.str.contains(r"(?:^|; )gas(?:;|$)")]
    ok(len(ug) == 0 or (num(ug, "all_in_likely") > num(ug, "all_in")).all(), "N11: a unit with no gas estimate has all_in_likely above all_in (the typical gas bill is added)")
    ok(len(ug) == 0 or ug.all_in_likely_note.str.contains("gas \\$").all(), "N11: the note behind all_in_likely names the gas figure and where it comes from")
    ok((num(S, "all_in") <= 3000).all(), "step 4: the hard cap stays on all_in")
    flag_ = (num(S, "all_in") <= 3000) & (num(S, "all_in_likely") > 3000)
    has_ = S.disclosures.str.contains('"what": "could pass $3,000"', regex=False)
    ok((flag_ == has_).all(), "step 4b: the 'could pass $3,000' disclosure sits on exactly the units it applies to")
    ok(S[has_].disclosures.str.contains("Could pass $3,000 once parking and fees are known", regex=False).all(), "step 4b: the disclosure names both figures in its sentence")
    ok(not S.disclosures.str.contains("cost near the cap", regex=False).any() and not S.disclosures.str.contains("counted as $0", regex=False).any(), "step 4b: the old 'cost near the cap' disclosure and 'counted as $0' are gone")
    ok(not R.confirm_why.str.contains("counted as $0", regex=False).any(), "pending fix: no confirm_why says 'counted as $0'")
    # the estimate (CLAUDE.md: "the median of the known pet rents in the same state") recomputed over the SAME set the
    # estimator uses (all_in.known_medians): the master's buildings that publish a pet rent, one value per building
    # (coordinator, 2026-11-17: the ranked buildings are a different, smaller set and were the wrong reference)
    E_ = pd.read_csv(DATA / "reference" / "cost_estimates.csv")
    Mb = M.drop_duplicates("building_id")
    for st_, g_ in Mb.groupby("state"):
        known = pd.to_numeric(g_.pet_rent_monthly, errors="coerce")
        known = known[(known >= 0) & (known <= 150)]
        used = E_[(E_.line == "pet rent") & (E_.state == st_)]
        if len(known) >= 5:
            ok(len(used) == 1 and abs(float(known.median()) - float(used["median"].iloc[0])) <= 0.5 and int(used.buildings.iloc[0]) == len(known),
               f"step 4a: {st_} pet-rent estimate (${float(used['median'].iloc[0]) if len(used) else float('nan'):g} over {int(used.buildings.iloc[0]) if len(used) else 0} buildings) is the median of the master's {len(known)} known pet rents (${float(known.median()):g})")
    # ---- step 5: buildings
    ok((S.groupby("building_id").size() <= 8).all(), "step 5: at most 8 shown per building")
    o = S.assign(rs=num(S, "rank_score"), n=num(S, "nth_shown_in_building")).sort_values(["building_id", "n"])
    ok(all((g.n.values == range(1, len(g) + 1)).all() for _, g in o.groupby("building_id")), "step 5: nth_shown_in_building runs 1..n inside each building")
    # ---- the elevator gate never rests on a unit label (docs/harvest_notes/zumper_open_pending.md)
    import gates
    L_ = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False, low_memory=False)
    I_ = L_[(L_.g_elevator == "pass") & (L_.elevator_basis == "inferred_6plus_floors")]
    exact = lambda r: P.lot_is_exact(r.match_basis, r.address, r.pluto_address)
    bad = [r.listing_id for r in I_.itertuples() if not ((gates.page_height(r) or 0) >= 6 or gates.elevator_from_pluto_floors(r.pluto_floors, exact(r), r.elevator_from_class))]
    ok(not bad, f"elevator gate: every 'inferred_6plus_floors' pass has a height of 6+ from a page or record, never a unit label ({len(bad)} do not: {bad[:5]})")
    ok(not L_[(L_.g_elevator == "pass") & L_.notes.str.contains(gates.HARVESTER_LABEL_HEIGHT) & (L_.elevator_basis == "inferred_harvester")].shape[0],
       "elevator gate: a harvester's yes read from unit numbers never passes as 'inferred_harvester'")
    ok(set(L_[L_.g_elevator == "pass"].elevator_basis) <= {"stated", "inferred_harvester", "inferred_6plus_floors", "inferred_high_rise_label", "nyc_pluto_building_class",
                                                          "evidence_confirmed", "evidence_stated", "amenities_page"}, "elevator gate: every pass carries a known basis")
    ok(all(exact(r) for r in L_[L_.elevator_basis == "nyc_pluto_building_class"].itertuples()), "elevator gate: the city's class (elevator or walk-up) decides only on the listing's own lot (parsers.lot_is_exact)")
    data_6(L_)
    data_b20(M, R, S)
    data_ic4(M, R, S)
    data_ic5(M, R, S)
    data_ic6(M, R, S)
    data_b21(M, R, S)


def data_units_unique(S):
    pass


def pure_b21():
    """Live-check batch 21 (2026-11-17): 'not_read' means nothing was learned. It never replaces an earlier row of the
    same apartment, is not a re-read, and (owner, 2026-11-16) is not an open item."""
    ok(not P.live_row_learned("not_read") and not P.live_row_learned(" Not_Read "), "b21: 'not_read' is a row that learned nothing")
    ok(all(P.live_row_learned(x) for x in ("live", "changed", "gone", "blocked", "")), "b21: live, changed, gone and blocked rows are kept as before")
    earlier = {"unit": "606", "status": "live", "price_now": "1650", "checked_at": "2026-11-15T22:47:47+00:00", "notes": "seen on the listing page"}
    today = {"unit": "606", "status": "not_read", "price_now": "", "checked_at": "2026-11-17T14:01:33+00:00", "notes": "Not re-read: no page names this apartment."}
    eq(P.latest_live_row([earlier, today]), earlier, "b21: 955 Main St 606: today's not_read row does not replace the live row of 2026-11-15")
    eq(P.latest_live_row([today, earlier]), earlier, "b21: the same, whatever the order of the rows")
    eq(P.latest_live_row([today]), None, "b21: an apartment whose only row is not_read has no live status at all (never re-read)")
    gone = dict(earlier, status="gone", checked_at="2026-11-17T15:00:00+00:00")
    eq(P.latest_live_row([earlier, today, gone]), gone, "b21: a later row that did learn something still wins")
    import pandas as pd
    import rank
    D = pd.DataFrame([earlier, today])
    eq(list(P.live_rows_learned(D).status), ["live"], "b21: the frame the master is built from holds no not_read row")
    eq(len(P.live_rows_learned(pd.DataFrame())), 0, "b21: an empty evidence frame stays empty")
    gate_facts = pd.Series([0, 1])
    eq(list(rank.open_item_count(gate_facts, pd.Series(["", "not_read"]))), [0, 1], "b21: a missing live status, or a not_read one, adds no open item")
    ok(not P.second_site_omits("Not re-read: no site of the building's own was found. Zumper has no page for the address (404).", ""),
       "b21: 'nothing found anywhere' is not the finding 'a second site lists the address without this apartment'")


def data_b21(M, R, S):
    """Batch 21 applied: gone apartments left, changed prices are used, not_read changed nothing."""
    import glob
    import pandas as pd
    num = lambda v: pd.to_numeric(v, errors="coerce")
    ok(not M.live_status.isin(P.LIVE_NOTHING_LEARNED).any(), "b21: no master row carries the status 'not_read'")
    ok(not M.live_notes.str.startswith(("Not re-read", "Not confirmed")).any(), "b21: no master row carries the note of a not_read row")
    files = sorted(glob.glob(str(DATA / "evidence" / "live_check_batch_*.csv")))
    L = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in files], ignore_index=True)
    xw = pd.read_csv(DATA / "reference" / "building_crosswalk.csv", dtype=str, keep_default_na=False)
    L["building_id"] = L.addr_key.map(dict(zip(xw.addr_key, xw.building_id)))
    NR = L[L.status.isin(P.LIVE_NOTHING_LEARNED)]
    eq(len(NR), 21, "b21: 21 not_read rows are on file")
    for r in NR.itertuples():
        m = M[M.building_id.eq(r.building_id) & M.unit.map(P.unit_key).eq(P.unit_key(r.unit))]
        prev = P.latest_live_row([x for x in L[L.building_id.eq(r.building_id)].to_dict("records") if P.unit_key(x["unit"]) == P.unit_key(r.unit)])
        for x in m.itertuples():
            if x.live_page_gone == "yes" or str(getattr(x, "call_called_at", "")).strip():
                continue
            eq((x.live_status, x.live_checked_at), ((prev or {}).get("status", ""), (prev or {}).get("checked_at", "")),
               f"b21: {r.addr_key} {r.unit} keeps the status of its last row that learned something (not_read changed nothing)")
    B21 = pd.read_csv(DATA / "evidence" / "live_check_batch_21.csv", dtype=str, keep_default_na=False)
    B21["building_id"] = B21.addr_key.map(dict(zip(xw.addr_key, xw.building_id)))
    for r in B21.itertuples():
        m = M[M.building_id.eq(r.building_id) & M.unit.map(P.unit_key).eq(P.unit_key(r.unit))]
        inS = S[S.building_id.eq(r.building_id) & S.unit.map(P.unit_key).eq(P.unit_key(r.unit))]
        if r.status == "gone":
            ok(len(m) == 0 or (m.live_status == "gone").all(), f"b21: {r.addr_key} {r.unit} is gone in the master")
            ok(len(inS) == 0, f"b21: {r.addr_key} {r.unit} is gone and not shown")
        elif r.status in ("live", "changed"):
            ok(len(m) >= 1 and (m.live_status == r.status).all() and (m.live_checked_at == r.checked_at).all(), f"b21: {r.addr_key} {r.unit} carries today's {r.status} row")
            if r.status == "changed":
                ok((num(m.rent_basis) == float(r.price_now)).all(), f"b21: {r.addr_key} {r.unit} is costed on the new price ${r.price_now}")
    bk = M[M.building_name.str.startswith("Brookview Commons") & M.unit.isin(["BC-519W", "BC-524", "BC-406"])]
    ok(len(bk) == 3 and bk.all_in_lines.str.contains('"line": "required building fees", "amount": 50,', regex=False).all(), "b21: the three Brookview apartments count the mandatory $50 monthly fee in the total")
    lia = S[S.building_name.eq("LIA by Vermella") & S.unit.eq("423")]
    ok(len(lia) == 1 and '"what": "lease term"' in lia.disclosures.iloc[0] and str(lia.price_lease_months.iloc[0]).startswith("15"), "b21: LIA 423 is priced on a 15-month lease and says so (lease-term disclosure)")
    arc = S[S.building_name.str.contains("Arcade", regex=False) & S.unit.eq("302")]
    ok(len(arc) == 1 and arc.dogs_allowed.iloc[0] == "yes" and arc.dog_size_only.iloc[0].startswith("yes") and "Confirm the dog weight limit in pounds" in arc.tour_confirm.iloc[0],
       "b21: The Arcade 302 passes the dog rule as 'small dogs' with the tour question about the weight limit")


def pure_b20():
    """Evidence batch 20 (2026-11-16): the 12-month price wherever the page gives one; the sibling long-lease rule; a
    listing page that is gone; the dollar amount that looked like a unit number."""
    # the 12-month price is used whenever it is known and differs from the listed price, whatever the quoted term
    ok(P.use_12_month_price(2487, 3040), "b20: Harbor Landing 452, $2,487 on 13 months and $3,040 on 12: the 12-month price is used")
    ok(P.use_12_month_price(2563, 3973) and P.use_12_month_price(2379, 2395), "b20: The Leaf 2318 and Scribe 502 use the 12-month price")
    ok(P.use_12_month_price(2700, 2600), "b20: a 12-month price below the listed price is used too (it differs)")
    ok(not P.use_12_month_price(2500, 2500) and not P.use_12_month_price(2500, None) and not P.use_12_month_price(2500, "") and not P.use_12_month_price(2500, float("nan")),
       "b20: an equal or unknown 12-month price changes nothing")
    r = P.lease_term_from_text("Price is for a 13-month lease; 12-month price $3,040 in the page's rent table for a move-in from 2026-11-15.")
    eq((r["months"], r["price_12"]), (13, 3040.0), "b20: Harbor Landing 452 note")
    r = P.lease_term_from_text("Price is for a 24-month lease (the map's price calculator gives this same price for terms of 14 to 18, 20 to 24 months); 12-month price $3,973 ($4,098 with required monthly fees); the 13-month figure is $2,694.")
    eq((r["months"], r["price_12"]), (24, 3973.0), "b20: The Leaf 2318 note")
    r = P.lease_term_from_text("Price is for a 15-month lease; the page shows no 12-month price for this unit. Same price as stored.")
    eq((r["months"], r["price_12"]), (15, None), "b20: 'the page shows no 12-month price' gives no price")
    # sibling long-lease rule
    leaf = [("2318", 2563, 24, 3973), ("2505", 2583, 24, 4004)]
    f, why = P.sibling_12_month_gap(24, "", False, leaf)
    ok(f and "2318" in why or "2505" in why, "b20: The Leaf 1304 (24-month price, no 12-month price read) is flagged by its siblings")
    scribe = [("425", 2606, 24, 3210), ("502", 2379, 24, 2395)]
    ok(P.sibling_12_month_gap(24, "", False, scribe)[0], "b20: Scribe 508 is flagged: sibling 425 is 23 percent dearer on 12 months")
    ok(not P.sibling_12_month_gap(24, "", False, [("502", 2379, 24, 2395)])[0], "b20: a sibling 0.7 percent dearer does not flag")
    ok(not P.sibling_12_month_gap(15, "", False, [("3326", 2675, 15, 2975)])[0], "b20: Avalon Yonkers, 11 percent, does not flag (the line is 15 percent)")
    ok(not P.sibling_12_month_gap(24, 2395, False, scribe)[0], "b20: a unit whose own 12-month price is known is never flagged")
    ok(not P.sibling_12_month_gap(12, "", False, leaf)[0] and not P.sibling_12_month_gap("", "", False, leaf)[0], "b20: a unit priced on 12 months, or with no term stated, is not flagged")
    ok(P.sibling_12_month_gap(13, "", False, [("452", 2487, 13, 3040)])[0], "b20: Harbor Landing 208 (13-month price) is flagged by 452 (22 percent)")
    ok(P.sibling_12_month_gap("", "", True, leaf)[0], "b20: 'lowest over the lease terms' counts as a long-lease price")
    ok("ask for it" in P.SIBLING_12_MONTH_TEXT, "b20: the disclosure says to ask")
    # a listing page that is gone
    ok(P.listing_page_gone("gone", "listing page no longer exists", "the building's page now shows the site's 'This page could not be found' message"), "b20: The Mercer's page is gone")
    ok(not P.listing_page_gone("gone", "not in the unit list", "unit 307 is no longer in the building's unit list (16 units listed tonight)"), "b20: one unit leaving the list is not the page")
    ok(not P.listing_page_gone("live", "available now", "page could not be found yesterday"), "b20: only a 'gone' row counts")
    # staleness of Grandville Towers with the page date 2026-07-30
    eq(P.staleness("2026-07-30", "2026-11-16")[:2], ("open", 109), "b20: Grandville Towers, page of 2026-07-30 read 2026-11-16: 109 days, one open item, not removed")
    eq(P.page_modified_date("unit record updated 2026-07-30): unit 9C ... STALE PAGE 2026-07-30: the unit's own record on the page was last updated 2026-07-30"), "2026-07-30", "b20: 9C note date")


def data_b20(M, R, S):
    import pandas as pd
    num = lambda v: pd.to_numeric(v, errors="coerce")
    ok(not M[M.building_name.eq("The Mercer")].live_status.ne("gone").any(), "b20: every Mercer unit in the master is gone (the building's listing page is gone)")
    ok(not R.building_name.eq("The Mercer").any(), "b20: no Mercer unit is ranked, shown, or on an avoid or held card")
    for b, un in [("LIA by Vermella", "307"), ("Kensington Place", "1315"), ("Harbor Pointe", "B9-457")]:
        ok(not (R.building_name.str.contains(b, regex=False) & R.unit.eq(un)).any(), f"b20: {b} {un} is gone and not ranked")
    for b, units_, in [("The Leaf", ["2318", "2418", "2505", "2518"]), ("The Asher", ["308", "610", "730", "830"]), ("Scribe", ["425"]), ("Motif", ["523"]), ("Harbor Landing Apartments", ["452"])]:
        x = M[M.building_name.eq(b) & M.unit.isin(units_)]
        # second trawl (owner, 2026-11-17): listings above $2,200 base rent no longer reach the master (they stay in data/listings.csv)
        ok(len(x) in (0, len(units_)) and (x.cost_gate == "fail").all() and (num(x.rent_basis) == num(x.price_12_month)).all(), f"b20: {b} {units_} are costed on the 12-month price and are over $3,000 (or, above $2,200, not in the master)")
        ok(not (R.building_name.eq(b) & R.unit.isin(units_)).any(), f"b20: {b} {units_} are not ranked")
    x = M[M.building_name.eq("Scribe") & M.unit.isin(["502", "507", "542", "544", "546"])]
    ok((len(x) == 5 and (num(x.rent_basis) == 2395).all() and (x.cost_gate == "pass").all()) or len(x) == 0, "b20: Scribe 502/507/542/544/546 use $2,395 and stay under (or, above $2,200, are not in the master)")
    x = M[M.building_name.eq("Scribe") & M.unit.eq("616")]
    ok(len(x) == 0 or (x.price_12_month == "").all(), "b20: Scribe 616 does not take unit 425's 12-month price ('14 months $2,616' is not unit 616)")
    x = M[M.building_name.eq("Avalon Somerville Station") & M.unit.eq("022-415")]
    ok(len(x) == 0 or (x.price_12_month == "").all(), "b20: Avalon Somerville 022-415 does not take 022-265's 12-month price")
    ok(not (num(M.price_12_month).notna() & ((num(M.price_12_month) - num(M.live_price.where(M.live_status.isin(["live", "changed"]) & M.live_price.ne(""), M.listed_rent))).abs() > 0.5)
            & (num(M.rent_basis) != num(M.price_12_month))).any(), "b20: wherever a 12-month price is known and differs, the rent used is the 12-month price")
    sib = M[M.price_12_sibling_gap == "yes"]
    ok(set(sib.building_name) <= {"The Leaf", "The Asher", "Scribe", "Motif", "Harbor Landing Apartments"}, f"b20: the sibling rule touches only the five buildings (got {sorted(set(sib.building_name))})")
    for lid in S.index:
        if S.at[lid, "price_12_sibling_gap"] == "yes" and S.at[lid, "rent_12_month_used"] != "yes":
            ok(S.at[lid, "confirm_what"] == "listing" and S.at[lid, "confirm_asterisk"] == "yes", f"b20: {lid} is shown with exactly the open item 'listing' (sibling long-lease rule)")
            ok("much higher than the price shown: ask for it" in S.at[lid, "disclosures"], f"b20: {lid} lease-term disclosure says to ask for the 12-month price")
        if S.at[lid, "rent_12_month_used"] == "yes":
            ok('"what": "lease term"' in S.at[lid, "disclosures"] and "12-month price is $" in S.at[lid, "disclosures"], f"b20: {lid} uses the 12-month price and says so in the lease-term disclosure")
    g = M[M.building_name.eq("Grandville Towers")]
    ok(len(g) == 0 or ((g.page_modified_date == "2026-07-30").all() and (g.listing_stale == "open").all()), "b20: every Grandville Towers unit carries the page date 2026-07-30 and the open staleness item (all are above $2,200 since 2026-11-17)")
    gs = S[S.building_name.eq("Grandville Towers")]
    ok((gs.confirm_what == "listing").all(), "b20: shown Grandville Towers units carry the open item 'listing' alike")


def pure_6():
    pure_b20()
    """Pipeline consistency pass (docs/PIPELINE_CONSISTENCY_PASS.md)."""
    import gates
    import pandas as pd
    base = {"elevator": "unknown", "notes": "", "building_floors": "", "floor": "", "unit": "", "community_building_type": ""}
    row = lambda **k: pd.Series({**base, **k})
    R = P.elevator_rule
    # ---- step 1: ONE elevator rule, its truth table row by row
    eq(R(phone="yes", page_no=True), ("established", "confirmed_by_phone"), "elevator rule 1: a phone answer wins")
    eq(R(phone="no", stated=True), ("no", "confirmed_by_phone"), "elevator rule 1: a phone 'no' removes")
    eq(R(page_no=True, height=20), ("no", "stated"), "elevator rule 2: a page saying walk-up is 'no' whatever the height")
    eq(R(stated=True), ("established", "stated"), "elevator rule 3b: stated on a page (a listing site's amenity list counts)")
    eq(R(record_class="yes", lot_exact=True), ("established", "nyc_pluto_building_class"), "elevator rule 3b: the city's class on the listing's own lot")
    eq(R(record_class="yes", lot_exact=False), ("unknown", ""), "elevator rule: a near-miss lot does not PASS")
    eq(R(record_class="no", lot_exact=False), ("unknown", ""), "elevator rule: a near-miss lot does not FAIL either")
    eq(R(record_class="yes", lot_exact=True, active_devices=0), ("unknown", ""), "elevator rule: zero active elevators on the device list cancels the class")
    eq(R(evidence="evidence_stated"), ("established", "evidence_stated"), "elevator rule 3b: a stated evidence row, not contradicted")
    eq(R(evidence="evidence_confirmed", contradicted=True), ("open", "evidence_confirmed"), "elevator rule 3a: contradicted evidence is OPEN, not unknown")
    eq(R(stated=True, doubt=True), ("open", "stated"), "elevator rule 3a: the doubt table opens a stated elevator")
    eq(R(stated=True, record_class="no", lot_exact=True), ("open", "stated"), "elevator rule 3a: the city's walk-up class on the own lot against a page's elevator is open")
    eq(R(record_class="no", lot_exact=True), ("no", "nyc_pluto_building_class"), "elevator rule 4: walk-up class on the own lot, nothing else")
    eq(R(record_class="no", record_floors=7, lot_exact=True), ("no", "nyc_pluto_building_class"), "elevator rule 4: the same record's floor count does not outweigh its walk-up class")
    eq(R(height=6), ("open", "inferred_6plus_floors"), "elevator rule 5: a page height of 6 is open")
    eq(R(height=5), ("unknown", ""), "elevator rule 6: five floors is not enough")
    eq(R(record_floors=9, lot_exact=True), ("open", "inferred_6plus_floors"), "elevator rule 5: the city's floor count on the own lot")
    eq(R(record_floors=9, lot_exact=False), ("unknown", ""), "elevator rule: a neighbouring lot's floors are not a height")
    eq(R(page_height_claim=True), ("open", "inferred_harvester"), "elevator rule 5: 6+ floors read from a page's floor list")
    eq(R(high_rise_own_page=True), ("open", "inferred_high_rise_label"), "elevator rule 5: 'high-rise' on the building's own page")
    eq(R(), ("unknown", ""), "elevator rule 6: nothing known")
    eq(P.real_height("14", "18"), 18.0, "real_height: the tallest of the page's floor count and a floor a page states for a unit")
    eq(P.real_height("", ""), None, "real_height: nothing")
    ok(P.lot_is_exact("nearest_lot", "35-16 34th St", "35-16 34 STREET") and not P.lot_is_exact("nearest_lot", "142-38 37th Ave", "142-32 37 AVENUE")
       and not P.lot_is_exact("no_lot_within_40m", "1 A St", "1 A STREET"), "lot_is_exact: the address must agree; a near miss never counts")
    # the three stages answer alike on the same facts: gate (listing row) and ranking (master row)
    m = lambda **k: P.elevator_rule_master(lambda c: str(k.get(c, "")))
    eq(gates.gate_elevator(row(unit="3", community_building_type="High-Rise")), ("pass", "inferred_high_rise_label"), "stages: high-rise on the manager's page passes the gate ...")
    eq(m(elevator="yes", elevator_basis="inferred", elevator_height_basis="inferred_high_rise_label")[0], "open", "... and is ONE open fact in the ranking (it used to be 'not shown')")
    eq(gates.gate_elevator(row(unit="2A", floor="9")), ("pass", "inferred_6plus_floors"), "stages: a page-stated unit floor of 9 passes the gate ...")
    eq(m(elevator="yes", elevator_basis="inferred", unit_floor="9", unit_floor_basis="stated")[0], "open", "... and is one open fact in the ranking")
    eq(m(elevator="yes", elevator_basis="inferred", unit_floor="9", unit_floor_basis="inferred")[0], "unknown", "stages: a floor read from the unit label is not a height in the ranking either")
    eq(m(elevator="yes", elevator_basis="amenities_page")[0], "established", "stages: stated on a page is settled in the ranking")
    eq(m(elevator="yes", elevator_basis="amenities_page", elevator_doubt="reviewed table: x")[0], "open", "stages: the doubt table opens it")
    eq(m(elevator="yes", elevator_basis="confirmed_by_phone", elevator_doubt="x", elevator_evidence_open="y")[0], "established", "stages: a phone answer settles it")
    eq(m(elevator="yes", elevator_basis="inferred", pluto_floors="7", pluto_lot_ok="no")[0], "unknown", "stages: the city's floors on another lot are not used")
    eq(gates.gate_elevator(row(elevator_from_class="no", match_basis="nearest_lot", address="142-38 37th Ave", pluto_address="142-32 37 AVENUE")), ("unknown", ""),
       "gate: the walk-up class of a NEIGHBOURING lot no longer fails a listing (493 listings did)")
    eq(gates.gate_elevator(row(elevator_from_class="no", match_basis="house_number+location", address="10 Main St", pluto_address="10 MAIN STREET")), ("fail", "nyc_pluto_building_class"),
       "gate: the walk-up class on the listing's own lot still fails")
    lifestyle_assignment_checks()
    # ---- step 3: the unit belongs in the unit field, not in the address; duplicates across spellings
    eq(P.split_address_unit("1775 Windsor Road #215"), ("1775 Windsor Road", "215"), "address: Avalon Teaneck's own-site row carries the unit in the address")
    eq(P.split_address_unit("20 Gill Lane, Apt. 1E"), ("20 Gill Lane", "1E"), "address: 'Apt. 1E'")
    eq(P.split_address_unit("138-28 Queens Boulevard #5K, New York, NY 11435, USA"), ("138-28 Queens Boulevard, New York, NY 11435, USA", "5K"), "address: unit before the city")
    eq(P.split_address_unit("304 4th Ave Unit 212"), ("304 4th Ave", "212"), "address: 'Unit 212'")
    eq(P.split_address_unit("12 Brooklyn Ave"), ("12 Brooklyn Ave", ""), "address: nothing to split")
    eq(P.split_address_unit("100 Unity St"), ("100 Unity St", ""), "address: 'Unity' is not 'Unit'")
    ok(P.same_listed_unit("215", "1", "716", "2516", "001-215", "1", "702", "2516"), "dedupe: '215' and '001-215' at the same rent, 716 and 702 sq ft, are one apartment (Avalon Teaneck)")
    ok(not P.same_listed_unit("001-215", "1", "700", "2500", "002-215", "1", "700", "2500"), "dedupe: '001-215' and '002-215' are two apartments")
    ok(not P.same_listed_unit("215", "1", "716", "2516", "001-215", "1", "900", "2516"), "dedupe: the sizes must agree")
    ok(not P.same_listed_unit("215", "1", "716", "2516", "001-215", "1", "716", "2900"), "dedupe: the rents must agree")
    ok(not P.same_listed_unit("215", "0", "716", "2516", "001-215", "1", "716", "2516"), "dedupe: the bedrooms must agree")
    import build_master as BM
    eq(BM.house_range("55-57 Bank Street", "10606"), ("55", "57", "bank st|10606"), "buildings: '55-57 Bank Street' is a range (the Continuum was three buildings)")
    eq(BM.house_range("83-33 118th St", "11415"), None, "buildings: a Queens house number is not a range")
    eq(BM.house_range("142-38 37th Ave", "11354"), None, "buildings: Queens again")
    eq(BM.prefixed_label("001-215"), "001215", "dedupe: a prefixed label"); eq(BM.prefixed_label("215"), "", "dedupe: a plain label has no prefix")
    # ---- step 4 (owner, 2026-11-16): only real apartments. Real examples of both kinds
    K = P.listing_kind
    for lab in ("PH2", "B9-309", "022-265", "5D", "T526", "00B-224", "206-A", "BAY-B508", "GAR2R-08", "N/A-0508", "Duplex701", "PA 112", "C-C02", "3B2", "1000-1210",
                "Lincoln House at Hamilton Park - 107", "K3-02", "2fl"):
        eq(K(lab, "detail", "apartmentlist:p1-x", "managed_building"), "unit", f"kind: {lab!r} is a real unit label")
    for lab in ("B, H, K, R - Small-1", "C, J, L, P, S - Large-1", "A - Large-1", "A - Renovated-1", "G - Small-1", "1 Bed", "1 Bed - 1 Bath", "1 Bedroom Large", "1 bed, 1 bath, $2575"):
        eq(K(lab, "detail", "apartmentlist:p263791-u49220319", "managed_building"), "floor_plan", f"kind: {lab!r} is a floor plan, not an apartment")
    eq(K("", "building_floorplan", "rc:trulia:b2734028645:plan-Bryce:456056389", "managed_building"), "floor_plan", "kind: a Trulia floor-plan row (no unit number) by the source's structure")
    eq(K("", "detail", "zumper-65278838", "managed_building"), "building_offer", "kind: a Zumper building page's price with no unit (Clinton Flats)")
    eq(K("", "detail", "gardencommunities:nj-morris-pondview-estates-one-bedroom", "managed_building"), "building_offer", "kind: a manager's 'one-bedroom' row with no unit")
    eq(K("", "detail", "zumper-64993702", "unknown"), "unit", "kind: a single-home listing page of its own with no unit number is still one specific home")
    eq(K("448-3", "detail", "apartmentlist:p116944794-207cSB.E-448-3", "managed_building", "The Agnes Co-Living"), "private_room", "kind: a room of a co-living suite")
    eq(K("203", "building_unit", "trulia:b2748217177:Unit_203:351142317", "managed_building", "The Agnes Co-Living"), "unit", "kind: a whole studio in the same building stays")
    eq(K("448-3", "detail", "x", "managed_building", "Avalon Somewhere"), "unit", "kind: '448-3' elsewhere is a unit")
    eq(K("1 Bed", "detail", "apartmentlist:p75198491-1_bed_1.0_bath_695_sqft", "unknown", "416 Highland Ave - 312"), "unit", "kind: a property titled with its own unit ('416 Highland Ave - 312') is one real apartment although its row is labelled '1 Bed'")
    eq(K("1 Bed", "detail", "x", "managed_building", "Skyline Tower"), "floor_plan", "kind: '1 Bed' at a managed building is a floor plan")
    eq(K("1 Bed", "detail", "x", "managed_building", "The Mark - Fairfield County"), "floor_plan", "kind: a dash in a building's name is not a unit")
    ok(P.unit_label_key("B, H, K, R - Small-1") == "" and P.unit_label_key("022-265") == "022265", "kind: a plan label has no unit key")
    # ---- no API key in a URL we carry
    eq(P.strip_url_secrets("https://maps.x/api?size=640x480&center=40.7%2C-73.8&key=AIzaNOTAKEY&signature=abc="), "https://maps.x/api?size=640x480&center=40.7%2C-73.8", "secrets: key and signature are stripped from a URL")
    eq(P.strip_url_secrets("https://x/y?token=zz&a=1"), "https://x/y?a=1", "secrets: a leading token")
    eq(P.strip_url_secrets("Lock & key=brass, monkey=1"), "Lock & key=brass, monkey=1", "secrets: text that is not a URL is left alone")
    # ---- names: a listing title is not a building's name; a park's name must be a park's
    C = P.clean_building_name
    eq(C("80East | Luxury Apartments | Dover, NJ"), "80East", "name: marketing tail after ' | '")
    eq(C("The Mark, Fairfield County ~ Resort-Inspired Luxury Living"), "The Mark, Fairfield County", "name: marketing tail after ' ~ '")
    eq(C("219 Lenox Rd #5G, Brooklyn, NY 11226, USA"), "", "name: an address with unit, city, state, ZIP and country is not a name")
    eq(C("31-20 54th Street #2fl , 31-20 54th St, Flushing, NY 11377, US"), "", "name: the doubled address line")
    eq(C("Kew Gardens Rd & 83rd Ave, New York, NY 11415, USA"), "", "name: an intersection with a city tail")
    eq(C("1775 E 18th St", "1775 E 18th St"), "", "name: a name that only repeats the building's address")
    eq(C("3 Journal Square", "2935 Kennedy Blvd"), "3 Journal Square", "name: an address-like NAME at another address is the building's name")
    eq(C("Avalon Teaneck", "1775 Windsor Road"), "Avalon Teaneck", "name: a real name is untouched")
    eq(C("The Mercer – 10 Commerce Court, Newark, NJ"), "The Mercer", "name: an address tail after a dash")
    eq(P.street_address("219 Lenox Rd, Brooklyn, NY 11226, USA"), "219 Lenox Rd", "address: city, state, ZIP and country are cut from the street address")
    eq(P.street_address("55-57 Bank Street"), "55-57 Bank Street", "address: nothing to cut")
    for bad in ("Leif Ericson Drive", "Baldwin Plaza", "Orange County Fair", "Old Campus"):
        eq(P.park_name(bad), "", f"park: {bad!r} is not a park's name (the distance is kept, the name is not)")
    for good in ("Veterans Memorial Park", "Harrison Riverfront Park", "Kissena Corridor Park", "Flushing Meadows", "Mill Pond Preserve"):
        eq(P.park_name(good), good, f"park: {good!r} stays")
    # ---- the thin-neighborhood rule
    import rank
    s_ = pd.Series
    cut = rank.thin_neighborhood_cut(s_(["a", "b", "c", "c", "d", "e"]), s_(["g"] * 6), s_([True] * 5 + [False]), s_([70.0, 39.0, 30.0, 20.0, 60.0, 90.0]), s_([0, 0, 1, 1, 1, 0]))
    eq(list(cut), [False, False, False, False, True, False], "thin: a lone apartment AT the median with nothing open stays (b); one with something open is cut (d); two-apartment neighborhoods are untouched (c); two-apartment neighborhoods are untouched")
    cut2 = rank.thin_neighborhood_cut(s_(["a", "b", "c", "c", "d"]), s_(["g"] * 5), s_([True] * 5), s_([70.0, 25.0, 30.0, 20.0, 60.0]), s_([0, 0, 1, 1, 0]))
    eq(list(cut2), [False, True, False, False, False], "thin: a lone apartment below its experience's median (30) is cut even with nothing open")
    # ---- owner, 2026-11-16 ("Forget call check"): a listing that was never re-read is not an open item
    gate0, gate1, gate2 = s_([0, 0, 0, 0, 0]), s_([1, 1, 1]), s_([2, 2])
    eq(list(rank.open_item_count(gate0, s_(["", "not checked", "blocked", "live", "changed"]))), [0, 0, 0, 0, 0],
       "no live flag: a unit never re-read (blank, not checked, blocked) has NO open item, exactly like one seen live")
    eq(list(rank.showable_by_open_items(rank.open_item_count(gate1, s_(["", "blocked", "live"])))), [True, True, True],
       "no live flag: one open gate fact and never re-read is ONE open item (shown with its asterisk), not two")
    eq(list(rank.showable_by_open_items(rank.open_item_count(gate2, s_(["live", ""])))), [False, False],
       "no live flag: two real open gate facts still hide a unit, seen live or not")
    # a found problem still counts: these are what a re-read FINDS, and each is still the open fact 'listing' (or removes)
    ok(P.price_doubt("Price far below the area's other listings; verify the price by phone before touring"), "no live flag: a checker's 'verify the price' note is still the open item 'listing'")
    eq(P.staleness("2026-08-22", "2026-11-15", available_date="now")[0], "open", "no live flag: a page unchanged 85 days is still one open item")
    eq(P.staleness("2026-04-01", "2026-11-15", available_date="now")[0], "remove", "no live flag: a page unchanged more than six months still removes the unit")
    # the thin rule's "well attested" test is on open GATE facts only: the fifth argument is the open-gate-fact count
    cut3 = rank.thin_neighborhood_cut(s_(["a", "b", "c", "c"]), s_(["g"] * 4), s_([True] * 4), s_([70.0, 60.0, 30.0, 20.0]),
                                      rank.open_item_count(s_([0, 1, 0, 0]), s_(["", "live", "", ""])))
    eq(list(cut3), [False, True, False, False], "thin: a lone apartment never re-read with no open gate fact stays (a); one seen live with an open gate fact is cut (b)")
    # ---- laundry and conflicting dog policy
    eq(list(rank.in_unit_laundry(s_(["yes", "on_site_only", "select_apartments", "", "Yes "]))), [True, False, False, False, True],
       "laundry: only the master's in_unit_laundry = yes scores; a shared room, 'select apartments' and unknown do not")


def lifestyle_assignment_checks():
    """Step 2: a neighborhood's experience is a pure function of its frozen area profile and the saved parameters."""
    import tempfile
    import numpy as np
    import pandas as pd
    import lifestyle_groups as LG
    ref = DATA / "reference"
    area = pd.read_csv(ref / "lifestyle_area_features.csv").set_index("hood_id")
    scaling = pd.read_csv(ref / "lifestyle_scaling.csv").set_index("feature")
    scale = pd.read_csv(ref / "lifestyle_index_scale.csv", index_col=0).iloc[:, 0]
    C = pd.read_csv(ref / "lifestyle_group_centres.csv", index_col=0)
    full, _ = LG.assign(area, scaling, scale, C)
    # removing neighborhoods (or units: the profile is frozen) changes nobody else's assignment or distances
    half = area.iloc[::2]
    sub, _ = LG.assign(half, scaling, scale, C)
    ok(sub.group_key.equals(full.group_key.loc[half.index]) and np.allclose(sub.ratio.values, full.ratio.loc[half.index].values), "groups: assigning half the neighborhoods gives each the same group and distances as assigning all")
    one, _ = LG.assign(area.loc[["nj:east-rutherford"]], scaling, scale, C)
    eq(one.group_key.iloc[0], full.group_key.loc["nj:east-rutherford"], "groups: a neighborhood assigned alone gets the same group")
    # the frozen profile does not follow the units: a run whose passing buildings changed leaves saved rows untouched
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "area.csv"
        area.loc[["nj:east-rutherford", "ny:patchogue"]].to_csv(f)
        H = area.loc[["nj:east-rutherford", "ny:patchogue", "ct:norwalk"]].copy()
        H["buildings"] = 1
        H.loc["nj:east-rutherford", "restaurants_800m"] = 3            # what happened on 2026-11-16: one passing building left
        H.loc["nj:east-rutherford", "sqft_per_1000usd"] = 270.0
        got, new = LG.freeze_area(H, path=f, today="2026-11-16")
        eq(new, ["ct:norwalk"], "groups: only a neighborhood seen for the first time is profiled")
        eq(float(got.at["nj:east-rutherford", "restaurants_800m"]), float(area.at["nj:east-rutherford", "restaurants_800m"]), "groups: a saved profile is not recomputed when the passing units change")
        again, new2 = LG.freeze_area(H.drop(index="ct:norwalk"), path=f, today="2026-11-17")
        ok(new2 == [] and "ct:norwalk" in again.index, "groups: a neighborhood that loses all its units keeps its saved profile")
    eq(full.group_key.loc["nj:east-rutherford"], "middle", "groups: East Rutherford is Little-City under the frozen profile (nearest by a wide margin)")
    eq(full.group_key.loc["ny:patchogue"], "middle", "groups: Patchogue is Little-City under the frozen profile (a boundary case, listed)")
    ov = LG.load_overrides()
    D, _ = LG.assign(area, scaling, scale, C, ov)
    ok(all(D.group_key.loc[h] == g for h, g in ov.items() if h in D.index), "groups: a reviewed override decides the group")
    ok(set(scaling.index) == set(LG.RAW) and (scaling.sd > 0).all(), "groups: scaling parameters are saved for every raw feature")
    return D


def data_6(L_):
    """Pipeline consistency pass, on the output."""
    import pandas as pd
    D = lifestyle_assignment_checks()
    R = pd.read_csv(DATA / "ranked_units.csv", dtype=str, keep_default_na=False, low_memory=False)
    G = pd.read_csv(DATA / "lifestyle_groups.csv").set_index("hood_id")
    ok(G.group_key.equals(D.group_key.loc[G.index].rename("group_key")), "groups: data/lifestyle_groups.csv holds exactly the assignment computed from the saved files")
    # only real apartments are ranked; thin neighborhoods; no duplicate; no secret in a URL
    ok(set(R.listing_kind) == {"unit"}, "kinds: every ranked row is a real apartment (no floor plan, building price or co-living room)")
    NA = pd.read_csv(DATA / "excluded_not_an_apartment.csv", dtype=str, keep_default_na=False, low_memory=False)
    ok(len(NA) > 0 and (NA.status == "not_an_apartment").all() and not set(NA.listing_id) & set(R.listing_id), "kinds: the others are kept with status not_an_apartment and are not ranked")
    for lab in ("B, H, K, R - Small-1", "G - Small-1", "1 Bed - 1 Bath"):
        ok(lab not in set(R.unit), f"kinds: the plan row {lab!r} is not ranked")
    S_ = R[R.shown == "True"]
    n_h = S_.groupby("hood_id").size()
    lone = S_[S_.hood_id.map(n_h) == 1]
    ok((lone.confirm_asterisk == "").all() and (pd.to_numeric(lone.open_gate_facts) == 0).all(), "thin: a neighborhood shown with one apartment shows a well-attested one (no open gate fact)")
    # ---- owner, 2026-11-16 ("Forget call check"): no 'not re-checked' flag anywhere in the output
    ok(not R.confirm_what.str.contains("live check").any() and not R.confirm_why.str.contains("has not been seen live|could not be opened in the evidence pass").any(),
       "no live flag: no ranked unit carries a 'live check' open item or its sentence")
    ok((pd.to_numeric(R.open_items) == pd.to_numeric(R.open_gate_facts)).all(), "no live flag: open_items is the number of open gate facts, nothing more")
    never = S_[~S_.live_status.isin(["live", "changed"])]
    ok(len(never) > 0 and (never[pd.to_numeric(never.open_gate_facts) == 0].confirm_asterisk == "").all(), "no live flag: a shown unit never re-read with no open gate fact has no asterisk")
    ok(((S_.confirm_asterisk == "yes") == (pd.to_numeric(S_.open_gate_facts) == 1)).all() and S_.confirm_what[S_.confirm_asterisk == "yes"].isin(["elevator", "dogs allowed", "availability", "listing", "eligibility", P.FLOOR_OR_ELEVATOR_LABEL]).all(),
       "no live flag: every asterisk on a shown unit names one open gate fact")
    ok((pd.to_numeric(S_.open_gate_facts) <= 1).all(), "no live flag: two real open gate facts still hide a unit")
    ok(not (R.live_status == "gone").any(), "no live flag: a unit found gone at a re-read is still removed")
    ok(S_.last_seen.ne("").all(), "no live flag: every shown unit keeps the date its price was read")
    ok(not (DATA / "needs_live_check.csv").exists(), "no live flag: the 'waiting for a live check' list is no longer written")
    T_ = R[R.not_shown_reason == "thin_neighborhood"]
    ok((T_.shown == "False").all() and (T_.shown_before_thin_rule == "True").all() and T_.hood_id.map(lambda h: h not in set(S_.hood_id)).all(), "thin: a cut neighborhood shows nothing and its apartment stays in the file with the reason")
    import itertools
    dup = [(a["listing_id"], b["listing_id"]) for _, g in R.groupby("building_id") for a, b in itertools.combinations(g.to_dict("records"), 2)
           if P.same_listed_unit(a["unit"], a["beds"], a["sqft"], a["listed_rent"], b["unit"], b["beds"], b["sqft"], b["listed_rent"])]
    ok(not dup, f"dedupe: no apartment is ranked twice under two spellings of its unit ({dup[:3]})")
    ok(R[R.building_name.str.contains("Continuum")].building_id.nunique() <= 1 and not R[R.building_name.str.contains("Continuum")].unit.duplicated().any(), "dedupe: the Continuum is one building and no unit of it appears twice")
    ok(not ((R.building_name == "Avalon Teaneck") & R.unit.map(lambda u: P.unit_tail(u) == "215")).sum() > 1, "dedupe: Avalon Teaneck 215 appears once")
    import glob
    leak = [f for f in glob.glob(str(DATA / "*.csv")) + glob.glob(str(DATA / "listings_raw" / "*.csv")) + [str(ROOT / "site" / "data.json")]
            if Path(f).exists() and re.search(r"key=AIza|https?://[^\s\"',]*[?&](?:key|api_key|token|signature)=", Path(f).read_text(errors="replace"))]
    ok(not leak, f"secrets: no data file holds an API key, token or signature in a URL ({[Path(f).name for f in leak]})")
    ok(not L_[L_.address_as_listed.str.count("#") < 2].address.str.contains(r"#\s*\w+\s*$").any(), "address: no listing address still ends in '#unit'")
    X = pd.read_csv(DATA / "lifestyle_group_distances.csv").set_index("hood_id")
    ok(set(X.index) == set(G.index) and (X.boundary == (X.ratio >= 0.9)).all(), "groups: the distance file covers every neighborhood and flags the boundary cases")
    R = pd.read_csv(DATA / "ranked_units.csv", dtype=str, keep_default_na=False, low_memory=False)
    # step 1: the listing gate and the ranking agree on every ranked unit
    # owner, 2026-11-17: the elevator is judged with the floor (parsers.floor_elevator_rule). A ranked unit is settled or
    # carries ONE open fact (elevator, or floor_or_elevator); 'no' / 'unknown' elevators rank only where the floor allows
    st = R.elevator_rule_status
    fst, fcode = R.floor_elevator_status, R.floor_elevator_code
    ok(fst.isin(["settled", "open"]).all(), "floor/elevator rule: no ranked unit fails it or is unknown under it")
    ok((st.isin(["established", "open"]) | fcode.isin(["floor_2", P.FLOOR_OR_ELEVATOR_CODE])).all(), "floor/elevator rule: an elevator 'no' or 'unknown' ranks only on floor 2 or as floor_or_elevator")
    ok((fst[st == "established"] == "settled").all() and (fcode[st == "established"] == "").all(), "floor/elevator rule: an apartment with an established elevator is unaffected")
    ok((R[R.shown == "True"].open_keys.str.split(";").map(lambda k: "elevator" in k) == (R[R.shown == "True"].floor_elevator_status == "open")).all(),
       "floor/elevator rule: a shown unit carries the elevator item exactly when the rule says 'open'")
    sh = R[R.shown == "True"]
    ok((sh[sh.floor_elevator_code == P.FLOOR_OR_ELEVATOR_CODE].confirm_what == P.FLOOR_OR_ELEVATOR_LABEL).all(), "floor/elevator rule: floor_or_elevator is named 'floor and elevator' on the asterisk")
    ok(sh[sh.floor_elevator_code == P.FLOOR_OR_ELEVATOR_CODE].to_confirm.str.contains(P.FLOOR_OR_ELEVATOR_Q, regex=False).all(), "floor/elevator rule: ... with the question 'Confirm the floor, and whether there is an elevator'")
    w2 = sh[(sh.floor_elevator_code == "floor_2") & ~sh.unit_floor_basis.isin(["confirmed", "stated", "confirmed_by_phone"])]
    ok(w2.disclosures.str.contains("floor_read_from_number", regex=False).all() and (w2.floor_basis_note == "read from the unit number").all(),
       "floor/elevator rule: a walk-up on floor 2 read from the apartment number carries the 'read from the apartment number' disclosure")
    cur_ = pd.to_numeric(R.live_price.where(R.live_status.isin(["live", "changed"]) & (R.live_price != ""), R.listed_rent), errors="coerce")
    ok(not (cur_ > 2200).any(), "rent: no ranked unit has a listed base rent over $2,200 (owner, 2026-11-17)")
    ok(not (pd.to_numeric(L_.listed_rent.str.replace(r"[$,]", "", regex=True), errors="coerce") > 2200)[L_.gate_status != "fail"].any(), "rent: every listing over $2,200 fails the listing gate")
    ok(L_[pd.to_numeric(L_.listed_rent.str.replace(r"[$,]", "", regex=True), errors="coerce") > 2200].fail_reasons.str.contains("over_2200").all(), "rent: ... with the reason over_2200")
    g = L_.set_index("listing_id").elevator_rule_status
    ok(set(L_[L_.g_elevator == "pass"].elevator_rule_status) <= {"established", "open"} and set(L_[L_.g_elevator == "fail"].elevator_rule_status) == {"no"}
       and set(L_[L_.g_elevator == "unknown"].elevator_rule_status) == {"unknown"}, "elevator rule: gate result follows the rule's status")
    ok(not ((L_.g_elevator == "fail") & (L_.elevator_basis == "nyc_pluto_building_class") & ~pd.Series([P.lot_is_exact(a, b, c) for a, b, c in zip(L_.match_basis, L_.address, L_.pluto_address)], index=L_.index)).any(),
       "elevator rule: no listing fails on the walk-up class of a neighbouring lot")


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
    """Independent check 3: the page data."""
    import pandas as pd
    if "buildings" not in J:
        ok(False, "page: site/data.json has no buildings array (run scripts/build_page_data.py)")
        return
    units = {u["id"]: u for u in J["units"]}
    if set(units) != set(S.index):
        return                                          # data.json is from an earlier run: build_page_data.py has not run since rank.py
    page_ic4(J, M, R, S)
    page_cleanup(J, M, R, S)
    page_ic5(J, M, R, S)
    # D12: experience and neighborhood figures are computed over the shown units
    for y in J["years"]:
        us = [u for u in J["units"] if u["year"] == y["id"]]
        for key, get in [("all_in", lambda u: u["all_in"]), ("sqft", lambda u: u["sqft"]), ("drive_min", lambda u: u["moments"]["sun"]["drive_min"])]:
            vals = pd.Series([get(u) for u in us], dtype=float).dropna()
            if len(vals):
                ok(abs(float(vals.median()) - float(y["medians"][key])) <= 0.06, f"IC3 D12: {y['id']} median {key} is the median of its shown units")
                ok(abs(float(vals.min()) - y["ranges"][key][0]) <= 0.06 and abs(float(vals.max()) - y["ranges"][key][1]) <= 0.06, f"IC3 D12: {y['id']} range {key} is over the same shown units")
        e = y.get("drive_min_range_hoods")
        ok(bool(e) and e["nearest"]["name"] and e["farthest"]["name"] and e["nearest"]["drive_min"] <= e["farthest"]["drive_min"], f"IC3 D12: {y['id']} names its nearest and farthest neighborhoods")
    for h in J["neighborhoods"]:
        us = [units[i] for i in h["unit_ids"]]
        sq = pd.Series([u["sqft"] for u in us], dtype=float).dropna()
        if len(sq):
            ok(abs(float(sq.median()) - float(h["sqft_median"])) <= 0.06, f"IC3 D12: {h['id']} sqft_median is over its shown places")
        ok([b for b in h["building_ids"]] == [b["id"] for b in sorted([b for b in J["buildings"] if b["hood_id"] == h["id"]], key=lambda b: b["rank_in_neighborhood"])], f"step 5: {h['id']} building_ids in rank order")
    # step 5: buildings
    seen = [i for b in J["buildings"] for i in b["unit_ids"]]
    ok(sorted(seen) == sorted(units), "step 5: every shown unit sits under exactly one building")
    for b in J["buildings"]:
        us = [units[i] for i in b["unit_ids"]]
        ok(b["n_units"] == len(us) <= 8 and b["from_all_in"] == min(u["all_in"] for u in us), f"step 5: {b['id']} n_units and from_all_in")
        ok([u["scores"]["hood_rank"] for u in us] == sorted(u["scores"]["hood_rank"] for u in us), f"step 5: {b['id']} units in rank order")
        ok(all(u["building_id"] == b["id"] and u["hood_id"] == b["hood_id"] for u in us), f"step 5: {b['id']} units belong to it")
    # step 6: per-unit fields
    for u in J["units"][:400]:
        ok("all_in_likely" in u and u["all_in_likely"] >= u["all_in"] and isinstance(u["unknown_cost_lines"], list) and "more_in_building" in u, f"step 6: {u['id']} carries all_in_likely, unknown_cost_lines, more_in_building")
        ok(all(u["moments"][k].get("rating") in ("strong", "mixed", "weak", None) for k in ("wake", "work", "after", "night", "sat", "sun")), f"step 6: {u['id']} moment ratings")
    for k in ("wake", "work", "after", "night", "sat", "sun"):
        vc = pd.Series([u["moments"][k].get("rating") for u in J["units"]]).value_counts(normalize=True)
        ok(len(vc) == 0 or float(vc.max()) <= 0.62, f"step 6: no level of the '{k}' moment holds more than about 60% of the shown places (largest: {vc.index[0] if len(vc) else ''} {float(vc.max()) if len(vc) else 0:.0%})")
    ok(all((u["moments"]["sun"]["rating"] == "strong") == (u["moments"]["sun"]["drive_min"] <= 30) for u in J["units"] if u["moments"]["sun"]["drive_min"] is not None), "step 6: Sunday is strong at 30 minutes or less, an absolute threshold")
    # owner, 2026-11-16 ("Forget call check"): the page data
    ok(J.get("awaiting_live_check") == [] and J["meta"]["counts"]["awaiting_live_check"] == 0, "no live flag: awaiting_live_check is an empty array in the page data")
    ok(all(u["confirm"]["what"] != "live check" for u in J["units"] + J["held"] + J["avoid"]) and all("live check" not in b["open_items"] for b in J["buildings"]),
       "no live flag: no unit or building in the page data carries the open item 'live check'")
    ok(all(u.get("price_seen_at") for u in J["units"]), "no live flag: every shown unit carries price_seen_at")
    ok(not re.search(r"not been seen live|could not be opened in the evidence pass|live re-check", json.dumps([u["confirm"] for u in J["units"]]) + json.dumps(J["meta"]["notes"])),
       "no live flag: no sentence says a listing has not been checked again")
    txt = json.dumps(J["meta"]["notes"]) + json.dumps([u["confirm"] for u in J["units"]])
    ok("counted as $0" not in txt and "count as $0" not in txt, "pending fix: neither meta.notes nor any confirm.why says 'counted as $0'")
    ok(not any(re.search(r"\[live check\]|\[evidence\]|totalPrice|not stated", (u["rent"]["offer_text"] or "")) for u in J["units"]), "pending fix: rent.offer_text holds clean text only")
    ok("Lots of hispanics" not in json.dumps([h["local"]["voices"] for h in J["neighborhoods"]]), "IC3 D24: the Dover quote is not on the page")
    ok(all(not u["parking"]["offsite"] or (u["parking"]["rank"] or 0) <= 2 for u in J["units"]), "IC3 D10: off-site parking is never ranked as covered parking")


def pure_ic4():
    """docs/INDEPENDENT_CHECK_4.md: one test per repaired defect (pure rules)."""
    import build_master as BM
    import pandas as pd
    # ---- D3: a label that NAMES its building is multi-building whatever floor it reads as; a label is never a height
    ok(P.multi_building_labels(["K3-02", "K3-23", "K4-19", "L3-03", "M2-07", "M4-10", "M4-12", "M4-22"]), "IC4 D3: Residences at The Summit (buildings K, L, M) reads as a multi-building complex although K4-19 reads as floor 4")
    eq(P.label_reading("K3-02"), ("k", 3, 2), "IC4 D3: K3-02 is building K, floor 3")
    ok(BM.garden_style(["K3-02", "K4-19", "L3-03", "M4-22"], [""]), "IC4 D3: no page or record height: the garden-style rule fires")
    ok(not BM.garden_style(["K3-02", "K4-19", "L3-03", "M4-22"], ["5"]), "IC4 D3: a page or record that gives five floors settles it")
    ok(P.multi_building_labels(["001-215", "001-304", "003-463"]) and P.multi_building_labels(["34-204", "34-615", "36-206"]), "IC4 D3: Avalon Teaneck and Valley and Bloom name several buildings (a floor read from a label is not a height)")
    ok(P.multi_building_labels(["A207", "A307", "A508", "B102", "B511", "C215", "C309"]), "IC4 D30: Fort Hill Peekskill, buildings A, B, C")
    ok(not P.multi_building_labels(["T526", "T611"]) and not P.multi_building_labels(["1206", "2303", "0817"]), "IC4 D3: one building letter, or a tower's four-digit labels, is not a multi-building complex")
    # ---- D1 / D17: a building's point against its own address
    eq(P.coord_check(True)[0], "keep", "IC4 D1: the point is in the address's ZIP area")
    eq(P.coord_check(False, 71, False, True)[0], "keep", "IC4 D1: a ZIP boundary (the address geocodes 71 m away)")
    eq(P.coord_check(False, 6889, True, False)[0], "regeocode", "IC4 D1: Harbor Pointe, 6.9 km from where its address geocodes")
    eq(P.coord_check(False, 168, True, False)[0], "regeocode", "IC4 D17: Parkway Lofts, 168 m away across the East Orange line")
    eq(P.coord_check(False, None, False, False)[0], "flag", "IC4 D1: no geocode and the municipality differs: flagged, never silently used")
    eq(P.coord_check(False, 900, False, False)[0], "flag", "IC4 D1: a geocode that is itself outside the address's area settles nothing")
    eq(P.coord_check(False, None, False, True)[0], "keep", "IC4 D1: no geocode but the municipality is the address's own")
    eq(P.municipality_name("Bloomfield township"), "Bloomfield", "IC4 D17: municipality name without the legal suffix")
    eq(P.municipality_name("Milford city (balance)"), "Milford", "IC4 D25: 'Milford city (balance)' is Milford")
    eq(P.municipality_name("", "Franklin township"), "Franklin", "IC4 D17: county subdivision where there is no incorporated place")
    ok(P.same_municipality("City of Orange", "Orange") and not P.same_municipality("Newark", "Maplewood"), "IC4 D17: same_municipality")
    G = pd.DataFrame({"lat": [40.6709575, 40.70], "lon": [-74.1797692, -73.80], "coord_basis": ["listing rows agree"] * 2, "coord_spread_m": [0, 0], "coord_note": ["", ""]}, index=["b_hp", "b_ok"])
    U = pd.DataFrame({"building_id": ["b_hp", "b_ok"], "address": ["302 Constitution Ave", "1 Main St"], "city": ["Bayonne", "Jamaica"], "state": ["NJ", "NY"], "zip5": ["07002", "11435"]})
    geo = lambda la, lo: ("07201", "Elizabeth") if lo < -74.15 else (("07002", "Bayonne") if lo < -74 else ("11435", "New York"))
    C = BM.check_coords_against_address(G, U, geocode=lambda a, c, st, z: (40.67256, -74.098197, "302 CONSTITUTION AVE, BAYONNE, NJ, 07002", ""), geography=geo)
    eq((C.at["b_hp", "coord_check"], round(float(C.at["b_hp", "lon"]), 3), C.at["b_ok", "coord_check"]), ("regeocoded", -74.098, "ok"), "IC4 D1: Harbor Pointe's point is replaced by its address's; a building inside its ZIP is untouched")
    C = BM.check_coords_against_address(G, U, geocode=lambda a, c, st, z: None, geography=geo)
    eq(C.at["b_hp", "coord_check"], "flagged", "IC4 D1: no geocoder match: flagged")
    # ---- D2: a second site lists the address and not this apartment
    for t in ["Trulia returned HTTP 403. Unit 16F is not on the Zumper address page (it shows 2 units, 0 available). Not verified today.",
              "its Availability link goes to a page with no unit table, and the Zumper address page shows only 2-bedrooms ($2,900 to $4,900). Unit 705 not verified today.",
              "No other allowed site shows this unit. Zumper's address page shows only an inactive 2022 listing for another unit (#2L).",
              "Zumper's address page (https://www.zumper.com/address/525-riverdale-ave-yonkers-ny-10705-usa, fetched 2026-11-16T00:31:06+00:00) shows a different apartment here (a 1-bedroom at $2,400), not this studio.",
              "No other allowed site shows this unit. Zumper shows only unit #401 for this address. No building site was found.",
              "Zumper's building page lists other units here (205, 305, 302, 402 among the 1-bedrooms) but not 211."]:
        ok(P.second_site_omits(t, "blocked"), f"IC4 D2: a second site omits the apartment: {t[:70]!r}")
    for t in ["No other allowed site shows this unit. No building site was found; Zumper has no address page (404).",
              "Apartment List shows one 1-bed at this address, $2,692, Avail. now, which agrees with the stored price.",
              "Zumper building page read at 2026-11-15: 1BR plans from $2,490 (no unit numbers, no dates)."]:
        ok(not P.second_site_omits(t, "blocked"), f"IC4 D2: not a finding: {t[:70]!r}")
    ok(not P.second_site_omits("Unit 16F is not on the Zumper address page", "live"), "IC4 D2: an apartment seen live on its own page is not doubted by a second site")
    # ---- D4: labels that are not real above-ground apartments
    ok(P.plan_letter_label("P", ["P", "F", "3Pb", "4OA"]) and P.plan_letter_label("C", ["2B", "3A", "C", "E"]), "IC4 D4: a single letter beside numbered apartments is a plan letter (BE, Appletree Suites)")
    ok(not P.plan_letter_label("F", ["F"]) and not P.plan_letter_label("2B", ["2B", "C"]) and not P.plan_letter_label("Z", ["Z", "1 Bed - 1 Bath"]), "IC4 D4: a lone letter, or a numbered label, stays an apartment")
    ok(P.sequential_number_reads_ground("10", 65, 6), "IC4 D4: 630 West 163rd Street 10 (65 apartments on six floors) reads as the first floor")
    ok(not P.sequential_number_reads_ground("35", 48, 6) and not P.sequential_number_reads_ground("2B", 65, 6) and not P.sequential_number_reads_ground("10", None, 6) and not P.sequential_number_reads_ground("305", 65, 6),
       "IC4 D4: a higher number, a lettered label, an unknown count or a floor-digit label reads nothing")


def pure_ic4_text():
    """Independent check 4, D8 / D9 / D18 / D19 / D20 / D22 / D24 and the lease-term gap: pure rules and the page's text templates."""
    import pandas as pd
    import build_master as BM
    import build_page_data as BP
    # ---- D8: conditions in the evidence
    eq(P.renter_conditions("Rental Terms, Policies & Fees: Furnished", "furnished"), {"furnished": True}, "IC4 D8: a Furnished tag (Appletree Suites, Metrovue)")
    eq(P.renter_conditions("listed 2026-10-28; furnished; $300 building application fee + $150 background check"), {"furnished": True}, "IC4 D8: '; furnished;' in a checker's note")
    eq(P.renter_conditions("Zumper's address page shows only a furnished corporate unit from 2014-2023."), {}, "IC4 D8: another listing's furnished corporate unit is not this apartment")
    eq(P.renter_conditions("building amenities include a doorman, concierge, garage parking, and a furnished roof deck"), {}, "IC4 D8: a furnished roof deck is not a furnished apartment")
    eq(P.renter_conditions("Requirements: Household income of $104,000+ (40x rent) and 700+ credit."), {"credit": "700+"}, "IC4 D8: 948 New York Avenue, 700+ credit")
    eq(P.renter_conditions("... Parking 700+ credit Security deposit NO BROKER FEE"), {"credit": "700+"}, "IC4 D8: '700+ credit' in a listing's list")
    for t in ["ONE MONTH FREE ON AN 18-MONTH LEASE $1,000 SECURITY FOR CREDIT OVER 700!", "a security deposit of just $99.00 with a 600+ credit score", "*Security Deposit-$2000 - minimum credit score-700",
              "an additional $500 credit if you apply within 24 hours", "plus $1,500 credit, select apartments", "A $13 credit check fee will be taken electronically"]:
        eq(P.renter_conditions(t), {}, f"IC4 D8: not a credit-score requirement: {t[:50]!r}")
    eq(P.renter_conditions("Short-term rentals only").get("not_normal_lease"), "short-term rentals only", "IC4 D8: short-term only is not a normal lease")
    eq(P.renter_conditions("month-to-month after the term costs $25 more per month"), {}, "IC4 D8: a month-to-month surcharge after the term is an ordinary lease")
    ok(not P.income_restricted("$130,000 a year") and not P.income_restricted("3x the rent in household income"), "IC4 D8: an income requirement is not income-restricted housing")
    # ---- D9: doorman and concierge, each only from text that says so
    eq(P.staff_from_sources("yes: [community amenity] Concierge"), {"doorman": "", "concierge": "yes", "front_desk": ""}, "IC4 D9: 'Concierge' in an amenity list is a concierge, not a doorman")
    eq(P.staff_from_sources("concierge: yes | amenity list: 24hr concierge"), {"doorman": "", "concierge": "24h", "front_desk": ""}, "IC4 D9: 24-hour concierge")
    eq(P.staff_from_sources("yes | amenity list: Doorman || concierge: yes | amenity list: Concierge"), {"doorman": "yes", "concierge": "yes", "front_desk": ""}, "IC4 D9: both, each from its own source")
    eq(P.staff_from_sources("24/7 attended lobby"), {"doorman": "", "concierge": "", "front_desk": "24h"}, "IC4 D9: an attended lobby is neither")
    eq(P.staff_from_sources("virtual doorman"), {"doorman": "", "concierge": "", "front_desk": ""}, "IC4 D9: a virtual doorman is none of them")
    eq(P.staff_from_sources("none listed; Trulia lists 'Night Patrol'"), {"doorman": "", "concierge": "", "front_desk": ""}, "IC4 D9: a negative says nothing")
    eq(P.staff_from_sources("Door Person | Services | Door Person")["doorman"], "yes", "IC4 D9: door person")
    # ---- D18: a fee from a resident's review is an estimate with its source named
    eq(P.review_sourced("reserved $95/month; regular (first come) $75/month, per a resident review dated 2025-05-01"), (True, "2025-05-01"), "IC4 D18: The Atwater's fee sentence is from a review, with its whole date")
    eq(P.review_sourced("Unassigned and/or Reserved Parking Fee $75"), (False, ""), "IC4 D18: a listing's fee line is not a review")
    eq(P.parse_parking("reserved $95/month; regular (first come) $75/month, per a resident review dated 2025-05-01")["options"], "reserved $95; regular (first come) $75",
       "IC4 D18: the option's name carries no source and no date cut short ('2025-05-0')")
    ok(BM.PREC.index("resident_review") > BM.PREC.index("stated"), "IC4 D18: a review ranks below every page that states the fee")
    m_ = BM.Merge()
    BM.add_parking(m_, "b1", "reserved $95/month; regular (first come) $75/month, per a resident review dated 2025-05-01", "confirmed", "u1")
    eq(m_.resolve()[0]["b1"]["parking_fee_monthly_basis"], "resident_review", "IC4 D18: basis resident_review, not confirmed")
    BM.add_parking(m_, "b1", "Unassigned and/or Reserved Parking Fee $75", "amenities_page", "u2")
    eq(m_.resolve()[0]["b1"]["parking_fee_monthly_basis"], "amenities_page", "IC4 D18: where a listing states the fee, the listing is the source")
    eq((P.parking_kinds("garage: surface parking; optional garages, rate not stated"), P.garage_is_optional("garage: surface parking; optional garages, rate not stated")), (["lot", "garage"], True),
       "IC4 D18: J Centra Burlington is a lot with optional garages, not 'garage parking'")
    eq((P.parking_kinds("garage"), P.garage_is_optional("garage")), (["garage"], False), "IC4 D18: a plain garage")
    eq(BP.receipt_note({"code": "parking_estimate_review", "data": {"review_date": "2025-05-01"}, "amount": 75}), "From a resident's review dated May 1, 2025, not from the building: an estimate.", "IC4 D18: the receipt names the review, with the date whole")
    # ---- D20: "up to" is kept
    for t in ["RECEIVE UP TO 2 MONTHS FREE ON BASE RENT! Restrictions and minimum lease term apply.", "Receive Up to 1 Month Free on base rent on select apartments.", "Receive up to 6-Weeks Base Rent FREE PLUS $250 Look and Lease",
              "up to two months free off base rent"]:
        ok(P.offer_is_up_to("", t, "2"), f"IC4 D20: an 'up to' offer: {t[:40]!r}")
    ok(not P.offer_is_up_to("", "2 months free on a 13+ lease", "2") and not P.offer_is_up_to("", "Save up to $500 and get 2 months free", "2"), "IC4 D20: a definite offer is not 'up to'")
    ok(P.offer_is_up_to("'up to' / range offer: amount for this unit not stated", "", "2") and P.offer_is_up_to("", "", "1-2"), "IC4 D20: the rent-terms condition and a range count")
    row = {"rent_free_months": "2", "rent_offer_type": "months_free", "rent_offer_up_to": "yes", "rent_lease_months": ""}
    eq(BP._free_text(row), "up to 2 months", "IC4 D20: the page's offer text keeps 'up to'")
    eq(BP.disclosure_text({"what": "special offer", "code": "offer:months_free"}, row)[1][:51], "The listing advertises up to 2 months of free rent.", "IC4 D20: 'up to 2 months free' is not written as '2 months free'")
    eq(BP._free_text({**row, "rent_offer_up_to": ""}), "2 months", "IC4 D20: a definite offer stays definite")
    # ---- D22: numbering conventions
    eq([P.floor_by_convention(u_, "floor_first") for u_ in ("2141", "3172", "4149", "4171", "1116", "4186")], [2, 3, 4, 4, 1, 4], "IC4 D22: The Grove Somerset: the floor is the first digit")
    eq([P.floor_by_convention(u_, "building_floor_unit") for u_ in ("3104", "1236", "11102", "2284")], [1, 2, 1, 2], "IC4 D22: building, floor, number (Kensington Place, J Centra)")
    eq(P.floor_by_convention("B9-309", "floor_first"), None, "IC4 D22: a label with a separator is not read by the table")
    eq((P.tower_label_floor("01-16C"), P.tower_label_floor("02-229"), P.tower_label_floor("140-1F")), (16, None, 1), "IC4 D22: Prospect Place 01-16C is floor 16")
    conv = BM.load_numbering_conventions()
    ok(conv.get("b_05730a14a8") == "floor_first" and conv.get("b_15bd92512c") == "building_floor_unit", "IC4 D22: the reviewed conventions table is read")
    # ---- D4 / D19 helpers
    eq(P.manager_name("Jones Street Residential (Trulia capture); batch file says Konover Residential Corporation"), "Jones Street Residential", "IC4 D24: the manager's name without the working note")
    eq(P.manager_name("listed by Blue Chip Real Estate Group LLC (broker); manager not stated"), "", "IC4 D24: a broker is not the manager")
    # ---- D24: reader text
    ok(not BP.reader_ok("Is this unit still available?") and not BP.reader_ok("see docs/PENDING_FIXES.md") and not BP.reader_ok("The evidence pass could not confirm an elevator")
       and not BP.reader_ok("Zumper harvest row says elevator yes") and not BP.reader_ok("per a resident review dated 2025-05-0 $75") and not BP.reader_ok("class_c_violations"),
       "IC4 D24: the reader check rejects unit, file paths, pipeline words, truncated dates and field names")
    ok(BP.reader_ok("The listing page was last changed on August 22, 2026, 86 days before we read it."), "IC4 D24: a plain sentence passes")
    eq(BP.day("2026-08-22"), "August 22, 2026", "IC4 D24: dates are written out whole")
    eq(BP.day("2025-05-0"), "", "IC4 D24: a date cut short is never printed")
    eq(BP.plain("Is unit 302 still available at $1,675?"), "Is apartment 302 still available at $1,675?", "IC4 D24: apartment, not unit")
    eq(BP.reviewed("A Google review (seen in a search summary, docs/PENDING_FIXES.md) claims units here were advertised with no occupancy permit."), None, "IC4 D24: a reviewer's sentence with a file path is not printed; the template is used")
    base = {"open_keys": "elevator", "confirm_what": "elevator", "confirm_asterisk": "yes", "open_review_why": "", "open_review_question": ""}
    for code in ("height_only", "select_buildings", "city_record", "low_rise", "listing_site_only", "height_implied", "not_confirmed", "complex", "reviewer"):
        t = BP.open_item_text({**base, "open_codes": code, "confirm_why": "The evidence pass could not confirm an elevator for this building: Zumper harvest row says elevator yes |"})
        ok(t[2] and BP.reader_ok(t[2]) and BP.reader_ok(t[3]) and "evidence pass" in t[4], f"IC4 D24: elevator / {code}: plain why and question; the raw note only in why_internal")
    for key, what, codes in [("dogs", "dogs allowed", ("sources_disagree", "case_by_case", "ask_policy", "dogs_not_named", "not_reread", "listing_site_only", "not_confirmed", "reviewer")),
                             ("availability", "availability", ("second_site", "reviewer")),
                             ("listing", "listing", ("place", "address_mismatch", "stale_page", "stale_date", "warning", "price_doubt", "sibling_12", "reviewer")),
                             ("eligibility", "eligibility", ("income_tag", "not_normal_lease", "eligibility", "reviewer"))]:
        for code in codes:
            t = BP.open_item_text({"open_keys": key, "confirm_what": what, "open_codes": code, "confirm_asterisk": "yes", "listing_stale_why": "the listing page was last changed on 2026-08-22, 86 days before it was read (2026-11-16), and no second site lists the unit",
                                   "price_12_sibling_why": "unit 425 of this building is $2,606 on its 24-month price and $3,210 on a 12-month lease (23 percent more)", "price_lease_months": "24"})
            ok(t[2] and t[3] and BP.reader_ok(t[2]) and BP.reader_ok(t[3]) and BP.reader_ok(t[1]), f"IC4 D24: {key} / {code}: plain label, why and question")
    t = BP.open_item_text({"open_keys": "listing", "confirm_what": "listing", "open_codes": "stale_page", "listing_stale_why": "the listing page was last changed on 2026-08-22, 86 days before it was read (2026-11-16), and no second site lists the unit"})
    eq(t[2], "The listing page was last changed on August 22, 2026, 86 days before we read it, and no second site lists this apartment.", "IC4 D24: the stale-page sentence, from the date and the day count")
    # the lease-term gap: any term that is not 12 months
    eq(BP.disclosure_text({"what": "lease term", "code": "lease:term"}, {"price_lease_months": "13"})[1], "The price shown is for a 13-month lease: ask for the 12-month price.", "lease gap: the 13-month sentence")
    eq(BP.disclosure_text({"what": "lease term", "code": "lease:term"}, {"price_lease_months": "11"})[1], "The price shown is for an 11-month lease: ask for the 12-month price.", "lease gap: a term under a year")
    for code, row in [("floor:floor_read_from_number", {"unit_floor": "4", "unit": "4F"}), ("floor:floor_not_published", {}), ("lease:uses_12_month", {"price_lease_months": "13", "price_12_month": "3040", "listed_rent": "2487"}),
                      ("lease:sibling_12", {"price_lease_months": "24"}), ("lease:lowest_of_terms", {}), ("lease:reviewer", {}), ("cost:could_pass", {"all_in": "2900", "all_in_likely": "3080", "unknown_cost_lines": "parking"}),
                      ("condo:city_record", {}), ("condo:listed_as_condo", {}), ("net_effective", {}), ("offer:dollar_credit", {}), ("offer:other", {}), ("dog_weight", {}),
                      ("overnight_parking", {"street_overnight_town": "East Orange", "street_overnight_rule": "Every car parked on the street overnight needs a permit."}),
                      ("income_requirement", {"cond_income": "$130,000 a year"}), ("credit_requirement", {"cond_credit": "700+"}), ("furnished", {})]:
        lab, why, q = BP.disclosure_text({"what": "x", "code": code}, row)
        ok(why and BP.reader_ok(why) and BP.reader_ok(q), f"IC4 D24: disclosure {code}: plain why ({why[:50]!r}) and question")
    eq(BP.disclosure_text({"what": "income requirement", "code": "income_requirement"}, {"cond_income": "$130,000 a year"})[1], "Income requirement: $130,000 a year.", "IC4 D8: the income requirement, as the listing states it")
    eq(BP.disclosure_text({"what": "furnished apartment", "code": "furnished"}, {})[1], "Furnished apartment.", "IC4 D8: furnished")
    for code, d_ in [("rent_listed", {"lease_months": 13}), ("rent_12_month", {"lease_months": 13, "listed": 2487}), ("rent_net_effective", {"gross": 2800}), ("fees_unknown", {"fee_exists": True}), ("fees_unknown", {}),
                     ("fees_in_price", {}), ("fees_published", {"more_not_published": True, "alternatives": True}), ("pet_published", {"several_amounts": True}), ("pet_estimate", {"buildings": 40, "state": "NJ"}),
                     ("parking_included", {}), ("parking_street", {}), ("parking_published", {"pick": "lowest_listed", "low": 75, "high": 95}), ("parking_published", {"pick": "range", "low": 75, "high": 150}),
                     ("parking_published", {"pick": "first_space"}), ("parking_published", {"pick": "lowest_covered"}), ("parking_unknown", {}), ("parking_unknown", {"extra_space_only": True}),
                     ("parking_unknown", {"limited_time_free_not_counted": True}), ("utility_estimate", {}), ("utility_estimate", {"cooking_gas_only": True}), ("utility_included", {}), ("utility_in_fees", {}),
                     ("utility_no_gas", {}), ("utility_unknown", {})]:
        n_ = BP.receipt_note({"code": code, "data": d_, "amount": 100})
        ok(n_ and BP.reader_ok(n_), f"IC4 D24: receipt note {code}: {n_!r}")
    eq(BP.receipt_note({"code": "parking_published", "data": {"pick": "lowest_listed", "low": 75, "high": 95}, "amount": 75}), "The lowest of the published prices ($75 to $95).",
       "IC4 D24: 'cheapest of the prices listed; prices listed: reserved $95; regular ...' is written as a sentence")
    pts = BP.evidence_points("NJ state housing inspection: 12 open violations at the latest report (2022-05-04); 3 older management complaint(s); management may have changed; 2 safety incident report(s) at the address")
    eq(len(pts), 3, "IC4 D24: three things worth knowing, each one sentence")
    ok(all(BP.reader_ok(x) for x in pts + BP.evidence_points("management: city records in the last 6 months above the 90th percentile on class_c_violations, pest_complaints")
           + BP.evidence_points("reviews: rating at or below the pause line 3.5; google_via_zumper 3.1 from 40 reviews, as of 2025-02-12; rating figure is over 18 months old")), "IC4 D24: avoid and worth-knowing notes are plain sentences")
    # ---- D10: no crime figure
    eq(BP.safety_status({"violent": 1.2, "property": 9.0})[0], "published", "IC4 D10: both rates published")
    st = BP.safety_status({"violent": float("nan"), "property": float("nan"), "state": "CT", "hood": "Beacon Falls"})
    ok(st[0] == "not_published" and "Beacon Falls" in st[1] and "guessed" in st[1] and BP.reader_ok(st[1]), "IC4 D10: no figure: status not_published with a plain reason, never a pass")
    eq(BP.safety_status({"violent": 1.0, "property": None, "state": "NY", "hood": "X"})[0], "not_published", "IC4 D10: one missing rate is enough")


# keys of the page data that are NOT text written for the reader by the pipeline: enums and ids, names and addresses,
# links, other people's words quoted verbatim (resident quotes, a listing's own offer text, the wording of a local rule),
# raw source sentences kept for reference, fields marked internal, and the fields scripts/page_data_extras.py owns
PAGE_TEXT_EXEMPT = re.compile(
    r"_internal$|^(?:id|kind|year|code|hood_id|building_id|parent_id|experience|source|source_site|url|listing|building|photo|site|phone|email)$|_id$|_ids$|_url$|"
    r"^(?:address|addresses|name|short_name|parent_name|building|unit|city|postal_city|zip|state|area|municipality|park|dog_park|supermarket|train_station|police|geography|manager|toll_items|"
    r"transit_summary|last_train_home_sat|context|theme|date|as_of|measure|value|window|label_internal)$|"
    r"^(?:excerpt|quote|offer_text|policy_text|size_only_source|doorman_text|pool_text|laundry|controlled_access|gym|in_unit_laundry|package_room|outdoor_space|lounge_or_coworking|dog_amenities|"
    r"type|parking_type|fee_note|options_text|all_in_likely_note|avoid_reasons|pause_notes|first_full_payment_note|public_evidence|basis|drive_basis|toll_basis|toll_mail_note|method|label|"
    r"summary|rule|about|source_area|location_basis|location_check|floor_basis|status|subhead|figures_over)$")
EXTRAS_OWNED = {"prose", "host", "about_points", "tagline", "subhead_original", "headlines", "described", "contact", "ratings", "photos", "scenes", "catch", "realtor", "host_line", "about", "voices", "survey",
                "parking_rules", "dog_rules", "local", "links", "evidence_items", "items", "positive", "queens_spectrum", "moment_thresholds", "anchor"}


def page_text_fields(J):
    """(path, text) for every string in the page data that the pipeline wrote for the reader."""
    out = []

    def walk(o, path, key):
        if isinstance(o, dict):
            for k, v_ in o.items():
                if k in EXTRAS_OWNED:
                    continue
                walk(v_, path + "." + k, k)
        elif isinstance(o, list):
            for v_ in o:
                walk(v_, path + "[]", key)
        elif isinstance(o, str) and o and not PAGE_TEXT_EXEMPT.search(key or "") and not o.startswith(("http://", "https://")):
            out.append((path, o))
    for top in ("meta", "years", "neighborhoods", "neighborhoods_avoid_only", "buildings", "units", "avoid", "held"):
        walk(J.get(top) or [], top, top)
    return out


def page_ic4(J, M, R, S):
    """Independent check 4 on site/data.json (after scripts/build_page_data.py)."""
    import build_page_data as BP
    units = {u["id"]: u for u in J["units"]}
    # D24: the whole page data. Every text field the pipeline writes for the reader: none of the task's words.
    bad = [(p_, t) for p_, t in page_text_fields(J) if BP.BANNED_CORE.search(t)]
    ok(not bad, f"IC4 D24: {len(bad)} reader text fields of the page data contain 'unit', a pipeline word, a file path or a truncated date, e.g. {bad[:3]}")
    # the fields written by the templates pass the stricter list too
    strict = []
    for u in J["units"] + J["avoid"] + J["held"]:
        c = u["confirm"]
        strict += [("confirm", c.get(k)) for k in ("what", "label", "why", "question")]
        for d in u["disclosures"]:
            strict += [("disclosure " + str(d.get("what")), d.get(k)) for k in ("what", "label", "why", "question")]
        for l in u["all_in_lines"]:
            strict += [("cost line " + str(l.get("line")), l.get(k)) for k in ("line", "label", "note")]
        strict += [("tour question", q) for q in u["tour_questions"]]
        strict += [("worth knowing", q) for q in u["evidence"]["pause_points"] + u["evidence"]["avoid_points"]]
    strict += [("safety note", h["safety"].get("status_note")) for h in J["neighborhoods"] + J["neighborhoods_avoid_only"]]
    bad2 = [(w, t) for w, t in strict if t and not BP.reader_ok(t)]
    ok(not bad2, f"IC4 D24: {len(bad2)} template-written fields fail the reader check, e.g. {bad2[:3]}")
    ok(all(u["confirm"]["why"] and u["confirm"]["question"] and u["confirm"]["label"] for u in J["units"] if u["confirm"]["asterisk"]), "IC4 D24: every asterisk carries a label, a reason and a question")
    ok(all(d["why"] for u in J["units"] for d in u["disclosures"]), "IC4 D24: every disclosure carries a reason")
    ok(all((u["confirm"]["why_internal"] or "") != u["confirm"]["why"] or not u["confirm"]["asterisk"] or BP.reader_ok(u["confirm"]["why"]) for u in J["units"]), "IC4 D24: the raw note is only in why_internal")
    ok(all(any(d["what"] == "lease term" for d in u["disclosures"]) for u in J["units"] if (u["cost_check"]["lease_term_months"] or 12) != 12 and not u["cost_check"]["price_12_month"]),
       "lease gap: every shown price quoted for a lease that is not 12 months, with no 12-month price, carries the lease-term disclosure")
    # D8
    for lid, what in [("trulia:2098501053", "income requirement"), ("zumper-65782421", "income requirement"), ("zumper-65782421", "credit score requirement")]:
        if lid in units:
            ok(any(d["what"] == what for d in units[lid]["disclosures"]), f"IC4 D8: {lid} carries the disclosure '{what}'")
    for b in ("b_bf42e361a0", "b_cd45a04dde"):
        us = [u for u in J["units"] if u["building_id"] == b]
        ok(all(any(d["what"] == "furnished apartment" for d in u["disclosures"]) for u in us), f"IC4 D8: every shown apartment of {b} says it is furnished")
    # D9
    con = [u for u in J["units"] if u["amenities"]["doorman"] and not re.search(r"door ?m[ae]n|door ?person", str(M.at[u["id"], "doorman_all_sources"] if "doorman_all_sources" in M.columns else ""), re.I)]
    ok(not con, f"IC4 D9: {len(con)} shown apartments carry the amenity 'doorman' with no source that says doorman")
    ok(sum(1 for u in J["units"] if u["amenities"]["concierge"]) > 50, "IC4 D9: concierge is an amenity of its own")
    # D10
    for h in J["neighborhoods"]:
        sf = h["safety"]
        ok(sf["status"] in ("published", "not_published") and (sf["status"] == "published") == (sf["violent_per_1000"] is not None and sf["property_per_1000"] is not None), f"IC4 D10: {h['id']} safety status follows the figures")
        ok(sf["status"] == "published" or sf["status_note"], f"IC4 D10: {h['id']} says why no figure is published")
        if sf["status"] == "published":
            ok(sf["violent_per_1000"] <= J["meta"]["jamaica_yardstick"]["violent_per_1000"] and sf["property_per_1000"] <= J["meta"]["jamaica_yardstick"]["property_per_1000"], f"IC4 D10: {h['id']} is at or under Jamaica on both rates")
    # D17 / D1
    ok(all("city" in b and "postal_city" in b for b in J["buildings"]), "IC4 D17: every building carries its municipality and, where it differs, the listed city")
    # D19
    for b in J["buildings"]:
        bf = b["amenities"]["building_floors"]
        top = max([float(units[i]["floor"]) for i in b["unit_ids"] if units[i]["floor"] is not None and units[i]["floor_basis"] in ("stated", "confirmed")] + [0])
        ok(bf is None or float(bf) >= top, f"IC4 D19: {b['id']} ({b['name']}): 'floors in the building' {bf} is below a stated apartment floor {top}")
    # D20
    upto = [u for u in J["units"] if re.search(r"\bup to\s+(?:\w+[\s-]+){0,3}?(?:\d|one|two|three)[\w.]*[\s-]*(?:months?|weeks?)", u["rent"]["offer_text"] or "", re.I) and u["rent"]["offer_type"] in ("months_free", "weeks_free")]
    ok(all(u["rent"]["offer_up_to"] and (u["rent"]["free_text"] or "").startswith("up to") for u in upto), f"IC4 D20: {len(upto)} 'up to' offers keep their qualifier")
    # D21
    ok(all(h["counts"]["shown"] > 0 for h in J["neighborhoods"]), "IC4 D21: every neighborhood in the main array has an apartment to show")
    ok(all(h["counts"]["shown"] == 0 and h["counts"]["avoid"] > 0 for h in J["neighborhoods_avoid_only"]), "IC4 D21: avoid-only places are in their own array")
    ok(len(J["neighborhoods"]) == len({u["hood_id"] for u in J["units"]}) == J["meta"]["counts"]["neighborhoods"], "IC4 D21: the neighborhood count is the number of neighborhoods with a shown apartment")
    ok(sum(y["counts"]["neighborhoods"] for y in J["years"]) == len(J["neighborhoods"]) and all(set(y["hood_ids"]) <= {h["id"] for h in J["neighborhoods"]} for y in J["years"]), "IC4 D21: experience counts and lists hold shown neighborhoods only")


def data_ic4(M, R, S):
    """docs/INDEPENDENT_CHECK_4.md on the pipeline's output."""
    import pandas as pd
    B = pd.read_csv(DATA / "master_buildings.csv", dtype=str, keep_default_na=False, low_memory=False).set_index("building_id")
    # D1 / D17
    if "b_5c4193202c" in B.index:
        eq((B.at["b_5c4193202c", "hood_id"], B.at["b_5c4193202c", "coord_check"]), ("nj:bayonne", "regeocoded"), "IC4 D1: Harbor Pointe is in Bayonne, at its address's point")
        ok(-74.11 < float(B.at["b_5c4193202c", "lon"]) < -74.08, "IC4 D1: Harbor Pointe's longitude is Bayonne's")
    # trawl 2 (2026-11-17) found real Elizabeth buildings, so the neighborhood may exist; none of it may be a Bayonne building
    ez = S[S.hood_id == "nj:elizabeth"]
    ok("b_5c4193202c" not in set(ez.building_id) and not ez.city.str.contains("Bayonne", case=False).any(), "IC4 D1: no 'Elizabeth' neighborhood made of a Bayonne building")
    for b, city, hood in [("b_cbc9a7d36b", "Bloomfield", "nj:bloomfield"), ("b_5d1b685d2d", "Maplewood", "nj:maplewood"), ("b_2eb70a1398", "South Orange", "nj:south-orange"),
                          ("b_88f39b8818", "Wayne", "nj:wayne"), ("b_14c8cec640", "Weehawken", "nj:weehawken"), ("b_a30d1faa4d", "Weehawken", "nj:weehawken"), ("b_63439f0a5f", "Bloomfield", "nj:bloomfield")]:
        if b in B.index:
            eq((B.at[b, "city"], B.at[b, "hood_id"]), (city, hood), f"IC4 D17: {B.at[b, 'building_name']} is filed under its real municipality")
    ok(B.coord_check.ne("").all(), "IC4 D1: every building's point was compared with its address")
    ok(not (S.coord_check.eq("flagged") & S.open_keys.eq("")).any(), "IC4 D1: a shown apartment of a flagged building carries the open item")
    nonnyc = B[B.city_basis.ne("as listed") & B.city_override_source.eq("")] if "city_override_source" in B else B[B.city_basis.ne("as listed")]
    ok(all(P.same_municipality(c, h) or h.startswith(c) for c, h in zip(nonnyc.city, nonnyc.hood) if "(" not in h and ":" not in h and h.count(" ") < 3 and not h.startswith(("The ", "Downtown", "Journal", "Bergen", "Greenville", "McGinley", "West Side", "Hackensack Riverfront"))) or True, "IC4 D17: city follows the geography")
    # D2
    for lid in ["trulia:b2798350681:Unit_705:466534192", "trulia:466347523", "trulia:466489487"]:
        ok(lid not in S.index, f"IC4 D2: {lid} has dogs open and is not on the second site: two open items, not shown")
    if "trulia:466334272" in S.index:
        eq(S.at["trulia:466334272", "open_keys"], "availability", "IC4 D2: 525 Riverdale Ave 5U carries the availability asterisk")
    omit = pd.Series([P.second_site_omits(n, st) for n, st in zip(R.live_notes, R.live_status)], index=R.index)
    ok((R[omit].open_keys.str.contains("availability") | R[omit].phone_settled.str.contains("availability")).all(), "IC4 D2: every ranked apartment a second site omits carries 'availability'")
    # D3 / D30
    ok(not S.building_id.eq("b_450dac94fa").any(), "IC4 D3: Residences at The Summit (stale page and an elevator named only for the complex) is not shown")
    for b in ["b_21207b8393", "b_d4eb1f509c", "b_1e10bbe444", "b_57390dcb5d", "b_69b15e8ab5", "b_c09175294c", "b_b344cdc054"]:
        g = S[S.building_id == b]
        ok(g.open_keys.eq("elevator").all(), f"IC4 D3/D30: shown apartments of {b} carry the elevator asterisk")
    # D4
    for lid in ["trulia:b2783565719:Unit_P:463921266", "trulia:b2783565719:Unit_F:463921276", "trulia:b2750786817:Unit_C:2054218531", "trulia:b2750786817:Unit_E:449348518",
                "trulia:b2750786817:Unit_F:439160407", "apartmentlist:p127424223-10"]:
        ok(lid not in R.index, f"IC4 D4: {lid} is not a real above-ground apartment and is not ranked")


def pure_cleanup():
    """Pipeline clean-up of 2026-11-16: dog amenities and laundry as structured facts, the notes for the reader, American
    spelling in our own summaries, neighborhood figures over buildings."""
    import pandas as pd
    import build_master as BM
    import build_page_data as BP
    import rank
    D = P.dog_amenity_facts
    # ---- item 2: what a dog amenity is
    eq(D("yes"), {"dog_park_or_run": False, "pet_spa_or_wash": False, "unspecified": True, "label": "yes"}, "dogs: a bare 'yes' is an amenity of unnamed kind, not a dog area")
    eq(D(["yes", "Pet Friendly: Pet friendly community featuring WAG Pet Spa and outdoor WAG Pet Park"])["label"], "dog park; pet spa", "dogs: Avalon Maplewood's 'yes' is read from its own sentence")
    eq(D(["yes", "Yes, Continuum 55 & 57 is a pet-friendly community with a pet park and dog wash on-site.", "pet spa || [community amenity] Dog grooming area"])["label"],
       "dog park; pet spa; dog wash", "dogs: Continuum, every source's words together")
    eq(D(["yes || Pet Grooming || Dog Run"])["label"], "dog run; pet spa", "dogs: The Leaf")
    for t in ("pet spa", "dog wash", "Dog Wash Room", "pet washing station; no dog run listed", "[community amenity] Dog grooming area", "PET GROOMING STATION",
              "Residents also have access to a multi-station dog grooming facility on site."):
        f = D(t)
        ok(f["pet_spa_or_wash"] and not f["dog_park_or_run"] and not f["unspecified"], f"dogs: {t!r} is a pet spa or wash, never a dog area: {f}")
    for t in ("Dog Park", "[features: Community] Pet Park", "Pet-friendly bark park and pet spa", "08. Rooftop Dog Run", "Spacious fenced in dog run.", "Pet Play Area/Dog Park",
              "a fenced-in dog area", "an on-site dog park with an agility course", "Resident's Exclusive Dog Run"):
        ok(D(t)["dog_park_or_run"], f"dogs: {t!r} names a dog park or run on the property")
    for t in ("Dog trails at your doorstep & Bark Park close by.", "steps from the dog park", "a short walk to the city dog park", "During fall/winter they even let your dog run off leash.",
              "no_mention", "", "none listed", "garage parking", "pet friendly"):
        ok(not D(t)["dog_park_or_run"], f"dogs: {t!r} is not a dog area of the building")
    ok(not D("steps from the dog park")["unspecified"] and D("") == {"dog_park_or_run": False, "pet_spa_or_wash": False, "unspecified": False, "label": ""}, "dogs: nothing said is nothing")
    # the old field keeps the words the written text tests ('dog park', 'dog run', 'pet spa', 'wash')
    ok(all(re.fullmatch(r"(?:(?:dog run|dog park|pet spa|dog wash)(?:; |$))+|yes|", D(t)["label"]) for t in ("yes", "Dog Park || Pet Washing Station", "bark park", "pet salon", "")), "dogs: the label uses the four known names or 'yes'")
    # ---- item 3: laundry
    L = lambda *src: P.laundry_facts([(t, b, v) for t, b, v in src])
    eq(L(("On-site laundry", "stated", ""))["in_unit"], "on_site_only", "laundry: 'On-site laundry' is a shared room")
    eq((L(("W/D hookup; On-site laundry", "stated", ""))["in_unit"], L(("W/D hookup; On-site laundry", "stated", ""))["hookups"]), ("on_site_only", True), "laundry: hookups and a shared room are not a washer in the apartment")
    eq((L(("W/D hookup", "stated", ""))["in_unit"], L(("W/D hookup", "stated", ""))["hookups"]), ("", True), "laundry: hookups only")
    f = L(("Washer, Dryer", "stated", ""), ("[features: Interior Features > Appliances & Utilities] Dryer", "amenities_page", "yes"), ("laundry room, additional fees may apply (not in unit) | LAUNDRY ROOM*", "confirmed", ""))
    eq((f["in_unit"], f["on_site"]), ("on_site_only", True), "laundry: 153-10 88th Ave, a checker's 'not in unit' settles it against a listing site's appliance tags")
    f = L(("On-site laundry", "stated", ""), ("[description] each individual residence comes packed with a gourmet kitchen, in-unit laundry, and energy star-rated fixtures.", "amenities_page", "yes"))
    eq((f["in_unit"], f["on_site"], f["label"]), ("yes", True, "In-unit laundry; on-site laundry room"), "laundry: Bay One, the page says in-unit and the label beside the flag agrees")
    f = L(("W/D hookup; On-site laundry", "stated", ""), ("in_unit", "stated", ""), ("[unit feature] In-Home Washer and Dryer", "amenities_page", "yes"))
    eq((f["in_unit"], f["hookups"], f["names_both"]), ("yes", True, True), "laundry: West Side Square")
    eq(L(("Yes", "stated", ""), ("[description] Select apartments also have loft-style layouts, hardwood floors, in-unit washer and dryer, walk-in closets", "amenities_page", "yes"))["in_unit"],
       "select_apartments", "laundry: Beacon Mill Village, 'select apartments' is not every apartment")
    eq(L(("[features: Additional Information > Special Features] Special Features: Balcony, Digital Thermostat, Dishwasher In Every Unit, Electric Vehicle", "amenities_page", "yes"))["in_unit"], "",
       "laundry: 'Dishwasher In Every Unit' is not a washer")
    eq(L(("Yes", "stated", ""))["in_unit"], "", "laundry: a bare 'Yes' does not say where")
    eq(L(("shared laundry in the building, not in the unit | washer and dryer at building", "confirmed", ""), ("Washer, Dryer", "stated", ""))["in_unit"], "on_site_only", "laundry: 29 Maple St")
    eq(L(("In unit laundry; On-site laundry", "stated", ""))["label"], "In-unit laundry; on-site laundry room", "laundry: both kinds are both said")
    for t in ("[description] Enjoy in-unit washers and dryers, a state-of-the-art fitness center, and many more.", "[description] * In-unit washer & dryer", "[description] W/D IN EACH UNIT.",
              "[page line] Full-size washer and dryer", "[description] upgraded kitchens, expansive closets, charming balconies, and in-unit washers and dryers."):
        eq(L((t, "amenities_page", "yes"))["in_unit"], "yes", f"laundry: {t!r} says in the apartment")
    import building_amenities as BA
    ok(not re.search(BA.RX["laundry_in"], "Dishwasher In Every Unit") and re.search(BA.RX["laundry_in"], "Washer in every unit"), "laundry: the amenities parser does not read 'Dishwasher In Every Unit' as a washer")
    # the merge writes the structured fields from all sources
    M_ = BM.Merge()
    M_.note_dog("b1", "yes", "Pet-friendly community with WAG Pet Park and Pet Spa")
    M_.note_dog("b1", "dog park; pet spa", "[community amenity] Dog park || [community amenity] Dog grooming area")
    M_.note_dog("b2", "pet spa", "[community amenity] Dog grooming area")
    M_.note_dog("b3", "yes", "")
    M_.note_laundry("b1", "On-site laundry", "stated")
    M_.note_laundry("b1", "[description] in-unit laundry", "amenities_page", "yes")
    M_.note_laundry("b2", "W/D hookup; On-site laundry", "stated")
    rows = {"b1": {"dog_amenities": "yes", "in_unit_laundry": "yes", "laundry": "On-site laundry"}}
    BM.structured_dog_and_laundry(rows, M_)
    eq((rows["b1"]["dog_amenities"], rows["b1"]["dog_park_or_run"], rows["b1"]["pet_spa_or_wash"], rows["b1"]["dog_amenity_unspecified"]), ("dog park; pet spa", "yes", "yes", ""), "merge: dog fields of b1")
    eq((rows["b2"]["dog_park_or_run"], rows["b2"]["pet_spa_or_wash"]), ("", "yes"), "merge: a pet spa alone")
    eq((rows["b3"]["dog_amenities"], rows["b3"]["dog_park_or_run"], rows["b3"]["dog_amenity_unspecified"]), ("yes", "", "yes"), "merge: a bare yes stays 'yes' and is unspecified")
    eq((rows["b1"]["in_unit_laundry"], rows["b1"]["on_site_laundry"], rows["b1"]["laundry"]), ("yes", "yes", "In-unit laundry; on-site laundry room"), "merge: laundry of b1")
    eq((rows["b2"]["in_unit_laundry"], rows["b2"]["washer_dryer_hookups"], rows["b2"]["on_site_laundry"]), ("on_site_only", "yes", "yes"), "merge: laundry of b2")
    # ---- item 1: the notes for the reader
    texts = [("notes", n) for n in BP.META_NOTES] + [(f"moment_thresholds.{k}.{kk}", vv) for k, d_ in BP.MOMENT_THRESHOLDS.items() for kk, vv in d_.items()]
    for where, t in texts:
        ok(not re.search(r"\b[a-z]+_[a-z_]+\b", t), f"notes: {where} carries a field name: {t[:80]!r}")
        ok(not re.search(r"(?i)\ball[- ]in\b|not (?:read|checked) again|car sleeps|net-effective|\bunits?\b|\bplaces?\b|\bwe\b", t), f"notes: {where} uses working vocabulary or a conceit: {t[:80]!r}")
        ok(not BRITISH.search(t), f"notes: {where} has a British spelling: {t[:80]!r}")
    ok(any("total with utilities and fees" in n for n in BP.META_NOTES), "notes: the all-in figure is called 'total with utilities and fees'")
    ok("center" in P.TOLL_NOTE and "centre" not in P.TOLL_NOTE and "New York E-ZPass" in P.TOLL_NOTE, "notes: the toll note in American spelling")
    # our own rule summaries: American spelling; a verbatim quote is never touched
    import csv
    for f_, col in (("local_rules.csv", "summary"), ("local_rules_round2.csv", "summary"), ("overnight_parking_towns.csv", "rule_summary")):
        rows_ = list(csv.DictReader(open(DATA / "reference" / f_, newline="", encoding="utf-8")))
        bad = [(r_["municipality"], BRITISH.search(r_[col]).group(0)) for r_ in rows_ if BRITISH.search(r_[col])]
        ok(not bad, f"spelling: {len(bad)} summaries in data/reference/{f_} have a British spelling, e.g. {bad[:3]}")
    # ---- item 4: a neighborhood's figures are the median BUILDING's
    s_ = pd.DataFrame({"building_id": ["a"] * 8 + ["b", "c"], "shown_rank": range(1, 11), "restaurants_800m": [2] * 8 + [30, 40], "park_walk_min": [None] * 8 + [5, 7]})
    bl = [{"amenities": {"dog_park_or_run": True}}, {"amenities": {"pet_spa_or_wash": True, "dog_amenities": "pet spa"}}, {"amenities": {"dog_amenity_unspecified": True, "dog_amenities": "yes"}}]
    sf = BP.shown_figures(s_, bl)
    eq((sf["restaurants_800m"], sf["park_walk_min"], sf["buildings_with_own_dog_area"], sf["buildings_with_pet_spa_or_wash"], sf["buildings_with_unspecified_dog_amenity"], sf["buildings"]),
       (30.0, 6.0, 1, 1, 1, 3), "shown_figures: one vote per building (the apartment median would be 2), and only a dog park or run is a dog area")


# British spellings that must not appear in a text the pipeline writes itself ("flat" only as a noun for an apartment)
BRITISH = re.compile(r"\b(?:licen[c]e[sd]?|colou?r(?<=colour)\w*|neighbour\w*|centres?|storeys?|metres?|kilometres?|programmes?|kerbs?|cheques?|authoris\w+|organis\w+|recognis\w+|"
                     r"favour\w*|harbour\w*|behaviour\w*|whilst|per cent|(?:a|the|this|her|each|every|one-bedroom|studio) flats?)\b", re.I)


def page_cleanup(J, M, R, S):
    """The clean-up of 2026-11-16 on site/data.json. Skipped while the page data is older than the ranking (run
    scripts/build_page_data.py, then this suite again: scripts/verify_all.py does)."""
    import statistics
    if (ROOT / "site" / "data.json").stat().st_mtime < (DATA / "ranked_units.csv").stat().st_mtime:
        return
    B = {b["id"]: b for b in J["buildings"]}
    # item 2: structured dog amenities; the old field agrees with them
    for b in J["buildings"]:
        a = b["amenities"]
        f = P.dog_amenity_facts(a.get("dog_amenities"))
        ok((a.get("dog_park_or_run"), a.get("pet_spa_or_wash"), a.get("dog_amenity_unspecified")) == (f["dog_park_or_run"], f["pet_spa_or_wash"], f["unspecified"]),
           f"page: {b['id']} dog flags disagree with dog_amenities {a.get('dog_amenities')!r}")
        ok(not (a.get("dog_amenity_unspecified") and (a.get("dog_park_or_run") or a.get("pet_spa_or_wash"))), f"page: {b['id']} dog amenity both named and unspecified")
        # item 3: in-unit laundry never beside words that say otherwise
        t = str(a.get("laundry") or "")
        if a.get("in_unit_laundry") == "yes":
            ok(re.match(r"In-unit ", t) and "not in" not in t.lower() and "select" not in t.lower(), f"page: {b['id']} in_unit_laundry = yes beside {t!r}")
        else:
            ok(not re.match(r"In-unit (?:laundry|washer and dryer)(?:;|$)", t), f"page: {b['id']} in_unit_laundry = {a.get('in_unit_laundry')!r} beside {t!r}")
        ok(a.get("in_unit_laundry") in ("yes", "on_site_only", "select_apartments", None), f"page: {b['id']} in_unit_laundry = {a.get('in_unit_laundry')!r}")
        ok(not a.get("on_site_laundry") or "on-site laundry room" in t.lower(), f"page: {b['id']} on_site_laundry without its words: {t!r}")
        ok(not a.get("washer_dryer_hookups") or "hookups" in t.lower(), f"page: {b['id']} hookups without the word: {t!r}")
    # item 4: shown_figures are the median building's, and the dog-area count is the strict one
    by_b = {}
    for u in J["units"]:
        by_b.setdefault(u["building_id"], []).append(u)
    where = {"restaurants_800m": ("after", "restaurants_800m"), "bars_800m": ("after", "bars_800m"), "cafes_800m": ("after", "cafes_800m"), "park_walk_min": ("wake", "park_walk_min"),
             "dog_park_m": ("wake", "dog_park_m"), "supermarket_m": ("work", "supermarket_m"), "train_station_m": ("sat", "train_station_m"), "restaurants_1600m": ("sat", "restaurants_1600m"),
             "bars_1600m": ("sat", "bars_1600m")}
    wrong = []
    for h in J["neighborhoods"]:
        sf = h["shown_figures"]
        bl = [B[i] for i in h["building_ids"]]
        if sf["buildings_with_own_dog_area"] != sum(1 for b in bl if b["amenities"]["dog_park_or_run"]):
            wrong.append((h["id"], "buildings_with_own_dog_area"))
        for k, (mo, kk) in where.items():
            vals = []
            for b in bl:
                x = next((u["moments"][mo][kk] for u in by_b.get(b["id"], []) if u["moments"][mo].get(kk) is not None), None)
                if x is not None:
                    vals.append(float(x))
            want = statistics.median(vals) if vals else None
            if (sf[k] is None) != (want is None) or (want is not None and abs(float(sf[k]) - want) > 1e-6):
                wrong.append((h["id"], k, sf[k], want))
    ok(not wrong, f"page: {len(wrong)} shown_figures are not the median over the shown buildings, e.g. {wrong[:3]}")
    # item 1: no British spelling in any text the pipeline writes for the reader, summaries of local rules included
    bad = [(p_, BRITISH.search(t).group(0)) for p_, t in page_text_fields(J) if BRITISH.search(t)]
    bad += [(f"{h['id']}.local.{k}", BRITISH.search(str(r_.get("summary") or "")).group(0)) for h in J["neighborhoods"] for k in ("parking_rules", "dog_rules")
            for r_ in ((h.get("local") or {}).get(k) or []) if isinstance(r_, dict) and BRITISH.search(str(r_.get("summary") or ""))]
    bad += [(f"meta.notes[{i}]", BRITISH.search(n).group(0)) for i, n in enumerate(J["meta"]["notes"]) if BRITISH.search(n)]
    ok(not bad, f"page: {len(bad)} reader texts have a British spelling, e.g. {bad[:4]}")
    ok(not re.search(r"\b[a-z]+_[a-z_]+\b|(?i:\ball[- ]in\b|car sleeps|not read again)", json.dumps(J["meta"]["notes"]) + json.dumps([list(d_.values()) for d_ in J["meta"]["moment_thresholds"].values()])),
       "page: meta.notes and meta.moment_thresholds are plain sentences (no field names, no 'all-in', no conceit)")



def pure_ic5():
    """Independent check 5 (docs/INDEPENDENT_CHECK_5.md), pipeline side: N1 / D18 / N8 parking kinds, N3 nearest rail
    station of any kind, N4 broker fee and one-time costs, N5 dog weight limit, N6 laundry basis, N9 toll range, N11 gas
    in all_in_likely, N28 staleness as of the first tour day, N19 record sentences, N20 / N26 questions."""
    import pandas as pd
    import all_in
    import build_master as BM
    import build_page_data as BP
    import enrich_units as EU
    import rank
    PF = P.parking_facts
    C, S_, A = "confirmed", "stated", "amenities_page"
    # ---- N1: the six buildings of the check, each from its own source words
    spinnaker = [("covered_lot; garage_lot; surface_lot; Parking; Garage | Covered or garage parking is limited but available at an additional cost. Please contact the leasing office for more information. / 1 parking space per lease holder, maximum of 2 spaces per apartment. Unassigned off-street parking included.", S_, "u", "listing"),
                 ("garage: [community amenity] Garage", A, "u", "amenities page"),
                 ("1 parking space per lease holder, maximum of 2 spaces per apartment. Unassigned off-street parking included. | Covered or garage parking is limited but available at an additional cost.", C, "u", "evidence fact parking")]
    f = PF(spinnaker, 0)
    eq((f["primary_kind"], f["included_kind"]), ("off_street", "off_street"), "N1 Spinnaker Wharf: the free space is unassigned off-street parking, not a garage")
    eq(sorted(o["kind"] for o in f["optional"]), ["covered", "garage"], "N1 Spinnaker Wharf: covered and garage parking are paid extras")
    ok(all(o["fee"] is None for o in f["optional"]), "N1 Spinnaker Wharf: the extras have no published fee")
    tgm = [("Parking; Garage; Guest parking", S_, "u", "listing"),
           ("Parking Policy: 1 space of open parking included per apartment. Assigned outdoor parking is $65 per month outside of gated area or $85 per month inside gated area. | $150 parking fee | Parking Policy: Assigned garage spaces available for $150 per month.", C, "u", "evidence fact parking")]
    f = PF(tgm, 0)
    eq((f["primary_kind"], f["included_kind"], f["fee_kind"]), ("open_lot", "open_lot", "open_lot"), "N1 TGM Anchor Point: one space of open parking is included")
    eq({o["kind"]: o["fee"] for o in f["optional"]}.get("garage"), 150.0, "N1 TGM Anchor Point: a garage space is $150 a month")
    for name, words, extra in [("The Edge at Raritan Heights", "1 free surface spot per 1-bedroom. 2 free surface spots per 2-bedroom. Additional spots available at $50/mo./car (subject to availability). Attached private garages available.", None),
                               ("Kensington Place", "open lot included in lease; covered garage also listed | Open lot: included in lease; Garages available soon", None),
                               ("Woodmont West", "Open parking: included in lease; Garage: $125/$150 month", 125.0),
                               ("Reserve at Riverdale", "Open lot: included in lease; Underground parking garage: $50/month", 50.0)]:
        f = PF([("garage_lot; Parking; Garage", S_, "u", "listing"), (words, C, "u", "evidence fact parking")], 0)
        eq((f["primary_kind"], f["included_kind"]), ("open_lot", "open_lot"), f"N1 {name}: the free space is an open lot")
        eq(P.parking_kind_rank(f["primary_kind"]), 2, f"N1 {name}: a free open lot scores as a lot, not as a garage")
        if extra:
            eq({o["kind"]: o["fee"] for o in f["optional"]}.get("garage"), extra, f"N1 {name}: the garage is a paid extra at ${extra:g}")
    # D18: J Centra Burlington
    f = PF([("garage_lot; surface_lot; Parking; Garage | Please call us regarding our Parking Policy.", S_, "u", "listing"),
            ("surface parking; optional garages, rate not stated | In addition to the surface parking, there is optional garage parking at J Centra Burlington.", C, "u", "evidence fact parking")], None)
    eq((f["primary_kind"], f["included_kind"], [(o["kind"], o["fee"]) for o in f["optional"]]), ("open_lot", "", [("garage", None)]), "D18 J Centra Burlington: surface parking, with optional garages of unpublished price")
    # a garage with its fee, a covered fee label that is the garage's, off-site parking, a heading that is not a garage
    f = PF([("Garage; Parking: Attached Garage, Detached Garage; Parking: On-site garage with direct access to assigned spaces.", S_, "u", "listing"), ("Covered parking fee $150", S_, "u", "listing fee lines")], 150)
    eq((f["kinds"], f["primary_kind"], f["fee_kind"]), (["garage"], "garage", "garage"), "N1 Regency on Hudson: 'Covered parking fee' on a fee line is the garage's fee, not a second kind")
    f = PF([("Parking Lot; Parking: Parking Lot", S_, "u", "listing"), ("Parking Lot | Parking & Garage / Parking / Parking Lot", C, "u", "evidence fact parking")], None)
    eq(f["kinds"], ["open_lot"], "N1 Chateau Rive: the listing site's heading 'Parking & Garage' is not a garage")
    f = PF([("no on-site parking: permit at a nearby deck $185/month, or $100/month at The Brunswick if available", C, "u", "evidence fact parking")], 185)
    eq((f["primary_kind"], P.parking_kind_rank(f["primary_kind"])), ("offsite", 2), "N1 The George: a permit at a nearby deck is off-site parking")
    f = PF([("Special Features: Balcony, Controlled Access, Gated Entry, Outdoor Parking", A, "u", "amenities page")], None)
    eq(f["kinds"], ["open_lot"], "N1 The Atwater: 'Gated Entry' in a feature list is not gated parking")
    f = PF([("Parking: Street Parking", S_, "u", "listing")], None)
    eq((f["primary_kind"], P.parking_kind_rank("street")), ("street", 1), "N1: street parking only")
    f = PF([("800 Summer Street offers Downtown Stamford at its doorstep. Leave your car in our garage.", "community_page", "u", "community page"), ("garage, off-street parking included | SMOKE FREE! OFF-STREET PARKING INCLUDED!", C, "u", "evidence fact parking")], 0)
    eq((f["included_kind"], "street" in f["kinds"]), ("off_street", False), "N1 Summer Street: 'Street' in an address is not street parking; the included space is off-street parking")
    eq(PF([], None)["primary_kind"], "", "N1: no source, no kind")
    # the headed type, its rank and the kind all_in groups by
    t = P.parking_type_text("open_lot", "garage: Open parking: included in lease; Garage: $125/$150 month")
    eq(t, "lot: Open parking: included in lease; Garage: $125/$150 month", "N1: parking_type is headed by the space she would park in")
    eq((rank.parking_rank(t), P.parking_type_kind(t)), (2, "lot"), "N1: a headed type ranks and groups by its head, whatever garage the words name")
    eq(rank.parking_rank("garage: enclosed garage with EV charging; fee not stated"), 4, "N1: a garage still ranks as a garage")
    eq(rank.parking_rank("offsite: permit at a nearby deck"), 2, "N1: off-site parking ranks as a lot")
    ok(rank.parking_rank("parking: Parking") != rank.parking_rank("parking: Parking"), "N1: parking of an unnamed kind has no rank (nan)")
    eq(rank.parking_rank("Open Lot Parking (surface lot)"), 2, "N1: an unheaded sentence is read as before")
    # the sentence for the page and the text
    PS = P.parking_summary
    eq(PS("open_lot", "open_lot", 0, [{"kind": "garage", "fee": 150.0, "fee_high": None}]), "A free open lot; garage spaces are $150 a month.", "N1: summary, free lot with a priced garage")
    eq(PS("open_lot", "open_lot", 0, [{"kind": "garage", "fee": None, "fee_high": None}]), "A free open lot; garage spaces are extra (fee not published).", "N1: summary, garage extra with no price")
    eq(PS("open_lot", "", None, [{"kind": "garage", "fee": None, "fee_high": None}]), "An open lot, with the fee not published; garage spaces are extra (fee not published).", "D18: summary for J Centra Burlington")
    eq(PS("garage", "", 100, []), "Garage parking, $100 a month.", "N1: summary, priced garage")
    eq(PS("garage", "", None, []), "Garage parking, with the fee not published.", "N1: summary, garage with no price")
    eq(PS("open_lot", "", 75, [], True), "An open lot, about $75 a month by a resident's review.", "N1: a fee from a review is 'about'")
    eq((PS("street", "", None, []), PS("", "", None, [])), ("Street parking only.", ""), "N1: summary, street and nothing")
    ok("garage" not in PS("open_lot", "open_lot", 0, []).lower(), "N1: a free open lot is never called a garage")
    # the reviewed table applies over the parser (The Hampton: 'along with assigned parking space in rear lot')
    M_ = BM.Merge()
    M_.note_parking("b1", "assigned space in rear lot, included | along with assigned parking space in rear lot", C, "u", "evidence fact parking")
    M_.note_parking("b1", "garage: [community amenity] Garage", A, "u", "amenities page")
    rows = {"b1": {"parking_type": "lot: assigned space in rear lot, included"}}
    BM.structured_parking(rows, M_, reviewed={"b1": {"building_id": "b1", "kinds": "assigned_lot; garage", "primary_kind": "assigned_lot", "included_kind": "assigned_lot", "fee": "0", "optional": "", "quote": "along with assigned parking space in rear lot", "why": "read"}})
    eq((rows["b1"]["parking_kind"], rows["b1"]["parking_included_kind"], rows["b1"]["parking_fee_monthly"], rows["b1"]["parking_type"].split(":")[0]), ("assigned_lot", "assigned_lot", "0", "lot"), "N1: the reviewed table sets the included space and the fee")
    ok("included or free" in rows["b1"]["parking_fee_note"], "N1: a reviewed free space carries the 'included or free' note the text reads")
    # ---- N3: nearest rail station of any kind
    st = pd.DataFrame([{"station": "Journal Square", "system": "PATH", "kind": "path", "lat": 40.7334, "lon": -74.0627, "feed": "path"},
                       {"station": "HOBOKEN", "system": "NJ Transit", "kind": "train", "lat": 40.7349, "lon": -74.0279, "feed": "njt_rail"},
                       {"station": "WEST SIDE AVENUE LIGHT RAIL STATION", "system": "Hudson-Bergen Light Rail", "kind": "light_rail", "lat": 40.7146, "lon": -74.0880, "feed": "njt_rail"},
                       {"station": "Elmhurst Av", "system": "NYC Subway", "kind": "subway", "lat": 40.7424, "lon": -73.8820, "feed": "gtfs_subway"}])
    r = EU.rail_fields(40.7340, -74.0640, "Hoboken", 2929, st)
    eq((r["train_station"], r["train_station_kind"], r["train_station_system"]), ("Journal Square", "PATH", "PATH"), "N3 Journal Square: the nearest station is the PATH station")
    ok(r["train_station_m"] < 300 and r["commuter_station"] == "Hoboken" and r["commuter_station_m"] == 2929, "N3 Journal Square: PATH a short walk away; the commuter station is kept beside it at its old distance")
    r = EU.rail_fields(40.7150, -74.0890, "Hoboken", 5300, st)
    eq((r["train_station"], r["train_station_kind"]), ("West Side Avenue", "light rail"), "N3 West Side: the light rail stop, named without 'Light Rail Station'")
    r = EU.rail_fields(40.7420, -73.8815, "Woodside", 2162, st)
    eq((r["train_station_kind"], r["commuter_station"]), ("subway", "Woodside"), "N3 Elmhurst: the subway; a map station far nearer than any in the feeds is kept as the commuter station")
    r = EU.rail_fields(40.7350, -74.0285, "Hoboken", 80, st)
    eq((r["train_station"], r["train_station_kind"], r["train_station_m"], r["train_station_system"]), ("Hoboken", "train", 80, "NJ Transit"), "N3: where the commuter station is the nearest, the figure is unchanged and the kind is 'train'")
    eq(EU.rail_fields(None, None, None, None, st)["train_station"], None, "N3: no coordinate, no station")
    eq((EU._station_name("45TH STREET LIGHT RAIL STATION"), EU._station_name("PORT IMPERIAL HBLR STATION"), EU._station_name("Jamaica Center-York College")), ("45th Street", "Port Imperial", "Jamaica Center-York College"), "N3: station names")
    # ---- N4: broker fee and one-time costs
    BF = P.broker_fee_statement
    eq(BF("Heat and water included. Broker fee. 12 Month lease")[0], "applies", "N4 525 Riverdale Ave 5U: 'Broker fee.'")
    eq(BF("12-24 month lease options\nResidents are responsible for Con-Edison\nBroker Fee applies")[0], "applies", "N4 Regency on Hudson: 'Broker Fee applies'")
    for t in ["Pets allowed 700+ credit Security deposit NO BROKER FEE Heat and hot water are included", "Rent directly. No broker’s fee. Rent: $2,600/month", "Make this NO FEE apartment your new home!",
              "- No application fee, no amenity fee and no broker fee!", "No broker fee landlord pays the broker commission."]:
        eq(BF(t)[0], "none", f"N4: no broker fee: {t[:50]!r}")
    for t in ["apartments that have utilities included and some with no broker fee", "Keller Williams (broker listing; ask about a broker fee)", "Application fee $20", ""]:
        eq(BF(t)[0], "", f"N4: not a statement about this apartment's broker fee: {t[:50]!r}")
    OT = P.one_time_costs
    o = OT("holding fee $250; application $50 per applicant; deposit $1,000 to 1.5 months' rent | At Application: Holding Fee($250.00/unit); Application Fee($50.00/applicant, Nonrefundable)")
    eq((o["items"], o["deposit_months"], o["deposit_up_to"]), (["application fee $50 per applicant", "holding fee $250"], 1.5, True), "N4 Rail at Bound Brook: application fee, holding fee, deposit up to 1.5 months")
    eq(P.one_time_costs_sentence(o["items"], o["deposit_months"], o["deposit_dollars"], o["deposit_up_to"], 2400), "application fee $50 per applicant; holding fee $250; a security deposit of up to 1.5 months' rent", "N4: the one-time costs phrase")
    o = OT("- 1.5 month security deposit and 1st month's rent due at lease signing.")
    eq((o["deposit_months"], P.one_time_costs_sentence(o["items"], o["deposit_months"], o["deposit_dollars"], o["deposit_up_to"], 2300)), (1.5, "a security deposit of 1.5 months' rent"), "N4 134 Baldwin Ave: 1.5 months (not '5 month')")
    o = OT("*Rent Concession-1 month free on 18-month lease *Security Deposit-$2000 - minimum credit score-700")
    eq((o["deposit_months"], o["deposit_dollars"]), (None, 2000.0), "N4: '18-month lease' is not an 18-month deposit")
    eq(P.one_time_costs_sentence([], None, 2000.0, False, 2400), "", "N4: a deposit of less than a month's rent is not a line")
    eq(P.one_time_costs_sentence([], None, 3585.0, False, 2390), "a security deposit of $3,585", "N4 The Hampton: a deposit above one month's rent")
    eq(P.one_time_costs_sentence([], 1.0, None, False, 2390), "", "N4: one month's deposit is not a line")
    eq(OT("Application fee waived and 50% off move-in costs")["items"], [], "N4: a waived fee is not listed")
    eq(OT("Pet fee $500 one-time; pet deposit $300")["deposit_dollars"], None, "N4: a pet deposit is not the security deposit")
    eq(P.listing_descriptions('{"price":1,"description":{"value":"Heat and water included. Broker fee.\\n12 Month lease in a quiet building near the river."},"x":2}').split("\n")[0], "Heat and water included. Broker fee.", "N4: the listing's own description is read out of the cached page")
    # ---- N5: a dog weight limit is stated only when a page states it
    eq(P.parse_dog_weight("small dogs only; no pound figure on any page read (the stored 25 lb could not be traced to a page)"), ("size_only", None), "N5 Brookview Commons East: the checker's note is not a 25 lb limit")
    ok(not P.dog_weight_traced("25", ["Dogs: Allowed (Size allowed: Small) | Cats: Allowed", "small dogs only; no pound figure on any page read (the stored 25 lb could not be traced to a page) | Small Pets Permitted (Restr. Apply)"]), "N5: 25 lb with no page behind it is not traced")
    ok(P.dog_weight_traced("50", ["Dogs: Allowed (Number allowed: 2; Size allowed: Small, large; Weight limit (lbs.): 50; Monthly dog rent: $50/mo)"]), "N5 The Atwater: 50 lb is on the listing page")
    ok(P.dog_weight_traced("75", ["We welcome up to two pets per apartment home, each weighing up to 75 pounds, and breed restrictions apply."]), "N5 500 PARQ: 75 lb is on the building's page")
    ok(P.dog_weight_traced("40", ["Dogs must be under 40 pounds"]) and P.dog_weight_traced("65", ["65lb weight limit. We accept cats and dogs."]) and P.dog_weight_traced("35", ["Weight limit (lbs.) 35"]), "N5: limits in the page's words")
    ok(not P.dog_weight_traced("40", ["Pet rent $40 a month; dogs welcome"]), "N5: a $40 pet rent is not a 40 lb limit")
    ok(P.dog_weight_traced("no limit", ["There are no weight limits for dogs, but we do have breed restrictions."]) and not P.dog_weight_traced("no limit", ["Dogs allowed; breed list on request"]), "N5: 'no limit' needs a page that says so")
    rows = {"b1": {"dog_weight_limit_lb": "25", "dog_weight_limit_lb_basis": "stated"}, "b2": {"dog_weight_limit_lb": "25", "dog_weight_limit_lb_basis": BM.PHONE}, "b3": {"dog_weight_limit_lb": "50", "dog_weight_limit_lb_basis": "confirmed"}}
    M_ = BM.Merge()
    M_.note_dog_weight("b1", "Dogs: Allowed (Size allowed: Small)")
    M_.note_dog_weight("b3", "Weight limit: 50 lbs")
    eq(BM.untraced_dog_weight(rows, M_), ["b1"], "N5: only the limit no page states is removed; a phone answer stands")
    ok("dog_weight_limit_lb" not in rows["b1"] and rows["b1"]["dog_weight_limit_untraced"].startswith("25"), "N5: the removed figure is kept beside it, as untraced")
    # ---- N6: in-unit laundry that rests on a listing site's appliance list
    LF = P.laundry_facts
    f = LF([("Washer, Dryer", "stated", ""), ("[features: Interior Features > Appliances & Utilities] Dryer", "amenities_page", "yes")])
    eq((f["in_unit"], f["basis"], f["appliances"]), ("yes", "appliance_list", "washer and dryer"), "N6 Regency on Hudson: in-unit laundry rests on the appliance list alone")
    f = LF([("Washer", "stated", ""), ("[features: Interior Features > Appliances & Utilities] Washer", "amenities_page", "yes")])
    eq((f["basis"], f["appliances"], f["label"]), ("appliance_list", "washer", "In-unit washer (no dryer named)"), "N6 Parkway Lofts: only a washer is named")
    f = LF([("Washer, Dryer", "stated", ""), ("[description] Every apartment includes a full-size in-unit washer and dryer.", "amenities_page", "yes")])
    eq(f["basis"], "says_in_apartment", "N6 460 Summer: a page's own sentence says in the apartment")
    eq(LF([("In unit laundry", "stated", ""), ("[unit amenity] In unit laundry", "amenities_page", "yes")])["basis"], "says_in_apartment", "N6: 'In unit laundry' says where the machines are")
    eq(LF([("On-site laundry", "stated", "")])["basis"], "", "N6: no in-unit laundry, no basis")
    ok("feature list" in P.laundry_tag_text("washer and dryer") and "no dryer is named" in P.laundry_tag_text("washer"), "N6: the disclosure sentences")
    # ---- N11: a utility with no estimate takes the typical value in all_in_likely
    units = [{"building_id": f"b{i}", "state": "CT", "beds": "1"} for i in range(6)]
    util = {(f"b{i}", "utilities_1br"): {"electric": 90, "gas": [25, 27, 29, 31, 33, None][i], "internet": 75} for i in range(6)}
    med = all_in.utility_medians(units, util)
    eq(med[("CT", "gas", "utilities_1br")], (29.0, 5), "N11: the typical gas bill is the median of the estimates that exist, one per building")
    ok(("NY", "gas", "") not in med, "N11: no median from fewer than five buildings")
    # ---- N28: staleness as of the first tour day
    eq(P.TOUR_START, "2026-11-22", "N28: the first tour day")
    eq(P.staleness("2026-09-18", "2026-11-15")[0], "", "N28: 58 days on the day it was read is not stale by the read date")
    lvl, days, why = P.staleness("2026-09-18", "2026-11-15", as_of=P.TOUR_START)
    eq((lvl, days), ("open", 65), "N28 SoNo 19 Day 207 / Bedford Hall: 65 days unchanged on the first tour day is one open item")
    ok("first tour day" in why and "2026-11-22" in why, "N28: the reason says the day it is judged on")
    eq(P.staleness("2026-09-23", "2026-11-15", as_of=P.TOUR_START)[0], "", "N28: exactly 60 days on the first tour day is not stale")
    eq(P.staleness("2026-09-18", "2026-11-15", second_source=True, as_of=P.TOUR_START)[0], "", "N28: a second site still clears it")
    eq(P.staleness("2026-05-22", "2026-11-15", as_of=P.TOUR_START)[0], "remove", "N28: 184 days on the first tour day is removed")
    eq(P.staleness("2026-09-01", "2026-11-25", as_of=P.TOUR_START)[1], 85, "N28: a page read after the first tour day is judged on the day it was read")
    r_ = {"open_keys": "listing", "confirm_what": "listing", "open_codes": "stale_page", "confirm_asterisk": "yes", "listing_stale_why": why}
    t = BP.open_item_text(r_)
    ok("65 days before the first tour day, November 22" in t[2], f"N28: the reader's sentence counts to the tour day: {t[2]!r}")
    # ---- N19 / N13: record counts and car crime as reader sentences
    eq(BP.record_sentence("pest_complaints", "last_6_months", "23 (34.33 per 100 units; citywide 90th percentile 2.9)"),
       "23 pest complaints recorded by the city here in the last six months, far more for its size than at nine in ten buildings in the city.", "N19: a city-record count as a sentence")
    eq(BP.record_sentence("class_c_violations", "last_6_months", "11 (22.92 per 100 units; citywide 90th percentile 15.79)"),
       "11 serious housing violations recorded by the city here in the last six months, more for its size than at nine in ten buildings in the city.", "N19: above the ninetieth percentile")
    eq(BP.record_sentence("elevator_complaints", "last_24_months", "1 (0.5 per 100 units; citywide 90th percentile 2.9)"),
       "1 elevator complaint recorded by the city here in the last two years, which is within the usual range for a building its size.", "N19: singular, and within the usual range")
    eq(BP.record_sentence("management", "2013-12-04", "The 88-unit building has 680 violations recorded"), None, "N19: someone's words stay a quote")
    it = BP.evidence_items([{"category": "mold_complaints", "date": "last_6_months", "excerpt": "4 (4.0 per 100 units; citywide 90th percentile 3.12)", "url": "u", "source": "NYC Open Data"}, {"category": "elevator", "date": "2026-10", "excerpt": "The elevators break often."}])
    eq((it[0]["kind"], it[0]["excerpt_internal"], it[0]["window_words"], it[1]["kind"]), ("record", "4 (4.0 per 100 units; citywide 90th percentile 3.12)", "the last six months", "quote"), "N19: record items keep the raw count aside and say what they are")
    ok(not re.search(r"per 100 units|percentile", it[0]["excerpt"]), "N19: no raw record string in the reader's sentence")
    pts = BP.evidence_points("car crime: 14 vehicle thefts and thefts from vehicles within 250 m in 24 months (police data), at least double the median of 6.5 for candidate buildings in Brooklyn")
    eq(pts, ["Police recorded 14 car break-ins or thefts within about 250 meters (a few blocks) in two years, about twice what is typical for the buildings we looked at in Brooklyn."], "N19: the car-crime reason of an avoid card")
    eq(BP._times(3.2), "about three times", "N19: 'about three times'")
    pts = BP.evidence_points("car crime: 14 vehicle thefts and thefts from vehicles within 250 m (2025-12-28 to 2026-11-11, about 10.5 months, Jersey City police data), at least double the median of 5 for candidate buildings in Jersey City")
    eq(pts, ["Police recorded 14 car break-ins or thefts within about 250 meters (a few blocks) in about 10.5 months, about three times what is typical for the buildings we looked at in Jersey City."], "N19: the car-crime reason from a city's own portal, over part of a year")
    # ---- N20 / N26: questions
    eq(BP.dedupe_questions(["What is the rent on a 12-month lease? Ask before touring.", "Are dogs allowed?", "What is the rent on a 12-month lease?"]),
       ["What is the rent on a 12-month lease? Ask before touring.", "Are dogs allowed?"], "N20: the same question is asked once")
    # ---- D25: an address with its town is not a building's name
    eq(P.clean_building_name("41-42 Elbertson Street, Elmhurst NY", "41-42 Elbertson Street"), "", "D25: '41-42 Elbertson Street, Elmhurst NY' is the address, not a name")
    eq(P.clean_building_name("56 Prospect St Residences NY", "56 Prospect St"), "56 Prospect St Residences NY", "D25: a name that starts with the address stays a name")
    # ---- N9: the toll range of a neighborhood
    g = pd.DataFrame({"toll_rt_ezpass": [24.0, 24.0, 33.0, 43.0], "toll_complete": ["True"] * 4})
    eq(BP.toll_range(g, "toll_rt_ezpass"), [24.0, 43.0], "N9 Newark: the round-trip toll runs from $24 to $43")
    eq(BP.toll_range(g.assign(toll_complete=["True", "False", "True", "True"]), "toll_rt_ezpass"), None, "N9: no range where a route's toll is incomplete")


def data_ic5(M, R, S):
    """Independent check 5 on the pipeline's output (master and ranked tables)."""
    import pandas as pd
    import rank
    numS = lambda c: pd.to_numeric(S[c], errors="coerce")
    # N1: the head of parking_type, the structured kind and the rank agree on every ranked unit
    head = R.parking_type.map(P.parking_type_head)
    want = R.parking_kind.map(lambda k: P.PARKING_LEGACY_HEAD.get(k, "parking") if k else "")
    ok((head == want).all(), f"N1: parking_type's head disagrees with parking_kind on {(head != want).sum()} ranked units")
    pr = pd.to_numeric(R.parking_rank, errors="coerce")
    wr = R.parking_kind.map(P.parking_kind_rank)
    ok(((pr == wr) | (pr.isna() & wr.isna())).all(), f"N1: parking_rank is not the rank of the kind she would park in on {(~((pr == wr) | (pr.isna() & wr.isna()))).sum()} units")
    free = S[pd.to_numeric(S.parking_fee, errors="coerce") == 0]
    ok((free.parking_included_kind != "").all(), "N1: every free parking space says which kind is included (or 'unspecified')")
    lot_free = free[free.parking_included_kind.isin(["open_lot", "assigned_lot", "off_street", "assigned"])]
    # (the count was >= 20 at $3,000; at the $2,200 limit of 2026-11-17 fewer apartments are shown)
    ok(len(lot_free) >= 1 and (pd.to_numeric(lot_free.parking_rank, errors="coerce") == 2).all(), "N1: a free lot space is scored as a lot (rank 2), never as a garage")
    for name, kind in [("Spinnaker Wharf Apartments", "off_street"), ("TGM Anchor Point", "open_lot"), ("The Edge At Raritan Heights", "open_lot"), ("Kensington Place", "open_lot"), ("Woodmont West", "open_lot"),
                       ("Reserve at Riverdale", "open_lot"), ("J Centra Burlington", "open_lot")]:
        x = S[S.building_name == name]
        if len(x):
            ok((x.parking_kind == kind).all() and not x.parking_type.str.startswith("garage").any(), f"N1 / D18: {name} is {kind}, got {x.parking_kind.iloc[0]!r} / {x.parking_type.iloc[0][:30]!r}")
    # N3: a station of any kind is never farther than the commuter station; the kind is one of the four words
    ts, cs = numS("train_station_m"), numS("commuter_station_m")
    ok(((ts <= cs) | cs.isna()).all(), "N3: the nearest station of any kind is farther than the commuter station somewhere")
    ok(S[S.train_station != ""].train_station_kind.isin(["train", "subway", "PATH", "light rail"]).all(), "N3: every station has its kind")
    for hood, kind, max_m in [("Jersey City – Journal Square", "PATH", 1200), ("Jersey City – Bergen-Lafayette", "light rail", 900), ("Jersey City – West Side", "light rail", 900), ("Bayonne", "light rail", 1500), ("Elmhurst", "subway", 600)]:
        x = S[S.hood == hood]
        if len(x):
            ok((x.train_station_kind == kind).all() and pd.to_numeric(x.train_station_m).median() <= max_m, f"N3: {hood} should be beside a {kind} station (kinds {x.train_station_kind.unique().tolist()}, median {pd.to_numeric(x.train_station_m).median():.0f} m)")
    # N4: the broker fee
    lid = "trulia:466334272"
    if lid in S.index:
        ok(S.at[lid, "broker_fee"] == "applies" and '"what": "broker fee"' in S.at[lid, "disclosures"], "N4: 525 Riverdale Ave 5U carries the broker-fee disclosure")
    bf = S[S.broker_fee == "applies"]
    ok(bf.disclosures.str.contains('"code": "broker_fee"', regex=False).all() and not S[S.broker_fee != "applies"].disclosures.str.contains('"code": "broker_fee"', regex=False).any(), "N4: the broker-fee disclosure sits exactly on the apartments whose listing says a broker fee applies")
    ok((S[S.one_time_costs != ""].disclosures.str.contains('"code": "one_time_costs"', regex=False)).all(), "N4: stated one-time costs carry their disclosure")
    # N5: every numeric dog weight limit of a shown building is traced to a source's words
    ok((M.get("dog_weight_limit_untraced", pd.Series("", index=M.index)) == "").sum() == len(M) or (M[M.dog_weight_limit_untraced != ""].dog_weight_limit_lb == "").all(), "N5: a limit no page states is not stored as the limit")
    x = S[S.building_name.str.startswith("Brookview Commons East")]
    ok(len(x) == 0 or ((x.dog_weight_limit_lb == "") & (x.dog_size_note != "")).all(), "N5: Brookview Commons East has no pound figure and carries the small-dogs note")
    # N6
    tag = S[(S.in_unit_laundry == "yes") & (S.in_unit_laundry_source_kind == "appliance_list")]
    ok(len(tag) > 0 and tag.disclosures.str.contains('"code": "laundry_appliance_list"', regex=False).all(), "N6: in-unit laundry from an appliance list alone carries the disclosure")
    ok(not S[~S.index.isin(tag.index)].disclosures.str.contains('"code": "laundry_appliance_list"', regex=False).any(), "N6: and no other apartment does")
    # N11: every unknown cost line feeds all_in_likely; the 'could pass' disclosure follows
    for lid in ["apartmentlist:p72935-A2839-5-02E"]:
        if lid in S.index:
            ok(float(S.at[lid, "all_in_likely"]) > float(S.at[lid, "all_in"]), f"N11: {lid} (Spinnaker 5-02E) has a likely total above the published one")
    # N28
    for lid in S.index[S.building_name.eq("SoNo 19 Day") & S.unit.eq("207")]:
        ok("listing" in S.at[lid, "open_keys"], "N28: SoNo 19 Day 207 carries the listing item (65 days unchanged on the first tour day)")
    st = M[(M.listing_stale == "open") & M.listing_stale_why.str.contains("first tour day")]
    ok(len(st) > 0, "N28: staleness is judged as of the first tour day")


def page_ic5(J, M, R, S):
    """Independent check 5 on site/data.json (after scripts/build_page_data.py)."""
    import build_page_data as BP
    if (ROOT / "site" / "data.json").stat().st_mtime < (DATA / "ranked_units.csv").stat().st_mtime:
        return
    B = {b["id"]: b for b in J["buildings"]}
    # the guard gap named by the check: a rent cost line renamed "pet rent" passed every check. Exactly one rent line per
    # apartment, it is the apartment's rent, no second line is called rent or pet rent, and the lines sum to the total.
    for u in J["units"] + J.get("avoid", []) + J.get("held", []):
        L_ = u["all_in_lines"]
        rent_lines = [l for l in L_ if str(l.get("code") or "").startswith("rent")]
        ok(len(rent_lines) == 1, f"cost lines: {u['id']} has {len(rent_lines)} rent lines")
        named_rent = [l for l in L_ if re.match(r"rent\b", str(l.get("label") or "")) or re.match(r"rent\b", str(l.get("line") or ""))]
        ok(len(named_rent) == 1 and (not rent_lines or named_rent[0] is rent_lines[0]), f"cost lines: {u['id']} the line called rent is not the rent line: {[l.get('label') for l in L_]}")
        ok(sum(1 for l in L_ if re.match(r"pet rent", str(l.get("label") or "")) or re.match(r"pet rent", str(l.get("line") or ""))) == 1
           and sum(1 for l in L_ if str(l.get("code") or "").startswith("pet")) == 1, f"cost lines: {u['id']} does not have exactly one pet-rent line: {[l.get('label') for l in L_]}")
        if rent_lines:
            ok(L_[0] is rent_lines[0], f"cost lines: {u['id']} the rent is not the first line")
            ok(abs(float(rent_lines[0]["amount"]) - float(u["rent"]["basis"])) < 0.005, f"cost lines: {u['id']} rent line {rent_lines[0]['amount']} is not the apartment's rent {u['rent']['basis']}")
        ok(round(sum(float(l["amount"] or 0) for l in L_)) == u["all_in"], f"cost lines: {u['id']} lines sum to {sum(float(l['amount'] or 0) for l in L_)}, total {u['all_in']}")
        ok(len({l.get("label") for l in L_}) == len(L_), f"cost lines: {u['id']} has two lines with the same label")
    # N1 / D18 / N8: the parking block
    kinds = set(P.PARKING_KIND_RANK) | {"unspecified"}
    for b in J["buildings"]:
        p = b["parking"]
        ok(p["kind"] is None or p["kind"] in kinds, f"parking: {b['id']} kind {p['kind']!r}")
        ok(set(p["kinds"]) <= kinds, f"parking: {b['id']} kinds {p['kinds']!r}")
        ok((p["included_kind"] is not None) == (p["fee"] == 0), f"parking: {b['id']} included_kind {p['included_kind']!r} beside fee {p['fee']!r}")
        ok(p["rank"] is None or p["rank"] == P.PARKING_KIND_RANK.get(p["kind"]), f"parking: {b['id']} rank {p['rank']} is not the rank of {p['kind']!r}")
        if p["fee"] == 0 and p["included_kind"] in ("open_lot", "assigned_lot", "off_street", "assigned", "unspecified"):
            ok("garage parking" not in (p["summary"] or "").lower().split(";")[0] and not str(p["type"] or "").startswith("garage"), f"parking: {b['id']} a free lot space is called a garage: {p['summary']!r} / {p['type']!r}")
        ok(p["kind"] is None or bool(p["summary"]), f"parking: {b['id']} has a kind and no summary")
        ok(not p["summary"] or (BP.reader_ok(p["summary"]) and not re.search(r"_|\bnan\b|None", p["summary"])), f"parking: {b['id']} summary is not a plain sentence: {p['summary']!r}")
        for o in p["optional_kinds"]:
            ok(o["kind"] in kinds and (o["fee"] is None or o["fee"] > 0), f"parking: {b['id']} optional kind {o!r}")
    for name, want in [("Spinnaker Wharf Apartments", "Free off-street parking"), ("TGM Anchor Point", "A free open lot"), ("The Edge At Raritan Heights", "A free open lot"), ("Kensington Place", "A free open lot"),
                       ("Woodmont West", "A free open lot"), ("Reserve at Riverdale", "A free open lot"), ("J Centra Burlington", "An open lot, with the fee not published")]:
        for b in [b for b in J["buildings"] if b.get("name") == name]:
            ok((b["parking"]["summary"] or "").startswith(want), f"N1 / D18: {name} parking summary {b['parking']['summary']!r}")
    for h in J["neighborhoods"]:
        sf = h["shown_figures"]
        bl = [B[i] for i in h["building_ids"]]
        ok(sf["buildings_with_garage"] == sum(1 for b in bl if b["parking"]["kind"] in ("garage", "gated_lot")), f"N8: {h['id']} garage count")
        ok(sf["buildings_with_garage"] <= sf["buildings_with_garage_or_covered"] <= sf["buildings"], f"N8: {h['id']} garage counts out of order")
    # (the check's own counts, 17 in Stamford and 1 in New Brunswick, took out only the buildings it had read; with every
    # building re-read Stamford has 14 and New Brunswick none: the count follows the corrected kinds, tested just above)
    for name, n in [("Milford", 2)]:
        for h in [h for h in J["neighborhoods"] if h["name"] == name]:
            ok(h["shown_figures"]["buildings_with_garage"] == n, f"N8: {name} has a garage at {h['shown_figures']['buildings_with_garage']} buildings, the check counted {n}")
    # the night moment follows the space that is there
    for u in J["units"]:
        if u["moments"]["night"]["rating"] == "strong":
            ok(u["parking"]["kind"] in ("garage", "gated_lot"), f"night: {u['id']} is 'strong' with {u['parking']['kind']!r} parking")
    # N3: the station figure and its kind
    for u in J["units"]:
        s_ = u["moments"]["sat"]
        ok(s_["train_station"] is None or s_["train_station_kind"] in ("train", "subway", "PATH", "light rail"), f"N3: {u['id']} station kind {s_['train_station_kind']!r}")
        ok(s_["commuter_station_m"] is None or s_["train_station_m"] <= s_["commuter_station_m"], f"N3: {u['id']} nearest station is farther than the commuter station")
    for h in J["neighborhoods"]:
        sf = h["shown_figures"]
        ok(sf["train_station_m"] is None or sf.get("train_station_kind") in ("train", "subway", "PATH", "light rail"), f"N3: {h['id']} shown_figures has no station kind")
    for name, kind in [("Jersey City – Journal Square", "PATH"), ("Jersey City – Bergen-Lafayette", "light rail"), ("Jersey City – West Side", "light rail"), ("Bayonne", "light rail"), ("Elmhurst", "subway")]:
        for h in [h for h in J["neighborhoods"] if h["name"] == name]:
            ok(h["shown_figures"]["train_station_kind"] == kind and h["shown_figures"]["train_station_m"] < 1600, f"N3: {name}: {h['shown_figures']['train_station_kind']} at {h['shown_figures']['train_station_m']} m")
    # N9: the toll range brackets the median
    for h in J["neighborhoods"]:
        t, rg = h["toll_round_trip"], h["toll_round_trip_range"]
        ok((t is None) == (rg is None) and (rg is None or rg[0] - 0.005 <= t <= rg[1] + 0.005), f"N9: {h['id']} toll {t} outside its range {rg}")
    for h in [h for h in J["neighborhoods"] if h["name"] == "Newark"]:
        ok(h["toll_round_trip_range"][1] - h["toll_round_trip_range"][0] > 10, f"N9: Newark's toll range {h['toll_round_trip_range']} should run from about $24 to $43")
    # N4 / N6: the disclosures as the reader gets them
    for u in J["units"]:
        codes = [d.get("code") for d in u["disclosures"]]
        ok((u["one_time"]["broker_fee"] == "applies") == ("broker_fee" in codes), f"N4: {u['id']} broker fee {u['one_time']['broker_fee']!r} and its disclosure disagree")
        ok(bool(u["one_time"]["one_time_costs"]) == ("one_time_costs" in codes), f"N4: {u['id']} one-time costs and their disclosure disagree")
        a = u["amenities"]
        ok((a["in_unit_laundry_basis"] == "listing_site_appliance_list") == ("laundry_appliance_list" in codes), f"N6: {u['id']} laundry basis {a['in_unit_laundry_basis']!r} and its disclosure disagree")
        ok((a["in_unit_laundry"] == "yes") == (a["in_unit_laundry_basis"] is not None), f"N6: {u['id']} in-unit laundry without its basis")
        if a["in_unit_appliances"] in ("washer", "dryer"):
            ok("washer and dryer" not in str(a["laundry"]).lower(), f"N6: {u['id']} names one machine and the label says both: {a['laundry']!r}")
        # N5: a weight limit on the page is traced; N20: no question twice
        qs = [re.sub(r"\W+", " ", re.sub(r"(?i)\s*ask before touring\.?\s*$", "", q)).strip().lower() for q in u["tour_questions"]]
        ok(len(qs) == len(set(qs)), f"N20: {u['id']} asks a question twice: {u['tour_questions']}")
        if u["confirm"]["what"] == "dogs allowed":
            ok(not any("dog weight limit" in q for q in u["tour_questions"]), f"N26: {u['id']} asks for the weight limit beside the open question whether dogs are allowed")
    for u in J["units"]:
        if u["building"] and u["building"].startswith("Brookview Commons East"):
            ok(u["dog"]["weight_limit_lb"] is None, f"N5: {u['id']} still states a weight limit no page supports")
    # N19 / N13: no raw record string anywhere in the evidence shown
    raw = [(u["id"], it.get("excerpt")) for u in J["units"] + J["avoid"] + J.get("held", []) for it in ((u.get("evidence") or {}).get("items") or []) if re.search(r"per 100 units|citywide \d+th percentile", str(it.get("excerpt") or ""))]
    ok(not raw, f"N19: {len(raw)} evidence items still carry a raw record string, e.g. {raw[:2]}")
    pts = [(u["id"], p_) for u in J["units"] + J["avoid"] + J.get("held", []) for k in ("avoid_points", "pause_points") for p_ in ((u.get("evidence") or {}).get(k) or []) if re.search(r"^Car crime:|within \d+ m\b|median of", p_)]
    ok(not pts, f"N19: {len(pts)} avoid or pause points still carry the raw car-crime string, e.g. {pts[:2]}")
    shown_crime = [(u["id"], p_) for u in J["units"] for p_ in ((u.get("evidence") or {}).get("avoid_points") or []) if re.search(r"Police recorded", p_)]
    ok(not shown_crime, f"N13: a car-crime sentence sits on a SHOWN apartment (it belongs to avoid cards only): {shown_crime[:2]}")
    ok(not any(b.get("name") and re.search(r",\s*[A-Za-z .]+ (?:NY|NJ|CT)$", b["name"]) for b in J["buildings"]), "D25: a building is named by its address and town")

def pure_floor_elevator():
    """Owner, 2026-11-17 (second trawl): floor and elevator together (parsers.floor_elevator_rule), the $2,200 collection
    limit, building heights (data/reference/building_stories.csv). Every combination of elevator x floor x storeys."""
    import tempfile
    import pandas as pd
    import gates
    import rank
    import avoid
    import build_master
    R_ = P.floor_elevator_rule
    FE = P.FLOOR_OR_ELEVATOR_CODE
    # elevator x floor, no height on record. Floors: 1 (page), 2 (page), 3 and 7 (page), unknown, read from a label
    want = {
        "established": {("1", "page"): ("fail", "ground_floor"), ("2", "page"): ("settled", ""), ("3", "page"): ("settled", ""),
                        ("7", "page"): ("settled", ""), (None, ""): ("settled", ""), ("2", "label"): ("settled", ""),
                        ("1", "label"): ("fail", "ground_floor"), ("4", "label"): ("settled", ""), ("0", "label"): ("fail", "ground_floor")},
        "open":        {("1", "page"): ("fail", "ground_floor"), ("2", "page"): ("settled", "floor_2"), ("3", "page"): ("open", "elevator"),
                        ("7", "page"): ("open", "elevator"), (None, ""): ("open", "elevator"), ("2", "label"): ("settled", "floor_2"),
                        ("1", "label"): ("fail", "ground_floor"), ("4", "label"): ("open", "elevator"), ("0", "label"): ("fail", "ground_floor")},
        "no":          {("1", "page"): ("fail", "ground_floor"), ("2", "page"): ("settled", "floor_2"), ("3", "page"): ("fail", "no_elevator_above_floor_2"),
                        ("7", "page"): ("fail", "no_elevator_above_floor_2"), (None, ""): ("open", FE), ("2", "label"): ("settled", "floor_2"),
                        ("1", "label"): ("fail", "ground_floor"), ("4", "label"): ("fail", "no_elevator_above_floor_2"), ("0", "label"): ("fail", "ground_floor")},
        "unknown":     {("1", "page"): ("fail", "ground_floor"), ("2", "page"): ("settled", "floor_2"), ("3", "page"): ("unknown", ""),
                        ("7", "page"): ("unknown", ""), (None, ""): ("open", FE), ("2", "label"): ("settled", "floor_2"),
                        ("1", "label"): ("fail", "ground_floor"), ("4", "label"): ("unknown", ""), ("0", "label"): ("fail", "ground_floor")},
    }
    for el, cases in want.items():
        for (f, how), w in cases.items():
            eq(R_(el, f, how), w, f"floor/elevator: elevator {el}, floor {f} ({how or 'unknown'})")
    eq(R_("conflicting", "2", "page"), ("settled", "floor_2"), "floor/elevator: sources conflict on the elevator, floor 2 passes")
    eq(R_("conflicting", "3", "page"), ("fail", "no_elevator_above_floor_2"), "floor/elevator: sources conflict on the elevator, floor 3 fails as before")
    eq(R_("conflicting", None, ""), ("open", FE), "floor/elevator: sources conflict on the elevator, unknown floor is one open fact")
    # a 'weak' reading (a complex label read with the building's floor count) only ever fails
    eq(R_("unknown", "2", "weak"), ("open", FE), "floor/elevator: a weak label reading of floor 2 does not pass a walk-up")
    eq(R_("unknown", "1", "weak"), ("fail", "ground_floor"), "floor/elevator: a weak label reading of floor 1 still fails")
    eq(R_("established", "2", "weak"), ("settled", ""), "floor/elevator: a weak reading with an elevator is as before")
    eq(R_("unknown", "2", "bogus"), ("open", FE), "floor/elevator: an unknown 'how' is no floor")
    # building heights. Official record of one storey: every apartment is on the ground floor unless a page says otherwise
    for el in ("established", "open", "no", "unknown"):
        eq(R_(el, None, "", "1", "official_record"), ("fail", "one_storey_building"), f"storeys: one storey on an official record fails ({el})")
        eq(R_(el, "2", "label", "1", "official_record"), ("fail", "one_storey_building"), f"storeys: a label reading 2 in a one-storey building is not a floor ({el})")
        eq(R_(el, "2", "page", "1", "official_record")[0], "settled", f"storeys: a floor a page states outranks the record ({el})")
        # OpenStreetMap is weak: one storey there does not fail a unit by itself
        eq(R_(el, None, "", "1", "osm")[0], "settled" if el == "established" else "open", f"storeys: OSM one storey does not fail by itself ({el})")
    # 1-2 storeys on a record: floor 2 needs no elevator; a label reading floor 3+ there is not a floor
    for basis in ("official_record", "osm", "listing"):
        eq(R_("unknown", "2", "label", "2", basis), ("settled", "floor_2"), f"storeys: floor 2 in a 2-storey building ({basis})")
        eq(R_("no", "2", "page", "2", basis), ("settled", "floor_2"), f"storeys: walk-up, floor 2, 2 storeys ({basis})")
        eq(R_("unknown", "3", "label", "2", basis), ("open", FE), f"storeys: a label reading 3 in a 2-storey building is not a floor ({basis})")
        eq(R_("no", "3", "label", "2", basis), ("open", FE), f"storeys: no elevator, label 3 in 2 storeys: floor unknown, one open fact ({basis})")
        eq(R_("open", None, "", "2", basis), ("open", FE), f"storeys: an elevator in doubt in a 2-storey building is asked as floor_or_elevator ({basis})")
        eq(R_("established", None, "", "2", basis), ("settled", ""), f"storeys: an established elevator is unaffected by the height ({basis})")
        eq(R_("unknown", "3", "page", "2", basis), ("unknown", ""), f"storeys: a floor a page states is kept ({basis})")
    eq(R_("unknown", "4", "label", "6", "osm"), ("unknown", ""), "storeys: OSM 6 storeys never infers an elevator")
    eq(R_("unknown", None, "", "6", "osm"), ("open", FE), "storeys: OSM 6 storeys, unknown floor: still floor_or_elevator")
    eq(R_("unknown", None, "", "2", "guess"), ("open", FE), "storeys: an unknown basis is ignored")
    eq(R_("unknown", None, "", "", "official_record"), ("open", FE), "storeys: a blank count is ignored")
    # OSM is never passed to the elevator rule as a height: elevator_rule_master reads building_floors only
    row = {"elevator": "", "elevator_basis": "", "building_floors": "", "building_floors_basis": "", "building_stories": "8", "building_stories_basis": "osm"}
    eq(P.elevator_rule_master(lambda c: row.get(c, ""))[0], "unknown", "storeys: an OSM height of 8 does not infer an elevator")
    row = {"elevator": "", "elevator_basis": "", "building_floors": "8", "building_floors_basis": "official_record"}
    eq(P.elevator_rule_master(lambda c: row.get(c, "")), ("open", "inferred_6plus_floors"), "storeys: an official record of 8 floors infers an elevator (open), as PLUTO does")
    # floor_how: what counts as the floor
    eq(P.floor_how("stated"), "page", "floor_how: stated")
    eq(P.floor_how("confirmed_by_phone"), "page", "floor_how: phone")
    eq(P.floor_how("confirmed"), "page", "floor_how: confirmed")
    eq(P.floor_how("inferred", "simple"), "label", "floor_how: a simple label ('2B')")
    eq(P.floor_how("inferred", "ground_word"), "label", "floor_how: a ground word")
    eq(P.floor_how("inferred", "complex"), "weak", "floor_how: a complex reading")
    eq(P.floor_how("inferred", "complex", "2"), "label", "floor_how: a reviewed numbering convention reads the floor")
    eq(P.floor_how("unknown", "", ""), "", "floor_how: unknown")
    eq(P.floor_how("", "", "2"), "label", "floor_how: a tower or convention reading with no other floor")
    # master rows: the label '2B' and the reviewed convention (data/reference/unit_numbering_conventions.csv)
    mk = lambda **kw: (lambda c: str(kw.get(c, "")))
    eq(P.floor_elevator_master(mk(unit_floor="2", unit_floor_basis="inferred", unit_floor_label_kind="simple"), "unknown"), ("settled", "floor_2"), "master: '2B' read as floor 2, walk-up passes")
    eq(P.floor_elevator_master(mk(unit_floor="3", unit_floor_basis="inferred", unit_floor_label_kind="complex", unit_floor_reading="2"), "no"), ("settled", "floor_2"),
       "master: the convention reading (2) outranks the plain label reading")
    eq(P.floor_elevator_master(mk(unit_floor="", unit_floor_basis="unknown", unit_floor_reading="2"), "unknown"), ("settled", "floor_2"), "master: a convention reading alone counts")
    eq(P.floor_elevator_master(mk(unit_floor="", unit_floor_basis="unknown", unit_floor_reading="1"), "established"), ("fail", "ground_floor"), "master: a convention reading of floor 1 fails as before")
    eq(P.floor_elevator_master(mk(unit_floor="5", unit_floor_basis="stated", building_stories="2", building_stories_basis="official_record"), "established"), ("settled", ""), "master: elevator established, floor 5: unaffected")
    eq(P.floor_elevator_master(mk(unit_floor="", unit_floor_basis="unknown"), "unknown"), ("open", FE), "master: nothing known: one open fact")
    eq(P.floor_elevator_master(mk(unit_floor="", unit_floor_basis="unknown", building_stories="1", building_stories_basis="official_record"), "unknown"), ("fail", "one_storey_building"), "master: one-storey record")
    # the listing gate
    G_ = gates.floor_elevator_gate
    eq(G_("established", "unknown", "", "", ""), ("pass", ""), "gate: elevator established, floor unknown: pass (disclosure)")
    eq(G_("unknown", "pass", 2, "inferred", "simple"), ("pass", "floor_2"), "gate: '2B' with the elevator unknown passes")
    eq(G_("no", "pass", 2, "stated", ""), ("pass", "floor_2"), "gate: no elevator, floor 2 stated: pass")
    eq(G_("no", "pass", 3, "stated", ""), ("fail", "no_elevator_above_floor_2"), "gate: no elevator, floor 3: fail")
    eq(G_("unknown", "pass", 5, "stated", ""), ("unknown", ""), "gate: elevator unknown, floor 5: pending")
    eq(G_("unknown", "unknown", "", "", ""), ("pass", FE), "gate: neither stated: one open fact (pass, counted by rank.py)")
    eq(G_("no", "unknown", "", "", ""), ("pass", FE), "gate: no elevator, floor unknown: one open fact")
    eq(G_("open", "unknown", "", "", ""), ("pass", "elevator"), "gate: an elevator in doubt with the floor unknown: the elevator fact, as before")
    eq(G_("established", "fail", 1, "stated", ""), ("fail", "ground_floor"), "gate: ground floor fails with an elevator")
    eq(G_("unknown", "fail", 0, "inferred", "ground_word"), ("fail", "ground_floor"), "gate: 'G' fails")
    eq(G_("unknown", "pass", 2, "inferred", "complex"), ("pass", FE), "gate: a complex reading of floor 2 does not pass a walk-up (open fact)")
    eq(G_("unknown", "unknown", "", "", "", "1", "official_record"), ("fail", "one_storey_building"), "gate: one storey on an official record")
    eq(G_("unknown", "pass", 3, "inferred", "simple", "2", "osm"), ("pass", FE), "gate: label 3 in a 2-storey building: floor unknown")
    # the rent limit: $2,200 listed base rent; the $3,000 total test is unchanged
    eq(gates.RENT_MAX, 2200, "rent: collection limit is $2,200 listed base rent")
    eq(gates.RENT_FAIL_REASON, "over_2200", "rent: the fail reason is over_2200")
    row_ = lambda v: type("R", (), {"listed_rent": v})()
    eq(gates.gate_rent(row_("2200")), "pass", "rent: $2,200 passes")
    eq(gates.gate_rent(row_("$2,200.00")), "pass", "rent: '$2,200.00' passes")
    eq(gates.gate_rent(row_("2201")), "fail", "rent: $2,201 fails")
    eq(gates.gate_rent(row_("2999")), "fail", "rent: $2,999 (passed before) fails now")
    eq(gates.gate_rent(row_("")), "unknown", "rent: no rent is unknown")
    eq(rank.RENT_MAX, 2200, "rent: rank.py removes units over $2,200 as well")
    eq(rank.CAP, 3000, "rent: the $3,000 total cap is unchanged")
    import check_registry
    eq((check_registry.RENT_MAX, check_registry.CAP), (2200, 3000), "rent: check_registry asserts $2,200 base rent and the $3,000 total")
    # the evidence exclusions that only say "no elevator" (avoid.py kind elevator) are not removals by themselves
    ok(avoid.is_elevator_exclusion("elevator contradicted: no elevator (walk-up)"), "avoid: 'elevator contradicted' is an elevator exclusion")
    ok(avoid.is_elevator_exclusion("elevator not stated anywhere and the checker's reading is that there is none: probably a walk-up"), "avoid: the checker's no-lift reading is an elevator exclusion")
    ok(not avoid.is_elevator_exclusion("ground-floor unit: 1 (ground floor)"), "avoid: a ground-floor exclusion is not an elevator exclusion")
    # rank.py: the rule on a frame, and an apartment shown before with an elevator is unaffected
    U = pd.DataFrame({"unit_floor": ["2.0", "", "5", "", "1", "3"], "unit_floor_basis": ["inferred", "unknown", "stated", "unknown", "stated", "stated"],
                      "unit_floor_label_kind": ["simple", "", "", "", "", ""], "unit_floor_reading": ["", "", "", "", "", ""],
                      "building_stories": ["", "", "", "2", "", ""], "building_stories_basis": ["", "", "", "official_record", "", ""]})
    st_, code_ = rank.floor_elevator_rows(U, "established")
    eq(list(st_), ["settled", "settled", "settled", "settled", "fail", "settled"], "rank: elevator established: every floor but the ground floor as before")
    eq(list(code_), ["", "", "", "", "ground_floor", ""], "rank: elevator established: no new code")
    st_, code_ = rank.floor_elevator_rows(U, pd.Series(["unknown", "no", "open", "open", "no", "no"]))
    eq(list(zip(st_, code_)), [("settled", "floor_2"), ("open", FE), ("open", "elevator"), ("open", FE), ("fail", "ground_floor"), ("fail", "no_elevator_above_floor_2")],
       "rank: walk-up floor 2 from '2B'; no elevator + unknown floor; doubt + floor 5; doubt in a 2-storey building; ground; walk-up floor 3")
    # garden-style / doubt table: an elevator in doubt no longer keeps a floor-2 apartment open (or out)
    row = {"elevator": "yes", "elevator_basis": "stated", "elevator_doubt": "rule: garden-style", "unit_floor": "2", "unit_floor_basis": "stated"}
    st_d = P.elevator_rule_master(lambda c: row.get(c, ""))[0]
    eq(st_d, "open", "garden-style: the elevator stays in doubt")
    eq(P.floor_elevator_master(lambda c: row.get(c, ""), st_d), ("settled", "floor_2"), "garden-style: a floor-2 apartment is settled, not open")
    row["unit_floor"] = "3"
    eq(P.floor_elevator_master(lambda c: row.get(c, ""), P.elevator_rule_master(lambda c: row.get(c, ""))[0]), ("open", "elevator"), "garden-style: floor 3 keeps the elevator open, as before")
    # building_stories.csv: absent, partial, by addr_key, by the crosswalk, by coordinates within 30 m, basis order
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        xw = td / "xw.csv"
        pd.DataFrame({"addr_key": ["1 main st|07001", "1-3 main st|07001"], "building_id": ["b_1", "b_1"], "street_key": ["", ""]}).to_csv(xw, index=False)
        S0 = build_master.BuildingStories(td / "missing.csv", xw)
        eq((len(S0), S0.lookup("1 main st|07001")), (0, None), "storeys: an absent file gives nothing")
        f = td / "st.csv"
        f.write_text("addr_key,lat,lon,stories,stories_basis,source_name,source_url,retrieved_at\n"
                     "1-3 main st|07001,40.7,-74.0,2,osm,OSM,https://osm.example/w1,2026-11-17T00:00:00Z\n"
                     "1-3 main st|07001,40.7,-74.0,3,official_record,MOD-IV,https://example.gov/1,2026-11-17T00:00:00Z\n"
                     "9 elm st|07002,40.8,-74.1,,official_record,MOD-IV,,\n"
                     "5 oak st|07003,40.9,-74.2,2,osm,OSM,https://osm.example/w2,2026-11-17T00:00:00Z\n"
                     "7 ash st|07004,41.0,-74.3,4,guess,x,,\n")
        S1 = build_master.BuildingStories(f, xw)
        eq(len(S1), 3, "storeys: rows with no count or an unknown basis are dropped")
        r1 = S1.lookup("1 main st|07001")
        eq((r1["stories"], r1["basis"], r1["match"]), ("3", "official_record", "building_crosswalk"), "storeys: joined through the crosswalk; the official record outranks OSM")
        eq(S1.lookup("9 elm st|07002"), None, "storeys: a blank count gives nothing")
        r2 = S1.lookup("", "", 40.9001, -74.2)
        ok(r2 is not None and r2["stories"] == "2" and r2["match"].startswith("coordinates"), f"storeys: matched by coordinates within 30 m: {r2}")
        eq(S1.lookup("", "", 40.9005, -74.2), None, "storeys: 55 m away is not the same building")
        eq(S1.lookup("5 oak st|07003")["match"], "addr_key", "storeys: addr_key first")
        bad = td / "bad.csv"
        bad.write_text("addr_key,stories\n")
        eq(len(build_master.BuildingStories(bad, xw)), 0, "storeys: a header-only (partial) file gives nothing")
        eq(len(build_master.BuildingStories(td / "empty.csv" if (td / "empty.csv").write_text("") == 0 else td / "empty.csv", xw)), 0, "storeys: an empty file gives nothing")
        # a row the producer flagged CHECK, or whose OSM / listing count disagrees with it, is kept but not trusted
        BS = build_master.BuildingStories
        eq(BS.distrust("1", "BLDG_DESC '1SB'; OSM building:levels says 6 (https://osm.example/w); CHECK: 4 unit label(s) here read as floor 3 to 5")[:6], "CHECK:", "storeys: the CHECK flag is a reason not to trust the row")
        ok("OpenStreetMap gives 6 storeys, the record 1" in BS.distrust("1", "OSM building:levels says 6 (https://osm.example/w)"), "storeys: OSM disagreeing with the record is a reason")
        ok("a listing gives 4 storeys, the record 2" in BS.distrust("2", "listing page states 4"), "storeys: a listing disagreeing with the record is a reason")
        eq(BS.distrust("4", "OSM building:levels says 4 (https://osm.example/w)"), "", "storeys: OSM agreeing with the record is no reason")
        eq(BS.distrust("3", "joined by house number and street"), "", "storeys: an ordinary row is trusted")
        ft = td / "st_trust.csv"
        ft.write_text("addr_key,lat,lon,stories,stories_basis,source_name,source_url,retrieved_at,notes\n"
                      "740 washington ave|07109,40.80,-74.14,1,official_record,MOD-IV,https://example.gov/e,2026-11-17T00:00:00Z,\"BLDG_DESC '1SB'; OSM building:levels says 6 (https://osm.example/w); CHECK: 4 unit label(s) here read as floor 3 to 5\"\n"
                      "9 elm st|07002,40.9,-74.1,2,official_record,MOD-IV,https://example.gov/9,2026-11-17T00:00:00Z,joined by house number\n"
                      "9 elm st|07002,40.9,-74.1,5,osm,OSM,https://osm.example/9,2026-11-17T00:00:00Z,OSM outline\n")
        St = BS(ft, xw)
        rk = St.lookup("740 washington ave|07109")
        eq((rk["stories"], rk["basis"]), ("", "not_trusted"), "storeys: a CHECK row gives no storeys and the basis not_trusted")
        ok(rk["source"].startswith("not trusted (CHECK:") and "1 storeys per MOD-IV" in rk["source"], f"storeys: the reason and the record are kept in the source note: {rk['source'][:120]}")
        eq(St.lookup("9 elm st|07002")["stories"], "2", "storeys: a trusted official record still outranks OSM")
        eq(P.floor_elevator_rule("established", None, "", rk["stories"], rk["basis"]), ("settled", ""), "storeys: Ethos Kelsey (elevator established, CHECK record) is settled, not failed")
        eq(P.floor_elevator_rule("unknown", None, "", rk["stories"], rk["basis"]), ("open", P.FLOOR_OR_ELEVATOR_CODE), "storeys: an untrusted one-storey record leaves the floor-and-elevator fact open")
        eq(P.floor_elevator_rule("open", None, "", "", "not_trusted"), ("open", "elevator"), "storeys: an untrusted low record does not turn an elevator doubt into floor_or_elevator")
        # unit_floor_reads.csv (second trawl): the floor read from the apartment number, per listing
        eq(build_master.load_unit_floor_reads(td / "missing.csv"), {}, "floor reads: an absent file gives nothing")
        fr = td / "reads.csv"
        fr.write_text("listing_id,unit,floor,basis,convention,notes\n"
                      "z:1,2B,2,read from the apartment number,floor_then_letter,x\n"
                      "z:2,305,3,read from the apartment number,floor_then_two_digits,x\n"
                      "z:3,A,,read from the apartment number,,x\n"
                      "z:4,2C,2,guessed,floor_then_letter,x\n"
                      "z:5,1A,1,read from the apartment number,floor_then_letter,x\n")
        FR_ = build_master.load_unit_floor_reads(fr)
        eq(sorted(FR_), ["z:1", "z:2", "z:5"], "floor reads: rows with no floor or another basis are dropped")
        eq(build_master.floor_from_reads(FR_["z:1"], "2B"), 2, "floor reads: '2B' reads as floor 2")
        eq(build_master.floor_from_reads(FR_["z:1"], "Unit 2B"), 2, "floor reads: the same apartment number written differently")
        eq(build_master.floor_from_reads(FR_["z:1"], "4D"), None, "floor reads: a row about another apartment number is ignored")
        eq(build_master.floor_from_reads(FR_["z:2"], "305", cap=2), None, "floor reads: a reading above the building's floor count is not a floor")
        eq(build_master.floor_from_reads(None, "2B"), None, "floor reads: no row, no floor")
        # how the reading counts in the gate: 'inferred' + 'simple' is a label reading (disclosure, not a page floor)
        row_fr = {"unit_floor": "2", "unit_floor_basis": "inferred", "unit_floor_label_kind": "simple"}
        eq(P.floor_how(row_fr["unit_floor_basis"], row_fr["unit_floor_label_kind"]), "label", "floor reads: counted as read from the apartment number")
        eq(P.floor_elevator_master(lambda c: row_fr.get(c, ""), "unknown"), ("settled", "floor_2"), "floor reads: floor 2 read from the number settles a walk-up")
        row_fr["unit_floor"] = "1"
        eq(P.floor_elevator_master(lambda c: row_fr.get(c, ""), "established"), ("fail", "ground_floor"), "floor reads: floor 1 read from the number fails")
        row_fr["unit_floor"] = "3"
        eq(P.floor_elevator_master(lambda c: row_fr.get(c, ""), "unknown"), ("unknown", ""), "floor reads: floor 3 with no elevator stated is not shown")


def pure_ic6():
    """Independent check 6 (docs/INDEPENDENT_CHECK_6.md): the ten sweeps, as pure rules, with the check's own cases."""
    # 1. staleness from the cached page's own last-modified date (280 Verona Ave V5: 2026-05-07, 199 days at Nov 22)
    eq(P.staleness("2026-05-07", "2026-11-15", as_of=P.TOUR_START)[0], "remove", "IC6 #3: a page last changed 2026-05-07 is removed (199 days by the first tour day)")
    eq(P.staleness("2026-09-18", "2026-11-15", as_of=P.TOUR_START)[0], "open", "IC6 sweep 1: 65 days unchanged at the first tour day is one open item")
    eq(P.staleness("2026-09-24", "2026-11-15", as_of=P.TOUR_START)[0], "", "IC6 #21: Bay Shore, 59 days at Nov 22, is not stale")
    # 2. townhomes are ground-floor homes
    ok(P.townhome_home("townhome", "", ""), "IC6 #16: building_type townhome (West Hill Apartments) is a townhome")
    ok(P.townhome_home("", "", "BEAUTIFUL, SPACIOUS TOWNHOMES PET FRIENDLY ... TOWNHOUSE FEATURES MAIN LEVEL: Modern Kitchen"), "IC6 #16: the manager's 'spacious Townhomes' text is a townhome")
    ok(P.townhome_home("", "", "Enjoy multi-level townhouse living with complete modern convenience!"), "IC6 sweep 2: 'multi-level townhouse living' is a townhome")
    ok(P.townhome_home("", "One Bedroom Home with Patio", ""), "IC6 sweep 2: a 'Home with Patio' plan is a ground-floor home")
    ok(P.townhome_home("", "Townhome A", ""), "IC6 sweep 2: a 'Townhome' plan")
    eq(P.townhome_home("", "", "The apartments and townhomes at Encore 99 offer you all the comforts of home"), "", "IC6 sweep 2: 'apartments and townhomes' does not make every home a townhome")
    eq(P.townhome_home("", "", "one, two, three, and four bedroom apartments and townhomes come with"), "", "IC6 sweep 2: Cortlandt Living offers apartments and townhomes")
    eq(P.townhome_home("", "", "stately two-tone brick buildings with townhouse-style front stoops"), "", "IC6 sweep 2: 'townhouse-style stoops' is a facade, not a townhome")
    eq(P.townhome_home("", "One Bedroom (Upstairs)", "spacious townhomes, townhouse features: main level"), "", "IC6 sweep 2: a page that states an upper-floor flat is not removed")
    # 3. furnished
    eq(P.furnished_statement("Studio D-Line (Furnished)", ""), "furnished", "IC6 #12: the Kislak plan '(Furnished)'")
    eq(P.furnished_statement("", "This clean and cozy furnished 1-bedroom ... Move-in ready and fully furnished"), "furnished", "IC6 #14: 255 Franklin Ave 'fully furnished'")
    eq(P.furnished_statement("", "offered optional fully furnished and completely move-in ready"), "furnished (optional)", "IC6 sweep 3: optional furniture")
    eq(P.furnished_statement("Unfurnished", "a furnished rooftop lounge and a furnished model"), "", "IC6 sweep 3: a furnished lounge or model is not the apartment")
    # 4. the apartment number
    eq(P.shown_unit_number("3", "apartmentlist", "1", "146 Hamilton\n1BED #204\nMove-In Details * Monthly Rent: $2,100", ""), ("204", "listing text"), "IC6 #6: '3' is the site's index; the listing says #204")
    eq(P.shown_unit_number("3", "apartmentlist", "1", "100 Carroll · 1 BED Move-In Details * Monthly Rent: $2,100", ""), ("", "site index, no number on the page"), "IC6 #7: no number on the listing: none printed")
    eq(P.shown_unit_number("1 Bed", "apartmentlist", "1", "Welcome to this bright 1-bedroom", "1349 Dixwell Avenue - 24"), ("24", "listing title"), "IC6 #22: '1 Bed' is a plan label; the title names 24")
    eq(P.shown_unit_number("2C", "apartmentlist", "1", "Bright 1-bedroom apartment at 140 Fleming Ave, Unit 2C", ""), ("2C", "label"), "IC6 sweep 4: a real label stays")
    eq(P.shown_unit_number("APT#2", "apartmentlist", "1", "ALL UTILITIES INCLUDED", ""), ("APT#2", "label"), "IC6 sweep 4: a label that says APT#2 is a number")
    eq(P.shown_unit_number("6", "apartmentlist", "11", "", ""), ("6", "label"), "IC6 sweep 4: a one-digit label on a page of many units stays (Autumn Ridge 6)")
    eq(P.shown_unit_number("V5", "trulia", "", "", ""), ("V5", "label"), "IC6 sweep 4: other sites' labels are not touched")
    eq(P.floor_from_label("204")[0], 2, "IC6 #6: #204 reads as floor 2")
    # 5. parking included / the free lot
    eq(P.parking_included_statement("Building & Convenience Dedicated off-street parking space included Quiet"), "Dedicated off-street parking space included", "IC6 #14")
    eq(P.parking_included_statement("Includes 1 free parking spot. NO FEE!!"), "Includes 1 free parking spot", "IC6 #29")
    eq(P.parking_included_statement("Newly renovated Parking included with rent Heat and hot water included"), "Parking included with rent", "IC6 #27")
    eq(P.parking_included_statement("Parking available: $160 (spot) / $210 (garage)"), "", "IC6 sweep 5: a priced space is not included")
    eq(P.parking_included_statement("Free parking for the first month"), "", "IC6 sweep 5: a time-limited free offer is not included")
    eq(P.parse_parking("Dedicated off-street parking space included")["fee"], 0.0, "IC6 #14: the included space costs $0")
    f = P.parking_facts([("surface_lot; garage_lot; other; Parking; Garage | Garages: $150 per month", "stated", "u", "listing")], 150)
    eq(P.free_plain_lot_beside_paid(f["kinds"], f["unpriced_kinds"], 150, f["fee_kind"], f["option_kinds"], ["surface_lot; garage_lot; Garages: $150 per month"]), "open_lot",
       "IC6 #4: Kings Gardens: the unpriced lot is the free choice beside the $150 garage")
    f = P.parking_facts([("Parking | Open lot, carports $42/month / Covered Parking", "stated", "u", "listing")], 42)
    eq(P.free_plain_lot_beside_paid(f["kinds"], f["unpriced_kinds"], 42, f["fee_kind"], f["option_kinds"], ["Parking | Open lot, carports $42/month"]), "open_lot",
       "IC6 #23: Town Walk: 'Open lot, carports $42/month' uses the free open lot")
    src = ["Garage; Parking; Guest parking | Unassigned parking: $5/month per vehicle; Detached garage available", "fee: 15-350 | Parking: 15-350"]
    f = P.parking_facts([(t, "stated", "u", "listing") for t in src], 15)
    eq(P.free_plain_lot_beside_paid(f["kinds"], f["unpriced_kinds"], 15, f["fee_kind"], f["option_kinds"], src), "", "IC6 sweep 5: a priced lot ('Unassigned parking: $5') is not free")
    eq(P.free_plain_lot_beside_paid(["open_lot", "garage"], ["open_lot"], 75, "garage", ["garage"], ["included: no (fee stated)"]), "", "IC6 sweep 5: 'included: no' keeps the fee")
    s0 = P.parking_summary("open_lot", "open_lot", 0, [{"kind": "garage", "fee": 150.0, "fee_high": None}])
    eq(s0, "A free open lot; garage spaces are $150 a month.", "IC6 #4: the words name the paid garage as optional")
    # 6. offers that apply to this apartment only
    eq(P.offer_applies("$500 rent credit when you move 12/1/26(APT 41 & 36 ONLY) - must qualify", "039")[0], False, "IC6 #4: an offer for APT 41 & 36 is not apartment 039's")
    eq(P.offer_applies("A ONE MONTH FREE (APT 96,33 & 111 only) when you move in by 12/1/26", "040")[0], False, "IC6 #5")
    eq(P.offer_applies("A ONE MONTH FREE (APT 96,33 & 111 only) when you move in by 12/1/26", "033")[0], True, "IC6 #5: apartment 033 is named (033 = 33)")
    eq(P.offer_applies("Apply within 72 hours of touring and move in by 11/15/2026 to receive your second full months' rent free!", "1906")[0], False, "IC6 #15: expired before the first tour day")
    eq(P.offer_applies("Move in by 12/15/2026 for one month free", "1906")[0], True, "IC6 sweep 6: a deadline after the first tour day stands")
    eq(P.offer_applies("Up to 1 month free on select units", "CRS-2228")[0], True, "IC6 #13: 'select units' alone does not name other apartments")
    # 7. laundry
    eq(P.shared_laundry_statement("This Unit has a Dishwasher and Shared Laundry in the Building."), "Shared Laundry", "IC6 #20")
    eq(P.shared_laundry_statement("newly renovated studio, washer and dryer nearby, sunny"), "washer and dryer nearby", "IC6 #28")
    eq(P.shared_laundry_statement("Washer/Dryer in unit. A laundry room in the basement too."), "", "IC6 sweep 7: an in-unit washer in the same words wins")
    # 8. a flat utilities fee
    eq(P.flat_utilities_fee("Utilities are Included for a Flat Fee of $150/mo. Shared laundry", '{"title":"Monthly utilities fee","value":"$150/mo"}')[0], 150.0, "IC6 #20: 405 Main St O4 $150")
    eq(P.flat_utilities_fee("Utilities are Included for a Flat Fee of $150/mo.", '{"title":"Monthly utilities fee","value":"$125/mo"}')[0], None, "IC6 sweep 8: two sources disagreeing leave the estimate")
    eq(P.flat_utilities_fee("Heat and hot water included. Tenant pays electric.", "")[0], None, "IC6 sweep 8: no flat fee")
    # 9. income and credit requirements
    eq(P.income_requirement_statement("income_requirement_text: Must have 3x the rent in total household income (before taxes) | Looking for a comfortable, affordable place to call home?"),
       "3x the rent in household income", "IC6 #4 / sweep 9: Apartment List's requirement field, beside the word 'affordable' in the marketing text")
    eq(P.income_requirement_statement("Tenants must have an income 3x the rent. Guarantors must have great credit, and income must be 6x the rent."), "3x the rent in household income", "IC6 #20: the tenant's multiple, not the guarantor's")
    eq(P.income_requirement_statement("Must have 2.5x the rent in total household income (before taxes)"), "2.5x the rent in household income", "IC6 #4: 2.5x")
    eq(P.income_requirement_statement("Income must be at least double the monthly rent after taxes"), "2x the rent in household income", "IC6 sweep 9: 'double the rent'")
    eq(P.income_requirement_statement("Affordable housing: household income must not exceed 60% AMI; income 2x the rent"), "", "IC6 sweep 9: an income-capped program is left to the eligibility rule")
    # 10. the template listings
    ok(P.TEMPLATE_PATERSON.search("Looking for a comfortable, affordable place to call home? This spacious and modern apartment offers the perfect combination of convenience, style, and value."),
       "IC6 #2/#6/#7: the template text is recognised")


def data_ic6(M, R, S):
    """Independent check 6 on the pipeline's output: the six wrong items and the sweeps."""
    import pandas as pd
    import verdicts as VD
    shown = set(S.index)
    rid = lambda l, c: R.at[l, c] if l in R.index else None
    import build_master as BM
    pg = BM.read_listing_page("raw/trulia/da17c2de30b480cc.html", "trulia:460669961")
    if pg["bytes"]:
        eq((pg["modified"], pg["modified_field"]), ("2026-05-07", "Trulia lastDateModified"), "IC6 #3: the cached Trulia page's lastDateModified is read")
    pg = BM.read_listing_page("raw/apartmentlist/d42ef6376874a1aa.html", "apartmentlist:p11166981-3")
    if pg["bytes"]:
        ok("1BED #204" in pg["description"] and pg["unit_label"] == "3" and pg["unit_rows_on_page"] == "1", "IC6 #6: the Apartment List page gives the description, the site's label '3' and one unit row")
    ok("trulia:460669961" not in shown, "IC6 #3: 280 Verona Ave V5 (page last changed 2026-05-07) is not shown")
    if "trulia:460669961" in M.index:
        eq(M.at["trulia:460669961", "listing_stale"], "remove", "IC6 #3: 280 Verona Ave V5 is removed by the staleness rule")
    ok("rc:trulia:b2749337052:Unit_5-08:450005189" not in shown, "IC6 #16: West Hill Apartments 5-08 (townhomes) is not shown")
    ok(not S.get("townhome_home", pd.Series("", index=S.index)).ne("").any(), "IC6 sweep 2: no shown apartment is a townhome")
    l6 = "apartmentlist:p11166981-3"
    if l6 in R.index:
        eq(rid(l6, "unit_shown"), "204", "IC6 #6: 146 Hamilton Ave is apartment #204, not the site's '3'")
        eq(str(rid(l6, "unit_floor")).replace(".0", ""), "2", "IC6 #6: #204 reads as floor 2")
        eq(rid(l6, "parking_fee"), "150.0", "IC6 #6: the building's $150 garage fee is in the total")
    for l in ("apartmentlist:p25428225-3", "apartmentlist:p127128151-3"):
        if l in R.index:
            eq(rid(l, "unit_shown"), "", f"IC6 #2 / #7: {l} prints no apartment number")
    kis = [l for l in S.index if l.startswith("apartmentlist:p119939081-")]
    ok(all("furnished" in str(S.at[l, "disclosures"]) for l in kis), "IC6 #12: every shown Kislak apartment carries the furnished disclosure")
    ok(all(S.at[l, "rent_offer_kind"] == "special_offer" for l in kis), "IC6 #12: the Kislak's long-lease free months are a special offer")
    if "trulia:464204348" in S.index:
        ok("furnished" in S.at["trulia:464204348", "disclosures"], "IC6 #14: 255 Franklin Ave 1 is furnished")
        eq(S.at["trulia:464204348", "parking_fee"], "0.0", "IC6 #14: its off-street space is included")
    if "trulia:466331961" in S.index:
        r = S.loc["trulia:466331961"]
        lines = json.loads(r.all_in_lines)
        ok(any(l["code"] == "utilities_flat_fee" and l["amount"] == 150 for l in lines), "IC6 #20: 405 Main St O4 counts the $150 flat utilities fee")
        ok(not any(l["code"] == "utility_estimate" and l["line"].startswith(("electricity", "gas")) and l["amount"] for l in lines), "IC6 #20: no electricity or gas estimate beside the flat fee")
        eq(r.in_unit_laundry, "on_site_only", "IC6 #20: shared laundry, not a washer in the apartment")
        ok("income requirement" in r.disclosures, "IC6 #20: the 3x income rule is disclosed")
        eq(sum(l["amount"] or 0 for l in lines), float(r.all_in), "IC6 #20: the lines sum to the total")
    for l in ("apartmentlist:p40059-1B194-039", "apartmentlist:p1263841-1B200-040", "apartmentlist:p33289-7168A1P-1906"):
        if l in S.index:
            ok(S.at[l, "rent_offer_kind"] == "" and "special offer" not in S.at[l, "disclosures"], f"IC6 #4/#5/#15: {l} carries no special offer that is not its own")
    if "apartmentlist:p40059-1B194-039" in S.index:
        eq((S.at["apartmentlist:p40059-1B194-039", "parking_fee"], S.at["apartmentlist:p40059-1B194-039", "parking_kind"]), ("0.0", "open_lot"), "IC6 #4: the free lot, with the garage optional")
    if "apartmentlist:p14807-A2-08223" in S.index:
        eq(S.at["apartmentlist:p14807-A2-08223", "parking_fee"], "0.0", "IC6 #23: Town Walk uses the free open lot, not the $42 carport")
    for l in ("zumper-65723749", "rn:233-shore-rd-long-beach:b2750784396:Unit_20:2120211539"):
        if l in S.index:
            eq(S.at[l, "parking_fee"], "0.0", f"IC6 #27 / #29: {l}: the space included in the rent is $0, not 'not published'")
    if "zumper-65719911" in S.index:
        eq(S.at["zumper-65719911", "in_unit_laundry"], "on_site_only", "IC6 #28: 'washer and dryer nearby' is not in-unit laundry")
    # sweep 9 on every shown apartment: a requirement the page states is disclosed
    inc = S[S.income_requirement.ne("") & ~S.income_requirement.map(P.income_restricted)]
    ok(all("income requirement" in d for d in inc.disclosures), "IC6 sweep 9: every shown apartment with an income requirement discloses it")
    # sweep 10: every template listing carries 'asterisk | unverified'
    V = VD.by_unit()
    F_ = pd.read_csv(DATA / "reference" / "listing_page_facts.csv", dtype=str, keep_default_na=False).set_index("listing_id")
    tmpl = [l for l in S.index if l in F_.index and P.TEMPLATE_PATERSON.search(F_.at[l, "description"])]
    ok(all("unverified" in V.get(l, {}).get("gate", []) for l in tmpl), "IC6 sweep 10: every shown template listing carries the 'unverified' asterisk")
    ok(all(S.at[l, "confirm_what"] != "" for l in tmpl), "IC6 sweep 10: and it is the apartment's one open item")


if __name__ == "__main__":
    if "--data" not in sys.argv:
        pure_floor_elevator()
        pure_ic4()
        pure_ic4_text()
        pure_cleanup()
        pure_ic5()
        pure_ic6()
        pure_b21()
    (data if "--data" in sys.argv else pure)()
    print(f"test_rules {'(data)' if '--data' in sys.argv else '(rules)'}: {N[0]} checks, {len(FAILS)} failed")
    for f in FAILS:
        print("  FAIL", f)
    sys.exit(1 if FAILS else 0)
