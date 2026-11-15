"""Evidence batch 7: rebuild data/evidence/{live_check,confirm,items,facts,ratings}_batch_7.csv from the cached pages
in raw/evidence_b7/ (no network). Idempotent: every run rewrites the five files whole.

Sources read from the cache: Apartment List property pages (unit table, pet policy, review summary), Trulia building
pages (unit table, pet card, fees, features), Zumper building pages (raw/evidence_b7/zumper_bld.json: Google rating and
review texts), the buildings' own sites, and three news / trade articles. Hand-entered rows below quote text that was
read on the cached page named in the row.
Usage: python3 scripts/ev7_write.py
"""
import csv, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "scripts")
import h_apartmentlist as A
import h_trulia as TR
import ratings_round1 as R1

ROOT = Path(".")
RAWD = ROOT / "raw" / "evidence_b7"
OUT = ROOT / "data" / "evidence"
WINDOW_END = "2026-12-15"
M6 = datetime(2026, 5, 15, tzinfo=timezone.utc)   # six months before the check date
TL = "https://www.trulia.com/building/"
ALU = "https://www.apartmentlist.com/"

rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_7.csv")))
NAME = {r["addr_key"]: r["building_name"] for r in rows}

idx, bad = {}, {}
for line in open(RAWD / "_index.jsonl"):
    d = json.loads(line)
    (idx if d.get("status") == 200 else bad)[d["url"]] = d


def html(u):
    return open(idx[u]["path"], encoding="utf-8", errors="replace").read()


def at(u):
    return idx[u]["retrieved_at"]


# second source (Trulia building page) for the buildings whose listing link is Apartment List
TR2 = {
    "1-5 schooner ln|06460": TL + "spinnaker-wharf-15-schooner-ln-milford-ct-06460-2739037099",
    "158 cherry st|06460": TL + "spinnaker-brook-158-cherry-st-milford-ct-06460-2744859506",
    "467 w ave|06850": TL + "piper-467-west-ave-norwalk-ct-06850-2753811727",
    "515 w ave|06850": TL + "the-waypointe-515-west-ave-norwalk-ct-06850-1009251582",
    "26 belden ave|06850": TL + "the-confluence-at-norwalk-26-belden-ave-norwalk-ct-06850-1001813470",
    "8 norden pl|06855": TL + "halstead-norwalk-8-norden-pl-norwalk-ct-06855-1001652613",
    "75 tresser blvd|06901": TL + "75-tresser-blvd-apartments-75-tresser-blvd-stamford-ct-06901-1002386555",
    "1340 washington blvd|06902": TL + "parallel-41-1340-washington-blvd-stamford-ct-06902-1002385434",
    "355 atlantic st|06901": TL + "atlantic-station-355-atlantic-st-stamford-ct-06901-2747974504",
    "1455 washington blvd|06902": TL + "stamford-corners-1455-washington-blvd-stamford-ct-06902-1001522631",
    "44 john st|06902": TL + "the-hazel-stamford-44-john-st-stamford-ct-06902-2764583694",
    "150 southfield ave|06902": TL + "tgm-anchor-point-150-southfield-ave-stamford-ct-06902-1001819997",
    "184 summer st|06901": TL + "summer-house-apartments-184-summer-st-stamford-ct-06901-2750808731",
    "201 broad st|06901": TL + "canterbury-green-201-broad-st-stamford-ct-06901-1037829552",
    "100 avalon gates|06611": TL + "the-royce-at-trumbull-100-avalon-gates-trumbull-ct-06611-1001444574",
    "2300 reservoir ave|06611": TL + "woodside-trumbull-100-woodside-ct-trumbull-ct-06611-2750920248",
    "33 aberdeen rd|07747": TL + "tree-haven-33-aberdeen-rd-aberdeen-nj-07747-1045891266",
    "1101 schindler dr|07747": TL + "the-link-at-aberdeen-station-1101-schindler-dr-aberdeen-nj-07747-2734220747",
}

# own leasing site: (url, state) where state is ok / blocked / none
SITE = {
    "333 state st|06604": ("", "not found (searches return listing sites only)"),
    "100 reserve rd|06810": ("https://theresidencesatthesummit.com/", "ok"),
    "50 derby ave|06418": ("https://www.bluebrookproperties.com/franklin-school-lofts", "ok (manager's page for the building)"),
    "1-5 schooner ln|06460": ("https://paredimcommunities.com/communities/spinnaker-wharf/", "ok"),
    "1 avalon dr|06460": ("https://www.merionmilford.com/", "HTTP 403 (bot wall), not read"),
    "158 cherry st|06460": ("https://paredimcommunities.com/communities/spinnaker-milford/", "ok"),
    "467 w ave|06850": ("https://www.liveatpiper.com/", "ok"),
    "515 w ave|06850": ("https://www.thewaypointe.com/", "ok"),
    "26 belden ave|06850": ("https://www.confluencenorwalk.com/", "HTTP 403 (bot wall), not read"),
    "101 washington st|06854": ("https://sonopearl.com/", "robots.txt disallows Claude agents, not read"),
    "8 norden pl|06855": ("https://www.halsteadnorwalk.com/", "ok"),
    "75 tresser blvd|06901": ("https://www.75tresser.com/", "ok"),
    "1340 washington blvd|06902": ("https://paredimcommunities.com/communities/parallel-41/", "ok"),
    "355 atlantic st|06901": ("https://www.as.atlanticstationstamford.com/", "ok"),
    "1455 washington blvd|06902": ("https://www.stamfordcornersapts.com/", "HTTP 403 (bot wall), not read"),
    "750 summer st|06901": ("", "not found (navarinoproperty.com building pages return 404)"),
    "44 john st|06902": ("https://www.thehazelstamford.com/", "ok"),
    "66 glenbrook rd|06902": ("https://parcatglenbrook.com/", "ok"),
    "150 southfield ave|06902": ("https://tgmanchorpoint.com/", "ok"),
    "184 summer st|06901": ("https://www.summerhousestamford.com/", "ok"),
    "201 broad st|06901": ("https://canterburygreenapartments.com/", "ok"),
    "545 bedford st|06901": ("https://www.bedfordhallapartments.com/", "ok"),
    "1000 avalon way|06614": ("https://www.merionstratford.com/", "HTTP 403 (bot wall), not read"),
    "100 avalon gates|06611": ("https://www.royceattrumbull.com/", "ok"),
    "2300 reservoir ave|06611": ("https://woodsidetrumbull.com/", "ok"),
    "33 aberdeen rd|07747": ("https://www.treehavenapts.com/", "HTTP 403 (bot wall), not read"),
    "1101 schindler dr|07747": ("https://www.rentatthelink.com/", "HTTP 403 (bot wall), not read"),
    "10 ocean blvd|07716": ("", "not found (searches return listing sites only)"),
    "260 ave e|07002": ("https://skyelofts.com/north/", "ok"),
}

# ---------------------------------------------------------------- parse the cached listing pages
def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower()).lstrip("0")


_al, _tr = {}, {}


def al(u):
    if u not in _al:
        t = html(u)
        L = A.parse_listing(t)
        t2 = t.replace('\\"', '"')
        m = re.search(r'"reviewSummary":(\{"rental_id":"%s".*?\})' % re.escape(str(L.get("rental_id"))), t2)
        rs = None
        if m:
            try:
                rs = json.loads(m.group(1))
            except Exception:
                rs = None
        units = []
        for fp in L.get("available_units") or []:
            for x in fp.get("units") or []:
                units.append(dict(x, plan=fp.get("name"), bed=fp.get("bed")))
        _al[u] = dict(L=L, rs=rs, units=units)
    return _al[u]


def tr(u):
    if u not in _tr:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html(u), re.S)
        hd = json.loads(m.group(1))["props"].get("homeDetails") or {}
        units = []
        for g in ((hd.get("floorPlans") or {}).get("floorPlanGroups") or []):
            for plan in g.get("plans") or []:
                us = plan.get("units") or []
                for x in (us or [plan]):
                    units.append(dict(plan=plan.get("name"), unit=(x.get("name") or "").replace("Unit ", "") if us else "",
                                      price=(x.get("priceRange") or {}).get("min"), avail=x.get("availabilityText"),
                                      adate=(x.get("availabilityDate") or "")[:10]))
        afr = hd.get("activeForRentListing") or {}
        pet = afr.get("petPolicy") or {}
        dog = next((c for c in pet.get("cards") or [] if c.get("species") == "DOGS"), {})
        price = hd.get("price") or {}
        fb = (((hd.get("rentalCostsAndFees") or {}).get("costAndFeeCalculator") or {}).get("fees") or {})
        fees = {k: [((f.get("fee") or {}).get("displayValue") or "") for f in fb.get(k) or []] for k in
                ("monthlyRequiredFees", "oneTimeRequiredFees", "monthlyOptionalFees")}
        _tr[u] = dict(units=units, feats=TR.flat_features(hd.get("features")), dog=dog,
                      dogfacts={f["label"]: f["value"] for f in dog.get("facts") or []},
                      petadd=pet.get("additionalDetails") or [], ptype=price.get("typeDescription"),
                      ptext=re.sub(r"\s+", " ", ((price.get("typeDescriptionDetails") or {}).get("text") or "")).split(" Review the")[0].strip(),
                      modified=((hd.get("activeListing") or {}).get("lastDateModified") or "")[:10],
                      ud=hd.get("unitDetails") or {}, mgr=(((hd.get("planVisit") or {}).get("propertyManagementCompany") or {}).get("name")),
                      desc=(hd.get("description") or {}).get("value") or "", fees=fees,
                      special=[s.get("description") for s in hd.get("specialOffers") or []])
    return _tr[u]


def money(n):
    return f"${int(n):,}"


# ---------------------------------------------------------------- 1. live check
LIVE = []
EXTRA_NOTE = {
    ("33 aberdeen rd|07747", "31B"): "STALE FEED: Apartment List shows this unit with available_on 2024-02-05 and no 'availability last checked' time; the Trulia building page (modified 2026-10-06) shows 0 available units; own site returns 403. Treat as unverified until the office confirms.",
    ("158 cherry st|06460", "158-2H"): "Available on 2026-12-15, the last day of the window.",
    ("260 ave e|07002", "S207"): "Trulia lists floor plans, not units: 'S207' at $2,185 is the stored $2,185 row. Trulia's header says 0 available units and the page was last modified 2026-09-03. The building's own availability page (skyelofts.com/north/availability, read 2026-11-15) lists residence 207, 1 Bedroom / 1 Bath, with the price hidden.",
    ("260 ave e|07002", "417"): "Trulia lists floor plans, not units: '417' at $2,207 is the stored $2,207 row. Trulia's header says 0 available units and the page was last modified 2026-09-03. The building's own availability page (skyelofts.com/north/availability, read 2026-11-15) lists residence 417, 1 Bedroom / 1 Bath, with the price hidden.",
    ("50 derby ave|06418", "51-A"): "Unit '51-A' looks like a street number plus letter (the manager lists the property as 45-47 and 51 Derby Ave), so the floor is unknown.",
}
GROUND = {("1 avalon dr|06460", "1133"), ("467 w ave|06850", "1013"), ("515 w ave|06850", "MB128"), ("26 belden ave|06850", "2140"),
          ("150 southfield ave|06902", "1109"), ("1000 avalon way|06614", "1104"), ("100 avalon gates|06611", "9114"),
          ("1101 schindler dr|07747", "5102")}

for r in rows:
    k = r["addr_key"]
    url = r["urls"].split(" | ")[0]
    units = [u.strip() for u in r["unit_list"].split(",")]
    rents = [int(x) for x in r["rents"].split(",")]
    site = SITE[k][0]
    site_note = "" if SITE[k][1] == "ok" else f"Own site: {SITE[k][1]}."
    for unit, rent in zip(units, rents):
        notes = []
        if "apartmentlist.com" in url:
            P = al(url)
            L = P["L"]
            x = next((x for x in P["units"] if norm(x.get("name")) == norm(unit)), None)
            if x is None:
                left = [f"{y['name']} at {money(y['price'])} from {y.get('available_on')}" for y in P["units"] if (y.get("bed") or 0) <= 1]
                LIVE.append([k, url, unit, "gone", "", "", "no", site, at(url),
                             f"Unit no longer in the Apartment List unit table (stored {money(rent)}). Studio/1BR units still listed: "
                             + ("; ".join(left) if left else "none") + ". " + site_note])
                continue
            price, on = x.get("price"), x.get("available_on") or ""
            status = "live" if price == rent else "changed"
            if status == "changed":
                notes.append(f"Stored {money(rent)}, now {money(price)}.")
            notes.append(f"Apartment List unit table, plan '{x.get('plan')}'; feed last checked availability {str(L.get('availability_last_checked_at') or 'not stated')[:16]}.")
            if x.get("total_price") and x.get("total_price") != price:
                notes.append(f"Apartment List total with required monthly fees: {money(x['total_price'])} (fees ${x.get('required_fees')}).")
            if price and price > 3000:
                notes.append("REPRICED ABOVE $3,000.")
            if on and on > WINDOW_END:
                notes.append(f"NOT AVAILABLE BY {WINDOW_END}.")
            if k in TR2:
                T = tr(TR2[k])
                y = next((y for y in T["units"] if norm(y["unit"]) == norm(unit)), None)
                if y:
                    notes.append(f"Trulia building page shows the same unit at {money(y['price'])}" + (" (Trulia 'total price': " + T["ptext"] + ")" if T["ptype"] == "Total price" else "") + ".")
                else:
                    notes.append(f"Unit not shown on the Trulia building page (modified {T['modified']}, {T['ud'].get('availableRentalUnits')} available).")
            avail = on + (" (available now)" if x.get("available_now") else "")
        else:
            T = tr(url)
            if unit == "?":  # stored without a unit number: match the floor-plan row by price
                y = next((y for y in T["units"] if y["price"] == rent), None)
                if y:
                    unit = y["plan"]
            else:
                y = next((y for y in T["units"] if norm(y["unit"]) == norm(unit)), None)
            if y is None:
                LIVE.append([k, url, unit, "gone", "", "", "no", site, at(url), f"Unit no longer on the Trulia building page (stored {money(rent)}). " + site_note])
                continue
            price = y["price"]
            status = "live" if price == rent else "changed"
            if status == "changed":
                notes.append(f"Stored {money(rent)}, now {money(price)}.")
            notes.append(f"Trulia building page, plan '{y['plan']}'; page last modified {T['modified']}; {T['ud'].get('availableRentalUnits')} units available per the page header.")
            if T["ptype"] == "Total price":
                notes.append("Trulia price is a 'total price': " + T["ptext"] + ".")
            if price and price > 3000:
                notes.append("REPRICED ABOVE $3,000.")
            if y["adate"] and y["adate"] > WINDOW_END:
                notes.append(f"NOT AVAILABLE BY {WINDOW_END}.")
            avail = (y["avail"] or "") + (f" ({y['adate']})" if y["adate"] else "")
        if (k, unit) in GROUND:
            notes.append("Unit number suggests floor 1 (unconfirmed): would fail the no-ground-floor gate.")
        if (k, unit) in EXTRA_NOTE:
            notes.insert(0, EXTRA_NOTE[(k, unit)])
        if site_note:
            notes.append(site_note)
        LIVE.append([k, url, unit, status, price, avail, "yes" if status == "live" else "no", site, at(url), " ".join(notes)])

# ---------------------------------------------------------------- 2. gate facts
CONF = []


def C(k, fact, value, quote, src, status):
    CONF.append([k, fact, value, quote, src, status])


FLOOR = {  # inferred from the unit number; never stated on a page
    "604": "6", "M2-07": "2", "M4-22": "4", "51-A": "unknown", "5-02E": "unknown", "7211": "2", "1133": "1", "158-2L": "2", "158-2H": "2",
    "3012": "3", "1013": "1", "MB128": "1", "MB232": "2", "2318": "3", "2140": "1", "313": "3", "401": "4", "212": "2", "310": "3",
    "421": "4", "521": "5", "217": "2", "323": "3", "23A": "23", "341": "3", "603": "6", "203": "2", "324": "3", "2328": "3",
    "1109": "1", "1323": "3", "0807": "8", "2204": "2 (ambiguous: tower 2, floor 2; the building has 14 storeys)", "516": "5", "1104": "1", "4304": "3",
    "4234": "2", "9114": "1", "9210": "2", "8311": "3", "31B": "unknown", "5102": "1", "1213": "2", "7C": "7", "S207": "2", "417": "4",
}
ELEV_OVERRIDE = {
    "1-5 schooner ln|06460": ("select buildings only", "private and controlled access entries, covered parking and an elevator. Additional features vary by unit ... *Elevator Access",
                              "https://paredimcommunities.com/communities/spinnaker-wharf/", "unconfirmed"),
    "515 w ave|06850": ("yes", "Yes. The Waypointe provides elevator access in all buildings.", "https://www.thewaypointe.com/faq/", "confirmed"),
    "545 bedford st|06901": ("yes", "Rack 'em up for game night just an elevator ride from your door.", "https://www.bedfordhallapartments.com/", "confirmed"),
    "201 broad st|06901": ("yes", "Elevator Access", "https://canterburygreenapartments.com/", "confirmed"),
}
STORIES = {
    "10 ocean blvd|07716": ("11", "the 11 story high rise has apartments ranging from Studio's - 3BR's", TL + "elk-harbor-view-llc-10-ocean-blvd-atlantic-highlands-nj-07716-1001443078"),
    "201 broad st|06901": ("14", "A 14-story mixed-use office and apartment building in downtown Stamford has sold for $25 million", "https://hartfordbusiness.com/article/mixed-use-stamford-office-apartment-tower-sells-for-25m/"),
    "33 aberdeen rd|07747": ("2", "thick black smoke curling upward from under the roof of the two-story brick building", "https://nj1015.com/woman-dies-after-apartment-building-fire-in-aberdeen-nj/"),
}
# dog weight limit: value, quote, source, status
W = {
    "750 summer st|06901": ("75", "Weight limit (lbs.): 75", TL + "750-summer-street-750-summer-st-stamford-ct-06901-1045077069", "confirmed"),
    "1340 washington blvd|06902": ("65", "65 lb Weight Limit 2 Pet Limit Some Breed Restrictions", TR2["1340 washington blvd|06902"], "confirmed"),
    "33 aberdeen rd|07747": ("80", "Weight limit (lbs.): 80 ... Restrictions: 50 lb. restriction for Greyhounds", TR2["33 aberdeen rd|07747"], "confirmed"),
    "515 w ave|06850": ("100", "Pet Policy: Limit 2, maximum weight of 100lbs, $500 one time non-refundable fee, $40/mo per cat and $70/mo per dog", TR2["515 w ave|06850"], "confirmed"),
    "158 cherry st|06460": ("30", "Pet Policy: Two pets/unit, 30 lbs max weight, breed and additional deposits apply", TR2["158 cherry st|06460"], "confirmed"),
    "100 avalon gates|06611": ("no limit", "There are no weight limits for dogs, but we do have breed restrictions.", "https://www.royceattrumbull.com/pet-policya5b776fb", "confirmed"),
    "66 glenbrook rd|06902": ("40", "Dogs Allowed: Breed Restriction and Weight Restriction of 40lbs.", "https://parcatglenbrook.com/about/", "confirmed"),
    "75 tresser blvd|06901": ("limit exists, number not published", "Yes, 75 Tresser is a pet-friendly community. Breed restrictions, weight limits, and pet fees apply.", "https://www.75tresser.com/faqs/", "unconfirmed"),
    "2300 reservoir ave|06611": ("limit exists, number not published", "Yes, Woodside Trumbull is a pet-friendly community. Breed restrictions, weight limits, and pet fees apply.", "https://woodsidetrumbull.com/faqs/", "unconfirmed"),
    "150 southfield ave|06902": ("limit exists, number not published", "Weight and breed restrictions apply. Please call for details.", ALU + "ct/stamford/tgm-anchor-point", "unconfirmed"),
    "1-5 schooner ln|06460": ("limit exists, number missing from the page", "A pound maximum weight limit per pet will be strictly enforced.", ALU + "ct/milford-city/spinnaker-wharf-apartments--1", "unconfirmed"),
    "101 washington st|06854": ("small dogs only, number not stated", "Dogs: Allowed; Number allowed: 1; Size allowed: Small", TL + "sono-pearl-101-washington-st-norwalk-ct-06854-2757887032", "unconfirmed"),
}

for r in rows:
    k = r["addr_key"]
    url = r["urls"].split(" | ")[0]
    is_al = "apartmentlist.com" in url
    T = tr(url) if not is_al else (tr(TR2[k]) if k in TR2 else None)
    turl = url if not is_al else TR2.get(k)
    L = al(url)["L"] if is_al else None
    # elevator
    if k in ELEV_OVERRIDE:
        C(k, "elevator", *ELEV_OVERRIDE[k])
    else:
        al_el = is_al and "Elevator" in A.amen_names(L, "community_amenities") + A.amen_names(L, "unit_amenities") + A.amen_names(L, "top_amenities")
        tr_el = bool(T) and any(f[-1] == "Elevator" for f in T["feats"])
        if al_el:
            C(k, "elevator", "yes", "Elevator" + (" (also listed on the Trulia building page)" if tr_el else " (amenity list)"), url, "confirmed")
        elif tr_el:
            C(k, "elevator", "yes", "Elevator (Interior Features: Levels, Entrance, & Accessibility)", turl, "confirmed")
        else:
            looked = [u for u in (url, turl if turl != url else None, SITE[k][0] if SITE[k][1].startswith("ok") else None) if u]
            C(k, "elevator", "unconfirmed", "no elevator listed on: " + " ; ".join(looked) + ("" if SITE[k][1].startswith("ok") else f" (own site: {SITE[k][1]})"), url, "unconfirmed")
    if k in STORIES:
        C(k, "building_floors", *STORIES[k], "confirmed")
    # floor of each unit
    for row in [x for x in LIVE if x[0] == k]:
        u = row[2]
        C(k, "floor", f"unit {u}: {FLOOR.get(u, 'unknown')}", "inferred from the unit number only; the page does not state the floor", url, "unconfirmed")
    # dogs allowed
    al_d = A.pet_facts(L)[0] if is_al else None
    tr_d = (T["dog"].get("statusLabel") if T else None)
    if is_al:
        pp = L.get("pet_policies") or {}
        if al_d == "yes":
            C(k, "dogs_allowed", "yes", ("allowed pets: " + ", ".join(pp["allowed_pets"])) if pp.get("allowed_pets") else "Dogs allowed (amenity list)", url, "confirmed")
        elif tr_d == "Allowed":
            C(k, "dogs_allowed", "yes", "Dogs: Allowed" + ("; Size allowed: " + T["dogfacts"]["Size allowed"] if T["dogfacts"].get("Size allowed") else ""), turl, "confirmed")
        else:
            C(k, "dogs_allowed", "unconfirmed", "Apartment List says pets allowed but names no species", url, "unconfirmed")
        if tr_d == "Not allowed":
            C(k, "dogs_allowed", "no (Trulia)", "Dogs: Not allowed (Trulia building page; the Apartment List page for the same building lists dogs as allowed)", turl, "contradicts")
    else:
        C(k, "dogs_allowed", "yes" if tr_d == "Allowed" else "unconfirmed",
          "Dogs: " + str(tr_d) + ("; Size allowed: " + T["dogfacts"]["Size allowed"] if T["dogfacts"].get("Size allowed") else ""), url,
          "confirmed" if tr_d == "Allowed" else "unconfirmed")
    # weight limit
    if k in W:
        C(k, "dog_weight_limit", *W[k])
    else:
        size = (T["dogfacts"].get("Size allowed") if T else None)
        q = "no weight limit stated on the listing page" + (f"; Trulia pet card says 'Size allowed: {size}'" if size else "") \
            + ("" if SITE[k][1].startswith("ok") else f"; own site: {SITE[k][1]}")
        C(k, "dog_weight_limit", "not stated" + (" (large dogs allowed per Trulia)" if size and "large" in size else ""), q, turl or url, "unconfirmed")

C("66 glenbrook rd|06902", "dog_weight_limit", "40", "Dogs must be under 40 pounds", TL + "parc-at-glenbrook-apartments-66-glenbrook-rd-stamford-ct-06902-1001933587", "confirmed")
C("158 cherry st|06460", "dog_weight_limit", "number missing from the page", "A pound maximum weight limit per pet will be strictly enforced.", ALU + "ct/milford-city/spinnaker-brook", "unconfirmed")
C("515 w ave|06850", "dog_weight_limit", "not stated on the own site", "Pet policies and any restrictions are confirmed during the leasing process.", "https://www.thewaypointe.com/faq/", "unconfirmed")

# ---------------------------------------------------------------- 4. facts
FACTS = []


def F(k, fact, value, quote, src):
    FACTS.append([k, fact, value, quote, src])


Z = json.load(open(RAWD / "zumper_bld.json"))
for r in rows:
    k = r["addr_key"]
    url = r["urls"].split(" | ")[0]
    is_al = "apartmentlist.com" in url
    T = tr(url) if not is_al else (tr(TR2[k]) if k in TR2 else None)
    turl = url if not is_al else TR2.get(k)
    if is_al:
        L = al(url)["L"]
        if L.get("year_built"):
            F(k, "year_built", L["year_built"], f"year_built: {L['year_built']} (page data)", url)
        if L.get("total_units_count"):
            F(k, "building_size", f"{L['total_units_count']} units", f"total_units_count: {L['total_units_count']} (page data)", url)
        if L.get("pmc_display_name"):
            F(k, "management_company", L["pmc_display_name"], f"pmc_display_name: {L['pmc_display_name']} (page data)", url)
        ptxt = re.sub(r"\s+", " ", L.get("parking_details_text") or "").strip()
        pcom = "; ".join(re.sub(r"\s+", " ", p.get("comment") or "").strip() for p in L.get("parking") or [] if p.get("comment"))
        pfee = "; ".join(f"{p.get('category')}: {p.get('space_fee')}" for p in L.get("parking") or [] if p.get("space_fee"))
        if ptxt or pcom or pfee:
            F(k, "parking", (pfee or "see quote"), " | ".join(x for x in (ptxt, pcom) if x) or pfee, url)
        pp = L.get("pet_policies") or {}
        bits = []
        for g in ("dogs", "general"):
            for f in ("rent", "fee", "deposit", "limit"):
                v = A.txt((pp.get(g) or {}).get(f))
                if v:
                    bits.append(f"{g} {f}: {v.replace('$$', '$')}")
        if bits:
            F(k, "pet_fees", "; ".join(bits), "pet policy block: " + "; ".join(bits), url)
        add = re.sub(r"\s+", " ", L.get("additional_fees_text") or "").strip()
        if add:
            F(k, "required_monthly_fees", "see quote", add, url)
        mv = "; ".join(x for x in (re.sub(r"\s+", " ", (L.get("move_in_fees_text") or "")).replace("$$", "$").strip(),
                                   "deposit: " + re.sub(r"^Deposit:\s*", "", (L.get("deposit_fee_text") or "").replace("$$", "$")) if L.get("deposit_fee_text") else "",
                                   "application: " + (L.get("application_fee_text") or "").replace("$$", "$") if L.get("application_fee_text") else "") if x)
        if mv:
            F(k, "move_in_fees", "see quote", mv, url)
        am = list(dict.fromkeys(A.amen_names(L, "community_amenities") + A.amen_names(L, "top_amenities")))
        pool = [a for a in am if re.search(r"pool", a, re.I)]
        if pool:
            F(k, "pool", ", ".join(pool), "amenity list: " + ", ".join(pool), url)
        door = [a for a in am if re.search(r"doorman|concierge|front desk", a, re.I)]
        if door:
            F(k, "doorman", ", ".join(door), "amenity list: " + ", ".join(door), url)
        for s in L.get("specials") or []:
            txt = re.sub(r"\s+", " ", json.dumps(s) if not isinstance(s, str) else s)[:300]
            F(k, "special_offer", "see quote", txt, url)
    if T:
        if not is_al:
            if T["mgr"] or r["manager"]:
                F(k, "management_company", T["mgr"] or r["manager"], f"property management company: {T['mgr'] or r['manager']} (page data)", turl)
            if T["ud"].get("totalUnitsInBuilding"):
                F(k, "building_size", f"{T['ud']['totalUnitsInBuilding']} units", f"totalUnitsInBuilding: {T['ud']['totalUnitsInBuilding']} (page data)", turl)
        park = [f[-1] for f in T["feats"] if re.search(r"parking (policy|fee)|^\$\d+ parking|parking spot|parking garage|underground|dedicated parking|see fee", " ".join(map(str, f[2:])), re.I)]
        park = list(dict.fromkeys(park))
        if park:
            F(k, "parking", "see quote", " | ".join(park), turl)
        df = T["dogfacts"]
        petbits = [f"{a}: {b}" for a, b in df.items() if a in ("Monthly dog rent", "One-time fee", "Fee", "Number allowed")]
        if petbits:
            F(k, "pet_fees", "; ".join(petbits), "Dogs: " + "; ".join(petbits), turl)
        if T["ptype"] == "Total price" and T["ptext"]:
            mm = re.search(r"monthly fees \((\$[\d,]+)\)", T["ptext"])
            F(k, "required_monthly_fees", (mm.group(1) + "/mo") if mm else "see quote", T["ptext"], turl)
        req = [x for x in T["fees"]["monthlyRequiredFees"] if x and not re.match(r"(Monthly base rent|Rent)$", x)]
        if req:
            F(k, "required_monthly_fee_items", "see quote", "Required monthly: " + "; ".join(req), turl)
        opt = [x for x in T["fees"]["monthlyOptionalFees"] if re.search(r"park|garage|pet|dog|storage", x, re.I)]
        if opt:
            F(k, "optional_monthly_fee_items", "see quote", "Optional monthly: " + "; ".join(opt), turl)
        pool = list(dict.fromkeys(f[-1] for f in T["feats"] if re.search(r"\bpool\b", str(f[-1]), re.I)))
        if pool and not is_al:
            F(k, "pool", "see quote", " | ".join(pool)[:300], turl)
        for s in T["special"]:
            if s and not s.startswith("Total monthly leasing prices"):
                F(k, "special_offer", "see quote", re.sub(r"\s+", " ", s)[:300], turl)
    z = Z.get(k) or {}
    if z.get("status") == 200 and z.get("name") and "/apartment-buildings/" in z.get("url", ""):
        zn = z["name"]
        if norm(zn)[:6] != norm(NAME[k])[:6] and not re.match(r"\d", zn):
            F(k, "former_or_other_name", zn, f"Zumper building page for this address is titled '{zn}'", z["url"])
        if z.get("year_built"):
            F(k, "year_built", z["year_built"], f"year_built: {z['year_built']} (page data)", z["url"])

HB1 = "https://hartfordbusiness.com/article/downtown-bridgeport-apartments-sell-for-136m/"
HB2 = "https://hartfordbusiness.com/article/mixed-use-stamford-office-apartment-tower-sells-for-25m/"
F("333 state st|06604", "ownership_change", "sold October 2021 to Premier Properties (Lakewood, NJ) for $13.6M",
  "The 65-unit apartment complex at 333 State St., sold in October to Premier Properties of Lakewood, New Jersey, records show. The property, which was originally built in 1968", HB1)
F("333 state st|06604", "year_built", "1968 (office building, later converted)", "The property, which was originally built in 1968, was redeveloped last decade", HB1)
F("201 broad st|06901", "ownership_change", "building sold for $25M; article dated 2026-02-27",
  "A 14-story mixed-use office and apartment building in downtown Stamford has sold for $25 million, according to city property records.", HB2)
CG = "https://canterburygreenapartments.com/assets/files/CBG-Fees-for-Website-1.pdf"
F("201 broad st|06901", "required_monthly_fees", "$50/mo amenity fee", "Amenity Fee $50 per month required", CG)
F("201 broad st|06901", "parking", "$125/mo first car, $150/mo additional car (garage)", "Parking Fee $125 per month, first car optional; Parking Fee $150 per month, additional car optional", CG)
F("201 broad st|06901", "pet_fees", "$50/mo per pet; $500 one-time per pet", "Pet Fee $500(one-time, per pet, at move in) optional; Pet Rent $50 per month, per pet optional", CG)
F("201 broad st|06901", "move_in_fees", "application $34; holding fee $500; deposit one month", "Application Fee $34 per applicant; Holding Fee $500; Security Deposit Equal to one month's rent", CG)
F("66 glenbrook rd|06902", "pet_fees", "$60/mo pet rent; $525 deposit; 2 pets", "$525 Deposit; $60 Monthly Pet Rent; 40 lb Weight Limit; 2 Pet Limit", "https://parcatglenbrook.com/about/")
F("545 bedford st|06901", "management_company", "Navarino Property Management", "Bedford Hall · Managed by Navarino Property Management", "https://www.bedfordhallapartments.com/")
F("545 bedford st|06901", "parking", "garage, covered; fee not stated on own site", "Secure covered parking — plus a home for your motorcycle.", "https://www.bedfordhallapartments.com/")
F("545 bedford st|06901", "pet_policy", "dogs and cats, up to two pets", "Dogs and cats are welcome home — up to two pets per residence.", "https://www.bedfordhallapartments.com/amenities.html")
F("50 derby ave|06418", "management_company", "Blue Brook Properties (page host)", "The Franklin School Lofts are nestled in a residential neighborhood in Derby, CT", "https://www.bluebrookproperties.com/franklin-school-lofts")
F("50 derby ave|06418", "building_size", "32 units (16 one-bedroom, 16 two-bedroom)", "The property includes (16) One-Bedroom Apartments & (16) Two-Bedroom Apartments.", "https://www.bluebrookproperties.com/franklin-school-lofts")
F("50 derby ave|06418", "parking", "off-street lot; fee not stated", "Ample off-street parking", "https://www.bluebrookproperties.com/franklin-school-lofts")
F("50 derby ave|06418", "pet_fees", "pet fee varies", "Pet Friendly (additional fees apply) ... Pet Fee (varies)", "https://www.bluebrookproperties.com/franklin-school-lofts")
F("260 ave e|07002", "parking", "garage parking; fee not stated", "Garage Parking", "https://skyelofts.com/north/amenities")
F("515 w ave|06850", "parking", "parking garage; fee not stated", "The community offers a parking garage along with bike storage.", "https://www.thewaypointe.com/faq/")
F("184 summer st|06901", "parking", "covered gated garage, limited", "has a covered, gated parking garage. Parking is limited and there are many additional parking options in the area.", "https://www.summerhousestamford.com/faq/")
F("184 summer st|06901", "doorman", "onsite concierge", "The community offers an onsite concierge and a shuttle service to the Stamford Transportation Center", "https://www.summerhousestamford.com/faq/")
F("355 atlantic st|06901", "doorman", "24/7 concierge", "24/7 Concierge", "https://www.as.atlanticstationstamford.com/amenities/")
F("150 southfield ave|06902", "parking", "1 reserved space per lease; underground parking", "Parking – 1 Reserved Space Per Lease", "https://tgmanchorpoint.com/")
F("1000 avalon way|06614", "former_or_other_name", "Avalon Stratford", "Zumper building page for this address is titled 'Avalon Stratford'", (Z.get("1000 avalon way|06614") or {}).get("url", ""))
F("10 ocean blvd|07716", "pool", "outdoor pool", "breathtaking views, full outdoor pool, gym, and unlimited outdoor recreations", TL + "elk-harbor-view-llc-10-ocean-blvd-atlantic-highlands-nj-07716-1001443078")
# de-duplicate facts (same key, fact, quote)
seen, FX = set(), []
for f in FACTS:
    key = (f[0], f[1], f[3])
    if key not in seen and f[4]:
        seen.add(key); FX.append(f)
FACTS = FX

# ---------------------------------------------------------------- 3. evidence items
ITEMS = []


def I(k, cat, date, excerpt, site, url, about, when=None):
    ITEMS.append([k, NAME[k], cat, date, excerpt, site, url, about, when or (at(url) if url in idx else "")])


for r in rows:  # Apartment List: the one review snippet the page shows
    k = r["addr_key"]
    url = r["urls"].split(" | ")[0]
    if "apartmentlist.com" not in url:
        continue
    rs = al(url)["rs"] or {}
    s = (rs.get("snippet") or "").strip()
    if not s or re.search(r"my id|i really want it", s):
        continue  # a prospect's note about their own application, not about the building
    sents = re.split(r"(?<=[.!?])\s+", s)
    neg = [x for x in sents if re.search(r"nois|insulat|wish|gripe", x, re.I)]
    if neg and re.search(r"nois|insulat", s, re.I):
        I(k, "noise", rs["snippet_submit_date"][:10], " ".join(x for x in sents if re.search(r"nois|insulat", x, re.I))[:300], "Apartment List (verified renter review)", url, "building")
    pos = " ".join(sents[:2])[:300]
    I(k, "positive", rs["snippet_submit_date"][:10], pos, "Apartment List (verified renter review)", url, "building")
    if re.search(r"more affordable indoor parking", s):
        I(k, "other", rs["snippet_submit_date"][:10], next(x for x in sents if "indoor parking" in x)[:300], "Apartment List (verified renter review)", url, "garage_or_lot")

ZS = "Google review shown on Zumper"
zu = Z["100 reserve rd|06810"]["url"]; zt = Z["100 reserve rd|06810"]["at"]
I("100 reserve rd|06810", "positive", "2024-10-06", "The apartments itself, the building and amenities are so great, the security in the building and a convenience to have everything on the site is just amazing.", ZS, zu, "building", zt)
I("100 reserve rd|06810", "positive", "2024-10-10", "The staff is very friendly and engaging and the community is wonderful.", ZS, zu, "management_company", zt)
zu = Z["26 belden ave|06850"]["url"]; zt = Z["26 belden ave|06850"]["at"]
I("26 belden ave|06850", "positive", "2025-02-06", "Jairo and Ben from maintenance are really awesome. I sent a request in the morning for anything and they come by and fix right away.", ZS, zu, "management_company", zt)
I("26 belden ave|06850", "positive", "2024-06-07", "The apartment is spacious and comfortable, the building is constantly being cleaned, and the amenities are convenient", ZS, zu, "building", zt)
I("26 belden ave|06850", "positive", "2024-11-07", "The hallways, office area and elevators are immaculate and I can only give a positive review of my experience.", ZS, zu, "building", zt)
I("26 belden ave|06850", "elevator", "2025-02", "Some note occasional elevator outages.", "Zumper's machine-written summary of the building's Google reviews (figures pulled 2025-02-12); no individual review text behind it is shown", zu, "building", zt)
FR = "https://www.1strespondernews.com/news/101620103/Apartment-Fire-in-Norwalk"
I("26 belden ave|06850", "other", "2020-10-15", "Firefighters made their way to apartment 1103 and found a small fire in the master bedroom of the two bedroom apartment. The fire was held in check by the sprinkler system and then completely extinguished by firefighters.", "1st Responder News", FR, "building")
NJ = "https://nj1015.com/woman-dies-after-apartment-building-fire-in-aberdeen-nj/"
I("33 aberdeen rd|07747", "other", "2023-01-06", "A woman died after an apartment complex fire that displaced 14 residents Thursday afternoon. The fire started around 12:30 p.m. in a building at the Tree Haven III apartment complex off Aberdeen Road.", "New Jersey 101.5", NJ, "building")

LEADS = {  # search results that point at a page we may not fetch; recorded as where-we-looked, never as evidence
    "355 atlantic st|06901": "LEAD NOT READ: atlanticstreetresidents.com (a residents' outage log for 355 Atlantic St) disallows Claude agents in robots.txt",
    "100 avalon gates|06611": "LEAD NOT READ: a trumbull-ct.gov civic alert dated 2023-05-01 titled 'Incident at The Royce at Avalon Gates' and a CT Post article on police calls to the Trumbull complexes; both hosts disallow our fetch",
    "8 norden pl|06855": "LEAD NOT READ: nancyonnorwalk.com article on a Norden Place cleanup order (HTTP 403)",
    "1 avalon dr|06460": "LEAD NOT READ: CT Post article on the sale of Halstead Milford on Avalon Drive to Merion Realty Partners (ctpost.com disallows Claude agents)",
    "467 w ave|06850": "CT Post / Darien Times articles on the building's 2025 opening exist but the Hearst sites disallow Claude agents",
}
have = {x[0] for x in ITEMS if x[2] not in ("positive",)}
for r in rows:
    k = r["addr_key"]
    url = r["urls"].split(" | ")[0]
    z = Z.get(k) or {}
    where = ["web search for the building name, address" + (" and former name" if any(f[0] == k and f[1] == "former_or_other_name" for f in FACTS) else "")
             + " with police / fire / break-in / tenants terms (2026-11-15): only listing sites returned, or nothing about this address",
             "listing page reviews (" + ("Apartment List" if "apartmentlist" in url else "Trulia shows none") + ")",
             "Zumper page " + (z.get("url") or "not found") + (" (no reviews shown)" if not (((z.get("reviews") or {}).get("sources") or {}).get("google")) else "")]
    if not SITE[k][1].startswith("ok"):
        where.append("own site: " + SITE[k][1])
    where.append("not fetched by rule: Patch, QNS, BBB, Hearst CT papers (robots.txt names Claude)")
    if k in LEADS:
        where.append(LEADS[k])
    if k not in have:
        ITEMS.append([k, NAME[k], "none_found", "", "No dated incident, complaint or news item found. Looked at: " + "; ".join(where), "search log", url, "building", at(url)])
    elif k in LEADS:
        ITEMS.append([k, NAME[k], "none_found", "", "No further item found. " + LEADS[k], "search log", url, "building", at(url)])

# ---------------------------------------------------------------- 5. ratings
RATE = []
RCOLS = ["addr_key", "building_name", "rating_source", "rating_value", "rating_scale", "review_count", "as_of_date", "reviews_read",
         "reviews_last_6_months", "negative_last_6_months", "negative_older", "serious_issue_tags_last_6_months", "source_url", "retrieved_at", "notes"]


def summarise(revs):
    r6 = n6 = nold = 0; tg = []
    for d, s, body in revs:
        neg, t = R1.is_negative(s, body)
        if d is not None and d >= M6:
            r6 += 1
            if neg:
                n6 += 1; tg += t
        elif neg:
            nold += 1
    return len(revs), r6, n6, nold, ";".join(sorted(set(tg)))


for r in rows:
    k = r["addr_key"]
    url = r["urls"].split(" | ")[0]
    found = []
    z = Z.get(k) or {}
    g = (((z.get("reviews") or {}).get("sources") or {}).get("google")) if z.get("status") == 200 else None
    if g and g.get("aggregateRating") is not None:
        revs = [(datetime.fromtimestamp(x["date"], timezone.utc) if x.get("date") else None, x.get("rating"), x.get("body") or "") for x in g.get("reviews") or []]
        n, r6, n6, nold, tg = summarise(revs)
        pulled = datetime.fromtimestamp(g["lastPulled"], timezone.utc).date().isoformat() if g.get("lastPulled") else ""
        newest = max([x[0] for x in revs if x[0]], default=None)
        note = f"Zumper pulled the Google figures on {pulled}; it shows only {n} 'highest rated' review texts" + (f", newest dated {newest.date().isoformat()}" if newest else "") \
               + ", so the negative counts here say nothing about the low-star reviews"
        if z.get("summary") and re.search(r"elevator outages", z["summary"]):
            note += "; Zumper's own summary of the reviews says 'Some note occasional elevator outages.'"
        found.append([k, NAME[k], "Google rating shown on Zumper", g.get("aggregateRating"), g.get("ratingScale") or 5, g.get("reviewCount"), pulled, n, r6, n6, nold, tg, z["url"], z.get("at", ""), note])
    if "apartmentlist.com" in url:
        rs = al(url)["rs"]
        if rs and rs.get("rating_count"):
            revs = []
            if rs.get("snippet"):
                d = datetime.fromisoformat(rs["snippet_submit_date"][:10]).replace(tzinfo=timezone.utc)
                revs.append((d, rs.get("snippet_rating"), rs["snippet"]))
            n, r6, n6, nold, tg = summarise(revs)
            low = rs.get("worst_rating") is not None and rs["worst_rating"] <= 2
            note = (f"verified-renter ratings; best {rs.get('best_rating')}, worst {rs.get('worst_rating')}; sub-scores amenities {round(rs.get('amenities') or 0, 1)}, value {round(rs.get('value') or 0, 1)}; "
                    f"the page shows {n} review text" + ("" if n == 1 else "s") + (f" (dated {rs['snippet_submit_date'][:10]})" if n else "")
                    + ("; at least one 1 or 2 star rating exists but its date and text are not shown, so it is not in the negative counts" if low else ""))
            if low:  # low-star ratings exist but carry no date: leave the dated counts blank rather than write a false zero
                tot, cnt, best, worst = round(rs["overall"] * rs["rating_count"]), rs["rating_count"], rs["best_rating"], rs["worst_rating"]
                nneg = cnt if best <= 2 else (round((best * cnt - tot) / (best - worst)) if best == 5 and worst == 1 else "at least 1")
                note += f"; negative ratings of unknown date: {nneg} of {cnt} (worked out from the average, best and worst)"
                n6, nold = "", ""
            found.append([k, NAME[k], "Apartment List", round(rs["overall"], 1), 5, rs["rating_count"], at(url)[:10], n, r6, n6, nold, tg, url, at(url), note])
    if not found:
        looked = [f"{url} -> 200 (no rating)"]
        if z.get("url"):
            looked.append(f"{z['url']} -> {z.get('status')}" + (" (no rating)" if z.get("status") == 200 else ""))
        if k in TR2:
            looked.append("Trulia building page shows no rating")
        looked.append("own site: " + (SITE[k][0] + " (no rating widget)" if SITE[k][1].startswith("ok") else SITE[k][1]))
        found.append([k, NAME[k], "none_found", "", 5, "", "", "", "", "", "", "", "", at(url), "looked at: " + " | ".join(looked)])
    RATE += found

# ---------------------------------------------------------------- write
def w(name, header, data):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f); cw.writerow(header); cw.writerows(data)
    print(name, len(data))


w("live_check_batch_7.csv", ["addr_key", "listing_url", "unit", "status", "price_now", "available_now_text", "matches_stored", "building_site_url", "checked_at", "notes"], LIVE)
w("confirm_batch_7.csv", ["addr_key", "fact", "value", "quote", "source_url", "status"], CONF)
w("items_batch_7.csv", ["addr_key", "building_name", "category", "item_date", "excerpt", "source_site", "source_url", "about", "retrieved_at"], ITEMS)
w("facts_batch_7.csv", ["addr_key", "fact", "value", "quote", "source_url"], FACTS)
w("ratings_batch_7.csv", RCOLS, RATE)
keys = {r["addr_key"] for r in rows}
for nm, data in (("live", LIVE), ("confirm", CONF), ("items", ITEMS), ("facts", FACTS), ("ratings", RATE)):
    miss = keys - {x[0] for x in data}
    print(nm, "buildings missing:", sorted(miss))
