"""Evidence batch 2: items_batch_2.csv. Excerpts are verbatim from the fetched page in raw/evidence_batch2/."""
import csv, json, sys
sys.path.insert(0, "scripts")
from ev_batch2_add import add
def m(k): return json.load(open(f"raw/evidence_batch2/{k}.meta.json"))["retrieved_at"]
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_2.csv")))
name = {r["addr_key"]: r["building_name"] or r["address"] for r in rows}
I = []
k = "20 beacon way|07304"; u = "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/"; s = "bltliveworkplay.com (Google reviews widget on the building's own page)"; t = m("blt_beacon")
for cat, d, ex, ab in [
 ("management", "2026-11-01", "Some of the concierge staff are very rude, and it honestly makes me afraid to go pick up my packages.", "building"),
 ("management", "2026-10-16", "This is what gets sold for luxury. Months and months or reaching out to improve conditions and nothing gets done.", "building"),
 ("management", "2026-10-13", "Monthly garage parking fees increase every six months. Management has taken over nearly all the guest parking around the building, and now staff are occupying garage spaces to charge their personal cars using the outlets", "garage_or_lot"),
 ("other", "2026-10-09", "There are still people who do not live here that workout and use the amenities here as recently as 10/7 8:30p.", "building"),
 ("positive", "2026-10-18", "She was extremely professional, patient, responsive, and helpful throughout the entire leasing and move-in process.", "management_company"),
 ("positive", "2026-01-10", "They even let us use the shuttle that takes ppl from the complex to the PATH stations to experience how commuting looks, and it was great.", "building"),
 ("positive", "2025-11-07", "I absolutely love the community, the spacious apartment, the beautiful Art Deco building, and the incredible amenities", "building"),
]:
    I.append((k, name[k], cat, d, ex, s, u, ab, t))
I.append((k, name[k], "other", "2025-08-06", "The non-profit additionally claims that parking and traffic issues described by the public during several meetings were ignored by the Zoning Board, as well as \"the over-close proximity of the proposed...building to existing buildings\" on the Beacon campus.", "jerseydigs.com", "https://jerseydigs.com/595-montgomery-street-jersey-city-lawsuit/", "street", m("jd_beacon_suit")))
k = "155 washington st|07302"
I += [(k, name[k], "management", "2025-04-01", "The case is now facing federal court, after tenants filed a class action lawsuit against Equity Residential seeking financial reparations of over $400 million in damages, including treble damages under the NJ Consumer Fraud Act.", "jerseydigs.com", "https://jerseydigs.com/portside-towers-jersey-city-rent-control-case/", "management_company", m("jd_portside")),
      (k, name[k], "management", "2025-04-01", "The decision paved the way for rent reductions to 2016 rates, providing relief to tenants who had faced increases of up to 50 percent at 155 Washington Street and 100 Warren Street.", "jerseydigs.com", "https://jerseydigs.com/portside-towers-jersey-city-rent-control-case/", "building", m("jd_portside")),
      (k, name[k], "management", "2022-12-07", "\"No filing, no exemption,\" said tenants from Portside Towers who stood in front of Jersey City council members, pleading to follow through with city rent control ordinances as tenants faced rent increases of over 30 percent.", "hudsonreporter.com", "https://hudsonreporter.com/news/jersey-city/portside-tenants-voice-concerns-over-30-rent-increases/", "building", m("hr_portside"))]
k = "200 boyden ave|07040"
I.append((k, name[k], "other", "2017-02-06", "Crews from 24 different fire companies worked for several hours to extinguish a blaze that destroyed part of an AvalonBay apartment complex under construction at 200 Boyden Avenue.", "cbsnews.com", "https://www.cbsnews.com/newyork/news/maplewood-fire-lightweight-wood-construction/", "building", m("cbs_maplewood")))
BASE = "Apartment List, Trulia and Zumper building pages carry no resident reviews; web search for the building name and address (some buildings in combined queries), plus searches limited to News 12, Daily Voice, CBS, Jersey Digs and Hudson Reporter, found no incident, elevator, car-crime or management report. Not readable (robots.txt names Claude or 403): Patch, NJ.com, TAPinto, RE-NJ, Hudson County View, Jersey City Times, northjersey.com, BBB."
extra = {
 "100 park plaza dr|07094": " Unread lead: a Patch (Secaucus) article about a town meeting with the owner over crime at The Harper appears in search results; Patch disallows Claude agents, so nothing was taken from it.",
 "1200 s fifth st|07029": " Bozzuto's own reviews page for Cobalt Lofts exists (bozzuto.com/.../cobalt-lofts/reviews) but its robots.txt disallows ClaudeBot (it allows Claude-User); not read.",
 "1100 s 5th st|07029": " Bozzuto's own reviews pages exist for its buildings but bozzuto.com robots.txt disallows ClaudeBot (it allows Claude-User); not read.",
 "49 fisk st|07305": " Bozzuto's own reviews pages exist for its buildings but bozzuto.com robots.txt disallows ClaudeBot (it allows Claude-User); not read.",
 "1200 frank e rodgers blvd s|07029": " Building site robots.txt disallows Claude agents.",
 "1075 w side ave|07306": " A News 12 report (2026-08) of a shooting at Marion Gardens public housing surfaced in search; distance to this address not established, not recorded as an item.",
 "30 clinton st newark nj 07102 usa|07102": " Unread leads: resident reviews of Clinton Flats on Apartments.com-network pages (forrent.com, a university off-campus housing page) surfaced in search; that network is off limits, nothing was taken.",
 "345 prospect ave|07601": " Unread lead: a 2021 resident review on forrent.com (Apartments.com network, off limits) surfaced in search; nothing was taken.",
 "9060 palisade ave d710 n bergen nj 07047 usa|07047": " No building name known; searched the street address only.",
}
t = m("jd_portside")
have = {r[0] for r in I}
for r in rows:
    if r["addr_key"] not in have:
        I.append((r["addr_key"], name[r["addr_key"]], "none_found", "", BASE + extra.get(r["addr_key"], ""), "", "", "", "2026-11-15T20:55:00+00:00"))
add("items", I)
