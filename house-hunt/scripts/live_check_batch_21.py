"""Live check batch 21: re-read of the 45 apartments at or under $2,000 listed rent (the concierge page), from each
building's own site, its manager's site, or an allowed listing site. No Trulia requests.

  python3 scripts/live_check_batch_21.py get <url> [<url> ...]   fetch (cached, robots-checked, 3 s apart) and print a summary
  python3 scripts/live_check_batch_21.py text <url>              print the cached page as plain text
  python3 scripts/live_check_batch_21.py write                   rebuild data/evidence/live_check_batch_21.csv (no network)

Every response is cached in raw/live_check_b21/. A 401, 403, 429 or bot wall is written to raw/_host_kill_shared.json
and the host is never asked again. Findings (what a person read on each cached page) are in
scripts/live_check_batch_21_rows.json; `write` only joins them to the 45 units and to the cache's retrieval times.
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

SRC = "live_check_b21"
BY = "live_check_batch_21"
KILL = lib.RAW / lib.KILL_FILE_NAME
DELAY = 3.0
UA_NAMES = ["Claude-User", "ClaudeBot", "anthropic-ai", "Claude-Web", "claude"]
_last: dict[str, float] = {}
_robots: dict[str, object] = {}
WALL = re.compile(r"captcha|are you a human|attention required|access denied|just a moment\.\.\.|px-captcha|incapsula incident|"
                  r"request unsuccessful|verify you are human|unusual traffic", re.I)


def kill(host: str, reason: str, url: str) -> None:
    try:
        k = json.loads(KILL.read_text())
    except (OSError, ValueError):
        k = {}
    if host not in k:
        k[host] = {"reason": reason, "url": url, "at": lib.now_iso(), "by": BY}
        KILL.write_text(json.dumps(k, indent=1))


def _wait(host: str) -> None:
    w = _last.get(host, 0) + DELAY - time.time()
    if w > 0:
        time.sleep(w)
    _last[host] = time.time()


def _raw(url: str, ext: str):
    """One request, no retry. Returns (content or None, status text)."""
    host = urlparse(url).netloc
    try:
        lib.check_host(url)
    except lib.HostRefused as e:
        return None, f"not requested: {e}"
    cached = True
    try:
        # cache hit returns at once; otherwise one try only (a 429 must not be retried)
        key_exists = None
        _wait(host)
        content, meta = lib.cached_get(url, SRC, ext=ext, retries=1, timeout=45,
                                       headers={"Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"})
    except RuntimeError as e:
        m = re.search(r"HTTP (\d+)", str(e))
        if m and m.group(1) == "429":
            kill(host, "HTTP 429", url)
            return None, "HTTP 429 (host ended)"
        return None, f"fetch failed: {str(e)[-200:]}"
    st = meta["status"]
    if st in (401, 403, 429):
        kill(host, f"HTTP {st}", url)
        return None, f"HTTP {st} (host ended)"
    if st != 200:
        return None, f"HTTP {st}"
    head = content[:6000].decode("utf-8", "replace")
    if len(content) < 20000 and WALL.search(head):
        kill(host, "bot wall page served (HTTP 200)", url)
        return None, "bot wall (host ended)"
    return content, f"200 at {meta['retrieved_at']}"


def robots_ok(url: str):
    p = urlparse(url)
    host = p.netloc
    if host not in _robots:
        body, st = _raw(f"{p.scheme}://{host}/robots.txt", "txt")
        if body is None:
            _robots[host] = st if "ended" in st or "not requested" in st else None  # no robots file: allowed
        else:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(body.decode("utf-8", "replace").splitlines())
            _robots[host] = rp
    r = _robots[host]
    if r is None:
        return True, "no robots.txt"
    if isinstance(r, str):
        return False, f"robots.txt: {r}"
    txt = (lib.RAW / SRC).exists() and ""  # noqa
    # a group naming Claude overrides *: RobotFileParser picks the first matching named entry, else *
    named = [e for e in r.entries if any(any(n.lower() in a.lower() for n in UA_NAMES) for a in e.useragents)]
    ua = "Claude-User" if any("claude-user" in a.lower() for e in named for a in e.useragents) else ("ClaudeBot" if named else "house-hunt-research")
    return r.can_fetch(ua, url), f"robots group used: {ua if named else '*'}"


def get(url: str, ext: str = "html"):
    ok, why = robots_ok(url)
    if not ok:
        return None, f"robots disallow ({why})"
    return _raw(url, ext)


def to_text(content: bytes) -> str:
    s = content.decode("utf-8", "replace")
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|td|th|section|article)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    import html
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


COLS = ["addr_key", "listing_url", "unit", "status", "price_now", "available_now_text", "matches_stored", "building_site_url", "checked_at", "notes"]


def write() -> None:
    rows = json.loads((Path(__file__).with_name("live_check_batch_21_rows.json")).read_text())
    out = lib.DATA / "evidence" / "live_check_batch_21.csv"
    tmp = out.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    tmp.replace(out)
    print(len(rows), "rows ->", out)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "get":
        for u in sys.argv[2:]:
            c, st = get(u, "json" if "json" in u or "/api/" in u else "html")
            print(u, "->", st, "| bytes", len(c) if c else 0)
            if c:
                t = to_text(c)
                print("   title:", (re.search(r"(?is)<title[^>]*>(.*?)</title>", c.decode('utf-8', 'replace')) or [0, ""])[1].strip()[:120], "| text chars", len(t))
    elif cmd == "text":
        c, st = get(sys.argv[2])
        print(st)
        print(to_text(c) if c else "")
    elif cmd == "write":
        write()
    else:
        print(__doc__)
