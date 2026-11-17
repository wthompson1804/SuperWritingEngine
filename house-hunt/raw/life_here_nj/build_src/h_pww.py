from R import *
PL=B('nj:plainsboro'); WW=B('nj:west-windsor')
DP='https://www.plainsboronj.com/248/Dog-Park'
PP='https://www.plainsboronj.com/397/Plainsboro-Preserve'
FM='https://www.westwindsorfarmersmarket.org/about/'
r('nj:plainsboro','neighborhood','Plainsboro Preserve','park','The township\'s Plainsboro Preserve on Scotts Corner Road covers over 1,000 acres of trails, woods and wetlands around 50-acre McCormack Lake.',
  'Plainsboro Township, Plainsboro Preserve',PP,'high','Trails open daily from 7am; the Rush Holt Environmental Education Center is open 10am to 4pm Tuesday to Sunday.')
r('nj:west-windsor','neighborhood','West Windsor Community Farmers Market','market','West Windsor\'s Saturday farmers market, in its 23rd season in 2026, has been voted New Jersey\'s favorite farmers market many times.',
  'West Windsor Community Farmers Market (own site)',FM,'high','Voted NJ favorite 2012 to 2020, 2022 and 2023 (American Farmland Trust), per the same page.')
r(PL,'dog_walk','Plainsboro Dog Park','dog_run','Plainsboro\'s township dog park is a fenced, unsupervised off-leash area open sunrise to sunset; dogs must be licensed, vaccinated and over six months, two dogs per adult, leashed until inside the gate.',
  'Plainsboro Township, Dog Park rules',DP,'high','Location of the dog park is not given on the rules page; distance not measured.',schedule='Sunrise to sunset')
r(PL,'dog_walk','Plainsboro Preserve (no pets)','park','Note: the Plainsboro Preserve trails do not allow pets.',
  'Plainsboro Township, Plainsboro Preserve',PP,'high')
for b in PL+WW:
    if N[b]['park']:
        p=N[b]['park'][0][1]
        osm_row([b],'dog_walk',p,'park',f'The nearest mapped park is {p}.','No official page for this park was read. OSM data as of 2026-11-14.')
supermarket_rows(PL+WW)
for b in PL+WW:
    c=nearest(b,'cafe')
    if c and c!='Starbucks': osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(PL+WW,'saturday','West Windsor Community Farmers Market','market','Every Saturday from 9am to 1pm the West Windsor market sells local produce, meat, cheese, bread, fish, wine and prepared food.',
  'West Windsor Community Farmers Market (own site)',FM,'high','Location (Vaughn Drive lot at Princeton Junction station) and season from search listings only; not confirmed on the market\'s own page read.',schedule='Saturdays 9am to 1pm, in season')
r(PL+WW,'sunday','Plainsboro Preserve','park','For a Sunday walk without the dog, the Plainsboro Preserve has trails around McCormack Lake and a nature center open Tuesday to Sunday.',
  'Plainsboro Township, Plainsboro Preserve',PP,'high',schedule='Trails daily from 7am; center Tue to Sun 10am to 4pm')
