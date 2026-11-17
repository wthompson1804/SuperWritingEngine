"""Live check batch 21: re-read of the 45 apartments at or under $2,000 listed rent (the concierge page), from each
building's own site, its manager's site, or an allowed listing site. No Trulia requests.

  python3 scripts/live_check_batch_21.py get <url> [<url> ...]   fetch (cached, robots-checked, 3 s apart) and print a summary
  python3 scripts/live_check_batch_21.py text <url>              print the cached page as plain text
  python3 scripts/live_check_batch_21.py write                   rebuild data/evidence/live_check_batch_21.csv (no network)

Every response is cached in raw/live_check_b21/. A 401, 403, 429 or bot wall is written to raw/_host_kill_shared.json
and the host is never asked again. Three pages that fill their unit list by script (333statestreet.com, brt.com,
beaconmillvillage.com, all the same AppFolio listing widget) were opened once each with scripts/h_mgmt_render.js into
raw/live_check_b21/render/. FINDINGS below is what was read on each cached page; `write` joins it to the 45 units
(site/data.json, rent.listed <= 2000), to data/reference/building_crosswalk.csv and to the cache's retrieval times.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

SRC = "live_check_b21"
BY = "live_check_batch_21"
KILL = lib.RAW / lib.KILL_FILE_NAME
DELAY = 3.0
UA_NAMES = ["Claude-User", "ClaudeBot", "anthropic-ai", "Claude-Web", "claude"]
_last: dict[str, float] = {}
_robots: dict[str, object] = {}
WALL = re.compile(r"captcha|are you a human|attention required|access denied|just a moment\.\.\.|px-captcha|incapsula incident|"
                  r"request unsuccessful|verify you are human|unusual traffic", re.I)


def kill(host: str, reason: str, url: str) -> None:
    try:
        k = json.loads(KILL.read_text())
    except (OSError, ValueError):
        k = {}
    if host not in k:
        k[host] = {"reason": reason, "url": url, "at": lib.now_iso(), "by": BY}
        KILL.write_text(json.dumps(k, indent=1))


def _wait(host: str) -> None:
    w = _last.get(host, 0) + DELAY - time.time()
    if w > 0:
        time.sleep(w)
    _last[host] = time.time()


def _raw(url: str, ext: str):
    """One request, no retry. Returns (content or None, status text)."""
    host = urlparse(url).netloc
    try:
        lib.check_host(url)
    except lib.HostRefused as e:
        return None, f"not requested: {e}"
    cached = True
    try:
        # cache hit returns at once; otherwise one try only (a 429 must not be retried)
        key_exists = None
        _wait(host)
        content, meta = lib.cached_get(url, SRC, ext=ext, retries=1, timeout=45,
                                       headers={"Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"})
    except RuntimeError as e:
        m = re.search(r"HTTP (\d+)", str(e))
        if m and m.group(1) == "429":
            kill(host, "HTTP 429", url)
            return None, "HTTP 429 (host ended)"
        return None, f"fetch failed: {str(e)[-200:]}"
    st = meta["status"]
    if st in (401, 403, 429):
        kill(host, f"HTTP {st}", url)
        return None, f"HTTP {st} (host ended)"
    if st != 200:
        return None, f"HTTP {st}"
    head = content[:6000].decode("utf-8", "replace")
    if len(content) < 20000 and WALL.search(head):
        kill(host, "bot wall page served (HTTP 200)", url)
        return None, "bot wall (host ended)"
    return content, f"200 at {meta['retrieved_at']}"


def robots_ok(url: str):
    p = urlparse(url)
    host = p.netloc
    if host not in _robots:
        body, st = _raw(f"{p.scheme}://{host}/robots.txt", "txt")
        if body is None:
            _robots[host] = st if "ended" in st or "not requested" in st else None  # no robots file: allowed
        else:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(body.decode("utf-8", "replace").splitlines())
            _robots[host] = rp
    r = _robots[host]
    if r is None:
        return True, "no robots.txt"
    if isinstance(r, str):
        return False, f"robots.txt: {r}"
    txt = (lib.RAW / SRC).exists() and ""  # noqa
    # a group naming Claude overrides *: RobotFileParser picks the first matching named entry, else *
    named = [e for e in r.entries if any(any(n.lower() in a.lower() for n in UA_NAMES) for a in e.useragents)]
    ua = "Claude-User" if any("claude-user" in a.lower() for e in named for a in e.useragents) else ("ClaudeBot" if named else "house-hunt-research")
    return r.can_fetch(ua, url), f"robots group used: {ua if named else '*'}"


def get(url: str, ext: str = "html"):
    ok, why = robots_ok(url)
    if not ok:
        return None, f"robots disallow ({why})"
    return _raw(url, ext)


def to_text(content: bytes) -> str:
    s = content.decode("utf-8", "replace")
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|td|th|section|article)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    import html
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


COLS = ["addr_key", "listing_url", "unit", "status", "price_now", "available_now_text", "matches_stored", "building_site_url", "checked_at", "notes"]
TRULIA = "Stored price and availability were read on Trulia on 2026-11-15; Trulia was not asked again."
GH = "https://gardenhomesmanagement.com/Property?pid="
AL = "https://www.apartmentlist.com/"
NO_DATE = "listed on the manager's availability page (no date given: treated as available now)"


def gh(pid, unit, price, extra=""):
    return dict(status="live", price=price, avail=NO_DATE, site=GH + str(pid), read=GH + str(pid),
                note=f"Manager's own site (Garden Homes Management) re-read 2026-11-17: Apt #{unit} is on the building's availability list at ${price:,}, the same price as stored. The page gives no move-in date.{extra}")


BEACON = ("The building's own availability page (beaconmillvillage.com/availability, the leasing office's AppFolio listing feed; 10 apartments listed, the newest posted "
          "2026-11-16) does not list {u}. What it lists today: PA-107 studio $1,545; PA-212, SH-108, SH-309 and SH-408 one-bedrooms $1,795; PA-218 one-bedroom $1,895; "
          "PA-315 one-bedroom $2,195; two-bedrooms VH-156 $2,250, BX-172 $2,495, BX-168 $2,650. None of those is in our data. " + TRULIA)
CITYTRUST = ("Not re-read: no page names this apartment. The building has no site of its own. Felner Corporation's listing board (felnercorptei.appfolio.com/listings, read "
             "2026-11-17) has one entry for 955 Main Street with no apartment number: 1 bed, 751 sqft, $1,675, 'Available Now' (its offer text is a June special). Zumper's "
             "building page carries the same single unlabelled 1-bedroom at $1,675, 'updated 5+ days ago'. Neither can be matched to apartment {u} (stored: {d}). "
             "RentCafe is off limits. " + TRULIA)
WHIT = ("Manager's own listing board (Franklin Communities, franklin.appfolio.com/listings, the board embedded on the building's page) re-read 2026-11-17: "
        "2405 Whitney Avenue, {u}: 1 bd / 1 ba, {sq} sqft, rent ${p:,}, available {a}. Stored price was ${old:,} (read on Trulia 2026-11-15): the manager's price is ${diff} lower. "
        "Trulia was not asked again.")
SINGLE = "Not re-read: single-apartment listing seen only on Trulia (not asked again). "

FINDINGS = {
    # Beacon Mill Village
    "b_8cb8bf6346": {u: dict(status="gone", avail="not on the building's own availability list", site="https://www.beaconmillvillage.com/availability",
                             read="render:beaconmill_availability", note=BEACON.format(u=u)) for u in ["PA-405", "PA-202", "PA-402", "BM-322", "PU-242"]},
    # City Trust Apartments, 955 Main St
    "b_917f6a1ed1": {u: dict(status="not_read", site="", read="https://felnercorptei.appfolio.com/listings", note=CITYTRUST.format(u=u, d=d)) for u, d in [
        ("606", "1 bed, 751 sqft, $1,650"), ("511", "studio, 491 sqft, $1,400"), ("611", "studio, 491 sqft, $1,400"), ("711", "studio, 491 sqft, $1,400"),
        ("Duplex701", "1 bed, 712 sqft, $1,850"), ("302", "1 bed, 745 sqft, $1,650"), ("402", "1 bed, 614 sqft, $1,650"), ("702", "1 bed, 614 sqft, $1,650")]},
    # City Trust Collection: Arcade, 991 Main St
    "b_b29a9ae0e3": {"302": dict(status="live", price=1675, avail="available now (manager's board: 'Available Now')", site="https://felnercorptei.appfolio.com/listings",
                                 read="https://felnercorptei.appfolio.com/listings",
                                 note="Read on two pages 2026-11-17. Manager's own listing board (Felner Corporation, felnercorptei.appfolio.com/listings): '991 Main Street, Unit 302', 1 bd / 1 ba, "
                                      "751 sqft, $1,675, Available Now; pet policy there: 'Cats allowed, Small dogs allowed'. Apartment List building page (availability last checked by the site "
                                      "2026-11-17): unit 302, 751 sqft, available, $1,675 base rent, 12-month lease. Same price as stored.")},
    # Soundview, 855 Main St
    "b_0e634d994b": {"855-1015": dict(status="changed", price=1900, avail="available now (available_on 2026-11-17)", site="", read=AL + "ct/bridgeport/soundview",
                                      note="Apartment List building page re-read 2026-11-17 (availability last checked by the site 2026-11-17; unit record updated 2026-11-17): unit 855-1015, "
                                           "plan SV15, studio, 330 sqft, available, $1,900 base rent, 12-month lease. Stored price was $1,950 (read on Trulia 2026-11-15): $50 lower now. "
                                           "No site of the building's own is known; Trulia was not asked again.")},
    # 333 State St
    "b_5f84c933a2": {"604": dict(status="not_read", site="https://www.333statestreet.com/available-rentals", read="render:333state_available",
                                 note="Not confirmed. The building's own 'Available Rentals' page (333statestreet.com/available-rentals, an AppFolio listing feed) answered normally on 2026-11-17 "
                                      "and shows 'No results found': no apartment is offered there today, 604 included. Whether the feed is kept up to date is not known (the site footer is dated 2022). "
                                      "Zumper's building page ('updated 5+ days ago') still gives $1,850 to $2,350 for 1 to 2 beds, 745 to 1,090 sqft, with no apartment numbers. "
                                      "Ask the office (LYP Management) whether 604 is still free. " + TRULIA)},
    # Brookview Commons II (West), 333 Main St
    "b_5204934871": {"BC-519W": dict(status="live", price=1975, avail="available now (available_date 2026-10-08)", site="https://www.brt.com/vacancies", read="render:brt_vacancies",
                                     note="Manager's own vacancies page (BRT General, brt.com/vacancies, AppFolio listing feed, 22 listings) read 2026-11-17: '333 Main Street, Unit 519', studio, 600 sqft, "
                                          "rent $1,975, shown as 'TOTAL MONTHLY PRICE $2,025' because a mandatory $50 a month amenity fee is added; available since 2026-10-08; 'Small dogs allowed'. "
                                          "Same base rent as stored.")},
    # Brookview Commons East, 30 Crosby St
    "b_e2378bf884": {"BC-524": dict(status="live", price=1925, avail="available 2026-11-26", site="https://www.brt.com/vacancies", read="render:brt_vacancies",
                                    note="Manager's own vacancies page (BRT General, brt.com/vacancies, AppFolio listing feed) read 2026-11-17: '30 Crosby Street, Unit 524', 1 bed, 675 sqft, rent $1,925, "
                                         "shown as 'TOTAL MONTHLY PRICE $1,975' with the mandatory $50 a month amenity fee; available 11/26/2026; 'Small dogs allowed'. Same base rent and date as stored."),
                     "BC-406": dict(status="live", price=1925, avail="available 2026-12-15", site="https://www.brt.com/vacancies", read="render:brt_vacancies",
                                    note="Manager's own vacancies page (BRT General, brt.com/vacancies, AppFolio listing feed) read 2026-11-17: '30 Crosby Street, Unit 406', 1 bed, 675 sqft, rent $1,925, "
                                         "shown as 'TOTAL MONTHLY PRICE $1,975' with the mandatory $50 a month amenity fee; available 2026-12-15, the last day of the move-in window; "
                                         "'Small dogs allowed'. Same base rent and date as stored.")},
    # Whitney Towers
    "b_0ba5cc966d": {"306": dict(status="changed", price=1895, avail="available 2026-12-15", note=WHIT.format(u="306", sq=860, p=1895, a="12/15/26", old=1945, diff="$50")),
                     "409": dict(status="changed", price=1715, avail="available 2026-12-01", note=WHIT.format(u="409", sq=730, p=1715, a="12/1/26", old=1865, diff="$150")),
                     "607": dict(status="changed", price=1725, avail="available 2026-12-15", note=WHIT.format(u="607", sq=730, p=1725, a="12/15/26", old=1875, diff="$150"))},
    # Garden Homes: Summer Street, The Stanley, 111 Prospect
    "b_893edb6df8": {"320": gh(103, "320", 1615, " The page gives 400 sqft for this apartment (stored: 350)."), "417": gh(103, "417", 1615)},
    "b_f95c86db48": {"504": gh(100, "504", 1935)},
    "b_377a717d0d": {"206": gh(110, "206", 1675), "306": gh(110, "306", 1675),
                     "511": dict(status="changed", price=1675, avail=NO_DATE, site=GH + "110", read=GH + "110",
                                 note="Manager's own site (Garden Homes Management) re-read 2026-11-17: Apt #511 is on the building's availability list at $1,675. Stored price was $1,715 "
                                      "(Trulia, 2026-11-15); the manager's page also showed $1,675 on 2026-11-16. The page gives no move-in date.")},
    # The Royce at Trumbull
    "b_8f7ec4f0f6": {"4211": dict(status="gone", avail="not in the unit list", site="https://www.royceattrumbull.com/floor-plans", read=AL + "ct/trumbull/the-royce-at-trumbull",
                                  note="Apartment List building page re-read 2026-11-17 (availability last checked by the site 2026-11-17): unit 4211 is no longer in the unit list. Its plan, "
                                       "The Dover (1 bed, 713 sqft), now lists 4302 at $2,080 base rent ($2,180 with $100 required monthly fees, from 2026-11-25) and 6103 at $2,220 ($2,320). "
                                       "The building's own floor-plan page (royceattrumbull.com/floor-plans, read the same day) agrees at plan level: The Dover, 2 units available, total monthly "
                                       "leasing price starting at $2,295; it names no apartment numbers. Nothing at this building is at or under $2,000 today. Stored: $2,000, seen live 2026-11-16.")},
    # Ethos Kelsey
    "b_66dc364565": {"301": dict(status="not_read", site="https://ethoskelsey.com/", read="https://ethoskelsey.com/floorplans",
                                 note="Not re-read: the building's own site (ethoskelsey.com) publishes floor plans and a waiting-list form but no apartment list and no prices; its "
                                      "'Availability' link answers 'not found' (404). Zumper has no page for the address (404). " + TRULIA)},
    # 64 Park Avenue
    "b_e39cde86f4": {"D10": dict(status="live", price=1910, avail="available now (available_on 2026-11-14)", site="", read=AL + "nj/bloomfield/64-park-avenue--1",
                                 note="Apartment List building page re-read 2026-11-17 (availability last checked by the site 2026-11-17; unit record updated 2026-11-17): unit D10, plan One Bedroom, "
                                      "564 sqft, available, $1,910 base rent, 12-month lease, no required monthly fees listed. Same price as stored. The manager's own site "
                                      "(goldberg-realty.com) refused us (HTTP 403) and was not asked again.")},
    # LIA by Vermella
    "b_022934bcb2": {"423": dict(status="live", price=1984, avail="available now (available_on 2026-10-27)", site="", read=AL + "nj/orange/lia-by-vermella",
                                 note="Apartment List building page re-read 2026-11-17 (availability last checked by the site 2026-11-17; unit record updated 2026-11-17): unit 423, plan S1, studio, "
                                      "500 sqft, available, $1,984 base rent. Price is for a 15-month lease; the page shows no 12-month price for this unit. Same price as stored. "
                                      "The building's own site (tours.liabyvermella.com) refused us (HTTP 403) and was not asked again.")},
    # Harclay House
    "b_296b3095f3": {u: dict(status="not_read", site="https://shamcomanagement.com/properties/new-jersey/south-harrison-property/",
                             read="https://shamcomanagement.com/properties/new-jersey/south-harrison-property/",
                             note=f"Not re-read: the manager's own page for the building (Shamco Management) gives no apartment list and no prices; its 'Rental Rates / More Info' button "
                                  f"leads to Apartments.com, which is off limits. Zumper's page for the address has a one-bedroom plan (912 sqft) with no price and 'Notify me', and no "
                                  f"apartment numbers, so it says nothing about {u}. " + TRULIA) for u in ["3CW", "5CE"]},
    # Symphony, 1009 Broad St
    "b_fec325fa9f": {u: dict(status="not_read", site="", read="https://www.zumper.com/address/1009-broad-st-newark-nj-07102-usa",
                             note=f"Not re-read: no site of the building's own was found. Zumper's page for the address carries one unlabelled 1-bedroom at $1,850 ('updated 5+ days ago'), "
                                  f"no studios and no apartment numbers, so it says nothing about studio {u}. " + TRULIA) for u in ["202E", "211E", "208E"]},
    # 1483 Shore Pkwy
    "b_674db3118a": {"F": dict(status="not_read", site="https://revonaproperties.com/properties/resident-services/shore-haven-apartments/",
                               read="https://revonaproperties.com/",
                               note=SINGLE + "The manager's site for the complex (Revona Properties, Shore Haven Apartments) has resident services only: no apartments for rent and no "
                                             "prices. Zumper has no page for the address (404).")},
    # 4110 Bowne St
    "b_d007846fe9": {"5W": dict(status="not_read", site="", read="",
                                note=SINGLE + "No site was found for the building or for the listing broker (Dan T Gulino Group Realty); Zumper has no page for the address (404). "
                                              "Nothing was requested for this apartment today beyond that Zumper address.")},
    # 13324 Sanford Ave
    "b_0f0fcfc79c": {"2D": dict(status="not_read", site="", read="https://www.zumper.com/address/133-24-sanford-ave-flushing-ny-11355-usa",
                                note=SINGLE + "No site of the building's own is known. Zumper's pages for this address are about other apartments (5J, a studio no longer offered; 6G, a "
                                              "1-bedroom at $2,450, updated today) and say nothing about 2D.")},
    # 84-18 143rd St
    "b_0c3a7051d4": {"3L": dict(status="gone", avail="not on the listing broker's own site", site="https://tribro.realtymx.com/", read="tribro",
                                note="The listing broker's own site (TriBro NYC, tribro.realtymx.com) was read 2026-11-17 with every rental the company has on offer (196 listings in one list): "
                                     "none is at 84-18 143rd St and none is in Jamaica, Briarwood or Kew Gardens. The apartment is judged no longer offered because it is absent from the "
                                     "broker's list; no page says in words that it was rented. Stored: $1,895, read on Trulia 2026-11-15; Trulia was not asked again.")},
    # 3625 Parsons Blvd
    "b_1d1be12629": {"5H": dict(status="live", price=1930, avail="on the broker's site as an active rental (no date given)",
                                site="https://www.hillelrealtygroup.com/flushing/apartment-for-rent/parsons-blvd/559771",
                                read="https://www.hillelrealtygroup.com/flushing/apartment-for-rent/parsons-blvd/559771",
                                note="Matched by broker, street, size and price, not by apartment number. The listing broker's own site (Hillel Realty Group; all 418 of its rentals were listed) "
                                     "has one studio on Parsons Blvd, Flushing: Web ID 559771, 'Studio, 1 bath', $1,930, No Fee, elevator building, heat, hot water and gas included, "
                                     "'Rent Stabilized unit'. The page names the street but not the house number or the apartment, and gives no move-in date. Same price as stored ($1,930, "
                                     "read on Trulia 2026-11-15; Trulia was not asked again). Confirm by phone that this is 36-25 Parsons Blvd 5H.")},
    # 2781 Ocean Ave
    "b_84bbe8d99e": {"6E": dict(status="not_read", site="", read="https://www.zumper.com/address/2781-ocean-ave-brooklyn-ny-11229-usa",
                                note=SINGLE + "Listed by its owner; no site of the building's own. Zumper's page for the address is an old listing for #4K with no price, and says nothing "
                                              "about 6E. The stored move-in date was 2026-11-16.")},
    # Regency on Hudson
    "b_ee2549a834": {"606": dict(status="not_read", site="https://regencyhudson.com/floorplans/", read="https://regencyhudson.com/floorplans/",
                                 note="Not confirmed, and the building's own site points the other way. regencyhudson.com/floorplans (read 2026-11-17) lists floor plans, not apartments: "
                                      "480 sqft studios S1 and S21 at $2,195 and S8 at $2,250, each with 'Contact Us' and an availability count of 0; no plan shows an open apartment and no "
                                      "price on the site is under $2,195. Apartment 606 (studio, 480 sqft, stored at $1,995) is not named anywhere on the site. Ask the office whether 606 is "
                                      "free and at what rent. " + TRULIA)},
    # 525 Riverdale Ave
    "b_c4831201c1": {"5U": dict(status="not_read", site="", read="https://www.zumper.com/address/525-riverdale-ave-yonkers-ny-10705-usa",
                                note=SINGLE + "No site of the building's own was found. Zumper's address page for 525 Riverdale Ave lists other units (527 at $2,400, updated today, and 2F) "
                                              "but not 5U.")},
}
for _u, _f in FINDINGS["b_0ba5cc966d"].items():
    _f.update(site="https://www.liveatfranklin.com/our-communities/whitney-towers/", read="https://franklin.appfolio.com/listings")


def read_time(key: str) -> str:
    """Retrieval time (UTC) of the page a finding was read from, from the cache."""
    d = lib.RAW / SRC
    if key.startswith("render:"):
        return json.loads((d / "render" / (key[7:] + ".meta.json")).read_text())["retrieved_at"]
    best = ""
    for m in d.glob("*.meta.json"):
        meta = json.loads(m.read_text())
        if (key == "tribro" and "tribro.realtymx.com/?page=properties" in meta["url"]) or meta["url"] == key:
            best = max(best, meta["retrieved_at"])
    return best


def write() -> None:
    data = json.loads((lib.ROOT / "site" / "data.json").read_text())
    units = [u for u in data["units"] if (u.get("rent") or {}).get("listed") is not None and u["rent"]["listed"] <= 2000]
    xw = {}
    for r in csv.DictReader(open(lib.DATA / "reference" / "building_crosswalk.csv")):
        xw.setdefault(r["building_id"], r["addr_key"])  # first key of the building; every key maps to the same building
    rows, missing = [], []
    for u in units:
        f = FINDINGS.get(u["building_id"], {}).get(u["unit"])
        if not f:
            missing.append((u["building_id"], u["unit"]))
            continue
        stored = u["rent"]["listed"]
        t = read_time(f["read"]) if f.get("read") else ""
        rows.append({"addr_key": xw[u["building_id"]], "listing_url": u["links"]["listing"], "unit": u["unit"], "status": f["status"],
                     "price_now": f.get("price", ""), "available_now_text": f.get("avail", ""),
                     "matches_stored": {"live": "yes", "changed": "no", "gone": "no"}.get(f["status"], ""),
                     "building_site_url": f.get("site", ""), "checked_at": t or BOWNE_TIME, "notes": f["note"]})
        if f["status"] == "live":
            assert f["price"] == stored, (u["unit"], f["price"], stored)
    assert not missing, missing
    assert len(rows) == len({(r["addr_key"], r["unit"]) for r in rows}) == len(units)
    out = lib.DATA / "evidence" / "live_check_batch_21.csv"
    tmp = out.with_suffix(".tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(out)
    import collections
    print(len(rows), "rows ->", out, dict(collections.Counter(r["status"] for r in rows)))


BOWNE_TIME = "2026-11-17T14:02:55+00:00"  # 4110 Bowne St: the only request was Zumper's address page, which answered 404 (not cached)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "get":
        for u in sys.argv[2:]:
            c, st = get(u, "json" if "json" in u or "/api/" in u else "html")
            print(u, "->", st, "| bytes", len(c) if c else 0)
            if c:
                t = to_text(c)
                print("   title:", (re.search(r"(?is)<title[^>]*>(.*?)</title>", c.decode('utf-8', 'replace')) or [0, ""])[1].strip()[:120], "| text chars", len(t))
    elif cmd == "text":
        c, st = get(sys.argv[2])
        print(st)
        print(to_text(c) if c else "")
    elif cmd == "write":
        write()
    else:
        print(__doc__)
