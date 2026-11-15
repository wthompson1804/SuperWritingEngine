"""Evidence batch 10: parse refetched Trulia /building/ and /home/ pages -> scratch trulia_parsed.json + compact print."""
import json, re, sys, csv
sys.path.insert(0,'scripts')
import h_trulia as T
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b10/'
B={}
for r in csv.DictReader(open('data/reference/evidence_batches/batch_10.csv')):
    for u in r['urls'].split(' | '): B[u]=r
out={}
for line in open(S+'fetch1.log'):
    u,st,n,path,ts=json.loads(line)
    if 'trulia.com' not in u: continue
    html=open(path,encoding='utf-8',errors='replace').read()
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not m: print(u,'NO NEXT_DATA',html[:200]); continue
    d=json.loads(m.group(1)); hd=d['props'].get('homeDetails') or {}
    r=B[u]
    feats=T.flat_features(hd.get('features')); hl=T.highlighted(hd.get('features'))
    desc=((hd.get('description') or {}).get('value') or '')
    rec=dict(url=u,ts=ts,path=path,hl=hl,feats=feats,pet=hd.get('petPolicy'),desc=desc,
        status=hd.get('currentStatus'),price=(hd.get('price') or {}).get('formattedPrice'),
        avail=hd.get('formattedAvailableDate'),listed=(hd.get('activeListing') or {}).get('dateListed'),
        provider=hd.get('provider'),fees=hd.get('rentalCostsAndFees'),floorPlans=hd.get('floorPlans'),unitDetails=hd.get('unitDetails'),
        name=hd.get('name'),special=hd.get('specialOffers'),faq=hd.get('frequentlyAskedQuestions'))
    out[u]=rec
    print('=====',r['building_name'],'| stored',r['unit_list'],'|',r['rents'],'|',ts)
    print('  status',json.dumps(rec['status'])[:200],'price',rec['price'],'avail',rec['avail'],'listed',rec['listed'])
    print('  HL',hl)
    print('  FEATS',[f for f in feats if re.search(r'pet|dog|elevator|floor|stor|park|built|doorman|pool|garage|lb|weight',' '.join(map(str,f)),re.I)][:25])
    print('  PET',json.dumps(rec['pet'])[:700])
    print('  DESC',desc[:900].replace('\n',' '))
    print('  PROV',json.dumps(rec['provider'])[:400])
    print('  FEES',json.dumps(rec['fees'])[:900])
    print('  FP',json.dumps(rec['floorPlans'])[:300]); print('  UD',json.dumps(rec['unitDetails'])[:300])
json.dump(out,open(S+'trulia_parsed.json','w'),indent=1)
