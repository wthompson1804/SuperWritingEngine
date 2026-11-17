import re
def nice(r):
    r=re.sub(r'\s*\((?:I|US|NY|CT|NJ|CR) ?\d+[^)]*\)','',r).strip()
    r=re.sub(r'\s*\((GCP|BP|HR)\)','',r)
    r=r.replace('I 95','I-95').replace('I 87','I-87').replace('I 678','I-678').replace('I 495','I-495')
    r=re.sub(r'^CT (\d+)',r'Route \1',r); r=re.sub(r'^NY (\d+)',r'Route \1',r); r=re.sub(r'^NJ (\d+)',r'NJ Route \1',r)
    r=r.replace('US 6; NY 17','US 6 / Route 17').replace('NY 208','Route 208')
    r=r.replace('Rossevelt','Roosevelt').replace('State Highway 208','Route 208')
    return r
def fact(roads):
    seen=[]
    for r in roads:
        n=nice(r)
        if n=='New England Thruway' and 'I-95' in seen: continue
        if n and n not in seen: seen.append(n)
    if len(seen)==1: return f'The mapped route is a short local drive on {seen[0]} to Jamaica.'
    return 'The mapped route to Jamaica follows ' + ', '.join(seen[:-1]) + ' and ' + seen[-1] + '.'
