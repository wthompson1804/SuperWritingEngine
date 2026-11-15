"""Hand-recorded building facts for the westchester_rockland region pass.

CURATED: key -> building. Keys used by h_region_westchester_rockland.py:
  trulia      Trulia building page (URL without its trailing numeric id; matched by slug) whose unit rows / pet card /
              elevator feature belong to this building
  sightmap    SightMap embed found on the building's own leasing site (site, avail_url, site_host)
  elevator / elev_basis / floors / unit_floor_ok / unit_floor_rx   elevator evidence (page named in elev_basis)
  dogs / dog_text / wl / dog_src                                  dog policy read on the page named in dog_src
  notes       goes into every row's notes;  bnotes goes into the buildings file
Every statement below was read on the page it names on 2026-11-15 (cached under raw/region_westchester_rockland/,
raw/trulia/ or raw/mgmt_gdc/). Nothing here comes from a search-result snippet.
MANUAL_BUILDINGS: buildings examined that produced no unit rows (blocked sites, price above the cap, condos).
"""
T = "https://www.trulia.com/building/"
IN_UNITS = "building already has passing units in data/units.csv from the earlier crawl"

CURATED = {
    # ---------------- own-site SightMap feeds
    "one_webb": dict(name="One Webb Ave", address="1 Webb Avenue", city="Purchase", zip="10577", site="https://onewebbave.com/", site_host="onewebbave.com",
                     avail_url="https://onewebbave.com/floorplans/", sightmap="https://sightmap.com/embed/dqw9do2gvo9", trulia=T + "one-webb-ave-1-webb-ave-purchase-ny-10577",
                     dogs="yes", dog_text='Building site pet policy (onewebbave.com): "One Webb Ave is a pet friendly community and welcomes both dogs and cats. There is a maximum of two pets allowed per apartment home. Certain breed restrictions and fees apply." No weight limit is stated.',
                     dog_src="https://onewebbave.com/", elevator="yes", elev_basis="6+ floors (the SightMap floor list on onewebbave.com runs from 2 to 6; unit numbers 2xx-6xx)", floors=6, unit_floor_ok=True,
                     pet_rent="50", parking_type="garage (optional)", parking_fee="150", manager="NRP Group",
                     notes="pet rent $50/mo, one-time pet fee $500, garage parking $150/mo (optional items in the SightMap fee list); amenity site lists onsite pet spa, dog park, 24/7 package system, secure parking garage"),
    "sawyer_place": dict(name="Sawyer Place", address="45 Main Street", city="Yonkers", zip="10701", site="https://www.sawyerplaceny.com/", site_host="sawyerplaceny.com",
                         avail_url="https://www.sawyerplaceny.com/floor-plans/", sightmap="https://sightmap.com/embed/40vl6682vle", trulia=T + "sawyer-place-50-nepperhan-st-yonkers-ny-10701",
                         elevator="yes", elev_basis="6+ floors (the SightMap floor list on sawyerplaceny.com reaches floor 26)", floors=26, pet_rent="65", parking_type="valet / third-party garage (optional, price varies)",
                         notes="own site says only 'Pet friendly'; pet rent $65/mo in the SightMap fee list; concierge, controlled access with video intercom, package receiving (sawyerplaceny.com/amenities/)"),
    "mitchell": dict(name="The Mitchell", address="131 Mamaroneck Avenue", city="White Plains", zip="10601", site="https://livethemitchell.com/", site_host="livethemitchell.com",
                     avail_url="https://livethemitchell.com/floorplans/", sightmap="https://sightmap.com/embed/jlw097x9w2y", trulia=T + "the-mitchell-131-mamaroneck-ave-white-plains-ny-10601",
                     elevator="yes", elev_basis="6+ floors (the SightMap floor list on livethemitchell.com reaches floor 15)", floors=15,
                     notes="own site: 'The Mitchell is pet-friendly! *Breed restrictions may apply.'"),
    "halden": dict(name="The Halden", address="1137 Westchester Ave", city="White Plains", zip="10605", site="https://thehalden.com/", site_host="thehalden.com",
                   avail_url="https://thehalden.com/floorplans/", sightmap="https://sightmap.com/embed/rxwjj1dzw1e", trulia=T + "the-halden-1137-westchester-ave-west-harrison-ny-10604",
                   notes="own site FAQ: 'Is The Halden pet-friendly? Yes. Breed restrictions apply.' (dogs not named there); SightMap floor list 1-5; unit 2118 is on floor 1 (ground floor)"),
    "huguenot360": dict(name="360 Huguenot", address="360 Huguenot Street", city="New Rochelle", zip="10801", site="https://360huguenot.com/", site_host="360huguenot.com",
                        avail_url="https://360huguenot.com/floorplans/", sightmap="https://sightmap.com/embed/l8xvr3d5vjk",
                        elevator="yes", elev_basis="6+ floors (the SightMap floor list on 360huguenot.com reaches floor 28)", floors=28, dogs="unknown",
                        dog_text='Building site FAQ (360huguenot.com/faqs/): "Yes, 360 Huguenot is a pet-friendly community. Breed restrictions, weight limits, and pet fees apply. Please refer to our community fee guide for complete details." Dogs are not named and the weight limit number is not published on the pages read.',
                        dog_src="https://360huguenot.com/faqs/", parking_type="third-party valet (price on request)", utilities_included="none (FAQ: utilities are not included in base rent)",
                        notes="WEIGHT LIMIT EXISTS BUT NUMBER NOT PUBLISHED: ask the leasing office (914-266-9619); 24/7 concierge, mail and package room"),
    # ---------------- Trulia building pages + hand-checked elevator evidence
    "skyline_nr": dict(trulia=T + "skyline-new-rochelle-40-memorial-hwy-new-rochelle-ny-10801", unit_floor_ok=True,
                       notes="unit numbers are floor + line (08O ... 37I); own site skylinenewrochelle.com redirects to harborgroupmanagement.com, which answers 403"),
    "broad42": dict(trulia=T + "42-broad-42-broad-st-w-mount-vernon-ny-10552", unit_floor_ok=True, site="https://www.42broad.com/",
                    notes="unit numbers are floor + unit (209 ... PH1501); own site 42broad.com says only 'pet-friendly community'; its unit list is on securecafe.com (not fetched)"),
    "hamilton_crossing": dict(trulia=T + "hamilton-crossing-440-hamilton-ave-white-plains-ny-10601", unit_floor_ok=True, unit_floor_rx=r"-(\d{2})\d{2}$", site="https://www.renthamiltoncrossing.com/",
                              notes="unit numbers are building-floor-unit (440-0915 = 440 Hamilton, floor 9; 50-0603 = floor 6), so both buildings have 6+ floors; units 50-01xx are on floor 1; own site: 'We welcome all your furry friends at Hamilton Crossing.'"),
    "park_place_towers": dict(trulia=T + "park-place-towers-1108-brown-st-peekskill-ny-10566", unit_floor_ok=True, notes="unit numbers are floor + line (2L ... 8V); own site parkplacetowers.com answers 403"),
    "hudson44": dict(trulia=T + "hudson-44-44-hudson-st-yonkers-ny-10701", unit_floor_ok=True, floors=25, notes="Trulia description: 'rises 25 stories over the Hudson River'; own site hudson44.com: robots.txt disallows"),
    "regency_hudson": dict(trulia=T + "regency-on-hudson-56-prospect-st-yonkers-ny-10701", unit_floor_ok=True),
    "hudson_park": dict(trulia=T + "hudson-park-community-1-alexander-st-yonkers-ny-10701", unit_floor_ok=True, site="https://hudsonparkny.com/"),
    "magnolia_pc": dict(trulia=T + "the-magnolia-146-westchester-ave-port-chester-ny-10573", unit_floor_ok=True, site="https://themagnoliapc.com/",
                        notes="CONFLICT on dog size: Trulia pet card says 1 dog, Size allowed: Small; own site says 'cat and dog-friendly apartments ... up to two pets' with no size or weight"),
    "main66": dict(trulia=T + "66-main-st-66-main-st-yonkers-ny-10701", unit_floor_ok=True, notes="own site 66main.com answers 403"),
    "miroza": dict(trulia=T + "miroza-tower-iii-601-ridge-hill-blvd-yonkers-ny-10710", unit_floor_ok=True),
    "broad30": dict(trulia=T + "30-broad-street-30-broad-st-port-chester-ny-10573", unit_floor_ok=True),
    "brompton": dict(trulia=T + "the-brompton-1880-palmer-ave-larchmont-ny-10538", unit_floor_ok=True),
    # ---------------- Ginsburg (GDC) buildings: units from Trulia, own-site wording added
    "river_tides": dict(trulia=T + "river-tides-1133-warburton-ave-yonkers-ny-10701", site="https://gdcrentals.com/river-tides/", dogs="yes",
                        dog_text="CONFLICT: building site gdcrentals.com/river-tides/ says '100% Smoke Free and Pet Friendly (with Dog Wash)'; the Trulia pet card says Dogs: Not allowed, Cats: Not allowed. No weight limit is published on either page.",
                        dog_src="https://gdcrentals.com/river-tides/ and the Trulia building page", elevator="yes", elev_basis="Trulia building page lists an elevator; gdcrentals.com calls it 'high-rise'",
                        verdict="unconfirmed:dogs (contradictory policy)",
                        notes="CONFLICT: contradictory dog policy between the building site and Trulia (ask GDC leasing; sister GDC buildings at Haverstraw show a 30 lb dog limit on Trulia); garage parking (reserved), EV charging"),
    "pier70": dict(trulia=T + "70-pier-by-gdc-70-pier-st-yonkers-ny-10705", site="https://gdcrentals.com/70-pier-street/", dogs="unknown",
                   dog_text="CONFLICT: building site gdcrentals.com/70-pier-street/ says 'Smoke-Free and Pet Friendly' (dogs not named); the Trulia pet card says Dogs: Not allowed, Cats: Not allowed.",
                   dog_src="https://gdcrentals.com/70-pier-street/ and the Trulia building page", notes="CONFLICT: contradictory pet policy between the building site and Trulia; indoor garage and outdoor parking"),
    "martine1": dict(trulia=T + "1-martine-at-city-square-1-martine-ave-white-plains-ny-10606", site="https://gdcrentals.com/one-martine/", unit_floor_ok=True,
                     notes="own site gdcrentals.com/one-martine/ lists 'Pet Wash' and indoor garage parking; unit numbers are floor + line"),
    "metro_wp": dict(trulia=T + "the-metro-34-s-lexington-ave-white-plains-ny-10606", site="https://gdcrentals.com/the-metro-2/", unit_floor_ok=True,
                     notes="own site gdcrentals.com/the-metro-2/: 'Pet Friendly and 100% Smoke-Free', enclosed garage parking; unit numbers are floor + line"),
    "fort_hill": dict(trulia=T + "fort-hill-peekskill-1-saint-marys-convent-peekskill-ny-10566", site="https://gdcrentals.com/fort-hill/",
                      notes="own site gdcrentals.com/fort-hill/: '100% Smoke Free Property and is Pet Friendly', indoor garage and outdoor parking, pool, shuttle to Peekskill station; unit numbers are building letter + floor + unit (A207, B102 = floor 1)"),
    "admirals_cove": dict(trulia=T + "admirals-cove-1100-admirals-cove-blvd-haverstraw-ny-10927", site="https://gdcrentals.com/admirals-cove/",
                          notes="Harbors at Haverstraw (GDC). CHECK DOG WEIGHT: this page states no weight limit, but the sister GDC buildings Riverside and Parkside in the same complex show a 30 lb limit on Trulia; own site says only 'Pet Friendly & Smoke-Free buildings'"),
    "riverside_hav": dict(trulia=T + "riverside-4100-southernly-pointe-dr-haverstraw-ny-10927", site="https://gdcrentals.com/riverside/", notes="Harbors at Haverstraw (GDC); own site says only 'Pet Friendly'"),
    "parkside_hav": dict(trulia=T + "parkside-at-the-harbors-2100-round-pointe-dr-haverstraw-ny-10927", site="https://gdcrentals.com/parkside/", notes="Harbors at Haverstraw (GDC); own site says only 'Pet Friendly'"),
    # ---------------- Apartment List property pages (unit rows read earlier today) + building evidence
    "modera_nr": dict(al="Modera New Rochelle", trulia=T + "modera-new-rochelle-111-centre-ave-new-rochelle-ny-10801", unit_floor_ok=True, site="https://www.moderanewrochelle.com/",
                      notes="own site moderanewrochelle.com answers 403 (Mill Creek); elevator, dog policy ($75/mo dog rent, limit 2, restricted breeds) from the Apartment List property page; unit numbers are floor + unit"),
    "gramercy_wp": dict(al="The Gramercy", trulia=T + "the-gramercy-2-canfield-ave-white-plains-ny-10601", unit_floor_ok=True, site="https://www.thegramercywhiteplains.com/",
                        notes="own site thegramercywhiteplains.com answers 403; elevator and dogs from the Apartment List property page; unit 110 is on floor 1"),
    "rockwell_nr": dict(al="Rockwell", trulia=T + "rockwell-585-north-ave-new-rochelle-ny-10801", unit_floor_ok=True, site="https://www.liveatrockwell.com/",
                        notes="own site liveatrockwell.com returns an empty script shell to a plain fetch; unit numbers 2xx-5xx; no page read states an elevator"),
    "encore_nr": dict(al="Encore", trulia=T + "encore-325-huguenot-st-new-rochelle-ny-10801", unit_floor_ok=True, site="https://www.encore325.com/",
                      notes="own site encore325.com answers 403; unit numbers are floor + unit (1009, 1702)"),
    "mason_mam": dict(al="The Mason", trulia=T + "the-mason-270-waverly-ave-mamaroneck-ny-10543", site="https://www.rentthemason.com/", notes="own site rentthemason.com answers 403"),
    "abendroth_pc": dict(al="Abendroth", trulia=T + "the-abendroth-169-n-main-st-port-chester-ny-10573", unit_floor_ok=True, site="https://theabendroth.com/",
                         notes="own site theabendroth.com (pages read: home, floorplans, availability, amenities) shows no prices in plain HTML and does not mention an elevator; its amenities page invites pets without naming a weight; unit numbers 2xx-5xx"),
    "alexan_harrison": dict(al="Alexan Harrison Apartments", trulia=T + "alexan-harrison-3-westchester-park-dr-west-harrison-ny-10604", unit_floor_ok=True,
                            notes="own site is equityapartments.com (Cloudflare wall, not fetched); units 525 and 548 are on floor 5"),
    "ave_cottage": dict(al="AVE Hamilton Green 5 Cottage", site="https://www.aveliving.com/locations/white-plains-ny/hamilton-green-5-cottage/luxury-apartments", unit_floor_ok=True,
                        elevator="yes", elev_basis="6+ floors (the SightMap floor list on aveliving.com reaches floor 24 plus PH)", floors=24,
                        notes="own site aveliving.com: indoor dog run, dog wash; garage parking $225/mo unreserved, $325/mo reserved (FAQ); its SightMap feed showed 13 units, none a studio/1BR at or under $3,000"),
    "riverview_nyack": dict(trulia=T + "riverview-at-nyack-197-sickles-ave-nyack-ny-10960", al="Riverview at Nyack", site="https://www.riverviewatnyack.com/", dogs="yes",
                            dog_text='Building site (riverviewatnyack.com/amenities): "We accept cats and dogs, each subject to a $300.00 deposit, in addition to $60.00 a month in pet rent for a dog and $40.00 for a cat. Breed restrictions apply." Maximum pets per unit: 2. No weight limit stated.',
                            dog_src="https://www.riverviewatnyack.com/amenities", pet_rent="60",
                            notes="own site lists a dog park, on-site laundry room, fitness center; it does not mention an elevator on the pages read (home, floorplans, amenities); own-site floor plans page shows $2,775 and $2,975"),
}

MANUAL_BUILDINGS = []
