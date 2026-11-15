"""Evidence batch 7: parse cached Trulia building pages -> scratch trulia_parsed.json. Usage: ev7_trulia_parse.py <scratch dir>"""
import json, re, sys
sys.path.insert(0,'scripts')
import h_trulia as T
S=sys.argv[1]
out={}
for log in ('fetch1.log','fetch2.log'):
  for line in open(S+'/'+log):
    u,st,n,path,ts=json.loads(line)
    if 'trulia.com' not in u or st!=200: continue
    html=open(path,encoding='utf-8',errors='replace').read()
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not m: print(u,'NO NEXT_DATA'); continue
    hd=json.loads(m.group(1))['props'].get('homeDetails') or {}
    feats=T.flat_features(hd.get('features')); hl=T.highlighted(hd.get('features'))
    afr=hd.get('activeForRentListing') or {}
    units=[]
    for g in ((hd.get('floorPlans') or {}).get('floorPlanGroups') or []):
        for plan in g.get('plans') or []:
            us=plan.get('units') or []
            for x in (us or [plan]):
                units.append(dict(plan=plan.get('name'),unit=x.get('name') if us else None,price=(x.get('priceRange') or {}).get('min'),pmax=(x.get('priceRange') or {}).get('max'),
                    beds=(x.get('bedrooms') or {}).get('formattedValue'),sqft=(x.get('floorSpace') or {}).get('max'),avail=x.get('availabilityText'),adate=x.get('availabilityDate'),now=x.get('isAvailableNow')))
    uq=[]; 
    for x in units:
        if x not in uq: uq.append(x)
    out[u]=dict(ts=ts,path=path,name=hd.get('name'),type=hd.get('__typename'),price=hd.get('price'),hl=hl,feats=feats,pet=afr.get('petPolicy'),petsum=hd.get('petPolicy'),
        desc=(hd.get('description') or {}).get('value'),units=uq,fees=hd.get('rentalCostsAndFees'),mgr=((hd.get('planVisit') or {}).get('propertyManagementCompany') or {}),
        ud=hd.get('unitDetails'),special=hd.get('specialOffers'),modified=(hd.get('activeListing') or {}).get('lastDateModified'),faq=hd.get('frequentlyAskedQuestions'),
        heroTags=[t.get('formattedName') for t in hd.get('heroTags') or []], ugc=((hd.get('surroundings') or {}).get('localUGC')))
json.dump(out,open(S+'/trulia_parsed.json','w'))
print(len(out))
