from R import *
TR=B('nj:trenton'); LW=B('nj:lawrence'); HM=B('nj:hamilton')
TFM='https://www.thetrentonfarmersmarket.com/'
ELL='https://ellarslie.org/'
WHY='https://whyy.org/articles/what-trentons-central-park-once-looked-like/'
r('nj:trenton','neighborhood','Cadwalader Park','park','Cadwalader Park, 109.5 acres designed by Frederick Law Olmsted, is the largest park in Trenton, with the Ellarslie mansion at its center.',
  'WHYY (public media)',WHY,'high','The D&R Canal State Park path also reaches the park, per the same article.')
r('nj:lawrence','neighborhood','Trenton Farmers Market','market','The Trenton Farmers Market, a farmer-owned cooperative since 1939, has been on Spruce Street in Lawrence since 1948.',
  'Trenton Farmers Market (own site)',TFM,'high','960 Spruce Street, Lawrence Township.')
cad=[b for b in TR if any(t[1]=='Cadwalader Park' for t in N[b]['park'])]
r(cad,'dog_walk','Cadwalader Park','park','Cadwalader Park, Trenton\'s 109.5-acre Olmsted park, has winding paths up to Ellarslie and links to the D&R Canal path.',
  'WHYY (public media)',WHY,'high','No dog rules or dog run found on a city page.',ll='osm')
dr=[b for b in TR+LW+HM if any(t[1]=='Delaware and Raritan Canal State Park' for t in N[b]['park'][:3])]
osm_row(dr,'dog_walk','Delaware and Raritan Canal State Park','park','A mapped stretch of the Delaware and Raritan Canal State Park, with its towpath, is near the building.','State park rules not read (nj.gov refused us this session). OSM data as of 2026-11-14.')
for b in LW+HM:
    if b in dr: continue
    if N[b]['park']:
        p=N[b]['park'][0][1]
        osm_row([b],'dog_walk',p,'park',f'The nearest mapped park is {p}.','No official page for this park was read. OSM data as of 2026-11-14.')
supermarket_rows(TR+LW+HM)
for b in TR+LW+HM:
    c=nearest(b,'cafe')
    if c and c!='Starbucks': osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(TR+LW,'saturday','Trenton Farmers Market','market','The indoor Trenton Farmers Market sells Jersey Fresh produce, Amish meats and poultry, a Polish deli and kielbasa, cheese and baked goods.',
  'Trenton Farmers Market (own site)',TFM,'high','Regular hours on its page: Wednesday to Saturday 9am to 6pm, Sunday 10am to 4pm; the page also lists other seasonal schedules.',schedule='Wed to Sat 9am to 6pm, Sun 10am to 4pm (regular schedule)')
r(TR,'saturday','Trenton City Museum at Ellarslie','museum','The Trenton City Museum in Ellarslie mansion, in Cadwalader Park, shows art and Trenton history and holds weekend events such as a holiday market (November 21 and 22, 2026) and a Sunday cabaret.',
  'Trenton City Museum at Ellarslie (own site)',ELL,'high','Dangerous Women 3 Cabaret: Sunday, December 6, 1 to 3pm.')
r(TR+LW,'sunday','Trenton Farmers Market','market','On Sundays the Trenton Farmers Market opens 10am to 4pm.',
  'Trenton Farmers Market (own site)',TFM,'high',schedule='Sundays 10am to 4pm (regular schedule)')
