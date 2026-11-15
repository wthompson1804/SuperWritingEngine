"""Polite probe helper for Job B (non-NYC record sources): robots check (Claude-named groups override *), >= 2.5 s per
host, cache in raw/non_nyc_records/. Usage: python3 scripts/non_nyc_probe.py URL [URL ...]  -> status, bytes, title."""
import re, sys, json
from pathlib import Path
from urllib.parse import urlparse
from urllib import robotparser
sys.path.insert(0, str(Path(__file__).parent))
import lib
lib.DEFAULT_DELAY = 2.5
SRC = "non_nyc_records"
_rp = {}
AGENTS = ["Claude-User", "ClaudeBot", "Claude-SearchBot", "anthropic-ai", "Claude-Web", "house-hunt-research"]


def robots(url):
    p = urlparse(url); base = f"{p.scheme}://{p.netloc}"
    if base not in _rp:
        try:
            c, m = lib.cached_get(base + "/robots.txt", SRC, ext="txt", retries=1, timeout=30)
            txt = c.decode(errors="replace") if m["status"] == 200 else ""
            st = m["status"]
        except Exception as e:
            txt, st = "", "ERR"
        if st == 200 and "<html" in txt[:500].lower():
            txt = ""
        rp = robotparser.RobotFileParser(); rp.parse(txt.splitlines())
        _rp[base] = (rp, st, txt)
    rp, st, txt = _rp[base]
    if st in (401, 403):
        return False, f"robots.txt -> {st}"
    named = [a for a in AGENTS[:5] if re.search(rf"user-agent:\s*{a}", txt, re.I)]
    for a in (named or ["*"]):
        if not rp.can_fetch(a, url):
            return False, f"robots disallows for {a}"
    cd = rp.crawl_delay(named[0] if named else "*")
    if cd:
        lib.HOST_DELAY[p.netloc] = max(float(cd), 2.5)
    return True, f"robots {st}" + (f"; named groups {named}" if named else "")


def get(url, ext="html", **kw):
    ok, why = robots(url)
    if not ok:
        return None, {"status": "robots", "why": why, "url": url}
    try:
        c, m = lib.cached_get(url, SRC, ext=ext, retries=1, timeout=45, **kw)
    except Exception as e:
        return None, {"status": "ERR", "why": repr(e)[:160], "url": url}
    m = dict(m, why=why)
    return c, m


if __name__ == "__main__":
    for u in sys.argv[1:]:
        c, m = get(u, ext="json" if ("json" in u or "api" in u) else "html")
        t = (c or b"").decode(errors="replace")
        ti = re.search(r"<title[^>]*>(.*?)</title>", t, re.S)
        print(json.dumps([u, m.get("status"), len(t), m.get("why"), (ti.group(1).strip()[:80] if ti else t[:300])]))
