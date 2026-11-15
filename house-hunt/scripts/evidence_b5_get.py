"""Evidence batch 5 helper: robots-checked, cached, throttled page fetch -> visible text.
usage: evidence_b5_get.py URL [regex] [context_chars]   (prints matches of regex with context, or the head of the text)"""
import json, re, sys, html as H, urllib.robotparser as RP
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).parent))
import lib
E = lib.RAW / "evidence_b5"
AGENTS = ["Claude-User", "ClaudeBot", "Claude-SearchBot", "anthropic-ai", "house-hunt-research"]
OFF = ("yelp.", "niche.com", "city-data", "reddit.", "nextdoor.", "zillow.", "streeteasy.", "apartments.com", "apartmentratings", "google.")

def robots_ok(url):
    p = urlparse(url); host = p.netloc
    if any(o in host for o in OFF): return False, "off-limits source"
    lib.HOST_DELAY.setdefault(host, 2.5)
    try:
        c, m = lib.cached_get(f"{p.scheme}://{host}/robots.txt", "evidence_b5", ext="txt")
    except Exception as e:
        return False, f"robots fetch failed {e}"
    if m["status"] in (403, 429): return False, f"robots.txt HTTP {m['status']}"
    if m["status"] != 200: return True, f"robots.txt HTTP {m['status']} (treated as none)"
    rp = RP.RobotFileParser(); rp.parse(c.decode(errors="replace").splitlines())
    for a in AGENTS:
        if not rp.can_fetch(a, url): return False, f"robots disallows for {a}"
    d = rp.crawl_delay("Claude-User") or rp.crawl_delay("*")
    if d: lib.HOST_DELAY[host] = max(lib.HOST_DELAY[host], float(d))
    return True, "ok"

def text_of(url):
    ok, why = robots_ok(url)
    if not ok: return None, {"status": "blocked", "why": why}
    c, m = lib.cached_get(url, "evidence_b5", ext="html")
    t = c.decode(errors="replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", t, flags=re.S)
    t = H.unescape(re.sub(r"<[^>]+>", "\n", t))
    t = re.sub(r"[ \t\r]+", " ", t); t = re.sub(r"\n\s*\n+", "\n", t)
    return t, m

if __name__ == "__main__":
    url = sys.argv[1]; rx = sys.argv[2] if len(sys.argv) > 2 else None; ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    t, m = text_of(url)
    print("META", json.dumps(m))
    if t is None: sys.exit(0)
    if m.get("status") != 200: print(t[:300]); sys.exit(0)
    if not rx: print(t[:4000]); sys.exit(0)
    seen = -1
    for mm in re.finditer(rx, t, re.I):
        if mm.start() < seen: continue
        print("...", t[max(0, mm.start() - ctx): mm.end() + ctx].replace("\n", " | "), "...\n"); seen = mm.end() + ctx
