"""Evidence batch 3: gate confirmations, facts and the remaining evidence items, read from cached pages
(raw/evidence_b3) and typed in from them. Quotes are checked against the cached page text where a page is named."""
import csv, json, re, sys, datetime, html as H
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib, h_zumper as Z, h_trulia as T
from ev_b3_util import page, put, index
from h_mgmt_common import strip_tags

batch = list(csv.DictReader(open(lib.DATA / "reference" / "evidence_batches" / "batch_3.csv")))
BK = {b["addr_key"]: b for b in batch}
pluto = {r["addr_key"]: r for r in csv.DictReader(open(lib.DATA / "reference" / "nyc_building_facts.csv"))}
IDX = index()
NOW = lib.now_iso()
conf, facts, items = [], [], []
def C(k, fact, value, quote, url, status): conf.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=url, status=status))
def F(k, fact, value, quote, url): facts.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=url))
def I(k, cat, date, ex, site, url, about="building"):
    items.append(dict(addr_key=k, building_name=BK[k]["building_name"] or BK[k]["address"].split(",")[0], category=cat, item_date=date, excerpt=ex,
                      source_site=site, source_url=url, about=about, retrieved_at=IDX.get(url, {}).get("retrieved_at", NOW)))

AL = "https://www.apartmentlist.com/nj/"
AV = "https://www.avaloncommunities.com/new-jersey/"
TR = "https://www.trulia.com/building/"
PL = "https://data.cityofnewyork.us/Housing-Development/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks"
BREEDS = "Cats and dogs are welcome. Please check the dog breed and pet restrictions below."
NOWL = "no weight limit stated (breed list only; the site's maximumPetWeight field is 0)"

# ---------------- New Jersey managed buildings
k = "153 valley st|07079"; u = AL + "east-orange/third-valley"; tu = TR + "third-valley-153-valley-st-south-orange-nj-07079-1150870531"
C(k, "elevator", "yes", "community amenity: Elevator", u, "confirmed")
C(k, "floor", "unit 222: floor 2; unit 344: floor 3 (from unit numbers; the page also lists units 003 and 044, so numbering may start at a lower level)", "units 222, 344", u, "unconfirmed")
C(k, "dogs_allowed", "yes on Apartment List (Bozzuto feed)", "pet_policies: allowed true; allowed_pets dogs, cats; amenities: Dogs allowed, Dog grooming area", u, "contradicts")
C(k, "dogs_allowed", "no on Trulia's building page", "Dogs: Not allowed; Cats: Not allowed", tu, "contradicts")
C(k, "dog_weight_limit", "unconfirmed", "dogs restrictions: Yes (no figure given); the building's own site and bozzuto.com disallow Claude agents in robots.txt", u, "unconfirmed")
F(k, "year_built", "2016", "year_built 2016", u); F(k, "management_company", "Bozzuto", "pmc_display_name Bozzuto", u)
F(k, "parking_type", "parking garage; fee not published", "Parking garage", u); F(k, "pool", "yes (indoor or outdoor not stated)", "amenity: Pool", u)
F(k, "required_fees", "not readable: fee sheet is on communityfees.bozzuto.com (Bozzuto sites disallow Claude agents)", "fee_url https://communityfees.bozzuto.com/property/82DD91/export", u)
F(k, "pet_limit", "2 pets", "general limit: 2", u)

k = "1775 windsor rd|07666"; u = AL + "bergenfield/avalon-teaneck"; o = AV + "teaneck-apartments/avalon-teaneck"
C(k, "elevator", "yes (4 floors seen among listed units)", "amenity: Elevator (Apartment List). Own site: Parking garage with direct access to every floor of the building is available for an additional monthly fee.", u, "confirmed")
C(k, "floor", "unit 001-215: floor 2", "floorNumber 2 for unit AVB-NJ030-001-215", o, "confirmed")
C(k, "floor", "unit 002-129: floor 1 (ground floor: fails the no-ground-floor gate)", "floorNumber 1 for unit AVB-NJ030-002-129", o + "#unit-002-129", "confirmed")
C(k, "dogs_allowed", "yes", BREEDS, o, "confirmed")
C(k, "dog_weight_limit", NOWL, "Dogs: Allowed; Size allowed: Small, large (Trulia building page)", TR + "avalon-teaneck-1775-windsor-rd-teaneck-nj-07666-2747892426", "confirmed")
F(k, "year_built", "2019", "year_built 2019", u); F(k, "management_company", "AvalonBay Communities (owner-operator)", "pmc_display_name AvalonBay", u)
F(k, "parking_type", "garage, monthly fee (amount not on the community page)", "Parking garage with direct access to every floor of the building is available for an additional monthly fee.", o)
F(k, "price_with_required_fees", "unit 001-215: $2,516 rent, $2,582 total; unit 002-129: $2,680 rent, $2,746 total", "price 2516, totalPrice 2582; price 2680, totalPrice 2746", o)
F(k, "pool", "yes", "amenity: Pool", u)

for k, lu in (("2400 vauxhall rd|07083", AL + "newark/avalon-union"), ("5306 bristol dr|07083", AV + "union-apartments/avalon-union/apartment/NJ026-NJ026-005-5306")):
    o = AV + "union-apartments/avalon-union"; uu = AV + "union-apartments/avalon-union/apartment/NJ026-NJ026-005-5306"
    C(k, "elevator", "unconfirmed: Apartment List tags 'Elevator'; AvalonBay's own pages never mention one; listed units are on floors 1 to 3; a 2022 resident review describes leaving a second-story unit because a senior dog needed a first-floor home", "amenity: Elevator", AL + "newark/avalon-union", "unconfirmed")
    C(k, "floor", "3", "Floor 3", uu, "confirmed")
    C(k, "dogs_allowed", "yes", BREEDS, uu, "confirmed")
    C(k, "dog_weight_limit", NOWL, "Dogs: Allowed; Size allowed: Small, large (Trulia building page)", TR + "avalon-union-2400-vauxhall-rd-union-nj-07083-1150783294", "confirmed")
    F(k, "pet_rent", "$60 a month per dog; $500 one-time", "Pet Dog Fee Monthly 60; Pet Dog Fee MoveIn 500", uu)
    F(k, "required_monthly_fees", "Technology Connect $138 a month (required); total shown $2,878 against $2,740 rent", "Technology Connect Monthly 138 optional false; price 2740 totalPrice 2878", o)
    F(k, "required_one_time_fees", "Common Area/Amenities $575 at move-in and at renewal; application $50; security deposit $750", "Common Area/Amenities MoveIn 575; Renewal 575", uu)
    F(k, "parking_type", "surface spots and assigned indoor bay garages, monthly fee $20 to $215", "Additional unassigned surface spots are available for an additional monthly fee. ... Our indoor bay garages are assigned and are on a first come, first serve basis with a monthly charge.", uu)
    F(k, "pool", "outdoor", "Heated saline outdoor swimming pool with sundeck", uu)
    F(k, "year_built", "2015", "year_built 2015", AL + "newark/avalon-union")
    F(k, "management_company", "AvalonBay Communities (owner-operator)", "communityId AVB-NJ026", uu)
    F(k, "utilities", "resident pays electric, gas, trash, water, sewer", "Electric Resident; Gas Resident; Trash Resident; Water Resident; Sewer Resident", uu)

for k, slug, unit, fl, yb in (("1500 ave at port imperial|07086", "riversedge-at-port-imperial", "RSE-347", 3, 2009), ("1300 ave at port imperial|07086", "riverparc", "RVP-0203", 2, 2015)):
    u = AL + "west-new-york/" + slug
    C(k, "elevator", "yes", "amenity: Elevator", u, "confirmed")
    C(k, "floor", f"{fl} (from unit number {unit})", f"unit {unit}", u, "confirmed")
    C(k, "dogs_allowed", "yes", "pet_policies: allowed true; allowed_pets cats, dogs; limit 2", u, "confirmed")
    F(k, "pet_rent", "$50 a month; $500 one-time", "rent: $50 per month; fee: $500", u)
    F(k, "year_built", str(yb), f"year_built {yb}", u); F(k, "management_company", "RHO Residential LLC", "pmc_display_name RHO Residential LLC", u)
    F(k, "doorman", "24-hour concierge", "amenity: 24hr concierge", u); F(k, "pool", "yes (indoor or outdoor not stated)", "amenity: Pool", u)
    F(k, "parking_type", "garage; fee not published (own site returned HTTP 403)", "amenities: Garage, Parking, Guest parking", u)
C("1500 ave at port imperial|07086", "dog_weight_limit", "unconfirmed", "restrictions: Pets are not allowed in the pool or amenity areas at any time. *One time and monthly fees will apply (no weight figure; own site returned HTTP 403)", AL + "west-new-york/riversedge-at-port-imperial", "unconfirmed")
C("1300 ave at port imperial|07086", "dog_weight_limit", "large dogs allowed; no pound figure; breed restrictions apply", "Dogs: Allowed; Number allowed: 2; Size allowed: Small, large; Monthly dog rent: $50/mo; One-time fee: $550", TR + "riverparc-at-port-imperial-1300-avenue-at-port-weehawken-nj-07086-2741124926", "confirmed")
F("1300 ave at port imperial|07086", "pet_fee_conflict", "one-time pet fee is $500 on Apartment List and $550 on Trulia", "fee: $500/one time | One-time fee: $550", TR + "riverparc-at-port-imperial-1300-avenue-at-port-weehawken-nj-07086-2741124926")

k = "4 ave at port imperial|07093"; u = AL + "west-new-york/the-landings-at-port-imperial"; zu = "https://www.zumper.com/apartment-buildings/p12562/the-landings-at-port-imperial-west-new-york-nj"
C(k, "elevator", "yes per Apartment List's amenity tag only; the owner's site returned HTTP 403, so floors and elevators per building could not be checked", "amenity: Elevator", u, "confirmed")
C(k, "floor", "unconfirmed: unit 1109 could be building 11, or floor 1 (ground floor)", "unit 1109", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Dog | Policy | Allowed | Limit | 3", zu, "confirmed")
C(k, "dog_weight_limit", "large dogs allowed; no pound figure", "Dogs: Allowed; Number allowed: 3; Size allowed: Small, large; Monthly dog rent: $80/mo; One-time fee: $500", TR + "the-landings-at-port-imperial-4-avenue-at-port-west-new-york-nj-07093-2750796385", "confirmed")
F(k, "pet_rent", "$80 a month per dog; $500 one-time", "Dog | Monthly Pet Fee | Monthly. 3 dogs max. | $80 | Pet Fee | One-time fee per pet. | $500", zu)
F(k, "year_built", "1998", "year_built 1998", u); F(k, "management_company", "Equity Residential", "pmc_display_name Equity Residential", u)
F(k, "parking_type", "garage; fee not published", "Garage Parking", zu); F(k, "pool", "yes (reviews describe a pool with skyline views)", "amenity: Pool", u)

EV = AV + "west-windsor-apartments/eaves-west-windsor"
for k, un, fl in (("6223 kaitlyn ct|08550", "006-6223", 2), ("9124 taylor ct|08550", "009-9124", 2), ("7132 heather dr|08550", "007-7132", 3)):
    uu = EV + "/apartment/NJ006-NJ006-" + un
    C(k, "elevator", "unconfirmed, and doubtful: the community and unit pages list no elevator, and every listed unit is on floor 1, 2 or 3, so the 'inferred from floor count' basis does not hold", "unit features: Floor %d; Corridor Access (no elevator feature listed)" % fl, uu, "unconfirmed")
    C(k, "floor", str(fl), "Floor %d" % fl, uu, "confirmed")
    C(k, "dogs_allowed", "yes", BREEDS, uu, "confirmed")
    C(k, "dog_weight_limit", NOWL, "Dogs: Allowed; Size allowed: Small, large (Trulia building page)", TR + "eaves-west-windsor-1000-jamie-brooks-ln-west-windsor-nj-08550-1003141797", "confirmed")
    F(k, "pet_rent", "$60 a month per dog; $500 one-time (Trulia still shows $55 a month)", "Pet Dog Fee Monthly 60; Pet Dog Fee MoveIn 500", uu)
    F(k, "required_monthly_fees", "Technology Connect $58 a month (required)", "Technology Connect Monthly 58 optional false", uu)
    F(k, "required_one_time_fees", "Common Area/Amenities $575 at move-in and at renewal; application $50; security deposit $750 ($99 deposit promotion if applied by 2026-11-30)", "Common Area/Amenities MoveIn 575; $99 deposit when you apply by 11-30!", uu)
    F(k, "parking_type", "unassigned surface parking with permit, monthly fee per vehicle ($15 to $350 range covers garages); detached garages for rent", "Residents are charged an additional monthly fee per vehicle. Spaces are unassigned however each resident will receive a parking permit to display in their vehicle. A limited number of detached garages are available for rent.", uu)
    F(k, "pool", "outdoor", "Heated outdoor swimming pool", uu)
    F(k, "management_company", "AvalonBay Communities (owner-operator)", "communityId AVB-NJ006", uu)
    F(k, "utilities", "trash included; resident pays electric, water, sewer; internet is in the required technology fee", "Trash Community; Electric Resident; Water Resident; Sewer Resident", uu)
    F(k, "community_address", "1000 Jamie Brooks Lane, West Windsor, NJ 08550", "addressLine1 1000 Jamie Brooks Lane", uu)

k = "555 new brunswick ave|08863"; g = "https://www.greystar.com/the-park-at-fords-corner-fords-nj/p_23509"; o = "https://theparkfords.com/"
C(k, "elevator", "not stated anywhere; six-story building, both units on floor 6 (plan rule: 6+ floors treated as elevator, with an asterisk)", "Construction is nearing completion on The Park at Fords Corner, a six-story residential building at 555 New Brunswick Avenue in Woodbridge Township, New Jersey", "https://newyorkyimby.com/2026/05/555-new-brunswick-avenue-nears-completion-in-woodbridge-township-new-jersey.html", "unconfirmed")
C(k, "floor", "units 616 and 607: floor 6", "floorLabel Floor 6", g, "confirmed")
C(k, "dogs_allowed", "yes", "The community accommodates cats and dogs and offers outdoor spaces where residents can enjoy time with their animals.", o + "faqs/", "confirmed")
C(k, "dog_weight_limit", "65", "We're a pet-friendly apartment community! Breed restrictions and a 65 pound weight limit apply", o, "confirmed")
F(k, "pet_rent", "$65 a month; $500 one-time pet fee; $30 one-time third-party pet screening", "Pet Rent 65 monthly; Pet Fee 500 one_time; Pet Management - Third Party 30 one_time", g)
F(k, "required_monthly_fees", "Community Lifestyle Fee $40; utility billing admin fee $6.06; renters liability insurance, electric and water/sewer required, amounts not stated", "Community Lifestyle Fee 40 monthly required; Utility - Billing Administrative Fee 6.06 monthly required", g)
F(k, "parking_type", "surface $100 a month; covered $200 a month; EV charging", "Parking 100 monthly; Parking - Covered 200 monthly", g)
F(k, "year_built", "2026 (new construction, nearing completion in May 2026)", "Construction is nearing completion on The Park at Fords Corner", "https://newyorkyimby.com/2026/05/555-new-brunswick-avenue-nears-completion-in-woodbridge-township-new-jersey.html")
F(k, "management_company", "Greystar (new building; no earlier manager)", "listed on greystar.com property page p_23509", g)
F(k, "doorman", "virtual doorman", "Virtual doorman system", o + "amenities/"); F(k, "pool", "none listed (pool table only)", "Shuffleboard Pool table", o + "amenities/")
F(k, "utilities", "all-electric building", "The all-electric design eliminates gas", o + "amenities/")
F(k, "availability_note", "site shows availableOn 2026-07-01 for both units, i.e. vacant since the building opened", "availableOn 2026-07-01", g)

# ---------------- NYC: elevator (PLUTO class), floor, dogs
FLOOR = {  # addr_key prefix -> (value, quote, status)
 "3516 34th": ("5 (from unit number 5E)", "unit 5E", "confirmed"), "3242 33rd": ("unconfirmed: unit D3 does not show the floor", "unit D3", "unconfirmed"),
 "31-20 54th": ("2 (listing gives the unit as '2fl')", "31-20 54th Street #2fl", "confirmed"), "23-50 waters edge dr|": ("5 (from unit number 5F)", "unit 5F", "confirmed"),
 "23-50 waters edge dr 4t": ("4 (from unit number 4T)", "unit 4T", "confirmed"), "16-70 bell": ("3 (from unit number 317)", "unit 317", "confirmed"),
 "867 dekalb": ("2 (from unit number 2B)", "unit 2B", "confirmed"), "1875 atlantic": ("6 (from unit number 601A)", "unit 601A", "confirmed"),
 "96 hart": ("3 (from unit number 3E)", "unit 3E", "confirmed"), "3440 guider": ("5", "1 bedroom 1 bath - 5th floor", "confirmed"),
 "2920 brighton": ("4 (from unit number 4CD; top floor of a 4-floor building, with a roof terrace)", "unit 4CD", "confirmed"), "2925 w 5th": ("7", "on the 7th floor with an east-facing balcony", "confirmed"),
 "250 clarkson": ("4 (from unit number 422)", "unit 422", "confirmed"), "219 lenox": ("5 (from unit number 5G)", "unit 5G", "confirmed"),
 "1010 rogers": ("4 (from unit number 4E)", "unit 4E", "confirmed"), "2561 bedford": ("3", "beautifully renovated third-floor one-bedroom residence", "confirmed"),
 "948 new york": ("2", "the second-floor location means a quick trip up and down, with an elevator for move-in day and grocery runs", "confirmed"),
 "3415 farragut": ("7 (from unit number 7K)", "unit 7K", "confirmed"), "1244 new york": ("3 (from unit number 3A)", "unit 3A", "confirmed"),
 "1644 new york": ("6 (from unit number 6E)", "unit 6E", "confirmed"), "2840 atlantic ave new york": ("unit 1029: floor 10; unit 714: floor 7 (from unit numbers)", "Unit 1029; Unit 714", "confirmed"),
 "2840 atlantic ave|": ("10 (from unit number E1029)", "unit E1029", "confirmed"), "44-10 ketcham": ("2 (from unit number 2F)", "unit 2F", "confirmed"),
 "41-42 elbertson": ("4 (from unit number 407)", "APT #407", "confirmed"),
}
ESA = {"23-50 waters edge dr|11360": "Cats are ok but no dogs unless service or emotional support dogs.",
       "23-50 waters edge dr 4t new york ny 11360 usa|11360": "**Dog is allowed only for service or emotional support dog.",
       "16-70 bell blvd 317 16-70 bell blvd bayside ny 11360 us|11360": "**Dog is allowed only for service or emotional support dog."}
for b in batch:
    if b["state"] != "NY": continue
    k = b["addr_key"]; url = b["urls"].split("|")[0].strip(); p = pluto.get(k)
    if p:
        cls = p["pluto_class"]; near = " (matched to the nearest lot, " + p["pluto_address"].title() + ")" if p["match_basis"] == "nearest_lot" else ""
        if cls.startswith("D"):
            C(k, "elevator", f"yes ({p['pluto_floors'] or 'unknown'} floors){near}", f"PLUTO building class {cls} (class D = elevator apartments); numfloors {p['pluto_floors'] or 'blank'}", PL, "confirmed")
        else:
            C(k, "elevator", f"yes ({p['pluto_floors']} floors) per the listing; PLUTO class {cls} is a condo class that does not say", "Elevator (Trulia feature list); The Highland spans 14 stories (Zumper description)", url, "confirmed")
        F(k, "building_size", f"{p['pluto_floors'] or 'unknown'} floors; {p['pluto_units']} units; built {p['pluto_year']}{near}", f"numfloors {p['pluto_floors']}; unitsres {p['pluto_units']}; yearbuilt {p['pluto_year']}", PL)
        F(k, "owner_of_record", p["pluto_owner"].title(), "ownername " + p["pluto_owner"], PL)
    v = next(val for key, val in FLOOR.items() if k.startswith(key))
    C(k, "floor", v[0], v[1], url, v[2])
    if k in ESA:
        C(k, "dogs_allowed", "no, except service or emotional-support dogs: the listing's description contradicts its own 'dogs allowed' field", ESA[k], url, "contradicts")
        C(k, "dog_weight_limit", "not applicable (pet dogs not accepted)", ESA[k], url, "contradicts")
    elif "trulia" in url:
        C(k, "dogs_allowed", "yes (listing field)", "Dogs: Allowed (Size allowed: Small)", url, "confirmed")
        C(k, "dog_weight_limit", "unconfirmed: the page says small dogs only and gives no pound figure; no building pet policy found", "Cats, small dogs allowed", url, "unconfirmed")
    elif "zumper" in url:
        C(k, "dogs_allowed", "yes (listing field)", "Pets | Dog | Policy | Allowed" if "p1528434" not in url else "page data lists dogs among accepted pets; no visible policy block", url, "confirmed")
        C(k, "dog_weight_limit", "unconfirmed: no weight figure", "Contact for more information on pet policy.", url, "unconfirmed")
    else:
        C(k, "dogs_allowed", "yes (listing field)", "amenities: Cats allowed, Dogs allowed, Pet friendly", url, "confirmed")
        C(k, "dog_weight_limit", "unconfirmed: no weight figure", "pet_policies: allowed true; no limit or restriction text", url, "unconfirmed")

def tf(prefix, fact, value, quote, url=None):
    for b in batch:
        if b["addr_key"].startswith(prefix): F(b["addr_key"], fact, value, quote, url or b["urls"].split("|")[0].strip())
tf("23-50 waters edge dr|", "doorman", "24-hour security with doorman", "24 hour security building with door man")
tf("23-50 waters edge dr|", "utilities", "heat, water and cooking gas included", "Heat, water, and cooking gas are included.")
tf("23-50 waters edge dr|", "parking_type", "assigned spaces, garage on site; fee not stated", "assigned parking spaces")
tf("23-50 waters edge dr|", "price_history", "raised from $2,200 to $2,250 on 2026-11-12; listed 2026-10-29", "Nov 12, 2026 PriceChange $2,250; Oct 29, 2026 Listed For Rent $2,200")
tf("23-50 waters edge dr 4t", "doorman", "24-hour doorman", "**24 hours doorman.")
tf("23-50 waters edge dr 4t", "utilities", "heat and cooking gas included", "**Heating and cooking gas are included, only pays electric.")
tf("16-70 bell", "utilities", "heat and cooking gas included", "**Heating and cooking gas are included, only pays electric.")
tf("16-70 bell", "parking_type", "on-site parking available; fee not stated", "** Parking available.")
tf("867 dekalb", "income_restriction", "income-restricted, rent-stabilized unit: household income $90,000 to $154,000", "HPD rent stabilized 1 bedroom apartment Some HPD guidelines may apply Minimum combined income 90k Maximum combined income 154k Maximum savings 210k")
tf("867 dekalb", "management_company", "YNS Management NY Inc (listing provider)", "YNS Management NY Inc")
tf("1875 atlantic", "parking_type", "parking available for an additional fee (amount not stated)", "Parking available for an additional fee")
tf("1875 atlantic", "doorman", "virtual doorman", "Virtual doorman")
tf("96 hart", "utilities", "heat and hot water included", "Multi-unit Building with Elevator Heat & Hot Water Included")
tf("96 hart", "parking_type", "street parking only", "Plenty of Street Parking")
tf("3440 guider", "doorman", "doorman", "Modern Building with doorman, Elevator, Gym, Laundry, Roof Top")
tf("3440 guider", "parking_type", "attached garage on site; fee not stated", "Parking: Attached Garage, On Site")
tf("250 clarkson", "availability_note", "available 2026-12-15, the last day of the window", "Available December 15th")
tf("1010 rogers", "price_history", "relisted at $2,699 on 2026-11-09 after $3,000 in July 2026", "Nov 9, 2026 Listed For Rent $2,699; Jul 21, 2026 Listed For Rent $3,000")
tf("2561 bedford", "listing_age", "listed 2026-09-23 at $2,950, cut to $2,850 then $2,750: about 53 days old", "Oct 27, 2026 PriceChange $2,750; Oct 19, 2026 PriceChange $2,850; Sep 23, 2026 Listed For Rent $2,950")
tf("2561 bedford", "building_note", "PLUTO shows 4 floors, 8 units, built 1910 with an elevator-class code; the listing never mentions an elevator", "Well-maintained multifamily building")
tf("948 new york", "income_requirement", "household income of $104,000+ and 700+ credit", "Requirements: Household income of $104,000+ (40x rent) and 700+ credit.")
tf("948 new york", "parking_type", "parking in building (assigned); fee not stated", "Elevator Shared rooftop Parking Bike room")
tf("3415 farragut", "doorman", "doorman / concierge / virtual doorman", "building amenities include a doorman, concierge, elevator, gym, package room, bike room, garage parking, and a furnished roof deck")
tf("3415 farragut", "parking_type", "garage parking; fee not stated", "Garage parking")
tf("1244 new york", "parking_type", "garage parking available; fee not stated", "Garage parking available")
tf("1644 new york", "price_history", "cut from $2,900 to $2,750 on 2026-11-10", "Nov 10, 2026 PriceChange $2,750; Nov 2, 2026 Listed For Rent $2,900")
tf("2840 atlantic", "management_company", "Bushburg Properties", "Bushburg Properties")
tf("2840 atlantic", "building_floors", "14", "The Highland spans 14 stories", "https://www.zumper.com/apartment-buildings/p1528434/the-highland-east-new-york-new-york-ny")
tf("44-10 ketcham", "building_type", "co-op building (unit rented by owner or broker; co-op board rules may apply to pets)", "Nice Coop Building in the heart of Elmhurst")
tf("44-10 ketcham", "utilities", "all utilities except cooking gas and electricity", "All utilities included except cooking gas and electricity")
tf("41-42 elbertson", "rent_regulation", "rent stabilized", "Rent stabilized, renovated luxury apartments 4 minutes from subway")
tf("41-42 elbertson", "parking_type", "garage parking; fee not stated", "Garage Parking")
tf("2925 w 5th", "listing_warning", "unit mismatch and co-op: Apartment List shows unit 7A at $1,776 for an 800 sq ft 1BR; its source link is a realtor.com record for Apt 23B; the lot belongs to Trump Village Section 3 Inc (co-op); text reads like a sale listing", "Original condition - perfect to renovate to your taste. | source_listing_url .../2925-W-5th-St-Apt-23B_Brooklyn_NY_11224_M98275-50211")
tf("2925 w 5th", "income_requirement", "3x the rent in household income", "Must have 3x the rent in total household income (before taxes)")
tf("2925 w 5th", "parking_type", "surface lot; fee not stated", "parking category surface_lot")
tf("3516 34th", "listing_warning", "same broker text as 32-42 33rd St #D3 word for word (TurboTenant, same phone), including '14 ft high ceilings': the description is not specific to this unit", "Beautiful, newly renovated 1 bedroom and 1 bathroom with eat in kitchen and 14 ft high ceilings, washer and dryer nearby")
tf("3242 33rd", "listing_warning", "same broker text as 35-16 34th St #5E word for word (TurboTenant, same phone): the description is not specific to this unit", "Beautiful, newly renovated 1 bedroom and 1 bathroom with eat in kitchen and 14 ft high ceilings, washer and dryer nearby")
tf("3242 33rd", "owner_operator", "A&E Real Estate (per Queens Ledger, 2026-02-12)", "Since acquiring 32-42 and 32-52 33rd Street, we have invested millions of dollars", "https://queensledger.com/?p=17428")

# ---------------- remaining evidence items
QL = "https://queensledger.com/?p=17428"
k = "3242 33rd st d3 astoria ny 11106 usa|11106"
I(k, "management", "2026-02-12", "tenants in Astoria, who are reporting major heating outages and negligent management at 32-52 33rd and its adjacent building, 32-42, are wondering when they’ll get their turn for justice.", "Queens Ledger", QL, "management_company")
I(k, "management", "2026-02-12", "That investment helps explain why building temperatures in 32-42 33rd Street have remained above the minimum threshold of 68 degrees despite some reported challenges with the heat.", "Queens Ledger (landlord's reply)", QL, "management_company")
# reviews shown on Zumper building pages ("Reviews from the web", Google source, dated)
ZR = [
 ("4 ave at port imperial|07093", "https://www.zumper.com/apartment-buildings/p12562/the-landings-at-port-imperial-west-new-york-nj", "positive", "The facility is always clean, the staff are very polite and accommodating to the needs of the tenants."),
 ("4 ave at port imperial|07093", "https://www.zumper.com/apartment-buildings/p12562/the-landings-at-port-imperial-west-new-york-nj", "positive", "I have lived here for 3 years and I love it."),
 ("1775 windsor rd|07666", "https://www.zumper.com/apartment-buildings/p373478/avalon-teaneck-teaneck-nj", "positive", "They keep it clean, well maintained and looking good. The property managers are on top of any issues that do come up."),
 ("1775 windsor rd|07666", "https://www.zumper.com/apartment-buildings/p373478/avalon-teaneck-teaneck-nj", "safety_incident", "Just today I witnessed him having to escort someone with a mental illness, who is not allowed on the property off the premises."),
 ("1775 windsor rd|07666", "https://www.zumper.com/apartment-buildings/p373478/avalon-teaneck-teaneck-nj", "other", "The only thing we've had trouble with since we moved in has been that periodically our apartment gets a smoky smell"),
 ("2400 vauxhall rd|07083", "https://www.zumper.com/apartment-buildings/p17845/avalon-union-union-nj", "other", "We have been here for 3 years in a second story unit. Our senior dog is getting older and we needed to move out because we need a 1st floor apartment."),
 ("2400 vauxhall rd|07083", "https://www.zumper.com/apartment-buildings/p17845/avalon-union-union-nj", "positive", "Although it’s a little pricey, the community is upgraded constantly and beautifully maintained."),
 ("5306 bristol dr|07083", "https://www.zumper.com/apartment-buildings/p17845/avalon-union-union-nj", "other", "We have been here for 3 years in a second story unit. Our senior dog is getting older and we needed to move out because we need a 1st floor apartment."),
 ("5306 bristol dr|07083", "https://www.zumper.com/apartment-buildings/p17845/avalon-union-union-nj", "positive", "Although it’s a little pricey, the community is upgraded constantly and beautifully maintained."),
]
revs = {}
for k, zu, cat, ex in ZR:
    if zu not in revs:
        st = Z.parse_state(page(zu)[0]); revs[zu] = (((st["detail"].get("buildingReviews") or {}).get("data") or {}).get("sources") or {}).get("google", {}).get("reviews") or []
    hit = [r for r in revs[zu] if ex in r["body"]]
    if not hit: print("NOT VERBATIM", ex[:50]); continue
    I(k, cat, datetime.date.fromtimestamp(hit[0]["date"]).isoformat(), ex, "Zumper building page ('Reviews from the web', Google)", zu)
LOOKED = ("No news or police item naming the building found (web search 2026-11-15: building name or address with police, theft, break-in, fire, tenants). "
          "Apartment List and Trulia pages carry no resident reviews. Better Business Bureau profile pages returned HTTP 403.")
for k, extra, url in (
    ("153 valley st|07079", " Building's own site and bozzuto.com disallow Claude agents.", AL + "east-orange/third-valley"),
    ("1500 ave at port imperial|07086", " Own site returned HTTP 403. No Zumper building page found.", AL + "west-new-york/riversedge-at-port-imperial"),
    ("1300 ave at port imperial|07086", " Own site returned HTTP 403. No Zumper building page found.", AL + "west-new-york/riverparc"),
    ("6223 kaitlyn ct|08550", " Zumper building page shows no reviews.", "https://www.zumper.com/apartment-buildings/p18722/eaves-West-Windsor-Apartments-Township-NJ"),
    ("9124 taylor ct|08550", " Zumper building page shows no reviews.", "https://www.zumper.com/apartment-buildings/p18722/eaves-West-Windsor-Apartments-Township-NJ"),
    ("7132 heather dr|08550", " Zumper building page shows no reviews.", "https://www.zumper.com/apartment-buildings/p18722/eaves-West-Windsor-Apartments-Township-NJ"),
    ("555 new brunswick ave|08863", " Building opened in 2026, so there is no tenant history yet.", "https://theparkfords.com/")):
    I(k, "none_found", "", LOOKED + extra, "search log", url)
for k in ("1775 windsor rd|07666", "2400 vauxhall rd|07083", "5306 bristol dr|07083", "4 ave at port imperial|07093"):
    I(k, "none_found", "", "car_crime, elevator, management complaints: none found. " + LOOKED + " Zumper shows only its eight highest-rated web reviews.", "search log", BK[k]["urls"].split("|")[0].strip())
NYL = "No Openigloo reviews (building not in Openigloo's reviewed-buildings sitemaps) and no news item found; official 311 and HPD records are listed separately."
for pre in ("31-20 54th", "2920 brighton", "2925 w 5th", "1010 rogers", "2561 bedford", "1244 new york", "1644 new york", "44-10 ketcham", "41-42 elbertson"):
    for b in batch:
        if b["addr_key"].startswith(pre): I(b["addr_key"], "none_found", "", "Tenant reviews and news: " + NYL, "search log", "https://www.openigloo.com/sitemap.xml")
print(put("confirm", conf), "confirm rows;", put("facts", facts), "fact rows;", put("items", items), "item rows")
