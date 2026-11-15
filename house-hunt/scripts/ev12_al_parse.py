"""Evidence batch 12: parse refetched Apartment List pages -> scratch al_parsed.json, print compact summary."""
import sys, json, re
sys.path.insert(0,'scripts')
import h_apartmentlist as A
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b12/'
res={}
for line in open(S+'fetch1.log'):
    u,st,n,path,ts=json.loads(line)
    if 'apartmentlist.com' not in u: continue
    html=open(path,encoding='utf-8',errors='replace').read()
    L=A.parse_listing(html)
    if not L: print(u,'NO LISTING'); continue
    res[u]=dict(ts=ts,L=L,path=path)
    if '-v' in sys.argv: print(sorted(L.keys()))
    print('=====',u,ts)
    print(' name',L.get('display_name'),'|',L.get('street_address'),L.get('city'),'| year',L.get('year_built'),'| keys w/ floor/story:',{k:L[k] for k in L if re.search('stor(y|ies)|floors|total_units|unit_count|rating|review_count',k,re.I) and not isinstance(L[k],(list,dict))})
    for un in L.get('available_units') or []:
        if (un.get('bed') or 0)<=1:
            print('   unit',{k:v for k,v in un.items() if v not in (None,'',[],{}) and k not in('photos','floorplan_photos','virtual_tours','videos')})
    print(' PET',A.pet_facts(L), json.dumps(L.get('pet_policies'))[:600])
    print(' misc',json.dumps({k:L.get(k) for k in L if re.search('fee|parking|lease_|special|concession|manage|utilit',k,re.I)})[:900])
    am=A.amen_names(L,'community_amenities')+A.amen_names(L,'unit_amenities')
    print(' AMEN',[a for a in am if re.search('elevator|park|garage|pool|door|concierge|dog|pet|cat',a,re.I)])
json.dump(res,open(S+'al_parsed.json','w'))
# ratings + reviews embedded in the page
dec=json.JSONDecoder(); rv_out={}
for u,o in res.items():
    fl=A.flight(open(o['path'],encoding='utf-8',errors='replace').read())
    slug=u.split('apartmentlist.com')[1]
    agg=None
    m=re.search(r'"@id":"https://www\.apartmentlist\.com%s","@type":"Product","aggregateRating":(\{[^}]*\})'%re.escape(slug),fl)
    if m: agg=json.loads(m.group(1))
    revs=[]
    for m in re.finditer(r'"reviews":(\[\{"propertyId")',fl):
        try: arr,_=dec.raw_decode(fl[m.start(1):])
        except Exception: continue
        for rv in arr:
            if rv.get('propertyName') and rv not in revs: revs.append(rv)
    rv_out[u]=dict(at=o['ts'],agg=agg,reviews=revs)
    print('RV',u.split('/')[-1],agg,len(revs),{rv.get('propertyName') for rv in revs})
json.dump(rv_out,open(S+'al_reviews.json','w'),indent=1)
