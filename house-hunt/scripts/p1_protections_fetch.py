"""Helper: fetch an official page via lib.cached_get (source=renter_protection), extract text, grep.
Usage: python3 scripts/p1_protections_fetch.py URL [regex ...]
"""
import re, sys, subprocess, html
sys.path.insert(0, __import__('os').path.dirname(__file__))
from lib import cached_get, ROOT

def text_of(url):
    ext = 'pdf' if url.lower().split('?')[0].endswith('.pdf') else 'html'
    content, meta = cached_get(url, 'renter_protection', ext=ext, timeout=90)
    if content[:4] == b'%PDF':
        p = ROOT / meta['path']
        if not str(p).endswith('.pdf'):
            pass
        t = subprocess.run(['pdftotext', '-layout', str(p), '-'], capture_output=True).stdout.decode('utf8', 'replace')
    else:
        t = content.decode('utf8', 'replace')
        t = re.sub(r'(?is)<(script|style).*?</\1>', ' ', t)
        t = re.sub(r'<[^>]+>', ' ', t)
        t = html.unescape(t)
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return t, meta

if __name__ == '__main__':
    url = sys.argv[1]
    t, meta = text_of(url)
    print(meta.get('status'), meta.get('path'), len(t))
    pats = sys.argv[2:]
    if not pats:
        print(t[:3000])
    for p in pats:
        for m in re.finditer(p, t, re.I):
            s = max(0, m.start()-300); print('...', t[s:m.end()+400].replace('\n', ' '), '\n---')
