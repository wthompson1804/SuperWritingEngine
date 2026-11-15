"""Evidence batch 17: fetch (robots-checked, cached) a page and print keyword context from its plain text. Usage: ev17_text.py url [regex]"""
import sys, re, html as H, json
sys.path.insert(0, 'scripts')
import ev17_site as S
def text(t):
    t = re.sub(r'<script.*?</script>|<style.*?</style>|<svg.*?</svg>', '', t, flags=re.S)
    t = re.sub(r'<(br|/p|/div|/li|/h\d|/tr)[^>]*>', '\n', t)
    t = H.unescape(re.sub(r'<[^>]+>', ' ', t)); t = re.sub(r'[ \t]+', ' ', t); return re.sub(r'\n\s*\n+', '\n', t)
if __name__ == '__main__':
    u = sys.argv[1]; rx = sys.argv[2] if len(sys.argv) > 2 else r'pet|dog|lbs|pound|elevator|floor|parking|garage|\$\d|special|free|review|rating|built|manag'
    r = S.get(u); print(json.dumps({k: v for k, v in r.items() if k != 'path'}))
    if r.get('status') == 200:
        raw = open(r['path'], encoding='utf-8', errors='replace').read(); t = text(raw)
        links = sorted(set(re.findall(r'href="([^"#]+)"', raw)))
        if '--links' in sys.argv: print('\n'.join(l for l in links if not re.search(r'\.(css|js|png|jpg|svg|ico|woff2?)(\?|$)', l))[:4000])
        seen = set(); last = -999
        for m in re.finditer(rx, t, re.I):
            if m.start() < last + 260: continue
            last = m.start()
            s = t[max(0, m.start() - 110):m.end() + 150].replace('\n', ' / ')
            key = s[60:140]
            if key in seen: continue
            seen.add(key); print('  ~', s)
            if len(seen) > 45: break
