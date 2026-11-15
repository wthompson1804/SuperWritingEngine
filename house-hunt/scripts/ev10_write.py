"""Evidence batch 10: rebuild data/evidence/{live_check,confirm,items,facts,ratings}_batch_10.csv from the pages
cached in raw/evidence_b10/. No network: every page is read with cached_get (cache hit). Idempotent.
Run from the project root: python3 scripts/ev10_write.py   (add -v to list every quote that fails the verbatim check)"""
import csv, json, re, sys, html as H, datetime
sys.path.insert(0, "scripts")
import lib, h_apartmentlist as A

SRC = "evidence_b10"
TODAY = datetime.date(2026, 11, 15)
RUN_AT = "2026-11-15T21:40:00+00:00"   # time of the news searches (search log rows)
BATCH = list(csv.DictReader(open("data/reference/evidence_batches/batch_10.csv")))
NAME = {r["addr_key"]: r["building_name"] for r in BATCH}

_pg = {}
def page(u):
    if u not in _pg:
        c, m = lib.cached_get(u, SRC, ext="html")
        _pg[u] = (c.decode("utf8", "replace"), m["retrieved_at"])
    return _pg[u]
def at(u): return page(u)[1]
def norm(s): return re.sub(r"\s+", " ", H.unescape(s)).strip()
def text_of(t):
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    return norm(re.sub(r"(?s)<[^>]+>", " ", t))
_tx = {}
def haystack(u):
    if u not in _tx:
        raw = page(u)[0]
        j = raw.replace("\\u0026", "&").replace("\\u2019", "’").replace('\\"', '"').replace("\\n", " ")
        _tx[u] = text_of(raw) + " || " + norm(j)
    return _tx[u]
BAD = []
def chk(u, quote):
    """Each ' / '-separated part of a quote must appear verbatim in the cached page."""
    if not u.startswith("http") or not quote or quote.startswith("["): return
    for part in quote.split(" / "):
        if norm(part) not in haystack(u): BAD.append((u, part))

# ---------------------------------------------------------------- short names
AL = "https://www.apartmentlist.com"; TR = "https://www.trulia.com"; ZU = "https://www.zumper.com"
U = {
 "sofi": AL + "/nj/south-orange/sofi-gaslight-commons--1", "high": AL + "/nj/south-plainfield/the-highlands-at-south-plainfield",
 "cove": AL + "/nj/westfield/the-cove", "manley": AL + "/nj/summit/manley-court", "avalon": AL + "/nj/lincoln-park/avalon-wayne",
 "wlb": TR + "/building/the-village-at-west-long-branch-apartments-10-avalon-ct-west-long-branch-nj-07764-1008633317",
 "modera": AL + "/nj/woodbridge/modera-woodbridge", "georgian": AL + "/nj/iselin/georgian-arms",
 "pine": AL + "/ny/coram/the-point-at-pine-ridge", "renbay": AL + "/ny/patchogue/renaissance-bay",
 "parkside": TR + "/building/parkside-at-the-harbors-2100-round-pointe-dr-haverstraw-ny-10927-1002377678",
 "admirals": TR + "/building/admirals-cove-1100-admirals-cove-blvd-haverstraw-ny-10927-2751292880",
 "riverside": TR + "/building/riverside-4100-southernly-pointe-dr-haverstraw-ny-10927-1150442698",
 "fulton": TR + "/home/316-fulton-ave-4-hempstead-ny-11550-2068681120",
 "midisland": TR + "/building/mid-island-apartments-35-penataquit-ave-bay-shore-ny-11706-1001914921",
 "renhills": AL + "/ny/hauppauge/renaissance-hills",
 "lagrange": "https://www.zillow.com/apartments/poughkeepsie-ny/lagrange-farms/CkQ7qY/",
 "brompton": TR + "/building/the-brompton-1880-palmer-ave-larchmont-ny-10538-2739683824",
 "riv310": TR + "/home/310-riverside-blvd-6j-long-beach-ny-11561-2056770238",
 "bway25": TR + "/home/25-w-broadway-204-long-beach-ny-11561-2069636201",
 "promenade": TR + "/building/the-promenade-at-lynbrook-5-freer-st-lynbrook-ny-11563-2750930060",
 "northct": "https://www.zillow.com/apartments/middletown-ny/the-north-court-apartments/9VnZc7/",
 "sterling": TR + "/building/sterling-parc-at-middletown-23-james-p-kelly-way-middletown-ny-10940-1002205200",
 "main142": TR + "/home/142-main-st-4a-mineola-ny-11501-2102586359",
 "broad42": TR + "/building/42-broad-42-broad-st-w-mount-vernon-ny-10552-2750793491",
 "trail": "https://www.zillow.com/apartments/new-paltz-ny/trail-link-collective/CqLF7Y/",
 "alary": TR + "/building/the-alary-33-westchester-pl-new-rochelle-ny-10801-2756501402",
 "skyline": TR + "/building/skyline-new-rochelle-40-memorial-hwy-new-rochelle-ny-10801-1001780778",
 "arc": TR + "/building/arc-house-64-centre-ave-new-rochelle-ny-10801-2757148131",
}
K = {}
for r in BATCH:
    for a, u in U.items():
        if u in r["urls"]: K[a] = r["addr_key"]
assert len(K) == 29, len(K)
ZP = json.load(open("raw/evidence_b10/zumper_bld.json"))
def zu(a): return ZP[K[a]]["url"]

# own sites and other pages read
O = {
 "sofi": "https://www.sofigaslightcommons.com/", "sofi_pet": "https://www.sofigaslightcommons.com/apartments/nj/south-orange/pet-friendly",
 "sofi_am": "https://www.sofigaslightcommons.com/apartments/nj/south-orange/amenities",
 "cove": "https://www.oxfordrealtygroup.com/communities/the-cove/",
 "avalon": "https://www.avaloncommunities.com/new-jersey/wayne-apartments/avalon-wayne/",
 "av224": "https://www.avaloncommunities.com/new-jersey/wayne-apartments/avalon-wayne/apartment/NJ036-NJ036-00B-224",
 "av308": "https://www.avaloncommunities.com/new-jersey/wayne-apartments/avalon-wayne/apartment/NJ036-NJ036-00B-308",
 "renbay": "https://renaissancebay.com/", "renhills": "https://renhills.com/", "renhills_am": "https://renhills.com/amenities/",
 "parkside": "https://gdcrentals.com/parkside/", "riverside": "https://gdcrentals.com/riverside/", "admirals": "https://gdcrentals.com/admirals-cove/",
 "sterling": "https://sterlingparcny.com/", "sterling_pet": "https://sterlingparcny.com/pets/",
 "broad42": "https://www.42broad.com/", "arc": "https://www.archousenr.com/", "arc_faq": "https://www.archousenr.com/faq",
 "arc_av": "https://www.archousenr.com/availability", "arc_am": "https://www.archousenr.com/amenities",
 "brompton": "https://www.delaurentismanagement.com/copy-of-the-apuovia", "lagrange": "https://www.lagrangefarms.com/",
 "loop": "https://larchmontloop.com/larchmont-cops-bust-picky-porch-pirate/",
 "herald1": "https://www.liherald.com/merrick/stories/residential-rental-development-switches-ownership,146760",
 "herald2": "https://www.liherald.com/merrick/stories/cornerstone-at-yorkshire-apartment-complex-replaces-much-maligned-motel-in-lynbrook,137938",
 "yimby_alary": "https://newyorkyimby.com/2025/03/the-alary-nears-completion-at-33-westchester-place-in-new-rochelle.html",
 "yimby_42": "https://newyorkyimby.com/2023/07/developers-reveal-completed-249-unit-passive-house-building-at-42-west-broad-street-in-mount-vernon.html",
 "rj": "https://riverjournalonline.com/news/admirals-cove-luxury-resort-style-community-opens-in-haverstraw/73513/",
 "petition": "https://www.change.org/p/upgrade-the-elevators-in-skyline-building-40-memorial-highway-new-rochelle-ny",
}
SITE = {"sofi": O["sofi"], "high": "https://www.equityapartments.com/south-plainfield/south-plainfield/the-highlands-at-south-plainfield-apartments",
 "cove": O["cove"], "manley": "https://www.goldberg-realty.com/nj/summit/manley-court-associates/index.aspx", "avalon": O["avalon"],
 "wlb": "https://www.thevillagewlb.com/", "modera": "https://www.moderawoodbridge.com/", "georgian": "https://www.goldberg-realty.com/nj/iselin/georgian-arms-apartments/index.aspx",
 "pine": "https://www.thepointpineridge.com/", "renbay": O["renbay"], "parkside": O["parkside"], "admirals": O["admirals"], "riverside": O["riverside"],
 "renhills": O["renhills"], "lagrange": "https://www.lagrangefarmshvny.com/", "brompton": O["brompton"], "sterling": O["sterling"],
 "broad42": O["broad42"], "trail": "https://traillink.baxterbuilt.com/", "skyline": "https://www.skylinenewrochelle.com/", "arc": O["arc"]}

# ---------------------------------------------------------------- 1. live check
def al_units(u):
    L = A.parse_listing(page(u)[0]); out = {}
    for fp in L.get("available_units") or []:
        for un in fp.get("units") or []:
            out[un.get("name")] = dict(price=un.get("price"), on=un.get("available_on"), lease=un.get("lease_length"), plan=fp.get("name"), upd=un.get("updated_at"))
    return L, out
def next_data(u):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page(u)[0], re.S)
    return json.loads(m.group(1))["props"].get("homeDetails") or {}
def tr_units(u):
    hd = next_data(u); units = {}; plans = []
    for g in ((hd.get("floorPlans") or {}).get("floorPlanGroups") or []):
        for p in g.get("plans") or []:
            plans.append((g.get("title"), p.get("name"), p.get("availabilityText"), (p.get("priceRange") or {}).get("min")))
            for un in p.get("units") or []:
                pr = re.sub(r"[^\d]", "", ((un.get("pricePeriodRange") or {}).get("formattedPrice") or ""))
                units[(un.get("name") or "").replace("Unit ", "")] = dict(price=int(pr) if pr else None, text=un.get("availabilityText"), date=(un.get("availabilityDate") or "")[:10], plan=p.get("name"))
    return hd, units, plans
def when(d):
    if not d: return "not stated"
    return f"now (listed as available from {d})" if d <= TODAY.isoformat() else d
LIVE = []
def live(a, url, unit, status, price, avail, match, checked, notes):
    LIVE.append(dict(addr_key=K[a], listing_url=url, unit=unit, status=status, price_now=price, available_now_text=avail, matches_stored=match,
                     building_site_url=SITE.get(a, ""), checked_at=checked, notes=notes))
EXTRA = {
 "sofi": "Apartment List unit table, 15-month lease price. Own site (sofigaslightcommons.com) reads fine but its unit list is on a RentCafe portal that was not opened.",
 "high": "Apartment List unit table, 12-month price. Equity's own page returns a Cloudflare challenge (403), so the price could not be checked at source.",
 "manley": "Apartment List unit table. Goldberg Realty's own page returns a Cloudflare challenge (403).",
 "modera": "Apartment List unit table. moderawoodbridge.com answers 403 on robots.txt, so it was not fetched.",
 "georgian": "Apartment List unit table. Goldberg Realty's own page returns a Cloudflare challenge (403).",
 "pine": "Apartment List unit table. thepointpineridge.com returns a Cloudflare challenge (403).",
 "renbay": "Apartment List unit table. Own site (renaissancebay.com) shows floor plans but no unit numbers.",
 "renhills": "Apartment List unit table. Own site (renhills.com) shows floor plans but no unit numbers.",
}
for r in BATCH:
    a = [x for x in K if K[x] == r["addr_key"]][0]; u = U[a]
    rents = [int(x) for x in r["rents"].split(", ")]
    if a in ("lagrange", "northct", "trail"):
        why = {"lagrange": "Only link is a Zillow page (off limits). lagrangefarms.com says 'Launching Soon' with no units; lagrangefarmshvny.com answers 403 on robots.txt; the RentCafe page is a 403. No allowed copy of unit 303 found.",
               "northct": "Only link is a Zillow page (off limits). No own site found. Zumper's page for 48 North St shows a different unit (#307), not 206 or 208. Broker copies seen in search results were for other units and were not opened.",
               "trail": "Only link is a Zillow page (off limits). Own site traillink.baxterbuilt.com and traillinkcollective.com return a Cloudflare challenge (403); the RentCafe page is a 403."}[a]
        for un in r["unit_list"].split(", "):
            live(a, u, un, "blocked", "", "", "", RUN_AT, why)
        continue
    if a == "cove":
        L, us = al_units(u)
        chk(O["cove"], "$2,575+")
        for nm in ("1 bed, 1 bath, $2575", "1 Bed - 1 Bath"):
            x = us[nm]
            live(a, u, nm, "live", x["price"], "not stated", "yes", at(u),
                 f"Floor-plan level only, no unit number and no availability date. Apartment List last updated this entry on {x['upd'][:10]}. Own site (read {at(O['cove'])[:16]}Z) shows 1 bedroom '$2,575+' and a '$500 Security Deposit' special. Availability by Dec 15 cannot be confirmed from either page.")
        continue
    if a == "avalon":
        L, us = al_units(u)
        for nm, rent in zip(r["unit_list"].split(", "), rents):
            x = us.get(nm); own = O["av224"] if nm.endswith("224") else O["av308"]
            seen = f"{x['price']:,}" in page(own)[0] or str(x["price"]) in page(own)[0]
            live(a, own, nm, "live" if x["price"] == rent else "changed", x["price"], when(x["on"]), "yes" if x["price"] == rent else "no", at(own),
                 f"AvalonBay's own unit page is live for this unit{' and carries the same price' if seen else ' (price read from Apartment List)'}; Apartment List shows ${x['price']:,} for a {x['lease']}-month lease, available {x['on']}. Community page: 'Available starting Nov 16'.")
        continue
    if "apartmentlist.com" in u:
        L, us = al_units(u)
        for nm, rent in zip(r["unit_list"].split(", "), rents):
            x = us.get(nm)
            if not x:
                others = sorted((v["price"], k) for k, v in us.items() if v["price"] and v["price"] <= 3000)[:4]
                live(a, u, nm, "gone", "", "", "no", at(u), f"Unit {nm} is no longer in the unit table. Still listed at or under $3,000: " + ", ".join(f"{k} ${p:,}" for p, k in others) + ". " + EXTRA.get(a, ""))
                continue
            st = "live" if x["price"] == rent else "changed"
            late = " NOT available by 2026-12-15." if (x["on"] or "") > "2026-12-15" else ""
            live(a, u, nm, st, x["price"], when(x["on"]), "yes" if st == "live" else "no", at(u),
                 (f"Stored ${rent:,}, now ${x['price']:,}. " if st == "changed" else "") + f"Plan {x['plan']}, {x['lease']}-month lease." + late + " " + EXTRA.get(a, ""))
        continue
    if "/home/" in u:
        hd = next_data(u); stt = hd.get("currentStatus") or {}
        pr = int(re.sub(r"[^\d]", "", (hd.get("price") or {}).get("formattedPrice") or "0"))
        av = hd.get("formattedAvailableDate") or "not stated"
        act = stt.get("isActiveForRent") and not stt.get("isOffMarket")
        st = ("live" if pr == rents[0] else "changed") if act else "gone"
        n = {"fulton": "Trulia: For Rent, listed 2026-11-02; 'Decreased by $100 (4%) on Nov 11, 2026'. The page says Dogs: Not allowed (see confirm file): fails the dog gate.",
             "riv310": "Trulia: For Rent, listed 2026-10-30, broker Paul Gold Real Estate, Inc. The page says Dogs: Not allowed (see confirm file): fails the dog gate. Zumper carries the same unit (310 Riverside Blvd #6J).",
             "bway25": "Trulia: For Rent, listed 2026-10-30. Condo unit; 'Pets considered on a case-by-case basis.' Deposit $3,300.",
             "main142": "Trulia: For Rent, listed 2026-11-14 (one day on the market). Condo unit; 'Tenant will need approval by board.'"}[a]
        live(a, u, r["unit_list"], st, pr, av, "yes" if st == "live" else "no", at(u), n)
        continue
    hd, us, plans = tr_units(u); ud = hd.get("unitDetails") or {}
    if r["unit_list"] == "?":
        want = {"promenade": "S01", "alary": "14J", "arc": "907"}[a]
        p = [x for x in plans if x[1] == want]
        n = {"promenade": f"Floor-plan level only: plan S01 (studio) '{p[0][2]}' at ${p[0][3]:,}; no unit number or date. Trulia's unit counter for the building reads {ud.get('availableRentalUnits')} available units, which does not agree with the plans shown. Zumper has a unit page for 5 Freer St #415 (not the stored plan). No own site found.",
             "alary": f"Floor-plan level only: plan '14J' (studio) '{p[0][2]}' at ${p[0][3]:,}; no date. The plan name looks like a unit on floor 14, but the page does not say so. thealary.com is a different building (Fort Myers, FL); no own site found for New Rochelle.",
             "arc": f"Floor-plan level only: plan '907' (studio) '{p[0][2]}' at ${p[0][3]:,}; no date. Trulia's unit counter reads {ud.get('availableRentalUnits')} available units. Own site availability page shows no units ('inquire for availability') and says 'Rents reflect net effective pricing' with 1 month free on 13 months: $2,300 is probably a net-effective figure, so the monthly payment would be higher."}[a]
        live(a, u, want + " (floor plan)", "live" if p and p[0][3] == rents[0] else "changed", p[0][3] if p else "", "Available Now (no date)" if p else "", "yes" if p and p[0][3] == rents[0] else "no", at(u), n)
        continue
    for nm, rent in zip(r["unit_list"].split(", "), rents):
        x = us.get(nm)
        if not x:
            live(a, u, nm, "gone", "", "", "no", at(u), f"Unit {nm} is no longer in Trulia's unit list."); continue
        st = "live" if x["price"] == rent else "changed"
        av = x["text"] + (f" (date on page {x['date']})" if x["date"] else "")
        n = f"Trulia unit list, plan {x['plan']}. " + {
            "wlb": "Own site thevillagewlb.com disallows ClaudeBot in robots.txt, so it was not fetched.",
            "parkside": f"Also on the manager's own site (read {at(O['parkside'])[:16]}Z): 'Unit C-1.1 Bed: 1 | Baths: 1.5 | 861 sq ft Rent: $2,595 Status: Available (Now)'." if a == "parkside" else "",
            "admirals": "Manager's own site (gdcrentals.com) lists floor plans, not unit numbers.",
            "riverside": f"Manager's own site (read {at(O['riverside'])[:16]}Z): 'Unit B1 Studio | Bath: 1 | 701 sq ft Rent: $2,295 Status: Available (Now)'." if a == "riverside" else "",
            "midisland": "No own leasing site found (search returned listing sites only).",
            "brompton": "DeLaurentis Management's page for the building gives no prices or units.",
            "sterling": "Own site sterlingparcny.com links to RentCafe for unit prices (RentCafe is a 403), so the price is Trulia's.",
            "broad42": "Own site 42broad.com home page read; its floor-plan pages are a 404 and the unit list sits on a securecafe portal that was not opened. Listing text: 'approvals are based on the gross rent, not the net effective rent', so the price shown may be net-effective.",
            "skyline": "skylinenewrochelle.com answers 403 on robots.txt, so it was not fetched.",
        }.get(a, "")
        live(a, u, nm, st, x["price"], av, "yes" if st == "live" else "no", at(u), n.strip())
chk(O["parkside"], "Unit C-1.1 Bed: 1 | Baths: 1.5 | 861 sq ft Rent: $2,595 Status: Available (Now)")
chk(O["riverside"], "Unit B1 Studio | Bath: 1 | 701 sq ft Rent: $2,295 Status: Available (Now)")
chk(O["arc_av"], "inquire for availability"); chk(O["arc_av"], "Rents reflect net effective pricing")
chk(U["fulton"], "Decreased by $100 (4%)"); chk(O["avalon"], "Available starting Nov 16")

# ---------------------------------------------------------------- 2. gate facts
CONF = []
def c(a, fact, value, quote, src, status):
    chk(src, quote); CONF.append(dict(addr_key=K[a], fact=fact, value=value, quote=quote, source_url=src, status=status))
GARDEN = "No page read states an elevator. The batch file's 'elevator' was inferred from a floor count, not stated anywhere. "
c("sofi", "elevator", "unconfirmed", "[" + GARDEN + "Own site calls it a 'garden style community' with 'mid-rise one and two bedroom apartments'; unit numbers (1322, 2344) suggest building 1 or 2, floor 3, so there may be lifts, but no page says so.]", O["sofi_pet"], "unconfirmed")
c("sofi", "floor", "3 (inferred from unit numbers 1322 and 2344)", "[page does not state the floor]", U["sofi"], "unconfirmed")
c("sofi", "dogs_allowed", "yes", "$60 for Dog Rent", O["sofi_pet"], "confirmed")
c("sofi", "dog_weight_limit", "unconfirmed", "Two Pets Maximum $60 for Dog Rent $45 for Cat Rent $500 Non-Refundable Pet Fee", O["sofi_pet"], "unconfirmed")
c("high", "elevator", "unconfirmed", "[" + GARDEN + "Built 2000 per Apartment List; unit numbers are three digits (825, 433, 516) in what looks like a multi-building garden complex. Equity's own page is behind a Cloudflare challenge.]", U["high"], "unconfirmed")
c("high", "floor", "unconfirmed", "[page does not state the floor; unit 825]", U["high"], "unconfirmed")
c("high", "dogs_allowed", "yes", "[Apartment List pet policy data: allowed_pets dogs, cats; dog fee 300.00; pet rent 55.00; limit 3]", U["high"], "confirmed")
c("high", "dog_weight_limit", "unconfirmed", "[no weight figure in Apartment List or Zumper pet data]", U["high"], "unconfirmed")
c("cove", "elevator", "yes", "Elevators Convenient elevetors for residents to easily access their home.", O["cove"], "confirmed")
c("cove", "floor", "unconfirmed", "[listing is at floor-plan level; no unit number]", U["cove"], "unconfirmed")
c("cove", "dogs_allowed", "yes", "Cat $350 Dog $350", O["cove"], "confirmed")
c("cove", "dog_weight_limit", "unconfirmed", "[own site lists dog fees only; no weight figure]", O["cove"], "unconfirmed")
c("manley", "elevator", "unconfirmed", "[" + GARDEN + "Built 1945 per Apartment List; unit numbers like 16C, 19D, 01B, 03B read as building number plus letter, the pattern of a garden court. Goldberg Realty's own page is behind a Cloudflare challenge.]", U["manley"], "unconfirmed")
c("manley", "floor", "unconfirmed", "[page does not state the floor; units 16C and 19D]", U["manley"], "unconfirmed")
c("manley", "dogs_allowed", "yes", "Weight limit: 40lbs; No aggressive breeds", U["manley"], "confirmed")
c("manley", "dog_weight_limit", "40", "Weight limit: 40lbs; No aggressive breeds", U["manley"], "confirmed")
c("avalon", "elevator", "yes (Apartment List amenity tag only)", "Elevator", U["avalon"], "unconfirmed")
c("avalon", "floor", "2 (unit 00B-224)", "Floor 2", O["av224"], "confirmed")
c("avalon", "floor", "3 (unit 00B-308)", "Floor 3", O["av308"], "confirmed")
c("avalon", "dogs_allowed", "yes", "Dog $60 / mo.", O["av224"], "confirmed")
c("avalon", "dog_weight_limit", "unconfirmed", "[AvalonBay unit page lists dog rent and fee only; no weight figure on the pages read]", O["av224"], "unconfirmed")
c("wlb", "elevator", "unconfirmed", "[" + GARDEN + "Trulia's feature list for the building has no elevator entry; units are numbered 8203 and 5208 (building, floor 2). Own site disallows ClaudeBot.]", U["wlb"], "unconfirmed")
c("wlb", "floor", "2 (inferred from unit numbers 8203 and 5208)", "[page does not state the floor]", U["wlb"], "unconfirmed")
c("wlb", "dogs_allowed", "yes", "Cats, small dogs, large dogs allowed", U["wlb"], "confirmed")
c("wlb", "dog_weight_limit", "no number published; large dogs allowed", "Two pet max. Breed restrictions apply. $500 fee. $50/month rent.", U["wlb"], "unconfirmed")
c("modera", "elevator", "unconfirmed", "[No page read states an elevator: Apartment List's amenity list has none and the own site answers 403 on robots.txt. Units run to 7xx (741, 765) in a 2022 building, so an elevator is very likely.]", U["modera"], "unconfirmed")
c("modera", "floor", "6 (inferred from unit numbers 607 and 608)", "[page does not state the floor]", U["modera"], "unconfirmed")
c("modera", "dogs_allowed", "yes", "Our weight limit for each pet is 120lbs", zu("modera"), "confirmed")
c("modera", "dog_weight_limit", "120", "Our weight limit for each pet is 120lbs", zu("modera"), "confirmed")
c("georgian", "elevator", "unconfirmed", "[" + GARDEN + "Built 1990 per Apartment List; unit numbers like 42A, 34A, 41A, 31 read as small garden buildings. Goldberg Realty's own page is behind a Cloudflare challenge.]", U["georgian"], "unconfirmed")
c("georgian", "floor", "unconfirmed", "[page does not state the floor; units 42A and 34A]", U["georgian"], "unconfirmed")
c("georgian", "dogs_allowed", "yes", "$50 per dog.", U["georgian"], "confirmed")
c("georgian", "dog_weight_limit", "unconfirmed (a limit exists, number not published)", "Breed and Weight Restrictions", U["georgian"], "unconfirmed")
c("pine", "elevator", "unconfirmed", "[" + GARDEN + "Built 1989 per Apartment List; four-digit unit numbers (1425, 0906) in a large suburban complex with a plan called 'The Woods Loft'. Own site is behind a Cloudflare challenge.]", U["pine"], "unconfirmed")
c("pine", "floor", "unconfirmed", "[page does not state the floor; units 1425 and 0906]", U["pine"], "unconfirmed")
c("pine", "dogs_allowed", "yes", "[Apartment List pet policy data: allowed_pets cats, dogs; every fee and restriction field is empty]", U["pine"], "confirmed")
c("pine", "dog_weight_limit", "unconfirmed", "[no weight figure in Apartment List data; own site blocked]", U["pine"], "unconfirmed")
c("renbay", "elevator", "unconfirmed", "[" + GARDEN + "Built 1975 per Apartment List; unit numbers like 24H, 63C, 137E read as building plus letter. Own site's home, amenities and floor-plan pages do not mention an elevator.]", O["renbay"], "unconfirmed")
c("renbay", "floor", "unconfirmed", "[page does not state the floor; units 17D and 24H]", U["renbay"], "unconfirmed")
c("renbay", "dogs_allowed", "yes", "$50/month per dog", U["renbay"], "confirmed")
c("renbay", "dog_weight_limit", "unconfirmed", "Renaissance Bay is a pet-friendly community!", O["renbay"], "unconfirmed")
c("parkside", "elevator", "yes", "Elevator", U["parkside"], "confirmed")
c("parkside", "floor", "3 (inferred from unit number 2307)", "[page does not state the floor]", U["parkside"], "unconfirmed")
c("parkside", "dogs_allowed", "yes", "Pet Friendly building", O["parkside"], "confirmed")
c("parkside", "dog_weight_limit", "30", "30 lbs max weight", U["parkside"], "confirmed")
c("admirals", "elevator", "yes", "Elevator", U["admirals"], "confirmed")
c("admirals", "floor", "4 (inferred from unit numbers 2401 and 1410)", "[page does not state the floor]", U["admirals"], "unconfirmed")
c("admirals", "dogs_allowed", "yes", "Pet Friendly & Smoke-Free buildings", O["admirals"], "confirmed")
c("admirals", "dog_weight_limit", "unconfirmed", "[Trulia shows 'Restrictions: None' for dogs and no weight; the manager's two sister buildings next door publish 30 lbs]", U["admirals"], "unconfirmed")
c("riverside", "elevator", "yes", "Elevator", U["riverside"], "confirmed")
c("riverside", "floor", "4 (inferred from unit number 4401)", "[page does not state the floor]", U["riverside"], "unconfirmed")
c("riverside", "dogs_allowed", "yes", "Pet Friendly & Smoke Free building", O["riverside"], "confirmed")
c("riverside", "dog_weight_limit", "30", "30 lbs max weight", U["riverside"], "confirmed")
c("fulton", "elevator", "unconfirmed", "[listing does not mention an elevator or the number of floors]", U["fulton"], "unconfirmed")
c("fulton", "floor", "unconfirmed", "[unit is '#4'; the page does not state the floor]", U["fulton"], "unconfirmed")
c("fulton", "dogs_allowed", "no", "Pet policy Dogs Not allowed Cats Not allowed", U["fulton"], "contradicts")
c("fulton", "dog_weight_limit", "not applicable (no pets)", "No Pets", U["fulton"], "contradicts")
c("midisland", "elevator", "unconfirmed", "[" + GARDEN + "Built 1965 per Zumper; the listing describes 'traditional brick architecture' around 'expansive green courtyards'; unit numbers like 0672D and 0631E read as building plus letter.]", U["midisland"], "unconfirmed")
c("midisland", "floor", "unconfirmed", "[page does not state the floor; units 0672D and 0631E]", U["midisland"], "unconfirmed")
c("midisland", "dogs_allowed", "yes", "Two pet limit. Breed restrictions. 35 lb. weight restriction.", U["midisland"], "confirmed")
c("midisland", "dog_weight_limit", "35", "Two pet limit. Breed restrictions. 35 lb. weight restriction.", U["midisland"], "confirmed")
c("renhills", "elevator", "unconfirmed", "[" + GARDEN + "Built about 1970 per Apartment List; unit numbers like 801, 910, 021E, 142G read as building plus letter. Own site's home, amenities and floor-plan pages do not mention an elevator.]", O["renhills"], "unconfirmed")
c("renhills", "floor", "unconfirmed", "[page does not state the floor; units 801 and 910]", U["renhills"], "unconfirmed")
c("renhills", "dogs_allowed", "yes", "$50/month per pet", U["renhills"], "confirmed")
c("renhills", "dog_weight_limit", "unconfirmed", "[Apartment List restriction text is 'Aggressive Breeds' only; Zumper says 'Contact Leasing for breed restrictions and fees']", U["renhills"], "unconfirmed")
for a, why in (("lagrange", "Zillow page off limits; own sites blocked or empty"), ("northct", "Zillow page off limits; no own site found"), ("trail", "Zillow page off limits; own site behind a Cloudflare challenge")):
    for f in ("elevator", "floor", "dogs_allowed", "dog_weight_limit"):
        v = "unconfirmed"; q = f"[{why}]"; s = U[a]
        if a == "lagrange" and f == "dogs_allowed": v = "yes (Zumper building data only)"; q = "[Zumper building data: dog ok, limit 1 pet, no fee shown; no sentence to quote]"; s = zu("lagrange")
        if f == "floor": v = "3 (inferred from unit numbers)" if a != "northct" else "2 (inferred from unit numbers 206 and 208)"
        c(a, f, v, q, s, "unconfirmed")
c("brompton", "elevator", "unconfirmed", "[Trulia's feature list has no elevator entry; the stored unit is 7B, which implies seven or more floors, but no page states an elevator]", U["brompton"], "unconfirmed")
c("brompton", "floor", "7 (inferred from unit number 7B)", "[page does not state the floor]", U["brompton"], "unconfirmed")
c("brompton", "dogs_allowed", "yes (small dogs)", "Cats, small dogs allowed", U["brompton"], "confirmed")
c("brompton", "dog_weight_limit", "unconfirmed ('small dogs', no number)", "Cats, small dogs allowed", U["brompton"], "unconfirmed")
c("riv310", "elevator", "unconfirmed", "[listing says 'high floor' but does not mention an elevator]", U["riv310"], "unconfirmed")
c("riv310", "floor", "6 (inferred from unit number 6J)", "Beautiful high floor cozy studio in the historic Grenada Towers.", U["riv310"], "unconfirmed")
c("riv310", "dogs_allowed", "no", "Pet policy Dogs Not allowed Cats Not allowed", U["riv310"], "contradicts")
c("riv310", "dog_weight_limit", "not applicable (no pets)", "No Pets", U["riv310"], "contradicts")
c("bway25", "elevator", "yes", "Elevator", U["bway25"], "confirmed")
c("bway25", "floor", "2 (inferred from unit number 204)", "[page does not state the floor]", U["bway25"], "unconfirmed")
c("bway25", "dogs_allowed", "case by case", "Pets considered on a case-by-case basis.", U["bway25"], "unconfirmed")
c("bway25", "dog_weight_limit", "unconfirmed ('small dogs', no number)", "Cats, small dogs allowed", U["bway25"], "unconfirmed")
c("promenade", "elevator", "yes", "Elevator", U["promenade"], "confirmed")
c("promenade", "floor", "unconfirmed (apartments are on floors 2 to 4; ground floor is the garage)", "The building’s first story houses a parking garage, and three stories are for the apartments", O["herald2"], "unconfirmed")
c("promenade", "dogs_allowed", "yes", "Cats, small dogs, large dogs allowed", U["promenade"], "confirmed")
c("promenade", "dog_weight_limit", "no number published; large dogs allowed", "Large dogs allowed", U["promenade"], "unconfirmed")
c("sterling", "elevator", "unconfirmed", "[" + GARDEN + "Own site lists 'Controlled Building Access' but no elevator; units are numbered building-unit (25-17, 27-01, 15-06), the pattern of low-rise walk-up blocks.]", O["sterling"], "unconfirmed")
c("sterling", "floor", "unconfirmed", "[page does not state the floor; units 25-17 and 27-01]", U["sterling"], "unconfirmed")
c("sterling", "dogs_allowed", "yes", "Cats, small dogs, large dogs allowed", U["sterling"], "confirmed")
c("sterling", "dog_weight_limit", "50", "50 lbs max weight", U["sterling"], "confirmed")
c("main142", "elevator", "yes", "Elevator", U["main142"], "confirmed")
c("main142", "floor", "4 (inferred from unit number 4A)", "[page does not state the floor]", U["main142"], "unconfirmed")
c("main142", "dogs_allowed", "yes (small dogs; condo board approval needed)", "142 Main St #4A in Mineola, NY allows cats and small dogs.", U["main142"], "confirmed")
c("main142", "dog_weight_limit", "unconfirmed ('small dogs', no number)", "Cats, small dogs allowed", U["main142"], "unconfirmed")
c("broad42", "elevator", "unconfirmed", "[Trulia's feature list has no elevator entry and the own home page does not mention one. Units run from 209 to 612 and the building has 249 apartments with a concierge, so an elevator is very likely.]", U["broad42"], "unconfirmed")
c("broad42", "floor", "2 (unit 209) and 6 (unit 612), inferred from unit numbers", "[page does not state the floor]", U["broad42"], "unconfirmed")
c("broad42", "dogs_allowed", "yes", "Cats, small dogs, large dogs allowed", U["broad42"], "confirmed")
c("broad42", "dog_weight_limit", "no number published; large dogs allowed", "42 Broad is a pet-friendly community!", O["broad42"], "unconfirmed")
c("alary", "elevator", "yes", "Elevator", U["alary"], "confirmed")
c("alary", "floor", "unconfirmed (plan name '14J' suggests floor 14)", "a 28-story rental tower at 33 Westchester Place", O["yimby_alary"], "unconfirmed")
c("alary", "dogs_allowed", "yes", "Cats, small dogs, large dogs allowed", U["alary"], "confirmed")
c("alary", "dog_weight_limit", "no number published; large dogs allowed", "Large dogs allowed", U["alary"], "unconfirmed")
c("skyline", "elevator", "yes (per a residents' petition, which also reports outages)", "the regular service outages of our elevators - the only access residents have to their homes", O["petition"], "confirmed")
c("skyline", "floor", "2 (inferred from unit numbers 02H and 02A)", "[page does not state the floor]", U["skyline"], "unconfirmed")
c("skyline", "dogs_allowed", "yes", "Maximum of two pets per apartment home. No breed restrictions or weight limits.", zu("skyline"), "confirmed")
c("skyline", "dog_weight_limit", "no limit", "Maximum of two pets per apartment home. No breed restrictions or weight limits.", zu("skyline"), "confirmed")
c("arc", "elevator", "yes", "Elevator", U["arc"], "confirmed")
c("arc", "floor", "unconfirmed (plan name '907' suggests floor 9)", "Arc House - A 17-story New Development", U["arc"], "unconfirmed")
c("arc", "dogs_allowed", "yes (one dog)", "Yes! Arc House welcomes pets and offers amenities like an indoor dog run for your convenience.", O["arc_faq"], "confirmed")
c("arc", "dog_weight_limit", "no number published; large dogs allowed", "Large dogs allowed", U["arc"], "unconfirmed")

# ---------------------------------------------------------------- 4. facts
FACTS = []
def f(a, fact, value, quote, src):
    chk(src, quote); FACTS.append(dict(addr_key=K[a], fact=fact, value=value, quote=quote, source_url=src))
f("sofi", "building_type", "garden-style community, mid-rise", "Our garden style community is perfectly situated close to parks and recreation for you and your pets.", O["sofi_pet"])
f("sofi", "pet_fees", "dog rent $60/month; $500 non-refundable pet fee; two pets max", "Two Pets Maximum $60 for Dog Rent $45 for Cat Rent $500 Non-Refundable Pet Fee", O["sofi_pet"])
f("sofi", "pool", "outdoor, heated", "Outdoor Heated Swimming Pool w/ Sundeck", O["sofi_am"])
f("sofi", "parking", "garage and outside parking on site; fee not stated", "Onsite Parking Garage & Outside Parking", O["sofi_am"])
f("sofi", "year_built", "2002", "[Apartment List listing data: year_built 2002]", U["sofi"])
f("sofi", "management_company", "conflicting: batch file says Cushman & Wakefield; Zumper names Bozzuto Management", "[Zumper page data: pm_name Bozzuto Management]", zu("sofi"))
f("high", "year_built", "2000", "[Apartment List listing data: year_built 2000]", U["high"])
f("high", "pet_fees", "dog fee $300; pet rent $55/month (Apartment List) or $60 (Zumper); limit 3", "[Apartment List pet policy data: dogs fee 300.00; general rent 55.00, limit 3]", U["high"])
f("high", "management_company", "Equity Residential", "[Apartment List links the listing to equityapartments.com]", U["high"])
f("high", "pool", "yes (Apartment List amenity tag)", "Pool", U["high"])
f("cove", "pet_fees", "dog: $350 one-time, $40/month", "Cat $350 Dog $350 Description Price Cat $40 Dog $40", O["cove"])
f("cove", "parking", "private garages and on-site parking; fee not stated", "Private Garages Keep your belongings safe in your private garage.", O["cove"])
f("cove", "required_fees", "application $50; security deposit special $500", "Specials: $500 Security Deposit", O["cove"])
f("cove", "management_company", "Oxford Realty Group", "[the building's page is on oxfordrealtygroup.com]", O["cove"])
f("cove", "year_built", "2012", "[Apartment List listing data: year_built 2012]", U["cove"])
f("manley", "year_built", "1945", "[Apartment List listing data: year_built 1945]", U["manley"])
f("manley", "pet_fees", "dog rent $50/month; $250 pet fee; limit 2; 40 lb limit", "Weight limit: 40lbs; No aggressive breeds", U["manley"])
f("manley", "required_fees", "application $50; deposit 1 to 1.5 months' rent", "1 month - 1.5 month's rent", U["manley"])
f("manley", "management_company", "Goldberg Realty Associates", "[Apartment List links the listing to goldberg-realty.com]", U["manley"])
f("avalon", "parking", "$50/month (optional)", "Parking $50 / mo.", O["av224"])
f("avalon", "pet_fees", "dog rent $60/month; $500 one-time", "Dog $60 / mo. / Dog $500 (one-time charge)", O["av224"])
f("avalon", "required_fees", "application $50 per person; amenity fee $650 at move-in; security deposit $750", "Application Fees $50 / person Common Area/Amenities $650 (move-in) Security Deposit $750 (refundable)", O["av224"])
f("avalon", "utilities", "resident pays electric, trash, water, sewer; no gas", "Electric Resident Gas N/A Trash Resident Water Resident Sewer Resident", O["av224"])
f("avalon", "pool", "yes, outdoor (sundeck)", "Pool and sundeck with lounge areas and cabanas", O["av224"])
f("avalon", "management_company", "AvalonBay Communities", "[the building's page is on avaloncommunities.com]", O["avalon"])
f("wlb", "building_size", "180 units", "[Trulia page data: totalUnitsInBuilding 180]", U["wlb"])
f("wlb", "pet_fees", "$500 fee; $50/month (policy text) or $60/month (fee table) per pet; two pets max", "Two pet max. Breed restrictions apply. $500 fee. $50/month rent. / $60 monthly pet fee", U["wlb"])
f("wlb", "pool", "yes", "a shimmering swimming pool and state-of-the-art fitness center await your embrace", U["wlb"])
f("wlb", "management_company", "Afton Properties; Zumper still lists the building under its former name, Avalon West Long Branch", "[Zumper page data: pm_name Afton Properties]", zu("wlb"))
f("modera", "year_built", "2022", "[Apartment List listing data: year_built 2022]", U["modera"])
f("modera", "pet_fees", "$500 one-time; $50/month per pet; $30 PetScreening fee; 2 pets", "Our one-time pet fee is $500, and our pet rent is $50 per month per pet.", zu("modera"))
f("modera", "management_company", "Mill Creek Residential", "[Zumper page data: pm_name Mill Creek Residential]", zu("modera"))
f("georgian", "year_built", "1990", "[Apartment List listing data: year_built 1990]", U["georgian"])
f("georgian", "pet_fees", "dog rent $50/month; $250 per pet non-refundable; limit 2", "$50 per dog. / $250 per pet (non-refundable).", U["georgian"])
f("georgian", "management_company", "Goldberg Realty Associates", "[Apartment List links the listing to goldberg-realty.com]", U["georgian"])
f("pine", "year_built", "1989", "[Apartment List listing data: year_built 1989]", U["pine"])
f("pine", "management_company", "Bozzuto", "[Apartment List fee link points to communityfees.bozzuto.com]", U["pine"])
f("pine", "pool", "yes (Apartment List amenity tag)", "Pool", U["pine"])
f("renbay", "year_built", "1975", "[Apartment List listing data: year_built 1975]", U["renbay"])
f("renbay", "pet_fees", "dog rent $50/month; $250 fee; limit 2", "$50/month per dog", U["renbay"])
f("renbay", "pool", "yes (Apartment List amenity tag)", "Pool", U["renbay"])
f("parkside", "building_size", "110 units", "[Trulia page data: totalUnitsInBuilding 110]", U["parkside"])
f("parkside", "pet_fees", "dog rent $75/month; $500 one-time; 2 pets; 30 lb", "$75 monthly pet fee / $500 One-time pet fee", U["parkside"])
f("parkside", "parking", "outdoor or garage; fee not stated", "Choice of Outdoor & Garage Parking", O["parkside"])
f("parkside", "pool", "outdoor (Harbors Club)", "Harbors Club Swimming Pool", O["parkside"])
f("parkside", "management_company", "Ginsburg Development Companies (GDC)", "Learn why GDC Rentals are the best luxury rentals in Westchester and Rockland.", O["parkside"])
f("admirals", "building_size", "245 apartments in four buildings; opened July 2023", "Admirals Cove features 245 luxury apartments in four boutique-scaled buildings each with its own elegant lobby, fitness center and two community club lounges.", O["rj"])
f("admirals", "parking", "outdoor or garage, EV charging; fee not stated", "Choice of Outdoor & Garage Parking with available EV Charging", O["admirals"])
f("admirals", "pool", "outdoor, seasonal", "Seasonal Swimming Pool, Cabana, Sundeck, Fire Pit, BBQ & Children’s Playground", O["admirals"])
f("admirals", "management_company", "Ginsburg Development Companies (GDC)", "[the building's page is on gdcrentals.com]", O["admirals"])
f("riverside", "building_size", "107 units", "[Trulia page data: totalUnitsInBuilding 107]", U["riverside"])
f("riverside", "pet_fees", "dog rent $75/month; $500 one-time; 2 pets; 30 lb", "$75 monthly pet fee / $500 One-time pet fee", U["riverside"])
f("riverside", "parking", "outdoor or garage; fee not stated", "Choice of Outdoor & Garage Parking", O["riverside"])
f("riverside", "pool", "outdoor", "In-building Gym, Club Room and Riverside Pool", O["riverside"])
f("fulton", "price_history", "cut by $100 on 2026-11-11", "Decreased by $100 (4%)", U["fulton"])
f("fulton", "parking", "attached garage, on site; fee not stated", "Parking available", U["fulton"])
f("fulton", "required_fees", "deposit $2,200", "$2,200 deposit", U["fulton"])
f("midisland", "pet_fees", "$50/month per dog; $300 non-refundable per pet; two pets; 35 lb", "$25 per cat & $50 per dog, $300 non-refundable fee per pet.", U["midisland"])
f("midisland", "building_size", "232 units; built 1965", "[Trulia page data: totalUnitsInBuilding 232; Zumper page data: year_built 1965]", U["midisland"])
f("midisland", "parking", "surface lot, $50/month (Zumper data)", "[Zumper page data: parking type Surface Lot, fee 50, comment 'Parking Available.']", zu("midisland"))
f("midisland", "required_fees", "utility billing administrative fee (amount not shown)", "Utility - Billing Administrative Fee", U["midisland"])
f("midisland", "management_company", "Eagle Rock (Zumper: Eagle Rock Properties)", "[Zumper page data: pm_name Eagle Rock Properties]", zu("midisland"))
f("renhills", "parking", "open lot, included", "Open lot: included in lease", U["renhills"])
f("renhills", "required_fees", "$500 admin fee; $50 application per applicant; renter's insurance required", "$500 admin fee", U["renhills"])
f("renhills", "pet_fees", "$50/month per pet; $275 per pet; 2 pets", "$50/month per pet", U["renhills"])
f("renhills", "pool", "two outdoor pools", "Outdoor amenities include 2 outdoor pools", O["renhills_am"])
f("renhills", "year_built", "1970 (Apartment List) or 1968 (Zumper)", "[listing data fields: year_built]", U["renhills"])
f("renhills", "management_company", "Renaissance Management Group Inc", "[Zumper page data: pm_name Renaissance Management Group Inc]", zu("renhills"))
f("lagrange", "management_company", "Baxter PM Inc.", "[Zumper page data: pm_name Baxter PM Inc.]", zu("lagrange"))
f("lagrange", "own_site", "lagrangefarms.com is a placeholder with no listings", "Launching Soon", O["lagrange"])
f("brompton", "building_size", "92 units", "[Trulia page data: totalUnitsInBuilding 92]", U["brompton"])
f("brompton", "management_company", "DeLaurentis Management", "1880 Palmer Avenue, Larchmont, NY", O["brompton"])
f("riv310", "building_name", "Grenada Towers (the listing's spelling)", "Beautiful high floor cozy studio in the historic Grenada Towers.", U["riv310"])
f("riv310", "utilities", "tenant pays electricity and cooking gas; laundry in basement", "tenant pays for electricity and cooking gas", U["riv310"])
f("riv310", "required_fees", "deposit $2,100", "$2,100 deposit", U["riv310"])
f("bway25", "year_built", "1920", "Year Built", U["bway25"])
f("bway25", "doorman", "concierge in lobby", "The building features a vast lobby with a concierge", U["bway25"])
f("bway25", "parking", "assigned parking for a fee (amount not stated)", "assigned parking available for a fee", U["bway25"])
f("bway25", "required_fees", "deposit $3,300", "$3,300 deposit", U["bway25"])
f("promenade", "building_size", "four storeys, 80 units; ground floor is the garage", "A four-story, 80-unit, $24 million apartment building replaced the motel, which was razed in June 2020", O["herald2"])
f("promenade", "year_built", "opened December 2021", "Despite several delays caused by the Covid-19 pandemic, the property officially opened in December 2021.", O["herald1"])
f("promenade", "ownership_change", "sold to the Birch Group, reported 2022-10-06; formerly The Cornerstone at Yorkshire", "The Cornerstone at Yorkshire, at 5 Freer St. in Lynbrook, was recently sold to the Birch Group for $42.85 million.", O["herald1"])
f("promenade", "management_company", "Greystar at the time of the 2022 sale; current manager not confirmed", "the current Greystar management staff is expected to remain in place under the new ownership", O["herald1"])
f("promenade", "parking", "assigned covered parking; fee not stated", "Assigned covered parking.", U["promenade"])
f("promenade", "required_fees", "amenity fee and doorstep trash service (amounts not shown)", "Amenity fee / Doorstep trash services", U["promenade"])
f("northct", "not_found", "no allowed page read for this building", "[Zillow off limits; no own site found]", U["northct"])
f("sterling", "building_size", "192 units", "[Trulia page data: totalUnitsInBuilding 192]", U["sterling"])
f("sterling", "pet_fees", "dog rent $60/month; 2 pets; 50 lb", "$60 monthly pet fee", U["sterling"])
f("sterling", "pool", "outdoor", "Residents enjoy a swim in our beautiful outdoor pool", O["sterling"])
f("sterling", "management_company", "The Solomon Organization (affiliate)", "Managed by an affiliate of The Solomon Organization", O["sterling"])
f("sterling", "pet_policy_on_own_site", "not published", "Pet Policy: Please Call For Details.", O["sterling_pet"])
f("main142", "building_name", "The Harrison House (condominium)", "Welcome to The Harrison House!", U["main142"])
f("main142", "parking", "2 spots allocated to the unit; attached garage", "2 parking spots allocated for the unit.", U["main142"])
f("main142", "required_fees", "deposit $2,700; tenant pays all utilities; board approval needed", "Tenant will need approval by board.", U["main142"])
f("broad42", "building_size", "249 apartments", "comprises 249 market-rate apartments, more than 20,000 square feet of amenities, a parking garage", O["yimby_42"])
f("broad42", "parking", "valet garage; fee not stated", "Additional services include a valet attended parking garage, on-site concierge service, electric vehicle charging stations, and bike storage.", O["yimby_42"])
f("broad42", "doorman", "concierge on site", "on-site concierge service", O["yimby_42"])
f("broad42", "pool", "lap pool (the 2023 article calls it an all-season heated pool)", "rooftop lounge, lap pool, library, and fitness center", O["broad42"])
f("broad42", "pet_fees", "$500 pet deposit; $50/month", "$500 pet deposit / $50 monthly pet fee", U["broad42"])
f("broad42", "required_fees", "amenity fee, water and sewer (amounts not shown)", "Amenity Fee / Water and Sewer", U["broad42"])
f("broad42", "pricing_basis", "prices may be net-effective", "approvals are based on the gross rent, not the net effective rent", U["broad42"])
f("trail", "not_found", "no allowed page read for this building", "[Zillow off limits; own site behind a Cloudflare challenge]", U["trail"])
f("alary", "building_size", "28 storeys, 315 units; new in 2025", "The Alary, a 28-story rental tower at 33 Westchester Place", O["yimby_alary"])
f("alary", "parking", "attached garage; fee not stated", "Attached Garage", U["alary"])
f("alary", "pool", "yes (rooftop per the listing text)", "Pool", U["alary"])
f("skyline", "building_size", "588 units", "[Trulia page data: totalUnitsInBuilding 588]", U["skyline"])
f("skyline", "parking", "garage $140/month; covered $175/month (Zumper data)", "[Zumper page data: parking Garage Lot fee 140; Covered Lot fee 175]", zu("skyline"))
f("skyline", "pet_fees", "pet rent $85/month (Zumper data); 2 pets; PetScreening profile required", "A pet profile (with PetScreening.com) and agreement for each pet required.", zu("skyline"))
f("skyline", "management_company", "Harbor Group", "[Zumper page data: pm_name Harbor Group]", zu("skyline"))
f("skyline", "pool", "yes", "Pool", U["skyline"])
f("arc", "building_size", "17 storeys, 144 units", "Arc House - A 17-story New Development", U["arc"])
f("arc", "pricing_basis", "advertised rents are net-effective (1 month free on 13 months)", "*Offering 1 month free on a 13 month lease and 2 months free on 22 month lease. Rents reflect net effective pricing.", O["arc_av"])
f("arc", "parking", "valet garage; fee not stated", "Valet Garage Parking", U["arc"])
f("arc", "pet_amenities", "indoor dog run and rooftop dog park; one dog per home", "an indoor dog run that offers relief no matter the weather, as well as a rooftop dog park", O["arc_am"])

# ---------------------------------------------------------------- 3. items
ITEMS = []
def it(a, cat, date, excerpt, site, src, about, when_):
    if cat != "none_found": chk(src, excerpt)
    ITEMS.append(dict(addr_key=K[a], building_name=NAME[K[a]], category=cat, item_date=date, excerpt=excerpt, source_site=site, source_url=src, about=about, retrieved_at=when_))
it("high", "positive", "2024-08-16", "Any maintenance issue and the team is there within the hour. Management is great and super helpful.", "Apartment List (verified renter review)", U["high"], "management_company", at(U["high"]))
it("pine", "noise", "2025-05-01", "Do hear some noise from upstairs apartment and some cars/motorcycles are loud.", "Apartment List (verified renter review)", U["pine"], "building", at(U["pine"]))
it("pine", "management", "2025-05-01", "Maintenance is good but some areas need to be cleaned up. There are broken covers over yard irrigation systems etc.", "Apartment List (verified renter review)", U["pine"], "building", at(U["pine"]))
it("brompton", "safety_incident", "2024-12-28", "In addition to the West Avenue building, police believe Shafer is responsible for burglaries at 125 Larchmont Avenue, 1880 Palmer Avenue, & 10 Chatsworth Avenue in the Village.", "Larchmont Loop (local news)", O["loop"], "building", at(O["loop"]))
it("skyline", "elevator", "2023-12-06", "The most pressing among these is the regular service outages of our elevators - the only access residents have to their homes.", "Change.org residents' petition (not a news outlet; tenant allegation; closed with 70 supporters)", O["petition"], "building", at(O["petition"]))
it("promenade", "other", "2022-01-27", "A four-story, 80-unit, $24 million apartment building replaced the motel, which was razed in June 2020, after several battles between village officials and the motel’s owners over alleged crime at the site.", "LI Herald (local news)", O["herald2"], "street", at(O["herald2"]))
def first_sentences(b, n=2):
    s = re.split(r"(?<=[.!?])\s+", norm(b)); out = " ".join(s[:n])
    return out if len(out) <= 320 else s[0][:320]
for a in ("modera", "midisland", "renhills", "skyline", "lagrange"):
    z = ZP[K[a]]; rs = [r for v in (z.get("reviews") or {}).values() for r in (v.get("reviews") or [])]
    r = max(rs, key=lambda r: int(r["date"]))
    if a == "renhills": r = [x for x in rs if "almost 3 years" in x["body"]][0]   # newest one starts mid-sentence
    d = datetime.datetime.fromtimestamp(int(r["date"]), datetime.timezone.utc).date().isoformat()
    ITEMS.append(dict(addr_key=K[a], building_name=NAME[K[a]], category="other" if a == "lagrange" else "positive", item_date=d, excerpt=first_sentences(r["body"]),
                      source_site="Google review shown on Zumper (Zumper shows only its 'highest rated' reviews)", source_url=z["url"], about="building", retrieved_at=z["at"]))
have = {i["addr_key"] for i in ITEMS if i["category"] not in ("positive", "other")}   # buildings with no negative or incident item also get a none_found row
LOOK = ("One web search for the building name and address with police, fire, theft and tenants ({d}); no news article names this address. "
        "nj.com, Newsday, northjersey.com, app.com and mycentraljersey.com refuse our crawler, Patch was not used. {extra}")
XTRA = {
 "sofi": "Apartment List, Zumper and the own site show no review text.", "cove": "No reviews on Apartment List, Zumper or the own site.",
 "manley": "No reviews on Apartment List; no Zumper page.", "avalon": "No reviews on Apartment List, Zumper or the AvalonBay page; news hits were planning stories only.",
 "wlb": "No reviews on Trulia or Zumper; own site disallows ClaudeBot.", "georgian": "No reviews on Apartment List; no Zumper page.",
 "renbay": "No reviews on Apartment List or the own site; no Zumper page.", "parkside": "No reviews on Trulia, Zumper or the manager's site.",
 "admirals": "No reviews on Trulia or the manager's site; no Zumper page.", "riverside": "No reviews on Trulia, Zumper or the manager's site.",
 "fulton": "News results were about other points on Fulton Avenue, none naming number 316.", "riv310": "No reviews on Trulia or Zumper.",
 "bway25": "No reviews on Trulia or Zumper.", "northct": "No allowed page read for the building.", "sterling": "No reviews on Trulia or Zumper; the own site's review page is a submission form only.",
 "main142": "No reviews on Trulia or Zumper.", "broad42": "No reviews on Trulia; no Zumper page; news hits were development stories.",
 "trail": "No allowed page read for the building.", "alary": "No reviews on Trulia; no Zumper page; news hits were development stories.",
 "arc": "No reviews on Trulia or the own site; talkofthesound.com asks for a 600-second crawl delay and was not fetched.",
 "high": "The only review text is the 2024 Apartment List one; Equity's own reviews page is behind a Cloudflare challenge.",
 "modera": "The own site's reviews page (moderawoodbridge.com) answers 403 on robots.txt and was not read.",
 "midisland": "", "renhills": "", "lagrange": "", "promenade": "Coverage found is about the motel that stood on the site before 2020 and the 2022 sale.",
}
for a in K:
    if K[a] not in have:
        it(a, "none_found", "", LOOK.format(d="2026-11-15", extra=XTRA.get(a, "")).strip(), "search log", U[a], "building", RUN_AT)

# ---------------------------------------------------------------- 5. ratings
RAT = []
COLS_R = ["addr_key", "building_name", "rating_source", "rating_value", "rating_scale", "review_count", "as_of_date", "reviews_read", "reviews_last_6_months",
          "negative_last_6_months", "negative_older", "serious_issue_tags_last_6_months", "source_url", "retrieved_at", "notes"]
def rat(a, **kw):
    d = dict.fromkeys(COLS_R, ""); d.update(addr_key=K[a], building_name=NAME[K[a]], rating_scale=5); d.update(kw); RAT.append(d)
CUT = (TODAY - datetime.timedelta(days=183)).isoformat()
for a in K:
    z = ZP.get(K[a]) or {}; g = (z.get("reviews") or {}).get("google") or {}
    n = 0
    if g.get("aggregateRating"):
        rs = g.get("reviews") or []; ds = sorted(datetime.datetime.fromtimestamp(int(r["date"]), datetime.timezone.utc).date().isoformat() for r in rs)
        neg = [r for r in rs if int(float(r["rating"])) <= 2]
        rat(a, rating_source="Google rating shown on Zumper", rating_value=g["aggregateRating"], review_count=g["reviewCount"],
            as_of_date=datetime.datetime.fromtimestamp(g["lastPulled"], datetime.timezone.utc).date().isoformat(), reviews_read=len(rs),
            reviews_last_6_months=sum(d >= CUT for d in ds), negative_last_6_months=0, negative_older=len(neg), source_url=z["url"], retrieved_at=z["at"],
            notes=f"Zumper pulled the Google figures on the as_of date, so they are about two years old; it shows only {len(rs)} 'highest rated' review texts, dated {ds[0]} to {ds[-1]}, so negatives cannot be seen here"); n += 1
    alr = {"high": (5, "2024-08-16", 1, 0, "one verified renter review with text (5 stars)"), "pine": (5, "2025-05-01", 1, 0, "one verified renter review with text (5 stars; mentions noise from upstairs and some unkept areas)"),
           "modera": (2, "", 0, 1, "one verified rating of 2 with no text and no date shown; counted as an older negative because the date is unknown"),
           "renhills": (5, "", 0, 0, "one verified rating with no text and no date shown (amenities 2, value 3)")}.get(a)
    if alr:
        rat(a, rating_source="Apartment List", rating_value=alr[0], review_count=1, as_of_date=alr[1], reviews_read=alr[2], reviews_last_6_months=0,
            negative_last_6_months=0, negative_older=alr[3], source_url=U[a], retrieved_at=at(U[a]), notes=alr[4]); n += 1
    if not n:
        looked = [U[a] if "zillow" not in U[a] else "Zillow page not opened (off limits)"]
        looked.append(f"{z['url']} -> {z.get('status')}" if z else "no Zumper page tried")
        if a in SITE: looked.append(SITE[a] + {"high": " -> Cloudflare 403", "manley": " -> Cloudflare 403", "georgian": " -> Cloudflare 403", "wlb": " -> robots.txt disallows ClaudeBot",
                                               "trail": " -> Cloudflare 403", "lagrange": " -> robots.txt 403", "skyline": " -> robots.txt 403", "pine": " -> Cloudflare 403"}.get(a, " -> read, no rating widget"))
        rat(a, rating_source="none_found", retrieved_at=RUN_AT, notes="looked at: " + " | ".join(looked) + " | Trulia and Apartment List pages show no rating for this building")

# ---------------------------------------------------------------- write
def write(name, rows, cols=None):
    cols = cols or list(rows[0].keys())
    with open(f"data/evidence/{name}_batch_10.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"{name}_batch_10.csv: {len(rows)} rows, {len({r['addr_key'] for r in rows})} buildings")
write("live_check", LIVE); write("confirm", CONF); write("items", ITEMS); write("facts", FACTS); write("ratings", RAT, COLS_R)
from collections import Counter
print("live", dict(Counter(r["status"] for r in LIVE)))
print("confirm", dict(Counter(r["status"] for r in CONF)))
print("items", dict(Counter(r["category"] for r in ITEMS)))
print("ratings", dict(Counter(r["rating_source"] for r in RAT)))
print("quotes not found verbatim:", len(BAD))
for u, q in BAD: print("  !!", u[:70], "|", q[:110])
