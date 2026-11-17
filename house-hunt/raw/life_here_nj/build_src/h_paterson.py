from R import *
H='nj:paterson'; A=B(H)
NPS_P='https://www.nps.gov/pagr/planyourvisit/pets.htm'; NPS_B='https://www.nps.gov/pagr/planyourvisit/basicinfo.htm'
PT1='https://patersontimes.com/2017/02/21/paterson-approves-193000-contract-for-dog-park-construction/print'
PT2='https://patersontimes.com/?p=29084'
GM='https://seepassaiccounty.org/explore/parks/garret-mountain-reservation/'
JK='https://jackals.com/articles/the-new-new-jersey-jackals-new-ownership-is-placing-the-community-first'
NJM_ME='https://njmonthly.com/articles/eat-drink/a-guide-to-patersons-middle-eastern-restaurants/'
NJM_PE='https://njmonthly.com/articles/eat-drink/tasty-peruvian-food-to-try-in-paterson/'
SILK='https://www.maxspann.com/news/detail/silk-cafe-opens-in-paterson-bringing-new-flavor-and-fresh-energy-to-the-gre'
# neighborhood
r(H,'neighborhood','Paterson Great Falls National Historical Park','park','The Great Falls of the Passaic are a national historical park inside the city; the grounds are open every day, with no visitor center or indoor facilities.',
  'National Park Service, Paterson Great Falls: Basic Information',NPS_B,'high','Some facilities and paths close in winter, per the same page. Main lot at 72 McBride Avenue Extension closes after dark.')
r(H,'neighborhood','Hinchliffe Stadium','stadium','Hinchliffe Stadium, by the falls, is a 7,800-seat National Historic Landmark built in 1932 and one of four remaining Negro League ballparks.',
  'New Jersey Jackals (team site), March 2026 announcement',JK,'high','Restored in 2023; home of the Jackals and the Charles J. Muth Museum.')
# dog walk: DeCando dog park for all
r(A,'dog_walk','John DeCando Riverview Dog Park','dog_park','The city built an off-leash dog park on River Street between Lawrence and Montgomery Streets, named for its longtime animal control officer John DeCando.',
  'Paterson Times (local news), February 2017 contract report',PT1,'medium','Construction contract approved in February 2017; the name was approved in October 2017 (Paterson Times, https://patersontimes.com/?p=29084). No city page with rules or hours was found; passaiccountynj.org refused us (403).',ll='osm')
falls=[b for b in A if any(t[1] in ('Mary Ellen Kramer Park','Overlook Park') for t in N[b]['park'])]
r(falls,'dog_walk','Paterson Great Falls National Historical Park','park','Dogs are welcome at the Great Falls on a hard, non-retractable leash no longer than six feet, and may not be left unattended.',
  'National Park Service, Paterson Great Falls: Pets',NPS_P,'high','Mary Ellen Kramer Park and Overlook Park, the falls-side parks, are mapped within about a mile of this building in OpenStreetMap.')
gm=[b for b in A if any(t[1]=='Garret Mountain Reservation' for t in N[b]['park'])]
r(gm,'dog_walk','Garret Mountain Reservation','park','Garret Mountain is a 300-plus-acre Olmsted Brothers county park on the ridge above the city, with trails, Barbour Pond and city views; leashed dogs are allowed.',
  'See Passaic County (county tourism), Garret Mountain Reservation',GM,'high','The Lambert Castle to Lambert Tower trail is closed indefinitely, per the same page.',ll='osm')
# weekday
supermarket_rows(A)
r(A,'weekday','Silk Café','cafe','Silk Café opened in August 2025 in the old Libby\'s Lunch building by the Great Falls, serving all-day breakfast, bagels, specialty coffee and bakery items.',
  'Max Spann Real Estate & Auction (auctioneer of the site), August 2025 report',SILK,'medium','98 McBride Ave. Hours given at opening: daily 7am to 11pm; not confirmed on a page of the café\'s own.',schedule='Daily 7am to 11pm (at opening, 2025)')
# saturday
r(A,'saturday','New Jersey Jackals at Hinchliffe Stadium','event','The Jackals play pro baseball at Hinchliffe; from 2026 every seat is $10, and on "Silk City Fridays" single-game tickets are $5.',
  'New Jersey Jackals (team site), March 2026 announcement',JK,'high','The 2026 season opened on Friday, May 8 (The Beacon, William Paterson University: https://wpubeacon.com/15845/jackals/new-jersey-jackals-ignite-2026-season-under-the-lights-at-historic-hinchliffe-stadium/). A Friday event filed under saturday.',schedule='Home games May to September; Silk City Fridays $5')
r(A,'saturday','Palestine Way (Main Street, South Paterson)','strip','A five-block stretch of Main Street in South Paterson is lined with restaurants, bakeries and cafés, including Baklava Home and the late-opening Mokafe coffee house.',
  'New Jersey Monthly, April 2026',NJM_ME,'medium','Al Basha, named by the same article, has its dining room on Crooks Avenue and take-out on Main Street. Places not checked on their own pages.')
r(A,'saturday','La Tia Delia (Market Street)','restaurant','Market Street\'s run of Peruvian restaurants includes La Tia Delia at 28 Market Street, which also serves Peruvian breakfasts.',
  'New Jersey Monthly, March 2023',NJM_PE,'medium','2023 article; current operation not confirmed on its own page.')
# sunday
r(A,'sunday','Paterson Great Falls National Historical Park','park','For a Sunday walk, the falls grounds are open every day; the best time to visit is between sunrise and sunset.',
  'National Park Service, Paterson Great Falls: Basic Information',NPS_B,'high','Parking at 72 McBride Avenue Extension reopens each morning between 7:45 and 8:45am.')
