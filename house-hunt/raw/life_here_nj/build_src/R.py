import json, hashlib, os
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/nj/'
P0='/home/user/SuperWritingEngine/house-hunt/raw/life_here/pages/'
P='/home/user/SuperWritingEngine/house-hunt/raw/life_here_nj/pages/'
C=json.load(open(S+'cands.json')); N=json.load(open(S+'near.json'))
HOOD={c['building_id']:c['hood_id'] for c in C}
def B(hood): return [c['building_id'] for c in C if c['hood_id']==hood]
def ra(url):
    k=hashlib.sha1(url.encode()).hexdigest()[:16]
    f=P+k+'.meta.json'
    if not os.path.exists(f): f=P0+k+'.meta.json'
    m=json.load(open(f))
    assert str(m['status'])=='200', url
    return m['retrieved_at']
OSM_RA='2026-11-15T18:32:19Z'
def osm(bid,name):
    for kind,L in N[bid].items():
        for t in L:
            if t[1]==name: return t[3],t[4],'https://www.openstreetmap.org/'+t[2]
    return None
ROWS=[]
def r(targets,moment,place,kind,fact,src,url,conf,notes='',schedule='',ll=None,hood=None):
    """targets: hood id string (neighborhood row) or list of building ids. ll='osm' to take OSM point by place name."""
    if isinstance(targets,str):
        targets=[(None,targets)]
    else:
        targets=[(b,HOOD[b]) for b in targets]
    at=OSM_RA if url.startswith('https://www.openstreetmap.org') else ra(url)
    for b,h in targets:
        lat=lon=''; nn=notes
        if ll=='osm' and b:
            o=osm(b,place)
            if o:
                lat,lon=o[0],o[1]
                if 'lat/lon from OpenStreetMap' not in nn: nn=(nn+' ' if nn else '')+f'lat/lon from OpenStreetMap ({o[2]}).'
        elif isinstance(ll,tuple): lat,lon=ll
        ROWS.append(dict(building_id=b or '',neighborhood_id=hood or h,moment=moment,place_name=place,place_kind=kind,fact=fact,schedule=schedule,lat=lat,lon=lon,source_name=src,source_url=url,retrieved_at=at,confidence=conf,notes=nn))
def osm_row(bids,moment,place,kind,fact,notes='Not checked on its own page. OSM data as of 2026-11-14 (Geofabrik extract).'):
    """OSM-only row (medium); per building, point & url from near.json"""
    for b in bids:
        o=osm(b,place)
        if not o: continue
        ROWS.append(dict(building_id=b,neighborhood_id=HOOD[b],moment=moment,place_name=place,place_kind=kind,fact=fact,schedule='',lat=o[0],lon=o[1],source_name='OpenStreetMap (project extract, 2026-11-14)',source_url=o[2],retrieved_at=OSM_RA,confidence='medium',notes=notes))
def nearest(b,kind,i=0):
    L=N[b][kind]; return L[i][1] if len(L)>i else None
def supermarket_rows(bids,skip=()):
    for b in bids:
        nm=nearest(b,'supermarket')
        if nm and nm not in skip: osm_row([b],'weekday',nm,'supermarket',f'The nearest mapped supermarket is {nm}.','Hours not checked. OSM data as of 2026-11-14 (Geofabrik extract).')
