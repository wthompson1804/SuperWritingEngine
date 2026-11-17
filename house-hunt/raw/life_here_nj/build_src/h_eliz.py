from R import *
H='nj:elizabeth'; A=B(H)
WD='https://ucnj.org/press-releases/public-info/2018/12/11/new-dog-park-opens-at-warinanco-park-in-roselle-becomes-second-county-wide-facility-for-canines/'
GH='https://www.goelizabethnj.com/'
FE='https://www.goelizabethnj.com/events/festivals/'
BA='https://www.goelizabethnj.com/restaurants/bars-and-lounges/'
r(H,'neighborhood','Elizabeth','city','Elizabeth, founded in 1664 as Elizabethtown, was the first capital of New Jersey.',
  'Visit Elizabeth (Elizabeth Destination Marketing Organization)',GH,'high','The old Elizabeth train station is becoming a visitor welcome center and living museum, per the same site.')
r(A,'dog_walk','Warinanco Dog Park','dog_run','Union County\'s Warinanco Dog Park, behind the Warinanco Sports Center at 1 Park Drive (Roselle side), has separate large and small dog areas with agility equipment and dog fountains, open dawn to dusk every day.',
  'Union County, press release on the dog park opening (December 2018)',WD,'high','Opened December 2018; county parks keep dawn-to-dusk hours, per the release.',schedule='Daily, dawn to dusk',ll='osm')
war=[b for b in A if any(t[1]=='Warinanco Park' for t in N[b]['park'])]
r(war,'dog_walk','Warinanco Park','park','Warinanco Park, about 200 acres on the Elizabeth and Roselle line, is the big park for long walks.',
  'Visit Elizabeth (Elizabeth Destination Marketing Organization), festivals page',FE,'high',ll='osm')
for b in A:
    if b in war: continue
    p=N[b]['park'][0][1]
    osm_row([b],'dog_walk',p,'park',f'The nearest mapped park is {p}.','No official page for this park was read. OSM data as of 2026-11-14.')
supermarket_rows(A)
for b in A:
    c=nearest(b,'cafe')
    if c: osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(A,'saturday','Barcode','bar','Barcode is a sports bar, restaurant and nightclub with a giant LED screen, pool tables and an indoor heated line.',
  'Visit Elizabeth (Elizabeth Destination Marketing Organization), bars and lounges',BA,'medium','Listed on the tourism site; not checked on its own page.',ll='osm')
r(A,'saturday','Elizabeth Portugal Day Parade','event','The city\'s Portugal Day Parade has filled the streets every year since 1978; other yearly parades and festivals run from May through the summer.',
  'Visit Elizabeth (Elizabeth Destination Marketing Organization), festivals page',FE,'high','Also listed: Cuban Day Parade (May), Peterstown Cultural Festival, Puerto Rican parade and festival, Midtown Car & Bike Show. Dates not given on that page.',schedule='Yearly')
r(A,'sunday','Warinanco Park','park','For a Sunday walk, Warinanco Park\'s 200 acres are the nearest big park.',
  'Visit Elizabeth (Elizabeth Destination Marketing Organization), festivals page',FE,'high')
