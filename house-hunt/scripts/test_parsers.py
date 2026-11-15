"""Plain-assert tests for scripts/parsers.py: every example string quoted in docs/INDEPENDENT_CHECK.md.

Run: python3 scripts/test_parsers.py   (exits non-zero on the first failure; a step of scripts/run_all.py)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import parsers as P  # noqa: E402

N = 0


def eq(got, want, what):
    global N
    N += 1
    assert got == want, f"{what}: got {got!r}, want {want!r}"


def floor(label, bf=None):
    return P.floor_from_label(label, bf)[0]


# ---- W1 / W11 / A10 / A11: floor labels
eq(P.floor_from_label("4F"), (4, "simple"), "4F")
eq(P.floor_from_label("12B"), (12, "simple"), "12B")
eq(P.floor_from_label("305"), (3, "simple"), "305")
eq(P.floor_from_label("7B"), (7, "simple"), "7B (The Brompton)")
eq(P.floor_from_label("Unit 2F"), (2, "simple"), "Unit 2F")
eq(P.floor_from_label("4CD"), (4, "simple"), "4CD")
for lab, wrong in [("H2-316", 23), ("158-2L", 15), ("5-204", 52), ("3-117", 31), ("1-219", 12), ("9114", 91), ("2307", 23),
                   ("2182", 21), ("1200", 12), ("1147", 11), ("1109", 11), ("1177", 11), ("1119", 11), ("2154", 21), ("1103", 11),
                   ("1142", 11), ("2106", 21), ("005-5106", 51), ("001-215", 0)]:
    eq(floor(lab), None, f"{lab} must not be read as floor {wrong} without the building's floor count")
    eq(P.floor_from_label(lab)[1], "complex", f"{lab} is a complex label")
eq(floor("7012", 13), 7, "7012 in a 13-floor building")
eq(floor("3203", 3), None, "3203 in a 3-floor building is ambiguous (3 or 2)")
eq(floor("2204", 14), 2, "2204 in a 14-floor building (22 impossible; floor 2 either way)")
eq(floor("1203", 20), None, "1203 in a 20-floor building: 12, 1 or 2")
eq(floor("H2-316", 5), 3, "H2-316 with 5 floors")
eq(floor("5-204", 4), 2, "5-204 with 4 floors")
eq(floor("5-204", 6), None, "5-204 with 6 floors: 5 or 2")
eq(floor("2307", 4), None, "2307 in a low-rise: 2 or 3")
eq(floor("7B", 6), None, "a reading above the building's floors is rejected, not clamped")
eq(floor("26B", 30), 26, "26B")
for lab in ["B2", "C4", "B10", "L3", "G02", "PH2", "48", "D3", "H41"]:
    eq(floor(lab), None, f"{lab}: a letter plus digits is not a ground-floor (or any) reading")
    eq(floor(lab, 6), None, f"{lab} with floors known")
for lab in ["G", "GR", "LOBBY", "BSMT"]:
    eq(P.floor_from_label(lab), (0, "ground_word"), lab)
eq(floor(""), None, "blank")

# ---- W17: evidence floor values
eq(P.parse_floor_confirm("3 (from unit number 317)"), ([("317", 3)], True), "3 (from unit number 317)")
eq(P.parse_floor_confirm("unit 231: 2nd Floor"), ([("231", 2)], False), "unit 231: 2nd Floor")
eq(P.parse_floor_confirm("1 (ground floor)"), ([("*", 1)], False), "1 (ground floor)")
eq(P.parse_floor_confirm("unit 1177: 1"), ([("1177", 1)], False), "unit 1177: 1")
eq(P.parse_floor_confirm("unit 5106: floor 1 (ground floor)"), ([("5106", 1)], False), "unit 5106")
eq(P.parse_floor_confirm("001-436: 4; 001-324: 3"), ([("001-436", 4), ("001-324", 3)], False), "two units")
eq(P.parse_floor_confirm("2206: floor 2; 2321: floor 3"), ([("2206", 2), ("2321", 3)], False), "floor N form")
eq(P.parse_floor_confirm("003-3326: floor 3; 002-2130: floor 1 (ground floor)"), ([("003-3326", 3), ("002-2130", 1)], False), "Avalon Yonkers")
eq(P.parse_floor_confirm("units 1-219 and 1-234: floor 2 (inferred)"), ([("1-219", 2), ("1-234", 2)], True), "units a and b")
eq(P.parse_floor_confirm("unit G02: Ground Floor"), ([("G02", 1)], False), "ground floor word")
eq(P.parse_floor_confirm("5 for 5G, 6 for 6A (inferred from unit numbers only)"), ([("5G", 5), ("6A", 6)], True), "N for label")
eq(P.parse_floor_confirm("3 (inferred from unit number 2307)"), ([("2307", 3)], True), "A10 Parkside 2307")
eq(P.parse_floor_confirm("unit 1200: unknown"), ([], False), "unit 1200: unknown")
eq(P.parse_floor_confirm("10"), ([("*", 10)], False), "bare number")
eq(P.parse_floor_confirm("7 (from unit number 7K)"), ([("7K", 7)], True), "confirmed-but-derived")
eq(P.units_match("5106", "005-5106"), True, "5106 = 005-5106 (Avalon Piscataway)")
eq(P.units_match("001-215", "215"), True, "001-215 = 215")
eq(P.units_match("2F", "Unit 2f"), True, "2F")
eq(P.units_match("2F", "2A"), False, "2F != 2A")
eq(P.units_match("316", "H2-316"), True, "316 = H2-316")
eq(P.units_match("1-219", "1-234"), False, "1-219 != 1-234")

# ---- A1 / A2 / A14 / A15 / A16 / W4: parking sentences
pf = lambda s: P.parse_parking(s)["fee"]
eq(pf("Garage Parking: $175 parking fee"), 175.0, "A1 One City Place")
eq(pf("Assigned Parking; 1 spaces available; $175 parking fee; Special Features: 9 FT Ceilings, Garage, Garage Lot, Pantry"), 175.0, "A1 as stored")
eq(pf("Parking Policy: Up to 3 spots: 1st $100, 2nd $75, 3rd $200"), 100.0, "A2 The Jefferson: the first spot")
eq(pf("Covered parking fee ($150)"), 150.0, "A14 Regency on Hudson")
eq(pf("Covered parking fee $135; Garage parking fee $100; Surface lot parking fee $85"), 100.0, "A15 The Highlands: cheapest covered or garage")
eq(pf("covered $135, garage $100, surface $85"), 100.0, "A15 in one clause")
a16 = P.parse_parking("1 free surface spot per 1-bedroom. 2 free surface spots per 2-bedroom. Additional spots available at $50/mo./car (subject to availability). Attached private garages available.")
eq((a16["fee"], a16["included"]), (0.0, True), "A16 The Edge at Raritan Heights: the first spot is free")
eq(pf("Parking: Open lot: included in lease; Underground parking garage: $100/month"), 0.0, "an included open lot")
eq(pf("Indoor $275/Month Outdoor $225/Month"), 275.0, "indoor against outdoor")
eq(pf("$250 covered, $225 surface"), 250.0, "Harrison Yards: covered, not surface")
eq(pf("$100; $150; $175"), 100.0, "Halstead: cheapest of unlabelled prices")
eq(pf("$150 (plus tax) for covered and $120 (plus tax) for uncovered"), 150.0, "label after the price")
eq(pf("Parking Garage: $125/month (1 Space) $75/month (2nd space)"), 125.0, "second-space price ignored")
eq(pf("Parking Type: Garage Lot Parking Comment: First space is $75 Monthly. Additional parking available at $150 monthly per space."), 75.0, "first space")
eq(pf("interior garage $175 per month; exterior $100 per month; no amenity fee"), 175.0, "garage against exterior")
eq(pf("garage $140/month; covered $175/month (Zumper data)"), 140.0, "two covered options")
eq(pf("assigned garage parking, $116-$188/month"), 116.0, "range: low end")
eq(pf("off-site covered garage two blocks away, not assigned; first year free"), None, "time-limited free is not $0")
eq(pf("one spot per home; additional/optional parking fee $55-$135/month"), None, "only an additional-spot price")
eq(pf("garage (Trulia feature says valet); fee not stated"), None, "fee not stated")
eq(pf("Parking - Garage: 185; Parking - Reserved: 63"), 185.0, "amounts without $ (community page data)")
eq(pf("Parking: 75 (monthly; required=False; included=False) ; Parking - Garage: 150 (monthly; required=False; included=False)"), 150.0, "included=False is not 'included'")
eq(pf("115.07-285.39"), 115.07, "bare range")
eq(pf("$50/month (optional)"), 50.0, "single price")
eq(pf("Parking $195 monthly"), 195.0, "single price, no label")
eq(pf("2 spots allocated to the unit; attached garage"), None, "no price")
eq(P.parse_parking(P.parking_from_fee_items([{"title": "Covered parking fee ($135)", "value": "Contact for details"}, {"title": "Garage parking fee ($100)", "value": "Contact for details"},
                                             {"title": "Surface lot parking fee ($85)", "value": "Contact for details"}]))["fee"], 100.0, "A15 from the Trulia fee lines")
eq(P.parse_parking(P.parking_from_fee_items([{"title": "Parking fee", "value": "Included"}]))["fee"], 0.0, "Trulia 'Parking fee: Included'")

# ---- W9 / A4 / A17: fee sentences
fee = lambda s, u="": P.monthly_fees_from_text(s, u)[0]
eq(fee("Technology Connect: 66"), 66.0, "A17 Avalon Teaneck")
eq(fee("Community Lifestyle Fee: 75"), 75.0, "W9")
eq(fee("Trash Services - Hauling: 15"), 15.0, "W9")
eq(fee("no amenity fee"), 0.0, "A4: 'no amenity fee' is a known $0")
eq("fee exists" in P.monthly_fees_from_text("no amenity fee")[1], False, "A4: not 'fee exists'")
eq(fee("interior garage $175 per month; exterior $100 per month; no amenity fee"), 0.0, "A4 as stored: parking is not a building fee")
eq(fee("$575 amenity fee, $695 admin fee"), None, "over $400 is not counted")
eq("not counted" in P.monthly_fees_from_text("$575 amenity fee, $695 admin fee")[1], True, "... and is not skipped silently")
eq(fee("$182: Common Area/Amenities $90 + Technology Connect $92"), 182.0, "stated total with its breakdown")
eq(fee("Renter's insurance required; sewer fee: $80; trash: $30; $100 Amenity fee"), 210.0, "three monthly items")
eq(fee("Community Lifestyle Fee $40; utility billing admin fee $6.06; renters liability insurance, electric and water/sewer required, amounts not stated"), 46.06, "two priced items")
eq(fee("Trash Services - Hauling: 20; Community Amenity Fee: 75; Utility - Billing Administrative Fee: 4.65 [site total of priced required fees: 99.65]"), 99.65, "site total")
eq(fee("one-time: $300 building application fee + $150 background check"), None, "one-time only")
eq(fee("deposit $2,200"), None, "deposit")
eq(fee("$50/mo amenity fee"), 50.0, "simple")
eq(fee("97.55"), 97.55, "bare number")
eq(fee("$95 (unit 622, added to base rent on the page)", "622"), 95.0, "unit-specific fee, same unit")
eq(fee("$95 (unit 622, added to base rent on the page)", "401"), None, "unit-specific fee, other unit")
eq(P.monthly_fees_from_text("amenity fee exists, amount not published")[1].startswith("fee exists"), True, "fee exists")
eq(P.fees_from_json('{"Technology Connect": 85}')["fee"], 85.0, "Avalon fee JSON")
eq(P.fees_from_json('{"additional_fees": "Amenity fee: $75/month.", "move_in_fees": "Move-in fees are $120.", "deposit_fee": "Deposit: $1500", "total_price_with_required_fees": 2560, "required_fees": 109.05}')["fee"], 109.05, "Bozzuto fee JSON")
j = P.fees_from_json('{"monthlyRequiredFees":[{"title":"Monthly base rent","value":"2500-3450"}],"monthlyOptionalFees":[{"title":"Covered parking fee ($135)","value":"Contact for details"},{"title":"Garage parking fee ($100)","value":"Contact for details"},{"title":"Surface lot parking fee ($85)","value":"Contact for details"}]}')
eq((j["fee"], P.parse_parking(j["parking_text"])["fee"]), (None, 100.0), "A15 fee JSON: base rent is not a fee; parking lines found")
j = P.fees_from_json('{"oneTimeRequiredFees":[{"title":"Security deposit","value":"2700-4300"}],"monthlyOptionalFees":[{"title":"Cat rent ($50)","value":"Contact for details"},{"title":"Dog rent ($60)","value":"Contact for details"}]}')
eq((j["fee"], P.parse_pet_rent(j["pet_text"])[0]), (None, 60.0), "A1 fee JSON: dog rent, not cat rent")
eq(P.money("1500"), 1500.0, "W15: unformatted number")
eq(P.money("$1,500"), 1500.0, "money with comma")

# ---- W15: pet rent
pr = lambda s, d=True: P.parse_pet_rent(s, d)[0]
eq(pr("one-time $500 per pet; $50 per pet monthly"), 50.0, "W15 The George")
eq(pr("one-time $500 per pet; $50 per pet monthly; $30 per pet yearly PetScreening fee"), 50.0, "W15 full sentence")
eq(pr("$350 one-time; pet rent $40 or $50"), 40.0, "W15 Parc at Roxbury")
eq(pr("$60 a month per dog; $500 one-time"), 60.0, "monthly first")
eq(pr("pet rent: 50.00; one-time fee: 500.00"), 50.0, "no $ signs")
eq(pr("$35 monthly; $300 non-refundable"), 35.0, "non-refundable")
eq(pr("$50/month per pet; $350 fee; max 2; 50 lb each"), 50.0, "fee and weight ignored")
eq(pr("$50/month for 1 pet; $75 for 2"), 50.0, "one pet")
eq(pr("65.00"), 65.0, "bare number")
eq(pr("general rent: 60.0; general fee: 600.0; general limit: 2", False), 60.0, "pet_fees field")
eq(pr("$600 one-time"), None, "one-time only")
eq(pr("$275 per pet", False), None, "bare amount in a pet-fee field is not rent")
eq(pr("Dogs: Allowed (Size allowed: Small, large; Monthly dog rent: $60/mo; Dog deposit: $600) | Cats: Allowed (Monthly cat rent: $50/mo; Cat deposit: $500)", False), 60.0, "Trulia pet card")
eq(pr("One pet-$500 fee/$50 monthly or Two Pets-$750 fee/$75 monthly, with a max combined weight of 100lbs.", False), 50.0, "The Jefferson pet line")

# ---- W16 / W2: dog weight and size
eq(P.parse_dog_weight("no upper limit stated; dogs over 40 lb cost extra"), ("no_limit", None), "W16 743 Passaic Ave")
eq(P.parse_dog_weight("extra charge over 40 lb"), ("unknown", None), "a surcharge threshold is not a limit")
eq(P.parse_dog_weight("no limit"), ("no_limit", None), "no limit")
eq(P.parse_dog_weight("no weight limit stated (breed list only; the site's maximumPetWeight field is 0)"), ("no_limit", None), "no weight limit stated")
eq(P.parse_dog_weight("25lbs max"), ("limit", 25.0), "4545 46th St 5F")
eq(P.parse_dog_weight("under 40 lb"), ("limit", 40.0), "under 40 lb")
eq(P.parse_dog_weight("50"), ("limit", 50.0), "bare number")
eq(P.parse_dog_weight("no number; Trulia says small dogs only, large dogs not permitted"), ("size_only", None), "W2 127 Talmage Ave")
eq(P.parse_dog_weight("unconfirmed ('small dogs', no number)"), ("size_only", None), "small dogs, no number")
eq(P.parse_dog_weight("a weight restriction exists; number not stated"), ("unknown", None), "limit exists, no number")
eq(P.parse_dog_weight("no number given; page says large dogs allowed"), ("unknown", None), "large dogs allowed")
eq(P.dog_size_only("Dogs: Allowed (Size allowed: Small) | Cats: Allowed (Size allowed: n/a) | Summary: Dogs & Cats | Cats, small dogs allowed"), True, "W2 pet card: Small")
eq(P.dog_size_only("Dogs: Allowed, Size allowed: Small"), True, "W2 as quoted")
eq(P.dog_size_only("Dogs: Allowed (Size allowed: Small, large) | Cats: Allowed"), False, "Small, large")
eq(P.dog_size_only("Dogs: Allowed (Number allowed: 2; Size allowed: Small; Weight limit (lbs.): 25)"), False, "a number is given")
eq(P.dog_size_only("yes (small dogs)"), True, "W2 'yes (small dogs)'")
eq(P.dog_size_only("Dogs & Cats | tag: PET FRIENDLY"), False, "no size word")

# ---- W20: conflicting dog policy
eq(P.dog_conflict("Zumper's page for the address says no pets (its record shows only 6 units, so it may be stale); the building site and Apartment List say pet-friendly"), "yes", "19 E 19th St: own site wins")
eq(P.dog_conflict("no (Trulia)"), "conflicting", "100 Avenue G / 467 West Ave / 8 Norden Pl: an aggregator's no against the listing")
eq(P.dog_conflict("Apartment List says dogs allowed; Trulia's page for the same address says No Pets"), "conflicting", "aggregator vs aggregator")
eq(P.dog_conflict("no"), "no", "plain no")
eq(P.dog_conflict("NO: service or emotional-support dogs only"), "no", "service dogs only")
eq(P.dog_conflict("no, except service or emotional-support dogs: the listing's description contradicts its own 'dogs allowed' field"), "no", "listing's own description says no")
eq(P.dog_conflict("no (service or emotional-support dogs only)"), "no", "service dogs only, in brackets")

# ---- W5 / A3: utilities
inc = lambda s: sorted(P.parse_utilities(s)["included"])
eq(inc("gas/electric and water/sewer paid by resident"), [], "A3 The Jefferson")
eq(inc("resident pays electric, gas, trash, water, sewer"), [], "W5")
eq(inc("tenant pays electricity and cooking gas"), [], "W5")
eq(inc("all utilities except cooking gas and electricity"), ["heat", "hot_water", "water"], "W5 44-10 Ketcham St")
eq(inc("Heat and hot water"), ["heat", "hot_water"], "W5: heat is not cooking gas")
eq(inc("heat, water, cooking gas"), ["gas", "heat", "water"], "bare list")
eq(inc("none [Electric=Resident; Gas=Resident; Trash=Resident; Water=Resident; Sewer=Resident]"), [], "Electric=Resident")
eq(inc("Trash [Electric=Resident; Gas=N/A; Trash=Community; Water=Resident; Sewer=Resident]"), ["trash"], "Trash=Community")
eq(inc("all utilities"), ["electric", "gas", "heat", "hot_water", "water"], "all utilities: not internet")
eq(inc("Cable, Electric, Gas, Hot Water, Internet, Sewer, Trash, Water"), ["cable", "electric", "gas", "hot_water", "internet", "sewer", "trash", "water"], "full list")
eq(inc("trash included; resident pays electric, water, sewer; internet is in the required technology fee"), ["trash"], "mixed sentence")
eq(inc("yes per own site; which utilities not specified"), [], "unspecified")
eq(inc("none listed as included"), [], "none listed")
eq(sorted(P.parse_utilities("resident pays electric, trash, water, sewer; no gas")["none"]), ["gas"], "no gas")
eq(sorted(P.parse_utilities("tenant pays electricity and cooking gas")["tenant"]), ["electric", "gas"], "tenant list")

# ---- W14: pool and doorman
for s in ["Pool table", "none listed", "none listed (own site amenities, Trulia)", "none listed (pool table only)", "see quote", "no", ""]:
    eq(P.pool_state(s), "", f"pool: {s!r}")
for s in ["Pool", "Pool, Pool table", "yes (indoor or outdoor not stated)", "outdoor rooftop pool (26th floor)", "yes", "Resort-Style Pool (outdoor per roof/sundeck context; indoor/outdoor not stated)"]:
    eq(P.pool_state(s), "pool", f"pool: {s!r}")
eq(P.pool_state("indoor, with hot tub"), "indoor", "indoor pool")
eq(P.pool_state("outdoor (Olympic-size heated saltwater) and indoor saltwater"), "indoor", "outdoor and indoor")
for s in ["live-in super; no doorman stated", "none listed; Trulia lists 'Night Patrol'", "virtual doorman", "live-in superintendent; no doorman listed", "no doorman"]:
    eq(P.doorman_state(s), "", f"doorman: {s!r}")
eq(P.virtual_doorman("virtual doorman"), True, "a virtual doorman counts as controlled access")
eq(P.doorman_state("doorman / concierge / virtual doorman"), "doorman", "a real doorman beside a virtual one")
eq(P.doorman_state("24hr concierge, Doorman"), "24h", "24h")
eq(P.doorman_state("attended lobby"), "doorman", "attended lobby")
eq(P.doorman_state("Door Person"), "doorman", "door person")
eq(P.amenity_yes("none listed"), False, "generic negative")
eq(P.amenity_yes("no_mention"), False, "generic blank")
eq(P.amenity_yes("fitness center"), True, "generic yes")

# ---- W10: income language
for s in ["40x rent and 700+ credit", "3x the rent in household income", "$130,000 a year", "household income of $104,000+ and 700+ credit", "income 3x rent"]:
    eq(P.income_restricted(s), False, f"ordinary screening: {s}")
for s in ["income-restricted, rent-stabilized unit: household income $90,000 to $154,000", "described as an affordable development; income rules likely apply (not stated on the page)",
          "housing lottery unit", "maximum household income $98,000"]:
    eq(P.income_restricted(s), True, f"income-restricted: {s}")

# ---- cosmetic: numeric comparison
eq(P.num_str("6.0") == P.num_str("6"), True, "6 vs 6.0 is not a conflict")
eq(P.num_str("50.00") == P.num_str("50"), True, "50 vs 50.00")

print(f"test_parsers: {N} assertions passed")
