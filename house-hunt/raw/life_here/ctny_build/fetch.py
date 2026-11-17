#!/usr/bin/env python3
"""fetch.py URL [grep-regex...]: robots-aware, kill-list-aware, cached fetch; prints text (or matching lines)."""
import sys, json, hashlib, subprocess, time, re, html, os
from pathlib import Path
from urllib.parse import urlparse
from urllib import robotparser
from datetime import datetime, timezone
ROOT=Path('/home/user/SuperWritingEngine/house-hunt')
PAGES=ROOT/'raw/life_here/pages'; ROB=ROOT/'raw/life_here/robots'
KILL=ROOT/'raw/_host_kill_shared.json'
UA="house-hunt-research/0.1 (personal non-commercial research; low volume)"
OFF=['yelp.','reddit.','nextdoor.','zillow.','streeteasy.','apartments.com','trulia.','renthop.','realtor.com','rent.com','hotpads.','rentcafe.','craigslist.','patch.com','qns.com','tripadvisor.','google.','facebook.','appfolio.','realtymx.','wikipedia.org','ecode360','municode','amlegal','toasttab']
SP=Path(__file__).parent; LAST=SP/'last_hit.json'
def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def kill(host,reason,url):
    d=json.loads(KILL.read_text())
    if host not in d:
        d[host]={"reason":reason,"url":url,"at":now(),"by":"life_here_ctny"}
        KILL.write_text(json.dumps(d,indent=1))
    print(f"KILLED {host}: {reason}")
def wait(host):
    last=json.loads(LAST.read_text()) if LAST.exists() else {}
    dt=time.time()-last.get(host,0)
    delay=float(os.environ.get('DELAY','3.2'))
    if dt<delay: time.sleep(delay-dt)
    last[host]=time.time(); LAST.write_text(json.dumps(last))
def curl(url):
    r=subprocess.run(['curl','-sS','-L','--max-time','40','-A',UA,'-o','-','-w','\n__CODE__%{http_code}__%{url_effective}',url],capture_output=True)
    out=r.stdout
    m=re.search(rb'\n__CODE__(\d+)__(.*)$',out)
    if not m: return None,out,r.stderr.decode()[:200]
    return int(m.group(1)),out[:m.start()],m.group(2).decode()
def is_wall(body):
    b=body[:20000].lower()
    return any(x in b for x in [b'captcha',b'cf-chl',b'challenge-platform',b'incapsula',b'attention required',b'are you a robot',b'px-captcha',b'access denied'])
def robots_ok(url):
    p=urlparse(url); host=p.netloc
    f=ROB/(host+'.txt'); c=ROB/(host+'.txt.code')
    if not f.exists():
        wait(host)
        code,body,_=curl(f'{p.scheme}://{host}/robots.txt')
        f.write_bytes(body or b''); c.write_text(str(code))
        if code in (401,403,429):
            kill(host,f"HTTP {code} on robots.txt",f'{p.scheme}://{host}/robots.txt'); return False
    code=int(c.read_text() or 0)
    if code>=400 or code==0: return True  # no robots = allowed
    txt=f.read_bytes().decode('utf-8','replace')
    if '<html' in txt[:500].lower(): return True
    # Claude-User group if present else *
    groups=re.split(r'(?im)^\s*user-agent\s*:',txt)
    has_cu=re.search(r'(?im)^\s*user-agent\s*:\s*claude-user\s*$',txt)
    rp=robotparser.RobotFileParser(); rp.parse(txt.splitlines())
    agent='Claude-User' if has_cu else 'house-hunt-research'
    ok=rp.can_fetch(agent,url)
    if not ok: print(f"ROBOTS DISALLOW ({agent}) {url}")
    return ok
def get(url):
    key=hashlib.sha1(url.encode()).hexdigest()[:16]
    hp=PAGES/f'{key}.html'; mp=PAGES/f'{key}.meta.json'
    if hp.exists() and mp.exists(): return hp.read_bytes(),json.loads(mp.read_text())
    host=urlparse(url).netloc
    if any(o in host for o in OFF): print("OFF LIMITS",host); return None,None
    if host in json.loads(KILL.read_text()): print("HOST KILLED ALREADY",host); return None,None
    if not robots_ok(url): return None,None
    if host in json.loads(KILL.read_text()): return None,None
    wait(host)
    code,body,eff=curl(url)
    if code is None: print("FETCH FAIL",eff); return None,None
    if code in (401,403,429): kill(host,f"HTTP {code}",url); return None,None
    if code==200 and is_wall(body) and len(body)<30000: kill(host,"bot wall/CAPTCHA page (HTTP 200)",url); return None,None
    meta={"url":url,"status":str(code),"retrieved_at":now(),"final_url":eff}
    if code==200:
        hp.write_bytes(body); mp.write_text(json.dumps(meta))
    else: print("HTTP",code,eff)
    return body,meta
def text(b):
    s=b.decode('utf-8','replace')
    s=re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>',' ',s)
    s=re.sub(r'(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>|</tr>','\n',s)
    s=re.sub(r'<[^>]+>',' ',s); s=html.unescape(s)
    s=re.sub(r'[ \t\xa0]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
    return s
if __name__=='__main__':
    url=sys.argv[1]; pats=sys.argv[2:]
    b,m=get(url)
    if not b: sys.exit(1)
    print("META",json.dumps(m))
    t=text(b); lines=[l.strip() for l in t.split('\n') if l.strip()]
    if pats:
        rx=re.compile('|'.join(pats),re.I)
        for i,l in enumerate(lines):
            if rx.search(l): print(i,':',l[:400])
    else:
        lim=int(os.environ.get('LIM','6000'))
        print('\n'.join(lines)[:lim])
