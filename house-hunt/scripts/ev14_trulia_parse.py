"""Evidence batch 14: dump the gate-relevant parts of the refetched Trulia pages to scratch JSON (no network)."""
import json, re, sys
sys.path.insert(0,'scripts')
import h_trulia as T
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b14/'
out={}
def strip(o):
    if isinstance(o,dict): return {k:strip(v) for k,v in o.items() if k not in('__typename','iconUrl','logoUrl') and v not in (None,[],{})}
    if isinstance(o,list): return [strip(x) for x in o]
    return o
for line in open(S+'fetch1.log'):
    u,st,n,path,ts=json.loads(line)
    if 'trulia.com' not in u: continue
    html=open(path,encoding='utf-8',errors='replace').read()
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not m: print(u,'NO NEXT_DATA'); continue
    hd=json.loads(m.group(1))['props'].get('homeDetails') or {}
    units=[]
    for g in ((hd.get('floorPlans') or {}).get('floorPlanGroups') or []):
        for p in g.get('plans') or []:
            pu=p.get('units') or []
            base=dict(group=g.get('title'),plan=p.get('name') or p.get('title'),pprice=(p.get('price') or {}).get('formattedPrice'),pavail=p.get('formattedAvailability') or p.get('availability'))
            if not pu: units.append(base)
            for x in pu: units.append(dict(base,unit=strip(x)))
    feats=T.flat_features(hd.get('features'))
    rec=dict(url=u,ts=ts,name=hd.get('name'),status=strip(hd.get('currentStatus')),price=(hd.get('price') or {}).get('formattedPrice'),
      hl=T.highlighted(hd.get('features')),feats=feats,pet=strip(hd.get('petPolicy')),pet2=strip((hd.get('activeForRentListing') or {}).get('petPolicy')),
      desc=((hd.get('description') or {}).get('value') or ''),site=((hd.get('description') or {}).get('additionalInfoHyperlink') or {}).get('url'),
      mgr=strip((hd.get('planVisit') or {}).get('propertyManagementCompany')),offers=strip(hd.get('specialOffers')),ud=strip(hd.get('unitDetails')),
      fees=strip(hd.get('rentalCostsAndFees')),faq=[(q['question'].get('text') or q['question'].get('markdown'),q['answer'].get('text') or q['answer'].get('markdown')) for q in ((hd.get('frequentlyAskedQuestions') or {}).get('questionAndAnswers') or [])],
      modified=(hd.get('activeListing') or {}).get('lastDateModified'),listed=(hd.get('activeListing') or {}).get('dateListed'),units=units,
      provider=strip((hd.get('activeListing') or {}).get('provider')),tags=[t.get('formattedName') for t in hd.get('heroTags') or []],keys=list(hd.keys()))
    out[u]=rec
json.dump(out,open(S+'trulia_parsed.json','w'),indent=1)
print(len(out))
