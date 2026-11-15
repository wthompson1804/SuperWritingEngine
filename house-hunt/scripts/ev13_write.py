"""Evidence batch 13: write the five evidence CSVs from what was read on the cached pages (no network).

Values below were read from pages cached in raw/evidence_b13/ (and, where noted, from pages the Trulia harvester cached
in raw/trulia/ earlier the same day, because Trulia answered 403 to this batch's later requests).
Retrieval times come from raw/evidence_b13/_index.jsonl. Re-running rewrites the files (idempotent).
"""
import csv, json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(ROOT)
N = 13
TS = {}
for line in open("raw/evidence_b13/_index.jsonl"):
    x = json.loads(line)
    if x["status"] == 200:
        TS[x["url"]] = x["retrieved_at"]
BLOCK_TS = {}
for line in open("raw/evidence_b13/_index.jsonl"):
    x = json.loads(line)
    if x["status"] == 403:
        BLOCK_TS.setdefault(x["url"], x["retrieved_at"])


def ts(u):
    return TS.get(u) or BLOCK_TS.get(u) or ""


T = "https://www.trulia.com/building/"
AL = "https://www.apartmentlist.com/"
Z = "https://www.zumper.com/"
U = {
    "quarry": T + "the-residences-at-quarry-walk-500-boulder-pass-oxford-ct-06478-2750903232",
    "quarry_al": AL + "ct/new-haven-county/the-residences-at-quarry-walk--2",
    "quarry_z": Z + "apartment-buildings/p833076/the-residences-at-quarry-walk-oxford-ct",
    "kestrel": T + "the-residences-at-the-kestrel-336-roosevelt-dr-seymour-ct-06483-2752176221",
    "kestrel_z": Z + "address/336-roosevelt-dr-seymour-ct-06483-usa",
    "lopresti": T + "lopresti-school-apartments-at-29-maple-street-29-maple-st-seymour-ct-06483-2750819801",
    "lopresti_own105": "https://websterrealty.managebuilding.com/Resident/public/rentals/16093",
    "lopresti_own306": "https://websterrealty.managebuilding.com/Resident/public/rentals/9286",
    "lopresti_z": Z + "apartment-buildings/p822012/lopresti-school-seymour-ct",
    "merion": AL + "ct/shelton/merion-riverwalk",
    "vista": T + "vista-apartments-1039-howe-ave-shelton-ct-06484-2766142177",
    "mark": T + "the-mark-fairfield-county-7-acadia-ln-shelton-ct-06484-2734028645",
    "brookview": T + "brookview-apts-303-bridgeport-ave-shelton-ct-06484-2758091490",
    "b301": T + "301-bridgeport-ave-301-bridgeport-ave-shelton-ct-06484-2795130832",
    "asher": "https://www.theasherstamford.com",
    "asher_sm": "https://sightmap.com/embed/5eved96mwqo",
    "asher_tr": T + "the-asher-150-broad-st-stamford-ct-06901-2748143234",
    "river": T + "the-riverhouse-9-w-main-st-stamford-ct-06902-2773044312",
    "river_own": "https://www.riverhousestamford.com/",
    "franklin": T + "163-franklin-street-163-franklin-st-stamford-ct-06901-1001659327",
    "franklin_z": Z + "apartment-buildings/p34538/moderne-stamford-ct",
    "prospect": T + "prospect-park-65-77-prospect-st-stamford-ct-06901-2750799601",
    "hoyt": T + "hoyt-bedford-apartments-112-hoyt-st-stamford-ct-06905-1002243171",
    "hoyt_z": Z + "address/112-hoyt-st-stamford-ct-06905-usa",
    "hoyt_n12": "https://connecticut.news12.com/2023/11/01/getting-the-hell-out-of-here-tenant-complains-of-condemned-stamford-apartment-building/6l13N0llouJS0ZPVm9widf",
    "ltl": T + "life-time-living-stamford-130-tresser-blvd-stamford-ct-06901-2775168599",
    "ltl_hbj": "https://hartfordbusiness.com/article/290-unit-apartment-and-athletic-country-club-complex-opens-in-stamford/",
    "lofts": T + "lofts-at-335-335-ferry-blvd-stratford-ct-06615-2750775490",
    "ten": T + "ten-trumbull-100-oakview-dr-trumbull-ct-06611-2737296301",
    "ten_own": "https://www.tentrumbull.com/apartments/ct/trumbull/amenities",
    "libc": T + "liberty-commons-619-s-main-st-waterbury-ct-06706-2754001738",
    "libc_al": AL + "ct/waterbury/liberty-commons",
    "m278": AL + "ct/west-haven/278-main-street",
    "m278_own": "https://www.278main.com/amenities/",
    "m278_faq": "https://www.278main.com/faq/",
    "m278_tr": T + "278-main-278-main-st-west-haven-ct-06516-1002374716",
    "crest": T + "crestview-estates-62-treat-st-west-haven-ct-06516-1002250793",
    "crest_z": Z + "apartment-buildings/p40637/crestview-apartments-west-haven-ct",
    "thom": T + "thompson-luxury-residences-165-richards-st-west-haven-ct-06516-2750806649",
    "thom_z": Z + "address/165-richards-st-west-haven-ct-06516-usa",
    "reg": T + "the-regency-200-elm-st-west-haven-ct-06516-1037833154",
    "m308": "https://www.trulia.com/home/308-main-st-8a-west-haven-ct-06516-466334129",
    "m308_z": Z + "apartment-buildings/p1257883/308-main-west-haven-ct",
    "k1202": "https://www.trulia.com/home/1202-kennedy-blvd-44r-bayonne-nj-07002-466488595",
    "k1204": "https://www.trulia.com/home/1204-kennedy-blvd-32a-bayonne-nj-07002-466510792",
    "k1204_z": Z + "address/1204-kennedy-blvd-bayonne-nj-07002-usa",
    "w25": "https://www.trulia.com/home/35-w-25th-st-30g-bayonne-nj-07002-466592982",
    "b971": "https://www.trulia.com/home/971-broadway-708-bayonne-nj-07002-2055080027",
    "lbc": AL + "nj/bayonne/liberty-bay-club",
    "lbc_own": "https://libertybayclub.com/floorplans/",
    "lbc_am": "https://libertybayclub.com/amenities/",
    "lbc_tr": T + "liberty-bay-club-190-w-54th-st-bayonne-nj-07002-2757882423",
    "lbc_z": Z + "address/190-w-54th-st-bayonne-nj-07002-usa",
    "rail": AL + "nj/bound-brook/rail-at-bound-brook",
    "rail_z": Z + "apartment-buildings/p1360226/the-rail-at-bound-brook-bound-brook-nj",
    "rail_cre": "https://www.connectcre.com/stories/development-team-cuts-ribbon-luxury-apartments-in-downtown-bound-brook/",
    "jc": AL + "nj/burlington/j-centra-burlington",
    "jc_own": "https://www.jcentraburlington.com/floorplans/",
    "jc_am": "https://www.jcentraburlington.com/amenities/",
    "jc_reb": "https://rebusinessonline.com/jefferson-apartment-group-completes-500-unit-project-in-burlington-new-jersey/",
}
# Trulia pages this batch could not refetch (403 bot wall) but which the harvester had cached earlier the same day.
EARLIER = {
    U["asher_tr"]: "2026-11-15T21:45:30+00:00", U["m278_tr"]: "2026-11-15T21:54:01+00:00", U["lbc_tr"]: "2026-11-15T20:01:11+00:00",
    U["m308"]: "2026-11-15T20:16:00+00:00", U["k1202"]: "2026-11-15T20:00:25+00:00", U["k1204"]: "2026-11-15T20:00:42+00:00",
    U["w25"]: "2026-11-15T20:00:56+00:00", U["b971"]: "2026-11-15T20:01:19+00:00",
}
NAME = {r["addr_key"]: (r["building_name"] or r["address"]) for r in csv.DictReader(open(f"data/reference/evidence_batches/batch_{N}.csv"))}
K = {
    "quarry": "500 boulder pass|06478", "kestrel": "336 roosevelt dr|06483", "lopresti": "29 maple st|06483", "merion": "185 canal st e|06484",
    "vista": "1039 howe ave|06484", "mark": "7 acadia ln|06484", "brookview": "303 bridgeport ave|06484", "b301": "301 bridgeport ave|06484",
    "asher": "150 broad st|06901", "river": "9 w main st|06902", "franklin": "163 franklin st|06901", "prospect": "65-77 prospect st|06901",
    "hoyt": "112 hoyt st|06905", "ltl": "130 tresser blvd|06901", "lofts": "335 ferry blvd|06615", "ten": "100 oakview dr|06611",
    "libc": "619 s main st|06706", "m278": "278 main st|06516", "crest": "62 treat st|06516", "thom": "165 richards st|06516",
    "reg": "200 elm st|06516", "m308": "308 main st|06516", "k1202": "1202 kennedy blvd|07002", "k1204": "1204 kennedy blvd|07002",
    "w25": "35 w 25th st|07002", "b971": "971 broadway|07002", "lbc": "190 w 54th st|07002", "rail": "100 hamilton st|08805", "jc": "3000 emily ln|08016",
}
assert set(K.values()) == set(NAME), set(NAME) ^ set(K.values())

live, conf, items, facts, ratings = [], [], [], [], []
PLAN = "Floor-plan level only: the page lists a plan price marked \"Available Now\" and no unit, so no unit, floor or date can be checked. Confirm by phone. "
WALL = "Trulia answered 403 (\"Access to this page has been denied\") at the re-fetch, so the listing could not be re-read. Last read by the harvester at %s UTC, when it showed: %s"


def L(k, url, unit, status, price, avail, match, site, notes, at=None):
    live.append([K[k], U.get(url, url), unit, status, price, avail, match, U.get(site, site), at or ts(U.get(url, url)), notes])


def C(k, fact, value, quote, src, status):
    conf.append([K[k], fact, value, quote, U.get(src, src), status])


def I(k, cat, date, excerpt, site, src, about):
    u = U.get(src, src)
    items.append([K[k], NAME[K[k]], cat, date, excerpt, site, u, about, ts(u) if cat != "none_found" else NOW])


def F(k, fact, value, quote, src):
    facts.append([K[k], fact, value, quote, U.get(src, src)])


def R(k, source, value, scale, count, asof, read, last6, neg6, negold, tags, src):
    ratings.append([K[k], NAME[K[k]], source, value, scale, count, asof, read, last6, neg6, negold, tags, U.get(src, src)])


NOW = max(TS.values())
SIZE = "no number on any page read"

# ---------------- 1. Quarry Walk
k = "quarry"
L(k, "quarry", "219", "live", 2625, "Available Now (date on page 2026-11-03)", "yes", "",
  "Trulia unit table: Unit 219, 1bd, 848 sqft, $2,625. Apartment List shows the same unit (plan G1, 219, $2,625, available now, updated 2026-11-14). "
  "Offer on page, verbatim: \"1 month free when you sign an 18 month lease.\" / \"Offer good until December 31, 2026\". The page does not say whether $2,625 is before or after the free month. "
  "Required monthly fee listed: Water and sewage $35-$45. Trulia page last modified 2026-11-12. Own leasing site not found (quarrywalk.com is the shopping village's site).")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility); Apartment List amenities also list Elevator", "quarry", "confirmed")
C(k, "floor", "unconfirmed", "Unit 219: my reading is floor 2. Why: three-digit unit numbers; the other listed unit is 112, and a resident review on Zumper says of a first-floor home \"We live in a 2 bedroom apartment on the first floor\". No page states the floor of 219.", "quarry", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; \"Cats, small dogs, large dogs allowed\"", "quarry", "confirmed")
C(k, "dog_weight_limit", "not stated (large dogs allowed)", "Dogs / Large dogs allowed; Size allowed: Small, large. " + SIZE + ". Zumper lists a limit of 1 dog.", "quarry", "unconfirmed")
F(k, "special_offer", "1 month free on an 18-month lease, until 2026-12-31; gross or net not stated", "1 month free when you sign an 18 month lease. | Offer good until December 31, 2026", "quarry")
F(k, "required_monthly_fees", "water and sewage $35-$45", "monthlyRequiredFees: Water and sewage min 35 max 45 (page data)", "quarry")
F(k, "parking", "optional garage parking $100 a month; underground parking", "Optional Garage Parking 100 Mo (special features); \"underground parking\" (description)", "quarry")
F(k, "management_company", "Haynes Development (Trulia); owner entity The Residences at Quarry Walk II LLC (Zumper)", "Property management company: Haynes Development", "quarry")
F(k, "deposit", "$2,675-$3,680", "Deposit Fee $2,675 - $3,680", "quarry")
F(k, "building_size", "86 units (Apartment List)", "total_units_count 86 (page data)", "quarry_al")
R(k, "Google rating shown on Zumper", 4.3, 5, 16, "2024-12-07", 8, 0, 0, 0, "", "quarry_z")
I(k, "positive", "2023-05-14", "I have been here since it opened January of last year. The community has grown. Management and Maintenance are wonderful and always greet you on a first name basis.", "Zumper (Google review)", "quarry_z", "building")
I(k, "positive", "2022-06-14", "Office Manager was amazing and Maintenance staff prompt and thorough.", "Zumper (Google review)", "quarry_z", "management_company")

# ---------------- 2. Kestrel
k = "kestrel"
L(k, "kestrel", "208", "live", 2100, "Available Now", "yes", "",
  "Trulia unit table: Unit 208, plan Style D, 1bd, 797 sqft, $2,100. Page last modified 2026-09-22 (about 8 weeks old) and the description says \"PLEASE CALL FOR CURRENT AVAILABLE UNITS OR FUTURE AVAILABLE UNITS\", so confirm by phone. No offer on the page. Own leasing site not found.")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "kestrel", "confirmed")
C(k, "floor", "unconfirmed", "Unit 208: my reading is floor 2. Why: the two listed units are 200 and 208 (three-digit numbers starting with 2). No page states the floor.", "kestrel", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; \"allows cats (up to 2), large dogs, and small dogs (up to 2)\"", "kestrel", "confirmed")
C(k, "dog_weight_limit", "not stated (large dogs allowed)", "Dogs / Large dogs allowed; Size allowed: Small, large. " + SIZE + ". Zumper lists a limit of 1 dog, Trulia 2.", "kestrel", "unconfirmed")
F(k, "pet_fees", "pet rent $40 a month; pet deposit $400", "Pet rent ($40); Pet deposit ($400)", "kestrel")
F(k, "year_built", "2023", "Brand new Building built in 2023", "kestrel")
F(k, "parking", "on-site parking lot; fee not stated; EV charging", "Parking Lot; \"There is onsite parking, electric vehicle charging, and basement storage available as well.\"", "kestrel")
F(k, "management_company", "Park Circle Holdings LLC (Zumper); Trulia names none", "pm_name Park Circle Holdings LLC (page data)", "kestrel_z")
R(k, "Google rating shown on Zumper", 5, 5, 2, "2024-12-08", 2, 0, 0, 0, "", "kestrel_z")
I(k, "positive", "2024-10-07", "It’s a wonderful place to live. You get great view of the river and it’s a very quiet area. Spacious parking lot and very well kept.", "Zumper (Google review)", "kestrel_z", "building")

# ---------------- 3. Lopresti
k = "lopresti"
L(k, "lopresti", "M306", "live", 2000, "Available Dec 1 (own site: Available 12/1/2026)", "yes", "lopresti_own306",
  "Trulia: Unit M306, 1bd, 1,315 sqft, $2,000. Manager's own Buildium page agrees: \"29 Maple St - 306 ... $2,000.00 / month Available 12/1/2026\". No offer.")
L(k, "lopresti", "M105", "live", 1750, "Trulia: Available Now; own site: Available 12/1/2026", "yes", "lopresti_own105",
  "Price agrees on both pages ($1,750). The date does not: Trulia says Available Now, the manager's own page says \"Available 12/1/2026\" (and 680 sqft against Trulia's 850). Use Dec 1. No offer.")
C(k, "elevator", "yes", "Property Features: Laundry room | Wheelchair access | Elevator", "lopresti_own306", "confirmed")
C(k, "floor", "unconfirmed", "Unit M306: my reading is floor 3. Why: other units listed for the building are M101-M114, M201-M213 and M301-M312, so the first digit looks like the floor. No page states it.", "lopresti_z", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit M105: my reading is floor 1, probably the ground floor (same numbering pattern). No page states it. If so it fails the no-ground-floor gate.", "lopresti_z", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed (Size allowed: Small); \"allows cats and small dogs. Large dogs are not permitted.\"", "lopresti", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed. Large dogs are not permitted. The manager's own pages state no pet policy.", "lopresti", "unconfirmed")
F(k, "management_company", "Webster School Realty LLC", "Property management company: Webster School Realty LLC", "lopresti")
F(k, "parking", "parking lot; \"abundant parking\"; fee not stated", "Parking Lot; Abundant Parking", "lopresti")
F(k, "laundry", "shared laundry in the building, not in the unit", "washer and dryer at building", "lopresti_own306")
F(k, "year_built", "own page says \"Built in 2026\" (a converted school; likely the conversion year)", "Built in 2026", "lopresti_own306")
F(k, "deposit", "$2,000 (306); $2,500 (105)", "$2,000.00 security deposit / $2,500.00 security deposit", "lopresti_own306")

# ---------------- 4. Merion Riverwalk
k = "merion"
MO = "Offer on page, verbatim: \"Move In by 12/15 for 1 Month Free! *Details Apply!\" The page does not say whether the listed price is before or after the free month. The price shown is for a 20-month lease (lease_length 20 in page data). Own site merionriverwalk.com answered 403."
L(k, "merion", "4083", "live", 2675, "available now (available_on 2026-10-22)", "yes", "", "Apartment List unit table: plan \"One Bedroom One Bathroom with Loft\", 978 sqft, $2,675, updated 2026-11-15. " + MO)
L(k, "merion", "2096", "live", 2283, "available now (available_on 2026-09-12)", "yes", "", "Apartment List unit table: plan \"One Bedroom One Bathroom\", 686 sqft, $2,283, updated 2026-11-15. On the market since September. " + MO)
C(k, "elevator", "yes", "Elevator (community amenities)", "merion", "confirmed")
C(k, "floor", "unconfirmed", "Unit 4083: my reading is floor 4 (top floor). Why: listed units are 2xxx, 3xxx and 4xxx, and every \"with Loft\" plan is a 4xxx unit, which fits a loft on the top floor. No page states it.", "merion", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 2096: my reading is floor 2 (same pattern). No page states it.", "merion", "unconfirmed")
C(k, "dogs_allowed", "yes", "allowed_pets: cats, dogs; amenities: Dogs allowed", "merion", "confirmed")
C(k, "dog_weight_limit", "not stated", "Pet policy on page: limit 2, rent $60, fee $600; no weight or size wording.", "merion", "unconfirmed")
F(k, "special_offer", "1 month free if moved in by Dec 15; gross or net not stated", "Move In by 12/15 for 1 Month Free! *Details Apply!", "merion")
F(k, "pet_fees", "pet rent $60 a month; pet fee $600; 2 pets", "general: limit 2, rent $60, fee $600", "merion")
F(k, "parking", "garage; fee not stated", "parking comment: Garage", "merion")
F(k, "pool", "yes (indoor or outdoor not stated)", "Pool (community amenities)", "merion")
F(k, "year_built", "2013; 250 units", "year_built 2013; total_units_count 250 (page data)", "merion")
F(k, "management_company", "Merion Residential (batch file); start date not found", "", "merion")
F(k, "application_fee", "$100 per application", "$100 per application", "merion")
R(k, "Apartment List", 4.7, 5, 3, "2026-11-15", 1, 0, 0, 0, "", "merion")
I(k, "positive", "2025-04-25", "The maintenance team is very efficient and professional. They stand out to me compared to places that I've lived previously.", "Apartment List", "merion", "management_company")

# ---------------- 5. Vista
k = "vista"
L(k, "vista", "200", "live", 2400, "Available Now", "yes", "",
  "Trulia: Unit 200 (plan named 201), 1bd, 1,148 sqft, $2,400. THE PAGE WAS LAST MODIFIED 2025-12-16, eleven months ago, so price and availability are not verified. "
  "Offer text, verbatim: \"Vista @11 leavenworth rd. 2 bedroom special. Rent is $2300. First month rent is $1100 with a savings of $1200. Vista 2@1039 howe ave. 1 bedroom w/office $2100. First month rent it $1100 with a savings of $1000.\" "
  "That offer quotes $2,100 for a 1-bedroom with office at this address, not $2,400. No own site found.")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "vista", "confirmed")
C(k, "floor", "unconfirmed", "Unit 200: my reading is floor 2, from the unit number only (plan name 201). No page states it.", "vista", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed (Size allowed: Small)", "vista", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "allows cats and small dogs. Large dogs are not permitted.", "vista", "unconfirmed")
F(k, "special_offer", "first month $1,100 on a $2,100 1-bedroom with office; gross or net not stated", "Vista 2@1039 howe ave. 1 bedroom w/office $2100. First month rent it $1100 with a savings of $1000.", "vista")
F(k, "parking", "assigned off-street parking lot; fee not stated", "Assigned off street parking", "vista")
F(k, "utilities_included", "garbage, sewer, water", "Rent Includes: Garbage, Sewer, Water", "vista")
F(k, "deposit", "$4,000", "Deposit Fee $4,000", "vista")

# ---------------- 6. The Mark
k = "mark"
for plan, p in (("Grand Denali", 2545), ("Grand Bryce", 2590)):
    L(k, "mark", "", "live", p, "plan marked \"Available Now\"; no unit listed", "yes", "",
      PLAN + f"Plan {plan}, 1bd, ${p:,}. 1-bedroom plans on the page: Bryce $2,470, Grand Denali $2,545, Grand Bryce $2,590, Denali $2,650. Page last modified 2026-10-29. No offer. Own site (themarkfairfieldcounty.com, a guess) did not resolve.")
C(k, "elevator", "yes", "Elevatored Buildings With Elegant Lobbies And Common Areas", "mark", "confirmed")
C(k, "floor", "unconfirmed", "No unit number on the page (plan-level listing), so no reading is possible.", "mark", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; \"allows cats, large dogs, and small dogs\"", "mark", "confirmed")
C(k, "dog_weight_limit", "not stated (large dogs allowed)", "Dogs / Large dogs allowed. " + SIZE + ".", "mark", "unconfirmed")
F(k, "pool", "yes, outdoor with cabanas", "chic poolside cabanas; Pool", "mark")
F(k, "parking", "parking lot / off-street; EV charging; fee not stated", "Parking Lot; Off Street Parking; EV Car Charging Station", "mark")
F(k, "management_company", "Continental Properties", "Property management company: Continental Properties", "mark")

# ---------------- 7. Brookview / 8. 301 Bridgeport
k = "brookview"
L(k, "brookview", "", "live", 2300, "plan marked \"Available Now\"; no unit listed", "yes", "",
  PLAN + "Plan \"1 bedroom with office\", 937 sqft, $2,300. THE PAGE WAS LAST MODIFIED 2025-06-09, seventeen months ago: treat as unverified. The description is a placeholder. No own site found.")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "brookview", "confirmed")
C(k, "floor", "unconfirmed", "No unit number on the page, so no reading is possible.", "brookview", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed (Number allowed: 1; Size allowed: Small)", "brookview", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "allows cats (up to 1) and small dogs (up to 1). Large dogs are not permitted.", "brookview", "unconfirmed")
F(k, "parking", "reserved off-street parking lot; fee not stated", "Reserved off street parking", "brookview")
F(k, "utilities_included", "garbage, sewer, water", "Rent Includes: Garbage, Sewer, Water", "brookview")
k = "b301"
L(k, "b301", "", "live", 2300, "plan marked \"Available Now\"; no unit listed", "yes", "",
  PLAN + "Plan \"1br\", 830 sqft, $2,300. Page last modified 2026-09-09. Description: \"Available is 35 units from 502 sq ft-907 sq ft\". No offer. No own site found.")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "b301", "confirmed")
C(k, "floor", "unconfirmed", "No unit number on the page, so no reading is possible.", "b301", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed (Number allowed: 1; Size allowed: Small)", "b301", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "allows cats (up to 1) and small dogs (up to 1). Large dogs are not permitted.", "b301", "unconfirmed")
F(k, "pet_fees", "pet deposit $600; a non-refundable pet fee is also listed, amount not stated", "Pet deposit ($600); Non-refundable pet fee", "b301")
F(k, "parking", "assigned off-street parking; fee not stated", "Assigned off street parking.", "b301")
F(k, "utilities_included", "garbage, sewer, water; storage room included", "Rent Includes: Garbage, Sewer, Water; \"storage room on the first floor included in rent\"", "b301")
F(k, "deposit", "$3,500", "Deposit Fee $3,500", "b301")
F(k, "building_age", "described as brand new, 35 units", "Beautiful brand new building ... Available is 35 units", "b301")

# ---------------- 9. The Asher
k = "asher"
AO = ("Offer on the building's site, verbatim: \"New Residents Can Enjoy 1-Month free! *For a limited time on select units and lease terms. Contact our leasing team for details and schedule your tour today.\" "
      "Neither the site nor the SightMap says whether the unit price is before or after the free month. The price shown is for a 21-month lease. Required monthly fees in the SightMap: Trash Fee $25, Amenity Fee $75; electricity varies.")
L(k, "asher", "530", "live", 2345, "Available Now", "yes", "asher", "Building's own SightMap: unit 530, 1 bed, 502 sqft, floor 5, $2,345; total with required fees $2,445. " + AO, at=ts(U["asher_sm"]))
L(k, "asher", "536", "live", 2332, "Available Dec 1st", "yes", "asher", "Building's own SightMap: unit 536, studio, 536 sqft, floor 5, $2,332; total with required fees $2,432. " + AO, at=ts(U["asher_sm"]))
C(k, "elevator", "yes", "Elevator (Trulia building page, read 2026-11-15 21:45 UTC); the building's SightMap lists floors B and 1 to 8", "asher_tr", "confirmed")
C(k, "floor", "5", "Unit 530: floor label 5 in the building's own SightMap unit data", "asher_sm", "confirmed")
C(k, "floor", "5", "Unit 536: floor label 5 in the building's own SightMap unit data", "asher_sm", "confirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; 2 pet max", "asher_tr", "confirmed")
C(k, "dog_weight_limit", "50", "Dogs / 50 lbs max weight (Trulia building page, read 2026-11-15 21:45 UTC; Trulia blocked the later re-fetch). The building's own site states no pet rules.", "asher_tr", "confirmed")
F(k, "special_offer", "1 month free on select units and lease terms; gross or net not stated", "New Residents Can Enjoy 1-Month free! *For a limited time on select units and lease terms.", "asher")
F(k, "special_offer_trulia", "up to 1 month free plus $500 look-and-lease", "For a limited time, enjoy up to 1-months free and $500 in look-and-lease savings on select units and lease terms.", "asher_tr")
F(k, "required_monthly_fees", "$100 (amenity $75 + trash $25); electricity extra", "Trash Fee 25.00; Amenity Fee 75.00; Electricity: Varies (utilities)", "asher_sm")
F(k, "pet_fees", "dog rent $50 a month; $600 one-time; 2 pets", "Dogs / $50 monthly pet fee; $600 One-time pet fee", "asher_tr")
F(k, "pool", "rooftop pool (outdoor)", "Rooftop pool with skyline views", "asher")
F(k, "parking", "garage; fee not stated", "Garage, Garage Lot (special features)", "asher_tr")
F(k, "building_floors", "8 above a basement level", "SightMap floor labels: B, 1, 2, 3, 4, 5, 6, 7, 8", "asher_sm")
F(k, "management_company", "RMS Companies (developer and manager); start date: since opening", "RMS Companies 148 Broad Street Stamford", "asher")
F(k, "lease_term_priced", "21 months", "display_lease_term: 21 Months", "asher_sm")

# ---------------- 10. Riverhouse
k = "river"
RN = ("THE LISTED PRICE IS NET-EFFECTIVE, NOT THE RENT PAID. Page text, verbatim: \"Net effective Prices advertised reflect 3 months free on 18 month leases! 12 month lease 1 month free + $2,000 sign on also ok. "
      "Tenants pay higher legal rent & take the credits throughout the lease. Extra Fees: Parking $95, Pets $50 and Amenity Fee\". "
      "My estimate of the gross rent, if 15 paid months of 18 give the advertised figure: $%s (estimate; the page does not state it). The amenity fee amount is not stated. "
      "Floor-plan level only: plans are named like unit numbers but the page lists no unit or date. Page last modified 2026-11-10. Own site riverhousestamford.com shows no prices.")
L(k, "river", "", "live", 2263, "plan \"308\" marked \"Available Now\"; no unit listed", "yes", "river_own", "Plan \"308\", 1bd, 640 sqft, $2,263. " + RN % "2,716")
L(k, "river", "", "live", 2025, "plan \"305\" marked \"Available Now\"; no unit listed", "yes", "river_own", "Plan \"305\", studio, 668 sqft, $2,025. " + RN % "2,430")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "river", "confirmed")
C(k, "floor", "unconfirmed", "Plan \"308\": my reading is floor 3. Why: the plans are named 319, 305, 308 and 304, which look like unit numbers on the third floor. The page gives no unit table, so this is not confirmed.", "river", "unconfirmed")
C(k, "floor", "unconfirmed", "Plan \"305\": my reading is floor 3 (same reason). Not confirmed.", "river", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; own site: \"Pet Policy: Pets are allowed\"", "river", "confirmed")
C(k, "dog_weight_limit", "not stated (large dogs allowed, 1 max)", "allows cats (up to 2), large dogs (up to 1), and small dogs (up to 2). " + SIZE + ".", "river", "unconfirmed")
F(k, "special_offer", "3 months free on an 18-month lease, or 1 month free plus $2,000 on a 12-month lease; listed price is net-effective", "Net effective Prices advertised reflect 3 months free on 18 month leases! 12 month lease 1 month free + $2,000 sign on also ok. Tenants pay higher legal rent & take the credits throughout the lease.", "river")
F(k, "gross_rent_estimate", "about $2,716 (1BR plan 308) and $2,430 (studio plan 305); value_type = estimate, method: advertised price x 18 / 15", "", "river")
F(k, "required_monthly_fees", "amenity fee, amount not stated", "Extra Fees: Parking $95, Pets $50 and Amenity Fee", "river")
F(k, "parking", "$95 a month; covered and uncovered, first come first served, secure lot", "Parking fee ($95); Covered and uncovered parking 1st come first serve. Available in secure parking lot.", "river")
F(k, "pet_fees", "pet rent $50 a month; pet deposit $250", "Pet rent ($50); Pet deposit ($250)", "river")
F(k, "building_age", "new building, now leasing", "Brand New Building Now leasing!", "river")
F(k, "management_company", "Empire Realty USA Corp", "Property management company: Empire Realty USA Corp", "river")
F(k, "broker_fee", "none", "No Broker Fee!", "river")

# ---------------- 11. 163 Franklin (The Moderne)
k = "franklin"
FN = "No offer block on the page; the description says \"hear about our current discounts on select lines\". Trulia page last modified 2026-10-31. Own site (163franklin.com, a guess) answered 403. Zumper calls the building The Moderne."
L(k, "franklin", "403", "live", 2625, "Available Nov 28", "yes", "", "Trulia unit table: Unit 403, plan C, 1bd, 848 sqft, $2,625. " + FN)
L(k, "franklin", "310", "live", 2600, "Available Now", "yes", "", "Trulia unit table: Unit 310, plan I, 1bd, 807 sqft, $2,600. " + FN)
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "franklin", "confirmed")
C(k, "floor", "unconfirmed", "Unit 403: my reading is floor 4. Why: listed units are 107, 204, 215, 305, 310, 311 and 403, so the first digit looks like the floor. No page states it.", "franklin", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 310: my reading is floor 3 (same pattern). No page states it.", "franklin", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; 2 pet max", "franklin", "confirmed")
C(k, "dog_weight_limit", "75", "Dogs / 75 lbs max weight; \"allows ... dogs up to 75 lbs (up to 2, $50/mo)\"", "franklin", "confirmed")
F(k, "pet_fees", "dog rent $50 a month per dog; $500 one-time per dog; breed restrictions", "Dog rent ($50 per dog); Dog fee ($500 per dog); Breed restrictions apply.", "franklin")
F(k, "parking", "garage and surface lot; fee not stated", "Garage, Garage Lot, Off Street Parking, Surface Lot (special features)", "franklin")
F(k, "management_company", "Riverwest Management", "Property management company: Riverwest Management", "franklin")
F(k, "other_name", "The Moderne", "The Moderne Apartments - 163 Franklin St Stamford CT", "franklin_z")

# ---------------- 12. Prospect Park
k = "prospect"
L(k, "prospect", "6G", "live", 2282, "Available Now (date on page 2026-10-21)", "yes", "",
  "Trulia unit table: Unit 6G, studio, 721 sqft, $2,282. Page last modified 2026-08-29 (eleven weeks old); unit dates run to 2026-10-21. No offer on the page. \"Pet rent\" is listed among required monthly fees without an amount. No own site found.")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "prospect", "confirmed")
C(k, "floor", "unconfirmed", "Unit 6G: my reading is floor 6. Why: listed units are 2C, 3H, 4J, 5J, 6G, 7H and 11J, so the number looks like the floor and the letter the line. No page states it.", "prospect", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed (Number allowed: 1; Size allowed: Small)", "prospect", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "allows cats (up to 1) and small dogs (up to 1). Large dogs are not permitted.", "prospect", "unconfirmed")
F(k, "parking", "underground garage $130 a month; uncovered outside $100 a month; all spots assigned", "All spots are assigned / Underground garage $130/month / Uncovered outside parking $100/month", "prospect")
F(k, "pet_fees", "pet deposit $500; pet rent amount not stated", "Pet deposit ($500); Pet rent", "prospect")
F(k, "utilities_included", "gas, heat, hot water", "Rent Includes: Gas, Heat, Hot Water", "prospect")

# ---------------- 13. Hoyt Bedford
k = "hoyt"
L(k, "hoyt", "140-3K", "live", 2145, "Available Dec 1", "yes", "",
  "Trulia unit table: Unit 140-3K, 1bd, 743 sqft, $2,145. Offer on page, verbatim: \"One Month's Rent Free! +Waived application fee\". The page does not say whether $2,145 is before or after the free month. "
  "Required monthly fees listed without amounts: \"Asset Protection\". Page last modified 2026-08-26. Description: \"Now under NEW MANAGEMENT!\" No working own site found (hoytbedford.com is another property).")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility). Note the 2023 News 12 report of an elevator out of use for a year in one of the buildings.", "hoyt", "confirmed")
C(k, "floor", "unconfirmed", "Unit 140-3K: my reading is floor 3 in the building numbered 140. Why: units are written building-floor+line (112-T2, 140-1F, 126-2E, 126-3E, 112-4D). No page states it.", "hoyt", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; Monthly dog rent $65/mo", "hoyt", "confirmed")
C(k, "dog_weight_limit", "not stated (small and large allowed)", "Size allowed: Small, large. " + SIZE + ". Zumper: \"We allow 1 pet per household.\"", "hoyt", "unconfirmed")
F(k, "special_offer", "one month free plus waived application fee; gross or net not stated", "One Month's Rent Free! +Waived application fee", "hoyt")
F(k, "pet_fees", "dog rent $65 a month; dog fee $350", "Dog rent ($65 per dog); Dog Fee ($350 each)", "hoyt")
F(k, "parking", "garage $150 a month; surface lot $40 a month", "Garage parking ($150 per vehicle); Surface parking ($40 per vehicle)", "hoyt")
F(k, "required_monthly_fees", "\"Asset Protection\", amount not stated", "monthlyRequiredFees: Asset Protection", "hoyt")
F(k, "utilities_included", "garbage, gas, heat, sewer, water, hot water", "Rent Includes: Garbage, Gas, Heat, Sewer, Water, Hot Water", "hoyt")
F(k, "year_built", "1940", "year_built 1940 (page data)", "hoyt_z")
F(k, "management_company", "Trulia names Rushmore Management; Zumper names Oakmark Management; the listing says \"Now under NEW MANAGEMENT!\". Date of the change not found.", "Now under NEW MANAGEMENT!", "hoyt")
R(k, "Google rating shown on Zumper", 3.6, 5, 145, "2024-12-07", 8, 0, 0, 0, "", "hoyt_z")
I(k, "management", "2023-11-01", "They say they have plenty to complain about, such as roaches in sinks and on walls, trash cans overflowing and a sometimes flooded parking garage.", "News 12", "hoyt_n12", "building")
I(k, "elevator", "2023-11-01", "There's even an elevator in one of the buildings that's been out of use for a year.", "News 12", "hoyt_n12", "building")
I(k, "management", "2023-11-01", "A woman who lives at the building says three buildings were recently without heat and hot water. The Stamford Health Department has since condemned the building at 98 Hoyt St.", "News 12", "hoyt_n12", "building")
I(k, "management", "2023-11-01", "Tenants say they were promised credits or compensation for the inconvenience in a letter from the management company, but no credits have been given yet.", "News 12", "hoyt_n12", "management_company")
I(k, "positive", "2024-11-17", "I have some years of living in the Hoyt Bedford apartments, very nice apartments very satisfied with the maintenance", "Zumper (Google review)", "hoyt_z", "building")

# ---------------- 14. Life Time Living
k = "ltl"
L(k, "ltl", "500", "live", 2400, "Available Dec 7", "yes", "",
  "Trulia unit table: Unit 500, plan S2, studio, 451 sqft, $2,400, date 2026-12-07 (inside the Dec 15 window). Offer on page, verbatim: \"1/2 Month Free\". The page does not say whether $2,400 is before or after it. Page last modified 2026-11-12. Own leasing site not identified.")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility); Hartford Business Journal: \"The 10-story building\"", "ltl", "confirmed")
C(k, "floor", "unconfirmed", "Unit 500: my reading is floor 5. Why: listed units are 500, 721, 826 and 903 in a 10-story building, so the first digit looks like the floor. No page states it.", "ltl", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; 2 pet max", "ltl", "confirmed")
C(k, "dog_weight_limit", "not stated (small and large allowed)", "Size allowed: Small, large; Restrictions: Certain Breed Restrictions. " + SIZE + ".", "ltl", "unconfirmed")
F(k, "special_offer", "half a month free; gross or net not stated", "1/2 Month Free", "ltl")
F(k, "pet_fees", "dog rent $50 a month; $500 deposit and $500 one-time fee per dog", "Dog rent ($50 per dog); Dog fee ($500 per dog); Dog deposit ($500 per dog)", "ltl")
F(k, "pool", "yes (in the attached Life Time club; indoor or outdoor not stated)", "Pool; Sauna", "ltl")
F(k, "parking", "garage; fee not stated", "Garage, Garage Lot (special features)", "ltl")
F(k, "building_floors", "10; 290 units; opened September 2023", "A 290-unit mixed-use apartment complex and athletic club has opened in Stamford ... The 10-story building's one-, two- and three-bedroom apartments", "ltl_hbj")
F(k, "management_company", "Mirador Real Estate (leasing)", "Property management company: Mirador Real Estate", "ltl")

# ---------------- 15. Lofts at 335
k = "lofts"
LO = ("Offer on page, verbatim: \"The next 2 approved applications will receive December rent free with move in by November 30th. Just pay utilities.\" The page does not say whether the listed price is net of it. "
      "Required monthly fees: Pest Control $5, Trash $15, Water $45 ($65 in all). Trulia page last modified 2026-09-30; unit dates are current. Own site loftsat335.com answered 403.")
L(k, "lofts", "313", "live", 2145, "Available Now (date on page 2026-11-13)", "yes", "", "Trulia unit table: Unit 313, plan 1 Bedroom F, 735 sqft, $2,145. " + LO)
L(k, "lofts", "305", "live", 2125, "Available Dec 7", "yes", "", "Trulia unit table: Unit 305, plan 1 Bedroom B1, 720 sqft, $2,125. A Dec 7 move-in misses the offer's Nov 30 deadline. " + LO)
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "lofts", "confirmed")
C(k, "floor", "unconfirmed", "Unit 313: my reading is floor 3. Why: listed units are 206, 207, 209, 305, 307, 313 and 409, so the first digit looks like the floor. No page states it.", "lofts", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 305: my reading is floor 3 (same pattern). No page states it.", "lofts", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; 2 pet max", "lofts", "confirmed")
C(k, "dog_weight_limit", "not stated (small and large allowed)", "Size allowed: Small, large. " + SIZE + ".", "lofts", "unconfirmed")
F(k, "special_offer", "December rent free for the next 2 approved applications moving in by Nov 30; gross or net not stated", "The next 2 approved applications will receive December rent free with move in by November 30th. Just pay utilities.", "lofts")
F(k, "required_monthly_fees", "$65 (pest control $5, trash $15, water $45)", "Pest Control ($5 each); Trash ($15 each); Water ($45 each)", "lofts")
F(k, "pet_fees", "pet rent $75 a month per pet; $300 one-time per pet", "Dog rent ($75 per dog); Dog fee ($300 per dog)", "lofts")
F(k, "parking", "not stated on the page; EV charging station listed", "Electric Car Charging Station", "lofts")
F(k, "management_company", "Red Tail Residential", "Property management company: Red Tail Residential", "lofts")
F(k, "deposit", "$1,900-$2,400", "Deposit min 1900 max 2400 (page data)", "lofts")

# ---------------- 16. Ten Trumbull
k = "ten"
L(k, "ten", "", "live", 2469, "plan marked \"Available Now\"; no unit listed", "yes", "https://www.tentrumbull.com/",
  PLAN + "Plan Kentfield, 1bd, 867 sqft, $2,469. THE TRULIA PAGE WAS LAST MODIFIED 2025-08-18, fifteen months ago: treat as unverified. The building's own floor-plans page shows no prices (\"contact us today\"). No offer on either page.")
C(k, "elevator", "yes", "Elevatored Buildings With Elegant Lobbies & Common Areas", "ten_own", "confirmed")
C(k, "floor", "unconfirmed", "No unit number on any page read, so no reading is possible.", "ten", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed; own site lists a Dog Park", "ten", "confirmed")
C(k, "dog_weight_limit", "not stated (large dogs allowed)", "Dogs / Large dogs allowed. " + SIZE + "; the own site states no pet rules.", "ten", "unconfirmed")
F(k, "pool", "outdoor, heated, with cabanas", "Step outside to the resort-style heated pool with cabanas, dog park, bocce court", "https://www.tentrumbull.com/")
F(k, "parking", "parking lot / off-street; car charging; fee not stated", "Parking Lot; Off Street Parking; Car Charging Station", "ten")
F(k, "management_company", "Continental Properties", "Property management company: Continental Properties", "ten")
F(k, "building_size", "202 units (Apartment List)", "total_units_count 202 (page data)", AL + "ct/trumbull/ten-trumbull")
F(k, "deposit", "$1,000", "Deposit Fee $1,000", "ten")

# ---------------- 17. Liberty Commons
k = "libc"
L(k, "libc", "3", "live", 1500, "Available Now", "yes", "",
  "Trulia: Unit 3, $1,500, 912 sqft, filed under Studio but the plan is named \"2 Bedroom\" and the description says the property \"offers spacious two and three bedroom apartments\": this is almost certainly a 2-bedroom, not a studio or 1-bedroom. "
  "THE PAGE WAS LAST MODIFIED 2025-05-05, eighteen months ago. Offer block, verbatim: \"There is no application fee and some income restrictions apply.\" (income-restricted housing). "
  "Trulia says dogs are not allowed. carabetta.com did not connect.")
C(k, "elevator", "yes", "The upper floors are handicap accessible with elevators.", "libc", "confirmed")
C(k, "floor", "unconfirmed", "Unit \"3\": no reading possible; the label looks like a listing slot, not an apartment number.", "libc", "unconfirmed")
C(k, "dogs_allowed", "no (Trulia) / yes (Apartment List)", "Trulia: Dogs: Not allowed; Cats: Allowed. Apartment List: allowed_pets include dogs, limit 2, \"25 lbs weight restriction\". The two sources disagree; ask the manager.", "libc", "contradicts")
C(k, "dog_weight_limit", "25 (Apartment List only)", "25 lbs weight restriction", "libc_al", "contradicts")
F(k, "income_restricted", "yes", "There is no application fee and some income restrictions apply.", "libc")
F(k, "year_built", "2015", "Built in 2015", "libc")
F(k, "management_company", "Carabetta Companies", "The property is maintained by Carabetta's 24 hour Maintenance Team", "libc")
F(k, "parking", "off-street parking; fee not stated", "There is also ample off-street parking.", "libc")
F(k, "pet_fees", "$300 deposit / $300 fee (Apartment List)", "general: deposit $300, fee $300, limit 2", "libc_al")
F(k, "security", "foot patrol and access system", "secured by foot patrol and a security access system", "libc")

# ---------------- 18. 278 Main
k = "m278"
MN = "No offer on the page (specials empty). Price is for a 16-month lease (lease_length 16 in page data). Own site 278main.com has no prices in its HTML (floor plans load from RentCafe)."
L(k, "m278", "G112", "live", 1933, "available 2026-12-08", "yes", "https://www.278main.com/", "Apartment List unit table: plan THE FRANKLIN, unit G112, 952 sqft, $1,933. " + MN)
L(k, "m278", "G107", "live", 1998, "available now (available_on 2026-09-16)", "yes", "https://www.278main.com/", "Apartment List unit table: plan THE FRANKLIN, unit G107, 952 sqft, $1,998. On the market since September. " + MN)
C(k, "elevator", "yes", "Elevators (amenities list on the building's own site)", "m278_own", "confirmed")
C(k, "floor", "unconfirmed", "Unit G112: my reading is floor 1, probably the ground floor. Why: other units listed are F201 and F322, so the letter looks like a wing and the first digit the floor. No page states it. If so it fails the no-ground-floor gate.", "m278", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit G107: my reading is floor 1, probably the ground floor (same pattern). No page states it.", "m278", "unconfirmed")
C(k, "dogs_allowed", "yes", "Yes, 278 Main is a pet-friendly community and welcomes both cats and dogs. The community allows a maximum of 1 dog and 1 cat per apartment", "m278_faq", "confirmed")
C(k, "dog_weight_limit", "25", "Pet Policy: 25lbs max. Maximum 2 Pets per unit. $400. Non-Refundable Pet Deposit. $25. Monthly Pet Rent. Breed Restrictions Apply. (Trulia building page, read 2026-11-15 21:54 UTC; Trulia blocked the later re-fetch. The own site gives no number.) 25 lb is exactly the gate.", "m278_tr", "confirmed")
F(k, "pet_fees", "pet rent $35 a month (Apartment List) or $25 (Trulia text); $400 one-time; own site: 1 dog and 1 cat max", "general: rent 35.0, fee 400.0, limit 2", "m278")
F(k, "parking", "open lot, included in the lease", "Open lot: included in lease", "m278")
F(k, "utilities_included", "sewer, water", "utilities_included_text: Sewer, Water", "m278")
F(k, "year_built", "1926; 100 units; restored historic building", "year_built 1926; total_units_count 100 (page data)", "m278")
F(k, "management_company", "South Oxford Management", "Property management company: South Oxford Management", "m278_tr")
F(k, "move_in_fees", "$27 application per applicant; $200 holding fee; deposit from $250 based on credit", "$27 Per Applicant; $200 holding fee; $250-Based on credit/background", "m278")

# ---------------- 19. Crestview
k = "crest"
CO = ("Offer on page, verbatim: \"One Month Security Deposit for a December 1 move-in!\" / \"Offer good until November 30, 2026\" (a deposit offer, not a rent discount). "
      "Floor-plan level only: plans are named like unit numbers but the page lists no unit or date. Page last modified 2026-09-14. No own site found.")
L(k, "crest", "", "live", 1575, "plan \"103\" marked \"Available Now\"; no unit listed", "yes", "", "Plan \"103\", 1bd, 900 sqft, $1,575. " + CO)
L(k, "crest", "", "live", 1625, "plan \"208\" marked \"Available Now\"; no unit listed", "yes", "", "Plan \"208\", 1bd, 900 sqft, $1,625. " + CO)
C(k, "elevator", "yes", "Brand new, state-of-the-art elevator", "crest", "confirmed")
C(k, "floor", "unconfirmed", "Plan \"103\": my reading is floor 1, probably the ground floor, if the plan name is the unit number. Not confirmed.", "crest", "unconfirmed")
C(k, "floor", "unconfirmed", "Plan \"208\": my reading is floor 2, if the plan name is the unit number. Not confirmed.", "crest", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed (Size allowed: Small)", "crest", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed; Pet Policy: Pet rent $40/month + one time $400 fee (no bully breeds)", "crest", "unconfirmed")
F(k, "special_offer", "one-month security deposit for a Dec 1 move-in, until 2026-11-30", "One Month Security Deposit for a December 1 move-in! | Offer good until November 30, 2026", "crest")
F(k, "pet_fees", "pet rent $40 a month; $400 one-time; no bully breeds", "Pet rent $40/month + one time $400 fee (no bully breeds)", "crest")
F(k, "pool", "outdoor (summer)", "Gorgeous pool with relaxing sitting area; Zumper: \"a pool for the summer\"", "crest")
F(k, "parking", "large parking lot, EV chargers; fee not stated", "EV chargers and a large parking lot", "crest")
F(k, "utilities_included", "garbage, gas, heat, hot water", "Rent Includes: Garbage, Gas, Heat, Hot Water", "crest")
F(k, "year_built", "1978", "year_built 1978 (page data)", "crest_z")

# ---------------- 20. Thompson (165 Richards)
k = "thom"
L(k, "thom", "?", "changed", 2095, "Unit 112: Available Now", "no", "",
  "The stored row was $2,100 with no unit. Nothing is at $2,100 now: the nearest 1-bedrooms are Unit 112 at $2,095 (Trulia) and #106 at $2,095 (Zumper). Trulia page last modified 2025-12-08 though its unit dates are current.")
L(k, "thom", "007", "live", 1885, "Available Now (date on page 2026-11-01)", "yes", "",
  "Trulia unit table: Unit 007, 1bd, $1,885. Zumper's page for the same address shows #007 at $1,795 (listing modified 2026-11-15): the two disagree by $90, ask which is current. No offer on the page. Trulia page last modified 2025-12-08. Own site (a guess) did not resolve.")
C(k, "elevator", "yes", "Elevator (Levels, Entrance, & Accessibility)", "thom", "confirmed")
C(k, "floor", "unconfirmed", "Unit 007: my reading is the lowest level (ground or garden level). Why: the building's units run 007-014, 103-115 and 204-211, so 0xx sits below floor 1. No page states it. Likely fails the no-ground-floor gate.", "thom_z", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 112 (nearest to the stored $2,100 row): my reading is floor 1, one level above the 0xx units. No page states it.", "thom", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed (Number allowed: 1; Size allowed: Small)", "thom", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed; 1 pet max", "thom", "unconfirmed")
F(k, "parking", "free on-site parking lot", "Free on-Site Parking Lot", "thom")
F(k, "management_company", "The Bouklis Group | MFH", "Property management company: The Bouklis Group | MFH", "thom")
F(k, "price_conflict", "Unit 007: $1,885 on Trulia, $1,795 on Zumper", "165 Richards St #007, 1 bed, 1795 (page data, modified 2026-11-15)", "thom_z")

# ---------------- 21. Regency
k = "reg"
L(k, "reg", "", "live", 1420, "plan marked \"Available Now\"; no unit listed", "yes", "",
  PLAN + "Plan \"JR 1 BEDROOM\", filed as studio, 450 sqft, $1,420. THE PAGE WAS LAST MODIFIED 2025-12-19, eleven months ago: treat as unverified. No offer. The manager's site fountainheadpm1.com failed with a certificate error and was not read.")
C(k, "elevator", "yes", "Two 2 Elevators In The Building", "reg", "confirmed")
C(k, "floor", "unconfirmed", "No unit number on the page, so no reading is possible.", "reg", "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs: Allowed (Size allowed: Small)", "reg", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed", "reg", "unconfirmed")
F(k, "parking", "assigned, one space per unit, enclosed lit lot; fee not stated", "Assigned parking. One parking space per unit.", "reg")
F(k, "utilities_included", "gas, heat, hot water, internet", "Rent Includes: Gas, Heat, Internet, Hot Water", "reg")
F(k, "management_company", "Fountainhead Property Management", "Property management company: Fountainhead Property Management", "reg")

# ---------------- 22-26. single units behind the Trulia wall
k = "m308"
L(k, "m308", "8A", "blocked", "", "", "", "",
  WALL % ("20:16", "$1,295, For Rent, listed 2026-10-30, available now, studio. ") + "Zumper's building page for 308 Main (read at this check) shows a studio at $1,295 still active, with no unit number, so the price is corroborated but the unit is not.")
C(k, "elevator", "unconfirmed", "No page read says the building has an elevator (Trulia listing as cached at 20:16 UTC, Zumper building page). It was only inferred from height.", "m308_z", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 8A: no reading possible. Another listing in the building is \"unit #14\", so 8A may be an apartment number, not floor 8.", "m308_z", "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats & Dogs allowed. (listing text as cached at 20:16 UTC)", "m308", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed", "m308", "unconfirmed")
F(k, "pet_fees", "pet rent $25 a month; pet fee $250", "Pet rent $25/mo; Pet fee $250", "m308")
F(k, "utilities_included", "heat and hot water", "Heat & Hot Water Included in Rent", "m308")
F(k, "deposit", "$1,943 (1.5 months); $50 application per adult", "Move-in: 1st month's rent + 1.5-month security deposit.", "m308")
k = "k1202"
L(k, "k1202", "44R", "blocked", "", "", "", "",
  WALL % ("20:00", "$1,695, For Rent, listed 2026-11-06, available now. ") + "Its description read \"CHARMING 1 BEDROOM APARTMENT | 4TH FLOOR WALKUP\": no elevator. "
  "Offer in that text, verbatim: \"SPECIAL RENT PROMOTION! Sign an 18-Month Lease and Receive 1 MONTH FREE! Sign a 13-Month Lease and Receive HALF A MONTH FREE!\" (\"offer ends 11/30/2026\"); gross or net not stated.")
C(k, "elevator", "no", "CHARMING 1 BEDROOM APARTMENT | 4TH FLOOR WALKUP. (listing text as cached at 20:00 UTC)", "k1202", "contradicts")
C(k, "floor", "4", "Unit 44R: \"4TH FLOOR WALKUP\" (listing text as cached at 20:00 UTC)", "k1202", "confirmed")
C(k, "dogs_allowed", "case by case", "Pet Policy: Pets allowed on a case-by-case basis. $250 refundable pet deposit. $25/month pet rent.", "k1202", "unconfirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed", "k1202", "unconfirmed")
F(k, "special_offer", "1 month free on an 18-month lease or half a month on a 13-month lease, ends 2026-11-30; gross or net not stated", "SPECIAL RENT PROMOTION! Sign an 18-Month Lease and Receive 1 MONTH FREE! Sign a 13-Month Lease and Receive HALF A MONTH FREE!", "k1202")
F(k, "parking", "street parking only", "Street parking only.", "k1202")
F(k, "pet_fees", "pet rent $25 a month; $250 refundable deposit", "$250 refundable pet deposit, $25/month pet rent.", "k1202")
F(k, "utilities_included", "heat and hot water", "Heat and hot water included.", "k1202")
k = "k1204"
L(k, "k1204", "32A", "blocked", "", "", "", "",
  WALL % ("20:00", "$1,695, For Rent, listed 2026-11-09, available now; \"Subject to broker fee\". ") + "Zumper (read at this check) lists other units at this address, 32M, 42M and 35M, at $1,695, active since late October, but not 32A.")
C(k, "elevator", "unconfirmed", "No page read mentions an elevator. The adjoining 1202 Kennedy Blvd is advertised as a \"4TH FLOOR WALKUP\", so this is probably a walk-up too; not stated.", "k1204", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 32A: my reading is floor 3, by analogy with next door, where 44R is on the 4th floor. No page states it.", "k1204", "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed (listing as cached at 20:00 UTC); Zumper listings at the address say \"Pet Friendly\"", "k1204", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed", "k1204", "unconfirmed")
F(k, "broker_fee", "yes", "Subject to broker fee", "k1204")
F(k, "utilities_included", "heat and water", "Heat and water are included for added convenience.", "k1204")
k = "w25"
L(k, "w25", "30G", "blocked", "", "", "", "", WALL % ("20:00", "$1,749, For Rent, listed 2026-11-12, available now, studio. ") + "No other source for this unit was found.")
C(k, "elevator", "unconfirmed", "No page read mentions an elevator. Only inferred from height.", "w25", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 30G: no reading possible from the number alone.", "w25", "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed; \"is pet friendly\" (listing as cached at 20:00 UTC)", "w25", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed", "w25", "unconfirmed")
F(k, "parking", "off-street, on site, $100 a month", "Parking fee $100/mo; Off Street Parking, On Site", "w25")
F(k, "pet_fees", "pet rent $50 a month", "Pet rent $50/mo", "w25")
k = "b971"
L(k, "b971", "708", "blocked", "", "", "", "", WALL % ("20:01", "$2,355, For Rent, listed 2026-10-26, available now. ") + "No other source for this unit was found; the building's own leasing site was not identified.")
C(k, "elevator", "unconfirmed", "No page read says \"elevator\". The listing names a rooftop lounge and an attached garage and the unit is 708, which points to a mid-rise that would have one; not stated.", "b971", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 708: my reading is floor 7, from the unit number only.", "b971", "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed; \"Pet Friendly\" (listing as cached at 20:01 UTC)", "b971", "confirmed")
C(k, "dog_weight_limit", "small dogs only; no number", "Cats, small dogs allowed", "b971", "unconfirmed")
F(k, "parking", "attached garage, on site; fee not stated", "Attached Garage, On Site", "b971")
F(k, "pet_fees", "pet rent $50 a month; pet fee $550", "Pet rent $50/mo; Pet fee $550", "b971")

# ---------------- 27. Liberty Bay Club
k = "lbc"
L(k, "lbc", "457", "live", 2276, "available now (available_on 2026-08-12)", "yes", "lbc_own",
  "Apartment List: plan Abby, unit 457, 780 sqft, $2,276 base, $2,283 with required fees. The building's own site agrees: #457, \"$2,276 Base Rent\", \"Total Monthly Leasing Price $2,282.06\", Available Now, priced for a 10-month term, floor 4. "
  "No offer: Apartment List says \"Liberty Bay Club is not currently offering any rent specials\" and the own site lists none for the unit. Vacant since August.")
C(k, "elevator", "yes", "Elevator convenience (amenities list on the building's own site)", "lbc_am", "confirmed")
C(k, "floor", "4", "Unit 457: floor_name \"4\", Building 1, in the building's own unit data", "lbc_own", "confirmed")
C(k, "dogs_allowed", "yes", "Liberty Bay Club welcomes cats and dogs and accepts a maximum of two pets per", "lbc_am", "confirmed")
C(k, "dog_weight_limit", "no limit", "Dogs and Cats allowed, $500 one-time fee per pet, $65 pet rent monthly per pet, no weight restrictions but breed restrictions apply.", "lbc", "confirmed")
F(k, "pet_fees", "pet rent $65 a month per pet; $500 one-time per pet; $25 third-party pet screening; long restricted-breed list", "The following dog breeds are restricted: Akita, Tosa Inus, German Shepherd, Malamute, Rottweiler ...", "lbc_am")
F(k, "parking", "private garage and surface parking; $135 a month, covered $160 (Trulia page read 20:01 UTC)", "Parking - Covered ($160); Parking ($135)", "lbc_tr")
F(k, "required_monthly_fees", "about $6 (total $2,282.06 against base $2,276); electric, water/sewer and renters insurance are extra", "Total Monthly Leasing Price * $2,282.06", "lbc_own")
F(k, "pool", "outdoor pool with sundeck", "Stunning swimming pool, sundeck and spa", "lbc_am")
F(k, "management_company", "Greystar; Zumper still lists the building as Woodmont Bay Club under Woodmont Properties, so management changed; date not found", "pm_name Woodmont Properties (Zumper page data); own site footer links greystar.com", "lbc_z")
F(k, "building_size", "220 units", "total_units_count 220 (page data)", "lbc")
F(k, "move_in_costs", "estimated application costs $1,050; estimated move-in costs $2,949.06", "Est. Application Costs $1,050; Est. Move-in Costs $2,949.06", "lbc_own")

# ---------------- 28. Rail at Bound Brook
k = "rail"
RL = "No offer: \"Rail at Bound Brook is not currently offering any rent specials.\" Required monthly amenity fee $25 on top of rent. Own site therailboundbrook.com answered 403."
L(k, "rail", "303", "live", 2604, "available now (available_on 2026-10-30)", "yes", "", "Apartment List unit table: plan 1 Bedroom with Den, unit 303, 852 sqft, $2,604. " + RL)
L(k, "rail", "529", "live", 2453, "available now (available_on 2026-11-06)", "yes", "", "Apartment List unit table: plan 1 Bedroom Standard, unit 529, 709 sqft, $2,453. " + RL)
C(k, "elevator", "yes", "Elevator (community amenities); Connect CRE: \"Standing at six stories\"", "rail", "confirmed")
C(k, "floor", "unconfirmed", "Unit 303: my reading is floor 3. Why: listed units are 303, 422, 529 and 605 in a six-story building, so the first digit looks like the floor. No page states it.", "rail", "unconfirmed")
C(k, "floor", "unconfirmed", "Unit 529: my reading is floor 5 (same pattern). No page states it.", "rail", "unconfirmed")
C(k, "dogs_allowed", "yes", "allowed_pets: cats, dogs; Zumper: dog ok", "rail", "confirmed")
C(k, "dog_weight_limit", "not stated", "Zumper pet policy for dogs: \"Restrictions: None\". No page gives a number or says there is no weight limit.", "rail_z", "unconfirmed")
F(k, "required_monthly_fees", "amenity fee $25 a month", "Monthly Amenity Fee($25.00/unit)", "rail")
F(k, "move_in_fees", "holding fee $250; application $50 per applicant; deposit $1,000 to 1.5 months' rent", "At Application: Holding Fee($250.00/unit); Application Fee($50.00/applicant, Nonrefundable); At Move-in: Security Deposit (Refundable)($1000.00-1.5 Months Rent)", "rail")
F(k, "parking", "garage; optional, price varies", "Parking: Optional & Pricing Varies", "rail")
F(k, "building_floors", "6; 143 units; ribbon cut June 2025", "Standing at six stories in downtown Bound Brook ... a new 143-unit luxury multifamily community", "rail_cre")
F(k, "management_company", "Aventerra Property Management LLC (Zumper); developer Denholtz Properties", "pm_name Aventerra Property Management LLC (page data)", "rail_z")

# ---------------- 29. J Centra
k = "jc"
JO = ("Offer on Apartment List, verbatim: \"SAVE UP TO 6 WEEKS RENT FREE ON BRAND NEW APARTMENTS & TOWNHOME RENTALS! *must be a 12 or 18 month lease term. new applications only. subject to change without notice.\" "
      "Neither page says whether $2,489 is before or after it. The own site prices the unit at \"Starting at $2,489\" for an 18-month term ($2,602 for 7 months). THE UNIT IS ON FLOOR 1 (own site unit data): it fails the no-ground-floor gate.")
L(k, "jc", "8102", "live", 2489, "available now (available_on 2025-12-10)", "yes", "jc_own", "Apartment List: plan C5, unit 8102, 1,034 sqft, $2,489; own site agrees (#8102, C5 Den, Building 8). Listed as available since December 2025, eleven months. " + JO)
L(k, "jc", "11102", "live", 2489, "available now (available_on 2026-02-15)", "yes", "jc_own", "Apartment List: plan C5, unit 11102, 1,034 sqft, $2,489; own site agrees (#11102, C5 Den, Building 11). Listed as available since February 2026. " + JO)
C(k, "elevator", "unconfirmed", "Elevators in select buildings (own site). Trade press: \"four-story buildings with elevators (3), three-story breezeway walk-ups (11) and both three-story and four-story stacked buildings\". Whether buildings 8 and 11 have one is not stated; most buildings do not.", "jc_am", "unconfirmed")
C(k, "floor", "1", "Unit 8102: floor_name \"1\", building 8, in the building's own unit data (ground floor)", "jc_own", "confirmed")
C(k, "floor", "1", "Unit 11102: floor_name \"1\", building 11, in the building's own unit data (ground floor)", "jc_own", "confirmed")
C(k, "dogs_allowed", "yes", "J Centra Burlington is a pet-friendly community and welcomes up to 2 cats or dogs per home", "jc_am", "confirmed")
C(k, "dog_weight_limit", "200 (combined, two pets)", "welcomes up to 2 cats or dogs per home with a combined weight of 200lbs. Please see leasing associate for details.", "jc_am", "confirmed")
F(k, "special_offer", "up to 6 weeks free on a 12- or 18-month lease; gross or net not stated", "SAVE UP TO 6 WEEKS RENT FREE ON BRAND NEW APARTMENTS & TOWNHOME RENTALS! *must be a 12 or 18 month lease term.", "jc")
F(k, "pet_fees", "pet rent $50 a month", "general: rent 50.0", "jc")
F(k, "parking", "surface parking; optional garages, rate not stated", "In addition to the surface parking, there is optional garage parking at J Centra Burlington.", "https://www.jcentraburlington.com/faqs/")
F(k, "pool", "two outdoor pools", "Resort-style pool with sunshelf and sunken dry seating area; Exercise pool with swim lanes", "jc_am")
F(k, "building_layout", "20 buildings, 500 units; 3 four-story elevator buildings, 11 three-story walk-ups, the rest stacked; completed 2025", "J Centra's design plans include three styles across its 20 buildings: four-story buildings with elevators (3), three-story breezeway walk-ups (11) and both three-story and four-story stacked buildings.", "jc_reb")
F(k, "management_company", "Jefferson Apartment Group (developer; own site footer)", "", "https://www.jcentraburlington.com/")

# ---------------- ratings: none_found rows, and none_found items
LOOKED_Z_NONE = "Zumper: no building page (address page 404, not on the city page)"
NF = {
    "lopresti": "Zumper building page (review block empty): " + U["lopresti_z"] + "; Apartment List: no building page; Trulia building page carries no ratings; manager's Buildium site: no ratings",
    "vista": LOOKED_Z_NONE + "; Apartment List: no building page; Trulia building page carries no ratings",
    "mark": "Zumper: only an old single-unit page at the address, no review block; Apartment List: no building page at the guessed address; Trulia building page carries no ratings; own site did not resolve",
    "brookview": LOOKED_Z_NONE + "; Apartment List: no building page; Trulia building page carries no ratings",
    "b301": LOOKED_Z_NONE + "; Apartment List: no building page; Trulia building page carries no ratings",
    "asher": LOOKED_Z_NONE + "; Apartment List: no building page at the guessed address; own site theasherstamford.com: no rating widget; Trulia page carries no ratings",
    "river": LOOKED_Z_NONE + "; Apartment List: no building page at the guessed address; own site riverhousestamford.com shows three undated promotional testimonials with no stars or count (not recorded); Trulia page carries no ratings",
    "franklin": "Zumper building page (review block empty): " + U["franklin_z"] + "; Apartment List: no building page at the guessed address; Trulia page carries no ratings",
    "prospect": LOOKED_Z_NONE + "; Apartment List: no building page at the guessed address; Trulia page carries no ratings",
    "ltl": LOOKED_Z_NONE + "; Apartment List building page exists with no rating and no reviews: " + AL + "ct/stamford/life-time-living-stamford; Trulia page carries no ratings",
    "lofts": LOOKED_Z_NONE + "; Apartment List: no building page at the guessed address; own site answered 403; Trulia page carries no ratings",
    "ten": LOOKED_Z_NONE + "; Apartment List building page exists with no rating and no reviews: " + AL + "ct/trumbull/ten-trumbull; own site tentrumbull.com: no rating widget (it links to Yelp, which is off limits); Trulia page carries no ratings",
    "libc": "Zumper address page (review block empty): " + Z + "address/619-s-main-st-waterbury-ct-06706-usa; Apartment List building page exists with no rating and no reviews: " + U["libc_al"] + "; Trulia page carries no ratings",
    "m278": "Apartment List building page: no rating, no reviews: " + U["m278"] + "; Zumper address page (review block empty); own site 278main.com: no rating widget, only a survey link",
    "crest": "Zumper building page (review block empty): " + U["crest_z"] + "; Apartment List: no building page; Trulia page carries no ratings",
    "thom": "Zumper address page (review block empty): " + U["thom_z"] + "; Apartment List: no building page at the guessed address; Trulia page carries no ratings",
    "reg": "Zumper address page (review block empty): " + Z + "address/200-elm-st-west-haven-ct-06516-usa; Trulia page carries no ratings; manager's site not reachable (certificate error)",
    "m308": "Zumper building page (review block empty): " + U["m308_z"] + "; Trulia listing blocked (403)",
    "k1202": "Zumper address page (review block empty): " + Z + "address/1202-kennedy-blvd-bayonne-nj-07002-usa; Trulia listing blocked (403)",
    "k1204": "Zumper address page (review block empty): " + U["k1204_z"] + "; Trulia listing blocked (403)",
    "w25": "Zumper: no page for the address (404); Trulia listing blocked (403)",
    "b971": "Zumper: no page for the address (404); Trulia listing blocked (403)",
    "lbc": "Apartment List building page: no rating, no reviews: " + U["lbc"] + "; Zumper address page under the old name Woodmont Bay Club (review block empty): " + U["lbc_z"] + "; own site libertybayclub.com: no rating widget",
    "rail": "Apartment List building page: no rating, no reviews: " + U["rail"] + "; Zumper building page (review block empty): " + U["rail_z"] + "; own site answered 403",
    "jc": "Apartment List building page: no rating, no reviews: " + U["jc"] + "; Zumper: no page for the address (404); own site jcentraburlington.com: no rating widget",
}
for kk, where in NF.items():
    ratings.append([K[kk], NAME[K[kk]], "none_found", "", "", "", "2026-11-15", 0, "", "", "", "", where])
NEWS = "one web search for news about the building and its manager (no article about this address found)"
have = {r[0] for r in items}
for kk, where in NF.items():
    if K[kk] not in have:
        items.append([K[kk], NAME[K[kk]], "none_found", "", "", "", "Looked at: " + where + "; " + NEWS if kk not in ("m308", "k1202", "k1204", "w25", "vista", "brookview", "b301", "crest", "reg", "lopresti") else "Looked at: " + where + "; no news search was run for this small building", "", NOW])

rk = {k_: i for i, k_ in enumerate(K.values())}
for rows in (live, conf, items, facts, ratings):
    rows.sort(key=lambda r: rk[r[0]])
OUT = {
    "live_check": (["addr_key", "listing_url", "unit", "status", "price_now", "available_now_text", "matches_stored", "building_site_url", "checked_at", "notes"], live),
    "confirm": (["addr_key", "fact", "value", "quote", "source_url", "status"], conf),
    "items": (["addr_key", "building_name", "category", "item_date", "excerpt", "source_site", "source_url", "about", "retrieved_at"], items),
    "facts": (["addr_key", "fact", "value", "quote", "source_url"], facts),
    "ratings": (["addr_key", "building_name", "rating_source", "rating_value", "rating_scale", "review_count", "as_of_date", "reviews_read", "reviews_last_6_months", "negative_last_6_months", "negative_older", "serious_issue_tags_last_6_months", "source_url"], ratings),
}
for name, (hdr, rows) in OUT.items():
    with open(f"data/evidence/{name}_batch_{N}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        w.writerows(rows)
    print(name, len(rows))
from collections import Counter
print("live", Counter(r[3] for r in live))
print("confirm", Counter(r[5] for r in conf), Counter((r[1], r[5]) for r in conf))
print("items", Counter(r[2] for r in items))
print("ratings", Counter("none" if r[2] == "none_found" else "rated" for r in ratings))
print("buildings in live", len({r[0] for r in live}), "ratings", len({r[0] for r in ratings}), "items", len({r[0] for r in items}))
print("missing ts", [r[:3] for r in live if not r[8]], [r[:3] for r in items if not r[8]])
