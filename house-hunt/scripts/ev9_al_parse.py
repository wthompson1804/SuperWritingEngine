import sys, json, re
sys.path.insert(0,'scripts')
import h_apartmentlist as A
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/'
res={}
for line in open(S+'b9_fetch1.log'):
    u,st,n,path,ts=json.loads(line)
    if 'apartmentlist.com' not in u: continue
    html=open(path,encoding='utf-8',errors='replace').read()
    fl=A.flight(html)
    fn=[getattr(A,x) for x in dir(A) if 'listing' in x.lower() and callable(getattr(A,x))]
    L=None
    for f in fn:
        try:
            L=f(html)
            if isinstance(L,dict) and 'available_units' in L: break
        except Exception as e: pass
    if not isinstance(L,dict): print(u,'NO LISTING',[f.__name__ for f in fn]); continue
    res[u]=dict(ts=ts,L=L)
    print('=====',u,ts)
    print(' keys',[k for k in L.keys()][:90])
    print(' name',L.get('display_name'),'|',L.get('street_address') or L.get('address'),'| stories',L.get('stories'),L.get('number_of_floors'),'| year',L.get('year_built'),'| units',L.get('total_units') or L.get('unit_count'))
    for un in L.get('available_units') or []:
        print('   unit',{k:un.get(k) for k in ('name','unit_name','display_name','bed','beds','bedrooms','price','rent','availability','available_on','move_in_date','sqft','floor','remote_listing_id') if un.get(k) is not None})
    print(' PET',A.pet_facts(L))
    print(' fees',json.dumps({k:L.get(k) for k in L if re.search('fee|parking|lease|special|concession|manage',k,re.I)})[:1500])
json.dump(res,open(S+'b9_al_parsed.json','w'))
