"""AvalonBay (avaloncommunities.com) harvest: studios and 1BRs with starting base rent <= $3,000.

Discovery: tri-state market page + the Arc sitemap named in robots.txt (NY / NJ / CT community URLs).
Community page -> Fusion.globalContent (units, policies, utilities). Unit page -> fees, per-lease-term prices.
Equity Residential communities shown on the market page link to equityapartments.com (Cloudflare wall): skipped.
Idempotent: cached under raw/mgmt_avalon/; pass --refresh to refetch prices.
"""
from __future__ import annotations

import json
import re
import sys

from h_mgmt_common import OUT_DIR, BotWall, grid, jdump, polite_get, upsert, fill_rates

SRC = "mgmt_avalon"
BASE = "https://www.avaloncommunities.com"
OUT = OUT_DIR / "mgmt_avalon.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000


def fusion(html: str) -> dict:
    i = html.find("Fusion.globalContent=")
    if i < 0:
        return {}
    return json.JSONDecoder().raw_decode(html[i + len("Fusion.globalContent="):])[0]


def iso_date(s: str) -> str:
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s or "")
    if m:
        return m.group(1)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else ""


def main() -> None:
    g = grid()
    stats = {"communities": 0, "eqr_skipped": 0, "out_of_grid": 0, "units_seen": 0, "units_kept": 0, "errors": []}
    urls: dict[str, str] = {}
    html, m = polite_get(BASE + "/new-york/nyc-metro-apartments", SRC, refresh=REFRESH)
    for it in fusion(html)["communityResults"]["communities"]["items"]:
        if it["url"].startswith("/"):
            urls[BASE + it["url"].rstrip("/")] = it["name"]
        else:
            stats["eqr_skipped"] += 1
    sm, _ = polite_get(BASE + "/arc/outboundfeeds/avb-sitemap/?outputType=xml&_website=avalon-communities", SRC,
                       ext="xml", refresh=REFRESH)
    for loc in re.findall(r"<loc>([^<]+)", sm):
        loc = loc.rstrip("/")
        parts = loc.split("/")
        if len(parts) == 6 and parts[3] in ("new-york", "new-jersey", "connecticut") and parts[4].endswith("-apartments"):
            urls.setdefault(loc, parts[5])
    print("community urls:", len(urls))

    for curl in sorted(urls):
        try:
            html, cm = polite_get(curl, SRC, refresh=REFRESH)
        except BotWall as e:
            stats["errors"].append(str(e))
            break
        if cm["status"] != 200:
            stats["errors"].append(f"{cm['status']} {curl}")
            continue
        d = fusion(html)
        if not d.get("units") and not d.get("address"):
            stats["errors"].append(f"no data {curl}")
            continue
        stats["communities"] += 1
        addr = d.get("address", {})
        z = (addr.get("zip") or "")[:5]
        if z not in g:
            stats["out_of_grid"] += 1
            continue
        pol = d.get("policies", {})
        feats = d.get("features", [])
        feat_txt = "; ".join(f["name"] + (": " + f["description"] if f.get("description") else "") for f in feats)
        dogs_allowed = "dogs" in [a.lower() for a in d.get("allowedPets", [])]
        maxw = pol.get("maximumPetWeight") or 0
        util_inc = [u["name"] for u in d.get("utilities", []) if u.get("responsibleSide", "").lower() in ("community", "owner", "landlord", "included")]
        util_txt = "; ".join(f"{u['name']}={u.get('responsibleSide')}" for u in d.get("utilities", []))
        elev = "yes" if re.search(r"(?i)elevator", feat_txt) else "unknown"
        laundry = "in_unit" if re.search(r"(?i)in-unit washer|washer/dryer", feat_txt) else "unknown"
        max_floor = max([int(u["floorNumber"]) for u in d.get("units", []) if str(u.get("floorNumber", "")).isdigit()] or [0])
        photo = ""
        pm = re.search(r'"(https://[^"]*arcpublishing\.com/[^"]+\.(?:jpe?g|png))"', html)
        if pm:
            photo = pm.group(1)
        rows = []
        for u in d.get("units", []):
            stats["units_seen"] += 1
            sp = u.get("startingAtPricesUnfurnished") or {}
            pr = sp.get("prices") or {}
            price = pr.get("price")
            if u.get("bedroomNumber") not in (0, 1) or not price or price > CAP:
                continue
            fees, per_term, raw_path, seen, detail = [], {}, cm["path"], cm["retrieved_at"], "building_page_unit_row"
            uurl = u.get("url") or curl
            if u.get("url"):
                try:
                    uh, um = polite_get(u["url"], SRC, refresh=REFRESH)
                    ud = fusion(uh) if um["status"] == 200 else {}
                    if ud.get("unit"):
                        fees = ud.get("fees", [])
                        ppm = (ud["unit"].get("unitRentPrice") or {}).get("pricesPerMoveinDate") or []
                        if ppm:
                            per_term = ppm[0].get("pricesPerTerms") or {}
                        raw_path, seen, detail = um["path"], um["retrieved_at"], "detail"
                except BotWall as e:
                    stats["errors"].append(str(e))
                    raise
            # price on the unit page for the same lease term overrides the community-page row
            term = sp.get("leaseTerm")
            if per_term.get(str(term), {}).get("price"):
                price = per_term[str(term)]["price"]
                total = per_term[str(term)].get("totalPrice")
            else:
                total = pr.get("totalPrice")
            if price > CAP:
                continue
            p12 = per_term.get("12", {}).get("price")
            monthly = [f for f in fees if f.get("dueAt") == "Monthly"]
            req = {f["name"]: f["amount"]["max"] for f in monthly if not f.get("optional")}
            if not fees and total and total > price:
                req = {"required monthly fees (total - base)": total - price}
            def rng(f):
                a = f["amount"]
                return str(a["min"]) if a["min"] == a["max"] else f"{a['min']}-{a['max']}"
            park = [f for f in monthly if f.get("type") == "Parking" or "parking" in f["name"].lower()]
            dogfee = [f for f in monthly if f.get("subCategory") == "dog" or "dog" in f["name"].lower()]
            avail = iso_date(u.get("availableDateUnfurnished", ""))
            promos = "; ".join(p.get("promotionTitle", "") for p in (u.get("promotions") or []))
            conc = "; ".join(json.dumps(c)[:200] for c in (u.get("concessions") or []))
            park_desc = next((f["description"] or f["name"] for f in feats if f["name"].lower().startswith("parking") or "garage" in f["name"].lower()), "")
            notes = []
            if p12:
                notes.append(f"12-month base rent {p12}")
            if max_floor:
                notes.append(f"highest floor among available units: {max_floor}")
            if u.get("unitStatus"):
                notes.append(f"status {u['unitStatus']}")
            notes.append("elevator not stated on site")
            rows.append({
                "listing_id": "avalon:" + u["unitId"], "source_site": "avaloncommunities.com", "url": uurl,
                "detail_level": detail, "first_seen": seen, "last_seen": seen,
                "building_name": d.get("name"), "address": (u.get("address") or addr).get("addressLine1"),
                "city": addr.get("city"), "state": addr.get("state"), "zip": z,
                "lat": (d.get("coordinates") or {}).get("latitude"), "lon": (d.get("coordinates") or {}).get("longitude"),
                "unit": u.get("unitName"), "beds": u.get("bedroomNumber"), "baths": u.get("bathroomNumber"),
                "sqft": u.get("squareFeet"), "listed_rent": price,
                "price_basis": f"base rent, lowest 'starting at' price ({term}-month lease, unfurnished); total incl. required monthly fees {total}",
                "concession_text": "; ".join(x for x in (promos, conc) if x),
                "available_date_text": u.get("availableDateUnfurnished"), "available_date": avail,
                "dogs": "yes" if dogs_allowed else "no",
                "dog_policy_text": (pol.get("petPolicy") or "") + f" Max pets {pol.get('maximumPets')}; maximumPetWeight field = {maxw}"
                                   + ("; restricted breeds: " + ", ".join((pol.get("restrictedBreeds") or {}).get("breeds", [])) if pol.get("restrictedBreeds") else ""),
                "dog_weight_limit_lb": (maxw if maxw else ("none_stated" if dogs_allowed else "")),
                "elevator": elev, "floor": u.get("floorNumber") or "unknown", "building_floors": "unknown",
                "parking_type": "; ".join(x for x in (park_desc, pol.get("residentPolicy") or "") if x)[:400],
                "parking_fee": "; ".join(rng(f) for f in park), "pet_rent": "; ".join(rng(f) for f in dogfee),
                "other_monthly_fees_json": jdump(req) if req else "", "utilities_included": ("; ".join(util_inc) if util_inc else "none") + f" [{util_txt}]" if util_txt else "",
                "laundry": laundry, "listing_type": "managed_building", "manager": "AvalonBay Communities",
                "listing_age_days": "", "photo_url": photo, "building_url": curl, "raw_path": raw_path,
                "notes": "; ".join(notes),
            })
        if rows:
            n = upsert(OUT, rows)
            stats["units_kept"] += len(rows)
            print(f"{d.get('name')}: {len(rows)} kept; csv rows {n}", flush=True)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
