import sys, os, json, csv, glob, importlib
S=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,S); os.chdir(S)
import R
for f in sorted(glob.glob('h_*.py')): importlib.import_module(f[:-3])
ROWS=R.ROWS
# sunday route rows from our OSRM data
for c in R.C:
    d=c.get('drive') or {}
    mr=(d.get('main_roads') or {})
    roads=mr.get('value') or []
    if not roads: continue
    names=[]
    for x in roads:
        n=x['road']
        if n not in names: names.append(n)
    seq=' > '.join(names)
    short=[n.split(' (')[0] for n in names]
    if len(short)>1: txt=', '.join(short[:-1])+' and '+short[-1]
    else: txt=short[0]
    ra=mr.get('retrieved_at','').replace('+00:00','Z')
    ROWS.append(dict(building_id=c['building_id'],neighborhood_id=c['hood_id'],moment='sunday',place_name='Drive to Jamaica, Queens',place_kind='route',
        fact=f'The mapped route to Jamaica takes {txt}.',schedule='',lat='',lon='',source_name='OSRM route (project drive data, data/enriched)',
        source_url=mr.get('source_url',''),retrieved_at=ra,confidence='medium',
        notes=f'Road sequence from the OSRM free-flow fastest route, no traffic: {seq}. Minutes and tolls are already in the page data.'))
KIND={'strip':'street','dog_park':'dog_run','theatre':'other','museum':'other','stadium':'other','district':'downtown','city':'downtown','rule':'other','bakery':'restaurant'}
COLS=['building_id','neighborhood_id','moment','place_name','place_kind','fact','schedule','lat','lon','source_name','source_url','retrieved_at','confidence','notes']
rank={c['building_id']:(i,c['building_id']) for i,c in enumerate(R.C)}
hood_first={}
for c in R.C: hood_first.setdefault(c['hood_id'],len(hood_first))
MO={'neighborhood':0,'dog_walk':1,'weekday':2,'saturday':3,'sunday':4}
out={}
OUT='/home/user/SuperWritingEngine/house-hunt/data/reference/life_here_facts_nj.csv'
for r in ROWS:
    r['place_kind']=KIND.get(r['place_kind'],r['place_kind'])
    for k in ('lat','lon'): r[k]='' if r[k] in (None,'') else str(r[k])
    assert r['moment'] in MO and r['confidence'] in ('high','medium'), r
    assert r['source_url'] and r['retrieved_at'], r
    out[(r['building_id'],r['moment'],r['place_name'],r['fact'])]={k:r[k] for k in COLS}
def key(r):
    b=r['building_id']
    if b: return (hood_first.get(r['neighborhood_id'],99),1,rank[b][0],MO[r['moment']])
    return (hood_first.get(r['neighborhood_id'],99),0,0,0)
rows=sorted(out.values(),key=key)
with open(OUT,'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=COLS); w.writeheader(); w.writerows(rows)
print(len(rows))
