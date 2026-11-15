"""Probe helper for the Connecticut region pass: polite fetch (robots, >=2 s/host, bot-wall stop) of building pages
into raw/region_connecticut/, printing only compact facts (platform, SightMap embed, keyword snippets, prices).
Usage: python3 scripts/h_region_connecticut_probe.py [-k kw1,kw2] [-w width] URL [URL...]
"""
import re, sys, json
from h_mgmt_common import polite_get, BotWall, strip_tags
import h_mgmt_sightmap as sm
SRC = "region_connecticut"
KW = r"elevator|\bdogs?\b|\bpets?\b|\blbs?\b|pounds|weight|breed|stor(?:y|ies)\b|\bfloors\b|garage|parking"
PLAT = {"rentcafe": r"rentcafe|securecafe", "entrata": r"entrata|prospectportal", "realpage": r"realpage|onsite\.com|leasestar|g5", "appfolio": r"appfolio",
        "knock": r"knockrentals|knockcrm", "yardi_nwg": r"nwgapi", "buildium": r"buildium|managebuilding", "funnel": r"funnelleasing|nestiolistings",
        "jonah": r"jonahdigital", "spherexx": r"spherexx", "repli": r"repli360", "rentmanager": r"rentmanager", "showmojo": r"showmojo", "propertyware":"propertyware", "apartmentsdotcom_embed": r"apartments\.com", "yougotlistings": r"yougotlistings", "engrain": r"sightmap|engrain", "udr": r"udr\.com", "rentvine": "rentvine", "tenantturner":"tenantturner", "zillow":"zillow.com","turbotenant":"turbotenant"}
def main():
    a = sys.argv[1:]; kw = KW; width = 90; links = False
    while a and a[0].startswith("-"):
        if a[0] == "-k": kw = a[1]; a = a[2:]
        elif a[0] == "-w": width = int(a[1]); a = a[2:]
        elif a[0] == "-l": links = True; a = a[1:]
        else: a = a[1:]
    for u in a:
        try:
            h, m = polite_get(u, SRC)
        except BotWall as e:
            print(f"## {u}\n  BOTWALL {e}"); continue
        except Exception as e:
            print(f"## {u}\n  ERR {str(e)[:150]}"); continue
        t = strip_tags(h)
        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", h)
        print(f"## {u}\n  status={m['status']} len={len(h)} text={len(t)} seen={m['retrieved_at']} raw={m['path']}\n  title={(title.group(1).strip()[:100] if title else '')}")
        if m["status"] != 200: continue
        pl = [k for k, v in PLAT.items() if re.search(v, h, re.I)]
        e = sm.find_embed(h)
        print(f"  platforms={pl} sightmap={e}")
        seen = set(); n = 0
        for mm in re.finditer(kw, t, re.I):
            s = t[max(0, mm.start() - width): mm.end() + width].strip()
            key = s[20:60]
            if key in seen: continue
            if any(abs(mm.start() - p) < width for p in seen if isinstance(p, int)): continue
            seen.add(key); seen.add(mm.start()); n += 1
            print("   ~", s)
            if n >= 14: break
        pr = sorted({int(x.replace(",", "")) for x in re.findall(r"\$\s?(\d,\d{3})", t)})
        print(f"  prices={pr[:25]}")
        if links:
            ls = sorted(set(re.findall(r'href="([^"#]+)"', h)))
            ls = [x for x in ls if re.search(r"floor|avail|pet|ameni|faq|apart|resid|sightmap|securecafe|feature|neigh|lease|rent|propert|communit", x, re.I) and not re.search(r"\.(css|js|png|jpg|svg|woff)", x)]
            print("  links:", ls[:60])
main()
