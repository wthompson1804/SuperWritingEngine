"""Evidence batch 11: build the five output CSVs from cached pages. No network.

Inputs: data/reference/evidence_batches/batch_11.csv, raw/evidence_b11/ (cached pages), and two scratch JSON files made
by ev11_trulia_parse.py and ev11_zumper_reviews.py (rerun those first if the scratch folder is gone).
Outputs: data/evidence/{live_check,confirm,items,facts,ratings}_batch_11.csv. Re-running overwrites them.
"""
import csv, json, re, sys
sys.path.insert(0, 'scripts')
from ev11_text import text

S = '/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b11/'
OUT = 'data/evidence/'
T = json.load(open(S + 'trulia_parsed.json'))
Z = json.load(open(S + 'zumper_reviews.json'))
BATCH = list(csv.DictReader(open('data/reference/evidence_batches/batch_11.csv')))
TR = 'https://www.trulia.com/building/'
ZB = 'https://www.zumper.com/apartment-buildings/'

# Page actually read for each building (Zillow links in the batch were not fetched; the Trulia copy was used).
PAGE = {
    '430 e main st|10940': TR + 'the-park-at-main-430-e-main-st-middletown-ny-10940-2088963592',
    '1200 regency ct|10940': TR + 'the-regency-club-1200-regency-ct-middletown-ny-10940-1001943070',
    '131 mamaroneck ave|10601': TR + 'the-mitchell-131-mamaroneck-ave-white-plains-ny-10601-2750800357',
}
SITE = {  # building's own site, where one was found and readable
    '1 saint marys convent|10566': 'https://gdcrentals.com/fort-hill/',
    '1 martine ave|10606': 'https://gdcrentals.com/one-martine/',
    '131 mamaroneck ave|10601': 'https://livethemitchell.com/',
    '430 e main st|10940': 'https://www.theparkatmain.com/',
    '7-11 s broadway|10601': 'https://www.theazzure.com/',
}
ZUMPER = {  # Zumper building page found for the address (None = none found)
    '11 park pl|10801': ZB + 'p221266/lombardi-downtown-new-rochelle-new-rochelle-ny',
    '1 saint marys convent|10566': ZB + 'p397878/fort-hill-peekskill-peekskill-ny',
    '12 brooklyn ave valley stream ny 11581 usa|11581': ZB + 'p294775/12-brooklyn-avenue-valley-stream-ny',
    '12 brooklyn ave|11581': ZB + 'p294775/12-brooklyn-avenue-valley-stream-ny',
    '201 genung st|10940': ZB + 'p15561/boulder-pointe-middletown-ny',
    '1200 regency ct|10940': ZB + 'p216713/the-regency-club-middletown-ny',
    '1 kensington cir|10923': ZB + 'p17945/tor-view-village-west-haverstraw-ny',
    '440 hamilton ave|10601': ZB + 'p913529/hamilton-crossing-apartments-white-plains-ny',
    '1 dekalb ave|10605': ZB + 'p361437/one-dekalb-white-plains-ny',
    '1 alexander st|10701': ZB + 'p8364/hudson-park-i-ii-downtown-yonkers-yonkers-ny',
    '20 water grant st|10701': ZB + 'p288235/modera-hudson-riverfront-downtown-yonkers-yonkers-ny',
}
AL = {'440 hamilton ave|10601': 'https://www.apartmentlist.com/ny/white-plains/hamilton-crossing',
      '131 mamaroneck ave|10601': 'https://www.apartmentlist.com/ny/white-plains/the-mitchell-apartments'}
# Floor of each stored unit. 'c' = stated on a page, 'i' = inferred from the unit number only, 'u' = cannot tell.
FLOOR = {'6S': ('6', 'i'), 'A508': ('5', 'i'), '304': ('3', 'i'), '406': ('4', 'i'), '705': ('7', 'i'), '501': ('5', 'i'),
         '63': ('', 'u'), '0801': ('', 'u'), '0708': ('', 'u'), '14D': ('', 'u'), '21H': ('', 'u'), '440-0915': ('9', 'i'),
         '307': ('3', 'i'), '207': ('2', 'c'), '617': ('6', 'i'), '1013': ('10', 'i'), '1405': ('14', 'i'), '203': ('2', 'i'),
         '512': ('5', 'i'), '306F': ('3', 'i'), '606F': ('6', 'i'), '401': ('4', 'i'), '01-202': ('2', 'i'), '01-468': ('4', 'i')}


def page_of(r):
    return PAGE.get(r['addr_key']) or r['urls'].split(' | ')[0]


def units_of(rec):
    out = {}
    for x in rec['units']:
        u = x.get('unit')
        if u:
            out[u['name'].replace('Unit ', '')] = dict(price=(u.get('priceRange') or {}).get('min'), avail=u.get('availabilityText', ''),
                                                       date=(u.get('availabilityDate') or '')[:10], beds=u['bedrooms'].get('fullValue'), plan=x.get('plan'))
    return out


def dog_card(rec):
    for c in (rec.get('pet2') or {}).get('cards', []):
        if c['species'] == 'DOGS':
            return c.get('statusLabel'), {f['label']: f['value'] for f in c.get('facts', [])}
    return None, {}


def grab(path, start, end, last=False):
    """Verbatim excerpt from a cached page: from `start` through `end`, whitespace collapsed."""
    t = re.sub(r'\s+', ' ', text(path))
    i = t.rfind(start) if last else t.find(start)
    j = t.find(end, i)
    assert i >= 0 and j >= 0, (path, start)
    return t[i:j + len(end)].strip()


def write(name, cols, rows):
    with open(OUT + name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in cols})
    print(name, len(rows))


live, conf, facts, items, ratings = [], [], [], [], []
NOW = '2026-11-15T21:30:00+00:00'

# ---------------------------------------------------------------- live check, confirm, facts (from Trulia pages)
for r in BATCH:
    k, name = r['addr_key'], r['building_name']
    url = page_of(r)
    stored_units = [x.strip() for x in r['unit_list'].split(',')]
    stored_rents = [x.strip() for x in r['rents'].split(',')]
    site = SITE.get(k, '')
    via = '' if url == r['urls'].split(' | ')[0] else f' Batch link is a Zillow page (not fetched); read the Trulia copy {url}.'

    if 'zumper.com/listings' in url:   # 12 Brooklyn Ave, Zumper listing without a unit number
        ts = '2026-11-15T21:14:01+00:00'
        live.append(dict(addr_key=k, listing_url=url, unit='', status='live', price_now=2700, available_now_text='not stated (page says "Listed 5+ Days Ago")',
                         matches_stored='yes', building_site_url='', checked_at=ts,
                         notes='Zumper listing page: 1 bed, 1 bath, 806 sqft, "Monthly rent $2,700". No unit number and no availability date on the page. Own leasing site not found.'))
        conf += [dict(addr_key=k, fact='elevator', value='yes', quote='Building | Cats OK Dogs OK | Elevator Fitness Center', source_url=url, status='confirmed'),
                 dict(addr_key=k, fact='floor', value='unknown', quote='no unit number or floor on the page', source_url=url, status='unconfirmed'),
                 dict(addr_key=k, fact='dogs_allowed', value='yes', quote='Dog Policy | Allowed', source_url=url, status='confirmed'),
                 dict(addr_key=k, fact='dog_weight_limit', value='unconfirmed', quote='Contact for more information on pet policy.', source_url=url, status='unconfirmed')]
        facts += [dict(addr_key=k, fact='application_fee', value='$20 per applicant', quote='Application Fee | Per-applicant. Agent application fee. | $20', source_url=url),
                  dict(addr_key=k, fact='utilities_included', value='heat and hot water', quote='Heat and hot water included', source_url=url),
                  dict(addr_key=k, fact='parking', value='garage parking listed; fee not stated', quote='Grounds | Garage Parking Outdoor Space', source_url=url)]
        continue

    rec = T[url]
    ts = rec['ts']
    mod = (rec.get('modified') or '')[:10]
    feats = rec['feats']

    if '/home/' in url:   # 12 Brooklyn Ave 501, Trulia single-unit page
        live.append(dict(addr_key=k, listing_url=url, unit='501', status='live', price_now=2675, available_now_text='now', matches_stored='yes',
                         building_site_url='', checked_at=ts,
                         notes='Trulia: For Rent, listed 2026-11-06 ("8 days on Trulia"), broker Blue Chip Real Estate Group LLC. Own leasing site not found.'))
        conf += [dict(addr_key=k, fact='elevator', value='unconfirmed', quote='not listed on this Trulia page; the Zumper listing for the same address lists "Elevator"', source_url=url, status='unconfirmed'),
                 dict(addr_key=k, fact='floor', value='5', quote='inferred from the unit number only; the page does not state the floor', source_url=url, status='unconfirmed'),
                 dict(addr_key=k, fact='dogs_allowed', value='yes', quote='Cats, small dogs allowed', source_url=url, status='confirmed'),
                 dict(addr_key=k, fact='dog_weight_limit', value='unconfirmed', quote='Cats, small dogs allowed (no number given)', source_url=url, status='unconfirmed')]
        facts += [dict(addr_key=k, fact='pet_rent', value='none', quote='This pet-friendly building features no pet rent and no pet deposit', source_url=url),
                  dict(addr_key=k, fact='utilities_included', value='heat and hot water', quote='Heat and hot water are included, with parking available for an additional fee.', source_url=url),
                  dict(addr_key=k, fact='parking', value='on site, extra fee, amount not stated', quote='Off Street Parking, On Site', source_url=url),
                  dict(addr_key=k, fact='building_age', value='new construction', quote='this new construction building is ideally located right off Rockaway Avenue', source_url=url),
                  dict(addr_key=k, fact='management_company', value='listed by Blue Chip Real Estate Group LLC (broker); manager not stated', quote='Listing by: Blue Chip Real Estate Group LLC', source_url=url)]
        continue

    units = units_of(rec)
    plans = [x for x in rec['units'] if not x.get('unit')]
    cheapest = sorted((v['price'], n) for n, v in units.items() if v['price'] and v['beds'] in ('Studio', '1 Bedroom'))
    for su, sr in zip(stored_units, stored_rents):
        row = dict(addr_key=k, listing_url=r['urls'].split(' | ')[0], unit='' if su == '?' else su, building_site_url=site, checked_at=ts)
        if su in units:
            u = units[su]
            in_window = (not u['date']) or u['date'] <= '2026-12-15'
            same = str(u['price']) == sr
            row.update(status='live' if same and in_window else 'changed', price_now=u['price'], available_now_text=u['avail'].replace('Available ', '') or 'not stated',
                       matches_stored='yes' if same else 'no',
                       notes=f"Trulia building page (last modified {mod}): Unit {su}, {u['beds']}, plan {u['plan']}." + via)
        elif su == '?' and units:   # stored row had no unit; compare with the cheapest studio/1BR now
            p, n = cheapest[0] if cheapest else ('', '')
            # the cheapest unit may already be another stored row; take the cheapest that is not
            other = [c for c in cheapest if c[1] not in stored_units]
            p, n = other[0] if other else (p, n)
            row.update(status='changed' if str(p) != sr else 'live', price_now=p, available_now_text=units[n]['avail'].replace('Available ', '') if n else '',
                       matches_stored='yes' if str(p) == sr else 'no',
                       notes=f"Stored row had no unit number (${sr}). No unit at that price now; nearest is Unit {n} at ${p}. Trulia page last modified {mod}." + via)
        else:   # floor-plan level only
            ptxt = '; '.join(f"{x['plan']}" for x in plans)
            row.update(status='live', price_now=sr, available_now_text='plan marked "Available Now"; no unit listed', matches_stored='yes',
                       notes=f"Floor-plan level only: the page lists plans ({ptxt}) and {(rec.get('ud') or {}).get('availableRentalUnits', 0)} available units, so no unit, floor or date can be checked. "
                             f"Price range on page {rec['price']}. Trulia page last modified {mod}. Confirm by phone." + via)
        live.append(row)

    # gate facts
    has_elev = any(t[3] == 'Elevator' for t in feats)
    conf.append(dict(addr_key=k, fact='elevator', value='yes' if has_elev else 'unconfirmed',
                     quote='Elevator' if has_elev else 'no elevator in the feature list on this page', source_url=url,
                     status='confirmed' if has_elev else 'unconfirmed'))
    for su in stored_units:
        fl, how = FLOOR.get(su, ('', 'u'))
        if su == '?':
            q = 'floor-plan level listing; no unit number'
        elif how == 'i':
            q = f'inferred from unit number {su} only; the page does not state the floor'
        elif how == 'c':
            q = 'floor_name "2" in the unit data on livethemitchell.com/floorplans/'
        else:
            q = f'unit number {su} does not show the floor (looks like a building or sequence number)'
        conf.append(dict(addr_key=k, fact='floor', value=fl or 'unknown', quote=q,
                         source_url='https://livethemitchell.com/floorplans/' if how == 'c' else url, status='confirmed' if how == 'c' else 'unconfirmed'))
    st, df = dog_card(rec)
    allowed = (rec.get('pet') or {}).get('formattedPetsAllowed', '')
    conf.append(dict(addr_key=k, fact='dogs_allowed', value='yes' if st == 'Allowed' else 'unconfirmed', quote=allowed or f'Dogs: {st}', source_url=url,
                     status='confirmed' if st == 'Allowed' else 'unconfirmed'))
    extra = ' '.join((rec.get('pet2') or {}).get('additionalDetails') or [])
    m = re.search(r'[^.]*(max(imum)? \d+ ?lbs\.?[^.]*|Weight Limit: Maximum \d+ lbs\.[^.]*)', extra)
    if df.get('Weight limit (lbs.)'):
        conf.append(dict(addr_key=k, fact='dog_weight_limit', value=df['Weight limit (lbs.)'], quote=f"Weight limit (lbs.): {df['Weight limit (lbs.)']}; Size allowed: {df.get('Size allowed', '')}",
                         source_url=url, status='confirmed'))
    elif m:
        n = re.search(r'(\d+) ?lbs', m.group(0)).group(1)
        conf.append(dict(addr_key=k, fact='dog_weight_limit', value=n + (' combined for up to 2 pets' if 'combined' in m.group(0) else ''), quote=m.group(0).strip(), source_url=url, status='confirmed'))
    else:
        size = df.get('Size allowed', '')
        conf.append(dict(addr_key=k, fact='dog_weight_limit', value='unconfirmed', source_url=url, status='unconfirmed',
                         quote=f'Size allowed: {size} (no number given)' + ('; "small" only suggests a low limit' if size == 'Small' else '')))

    # useful facts
    ud = rec.get('ud') or {}
    if ud.get('totalUnitsInBuilding'):
        facts.append(dict(addr_key=k, fact='building_size', value=f"{ud['totalUnitsInBuilding']} units, {ud.get('availableRentalUnits', 0)} listed available",
                          quote=f"totalUnitsInBuilding {ud['totalUnitsInBuilding']}; availableRentalUnits {ud.get('availableRentalUnits', 0)} (page data)", source_url=url))
    if (rec.get('mgr') or {}).get('name'):
        facts.append(dict(addr_key=k, fact='management_company', value=rec['mgr']['name'].replace('&amp;', '&'), quote=f"Property management company: {rec['mgr']['name'].replace('&amp;', '&')}", source_url=url))
    for lab in ('Monthly dog rent', 'One-time fee'):
        if df.get(lab):
            facts.append(dict(addr_key=k, fact='pet_rent' if 'rent' in lab else 'pet_fee_one_time', value=df[lab], quote=f'Dogs: {lab} {df[lab]}', source_url=url))
    park = [' / '.join(x for x in t[1:] if x) for t in feats if re.search(r'park|garage', ' '.join(t[1:3]), re.I) and 'Pet Park' not in t[3] and t[3] != 'Park']
    if park:
        facts.append(dict(addr_key=k, fact='parking', value='; '.join(dict.fromkeys(p.split(' / ')[-1].replace('\n', ' ') for p in park))[:300], quote=' | '.join(park).replace('\n', ' ')[:400], source_url=url))
    if any(t[3] == 'Pool' for t in feats):
        facts.append(dict(addr_key=k, fact='pool', value='yes (indoor or outdoor not stated in the feature list)', quote='Pool', source_url=url))
    for o in rec.get('offers') or []:
        facts.append(dict(addr_key=k, fact='concession', value=o['description'].replace('\n', ' ')[:200], quote=(o['description'] + (' ' + o.get('subText', '') if o.get('subText') else '')).replace('\n', ' ')[:300], source_url=url))
    facts.append(dict(addr_key=k, fact='listing_last_modified', value=mod, quote=f'lastDateModified {mod} (page data)', source_url=url))

# ---------------------------------------------------------------- manual additions read from the pages
def F(k, fact, value, quote, url): facts.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=url))
def C(k, fact, value, quote, url, status): conf.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=url, status=status))

u = TR + 'hamilton-crossing-440-hamilton-ave-white-plains-ny-10601-2747817576'
F('440 hamilton ave|10601', 'required_monthly_fee', '$80 amenities fee', 'Amenities Fee: $80 (Per Unit, Per Month, Mandatory)', u)
F('440 hamilton ave|10601', 'parking', 'garage $170 + tax for the first vehicle', 'Parking: 1st vehicle ($170+tax) 2nd vehicle ($250+tax) (First-come, first-served, EV charging stations are pay-per-use)', u)
F('440 hamilton ave|10601', 'pet_rent', '$50 per pet, max 2', 'Monthly Pet Fee: $50 (Per Pet, Per Month, Max 2 Pets).', u)
F('440 hamilton ave|10601', 'management_company', 'Rose Associates (leasing agent); start date not found', "Rose Associates is the exclusive broker/agent for the Landlord (Landlord's Agent) for this property", u)
u = TR + 'the-azzure-7-11-s-broadway-white-plains-ny-10601-2748838571'
F('7-11 s broadway|10601', 'required_monthly_fee', 'flat electric charge: $125 studio, $165 one-bedroom', 'tenants pay a monthly flat rate for electric which includes heat and central AC. Studios pay $125 month, 1 bedrooms $165 a month', u)
F('7-11 s broadway|10601', 'parking', 'adjacent garage, $64 to $140 a month', 'Plenty of Parking with adjacent garage. $140 month. out by 8am back after 6pm & all day/night weekends just $64 a month!', u)
F('7-11 s broadway|10601', 'own_site_quality', 'own site is an unfinished template (placeholder text, "Bali, Indonesia", 0% counters); nothing on it is usable',
  'Guest Satisfaction | 0 | % | Positive Reviews | 0 | %', 'https://www.theazzure.com/')
u = TR + 'hudson-44-44-hudson-st-yonkers-ny-10701-2775827441'
F('44 hudson st|10701', 'building_floors', '25 stories (listing text)', "Yonkers' newest and tallest luxury rental building that rises 25 stories over the Hudson River", u)
F('44 hudson st|10701', 'doorman', 'yes', 'Doorman-attended lobby & package room', u)
F('44 hudson st|10701', 'parking', 'indoor self-park garage; fee not stated', 'Indoor self-park garage with EV charging', u)
F('44 hudson st|10701', 'pool', 'heated rooftop pool (outdoor)', 'From the 25th-floor Sky Lounge with a heated rooftop pool', u)
u = 'https://gdcrentals.com/one-martine/'
F('1 martine ave|10606', 'doorman', '24/7 concierge', '24/7 Staffed Concierge Desk', u)
F('1 martine ave|10606', 'parking', 'indoor garage; fee not stated', 'Indoor Garage Parking with available Electric Charging Stations', u)
F('1 martine ave|10606', 'management_company', 'GDC (Ginsburg Development Companies), on site', 'On-site Property Management by GDC', u)
F('1 martine ave|10606', 'price_conflict', "own site: Line 17 at $2,675 available now; Trulia: unit 617 at $2,775 now and unit 417 at $2,675 from Jan 25",
  'Line 17 | Bed: 1 | Bath: 1 | 635 sq ft | Rent: $2,675 | Status: Available (Now)', u)
u = 'https://gdcrentals.com/fort-hill/'
F('1 saint marys convent|10566', 'parking', 'indoor garage and outdoor spaces; fee not stated', 'Indoor garage parking and outdoor parking spaces', u)
F('1 saint marys convent|10566', 'own_site_price', 'plan B4 (unit A508 is a B4) $2,675, available now', 'Unit B4 | Bed: 1 | Bath: 1 | 675 sq ft | Rent: $2,675 | Status: Available (Now)', u)
F('131 mamaroneck ave|10601', 'own_site_price', 'unit 207: $2,781, available now, floor 2', '#207 ... Starting at $2,781 ... Available Now', 'https://livethemitchell.com/floorplans/')
F('131 mamaroneck ave|10601', 'pool', 'rooftop pool (outdoor)', 'Rooftop pool with firepits, grills and private dining areas', 'https://livethemitchell.com/amenities/')
C('430 e main st|10940', 'elevator', 'yes', 'Apartment Features | Stainless Steel Appliances | In-Unit Washer & Dryer | Dishwasher | Electric Heating | Elevator | Pet-Friendly',
  'https://www.theparkatmain.com/amenities/', 'confirmed')
F('430 e main st|10940', 'own_site_price', 'own site: Floorplan D "Starting at $2400"; Trulia unit 63 (Floorplan D) is $2,450', 'Floorplan D | 1 bed 1 bath 898 sq. ft. | Starting at $2400', 'https://www.theparkatmain.com/floorplans/')
F('430 e main st|10940', 'pool', 'seasonal pool (outdoor)', 'The Park at Main offers communal spaces such as a seasonal pool', PAGE['430 e main st|10940'])
F('1200 regency ct|10940', 'building_type', 'townhome-style homes; no elevator mentioned', 'The Regency Club offers 1 bedroom w/ den and 2 bedroom townhome-style rental homes.', PAGE['1200 regency ct|10940'])
F('1200 regency ct|10940', 'pool', 'outdoor pool', 'This pet-friendly community includes a Club House, fitness center, outdoor pool, tennis court, and playground.', PAGE['1200 regency ct|10940'])
F('1200 regency ct|10940', 'parking', 'surface lot; fee not stated', 'Parking Policy Surface Lot', ZUMPER['1200 regency ct|10940'])
u = TR + 'chateau-rive-305-chateau-rive-peekskill-ny-10566-2739941135'
F('305 chateau rive|10566', 'listing_text_stale', 'description still advertises a July 26 open house and a two-bedroom; unit 304 is listed as a 1BR', 'OPEN HOUSE THIS WEEKEND SATURDAY JULY 26th BETWEEN 10:30-12:30pm', u)
F('305 chateau rive|10566', 'application_fee', '$20', '$20.00 non-refundable fee with application.', u)
u = TR + 'park-place-towers-1108-brown-st-peekskill-ny-10566-2737454290'
F('1108 brown st|10566', 'parking', 'free for 1 to 3 vehicles (current offer)', 'Free Parking for 1-3 vehicles!', u)
F('1108 brown st|10566', 'required_monthly_fee', 'no amenity fee (current offer)', 'No Amenity Fee!', u)
H1 = 'https://peekskillherald.com/31447/news/park-place-tower-tenants-grapple-with-package-thief-and-quality-of-life/'
HP = 'raw/evidence_b11/98dfbf7eec485a1b.html'
F('1108 brown st|10566', 'year_built', 'opened spring 2024; 8 floors, 181 units', grab(HP, 'The market rate rental apartment with eight floors', 'opened in spring 2024.'), H1)
F('1108 brown st|10566', 'management_company', 'Alma Realty (owner, per Peekskill Herald); ownership entity BNS I, LLC (per News 12)', grab(HP, 'Fabrizio Villalta of Alma Realty, which owns Park Place Tower', 'Park Place Tower'), H1)
u = TR + 'apex-hudson-riverfront-20-water-grant-st-yonkers-ny-10701-2740011249'
F('20 water grant st|10701', 'optional_monthly_fee', 'Premium Resident Package $95; storage $150', 'Premium Resident Package ($95); Storage ($150)', u)
F('20 water grant st|10701', 'year_built', '2018', 'Year Built: 2018', ZUMPER['20 water grant st|10701'])
C('20 water grant st|10701', 'dog_weight_limit', '75', 'Maximum Number of Pets: 2 ; Max Weight of Pets: 75 lbs.', ZUMPER['20 water grant st|10701'], 'confirmed')
u = TR + 'hudson-park-community-1-alexander-st-yonkers-ny-10701-1001440943'
F('1 alexander st|10701', 'doorman', '24-hour concierge', 'Amenities include a 24-hour concierge, fitness center, and coffee shop', u)
F('1 alexander st|10701', 'parking', '$109 uncovered or $180 covered, one assigned space per apartment', 'Garage Parking / $109 parking fee ... One assigned uncovered space per apartment ... $180 parking fee ... One covered assigned space per apartment', u)
u = TR + 'tor-view-village-apartments-1-kensington-cir-garnerville-ny-10923-1001440742'
F('1 kensington cir|10923', 'parking', 'lot, one assigned space per apartment', 'Off Street Parking One Assigned Space per Apartment', u)
F('1 kensington cir|10923', 'management_company', 'owner Berk-Cohen Associates; manager Manhattan Management Company (as of March 2020)',
  grab('raw/evidence_b11/4ceec6a3c563c14c.html', 'Berk-Cohen Associates owns', 'for that complex.'), 'https://hgar.com/wro-alleges-rockland-county-apartment-complex-discriminated-against-people-with-mental-disabilities')
u = TR + '30-broad-street-30-broad-st-port-chester-ny-10573-2785857715'
F('30 broad st|10573', 'parking', 'off-site covered garage two blocks away, not assigned; first year free', 'Offsite parking available - 1st year FREE! 2 blocks away covered and permitted not assigned.', u)
u = TR + 'the-atelier-at-westchester-place-40-westchester-pl-new-rochelle-ny-10801-2750910517'
F('40 westchester pl|10801', 'income_restricted', 'described as an affordable development; income rules likely apply (not stated on the page)', 'Welcome to The Atelier, an exquisite affordable new development in the heart of charming New Rochelle.', u)
F('40 westchester pl|10801', 'unit_hint', 'the two "plans" are named 207 ($1,999) and 607 ($2,218): probably unit numbers on floors 2 and 6', 'Studio (2 Floorplans): 207 $1,999; 607 $2,218', u)
u = TR + 'the-lombardi-11-park-pl-new-rochelle-ny-10801-2750951745'
F('11 park pl|10801', 'pet_rules', '$350 fee, monthly charge, breed list; $1,000 fine for an unregistered pet', 'non-refundable $350 pet fee and a monthly charge per pet. A $1,000 fine will be assessed for each unregistered pet.', u)
u = TR + '1180-midland-1180-midland-ave-bronxville-ny-10708-2750793263'
F('1180 midland ave|10708', 'listing_stale', 'Trulia page last modified 2025-10-14, 13 months before the check; treat price and availability as unverified', 'lastDateModified 2025-10-14 (page data)', u)
F('1180 midland ave|10708', 'building_age', 'about 50 years old (listing text)', 'has enjoyed an excellent reputation in the community for the past 50 years', u)
u = TR + 'wakefield-station-apartments-135-wakefield-ave-yonkers-ny-10704-2743593441'
F('135 wakefield ave|10704', 'second_listing', 'Zumper copy of unit 401 also live at $2,595 (updated within the hour)', 'Monthly rent $2,595 ... Updated 1 Hour Ago', 'https://www.zumper.com/listings/25937100p/1-bedroom-southeast-yonkers-yonkers-ny')

# ---------------------------------------------------------------- evidence items and ratings
def I(k, name, cat, date, excerpt, site, url, about, at=NOW):
    items.append(dict(addr_key=k, building_name=name, category=cat, item_date=date, excerpt=excerpt, source_site=site, source_url=url, about=about, retrieved_at=at))

PK = '1108 brown st|10566'
N1 = 'https://westchester.news12.com/tenants-of-a-peekskill-apartment-meet-to-address-concerns'
NP = 'raw/evidence_b11/01748de79917876d.html'
I(PK, 'Park Place Towers', 'management', '2026-04-07', grab(NP, 'News 12 first spoke to tenants at Park Place Towers in Peekskill back in January because', "but they're still having problems.", last=True), 'News 12', N1, 'building', '2026-11-15T21:21:46+00:00')
I(PK, 'Park Place Towers', 'management', '2026-04-07', grab(NP, 'Tenants brought these concerns to Peekskill City Manager', 'with violations.'), 'News 12', N1, 'building', '2026-11-15T21:21:46+00:00')
I(PK, 'Park Place Towers', 'other', '2026-04-07', grab(NP, '"Our garage doors are constantly open', 'one garage door,"'), 'News 12', N1, 'garage_or_lot', '2026-11-15T21:21:46+00:00')
I(PK, 'Park Place Towers', 'safety_incident', '2025-10-06', grab(HP, 'A female tenant of 1108 Brown St. was arrested', 'totaling over $400.'), 'Peekskill Herald', H1, 'building', '2026-11-15T21:21:30+00:00')
I(PK, 'Park Place Towers', 'safety_incident', '2025-10-06', grab(HP, 'A spreadsheet compiled by those in the building', 'a total value of $1,308.'), 'Peekskill Herald', H1, 'building', '2026-11-15T21:21:30+00:00')
I(PK, 'Park Place Towers', 'other', '2025-10-06', grab(HP, 'Security concerns include a garage door', 'lock behind you.'), 'Peekskill Herald', H1, 'garage_or_lot', '2026-11-15T21:21:30+00:00')
I(PK, 'Park Place Towers', 'management', '2025-10-06', grab(HP, 'Quality of life complaints from tenants at Park Place Tower include', 'in the summer'), 'Peekskill Herald', H1, 'building', '2026-11-15T21:21:30+00:00')
I(PK, 'Park Place Towers', 'management', '2025-10-06', grab(HP, 'Alma Realty was also sued by New York City in 2023', 'in 13 buildings.'), 'Peekskill Herald', H1, 'management_company', '2026-11-15T21:21:30+00:00')
HG = 'https://hgar.com/wro-alleges-rockland-county-apartment-complex-discriminated-against-people-with-mental-disabilities'
I('1 kensington cir|10923', 'Tor View Village Apartments', 'other', '2020-03-11', grab('raw/evidence_b11/4ceec6a3c563c14c.html', 'During the investigation, WRO', 'three distinct agents.'),
  'HGAR Real Estate In-Depth', HG, 'management_company', '2026-11-15T21:21:49+00:00')

def first_sentences(body, n=2, cap=300):
    s = re.split(r'(?<=[.!?])\s+', body.strip())
    out = ' '.join(s[:n])
    return out if len(out) <= cap else s[0][:cap]

have_rating = set()
for r in BATCH:
    k, name = r['addr_key'], r['building_name']
    zu = ZUMPER.get(k)
    z = Z.get(zu) if zu else None
    looked = []
    if z and z.get('rating'):
        have_rating.add(k)
        revs = z['reviews']
        recent = [x for x in revs if x['date'] >= '2026-05-15']
        ratings.append(dict(addr_key=k, building_name=name, rating_source='Google rating shown on Zumper', rating_value=z['rating'], rating_scale=z['scale'], review_count=z['count'],
                            as_of_date=z['pulled'], reviews_read=len(revs), reviews_last_6_months=len(recent), negative_last_6_months=0,
                            negative_older=sum(1 for x in revs if x['rating'] <= 2), serious_issue_tags_last_6_months='', source_url=zu))
        for x in sorted(revs, key=lambda x: x['date'], reverse=True)[:3]:
            I(k, name, 'positive', x['date'], first_sentences(x['body']), 'Google review shown on Zumper (Zumper shows only the highest rated; weak evidence)', zu, 'building', z['ts'])
    else:
        looked.append(f"Zumper building page (review block empty): {zu}" if zu else 'Zumper: no building page found (city pages, address page and search)')
        if k in AL:
            looked.append(f'Apartment List page ("We are collecting reviews ... Check back soon."): {AL[k]}')
        else:
            looked.append('Apartment List: no building page found on the city page')
        looked.append('Trulia building page: carries no ratings')
        if k in SITE:
            looked.append(f'own site {SITE[k]}: no rating widget' + (' (the "Rated 5 out of 5" there is template filler)' if 'azzure' in SITE[k] else ''))
        ratings.append(dict(addr_key=k, building_name=name, rating_source='none_found', as_of_date='2026-11-15', reviews_read=0, source_url='; '.join(looked)))
    if k not in {i['addr_key'] for i in items}:
        I(k, name, 'none_found', '', 'No tenant review or news item found. Looked at: ' + '; '.join(looked or ['Zumper building page']) +
          '; one web search for the building name with tenants / news / complaints (results were listing sites only).', 'search log', page_of(r), 'building')

write('live_check_batch_11.csv', ['addr_key', 'listing_url', 'unit', 'status', 'price_now', 'available_now_text', 'matches_stored', 'building_site_url', 'checked_at', 'notes'], live)
write('confirm_batch_11.csv', ['addr_key', 'fact', 'value', 'quote', 'source_url', 'status'], conf)
write('items_batch_11.csv', ['addr_key', 'building_name', 'category', 'item_date', 'excerpt', 'source_site', 'source_url', 'about', 'retrieved_at'], items)
write('facts_batch_11.csv', ['addr_key', 'fact', 'value', 'quote', 'source_url'], facts)
write('ratings_batch_11.csv', ['addr_key', 'building_name', 'rating_source', 'rating_value', 'rating_scale', 'review_count', 'as_of_date', 'reviews_read', 'reviews_last_6_months',
                               'negative_last_6_months', 'negative_older', 'serious_issue_tags_last_6_months', 'source_url'], ratings)
