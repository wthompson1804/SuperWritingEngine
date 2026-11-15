"""Connecticut region pass (building-first): merge what was read per building and write the three outputs.

Inputs (all cached reads, nothing fetched here):
  raw/region_connecticut/al_buildings.jsonl      Apartment List property pages (h_region_connecticut_al.py)
  raw/region_connecticut/trulia_detail.jsonl     Trulia building pages for the leads (h_region_connecticut_trulia.py)
  raw/region_connecticut/sightmap_units.jsonl    SightMap embeds of building sites (h_region_connecticut_sm.py)
  scripts/h_region_connecticut_manual.json       facts read by hand from leasing sites, each with its page URL
Outputs:
  data/listings_raw/region_connecticut.csv, data/reference/region_buildings_connecticut.csv
Idempotent: rewrites both files from the inputs (first_seen kept by upsert).
Gates recorded, not applied: dog weight limit >= 25 lb, rent <= $3,000, window now..2026-12-15, elevator.
"""
import csv, json, re, sys, collections
from pathlib import Path
import lib
from h_mgmt_common import COLS, upsert, grid

D = lib.RAW / "region_connecticut"
OUT = lib.DATA / "listings_raw" / "region_connecticut.csv"
BOUT = lib.DATA / "reference" / "region_buildings_connecticut.csv"
MANUAL = Path(__file__).with_name("h_region_connecticut_manual.json")
WINDOW_END = "2026-12-15"
CAP = 3000
MIN_WL = 25
G = grid()
BCOLS = ("name,address,town,zip,url,floors,elevator,dogs,weight_limit,verdict,units_le_3000,units_in_window,min_rent_seen,"
         "source_url,manager,year_built,unit_count,pet_rent,parking,special_offer,required_fees,utilities_included,pool,doorman,"
         "lat,lon,already_covered,sources,notes").split(",")

ABBR = {"street": "st", "avenue": "ave", "boulevard": "blvd", "road": "rd", "drive": "dr", "place": "pl", "lane": "ln", "court": "ct",
        "north": "n", "south": "s", "east": "e", "west": "w", "square": "sq", "terrace": "ter", "highway": "hwy", "extension": "ext"}


def akey(addr, zp):
    a = re.sub(r"[.,#]", " ", (addr or "").lower())
    a = re.sub(r"\b(apt|unit|ste|suite)\b.*$", "", a)
    a = re.sub(r"^(\d+)\s*-\s*\d+\b", r"\1", a)
    return " ".join(ABBR.get(w, w) for w in a.split()) + "|" + str(zp or "").zfill(5)[:5]


def covered_keys():
    out = {}
    for f in ("mgmt_blt", "mgmt_avalon", "mgmt_greystar"):
        p = lib.DATA / "listings_raw" / f"{f}.csv"
        if p.exists():
            for r in csv.DictReader(open(p)):
                if r["state"] == "CT": out[akey(r["address"], r["zip"])] = f
    for b in ("batch_7", "batch_1"):
        for r in csv.DictReader(open(lib.DATA / "reference" / "evidence_batches" / f"{b}.csv")):
            if r["state"] == "CT": out[akey(r["address"], r["zip"])] = "evidence_" + b
    return out


def in_window(d):
    return d == "now" or (bool(d) and d <= WINDOW_END)


def row_in_window(r):
    return in_window(r.get("available_date") or "") or "AVAILABLE_COUNT=" in (r.get("notes") or "")


def num(x):
    try: return float(str(x).replace("$", "").replace(",", ""))
    except Exception: return None


class B(dict):
    pass


def new_b(name, address, town, zp):
    return B(name=name, address=address, town=town, zip=str(zp).zfill(5)[:5], url="", floors="", elevator="unknown", dogs="unknown",
             weight_limit="", manager="", year_built="", unit_count="", pet_rent="", parking="", special_offer="", required_fees="",
             utilities_included="", pool="", doorman="", lat="", lon="", sources=[], notes=[], rows=[], source_url="", min_all=None,
             elev_basis="", fail="")


def setif(b, k, v):
    if v not in (None, "", "unknown") and not b.get(k): b[k] = v


def from_al(bs):
    p = D / "al_buildings.jsonl"
    if not p.exists(): return
    for l in open(p):
        d = json.loads(l)
        if d["zip"] not in G: continue
        managed = d["rental_type"] in ("apartment", "other", "condo") and (d["elevator_amenity"] or (d["units_count"] or 0) >= 20 or d["website"])
        if not managed: continue
        k = akey(d["address"], d["zip"])
        b = bs.setdefault(k, new_b(d["name"].replace("&amp;", "&"), d["address"], d["city"], d["zip"]))
        url = "https://www.apartmentlist.com" + d["slug"]
        b["sources"].append(url)
        setif(b, "source_url", url); setif(b, "url", (d["website"] or "").split("?")[0]); setif(b, "manager", d["pmc"])
        setif(b, "year_built", d["year_built"]); setif(b, "unit_count", d["units_count"]); setif(b, "lat", d["lat"]); setif(b, "lon", d["lon"])
        am = [a.lower() for a in d["amenities"]]
        if d["elevator_amenity"]:
            b["elevator"] = "yes"; b["elev_basis"] = "Apartment List amenity 'Elevator'"
        if d["dogs"] in ("yes", "no") and b["dogs"] == "unknown":
            b["dogs"] = d["dogs"]; b["dog_text"] = d["policy"]
        setif(b, "weight_limit", d["wl"]); setif(b, "pet_rent", d["pet_rent"])
        if "pool" in am: setif(b, "pool", "yes (indoor/outdoor not stated)")
        if "doorman" in am: setif(b, "doorman", "yes (Apartment List amenity 'Doorman')")
        elif "concierge" in am: setif(b, "doorman", "concierge (Apartment List amenity)")
        if d["low_0_1"] is not None: b["min_all"] = min(x for x in (b["min_all"], d["low_0_1"]) if x is not None)
        if d["reason"] == "no_studio_1br": b["notes"].append("Apartment List shows no studio/1BR available")
        for r in d["rows"]:
            r = dict(r); r["listing_id"] = "rc:" + r["listing_id"]
            b["rows"].append(r)
            setif(b, "parking", r.get("parking_type")); setif(b, "utilities_included", r.get("utilities_included"))
            setif(b, "special_offer", r.get("concession_text")); setif(b, "required_fees", r.get("other_monthly_fees_json"))


def from_trulia(bs):
    p = D / "trulia_detail.jsonl"
    if not p.exists(): return
    for l in open(p):
        d = json.loads(l)
        if not d["rows"]: continue
        r0 = d["rows"][0]
        if str(r0["zip"]).zfill(5) not in G: continue
        k = akey(r0["address"], r0["zip"])
        b = bs.setdefault(k, new_b(r0["building_name"], r0["address"], r0["city"], r0["zip"]))
        b["sources"].append(d["url"])
        setif(b, "source_url", d["url"]); setif(b, "manager", r0.get("manager")); setif(b, "lat", r0.get("lat")); setif(b, "lon", r0.get("lon"))
        if r0.get("elevator") == "yes" and b["elevator"] != "yes":
            b["elevator"] = "yes"; b["elev_basis"] = "Trulia building page lists Elevator"
        elif r0.get("elevator") == "no" and b["elevator"] == "unknown":
            b["elevator"] = "no"; b["elev_basis"] = "Trulia building page"
        pol = r0.get("dog_policy_text") or ""
        if r0.get("dogs") in ("yes", "no"):
            if b["dogs"] == "unknown": b["dogs"] = r0["dogs"]; b["dog_text"] = pol
            elif b["dogs"] != r0["dogs"]: b["notes"].append(f"dog policy conflict: Trulia says dogs={r0['dogs']} ({pol[:80]})")
            elif pol: b["dog_text"] = (b.get("dog_text") or "") + " || Trulia: " + pol
        if re.search(r"Dogs: Allowed \([^)]*Size allowed: Small\)", pol) and "large" not in pol.lower():
            b["notes"].append("Trulia: only small dogs allowed (no weight number)")
        setif(b, "weight_limit", r0.get("dog_weight_limit_lb")); setif(b, "pet_rent", r0.get("pet_rent"))
        setif(b, "parking", "; ".join(x for x in (r0.get("parking_type"), r0.get("parking_fee")) if x))
        setif(b, "special_offer", r0.get("concession_text")); setif(b, "required_fees", r0.get("other_monthly_fees_json"))
        setif(b, "utilities_included", r0.get("utilities_included")); setif(b, "floors", r0.get("building_floors"))
        m = re.search(r"building has (\d+) units", r0.get("notes") or "")
        if m: setif(b, "unit_count", m.group(1))
        have = {(str(x.get("unit")).lower(), int(num(x["listed_rent"]) or 0)) for x in b["rows"]}
        for r in d["rows"]:
            pr = num(r.get("listed_rent"))
            if pr is None: continue
            b["min_all"] = pr if b["min_all"] is None else min(b["min_all"], pr)
            if pr > CAP or str(r.get("beds")) not in ("0", "1"): continue
            if (str(r.get("unit")).lower(), int(pr)) in have: continue
            r = dict(r); r["listing_id"] = "rc:" + r["listing_id"]
            b["rows"].append(r)


def from_zumper(bs):
    """Zumper building pages already read by h_zumper.py (data/listings_raw/zumper.csv): building facts + units."""
    p = lib.DATA / "listings_raw" / "zumper.csv"
    if not p.exists(): return
    for r in csv.DictReader(open(p)):
        if r["state"] != "CT" or r["detail_level"] != "detail" or str(r["zip"]).zfill(5) not in G: continue
        if not (r["elevator"] == "yes" or r["listing_type"] == "managed_building"): continue
        addr = re.sub(r"\s+#\S+$", "", r["address"].split(",")[0]).strip()
        k = akey(addr, r["zip"])
        b = bs.setdefault(k, new_b(r["building_name"] or addr, addr, r["city"], r["zip"]))
        if r["url"] not in b["sources"]: b["sources"].append(r["url"])
        setif(b, "source_url", r["url"]); setif(b, "manager", r["manager"]); setif(b, "lat", r["lat"]); setif(b, "lon", r["lon"])
        if r["elevator"] == "yes" and b["elevator"] != "yes":
            b["elevator"] = "yes"; b["elev_basis"] = "Zumper building page amenity 'Elevator'"
        if r["dogs"] in ("yes", "no") and b["dogs"] == "unknown":
            b["dogs"] = r["dogs"]; b["dog_text"] = r["dog_policy_text"]
        setif(b, "weight_limit", r["dog_weight_limit_lb"]); setif(b, "pet_rent", r["pet_rent"]); setif(b, "parking", r["parking_type"])
        setif(b, "special_offer", r["concession_text"]); setif(b, "floors", r["building_floors"])
        pr = num(r["listed_rent"])
        if pr is None: continue
        b["min_all"] = pr if b["min_all"] is None else min(b["min_all"], pr)
        have = {(str(x.get("unit")).lower(), int(num(x["listed_rent"]) or 0)) for x in b["rows"]}
        if pr <= CAP and str(r["beds"]) in ("0", "1") and (str(r["unit"]).lower(), int(pr)) not in have:
            x = dict(r); x["listing_id"] = "rc:" + x["listing_id"]; x["address"] = addr
            b["rows"].append(x)


def from_sightmap(bs):
    p = D / "sightmap_units.jsonl"
    if not p.exists(): return
    for l in open(p):
        d = json.loads(l)
        k = akey(d["address"], d["zip"])
        b = bs.setdefault(k, new_b(d["name"], d["address"], d["town"], d["zip"]))
        b["sources"].append(d["page"]); setif(b, "url", d["site"]); b["source_url"] = d["page"]
        setif(b, "lat", d.get("lat")); setif(b, "lon", d.get("lon"))
        fl = [int(x) for x in d.get("floor_labels", []) if str(x).isdigit()]
        if fl: b["floors"] = b["floors"] or str(max(fl))
        # SightMap rows carry the floor, so they replace aggregator rows for the building
        srows = []
        for u in d["units"]:
            if u["beds"] not in (0, 1) or not u["price"]: continue
            b["min_all"] = u["price"] if b["min_all"] is None else min(b["min_all"], u["price"])
            if u["price"] > CAP: continue
            av = u["available_on"]
            srows.append({"listing_id": f"rc:sightmap:{d['slug']}:{u['unit']}", "source_site": d["site"].split("//")[1].split("/")[0] + " (SightMap embed)",
                          "url": d["page"], "detail_level": "unit", "first_seen": u["seen"], "last_seen": u["seen"], "unit": u["unit"],
                          "beds": u["beds"], "baths": u["baths"], "sqft": u["sqft"], "listed_rent": u["price"],
                          "price_basis": "unit price shown in the building's SightMap" + (f"; lease term {u['lease_term']}" if u.get("lease_term") else "")
                          + (f"; total with required fees {u['total_min']}" if u.get("total_min") and u["total_min"] != u["price"] else ""),
                          "concession_text": u.get("specials") or "", "available_date_text": u.get("available_text") or av,
                          "available_date": "now" if av and av <= lib.now_iso()[:10] else av, "floor": u["floor"],
                          "other_monthly_fees_json": json.dumps(u["required_fees"]) if u.get("required_fees") else "",
                          "photo_url": u.get("image") or "", "raw_path": u["raw_path"], "listing_type": "managed_building",
                          "notes": f"floor plan {u['plan']}" + ("; affordable-housing unit (income limits)" if u.get("affordable") else "")})
        if srows:
            b["rows"] = srows
            b["notes"].append("unit rows from the building's own SightMap (with floor numbers)")


def from_manual(bs):
    if not MANUAL.exists(): return
    for m in json.loads(MANUAL.read_text()):
        k = akey(m["address"], m["zip"])
        b = bs.setdefault(k, new_b(m["name"], m["address"], m["town"], m["zip"]))
        if m.get("name"): b["name"] = m["name"]
        for f in ("url", "floors", "elevator", "dogs", "weight_limit", "manager", "year_built", "unit_count", "pet_rent", "parking",
                  "special_offer", "required_fees", "utilities_included", "pool", "doorman", "lat", "lon", "fail", "dog_text", "elev_basis", "min_all"):
            if m.get(f) not in (None, ""): b[f] = m[f]
        if m.get("source_url"):
            b["sources"].append(m["source_url"])
            if not b["source_url"] or m.get("primary"): b["source_url"] = m["source_url"]
        if m.get("notes"): b["notes"].append(m["notes"])
        for r in m.get("rows", []):
            r = dict(r); b["rows"].append(r)
        if m.get("fp"):
            fp = json.loads((D / f"fp_{m['fp']}.json").read_text())
            frows = []
            for pl in fp["plans"]:
                if pl["beds"] > 1: continue
                b["min_all"] = pl["min"] if b["min_all"] is None else min(b["min_all"], pl["min"])
                if not pl["avail"] or pl["min"] > CAP: continue
                name = re.sub(r"^.*Bedrooms? ", "", pl["plan"])
                frows.append({"listing_id": f"rc:fp:{m['fp']}:{re.sub(r'[^a-z0-9]+', '-', name.lower())}", "source_site": fp["url"].split("//")[1].split("/")[0],
                              "url": fp["url"], "detail_level": "floorplan", "first_seen": fp["seen"], "last_seen": fp["seen"], "unit": "",
                              "beds": pl["beds"], "baths": pl["baths"], "sqft": pl["sqft"], "listed_rent": pl["min"],
                              "price_basis": f"floor plan price on the building's site (range ${pl['min']}-${pl['max']}); lowest shown",
                              "available_date_text": f"{pl['avail']} unit(s) available (page shows a count, no date)", "available_date": "",
                              "raw_path": fp["raw"], "listing_type": "managed_building", "notes": f"floor plan {name}; AVAILABLE_COUNT={pl['avail']}; move-in date not shown: ask"})
            if frows:
                b["rows"] = frows; b["source_url"] = fp["url"]; b["sources"].append(fp["url"])
                b["notes"].append("rows are floor plans from the building's own site (unit numbers and dates not shown)")
        if m.get("blocked"): b["blocked"] = m["blocked"]


def verdict(b):
    rows = [r for r in b["rows"] if (num(r.get("listed_rent")) or 9e9) <= CAP]
    win = [r for r in rows if row_in_window(r)]
    wl = num(b["weight_limit"])
    if b.get("fail"): v = "fails:" + b["fail"]
    elif b["dogs"] == "no": v = "fails:no dogs"
    elif wl is not None and wl < MIN_WL: v = f"fails:dog weight limit {int(wl)} lb"
    elif b["elevator"] == "no": v = "fails:no elevator"
    elif not rows and b["min_all"] is not None and b["min_all"] > CAP: v = f"fails:nothing <= $3,000 (lowest studio/1BR seen ${int(b['min_all'])})"
    elif b["elevator"] != "yes": v = "unconfirmed:elevator not stated" + ("" if b["dogs"] == "yes" else "; dogs not named")
    elif b["dogs"] != "yes": v = "unconfirmed:dogs not named on the page"
    elif rows and not win: v = "fails:nothing available by 2026-12-15"
    elif not rows: v = "blocked" if b.get("blocked") and b["min_all"] is None else "pass_no_availability"
    else: v = "pass_with_units"
    return v, rows, win


def main():
    bs = {}
    from_al(bs); from_trulia(bs); from_zumper(bs); from_sightmap(bs); from_manual(bs)
    cov = covered_keys()
    out_rows, brows = [], []
    stats = collections.Counter()
    for k, b in sorted(bs.items(), key=lambda kv: (G.get(kv[1]["zip"], 999), kv[1]["name"])):
        v, rows, win = verdict(b)
        b["already_covered"] = cov.get(k, "")
        stats[v.split(":")[0]] += 1
        base = {"building_name": b["name"], "address": b["address"], "city": b["town"], "state": "CT", "zip": b["zip"], "lat": b["lat"], "lon": b["lon"],
                "dogs": b["dogs"], "dog_policy_text": b.get("dog_text", ""), "dog_weight_limit_lb": b["weight_limit"], "elevator": b["elevator"],
                "building_floors": b["floors"], "manager": b["manager"], "building_url": b["url"] or b["source_url"], "listing_type": "managed_building"}
        bnote = "; ".join(dict.fromkeys(n for n in b["notes"] if n))
        if b["elev_basis"]: bnote = (f"elevator: {b['elev_basis']}; " + bnote).strip("; ")
        if b["pool"]: bnote += f"; pool: {b['pool']}"
        if b["doorman"]: bnote += f"; doorman: {b['doorman']}"
        if b["year_built"]: bnote += f"; year built {b['year_built']}"
        if v.startswith(("fails", "blocked")) or not rows:
            tag = "BUILDING_FAILS: " if v.startswith("fails") else "NO_AVAILABILITY: " if v == "pass_no_availability" else "BLOCKED: " if v == "blocked" else "UNCONFIRMED: "
            r = dict(base)
            r.update({"listing_id": "rc:bldg:" + re.sub(r"[^a-z0-9]+", "-", k), "source_site": (b["source_url"].split("//")[-1].split("/")[0] if b["source_url"] else ""),
                      "url": b["source_url"], "detail_level": "building", "first_seen": lib.now_iso(), "last_seen": lib.now_iso(),
                      "pet_rent": b["pet_rent"], "parking_type": b["parking"], "concession_text": b["special_offer"], "utilities_included": b["utilities_included"],
                      "notes": tag + v + ("; " + bnote if bnote else "")})
            out_rows.append(r)
        else:
            for r in rows:
                x = {c: r.get(c, "") for c in COLS}
                for c, val in base.items():
                    if x.get(c) in ("", None, "unknown") or c in ("elevator", "dogs", "building_name"): x[c] = val
                if not x["pet_rent"]: x["pet_rent"] = b["pet_rent"]
                if not x["parking_type"]: x["parking_type"] = b["parking"]
                if not x["concession_text"]: x["concession_text"] = b["special_offer"]
                if not x["floor"]: x["floor"] = "unknown"
                tag = "" if v == "pass_with_units" else "UNCONFIRMED: " + v + "; "
                x["notes"] = (tag + (x["notes"] or "") + ("; " + bnote if bnote else "")).strip("; ")
                out_rows.append(x)
        brows.append({**{c: b.get(c, "") for c in BCOLS}, "verdict": v, "units_le_3000": len(rows), "units_in_window": len(win),
                      "min_rent_seen": b["min_all"] if b["min_all"] is not None else "", "sources": " | ".join(dict.fromkeys(b["sources"])),
                      "notes": bnote + ("; dog policy: " + b.get("dog_text", "")[:400] if b.get("dog_text") else "")})
    if OUT.exists() and "--fresh" in sys.argv: OUT.unlink()
    n = upsert(OUT, out_rows)
    with open(BOUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BCOLS); w.writeheader(); w.writerows(brows)
    print("buildings", len(brows), dict(stats), "rows written", len(out_rows), "csv total", n)


if __name__ == "__main__":
    main()
