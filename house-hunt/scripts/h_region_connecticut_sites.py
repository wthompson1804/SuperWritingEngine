"""Connecticut region pass, stage 2: read each building's own leasing site (URL from Apartment List's website_url or
from the hand list EXTRA below) for pet policy, elevator, floors, parking. Robots-checked, >= 2 s per host, stops at
bot walls (recorded as blocked). Output: raw/region_connecticut/site_facts.jsonl (snippets, one JSON per building).
Usage: python3 h_region_connecticut_sites.py [--show] [name-substring ...]
"""
import json, re, sys
from urllib.parse import urljoin, urlparse
from h_mgmt_common import polite_get, BotWall, strip_tags
import h_mgmt_sightmap as sm
import lib

SRC = "region_connecticut"
D = lib.RAW / SRC
AL = D / "al_buildings.jsonl"
OUT = D / "site_facts.jsonl"
EXTRA = D / "extra_sites.txt"   # name|url lines for buildings found by other means
KW = re.compile(r"elevator|\bdogs?\b|\bpets?\b|\blbs?\b|pounds|weight limit|breed|\bstor(?:y|ies)\b|\d+ floors|garage|parking|canine|bark", re.I)
LINK = re.compile(r"pet|faq|amenit|feature|polic", re.I)
PLAT = {"rentcafe": r"rentcafe|securecafe", "entrata": r"entrata|prospectportal", "realpage": r"realpage|onsite\.com|leasestar", "appfolio": r"appfolio",
        "knock": r"knockrentals|knockcrm|utm_knock", "funnel": r"funnelleasing|nestio", "engrain": r"sightmap|engrain", "yardi_nwg": r"nwgapi"}

def snips(t, width=110, cap=18):
    out, last = [], -10**9
    for m in KW.finditer(t):
        if m.start() - last < width: continue
        last = m.start()
        out.append(t[max(0, m.start() - width): m.end() + width].strip())
        if len(out) >= cap: break
    return out

def clean(u):
    u = u.split("?")[0].rstrip("/")
    if u.startswith("http://"): u = "https://" + u[7:]
    return u

def do(name, site):
    rec = {"name": name, "site": site, "pages": [], "sightmap": "", "platforms": [], "blocked": ""}
    try:
        h, m = polite_get(site, SRC)
    except BotWall as e:
        rec["blocked"] = str(e)[:120]; return rec
    except Exception as e:
        rec["blocked"] = "fetch error: " + str(e)[:120]; return rec
    if m["status"] != 200:
        rec["blocked"] = f"HTTP {m['status']}"; return rec
    host = urlparse(site).netloc
    pages = [(site, h, m)]
    links = []
    for l in re.findall(r'href="([^"#]+)"', h):
        if not LINK.search(l) or re.search(r"\.(css|js|png|jpe?g|svg|pdf|ico|woff2?)(\?|$)|privacy|cookie|wp-json|wp-content|xmlrpc|feed", l, re.I): continue
        u = clean(urljoin(site + "/", l))
        if urlparse(u).netloc == host and u != site and u not in links: links.append(u)
    for u in links[:5]:
        try:
            h2, m2 = polite_get(u, SRC)
        except BotWall as e:
            rec["pages"].append({"url": u, "blocked": str(e)[:100]}); continue
        except Exception as e:
            continue
        if m2["status"] == 200: pages.append((u, h2, m2))
    for u, hh, mm in pages:
        t = strip_tags(hh)
        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", hh)
        e = sm.find_embed(hh)
        if e: rec["sightmap"] = e
        for k, v in PLAT.items():
            if re.search(v, hh, re.I) and k not in rec["platforms"]: rec["platforms"].append(k)
        pr = sorted({int(x.replace(",", "")) for x in re.findall(r"\$\s?(\d,\d{3})", t)})
        rec["pages"].append({"url": u, "seen": mm["retrieved_at"], "raw": mm["path"], "title": (title.group(1).strip()[:90] if title else ""),
                             "textlen": len(t), "snips": snips(t), "prices": pr[:12]})
    return rec

def show(rec):
    print(f"## {rec['name']} | {rec['site']} | plat={rec['platforms']} sm={rec['sightmap']} blocked={rec['blocked']}")
    seen = set()
    for p in rec["pages"]:
        print(f"  - {p['url']} [{p.get('seen','')}] {p.get('title','')} textlen={p.get('textlen')} prices={p.get('prices')} {p.get('blocked','')}")
        for s in p.get("snips", []):
            k = s[30:90]
            if k in seen: continue
            seen.add(k); print("      ~", s[:260])

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    done = {}
    if OUT.exists():
        for l in open(OUT):
            r = json.loads(l); done[r["name"]] = r
    todo = []
    if AL.exists() and "--extra" not in sys.argv:
        for l in open(AL):
            d = json.loads(l)
            if d["website"]: todo.append((d["name"], clean(d["website"])))
    if EXTRA.exists():
        for l in EXTRA.read_text().splitlines():
            if "|" in l and not l.startswith("#"):
                n, u = l.split("|", 1); todo.append((n.strip(), clean(u.strip())))
    for name, site in todo:
        if args and not any(a.lower() in name.lower() for a in args): continue
        if name not in done:
            if "--show" in sys.argv and "--fetch" not in sys.argv: continue
            rec = do(name, site)
            done[name] = rec
            with open(OUT, "a") as f: f.write(json.dumps(rec) + "\n")
        if "--show" in sys.argv: show(done[name])
    print("sites recorded:", len(done), "blocked:", sum(1 for r in done.values() if r["blocked"]))
main()
