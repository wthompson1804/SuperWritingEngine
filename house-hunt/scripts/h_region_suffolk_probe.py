"""Suffolk region pass: polite fetch (robots checked, >= 2 s/host, cached in raw/region_suffolk) of leasing-site pages,
printing keyword contexts so facts can be hand-read.  usage: h_region_suffolk_probe.py [-l] [-k regex] [-w width] url..."""
import re, sys, html as H
from pathlib import Path
from urllib.parse import urljoin, urlparse
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
from h_mgmt_common import polite_get, BotWall, strip_tags, set_delay
SRC = "region_suffolk"
KW = r"elevator|walk[- ]?up|\bstor(y|ies)\b|\bfloors?\b|\bpets?\b|\bdogs?\b|breed|\blbs?\b|pound|weight|parking|garage|special|free\b|concession|\$\s?\d[\d,]{2,}|studio|doorman|concierge|pool|built|utilit|income|afford|55\+|62\+|senior|available"
def main():
    a = sys.argv[1:]; links = False; kw = KW; w = 90; full = False
    while a and a[0].startswith("-"):
        f = a.pop(0)
        if f == "-l": links = True
        elif f == "-k": kw = a.pop(0)
        elif f == "-w": w = int(a.pop(0))
        elif f == "-f": full = True
    for u in a:
        host = urlparse(u).netloc
        lib.HOST_DELAY.setdefault(host, 2.0)
        try:
            t, m = polite_get(u, SRC)
        except BotWall as e:
            print("## BOTWALL", u, e); continue
        except Exception as e:
            print("## ERR", u, repr(e)[:200]); continue
        title = re.search(r"(?is)<title[^>]*>(.*?)</title>", t)
        txt = re.sub(r"\s+", " ", H.unescape(strip_tags(t)))
        print(f"## [{m['status']}] {u} | {m['retrieved_at']} | {m.get('path')} | title={title.group(1).strip()[:90] if title else ''} | textlen={len(txt)}")
        if m["status"] != 200: continue
        if full:
            print(txt[:w * 100]); continue
        last = -1
        for mm in re.finditer("(?i)" + kw, txt):
            if mm.start() < last: continue
            s, e = max(0, mm.start() - w), min(len(txt), mm.end() + w)
            print("   ..", txt[s:e]); last = e
        emb = set(re.findall(r'https?://[^"\'\s<>\\]*(?:sightmap|securecafe|rentcafe|entrata|appfolio|buildium|yardi|engrain|knock|realpage|on-site|loftliving|apartments\.com|zillow|streeteasy)[^"\'\s<>\\]*', t))
        for x in sorted(emb)[:8]: print("   EMBED", x[:160])
        if links:
            ls = sorted({urljoin(u, x).split("#")[0] for x in re.findall(r'href=["\']([^"\']+)', t)})
            print("   LINKS", [x for x in ls if urlparse(x).netloc.replace("www.", "") == host.replace("www.", "") and not re.search(r"\.(css|js|png|jpg|svg|ico|woff2?)(\?|$)", x)][:60])
main()
