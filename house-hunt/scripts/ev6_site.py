"""Evidence batch 6: polite fetch of a building's own site: robots check (incl. Claude groups), then page. Usage: ev6_site.py url [url...]"""
import sys, json, re, urllib.robotparser
from urllib.parse import urlparse
sys.path.insert(0, 'scripts')
import lib
UA_NAMES = ['ClaudeBot', 'Claude-User', 'Claude-SearchBot', 'anthropic-ai', 'house-hunt-research']
_rp = {}
def allowed(u):
    p = urlparse(u); base = f'{p.scheme}://{p.netloc}'
    lib.HOST_DELAY.setdefault(p.netloc, 2.5)
    if base not in _rp:
        try:
            c, m = lib.cached_get(base + '/robots.txt', 'evidence_b6', ext='txt', retries=1)
        except Exception as e:
            _rp[base] = ('ERR', repr(e)[:100]); return False, _rp[base]
        if m['status'] in (401, 403, 429):
            _rp[base] = ('BLOCK', m['status'])
        elif m['status'] != 200 or b'<html' in c[:500].lower():
            _rp[base] = ('NONE', m['status'])
        else:
            rp = urllib.robotparser.RobotFileParser(); rp.parse(c.decode(errors='replace').splitlines()); _rp[base] = ('OK', rp)
    k, v = _rp[base]
    if k in ('BLOCK', 'ERR'): return False, (k, v)
    if k == 'NONE': return True, (k, v)
    ok = all(v.can_fetch(n, u) for n in UA_NAMES)
    cd = max([v.crawl_delay(n) or 0 for n in UA_NAMES])
    if cd: lib.HOST_DELAY[p.netloc] = max(2.5, float(cd))
    return ok, ('robots', 'crawl-delay=%s' % cd)
def get(u, refresh=False):
    ok, why = allowed(u)
    if not ok: return {'url': u, 'status': 'robots_or_block', 'why': str(why)}
    try:
        c, m = lib.cached_get(u, 'evidence_b6', ext='html', refresh=refresh, retries=1)
    except Exception as e:
        return {'url': u, 'status': 'ERR', 'why': repr(e)[:150]}
    t = c.decode(errors='replace')
    wall = bool(re.search(r'captcha|cf-challenge|Just a moment|Access Denied|px-captcha', t[:20000], re.I)) and len(t) < 60000
    return {'url': u, 'status': m['status'], 'len': len(c), 'path': m.get('path'), 'retrieved_at': m['retrieved_at'], 'wall': wall}
if __name__ == '__main__':
    for u in sys.argv[1:]:
        print(json.dumps(get(u)), flush=True)
