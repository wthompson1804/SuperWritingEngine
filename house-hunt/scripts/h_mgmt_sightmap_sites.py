"""Per-building websites (several owners) whose availability is a SightMap embed.

Seeds: scripts/h_mgmt_sightmap_sites_seeds.txt, one "owner|https://site" per line (found by following the
owners' directory pages: Tritec, Rose Associates, Mill Creek, ...). For each site: robots.txt check, home page,
then the usual availability paths until a sightmap.com/embed/<id> is found; units come from h_mgmt_sightmap.
Pet / parking / elevator wording is taken from the site's home, /amenities/, /features/, /faq/ and /pet-policy/ pages
when they exist. Sites that answer 403 / challenge are logged and skipped (never retried another way).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from h_mgmt_common import OUT_DIR, BotWall, grid, jdump, polite_get, strip_tags, upsert, fill_rates, weight_limit
from h_mgmt_gardencommunities import snips
import h_mgmt_sightmap as sm

SRC = "mgmt_sightmap_sites"
OUT = OUT_DIR / "mgmt_sightmap_sites.csv"
SEEDS = Path(__file__).with_name("h_mgmt_sightmap_sites_seeds.txt")
REFRESH = "--refresh" in sys.argv
CAP = 3000
AVAIL_PATHS = ["", "/floorplans/", "/floor-plans/", "/availability/", "/sightmap/", "/apartments/", "/availabilities/", "/residences/"]
INFO_PATHS = ["/amenities/", "/features/", "/faq/", "/pet-policy/", "/pets/"]


def main() -> None:
    g = grid()
    stats = {"sites": 0, "walled": [], "no_embed": [], "units_seen": 0, "kept": 0, "out_of_grid": [], "none_under_cap": []}
    seeds = [l.strip().split("|", 1) for l in SEEDS.read_text().splitlines() if l.strip() and not l.startswith("#")]
    for owner, site in seeds:
        site = site.rstrip("/")
        pages, embed, embed_page = {}, "", ""
        try:
            for p in AVAIL_PATHS:
                h, m = polite_get(site + p, SRC, refresh=REFRESH)
                if m["status"] != 200:
                    continue
                pages[p] = h
                e = sm.find_embed(h)
                if e:
                    embed, embed_page = e, site + p
                    break
            if not embed:
                stats["no_embed"].append(site)
                continue
            us, info = sm.units(embed, SRC, refresh=REFRESH)
            for p in INFO_PATHS:
                h, m = polite_get(site + p, SRC, refresh=REFRESH)
                if m["status"] == 200 and len(h) > 3000 and "not found" not in h[:3000].lower():
                    pages[p] = h
        except BotWall as e:
            stats["walled"].append(f"{site}: {str(e)[:70]}")
            continue
        except RuntimeError as e:
            stats["walled"].append(f"{site}: fetch error {str(e)[:60]}")
            continue
        stats["sites"] += 1
        addr = info.get("address", {})
        z = (addr.get("zip") or "")[:5]
        if z and z not in g:
            stats["out_of_grid"].append(site)
            continue
        text = " || ".join(strip_tags(h) for h in pages.values())
        home = pages.get("", "")
        tm = re.search(r"<title>\s*([^<|]+)", home)
        name = info.get("asset_name") or (tm.group(1).strip() if tm else site)
        pet_txt = snips(text, r"(?i)\b(pets?|dogs?|breed)\b", 5)
        park_txt = snips(text, r"(?i)\b(parking|garages?)\b", 3, 50)
        elev_txt = snips(text, r"(?i)elevator|mid-rise|high-rise|stor(y|ies)\b", 3)
        util_txt = snips(text, r"(?i)(heat|hot water|gas|water|electric|utilities|wi-?fi|internet)[^.|]{0,30}included|included[^.|]{0,30}(heat|hot water)", 3, 50)
        dogs = "no" if re.search(r"(?i)no (pets|dogs)|dogs? (are )?not (allowed|permitted)", pet_txt) else ("yes" if re.search(r"(?i)\bdogs?\b", pet_txt) else "unknown")
        elev = "yes" if re.search(r"(?i)\belevators?\b", text) else "unknown"
        laundry = "in_unit" if re.search(r"(?i)washers? (and|&) dryers?|washer/dryer|in-(home|unit) (laundry|washer)", text) else ("on_site" if re.search(r"(?i)laundry", text) else "unknown")
        nums = [int(x) for x in info.get("floor_labels", []) if str(x).isdigit()]
        pr = re.search(r"(?i)pet rent[^$]{0,40}\$(\d+)|\$(\d+)[^.$]{0,25}pet rent", pet_txt)
        rows = []
        for u in us:
            stats["units_seen"] += 1
            if u["beds"] not in (0, 1) or not u["price"] or u["price"] > CAP:
                continue
            avail = "now" if re.search(r"(?i)now", u["available_text"]) else u["available_on"]
            rows.append({
                "listing_id": f"sightmap:{urlparse(site).netloc.replace('www.', '')}:{u['sightmap_unit_id']}",
                "source_site": urlparse(site).netloc + " (SightMap embed)", "url": embed_page, "detail_level": "detail",
                "first_seen": u["seen"], "last_seen": u["seen"], "building_name": name, "address": addr.get("street", ""),
                "city": addr.get("city", ""), "state": addr.get("state", ""), "zip": z, "lat": info.get("lat"), "lon": info.get("lon"),
                "unit": u["unit"], "beds": u["beds"], "baths": u["baths"], "sqft": u["sqft"], "listed_rent": u["price"],
                "price_basis": f"unit price shown in SightMap; total with required monthly fees {u['total_min']}"
                               + (f"-{u['total_max']}" if u["total_max"] != u["total_min"] else "") + (f"; lease term {u['lease_term']}" if u["lease_term"] else ""),
                "concession_text": u["specials"], "available_date_text": u["available_text"] or u["available_on"],
                "available_date": avail, "dogs": dogs, "dog_policy_text": pet_txt[:600], "dog_weight_limit_lb": weight_limit(pet_txt),
                "elevator": elev, "floor": u["floor"] or "unknown", "building_floors": max(nums) if nums else "unknown",
                "parking_type": park_txt[:300], "parking_fee": "", "pet_rent": (pr.group(1) or pr.group(2)) if pr else "",
                "other_monthly_fees_json": jdump(u["required_fees"]) if u["required_fees"] else "",
                "utilities_included": util_txt[:300], "laundry": laundry, "listing_type": "managed_building", "manager": owner,
                "listing_age_days": "", "photo_url": u["image"], "building_url": site, "raw_path": u["raw_path"],
                "notes": "; ".join(x for x in (f"plan {u['plan']}", f"building {u['building']}" if u["building"] else "",
                                               "income-restricted unit" if u["affordable"] else "",
                                               "building_floors = highest floor label in SightMap floor list",
                                               f"building-type text: {elev_txt[:200]}") if x),
            })
        if rows:
            upsert(OUT, rows)
            stats["kept"] += len(rows)
        else:
            stats["none_under_cap"].append(site)
        print(f"{owner} | {name}: units {len(us)}, kept {len(rows)}", flush=True)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
