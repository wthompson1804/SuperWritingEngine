"""Evidence batch 9: build data/evidence/{live_check,confirm,items,facts,ratings}_batch_9.csv from cached pages. No network.
Inputs: raw/evidence_b9/ (_index.jsonl, zumper_bld.json, _al_reviews.json, cached html). Every excerpt is sliced out of the
cached page or review body by start/end markers, so it is verbatim; a marker that is not found stops the script."""
import csv, json, re, sys, datetime, html as H
sys.path.insert(0, "scripts")
import h_apartmentlist as A
from ev9_text import text
ROOT = "."
E = "raw/evidence_b9/"
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_9.csv")))
BY = {r["addr_key"]: r for r in rows}
idx = {}
for l in open(E + "_index.jsonl"):
    x = json.loads(l)
    if x["status"] == 200: idx[x["url"]] = x
ZUM = json.load(open(E + "zumper_bld.json"))
ALR = json.load(open(E + "_al_reviews.json"))
def at(u): return idx[u]["retrieved_at"]
_tc = {}
def page(u):
    if u not in _tc: _tc[u] = re.sub(r"\s+", " ", text(idx[u]["path"]))
    return _tc[u]
def cut(u, start, end):
    t = page(u); i = t.find(start)
    if i < 0: raise SystemExit(f"start not found: {start!r} in {u}")
    j = t.find(end, i)
    if j < 0: raise SystemExit(f"end not found: {end!r} in {u}")
    return t[i:j + len(end)].replace(" | ", " ").strip()
def zrev(k, date, start, end):
    for r in ZUM[k]["reviews"]["sources"]["google"]["reviews"]:
        if datetime.date.fromtimestamp(r["date"]).isoformat() == date:
            b = re.sub(r"\s+", " ", r["body"]); i = b.find(start); j = b.find(end, i)
            if i < 0 or j < 0: raise SystemExit(f"zrev marker missing {k} {date} {start!r} {end!r}")
            return b[i:j + len(end)]
    raise SystemExit(f"zrev date missing {k} {date}")
def alrev(k, date, start, end):
    for r in ALR[k]["reviews"]:
        if r["submitDate"][:10] == date:
            b = re.sub(r"\s+", " ", r["detail"]); i = b.find(start); j = b.find(end, i)
            if i < 0 or j < 0: raise SystemExit(f"alrev marker missing {k} {date}")
            return b[i:j + len(end)]
    raise SystemExit(f"alrev date missing {k} {date}")

# short keys
K = {"woodland": "12 van riper rd|07645", "highlands": "40 e hanover ave|07950", "alister": "1 washington ave|07960",
     "woodmont": "100 fieldstone dr|07856", "edge": "11 us hwy 1|08901", "plaza": "1 richmond st|08901",
     "brunswick": "100 hiram sq|08901", "george": "285 george st|08901", "premiere": "7 livingston ave|08901",
     "gardens": "one chester circle|08901", "eleven80": "1180 raymond blvd|07102", "cosmo": "440 elizabeth ave|07112",
     "urby": "155 washington st|07102", "symphony": "1009 broad st|07102", "rail": "4828 tonnelle ave|07047",
     "noble": "7711 river rd|07047", "molly": "920 belmont ave|07508", "halstead": "1715 us hwy 46|07054",
     "district": "1515 route 10|07054", "avalon": "7000 avalon way|08854", "villas": "1636 stelton rd|08854",
     "centurion": "1222 s ave|07062", "quail": "2005 quail ridge dr|08536", "parksq": "1 park sq|07065",
     "mint": "81 monroe st|07065", "riverdale": "6000 riverdale rd|07457", "park": "417 raritan rd|07203",
     "parc": "400 cardinal ct|07852", "morgans": "1101 klimek pl|08879"}
assert set(K.values()) == set(BY), set(BY) - set(K.values())
def L(k): return BY[K[k]]["building_url"]          # listing / building page url
def Z(k): return ZUM[K[k]]["url"]
def ZT(k): return ZUM[K[k]]["at"]
def name(k): return BY[K[k]]["building_name"]

SITE = {"alister": "https://www.alistermorristown.com/", "woodmont": "https://www.woodmontwest.net/", "edge": "https://www.theedgeatraritanheights.com/",
        "plaza": "https://plazasquareapts.com/", "premiere": "https://www.rentpremiere.com/", "gardens": "https://thegardensatraritan.com/",
        "eleven80": "https://www.eleven80rentals.com/", "rail": "https://www.therailnorthbergen.com/", "molly": "https://livemollybrook.com/",
        "halstead": "https://www.halsteadparsippany.com/", "district": "https://www.district1515.com/", "avalon": "https://www.avaloncommunities.com/new-jersey/piscataway-apartments/avalon-piscataway",
        "villas": "https://www.thevillasatfairway.com/", "mint": "https://www.themintrahway.com/", "riverdale": "https://www.liveatriverdale.com/",
        "park": "https://www.theparknewjersey.com/", "morgans": "https://www.morgansbluff.com/", "noble": "https://www.noblenj.com/",
        "centurion": "https://livecenturion.com/sleepy-hollow/", "parksq": "https://www.parksquareapt.com/", "highlands": "https://www.highlandsmorrisplains.com/",
        "woodland": "https://map.liveatwoodlandsquare.com/", "parc": "https://parcatroxbury.com/"}
SITE_NOTE = {"alister": "own site HTTP 403", "premiere": "own site HTTP 403", "eleven80": "own site HTTP 403", "rail": "own site HTTP 403",
             "mint": "own site HTTP 403", "riverdale": "own site HTTP 403", "morgans": "own site HTTP 403", "parksq": "own site HTTP 403",
             "woodland": "own site HTTP 403", "highlands": "own site closed to us by robots.txt", "parc": "own site reviews page 404; home not fetched"}

# ---------------------------------------------------------------- 1. live check
live = []
LIVE_NOTES = {
 ("woodland", "217"): "Only this 1BR is in the window; the other two listed 1BRs (205 at $3,000, 438 at $2,995) are available 2026-12-21, after the window.",
 ("alister", "15-06B"): "Available 2026-12-07, inside the window.",
 ("alister", "11-01B"): "",
 ("woodmont", "1109"): "Unit number suggests building 1, floor 1 (ground floor): confirm on tour.",
 ("woodmont", "5201"): "Available 2026-12-09, inside the window.",
 ("edge", "407"): "", ("edge", "329"): "",
 ("plaza", "2017"): "Apartment List last checked this building's availability on 2026-11-14.", ("plaza", "2065"): "Apartment List last checked this building's availability on 2026-11-14.",
 ("premiere", "1804"): "Shown as available since 2026-09-13 (two months): ask why it has sat.",
 ("gardens", "97-1C"): "Unit number suggests floor 1 of a garden building; no elevator is listed anywhere for this 1948 complex.",
 ("gardens", "108-2A"): "No elevator is listed anywhere for this 1948 garden complex; unit number suggests floor 2.",
 ("eleven80", "08J"): "", ("eleven80", "23A"): "",
 ("rail", "4102"): "Unit number suggests building 4, floor 1 (ground floor): confirm.", ("rail", "3313"): "",
 ("molly", "1-306"): "Price is $5 lower than stored ($2,543).", ("molly", "2-102"): "Price is $5 lower than stored ($2,638). Unit number suggests floor 1 (ground floor): confirm.",
 ("halstead", "1103"): "Shown as available since 2026-09-07. Unit number suggests floor 1 (ground floor): confirm. Zumper lists this address as Modera Parsippany.", ("halstead", "2182"): "Listed as available since 2026-05-14 (six months): ask why it has sat. Zumper lists this address as Modera Parsippany.",
 ("district", "1-219"): "Listed as available since 2026-08-17. One of the three communities here (Mason East) is 55+: confirm which community this unit is in.",
 ("district", "1-234"): "One of the three communities here (Mason East) is 55+: confirm which community this unit is in.",
 ("villas", "3316"): "", ("villas", "4312"): "",
 ("centurion", "403"): "Apartment List source feed is show_me_the_rent; last checked 2026-11-14.",
 ("mint", "307-A"): "", ("mint", "331-A"): "",
 ("riverdale", "3-117"): "Unit number suggests building 3, floor 1 (ground floor): confirm.", ("riverdale", "4-412"): "",
 ("park", "2804"): "", ("park", "2322"): "",
 ("morgans", "3307"): "",
}
alparsed = {}
for k, key in K.items():
    u = L(k)
    if "apartmentlist" not in u: continue
    fl_html = open(idx[u]["path"], encoding="utf-8", errors="replace").read()
    Lst = None
    for fn in [getattr(A, x) for x in dir(A) if "listing" in x.lower() and callable(getattr(A, x))]:
        try:
            Lst = fn(fl_html)
            if isinstance(Lst, dict) and "available_units" in Lst: break
        except Exception: pass
    alparsed[k] = Lst
    units = {x["name"]: x for fp in Lst["available_units"] for x in (fp.get("units") or [])}
    r = BY[key]
    for un, rent in zip([x.strip() for x in r["unit_list"].split(",")], [x.strip() for x in r["rents"].split(",")]):
        if k == "avalon": continue
        x = units.get(un)
        if not x:
            live.append([key, u, un, "gone", "", "", "no", SITE.get(k, ""), at(u), "Unit no longer in the page's unit list."]); continue
        price = x["price"]; same = str(price) == rent
        note = LIVE_NOTES.get((k, un), "")
        if SITE_NOTE.get(k): note = (note + " " if note else "") + "Price from Apartment List (" + SITE_NOTE[k] + ")."
        elif k in SITE: note = (note + " " if note else "") + "Price from Apartment List; the building's own site shows no unit prices in its HTML."
        live.append([key, u, un, "live" if same else "changed", price, f"{x['availability']} {x['available_on']}", "yes" if same else "no", SITE.get(k, ""), at(u), note.strip()])
# Avalon Piscataway: own site
AV = SITE["avalon"]
avh = open(idx[AV]["path"], encoding="utf-8", errors="replace").read()
i = avh.find('"unitId":"AVB-NJ031-005-5106"'); assert i > 0
seg = avh[i:i + 2600]
assert '"floorNumber":"1"' in seg and '"price":2520,"totalPrice":2628' in seg and '"availableDateUnfurnished":"2026-11-16' in seg and '"leaseTerm":20' in seg
live.append([K["avalon"], AV, "005-5106", "live", 2520, "available 2026-11-16 (VacantAvailable)", "yes", AV, at(AV),
             "From AvalonBay's own page: $2,520 base on a 20-month lease, $2,628 with required monthly fees. The unit is on FLOOR 1 (floorNumber 1): fails the no-ground-floor gate. Address on Avalon's page is 5000 Avalon Way #5106. Apartment List shows $2,485 for the same unit (fetched " + at(L("avalon")) + ")."])
# Trulia building pages
TR_NOTES = {
 ("highlands", "1200"): "Special on page: 'Up to 2-months free.' good until 2026-11-30. Own site closed to us by robots.txt.",
 ("brunswick", "100-502"): "", ("brunswick", "5-204"): "",
 ("george", "N/A-0508"): "",
 ("cosmo", "1008"): "Available Nov 16. Special: 1 month free applied to the second month, select units, until 2026-12-31.",
 ("urby", "155-1001"): "Available Dec 4, inside the window. Required: $50 monthly amenity fee plus a utility billing fee.",
 ("urby", "155-1412"): "Available Nov 19. Required: $50 monthly amenity fee plus a utility billing fee.",
 ("symphony", "206E"): "The page's description is for 'ENCORE', a 63-home building; the page title is Symphony (56 units). Confirm which building the unit is in. Special: 2 months free on an 18-month lease.",
 ("symphony", "207E"): "Same as 206E: description names ENCORE, title names Symphony. Confirm the building.",
 ("quail", "4522"): "Required: bulk internet and cable $95/month plus a $5.25 utility service fee. No elevator is listed for this garden community.",
 ("quail", "2215"): "Studio. Required: bulk internet and cable $95/month plus a $5.25 utility service fee. No elevator is listed for this garden community.",
 ("parksq", "2311"): "Available Dec 4, inside the window. Special: $1,500 off the 2nd month. Own site HTTP 403.",
 ("parc", "N/A-0715"): "", ("parc", "N/A-1018"): "Available 2026-11-20.",
}
for k, key in K.items():
    u = L(k)
    if "trulia" not in u: continue
    h = open(idx[u]["path"], encoding="utf-8", errors="replace").read()
    hd = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S).group(1))["props"]["homeDetails"]
    units = {}
    for g in (hd.get("floorPlans") or {}).get("floorPlanGroups") or []:
        for p in g["plans"]:
            for x in p.get("units") or []:
                units[x["name"].replace("Unit ", "")] = x
    r = BY[key]
    if k == "noble":
        plans = {p["name"]: p for g in hd["floorPlans"]["floorPlanGroups"] for p in g["plans"]}
        p = plans["Alcove Studios"]; assert p["priceRange"]["formattedPrice"] == "$2,550"
        live.append([key, u, "(no unit number: floor plan 'Alcove Studios')", "live", 2550, p["availabilityText"], "yes", SITE["noble"], at(u),
                     "Plan-level price only; the page lists 0 available units ('availableRentalUnits': 0) and no unit numbers. New building: own site says opening October 15, 2026. Own site shows no prices in its HTML. The Zumper copy of this building has no pet policy data."])
        continue
    for un, rent in zip([x.strip() for x in r["unit_list"].split(",")], [x.strip() for x in r["rents"].split(",")]):
        x = units.get(un)
        if not x:
            live.append([key, u, un, "gone", "", "", "no", SITE.get(k, ""), at(u), "Unit no longer in the page's unit list."]); continue
        price = x["priceRange"]["min"]; same = str(int(price)) == rent
        live.append([key, u, un, "live" if same else "changed", int(price), x["availabilityText"] + (" (" + x["availabilityDate"][:10] + ")" if x.get("availabilityDate") else ""),
                     "yes" if same else "no", SITE.get(k, ""), at(u), TR_NOTES.get((k, un), "")])

# ---------------------------------------------------------------- 2. confirm
conf = []
def C(k, fact, value, quote, src, status): conf.append([K[k], fact, value, quote, src, status])
def AM(k):  # Apartment List amenity names
    Lst = alparsed[k]; return [a["display_name"] for a in (Lst.get("community_amenities") or []) + (Lst.get("unit_amenities") or [])]
def el_al(k, extra=""):
    if "Elevator" in AM(k): C(k, "elevator", "yes" + extra, "Elevator (in the page's community amenities list)", L(k), "confirmed")
    else: C(k, "elevator", "not listed" + extra, "No 'Elevator' entry in the Apartment List amenities list for this building", L(k), "unconfirmed")
def tr_feats(k):
    h = open(idx[L(k)]["path"], encoding="utf-8", errors="replace").read()
    hd = json.loads(re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S).group(1))["props"]["homeDetails"]
    import h_trulia as T
    return T.flat_features(hd.get("features")), ((hd.get("description") or {}).get("value") or "")
def el_tr(k, extra=""):
    f, d = tr_feats(k)
    if any(x[-1] == "Elevator" for x in f): C(k, "elevator", "yes" + extra, "Elevator (listed under Levels, Entrance, & Accessibility)", L(k), "confirmed")
    else: C(k, "elevator", "not listed" + extra, "No 'Elevator' entry in the Trulia features list for this building", L(k), "unconfirmed")
def tr_has(k, s):
    f, d = tr_feats(k); assert any(s in x[-1] for x in f) or s in d, (k, s); return s
def al_pet(k, field, sub="general"):
    v = (alparsed[k]["pet_policies"].get(sub) or {}).get(field); assert v, (k, field); return H.unescape(str(v))
FLOOR_INF = "inferred from the unit number; not stated on any page"

# Woodland Square
el_al("woodland")
C("woodland", "floor", "unit 217: floor 2 (inferred)", FLOOR_INF, L("woodland"), "unconfirmed")
C("woodland", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("woodland"), "confirmed")
C("woodland", "dog_weight_limit", "unconfirmed", "Apartment List gives no weight limit. Own site (map.liveatwoodlandsquare.com) returned HTTP 403; a Redfin page that a web search said carries a limit returned HTTP 403, so nothing was read.", L("woodland"), "unconfirmed")
# Highlands
el_tr("highlands")
C("highlands", "floor", "unit 1200: unknown", "Unit number does not reveal the floor; Trulia gives none", L("highlands"), "unconfirmed")
C("highlands", "dogs_allowed", "yes", tr_has("highlands", "Cats, small dogs, large dogs allowed"), L("highlands"), "confirmed")
C("highlands", "dog_weight_limit", "no limit", tr_has("highlands", "We love your dogs! No Breed or Weight Restrictions!"), L("highlands"), "confirmed")
# Alister
el_al("alister", "; complex dates to the 1950s per Morristown Green (2018)")
C("alister", "floor", "units 15-06B and 11-01B: unknown", "Unit numbers look like building-unit; no floor on any page", L("alister"), "unconfirmed")
C("alister", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("alister"), "confirmed")
C("alister", "dog_weight_limit", "unconfirmed", "Apartment List gives no weight limit; own site alistermorristown.com returned HTTP 403", L("alister"), "unconfirmed")
# Woodmont West
WF = "https://www.woodmontwest.net/pages/pet_policy.asp"
el_al("woodmont")
C("woodmont", "floor", "unit 1109: floor 1 (inferred, likely ground floor); unit 5201: floor 2 (inferred)", FLOOR_INF, L("woodmont"), "unconfirmed")
C("woodmont", "dogs_allowed", "yes", cut(WF, "Woodmont West welcomes cats and dogs", "per apartment."), WF, "confirmed")
C("woodmont", "dog_weight_limit", "no limit", cut(WF, "Although we do not have a weight limit", "breed restrictions."), WF, "confirmed")
# Edge
el_al("edge")
C("edge", "floor", "unit 329: floor 3 (inferred); unit 407: floor 4 (inferred)", FLOOR_INF, L("edge"), "unconfirmed")
C("edge", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("edge"), "confirmed")
zp = ZUM[K["edge"]]["pet_policy"][1]; assert zp["type"] == "dog"
C("edge", "dog_weight_limit", "under 40 lb", zp["description"].split(" Non-refundable")[0], Z("edge"), "confirmed")
# Plaza Square
el_al("plaza", "; building floors not stated")
C("plaza", "floor", "units 2017 and 2065: unknown", "Unit numbers do not clearly reveal the floor", L("plaza"), "unconfirmed")
PH = "https://plazasquareapts.com/"
C("plaza", "dogs_allowed", "yes", cut(PH, "Renaissance Plaza Square is a pet-friendly community!", "limitations apply."), PH, "confirmed")
C("plaza", "dog_weight_limit", "75 lb per Apartment List; Zumper's data says 150 lb for dogs; own site gives no number", al_pet("plaza", "restrictions"), L("plaza"), "confirmed")
# Brunswick
el_tr("brunswick")
C("brunswick", "floor", "unit 100-502: floor 5 of building 100 (inferred); unit 5-204: floor 2 of building 5 (inferred)", FLOOR_INF, L("brunswick"), "unconfirmed")
C("brunswick", "dogs_allowed", "yes", tr_has("brunswick", "Cats, small dogs, large dogs allowed"), L("brunswick"), "confirmed")
C("brunswick", "dog_weight_limit", "no number stated; 'large dogs allowed'", "Cats, small dogs, large dogs allowed. (Same manager's Parc at Roxbury listing says AION has no weight restrictions, but The George, also AION, states 60 lb.)", L("brunswick"), "unconfirmed")
# George
el_tr("george")
C("george", "floor", "unit 0508: floor 5 (inferred)", FLOOR_INF, L("george"), "unconfirmed")
C("george", "dogs_allowed", "yes", tr_has("george", "Cats, small dogs, large dogs allowed"), L("george"), "confirmed")
C("george", "dog_weight_limit", "60 lb", tr_has("george", "Two pet max. 60 lb. weight limit. $350 one-time pet fee and $40 pet rent."), L("george"), "confirmed")
# Premiere
el_al("premiere")
C("premiere", "floor", "unit 1804: floor 18 (inferred)", FLOOR_INF, L("premiere"), "unconfirmed")
C("premiere", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("premiere"), "confirmed")
C("premiere", "dog_weight_limit", "50 lb", al_pet("premiere", "restrictions"), L("premiere"), "confirmed")
# Gardens at Raritan
GF = "https://thegardensatraritan.com/features-amenities/"
el_al("gardens", "; own site's features page lists none either; built 1948 (Apartment List)")
C("gardens", "floor", "unit 97-1C: floor 1 (inferred, ground floor); unit 108-2A: floor 2 (inferred)", FLOOR_INF, L("gardens"), "unconfirmed")
C("gardens", "dogs_allowed", "yes", cut(GF, "Cats and Dogs OK.", "Call for restrictions."), GF, "confirmed")
C("gardens", "dog_weight_limit", "30 lb", cut(GF, "30 lb. full grown max weight.", "max weight."), GF, "confirmed")
# Eleven80
el_al("eleven80")
C("eleven80", "floor", "unit 08J: floor 8 (inferred); unit 23A: floor 23 (inferred)", FLOOR_INF, L("eleven80"), "unconfirmed")
C("eleven80", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("eleven80"), "confirmed")
C("eleven80", "dog_weight_limit", "35 lb", al_pet("eleven80", "restrictions"), L("eleven80"), "confirmed")
# Cosmo
el_tr("cosmo")
C("cosmo", "floor", "unit 1008: floor 10 (inferred)", FLOOR_INF, L("cosmo"), "unconfirmed")
C("cosmo", "dogs_allowed", "yes", tr_has("cosmo", "Cats, small dogs, large dogs allowed"), L("cosmo"), "confirmed")
C("cosmo", "dog_weight_limit", "no number stated; 'large dogs allowed'", tr_has("cosmo", "Large dogs allowed"), L("cosmo"), "unconfirmed")
# Urby
el_tr("urby", "; 16 floors")
C("urby", "floor", "unit 155-1001: floor 10 (inferred); unit 155-1412: floor 14 (inferred)", FLOOR_INF + ". Page says: " + tr_has("urby", "our 16-story tower"), L("urby"), "unconfirmed")
C("urby", "dogs_allowed", "yes", tr_has("urby", "Cats, small dogs, large dogs allowed"), L("urby"), "confirmed")
C("urby", "dog_weight_limit", "no number stated; 'large dogs allowed'", "Cats, small dogs, large dogs allowed", L("urby"), "unconfirmed")
# Symphony
el_tr("symphony")
C("symphony", "floor", "units 206E and 207E: floor 2 (inferred)", FLOOR_INF, L("symphony"), "unconfirmed")
C("symphony", "dogs_allowed", "small dogs only", tr_has("symphony", "Cats, small dogs allowed"), L("symphony"), "confirmed")
C("symphony", "dog_weight_limit", "unconfirmed; page says small dogs only, no number, and its dog rows are empty (only 'Cats: 1 pet max')", "Symphony in Newark, NJ allows cats (up to 1) and small dogs (up to 1). Large dogs are not permitted.", L("symphony"), "unconfirmed")
# Rail
el_al("rail")
C("rail", "floor", "unit 4102: floor 1 of building 4 (inferred, likely ground floor); unit 3313: floor 3 of building 3 (inferred)", FLOOR_INF, L("rail"), "unconfirmed")
C("rail", "dogs_allowed", "yes", "Dogs allowed (amenities list); Zumper: dog ok, limit 2, 'Restrictions: Breed Restrictions'", L("rail"), "confirmed")
C("rail", "dog_weight_limit", "unconfirmed; breed restrictions only on Zumper, no number", "| Restrictions: Breed Restrictions", Z("rail"), "unconfirmed")
# Noble
NB = SITE["noble"]
C("noble", "elevator", "yes; residences on floors 3 through 12", cut(NB, "Monitored elevator lobbies on all floors", "all floors"), NB, "confirmed")
C("noble", "floor", "no unit number; every residence is on floor 3 or higher", cut(NB, "Choose a home type", "in the 05 line."), NB, "confirmed")
C("noble", "dogs_allowed", "yes per Trulia; own site says nothing about pets; Zumper copy has no pet data", tr_has("noble", "Cats, small dogs, large dogs allowed"), L("noble"), "unconfirmed")
C("noble", "dog_weight_limit", "no number stated; 'large dogs allowed', 1 pet max", tr_has("noble", "Large dogs allowed"), L("noble"), "unconfirmed")
# Molly Brook
el_al("molly", "; own site's amenities page does not mention one")
C("molly", "floor", "unit 1-306: floor 3 (inferred); unit 2-102: floor 1 (inferred, likely ground floor)", FLOOR_INF, L("molly"), "unconfirmed")
MH = "https://livemollybrook.com/"
C("molly", "dogs_allowed", "yes", cut(MH, "Molly Brook on Belmont is a pet-friendly community!", "community!") + " (Apartment List: dogs allowed, $50 dog rent)", MH, "confirmed")
C("molly", "dog_weight_limit", "unconfirmed", "Own site and Apartment List give no weight limit. Manager is Bozzuto, whose site is closed to us for this.", L("molly"), "unconfirmed")
# Halstead
el_al("halstead")
C("halstead", "floor", "unit 1103: floor 1 (inferred, likely ground floor); unit 2182: unclear", FLOOR_INF, L("halstead"), "unconfirmed")
C("halstead", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: dogs, cats; limit 2", L("halstead"), "confirmed")
C("halstead", "dog_weight_limit", "unconfirmed", "No weight limit on Apartment List or on the own site's amenities page", L("halstead"), "unconfirmed")
# District
DF = "https://www.district1515.com/faq"
el_al("district")
C("district", "floor", "units 1-219 and 1-234: floor 2 (inferred)", FLOOR_INF, L("district"), "unconfirmed")
C("district", "dogs_allowed", "yes", cut(DF, "District 15Fifteen welcomes cats and dogs", "per apartment home."), DF, "confirmed")
C("district", "dog_weight_limit", "no limit stated; fees apply 'regardless of pet size'", cut(DF, "A $500 one-time pet fee per pet", "complete pet guidelines."), DF, "unconfirmed")
# Avalon
C("avalon", "elevator", "yes, for select apartments only", cut(AV, "Elevator access (for select apartments)", "apartments)"), AV, "confirmed")
C("avalon", "floor", "unit 5106: floor 1 (ground floor)", '"unitName":"5106" ... "floorNumber":"1" (unit record in the page data)', AV, "contradicts")
AP = "https://www.avaloncommunities.com/pet-friendly"
C("avalon", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs; 2 pet maximum; Breed restrictions.", L("avalon"), "confirmed")
C("avalon", "dog_weight_limit", "no limit stated; breed list only", cut(AP, "The following breeds are restricted:", "related to above"), AP, "confirmed")
# Villas
el_al("villas", "; own site home page does not mention one")
C("villas", "floor", "unit 3316: floor 3 (inferred); unit 4312: floor 3 (inferred)", FLOOR_INF, L("villas"), "unconfirmed")
C("villas", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("villas"), "confirmed")
C("villas", "dog_weight_limit", "under 40 lb", al_pet("villas", "restrictions").split(" Non-refundable")[0], L("villas"), "confirmed")
# Centurion
CT = "https://www.trulia.com/building/centurion-sleepy-hollow-1222-south-ave-plainfield-nj-07062-2765859619"
el_al("centurion")
C("centurion", "floor", "unit 403: floor 4 (inferred)", FLOOR_INF, L("centurion"), "unconfirmed")
C("centurion", "dogs_allowed", "small dogs only per Trulia; Apartment List and Zumper say dogs allowed, 1 pet", "Centurion Sleepy Hollow in Plainfield, NJ allows cats and small dogs. Large dogs are not permitted.", CT, "confirmed")
C("centurion", "dog_weight_limit", "unconfirmed; 'small dogs' with no number; own site gives no policy", "Cats, small dogs allowed", CT, "unconfirmed")
# Quail Ridge
el_tr("quail", "; garden community of 1,032 units")
C("quail", "floor", "units 4522 and 2215: unknown", "Unit numbers do not reveal the floor", L("quail"), "unconfirmed")
C("quail", "dogs_allowed", "yes", tr_has("quail", "Cats, small dogs, large dogs allowed"), L("quail"), "confirmed")
C("quail", "dog_weight_limit", "no number stated; breed restrictions only", tr_has("quail", "Apartments | Restrictions: Certain Breed Restrictions.  Ask our leasing staff."), L("quail"), "unconfirmed")
# Park Square
el_tr("parksq", "; five floors")
C("parksq", "floor", "unit 2311: floor 3 (inferred)", FLOOR_INF + ". Page says: " + tr_has("parksq", "This distinguished five-story residence"), L("parksq"), "unconfirmed")
C("parksq", "dogs_allowed", "yes", tr_has("parksq", "Cats, small dogs, large dogs allowed"), L("parksq"), "confirmed")
C("parksq", "dog_weight_limit", "80 lb", tr_has("parksq", "80 lbs max weight"), L("parksq"), "confirmed")
# Mint
el_al("mint")
C("mint", "floor", "units 307-A and 331-A: floor 3 (inferred)", FLOOR_INF, L("mint"), "unconfirmed")
C("mint", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("mint"), "confirmed")
C("mint", "dog_weight_limit", "no number stated; breed list only", al_pet("mint", "restrictions"), L("mint"), "unconfirmed")
# Riverdale
el_al("riverdale")
C("riverdale", "floor", "unit 3-117: floor 1 (inferred, likely ground floor); unit 4-412: floor 4 (inferred)", FLOOR_INF, L("riverdale"), "unconfirmed")
C("riverdale", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("riverdale"), "confirmed")
C("riverdale", "dog_weight_limit", "no number stated", al_pet("riverdale", "restrictions"), L("riverdale"), "unconfirmed")
# The Park
PF = "https://www.theparknewjersey.com/faq"
el_al("park", "; own site's amenities and FAQ pages do not mention one")
C("park", "floor", "unit 2322: floor 3 (inferred); unit 2804: unclear", FLOOR_INF, L("park"), "unconfirmed")
C("park", "dogs_allowed", "yes", cut(PF, "Yes! The Park is a pet-friendly community", "pet spa."), PF, "confirmed")
C("park", "dog_weight_limit", "unconfirmed; own site says weight restrictions may apply", cut(PF, "Please contact the leasing office for more details on our pet policy", "may apply."), PF, "unconfirmed")
# Parc at Roxbury
el_tr("parc")
C("parc", "floor", "units 0715 and 1018: unknown (building 7 and building 10; floor not clear)", "Unit numbers do not clearly reveal the floor", L("parc"), "unconfirmed")
C("parc", "dogs_allowed", "yes", tr_has("parc", "Cats, small dogs, large dogs allowed"), L("parc"), "confirmed")
pz = ZUM[K["parc"]]["pet_policy"][1]["description"]; assert "AION does not have weight restrictions in its pet policy." in pz
C("parc", "dog_weight_limit", "no limit", "AION does not have weight restrictions in its pet policy.", Z("parc"), "confirmed")
# Morgan's Bluff
el_al("morgans", "; described as garden-style")
C("morgans", "floor", "unit 3307: floor 3 (inferred)", FLOOR_INF, L("morgans"), "unconfirmed")
C("morgans", "dogs_allowed", "yes", "Dogs allowed (amenities list); pet_policies allowed_pets: cats, dogs", L("morgans"), "confirmed")
C("morgans", "dog_weight_limit", "unconfirmed", "Apartment List gives no weight limit; own site morgansbluff.com returned HTTP 403", L("morgans"), "unconfirmed")

# ---------------------------------------------------------------- 3. items
items = []
def I(k, cat, date, excerpt, site, url, about, t): items.append([K[k], name(k), cat, date, excerpt, site, url, about, t])
def NF(k, where, url): I(k, "none_found", "", where, "", url, "building", at(url) if url in idx else "")
ALS = "Apartment List (resident review on the building page)"
ZG = "Zumper building page (Google review shown by Zumper; Zumper shows only eight reviews, all 5-star)"
BE = "Birdeye profile page (review posted on Birdeye; the page gives only a relative date, so the year is approximate)"
JD1 = "https://jerseydigs.com/eleven80-newark-apartments/"; JD2 = "https://jerseydigs.com/eleven80-newark-evicts-tenant-union-leader/"
MG = "https://morristowngreen.com/2018/04/16/renters-say-landlord-is-forcing-them-out-morristown-councilman-wants-to-revisit-rent-controls/"
N12 = "https://newjersey.news12.com/residents-displaced-by-piscataway-apartment-fire-relocated-to-nearby-hotels"
BW = "https://reviews.birdeye.com/woodmont-west-at-mt-arlington-156811360610697"; BP = "https://birdeye.com/parc-at-roxbury-169688995707859"
BA = "https://reviews.birdeye.com/avalon-piscataway-156816793500464"

I("woodland", "noise", "2025-04-24", alrev(K["woodland"], "2025-04-24", "Between the noise", "common areas."), ALS + "; reviewer scored noise 1 of 5 and parking 1 of 5, overall 5 of 5", L("woodland"), "building", at(L("woodland")))
NF("highlands", "Birdeye profile shows a rating (4.2 from 111) but no review text. Own site highlandsmorrisplains.com is closed to us by robots.txt. modernmsg.com resident-review page is deactivated. Trulia and Zumper pages carry no reviews. Web search found no news, police or court items; it pointed to review aggregators (wanderlog, wheree) that were not read.", "https://reviews.birdeye.com/the-highlands-at-morris-plains-apartments-156720906550002")
I("alister", "management", "2018-04-16", cut(MG, "Over the last month, tenants from the Alister apartments", "late rent payments."), "Morristown Green (local news)", MG, "management_company", at(MG))
I("alister", "other", "2018-04-16", cut(MG, "a representative of Mill Creek Residential", "investigate these complaints."), "Morristown Green (local news); shows Mill Creek Residential took over in 2017", MG, "management_company", at(MG))
I("woodmont", "management", "2024-08-16", alrev(K["woodmont"], "2024-08-16", "Moving in the apartment was not cleaned.", "broken equipment."), ALS + "; overall 4 of 5", L("woodmont"), "building", at(L("woodmont")))
I("woodmont", "management", "2024-08-16", alrev(K["woodmont"], "2024-08-16", "I'm not a fan", "every month"), ALS + "; overall 4 of 5", L("woodmont"), "building", at(L("woodmont")))
I("woodmont", "positive", "2024-08-15", alrev(K["woodmont"], "2024-08-15", "Management is very responsive", "easily accessible."), ALS, L("woodmont"), "building", at(L("woodmont")))
I("woodmont", "other", "2021", cut(BW, "The complex is too big and the parking is a nightmare.", "two your car."), BE + " ('5 years ago'); a parking and towing-threat complaint, not a theft", BW, "garage_or_lot", at(BW))
I("woodmont", "noise", "2021", cut(BW, "the floor and walls are thin", "if you complained."), BE + " ('5 years ago')", BW, "building", at(BW))
I("woodmont", "management", "2022", cut(BW, "management is full of pushovers.", "fake apologies"), BE + " ('4 years ago')", BW, "management_company", at(BW))
NF("edge", "Own site reviews page shows four undated, all-positive testimonials (not recorded). Renter's Voice page: 'No reviews found.' Apartment List and Zumper pages carry no reviews. Web search found no news, police or court items; it pointed to a BBB complaints page for the manager, Edgewood Properties, which was not fetched (bbb.org returns HTTP 403 to us).", "https://www.rentersvoice.com/reviews/nj/new-brunswick/the-edge-at-raritan-heights")
I("plaza", "management", "2024-08-15", alrev(K["plaza"], "2024-08-15", "maintenance is usually good", "to fix it."), ALS + "; overall 4 of 5", L("plaza"), "building", at(L("plaza")))
I("plaza", "noise", "2024-08-15", alrev(K["plaza"], "2024-08-15", "Right on the bridge", "loud at night"), ALS + "; overall 4 of 5", L("plaza"), "street", at(L("plaza")))
I("plaza", "other", "2024-08-15", alrev(K["plaza"], "2024-08-15", "Garage parking is $150 a month.", "changing apparently."), ALS + "; overall 4 of 5", L("plaza"), "building", at(L("plaza")))
I("brunswick", "positive", "2022-01-03", zrev(K["brunswick"], "2022-01-03", "I moved in back in 2020", "dramatically improved."), ZG + "; overall Google score there is 2.8 from 69", Z("brunswick"), "management_company", ZT("brunswick"))
I("brunswick", "none_found", "", "No dated negative text could be read although the scores are low (Google 2.8 from 69 as shown by Zumper; Birdeye 3.1 from 80). Birdeye shows two old complaints imported from Apartments.com (flooding by maintenance, mice), which is an off-limits source, so they are not recorded. Web search found no news, police or court items.", "", "https://birdeye.com/the-brunswick-169689000297323", "building", at("https://birdeye.com/the-brunswick-169689000297323"))
I("george", "safety_incident", "2022-12-19", zrev(K["george"], "2022-12-19", "There are some issues with homeless people", "hallways"), ZG + "; overall Google score there is 3.6 from 26", Z("george"), "building", ZT("george"))
I("george", "positive", "2023-09-01", zrev(K["george"], "2023-09-01", "This is our 8th year living here.", "well-thought-out."), ZG, Z("george"), "building", ZT("george"))
NF("premiere", "Apartment List and Zumper pages carry no reviews. Own site rentpremiere.com returned HTTP 403; Pennrose's page for the building has no reviews. Web search found only marketing and project pages.", "https://www.pennrose.com/apartments/new-jersey/premiere-residences/")
I("gardens", "positive", "2024-02-03", zrev(K["gardens"], "2024-02-03", "the way they organize the parkings is great", "find your spot"), ZG + "; overall Google score there is 4.4 from 211", Z("gardens"), "garage_or_lot", ZT("gardens"))
I("gardens", "other", "2024-09-25", zrev(K["gardens"], "2024-09-25", "Wish the laundry room was open later", "not all of us work 9-5"), ZG, Z("gardens"), "building", ZT("gardens"))
I("eleven80", "safety_incident", "2026-01-16", cut(JD1, "Last year, on September 17th, a security guard was attacked twice", "with a knife."), "Jersey Digs (local news); the attack was on 2025-09-17", JD1, "building", at(JD1))
I("eleven80", "safety_incident", "2026-01-16", cut(JD1, "The front doors still remain unlocked", "times of the day."), "Jersey Digs (local news)", JD1, "building", at(JD1))
I("eleven80", "safety_incident", "2026-01-16", cut(JD1, "One such stranger, an unidentified man", "locker room."), "Jersey Digs (local news)", JD1, "building", at(JD1))
I("eleven80", "management", "2026-01-16", cut(JD1, "“Everything is broken", "about the intruder,”"), "Jersey Digs (local news); a ten-year resident who moved out", JD1, "management_company", at(JD1))
I("eleven80", "management", "2026-04-22", cut(JD2, "Making matters worse, the leader of their tenant union", "legal action."), "Jersey Digs (local news)", JD2, "management_company", at(JD2))
I("eleven80", "management", "2026-04-22", cut(JD2, "But the lawsuit alleges other problems", "the city’s limit."), "Jersey Digs (local news); a tenant lawsuit in Superior Court against the owner and Cushman & Wakefield", JD2, "management_company", at(JD2))
I("eleven80", "management", "2026-04-22", cut(JD2, "Dwyer admits that the apartment needs repairs", "past five years."), "Jersey Digs (local news)", JD2, "management_company", at(JD2))
I("eleven80", "positive", "2024-11-14", zrev(K["eleven80"], "2024-11-14", "My experience with maintenance", "good one."), ZG + "; overall Google score there is 4.3 from 146 (pulled 2024-12-07)", Z("eleven80"), "building", ZT("eleven80"))
NF("cosmo", "Trulia page carries no reviews; the Zumper address page is a single unit with no reviews. Web search found no news, police or court items about the current building; it pointed to a Jersey Digs history piece on the former Carmel Towers at this site, which was not read.", L("cosmo"))
NF("urby", "Trulia page carries no reviews; Zumper has no building page at this address. Own site urby.com is behind Cloudflare (SOURCES.md). Web search found no news, police or court items; it pointed to review aggregators (veryapt, safebutler, wheree) that were not read.", L("urby"))
NF("symphony", "Trulia page carries no reviews; Zumper has no building page at this address. Web search found only listing pages (the building is new).", L("symphony"))
I("rail", "other", "2024-05-24", zrev(K["rail"], "2024-05-24", "Package Room needs more organization.", "it was not cheap."), ZG + "; overall Google score there is 4.4 from 106 (pulled 2025-03-26); property was then called Solo at North Bergen", Z("rail"), "building", ZT("rail"))
I("rail", "other", "2024-08-31", zrev(K["rail"], "2024-08-31", "I do wish the garage parking was free", "free"), ZG, Z("rail"), "garage_or_lot", ZT("rail"))
I("rail", "positive", "2025-01-24", zrev(K["rail"], "2025-01-24", "Love the property", "modern it is!"), ZG, Z("rail"), "building", ZT("rail"))
NF("noble", "New building (own site: opening October 15, 2026), so there are no resident reviews. Trulia and Zumper pages carry none. Web search found only listing pages.", SITE["noble"])
NF("molly", "Apartment List page carries no reviews; Zumper has no page at this address; own site has none. Web search found only listing pages. Manager Bozzuto's review pages are closed to us by robots.txt.", L("molly"))
NF("halstead", "Apartment List and Zumper pages carry no reviews; Renter's Voice page: 'No reviews found.' Web search found no news, police or court items; it pointed to a review aggregator (wheree) summarising elevator outages and false fire alarms, which was not read and is not recorded.", "https://www.rentersvoice.com/reviews/nj/parsippany-troy-hills/halstead-parsippany")
NF("district", "Opened 2025 to 2026. Apartment List page carries no reviews; Zumper has no page at this address; own site has none. Web search found only listing pages.", L("district"))
I("avalon", "other", "2024-08-02", cut(N12, "It quickly became clear to the residents at the Avalon Piscataway apartment complex", "weren’t a drill."), "News 12 New Jersey; a mulch fire spread to a building on 2024-08-01", N12, "building", at(N12))
I("avalon", "other", "2024-08-02", cut(N12, "All the families have been displaced.", "heavily damaged."), "News 12 New Jersey; about 20 families", N12, "building", at(N12))
I("avalon", "noise", "2024-08-02", cut(N12, "“Sometimes we get false alarms", "to check.”"), "News 12 New Jersey; a displaced resident on false fire alarms", N12, "building", at(N12))
I("avalon", "management", "2021", cut(BA, "We pay online every single month", "water and sewer"), BE + " ('5 years ago'); a billing and collections complaint", BA, "management_company", at(BA))
NF("villas", "Apartment List page carries no reviews; the Zumper address page is one unit with no reviews; own site home page has none. Web search found no news, police or court items; it pointed to listing-site reviews (a 2024 deposit dispute) on pages that were not read.", L("villas"))
NF("centurion", "Opened for leasing in 2026. Apartment List, Zumper and Trulia pages carry no reviews; own site has none. Web search found only opening and leasing coverage.", L("centurion"))
I("quail", "positive", "2023-11-16", zrev(K["quail"], "2023-11-16", "I had an emergency", "my call"), ZG + "; overall Google score there is 3.6 from 317 (pulled 2024-11-21), so the low reviews exist but are not shown", Z("quail"), "management_company", ZT("quail"))
I("quail", "none_found", "", "No dated negative text could be read although the Google score is 3.6 from 317. Web search pointed to mold and maintenance complaints on RentCafe, Rent.com and Point2Homes pages and to a BBB profile; Rent.com and bbb.org are blocked for us and the others were not read. Nothing from them is recorded.", "", Z("quail"), "building", ZT("quail"))
NF("parksq", "Birdeye profile shows a rating (4.2 from 95) and two Facebook entries with no text. Trulia and Zumper pages carry no reviews. Own site parksquareapt.com returned HTTP 403. Web search found no news, police or court items.", "https://reviews.birdeye.com/park-square-156778471297509")
I("mint", "elevator", "2022-08-05", zrev(K["mint"], "2022-08-05", "The elevator has been down once in a while", "supply chain issues."), ZG + "; overall Google score there is 4.2 from 72 (pulled 2025-02-06)", Z("mint"), "building", ZT("mint"))
I("mint", "positive", "2023-02-07", zrev(K["mint"], "2023-02-07", "The building is always clean", "responded to"), ZG, Z("mint"), "building", ZT("mint"))
NF("riverdale", "Apartment List page carries no reviews; Zumper lists the address under its old name (Alexan Riverdale) with no reviews. Own site liveatriverdale.com and the BBB profile both returned HTTP 403. Web search found no news, police or court items; it pointed to listing-site reviews (rude management, thin walls, limited parking) on pages that were not read.", L("riverdale"))
I("park", "none_found", "", "Birdeye profile shows a rating (3.6 from 380) and four Facebook entries from 2017 to 2020, all positive (not recorded: too old to matter). Bozzuto's own reviews page for The Park is closed to us by robots.txt; modernmsg.com page is deactivated. Web search found no news, police or court items; it pointed to aggregator summaries (parking shortage, lost packages) that were not read.", "", "https://reviews.birdeye.com/the-park-156778018221722", "building", at("https://reviews.birdeye.com/the-park-156778018221722"))
I("parc", "management", "2025", cut(BP, "There is a serious lack of communication", "for years."), BE + " ('a year ago')", BP, "management_company", at(BP))
I("parc", "management", "2025", cut(BP, "The doors to the buildings may, or may not, lock.", "not repaired."), BE + " ('a year ago'); a building-security complaint, no incident reported", BP, "building", at(BP))
I("parc", "management", "2025", cut(BP, "Nice place until you have a problem", "nobody responds."), BE + " ('a year ago'; same reviewer as the two rows above)", BP, "management_company", at(BP))
I("parc", "positive", "2024", cut(BP, "John and Stephanie were fantastic.", "immediately."), BE + " ('2 years ago')", BP, "building", at(BP))
I("morgans", "positive", "2024-08-19", alrev(K["morgans"], "2024-08-19", "Morgans bluff is tremendous", "residency."), ALS, L("morgans"), "building", at(L("morgans")))
I("morgans", "none_found", "", "Birdeye profile shows a rating (3.8 from 87) and six Facebook entries from 2017 to 2019, all positive (not recorded). Own site morgansbluff.com returned HTTP 403; modernmsg.com page is deactivated. Web search found no news, police or court items; it pointed to aggregator summaries (package thefts, slow maintenance, abandoned cars) that were not read.", "", "https://reviews.birdeye.com/morgans-bluff-156778729020725", "building", at("https://reviews.birdeye.com/morgans-bluff-156778729020725"))
items = [x for x in items if x]

# ---------------------------------------------------------------- 4. facts
facts = []
def F(k, fact, value, quote, src): facts.append([K[k], fact, value, quote, src])
def alf(k, field): return H.unescape(str(alparsed[k].get(field) or "")).strip()
for k in K:
    u = L(k)
    if "apartmentlist" not in u: continue
    Lst = alparsed[k]
    if Lst.get("pmc_display_name"): F(k, "management_company", Lst["pmc_display_name"], "pmc_display_name: " + Lst["pmc_display_name"], u)
    if Lst.get("year_built"): F(k, "year_built", str(Lst["year_built"]) + (f"; remodeled {Lst['year_remodeled']}" if Lst.get("year_remodeled") else ""), f"year_built: {Lst['year_built']}", u)
    if Lst.get("total_units_count"): F(k, "total_units", str(Lst["total_units_count"]), f"total_units_count: {Lst['total_units_count']}", u)
    pk = alf(k, "parking_details_text") or "; ".join(str(p.get("comment")) + (f" (${p['space_fee']})" if p.get("space_fee") else "") for p in (Lst.get("parking") or []) if p.get("comment"))
    if pk: F(k, "parking", pk, pk, u)
    g = Lst["pet_policies"].get("general") or {}; d = Lst["pet_policies"].get("dogs") or {}
    pr = d.get("rent") or g.get("rent"); pf = d.get("fee") or g.get("fee")
    if pr or pf: F(k, "pet_rent_and_fee", f"pet rent: {H.unescape(str(pr or 'not stated')).replace('$$', '$')}; one-time fee: {H.unescape(str(pf or 'not stated')).replace('$$', '$')}", json.dumps({"rent": pr, "fee": pf, "limit": d.get("limit") or g.get("limit")}), u)
    add = "; ".join(x for x in [alf(k, "additional_fees_text"), alf(k, "move_in_fees_text"), alf(k, "utilities_included_text") and "Utilities included: " + alf(k, "utilities_included_text")] if x).replace("$$", "$")
    if add: F(k, "fees_and_utilities", add, add, u)
    am = AM(k)
    if "Pool" in am: F(k, "pool", "yes (indoor or outdoor not stated)", "Pool (amenities list)", u)
    dm = [a for a in am if re.search("doorman|concierge", a, re.I)]
    if dm: F(k, "doorman", ", ".join(dm), ", ".join(dm) + " (amenities list)", u)
F("woodmont", "pet_rent_and_fee", "one-time $500 per pet; $50 per pet monthly; $30 per pet yearly PetScreening fee", cut(WF, "One-time pet fee of $500 per pet", "$30 per pet"), WF)
F("highlands", "parking", "covered $135, garage $100, surface lot $85 per month (optional fees)", "Covered parking fee ($135); Garage parking fee ($100); Surface lot parking fee ($85)", L("highlands"))
F("highlands", "required_fees", "community amenities usage fee and internet fee, amounts not stated", "Community amenities usage fee: Contact for details; Internet fee: Contact for details", L("highlands"))
F("highlands", "year_built", "2003", "year_built: 2003 (Zumper building data)", Z("highlands"))
F("highlands", "name", "Highlands at Morris Plains", "Highlands at Morris Plains Apartments - 40 E Hanover Ave Morris Plains", Z("highlands"))
F("alister", "management_change", "Mill Creek Residential acquired the complex in 2017; formerly Jacob Ford Village", cut(MG, "a representative of Mill Creek Residential, which acquired the complex last year", "last year"), MG)
F("brunswick", "pet_rent_and_fee", "$50 monthly; $300 one-time", tr_has("brunswick", "$50 monthly pet fee") + "; " + tr_has("brunswick", "$300 One-time pet fee"), L("brunswick"))
F("brunswick", "parking", "off-street parking, 1 car per resident; fee not stated", tr_has("brunswick", "Parking Policy: Off street parking available. 1 car per resident. Please call us regarding our Parking Policy."), L("brunswick"))
F("brunswick", "management_company", "AION Management (took over after 2020 per a resident review; formerly Riverwatch Commons)", zrev(K["brunswick"], "2022-01-03", "I moved in back in 2020", "now Aion."), Z("brunswick"))
F("brunswick", "required_fees", "trash, utility administrative billing fee, electric, water and sewer billed on top of rent; amounts not stated", "Trash Service; Utility - Administrative Billing Fee; Utility - Electric Service; Utility - Water/Sewer Service", L("brunswick"))
F("george", "parking", "no on-site parking: permit at a nearby deck $185/month, or $100/month at The Brunswick if available", tr_has("george", "Parking permits are available at a nearby parking deck for $185/month when you show your lease."), L("george"))
F("george", "pet_rent_and_fee", "$350 one-time; pet rent $40 (policy text) or $50 (fee table) monthly", "Two pet max. 60 lb. weight limit. $350 one-time pet fee and $40 pet rent. / $50 monthly pet fee", L("george"))
F("george", "required_fees", "trash, utility administrative billing fee, electric, water and sewer billed on top of rent; amounts not stated", "Trash Service; Utility - Administrative Billing Fee; Utility - Electric Service; Utility - Water/Sewer Service", L("george"))
PN = "https://www.pennrose.com/apartments/new-jersey/premiere-residences/"
F("premiere", "pool_and_concierge", "rooftop pool and deck; 24-hour concierge", cut(PN, "Community amenities include a rooftop pool and deck", "emergency call service."), PN)
F("gardens", "pet_rent_and_fee", "$35 monthly; $300 non-refundable", cut(GF, "$300.00 non-refundable pet damage fee", "monthly pet fee"), GF)
F("gardens", "management_company", "Renaissance Management Group", cut(GF, "Property managed by Renaissance Management Group", "Group"), GF)
F("eleven80", "management_company", "Cushman & Wakefield since about 2020 (before that Cogswell, per a search summary of a TAPinto article that we cannot read); owner Pacific Oak Strategic Opportunity REIT, which put the building up for sale in 2025", cut(JD1, "Amid all of these mounting problems, last year", "as the broker."), JD1)
F("cosmo", "parking", "garage, $195 per month (optional)", "Parking fee ($195)", L("cosmo"))
F("cosmo", "special", "1 month free applied to the second month, select units, until 2026-12-31", "1 Month free applied to your second month!", L("cosmo"))
F("urby", "required_fees", "$50 monthly amenity fee plus a monthly utility billing fee", "Monthly Amenity Fee Charge ($50 each); Monthly Utility Billing Fee", L("urby"))
F("urby", "pet_rent_and_fee", "$75 per pet monthly; 2 pet max", tr_has("urby", "$75 monthly pet fee"), L("urby"))
F("symphony", "parking", "attached garage, $200 per vehicle monthly", tr_has("symphony", "$200 Monthly Per Vehicle"), L("symphony"))
F("symphony", "listing_identity", "page titled Symphony (56 units) but its description is for ENCORE (63 residences)", tr_has("symphony", "Welcome to ENCORE a brand-new residential community"), L("symphony"))
F("rail", "name_change", "formerly Solo at North Bergen (Zumper's URL and its 2024 Google reviews use that name)", zrev(K["rail"], "2024-08-14", "Solo apartments are beautiful", "great amenities."), Z("rail"))
F("noble", "parking", "interior garage $175 per month; exterior $100 per month; no amenity fee", cut(NB, "Interior parking garage — $175 per month", "$100 per month"), NB)
F("noble", "doorman", "24-hour doorman", cut(NB, "elegant lobby with 24-hour doorman service", "service"), NB)
F("noble", "opening", "new building, opening October 15, 2026", cut(NB, "Luxury impeccably designed waterfront rentals coming October 15, 2026", "2026"), NB)
F("noble", "special", "first month free on homes under $5,000 with a 13-month lease", cut(NB, "1st month free", "13-month lease"), NB)
F("halstead", "name_change", "Zumper lists 1715 US-46 as Modera Parsippany", ZUM[K["halstead"]]["title"], Z("halstead"))
F("district", "age_restriction", "three communities at this address; Mason East is 55+, Mason and Smyth are not", cut(DF, "Mason East at District 15Fifteen is an active adult community", "55 and older."), DF)
F("district", "parking", "covered garage; first vehicle guaranteed a garage space; fee not stated", cut(DF, "Covered garage parking is available", "first-served basis."), DF)
F("district", "pet_rent_and_fee", "$500 one-time per pet; $50 monthly per pet", cut(DF, "A $500 one-time pet fee per pet", "pet size."), DF)
F("avalon", "required_fees", "$108 a month on top of base rent for unit 5106 ($2,520 base, $2,628 total)", cut(AV, "The total price displayed includes base rent and all required monthly fees", "fees") if "The total price displayed includes base rent and all required monthly fees" in page(AV) else '"price":2520,"totalPrice":2628', AV)
F("centurion", "parking", "fully covered parking; fee not stated", "Fully Covered Parking", "https://livecenturion.com/sleepy-hollow/amenities/")
F("quail", "required_fees", "bulk internet and cable $95 per month; utility service fee $5.25; water and sewer billed", "Bulk Internet and Cable ($95 each); Utility Service Fee ($5.25 each)", L("quail"))
F("quail", "pet_rent_and_fee", "$50 monthly; $500 one-time", tr_has("quail", "$50 monthly pet fee") + "; " + tr_has("quail", "$500 One-time pet fee"), L("quail"))
F("quail", "special", "one month free on select 1 and 2 bedrooms with a move-in by 2026-11-30", "One month free on select 1 and 2 bedrooms with a move in by 11/30/2026. Restrictions apply!", L("quail"))
F("parksq", "pet_rent_and_fee", "$50 monthly per dog; $350 one-time per dog", "Dog rent ($50 per dog); Dog fee ($350 per dog)", L("parksq"))
F("parksq", "parking", "secured garage; fee not stated", tr_has("parksq", "Secured Garage"), L("parksq"))
F("riverdale", "name_change", "Zumper lists 6000 Riverdale Rd as Alexan Riverdale (the earlier name); year built 2010", ZUM[K["riverdale"]]["title"], Z("riverdale"))
F("parc", "pet_rent_and_fee", "$350 one-time per pet; $50 monthly per pet; two pets maximum", "Pet Fees: (one-time non-refundable): $350 per pet (due at move-in) and monthly pet rent is $50 for per pet. Two pets maximum.", Z("parc"))
F("parc", "management_company", "AION Management", "AION allows residents to have dogs, cats and service animals.", Z("parc"))
F("parc", "required_fees", "pest control, trash, utility billing fee, electric, gas, water and sewer billed on top of rent; amounts not stated", "Pest Control; Trash Service; Utility - Administrative Billing Fee; Utility - Electric Service; Utility - Gas; Utility - Water/Sewer Service", L("parc"))
assert "Pet Fees: (one-time non-refundable): $350 per pet" in pz

# ---------------------------------------------------------------- 5. ratings
rat = []
HDR_R = ["addr_key", "building_name", "rating_source", "rating_value", "rating_scale", "review_count", "as_of_date", "reviews_read", "reviews_last_6_months", "negative_last_6_months", "negative_older", "serious_issue_tags_last_6_months", "source_url"]
CUT6 = datetime.date(2026, 5, 15)
def R(k, src, val, cnt, asof, read, last6, neg6, negold, tags, url): rat.append([K[k], name(k), src, val, 5, cnt, asof, read, last6, neg6, negold, tags, url])
BIRD = {"highlands": "https://reviews.birdeye.com/the-highlands-at-morris-plains-apartments-156720906550002", "woodmont": BW, "parksq": "https://reviews.birdeye.com/park-square-156778471297509",
        "park": "https://reviews.birdeye.com/the-park-156778018221722", "parc": BP, "morgans": "https://reviews.birdeye.com/morgans-bluff-156778729020725",
        "alister": "https://reviews.birdeye.com/alister-morristown-156705756272075", "avalon": BA, "gardens": "https://reviews.birdeye.com/the-gardens-at-raritan-156779020235266",
        "brunswick": "https://birdeye.com/the-brunswick-169689000297323"}
# reviews read on Birdeye pages (Birdeye-native texts only; negative_older counted by hand from the page text)
BIRD_READ = {"woodmont": (2, 2), "parc": (4, 2), "avalon": (1, 1)}
done = set()
for k in K:
    key = K[k]
    z = ZUM.get(key) or {}
    g = ((z.get("reviews") or {}).get("sources") or {}).get("google")
    if g:
        rs = g["reviews"]; d6 = [r for r in rs if datetime.date.fromtimestamp(r["date"]) >= CUT6]
        neg_old = sum(1 for r in rs if (r.get("rating") or 5) <= 2)
        R(k, "Google rating shown on Zumper (Zumper shows only 8 reviews, all 5-star, so negatives are not visible)", g["aggregateRating"], g["reviewCount"],
          datetime.date.fromtimestamp(g["lastPulled"]).isoformat(), len(rs), len(d6), 0, neg_old, "", z["url"]); done.add(k)
    a = (ALR.get(key) or {}).get("agg")
    if a:
        rs = ALR[key]["reviews"]
        R(k, "Apartment List", a["ratingValue"], a["reviewCount"], ALR[key]["at"][:10], len(rs), sum(1 for r in rs if r["submitDate"][:10] >= CUT6.isoformat()), 0,
          sum(1 for r in rs if (r.get("overallScore") or 5) <= 2), "", ALR[key]["url"]); done.add(k)
    if k in BIRD:
        t = page(BIRD[k]); m = re.search(r"(\d\.\d) (\d+) reviews", t); assert m, k
        read, negold = BIRD_READ.get(k, (0, 0))
        R(k, "Birdeye profile (aggregate across sources, mostly Google; review texts mostly not shown)", m.group(1), m.group(2), at(BIRD[k])[:10], read, 0, 0, negold, "", BIRD[k]); done.add(k)
NONE = {
 "edge": ("Looked at: Apartment List page (no rating), Zumper building page (no review data), Renter's Voice (0 reviews), own site reviews page (testimonials, no score). A Birdeye search did not find a page.", "https://www.rentersvoice.com/reviews/nj/new-brunswick/the-edge-at-raritan-heights"),
 "premiere": ("Looked at: Apartment List page (no rating), Zumper address page (no review data), Pennrose page. Own site HTTP 403. A Birdeye search did not find a page.", L("premiere")),
 "cosmo": ("Looked at: Trulia building page (no rating), Zumper address page (no review data). A Birdeye search did not find a page.", L("cosmo")),
 "urby": ("Looked at: Trulia building page (no rating); Zumper has no page at this address. A Birdeye search did not find a page.", L("urby")),
 "symphony": ("Looked at: Trulia building page (no rating); Zumper has no page at this address. New building.", L("symphony")),
 "noble": ("Looked at: Trulia building page, Zumper building page (no review data), own site. New building, opened October 2026.", L("noble")),
 "molly": ("Looked at: Apartment List page (no rating), own site; Zumper has no page at this address. A Birdeye search did not find a page. Bozzuto's site is closed to us.", L("molly")),
 "halstead": ("Looked at: Apartment List page (no rating), Zumper building page (no review data), Renter's Voice (0 reviews). A Birdeye search did not find a page. Bozzuto's site is closed to us.", L("halstead")),
 "district": ("Looked at: Apartment List page (no rating), own site; Zumper has no page at this address. A Birdeye search did not find a page.", L("district")),
 "villas": ("Looked at: Apartment List page (no rating), Zumper address page (no review data), own site home page. A Birdeye search did not find a page.", L("villas")),
 "centurion": ("Looked at: Apartment List page (no rating), Zumper building page (no review data), Trulia building page, own site. Opened 2026.", L("centurion")),
 "riverdale": ("Looked at: Apartment List page (no rating), Zumper building page (no review data). Own site and BBB profile HTTP 403. The Birdeye search hit was a different property in Georgia.", L("riverdale")),
}
for k in K:
    if k not in done:
        w, u = NONE[k]; rat.append([K[k], name(k), "none_found", "", "", "", at(u)[:10] if u in idx else "", 0, 0, 0, 0, w, u])
order = list(K.values()); rat.sort(key=lambda r: order.index(r[0]))

# ---------------------------------------------------------------- write
def W(fn, hdr, data):
    with open(f"data/evidence/{fn}_batch_9.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(data)
    print(fn, len(data))
live.sort(key=lambda r: order.index(r[0]))
W("live_check", ["addr_key", "listing_url", "unit", "status", "price_now", "available_now_text", "matches_stored", "building_site_url", "checked_at", "notes"], live)
W("confirm", ["addr_key", "fact", "value", "quote", "source_url", "status"], conf)
W("items", ["addr_key", "building_name", "category", "item_date", "excerpt", "source_site", "source_url", "about", "retrieved_at"], items)
W("facts", ["addr_key", "fact", "value", "quote", "source_url"], facts)
W("ratings", HDR_R, rat)
from collections import Counter
print("live", Counter(r[3] for r in live)); print("confirm", Counter(r[5] for r in conf)); print("items", Counter(r[2] for r in items))
print("ratings", Counter("none_found" if r[2] == "none_found" else "rated" for r in rat), "buildings with a rating:", len({r[0] for r in rat if r[2] != "none_found"}))
