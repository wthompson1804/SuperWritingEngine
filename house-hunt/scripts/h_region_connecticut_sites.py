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

from h_mgmt_common import DOG_YES, DOG_NO
WEIGHT = re.compile(r"(?i)\b\d{2,3}\s*(?:-\s*)?(?:lbs?\b|pounds?\b|lb\.)|no (?:weight|size) (?:limit|restriction)|weight (?:limit|restriction)s?")
ELEV = re.compile(r"(?i)elevator")
STORIES = re.compile(r"(?i)\b(\d{1,2}|four|five|six|seven|eight|nine|ten|eleven|twelve)[- ]stor(?:y|ies)\b|\b\d{1,2} floors\b|high[- ]rise|mid[- ]rise")

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
        if urlparse(u).netloc.replace("www.", "") == host.replace("www.", "") and u.rstrip("/") != site and u not in links: links.append(u)
    links.sort(key=lambda u: (0 if re.search("pet", u, re.I) else 1 if re.search("faq", u, re.I) else 2))
    for u in links[:6]:
        try:
            h2, m2 = polite_get(u, SRC)
        except BotWall as e:
            rec["pages"].append({"url": u, "blocked": str(e)[:100]}); continue
        except Exception as e:
            continue
        if m2["status"] == 200: pages.append((u, h2, m2))
    facts = {"dog_yes": [], "dog_no": [], "weights": [], "elevator": [], "stories": []}
    for u, hh, mm in pages:
        t = strip_tags(hh)
        for key, rx in (("dog_yes", DOG_YES), ("dog_no", DOG_NO), ("weights", WEIGHT), ("elevator", ELEV), ("stories", STORIES)):
            for mm2 in list(rx.finditer(t))[:3]:
                c = t[max(0, mm2.start() - 120): mm2.end() + 120].strip()
                if all(c[40:100] not in x["text"] for x in facts[key]): facts[key].append({"url": u, "seen": mm["retrieved_at"], "text": c})
    rec["facts"] = facts
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
        for s in ([] if "--facts" in sys.argv else p.get("snips", [])):
            k = s[30:90]
            if k in seen: continue
            seen.add(k); print("      ~", s[:260])
    if "--facts" in sys.argv:
        for k, v in (rec.get("facts") or {}).items():
            for x in v[:3]: print(f"      [{k}] {x['text'][:250]}  <{x['url']}>")

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
