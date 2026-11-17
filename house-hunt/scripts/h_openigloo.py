"""Openigloo (www.openigloo.com) listing harvest for Brooklyn and Long Island City: studios and 1BR at or under $2,200.

  python3 scripts/h_openigloo.py list     # walk /apartments/<area>/<beds>?page=N search pages (JSON-LD item lists)
  python3 scripts/h_openigloo.py detail   # open each unit page whose search price is <= $2,200
  python3 scripts/h_openigloo.py build    # write data/listings_raw/openigloo.csv from the cache (no network)
  python3 scripts/h_openigloo.py all

Access (probed 2026-11-17, docs/SOURCES.md "Trawl 2 new-source probe"): robots.txt has ClaudeBot and Claude-User groups
that allow everything except /api, /_nuxt, /internal and two /None paths; no crawl-delay. Terms of use (read
2026-11-17) have no clause on automated access; they bar copying or republishing the site's content, so only facts
(price, unit, dates, policies) are recorded, never descriptions or photos. 3.5 s between requests, honest user agent
(lib.cached_get), one try per URL, and any 401/403/429 or bot wall ends the host (raw/_host_kill_shared.json).
Price, date and facts come from the unit page itself; the search-page price only decides which unit pages to open.
"""
from __future__ import annotations

import csv
import html as htmlmod
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

SRC = "openigloo"
HOST = "www.openigloo.com"
BASE = f"https://{HOST}"
DELAY = 3.5
MAX_RENT = 2200
KILL = lib.RAW / lib.KILL_FILE_NAME
OUT = lib.DATA / "listings_raw" / "openigloo.csv"
CARDS = lib.RAW / SRC / "_cards.jsonl"
AREAS = [("brooklyn", "Brooklyn"), ("queens/long-island-city", "Long Island City")]
BEDS = [("studio", 0), ("1-bedroom", 1)]
DISALLOW = ("/api", "/_nuxt", "/internal", "/wp-admin", "/building/nyc/None", "/contact/nyc/None")
WALL = re.compile(r"captcha|are you a human|attention required|access denied|just a moment\.\.\.|px-captcha|"
                  r"verify you are human|unusual traffic|challenge-platform", re.I)
COLS = ["listing_id", "source_site", "url", "detail_level", "first_seen", "last_seen", "building_name", "address", "city",
        "state", "zip", "lat", "lon", "unit", "beds", "baths", "sqft", "listed_rent", "price_basis", "concession_text",
        "available_date_text", "available_date", "dogs", "dog_policy_text", "dog_weight_limit_lb", "elevator", "floor",
        "building_floors", "parking_type", "parking_fee", "pet_rent", "other_monthly_fees_json", "utilities_included",
        "laundry", "listing_type", "manager", "listing_age_days", "photo_url", "building_url", "raw_path", "notes"]
_last = [0.0]


class Stop(RuntimeError):
    pass


def kill(reason: str, url: str) -> None:
    try:
        k = json.loads(KILL.read_text())
    except (OSError, ValueError):
        k = {}
    if HOST not in k:
        k[HOST] = {"reason": reason, "url": url, "at": lib.now_iso(), "by": "scripts/h_openigloo.py"}
        KILL.write_text(json.dumps(k, indent=1))


def get(url: str) -> tuple[str | None, dict | None]:
    """Cached fetch, one try. Returns (text, meta) or (None, meta/None) on a non-200. Raises Stop on a refusal."""
    path = urlparse(url).path
    if any(path.startswith(d) for d in DISALLOW):
        return None, None
    lib.check_host(url)
    lib.HOST_DELAY[HOST] = DELAY
    try:
        content, meta = lib.cached_get(url, SRC, ext="html", retries=1, timeout=45,
                                       headers={"Accept": "text/html,application/xhtml+xml"})
    except RuntimeError as e:
        if "HTTP 429" in str(e):
            kill("HTTP 429", url)
            raise Stop(f"429 on {url}")
        print("  fetch failed:", str(e)[-150:])
        return None, None
    st = meta["status"]
    if st in (401, 403, 429):
        kill(f"HTTP {st}", url)
        raise Stop(f"HTTP {st} on {url}")
    if st != 200:
        return None, meta
    text = content.decode("utf-8", "replace")
    if len(content) < 30000 and WALL.search(text[:8000]):
        kill("bot wall page served (HTTP 200)", url)
        raise Stop(f"bot wall on {url}")
    return text, meta


def flight(text: str) -> str:
    out = []
    for c in re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', text, re.S):
        try:
            out.append(json.loads('"' + c + '"'))
        except ValueError:
            pass
    return "".join(out)


LISTING = re.compile(r'\{"listing":\{"id":"([0-9a-f-]{36})","slug":"([^"]+)","addressSlug":"([^"]+)","fullAddress":"([^"]+)",'
                     r'"numBedrooms":(\d+),"numBathrooms":([\d.]+)(?:(?!\{"listing":).)*?"activeListing":(\{[^{}]*\})', re.S)


def unit_url(slug: str, address_slug: str) -> str:
    return f"{BASE}/unit/nyc/{slug}/{address_slug}"


def cmd_list() -> None:
    """Search pages carry each card's listing object: gross rent (the listed rent), net rent (after a promotion,
    which is the JSON-LD "price"), promotion text, beds, baths. The JSON-LD url (/unit/brooklyn/<uuid>/...) 404s;
    the site's own links use /unit/nyc/<slug>/<addressSlug>."""
    CARDS.write_text("")
    with open(CARDS, "a") as f:
        for slug, area in AREAS:
            for bslug, beds in BEDS:
                page, pages = 1, 1
                while page <= pages:
                    url = f"{BASE}/apartments/{slug}/{bslug}" + (f"?page={page}" if page > 1 else "")
                    text, meta = get(url)
                    if text is None:
                        print("  no page", url, meta and meta.get("status"))
                        break
                    mx = [int(x) for x in re.findall(rf'/apartments/{re.escape(slug)}/{bslug}\?page=(\d+)', text)]
                    pages = max([pages] + mx)
                    n, ids = 0, set()
                    for m in LISTING.finditer(flight(text)):
                        if m.group(1) in ids:
                            continue
                        ids.add(m.group(1))
                        try:
                            al = json.loads(m.group(7))
                        except ValueError:
                            al = {}
                        rec = {"search": url, "seen_at": meta["retrieved_at"], "area": area, "id": m.group(1),
                               "url": unit_url(m.group(2), m.group(3)), "name": m.group(4), "beds": int(m.group(5)),
                               "baths": float(m.group(6)), "gross": al.get("grossRent"), "net": al.get("netRent"),
                               "promotion": al.get("promotion"), "future": al.get("isFutureListing")}
                        n += 1
                        f.write(json.dumps(rec) + "\n")
                    print(f"{area} {bslug} page {page}/{pages}: {n} cards")
                    if n == 0:
                        break
                    page += 1


def cards() -> dict:
    best = {}
    for line in CARDS.read_text().splitlines():
        r = json.loads(line)
        if r["beds"] not in (0, 1):
            continue
        best.setdefault(r["url"], r)
    return best


def cmd_detail() -> None:
    todo = [r for r in cards().values() if (r["gross"] or r["net"] or 10**6) <= MAX_RENT]
    print(len(todo), "unit pages at or under", MAX_RENT)
    for i, r in enumerate(todo):
        text, meta = get(r["url"])
        print(i + 1, r["gross"], r["name"], "ok" if text else (meta or {}).get("status"))


# ---- unit page parsing ------------------------------------------------------------------------------------------------

FLOOR_WORDS = {"ground": 1, "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
               "eighth": 8, "ninth": 9, "tenth": 10}
FLOOR_RX = re.compile(r"\b(ground|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d{1,2})(?:st|nd|rd|th)?"
                      r"[- ]floor\b|\bfloor[: ]+(\d{1,2})\b", re.I)


def listing_obj(text: str, uid: str) -> dict | None:
    fl = flight(text)
    i = fl.find('{"listing":{"id":"' + uid)
    if i < 0:
        return None
    try:
        return json.JSONDecoder().raw_decode(fl, i)[0]["listing"]
    except (ValueError, KeyError):
        return None


def _plain(desc: str) -> str:
    t = re.sub(r"(?i)<br\s*/?>", "\n", desc or "")
    return htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))


def row_for(card: dict, o: dict, meta: dict) -> dict | None:
    al = o.get("activeListing") or {}
    gross, net = al.get("grossRent"), al.get("netRent")
    rent = gross if gross is not None else al.get("rent")
    if rent is None or rent > MAX_RENT or o.get("numBedrooms") not in (0, 1):
        return None
    b = o.get("building") or {}
    pa = b.get("primaryAddress") or {}
    desc = _plain(o.get("description") or "")
    notes = []
    # floor: only when the listing text states it (an apartment number is not read here; gates.py does that)
    floor, ftxt = "", ""
    m = FLOOR_RX.search(desc)
    if m:
        w = (m.group(1) or m.group(2) or "").lower()
        floor = str(FLOOR_WORDS.get(w, w))
        ftxt = desc[max(0, m.start() - 20):m.end() + 5].replace("\n", " ").strip()
        notes.append(f'floor stated in the listing text: "{ftxt}"')
    # dogs
    pp, ppn = o.get("petPolicy"), o.get("petPolicyNote")
    ptxt = " ".join(x for x in [f"petPolicy={pp}" if pp else "", ppn or "",
                                f"isUnitPetsAllowed={o.get('isUnitPetsAllowed')}" if o.get("isUnitPetsAllowed") is not None else ""] if x)
    low = f"{pp or ''} {ppn or ''}".lower()
    if re.search(r"\bno dogs?\b|dogs? not allowed|no pets|not[_ ]allowed|cats? only", low):
        dogs = "no"
    elif "dog" in low and not re.search(r"no dog", low):
        dogs = "yes"
    else:
        dogs = "unknown"  # "allowed" names pets, not dogs: kept as text
    weight = ""
    mw = re.search(r"(\d{2,3})\s*(?:lb|lbs|pounds)", f"{ppn or ''}", re.I)
    if mw:
        weight = mw.group(1)
    # elevator: the amenity flag is a checkbox; true is a statement, false is only "not ticked"
    if o.get("isBuildingElevator") is True or re.search(r"\belevator\b", desc, re.I) and not re.search(r"no elevator|walk[- ]?up", desc, re.I):
        elevator = "yes"
        notes.append("elevator: " + ("building amenity ticked on the listing (aggregator)" if o.get("isBuildingElevator") else "named in the listing text"))
    elif re.search(r"\bno elevator\b|\bwalk[- ]?up\b", desc, re.I):
        elevator = "no"
        notes.append("listing text says walk-up / no elevator")
    else:
        elevator = "unknown"
    laundry = "in_unit" if o.get("isUnitWasherDryer") else ("in_building" if o.get("isBuildingLaundryRoom") else "")
    avail = al.get("availableDate") or ""
    avtxt = f"availableDate={avail}" + ("; Openigloo marks it a future listing ('not available yet')" if al.get("isFutureListing") else "")
    age = ""
    if al.get("atCreated"):
        try:
            from datetime import datetime
            age = str((datetime.fromisoformat(meta["retrieved_at"]) - datetime.fromisoformat(al["atCreated"])).days)
        except ValueError:
            age = ""
    if net is not None and gross is not None and net != gross:
        notes.append(f"net-effective rent ${net:,} shown on Openigloo search cards; listed_rent is the gross rent")
    if o.get("isNoFee"):
        notes.append("no broker fee (isNoFee)")
    if o.get("isBuildingRentStabilized"):
        notes.append("building has rent-stabilized units on record")
    if b.get("numFloors"):
        notes.append(f"building_floors from Openigloo's building record (city open data), built {b.get('builtYear')}, {b.get('numUnits')} units")
    if re.search(r"amenity fee|guarantor fee", desc, re.I):
        notes.append("listing text says it 'might require' an application fee, deposit, amenity or guarantor fees (no amounts)")
    if re.search(r"similar units", desc, re.I):
        notes.append("listing text: photos may depict similar units")
    if al.get("leaseTermMonths"):
        notes.append(f"lease term {al['leaseTermMonths']} months")
    if al.get("listerOrg"):
        notes.append(f"listed by {al['listerOrg']}")
    imgs = o.get("images") or []
    ld = lambda v: "" if v is None else v  # noqa: E731
    return {
        "listing_id": f"openigloo_{o['id']}", "source_site": "openigloo", "url": card["url"], "detail_level": "detail",
        "first_seen": meta["retrieved_at"], "last_seen": meta["retrieved_at"],
        "building_name": ld(b.get("name")), "address": pa.get("streetAddress") or o.get("fullAddress", "").split(" #")[0],
        "city": "Brooklyn" if (o.get("neighborhood") or {}).get("borough") == "Brooklyn" else (o.get("neighborhood") or {}).get("borough", ""),
        "state": "NY", "zip": ld(b.get("zipCode")), "lat": ld(b.get("lat") or o.get("buildingLat")),
        "lon": ld(b.get("lon") or o.get("buildingLon")), "unit": ld(o.get("unitNumber")), "beds": o.get("numBedrooms"),
        "baths": ld(o.get("numBathrooms")), "sqft": o.get("area") or "", "listed_rent": rent,
        "price_basis": "gross monthly rent on the unit page (activeListing.grossRent)",
        "concession_text": ld(al.get("promotion")), "available_date_text": avtxt, "available_date": avail,
        "dogs": dogs, "dog_policy_text": ptxt, "dog_weight_limit_lb": weight, "elevator": elevator, "floor": floor,
        "building_floors": ld(b.get("numFloors")), "parking_type": "building parking listed" if o.get("isBuildingParking") else "",
        "parking_fee": "", "pet_rent": "", "other_monthly_fees_json": "", "utilities_included":
            "heat and hot water (listing text)" if re.search(r"heat ?(?:&|and|\+) ?hot water(?: are)? included", desc, re.I) else "",
        "laundry": laundry, "listing_type": "unknown", "manager": ld(al.get("listerOrg")), "listing_age_days": age,
        "photo_url": (imgs[0].get("url") if imgs else ""), "building_url": ld(b.get("webUrl")),
        "raw_path": meta["path"], "notes": "; ".join(notes),
    }


def build() -> None:
    old = {}
    if OUT.exists():
        with open(OUT) as f:
            old = {r["listing_id"]: r for r in csv.DictReader(f)}
    rows, skipped = {}, {"no listing object": 0, "over cap or not studio/1BR on unit page": 0, "page not cached": 0}
    for card in cards().values():
        if (card["gross"] or card["net"] or 10**6) > MAX_RENT:
            continue
        text, meta = None, None
        try:
            lib.HOST_DELAY[HOST] = DELAY
            content, meta = lib.cached_get(card["url"], SRC, ext="html", retries=1)  # cache hit only after `detail`
            text = content.decode("utf-8", "replace") if meta["status"] == 200 else None
        except Exception:
            text = None
        if not text:
            skipped["page not cached"] += 1
            continue
        o = listing_obj(text, card["id"])
        if not o:
            skipped["no listing object"] += 1
            continue
        r = row_for(card, o, meta)
        if not r:
            skipped["over cap or not studio/1BR on unit page"] += 1
            continue
        if r["listing_id"] in old:
            r["first_seen"] = min(old[r["listing_id"]]["first_seen"], r["first_seen"])
        rows[r["listing_id"]] = r
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: (r["listed_rent"], r["address"])):
            w.writerow(r)
    print(f"wrote {len(rows)} rows to {OUT.relative_to(lib.ROOT)}; skipped {skipped}")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    try:
        if cmd in ("list", "all"):
            cmd_list()
        if cmd in ("detail", "all"):
            cmd_detail()
    except Stop as e:
        print("STOPPED:", e)
        return
    if cmd in ("build", "all"):
        build()


if __name__ == "__main__":
    main()
