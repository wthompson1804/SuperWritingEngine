"""Region pass (westchester_rockland): probe a building's own leasing site.

Usage: python3 scripts/h_region_westchester_rockland_probe.py <url> [<url> ...]   (or --seeds to run every seed URL)
For each site: robots check (Claude-named groups override *), home page, then up to MAXP internal pages whose
link looks like floor plans / availability / pets / amenities / FAQ / fees. Prints keyword snippets (pets, dogs,
weight, elevator, storeys, parking, fees), platform hints (SightMap, RentCafe, Entrata...) and price strings so a
person can record facts by hand. Everything goes through h_mgmt_common.polite_get (cache in
raw/region_westchester_rockland/, >= 2 s per host, stop on 403/429/challenge).
"""
from __future__ import annotations
import re, sys, json
from urllib.parse import urljoin, urlparse
from h_mgmt_common import polite_get, BotWall, strip_tags, ROOT
from h_mgmt_sightmap import find_embed

SRC = "region_westchester_rockland"
MAXP = 5
LINK_RE = re.compile(r"floor-?plans?|availab|apartments?$|residences|pet|amenit|faq|feature|fees|policies|lease|pricing|units|gallery-and|neighborhood-and", re.I)
KW = re.compile(r"(?i)\bpets?\b|\bdogs?\b|\blbs?\b|pounds|elevator|stor(?:y|ies|ey)|\bfloors\b|parking|garage|\bfees?\b|utilit|available now|move.in|breed|concierge|doorman")
PLAT = {"sightmap": r"sightmap\.com", "rentcafe": r"rentcafe|securecafe|yardi", "entrata": r"entrata|prospectportal", "knock": r"knockrentals|knockcrm",
        "realpage": r"realpage|onesite|loftliving", "appfolio": r"appfolio", "nwgapi": r"nwgapi", "rentmanager": r"rentmanager", "buildium": r"buildium|managebuilding",
        "funnel": r"funnelleasing|nestiolistings|nestio", "engrain": r"engrain", "resman": r"myresman", "jonah": r"jonahdigital", "g5": r"g5search|g5marketingcloud", "repli": r"repli360",
        "streeteasy": r"streeteasy", "showmojo": r"showmojo", "tenantturner": r"tenantturner", "apartments.com": r"apartments\.com", "rentgrata": r"rentgrata", "spaces": r"smartrent|udr", "peek": r"peek\.us|leasestar"}

def snippets(text, n=24, w=110):
    out, last = [], -999
    for m in KW.finditer(text):
        if m.start() - last < w: continue
        last = m.start()
        out.append(text[max(0, m.start() - w):m.start() + w + 60].strip())
        if len(out) >= n: break
    return out

def probe(url, deep=True, quiet=False):
    host = urlparse(url).netloc
    res = {"url": url, "pages": {}, "platform": set(), "sightmap": "", "block": ""}
    try:
        html, m = polite_get(url, SRC)
    except BotWall as e:
        res["block"] = str(e); print("BLOCK", url, res["block"]); return res
    except Exception as e:
        res["block"] = "error " + repr(e)[:150]; print("BLOCK", url, res["block"]); return res
    if m["status"] != 200:
        res["block"] = f"HTTP {m['status']}"; print("BLOCK", url, res["block"]); return res
    pages = {url: (html, m)}
    links = []
    for h in re.findall(r'href=["\']([^"\'#]+)', html):
        u = urljoin(url, h)
        if urlparse(u).netloc.replace("www.", "") != host.replace("www.", ""): continue
        if re.search(r"\.(jpg|png|pdf|css|js|svg|webp|ico)(\?|$)", u, re.I): continue
        if LINK_RE.search(urlparse(u).path) and u not in links and u.rstrip("/") != url.rstrip("/"): links.append(u)
    def rank(u):
        p = urlparse(u).path.lower()
        return (0 if "pet" in p else 1 if "floor" in p or "availab" in p else 2 if "faq" in p or "fees" in p else 3 if "amenit" in p or "feature" in p else 4, len(p))
    if deep:
        for u in sorted(links, key=rank)[:MAXP]:
            try:
                pages[u] = polite_get(u, SRC)
            except BotWall as e:
                res["block"] += f" | {u}: {e}"
                break
            except Exception as e:
                res["block"] += f" | {u}: error {repr(e)[:80]}"
    seen = set()
    def uniq(text, rx, n, w=120):
        out = []
        for m in re.finditer(rx, text):
            s = text[max(0, m.start() - w):m.start() + w + 80].strip()
            key = re.sub(r"\W+", "", text[m.start():m.start() + 60].lower())
            if key in seen: continue
            seen.add(key); out.append(s)
            if len(out) >= n: break
        return out
    res["text"] = {}
    for u, (h, mm) in pages.items():
        for k, rx in PLAT.items():
            if re.search(rx, h, re.I): res["platform"].add(k)
        e = find_embed(h)
        if e: res["sightmap"] = e
        t = strip_tags(h)
        res["text"][u] = t
        res["pages"][u] = {"status": mm["status"], "at": mm["retrieved_at"], "path": mm.get("path"), "len": len(h),
                           "title": (re.search(r"<title[^>]*>(.*?)</title>", h, re.S | re.I) or [None, ""])[1].strip()[:90],
                           "prices": sorted(set(re.findall(r"\$\s?[1-9],?\d{3}\b", t)))[:12],
                           "pet": uniq(t, r"(?i)\bdogs?\b|\bbreeds?\b|\d+ ?(lbs?\b|pounds)|weight limit|\bpets? (policy|fee|rent|deposit)|no pets|pets (are )?(allowed|welcome|not)", 5),
                           "elev": uniq(t, r"(?i)elevator|\b\d+[- ]stor(y|ies)|\bstories\b", 2, 80),
                           "park": uniq(t, r"(?i)parking|garage", 2, 70)}
    res["links"] = links[:40]
    if not quiet:
        print("=" * 80); print(url, "| platform:", sorted(res["platform"]), "| sightmap:", res["sightmap"], "| block:", res["block"])
        for u, p in res["pages"].items():
            print("--", u, p["status"], p["len"], "|", p["title"], "| prices:", p["prices"])
            for k in ("pet", "elev", "park"):
                for s in p[k]: print("   %s>" % k, s[:300])
        if res["sightmap"]:
            try:
                import h_mgmt_sightmap as sm
                us, info = sm.units(res["sightmap"], SRC)
                c = [x for x in us if x["beds"] in (0, 1) and x["price"] and x["price"] <= 3000]
                w = [x for x in c if (x["available_on"] or "9") <= "2026-12-15"]
                print("   SIGHTMAP:", info.get("asset_name"), info.get("address"), "units", len(us), "st/1br<=3000:", len(c), "in window:", len(w), "floors:", info.get("floor_labels"))
                for x in w[:6]: print("     ", x["unit"], x["beds"], x["sqft"], x["price"], x["total_min"], x["available_on"], "fl", x["floor"], x["required_fees"])
            except Exception as e:
                print("   SIGHTMAP error", repr(e)[:200])
    return res

if __name__ == "__main__":
    for u in sys.argv[1:]:
        try:
            probe(u)
        except Exception as e:
            print("ERR", u, repr(e)[:200])
