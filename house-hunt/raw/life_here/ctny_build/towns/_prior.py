import csv
P='/home/user/SuperWritingEngine/house-hunt/data/reference/life_here_facts.csv'
C=['moment','place_name','place_kind','fact','schedule','lat','lon','source_name','source_url','retrieved_at','confidence','notes']
def carry(hood, picks, bids, extra_note):
    """picks: list of (moment, place_name, fact-substring or None)"""
    out=[]; seen=set()
    for r in csv.DictReader(open(P)):
        if r['neighborhood_id']!=hood or not r['building_id']: continue
        for m,pn,sub in picks:
            if r['moment']==m and r['place_name']==pn and (sub is None or sub in r['fact']):
                k=(m,pn,r['fact'])
                if k in seen: continue
                seen.add(k)
                d={c:r[c] for c in C}
                d['notes']=(d['notes']+' ' if d['notes'] else '')+extra_note
                d['bids']=list(bids); out.append(d)
    return out
