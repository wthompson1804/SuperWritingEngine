"""Local rules, round 2: municipalities round 1 left empty, plus municipalities added to site/data.json since.

Reuses the fetch / robots / text helpers of scripts/local_rules_fetch.py (imported, not edited) but writes to its own
cache `raw/local_rules_round2/` and its own outputs:

  scripts/local_rules_round2_rows.jsonl   rows entered by hand after reading the cached page text
  data/reference/local_rules_round2.csv   same columns as local_rules.csv

Hard rule kept in code: a host that refused once (401 / 403 / 429 / bot wall, in round 1 or in this round) is
recorded in raw/local_rules_round2/_blocked_hosts.json and never requested again. ecode360, Municode, American Legal
and the other off-limits hosts are refused before any request.

Usage:
  python3 scripts/local_rules_round2.py munis                          list municipalities from site/data.json by shown units
  python3 scripts/local_rules_round2.py get <muni> <url> [...]         fetch pages, store text
  python3 scripts/local_rules_round2.py crawl <muni> <start_url> [max]
  python3 scripts/local_rules_round2.py sitemap <muni> <base_url> [max]
  python3 scripts/local_rules_round2.py links <url> [regex]
  python3 scripts/local_rules_round2.py grep <muni-or-url-substring> <regex> [width] [max_hits]
  python3 scripts/local_rules_round2.py pages <muni>
  python3 scripts/local_rules_round2.py build                          verify quotes, write the CSV
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
import local_rules_fetch as F  # noqa: E402

SRC = "local_rules_round2"
F.SRC = SRC
F.OUT = lib.RAW / SRC
F.TXT = F.OUT / "text"
F.TXT.mkdir(parents=True, exist_ok=True)
F.PAGES = F.OUT / "_pages.jsonl"
F.BLOCKED = F.OUT / "_blocked.jsonl"
F.PAGES.touch()
BLOCKED_HOSTS = F.OUT / "_blocked_hosts.json"
ROWS = lib.ROOT / "scripts/local_rules_round2_rows.jsonl"
OUT_CSV = lib.ROOT / "data/reference/local_rules_round2.csv"

OFF_LIMITS = ("ecode360.com", "municode.com", "amlegal.com", "reddit.com", "yelp.com", "nextdoor.com", "patch.com",
              "trulia.com", "zillow.com")
# Refused in round 1 (raw/local_rules/_blocked.jsonl): same working session, so still closed.
ROUND1_REFUSED = {
    "www.yonkersny.gov": "round 1: robots.txt HTTP 403 bot wall",
    "www.yonkersparkingauthority.com": "round 1: robots.txt HTTP 403 bot wall",
    "www.newarknj.gov": "round 1: robots.txt HTTP 403 bot wall",
    "www.montclairnjusa.org": "round 1: robots.txt HTTP 403 bot wall",
    "www.morrisplainsboro.org": "round 1: robots.txt HTTP 403 bot wall",
    "www.stamfordct.gov": "round 1: robots.txt HTTP 403 bot wall",
    "www.westportct.gov": "round 1: robots.txt HTTP 403 bot wall",
    "www.townofnewpaltz.org": "round 1: HTTP 403 bot wall",
    "www.nycgovparks.org": "round 1: HTTP 403 bot wall",
    "www.nysenate.gov": "round 1: HTTP 403 Cloudflare",
}


def _bare(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def load_blocked() -> dict:
    d = dict(ROUND1_REFUSED)
    if BLOCKED_HOSTS.exists():
        d.update(json.loads(BLOCKED_HOSTS.read_text()))
    return d


def save_blocked() -> None:
    d = load_blocked()
    for host, (kind, val) in F._robots.items():
        if kind == "blocked" and host not in d:
            d[host] = f"round 2 ({lib.now_iso()}): {val}"
    BLOCKED_HOSTS.write_text(json.dumps(d, indent=1, sort_keys=True))


_orig_robots_ok = F.robots_ok


def robots_ok(url: str):
    host = urlparse(url).netloc.lower()
    if any(_bare(host) == o or host.endswith("." + o) for o in OFF_LIMITS):
        return False, "off limits (project rule)"
    blocked = load_blocked()
    for h, why in blocked.items():
        if _bare(h) == _bare(host):
            return False, "host refused earlier: " + why
    ok, why = _orig_robots_ok(url)
    save_blocked()
    return ok, why


F.robots_ok = robots_ok
# Hosts whose /robots.txt is not a robots file (checked by hand): www.jerseycitynj.gov answers 301 -> plain-http
# /robots.txt/ -> /robots.txt/Default.aspx -> 404 "Page Not Found", i.e. no robots rules; pages load over https.
for _h in ("www.jerseycitynj.gov",):
    F._robots[_h] = ("none", "")
_orig_fetch = F.fetch


def fetch(muni, url, quiet=False):
    r = _orig_fetch(muni, url, quiet)
    save_blocked()
    return r


F.fetch = fetch

NYC_AREAS = {"Queens", "Brooklyn", "Manhattan", "Bronx", "Staten Island"}


def munis() -> list[dict]:
    d = json.loads((lib.ROOT / "site/data.json").read_text())
    r1 = {}
    for x in csv.DictReader(open(lib.ROOT / "data/reference/local_rules.csv")):
        if x["value_type"] == "found":
            for h in x["applies_to_hood_ids"].split(";"):
                r1[h] = r1.get(h, 0) + 1
    out = []
    for n in d["neighborhoods"]:
        if n["area"] in NYC_AREAS:
            continue
        out.append({"id": n["id"], "name": n["name"], "county": n["area"], "state": n["state"],
                    "shown": n["counts"].get("shown", 0), "round1_found": r1.get(n["id"], 0)})
    out.sort(key=lambda x: (-x["shown"], x["id"]))
    return out


COLS = ["municipality", "state", "applies_to_hood_ids", "topic", "rule", "summary", "quote", "source_url",
        "source_type", "retrieved_at", "value_type"]


def build() -> None:
    when = {}
    for l in F.PAGES.read_text().splitlines():
        r = json.loads(l)
        when.setdefault(r["url"], r["retrieved_at"])
    out, bad, seen = [], 0, set()
    for i, l in enumerate(ROWS.read_text().splitlines(), 1):
        if not l.strip():
            continue
        r = json.loads(l)
        key = (r["m"], r["rule"], r.get("url", ""), r.get("quote", "")[:60])
        if key in seen:
            continue
        seen.add(key)
        vt = r.get("vt", "found")
        if vt != "not_found":
            tp = F.text_path(r["url"])
            if not (tp.exists() and F.norm(r["quote"]) in F.norm(tp.read_text())):
                bad += 1
                print(f"QUOTE NOT VERIFIED line {i}: {r['m']} {r['rule']} :: {r['quote'][:90]}")
                continue
        out.append({"municipality": r["m"], "state": r["state"], "applies_to_hood_ids": r["hoods"], "topic": r["t"],
                    "rule": r["rule"], "summary": r["s"], "quote": r.get("quote", ""), "source_url": r.get("url", ""),
                    "source_type": r.get("st", "municipal page"),
                    "retrieved_at": when.get(r.get("url", ""), r.get("at", "")), "value_type": vt})
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(out)
    print(f"{OUT_CSV.name}: {len(out)} rows ({bad} rejected)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    a = sys.argv[2:]
    if cmd == "munis":
        for m in munis():
            print(m["shown"], m["id"], "|", m["county"], "| round1 found rows:", m["round1_found"])
    elif cmd == "get":
        for u in a[1:]:
            F.fetch(a[0], u)
    elif cmd == "crawl":
        F.crawl(a[0], a[1], int(a[2]) if len(a) > 2 else 14)
    elif cmd == "sitemap":
        F.sitemap(a[0], a[1], int(a[2]) if len(a) > 2 else 18)
    elif cmd == "links":
        t, m, b = F.fetch("_links", a[0], quiet=True)
        if b is None:
            print("blocked:", m)
        else:
            rx = re.compile(a[1], re.I) if len(a) > 1 else F.KEY
            for h, tx in F.page_links(b, a[0]):
                if rx.search(h) or rx.search(tx):
                    print(tx[:60], "|", h)
    elif cmd == "grep":
        F.grep(a[0], a[1], int(a[2]) if len(a) > 2 else 240, int(a[3]) if len(a) > 3 else 5)
    elif cmd == "pages":
        F.pages(a[0])
    elif cmd == "build":
        build()
    save_blocked()
