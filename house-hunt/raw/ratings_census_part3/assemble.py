"""Assemble data/evidence/ratings_census_part3.csv from offline.json, own-site result, search_findings.tsv, search_log.tsv, search_notes.tsv. Idempotent."""
import csv,json,os,collections,statistics,datetime
D='raw/ratings_census_part3'
T=[x for x in csv.DictReader(open('data/reference/ratings_census_targets.csv')) if x['part']=='3']
now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
BASE=['google','yelp','apartments_com','apartmentratings','zillow','apartment_list','zumper','openigloo','facebook','rent_com']
def nyc(z): return z[:3] in('100','101','102','103','104','110','111','112','113','114','116')
SCALE10={'veryapt','atly','lucidrents'}
rows=collections.defaultdict(list)   # bid -> list of found dicts
neg=collections.defaultdict(dict)    # bid -> platform -> (basis,url,at,note)
for o in json.load(open(f'{D}/offline.json')):
    if o['rating']:
        rows[o['building_id']].append(dict(platform=o['platform'],rating=o['rating'],rating_scale=o['rating_scale'],review_count=o['review_count'],basis=o['basis'],source_url=o['source_url'],search_query='',match_confidence=o['match_confidence'],retrieved_at=o['retrieved_at'],note=o['note']))
    else:
        neg[o['building_id']][o['platform']]=(o['basis'],o['source_url'],o['retrieved_at'],o['note'].replace('NOT_SEEN: ',''))
rows['b_d4eb1f509c'].append(dict(platform='own_site',rating='5',rating_scale=5,review_count='1',basis='own_site_widget',source_url='https://www.livethebrunswick.com/',search_query='',match_confidence='high',retrieved_at='2026-11-16T01:05:00+00:00',note="JSON-LD aggregateRating on the building's own site (one testimonial-style review dated 2025-02-05); not a third-party platform"))
log={}
for l in open(f'{D}/search_log.tsv'):
    a=l.rstrip('\n').split('\t'); log[a[0]]=(a[1],a[2])
for l in open(f'{D}/search_findings.tsv'):
    b,p,r,c,u,conf,note,q,at=l.rstrip('\n').split('\t')
    note2=note
    if c=='300' and p=='average_rent': note2+=' [count displayed as "about 300"]'
    rows[b].append(dict(platform=p,rating=r,rating_scale=10 if p in SCALE10 and not (p=='veryapt' and r=='4.0') else 5,review_count=c,basis='search_result_display',source_url=u,search_query=q,match_confidence=conf,retrieved_at=at,note=note2))
notes=collections.defaultdict(list)
for l in open(f'{D}/search_notes.tsv'):
    a=l.rstrip('\n').split('\t'); notes[a[0]].append(a[1])
KEY={'apartments_com':'apartments.com','apartment_list':'apartment list','zumper':'zumper','yelp':'yelp','openigloo':'openigloo','zillow':'zillow','apartmentratings':'apartmentratings','google':'google'}
out=[]
for t in T:
    b=t['building_id']; found=rows.get(b,[])
    # dedupe identical platform/rating/count, prefer cached_page then search display
    seen={}
    for f in found:
        try: k=(f['platform'],float(f['rating']),str(f['review_count']).split('.')[0])
        except ValueError: k=(f['platform'],f['rating'],f['review_count'])
        pr={'cached_page':0,'own_site_widget':1,'earlier_evidence':2,'search_result_display':3}[f['basis']]
        if k not in seen or pr<seen[k][0]: seen[k]=(pr,f)
    found=[v[1] for v in seen.values()]
    base=dict(building_id=b,building_name=t['building_name'],address=t['address'],city=t['city'],state=t['state'])
    for f in found:
        rc=str(f['review_count']).split('.')[0] if f['review_count'] not in('',None) else ''
        out.append({**base,**f,'status':'found','review_count':rc})
    have={f['platform'] for f in found}
    plats=[p for p in BASE if p!='openigloo' or nyc(t['zip5'])]
    q,at=log.get(b,('',''))
    for p in plats:
        if p in have: continue
        basis,url,rat,note='','',at or now,''
        if p in neg[b]: basis,url,rat,note=neg[b][p]
        extra=[n for n in notes.get(b,[]) if KEY.get(p) and KEY[p] in n.lower()]
        if q:
            note=(note+'; ' if note else '')+('search display: '+' | '.join(extra) if extra else 'no rating for this platform displayed in the search results')
            basis=basis or 'search_result_display'
        else:
            note=(note+'; ' if note else '')+'WEB SEARCH NOT RUN: the session web-search budget (200, shared by all agents) ran out before this building; offline sources and earlier evidence only'
            basis=basis or 'earlier_evidence'
        out.append({**base,'platform':p,'status':'not_seen','rating':'','rating_scale':'','review_count':'','basis':basis,'source_url':url,'search_query':q,'match_confidence':'','retrieved_at':rat,'note':note})
cols=['building_id','building_name','address','city','state','platform','status','rating','rating_scale','review_count','basis','source_url','search_query','match_confidence','retrieved_at','note']
tmp='data/evidence/ratings_census_part3.csv.tmp'
with open(tmp,'w',newline='') as f:
    w=csv.DictWriter(f,cols); w.writeheader(); w.writerows(out)
os.replace(tmp,'data/evidence/ratings_census_part3.csv')
# ---- summary
F=[r for r in out if r['status']=='found']
print('rows',len(out),'found',len(F),'buildings',len({r['building_id'] for r in out}))
for label,sub in [('ALL confidence',F),('excluding low',[r for r in F if r['match_confidence']!='low'])]:
    print('==',label)
    pp=collections.defaultdict(dict)
    for r in sub:
        c=int(r['review_count']) if r['review_count'] else None
        pp[r['platform']].setdefault(r['building_id'],[]).append(c)
    for p,d in sorted(pp.items(),key=lambda x:-len(x[1])):
        cs=[max(x for x in v if x is not None) for v in d.values() if any(x is not None for x in v)]
        print(f'  {p}: {len(d)} buildings; median review count {statistics.median(cs) if cs else "n/a"} (max per building)')
    rated={r['building_id'] for r in sub}
    nr=[t for t in T if t['building_id'] not in rated]
    print('  no rating on any platform:',len(nr),'| named',sum(1 for t in nr if t['building_name']),'unnamed',sum(1 for t in nr if not t['building_name']),'| by state',dict(collections.Counter(t['state'] for t in nr)),'| named by state',dict(collections.Counter(t['state'] for t in nr if t['building_name'])),'| unnamed by state',dict(collections.Counter(t['state'] for t in nr if not t['building_name'])))
    ns=[t for t in nr if t['building_id'] not in log]; print('  of which not web-searched:',len(ns))
    # best count any platform >= thresholds
    best=collections.defaultdict(int)
    for r in sub:
        if r['review_count']: best[r['building_id']]=max(best[r['building_id']],int(r['review_count']))
    print('  buildings whose largest single-platform count is >=20:',sum(1 for v in best.values() if v>=20),'; 5-19:',sum(1 for v in best.values() if 5<=v<20),'; 1-4:',sum(1 for v in best.values() if 1<=v<5))
print('searched',len(log),'not searched',len(T)-len(log), 'named',sum(1 for t in T if t['building_name']),'unnamed',sum(1 for t in T if not t['building_name']))
print('not searched ids:',[ (t['address'][:22]) for t in T if t['building_id'] not in log])
json.dump({'no_rating_named':[t['building_name']+' ('+t['city']+' '+t['state']+')' for t in T if t['building_id'] not in {r['building_id'] for r in F} and t['building_name']]},open(f'{D}/summary.json','w'),indent=1)
print(json.load(open(f'{D}/summary.json')))
