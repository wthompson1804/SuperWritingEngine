"""Evidence batch 9 helper: grep visible text of cached own-site pages. Usage: ev9_grep.py <key|all> <regex> [width]"""
import sys, json, re
sys.path.insert(0,'scripts')
from ev9_text import text
k, pat = sys.argv[1], sys.argv[2]; w = int(sys.argv[3]) if len(sys.argv) > 3 else 160
seen=set()
for l in open('raw/evidence_b9/_sites.jsonl'):
    x = json.loads(l)
    if x.get('status') != 200 or x.get('wall') or (k != 'all' and x['k'] != k) or x['url'] in seen: continue
    seen.add(x['url'])
    t = text(x['path']); hits=set()
    for m in re.finditer(pat, t, re.I):
        s = t[max(0, m.start()-w):m.end()+w].replace('\n', ' | ')
        if hits: break
        hits.add(s[:60]); print(f"[{x['k']}] {x['url']} @{x['retrieved_at']}\n    ...{s}")
