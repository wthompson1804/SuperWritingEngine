"""Evidence batch 10 helper: list links in a cached page whose href or text matches a regex. usage: ev10_links.py URL regex"""
import sys, re, html as H
from urllib.parse import urljoin
sys.path.insert(0,'scripts'); import lib
u, pat = sys.argv[1], sys.argv[2]
c, m = lib.cached_get(u, 'evidence_b10', ext='html')
t = c.decode('utf8','replace'); seen=set()
for mm in re.finditer(r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t):
    href, txt = H.unescape(mm.group(1)), re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',mm.group(2))).strip()
    if re.search(pat, href+' '+txt, re.I):
        k = urljoin(u, href)
        if k not in seen: seen.add(k); print(k, '|', txt[:60])
