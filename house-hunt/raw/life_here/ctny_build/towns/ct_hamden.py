import csv
H='ct:hamden'
ALL=['b_83debd3403','b_c7c4e6e0fd','b_997440dae7','b_a70d51cf28','b_fd00a92a6c']
NORTH=['b_c7c4e6e0fd','b_a70d51cf28']
SOUTH=['b_83debd3403','b_997440dae7','b_fd00a92a6c']
SG='https://ctparks.com/parks/sleeping-giant-state-park'
BV='https://bestvideo.com/'
OSMN='OpenStreetMap (project extract, 2026-11-14)'
# reuse round-1 Hamden rows (already sourced) for the northern buildings near Town Center Park and Whitney Ave
prior=[r for r in csv.DictReader(open('/home/user/SuperWritingEngine/house-hunt/data/reference/life_here_facts.csv')) if r['neighborhood_id']==H and r['moment']!='sunday' and r['building_id']]
ROWS=[]
seen=set()
for r in prior:
    k=(r['moment'],r['place_name'],r['fact'])
    if k in seen: continue
    seen.add(k)
    d={c:r[c] for c in ['moment','place_name','place_kind','fact','schedule','lat','lon','source_name','source_url','retrieved_at','confidence','notes']}
    d['notes']=(d['notes']+' ' if d['notes'] else '')+'Row carried over from the first Life-here round (Whitney Towers), same source and retrieval.'
    tgt=list(NORTH)
    if r['place_name'] in ("Trader Joe's",): tgt=['b_c7c4e6e0fd']
    if r['place_name'] in ('Hamden Summer Concert Series',"Eli's on Whitney",'Glenwood Drive-In'): tgt=ALL
    d['bids']=tgt
    ROWS.append(d)
ROWS+=[
 dict(bids=[''],hood=H,moment='neighborhood',place_name='Sleeping Giant',place_kind='park',fact='The Sleeping Giant, two miles of traprock ridge shaped like a reclining man, is on Hamden\'s skyline; its 1,439-acre state park has 40 miles of trails.',source_name='Connecticut State Parks (CT DEEP): Sleeping Giant State Park',source_url=SG,confidence='high'),
 dict(bids=SOUTH,moment='dog_walk',place_name='Hamden Dog Park',place_kind='dog_park',fact='The nearest mapped dog park is the Hamden Dog Park in the south of town.',source_name=OSMN,source_url='https://www.openstreetmap.org/way/766144043',confidence='medium',notes='OSM only; no town page with rules or hours was found (directories give 300 Waite St and separate small- and large-dog areas, not confirmed).'),
 dict(bids=ALL,moment='weekday',place_name='Best Video Film & Cultural Center',place_kind='cafe',fact='Best Video on Whitney Avenue is a coffee bar, film archive and small performance space, the last of a legendary video store.',source_name='Best Video Film & Cultural Center (own site)',source_url=BV,confidence='high',notes='1842 Whitney Avenue. Events on most evenings; wine and beer at events per listings.',osm='node/13136707304'),
 dict(bids=['b_83debd3403','b_997440dae7','b_fd00a92a6c'],moment='weekday',place_name='Whitneyville Food Center',place_kind='supermarket',fact='The nearest mapped supermarket is Whitneyville Food Center.',source_name=OSMN,source_url='https://www.openstreetmap.org/way/845773610',confidence='medium',notes='OSM only; hours not checked.'),
 dict(bids=['b_a70d51cf28'],moment='weekday',place_name='Aldi',place_kind='supermarket',fact='The nearest mapped supermarket is Aldi.',source_name=OSMN,source_url='https://www.openstreetmap.org/node/7747853914',confidence='medium',notes='OSM only; hours not checked.',osm='node/7747853914'),
 dict(bids=ALL,moment='saturday',place_name='Best Video Film & Cultural Center',place_kind='other',fact='Best Video runs jazz nights, readings, screenings and book launches through the week.',schedule='Jazz Night with Allen Lowe & The All-Stars, Nov 17, 2026; listings most evenings',source_name='Best Video Film & Cultural Center (own site)',source_url=BV,confidence='high'),
 dict(bids=ALL,moment='sunday',place_name='Sleeping Giant State Park',place_kind='park',fact='Sleeping Giant\'s gravel Tower Trail climbs gently to a stone tower with views of Long Island Sound; dogs are welcome on a leash.',schedule='8am to sunset',source_name='Connecticut State Parks (CT DEEP): Sleeping Giant State Park',source_url=SG,confidence='high',notes='200 Mount Carmel Avenue. Three-mile out-and-back; the park often fills to capacity on fine weekends.'),
]
