"""Evidence batch 8: parse refetched Trulia building pages -> scratch JSON + compact print."""
import json, re, sys
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/'
def strip(o):
    if isinstance(o,dict): return {k:strip(v) for k,v in o.items() if k!='__typename' and 'Url' not in k and k not in('media','photos','image','images')}
    if isinstance(o,list): return [strip(x) for x in o]
    return o
def feats(c,pre=''):
    out=[]
    for g in c or []:
        n=pre+(g.get('formattedName') or '')
        for a in g.get('attributes') or []:
            out.append(n+': '+ (a.get('formattedName')+'=' if a.get('formattedName') else '')+str(a.get('formattedValue')))
        out+=feats(g.get('categories'),n+' > ')
    return out
out={}
for line in open(S+'fetch1.log'):
    u,st,n,path,ts=json.loads(line)
    if 'trulia.com' not in u: continue
    html=open(path,encoding='utf-8',errors='replace').read()
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not m: print(u,'NO NEXT_DATA'); continue
    hd=json.loads(m.group(1))['props'].get('homeDetails') or {}
    units=[]
    for g in (hd.get('floorPlans') or {}).get('floorPlanGroups') or []:
        for p in g.get('plans') or []:
            p=strip(p); units.append(p)
    rec=dict(url=u,ts=ts,name=hd.get('name'),type=hd.get('__typename'),price=(hd.get('price') or {}).get('formattedPrice'),
      tags=[t.get('formattedName') for t in hd.get('heroTags') or []],
      desc=(hd.get('description') or {}).get('value'),feats=feats((hd.get('features') or {}).get('categories')),
      hl=(hd.get('features') or {}).get('highlightedInfoAttributesSummary'),
      pet=strip(hd.get('petPolicy')),pet2=strip((hd.get('activeForRentListing') or {}).get('petPolicy')),
      mgmt=strip((hd.get('planVisit') or {}).get('propertyManagementCompany')),offers=strip(hd.get('specialOffers')),
      unitDetails=strip(hd.get('unitDetails')),fees=strip(hd.get('rentalCostsAndFees')),mod=(hd.get('activeListing') or {}).get('lastDateModified'),
      units=units, keys=list(hd.keys()), reviews=strip(hd.get('reviews') or hd.get('ratingsAndReviews')))
    out[u]=rec
json.dump(out,open(S+'trulia_parsed.json','w'),indent=1)
print(len(out))
