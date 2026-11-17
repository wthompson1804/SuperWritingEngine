from R import *
HB=B('nj:hillsborough'); PS=B('nj:piscataway'); LP=B('nj:lopatcong'); BT=B('nj:boonton'); RW=B('nj:rahway'); HM=B('nj:hamilton')
SMP='https://visitsomersetnj.org/fun-somerset-nj/sourland-mountain-preserve/'
DF='https://www.dukefarms.org/'
EFM='https://eastonpartnership.org/easton-farmers-market/'
JDB='https://jerseydigs.com/boonton-nj-guide/'
UC='https://ucpac.org/about/'
RIH='https://rahwayishappening.com/'
# Hillsborough
r('nj:hillsborough','neighborhood','Duke Farms','park','Duke Farms, the Doris Duke Foundation\'s 2,700-acre campus in Hillsborough, is a conservation center open to local visitors.',
  'Duke Farms (own site)',DF,'medium','Hours and pet rules not shown on the page read.')
r(HB,'dog_walk','Sourland Mountain Preserve','park','The 3,000-plus-acre Sourland Mountain Preserve, run by the Somerset County Park Commission, is wooded hiking country at the edge of the township.',
  'Visit Somerset County (county tourism)',SMP,'medium','Dog rules not on that page; somersetcountyparks.org refused us (403). Trail sites say leashed dogs are allowed; not confirmed.',ll='osm')
r(HB,'sunday','Duke Farms','park','For a Sunday outing, Duke Farms\' 2,700-acre grounds in Hillsborough are open to the public.',
  'Duke Farms (own site)',DF,'medium','Opening days and whether dogs are allowed were not confirmed on the page read.')
# Lopatcong
r(LP,'saturday','Easton Farmers\' Market','market','Across the Delaware in Easton, Pennsylvania, the Easton Farmers\' Market, founded in 1752, is the oldest continuous open-air market in the country.',
  'Greater Easton Development Partnership, Easton Farmers\' Market',EFM,'high','Distance not measured.',schedule='Saturdays 9am to 1pm, May to November; Wednesdays 4 to 8pm, June to September')
# Boonton
r('nj:boonton','neighborhood','Boonton Main Street','street','Boonton grew up as a stop on the Morris Canal; remains of the canal can still be seen in Grace Lord Park, and the downtown is a National Register historic district.',
  'Jersey Digs (local news), October 2024',JDB,'medium')
r(BT,'weekday','Main Street coffee shops','cafe','Boonton\'s Main Street has three independent coffee shops within half a mile, Catfight Coffee among them.',
  'Jersey Digs (local news), October 2024',JDB,'medium','Shops not checked on their own pages.')
r(BT,'saturday','Boonton Main Street galleries and bars','street','Main Street mixes art galleries such as Hollywould Studios and Speakeasy Art Gallery with newer openings like the cocktail bar Ombra and the record shop Hidden Tracks.',
  'Jersey Digs (local news), October 2024',JDB,'medium','Places not checked on their own pages.')
r(BT,'sunday','Grace Lord Park','park','Grace Lord Park keeps remains of the Morris Canal and is a draw for canal history walks.',
  'Jersey Digs (local news), October 2024',JDB,'medium',ll='osm')
# Rahway
r('nj:rahway','neighborhood','Union County Performing Arts Center','theatre','Downtown Rahway is anchored by the Union County Performing Arts Center in the historic Rahway Theatre, listed on the State and National Registers of Historic Places, with three stages.',
  'Union County Performing Arts Center (own site)',UC,'high','')
r(RW,'saturday','Union County Performing Arts Center','theatre','The arts center runs shows on its Main Stage, Hamilton Stage and Fazioli Room downtown.',
  'Union County Performing Arts Center (own site)',UC,'high')
r(RW,'saturday','Rahway Is Happening','event','The downtown events program lists shop and restaurant promotions and holiday events from November 27.',
  'Rahway Is Happening (downtown events site)',RIH,'medium')
# OSM only rows for Hillsborough, Piscataway, Lopatcong, Boonton, Hamilton (not Rahway: building address unknown)
for b in HB+PS+LP+BT:
    if N[b]['park'] and N[b]['park'][0][1] not in ('Sourland Mountain Preserve','Grace Lord Park'):
        p=N[b]['park'][0][1]
        osm_row([b],'dog_walk',p,'park',f'The nearest mapped park is {p}.','No official page for this park was read. OSM data as of 2026-11-14.')
supermarket_rows(HB+PS+LP+BT)
for b in HB+PS+LP+BT:
    c=nearest(b,'cafe')
    if c and c!='Starbucks': osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
