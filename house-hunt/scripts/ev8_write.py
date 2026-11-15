"""Evidence batch 8: rebuild live_check / confirm / items / facts / ratings CSVs from cached pages (no network).
Inputs: raw/evidence_b8/{trulia_parsed,al_parsed,al_reviews,zumper_bld}.json (made by ev8_trulia_parse.py, ev8_al_parse.py, ev8_zumper.py)
plus the hand-read findings below (own-site pages cached in raw/evidence_b8/). Idempotent: overwrites only *_batch_8.csv."""
import csv, json, re, datetime as dt
R = 'raw/evidence_b8/'
T = json.load(open(R + 'trulia_parsed.json')); A = json.load(open(R + 'al_parsed.json'))
ALR = json.load(open(R + 'al_reviews.json')); Z = json.load(open(R + 'zumper_bld.json'))
rows = list(csv.DictReader(open('data/reference/evidence_batches/batch_8.csv')))
NOW = '2026-11-15'; CUT = dt.date(2026, 5, 15)
money = lambda s: int(re.sub(r'[^\d]', '', str(s))) if s and re.sub(r'[^\d]', '', str(s)) else None

SITE = {  # building's own site (read or attempted)
 '740-748 washington ave|07109': 'https://www.ethoskelsey.com/', '500 district dr|07922': 'https://rt500residences.com/',
 '1 avalon way|07005': 'https://www.avaloncommunities.com/new-jersey/boonton-apartments/avalon-boonton/',
 '36 washington ave|07008': 'https://www.livethebotanic.com/ (HTTP 403, not read)', '2 river rd|07928': 'https://www.theivychatham.com/ (HTTP 403, not read)',
 '540 main st 9f|07928': 'https://springbrookchatham.com/', '540 main st|07928': 'https://springbrookchatham.com/',
 '51 lincoln ave|07050': 'https://www.liabyvermella.com/ (challenge page, not read)', '80 e mcfarlan st|07801': 'https://www.80eastdover.com/',
 '240 s harrison st|07018': 'https://www.aura240.com/ (JavaScript only)', '5 lawrence st|07003': 'https://www.parkwaylofts.com/',
 '500 n ave|07027': 'https://www.garwoodlofts2.com/ (HTTP 403, not read)', '90 lupton ln|07508': 'https://www.haledonestates.com/',
 '132 yale ave|07304': 'https://www.theagnes.com/ (HTTP 403, not read)', '161 van wagenen ave|07306': 'https://www.metrovuejc.com/ (no policy text)',
 '55 jordan ave|07306': 'https://www.55jordan.com/', '19 rock st|07306': 'https://www.19rock.com/ (JavaScript only)',
 '26 brook st|07302': 'https://www.skylarloftsjc.com/ (no policy text)', '76 cottage st|07306': 'https://www.appletreesuites.com/ (JavaScript only)',
 '156 e cedar st|07039': 'https://www.goldberg-realty.com/nj/livingston/cedar-street-commons/index.aspx (HTTP 403, not read)',
 '51 okner pkwy|07039': 'https://www.canterlyplace.com/ (no policy text)', '2 s willow st|07042': 'https://www.twosouthwillow.com/ (no policy text)',
 '10 ridgedale ave|07940': 'https://www.kriegmanandsmith.com/ (no policy text)',
}
# dog weight: (value, quote, source_url, status)
PW = 'https://www.parkwaylofts.com/amenities/'; HE = 'https://www.haledonestates.com/amenities/'; SB = 'https://springbrookchatham.com/faq/'
AV = 'https://www.avaloncommunities.com/new-jersey/boonton-apartments/avalon-boonton/'
WEIGHT = {
 '240 s harrison st|07018': ('25', 'Small Pets Welcome! 25lb weight limit for dogs. Max 2 pets per apartment. $600 Non-refundable pet fee. $75 Pet Rent.', None, 'confirmed'),
 '500 n ave|07027': ('25', 'Apartment List pet policy, restrictions field: "25 lbs"', None, 'confirmed'),
 '10 ridgedale ave|07940': ('45', 'Trulia pet policy: Weight limit (lbs.) 45', None, 'confirmed'),
 '90 lupton ln|07508': ('50', 'Limit 1 cat and/or dog per apartment up to 50 pounds. No exotic animals.', HE, 'confirmed'),
 '5 lawrence st|07003': ('65', 'We are pet-friendly with an aggressive breed restriction. Limit of 2 pets per home. Maximum adult weight is 65 pounds.', PW, 'confirmed'),
 '77-81 s st|07728': ('75', 'Trulia pet policy: Weight limit (lbs.) 75', None, 'confirmed'),
 '540 main st 9f|07928': ('no limit', 'There are no weight restrictions. However, certain breed and age restrictions apply.', SB, 'confirmed'),
 '540 main st|07928': ('no limit', 'There are no weight restrictions. However, certain breed and age restrictions apply.', SB, 'confirmed'),
 '1 avalon way|07005': ('no limit stated', 'Own-site data: "maximumPets":2,"maximumPetWeight":0; "Cats and dogs are welcome. Please check the dog breed and pet restrictions below." Restricted breeds include German Shepherds.', AV, 'confirmed'),
 '156 e cedar st|07039': ('unconfirmed', 'Apartment List pet policy, restrictions field: "Breed and Weight Restrictions" (no number)', None, 'unconfirmed'),
}
# floor of each stored unit: (value, status, quote)
FLOOR = {
 ('1 avalon way|07005', '1177'): ('1', 'contradicts', 'AvalonBay unit data: "unitName":"1177" ... "floorNumber":"1" (ground floor: fails the no-ground-floor gate)', AV),
 ('1 avalon way|07005', '2154'): ('2', 'confirmed', 'AvalonBay unit data: "unitName":"2154" ... "floorNumber":"2"', AV),
}
INFER = {'526': 5, '320': 3, '917': 9, '617': 6, '430': 4, '245': 2, '621': 6, '333': 3, '423': 4, '308': 3, '413': 4, '3CW': 3, '5CE': 5,
         '736': 7, '1612': 16, '203': 2, '311': 3, '201': 2, '301': 3, '411': 4, '2B': 2, '3B': 3, '505': 5, '418': 4, '2001': 2, '3024': 3, '508': 5, '547': 5}
ELEV_EXTRA = {'161 van wagenen ave|07306': 'Welcome to Metrovue, a 13-story, 124-unit luxury high-rise that redefines modern living in the heart of Journal Square, Jersey City.'}
LIVE_NOTE = {
 '500 district dr|07922': 'Apartment List total with required monthly fees is $110 higher; lease length shown 24 months',
 '1 avalon way|07005': 'AvalonBay site confirms price; total with required fees is $85 higher; starting price is for a 10-month (1177) or 20-month (2154) term; unit 1177 is on floor 1',
 '36 washington ave|07008': 'price up $9 since stored; Apartment List total with required fees is $97.55 higher',
 '2 river rd|07928': 'total with required fees $2,809; 18-month lease; shown as available since 2026-07-17',
 '51 lincoln ave|07050': '15-month lease price; required fees shown as $0',
 '416 highland ave|07050': 'page gives no unit number (title says 312); feed from Buildium, last updated 2026-11-12',
 '240 s harrison st|07018': 'floor-plan level only: Trulia lists 0 available units for the building; no unit number',
 '55 jordan ave|07306': 'floor-plan level only (plan named "304"): Trulia lists 0 available units for the building',
 '161 van wagenen ave|07306': 'Trulia tags the building Furnished',
 '76 cottage st|07306': 'Trulia tags the building Furnished',
 '156 e cedar st|07039': 'age-restricted: 62+ senior housing (Apartment List occupancy type "senior")',
 '51 okner pkwy|07039': 'unit 2001 shown as available since 2026-04-02, unit 3024 since 2026-09-01',
 '2 s willow st|07042': 'Apartment List total with required fees is $57.14 higher; 508 available since 2026-08-29, 547 since 2026-07-09',
 '80 e mcfarlan st|07801': '46 of 90 units listed as available',
}
live, conf, facts, items, ratings = [], [], [], [], []
def fact(k, f, v, q, u):
    if v not in (None, '', [], 'None'): facts.append([k, f, v, q or '', u])

def trulia_units(rec):
    out = {}
    for p in rec['units']:
        pr = (p.get('priceRange') or {}).get('formattedPrice')
        out['PLAN:' + (p.get('name') or '')] = (pr, p.get('availabilityText'), None, (p.get('bedrooms') or {}).get('formattedValue'))
        for x in p.get('units') or []:
            xp = (x.get('price') or x.get('priceRange') or {}).get('formattedPrice') or pr
            out[re.sub(r'^Unit ', '', x.get('name') or '')] = (xp, x.get('availabilityText'), (x.get('availabilityDate') or '')[:10], None)
    return out

for r in rows:
    k, name, u = r['addr_key'], r['building_name'], r['building_url']
    units = [x.strip() for x in r['unit_list'].split(',')]; rents = [x.strip() for x in r['rents'].split(',')]
    site = SITE.get(k, 'not found')
    note0 = LIVE_NOTE.get(k, '')
    if u in T:
        rec = T[u]; tu = trulia_units(rec); ts = rec['ts']
        plans = [(kk, v) for kk, v in tu.items() if kk.startswith('PLAN:')]
        for un, st in zip(units, rents):
            hit = tu.get(un)
            if not hit:  # plan-level listing: match on stored price
                c = [(kk, v) for kk, v in plans if money(v[0]) == int(st) and (v[3] or '').lower() in ('1bd', 'studio')]
                hit = c[0][1] if c else None; un2 = (c[0][0][5:] + ' (floor plan)') if c else un
            else: un2 = un
            if not hit: live.append([k, u, un, 'gone', '', '', 'no', site, ts, 'unit not on the building page ' + note0]); continue
            pn = money(hit[0]); m = pn == int(st)
            live.append([k, u, un2, 'live' if m else 'changed', pn, (hit[1] or '') + (f' ({hit[2]})' if hit[2] else ''), 'yes' if m else 'no', site, ts, note0])
        # confirm
        f = rec['feats']; el = any(re.search(r'Accessibility: Elevator', x) for x in f)
        q = ELEV_EXTRA.get(k)
        conf.append([k, 'elevator', 'yes' if el else 'unknown', ('Trulia building features: "Elevator"' + ('; ' + q if q else '')) if el else 'no elevator line among the Trulia building features', u, 'confirmed' if el else 'unconfirmed'])
        if q: conf.append([k, 'building_floors', '13', q, u, 'confirmed'])
        cards = [c for c in ((rec['pet2'] or {}).get('cards') or []) if c['species'] == 'DOGS']
        pt = (rec['pet'] or {}).get('formattedPetsAllowed') or ''
        dq = pt + ('; dog card: ' + '; '.join(f"{x['label']} {x['value']}" for x in cards[0].get('facts') or []) if cards else '')
        conf.append([k, 'dogs_allowed', 'yes' if cards and cards[0]['status'] == 'ALLOWED' else 'unknown', dq, u, 'confirmed' if cards else 'unconfirmed'])
        w = WEIGHT.get(k)
        if w: conf.append([k, 'dog_weight_limit', w[0], w[1], w[2] or u, w[3]])
        else:
            size = next((x['value'] for x in (cards[0].get('facts') or []) if x['label'] == 'Size allowed'), '') if cards else ''
            conf.append([k, 'dog_weight_limit', 'unconfirmed', f'Trulia: "{pt}" (size allowed: {size}); no weight in pounds on the page or on the building site', u, 'unconfirmed'])
        # facts
        fact(k, 'management_company', (rec['mgmt'] or {}).get('name'), 'Trulia: property management company', u)
        ud = rec['unitDetails'] or {}
        fact(k, 'total_units', ud.get('totalUnitsInBuilding'), 'Trulia unit details', u); fact(k, 'available_units_listed', ud.get('availableRentalUnits'), 'Trulia unit details', u)
        for x in f:
            s = x.split(' > ')[-1]
            if re.search(r'Parking|Garage', x) and not s.startswith('Special'): fact(k, 'parking', s.split(': ', 1)[-1], s, u)
            if 'Rent Includes' in x: fact(k, 'utilities_included', s.split('=', 1)[-1], s, u)
            if s.startswith('Pool: Pool'): fact(k, 'pool', 'yes (type not stated)', s, u)
            if 'Deposit Fee' in x: fact(k, 'deposit', s.split('=', 1)[-1], s, u)
            if s.startswith('Rental Terms, Policies & Fees: Furnished'): fact(k, 'furnished', 'yes', s, u)
        fees = ((rec['fees'] or {}).get('costAndFeeCalculator') or {}).get('fees') or {}
        for grp, lst in fees.items():
            if not isinstance(lst, list): continue
            for x in lst:
                dv = x['fee'].get('displayValue') or ''
                if dv in ('Rent', 'Monthly base rent'): continue
                amt = (x['fee'].get('amount') or {}).get('displayText') or x['fee'].get('min')
                fact(k, 'fee:' + grp, dv, f'Trulia costs and fees: {dv} = {amt}', u)
        if cards:
            for x in cards[0].get('facts') or []:
                if x['label'] in ('Monthly dog rent', 'One-time fee', 'Dog deposit', 'Number allowed'): fact(k, 'dog:' + x['label'].lower().replace(' ', '_'), x['value'], f"Trulia pet policy: {x['label']} {x['value']}", u)
        for o in rec['offers'] or []: fact(k, 'special_offer', re.sub(r'\s+', ' ', o.get('description', ''))[:200], (o.get('subText') or ''), u)
        d = rec['desc'] or ''
        for pat, fn in [(r'[^.\n]*concierge[^.\n]*', 'concierge'), (r'[^.\n]*attended lobby[^.\n]*', 'attended_lobby')]:
            mm = re.search(pat, d, re.I)
            if mm: fact(k, fn, 'yes', mm.group(0).strip()[:250], u)
        fact(k, 'listing_last_modified', (rec['mod'] or '')[:10], 'Trulia activeListing.lastDateModified', u)
    else:
        L = A[u]['L']; ts = A[u]['ts']; au = {}
        for fp in L['available_units']:
            for x in fp.get('units') or []: au[x['name']] = x
        for un, st in zip(units, rents):
            x = au.get(un)
            if not x: live.append([k, u, un, 'gone', '', '', 'no', site, ts, 'unit not on the page ' + note0]); continue
            m = int(x['price']) == int(st)
            n = note0 + (f"; total with required fees ${x['total_price']}" if x.get('total_price') and x['total_price'] != x['price'] else '')
            live.append([k, u, un, 'live' if m else 'changed', x['price'], ('available now, since ' if x.get('available_now') else 'available ') + (x.get('available_on') or ''), 'yes' if m else 'no', site, ts, n.strip('; ')])
        am = [(a.get('display_name') or a.get('name')) if isinstance(a, dict) else a for a in (L.get('community_amenities') or []) + (L.get('unit_amenities') or [])]
        el = 'Elevator' in am
        conf.append([k, 'elevator', 'yes' if el else 'unknown', 'Apartment List amenities: "Elevator"' if el else 'no elevator among the Apartment List amenities; building site did not state it', u, 'confirmed' if el else 'unconfirmed'])
        pp = L.get('pet_policies') or {}; g = pp.get('general') or {}
        da = pp.get('allowed') or ('Dogs allowed' in am)
        conf.append([k, 'dogs_allowed', 'yes' if da else 'unknown', 'Apartment List: ' + ('pet policy allowed=true; ' if pp.get('allowed') else '') + ('amenity "Dogs allowed"' if 'Dogs allowed' in am else ''), u, 'confirmed' if da else 'unconfirmed'])
        w = WEIGHT.get(k)
        if w: conf.append([k, 'dog_weight_limit', w[0], w[1], w[2] or u, w[3]])
        else: conf.append([k, 'dog_weight_limit', 'unconfirmed', 'Apartment List pet policy gives no weight' + (f' (restrictions: {g.get("restrictions")})' if g.get('restrictions') else '') + '; building site not readable or silent', u, 'unconfirmed'])
        fact(k, 'management_company', L.get('pmc_display_name'), 'Apartment List pmc_display_name', u); fact(k, 'year_built', L.get('year_built'), 'Apartment List year_built', u)
        fact(k, 'total_units', L.get('total_units_count'), 'Apartment List total_units_count', u)
        cl = lambda s: re.sub(r'\$\$', '$', str(s)).strip() if s else s
        fact(k, 'pet_rent', cl(g.get('rent')), 'Apartment List pet policy (general): rent', u); fact(k, 'pet_fee', cl(g.get('fee')), 'Apartment List pet policy (general): fee', u)
        fact(k, 'pet_limit', cl(g.get('limit')), 'Apartment List pet policy (general): limit', u); fact(k, 'pet_restrictions', cl(g.get('restrictions')), 'Apartment List pet policy (general): restrictions', u)
        for sp in ('dogs', 'cats'):
            if (pp.get(sp) or {}).get('rent'): fact(k, sp + '_rent', cl(pp[sp]['rent']), f'Apartment List pet policy ({sp}): rent', u)
        pk = '; '.join(filter(None, [p.get('category') or '' for p in L.get('parking') or []] + [p.get('comment') or '' for p in L.get('parking') or []]))
        fact(k, 'parking', pk, 'Apartment List parking', u)
        for fn in ('deposit_fee_text', 'application_fee_text', 'additional_fees_text', 'move_in_fees_text', 'lease_terms_text'): fact(k, fn.replace('_text', ''), cl(L.get(fn)), 'Apartment List ' + fn, u)
        rf = {x.get('required_fees') for x in au.values() if x.get('required_fees')}
        if rf: fact(k, 'required_monthly_fees', '; '.join(str(x) for x in sorted(rf)), 'Apartment List unit data: required_fees (total_price minus base_price)', u)
        for a_, fn in [('Pool', 'pool'), ('Concierge', 'concierge'), ('24hr concierge', 'concierge'), ('Garage', 'garage')]:
            if a_ in am: fact(k, fn, 'yes' + (' (type not stated)' if fn == 'pool' else ''), f'Apartment List amenity "{a_}"', u)
        if L.get('occupancy_types'): fact(k, 'occupancy_type', ','.join(L['occupancy_types']), 'Apartment List occupancy_types', u)
        fact(k, 'listing_updated_at', (L.get('updated_at') or '')[:10], 'Apartment List updated_at', u)
    for un in units:
        fl = FLOOR.get((k, un))
        if fl: conf.append([k, 'floor', f'unit {un}: {fl[0]}', fl[2], fl[3], fl[1]])
        elif un in INFER: conf.append([k, 'floor', f'unit {un}: {INFER[un]} (inferred)', f'inferred from the unit number {un}; no page states the floor', u, 'unconfirmed'])
        else: conf.append([k, 'floor', f'unit {un}: unknown', f'unit label "{un}" does not reveal the floor and no page states it', u, 'unconfirmed'])

# hand-read facts from own sites and Zumper
X = lambda k, f, v, q, u: facts.append([k, f, v, q, u])
X('500 district dr|07922', 'management_company', 'Greystar', 'RT 500 Residences is professionally managed by Greystar.', 'https://rt500residences.com/faqs/')
X('500 district dr|07922', 'parking', 'private garage, EV charging; fee not stated', 'Yes. RT 500 offers private garage parking as well as EV charging stations for electric vehicle owners.', 'https://rt500residences.com/faqs/')
X('1 avalon way|07005', 'required_monthly_fees', '85', 'AvalonBay unit data: price 2535, totalPrice 2620 (unit 1177); price 2010, totalPrice 2095 (unit 2154)', AV)
X('1 avalon way|07005', 'restricted_breeds', 'Akitas; Alaskan Malamutes; American Bull Dogs; American Staffordshire Terriers; Argentine Dogos; Bull Mastiffs; Cane Corsos; Doberman Pinschers; Fila Brasileiros; German Shepherds; Pit Bulls; Presa Canarios; Rottweiler; Staffordshire Bull Terriers; Tosa Inus; Wolf Hybrids; mixes', 'The following breeds are restricted', AV)
X('1 avalon way|07005', 'pool', 'outdoor', 'Community amenities include a fitness center, outdoor pool, resident lounge, and courtyard with gas grills.', 'https://www.apartmentlist.com/nj/boonton/avalon-boonton')
for kk in ('540 main st 9f|07928', '540 main st|07928'):
    X(kk, 'pet_fee', '$250 per pet one-time; $50 per pet monthly', 'A $250 one-time pet fee per pet is due at move-in, along with $50 monthly pet rent per pet.', SB)
    X(kk, 'parking', 'on-site parking free; private garages from $99/month', 'Residents enjoy access to on-site parking at no additional cost. Private garages are also available for rent starting at $99 per month, subject to availability.', SB)
    X(kk, 'guest_parking', 'none on site', 'Guest parking is not available on-site.', SB)
X('80 e mcfarlan st|07801', 'pet_fee', '$500 non-refundable deposit; $50 monthly', 'A $500 non-refundable pet deposit applies, along with a $50 monthly pet fee.', 'https://www.80eastdover.com/')
X('80 e mcfarlan st|07801', 'parking', 'on-site parking and EV charging; fee not stated', 'The community provides convenient on-site parking and EV charging stations, making commuting and everyday travel effortless.', 'https://www.80eastdover.com/')
X('5 lawrence st|07003', 'pet_fee', '$500 per pet non-refundable; $75 per pet monthly; limit 2', 'Limit of 2 pets per home. Maximum adult weight is 65 pounds. Non-refundable pet fee is $500 per pet. Monthly pet rent of $75 will be charged per pet.', PW)
X('5 lawrence st|07003', 'management_company', 'AJH Management (named in a resident testimonial on the building site; start date not given)', "it's only gotten better and better since AJH management placed Melanie and her team in place", 'https://www.parkwaylofts.com/')
X('5 lawrence st|07003', 'concierge', 'yes', '24/7 Concierge', 'https://www.parkwaylofts.com/')
X('90 lupton ln|07508', 'pet_fee', '$300 registration; $50 per pet monthly; limit 1 pet', 'Non-refundable registration fee of $300. Monthly fee $50 per pet.', HE)
X('90 lupton ln|07508', 'parking', 'free', 'Haledon Estates Apartments offer free vehicle parking for our residents.', HE)
X('90 lupton ln|07508', 'year_built', '1965', 'Zumper building data: year_built 1965', Z['90 lupton ln|07508']['url'])
X('76 cottage st|07306', 'year_built', '2021', 'Zumper building data: year_built 2021', Z['76 cottage st|07306']['url'])
X('36 washington ave|07008', 'required_monthly_fees', '$295 flat utilities fee (Zumper); $97.55 required fees (Apartment List): the two sources differ', 'Zumper fees: Utilities, "Flat rate to cover electricity, Internet etc.", 29500 cents', Z['36 washington ave|07008']['url'])

# ratings and review items from Zumper (Google reviews shown there)
SER = [('unresponsive_management', r'unresponsive|no transparency|will not update|never (called|respond)'), ('pests', r'roach|mice|bed ?bug|rodent'), ('mold', r'\bmold'), ('no_heat_hot_water', r'no (heat|hot water)'),
       ('elevator_outage', r'elevator.{0,40}(broken|out)'), ('car_break_in', r'broken into|break-?in'), ('package_theft', r'package.{0,30}stolen|stolen package'), ('fees_or_deposit', r'deposit|hidden fee'), ('noise', r'nois')]
rated = set()
for k, v in Z.items():
    g = ((v.get('reviews') or {}).get('sources') or {}).get('google') if v.get('status') == 200 else None
    if not g: continue
    nm = next(r['building_name'] for r in rows if r['addr_key'] == k); rated.add(k)
    rv = g.get('reviews') or []; asof = dt.datetime.fromtimestamp(g['lastPulled'], dt.timezone.utc).date().isoformat()
    rec6 = neg6 = negold = 0; tags = set(); pos = 0
    for x in sorted(rv, key=lambda x: -x['date']):
        d = dt.datetime.fromtimestamp(x['date'], dt.timezone.utc).date(); body = re.sub(r'\s+', ' ', x['body']).strip()
        neg = x['rating'] <= 2
        if d >= CUT:
            rec6 += 1; neg6 += neg
            if neg: tags |= {t for t, p in SER if re.search(p, body, re.I)}
        elif neg: negold += 1
        sents = [t for t in re.split(r'(?<=[.!?])\s+', body) if not re.search(r'\b(Jeff|John|Barry|Thalia|Alex|Marino|Maylene|Jameria|Megan|Ian|Rene|Mu|Mark)\b', t)]; ex = ' '.join(sents[:2])[:300]
        if not ex: continue
        if neg: items.append([k, nm, 'management', d.isoformat(), ex, f'Google review ({x["rating"]} stars) shown on Zumper', v['url'], 'management_company', v['at']])
        elif pos < 2:
            pos += 1; items.append([k, nm, 'positive', d.isoformat(), ex, f'Google review ({x["rating"]} stars) shown on Zumper', v['url'], 'building', v['at']])
    src = 'Google rating shown on Zumper' + (' (Zumper page is titled 100 Daibes Ct; reviews name the Riello)' if k.startswith('99 gorge') else '')
    ratings.append([k, nm, src, g['aggregateRating'], g['ratingScale'], g['reviewCount'], asof, len(rv), rec6, neg6, negold, ';'.join(sorted(tags)), v['url']])
rs = ALR.get('https://www.apartmentlist.com/nj/boonton/avalon-boonton')
ratings.append(['1 avalon way|07005', 'Avalon Boonton', "building's own site (AvalonBay page, JSON-LD aggregateRating)", 4.3, 5, 256, NOW, 0, '', '', '', '', AV])
ratings.append(['1 avalon way|07005', 'Avalon Boonton', 'Apartment List', rs['overall'], 5, rs['rating_count'], rs['snippet_submit_date'][:10], 1, 0, 0, 0, '', 'https://www.apartmentlist.com/nj/boonton/avalon-boonton'])
items.append(['1 avalon way|07005', 'Avalon Boonton', 'positive', rs['snippet_submit_date'][:10], rs['snippet'], 'Apartment List verified review (5 stars)', 'https://www.apartmentlist.com/nj/boonton/avalon-boonton', 'building', A['https://www.apartmentlist.com/nj/boonton/avalon-boonton']['ts']])
for kk in ('540 main st 9f|07928', '540 main st|07928'):
    ratings.append([kk, 'Spring Brook at Chatham', "building's own site widget (\"From Over 2900 Reviews\"; a 35-unit listing cannot have 2,900 reviews, so this is probably company-wide)", 5, 5, 2900, NOW, 0, '', '', '', '', 'https://springbrookchatham.com/'])
rated |= {'1 avalon way|07005', '540 main st 9f|07928', '540 main st|07928'}
itemed = {i[0] for i in items}
NEWS = {'740-748 washington ave|07109', '500 district dr|07922', '1 avalon way|07005', '36 washington ave|07008', '2 river rd|07928', '51 lincoln ave|07050', '240 s harrison st|07018', '299 s harrison st|07018',
        '5 lawrence st|07003', '99 gorge rd|07020', '90 lupton ln|07508', '132 yale ave|07304', '161 van wagenen ave|07306', '55 jordan ave|07306', '2 s willow st|07042', '51 okner pkwy|07039', '26 brook st|07302',
        '19 rock st|07306', '134 baldwin ave|07306', '500 n ave|07027', '10 ridgedale ave|07940', '156 e cedar st|07039', '540 main st 9f|07928', '540 main st|07928', '416 highland ave|07050', '80 e mcfarlan st|07801',
        '77-81 s st|07728', '76 cottage st|07306', '83 87 forest st|07042'}
for r in rows:
    k, u = r['addr_key'], r['building_url']; z = Z.get(k, {})
    zs = f"Zumper page {z.get('url')} ({'no review block' if z.get('status') == 200 else 'HTTP ' + str(z.get('status'))})"
    looked = f"{'Apartment List reviews section (\"collecting reviews\")' if 'apartmentlist' in u else 'Trulia building page (carries no reviews)'}; {zs}; own site: {SITE.get(k, 'not found')}"
    if k not in rated: ratings.append([k, r['building_name'], 'none_found', '', '', '', NOW, 0, '', '', '', '', looked])
    if k not in itemed:
        items.append([k, r['building_name'], 'none_found', '', 'No dated tenant or public evidence found. Looked: ' + looked + ('; web news search for the building name and address (no incident, lawsuit or complaint coverage of this building)' if k in NEWS else ''), 'search log', u, 'building', NOW + 'T22:00:00+00:00'])
    elif k in NEWS:
        items.append([k, r['building_name'], 'none_found', '', 'News search for the building name and address found no incident, lawsuit or complaint coverage (car crime, elevator, safety).', 'search log', u, 'building', NOW + 'T22:00:00+00:00'])

def w(name, head, data):
    with open(f'data/evidence/{name}_batch_8.csv', 'w', newline='') as f:
        cw = csv.writer(f); cw.writerow(head); cw.writerows(data)
    print(name, len(data))
w('live_check', 'addr_key,listing_url,unit,status,price_now,available_now_text,matches_stored,building_site_url,checked_at,notes'.split(','), live)
w('confirm', 'addr_key,fact,value,quote,source_url,status'.split(','), conf)
w('items', 'addr_key,building_name,category,item_date,excerpt,source_site,source_url,about,retrieved_at'.split(','), items)
w('facts', 'addr_key,fact,value,quote,source_url'.split(','), facts)
w('ratings', 'addr_key,building_name,rating_source,rating_value,rating_scale,review_count,as_of_date,reviews_read,reviews_last_6_months,negative_last_6_months,negative_older,serious_issue_tags_last_6_months,source_url'.split(','), ratings)
