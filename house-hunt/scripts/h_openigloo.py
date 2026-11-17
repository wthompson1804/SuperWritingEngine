"""Openigloo (www.openigloo.com) listing harvest for Brooklyn and Long Island City: studios and 1BR at or under $2,200.

  python3 scripts/h_openigloo.py list     # walk /apartments/<area>/<beds>?page=N search pages (JSON-LD item lists)
  python3 scripts/h_openigloo.py detail   # open each unit page whose search price is <= $2,200
  python3 scripts/h_openigloo.py build    # write data/listings_raw/openigloo.csv from the cache (no network)
  python3 scripts/h_openigloo.py all

Access (probed 2026-11-17, docs/SOURCES.md "Trawl 2 new-source probe"): robots.txt has ClaudeBot and Claude-User groups
that allow everything except /api, /_nuxt, /internal and two /None paths; no crawl-delay. Terms of use (read
2026-11-17) have no clause on automated access; they bar copying or republishing the site's content, so only facts
(price, unit, dates, policies) are recorded, never descriptions or photos. 3.5 s between requests, honest user agent
(lib.cached_get), one try per URL, and any 401/403/429 or bot wall ends the host (raw/_host_kill_shared.json).
Price, date and facts come from the unit page itself; the search-page price only decides which unit pages to open.
"""
from __future__ import annotations

import csv
import html as htmlmod
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

SRC = "openigloo"
HOST = "www.openigloo.com"
BASE = f"https://{HOST}"
DELAY = 3.5
MAX_RENT = 2200
KILL = lib.RAW / lib.KILL_FILE_NAME
OUT = lib.DATA / "listings_raw" / "openigloo.csv"
CARDS = lib.RAW / SRC / "_cards.jsonl"
AREAS = [("brooklyn", "Brooklyn"), ("queens/long-island-city", "Long Island City")]
BEDS = [("studio", 0), ("1-bedroom", 1)]
DISALLOW = ("/api", "/_nuxt", "/internal", "/wp-admin", "/building/nyc/None", "/contact/nyc/None")
WALL = re.compile(r"captcha|are you a human|attention required|access denied|just a moment\.\.\.|px-captcha|"
                  r"verify you are human|unusual traffic|challenge-platform", re.I)
COLS = ["listing_id", "source_site", "url", "detail_level", "first_seen", "last_seen", "building_name", "address", "city",
        "state", "zip", "lat", "lon", "unit", "beds", "baths", "sqft", "listed_rent", "price_basis", "concession_text",
        "available_date_text", "available_date", "dogs", "dog_policy_text", "dog_weight_limit_lb", "elevator", "floor",
        "building_floors", "parking_type", "parking_fee", "pet_rent", "other_monthly_fees_json", "utilities_included",
        "laundry", "listing_type", "manager", "listing_age_days", "photo_url", "building_url", "raw_path", "notes"]
_last = [0.0]


class Stop(RuntimeError):
    pass


def kill(reason: str, url: str) -> None:
    try:
        k = json.loads(KILL.read_text())
    except (OSError, ValueError):
        k = {}
    if HOST not in k:
        k[HOST] = {"reason": reason, "url": url, "at": lib.now_iso(), "by": "scripts/h_openigloo.py"}
        KILL.write_text(json.dumps(k, indent=1))


def get(url: str) -> tuple[str | None, dict | None]:
    """Cached fetch, one try. Returns (text, meta) or (None, meta/None) on a non-200. Raises Stop on a refusal."""
    path = urlparse(url).path
    if any(path.startswith(d) for d in DISALLOW):
        return None, None
    lib.check_host(url)
    lib.HOST_DELAY[HOST] = DELAY
    try:
        content, meta = lib.cached_get(url, SRC, ext="html", retries=1, timeout=45,
                                       headers={"Accept": "text/html,application/xhtml+xml"})
    except RuntimeError as e:
        if "HTTP 429" in str(e):
            kill("HTTP 429", url)
            raise Stop(f"429 on {url}")
        print("  fetch failed:", str(e)[-150:])
        return None, None
    st = meta["status"]
    if st in (401, 403, 429):
        kill(f"HTTP {st}", url)
        raise Stop(f"HTTP {st} on {url}")
    if st != 200:
        return None, meta
    text = content.decode("utf-8", "replace")
    if len(content) < 30000 and WALL.search(text[:8000]):
        kill("bot wall page served (HTTP 200)", url)
        raise Stop(f"bot wall on {url}")
    return text, meta


def flight(text: str) -> str:
    out = []
    for c in re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', text, re.S):
        try:
            out.append(json.loads('"' + c + '"'))
        except ValueError:
            pass
    return "".join(out)


LISTING = re.compile(r'\{"listing":\{"id":"([0-9a-f-]{36})","slug":"([^"]+)","addressSlug":"([^"]+)","fullAddress":"([^"]+)",'
                     r'"numBedrooms":(\d+),"numBathrooms":([\d.]+)(?:(?!\{"listing":).)*?"activeListing":(\{[^{}]*\})', re.S)


def unit_url(slug: str, address_slug: str) -> str:
    return f"{BASE}/unit/nyc/{slug}/{address_slug}"


def cmd_list() -> None:
    """Search pages carry each card's listing object: gross rent (the listed rent), net rent (after a promotion,
    which is the JSON-LD "price"), promotion text, beds, baths. The JSON-LD url (/unit/brooklyn/<uuid>/...) 404s;
    the site's own links use /unit/nyc/<slug>/<addressSlug>."""
    CARDS.write_text("")
    with open(CARDS, "a") as f:
        for slug, area in AREAS:
            for bslug, beds in BEDS:
                page, pages = 1, 1
                while page <= pages:
                    url = f"{BASE}/apartments/{slug}/{bslug}" + (f"?page={page}" if page > 1 else "")
                    text, meta = get(url)
                    if text is None:
                        print("  no page", url, meta and meta.get("status"))
                        break
                    mx = [int(x) for x in re.findall(rf'/apartments/{re.escape(slug)}/{bslug}\?page=(\d+)', text)]
                    pages = max([pages] + mx)
                    n, ids = 0, set()
                    for m in LISTING.finditer(flight(text)):
                        if m.group(1) in ids:
                            continue
                        ids.add(m.group(1))
                        try:
                            al = json.loads(m.group(7))
                        except ValueError:
                            al = {}
                        rec = {"search": url, "seen_at": meta["retrieved_at"], "area": area, "id": m.group(1),
                               "url": unit_url(m.group(2), m.group(3)), "name": m.group(4), "beds": int(m.group(5)),
                               "baths": float(m.group(6)), "gross": al.get("grossRent"), "net": al.get("netRent"),
                               "promotion": al.get("promotion"), "future": al.get("isFutureListing")}
                        n += 1
                        f.write(json.dumps(rec) + "\n")
                    print(f"{area} {bslug} page {page}/{pages}: {n} cards")
                    if n == 0:
                        break
                    page += 1


def cards() -> dict:
    best = {}
    for line in CARDS.read_text().splitlines():
        r = json.loads(line)
        if r["beds"] not in (0, 1):
            continue
        best.setdefault(r["url"], r)
    return best


def cmd_detail() -> None:
    todo = [r for r in cards().values() if (r["gross"] or r["net"] or 10**6) <= MAX_RENT]
    print(len(todo), "unit pages at or under", MAX_RENT)
    for i, r in enumerate(todo):
        text, meta = get(r["url"])
        print(i + 1, r["gross"], r["name"], "ok" if text else (meta or {}).get("status"))


# ---- unit page parsing ------------------------------------------------------------------------------------------------

def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_unit(text: str) -> dict:
    fl = flight(text)
    d = {}
    # JSON-LD on the unit page
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, re.S):
        try:
            j = json.loads(m.group(1))
        except ValueError:
            continue
        for o in (j if isinstance(j, list) else [j]):
            if isinstance(o, dict) and "offers" in o:
                d["ld"] = o
    d["flight"] = fl
    return d


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    try:
        if cmd in ("list", "all"):
            cmd_list()
        if cmd in ("detail", "all"):
            cmd_detail()
    except Stop as e:
        print("STOPPED:", e)
        return
    if cmd in ("build", "all"):
        build()


def build() -> None:  # replaced below once the unit page layout is known
    raise SystemExit("build not written yet")


if __name__ == "__main__":
    main()
