from R import *
JC=B('nj:jersey-city-greenville')+B('nj:jersey-city-bergen-lafayette')+B('nj:jersey-city-mcginley-square')+B('nj:jersey-city-journal-square')+B('nj:jersey-city-west-side')
BY=B('nj:bayonne')
LP='https://www.visithudson.org/lincoln-park/'
GP='https://www.visithudson.org/bayonne-park/'
RK='https://www.visithudson.org/things-to-do/attractions/richard-a-rutkowski-park/'
BDP='https://www.bayonnenj.org/Departments/division-of-parks'
BFM='https://www.visithudson.org/things-to-do/attractions/bayonne-farmers-market/'
BFM25='https://riverviewobserver.net/tag/now-open-bayonne-farmers-market/'
DINE='https://www.bayonnenj.org/_Content/pdf/Dine-Bayonne-2026.pdf'
SNAP='https://jerseydigs.com/snapdragon-coffee-social-now-open-190-monticello-avenue-jersey-city/'
LOEW='https://loewsjersey.com/'
NJA='https://www.njarts.net/182655'
haslp=[b for b in JC if any(t[1]=='Lincoln Park' for t in N[b]['park'])]
for h in ['nj:jersey-city-west-side','nj:jersey-city-mcginley-square']:
    r(h,'neighborhood','Lincoln Park','park','Lincoln Park is the oldest and largest Hudson County park: 150 acres east of Route 440 with fields, monuments and trails, and 123 acres along the Hackensack River to the west.',
      'Visit Hudson (Hudson County tourism office), Lincoln Park',LP,'high')
r('nj:jersey-city-journal-square','neighborhood',"Loew's Jersey Theatre",'theatre',"The Loew's Jersey, a 1929 \"Wonder Theatre\" on Journal Square, is back as a live venue for 2,600 to 4,000 people after a long restoration, with shows from November 2026.",
  "Loew's Jersey Theatre (official site)",LOEW,'high','Capacity from NJ Arts, 2026 (https://www.njarts.net/182655).')
r('nj:bayonne','neighborhood','Broadway','street',"Broadway is Bayonne's main street; about two-thirds of the places in the city's 2026 dining guide have a Broadway address.",
  'City of Bayonne, Dine Bayonne 2026 guide (PDF)',DINE,'high')
r(haslp,'dog_walk','Lincoln Park','park','Lincoln Park, the biggest county park in Hudson, has full-length trails and an enclosed dog run.',
  'Visit Hudson (Hudson County tourism office), Lincoln Park',LP,'high','Dog-run rules and hours are not published on that page.',ll='osm')
for b in JC:
    if b in haslp: continue
    p=N[b]['park'][0][1]
    osm_row([b],'dog_walk',p,'park',f'The nearest mapped park is {p}.','No official page found for this park. Lincoln Park, with the county\'s enclosed dog run, is the nearest big park. OSM data as of 2026-11-14.')
r(['b_21c3c3e483','b_8f314b2e2f','b_c4cb43f49a'],'weekday','Snapdragon Coffee & Social','cafe','Snapdragon, at 190 Monticello Avenue just south of Jewett, is a two-floor coffee house in a brick row house, open since November 2018.',
  'Jersey Digs (local news), 2019 opening feature',SNAP,'medium','Current hours not confirmed on its own page.',ll='osm')
for b in JC+BY:
    c=nearest(b,'cafe')
    if c and c not in ('Snapdragon Coffee & Social','Starbucks','Deli Plus','3 Guys From Italy','Cafe Bello','Hot & Toasty Bagels'):
        osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
supermarket_rows(JC+BY)
r(JC,'saturday',"Loew's Jersey Theatre",'theatre',"The restored Loew's Jersey on Journal Square is booking concerts and shows again; its calendar lists dates in November and December 2026.",
  "Loew's Jersey Theatre (official site)",LOEW,'high','Restoration and reopening: NJ Arts, 2026 (https://www.njarts.net/182655).')
# Bayonne
r(BY,'dog_walk','Sirius Dog Park and Oliva Mini Dog Park','dog_run','Bayonne\'s two city dog parks sit behind the Pony League and Little League fields in Dennis P. Collins Park: the Sirius park for large dogs and the Oliva mini park for small dogs, both on synthetic turf with agility pieces and dog fountains.',
  'City of Bayonne, Division of Parks',BDP,'high','At the south end of the city; distance not measured.',ll=('',''))
hasg=[b for b in BY+JC if any(t[1]=='Stephen R. Gregg Bayonne Park' for t in N[b]['park'])]
for b in hasg:
    o=osm(b,'Stephen R. Gregg Bayonne Park')
    r([b],'dog_walk','Stephen R. Gregg Park','park','Stephen R. Gregg Park is nearly 100 acres of Hudson County parkland on the Newark Bay waterfront, with sports fields and quiet lawns.',
      'Visit Hudson (Hudson County tourism office), Stephen R. Gregg Park',GP,'high',f'lat/lon from OpenStreetMap ({o[2]}).',ll=(o[0],o[1]))
r(BY,'weekday','Bayonne Farmers Market','market','The city farmers market sets up on Tuesday afternoons at West 23rd Street and Broadway.',
  'Visit Hudson (Hudson County tourism office), Bayonne Farmers Market',BFM,'medium','Visit Hudson says Tuesdays 2 to 7pm, June to November; the 2025 city notice (Riverview Observer, https://riverviewobserver.net/tag/now-open-bayonne-farmers-market/) gave May 27 to October 28. The 2026 season dates were not confirmed.',schedule='Tuesdays 2pm to 7pm, late spring to fall')
for b in BY+['b_99e0dbc360']:
    if any(t[1]=='Cafe Bello' for t in N[b]['cafe'][:2]):
        o=osm(b,'Cafe Bello')
        r([b],'weekday','Café Bello','cafe','Café Bello, an Italian café-restaurant at 1044 Avenue C, is in the city\'s 2026 dining guide.',
          'City of Bayonne, Dine Bayonne 2026 guide (PDF)',DINE,'high',f'lat/lon from OpenStreetMap ({o[2]}).',ll=(o[0],o[1]))
r(BY,'saturday','Broadway restaurants','street',"Bayonne's evening out is on Broadway: the city's 2026 guide lists places such as Adour Bistro (715 Broadway, French American, takes reservations) and The Well & Grill pub (879 Broadway).",
  'City of Bayonne, Dine Bayonne 2026 guide (PDF)',DINE,'high')
r(BY,'sunday','Richard A. Rutkowski Park','park','Next to Gregg Park, Rutkowski Park has a shaded bike path and a boardwalk along the water, with a butterfly garden and good bird watching.',
  'Visit Hudson (Hudson County tourism office), Rutkowski Park',RK,'high')
r(BY,'sunday','Union Grounds Coffee','cafe','For a Sunday coffee on Broadway, Union Grounds Coffee (199 Broadway) is in the city\'s 2026 dining guide.',
  'City of Bayonne, Dine Bayonne 2026 guide (PDF)',DINE,'medium','Opening days not given in the guide.')
