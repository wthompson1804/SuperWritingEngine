import sys; sys.path.insert(0,__file__.rsplit('/',1)[0])
from _prior import carry
ST='b_5f667364a3'; BP='b_4278658026'
AUD='https://ct.audubon.org/conservation/share-love-sharetheshore'
BEA='https://www.bridgeportct.gov/government/departments/parks-recreation/beardsley-park-history'
OSMN='OpenStreetMap (project extract, 2026-11-14)'
NOTE_ST='Carried over from the first Life-here round (downtown Stamford). 1078 East Main St is on the East Side, a short drive or bus ride from downtown.'
NOTE_BP='Carried over from the first Life-here round (downtown Bridgeport). 150 Anton St is in the North End, a drive or bus ride up Main Street from downtown.'
ROWS=[]
ROWS+=carry('ct:stamford',[('saturday','Barcelona Wine Bar',None),('saturday','Palace Theatre Stamford',None),('saturday','Stamford Downtown Farmers Market',None),('sunday','Barcelona Wine Bar',None),('dog_walk','Mill River Park',None)],[ST],NOTE_ST)
ROWS+=carry('ct:bridgeport',[('saturday','Berlinetta Brewing Company',None),('saturday','The Bijou Theatre',None),("saturday","Vinnie Brand's Stress Factory Comedy Club",None),('sunday','Gold Note Jazz at Berlinetta',None),('dog_walk','Seaside Park','six-foot')],[BP],NOTE_BP)
for r in ROWS:
    if r['moment']=='dog_walk' and r['place_name']=='Mill River Park': r['moment']='sunday'
    if r['moment']=='dog_walk' and r['place_name']=='Seaside Park':
        r['place_name']='Bridgeport city parks'; r['lat']=r['lon']=''
ROWS+=[
 dict(bids=[ST],moment='dog_walk',place_name='Stamford Dog Park (Courtland Park)',place_kind='dog_park',fact='The city dog park is at Courtland Park, 39 Courtland Avenue, close to the building.',source_name='Audubon Connecticut: Dogs on Beaches, State and Local Laws (dog-friendly parks list)',source_url=AUD,confidence='medium',notes='stamfordct.gov refuses us, so hours and rules were not read. OSM maps it as Courtland Dog Park.',osm='node/2912033963'),
 dict(bids=[ST],moment='dog_walk',place_name='Edward Hunt Recreation Area',place_kind='park',fact='The nearest mapped park is the Edward Hunt Recreation Area.',source_name=OSMN,source_url='https://www.openstreetmap.org/way/43399475',confidence='medium',notes='OSM only.'),
 dict(bids=[ST],moment='weekday',place_name='ShopRite',place_kind='supermarket',fact='The nearest mapped supermarket is ShopRite.',source_name=OSMN,source_url='https://www.openstreetmap.org/node/7972040624',confidence='medium',notes='OSM only; hours not checked. No cafe is mapped within walking range.',osm='node/7972040624'),
 dict(bids=[ST],moment='saturday',place_name='Seaside Tavern',place_kind='bar',fact='The nearest mapped bar is Seaside Tavern.',source_name=OSMN,source_url='https://www.openstreetmap.org/node/1324008674',confidence='medium',notes='OSM only; not checked on its own page.',osm='node/1324008674'),
 dict(bids=[''],hood='ct:bridgeport',moment='neighborhood',place_name='Beardsley Park',place_kind='park',fact='Beardsley Park, designed by Frederick Law Olmsted in 1884, is 125 acres of rolling parkland along the Pequonnock River and holds Connecticut\'s only zoo.',source_name='City of Bridgeport, Parks & Recreation: Beardsley Park History',source_url=BEA,confidence='high'),
 dict(bids=[BP],moment='dog_walk',place_name='Beardsley Park',place_kind='park',fact='Beardsley Park in the North End has open fields sloping to Bunnell\'s Pond, stone bridges and tree-lined paths.',source_name='City of Bridgeport, Parks & Recreation: Beardsley Park History',source_url=BEA,confidence='high',notes='Entrance from Noble Avenue. The nearest mapped park to the building is Elton G. Rogers Park (OSM). City park rules apply (six-foot leash).'),
 dict(bids=[BP],moment='weekday',place_name='Price Rite',place_kind='supermarket',fact='The nearest mapped supermarket is Price Rite.',source_name=OSMN,source_url='https://www.openstreetmap.org/way/204056731',confidence='medium',notes='OSM only; hours not checked.'),
 dict(bids=[BP],moment='weekday',place_name='Galaxy Diner and Main Street Creamery',place_kind='restaurant',fact='A diner (Galaxy Diner) and an ice cream shop (Main Street Creamery) are mapped close by on Main Street.',source_name=OSMN,source_url='https://www.openstreetmap.org/way/204056658',confidence='medium',notes='OSM only; not checked on their own pages. Nearest mapped cafe is 7 Brew, a drive-through coffee chain.'),
]
