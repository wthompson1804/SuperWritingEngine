"""Resolve pending listings in the three thin years (Walk-Everywhere, Quiet-Street, Fresh-Start).

Read-only on every existing file. Writes only data/evidence_pending/* (and raw/ caches through lib.cached_get).

Run in this order (each step is resumable; a URL already in fetch_log.jsonl is never requested twice):
  select        candidates.csv, candidate_buildings.csv, funnel.json (hood = pipeline method, see hood_lookup)
  fetch         re-read each candidate's own listing page (Apartment List, Zumper, management sites; never Trulia)
  sites         building_sites.csv: each building's own website and how many of its units already pass
  crawl-sites   robots.txt, home page and up to four amenity / pet / FAQ / floor-plan pages of each own site
  secondary     secondary_urls.csv: Zumper address pages and guessed Apartment List pages for buildings not yet on them
  fetch-urls F  fetch the URLs in F (the file written by `secondary`)
  write         confirm/facts/live_check/items _batch_18.csv, resolved_candidates.csv, open_questions_by_building.csv,
                summary.json (all under data/evidence_pending/, NOT data/evidence/, which the repair agent reads)

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


def secondary():
    """Cross-aggregator lookups for buildings still missing elevator or dog facts: the Zumper address page when we hold
    no Zumper row for the building, and a guessed Apartment List property page for named communities."""
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    L["bkey"] = L.apply(building_key, axis=1)
    nk = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())
    L["nkey"] = L.building_name.map(nk) + "|" + L.zip5
    C = pd.read_csv(OUT / "candidates.csv", dtype=str, keep_default_na=False)
    C["nkey"] = C.building_name.map(nk) + "|" + C.zip5
    rows = []
    for bk, g in C.groupby("bkey", sort=False):
        if not set(";".join(g.pending_reasons).split(";")) & {"elevator", "dog"}:
            continue
        srcs = set(L[(L.bkey == bk) | L.nkey.isin(set(g.nkey[g.building_name != ""]))].source_site)
        r = g.iloc[0]
        m = re.match(r"^(.*?),\s*[^,]+,\s*[A-Z]{2}\s*\d{5}", r.address)
        addr = m.group(1) if m else r.address
        if "zumper" not in srcs and re.match(r"^\d", addr):
            rows.append(dict(url=zumper_address_url(addr, r.city, r.state, r.zip5), why="zumper address page|" + bk))
        if "apartmentlist.com" not in srcs and r.building_name and not re.match(r"^\d", r.building_name) and "LLC" not in r.building_name:
            slug = re.sub(r"[^a-z0-9]+", "-", r.building_name.lower().replace("&", "and")).strip("-")
            city = re.sub(r"[^a-z0-9]+", "-", r.city.lower()).strip("-")
            rows.append(dict(url=f"https://www.apartmentlist.com/{r.state.lower()}/{city}/{slug}", why="apartment list guess|" + bk))
    pd.DataFrame(rows).drop_duplicates("url").to_csv(OUT / "secondary_urls.csv", index=False)
    print(len(rows), "secondary urls")


# ---------------------------------------------------------------- evidence -> verdicts
WINDOW_END = "2026-12-15"
ELEV_Q = "Is there a passenger elevator that serves this unit's floor?"
DOG_Q = "Are dogs allowed, and is there a weight limit (must be 25 lb or more)?"
DATE_Q = "Which unit is this and when is it available (must be on or before Dec 15)?"


def vis(t: str) -> str:
    import html as H
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = H.unescape(re.sub(r"<[^>]+>", "|", t))
    return re.sub(r"(\s*\|\s*)+", " | ", re.sub(r"\s+", " ", t))


def around(t: str, m, w: int = 80) -> str:
    return t[max(0, m.start() - w):m.end() + w].strip(" |")


def desc_elevator(desc: str, where: str):
    """A listing's own description text: 'walk-up' / 'no elevator' is a negative, 'elevator' a positive."""
    m = re.search(r"\b(no elevator|walk[- ]?up)\b", desc, re.I)
    if m:
        return (f"{where}: \"{around(desc, m, 70)}\"", "no")
    for m in re.finditer(r"\belevators?\b", desc, re.I):
        c = around(desc, m, 70)
        if not re.search(r"wheelchair|lift|freight|no elevator", c, re.I):
            return (f"{where}: \"{c}\"", "yes")
    return None


def page_elevator(path: str, url: str):
    """Elevator named on a cached page we were allowed to read: (quote, kind) or None. An accessibility or
    wheelchair lift is not an elevator; 'no elevator' / 'walk-up' is returned as a negative."""
    import h_apartmentlist as A
    import h_zumper as Z
    import h_trulia as T
    try:
        raw = (ROOT / path).read_text(errors="replace")
    except Exception:
        return None
    if "apartmentlist.com" in url:
        L = A.parse_listing(raw) or {}
        am = A.amen_names(L, "community_amenities") + A.amen_names(L, "unit_amenities") + A.amen_names(L, "top_amenities")
        hit = [a for a in am if re.fullmatch(r"elevators?", a.strip(), re.I)]
        if hit:
            return (f"Apartment List amenity list: {hit[0]}", "yes")
        return desc_elevator(str(L.get("description") or ""), "Apartment List listing description")
    if "zumper.com" in url:
        st = Z.parse_state(raw) or {}
        d = ((st.get("detail") or {}).get("entity") or {}).get("data") or {}
        tags = (d.get("amenity_tags") or []) + (d.get("building_amenity_tags") or [])
        hit = [a for a in tags if re.search(r"\belevator", a, re.I)]
        if hit:
            return (f"Zumper amenity tag: {hit[0]}", "yes")
        return desc_elevator(str(d.get("description") or ""), "Zumper listing description")
    if "trulia.com" in url:
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw, re.S)
        try:
            hd = json.loads(m.group(1))["props"].get("homeDetails") or {}
            feats = T.flat_features(hd.get("features"))
        except Exception:
            return None
        hit = [f for f in feats if re.search(r"\belevator", str(f[-1]), re.I)]
        if hit:
            return (f"Trulia page feature ({hit[0][0]} / {hit[0][1]}): {hit[0][-1]}"[:200], "yes")
        return desc_elevator(str((hd.get("description") or {}).get("value") or ""), "cached Trulia listing description")
    t = vis(raw)
    m = re.search(r"\b(no elevator|walk[- ]?up)\b", t, re.I)
    if m:
        return (around(t, m), "no")
    for m in re.finditer(r"\belevators?\b", t, re.I):
        c = around(t, m)
        if not re.search(r"wheelchair|accessib\w* lift|freight", c, re.I):
            return (c, "yes")
    return None


def page_dogs(path: str):
    """Own-site wording about dogs: (value, weight, quote). value: yes / conditional / ''."""
    try:
        t = vis((ROOT / path).read_text(errors="replace"))
    except Exception:
        return None
    m = re.search(r"(cats?\s*(and|&|/)\s*dogs?[^|.]{0,40}(welcome|allowed|accepted|friendly)|dogs?\s*(are\s*)?(welcome|allowed|accepted)|"
                  r"(welcome|allow|accept)s?[^|.]{0,30}\bdogs?\b|dog[- ]friendly)", t, re.I)
    if not m:
        return None
    q = around(t, m, 110)
    w = re.search(r"(\d{2,3})\s*(?:-\s*)?(?:lbs?\b|pounds?\b)", q, re.I)
    cond = re.search(r"case[- ]by[- ]case|upon approval|with (management |owner )?approval|subject to approval", q, re.I)
    return ("conditional" if cond else "yes", w.group(1) if w else "", q)


def write():
    import csv
    import h_apartmentlist as A
    import parsers
    C = pd.read_csv(OUT / "candidates.csv", dtype=str, keep_default_na=False)
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    L["bkey"] = L.apply(building_key, axis=1)
    nk = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    L["nkey"] = L.building_name.map(nk) + "|" + L.zip5
    C["nkey"] = C.building_name.map(nk) + "|" + C.zip5
    F = fetched()
    site_pages = {}
    if (OUT / "site_pages.jsonl").exists():
        for line in open(OUT / "site_pages.jsonl"):
            b = json.loads(line)
            site_pages[b["bkey"]] = [p for p in b["pages"] if p.get("path")]
    sec = {}
    if (OUT / "secondary_urls.csv").exists():
        for r in pd.read_csv(OUT / "secondary_urls.csv", dtype=str, keep_default_na=False).itertuples():
            sec.setdefault(r.why.split("|", 1)[1], []).append(r.url)
    blocked_sites = {}
    for line in (open(OUT / "site_pages.jsonl") if (OUT / "site_pages.jsonl").exists() else []):
        b = json.loads(line)
        bad = [p for p in b["pages"] if not p.get("path")]
        if bad and not [p for p in b["pages"] if p.get("path")]:
            blocked_sites[b["bkey"]] = f"{bad[0]['url']} -> {bad[0]['status']}"

    # all-in warning: what this building's already-judged units carry on top of rent (scripts/all_in.py results, read-only)
    M = pd.read_csv(DATA / "master_units.csv", dtype=str, keep_default_na=False,
                    usecols=["building_name", "zip5", "listed_rent", "all_in", "cost_gate"])
    M["over"] = pd.to_numeric(M.all_in, errors="coerce") - pd.to_numeric(M.listed_rent, errors="coerce")
    M["nkey"] = M.building_name.map(nk) + "|" + M.zip5.str.zfill(5)
    overhead = M[M.building_name != ""].groupby("nkey").over.median().dropna().to_dict()

    confirm, facts, live, resolved = [], [], [], []
    for bk, g in C.groupby("bkey", sort=False):
        nks = set(g.nkey[g.building_name != ""])
        X = L[(L.bkey == bk) | L.nkey.isin(nks)]
        r0 = g.iloc[0]
        bname = r0.building_name or r0.address
        akeys = list(dict.fromkeys(g.addr_key))
        looked = []                      # where we looked, for unconfirmed rows

        # ---------- elevator (building level)
        elev = None                      # (value, quote, url, at, how)
        for x in X[(X.elevator.str.lower() == "yes") & (X.elevator_basis == "stated")].itertuples():
            if x.raw_path.endswith((".html", ".htm")):
                pe = page_elevator(x.raw_path, x.url)
                if pe and pe[1] == "yes":
                    elev = ("yes", pe[0], x.url, x.last_seen, f"stated on the {x.source_site} page of the same building (cached harvest page)")
                    break
        if not elev:
            for p in site_pages.get(bk, []):
                pe = page_elevator(p["path"], p["url"])
                if pe:
                    elev = (pe[1], pe[0], p["url"], p["retrieved_at"], "building's own site")
                    break
            looked += [p["url"] for p in site_pages.get(bk, [])]
        if not elev:
            for u in list(dict.fromkeys(g.url)) + sec.get(bk, []):
                f = F.get(u.split("?")[0] if "zumper.com" in u else u)
                if f and f["path"]:
                    looked.append(f["url"])
                    pe = page_elevator(f["path"], f["url"])
                    if pe and (pe[1] == "yes" or f["url"] in set(g.url)):
                        elev = (pe[1], pe[0], f["url"], f["retrieved_at"], "listing / aggregator page of the same address, re-read")
                        break
        if not elev:                    # cached Trulia pages of the candidates themselves (never re-requested)
            for x in g[g.source_site == "trulia"].itertuples():
                pe = page_elevator(x.raw_path, x.url)
                if pe:
                    elev = (pe[1], pe[0], x.url, x.last_seen, "cached Trulia page")
                    break
        if not elev:
            hi = X[(X.floor_basis == "stated") & (pd.to_numeric(X.floor, errors="coerce") >= 6)]
            hi = hi[hi.bkey == bk] if (hi.bkey == bk).any() else hi
            if len(hi):
                x = hi.sort_values("floor", key=lambda s: pd.to_numeric(s)).iloc[-1]
                elev = ("inferred_6plus_floors", f"unit {x.unit} is listed on floor {x.floor} (floor field on the page, not a unit-label guess)",
                        x.url, x.last_seen, "plan rule: a building of 6+ floors is treated as having an elevator, with an asterisk")
        pluto_note = ""
        if r0.elevator_from_class and r0.match_basis != "house_number+location":
            pluto_note = f"PLUTO class {r0.pluto_class} ({r0.elevator_from_class}) rests on a {r0.match_basis} match, not an exact address match"
        if r0.elevator_from_class == "no" and r0.g_elevator == "pass":
            pluto_note = f"CONFLICT: listing page names an elevator but PLUTO class {r0.pluto_class} is a walk-up class ({r0.match_basis})"

        # ---------- dogs (building level)
        dog = None                       # (value, weight, quote, url, at, how)
        yes = X[(X.dogs.str.lower() == "yes") & (X.detail_level != "card")]     # a search card is not a page reading
        no = X[X.dogs.str.lower() == "no"]
        if len(yes) and len(no):
            y, n = yes.iloc[0], no.iloc[0]
            dog = ("conflict", "", f"{y.source_site}: {y.dog_policy_text[:90]} / {n.source_site}: {n.dog_policy_text[:90] or 'dogs not allowed'}",
                   n.url, n.last_seen, "pages for the same building disagree")
        elif len(yes):
            wl = pd.to_numeric(yes.dog_weight_limit_lb, errors="coerce").dropna()
            y = yes[yes.source_site != "trulia"].iloc[0] if (yes.source_site != "trulia").any() else yes.iloc[0]
            # A managed community has one pet policy; a co-op/condo or small building listed unit by unit does not.
            # Another unit's listing counts only for a community (5+ listings of it, or a building-level page).
            community = len(X) >= 5 or yes.detail_level.str.startswith("building").any()
            dog = ("yes" if community else "other_unit_only", str(int(wl.min())) if len(wl) else "", y.dog_policy_text[:220], y.url, y.last_seen,
                   f"dog policy on the {y.source_site} page of the same building" + ("" if y.listing_id in set(g.listing_id) else " (another listing of this building)"))
        if not dog:
            for p in site_pages.get(bk, []):
                pdg = page_dogs(p["path"])
                if pdg:
                    dog = (pdg[0], pdg[1], pdg[2], p["url"], p["retrieved_at"], "building's own site")
                    break

        for k in akeys[:1]:
            if "elevator" in ";".join(g.pending_reasons):
                if elev:
                    confirm.append([k, "elevator", elev[0], elev[1], elev[2], "confirmed" if elev[0] in ("yes", "no") else "unconfirmed"])
                else:
                    confirm.append([k, "elevator", "not stated", "looked at: " + " ; ".join(dict.fromkeys(looked))[:400]
                                    + (f" ; own site blocked: {blocked_sites[bk]}" if bk in blocked_sites else ""), r0.url, "unconfirmed"])
            if "dog" in ";".join(g.pending_reasons):
                if dog:
                    confirm.append([k, "dogs_allowed", dog[0], dog[2], dog[3], {"yes": "confirmed", "conflict": "contradicts"}.get(dog[0], "unconfirmed")])
                    confirm.append([k, "dog_weight_limit", dog[1] or "none stated", dog[2], dog[3], "confirmed" if dog[1] else "unconfirmed"])
                else:
                    confirm.append([k, "dogs_allowed", "not stated", "page says only 'pet friendly' or nothing about dogs", r0.url, "unconfirmed"])
            if pluto_note:
                facts.append([k, "nyc_pluto_note", pluto_note, "", "https://data.cityofnewyork.us/Housing-Development/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks"])

        # ---------- per unit
        passing = L[(L.gate_status == "pass") & ((L.bkey == bk) | L.nkey.isin(nks))]
        unit_tail = lambda u: re.sub(r"^.*[^0-9a-z]", "", str(u).lower()) if re.search(r"\d", str(u)) else ""
        pass_tails = {unit_tail(u): lid for u, lid in zip(passing.unit, passing.listing_id) if unit_tail(u)}
        seen_tails = {}
        for r in g.itertuples():
            reasons = [x for x in r.pending_reasons.split(";") if x]
            opens, fails, how, notes = [], [], [], []
            src_url, checked = r.url, r.last_seen
            # live check: price and date from the listing page itself
            status, price_now, avail_txt, avail_iso = "", "", "", ""
            host = urlparse(r.url).netloc.lower()
            if "trulia.com" in host:
                status = "blocked"
                notes.append("Trulia not requested (blocking us); price and date as on the cached page of " + r.last_seen)
                price_now, avail_txt, avail_iso = r.listed_rent, r.available_date_text or r.available_date, r.available_date
            elif "apartmentlist.com" in host:
                Ld, f = al_listing(r.url)
                checked = (f or {}).get("retrieved_at", checked)
                uid = r.listing_id.rsplit(":", 1)[1]          # "p<rental>-<unit_rental_id tail>" or "p<rental>-u<unit id>"
                hit = None
                for fp in (Ld or {}).get("available_units") or []:
                    for u in fp.get("units") or []:
                        if u.get("unit_rental_id") == uid or uid.endswith(f"-u{u.get('id')}"):
                            hit = u
                if hit is None:
                    status = "gone"
                    notes.append("unit id not on the re-read Apartment List page" if Ld else "re-read page carries no listing")
                else:
                    price_now = str(hit.get("price") or "")
                    avail_iso = "now" if hit.get("available_now") else str(hit.get("available_on") or "")
                    avail_txt = ("available now" if hit.get("available_now") else "") + (f" (available_on {hit.get('available_on')})" if hit.get("available_on") else "")
                    status = "live" if price_now == str(int(float(r.listed_rent))) else "changed"
                    desc = str((Ld or {}).get("description") or "")
                    if len([u for fp in Ld.get("available_units") or [] for u in fp.get("units") or []]) == 1:
                        m = re.search(r"\b(first|ground|1st)[- ]floor (apartment|apt|unit|condo|co-op|home|residence|studio|one|1)|"
                                      r"(located|situated|apartment|unit|condo) (is )?on the (first|ground|1st) floor|"
                                      r"\b(garden|basement)[- ]level (apartment|unit|studio)|\bbasement apartment", desc, re.I)
                        if m:
                            fails.append(f"ground floor: page says \"{around(desc, m, 60)}\"")
            elif "zumper.com" in host:
                d, t, f = zumper_entity(r.url)
                checked = (f or {}).get("retrieved_at", checked)
                lid = re.search(r"(\d+)$", r.listing_id).group(1)
                fps = {str(x.get("listing_id")): x for x in (d or {}).get("floorplan_listings") or []}
                hit = fps.get(lid) or (d if d and str(d.get("listing_id")) == lid else None)
                if hit is None:
                    status = "gone" if d else "blocked"
                    notes.append("floor plan id not on the re-read Zumper page" if d else "Zumper page not parsed")
                else:
                    price_now = str(hit.get("min_price") or hit.get("price") or "")
                    status = "live" if price_now == str(int(float(r.listed_rent))) else "changed"
                    da = hit.get("date_available")
                    avail_iso = str(da)[:10] if da else ""
                    avail_txt = avail_iso or "not stated on the Zumper page"
                    notes.append("Zumper floor-plan row (a 'from' price for a plan), not a numbered unit" if not r.unit else "")
            else:
                f = F.get(r.url) or {}
                raw = (ROOT / f["path"]).read_text(errors="replace") if f.get("path") else ""
                checked_page = f.get("retrieved_at", "")
                p = str(int(float(r.listed_rent)))
                has_price = p in raw or f"{int(p):,}" in raw
                has_unit = bool(r.unit) and r.unit in raw
                price_now, avail_txt, avail_iso = r.listed_rent, r.available_date_text or r.available_date, r.available_date
                if raw and has_price and (has_unit or not r.unit):
                    status, checked = "live", checked_page
                    notes.append("re-read page still shows this price" + (" and unit" if has_unit else " (floor-plan 'from' price)"))
                else:
                    status = "live"
                    notes.append(f"unit list of this site loads from a script feed that was not re-requested; price and date are the "
                                 f"harvester's reading of the site's own unit feed at {r.last_seen}")
            if status == "gone":
                fails.append("no longer listed on the page it came from")
            if price_now and float(price_now) > 3000:
                fails.append(f"price now ${price_now}")

            # facts
            if "elevator" in reasons:
                if elev and elev[0] == "yes":
                    how.append(f"elevator: {elev[1]} [{elev[4]}]")
                    src_url = elev[2]
                elif elev and elev[0] == "inferred_6plus_floors":
                    how.append(f"elevator (asterisk, inferred): {elev[1]} [{elev[4]}]")
                    src_url = elev[2]
                    notes.append("tour question: confirm the elevator")
                elif elev and elev[0] == "no":
                    fails.append(f"no elevator: \"{elev[1][:120]}\"")
                    src_url = elev[2]
                else:
                    opens.append(ELEV_Q)
            if "dog" in reasons:
                if dog and dog[0] == "yes" and (not dog[1] or float(dog[1]) >= 25):
                    how.append(f"dogs: {dog[2][:140]} [{dog[5]}]" + (f"; limit {dog[1]} lb" if dog[1] else "; no weight limit stated"))
                    if re.search(r"small", dog[2], re.I) and not dog[1]:
                        notes.append("size-only 'small dogs' policy: passes per Will, tour question to confirm the limit")
                    src_url = dog[3] if "elevator" not in reasons else src_url
                elif dog and dog[0] == "yes":
                    fails.append(f"dog weight limit {dog[1]} lb (< 25)")
                elif dog and dog[0] == "other_unit_only":
                    opens.append(f"Another unit's listing in this building says \"{dog[2][:80]}\" ({dog[3]}); does that hold for this unit? " + DOG_Q)
                elif dog and dog[0] == "conflict":
                    opens.append("Dog policy conflicts between pages (" + dog[2][:150] + "): which is right?")
                else:
                    opens.append(DOG_Q)
            if "dog" not in reasons and dog and dog[0] == "conflict":
                opens.append("Dog policy conflicts between pages (" + dog[2][:150] + "): which is right?")
            if "movein" in reasons:
                if avail_iso == "now" or (re.match(r"\d{4}-\d\d-\d\d", avail_iso) and avail_iso <= WINDOW_END):
                    how.append(f"availability: {avail_txt} (read from the listing page)")
                elif re.match(r"\d{4}-\d\d-\d\d", avail_iso):
                    fails.append(f"available {avail_iso}, after Dec 15")
                else:
                    opens.append(DATE_Q)
            if "proof" in reasons:
                if status == "live" and "trulia.com" not in host:
                    how.append("listing page re-read")
                else:
                    opens.append("Search-card listing only: the listing page itself has not been read (price, date).")
            # ground floor, from the unit label the same way gates.py reads it
            lab = r.unit or (re.search(r"(?:apt|unit|#)\s*#?\s*([\w-]+)\s*$", r.building_name, re.I) or [None, ""])[1]
            if lab and r.g_floor != "pass":
                fl, kind = parsers.floor_from_label(lab, None)
                if fl is not None and fl < 2:
                    fails.append(f"ground floor (unit label '{lab}', read as gates.py reads labels)")
            if re.search(r"first floor", r.notes, re.I) and not r.unit:
                fails.append("floor plan is described as first floor on the site")
            if pluto_note.startswith("CONFLICT"):
                opens.append(pluto_note + ": " + ELEV_Q)
            elif pluto_note and r.g_elevator == "pass" and r.elevator_basis == "nyc_pluto_building_class":
                opens.append(pluto_note + ": " + ELEV_Q)
            if status == "blocked" and not opens and not fails:
                opens.append("Listing page could not be re-read (Trulia is blocking us): is it still listed at this price and date?")
            if status == "changed":
                notes.append(f"price changed: stored {r.listed_rent}, now {price_now}")
            dup = pass_tails.get(unit_tail(r.unit), "") or seen_tails.get(unit_tail(r.unit), "") if unit_tail(r.unit) else ""
            if unit_tail(r.unit):
                seen_tails.setdefault(unit_tail(r.unit), r.listing_id)
            oh = overhead.get(r.nkey)
            warn = ""
            if oh is not None and float(r.listed_rent) + oh > 3000:
                warn = (f"all-in likely over $3,000: units of this building already judged carry about ${oh:.0f} a month on top of rent "
                        f"(fees, pet rent, parking, utilities), so rent would need to be ${3000 - oh:.0f} or less")
            if fails:
                verdict = "fails (" + "; ".join(fails) + ")"
            elif opens:
                verdict = "still_open (" + " | ".join(opens) + ")"
            else:
                verdict = "now_passes"
            live.append([r.addr_key, r.url, r.unit, status, price_now, avail_txt, "yes" if status == "live" else "no",
                         "", checked, "; ".join(n for n in notes if n)])
            resolved.append([r.listing_id, r.addr_key, bname, r.unit, r.hood, r.year, r.listed_rent, ";".join(reasons),
                             " ; ".join(how), verdict, src_url, checked, dup, len(opens) if not fails else 0,
                             "; ".join(n for n in notes if n), len(passing), warn])
        if len(g):
            Ld = None
            for u in dict.fromkeys(g.url):
                if "apartmentlist.com" in u:
                    Ld, f = al_listing(u)
                    if Ld:
                        for key, lab in (("year_built", "year_built"), ("total_units_count", "building_size"), ("pmc_display_name", "management_company"),
                                         ("rental_type", "listing_type"), ("website_url", "building_site_url")):
                            if Ld.get(key):
                                facts.append([akeys[0], lab, str(Ld.get(key)), f"Apartment List page data field {key}", u])
                        break

    def dump(name, cols, rows):
        with open(OUT / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
    dump("confirm_batch_18.csv", ["addr_key", "fact", "value", "quote", "source_url", "status"], confirm)
    dump("facts_batch_18.csv", ["addr_key", "fact", "value", "quote", "source_url"], facts)
    dump("live_check_batch_18.csv", ["addr_key", "listing_url", "unit", "status", "price_now", "available_now_text", "matches_stored",
                                     "building_site_url", "checked_at", "notes"], live)
    dump("items_batch_18.csv", ["addr_key", "building_name", "category", "item_date", "excerpt", "source_site", "source_url", "about",
                                "retrieved_at"], [])
    dump("resolved_candidates.csv", ["listing_id", "addr_key", "building", "unit", "hood", "year", "rent", "missing_fact", "how_settled",
                                     "verdict", "source_url", "checked_at", "duplicate_of", "open_questions", "notes",
                                     "units_of_building_already_passing", "all_in_warning"], resolved)
    R = pd.DataFrame(resolved, columns=["listing_id", "addr_key", "building", "unit", "hood", "year", "rent", "missing", "how", "verdict",
                                        "src", "at", "dup", "nq", "notes", "npass", "warn"])
    R["v"] = R.verdict.str.split(" ").str[0]
    R["bkey"] = C.set_index("listing_id").bkey.reindex(R.listing_id).values
    print(R.v.value_counts().to_dict())
    print(R.groupby(["year", "v"]).agg(units=("listing_id", "size"), buildings=("bkey", "nunique")).to_string())
    # call sheet: one row per building that is one answer away
    O = R[(R.v == "still_open") & (R.nq == 1)].copy()
    O["question"] = O.verdict.str.replace(r"^still_open \(|\)$", "", regex=True)
    O["rent"] = pd.to_numeric(O.rent)
    cs = O.groupby(["year", "hood", "building", "bkey"]).agg(units=("listing_id", "size"), min_rent=("rent", "min"),
                                                             question=("question", "first"), already_passing_units=("npass", "max"),
                                                             all_in_warning=("warn", lambda x: next((w for w in x if w), "")),
                                                             example_url=("src", "first")).reset_index()
    cs.sort_values(["year", "hood", "units"], ascending=[True, True, False]).drop(columns="bkey").to_csv(OUT / "open_questions_by_building.csv", index=False)
    summary = {"verdicts": R.v.value_counts().to_dict(),
               "now_passes_with_all_in_warning": int(((R.v == "now_passes") & (R.warn != "")).sum()),
               "now_passes_new_units": int(((R.v == "now_passes") & (R.dup == "")).sum()),
               "now_passes_duplicates_of_passing_units": int(((R.v == "now_passes") & (R.dup != "")).sum()),
               "now_passes_by_year_hood_building": {f"{k[0]} | {k[1]} | {k[2]}": {"units": int(v), "new_units": int(n), "already_passing_units_in_building": int(p)}
                                                    for k, v, n, p in [(k, len(x), (x.dup == "").sum(), pd.to_numeric(x.npass).max())
                                                                       for k, x in R[R.v == "now_passes"].groupby(["year", "hood", "building"])]},
               "still_open_single_question_in_buildings_with_no_passing_unit": int(((R.v == "still_open") & (R.nq == 1) & (pd.to_numeric(R.npass) == 0)).sum()),
               "still_open_single_question": int(((R.v == "still_open") & (R.nq == 1)).sum()),
               "still_open_single_question_buildings": int(R[(R.v == "still_open") & (R.nq == 1)].bkey.nunique()),
               "refused_hosts": refused()}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "select"
    if cmd == "select":
        select()
    elif cmd == "fetch":
        fetch_primary()
    elif cmd == "fetch-urls":
        fetch_urls(sys.argv[2])
    elif cmd == "secondary":
        secondary()
    elif cmd == "write":
        write()
    elif cmd == "sites":
        sites()
    elif cmd == "crawl-sites":
        crawl_sites()
