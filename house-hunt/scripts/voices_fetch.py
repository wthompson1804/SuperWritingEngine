"""Fetch Trulia neighborhood pages and Niche review pages for shown neighborhoods, nearest to Jamaica first.

User-requested, low-volume lookups: robots `*` group for both sites (neither has a Claude-User group), >= 3.5 s per
host, stop a source on the first bot wall / 403 / CAPTCHA. Parsed reviews go to raw/voices_pool/<source>.jsonl
(one line per review, no reviewer names); status lines go to raw/voices_pool/_status.jsonl.
Usage: python3 scripts/voices_fetch.py [trulia|niche]
"""
import csv, json, re, sys, html
from pathlib import Path
import lib, voices_lib as v
from voices_targets import TRULIA, NICHE, T

POOL = lib.RAW / "voices_pool"; POOL.mkdir(parents=True, exist_ok=True)
STATUS = POOL / "_status.jsonl"

def hoods():
    hs = {r["hood_id"]: r for r in csv.DictReader(open(lib.DATA / "neighborhoods.csv"))}
    rows = list(csv.DictReader(open(lib.DATA / "reference/shown_neighborhoods.csv")))
    rows.sort(key=lambda r: float(hs.get(r["id"], {}).get("drive_min") or 999))
    return rows

def done(source):
    s = set()
    if STATUS.exists():
        for l in open(STATUS):
            d = json.loads(l)
            if d["source"] == source: s.add((d["hood_id"], d["url"], d.get("status") == 200))
    return s

def log(**kw):
    with open(STATUS, "a") as f: f.write(json.dumps(kw) + "\n")

def app(source, rows):
    with open(POOL / f"{source}.jsonl", "a") as f:
        for r in rows: f.write(json.dumps(r) + "\n")

def walled(status, text):
    t = text[:20000].lower()
    return status in (401, 403, 429) or "px-captcha" in t or "are you a robot" in t or "access denied" in t[:3000] or "just a moment" in t[:2000]

def trulia():
    seen = done("trulia"); cache = {}
    for h in hoods():
        for path, area in TRULIA.get(h["id"], []):
            url = T + path
            if (h["id"], url, True) in seen or (h["id"], url, False) in seen: continue
            if url in cache: content, meta = cache[url]
            else:
                content, meta = v.get(url, "voices_trulia"); cache[url] = (content, meta)
            s = content.decode("utf8", "ignore")
            if walled(meta["status"], s):
                log(source="trulia", hood_id=h["id"], url=url, status=meta["status"], note="bot wall: stopped"); print("WALL", url); return
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s, re.S)
            if meta["status"] != 200 or not m:
                log(source="trulia", hood_id=h["id"], url=url, status=meta["status"], note="no data"); continue
            d = json.loads(m.group(1))
            # keep only the data tag, with reviewer names removed (working rule 6), as h_trulia.py does
            def scrub(o):
                if isinstance(o, dict):
                    if o.get("__typename") == "USER_Reviewer": o["name"] = None
                    for x in o.values(): scrub(x)
                elif isinstance(o, list):
                    for x in o: scrub(x)
            scrub(d)
            p = lib.ROOT / meta["path"]
            p.write_text('<script id="__NEXT_DATA__" type="application/json">' + json.dumps(d).replace("</", "<\\/") + "</script>")
            u = d["props"].get("localUGC") or {}
            stats = (u.get("stats") or {})
            lr = u.get("localReviews") or {}
            rows = [dict(hood_id=h["id"], source="trulia", url=url, area=area, kind="stat", measure=a["type"], value=a["score"],
                         retrieved_at=meta["retrieved_at"]) for a in (stats.get("attributes") or [])]
            if stats.get("minimumResponseCount") is not None:
                rows.append(dict(hood_id=h["id"], source="trulia", url=url, area=area, kind="stat", measure="MinResponseCount", value=stats["minimumResponseCount"], retrieved_at=meta["retrieved_at"]))
            if lr.get("totalReviews") is not None:
                rows.append(dict(hood_id=h["id"], source="trulia", url=url, area=area, kind="stat", measure="ReviewCount", value=lr["totalReviews"], retrieved_at=meta["retrieved_at"]))
            n = 0
            for r in lr.get("reviews") or []:
                if not r.get("text"): continue
                n += 1
                rows.append(dict(hood_id=h["id"], source="trulia", url=url, area=area, kind="review", post_id=r["id"], text=r["text"],
                                 date=(r.get("dateCreated") or "")[:10], who=(r.get("context") or {}).get("displayName") or "",
                                 category=(r.get("category") or {}).get("displayName") or "", rating=None, retrieved_at=meta["retrieved_at"], path=meta["path"]))
            app("trulia", rows)
            log(source="trulia", hood_id=h["id"], url=url, status=200, reviews=n, stats=len(stats.get("attributes") or []), page_hood=d["props"].get("neighborhoodName"), city=str(d["props"].get("city"))[:80])
            print(h["id"], area, n, flush=True)

def strip(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip()

def niche():
    seen = done("niche"); cache = {}
    hs = {r["hood_id"]: r for r in csv.DictReader(open(lib.DATA / "neighborhoods.csv"))}
    for h in hoods():
        got = False
        for slug in NICHE.get(h["id"], []):
            if got and not slug.startswith("n/"): break
            if got and float(hs[h["id"]]["drive_min"]) > 12: break   # second named area only for the nearest hoods
            base = f"https://www.niche.com/places-to-live/{slug}/reviews/"
            pages = [base]
            for url in pages:
                if (h["id"], url, True) in seen: got = True; continue
                if (h["id"], url, False) in seen: continue
                if url in cache: content, meta = cache[url]
                else:
                    content, meta = v.get(url, "voices_niche"); cache[url] = (content, meta)
                s = content.decode("utf8", "ignore")
                if walled(meta["status"], s):
                    log(source="niche", hood_id=h["id"], url=url, status=meta["status"], note="bot wall: stopped"); print("WALL", url); return
                if meta["status"] != 200:
                    log(source="niche", hood_id=h["id"], url=url, status=meta["status"], note="not found"); print(h["id"], slug, meta["status"], flush=True); continue
                got = True
                title = strip(re.search(r"<title[^>]*>(.*?)</title>", s, re.S).group(1))
                rows = []
                m = re.search(r"Rating\s*(?:<!-- -->)?\s*([\d.]+)\s*(?:<!-- -->)?\s*out of 5\s*</p>.{0,400}?([\d,]+)\s*(?:<!-- -->)?\s*reviews", s, re.S)
                txt = strip(s)
                m2 = re.search(r"Rating ([\d.]+) out of 5 ([\d,]+) reviews", txt)
                if m2:
                    rows.append(dict(hood_id=h["id"], source="niche", url=url, area=title, kind="stat", measure="niche_overall_rating", value=m2.group(1), retrieved_at=meta["retrieved_at"]))
                    rows.append(dict(hood_id=h["id"], source="niche", url=url, area=title, kind="stat", measure="niche_review_count", value=m2.group(2).replace(",", ""), retrieved_at=meta["retrieved_at"]))
                n = 0
                for blk in re.split(r'(?=<div class="review" data-testid="review")', s)[1:]:
                    b = re.search(r'itemprop="reviewBody">(.*?)</div>', blk, re.S)
                    dt = re.search(r'<meta content="([\d-]+)" itemprop="datePublished"', blk)
                    rt = re.search(r'<meta content="(\d)" itemprop="ratingValue"', blk)
                    who = re.search(r'itemprop="author".*?<span itemprop="name">(.*?)</span>', blk, re.S)
                    pid = re.search(r'helpfulness-rating[^"]*" data-testid="([0-9a-f-]+)"', blk)
                    if not b or not dt: continue
                    paras = [strip(x) for x in re.split(r"<br\s*/?>", b.group(1))]
                    n += 1
                    rows.append(dict(hood_id=h["id"], source="niche", url=url, area=title, kind="review", post_id=pid.group(1) if pid else f"{url}#{n}",
                                     text="\n".join(p for p in paras if p), date=dt.group(1), who=strip(who.group(1)) if who else "", category="",
                                     rating=int(rt.group(1)) if rt else None, retrieved_at=meta["retrieved_at"], path=meta["path"]))
                app("niche", rows)
                log(source="niche", hood_id=h["id"], url=url, status=200, reviews=n, title=title, rating=m2.groups() if m2 else None)
                print(h["id"], slug, n, m2.groups() if m2 else None, flush=True)
                # (?page=2 returns the same 20 reviews as page 1: pagination is client-side, so one page per place)
        if not NICHE.get(h["id"]): log(source="niche", hood_id=h["id"], url="", status=None, note="no slug")

if __name__ == "__main__":
    {"trulia": trulia, "niche": niche}[sys.argv[1]]()
