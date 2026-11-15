"""Fetch official municipal pages for the local-rules pass (street parking, dogs).

Robots: every host's robots.txt is read once. A group naming Claude (claudebot, claude-user,
claude-searchbot, claude-web, anthropic-ai) overrides `*`. Disallowed hosts and bot walls are logged in
raw/local_rules/_blocked.jsonl and never retried. 2.2 s between requests per host.

Usage:
  python3 scripts/local_rules_fetch.py get <muni> <url> [<url> ...]     fetch pages, store text
  python3 scripts/local_rules_fetch.py crawl <muni> <start_url> [max]   follow keyword links from a start page
  python3 scripts/local_rules_fetch.py digest <muni> [regex]            print keyword sentences from stored text
  python3 scripts/local_rules_fetch.py links <url> [regex]              list links on a fetched page
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402

lib.DEFAULT_DELAY = 2.2
SRC = "local_rules"
OUT = lib.RAW / SRC
TXT = OUT / "text"
TXT.mkdir(parents=True, exist_ok=True)
PAGES = OUT / "_pages.jsonl"
BLOCKED = OUT / "_blocked.jsonl"
CLAUDE_AGENTS = ("claudebot", "claude-user", "claude-searchbot", "claude-web", "anthropic-ai", "claude")

KEY = re.compile(
    r"park(ing)?|permit|overnight|meter|garage|snow|street.?(sweep|clean)|alternate|dog|animal|pet|licens|"
    r"leash|recreation|police|clerk|faq|ordinance|code|health|resident", re.I)
STRONG = re.compile(r"parking|overnight|dog|animal|pet\b|snow|sweep|leash|garage|meter|permit", re.I)
SENT = re.compile(
    r"overnight|permit|alternate side|street (sweep|clean)|snow|meter|garage|monthly|per month|dog|leash|"
    r"licens|canine|pooper|feces|waste|guest|visitor|a\.m\.|p\.m\.|\bam\b|\bpm\b", re.I)

_robots: dict[str, object] = {}


def _log(path: Path, rec: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def parse_robots(text: str) -> dict[str, list[tuple[str, str]]]:
    groups: dict[str, list[tuple[str, str]]] = {}
    agents: list[str] = []
    in_rules = False
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = [x.strip() for x in line.split(":", 1)]
        k = k.lower()
        if k == "user-agent":
            if in_rules:
                agents, in_rules = [], False
            agents.append(v.lower())
            groups.setdefault(v.lower(), [])
        elif k in ("allow", "disallow", "crawl-delay"):
            in_rules = True
            for a in agents:
                groups[a].append((k, v))
    return groups


def _match(pat: str, path: str) -> bool:
    rx = re.escape(pat).replace(r"\*", ".*")
    if rx.endswith(r"\$"):
        rx = rx[:-2] + "$"
    return re.match(rx, path) is not None


def robots_ok(url: str) -> tuple[bool, str]:
    u = urlparse(url)
    host = u.netloc
    if host not in _robots:
        try:
            body, meta = lib.cached_get(f"{u.scheme}://{host}/robots.txt", SRC, ext="txt", retries=2, timeout=30)
        except Exception as e:  # noqa: BLE001
            _robots[host] = ("error", repr(e)[:200])
        else:
            st = meta["status"]
            t = body.decode("utf-8", "replace")
            if st in (401, 403, 429) or (st == 200 and re.search(r"just a moment|captcha|access denied", t[:3000], re.I)):
                _robots[host] = ("blocked", f"robots.txt HTTP {st} bot wall")
            elif st != 200 or "<html" in t[:500].lower():
                _robots[host] = ("none", "")
            else:
                _robots[host] = ("rules", parse_robots(t))
    kind, val = _robots[host]
    if kind == "blocked" or kind == "error":
        return False, val
    if kind == "none":
        return True, "no robots rules"
    groups = val
    named = [a for a in groups if any(a == c or a.startswith(c) for c in CLAUDE_AGENTS)]
    rules = []
    if named:
        for a in named:
            rules += groups[a]
        which = "claude group"
    else:
        rules = groups.get("*", [])
        which = "* group"
    path = u.path or "/"
    if u.query:
        path += "?" + u.query
    best = (-1, True)
    for k, v in rules:
        if k == "crawl-delay":
            try:
                lib.HOST_DELAY[host] = max(2.2, float(v))
            except ValueError:
                pass
            continue
        if v == "":
            continue
        if _match(v, path):
            ln = len(v)
            allow = k == "allow"
            if ln > best[0] or (ln == best[0] and allow):
                best = (ln, allow)
    return best[1], which


def to_text(body: bytes, ctype_hint: str) -> tuple[str, str]:
    if body[:5] == b"%PDF-":
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(body)
            f.flush()
            r = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=120)
        return "(pdf)", r.stdout.decode("utf-8", "replace")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(body, "lxml")
    title = (soup.title.get_text(" ", strip=True) if soup.title else "")[:150]
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    text = soup.get_text("\n", strip=True)
    return title, text


def norm(s: str) -> str:
    s = s.replace(" ", " ").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip()


def text_path(url: str) -> Path:
    return TXT / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".txt")


def fetch(muni: str, url: str, quiet: bool = False):
    """Return (text, meta, body) or (None, reason, None)."""
    url = urldefrag(url)[0]
    ok, why = robots_ok(url)
    if not ok:
        _log(BLOCKED, {"muni": muni, "url": url, "reason": "robots: " + why, "at": lib.now_iso()})
        if not quiet:
            print(f"  ROBOTS-BLOCKED {url} ({why})")
        return None, "robots: " + why, None
    ext = "pdf" if url.lower().split("?")[0].endswith(".pdf") else "html"
    try:
        body, meta = lib.cached_get(url, SRC, ext=ext, retries=2, timeout=45)
    except Exception as e:  # noqa: BLE001
        _log(BLOCKED, {"muni": muni, "url": url, "reason": "error " + repr(e)[:150], "at": lib.now_iso()})
        if not quiet:
            print(f"  ERROR {url} {repr(e)[:120]}")
        return None, "error", None
    st = meta["status"]
    head = body[:4000].decode("utf-8", "replace")
    wall = re.search(r"just a moment\.\.\.|cf-chl|captcha|access denied|request blocked|incapsula|perimeterx|"
                     r"enable javascript and cookies", head, re.I)
    if st != 200 or (wall and len(body) < 30000):
        reason = f"HTTP {st}" + (" bot wall" if wall else "")
        _log(BLOCKED, {"muni": muni, "url": url, "reason": reason, "at": lib.now_iso()})
        if st in (401, 403, 429) or wall:
            _robots[urlparse(url).netloc] = ("blocked", reason)  # stop at bot walls: no more requests this run
        if not quiet:
            print(f"  FAIL {reason} {url}")
        return None, reason, None
    title, text = to_text(body, ext)
    tp = text_path(url)
    new = not tp.exists()
    tp.write_text(text)
    if new:
        _log(PAGES, {"muni": muni, "url": url, "title": title, "retrieved_at": meta["retrieved_at"],
                     "text": str(tp.relative_to(lib.ROOT)), "chars": len(text)})
    if not quiet:
        print(f"  OK {len(text):>7} {title[:60]!r} {url}")
    return text, meta, body


def page_links(body: bytes, base: str) -> list[tuple[str, str]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(body, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        h = urldefrag(urljoin(base, a["href"]))[0]
        if not h.startswith("http") or h in seen:
            continue
        seen.add(h)
        out.append((h, a.get_text(" ", strip=True)[:100]))
    return out


def crawl(muni: str, start: str, max_pages: int = 14) -> None:
    host = urlparse(start).netloc.replace("www.", "")
    text, meta, body = fetch(muni, start)
    if text is None:
        return
    queue = [(h, t) for h, t in page_links(body, start)]
    done = {start}
    n = 0
    lvl2: list[tuple[str, str]] = []
    for rnd in (1, 2):
        cand = []
        for h, t in queue:
            if h in done or host not in urlparse(h).netloc:
                continue
            if re.search(r"\.(jpg|png|gif|zip|docx?|xlsx?|ics)$|mailto:|/calendar|/news|agenda|minutes|login|facebook", h, re.I):
                continue
            s = (3 if STRONG.search(t) else 0) + (2 if STRONG.search(urlparse(h).path) else 0) + (1 if KEY.search(t) else 0)
            if rnd == 2 and s < 3:
                continue
            if s >= 1:
                cand.append((s, h, t))
        cand.sort(key=lambda x: -x[0])
        for s, h, t in cand:
            if n >= max_pages:
                return
            if h in done:
                continue
            done.add(h)
            text, meta, body = fetch(muni, h)
            n += 1
            if text is not None and body[:5] != b"%PDF-" and rnd == 1 and s >= 2:
                lvl2 += page_links(body, h)
        queue = lvl2


def digest(muni: str, rx: str | None = None, width: int = 260) -> None:
    pat = re.compile(rx, re.I) if rx else SENT
    seen = set()
    for line in PAGES.read_text().splitlines():
        r = json.loads(line)
        if r["muni"] != muni or r["url"] in seen:
            continue
        seen.add(r["url"])
        text = norm((lib.ROOT / r["text"]).read_text())
        hits = []
        last = -10**9
        for m in pat.finditer(text):
            if m.start() < last:
                continue
            a, b = max(0, m.start() - width // 2), min(len(text), m.end() + width // 2)
            hits.append(text[a:b])
            last = b
        print(f"\n### {r['title'][:70]} | {r['url']} | {r['chars']} chars, {len(hits)} hits")
        for h in hits[:14]:
            print("  -", h)


SM = re.compile(r"park(ing)?[-_/]|parking|overnight|dog|animal|pets?\b|snow|sweep|leash|garage|meter|canine|"
                r"street[-_ ]clean|alternate|winter", re.I)
SM_NO = re.compile(r"agenda|minutes|calendar|/news|civicalerts|bids?\b|rfp|job|employment|parks?-and-rec.*program|"
                   r"\.(jpg|png|gif|docx?|xlsx?)$|park-?(rental|pavilion)|pickleball|tennis|camp|parkway|parker", re.I)


def sitemap(muni: str, base: str, max_pages: int = 18) -> None:
    urls: list[str] = []
    todo = [base.rstrip("/") + "/sitemap.xml"]
    seen = set()
    while todo and len(seen) < 8:
        sm = todo.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        ok, why = robots_ok(sm)
        if not ok:
            print("  ROBOTS-BLOCKED", sm, why[:80])
            continue
        try:
            body, meta = lib.cached_get(sm, SRC, ext="xml", retries=2, timeout=45)
        except Exception as e:  # noqa: BLE001
            print("  ERROR", sm, repr(e)[:100])
            continue
        if meta["status"] != 200:
            print("  FAIL", meta["status"], sm)
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body.decode("utf-8", "replace"))
        for l in locs:
            l = l.replace("&amp;", "&")
            if l.endswith(".xml") or "sitemap" in l.lower():
                todo.append(l)
            else:
                urls.append(l)
    print(f"  sitemap urls: {len(urls)}")
    cand = [u for u in dict.fromkeys(urls) if SM.search(urlparse(u).path) and not SM_NO.search(u)]
    cand.sort(key=lambda u: (-len(SM.findall(urlparse(u).path)), len(u)))
    print(f"  candidates: {len(cand)}")
    for u in cand[:max_pages]:
        if not text_path(u).exists():
            fetch(muni, u)
    for u in cand[max_pages:max_pages + 40]:
        print("  (not fetched)", u)


def grep(sub: str, rx: str, width: int = 240, mx: int = 5) -> None:
    pat = re.compile(rx, re.I)
    seen = set()
    for line in PAGES.read_text().splitlines():
        r = json.loads(line)
        if sub not in r["url"] and sub != r["muni"] or r["url"] in seen:
            continue
        seen.add(r["url"])
        text = norm((lib.ROOT / r["text"]).read_text())
        hits, last = [], -1
        for m in pat.finditer(text):
            if m.start() < last:
                continue
            a, b = max(0, m.start() - width // 3), min(len(text), m.end() + width)
            hits.append(text[a:b])
            last = b
        if hits:
            print(f"## {r['url']} ({len(hits)})")
            for h in hits[:mx]:
                print("  -", h)


BODY = re.compile(r"overnight|permit|alternate side|street (sweep|clean)|snow|meter|garage|monthly|per month|dogs?\b|"
                  r"leash|licens|canine|feces|waste|guest|visitor|\$\d|a\.m\.|p\.m\.|\d ?[ap]m\b", re.I)


def body(muni: str, per_page: int = 700, rx: str | None = None) -> None:
    """Print keyword lines of each page with host boilerplate (lines repeated on 3+ pages) removed."""
    from collections import Counter
    pat = re.compile(rx, re.I) if rx else BODY
    recs, seen = [], set()
    for line in PAGES.read_text().splitlines():
        r = json.loads(line)
        if r["muni"] == muni and r["url"] not in seen:
            seen.add(r["url"])
            r["lines"] = [norm(x) for x in (lib.ROOT / r["text"]).read_text().splitlines() if norm(x)]
            recs.append(r)
    cnt = Counter()
    for r in recs:
        for x in set(r["lines"]):
            cnt[(urlparse(r["url"]).netloc, x)] += 1
    for r in recs:
        host = urlparse(r["url"]).netloc
        if not rx and not STRONG.search(r["title"] + " " + urlparse(r["url"]).path):
            continue
        keep = [x for x in r["lines"] if cnt[(host, x)] < 3]
        txt = " | ".join(keep) if r["title"] != "(pdf)" else " ".join(keep)
        hits, last = [], -1
        for m in pat.finditer(txt):
            if m.start() < last:
                continue
            a, b = max(0, m.start() - 110), min(len(txt), m.end() + 230)
            hits.append(txt[a:b])
            last = b
        if not hits:
            continue
        out = " ... ".join(hits)
        print(f"## {r['url']} [{len(txt)}c]\n   {out[:per_page]}")


def view(muni: str, n: int = 600, rx: str | None = None) -> None:
    """Print the first n chars of each topic page's own text (host boilerplate lines removed)."""
    from collections import Counter
    pat = re.compile(rx, re.I) if rx else SM
    recs, seen = [], set()
    for line in PAGES.read_text().splitlines():
        r = json.loads(line)
        if r["muni"] == muni and r["url"] not in seen:
            seen.add(r["url"])
            r["lines"] = [norm(x) for x in (lib.ROOT / r["text"]).read_text().splitlines() if norm(x)]
            recs.append(r)
    cnt = Counter()
    for r in recs:
        for x in set(r["lines"]):
            cnt[(urlparse(r["url"]).netloc, x)] += 1
    for r in recs:
        if not pat.search(r["title"] + " " + r["url"]) or (not rx and SM_NO.search(r["url"])):
            continue
        host = urlparse(r["url"]).netloc
        keep = [x for x in r["lines"] if cnt[(host, x)] < 3 and len(x) > 3]
        txt = " ".join(keep)
        print(f"## {r['url']} [{len(txt)}c]\n   {txt[:n]}")


def pages(muni: str) -> None:
    seen = set()
    for line in PAGES.read_text().splitlines():
        r = json.loads(line)
        if r["muni"] == muni and r["url"] not in seen:
            seen.add(r["url"])
            print(f"{r['chars']:>7} {r['title'][:45]!r} {r['url']}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "grep":
        grep(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 240, int(sys.argv[5]) if len(sys.argv) > 5 else 5)
        sys.exit()
    if cmd == "sitemap":
        sitemap(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 18)
        sys.exit()
    if cmd == "body":
        body(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 700, sys.argv[4] if len(sys.argv) > 4 else None)
        sys.exit()
    if cmd == "view":
        view(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 600, sys.argv[4] if len(sys.argv) > 4 else None)
        sys.exit()
    if cmd == "pages":
        pages(sys.argv[2])
        sys.exit()
    if cmd == "get":
        for u in sys.argv[3:]:
            fetch(sys.argv[2], u)
    elif cmd == "crawl":
        crawl(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 14)
    elif cmd == "digest":
        digest(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "links":
        t, m, b = fetch("_links", sys.argv[2], quiet=True)
        if b is None:
            print("blocked:", m)
        else:
            rx = re.compile(sys.argv[3], re.I) if len(sys.argv) > 3 else KEY
            for h, tx in page_links(b, sys.argv[2]):
                if rx.search(h) or rx.search(tx):
                    print(tx[:60], "|", h)
