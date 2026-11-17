"""usage: python3 -I fetch.py URL [URL...]  -> prints cache path + status + text length; text saved as .txt"""
import sys, os, json, time, hashlib, re, subprocess, html
from urllib.parse import urlparse
from urllib import robotparser
ROOT='/home/user/SuperWritingEngine/house-hunt'
D=ROOT+'/raw/life_here_nj'; P=D+'/pages'; R=D+'/robots'
os.makedirs(P,exist_ok=True); os.makedirs(R,exist_ok=True)
KILL=ROOT+'/raw/_host_kill_shared.json'
UA="house-hunt-research/0.1 (personal non-commercial research; low volume)"
OFF=['yelp.','reddit.','nextdoor.','zillow.','streeteasy.','apartments.com','trulia.','renthop.','realtor.com','rent.com','hotpads.','rentcafe.','craigslist.','patch.com','qns.com','tripadvisor.','google.','facebook.','appfolio.','realtymx','wikipedia.org','instagram.']
def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
def bare(h): return h[4:] if h.startswith('www.') else h
def killed(h):
    k=json.load(open(KILL))
    for e in k:
        if bare(e)==bare(h) or h.endswith('.'+bare(e)): return e
def kill(h,reason,url):
    k=json.load(open(KILL)); k[h]={"reason":reason,"url":url,"at":now(),"by":"life_here_nj"}
    json.dump(k,open(KILL,'w'),indent=1,ensure_ascii=False)
LAST=D+'/_last.json'
def throttle(h):
    try: l=json.load(open(LAST))
    except Exception: l={}
    w=l.get(h,0)+3.5-time.time()
    if w>0: time.sleep(w)
    l[h]=time.time(); json.dump(l,open(LAST,'w'))
def curl(url):
    throttle(urlparse(url).netloc)
    tmp=P+'/_tmp'
    r=subprocess.run(['curl','-sS','-L','--max-time','40','-A',UA,'-o',tmp,'-w','%{http_code} %{url_effective}',url],capture_output=True,text=True)
    if r.returncode!=0: return None,r.stderr.strip()[:200],url
    code,eff=r.stdout.split(' ',1)
    b=open(tmp,'rb').read(); os.remove(tmp)
    return int(code),b,eff
CHAL=re.compile(rb'(Incapsula|cf-chl|challenge-platform|Just a moment\.\.\.|captcha|Access Denied|px-captcha|_Incapsula_Resource|Attention Required)',re.I)
def robots_ok(url):
    u=urlparse(url); h=u.netloc
    f=R+'/'+h+'.txt'
    if not os.path.exists(f):
        code,b,eff=curl(f'{u.scheme}://{h}/robots.txt')
        if code in (401,403,429): kill(h,f'HTTP {code} on robots.txt',f'{u.scheme}://{h}/robots.txt'); return False,f'killed {code} robots'
        if code is None: return False,'unreachable: '+str(b)
        txt=b.decode('utf-8','replace') if code==200 else ''
        if code==200 and CHAL.search(b) and 'user-agent' not in txt.lower(): kill(h,'bot challenge on robots.txt',f'{u.scheme}://{h}/robots.txt'); return False,'killed challenge robots'
        open(f,'w').write(txt); open(f+'.code','w').write(str(code))
    txt=open(f).read()
    # choose group: Claude-User if named, else *
    agent='Claude-User' if re.search(r'(?im)^\s*user-agent:\s*claude-user\s*$',txt) else '*'
    rp=robotparser.RobotFileParser(); rp.parse(txt.splitlines())
    ok=rp.can_fetch(agent,url)
    return ok,f'robots {agent} {"allow" if ok else "DISALLOW"}'
def totext(b):
    s=b.decode('utf-8','replace')
    s=re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>',' ',s)
    s=re.sub(r'(?i)<br\s*/?>|</p>|</div>|</li>|</h\d>|</tr>','\n',s)
    s=re.sub(r'<[^>]+>',' ',s); s=html.unescape(s)
    s=re.sub(r'[ \t\xa0]+',' ',s); s=re.sub(r'\n\s*\n+','\n',s)
    return s.strip()
def get(url):
    h=urlparse(url).netloc
    key=hashlib.sha1(url.encode()).hexdigest()[:16]
    if os.path.exists(f'{P}/{key}.meta.json'):
        m=json.load(open(f'{P}/{key}.meta.json')); return key,m,'cached'
    if any(o in h for o in OFF): return key,None,'OFF LIMITS'
    k=killed(h)
    if k: return key,None,f'KILLED host ({k})'
    ok,why=robots_ok(url)
    if not ok: return key,None,why
    code,b,eff=curl(url)
    if code is None: return key,None,'unreachable '+str(b)
    eh=urlparse(eff).netloc
    if code in (401,403,429):
        open(f'{P}/_killed_{eh}.html','wb').write(b)
        kill(eh,f'HTTP {code}',url); return key,None,f'KILLED now HTTP {code}'
    if code==200 and len(b)<15000 and CHAL.search(b):
        open(f'{P}/_killed_{eh}.html','wb').write(b)
        m0=CHAL.search(b).group(0).decode('latin1')
        kill(eh,f'bot challenge page (HTTP 200, {len(b)} bytes, matched {m0!r})',url); return key,None,'KILLED challenge '+m0
    m={'url':url,'final_url':eff,'status':code,'retrieved_at':now()}
    if code==200:
        open(f'{P}/{key}.html','wb').write(b); open(f'{P}/{key}.txt','w').write(totext(b))
    json.dump(m,open(f'{P}/{key}.meta.json','w'))
    return key,m,why
if __name__=='__main__':
    for u in sys.argv[1:]:
        key,m,why=get(u)
        n=os.path.getsize(f'{P}/{key}.txt') if os.path.exists(f'{P}/{key}.txt') else 0
        print(key, m['status'] if m else '-', m['retrieved_at'] if m else '', n, why, u)
