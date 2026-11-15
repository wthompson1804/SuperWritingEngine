"""Evidence pass, batch 4: assemble the four output CSVs from pages already fetched by
evidence_batch_4_fetch.py / _openigloo.py / _get.py. Hand-read findings live in this file as data;
every excerpt/quote is checked to be a verbatim substring of the cached page before it is written.
Idempotent: rewrites the batch-4 files in full."""
import csv, html, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
ROOT = lib.ROOT
EV = ROOT / "data/evidence"; EV.mkdir(exist_ok=True)
LIVE = json.loads((lib.RAW / "evidence_b4/live_summary.json").read_text())
OI = json.loads((lib.RAW / "openigloo/batch4_pages.json").read_text())
BATCH = list(csv.DictReader(open(ROOT / "data/reference/evidence_batches/batch_4.csv")))
T = "https://www.trulia.com/home/"; Z = "https://www.zumper.com/listings/"; O = "https://www.openigloo.com/building/nyc/"

def norm(s):
    s = html.unescape(s).replace("\\n", " ").replace("\\u0026", "&").replace('\\"', '"')
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"'))
_cache = {}
def page_text(url):
    if url in _cache: return _cache[url]
    if url in LIVE: p, ts = ROOT / LIVE[url]["path"], LIVE[url]["retrieved_at"]
    elif url in OI: p, ts = ROOT / OI[url]["path"], OI[url]["retrieved_at"]
    else:
        src = "openigloo" if "openigloo.com" in url else "evidence_b4"
        c, m = lib.cached_get(url, src, ext="html"); p, ts = ROOT / m["path"], m["retrieved_at"]
    raw = p.read_text(encoding="utf8", errors="replace")
    _cache[url] = (norm(re.sub(r"<[^>]+>", " ", raw)) + " " + norm(raw), ts)
    return _cache[url]
BAD = []
def check(q, url):
    if not q: return page_text(url)[1]
    txt, ts = page_text(url)
    if norm(q) not in txt: BAD.append((url[-60:], q[:70]))
    return ts

# ---------------------------------------------------------------- listing URL -> hand-read live facts
# unit, price_now, available text, notes, building_site_url
L = {
 T+"85-05-elmhurst-ave-3j-elmhurst-ny-11373-466548407": ("3J", 2099, "Available now", "listed 2026-11-11; studio; base rent", ""),
 T+"2165-clarendon-rd-2e-brooklyn-ny-11226-466620083": ("2E", 2395, "Available now", "listed 2026-11-14; studio; description gives no building facts", ""),
 T+"1634-flatbush-ave-667-brooklyn-ny-11210-466464245": ("667", 2342, "Available now", "listed 2026-11-05; base rent", ""),
 T+"3420-avenue-h-4g-brooklyn-ny-11210-245055375": ("4G", 1749, "Available now", "listed 2026-11-06; studio", ""),
 Z+"28902181p/1-bedroom-flushing-new-york-ny": ("6D", 2450, "date_available 2026-11-13 (page data); 'Updated 18 Hours Ago'", "same unit as the Trulia row (Metro Real Estate asks $2,400); description: dogs only as service/ESA", ""),
 Z+"29859034p/1-bedroom-flushing-new-york-ny": ("714", 2550, "date_available 2026-11-13 (page data)", "description: dogs only as service/ESA", ""),
 Z+"65719910/1-bedroom-flushing-new-york-ny": ("6G", 2450, "date_available 2026-11-04 (page data)", "TurboTenant feed, listed 2026-11-05", ""),
 T+"142-38-37th-ave-8e-flushing-ny-11354-2068977818": ("8E", 2600, "Available now", "listed 2026-10-28; furnished; $300 building application fee + $150 background check", ""),
 T+"14016-34th-ave-404-flushing-ny-11354-465851197": ("404", 2500, "Available now", "listed 2026-10-29; The Bennington; description: no dogs unless service/ESA", ""),
 Z+"65719902/studio-flushing-new-york-ny": ("2D", 1850, "date_available 2026-11-04 (page data)", "TurboTenant feed, listed 2026-11-05", ""),
 T+"139-81-35th-ave-6d-flushing-ny-11354-2062165222": ("6D", 2400, "Available now", "listed 2026-11-08, price cut $50 that day; Rose Terrace; description: no dogs unless service/ESA", ""),
 Z+"29783777p/studio-flushing-new-york-ny": ("5C", 2150, "date_available 2026-11-13 (page data)", "same unit as the Trulia 13702 Northern Blvd row; description: dogs only as service/ESA", ""),
 T+"136-35-maple-ave-4e-queens-ny-11355-89219296": ("4E", 2200, "Available now", "listed 2026-10-16; co-op, 'Board approval required'", ""),
 T+"4110-bowne-st-5w-flushing-ny-11355-466185521": ("5W", 1925, "Available now", "listed 2026-10-22; price cut $25 on 2026-10-25", ""),
 T+"14212-41st-ave-502-flushing-ny-11355-466588117": ("502", 2550, "Available now", "listed 2026-11-12", ""),
 T+"14227-barclay-ave-316-flushing-ny-11355-466617922": ("316", 2200, "Available now", "listed 2026-11-13", ""),
 T+"13702-northern-blvd-5c-flushing-ny-11354-465602188": ("5C", 2150, "Available now", "listed 2026-10-06; North Main Towers; description: no dogs unless service/ESA", ""),
 T+"14345-sanford-ave-602-flushing-ny-11355-2118604043": ("602", 1900, "Available now", "listed 2026-11-03; 'Pictures can be of a similar unit'", ""),
 T+"139-55-35th-ave-5mm-flushing-ny-11354-466537255": ("5MM", 2350, "Available now", "listed 2026-11-10", ""),
 "https://www.apartmentlist.com/ny/queens/98-76-queens-blvd--1": ("2M", 1663, "available_on 2026-11-14, available now", "1BR 900 sqft at $1,663 is far below the area's other listings in this batch: verify the price by phone before touring", ""),
 Z+"30083571p/1-bedroom-rego-park-new-york-ny": ("A3", 1699, "date_available 2026-11-20 (page data)", "Galaxy Tower condo, listed 2026-11-12; page data lists a $3,400 'Moveinfee' (not marked required); low price for a 1BR: verify", ""),
 T+"109-10-queens-blvd-12c-forest-hills-ny-11375-466311584": ("12C", 2795, "Available now", "listed 2026-10-29; price cut $105 on 2026-11-05; 'apt under renovation, pics of same layout unit'", ""),
 T+"63-60-102nd-st-d-8-rego-park-ny-11374-31977450": ("D-8", 2750, "Available Dec 1", "listed 2026-11-11; 'Available For December 1st Move-In'", ""),
 T+"273-w-131st-st-4f-new-york-ny-10027-466557585": ("4F", 2595, "Available now (description: 'Current tenant is vacating 11/30')", "listed 2026-11-11; real move-in is after 2026-11-30, inside the window", ""),
 "https://www.apartmentlist.com/ny/hempstead/479-front-street": ("2F", 2650, "available_on 2026-11-02, available now", "same unit as the Zumper row", ""),
 Z+"1103429p/1-bedroom-hempstead-ny": ("2F", 2650, "date_available 2026-11-02 (page data)", "Village Lofts; description adds WST $30/mo, pet fee $50/mo, parking $75/mo", ""),
 Z+"28196958p/1-bedroom-jackson-heights-new-york-ny": ("H41", 2175, "date_available 2026-05-05 (page data); unit list shows H41 'Available'", "La Mesa Verde; listed 2026-10-29", ""),
 Z+"28794097p/1-bedroom-jackson-heights-new-york-ny": ("E63", 2150, "date_available 2026-10-14 (page data)", "La Mesa Verde; listed 2026-11-09", ""),
 Z+"29641750p/studio-jackson-heights-new-york-ny": ("E42", 1800, "date_available 2026-09-23 (page data)", "La Mesa Verde; address line says #E12 but the page's unit field says E42; listed 2026-09-23", ""),
 T+"34-19-90th-st-451-jackson-heights-ny-11372-466242622": ("451", 2100, "Available now", "La Mesa Verde; listed 2026-10-26; description says 'Walk Up Building'", ""),
 Z+"22717917p/studio-jackson-heights-new-york-ny": ("H53", 1850, "date_available 2026-08-05 (page data)", "La Mesa Verde; address line says #H51 but the page's unit field says H53; listed 2026-10-14", ""),
 T+"148-37-88th-ave-5g-jamaica-ny-11435-2066432661": ("5G", 2425, "Available now", "Archer House; listed 2026-10-27; own site shows no unit list ('For current availability, call')", "https://www.archerhousenyc.com/"),
 T+"148-37-88th-ave-6a-jamaica-ny-11435-2066489615": ("6A", 2450, "Available now", "Archer House; listed 2026-10-14", "https://www.archerhousenyc.com/"),
 T+"153-10-88th-ave-621-jamaica-ny-11432-466380287": ("621", 2550, "Available now", "The 88; listed 2026-11-02; own site shows no unit prices", "https://www.the88nyc.com/"),
}
MULTI = [  # building pages with several stored units: (addr_key, url, unit, stored, now, avail, status, notes, site)
 ("105 corporate park dr|10604", "https://www.apartmentlist.com/ny/harrison/carraway", "3035", 2700, 2700, "available_on 2026-10-16, available now", "live",
  "base rent. Own site (floor-plans page) shows Studio-S2 'From $2,847.14 Total Monthly Price' = base + $147.14 required monthly fees; with pet rent $50 and parking $125 that is $3,022.14 before electric", "https://www.livecarraway.com/floor-plans/"),
 ("105 corporate park dr|10604", "https://www.apartmentlist.com/ny/harrison/carraway", "3078", 2795, 2805, "available_on 2026-10-05, available now", "changed",
  "base rent up $10. Own site shows Studio-S6 'From $2,952.14 Total Monthly Price'; with pet rent $50 and parking $125 that is $3,127.14 before electric", "https://www.livecarraway.com/floor-plans/"),
 ("14725 94th ave|11435", "https://www.trulia.com/building/alvista-rise-14725-94th-ave-jamaica-ny-11435-2751621369", "2410", 2365, 2365, "Available Now", "live",
  "NET-EFFECTIVE price: page says gross rent is $2,800 (2.5 months free on an 18-month lease). Own site alvistarise.com failed TLS (certificate hostname mismatch), not fetched", ""),
 ("14725 94th ave|11435", "https://www.trulia.com/building/alvista-rise-14725-94th-ave-jamaica-ny-11435-2751621369", "1922", 2435, 2435, "Available Now", "live",
  "NET-EFFECTIVE price: page says gross rent is $2,825 (2.5 months free on an 18-month lease)", ""),
]
live_rows = []
for r in BATCH:
    urls = list(dict.fromkeys(u.strip() for u in r["urls"].split("|")))
    stored = [x.strip() for x in r["rents"].split(",")]
    for u in urls:
        if u in L:
            unit, price, avail, notes, site = L[u]
            st = stored[0]
            if r["addr_key"].startswith("148-37"):
                st = stored[0] if unit == "5G" else stored[1]
            match = "yes" if str(price) == st else "no"
            if unit not in [x.strip() for x in r["unit_list"].split(",")]:
                notes += f"; stored unit list says {r['unit_list']}"
            live_rows.append([r["addr_key"], u, unit, "live" if match == "yes" else "changed", price, avail, match, site, LIVE[u]["retrieved_at"], notes])
for ak, u, unit, st, now, avail, status, notes, site in MULTI:
    live_rows.append([ak, u, unit, status, now, avail, "yes" if st == now else "no", site, LIVE[u]["retrieved_at"], notes])
with open(EV / "live_check_batch_4.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow("addr_key,listing_url,unit,status,price_now,available_now_text,matches_stored,building_site_url,checked_at,notes".split(",")); w.writerows(live_rows)

# ---------------------------------------------------------------- building groups (same building, several batch rows)
def keys(*frags):
    out = [r["addr_key"] for r in BATCH if any(r["addr_key"].startswith(x) for x in frags)]
    assert out, frags
    return out
G = {
 "elm": keys("85-05 elmhurst"), "clar": keys("2165 clarendon"), "flat": keys("1634 flatbush"), "aveh": keys("3420 ave h"),
 "rose": keys("139-81 35th"), "benn": keys("140-16 34th", "14016 34th"), "sanf133": keys("13324 sanford"), "37th": keys("142-38 37th"),
 "nmt": keys("137-02 northern", "13702 northern"), "maple": keys("136-35 maple"), "bowne": keys("4110 bowne"), "41st": keys("14212 41st"),
 "barc": keys("14227 barclay"), "sanf143": keys("14345 sanford"), "13955": keys("139-55 35th"), "9876": keys("98-76 queens"),
 "galaxy": keys("9508 65th"), "10910": keys("109-10 queens"), "6360": keys("63-60 102nd"), "w131": keys("273 w 131st"),
 "carr": keys("105 corporate"), "front": keys("479 front"), "lmv": keys("34-47 90th", "34-32 91st", "34-33 90th", "34-19 90th", "34-46 91st"),
 "alv": keys("14725 94th"), "archer": keys("148-37 88th"), "the88": keys("153-10 88th"),
}
NAME = {"rose": "Rose Terrace", "benn": "The Bennington", "nmt": "North Main Towers", "galaxy": "Galaxy Tower", "carr": "Carraway",
        "front": "Village Lofts", "lmv": "La Mesa Verde", "alv": "Alvista Rise", "archer": "Archer House", "the88": "The 88", "flat": "1634 Flatbush Ave"}
u_ = {  # short names for source pages
 "elm_t": T+"85-05-elmhurst-ave-3j-elmhurst-ny-11373-466548407", "elm_o": O+"4037521-4015180050/queens-elmhurst-85-05-elmhurst-avenue-11373",
 "clar_t": T+"2165-clarendon-rd-2e-brooklyn-ny-11226-466620083",
 "flat_t": T+"1634-flatbush-ave-667-brooklyn-ny-11210-466464245", "flat_o": O+"3428953-3075770060/brooklyn-east-flatbush-1634-flatbush-ave-11210",
 "aveh_t": T+"3420-avenue-h-4g-brooklyn-ny-11210-245055375", "aveh_o1": O+"3337329-3075790029/brooklyn-flatlands-3310-avenue-h-11210", "aveh_o2": O+"3413638-3075790029/brooklyn-east-flatbush-3320-avenue-h-11210",
 "rose_z": Z+"28902181p/1-bedroom-flushing-new-york-ny", "rose_t": T+"139-81-35th-ave-6d-flushing-ny-11354-2062165222", "rose_o": O+"4112964-4049940070/queens-flushing-139-81-35-avenue-11354",
 "benn_z": Z+"29859034p/1-bedroom-flushing-new-york-ny", "benn_t": T+"14016-34th-ave-404-flushing-ny-11354-465851197", "benn_o": O+"4112947-4049940017/queens-flushing-140-16-34-avenue-11354",
 "s133_z": Z+"65719910/1-bedroom-flushing-new-york-ny", "s133_z2": Z+"65719902/studio-flushing-new-york-ny", "s133_o": O+"4115368-4051210017/queens-flushing-133-24-sanford-avenue-11355",
 "37_t": T+"142-38-37th-ave-8e-flushing-ny-11354-2068977818",
 "nmt_z": Z+"29783777p/studio-flushing-new-york-ny", "nmt_t": T+"13702-northern-blvd-5c-flushing-ny-11354-465602188", "nmt_o": O+"4112343-4049770021/queens-flushing-137-02-northern-boulevard-11354",
 "maple_t": T+"136-35-maple-ave-4e-queens-ny-11355-89219296", "maple_o": O+"4115672-4051340059/queens-flushing-136-35-maple-avenue-11355",
 "bowne_t": T+"4110-bowne-st-5w-flushing-ny-11355-466185521",
 "41_t": T+"14212-41st-ave-502-flushing-ny-11355-466588117", "41_o": O+"4114651-4050460006/queens-flushing-14212-41-avenue-11355",
 "barc_t": T+"14227-barclay-ave-316-flushing-ny-11355-466617922", "barc_o": O+"4114654-4050460037/queens-flushing-142-27-barclay-avenue-11355",
 "s143_t": T+"14345-sanford-ave-602-flushing-ny-11355-2118604043",
 "13955_t": T+"139-55-35th-ave-5mm-flushing-ny-11354-466537255", "13955_o": O+"4112965-4049940078/queens-flushing-139-55-35-avenue-11354",
 "9876_a": "https://www.apartmentlist.com/ny/queens/98-76-queens-blvd--1", "9876_o": O+"4074783-4031597501/queens-rego-park-98-76-queens-boulevard-11374",
 "gal_z": Z+"30083571p/1-bedroom-rego-park-new-york-ny",
 "10910_t": T+"109-10-queens-blvd-12c-forest-hills-ny-11375-466311584", "10910_o": O+"4078024-4032580001/queens-forest-hills-10910-queens-blvd-11375",
 "6360_t": T+"63-60-102nd-st-d-8-rego-park-ny-11374-31977450", "6360_o": O+"4050659-4021127501/queens-rego-park-63-60-102-street-11374",
 "w131_t": T+"273-w-131st-st-4f-new-york-ny-10027-466557585", "w131_o": O+"1058687-1019370001/manhattan-harlem-273-west-131-street-10027",
 "carr_a": "https://www.apartmentlist.com/ny/harrison/carraway", "carr_fp": "https://www.livecarraway.com/floor-plans/", "carr_am": "https://www.livecarraway.com/amenities/", "carr_ft": "https://www.livecarraway.com/features/",
 "front_a": "https://www.apartmentlist.com/ny/hempstead/479-front-street", "front_z": Z+"1103429p/1-bedroom-hempstead-ny",
 "lmv_h41": Z+"28196958p/1-bedroom-jackson-heights-new-york-ny", "lmv_e63": Z+"28794097p/1-bedroom-jackson-heights-new-york-ny", "lmv_e42": Z+"29641750p/studio-jackson-heights-new-york-ny",
 "lmv_h53": Z+"22717917p/studio-jackson-heights-new-york-ny", "lmv_451": T+"34-19-90th-st-451-jackson-heights-ny-11372-466242622",
 "lmv_o1": O+"4431424-4014510047/queens-jackson-heights-34-19-90-street-11372", "lmv_o2": O+"4431425-4014510047/queens-jackson-heights-34-33-90-street-11372",
 "lmv_o3": O+"4431358-4014510012/queens-jackson-heights-34-46-91-street-11372", "lmv_o4": O+"4431342-4014510012/queens-jackson-heights-34-18-91-st-11372",
 "lmv_ql": "https://queensledger.com/?p=16832", "lmv_pny": "https://politicsny.com/2026/02/24/mesa-verde-tenants-rally-for-repairs-in-jackson-heights-as-several-residents-report-a-month-of-no-heat/",
 "alv_t": "https://www.trulia.com/building/alvista-rise-14725-94th-ave-jamaica-ny-11435-2751621369", "alv_o": O+"4618544-4099987502/queens-jamaica-14725-94-ave-11435",
 "arch_t": T+"148-37-88th-ave-5g-jamaica-ny-11435-2066432661", "arch_o": O+"4595994-4096940049/queens-jamaica-148-37-88-avenue-11435", "arch_o2": O+"4096940049-4096940049/queens-jamaica-hills-148-31-88-avenue-11435",
 "arch_site": "https://www.archerhousenyc.com/archer/amenities/",
 "88_t": T+"153-10-88th-ave-621-jamaica-ny-11432-466380287", "88_o": O+"4097620010-4097620010/queens-briarwood-153-10-88-avenue-11432", "88_site": "https://www.the88nyc.com/amenities/",
 "zara_ag": "https://ag.ny.gov/press-release/2025/attorney-general-james-and-hcr-commissioner-visnauskas-sue-queens-landlord",
}
SMALL = "Cats, small dogs allowed"   # Trulia's structured pet line, identical on every broker listing in this batch
NODOG_T = "Cats are ok but no dogs unless service or emotional support dogs."
NODOG_Z = "Dog is allowed only for service or emotional support dogs."

# ---------------------------------------------------------------- confirm: (group, fact, value, quote, src, status)
C = [
 ("elm", "elevator", "yes; 6 floors", "6 floors", "elm_o", "confirmed"), ("elm", "elevator", "yes (listing feature 'Elevator')", "Elevator", "elm_t", "confirmed"),
 ("elm", "floor", "3 (inferred from unit number 3J only)", "", "elm_t", "unconfirmed"),
 ("elm", "dogs_allowed", "yes (structured pet line; description asks 'Any pets?')", SMALL, "elm_t", "confirmed"),
 ("elm", "dog_weight_limit", "not stated; page says small dogs", SMALL, "elm_t", "unconfirmed"),
 ("clar", "elevator", "not stated on listing; building not on Openigloo's reviewed list", "", "clar_t", "unconfirmed"),
 ("clar", "floor", "2 (inferred from unit number 2E only)", "", "clar_t", "unconfirmed"),
 ("clar", "dogs_allowed", "yes (structured pet line only)", SMALL, "clar_t", "confirmed"), ("clar", "dog_weight_limit", "not stated; page says small dogs", SMALL, "clar_t", "unconfirmed"),
 ("flat", "elevator", "yes; 13 floors", "Rising proudly across 13 floors", "flat_t", "confirmed"),
 ("flat", "floor", "6 (inferred from unit number 667 only)", "", "flat_t", "unconfirmed"),
 ("flat", "dogs_allowed", "yes (structured pet line; Openigloo calls it pet-friendly)", SMALL, "flat_t", "confirmed"), ("flat", "dog_weight_limit", "not stated; page says small dogs", SMALL, "flat_t", "unconfirmed"),
 ("aveh", "elevator", "yes (listing feature 'Elevator'); floor count not found for 3420 itself", "Elevator", "aveh_t", "confirmed"),
 ("aveh", "floor", "4 (inferred from unit number 4G only)", "", "aveh_t", "unconfirmed"),
 ("aveh", "dogs_allowed", "yes (structured pet line only)", SMALL, "aveh_t", "confirmed"), ("aveh", "dog_weight_limit", "not stated; page says small dogs", SMALL, "aveh_t", "unconfirmed"),
 ("rose", "elevator", "yes; 6 floors (Openigloo)", "elevator building", "rose_t", "confirmed"),
 ("rose", "floor", "6", "Unit is located on 6th floor.", "rose_z", "confirmed"),
 ("rose", "dogs_allowed", "NO: service or emotional-support dogs only", NODOG_T, "rose_t", "contradicts"),
 ("rose", "dogs_allowed", "NO: service or emotional-support dogs only", NODOG_Z, "rose_z", "contradicts"),
 ("rose", "dog_weight_limit", "n/a: dogs not allowed", NODOG_T, "rose_t", "contradicts"),
 ("benn", "elevator", "yes; 12 floors (Openigloo)", "elevator building", "benn_t", "confirmed"),
 ("benn", "floor", "7 for unit 714, 4 for unit 404 (inferred from unit numbers only)", "", "benn_z", "unconfirmed"),
 ("benn", "dogs_allowed", "NO: service or emotional-support dogs only", NODOG_T, "benn_t", "contradicts"),
 ("benn", "dogs_allowed", "NO: service or emotional-support dogs only", NODOG_Z, "benn_z", "contradicts"),
 ("benn", "dog_weight_limit", "n/a: dogs not allowed", NODOG_Z, "benn_z", "contradicts"),
 ("sanf133", "elevator", "not stated on either listing; Openigloo: 10 floors", "10 floors", "s133_o", "unconfirmed"),
 ("sanf133", "floor", "6 for 6G, 2 for 2D (inferred from unit numbers only)", "", "s133_z", "unconfirmed"),
 ("sanf133", "dogs_allowed", "yes per Zumper policy block (Dog | Policy | Allowed); nothing in the owner's description", "Contact for more information on pet policy.", "s133_z", "unconfirmed"),
 ("sanf133", "dog_weight_limit", "not stated", "", "s133_z", "unconfirmed"),
 ("37th", "elevator", "yes (listing feature 'Elevator'); floor count not found", "Elevator", "37_t", "confirmed"),
 ("37th", "floor", "8", "Facing south on 8th floor", "37_t", "confirmed"),
 ("37th", "dogs_allowed", "small pets only; dogs not named in the description", "Small pets allowed.", "37_t", "unconfirmed"),
 ("37th", "dog_weight_limit", "not stated; 'small pets'", "Small pets allowed.", "37_t", "unconfirmed"),
 ("nmt", "elevator", "yes; 8 floors (Openigloo)", "elevator building", "nmt_t", "confirmed"),
 ("nmt", "floor", "5 (inferred from unit number 5C only)", "", "nmt_t", "unconfirmed"),
 ("nmt", "dogs_allowed", "NO: service or emotional-support dogs only", NODOG_T, "nmt_t", "contradicts"),
 ("nmt", "dogs_allowed", "NO: service or emotional-support dogs only", NODOG_Z, "nmt_z", "contradicts"),
 ("nmt", "dog_weight_limit", "n/a: dogs not allowed", NODOG_T, "nmt_t", "contradicts"),
 ("maple", "elevator", "yes; 6 floors", "6 floors", "maple_o", "confirmed"),
 ("maple", "floor", "4 (inferred from unit number 4E only)", "", "maple_t", "unconfirmed"),
 ("maple", "dogs_allowed", "structured pet line only; co-op, board approval required", "Board approval required.", "maple_t", "unconfirmed"),
 ("maple", "dog_weight_limit", "not stated; page says small dogs", SMALL, "maple_t", "unconfirmed"),
 ("bowne", "elevator", "not stated on listing; building not on Openigloo's reviewed list", "", "bowne_t", "unconfirmed"),
 ("bowne", "floor", "5 (inferred from unit number 5W only)", "", "bowne_t", "unconfirmed"),
 ("bowne", "dogs_allowed", "yes (structured pet line only)", SMALL, "bowne_t", "confirmed"), ("bowne", "dog_weight_limit", "not stated; page says small dogs", SMALL, "bowne_t", "unconfirmed"),
 ("41st", "elevator", "yes per a tenant review; 6 floors (Openigloo). Listing does not say", "Elevator building.", "41_o", "confirmed"),
 ("41st", "floor", "5 (inferred from unit number 502 only)", "", "41_t", "unconfirmed"),
 ("41st", "dogs_allowed", "yes (structured pet line only)", SMALL, "41_t", "confirmed"), ("41st", "dog_weight_limit", "not stated; page says small dogs", SMALL, "41_t", "unconfirmed"),
 ("barc", "elevator", "yes per a tenant review; 6 floors (Openigloo). Listing does not say", "elevator sometimes breaks", "barc_o", "confirmed"),
 ("barc", "floor", "3 (inferred from unit number 316 only)", "", "barc_t", "unconfirmed"),
 ("barc", "dogs_allowed", "yes (structured pet line; Openigloo calls it pet-friendly)", SMALL, "barc_t", "confirmed"), ("barc", "dog_weight_limit", "not stated; page says small dogs", SMALL, "barc_t", "unconfirmed"),
 ("sanf143", "elevator", "yes (listing feature 'Elevator'); floor count not found", "Elevator", "s143_t", "confirmed"),
 ("sanf143", "floor", "6 (inferred from unit number 602 only)", "", "s143_t", "unconfirmed"),
 ("sanf143", "dogs_allowed", "yes (structured pet line only)", SMALL, "s143_t", "confirmed"), ("sanf143", "dog_weight_limit", "not stated; page says small dogs", SMALL, "s143_t", "unconfirmed"),
 ("13955", "elevator", "yes; 6 floors (Openigloo)", "Elevator and Laundry in the building", "13955_t", "confirmed"),
 ("13955", "floor", "5 (inferred from unit number 5MM only)", "", "13955_t", "unconfirmed"),
 ("13955", "dogs_allowed", "yes: 'Pet friendly' in description plus structured pet line", "Pet friendly", "13955_t", "confirmed"), ("13955", "dog_weight_limit", "not stated; page says small dogs", SMALL, "13955_t", "unconfirmed"),
 ("9876", "elevator", "yes; 6 floors (Openigloo)", "elevator, laundry, live in super", "9876_a", "confirmed"),
 ("9876", "floor", "2 (inferred from unit number 2M only)", "", "9876_a", "unconfirmed"),
 ("9876", "dogs_allowed", "yes per Apartment List pet data (allowed_pets cats, dogs); no policy text", "", "9876_a", "unconfirmed"), ("9876", "dog_weight_limit", "not stated", "", "9876_a", "unconfirmed"),
 ("galaxy", "elevator", "yes; floor count not found", "Located in an elevator building", "gal_z", "confirmed"),
 ("galaxy", "floor", "not stated; unit 'A3' does not show a floor", "", "gal_z", "unconfirmed"),
 ("galaxy", "dogs_allowed", "yes per Zumper policy block and 'dogs and cats ok' chip; condo, owner's description silent", "Contact for more information on pet policy.", "gal_z", "unconfirmed"),
 ("galaxy", "dog_weight_limit", "not stated", "", "gal_z", "unconfirmed"),
 ("10910", "elevator", "yes; 12 floors (Openigloo)", "12 floors", "10910_o", "confirmed"),
 ("10910", "floor", "12 (inferred from unit number 12C only)", "", "10910_t", "unconfirmed"),
 ("10910", "dogs_allowed", "yes: 'Pet friendly' in description plus structured pet line", "Pet friendly", "10910_t", "confirmed"), ("10910", "dog_weight_limit", "not stated; page says small dogs", SMALL, "10910_t", "unconfirmed"),
 ("6360", "elevator", "yes; 6 floors (Openigloo)", "4th-Floor Apartment With Elevator Access", "6360_t", "confirmed"),
 ("6360", "floor", "4", "4th-Floor Apartment With Elevator Access", "6360_t", "confirmed"),
 ("6360", "dogs_allowed", "small pets with landlord approval; dogs not named. Openigloo's building summary says 'it is not pet-friendly'", "Small Pets Allowed With Landlord Approval", "6360_t", "unconfirmed"),
 ("6360", "dog_weight_limit", "not stated; 'small pets'", "Small Pets Allowed With Landlord Approval", "6360_t", "unconfirmed"),
 ("w131", "elevator", "yes; 8 floors (Openigloo)", "BRIGHT 1 BED IN ELEVATOR BUILDING", "w131_t", "confirmed"),
 ("w131", "floor", "4 (inferred from unit number 4F only)", "", "w131_t", "unconfirmed"),
 ("w131", "dogs_allowed", "yes (structured pet line only; description silent)", SMALL, "w131_t", "confirmed"), ("w131", "dog_weight_limit", "not stated; page says small dogs", SMALL, "w131_t", "unconfirmed"),
 ("carr", "elevator", "yes per Apartment List amenity list ('Elevator'); floor count not stated (unit numbers run G, 1xxx to 5xxx)", "", "carr_a", "confirmed"),
 ("carr", "floor", "3 for both 3035 and 3078 (inferred from unit numbers only)", "", "carr_a", "unconfirmed"),
 ("carr", "dogs_allowed", "yes: own site lists Pet Rent and a pet spa; Apartment List amenity 'Dogs allowed'", "Pet Rent $50.00 Monthly", "carr_fp", "confirmed"),
 ("carr", "dog_weight_limit", "not stated on the building's site or Apartment List", "", "carr_fp", "unconfirmed"),
 ("front", "elevator", "yes; floor count not stated", "The elevator building also offers controlled access, and on-site parking.", "front_z", "confirmed"),
 ("front", "floor", "2 (inferred from unit number 2F only)", "", "front_z", "unconfirmed"),
 ("front", "dogs_allowed", "yes: Zumper policy block 'Dog | Policy | Allowed', Apartment List allowed_pets dogs, and a monthly pet fee", "Pet fee: $50/month", "front_z", "confirmed"),
 ("front", "dog_weight_limit", "not stated", "", "front_z", "unconfirmed"),
 ("lmv", "elevator", "CONFLICTING: six-story, six-building complex with only two elevators; tenants say some buildings are walk-ups and both elevators were out for over six months in 2025", "Elevator only in 2 of the buildings", "lmv_o1", "contradicts"),
 ("lmv", "elevator", "the manager's own listing for unit 451 says walk-up", "Walk Up Building", "lmv_451", "contradicts"),
 ("lmv", "elevator", "older listing by the same agent", "Elevator (In Center Of Building)", "lmv_h53", "unconfirmed"),
 ("lmv", "elevator", "complex is six stories; which buildings have an elevator is not established", "a six story, six building complex in Jackson Heights spanning 90th and 91st with the buildings connected by sky bridges", "lmv_h53", "unconfirmed"),
 ("lmv", "floor", "by unit numbering: H41 = 4, E63 = 6, E42 = 4, 451 = 4 or 5, H53 = 5 (inferred; not stated on any page)", "", "lmv_h41", "unconfirmed"),
 ("lmv", "dogs_allowed", "yes: 'Pets are allowed in the building' (2026 listing text) and Zumper policy block", "Pets are allowed in the building.", "lmv_h53", "confirmed"),
 ("lmv", "dog_weight_limit", "30 lb in an older listing (unit H13, first listed Dec 2023, now occupied) by the same agent; current listings give no limit and say the complex is 'under new management'", "Pet Friendly up to 30 Pounds", "lmv_h53", "unconfirmed"),
 ("alv", "elevator", "yes; 25 stories", "The brand new, 25-story Alvista Rise rental property", "alv_t", "confirmed"),
 ("alv", "floor", "24 for unit 2410, 19 for unit 1922 (inferred from unit numbers only)", "", "alv_t", "unconfirmed"),
 ("alv", "dogs_allowed", "yes, large dogs included", "Cats, small dogs, large dogs allowed", "alv_t", "confirmed"),
 ("alv", "dog_weight_limit", "no number given; page says large dogs allowed", "Large dogs allowed", "alv_t", "unconfirmed"),
 ("archer", "elevator", "yes (listing feature 'Elevator'); 8 floors (Openigloo)", "8 floors", "arch_o", "confirmed"),
 ("archer", "floor", "5 for 5G, 6 for 6A (inferred from unit numbers only)", "", "arch_t", "unconfirmed"),
 ("archer", "dogs_allowed", "pet-friendly; dogs named only in the structured pet line", "Pet-friendly community", "arch_t", "confirmed"),
 ("archer", "dog_weight_limit", "not stated on listing or the building's site; page says small dogs", SMALL, "arch_t", "unconfirmed"),
 ("the88", "elevator", "yes (listing feature 'Elevator'); floor count not stated", "Elevator", "88_t", "confirmed"),
 ("the88", "floor", "6 (inferred from unit number 621 only)", "", "88_t", "unconfirmed"),
 ("the88", "dogs_allowed", "yes per structured pet line; building site lists a pet spa but no policy", "PET SPA", "88_site", "confirmed"),
 ("the88", "dog_weight_limit", "not stated on listing or the building's site; page says small dogs", SMALL, "88_t", "unconfirmed"),
]
rows = []
for g, fact, val, q, src, st in C:
    check(q, u_[src])
    for ak in G[g]:
        rows.append([ak, fact, val, q, u_[src], st])
with open(EV / "confirm_batch_4.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow("addr_key,fact,value,quote,source_url,status".split(",")); w.writerows(rows)
n_conf = len(rows)

# ---------------------------------------------------------------- items: (group, category, date, excerpt, site, src, about)
OG = "openigloo"
I = [
 ("elm", "management", "2025-04-04", "- Roaches - Prior roof leak", OG, "elm_o", "building"),
 ("elm", "positive", "2025-04-04", "- Respectful neighbors - Strong heat - Effective garbage management", OG, "elm_o", "building"),
 ("elm", "management", "2021-11-16", "Cockroach infested. Dirty basement. Smelly lobby.", OG, "elm_o", "building"),
 ("elm", "elevator", "2021-11-16", "Elevator is outdated. When it rains, water leaks inside the elevator.", OG, "elm_o", "building"),
 ("elm", "safety_incident", "2021-11-16", "Packages gets stolen in the lobby.", OG, "elm_o", "building"),
 ("flat", "positive", "2025-07-26", "The super is very responsive and pleasant. My apartment is always quiet.", OG, "flat_o", "building"),
 ("flat", "other", "2025-07-26", "I don't like that there's never a time when all of the washers and dryers are working.", OG, "flat_o", "building"),
 ("flat", "positive", "2025-07-26", "Very clean and quiet", OG, "flat_o", "building"),
 ("flat", "noise", "2025-05-20", "Neighbors were a little loud", OG, "flat_o", "building"),
 ("rose", "positive", "2024-02-18", "They always clean it and take care of the garbage", OG, "rose_o", "building"),
 ("rose", "other", "2024-02-18", "The parking fees", OG, "rose_o", "garage_or_lot"),
 ("benn", "management", "2024-08-13", "Violations being ignored, harassment from management, roach infestation, unfair evictions", OG, "benn_o", "building"),
 ("benn", "management", "2024-02-10", "This apt building did not have working gas for the first four months I lived here.", OG, "benn_o", "building"),
 ("sanf133", "safety_incident", "2021-11-16", "tons of teenagers (who don't even live in the building) who smoke pot and other drugs (once saw a crack pipe) in the stairway and roof.", OG, "s133_o", "building"),
 ("sanf133", "management", "2021-11-16", "There's no security and the owner and his staff are aggressive and unresponsive", OG, "s133_o", "building"),
 ("nmt", "management", "2024-03-29", "Pest control is bad", OG, "nmt_o", "building"),
 ("nmt", "noise", "2024-03-29", "many incidents of neighbors disturbing others with noise level and landlord doesn't do anything after many emails", OG, "nmt_o", "building"),
 ("nmt", "management", "2023-12-17", "Roaches everywhere with exterminators coming once in a blue moon", OG, "nmt_o", "building"),
 ("maple", "other", "2021-11-16", "Expensive monthly maintenance cost", OG, "maple_o", "building"),
 ("41st", "management", "2025-04-22", "Pests pests pests. Saw a flying roach three days into move in.", OG, "41_o", "building"),
 ("41st", "positive", "2025-04-22", "Location is great. Elevator building. Quiet neighborhood.", OG, "41_o", "building"),
 ("barc", "management", "2024-01-08", "Rats, roaches so many roaches.", OG, "barc_o", "building"),
 ("barc", "elevator", "2024-01-08", "elevator sometimes breaks", OG, "barc_o", "building"),
 ("13955", "elevator", "2026-02-06", "The elevator is constantly getting stuck and hasn't been inspected in a year.", OG, "13955_o", "building"),
 ("13955", "management", "2026-02-06", "Pests are a HUGE issue in the building.", OG, "13955_o", "building"),
 ("13955", "management", "2026-02-06", "Heat is inconsistent and water is brown and rust colored at times.", OG, "13955_o", "building"),
 ("13955", "safety_incident", "2026-02-06", "Package theft has been an issue in the building as well.", OG, "13955_o", "building"),
 ("13955", "noise", "2026-02-06", "Neighbors are constantly fighting and building management does nothing even when residents are in clear violation of the lease.", OG, "13955_o", "building"),
 ("13955", "positive", "2026-02-06", "Units are pretty spacious and have lots of closet space.", OG, "13955_o", "building"),
 ("9876", "management", "2023-05-18", "First off, the building is infested with ROACHES BIG AND SMALL.", OG, "9876_o", "building"),
 ("9876", "management", "2023-05-18", "it took me calling 311 to find out I have chipping lead paint on my door.", OG, "9876_o", "management_company"),
 ("10910", "positive", "2025-06-30", "The staff was very friendly and for the most part attentive to all.", OG, "10910_o", "building"),
 ("10910", "positive", "2023-12-15", "The super is very responsive and will help you with almost anything needed.", OG, "10910_o", "building"),
 ("10910", "management", "2023-12-15", "They can be a bit stingy with the heat", OG, "10910_o", "building"),
 ("10910", "management", "2023-02-17", "Cockroaches, even tho I keep my apartment very clean", OG, "10910_o", "building"),
 ("10910", "noise", "2023-02-17", "The walls are thin so that you can hear neighbors.", OG, "10910_o", "building"),
 ("10910", "positive", "2022-06-12", "Very friendly and welcoming staff and doormen. Pet friendly.", OG, "10910_o", "building"),
 ("10910", "management", "2021-11-16", "Issues with heat and hot water. Some disrepair in the laundry room and elevator.", OG, "10910_o", "building"),
 ("6360", "management", "2021-11-16", "I would ended up with a completely flooded bathroom with giant roaches flying around.", OG, "6360_o", "building"),
 ("w131", "elevator", "2022-04-03", "Elevator broken for over 3 weeks.", OG, "w131_o", "building"),
 ("w131", "management", "2022-04-03", "Hot water rarely works and every time they fix it the water pressure decreases.", OG, "w131_o", "building"),
 ("w131", "safety_incident", "2022-04-03", "Neighborhood is awful - shooting every other day.", OG, "w131_o", "street"),
 ("lmv", "elevator", "2025-12-18", "Tenants explained that the building's only two elevators were out of service for more than six months, forcing some elderly residents to walk up multiple flights of stairs and causing stress injuries.", "queensledger.com", "lmv_ql", "building"),
 ("lmv", "management", "2025-12-18", "She's one of more than 100 tenants who have joined a lawsuit against A&E seeking immediate correction to over 800 NYC Housing Preservation Department (HPD) violations across La Mesa Verde's six buildings", "queensledger.com", "lmv_ql", "management_company"),
 ("lmv", "elevator", "2025-12-18", "Management sent a repair crew to fix one of the elevators last month, while the other remains out of order.", "queensledger.com", "lmv_ql", "building"),
 ("lmv", "management", "2026-02-24", "building owner A&E make immediate repairs, with several residents alleging that they have been without heat for over a month.", "politicsny.com", "lmv_pny", "management_company"),
 ("lmv", "elevator", "2026-02-24", "Mesa Verde tenants also complained of persistent leaks and rat, roach and mold infestations during the Feb. 22 rally, while others called on A&E to restore service to elevators in the complex.", "politicsny.com", "lmv_pny", "building"),
 ("lmv", "management", "2025-03-16", "- Roaches very heavily infested - Mice in the walls", OG, "lmv_o1", "building"),
 ("lmv", "elevator", "2025-03-16", "- Elevator only in 2 of the buildings and have to cross the roof to get to", OG, "lmv_o1", "building"),
 ("lmv", "positive", "2025-03-16", "- No broker fee and reasonable rent - Renovated kitchen, bathroom, incl dishwasher", OG, "lmv_o1", "building"),
 ("lmv", "elevator", "2022-11-11", "Not every building has elevators so some are walk ups, lots of rats", OG, "lmv_o2", "building"),
 ("lmv", "management", "2022-06-02", "Staircase is falling apart. Literally a hazard to walk on and it's a walk up apartment.", OG, "lmv_o3", "building"),
 ("lmv", "management", "2024-03-22", "The building was old and maintained bad", OG, "lmv_o4", "building"),
 ("alv", "positive", "2025-12-01", "The super was so sweet, and i liked the door men.", OG, "alv_o", "building"),
 ("alv", "safety_incident", "2025-12-01", "There is a bunch of criminal in the surrounding area and the lobby area gets kinda packed at night.", OG, "alv_o", "street"),
 ("alv", "management", "2025-12-01", "it sucks that they make you pay extra for amenity acess", OG, "alv_o", "building"),
 ("archer", "management", "2022-09-26", "REZI is responsive only until lease is signed. Once you move in and have an issue to point it to another company called AKAM who's manager never responds.", OG, "arch_o", "management_company"),
 ("archer", "positive", "2025-01-31", "- Incredibly clean - No bugs or rodents - Super is very fast about responding", OG, "arch_o2", "building"),
 ("archer", "other", "2025-01-31", "- Washer/Dryers are often broken, but hasn't been too big of a problem for me.", OG, "arch_o2", "building"),
 ("the88", "management", "2026-07-24", "Fishy fees, utility shams and constant power outages.", OG, "88_o", "building"),
 ("the88", "positive", "2026-07-24", "Clean lobby at all times, good concierge", OG, "88_o", "building"),
 ("the88", "management", "2025-08-06", "for repeatedly violating rent stabilization laws and overcharging rent-stabilized tenants in Jamaica and Elmhurst, Queens.", "ag.ny.gov", "zara_ag", "management_company"),
]
# 3310/3320 Avenue H share the tax lot with 3420 but are separate co-op buildings under other managers: logged in the notes, not as items.
NONE = {  # group -> where we looked
 "clar": "Trulia listing page (no reviews section); Openigloo reviewed-buildings sitemap (BBL 3051650059 not present); web search for the address + tenants/police/fire",
 "aveh": "Trulia listing page; Openigloo has no reviewed page for 3420 Avenue H itself (same tax lot lists 3310 and 3320 Avenue H, different co-op buildings); web search for the address",
 "37th": "Trulia listing page; Openigloo reviewed-buildings sitemap (BBL 4050117504 not present)",
 "bowne": "Trulia listing page; Openigloo reviewed-buildings sitemap (BBL 4050460020 not present)",
 "sanf143": "Trulia listing page; Openigloo reviewed-buildings sitemap (BBL 4050490038 not present)",
 "galaxy": "Zumper listing page (reviews block empty); Openigloo reviewed-buildings sitemap (BBL 4030997501 not present)",
 "carr": "Apartment List property page (no reviews in page data); livecarraway.com; Openigloo does not cover Westchester; web search",
 "front": "Apartment List and Zumper pages (reviews blocks empty); web search for '479 Front Street' + police/fire/shooting (results were other Front Street addresses)",
}
rows = []
for g, cat, d, ex, site, src, about in I:
    ts = check(ex, u_[src])
    for ak in G[g]:
        r0 = next(r for r in BATCH if r["addr_key"] == ak)
        rows.append([ak, NAME.get(g) or r0["building_name"], cat, d, ex, site, u_[src], about, ts])
for g, where in NONE.items():
    for ak in G[g]:
        r0 = next(r for r in BATCH if r["addr_key"] == ak)
        rows.append([ak, NAME.get(g) or r0["building_name"], "none_found", "", "looked at: " + where, "", "", "building", lib.now_iso()[:10]])
with open(EV / "items_batch_4.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow("addr_key,building_name,category,item_date,excerpt,source_site,source_url,about,retrieved_at".split(",")); w.writerows(rows)
n_items = len(rows)

# ---------------------------------------------------------------- facts: (group, fact, value, quote, src)
F = [
 ("elm", "year_built", "1940", "Built in 1940", "elm_o"), ("elm", "units", "60", "60 units", "elm_o"), ("elm", "management_company", "85-05 Elmhurst LLC (owner entity per Openigloo); listing broker Gugenheim Realty LLC", "managed by 85-05 Elmhurst LLC", "elm_o"),
 ("flat", "building_floors", "13", "Rising proudly across 13 floors", "flat_t"), ("flat", "management_company", "owner entity 1640 Flatbush Oz Jv LLC; leasing by Rentopia", "managed by 1640 Flatbush Oz Jv LLC", "flat_o"),
 ("flat", "amenities", "rooftop, fitness center, bike storage, package room, laundry room (no pool listed)", "Laundry Room: Modern laundry facilities for hassle-free laundering.", "flat_t"),
 ("aveh", "laundry", "in building; 24/7 super", "24/7 super on site", "aveh_t"),
 ("rose", "year_built", "1972", "Built in 1972", "rose_o"), ("rose", "units", "103", "103 units", "rose_o"), ("rose", "utilities_included", "heat, water, cooking gas", "Heat, water, and cooking gas are included.", "rose_t"),
 ("rose", "parking", "on-site spaces available; fee not stated (a tenant review complains about 'The parking fees')", "parking spaces available", "rose_t"), ("rose", "rent_regulation", "rent stabilized", "Rent stabilized 1 bedroom apartment", "rose_t"),
 ("benn", "year_built", "1985", "Built in 1985", "benn_o"), ("benn", "units", "151", "151 units", "benn_o"), ("benn", "management_company", "The Bennington, LLC (owner entity per Openigloo)", "managed by The Bennington, LLC", "benn_o"),
 ("benn", "parking", "indoor garage available; fee not stated", "indoor garage available", "benn_t"), ("benn", "utilities_included", "heat, water, cooking gas", "Heat, water, and cooking gas are included.", "benn_t"),
 ("sanf133", "year_built", "1963", "Built in 1963", "s133_o"), ("sanf133", "units", "146", "146 units", "s133_o"), ("sanf133", "management_company", "Fortune Plaza LLC (owner entity per Openigloo)", "managed by Fortune Plaza LLC", "s133_o"),
 ("37th", "parking", "garage (Trulia feature says valet); fee not stated", "Garage parking/ 24 hour doorman/ gym/ Landry in the building.", "37_t"), ("37th", "doorman", "24-hour doorman", "Garage parking/ 24 hour doorman/ gym/ Landry in the building.", "37_t"),
 ("37th", "required_fees", "one-time: $300 building application fee + $150 background check", "Tenants pays $300 building application fee and $150 background check.", "37_t"),
 ("nmt", "year_built", "2000", "built in 2000", "nmt_o"), ("nmt", "units", "71", "71-unit", "nmt_o"), ("nmt", "management_company", "Ciampa Management Corp.", "managed by Ciampa Management Corp.", "nmt_o"),
 ("nmt", "utilities_included", "heat and cooking gas", "Heat and cooking gas are included.", "nmt_t"), ("nmt", "parking", "on-site spaces available; fee not stated", "parking spaces available", "nmt_t"),
 ("maple", "year_built", "1973 (Openigloo); Trulia says 1974", "Built in 1973", "maple_o"), ("maple", "units", "52", "52 units", "maple_o"), ("maple", "management_company", "Briarwood At Maple Tenants Corp. (co-op)", "managed by Briarwood At Maple Tenants Corp.", "maple_o"),
 ("maple", "parking", "street only per listing features", "", "maple_t"),
 ("41st", "year_built", "1968", "Built in 1968", "41_o"), ("41st", "units", "42", "42 units", "41_o"), ("41st", "management_company", "Nhe Management Assoc., LLC", "Managed by Nhe Management Assoc., LLC", "41_o"),
 ("barc", "year_built", "1962", "Built in 1962", "barc_o"), ("barc", "units", "50", "50 units", "barc_o"), ("barc", "management_company", "200 Sunrise Associates, LLC (owner entity per Openigloo)", "managed by 200 Sunrise Associates, LLC", "barc_o"),
 ("13955", "year_built", "1967", "Built in 1967", "13955_o"), ("13955", "units", "90", "90 units", "13955_o"), ("13955", "management_company", "139-55 35Th Realty LLC (owner entity per Openigloo)", "managed by 139-55 35Th Realty LLC", "13955_o"),
 ("9876", "year_built", "1939", "Built in 1939", "9876_o"), ("9876", "units", "66", "66 units", "9876_o"), ("9876", "management_company", "98-76 Queens Blvd. Condo; a 2023 tenant review names Leemar Management", "Managed by 98-76 Queens Blvd. Condo", "9876_o"),
 ("galaxy", "parking", "garage parking listed as a building amenity; fee not stated", "", "gal_z"), ("galaxy", "move_in_fee", "$3,400 'Moveinfee' in page data, not marked required", "", "gal_z"),
 ("10910", "year_built", "1959", "Built in 1959", "10910_o"), ("10910", "units", "121", "121 units", "10910_o"), ("10910", "management_company", "109-10 Queens Blvd LLC (owner entity per Openigloo)", "Managed by 109-10 Queens Blvd LLC", "10910_o"),
 ("10910", "parking", "garage in building, for rent; fee not stated", "parking garage in the building for rent", "10910_t"), ("10910", "doorman", "tenant reviews mention doormen; listing mentions super and porter", "Very friendly and welcoming staff and doormen.", "10910_o"),
 ("10910", "utilities_included", "heat, water, gas", "Includes heat , water and gas", "10910_t"),
 ("6360", "year_built", "1949", "Built in 1949", "6360_o"), ("6360", "units", "139", "139 units", "6360_o"), ("6360", "management_company", "New Hampshire House Condominium", "Managed by New Hampshire House Condominium", "6360_o"),
 ("6360", "required_fees", "one-time: $20 application fee per person", "Total Required Fees: $20 Application Fee Per Person + 1st Month Rent + 1 Month Security Deposit", "6360_t"),
 ("w131", "year_built", "1972", "built in 1972", "w131_o"), ("w131", "units", "44", "44-unit", "w131_o"), ("w131", "management_company", "273 W 131, LLC (owner entity per Openigloo); listing by Bruma Realty LLC", "managed by 273 W 131, LLC", "w131_o"),
 ("carr", "management_company", "Bozzuto (resident portal and footer links on the building's site); stored record says Toll Brothers", "", "carr_fp"),
 ("carr", "required_monthly_fees", "$147.14: amenity fee $70 + utility admin billing $7.14 + required internet $50 + trash $20; water, sewer, stormwater usage-based; electric third party", "Amenity Fee – Monthly $70.00 Monthly required", "carr_fp"),
 ("carr", "pet_rent", "$50/month", "Pet Rent $50.00 Monthly optional", "carr_fp"),
 ("carr", "parking", "garage; unreserved $125/month", "Parking – Unreserved $125.00 Monthly optional", "carr_fp"),
 ("carr", "security_deposit", "$750 standard", "Security Deposit – Standard $750.00 One Time required", "carr_fp"),
 ("carr", "pool", "pool listed in Apartment List amenities; building site mentions cabanas (indoor/outdoor not stated)", "", "carr_am"),
 ("carr", "concession", "1.5 months free base rent advertised (restrictions apply)", "Receive 1.5 Months Free Base Rent*", "carr_fp"),
 ("carr", "year_built", "2021 (Apartment List page data)", "", "carr_a"),
 ("front", "required_monthly_fees", "water, sewer, trash $30/month for a 1BR", "Water, sewer, and trash (WST): $30/month for a 1b", "front_z"),
 ("front", "pet_rent", "$50/month", "Pet fee: $50/month", "front_z"), ("front", "parking", "on-site, assigned; $75/month", "Parking: $75/month", "front_z"),
 ("front", "laundry", "in unit", "in-unit washers and dryers", "front_z"), ("front", "building_name", "Village Lofts", "Welcome to Village Lofts, a boutique rental community conveniently located at 479 Front Street in Hempstead.", "front_z"),
 ("lmv", "year_built", "1927", "Built in 1927", "lmv_o1"), ("lmv", "management_company", "A&E Real Estate Holdings, owner since 2016 (Queens Ledger, Dec 2025); listings are by OPGNY and say 'Now under new management' without a date", "Now under new management and undergoing a complete transformation to all apartments and the complex.", "lmv_h53"),
 ("lmv", "management_company", "A&E bought the complex in 2016", "A&E purchased La Mesa Verde in 2016 for $72,500,000 from a company called BRG Queens LLC.", "lmv_ql"),
 ("lmv", "utilities_included", "heat and hot water", "Heat and hot water included in the rent.", "lmv_h53"), ("lmv", "open_violations_note", "Openigloo counts 136 to 276 open violations per building page (public-records agent has the detail)", "276 open violations", "lmv_o3"),
 ("alv", "building_floors", "25", "The brand new, 25-story Alvista Rise rental property", "alv_t"), ("alv", "doorman", "24-hour doorman", "Alvista Rise is a 24-hour-doorman building with a secure package room", "alv_t"),
 ("alv", "concession", "2.5 months free on an 18-month lease; listed prices are net-effective; gross rents $2,800 (2410) and $2,825 (1922)", "We are offering 2.5 months free on an 18-month lease on each unit.", "alv_t"),
 ("alv", "parking", "parking garage; fee not stated", "Parking Garage", "alv_t"), ("alv", "required_fees", "$20 application fee per applicant; electricity paid by tenant", "Application fee of $20 per each Applicant", "alv_t"),
 ("alv", "management_company", "Heller Organization (listing); Openigloo names Grenadier Realty Management", "this building is managed by Grenadier Realty Management", "alv_o"),
 ("alv", "amenity_fee", "a Dec 2025 tenant review says amenity access costs extra; amount not stated", "it sucks that they make you pay extra for amenity acess", "alv_o"),
 ("archer", "year_built", "2020", "Built in 2020", "arch_o"), ("archer", "units", "109", "a luxury boutique 109-unit development", "arch_t"),
 ("archer", "management_company", "Andover Property Management now (listing and building site); a Sept 2022 review names REZI and AKAM, and Openigloo still lists Akam Associates. Date of the change not found", "Managed by Akam Associates, INC", "arch_o"),
 ("archer", "amenity_fee", "none", "(Offering no Amenity fees!)", "arch_t"), ("archer", "parking", "garage on site; fee not stated", "Garage parking", "arch_site"),
 ("archer", "required_fees", "$20 application fee per leaseholder/guarantor", "Application Fee: $20 per leaseholder/guarantor", "arch_t"),
 ("the88", "management_company", "Zara Realty (application@zararealty.com on the building's site; © The 88 LLC)", "application@zararealty.com", "88_site"),
 ("the88", "parking", "indoor garage; additional fee, amount not stated", "INDOOR PARKING*", "88_site"), ("the88", "doorman", "24-hour attended lobby", "24-hour attended lobby", "88_site"),
 ("the88", "laundry", "laundry room, additional fees may apply (not in unit)", "LAUNDRY ROOM*", "88_site"), ("the88", "pool", "none listed", "", "88_site"),
]
rows = []
for g, fact, val, q, src in F:
    check(q, u_[src])
    for ak in G[g]:
        rows.append([ak, fact, val, q, u_[src]])
with open(EV / "facts_batch_4.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow("addr_key,fact,value,quote,source_url".split(",")); w.writerows(rows)
print("live", len(live_rows), "confirm", n_conf, "items", n_items, "facts", len(rows))
print("QUOTES NOT FOUND VERBATIM:", len(BAD))
for b in BAD: print("  ", b)
