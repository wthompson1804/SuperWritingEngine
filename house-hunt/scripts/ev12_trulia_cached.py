"""Evidence batch 12: read Trulia building pages captured earlier today by the harvest (raw/trulia, raw/region_connecticut); no network.
Used because Trulia returned 403 to this batch after 17 requests. Usage: ev12_trulia_cached.py substr [substr...]"""
import json,re,sys
sys.path.insert(0,'scripts'); import h_trulia as T
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b12/'
want=sys.argv[1:]
idx={}
for src in ['trulia','region_connecticut']:
    for l in open(f'raw/{src}/_index.jsonl'):
        try: x=json.loads(l)
        except Exception: continue
        if x['status']==200 and 'trulia.com/building' in x['url'] and any(k in x['url'] for k in want): idx[x['url']]=x
try: out=json.load(open(S+'trulia_cached6.json'))
except Exception: out={}
for u,x in idx.items():
    html=open(x['path'],encoding='utf-8',errors='replace').read()
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not m: print('no data',u); continue
    hd=json.loads(m.group(1))['props']['homeDetails']
    units=[]
    for g in ((hd.get('floorPlans') or {}).get('floorPlanGroups') or []):
        for p in g.get('plans') or []:
            pu=p.get('units') or []
            if not pu: units.append(dict(group=g['title'],plan=p.get('name'),price=(p.get('priceRange') or {}).get('formattedPrice'),avail=p.get('availabilityText')))
            for q in pu: units.append(dict(group=g['title'],plan=p.get('name'),unit=q['name'],price=q['priceRange'].get('formattedPrice'),avail=q.get('availabilityText'),date=(q.get('availabilityDate') or '')[:10],sqft=(q.get('floorSpace') or {}).get('formattedDimension')))
    feats=T.flat_features(hd.get('features'))
    cards=((hd.get('activeForRentListing') or {}).get('petPolicy') or {}).get('cards') or []
    rec=dict(url=u,ts=x['retrieved_at'],path=x['path'],name=hd.get('name'),price=(hd.get('price') or {}).get('formattedPrice'),feats=feats,pet=(hd.get('petPolicy') or {}).get('formattedPetsAllowed'),
       dogs=[(c.get('statusLabel'),[(f['label'],f['value']) for f in (c.get('facts') or [])]) for c in cards if c['species']=='DOGS'],desc=(hd.get('description') or {}).get('value') or '',
       mgr=((hd.get('planVisit') or {}).get('propertyManagementCompany') or {}).get('name'),offers=[(o.get('description'),o.get('subText')) for o in hd.get('specialOffers') or []],ud=hd.get('unitDetails'),
       modified=(hd.get('activeListing') or {}).get('lastDateModified'),units=units)
    out[u]=rec
    print('=====',rec['name'],u[-50:],'| cap',rec['ts'],'| mod',rec['modified'],'|',rec['price'],'| mgr',rec['mgr'],'| ud',{k:v for k,v in (rec['ud'] or {}).items() if k!='__typename'})
    print(' feats',[f[-2]+':'+f[-1] if f[-2] else f[-1] for f in feats if re.search(r'Elevator|Parking|Garage|Pool|lbs|pet fee|Pet Policy|Restrictions|Includes',f[-1]+f[-2])])
    print(' pet',rec['pet'],rec['dogs']); print(' offers',rec['offers'])
    for kw in ['pet','dog','lb','floor','elevator','stor','park']:
        for mm in re.finditer(r'[^.\n]*\b'+kw+r'[^.\n]*',rec['desc'],re.I): print('  ',kw,':',mm.group(0).strip()[:250])
    for q in units:
        if '2 Bed' in q['group'] or '3 Bed' in q['group']: continue
        if rec['name']=='Scribe' and q.get('unit') not in ('Unit 508','Unit 446'): continue
        print('  U',q)
json.dump(out,open(S+'trulia_cached6.json','w'),indent=1)
