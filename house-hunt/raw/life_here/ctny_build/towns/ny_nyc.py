import sys; sys.path.insert(0,__file__.rsplit('/',1)[0])
from _prior import carry
EL='b_73eecaf004'; JH='b_6b0a5d8f58'; RP='b_91121ba2c7'; JA='b_cffdb3842e'; BW='b_25caa353a4'; SP='b_d03c93be22'; GR='b_d47c36cd31'
OSMN='OpenStreetMap (project extract, 2026-11-14)'
T_JH='https://www.nyctourism.com/boroughs-neighborhoods/queens/jackson-heights/'
T_JA='https://www.nyctourism.com/new-york/queens/jamaica/'
T_SP='https://www.nyctourism.com/new-york/brooklyn/sunset-park/'
T_FH='https://www.nyctourism.com/new-york/queens/forest-hills/'
T_CI='https://www.nyctourism.com/new-york/brooklyn/coney-island/'
DOT34='https://nyc.gov/34ave'
T7='https://www.terraza7.com/'
JD='https://www.jacksondiner.com/'
BL='https://www.forestparkbarkinglot.org/rules/'
FPT='https://www.forestparktrust.org/'
KM='https://www.kingmanor.org/'
IC='https://industrycity.com/'
def osm(bids,moment,name,kind,fact,ref,notes='OSM only; not checked on its own page.'):
    return dict(bids=bids,moment=moment,place_name=name,place_kind=kind,fact=fact,source_name=OSMN,source_url='https://www.openstreetmap.org/'+ref,confidence='medium',notes=notes,osm=ref if ref.startswith('node') else None)
ROWS=[
 # Jackson Heights / Elmhurst
 dict(bids=[''],hood='ny:jackson-heights',moment='neighborhood',place_name='34th Avenue Open Street (Paseo Park)',place_kind='street',fact='34th Avenue is being rebuilt as the city\'s first permanent Open Street, a car-light corridor from 69th to 96th Street, after a 1.3-mile temporary open street proved popular.',source_name='NYC DOT: 34th Avenue Open Street',source_url=DOT34,confidence='high',notes='NYC DOT shared a draft capital design framework in fall 2025; construction timing not stated.'),
 dict(bids=[''],hood='ny:jackson-heights',moment='neighborhood',place_name='Jackson Heights nightlife',place_kind='neighborhood',fact='The city tourism office singles out Jackson Heights for its food and an active nightlife scene.',source_name='NYC Tourism + Conventions: Jackson Heights',source_url=T_JH,confidence='high'),
 dict(bids=[JH],moment='dog_walk',place_name='34th Avenue Open Street',place_kind='street',fact='The building is on 34th Avenue\'s open street, a long pedestrian-priority corridor for walks.',source_name='NYC DOT: 34th Avenue Open Street',source_url=DOT34,confidence='high',notes='Current open hours were not on the page. Travers Park is the nearest mapped park (OSM); NYC Parks refuses us, so no park dog rules.'),
 osm([JH],'dog_walk','Travers Park','park','The nearest mapped park is Travers Park, on 34th Avenue.','way/134158685','OSM only; NYC Parks site refuses us, so rules and off-leash hours were not read.'),
 osm([EL],'dog_walk','Sherry Dog Run','dog_park','The nearest mapped dog run is the Sherry Dog Run.','way/374134774','OSM only; NYC Parks and NYC Open Data refuse us, so status and rules were not read.'),
 osm([JH],'weekday','Over the Moon Juice & Coffee','cafe','The nearest mapped cafe is Over the Moon Juice & Coffee.','node/2570139436'),
 osm([JH],'weekday','Key Food','supermarket','The nearest mapped supermarket is Key Food.','node/5344148021','OSM only; hours not checked.'),
 osm([EL],'weekday','Better Half','cafe','The nearest mapped cafes are Better Half and Tea Cup Cafe.','node/13142395240'),
 osm([EL],'weekday','Tindahan','supermarket','The nearest mapped supermarket is Tindahan, a small grocery.','node/2570185564','OSM only; hours not checked.'),
 dict(bids=[EL,JH],moment='saturday',place_name='Terraza 7',place_kind='bar',fact='Terraza 7 is a bar and live-music room with performances almost every night, from jazz fusion to cumbia.',schedule='Open daily 4pm to 4am; shows from 7pm',source_name='Terraza 7 (own site)',source_url=T7,confidence='high',notes='40-19 Gleane St, Elmhurst. Site lists sets on Nov 17, 18 and 20, 2026.'),
 dict(bids=[EL,JH],moment='saturday',place_name='Jackson Diner',place_kind='restaurant',fact='Jackson Diner has served North and South Indian food in Jackson Heights since 1980.',schedule='Sun to Thu 11:30am to 9pm; Fri and Sat to 10pm',source_name='Jackson Diner (own site)',source_url=JD,confidence='high'),
 # Rego Park
 dict(bids=[''],hood='ny:rego-park',moment='neighborhood',place_name='Forest Park',place_kind='park',fact='Forest Park, one of the oldest parks in the city, is a 543-acre oak forest with trails, a bandshell, a carousel and a golf course.',source_name='The Forest Park Trust',source_url=FPT,confidence='high'),
 dict(bids=[RP,JA,BW],moment='dog_walk',place_name='Forest Park Barking Lot',place_kind='dog_park',fact='Forest Park\'s fenced dog run, the Barking Lot: licensed and rabies-vaccinated dogs, at most three per person, leashed on the way out.',source_name='Forest Park Barking Lot (volunteer group site, quoting NYC Parks rules)',source_url=BL,confidence='medium',notes='Hours not on the page. Dogs may not be off leash elsewhere in the Overlook area. NYC Parks site refuses us.',osm=None),
 osm([RP],'weekday','C-Town','supermarket','The nearest mapped supermarket is C-Town.','node/2569755214','OSM only; hours not checked.'),
 osm([RP],'weekday','Bagelette','cafe','Mapped cafes nearby include Bagelette and Gong Cha.','node/2689493100'),
 dict(bids=[RP],moment='saturday',place_name='Forest Hills Stadium',place_kind='music',fact='Next door in Forest Hills, the old tennis stadium is now a seasonal outdoor concert venue.',source_name='NYC Tourism + Conventions: Forest Hills',source_url=T_FH,confidence='medium',notes='Season is summer to early fall.'),
 dict(bids=[RP],moment='saturday',place_name="Eddie's Sweet Shop",place_kind='other',fact="Eddie's Sweet Shop in Forest Hills is an old-school ice cream parlor, open since 1925 and run as Eddie's since 1967.",source_name='NYC Tourism + Conventions: Forest Hills',source_url=T_FH,confidence='medium',notes='Not checked on its own page.'),
 dict(bids=[RP,JA,BW],moment='sunday',place_name='Forest Park',place_kind='park',fact='Forest Park\'s 543-acre oak woods have hiking trails and bird watching, plus a carousel and bandshell.',source_name='The Forest Park Trust',source_url=FPT,confidence='high'),
 # Jamaica / Briarwood
 dict(bids=[''],hood='ny:jamaica',moment='neighborhood',place_name='Jamaica',place_kind='neighborhood',fact='Jamaica is best known as a transit hub linking much of the city to JFK, with restaurants and groceries along Liberty Avenue.',source_name='NYC Tourism + Conventions: Jamaica',source_url=T_JA,confidence='high'),
 dict(bids=[''],hood='ny:jamaica',moment='neighborhood',place_name='King Manor Museum',place_kind='museum',fact='King Manor, the home of Founding Father and antislavery advocate Rufus King, is a museum in Rufus King Park on Jamaica Avenue.',source_name='King Manor Museum (own site)',source_url=KM,confidence='high',notes='150-03 Jamaica Avenue.'),
 dict(bids=[JA,BW],moment='sunday',place_name='King Manor Museum',place_kind='museum',fact='King Manor Museum, Rufus King\'s restored house, runs tours and exhibitions on the fight against slavery.',schedule='Fall and winter: Thursday to Saturday, noon to 4pm',source_name='King Manor Museum (own site)',source_url=KM,confidence='high',notes='Open Saturday, not Sunday, in fall and winter.'),
 osm([JA],'weekday','Ideal Food Basket','supermarket','The nearest mapped supermarket is Ideal Food Basket.','node/9527202757','OSM only; hours not checked.'),
 osm([BW],'weekday','Aftab Supermarket','supermarket','The nearest mapped supermarket is Aftab Supermarket.','node/6207551264','OSM only; hours not checked.'),
 osm([JA,BW],'weekday','Coffee Cloud','cafe','Coffee Cloud is the nearest mapped independent cafe.','node/11731646617'),
 # Sunset Park
 dict(bids=[''],hood='ny:sunset-park-east-borough-park-west-',moment='neighborhood',place_name='Fifth and Eighth Avenues',place_kind='street',fact='Fifth and Eighth Avenues are Sunset Park\'s busy shopping streets, lined with restaurants, bakeries and grocers.',source_name='NYC Tourism + Conventions: Sunset Park',source_url=T_SP,confidence='high'),
 dict(bids=[''],hood='ny:sunset-park-east-borough-park-west-',moment='neighborhood',place_name='Sunset Park (the park)',place_kind='park',fact='The neighborhood is named for its hilltop park, which has views across the harbor to the Manhattan skyline.',source_name='NYC Tourism + Conventions: Sunset Park',source_url=T_SP,confidence='high'),
 dict(bids=[SP],moment='dog_walk',place_name='Sunset Park',place_kind='park',fact='The hilltop park has harbor and skyline views and family activities.',source_name='NYC Tourism + Conventions: Sunset Park',source_url=T_SP,confidence='medium',notes='No dog rules read (NYC Parks refuses us). Nearest mapped dog run: Greenwood Playground Dog Run (OSM, https://www.openstreetmap.org/way/997306758).'),
 osm([SP],'weekday','FillUp Coffee','cafe','Mapped cafes nearby include FillUp Coffee and Liebre Cafe.','node/11079620505'),
 osm([SP],'weekday',"Jenny's Food Market",'supermarket',"The nearest mapped supermarket is Jenny's Food Market.",'node/5728827342','OSM only; hours not checked.'),
 dict(bids=[SP],moment='saturday',place_name='Industry City',place_kind='market',fact='Industry City on the waterfront has more than 35 places to eat and drink, a distillery, design shops, galleries and a weekend market.',source_name='Industry City (own site)',source_url=IC,confidence='high',notes='Says it hosts over 1,000 events a year.'),
 dict(bids=[SP],moment='sunday',place_name='Green-Wood Cemetery',place_kind='park',fact='Green-Wood Cemetery, next to Sunset Park, is a classic place for long walks.',source_name='NYC Tourism + Conventions: Sunset Park',source_url=T_SP,confidence='medium',notes='Dog rules not checked (dogs are usually not allowed in cemeteries; confirm).'),
 # Gravesend / Coney Island
 dict(bids=[''],hood='ny:gravesend-south-',moment='neighborhood',place_name='Coney Island',place_kind='neighborhood',fact='Coney Island, home of the Cyclone, the Wonder Wheel, the original Nathan\'s and the Boardwalk, is a seaside playground that is also a real neighborhood.',source_name='NYC Tourism + Conventions: Coney Island',source_url=T_CI,confidence='high'),
 osm([GR],'weekday','Food Bazaar','supermarket','The nearest mapped supermarket is Food Bazaar.','way/248841441','OSM only; hours not checked.'),
 osm([GR],'weekday','Café Dacha','cafe','Mapped cafes nearby include Café Dacha and Milk+Honey Coffee+Kitchen.','node/11030368694'),
 dict(bids=[GR],moment='saturday',place_name='Coney Island Brewing Company',place_kind='bar',fact='Coney Island Brewing makes Coney-themed beers such as Mermaid Pilsner by the Boardwalk.',source_name='NYC Tourism + Conventions: Coney Island',source_url=T_CI,confidence='medium',notes='Not checked on its own page; Coney Island is busiest in summer.'),
 dict(bids=[GR],moment='saturday',place_name='Coney Island events',place_kind='event',fact='Coney Island\'s big yearly events are the Mermaid Parade, the Polar Bear Plunge and the Nathan\'s hot-dog-eating contest.',source_name='NYC Tourism + Conventions: Coney Island',source_url=T_CI,confidence='medium',notes='The page gives no dates.'),
 dict(bids=[GR],moment='sunday',place_name='Coney Island Boardwalk and New York Aquarium',place_kind='park',fact='At the eastern end of the Boardwalk, the New York Aquarium has seals, sea lions, rays and sharks.',source_name='NYC Tourism + Conventions: Coney Island',source_url=T_CI,confidence='medium'),
]
ROWS+=carry('ny:bath-beach',[('dog_walk','Shore Parkway Greenway',None)],[GR],'Carried over from the first Life-here round (Bath Beach); the greenway runs along Shore Parkway past this building.')
for r in ROWS:
    if r.get('place_name')=='Shore Parkway Greenway': r['lat']=r['lon']=''
ROWS.append(dict(bids=[JA,BW],moment='saturday',place_name='Jamaica Center for Arts and Learning (JCAL)',place_kind='music',fact='JCAL on Jamaica Avenue runs a Thursday Night Jazz series, plays, dance weekends and art classes.',schedule='Thursday Night Jazz: Tyreek McDole, December 10, 2026, 8pm',source_name='Jamaica Center for Arts and Learning (own site)',source_url='https://www.jcal.org/',confidence='high',notes='153-10 Jamaica Avenue. A Thursday series; no Saturday bar strip was confirmed near these buildings.'))
