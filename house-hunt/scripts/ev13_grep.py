"""Evidence batch 13: print title, keyword lines and internal links of cached pages from a scratch log (no network). Usage: ev13_grep.py log [regex]"""
import json,re,sys
sys.path.insert(0,'scripts')
from ev13_text import text
KW=re.compile(sys.argv[2] if len(sys.argv)>2 else r'elevator|pound|lbs?\b|weight|breed|pet |pets|dog|parking|garage|floors?\b|stor(y|ies)|special|free|managed by|management|built|pool|concierge|doorman|rating|reviews',re.I)
for line in open(sys.argv[1]):
    try: o=json.loads(line)
    except Exception: continue
    if isinstance(o,list): o=dict(url=o[0],status=o[1],path=o[3])
    if o.get('status')!=200: continue
    raw=open(o['path'],encoding='utf-8',errors='replace').read()
    t=text(o['path']); ti=re.search(r'<title[^>]*>(.*?)</title>',raw,re.S)
    print('=====',o['url'],'|',(ti.group(1).strip() if ti else '')[:100],'| textlen',len(t))
    seen=set()
    for l in t.split('\n'):
        l=l.strip()
        if KW.search(l) and l not in seen and len(l)<600: seen.add(l); print('   ',l[:400])
    links=sorted(set(re.findall(r'href="([^"#]+)"',raw)))
    print('  LINKS',[l for l in links if not re.search(r'\.(css|js|png|jpe?g|svg|ico|woff2?|webp)(\?|$)|facebook|instagram|twitter|google|linkedin|youtube|wp-json|xmlrpc|/feed',l)][:45])
