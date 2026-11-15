"""Evidence batch 6: write the four output CSVs from the cached, parsed pages (no network). Idempotent: rewrites the files.

Inputs: raw/evidence_b6/ (fetch log copy _fetch_log.jsonl, _igloo_reviewed.json). Every value below was read from the page
named in its source_url; nothing is taken from search snippets.
"""
import csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
E = ROOT / "raw/evidence_b6"
OUT = ROOT / "data/evidence"
OUT.mkdir(parents=True, exist_ok=True)

ts = {}
for line in (E / "_fetch_log.jsonl").read_text().splitlines():
    u, st, n, path, t = json.loads(line)
    ts[u] = t
igloo = json.loads((E / "_igloo_reviewed.json").read_text())

T = "https://www.trulia.com/home/"
K = {  # short name -> (addr_key, building_name, listing url)
 "junction": ("33-25 junction blvd|11372", "Lumina (name from listing)", T + "33-25-junction-blvd-2d-jackson-heights-ny-11372-466321150"),
 "northern": ("103-14 northern blvd|11368", "", T + "103-14-northern-blvd-6f-corona-ny-11368-350209733"),
 "30rd": ("1105 30th rd|11102", "", T + "1105-30th-rd-2f-astoria-ny-11102-2101445300"),
 "winslow": ("26-25 4th st|11102", "The Winslow (name from listing)", T + "26-25-4th-st-1020-astoria-ny-11102-463846279"),
 "view": ("26-02 4th st|11102", "View Astoria (name from listing)", T + "26-02-4th-st-5e-astoria-ny-11102-2068488375"),
 "astor": ("2-24 26th ave|11102", "Astor 2 on Third (name from listing)", T + "2-24-26th-ave-311-astoria-ny-11102-347393740"),
 "pelham": ("1890 pelham pkwy s 4g 1890 pelham pkwy s bronx ny 10461 us|10461", "", "https://www.zumper.com/listings/29834478p/studio-pelham-bay-new-york-ny"),
 "parluxe": ("71-82 parsons blvd|11365", "Parluxe (name from listing)", T + "71-82-parsons-blvd-615-fresh-meadows-ny-11365-457456755"),
 "lefferts": ("375 lefferts ave|11225", "", T + "375-lefferts-ave-7e-brooklyn-ny-11225-453282973"),
 "clarkson": ("61 clarkson ave|11226", "", T + "61-clarkson-ave-2b-brooklyn-ny-11226-339926856"),
 "eny": ("824 e new york ave|11203", "Ensemble (name from listing)", T + "824-e-new-york-ave-403-brooklyn-ny-11203-466610780"),
 "saunders": ("63-45 saunders st|11374", "", T + "63-45-saunders-st-3a-rego-park-ny-11374-72650072"),
 "netherland": ("3215 netherland ave 3a bronx ny 10463 usa|10463", "", "https://www.zumper.com/listings/30111551p/1-bedroom-riverdale-new-york-ny"),
 "e12": ("2750 e 12th st|11235", "", T + "2750-e-12th-st-3i-brooklyn-ny-11235-2104601160"),
 "51st": ("3925 51st st 3e woodside ny 11377 usa|11377", "Sunny Hill Gardens (name from listing)", "https://www.zumper.com/listings/30083572p/studio-woodside-new-york-ny"),
 "46th": ("4545 46th st|11377", "", T + "4545-46th-st-5f-woodside-ny-11377-2093254023"),
 "urby": ("7 navy pier ct staten island ny 10304 usa|10304", "Staten Island Urby", "https://www.zumper.com/apartment-buildings/p221698/staten-island-urby-stapleton-staten-island-ny"),
 "e61": ("255 e 61st st|10065", "", T + "255-e-61st-st-2a-new-york-ny-10065-2111411099"),
 "w72": ("53 w 72nd st 4c new york ny 10023 usa|10023", "", "https://www.zumper.com/listings/2562116p/studio-upper-west-side-new-york-ny"),
 "w181": ("720 w 181st st|10033", "720 West 181st Street", "https://www.apartmentlist.com/ny/new-york/720-west-181st-street--1"),
 "w163": ("630 w 163rd st|10032", "630 West 163rd Street", "https://www.apartmentlist.com/ny/new-york/630-west-163rd-street"),
 "altos": ("27 barker ave|10601", "The Altos", "https://www.apartmentlist.com/ny/white-plains/the-altos"),
 "lex": ("25 n lexington ave|10601", "25 North Lex", "https://www.apartmentlist.com/ny/white-plains/25-north-lex"),
 "c55": ("55 bank st|10606", "Continuum 55", "https://www.greystar.com/continuum-55-white-plains-ny/p_22789"),
 "c57": ("57 bank st|10606", "Continuum 57", "https://www.greystar.com/continuum-57-white-plains-ny/p_22790"),
 "cal": ("55-57 bank st|10606", "Continuum", "https://www.apartmentlist.com/ny/white-plains/continuum--1"),
 "51s": ("51 s broadway|10601", "51 South", "https://www.apartmentlist.com/ny/white-plains/51-south"),
 "alex": ("57 alexander st|10701", "Alexander Crossing", "https://www.apartmentlist.com/ny/yonkers/alexander-crossing"),
 "av3326": ("80 alexander st 3326|10701", "Avalon Yonkers", "https://www.avaloncommunities.com/new-york/yonkers-apartments/avalon-yonkers/apartment/NY047-NY047-003-3326"),
 "aval": ("79 alexander st|10701", "Avalon Yonkers", "https://www.apartmentlist.com/ny/yonkers/avalon-yonkers"),
 "av2336": ("137 alexander st 2336|10701", "Avalon Yonkers", "https://www.avaloncommunities.com/new-york/yonkers-apartments/avalon-yonkers/apartment/NY047-NY047-002-2336"),
 "apex": ("20 water grant st yonkers ny 10701 usa|10701", "Apex Hudson Riverfront", "https://www.zumper.com/apartment-buildings/p288235/modera-hudson-riverfront-downtown-yonkers-yonkers-ny"),
 "av1555": ("79 alexander st 1555|10701", "Avalon Yonkers", "https://www.avaloncommunities.com/new-york/yonkers-apartments/avalon-yonkers/apartment/NY047-NY047-001-1555"),
}
AVALON = ["av3326", "aval", "av2336", "av1555"]
CONT = ["c55", "c57", "cal"]
AV_COMM = "https://www.avaloncommunities.com/new-york/yonkers-apartments/avalon-yonkers"
ALTOS_SITE = "https://thealtoswhiteplains.com/"
TB = "https://www.trulia.com/building/"
TRB = {"alex": TB + "alexander-crossing-57-alexander-st-yonkers-ny-10701-2750788390",
       "apex": TB + "apex-hudson-riverfront-20-water-grant-st-yonkers-ny-10701-2740011249",
       "avalon": TB + "avalon-yonkers-79-alexander-st-yonkers-ny-10701-2754252176",
       "urby": TB + "staten-island-urby-7-navy-pier-ct-staten-island-ny-10304-2750948746",
       "cont": TB + "continuum-55-bank-st-white-plains-ny-10606-2734175071",
       "lex": TB + "25-north-lex-25-n-lexington-ave-white-plains-ny-10601-2750927039",
       "altos": TB + "the-altos-27-barker-ave-white-plains-ny-10601-1002080890",
       "51s": TB + "51-south-51-s-broadway-white-plains-ny-10601-2757739754"}
LEX_G = "https://www.greystar.com/25-north-lex-white-plains-ny/p_21088"
AV_Z = "https://www.zumper.com/apartment-buildings/p366939/avalon-yonkers-downtown-yonkers-yonkers-ny"

# ------------------------------------------------------------------ live check
live = []
def L(k, unit, status, price, avail, match, site, notes, url=None):
    a, _, u = K[k]
    u = url or u
    live.append([a, u, unit, status, price, avail, match, site, ts.get(u, ""), notes])

L("junction", "2D", "live", 2350, "Nov 16th", "yes", "", "Trulia: For Rent, listed 2026-10-29, broker Nest Seekers International. Own leasing site not found.")
L("northern", "6F", "live", 2575, "now", "yes", "", "Trulia: For Rent, listed 2026-11-01, broker Highline Residential. Own leasing site not found.")
L("30rd", "2F", "live", 2595, "now", "yes", "", "Trulia: For Rent, listed 2026-11-13, broker TriBro NYC LLC. A second listing at this address on Zumper (listings/23677324p) shows a studio at $2,650 with no unit number.")
L("winslow", "1020", "live", 2800, "now", "yes", "", "Trulia: For Rent, listed 2026-11-13, broker Nooklyn NYC LLC. Own leasing site not found.")
L("view", "5E", "live", 2600, "now", "yes", "", "Trulia: For Rent, listed 2026-11-12, broker Visual Arts Realty. Listing says 'photos are similar model unit' and 'Email inquiries only'. Says RENT STABILIZED.")
L("astor", "311", "live", 2400, "now", "yes", "", "Trulia: For Rent, listed 2026-10-30, broker Nooklyn NYC LLC. Own leasing site not found.")
L("pelham", "3G (page title) / 4G (address line)", "live", 2795, "2026/10/13 (page data; already past = now)", "yes", "",
  "Zumper: active, broker New & Modern, listed 2026-10-14, 'Updated 5+ Days Ago'. Page title says #3G but the address line says #4G: unit is ambiguous. Text: 'No Broker Fee & Half Month Free!'.")
L("parluxe", "615", "live", 2800, "Dec 15th", "yes", "", "Trulia: For Rent, listed 2026-11-09, broker A&R Properties Group LLC. Available date is the last day of the window (2026-12-15). Same unit on Zumper (listings/29679977p): $2,800, 2026/12/15.")
L("lefferts", "7E", "live", 2500, "now", "yes", "", "Trulia: For Rent, listed 2026-11-04, broker Nooklyn NYC LLC.")
L("clarkson", "2B", "live", 2800, "Nov 18th", "yes", "", "Trulia: For Rent, listed 2026-11-13, broker Real Street Inc. 'Select photos are virtually staged.'")
L("eny", "403", "live", 2750, "now", "yes", "", "Trulia: For Rent, listed 2026-11-13, broker Nooklyn NYC LLC.")
L("saunders", "3A", "live", 2350, "now", "yes", "", "Trulia: For Rent, listed 2026-11-10, broker Compass. 'Open Houses by Appointment Only'.")
L("netherland", "3A", "live", 1180, "2026/11/24 (page data)", "yes", "",
  "Zumper: active, listed 2026-11-14 via feed 'avail', contact phone area code 570 (not a NYC code). Zumper says the price is '57% below the median price for 1 bedroom apartments in Riverdale' (898 sq ft 1BR at $1,180; deposit $1,180). Price far below market: treat as unverified until someone sees the unit.")
L("e12", "3I", "live", 1900, "now", "yes", "", "Trulia: For Rent, listed 2026-11-02, broker RMR Apartments LLC. Page: 'Decreased by $100 (5%) on Nov 12, 2026.'")
L("51st", "3E", "live", 1699, "2026/11/21 (page data)", "yes", "",
  "Zumper: active, listed 2026-11-12 via feed 'avaasa_listings', contact FBPH Rentals, phone area code 239 (not a NYC code). Zumper says '26% below the median price for studio apartments in Woodside'. Openigloo shows this tax lot as a co-op corporation building (see items).")
L("46th", "5F", "live", 2650, "now", "yes", "", "Trulia: For Rent, listed 2026-09-27 (seven weeks on the market), broker Voro New York.")
L("urby", "floor plan M1 (studio, 538 sq ft); unit number not shown", "live", 2182, "2026/11/13 (page data; already past = now)", "yes", "https://www.urby.com/location/staten-island",
  "Zumper building page: M1 studio $2,182-$2,605, '3 units available'. Lowest price matches stored. Unit numbers are not shown. Urby's own site pages fetched (home, amenities, apartment features) show no prices in plain HTML.")
L("e61", "2A", "live", 2800, "now", "yes", "", "Trulia: For Rent, listed 2026-11-03, broker City Wide Apartments. '*Photos are of a similar unit in building.'")
L("w72", "4C", "live", 2750, "2026/11/14 (page data; already past = now)", "yes", "",
  "Zumper: active, 'Listed 13 Hours Ago' via TurboTenant feed, contact phone area code 612 (not a NYC code). A second active listing at this address shows $2,800 (feed 'reallyo'). Zumper: '29% below the median price for studio apartments in Upper West Side'. Listing text: 'syndicated listings may remain online briefly after a unit is rented'.")
L("w181", "21", "live", 2499, "2026-11-11 (already past = now)", "yes", "", "Apartment List: active, source feed 'reallyo', availability last checked 2026-11-15. No building site or manager named.")
L("w163", "10", "live", 2305, "2026-11-11 (already past = now)", "yes", "", "Apartment List: active, source feed 'reallyo', availability last checked 2026-11-15. No building site or manager named.")
L("altos", "410", "changed", 2733, "2026-10-16 (already past = now)", "no", ALTOS_SITE, "Stored $2,726, now $2,733 (floor plan The Acadia, 753 sq ft). Apartment List feed yardi_rentcafe, last checked 2026-11-14. Own site found; its floor-plan prices were not fetched.")
L("lex", "610", "live", 2557, "2026-12-08", "yes", "https://25northlex.com/", "Same price and date on the Greystar property page (unit 610, floor 6).")
L("lex", "312", "live", 2806, "2026-11-15 (Apartment List); 2026-10-19 (Greystar page)", "yes", "https://25northlex.com/", "Same price on the Greystar property page (unit 312, floor 3); both dates mean available now.")
L("c55", "N0311", "live", 2294, "2026-12-11", "yes", "https://continuumwhiteplains.com/", "Greystar page unit table: floor 3, 557 sq ft.")
L("c55", "N0419", "live", 2335, "2026-11-17", "yes", "https://continuumwhiteplains.com/", "Greystar page unit table: floor 4, 528 sq ft.")
L("c57", "S0904", "live", 2600, "2026-11-24", "yes", "https://continuumwhiteplains.com/", "Greystar page unit table: floor 9, 632 sq ft.")
L("c57", "S0515", "live", 2222, "2026-12-02", "yes", "https://continuumwhiteplains.com/", "Greystar page unit table: floor 5, 424 sq ft.")
L("cal", "S0904", "live", 2600, "2026-11-24", "yes", "https://continuumwhiteplains.com/", "Same unit as the Continuum 57 row; Apartment List agrees with Greystar.")
L("cal", "N1119", "live", 2455, "2026-11-06 (already past = now)", "yes", "https://continuumwhiteplains.com/", "Greystar page (Continuum 55) shows the same: $2,455, floor 11.")
L("51s", "311", "live", 2808, "2026-07-28 (already past = now)", "yes", "https://www.51southwhiteplains.com/", "Apartment List feed yardi_rentcafe, last checked 2026-11-15. Own site returned HTTP 403 (bot wall): not read.")
L("51s", "710", "live", 2808, "2026-12-04", "yes", "https://www.51southwhiteplains.com/", "As above.")
L("alex", "0405", "live", 2517, "2026-11-12 (already past = now)", "yes", "https://www.rentalexandercrossing.com/", "Apartment List feed spherexx, last checked 2026-11-15. Own site has no prices in plain HTML.")
L("alex", "0243", "live", 2598, "2026-11-10 (already past = now)", "yes", "https://www.rentalexandercrossing.com/", "As above.")
L("av3326", "3326", "live", 2675, "move-in from 12/1/2026", "yes", AV_COMM,
  "AvalonBay unit page: $2,675 is the 14- or 15-month price; 12-month price $2,975; 13-month $2,680. Page 'totalPrice' with required monthly fees: $2,857 (14/15 mo). Floor 3. Page banner: 'AVAILABLE FURNISHED' option.")
L("aval", "003-3326", "live", 2675, "2026-12-01", "yes", AV_COMM, "Same unit as the 80 Alexander St #3326 row.")
L("aval", "002-2130", "live", 2430, "2026-11-16", "yes", AV_COMM, "AvalonBay community page: unit 2130, 15-month price $2,430, total with required fees $2,612, floorNumber 1 (ground floor: fails the no-ground-floor gate).")
L("av2336", "2336", "live", 2440, "move-in from 12/1/2026", "yes", AV_COMM, "AvalonBay unit page: $2,440 is the 15-month price; 12-month price $2,485. 'totalPrice' with required monthly fees: $2,622 (15 mo). Floor 3.")
L("apex", "floor plan Newton (1BR, 718 sq ft); unit number not shown", "live", 2669, "2026/11/14 (page data; already past = now)", "yes", "https://www.apexhudsonriverfront.com/",
  "Zumper building page: Newton 1BR $2,669-$3,172, '7 units available'; Zumper labels this 'Total Monthly Price' (base rent plus known required monthly fees). All studio plans are 'Coming soon / waitlist'. Own site robots.txt returned HTTP 403: not read.")
L("av1555", "1555", "live", 2475, "move-in from 12/9/2026", "yes", AV_COMM, "AvalonBay unit page: $2,475 is the 15-month price; 12-month price $2,520. 'totalPrice' with required monthly fees: $2,657 (15 mo). Page shows 'Floor 5'.")

# ------------------------------------------------------------------ confirm
conf = []
def C(k, fact, value, quote, src, status):
    conf.append([K[k][0], fact, value, quote, src, status])

SMALL = "Cats, small dogs allowed"
def trulia_std(k, unit_floor, floor_quote=None, floor_status="unconfirmed", elev=True, elev_quote="Elevator", elev_value="yes", elev_status="confirmed"):
    u = K[k][2]
    C(k, "elevator", elev_value, elev_quote, u, elev_status)
    C(k, "floor", unit_floor, floor_quote or "inferred from the unit number only; the page does not state the floor", u, floor_status)
    C(k, "dogs_allowed", "yes", SMALL, u, "confirmed")
    C(k, "dog_weight_limit", "not stated in pounds; listing says small dogs only", "Dogs: Allowed; Size allowed: Small", u, "unconfirmed")

trulia_std("junction", "2")
trulia_std("northern", "6", "Enjoy modern living in this stylish studio apartment on the 6th floor of a newly built full-service building.", "confirmed", elev_quote="-Elevator & live-in super")
trulia_std("30rd", "2")
C("30rd", "elevator", "yes; 8 floors", "Built in 2014, this building has 81 units and 8 floors.", igloo["1105 30th rd|11102"]["url"], "confirmed")
trulia_std("winslow", "10", elev_quote="AMENITIES ... Elevator")
trulia_std("view", "5", elev_quote="This pet friendly building offers tenants an amenity package that includes washer/dryer in units, garage parking, elevator, bike room, package room and live-in super.")
C("view", "elevator", "7 floors", "7 floors", igloo["26-02 4th st|11102"]["url"], "confirmed")
trulia_std("astor", "3")
trulia_std("parluxe", "6", elev_quote="This 8-Story Building offers 94 Luxurious Rental Units ranging from Studios, 1 & 2 Bedroom Homes. (page attribute: Elevator)")
C("parluxe", "dogs_allowed", "no (Zumper copy of the same unit)", "Pets | Dog | Policy | Not allowed | Cat | Policy | Not allowed | No pets allowed.", "https://www.zumper.com/listings/29679977p/studio-pomonok-new-york-ny", "contradicts")
trulia_std("lefferts", "7")
trulia_std("clarkson", "2", elev_quote="This elevator building offers laundry on-site and a shared roof deck, with Prospect Park nearby.")
trulia_std("eny", "4", elev_quote="Amenities include: Virtual Doorman / Elevator service")
C("eny", "elevator", "7 floors", "7 floors", igloo["824 e new york ave|11203"]["url"], "confirmed")
trulia_std("saunders", "3", elev_value="unknown", elev_quote="the page lists no elevator attribute and the description does not mention one", elev_status="unconfirmed")
trulia_std("e12", "3", elev_value="unknown", elev_quote="the page lists no elevator attribute and the description does not mention one", elev_status="unconfirmed")
C("e12", "dogs_allowed", "yes", "Dog Run / Pet Friendly Building", K["e12"][2], "confirmed")
# 4545 46th: weight limit stated
u = K["46th"][2]
C("46th", "elevator", "yes; 6 floors", "Elevator (Trulia attribute)", u, "confirmed")
C("46th", "elevator", "yes; 6 floors", "elevator pretty reliable and 2 washers + 2 dryers working 99.9% of the time (tenant review, 2022-11-14); 6 floors", igloo["4545 46th st|11377"]["url"], "confirmed")
C("46th", "floor", "5", "inferred from the unit number only; the page does not state the floor", u, "unconfirmed")
C("46th", "dogs_allowed", "yes", "Cats and small dogs (25lbs max) are welcomed", u, "confirmed")
C("46th", "dog_weight_limit", "25", "Cats and small dogs (25lbs max) are welcomed", u, "confirmed")
# 255 E 61st
u = K["e61"][2]
C("e61", "elevator", "unknown; four-story building, no elevator mentioned", "Beautiful and sunny studio apartment on the 2nd floor of a well-maintained four story building in Lenox Hill.", u, "unconfirmed")
C("e61", "floor", "2", "Beautiful and sunny studio apartment on the 2nd floor of a well-maintained four story building in Lenox Hill.", u, "confirmed")
C("e61", "dogs_allowed", "yes", SMALL, u, "confirmed")
C("e61", "dog_weight_limit", "not stated in pounds; listing says small dogs only", "Dogs: Allowed; Size allowed: Small", u, "unconfirmed")

def zumper_std(k, floor, elev_quote, floor_note="inferred from the unit number only; the page does not state the floor"):
    u = K[k][2]
    C(k, "elevator", "yes", elev_quote, u, "confirmed")
    C(k, "floor", floor, floor_note, u, "unconfirmed")
    C(k, "dogs_allowed", "yes", "Pets | Dog | Policy | Allowed", u, "confirmed")
    C(k, "dog_weight_limit", "not stated", "Contact for more information on pet policy.", u, "unconfirmed")
zumper_std("pelham", "3 or 4", "Building Features: Gym / Elevator / Laundry / Roof Deck / Lounge Area", "page title says #3G, address line says #4G; floor inferred from the unit number only")
zumper_std("netherland", "3", "The building offers convenient amenities, including elevator access, on-site laundry facilities, and a live-in superintendent.")
zumper_std("51st", "3", "Residents enjoy elevator access, on-site laundry, a fitness room, parking options, and a live-in superintendent.")
C("51st", "elevator", "6 floors (Openigloo page for the same tax lot, listed as 39-30 52 Street)", "Built in 1951, this building has 40 units and 6 floors.", igloo["3925 51st st 3e woodside ny 11377 usa|11377"]["url"], "confirmed")
zumper_std("w72", "4", "The building offers elevator access and a full-time superintendent.")
C("w72", "elevator", "7 floors", "Built in 1889, this 7-floor building at 53 West 72 Street in the Upper West Side, Manhattan has 57 units", igloo["53 w 72nd st 4c new york ny 10023 usa|10023"]["url"], "confirmed")
# Urby
u = K["urby"][2]
C("urby", "elevator", "yes", "Building: ... Dogs OK / Elevator / EV Charging", u, "confirmed")
C("urby", "elevator", "5 floors", "Built in 2016, this 5-floor building at 7 Navy Pier Court in Stapleton, Staten Island has 467 units and is managed by Homeport 1 LLC.", igloo["7 navy pier ct staten island ny 10304 usa|10304"]["url"], "confirmed")
C("urby", "floor", "unknown", "the Zumper building page shows floor plans (M1: 3 units available) without unit numbers", u, "unconfirmed")
C("urby", "dogs_allowed", "yes", "2 dogs max. Dogs and cats allowed, 1 pet per unit (2 on approval), none of the following aggressive breeds are permitted: Rottweiler, American Pit bull, Pit bull Terrier, Pit bull, German Shepherd, and Doberman Pinscher variety", u, "confirmed")
C("urby", "dog_weight_limit", "no weight limit stated (breed list only)", "Dogs: Allowed; Number allowed: 2; Size allowed: Small, large", TRB["urby"], "unconfirmed")
# Washington Heights
for k, n in (("w181", "21"), ("w163", "10")):
    u = K[k][2]
    C(k, "floor", "unknown", f"unit is listed as '{n}' (an apartment number); the page gives no floor", u, "unconfirmed")
    C(k, "dogs_allowed", "yes", "Cats allowed, Dogs allowed, Pet friendly", u, "confirmed")
    C(k, "dog_weight_limit", "not stated", "no weight or size text on the page", u, "unconfirmed")
C("w181", "elevator", "unknown; 6 floors", "the Apartment List page lists no amenities; Openigloo: 52 units, 6 floors, built in 1910", igloo["720 w 181st st|10033"]["url"], "unconfirmed")
C("w163", "elevator", "yes (tenant reviews); 6 floors", "It took management over a week to fix the out-of-order elevator. (tenant review, 2024-05-16)", igloo["630 w 163rd st|10032"]["url"], "confirmed")
# Altos
C("altos", "elevator", "yes", "Elevators", "https://thealtoswhiteplains.com/amenities/", "confirmed")
C("altos", "floor", "4", "inferred from the unit number 410 only", K["altos"][2], "unconfirmed")
C("altos", "dogs_allowed", "yes", "Pet Policy Type: Cat, Dog, Fish", ALTOS_SITE, "confirmed")
C("altos", "dog_weight_limit", "40", "Pet Weight Limit: 40 lbs.", ALTOS_SITE, "confirmed")
# 25 North Lex
C("lex", "elevator", "yes", "High speed elevators", "https://25northlex.com/amenities/", "confirmed")
C("lex", "floor", "unit 610: floor 6; unit 312: floor 3", "Greystar unit table: 610 floorShortLabel 6; 312 floorShortLabel 3", LEX_G, "confirmed")
C("lex", "dogs_allowed", "yes", "Dog run & pet spa / A Pet-Friendly Community", "https://25northlex.com/amenities/", "confirmed")
C("lex", "dog_weight_limit", "not stated in pounds; Trulia building page says small and large dogs", "Dogs: Allowed; Number allowed: 2; Size allowed: Small, large; Monthly dog rent: $60/mo; 'Dogs: Based on NAA pet rider'", TRB["lex"], "unconfirmed")
# Continuum
for k, fl in (("c55", "N0311: floor 3; N0419: floor 4"), ("c57", "S0904: floor 9; S0515: floor 5"), ("cal", "S0904: floor 9; N1119: floor 11")):
    g = K["c57"][2] if k == "c57" else K["c55"][2]
    C(k, "elevator", "not stated explicitly; high-rise", "Greystar page data: buildingType 'High-Rise'; available units on floors 2 to 16", g, "unconfirmed")
    C(k, "floor", fl, "Greystar unit table (floorShortLabel)" + ("; S0904 from the Continuum 57 page, N1119 from the Continuum 55 page" if k == "cal" else ""), g, "confirmed")
    C(k, "dogs_allowed", "yes", "Yes, Continuum 55 & 57 is a pet-friendly community with a pet park and dog wash on-site.", "https://continuumwhiteplains.com/faqs/", "confirmed")
    C(k, "dog_weight_limit", "a limit exists but the number is not published; Trulia building page says small and large dogs", "Breed restrictions, weight limits, and pet fees apply. Please refer to our community fee guide for complete details.", "https://continuumwhiteplains.com/faqs/", "unconfirmed")
# 51 South
u = K["51s"][2]
C("51s", "elevator", "yes; 8 stories", "Set at the gateway to downtown White Plains, this eight-story residence ... (amenity list: Elevator)", u, "confirmed")
C("51s", "floor", "unit 311: 3; unit 710: 7", "inferred from the unit numbers only", u, "unconfirmed")
C("51s", "dogs_allowed", "yes", "Dogs allowed, Pet friendly, Cats allowed, Dog grooming area", u, "confirmed")
C("51s", "dog_weight_limit", "not stated in pounds; Trulia building page says small and large dogs", "Dogs: Allowed; Size allowed: Small, large", TRB["51s"], "unconfirmed")
# Alexander Crossing
u = K["alex"][2]
C("alex", "elevator", "yes", "amenity list: Doorman, Elevator, Parking, Pool, Garage, 24hr concierge", u, "confirmed")
C("alex", "floor", "unit 0405: 4; unit 0243: 2", "inferred from the unit numbers only", u, "unconfirmed")
C("alex", "dogs_allowed", "yes", "We welcome all your furry friends at Alexander Crossing.", "https://www.rentalexandercrossing.com/", "confirmed")
C("alex", "dog_weight_limit", "not stated in pounds; Trulia building page says small and large dogs", "Dogs: Allowed; Size allowed: Small, large; Monthly dog rent: $50/mo", TRB["alex"], "unconfirmed")
# Avalon Yonkers
for k, fl, q in (("av3326", "3", "community page unit data: unit 3326 floorNumber 3"), ("av2336", "3", "community page unit data: unit 2336 floorNumber 3"),
                 ("av1555", "5", "Floor 5"), ("aval", "003-3326: floor 3; 002-2130: floor 1 (ground floor)", "community page unit data: unit 3326 floorNumber 3; unit 2130 floorNumber 1")):
    C(k, "elevator", "yes (aggregator amenity list); buildings have floors 1 to 5", "Apartment List amenity list: Pool, Elevator, 24hr concierge", K["aval"][2], "confirmed")
    C(k, "floor", fl, q, K[k][2] if k == "av1555" else AV_COMM, "contradicts" if k == "aval" else "confirmed")
    C(k, "dogs_allowed", "yes", "Cats and dogs are welcome. Please check the dog breed and pet restrictions.", AV_COMM, "confirmed")
    C(k, "dog_weight_limit", "no weight limit stated (page data maximumPetWeight = 0; breed list only; max 2 pets)", "Cats and dogs are welcome. Please check the dog breed and pet restrictions below.", AV_COMM, "confirmed")
# Apex
u = K["apex"][2]
C("apex", "elevator", "yes", "Building: ... Cats OK / Dogs OK / Elevator / Fitness Center", u, "confirmed")
C("apex", "floor", "unknown", "the Zumper building page shows floor plans (Newton: 7 units available) without unit numbers", u, "unconfirmed")
C("apex", "dogs_allowed", "yes", "We love furry companions and welcome up to two pets per apartment home.", u, "confirmed")
C("apex", "dog_weight_limit", "75", "Maximum Number of Pets: 2 ; Max Weight of Pets: 75 lbs.", u, "confirmed")

# ------------------------------------------------------------------ items
items = []
def I(k, cat, date, excerpt, site, url, about, when):
    items.append([K[k][0], K[k][1], cat, date, excerpt, site, url, about, when])

def R(k, date, cat, start, end, about="building", note=""):
    """Openigloo review excerpt: verbatim slice of the review body from `start` through `end`."""
    o = igloo[K[k][0]]
    body = next(r["body"] for r in o["reviews"] if r["date"].startswith(date))
    i = body.index(start); j = body.index(end, i) + len(end)
    ex = " ".join(body[i:j].split())
    I(k, cat, date[:10], ex, "Openigloo" + (f" ({note})" if note else ""), o["url"], about, o["retrieved_at"])

R("30rd", "2024-06-21", "management", "Management not always responsive", "regular basis.", "management_company")
R("30rd", "2024-06-21", "positive", "Doormen staff are awesome", "laundry in building.")
R("30rd", "2024-03-15", "other", "Flooded multiple floors previously", "Leaks are common")
R("30rd", "2022-07-29", "noise", "The park across the street gets VERY loud", "in the summer.", "street")
R("30rd", "2021-12-21", "management", "Cold air comes through", "does nothing to help.", "management_company")
R("30rd", "2021-12-06", "management", "Management company is awful and lie.", "Two major floods in two years.", "management_company")

R("view", "2025-08-17", "management", "Management is impossible to reach", "decide to respond.", "management_company")
R("view", "2025-08-17", "management", "No community room, gym", "over 4 years.", "management_company")
R("view", "2025-08-17", "noise", "If you rent here, you'll get paper thin walls", "weed smoke.")
R("view", "2025-08-17", "other", "Leaks from rainwater are a massive problem here", "energy efficiency.")
R("view", "2025-01-28", "management", "No amenities or anything", "supposed to be built", "management_company")
R("view", "2024-01-16", "positive", "Never had any issues with running out of hot water.", "deliveries and visitors.")
R("view", "2023-11-15", "safety_incident", "Pretty much anybody can walk in at any time.", "stolen every single day.")
R("view", "2023-11-15", "other", "Construction workers leave the garage door open all the time.", "open all the time.", "garage_or_lot")
R("view", "2023-11-15", "management", "Management is slow to respond to issues within the apartment.", "responsive every time.", "management_company")
R("view", "2023-09-29", "management", "There is no response", "needs fixing.", "management_company")
R("view", "2023-09-29", "noise", "The noise between floors is very loud.", "neighbors walking.")

R("clarkson", "2025-10-06", "management", "Cheaply made/things break.", "difficult to deal with.", "management_company")
R("clarkson", "2025-10-06", "noise", "Lots of noise from the street", "cigarettes indoors.")

R("eny", "2025-07-18", "positive", "Management was responsive when roof began leaking.", "No real issues", "management_company")
R("eny", "2025-07-18", "other", "Trash would pile up on weekends", "(thankfully)")
R("eny", "2024-09-07", "management", "I had literal mold and roaches", "once I involved 311.", "management_company")
R("eny", "2024-09-07", "other", "Rent is too damn high, and the garage rate is insane.", "is insane.", "garage_or_lot")
R("eny", "2021-11-16T16", "other", "People who don't live in the building can walk in and out", "not so safe area")

R("51st", "2021-11-16", "elevator", "Elevator issues, recoccuring bedbugs", "last few years.", note="page is for 39-30 52 Street, same tax lot 4001280007 as 39-25 51st St")

R("46th", "2025-12-28", "safety_incident", "When I had a series of packages stolen", "internal or external.")
R("46th", "2025-12-28", "management", "The laundry downstairs does not work", "frequently dirty.")
R("46th", "2025-12-28", "positive", "Super is on-site", "exterminator visit")
R("46th", "2022-11-14", "positive", "elevator pretty reliable", "99.9% of the time")
R("46th", "2022-11-14", "management", "building rated as an F", "pests are persistent")

R("urby", "2026-10-07", "positive", "Management here is really nice", "things like that.", "management_company")
R("urby", "2026-10-07", "noise", "Courtyard can be loud", "regarding pets here.")
R("urby", "2025-08-06", "management", "Maintenance is not good at their job.", "painted over it.", "management_company")
R("urby", "2025-02-05", "management", "The heat is none existent", "high electric bill.")
R("urby", "2024-10-30", "other", "Wish the surrounding neighborhood was less rough", "less rough", "street")

R("e61", "2022-01-15", "management", "Building management is evil.", "security deposit back.", "management_company", note="page is for 257 East 61 Street, same tax lot 1014160021")
R("e61", "2022-01-15", "positive", "Really nice super", "help you with things.")

R("w72", "2024-10-09", "positive", "I had no interactions with the landlord", "without any problems.", "management_company")
R("w72", "2024-07-26", "management", "Absolutely awful management", "no sense of urgency", "management_company")
R("w72", "2023-07-02", "management", "Small apartments and slower maintenance", "slower maintenance")
R("w72", "2022-06-04", "management", "The management company was always difficult to get a hold of.", "get a hold of.", "management_company")
R("w72", "2021-11-16", "management", "Building management takes days, even weeks to respond.", "to respond.", "management_company")

R("w181", "2025-07-28", "management", "Freezing in the winter", "really cold.")
R("w181", "2025-07-28", "safety_incident", "Mice, roaches. Constant package theft.", "package theft.")
R("w181", "2025-04-24", "management", "THERE IS NO GAS.", "without gas.", "management_company")
R("w181", "2025-04-24", "management", "Owner is shady", "without permits.", "management_company")
R("w181", "2021-11-16", "management", "We haven’t had working gas for over a year", "impossible to contact", "management_company")

R("w163", "2024-05-16", "elevator", "It took management over a week", "out-of-order elevator.", note="page is for 90 Fort Washington Ave, same tax lot 1021370091")
R("w163", "2024-05-16", "management", "The super is a ghost", "heat or a leak.", "management_company", note="page is for 90 Fort Washington Ave, same tax lot 1021370091")
R("w163", "2023-11-04", "elevator", "Elevator is slow and noisy.", "inside my unit.", note="page is for 90 Fort Washington Ave, same tax lot 1021370091")
R("w163", "2023-10-12", "elevator", "Elevator (that is out of service lots of the time though)", "though)", note="page is for 90 Fort Washington Ave, same tax lot 1021370091")
R("w163", "2023-10-12", "management", "Leaky/raining ceilings", "as a result.", "management_company", note="page is for 90 Fort Washington Ave, same tax lot 1021370091")
R("w163", "2022-10-10T14", "management", "Terrible unresponsive management!", "unresponsive management!", "management_company", note="page is for 90 Fort Washington Ave, same tax lot 1021370091")
R("w163", "2022-10-10T12", "management", "The building manager barely exists.", "barely exists.", "management_company", note="page is for 90 Fort Washington Ave, same tax lot 1021370091")

ZT = ts[K["urby"][2]]
I("urby", "positive", "2024-11-03", "I've been here for about a month now and I absolutely love it. The apartment is perfect for me (and my cat and dog) and I have a wonderful view!",
  "Zumper building page (Google review shown by Zumper; Zumper shows eight reviews, all 5-star, pulled 2024-12-07)", K["urby"][2], "building", ZT)
AZT = ts[AV_Z]
news_t = json.loads((E / "_news_times.json").read_text())
for k in AVALON:
    I(k, "car_crime", "2023-03-01", "On Wednesday, March 1, 2023, shortly after 6AM, members of the Yonkers Police Department responded to the parking garage in the rear of 80 Alexander Street on a report of an occupied suspicious vehicle. [...] An inventory search of the BMW yielded 17 cut catalytic converters in the trunk, presumed stolen.",
      "Yonkers Times (article dated 2023-03-05; two sentences from the same article, joined at [...])", "https://yonkerstimes.com/suspicious-vehicle-call-to-yonkers-police-results-in-three-arrests/", "garage_or_lot", news_t["yonkerstimes"])
    I(k, "car_crime", "2023-03-01", "On March 1, shortly after 6 a.m., police responded to a parking garage at 80 Alexander St. for a report of an occupied suspicious vehicle.",
      "News 12 Westchester (article dated 2023-03-05; same incident as the Yonkers Times item)", "https://westchester.news12.com/2023/03/05/yonkers-pd-3-men-arrested-on-suspicion-of-catalytic-converter-thefts/6r2ktYkTNo3KkWtFsWC1l1", "garage_or_lot", news_t["news12_cat"])
    I(k, "positive", "2024-02-13", "Full amenities - I see security in the hallways- never an issue with parking.",
      "Zumper building page (Google review shown by Zumper; Zumper shows eight reviews, all 5-star, pulled 2024-12-07)", AV_Z, "building", AZT)
    I(k, "noise", "2024-06-28", "It's a great place to live, but I def recommend not facing a courtyard if you value peace and quiet.",
      "Zumper building page (Google review shown by Zumper; Zumper shows eight reviews, all 5-star, pulled 2024-12-07)", AV_Z, "building", AZT)
    I(k, "positive", "2024-08-15", "Since I moved in, everything that was mentioned from the service and accommodations have been fantastic.",
      "Apartment List (review snippet on the building page; 2 ratings, overall 3 of 5)", K["aval"][2], "building", ts[K["aval"][2]])
I("apex", "other", "2024-02-13", "Down the block, Apex was a disaster.",
  "Zumper page for Avalon Yonkers (Google review of Avalon Yonkers by a former Apex resident, shown by Zumper; no specifics given)", AV_Z, "building", AZT)
I("altos", "management", "2023-08-16", "Residents who live at the Avalon in downtown White Plains are sounding the alarm after they say the fire alarm in their building goes off for no reason several times a night, every week.",
  "News 12 Westchester (building named as 'the Avalon in downtown White Plains'; The Altos' own site says 'Formerly Avalon White Plains'; the article gives no street address)",
  "https://westchester.news12.com/white-plains-residents-raise-safety-concerns-after-months-of-false-fire", "building", news_t["news12_alarm"])
I("altos", "noise", "2023-08-16", "\"Anywhere from three to five, sometimes more times a week we have fire alarms going off predominantly between midnight and 3 a.m.,\" said three-year resident Paul Corrente.",
  "News 12 Westchester (same article; resident named in the article is quoted as published)", "https://westchester.news12.com/white-plains-residents-raise-safety-concerns-after-months-of-false-fire", "building", news_t["news12_alarm"])

NOW = news_t["none_found_at"]
def NF(k, where, url):
    I(k, "none_found", "", where, "search log", url, "building", NOW)
OI = "https://www.openigloo.com/sitemap.xml"
NF("junction", "Openigloo: building page exists by BBL with 0 reviews; not in the reviewed-buildings sitemaps. No reviews on the Trulia listing page. No news search run for this address.", "https://www.openigloo.com/building/nyc/4017100065-4017100065/queens-north-corona-33-25-junction-boulevard-11372")
NF("northern", "Openigloo: building page exists by BBL (as 103-12 Northern Boulevard) with 0 reviews. No reviews on the Trulia listing page. No news search run for this address.", "https://www.openigloo.com/building/nyc/4017180005-4017180005/queens-corona-103-12-northern-boulevard-11368")
NF("winslow", "Openigloo: building page exists by BBL with 0 reviews. Web search for the building's own site returned only listing sites. No reviews on the Trulia listing page.", "https://www.openigloo.com/building/nyc/4009090009-4009090009/queens-astoria-26-25-4-street-11102")
NF("astor", "Openigloo: building page exists by BBL (as 2-06 26 Avenue) with 0 reviews. Web search for a pet policy or own site found nothing for this building.", "https://www.openigloo.com/building/nyc/4009140022-4009140022/queens-astoria-2-06-26-avenue-11102")
NF("pelham", "Openigloo: building page has 0 reviews. Web search for news on '1890 Pelham Parkway South' found only listing pages and stories about other addresses. Zumper listing page has no reviews.", igloo[K["pelham"][0]]["url"])
NF("parluxe", "Openigloo: reviewed-sitemap page for 71-82 Parsons Boulevard shows 'No reviews yet'. Web search found only listing pages. No reviews on the Trulia or Zumper listing pages.", igloo[K["parluxe"][0]]["url"])
NF("lefferts", "Openigloo: building page exists by BBL with 0 reviews. Web search for news on '375 Lefferts Avenue' found only other addresses (415 and 501 Lefferts Ave).", "https://www.openigloo.com/building/nyc/3013210050-3013210050/brooklyn-prospect-lefferts-gardens-375-lefferts-avenue-11225")
NF("saunders", "Openigloo: no page for BBL 4030800043 in the reviewed-buildings sitemaps (the BBL-keyed URL returns 404). No reviews on the Trulia listing page. No news search run for this address.", OI)
NF("netherland", "Openigloo: no page for BBL 2057880119 in the reviewed-buildings sitemaps (the BBL-keyed URL returns 404). Zumper listing page has no reviews. No news search run for this address.", OI)
NF("e12", "Openigloo: no page for BBL 3087630013 in the reviewed-buildings sitemaps (the BBL-keyed URL returns 404). Web search for '2750 East 12th Street' found nothing about this building.", OI)
NF("lex", "Web search for news on '25 North Lex' found only construction and leasing coverage (opened 2024). Apartment List and Trulia building pages show no resident reviews.", K["lex"][2])
for k in CONT:
    NF(k, "Web search for tenant complaints, garage, break-in, elevator or lawsuit at Continuum (55/57 Bank St) found nothing about this building; hits were for other White Plains buildings (86 DeKalb Ave, 15 Bank St). Apartment List, Trulia and Greystar pages show no resident reviews.", K["cal"][2])
NF("51s", "Apartment List and Trulia building pages show no resident reviews. Own site blocked (HTTP 403). One combined web search (with 25 North Lex and The Altos) returned nothing on 51 South Broadway.", K["51s"][2])
NF("alex", "Web search for car break-ins, theft, shooting, elevator or tenant issues at Alexander Crossing found nothing about this building. Apartment List and Trulia building pages show no resident reviews.", K["alex"][2])
NF("apex", "News: web search found only 2018-era opening coverage and listing pages. A local blog post (news.hamlethub.com, 'Yonkers Waterfront Woes') appeared in search results but its text could not be read from the page (JavaScript only), so nothing from it is recorded. Zumper page shows no resident reviews.", K["apex"][2])
NF("urby", "News: web search for car break-ins, garage or police incidents at 7 Navy Pier Court found nothing. A 2018 fair-housing lawsuit against Urby appeared in search results (amNY, Legal Services NYC); amNY's robots.txt disallows us and the text was not read, so it is not recorded as an item.", K["urby"][2])

# ------------------------------------------------------------------ facts
facts = []
def F(k, fact, value, quote, src):
    facts.append([K[k][0], fact, value, quote, src])

F("junction", "building_size", "24 units, new construction", "Welcome to Lumina, a new 24-unit boutique building in the heart of Jackson Heights", K["junction"][2])
F("junction", "parking", "optional private parking; fee not stated", "Optional private parking", K["junction"][2])
F("junction", "doorman", "virtual doorman", "ButterflyMX virtual doorman with smartphone entry", K["junction"][2])
F("northern", "parking", "available at extra cost; fee not stated", "-Parking available (extra)", K["northern"][2])
F("northern", "doorman", "live-in super; no doorman stated", "-Elevator & live-in super", K["northern"][2])
o = igloo["1105 30th rd|11102"]["url"]
F("30rd", "year_built", "2014", "Built in 2014, this building has 81 units and 8 floors.", o)
F("30rd", "management_company", "30 Vernon LLC (owner entity named by Openigloo)", "Built in 2014, this 8-floor building at 11-05 30 Road in Astoria, Queens has 81 units and is managed by 30 Vernon LLC.", o)
F("30rd", "doorman", "yes (per tenant reviews)", "Doormen staff are awesome, view is great, apartments are good size, laundry in building.", o)
F("30rd", "openigloo_summary", "3.5/5 across 6 reviews; 7 open violations, 5 evictions, 1 litigation case (Openigloo count)", "Tenants rate it 3.5/5 across 6 reviews, with 50% recommending it and 34% approving of the owner. It records 5 evictions, 7 open violations, and 1 litigation case. Data last updated November 10, 2026.", o)
F("winslow", "parking", "private parking; fee not stated", "Private parking", K["winslow"][2])
o = igloo["26-02 4th st|11102"]["url"]
F("view", "year_built", "2017 (Openigloo); listing calls it newly constructed, 46 units", "Built in 2017", o)
F("view", "parking", "garage parking, assigned, paid; fee not stated", "There's also a (paid) parking garage.", o)
F("view", "rent_stabilized", "yes (listing)", "RENT STABILIZED + BALCONY!", K["view"][2])
F("view", "openigloo_summary", "3.4/5 across 8 reviews; 71 open violations, 0 evictions, 1 litigation case (Openigloo count)", "Tenants rate it 3.4/5 across 8 reviews, with 13% recommending it and 13% approving of the owner. It records 0 evictions, 71 open violations, and 1 litigation case. Data last updated November 8, 2026.", o)
F("astor", "amenities", "fitness center, rooftop, lounge, pet spa, laundry facility", "an array of favorable building amenities including a fitness center, rooftop, lounge, work space, pet spa, theater, laundry facility", K["astor"][2])
F("pelham", "concession", "no broker fee and half a month free", "No Broker Fee & Half Month Free!", K["pelham"][2])
F("pelham", "application_fee", "$20 per applicant", "Applicants will pay a $20 application / credit check fee per applicant.", K["pelham"][2])
F("parluxe", "year_built", "2023", "Built in 2023", igloo[K["parluxe"][0]]["url"])
F("parluxe", "management_company", "A&R Properties Group", "this building is managed by A&R Properties Group", igloo[K["parluxe"][0]]["url"])
F("parluxe", "parking", "garage in building; fee not stated", "In Building Garage", K["parluxe"][2])
F("parluxe", "doorman", "virtual doorman", "Virtual Doorman", K["parluxe"][2])
F("lefferts", "parking", "parking garage, assigned; fee not stated", "Amenities include a fitness center, parking garage, laundry facility, bicycle storage, finished rooftop with skyline views of Manhattan.", K["lefferts"][2])
o = igloo["61 clarkson ave|11226"]["url"]
F("clarkson", "management_company", "Clarkson Parnasa LLC (owner entity named by Openigloo)", "this building at 61 Clarkson Avenue in Prospect Lefferts Gardens, Brooklyn, is managed by Clarkson Parnasa LLC.", o)
o = igloo["824 e new york ave|11203"]["url"]
F("eny", "year_built", "2018", "Built in 2018", o)
F("eny", "parking", "on-site parking garage; fee not stated (a 2024 tenant review calls the rate 'insane')", "On Site parking garage", K["eny"][2])
F("eny", "doorman", "virtual doorman", "Virtual Doorman", K["eny"][2])
F("eny", "openigloo_summary", "3.8/5 across 4 reviews; 8 open violations, 4 evictions, 0 litigation cases (Openigloo count)", "Tenants rate it 3.8/5 across 4 reviews, with 75% recommending it and 75% approving of the owner. It records 4 evictions, 8 open violations, and 0 litigation cases. Data last updated November 14, 2026.", o)
F("netherland", "parking", "assigned parking; fee not stated", "Parking Policy: Assigned Parking", K["netherland"][2])
F("netherland", "security_deposit", "$1,180", "Security Deposit ... $1,180", K["netherland"][2])
F("e12", "parking", "on-site parking; fee not stated", "On-Site Parking", K["e12"][2])
F("e12", "price_change", "reduced by $100 on 2026-11-12", "Decreased by $100 (5%) on Nov 12, 2026.", K["e12"][2])
F("e12", "amenities", "live-in super, gym, dog run, two laundry rooms", "Live-In Super / On-Site Parking / Resident Lounge with Wi-Fi / Complimentary Gym / Sun Deck / Dog Run / Two Laundry facilities / Pet Friendly Building", K["e12"][2])
o = igloo["3925 51st st 3e woodside ny 11377 usa|11377"]["url"]
F("51st", "year_built", "1951", "Built in 1951, this building has 40 units and 6 floors.", o)
F("51st", "management_company", "Metro Management Development Inc (named in a 2021 tenant review; not confirmed elsewhere)", "When you look up 51sr/52nd St Tenants Corp you will see it's really METRO MANAGEMENT DEVELOPMENT INC.", o)
F("51st", "parking", "garage parking; fee not stated", "Garage Parking", K["51st"][2])
o = igloo["4545 46th st|11377"]["url"]
F("46th", "year_built", "1927", "Built in 1927", o)
F("46th", "utilities_included", "heat and hot water", "Heat and hot water included in rent", K["46th"][2])
F("46th", "openigloo_summary", "3.1/5 across 3 reviews; 4 open violations, 0 evictions, 1 litigation case (Openigloo count)", "Tenants rate it 3.1/5 across 3 reviews, with 100% recommending it and 100% approving of the owner. It records 0 evictions, 4 open violations, and 1 litigation case. Data last updated November 12, 2026.", o)
o = igloo["7 navy pier ct staten island ny 10304 usa|10304"]["url"]
F("urby", "year_built", "2016", "Year built 2016", K["urby"][2])
F("urby", "management_company", "URBY (leasing); owner entity Homeport 1 LLC per Openigloo", "Managed by ... URBY", K["urby"][2])
F("urby", "pool", "outdoor heated saltwater pool", "Heated Saltwater Pool", "https://www.urby.com/location/staten-island/amenities")
F("urby", "parking", "underground garage with EV charging; fee not stated", "Underground Parking Garage with EV Charging Stations", "https://www.urby.com/location/staten-island/amenities")
F("urby", "doorman", "24/7 welcome desk", "24/7 Welcome Desk", "https://www.urby.com/location/staten-island/amenities")
F("urby", "fees", "application $20 per applicant; holding deposit $250 (non-refundable)", "Non-refundable Application Fee ... $20 / Holding Deposit ... $250", K["urby"][2])
F("urby", "openigloo_summary", "3.9/5 across 9 reviews; 7 open violations, 51 evictions, 2 litigation cases (Openigloo count, 467 units)", "Tenants rate it 3.9/5 across 9 reviews, with 78% recommending it and 78% approving of the owner. It records 51 evictions, 7 open violations, and 2 litigation cases. Data last updated November 12, 2026.", o)
o = igloo["255 e 61st st|10065"]["url"]
F("e61", "year_built", "1900; 23 units, 4 floors", "Built in 1900, this building has 23 units and 4 floors.", o)
F("e61", "application_fee", "$20 per applicant", "Rental Requirements: A $20 application fee applies to all applicants and personal guarantors.", K["e61"][2])
o = igloo["53 w 72nd st 4c new york ny 10023 usa|10023"]["url"]
F("w72", "year_built", "1889; 57 units, 7 floors", "Built in 1889, this 7-floor building at 53 West 72 Street in the Upper West Side, Manhattan has 57 units and is managed by Bldg Management Co., INC.", o)
F("w72", "management_company", "Bldg Management Co., Inc. (Openigloo)", "managed by Bldg Management Co., INC.", o)
F("w72", "laundry", "none in building per listing text (pickup service nearby), although the amenity list says Onsite Laundry", "Laundry service is conveniently available nearby, with pickup and drop-off.", K["w72"][2])
F("w72", "kitchen", "kitchenette only", "a kitchenette with a cooktop and compact refrigerator", K["w72"][2])
o = igloo["720 w 181st st|10033"]["url"]
F("w181", "year_built", "1910; 52 units, 6 floors", "Built in 1910", o)
F("w181", "management_company", "Bcc Pm LLC (Openigloo)", "Built in 1910 and managed by Bcc Pm LLC", o)
F("w181", "openigloo_summary", "2.5/5 across 3 reviews; 36 open violations, 6 evictions, 5 litigation cases (Openigloo count)", "Tenants rate it 2.5/5 across 3 reviews, with 0% recommending it and 0% approving of the owner. It records 6 evictions, 36 open violations, and 5 litigation cases. Data last updated November 13, 2026.", o)
o = igloo["630 w 163rd st|10032"]["url"]
F("w163", "year_built", "1930; 65 units, 6 floors (Openigloo page for the same tax lot, 90 Fort Washington Ave)", "Built in 1930", o)
F("w163", "openigloo_summary", "2.2/5 across 8 reviews; 11 open violations, 1 eviction, 14 litigation cases (Openigloo count)", "Tenants rate it 2.2/5 across 8 reviews, with 0% recommending it and 0% approving of the owner. It records 1 eviction, 11 open violations, and 14 litigation cases. Data last updated November 9, 2026.", o)
F("altos", "pet_fees", "pet rent $60/month; one-time pet fee $500; max 2 pets", "One-time Pet Fee: $500 / Non-Refundable, Pet Rent: $60 monthly / Max Number of Pets: 2", ALTOS_SITE)
F("altos", "parking", "garage; off-street parking $114.53/month (Apartment List)", "Off-street parking: $114.53/month", K["altos"][2])
F("altos", "pool", "yes; indoor or outdoor not stated", "Resort-Style Pool", "https://thealtoswhiteplains.com/amenities/")
F("altos", "doorman", "concierge", "Concierge", "https://thealtoswhiteplains.com/amenities/")
F("altos", "year_built", "2008; 407 units (Apartment List)", "year_built 2008; total_units_count 407 (page data)", K["altos"][2])
F("altos", "management_company", "site says 'Formerly Avalon White Plains'; Apartment List still names AvalonBay; current manager and takeover date not found", "The Altos | Apartments in White Plains, NY | Formerly Avalon White Plains", ALTOS_SITE)
F("lex", "required_monthly_fees", "$101.06: community amenity fee $75, trash $20, utility billing admin fee $6.06; plus usage-based electric, gas, water/sewer and renters liability insurance", "Greystar fee table: Community Amenity Fee 75 (required); Trash Services - Hauling 20 (required); Utility - Billing Administrative Fee 6.06 (required)", LEX_G)
F("lex", "pet_rent", "$60/month", "Pet Rent 60 (monthly, optional add-on)", LEX_G)
F("lex", "parking", "garage, $235/month", "Parking 235 (monthly, optional add-on); 'Monthly resident garage parking'", LEX_G)
F("lex", "internet", "$65/month, optional", "Internet Services 65 (monthly, not required)", LEX_G)
F("lex", "pool", "outdoor infinity-edge pool", "Expansive infinity-edge pool with wet bar", "https://25northlex.com/amenities/")
F("lex", "doorman", "24/7 concierge", "24/7 Concierge", "https://25northlex.com/amenities/")
F("lex", "year_built", "2024; 500 units; manager Greystar", "year_built 2024; total_units_count 500 (page data)", K["lex"][2])
for k in CONT:
    g = K["c57"][2] if k == "c57" else K["c55"][2]
    F(k, "required_monthly_fees", "$126: community amenity fee $50, internet $60, trash $10, utility billing admin fee $6; plus electric (metered), gas and water/sewer (allocated) and renters liability insurance", "Greystar fee table: Community Amenity Fee 50 (required); Internet Services 60 (required); Trash Services - Hauling 10 (required); Utility - Billing Administrative Fee 6 (required)", g)
    F(k, "pet_rent", "$40-$60/month by pet type (dog $60, cat $40 per Trulia building page)", "Pet Rent: 40-60 monthly, 'Price varies based on pet type.'", g)
    F(k, "parking", "on-site garage run by a third party; price not published", "Yes, Continuum 55 & 57 offers on-site garage parking including spaces with EV charging, via a third party management company. Please visit the garage or contact the leasing office for current parking availability and pricing.", "https://continuumwhiteplains.com/faqs/")
    F(k, "pool", "outdoor pool", "Outdoor Pool & Grilling Stations", "https://continuumwhiteplains.com/amenities/")
    F(k, "doorman", "24-hour concierge", "24-hour concierge", "https://continuumwhiteplains.com/faqs/")
    F(k, "management_company", "Greystar (listing site and fair-housing notice); Apartment List names LCOR; takeover date not found", "greystar-new-york-reasonable-accomodation.pdf linked from the building site; Apartment List pmc_display_name LCOR", "https://continuumwhiteplains.com/")
F("cal", "year_built", "2017; 599 units across both towers (Apartment List)", "year_built 2017; total_units_count 599 (page data)", K["cal"][2])
F("51s", "building_size", "eight stories, 134 units", "this eight-story residence; total_units_count 134 (page data)", K["51s"][2])
F("51s", "pool", "yes; indoor or outdoor not stated", "amenity list: Elevator, Parking, Pool", K["51s"][2])
F("51s", "parking", "off-street parking; fee not stated", "Off Street Parking", TRB["51s"])
F("alex", "pet_fees", "pet rent $50/month; one-time fee $500", "pet policy data: rent 50; fee 500; deposit 0", K["alex"][2])
F("alex", "pool", "outdoor heated pool", "Outdoor Heated Swimming Pool", "https://www.rentalexandercrossing.com/amenities/")
F("alex", "parking", "on-site garage; fee not stated", "On-Site Garage Parking", "https://www.rentalexandercrossing.com/amenities/")
F("alex", "doorman", "concierge services", "Concierge Services", "https://www.rentalexandercrossing.com/amenities/")
for k in AVALON:
    u = K[k][2] if k != "aval" else K["av3326"][2]
    F(k, "required_monthly_fees", "$182: Common Area/Amenities $90 + Technology Connect $92", "Required Monthly: Base Rent / Common Area/Amenities $90 / mo. / Technology Connect $92 / mo.", u)
    F(k, "pet_rent", "dog $60/month; no one-time pet charge", "Dog $60 / mo. ... Dog $0 (one-time charge)", u)
    F(k, "parking", "assigned garage parking, $116-$188/month", "Parking $116-$188 / mo.; Monthly, assigned parking is available in our controlled-access, seven level garage for an additional monthly fee.", u)
    F(k, "utilities", "resident pays electric, gas, trash, water, sewer", "Utility Responsibility: Electric Resident / Gas Resident / Trash Resident / Water Resident / Sewer Resident", u)
    F(k, "deposit", "$2,000 refundable; promotion: $99 deposit on approved credit if applying by 2026-11-30", "$99 security deposit (on approved credit) on select homes when you apply by 11-30-2026.", u)
    F(k, "pool", "yes; indoor or outdoor not stated", "Pool", AV_COMM)
    F(k, "doorman", "concierge", "Concierge", AV_COMM)
    F(k, "management_company", "AvalonBay Communities; year built 2021, 590 units (Apartment List)", "pmc_display_name AvalonBay; year_built 2021; total_units_count 590 (page data)", K["aval"][2])
u = K["apex"][2]
F("apex", "required_monthly_fees", "$56: pest control $15 + trash $41 (Zumper says its price already includes known required fees)", "Utilities: Monthly ... Pest Control. $15 / Monthly ... Trash. $41", u)
F("apex", "pet_fees", "pet rent $75/month per pet; one-time $500 for one pet, $1,000 for two", "There is a one-time $500 non-refundable pet charge for one pet and $1000 for two. In addition, there is a $75 pet rent per pet each month.", u)
F("apex", "deposit", "$1,700", "Security Deposit ... $1,700", u)
F("apex", "pool", "yes ('resort style'); indoor or outdoor not stated", "Resort Style Pool", u)
F("apex", "doorman", "full-service concierge", "Full Service Concierge", u)
F("apex", "parking", "garage, valet parking; fee not stated", "Special Features: ... Significant Garage Renovations, Sundeck, Tile Backsplashes, Valet Parking", TRB["apex"])
F("apex", "year_built", "2018; 323 units; manager Two Coast Living", "Year built 2018 / Units 323 / Managed by Two Coast Living", u)

def w(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f); cw.writerow(header); cw.writerows(rows)
    print(name, len(rows))
w("live_check_batch_6.csv", "addr_key,listing_url,unit,status,price_now,available_now_text,matches_stored,building_site_url,checked_at,notes".split(","), live)
w("confirm_batch_6.csv", "addr_key,fact,value,quote,source_url,status".split(","), conf)
w("items_batch_6.csv", "addr_key,building_name,category,item_date,excerpt,source_site,source_url,about,retrieved_at".split(","), items)
w("facts_batch_6.csv", "addr_key,fact,value,quote,source_url".split(","), facts)
