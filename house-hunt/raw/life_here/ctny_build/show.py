import json,sys
s=json.load(open('summ.json'))
for b in sys.argv[1:]:
    x=s[b]; print(b,x['addr'])
    for k in ('nearest_supermarket','nearest_dog_park','nearest_named_park','nearest_cafes','nearest_bakeries','nearest_bars','diner_ice_cream_examples','market_examples','cinema_theatre_examples'):
        v=x.get(k)
        if isinstance(v,list): print('  ',k,[(i[0],i[1],(i[2] or '').replace('https://www.openstreetmap.org/','')) for i in v[:5]])
