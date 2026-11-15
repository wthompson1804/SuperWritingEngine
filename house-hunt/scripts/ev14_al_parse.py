"""Evidence batch 14: parse refetched Apartment List pages (no network) into scratch JSON."""
import json, sys
sys.path.insert(0,'scripts')
import h_apartmentlist as al
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b14/'
out={}
for line in open(S+'fetch1.log'):
    u,st,n,path,ts=json.loads(line)
    if 'apartmentlist.com' not in u or st!=200: continue
    L=al.parse_listing(open(path,encoding='utf-8',errors='replace').read())
    out[u]=dict(ts=ts,listing=L)
json.dump(out,open(S+'al_parsed.json','w'),indent=1)
print(len(out))
