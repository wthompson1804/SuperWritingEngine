from R import *
H='nj:newark'; A=B(H)
NORTH=['b_080e9e0293','b_a564f7a7f5','b_0574ac1a01','b_afec34bc3d','b_68e3f26c07','b_e4066e3234','b_12be042caa','b_99ec10a746','b_879c33564e']
IRON=['b_e053355398','b_a6ae52079b','b_3eea33c4f6','b_2de6eb06b7','b_ffbbf4428e']
VAILS=['b_62ca4d5f02','b_3180b530b6']
WEST=['b_2a184be67b']; SOUTH=['b_3293e8ba54','b_8b3af85359']
assert set(NORTH+IRON+VAILS+WEST+SOUTH)==set(A), set(A)-set(NORTH+IRON+VAILS+WEST+SOUTH)
BB='https://www.essexcountyparks.org/parks/branch-brook-park'
BBD='https://essexcountynj.org/essex-county-executive-divincenzo-announces-the-opening-of-new-dog-park-in-essex-county-branch-brook-park/'
CB='https://essexcountyparks.org/parks/branch-brook-park/calendar/2026-essex-county-cherry-blossom-festival'
IP='https://essexcountyparks.org/parks/independence-park/about'
RF='https://www.newarkcityparks.org/riverfrontpark'
RD='https://www.newarkcityparks.org/events-_/14th-annual-river-day'
PD='https://www.newyorklatinculture.com/?p=80788'
IB='https://www.newarkhappening.com/neighborhoods/ironbound/'
VP='https://essexcountyparks.org/parks/vailsburg-park/about'
VD='https://essexcountynj.org/essex-county-executive-divincenzo-opens-dog-park-in-essex-county-vailsburg-park-renovation-of-playground-restroom-building-continues/'
WS='https://essexcountyparks.org/parks/west-side-park/about'
IR='https://essexcountyparks.org/parks/irvington-park/about'
WQ='https://essexcountyparks.org/parks/weequahic-park/about'
r(H,'neighborhood','Essex County park system','park','Newark sits in the first county park system in the United States, created in 1895; Branch Brook, at about 360 acres, is the largest of its parks.',
  'Essex County, press release on the Branch Brook Dog Park',BBD,'high')
r(H,'neighborhood','Newark Riverfront Park','park','Riverfront Park on the Passaic, first opened in 2013, now stretches to NJPAC; its newest section, "The Notch", opened in October 2024.',
  'Newark City Parks Foundation, Riverfront Park',RF,'high','Summer programs by Newark Riverfront Revival: festivals, music, kayaking, boat tours, rowing classes with Brick City Rowing.')
# North Ward
r(NORTH,'dog_walk','Branch Brook Park','park','Branch Brook Park, the nation\'s first county park, runs through the North Ward between Forest Hill and Roseville, with paths, a lake and the county\'s cherry tree collection.',
  'Essex County Parks, Branch Brook Park',BB,'high',ll='osm')
r(NORTH,'dog_walk','Branch Brook Park Dog Park','dog_run','Branch Brook Dog Park, opened in 2019 off the Heller Parkway entrance, has separate fenced areas for small and large dogs, with agility stations and dog water fountains.',
  'Essex County, press release on the Branch Brook Dog Park',BBD,'high','30,000 sq ft in the park\'s Northern Division near the maintenance facility.',ll='osm')
r(NORTH,'saturday','Essex County Cherry Blossom Festival','event','Each April Branch Brook Park holds the county Cherry Blossom Festival; 2026 was its 50th year.',
  'Essex County Parks, 2026 Cherry Blossom Festival calendar',CB,'high',schedule='April, yearly')
# Ironbound
r(IRON,'dog_walk','Independence Park','park','Independence Park is a 12.7-acre Olmsted-designed park in the Ironbound with a central bandstand, tree-lined promenades, fields and walking paths.',
  'Essex County Parks, Independence Park',IP,'high','No fenced dog run in the Ironbound was found; the nearest county dog park is in Branch Brook Park.',ll='osm')
r(['b_ffbbf4428e','b_e053355398'],'dog_walk','Riverfront Park','park','Newark Riverfront Park\'s riverside walkway and boardwalk run along the Passaic on the Ironbound\'s edge.',
  'Newark City Parks Foundation, Riverfront Park',RF,'high',ll='osm')
r(IRON,'saturday','Ferry Street','street','Ferry Street is the Ironbound\'s main eating street, a walk southeast from Newark Penn Station.',
  'Newark Happening (Newark tourism site), Ironbound',IB,'high')
r(IRON,'saturday','Portugal Day Festival','event','Each June the Portugal Day festival takes over Ferry Street for three days, with a main stage at Peter Francisco Park and a Sunday parade down Ferry Street.',
  'New York Latin Culture Magazine, 2026 festival guide',PD,'medium','2026 dates were June 12 to 14; parade Sunday 3pm. Not confirmed on an organizer\'s own page.',schedule='Mid-June, Friday to Sunday')
r(IRON+NORTH,'saturday','Newark River Day','event','The city\'s yearly River Day celebrates the Passaic waterfront with activities in Riverfront Park, usually near the "Orange Sticks" on Raymond Boulevard.',
  'Newark City Parks Foundation, event listing',RD,'high','2026: Saturday, June 20, 11am to 3pm.',schedule='One Saturday in June')
# Vailsburg
r(VAILS,'dog_walk','Vailsburg Park','park','Vailsburg Park is a 30-acre Olmsted-designed park with broad lawns, jogging paths, ballfields and a bandstand, beside the Garden State Parkway.',
  'Essex County Parks, Vailsburg Park',VP,'high',ll='osm')
r(VAILS,'dog_walk','Vailsburg Dog Park','dog_run','Vailsburg Park has had a county dog park since December 2023, with separate fenced areas for small and large dogs, agility equipment and dog fountains.',
  'Essex County, press release on the Vailsburg Dog Park opening',VD,'high','In the western section of the park; about 24,000 sq ft. Not mapped as a dog park in OpenStreetMap.')
# West Side
r(WEST,'dog_walk','West Side Park','park','West Side Park, 31 acres between South 13th and South 17th Streets, is one of the county\'s five original 1895 parks, designed by the Olmsted Brothers.',
  'Essex County Parks, West Side Park',WS,'high',ll='osm')
r(WEST+VAILS,'dog_walk','Vailsburg Dog Park','dog_run','The nearest county dog park is in Vailsburg Park (opened December 2023), with separate small and large dog areas.',
  'Essex County, press release on the Vailsburg Dog Park opening',VD,'medium','Nearest by our reading of the county list of dog parks; distance not measured.') if False else None
r(WEST,'dog_walk','Vailsburg Dog Park','dog_run','The nearest county dog park found is in Vailsburg Park (opened December 2023), with separate small and large dog areas.',
  'Essex County, press release on the Vailsburg Dog Park opening',VD,'medium','Nearest from the county\'s list of dog parks; distance not measured.')
# South
r(['b_8b3af85359','b_3293e8ba54'],'dog_walk','Irvington Park','park','Irvington Park, just over the Irvington line, is a 24-acre Olmsted Brothers park with tiered lawns and a small pond for fishing and model boats.',
  'Essex County Parks, Irvington Park',IR,'high',ll='osm')
r(SOUTH+WEST,'sunday','Weequahic Park','park','Weequahic Park in the South Ward is the county\'s second-largest developed park, 311 acres with an 80-acre lake, a jogging trail and summer concerts and festivals.',
  'Essex County Parks, Weequahic Park',WQ,'high')
r(VAILS+NORTH,'sunday','Branch Brook Park','park','On a Sunday, Branch Brook\'s lake, paths and cherry groves are the big park nearby.',
  'Essex County Parks, Branch Brook Park',BB,'high') if False else None
r(NORTH,'sunday','Branch Brook Park','park','For a long Sunday walk, Branch Brook stretches about 360 acres through the North Ward into Belleville.',
  'Essex County, press release on the Branch Brook Dog Park',BBD,'high')
r(IRON,'sunday','Portugal Day Parade','event','The Portugal Day parade runs down Ferry Street on the Sunday afternoon of the June festival.',
  'New York Latin Culture Magazine, 2026 festival guide',PD,'medium','2026: Sunday, June 14, 3pm, Wilson Ave to Newark Penn Station.',schedule='Mid-June Sunday, afternoon')
# weekday
supermarket_rows(A)
for b in A:
    c=nearest(b,'cafe')
    if c and c!='Starbucks': osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(SOUTH+WEST+VAILS,'saturday','Weequahic Park concerts and festivals','event','Weequahic Park hosts outdoor concerts and festivals in season around its 80-acre lake.',
  'Essex County Parks, Weequahic Park',WQ,'medium','Dates not given on the page read.',schedule='Summer')
r(SOUTH+WEST+VAILS,'saturday','Ferry Street','street','For a night out, Ferry Street in the Ironbound is Newark\'s main eating street, a walk southeast from Newark Penn Station.',
  'Newark Happening (Newark tourism site), Ironbound',IB,'high','Distance not measured.')
