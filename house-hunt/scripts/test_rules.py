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
                       (["1147", "2113", "2117", "4108", "5136", "5158"], "Cobalt Lofts"), (["001-215", "001-304", "003-463"], "Avalon Teaneck (a fourth floor)"),
                       (["305", "4F", "12B"], "plain labels"), (["34-204", "34-615", "36-206"], "Valley and Bloom (a sixth floor)"), (["1-101", "1-208"], "one building number only")]:
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
    ok(not S.confirm_what.str.contains("cost near the cap|lease term|condo|floor").any(), "disclosures never count as the open gate fact")
    npub = S[~S.unit_floor_basis.isin(["confirmed", "stated"])]
    ok(npub.disclosures.str.contains('"what": "floor not published"', regex=False).all() and npub.tour_confirm.str.contains("above the ground floor").all(),
       "a shown unit whose floor is not published carries the disclosure and the tour question")
    ok(not (pd.to_numeric(S.unit_floor, errors="coerce") < 2).any(), "no shown unit on floor 1 or the ground floor")
    ok((S.open_gate_facts.astype(float) <= 1).all(), "a shown unit has at most one open gate fact")
    sk_ = pd.read_csv(DATA / "excluded_sketchy.csv", dtype=str, keep_default_na=False, low_memory=False)
    ok(not sk_.sketchy_reason.str.contains("cost near the cap|lease term|floor(?! plan)").any() or not sk_.sketchy_reason.str.contains("unconfirmed: [^;]*floor").any(), "no unit is dropped as sketchy because of a disclosure")
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
    for r in V[V.verdict == "asterisk"].itertuples():
        if r.listing_id in S.index:
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
                     ("rc:trulia:b2751605456:Unit_K3-02:351211069", "D3: Residences at The Summit K3-02 (stale page, never seen live)")]:
        ok(lid not in S.index, f"IC3 {why} must not be shown")
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
    ok(set(DT.building_id) <= set(M.building_id) | set(), "step 3: every row of the doubt table names a building in the master")
    dm = M[M.building_id.isin(set(DT.building_id)) & (M.elevator == "yes") & (M.elevator_basis != "confirmed_by_phone")]
    ok((dm.elevator_doubt != "").all(), "step 3: every building of the doubt table has the elevator doubt set")
    ds = S[S.elevator_doubt != ""]
    ok((ds.confirm_what == "elevator").all() and (ds.confirm_asterisk == "yes").all(), "step 3: a shown unit under elevator doubt carries the elevator asterisk as its one open item")
    ok(ds[(ds.elevator_evidence_open == "")].to_confirm.str.contains("Confirm an elevator serves this apartment", regex=False).all(), "step 3: ... with the question 'confirm an elevator serves this apartment'")
    ok((pd.to_numeric(ds.open_gate_facts) == 1).all(), "step 3: a doubted unit is shown only when the elevator is its single open gate fact (a listing never re-read is not a second one)")
    # ---- step 4: pet rent estimated, all_in_likely, the new disclosure
    ok(not M.all_in_unknown_lines.str.contains("pet rent").any(), "step 4a: pet rent is never unknown-and-nothing")
    est = M[M.all_in_estimated_lines.str.contains("pet rent")]
    ok(len(est) > 0 and all(next(l for l in json.loads(a) if l["line"].startswith("pet rent"))["amount"] > 0 for a in est.all_in_lines), "step 4a: an unpublished pet rent is a positive estimate line")
    ok((num(M, "all_in_likely") >= num(M, "all_in")).all(), "step 4b: all_in_likely is never below all_in")
    kn = M[~M.all_in_unknown_lines.str.contains("parking fee|building fees")]
    ok((num(kn, "all_in_likely") == num(kn, "all_in")).all(), "step 4b: with parking and fees known, all_in_likely equals all_in")
    ok((num(S, "all_in") <= 3000).all(), "step 4: the hard cap stays on all_in")
    flag_ = (num(S, "all_in") <= 3000) & (num(S, "all_in_likely") > 3000)
    has_ = S.disclosures.str.contains('"what": "could pass $3,000"', regex=False)
    ok((flag_ == has_).all(), "step 4b: the 'could pass $3,000' disclosure sits on exactly the units it applies to")
    ok(S[has_].disclosures.str.contains("Could pass $3,000 once parking and fees are known", regex=False).all(), "step 4b: the disclosure names both figures in its sentence")
    ok(not S.disclosures.str.contains("cost near the cap", regex=False).any() and not S.disclosures.str.contains("counted as $0", regex=False).any(), "step 4b: the old 'cost near the cap' disclosure and 'counted as $0' are gone")
    ok(not R.confirm_why.str.contains("counted as $0", regex=False).any(), "pending fix: no confirm_why says 'counted as $0'")
    # the estimate's reference set (master buildings) against the ranked buildings, per state: reported, and must be close
    E_ = pd.read_csv(DATA / "reference" / "cost_estimates.csv")
    Rb = R.drop_duplicates("building_id")
    for st_, g_ in Rb.groupby("state"):
        known = pd.to_numeric(g_.pet_rent, errors="coerce").dropna()
        used = E_[(E_.line == "pet rent") & (E_.state == st_)]["median"]
        if len(known) >= 5 and len(used):
            ok(abs(float(known.median()) - float(used.iloc[0])) <= 10, f"step 4a: {st_} pet-rent estimate ${float(used.iloc[0]):g} is within $10 of the median among ranked buildings (${float(known.median()):g})")
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


def data_units_unique(S):
    pass


def pure_6():
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
    eq(list(rank.in_unit_laundry(s_(["yes", "washer, dryer", "laundry room (not in unit)", "In unit", ""]), s_(["on_site_only", "yes", "yes", "", ""]))), [False, True, False, True, False],
       "laundry: 'yes' with on_site_only is a shared laundry room, not a washer in the apartment")


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
    ok(((S_.confirm_asterisk == "yes") == (pd.to_numeric(S_.open_gate_facts) == 1)).all() and S_.confirm_what[S_.confirm_asterisk == "yes"].isin(["elevator", "dogs allowed", "availability", "listing", "eligibility"]).all(),
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
    st = R.elevator_rule_status
    ok(st.isin(["established", "open"]).all(), "elevator rule: no ranked unit has an 'unknown' or 'no' elevator")
    ok((R[R.shown == "True"].open_keys.str.split(";").map(lambda k: "elevator" in k) == (R[R.shown == "True"].elevator_rule_status == "open")).all(),
       "elevator rule: a shown unit carries the elevator asterisk exactly when the rule says 'open'")
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


if __name__ == "__main__":
    (data if "--data" in sys.argv else pure)()
    print(f"test_rules {'(data)' if '--data' in sys.argv else '(rules)'}: {N[0]} checks, {len(FAILS)} failed")
    for f in FAILS:
        print("  FAIL", f)
    sys.exit(1 if FAILS else 0)
