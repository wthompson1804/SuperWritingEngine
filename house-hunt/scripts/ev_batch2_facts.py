"""Evidence batch 2: facts_batch_2.csv rows from the refreshed Apartment List listing objects plus hand-read pages."""
import csv, json, re, sys
sys.path.insert(0, "scripts")
from ev_batch2_add import add
import h_apartmentlist as al
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_2.csv")))
F = []
def cl(s): return re.sub(r"\s+", " ", str(s).replace("$$", "$")).strip()
for r in rows:
    u = r["urls"].split(" | ")[0].strip()
    if "apartmentlist" not in u: continue
    L = json.load(open("raw/evidence_batch2/al_%s.json" % u.rsplit("/", 1)[1]))["listing"]
    k = r["addr_key"]
    def f(fact, value, quote): F.append((k, fact, cl(value), cl(quote), u))
    if L.get("year_built"): f("year_built", L["year_built"], f"year_built: {L['year_built']}")
    if L.get("total_units_count"): f("total_units", L["total_units_count"], f"total_units_count: {L['total_units_count']}")
    if L.get("pmc_display_name"): f("management_company", L["pmc_display_name"], f"pmc_display_name: {L['pmc_display_name']}")
    if cl(L.get("parking_details_text") or ""): f("parking", cl(L["parking_details_text"]), cl(L["parking_details_text"]))
    pp = L.get("pet_policies") or {}
    for grp in ("dogs", "general"):
        g = pp.get(grp) or {}
        for fld, name in (("rent", "pet_rent"), ("fee", "pet_fee"), ("deposit", "pet_deposit"), ("limit", "pet_limit")):
            if cl(g.get(fld) or "") and cl(g.get(fld)) != "null":
                f(f"{name} ({grp})", cl(g[fld]), f"pet_policies.{grp}.{fld}: {cl(g[fld])}")
    if cl(L.get("additional_fees_text") or ""): f("additional_fees", cl(L["additional_fees_text"]), cl(L["additional_fees_text"]))
    if cl(L.get("utilities_included_text") or ""): f("utilities_included", cl(L["utilities_included_text"]), cl(L["utilities_included_text"]))
    if cl(L.get("storage_details_text") or ""): f("storage", cl(L["storage_details_text"]), cl(L["storage_details_text"]))
    am = list(dict.fromkeys(al.amen_names(L, "community_amenities") + al.amen_names(L, "unit_amenities")))
    for pat, name in ((r"^pool$", "pool"), (r"doorman", "doorman"), (r"concierge", "concierge"), (r"^garage$", "garage")):
        hit = [a for a in am if re.search(pat, a, re.I)]
        if hit: f(name, "yes (indoor/outdoor not stated)" if name == "pool" else "yes", "amenity list: " + ", ".join(hit))
    if L.get("website_url"): f("building_site", L["website_url"].split("?")[0], "website_url")
    if L.get("lease_terms_text"): f("lease_terms", cl(L["lease_terms_text"]), cl(L["lease_terms_text"]))
J = "https://www.gardencommunities.com/Properties/NJ/Bergen/The-Jefferson-Hackensack.aspx"; JP = "https://www.gardencommunities.com/CMSPages/GetFile.aspx?guid=92b3fa11-3aac-4f96-8b37-6d2cec922a51"
P = "https://www.gardencommunities.com/Properties/NJ/Morris/Pondview-Estates.aspx"
B = "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/"
HY = "https://www.harrisonyards.com/amenities.aspx"; AV = "https://avivajc.com/faq"
Q = "https://www.greystar.com/the-quincy-new-brunswick-nj/p_17425"; G = "https://www.greystar.com/the-grand-west-new-york-nj/p_22449"; PQ = "https://www.greystar.com/500-parq-parisppany-nj/p_20984"
ZC = "https://www.zumper.com/apartment-buildings/p1647219/clinton-flats-newark-central-business-district-newark-nj"; ZP = "https://www.zumper.com/listings/30002373p/1-bedroom-north-bergen-nj"
k = "2 kinderkamack rd|07601"
F += [(k, "parking", "indoor garage; $100/month first car, $75 second, $200 third", "Parking: $100/month for first car, $75/month for second car, $200/month for third car, subject to availability", JP),
      (k, "pet_rent", "$50/month for 1 pet; $75 for 2", "Pet Rent: $50/month for 1 pet $75/month for 2 pets", JP), (k, "pet_fee", "$500 one-time first pet; $750 second", "Pet Fee: $500 one-time non-refundable for first pet", JP),
      (k, "required_monthly_fees", "no amenity fee", "Amenity Fee: No amenity fees", JP), (k, "utilities", "gas/electric and water/sewer paid by resident", "Water/Sewer: Conservice - monthly charge paid directly to service provider by resident", JP),
      (k, "pool", "outdoor, heated", "Heated Outdoor Pool & Sundecks with Outdoor Kitchen, BBQs & Outdoor Dining Areas", J), (k, "concierge", "yes", "Concierge-Attended Lobby", J),
      (k, "management_company", "Garden Communities", "listing is on gardencommunities.com", J), (k, "concession", "up to 3 months free plus $1,000 credit on select apartments", "Up to 3 months free plus a $1000 move-in credit. All offers are on select apartments and lease terms may vary.", J),
      (k, "security_deposit", "half a month's rent", "Security Deposit: 1/2 month's rent", JP)]
k = "100 julia dr|07885"
F += [(k, "pool", "outdoor (Olympic-size heated saltwater) and indoor saltwater", "there's an Olympic-size heated saltwater pool ... spa facilities that include an indoor saltwater pool, saunas, a yoga studio", P),
      (k, "required_monthly_fees", "no amenity fee", "No Amenity Fees", P), (k, "management_company", "Garden Communities", "listing is on gardencommunities.com", P),
      (k, "concession", "up to two months free on a 26-month lease plus $1,500 credit, select apartments", "Up to two months free on a new 26-month lease plus a $1500 move-in credit on select apartments for a limited time.", P)]
k = "20 beacon way|07304"
F += [(k, "pool", "indoor, with hot tub", "Indoor Pool & Hot Tub", B), (k, "management_company", "Building and Land Technology (BLT)", "listing is on bltliveworkplay.com", B), (k, "shuttle", "free shuttle", "Free Shuttle Service", B)]
k = "600 frank e rodgers blvd s|07029"
F += [(k, "parking", "surface lot $225; covered lot $250; assigned", "Parking Type: Surface Lot Parking Parking Fee: 225 ... Parking Type: Covered Lot Parking Parking Fee: 250", HY), (k, "pet_rent", "$65 per pet", "$65 pet rent monthly per pet", HY), (k, "pet_fee", "$500 one-time per pet", "$500 one-time fee per pet", HY),
      (k, "concierge", "yes", "Concierge services", HY), (k, "management_company", "Greystar (site footer links to greystar.com)", "greystar.com links in site footer", "https://www.harrisonyards.com/")]
k = "2935 john f kennedy blvd|07306"
F += [(k, "pet_rent", "$65 monthly", "Upfront $500 non-refundable pet fee and a $65 monthly dog rent and a $65 monthly cat rent.", "https://www.threejournalsquare.com/features.aspx"), (k, "concession", "up to $2,000 off studios and 1BRs", "3 Journal Square now offering up to $2000 off for studio and 1-bedroom units.", "https://www.threejournalsquare.com/features.aspx"),
      (k, "management_company", "Greystar (site footer links to greystar.com)", "greystar.com links in site footer", "https://www.threejournalsquare.com/"), (k, "concierge", "24/7", "24/7 Concierge", "https://www.threejournalsquare.com/features.aspx")]
k = "189 phillip st|07305"
F += [(k, "parking", "on-site garage, 150 spaces, $275/month", "AVIVA offers an on-site parking garage with 150 parking spaces and EV charging stations. Parking is available for $275 per month", AV), (k, "pet_rent", "$55 per pet", "There is a one-time non-refundable pet fee of $600 per pet and monthly pet rent of $55 per pet.", AV),
      (k, "pool", "rooftop (outdoor)", "Our rooftop pool, sky lounge, communal kitchen, and outdoor gathering spaces", AV), (k, "concierge", "24-hour", "AVIVA offers 24-hour concierge service", AV)]
k = "100 park plaza dr|07094"
F += [(k, "management_company", "Greystar (site footer links to greystar.com)", "greystar.com links in site footer", "https://www.theharperapts.com/"), (k, "pool", "yes (outdoor implied: 'with Lounge Chairs')", "Swimming Pool with Lounge Chairs", "https://www.theharperapts.com/amenities/")]
k = "89 monitor st|07304"
F += [(k, "pool", "rooftop (outdoor)", "Rooftop Terrace With Pool", "https://thehazeljc.com/page/amenities.php")]
k = "270 johnston ave|07304"
F += [(k, "pool", "rooftop (outdoor)", "Rooftop Pool", "https://www.atlasjc.com/amenities"), (k, "concession", "2 months free on select homes; rents shown are net-effective", "*2 Month Free on select apartment homes Specials vary based on the lease term. Rents reflect net-effective pricing.", "https://www.atlasjc.com/amenities")]
k = "65 maple st|07304"
F += [(k, "price_basis", "rents shown are net-effective, including concessions", "Rents reflect net-effective pricing inclusive of concessions.", "https://www.solarislofts.com/faq/")]
k = "1100 s 5th st|07029"
F += [(k, "parking", "on-site covered", "On-Site Covered Parking", "https://www.thewyldes.com/amenities"), (k, "pool", "outdoor (courtyard infinity pool)", "Resort Style, Infinity Edge Pool with In-water Chaise Lounges", "https://www.thewyldes.com/amenities"), (k, "management_company", "Bozzuto (site links to BozzutoResidents.com)", "BozzutoResidents.com link", "https://www.thewyldes.com/")]
k = "49 fisk st|07305"
F += [(k, "parking", "indoor garage, extra fee", "Indoor Parking Garage with Electric Vehicle Charging Available*", "https://www.birchhousejc.com/amenities"), (k, "concierge", "daytime only", "Day Time Concierge", "https://www.birchhousejc.com/amenities"), (k, "management_company", "Bozzuto (site links to MyBozzuto.com)", "MyBozzuto.com link", "https://www.birchhousejc.com/"), (k, "shuttle", "to Journal Square PATH", "Shuttle to Journal Square PATH Station", "https://www.birchhousejc.com/amenities")]
for k, s, park, trash in (("120 neilson st|08901", Q, "Parking $195 monthly", "Trash Services - Doorstep $35 monthly (required)"), ("508 51st st|07093", G, "Parking - Garage $200 monthly", "Trash Services - Hauling $25 monthly (required)"), ("500 parq ln|07054", PQ, "Parking $150 monthly", "Trash Services - Hauling $15 monthly (required)")):
    F += [(k, "parking", park, "fee table: " + park, s), (k, "required_monthly_fees", trash, "fee table: " + trash, s), (k, "pet_rent", "$65 monthly", "fee table: Pet Rent 65 monthly", s), (k, "management_company", "Greystar", "listing is on greystar.com", s)]
F += [("120 neilson st|08901", "pool", "yes (cabanas: outdoor implied)", "Swimming Pool w/Cabanas", Q), ("500 parq ln|07054", "pool", "outdoor", "Sparkling pool & sun deck", PQ), ("500 parq ln|07054", "building_floors", "6", "Our six-story architectural design", PQ), ("120 neilson st|08901", "pet_fee", "$500 one-time", "fee table: Pet Fee 500 one_time", Q), ("508 51st st|07093", "pet_fee", "$500 one-time", "fee table: Pet Fee 500 one_time", G), ("500 parq ln|07054", "pet_fee", "$600 one-time", "fee table: Pet Fee 600 one_time", PQ)]
k = "30 clinton st newark nj 07102 usa|07102"
F += [(k, "pet_rent", "$50 monthly", "Tenant will pay an additional $50.00 Pet Fee every month", ZC), (k, "pet_deposit", "$500", "An additional $50.00 monthly pet fee and an additional $500.00 pet deposit are required when applicable.", ZC), (k, "building_size", "30 Clinton has 20 studio and one-bedroom apartments", "30 Clinton offers 20 studio and one-bedroom apartments", ZC)]
k = "9060 palisade ave d710 n bergen nj 07047 usa|07047"
F += [(k, "pool", "outdoor", "an outdoor swimming pool, fitness facilities, an elevator, and a community room", ZP), (k, "doorman", "yes", "Services: Door Attendant", ZP), (k, "parking", "garage; availability to be confirmed", "Parking availability can be confirmed during the leasing process.", ZP), (k, "listing_type", "condo unit", "1 Bedroom Condo for $1,699/month", ZP)]
AO = "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge"
for k, u in (("900 forest park ln 9206|08857", "9206"), ("900 forest park ln 9204|08857", "9204")):
    F += [(k, "required_monthly_fees", "Technology Connect $109 (internet + basic cable)", "fee list: Technology Connect $109 Monthly, not optional; 'AvalonConnect ... high-speed internet and basic cable TV package ... bundled with your monthly rent'", AO + f"/apartment/NJ032-NJ032-009-{u}"),
          (k, "pet_rent", "$60 monthly per dog", "fee list: Pet Dog Fee $60 Monthly", AO + f"/apartment/NJ032-NJ032-009-{u}"), (k, "parking", "$15 to $260 monthly (optional)", "fee list: Parking $15-$260 Monthly, optional", AO + f"/apartment/NJ032-NJ032-009-{u}"), (k, "management_company", "AvalonBay Communities", "listing is on avaloncommunities.com", AO)]
k = "200 boyden ave|07040"
F += [(k, "required_monthly_fees", "$89 (total price minus base rent)", "unit 324: price 2590, totalPrice 2679; unit 436: price 2710, totalPrice 2799", "https://www.avaloncommunities.com/new-jersey/maplewood-apartments/avalon-maplewood")]
add("facts", F)
