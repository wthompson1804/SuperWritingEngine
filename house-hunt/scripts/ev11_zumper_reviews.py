"""Evidence batch 11: read the Google rating block (buildingReviews) that Zumper building pages embed. No network."""
import json,re,sys,datetime
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/b11/'
out={}
for fn in ['fetch1.log','fetch_addr.log']:
  for x in open(S+fn):
    try: u,st,n,p,ts=json.loads(x)
    except Exception: continue
    if st!=200 or 'zumper.com' not in u: continue
    t=open(p,encoding='utf-8',errors='replace').read()
    i=t.find('"buildingReviews":')
    if i<0: out[u]=dict(ts=ts,none=True); continue
    try: br,_=json.JSONDecoder().raw_decode(t[i+len('"buildingReviews":'):])
    except Exception as e: out[u]=dict(ts=ts,err=str(e)); continue
    g=((br.get('data') or {}).get('sources') or {}).get('google')
    if not g: out[u]=dict(ts=ts,none=True,keys=list((br.get('data') or {}).keys())); continue
    out[u]=dict(ts=ts,rating=g.get('aggregateRating'),scale=g.get('ratingScale'),count=g.get('reviewCount'),
      pulled=datetime.datetime.utcfromtimestamp(g['lastPulled']).date().isoformat() if g.get('lastPulled') else '',
      reviews=[dict(date=datetime.datetime.utcfromtimestamp(r['date']).date().isoformat(),rating=r.get('rating'),body=r.get('body')) for r in g.get('reviews') or []])
json.dump(out,open(S+'zumper_reviews.json','w'),indent=1)
for u,o in out.items(): print(u.split('/')[-1][:50],o.get('rating'),o.get('count'),o.get('pulled'),[(r['date'],r['rating']) for r in o.get('reviews',[])] if not o.get('none') else 'NONE')
