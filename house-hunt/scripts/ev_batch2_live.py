"""Evidence batch 2: write live_check rows from the refreshed pages in raw/evidence_batch2/."""
import csv, json, sys
sys.path.insert(0, "scripts")
from ev_batch2_add import add
rows = list(csv.DictReader(open("data/reference/evidence_batches/batch_2.csv")))
out = []
for r in rows:
    u = r["urls"].split(" | ")[0].strip()
    if "apartmentlist" not in u:
        continue
    d = json.load(open("raw/evidence_batch2/al_%s.json" % u.rsplit("/", 1)[1]))
    L, meta = d["listing"], d["meta"]
    site = (L.get("website_url") or "").split("?")[0]
    cur = {}
    for fp in L["available_units"]:
        for un in fp.get("units") or []:
            cur[un["name"]] = (un, fp)
    chk = L.get("availability_last_checked_at") or "not stated"
    for unit, rent in zip([s.strip() for s in r["unit_list"].split(",")], [s.strip() for s in r["rents"].split(",")]):
        if unit not in cur:
            others = sorted((un["price"], n, un.get("available_on")) for n, (un, fp) in cur.items() if fp["bed"] <= 1 and un["price"] and un["price"] <= 3000)
            note = "unit no longer in the page's unit list. Other studio/1BR units <= $3,000 now listed: " + ("; ".join(f"{n} ${p} avail {a}" for p, n, a in others[:5]) or "none")
            out.append((r["addr_key"], u, unit, "gone", "", "", "no", site, meta["retrieved_at"], note))
            continue
        un, fp = cur[unit]
        on = un.get("available_on") or ""
        price = un["price"]
        notes = [f"Apartment List feed={L.get('source_name')}; feed availability last checked {chk}"]
        if on and on <= meta["retrieved_at"][:10]:
            txt = f"available_on {on} (date already passed: available now)"
            if on < "2026-01-01":
                notes.append("available_on date is over 10 months old: the unit data may be stale, confirm by phone")
        else:
            txt = f"available_on {on}"
            if on > "2026-12-15":
                notes.append("NOT available by 2026-12-15")
        status = "live" if str(price) == rent else "changed"
        if status == "changed":
            notes.append(f"stored rent {rent}, now {price}")
        if price > 3000:
            notes.append("repriced above $3,000")
        out.append((r["addr_key"], u, unit, status, price, txt, "yes" if status == "live" else "no", site, meta["retrieved_at"], "; ".join(notes)))
def m(k):
    return json.load(open(f"raw/evidence_batch2/{k}.meta.json"))["retrieved_at"]
GC = "https://www.gardencommunities.com/Properties/NJ/"
out += [
 ("2 kinderkamack rd|07601", GC + "Bergen/The-Jefferson-Hackensack.aspx", "floor plan A-01 One Bedroom (no unit number published)", "live", 2740, "Available Now", "yes", "https://www.thejeffersonnj.com/ (named in the fees PDF; unit list is on securecafe.com, not fetched)", m("gc_jefferson"), "floor-plan row: '$2,740 - $3,040', 735 sq.ft.; page special: 'Up to 3 months free plus a $1000 move-in credit' on select apartments; other 1BR plans start at $3,125 and $3,175"),
 ("100 julia dr|07885", GC + "Morris/Pondview-Estates.aspx", "floor plan One Bedroom (no unit number published)", "live", 2600, "Available Now", "yes", GC + "Morris/Pondview-Estates.aspx", m("gc_pondview"), "floor-plan row: '$2,600', 662-730 sq.ft.; page special: 'Up to two months free on a new 26-month lease plus a $1500 move-in credit on select apartments'; 'One Bedroom with Basement' $2,775 is available Jan 13 (outside window)"),
 ("20 beacon way|07304", "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/availability/", "O-0404", "live", 2501, "Available Dec 8th", "yes", "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/", m("blt_beacon_avail"), "SightMap embed on the building's own site; floor 4, 772 sq.ft., plan O-A2"),
 ("20 beacon way|07304", "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/availability/", "P-1203", "live", 2495, "Available Nov 28th", "yes", "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/", m("blt_beacon_avail"), "SightMap embed on the building's own site; floor 12, 709 sq.ft., plan P-A11"),
 ("120 neilson st|08901", "https://www.greystar.com/the-quincy-new-brunswick-nj/p_17425", "202", "live", 2694, "availableOn 2026-11-23", "yes", "https://www.greystar.com/the-quincy-new-brunswick-nj/p_17425", m("gs_quincy"), "manager's own page; 12-month base rent 2694; Floor 2; 750 sq.ft.; required monthly: Trash Services - Doorstep $35"),
 ("120 neilson st|08901", "https://www.greystar.com/the-quincy-new-brunswick-nj/p_17425", "425", "live", 2742, "availableOn 2026-10-13 (date passed: available now)", "yes", "https://www.greystar.com/the-quincy-new-brunswick-nj/p_17425", m("gs_quincy"), "manager's own page; 12-month base rent 2742; Floor 4; 777 sq.ft.; required monthly: Trash Services - Doorstep $35"),
 ("508 51st st|07093", "https://www.greystar.com/the-grand-west-new-york-nj/p_22449", "0206", "live", 2725, "availableOn 2026-10-03 (date passed: available now)", "yes", "https://www.greystar.com/the-grand-west-new-york-nj/p_22449", m("gs_grand"), "manager's own page; 12-month base rent 2725; Floor 2; 764 sq.ft.; required monthly: Trash Services - Hauling $25"),
 ("508 51st st|07093", "https://www.greystar.com/the-grand-west-new-york-nj/p_22449", "0612", "live", 2750, "availableOn 2026-11-18", "yes", "https://www.greystar.com/the-grand-west-new-york-nj/p_22449", m("gs_grand"), "manager's own page; 12-month base rent 2750; Floor 6; 697 sq.ft.; required monthly: Trash Services - Hauling $25"),
 ("500 parq ln|07054", "https://www.greystar.com/500-parq-parisppany-nj/p_20984", "558", "live", 2673, "availableOn 2026-10-21 (date passed: available now)", "yes", "https://www.greystar.com/500-parq-parisppany-nj/p_20984", m("gs_parq"), "manager's own page; Floor 5; 884 sq.ft.; required monthly: Trash Services - Hauling $15"),
 ("500 parq ln|07054", "https://www.greystar.com/500-parq-parisppany-nj/p_20984", "627", "live", 2560, "availableOn 2026-08-27 (date passed: available now)", "yes", "https://www.greystar.com/500-parq-parisppany-nj/p_20984", m("gs_parq"), "manager's own page; Floor 6; 748 sq.ft.; required monthly: Trash Services - Hauling $15"),
 ("30 clinton st newark nj 07102 usa|07102", "https://www.zumper.com/apartment-buildings/p1647219/clinton-flats-newark-central-business-district-newark-nj", "floor plan Lex II (1 bed, 588 sqft; no unit number)", "live", 2150, "no date on page ('Check availability'); page 'Updated 11 Hours Ago'", "yes", "", m("zu_clinton"), "Zumper building page, floor-plan level; availability date not published"),
 ("30 clinton st newark nj 07102 usa|07102", "https://www.zumper.com/apartment-buildings/p1647219/clinton-flats-newark-central-business-district-newark-nj", "floor plan Madison (1 bed, 560 sqft; no unit number)", "live", 2200, "no date on page ('Check availability'); page 'Updated 11 Hours Ago'", "yes", "", m("zu_clinton"), "Zumper building page, floor-plan level; availability date not published"),
 ("9060 palisade ave d710 n bergen nj 07047 usa|07047", "https://www.zumper.com/listings/30002373p/1-bedroom-north-bergen-nj", "D710", "live", 1699, "no date on page; page 'Updated 18 Hours Ago'", "yes", "", m("zu_palisade"), "condo unit listed by FBPH Rentals; 815 sqft. CAUTION: $1,699 is far below the same page's North Bergen 1-bed median ($2,500, 'Median rents as of Nov 7 2026') for a doorman/pool building: verify the lister before contact"),
 ("900 forest park ln 9206|08857", "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge/apartment/NJ032-NJ032-009-9206", "9206", "live", 2265, "move-in from 11/16/2026", "yes", "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge", m("av_9206"), "AvalonBay unit page; $2,265 is the 14-month term (total with required Technology Connect $109 = $2,374); 12-month term $2,275 (total $2,384); floor 2 per community page; 809 sq.ft."),
 ("900 forest park ln 9204|08857", "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge/apartment/NJ032-NJ032-009-9204", "9204", "live", 2290, "move-in from 12/10/2026", "yes", "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge", m("av_9204"), "AvalonBay unit page; $2,290 is the 14-month term (total with required Technology Connect $109 = $2,399); 12-month term is $2,700 (total $2,809); 13-month $2,295; floor 2 per community page; 739 sq.ft."),
]
add("live", out)
