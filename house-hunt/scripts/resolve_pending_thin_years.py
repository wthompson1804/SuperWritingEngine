"""Resolve pending listings in the three thin years (Walk-Everywhere, Quiet-Street, Fresh-Start).

Read-only on every existing file. Writes only data/evidence_pending/* (and raw/ caches through lib.cached_get).

  python3 scripts/resolve_pending_thin_years.py select   -> data/evidence_pending/candidates.csv, candidate_buildings.csv, funnel.json
  python3 scripts/resolve_pending_thin_years.py fetch    -> fetches pages for the selected buildings (resumable)
  python3 scripts/resolve_pending_thin_years.py write    -> the batch-18 files and resolved_candidates.csv

HARD RULE (persisted): one refusal (401/403/429, CAPTCHA, bot wall) from a host ends every request to that host,
also after a restart: data/evidence_pending/refused_hosts.json. trulia.com is pre-refused (blocking us since Nov 15).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import lib  # noqa: E402
from lib import DATA, ROOT, cached_get, now_iso  # noqa: E402
from gates import norm_addr  # noqa: E402

OUT = DATA / "evidence_pending"
OUT.mkdir(exist_ok=True)
REFUSED = OUT / "refused_hosts.json"
REQLOG = OUT / "request_log.jsonl"
THIN = ["The Walk-Everywhere Year", "The Quiet-Street Year", "The Fresh-Start Year"]
RENT_MAX = 2800
MAX_BUILDINGS = 150
SOURCE = "resolve_pending_b18"
OFF_LIMITS = ("trulia.com", "zillow.com", "streeteasy.com", "apartments.com", "apartmentratings.com", "craigslist.org",
              "yelp.com", "reddit.com", "hotpads.com", "rent.com", "renthop.com", "realtor.com", "rentcafe.com",
              "niche.com", "city-data.com", "google.com", "nextdoor.com", "patch.com", "qns.com")
HOST_DELAY = {"www.apartmentlist.com": 3.0, "www.zumper.com": 3.0}
BOT_WALL = re.compile(r"captcha|px-captcha|perimeterx|just a moment\.\.\.|cf-challenge|access denied|are you a robot|"
                      r"unusual traffic|request unsuccessful\. incapsula|attention required", re.I)


# ---------------------------------------------------------------- refusal ledger (persisted)
def refused() -> dict:
    return json.loads(REFUSED.read_text()) if REFUSED.exists() else {}


def base_host(host: str) -> str:
    p = host.lower().split(":")[0].split(".")
    return ".".join(p[-2:])


def mark_refused(host: str, why: str, url: str) -> None:
    r = refused()
    r.setdefault(base_host(host), {"why": why, "url": url, "at": now_iso()})
    REFUSED.write_text(json.dumps(r, indent=1))


def polite_get(url: str, *, refresh: bool = False, ext: str = "html"):
    """Returns (bytes|None, meta). Never retries a refusal; never requests an off-limits or refused host."""
    host = urlparse(url).netloc.lower()
    bh = base_host(host)
    if any(bh == o or host.endswith("." + o) for o in OFF_LIMITS):
        return None, {"url": url, "status": "off_limits"}
    if bh in refused():
        return None, {"url": url, "status": "host_refused_earlier"}
    lib.HOST_DELAY.setdefault(host, HOST_DELAY.get(host, 3.0))
    try:
        content, meta = cached_get(url, SOURCE, ext=ext, refresh=refresh, retries=1, timeout=40,
                                   headers={"Accept": "text/html,application/xhtml+xml"})
    except RuntimeError as e:  # lib raises after a 429/5xx (retries=1 -> no second request) or a network error
        st = "429" if "HTTP 429" in str(e) else "error"
        if st == "429":
            mark_refused(host, "HTTP 429", url)
        meta = {"url": url, "status": st, "err": str(e)[:200], "retrieved_at": now_iso()}
        with open(REQLOG, "a") as f:
            f.write(json.dumps(meta) + "\n")
        return None, meta
    status = meta.get("status")
    head = content[:6000].decode("utf-8", "ignore") if content else ""
    wall = status in (401, 403, 429) or (len(content) < 20000 and BOT_WALL.search(head))
    if wall:
        mark_refused(host, f"HTTP {status}" + (" bot wall text" if status == 200 else ""), url)
        if status == 200:  # do not keep a wall page as if it were content
            p = ROOT / meta["path"]
            p.unlink(missing_ok=True)
            Path(str(p).rsplit(".", 1)[0] + ".meta.json").unlink(missing_ok=True)
        meta = dict(meta, status=f"refused_{status}")
        content = None
    with open(REQLOG, "a") as f:
        f.write(json.dumps({k: meta.get(k) for k in ("url", "status", "retrieved_at", "path")}) + "\n")
    return (content if status == 200 and not wall else None), meta


# ---------------------------------------------------------------- selection
def building_key(r) -> str:
    """Building = street address without the unit (some harvesters put '#555' in the address) + ZIP."""
    a = str(r.address)
    m = re.match(r"^(.*?),\s*[^,]+,\s*[A-Z]{2}\s*\d{5}", a)   # Zumper style: "515 West Ave, Norwalk, CT 06850, USA"
    if m:
        a = m.group(1)
    a = re.sub(r"\s*(#|apt\.?|unit|suite|ste\.?)\s*[\w-]+\s*$", "", a, flags=re.I)
    return norm_addr(a) + "|" + r.zip5


def hood_lookup(C: pd.DataFrame) -> pd.DataFrame:
    """Same method as scripts/build_neighborhoods.py (imported read-only): NYC 2020 NTA polygon inside the city, else
    Census incorporated place, else county subdivision, from the listing's coordinates. Fallback for rows without
    coordinates: ZIP -> the hood that passing units in that ZIP were assigned to (hood_basis says which)."""
    from shapely.geometry import Point
    from build_neighborhoods import nta_polys
    from build_areas import census_geo, first
    ntas = nta_polys()
    U = pd.read_csv(DATA / "units.csv", dtype=str, keep_default_na=False, usecols=["zip5", "hood_id", "hood"])
    U["zip5"] = U.zip5.str.zfill(5)
    zmap = U[U.hood_id != ""].groupby("zip5").hood_id.agg(lambda s: s.value_counts().index[0]).to_dict()
    cache_p = OUT / "hood_cache.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    # Prefilter so the Census geocoder is asked about ~hundreds of buildings, not 2,700: a building is geocoded only
    # if it lies within 10 km of a passing unit of a thin-year neighborhood or its listing city equals such a
    # neighborhood's name. NYC needs no geocoder call: a point inside an NTA polygon is in New York city.
    G = pd.read_csv(DATA / "lifestyle_groups.csv", dtype=str, keep_default_na=False)
    thin_ids = set(G[G.group_label.isin(THIN)].hood_id)
    thin_names = {h.split(":", 1)[1].replace("-", " ").strip() for h in thin_ids}
    UU = pd.read_csv(DATA / "units.csv", dtype=str, keep_default_na=False, usecols=["hood_id", "lat", "lon"])
    UU = UU[UU.hood_id.isin(thin_ids)]
    pts = np.array([[float(a), float(b)] for a, b in zip(UU.lat, UU.lon) if a and b])

    def near(lat, lon):
        d = np.hypot((pts[:, 0] - lat) * 111.3, (pts[:, 1] - lon) * 111.3 * np.cos(np.radians(lat)))
        return d.min() <= 10

    for i, (bk, g) in enumerate(C.groupby("bkey")):
        if bk in cache:
            continue
        r = g.iloc[0]
        try:
            lat, lon = float(r.lat), float(r.lon)
        except ValueError:
            hid = zmap.get(r.zip5, "")
            cache[bk] = [hid, "zip_fallback (no coordinates)" if hid else "none"]
            continue
        p = Point(lon, lat)
        hit = [n for n, b, poly in ntas if poly.contains(p)]
        if hit:
            cache[bk] = [re.sub(r"[^a-z0-9:]+", "-", ("ny:" + hit[0]).lower()), "pipeline_method (NYC NTA polygon from coordinates)"]
            continue
        if not (near(lat, lon) or r.city.lower().strip() in thin_names):
            cache[bk] = ["", "not geocoded: >10 km from any thin-year passing unit and city name differs"]
            continue
        try:
            geo, _ = census_geo(lat, lon)
        except Exception:  # geocoder hiccup: fall back, say so
            hid = zmap.get(r.zip5, "")
            cache[bk] = [hid, "zip_fallback (geocoder error)" if hid else "none"]
            continue
        if first(geo, "Incorporated Places") == "New York city":
            name = "New York city (unmatched)"
        else:
            name = first(geo, "Incorporated Places") or first(geo, "County Subdivisions")
            for suf in (" city", " village", " town", " borough", " township", " CDP"):
                name = name[:-len(suf)] if name.endswith(suf) else name
        st = first(geo, "States", "STUSAB") or r.state
        hid = re.sub(r"[^a-z0-9:]+", "-", (st + ":" + name).lower())
        cache[bk] = [hid, "pipeline_method (Census place from coordinates)"]
        if i % 50 == 0:
            cache_p.write_text(json.dumps(cache))
    cache_p.write_text(json.dumps(cache))
    C["hood_id"] = C.bkey.map(lambda k: cache[k][0])
    C["hood_basis"] = C.bkey.map(lambda k: cache[k][1])
    return C


def select():
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    funnel = {"all_listings": len(L)}
    P = L[L.gate_status == "pending"].copy()
    funnel["pending"] = len(P)
    P = P[P.g_type == "pass"]
    funnel["studio_or_1br"] = len(P)
    P["rent"] = pd.to_numeric(P.listed_rent.str.replace(r"[$,]", "", regex=True), errors="coerce")
    P = P[P.rent <= RENT_MAX]
    funnel[f"rent_le_{RENT_MAX}"] = len(P)
    P = P[P.g_movein.isin(["pass", "unknown"])]
    funnel["available_by_dec15_or_unstated"] = len(P)
    P["n_unstated"] = P.pending_reasons.map(lambda s: len([x for x in s.split(";") if x]))
    P = P[(P.fail_reasons == "") & P.n_unstated.between(1, 2)]
    funnel["one_or_two_unstated_none_failed"] = len(P)
    P["bkey"] = P.apply(building_key, axis=1)
    funnel["  buildings_at_that_point"] = P.bkey.nunique()
    P = hood_lookup(P)
    G = pd.read_csv(DATA / "lifestyle_groups.csv", dtype=str, keep_default_na=False)
    T = G[G.group_label.isin(THIN)]
    cut = set(T[T.safety_cut == "True"].hood_id)
    funnel["in_thin_year_hood_incl_crime_cut"] = int(P.hood_id.isin(T.hood_id).sum())
    funnel["  of_which_in_crime_cut_hoods"] = {h: int((P.hood_id == h).sum()) for h in sorted(cut)}
    T = T[T.safety_cut != "True"]
    P = P[P.hood_id.isin(T.hood_id)].copy()
    P["year"] = P.hood_id.map(dict(zip(T.hood_id, T.group_label)))
    P["hood"] = P.hood_id.map(dict(zip(T.hood_id, T.hood)))
    funnel["in_thin_year_hood_passing_safety"] = len(P)
    funnel["  hood_basis"] = P.hood_basis.value_counts().to_dict()
    funnel["  by_year_listings"] = P.year.value_counts().to_dict()
    funnel["candidate_buildings"] = P.bkey.nunique()
    funnel["  by_year_buildings"] = P.groupby("year").bkey.nunique().to_dict()
    funnel["  by_pending_reason"] = P.pending_reasons.value_counts().to_dict()
    B = P.groupby("bkey").agg(n_units=("listing_id", "size"), min_rent=("rent", "min"), year=("year", "first"),
                              hood_id=("hood_id", "first"), hood=("hood", "first"),
                              building_name=("building_name", lambda s: next((x for x in s if x), "")),
                              address=("address", "first"), city=("city", "first"), state=("state", "first"),
                              zip5=("zip5", "first"), sources=("source_site", lambda s: ";".join(sorted(set(s)))),
                              reasons=("pending_reasons", lambda s: ";".join(sorted(set(";".join(s).split(";")))))).reset_index()
    B = B.sort_values(["n_units", "min_rent"], ascending=[False, True]).reset_index(drop=True)
    B["rank"] = B.index + 1
    B["taken"] = B["rank"] <= MAX_BUILDINGS
    funnel["buildings_taken"] = int(B.taken.sum())
    P = P[P.bkey.isin(B[B.taken].bkey)]
    funnel["candidate_units_in_taken_buildings"] = len(P)
    B.to_csv(OUT / "candidate_buildings.csv", index=False)
    P.to_csv(OUT / "candidates.csv", index=False)
    (OUT / "funnel.json").write_text(json.dumps(funnel, indent=1))
    print(json.dumps(funnel, indent=1))


# ---------------------------------------------------------------- fetch
FETCHLOG = OUT / "fetch_log.jsonl"


def fetched() -> dict:
    d = {}
    if FETCHLOG.exists():
        for line in open(FETCHLOG):
            r = json.loads(line)
            d[r["url"]] = r
    return d


def get_logged(url: str, why: str, *, refresh: bool = True):
    """One request per URL per session (resumable: a URL already in fetch_log.jsonl is not requested again)."""
    done = fetched()
    if url in done:
        return done[url]
    content, meta = polite_get(url, refresh=refresh)
    rec = {"url": url, "why": why, "status": meta.get("status"), "path": meta.get("path") if content else "",
           "retrieved_at": meta.get("retrieved_at", now_iso()), "bytes": len(content) if content else 0}
    with open(FETCHLOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def zumper_address_url(address: str, city: str, state: str, zip5: str) -> str:
    a = re.sub(r"[#,].*", "", address).strip().lower()
    for x, y in [("avenue", "ave"), ("street", "st"), ("boulevard", "blvd"), ("road", "rd"), ("drive", "dr"),
                 ("terrace", "ter"), ("place", "pl"), ("lane", "ln"), ("north ", "n "), ("east ", "e "), ("west ", "w "),
                 ("south ", "s "), ("highway", "hwy")]:
        a = re.sub(r"\b" + x.strip() + r"\b", y.strip(), a)
    return "https://www.zumper.com/address/" + re.sub(r"[^a-z0-9]+", "-", f"{a} {city} {state} {zip5} usa".lower()).strip("-")


def fetch_primary():
    """Re-read each candidate's own listing page (Apartment List, Zumper, management sites). Trulia is never requested."""
    C = pd.read_csv(OUT / "candidates.csv", dtype=str, keep_default_na=False)
    urls = {}
    for r in C.itertuples():
        host = urlparse(r.url).netloc.lower()
        if "trulia.com" in host:
            continue
        mgmt = not ("apartmentlist.com" in host or "zumper.com" in host)
        u = r.url.split("?")[0] if "zumper.com" in host else r.url
        if mgmt and r.building_url:
            urls.setdefault(r.building_url, "building page")
        urls.setdefault(u, "listing page")
    print(len(urls), "primary urls;", len(fetched()), "already logged")
    for n, (u, why) in enumerate(urls.items()):
        rec = get_logged(u, why)
        if n % 20 == 0:
            print(n, rec["status"], u[:90], flush=True)
    print("refused hosts:", refused())


def fetch_urls(path: str):
    """Fetch the URLs listed in a small CSV (url, why): secondary pages chosen after reading the primary ones."""
    for r in pd.read_csv(path, dtype=str, keep_default_na=False).itertuples():
        rec = get_logged(r.url, r.why)
        print(rec["status"], rec["bytes"], r.url[:100], flush=True)
    print("refused hosts:", refused())


# ---------------------------------------------------------------- own sites
def next_data(path: str) -> dict:
    """homeDetails from a cached Trulia page (never fetched here)."""
    try:
        h = (ROOT / path).read_text(errors="replace")
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
        return json.loads(m.group(1))["props"].get("homeDetails") or {}
    except Exception:
        return {}


def al_listing(url: str):
    import h_apartmentlist as A
    r = fetched().get(url)
    if not r or not r["path"]:
        return None, r
    return A.parse_listing((ROOT / r["path"]).read_text(errors="replace")), r


def zumper_entity(url: str):
    import h_zumper as Z
    r = fetched().get(url.split("?")[0])
    if not r or not r["path"]:
        return None, None, r
    t = (ROOT / r["path"]).read_text(errors="replace")
    st = Z.parse_state(t) or {}
    return (((st.get("detail") or {}).get("entity") or {}).get("data") or {}), t, r


def sites():
    """Per building: its own website (Apartment List `website_url`, Zumper `homepage`, the link on the cached Trulia
    page, or the management site we harvested from) and how many units of the same building already pass."""
    C = pd.read_csv(OUT / "candidates.csv", dtype=str, keep_default_na=False)
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    L = L[L.gate_status == "pass"].copy()
    L["bkey"] = L.apply(building_key, axis=1)
    pb = L.groupby("bkey").size().to_dict()
    nk = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    pn = L[L.building_name != ""].groupby([L.building_name.map(nk), "zip5"]).size().to_dict()
    rows = []
    for bk, g in C.groupby("bkey", sort=False):
        site = ""
        for u in dict.fromkeys(g.url):
            if "apartmentlist.com" in u:
                Ld, _ = al_listing(u)
                site = site or ((Ld or {}).get("website_url") or "")
            elif "zumper.com" in u:
                d, _, _ = zumper_entity(u)
                site = site or ((d or {}).get("homepage") or "")
        for r in g.itertuples():
            if r.source_site == "trulia" and not site:
                hd = next_data(r.raw_path)
                site = ((hd.get("description") or {}).get("additionalInfoHyperlink") or {}).get("url") or ""
            if not site and r.building_url and not re.search(r"trulia|zumper|apartmentlist", r.building_url):
                site = r.building_url
        r0 = g.iloc[0]
        rows.append(dict(bkey=bk, name=r0.building_name, hood_id=r0.hood_id, year=r0.year, n=len(g),
                         sources=";".join(sorted(set(g.source_site))),
                         reasons=";".join(sorted(set(";".join(g.pending_reasons).split(";")))), site=site,
                         pass_same_addr=pb.get(bk, 0),
                         pass_same_name=pn.get((nk(r0.building_name), r0.zip5), 0) if r0.building_name else 0))
    pd.DataFrame(rows).to_csv(OUT / "building_sites.csv", index=False)
    print(len(rows), "buildings;", sum(1 for r in rows if r["site"]), "with an own site")


_robots = {}


def robots_ok(url: str) -> bool:
    """robots.txt of the host; the Claude-User group if there is one, else `*` (docs/SOURCES.md, targeted lookups).
    A refused robots.txt ends the host (polite_get marks it); a missing one (404) means no rules."""
    from urllib import robotparser
    pu = urlparse(url)
    host = pu.netloc.lower()
    if host not in _robots:
        rec = get_logged(f"{pu.scheme}://{host}/robots.txt", "robots", refresh=False)
        rp = robotparser.RobotFileParser()
        if rec["path"]:
            rp.parse((ROOT / rec["path"]).read_text(errors="replace").splitlines())
        elif str(rec["status"]) in ("404", "410"):
            rp.parse([])
        else:
            rp = None      # refused, or unreachable: do not go on
        _robots[host] = rp
        if rp:
            cd = rp.crawl_delay("Claude-User") or rp.crawl_delay("*")
            if cd:
                lib.HOST_DELAY[host] = max(float(cd), 3.0)
    rp = _robots[host]
    return bool(rp) and all(rp.can_fetch(ua, url) for ua in ("Claude-User", "ClaudeBot"))


TRACK = re.compile(r"[?&](rcstdid|utm_[a-z]+|built_in|switch_cls\[id\])=[^&#]*", re.I)
LINK_WANT = [r"amenit", r"pet", r"faq", r"feature", r"floor-?plans?", r"availab"]


def clean_site(u: str) -> str:
    u = u.strip()
    if not u.startswith("http"):
        u = "https://" + u
    u = TRACK.sub("", u).split("#")[0]
    return re.sub(r"/\?$|\?$", "/", u) if u.endswith("?") else u


def crawl_sites(max_links: int = 4):
    """Home page of each building's own site plus up to four same-host pages whose link names amenities, pets, FAQ,
    features or floor plans. Result: site_pages.jsonl (bkey, url, path, status)."""
    from urllib.parse import urljoin
    B = pd.read_csv(OUT / "building_sites.csv", dtype=str, keep_default_na=False)
    out = OUT / "site_pages.jsonl"
    done = {json.loads(l)["bkey"] for l in open(out)} if out.exists() else set()
    for b in B[B.site != ""].itertuples():
        if b.bkey in done:
            continue
        home = clean_site(b.site)
        pages = []
        if "securecafe.com" in home or "rentcafe.com" in home:
            pages.append({"url": home, "status": "off_limits (RentCafe)", "path": ""})
        elif not robots_ok(home):
            pages.append({"url": home, "status": "robots_disallow_or_refused", "path": ""})
        else:
            rec = get_logged(home, "own site home")
            pages.append(rec)
            if rec["path"] and "propertyware.com" not in home:
                t = (ROOT / rec["path"]).read_text(errors="replace")
                host = urlparse(home).netloc
                links = {}
                for m in re.finditer(r'<a\b[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', t, re.S | re.I):
                    u = urljoin(home, m.group(1)).split("#")[0]
                    label = re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip().lower()
                    if urlparse(u).netloc != host or re.search(r"\.(pdf|jpg|png|webp)$", u, re.I) or u.rstrip("/") == home.rstrip("/"):
                        continue
                    for rank, w in enumerate(LINK_WANT):
                        if re.search(w, urlparse(u).path.lower()) or re.search(w, label):
                            links.setdefault(u, rank)
                            break
                for u in [u for u, _ in sorted(links.items(), key=lambda kv: kv[1])][:max_links]:
                    if robots_ok(u):
                        pages.append(get_logged(u, "own site page"))
        with open(out, "a") as f:
            f.write(json.dumps({"bkey": b.bkey, "name": b.name, "pages": pages}) + "\n")
        print(b.name[:40], [(str(p["status"]), p["url"][-50:]) for p in pages][:5], flush=True)
    print("refused hosts:", refused())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "select"
    if cmd == "select":
        select()
    elif cmd == "fetch":
        fetch_primary()
    elif cmd == "fetch-urls":
        fetch_urls(sys.argv[2])
    elif cmd == "sites":
        sites()
    elif cmd == "crawl-sites":
        crawl_sites()
