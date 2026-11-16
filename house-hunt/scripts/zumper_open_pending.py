#!/usr/bin/env python3
"""Open the Zumper listings that were only ever seen as search cards (owner request, 2026-11-16).

Read-only on every existing script and data file. Writes only:
  data/listings_pending/zumper_open_selection.csv      the selected rows and the fetch order
  data/listings_pending/zumper_open_funnel.json        the selection funnel
  data/listings_pending/zumper_open_requests.jsonl     one line per request (resumable; the cap counts these)
  data/listings_pending/zumper_open_hood_cache.json    building -> neighborhood
  data/listings_pending/zumper_opened.csv              layout of data/listings_raw/zumper.csv + extra columns at the end
  data/listings_pending/zumper_opened_summary.csv      per listing: status and a preview of each gate
  raw/zumper_open_pending/                             page cache (lib.cached_get), raw/_host_kill_shared.json

  python3 scripts/zumper_open_pending.py select    # funnel + ordered URL list (no zumper.com request)
  python3 scripts/zumper_open_pending.py fetch     # paced fetch, hard cap 900 requests in total, resumable
  python3 scripts/zumper_open_pending.py build     # parse every page on disk -> the two CSVs (no network)
  python3 scripts/zumper_open_pending.py report    # counts for the hand-off

HARD RULE: before every request raw/_host_kill_shared.json is read (and the other agent's
data/evidence_pending/refused_hosts.json); if zumper.com is listed, nothing is requested. One refusal here (401/403/429,
CAPTCHA, bot wall, challenge page) is written there at once and ends zumper.com for good, also after a restart.
Nothing is retried and nothing is bypassed.

Parsers: imported read-only from scripts/h_zumper.py (parse_state, visible_text, facts_from, fees_block,
parse_fee_text, iso_avail, photo, ltype, load_cards, to_path). `unit_row` below is a COPY of the closure of the same
name inside h_zumper.build() (a closure cannot be imported); the differences are marked "DIFF".
Gates: the functions of scripts/gates.py, imported read-only and applied per row.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import html as htmllib
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))
import lib  # noqa: E402
import h_zumper as hz  # noqa: E402  (read-only import; sets lib.HOST_DELAY for zumper to 2.2, raised below)

HOST = "www.zumper.com"
KILL_KEY = "zumper.com"
lib.HOST_DELAY[HOST] = 4.0          # floor between requests; a random 0.5-2.5 s is added on top of it
JITTER = (0.5, 2.5)
CAP = 900                           # hard cap on requests to zumper.com by this script, across restarts
SRC = "zumper_open_pending"
RENT_SELECT = 2800
OUT = lib.DATA / "listings_pending"
SEL_F = OUT / "zumper_open_selection.csv"
FUNNEL_F = OUT / "zumper_open_funnel.json"
REQ_F = OUT / "zumper_open_requests.jsonl"
HOOD_F = OUT / "zumper_open_hood_cache.json"
OPENED_F = OUT / "zumper_opened.csv"
SUMMARY_F = OUT / "zumper_opened_summary.csv"
KILL_F = lib.RAW / "_host_kill_shared.json"
OTHER_LEDGER = lib.DATA / "evidence_pending" / "refused_hosts.json"
BOT_WALL = re.compile(r"captcha|px-captcha|perimeterx|just a moment\.\.\.|cf-challenge|challenge-platform|access denied|"
                      r"are you a robot|unusual traffic|incapsula|attention required|verify you are human", re.I)
EXTRA = ["leasing_phone", "listing_updated", "listed_on", "office_hours", "building_year_built", "building_units",
         "card_listed_rent", "page_kind", "selected_card_row", "hood_id", "hood_basis", "listings_csv_id"]
COLS = list(hz.COLS) + EXTRA


# ---------------------------------------------------------------- shared kill file
def kill_state() -> dict:
    """host -> record, merged from the shared file and the other agent's own ledger (read-only)."""
    if not KILL_F.exists():
        try:
            fd = os.open(KILL_F, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, b"{}\n")
            os.close(fd)
        except FileExistsError:
            pass
    out = {}
    for f in (OTHER_LEDGER, KILL_F):
        try:
            d = json.loads(f.read_text() or "{}")
            if isinstance(d, dict):
                out.update(d)
        except (OSError, json.JSONDecodeError):
            if f == KILL_F and f.exists() and f.read_text().strip():
                # unreadable shared file: treat as a stop rather than guess
                out["zumper.com"] = {"status": "kill file unreadable", "time": lib.now_iso(), "url": ""}
    return out


def zumper_killed():
    k = kill_state()
    for key, v in k.items():
        if key.lower().endswith("zumper.com"):
            return v
    return None


def write_kill(status: str, url: str) -> None:
    try:
        d = json.loads(KILL_F.read_text() or "{}") if KILL_F.exists() else {}
        if not isinstance(d, dict):
            d = {}
    except json.JSONDecodeError:
        d = {}
    d.setdefault(KILL_KEY, {"time": lib.now_iso(), "status": status, "url": url, "by": "scripts/zumper_open_pending.py"})
    tmp = KILL_F.with_suffix(".json.tmp%d" % os.getpid())
    tmp.write_text(json.dumps(d, indent=1) + "\n")
    os.replace(tmp, KILL_F)


# ---------------------------------------------------------------- cache lookup (any raw/ folder)
def cache_key(url: str) -> str:
    return hashlib.sha1(("GET " + url + " ").encode()).hexdigest()[:16]


_ANY = None


def cached_anywhere(url: str):
    """(path, meta) of a 200 copy of this exact URL under raw/<any source>/, newest first, or (None, None)."""
    global _ANY
    if _ANY is None:
        _ANY = defaultdict(list)
        for f in glob.glob(str(lib.RAW / "*" / "_index.jsonl")):
            for line in open(f, errors="replace"):
                if "zumper.com" not in line:
                    continue
                try:
                    m = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if m.get("status") == 200 and m.get("path"):
                    _ANY[m["url"]].append(m)
    own = lib.RAW / SRC / f"{cache_key(url)}.html"
    cands = list(_ANY.get(url, []))
    mp = own.with_name(own.stem + ".meta.json")
    if own.exists() and mp.exists():
        cands.append(json.loads(mp.read_text()))
    cands = [m for m in cands if (lib.ROOT / m["path"]).exists()]
    if not cands:
        return None, None
    m = max(cands, key=lambda m: m.get("retrieved_at", ""))
    return lib.ROOT / m["path"], m


def req_log() -> list:
    return [json.loads(x) for x in open(REQ_F)] if REQ_F.exists() else []


# ---------------------------------------------------------------- selection
def building_key(address: str, zip5: str) -> str:
    """Street address without the unit + ZIP (same idea as resolve_pending_thin_years.building_key)."""
    from gates import norm_addr
    a = str(address)
    m = re.match(r"^(.*?),\s*[^,]+,\s*[A-Z]{2}\s*\d{5}", a)
    if m:
        a = m.group(1)
    a = re.sub(r"\s*(#|apt\.?|unit|suite|ste\.?)\s*[\w-]+\s*$", "", a, flags=re.I)
    return norm_addr(a) + "|" + zip5


def hood_for(rows, need_all=False):
    """rows: iterable of dicts with bkey, lat, lon, city, state, zip5. Returns {bkey: (hood_id, basis)}.

    Method = scripts/build_neighborhoods.py (nta_polys imported read-only) + build_areas.census_geo: NYC 2020 NTA
    polygon from the coordinates inside the city, else the Census incorporated place / county subdivision from the
    coordinates. To keep the Census geocoder load small, a building outside New York City is geocoded only when it
    lies within 10 km of a passing unit of a safety-cut neighborhood or its city name equals such a neighborhood's
    name (need_all=True geocodes every building given). Rows without coordinates fall back to ZIP -> the neighborhood
    that passing units in that ZIP have (basis says so)."""
    import numpy as np
    import pandas as pd
    from shapely.geometry import Point
    from build_neighborhoods import nta_polys
    from build_areas import census_geo, first
    cache = json.loads(HOOD_F.read_text()) if HOOD_F.exists() else {}
    ntas = nta_polys()
    U = pd.read_csv(lib.DATA / "units.csv", dtype=str, keep_default_na=False, usecols=["zip5", "hood_id", "lat", "lon"])
    U["zip5"] = U.zip5.str.zfill(5)
    zmap = U[U.hood_id != ""].groupby("zip5").hood_id.agg(lambda s: s.value_counts().index[0]).to_dict()
    G = pd.read_csv(lib.DATA / "lifestyle_groups.csv", dtype=str, keep_default_na=False)
    cut = set(G[G.safety_cut == "True"].hood_id)
    cut_names = {h.split(":", 1)[1].replace("-", " ").strip() for h in cut}
    UC = U[U.hood_id.isin(cut)]
    pts = np.array([[float(a), float(b)] for a, b in zip(UC.lat, UC.lon) if a and b])

    def near(lat, lon):
        d = np.hypot((pts[:, 0] - lat) * 111.3, (pts[:, 1] - lon) * 111.3 * np.cos(np.radians(lat)))
        return d.min() <= 10

    n = 0
    for r in rows:
        bk = r["bkey"]
        if bk in cache and not (need_all and cache[bk][1].startswith("not geocoded")):
            continue
        try:
            lat, lon = float(r["lat"]), float(r["lon"])
        except (ValueError, TypeError):
            hid = zmap.get(r["zip5"], "")
            cache[bk] = [hid, "zip_fallback (no coordinates)" if hid else "none (no coordinates, ZIP has no passing unit)"]
            continue
        hit = [nm for nm, b, poly in ntas if poly.contains(Point(lon, lat))]
        if hit:
            cache[bk] = [re.sub(r"[^a-z0-9:]+", "-", ("ny:" + hit[0]).lower()), "pipeline_method (NYC NTA polygon from coordinates)"]
            continue
        if not need_all and not (near(lat, lon) or str(r["city"]).lower().strip() in cut_names):
            cache[bk] = ["", "not geocoded: outside NYC and >10 km from every passing unit of a safety-cut neighborhood"]
            continue
        try:
            geo, _ = census_geo(lat, lon)
        except Exception:
            hid = zmap.get(r["zip5"], "")
            cache[bk] = [hid, "zip_fallback (geocoder error)" if hid else "none (geocoder error)"]
            continue
        if first(geo, "Incorporated Places") == "New York city":
            name = "New York city (unmatched)"
        else:
            name = first(geo, "Incorporated Places") or first(geo, "County Subdivisions")
            for suf in (" city", " village", " town", " borough", " township", " CDP"):
                name = name[:-len(suf)] if name.endswith(suf) else name
        st = first(geo, "States", "STUSAB") or r["state"]
        cache[bk] = [re.sub(r"[^a-z0-9:]+", "-", (st + ":" + name).lower()), "pipeline_method (Census place from coordinates)"]
        n += 1
        if n % 40 == 0:
            HOOD_F.write_text(json.dumps(cache))
    HOOD_F.write_text(json.dumps(cache))
    return cache


def select():
    import pandas as pd
    OUT.mkdir(exist_ok=True)
    L = pd.read_csv(lib.DATA / "listings.csv", dtype=str, keep_default_na=False)
    fun = {"listings_csv_rows": len(L)}
    Z = L[L.source_site == "zumper"]
    fun["zumper_rows"] = len(Z)
    P = Z[(Z.g_proof == "unknown") & (Z.gate_status == "pending")].copy()
    fun["unopened (g_proof unknown, gate_status pending)"] = len(P)
    P = P[P.g_type == "pass"]
    fun["studio_or_1br"] = len(P)
    P["rent"] = pd.to_numeric(P.listed_rent.str.replace(r"[$,]", "", regex=True), errors="coerce")
    P = P[P.rent <= RENT_SELECT]
    fun[f"card_rent_le_{RENT_SELECT}"] = len(P)
    P = P[P.fail_reasons == ""]
    fun["no_gate_failing"] = len(P)
    P["path"] = P.url.map(hz.to_path)
    P = P[P.path != ""]
    fun["robots_allowed_detail_url"] = len(P)
    P["bkey"] = [building_key(a, z) for a, z in zip(P.address, P.zip5)]
    fun["  buildings (address+ZIP)"] = int(P.bkey.nunique())
    hc = hood_for(P.drop_duplicates("bkey").to_dict("records"))
    P["hood_id"] = P.bkey.map(lambda k: hc[k][0])
    P["hood_basis"] = P.bkey.map(lambda k: hc[k][1])
    G = pd.read_csv(lib.DATA / "lifestyle_groups.csv", dtype=str, keep_default_na=False)
    cut = set(G[G.safety_cut == "True"].hood_id)
    fun["  in_safety_cut_neighborhood"] = {h: int(n) for h, n in P[P.hood_id.isin(cut)].hood_id.value_counts().items()}
    P = P[~P.hood_id.isin(cut)].copy()
    fun["not_in_safety_cut_neighborhood"] = len(P)
    fun["  hood_basis"] = {k: int(v) for k, v in P.hood_basis.str.replace(r":.*", "", regex=True).value_counts().items()}
    P["group_label"] = P.hood_id.map(dict(zip(G.hood_id, G.group_label))).fillna("")

    cards, _ = hz.load_cards()
    cards = {f"zumper-{k}": v["card"] for k, v in cards.items()}
    P["page_kind"] = P.path.map(lambda p: "building" if p.startswith("/apartment-buildings/") else "listing")
    P["floorplans"] = [int((cards.get(i.split(":")[-1]) or {}).get("floorplan_count") or 1) for i in P.listing_id]
    P["card_unknowns"] = ((P.g_dog != "pass").astype(int) + (P.g_elevator != "pass").astype(int)
                          + (P.g_movein != "pass").astype(int))
    fun["distinct_detail_urls"] = int(P.path.nunique())
    fun["  building_pages"] = int(P[P.page_kind == "building"].path.nunique())
    fun["  listing_pages"] = int(P[P.page_kind == "listing"].path.nunique())
    # one line per URL
    rows_at = P.groupby("bkey").size()
    U = P.groupby("path").agg(page_kind=("page_kind", "first"), state=("state", "first"), n_rows=("listing_id", "size"),
                              listing_ids=("listing_id", lambda s: " ".join(s)), bkey=("bkey", "first"),
                              floorplans=("floorplans", "max"), min_rent=("rent", "min"),
                              card_unknowns=("card_unknowns", "min"), hood_id=("hood_id", "first"),
                              hood_basis=("hood_basis", "first"), group_label=("group_label", "first")).reset_index()
    U["units_est"] = [max(int(rows_at[b]), int(fp) if k == "building" else 1) for b, fp, k in zip(U.bkey, U.floorplans, U.page_kind)]
    U["cached"] = [cached_anywhere(hz.BASE + p)[0] is not None for p in U.path]
    fun["  already_cached_under_raw"] = int(U.cached.sum())
    fun["urls_to_request"] = int((~U.cached).sum())
    fun["  to_request_by_state"] = {k: int(v) for k, v in U[~U.cached].state.value_counts().items()}
    # expected value: most candidate units first, then fewest gate facts the card leaves open (move-in, dogs,
    # elevator), then building pages (they carry the policy block) before single listings, then lower rent
    U["is_listing"] = (U.page_kind == "listing").astype(int)
    U = U.sort_values(["units_est", "card_unknowns", "is_listing", "min_rent", "path"], ascending=[False, True, True, True, True])
    U["rank_in_state"] = U.groupby("state").cumcount()
    U["frac"] = (U.rank_in_state + 0.5) / U.groupby("state").path.transform("size")
    U = U.sort_values(["frac", "state"]).reset_index(drop=True)      # every state advances at the same share
    U["order"] = range(1, len(U) + 1)
    U.drop(columns=["frac"]).to_csv(SEL_F, index=False)
    fun["request_cap"] = CAP
    fun["  within_cap_by_state"] = {k: int(v) for k, v in U[~U.cached].head(CAP).state.value_counts().items()}
    fun["  within_cap_page_kind"] = {k: int(v) for k, v in U[~U.cached].head(CAP).page_kind.value_counts().items()}
    FUNNEL_F.write_text(json.dumps(fun, indent=1))
    print(json.dumps(fun, indent=1))


# ---------------------------------------------------------------- fetch
def fetch(limit: int | None = None):
    sel = list(csv.DictReader(open(SEL_F)))
    log = req_log()
    done = {r["url"] for r in log if r.get("outcome") in ("ok", "gone", "unparsed", "no_entity")}
    n_req = sum(1 for r in log if r.get("counted"))
    errors = unparsed_run = 0
    made = 0
    lf = open(REQ_F, "a")

    def note(rec):
        lf.write(json.dumps(rec) + "\n")
        lf.flush()

    for row in sel:
        url = hz.BASE + row["path"]
        if url in done or cached_anywhere(url)[0] is not None:
            continue
        if n_req >= CAP:
            print(f"cap of {CAP} requests reached")
            break
        if limit is not None and made >= limit:
            break
        k = zumper_killed()
        if k:
            print("STOP: zumper.com is in the kill file:", k)
            break
        time.sleep(random.uniform(*JITTER))
        n_req += 1
        made += 1
        rec = {"url": url, "order": row["order"], "counted": True, "requested_at": lib.now_iso()}
        try:
            content, meta = lib.cached_get(url, SRC, ext="html", retries=1, timeout=40,
                                           headers={"Accept": "text/html,application/xhtml+xml"})
        except RuntimeError as e:
            msg = str(e)
            if "HTTP 429" in msg:
                write_kill("HTTP 429", url)
                note(dict(rec, status=429, outcome="blocked"))
                print("REFUSED (429). zumper.com is closed for the session.", url)
                break
            errors += 1
            note(dict(rec, status="error", outcome="error", err=msg[-160:]))
            if errors >= 3:
                print("3 network/5xx errors: stopping (not a refusal; safe to rerun later)")
                break
            continue
        status = meta.get("status")
        text = content.decode("utf8", "replace") if content else ""
        has_state = "__PRELOADED_STATE__" in text
        rec.update(status=status, retrieved_at=meta.get("retrieved_at"), path=meta.get("path"), bytes=len(content or b""))
        if status in (401, 403, 429) or (status == 200 and not has_state and BOT_WALL.search(text[:20000])):
            write_kill(f"HTTP {status}" + (" bot wall / challenge page" if status == 200 else ""), url)
            if status == 200:   # never keep a wall page as content
                p = lib.ROOT / meta["path"]
                p.unlink(missing_ok=True)
                p.with_name(p.stem + ".meta.json").unlink(missing_ok=True)
            note(dict(rec, outcome="blocked"))
            print(f"REFUSED ({status}). zumper.com is closed for the session.", url)
            break
        errors = 0
        if status in (404, 410):
            note(dict(rec, outcome="gone"))
            unparsed_run = 0
        elif status != 200:
            note(dict(rec, outcome="error"))
        elif not has_state:
            unparsed_run += 1
            note(dict(rec, outcome="unparsed"))
            if unparsed_run >= 3:
                write_kill("3 consecutive 200 pages without page data (suspected challenge page)", url)
                print("STOP: three pages in a row without page data; treated as a refusal.")
                break
        else:
            unparsed_run = 0
            st = hz.parse_state(text)
            ent = (((st or {}).get("detail") or {}).get("entity") or {}).get("data")
            note(dict(rec, outcome="ok" if ent else "no_entity"))
        if made % 25 == 0:
            print(f"{lib.now_iso()} requests this run {made}, total {n_req}/{CAP}", flush=True)
        if made % 100 == 0:
            try:
                build(quiet=True)
            except Exception as e:  # the fetch must not die on a parse problem
                print("build during fetch failed:", repr(e))
    lf.close()
    print(f"fetch finished: requests this run {made}, total {n_req}")


# ---------------------------------------------------------------- parse (copy of h_zumper.build's unit_row)
def d_utc(ts):
    try:
        return datetime.fromtimestamp(int(ts), timezone.utc).date().isoformat() if ts else ""
    except (ValueError, OSError, TypeError):
        return ""


def base_row(lid, url, seen, raw_path):
    r = {c: "" for c in COLS}
    r.update(listing_id=f"zumper-{lid}", source_site="zumper", url=hz.BASE + url, detail_level="detail",
             first_seen=seen, last_seen=seen, raw_path=raw_path, dogs="unknown", elevator="unknown",
             listing_type="unknown", price_basis="base_rent_monthly")
    return r


def fill_common(r, f, block):
    for k in ("dogs", "dog_policy_text", "dog_weight_limit_lb", "elevator", "building_floors", "parking_type",
              "utilities_included", "laundry"):
        r[k] = f[k]
    lines, pet, park = hz.parse_fee_text(block)
    r["pet_rent"], r["parking_fee"] = pet, park
    blob = {}
    mon = [x for x in lines if x["cadence"] == "monthly"]
    if mon:
        blob["monthly"] = [{k: v for k, v in x.items() if v and k != "cadence"} for x in mon]
    oth = [x for x in lines if x["cadence"] != "monthly"]
    if oth:
        blob["non_monthly"] = [{"name": x["name"], "amount": x["amount"], "cadence": x["cadence"],
                                "requirement": x["requirement"]} for x in oth]
    if f["_fees"]:
        blob["page_data_fees"] = f["_fees"]
    if f.get("_ambig_util"):
        blob["utility_tags_unclear_if_included"] = f["_ambig_util"]
    r["other_monthly_fees_json"] = json.dumps(blob, ensure_ascii=False) if blob else ""


def unit_row(L, url, seen, raw_path, bld, f, block, kind, cards, seen_day):
    loc = L.get("listing_location") or {}
    r = base_row(L["listing_id"], url, seen, raw_path)
    fill_common(r, f, block)
    notes = list(f.get("_notes") or [])
    r["building_name"] = (bld or {}).get("name") or L.get("building_name") or ""
    addr = loc.get("formatted_address") or L.get("address") or (bld or {}).get("formatted_address") or ""
    r["address"] = addr
    r["city"] = loc.get("city") or (bld or {}).get("city") or ""
    r["state"] = loc.get("state") or (bld or {}).get("state") or ""
    r["zip"] = loc.get("zipcode") or (bld or {}).get("zipcode") or ""
    r["lat"] = loc.get("lat") or (bld or {}).get("lat") or ""
    r["lon"] = loc.get("lng") or (bld or {}).get("lng") or ""
    unit = loc.get("unit") or ""
    title = L.get("title") or ""
    if not unit:
        m = re.search(r"(?:#|\b(?:Unit|Apt\.?|APT|Apartment)\s*#?\s*)([A-Za-z]?\d+[A-Za-z]?|\d*[A-Za-z]{1,2}\d*)\b",
                      (L.get("address") or "") + " | " + title)
        if m:
            unit = m.group(1)
            notes.append("unit parsed from title/address")
    unit = re.sub(r"^(?:#|\s|unit|apt\.?|apartment)+", "", str(unit), flags=re.I).strip(" #")
    r["unit"] = unit
    r["floor"] = loc.get("floor") if loc.get("floor") is not None else ""
    if r["floor"] == "":
        ORD = (r"(ground|first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th|sixth|6th|seventh|7th|"
               r"eighth|8th|ninth|9th|tenth|10th|\d{1,2}(?:st|nd|rd|th))")
        own = (L.get("description") or "") + " " + (L.get("short_description") or "") + " " + title
        m = re.search(r"\b(?:located|situated|unit|apartment|apt|studio|bedroom|home|residence|is) (?:is )?"
                      r"(?:conveniently )?(?:located |situated )?on the " + ORD + r"[- ]floor\b", own, re.I) or \
            re.search(r"\b" + ORD + r"[- ]floor (?:unit|apartment|apt|studio|one[- ]bedroom|1[- ]?(?:br|bed(?:room)?)|"
                      r"walk[- ]?up|corner|rear|front)\b", own, re.I)
        if m:
            w = m.group(1).lower()
            n = {"ground": 1, "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
                 "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}.get(w)
            if n is None and w[0].isdigit():
                n = int(re.match(r"\d+", w).group(0))
            if n:
                r["floor"] = n
                notes.append(f"floor from description text: '{m.group(0)}'" + (" (ground)" if w == "ground" else ""))
        else:
            m = re.search(r"\b" + ORD + r"[- ]floor\b", own, re.I)
            if m:
                notes.append(f"floor text in description (not used): '{m.group(0)}'")
    r["beds"] = L.get("bedrooms") if L.get("bedrooms") is not None else ""
    hb = L.get("half_bathrooms") or 0
    ba = L.get("bathrooms")
    r["baths"] = (ba + 0.5 * hb) if ba is not None else ""
    r["sqft"] = L.get("square_feet") or (L.get("unit_data") or {}).get("min_square_feet") or ""
    card = cards.get(L.get("listing_id")) or {}
    if r["sqft"] == "":
        cs = card.get("card", {}).get("min_square_feet")
        if cs:
            notes.append(f"sqft absent on detail page; search card showed {cs}")
    price = L.get("min_price") if L.get("min_price") is not None else L.get("price")
    r["listed_rent"] = price
    if L.get("max_price") and L.get("max_price") != price:
        notes.append(f"price range {price}-{L['max_price']}")
    if L.get("fee_uplift"):
        notes.append(f"fee_uplift={L['fee_uplift']}")
    if L.get("base_min_price") is not None and L.get("base_min_price") != price:
        notes.append(f"base_min_price={L['base_min_price']}")
    sp = (bld or {}).get("specials") or L.get("specials")
    conc = []
    if sp:
        conc.append(json.dumps(sp, ensure_ascii=False)[:400])
    if f.get("_conc"):
        conc.append("tags: " + ", ".join(f["_conc"]))
    r["concession_text"] = " ; ".join(conc)
    # DIFF: "now" is judged against the day the page was read, not the day the CSV is built
    r["available_date_text"], r["available_date"] = hz.iso_avail(L.get("date_available"), seen_day)
    mgr = L.get("brokerage_name") or (bld or {}).get("brokerage_name") or ""
    ag = (L.get("listing_agents") or (bld or {}).get("agents") or [{}])[0] or {}
    r["manager"] = mgr or ag.get("company_name") or ag.get("long_name") or (bld or {}).get("agent_name") or ""
    lo = L.get("listed_on") or L.get("created_on")
    if lo:
        r["listing_age_days"] = max(0, (seen_day - datetime.fromtimestamp(lo, timezone.utc).date()).days)
    if L.get("created_on") and L.get("listed_on") and L["created_on"] != L["listed_on"]:
        notes.append("created_on=" + datetime.fromtimestamp(L["created_on"], timezone.utc).date().isoformat())
    r["photo_url"] = hz.photo(L.get("media")) or hz.photo((bld or {}).get("media"))
    if bld and bld.get("pb_id"):
        r["building_url"] = f"{hz.BASE}/apartment-buildings/p{bld['pb_id']}/{bld.get('pb_url')}"
    r["listing_type"] = hz.ltype(kind, L.get("property_type"), L.get("feed_name"), None)
    if L.get("feed_name") or (bld or {}).get("feed_name"):
        notes.append("feed=" + str(L.get("feed_name") or bld.get("feed_name")))
    if L.get("provider_url"):
        notes.append("provider_url=" + L["provider_url"])
    if L.get("lease_terms"):
        notes.append("lease_terms=" + str(L["lease_terms"])[:80])
    if L.get("active_units"):
        notes.append(f"active_units={L['active_units']}")
    if L.get("income_restrictions_json") or (bld or {}).get("income_restrictions"):
        notes.append("income_restricted")
    desc = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", L.get("description") or "")))
    if not desc and bld:
        desc = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", bld.get("description") or "")))
    keys = re.compile(r"\b(fees?|pets?|dogs?|cats?|lbs?|pounds|floor|elevator|walk[- ]?up|utilit\w+|included|"
                      r"available|parking|garage|heat|hot water|move[- ]in)\b", re.I)
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\s[•*-]\s", desc) if keys.search(x)]
    if sents:
        notes.append("desc: " + " / ".join(sents)[:500])
    if r["elevator"] == "unknown" and re.search(r"walk[- ]?up|no elevator", desc, re.I):
        r["elevator"] = "no"
        notes.append("elevator=no from description (walk-up / no elevator)")
    if r["elevator"] == "unknown" and re.search(r"\belevator\b", desc, re.I) and not re.search(r"no elevator", desc, re.I):
        notes.append("description mentions elevator (not an amenity tag)")
    if r["dogs"] == "unknown" and re.search(r"\bno (pets|dogs)\b|pets? (are )?not (allowed|permitted)", desc, re.I):
        r["dogs"] = "no"
        r["dog_policy_text"] = (r["dog_policy_text"] + " ; description says no pets/dogs").strip(" ;")
    if not r["dog_weight_limit_lb"]:
        for x in sents:
            wm = re.search(r"(\d{2,3})\s*(?:lbs?|pounds?)\b", x, re.I)
            if wm and re.search(r"pet|dog|weight|breed", x, re.I):
                r["dog_weight_limit_lb"] = wm.group(1)
                notes.append("weight limit from description")
                break
    # DIFF: the page-data pet policy carries `max_wt_in_lbs`, which the harvester's "NN lb" pattern does not see.
    # Used only when no limit was found above: the largest limit among the dog entries that are allowed.
    if not r["dog_weight_limit_lb"]:
        pp = L.get("pet_policy") or (bld or {}).get("pet_policy") or []
        ws = [p.get("max_wt_in_lbs") for p in pp if isinstance(p, dict) and "dog" in str(p.get("type", "")).lower()
              and p.get("ok") and p.get("max_wt_in_lbs")]
        if ws:
            r["dog_weight_limit_lb"] = int(max(ws))
            notes.append("weight limit from page-data pet_policy max_wt_in_lbs")
    # ---- extra columns
    r["leasing_phone"] = L.get("phone") or (bld or {}).get("phone") or ag.get("phone") or ""
    r["listing_updated"] = d_utc(L.get("modified_on") or (bld or {}).get("modified_on"))
    r["listed_on"] = d_utc(L.get("listed_on"))
    hrs = L.get("hours") or (bld or {}).get("hours")
    r["office_hours"] = json.dumps(hrs)[:300] if hrs else ""
    r["building_year_built"] = (bld or {}).get("year_built") or ""
    r["building_units"] = (bld or {}).get("units") or ""
    r["page_kind"] = kind
    r["notes"] = "; ".join(notes)
    return r


def akey(r):
    a = re.split(r",", str(r["address"]))[0].lower()
    a = re.sub(r"\s*(#|\b(?:apt|unit|apartment|ste|suite|fl|floor)\b\.?).*$", "", a)
    a = re.sub(r"[^a-z0-9 ]", "", a)
    a = re.sub(r"\s+", " ", a).strip()
    return (a, str(r["zip"]).zfill(5)[:5]) if a and re.match(r"\d", a) else None


def gate_preview(r, drive):
    import gates
    ns = SimpleNamespace(**{k: ("" if v is None else str(v)) for k, v in r.items()})
    ns.community_building_type = ""
    ns.pluto_floors = ""
    el, el_basis = gates.gate_elevator(ns)
    fl, floor_used, fl_basis, _ = gates.gate_floor(ns)
    z = str(r["zip"]).zfill(5)[:5]
    dm = drive.get(z)
    g = {"g_type": gates.gate_type(ns), "g_rent": gates.gate_rent(ns), "g_movein": gates.gate_movein(ns),
         "g_dog": gates.gate_dog(ns), "g_elevator": el, "g_floor": fl,
         "g_place": "unknown" if dm is None else ("pass" if dm <= gates.MAX_DRIVE_MIN else "fail"),
         "elevator_basis": el_basis, "floor_used": floor_used, "floor_basis": fl_basis}
    return g


def build(quiet=False):
    import gates  # noqa: F401  (import check)
    OUT.mkdir(exist_ok=True)
    sel = list(csv.DictReader(open(SEL_F)))
    cards, _ = hz.load_cards()
    card_ids = {f"zumper-{k}" for k in cards}
    drive = {z: dm for z, _, _, dm in hz.load_grid()}
    log = {}
    for rec in req_log():
        log[rec["url"]] = rec
    L = {r["listing_id"]: r for r in csv.DictReader(open(lib.DATA / "listings.csv"))
         if r["source_site"] == "zumper" and r["detail_level"] == "card"}
    rows, summ, sel_id = {}, {}, {}
    for s in sel:
        url = hz.BASE + s["path"]
        ids = s["listing_ids"].split()
        tail = {i.split(":")[-1]: i for i in ids}     # region-harvester rows carry ids like rs:<slug>:zumper-<n>
        path, meta = cached_anywhere(url)
        rec = log.get(url)

        def mark(status, note="", ids=ids):
            for i in ids:
                summ[i] = {"listing_id": i, "url": url, "status": status, "note": note, "selected_card_row": "yes",
                           "page_retrieved_at": (meta or rec or {}).get("retrieved_at", ""),
                           "card_listed_rent": (L.get(i) or {}).get("listed_rent", ""),
                           "state": s["state"], "hood_id": s["hood_id"], "group_label": s["group_label"]}
        if path is None:
            if rec and rec.get("outcome") == "gone":
                mark("gone", f"HTTP {rec.get('status')}")
            elif rec and rec.get("outcome") == "blocked":
                mark("blocked", f"HTTP {rec.get('status')}")
            elif rec and rec.get("outcome") == "unparsed":
                mark("unparsed", "HTTP 200 without page data")
            elif rec and rec.get("outcome") == "error":
                mark("not_requested", "network or 5xx error; not retried")
            else:
                mark("not_requested", "")
            continue
        text = path.read_text("utf8", "replace")
        st = hz.parse_state(text)
        ent = (((st or {}).get("detail") or {}).get("entity") or {}).get("data") if st else None
        if not st:
            mark("unparsed", "page has no readable __PRELOADED_STATE__")
            continue
        if not ent:
            mark("gone", "page loads but carries no listing or building (redirected to a search or removed page)")
            continue
        vt = hz.visible_text(text)
        seen = meta["retrieved_at"]
        seen_day = datetime.fromisoformat(seen).date()
        rawp = meta["path"]
        mark("gone", "not among the active units on its page")     # overwritten below when the unit is found
        if ent.get("__typename") == "Building" or s["path"].startswith("/apartment-buildings/"):
            f = hz.facts_from(ent, vt, None, "")
            block = hz.fees_block(vt)
            for U in ent.get("floorplan_listings") or []:
                lid = f"zumper-{U.get('listing_id')}"
                why = ""
                if U.get("listing_status") != 1:
                    why = ("gone", "inactive on the building page")
                elif U.get("bedrooms") is None or U["bedrooms"] > 1:
                    why = ("opened", "page shows 2+ bedrooms (or none stated); not written to zumper_opened.csv")
                else:
                    p = U.get("min_price") if U.get("min_price") is not None else U.get("price")
                    if p is None or p > hz.MAX_RENT:
                        why = ("opened", f"page price {p} is over $3,000 (or absent); not written to zumper_opened.csv")
                if why:
                    sid = tail.get(lid)
                    if sid:
                        summ[sid].update(status=why[0], note=why[1])
                        if why[0] == "opened":
                            g = "type" if "bedrooms" in why[1] else "rent"
                            summ[sid].update(preview_status="fail", fail_gates=g, **{"g_" + g: "fail"})
                    continue
                fu = hz.facts_from(U, vt, ent, "")
                for k in ("dogs", "dog_policy_text", "dog_weight_limit_lb", "elevator", "building_floors"):
                    fu[k] = f[k]
                fu["_notes"] = f["_notes"]
                r = unit_row(U, s["path"], seen, rawp, ent, fu, block, "building", cards, seen_day)
                if lid in tail:
                    sel_id[lid] = tail[lid]
                r["selected_card_row"] = "yes" if lid in tail else ("no (other card row)" if lid in card_ids else "no (unit found on the building page)")
                r["hood_id"], r["hood_basis"] = s["hood_id"], s["hood_basis"]
                rows[lid] = r
        else:
            lid = f"zumper-{ent.get('listing_id')}"
            target = tail.get(lid) or ids[0]
            if ent.get("listing_status") not in (1, None):
                summ[target].update(status="gone", note=f"listing_status={ent.get('listing_status')} (inactive) on its page")
                continue
            p = ent.get("min_price") if ent.get("min_price") is not None else ent.get("price")
            if ent.get("bedrooms") is None or ent["bedrooms"] > 1:
                summ[target].update(status="opened", g_type="fail", preview_status="fail", fail_gates="type",
                                    note="page shows 2+ bedrooms (or none stated); not written to zumper_opened.csv")
                continue
            if p is None or p > hz.MAX_RENT:
                summ[target].update(status="opened", g_rent="fail", preview_status="fail", fail_gates="rent",
                                    note=f"page price {p} is over $3,000 (or absent); not written to zumper_opened.csv")
                continue
            bld, bvt, bblock = None, "", ""
            if ent.get("pb_id") and ent.get("pb_url"):
                bp, _bm = cached_anywhere(f"{hz.BASE}/apartment-buildings/p{ent['pb_id']}/{ent['pb_url']}")
                if bp:
                    bst = hz.parse_state(bp.read_text("utf8", "replace"))
                    bld = ((((bst or {}).get("detail") or {}).get("entity") or {}).get("data")) or None
                    if bld:
                        bvt = hz.visible_text(bp.read_text("utf8", "replace"))
                        bblock = hz.fees_block(bvt)
            f = hz.facts_from(ent, vt, bld, bvt)
            r = unit_row(ent, s["path"], seen, rawp, bld, f, hz.fees_block(vt) or bblock, "listing", cards, seen_day)
            if lid != target.split(":")[-1]:
                r["notes"] = (r["notes"] + f"; page listing_id {lid} differs from the card row {target}").strip("; ")
            sel_id[lid] = target
            r["selected_card_row"] = "yes"
            r["hood_id"], r["hood_basis"] = s["hood_id"], s["hood_basis"]
            rows[lid] = r

    # building facts settled on a detail page apply to the other opened rows at the same street address
    # (same rule as h_zumper.build: dogs only from a building page with a visible policy, elevator from any page)
    settled = {}
    for r in rows.values():
        k = akey(r)
        if not k:
            continue
        d = settled.setdefault(k, {})
        if r["page_kind"] == "building" and r["dogs"] in ("yes", "no") and "rests on the code only" not in r["dog_policy_text"]:
            d.setdefault("dogs", (r["dogs"], r["dog_policy_text"], r["dog_weight_limit_lb"], r["url"]))
        if r["elevator"] == "yes":
            d.setdefault("elevator", r["url"])
        if r["building_floors"] != "":
            d.setdefault("floors", (r["building_floors"], r["url"]))
    for r in rows.values():
        d = settled.get(akey(r) or ())
        if not d:
            continue
        add = []
        if "dogs" in d and d["dogs"][3] != r["url"] and (r["dogs"] == "unknown" or "rests on the code only" in r["dog_policy_text"]):
            if r["dogs"] != d["dogs"][0]:
                prev = r["dogs"]
                r["dogs"], r["dog_weight_limit_lb"] = d["dogs"][0], d["dogs"][2] or r["dog_weight_limit_lb"]
                r["dog_policy_text"] = f"from building page {d['dogs'][3]}: {d['dogs'][1]}"[:1200]
                add.append(f"dogs applied from building page at same address (was {prev})")
        if "elevator" in d and r["elevator"] == "unknown":
            r["elevator"] = "yes"
            add.append(f"elevator=yes applied from {d['elevator']} (same address)")
        if "floors" in d and r["building_floors"] == "":
            r["building_floors"] = d["floors"][0]
            add.append(f"building_floors applied from {d['floors'][1]}")
        if add:
            r["notes"] = "; ".join(x for x in [r["notes"]] + add if x)

    grid = set(drive)
    out_rows = []
    first_seen = {i: r["first_seen"] for i, r in L.items()}
    for zid, r in rows.items():
        lid = sel_id.get(zid, zid)                    # the id this row has in data/listings.csv, when it has one
        r["listings_csv_id"] = lid if lid in L else ""
        r["card_listed_rent"] = (L.get(lid) or {}).get("listed_rent", "")
        if first_seen.get(lid):
            r["first_seen"] = min(first_seen[lid], r["first_seen"])
        g = gate_preview(r, drive)
        base = summ.get(lid) or {"listing_id": lid, "url": r["url"], "selected_card_row": r["selected_card_row"],
                                 "page_retrieved_at": r["last_seen"], "card_listed_rent": r["card_listed_rent"],
                                 "state": r["state"], "hood_id": r["hood_id"], "group_label": ""}
        dog_basis = ""
        if r["dogs"] == "yes":
            t = r["dog_policy_text"]
            dog_basis = ("code_only" if "rests on the code only" in t else
                         "building_page_same_address" if t.startswith("from building page") else
                         "policy_block" if "Policy | Allowed" in t else "amenity_chip")
        opens = [k[2:] for k in ("g_rent", "g_movein", "g_dog", "g_elevator", "g_place") if g[k] == "unknown"]
        fails = [k[2:] for k in ("g_type", "g_rent", "g_movein", "g_dog", "g_elevator", "g_floor", "g_place") if g[k] == "fail"]
        in_grid = str(r["zip"]).zfill(5)[:5] in grid
        base.update(status="opened", note="" if in_grid else "ZIP on the page is outside the search grid; not written to zumper_opened.csv",
                    url=r["url"], page_retrieved_at=r["last_seen"], building_key="|".join(akey(r) or (r["address"], str(r["zip"]))),
                    building_name=r["building_name"], address=r["address"], unit=r["unit"], beds=r["beds"],
                    listed_rent=r["listed_rent"], available_date=r["available_date"], dogs=r["dogs"], dog_basis=dog_basis,
                    dog_weight_limit_lb=r["dog_weight_limit_lb"], elevator=r["elevator"], floor=r["floor"],
                    rent_le_2800="yes" if gates.to_num(r["listed_rent"]) is not None and gates.to_num(r["listed_rent"]) <= RENT_SELECT else "no",
                    fail_gates=";".join(fails), unknown_gates=";".join(opens), n_unknown=len(opens),
                    preview_status="fail" if fails else ("pending" if opens else "pass"),
                    state=r["state"], hood_id=r["hood_id"] or base.get("hood_id", ""), **g)
        summ[lid] = base
        if in_grid:
            out_rows.append(r)
    out_rows.sort(key=lambda r: (drive.get(str(r["zip"]).zfill(5)[:5], 999), r["listing_id"]))
    tmp = OPENED_F.with_suffix(".tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out_rows)
    os.replace(tmp, OPENED_F)
    scol = ["listing_id", "url", "status", "g_type", "g_rent", "g_movein", "g_dog", "g_elevator", "g_floor", "g_place",
            "preview_status", "fail_gates", "unknown_gates", "n_unknown", "selected_card_row", "note", "page_retrieved_at",
            "state", "hood_id", "group_label", "building_key", "building_name", "address", "unit", "beds", "card_listed_rent",
            "listed_rent", "rent_le_2800", "available_date", "dogs", "dog_basis", "dog_weight_limit_lb", "elevator",
            "elevator_basis", "floor", "floor_used", "floor_basis"]
    tmp = SUMMARY_F.with_suffix(".tmp")
    with open(tmp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=scol, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(summ.values(), key=lambda x: (x["status"], x["listing_id"])))
    os.replace(tmp, SUMMARY_F)
    if not quiet:
        print("opened rows written:", len(out_rows), "| summary:", dict(Counter(x["status"] for x in summ.values())))


def report():
    import pandas as pd
    S = pd.read_csv(SUMMARY_F, dtype=str, keep_default_na=False)
    log = req_log()
    print("requests:", sum(1 for r in log if r.get("counted")), dict(Counter(str(r.get("outcome")) for r in log)))
    print("selected card rows by status:", S[S.selected_card_row == "yes"].status.value_counts().to_dict())
    O = S[S.status == "opened"].copy()
    print("opened rows (incl. units found on building pages):", len(O), O.selected_card_row.value_counts().to_dict())
    print("preview:", O.preview_status.value_counts().to_dict())
    for g in ("g_type", "g_rent", "g_movein", "g_dog", "g_elevator", "g_floor", "g_place"):
        print(" ", g, O[g].value_counts().to_dict())
    # lifestyle group for rows that pass or are one fact away: geocode those buildings (pipeline method)
    need = O[(O.preview_status == "pass") | ((O.preview_status == "pending") & (O.n_unknown == "1"))]
    R = {}
    for r in csv.DictReader(open(OPENED_F)):
        R[r["listing_id"]] = r
        if r["listings_csv_id"]:
            R[r["listings_csv_id"]] = r
    recs, seen = [], set()
    for i in need.listing_id:
        r = R.get(i)
        if not r:
            continue
        bk = "open:" + "|".join(akey(r) or (r["address"], r["zip"]))
        if bk not in seen:
            seen.add(bk)
            recs.append({"bkey": bk, "lat": r["lat"], "lon": r["lon"], "city": r["city"], "state": r["state"],
                         "zip5": str(r["zip"]).zfill(5)[:5]})
    hc = hood_for(recs, need_all=True)
    G = pd.read_csv(lib.DATA / "lifestyle_groups.csv", dtype=str, keep_default_na=False)
    gl, cutset = dict(zip(G.hood_id, G.group_label)), set(G[G.safety_cut == "True"].hood_id)

    def hood(i):
        r = R.get(i)
        if not r:
            return ""
        return hc.get("open:" + "|".join(akey(r) or (r["address"], r["zip"])), ["", ""])[0]
    need = need.copy()
    need["hood_final"] = need.listing_id.map(hood)
    need["group"] = need.hood_final.map(lambda h: gl.get(h, "(neighborhood not in lifestyle_groups.csv)"))
    need["cut"] = need.hood_final.isin(cutset)
    need.to_csv(OUT / "zumper_opened_pass_or_one_open.csv", index=False)
    P = need[need.preview_status == "pass"]
    print("PASS every listing gate (floor pass or unknown):", len(P), "units in", P.building_key.nunique(), "buildings;",
          "of which in a safety-cut neighborhood:", int(P.cut.sum()))
    P = P[~P.cut]
    print("  after safety cut:", len(P), "units /", P.building_key.nunique(), "buildings; rent<=2800:",
          int((P.rent_le_2800 == "yes").sum()), "; floor unknown:", int((P.g_floor == "unknown").sum()),
          "; dog basis:", P.dog_basis.value_counts().to_dict(), "; elevator basis:", P.elevator_basis.value_counts().to_dict())
    print("  by state:", {k: (len(g), g.building_key.nunique()) for k, g in P.groupby("state")})
    print("  by group:", {k: (len(g), g.building_key.nunique()) for k, g in P.groupby("group")})
    Q = need[(need.preview_status == "pending") & ~need.cut]
    print("ONE fact open:", len(Q), "units /", Q.building_key.nunique(), "buildings:", Q.unknown_gates.value_counts().to_dict())
    print("  by state:", {k: (len(g), g.building_key.nunique()) for k, g in Q.groupby("state")})
    allp = O[O.preview_status == "pending"]
    print("pending by open facts:", allp.unknown_gates.value_counts().to_dict())
    print("fails:", O[O.preview_status == "fail"].fail_gates.value_counts().to_dict())


if __name__ == "__main__":
    a = sys.argv[1:]
    stage = a[0] if a else ""
    if stage == "select":
        select()
    elif stage == "fetch":
        fetch(int(a[a.index("--limit") + 1]) if "--limit" in a else None)
        build()
    elif stage == "build":
        build()
    elif stage == "report":
        report()
    else:
        print(__doc__)
