"""Evidence batch 12: build the five output CSVs from cached pages and the scratch parse files. No network.
Inputs: scratch b12/trulia_parsed.json (refetched Trulia pages), trulia_cached6.json (Trulia pages captured by the
harvest earlier the same day, used where the refetch got 403), al_parsed.json, raw/evidence_b12/zumper_bld.json,
raw/evidence_b12/august_units.json, raw/evidence_b12/scribe_sightmap.json. If the scratch folder is gone, rerun
ev12_fetch.py, ev12_trulia_parse.py, ev12_trulia_cached.py and ev12_al_parse.py first."""
import csv, json, datetime
S = '/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b12/'
TP = json.load(open(S + 'trulia_parsed.json')); TC = json.load(open(S + 'trulia_cached6.json')); AL = json.load(open(S + 'al_parsed.json'))
ZB = json.load(open('raw/evidence_b12/zumper_bld.json')); AUG = json.load(open('raw/evidence_b12/august_units.json'))
SCR = json.load(open('raw/evidence_b12/scribe_sightmap.json'))
B = {r['addr_key']: r for r in csv.DictReader(open('data/reference/evidence_batches/batch_12.csv'))}
NOW = '2026-11-15T23:05:00+00:00'
T = 'https://www.trulia.com/building/'
URL = {k: r['building_url'] for k, r in B.items()}
def tfind(d, frag):
    for u, r in d.items():
        if frag in u: return u, r
    raise KeyError(frag)
def tunit(rec, unit):
    for x in rec['units']:
        un = x.get('unit')
        if isinstance(un, dict) and un['name'] == 'Unit ' + unit:
            return dict(price=un['priceRange'].get('min'), avail=un.get('availabilityText'), date=(un.get('availabilityDate') or '')[:10])
        if un == 'Unit ' + unit:
            return dict(price=int(x['price'].replace('$', '').replace(',', '')), avail=x.get('avail'), date=x.get('date'))
    return None
def alunit(u, unit):
    for fp in AL[u]['L'].get('available_units') or []:
        for un in fp.get('units') or []:
            if un.get('name') == unit: return dict(un, plan=fp['name'])
    return None
live, conf, items, facts, ratings = [], [], [], [], []
def L(k, url, unit, status, price, avail, match, site, at, notes): live.append([k, url, unit, status, price, avail, match, site, at, notes])
def C(k, fact, value, quote, url, status): conf.append([k, fact, value, quote, url, status])
def I(k, cat, date, excerpt, site, url, about, at=NOW): items.append([k, B[k]['building_name'], cat, date, excerpt, site, url, about, at])
def F(k, fact, value, quote, url): facts.append([k, fact, value, quote, url])
def R(k, src, val, scale, n, asof, read, last6, neg6, negold, tags, url): ratings.append([k, B[k]['building_name'], src, val, scale, n, asof, read, last6, neg6, negold, tags, url])
def none_item(k, where): I(k, 'none_found', '', 'Nothing about this building found. Looked at: ' + where, 'search', '', 'building')
def none_rating(k, where): R(k, 'none_found', '', '', '', '2026-11-15', 0, '', '', '', '', where)
NEWS = 'one web search for news, tenant complaints and incidents (no article about this building came back)'
def zstat(k):
    z = ZB.get(k) or {}
    if z.get('status') != 200: return 'Zumper: no building page at the address URL (%s)' % z.get('status')
    return 'Zumper page %s: review block empty' % z['url']
BLOCK = 'Trulia returned HTTP 403 to this refetch (bot wall after 17 requests; one retry 4 minutes later also 403; not retried again). '

# ---------- helpers for Trulia-backed buildings ----------
def trulia_live(k, frag, units, site=''):
    u, rec = tfind(TP, frag)
    for unit, stored in units:
        x = tunit(rec, unit)
        if not x: L(k, u, unit, 'gone', '', '', 'no', site, rec['ts'], 'Unit not on the page any more. Page last modified %s.' % rec['modified'][:10]); continue
        yield_note = 'Page last modified %s.' % rec['modified'][:10]
        L(k, u, unit, 'live' if x['price'] == stored else 'changed', x['price'], x['avail'] + (' (date on page %s)' % x['date'] if x['date'] else ''), 'yes' if x['price'] == stored else 'no', site, rec['ts'], yield_note + NOTE.get((k, unit), '') + NOTE.get(k, ''))
    return u, rec
def cached_live(k, frag, units, extra=''):
    u, rec = tfind(TC, frag)
    for unit, stored in units:
        x = tunit(rec, unit)
        L(k, u, unit, 'blocked', '', '', '', '', '2026-11-15T22:48:40+00:00', BLOCK + 'Last good capture by the harvest at %s: Unit %s %s, %s%s; page last modified %s. Not re-verified in this pass.' % (rec['ts'], unit, ('$%s' % format(x['price'], ',')) if x else 'not listed', x['avail'] if x else '', (' (date %s)' % x['date']) if x and x['date'] else '', rec['modified'][:10]) + extra)
    return u, rec
def offer(k, rec, url, basis='The page does not say whether the listed price is gross or net-effective.'):
    for o in rec.get('offers') or []:
        d, sub = (o.get('description'), o.get('subText')) if isinstance(o, dict) else o
        F(k, 'special_offer', (d or '') + (' [' + sub + ']' if sub else ''), basis, url)
NOTE = {}
NOTE[('7 station rd|06804', '6108')] = ' Unit number 6108 may be a ground-floor unit (building 6, floor 1?): confirm.'
NOTE['2405 whitney ave|06518'] = ''
NOTE[('2405 whitney ave|06518', '306')] = ' Available Dec 15 is the last day of the window.'
NOTE[('121 w main st|06460', '121-2T')] = ' Available Dec 15 is the last day of the window. Listing tagged NEW - 1 DAY AGO.'
NOTE['5545 park ave|06825'] = ' Listing record is old (last modified April 2026) although the unit shows an availability date of 2026-11-04.'
NOTE['1 new haven ave|06460'] = ' Listing last modified in August 2026: confirm by phone.'
NOTE['135 broad st|06460'] = ' Listing last modified in August 2026: confirm by phone.'

def std_trulia(k, frag, units, small=False, weight=None, elev_quote='Elevator (listed under Levels, Entrance & Accessibility)', floors=None, site=''):
    u, rec = trulia_live(k, frag, units, site)
    C(k, 'elevator', 'yes', elev_quote, u, 'confirmed')
    C(k, 'dogs_allowed', 'yes', rec['pet']['formattedPetsAllowed'], u, 'confirmed')
    return u, rec
def floor_guess(k, unit, reading, why, url, status='unconfirmed'):
    C(k, 'floor', 'unconfirmed (unit %s): reading %s' % (unit, reading), why, url, status)
def dog_small(k, quote, url): C(k, 'dog_weight_limit', 'small dogs only; no pound figure given', quote, url, 'confirmed')
def dog_none(k, quote, url, extra=''): C(k, 'dog_weight_limit', 'unconfirmed: no weight limit stated' + extra, quote, url, 'unconfirmed')

# 1 Ansonia On Main
k = '36 main st|06401'; u = URL[k]; a = alunit(u, '66C'); at = AL[u]['ts']
L(k, u, '66C', 'live', a['price'], 'available now (available_on %s)' % a['available_on'], 'yes', 'https://bluebrookprop.appfolio.com/listings', at,
  "ADDRESS PROBLEM: the manager's own listing page (Blue Brook Properties, AppFolio) shows this $1,500 unit as '66 Main St - Apt C, Ansonia', not 36 Main Street. '66C' is street number 66, apartment C; it is not a sixth-floor unit. Apartment List unit record updated 2026-11-14.")
C(k, 'elevator', 'unconfirmed: no page lists an elevator; the earlier height inference came from reading unit 66C as floor 6, which is wrong', "66 Main St - Apt C, Ansonia, CT 06401 ... Amenities: On-site Laundry", 'https://bluebrookprop.appfolio.com/listings', 'unconfirmed')
floor_guess(k, '66C', 'unknown', "Manager's listing: '66 Main St - Apt C'. The letter is an apartment label; no floor is stated anywhere.", 'https://bluebrookprop.appfolio.com/listings')
C(k, 'dogs_allowed', 'yes', 'Pet Policy: Cats allowed, Dogs allowed', 'https://bluebrookprop.appfolio.com/listings', 'confirmed')
dog_none(k, 'Pet Policy: Cats allowed, Dogs allowed (Apartment List: pet limit 1)', 'https://bluebrookprop.appfolio.com/listings')
F(k, 'management_company', 'Blue Brook Properties, LLC', 'pm: Blue Brook Properties, LLC (Zumper); apply link bluebrookprop.appfolio.com', ZB[k]['url'])
F(k, 'listing_address_mismatch', 'unit is at 66 Main Street, Apt C', '**Location:** 66 Main Street, Ansonia, CT 06401', 'https://bluebrookprop.appfolio.com/listings')
F(k, 'utilities_included', 'cold water, sewer, trash', 'Utilities Included: Cold Water, Sewer Use, Trash Collection', 'https://bluebrookprop.appfolio.com/listings')
F(k, 'security_deposit', '$1,500', 'deposit_fee_text: 1500.00', u)
none_item(k, NEWS.replace('one web search', 'no dedicated news search (address in doubt)') + '; Apartment List page (no reviews); ' + zstat(k))
none_rating(k, 'Apartment List %s: no rating; %s; Trulia not reachable' % (u, zstat(k)))

# 2 Beacon Mill Village
k = '2 n main st|06403'
u, rec = std_trulia(k, 'beacon-mill-village', [('PA-405', 1805), ('PA-202', 1805)], site='https://www.beaconmillvillage.com/')
floor_guess(k, 'PA-405', '4', "Unit number only ('PA' looks like a building code, then 405). The complex is several converted mill buildings; no page states the floor.", u)
floor_guess(k, 'PA-202', '2', "Unit number only ('PA' building code, then 202). No page states the floor.", u)
dog_none(k, 'Dogs: Allowed; Number allowed 1; Size allowed: Small, large', u, ' (large dogs are allowed, one pet)')
offer(k, rec, u, 'Discount is on move-in costs, not rent; the page does not say whether rent is gross or net-effective.')
F(k, 'parking', 'rear lot free; front lot $50 per vehicle per month', 'free parking in rear lot front lot: $50 per vehicle', u)
F(k, 'required_monthly_fees', 'trash $10/mo', 'Trash $10/mo; electric, hot water and internet paid by resident.', u)
F(k, 'pool', 'outdoor', 'outdoor pool with sundeck', u)
F(k, 'building_size', '187 units, 8 listed available', 'totalUnitsInBuilding 187; availableRentalUnits 8 (page data)', u)
F(k, 'own_site', 'https://www.beaconmillvillage.com/ (availability table is script-rendered; lists Dog Park, Sparkling Pool, Property Manager On-Site)', 'Dog Park', 'https://www.beaconmillvillage.com/')
none_item(k, NEWS + ' (only sale notices: sold in 2024 per trade press); ' + zstat(k))
none_rating(k, 'Trulia page: no ratings; %s; own site: no rating widget; Apartment List: no page known' % zstat(k))

# 3 City Trust
k = '955 main st|06604'
u, rec = std_trulia(k, 'city-trust-apartments', [('606', 1650), ('511', 1400)])
floor_guess(k, '606', '6', 'Unit number only; residential floors run at least to 9 (unit 910 is listed). No page states the floor.', u)
floor_guess(k, '511', '5', 'Unit number only. No page states the floor.', u)
dog_small(k, 'Cats, small dogs allowed ... Large dogs are not permitted. (1 pet max)', u)
offer(k, rec, u)
F(k, 'pet_rent', '$50/mo', 'Pet rent ($50)', u); F(k, 'parking', 'garage, $100/mo', 'Parking Garage Pass: Available for an additional $100/month.', u)
F(k, 'utilities_included', 'water, hot water, trash', 'Water, hot water, and trash are included in the rent.', u)
F(k, 'management_company', 'Bordentown DB LLC (per Zumper); leasing office at 1485 E Main St', 'Leasing Office: 1485 E Main St, Bridgeport, CT 06608', u)
F(k, 'building_size', '117 units, 10 listed available', 'totalUnitsInBuilding 117; availableRentalUnits 10', u)
F(k, 'duplicate_listing_note', "Felner Corp's AppFolio page also lists a 955 Main Street 1BR at $1,675 with a 'sign by June 30' special; Trulia lists a 955 Main unit 302 at $1,650 while 991 Main (Arcade) also lists a unit 302", "955 Main Street, Bridgeport, CT 06604 ... Limited Time: Sign your lease by June 30", 'https://felnercorptei.appfolio.com/listings')
none_item(k, NEWS + ' (results were about other Bridgeport buildings); ' + zstat(k))
none_rating(k, 'Trulia page: no ratings; %s; Apartment List page not read' % zstat(k))

# 4 1269 Main
k = '1269 main st|06604'; u, rec = tfind(TP, '1269-main-street')
L(k, u, '', 'live', 2050, "plan '410' marked Available Now; 0 units listed", 'yes', '', rec['ts'], "Floor-plan level only: the 1BR plan named '410' (880 sqft) is $2,050 and marked Available Now, but the page lists 0 available units, so no unit or date can be checked. Page last modified 2026-10-20. Confirm by phone.")
C(k, 'elevator', 'yes (2 elevators)', '2 elevators', u, 'confirmed'); C(k, 'dogs_allowed', 'yes', rec['pet']['formattedPetsAllowed'], u, 'confirmed')
floor_guess(k, "plan '410'", '4', "The only 1BR floor plan is named '410', which looks like a unit number on floor 4; the page does not say so.", u)
dog_small(k, 'Cats, small dogs allowed ... Large dogs are not permitted. (1 pet max)', u)
F(k, 'parking', 'attached garage $100 per car, or free street parking', '$100 per car or street parking for free', u)
F(k, 'year_built', 'new construction (year not stated)', 'Brand new construction', u); F(k, 'building_size', '92 units, 0 listed available', 'totalUnitsInBuilding 92; availableRentalUnits 0', u)
F(k, 'utilities_included', 'water', 'Rent Includes: Water', u)
none_item(k, NEWS + '; Zumper address page (one 2BR listing, no reviews)'); none_rating(k, 'Trulia page: no ratings; Zumper address page: single-unit listing, no review block')

# 5 Soundview Bridgeport
k = '855 main st|06604'
u, rec = std_trulia(k, 'soundview-apartments-855', [('855-908', 2150), ('855-1015', 1950)])
floor_guess(k, '855-908', '9', "Unit number only ('855' is the street number, then 908). No page states the floor.", u)
floor_guess(k, '855-1015', '10', "Unit number only (855 then 1015). No page states the floor. Note: listed at 330 sqft.", u)
dog_small(k, 'Cats, small dogs allowed ... Large dogs are not permitted. (1 pet max)', u)
offer(k, rec, u)
F(k, 'special_offer', '**NOW OFFERING 1 MONTH FREE ... 1 MONTH FREE on qualifying leases; $0 SECURITY DEPOSIT for qualifying essential workers', 'From the description. The page does not say whether the listed price is gross or net-effective.', u)
F(k, 'parking', 'attached garage (fee not stated)', 'Parking: Attached Garage', u); F(k, 'building_size', '121 units, 5 listed available', 'totalUnitsInBuilding 121; availableRentalUnits 5', u)
none_item(k, NEWS + '; Zumper: no page at the address URL (404)'); none_rating(k, 'Trulia page: no ratings; Zumper: 404 at the address URL; Apartment List page (/ct/bridgeport/soundview) not read')

# 6 Siena
k = '2340 n ave|06604'; u, rec = tfind(TP, 'the-siena')
L(k, u, '', 'live', 1899, "plan '2J' marked Available Now; 0 units listed", 'yes', '', rec['ts'], "Floor-plan level only: 1BR plan '2J' (850 sqft) $1,899 marked Available Now; 0 available units listed, so no date can be checked. Page last modified 2026-10-29.")
C(k, 'elevator', 'yes; 7 storeys', 'The Siena is a mid-rise, 7 story elevator building ... Building offers brand new elevator', u, 'confirmed')
C(k, 'dogs_allowed', 'yes', rec['pet']['formattedPetsAllowed'], u, 'confirmed')
floor_guess(k, "plan '2J'", '2', "The floor plan is named '2J', which reads as apartment J on floor 2; the page does not state the floor.", u)
dog_small(k, 'Cats, small dogs allowed (2 pet max) ... Pet friendly (fees and breed restrictions apply).', u)
offer(k, rec, u, 'Free month is tied to an 18-month term; the page does not say whether the listed price is gross or net-effective.')
F(k, 'pet_rent', '$50/mo; pet deposit $250', 'Pet rent ($50); Pet deposit ($250)', u); F(k, 'parking', 'on-site lot, extra cost (amount not stated)', 'On-site parking is available at an additional cost.', u)
F(k, 'year_built', '1969 (Zumper)', 'year_built 1969', ZB[k]['url']); F(k, 'management_company', 'Kolich Holdings, LLC/Empire Residential, LLC (Zumper; page last modified Jan 2025)', 'pm_name', ZB[k]['url'])
none_item(k, NEWS + '; ' + zstat(k)); none_rating(k, 'Trulia page: no ratings; ' + zstat(k))

# 7 Arcade
k = '991 main st|06604'; u = URL[k]; at = AL[u]['ts']; a = alunit(u, '302'); a2 = alunit(u, '1 bed, 1 bath, $1675'); FL = 'https://felnercorptei.appfolio.com/listings'
L(k, u, '302', 'live', a['price'], "available now (Apartment List available_on %s; manager's page: Available NOW)" % a['available_on'], 'yes', FL, at, "Also on the manager's AppFolio page: '991 Main Street, Unit 302' $1,675 Available NOW. Apartment List's availability date is stale (2025-06-01) and the description still says 'FIRST MONTH FREE -- sign by June 30'.")
L(k, u, '1 bed, 1 bath, $1675', 'live', a2['price'], 'available now (available_on %s)' % a2['available_on'], 'yes', FL, at, "Unnamed second listing at the same price and size (751 sqft); probably the same apartment as unit 302 advertised twice. Trulia (captured 21:50 UTC) counts 1 available unit in 23.")
C(k, 'elevator', 'yes', 'On-site laundry and elevator access.', u, 'confirmed')
floor_guess(k, '302', '3', "Unit number only; the homes are 'set above street-level shops'. No page states the floor.", FL)
C(k, 'floor', 'unconfirmed (unnamed listing): unknown', 'No unit number given.', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Pet Policy: Cats allowed, Small dogs allowed', FL, 'confirmed'); dog_small(k, 'Pet Policy: Cats allowed, Small dogs allowed', FL)
F(k, 'special_offer', 'FIRST MONTH FREE -- sign by June 30. *Restrictions apply.', 'Apartment List description (June deadline has passed). Trulia (captured 2026-11-15 21:50 UTC): "1 Month Free on a 13-Month Lease". Move-in: first month\'s rent + security deposit only. Neither page says whether $1,675 is gross or net-effective.', u)
F(k, 'management_company', 'Felner Corporation', 'apply link felnercorptei.appfolio.com; Trulia names Felner Corportation', FL)
F(k, 'building_size', '23 units, 1 listed available', 'totalUnitsInBuilding 23; availableRentalUnits 1 (Trulia capture 2026-11-15 21:50 UTC)', tfind(TC, 'city-trust-collection-arcade')[0])
none_item(k, NEWS.replace('one web search', 'the City Trust web search') + '; Apartment List page (no reviews); ' + zstat(k)); none_rating(k, 'Apartment List %s: no rating or reviews; %s' % (u, zstat(k)))

# 8 The August
k = '55 e main st|06608'; tu, rec = tfind(TP, 'the-august'); au = 'https://www.apartmentlist.com/ct/bridgeport/the-august-at-steelpointe-harbor'; OWN = 'https://theaugust.com/floorplans/'
a = alunit(au, '1031'); o = AUG['1031']
L(k, au, '1031', 'live', a['price'], 'Available Now', 'yes', OWN, AL[au]['ts'], "Own site: #1031 $2,791 total monthly ($2,687 base rent + $104 required fees), Available Now, Floor 1, plan 'Stern Watch - B1.A -100'. INCOME-RESTRICTED: the plan page says 'Income Limits Apply. Build for Connecticut Income Qualification required.' FLOOR 1. Trulia no longer lists unit 1031 (it lists 1005, 2005, 2035 and others at $2,687).")
x = tunit(rec, '1054'); o2 = AUG['1054']
L(k, tu, '1054', 'live', x['price'], x['avail'], 'yes', OWN, rec['ts'], "Own site: #1054 $2,046 total monthly ($1,942 base + $104 fees), Available Now, Floor 1, plan 'Soft Shore - S1.C -80'. INCOME-RESTRICTED (80% AMI plan: 'Income Limits Apply'); the same plan at market rate is $2,400. FLOOR 1.")
C(k, 'elevator', 'yes', "Elevator (Trulia features; Apartment List amenity 'Elevator')", tu, 'confirmed')
C(k, 'floor', '1 (unit 1031)', "Building's own unit data: apartment_number 1031, floor_name '1'; plan page lists it under 'Floor 1'", OWN, 'confirmed')
C(k, 'floor', '1 (unit 1054)', "Building's own unit data: apartment_number 1054, floor_name '1'; plan page lists it under 'Floor 1'", OWN, 'confirmed')
C(k, 'dogs_allowed', 'yes', 'We allow up to two pets per apartment', 'https://theaugust.com/faqs/', 'confirmed')
C(k, 'dog_weight_limit', '100 lb combined for up to two pets', 'We allow up to two pets per apartment, with a combined weight limit of 100 pounds at full growth.', 'https://theaugust.com/faqs/', 'confirmed')
F(k, 'income_restricted_units', 'stored units 1031 (plan -100) and 1054 (plan -80) are Build for Connecticut units: renters must earn between 80% and 120% of area median income', 'Select studio, one-bedroom, and two-bedroom apartments at The August are part of the Build for Connecticut Housing program. These apartments are reserved for renters earning between 80% and 120% of the Area Median Income (AMI).', 'https://theaugust.com/p/build-for-connecticut/')
F(k, 'income_limits', 'Studio 80% AMI: 1 occupant $87,808; One Bedroom + Den 100% AMI: 1 occupant $109,760 (maximum yearly gross income); minimum income two times monthly gross rent', 'Studio 80% AMI: 1 Occupant - Yearly Gross Income $87,808 ... One Bedroom + Den 100% AMI: 1 Occupant - Yearly Gross Income $109,760', 'https://theaugust.com/p/build-for-connecticut/')
F(k, 'special_offer', 'Move In Now. Pay Rent in 2027! Make your move today and enjoy the rest of 2026 rent-free! Plus, receive one complimentary parking space for your entire initial lease term.', 'Trulia and Apartment List wording. Prices shown are base rent (gross); the page does not give a net-effective figure.', tu)
F(k, 'special_offer', '2 Months Free + Complimentary Parking: Move in and enjoy 2 months free on a lease term of 10 months or longer, plus one complimentary parking space for your entire first lease term.', "Own site wording (differs from the aggregator text). Own site states prices as 'Total Monthly Price includes base rent, all monthly mandatory and any user-selected optional fees': gross, not net-effective. Whether the offer applies to income-restricted units is not stated.", OWN)
F(k, 'required_monthly_fees', '$104/mo on top of base rent', 'Apartment List: base_price 2687, required_fees 104, total_price 2791; own site: $2,791 /mo* vs $2,687 Base Rent', OWN)
F(k, 'pet_rent', '$50/mo per pet; one-time $250', 'Monthly dog rent $50/mo; One-time fee $250', tu)
F(k, 'pool', 'outdoor saltwater pool', 'Oceanfront Saltwater Pool & Resort-Style Sun Deck', 'https://theaugust.com/amenities/')
F(k, 'management_company', 'Flaherty & Collins Properties', 'Property management company: Flaherty & Collins Properties', tu)
F(k, 'year_built', '2026 (opened August 2026)', 'ribbon cutting ceremony for The August ... on Aug. 6, 2026', 'https://www.ctpublic.org/news/2026-08-06/bridgeports-steelpointe-harbor-project-wraps-up-first-residential-phase')
F(k, 'building_size', '420 apartments (news); Trulia shows 157 units available', 'The August, situated on the city\'s waterfront, features 420 apartments.', 'https://www.ctpublic.org/news/2026-08-06/bridgeports-steelpointe-harbor-project-wraps-up-first-residential-phase')
F(k, 'floors_with_units', 'unit data shows floors 1 to 4 only', 'floor_name values 1,2,3,4 across 319 units', OWN)
I(k, 'other', '2026-08-06', 'Several units at The August are reserved for middle-income residents, although income restrictions apply.', 'Connecticut Public', 'https://www.ctpublic.org/news/2026-08-06/bridgeports-steelpointe-harbor-project-wraps-up-first-residential-phase', 'building')
I(k, 'other', '2026-08-06', "“We just started moving residents in and I think we’re getting close to right around 10% occupied and maybe over 20% leased,\" he said.", 'Connecticut Public', 'https://www.ctpublic.org/news/2026-08-06/bridgeports-steelpointe-harbor-project-wraps-up-first-residential-phase', 'building')
I(k, 'other', '2026-04-13', 'The August at Steelpointe Harbor also includes more affordable options, with studios starting at $1,965 for 447 square feet. Some apartments will be reserved for affordable or middle-income renters.', 'News 12', 'https://connecticut.news12.com/2026/04/13/luxury-bridgeport-apartment-complex-comes-with-rents-as-high-as-nearly-10k/jEvgKDyZorhKqtMbYolRb', 'building')
none_rating(k, 'Apartment List %s: no rating; Zumper address page is a furnished-rental (Landing) listing with no reviews; Trulia: no ratings; own site: no rating widget. Building opened August 2026.' % au)

# 9 Brookfield Village
k = '7 station rd|06804'
u, rec = std_trulia(k, 'brookfield-village', [('5204', 2590), ('6108', 2590)])
floor_guess(k, '5204', '2', "Four-digit unit number, probably building 5, floor 2, unit 04. No page states the floor.", u)
floor_guess(k, '6108', '1 (possible ground floor)', "Four-digit unit number, probably building 6, floor 1, unit 08; if so this is a first-floor unit. No page states the floor.", u)
dog_none(k, 'Dogs: Allowed; Size allowed: Small, large | Restrictions: None', u)
offer(k, rec, u, "The offer text requires a lease 'starting by November 1st', which has passed. The page does not say whether the listed price is gross or net-effective.")
F(k, 'management_company', 'Simon Konover Company', 'Property management company: Simon Konover Company', u); F(k, 'pool', 'yes (indoor or outdoor not stated)', 'Pool', u)
F(k, 'building_size', '48 units, 3 listed available', 'totalUnitsInBuilding 48; availableRentalUnits 3', u)
F(k, 'own_site', 'www.brookfieldvillageapts.com returned 403 (bot wall); not read', '', 'https://www.brookfieldvillageapts.com/')
none_item(k, NEWS + '; Zumper: 404 at the address URL'); none_rating(k, 'Trulia page: no ratings; Zumper: 404 at the address URL; own site blocked (403)')

# 10 1 Kennedy Flats
k = '1 kennedy ave|06810'; u = URL[k]; at = AL[u]['ts']; tcu, tc = tfind(TC, '1-kennedy-ave')
for unit in ('2117', '2119'):
    a = alunit(u, unit)
    L(k, u, unit, 'live', a['price'], 'available now (available_on %s)' % a['available_on'], 'yes', 'https://www.1kennedyflats.com/', at, 'Total with required fees $%s (15-month term). Own site returned 403 (bot wall). Trulia capture at 21:51 UTC showed this unit at $2,374.' % a['total_price'])
    floor_guess(k, unit, '1 (possible ground floor)', 'Four-digit unit number, probably building 2, floor 1, unit %s (other listed units: 2303, 2423, 1315, 5106). If so this is a first-floor unit. No page states the floor.' % unit[2:], u)
C(k, 'elevator', 'yes', "Apartment List amenity 'Elevator'", u, 'confirmed')
C(k, 'dogs_allowed', 'yes', 'allowed_pets: cats, dogs; 2 pets maximum', u, 'confirmed')
C(k, 'dog_weight_limit', '50 lb per Apartment List; Trulia shows 80 lb for dogs (50 lb for cats): both pass, sources differ', 'restrictions: Aggressive breeds; Weight limit: 50 lbs', u, 'confirmed')
C(k, 'dog_weight_limit', '80 lb (Trulia capture 2026-11-15 21:51 UTC)', 'Dogs: Weight limit (lbs.) 80; Monthly dog rent $60/mo; One-time fee $500', tcu, 'confirmed')
F(k, 'special_offer', "Fall Special! Enjoy $1,500 off your first full month's rent. Select homes only. Terms and conditions apply. Valid for new, first-time renters only. Contact the leasing office for more details.", 'Listed price is base rent (base_price field); not stated as net-effective.', u)
F(k, 'pet_rent', '$50/month per dog, $400 fee per dog (Apartment List); Trulia shows $60/mo and $500', 'rent: $50/month per dog; fee: $400 per dog', u)
F(k, 'required_monthly_fees', '$90/mo (total_price minus base_price); $50 amenity fee named', 'required_fees 90; move_in_fees_text: $50 amenity fee', u)
F(k, 'parking', 'second reserved spot $50', 'Reserved Parking (if applicable): $50 for second spot', u); F(k, 'utilities_included', 'sewer, trash, water', 'Sewer, Trash, Water', u)
F(k, 'year_built', '2015', 'year_built 2015', u); F(k, 'management_company', 'Jones Street Residential', 'Trulia capture: Property management company Jones Street Residential', tcu)
F(k, 'building_size', '374 units', 'total_units_count 374', u); F(k, 'pool', 'yes, seasonal', 'Seasonal Pool', ZB[k]['url'])
none_item(k, NEWS + '; ' + zstat(k))
R(k, 'Apartment List', 5, 5, 1, '2026-11-15', 0, '', '', '', '', u)

# 11 Brookview Commons II (West)
k = '333 main st|06810'; u = URL[k]; at = AL[u]['ts']; BL = 'https://brt.appfolio.com/listings'; z = ZB[k]
a = alunit(u, 'BC-603W'); L(k, u, 'BC-603W', 'live', a['price'], "available now (available_on %s); manager's page: Available NOW" % a['available_on'], 'yes', BL, at, "Manager's AppFolio page: '333 Main Street, Unit 603' RENT $2,185, TOTAL MONTHLY PRICE $2,235 ($50 amenity fee), Available NOW.")
a = alunit(u, 'BC-519W'); L(k, u, 'BC-519W', 'live', a['price'], "available now (available_on %s); manager's page: Available NOW" % a['available_on'], 'yes', BL, at, "Studio. Manager's AppFolio page: '333 Main Street, Unit 519' RENT $1,975, TOTAL MONTHLY PRICE $2,025, Available NOW.")
C(k, 'elevator', 'yes', 'NON-SMOKING elevator building.', u, 'confirmed')
C(k, 'floor', '6 (unit BC-603W)', "Apartment List floor plan for this unit is named 'BCW-A1-6th' (the manager's feed labels sixth-floor plans '-6th')", u, 'confirmed')
floor_guess(k, 'BC-519W', '5', "Unit number only; its floor plan is 'BCW-E1' (not the '-6th' variant). No page states the floor.", u)
C(k, 'dogs_allowed', 'yes', 'Pet Policy: Cats allowed, Small dogs allowed', BL, 'confirmed')
dog_small(k, 'Small pet friendly, restrictions and fees apply. / Small Pets Permitted (Restr. Apply)', 'https://www.brt.com/brookview-west')
F(k, 'required_monthly_fees', '$50/mo amenity fee', '[$50/mo Amenity Fee Applies]', BL); F(k, 'management_company', 'BRT General Corporation (owner-manager, "Since 1955")', 'BRT General Realty', 'https://www.brt.com/brookview-west')
F(k, 'year_built', '2023', 'year_built 2023', u); F(k, 'building_size', '149 units', 'total_units_count 149', u)
F(k, 'pool', 'outdoor, seasonal (pool terrace)', 'Pool Terrace (seasonal)', 'https://www.brt.com/brookview-west'); F(k, 'utilities_included', 'refuse removal', 'Utilities Included: Refuse Removal', BL)
F(k, 'special_offer', '** SPECIAL: $1,000 Security for Qual MI **', 'A reduced security deposit, not a rent discount; listed rent is gross.', BL)
R(k, 'Google rating shown on Zumper', 4.3, 5, 14, '2024-12-07', 7, 0, 0, 0, '', z['url'])
I(k, 'positive', '2024-10-21', 'The management is responsive and compassionate, and maintenance is really friendly. I got to move in with my dog and there\'s a dog park and wash on site.', 'Google review shown on Zumper', z['url'], 'building', z['at'])
I(k, 'positive', '2024-08-14', 'Great location. Close to all. Dog friendly! Great amenities (pool, club room, grills).', 'Google review shown on Zumper', z['url'], 'building', z['at'])

# 12 Brookview Commons East
k = '30 crosby st|06810'; u = URL[k]; at = AL[u]['ts']; z = ZB[k]
a = alunit(u, 'BC-524'); L(k, u, 'BC-524', 'live', a['price'], "available %s; manager's page: Available 11/26/26" % a['available_on'], 'yes', BL, at, "Manager's AppFolio page: '30 Crosby Street, Unit 524' RENT $1,925, TOTAL MONTHLY PRICE $1,975, Available 11/26/26.")
a = alunit(u, 'BC-406'); L(k, u, 'BC-406', 'live', a['price'], "available %s; manager's page: Available 12/15/26" % a['available_on'], 'yes', BL, at, "Available 12/15/26 is the last day of the window. Manager's AppFolio page: Unit 406 RENT $1,925, TOTAL $1,975.")
C(k, 'elevator', 'yes', 'Modern, secure elevator building built in 2007 is in CityCenter Danbury', 'https://www.brt.com/brookview-commons', 'confirmed')
floor_guess(k, 'BC-524', '5', 'Unit number only. No page states the floor.', BL); floor_guess(k, 'BC-406', '4', 'Unit number only. No page states the floor.', BL)
C(k, 'dogs_allowed', 'yes', 'Pet Policy: Cats allowed, Small dogs allowed', BL, 'confirmed')
C(k, 'dog_weight_limit', 'small dogs only; no pound figure on any page read (the stored 25 lb could not be traced to a page)', 'Small Pets Permitted (Restr. Apply)', 'https://www.brt.com/brookview-commons', 'confirmed')
F(k, 'required_monthly_fees', '$50/mo amenity fee', 'AMENITY FEE $50/mo', 'https://www.brt.com/brookview-commons'); F(k, 'year_built', '2007', 'elevator building built in 2007', 'https://www.brt.com/brookview-commons')
F(k, 'management_company', 'BRT General Corporation', 'BRT General Realty', 'https://www.brt.com/brookview-commons'); F(k, 'parking', 'assigned outside parking included', 'Utilities Included: Refuse Removal, Assigned Outside Parking', BL)
F(k, 'laundry', 'shared, on every floor', 'Laundry Facilities on Every Floor', 'https://www.brt.com/brookview-commons'); F(k, 'building_size', '115 units', 'total_units_count 115', u)
F(k, 'special_offer', '** SPECIAL: $1,000 Security for Qual MI **', 'A reduced security deposit, not a rent discount; listed rent is gross.', BL)
R(k, 'Google rating shown on Zumper', 3.6, 5, 18, '2024-12-07', 6, 0, 0, 0, '', z['url'])
I(k, 'other', '2021-10-06', 'Apartments do not have balcony/patio and the visitor parking spots are very limited but overall very good apartment.', 'Google review shown on Zumper', z['url'], 'garage_or_lot', z['at'])
I(k, 'management', '2021-10-09', 'maintenance staff are good and quickly resolve issues. but common area carpets & laundry area needs more frequent cleaning.', 'Google review shown on Zumper', z['url'], 'building', z['at'])

# 13 Ridgeway Place
k = '10 clapboard ridge rd|06811'; u = URL[k]; at = AL[u]['ts']; tcu, tc = tfind(TC, 'ridgeway-place'); a = alunit(u, '71A')
L(k, u, '71A', 'live', a['price'], 'available now (available_on %s)' % a['available_on'], 'yes', 'https://www.ridgewaydanbury.com/', at, "Studio ('Florence', 500 sqft). Total with required fees $%s (17-month term). Own site returned 403 (bot wall)." % a['total_price'])
C(k, 'elevator', 'unconfirmed: neither Apartment List nor Trulia lists an elevator; a 1973 complex with unit labels like 71A and 32H reads as low-rise garden buildings', 'amenities: Pool, Cats allowed, Dogs allowed, Pet friendly (no Elevator)', u, 'unconfirmed')
floor_guess(k, '71A', 'unknown', "'71A' looks like building 71, apartment A; no floor can be read from it and no page states one.", u)
C(k, 'dogs_allowed', 'yes', 'allowed_pets: cats, dogs; limit 2', u, 'confirmed')
C(k, 'dog_weight_limit', '80 lb (Trulia capture 2026-11-15 21:51 UTC); Apartment List gives no number', 'Dogs: Weight limit (lbs.) 80; Monthly dog rent $60/mo; One-time fee $500', tcu, 'confirmed')
F(k, 'special_offer', 'Fall Special! Enjoy one month free on select apartment homes when applying within 72 hours of touring. Limited-time offer. Terms and conditions apply. Subject to availability. Valid for first-time residents only. Contact the leasing office for more details.', 'Listed price is base rent (base_price field); not stated as net-effective.', u)
F(k, 'pet_rent', '$60/mo per dog; $500 fee', 'dogs: rent 60.0, fee 500.0', u); F(k, 'required_monthly_fees', '$90/mo (total_price minus base_price)', 'required_fees 90', u)
F(k, 'year_built', '1973', 'year_built 1973', u); F(k, 'building_size', '192 units', 'total_units_count 192', u); F(k, 'pool', 'yes, with sundeck (outdoor implied, not stated)', 'sparkling pool with sundeck', u)
F(k, 'management_company', 'Jones Street Residential (Trulia capture); batch file says Cushman & Wakefield', 'Property management company: Jones Street Residential', tcu)
none_item(k, NEWS + ' (a search summary mentioned a reviewer complaint about assigned parking on a site we do not read: not recorded); Zumper: 404 at the address URL')
none_rating(k, 'Apartment List %s: no rating; Zumper: 404 at the address URL; own site blocked (403)' % u)

# 14 5545 Park
k = '5545 park ave|06825'
u, rec = std_trulia(k, '5545-park', [('408', 2700)])
floor_guess(k, '408', '4', 'Unit number only. No page states the floor.', u)
dog_small(k, 'Cats, small dogs allowed ... Large dogs are not permitted.', u); offer(k, rec, u, 'Free month is tied to a 13-month lease; the page does not say whether $2,700 is gross or net-effective.')
F(k, 'parking', 'surface lot included; garage extra (fee not stated)', 'Parking around the lot is included. Garage parking available for an additional fee.', u)
F(k, 'building_size', '120 units, 2 listed available', 'totalUnitsInBuilding 120; availableRentalUnits 2', u); F(k, 'own_site', 'www.5545park.com returned 403; not read', '', 'https://www.5545park.com/')
none_item(k, NEWS + '; Zumper: 404 at the address URL'); none_rating(k, 'Trulia page: no ratings; Zumper: 404 at the address URL; own site blocked (403)')

# 15 Alto Fairfield Metro
k = '1401 kings hwy|06824'; u = URL[k]; at = AL[u]['ts']; tcu, tc = tfind(TC, 'alto-fairfield-metro'); a = alunit(u, '402A')
L(k, u, '402A', 'changed', a['price'], 'available now (available_on %s)' % a['available_on'], 'no', 'https://www.altofairfieldmetro.com/', at, "Studio (559 sqft). Was $2,335, now $2,343; total with required fees $%s (14-month term). Trulia capture at 21:48 UTC also showed $2,343. Own site returned 403." % a['total_price'])
C(k, 'elevator', 'yes', "Apartment List amenity 'Elevator'", u, 'confirmed'); floor_guess(k, '402A', '4', "Unit number only ('A' may be a building or wing). No page states the floor.", u)
C(k, 'dogs_allowed', 'yes', 'allowed_pets: cats, dogs; limit 2', u, 'confirmed')
C(k, 'dog_weight_limit', '75 lb (Trulia capture 2026-11-15 21:48 UTC); Apartment List gives no number', 'Dogs: Weight limit (lbs.) 75; Monthly dog rent $70/mo; One-time fee $500', tcu, 'confirmed')
F(k, 'pet_rent', '$70/mo; $500 fee', 'rent: 70.0; fee: 500.0', u); F(k, 'required_monthly_fees', '$97.95/mo', 'required_fees 97.95', u)
F(k, 'parking', 'garage (fee not stated)', 'parking comment: Garage', u); F(k, 'utilities_included', 'gas, hot water, sewer, trash, water', 'Gas, Hot Water, Sewer, Trash, Water', u)
F(k, 'management_company', 'Jones Street Residential (Trulia capture); batch file says Konover Residential Corporation', 'Property management company: Jones Street Residential', tcu); F(k, 'building_size', '160 units', 'total_units_count 160', u)
none_item(k, NEWS + '; Zumper: 404 at the address URL'); none_rating(k, 'Apartment List %s: no rating; Zumper: 404; own site blocked (403)' % u)

# 16 Broadmoor
k = '676 mix ave|06514'; u, rec = tfind(TP, 'broadmoor')
x = tunit(rec, '18'); OLD = ' LISTING RECORD LAST MODIFIED 2026-01-27 (about 10 months ago): treat as unverified until the office confirms.'
L(k, u, '18', 'live', x['price'], x['avail'], 'yes', '', rec['ts'], "Studio 'Madison' (570 sqft); the only unit listed in a 498-unit complex." + OLD)
L(k, u, '', 'live', 1725, "plan 'Birmingham/ Brighton' marked Available Now; no unit listed", 'yes', '', rec['ts'], "Floor-plan level only: 1BR plan 'Birmingham/ Brighton' (800 sqft) $1,725; no unit or date." + OLD)
C(k, 'elevator', 'yes (listed for the complex; whether every building has one is not stated)', 'Elevator', u, 'confirmed'); C(k, 'dogs_allowed', 'yes', 'Dogs and Cats welcome with 25lb weight limit.', u, 'confirmed')
floor_guess(k, '18', 'unknown', "Unit '18' does not encode a floor and the page states none.", u); C(k, 'floor', 'unconfirmed (1BR plan): unknown', 'No unit number given.', u, 'unconfirmed')
C(k, 'dog_weight_limit', '25 lb (exactly at the gate)', 'Pets Upon Approval. Dogs and Cats welcome with 25lb weight limit.', u, 'confirmed')
offer(k, rec, u)
F(k, 'pet_rent', '$50/mo dogs; $250 or $500 pet fee', '$250 or $500 pet fee, $50 pet rent for dogs, $35 pet rent for cats.', u); F(k, 'utilities_included', 'heat, hot water (AC named in the offer)', 'Rent Includes: Heat, Hot Water', u)
F(k, 'parking', 'lot; detached garages available (fee not stated)', 'Parking Lot, Detached Garage ... Private garages are also available.', u); F(k, 'pool', 'yes (indoor or outdoor not stated)', 'a beautiful swimming pool', u)
F(k, 'management_company', 'CT Management', 'Property management company: CT Management', u); F(k, 'lease_terms', '9-12 months; 9-month term costs $100 more per month', 'Terms of lease range from 9-12 months. 9 month term with a $100 premium per month.', u)
F(k, 'own_site', 'www.broadmoorapts.com returned 403; not read', '', 'https://www.broadmoorapts.com/')
none_item(k, NEWS + ' (tenant-union coverage found was for a different Mix Avenue complex); ' + zstat(k)); none_rating(k, 'Trulia page: no ratings; ' + zstat(k))

# 17 Whitney Towers
k = '2405 whitney ave|06518'; z = ZB[k]
u, rec = std_trulia(k, 'whitney-towers', [('306', 1945), ('409', 1865)])
floor_guess(k, '306', '3', 'Unit number only (units up to 702 are listed). No page states the floor.', u); floor_guess(k, '409', '4', 'Unit number only. No page states the floor.', u)
dog_none(k, 'Dogs: Allowed; Size allowed: Small, large', u, ' (large dogs are allowed)')
F(k, 'pet_rent', '$50 per dog per month', 'Dog rent ($50 per dog)', u); F(k, 'required_monthly_fees', 'none', 'WE HAVE NO FEES! No amenity, admin, or trash fees!!', u)
F(k, 'utilities_included', 'heat, hot water, air conditioning', '**Heat, Hot water, and A/C are included.', u); F(k, 'parking', 'on-site, off-street, solar carports (fee not stated)', 'Off Street Parking, Solar Carports', u)
F(k, 'management_company', 'Franklin Communities', 'Property management company: Franklin Communities', u); F(k, 'building_size', '85 units, 6 listed available', 'totalUnitsInBuilding 85; availableRentalUnits 6', u)
R(k, 'Google rating shown on Zumper', 4.8, 5, 14, '2024-10-31', 8, 0, 0, 0, '', z['url'])
I(k, 'positive', '2024-04-17', 'I especially appreciate the quick turnaround of maintenance and the tenants are friendly.', 'Google review shown on Zumper', z['url'], 'building', z['at'])
I(k, 'positive', '2024-03-29', "I have been living here at Whitney Towers for 5 Years. I’m glad to have moved here. I needed something that didn’t have stairs.", 'Google review shown on Zumper', z['url'], 'building', z['at'])
I(k, 'positive', '2018-03-23', 'Noise level is low and I can barely ever hear other tenants from my apartment. A/C and heat are included and the panels on the roof keep my electric costs really low.', 'Google review shown on Zumper', z['url'], 'building', z['at'])

# 18-21 Metro Star
MS = 'https://www.metrostarproperties.com/property/'
def metro(k, frag, units, own, ownq, floors):
    u, rec = std_trulia(k, frag, units, site=own or 'https://www.metrostarproperties.com/')
    for unit, why in floors: floor_guess(k, unit, '2', why, u)
    if own: C(k, 'elevator', 'yes (own site)', ownq, own, 'confirmed')
    return u, rec
WHY = "Unit label reads as building or street number, then floor 2, then a letter (third-floor units on the same page are labelled '3'). No page states the floor."
k = '1 new haven ave|06460'
u, rec = metro(k, 'metro-point', [('1-2K', 2462), ('1-2R', 2562)], MS + 'metro-point', 'Elevator', [('1-2K', WHY), ('1-2R', WHY)])
dog_none(k, 'Dogs: Allowed; Size allowed: Small, large | Restrictions: None', u)
F(k, 'pet_rent', '$55 per pet per month; $550 pet fee', 'Pet Rent ($55 per pet); Pet Fee ($550)', u); F(k, 'parking', 'gated garage, $39 per vehicle per month', 'Garage parking fee ($39 per vehicle)', u)
F(k, 'required_monthly_fees', 'trash removal fee (amount not shown); water and sewer included', 'Trash Removal Fee = Contact for details; Water and sewer fee = Included', u)
F(k, 'management_company', 'Metro Star Property Management', 'Property management company', u); F(k, 'building_size', '41 units, 4 listed available', 'totalUnitsInBuilding 41; availableRentalUnits 4', u)
none_item(k, NEWS + ' (one search covering the four Metro Star buildings); Zumper: 404 at the address URL'); none_rating(k, 'Trulia page: no ratings; Zumper: 404; Metro Star site: no rating shown')
k = '135 broad st|06460'
u, rec = metro(k, 'metro-on-broad', [('131-2F', 2237), ('127-2R', 2392)], MS + 'metro-on-broad', 'Community amenities include off-street parking, high-speed elevators, state-of-the-art fitness center.', [('131-2F', WHY), ('127-2R', WHY)])
C(k, 'dog_weight_limit', 'unconfirmed: Trulia says no restrictions, but the manager\'s page says size restrictions apply and gives no number', 'Our pet-friendly community (breed and size restrictions) shares your love for your pets', MS + 'metro-on-broad', 'unconfirmed')
F(k, 'pet_rent', '$55 per pet per month; $550 pet fee', 'Pet Rent ($55 per pet); Pet Fee ($550)', u); F(k, 'parking', 'garage $69/mo; off-street parking', 'Garage parking fee ($69)', u)
F(k, 'required_monthly_fees', 'amenity fee and trash removal fee (amounts not shown)', 'Amenity Fee = Contact for details; Trash Removal Fee = Contact for details', u)
F(k, 'management_company', 'Metro Star Property Management', 'Property management company', u); F(k, 'building_size', '77 units, 3 listed available', 'totalUnitsInBuilding 77; availableRentalUnits 3', u)
F(k, 'unit_type', 'both stored units are studios (131-2F 480 sqft; 127-2R Studio Plus 493 sqft)', 'Studio; Studio Plus', u)
none_item(k, NEWS + ' (one search covering the four Metro Star buildings); Zumper: 404'); none_rating(k, 'Trulia page: no ratings; Zumper: 404; Metro Star site: no rating shown')
k = '121 w main st|06460'
u, rec = metro(k, 'metro-121', [('121-2T', 2468)], MS + 'metro-121', 'These beautiful apartments in Milford, CT offer covered parking, elevator, secured access, additional storage and a fitness center.', [('121-2T', WHY)])
dog_none(k, 'Dogs: Allowed; Size allowed: Small, large | Restrictions: None', u, " (a sister building's page says breed and size restrictions apply)")
F(k, 'pet_rent', '$55 per pet per month; $550 pet fee', 'Pet Rent ($55 per pet); Pet Fee ($550)', u); F(k, 'parking', 'covered parking $45 each per month', 'Covered Parking Rent ($45 each)', u)
F(k, 'year_built', '2015 (Zumper)', 'year_built 2015', ZB[k]['url']); F(k, 'management_company', 'Metro Star Property Management', 'Property management company', u); F(k, 'building_size', '49 units, 1 listed available', 'totalUnitsInBuilding 49; availableRentalUnits 1', u)
none_item(k, NEWS + ' (one search covering the four Metro Star buildings); ' + zstat(k)); none_rating(k, 'Trulia page: no ratings; %s; Metro Star site: no rating shown' % zstat(k))
k = '249 bridgeport ave|06460'
u, rec = std_trulia(k, 'value-star-249', [('249-204', 2285), ('249-209', 2285)])
W2 = "Unit label is the street number then 204/209 (units 302 to 507 are also listed), so floor 2 is the natural reading. No page states the floor."
floor_guess(k, '249-204', '2', W2, u); floor_guess(k, '249-209', '2', W2, u)
dog_none(k, 'Dogs: Allowed; Size allowed: Small, large | Restrictions: None', u); offer(k, rec, u)
F(k, 'income_restricted_units', "the building mixes market-rate and income-restricted units; both stored units are on the 'Market Rate' plan", 'Market Rate and Income Restricted Units Now Accepting Applications', u)
F(k, 'utilities_included', 'water, sewer, trash', 'No surprise add-on charges, water, sewer and trash included in the base rent.', u); F(k, 'parking', 'surface lot (fee not stated)', 'Off Street Parking, Surface Lot', u)
F(k, 'year_built', 'new (year not stated)', 'Brand New Now Leasing!', u); F(k, 'management_company', 'Metro Star Property Management', 'Property management company', u); F(k, 'building_size', '80 one-bedroom apartments in two buildings; 7 listed available', 'features 80 modern one-bedroom apartments across two contemporary buildings', u)
none_item(k, NEWS + ' (one search covering the four Metro Star buildings); Zumper: 404'); none_rating(k, 'Trulia page: no ratings; Zumper: 404; valuestarapartments.com is a script shell with no text')

# 22 Covered Bridge
k = '9 covered bridge rd|06470'; u, rec = tfind(TP, 'covered-bridge'); KS = 'https://www.keen-summit.com/project/bankruptcy-sale-covered-bridge-newtown-ct'
L(k, u, '', 'live', 2300, "plans 'The Willow' and 'The Willow- ADA' marked Available Now; 0 units listed", 'yes', '', rec['ts'], "Floor-plan level only: both 1BR plans (751 sqft) $2,300 marked Available Now; 0 available units listed, so no unit, floor or date can be checked. Page last modified 2026-09-01. Confirm by phone.")
C(k, 'elevator', 'yes', 'Community Clubhouse, Elevator Access, Close Proximity to I-84', u, 'confirmed'); C(k, 'dogs_allowed', 'yes', rec['pet']['formattedPetsAllowed'], u, 'confirmed')
C(k, 'floor', 'unconfirmed: unknown (no unit listed); the buildings have 3 storeys', '210 total units across seven 3-story buildings (30 units each)', KS, 'unconfirmed')
dog_none(k, 'Dogs: Allowed; Number allowed 2; Size allowed: Small, large', u, ' (large dogs are allowed, two pets)'); offer(k, rec, u, 'A one-time $1,000 credit; the page does not say whether $2,300 is gross or net-effective.')
F(k, 'pet_rent', '$60/mo', 'Pet Rent ($60)', u); F(k, 'parking', 'garage $150-175 per vehicle per month', 'Garage parking fee ($150-175 per vehicle)', u)
F(k, 'required_monthly_fees', 'amenity fee (amount not shown)', 'Amenity Fee = Contact for details', u); F(k, 'pool', 'yes (indoor or outdoor not stated)', 'Swimming Pool, Sun Deck', u)
F(k, 'management_company', 'PeakMade', 'Property management company: PeakMade', u); F(k, 'building_size', '210 units in seven 3-storey buildings on 21.5 acres', '210 total units across seven 3-story buildings (30 units each)', KS)
F(k, 'ownership_status', 'owner is in Chapter 11 bankruptcy and the property is being sold', 'Covered Bridge has retained Keen-Summit Capital Partners LLC ... as its exclusive marketing agent and real estate broker in its Chapter 11 Bankruptcy for the sale of the real property.', KS)
F(k, 'income_restricted_units', '42 of 210 units are restricted to 80% AMI', '168 market-rate and 42 affordable units restricted to 80% AMI for 30 years.', KS)
I(k, 'other', '2026', 'Covered Bridge has retained Keen-Summit Capital Partners LLC (“Keen”), as its exclusive marketing agent and real estate broker in its Chapter 11 Bankruptcy for the sale of the real property.', 'Keen-Summit Capital Partners (sale broker)', KS, 'management_company')
none_rating(k, 'Trulia page: no ratings; Zumper: 404 at the address URL; own site address not found (guessed address did not resolve)')

# 23 Carmen Romano (blocked)
k = '67 sackett point rd|06473'; u, rec = cached_live(k, 'carmen-romano', [('402', 1315)], ' LEAD, NOT VERIFIED: search results describe this as a 55+ community with income limits; no allowed page could be read to confirm.')
C(k, 'elevator', 'yes (Trulia capture 2026-11-15 21:59 UTC)', 'Elevator', u, 'confirmed'); floor_guess(k, '402', '4', 'Unit number only. No page states the floor.', u)
C(k, 'dogs_allowed', 'yes (Trulia capture 21:59 UTC)', rec['pet'], u, 'confirmed'); dog_none(k, 'Dogs: Allowed; Size allowed: Small, large', u)
F(k, 'building_size', '103 units, 3 listed available', 'totalUnitsInBuilding 103; availableRentalUnits 3 (capture 21:59 UTC)', u); F(k, 'parking', 'parking lot (fee not stated)', 'Parking: Parking Lot', u)
F(k, 'age_or_income_restriction', 'not_found on an allowed page (town site failed to load; After55 blocked). Search results call it a 55+ community: treat as an open question', '', 'https://northhaven-ct.gov/government/hearings_committees_authorities_and_task_forces/housing_authority/')
none_item(k, 'one web search (results were listing sites; several describe a 55+ community); Zumper: 404'); none_rating(k, 'Trulia blocked on refetch (cached capture has no ratings); Zumper: 404')

# 24 Scribe
k = '370 w ave|06850'; u = URL[k]; tcu, tc = tfind(TC, 'scribe-370'); SM = 'https://sightmap.com/embed/10pdq1gmw2z'
for unit, stored in (('508', 2426), ('446', 2359)):
    x = [q for q in SCR['units'] if q['unit'] == unit][0]
    L(k, u, unit, 'live' if x['price'] == stored else 'changed', x['price'], x['available_text'], 'yes' if x['price'] == stored else 'no', u, x['seen'], "From the building's own SightMap unit map. Price is for a %s lease; total with required fees $%s (trash $25 + amenity $75). Floor %s. %s" % (x['lease_term'], x['total_min'], x['floor'], 'Studio.' if x['beds'] == 0 else ''))
    C(k, 'floor', '%s (unit %s)' % (x['floor'], unit), "Building's own SightMap unit data: unit %s on floor %s (floors labelled 1 to 7)" % (unit, x['floor']), SM, 'confirmed')
C(k, 'elevator', 'yes (Trulia capture 2026-11-15 21:48 UTC); 7 floors per the unit map', 'Elevator', tcu, 'confirmed')
C(k, 'dogs_allowed', 'yes', 'Dogs: Allowed; Number allowed 2', tcu, 'confirmed')
C(k, 'dog_weight_limit', '50 lb (Trulia capture 2026-11-15 21:48 UTC)', 'Dogs: Weight limit (lbs.) 50; Monthly dog rent $50/mo; One-time fee $600', tcu, 'confirmed')
F(k, 'special_offer', 'New residents can enjoy up to 2-months free! For a limited time on select units and lease terms. Contact our leasing team for details and schedule your tour today.', "Trulia capture. Own site: 'Book your tour today for launch incentives and special offers.' The unit map prices are quoted for a 24-month term; neither page says whether they are gross or net-effective.", tcu)
F(k, 'lease_term_of_listed_price', '24 months', "SightMap lease_term '24 Months' on both stored units", SM)
F(k, 'required_monthly_fees', '$100/mo (trash $25 + amenity $75); electricity separate', "required_fees: Trash Fee 25.00, Amenity Fee 75.00, Electricity 'Varies (utilities)'", SM)
F(k, 'pet_rent', '$50/mo; $600 one-time', 'Monthly dog rent $50/mo; One-time fee $600', tcu); F(k, 'parking', 'garage (fee not stated)', 'Garage, Garage Lot', tcu)
F(k, 'pool', 'outdoor (pool deck with cabanas)', 'an expansive pool deck with cabanas and firepits', u); F(k, 'building_size', '204 residences', 'With 204 beautifully crafted residences', u)
F(k, 'management_company', 'RMS Companies (developer-manager)', 'Scribe | Award Winning Tri-State Real Estate Developer | RMS', u); F(k, 'year_built', 'new (launch phase; year not stated)', 'launch incentives', u)
none_item(k, NEWS + '; Zumper: 404 at the address URL'); none_rating(k, 'Own site: no rating widget; Zumper: 404; Trulia capture: no ratings')

# 25-29 Norwalk, Trulia blocked
k = '19 day st|06854'; u, rec = cached_live(k, 'sono-19-day', [('207', 2500)])
C(k, 'elevator', 'yes (Trulia capture 21:47 UTC)', 'Elevator', u, 'confirmed'); floor_guess(k, '207', '2', "Unit number only; the floor plan is named '07'. No page states the floor.", u)
C(k, 'dogs_allowed', 'yes (Trulia capture)', rec['pet'], u, 'confirmed'); dog_none(k, 'Dogs: Allowed; Size allowed: Small, large', u, ' (large dogs are allowed)')
F(k, 'parking', 'permit lot, $50 per vehicle per month', 'Parking fee ($50 per vehicle); Permitted parking', u); F(k, 'utilities_included', 'garbage, sewer, water', 'Rent Includes: Garbage, Sewer, Water', u)
F(k, 'management_company', 'Alpha5MK (own site footer: A5MKManagement)', 'A5MKManagement Property | 914-484-6964', 'https://www.sono19day.com/'); F(k, 'building_size', '40 units, 1 listed available', 'totalUnitsInBuilding 40; availableRentalUnits 1', u)
none_item(k, NEWS + ' (one search for the two SoNo buildings); own site www.sono19day.com is a script shell; Zumper: 404'); none_rating(k, 'Trulia blocked on refetch (capture has no ratings); Zumper: 404; own site shows no rating')
k = '61 wall st|06850'; u, rec = cached_live(k, 'wall-street-place', [('2-318', 2090), ('2-422', 2210)], " Both units are on plan 'A1-70'; the same plan as 'A1-80' is $2,479, so the -70/-80 suffix looks like an income tier (unverified).")
C(k, 'elevator', 'yes (Trulia capture 21:48 UTC)', 'Elevator', u, 'confirmed')
floor_guess(k, '2-318', '3', "Unit label reads as building 2, unit 318. No page states the floor.", u); floor_guess(k, '2-422', '4', "Unit label reads as building 2, unit 422. No page states the floor.", u)
C(k, 'dogs_allowed', 'yes (Trulia capture)', rec['pet'], u, 'confirmed'); dog_none(k, 'Dogs: Allowed; Number allowed 2; Size allowed: Small, large; Restrictions: Aggressive breeds including Pit Bull, Doberman ...', u, ' (breed list only)')
offer(k, dict(offers=rec['offers']), u, 'Trulia capture 21:48 UTC. A one-time $1,000 credit; not stated whether the listed price is gross or net-effective.')
F(k, 'income_restricted_units', "likely: stored units are on plan 'A1-70' (cheaper than 'A1-80'); News 12 describes a mixed-income building. Not confirmed on a leasing page", 'Wall Street Place will now include 155 apartments at all income levels, as well as new stores at street level. Almost a third of it is paid for with public dollars.', 'https://connecticut.news12.com/eyesore-no-more-after-8-years-construction-resumes-on-norwalk-building')
F(k, 'management_company', 'Richman Property Services', 'Property management company: Richman Property Services', u); F(k, 'year_built', '2026 (brand new)', 'brand new Wall Street Place', u); F(k, 'building_size', '151 units, 9 listed available', 'totalUnitsInBuilding 151; availableRentalUnits 9', u)
I(k, 'other', '2024-10-18', 'Wall Street Place, mired in legal and financing fights for almost a decade, will finally open late next year.', 'News 12', 'https://connecticut.news12.com/eyesore-no-more-after-8-years-construction-resumes-on-norwalk-building', 'building')
none_rating(k, 'Trulia blocked on refetch (capture has no ratings); Zumper: 404; own site address not found. Building is new.')
k = '93 richards ave|06854'; u, rec = cached_live(k, '93-richards', [('508', 2150)])
C(k, 'elevator', 'yes (Trulia capture 21:47 UTC)', 'Elevator', u, 'confirmed'); floor_guess(k, '508', '5', 'Unit number only (unit 112 is also listed). No page states the floor.', u)
C(k, 'dogs_allowed', 'yes (Trulia capture)', rec['pet'], u, 'confirmed'); dog_none(k, 'Dogs: Allowed; Size allowed: Small, large | Restrictions: None', u)
F(k, 'special_offer', rec['offers'][0][0], 'Trulia capture 21:47 UTC. The free month applies to 2-bedrooms only, so not to the stored 1BR; gross or net-effective not stated.', u)
F(k, 'management_company', 'KGP Management', 'Property management company: KGP Management', u); F(k, 'year_built', '1990 (Zumper, which names the building Riverview Apartments)', 'year_built 1990', ZB[k]['url'])
F(k, 'parking', 'garage and surface lot (fee not stated)', 'Garage, Garage Lot, Off Street Parking, Surface Lot', u); F(k, 'building_size', '93 units, 8 listed available', 'totalUnitsInBuilding 93; availableRentalUnits 8', u)
F(k, 'own_site', 'www.93richards.com now serves unrelated spam content: not the building, discarded', '', 'https://www.93richards.com/')
none_item(k, 'one combined web search (returned nothing for this address); ' + zstat(k)); none_rating(k, 'Trulia blocked on refetch (capture has no ratings); ' + zstat(k))
k = '123 water st|06854'; z = ZB[k]; u, rec = cached_live(k, 'harbourside-sono', [('225', 2664)], ' Zumper building page read at %s: 1BR plans from $2,490 (no unit numbers, no dates).' % z['at'])
C(k, 'elevator', 'yes', "Zumper building amenity 'Elevator'", z['url'], 'confirmed'); floor_guess(k, '225', '2', 'Unit number only (units 213 to 611 are listed). No page states the floor.', u)
C(k, 'dogs_allowed', 'yes', 'pet_policy: dog ok | Restrictions: None', z['url'], 'confirmed'); dog_none(k, 'Dogs: Allowed; Size allowed: Small, large; Monthly dog rent $50/mo; One-time fee $500', u)
F(k, 'special_offer', rec['offers'][0][0], 'Trulia capture 21:47 UTC; not stated whether the listed price is gross or net-effective.', u)
F(k, 'pet_rent', '$50 per pet per month; $500 pet fee', 'Pet Rent ($50 per pet); Pet Fee ($500 per pet)', u)
F(k, 'required_monthly_fees', 'amenity fee, common area maintenance, pest control, utility billing fee $5.50 (other amounts not shown)', 'Amenity fee; Monthly Common Area Maintenance; Pest control fee; Utility billing bundle fee ($5.50 each)', u)
F(k, 'parking', 'garage (fee varies)', 'Parking = Varies; Garage Parking', u); F(k, 'pool', 'yes (indoor or outdoor not stated)', 'Swimming Pool', z['url'])
F(k, 'management_company', 'BH Management Services, LLC', 'pm_name', z['url']); F(k, 'building_size', '129 units, 9 listed available', 'totalUnitsInBuilding 129; availableRentalUnits 9', u)
F(k, 'own_site', 'www.harboursidesono.com returned 403; not read', '', 'https://www.harboursidesono.com/')
R(k, 'Google rating shown on Zumper', 4.9, 5, 90, '2024-12-07', 8, 0, 0, 0, '', z['url'])
I(k, 'positive', '2024-04-15', "I’ve been living here since 2021 and have no complaints about how things are handled here.", 'Google review shown on Zumper', z['url'], 'management_company', z['at'])
I(k, 'positive', '2024-11-14', 'Lived here since the building was opened Best location, best views, best amenities , best management and staff', 'Google review shown on Zumper', z['url'], 'building', z['at'])
k = '32 prospect ave|06850'; u, rec = cached_live(k, 'soundview-apartments-32', [('6H', 2145)])
C(k, 'elevator', 'unconfirmed: the Trulia capture does not list an elevator; unit labels on the page are 1C, 2E, 2F and 6H', 'features listed: Laundry Facilities, Controlled access, 24 hour maintenance, Parking Lot (no Elevator)', u, 'unconfirmed')
floor_guess(k, '6H', '6', "Label '6H' reads as floor 6, apartment H (others on the page: 1C, 2E, 2F). No page states the floor or the building height.", u)
C(k, 'dogs_allowed', 'yes (Trulia capture)', rec['pet'], u, 'confirmed'); dog_small(k, 'Cats, small dogs allowed (1 pet max); $500 non-refundable upfront pet fee; $50 per month pet fee; Breed restrictions', u)
F(k, 'pet_rent', '$50/mo; $500 non-refundable fee', '$500 non-refundable upfront pet fee $50 per month pet fee', u); F(k, 'required_monthly_fees', '$40/mo service fee', 'A monthly $40 service fee includes cold water, trash removal, and recycling services.', u)
F(k, 'parking', 'free lot', 'Parking: Free Parking', u); F(k, 'building_size', '69 units, 4 listed available', 'totalUnitsInBuilding 69; availableRentalUnits 4', u)
none_item(k, 'one combined web search (returned nothing for this address); Zumper address URL resolves to a different property (Morningside Gardens, 32 Prospect St): discarded')
none_rating(k, 'Trulia blocked on refetch (capture has no ratings); Zumper address URL is a different property')

def W(name, head, rows):
    with open('data/evidence/%s_batch_12.csv' % name, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)
    print(name, len(rows))
W('live_check', 'addr_key,listing_url,unit,status,price_now,available_now_text,matches_stored,building_site_url,checked_at,notes'.split(','), live)
W('confirm', 'addr_key,fact,value,quote,source_url,status'.split(','), conf)
W('items', 'addr_key,building_name,category,item_date,excerpt,source_site,source_url,about,retrieved_at'.split(','), items)
W('facts', 'addr_key,fact,value,quote,source_url'.split(','), facts)
W('ratings', 'addr_key,building_name,rating_source,rating_value,rating_scale,review_count,as_of_date,reviews_read,reviews_last_6_months,negative_last_6_months,negative_older,serious_issue_tags_last_6_months,source_url'.split(','), ratings)
import collections
print('live', collections.Counter(r[3] for r in live)); print('confirm', collections.Counter(r[5] for r in conf)); print('items', collections.Counter(r[2] for r in items))
miss = [k for k in B if not any(r[0] == k for r in live) or not any(r[0] == k for r in ratings) or not any(r[0] == k for r in items) or not any(r[0] == k for r in conf)]
print('buildings', len({r[0] for r in live}), 'missing', miss)
