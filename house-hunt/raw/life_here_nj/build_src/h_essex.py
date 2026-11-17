from R import *
OR=B('nj:city-of-orange'); EO=B('nj:east-orange'); BL=B('nj:bloomfield'); WO=B('nj:west-orange')
MI='https://www.essexcountyparks.org/parks/monte-irvin-orange-park'
WP='https://essexcountyparks.org/parks/watsessing-park/programs'
WPA='https://www.essexcountyparks.org/parks/watsessing-park'
DUS='https://www.bloomfieldcenter.com/pub/gen/discovery/7'
SIX='https://njmonthly.com/articles/restaurant-reviews/six-points-pub-bloomfield'
EDH='https://www.nps.gov/edis/planyourvisit/hours.htm'
VAD='https://jerseydigs.com/valley-arts-district-seven-oaks-park-orange-new-jersey/'
HCK='https://hatcitykitchen.com/'
LUNA='https://www.lunastage.org/'
BBD='https://essexcountynj.org/essex-county-executive-divincenzo-announces-the-opening-of-new-dog-park-in-essex-county-branch-brook-park/'
r('nj:west-orange','neighborhood','Valley Arts District','district','The Valley, on the Orange and West Orange line, was the industrial Orange Valley of hat and shoe factories and is now an arts district.',
  'Jersey Digs (local news), December 2017',VAD,'medium')
r('nj:west-orange','neighborhood','Thomas Edison National Historical Park','museum',"Edison's laboratory complex in West Orange is a national park: visitors start at the lab visitor center and can go on to Glenmont, the family estate in Llewellyn Park.",
  'National Park Service, Thomas Edison NHP: Operating Hours & Seasons',EDH,'high')
# dog walk
mi=[b for b in OR+EO+WO if any(t[1]=='Orange Park' for t in N[b]['park'])]
for b in mi:
    o=osm(b,'Orange Park')
    r([b],'dog_walk','Monte Irvin Orange Park','park','Monte Irvin Orange Park is a 48-acre Olmsted-designed county park with walking paths, athletic fields and a playground.',
      'Essex County Parks, Monte Irvin Orange Park',MI,'high',f'lat/lon from OpenStreetMap ({o[2]}).',ll=(o[0],o[1]))
for b in OR+EO+BL+WO:
    o=osm(b,'Watsessing Dog Park')
    if not o: continue
    r([b],'dog_walk','Watsessing Dog Park','dog_run',"Essex County's first off-leash dog area, in Watsessing Park on Glenwood Avenue, is a 19,500-sq-ft fenced run with a stone-dust surface, benches, pet fountains and a double entry gate.",
      'Essex County Parks, Watsessing Park programs',WP,'high',f'lat/lon from OpenStreetMap ({o[2]}). Distance not measured.',ll=(o[0],o[1]))
ws=[b for b in BL+EO if any(t[1]=='Watsessing Park' for t in N[b]['park'])]
r(ws,'dog_walk','Watsessing Park','park','Watsessing Park is a 69-acre Olmsted-designed county park on the Bloomfield and East Orange line, with fields and a bandstand.',
  'Essex County Parks, Watsessing Park',WPA,'high',ll='osm')
for b in EO+OR+WO+BL:
    if b in mi or b in ws: continue
    if N[b]['park']:
        p=N[b]['park'][0][1]
        osm_row([b],'dog_walk',p,'park',f'The nearest mapped park is {p}.','No official page for this park was read. OSM data as of 2026-11-14.')
# weekday
supermarket_rows(OR+EO+BL+WO)
for b in BL+WO:
    c=nearest(b,'cafe')
    if c and c!='Starbucks': osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(BL,'weekday','Dinner Under the Stars','event','Every Friday evening from the last Friday in May to the first Friday in September, the heart of downtown Bloomfield turns into open-air dining with live entertainment.',
  'Bloomfield Center Alliance, Dinner Under the Stars',DUS,'high','9th year in 2026.',schedule='Fridays, late May to early September')
# saturday
r(BL,'saturday','Six Points Pub','bar','Six Points Pub on Bloomfield Avenue serves burgers and craft beer and runs trivia and karaoke nights.',
  'New Jersey Monthly',SIX,'medium','Not checked on its own page.',ll='osm')
r(OR+WO,'saturday','Hat City Kitchen','bar','Hat City Kitchen, in one of the oldest buildings in Orange, has live music several nights a week: bands, open-mic and blues jams; its profits go to reviving the Valley neighborhood.',
  'Hat City Kitchen (own site)',HCK,'high','In the Valley Arts District, per Jersey Digs (2017, https://jerseydigs.com/valley-arts-district-seven-oaks-park-orange-new-jersey/). Distance not measured.')
r(OR+EO,'saturday','Monte Irvin Orange Park concerts','event','Monte Irvin Orange Park hosts free concerts every summer.',
  'Essex County Parks, Monte Irvin Orange Park',MI,'medium','Dates not on the page.',schedule='Summer')
# sunday
r(OR+WO+EO,'sunday','Thomas Edison National Historical Park','museum',"Edison's West Orange laboratory, with his library and machine shops, is open whenever the park is; his Glenmont estate grounds usually open with it, and the garage of his cars opens Friday to Sunday as staffing allows.",
  'National Park Service, Thomas Edison NHP: Operating Hours & Seasons',EDH,'high')
r(BL,'sunday','Brookdale Park and Dog Park','park','Brookdale Park, on the Bloomfield and Montclair line, is an Essex County park with its own dog park (opened 2007).',
  'Essex County, press release listing county dog parks',BBD,'medium')
