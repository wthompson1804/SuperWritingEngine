"""Evidence batch 16: rebuild the five CSVs in data/evidence from cached pages (no network).
Inputs: scratch trulia_parsed.json (pages refetched 2026-11-15 22:47 UTC), trulia_stored.json (the earlier capture in
raw/trulia for the 12 units whose refetch was refused with HTTP 403), raw/evidence_b16/_igloo.json (Openigloo), and
hand-read facts from the other cached pages in raw/evidence_b16/. Review excerpts are checked against the cached text."""
import csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
S = Path('/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b16')
E = lib.RAW / 'evidence_b16'
OUT = lib.DATA / 'evidence'
batch = list(csv.DictReader(open(lib.DATA / 'reference/evidence_batches/batch_16.csv')))
live = json.load(open(S / 'trulia_parsed.json'))
stored = json.load(open(S / 'trulia_stored.json'))
igloo = json.load(open(E / '_igloo.json'))
pluto = {r['addr_key']: r for r in csv.DictReader(open(lib.DATA / 'reference/nyc_building_facts.csv'))}
BLOCK_AT = '2026-11-15T22:48:29+00:00'
TODAY = '2026-11-15'
FF = 'https://fairfieldproperties.com/'
GC_T = 'https://www.trulia.com/building/fairfield-metro-at-glen-cove-1100-avalon-sq-glen-cove-ny-11542-1045082049'
WM_T = 'https://www.trulia.com/building/fairfield-estates-at-woodmere-37-woodmere-blvd-woodmere-ny-11598-1001489336'
GC_S, WM_S = FF + 'fairfield-metro-at-glen-cove/', FF + 'fairfield-estates-at-woodmere/'
AL10 = 'https://www.apartmentlist.com/ny/new-york/10-park-terrace-east'
ZU10 = 'https://www.zumper.com/address/10-park-ter-e-new-york-ny-10034-usa'
ZU770 = 'https://www.zumper.com/address/770-ocean-pkwy-brooklyn-ny-11230-usa'
ZU3250 = 'https://www.zumper.com/address/32-50-93rd-st-east-elmhurst-ny-11369-usa'
H29 = 'https://29hundredbk.com/availability'
PLUTO_URL = 'https://data.cityofnewyork.us/resource/64uk-42ks.json'

def feat(r, pat):
    return [x[3] for x in r['feats'] if re.search(pat, (x[2] or '') + ' ' + (x[3] or ''), re.I)]
def fval(r, label):
    for x in r['feats']:
        if x[2] == label: return x[3]
    return ''
def norm(s): return re.sub(r'\s+', ' ', s or '').strip()
def around(desc, pat, w=75):
    """Verbatim window around the first match of pat, cut at word boundaries, with ellipses where trimmed."""
    m = re.search(pat, desc, re.I)
    if not m: return ''
    a, b = max(0, m.start() - w), min(len(desc), m.end() + w)
    while a > 0 and desc[a - 1] != ' ': a -= 1
    while b < len(desc) and desc[b] != ' ': b += 1
    return ('... ' if a > 0 else '') + desc[a:b].strip() + (' ...' if b < len(desc) else '')

# ---- floor readings: (value, status, why) ---------------------------------------------------------------
FLOOR = {
 '1710 newkirk ave|11226': ('unknown', 'unconfirmed', 'Unit is "4" with no letter; the page does not state a floor. 19 units over 5 floors (city lot data), so apartment 4 is most likely on floor 1 or 2: a ground-floor unit is possible. Ask.'),
 '1256 ocean ave|11230': ('5 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 5D in an 8-floor building reads as floor 5.'),
 '623 ave h|11230': ('6 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 6C in an 8-floor building reads as floor 6 (the description puts a sundeck on the 8th floor).'),
 '770 ocean pkwy|11230': ('2 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 2O in a 6-floor building reads as floor 2.'),
 '1941 coney island ave|11223': ('4 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 402 in a 7-floor building reads as floor 4.'),
 '2611 w 2nd st|11223': ('unknown', 'unconfirmed', 'Unit is "5" with no letter; the listing is a generic ad ("Multiple floor plans are available") for a 120-unit, 6-floor building, so the number says nothing about the floor. A ground-floor unit is possible.'),
 '2121 shore pkwy|11214': ('2 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 201 in a 6-floor building reads as floor 2.'),
 '8700 25th ave|11214': ('6 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 6G in a 7-floor building reads as floor 6.'),
 '137 w 137th st|10030': ('3 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 3D in a 6-floor building reads as floor 3.'),
 '100 w 139th st|10030': ('unknown', 'unconfirmed', 'Unit 27A cannot be floor 27: the building has 6 floors. The number is an apartment number and the page gives no floor.'),
 '2419 adam clayton powell jr blvd|10030': ('5 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 5R in a 6-floor building reads as floor 5.'),
 '10 wendell st|11550': ('unknown', 'unconfirmed', 'Unit is "20"; the page gives no floor and we have no floor count for the building.'),
 '405 w 206th st|10034': ('7 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 713E in a 17-floor building reads as floor 7, east tower.'),
 '204 sherman ave|10034': ('4', 'confirmed', ''),
 '121 seaman ave|10034': ('5 (reading)', 'unconfirmed', 'Page does not state the floor. Unit 5B in a 6-floor building reads as floor 5.'),
 '4778 broadway|10034': ('6 (reading)', 'unconfirmed', 'Earlier capture does not state the floor. Unit 6G in a 12-floor building reads as floor 6.'),
 '10 park ter e|10034': ('6 (reading)', 'unconfirmed', 'Earlier capture does not state the floor. Unit 6G in a 6-floor building reads as floor 6 (top).'),
 '3250 93rd st|11369': ('unknown', 'unconfirmed', 'Unit A3: no floor on the page. The letter is likely a wing or entrance; in a 4-floor building "3" could be the floor or the apartment number.'),
 '139-05 85th dr|11435': ('unknown', 'unconfirmed', 'Unit is "1": no floor on the page. Could well be a ground-floor apartment. Ask.'),
 '490 ocean pkwy|11218': ('unknown', 'unconfirmed', 'Unit is "64": no floor on the page. In a 7-floor building it may mean floor 6, apartment 4, but that is a guess.'),
 '3660 waldo ave|10463': ('unknown', 'unconfirmed', 'Unit J2: no floor on the page. Could be wing J, floor 2, or line J; a guess either way.'),
 '|11561': ('unknown', 'unconfirmed', 'Address and unit withheld on the listing; only the search card was ever read.'),
 '3310 nostrand ave|11229': ('5 (reading)', 'unconfirmed', 'Earlier capture does not state the floor. Unit 503 in a 6-floor building reads as floor 5.'),
 '2900 nostrand ave|11229': ('2 (reading)', 'unconfirmed', 'Earlier capture does not state the floor. Unit 2M in a 9-floor building reads as floor 2. The building\'s own availability page does not list 2M.'),
 '3280-3310 nostrand ave|11229': ('2 (reading)', 'unconfirmed', 'Earlier capture does not state the floor. Unit 202 in a 6-floor building reads as floor 2.'),
 '408 w 130th st|10027': ('unknown', 'unconfirmed', 'Unit is "61": no floor on the page. In a 6-floor building it may mean floor 6, apartment 1, but that is a guess.'),
 '1802 ocean ave|11230': ('7 (reading)', 'unconfirmed', 'Earlier capture does not state the floor. Unit 7F in an 8-floor building reads as floor 7.'),
}

lc, cf, fa = [], [], []   # live_check, confirm, facts
def add_conf(k, fact, value, quote, url, status): cf.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=url, status=status))
def add_fact(k, fact, value, quote, url): fa.append(dict(addr_key=k, fact=fact, value=value, quote=quote, source_url=url))

for b in batch:
    k = b['addr_key']; url = b['urls'].split(' | ')[0]
    if k in ('1100 avalon sq|11542', '37 woodmere blvd|11598'): continue
    r = live.get(url); from_live = r is not None
    if not from_live: r = stored.get(url)
    pf = pluto.get(k) or {}
    # ---- live check
    if from_live:
        price = int(re.sub(r'\D', '', r['price'])); avail = fval(r, 'Available')
        st = r['status'] or {}
        ok = st.get('isActiveForRent') and str(price) == b['rents'].strip()
        notes = [f"Trulia: {fval(r, 'Days on Market')}; listed {(r.get('listed') or '')[:10]}."]
        disc = norm(((r.get('fees') or {}).get('disclaimer') or {}).get('text', '')).replace('Price shown is base rent. Additional costs and fees may apply.', '').strip()
        if disc: notes.append('Price history on page: ' + disc)
        notes.append('Page says: "Price shown is base rent. Additional costs and fees may apply." No special offer on the page.')
        if k == '1941 coney island ave|11223': notes.append('Available date is Dec 15, the last day of the window.')
        if k == '10 wendell st|11550': notes.append('Listed 2026-09-24: reaches 60 days on market on Nov 23. Co-op rental, board approval, one month broker fee.')
        if k == '770 ocean pkwy|11230': notes.append('Co-op sublet: board approval, application costs $350 plus $20 credit check. Description says only "Cats allowed": see dogs_allowed.')
        if k == '8700 25th ave|11214': notes.append('Description ends with the word "Incentives" but gives no offer text.')
        lc.append(dict(addr_key=k, listing_url=url, unit=b['unit_list'], status='live' if ok else 'changed', price_now=price, available_now_text=avail,
                       matches_stored='yes' if ok else 'no', building_site_url='', checked_at=r['ts'], notes=' '.join(notes)))
    else:
        base = 'Refetch refused: Trulia returned HTTP 403 (bot wall) from 22:48 UTC; two later single retries (22:54, 22:58) also 403. Not worked around.'
        if r and not r.get('card_only'):
            base += f" Last successful read was the harvest capture at {r['stored_seen'][:16]}Z: {r['price']}, available {fval(r, 'Available')}, {fval(r, 'Days on Market')}."
        else:
            base += ' The harvest only ever read the search card for this listing (address withheld), so the price was never verified on the listing page.'
        site = ''; status = 'blocked'; price = ''; avail = ''; chk = BLOCK_AT
        if k == '10 park ter e|10034':
            base += ' Independent read: Apartment List shows one 1-bed at this address, $2,692, "Avail. now", feed updated 2026-11-15T10:30Z (unit not named), which agrees with the stored price.'
            site = AL10
        if k == '2900 nostrand ave|11229':
            base += " The building's own site (29 Hundred) lists 24 available units at 22:57 UTC and unit 2M is not among them; its cheapest 1-bed is 3A at $2,700, then 3E $2,745, 3G $2,785. Treat 2M at $2,650 as probably gone."
            site = H29
        if k == '3660 waldo ave|10463': base += ' 39 days on market at the earlier capture.'
        if k == '408 w 130th st|10027': base += ' 37 days on market at the earlier capture; available Dec 7.'
        if k == '3310 nostrand ave|11229': base += ' Earlier capture shows the price was cut by $100 on Nov 11.'
        lc.append(dict(addr_key=k, listing_url=url, unit=b['unit_list'], status=status, price_now=price, available_now_text=avail, matches_stored='',
                       building_site_url=site, checked_at=chk, notes=base))
    if not r or r.get('card_only'):
        for f in ('elevator', 'floor', 'dogs_allowed', 'dog_weight_limit'):
            add_conf(k, f, 'unknown', FLOOR[k][2] if f == 'floor' else 'Listing page never read (address withheld; search card only; refetch refused with HTTP 403).', url, 'unconfirmed')
        add_fact(k, 'building_identity', 'Surfview Towers, 25 Franklin Blvd, Long Beach (not verified)', 'Name comes from the batch file; the Trulia listing withholds the address. Zumper has an address page for 25 Franklin Blvd with no pet policy or building data.', 'https://www.zumper.com/address/25-franklin-blvd-long-beach-ny-11561-usa')
        continue
    src = url if from_live else url + ' (harvest capture ' + r['stored_seen'][:16] + 'Z; refetch blocked)'
    desc = norm(r['desc'])
    # ---- elevator
    el = feat(r, r'^\s*Elevator$|\bElevator\b')
    m = around(desc, r'\belevators?\b')
    floors = (pf.get('pluto_floors') or '')
    if k == '4778 broadway|10034': floors = '12'
    if k == '3250 93rd st|11369':
        add_conf(k, 'elevator', 'no (walk-up)', 'City tax-lot data for 32-50 93 STREET: building class C1 (walk-up apartments), 4 floors, 39 units, built 1925. Older Zumper listings for this address say "Pre-war building - Live-in super - Walk-up". The stored match to a 6-floor elevator building was the neighbouring lot (32-30 93 St). The listing itself does not mention an elevator.', PLUTO_URL + "?address=32-50 93 STREET ; " + ZU3250, 'contradicts')
    elif el:
        add_conf(k, 'elevator', 'yes' + (f' ({floors} floors per city lot data)' if floors else ''), 'Listed feature: Elevator' + (f'; description: "{m}"' if m else ''), src, 'confirmed')
    elif m:
        add_conf(k, 'elevator', 'yes' + (f' ({floors} floors per city lot data)' if floors else ''), m, src, 'confirmed')
    elif k == '770 ocean pkwy|11230':
        add_conf(k, 'elevator', 'yes (6 floors per city lot data)', 'Trulia page does not mention an elevator. Zumper building page: "Things you\'ll love: Elevator, Laundry available on site"; an older listing there reads "building with doorman, elevator, laundry on every floor".', ZU770, 'confirmed')
    else:
        add_conf(k, 'elevator', f'not stated on the listing ({floors or "?"} floors per city lot data)', 'No elevator in the feature list or description.' + (' Building has 6 or more floors, so the plan\'s asterisk rule would apply.' if floors and int(float(floors)) >= 6 else ''), src, 'unconfirmed')
    # ---- floor
    fv, fs, why = FLOOR[k]
    if k == '204 sherman ave|10034':
        add_conf(k, 'floor', '4', 'located in a prewar elevator building 4th floor', src, 'confirmed')
    else:
        add_conf(k, 'floor', fv, why, src, fs)
    # ---- dogs
    pol = feat(r, r'dogs? allowed|small dogs')
    q = pol[0] if pol else ''
    extra = re.search(r'(Small dogs or cats ok|Pets? (?:ok|allowed|welcome|friendly)|Pet[- ]friendly|Pets Allowed)', desc, re.I)
    if k == '770 ocean pkwy|11230':
        add_conf(k, 'dogs_allowed', 'contradictory: probably no dogs', 'Trulia field says "Cats, small dogs allowed", but the same listing\'s description says only "Cats allowed." Older listings for the building on Zumper say "Sorry: no dogs." and "Board approval required.No pets allowed."', url + ' ; ' + ZU770, 'contradicts')
        add_conf(k, 'dog_weight_limit', 'not stated', 'No number anywhere; co-op, so the board\'s rules govern.', url, 'unconfirmed')
    elif k == '10 park ter e|10034':
        add_conf(k, 'dogs_allowed', 'contradictory', 'Trulia field (earlier capture) says "Cats, small dogs allowed". Apartment List, same day, same broker phone: "No, 10 Park Terrace East is not pet-friendly." An older listing on Zumper: "Cats allowed; sorry, no dogs."', src + ' ; ' + AL10 + ' ; ' + ZU10, 'contradicts')
        add_conf(k, 'dog_weight_limit', 'not stated', 'No number on any page read.', src, 'unconfirmed')
    else:
        note = f'Trulia pet field: "{q}" (Dogs: Allowed, Size allowed: Small)' + (f'; description: "{extra.group(1)}"' if extra else '')
        if k == '139-05 85th dr|11435':
            note += '. Caution: this is a co-op (Manton House); a web search surfaced several sale listings saying "no pets" or "no dogs", on pages we are not allowed to read, so nothing from them is recorded as fact. Ask the board.'
        if k == '405 w 206th st|10034':
            note += '. Apartment List building page: "Yes, 405 West 206th Street is pet-friendly."'
        add_conf(k, 'dogs_allowed', 'yes (small dogs)', note, src, 'confirmed' if from_live else 'unconfirmed')
        wl = 'size-only: "small dogs", no number'
        wq = 'Passes the size-only rule; no weight in pounds is given on the page.'
        if k == '405 w 206th st|10034':
            wq += ' Lead only: a web search summary of CityRealty\'s page for Miramar mentions two pets and a 40-pound limit, but CityRealty refuses our requests (HTTP 403), so this is not confirmed.'
        add_conf(k, 'dog_weight_limit', wl, wq, src, 'unconfirmed')
    # ---- facts from the listing
    if pf.get('pluto_year') or k == '4778 broadway|10034':
        add_fact(k, 'year_built', '2023' if k == '4778 broadway|10034' else pf['pluto_year'], 'city tax-lot data (already in data/reference/nyc_building_facts.csv)' if k != '4778 broadway|10034' else 'city tax-lot data for 4778 BROADWAY: lot 1022337502, class RM, 12 floors, built 2023 (our reference file had no lot for this address)', PLUTO_URL)
    by = (r.get('provider') or {}).get('fullTextSummary') if from_live else r.get('by')
    if by: add_fact(k, 'listing_broker', norm(by[0]).replace('Listing by: ', ''), norm(by[0]), src)
    pk = feat(r, r'Garage|Parking|Valet')
    pfee = [y for s_ in ((r.get('fees') or {}).get('rentalFeeSections', []) if from_live else []) for y in s_.get('rentalFees', []) if 'Parking' in y['title']]
    if not from_live:
        pfee = [dict(title=a, formattedValue=v) for sec, items in r['fees'] for a, v in items if 'Parking' in a]
    pm = around(desc, r'\b(parking|garage)\b')
    if pk or pfee or pm:
        val = '; '.join(dict.fromkeys(pk)) or 'mentioned in description'
        if pfee: val += f"; fee {pfee[0]['formattedValue']} (optional)"
        add_fact(k, 'parking', val, pm if pm else 'feature list', src)
    for pat, name in [(r'\bdoorman\b', 'doorman'), (r'heat (?:and|&) hot water|Hot Water included|Free Heating', 'utilities_included'),
                      (r'application (?:fee|costs)', 'application_fee'), (r'broker fee', 'broker_fee'),
                      (r'rent[- ]stabilized', 'rent_stabilized'), (r'board approval', 'board_approval')]:
        mm = around(desc, pat, 60)
        if mm: add_fact(k, name, 'see quote', mm, src)
    if k == '405 w 206th st|10034':
        add_fact(k, 'building_name', 'Miramar', 'Welcome to Miramar.', src)
        add_fact(k, 'doorman', '24/7 attended lobby', '24 / 7 attended lobby Indoor parking garage Pet washing station', src)
        add_fact(k, 'other_fees', 'lockout $50 day / $100 after hours; key $25; fob $50', 'Day Hours: $50 Lockout Fee After Hours: $100 Key Replacement: $25 Key Fob Replacement: $50', src)
    if k == '1941 coney island ave|11223':
        add_fact(k, 'building_name', 'The Posh (43 units, two elevators)', 'The Posh is a finely crafted 43 unit boutique rental building located in Midwood, Brooklyn. ... Building amenities include two elevators, a fitness center, furnished roof deck', src)
    if k == '623 ave h|11230':
        add_fact(k, 'building_name', 'H7 Condominium (dog run and pet wash station)', 'Pet owners will adore the dedicated dog run and pet wash station.', src)
    if k == '2900 nostrand ave|11229':
        add_fact(k, 'building_name', '29 Hundred', '29 Hundred | Modern Apartments in Midwood, Brooklyn ... 2900 Nostrand Avenue, Brooklyn, NY, 11229', 'https://29hundredbk.com/')
        add_fact(k, 'own_site_availability', '24 units listed; 1-beds from $2,700 (3A), $2,745 (3E), $2,785 (3G), $2,850 (4B), $2,875 (5J), $2,950 (5F), $2,975 (6F); no pet policy on the site', '1 BR $2,700/mo Available Unit 3A', H29)
    if k == '770 ocean pkwy|11230':
        add_fact(k, 'last_sale', 'sold for $200,000 in April 2026', '770 Ocean Pkwy #2O in Brooklyn, NY last sold for $200,000 in April 2026.', src)
    if k == '3250 93rd st|11369':
        add_fact(k, 'building_type', '4-floor walk-up, 39 units, built 1925 (class C1); owner 32-40 AND 32-50 93RD STREET, LLC', 'city tax-lot data for 32-50 93 STREET (lot 4014220029). Our reference file had matched the neighbouring lot.', PLUTO_URL)

# ---- the two Fairfield buildings -----------------------------------------------------------------------
GC_AT, WM_AT = live[GC_T]['ts'], live[WM_T]['ts']
GC_OFFER = 'NOVEMBER-2026 FREE* Metro South Apts S1117, S1319, S1401, S1466* PLUS $150 OFF Monthly-months 2-11* Other Units GET $1000 OFF 1-TIME W/Move In By 11/24/26*. Metro North Special Apt N2322 $3550 and NOV-2026 FREE* LEASE 18 MTH NO INCREASE*$99 SEC.* *Restric'
gk, wk = '1100 avalon sq|11542', '37 woodmere blvd|11598'
for price, plan in ((2650, 'S7 North FR Studio, 570 sqft'), (2820, 'S3 South Studio, 698 sqft')):
    lc.append(dict(addr_key=gk, listing_url=GC_T, unit='', status='live', price_now=price, available_now_text='plan marked "Available Now"; no unit listed', matches_stored='yes',
                   building_site_url=GC_S, checked_at=GC_AT,
                   notes=f'Floor-plan level only: Trulia shows plan {plan} at ${price:,} "Available Now" but 0 available units of 367, so no unit, floor or date can be checked. '
                         'The building\'s own page (read 22:49 UTC) shows only "One Bedroom 1 Bath - from $2,950/mo." and no studio price, so the studio price is not confirmed by the owner\'s site. '
                         f'Special offer on Trulia, verbatim (cut off by the page): "{GC_OFFER}" / "Offer good until November 29, 2026". The page does not say whether listed prices are gross or net of the offer; they look like gross rents. '
                         'Own site still shows the previous month\'s text ("RECEIVE OCTOBER-2026 FREE* Metro South Apts S1117, S1219, S1319, S1401* PLUS $100 OFF Monthly-months 2-11*"). Trulia page last modified 2026-04-18. Confirm by phone.'))
lc.append(dict(addr_key=wk, listing_url=WM_T, unit='', status='live', price_now=2235, available_now_text='plan marked "Available Now"; no unit listed', matches_stored='yes',
               building_site_url=WM_S, checked_at=WM_AT,
               notes='Floor-plan level only: Trulia shows The Atlantic I and II studios at $2,235 "Available Now" but 0 available units of 87; the owner\'s site agrees ("Studio - from $2,235/mo."). One-beds start at $2,845 (The Woodsburgh). '
                     'Special offer, verbatim: "Inflation Buster Move-In Special Lease Choice Of 18 Months With No Increase* $99 Security* *Restrictions Apply." / "Offer good until November 30, 2026". No rent discount in the offer, so gross and net are the same. Trulia page last modified 2026-08-19.'))
add_conf(gk, 'elevator', 'yes', 'Listed feature: Elevator', GC_T, 'confirmed')
add_conf(gk, 'floor', 'unknown', 'Floor-plan level listing; no unit. The offer text names apartments S1117, S1319, S1401, S1466 and N2322, but none is tied to the studio prices.', GC_T, 'unconfirmed')
add_conf(gk, 'dogs_allowed', 'yes (small dogs)', 'Cats, small dogs allowed; Pet Policy: Restrictions Apply. FAQ: "Fairfield Metro at Glen Cove allows cats and small dogs. Large dogs are not permitted."', GC_T, 'confirmed')
add_conf(gk, 'dog_weight_limit', 'size-only: "small dogs", no number', 'The owner\'s page for this community gives no pet policy. (Its sister building in Woodmere states 30 lbs; that does not prove the same limit here.)', GC_S, 'unconfirmed')
add_conf(wk, 'elevator', 'yes', 'Historic Elevator Building with Hotel-Style Lobby', WM_S, 'confirmed')
add_conf(wk, 'floor', 'unknown', 'Floor-plan level listing; no unit.', WM_T, 'unconfirmed')
add_conf(wk, 'dogs_allowed', 'yes', 'Pet policy: Monthly fee $35 per dog/$400 pet deposit* Weight limit 30 lbs.', WM_S, 'confirmed')
add_conf(wk, 'dog_weight_limit', '30', 'Pet policy: Monthly fee $35 per dog/$400 pet deposit* Weight limit 30 lbs. $20 per cat/$300 pet deposit* Restrictions apply.', WM_S, 'confirmed')
add_fact(gk, 'management_company', 'Fairfield Properties (bought the community, then Avalon Glen Cove, in 2021 per a search result not read)', 'Property management company: Fairfield Properties (verified)', GC_T)
add_fact(gk, 'building_size', '367 units, 0 listed available', 'totalUnitsInBuilding 367; availableRentalUnits 0 (page data)', GC_T)
add_fact(gk, 'pool', 'two outdoor pools', 'Two sparkling Outdoor Swimming Pools with Sundeck', GC_S)
add_fact(gk, 'doorman', 'concierge, AM/PM', 'AM/PM Concierge attended Grand Lobbies', GC_S)
add_fact(gk, 'parking', 'garage; fee not stated', 'Parking Fees Apply. Contact Us For Details.', GC_T)
add_fact(gk, 'special_offer', 'see quote; gross or net not stated', GC_OFFER + ' (Offer good until November 29, 2026)', GC_T)
add_fact(gk, 'deposit', '$99 with the special', 'All Apts Inflation Buster Lease Special 18-Mth NO INCREASE* $99 Security* *Restrictions Apply.', GC_S)
add_fact(wk, 'management_company', 'Fairfield Properties', 'Property management company: Fairfield Properties (verified)', WM_T)
add_fact(wk, 'building_size', '87 units, 0 listed available', 'totalUnitsInBuilding 87; availableRentalUnits 0 (page data)', WM_T)
add_fact(wk, 'pet_rent', '$35 per dog per month; $400 pet deposit', 'Pet policy: Monthly fee $35 per dog/$400 pet deposit* Weight limit 30 lbs.', WM_S)
add_fact(wk, 'utilities_included', 'gas heat and hot water', 'Utilities: Gas heat and hot water included.', WM_S)
add_fact(wk, 'lease_terms', 'one or two years', 'Lease term: One or two year lease with per month increase for second year.*', WM_S)
add_fact(wk, 'deposit', '$99 with excellent credit', 'Security deposit: $99 Security Deposit Special with excellent credit and financial history. *Restrictions apply.', WM_S)
add_fact(wk, 'special_offer', 'no rent discount (lease-length and deposit only)', 'Inflation Buster Move-In Special Lease Choice Of 18 Months With No Increase* $99 Security* *Restrictions Apply. (Offer good until November 30, 2026)', WM_T)
add_fact(wk, 'parking', 'not stated', 'Neither the owner\'s page nor Trulia mentions parking.', WM_S)

# ---- Openigloo ------------------------------------------------------------------------------------------
IG = {}   # addr_key -> dict(url, at, agg, reviews, text)
for k, o in igloo.items():
    for p in o.get('pages', []):
        if p.get('status') == 200:
            IG[k] = dict(url=p['fetched'], at=p['retrieved_at'], agg=p.get('agg'), reviews=p.get('reviews') or [], in_sitemap=p.get('in_sitemap'))
U623 = 'https://www.openigloo.com/building/nyc/3170090-3064940032/brooklyn-flatbush-623-avenue-h-11230'
t623 = (E / [json.loads(l)['path'].split('/')[-1] for l in open(E / '_index.jsonl') if U623 in l][-1]).read_text(errors='replace')
r623 = []
for j in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', t623, re.S):
    def walk(x):
        if isinstance(x, dict):
            if x.get('@type') == 'Review': r623.append({'date': x.get('datePublished'), 'body': x.get('reviewBody'), 'rating': (x.get('reviewRating') or {}).get('ratingValue')})
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(json.loads(j))
IG['623 ave h|11230'] = dict(url=U623, at='2026-11-15T22:54:02+00:00', agg={'ratingValue': 4.62, 'reviewCount': 1}, reviews=r623, in_sitemap=True)

names = {b['addr_key']: (b['building_name'] or b['address']) for b in batch}
IMPORT = '2021-11 or earlier (Openigloo bulk-import date 2021-11-16)'
# (addr_key, category, date ('' = take from the matching review), about, excerpt)
ITEMS = [
 ('1710 newkirk ave|11226', 'elevator', '', 'building', 'Elevator (breaks down occasionally)'),
 ('1710 newkirk ave|11226', 'management', '', 'building', 'Heating is my biggest complaint - the building is very drafty and central heating unit feels not so efficient, makes gas bill quite high in the winter'),
 ('1710 newkirk ave|11226', 'safety_incident', '', 'building', "Drug Addicts squat in the building. They yell for extended periods of time and at random hours. Owner does nothing and won't even acknowledge the problem"),
 ('1710 newkirk ave|11226', 'safety_incident', '', 'building', 'Any and all packages will be stolen if you do not immediately pick them up'),
 ('1710 newkirk ave|11226', 'elevator', '', 'building', 'elevator often out, but you get what you pay for'),
 ('1256 ocean ave|11230', 'management', '', 'building', 'there are constantly pests, roaches, mice, everything. I was on the 8th floor and even then I had all the above.'),
 ('1256 ocean ave|11230', 'management', '', 'management_company', 'Went without heat sometimes, water randomly shutting off, etc.'),
 ('1256 ocean ave|11230', 'management', '', 'building', 'We have had a mouse issue since we moved in two years. They bring an exterminator in once people complain, but all they do is hand us traps and throw a few pieces of poison behind the stove.'),
 ('1256 ocean ave|11230', 'management', '', 'management_company', 'The trade off is you will be dealing with a terrible management, mice and flies.'),
 ('1256 ocean ave|11230', 'management', '', 'building', 'Living with mice, they’re in the walls and on the ceiling constantly walking around.'),
 ('1256 ocean ave|11230', 'positive', '', 'building', 'gym, nice rooftop, spacious apt, rent stabilized'),
 ('623 ave h|11230', 'positive', '', 'building', 'I love that I have a balcony, and the air conditioning in my unit is awesome.'),
 ('2611 w 2nd st|11223', 'management', '', 'management_company', 'Difficult to get ahold of management, have to leave messages and sometimes they just dismiss or never respond when reporting important issues like big leaks and persistent roach issues.'),
 ('2121 shore pkwy|11214', 'management', '', 'building', 'Heat and insulation is bad'),
 ('8700 25th ave|11214', 'other', '', 'building', 'Windows need to get replaced'),
 ('137 w 137th st|10030', 'management', '', 'building', 'We’ve not had heat or hot water for months. The boiler is always broken but never fixed.'),
 ('137 w 137th st|10030', 'safety_incident', '', 'building', 'There are several tenants with mental health issues and the landlord is unresponsive despite assaults from those tenants on other tenants.'),
 ('137 w 137th st|10030', 'management', '', 'building', 'Heat and hot water never work even when it’s freezing outside. We had rats in the walls.'),
 ('137 w 137th st|10030', 'safety_incident', '', 'building', 'I do not like the other tenant, packages getting lost, and people loitering outside the building.'),
 ('137 w 137th st|10030', 'safety_incident', '', 'building', 'Sometimes deals with package theft in lobby'),
 ('100 w 139th st|10030', 'management', '', 'building', 'Not great pest control and area does not feel safe'),
 ('100 w 139th st|10030', 'positive', '', 'management_company', 'The property manager is also very responsive and helpful.'),
 ('100 w 139th st|10030', 'noise', '', 'street', "you could literally hear every single noise off the street and it's on a major road"),
 ('100 w 139th st|10030', 'management', '', 'management_company', 'They refuse to make any necessary repairs, causing undo hardship on residents who aren’t in the position to fight back.'),
 ('100 w 139th st|10030', 'safety_incident', '', 'building', 'Stolen packages every week'),
 ('100 w 139th st|10030', 'positive', '', 'management_company', 'owner is very responsive'),
 ('2419 adam clayton powell jr blvd|10030', 'management', '', 'management_company', 'Building was infested with roaches and mice, management did not address.'),
 ('2419 adam clayton powell jr blvd|10030', 'other', '', 'street', 'Front of building is loud and dirty.'),
 ('204 sherman ave|10034', 'noise', '', 'street', 'Loud music throughout the entire neighborhood all hours of the night'),
 ('204 sherman ave|10034', 'management', '', 'building', 'roaches in the unit, super would avoid/ignore requests for maintenance often'),
 ('121 seaman ave|10034', 'car_crime', '', 'street', 'Car vandalism nearby'),
 ('121 seaman ave|10034', 'positive', '', 'building', 'It’s clean, neighbors are friendly, super doesn’t live here but is reliable and friendly.'),
 ('121 seaman ave|10034', 'elevator', '', 'building', 'Elevator was slow, only a few washers/dryers in basement and they were often out of order'),
 ('490 ocean pkwy|11218', 'management', '', 'management_company', 'No response from landlords regarding ANY issues. There is a roach problem with the building.'),
 ('490 ocean pkwy|11218', 'safety_incident', '', 'building', '(there was an issue with package theft for a while)'),
 ('3660 waldo ave|10463', 'noise', '', 'building', 'Stairs are often dirty, noisy neighbors and nothing absolutely nothing is done about it from management.'),
 ('3660 waldo ave|10463', 'positive', '', 'building', 'I have seen an improvement overall after he came.'),
 ('3660 waldo ave|10463', 'management', '', 'building', 'Mold, lack of owner accountability, dirty hallways, rusted fire escapes'),
 ('3660 waldo ave|10463', 'positive', '', 'building', 'very pet friendly'),
 ('3660 waldo ave|10463', 'management', '', 'management_company', 'management is useless'),
 ('3660 waldo ave|10463', 'management', '', 'building', 'we also had a borderline roach infestation and no exterminator was sent.'),
 ('3660 waldo ave|10463', 'management', '', 'management_company', 'water and heat shut off for extended periods of time. took 1 yr to get my security deposit back.'),
 ('3310 nostrand ave|11229', 'safety_incident', '', 'building', 'Packages are stolen everyday we have cameras that he refuses to look at.'),
 ('3310 nostrand ave|11229', 'management', '', 'management_company', 'It’s hard getting a hold on the landlord and most of the things we needed to fix we had to rely on “Management.”'),
 ('3310 nostrand ave|11229', 'positive', '', 'building', 'Security, Cleanliness, Friendly, Professional, and private.'),
 ('408 w 130th st|10027', 'elevator', '', 'building', 'The elevator broke down frequently and would not be repaired for weeks.'),
 ('408 w 130th st|10027', 'management', '', 'management_company', 'Management did not reply to complaints - we had several litigations.'),
 ('408 w 130th st|10027', 'elevator', '', 'building', 'Elevator is small and breaks down occasionally'),
 ('408 w 130th st|10027', 'management', '', 'building', 'We had bed bugs in our apartment that came from other units: we eradicated it, but it was a hassle'),
 ('408 w 130th st|10027', 'management', '', 'management_company', 'Management is basically nonexistent and impossible to reach.'),
 ('408 w 130th st|10027', 'management', '', 'management_company', 'There was a bed bug infestation that they weren’t managing at all, and our apartment got bed bugs multiple times.'),
]
items = []
def add_item(k, cat, date, exc, site, url, about, at): items.append(dict(addr_key=k, building_name=names.get(k, ''), category=cat, item_date=date, excerpt=exc, source_site=site, source_url=url, about=about, retrieved_at=at))
bad = 0
for k, cat, date, about, exc in ITEMS:
    g = IG[k]; hit = [r for r in g['reviews'] if norm(exc) in norm(r.get('body'))]
    if not hit: print('EXCERPT NOT FOUND', k, exc[:50]); bad += 1; continue
    d = (hit[0]['date'] or '')[:10]
    if d == '2021-11-16': d = IMPORT
    site = 'Openigloo' + (' (page is for 3280 Nostrand Avenue, same tax lot)' if 'nostrand' in k else '') + (' (page keyed to the pre-condo tax lot)' if k.startswith('623') else '')
    add_item(k, cat, d, exc, site, g['url'], about, g['at'])
# 3280-3310 Nostrand shares the page with 3310 Nostrand
for it in [dict(x) for x in items if x['addr_key'] == '3310 nostrand ave|11229']:
    it['addr_key'] = '3280-3310 nostrand ave|11229'; it['building_name'] = names['3280-3310 nostrand ave|11229']; items.append(it)

def page_at(u):
    for name in ('site.log', 'fetch_leads.log', 'fetch_addr.log'):
        for l in open(S / name):
            try: r = json.loads(l)
            except Exception: continue
            if r.get('url') == u: return r
def check(u, exc):
    from ev11_text import text
    r = page_at(u); t = norm(text(r['path']))
    if norm(exc) not in t: print('PAGE EXCERPT NOT FOUND', u[:50], exc[:50]); return None
    return r['retrieved_at']
PAGE_ITEMS = [
 ('3660 waldo ave|10463', 'safety_incident', '2012-03-14', 'building', 'Responding to persistent complaints of squatters, drug dealers and worse at 3660 Waldo Ave., the Majestic’s landlord has signed the building up for police patrols and hired a private security guard.', 'The Riverdale Press', 'https://www.riverdalepress.com/stories/majestic-landlord-promises-to-ramp-up-security,50043'),
 ('3660 waldo ave|10463', 'management', '2013-12-04', 'building', 'The 88-unit building has 680 violations recorded on the Department of Housing Preservation and Development’s (HPD) website.', 'City Limits', 'https://citylimits.org/program-to-take-buildings-from-bad-landlords-fades/'),
 ('3660 waldo ave|10463', 'elevator', '2013-12-04', 'building', 'And the inner part of the elevator has recently been replaced but doesn’t work for at least two days a week.', 'City Limits', 'https://citylimits.org/program-to-take-buildings-from-bad-landlords-fades/'),
 ('770 ocean pkwy|11230', 'other', 'undated (older listing shown on the page as occupied)', 'building', 'Sorry: no dogs.', 'Zumper (listing text)', ZU770),
 ('770 ocean pkwy|11230', 'other', 'undated (older listing, 2595 days on market)', 'building', 'Board approval required.No pets allowed.', 'Zumper (listing text)', ZU770),
 ('10 park ter e|10034', 'other', '2026-11-15', 'building', 'No, 10 Park Terrace East is not pet-friendly.', 'Apartment List (building FAQ)', AL10),
 ('10 park ter e|10034', 'other', 'undated (older listing shown on the page as occupied)', 'building', 'Cats allowed; sorry, no dogs.', 'Zumper (listing text)', ZU10),
 ('3250 93rd st|11369', 'other', 'undated (older listing, about 3,800 days on market)', 'building', 'Quiet building - Pre-war building - Live-in super - Walk-up', 'Zumper (listing text)', ZU3250),
]
for k, cat, date, about, exc, site, u in PAGE_ITEMS:
    at = check(u, exc)
    if at: add_item(k, cat, date, exc, site, u, about, at)
    else: bad += 1
NYC_NONE = 'Openigloo: no page with reviews for this lot (reviewed-buildings sitemaps and the lot-keyed address); one web search for news on the address returned only listing and data-aggregator pages'
NONE = {
 '1100 avalon sq|11542': 'Trulia building page (no reviews); Zumper address page (still titled Avalon at Glen Cove, no review block); Apartment List (no page); Fairfield\'s own page (no reviews); one web search for news: only listings and the 2021 purchase',
 '37 woodmere blvd|11598': 'Trulia building page (no reviews); Zumper address page (no review block); Apartment List (no page); Fairfield\'s own page; one web search for news: listings only',
 '10 wendell st|11550': 'Trulia unit page (no reviews); Zumper address page (404); one web search for news: listings only, mostly for the co-op at 20 Wendell St',
 '|11561': 'Zumper address page for 25 Franklin Blvd (no review block); Apartment List (no page); one web search: listing sites only (ForRent, ApartmentFinder, Redfin, not read)',
 '1941 coney island ave|11223': NYC_NONE, '405 w 206th st|10034': NYC_NONE + '; Openigloo has an empty page for the sister tower, 407 West 206 Street; Apartment List building page has no reviews',
 '4778 broadway|10034': 'Openigloo page exists for the lot with 0 reviews; one web search: listings only', '3250 93rd st|11369': NYC_NONE,
 '139-05 85th dr|11435': NYC_NONE, '2900 nostrand ave|11229': 'Openigloo page exists for the lot with 0 reviews (building opened 2025); own site has no reviews; one web search: listings only',
 '1802 ocean ave|11230': NYC_NONE,
}
for k, where in NONE.items():
    add_item(k, 'none_found', '', where, '', '', 'building', lib.now_iso()[:10] + 'T22:58:00+00:00')

# ---- ratings --------------------------------------------------------------------------------------------
# hand counts from the review texts read (Openigloo embeds only the five newest). Window: 2026-05-15 to 2026-11-15.
# key: (reviews_last_6_months, negative_last_6_months, negative_older, tags_last_6_months)
RC = {
 '1710 newkirk ave|11226': (0, 0, 4, ''), '1256 ocean ave|11230': (1, 1, 4, 'pests;no_heat_hot_water;unresponsive_management'),
 '623 ave h|11230': (0, 0, 0, ''), '2611 w 2nd st|11223': (0, 0, 1, ''), '2121 shore pkwy|11214': (0, 0, 1, ''), '8700 25th ave|11214': (0, 0, 0, ''),
 '137 w 137th st|10030': (0, 0, 5, ''), '100 w 139th st|10030': (0, 0, 4, ''), '2419 adam clayton powell jr blvd|10030': (0, 0, 2, ''),
 '204 sherman ave|10034': (0, 0, 1, ''), '121 seaman ave|10034': (0, 0, 1, ''), '490 ocean pkwy|11218': (0, 0, 1, ''),
 '3660 waldo ave|10463': (1, 1, 4, 'noise;unresponsive_management'), '3310 nostrand ave|11229': (0, 0, 3, ''), '3280-3310 nostrand ave|11229': (0, 0, 3, ''),
 '408 w 130th st|10027': (0, 0, 5, ''),
}
ra = []
for b in batch:
    k = b['addr_key']; g = IG.get(k)
    if g and g.get('agg') and k in RC:
        a = g['agg']; n6, neg6, nego, tags = RC[k]
        ra.append(dict(addr_key=k, building_name=names[k], rating_source='Openigloo', rating_value=round(float(a['ratingValue']), 2), rating_scale=5, review_count=a['reviewCount'],
                       as_of_date=TODAY, reviews_read=len(g['reviews']), reviews_last_6_months=n6, negative_last_6_months=neg6, negative_older=nego,
                       serious_issue_tags_last_6_months=tags, source_url=g['url']))
    else:
        where = NONE.get(k) or NYC_NONE
        if k == '770 ocean pkwy|11230': where = 'Openigloo: no page for this lot (co-op); Zumper address page has listings but no rating block; Trulia page carries no ratings'
        if k == '10 park ter e|10034': where = 'Openigloo: no page for this lot; Apartment List and Zumper address pages have no rating block; Trulia not readable (403)'
        ra.append(dict(addr_key=k, building_name=names[k], rating_source='none_found', rating_value='', rating_scale='', review_count='', as_of_date=TODAY, reviews_read=0,
                       reviews_last_6_months='', negative_last_6_months='', negative_older='', serious_issue_tags_last_6_months='', source_url=where))

def w(name, rows, cols):
    with open(OUT / name, 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
    print(name, len(rows))
w('live_check_batch_16.csv', lc, ['addr_key', 'listing_url', 'unit', 'status', 'price_now', 'available_now_text', 'matches_stored', 'building_site_url', 'checked_at', 'notes'])
w('confirm_batch_16.csv', cf, ['addr_key', 'fact', 'value', 'quote', 'source_url', 'status'])
w('items_batch_16.csv', items, ['addr_key', 'building_name', 'category', 'item_date', 'excerpt', 'source_site', 'source_url', 'about', 'retrieved_at'])
w('facts_batch_16.csv', fa, ['addr_key', 'fact', 'value', 'quote', 'source_url'])
w('ratings_batch_16.csv', ra, ['addr_key', 'building_name', 'rating_source', 'rating_value', 'rating_scale', 'review_count', 'as_of_date', 'reviews_read', 'reviews_last_6_months', 'negative_last_6_months', 'negative_older', 'serious_issue_tags_last_6_months', 'source_url'])
from collections import Counter
print('live', Counter(r['status'] for r in lc)); print('confirm', Counter(r['status'] for r in cf)); print('items', Counter(r['category'] for r in items)); print('bad excerpts', bad)
