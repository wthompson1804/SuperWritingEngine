#!/usr/bin/env python3
"""Manual addition: Envy by Gomes, 58-84 Norfolk St, Newark NJ 07103 (Will's screenshot, 2026-11-15).

Sources (all cached in raw/manual_envy/ by lib.cached_get; pass --refresh to refetch):
  - bygomes.com/property/envy/ (building's own site, Gatsby; per-unit page-data.json carries the RentCafe feed values)
  - trulia.com building page (full unit table, pet policy, elevator, unit count)
  - jerseydigs.com articles (opening date, floors, parking count)
  - Census geocoder
Blocked, not worked around: securecafe.com (Cloudflare challenge on robots.txt), rentcafe.com (403), bbb.org (challenge).
Writes data/listings_raw/manual.csv, data/reference/manual_buildings.csv and data/evidence/*_batch_manual.csv.
Idempotent: rows are keyed by listing_id; first_seen is kept from an existing file.
Also reads the inbox/ drop box (scripts/h_inbox.py -> data/listings_raw/manual_inbox.csv); `--inbox` runs only that.
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from lib import DATA, ROOT, cached_get  # noqa: E402

lib.DEFAULT_DELAY = 3.0
SRC = "manual_envy"
REFRESH = "--refresh" in sys.argv
NOTE = "added at Will's request 2026-11-15 (screenshot)"
ADDR_KEY = "58 norfolk st|07103"
NAME = "Envy by Gomes"

OWN = "https://bygomes.com/property/envy/"
TRULIA = "https://www.trulia.com/building/envy-by-gomes-58-norfolk-st-newark-nj-07103-2734055214"
JD_OPEN = "https://jerseydigs.com/envy-by-gomes-newark-launch/"
JD_PROP = "https://jerseydigs.com/gomes-group-proposes-165-unit-mixed-use-project-in-university-heights-newark/"
JD_PEDRO = "https://jerseydigs.com/pedro-gomes-newark-developer/"
TEAM = "https://bygomes.com/team/"
BBB = "https://www.bbb.org/us/nj/newark/profile/property-management/gomes-group-llc-0221-90224700"
GEO = ("https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=58+Norfolk+St,+Newark,+NJ+07103"
       "&benchmark=Public_AR_Current&format=json")

COLS = ("listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,unit,"
        "beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,dog_policy_text,"
        "dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,other_monthly_fees_json,"
        "utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,building_url,raw_path,notes").split(",")

DOG_TEXT = ("Trulia building page: 'Dogs Allowed 2 pet max 35 lbs max weight $50 monthly pet fee $500 One-time pet fee | "
            "Restrictions: Size and breed restrictions.' Own site has no pet policy text (only 'Pet Washing Station').")
CONCESSION = ("Own site: '* PRICE INCLUDES CONCESSIONS.' Trulia: 'Special Offer 1 - 2 Months Free on selected units*'")
FEES = json.dumps({"amenity_fee": "Contact for details (Trulia 'Required monthly rent & fees')",
                   "application_fee": "Contact for details", "security_deposit": "Contact for details",
                   "one_time_pet_fee": 500, "lease_terms_months": "12-24 (Trulia)"})


def get(url, ext="html"):
    c, m = cached_get(url, SRC, ext=ext, refresh=REFRESH, retries=1)
    return c.decode("utf8", "ignore"), m


def floor_of(unit):
    if unit.upper().startswith("G"):
        return "0"
    return unit[0] if unit[:1].isdigit() else "unknown"


def main():
    geo, _ = get(GEO, "json")
    xy = json.loads(geo)["result"]["addressMatches"][0]["coordinates"]
    lat, lon = round(xy["y"], 6), round(xy["x"], 6)

    # --- Trulia unit table (all available units, with sqft) ---
    th, tm = get(TRULIA)
    nd = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', th, re.S).group(1))
    tunits = {}

    def walk(o):
        if isinstance(o, dict):
            if "pricePeriodRange" in o and str(o.get("name", "")).startswith("Unit "):
                tunits[o["name"][5:]] = o
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(nd)
    tphoto = (re.search(r'property="og:image" content="([^"]+)"', th) or [None, ""])[1]

    # --- Own site: unit links on the property page, then each unit's page-data.json ---
    oh, om = get(OWN)
    own = {}
    for u in sorted(set(re.findall(r'href="/property/envy/([A-Za-z0-9]+)/"', oh))):
        if u in ("coworking", "news"):
            continue
        get(f"{OWN}{u}/")  # the human-readable unit page (cached as proof)
        pj, pm = get(f"https://bygomes.com/page-data/property/envy/{u}/page-data.json", "json")
        own[u] = (json.loads(pj)["result"]["data"]["unit"]["data"], pm)

    old = {}
    out_path = DATA / "listings_raw" / "manual.csv"
    if out_path.exists():
        old = {r["listing_id"]: r for r in csv.DictReader(open(out_path, newline=""))}

    rows = []
    for unit in sorted(set(tunits) | set(own)):
        t = tunits.get(unit)
        o = own.get(unit)
        beds_txt = (o[0]["apt_type"] if o else t["bedrooms"]["formattedValue"])
        if not re.match(r"\s*(1 Bed|1bd|Studio|0)", beds_txt):
            continue  # 2BRs are out of scope
        beds = 0 if "tudio" in beds_txt else 1
        sqft = t["floorSpace"]["max"] if t else ""
        t_price = int(re.sub(r"\D", "", t["pricePeriodRange"]["formattedPrice"])) if t else None
        t_avail = ("now" if t["isAvailableNow"] else (t.get("availabilityDate") or "")[:10]) if t else ""
        notes = [NOTE]
        if o:
            d, pm = o
            av = d["availability"]
            mm, dd, yy = av["availableDate"].split("/")
            iso = f"{yy}-{mm}-{dd}"
            is_now = av["daysUntilAvailable"] <= 0
            rent = av["maxPrice"]  # the figure the page displays ("STARTING AT $x /MONTH *")
            src, url, level, seen, raw = "bygomes.com", f"{OWN}{unit}/", "detail", pm["retrieved_at"], pm["path"]
            basis = ("net-effective: own site footnote '* PRICE INCLUDES CONCESSIONS'; gross rent not shown; "
                     f"feed minPrice {av['minPrice']} maxPrice {av['maxPrice']}")
            avail_text = "AVAILABLE NOW" if is_now else f"AVAILABLE {av['availableDate']}"
            avail = "now" if is_now else iso
            photo = d["banner_images"][0]["image"]["url"] if d.get("banner_images") else tphoto
            floor = {"Ground Floor": "0"}.get(d["floor"], re.sub(r"\D", "", d["floor"]) or "unknown")
            notes.append(f"own-site floor field: '{d['floor']}'")
            if t:
                notes.append(f"sqft from Trulia building page; Trulia shows ${t_price:,}/mo, {t['availabilityText']}")
                if t_price != rent:
                    notes.append("PRICE DIFFERS between own site and Trulia")
            else:
                notes.append("not on Trulia unit table; sqft unknown")
        else:
            src, url, level, seen, raw = "trulia", TRULIA, "building_unit", tm["retrieved_at"], tm["path"]
            rent, avail, avail_text, photo = t_price, t_avail, t["availabilityText"], tphoto
            basis = ("Trulia: 'Prices shown are base rent'; but own site says its prices include concessions and Trulia "
                     "matches own-site prices on shared units, so likely net-effective; gross unknown")
            floor = floor_of(unit)
            notes.append("unit not shown on the building's own site (it lists 6 units); price, date, sqft from Trulia "
                         "building page; floor derived from unit number")
        if floor == "0":
            notes.append("GROUND FLOOR unit")
        if floor == "1":
            notes.append("1xx unit: building also has a G level, so whether floor 1 is at street level is unconfirmed")
        lid = f"manual:envy:{unit}"
        rows.append(dict(
            listing_id=lid, source_site=src, url=url, detail_level=level,
            first_seen=old.get(lid, {}).get("first_seen") or seen, last_seen=seen,
            building_name=NAME, address="58 Norfolk St", city="Newark", state="NJ", zip="07103", lat=lat, lon=lon,
            unit=unit, beds=beds, baths=1, sqft=sqft, listed_rent=rent, price_basis=basis, concession_text=CONCESSION,
            available_date_text=avail_text, available_date=avail, dogs="yes", dog_policy_text=DOG_TEXT,
            dog_weight_limit_lb=35, elevator="yes", floor=floor, building_floors=6,
            parking_type="Reserved Indoor Parking Space (own site); Trulia: Garage, Garage Lot, Surface Lot, Off Street Parking",
            parking_fee="", pet_rent=50, other_monthly_fees_json=FEES,
            utilities_included="'utilities included in every residence' (own site; which utilities not specified)",
            laundry="in_unit", listing_type="managed_building", manager="Gomes Group LLC (Gomes Management)",
            listing_age_days="", photo_url=photo, building_url=OWN, raw_path=raw, notes="; ".join(notes)))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"manual.csv: {len(rows)} rows")
    for r in rows:
        print(" ", r["unit"], r["source_site"], r["listed_rent"], r["available_date"], "floor", r["floor"], r["sqft"])

    write_building(lat, lon, om["retrieved_at"], tm["retrieved_at"])
    write_evidence(rows, tunits, own, om, tm)


def write_building(lat, lon, own_at, tr_at):
    F = [  # fact, value, quote, source_url
        ("building_name", NAME, "Envy by Gomes | Newark, New Jersey", OWN),
        ("address", "58-84 Norfolk St, Newark, NJ 07103", "58-84 Norfolk St, Newark, NJ 07103", OWN),
        ("lat_lon", f"{lat},{lon}", "matchedAddress: 58 NORFOLK ST, NEWARK, NJ, 07103", GEO),
        ("building_site", OWN, "envybygomes.com redirects to bygomes.com/property/envy/", OWN),
        ("contact", "973 330 8859; envy@bygomes.com; contact form at the foot of the building page",
         "973 330 8859 ENVY@BYGOMES.COM 58-84 Norfolk St, Newark, NJ 07103", OWN),
        ("management_company", "Gomes Group LLC (in-house: Gomes Management); developer Gomes Group, CEO Pedro Gomes",
         "Property Manager Gomes Group LLC (862) 397-7730 Verified source", TRULIA),
        ("management_company_about", "Gomes Group, since 2005; includes Gomes Management",
         "With a history dating back to 2005, Gomes Group began as a real estate investment firm, including Gomes Consulting, Gomes Management, and Gomes & Gomes Development.", TEAM),
        ("management_since", "opening (June 2023); developer-managed, no management change found",
         "Learn more about Envy By Gomes, which will begin leasing later this month.", JD_OPEN),
        ("year_built", "2023 (opened June 2023)", "A free festival called EnvyNewark will kick off the Envy By Gomes' reveal on June 10 [2023]", JD_OPEN),
        ("unit_count", "165", "totalUnitsInBuilding: 165 (page data); 2021 proposal: 'around 165 residential units'", TRULIA),
        ("floors", "6 on Norfolk St side, 5 on Newark St side (2021 site-plan notice); unit numbers G, 1xx-5xx",
         "The development is listed as being five stories tall on its Newark Street side and six stories tall on the Norfolk Street side.", JD_PROP),
        ("elevator", "yes", "Levels, Entrance, & Accessibility Elevator Gated Entry", TRULIA),
        ("dogs_allowed", "yes", "Dogs Allowed 2 pet max 35 lbs max weight", TRULIA),
        ("dog_weight_limit_lb", "35", "Weight limit (lbs.) 35", TRULIA),
        ("dog_breed_rules", "size and breed restrictions (list not published)", "Restrictions: Size and breed restrictions.", TRULIA),
        ("pet_rent", "$50/month per dog", "Monthly dog rent $50/mo", TRULIA),
        ("pet_fee_one_time", "$500", "One-time fee $500", TRULIA),
        ("pet_policy_own_site", "not_found (own site has no pet policy page; only amenity mentions)",
         "At Envy, even your pets enjoy the finer things. ... Pet Washing Station", OWN),
        ("parking_type", "reserved indoor (garage); 34 spaces planned for 165 units", "Reserved Indoor Parking Space", OWN),
        ("parking_spaces", "34 (2021 proposal)", "The building is also slated to include 34 parking spaces", JD_PROP),
        ("parking_fee", "not_found (own site, Trulia)", "", OWN),
        ("required_monthly_fees", "amenity fee exists, amount not published", "Required monthly rent & fees ... Amenity fee Contact for details", TRULIA),
        ("utilities_included", "yes per own site; which utilities not specified", "state-of-the-art security, custom storage options, and utilities included in every residence", OWN),
        ("lease_terms", "12 to 24 months", "Lease Term: 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24", TRULIA),
        ("concession", "1-2 months free on selected units; own-site prices are net of concessions",
         "* PRICE INCLUDES CONCESSIONS.", OWN),
        ("concession_trulia", "1 - 2 Months Free on selected units*", "Special Offer 1 - 2 Months Free on selected units*", TRULIA),
        ("price_basis", "net-effective on own site; gross rent not published", "* PRICE INCLUDES CONCESSIONS.", OWN),
        ("pool", "none listed (own site amenities, Trulia)", "", OWN),
        ("gym", "yes", "Our gym is outfitted with state of the art equipment, MIRROR Technology by Lululemon, and space to stretch.", OWN),
        ("coworking", "yes: ENVY CoWork, also sold to the public from $200/month",
         "Envy Co-Work, open to residents and the public for a fee, that includes a modern gym, private offices, lounges, and a luxurious terrace", JD_OPEN),
        ("doorman_concierge", "none listed; Trulia lists 'Night Patrol'", "Security Night Patrol", TRULIA),
        ("controlled_access", "yes", "Remote Entry Access and Smart Door Locks", OWN),
        ("package_room", "yes", "Secured Package System by Package Concierge", OWN),
        ("roof_deck", "yes", "Our rooftop was created for residents to rest, relax, socialize, and celebrate", OWN),
        ("dog_amenities", "pet washing station; no dog run listed", "Pet Washing Station", OWN),
        ("in_unit_laundry", "yes", "In-unit washer and dryer.", OWN + "G02/"),
        ("other_amenities", "zen garden, cafe, club room and movie screening, EV charging, bicycle storage",
         "Electric Vehicle Charging Capabilities - Club Room & Movie Screening ... Bicycle Storage", OWN),
    ]
    p = DATA / "reference" / "manual_buildings.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["addr_key", "building_name", "fact", "value", "quote", "source_url", "retrieved_at"])
        for fact, val, quote, url in F:
            w.writerow([ADDR_KEY, NAME, fact, val, quote, url, tr_at if "trulia" in url else own_at])
    print(f"manual_buildings.csv: {len(F)} facts")
    # facts_batch_manual.csv (evidence brief section 4) reuses the same facts
    ev = DATA / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    with open(ev / "facts_batch_manual.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["addr_key", "fact", "value", "quote", "source_url"])
        for fact, val, quote, url in F:
            w.writerow([ADDR_KEY, fact, val, quote, url])


def write_evidence(rows, tunits, own, om, tm):
    ev = DATA / "evidence"
    now = lib.now_iso()
    with open(ev / "live_check_batch_manual.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow("addr_key,listing_url,unit,status,price_now,available_now_text,matches_stored,building_site_url,checked_at,notes".split(","))
        for r in rows:
            u = r["unit"]
            t = tunits.get(u)
            tp = t["pricePeriodRange"]["formattedPrice"] if t else "not listed"
            agree = "n/a (single source)"
            if u in own and t:
                agree = "yes" if int(re.sub(r"\D", "", tp)) == r["listed_rent"] else "no"
            w.writerow([ADDR_KEY, r["url"], u, "live", r["listed_rent"], r["available_date_text"],
                        "n/a (first capture; no stored value)", OWN, r["last_seen"],
                        f"own site and Trulia agree on price: {agree}; Trulia {tp}"
                        + (f", {t['availabilityText']}" if t else "")
                        + ("; unit absent from own site's 6-unit list" if u not in own else "")])
        w.writerow([ADDR_KEY, "https://envy-by-gomes-rentcafewebsite.securecafe.com/onlineleasing/envy-by-gomes/", "",
                    "blocked", "", "", "", OWN, now,
                    "RentCafe/securecafe leasing portal (the Apply link): Cloudflare challenge on robots.txt (403); rentcafe.com property page 403. Not worked around."])
    C = [
        ("elevator", "yes", "Levels, Entrance, & Accessibility Elevator Gated Entry", TRULIA, "confirmed"),
        ("elevator", "implied", "the design flows smoothly through hallways and elevators (Pedro Gomes on Gomes buildings generally)",
         "https://www.brilliant.tech/blogs/news/gomes-group-transforming-newark-with-community-and-smart-living", "unconfirmed"),
        ("building_floors", "6 (Norfolk side) / 5 (Newark St side)",
         "The development is listed as being five stories tall on its Newark Street side and six stories tall on the Norfolk Street side.", JD_PROP, "confirmed"),
        ("dogs_allowed", "yes", "Dogs Allowed 2 pet max 35 lbs max weight $50 monthly pet fee $500 One-time pet fee", TRULIA, "confirmed"),
        ("dog_weight_limit", "35", "Weight limit (lbs.) 35", TRULIA, "confirmed"),
        ("dog_weight_limit", "not stated on own site", "At Envy, even your pets enjoy the finer things.", OWN, "unconfirmed"),
    ]
    for r in rows:
        u = r["unit"]
        if u in own:
            C.append(("floor", f"unit {u}: {own[u][0]['floor']}", f"floor = {own[u][0]['floor']} (unit page data)",
                      f"https://bygomes.com/page-data/property/envy/{u}/page-data.json", "confirmed"))
        else:
            C.append(("floor", f"unit {u}: {r['floor']} (from unit number)", f"Unit {u}", TRULIA, "unconfirmed"))
    with open(ev / "confirm_batch_manual.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["addr_key", "fact", "value", "quote", "source_url", "status"])
        for c in C:
            w.writerow([ADDR_KEY, *c])
    I = [
        ("other", "2025-12-19",
         "Gomes walked from Norfolk Street down Sussex Avenue, and even in the morning, there was a crowd of day-drinkers gathered outside the liquor store. The sign on the shop reads, Please remove ski masks and hoods before entering.",
         "jerseydigs.com", JD_PEDRO, "street"),
        ("positive", "2025-12-19",
         "he plans to convert an empty lot into a dog park, and he is teaming up with NJ Transit to renovate Norfolk Avenue Station. He also successfully lobbied to get a police substation inside his company's headquarters on Sussex Avenue.",
         "jerseydigs.com", JD_PEDRO, "management_company"),
        ("other", "2023-06-02",
         "Gomes Group is set to unveil the new rental building Envy By Gomes [sponsored article]; Learn more about Envy By Gomes, which will begin leasing later this month.",
         "jerseydigs.com", JD_OPEN, "building"),
        ("none_found", "", "No tenant reviews of the building on its Trulia building page (page has no review section; its FAQ covers the neighborhood only).",
         "trulia", TRULIA, "building"),
        ("none_found", "", "No Zumper or Apartment List page for the building found (web search; apartmentlist.com/nj/newark/envy-by-gomes is a soft 404).",
         "search", "https://www.apartmentlist.com/nj/newark/envy-by-gomes", "building"),
        ("none_found", "", "BBB profile for Gomes Group LLC exists but is behind a bot challenge (403); not read. Rating and complaint count not recorded (only seen in a search snippet).",
         "bbb.org", BBB, "management_company"),
        ("none_found", "", "No news of car crime, elevator outages, incidents or tenant complaints at 58-84 Norfolk St found in web searches (building name, address, Gomes Group + complaints/lawsuit/shooting/fire/break-ins; Newark police + Norfolk Street 2026).",
         "search", OWN, "building"),
    ]
    with open(ev / "items_batch_manual.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow("addr_key,building_name,category,item_date,excerpt,source_site,source_url,about,retrieved_at".split(","))
        for cat, date, ex, site, url, about in I:
            w.writerow([ADDR_KEY, NAME, cat, date, ex, site, url, about, now])
    print("evidence files written")


if __name__ == "__main__":
    # The drop box (inbox/, docs/TRAWL_2_PLAN.md step 5) lives in h_inbox.py and writes its own file,
    # data/listings_raw/manual_inbox.csv; the Envy rows above are unchanged. --inbox runs only the drop box.
    if "--inbox" not in sys.argv:
        main()
    import h_inbox  # noqa: E402
    h_inbox.run()
