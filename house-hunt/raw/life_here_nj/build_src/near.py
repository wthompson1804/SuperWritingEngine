import pickle, json
from pyproj import Transformer
import numpy as np
S='/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/nj/'
d=pickle.load(open('/home/user/SuperWritingEngine/house-hunt/raw/big/osm/places_index.pkl','rb'))
fw=Transformer.from_crs(4326,32618,always_xy=True); bw=Transformer.from_crs(32618,4326,always_xy=True)
C=json.load(open(S+'cands.json'))
from shapely.geometry import Point
from shapely.strtree import STRtree
pk=d['parks']; tree=STRtree(pk['geom'])
out={}
for c in C:
    x,y=fw.transform(c['lon'],c['lat']); res={}
    for kind,rad,n in [('cafe',1600,6),('bar',1600,5),('restaurant',1200,8),('bakery',1600,4),('brewery',3000,3),('supermarket',2500,4),('dog_park',4000,3),('music',2500,3)]:
        P=d['pts'][kind]; idx=P['tree'].query_ball_point([x,y],rad)
        L=[]
        for i in idx:
            nm=P['name'][i]
            if not nm: continue
            dd=float(np.hypot(P['xy'][i][0]-x,P['xy'][i][1]-y)); lo,la=bw.transform(*P['xy'][i])
            L.append((dd,nm,P['ref'][i],round(la,5),round(lo,5)))
        L.sort(); seen=set(); LL=[]
        for t in L:
            if t[1] in seen: continue
            seen.add(t[1]); LL.append(t)
        res[kind]=LL[:n]
    pt=Point(x,y); idx=tree.query(pt.buffer(1600))
    L=[]
    for i in idx:
        nm=pk['name'][i]
        if not nm or pk['area_m2'][i]<5000: continue
        g=pk['geom'][i]; dd=g.distance(pt); cc=g.representative_point(); lo,la=bw.transform(cc.x,cc.y)
        L.append((round(dd),nm,pk['ref'][i],round(la,5),round(lo,5),round(pk['area_m2'][i]/1e4,1),pk['kind'][i]))
    L.sort(); seen=set(); LL=[]
    for t in L:
        if t[1] in seen: continue
        seen.add(t[1]); LL.append(t)
    res['park']=LL[:6]
    out[c['building_id']]=res
json.dump(out,open(S+'near.json','w'))
