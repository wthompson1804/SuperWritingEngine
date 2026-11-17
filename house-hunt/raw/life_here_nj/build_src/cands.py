import pandas as pd, json, hashlib, math, sys
sys.path.insert(0,'scripts')
OUT='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/nj/'
r=pd.read_csv('data/ranked_units.csv',dtype=str,keep_default_na=False,low_memory=False)
r=r[(r.shown=='True')&(r.state=='NJ')]
r=r[pd.to_numeric(r.listed_rent,errors='coerce')<=2000]
have=set(pd.read_csv('data/reference/life_here_facts.csv',dtype=str,keep_default_na=False).building_id)
r=r[~r.building_id.isin(have)]
r['rk']=pd.to_numeric(r.shown_rank,errors='coerce')
g=r.sort_values('rk').groupby('building_id',sort=False).first().reset_index().sort_values('rk')
xw=pd.read_csv('data/reference/building_crosswalk.csv',dtype=str,keep_default_na=False)
from collections import defaultdict
X=defaultdict(list)
for a,b in zip(xw.addr_key,xw.building_id): X[b].append(a)
def hv(a,b,c,d):
    R=6371;p=math.pi/180
    return 2*R*math.asin(math.sqrt(math.sin((c-a)*p/2)**2+math.cos(a*p)*math.cos(c*p)*math.sin((d-b)*p/2)**2))
out=[]
for _,row in g.iterrows():
    lat,lon=float(row.lat or 0),float(row.lon or 0)
    best=None
    for k in sorted(X.get(row.building_id,[]),key=len):
        h=hashlib.sha1(k.encode()).hexdigest()[:14]
        try: e=json.load(open(f'data/enriched/{h}.json'))
        except FileNotFoundError: continue
        d=hv(lat,lon,e['lat'],e['lon'])
        if best is None or d<best[0]-1e-9:
            try: c=json.load(open(f'data/enriched_color/{h}.json'))
            except FileNotFoundError: c={}
            best=(d,e,c,h)
    rec=dict(building_id=row.building_id,rank=row.rk,name=row.building_name,address=row.address,city=row.city,hood=row.hood,hood_id=row.hood_id,lat=lat,lon=lon,park_name=row.park_name,dog_park_name=row.dog_park_name,hash=best[3] if best else None)
    if best:
        e,c=best[1],best[2]
        rec['enriched']=e.get('places'); rec['drive']=e.get('drive',{}).get('to_jamaica'); rec['color']=c
    out.append(rec)
json.dump(out,open(OUT+'cands.json','w'),default=str)
print(len(out))
for o in out: print(int(o['rank']),o['building_id'],o['hood_id'],'|',o['name'],'|',o['address'],o['city'],'| hash' if o['hash'] else 'NOHASH')
