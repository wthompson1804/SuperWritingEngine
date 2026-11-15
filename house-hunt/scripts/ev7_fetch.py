"""Evidence batch 7: refetch listing URLs (refresh) into raw/evidence_b7/. Usage: ev7_fetch.py [--cached] [url ...]; no args = batch urls."""
import csv, sys, json
sys.path.insert(0, 'scripts')
from lib import cached_get
import lib
for h in ['www.trulia.com','www.zumper.com','www.apartmentlist.com']:
    lib.HOST_DELAY[h] = 2.5
def fetch(u, refresh=True):
    try:
        c, m = cached_get(u, 'evidence_b7', ext='html', refresh=refresh, retries=1)
        return m['status'], len(c), m.get('path'), m['retrieved_at']
    except Exception as e:
        return 'ERR', 0, repr(e)[:150], ''
if __name__ == '__main__':
    urls = sys.argv[1:]
    refresh = True
    if urls and urls[0] == '--cached':
        refresh = False; urls = urls[1:]
    if not urls:
        seen = []
        for r in csv.DictReader(open('data/reference/evidence_batches/batch_7.csv')):
            for u in r['urls'].split(' | '):
                if u not in seen: seen.append(u)
        urls = seen
    for u in urls:
        print(json.dumps([u, *fetch(u, refresh)]), flush=True)
