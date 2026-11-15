"""Evidence batch 9: Apartment List building pages -> aggregate rating + review objects. Writes raw/evidence_b9/_al_reviews.json."""
import re, sys, json, csv
sys.path.insert(0, 'scripts')
import h_apartmentlist as A
rows = {r['building_url']: r for r in csv.DictReader(open('data/reference/evidence_batches/batch_9.csv'))}
idx = {}
for l in open('raw/evidence_b9/_index.jsonl'):
    x = json.loads(l)
    if x['status'] == 200: idx[x['url']] = x
out = {}
dec = json.JSONDecoder()
for u, r in rows.items():
    if 'apartmentlist' not in u: continue
    x = idx[u]; fl = A.flight(open(x['path'], encoding='utf-8', errors='replace').read())
    slug = u.split('apartmentlist.com')[1]
    agg = None
    m = re.search(r'"@id":"https://www\.apartmentlist\.com%s","@type":"Product","aggregateRating":(\{[^}]*\})' % re.escape(slug), fl)
    if m: agg = json.loads(m.group(1))
    revs = []
    for m in re.finditer(r'"reviews":(\[\{"propertyId")', fl):
        try:
            arr, _ = dec.raw_decode(fl[m.start(1):])
        except Exception: continue
        for rv in arr:
            if rv.get('propertyName') and rv not in revs: revs.append(rv)
    names = {rv.get('propertyName') for rv in revs}
    out[r['addr_key']] = {'url': u, 'at': x['retrieved_at'], 'agg': agg, 'reviews': revs}
    print('==', r['building_name'], agg and (agg.get('ratingValue'), agg.get('reviewCount')), len(revs), names)
    for rv in revs:
        print('    ', rv.get('submitDate', '')[:10], rv.get('overallScore'), '|', (rv.get('detail') or '')[:330].replace('\n', ' '))
json.dump(out, open('raw/evidence_b9/_al_reviews.json', 'w'), indent=1)
