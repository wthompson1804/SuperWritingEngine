"""Evidence batch 7: parse cached Apartment List property pages -> scratch al_parsed.json (listing objects)."""
import sys, json, re
sys.path.insert(0,'scripts')
import h_apartmentlist as A
S=sys.argv[1]
res={}
for line in open(S+'/fetch1.log'):
    u,st,n,path,ts=json.loads(line)
    if 'apartmentlist.com' not in u: continue
    html=open(path,encoding='utf-8',errors='replace').read()
    L=A.parse_listing(html)
    if not isinstance(L,dict): print(u,'NO LISTING'); continue
    res[u]=dict(ts=ts,L=L,path=path)
json.dump(res,open(S+'/al_parsed.json','w'))
print(len(res))
