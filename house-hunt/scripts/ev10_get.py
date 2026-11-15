"""Evidence batch 10 helper: robots-checked, throttled fetch of a page; prints keyword context.
usage: python3 scripts/ev10_get.py [--refresh] [--kw regex] [--all] URL..."""
import re, sys, json, html as H
from urllib.parse import urlparse
from urllib import robotparser
sys.path.insert(0, "scripts")
import lib
lib.DEFAULT_DELAY = 2.5
SRC = "evidence_b10"
AGENTS = ["ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai", "house-hunt-research"]
_rp = {}
def robots(url):
    p = urlparse(url); base = f"{p.scheme}://{p.netloc}"
    if base not in _rp:
        try:
            c, m = lib.cached_get(base + "/robots.txt", SRC, ext="txt", retries=1, timeout=30)
        except Exception as e:
            _rp[base] = ("err", str(e)); return _rp[base]
        if m["status"] in (401, 403):
            _rp[base] = ("blocked", m["status"])
        elif m["status"] != 200:
            _rp[base] = ("none", m["status"])
        else:
            t = c.decode("utf8", "replace")
            if re.search(r"<html|Just a moment", t[:500], re.I): _rp[base] = ("none", "html")
            else:
                rp = robotparser.RobotFileParser(); rp.parse(t.splitlines()); _rp[base] = ("ok", rp)
    return _rp[base]
def allowed(url):
    st, rp = robots(url)
    if st == "blocked": return False, f"robots.txt HTTP {rp}"
    if st != "ok": return True, f"no robots ({rp})"
    for a in AGENTS:
        if not rp.can_fetch(a, url): return False, f"disallowed for {a}"
    cd = max([rp.crawl_delay(a) or 0 for a in AGENTS + ["*"]])
    if cd: lib.HOST_DELAY[urlparse(url).netloc] = max(2.5, float(cd))
    return True, f"ok crawl-delay={cd}"
def text_of(b):
    t = b.decode("utf8", "replace")
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", H.unescape(t))
def get(url, refresh=False):
    ok, why = allowed(url)
    if not ok: return None, {"status": "robots", "why": why, "url": url}
    try:
        c, m = lib.cached_get(url, SRC, ext="html", refresh=refresh, retries=2, timeout=40)
    except Exception as e:
        return None, {"status": "error", "why": str(e)[:200], "url": url}
    if m["status"] == 200 and re.search(r"px-captcha|cf-challenge|Just a moment\.\.\.|Access Denied|captcha-delivery", c[:30000].decode("utf8", "replace"), re.I):
        m = dict(m, status="challenge")
    return c, m
if __name__ == "__main__":
    a = sys.argv[1:]; refresh = "--refresh" in a; allt = "--all" in a
    kw = r"\b(pets?|dogs?|lbs?|pounds?|weight|breed|elevators?|stor(?:y|ies)|floors?|parking|garage|pool|doorman|concierge|managed by|built in)\b"
    if "--kw" in a: kw = a[a.index("--kw") + 1]; a.remove(kw)
    for u in [x for x in a if x.startswith("http")]:
        c, m = get(u, refresh)
        print("##", u, m.get("status"), m.get("why", ""), m.get("retrieved_at", ""), len(c or b""))
        if not c or m["status"] != 200: 
            if c: print(text_of(c)[:300])
            continue
        t = text_of(c)
        if allt: print(t[:6000]); continue
        seen = []; last = -999
        for mm in re.finditer(kw, t, re.I):
            if mm.start() < last + 160: continue
            last = mm.start(); s = t[max(0, mm.start() - 140):mm.start() + 220]
            if s[:60] in seen: continue
            seen.append(s[:60]); print("  ..", s)
            if len(seen) > 40: break
