"""Evidence batch 12: print keyword sentences and internal links from cached pages (no network). Usage: ev12_grep.py [-l] url [url...]"""
import sys,re,json
sys.path.insert(0,'scripts'); import ev12_text as t
KW=r'pet|dog|lb|pound|weight|breed|elevator|floor|stor(y|ies)|park|garage|fee|special|free|built|manag|pool|concierge|doorman|rating|review'
idx={}
for l in open('raw/evidence_b12/_index.jsonl'):
    x=json.loads(l)
    if x['status']==200: idx[x['url']]=x
links='-l' in sys.argv
for u in [a for a in sys.argv[1:] if a!='-l']:
    x=idx.get(u)
    if not x: print('NOT CACHED',u); continue
    raw=open(x['path'],encoding='utf-8',errors='replace').read(); tx=t.text(x['path'])
    print('=====',u,x['retrieved_at'],len(tx))
    if links: print(' LINKS',sorted({h for h in re.findall(r'href="([^"#]+)"',raw) if not re.search(r'\.(css|js|png|jpg|svg|ico|woff2?)(\?|$)',h)})[:80])
    seen=set()
    for line in tx.split('\n'):
        s=line.strip()
        if len(s)>3 and re.search(KW,s,re.I) and s not in seen:
            seen.add(s); print('  ',s[:400])
