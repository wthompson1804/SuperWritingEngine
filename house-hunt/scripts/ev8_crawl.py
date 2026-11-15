"""Evidence batch 8: polite look at a building's own site: home page + up to 4 same-host pages whose link mentions pets/faq/amenities/fees/parking.
Prints sentences mentioning dogs, weight, elevator, parking, ratings. Usage: ev8_crawl.py url [url...]"""
import sys, re, json, html as H
from urllib.parse import urljoin, urlparse
sys.path.insert(0, 'scripts')
import ev8_site as S, ev8_text as T
KW = r'\bpets?\b|\bdogs?\b|\blbs?\b|pound|weight|breed|elevator|stor(y|ies)\b|parking|garage|review|rating|stars|managed by|built in'
def show(u, m):
    t = T.text(m['path'])
    lines = [l for l in t.split('\n') if re.search(KW, l, re.I) and len(l) > 12]
    seen = []
    for l in lines:
        if l not in seen: seen.append(l)
    print('   TEXT', ' || '.join(x[:260] for x in seen)[:2500])
    raw = open(m['path'], encoding='utf-8', errors='replace').read()
    for mm in re.finditer(r'"(aggregateRating|ratingValue|reviewCount|ratingCount)"\s*:\s*("?[^,}]{1,80})', raw): print('   LD', mm.group(0)[:120])
    return raw
for u in sys.argv[1:]:
    m = S.get(u)
    print('=====', u, {k: m.get(k) for k in ('status', 'len', 'wall', 'why', 'retrieved_at', 'path')}, flush=True)
    if m.get('status') != 200 or m.get('wall'): continue
    raw = show(u, m)
    host = urlparse(u).netloc
    links = []
    for mm in re.finditer(r'href="([^"#]+)"', raw):
        l = urljoin(u, H.unescape(mm.group(1)))
        if urlparse(l).netloc == host and re.search(r'pet|faq|amenit|fees|parking|policies|reviews|testimon', l, re.I) and not re.search(r'\.(css|js|png|jpg|svg|pdf|ico|webp)(\?|$)', l, re.I) and l not in links and l != u:
            links.append(l)
    print('   LINKS', links[:12])
    for l in links[:4]:
        m2 = S.get(l)
        print('  --', l, {k: m2.get(k) for k in ('status', 'len', 'wall', 'why', 'retrieved_at', 'path')}, flush=True)
        if m2.get('status') == 200 and not m2.get('wall'): show(l, m2)
