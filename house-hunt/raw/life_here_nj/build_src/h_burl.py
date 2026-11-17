from R import *
H='nj:burlington'; A=B(H)
EV='https://www.burlingtonnj.us/wp-content/uploads/2026/04/2026-Community-Events-Updated.pdf'
EM='https://evermorecoffee.com/'
r(H,'neighborhood','Riverfront Promenade','park','Burlington City\'s Riverfront Promenade on the Delaware is the town\'s stage, with food-truck Tuesdays, Thursday cruise nights, a folk arts festival and the trunk-or-treat in the city\'s 2026 calendar; parades run down High Street.',
  'City of Burlington, 2026 Events calendar (PDF, revised 29 April 2026)',EV,'high')
osm_row(A,'dog_walk','Riverfront Promenade','park','The Riverfront Promenade along the Delaware is the nearest mapped park, just by the building.','No dog rules found on a city page. OSM data as of 2026-11-14.')
r(A,'weekday','Evermore Coffee Roasters','cafe','Evermore Coffee Roasters, a café that roasts its own beans, is on the ground floor of this building at 1 East Pearl Street, open for indoor seating and takeaway.',
  'Evermore Coffee Roasters (own site)',EM,'high','Address from the city 2026 events calendar ("Evermore Coffee Roasters @ 1 E Pearl", https://www.burlingtonnj.us/wp-content/uploads/2026/04/2026-Community-Events-Updated.pdf). Hours not on the own page read.')
supermarket_rows(A)
r(A,'weekday','Food Truck Tuesday','event','Food trucks gather on the Riverfront Promenade on Tuesday evenings from 4pm through the warm months.',
  'City of Burlington, 2026 Events calendar (PDF)',EV,'high',schedule='Tuesdays 4pm, about every other week, May to September')
r(A,'saturday','Annual Wood Street Fair','event','The yearly Wood Street Fair fills Wood Street on a Saturday in September; Thursday cruise nights and an October car show use the Promenade.',
  'City of Burlington, 2026 Events calendar (PDF)',EV,'high','2026: Saturday, September 12, from 8am.',schedule='A Saturday in September')
r(A,'sunday','Carbs and Coffee','event','On one Sunday morning a month from spring to fall, the city calendar lists a "Carbs and Coffee" gathering at Evermore Coffee Roasters downstairs.',
  'City of Burlington, 2026 Events calendar (PDF)',EV,'high','2026 dates: May 24, June 28, July 26, Aug 23, Sept 27, 8am.',schedule='Monthly Sundays 8am, May to September')
