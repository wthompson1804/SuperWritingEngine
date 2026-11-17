from R import *
A=B('nj:new-brunswick')
DOG='https://getoutsidenj.com/places/donaldson-park-off-leash-dog-area-highland-park-middlesex-county-new-jersey'
FM='https://magic983.com/2026/02/23/highland-park-farmers-market-returns-march-6-for-weekly-season-through-december/'
MS='https://www.mainstreethp.org/'
HM='https://www.harvestmoonbrewery.com/'
r(A,'dog_walk','Donaldson Park','park','Across the Raritan in Highland Park, Donaldson Park is a 90-acre Middlesex County riverfront park with fields, picnic groves, playgrounds and a boat ramp.',
  'GetOutsideNJ (park directory)',DOG,'medium','The county parks site refused us (403), so the county page was not read.',ll='osm')
r(A,'dog_walk','Donaldson Park Off Leash Dog Area','dog_run','Donaldson Park\'s off-leash dog area, off South 2nd Avenue, has separate sections for large and small dogs; leash laws apply outside it.',
  'GetOutsideNJ (park directory)',DOG,'medium','Middlesex County runs it; its own page refused us (403).',ll=('',''))
for b in A:
    o=osm(b,'Donaldson Dog Park')
    if o:
        ROWS[-1]['lat'],ROWS[-1]['lon']=o[0],o[1]; ROWS[-1]['notes']+=f' lat/lon from OpenStreetMap ({o[2]}).'
supermarket_rows(A)
for b in A:
    c=nearest(b,'cafe')
    if c and c!='Starbucks': osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(A,'weekday','Highland Park Farmers Market','market','Highland Park\'s farmers market sets up every Friday, rain or shine, next to 212 Raritan Avenue downtown, from March to mid-December.',
  'Magic 98.3 FM (local radio), February 2026',FM,'medium','2026: March 6 to December 11; 11am to 4pm in March, November and December, to 5pm April to October. Run by Main Street Highland Park.',schedule='Fridays 11am to 4pm or 5pm, March to mid-December')
r(A,'saturday','Downtown Highland Park (Raritan Avenue)','street','Raritan Avenue in Highland Park is a small downtown run by a business district that holds dozens of events a year, such as Small Business Weekend and the tree lighting (November 28 and 29, 2026).',
  'Main Street Highland Park (downtown business district)',MS,'high')
r(A,'saturday','Harvest Moon Brewery & Cafe','bar','Harvest Moon, at 392 George Street in downtown New Brunswick, brews its own beer, serves American food and has live local music.',
  'Harvest Moon Brewery & Cafe (own site)',HM,'high',ll='osm')
PS=B('nj:piscataway')
r(PS,'saturday','Harvest Moon Brewery & Cafe','bar','The nearest downtown for a night out is New Brunswick, where Harvest Moon at 392 George Street brews its own beer and has live local music.',
  'Harvest Moon Brewery & Cafe (own site)',HM,'high','Distance not measured.',ll='osm')
