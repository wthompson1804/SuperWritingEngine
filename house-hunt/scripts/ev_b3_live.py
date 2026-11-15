"""Evidence batch 3, step 1: parse the re-fetched listing pages (raw/evidence_b3) and write live_check_batch_3.csv.
Run after ev_b3_fetch.py --refresh on the batch URLs. No network."""
import csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib, h_apartmentlist as A, h_trulia as T, h_zumper as Z, h_mgmt_greystar as G
from h_mgmt_avalon import fusion
from ev_b3_util import page, put

SITE = {  # building's own leasing site, and whether we could read it
    "third-valley": ("https://www.thirdandvalleyapts.com/", "own site not read: robots.txt disallows Claude agents (also bozzuto.com)"),
    "avalon-teaneck": ("https://www.avaloncommunities.com/new-jersey/teaneck-apartments/avalon-teaneck", ""),
    "avalon-union": ("https://www.avaloncommunities.com/new-jersey/union-apartments/avalon-union", ""),
    "riversedge-at-port-imperial": ("https://www.riversedgepi.com/", "own site not read: HTTP 403"),
    "riverparc": ("https://www.riverparcpi.com/", "own site not read: HTTP 403"),
    "the-landings-at-port-imperial": ("https://www.equityapartments.com/west-new-york/edgewater/the-landings-at-port-imperial-apartments", "own site not read: HTTP 403 (Cloudflare)"),
}
EXTRA = json.load(open(Path(__file__).with_name("ev_b3_live_notes.json"))) if Path(__file__).with_name("ev_b3_live_notes.json").exists() else {}
rows = []
batch = list(csv.DictReader(open(lib.DATA / "reference" / "evidence_batches" / "batch_3.csv")))
for b in batch:
    urls = list(dict.fromkeys(u.strip() for u in b["urls"].split("|") if u.strip()))
    units = [u.strip() for u in b["unit_list"].split(",")]
    rents = [r.strip() for r in b["rents"].split(",")]
    for url in urls:
        try:
            html, m = page(url)
        except KeyError:
            for un in units:
                rows.append(dict(addr_key=b["addr_key"], listing_url=url, unit=un, status="blocked", checked_at=lib.now_iso(), notes="page not fetched"))
            continue
        found = {}   # unit -> (price, avail_text, in_window, note)
        site, note0 = "", ""
        if "apartmentlist.com" in url:
            L = A.parse_listing(html)
            slug = url.rsplit("/", 1)[-1]
            site, note0 = SITE.get(slug, ("", "no own leasing site found (single-owner listing via " + str(L.get("source_name")) + ")"))
            for fp in L["available_units"]:
                for un in fp.get("units") or []:
                    nm = str(un.get("name") or un.get("unit_name") or un.get("display_name"))
                    av = "available now (available_on " + str(un.get("available_on")) + ")" if un.get("available_now") else "available_on " + str(un.get("available_on"))
                    found[nm] = (un.get("price"), av, (un.get("available_on") or "") <= "2026-12-15", f"page updated_at {L.get('updated_at')}")
        elif "avaloncommunities.com" in url:
            d = fusion(html); un = d["unit"]
            ppm = (un.get("unitRentPrice") or {}).get("pricesPerMoveinDate") or []
            site = url.split("/apartment/")[0]
            if ppm:
                first = ppm[0]
                best = min((v.get("netEffectivePrice") or v.get("price"), int(k)) for k, v in first["pricesPerTerms"].items())
                mm = re.match(r"(\d+)/(\d+)/(\d+)", first["moveInDate"])
                iso = f"{mm.group(3)}-{int(mm.group(1)):02d}-{int(mm.group(2)):02d}"
                found[units[0]] = (best[0], f"earliest move-in {iso}", iso <= "2026-12-15", f"lowest price is for a {best[1]}-month lease; this is the building's own site")
        elif "greystar.com" in url:
            s = G.flight(html); pu = G.grab(s, "propertyUnits", "[")
            site, note0 = "https://theparkfords.com/", "greystar.com is the manager's own listing page"
            for u in pu or []:
                found[str(u["unitNumber"])] = (u.get("minPrice"), "availableOn " + str(u.get("availableOn")), (u.get("availableOn") or "") <= "2026-12-15", f"{u.get('floorLabel')}; min price lease term {u.get('minBaseRentLeaseTerm')} months")
        elif "trulia.com" in url:
            hd = json.loads(T.NEXT_RE.search(html).group(1))["props"].get("homeDetails") or {}
            st = hd.get("currentStatus") or {}
            note0 = "no own leasing site found (broker listing)"
            if st.get("isActiveForRent"):
                p = (hd.get("price") or {}).get("price")
                av = hd.get("formattedAvailableDate") or ""
                if not av:
                    for _, _, n, v in T.flat_features(hd.get("features")):
                        if n == "Available": av = v
                iso = T.avail_iso(av, m["retrieved_at"])
                ph = [(x.get("formattedDate"), x.get("event"), (x.get("price") or {}).get("formattedPrice")) for x in (hd.get("priceHistory") or [])[:2]]
                found[units[0]] = (p, av or "not stated", iso in ("now",) or (iso and iso <= "2026-12-15"), "price history: " + "; ".join(f"{a} {b_} {c}" for a, b_, c in ph))
        elif "zumper.com" in url:
            e = (((Z.parse_state(html) or {}).get("detail") or {}).get("entity") or {}).get("data") or {}
            note0 = "no own leasing site found"
            fps = e.get("floorplan_listings") or []
            if fps:
                for fp in fps:
                    mm = re.search(r"(?:Unit|APT #?)\s*#?(\w+)\s*$", fp.get("title") or "")
                    if mm:
                        act = fp.get("listing_status") == 1
                        found[mm.group(1)] = (fp.get("price") if act else None, "date_available " + str(fp.get("date_available")), (fp.get("date_available") or "0") <= "2026/12/15", "" if act else "unit shown as not active on the building page")
            elif e.get("listing_status") == 1:
                found[units[0]] = (e.get("price"), "date_available " + str(e.get("date_available")), (e.get("date_available") or "0") <= "2026/12/15", "")
        for un, stored in zip(units, rents):
            key = un
            if key not in found:   # unit ids differ by source ("E1029" vs "1029", "005-5306" vs "5306")
                alt = [k for k in found if k.lstrip("E") == un.lstrip("E") or k.endswith("-" + un) or un.endswith("-" + k)]
                key = alt[0] if alt else None
            extra = EXTRA.get(b["addr_key"] + "|" + un, "")
            if key is None or found[key][0] is None:
                why = found[key][3] if key else "unit no longer on the page"
                rows.append(dict(addr_key=b["addr_key"], listing_url=url, unit=un, status="gone", price_now="", available_now_text="", matches_stored="no", building_site_url=site, checked_at=m["retrieved_at"], notes="; ".join(x for x in (why, note0, extra) if x)))
                continue
            price, av, inwin, note = found[key]
            same = str(int(float(price))) == str(int(float(stored)))
            status = "live" if same and inwin and price <= 3000 else "changed"
            bits = [note, note0, extra]
            if not same: bits.insert(0, f"stored rent {stored}, now {price}")
            if price > 3000: bits.insert(0, "repriced above $3,000")
            if not inwin: bits.insert(0, "not available by 2026-12-15")
            rows.append(dict(addr_key=b["addr_key"], listing_url=url, unit=un, status=status, price_now=price, available_now_text=av, matches_stored="yes" if same else "no", building_site_url=site, checked_at=m["retrieved_at"], notes="; ".join(x for x in bits if x)))
print(put("live_check", rows), "rows")
from collections import Counter
print(Counter(r["status"] for r in rows))
