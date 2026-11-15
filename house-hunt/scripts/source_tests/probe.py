"""Low-volume source access probe (2026-11-15).

For each test: fetch the host's robots.txt once, check the path against the
`*` group (Google-style longest match, Allow wins ties), and fetch it only if
allowed. Saves raw bodies (<=2 MB) under raw/source_tests/<host>/ and appends a
result row to raw/source_tests/_results.jsonl. At most 1 request / 2 s / host.

usage: python3 probe.py targets.json [name-substring ...]
targets.json: list of {"name","url", optional "method","data","headers","note"}
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "raw" / "source_tests"
UA = "house-hunt-research/0.1 (personal non-commercial research; low volume)"
MAXB = 2 * 1024 * 1024
DELAY = 2.1

_last: dict[str, float] = {}
_robots: dict[str, dict] = {}
_lock = threading.Lock()


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def throttle(host):
    w = _last.get(host, 0) + DELAY - time.time()
    if w > 0:
        time.sleep(w)
    _last[host] = time.time()


def safe(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:150]


def fetch(url, method="GET", data=None, headers=None, timeout=40):
    host = urlparse(url).netloc
    throttle(host)
    h = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    t0 = time.time()
    try:
        r = requests.request(method, url, data=data, headers=h, timeout=timeout,
                             stream=True, allow_redirects=True)
        body = b""
        if method != "HEAD":
            for chunk in r.iter_content(65536):
                body += chunk
                if len(body) >= MAXB:
                    body = body[:MAXB]
                    break
        r.close()
        return {"status": r.status_code, "final_url": r.url, "elapsed": round(time.time() - t0, 1),
                "ctype": r.headers.get("content-type", ""), "server": r.headers.get("server", ""),
                "clen": r.headers.get("content-length"),
                "redirects": [x.status_code for x in r.history],
                "hdr": {k: v for k, v in r.headers.items() if k.lower() in (
                    "x-ratelimit-limit", "x-ratelimit-remaining", "retry-after", "x-datadome",
                    "cf-ray", "x-px", "set-cookie", "last-modified", "x-amz-cf-id", "akamai-grn",
                    "x-cache", "via")}}, body
    except requests.RequestException as e:
        return {"status": None, "error": repr(e)[:300], "elapsed": round(time.time() - t0, 1)}, b""


def parse_robots(txt):
    """Return list of (directive, pattern) for the '*' group, plus sitemaps and specific-UA list."""
    groups, cur, last_was_ua = [], None, False
    sitemaps = []
    for raw in txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "sitemap":
            sitemaps.append(v)
            continue
        if k == "user-agent":
            if not last_was_ua:
                cur = {"uas": [], "rules": []}
                groups.append(cur)
            cur["uas"].append(v.lower())
            last_was_ua = True
            continue
        last_was_ua = False
        if cur is not None and k in ("allow", "disallow", "crawl-delay"):
            cur["rules"].append((k, v))
    star = [r for g in groups if "*" in g["uas"] for r in g["rules"]]
    mine = [r for g in groups if any(u and u in "house-hunt-research" for u in g["uas"] if u != "*") for r in g["rules"]]
    return {"star": star, "mine": mine, "sitemaps": sitemaps,
            "agents": sorted({u for g in groups for u in g["uas"]})}


def pat_re(p):
    end = p.endswith("$")
    if end:
        p = p[:-1]
    rx = "".join(".*" if c == "*" else re.escape(c) for c in p)
    return re.compile("^" + rx + ("$" if end else ""))


def allowed(rules, path):
    best = None  # (len, is_allow)
    for k, v in rules:
        if k == "crawl-delay":
            continue
        if k == "disallow" and v == "":
            continue
        if pat_re(v).match(path):
            cand = (len(v), k == "allow")
            if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1]):
                best = cand
    return (best is None or best[1]), best


def robots_for(scheme, host):
    key = f"{scheme}://{host}"
    if key in _robots:
        return _robots[key]
    meta, body = fetch(key + "/robots.txt")
    d = OUT / host
    d.mkdir(parents=True, exist_ok=True)
    (d / "robots.txt").write_bytes(body)
    info = {"status": meta.get("status"), "meta": meta}
    st = meta.get("status")
    txt = body.decode("utf-8", "replace")
    looks_html = "<html" in txt[:2000].lower()
    wall = any(re.search(rx, txt[:20000], re.I) for _, rx in BOT) or re.search(r"Request Rejected|Access Denied|Forbidden", txt[:5000], re.I)
    if st and 200 <= st < 300 and not looks_html:
        info.update(parse_robots(txt))  # empty 2xx body = no rules
        info["mode"] = "rules"
    elif st in (401, 403, 429) or (st == 200 and looks_html and wall):
        info["mode"] = "blocked"  # bot wall / rejection on robots itself: do not proceed
    elif st == 200 and looks_html:
        info["mode"] = "none"  # SPA/soft-404 HTML instead of a robots file: no rules published
    elif st and 400 <= st < 500:
        info["mode"] = "none"  # no robots file: unrestricted per RFC 9309
    else:
        info["mode"] = "unreachable"  # 5xx / network error: treat as full disallow
    cd = [v for k, v in info.get("star", []) if k == "crawl-delay"]
    info["crawl_delay"] = cd[0] if cd else None
    with _lock, open(OUT / "_robots.jsonl", "a") as f:
        f.write(json.dumps({"host": host, "at": now(), "status": st, "mode": info["mode"],
                            "n_star_rules": len(info.get("star", [])), "sitemaps": info.get("sitemaps", []),
                            "agents": info.get("agents", [])[:80], "crawl_delay": info["crawl_delay"],
                            "meta": meta}) + "\n")
    _robots[key] = info
    return info


BOT = [("captcha", r"captcha"), ("px", r"px-captcha|perimeterx|Press &amp; Hold|Press & Hold"),
       ("datadome", r"captcha-delivery\.com|datadome"), ("cloudflare", r"Just a moment\.\.\.|cf-chl|challenge-platform"),
       ("akamai_denied", r"Access Denied</|errors\.edgesuite\.net"), ("imperva", r"Incapsula|Pardon Our Interruption"),
       ("login", r"Log in to continue|Sign in to continue|please log in")]


def markers(body, ctype):
    t = body.decode("utf-8", "replace")
    m = {}
    tt = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    if tt:
        m["title"] = re.sub(r"\s+", " ", tt.group(1)).strip()[:120]
    m["bot"] = [n for n, rx in BOT if re.search(rx, t[:300000], re.I)]
    m["ldjson"] = len(re.findall(r"application/ld\+json", t))
    m["next_data"] = "__NEXT_DATA__" in t
    m["init_state"] = bool(re.search(r"__INITIAL_STATE__|__PRELOADED_STATE__|__APOLLO_STATE__|__NUXT__|window\.__data", t))
    m["prices"] = len(re.findall(r"\$\s?\d{1,2},\d{3}", t))
    m["bytes"] = len(body)
    return m


def run_one(t):
    url = t["url"]
    u = urlparse(url)
    rb = robots_for(u.scheme, u.netloc)
    path = (u.path or "/") + (("?" + u.query) if u.query else "")
    row = {"name": t["name"], "url": url, "at": now(), "robots_mode": rb["mode"]}
    if rb["mode"] == "rules":
        ok, rule = allowed(rb["star"], path)
        row["robots_rule"] = rule
        if rb.get("mine"):
            ok2, rule2 = allowed(rb["mine"], path)
            row["robots_rule_ua"] = rule2
            ok = ok and ok2
    elif rb["mode"] == "none":
        ok = True
    else:
        ok = False
    if not ok and t.get("override"):
        # documented machine API whose robots.txt could not be read as a file; see note
        row["robots_override"] = t["override"]
        ok = True
    row["robots_allowed"] = ok
    if t.get("robots_only"):
        row["skipped"] = "robots only"
    elif not ok:
        row["skipped"] = "disallowed by robots.txt" if rb["mode"] == "rules" else f"robots {rb['mode']}"
    else:
        meta, body = fetch(url, t.get("method", "GET"), t.get("data"), t.get("headers"))
        row.update(meta)
        if body:
            ext = ".json" if "json" in row.get("ctype", "") else ".xml" if "xml" in row.get("ctype", "") else ".csv" if "csv" in row.get("ctype", "") else ".html" if "html" in row.get("ctype", "") else ".bin"
            fn = OUT / u.netloc / (safe(t["name"]) + ext)
            fn.write_bytes(body)
            row["saved"] = str(fn.relative_to(ROOT))
            row.update(markers(body, row.get("ctype", "")))
    with _lock, open(OUT / "_results.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    short = {k: row.get(k) for k in ("name", "status", "skipped", "robots_rule", "ctype", "bytes", "title", "bot", "ldjson", "next_data", "init_state", "prices", "final_url", "error")}
    print(json.dumps({k: v for k, v in short.items() if v not in (None, [], False, 0)}), flush=True)
    return row


def main():
    targets = json.loads(Path(sys.argv[1]).read_text())
    flt = sys.argv[2:]
    if flt:
        targets = [t for t in targets if any(f in t["name"] for f in flt)]
    by_host = defaultdict(list)
    for t in targets:
        by_host[urlparse(t["url"]).netloc].append(t)
    with ThreadPoolExecutor(12) as ex:
        list(ex.map(lambda ts: [run_one(t) for t in ts], by_host.values()))


if __name__ == "__main__":
    main()
