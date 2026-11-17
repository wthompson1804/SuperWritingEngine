from R import *
H='nj:west-new-york'; A=B(H)
DP='https://www.visithudson.org/things-to-do/attractions/donnelly-memorial-park/'
BL='https://njmonthly.com/?p=308528'
r(H,'neighborhood','Bergenline Avenue','street','Bergenline Avenue is a busy shopping and eating strip that runs roughly 90 blocks through Union City, West New York, Guttenberg and North Bergen.',
  'New Jersey Monthly, Bergenline Avenue food guide',BL,'high')
r(H,'neighborhood','Donnelly Memorial Park','park','On the Palisades edge, Donnelly Memorial Park looks straight across the Hudson at the Manhattan skyline.',
  'Visit Hudson (Hudson County tourism office), Donnelly Memorial Park',DP,'high')
r(A,'dog_walk','Donnelly Memorial Park','park','Donnelly Memorial Park has a fenced dog park, a dog drinking fountain, shade trees and skyline views.',
  'Visit Hudson (Hudson County tourism office), Donnelly Memorial Park',DP,'high','No rules or hours for the dog area on that page; the town parks page had none either.',ll='osm')
supermarket_rows(A)
for b in A:
    c=nearest(b,'cafe')
    if c and c!='Starbucks': osm_row([b],'weekday',c,'cafe',f'The nearest mapped café is {c}.')
r(A,'saturday','La Pupusa Loca','restaurant','On Bergenline at 59th Street, La Pupusa Loca makes Salvadoran pupusas to order under a neon "Got pupusas?" sign.',
  'New Jersey Monthly, Bergenline Avenue food guide',BL,'medium','5910 Bergenline. 2023 article; not checked on its own page.',ll='osm')
r(A,'saturday','Parriyas','restaurant','Parriyas, at Bergenline and 55th Street since 2021, serves Colombian arepas and plates and a paisa burger.',
  'New Jersey Monthly, Bergenline Avenue food guide',BL,'medium','2023 article; not checked on its own page.')
r(A,'sunday','Dulce de Leche','bakery','For a Sunday bakery stop, Dulce de Leche at 65th and Bergenline is an Argentine bakery that also makes sandwiches such as chori-pan.',
  'New Jersey Monthly, Bergenline Avenue food guide',BL,'medium','2023 article; not checked on its own page.')
