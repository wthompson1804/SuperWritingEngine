"""Hand selection of quotes from the cached official pages -> picks_web.json.
Each entry gives the first and last words of the sentence; the exact text (curly quotes, dashes and
all) is copied from the cached page text so nothing is retyped. Run from the repo root."""
import hashlib, json, re, sys
D = "raw/neighborhood_descriptions_round2/"
CT = "CTvisit (Connecticut Office of Tourism)"
WC = "Visit Westchester (Westchester County Tourism & Film)"
EX = "Essex County Parks (Essex County, New Jersey)"
HU = "Visit Hudson (Hudson County Office of Cultural and Heritage Affairs/Tourism Development)"
NY = "NYC Tourism + Conventions"
ct = "https://ctvisit.com/listings/"
wc = "https://www.visitwestchesterny.com/"
hu = "https://www.visithudson.org/"
ny = "https://www.nyctourism.com/new-york/"
ex = "https://www.essexcountyparks.org/parks/"
P = [  # hood, url, starts with, ends with, source, about_area, scope, character, topic
 ("ct:shelton", ct+"city-shelton", "From Indian Wells State Park", "for everyone.", CT, "Shelton", "exact", 2, "parks"),
 ("ct:stratford", ct+"town-stratford", "Located along Long Island Sound", "boat launches.", CT, "Stratford", "exact", 3, "waterfront"),
 ("ct:stamford", ct+"city-stamford", "Whether you're strolling", "dull moment.", CT, "Stamford", "exact", 3, "food and nightlife"),
 ("ct:stamford", ct+"city-stamford", "Mill River Park, often referred", "landscaped space.", CT, "Stamford", "exact", 3, "parks"),
 ("ct:danbury", ct+"city-danbury", "Downtown, visitors will find", "vibrant scene.", CT, "Danbury", "exact", 3, "main street"),
 ("ct:danbury", ct+"city-danbury", "For a break from city life", "and swimming.", CT, "Danbury", "exact", 3, "parks"),
 ("ct:norwalk", ct+"city-norwalk", "South Norwalk, known as SoNo", "vibrant nightlife.", CT, "Norwalk", "exact", 3, "food and nightlife"),
 ("ct:norwalk", ct+"city-norwalk", "The Norwalk shoreline offers", "culture and class.", CT, "Norwalk", "exact", 3, "waterfront"),
 ("ct:westport", ct+"town-westport", "Stroll along walkable streets", "for a bite.", CT, "Westport", "exact", 3, "main street"),
 ("ct:westport", ct+"town-westport", "Spend a day unwinding", "Country Playhouse.", CT, "Westport", "exact", 3, "landmark"),
 ("ct:brookfield", ct+"town-brookfield", "The town is bordered by", "to the east.", CT, "Brookfield", "exact", 3, "waterfront"),
 ("ct:trumbull", ct+"town-trumbull", "With over 1,400 acres", "bike ride.", CT, "Trumbull", "exact", 3, "parks"),
 ("ct:trumbull", ct+"town-trumbull", "Just a quick 5-mile drive", "seaside dining.", CT, "Trumbull", "exact", 2, "waterfront"),
 ("ct:seymour", ct+"town-seymour", "The quaint, walkable historic downtown", "riverfront vistas.", CT, "Seymour", "exact", 3, "main street"),
 ("ct:seymour", ct+"town-seymour", "This charming town, with remnants", "the hillsides.", CT, "Seymour", "exact", 3, "housing feel"),
 ("ct:oxford", ct+"town-oxford", "Oxford also features two breweries", "to explore.", CT, "Oxford", "exact", 3, "food and nightlife"),
 ("ct:oxford", ct+"town-oxford", "This rural town is rich", "England character.", CT, "Oxford", "exact", 2, "housing feel"),
 ("ct:beacon-falls", ct+"town-beacon-falls", "It is a great community for", "several locations.", CT, "Beacon Falls", "exact", 3, "waterfront"),
 ("ct:milford-city-balance-", ct+"city-milford", "The meticulously maintained town green", "back centuries.", CT, "Milford", "exact", 3, "main street"),
 ("ct:milford-city-balance-", ct+"city-milford", "Don’t forget to hit one", "downtown restaurants.", CT, "Milford", "exact", 2, "food and nightlife"),
 ("ct:fairfield", ct+"town-fairfield", "Its historic downtown offers", "at the theater.", CT, "Fairfield", "exact", 3, "main street"),
 ("ct:hamden", ct+"town-hamden", "Sleeping Giant State Park, with", "New Haven area.", CT, "Hamden", "exact", 3, "parks"),
 ("ct:hamden", ct+"town-hamden", "Hamden also offers a variety", "every interest.", CT, "Hamden", "exact", 2, "main street"),
 ("ct:west-haven", ct+"city-west-haven", "Once the site of Connecticut", "at its heart.", CT, "West Haven", "exact", 3, "history"),
 ("ct:west-haven", ct+"city-west-haven", "With the longest publicly accessible", "coastal resiliency.", CT, "West Haven", "exact", 3, "waterfront"),
 ("ny:yonkers", wc+"about-westchester/communities-local-flair/southern-westchester/yonkers/", "During the summer months", "the evening.", WC, "Yonkers", "exact", 3, "event"),
 ("ny:white-plains", wc+"discover/communities/mid-county/", "It boasts a vibrant nightlife", "and budgets.", WC, "Mid-county Westchester, centred on White Plains", "enclosing", 3, "food and nightlife"),
 ("ny:white-plains", wc+"about-westchester/communities-local-flair/mid-county/white-plains/", "Every year, from May to September", "in White Plains.", WC, "White Plains", "exact", 3, "event"),
 ("ny:port-chester", wc+"about-westchester/communities-local-flair/sound-shore/port-chester/", "Port Chester has six parks", "and sports.", WC, "Port Chester", "exact", 2, "parks"),
 ("nj:city-of-orange", ex+"monte-irvin-orange-park", "The park hosts a variety of free concerts", "Park System.", EX, "Monte Irvin Orange Park", "part", 3, "parks"),
 ("nj:city-of-orange", ex+"monte-irvin-orange-park", "Monte Irvin Orange Park serves", "a playground.", EX, "Monte Irvin Orange Park", "part", 2, "parks"),
 ("nj:bloomfield", ex+"brookdale-park", "Brookdale Park offers the public", "picturesque vistas.", EX, "Brookdale Park (in Bloomfield and Montclair)", "part", 2, "parks"),
 ("nj:belleville", ex+"branch-brook-park", "The New Jersey Symphony Orchestra", "Branch Brook Park.", EX, "Branch Brook Park (in Newark and Belleville)", "part", 3, "event"),
 ("nj:hackensack", "https://www.hackensack.org/news/main-street-revitalization-continues-with-new-residential-developments-restaurants-and-shops-now-open/", "The Hackensack Performing Arts Center showcases", "community events.", "City of Hackensack", "Hackensack", "exact", 3, "landmark"),
 ("nj:bayonne", hu+"neighborhoods/bayonne/", "Richard A. Rutkowski Park is filled", "water vistas.", HU, "Bayonne", "exact", 3, "waterfront"),
 ("nj:harrison", hu+"neighborhoods/harrison/", "And, for nature enthusiasts", "Harrison-Kearny border.", HU, "West Hudson Park, on the Harrison-Kearny border", "part", 3, "parks"),
 ("nj:weehawken", hu+"neighborhoods/weehawken/", "From the waterfront walkway to the clifftop", "and serenity.", HU, "Weehawken", "exact", 3, "waterfront"),
 ("nj:jersey-city", hu+"things-to-do/attractions/", "At the heart of it all is Liberty State Park", "Ellis Island.", HU, "Liberty State Park", "part", 3, "waterfront"),
 ("nj:jersey-city-newport", hu+"things-to-do/attractions/hudson-river-waterfront-walkway/", "From biking and jogging", "Big Apple backdrop.", HU, "Hudson River Waterfront Walkway, which runs through Newport", "enclosing", 3, "waterfront"),
 ("ny:flushing-willets-point", ny+"queens/flushing/", "The neighborhood is quite lush", "Corona Park.", NY, "Flushing", "exact", 3, "parks"),
 ("ny:flushing-willets-point", ny+"queens/flushing/", "That park itself holds", "held here.", NY, "Flushing Meadows Corona Park", "part", 3, "landmark"),
 ("ny:jamaica", ny+"queens/jamaica/", "The neighborhood also features the 200-year-old", "the Constitution.", NY, "Jamaica", "exact", 3, "landmark"),
 ("ny:north-corona", ny+"queens/corona/", "Walk off your feast", "for the family.", NY, "Corona", "enclosing", 3, "parks"),
 ("ny:astoria-central-", ny+"queens/astoria/", "Savor Astoria’s international flavors", "trendy shops.", NY, "Astoria", "enclosing", 3, "food and nightlife"),
 ("ny:astoria-east-woodside-north-", ny+"queens/astoria/", "Savor Astoria’s international flavors", "trendy shops.", NY, "Astoria", "enclosing", 3, "food and nightlife"),
 ("ny:sunnyside", ny+"queens/sunnyside/", "Find an array of international cuisines", "in Sunnyside.", NY, "Sunnyside", "exact", 3, "food and nightlife"),
 ("ny:east-harlem-south-", ny+"manhattan/east-harlem/", "Numerous parks and works", "the allure.", NY, "East Harlem", "enclosing", 2, "parks"),
 ("ny:upper-west-side-manhattan-valley", ny+"manhattan/upper-west-side/", "Bordered by Central Park and Riverside Park", "in general.", NY, "Upper West Side", "exact", 3, "housing feel"),
 ("ny:upper-west-side-manhattan-valley", ny+"manhattan/upper-west-side/", "Lincoln Center performances", "its draws.", NY, "Upper West Side", "exact", 3, "landmark"),
 ("ny:bedford-stuyvesant-east-", ny+"brooklyn/bedford-stuyvesant/", "Dive into Bed-Stuy nightlife", "turtle races.", NY, "Bedford-Stuyvesant", "enclosing", 3, "food and nightlife"),
 ("ny:bedford-stuyvesant-west-", ny+"brooklyn/bedford-stuyvesant/", "Dive into Bed-Stuy nightlife", "turtle races.", NY, "Bedford-Stuyvesant", "enclosing", 3, "food and nightlife"),
]
out, bad = [], []
for hid, url, a, b, src, about, scope, ch, topic in P:
    p = D + "web_text/" + hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt"
    t = json.load(open(p))["text"]
    i = t.find(a)
    j = t.find(b, i) if i >= 0 else -1
    if i < 0 or j < 0 or "¶" in t[i:j]:
        bad.append((hid, a))
        continue
    out.append({"hood_id": hid, "web_url": url, "quote": t[i:j + len(b)], "source_name": src,
                "about_area": about, "scope": scope, "character": ch, "topic": topic})
if bad:
    sys.exit(f"not found: {bad}")
json.dump(out, open(D + "picks_web.json", "w"), indent=1, ensure_ascii=False)
print(len(out), "web picks; longest", max(len(o["quote"].split()) for o in out), "words")
