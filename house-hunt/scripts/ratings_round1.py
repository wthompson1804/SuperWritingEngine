"""Structured ratings for the round-1 candidate buildings (docs/EVIDENCE_AGENT_BRIEF.md, round-2 addendum).

For every building in data/reference/evidence_batches/all_candidate_buildings.csv, one row per rating source:
  Google rating shown on Zumper   Zumper building / address page (state blob: buildingReviews.sources.google)
  Apartment List                  property page JSON-LD (aggregateRating + Review items)
  Openigloo                       NYC building page (by tax lot)
  none_found                      when no source shows a rating (notes say where we looked)
Cache first: every page already under raw/*/ (looked up through the _index.jsonl files) is reused; only missing
Zumper address pages and Openigloo lot pages are fetched (raw/ratings_r1/, >= 4 s per host, robots-allowed paths:
Zumper /address/ and /apartment-buildings/, Openigloo /building/nyc/<id>/...).
Output: data/evidence/ratings_round1.csv (rewritten whole each run; idempotent).
Usage: python3 scripts/ratings_round1.py [--no-fetch]
"""
import csv, glob, html as H, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
import h_zumper as Z

for h in ("www.zumper.com", "www.openigloo.com", "www.apartmentlist.com"):
    lib.HOST_DELAY[h] = 4.0
NOFETCH = "--no-fetch" in sys.argv
TODAY = datetime(2026, 11, 15, tzinfo=timezone.utc)
M6 = datetime(2026, 5, 15, tzinfo=timezone.utc)
OUT = lib.DATA / "evidence" / "ratings_round1.csv"
COLS = ["addr_key", "building_name", "rating_source", "rating_value", "rating_scale", "review_count", "as_of_date",
        "reviews_read", "reviews_last_6_months", "negative_last_6_months", "negative_older",
        "serious_issue_tags_last_6_months", "source_url", "retrieved_at", "notes"]

TAGS = {
    "no_heat_hot_water": r"no heat|no hot water|without (heat|hot water)|(heat|hot water|boiler) (was|is|has been|went) (out|off|down|broken)|lack of heat",
    "pests": r"roach|\bmice\b|\bmouse\b|\brats?\b|rodent|bed ?bugs?|infest|vermin|\bpests?\b",
    "mold": r"\bmold|mildew",
    "elevator_outage": r"elevators?.{0,50}(broke|out of (service|order)|\bdown\b|not work|stuck|outage|never work|don.t work|doesn.t work)|(broken|out of service|no working).{0,30}elevator",
    "car_break_in": r"(car|cars|vehicle|garage|parking).{0,50}(broken into|break-?ins?|stolen|theft|vandal)|catalytic",
    "package_theft": r"packages?.{0,40}(stolen|theft|missing|stole|disappear)|(stolen|stole|missing).{0,20}packages?",
    "unresponsive_management": r"(management|manager|office|landlord|maintenance|super|staff).{0,60}(unresponsive|never respond|ignor|not respond|no response|\brude\b|never (fix|came|answer|return)|unprofessional|terrible|horrible|worst)|never (got )?fixed|(terrible|horrible|worst) (management|landlord|maintenance)",
    "fees_or_deposit": r"deposit.{0,50}(not return|withh|never|kept|back|refus)|hidden fees?|illegal fees?|junk fees?|bogus (fees?|charges?)",
    "safety_incident": r"shooting|shot\b|assault|robbed|robbery|break-?ins?|\bunsafe\b|stabb|burglar",
    "noise": r"\bnois|\bloud\b|thin walls|paper.thin",
}
NEG_GUARD = re.compile(r"(\bno|\bnot|never (had|seen|have)|without|zero|free of|n.t (had|have|seen))\s+(any\s+|a\s+|issues? with\s+|problems? with\s+)?$", re.I)


def tags_of(text):
    out = []
    for tag, pat in TAGS.items():
        for m in re.finditer(pat, text or "", re.I | re.S):
            if not NEG_GUARD.search(text[max(0, m.start() - 28):m.start()]):
                out.append(tag); break
    return out


def is_negative(stars, text):
    """Negative = 1 or 2 stars; or, when the review is 3 stars or carries no star value, text reporting a serious
    issue. A 4 or 5 star review is never counted as negative (keyword hits there are almost always 'no noise')."""
    t = tags_of(text)
    if stars is not None and stars <= 2:
        return True, t
    if (stars is None or stars <= 3) and t:
        return True, t
    return False, t


def load_index():
    idx = {}
    for f in glob.glob(str(lib.RAW / "*" / "_index.jsonl")):
        src = Path(f).parent.name
        if not (src.startswith("evidence") or src in ("apartmentlist", "zumper", "openigloo", "ratings_r1")):
            continue
        for line in open(f):
            try:
                m = json.loads(line)
            except Exception:
                continue
            if m.get("status") == 200 and m.get("path") and (lib.ROOT / m["path"]).exists():
                u = m["url"].rstrip("/")
                if u not in idx or m["retrieved_at"] > idx[u]["retrieved_at"]:
                    idx[u] = m
    return idx


def get(url, idx, ext="html"):
    """Cached copy from any raw/ folder, else a polite fetch. Returns (text or None, meta)."""
    m = idx.get(url.rstrip("/"))
    if m:
        return (lib.ROOT / m["path"]).read_text(errors="replace"), m
    miss = lib.RAW / "ratings_r1" / "_misses.json"
    misses = json.loads(miss.read_text()) if miss.exists() else {}
    if url in misses:
        return None, misses[url]
    if NOFETCH:
        return None, {"status": "not_fetched", "url": url}
    try:
        c, m = lib.cached_get(url, "ratings_r1", ext=ext, retries=2)
    except Exception as e:
        return None, {"status": "error", "url": url, "why": repr(e)[:120]}
    if m["status"] != 200:
        misses[url] = {"status": m["status"], "url": url, "retrieved_at": m["retrieved_at"]}
        miss.parent.mkdir(parents=True, exist_ok=True); miss.write_text(json.dumps(misses, indent=1))
        return None, misses[url]
    idx[url.rstrip("/")] = m
    return c.decode(errors="replace"), m


def visible(t):
    vt = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    return H.unescape(re.sub(r"\n\s*\n+", "\n", re.sub(r"<[^>]+>", "\n", vt)))


def ld_json(t):
    for j in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', t, re.S):
        try:
            yield json.loads(j)
        except Exception:
            continue


def walk(x, typ, acc):
    if isinstance(x, dict):
        if x.get("@type") == typ:
            acc.append(x)
        for v in x.values():
            walk(v, typ, acc)
    elif isinstance(x, list):
        for v in x:
            walk(v, typ, acc)
    return acc


def summarise(revs):
    """revs: list of (datetime or None, stars or None, text). -> read, last6, neg6, neg_older, tags6"""
    r6 = n6 = nold = 0; tg = []
    for d, s, body in revs:
        neg, t = is_negative(s, body)
        if d is not None and d >= M6:
            r6 += 1
            if neg:
                n6 += 1; tg += t
        elif neg:
            nold += 1
    return len(revs), r6, n6, nold, ";".join(sorted(set(tg)))


def norm_street(a):
    a = re.sub(r"[#,].*", "", a).strip().lower()
    for x, y in (("avenue", "ave"), ("street", "st"), ("boulevard", "blvd"), ("road", "rd"), ("drive", "dr"), ("terrace", "ter"),
                 ("place", "pl"), ("lane", "ln"), ("north ", "n "), ("east ", "e "), ("west ", "w "), ("south ", "s "),
                 ("parkway", "pkwy"), ("highway", "hwy"), ("court", "ct"), ("turnpike", "tpke")):
        a = re.sub(rf"\b{x.strip()}\b", y.strip(), a)
    return re.sub(r"\s+(apt|unit|ste)\b.*", "", a)


def zumper_urls(r):
    urls = []
    for f in glob.glob(str(lib.RAW / "evidence_*" / "zumper_bld.json")):
        v = json.load(open(f)).get(r["addr_key"]) or {}
        if v.get("status") == 200 and v.get("url"):
            urls.append(v["url"])
    a = norm_street(r["address"])
    slug = re.sub(r"[^a-z0-9]+", "-", f"{a} {r['city']} {r['state']} {r['zip'].zfill(5)} usa".lower()).strip("-")
    urls.append("https://www.zumper.com/address/" + slug)
    return list(dict.fromkeys(urls))


def zumper_row(r, idx):
    looked = []
    for u in zumper_urls(r):
        t, m = get(u, idx)
        looked.append(f"{u} -> {m.get('status')}")
        if not t:
            continue
        st = Z.parse_state(t) or {}
        det = st.get("detail") or {}
        d = (det.get("entity") or {}).get("data") or {}
        g = (((det.get("buildingReviews") or {}).get("data") or {}).get("sources") or {}).get("google")
        if not g or g.get("aggregateRating") is None:
            continue
        num = re.match(r"\s*([\d-]+)", r["address"])
        page_addr = " ".join(str(d.get(k) or "") for k in ("address", "name", "building_name", "pa_url", "url"))
        note = ""
        if num and num.group(1).replace("-", "") not in re.sub(r"[^0-9a-z ]", "", page_addr.lower().replace("-", "")) and "/address/" not in u:
            note = f"page address '{d.get('address')}' does not show our house number; matched by an earlier evidence batch"
        revs = []
        for x in g.get("reviews") or []:
            dt = datetime.fromtimestamp(x["date"], timezone.utc) if x.get("date") else None
            revs.append((dt, x.get("rating"), x.get("body") or ""))
        n, r6, n6, nold, tg = summarise(revs)
        pulled = datetime.fromtimestamp(g["lastPulled"], timezone.utc).date().isoformat() if g.get("lastPulled") else ""
        newest = max([x[0] for x in revs if x[0]], default=None)
        note = "; ".join(x for x in (note, f"Zumper pulled the Google figures on {pulled}; it shows only {n} 'highest rated' review texts"
                                     + (f", newest dated {newest.date().isoformat()}" if newest else "")) if x)
        return dict(rating_source="Google rating shown on Zumper", rating_value=g.get("aggregateRating"), rating_scale=g.get("ratingScale") or 5,
                    review_count=g.get("reviewCount"), as_of_date=pulled, reviews_read=n, reviews_last_6_months=r6,
                    negative_last_6_months=n6, negative_older=nold, serious_issue_tags_last_6_months=tg, source_url=u,
                    retrieved_at=m.get("retrieved_at", ""), notes=note), looked
    return None, looked


def al_rows(r, idx):
    rows, looked = [], []
    urls = dict.fromkeys(x.strip().rstrip("/") for x in (r["urls"] + " | " + r["building_url"]).split("|") if "apartmentlist.com" in x)
    for u in urls:
        t, m = get(u, idx)
        looked.append(f"{u} -> {m.get('status')}")
        if not t:
            continue
        agg, revs = None, []
        for d in ld_json(t):
            for a in walk(d, "AggregateRating", []):
                agg = agg or a
            for x in walk(d, "Review", []):
                try:
                    dt = datetime.fromisoformat(str(x.get("datePublished"))[:10]).replace(tzinfo=timezone.utc)
                except Exception:
                    dt = None
                s = (x.get("reviewRating") or {}).get("ratingValue")
                revs.append((dt, float(s) if s is not None else None, x.get("reviewBody") or ""))
        if not agg:
            continue
        revs = list(dict.fromkeys(revs))
        n, r6, n6, nold, tg = summarise(revs)
        rows.append(dict(rating_source="Apartment List", rating_value=agg.get("ratingValue"), rating_scale=agg.get("bestRating") or 5,
                         review_count=agg.get("reviewCount") or agg.get("ratingCount"), as_of_date=m.get("retrieved_at", "")[:10],
                         reviews_read=n, reviews_last_6_months=r6, negative_last_6_months=n6, negative_older=nold,
                         serious_issue_tags_last_6_months=tg, source_url=u, retrieved_at=m.get("retrieved_at", ""),
                         notes="verified-renter reviews (leased or toured); dates from the page's review markup"))
    return rows, looked


AGE = re.compile(r"^(?:(Over|About|Almost)\s+)?(\d+|a|an)\s+(minute|hour|day|week|month|year)s?\s+ago$", re.I)


def igloo_row(r, idx):
    bbl = (r["pluto_bbl"] or "").split(".")[0]
    if not bbl:
        return None, []
    cands = [u for u in idx if "openigloo.com/building/nyc/" in u and re.search(rf"/nyc/[^/]*{bbl}(/|$|-)", u.replace(f"-{bbl}", f"-{bbl}/x/", 1) if False else u)]
    cands = [u for u in idx if "openigloo.com/building/nyc/" in u and bbl in u.split("/nyc/")[1].split("/")[0].split("-")]
    cands.sort(key=lambda u: idx[u]["retrieved_at"], reverse=True)
    if not cands:
        cands = [f"https://www.openigloo.com/building/nyc/{bbl}-{bbl}/x"]
    looked = []
    for u in cands:
        t, m = get(u, idx)
        looked.append(f"{u} -> {m.get('status')}")
        if not t:
            continue
        vt = visible(t)
        mm = re.search(r"\n([\d.]+)\n(\d+) reviews?\n", vt)
        if not mm or int(mm.group(2)) == 0:
            looked[-1] += " (page has no reviews)"
            continue
        asof = re.search(r"Data last updated ([A-Z][a-z]+ \d{1,2}, \d{4})", vt)
        revs = []
        body = vt[vt.find("\nReviews of "):] if "\nReviews of " in vt else ""
        for blk in re.split(r"\n(?=(?:Former|Current) tenant\n)", body)[1:]:
            lines = [x.strip() for x in blk.split("\n") if x.strip()]
            age = next((x for x in lines[:4] if AGE.match(x)), "")
            dt = None
            a = AGE.match(age)
            if a and a.group(3).lower() not in ("minute", "hour"):   # "minutes ago" labels are render-time artefacts: undated
                k = 1 if a.group(2).lower() in ("a", "an") else int(a.group(2))
                days = k * {"day": 1, "week": 7, "month": 30.4, "year": 365}[a.group(3).lower()]
                if a.group(1) and a.group(1).lower() == "over":
                    days += 1
                dt = datetime.fromtimestamp(TODAY.timestamp() - days * 86400, timezone.utc)
            cons = blk.split("\nCons\n", 1)[1] if "\nCons\n" in blk else ""
            cons = re.split(r"\nHelpful|\nAdvice to|\nPros\n", cons)[0]
            revs.append((dt, None, cons))
        n, r6, n6, nold, tg = summarise(revs)
        return dict(rating_source="Openigloo", rating_value=mm.group(1), rating_scale=5, review_count=mm.group(2),
                    as_of_date=(datetime.strptime(asof.group(1), "%B %d, %Y").date().isoformat() if asof else m.get("retrieved_at", "")[:10]),
                    reviews_read=n, reviews_last_6_months=r6, negative_last_6_months=n6, negative_older=nold,
                    serious_issue_tags_last_6_months=tg, source_url=u, retrieved_at=m.get("retrieved_at", ""),
                    notes="page shows at most 2 review texts with relative ages; no per-review stars, so 'negative' = a serious issue named under Cons"
                    + ("" if bbl in u else "")), looked
    return None, looked


def main():
    rows = list(csv.DictReader(open(lib.DATA / "reference/evidence_batches/all_candidate_buildings.csv")))
    idx = load_index()
    out = []
    for i, r in enumerate(rows):
        found, looked = [], []
        for fn in (zumper_row, igloo_row):
            row, lk = fn(r, idx)
            looked += lk
            if row:
                found.append(row)
        ar, lk = al_rows(r, idx)
        found += ar; looked += lk
        if not found:
            found = [dict(rating_source="none_found", rating_scale=5, source_url="", retrieved_at=lib.now_iso(),
                          notes="looked at: " + " | ".join(looked) + " | Trulia building pages show no rating")]
        for f in found:
            out.append({**{c: "" for c in COLS}, "addr_key": r["addr_key"], "building_name": r["building_name"], **f})
        print(i, r["addr_key"][:40], [(f["rating_source"][:12], f.get("rating_value"), f.get("review_count")) for f in found], flush=True)
        with open(OUT, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(out)
    print("rows", len(out), "buildings", len(rows))


if __name__ == "__main__":
    main()
