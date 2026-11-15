"""Evidence batch 15: build the five CSVs from what was read (no network). Idempotent: rewrites the files.
Inputs: raw/evidence_b15/_index.jsonl (fetch times), _igloo.json (Openigloo), zumper_bld.json, _al_reviews.json,
and the facts below, each of which was read from the cached page named in its source_url."""
import csv, json, re, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
E = ROOT / "raw/evidence_b15"; OUT = ROOT / "data/evidence"; N = 15
TR = "https://www.trulia.com"; AL = "https://www.apartmentlist.com"; AV = "https://www.avaloncommunities.com/new-jersey"
ZU = "https://www.zumper.com/address/"
idx = {}
for l in open(E / "_index.jsonl"):
    x = json.loads(l)
    if x["status"] == 200: idx[x["url"]] = x["retrieved_at"]
    else: idx.setdefault(x["url"], x["retrieved_at"])
def ts(u): return idx.get(u) or idx.get(u.rstrip("/")) or ""
B = {r["addr_key"]: r for r in csv.DictReader(open(ROOT / "data/reference/evidence_batches/batch_15.csv"))}
def name(k): return B[k]["building_name"] or B[k]["address"].replace("  ", " ")
HARV = {}  # harvest copies of the Trulia pages that now answer 403
csv.field_size_limit(10**9)
for r in csv.DictReader(open(ROOT / "data/listings_raw/trulia.csv")): HARV[r["url"]] = r["last_seen"]
MATCH = ROOT / "data/evidence/nyc_records_match.csv"
PL = {r["addr_key"]: r for r in csv.DictReader(open(MATCH))}
IG = json.load(open(E / "_igloo.json"))
live, conf, items, facts, ratings = [], [], [], [], []
def L(k, unit, status, price, avail, match, site, notes, url=None, at=None):
    u = url or B[k]["urls"].split(" | ")[0]
    live.append(dict(addr_key=k, listing_url=u, unit=unit, status=status, price_now=price, available_now_text=avail, matches_stored=match,
                     building_site_url=site, checked_at=at or ts(u), notes=notes))
def C(k, fact, value, quote, src, status): conf.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=src, status=status))
def I(k, cat, date, excerpt, site, url, about="building", at=None):
    items.append(dict(addr_key=k, building_name=name(k), category=cat, item_date=date, excerpt=excerpt, source_site=site, source_url=url, about=about, retrieved_at=at or ts(url) or ""))
def F(k, fact, value, quote, src): facts.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=src))
def R(k, source, val, count, asof, read, last6, neg6, negold, tags, url):
    ratings.append(dict(addr_key=k, building_name=name(k), rating_source=source, rating_value=val, rating_scale=5 if val != "" else "", review_count=count, as_of_date=asof,
                        reviews_read=read, reviews_last_6_months=last6, negative_last_6_months=neg6, negative_older=negold, serious_issue_tags_last_6_months=tags, source_url=url))
def U(k): return B[k]["urls"].split(" | ")[0]
SMALL = "Size-only policy with no pound figure: passes the current gate (a size-only 'small dogs' policy passes); ask for the number."
NEWS = "Web search for the address or building name plus tenants / police / fire / elevator: no article about this address came back"
NO_RATING_NJ = "Zumper address page: no rating block; Apartment List: no building page; Trulia unit page: carries no ratings"

# ---------------------------------------------------------------- Newark, Forest Hill (three Abe Rosen listings)
for k, unit, price, dep, petrent, park, dogq in [
    ("5 beaumont pl|07104", "20B", 1695, "$2,550", "$40/mo", "$75/mo", "Cats, small dogs allowed"),
    ("85 forest hill pkwy|07104", "32D", 1795, "$2,700", "$50/mo", "$100/mo", "Cats, small dogs allowed"),
    ("57 branch brook pl|07104", "30C", 1625, "$2,437", "$40/mo", "$75/mo", "Small dogs allowed")]:
    u = U(k)
    extra = ""
    if k.startswith("5 beaumont"):
        extra = (" Zumper carries the same listing (same text, same $1,695, available 2026/11/12) as '5 Beaumont Pl #2B', so the unit label differs "
                 "between sites (20B on Trulia, 2B on Zumper).")
    L(k, unit, "live", price, "now", "yes", "", f"For Rent at ${price:,}/mo, 'Available: now'. Listed {'2026-11-13' if unit=='32D' else '2026-11-12'}. Price shown is base rent. No building site found (agent listing).{extra}")
    C(k, "elevator", "unconfirmed", "[Trulia feature list has no elevator entry and the description does not mention one]", u, "unconfirmed")
    C(k, "elevator", "my reading: probably no elevator",
      "[Reading, not a page statement: Forest Hill garden-apartment addresses listed by one agent; unit codes of the form number+letter; no lift in any feature list. The batch file's 'elevator inferred from height' appears to rest on the unit number, which is not a floor count.]", u, "unconfirmed")
    fl = {"20B": "2", "32D": "3", "30C": "3"}[unit]
    C(k, "floor", "unconfirmed",
      f"[No page states the floor. My reading: floor {fl}, if the first digit of {unit} is the floor, as it is in the same kind of listing at 330 50th St, West New York, where unit 43L is stated to be on the fourth floor."
      + (" Zumper labels this unit 2B.]" if unit == "20B" else "]"), u, "unconfirmed")
    C(k, "dogs_allowed", "yes", dogq, u, "confirmed")
    C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
    F(k, "dog_policy_gate_note", "passes on size-only wording", SMALL, u)
    F(k, "pet_rent", petrent, f"Optional monthly rent & fees: Pet rent {petrent}", u)
    F(k, "parking", f"off-street, on site; {park}", f"Parking: Off Street Parking, On Site / Parking fee {park}", u)
    F(k, "deposit_and_fees", f"security deposit {dep}; application fee $50" + ("; pet fee $500" if unit == "32D" else ""), f"Security deposit {dep}; Application fee $50", u)
    F(k, "listing_agent", "Abe rosen (individual agent; no management company named)", "listingAgent: Abe rosen", u)
    if unit != "32D": F(k, "utilities", "heat and water included" if unit == "20B" else "central air and central heat; laundry in building", "Heat and water are included in the rent" if unit == "20B" else "Central air conditioning and central heat provide year-round comfort, while laundry in the building adds everyday convenience.", u)
    I(k, "none_found", "", f"{NEWS}. Zumper address page {'(listing only)' if unit=='20B' else '(404)'}; no Apartment List page; no Openigloo (not NYC).", "search", u, at=ts(u))
    R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", NO_RATING_NJ.replace("no rating block", "no rating block" if unit == "20B" else "404"))

# ---------------------------------------------------------------- 800 S 14th St, Newark
k = "800 s 14th st|07108"; u = U(k)
L(k, "6D", "live", 1594, "now", "yes", "", "For Rent at $1,594/mo, 'Available: now'. Listed 2026-11-03 (12 days on Trulia). The description is Trulia's boilerplate only (address, 1 bed, about 600 sqft): the lister wrote nothing about the building. No building site found.")
C(k, "elevator", "unconfirmed", "[No elevator entry in the feature list; the description is boilerplate]", u, "unconfirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. Unit 6D could mean floor 6 or apartment 6 on line D; nothing on the page settles it.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed")
C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "parking", "off-street, on site; fee not stated", "Parking: Off Street Parking, On Site", u)
F(k, "deposit_and_fees", "security deposit $2,392; application fee $0", "Security deposit $2,392; Application fee $0", u)
F(k, "listing_agent", "Rachel (broker name as shown; no management company named)", "broker: Rachel", u)
I(k, "none_found", "", f"{NEWS}. Zumper address page 404; no Apartment List page.", "search", u, at=ts(u))
R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", NO_RATING_NJ.replace("no rating block", "404"))

# ---------------------------------------------------------------- Hoyt Tower
k = "50 sussex ave|07103"; u = U(k); JD = "https://jerseydigs.com/buildings/hoyt-tower/"; YI = "https://newyorkyimby.com/2024/12/hoyt-tower-completes-construction-at-50-sussex-avenue-in-newark-new-jersey.html"
L(k, "711", "live", 2420, "Available Now", "yes", "", "Unit 711, 1 bed, 691 sqft, $2,420/mo, 'Available Now' (no date attached, unlike the other units, which carry 2026-10-16). 7 units listed of 203. Trulia page last modified 2026-10-16, a month ago: confirm by phone. Other 1-beds: 1305 $2,510; 507 $2,525; 701 $2,600; 1301 $2,620. hoyttower.com does not belong to this building (it redirects to an unrelated company), so no own site was read.")
C(k, "elevator", "unconfirmed (15-story tower, so one is implied)", "Spanning 15 stories, the building offers 203 units", u, "unconfirmed")
C(k, "elevator", "15 floors, opened 2024", "Hoyt Tower is a 15-story, 203-unit luxury rental high-rise at 50-54 Sussex Avenue", JD, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. My reading: floor 7, from the unit number 711 in a 15-story building whose listed units run 507 to 1305.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Hoyt Tower in Newark, NJ allows cats (up to 1) and small dogs (up to 1). Large dogs are not permitted.", u, "confirmed")
C(k, "dog_weight_limit", "small dogs only, 1 pet; no pound figure", "Dogs: Allowed; Number allowed: 1; Size allowed: Small", u, "confirmed")
F(k, "pet_fees", "pet rent $50/month; pet deposit $400", "Pet rent ($50) / Pet deposit ($400)", u)
F(k, "parking", "16-space garage for 203 units", "the structure yields 203 units, 2,000 square feet of ground-floor retail space, and a 16-space parking garage", YI)
F(k, "building", "15 stories, 203 units, opened 2024; developed by KS Group and Tona", "Year opened 2024 Total units 203 Floors 15", JD)
F(k, "doorman", "concierge and attended lobby (per Jersey Digs); Trulia lists 'Night Patrol' and 'Controlled access'", "Concierge Doorman / attended lobby Package lockers Parking (on-site) Pet-friendly", JD)
F(k, "pool", "none listed (fitness center, sauna, lounge)", "Fitness Center, Lounge, Night Patrol, Controlled access, Sauna", u)
F(k, "management_company", "not named on the pages read", "[Trulia shows a verified leasing phone only: (201) 482-7762]", u)
I(k, "none_found", "", f"{NEWS} (only construction and opening coverage: Jersey Digs, New York YIMBY). Zumper address page: old 2024 listing, no reviews. Apartment List building page not read.", "search", JD)
R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", "Zumper address page (no rating block): " + ZU + "50-sussex-ave-newark-nj-07103-usa; Trulia building page carries no ratings")

# ---------------------------------------------------------------- 8300 Boulevard East (Woodcliff Gardens co-op)
k = "8300 jfk blvd e|07047"; u = U(k)
L(k, "4D", "live", 1474, "available 2026-11-14 (available now)", "yes", "", "Unit 4D, 1 bed, 610 sqft, $1,474, 12-month lease; unit record updated 2026-11-14. This is a single co-op unit in Woodcliff Gardens offered by an individual lister, not a managed rental: a co-op board normally has to approve a tenant and sets the pet rules. The price is low for the description (river and skyline views); verify the listing before relying on it. No building site found.")
C(k, "elevator", "yes", "Woodcliff Gardens is a well-maintained elevator building with landscaped grounds, swimming pool, and on-site laundry.", u, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. My reading: floor 4, from unit 4D in an elevator co-op.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes (listing tag only)", "Cats allowed, Dogs allowed, Pet friendly", u, "unconfirmed")
C(k, "dog_weight_limit", "unconfirmed", "[Apartment List shows 'allowed' with every limit, fee and restriction field empty. The co-op's own pet rules were not found.]", u, "unconfirmed")
F(k, "building", "Woodcliff Gardens, a co-op complex across from North Hudson (Braddock) Park", "This oversized 1 bedroom co-op offers a front-row seat to the Hudson River and Manhattan skyline", u)
F(k, "parking", "surface lot; fee not stated", "parking category: surface_lot", u)
F(k, "pool", "yes, outdoor (complex pool)", "landscaped grounds, swimming pool, and on-site laundry", u)
F(k, "deposit", "$1,474", "deposit_fee_text: 1474.00", u)
I(k, "none_found", "", f"{NEWS}. Apartment List page says it is still collecting reviews. Zumper address page 404.", "search", u)
R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", "Apartment List building page (collecting reviews): " + u + "; Zumper address page 404")

# ---------------------------------------------------------------- Presidential Estates
k = "500 adams ln|08902"; u = U(k)
L(k, "19F", "live", 2195, "Available Now (2026-11-13)", "yes", "", "Unit 19F ('Bachelor' plan, 1 bed, 947 sqft) $2,195/mo, Available Now. 5 units listed of 256. Trulia page last modified 2026-09-11, two months ago, although the unit dates read 2026-11-13. OFFER (verbatim): 'APPLY NOW AND GET ONE MONTH FREE / APPLICATION WITHIN 24HRS OF TOUR RECIEVE $250 STATEMENT CREDIT', 'Offer good until November 30, 2026'. The page does not say whether $2,195 is gross or net-effective. The building's own site is reached only through a Zillow redirect and was not fetched.")
C(k, "elevator", "unconfirmed", "[No elevator in the feature list: Business Center, Club House, Fitness Center, Lounge, 24 hour maintenance, Lawn, Parking Lot]", u, "unconfirmed")
C(k, "elevator", "my reading: no elevator", "[Reading: a 256-unit garden complex with a parking lot, lawns, a clubhouse and a '2 Bedroom - Duplex - Townhouse' plan; unit numbers are building+letter (19F, 6G, 20B, 2K, 2A). Nothing suggests a lift.]", u, "unconfirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. '19F' reads as building 19, apartment F; the floor cannot be read from it.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Presidential Estates in North Brunswick, NJ allows cats (up to 1) and small dogs (up to 1). Large dogs are not permitted.", u, "confirmed")
C(k, "dog_weight_limit", "small dogs only, 1 pet; no pound figure", "Dogs: Allowed; Number allowed: 1; Size allowed: Small", u, "confirmed")
F(k, "special_offer", "one month free plus $250 credit; gross or net not stated", "APPLY NOW AND GET ONE MONTH FREE / APPLICATION WITHIN 24HRS OF TOUR RECIEVE $250 STATEMENT CREDIT (Offer good until November 30, 2026)", u)
F(k, "pet_fees", "pet rent $40/month; pet deposit $500", "Pet rent ($40) / Pet deposit ($500)", u)
F(k, "parking", "lot; one assigned space per unit, no fee stated", "One assigned parking space per unit. Additional cars are first come first served.", u)
F(k, "pool", "none listed", "Business Center, Club House, Fitness Center, Lounge", u)
F(k, "other", "monthly pest control service; on-site super", "Monthly pest control service", u)
I(k, "none_found", "", f"{NEWS}. Zumper address page: one listing, no rating. No Apartment List building page read.", "search", u)
R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", "Zumper address page (no rating block): " + ZU + "500-adams-ln-north-brunswick-nj-08902-usa; Trulia building page carries no ratings. (A search result mentioned a Google rating; Google is off limits and the figure was not read from a page.)")

# ---------------------------------------------------------------- 99 Bridge
k = "99 old amboy rd|08857"; u = U(k); z = ZU + "99-old-amboy-rd-old-bridge-nj-08857-usa"
L(k, "232", "live", 2635, "available 2026-12-05", "yes", "https://www.rent99bridge.com/", "Unit 232 (plan A5, 758 sqft) base $2,635; Apartment List shows total $2,689 with $54 of required monthly fees, on a 15-month lease. Available 2026-12-05: inside the window by 10 days. Unit 231 (same plan) is 2027-01-05. OFFER (verbatim): 'Now Offering 1 Month Free on Select Apartments! *Prices and promotions may vary and are subject to change at any time, and exceptions may apply. Please contact the leasing center for full details.' Not stated whether the price is gross or net. Own site rent99bridge.com answers 403 (bot wall): not read.")
C(k, "elevator", "yes (Apartment List amenity tag only)", "Elevator", u, "unconfirmed")
C(k, "floor", "unconfirmed", "[No page states the floor; the own site is blocked. My reading: floor 2, from unit 232 (units listed run 1xx to 3xx).]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Dogs allowed; pet rent $50/month; fee $500", u, "confirmed")
C(k, "dog_weight_limit", "no restriction shown (Zumper: 'Restrictions: None'); no pound figure", "dog: | Restrictions: None", z, "unconfirmed")
F(k, "required_fees", "$54/month on top of base rent", "base_price 2635; required_fees 54; total_price 2689", u)
F(k, "pet_fees", "pet rent $50/month; one-time fee $500", "rent: $50/month; fee: $500", u)
F(k, "parking", "surface; Apartment List says $25/month, Zumper says first space included and second $25/month", "Parking Fees- Surface (1st Space Included,2nd Space $25/month)", z)
F(k, "management_company", "BNE Real Estate Group", "pm: BNE Real Estate Group LLC", z)
F(k, "building", "150 units; pool, dog park", "total_units_count 150; Dog park; Pool", u)
F(k, "lease_and_deposit", "leases 3-15 months; deposit $1,000 to 1.5x base rent; application $50", "3-15 months / $1,000- 1.5x Month Base Rent / $50", u)
for d, t in [("2024-05-31", "Very dog friendly place. Very lucky that the neighboring  apartments are occupied by nice people ."),
             ("2024-05-25", "Joe the maintenance man was amazing and very helpful with fixing my AC outside of regular hours. I appreciate his promptness!"),
             ("2023-08-22", "When you put in a request for maintenance Joe is either there that day or early the next day to fix the issue.")]:
    I(k, "positive", d, t, "Google review shown on Zumper", z)
R(k, "Google rating shown on Zumper", 4.4, 41, "2024-10-31", 8, 0, 0, 0, "", z)
R(k, "Apartment List", "", "", "2026-11-15", 0, "", "", "", "", u + " (page says it is still collecting reviews)")

# ---------------------------------------------------------------- Avalon Princeton on Harrison
k = "275 n harrison st|08540"; u = U(k); o = AV + "/princeton-apartments/avalon-princeton-on-harrison/"; ou = o + "apartment/NJ035-NJ035-001-431"; z = ZU + "275-n-harrison-st-princeton-nj-08540-usa"
L(k, "431", "live", 2571, "available 2026-11-21", "yes", o, "NET-EFFECTIVE PRICE. AvalonBay's own unit data for 431, 12-month lease, move-in 2026-11-21: price $2,805, total $2,901 (with the required $96 Technology Connect fee), netEffectivePrice $2,571, total net effective $2,667. So the stored $2,571 is the rent after spreading one free month; the monthly rent on the lease is $2,805, or $2,901 with the required fee. OFFER (verbatim): 'Advertised rates include 1 month off! Advertised rate on select homes is discounted and includes 1 month off when you apply by 11-30-2026. Terms and conditions apply. This offer is valid on lease terms of 12 months or longer. No on-site transfers.' Apartment List shows the same $2,571 and date. Studio, 725 sqft, with loft.", at=ts(ou))
C(k, "elevator", "yes (Apartment List amenity tag only)", "Elevator", u, "unconfirmed")
C(k, "elevator", "not listed on AvalonBay's own pages", "[The 21 community features and the unit's 14 features on avaloncommunities.com do not include an elevator]", ou, "unconfirmed")
C(k, "floor", "4", '"unitName":"431" ... "floorNumber":"4"', o, "confirmed")
C(k, "dogs_allowed", "yes", "Dog $60 / mo. ... Dog $500 (one-time charge)", ou, "confirmed")
C(k, "dog_weight_limit", "unconfirmed (breed list only)", "The following breeds are restricted: Akitas, Alaskan Malamutes, American Bull Dogs, American Staffordshire Terriers ... [no weight figure on the pages read]", ou, "unconfirmed")
F(k, "price_basis", "stored price is net-effective; gross $2,805; with required fee $2,901", "term 12: price 2805, totalPrice 2901, netEffectivePrice 2571, totalNetEffectivePrice 2667", ou)
F(k, "special_offer", "1 month off, already inside the advertised rate; apply by 2026-11-30; 12 months or longer", "Advertised rates include 1 month off! Advertised rate on select homes is discounted and includes 1 month off when you apply by 11-30-2026.", ou)
F(k, "required_fees", "Technology Connect $96/month; amenities fee $650 at move-in and at renewal; application $50 per person; deposit $750", "Required Monthly Base Rent Technology Connect $96 / mo. Required One-Time Application Fees $50 / person Common Area/Amenities $650 (move-in) Security Deposit $750 (refundable)", ou)
F(k, "pet_fees", "dog rent $60/month; $500 one-time", "Dog $60 / mo. ... Dog $500 (one-time charge)", ou)
F(k, "parking", "garage, unassigned, $50-$150/month", "Unassigned parking will be available in our garage for a monthly fee. / Parking $50-$150 / mo.", ou)
F(k, "utilities", "resident pays electric, gas, trash, water", "Electric Resident Gas Resident Trash Resident Water Resident Sewer N/A", ou)
F(k, "pool", "yes, outdoor (elevated pool with sundeck)", "Elevated Pool with Sundeck", o)
F(k, "management_company", "AvalonBay Communities (owner-manager); new building, leased up from early 2025", "communityId AVB-NJ035", ou)
I(k, "other", "2025-01-17", "Drove a half hour to be there for 2pm and the office was closed. By 2:40pm, still no office personnel.", "Google review shown on Zumper", z, "management_company")
I(k, "positive", "2025-01-26", "The leasing/community staff are reliable and their customer service is top notch!", "Google review shown on Zumper", z, "management_company")
I(k, "other", "2025-04-06", "Things are still in construction that I hoped would be ready by now, mail is somewhat unpredictable in terms of deliveries being left all over the place, but overall I’m happy all things considered.", "Apartment List", u)
R(k, "Google rating shown on Zumper", 4.4, 7, "2025-02-07", 7, 0, 0, 1, "", z)
R(k, "Apartment List", 4, 1, "2026-11-15", 1, 0, 0, 0, "", u)

# ---------------------------------------------------------------- Rahway, 1423 Irving St #1210 (SkyView)
k = "1423 irving st|07065"; u = U(k)
L(k, "1210", "live", 2200, "Nov 18th", "yes", "", "For Rent at $2,200/mo, 'Available: Nov 18th'. 'Decreased by $50 (2%) on Nov 4, 2026'. Listed 2026-10-31. A condo in the SkyView tower rented by the unit's owner, with screening through Zillow; 1.5 months' deposit ($3,000). No building site read.")
C(k, "elevator", "unconfirmed (12th-floor unit, so one is implied)", "SKYVIEW Luxury Condo - The nice overlooking condo on 12th floor", u, "unconfirmed")
C(k, "floor", "12", "The nice overlooking condo on 12th floor", u, "confirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed")
C(k, "dog_weight_limit", "small dogs only; no pound figure (the condo association's own rule was not found)", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "parking", "one covered garage space, described as separate", "- 1 Car Covered Parking (separate) ... - Secure covered parking available.", u)
F(k, "deposit", "$3,000 (1.5 months)", "Require 1.5-month security deposit and long-term lease ( minimum 1 year).", u)
F(k, "landlord", "individual unit owner", "Rented directly by the owner of the unit, Flexible/accommodating for tenant needs.", u)
F(k, "amenities", "rooftop with BBQ, gym; in-unit laundry", "- Rooftop access, grand view and access to BBQ / - Gym and other aminities onsite", u)
I(k, "none_found", "", f"{NEWS} (results were sale and rental listings for SkyView at 1 Carriage City Plaza). Zumper address page 404.", "search", u)
R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", NO_RATING_NJ.replace("no rating block", "404"))

# ---------------------------------------------------------------- Grandville Towers
k = "19 morford pl|07701"; u = U(k)
GN = ("Apartment List's unit records for this building were last updated 2026-07-30 and show 'available_on' 2026-07-29, although the building page itself was updated 2026-11-15: the unit rows may be stale. "
      "OFFERS (verbatim): 'Receive Half Off First Month's Rent! Contact our leasing office for more details! Available for limited time. Terms & Conditions Apply.' and 'Receive HALF OFF FIRST MONTH'S RENT on available units. Special applies only for new residents. Please reach out to our leasing office for more details.' "
      "Not stated whether the price is gross or net; total_price equals base_price. Own site grandvilletowers.com answers 403 (bot wall): not read.")
L(k, "5F", "live", 2660, "available (since 2026-07-29)", "yes", "https://www.grandvilletowers.com/", "Unit 5F (Shrewsbury, 800 sqft) $2,660, 12-month lease. " + GN)
L(k, "7C", "live", 2600, "available (since 2026-07-29)", "yes", "https://www.grandvilletowers.com/", "Unit 7C (Sandy Hook, 680 sqft) $2,600, 12-month lease. " + GN)
C(k, "elevator", "yes (Apartment List amenity tag only)", "Elevator", u, "unconfirmed")
C(k, "floor", "unconfirmed", "[No page states the floors; own site blocked. My reading: 5F on floor 5 and 7C on floor 7, from the unit numbers (listed units run 5F to 9C).]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "dogs: rent 55, limit 2, fee 250, restrictions: see list", u, "confirmed")
C(k, "dog_weight_limit", "unconfirmed ('see list')", "restrictions: see list [the list itself is not on the page; no pound figure]", u, "unconfirmed")
F(k, "special_offer", "half off the first month; gross or net not stated", "Receive Half Off First Month's Rent! Contact our leasing office for more details! Available for limited time. Terms & Conditions Apply.", u)
F(k, "pet_fees", "pet rent $55/month; $250 one-time; 2 pets", "rent $55; limit 2; fee $250", u)
F(k, "required_fees", "water fee $40/month for a 1-bedroom; trash included", "Water fee: $40 for 1-bedroom, $60 for 2-bedroom", u)
F(k, "parking", "surface lot; fee not stated", "parking category: surface_lot", u)
F(k, "building", "96 units, built 1969; pool", "total_units_count 96; year_built 1969; Pool", u)
I(k, "none_found", "", f"{NEWS} in the last two years (search results pointed to older Red Bank Green pieces on a rent-board award and a condo-conversion plan; not read). Apartment List: still collecting reviews. Zumper address page 404.", "search", u)
R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", "Apartment List building page (collecting reviews): " + u + "; Zumper address page 404; own site 403")

# ---------------------------------------------------------------- Avalon Somerville Station
k = "22 robeson st|08876"; u = U(k); o = AV + "/somerville-apartments/avalon-somerville-station/"; ou = o + "apartment/NJ033-NJ033-022-265"; z = ZU + "22-robeson-st-somerville-nj-08876-usa"
L(k, "022-265", "live", 2340, "available 2026-11-16", "yes", o, "$2,340 IS THE 20-MONTH LEASE PRICE. AvalonBay's own unit data for 265 (studio, 856 sqft, North Building), move-in 2026-11-16: 12-month price $2,430 ($2,519 with the required $89 Technology Connect fee); 13-month $2,425; 20-month $2,340, the lowest of any term, which is what the community page and Apartment List advertise. Net-effective equals price on every term, so no free month is folded in. OFFERS (verbatim): 'Apply by 11-16 for 1.5 months off! Get 1.5 months off on select homes when you apply by 11-16-2026. Terms and conditions apply. This offer is valid on lease terms of 12 months or longer. No on-site transfers.' and '$150 deposit when you apply by 11-30! $150 security deposit (on approved credit) on select homes when you apply by 11-30-2026.' The 1.5-months offer expires the day after this check.", at=ts(ou))
C(k, "elevator", "yes (Apartment List amenity tag only)", "Elevator", u, "unconfirmed")
C(k, "elevator", "not listed on AvalonBay's own pages", "[Community features on avaloncommunities.com do not include an elevator]", ou, "unconfirmed")
C(k, "floor", "2", "Floor 2", ou, "confirmed")
C(k, "floor", "2", '"unitName":"265" ... "floorNumber":"2"', o, "confirmed")
C(k, "dogs_allowed", "yes", "Dog $60 / mo. ... Dog $500 (one-time charge)", ou, "confirmed")
C(k, "dog_weight_limit", "no weight limit in the site's policy data (maximumPetWeight 0, 2 pets, breed list); not stated in words", '"maximumPets": 2, "maximumPetWeight": 0 / The following breeds are restricted: Akitas, Alaskan Malamutes, American Bull Dogs ...', ou, "unconfirmed")
F(k, "price_basis", "$2,340 is the 20-month price; 12-month $2,430; with required fee $2,519; gross (net-effective equals price)", "term 12: price 2430, totalPrice 2519, netEffectivePrice 2430; term 20: price 2340", ou)
F(k, "special_offer", "1.5 months off if applied by 2026-11-16; $150 deposit if applied by 2026-11-30; not folded into the price", "Apply by 11-16 for 1.5 months off! Get 1.5 months off on select homes when you apply by 11-16-2026.", ou)
F(k, "required_fees", "Technology Connect $89/month; amenities fee $600 at move-in and renewal; application $50 per person; deposit $750", "Required Monthly Base Rent Technology Connect $89 / mo. Required One-Time Application Fees $50 / person Common Area/Amenities $600 (move-in) Security Deposit $750 (refundable)", ou)
F(k, "pet_fees", "dog rent $60/month per pet; $500 one-time; 2 pets", "Dog $60 / mo. ... Dog $500 (one-time charge)", ou)
F(k, "parking", "assigned garage space for the first car, $65-$140/month", "We offer assigned garage parking (1st vehicle) for an additional monthly fee. / Parking $65-$140 / mo.", ou)
F(k, "utilities", "resident pays electric, gas, trash, water, sewer", "Electric Resident Gas Resident Trash Resident Water Resident Sewer Resident", ou)
F(k, "pool", "yes, outdoor", "Pool with sundeck, cabanas, and outdoor lounging area", o)
F(k, "building", "374 units, built 2022; AvalonBay owner-manager", "total_units_count 374; year_built 2022", u)
I(k, "positive", "2025-02-04", "We have lived at the Avalon for over 2 years. The location to downtown is unbeatable and amenities (the fantastic pool) made it hard to leave", "Google review shown on Zumper", z)
I(k, "positive", "2024-08-26", "Eddie is always prompt, courteous, and professional whenever I have a maintenance issue.", "Google review shown on Zumper", z, "management_company")
I(k, "other", "2024-10-17", "Very nice spot with accommodating staff. Extra charges for all bells and whistles but safety and quality is high.", "Apartment List", u)
R(k, "Google rating shown on Zumper", 4.2, 100, "2025-02-06", 8, 0, 0, 0, "", z)
R(k, "Apartment List", 5, 1, "2026-11-15", 1, 0, 0, 0, "", u)

# ---------------------------------------------------------------- The Edge at Main
k = "125 w main st|08876"; u = U(k); o = "https://www.theedgeatmain.com/"; oa = o + "about-the-edge-at-main/"; ob = o + "our-brand-new-building-2/"
EN = "DOGS: the building's own site calls it a 'Pet-free community'; pets are taken only in a set of ground-floor homes in the new building. Apartment List tags it 'Dogs allowed'. See the confirm file. Own site shows plans but no unit prices (leasing runs through a RealPage portal, not fetched)."
L(k, "327", "live", 2739, "available now", "yes", o, "Unit 327 (plan A3, 928 sqft) $2,739, 12-month lease, available now; unit record updated 2026-11-15. " + EN)
L(k, "328", "live", 2774, "available now", "yes", o, "Unit 328 (plan A5, 956 sqft) $2,774, 12-month lease, available now (Apartment List shows it available since 2025-07-22, 16 months); unit record updated 2026-11-15. " + EN)
C(k, "elevator", "yes", "Elevator access", oa, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floors. My reading: floor 3 for both, from unit numbers 327 and 328 (listed units run 1xx to 4xx).]", u, "unconfirmed")
C(k, "dogs_allowed", "no for these units: 'Pet-free community'", "Smoke-free community Pet-free community", oa, "contradicts")
C(k, "dogs_allowed", "pets only in ground-floor homes of the new building (plans B4-W, C2-W)", "An exclusive collection pet-friendly, ground-floor homes along S. Doughty Ave offer direct entrances, double-height ceilings and loft spaces.", ob, "contradicts")
C(k, "dogs_allowed", "yes (Apartment List tag)", "Cats allowed, Dogs allowed", u, "contradicts")
C(k, "dog_weight_limit", "not applicable to these units; no figure anywhere", "[Apartment List pet fields are all empty]", u, "unconfirmed")
F(k, "listing_trouble", "contradictory dog policy between the building's site and Apartment List", "Pet-free community", oa)
F(k, "parking", "surface, unassigned, residents only; no fee stated", "Designated surface parking for residents (no assigned spots)", oa)
F(k, "doorman", "concierge service", "Concierge service keep you connected to the community / Package acceptance", oa)
F(k, "management_company", "Edgewood Properties (developer and manager)", "Edgewood Properties® is a leading real estate development and property management company", oa)
F(k, "building", "261 units, built 2024 (Apartment List); two buildings; no pool listed", "total_units_count 261; year_built 2024", u)
I(k, "none_found", "", f"{NEWS}. Apartment List: still collecting reviews. Zumper address page has no rating.", "search", u)
R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", "Apartment List building page (collecting reviews): " + u + "; Zumper address page (no rating block): " + ZU + "125-w-main-st-somerville-nj-08876-usa; own site has no review widget")

# ---------------------------------------------------------------- Union City and West New York broker listings
for k, unit, price, listed, agent, extras in [
    ("137-148 36th st|07087", "26W", 1695, "2026-11-12", "Real Broker (Jose Francisco Inoa)", dict(dep="$2,542", app="$0", util="Heat and hot water are included.", park=None)),
    ("6122 monroe pl|07093", "17R", 1795, "2026-10-20", "Parkstone Agent", dict(dep="$2,693", app="$50", util="*Hot water included", park="*Street parking only")),
    ("5801 palisade ave|07093", "15C", 1795, "2026-10-29", "Santana (Liz Santana)", dict(dep="Contact for details", app="$40 on the fee table, $50 in the description", util="INCLUDING HEAT AND HOT WATER IN THE RENT!", park=None)),
    ("5008 palisade ave|07093", "24B", 1795, "2026-10-29", "Santana (Liz Santana)", dict(dep="Contact for details", app="$50", util="INCLUDING HEAT AND HOT WATER IN THE RENT!", park=None))]:
    u = U(k); fl = unit[0]
    note = f"For Rent at ${price:,}/mo, 'Available: now'. Listed {listed}. Broker listing; no building site."
    if unit == "26W": note += " The description gives the address as '137-147 36th St'. The broker's text also advertises other 'on-market and off-market' apartments."
    if unit == "17R": note += " 26 days on Trulia."
    L(k, unit, "live", price, "now", "yes", "", note)
    C(k, "elevator", "unconfirmed", "[No elevator in the feature list or the description]", u, "unconfirmed")
    C(k, "elevator", "my reading: probably a walk-up", "[Reading: an older Hudson County block listed by a broker with no lift mentioned; the same kind of listing at 330 50th St, West New York (unit 43L) states 'Fourth-Floor Walk-Up'.]", u, "unconfirmed")
    C(k, "floor", "unconfirmed", f"[No page states the floor. My reading: floor {fl}, if the first digit of {unit} is the floor, as at 330 50th St where 43L is on the fourth floor." + (" Floor 1 would be ground level.]" if fl == "1" else "]"), u, "unconfirmed")
    C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed")
    q = {"17R": "*Small dogs and cats only / *$250 one-time pet fee", "15C": "-Small pets allowed", "24B": "-Small pets allowed", "26W": "Dogs: Allowed; Size allowed: Small"}[unit]
    C(k, "dog_weight_limit", "small dogs only; no pound figure", q, u, "confirmed")
    F(k, "deposit_and_fees", f"security deposit {extras['dep']}; application fee {extras['app']}" + ("; pet fee $250 one-time" if unit == "17R" else ""), f"Security deposit {extras['dep']}", u)
    F(k, "utilities", "heat and hot water included" if unit != "17R" else "hot water included", extras["util"], u)
    if extras["park"]: F(k, "parking", "street parking only", extras["park"], u)
    if unit == "17R": F(k, "laundry", "not in the building", "*Laundry available in a nearby building", u)
    F(k, "listing_agent", agent + "; no management company named", "provider: " + agent, u)
    zz = {"5801 palisade ave|07093": "Zumper address page: old listings only, no rating", "5008 palisade ave|07093": "Zumper address page: no rating"}.get(k, "Zumper address page 404")
    I(k, "none_found", "", f"{NEWS}. {zz}. No Apartment List building page.", "search", u, at=ts(u))
    R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", zz + "; Apartment List: no building page; Trulia unit page carries no ratings")

k = "330 50th st|07093"; u = U(k); z = ZU + "330-50th-st-west-new-york-nj-07093-usa"
L(k, "43L", "live", 1795, "now", "yes", "", "For Rent at $1,795/mo, 'Available: now'. Listed 2026-10-26. FAILS THE ELEVATOR GATE: the listing says 'Fourth-Floor Walk-Up'. It also says 'pets case by case' in the terms while the feature table says small dogs allowed.")
C(k, "elevator", "no: fourth-floor walk-up", "Located on the fourth floor of a walk-up building, this apartment is an excellent option for anyone seeking a spacious home", u, "contradicts")
C(k, "elevator", "no (earlier listings at this address say the same)", "Unit #43, 4th floor (walk-up).", z, "contradicts")
C(k, "floor", "4", "Spacious 1-Bedroom, 1-Bathroom Apartment Fourth-Floor Walk-Up", u, "confirmed")
C(k, "dogs_allowed", "yes, but 'case by case'", "Cats, small dogs allowed / 12 Month Lease minimum required, pets case by case, Background Checks Required, No Smoking", u, "confirmed")
C(k, "dog_weight_limit", "small dogs only; no pound figure on the current listing (an older listing at this address said 25 lbs)", "Pet friendly 25 lbs.", z, "unconfirmed")
F(k, "deposit_and_fees", "security deposit $2,692; application fee $0", "Security deposit $2,692; Application fee $0", u)
F(k, "listing_agent", "REAL BROKER LLC (Jahiro Casado); no management company named", "broker: REAL BROKER LLC", u)
F(k, "parking", "street only (older listing at this address)", "Parking available 'on the streets' and always safe.", z)
I(k, "none_found", "", f"{NEWS}. Zumper address page: old listings only, no rating.", "search", u, at=ts(u))
R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", "Zumper address page (no rating block): " + z + "; Apartment List: no building page; Trulia unit page carries no ratings")

# ---------------------------------------------------------------- Woodmont Way at West Windsor
k = "100 woodstone circle|08540"; u = U(k); o = "https://www.woodmontwayapartments.com/"; op = o + "pages/pet_policy.asp"; of = o + "pages/faq.asp"; osp = o + "pages/specials.asp"; opl = o + "pages/plans.asp"
WN = ("Own site lists the Ruby plan at '$2540 - $4890' and Garnet at '$2610 - $3790' but shows no unit rows (those sit on a RentCafe portal whose robots.txt answers 403). "
      "REQUIRED FEES: the own site's FAQ lists $80 a month on top of base rent (billing $10, trash $20, amenity $50), although Apartment List shows total_price equal to base_price. "
      "OFFER (own site, verbatim): '1 MONTH FREE RENT! Valid on any vacant apartment. Minimum lease term of 13 months to qualify. Must take occupancy by 11/24/26. Enjoy your savings with your first full month of rent. Limited Time Special - May expire without notice.' "
      "Apartment List's copy reads '1 Month Free on any vacant, 13+ month lease term, move in by 11/15/2026'. The wording ('savings with your first full month') points to a gross listed price with the free month taken up front, but no page says gross or net.")
L(k, "02107", "live", 2610, "available now (since 2026-11-01)", "yes", o, "Unit 02107 (Ruby, 860 sqft) $2,610, 14-month lease; unit record updated 2026-11-15. " + WN)
L(k, "06303", "live", 2610, "available now (since 2026-10-29)", "yes", o, "Unit 06303 (Ruby, 860 sqft) $2,610, 14-month lease; unit record updated 2026-11-15. " + WN)
C(k, "elevator", "yes (Apartment List amenity tag only)", "Elevator", u, "unconfirmed")
C(k, "elevator", "not mentioned on the building's own site", "[The own site's apartment-features and community-amenities pages list no elevator]", o + "pages/amenities.asp", "unconfirmed")
C(k, "floor", "unconfirmed (02107)", "[No page states the floor. My reading: building 02, floor 1, apartment 07, so GROUND FLOOR; the five-digit numbers on Apartment List (02107, 06303, 10207, 11309) fit a building-floor-unit pattern. Needs a call.]", u, "unconfirmed")
C(k, "floor", "unconfirmed (06303)", "[No page states the floor. My reading: building 06, floor 3, apartment 03.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Woodmont Way welcomes cats and dogs and accepts a maximum of two pets per apartment.", op, "confirmed")
C(k, "dog_weight_limit", "no weight limit", "Although we do not have a weight limit, we do have breed restrictions.", op, "confirmed")
F(k, "special_offer", "1 month free on a 13+ month lease, occupancy by 2026-11-24; gross or net not stated", "1 MONTH FREE RENT! Valid on any vacant apartment. Minimum lease term of 13 months to qualify. Must take occupancy by 11/24/26. Enjoy your savings with your first full month of rent.", osp)
F(k, "required_fees", "$80/month: administrative billing $10, trash $20, amenity $50", "ESTIMATED MONTHLY COST INCLUDES: Base Rent plus Administrative Billing Fee: $10; Trash Fee: $20; Amenity Fee: $50.", of)
F(k, "pet_fees", "pet rent $50/month per pet; $500 one-time per pet; $30 a year PetScreening; $55 dog DNA registration", "One-time pet fee of $500 per pet Monthly pet charge of $50 per pet Yearly PETSCREENING fee of $30 per pet ... One-time Dog DNA Registration fee of $55 per dog", op)
F(k, "parking", "garage rent $200-$275/month (optional); surface parking fee not stated", "MONTHLY ADD-ON FEES: Pet Rent: $50 per pet; Storage Unit Rent: $50-$150; Garage Rent: $200-$275.", of)
F(k, "utilities", "resident pays electric, gas, water, sewer, cable/internet", "Utilities: Electric/Gas/Water/Sewer are metered and amount will vary with usage.", of)
F(k, "deposit", "$990 for fully qualified applicants; application $50 per adult", "We offer a $990 security deposit to fully qualified applicants with approved credit.", of)
F(k, "pool", "yes, outdoor heated", "Outdoor amenities include a sparkling heated pool, expansive sun deck", o)
F(k, "management_company", "Woodmont Properties (developer and manager); 443 units", "Woodmont Properties welcomes you to Woodmont Way at West Windsor.", o + "pages/about-us.asp")
I(k, "none_found", "", f"{NEWS} (results were development and leasing coverage; re-nj.com disallows our crawler). The own site shows only its own 5-star reviews, 2021 to 2024. Zumper address page 404.", "search", o)
R(k, "building's own site widget", 5, 8, "2026-11-15", 3, 0, 0, 0, "", op + " (review list shown on every page; newest 2024-10-19; all shown as 5 stars, chosen by the building)")
R(k, "Apartment List", 5, 1, "2026-11-15", 0, "", "", "", "", u + " (aggregate only; no review text on the page)")

# ---------------------------------------------------------------- NYC: Shore Haven and neighbours (Trulia pages live)
def igp(k):
    return [p for p in IG.get(k, {}).get("pages", []) if p.get("status") == 200]
def pluto(k):
    r = PL.get(k); return r
REC = "data/evidence/nyc_records_match.csv"
SH = "https://www.openigloo.com/building/nyc/3329127-3064890001/brooklyn-bath-beach-2072-20-lane-11214"
k = "2072 20th ln|11214"; u = U(k)
L(k, "6E", "live", 2250, "now", "yes", "", "For Rent at $2,250/mo, 'Available: now'. Listed 2026-10-22 (24 days on Trulia). Part of the Shore Haven complex (same tax lot as 1483 Shore Pkwy: 11 buildings, 462 apartments). No building site found.")
C(k, "elevator", "yes", "- Elevator and laundry in building", u, "confirmed")
C(k, "elevator", "6 floors", "42 units · 6 floors · Built in 1949 ... has an elevator, a laundry room and parking", SH, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. My reading: floor 6, the top floor, from unit 6E in a 6-floor building ('Water views in every room').]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed / Pets allowed", u, "confirmed")
C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "parking", "garage, extra fee (amount not stated here; the 1483 Shore Pkwy listing in the same complex says $200/month)", "- Garage parking available for additional fee", u)
F(k, "utilities", "heat and hot water included", "Heat and hot water are included", u)
F(k, "management_company", "Shore Haven Apartments Del LLC (owner, per Openigloo)", "managed by Shore Haven Apartments Del LLC", SH)
F(k, "building", "6 floors, 42 units in this building, built 1949; complex of 11 buildings and 462 apartments on one lot", "pluto_unitsres 462; pluto_numbldgs 11", REC)
k = "1483 shore pkwy|11214"; u = U(k); S1 = "https://www.openigloo.com/building/nyc/3329118-3064890001/brooklyn-bath-beach-1483-shore-pkwy-11214"
L(k, "F", "live", 1825, "now", "yes", "", "For Rent at $1,825/mo, 'Available: now'. Listed 2026-11-06. The text describes 'these spacious one-bedroom apartments' in general, so it reads as an advertisement for a type of apartment in the Shore Haven complex and 'F' may not be a real unit. Ask which apartment is on offer. No building site found.")
C(k, "elevator", "yes", "Residents enjoy convenient building amenities, including elevator access, on-site laundry facilities, garage parking for an additional fee", u, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor and the unit label 'F' gives none. The listing describes apartments in general.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed / The property is pet-friendly.", u, "confirmed")
C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "parking", "detached garage on site, $200/month", "Parking fee $200/mo / Parking: Detached Garage, On Site", u)
F(k, "management_company", "Shore Haven Apartments Del LLC (owner, per Openigloo pages for the same lot)", "managed by Shore Haven Apartments Del LLC", SH)
F(k, "building", "6 floors, built 1949; complex of 11 buildings and 462 apartments on one lot", "pluto_unitsres 462; pluto_numbldgs 11", REC)
k = "1429 shore pkwy|11214"; u = U(k); S2 = "https://www.openigloo.com/building/nyc/3336454-3064680016/brooklyn-bath-beach-1445-shore-parkway-11214"
L(k, "2D", "live", 2450, "now", "yes", "", "For Rent at $2,450/mo, 'Available: now'. Listed 2026-11-05. The text says 'Multiple apartment layouts are available within this sought-after community', so the unit shown may be an example. Three-building complex (263 apartments on the lot). Application fee $20. No building site found.")
C(k, "elevator", "yes", "Enjoy an excellent selection of community amenities, including a **swimming pool /  elevator access, on-site laundry, and 24-hour emergency maintenance.", u, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. My reading: floor 2, from unit 2D in a 6-floor building.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed / **Pets are welcome", u, "confirmed")
C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "parking", "garage, extra fee (amount not stated); a 2024 tenant review calls street parking 'impossible'", "Garage parking is available for an additional fee.", u)
F(k, "pool", "yes (outdoor or indoor not stated)", "- Swimming pool", u)
F(k, "utilities", "heat and hot water included", "Owner pays for heat and hot water.", u)
F(k, "management_company", "Southhampton Apts Del LLC (owner, per Openigloo pages for the same lot)", "managed by Southhampton Apts Del LLC", S2)
F(k, "building", "6 floors, built 1960; three buildings and 263 apartments on the lot", "pluto_unitsres 263; pluto_numbldgs 3", REC)

# ---------------------------------------------------------------- NYC: Trulia pages now blocked (403); facts from the harvest copy of the same page, read earlier today
HV = json.load(open(E / "_trulia_harvest_cached.json")) if (E / "_trulia_harvest_cached.json").exists() else {}
def blocked(k, unit, price, extra=""):
    u = U(k); h = HARV.get(u, "")
    L(k, unit, "blocked", "", "", "no", "", f"Refetch refused: Trulia answered HTTP 403 (bot wall) at this check and again 6 minutes later, so the unit could not be re-verified. The harvest read this page at {h}: For Rent at ${price:,}/mo, 'Available: now'. That earlier reading is the source of the facts recorded for this unit. {extra}".strip())
    return u, h
k = "310 94th st|11209"; u, h = blocked(k, "F7", 1660, "Listed 2026-10-08: 38 days on Trulia at the harvest, and the text says 'PRICE DROP FROM $1700 TO $1660 FOR A NOVEMBER 1ST MOVE IN'. Studio.")
C(k, "elevator", "yes", "Elevator Building", u, "confirmed"); C(k, "elevator", "elevator building on public record (class D7, lift device registered); 6 floors", "pluto_bldgclass D7; has_dob_elevator_device 1", REC, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor; 'F7' gives none.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed"); C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "building", "67 units, 6 floors, built 1928; owner Al-Abassi Building, LLC (Openigloo); batch file names AM Residential", "67 units · 6 floors · Built in 1928", "https://www.openigloo.com/building/nyc/3155473-3061140006/brooklyn-bay-ridge-310-94-street-11209")
k = "9949 shore rd|11209"; u, h = blocked(k, "502", 2595, "Listed 2026-11-11.")
C(k, "elevator", "yes", "Elevator", u, "confirmed"); C(k, "elevator", "elevator building on public record (class D1, lift device registered); 6 floors", "pluto_bldgclass D1; has_dob_elevator_device 1", REC, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. My reading: floor 5, from unit 502 in a 6-floor building ('Direct Verrazzano Bridge Views').]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed"); C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "building", "48 units, 6 floors, built 1931; gym, roof deck, live-in super; owner Meridian Properties (Openigloo); listed by Compass", "This recently renovated pre-war building has scenic river & bridge views. Amenities include a new fully equipped gym and a roof deck ... Live-in super.", u)
k = "8100 bay pkwy|11214"; u, h = blocked(k, "211", 2200, "Listed 2026-11-13.")
C(k, "elevator", "yes, two", "The apartment is located on the second floor of a beautiful, well-maintained building, which has 2 elevators.", u, "confirmed")
C(k, "floor", "2", "The apartment is located on the second floor of a beautiful, well-maintained building", u, "confirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed"); C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "building", "84 units, 6 floors, built 1939; class D4 (elevator co-op) on public record; laundry in the basement", "84 units · 6 floors · Built in 1939", "https://www.openigloo.com/building/nyc/3163920-3062990032/brooklyn-bensonhurst-8100-bay-parkway-11214")
k = "8635 21st ave|11214"; u, h = blocked(k, "4Q", 1800, "Listed 2026-11-06. Studio. 'Some photos may be virtually staged.'")
C(k, "elevator", "not on the listing; elevator building on public record (class D7, lift device registered); 6 floors", "pluto_bldgclass D7; has_dob_elevator_device 1", REC, "confirmed")
C(k, "elevator", "listing does not mention one", "[Trulia feature list at the harvest had no elevator entry]", u, "unconfirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. My reading: floor 4, from unit 4Q in a 6-floor building.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed"); C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "building", "120 units, 6 floors, built 1962; managed by New Park Management, LLC (Openigloo); batch file names Smart NY Realty LLC as lister", "Managed by New Park Management, LLC, the building at 8635 21 Avenue in Bath Beach, Brooklyn has 6 floors and 120 units. Built in 1962", "https://www.openigloo.com/building/nyc/3166996-3063780019/brooklyn-bensonhurst-8635-21-avenue-11214")
F(k, "utilities", "heat and hot water included (listing); tenant reviews dispute the heat", "* Heat & hot water included", u)
k = "123 linden blvd|11226"; PG = "https://www.openigloo.com/building/nyc/3116661-3050840084/brooklyn-flatbush-123-linden-blvd-11226"
u, h = blocked(k, "I19Q", 2599, "NET-EFFECTIVE PRICE: the listing text ends '* 2924, 1.5 ON 13.5 , 2599', which reads as gross rent $2,924 with 1.5 months free on a 13.5-month lease, giving $2,599 net. Listed 2026-11-11. The text says the photos 'may not represent the actual unit'. Zumper has a building page (PLG) with 1-bed plans from $2,667; no unit I19Q there.")
C(k, "elevator", "yes", "Elevator", u, "confirmed"); C(k, "elevator", "yes; 20 floors (Openigloo), 26 stories (Zumper)", "has a doorman, a concierge, an elevator, a laundry room, a gym and parking", PG, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. My reading: floor 19, from 'I19Q' in a tower of 20 or more floors; the label is the lister's code, not a standard unit number.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed"); C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "price_basis", "stored $2,599 is net-effective; gross $2,924; 1.5 months free on 13.5 months", "* 2924, 1.5 ON 13.5 , 2599", u)
F(k, "special_offer", "1.5 months free on a 13.5-month lease (lister's shorthand)", "* 2924, 1.5 ON 13.5 , 2599", u)
F(k, "required_fees", "amenity use is charged separately: tenants report $80 a month, and $700 for a 2026 outdoor-pool season pass (was $250 in 2025)", "Pool - season pass for pool is $700 (up from $250 in 2025). It’s per household with no discount for studios or single occupancy.", PG)
F(k, "pool", "yes: rooftop outdoor and indoor", "Rooftop and indoor swimming pools", u)
F(k, "parking", "valet / attached garage; fee not stated", "Parking: Valet", u)
F(k, "doorman", "doorman and concierge", "has a doorman, a concierge, an elevator, a laundry room, a gym and parking", PG)
F(k, "management_company", "Columbus Property Management (Openigloo); a June 2026 tenant review says 'We are on our 4th management'; batch file names Bushburg", "this 20-floor building at 123 Linden Blvd in Flatbush, Brooklyn has 467 units and is managed by Columbus Property Management", PG)
F(k, "building", "467 units; built 2017 (Openigloo) or 2019 (Zumper)", "467 units · 20 floors · Built in 2017", PG)
F(k, "openigloo_record_summary", "53 evictions, 93 open violations (28 class C), 8 litigation cases; 0.19 violations per unit against a city average of 0.81", "It records 53 evictions, 93 open violations, and 8 litigation cases. Data last updated November 15, 2026.", PG)
k = "3308 glenwood rd|11210"; u, h = blocked(k, "14", 2600, "Listed 2026-11-10. 'Available for ASAP move-in', no broker fee. Zumper's page for the address shows only an old 2-bedroom (#2F) with '1 Month free!'.")
C(k, "elevator", "yes", "-Elevator & wheelchair accessible", u, "confirmed"); C(k, "elevator", "elevator building on public record (class D3, lift device registered)", "pluto_bldgclass D3; has_dob_elevator_device 1", REC, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. Unit '14' in a 38-unit building could be on floor 1; nothing on the page settles it. Needs a call.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed / No broker fee. Pets allowed!", u, "confirmed"); C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "building", "38 units (public record); gym, lounge and coworking, rooftop, bike storage, package room; owner Glenwood Residence LLC (Openigloo); listed by Brooklyn Group", "-Laundry room + package room / -Elevator & wheelchair accessible / -Gym / -Lounge, and coworking space w/ public Wi-Fi / -Rooftop access / -Bike storage / -Private parking available", u)
F(k, "parking", "private parking available; fee not stated", "-Private parking available", u)
k = "315 e 108th st|10029"; ZG = ZU + "315-e-108th-st-new-york-ny-10029-usa"; PH = "https://www.openigloo.com/building/nyc/1052802-1016800011/manhattan-harlem-315-east-108-street-10029"
u, h = blocked(k, "6G", 2375, "Listed 2026-11-02. SECOND SOURCE: Zumper's page for the address, fetched at this check, shows an active 1-bedroom at $2,375 with the same description (last modified 2026-11-14); it names no unit number.")
C(k, "elevator", "yes", "Spacious - One Bedroom w/ Elevator ... -Elevator IN building", u, "confirmed"); C(k, "elevator", "yes; 6 floors", "-Laundry and super on site-Elevator IN building", ZG, "confirmed")
C(k, "floor", "unconfirmed", "[No page states the floor. My reading: floor 6, the top floor, from unit 6G in a 6-floor building.]", u, "unconfirmed")
C(k, "dogs_allowed", "yes", "Cats, small dogs allowed", u, "confirmed"); C(k, "dog_weight_limit", "small dogs only; no pound figure", "Dogs: Allowed; Size allowed: Small", u, "confirmed")
F(k, "building", "48 units, 6 floors, built 1920; laundry and super on site", "48 units · 6 floors · Built in 1920", PH)
F(k, "management_company", "A.J. Clarke Real Estate Corp. (Openigloo); batch file names Alpha Properties NYC I LLC as lister", "315 East 108 Street, Manhattan, NY 10029 is owned or managed by A.J. Clarke Real Estate Corp.", PH)
F(k, "deposit_and_fees", "application $20 per applicant; first month plus one month's deposit at signing", "Total Payments: application payment of $20 (non-refundable) per applicant/guarantor.", u)
F(k, "openigloo_record_summary", "3 evictions, 6 open violations, 5 housing-court cases; 0.12 violations per unit against a city average of 0.81", "This building has 6 open violations. ... This building has 5 housing court litigation cases.", PH)

# ---------------------------------------------------------------- Openigloo review items and ratings (NYC)
TODAY = datetime.date(2026, 11, 15); CUT = TODAY - datetime.timedelta(days=183)
TAGS = [("no_heat_hot_water", r"no heat|never ever had heat|inconsistent heat|heat has been worse|hot water"), ("pests", r"roach|mice|rats?\b|bugs|gnats|infest|pest"),
        ("mold", r"\bmold"), ("elevator_outage", r"elevators? (?:- )?(?:at least|are slow|is|out|broken)|elevators - |faulty elevator|elevators are slow"),
        ("package_theft", r"package theft|rampant theft|stolen package"), ("unresponsive_management", r"doesn.t respond|not very responsive|nonexistent maintenance|slow response|impossible to get a response|takes much longer|not fixed for long"),
        ("fees_or_deposit", r"\$700|you will be charged|squeeze every penny|fees"), ("safety_incident", r"lockdown|shattered|unsafe|not safe"), ("noise", r"\bnois|\bloud")]
def tags_of(b): return [t for t, rx in TAGS if re.search(rx, b, re.I)]
CAT = {"no_heat_hot_water": "management", "pests": "management", "mold": "management", "unresponsive_management": "management", "fees_or_deposit": "management",
       "elevator_outage": "elevator", "package_theft": "safety_incident", "safety_incident": "safety_incident", "noise": "noise"}
def sent(body, rx):
    """One or two verbatim sentences around the first match of rx."""
    parts = re.split(r"(?<=[.!?])\s+", body.replace("\n", " ").strip())
    for i, p in enumerate(parts):
        if re.search(rx, p, re.I):
            s = p if len(p) > 60 or i + 1 >= len(parts) else p + " " + parts[i + 1]
            return s[:330]
    return body[:300]
SIB = {"2072 20th ln|11214": "sibling building in the same complex (same tax lot)", "1483 shore pkwy|11214": "sibling building in the same complex (same tax lot)", "1429 shore pkwy|11214": "sibling building in the same complex (same tax lot)"}
OWN = {"2072 20th ln|11214": "2072-20-lane", "1483 shore pkwy|11214": "1483-shore-pkwy", "1429 shore pkwy|11214": "1429-shore-parkway"}
EXTRA_PAGES = {"2072 20th ln|11214": (SH, 0), "3308 glenwood rd|11210": ("https://www.openigloo.com/building/nyc/3206005-3075610041/brooklyn-east-flatbush-3308-glenwood-road-11210", 0)}
for k in [x for x in B if B[x]["state"] == "NY"]:
    pages = igp(k); any_item = False; rows_written = 0
    if k in EXTRA_PAGES:
        R(k, "Openigloo", "", 0, "2026-11-15", 0, 0, 0, 0, "", EXTRA_PAGES[k][0] + " (page exists, 0 reviews)"); rows_written += 1
    for p in pages:
        url = p["fetched"]; own = k not in SIB or OWN[k] in url
        label = "Openigloo" if own else "Openigloo, " + SIB[k]
        revs = p.get("reviews") or []; agg = p.get("agg") or {}
        if not agg and not revs:
            if own and k not in EXTRA_PAGES: R(k, label, "", 0, p["retrieved_at"][:10], 0, 0, 0, 0, "", url + " (page exists, 0 reviews)"); rows_written += 1
            continue
        last6 = neg6 = negold = 0; t6 = []
        for r in revs:
            d = datetime.date.fromisoformat(r["date"][:10]); body = r.get("body") or ""; tg = tags_of(body.split("Cons:")[-1]) if "Cons:" in body else tags_of(body)
            neg = float(r["rating"]) <= 2.5 or bool(set(tg) - {"noise", "fees_or_deposit"})
            if d >= CUT:
                last6 += 1; neg6 += neg; t6 += [t for t in tg if t not in t6]
            else: negold += neg
            cons = body.split("Cons:")[-1].strip() if "Cons:" in body else body
            pros = body.split("Cons:")[0].replace("Pros:", "").strip() if "Cons:" in body else ""
            done = set()
            for t in tg:
                c = CAT[t]
                if c in done: continue
                done.add(c); rx = dict(TAGS)[t]
                I(k, c, r["date"][:10], sent(cons, rx), label, url, "building" if own else "building", at=p["retrieved_at"]); any_item = True
            if not tg and float(r["rating"]) >= 4 and len(pros) > 25:
                I(k, "positive", r["date"][:10], pros[:300], label, url, at=p["retrieved_at"]); any_item = True
        note = "" if len(revs) >= int(agg.get("reviewCount") or 0) else f" ({len(revs)} newest of {agg.get('reviewCount')} reviews readable on the page)"
        R(k, label, round(float(agg.get("ratingValue") or 0), 2) if agg else "", agg.get("reviewCount", len(revs)), p["retrieved_at"][:10], len(revs), last6, neg6, negold, ";".join(t6), url + note); rows_written += 1
    if not rows_written:
        R(k, "none_found", "", "", "2026-11-15", 0, "", "", "", "", "Openigloo: no page for this building; Zumper address page: no rating; Trulia: page blocked or carries no ratings")
    if not any_item:
        I(k, "none_found", "", f"Openigloo page for the building has no review text. {NEWS}.", "Openigloo / search", (pages[0]["fetched"] if pages else EXTRA_PAGES.get(k, (U(k),))[0]), at=(pages[0]["retrieved_at"] if pages else ""))
# hand-written additions for the two buildings with the most to say
I("123 linden blvd|11226", "elevator", "2026-09-18", "Elevators - at least 1 is always out of use. Only 1 of 4 elevators in order at times. Very long lines.", "Openigloo", PG, at=ts(PG) or "")
I("123 linden blvd|11226", "other", "2026-11-15", "Tenants rate it 2.8/5 across 28 reviews, with 15% recommending it and 18% approving of the owner. It records 53 evictions, 93 open violations, and 8 litigation cases.", "Openigloo (site summary)", PG, at=ts(PG) or "")
I("8635 21st ave|11214", "other", "2026-11-11", "Tenants rate it 2.1/5 across 3 reviews, with 0% recommending it and 0% approving of the owner. It records 10 evictions, 32 open violations, and 8 litigation cases.", "Openigloo (site summary)", "https://www.openigloo.com/building/nyc/3166996-3063780019/brooklyn-bensonhurst-8635-21-avenue-11214")
I("1429 shore pkwy|11214", "car_crime", "", "", "", "", "")  # placeholder removed below
items[:] = [i for i in items if not (i["category"] == "car_crime" and not i["excerpt"])]
# de-duplicate items (the elevator line for 123 Linden is produced twice)
seen = set(); ded = []
for i in items:
    key = (i["addr_key"], i["category"], i["item_date"], i["excerpt"][:80])
    if key in seen: continue
    seen.add(key); ded.append(i)
items = ded
for i in items:
    if not i["retrieved_at"]:
        i["retrieved_at"] = next((p["retrieved_at"] for kk in IG for p in IG[kk].get("pages", []) if p.get("fetched") == i["source_url"]), "") or ts(i["source_url"]) or "2026-11-15T22:56:00+00:00"

def w(nm, rows, cols):
    with open(OUT / f"{nm}_batch_{N}.csv", "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
    print(nm, len(rows))
order = list(B)
for lst in (live, conf, items, facts, ratings): lst.sort(key=lambda r: order.index(r["addr_key"]))
w("live_check", live, "addr_key,listing_url,unit,status,price_now,available_now_text,matches_stored,building_site_url,checked_at,notes".split(","))
w("confirm", conf, "addr_key,fact,value,quote,source_url,status".split(","))
w("items", items, "addr_key,building_name,category,item_date,excerpt,source_site,source_url,about,retrieved_at".split(","))
w("facts", facts, "addr_key,fact,value,quote,source_url".split(","))
w("ratings", ratings, "addr_key,building_name,rating_source,rating_value,rating_scale,review_count,as_of_date,reviews_read,reviews_last_6_months,negative_last_6_months,negative_older,serious_issue_tags_last_6_months,source_url".split(","))
import collections
print("live", collections.Counter(r["status"] for r in live)); print("confirm", collections.Counter(r["status"] for r in conf))
print("items", collections.Counter(r["category"] for r in items)); print("ratings none", sum(r["rating_source"] == "none_found" for r in ratings))
missing = [k for k in B if not any(r["addr_key"] == k for r in ratings)]; print("no rating row:", missing)
print("no live row:", [k for k in B if not any(r["addr_key"] == k for r in live)], "no items:", [k for k in B if not any(r["addr_key"] == k for r in items)])
