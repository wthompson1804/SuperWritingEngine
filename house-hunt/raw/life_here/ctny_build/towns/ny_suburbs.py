G1='b_b6f6e7d714'; G2='b_8f01469adc'; MT='b_3d86019ee6'; MB='b_f0a7059dca'; OS='b_8909728008'; IS='b_e7ab1481ec'
OSMN='OpenStreetMap (project extract, 2026-11-14)'
HT='https://pickocny.com/news/orange-county-n-y-businesses-flourish-as-heritage-trail-expands'
GFM='https://www.villageofgoshen-ny.gov/farmers-market/'
GHT='https://goshenhistorictrack.com/events-2/'
CB='https://www.clemsonbrewing.com/'
SSF='https://dec.ny.gov/places/stewart-state-forest'
OCA='https://parks.ny.gov/parks/oldcrotonaqueduct/details.aspx'
OFM='https://marketspread.com/market/20863/ossining-down-to-earth-farmers-market/'
FVC='https://www.firstvillagecoffee.com/'
BC='https://www.boultoncenter.org/'
def osm(bids,moment,name,kind,fact,ref,notes='OSM only; not checked on its own page.'):
    return dict(bids=bids,moment=moment,place_name=name,place_kind=kind,fact=fact,source_name=OSMN,source_url='https://www.openstreetmap.org/'+ref,confidence='medium',notes=notes,osm=ref if ref.startswith('node') else None)
ROWS=[
 # Goshen
 dict(bids=[''],hood='ny:goshen',moment='neighborhood',place_name='Goshen Historic Track',place_kind='history',fact='Goshen\'s harness-racing track, established in 1838, is a National Historic Landmark next to the Harness Racing Museum & Hall of Fame.',source_name='Goshen Historic Track (own site)',source_url=GHT,confidence='high'),
 dict(bids=[''],hood='ny:goshen',moment='neighborhood',place_name='Heritage Trail',place_kind='trail',fact='The county\'s Heritage Trail, built on the old Erie Railroad main line, runs about 18 miles from Harriman through Goshen to Middletown.',source_name='Orange County Tourism (pickocny.com), May 2021',source_url=HT,confidence='medium',notes='Length as of 2021, with a further extension then planned.'),
 dict(bids=[G1,G2],moment='dog_walk',place_name='Heritage Trail (St. James Place access)',place_kind='trail',fact='The Heritage Trail has an access point at St. James Place in the village, and runs through wildlife sanctuary and past streams.',source_name='Orange County Tourism (pickocny.com), May 2021',source_url=HT,confidence='medium',notes='Leash rule not confirmed on a county page (directories say leashed dogs welcome).'),
 dict(bids=[G1,G2],moment='weekday',place_name='Trailside Treats Creamery',place_kind='other',fact='Trailside Treats Creamery, an ice cream stop beside the Heritage Trail in Goshen, says most of its customers come off the trail.',source_name='Orange County Tourism (pickocny.com), May 2021',source_url=HT,confidence='medium',notes='Opened 2012 per the article; current hours not checked.',osm=None),
 osm([G1,G2],'weekday','Cafe Yen','cafe','Mapped cafes in the village include Cafe Yen, Diplomat Cafe and Not Just Bagels.','way/1254693813'),
 dict(bids=[G1,G2],moment='weekday',place_name='Goshen Farmers\' Market',place_kind='market',fact='The Goshen Chamber of Commerce runs a farmers market on the Orange County Government Center grounds on Main Street.',schedule='Fridays, May to October, 9am to 3pm',source_name='Village of Goshen: Farmers\' Market',source_url=GFM,confidence='high',notes='255 Main Street.'),
 osm([G1,G2],'weekday','ShopRite','supermarket','The nearest mapped supermarket is ShopRite, a drive from the village.','way/326603772','OSM only; hours not checked.'),
 osm([G1,G2],'saturday','Kelly Jeans','bar','The nearest mapped bar in the village is Kelly Jeans.','way/401280830'),
 # Middletown
 dict(bids=[MT],moment='dog_walk',place_name='Heritage Trail (Middletown end)',place_kind='trail',fact='The county Heritage Trail has been extended into the City of Middletown, linking it by trail with Goshen.',source_name='Orange County Tourism (pickocny.com), May 2021',source_url=HT,confidence='medium',notes='2021 article: extension to Palmer Avenue built, extension to East Main Street then expected. Nearest mapped dog park: Maple Hill Dog Park (OSM, https://www.openstreetmap.org/way/670315603).'),
 osm([MT],'weekday','Ruben Jrs Supermarket & Deli','supermarket','The nearest mapped grocery is Ruben Jrs Supermarket & Deli.','way/679612339','OSM only; hours not checked.'),
 osm([MT],'weekday',"Jacobson's Bakery",'bakery',"Mapped bakeries nearby include Jacobson's Bakery and San Miguel Panaderia.",'way/679612060'),
 dict(bids=[MT],moment='saturday',place_name='Clemson Bros. Brewery',place_kind='bar',fact='Clemson Bros. Brewery in Middletown pours its own beers with a full kitchen, a tap room and a 7,500 sq ft beer garden in warm months.',source_name='Clemson Bros. Brewery (own site)',source_url=CB,confidence='high',notes='Hours and address not read from the page.'),
 # Maybrook
 dict(bids=[MB],moment='dog_walk',place_name='Stewart State Forest',place_kind='park',fact='Stewart State Forest is 6,700 acres of wetlands, fields and forest with more than 22 miles of trails and 18 miles of gravel roads.',source_name='NYS DEC: Stewart State Forest',source_url=SSF,confidence='high',notes='Closed to non-hunters during the regular big-game hunting season (late fall). Dog rules not stated on the page.'),
 dict(bids=[MB],moment='sunday',place_name='Great Swamp boardwalk (Stewart State Forest)',place_kind='trail',fact='A newer boardwalk across the Great Swamp in Stewart State Forest makes loop hikes of under three miles possible.',source_name='NYS DEC: Stewart State Forest',source_url=SSF,confidence='high',notes='Reached via the Schofield Lane Trail.'),
 osm([MB],'weekday','ShopRite','supermarket','The nearest mapped supermarket is ShopRite, a drive away.','node/2669556405','OSM only; hours not checked. No cafe or bar is mapped near the building.'),
 # Ossining
 dict(bids=[''],hood='ny:ossining',moment='neighborhood',place_name='Double Arch and Sing Sing Kill',place_kind='history',fact='In Ossining the Croton Aqueduct crosses the Sing Sing Kill gorge on the Double Arch, a bridge within a bridge, with an accessible greenway path underneath.',source_name='NYS Parks: Old Croton Aqueduct State Historic Park',source_url=OCA,confidence='high',notes='Across from the Ossining Community Center, 95 Broadway.'),
 dict(bids=[OS],moment='dog_walk',place_name='Old Croton Aqueduct Trail',place_kind='trail',fact='The Old Croton Aqueduct trail, a 26-mile linear state park from the Bronx line to the Croton Dam, passes close to the building; free, with access from many cross streets.',source_name='NYS Parks: Old Croton Aqueduct State Historic Park',source_url=OCA,confidence='high',notes='Dog rules not on the page. Nearest mapped dog park: Ossining Dog Park (OSM, https://www.openstreetmap.org/way/58422667).'),
 dict(bids=[OS],moment='weekday',place_name='First Village Coffee',place_kind='cafe',fact='First Village Coffee is a specialty coffee and espresso bar with a bakery and local art in downtown Ossining.',source_name='First Village Coffee (own site)',source_url=FVC,confidence='high',notes='Online orders by 3pm for next-day pickup.',osm='node/5962390839'),
 osm([OS],'weekday','Las Americas','supermarket','The nearest mapped supermarket is Las Americas.','node/12673139946','OSM only; hours not checked.'),
 dict(bids=[OS],moment='saturday',place_name='Down to Earth Ossining Farmers Market',place_kind='market',fact='Ossining\'s farmers market sets up at 11 Spring Street, by Spring and Main, with 2026 and 2027 seasons listed.',source_name='Down to Earth Ossining Farmers Market (market listing on MarketSpread)',source_url=OFM,confidence='medium',notes='The day and hours load by script and were not read; search results say Saturdays, not confirmed.'),
 osm([OS],'saturday','Here Coffee + Beer','bar','Here Coffee + Beer is a mapped cafe-bar downtown.','node/13824507891'),
 # Islip / Bay Shore
 dict(bids=[IS],moment='saturday',place_name='YMCA Boulton Center for the Performing Arts',place_kind='other',fact='The Boulton Center in Bay Shore is an intimate venue with tribute concerts, plays and Sunday afternoon films.',schedule='Most Fri and Sat 8pm, Sun 2:30pm (Nov to Dec 2026 listings)',source_name='YMCA Boulton Center (own site)',source_url=BC,confidence='high',notes='Upcoming: Story Songs of the Seventies Nov 21; Fleetwood Macked Dec 12, 2026.'),
 osm([IS],'saturday',"Destination Unknown Beer Company",'bar',"Main Street bars mapped near the building include Destination Unknown Beer Company and Kitty Mulligan's.",'node/4931039622','OSM only; the brewery\'s site was unreachable.'),
 osm([IS],'weekday','Bay Shore Bean','cafe','The nearest mapped independent cafe is Bay Shore Bean.','node/6478852909'),
 osm([IS],'weekday','Stop & Shop','supermarket','The nearest mapped supermarket is Stop & Shop.','node/9324833787','OSM only; hours not checked.'),
]
ROWS.append(dict(bids=[''],hood='ny:middletown',moment='neighborhood',place_name='Heritage Trail',place_kind='trail',fact='Middletown is the western end of the county\'s Heritage Trail, the rail trail on the old Erie main line that runs east through Goshen to Harriman.',source_name='Orange County Tourism (pickocny.com), May 2021',source_url=HT,confidence='medium'))
