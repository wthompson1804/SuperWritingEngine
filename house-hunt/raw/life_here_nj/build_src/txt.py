import sys,os,hashlib,re
sys.path.insert(0,os.path.dirname(__file__))
from fetch import totext
D=['/home/user/SuperWritingEngine/house-hunt/raw/life_here_nj/pages/','/home/user/SuperWritingEngine/house-hunt/raw/life_here/pages/']
pat=None; n=40
args=sys.argv[1:]
if args and args[0].startswith('-g'): pat=re.compile(args[1],re.I); args=args[2:]
for a in args:
    k=hashlib.sha1(a.encode()).hexdigest()[:16] if a.startswith('http') else a
    for d in D:
        if os.path.exists(d+k+'.html'):
            t=totext(open(d+k+'.html','rb').read())
            L=[l for l in t.split('\n') if len(l.strip())>50]
            if pat: L=[l for l in L if pat.search(l)]
            print('=====',a); print('\n'.join(l.strip()[:600] for l in L[:n])); break
    else: print('MISSING',a)
