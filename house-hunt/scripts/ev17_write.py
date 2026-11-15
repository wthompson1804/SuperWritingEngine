"""Evidence batch 17: write the five CSVs from what was read (no network). Excerpts are checked against the cached pages.
Inputs: scratch b17/trulia_parsed.json (refetched Trulia pages), b17/trulia_cached7.json (the 7 pages Trulia blocked on
refetch, read from the 19:32-19:54 UTC harvest cache), raw/evidence_b17/_igloo.json, cached own-site / review / news pages."""
import csv, json, re, sys, html as H
sys.path.insert(0, 'scripts')
from ev17_text import text
S = '/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b17/'
E = 'data/evidence/'
B = list(csv.DictReader(open('data/reference/evidence_batches/batch_17.csv')))
NAME = {r['addr_key']: r['building_name'] or r['address'] for r in B}
TP = json.load(open(S + 'trulia_parsed.json'))
C7 = json.load(open(S + 'trulia_cached7.json'))
IG = json.load(open('raw/evidence_b17/_igloo.json'))
IDX = {}
for l in open('raw/evidence_b17/_index.jsonl'):
    j = json.loads(l)
    if j.get('status') == 200: IDX[j['url']] = j
def page(u):
    j = IDX[u]; raw = open(j['path'], encoding='utf-8', errors='replace').read()
    return raw, j['retrieved_at']
NOW = '2026-11-15'
T = lambda k: [u for u in TP if k in u][0]
live, conf, items, facts, ratings = [], [], [], [], []
def L(k, url, unit, status, price, avail, match, site, at, notes): live.append([k, url, unit, status, price, avail, match, site, at, notes])
def Cf(k, fact, value, quote, src, status): conf.append([k, fact, value, quote, src, status])
def F(k, fact, value, quote, src): facts.append([k, fact, value, quote, src])
def R(k, src, val, cnt, asof, read, last6, neg6, negold, tags, url): ratings.append([k, NAME[k], src, val, 5 if val != '' else '', cnt, asof, read, last6, neg6, negold, tags, url])
_chk = {}
def It(k, cat, date, excerpt, site, url, about, at, corpus):
    c = re.sub(r'\s+', ' ', corpus)
    assert re.sub(r'\s+', ' ', excerpt) in c, ('excerpt not in source', k, excerpt[:60])
    items.append([k, NAME[k], cat, date, excerpt, site, url, about, at])
def NF(k, where): items.append([k, NAME[k], 'none_found', '', where, '', '', '', NOW + 'T23:00:00+00:00'])

# ---------- Trulia unit pages refetched OK (single-unit listings) ----------
OI = 'https://www.openigloo.com/building/nyc/'
def trulia_unit(k, key, unit, stored, elevator, floor, floor_status, floor_quote, extra_notes='', dog_note=''):
    u = T(key); r = TP[u]; price = int(re.sub(r'\D', '', r['price']))
    av = [f[3] for f in r['feats'] if f[2] == 'Available']; dom = [f[3] for f in r['feats'] if f[2] == 'Days on Market']
    fee = ((r.get('fees') or {}).get('disclaimer') or {}).get('text', '').replace('\n', ' ').strip()
    notes = f"Trulia unit page, listed {str(r['listed'])[:10]}, {dom[0] if dom else ''}. {re.sub(r' +', ' ', fee)} {extra_notes}".strip()
    L(k, u, unit, 'live', price, 'Available ' + (av[0] if av else '?'), 'yes' if price == stored else 'no', '', r['ts'], notes)
    pol = [f[3] for f in r['feats'] if 'allowed' in f[3].lower()]
    Cf(k, 'dogs_allowed', 'yes', pol[0] if pol else 'Dogs: Allowed', u, 'confirmed')
    Cf(k, 'dog_weight_limit', 'size only: "Small" (no number)', 'Dogs: Allowed; Size allowed: Small' + (('. ' + dog_note) if dog_note else ''), u, 'unconfirmed')
    if elevator: Cf(k, 'elevator', 'yes', elevator, u, 'confirmed')
    else: Cf(k, 'elevator', 'not stated on the listing', 'no elevator line in the listing features or description', u, 'unconfirmed')
    Cf(k, 'floor', floor, floor_quote, u, floor_status)
    prov = (r.get('provider') or {}).get('fullTextSummary') or []
    if prov: F(k, 'listing_broker', prov[0].replace('Listing by: ', ''), prov[0], u)
    return u, r

k = '1825 ocean ave|11230'
u, r = trulia_unit(k, '1825-ocean', '9G', 2539, 'Elevator', '9 (reading of unit number 9G)', 'unconfirmed',
    'Page gives no floor. Unit number 9G reads as floor 9, but city data lists the building at 8 floors, so the top level may be numbered 9 or the count differs. Ask.')
F(k, 'rent_regulation', 'advertised as rent stabilized', 'Brand New Modern Luxury Building Full Amenities - RENT STABALIZED', u)
F(k, 'parking', 'private parking available; fee not stated', 'Private parking available', u)
F(k, 'price_basis', 'base rent; no offer shown', 'Price shown is base rent. Additional costs and fees may apply.', u)
k = '80 richmond hill rd|10314'
u, r = trulia_unit(k, '80-richmond-hill', '7O', 2400, '', '7 (reading of unit number 7O)', 'unconfirmed', 'Page gives no floor. 7O reads as floor 7 of a 7-floor building (city data).', dog_note='Description: up to 2 pets total.')
F(k, 'pet_rent', '$50/mo (listed as optional monthly fee)', 'Optional monthly rent & fees: Pet rent $50/mo', u)
F(k, 'pet_fee_one_time', '$300', 'Optional one-time fees: Pet fee $300', u)
F(k, 'gym_fee', '$15/mo optional', 'Optional monthly rent & fees: Gym fee $15/mo', u)
F(k, 'pool', 'yes (indoor or outdoor not stated)', 'Pool', u)
F(k, 'utilities_included', 'heat, hot water, cooking gas', 'Heat, hot water and cooking gas are included. Tenant is responsible for their own electric and any cable services they want.', u)
F(k, 'screening', 'credit check and 4 months of income verification', 'Tenant screening includes credit check and verification of 4 months of income.', u)
k = '5550 netherland ave|10471'
u, r = trulia_unit(k, '5550-netherland', '3A', 2090, 'Elevator', '3 (reading of unit number 3A)', 'unconfirmed', 'Page gives no floor; 3A reads as floor 3.', extra_notes='Photos "can be of a similar unit in the building".')
F(k, 'parking', 'parking garage in building; fee not stated', 'Building Amenities:* -Laundry -Elevator -Parking Garage -Super On-Site', u)
k = '500 kappock st|10463'
u, r = trulia_unit(k, '500-kappock', '6J', 2095, 'Elevator', '6 (reading of unit number 6J)', 'unconfirmed', 'Page gives no floor; 6J reads as floor 6 of a 7-floor building (city data).', extra_notes="Description gives the exact rent as $2,094.72.")
F(k, 'parking', 'garage, optional, $300/mo', 'Garage Parking (Optional): $300. per month', u)
F(k, 'application_fee', '$20', 'Application fee: $20 per application First Month\'s Rent $2,094.72. Security deposit: $2,094.72.', u)
k = '4499 henry hudson pkwy w|10471'
u, r = trulia_unit(k, '4499-henry', 'E6', 2600, 'Laundry, Elevator in building', '6 (reading of unit number E6)', 'unconfirmed',
    'Page gives no floor. E6 may mean line E on floor 6 (building has 6 floors in city data) or apartment 6 in wing E. Ask.', extra_notes='Price was raised $100 on Nov 9, 2026; stored price is the new one. On the market 31 days.')
F(k, 'price_change', '+$100 (4%) on 2026-11-09', 'Increased by $100 (4%) on Nov 9, 2026.', u)
F(k, 'parking', 'parking "pending availability"; fee not stated', 'Parking (pending availability)', u)
k = '101-19 rockaway beach blvd|11694'
u, r = trulia_unit(k, '101-19-rockaway', '3G', 2595, 'Elevator', '3 (reading of unit number 3G)', 'unconfirmed', 'Page gives no floor; 3G reads as floor 3 (city data lists 3 floors, so this would be the top floor).',
    extra_notes='Structured field says available now, but the description says "Available 12/1". Price cut $55 on Nov 11, 2026. No broker fee.')
F(k, 'availability_conflict', 'field: now; description: 12/1', 'NO FEE! Available 12/1', u)
F(k, 'price_change', '-$55 (2%) on 2026-11-11', 'Decreased by $55 (2%) on Nov 11, 2026.', u)
F(k, 'gym', '24/7 gym', '24/7 Gym Facility', u)
k = '260 beach 81st st|11693'
u, r = trulia_unit(k, '260-beach-81st', '4', 2400, '', 'unknown (unit is listed as "4")', 'unconfirmed',
    'Page gives no floor. Unit "4" may be apartment 4, not floor 4; the description mentions a private terrace with ocean views. Ask.', dog_note='Description: Pets upon approval.')
conf[-4][3] = 'Small dogs allowed'; conf[-3][3] = 'Dogs: Allowed; Size allowed: Small. Description: "Pets upon approval." (approval is case by case)'
F(k, 'parking', 'dedicated spot included, off street, on site', 'featuring a private terrace with ocean views and a dedicated parking spot', u)
F(k, 'utilities_included', 'heat and water', 'Heat and water included! Pets upon approval. Management application fees apply.', u)
F(k, 'listing_type', 'condo unit rented by owner through broker', 'Rockaway Beach 1 Bedroom Condo Rental!', u)
k = '7914 rockaway beach blvd|11693'
u, r = trulia_unit(k, '7914-rockaway', '2F', 2825, 'Its an Elevator Building with a Live in Super', '2 (reading of unit number 2F)', 'unconfirmed', 'Page gives no floor; 2F reads as floor 2.', dog_note='Description: Pets Considered Only on a Case by case basis.')
F(k, 'dog_policy_condition', 'case by case', '1 Year Lease - Pets Considered Only on a Case by case basis.', u)
F(k, 'utilities_included', 'heat and hot water', 'Heat and hotwater is included.', u)
F(k, 'listing_type', 'condo unit (The Nautilus)', 'A Beautiful 1 Bedroom Condo for Rent at The Nautilus', u)
k = '2781 ocean ave|11229'
u, r = trulia_unit(k, '2781-ocean', '6E', 1700, "It's an elevator building, has live-in super, laundry room, cameras on all floors.", '6 (top floor)', 'confirmed', "it's on the top 6th floor.")
F(k, 'utilities_included', 'water, gas, heating', 'Water, gas and heating are included.', u)
F(k, 'listing_type', 'condo building (city data); listed by owner, 2 days on market', 'One year lease with possibility to extend.', u)
k = '5 stuyvesant pl|10301'
u, r = trulia_unit(k, '5-stuyvesant', '4F', 2750, 'Elevator', '4 (reading of unit number 4F)', 'unconfirmed', 'Page gives no floor; 4F reads as floor 4.', extra_notes='On the market 31 days.')
F(k, 'building_name', 'listing calls it the "Waters View community"', 'Charming 1Bd 1Bath apartment in the highly sought-after Waters View community.', u)
F(k, 'gym', 'fitness center', 'Fitness Center', u)
k = '157 white plains rd|10591'
u, r = trulia_unit(k, '157-white-plains', '44A', 1800, '', 'unknown (unit 44A)', 'unconfirmed',
    'Page gives no floor. 44A cannot be floor 44; in a garden complex it is probably building or entrance 44, apartment A, which may be ground level. Ask.',
    extra_notes='Photos "are not exact to unit". Listing is in Sleepy Hollow Gardens, a garden apartment complex (see evidence items).')
conf[-2][3] = 'No elevator line on the listing, and the complex\'s own page (https://samsonmanagement.com/sleepy-hollow-gardens/) lists garages, pool, laundry and terraces but no elevator. Garden complex: probably no elevator.'
F(k, 'building_name', 'Sleepy Hollow Gardens', 'Large one bedroom, one bathroom apartment located in Sleepy Hollow Gardens.', u)
F(k, 'utilities_included', 'heat and hot water', 'Heat and hot water included.', u)
F(k, 'management_company', 'Samson Management (complex page); rental contact ERA Insite Realty', 'News 12 contacted Samson Management and is waiting to hear back.', 'https://westchester.news12.com/2026/04/21/residents-in-sleepy-hollow-terraced-garden-apartments-voice-concerns-over-mold-vermin-more/6cUNTJCiMvAXay7n5Lpoud')
F(k, 'parking', 'indoor garages and outdoor parking; fee not stated', 'Indoor and outdoor parking is available.', 'https://samsonmanagement.com/sleepy-hollow-gardens/')
F(k, 'pool', 'outdoor', 'Outdoor Pool', 'https://samsonmanagement.com/sleepy-hollow-gardens/')
k = '949 w end ave|10025'
u, r = trulia_unit(k, '949-w-end', 'D', 2795, 'This pet friendly elevator building features a video intercom system', 'top floor (number not stated; city data lists 12 floors)', 'confirmed', 'NO FEE! This sunny top-floor studio has a galley kitchen and large bathroom.')
F(k, 'management_company', 'Metropolitan Equities (sole leasing agent for the landlord)', 'Metropolitan Equities LLC is the sole agent authorized by the landlord of the apartment to offer the apartment for rent.', u)
F(k, 'broker_fee', 'none', 'NO FEE!', u)
k = '241 w 101st st|10025'
u, r = trulia_unit(k, '241-w-101st', '2S', 2750, '', '2 (reading of unit number 2S)', 'unconfirmed', 'Page gives no floor; 2S reads as floor 2. The description never names the building, the floor or an elevator.',
    extra_notes='Generic description with no building details. City lot data lists the owner of 241 West 101 Street as NYC Housing Authority: check that this market-rate listing is at this address.')
F(k, 'listing_warning', 'description is generic; city lot data names NYC Housing Authority as owner of this address', 'Welcome to a beautifully designed studio apartment that offers the perfect blend of modern comfort, smart functionality, and everyday convenience.', u)
k = '610 w 196th st|10040'
u, r = trulia_unit(k, '610-w-196th', '4d', 2495, 'Gorgeous one bed , live in super and elevator', '4 (reading of unit number 4D)', 'unconfirmed', 'Page gives no floor; 4D reads as floor 4.')

# ---------- Trulia building pages refetched OK ----------
k = '260 w st|10549'; u = T('gardens-at-mt-kisco'); r = TP[u]
L(k, u, '8A', 'live', 2495, 'Available Now', 'yes', '', r['ts'],
  'Unit 8A is still shown at $2,495, Available Now (also 4B at $2,395). BUT the description opens "WAITLIST at The Gardens at Mt Kisco; please call for other locations" and the Trulia page was last modified 2026-08-11. This is a co-op: board approval and interview required. Treat as unverified; call.')
Cf(k, 'elevator', 'not stated', 'Features list has no elevator. Description: "Laundry in basement, building C." (several buildings; page data says 8 units in this one)', u, 'unconfirmed')
Cf(k, 'floor', 'unknown (unit 8A)', 'Page gives no floor. With 8 units in the building per page data, 8A is probably a building or apartment number, not floor 8. Ask.', u, 'unconfirmed')
Cf(k, 'dogs_allowed', 'yes', 'Cats, small dogs allowed', u, 'confirmed')
Cf(k, 'dog_weight_limit', 'size only: "Small" (no number); 1 dog', 'Dogs: Allowed; Number allowed: 1; Size allowed: Small', u, 'unconfirmed')
F(k, 'listing_warning', 'waitlist; co-op approval and interview', 'WAITLIST at The Gardens at Mt Kisco; please call for other locations. Coop approval/interview.', u)
F(k, 'required_fees', '$20 per occupant, non-refundable; tenant pays electric', 'Tenant pays electric. 20.00 per occupant fee. Non-refundable.', u)
F(k, 'parking', 'lot parking; garage extra when available, separate lease', 'Lot parking. Garage for an extra fee when available, separate lease.', u)
F(k, 'management_company', 'Fortune Financial (verified on Trulia)', 'Property management company: Fortune Financial', u)
F(k, 'building_size', '8 units, 2 listed available', 'totalUnitsInBuilding 8; availableRentalUnits 2 (page data)', u)
F(k, 'security_deposit', '$2,595', 'Deposit Fee: $2,595', u)
k = '80 w grand st|10552'; u = T('fleetwood-holdings'); r = TP[u]
L(k, u, 'D5', 'live', 1942, 'Available Now', 'yes', '', r['ts'],
  'Unit D5 is still shown at $1,942, Available Now, BUT the page description is "No Units currently available" and the Trulia page was last modified 2024-07-24 (16 months ago). Probably a dead listing; call before relying on it.')
Cf(k, 'elevator', 'yes', 'Elevator', u, 'confirmed')
Cf(k, 'floor', 'unknown (unit D5)', 'Page gives no floor. D5 may be floor 5 in line D, or apartment 5 in wing D. Ask.', u, 'unconfirmed')
Cf(k, 'dogs_allowed', 'yes', 'Cats, small dogs allowed', u, 'confirmed')
Cf(k, 'dog_weight_limit', 'size only: "Small" (no number)', 'Dogs: Allowed; Size allowed: Small', u, 'unconfirmed')
F(k, 'listing_warning', 'stale page that contradicts itself', 'No Units currently available', u)
F(k, 'management_company', 'CT Metro Holdings (verified on Trulia)', 'Property management company: CT Metro Holdings', u)
F(k, 'building_size', '38 units, 1 listed available', 'totalUnitsInBuilding 38; availableRentalUnits 1 (page data)', u)
k = '38 rider ave|11772'; u = T('patchogue-village'); r = TP[u]
for unit, pr in (('T526', 2265), ('T220', 2540)):
    L(k, u, unit, 'live', pr, 'Available Now', 'yes', '', r['ts'], f'Trulia building page (last modified 2026-11-05): Unit {unit}, plan A1 - 1X1, 700 sqft. Third unit T121 at $2,540. Own site (eaglerockproperties.com property page) could not be reached.')
Cf(k, 'elevator', 'yes; 5 floors', 'a five-story apartment community offering 65 one- and two-bedroom apartment homes ... the community features elevator access', u, 'confirmed')
Cf(k, 'floor', 'T526: 5; T220: 2 (reading of unit numbers)', 'Page gives no floor. In a five-story building T526 reads as floor 5 and T220 as floor 2. T121 would be floor 1.', u, 'unconfirmed')
Cf(k, 'dogs_allowed', 'yes', 'Cats, small dogs, large dogs allowed', u, 'confirmed')
Cf(k, 'dog_weight_limit', 'no number stated; small and large dogs allowed', 'Dogs: Allowed; Size allowed: Small, large. Special features: "Pet Friendly Some Restrictions Apply"', u, 'unconfirmed')
Cf(k, 'dog_weight_limit', 'company policy lists restricted breeds and a two-pet maximum, no weight limit', 'Most Eagle Rock communities allow cats and dogs and accept a maximum of two pets per home.', 'https://www.eaglerockproperties.com/pet-policy', 'unconfirmed')
F(k, 'pet_rent', '$50/mo per dog', 'Dogs: Monthly dog rent $50/mo', u)
F(k, 'pet_fee_one_time', '$250 per dog', 'Dog Fee ($250 each)', u)
F(k, 'optional_fees', 'renters insurance compliance fee $20.75 or renters insurance $14.50 (listed as optional monthly)', 'Renters insurance compliance fee ($20.75); Renters insurance fee ($14.50)', u)
F(k, 'application_fee', '$20 per adult', 'Application fee ($20 per adult applicant)', u)
F(k, 'parking', 'open surface lot on site; fee not stated', 'Open Lot Parking ... Surface Lot', u)
F(k, 'management_company', 'Eagle Rock Management (verified on Trulia)', 'Property management company: Eagle Rock Management', u)
F(k, 'building_size', '65 units, 5 floors, 3 listed available', 'a five-story apartment community offering 65 one- and two-bedroom apartment homes', u)
F(k, 'renovation', 'renovations announced', 'Newly Renovated Apartment Homes Coming Soon ... Renovated Leasing Office Lobby Coming Soon', u)
k = '99 waverly ave|11772'; u = T('heatherwood-house'); r = TP[u]; HW = 'https://www.heatherwood.com/our-properties/heatherwood-house-at-patchogue'
L(k, u, '10G', 'live', 2428, 'Available Now', 'yes', HW, r['ts'],
  'Trulia building page (last modified 2026-11-15): Unit 10G, The Junior Executive Imperial, 552 sqft, $2,428. Own site agrees at plan level: "The Junior Executive Imperial ... 2 Available Units $2,428+/month". Offer: $500 security deposit (no rent concession).')
Cf(k, 'elevator', 'not stated', 'Neither the Trulia page nor the building\'s own amenities page lists an elevator. The pet policy line "no dogs on 2nd floor apts" suggests two-level garden buildings. Probably no elevator.', u, 'unconfirmed')
Cf(k, 'floor', 'unknown (unit 10G)', 'Page gives no floor. 10G is probably building 10, apartment G. Ask which level.', u, 'unconfirmed')
Cf(k, 'dogs_allowed', 'yes, but one policy line bars dogs from second-floor apartments', 'One Time Non-Refundable/Non-Transferable Fee $400/pet. $25/month rent for cats, $50 for dogs. 30lbs max weight. Max 2 pets, no dogs on 2nd floor apts.', u, 'confirmed')
Cf(k, 'dog_weight_limit', '30', 'Dogs: Allowed; 1 pet max; 30 lbs max weight; $75 monthly pet fee', u, 'confirmed')
F(k, 'dog_policy_conflict', 'same page gives two versions: 1 pet max and $75/mo, or max 2 pets and $50/mo; both say 30 lb', 'Dogs: 1 pet max; 30 lbs max weight; $75 monthly pet fee | Pet Policy: ... $50 for dogs. 30lbs max weight. Max 2 pets, no dogs on 2nd floor apts.', u)
F(k, 'pet_rent', '$75/mo per dog (structured field); $50 in the free-text policy', 'Dog rent ($75 per dog)', u)
F(k, 'pet_fee_one_time', '$400 per pet', 'One Time Non-Refundable/Non-Transferable Fee $400/pet.', u)
F(k, 'special_offer', '$500 security deposit; listed price is not said to be net-effective', 'Limited-Time Leasing OfferLease now and secure your new apartment with just a $500 Security Deposit. Restrictions apply.', u)
F(k, 'special_offer_own_site', 'own site tags plans "Rent Special" without terms', 'Rent Special *Restrictions May Apply', HW)
F(k, 'pool', 'yes (indoor or outdoor not stated)', 'Pool', u)
F(k, 'management_company', 'Heatherwood (owner-manager; own site)', 'Property management company: Heatherwood', u)
F(k, 'building_size', '176 units, 13 listed available', 'totalUnitsInBuilding 176; availableRentalUnits 13 (page data)', u)

# ---------- Apartment List: Reserve at Lakeside ----------
k = '7 lakeside rd|12550'; u = 'https://www.apartmentlist.com/ny/newburgh/reserve-at-lakeside-senior-housing-55'; at = IDX[u]['retrieved_at']
OFFER = '1 MONTH OFF YOUR FIRST MONTH OF FULL RENT WITH MOVE-IN BY 11/15/26! WAIVED APPLICATION FEE IF YOU APPLY WITHIN 24 HOURS OF YOUR TOUR! REDUCED SECURITY DEPOSIT OF $500 WITH APPROVED CREDIT!'
for unit, pr, plan, on in (('1304', 2261, 'Oak', '2026-11-11'), ('1101', 2277, 'Maple', '2026-11-06')):
    L(k, u, unit, 'live', pr, f'available now (available_on {on})', 'yes', 'https://www.reserveatlakeside.com/', at,
      f'Apartment List page data (availability last checked 2026-11-15): unit {unit}, plan {plan}, 700 sqft, base price = total price = ${pr:,}, 12-month lease. AGE-RESTRICTED 55+ community. Offer requires move-in by 11/15/26 (today), so it has effectively lapsed. Own site returned HTTP 403 (bot wall).')
Cf(k, 'elevator', 'yes', 'Elevator (community amenity)', u, 'confirmed')
Cf(k, 'floor', '1304: 3; 1101: 1 (reading of unit numbers)', 'Page gives no floor. If numbers are building-floor-unit, 1304 is floor 3 and 1101 is floor 1, i.e. ground floor. Ask.', u, 'unconfirmed')
Cf(k, 'dogs_allowed', 'yes', 'allowed_pets: cats, dogs; limit 2; restrictions: Breed Restrictions may apply. Call for details.', u, 'confirmed')
Cf(k, 'dog_weight_limit', 'no weight limit stated', 'Breed Restrictions may apply. Call for details.', u, 'unconfirmed')
F(k, 'age_restriction', '55+ senior housing', 'Reserve at Lakeside is an upscale 55+ community that offers style, function, and sophistication.', u)
F(k, 'special_offer', 'one month off, move-in by 11/15/26; page prices show base = total, no net-effective label', OFFER, u)
F(k, 'pet_rent', '$75/mo', 'pet policy: rent 75.0; fee 500.0; limit 2', u)
F(k, 'pet_fee_one_time', '$500', 'pet policy: rent 75.0; fee 500.0; limit 2', u)
F(k, 'parking', 'surface lot; fee not stated', 'parking category: surface_lot', u)
F(k, 'pool', 'yes (indoor or outdoor not stated)', 'Pool (community amenity)', u)
F(k, 'year_built', '2020', 'year_built 2020; total_units_count 102', u)
F(k, 'income_requirement', '3x rent', 'Must have 3x the rent in total household income (before taxes)', u)
F(k, 'management_change', 'reviewers mention new management in 2026', 'We are excited about the new management changes and hope to see more activities and an updated community calendar of events.', 'https://modernmsg.com/reserve-at-lakeside')

# ---------- Trulia blocked on refetch (HTTP 403 from request 20 on): facts from the same day's harvest cache ----------
BL = 'Trulia returned HTTP 403 (bot wall) on the refetch at {t} UTC (one Trulia URL retried at 22:53 UTC was also 403, so I stopped); not rechecked. Last successful read {c} UTC today: {x}'
def blocked(k, unit, stored, t, x, site='', status='blocked', price='', avail='', match=''):
    c = C7[k]; L(k, c['url'], unit, status, price, avail, match, site, t, BL.format(t=t[11:16], c=c['ts'][:16].replace('T', ' '), x=x))
    return c['url'] + ' (read ' + c['ts'][:16] + 'Z; refetch blocked)', c
def cached_gate(k, src, elev_q, floor_v, floor_q, dog_q='Dogs: Allowed; Size allowed: Small', dog_v='size only: "Small" (no number)', allowed_q='Cats, small dogs allowed'):
    Cf(k, 'elevator', 'yes', elev_q, src, 'confirmed'); Cf(k, 'floor', floor_v, floor_q, src, 'unconfirmed')
    Cf(k, 'dogs_allowed', 'yes', allowed_q, src, 'confirmed'); Cf(k, 'dog_weight_limit', dog_v, dog_q, src, 'unconfirmed')
ts7 = {l.split('"')[1]: json.loads(l)[4] for l in open(S + 'fetch1.log') if ' 403, ' in l}
tt = lambda k: ts7[C7[k]['url']]
k = '1224 saint nicholas ave|10032'
src, c = blocked(k, '6A', 2495, tt(k), 'unit 6A at $2,495, available Dec 1 (description: "Available Dec. 1st"), listed 2026-11-13.')
cached_gate(k, src, "Located in a building with an ELEVATOR and LAUNDRY", '6 (reading of unit number 6A)', 'Page gives no floor; 6A reads as floor 6 (top of 6 in city data).', allowed_q='Dogs: Allowed; Cats: Allowed')
F(k, 'listing_broker', 'City Wide Apartments, 757-913-5019', 'Listing by: City Wide Apartments, 757-913-5019', src)
k = '545 edgecombe ave|10032'
src, c = blocked(k, '6D', 2700, tt(k), 'unit 6D at $2,700, available now, listed 2026-10-29 (17 days on Trulia). Photos are "of a similar unit in the same building".')
cached_gate(k, src, '-Live-in Super -Elevator Building', '6 (reading of unit number 6D)', 'Page gives no floor; 6D reads as floor 6 (top of 6 in city data).', allowed_q='Dogs: Allowed; Cats: Allowed')
F(k, 'listing_broker', 'Bohemia Realty Group, 973-615-4750', 'Listing by: Bohemia Realty Group, 973-615-4750', src)
k = '20 ter pl|11218'
src, c = blocked(k, '3J', 2600, tt(k), 'unit 3J (studio) at $2,600, available now, listed 2026-11-07.')
cached_gate(k, src, 'Bright Studio Apartment in Elevator Building Windsor Terrace', '3 (reading of unit number 3J)', 'Page gives no floor; 3J reads as floor 3 (city data lists 3 floors).', allowed_q='Dogs: Allowed; Cats: Allowed')
F(k, 'listing_broker', 'Brighton Management, 347-670-3019', 'Listing by: Brighton Management, 347-670-3019', src)
k = '34 s lexington ave|10606'; GDC = 'https://gdcrentals.com/the-metro/'; gat = IDX[GDC]['retrieved_at']
c = C7[k]
for unit, pr, plan, q in (('802', 2695, 'B3', 'Unit B3 / Bed: 1 | Bath: 1 | 664 sq ft / Rent: $2,695 / Status: Available (Now)'), ('816', 2595, 'A1', 'Unit A1 / Studio | Bath: 1 | 578 sq ft / Rent: $2,595 / Status: Available (Now)')):
    L(k, c['url'], unit, 'live', pr, 'Available (Now) on own site, plan level', 'yes', GDC, gat,
      f'Trulia refetch blocked (HTTP 403). Checked on the building\'s own site instead at {gat[11:16]} UTC: plan {plan} "{q}". The own site lists plans, not unit numbers, so unit {unit} itself is confirmed only by Trulia at {c["ts"][11:16]} UTC today (Unit {unit}, plan {plan}, ${pr:,}, Available Now). Offer on both: "One Month Free On Select Residences!"; listed price not labelled gross or net.')
src = c['url'] + ' (read ' + c['ts'][:16] + 'Z; refetch blocked)'
Cf(k, 'elevator', 'yes', 'Elevator', src, 'confirmed')
Cf(k, 'floor', '802: 8; 816: 8 (reading of unit numbers)', 'No page states the floor; the own site lists plans only. 802 and 816 read as floor 8.', src, 'unconfirmed')
Cf(k, 'dogs_allowed', 'yes', 'Cats, small dogs, large dogs allowed', src, 'confirmed')
Cf(k, 'dogs_allowed', 'yes', 'Pet Friendly and 100% Smoke-Free', GDC, 'confirmed')
Cf(k, 'dog_weight_limit', 'no number stated; small and large dogs allowed', '2 pet max; $60 monthly pet fee; $500 One-time pet fee; Breed Restrictions Apply', src, 'unconfirmed')
F(k, 'special_offer', 'one month free on select residences; gross or net not stated; own site says offers are for new residents only', 'One Month Free On Select Residences!', GDC)
F(k, 'special_offer_terms', 'new residents only', '*Prices and special offers valid for new residents only. Pricing and availability subject to change at any time.', GDC)
F(k, 'pet_rent', '$60/mo', '$60 monthly pet fee', src); F(k, 'pet_fee_one_time', '$500', '$500 One-time pet fee', src)
F(k, 'parking', 'enclosed garage with EV charging; fee not stated', 'Enclosed Garage Parking with available Electric Charging Station', GDC)
F(k, 'management_company', 'GDC (Ginsburg Development Companies)', 'The Metro by GDC offers smartly designed rental apartments in a boutique building', src)
F(k, 'building_size', '124 units, 5 listed available', 'totalUnitsInBuilding 124; availableRentalUnits 5 (page data)', src)
F(k, 'own_site_prices', 'A1 studio $2,595; B3 1BR $2,695; B4 1BR $2,795; C10 1BR $2,925, all Available (Now)', 'Studio 1 BA $2,595 578 Sq Ft A1 Available (Now) ... 1 BR 1 BA $2,695 664 Sq Ft B3 Available (Now)', GDC)
k = '66 main st|10701'; MLS = 'https://eliterealtyinc.net/properties/listing/OneKey/1048779/Yonkers/66-Main-Street-918'
src, c = blocked(k, '413', 2450, tt(k), 'Unit 413, plan 1B, 684 sqft, $2,450, Available Now. Own site 66main.com returned HTTP 403 (bot wall).', site='https://www.66main.com/')
blocked(k, '918', 2700, tt(k), 'Unit 918, plan 1A, 805 sqft, $2,700, Available Now. CONFLICT: a OneKey MLS record for 66 Main Street 918 at $2,700 reads "Rented/Leased 10/26/2026" (' + MLS + ', read ' + IDX[MLS]['retrieved_at'][11:16] + ' UTC). Unit 918 may be gone; call.', site='https://www.66main.com/')
cached_gate(k, src, 'Elevator', '413: 4; 918: 9 (reading of unit numbers)', 'No page states the floor. 413 reads as floor 4 and 918 as floor 9 of 10 stories.')
Cf(k, 'dog_weight_limit', 'size limit exists, number not given', 'Pets: Cats OK Dogs OK Size Limit', MLS, 'unconfirmed')
F(k, 'listing_conflict', 'unit 918: Trulia says available now; MLS record says rented 2026-10-26', '$2,700 / 66 Main Street 918 / Yonkers , NY 10701 / Apartment | Rented/Leased 10/26/2026', MLS)
F(k, 'special_offer', 'up to 2 months free plus free parking; terms not given; listed price not labelled gross or net', 'Up to 2 Months Fee rent plus free parking, leasing terms apply.', src)
F(k, 'parking', 'garage, 1 space (MLS record)', 'Garage: Yes; Garage Spaces: 1; Parking: Garage', MLS)
F(k, 'year_built', '2007; 10 stories', 'Year Built 2007 ... Number Of Stories 10', MLS)
F(k, 'building_size', '170 units, 4 listed available', 'totalUnitsInBuilding 170; availableRentalUnits 4 (page data)', src)
k = '70 ashburton ave|10701'; HB = 'https://www.hudsonblueyonkers.com/'
src, c = blocked(k, '', 1800, tt(k), 'floor-plan level only: plan L (studio) at $1,800, marked available; the page lists 0 available units of 92, so no unit, floor or date can be checked. Trulia page last modified 2026-11-05. Own site shows floor plans but no prices.', site=HB)
cached_gate(k, src, 'Elevator', 'unknown; plan L exists on floors 1 to 7', 'Own site: "1-7 L" and "Our L line of light-filled urban studio apartment homes begins on the 1st floor." A plan L unit could be on the ground floor. Ask which unit.')
conf[-3][4] = HB
F(k, 'special_offer', 'no amenity or parking fees (not a rent concession)', 'NO Amenity Fees EVER! NO Parking Fees EVER!', src)
F(k, 'parking', 'secured lot, one free spot per apartment', 'Secured Parking Lot. Every Apartment Comes w/ One Free Parking Spot!', src)
F(k, 'parking_own_site', 'no parking fees', 'No Parking Fees / We saved a spot just for you.', HB)
F(k, 'doorman', 'virtual doorman', '3 Fitness Centers, 4 On-Site Laundry Rooms, Parking, Virtual Doorman, Hi-Tech Security, Package Acceptance Room.', HB)
F(k, 'management_company', 'Blue Communities (own site); Trulia contact Coldwell Banker American Homes', 'Blue Communities has built an ideal living space', HB)
F(k, 'building_size', '92 units, 0 listed available', 'totalUnitsInBuilding 92; availableRentalUnits 0 (page data)', src)
k = '60 point st|10701'
src, c = blocked(k, '', 2404, tt(k), 'floor-plan level only: 1 Bedroom Apartment from $2,404; 0 available units of 146. INCOME-RESTRICTED (LIHTC) housing. Trulia page last modified 2025-08-27 (15 months ago). Probably not a live market listing.')
cached_gate(k, src, 'Elevator', 'unknown (no unit)', 'Floor-plan level listing; the description says townhouse units include "accessible ground-floor apartments".')
F(k, 'income_restriction', 'income-restricted (LIHTC limits apply)', '**NOW LEASING: 1 & 2 BEDROOMS $2404 - $2867/MO - THIS PROPERTY IS INCOME RESTRICTED - PLEASE VISIT OUR WEBSITE FOR OUR LIHTC YEARLY LIMITS OR CONTACT OFFICE FOR MORE DETAILS**', src)
F(k, 'management_company', 'Conifer Realty', 'Conifer Realty is proud to partner with the City of Yonkers', src)
F(k, 'parking', 'garage with EV charging, parking lot, street; fee not stated', 'Garage with EV charging stations parking lot and ample street parking', src)
F(k, 'building_size', '146 units in four buildings, 0 listed available', 'The development features 146 units across four buildings', src)
F(k, 'listing_warning', 'page last modified 2025-08-27; 0 available units', 'totalUnitsInBuilding 146; availableRentalUnits 0 (page data)', src)

# ---------- Openigloo ----------
def ig(k, title_part):
    p = [p for p in IG[k]['pages'] if p['status'] == 200 and title_part in p['title']][0]
    return p, p['fetched'], p['retrieved_at'], ' '.join((r['body'] or '') for r in p['reviews'])
def igfacts(k, p, url):
    m = re.search(r'Highlights\n(.*?)\nAbout', p['vt'], re.S)
    if m: F(k, 'openigloo_summary_counts', re.sub(r'\n', ' ', m.group(1))[:160], "Openigloo's own highlight box (its counts, not pulled records)", url)
NOIG = 'Openigloo: no building page for this tax lot in the reviewed-buildings sitemaps and the lot-number URL returns 404'
k = '1825 ocean ave|11230'; p, url, at, c = ig(k, '1825'); igfacts(k, p, url)
R(k, 'Openigloo', 3.13, 2, NOW, 2, 0, 0, 1, '', url)
It(k, 'management', '2024-04-28', 'Management ignores emails. Garbage takes up a lot of space in the garage. Doors constantly breaking, not ADA accessible.', 'Openigloo', url, 'building', at, c)
It(k, 'safety_incident', '2024-04-28', 'Theft of packages despite installing a door with a lock to the mailroom which is left unlocked.', 'Openigloo', url, 'building', at, c)
It(k, 'management', '2024-04-28', 'Rental listings stated doorman, but there is none. There are now fees to use the “amenities” like roof and lounge.', 'Openigloo', url, 'management_company', at, c)
It(k, 'management', '2023-08-02', 'The apartment is built poorly (ceiling leaks, floor leaks, walls are unevenly built)', 'Openigloo', url, 'building', at, c)
It(k, 'positive', '2023-08-02', 'Never had any issues with roaches or any bugs', 'Openigloo', url, 'building', at, c)
k = '80 richmond hill rd|10314'; p, url, at, c = ig(k, '80 Richmond'); igfacts(k, p, url)
R(k, 'Openigloo', 3.84, 3, NOW, 3, 0, 0, 1, '', url)
It(k, 'positive', '2025-03-16', 'responsive owners/maintenance! spacious!', 'Openigloo', url, 'management_company', at, c)
It(k, 'other', '2023-09-12', 'you have to pay extra for gym and pool', 'Openigloo', url, 'building', at, c)
It(k, 'management', '2021-11', 'Roaches were everywhere.', 'Openigloo (dated 2021-11-16, a bulk import date: 2021 or earlier)', url, 'building', at, c)
k = '5550 netherland ave|10471'
P = {n: ig(k, n) for n in ('5530', '5552', '5570', '5532')}
for n in P: igfacts(k, P[n][0], P[n][1])
R(k, 'Openigloo (no page for 5550 itself; 4 pages for other entrances on the same tax lot, Riverdale Gardens: 5530 3.1/2, 5552 1.0/1, 5570 3.4/1, 5532 2.5/1; value is my review-weighted mean)', 2.6, 5, NOW, 5, 0, 0, 4, '', P['5530'][1])
p, url, at, c = P['5530']
It(k, 'management', '2025-09-09', 'Roaches, Water damage, and lack of response from management', 'Openigloo (5530 Netherland Ave, same tax lot)', url, 'building', at, c)
It(k, 'other', '2021-11', 'Tons of various vermin Sewage in the parking garage', 'Openigloo (5530 Netherland Ave, same tax lot; dated 2021-11-16, a bulk import date)', url, 'garage_or_lot', at, c)
p, url, at, c = P['5552']
It(k, 'management', '2025-09-29', 'A & E real estate should be in prison', 'Openigloo (5552 Netherland Ave, same tax lot; 1 star)', url, 'management_company', at, c)
p, url, at, c = P['5570']
It(k, 'other', '2022-10-19', 'Unsafe feeling, unknown people coming and going all hours of the night, garbage thrown out windows, people spit in the elevator', 'Openigloo (5570 Netherland Ave, same tax lot)', url, 'building', at, c)
p, url, at, c = P['5532']
It(k, 'noise', '2021-11', 'No insulation between apartments. Can hear every step of upstairs neighbor.', 'Openigloo (5532 Netherland Ave, same tax lot; dated 2021-11-16, a bulk import date)', url, 'building', at, c)
k = '500 kappock st|10463'; p, url, at, c = ig(k, '500 Kappock'); igfacts(k, p, url)
R(k, 'Openigloo', 4.25, 2, NOW, 2, 0, 0, 2, '', url)
It(k, 'positive', '2022-04-25', 'Lots of space. Lots of light. Response super. Responsive management company.', 'Openigloo', url, 'management_company', at, c)
It(k, 'management', '2022-04-25', 'Sometimes gets cold during the winter. Heat isn’t always on, rather cycles on and off.', 'Openigloo', url, 'building', at, c)
It(k, 'management', '2021-11', 'illegally withheld security deposit.', 'Openigloo (dated 2021-11-16, a bulk import date: 2021 or earlier)', url, 'management_company', at, c)
k = '949 w end ave|10025'; p, url, at, c = ig(k, '949'); igfacts(k, p, url)
R(k, 'Openigloo', 4.81, 2, NOW, 2, 0, 0, 1, '', url)
It(k, 'positive', '2024-02-22', 'Very well maintained building; great location steps from Riverside and subways on Broadway; charming and sturdy apartment; responsive owners and managers; live in super', 'Openigloo', url, 'building', at, c)
It(k, 'elevator', '2024-02-22', 'Swing door elevator is mildly annoying but you get used to it, plus there is a service elevator if you need it.', 'Openigloo (a description of the elevator, not an outage)', url, 'building', at, c)
It(k, 'management', '2021-11', 'We didn’t have enough sunlight and mice got in once.', 'Openigloo (dated 2021-11-16, a bulk import date: 2021 or earlier)', url, 'building', at, c)
k = '1224 saint nicholas ave|10032'; p, url, at, c = ig(k, '1224'); igfacts(k, p, url)
R(k, 'Openigloo', 2.27, 6, NOW, 5, 0, 0, 5, '', url)
It(k, 'management', '2025-07-06', 'Impossible to get ahold of property management, but the worst is the BUGS. actual roach infestation, we keep the apartment spotless and they have not LET UP', 'Openigloo', url, 'building', at, c)
It(k, 'management', '2023-07-26', 'They don’t clean common areas for tenants in months such as hallways, lobby, laundry. The intercoms don’t work.', 'Openigloo', url, 'building', at, c)
It(k, 'management', '2022-09-26', 'Bugs- constant bug problem. Even with extermination, I spent the entire of my lease living with roaches not matter how clean I was.', 'Openigloo', url, 'building', at, c)
It(k, 'management', '2022-05-10', 'little to no heat during the winter despite complaints', 'Openigloo', url, 'building', at, c)
It(k, 'management', '2021-11', 'There was little to no heat during the winter months and the super said there was nothing they could do, my apartment got bed bugs 3 months after I moved in', 'Openigloo (dated 2021-11-16, a bulk import date: 2021 or earlier)', url, 'building', at, c)
k = '545 edgecombe ave|10032'; p, url, at, c = ig(k, '545'); igfacts(k, p, url)
R(k, 'Openigloo', 4.5, 1, NOW, 1, 0, 0, 0, '', url)
It(k, 'other', '2025-01-29', 'Unfortunately the roof fell in the apartment due to a clogged toilet upstairs.', 'Openigloo', url, 'building', at, c)
It(k, 'positive', '2025-01-29', 'Building and neighbors were lovely. Apartment was always quiet and walls were soundproof.', 'Openigloo', url, 'building', at, c)

# ---------- Reserve at Lakeside: resident review page (modernmsg, the review platform the property uses) ----------
k = '7 lakeside rd|12550'; url = 'https://modernmsg.com/reserve-at-lakeside'; raw, at = page(url)
c = H.unescape(raw.encode().decode('unicode_escape', errors='ignore')) + ' ' + raw
c = json.dumps(json.loads([m.group(1) for m in re.finditer(r'<script[^>]*>(.*?)</script>', raw, re.S) if '"@context"' in m.group(1)][0].split('//<![CDATA[')[-1].split('//]]>')[0]), ensure_ascii=False)
R(k, 'Resident reviews on modernmsg.com (review platform linked to the property)', 4.5, 90, NOW, 25, 8, 1, 1, 'unresponsive_management', url)
R(k, 'Apartment List', '', '', NOW, 0, '', '', '', '', 'https://www.apartmentlist.com/ny/newburgh/reserve-at-lakeside-senior-housing-55 (no rating or review data in the page)')
It(k, 'positive', '2026-09-18', 'Maintenance was very aware of my needs. Covered the elevator. I am very happy with my choice to move here.', 'modernmsg.com resident reviews', url, 'building', at, c)
It(k, 'management', '2026-07-02', 'Would like to see the garbage problem improve, cleanliness of the buildings improve and overall communication with management improve.', 'modernmsg.com resident reviews (2 stars)', url, 'management_company', at, c)
It(k, 'other', '2026-07-02', 'We are excited about the new management changes and hope to see more activities and an updated community calendar of events. The broken pool heater has been a bummer and hope it gets replaced soon.', 'modernmsg.com resident reviews', url, 'management_company', at, c)
It(k, 'other', '2026-06-02', 'The issues being addressed were known last year and now the opening and heating of the pool has been delayed indefinitely.', 'modernmsg.com resident reviews', url, 'building', at, c)
It(k, 'management', '2026-05-17', 'It is, however, very expensive. They also raise the the rent quite a bit each year.', 'modernmsg.com resident reviews', url, 'management_company', at, c)
It(k, 'other', '2026-02-13', 'The company that was plowing and snow blowing were rude and actually blew more snow into and onto parked cars making it more difficult to clear and move cars!', 'modernmsg.com resident reviews (2 stars)', url, 'garage_or_lot', at, c)
It(k, 'positive', '2026-05-16', 'Grateful to Chris from maintenance and Jess the property manager for their patience and their quick responses to solving various issues.', 'modernmsg.com resident reviews', url, 'management_company', at, c)

# ---------- Heatherwood: Birdeye ----------
k = '99 waverly ave|11772'; url = 'https://birdeye.com/heatherwood-house-at-patchogue-158137321935974'; raw, at = page(url); c = H.unescape(raw)
R(k, 'Birdeye aggregate (page shows 9 reviews, all 5-star, newest 2024-12-09: a biased sample)', 4.5, 301, NOW, 9, 0, 0, 0, '', url)
It(k, 'positive', '2024-12-09', 'Building was repaired for water issue. Work was completed far quicker than expected.', 'Birdeye', url, 'management_company', at, c)
It(k, 'positive', '2024-05-03', 'Had an Emergency on a sunday morning. Toilet tank streaming water, bathroom floor flooded. Problem resolved quickly.', 'Birdeye', url, 'management_company', at, c)

# ---------- Sleepy Hollow Gardens: News 12 ----------
k = '157 white plains rd|10591'; url = 'https://westchester.news12.com/2026/04/21/residents-in-sleepy-hollow-terraced-garden-apartments-voice-concerns-over-mold-vermin-more/6cUNTJCiMvAXay7n5Lpoud'; raw, at = page(url); c = text(raw)
It(k, 'management', '2026-04-21', 'residents of the Sleepy Hollow Terraced Garden Apartments in Tarrytown spoke with News 12 over what the say are unlivable conditions, including rats, cockroaches, mice, leaks, burst pipes and more at 177 White Plains Road.', 'News 12 Westchester', url, 'building', at, c)
It(k, 'management', '2026-04-21', '"We\'ve had numerous water main breaks that force the cockroaches through my sink, through my pipes, into my radiator," he said.', 'News 12 Westchester', url, 'building', at, c)
It(k, 'management', '2026-04-21', 'Other residents shared photos of leaking walls, uneven floors, mold and vermin within their units.', 'News 12 Westchester', url, 'building', at, c)
It(k, 'management', '2026-04-21', 'News 12 contacted Samson Management and is waiting to hear back.', 'News 12 Westchester', url, 'management_company', at, c)

# ---------- none_found and ratings none_found ----------
ZB = json.load(open('raw/evidence_b17/zumper_bld.json'))
def zw(k): z = ZB.get(k, {}); return ('Zumper address page (no rating or review block): ' + z['url']) if z.get('status') == 200 else 'Zumper: no page for the address (404)'
searched = {'1825 ocean ave|11230', '7 lakeside rd|12550', '80 richmond hill rd|10314', '99 waverly ave|11772', '60 point st|10701', '157 white plains rd|10591', '5550 netherland ave|10471',
            '1224 saint nicholas ave|10032', '34 s lexington ave|10606', '38 rider ave|11772', '66 main st|10701', '70 ashburton ave|10701', '260 w st|10549', '5 stuyvesant pl|10301', '80 w grand st|10552'}
NYC = set(IG)
have_items = {r[0] for r in items}; have_r = {r[0] for r in ratings}
EXTRA = {
 '34 s lexington ave|10606': ' Search results point to elevator-outage and package complaints on ApartmentRatings and RentCafe (both blocked for us): not read, not recorded.',
 '66 main st|10701': ' Search results point to reviews on Apple Maps about elevator, heat and garage-door problems and a management change: page not readable, not recorded.',
 '60 point st|10701': ' A Better Business Bureau complaint page for Conifer Realty came up in search; BBB is disallowed for us, not read.',
 '99 waverly ave|11772': ' Search results point to ApartmentRatings reviews mentioning a smashed car window and police in the lot: site blocked, not read, not recorded.',
 '1825 ocean ave|11230': ' Search found fire reports for Ocean Avenue without this street number: not recorded.',
}
for r in B:
    k = r['addr_key']; nyc = k in NYC
    where = []
    where.append('listing page: no reviews')
    if nyc: where.append('Openigloo: reviews read' if any(p['status'] == 200 for p in IG[k]['pages']) else NOIG)
    where.append(zw(k))
    where.append('one web search for news about the address: nothing about the building itself' if k in searched else 'no news search run for this address')
    if nyc: where.append('NYC public records left to the separate records pull')
    w = '; '.join(where) + EXTRA.get(k, '')
    if k not in have_items: NF(k, 'Looked at: ' + w)
    if k not in have_r:
        ratings.append([k, NAME[k], 'none_found', '', '', '', NOW, 0, '', '', '', '', 'Looked at: ' + w])

def out(name, head, rows):
    with open(E + name, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(head); w.writerows(rows)
    print(name, len(rows))
order = {r['addr_key']: i for i, r in enumerate(B)}
for lst in (live, conf, items, facts, ratings): lst.sort(key=lambda x: order[x[0]])
out('live_check_batch_17.csv', 'addr_key,listing_url,unit,status,price_now,available_now_text,matches_stored,building_site_url,checked_at,notes'.split(','), live)
out('confirm_batch_17.csv', 'addr_key,fact,value,quote,source_url,status'.split(','), conf)
out('items_batch_17.csv', 'addr_key,building_name,category,item_date,excerpt,source_site,source_url,about,retrieved_at'.split(','), items)
out('facts_batch_17.csv', 'addr_key,fact,value,quote,source_url'.split(','), facts)
out('ratings_batch_17.csv', 'addr_key,building_name,rating_source,rating_value,rating_scale,review_count,as_of_date,reviews_read,reviews_last_6_months,negative_last_6_months,negative_older,serious_issue_tags_last_6_months,source_url'.split(','), ratings)
from collections import Counter
print('live', Counter(r[3] for r in live)); print('conf', Counter(r[5] for r in conf)); print('items', Counter(r[2] for r in items))
print('missing buildings', [k for k in order if k not in {r[0] for r in live}])
