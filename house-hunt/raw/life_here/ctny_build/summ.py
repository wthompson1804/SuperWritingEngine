import json, sys, hashlib, csv, math
from pathlib import Path
from collections import defaultdict
ROOT=Path('/home/user/SuperWritingEngine/house-hunt')
SP=Path(__file__).parent
xw=defaultdict(list)
for r in csv.DictReader(open(ROOT/'data/reference/building_crosswalk.csv')):
    xw[r['building_id']].append(r['addr_key'])
def hk(a,b,c,d):
    R=6371;p=math.radians
    x=math.sin(p(c-a)/2)**2+math.cos(p(a))*math.cos(p(c))*math.sin(p(d-b)/2)**2
    return 2*R*math.asin(math.sqrt(x))
out={}
for r in csv.DictReader(open(SP.parent/'cands.csv')):
    bid=r['building_id'];lat=float(r['lat']);lon=float(r['lon'])
    best=None
    for k in sorted(xw.get(bid,[]),key=len):
        h=hashlib.sha1(k.encode()).hexdigest()[:14]
        f=ROOT/'data/enriched'/f'{h}.json'
        if not f.exists(): continue
        e=json.loads(f.read_text())
        d=hk(lat,lon,e['lat'],e['lon'])
        if best is None or d<best[0]-1e-9:
            c=ROOT/'data/enriched_color'/f'{h}.json'
            best=(d,e,json.loads(c.read_text()) if c.exists() else {},h)
    if not best: out[bid]={'missing':True};continue
    _,e,c,h=best
    def vals(rec):
        v=(rec or {}).get('value')
        if isinstance(v,list): return [(p.get('name'),p.get('metres'),p.get('osm_url'),p.get('lat'),p.get('lon')) for p in v if isinstance(p,dict)]
        if isinstance(v,dict): return [(v.get('name'),v.get('metres'),v.get('osm_url'),v.get('lat'),v.get('lon'))]
        if (rec or {}).get('name'): return [(rec.get('name'),v,rec.get('osm_url'),rec.get('area_ha'),rec.get('kind'))]
        return v
    P=e.get('places',{})
    s={'h':h,'addr':r['addr'],'city':r['city'],'hood':r['hid'],'sr':r['sr']}
    for g in ['green_space','going_out','errands']:
        for k,v in P.get(g,{}).items():
            if k.startswith('nearest') and not k.endswith('walk_min'): s[k]=vals(v)
    for g,d in c.items():
        if isinstance(d,dict):
            for k,v in d.items():
                if k.endswith('examples'): s[k]=vals(v)
    tj=e.get('drive',{}).get('to_jamaica',{})
    s['roads']=[x['road'] for x in (tj.get('main_roads',{}).get('value') or [])]
    s['osrm_url']=tj.get('main_roads',{}).get('source_url');s['osrm_at']=tj.get('main_roads',{}).get('retrieved_at')
    out[bid]=s
json.dump(out,open(SP/'summ.json','w'),indent=1)
for bid,s in out.items():
    print('==',bid,s.get('addr'),s.get('city'),s.get('hood'))
    for k in ['nearest_named_park','nearest_dog_park','nearest_cafes','nearest_bakeries','nearest_bars','nearest_supermarket','roads','diner_ice_cream_examples','library_examples','bar_examples','cafe_examples','market_examples','cinema_theatre_examples','park_examples']:
        v=s.get(k)
        if v: print(' ',k,':',[ (x[0],x[1]) if isinstance(x,tuple) else x for x in v] if isinstance(v,list) else v)
