import json, re, sys, glob
sys.path.insert(0,'scripts')
import h_trulia as T
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/'
out={}
for line in open(S+'fetch1.log'):
    u,st,n,path,ts=json.loads(line)
    if 'trulia.com' not in u: continue
    html=open(path,encoding='utf-8',errors='replace').read()
    m=re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.S)
    if not m: print(u,'NO NEXT_DATA',html[:200]); continue
    d=json.loads(m.group(1)); hd=d['props'].get('homeDetails') or {}
    cs=hd.get('currentStatus') or {}
    feats=T.flat_features(hd.get('features')); hl=T.highlighted(hd.get('features'))
    desc=((hd.get('description') or {}).get('value') or '')
    rec=dict(url=u,ts=ts,status=cs,price=(hd.get('price') or {}).get('formattedPrice'),
      hl=hl,feats=[f for f in feats if re.search(r'pet|dog|elevator|floor|stor|park|built|laundry|doorman|avail|fee|deposit',' '.join(f),re.I)],
      pet=hd.get('petPolicy'),desc=desc,provider=((hd.get('activeListing') or {}).get('provider') or {}).get('summary'),
      listed=(hd.get('activeListing') or {}).get('dateListed'), keys=[k for k in hd.keys()])
    out[u]=rec
    print('=====',u); print(cs, rec['price'], rec['listed'], rec['provider']); print('HL',hl); print('FEATS',rec['feats']); print('PET',json.dumps(rec['pet'])[:600]); print('DESC',desc[:1500])
json.dump(out,open(S+'trulia_parsed.json','w'),indent=1)
