"""Hand-checked lookup targets for the neighborhood-voices pass.

TRULIA: hood_id -> list of (trulia /n/ path, label of the Trulia area). Paths come from `ndpUrl` values already
present in cached Trulia listing pages (raw/trulia), matched by name or by distance to the hood centroid.
Where Trulia has no page of its own for a hood, the page of the enclosing/adjacent named area is used and
flagged through `source_area`. NICHE: hood_id -> list of candidate slugs (first that returns 200 wins).
"""
T = "https://www.trulia.com/n/"
TRULIA = {
 "ny:jamaica": [("ny/new-york/jamaica/85263/", "Jamaica")],
 "ny:jamaica-hills-briarwood": [("ny/new-york/briarwood/85164/", "Briarwood"), ("ny/new-york/jamaica-hills/85265/", "Jamaica Hills")],
 "ny:kew-gardens": [("ny/new-york/kew-gardens/85269/", "Kew Gardens")],
 "ny:forest-hills": [("ny/new-york/forest-hills/85231/", "Forest Hills")],
 "ny:flushing-willets-point": [("ny/new-york/flushing/85227/", "Flushing")],
 "ny:murray-hill-broadway-flushing": [("ny/new-york/flushing/85227/", "Flushing (enclosing area)")],
 "ny:jamaica-estates-holliswood": [("ny/new-york/jamaica-estates/85264/", "Jamaica Estates")],
 "ny:rego-park": [("ny/new-york/rego-park/85338/", "Rego Park")],
 "ny:elmhurst": [("ny/new-york/elmhurst/85216/", "Elmhurst")],
 "ny:middle-village": [("ny/new-york/middle-village/85289/", "Middle Village")],
 "ny:north-corona": [("ny/new-york/north-corona/404666/", "North Corona")],
 "ny:sunnyside": [("ny/new-york/sunnyside/85366/", "Sunnyside")],
 "ny:astoria-central-": [("ny/new-york/astoria/85146/", "Astoria (whole)")],
 "ny:astoria-east-woodside-north-": [("ny/new-york/astoria/85146/", "Astoria (whole)")],
 "ny:old-astoria-hallets-point": [("ny/new-york/astoria/85146/", "Astoria (whole)")],
 "ny:east-new-york-north-": [("ny/new-york/east-new-york/85211/", "East New York")],
 "ny:bedford-stuyvesant-east-": [("ny/new-york/bedford-stuyvesant/85155/", "Bedford-Stuyvesant (whole)")],
 "ny:bedford-stuyvesant-west-": [("ny/new-york/bedford-stuyvesant/85155/", "Bedford-Stuyvesant (whole)")],
 "ny:brighton-beach": [("ny/new-york/brighton-beach/85165/", "Brighton Beach")],
 "ny:east-flatbush-erasmus": [("ny/new-york/east-flatbush/85208/", "East Flatbush (whole)")],
 "ny:east-flatbush-farragut": [("ny/new-york/east-flatbush/85208/", "East Flatbush (whole)")],
 "ny:flatbush": [("ny/new-york/flatbush/85223/", "Flatbush")],
 "ny:prospect-lefferts-gardens-wingate": [("ny/new-york/prospect-lefferts-gardens/85332/", "Prospect Lefferts Gardens"), ("ny/new-york/wingate/175986/", "Wingate")],
 "ny:sheepshead-bay-manhattan-beach-gerritsen-beach": [("ny/new-york/sheepshead-bay/85351/", "Sheepshead Bay"), ("ny/new-york/manhattan-beach/85281/", "Manhattan Beach")],
 "ny:hamilton-heights-sugar-hill": [("ny/new-york/hamilton-heights/85250/", "Hamilton Heights")],
 "ny:harlem-north-": [("ny/new-york/harlem/85252/", "Harlem (whole)")],
 "ny:inwood": [("ny/new-york/inwood/85261/", "Inwood")],
 "ny:upper-east-side-lenox-hill-roosevelt-island": [("ny/new-york/upper-east-side/85381/", "Upper East Side")],
 "ny:washington-heights-north-": [("ny/new-york/washington-heights/85387/", "Washington Heights (whole)")],
 "ny:kingsbridge-heights-van-cortlandt-village": [("ny/new-york/kingsbridge/85270/", "Kingsbridge (adjacent)")],
 "ny:pelham-bay-country-club-city-island": [("ny/new-york/pelham-bay/165408/", "Pelham Bay"), ("ny/new-york/country-club/85199/", "Country Club")],
 "ny:williamsbridge-olinville": [("ny/new-york/williamsbridge/185683/", "Williamsbridge")],
 "ny:mount-vernon": [("ny/mount-vernon/fleetwood/197266/", "Fleetwood, Mount Vernon"), ("ny/mount-vernon/downtown/192510/", "Downtown Mount Vernon")],
 "ny:white-plains": [("ny/white-plains/eastview/917490/", "Eastview, White Plains"), ("ny/white-plains/carhart/917489/", "Carhart, White Plains")],
 "ny:yonkers": [("ny/yonkers/getty-square/85483/", "Getty Square, Yonkers"), ("ny/yonkers/locust-hill/134551/", "Locust Hill, Yonkers")],
 "ny:port-chester": [("ny/port-chester/purdys-grove/177212/", "Purdys Grove, Port Chester")],
 "ct:stamford": [("ct/stamford/downtown/96232/", "Downtown Stamford"), ("ct/stamford/south-end/229154/", "South End, Stamford")],
 "ct:bridgeport": [("ct/bridgeport/downtown/92009/", "Downtown Bridgeport")],
 "ct:norwalk": [("ct/norwalk/spring-hill/186792/", "Spring Hill, Norwalk")],
 "ct:trumbull": [("ct/trumbull/trumbull-center/917217/", "Trumbull Center")],
 "ct:westport": [("ct/westport/staples/917197/", "Staples, Westport")],
 "nj:bayonne": [("nj/bayonne/uptown-bayonne/917500/", "Uptown Bayonne")],
 "nj:hackensack": [("nj/hackensack/hackensack-east/917547/", "Hackensack East")],
 "nj:jersey-city": [("nj/jersey-city/mcginley-square/138233/", "McGinley Square, Jersey City"), ("nj/jersey-city/journal-square/142899/", "Journal Square, Jersey City")],
 "nj:newark": [("nj/newark/central-business-district/84721/", "Central Business District, Newark"), ("nj/newark/university-heights/84736/", "University Heights, Newark")],
 "nj:north-bergen": [("nj/north-bergen-township/racetrack/177502/", "Racetrack, North Bergen"), ("nj/north-bergen-township/bulls-ferry/187376/", "Bulls Ferry, North Bergen")],
 "nj:plainfield": [("nj/plainfield/netherwood/188304/", "Netherwood, Plainfield")],
 "nj:rahway": [("nj/rahway/perth-amboy-junction/137047/", "Perth Amboy Junction, Rahway")],
 "nj:east-orange": [("nj/east-orange/doddtown/180395/", "Doddtown, East Orange")],
}
def _n(s): return f"n/{s}-new-york-city-ny"
NICHE = {
 "ny:jamaica": [_n("jamaica")], "ny:jamaica-hills-briarwood": [_n("briarwood"), _n("jamaica-hills")],
 "ny:kew-gardens": [_n("kew-gardens")], "ny:forest-hills": [_n("forest-hills")], "ny:flushing-willets-point": [_n("flushing")],
 "ny:murray-hill-broadway-flushing": [_n("murray-hill-queens"), _n("east-flushing")],
 "ny:jamaica-estates-holliswood": [_n("jamaica-estates"), _n("holliswood")], "ny:rego-park": [_n("rego-park")],
 "ny:elmhurst": [_n("elmhurst")], "ny:middle-village": [_n("middle-village")], "ny:north-corona": [_n("north-corona"), _n("corona")],
 "ny:sunnyside": [_n("sunnyside")], "ny:astoria-central-": [_n("astoria")], "ny:astoria-east-woodside-north-": [_n("woodside")],
 "ny:old-astoria-hallets-point": [_n("old-astoria")], "ny:east-new-york-north-": [_n("east-new-york")],
 "ny:bedford-stuyvesant-east-": [_n("bedford-stuyvesant")], "ny:bedford-stuyvesant-west-": [_n("bedford-stuyvesant")],
 "ny:brighton-beach": [_n("brighton-beach")], "ny:east-flatbush-erasmus": [_n("east-flatbush")], "ny:east-flatbush-farragut": [_n("east-flatbush")],
 "ny:flatbush": [_n("flatbush")], "ny:flatlands": [_n("flatlands")], "ny:madison": [_n("madison")],
 "ny:prospect-lefferts-gardens-wingate": [_n("prospect-lefferts-gardens")],
 "ny:sheepshead-bay-manhattan-beach-gerritsen-beach": [_n("sheepshead-bay")],
 "ny:hamilton-heights-sugar-hill": [_n("hamilton-heights")], "ny:harlem-north-": [_n("harlem")], "ny:inwood": [_n("inwood")],
 "ny:upper-east-side-lenox-hill-roosevelt-island": [_n("upper-east-side")], "ny:washington-heights-north-": [_n("washington-heights")],
 "ny:kingsbridge-heights-van-cortlandt-village": [_n("kingsbridge-heights"), _n("kingsbridge")],
 "ny:pelham-bay-country-club-city-island": [_n("pelham-bay")], "ny:williamsbridge-olinville": [_n("williamsbridge")],
 "ny:haverstraw": ["haverstraw-rockland-ny"], "ny:hempstead": ["hempstead-nassau-ny"], "ny:lagrange": ["lagrange-dutchess-ny", "la-grange-dutchess-ny"],
 "ny:larchmont": ["larchmont-westchester-ny"], "ny:middletown": ["middletown-orange-ny"], "ny:mineola": ["mineola-nassau-ny"],
 "ny:mount-vernon": ["mount-vernon-westchester-ny"], "ny:new-paltz": ["new-paltz-ulster-ny"], "ny:new-rochelle": ["new-rochelle-westchester-ny"],
 "ny:peekskill": ["peekskill-westchester-ny"], "ny:port-chester": ["port-chester-westchester-ny"], "ny:valley-stream": ["valley-stream-nassau-ny"],
 "ny:white-plains": ["white-plains-westchester-ny"], "ny:yonkers": ["yonkers-westchester-ny"],
 "ct:bridgeport": ["bridgeport-fairfield-ct"], "ct:danbury": ["danbury-fairfield-ct"], "ct:milford-city-balance-": ["milford-new-haven-ct"],
 "ct:norwalk": ["norwalk-fairfield-ct"], "ct:stamford": ["stamford-fairfield-ct"], "ct:trumbull": ["trumbull-fairfield-ct"], "ct:westport": ["westport-fairfield-ct"],
 "nj:atlantic-highlands": ["atlantic-highlands-monmouth-nj"], "nj:bayonne": ["bayonne-hudson-nj"], "nj:belleville": ["belleville-essex-nj"],
 "nj:bloomfield": ["bloomfield-essex-nj"], "nj:bogota": ["bogota-bergen-nj"], "nj:bordentown": ["bordentown-burlington-nj"],
 "nj:carteret": ["carteret-middlesex-nj"], "nj:city-of-orange": ["city-of-orange-essex-nj", "orange-essex-nj"], "nj:clifton": ["clifton-passaic-nj"],
 "nj:dover": ["dover-morris-nj"], "nj:east-orange": ["east-orange-essex-nj"], "nj:edgewater": ["edgewater-bergen-nj"], "nj:englewood": ["englewood-bergen-nj"],
 "nj:hackensack": ["hackensack-bergen-nj"], "nj:harrison": ["harrison-hudson-nj"], "nj:hawthorne": ["hawthorne-passaic-nj"],
 "nj:jersey-city": ["jersey-city-hudson-nj"], "nj:montclair": ["montclair-essex-nj"], "nj:montvale": ["montvale-bergen-nj"],
 "nj:morris-plains": ["morris-plains-morris-nj"], "nj:mount-arlington": ["mount-arlington-morris-nj"], "nj:new-brunswick": ["new-brunswick-middlesex-nj"],
 "nj:newark": ["newark-essex-nj"], "nj:north-bergen": ["north-bergen-hudson-nj"], "nj:parsippany-troy-hills": ["parsippany-troy-hills-morris-nj", "parsippany-morris-nj"],
 "nj:plainfield": ["plainfield-union-nj"], "nj:rahway": ["rahway-union-nj"], "nj:riverdale": ["riverdale-morris-nj"], "nj:teaneck": ["teaneck-bergen-nj"],
 "nj:west-new-york": ["west-new-york-hudson-nj"],
}

# NJ townships use a "-township-" slug on Niche (confirmed for Teaneck through a web search result URL).
for _h, _s in {"nj:teaneck": "teaneck-township-bergen-nj", "nj:montclair": "montclair-township-essex-nj", "nj:bloomfield": "bloomfield-township-essex-nj",
               "nj:belleville": "belleville-township-essex-nj", "nj:city-of-orange": "city-of-orange-township-essex-nj",
               "nj:north-bergen": "north-bergen-township-hudson-nj", "nj:parsippany-troy-hills": "parsippany-troy-hills-township-morris-nj"}.items():
    NICHE[_h].append(_s)

# Connecticut places moved from county to planning-region slugs (canonical link on the old-slug page).
for _h, _s in {"ct:stamford": "stamford-western-connecticut-planning-region-ct", "ct:norwalk": "norwalk-western-connecticut-planning-region-ct",
               "ct:westport": "westport-western-connecticut-planning-region-ct", "ct:danbury": "danbury-western-connecticut-planning-region-ct",
               "ct:bridgeport": "bridgeport-greater-bridgeport-planning-region-ct", "ct:trumbull": "trumbull-greater-bridgeport-planning-region-ct",
               "ct:milford-city-balance-": "milford-south-central-connecticut-planning-region-ct"}.items():
    NICHE[_h].insert(0, _s)
