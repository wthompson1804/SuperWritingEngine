#!/usr/bin/env python3
"""Build data/reference/life_here_facts_ctny.csv from towns/*.py ROWS (upsert key building_id,moment,place_name,fact)."""
import json, csv, hashlib, importlib.util, pickle, sys
from pathlib import Path
ROOT=Path('/home/user/SuperWritingEngine/house-hunt'); SP=Path(__file__).parent
OUT=ROOT/'data/reference/life_here_facts_ctny.csv'
COLS=['building_id','neighborhood_id','moment','place_name','place_kind','fact','schedule','lat','lon','source_name','source_url','retrieved_at','confidence','notes']
OSM_AT='2026-11-15T18:32:19Z'
summ=json.load(open(SP/'summ.json'))
cands={r['building_id']:r for r in csv.DictReader(open(SP.parent/'cands.csv'))}
def at_for(url):
    key=hashlib.sha1(url.encode()).hexdigest()[:16]
    m=ROOT/'raw/life_here/pages'/f'{key}.meta.json'
    if m.exists():
        j=json.loads(m.read_text())
        if j.get('status')=='200': return j['retrieved_at']
    return None
_idx=None
def osm_ll(ref):
    global _idx
    if _idx is None:
        d=pickle.load(open(ROOT/'raw/big/osm/places_index.pkl','rb'))
        import pyproj
        tr=pyproj.Transformer.from_crs(32618,4326,always_xy=True)
        _idx={}
        for cat,v in d['pts'].items():
            if not isinstance(v,dict) or 'ref' not in v: continue
            for i,r in enumerate(v['ref']):
                if r: _idx[r]=v['xy'][i]
        _idx['_tr']=tr
    xy=_idx.get(ref)
    if xy is None: return '',''
    lon,lat=_idx['_tr'].transform(xy[0],xy[1]); return f'{lat:.5f}',f'{lon:.5f}'
rows=[]; errs=[]
for f in sorted(p for p in (SP/'towns').glob('*.py') if not p.name.startswith('_')):
    spec=importlib.util.spec_from_file_location(f.stem,f); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    for r in m.ROWS:
        bids=r.get('bids',[''])
        for b in bids:
            o={c:r.get(c,'') for c in COLS}
            o['building_id']=b
            o['neighborhood_id']=r.get('hood') or (cands[b]['hid'] if b else '')
            if not o['retrieved_at']:
                o['retrieved_at']=at_for(o['source_url']) or (OSM_AT if 'openstreetmap.org' in o['source_url'] else '')
            if r.get('osm') and not o['lat']:
                o['lat'],o['lon']=osm_ll(r['osm'])
            if not o['retrieved_at']: errs.append(('no retrieved_at',f.name,o['place_name'],o['source_url']))
            if b and b not in cands: errs.append(('bad bid',b))
            rows.append(o)
# route rows
for b,s in summ.items():
    roads=s.get('roads') or []
    if not roads: continue
    seq=' > '.join(roads)
    rows.append({'building_id':b,'neighborhood_id':cands[b]['hid'],'moment':'sunday','place_name':'Drive to Jamaica, Queens','place_kind':'route',
      'fact':'', 'schedule':'','lat':'','lon':'','source_name':'OSRM route (project drive data, data/enriched)',
      'source_url':s['osrm_url'],'retrieved_at':(s['osrm_at'] or '').replace('+00:00','Z'),'confidence':'medium',
      'notes':f'Road sequence from the OSRM free-flow fastest route, no traffic: {seq}. Minutes and tolls are already in the page data.'})
import route_text
for o in rows:
    if o['place_kind']=='route' and not o['fact']:
        o['fact']=route_text.fact(summ[o['building_id']]['roads'])
key=lambda o:(o['building_id'],o['moment'],o['place_name'],o['fact'])
ded={}
for o in rows: ded[key(o)]=o
order={'neighborhood':0,'dog_walk':1,'weekday':2,'saturday':3,'sunday':4}
rk={b:float(c['sr']) for b,c in cands.items()}
out=sorted(ded.values(),key=lambda o:(o['neighborhood_id'],o['building_id']!='',rk.get(o['building_id'],0),o['building_id'],order[o['moment']]))
for o in out:
    assert o['moment'] in order, o
    assert o['confidence'] in ('high','medium','low'), o
with open(OUT,'w',newline='') as fh:
    w=csv.DictWriter(fh,fieldnames=COLS); w.writeheader(); w.writerows(out)
print(len(out),'rows'); 
for e in errs: print('ERR',e)
