"""Region pass (westchester_rockland): list every Trulia rental BUILDING card (any price, studio/1BR filter) in the
region's ZIPs, so buildings priced above $3,000 or missing from the earlier <= $3,000 crawl are on record too.
/for_rent/<zip>_zip/0-1_beds/[<n>_p/] is robots-allowed (see h_trulia.py). 3 s delay, stops at a block.
Writes raw/region_westchester_rockland/trulia_zip_buildings.json: {building_url: {name, street, city, zip, price_min, price_max, beds}}.
With --fetch it then reads each building page not already in trulia_detail.jsonl and appends it there.
"""
import json, sys
import h_trulia as T
T.DELAY = 3.0
ZIPS = "10550 10552 10553 10803 10801 10804 10805 10701 10703 10704 10705 10710 10708 10707 10709 10583 10530 10601 10603 10605 10606 10607 10604 10528 10577 10543 10538 10580 10573 10591 10522 10706 10533 10523 10502 10562 10520 10566 10549 10570 10960 10968 10965 10954 10977 10901 10927 10993 10923 10994 10989 10956".split()
D = T.ROOT / "raw" / "region_westchester_rockland"
OUT = D / "trulia_zip_buildings.json"
found = json.loads(OUT.read_text()) if OUT.exists() else {}
donez = set(found.get("_zips", []))
try:
    for z in ZIPS:
        if z in donez: continue
        page, got = 1, 0
        while page <= 6:
            url = f"{T.BASE}/for_rent/{z}_zip/0-1_beds/" + ("" if page == 1 else f"{page}_p/")
            nd, meta = T.fetch(url, 48)
            if nd is None: break
            sd = (nd.get("props") or {}).get("searchData") or {}
            homes = sd.get("homes") or []
            for h in homes:
                u = h.get("url") or ""
                if not u.startswith("/building/"): continue
                loc = h.get("location") or {}; pr = h.get("price") or {}
                found[T.BASE + u] = {"name": loc.get("communityLocation") or "", "street": loc.get("streetAddress"), "city": loc.get("city"), "zip": loc.get("zipCode"),
                                     "price_min": pr.get("min") if pr.get("min") is not None else pr.get("price"), "price_max": pr.get("max"), "price_text": pr.get("formattedPrice"),
                                     "beds": (h.get("bedrooms") or {}).get("formattedValue"), "seen_at": meta["retrieved_at"], "search_url": url}
            got += len(homes)
            if not homes or got >= (sd.get("totalHomes") or 0): break
            page += 1
        donez.add(z); found["_zips"] = sorted(donez)
        OUT.write_text(json.dumps(found, indent=1))
        print(z, "buildings so far", len(found) - 1, flush=True)
except T.Blocked as e:
    print("BLOCKED", e)
if "--fetch" in sys.argv:
    det = D / "trulia_detail.jsonl"
    done = {json.loads(l)["url"] for l in det.read_text().splitlines()} if det.exists() else set()
    todo = [u for u in found if u.startswith("http") and u not in done]
    print("building pages to read", len(todo), flush=True)
    for u in todo:
        try:
            nd, meta = T.fetch(u, 48)
        except T.Blocked as e:
            print("BLOCKED", e); break
        if nd is None:
            rec = {"url": u, "at": meta.get("retrieved_at"), "rows": [], "why": f"gone http {meta.get('status')}"}
        else:
            rows, why = T.parse_detail(nd, meta)
            hd = (nd.get("props") or {}).get("homeDetails") or {}
            feats, hl = T.flat_features(hd.get("features")), T.highlighted(hd.get("features"))
            desc = ((hd.get("description") or {}).get("value") or "") if isinstance(hd.get("description"), dict) else ""
            pets = T.pet_fields((hd.get("activeForRentListing") or {}).get("petPolicy"), feats, hl) if hd else {}
            bf = T.building_feature_fields(feats, hl, desc) if hd else {}
            loc = hd.get("location") or {}
            rec = {"url": u, "at": meta.get("retrieved_at"), "rows": rows, "why": why, "raw_path": meta.get("path"), "card": found[u], "desc": desc,
                   "facts": dict(pets, elevator=bf.get("elevator"), building_floors=bf.get("building_floors"), street=loc.get("streetAddress"), city=loc.get("city"), zip=loc.get("zipCode"))}
        with open(det, "a") as f: f.write(json.dumps(rec) + "\n")
    print("done")
