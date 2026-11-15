"""Evidence batch 2: confirm_batch_2.csv rows (gate facts). Quotes are verbatim from the page named in source_url.
Dog weight gate is >= 25 lb (CLAUDE.md, lowered from 40). 'derived' floors come from unit numbering and stay unconfirmed."""
import sys
sys.path.insert(0, "scripts")
from ev_batch2_add import add
AL = "https://www.apartmentlist.com/nj/"
GS = "https://www.greystar.com/"
C = "confirmed"; U = "unconfirmed"
AMEN = "Apartment List amenity list: 'Elevator'"
def b(k, elev, floor, dogs, wt):
    return [(k, "elevator") + elev, (k, "floor") + floor, (k, "dogs_allowed") + dogs, (k, "dog_weight_limit") + wt]
def alsrc(slug): return AL + slug
R = []
k = "2 kinderkamack rd|07601"; gc = "https://www.gardencommunities.com/Properties/NJ/Bergen/The-Jefferson-Hackensack.aspx"; pdf = "https://www.gardencommunities.com/CMSPages/GetFile.aspx?guid=92b3fa11-3aac-4f96-8b37-6d2cec922a51"
R += b(k, ("yes; floor count not stated", "Community amenities list: 'Elevators'", gc, C), ("unknown", "price is per floor plan (A-01 One Bedroom); no unit number or floor on the page", gc, U),
       ("yes", "Community amenities: 'Dog Run', 'Dog Wash', 'Pet-Friendly'; fees sheet: 'Pet Rent: $50/month for 1 pet'", gc, C), ("100 lb combined (2 pets)", "2 pets with a combined weight of 100 pounds are allowed Breed restrictions apply", pdf, C))
k = "300 prospect ave|07601"; s = alsrc("hackensack/prospect-place--1")
R += b(k, ("yes; floor count not stated", AMEN + " (building site prospectplaceapts.com returned 403)", s, C), ("02-229: 2 (derived from unit number; '02' prefix = 'Mid' building); 02-122 is gone", "floor plan name 'Mid 1BR 1BA Den', unit '02-229'", s, U),
       ("yes", "allowed_pets: cats, dogs; amenity 'Dog park'", s, C), ("under 40 lb", "Weight: Under 40 lbs (Apartments) Breeds: Restrictions.", s, C))
k = "345 prospect ave|07601"; s = alsrc("hackensack/grand-imperial-apartments")
R += b(k, ("yes; 7 floors; 2 elevators", "this seven story mid-rise offers renovated Studio, One and Two Bedroom Apartments. ... new windows, two elevators, balconies (in selected apartments)", s, C), ("4K: 4; 3M: 3 (derived from unit number)", "units '4K', '3M'", s, U),
       ("yes", "allowed_pets: cats, dogs; dogs rent $50", s, C), ("limit exists, pounds not published", "Breed and Weight Restrictions", s, U))
k = "390 prospect ave|07601"; s = alsrc("hackensack/imperial-apartments")
R += b(k, ("yes; 6 floors", "this six story mid-rise offers renovated Studio, One and Two Bedroom Apartments. ... new windows, elevator, intercom service", s, C), ("5F: 5 (derived from unit number)", "unit '5F'", s, U),
       ("yes", "allowed_pets: cats, dogs; dogs rent $50, limit 2", s, C), ("limit exists, pounds not published", "Breed and Weight Restrictions", s, U))
k = "1100 s 5th st|07029"; s = alsrc("harrison/the-wyldes")
R += b(k, ("yes; floor count not stated", AMEN, s, C), ("439: 4; 477: 4 (derived from unit number)", "units '439', '477'", s, U), ("yes", "allowed_pets: dogs, cats; limit 2", s, C), ("not stated", "no weight text on Apartment List or thewyldes.com/amenities ('Pet Spa')", s, U))
k = "1200 s fifth st|07029"; s = alsrc("harrison/cobalt-lofts--2")
R += b(k, ("yes; floor count not stated", AMEN + " (cobaltlofts.com robots.txt disallows Claude agents)", s, C), ("2117: 2; 2113: 2 (derived: first digit looks like the floor, units listed run 1xxx-5xxx)", "units '2117', '2113'", s, U), ("yes", "allowed_pets: dogs, cats; 'Breed Restrictions Apply'", s, C), ("not stated", "Breed Restrictions Apply", s, U))
k = "1200 frank e rodgers blvd s|07029"; s = alsrc("harrison/steel-works")
R += b(k, ("yes; floor count not stated", AMEN + " (steelworksapts.com robots.txt disallows Claude agents)", s, C), ("1142: 1?; 1119: 1? (derived: first digit looks like the floor, units listed run 1xxx-5xxx; POSSIBLE GROUND FLOOR, ask)", "units '1142', '1119'", s, U), ("yes", "allowed_pets: dogs, cats; 'Restricted breeds list'", s, C), ("not stated", "Restricted breeds list", s, U))
k = "600 frank e rodgers blvd s|07029"; s = "https://www.harrisonyards.com/amenities.aspx"
R += b(k, ("yes; floor count not stated", "Community Features: '... Onsite Market Elevator On-site maintenance'", s, C), ("H2-316: 3 (derived from unit number)", "unit 'H2-316'", alsrc("harrison/harrison-yards"), U),
       ("yes", "Pet Policy: Dogs and Cats allowed, $500 one-time fee per pet, $65 pet rent monthly per pet, no weight restrictions but breed restrictions apply.", s, C), ("no limit", "no weight restrictions but breed restrictions apply", s, C))
k = "204 wagaraw rd|07506"; s = alsrc("hawthorne/hedges-at-hawthorne")
R += b(k, ("yes; floor count not stated", AMEN + " (hedgesathawthorne.com returned 403)", s, C), ("409: 4 (derived from unit number)", "unit '409'", s, U), ("yes", "allowed_pets: cats, dogs; amenities 'Dog park', 'Dog grooming area'", s, C),
       ("not stated (breed list only)", "With the exception for ESA or Service Animals, the following breeds will not be approved to accompany you to your new home: Doberman Pinscher, American Bulldog, Pitbull, Rottweiler, Chow, German Shepherd, Siberian Husky ... Great Dane, Mastiff", s, U))
k = "110 hoboken ave|07310"; s = alsrc("jersey-city/one-ten-at-the-enclave")
R += b(k, ("yes; floor count not stated", AMEN + " (onetenjc.com returned 403)", s, C), ("430: 4 (derived from unit number)", "unit '430'", s, U), ("yes", "allowed_pets: cats, dogs; rent '$50 Per Pet'; amenity 'Dog park'", s, C), ("not stated", "Breed Restrictions", s, U))
k = "20 beacon way|07304"; s = "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/availability/"
R += b(k, ("not stated in words; SightMap floor list for the Tower runs to floor 14 and unit P-1203 is on 12", "floor labels: 1-12, 14, A, B, G", s, U), ("O-0404: 4; P-1203: 12", "SightMap unit records: floor '4', floor '12'", s, C),
       ("yes", "Enjoy state-of-the-art fitness centers, pet-friendly dog parks, a Bocce court, an indoor pool", "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/", C), ("not stated", "no weight or breed text on the building page", "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/", U))
k = "270 johnston ave|07304"; s = alsrc("jersey-city/atlas--1")
R += b(k, ("yes; floor count not stated (units listed up to 17xx)", AMEN, s, C), ("0308: 3 (derived from unit number)", "unit '0308'", s, U), ("yes", "allowed_pets: cats, dogs", s, C), ("not stated", "no weight text on Apartment List or atlasjc.com", s, U))
k = "89 monitor st|07304"; s = alsrc("jersey-city/the-hazel-jersey-city")
R += b(k, ("yes; floor count not stated", AMEN, s, C), ("221: 2; 318: 3 (derived from unit number)", "units '221', '318'", s, U), ("yes", "allowed_pets: cats, dogs; amenity 'Dog park'; thehazeljc.com amenities: 'Dog Run'", s, C), ("not stated", "no weight text on Apartment List or thehazeljc.com", s, U))
k = "155 washington st|07302"; s = alsrc("jersey-city/portside-towers")
R += b(k, ("yes; floor count not stated", AMEN + " (equityapartments.com returned 403)", s, C), ("311: 3 (derived from unit number)", "unit '311'", s, U), ("yes", "allowed_pets: dogs, cats; dogs rent 80.00, fee 450.00; limit 3", s, C), ("not stated", "restrictions field is empty ('null')", s, U))
k = "2935 john f kennedy blvd|07306"; s = "https://www.threejournalsquare.com/features.aspx"
R += b(k, ("yes; floor count not stated (unit 1005 implies 10+)", "Community amenities: '... Rentable Party Room Elevator Parking ...'", s, C), ("1005: 10 (derived from unit number)", "unit '1005'", alsrc("jersey-city/3-journal-square--2"), U),
       ("yes", "We love your dogs! No Breed or Weight Restrictions! We welcome 2 pets per apartment home.", s, C), ("no limit", "We love your dogs! No Breed or Weight Restrictions!", s, C))
k = "49 fisk st|07305"; s = alsrc("jersey-city/birch-house")
R += b(k, ("yes; floor count not stated", AMEN, s, C), ("415: 4; 313: 3 (derived from unit number)", "units '415', '313'", s, U), ("yes", "Apartment List amenities 'Dogs allowed', 'Dog park'; birchhousejc.com/amenities: 'Private Outdoor Dog Run' (the Apartment List pet-policy block itself is empty)", s, C), ("not stated", "no pet policy text on Apartment List or birchhousejc.com", s, U))
k = "65 maple st|07304"; s = alsrc("jersey-city/solaris-lofts--1")
R += b(k, ("yes; floor count not stated", AMEN, s, C), ("0511: 5 (derived from unit number)", "unit '0511'", s, U), ("yes", "Pet limits ... include a maximum of 1 cat and a maximum of 2 dogs per apartment.", "https://www.solarislofts.com/faq/", C), ("not stated", "Additional rules, fees, and any restricted breeds are outlined in the community's pet policy resources.", "https://www.solarislofts.com/faq/", U))
k = "189 phillip st|07305"; s = alsrc("jersey-city/aviva")
R += b(k, ("yes; floor count not stated", AMEN, s, C), ("E0424: 4; E0521: 5 (derived from unit number)", "units 'E0424', 'E0521'", s, U), ("yes", "allowed_pets: cats, dogs (Apartment List); avivajc.com/faq: 'We welcome up to two pets per apartment home and even offer a dedicated pet salon'", s, C),
       ("not stated", "Breed restrictions apply, and all pets must complete a third-party pet screening process.", "https://avivajc.com/faq", U))
k = "1075 w side ave|07306"; s = alsrc("jersey-city/west-side-square")
R += b(k, ("not stated on Apartment List or westsidesquare.com; unit numbers run to 8xx", "amenities listed: Dog park, Pool, Garage (no 'Elevator' entry)", s, U), ("710: 7; 810: 8 (derived from unit number)", "units '710', '810'", s, U),
       ("yes", "We welcome 2 pets per apartment home. There is a $500 pet deposit (non-refundable) per pet. There is no weight restriction.", s, C), ("no limit", "There is no weight restriction.", s, C))
k = "200 boyden ave|07040"; s = "https://www.avaloncommunities.com/new-jersey/maplewood-apartments/avalon-maplewood"
R += b(k, ("yes; floor count not stated", AMEN + " (not in AvalonBay's own feature list)", alsrc("newark/avalon-maplewood"), C), ("001-436: 4; 001-324: 3", "AvalonBay unit records: floorNumber '4' (unit 436), '3' (unit 324)", s, C),
       ("yes", "Pet friendly community featuring WAG Pet Spa and outdoor WAG Pet Park; allowedPets: cats, dogs", s, C), ("none stated", "maximumPetWeight field is 0; no weight sentence on the page", s, U))
k = "218-226 millburn ave|07041"; s = alsrc("newark/218-millburn-avenue")
R += b(k, ("not stated", "amenities listed: Garage, Dogs allowed (no 'Elevator' entry); goldberg-realty.com returned 403", s, U), ("unknown (51C and 10C do not map clearly to a floor)", "units '51C', '10C'", s, U), ("yes", "allowed_pets: cats, dogs; limit 2", s, C), ("not stated", "no weight text", s, U))
k = "34 valley rd|07042"; s = alsrc("upper-montclair/valley-and-bloom")
R += b(k, ("yes; floor count not stated", AMEN + " (valleyandbloom.com returned 403)", s, C), ("36-305: 3 (derived from unit number; '36' = building 36 Valley Rd)", "unit '36-305'", s, U), ("yes", "allowed_pets: cats, dogs; dogs rent $60", s, C), ("limit exists, pounds not published", "Call for breed and weight restrictions.", s, U))
k = "120 neilson st|08901"; s = GS + "the-quincy-new-brunswick-nj/p_17425"
R += b(k, ("not stated; Greystar building type 'Mid-Rise', available units up to floor 4+", "buildingType: Mid-Rise", s, U), ("202: 2; 425: 4", "floorLabel 'Floor 2' (202), 'Floor 4' (425)", s, C), ("yes", "Amenities: 'Dog Park & Pet Spa'; fee 'Pet Rent' $65 monthly", s, C), ("not stated", "no weight or breed text on the page", s, U))
k = "30 clinton st newark nj 07102 usa|07102"; s = "https://www.zumper.com/apartment-buildings/p1647219/clinton-flats-newark-central-business-district-newark-nj"
R += b(k, ("yes; floor count not stated", "Building amenities: '... Dogs OK Elevator Fitness Center ...'", s, C), ("unknown", "floor-plan rows only (Lex II, Madison)", s, U), ("yes", "Dog Policy Allowed Limit 2 Breed restrictions Yes", s, C), ("40 lb", "Max of 2, 40 lbs. Weight Limit.", s, C))
k = "10 commerce ct|07102"; s = alsrc("newark/the-mercer-10-commerce-court-newark-nj")
R += b(k, ("yes; floor count not stated (units listed up to 12x)", AMEN, s, C), ("6E: 6; 8F: 8 (derived from unit number)", "units '6E', '8F'", s, U), ("yes", "allowed_pets: cats, dogs; limit 1", s, C), ("not stated", "no weight text", s, U))
k = "80 freeman st|07105"; s = alsrc("newark/the-ballantine--1")
R += b(k, ("not stated", "amenities listed: Concierge, Dogs allowed, Garage, Dog grooming area (no 'Elevator' entry); theballantine.com returned 403", s, U), ("619: 6 (derived from unit number)", "unit '619'", s, U), ("yes", "allowed_pets: cats, dogs; amenity 'Dog grooming area'", s, C), ("not stated", "no weight text", s, U))
k = "9060 palisade ave d710 n bergen nj 07047 usa|07047"; s = "https://www.zumper.com/listings/30002373p/1-bedroom-north-bergen-nj"
R += b(k, ("yes; floor count not stated", "an outdoor swimming pool, fitness facilities, an elevator, and a community room", s, C), ("7", "this seventh-floor residence features large windows that bring in natural light", s, C), ("yes", "Dog Policy Allowed Cat Policy Allowed Contact for more information on pet policy.", s, C), ("not stated", "Contact for more information on pet policy.", s, U))
k = "508 51st st|07093"; s = GS + "the-grand-west-new-york-nj/p_22449"
R += b(k, ("not stated; Greystar building type 'High-Rise'", "buildingType: High-Rise", s, U), ("0206: 2; 0612: 6", "floorLabel 'Floor 2' (0206), 'Floor 6' (0612)", s, C), ("yes", "Amenities: 'Outdoor Dog Park'; fee 'Pet Rent' $65 monthly", s, C), ("not stated", "no weight or breed text on the page", s, U))
for k, un in (("900 forest park ln 9206|08857", "9206"), ("900 forest park ln 9204|08857", "9204")):
    s = "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge"
    R += b(k, ("not stated; no elevator in AvalonBay's feature list, which mentions 'Select multi-level townhome units available with attached garages' (low-rise community: ASK, unit is on floor 2)", "feature list has no elevator entry", s, U), (f"{un}: 2", "AvalonBay unit record: floorNumber '2'", s, C),
           ("yes", "Cats and dogs are welcome. Please check the dog breed and pet restrictions.", s, C), ("none stated", "maximumPetWeight field is 0; only a restricted-breed list is published", s, U))
k = "500 parq ln|07054"; s = GS + "500-parq-parisppany-nj/p_20984"
R += b(k, ("not stated in words; 6 floors", "Our six-story architectural design seamlessly combines contemporary elegance and urban convenience", s, U), ("558: 5; 627: 6", "floorLabel 'Floor 5' (558), 'Floor 6' (627)", s, C), ("yes", "Amenities: 'Multi-station dog groom facility'; fee 'Pet Rent' $65 monthly", s, C), ("not stated", "no weight or breed text on the page", s, U))
k = "263 franklin ave|07450"; s = alsrc("ridgewood/263-franklin-avenue--1")
R += b(k, ("yes; 5 floors", "Situated in a historic, five story, elevator building near the center of town", s, C), ("unknown (unit '48' in a 48-unit building does not reveal the floor)", "unit '48'", s, U), ("yes", "allowed_pets: cats, dogs; limit 2", s, C), ("not stated", "no weight text; goldberg-realty.com returned 403", s, U))
k = "100 julia dr|07885"; s = "https://www.gardencommunities.com/Properties/NJ/Morris/Pondview-Estates.aspx"
R += b(k, ("not stated; page describes townhomes and 'two-story apartment residences' and lists no elevator (ASK: likely none)", "incredibly open and spacious two-story apartment residences", s, U), ("unknown", "price is per floor plan (One Bedroom); no unit number", s, U), ("yes", "designated parks for small and large dogs; amenity 'Dog Run'", s, C), ("not stated", "no weight text on the page (it names parks 'for small and large dogs')", s, U))
k = "101-616 goodmans crossing|07076"; s = alsrc("clark/riverview-terrace")
R += b(k, ("not stated; 1952 garden complex, unit numbers look like building+unit (ASK: likely none)", "amenities listed: Dogs allowed, Garage (no 'Elevator' entry); year_built 1952", s, U), ("unknown (613 is probably building 6, unit 13)", "unit '613'", s, U), ("yes (dogs named in allowed pets, but only cat fees are listed)", "allowed_pets: cats, dogs; cats rent $35, fee $250", s, C), ("limit exists, pounds not published", "Breed and Weight Restrictions", s, U))
k = "100 park plaza dr|07094"; s = alsrc("secaucus/the-harper-at-harmon-meadow-apartments")
R += b(k, ("not stated on Apartment List or theharperapts.com", "amenities listed: Dog park, Pool, Garage (no 'Elevator' entry)", s, U), ("unknown (1414 may be building 1, floor 4)", "unit '1414'", s, U), ("yes", "We love your dogs! No Breed or Weight Restrictions!. Please call our leasing office for complete pet policy information.", s, C), ("no limit", "We love your dogs! No Breed or Weight Restrictions!.", s, C))
add("confirm", R)
