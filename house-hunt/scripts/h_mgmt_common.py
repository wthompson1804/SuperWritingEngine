"""Shared helpers for the property-management harvest scripts (h_mgmt_<company>.py).

- COLS: the harvest CSV contract (docs/HARVEST_AGENT_BRIEF.md).
- upsert(): idempotent CSV write keyed by listing_id; keeps first_seen, updates last_seen.
- robots_ok(): robots.txt check that lets Claude-named groups override `*`.
- polite_get(): lib.cached_get with a per-host minimum delay (>= 2 s, or the site's Crawl-delay),
  and a hard stop (BotWall) on 403 / 429 / challenge pages.
- grid(): search-grid ZIPs -> drive minutes.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib import robotparser

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

ROOT = lib.ROOT
OUT_DIR = ROOT / "data" / "listings_raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)
lib.DEFAULT_DELAY = max(lib.DEFAULT_DELAY, 2.0)  # brief: minimum 2 s between requests to a host

COLS = ("listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,"
        "unit,beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,"
        "dog_policy_text,dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,"
        "other_monthly_fees_json,utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,"
        "building_url,raw_path,notes").split(",")

CLAUDE_AGENTS = ["Claude-User", "ClaudeBot", "Claude-SearchBot", "anthropic-ai", "Claude-Web"]


class BotWall(RuntimeError):
    pass


def set_delay(host: str, seconds: float) -> None:
    lib.HOST_DELAY[host] = max(2.0, seconds)


_robots: dict[str, tuple[robotparser.RobotFileParser | None, str]] = {}


def robots(host: str, source: str):
    """Return (parser or None, raw text). Parser None means robots.txt absent (404): no rules."""
    if host in _robots:
        return _robots[host]
    c, m = lib.cached_get(f"https://{host}/robots.txt", source, ext="txt")
    if m["status"] in (401, 403, 429):
        raise BotWall(f"robots.txt blocked ({m['status']}) on {host}")
    if m["status"] != 200:
        _robots[host] = (None, "")
        return _robots[host]
    txt = c.decode("utf8", "ignore")
    if "<html" in txt[:500].lower():
        _robots[host] = (None, "")
        return _robots[host]
    rp = robotparser.RobotFileParser()
    rp.parse(txt.splitlines())
    _robots[host] = (rp, txt)
    return _robots[host]


def robots_ok(url: str, source: str) -> bool:
    host = urlparse(url).netloc
    rp, txt = robots(host, source)
    if rp is None:
        return True
    low = txt.lower()
    named = [a for a in CLAUDE_AGENTS if re.search(r"user-agent:\s*" + re.escape(a.lower()), low)]
    if named:
        return all(rp.can_fetch(a, url) for a in named)
    return rp.can_fetch("*", url)


def crawl_delay(host: str, source: str) -> float:
    _, txt = robots(host, source)
    m = re.search(r"(?im)^\s*crawl-delay:\s*([\d.]+)", txt)
    return float(m.group(1)) if m else 0.0


CHALLENGE = re.compile(r"Just a moment\.\.\.|cf-chl|captcha-delivery|px-captcha|Access Denied|Are you a robot", re.I)


def polite_get(url: str, source: str, *, ext: str = "html", refresh: bool = False, check_robots: bool = True,
               **kw) -> tuple[str, dict]:
    host = urlparse(url).netloc
    if check_robots:
        if not robots_ok(url, source):
            raise BotWall(f"robots.txt disallows {url}")
        cd = crawl_delay(host, source)
        if cd:
            set_delay(host, cd)
    c, m = lib.cached_get(url, source, ext=ext, refresh=refresh, **kw)
    if m["status"] in (401, 403, 429):
        raise BotWall(f"HTTP {m['status']} at {url}")
    t = c.decode("utf8", "ignore")
    if m["status"] == 200 and len(t) < 20000 and CHALLENGE.search(t):
        raise BotWall(f"challenge page at {url}")
    return t, m


def grid() -> dict[str, float]:
    with open(ROOT / "data" / "reference" / "search_grid.csv") as f:
        return {r["zcta"].zfill(5): float(r["drive_min"]) for r in csv.DictReader(f)}


def upsert(csv_path: Path, rows: list[dict]) -> int:
    """Merge rows into csv_path by listing_id. Existing first_seen is kept. Returns total rows."""
    old: dict[str, dict] = {}
    if csv_path.exists():
        with open(csv_path, newline="") as f:
            for r in csv.DictReader(f):
                old[r["listing_id"]] = r
    for r in rows:
        r = {k: ("" if r.get(k) is None else r.get(k)) for k in COLS}
        if r["listing_id"] in old and old[r["listing_id"]].get("first_seen"):
            r["first_seen"] = old[r["listing_id"]]["first_seen"]
        old[r["listing_id"]] = r
    tmp = csv_path.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in old.values():
            w.writerow({k: r.get(k, "") for k in COLS})
    tmp.replace(csv_path)
    return len(old)


def strip_tags(html: str) -> str:
    t = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8217;", "'").replace("&#039;", "'")
    return re.sub(r"\s+", " ", t)


def weight_limit(text: str) -> str:
    """Largest dog weight limit stated in text ('50 lb', '75 pounds'), else ''. Never guessed."""
    if not text:
        return ""
    if re.search(r"(?i)no (weight|size) (limit|restriction)", text):
        return "none"
    v = [int(x) for x in re.findall(r"(?i)(\d{2,3})\s*(?:-\s*)?(?:lbs?\b|pounds?\b|lb\.)", text)]
    return str(max(v)) if v else ""


def fill_rates(csv_path: Path) -> dict:
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))
    n = len(rows) or 1
    def known(k):
        return sum(1 for r in rows if r[k] not in ("", "unknown")) / n
    return {"rows": len(rows), **{k: round(known(k), 2) for k in
            ("dogs", "dog_weight_limit_lb", "elevator", "floor", "building_floors", "available_date", "sqft",
             "parking_fee", "pet_rent", "utilities_included")}}


def jdump(o) -> str:
    return json.dumps(o, separators=(",", ":"), ensure_ascii=False)
