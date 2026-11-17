from R import *
A=B('nj:long-branch')
AC='https://longbranch.org/157/Animal-Control'
SP='https://www.monmouthcountyparks.com/page.aspx?Id=2535'
WH='https://www.monmouthcountyparks.com/page.aspx?Id=2548'
PV='https://piervillage.com/'
PVE='https://piervillage.com/event/the-pier-village-experience/'
r('nj:long-branch','neighborhood','Pier Village','district','Pier Village on the oceanfront is Long Branch\'s year-round cluster of restaurants, bars, shops, a carousel and two hotels along the boardwalk.',
  'Pier Village (own site)',PV,'high')
r(A,'dog_walk','Long Branch beaches and boardwalk (dog rules)','rule','City rules: dogs are allowed on the city beaches from Seaview to Brighton Avenue from October 1 to April 30, leashed; never on the boardwalk or promenade, and off all beaches May 1 to September 30.',
  'City of Long Branch, Animal Control',AC,'high',schedule='Beach dogs Oct 1 to Apr 30 only')
r(A,'dog_walk','Seven Presidents Oceanfront Park','park','Seven Presidents, a 38-acre Monmouth County beach park, allows leashed dogs throughout the park and beach from November 1 to March 31, and no pets from April 1 to October 31.',
  'Monmouth County Park System, Seven Presidents Oceanfront Park',SP,'high','Pets are never allowed on the playground, skatepark, pavilion, decks, boardwalks or dunes.',schedule='Dogs Nov 1 to Mar 31',ll='osm')
r(A,'dog_walk','Wolf Hill Off-Leash Dog Area','dog_run','The county\'s nearest off-leash dog area is at Wolf Hill Recreation Area in Oceanport: four acres, with a section for all dogs and one for dogs of 35 lb or less.',
  'Monmouth County Park System, Wolf Hill Recreation Area',WH,'high','Closed until 9am on Wednesdays, April to November, for maintenance. Distance not measured.')
supermarket_rows(A)
r(A,'weekday','Cowabunga Coffee Roasters','cafe','Cowabunga Coffee Roasters at Pier Village roasts small-batch arabica and grinds to order.',
  'Pier Village (own site)',PV,'high')
for b in A:
    c=nearest(b,'cafe')
    if c: osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(A,'saturday','Pier Village restaurants and bars','street','Pier Village\'s restaurants include McLoone\'s Pier House and Robinson Ale House; it also runs the free "Pier Village Experience", an afternoon of tastings and offers from its restaurants and shops.',
  'Pier Village (own site), event page',PVE,'high','Date of the Experience not shown on the event page read.')
r(A,'sunday','Seven Presidents Oceanfront Park','park','In the off-season the county beach park is a quiet place for walks, and dogs are welcome on leash from November to March.',
  'Monmouth County Park System, Seven Presidents Oceanfront Park',SP,'high',schedule='Dogs Nov 1 to Mar 31')
