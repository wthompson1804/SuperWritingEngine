"""Evidence batch 9: building own sites. Robots check then home page; follow internal links that look like pet / faq / amenities / reviews pages. Log to raw/evidence_b9/_sites.jsonl."""
import sys, json, re
from urllib.parse import urljoin, urlparse
sys.path.insert(0, 'scripts')
import ev9_site as S
def run(k, home, extra=()):
    r = S.get(home); r['k'] = k; r['kind'] = 'home'
    log = [r]
    if r.get('status') == 200 and not r.get('wall'):
        t = open(r['path'], encoding='utf-8', errors='replace').read()
        links = set()
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
            u = urljoin(home, m.group(1))
            if urlparse(u).netloc.replace('www.', '') != urlparse(home).netloc.replace('www.', ''): continue
            if re.search(r'pet|faq|amenit|review|testimonial|parking|fees', urlparse(u).path, re.I) and not re.search(r'\.(jpg|png|pdf|css|js|svg|webp)$', u, re.I):
                links.add(u.split('?')[0])
        for u in sorted(links)[:5] + list(extra):
            x = S.get(u); x['k'] = k; x['kind'] = 'sub'; log.append(x)
    with open('raw/evidence_b9/_sites.jsonl', 'a') as f:
        for x in log: f.write(json.dumps(x) + '\n')
    for x in log: print(k, x.get('kind'), x['url'], x.get('status'), x.get('len'), x.get('wall'), x.get('why', ''), flush=True)
if __name__ == '__main__':
    for a in sys.argv[1:]:
        k, u = a.split('=', 1); run(k, u)
