"""Low-volume reader for trawl 2 step 2 (Trulia card -> building's own site). One page per call.

  python3 scripts/trulia_match_fetch.py <url> [<url> ...]

For each URL: refuses off-limits hosts (lib.check_host plus the step's own list: RentCafe/securecafe, Entrata
prospectportal, AppFolio, RealtyMX, Trulia), reads robots.txt once per host (Claude-User group if present, else *),
throttles 3 s per host, sends one request (no retry on a refusal), and on 401/403/429 or a bot wall records the host in
raw/_host_kill_shared.json and in raw/trulia_matches/_refused.json. The page is cached in raw/trulia_matches/ and its
visible text written next to it (.txt) for reading. Every request is logged to raw/trulia_matches/_requests.jsonl.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.robotparser as rp
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

SRC = "trulia_matches"
D = lib.RAW / SRC
D.mkdir(parents=True, exist_ok=True)
REFUSED = D / "_refused.json"
LOG = D / "_requests.jsonl"
BLOCK = ("rentcafe.com", "securecafe.com", "prospectportal.com", "entrata.com", "appfolio.com", "realtymx.com",
         "trulia.com", "zillow.com", "streeteasy.com", "apartments.com", "realtor.com", "rent.com", "hotpads.com",
         "renthop.com", "apartmentratings.com", "craigslist.org", "yelp.com")
WALL = re.compile(r"(captcha|cf-chl|challenge-platform|access denied|attention required|incapsula|"
                  r"are you a human|px-captcha|_Incapsula_Resource|verify you are human)", re.I)
_robots: dict[str, rp.RobotFileParser | None] = {}


def log(rec):
    with open(LOG, "a") as f:
        f.write(json.dumps({**rec, "at": lib.now_iso()}) + "\n")


def refuse(host, url, reason):
    kill = json.loads((lib.RAW / lib.KILL_FILE_NAME).read_text())
    kill[host] = {"reason": reason, "url": url, "at": lib.now_iso(), "by": "trulia_card_matches"}
    (lib.RAW / lib.KILL_FILE_NAME).write_text(json.dumps(kill, indent=1))
    own = json.loads(REFUSED.read_text()) if REFUSED.exists() else {}
    own[host] = kill[host]
    REFUSED.write_text(json.dumps(own, indent=1))


def visible_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|td|th|section|article)>", "\n", html)
    t = re.sub(r"<[^>]+>", " ", html)
    t = re.sub(r"&nbsp;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def robots_ok(url) -> bool:
    p = urlparse(url)
    host = p.netloc.lower()
    if host not in _robots:
        r = rp.RobotFileParser()
        rurl = f"{p.scheme}://{host}/robots.txt"
        try:
            lib._throttle(host)
            content, meta = lib.cached_get(rurl, SRC, ext="txt", retries=1, timeout=30)
            log({"url": rurl, "status": meta["status"]})
            if meta["status"] in (401, 403, 429):
                refuse(host, rurl, f"HTTP {meta['status']} on robots.txt")
                _robots[host] = None
                return False
            if meta["status"] == 200:
                r.parse(content.decode("utf-8", "replace").splitlines())
            else:
                r.parse([])
        except Exception as e:  # unreachable robots: treat as no robots file, but log it
            log({"url": rurl, "error": repr(e)[:200]})
            r.parse([])
        _robots[host] = r
    r = _robots[host]
    if r is None:
        return False
    agent = "Claude-User"
    return r.can_fetch(agent, url)


def fetch(url):
    host = urlparse(url).netloc.lower()
    if any(lib._covers(b, host) for b in BLOCK):
        print(f"BLOCKED (off limits for this step): {url}")
        return
    why = lib.host_refusal(host)
    if why:
        print(f"REFUSED-HOST: {url}: {why}")
        return
    if not robots_ok(url):
        print(f"ROBOTS-DISALLOW or refused: {url}")
        log({"url": url, "skipped": "robots"})
        return
    lib.HOST_DELAY[host] = max(lib.HOST_DELAY.get(host, 0), 3.0)
    try:
        content, meta = lib.cached_get(url, SRC, ext="html", retries=1, timeout=45)
    except Exception as e:
        print(f"ERROR {url}: {e}")
        log({"url": url, "error": repr(e)[:200]})
        return
    st = meta["status"]
    html = content.decode("utf-8", "replace")
    log({"url": url, "status": st, "bytes": len(content), "path": meta.get("path")})
    if st in (401, 403, 429) or (st == 200 and len(html) < 5000 and WALL.search(html)):
        refuse(host, url, f"HTTP {st}" + (" bot wall" if st == 200 else ""))
        print(f"REFUSAL {st} from {host}; host recorded as refused")
        return
    if st != 200:
        print(f"HTTP {st}: {url}")
        return
    txt = Path(lib.ROOT / meta["path"]).with_suffix(".txt")
    txt.write_text(visible_text(html))
    print(f"OK {st} {len(content)}B retrieved_at={meta['retrieved_at']} text={txt}")


if __name__ == "__main__":
    for u in sys.argv[1:]:
        fetch(u)
        time.sleep(0.1)
