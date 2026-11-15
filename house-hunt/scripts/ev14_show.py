"""Evidence batch 14: show a cached page as text (keyword lines or head) plus its internal links. No network. Usage: ev14_show.py url [regex] [maxlines]"""
import sys,re,json,hashlib
sys.path.insert(0,'scripts')
from ev14_text import text
from lib import RAW
from urllib.parse import urljoin,urlparse
def path_for(u):
    import requests
    full=requests.Request('GET',u).prepare().url
    key=hashlib.sha1(('GET '+full+' ').encode()).hexdigest()[:16]
    for ext in ('html','txt','json'):
        p=RAW/'evidence_b14'/f'{key}.{ext}'
        if p.exists(): return p
if __name__=='__main__':
    u=sys.argv[1]; rx=sys.argv[2] if len(sys.argv)>2 else None; mx=int(sys.argv[3]) if len(sys.argv)>3 else 60
    p=path_for(u); raw=open(p,errors='replace').read(); t=text(p)
    lines=[x.strip() for x in t.split('\n') if x.strip()]
    if rx=='LINKS':
        ls=sorted(set(urljoin(u,h) for h in re.findall(r'href="([^"#]+)"',raw)))
        print('\n'.join(l for l in ls if urlparse(l).netloc==urlparse(u).netloc and not re.search(r'\.(css|js|png|jpg|svg|ico|woff2?)(\?|$)',l))[:4000]); sys.exit()
    if rx: lines=[x for x in lines if re.search(rx,x,re.I)]
    print(len(t)); print('\n'.join(x[:400] for x in list(dict.fromkeys(lines))[:mx]))
