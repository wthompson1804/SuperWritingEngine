"""Russo Development ("Vermella" communities, NJ): per-building sites linked from russodevelopment.com.

Each building site's /floorplans page loads its unit list in the browser from yardi.nwgapi.com/units2.php
(the site vendor's feed; that host has no robots.txt). The page is rendered headless (h_mgmt_render.js) and the
feed response the page itself receives is saved; nothing is requested that the public page does not request.
Policy / amenity wording comes from the site's home and /amenities pages (plain fetch).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

from h_mgmt_common import OUT_DIR, ROOT, BotWall, grid, polite_get, robots_ok, strip_tags, upsert, fill_rates, weight_limit
from h_mgmt_gardencommunities import snips

SRC = "mgmt_russo"
OUT = OUT_DIR / "mgmt_russo.csv"
REFRESH = "--refresh" in sys.argv
CAP = 3000
RENDER = ROOT / "raw" / SRC / "render"
SKIP = (r"facebook|instagram|twitter|linkedin|google|youtube|gstatic|w\.org|schema|apple|pinterest|tiktok|vimeo|"
        r"cloudflare|jsdelivr|typekit|gmpg|//x\.com|yelp|wp\.com|gravatar|miniorange|browsehappy|splendordesign|"
        r"office\.com|russodevelopment|njbmagazine|vermellanj\.com|rentcafe|securecafe|goo\.gl|bit\.ly|maps\.|njbiz|roi-nj|re-nj|globest|patch\.com|nj\.com")


def discover() -> list[str]:
    sm, _ = polite_get("https://russodevelopment.com/property-sitemap.xml", SRC, ext="xml", refresh=REFRESH)
    sites: dict[str, str] = {}
    for u in re.findall(r"<loc>([^<]+)", sm):
        try:
            h, m = polite_get(u, SRC)
        except (BotWall, RuntimeError):
            continue
        if m["status"] != 200 or not re.search(r"(?i)apartment|residen|rental", strip_tags(h)):
            continue
        for x in set(re.findall(r'href="(https?://[^"/]+)', h)):
            if not re.search(SKIP, x):
                sites.setdefault(urlparse(x).netloc.replace("www.", ""), x)
    return sorted(sites.values())


def main() -> None:
    g = grid()
    stats = {"sites": 0, "walled": [], "no_feed": [], "units_seen": 0, "kept": 0, "out_of_grid": 0, "errors": []}
    RENDER.mkdir(parents=True, exist_ok=True)
    sites = discover()
    print("building sites:", sites, flush=True)
    jobs, ok_sites = [], []
    for s in sites:
        try:
            if not robots_ok(s + "/floorplans", SRC):
                stats["walled"].append(s + " (robots)")
                continue
            home, hm = polite_get(s, SRC, refresh=REFRESH)
            if hm["status"] != 200:
                stats["errors"].append(f"{hm['status']} {s}")
                continue
        except (BotWall, RuntimeError) as e:
            stats["walled"].append(f"{s}: {str(e)[:60]}")
            continue
        ok_sites.append(s)
        jobs.append({"url": s + "/floorplans", "out": str(RENDER / (urlparse(s).netloc.replace("www.", "") + "_floorplans"))})
    cfg = RENDER / "_jobs.json"
    cfg.write_text(json.dumps({"delay_ms": 3000, "wait_ms": 9000, "capture": r"nwgapi\.com/units|units2\.php", "refresh": REFRESH, "jobs": jobs}))
    r = subprocess.run(["node", str(ROOT / "scripts" / "h_mgmt_render.js"), str(cfg)], capture_output=True, text=True, timeout=3600)
    print(r.stdout[-1500:], r.stderr[-300:], flush=True)
    for s, job in zip(ok_sites, jobs):
        base = Path(job["out"])
        if not Path(str(base) + ".meta.json").exists():
            stats["walled"].append(s + " (render stopped)")
            continue
        meta = json.loads(Path(str(base) + ".meta.json").read_text())
        xhr = json.loads(Path(str(base) + ".xhr.json").read_text())
        feed = None
        for x in xhr:
            if x["status"] == 200:
                try:
                    feed = json.loads(x["body"])
                    break
                except json.JSONDecodeError:
                    pass
        stats["sites"] += 1
        if not isinstance(feed, dict) or not feed:
            stats["no_feed"].append(s)
            continue
        home, hm = polite_get(s, SRC)
        text = strip_tags(home)
        try:
            am, amm = polite_get(s + "/amenities", SRC, refresh=REFRESH)
            if amm["status"] == 200 and len(am) > 3000:
                text += " || " + strip_tags(am)
        except (BotWall, RuntimeError):
            pass
        tm = re.search(r"<title>\s*([^<|]+)", home)
        name = tm.group(1).strip() if tm else s
        adm = re.search(r"(?<![\d-])(\d{1,5} [A-Za-z0-9 .'-]{3,50}?)\.?,?\s+([A-Z][A-Za-z .'-]{2,25}),\s*(NJ|NY)\s+(\d{5})", text)
        address, city, state, z = (adm.group(1), adm.group(2).strip(), adm.group(3), adm.group(4)) if adm else ("", "", "NJ", "")
        if z and z not in g:
            stats["out_of_grid"] += 1
            continue
        pet_txt = snips(text, r"(?i)\b(pets?|dogs?|breed)\b")
        park_txt = snips(text, r"(?i)\b(parking|garages?)\b", 3, 50)
        elev_txt = snips(text, r"(?i)elevator|mid-rise|stor(y|ies)\b", 3)
        dogs = "no" if re.search(r"(?i)no (pets|dogs)", pet_txt) else ("yes" if re.search(r"(?i)\bdogs?\b", pet_txt) else "unknown")
        elev = "yes" if re.search(r"(?i)\belevators?\b", text) else "unknown"
        laundry = "in_unit" if re.search(r"(?i)washers? (and|&) dryers?|washer/dryer|in-home laundry|in-unit laundry", text) else "unknown"
        rows = []
        for key, u in feed.items():
            if not isinstance(u, dict):
                continue
            stats["units_seen"] += 1
            rent = u.get("minimumRent")
            if u.get("beds") not in (0, 1) or not rent or rent > CAP:
                continue
            unit = str(u.get("apartmentName") or key).upper()
            digits = re.sub(r"\D", "", unit.split("-")[-1])
            # 3-4 digit unit numbers: leading digit(s) = floor. 5+ digits (e.g. VC-30304) mix building and floor: left unknown.
            floor = digits[:-2] if 3 <= len(digits) <= 4 else "unknown"
            ad = u.get("availableDate") or ""
            dm = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", ad)
            avail = f"{dm.group(3)}-{int(dm.group(1)):02d}-{int(dm.group(2)):02d}" if dm else ""
            if u.get("_available") is True and avail and avail <= meta["retrieved_at"][:10]:
                avail = "now"
            rows.append({
                "listing_id": f"russo:{u.get('propertyId')}:{u.get('apartmentId')}", "source_site": urlparse(s).netloc,
                "url": s + "/floorplans", "detail_level": "detail", "first_seen": meta["retrieved_at"], "last_seen": meta["retrieved_at"],
                "building_name": name, "address": address, "city": city, "state": state, "zip": z, "lat": "", "lon": "",
                "unit": unit, "beds": u.get("beds"), "baths": u.get("baths"), "sqft": u.get("sqft"), "listed_rent": rent,
                "price_basis": f"lowest rent over lease terms {u.get('minimumRentLeaseTerm')}-{u.get('maximumRentLeaseTerm')} months; range {rent}-{u.get('maximumRent')}",
                "concession_text": (u.get("specials") or "") or snips(text, r"(?i)move[- ]in bonus|months? free", 1, 80),
                "available_date_text": f"{ad} ({u.get('unitStatus')})", "available_date": avail,
                "dogs": dogs, "dog_policy_text": pet_txt[:500], "dog_weight_limit_lb": weight_limit(pet_txt),
                "elevator": elev, "floor": floor, "building_floors": "unknown", "parking_type": park_txt[:300],
                "parking_fee": "", "pet_rent": "", "other_monthly_fees_json": "", "utilities_included": "",
                "laundry": laundry, "listing_type": "managed_building", "manager": "Russo Development / Russo Property Management",
                "listing_age_days": "", "photo_url": u.get("floorplanImageURL") or "", "building_url": s,
                "raw_path": str((Path(str(base) + ".xhr.json")).relative_to(ROOT)),
                "notes": f"{'floor derived from unit number' if floor != 'unknown' else 'floor not derivable from unit number'}; floor plan {u.get('floorplanName')}; building-type text: {elev_txt[:200]}; pet policy page not found on site",
            })
        if rows:
            upsert(OUT, rows)
            stats["kept"] += len(rows)
        print(f"{name}: feed units {len(feed)}, kept {len(rows)}", flush=True)
    print(json.dumps(stats))
    if OUT.exists():
        print(fill_rates(OUT))


if __name__ == "__main__":
    main()
