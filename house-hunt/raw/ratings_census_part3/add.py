"""Append search-log and finding lines (read from stdin) with a timestamp.
Q|bid|query            -> search_log.tsv
F|bid|platform|rating|count|url|conf|note   -> search_findings.tsv (query = last Q for that bid)
N|bid|note             -> search_notes.tsv (things displayed that are not this building / no figures)"""
import sys,datetime,os
d=os.path.dirname(os.path.abspath(__file__)); now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
lastq={}
p=os.path.join(d,'search_log.tsv')
if os.path.exists(p):
    for l in open(p):
        a=l.rstrip('\n').split('\t'); lastq[a[0]]=a[1]
for l in sys.stdin:
    l=l.strip()
    if not l: continue
    a=l.split('|')
    if a[0]=='Q': open(p,'a').write('\t'.join([a[1],a[2],now])+'\n'); lastq[a[1]]=a[2]
    elif a[0]=='F':
        assert len(a)==8,l
        open(os.path.join(d,'search_findings.tsv'),'a').write('\t'.join(a[1:]+[lastq[a[1]],now])+'\n')
    elif a[0]=='N': open(os.path.join(d,'search_notes.tsv'),'a').write('\t'.join([a[1],'|'.join(a[2:]),now])+'\n')
    else: raise SystemExit('bad '+l)
