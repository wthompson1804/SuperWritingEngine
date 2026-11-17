from R import *
H='nj:woodbridge'; A=B(H)
WDP='https://www.twp.woodbridge.nj.us/861/Dog-Park'
WC='https://www.njarts.net/170892'
OT='https://njmonthly.com/articles/eat-drink/a-guide-to-exploring-edisons-50-indian-restaurants/'
r(H,'neighborhood','Woodbridge summer concerts','event','Woodbridge runs a free summer concert series nearly every night of the week, with national acts on Wednesdays at Parker Press Park and shows in Sewaren, at the high school field and at Anchors Tiki Bar.',
  'NJ Arts (njarts.net), 2026 Woodbridge concerts',WC,'high','Series run by the township arts office (woodbridgeartsnj.org). Shows 7:30pm unless noted; 2026 ran June to late September.')
r(A,'dog_walk','Woodbridge Dog Park','dog_run','The township dog park on Cliff Road in Sewaren is a fenced field with small and big dogs separated by a fence, plus a parking lot and portable toilet.',
  'Woodbridge Township, Dog Park',WDP,'high','No hours or rules posted on that page. Distance not measured.')
for b in A:
    if N[b]['park']:
        p=N[b]['park'][0][1]
        osm_row([b],'dog_walk',p,'park',f'The nearest mapped park is {p}.','No official page for this park was read. OSM data as of 2026-11-14.')
supermarket_rows(A)
for b in A:
    c=nearest(b,'cafe')
    if c: osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(A,'saturday','Woodbridge Summerfest','event','Woodbridge Summerfest is a free all-day June festival at Merrill Park in Iselin with tribute bands, food trucks, a beer garden and a drone show at dusk.',
  'NJ Arts (njarts.net), 2026 Woodbridge concerts',WC,'high','2026: Saturday, June 6.',schedule='One Saturday in June')
r(A,'saturday','Parker Press Park concerts','event','On summer Wednesdays the free series brings national acts to Parker Press Park in downtown Woodbridge.',
  'NJ Arts (njarts.net), 2026 Woodbridge concerts',WC,'high','A weekday event, kept with saturday as the going-out row.',schedule='Wednesdays 7:30pm, summer')
r(['b_08fbde9607'],'saturday','Oak Tree Road','street','Oak Tree Road, the mile-long strip from Edison into Iselin, is lined with plazas of Indian restaurants, supermarkets, jewelers and clothing shops; the Kumar Soni food court is on the Iselin side.',
  'New Jersey Monthly, April 2026',OT,'high')
r(['b_08fbde9607'],'sunday','Oak Tree Road weekend buffets','restaurant','On Sunday afternoons Oak Tree Road fills with shoppers at Patel Brothers and diners at the restaurants\' weekend buffets.',
  'New Jersey Monthly, April 2026',OT,'medium','Individual restaurants not checked on their own pages.')
r(A,'sunday','Anchors Tiki Bar concerts','event','In summer the free series puts Sunday country shows at Anchors Tiki Bar on the Sewaren waterfront.',
  'NJ Arts (njarts.net), 2026 Woodbridge concerts',WC,'high',schedule='Sundays in summer')
