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
    a = re.sub(r"\s*(#|apt\.?|unit|suite|ste\.?)\s*[\w-]+\s*$", "", str(r.address), flags=re.I)
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
    for i, (bk, g) in enumerate(C.groupby("bkey")):
        if bk in cache:
            continue
        r = g.iloc[0]
        try:
            lat, lon = float(r.lat), float(r.lon)
        except ValueError:
            hid = zmap.get(r.zip5, "")
            cache[bk] = [hid, "zip_fallback" if hid else "none"]
            continue
        try:
            geo, _ = census_geo(lat, lon)
        except Exception as e:  # geocoder hiccup: fall back, say so
            hid = zmap.get(r.zip5, "")
            cache[bk] = [hid, "zip_fallback(geocoder error)" if hid else "none"]
            continue
        if first(geo, "Incorporated Places") == "New York city":
            p = Point(lon, lat)
            hit = [n for n, b, poly in ntas if poly.contains(p)]
            name = hit[0] if hit else "New York city (unmatched)"
        else:
            name = first(geo, "Incorporated Places") or first(geo, "County Subdivisions")
            for suf in (" city", " village", " town", " borough", " township", " CDP"):
                name = name[:-len(suf)] if name.endswith(suf) else name
        st = first(geo, "States", "STUSAB") or r.state
        hid = re.sub(r"[^a-z0-9:]+", "-", (st + ":" + name).lower())
        cache[bk] = [hid, "pipeline_method(census place / NYC NTA from coordinates)"]
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


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "select"
    if cmd == "select":
        select()
    else:
        import resolve_pending_fetch as F  # noqa: F401  (kept in this file below in the final version)
