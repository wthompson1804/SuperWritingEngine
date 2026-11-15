"""Region inventory pass, building-first: Westchester and Rockland counties, NY.

Inputs (all read through cached fetches; nothing here invents a value):
  1. raw/region_westchester_rockland/trulia_detail.jsonl  (h_region_westchester_rockland_trulia.py: the Trulia
     building / home detail page of every Trulia lead; price, date, pet card, features read from that page)
  2. SightMap unit feeds embedded in buildings' own leasing sites (CURATED[...]["sightmap"])
  3. Ginsburg (gdcrentals.com) floor-plan rows already read today into data/listings_raw/mgmt_gdc.csv
  4. Hand-recorded buildings and units in h_region_westchester_rockland_data.py (each with the page URL read)
Building facts (dogs, weight limit, elevator, floors) are merged per building from those pages plus the hand-recorded
evidence in the data file; every merged fact names its source URL in `notes`.

Outputs:
  data/listings_raw/region_westchester_rockland.csv       (contract columns)
  data/reference/region_buildings_westchester_rockland.csv
Idempotent: rows are keyed by listing_id; first_seen is kept on re-runs.
Usage: python3 scripts/h_region_westchester_rockland.py [--refresh-sightmap]
"""
from __future__ import annotations
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path
from h_mgmt_common import COLS, ROOT, OUT_DIR, upsert, jdump, polite_get, BotWall
import h_mgmt_sightmap as sm
import lib
from h_region_westchester_rockland_data import CURATED, MANUAL_BUILDINGS

SRC = "region_westchester_rockland"
OUT = OUT_DIR / "region_westchester_rockland.csv"
BOUT = ROOT / "data" / "reference" / "region_buildings_westchester_rockland.csv"
TRULIA = ROOT / "raw" / SRC / "trulia_detail.jsonl"
CAP, WINDOW_END = 3000, "2026-12-15"
MIN_WL = 25  # dog weight gate lowered from 40 to 25 lb (plan v3 update)
BCOLS = ["building_name", "address", "town", "state", "zip", "url", "floors", "elevator", "elevator_basis", "dogs",
         "dog_weight_limit_lb", "dog_policy_text", "verdict", "units_written", "units_in_window", "min_rent_seen",
         "manager", "source_url", "notes"]


def norm_addr(a: str, z: str) -> str:
    a = re.sub(r"(?i)\b(apt|unit|#|ste)\b.*$", "", a or "").lower()
    a = re.sub(r"[^a-z0-9 ]", " ", a)
    rep = {"street": "st", "avenue": "ave", "place": "pl", "drive": "dr", "road": "rd", "boulevard": "blvd", "highway": "hwy",
           "north": "n", "south": "s", "east": "e", "west": "w", "lane": "ln", "court": "ct", "parkway": "pkwy", "terrace": "ter"}
    return " ".join(rep.get(w, w) for w in a.split()) + "|" + (z or "")[:5]


def floor_from_unit(u: str, rx: str = "") -> str:
    u = (u or "").strip().upper()
    if rx:
        m = re.search(rx, u)
        return str(int(m.group(1))) if m else ""
    m = re.fullmatch(r"(?:PH)?(\d{1,2})[A-Z]", u)
    if m: return str(int(m.group(1)))
    m = re.fullmatch(r"(\d{1,2})(\d{2})[A-Z]?", u)
    if m: return str(int(m.group(1)))
    return ""


def in_window(d: str) -> bool:
    return bool(d) and (d == "now" or d <= WINDOW_END)


def small_only(policy: str) -> bool:
    m = re.search(r"Dogs: Allowed \(([^)]*)\)", policy or "")
    return bool(m and re.search(r"Size allowed: Small(;|$)", m.group(1)))


def load_trulia() -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    if not TRULIA.exists(): return groups
    seen = set()
    for l in TRULIA.read_text().splitlines():
        d = json.loads(l)
        for r in d["rows"]:
            if r["listing_id"] in seen: continue
            seen.add(r["listing_id"])
            r["_desc"] = d.get("desc") or ""
            r["_why"] = d.get("why") or ""
            groups[d["url"]].append(r)
        if not d["rows"]:
            groups[d["url"]] = groups.get(d["url"], [])
            NOROWS[d["url"]] = d.get("why") or ""
            NOFACTS[d["url"]] = d
    return groups


NOROWS: dict[str, str] = {}
NOFACTS: dict[str, dict] = {}


def sightmap_rows(key: str, c: dict, refresh: bool) -> tuple[list[dict], dict]:
    us, info = sm.units(c["sightmap"], SRC, refresh=refresh)
    a = info.get("address") or {}
    nums = [int(x) for x in info.get("floor_labels", []) if str(x).isdigit()]
    rows = []
    for u in us:
        if u["beds"] not in (0, 1) or not u["price"] or u["price"] > CAP or u.get("affordable"): continue
        fees = {k: v for k, v in (u["required_fees"] or {}).items()}
        rows.append({
            "listing_id": f"region_wr:{key}:{u['unit']}", "source_site": c["site_host"], "url": c["avail_url"], "detail_level": "detail",
            "first_seen": u["seen"], "last_seen": u["seen"], "building_name": c["name"], "address": c.get("address") or a.get("street", "").strip(),
            "city": c.get("city") or a.get("city", ""), "state": "NY", "zip": c.get("zip") or a.get("zip", ""), "lat": info.get("lat", ""), "lon": info.get("lon", ""),
            "unit": u["unit"], "beds": u["beds"], "baths": u["baths"], "sqft": u["sqft"], "listed_rent": u["price"],
            "price_basis": "base rent from the building's SightMap unit feed" + (f"; total with required monthly fees {u['total_min']}" if u.get("total_min") and u["total_min"] != u["price"] else "") + (f"; lease term {u['lease_term']}" if u.get("lease_term") else ""),
            "concession_text": u.get("specials", ""), "available_date_text": u.get("available_text") or u.get("available_on"),
            "available_date": "now" if (u.get("available_on") or "9") <= lib.now_iso()[:10] else u.get("available_on"),
            "floor": u["floor"], "building_floors": str(max(nums)) if nums else "",
            "other_monthly_fees_json": jdump(fees) if fees else "", "listing_type": "managed_building", "photo_url": u.get("image", ""),
            "building_url": c["site"], "raw_path": u["raw_path"], "notes": f"floor plan {u['plan']}; floor from SightMap floor label",
        })
    return rows, {"units_total": len(us), "floors": nums}


def gdc_rows() -> dict[str, list[dict]]:
    g = defaultdict(list)
    p = OUT_DIR / "mgmt_gdc.csv"
    if p.exists():
        for r in csv.DictReader(open(p, newline="")):
            r["listing_id"] = "region_wr:" + r["listing_id"]
            g[r["url"]].append(r)
    return g


def al_rows() -> dict[str, list[dict]]:
    """Apartment List property-page rows already read today (data/listings_raw/apartmentlist.csv), by building name."""
    g = defaultdict(list)
    p = OUT_DIR / "apartmentlist.csv"
    if p.exists():
        for r in csv.DictReader(open(p, newline="")):
            if r["state"] == "NY" and r["building_name"]:
                r["listing_id"] = "region_wr:" + r["listing_id"]
                r["notes"] = "row carried over from the Apartment List property page read earlier today; " + re.sub(r"drive_min=[\d.]+; ", "", r["notes"])
                g[r["building_name"]].append(r)
    return g


POS_ELEV = re.compile(r"(?i)elevator (building|access)|elevator in (the )?building|(laundry|parking)[^.]{0,40}\belevator|accessible by elevator|high-speed elevator|^\s*elevator\s*$|\belevator\b")
NEG_ELEV = re.compile(r"(?i)walk[- ]?up|no elevator")


def apply_building(rows: list[dict], c: dict, key: str) -> tuple[list[dict], dict]:
    """Merge curated building facts into rows; collapse to one BUILDING_FAILS row when a gate clearly fails."""
    notes_b = []
    first = rows[0] if rows else {}
    name = c.get("name") or first.get("building_name", "")
    # ---- dogs
    dogs = c.get("dogs") or first.get("dogs") or "unknown"
    policy = c.get("dog_text") or first.get("dog_policy_text") or ""
    if c.get("dog_text") and first.get("dog_policy_text") and c["dog_text"] != first["dog_policy_text"]:
        policy = c["dog_text"] + " || listing page: " + first["dog_policy_text"]
    wl = str(c.get("wl") or first.get("dog_weight_limit_lb") or "")
    if c.get("dog_src"): notes_b.append(f"dog policy from {c['dog_src']}")
    sm_only = small_only(policy) and not c.get("large_ok")
    # ---- elevator
    ufo = bool(c.get("unit_floor_ok"))  # unit numbers encode the floor (checked by hand for this building)
    floors_seen = [int(f) for f in ((floor_from_unit(r.get("unit", ""), c.get("unit_floor_rx", "")) if ufo else "") if not str(r.get("floor") or "").isdigit() else r["floor"] for r in rows) if str(f).isdigit()]
    bfl = str(c.get("floors") or first.get("building_floors") or "")
    elev, basis = "unknown", ""
    if c.get("elevator"):
        elev, basis = c["elevator"], c.get("elev_basis", "")
    elif any(r.get("elevator") == "yes" for r in rows):
        elev, basis = "yes", "listing page lists an elevator"
    elif bfl.isdigit() and int(bfl) >= 6:
        elev, basis = "yes", f"6+ floors ({bfl} floors)"
    elif floors_seen and max(floors_seen) >= 6:
        elev, basis = "yes", f"6+ floors (unit numbers on the page reach floor {max(floors_seen)})"
    else:
        desc = first.get("_desc") or ""
        sent = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", desc) if re.search(r"(?i)elevator|walk[- ]?up", s)]
        if sent and NEG_ELEV.search(" ".join(sent)):
            elev, basis = "no", "listing description: '" + sent[0][:160] + "'"
        elif sent and POS_ELEV.search(" ".join(sent)):
            elev, basis = "yes", "listing description: '" + sent[0][:160] + "'"
    for r in rows:
        if not str(r.get("floor") or "").isdigit():
            f = floor_from_unit(r.get("unit", ""), c.get("unit_floor_rx", ""))
            if f and ufo:
                r["floor"] = f
                r["notes"] = (r.get("notes", "") + "; floor derived from unit number").strip("; ")
        r["building_name"] = name or r.get("building_name", "")
        r["dogs"], r["dog_policy_text"], r["dog_weight_limit_lb"] = dogs, policy[:900], wl
        r["elevator"] = elev
        if bfl: r["building_floors"] = bfl
        for k in ("pet_rent", "parking_type", "parking_fee", "utilities_included", "laundry", "manager"):
            if c.get(k) and not r.get(k): r[k] = c[k]
        if c.get("site") and "trulia.com" not in (r.get("building_url") or "x"): pass
        extra = []
        if basis: extra.append("elevator: " + basis)
        extra += notes_b
        if c.get("notes"): extra.append(c["notes"])
        if c.get("site"): extra.append("building site " + c["site"])
        r["notes"] = "; ".join([x for x in [r.get("notes", "")] + extra if x])
    # ---- verdict
    win = [r for r in rows if in_window(r.get("available_date", ""))]
    undated = [r for r in rows if not r.get("available_date")]
    fail = ""
    if dogs == "no": fail = "no dogs"
    elif wl.isdigit() and int(wl) < MIN_WL: fail = f"dog weight limit {wl} lb"
    elif elev == "no": fail = "no elevator"
    elif c.get("fail"): fail = c["fail"]
    elif rows and not win and not undated: fail = "nothing available by 2026-12-15"
    if c.get("verdict"):
        verdict = c["verdict"]
    elif fail:
        verdict = "fails:" + fail
    elif not rows:
        verdict = "pass_no_availability" if dogs == "yes" and elev == "yes" else "blocked"
    elif dogs == "yes" and elev == "yes":
        verdict = "pass_with_units"
    else:
        verdict = "unconfirmed:" + "+".join(x for x, ok in (("dogs", dogs == "yes"), ("elevator", elev == "yes")) if not ok)
    if sm_only and not verdict.startswith("fails:"):
        # gate is now 25 lb: "Size allowed: Small" with no number can no longer be read as a clear fail
        verdict = "unconfirmed:dog size (pet card says Size allowed: Small; no weight number given)" + ("+elevator" if elev != "yes" else "")
        for r in rows: r["notes"] = "DOG SIZE UNCONFIRMED: listing pet card says 'Size allowed: Small' with no weight number; " + r.get("notes", "")
    out = rows
    if verdict.startswith("fails:") and rows:
        best = sorted(win or rows, key=lambda r: float(r["listed_rent"]))[0]
        best["notes"] = f"BUILDING_FAILS: {verdict[6:]}; one row kept for the record ({len(rows)} studio/1BR at or under $3,000 seen on the page). " + best.get("notes", "")
        out = [best]
    rents = [float(r["listed_rent"]) for r in rows if r.get("listed_rent")]
    b = {"building_name": name, "address": c.get("address") or first.get("address", ""), "town": c.get("city") or first.get("city", ""), "state": "NY",
         "zip": c.get("zip") or first.get("zip", ""), "url": c.get("site") or first.get("building_url") or first.get("url", ""), "floors": bfl or (str(max(floors_seen)) + "+ (from unit numbers)" if floors_seen else ""),
         "elevator": elev, "elevator_basis": basis, "dogs": dogs, "dog_weight_limit_lb": wl, "dog_policy_text": policy[:300], "verdict": verdict,
         "units_written": len(out) if not verdict.startswith("fails:") else 0, "units_in_window": len(win), "min_rent_seen": min(rents) if rents else c.get("min_rent", ""),
         "manager": c.get("manager") or first.get("manager", ""), "source_url": c.get("source_url") or first.get("url", ""), "notes": c.get("bnotes", "") or c.get("notes", "")}
    return out, b


def main() -> None:
    refresh = "--refresh-sightmap" in sys.argv
    tr = load_trulia()
    gdc = gdc_rows()
    al = al_rows()
    all_rows, buildings, used = [], [], set()
    slug = {re.sub(r"-\d+$", "", u): u for u in tr}
    for c in CURATED.values():  # curated Trulia references are slugs without the numeric id
        if c.get("trulia"):
            c["trulia_slug"] = c["trulia"]
            c["trulia"] = slug.get(c["trulia"], "")
    # 1. curated buildings (own-site sources first)
    for key, c in CURATED.items():
        rows: list[dict] = []
        if c.get("sightmap"):
            try:
                r, info = sightmap_rows(key, c, refresh)
                rows += r
                if info["floors"] and not c.get("floors"): c["floors"] = max(info["floors"])
            except BotWall as e:
                c["notes"] = (c.get("notes", "") + f"; SightMap blocked: {e}").strip("; ")
        if c.get("gdc"):
            rows += [dict(r, source_site="gdcrentals.com", address=c.get("address", ""), city=c.get("city", ""), state="NY", zip=c.get("zip", ""),
                          lat=c.get("lat", ""), lon=c.get("lon", ""), listing_type="managed_building", building_url=c["gdc"],
                          notes="floor-plan row (unit number not published on gdcrentals.com); " + re.sub(r"; building-type text:.*", "", r.get("notes", "")))
                     for r in gdc.get(c["gdc"], [])]
        if c.get("al"):
            have = {str(r.get("unit")).lstrip("0").upper() for r in rows if r.get("unit")}
            rows += [dict(r) for r in al.get(c["al"], []) if str(r.get("unit")).lstrip("0").upper() not in have]
        for m in c.get("units", []):
            rows.append(dict({k: "" for k in COLS}, **m))
        if c.get("trulia"):
            t = [dict(r) for r in tr.get(c["trulia"], [])]
            used.add(c["trulia"])
            have = {(str(r.get("unit")).lstrip("0").upper()) for r in rows if r.get("unit")}
            for r in t:  # keep the Trulia copy only for units the own-site feed did not give
                if not (r.get("unit") and str(r["unit"]).lstrip("0").upper() in have):
                    rows.append(r)
                    if rows and not c.get("lat"): pass
            if t and not c.get("dog_text"):
                c.setdefault("dogs", t[0]["dogs"]); c["dog_text"] = t[0]["dog_policy_text"]; c.setdefault("wl", t[0]["dog_weight_limit_lb"]); c["dog_src"] = "Trulia building page " + c["trulia"]
            if t:
                for r in rows:
                    if not r.get("lat"): r["lat"], r["lon"] = t[0]["lat"], t[0]["lon"]
                if any(x["elevator"] == "yes" for x in t) and not c.get("elevator"):
                    c["elevator"], c["elev_basis"] = "yes", "Trulia building page lists an elevator (" + c["trulia"] + ")"
        out, b = apply_building(rows, c, key)
        all_rows += out; buildings.append(b)
    # 2. every other Trulia detail page
    for url, rows in tr.items():
        if url in used: continue
        rows = [dict(r) for r in rows]
        if not rows:
            if "/building/" in url:
                d = NOFACTS.get(url) or {}
                fx, card = d.get("facts") or {}, d.get("card") or {}
                nm = card.get("name") or re.sub(r"-\d+$", "", url.rsplit("/", 1)[1]).replace("-", " ")
                pmin = card.get("price_min")
                dogs = fx.get("dogs") or "unknown"; wl = str(fx.get("dog_weight_limit_lb") or "")
                why = "no dogs" if dogs == "no" else (f"dog weight limit {wl} lb" if wl.isdigit() and int(wl) < MIN_WL else "nothing at or under $3,000 / no studio or 1BR listed")
                b = {"building_name": nm, "address": fx.get("street") or "", "town": fx.get("city") or card.get("city") or "", "state": "NY", "zip": fx.get("zip") or card.get("zip") or "",
                     "url": url, "floors": fx.get("building_floors") or "", "elevator": fx.get("elevator") or "unknown", "elevator_basis": "Trulia building page lists an elevator" if fx.get("elevator") == "yes" else "",
                     "dogs": dogs, "dog_weight_limit_lb": wl, "dog_policy_text": (fx.get("dog_policy_text") or "")[:300], "verdict": "fails:" + why, "units_written": 0, "units_in_window": 0,
                     "min_rent_seen": pmin if pmin is not None else "", "source_url": url,
                     "notes": (NOROWS.get(url, "") + (f"; lowest studio/1BR price on the Trulia search card: {card.get('price_text') or pmin} ({card.get('beds')})" if pmin else "")).strip("; ")}
                buildings.append(b)
                if d.get("facts"):
                    all_rows.append(dict({k: "" for k in COLS}, listing_id="region_wr:bfail:" + url.rsplit("/", 1)[1], source_site="trulia", url=url, detail_level="card" if pmin else "building",
                                         first_seen=d.get("at") or "", last_seen=d.get("at") or "", building_name=nm, address=b["address"], city=b["town"], state="NY", zip=b["zip"],
                                         listed_rent=pmin if pmin is not None else "", price_basis="lowest studio/1BR price on the Trulia search card (card only)" if pmin else "",
                                         dogs=dogs, dog_policy_text=(fx.get("dog_policy_text") or "")[:900], dog_weight_limit_lb=wl, elevator=b["elevator"], building_floors=b["floors"],
                                         pet_rent=fx.get("pet_rent") or "", listing_type="managed_building", building_url=url, raw_path=d.get("raw_path") or "",
                                         notes=f"BUILDING_FAILS: {why}; {b['notes']}"))
            continue
        out, b = apply_building(rows, {}, url)
        all_rows += out
        if "/building/" in url or b["elevator"] == "yes":
            buildings.append(b)
    # 3. buildings examined by hand with no unit rows
    for b in MANUAL_BUILDINGS:
        buildings.append({k: b.get(k, "") for k in BCOLS})
        if b.get("row"):
            all_rows.append(dict({k: "" for k in COLS}, **b["row"]))
    for r in all_rows:
        for k in list(r):
            if k.startswith("_"): r.pop(k)
    ids = [r["listing_id"] for r in all_rows]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1][:5]
    if OUT.exists(): OUT.unlink()  # rebuilt from cached pages each run; first_seen comes from the page fetch time
    n = upsert(OUT, all_rows)
    with open(BOUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BCOLS); w.writeheader()
        for b in sorted(buildings, key=lambda b: (b.get("town", ""), b.get("building_name", ""))):
            w.writerow({k: b.get(k, "") for k in BCOLS})
    from collections import Counter
    print("rows", n, "buildings", len(buildings))
    print(Counter(re.sub(r":.*", "", b["verdict"]) for b in buildings))
    print("pass_with_units:", sorted(f"{b['building_name']} ({b['town']}) {b['units_in_window']}" for b in buildings if b["verdict"] == "pass_with_units"))


if __name__ == "__main__":
    main()
