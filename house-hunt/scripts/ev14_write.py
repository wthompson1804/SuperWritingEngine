"""Evidence batch 14: build the five output CSVs from the cached pages (no network).

Reads the scratch JSON made by ev14_trulia_parse.py, ev14_al_parse.py and ev14_zumper_reviews.py plus the fetch logs
(rerun ev14_fetch.py and those parsers first if the scratch folder is gone). Hand-read facts are written out below with
the sentence they came from. Outputs: data/evidence/{live_check,confirm,items,facts,ratings}_batch_14.csv.
Re-running overwrites them.
"""
import csv, json, re

S = '/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b14/'
B = list(csv.DictReader(open('data/reference/evidence_batches/batch_14.csv')))
T = json.load(open(S + 'trulia_parsed.json'))
A = json.load(open(S + 'al_parsed.json'))
Z = json.load(open(S + 'zumper_reviews.json'))
AR = json.load(open(S + 'al_reviews.json'))

TS = {}
for fn in ['fetch1.log', 'fetch_addr.log']:
    for l in open(S + fn):
        try:
            u, st, n, p, ts = json.loads(l)
        except Exception:
            continue
        TS[u] = (st, ts)
for l in open(S + 'site1.log'):
    try:
        o = json.loads(l)
    except Exception:
        continue
    if o.get('retrieved_at'):
        TS[o['url']] = (o['status'], o['retrieved_at'])


def ts(u):
    return TS.get(u, ('', '2026-11-15T22:55:00+00:00'))[1]


live, conf, facts, items, ratings = [], [], [], [], []
NAME = {b['addr_key']: (b['building_name'] or b['address']) for b in B}
URL = {b['addr_key']: b['urls'].split(' | ')[0] for b in B}


def L(k, unit, status, price, avail, match, notes, site='', url=None):
    u = url or URL[k]
    live.append(dict(addr_key=k, listing_url=u, unit=unit, status=status, price_now=price, available_now_text=avail,
                     matches_stored=match, building_site_url=site, checked_at=ts(u), notes=notes))


def C(k, fact, value, quote, src, status):
    conf.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=src, status=status))


def F(k, fact, value, quote, src):
    facts.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=src))


def I(k, cat, date, excerpt, site, src, about='building'):
    items.append(dict(addr_key=k, building_name=NAME[k], category=cat, item_date=date, excerpt=excerpt, source_site=site,
                      source_url=src, about=about, retrieved_at=ts(src)))


def R(k, source, value='', scale='', count='', asof='', read=0, r6='', n6='', nold='', tags='', src=''):
    ratings.append(dict(addr_key=k, building_name=NAME[k], rating_source=source, rating_value=value, rating_scale=scale,
                        review_count=count, as_of_date=asof, reviews_read=read, reviews_last_6_months=r6,
                        negative_last_6_months=n6, negative_older=nold, serious_issue_tags_last_6_months=tags, source_url=src))


SMALL = 'Cats, small dogs allowed'
ZA = 'https://www.zumper.com/address/'
TRULIA_NOTE = 'Trulia unit page: carries no ratings'


def trulia_basic(k, unit, stored, extra=''):
    """Live row for a single-unit Trulia listing, from the parsed page."""
    r = T[URL[k]]
    price = int(re.sub(r'\D', '', r['price']))
    av = next((x[3] for x in r['feats'] if x[2] == 'Available'), '')
    dom = next((x[3] for x in r['feats'] if x[2] == 'Days on Market'), '')
    ok = r['status'].get('isActiveForRent')
    L(k, unit, 'live' if ok else 'gone', price, av, 'yes' if price == stored else 'no',
      f"Trulia status For Rent; listed {r['listed'][:10]}; {dom}. " + extra)
    return r


def small_dog(k, src=None):
    src = src or URL[k]
    C(k, 'dogs_allowed', 'yes', SMALL, src, 'confirmed')
    C(k, 'dog_weight_limit', 'no number; size-only "small dogs"', 'Dogs: Allowed; Size allowed: Small', src,
      'unconfirmed')


def none_found(k, looked, news='one web search for the address returned no report about the building'):
    R(k, 'none_found', asof='2026-11-15', src='; '.join(looked))
    I(k, 'none_found', '', 'No tenant review or news item found. Looked at: ' + '; '.join(looked) + '; ' + news + '.',
      'search', URL[k])


# ------------------------------------------------------------------ 1. 434 Scotland Rd #45N, Orange
k = '434 scotland rd|07050'
trulia_basic(k, '45N', 2295, 'Required monthly fee on page: water, sewer and garbage $45/mo. The description is the '
             'marketing text for Be 448 ("Be the First to Live at Be 448!"), the new building at 448 Scotland Rd, so the '
             'address or the text is wrong: ask which building the unit is in.')
C(k, 'elevator', 'unknown', 'Page lists no elevator. Description is Be 448 text; if the unit is really in BE (448 Scotland Rd), '
  'that building lists an elevator', URL[k], 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit label 45N; no floor on the page. My reading: 45N is a unit label, not a 45th floor; it cannot be '
  'turned into a floor', URL[k], 'unconfirmed')
small_dog(k)
F(k, 'required_monthly_fee', '$45/mo water, sewer and garbage', 'Required monthly rent & fees: Base rent $2,295/mo; Water, sewer, and garbage fee $45/mo', URL[k])
F(k, 'one_time_fees', 'deposit $3,450; application $50', 'Security deposit $3,450; Application fee $50', URL[k])
F(k, 'parking', 'off-street, on site; fee not stated', 'Parking: Off Street Parking, On Site', URL[k])
F(k, 'listing_contact', 'Abe rosen (agent; also lists 50 Washington St 11E and 720 Park Ave 91C)', 'listingAgent: Abe rosen', URL[k])
F(k, 'address_mismatch', 'description is for Be 448 (448 Scotland Rd)', 'Be the First to Live at Be 448! Welcome to Be 448, a brand-new residential building', URL[k])
none_found(k, [TRULIA_NOTE, 'Zumper address page: 404'])

# ------------------------------------------------------------------ 2. BE, 448 Scotland Rd
k = '448 scotland rd|07050'
u = URL[k]
JD = 'https://jerseydigs.com/be448-orange-apartments/'
BE_OFFERS = ('"New Construction Lease Up Special 1 Month Free On 14 Month Lease Term"; "Penthouse Specials...TOP FLOOR"; '
             '"Indoor Parking Fee Waived For 6 Months With Same Day Applications"; "Waived Amenity Fee"')
for unit, price, plan in (('P', 2250, '1Bed'), ('F', 2350, '1 Bed with Den')):
    L(k, unit, 'live', price, 'Available Now', 'yes',
      f'Unit {unit} ({plan}) listed at ${price:,}. Page says 87 units in building, 7 available. Offers on page: {BE_OFFERS}. '
      'The page does not say whether the listed price is gross or net of the free month. Trulia page last modified 2026-07-16.')
C(k, 'elevator', 'yes', 'Elevator', u, 'confirmed')
C(k, 'elevator', 'yes', 'Elevator', ZA + '448-scotland-rd-orange-nj-07050-usa', 'confirmed')
C(k, 'floor', 'unknown', 'Units are labelled with letters (Unit P, Unit F); no floor in the unit data. No building height stated on '
  'Trulia or in the Jersey Digs article', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'BE in Orange, NJ allows cats (up to 1) and small dogs (up to 1). Large dogs are not permitted.', u, 'confirmed')
C(k, 'dog_weight_limit', 'no number; size-only "small dogs", 1 dog', 'Dogs: Allowed; Number allowed 1; Size allowed: Small', u, 'unconfirmed')
F(k, 'special_offer', BE_OFFERS, 'Gross or net-effective: not stated on the page', u)
F(k, 'building_size', '87 units (Trulia); 84 units, 9 affordable (Jersey Digs)', 'The complex, known as Be448, includes 84 units and a mix of studios, one-bedroom and two-bedroom apartments. There are also nine units set aside for affordable housing.', JD)
F(k, 'year_built', '2026 (new; broke ground June 2024)', 'The partnership broke ground on the site, which used to be a small iron workshop, in June 2024.', JD)
F(k, 'amenities', 'outdoor pool, sauna, fitness center, rooftop lounge, indoor parking, EV charging', 'Resident amenities at the complex include indoor storage units, a package room, an outdoor pool, a sauna, a fitness center, and a rooftop lounge. The property also includes a golf simulator, indoor parking and electric vehicle charging stations.', JD)
F(k, 'parking', 'indoor garage; fee exists but amount not stated (waived 6 months with same-day application)', 'Indoor Parking Fee Waived For 6 Months With Same Day Applications', u)
F(k, 'amenity_fee', 'exists; amount not stated; currently waived', 'Waived Amenity Fee', u)
F(k, 'developer', 'RISE Architecture with Limestone Builders Group', 'the project is a partnership between the architecture firm and Limestone Builders Group', JD)
I(k, 'other', '2026-07-27', 'The complex, known as Be448, includes 84 units and a mix of studios, one-bedroom and two-bedroom apartments. There are also nine units set aside for affordable housing.', 'Jersey Digs', JD)
R(k, 'none_found', asof='2026-11-15', src='Trulia building page: no ratings; Zumper address page ' + ZA + '448-scotland-rd-orange-nj-07050-usa: no review block; Apartment List /nj/orange/448-scotland-rd: no property page; building opened 2026, so few reviews can exist')

# ------------------------------------------------------------------ 3. 60 W Madison Ave, Dumont
k = '60 w madison ave|07628'
u = URL[k]
L(k, '9A', 'live', 1995, 'Available Now (date on page 2026-11-01)', 'yes', 'Unit 9A, 600 sqft. Building: 22 units, 1 available. Trulia page last modified 2026-10-30.')
C(k, 'elevator', 'unknown', 'No elevator in the feature list. My reading: unlikely. The page describes "a private entrance" and 22 units, '
  'which fits garden apartments, and "9A" reads as building/entry 9, apartment A, not a 9th floor', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit 9A; no floor in the unit data. "With a private entrance, you can come and go as you please" suggests ground-level entry', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', '60 W Madison Ave LLC in Dumont, NJ allows cats and small dogs. Large dogs are not permitted.', u, 'confirmed')
C(k, 'dog_weight_limit', 'no number; size-only "small dogs"', 'Dogs: Allowed; Size allowed: Small', u, 'unconfirmed')
F(k, 'utilities_included', 'garbage, heat, hot water', 'Rent Includes: Garbage, Heat, Hot Water', u)
F(k, 'parking', 'street parking', 'Special Features: Street Parking', u)
F(k, 'deposit', '$2,993', 'Deposit Fee $2,993', u)
F(k, 'building_size', '22 units', 'totalUnitsInBuilding 22; availableRentalUnits 1 (page data)', u)
F(k, 'management_company', '60 W Madison Ave LLC (not verified by Trulia)', 'Property management company: 60 W Madison Ave LLC', u)
none_found(k, ['Trulia building page: no ratings', 'Zumper address page ' + ZA + '60-w-madison-ave-dumont-nj-07628-usa: no Google review block (only Zumper\'s own "expert rating" 8.8, which is not tenant feedback)'])

# ------------------------------------------------------------------ 4. Kensington Place
k = '527 old bridge tpke|08816'
u = URL[k]
KS = 'https://www.kensingtonplacenj.com/'
KOFFER = '2 months free on a 13+ lease and an additional $500 credit if you apply within 24 hours of your tour. Book a tour today!'
al = A[u]['listing']
for unit, stored in (('4222', 2525), ('1322', 2554)):
    x = next(x for fp in al['available_units'] for x in fp['units'] if x['name'] == unit)
    L(k, unit, 'live', x['price'], f"available now (available_on {x['available_on']})", 'yes' if x['price'] == stored else 'no',
      f'Apartment List unit data, refreshed {x["updated_at"][:10]}. Own site banner: "{KOFFER}" Neither page says whether the '
      'listed price is gross or net of the free months; Apartment List shows base_price equal to price.', KS)
C(k, 'elevator', 'yes', 'Elevator access', KS + 'about-kensington-place/', 'confirmed')
C(k, 'floor', 'unknown', 'No floor field in the unit data and the own site lists layouts only. My reading: 4-digit numbers look like '
  'building-floor-unit, so 4222 = building 4, floor 2 and 1322 = building 1, floor 3. Not stated anywhere', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Pet-Friendly with dog park', KS + 'about-kensington-place/', 'confirmed')
C(k, 'dog_weight_limit', 'not stated', 'We accept 2 pets per apartment home. Pet fees and rents are per pet. Please call our leasing office for complete pet policy.', u, 'unconfirmed')
F(k, 'special_offer', KOFFER, 'Gross or net-effective: not stated', KS)
F(k, 'pet_rent', '$100/mo per pet; $500 fee per pet', 'pet_policies.general: rent 100.0, fee 500; "Pet fees and rents are per pet."', u)
F(k, 'parking', 'open lot included in lease; covered garage also listed', 'Open lot: included in lease; Garages available soon', u)
F(k, 'other_fees', 'unspecified extra fees possible', 'Additional fees may apply, such as but not limited to package delivery, trash, water, amenities, etc. Please see a representative for details.', u)
F(k, 'year_built', '2017 (Apartment List); 2018 (Zumper)', 'year_built 2017', u)
F(k, 'building_size', '400 units', 'total_units_count 400', u)
F(k, 'management_company', 'Edgewood Properties', 'For a quarter century, Edgewood Properties dedicated team of agents has provided numerous customers with outstanding properties', KS + 'about-kensington-place/')
F(k, 'doorman', 'concierge', 'Concierge (amenity list)', u)
F(k, 'pool', 'yes; indoor or outdoor not stated', 'Pool (amenity list)', u)
R(k, 'none_found', asof='2026-11-15', src=f'Apartment List {u}: "We are collecting reviews from verified residents"; Zumper building page https://www.zumper.com/apartment-buildings/p286071/kensington-place-east-brunswick-nj: no Google review block; own site {KS}reviews/: hand-picked testimonials with no star score or dates (not counted)')
I(k, 'none_found', '', 'No dated tenant review or news item found. Looked at: Apartment List (collecting reviews); Zumper building page (no review block); own site reviews page (undated, hand-picked testimonials, not recorded); one web search returned only listing pages.', 'search', u)

# ------------------------------------------------------------------ 5. 9 Lake Ave #6A, East Brunswick
k = '9 lake ave|08816'
u = URL[k]
trulia_basic(k, '6A', 2200, 'Description: 953 sq ft condo in the Lake Estates community, 1 bedroom plus den. "Pets require the landlord\'s prior written approval."')
C(k, 'elevator', 'unknown', 'No elevator on the page. My reading: unlikely. The listing calls it a condo in "Lake Estates" (built 1970) with "a '
  'private deck"; that is a garden-condo layout and "6A" is a unit label, not a 6th floor', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit 6A; no floor on the page', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes, with landlord approval', 'Cats, small dogs allowed / "Pets require the landlord\'s prior written approval."', u, 'confirmed')
C(k, 'dog_weight_limit', 'no number; size-only "small dogs"', 'Dogs: Allowed; Size allowed: Small', u, 'unconfirmed')
F(k, 'pet_rent', '$50/mo', 'Optional monthly rent & fees: Pet rent $50/mo', u)
F(k, 'utilities_included', 'all except electricity', 'Rent includes all utilities except electricity, which is paid by the tenant.', u)
F(k, 'parking', 'assigned parking included', 'Assigned parking is included.', u)
F(k, 'pool', 'outdoor community pool', 'Lake Estates features an outdoor community pool', u)
F(k, 'year_built', '1970', 'Year Built 1970', u)
F(k, 'listing_type', 'condo in Lake Estates, rented by owner', '1-Bedroom Condo with Den, Private Deck & In-Unit Laundry', u)
F(k, 'other_requirements', 'renters insurance required; deposit $2,200', 'Renters insurance with liability coverage is required, with proof provided to the landlord within 15 days of move-in.', u)
none_found(k, [TRULIA_NOTE, 'Zumper address page: 404', 'estately.com page for the address: HTTP 403 (not read)'])

# ------------------------------------------------------------------ 6. Allure 258
k = '258 s harrison st|07018'
u = URL[k]
AS = 'https://www.allure258.com/'
AOFFER = 'LIMITED TIME SPECIAL: RECEIVE UP TO 1 MONTH FREE RENT & 1 YEAR OF FREE PARKING (Offer good until November 30, 2026)'
for stored in (2250, 2500):
    L(k, '', 'changed', '', 'no unit or dated availability on page', 'no',
      f'Stored ${stored:,} with no unit number cannot be found. Trulia now shows only a building range $1,850 - $2,900/mo, four '
      'floor plans without prices (Studio, One Bedroom, One Bedroom Plus Study, Two Bedroom) and "0 available units" of 213. '
      f'Offer on Trulia: "{AOFFER}". Own site banner still says "NEW SPECIAL: MOVE IN BEFORE 10/31 TO RECEIVE UP TO 1 MONTH FREE '
      'RENT & 1 YEAR FREE PARKING". Gross or net-effective: not stated. Own site has no unit list. Trulia page last modified '
      '2026-10-29. Call (973) 318-6021 to confirm a unit.', AS)
C(k, 'elevator', 'yes; 17 stories', 'Elevator / "Rising 17 stories, Allure 258 sets a new standard for cutting-edge urban design."', u, 'confirmed')
C(k, 'floor', 'unknown', 'No unit listed', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Allure 258 in East Orange, NJ allows cats (up to 2) and small dogs (up to 2). Large dogs are not permitted.', u, 'confirmed')
C(k, 'dog_weight_limit', 'no number; size-only "small dogs", up to 2', 'Dogs: Allowed; Number allowed 2; Size allowed: Small', u, 'unconfirmed')
F(k, 'special_offer', AOFFER, 'Gross or net-effective: not stated', u)
F(k, 'parking', 'garage, $145 to $250 a month (free for 1 year under the current offer)', 'Garage parking fee: min 145, max 250 (monthly required fees block)', u)
F(k, 'pet_rent', 'exists; amount not stated', 'Pet rent: Contact for details', u)
F(k, 'building_size', '213 units, 17 stories', 'totalUnitsInBuilding 213; "Rising 17 stories"', u)
F(k, 'management_company', 'Blackstone Realty (Blackstone 360; leasing email at b360.us)', 'Property management company: Blackstone Realty / allure258leasing@b360.us', u)
F(k, 'doorman', 'concierge service', 'amenities, including concierge service, secure key fob entry, private garage parking', u)
F(k, 'deposit', '$500 to $4,000', 'Security deposit: min 500, max 4000', u)
none_found(k, ['Trulia building page: no ratings', 'Zumper address page ' + ZA + '258-s-harrison-st-east-orange-nj-07018-usa: a single 2-bedroom listing, no review block', 'Apartment List /nj/east-orange/allure-258: no property page', f'own site {AS}: no rating widget'],
           'one web search: News 12 elevator-outage and lawsuit stories it returned are about other East Orange buildings (The Pavilion, The Castle at 75 Prospect), not this one; search results mentioned critical reviews on Apartments.com, which is off limits and was not read')

# ------------------------------------------------------------------ 7. 50 Washington St #11E, East Orange
k = '50 washington st|07017'
u = URL[k]
ZU = ZA + '50-washington-st-east-orange-nj-07017-usa'
trulia_basic(k, '11E', 2295, 'The description opens "Welcome to 55 Washington Street in East Orange!" while the listing address is 50 Washington St: ask which building.')
C(k, 'elevator', 'yes (from another listing at this address on Zumper)', 'Laundry and parking onsite. Great elevator and appliances for comfort.', ZU, 'confirmed')
C(k, 'elevator', 'not mentioned on the Trulia unit page', 'Trulia feature list has no elevator entry', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit 11E; no floor on the page. My reading: 11E may be floor 11 if this is the elevator building, but the page does not say and the description names a different street number', u, 'unconfirmed')
small_dog(k)
F(k, 'pet_rent', '$50/mo; $250 pet fee', 'Optional monthly rent & fees: Pet rent $50/mo; Optional one-time fees: Pet fee $250', u)
F(k, 'parking', 'off-street on site, $100/mo', 'Parking fee $100/mo', u)
F(k, 'one_time_fees', 'deposit $3,450; application $50', 'Security deposit $3,450; Application fee $50', u)
F(k, 'address_mismatch', 'description says 55 Washington Street', 'Welcome to 55 Washington Street in East Orange!', u)
F(k, 'listing_contact', 'Abe rosen (agent)', 'listingAgent: Abe rosen', u)
none_found(k, [TRULIA_NOTE, f'Zumper address page {ZU}: no review block'],
           'one web search covering the East Orange addresses in this batch found news only about other buildings (a January 2026 fire at 85 Washington St, The Castle, The Pavilion)')

# ------------------------------------------------------------------ 8-11. East Orange single units
for k, unit, stored, extra, fl in (
    ('140 n walnut st|07017', '7A', 1600, 'Description: "Tenants pay utilities, electric, cooking gas ... Section 8 welcome ... Subject to broker fee". 27 days listed.', ''),
    ('111 washington st|07017', '11C', 1450, 'Studio. Description: "Owner pays for all utilities".', ''),
    ('720 park ave|07017', '91C', 2250, 'Description mentions "an additional room that can be used as a home office or storage space".', ''),
    ('57 washington st|07017', '9D', 2395, 'Description is auto-generated filler with no building detail. Deposit and fees "Contact for details". Page modified 2026-10-07.', ''),
):
    u = URL[k]
    trulia_basic(k, unit, stored, extra)
    C(k, 'elevator', 'unknown', 'The page lists no elevator and gives no building height. The earlier "inferred from height" came from the unit label only', u, 'unconfirmed')
    C(k, 'floor', 'unknown', f'Unit {unit}; no floor on the page. My reading: the label alone cannot be turned into a floor' + (' ("91C" is not a 91st floor)' if unit == '91C' else ''), u, 'unconfirmed')
    small_dog(k)
    none_found(k, [TRULIA_NOTE, 'Zumper address page: 404'],
               'one web search covering the East Orange addresses in this batch found news only about other buildings')
F('140 n walnut st|07017', 'broker_fee', 'yes, amount not stated', 'Subject to broker fee', URL['140 n walnut st|07017'])
F('140 n walnut st|07017', 'utilities_included', 'none stated; tenant pays electric and cooking gas', 'Tenants pay utilities, electric, cooking gas, must earn 2.5 x - 3 x the rent amount.', URL['140 n walnut st|07017'])
F('140 n walnut st|07017', 'parking', 'off-street, fee not stated', 'Off-street parking is available.', URL['140 n walnut st|07017'])
F('140 n walnut st|07017', 'one_time_fees', 'deposit $2,400; application $35', 'Security deposit $2,400; Application fee $35', URL['140 n walnut st|07017'])
F('111 washington st|07017', 'utilities_included', 'all', 'Beautiful studio fully renovated with stainless steal appliances and all utilities included  Owner pays for all utilities', URL['111 washington st|07017'])
F('111 washington st|07017', 'parking', 'detached garage on site; fee not stated', 'Parking: Detached Garage, On Site', URL['111 washington st|07017'])
F('111 washington st|07017', 'management_company', 'Freemount Management (listing contact)', 'listingAgent: Freemount Management', URL['111 washington st|07017'])
F('720 park ave|07017', 'parking', 'off-street on site, $150/mo', 'Optional monthly rent & fees: Parking fee $150/mo', URL['720 park ave|07017'])
F('720 park ave|07017', 'pet_fee', '$500 one-time; no pet rent listed', 'Optional one-time fees: Pet fee $500', URL['720 park ave|07017'])
F('720 park ave|07017', 'one_time_fees', 'deposit $3,375; application $50', 'Security deposit $3,375; Application fee $50', URL['720 park ave|07017'])
F('57 washington st|07017', 'parking', 'off-street on site; fee not stated', 'Parking: Off Street Parking, On Site', URL['57 washington st|07017'])

# ------------------------------------------------------------------ 12. 145 Park Ave #6B, East Rutherford
k = '145 park ave|07073'
u = URL[k]
trulia_basic(k, '6B', 1550, 'Description: "NO CLOSET", "No Laundry", "ONLY STREET PARKING", "YARD ACCESS".')
C(k, 'elevator', 'unknown', 'No elevator on the page. My reading: unlikely. "YARD ACCESS", "No Laundry" and "ONLY STREET PARKING" describe a small building, and 6B is a unit label', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit 6B; no floor on the page', u, 'unconfirmed')
small_dog(k)
F(k, 'pet_rent', '$35/mo; $350 non-refundable pet deposit', 'Pets: Non refundable $350 deposit + $35 monthly pet rent', u)
F(k, 'utilities_included', 'heat and hot water', 'HEAT & HOT WATER INCLUDED', u)
F(k, 'parking', 'street only', 'ONLY STREET PARKING', u)
F(k, 'one_time_fees', 'deposit $2,325 (1.5 months); application $50; no broker fee', 'Move in cost: 1st month rent + 1.5 month security deposit   $50 application fee  NO BROKER FEE', u)
none_found(k, [TRULIA_NOTE, 'Zumper address page: 404'])

# ------------------------------------------------------------------ 13. Harbor Pointe, Bayonne
k = '302 constitution ave|07002'
u = URL[k]
al = A[u]['listing']
HOFFER = al['specials'][0]['raw_text']
PET = 'https://www.change.org/p/harbor-pointe-resident-petition-2023'
for unit, stored in (('B9-309', 2223), ('B9-258', 2314)):
    x = next(x for fp in al['available_units'] for x in fp['units'] if x['name'] == unit)
    L(k, unit, 'live', x['price'], f"available_on {x['available_on']}", 'yes' if x['price'] == stored else 'no',
      f'Apartment List unit data, refreshed {x["updated_at"][:10]}. Offer on page: "{HOFFER}" The page does not say whether the '
      'listed price is gross or net of the free months. Own site livingatharborpointe.com: HTTP 403, not read.',
      'https://www.livingatharborpointe.com/')
C(k, 'elevator', 'yes', 'Elevator (community amenity list)', u, 'confirmed')
C(k, 'floor', 'unknown', 'No floor field in the unit data. My reading: B9-309 = building 9, floor 3 and B9-258 = building 9, floor 2. Not stated', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Dogs allowed; 2 pets maximum.', u, 'confirmed')
C(k, 'dog_weight_limit', '50 lb', 'Breed restrictions. Weight limit: 50 lbs.', u, 'confirmed')
F(k, 'special_offer', HOFFER, 'Gross or net-effective: not stated', u)
F(k, 'pet_rent', '$50/mo per pet; $500 fee per pet', '$50/month per pet. / $500 per pet.', u)
F(k, 'amenity_fee', 'exists; amount not stated; waived under the current offer', '2 Months Free & Waived Amenity Fee', u)
F(k, 'parking', 'garage and covered lot; fee exists, amount not stated (2 months free under the offer)', 'PLUS 2 Months of Free Parking!', u)
F(k, 'other_fees', 'trash valet charged; water billed through Conservice (per reviews); deposit $750 based on credit; application $100', 'I feel garbage vallet is not a great idea. I dnt use it yet I’m charged for it', u)
F(k, 'year_built', '2009', 'year_built 2009', u)
F(k, 'building_size', '544 units', 'total_units_count 544', u)
F(k, 'management_company', 'Pontis (took over from Greystar by May 2023); current manager not confirmed', 'Lack of communication around Pontis management transition from Greystar', PET)
F(k, 'pool', 'yes; indoor or outdoor not stated', 'Pool (amenity list)', u)
rv = AR[u]
R(k, 'Apartment List', rv['agg']['ratingValue'], 5, rv['agg']['reviewCount'], '2026-11-15', 3, 0, 0, 2, '', u)
I(k, 'management', '2024-08-15', 'Additionally, water bills were normal for the first two months but then suddenly became unbelievably high, about ten times more. Despite numerous complaints from many residents, management just says they’ll ask Conservice to look into it, but nothing ever changes.', 'Apartment List review', u, 'management_company')
I(k, 'safety_incident', '2024-08-15', 'First, there have been multiple instances of lost mail, and management consistently says they can’t do anything about it.', 'Apartment List review', u)
I(k, 'management', '2024-08-15', 'A management kinda of sucks, no one gets back to you the trash room on the 2nd fl is kept very nasty', 'Apartment List review', u, 'management_company')
I(k, 'car_crime', '2023-05-19', 'Car break-ins on community property and in parking garages', 'Change.org tenant petition', PET, 'garage_or_lot')
I(k, 'safety_incident', '2023-05-19', 'Broken, unlocked, or otherwise unsecured entrances to buildings along with broken card scanners / Mail/packages being stolen', 'Change.org tenant petition', PET)
I(k, 'car_crime', '2023-05-19', 'Parking behind B3 across from dog park was previously available for tenants, within last 2 months has been heavily ticketed with no warning from Pontis', 'Change.org tenant petition', PET, 'garage_or_lot')
I(k, 'noise', '2023-05-19', 'Frequency of false fire alarms (aka. nuisance alarms) / Multiple red fire alarms in each apartment that amplify sound at a decibel level of 120 and flashing lights.', 'Change.org tenant petition', PET)

# ------------------------------------------------------------------ 14. The Sterling, Fort Lee
k = '2055 center ave|07024'
u = URL[k]
L(k, '', 'live', 2500, 'no unit or date on page', 'yes',
  'Floor-plan level only and stale: the page shows "$2,500/mo", one plan ("Studios", no price or date of its own) and "0 available '
  'units" of 128. Trulia page last modified 2026-05-15, six months ago. No unit, floor or date can be checked. Call (908) 650-1771.')
C(k, 'elevator', 'yes', 'Elevator', u, 'confirmed')
C(k, 'floor', 'unknown', 'No unit listed', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'The Sterling in Fort Lee, NJ allows cats (up to 1) and small dogs (up to 1). Large dogs are not permitted.', u, 'confirmed')
C(k, 'dog_weight_limit', 'no number; size-only "small dogs", 1 dog', 'Dogs: Allowed; Number allowed 1; Size allowed: Small', u, 'unconfirmed')
F(k, 'parking', 'lot and attached garage, $100 to $250 a month', "Parking is NOT including with the unit it's an additional cost ranging from $100 - $250 based on where you park.", u)
F(k, 'pet_rent', 'exists; amount not stated', 'Pet rent: Contact for details', u)
F(k, 'building_size', '128 units', 'totalUnitsInBuilding 128; availableRentalUnits 0', u)
F(k, 'pool', 'yes; indoor or outdoor not stated', 'Pool', u)
F(k, 'laundry', 'shared laundry facilities', 'Laundry Facilities', u)
F(k, 'deposit', '$1,500 to $4,000', 'Security deposit: min 1500, max 4000', u)
none_found(k, ['Trulia building page: no ratings', 'Zumper address page: 404', 'Apartment List /nj/fort-lee/the-sterling: no property page', 're-nj.com article on the sale of the building: disallowed by robots.txt for us, not read'])

# ------------------------------------------------------------------ 15. Harrison Somerset
k = '575 easton ave|08904'
u = URL[k]
OX = 'https://www.oxfordrealtygroup.com/communities/harrison-somerset/'
XOFFER = 'Specials: 1 Month Free with One Year Lease; $500.00 Security Deposit with Approved Credit'
for plan, price in (('B, H, K, R - Small', 1835), ('G - Small', 1700)):
    L(k, plan + '-1', 'live', price, 'available (no date)', 'yes',
      f'Floor-plan level: Apartment List shows plan "{plan}" at ${price:,}, "available"; the manager\'s own page lists "{plan} '
      f'${price:,}+". No unit number, floor or date.' + (' G - Small is a studio.' if plan.startswith('G') else '') +
      f' Own site: "{XOFFER}". Gross or net-effective: not stated. Apartment List record last updated 2026-11-13.', OX)
C(k, 'elevator', 'yes', 'Elevator (Features list)', OX, 'confirmed')
C(k, 'floor', 'unknown', 'Listings are floor plans named by letter (B, H, K, R); no unit or floor', OX, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Pet Friendly / Fees, Recurring: Dog $40', OX, 'confirmed')
C(k, 'dog_weight_limit', 'not stated', 'Neither the community page nor the rental policy page gives a weight limit; Apartment List shows limit "2" pets and no restrictions text', OX, 'unconfirmed')
F(k, 'special_offer', XOFFER, 'Gross or net-effective: not stated', OX)
F(k, 'pet_rent', 'dog $40/mo; cat $350 one-time (Apartment List: rent 40, fee 350)', 'Fees: Application $50; Cat $350; Dog $40', OX)
F(k, 'parking', 'on-site parking; indoor garage and reserved off-street spaces available; fee not stated', 'Indoor parking to keep your vehicle out of the elements. / Reserved Off-Street Parking Available / Garage Parking Available', OX)
F(k, 'pool', 'outdoor', 'Outdoor pool that is perfect for swimming and lounging in the sun.', OX)
F(k, 'laundry', 'on-site laundry facility', 'On-Site Laundry Facility', OX)
F(k, 'year_built', '1974', 'year_built 1974', u)
F(k, 'building_size', '316 units', 'total_units_count 316', u)
F(k, 'management_company', 'Oxford Realty Group on the own site; Apartment List names AION Management. Which is current, and since when, not found', 'Oxford Realty Group | Harrison Somerset / pmc_display_name: AION Management', OX)
F(k, 'application_fee', '$50', 'You must pay a $50 non-refundable credit report and processing fee.', 'https://www.oxfordrealtygroup.com/rental-policy/')
rv = AR[u]
R(k, 'Apartment List', rv['agg']['ratingValue'], 5, rv['agg']['reviewCount'], '2026-11-15', 1, 0, 0, 0, '', u)
I(k, 'positive', '2025-04-25', 'I love this Apartment complex.Management is very responsive.The Lake view is to die for', 'Apartment List review', u)

# ------------------------------------------------------------------ 16. The Grove Somerset
k = '500 bristol blvd|08873'
u = URL[k]
GS = 'https://www.thegrovesomerset.com/'
ZG = ZA + '500-bristol-blvd-somerset-nj-08873-usa'
JG = 'https://jerseydigs.com/truamerica-buys-the-grove-somerset/'
GOFFER = 'Apply By 11/30 and Receive 50% Off Base Rent for Your First 4 Months Plus 6 Months of Complimentary Parking. Other Costs and Fees Excluded. Minimum Lease Terms and Restrictions Apply. Contact for Details. ** Offer available on select units for qualified applicants.'
al = A[u]['listing']
for unit, stored in (('1116', 2627), ('2205', 2677)):
    x = next(x for fp in al['available_units'] for x in fp['units'] if x['name'] == unit)
    L(k, unit, 'live', x['price'], f"available_on {x['available_on']}", 'yes' if x['price'] == stored else 'no',
      f'Apartment List unit data, refreshed {x["updated_at"][:10]}. Own site offer: "{GOFFER}" The offer is on base rent; the '
      'pages do not say whether the listed price is gross or net of it. Apartment List carries a fee note "$86" and the line '
      '"Total monthly leasing prices include base rent, all mandatory monthly fees"; the own-site fee guide is a Canva page '
      'that could not be read. Ask for the fee sheet.', GS)
C(k, 'elevator', 'only in some buildings', 'Elevator access in select buildings', GS + 'apartments/nj/somerset/amenities', 'unconfirmed')
C(k, 'floor', 'unknown', 'No floor field in the unit data. My reading: 4-digit numbers look like building-floor-unit, so 1116 = building 1, '
  'FLOOR 1 (ground: would fail the gate) and 2205 = building 2, floor 2. Not stated; and whether buildings 1 and 2 have elevators is not stated either', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'A maximum of two pets is allowed per apartment.', GS + 'apartments/nj/somerset/amenities', 'confirmed')
C(k, 'dog_weight_limit', 'exists but not published', 'Contact our leasing team to confirm breed and weight restrictions.', GS + 'apartments/nj/somerset/amenities', 'unconfirmed')
F(k, 'special_offer', GOFFER, 'Applies to base rent for the first 4 months; gross or net-effective listing price: not stated', GS + 'apartments/nj/somerset/floor-plans')
F(k, 'parking', 'fee exists, amount not stated (6 months free under the offer); garage listed', '6 Months of Complimentary Parking', GS)
F(k, 'other_fees', 'mandatory monthly fees exist; "$86" appears as a calculator note on Apartment List without a label', 'Total monthly leasing prices include base rent, all mandatory monthly fees and any user-selected optional fees. Excludes variable or usage-based fees and required charges due at or prior to move-in or at move-out.', u)
F(k, 'pet_screening', 'PetScreening.com profile required per pet', 'A PetScreening.com profile and agreement for each pet is required.', GS + 'apartments/nj/somerset/amenities')
F(k, 'year_built', '2012 (Apartment List); "13-year-old" in July 2026 (Jersey Digs)', 'The 13-year-old Grove Somerset apartment community.', JG)
F(k, 'building_size', '384 units', 'The Grove Somerset, a 384-unit apartment community in Somerset', JG)
F(k, 'ownership_change', 'sold June 2026 by a Harbor Group affiliate to TruAmerica Multifamily, which plans to renovate every unit over time. Apartment List still names Harbor Group Management; current manager not confirmed', 'that was remedied in June when it bought The Grove Somerset, a 384-unit apartment community in Somerset. / The seller was an affiliate of Harbor International Group.', JG)
z = Z[ZG]
R(k, 'Google rating shown on Zumper', z['rating'], z['scale'], z['count'], z['pulled'], len(z['reviews']), 0, 0, 0, '', ZG)
R(k, 'Apartment List', src=u + ' ("We are collecting reviews": no rating)', asof='2026-11-15')
I(k, 'other', '2026-07-08', 'TruAmerica Multifamily believed something was missing geographically in its portfolio, but that was remedied in June when it bought The Grove Somerset, a 384-unit apartment community in Somerset.', 'Jersey Digs', JG, 'management_company')
I(k, 'other', '2026-07-08', 'Based in Los Angeles , TruAmerica would not disclose the purchase price or how much it intends to spend on renovating every unit in the complex over time.', 'Jersey Digs', JG, 'management_company')
for d, t in (('2024-11-08', 'The property is well kept and my building feels very updated. Noise insulation is great, I honestly can’t hear anybody around me.'),
             ('2024-09-09', 'Peaceful and beautiful place to live. Jessica does a great job of managing and resolving tenant issues/complains.'),
             ('2024-09-23', 'The community is an oasis- so beautiful well maintained and peaceful.')):
    I(k, 'positive', d, t, 'Google review shown on Zumper (Zumper shows only the highest rated, and these predate the June 2026 sale; weak evidence)', ZG)

# ------------------------------------------------------------------ 17. 5 Linden St #6F, Hackensack
k = '5 linden st|07601'
u = URL[k]
trulia_basic(k, '6F', 2390, 'Tenant pays utilities. Assigned parking space in rear lot.')
C(k, 'elevator', 'yes', 'The building offers a welcoming lobby and elevator access.', u, 'confirmed')
C(k, 'floor', '6', 'Welcome to this bright and spacious 1 bedroom, 1 bathroom apartment located on the 6th floor in the heart of Hackensack!', u, 'confirmed')
small_dog(k)
F(k, 'parking', 'assigned space in rear lot, included', 'along with assigned parking space in rear lot', u)
F(k, 'utilities_included', 'none', 'Tenant is responsible for utilities.', u)
F(k, 'one_time_fees', 'deposit $3,585', 'Security deposit $3,585', u)
F(k, 'listing_contact', 'Keller Williams Village Square Realty (broker listing; ask about a broker fee)', 'broker: Keller Williams Village Square Realty', u)
none_found(k, [TRULIA_NOTE, 'Zumper address page ' + ZA + '5-linden-st-hackensack-nj-07601-usa: no review block'])

# ------------------------------------------------------------------ 18. 5 Elm Ave #7A, Hackensack
k = '5 elm ave|07601'
u = URL[k]
trulia_basic(k, '7A', 2000, 'Heat and water included; parking $75/mo.')
C(k, 'elevator', 'unknown', 'No elevator on the page. My reading: unlikely. The listing sells "the private entrance", which fits a garden building, and 7A is a unit label', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit 7A; no floor on the page. "Enjoy the private entrance" suggests ground-level entry', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Pets Ok maximum 40lbs allowed', u, 'confirmed')
C(k, 'dog_weight_limit', '40 lb', 'Pets Ok maximum 40lbs allowed', u, 'confirmed')
F(k, 'parking', 'attached garage on site, $75/mo', 'Parking is available for just $75 per month.', u)
F(k, 'utilities_included', 'heat and water', 'Heat and water are included.', u)
F(k, 'laundry', 'shared, in building', 'available shared laundromat in building', u)
F(k, 'one_time_fees', 'deposit $3,000 (1.5 months); no broker fee', '**No Broker fee**', u)
none_found(k, [TRULIA_NOTE, 'Zumper address page: 404'])

# ------------------------------------------------------------------ 19. 51 1st St, Hackensack
k = '51 1st st|07601'
u = URL[k]
L(k, '8A', 'live', 1865, 'Available Now (date on page 2026-11-15)', 'yes', 'Unit 8A. Building: 8 units, 1 available. No broker fee. Trulia page last modified 2026-11-11.')
C(k, 'elevator', 'unknown', 'No elevator in the feature list. My reading: unlikely. The page gives 8 units in the whole building, so "8A" is a unit label, not an 8th floor', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit 8A; no floor in the unit data', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', '51 First St Assoc LLC in Hackensack, NJ allows cats and small dogs. Large dogs are not permitted.', u, 'confirmed')
C(k, 'dog_weight_limit', 'no number; size-only "small dogs"', 'Dogs: Allowed; Size allowed: Small', u, 'unconfirmed')
F(k, 'building_size', '8 units', 'totalUnitsInBuilding 8; availableRentalUnits 1 (page data)', u)
F(k, 'parking', 'off-street; fee not stated', 'Special Features: Off Street Parking', u)
F(k, 'laundry', 'on-site common laundry', 'The building offers on-site common laundry', u)
F(k, 'deposit', '$2,798', 'Deposit Fee $2,798', u)
F(k, 'management_company', '51 First St Assoc LLC (not verified by Trulia)', 'Property management company: 51 First St Assoc LLC', u)
none_found(k, ['Trulia building page: no ratings', 'Zumper address page ' + ZA + '51-1st-st-hackensack-nj-07601-usa: no Google review block (only Zumper\'s own "expert rating" 7.9)'])

# ------------------------------------------------------------------ 20. 324 Monroe St, Hoboken
k = '324 monroe st|07030'
u = URL[k]
trulia_basic(k, '6AA', 2450, 'Page note: "Decreased by $100 (4%) on Nov 12, 2026." The description calls it "324 Monroe Street #6" and says "This apartment is a true 2 bedroom"; Zumper lists the same unit as a 2-bedroom at $2,450. Bedroom count needs checking.')
C(k, 'elevator', 'unknown', 'No elevator on the page. My reading: unlikely. The text says "324 Monroe Street #6" with "Laundry share in the basement", which fits a small walk-up; 6AA is not a 6th floor', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit "#6" / 6AA; no floor on the page', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Pets are fine, $50 a month.', u, 'confirmed')
C(k, 'dog_weight_limit', 'no number; Trulia field says size "Small", description says "Pets are fine"', 'Dogs: Allowed; Size allowed: Small / "Pets are fine, $50 a month."', u, 'unconfirmed')
F(k, 'pet_rent', '$50/mo', 'Pets are fine, $50 a month.', u)
F(k, 'utilities_included', 'none', 'Tenants pay for Wifi/Cable, Gas and Electric.', u)
F(k, 'one_time_fees', '1.5 months security; application $40; no broker fee', 'No brokers fee! / Checks up front are 1st month rent and 1.5 months Security.', u)
F(k, 'laundry', 'shared, basement', 'Laundry share in the basement.', u)
F(k, 'bedrooms', 'listed as 1 bedroom, described as 2', 'This apartment is a true 2 bedroom so enjoy the extra space.', u)
none_found(k, [TRULIA_NOTE, 'Zumper address page ' + ZA + '324-monroe-st-hoboken-nj-07030-usa: unit listing, no review block'])

# ------------------------------------------------------------------ 21. 280 Luis M Marin Blvd #15F
k = '280 luis m marin blvd|07302'
u = URL[k]
trulia_basic(k, '15F', 2350, 'Studio; all utilities included; one month broker fee; parking +$200; gym extra.')
C(k, 'elevator', 'unknown', 'Not stated on the page or on the Zumper page for 280. My reading: likely yes. The listing mentions "24/7 Concierge" and the twin tower at 270 (Metropolis) lists an elevator on Zumper', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit 15F; no floor on the page. My reading: 15th floor is plausible in a concierge tower, but not stated', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Pet is allowed.', u, 'confirmed')
C(k, 'dog_weight_limit', 'no number; Trulia field says size "Small"', 'Dogs: Allowed; Size allowed: Small', u, 'unconfirmed')
F(k, 'utilities_included', 'heat, air conditioning, hot water, electric, gas', 'All Utilities included. ( Heat, Air conditioning, Hot water, Electric, and gas..24/7 Concierge.', u)
F(k, 'parking', '$200/mo extra', "Add'tl 200 for parking.", u)
F(k, 'broker_fee', 'one month', "Req: one month rent, one and half months security, and one month broker's fee.", u)
F(k, 'other_fees', 'gym costs extra, amount not stated', 'ADD AMT OF MONEY FOR THE GYM.', u)
F(k, 'doorman', '24/7 concierge', '24/7 Concierge', u)
F(k, 'listing_contact', 'HOME STAR REALTY (broker)', 'broker: HOME STAR REALTY', u)
none_found(k, [TRULIA_NOTE, 'Zumper address page ' + ZA + '280-luis-m-marin-blvd-jersey-city-nj-07302-usa: unit listing, no review block'],
           'one web search for Metropolis Towers returned only stories about a different complex (Portside Towers)')

# ------------------------------------------------------------------ 22. 270 Luis M Marin Blvd #16F  (Trulia blocked)
k = '270 luis m marin blvd|07302'
u = URL[k]
ZU = ZA + '270-luis-m-marin-blvd-jersey-city-nj-07302-usa'
L(k, '16F', 'blocked', '', '', '', 'Trulia returned HTTP 403 at 22:48 UTC and again at 22:56 UTC (after 21 good fetches); not retried further. Unit 16F is not on the Zumper address page (it shows 2 units, 0 available). Not verified today.')
C(k, 'elevator', 'yes', 'Elevator (amenity on the Zumper page for 270 Luis M Marin Blvd, "the Metropolis")', ZU, 'confirmed')
C(k, 'floor', 'unknown', 'Listing page blocked. My reading: 16F is plausibly the 16th floor of the tower, not stated', u, 'unconfirmed')
C(k, 'dogs_allowed', 'unconfirmed', 'Listing page blocked today; stored value (dogs yes) not re-read', u, 'unconfirmed')
C(k, 'dog_weight_limit', 'unknown', 'Listing page blocked today', u, 'unconfirmed')
F(k, 'building_name', 'Metropolis (Metropolis Towers)', 'Beautiful junior 1BR/1BA home at the Metropolis downtown Jersey City right by Grove St PATH.', ZU)
F(k, 'utilities_included', 'all utilities, per another listing in the building', 'Rent includes all utilities.', ZU)
none_found(k, ['Trulia unit page: HTTP 403', f'Zumper address page {ZU}: no review block'],
           'one web search for Metropolis Towers returned only stories about a different complex (Portside Towers)')

# ------------------------------------------------------------------ 23. 328 Pacific (Lafayette House)  (Trulia blocked)
k = '328 pacific ave|07304'
u = URL[k]
LH = 'https://www.lafayettehousejc.com/'
L(k, '705', 'blocked', '', '', '', 'Trulia returned HTTP 403; not retried further. The building\'s own site (Lafayette House) has no unit list, its "Availability" link goes to a Modern Spaces page with no unit table, and the Zumper address page shows only 2-bedrooms ($2,900 to $4,900). Unit 705 not verified today. Leasing: 201-661-5035.', LH)
C(k, 'elevator', 'yes', 'The courtyard by the first floor elevator bank is another nice option for respite.', LH + 'amenities', 'confirmed')
C(k, 'floor', 'unknown', 'Listing page blocked; own site gives no unit list or floor count. My reading: 705 would normally mean floor 7, but the building is a converted church with 42 units and duplex penthouses, so do not assume', LH, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Dogs Ok (Zumper address page; "Contact for more information on pet policy.")', ZA + '328-pacific-ave-jersey-city-nj-07304-usa', 'confirmed')
C(k, 'dog_weight_limit', 'not stated', 'Contact for more information on pet policy.', ZA + '328-pacific-ave-jersey-city-nj-07304-usa', 'unconfirmed')
F(k, 'building_name', 'Lafayette House (converted 1885 church), 42 units', 'The rich history of the former church, which dates back to 1885, has been preserved and re-imagined ... The 42 one- and two-bedroom units', LH)
F(k, 'doorman', 'virtual doorman', 'Select amenities include a virtual doorman, a delightful rooftop deck and comfortable resident’s lounge', LH + 'amenities')
F(k, 'management_company', 'Modern Spaces NJ (leasing)', 'Leasing@ModernSpacesNJ.com 201-661-5035', LH)
F(k, 'amenities', 'roof deck, lounge, courtyard, fitness center', 'There’s also a fully equipped fitness center', LH + 'amenities')
none_found(k, ['Trulia building page: HTTP 403', 'Zumper address page ' + ZA + '328-pacific-ave-jersey-city-nj-07304-usa: no review block', 'Apartment List /nj/jersey-city/328-pacific: no property page', f'own site {LH}: no rating widget'])

# ------------------------------------------------------------------ 24. Pier Village
k = '50 chelsea ave|07740'
u = URL[k]
al = A[u]['listing']
POFFER = al['specials'][0]['raw_text']
ZP = 'https://www.zumper.com/apartment-buildings/p176600/pier-village-i-long-branch-city-long-branch-nj'
for unit, stored in (('4-408', 2371), ('1-347', 2716)):
    x = next(x for fp in al['available_units'] for x in fp['units'] if x['name'] == unit)
    L(k, unit, 'live' if x['price'] == stored else 'changed', x['price'], f"available_on {x['available_on']}", 'yes' if x['price'] == stored else 'no',
      f'Stored ${stored:,}; now ${x["price"]:,} (down ${stored - x["price"]}). Unit data shows total_price {x["total_price"]} with required_fees 0. '
      f'Offer on page (also on Zumper): "{POFFER}" The page does not say whether the listed price is gross or net of the free month. '
      'Own site wm-piervillage.com: HTTP 403, not read. Apartment List record last updated 2026-11-14.', 'https://www.wm-piervillage.com/')
C(k, 'elevator', 'yes', 'bike racks, package receiving, elevator access, and both garage and covered parking', u, 'confirmed')
C(k, 'floor', 'unknown', 'No floor field in the unit data. My reading: 4-408 = building 4, floor 4 and 1-347 = building 1, floor 3. Not stated', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Pier Village is a pet-friendly luxury oceanfront apartment community', u, 'confirmed')
C(k, 'dog_weight_limit', 'not stated (breed restrictions only)', 'Certain Breed Restrictions.  Ask our leasing staff.', u, 'unconfirmed')
F(k, 'special_offer', POFFER, 'Gross or net-effective: not stated', u)
F(k, 'pet_rent', '$50/mo; $500 fee; 2 pets', 'pet_policies.general: rent 50.0, fee 500.0, limit 2', u)
F(k, 'parking', 'garage and covered parking; fee not stated', 'both garage and covered parking', u)
F(k, 'pool', 'yes; indoor or outdoor not stated', 'Community amenities include swimming pool, on-site Gold\'s Gym with exclusive resident discounts, dog park', u)
F(k, 'year_built', '2005', 'year_built 2005', u)
F(k, 'building_size', '493 units', 'total_units_count 493', u)
F(k, 'management_company', 'Kushner Companies (own site on the Westminster Management domain wm-piervillage.com); start date not found', 'pmc_display_name: Kushner Companies', u)
F(k, 'doorman', 'concierge', 'Concierge (amenity list)', u)
rv = AR[u]
R(k, 'Apartment List', rv['agg']['ratingValue'], 5, rv['agg']['reviewCount'], '2026-11-15', 0, '', '', '', '', u + ' (one rating, no review text in the page data)')
I(k, 'none_found', '', f'No tenant review text or news item found. Looked at: Apartment List (one 5-star rating, no text); Zumper building page {ZP} (no Google review block); one web search returned only listing and trade pages. Search results mentioned 29 reviews on Apartments.com, which is off limits.', 'search', u)

# ------------------------------------------------------------------ 25. 99 Pine St #8A, Montclair  (Trulia blocked)
k = '99 pine st|07042'
u = URL[k]
L(k, '8A', 'blocked', '', '', '', 'Trulia returned HTTP 403; not retried further. No Zumper page for the address (404). Not verified today.')
C(k, 'elevator', 'unknown', 'Listing page blocked; no other page found for the address', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Listing page blocked. Unit 8A alone cannot be turned into a floor', u, 'unconfirmed')
C(k, 'dogs_allowed', 'unconfirmed', 'Listing page blocked today; stored value not re-read', u, 'unconfirmed')
C(k, 'dog_weight_limit', 'unknown', 'Listing page blocked today', u, 'unconfirmed')
F(k, 'management_company', 'Maybrook Management LLC (from the batch file; not re-read)', 'manager column of batch_14.csv', u)
none_found(k, ['Trulia unit page: HTTP 403', 'Zumper address page: 404'], 'one web search naming the address returned nothing about it')

# ------------------------------------------------------------------ 26. Carriage Club at Mt Arlington
k = '1 hillside dr|07856'
u = URL[k]
CC = 'https://carriageclub.net/'
al = A[u]['listing']
for unit, stored in (('B208', 2038), ('B305', 2018)):
    x = next(x for fp in al['available_units'] for x in fp['units'] if x['name'] == unit)
    L(k, unit, 'live', x['price'], f"available_on {x['available_on']}", 'yes' if x['price'] == stored else 'no',
      f'Apartment List unit data, refreshed {x["updated_at"][:10]}. AGE-RESTRICTED: the building is a 55+ senior community '
      '("designed exclusively for those aged 55+"). No special offer on the page.', CC)
C(k, 'elevator', 'yes', 'Elevator', CC + 'amenities/', 'confirmed')
C(k, 'floor', 'unknown', 'No floor field in the unit data. My reading: B208 = wing B, floor 2 and B305 = wing B, floor 3 (the site mentions "A&B Wings – EACH Floor"). Not stated', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Maximum of two pets per apartment', CC + 'amenities/', 'confirmed')
C(k, 'dog_weight_limit', '40 lb', 'Pets permitted up to 40 pounds (per pet) at full grown adult weight (breed restrictions apply)', CC + 'amenities/', 'confirmed')
F(k, 'age_restriction', '55+ only', 'A 55+ independent senior community, offering a vibrant lifestyle in the beautiful hills of western Morris County.', CC)
F(k, 'pet_rent', '$50/mo per pet; $275 one-time per pet', 'One time pet deposit fee of $275* per pet (non-refundable) / $50.00* (non-refundable) pet rent; per pet, per month', CC + 'amenities/')
F(k, 'parking', 'outdoor reserved parking', 'The community has outdoor, reserved parking around the community w/designated parking for visitors.', CC + 'amenities/')
F(k, 'pool', 'indoor heated', '55 + Community, Washer and Dryer in Each Unit, Indoor Heated Swimming Pool, State of the Art Fitness Center', ZA + '1-hillside-dr-mount-arlington-nj-07856-usa')
F(k, 'year_built', '2002', 'year_built 2002', u)
F(k, 'building_size', '105 units', 'total_units_count 105', u)
F(k, 'management_company', 'SELA Realty Investments (on-site property manager named on the site); takeover date not confirmed from an allowed page', 'SELA Realty Investments is a family-owned Real Estate investment and management company operating in New Jersey and Florida.', CC)
R(k, 'none_found', asof='2026-11-15', src=f'Apartment List {u}: "We are collecting reviews"; Zumper address page {ZA}1-hillside-dr-mount-arlington-nj-07856-usa: no review block; own site {CC}: no rating widget')
I(k, 'none_found', '', 'No tenant review or news item found. Looked at: Apartment List (collecting reviews); Zumper address page (no review block); own site; one web search returned only sale and financing stories.', 'search', u)

# ------------------------------------------------------------------ 27. Northampton Crossing
k = '64 regency dr|08060'
u = URL[k]
NS = 'https://www.northamptoncrossing.com/'
al = A[u]['listing']
x = next(x for fp in al['available_units'] for x in fp['units'] if fp['bed'] == 1)
L(k, x['name'], 'live', x['price'], f"available_on {x['available_on']}", 'yes' if x['price'] == 1605 else 'no',
  'Apartment List shows one 1-bedroom row (635 sqft) labelled unit "1", which reads as a placeholder for the floor plan, not a real '
  'unit number. Special on page: "5% Military Discount!" only. Move-in fee $295, application $50. Record last updated 2026-11-14.', NS)
C(k, 'elevator', 'listed on Apartment List; not on the own site', 'Apartment List amenity list: "Elevator". The own site\'s feature list (fitness center, on-site laundry, business center, EV charging) has no elevator. My reading: doubtful for a 1-bedroom garden community with townhomes', u, 'unconfirmed')
C(k, 'floor', 'unknown', 'Unit label "1" is a placeholder; no floor stated. If it does mean apartment 1 it could be ground floor', u, 'unconfirmed')
C(k, 'dogs_allowed', 'yes', 'Pet Friendly', NS + 'amenities', 'confirmed')
C(k, 'dog_weight_limit', 'not stated', 'Apartment List: limit 1 pet, rent 50.0; "Call for Breed Restrictions"', u, 'unconfirmed')
F(k, 'pet_rent', '$50/mo; 1 pet', 'pet_policies.general: rent 50.0, limit 1', u)
F(k, 'utilities_included', 'heating and cooling', 'Complimentary Heating and Cooling included', NS + 'amenities')
F(k, 'one_time_fees', 'move-in fee $295; application $50', 'move_in_fees_text 295.0; application_fee_text 50.0', u)
F(k, 'laundry', 'on-site (apartments); in-unit only in townhomes', 'On-Site Laundry', NS + 'amenities')
F(k, 'building_size', '163 units', 'total_units_count 163', u)
F(k, 'special_offer', '5% Military Discount!', 'Not a general offer', u)
R(k, 'none_found', asof='2026-11-15', src=f'Apartment List {u}: "We are collecting reviews"; Zumper address page: 404; own site {NS}: no rating widget')
I(k, 'none_found', '', 'No tenant review or news item found. Looked at: Apartment List (collecting reviews); Zumper (no page); own site; one web search returned only listing pages.', 'search', u)

# ------------------------------------------------------------------ 28. Village Square
k = '100 first montgomery dr|08060'
u = URL[k]
ZV = 'https://www.zumper.com/apartment-buildings/p9774/village-square-mount-holly-nj'
al = A[u]['listing']
for unit, stored in (('7D', 1565), ('45D', 1660)):
    fp, x = next((fp, x) for fp in al['available_units'] for x in fp['units'] if x['name'] == unit)
    L(k, unit, 'live', x['price'], f"available now (available_on {x['available_on']})", 'yes' if x['price'] == stored else 'no',
      f'Apartment List unit data under floor plan "{fp["name"]}", unit refreshed {x["updated_at"][:10]} (property record itself last '
      'updated 2026-09-21). No special offer on the page. Own site villagesquarefmg.com did not respond.', 'http://www.villagesquarefmg.com/')
C(k, 'elevator', 'none listed', 'Apartment List amenity list has no elevator; floor plans are "1BR 1st Floor" and "1BR 2nd Floor"; built 1946. My reading: two-storey garden buildings without elevators, so these second-floor units are walk-ups (one flight)', u, 'unconfirmed')
C(k, 'floor', '2', 'Both units sit under the building\'s own floor plan name "1BR 2nd Floor"', u, 'confirmed')
C(k, 'dogs_allowed', 'yes', 'Dogs allowed; limit 2', u, 'confirmed')
C(k, 'dog_weight_limit', '65 lb', "Up to 65lbs fully grown. Breed restrictions are Pit Bulls, Rottweiler's, German Sheppard's, Doberman Pinchers and any mixed breed including the previously mentioned.", u, 'confirmed')
F(k, 'pet_rent', 'dog $25/mo; $250 fee', 'dogs: rent $25, fee $250, limit 2', u)
F(k, 'utilities_included', 'sewer, water', 'utilities_included_text: Sewer, Water', u)
F(k, 'parking', 'parking lot; fee not stated', 'Parking Lot', u)
F(k, 'one_time_fees', 'deposit $99 or one month; application $50 per applicant', '$99.00 or one month\'s rent / $50 per applicant', u)
F(k, 'year_built', '1946', 'year_built 1946', u)
F(k, 'building_size', '205 units', 'total_units_count 205', u)
F(k, 'management_company', 'First Montgomery Group; start date not found (a 2022 review already names its staff)', 'pmc_display_name: First Montgomery Group', u)
F(k, 'pool', 'yes; indoor or outdoor not stated', 'They have nice activity space like the fire pits, a small playground, a dog park, and a pool.', ZV)
F(k, 'other_address', 'Zumper lists the complex at 533 Garden St, Mount Holly', 'Village Square Apartments - 533 Garden St Mount Holly NJ', ZV)
z = Z[ZV]
R(k, 'Google rating shown on Zumper', z['rating'], z['scale'], z['count'], z['pulled'], len(z['reviews']), 0, 0, 0, '', ZV)
R(k, 'Apartment List', src=u + ' ("We are collecting reviews": no rating)', asof='2026-11-15')
for d, t in (('2024-12-23', 'A wonderful place to live in. The staff is very knowledgeable and quick to respond to any issues.'),
             ('2024-04-03', "I've needed help from maintenance a few times while I've lived here, and they're always responsive and friendly."),
             ('2023-07-12', 'Anytime I need help with a maintenance issue they come right away. The grounds are keep clean, you have a wash, dryer, and dishwasher in each unit.')):
    I(k, 'positive', d, t, 'Google review shown on Zumper (Zumper shows only the highest rated; the overall score is 3.5, so lower reviews exist but cannot be read; weak evidence)', ZV)

# ------------------------------------------------------------------ 29. 479 Roseville Ave #34A, Newark  (Trulia blocked)
k = '479 roseville ave|07107'
u = URL[k]
ZR = ZA + '479-roseville-ave-newark-nj-07107-usa'
L(k, '34A', 'blocked', '', '', '', 'Trulia returned HTTP 403; not retried further. The Zumper address page shows a different unit (#6, 2 bedrooms) and not 34A. Not verified today.')
C(k, 'elevator', 'unknown', 'Listing page blocked; the Zumper page for the address lists no elevator', ZR, 'unconfirmed')
C(k, 'floor', 'unknown', 'Listing page blocked. Unit 34A alone cannot be turned into a floor', u, 'unconfirmed')
C(k, 'dogs_allowed', 'conflict: stored Trulia value was dogs yes; Zumper listing for unit #6 at this address says no pets', 'Hardwood Floor No Pets Allowed', ZR, 'contradicts')
C(k, 'dog_weight_limit', 'unknown', 'Listing page blocked today', u, 'unconfirmed')
F(k, 'listing_contact', 'Rovazo Realty Group (from the batch file; not re-read)', 'manager column of batch_14.csv', u)
none_found(k, ['Trulia unit page: HTTP 403', f'Zumper address page {ZR}: no review block'], 'one web search naming the address returned nothing about it')

# ------------------------------------------------------------------ write
OUT = {
    'live_check': (live, ['addr_key', 'listing_url', 'unit', 'status', 'price_now', 'available_now_text', 'matches_stored', 'building_site_url', 'checked_at', 'notes']),
    'confirm': (conf, ['addr_key', 'fact', 'value', 'quote', 'source_url', 'status']),
    'items': (items, ['addr_key', 'building_name', 'category', 'item_date', 'excerpt', 'source_site', 'source_url', 'about', 'retrieved_at']),
    'facts': (facts, ['addr_key', 'fact', 'value', 'quote', 'source_url']),
    'ratings': (ratings, ['addr_key', 'building_name', 'rating_source', 'rating_value', 'rating_scale', 'review_count', 'as_of_date', 'reviews_read', 'reviews_last_6_months', 'negative_last_6_months', 'negative_older', 'serious_issue_tags_last_6_months', 'source_url']),
}
for name, (rows, cols) in OUT.items():
    with open(f'data/evidence/{name}_batch_14.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(name, len(rows))
keys = {b['addr_key'] for b in B}
for name, (rows, _) in OUT.items():
    miss = keys - {r['addr_key'] for r in rows}
    if miss and name != 'facts':
        print('MISSING in', name, miss)
from collections import Counter
print('live', Counter(r['status'] for r in live))
print('confirm', Counter(r['status'] for r in conf))
print('items', Counter(r['category'] for r in items))
print('ratings', Counter('none' if r['rating_source'] == 'none_found' else 'rated' if r['rating_value'] != '' else 'no_score' for r in ratings))
