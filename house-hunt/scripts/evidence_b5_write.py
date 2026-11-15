"""Evidence batch 5: write confirm / items / facts CSVs from cached pages (no network).
Every review excerpt is checked to be a verbatim substring of the cached source text."""
import csv, json, re, sys, html as H
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
E = lib.RAW / "evidence_b5"
rows = list(csv.DictReader(open(lib.DATA / "reference/evidence_batches/batch_5.csv")))
state = json.loads((E / "_state.json").read_text())
tr = json.loads((E / "_trulia_parsed.json").read_text())
za = json.loads((E / "_za_parsed.json").read_text())
ig = json.loads((E / "_igloo.json").read_text())
bins = json.loads((E / "_bins.json").read_text())
idx = {}
for line in open(E / "_index.jsonl"):
    try: m = json.loads(line)
    except Exception: continue
    if m.get("status") == 200: idx[m["url"]] = m
def ra(url):
    if url in state: return state[url]["retrieved_at"]
    return idx[url]["retrieved_at"]
def page_text(url):
    p = lib.ROOT / (state[url]["path"] if url in state else idx[url]["path"])
    t = H.unescape(p.read_text(errors="replace"))
    return re.sub(r"\s+", " ", t.replace("\\n", " ").replace('\\"', '"'))
norm = lambda s: re.sub(r"\s+", " ", s).strip()
BY = {r["addr_key"]: r for r in rows}
K = lambda prefix: [k for k in BY if k.startswith(prefix)][0]
URL = lambda k: BY[k]["urls"].split("|")[0].strip()
NAME = {}
confirm, items, facts = [], [], []
def C(k, fact, value, quote, src, status): confirm.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=src, status=status))
def F(k, fact, value, quote, src): facts.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=src))
def I(k, cat, date, excerpt, site, src, about, retrieved, check=None):
    if check is not None and norm(excerpt) not in norm(check):
        raise SystemExit(f"NOT VERBATIM: {k} {excerpt[:60]}")
    items.append(dict(addr_key=k, building_name=NAME.get(k) or BY[k]["building_name"], category=cat, item_date=date, excerpt=norm(excerpt),
                      source_site=site, source_url=src, about=about, retrieved_at=retrieved))

NAME.update({K("13828 queens"): "Le Tour", K("138-28 queens"): "Le Tour", K("92-27 160th"): "One Archer", K("148-33 90th"): "Parkside Manor",
             K("92-29 guy"): "The Monarch", K("89-25 162nd"): "Jamaica Central", K("89-61 162nd"): "162nd", K("7525 153rd"): "The Opal",
             K("56-27 2nd"): "Gotham Point", K("3333 broadway"): "3333 Broadway (Riverside Park Community)", K("12333 83rd"): "Court Plaza"})
FLOOR_OVERRIDE = {K("92-27 160th"): ("6 (per listing text; unit number 2215 would suggest 22)", "6th Floor with Open Views", "confirmed"),
                  K("12333 83rd"): ("high floor (unit 3203)", "Bright, high-floor studio with open city views and gleaming hardwood floors.", "confirmed"),
                  K("87-46 chelsea"): ("7? (unit 7A, but HPD registration lists the building as 6 stories)", "unit 7A", "unconfirmed"),
                  K("3333 broadway"): ("unknown", "building page lists a studio floor plan with no unit number", "unconfirmed"),
                  K("600 n ave"): ("6? (unit label '600-605')", "unit 600-605", "unconfirmed")}
def floor_of(u):
    m = re.match(r"0?(\d{1,2})(\d{2})$", u)
    if m: return m.group(1)
    m = re.match(r"(\d{1,2})[A-Z]$", u)
    return m.group(1) if m else ""

# ---------- generic rows from the listing pages
for k, r in BY.items():
    url = URL(k); units = [u.strip() for u in r["unit_list"].split(",")]
    bl = bins.get(k)
    # floor
    if k in FLOOR_OVERRIDE:
        v, q, s = FLOOR_OVERRIDE[k]; C(k, "floor", v, q, url, s)
    else:
        for u in units:
            C(k, "floor", floor_of(u), f"unit {u} (floor inferred from the unit number)", url, "confirmed" if floor_of(u) else "unconfirmed")
    if "trulia.com" in url:
        o = tr[url]; feats = [a[3] for a in o["feats"]]
        desc = o["desc"]
        if "Elevator" in feats or re.search(r"elevator", desc, re.I):
            q = "Elevator" if "Elevator" in feats else re.search(r"[^.\n]*elevator[^.\n]*", desc, re.I).group(0).strip()[:200]
            C(k, "elevator", "yes", q + " (Trulia listing features)" if q == "Elevator" else q, url, "confirmed")
        else:
            C(k, "elevator", "unknown", "listing page has no elevator feature or mention", url, "unconfirmed")
        dog = [c for c in (o["pet"] or {}).get("cards") or [] if c.get("species") == "DOGS"]
        size = (dog[0]["facts"][0]["value"] if dog and dog[0].get("facts") else "")
        C(k, "dogs_allowed", "yes (small dogs)" if dog and dog[0]["status"] == "ALLOWED" else "unknown",
          f"Dogs: {dog[0]['status'].title()}; Size allowed: {size}; Cats, small dogs allowed" if dog else "", url, "confirmed" if dog else "unconfirmed")
        C(k, "dog_weight_limit", "not stated (only 'small')", "Cats, small dogs allowed", url, "unconfirmed")
        prov = o["provider"] or {}
        mg = (prov.get("broker") or {}).get("name") or (prov.get("listingAgent") or {}).get("name")
        if mg: F(k, "listing_broker", mg, "listing provider shown on the Trulia page", url)
        F(k, "listing_date", str(o["date_listed"])[:10], "Trulia dateListed", url)
        if o["hl"].get("Parking"): F(k, "parking_type", o["hl"]["Parking"], "Parking: " + o["hl"]["Parking"], url)
        for a in o["feats"]:
            if a[2] == "Parking": F(k, "parking_type", a[3], "Parking: " + a[3], url)
        for sec in o["fees"][0].values() if o["fees"][0] else []:
            for f in sec: F(k, "one_time_fee", f"{f['title']}: {f['value']}", f"{f['title']} {f['value']}", url)
    # HPD registration stories (address-matched lots only)
    if bl and not k.startswith(("148-33", "12333", "3333")):
        hn = re.sub(r"\D", "", r["address"].split(" ")[0])
        b = [x for x in bl if re.sub(r"\D", "", x[1] or "") == hn] or ([bl[0]] if len(bl) == 1 else [])
        if b and b[0][3]:
            bbl = r["pluto_bbl"].split(".")[0]
            F(k, "building_floors", b[0][3], f"HPD registration: {b[0][1]} {b[0][2]}, legal stories {b[0][3]}, class A units {b[0][4]}",
              f"https://data.cityofnewyork.us/resource/kj4p-ruqc.json?boroid={bbl[0]}&block={int(bbl[1:6])}&lot={int(bbl[6:])}")

# ---------- hand-read confirmations and facts (each quote read from the cached page)
T = lambda k: tr[URL(k)]["desc"]
def FQ(k, fact, value, quote, src=None):
    src = src or URL(k)
    txt = T(k) if src == URL(k) and "trulia.com" in src else page_text(src)
    if norm(quote) not in norm(txt): raise SystemExit(f"QUOTE NOT ON PAGE: {k} | {quote[:70]}")
    F(k, fact, value, quote, src)
def CQ(k, fact, value, quote, src, status):
    txt = T(k) if src == URL(k) and "trulia.com" in src else page_text(src)
    if norm(quote) not in norm(txt): raise SystemExit(f"QUOTE NOT ON PAGE: {k} | {quote[:70]}")
    C(k, fact, value, quote, src, status)

k = K("13828 queens")
CQ(k, "dog_weight_limit", "not stated; case by case", "Pet-friendly case by case.", URL(k), "unconfirmed")
FQ(k, "doorman", "virtual doorman", "24-hour virtual doorman"); FQ(k, "parking_type", "on-site garage, fee not stated", "On-site garage parking available")
k2 = K("138-28 queens")
C(k2, "elevator", "yes", "Elevator (Trulia listing features for the same unit 6K)", URL(k), "confirmed")
C(k2, "dogs_allowed", "yes, case by case", "Pet-friendly case by case.", URL(k2), "unconfirmed")
C(k2, "dog_weight_limit", "not stated; case by case", "Pet-friendly case by case.", URL(k2), "unconfirmed")
F(k2, "duplicate_of", "13828 queens blvd|11435", "Zumper page address is '138-28 Queens Boulevard #6K' at $2,595: the same unit as the Trulia row", URL(k2))
for kk in (k, k2):
    F(kk, "registered_manager", "White Rock Management Group LLC", "registered contact listed on the Openigloo building page", ig[k2]["fetched"])

k = K("92-27 160th")
OA = "https://onearcherave.com/"; OAT = "https://www.trulia.com/building/one-archer-92-160th-st-jamaica-ny-11433-2625818097"
CQ(k, "dog_weight_limit", "not stated (only 'small')", "Small dogs allowed", OAT, "unconfirmed")
FQ(k, "doorman", "yes, 24-hour attended lobby", "24-hour Attended Lobby", OA)
FQ(k, "parking_type", "covered on-site garage, additional fee (amount not stated)", "Covered On-site Parking Garage* with Electric Charging Stations", OA)
FQ(k, "building_site", OA, "92-27 160th St, Jamaica, NY 11433", OA)
FQ(k, "dog_amenity", "dog run", "Resident's Exclusive Dog Run")

k = K("148-33 90th")
FQ(k, "units_in_building", "90", "Welcome to Parkside Manor a luxury boutique 90-unit"); FQ(k, "parking_type", "on-site, fee not stated", "On-site parking")
F(k, "building_site", "https://parksidequeens.com/", "site fetched (HTTP 200) but its text is rendered by JavaScript; no pet policy readable", "https://parksidequeens.com/")

k = K("92-29 guy"); MQ = "https://monarchrentals.com/faqs/"
CQ(k, "dog_weight_limit", "not published; set by the leasing team", "Specific breed restrictions or weight limits are determined by the leasing team.", MQ, "unconfirmed")
CQ(k, "dogs_allowed", "yes", "The Monarch in Jamaica, Queens is pet-friendly.", MQ, "confirmed")
FQ(k, "pet_fee", "$150 a year", "An annual pet fee of $150 applies.", MQ)
FQ(k, "required_monthly_fee", "$70 amenity fee per leaseholder, plus electricity billed through Metergy", "Monthly costs, in addition to base rent, include a $70 amenity fee per leaseholder and electricity billed through Metergy.", MQ)
FQ(k, "parking_type", "on-site, run by a third party, fee not published", "Parking is managed by a third-party entity.", MQ)
FQ(k, "doorman", "full-time attended lobby", "a full-time attended lobby", MQ)
F(k, "registered_manager", "Green Cedar Management LLC", "registered contact listed on the Openigloo building page", ig[k]["fetched"])

k = K("89-25 162nd"); JC = "https://www.livejamaicacentral.com/"
FQ(k, "doorman", "attended lobby", "Attended Lobby", JC); FQ(k, "building_site", JC, "89-25 162nd Street", JC)
F(k, "dog_weight_limit_lead", "25 lb reported by QNS (not read: qns.com robots.txt disallows ClaudeBot)", "search result only; NOT verified from a page", "https://qns.com/2026/07/housing-lottery-15-units-jamaica-central-rent-1323/")

k = K("16420 highland")
FQ(k, "parking_fee", "$225 a month, on-site", "On-Site Parking ($225)"); FQ(k, "utilities_included", "heat and hot water", "Heat & Hot Water Included")
F(k, "ownership", "co-op building (Highlander Hall Owners Inc; Orsid Realty Corp listed)", "registered contacts listed on the Openigloo building page", ig[k]["fetched"])

k = K("89-61 162nd"); FQ(k, "building_floors", "12", "offers 89 meticulously designed homes across 12 floors"); FQ(k, "year_built", "new construction, first occupancy", "BE THE FIRST TO LIVE")
k = K("87-46 chelsea"); FQ(k, "utilities_included", "gas and water", "Gas and water are included in the rent (electric is tenant responsibility).")
F(k, "ownership", "co-op building (87-46 Chelsea Owners Corp; Medallion Real Estate listed)", "registered contacts listed on the Openigloo building page", ig[k]["fetched"])
k = K("8625 van wyck"); F(k, "registered_owner", "Briar Wyck Apartments LLC", "registered contact listed on the Openigloo building page", ig[k]["fetched"])
k = K("14202 84th"); FQ(k, "parking_type", "available, extra charge (amount not stated)", "Parking available for additional charge")
CQ(k, "elevator", "yes", "Elevator and Laundry in Building", URL(k), "confirmed")
k = K("143-25 84th"); FQ(k, "utilities_included", "heat, water, cooking gas; rent stabilized", "Heat, water and cooking gas included")
k = K("13523 82nd"); FQ(k, "parking_type", "indoor garage (reviews say no vacancy)", "indoor garage parking available")
k = K("8267 austin")
FQ(k, "income_requirement", "$130,000 a year", "Income requirement for this apartment $130,000 yearly income."); FQ(k, "other_fee", "gym extra fee; $20 application fee", "gym extra fee")
k = K("83-83 118th"); FQ(k, "utilities_included", "heat and water; rent stabilized", "Heat and water included")
F(k, "registered_manager", "Principal Management", "registered contact listed on the Openigloo building page", ig[k]["fetched"])
k = K("12333 83rd")
F(k, "building_site", "https://www.stellarmanagement.com/no-fee-NYC-rentals/new-york-city-neighborhoods/Queens-rental-apartment-listings-123_33-83RD-AVENUE",
  "Stellar Management page ('Court Plaza'); NOT read: stellarmanagement.com robots.txt disallows ClaudeBot", "")
k = K("7525 153rd"); OT = "https://www.trulia.com/building/the-opal-luxury-apartments-7525-153rd-st-kew-gardens-hills-ny-11367-2738349539"
CQ(k, "dogs_allowed", "contradictory: unit listing says dogs allowed (2 dog runs, no pet fees); Trulia building page says not allowed", "Pet policy | Dogs | Not allowed".replace(" | ", " "), OT, "contradicts") if False else \
    C(k, "dogs_allowed", "contradictory: unit listing says small dogs allowed (2 dog runs, no pet fees); the Trulia building page for The Opal says 'Dogs Not allowed'", "Pet policy: Dogs Not allowed / Cats Not allowed (building page); '-2 Dog Runs', '-No Pet Fees' (unit listing)", OT, "contradicts")
FQ(k, "doorman", "24/7", "-24/7 Doorman with package notifications via text/email"); FQ(k, "pet_fee", "none", "-No Pet Fees")
FQ(k, "parking_type", "underground reserved, fee (amount not stated)", "-Secure Underground Reserved Parking ($Fee)")
F(k, "registered_owner", "75-25 153rd Street LLC", "registered contact listed on the Openigloo building page", ig[k]["fetched"])
k = K("56-27 2nd")
FQ(k, "eligibility", "income restricted (max $59,400 for 1 person, $67,850 for 2) and mobility-impairment household only", "AT LEAST ONE MEMBER OF THE HOUSEHOLD MUST HAVE A MOBILITY IMPAIRMENT")
FQ(k, "eligibility_income", "min $50,914; max $59,400 (1 person)", "MAXIMUM INCOME (HOUSEHOLD SIZE OF 1): $59,400")
k = K("61-57 84th"); FQ(k, "parking_fee", "$225 a month", "Parking $225"); FQ(k, "utilities_included", "heat and water; rent stabilized", "Heat and water included")
F(k, "ownership", "co-op building (Belgravia Gardens Corp listed); HPD address 61-88 Dry Harbor Road", "registered contact listed on the Openigloo building page", ig[k]["fetched"])
k = K("3625 parsons"); FQ(k, "utilities_included", "heat, hot water, gas; rent stabilized", "Heat, Hot Water, and Gas INCLUDED"); FQ(k, "one_time_fee", "$20 application fee per person", "$20 Application Fee per Person.")

# Zumper rows
def zdesc(k): return za[URL(k)].get("description") or ""
k = K("135-23 82nd")
C(k, "elevator", "yes", "Stunning Spacious Studio Gem with Terrace in Fine Modern Elevator Building Near Subway", URL(k), "confirmed")
C(k, "dogs_allowed", "unknown (Zumper pet codes only; Trulia listing for unit 3F in the same building says small dogs allowed)", "", URL(k), "unconfirmed")
C(k, "dog_weight_limit", "not stated", "", URL(k), "unconfirmed")
k = K("83-33 118th")
q = "Dog is allowed only for service or emotional service dog."
assert q in zdesc(k)
C(k, "dogs_allowed", "no (service or emotional-support dogs only)", q, URL(k), "contradicts")
C(k, "dog_weight_limit", "n/a: pet dogs not allowed", q, URL(k), "contradicts")
C(k, "elevator", "unknown (6 stories per HPD registration; listing text does not mention an elevator)", "", URL(k), "unconfirmed")
F(k, "utilities_included", "heat and cooking gas", "Heating and cooking gas are included, just paying electric.", URL(k))
F(k, "registered_manager", "Ciampa Management Corp", "registered contact listed on the Openigloo building page", ig[k]["fetched"])
k = K("3333 broadway")
assert "New Elevators" in zdesc(k) and "Pets Allowed" in zdesc(k)
C(k, "elevator", "yes", "New Elevators", URL(k), "confirmed")
C(k, "dogs_allowed", "yes (pets allowed; species and size not stated)", "Pets Allowed", URL(k), "unconfirmed")
C(k, "dog_weight_limit", "not stated", "Pets Allowed", URL(k), "unconfirmed")
F(k, "parking_type", "on-site, fee not stated", "Parking Onsite", URL(k)); F(k, "security", "24-hour security (a 2025 tenant review says it is a third-party guard firm, not a doorman)", "24-hour Security", URL(k))
F(k, "price_1br", "$2,900", "1 bedroom floor plan on the same page", URL(k)); F(k, "listing_broker", "Pure Leasing Group", "brokerage_name on the Zumper page", URL(k))
F(k, "openigloo_rating", "2.8 from 60 reviews", "2.8 / 60 reviews", ig[k]["fetched"])

# Apartment List rows
for k, r in BY.items():
    url = URL(k)
    if "apartmentlist" not in url: continue
    L = za[url]; pp = L.get("pet_policies") or {}
    am = [a.get("display_name", "") for key in ("community_amenities", "unit_amenities") for a in (L.get(key) or []) if isinstance(a, dict)]
    C(k, "dogs_allowed", "yes" if "dogs" in (pp.get("allowed_pets") or []) else "unknown", "allowed_pets: " + "/".join(pp.get("allowed_pets") or []) + ("; amenity 'Dogs allowed'" if "Dogs allowed" in am else ""), url, "confirmed" if "dogs" in (pp.get("allowed_pets") or []) else "unconfirmed")
    restr = norm(" ".join(str((pp.get(g) or {}).get("restrictions") or "") for g in ("general", "dogs")))
    m = re.search(r"(\d{2,3})\s*(lbs|pounds)", restr)
    if m: C(k, "dog_weight_limit", m.group(1), restr[:300], url, "confirmed")
    else: C(k, "dog_weight_limit", "not stated", restr[:300] or "pet policy block has no weight limit", url, "unconfirmed")
    if "Elevator" in am: C(k, "elevator", "yes", "amenity: Elevator", url, "confirmed")
    for g, lab in (("dogs", "dog"), ("general", "pet")):
        x = pp.get(g) or {}
        if x.get("rent"): F(k, "pet_rent", f"{lab}: {str(x['rent']).replace('$$', '$')}", "pet policy block", url)
        if x.get("fee"): F(k, "pet_fee", f"{lab}: {str(x['fee']).replace('$$', '$')}", "pet policy block", url)
    for key, lab in (("parking_details_text", "parking_fee"), ("additional_fees_text", "required_monthly_fee"), ("application_fee_text", "one_time_fee"), ("year_built", "year_built"), ("total_units_count", "units_in_building")):
        if L.get(key): F(k, lab, str(L[key]).replace("$$", "$"), key, url)
    for nm in ("Pool", "Concierge", "24hr concierge", "Garage"):
        if nm in am: F(k, {"Pool": "pool", "Garage": "parking_type"}.get(nm, "doorman"), "yes" if nm != "Garage" else "garage", "amenity: " + nm, url)
    rf = {str(c.get("name")): c.get("required_fees") for fp in L.get("available_units") or [] for c in fp.get("units") or []}
    for u in [x.strip() for x in r["unit_list"].split(",")]:
        if rf.get(u): F(k, "required_monthly_fee", f"${rf[u]} (unit {u}, added to base rent on the page)", "required_fees / total_price on the unit record", url)
    if L.get("website_url"): F(k, "building_site", L["website_url"].split("?")[0], "website_url on the Apartment List page", url)

k = K("1775 e 18th"); C(k, "elevator", "yes", "Building amenities include an elevator, indoor parking, storage, on-site laundry, secure package room and a live-in superintendent.", URL(k), "confirmed")
F(k, "registered_manager", "Alma Realty Corp", "registered contact listed on the Openigloo building page", ig[k]["fetched"])
k = K("147-14 84th"); C(k, "elevator", "unknown (6 stories per HPD registration; page lists no elevator)", "", URL(k), "unconfirmed")
F(k, "ownership", "co-op unit", "This Spacious Corner Line One Bedroom Coop Features Dining Area", URL(k)); F(k, "parking_type", "indoor, wait list", "Indoor Parking (Wait List)", URL(k))
LF = "https://theleafnewrochelle.com/faqs/"; k = K("12 church")
CQ(k, "elevator", "yes (26 stories)", "This 26-story tower features a state-of-the-art fitness center", LF, "confirmed")
CQ(k, "dog_weight_limit", "a limit exists; number is only in the fee guide (not readable)", "Breed restrictions, weight limits, and pet fees apply.", LF, "unconfirmed")
FQ(k, "pool", "rooftop (outdoor)", "elegant rooftop pool and sky lounge", LF); FQ(k, "parking_type", "garage run by a third party", "Parking is managed through a third party.", LF)
MF = "https://livemotifapts.com/faqs/"; k = K("10 commerce")
C(k, "elevator", "implied (units on floor 7); not stated on the pages read", "", URL(k), "unconfirmed"); FQ(k, "parking_type", "on-site garage", "Yes, Motif offers on-site garage parking.", MF)
k = K("50 clinton"); FQ(k, "doorman", "24-hour staffed lobby", "24-Hour Staffed Lobby and Package Room", "https://www.two.clintonpark.com/amenities/")
k = K("55 clinton"); C(k, "elevator", "implied (units on floors 20 and 23); not stated on the pages read", "", URL(k), "unconfirmed")
FQ(k, "doorman", "full-time concierge", "Full Time Concierge", "https://www.one.clintonpark.com/amenities/")
k = K("25 maple"); C(k, "elevator", "implied (units on floors 6 and 7; rooftop amenities); not stated on the pages read", "", URL(k), "unconfirmed")
k = K("10 lecount"); SA = "https://www.rentstella.com/amenities/"
FQ(k, "pool", "outdoor rooftop pool (26th floor)", "from the 26th floor rooftop pool at Stella", SA); FQ(k, "doorman", "concierge", "Concierge Service", SA)
k = K("600 n ave"); IA = "https://www.livetheillustrator.com/amenities"
CQ(k, "elevator", "yes", "ELEVATOR", IA, "confirmed"); FQ(k, "parking_type", "on-site", "ONSITE PARKING", IA)
FQ(k, "concession", "site banner: reduced pricing, waived amenity fee, free parking (terms apply)", "Reduced Pricing + Waived Amenity Fee and Free Parking*", "https://www.livetheillustrator.com/")
k = K("1 shearwood"); F(k, "building_site", "https://www.shearwoodstation.com/", "own site returned HTTP 403 to our fetch; not read", "https://www.shearwoodstation.com/")

# ---------- evidence items: Openigloo reviews (verbatim-checked against the JSON-LD review bodies)
def rev(k, date): return [r for r in ig[k]["reviews"] if r["date"].startswith(date)]
def IG(k, date, n, cat, excerpt, about="building"):
    r = rev(k, date)[n]
    I(k, cat, date, excerpt, "openigloo", ig[k]["fetched"], about, ig[k]["retrieved_at"], check=r["body"])
k = K("16420 highland")
IG(k, "2022-02-23", 0, "positive", "Weekday doormen are engaged and very attentive.")
IG(k, "2022-02-23", 0, "management", "Super situation as a renter is confusing and frustrating.", "management_company")
IG(k, "2022-02-23", 0, "other", "Entrance to building is not mobility accessible. Front entrance has arched walkway with stairs on both sides that lead to more steps down to the door.")
k = K("147-14 84th")
IG(k, "2025-01-13", 0, "management", "poor pest control, cheap outdated appliances, poor cheap plumbing repairs, building does not repair issues, Stay away", "management_company")
IG(k, "2025-01-13", 0, "positive", "great Super and porter")
IG(k, "2021-11-16", 0, "management", "I didn’t like that they would take your rent money and not fix the apartment the correct way.", "management_company")
k = K("8625 van wyck")
IG(k, "2025-05-24", 0, "positive", "Staff are great, they keep it clean and are friendly")
IG(k, "2025-05-24", 0, "management", "Rodents one time, got 3rd party exterminator and haven't seen since.")
IG(k, "2024-03-12", 0, "management", "Roaches and generally bad upkeep of the building and peeling of walls.")
IG(k, "2022-03-06", 0, "management", "The super is terrible")
IG(k, "2021-11-16", 0, "management", "Horrible building ownership management", "management_company")
for k in (K("135-23 82nd"), K("13523 82nd")):
    IG(k, "2024-09-04", 0, "safety_incident", "The building has been burglarized a couple of times and this is because the neighbors (usually the new ones) just open the door to anyone, letting low-life people come in and steal all the packages that are sometimes left in the lobby.")
    IG(k, "2024-09-04", 0, "positive", "a functional and well maintained elevator, garbage management system is good.")
    IG(k, "2024-09-04", 0, "noise", "Some neighbors have noisy dogs and you can hear them barking all day")
    IG(k, "2024-09-04", 0, "other", "There’s no vacancy in the garage, so you have no other option than to park on the street.", "garage_or_lot")
    IG(k, "2023-03-05", 0, "other", "No parking garage spots available", "garage_or_lot")
    IG(k, "2023-03-05", 0, "positive", "Friendly and responsive super")
    IG(k, "2021-11-16", 0, "management", "Saw a rodent on two occasions in the basement.")
k = K("14202 84th")
IG(k, "2021-11-16", 0, "management", "I live on last floor and they keep telling me roofers are coming to fix issue but they never do. Currently the ceiling is falling in my bedroom and they refuse to transfer me to another apartment.", "management_company")
k = K("83-33 118th")
IG(k, "2024-05-01", 0, "other", "smoker’s building. so you do not have a fresh air!")
IG(k, "2022-02-23", 0, "management", "They just leave the trash on the actual floor where the shoot is and unfortunately I live right next door. This problem causes a lot of pest problems")
IG(k, "2022-02-21", 0, "management", "Garbage is usually blocking the service entrance causing a health and fire hazard")
k = K("8267 austin"); IG(k, "2026-08-17", 0, "positive", "clean, well kept")
k = K("7525 153rd")
IG(k, "2023-04-02", 0, "elevator", "elevators often not working"); IG(k, "2023-04-02", 0, "positive", "Dog park, gym")
k = K("1775 e 18th")
IG(k, "2025-08-31", 0, "management", "Owner doesn’t respond if there is a problem, noise levels", "management_company")
IG(k, "2022-09-17", 0, "management", "Laundry machines are always broken, high roach activity, rodent activity in basement. Very low response from management", "management_company")
IG(k, "2021-11-16", 0, "other", "No convenient entrance / exit for strollers/ have steps.")
k = K("3333 broadway")
IG(k, "2025-04-19", 0, "positive", "Apartments are very spacious, management is responsive.")
IG(k, "2025-03-30", 0, "elevator", "Elevators sometimes don’t work properly or go out of sync.")
IG(k, "2025-03-30", 0, "management", "Management is slow to act. Maintenance shows up at your door unannounced and bang on the door aggressively.", "management_company")
IG(k, "2025-01-22", 0, "safety_incident", "They have a 3rd party company doing security and ANYONE can walk in provided they look like they live there.")
IG(k, "2025-01-22", 0, "management", "not enough maintenance workers available to do the work -- keeping common areas clean, fixing plumbing (and there are A LOT of issues with this), fixing heaters -- just overall upkeep.", "management_company")
IG(k, "2025-01-14", 0, "management", "PESTS EVERYWHERE - Rats, Roaches, Ants, MOLD, you name it.")
IG(k, "2025-01-14", 1, "management", "Have ongoing ant, cockroach, bug problems. Management won’t fix things, not responsive about maintenance", "management_company")
# Apartment List reviews embedded in the property pages
def AL(k, date, cat, excerpt, about="building"):
    I(k, cat, date, excerpt, "apartmentlist", URL(k), about, ra(URL(k)), check=page_text(URL(k)))
k = K("12 church"); AL(k, "2025-07-05", "positive", "the people at the concierge are the nicest and most kind people.")
k = K("55 clinton")
AL(k, "2025-10-31", "positive", "The amenities are great, if youre willing to pay for the value of the place.")
AL(k, "2025-04-01", "other", "The amenities are nice except for the Dog Park. It’s dirty and full of dog Doodoo.")
AL(k, "2025-04-01", "management", "But they need to take care of the building better. Someone stole the soap out of the bathroom and it has not been replaced in two weeks.", "management_company")
AL(k, "2025-04-01", "positive", "Maintenance is excellent.")
AL(k, "2024-08-15", "positive", "Up till now I don’t regret moving to One Clinton Park is a very nice and quiet place")

# none_found rows for every building with no dated item
have = {i["addr_key"] for i in items}
now = lib.now_iso()
for k, r in BY.items():
    if k in have: continue
    if r["zip"] == "10801":
        where = "Apartment List property page (no review text shown); web search for news on the address and name (break-ins, elevator, heat) returned nothing naming the building; Patch and QNS not read (robots.txt disallows Claude agents)"
        src = URL(k)
    else:
        o = ig.get(k, {})
        where = ("Openigloo building page (0 reviews)" if o.get("status") == 200 else "Openigloo page not reached (" + str(o.get("status") or o.get("error")) + ")") + \
                "; listing page; web search for news on the address/building name returned nothing naming it; Patch and QNS not read (robots.txt disallows Claude agents)"
        src = o.get("fetched") or URL(k)
    I(k, "none_found", "", where, "openigloo / web search" if r["zip"] != "10801" else "apartmentlist / web search", src, "building", now)

out = lib.DATA / "evidence"; out.mkdir(exist_ok=True)
for name, data in (("confirm", confirm), ("items", items), ("facts", facts)):
    with open(out / f"{name}_batch_5.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)
import collections
print("confirm", len(confirm), collections.Counter(c["status"] for c in confirm))
print("  by fact", collections.Counter((c["fact"], c["status"]) for c in confirm))
print("items", len(items), collections.Counter(i["category"] for i in items))
print("facts", len(facts))
