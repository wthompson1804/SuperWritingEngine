"""Second pass for mid_hudson (2026-11-15): buildings read from their own leasing sites, manager portfolios
(Bottini Properties, Eastdale Village, Village Place at Goshen, The Park at Main, North Court) and Zumper/PadMapper
building pages. Pages were fetched with `h_region_mid_hudson.py fetch|zb|zj` (robots-checked, cached in
raw/region_mid_hudson/). This script only writes the facts read from those cached pages. Idempotent (upsert by key).
"""
import csv, hashlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import h_region_mid_hudson as H
import h_mgmt_common as C

SRC = H.SRC
def meta(url):
    t, m = H.fetch(url)   # cached: no network
    return m
def lid(url, key):
    return SRC + ":" + hashlib.sha1((url + "|" + key).encode()).hexdigest()[:12]
def row(url, name, addr, city, zip_, **kw):
    m = meta(url)
    g = H.geo(f"{addr}, {city}, NY {zip_}")
    r = dict(listing_id=lid(url, name + kw.get("unit", "")), source_site=url.split("/")[2].replace("www.", ""), url=url,
             detail_level="building_page", first_seen=m["retrieved_at"], last_seen=m["retrieved_at"], building_name=name,
             address=addr, city=city, state="NY", zip=zip_, lat=g[0] if g else "", lon=g[1] if g else "",
             listing_type="managed_building", building_url=url, raw_path=m["path"])
    r.update(kw)
    return r

BOT = "https://www.bottiniproperties.com/apartments-property-page/"
rows, bl = [], []
def B(**k):
    bl.append(k)

# ---- Eastdale Village, Poughkeepsie 12603 (own site + pet policy document + manager AppFolio listings)
rows.append(row("https://www.eastdalevillage.com/elevator-building", "Eastdale Village (Elevator Building)", "10 Otto Way", "Poughkeepsie", "12603",
    dogs="yes", dog_weight_limit_lb="35", elevator="yes", building_floors="3",
    dog_policy_text="Pet policy outline (https://www.eastdalevillage.com/s/UpdatedPetPolicy-2025.docx): 'A maximum of 1 dog is allowed per residence'; 'The maximum full-grown weight for dogs is 35 pounds'; breed list restricted (Akita, Pit Bull, Mastiff, Staffordshire, Cane Corso, Rottweiler, Great Dane, German Shepherd, Malamute, Presa Canario, Husky, Chow, Dalmatian, Doberman, Border Collie, Boxer). Pet rent not stated in the outline.",
    parking_type="reserved parking space (amenities page)", laundry="washer & dryer optional (included in some plans)",
    manager="Kirchhoff Property Management (resident portal kirchhoffpm.appfolio.com) / MHTC Development",
    notes="NO_AVAILABILITY: site says 'Availability is extremely limited'; no prices on the site; the manager's listing page https://kirchhoffpm.appfolio.com/listings showed 'No vacancies found' on 2026-11-15. Elevator buildings are three-story with studio (Fir 418 sf) and 1BR flats (750-961 sf); the community also has walk-up buildings, so confirm the building. 35 lb limit passes the 25 lb gate. 'Resort Style Pool' (not stated indoor), dog park, dog wash, clubhouse gym, trash removal. Call (845) 454-6500."))
B(name="Eastdale Village (Elevator Building)", address="10 Otto Way", town="Poughkeepsie (12603)", url="https://www.eastdalevillage.com/", floors="3", elevator="yes (elevator buildings; walk-ups also on site)", dogs="yes (1 dog)", weight_limit="35", verdict="pass_no_availability", source_url="https://www.eastdalevillage.com/elevator-building", notes="No prices on site; manager AppFolio listings page shows no vacancies. Pet policy docx on site.")

# ---- 7 Creek Drive, Beacon (Bottini)
rows.append(row(BOT + "7-creek-drive", "7 Creek Drive", "7 Creek Dr", "Beacon", "12508", beds="1", listed_rent="3000",
    price_basis="'Rent Starting At: 1 & 2 Bedrooms from $3000-$3800' (manager property page; starting price, not a unit)",
    dogs="yes", dog_policy_text="Manager page: 'Pet Fee $25 monthly & $300 Nonrefundable fee'; dog wash. Zumper building page: Dog policy allowed, limit 1. No weight limit stated.",
    elevator="yes", pet_rent="25", parking_type="heated garage (fee based)", laundry="in-unit washer & dryer", manager="Bottini Properties LLC",
    notes="NO_AVAILABILITY: no unit with a date found. Manager availability search is script-rendered (static page shows 0 results); Zumper building page listed only a 2BR at 3,800. 1BR starts at 3,000 = the cap, so all-in would exceed 3,000 once pet rent ($25) and garage fee are added. Elevator from Zumper/PadMapper amenities (https://www.zumper.com/apartment-buildings/p875023/7-creek-drive-beacon-ny). Creekside building, rooftop deck, fitness center, package room, key fob. Application fee $20."))
B(name="7 Creek Drive", address="7 Creek Dr", town="Beacon", url=BOT + "7-creek-drive", floors="not_stated", elevator="yes (Zumper amenities)", dogs="yes (limit 1)", weight_limit="not_stated", verdict="pass_no_availability (1BR from 3000 = cap; all-in over)", source_url=BOT + "7-creek-drive", notes="Bottini Properties. Pet fee $25/mo + $300. Heated garage fee based. Rooftop deck, dog wash.")
B(name="25-28 Creek Drive", address="28 Creek Dr", town="Beacon", url=BOT + "25-28-creek-drive", floors="", elevator="not stated", dogs="yes (pet fee $25/mo + $300)", weight_limit="not_stated", verdict="fails:no studio/1BR (2 & 3 bedrooms from $4,600-$7,600)", source_url=BOT + "25-28-creek-drive", notes="Bottini Properties.")
rows.append(row(BOT + "beacon-row-apartments", "Beacon Row Apartments", "65 E Main St", "Beacon", "12508", beds="0", listed_rent="1700",
    price_basis="'Rent Starting At: Studio $1,700, 1 Bedroom $2,200' (manager property page; starting price, not a unit)",
    dogs="yes", dog_policy_text="Manager page: 'Pet Fee $25 monthly & $300 Nonrefundable fee'. PadMapper building page: Dog policy allowed, limit 1. No weight limit stated.",
    elevator="unknown", pet_rent="25", parking_type="resident parking on site", laundry="on-site laundry room", manager="Bottini Properties LLC",
    notes="NO_AVAILABILITY: PadMapper building page (https://www.padmapper.com/buildings/p1575650/beacon-row-apartments-at-65-e-main-st-beacon-ny-12508) shows studios and 1BRs unavailable. ELEVATOR_UNKNOWN: 8-unit brick building (formerly Red Hook Terminal), no elevator mentioned on either page; likely walk-up, confirm."))
B(name="Beacon Row Apartments", address="65-71 E Main St", town="Beacon", url=BOT + "beacon-row-apartments", floors="", elevator="not stated (8 units; likely walk-up)", dogs="yes (limit 1)", weight_limit="not_stated", verdict="elevator_unknown; no availability", source_url=BOT + "beacon-row-apartments", notes="Studio from 1,700, 1BR from 2,200. Bottini.")
B(name="Royal Pointe Apartments", address="161 Clubhouse Dr", town="Poughkeepsie (12603)", url=BOT + "royal-pointe-apartments", floors="", elevator="not stated", dogs="pets (fee $25/mo + $300; pet park)", weight_limit="not_stated", verdict="elevator_unknown: 1BR from 1,975; no elevator or availability on the page", source_url=BOT + "royal-pointe-apartments", notes="Bottini. In-ground pool, fitness center, clubhouse.")
B(name="Carriage Hill Apartments", address="214 Woodhill Dr", town="Goshen", url=BOT + "carriage-hill-apartments", floors="", elevator="no (page: '140-unit garden style')", dogs="pets (fee $25/mo + $300)", weight_limit="not_stated", verdict="fails:garden-style, no elevator stated", source_url=BOT + "carriage-hill-apartments", notes="Bottini.")
B(name="Woodhill Fletcher Apartments", address="214 Woodhill Dr", town="Goshen", url=BOT + "woodhill-fletcher-apartments", floors="", elevator="no (page: '48 unit garden style')", dogs="pets (fee $25/mo + $300)", weight_limit="not_stated", verdict="fails:garden-style, no elevator stated (1BR from 1,950)", source_url=BOT + "woodhill-fletcher-apartments", notes="Bottini.")
B(name="Oak Tree Garden Apartments", address="120 Channingville Rd", town="Wappingers Falls", url=BOT + "oak-tree-garden-apartments-", floors="", elevator="no (page: 'garden style')", dogs="'Pet Friendly - 35 lbs. or less'", weight_limit="35", verdict="fails:garden-style, no elevator stated (1BR from 1,180; weight limit passes)", source_url=BOT + "oak-tree-garden-apartments-", notes="Bottini. Heat and hot water included.")
B(name="The Dutcher House", address="1 Oak St", town="Pawling", url=BOT + "the-dutcher-house-", floors="", elevator="not stated", dogs="no ('Pet Friendly - Cats Only')", weight_limit="", verdict="fails:no dogs", source_url=BOT + "the-dutcher-house-", notes="Bottini.")
B(name="Toje Realty", address="2757-2759 W Main St", town="Wappingers Falls", url=BOT + "toje-realty", floors="", elevator="not stated (several small buildings)", dogs="pets (fee $25/mo + $300)", weight_limit="not_stated", verdict="elevator_unknown: 1BR from 1,050; small buildings", source_url=BOT + "toje-realty", notes="Bottini.")

# ---- Village Place at Goshen (own site)
rows.append(row("https://www.villageplaceatgoshen.com/floor-plans", "Village Place at Goshen", "100 Canter Ct", "Goshen", "10924",
    dogs="yes", dog_policy_text="Own site: 'Pet friendly community'. Zumper 207 Canter Ct page: Dogs OK. Limits not published.", elevator="yes",
    parking_type="indoor parking beneath the building with elevator service to all units", laundry="full size washers and dryers", manager="Wainco Realty, LLC",
    notes="BUILDING_FAILS: no studio or 1BR. All four floor plans on the site are 2 bedroom / 2 bath (1,290-1,408 sq ft). Elevator confirmed on the own site ('Indoor parking with elevator service to all units')."))
B(name="Village Place at Goshen (Canter Ct)", address="100 Canter Ct", town="Goshen", url="https://www.villageplaceatgoshen.com/", floors="not_stated", elevator="yes (own site)", dogs="yes (pet friendly; limits not published)", weight_limit="not_stated", verdict="fails:no studio/1BR (all plans 2BR/2BA)", source_url="https://www.villageplaceatgoshen.com/floor-plans", notes="Wainco Realty. Indoor parking with elevator service.")

# ---- Zumper / PadMapper pages
Z = "https://www.zumper.com/apartment-buildings/"
B(name="RiverBend at Wappingers Falls Apartments", address="80 Sterling Dr", town="Wappingers Falls", url=Z + "p10613/riverbend-at-wappingers-falls-llc-wappingers-falls-ny", floors="", elevator="not listed in Zumper or Zillow amenities", dogs="yes (limit 2, breed restrictions)", weight_limit="not_stated", verdict="no_availability: only a 2BR (3,180) listed; no studio/1BR; elevator not listed", source_url=Z + "p10613/riverbend-at-wappingers-falls-llc-wappingers-falls-ny", notes="Eagle Rock Properties. Built 2007, 178 units. Dog monthly fee $60, one-time $500, DNA $50; billing admin fee $5/mo; surface parking $0, garage parking available; swimming pool with sundeck (not stated indoor).")
B(name="RiverBend East", address="120 Beacon Ln", town="Wappingers Falls", url=Z + "p1060031/riverbend-east-wappingers-falls-ny", floors="", elevator="not stated", dogs="no ('No pets allowed')", weight_limit="", verdict="fails:no pets; 2BR only", source_url=Z + "p1060031/riverbend-east-wappingers-falls-ny", notes="")
B(name="115 Jackson Street", address="115 Jackson St", town="Fishkill", url=Z + "p854300/115-jackson-street-fishkill-ny", floors="", elevator="not stated", dogs="no ('No pets')", weight_limit="", verdict="fails:no pets; 2BR only", source_url=Z + "p854300/115-jackson-street-fishkill-ny", notes="")
B(name="Knollcrest Village", address="300 Knollcrest Ln", town="Chester", url=Z + "p15313/knollcrest-village-chester-ny", floors="", elevator="not stated", dogs="no ('No pets allowed')", weight_limit="", verdict="fails:no pets", source_url=Z + "p15313/knollcrest-village-chester-ny", notes="")
B(name="170 Clove Branch Rd", address="170 Clove Branch Rd", town="Hopewell Junction", url=Z + "p1582455/170-clove-branch-rd-hopewell-junction-ny", floors="", elevator="not listed", dogs="yes (limit 1)", weight_limit="not_stated", verdict="elevator_unknown: 1BR 1,899; small building, no elevator in amenities", source_url=Z + "p1582455/170-clove-branch-rd-hopewell-junction-ny", notes="AJ3 Management Services LLC")
B(name="Squire Village", address="374 Temple Hill Rd", town="New Windsor", url=Z + "p71102/squire-village-properties-new-windsor-ny", floors="", elevator="not stated", dogs="unknown", weight_limit="", verdict="no_availability: page has no units, prices or policies", source_url=Z + "p71102/squire-village-properties-new-windsor-ny", notes="")
B(name="Country Club Apartments", address="19 Anthony Dr", town="Poughkeepsie (12601)", url=Z + "p1288354/country-club-apartments-poughkeepsie-ny", floors="", elevator="not listed", dogs="yes", weight_limit="not_stated", verdict="out_of_grid: ZIP 12601 is not in search_grid.csv", source_url=Z + "p1288354/country-club-apartments-poughkeepsie-ny", notes="Studio 1,850, 1BR 2,225 listed.")
B(name="Fulton Landing", address="10 Campus View Ct", town="Poughkeepsie (12601)", url=Z + "p668907/fulton-landing-poughkeepsie-ny", floors="", elevator="not listed (two-story lobby)", dogs="yes (limit 1)", weight_limit="not_stated", verdict="out_of_grid: ZIP 12601 is not in search_grid.csv", source_url=Z + "p668907/fulton-landing-poughkeepsie-ny", notes="1BR 2,258-2,363 listed. United Group of Companies.")
B(name="249 Main St (condominium)", address="249 Main St", town="Beacon", url="https://www.apartmentlist.com/ny/beacon/249-main-street-unit-301", floors="", elevator="unknown", dogs="unknown", weight_limit="", verdict="unknown: condo building; the Apartment List unit page returned no content; no building leasing page", source_url="https://www.apartmentlist.com/ny/beacon/249-main-street-unit-301", notes="Individual condo rentals only.")

# small buildings seen on Zillow search pages: no elevator, no pet policy on the building page
ZL = "https://www.zillow.com"
for name, town, path, what in [
    ("3 Fishkill Glen Dr", "Fishkill", "/b/3-fishkill-glen-dr-fishkill-ny-5XszFt/", "2BR only"),
    ("122 Murray Ave", "Goshen", "/b/122-murray-ave-goshen-ny-97XZx8/", "1BR 2,200 now; built 1911"),
    ("25 Gloria Trl", "Monroe", "/b/25-gloria-trl-monroe-ny-CrSbV9/", "price on page is a sale price"),
    ("530 State Route 32", "Highland Mills", "/b/530-state-route-32-highland-mills-ny-97XhgG/", "studio 1,500, 1BR 1,700 now"),
    ("534 State Route 32", "Highland Mills", "/b/534-state-route-32-highland-mills-ny-97XhgL/", "studio 1,850, 1BR 2,100 now; built 1900, above a deli"),
    ("17 Prospect St", "Highland Falls", "/b/17-prospect-st-highland-falls-ny-5YGYdx/", "1BR 2,900 now"),
    ("1600 Route 9", "Garrison", "/b/1600-route-9-garrison-ny-97VVLk/", "1BRs 2,300 now; built 2016"),
    ("31 Spring St", "Newburgh", "/b/31-spring-st-newburgh-ny-5vYmWx/", "1BR 1,700 now"),
    ("152 3rd St", "Newburgh", "/b/152-3rd-st-newburgh-ny-97xM9B/", "1BR 1,950 now"),
    ("222 Broadway", "Newburgh", "/b/222-broadway-newburgh-ny-97xNGX/", "1BRs 1,500 now"),
    ("9 Lattintown Rd", "Newburgh", "/b/9-lattintown-rd-newburgh-ny-97xSFh/", "1BR 1,750 now"),
    ("364 North St", "Middletown", "/b/364-north-st-middletown-ny-5j9CHS/", "1BRs 1,475 now"),
    ("11 Maple Ave", "Patterson", "/b/11-maple-ave-patterson-ny-97xYy9/", "1BRs 1,775-1,875 now"),
    ("77 Randall St", "Florida", "/b/77-randall-st-florida-ny-97XYXH/", "1BRs 1,800 now"),
]:
    B(name=name, address=name, town=town, url=ZL + path, floors="", elevator="not listed", dogs="unknown", weight_limit="",
      verdict="unknown: small building; page lists no elevator and no pet policy (" + what + ")", source_url=ZL + path, notes="Not an elevator-building candidate; no unit row written.")

print("listing rows:", C.upsert(H.OUT, rows))
for b in bl:
    n = H.bldg_upsert(b)
print("buildings:", n)

# ---- updates to existing rows / buildings from own-site reads
def patch_rows(pred, fn):
    rs = list(csv.DictReader(open(H.OUT, newline="")))
    k = 0
    for r in rs:
        if pred(r):
            fn(r); k += 1
    with open(H.OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=C.COLS); w.writeheader(); w.writerows(rs)
    return k
def add_note(r, text):
    if text not in r["notes"]:
        r["notes"] = (r["notes"] + " " + text).strip()
def hamlet(r):
    r["notes"] = ("BUILDING_FAILS: income-restricted housing. Own site https://www.thehamletatcarmel.com/ lists rents by household income "
                  "(1BR $675 at 30% AMI, $1,586 at 60% AMI) with maximum household income limits (1 person $59,340 at 60% AMI). "
                  "Dog limit 25 lb (Zillow page) would pass the 25 lb gate. Elevator not stated on the own site.")
print("hamlet", patch_rows(lambda r: r["building_name"] == "The Hamlet at Carmel", hamlet))
def park(r):
    add_note(r, "Own site https://www.theparkatmain.com/amenities/ confirms Elevator, Pool (not stated indoor), gym, community parking, tenant storage, in-unit washer & dryer, electric heating; floorplans page: 1BR 'Starting at $2400' (775 and 898 sq ft). Managed via AMI Management (amimgt.com link on site).")
    if not r["manager"]:
        r["manager"] = "AMI Management (site link); Avery Capital Group"
print("park", patch_rows(lambda r: r["building_name"] == "The Park at Main", park))
def north(r):
    add_note(r, "Own site https://www.northcourtapartments.com/blank: One Bedroom 'Starting at $2,265/Month' 750 sq ft; One Bedroom with Den 'Starting at $2,310' 825 sq ft; washer dryer in unit, ductless AC/heat, 'Parking Available Onsite'; gym, rooftop lounge (48-54 North St, restored building). Zillow unit prices are lower than the site's starting price for some units: confirm whether Zillow shows net-effective rent.")
print("north", patch_rows(lambda r: r["building_name"] == "The North Court Apartments", north))
def beacon445(r):
    add_note(r, "PadMapper address page (https://www.padmapper.com/address/445-main-st-beacon-ny-12508-usa, updated 21 hours before fetch 2026-11-15): studios 2 available $1,900-$2,400, 1BR 1 available $3,000, elevator listed, 'Cats/Dogs Allowed? —' (blank). Dog policy still unpublished: call (844) 338-5721 ext. 3738.")
print("445", patch_rows(lambda r: r["building_name"].startswith("The Beacon (35 Van Nydeck"), beacon445))
def riverbend(r):
    add_note(r, "Zumper building page (updated 15 hours before fetch): only a 2BR at 3,180 listed; dogs allowed limit 2 with breed restrictions, dog fee $60/mo + $500 one-time; billing admin fee $5/mo; built 2007; elevator not in amenities.")
print("riverbend", patch_rows(lambda r: r["building_name"].startswith("RiverBend at Wappingers"), riverbend))

bs = list(csv.DictReader(open(H.BOUT, newline="")))
for b in bs:
    if b["name"] == "The Hamlet at Carmel":
        b["verdict"] = "fails:income-restricted (AMI rent tiers on own site)"; b["notes"] = "Own site https://www.thehamletatcarmel.com/. Dog limit 25 lb (Zillow) would pass the new gate."
    if b["name"] == "The Park at Main":
        b["notes"] = "Own site https://www.theparkatmain.com/ confirms elevator, pool, gym; 1BR starting at 2,400."
    if b["name"] == "The North Court Apartments":
        b["notes"] = "Own site https://www.northcourtapartments.com/ : 1BR starting at 2,265; rooftop, gym."
with open(H.BOUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=H.BCOLS); w.writeheader(); w.writerows(bs)

# ---- elevator-flagged Zumper listings from the leads file (read 2026-11-15)
ZLi = "https://www.zumper.com/listings/"
more = []
more.append(row(ZLi + "25458653p/1-bedroom-pawling-ny", "Pawling Commons", "71 E Main St", "Pawling", "12564", unit="203", beds="1", baths="1", sqft="500",
    listed_rent="2400", price_basis="base rent (Zumper listing; 'Fees may apply')", detail_level="listing_page",
    available_date_text="'Property Status: Active'; 'Now Leasing' (no date given)", available_date="",
    dogs="unknown", dog_weight_limit_lb="40", dog_policy_text="Listing text: 'This is a pet-friendly residence for those with one pet under 40 pounds.' Dogs are not named.",
    elevator="yes", floor="2", building_floors="3", parking_type="'expansive lot' on site (fee not stated)",
    laundry="full-sized stackable washer and dryer in unit; commercial-grade laundry room", manager="broker listing via OneKey MLS",
    notes="Unit 203: floor inferred from unit number (three-story, 15-unit building with 'an elevator, and two staircases'). 'One pet under 40 pounds' implies dogs but does not name them: confirm. Page updated 5 hours before fetch. Village of Pawling, by the Metro-North station. Keyless entry, intercom, cameras, basement storage lockers, bicycle room."))
more.append(row(ZLi + "9145951p/1-bedroom-pawling-ny", "23 E Main St (Pawling)", "23 E Main St", "Pawling", "12564", unit="3A", beds="1", baths="1", sqft="775",
    listed_rent="2000", price_basis="base rent (Zumper listing; 'Fees may apply')", detail_level="listing_page",
    available_date_text="'Property Status: Active'; 'Now leasing' (no date given)", available_date="",
    dogs="unknown", dog_policy_text="No pet policy on the listing.", elevator="yes", floor="4",
    parking_type="'two private offsite parking lots' within walking distance (fee not stated)", laundry="in-unit washer & dryer",
    manager="broker listing via OneKey MLS No. 1057368; office (914) 447-3761",
    notes="DOG_POLICY_UNKNOWN: elevator building, '4th floor apartment' per listing text (unit 3A), newly completed, intercom, sprinklers; pet policy not stated: call. Page updated 5 hours before fetch."))
more.append(row(ZLi + "26603152p/1-bedroom-maybrook-ny", "Bluestone Commons (306 Bluestone Ct)", "306 Bluestone Ct", "Maybrook", "12543", unit="209", beds="1", baths="1", sqft="773",
    listed_rent="2150", price_basis="base rent (Zumper listing)", detail_level="listing_page", concession_text="'Now offering First Month Free - Available for a Limited time.'",
    dogs="unknown", elevator="yes", floor="2", laundry="full-size washer and dryer",
    notes="BUILDING_FAILS: age-restricted. Listing says 'Exclusive 55+ Community' and Zumper flags 'This property has an age requirement'. Second floor with elevator access."))
print("listing rows:", C.upsert(H.OUT, more))
H.bldg_upsert(dict(name="Pawling Commons", address="71 E Main St", town="Pawling", url=ZLi + "25458653p/1-bedroom-pawling-ny", floors="3", elevator="yes", dogs="unknown ('one pet under 40 pounds'; dogs not named)", weight_limit="40", verdict="pass_with_units_pending_dog_policy", source_url=ZLi + "25458653p/1-bedroom-pawling-ny", notes="15 units (1 studio, 2 one-bedroom, 12 two-bedroom). Unit 203 1BR 2,400."))
H.bldg_upsert(dict(name="23 E Main St (Pawling)", address="23 E Main St", town="Pawling", url=ZLi + "9145951p/1-bedroom-pawling-ny", floors="4+ (4th floor unit)", elevator="yes", dogs="unknown", weight_limit="not_stated", verdict="dog_policy_unknown: unit 3A 1BR 2,000, 4th floor", source_url=ZLi + "9145951p/1-bedroom-pawling-ny", notes=""))
print("buildings:", H.bldg_upsert(dict(name="Bluestone Commons (306 Bluestone Ct)", address="306 Bluestone Ct", town="Maybrook", url=ZLi + "26603152p/1-bedroom-maybrook-ny", floors="", elevator="yes", dogs="unknown", weight_limit="", verdict="fails:55+ age-restricted", source_url=ZLi + "26603152p/1-bedroom-maybrook-ny", notes="")))
