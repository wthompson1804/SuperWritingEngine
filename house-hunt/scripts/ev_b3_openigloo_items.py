"""Evidence batch 3: Openigloo review excerpts (verbatim, hand-selected from the cached building pages) and building facts.
Dates: Openigloo shows only relative ages; item_date is derived from the fetch date (2026-11-15). Labels such as
'9 minutes ago' on old-looking reviews are treated as undated."""
import csv, json, re, sys, html as H
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
from ev_b3_util import page, put
from h_mgmt_common import strip_tags
B = "https://www.openigloo.com/building/nyc/"
U = {
 "3516": B + "4008101-4006060029/queens-astoria-35-16-34-street-11106",
 "3242": B + "4008345-4006120053/queens-astoria-3242-33-street-11106",
 "2350": B + "4132709-4059580140/queens-bay-terrace-queens-23-50-waters-edge-drive-11360",
 "1670": B + "4131165-4058650112/queens-bay-terrace-queens-16-70-bell-boulevard-11360",
 "867": B + "3418264-3017770058/brooklyn-stuyvesant-heights-867-dekalb-avenue-11206",
 "1875": B + "3017140030-3017140030/brooklyn-weeksville-1889-atlantic-avenue-11233",
 "96": B + "3049320-3017710016/brooklyn-bed-stuy-96-hart-street-11206",
 "3440": B + "3395317-3088120137/brooklyn-brighton-beach-3440-guider-avenue-11235",
 "250": B + "3116266-3050660031/brooklyn-prospect-lefferts-gardens-250-clarkson-avenue-11226",
 "219": B + "3050660091-3050660091/brooklyn-prospect-lefferts-gardens-219-lenox-road-11226",
 "948": B + "3109337-3048860018/brooklyn-erasmus-948-new-york-avenue-11203",
 "3415": B + "3113855-3049980004/brooklyn-east-flatbush-3415-farragut-road-11210",
 "2840": B + "3428817-3039647501/brooklyn-east-new-york-199-schenck-ave-11207",
}
UND = "undated (page label '{}' looks like a display artifact)"
# (key, category, item_date, about, excerpt)
ITEMS = [
 ("3516", "management", UND.format("9 hours ago"), "building", "roof in the building has a huge leak (i seen the sky through my ceiling during the collapse). Unfortunately the building management is horribly neglecting and irresponsible of repair even with multiple open HPD violations."),
 ("3242", "management", "2026-03 (page: '8 months ago')", "management_company", "The cooking gas service been cut in all the apartments already 3 months and counting, not even one worker is in the building, after several emails, management doesn't give any answers when it will be restore."),
 ("3242", "management", "2026-03 (page: '8 months ago')", "management_company", "they want to raise the rent to the tenants for the renewal (14%+) and not even want to negotiate"),
 ("3242", "management", "before 2024-11 (page: 'Over 2 years ago')", "management_company", "The management company A&E was difficult to get a hold of. When I did manage to speak to someone, they informed my they were raising my rent 40%."),
 ("2350", "management", "before 2023-11 (page: 'Over 3 years ago')", "management_company", "The building manager is horrible. He is rude, obnoxious and horrible to deal with."),
 ("2350", "positive", "before 2023-11 (page: 'Over 3 years ago')", "building", "Large apartments, great super & building staff"),
 ("1670", "other", "before 2024-11 (page: 'Over 2 years ago')", "building", "Pet-friendly with restrictions (dogs have to be registered emotional service)."),
 ("1670", "other", "before 2024-11 (page: 'Over 2 years ago')", "garage_or_lot", "The upper parking deck (that we pay for) has had a pothole since January and we’ve been barred from parking on it since, and now have been moved to park on an abandoned tennis court on the other side of the property."),
 ("1670", "positive", "before 2024-11 (page: 'Over 2 years ago')", "building", "on-site building manager/maintenance who is extremely nice & very responsive. Overall very clean."),
 ("867", "management", UND.format("15 minutes ago"), "management_company", "Rent raises are too much, management is terrible and they don’t update or fix the amenities"),
 ("867", "management", "before 2024-11 (page: 'Over 2 years ago')", "management_company", "Management WILL try to steal your deposit. They depend on you not knowing the law and make you fight for your deposit back."),
 ("867", "other", "before 2024-11 (page: 'Over 2 years ago')", "garage_or_lot", "The parking area doorway has no lights, and there is no way to open the door other than getting out of your car to open it."),
 ("867", "positive", "before 2024-11 (page: 'Over 2 years ago')", "building", "The building is usually clean. It’s non-smoking, which is rare for NYC. Never saw a bug or rodent."),
 ("1875", "noise", UND.format("9 minutes ago"), "street", "Lower the rent since your in the hood near projects and across from loud LIRR"),
 ("1875", "positive", UND.format("9 minutes ago"), "building", "Nice gym and rooftop and near fast food"),
 ("96", "management", "before 2025-11 (page: 'Over 1 year ago')", "building", "Rat infestation outside of building - near recycle/trash bins"),
 ("96", "noise", "before 2024-11 (page: 'Over 2 years ago')", "building", "Windows are very old, drafts are huge; a lot of noise from building across the backyard on the back of the building during summer holidays"),
 ("96", "positive", "before 2025-11 (page: 'Over 1 year ago')", "building", "Super lives in building and is relatively responsive - Most neighbors are quiet and respectful"),
 ("3440", "positive", "before 2025-11 (page: 'Over 1 year ago')", "building", "New and updated appliances, floor to ceiling windows, elevator and rooftop"),
 ("250", "management", UND.format("9 minutes ago"), "building", "There are pest issues in a lot of the apartments"),
 ("250", "management", "before 2024-11 (page: 'Over 2 years ago')", "building", "Infested with mice, mold, and roaches throughout the building. It takes constant badgering to get a response from management."),
 ("250", "elevator", "before 2024-11 (page: 'Over 2 years ago')", "building", "It’s great having laundry in the building (when it’s not flooded) and an elevator (when it’s not trapping people inside)."),
 ("219", "management", "2026-07 (page: '4 months ago')", "management_company", "Huge roach infestation. Unprofessional and rude management. Disorganized management - my lease had the wrong name and unit number on it."),
 ("219", "management", "2026-07 (page: '4 months ago')", "management_company", "Unresponsive maintenance - you have to follow up ~4 times for anything to be addressed. No proactive pest control, only reactive"),
 ("219", "positive", "2026-09 (page: '2 months ago')", "building", "Clean and new"),
 ("219", "other", "2026-09 (page: '2 months ago')", "building", "Neighbors smoking mostly"),
 ("948", "management", UND.format("30 minutes ago"), "building", "Location, noise, low water pressure, leaks, poor insulation, cheapest possible appliances"),
 ("3415", "management", UND.format("3 minutes ago") + "; text says 'It is March 17th'", "management_company", "New Day Management is refusing to refund my security deposit deposit. I moved out on 11/1 and they were supposed to return security after 14 days! It is March 17th and they have not contacted me and I have called 16 times"),
 ("3415", "management", UND.format("3 minutes ago") + "; text says 'It is March 17th'", "building", "1. Over $2000 energy bill in 7 months!!! 2 Faulty HVAC system - apt freezing for months"),
 ("3415", "management", "2026-10 (page: '4 weeks ago')", "management_company", "NewDay Management has been a total disaster. Don’t move here!"),
 ("2840", "other", "before 2025-11 (page: 'Over 1 year ago')", "street", "Neighborhood needs a facelift. Not walkable"),
 ("2840", "positive", "before 2025-11 (page: 'Over 1 year ago')", "building", "Very nice amenities"),
]
batch = list(csv.DictReader(open(lib.DATA / "reference" / "evidence_batches" / "batch_3.csv")))
def keys_for(k):
    num = {"3516": "3516 34th", "3242": "3242 33rd", "2350": "23-50 waters", "1670": "16-70 bell", "867": "867 dekalb", "1875": "1875 atlantic",
           "96": "96 hart", "3440": "3440 guider", "250": "250 clarkson", "219": "219 lenox", "948": "948 new york", "3415": "3415 farragut", "2840": "2840 atlantic"}[k]
    return [b for b in batch if b["addr_key"].startswith(num)]
rows, facts, bad = [], [], 0
txt = {}
for k, u in U.items():
    hh, m = page(u)
    txt[k] = (re.sub(r"\s+", " ", H.unescape(strip_tags(hh))), m)
for k, cat, date, about, ex in ITEMS:
    t, m = txt[k]
    if re.sub(r"\s+", " ", ex) not in t:      # verbatim check against the cached page
        bad += 1; print("NOT VERBATIM:", k, ex[:60]); continue
    for b in keys_for(k):
        rows.append(dict(addr_key=b["addr_key"], building_name=b["building_name"] or b["address"].split(",")[0], category=cat, item_date=date,
                         excerpt=ex, source_site="Openigloo", source_url=U[k], about=about, retrieved_at=m["retrieved_at"]))
for k, u in U.items():
    t, m = txt[k]
    mm = re.search(r"Tenants rate it ([\d.]+)/5 across (\d+) reviews?, with (\d+)% recommending it and (\d+)% approving of the owner\. It records (\d+) evictions?, (\d+) open violations?, and (\d+) litigation cases?\. Data last updated ([A-Za-z]+ \d+, \d{4})\.", t)
    mg = re.search(r"(?:is |and )managed by ([^.]{3,80}?)(?:\.|, this building)", t)
    st = re.search(r"(\d+) units · (\d+) floors · Built in (\d{4})", t)
    for b in keys_for(k):
        if mm:
            facts.append(dict(addr_key=b["addr_key"], fact="openigloo_summary", value=f"rating {mm.group(1)}/5 from {mm.group(2)} review(s); evictions {mm.group(5)}; open violations {mm.group(6)}; litigation cases {mm.group(7)}; data updated {mm.group(8)}", quote=mm.group(0), source_url=u))
        if mg:
            facts.append(dict(addr_key=b["addr_key"], fact="management_company", value=mg.group(1).strip(), quote=mg.group(0).strip(), source_url=u))
        if st:
            facts.append(dict(addr_key=b["addr_key"], fact="building_size_openigloo", value=f"{st.group(1)} units; {st.group(2)} floors; built {st.group(3)}", quote=st.group(0), source_url=u))
print(put("items", rows), "item rows;", put("facts", facts), "fact rows; not verbatim:", bad)
