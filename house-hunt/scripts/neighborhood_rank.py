"""Rank neighborhoods on aggregate data from every apartment listing collected ("Version 7" in docs/CONCIERGE_DESIGN.md).

Reads only files on disk (no web requests) and writes, idempotently:
  data/neighborhood_rank.csv      one row per neighborhood considered, ranked ones first
  site/neighborhoods_data.json    the ranked neighborhoods with their buildings, for the page

Method in short (every number below is also in the JSON under meta):
  evidence     all rows of data/listings.csv with listing_kind == unit, studio or one bedroom, not a stated failure of type
  neighborhood the pipeline's hood_id: taken from data/units.csv where the address is there; otherwise the same geography
               (cached Census geocode, NYC neighborhood polygons, Jersey City polygons), then the ZIP's majority, then the listed city
  eligible     a neighborhood record on disk, drive under 2 hours, the owner's Jamaica rule, 5+ buildings listed at $2,000 or less
  score        eight measures, each 0 to 1 against the eligible list, weighted; a missing measure gets no credit and no penalty
  sensitivity  rank under each weight x1.5 and x0.5 and under equal weights; the lowest and highest rank are the stable range
No per-listing "confirmed today" multiplier is used anywhere. See docs/NEIGHBORHOOD_RANK_NOTES.md.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import math
import re
import statistics
import sys
import urllib.parse as up
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent.parent
DATA, SITE, RAW = ROOT / "data", ROOT / "site", ROOT / "raw"
OUT_CSV, OUT_JSON = DATA / "neighborhood_rank.csv", SITE / "neighborhoods_data.json"

RENT_SHOW, RENT_POOL = 2000, 2200           # shown limit; pool for medians and shares (the second trawl's ceiling)
MAX_DRIVE_MIN = 120
MIN_BUILDINGS = 5
MOVE_IN_BY = "2026-12-15"
VISITS_PER_MONTH = 2

WEIGHTS = {"near": 22, "cost": 18, "going_out": 16, "green": 14, "supply": 12, "space": 8, "parking": 6, "records": 4}
MEASURE_LABELS = {"near": "Near Mom and Dad", "cost": "Cost", "going_out": "Going out", "green": "Green and the dog",
                  "supply": "Supply she can use", "space": "Space", "parking": "Driving life", "records": "Records"}
# inside a measure: (key, share of the measure, True if higher is better, "log" to scale on log1p)
SUBS = {
    "near": [("drive_min", 0.7, False, ""), ("toll_round_trip", 0.3, False, "")],
    "cost": [("median_rent", 0.6, False, ""), ("apartments_2000", 0.4, True, "log")],
    "going_out": [("places_10min", 1.0, True, "log")],
    "green": [("park_walk_min", 0.4, False, ""), ("park_ha_800m", 0.3, True, "log"), ("dog_run_miles", 0.3, False, "log")],
    "supply": [("dogs_yes_share", 0.4, True, ""), ("dogs_or_pets_share", 0.2, True, ""), ("elevator_or_floor2_share", 0.4, True, "")],
    "space": [("median_sqft", 1.0, True, "")],
    "parking": [("offstreet_share", 0.6, True, ""), ("overnight_value", 0.4, True, "")],
    "records": [("records_index", 1.0, False, "")],
}
MIN_REVIEWS_SHOWN = 5                       # a rating from fewer reviews is not shown and earns no points
MIN_SQFT_N, MIN_PARKING_N = 5, 5            # fewer stated values than this: the figure is treated as missing
OVERNIGHT_VALUE = {"ban": 0.0, "permit": 0.5, "seasonal": 0.75}
WINSOR = (0.05, 0.95)

TAG_FLOORS = {"near family": "drive to Mom and Dad of 30 minutes or less",
              "lively": "20 or more restaurants, bars and cafés within a 10-minute walk",
              "quiet": "5 or fewer restaurants, bars and cafés within a 10-minute walk",
              "more room": "median stated size of 650 sq ft or more (at least 5 listings state a size)",
              "good value": "median listed rent of $1,700 or less",
              "green": "a park within a 5-minute walk",
              "easy parking": "off-street parking at more than half of the buildings that describe parking (at least 5 do)",
              "dog friendly": "at least half of the listings say dogs are allowed",
              "lots of choice": "40 or more apartments listed at $2,000 or less"}
TAG_MEASURE = {"near family": "near", "lively": "going_out", "quiet": "going_out", "more room": "space", "good value": "cost",
               "green": "green", "easy parking": "parking", "dog friendly": "supply", "lots of choice": "cost"}

BANNED = [r"\bunits?\b", r"\bgates?\b", r"\ball-in\b", r"\bcaps?\b", r"\bwe\b", r"\bnet-effective\b"]
RECORD_WORDS = [r"\bcrimes?\b", r"\bthefts?\b", r"\bviolen\w*", r"\brobber\w*", r"\bburglar\w*", r"\bassaults?\b", r"\bpolice\b",
                r"\bfelon\w*", r"\bshooting\w*", r"\bmurder\w*", r"\bsafety\b", r"\bunsafe\b", r"\bdangerous\b"]
PHONE_RE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")
PUBLIC_CONTACT_KINDS = {"leasing office", "management company"}

# Zumper "Pets | Dog | Policy | Not allowed | Cat | Policy | Not allowed" block (docs/AUDIT_2026-11-18.md item 6). The cached
# pages show it is a real statement: it is rendered when the page data holds an explicit empty pets list, pages where the
# lister said nothing hold no pets value and show no block, and most descriptions on these pages also say no pets. Rows stay
# "no dogs" except where the page contradicts itself (pets codes that include dogs, or a description that welcomes pets).
ZUMPER_BLOCK = "Pets | Dog | Policy | Not allowed | Cat | Policy | Not allowed"
ZUMPER_DESCRIPTION_CONFLICTS = {"zumper-65551400", "zumper-65499668", "zumper-59016052"}   # found reading the cached pages

SITE_NAMES = {"google": "Google", "apartments_com": "Apartments.com", "apartment_list": "Apartment List", "yelp": "Yelp",
              "apartmentratings": "ApartmentRatings", "zillow": "Zillow", "zumper": "Zumper", "facebook": "Facebook",
              "rent_com": "Rent.com", "openigloo": "Openigloo", "forrent": "ForRent", "rentcafe": "RentCafe", "birdeye": "Birdeye",
              "google_via_zumper": "Google", "own_site_widget": "Google", "own_site": "the building's own site"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


# ---------------------------------------------------------------- small helpers
def hood_id_of(state, hood):
    return re.sub(r"[^a-z0-9:]+", "-", f"{state}:{hood}".lower())


def text_ok(s):
    """True when a sentence carries none of the banned words and no records wording."""
    return not any(re.search(p, str(s), re.I) for p in BANNED + RECORD_WORDS)


def num(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def money(v):
    return f"${int(round(v)):,}"


def plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def haversine_km(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def read(path, **kw):
    return pd.read_csv(path, low_memory=False, **kw)


# ---------------------------------------------------------------- listings
def load_listings():
    L = read(DATA / "listings.csv")
    n_all = len(L)
    for c in ("sqft", "floor_used", "dog_weight_limit_lb", "listed_rent", "beds", "lat", "lon"):
        L[c] = pd.to_numeric(L[c], errors="coerce")
    U = L[(L.listing_kind == "unit")].copy()
    n_unit = len(U)
    U = U[(U.g_type != "fail") & U.beds.isin([0, 1]) & U.listed_rent.notna()].copy()
    t = U.dog_policy_text.fillna("")
    block = t.str.startswith(ZUMPER_BLOCK)
    conflict = block & (t.str.contains(r"pets codes \[[^\]]*[23]", regex=True) | U.listing_id.isin(ZUMPER_DESCRIPTION_CONFLICTS))
    U["dogs_adj"] = U.dogs.fillna("unknown")
    U.loc[conflict, "dogs_adj"] = "unknown"
    general = t.str.contains(r"allowed=true|pet[- ]friendly|petPolicy=allowed|pets allowed|pets welcome", case=False, regex=True)
    cats_only = t.str.contains(r"\bcats?\b", case=False, regex=True)
    negative = t.str.contains(r"allowed=false|not allowed|no pets", case=False, regex=True)
    U["pets_general"] = (U.dogs_adj == "unknown") & general & ~cats_only & ~negative
    U["elev_or_f2"] = (U.elevator == "yes") | (U.floor_used == 2)
    U["has_street"] = U.addr_key.astype(str).str.match(r"\s*\d")      # no house number: not a building anyone can be sent to
    U["stated_fail"] = (U.dogs_adj == "no") | (U.g_floor_elevator == "fail") | (U.g_movein == "fail")
    U["park_kind"] = U.parking_type.map(parking_kind)
    zstats = {"rows_with_block": int(block.sum()), "kept_as_no_dogs": int((block & ~conflict).sum()),
              "set_to_unknown_for_conflict": int(conflict.sum())}
    return U, {"listings_read": n_all, "apartment_listings": n_unit, "listings_used": len(U)}, zstats


def parking_kind(v):
    s = str(v).lower() if isinstance(v, str) else ""
    if not s:
        return ""
    if re.search(r"garage|parking lot|surface_lot|off[- ]street|assigned|covered|carport|driveway|dedicated|parking space|reserved|on site|open lot", s):
        return "garage" if "garage" in s else "offstreet"
    if "street" in s:
        return "street"
    if re.fullmatch(r"\s*none\s*", s):
        return "none"
    return ""


# ---------------------------------------------------------------- "pay months up front" template prices
TEMPLATE_ASK = "What is the real monthly rent? The price shown assumes extra months paid up front."


def apply_templates(U):
    """Independent check 6, sweep 10: one lister's listings advertise a reduced payment for months paid up front while the
    page states the real "Monthly Rent". Sets U.template ('' / confirmed / same_building / same_price) and replaces
    listed_rent by the real stated rent (NaN where it is not known, which takes the row out of every measure);
    the advertised figure stays in advertised_rent. Returns counts for meta."""
    U["advertised_rent"], U["template"], real = U.listed_rent, "", {}
    V = read(DATA / "evidence" / "review_verdicts.csv")
    v = V[(V.why.fillna("") + " " + V.what_to_confirm.fillna("")).str.contains("up front", case=False)]
    for r in v.itertuples():
        m = re.search(r"The rent is \$([\d,]+) a month", str(r.why))
        real.setdefault(r.listing_id, None)
        if m:
            real[r.listing_id] = float(m.group(1).replace(",", ""))
    F = read(DATA / "reference" / "listing_page_facts.csv")
    t = F.description.fillna("") + " " + F.extra_text.fillna("")
    for lid, txt in zip(F.listing_id, t):
        m = re.search(r"Monthly Rent:\s*\$\s*([\d,]+)", txt)
        if m and re.search(r"reduced monthly rent|up ?front", txt, re.I):
            real[lid] = real.get(lid) or float(m.group(1).replace(",", ""))
    B = read(DATA / "evidence" / "live_check_batch_22.csv")
    b = B[(B.status == "changed") & B.notes.fillna("").str.contains("up front", case=False) & B.price_now.notna()]
    by_unit = {(r.addr_key, str(r.unit).split(".")[0]): float(r.price_now) for r in b.itertuples()}
    for r in U[U.addr_key.isin(set(b.addr_key))].itertuples():
        k = (r.addr_key, str(r.unit).split(".")[0])
        if k in by_unit:
            real[r.listing_id] = real.get(r.listing_id) or by_unit[k]
    conf = U.listing_id.isin(real)
    U.loc[conf, "template"] = "confirmed"
    prices = set(U.loc[conf, "advertised_rent"])
    keys = set(U.loc[conf, "addr_key"])
    hoods = set(U.loc[conf, "hood_id"].dropna())
    same_b = ~conf & U.addr_key.isin(keys) & U.advertised_rent.isin(prices)
    U.loc[same_b, "template"] = "same_building"
    # the same odd figure (not ending in 0 or 5) elsewhere in a neighborhood where the template is confirmed, plus any
    # odd figure there that is 8/11, 9/11 or 10/11 of a round rent (the template's "months up front" steps)
    odd = {p for p in prices if p % 5}
    rep_ = U[U.hood_id.isin(hoods)].groupby("advertised_rent").addr_key.nunique()
    for p_, n in rep_.items():
        if p_ % 5 and any(abs(p_ * 11 / k - round(p_ * 11 / k / 50) * 50) < 1.5 for k in (8, 9, 10)):
            odd.add(p_)
    same_p = (U.template == "") & U.hood_id.isin(hoods) & U.advertised_rent.isin(odd)
    U.loc[same_p, "template"] = "same_price"
    U["listed_rent"] = [real.get(i) if tpl == "confirmed" else (float("nan") if tpl else r)
                        for i, tpl, r in zip(U.listing_id, U.template, U.advertised_rent)]
    U["listed_rent"] = pd.to_numeric(U.listed_rent, errors="coerce")
    T = U[U.template != ""]
    scan = U[U.hood_id.notna() & (U.advertised_rent <= RENT_POOL) & (U.advertised_rent % 5 != 0)]
    g = scan.groupby(["hood_id", "advertised_rent"]).agg(n=("listing_id", "size"), addresses=("addr_key", "nunique")).reset_index()
    g = g[(g.n >= 6) & (g.addresses >= 4)].sort_values(["n", "hood_id"], ascending=[False, True])
    return {"listings_flagged": int(len(T)), "by_basis": {k: int(v) for k, v in T.template.value_counts().sort_index().items()},
            "real_rent_known": int(T.listed_rent.notna().sum()), "real_rent_unknown_left_out": int(T.listed_rent.isna().sum()),
            "real_rent_at_2000_or_less": int((T.listed_rent <= RENT_SHOW).sum()),
            "by_neighborhood": {k: int(v) for k, v in T.hood_id.value_counts().items()},
            "advertised_prices": sorted(int(x) for x in set(T.advertised_rent)),
            "odd_price_scan": [{"neighborhood": r.hood_id, "advertised_rent": int(r.advertised_rent), "listings": int(r.n), "addresses": int(r.addresses)}
                               for r in g.itertuples()],
            "scan_rule": "a price not ending in 0 or 5 shared by 6+ listings at 4+ addresses in one neighborhood"}


# ---------------------------------------------------------------- neighborhood assignment
def assign_hoods(U, hood_table):
    """addr_key -> (hood_id, method). Same geography as scripts/build_neighborhoods.py, read from caches only."""
    ids = set(hood_table.hood_id)
    centre = {r.hood_id: (r.lat, r.lon) for r in hood_table.itertuples()}
    known = read(DATA / "units.csv", usecols=["addr_key", "hood_id"]).drop_duplicates("addr_key").set_index("addr_key").hood_id.to_dict()
    cached = {}
    for f in sorted(glob.glob(str(RAW / "census_geocoder" / "*.meta.json"))):
        m = json.loads(Path(f).read_text())
        if "geographies/coordinates" in m.get("url", "") and m.get("status") == 200:
            q = up.parse_qs(up.urlparse(m["url"]).query)
            cached[(q["x"][0], q["y"][0])] = ROOT / m["path"]
    nta_file = None
    for f in sorted(glob.glob(str(RAW / "nyc_open_data" / "*.meta.json"))):
        m = json.loads(Path(f).read_text())
        if "9nt8-h7nd.geojson" in m.get("url", ""):
            nta_file = ROOT / m["path"]
    nta = json.loads(nta_file.read_text())["features"]
    npoly, nname = [shape(f["geometry"]) for f in nta], [f["properties"]["ntaname"] for f in nta]
    tree = STRtree(npoly)
    sub = json.loads((DATA / "reference" / "subcity_neighborhoods.geojson").read_text())["features"]
    jc = [(ft["properties"]["hood_label"], shape(ft["geometry"])) for ft in sub if ft["properties"]["city"] == "Jersey City"]

    def first(g, k):
        v = g.get(k) or []
        return v[0].get("NAME") if v else ""

    A = U.dropna(subset=["lat", "lon"]).drop_duplicates("addr_key")
    out, later = {}, []
    for r in A.itertuples():
        k = r.addr_key
        if k in known:
            out[k] = (known[k], "pipeline")
            continue
        p = Point(r.lon, r.lat)
        name = None
        c = cached.get((f"{r.lon:.6f}", f"{r.lat:.6f}"))
        if c is not None and c.exists():
            try:
                g = json.loads(c.read_text())["result"]["geographies"]
                if first(g, "Incorporated Places") == "New York city":
                    name = "NYC"
                else:
                    name = first(g, "Incorporated Places") or first(g, "County Subdivisions") or None
                    for suf in (" city", " village", " town", " borough", " township", " CDP"):
                        if name and name.endswith(suf):
                            name = name[:-len(suf)]
            except (ValueError, KeyError):
                name = None
        if name in (None, "NYC"):
            hit = [i for i in tree.query(p) if npoly[i].contains(p)]
            if hit:
                out[k] = (hood_id_of("NY", nname[hit[0]]), "nyc_polygon")
                continue
            if name == "NYC":
                out[k] = (None, "unassigned")
                continue
        if name == "Jersey City" or (name is None and r.state == "NJ" and str(r.city).strip().lower() == "jersey city"):
            hit = [lab for lab, poly in jc if poly.contains(p)]
            near = min((poly.distance(p), lab) for lab, poly in jc)
            if hit or near[0] < 0.01:
                out[k] = (hood_id_of("NJ", hit[0] if hit else near[1]), "jersey_city_polygon")
                continue
        if name is not None:
            out[k] = (hood_id_of(r.state, name), "census_cache")
            continue
        later.append(r)
    by_zip = defaultdict(Counter)
    zip_of = A.set_index("addr_key").zip5.to_dict()
    for k, (h, m) in out.items():
        if m in ("pipeline", "census_cache") and h:
            by_zip[str(zip_of.get(k))][h] += 1
    for r in later:
        listed = hood_id_of(r.state, str(r.city).strip())
        z = by_zip.get(str(r.zip5), Counter())
        top = z.most_common(1)
        if listed in z or not top:
            h, m = listed, "listed_city"
        elif sum(z.values()) >= 3 and top[0][1] / sum(z.values()) >= 0.8:
            h, m = top[0][0], "zip_majority"
        else:
            h, m = listed, "listed_city"
        if h in centre and haversine_km(r.lat, r.lon, *centre[h]) > 15:
            h, m = None, "unassigned"          # the listed city and the coordinates disagree
        out[r.addr_key] = (h, m)
    return out


# ---------------------------------------------------------------- neighborhood measures
def hood_measures(U, hood_table, groups, overnight):
    """Raw figures per neighborhood, from the listings and the neighborhood record."""
    P22, P20 = U[U.listed_rent <= RENT_POOL], U[U.listed_rent <= RENT_SHOW]
    M = {}
    G = groups.set_index("hood_id")
    for r in hood_table.itertuples():
        h = r.hood_id
        a, b = P22[P22.hood_id == h], P20[P20.hood_id == h]
        m = {"listings": int(len(a)), "apartments_2000": int(b.dedupe_key.nunique()), "buildings_2000": int(b[b.has_street].bkey.nunique()),
             "apartments_no_street_address": int((~b.has_street).sum()),
             "drive_min": round(float(r.drive_min), 1), "toll_round_trip": round(float(r.toll_rt), 2),
             "record_buildings": int(r.buildings)}
        m["median_rent"] = float(a.listed_rent.median()) if len(a) else None
        m["typical_rent_shown"] = float(b.listed_rent.median()) if len(b) else None
        m["rent_low"] = float(b.listed_rent.min()) if len(b) else None
        m["dogs_yes"] = int((a.dogs_adj == "yes").sum())
        m["pets_general"] = int(a.pets_general.sum())
        m["dogs_no"] = int((a.dogs_adj == "no").sum())
        m["elevator_or_floor2"] = int(a.elev_or_f2.sum())
        n = len(a)
        m["dogs_yes_share"] = round(m["dogs_yes"] / n, 4) if n else None
        m["dogs_or_pets_share"] = round((m["dogs_yes"] + m["pets_general"]) / n, 4) if n else None
        m["elevator_or_floor2_share"] = round(m["elevator_or_floor2"] / n, 4) if n else None
        m["restaurants"], m["bars"], m["cafes"] = (num(r.restaurants_800m), num(r.bars_800m), num(r.cafes_800m))
        m["places_10min"] = None if m["restaurants"] is None else round(m["restaurants"] + (m["bars"] or 0) + (m["cafes"] or 0), 1)
        m["park_walk_min"] = None if num(r.park_walk_min) is None else round(num(r.park_walk_min), 1)
        m["park_ha_800m"] = None if num(r.park_ha_800m) is None else round(num(r.park_ha_800m), 2)
        d = num(G.dog_park_m.get(h)) if h in G.index else None
        m["dog_run_miles"] = None if d is None else round(d / 1609.344, 1)
        s = a.sqft.dropna()
        s = s[(s >= 150) & (s <= 2500)]
        m["sqft_stated"] = int(len(s))
        m["median_sqft"] = float(round(s.median())) if len(s) >= MIN_SQFT_N else None
        pk = a[a.park_kind != ""].groupby("bkey").park_kind.agg(lambda x: "off" if set(x) & {"garage", "offstreet"} else "other")
        m["parking_stated_buildings"] = int(len(pk))
        m["parking_offstreet_buildings"] = int((pk == "off").sum())
        m["offstreet_share"] = round(m["parking_offstreet_buildings"] / len(pk), 4) if len(pk) >= MIN_PARKING_N else None
        o = overnight.get(h)
        m["overnight_rule"] = o["severity"] if o else None
        m["overnight_value"] = OVERNIGHT_VALUE.get(o["severity"]) if o else None
        m["records_index"] = None if num(r.rec_index) is None else round(float(r.rec_index), 4)
        M[h] = m
    return M


def scale(values, higher_better, how):
    """{id: value or None} -> {id: 0..1 or None}: winsorised min-max over the ids that have a value."""
    known = {k: (math.log1p(v) if how == "log" else v) for k, v in values.items() if v is not None}
    if not known:
        return {k: None for k in values}
    xs = sorted(known.values())
    q = lambda p: xs[min(len(xs) - 1, max(0, int(round(p * (len(xs) - 1)))))]  # noqa: E731
    lo, hi = q(WINSOR[0]), q(WINSOR[1])
    out = {}
    for k in values:
        if k not in known:
            out[k] = None
        elif hi == lo:
            out[k] = 0.5
        else:
            s = min(1.0, max(0.0, (known[k] - lo) / (hi - lo)))
            out[k] = round(s if higher_better else 1 - s, 6)
    return out


def measure_scores(M, eligible):
    """{hood: {measure: 0..1 or None}} over the eligible neighborhoods."""
    S = {h: {} for h in eligible}
    for meas, subs in SUBS.items():
        parts = {key: scale({h: M[h].get(key) for h in eligible}, hb, how) for key, _, hb, how in subs}
        for h in eligible:
            got = [(parts[key][h], w) for key, w, _, _ in subs if parts[key][h] is not None]
            S[h][meas] = round(sum(v * w for v, w in got) / sum(w for _, w in got), 6) if got else None
    return S


def total_score(s, weights):
    got = [(s[m], w) for m, w in weights.items() if s.get(m) is not None]
    return round(100 * sum(v * w for v, w in got) / sum(w for _, w in got), 6) if got else 0.0


def rank_ids(S, weights):
    sc = {h: total_score(S[h], weights) for h in S}
    order = sorted(S, key=lambda h: (-sc[h], h))
    return {h: i + 1 for i, h in enumerate(order)}, sc


def scenarios():
    out = {"base": dict(WEIGHTS), "equal": {m: 1 for m in WEIGHTS}}
    for m in WEIGHTS:
        for tag, f in (("up", 1.5), ("down", 0.5)):
            w = dict(WEIGHTS)
            w[m] = WEIGHTS[m] * f
            out[f"{m}_{tag}"] = w
    return out


# ---------------------------------------------------------------- sentences
def display_figures(meas, m):
    """The figures a sentence about `meas` may quote, each computed from the measures block."""
    if meas == "near":
        return {"drive_min": int(round(m["drive_min"])), "hours_per_month": round(m["drive_min"] * 2 * VISITS_PER_MONTH / 60, 1),
                "toll_per_month": int(round(m["toll_round_trip"] * VISITS_PER_MONTH))}
    if meas == "cost":
        return {"median_rent": int(round(m["median_rent"])), "apartments_2000": m["apartments_2000"]}
    if meas == "supply":
        return {"listings": m["listings"], "dogs_yes": m["dogs_yes"], "pets_general": m["pets_general"],
                "elevator_or_floor2": m["elevator_or_floor2"]}
    if meas == "going_out":
        return {"places_10min": int(round(m["places_10min"]))}
    if meas == "green":
        f = {"park_walk_min": int(round(m["park_walk_min"]))}
        if m.get("dog_run_miles") is not None:
            f["dog_run_miles"] = m["dog_run_miles"]
        return f
    if meas == "space":
        return {"median_sqft": int(m["median_sqft"]), "sqft_stated": m["sqft_stated"]}
    if meas == "parking":
        f = {}
        if m.get("offstreet_share") is not None:
            f = {"parking_offstreet_buildings": m["parking_offstreet_buildings"], "parking_stated_buildings": m["parking_stated_buildings"]}
        return f
    return {}


def figure_text(key, v):
    if key in ("median_rent", "toll_per_month"):
        return money(v)
    if key == "median_sqft":
        return f"{v:,}"
    return str(v)


def sentence(meas, m):
    f = display_figures(meas, m)
    t = {k: figure_text(k, v) for k, v in f.items()}
    if meas == "near":
        toll = f"{t['toll_per_month']} in tolls" if f["toll_per_month"] else "no tolls ($0)"
        if f["toll_per_month"] == 0:
            f = dict(f)
            t["toll_per_month"] = "$0"
        s = (f"Mom and Dad are about {t['drive_min']} minutes away by car; two visits a month comes to about "
             f"{t['hours_per_month']} hours of driving and {toll}.")
    elif meas == "cost":
        s = (f"Half of the studios and one-bedrooms listed here ask {t['median_rent']} or less in rent, and "
             f"{t['apartments_2000']} {'is' if f['apartments_2000'] == 1 else 'are'} listed at $2,000 or less.")
    elif meas == "supply":
        s = (f"Of {t['listings']} listings here, {t['dogs_yes']} say dogs are allowed, {t['pets_general']} more {'says' if f['pets_general'] == 1 else 'say'} pets are allowed "
             f"without naming dogs, and {t['elevator_or_floor2']} state an elevator or a second-floor apartment.")
    elif meas == "going_out":
        s = (f"About {t['places_10min']} restaurants, bars and cafés are within a 10-minute walk of a typical building here."
             if f["places_10min"] else "There are 0 restaurants, bars or cafés within a 10-minute walk of a typical building here.")
    elif meas == "green":
        s = f"A park is about {t['park_walk_min']} minute{'' if f['park_walk_min'] == 1 else 's'} away on foot"
        s += f", and the nearest dog run is {t['dog_run_miles']} mile{'' if f['dog_run_miles'] == 1 else 's'} away." if "dog_run_miles" in f else "."
    elif meas == "space":
        s = f"Apartments that state a size run about {t['median_sqft']} square feet (the middle of {t['sqft_stated']} listings)."
    elif meas == "parking":
        bits = []
        if f:
            bits.append(f"{t['parking_offstreet_buildings']} of the {t['parking_stated_buildings']} buildings that describe parking "
                        f"have a garage, a lot or another space off the street")
        rule = {"ban": "overnight street parking is banned here", "permit": "overnight street parking needs a permit here",
                "seasonal": "overnight street parking is restricted for part of the year here"}.get(m.get("overnight_rule"))
        if rule:
            bits.append(rule)
        s = "; ".join(bits)
        s = s[0].upper() + s[1:] + "." if s else ""
    else:
        s = ""
    return s, f


ICONS = {"near": "car", "cost": "tag", "going_out": "fork", "green": "park", "supply": "key", "space": "ruler", "parking": "parking"}


DRAWBACK = {"near": ("drive_min", False), "going_out": ("places_10min", True), "space": ("median_sqft", True),
            "supply": ("dogs_yes_share", True), "green": ("park_walk_min", False)}


def drawback(meas, m, med):
    """(sentence, figures) when the neighborhood's own figure is worse than the middle of the ranked list, else None."""
    def worse(key, higher_better):
        v, c = m.get(key), med.get(key)
        return v is not None and c is not None and (v < c if higher_better else v > c)
    f = display_figures(meas, m) if meas != "parking" else {}
    t = {k: figure_text(k, v) for k, v in f.items()}
    if meas == "near" and worse("drive_min", False):
        return sentence("near", m)[0].replace("Mom and Dad are about", "It is far from Mom and Dad: about", 1).replace(" minutes away by car;", " minutes by car;", 1), f
    if meas == "going_out" and worse("places_10min", True):
        return (f"There are few places to eat and drink nearby: about {t['places_10min']} restaurants, bars and cafés within a 10-minute walk."), f
    if meas == "space" and worse("median_sqft", True):
        return f"Apartments run small here: about {t['median_sqft']} square feet where a size is stated (the middle of {t['sqft_stated']} listings).", f
    if meas == "supply" and worse("dogs_yes_share", True):
        f = {k: f[k] for k in ("listings", "dogs_yes")}
        return f"Few listings here say they take dogs: {t['dogs_yes']} of {t['listings']}.", f
    if meas == "green" and worse("park_walk_min", False):
        f = {"park_walk_min": f["park_walk_min"]}
        return f"The nearest park is a long walk: about {t['park_walk_min']} minutes on foot.", f
    if meas == "cost":
        pricey, thin = worse("median_rent", False), worse("apartments_2000", True)
        if pricey and (not thin or m["median_rent"] / med["median_rent"] - 1 >= 1 - m["apartments_2000"] / med["apartments_2000"]):
            return f"It is pricey for this list: half of the studios and one-bedrooms listed here ask {t['median_rent']} or more in rent.", {"median_rent": f["median_rent"]}
        if thin:
            n = f["apartments_2000"]
            return f"There is little to choose from: {t['apartments_2000']} {'apartment is' if n == 1 else 'apartments are'} listed at $2,000 or less.", {"apartments_2000": n}
    if meas == "parking" and (m.get("overnight_rule") or (m.get("offstreet_share") is not None and m["offstreet_share"] < 0.5)):
        return sentence("parking", m)
    return None


def why_and_know(h, S, M, eligible, med):
    """Three best measures and one or two worst, by the neighborhood's standing on each among the eligible list."""
    pct = {}
    for meas in WEIGHTS:
        if meas == "records" or S[h].get(meas) is None:
            continue
        others = [S[o][meas] for o in eligible if S[o].get(meas) is not None]
        pct[meas] = sum(1 for v in others if v < S[h][meas]) / max(1, len(others) - 1) if len(others) > 1 else 0.5
    order = sorted(pct, key=lambda k: (-pct[k], -WEIGHTS[k], k))
    made = {}
    for meas in order:
        s, f = sentence(meas, M[h])
        if s and text_ok(s):
            made[meas] = {"measure": meas, "icon": ICONS[meas], "text": s, "figures": f, "standing": round(pct[meas], 3)}
    usable = [k for k in order if k in made]
    why = [made[k] for k in usable[:3]]
    know = []
    for k in reversed(order):                    # worst standing first; only real drawbacks, and none when nothing is clearly low
        if k in usable[:3] or pct[k] >= 0.4 or len(know) == 2:
            continue
        d = drawback(k, M[h], med)
        if d and d[0] and text_ok(d[0]):
            know.append({"measure": k, "icon": ICONS[k], "text": d[0], "figures": d[1], "standing": round(pct[k], 3)})
    return why, know, pct


def tags_for(m, pct):
    holds = {"near family": m["drive_min"] <= 30,
             "lively": m["places_10min"] is not None and m["places_10min"] >= 20,
             "quiet": m["places_10min"] is not None and m["places_10min"] <= 5,
             "more room": m["median_sqft"] is not None and m["median_sqft"] >= 650,
             "good value": m["median_rent"] is not None and m["median_rent"] <= 1700,
             "green": m["park_walk_min"] is not None and m["park_walk_min"] <= 5,
             "easy parking": m["offstreet_share"] is not None and m["offstreet_share"] > 0.5,
             "dog friendly": m["dogs_yes_share"] is not None and m["dogs_yes_share"] >= 0.5,
             "lots of choice": m["apartments_2000"] >= 40}
    true = [t for t, ok in holds.items() if ok]
    true.sort(key=lambda t: (-(1 - pct.get("going_out", 0.5) if t == "quiet" else pct.get(TAG_MEASURE[t], 0.5)), t))
    out, seen = [], set()
    for t in true:                               # two tags about two different things
        if TAG_MEASURE[t] not in seen:
            out.append(t)
            seen.add(TAG_MEASURE[t])
    return out[:2], true


# ---------------------------------------------------------------- buildings
def building_sources():
    X = read(DATA / "reference" / "building_crosswalk.csv")
    cross = X.set_index("addr_key").building_id.to_dict()
    MB = read(DATA / "master_buildings.csv", usecols=["building_id", "addr_keys"])
    for r in MB.itertuples():
        for k in str(r.addr_keys).split(";"):
            if k.strip() and k.strip() != "nan":
                cross.setdefault(k.strip(), r.building_id)
    conc = json.loads((SITE / "concierge_data.json").read_text())
    verified = {b["id"]: b for b in conc["buildings"]}
    page = json.loads((SITE / "data.json").read_text())
    page_units = defaultdict(list)
    for u in page["units"]:
        page_units[u["building_id"]].append(u["id"])
    AV = read(DATA / "avoid_buildings.csv")
    avoid = {r.addr_key: r for r in AV[AV.avoid == "yes"].itertuples()}
    RS = read(DATA / "evidence" / "rating_standard.csv")
    rstd = {r.addr_key: r for r in RS.itertuples()}
    RC = pd.concat([read(f) for f in sorted(glob.glob(str(DATA / "evidence" / "ratings_census*.csv"))) if "summary" not in f])
    RC = RC[(RC.status == "found") & RC.rating.notna() & RC.review_count.notna() & (RC.match_confidence != "low")]
    RC = RC[pd.to_numeric(RC.rating_scale, errors="coerce").fillna(5) == 5].drop_duplicates(["building_id", "platform"])
    census = {}
    for r in RC.sort_values(["review_count", "platform"], ascending=[False, True]).itertuples():
        census.setdefault(r.building_id, r)
    NF = read(DATA / "evidence" / "nyc_records_flags.csv")
    rec_held = set(NF.addr_key) | set(read(DATA / "evidence" / "non_nyc_records.csv", usecols=["addr_key"]).addr_key)
    contacts = {}
    for f in ("building_contacts.csv", "building_contacts_trawl2.csv"):
        for r in read(DATA / "reference" / f).itertuples():
            contacts[r.building_id] = r
    own = {r.building_id: r for r in read(DATA / "reference" / "building_contacts_own_site.csv").itertuples()}
    RV = read(DATA / "evidence" / "review_verdicts.csv")
    unverified = set(RV[(RV.kind == "unverified") & (RV.verdict == "remove")].listing_id)
    return dict(cross=cross, verified=verified, page_units=page_units, avoid=avoid, rstd=rstd, census=census, rec_held=rec_held,
                contacts=contacts, own=own, unverified=unverified)


def plain_place(s):
    """A building name or address as shown: an apartment number written as "Unit 4" reads "Apt 4"."""
    return re.sub(r"\bunits?\b\.?", "Apt", str(s), flags=re.I).strip()


def bkey_of(addr_key, cross):
    return cross.get(addr_key) or "a_" + hashlib.sha1(str(addr_key).encode()).hexdigest()[:10]


def date_words(iso):
    y, mo, d = (int(x) for x in iso[:10].split("-"))
    return f"{MONTHS[mo - 1]} {d}"


AVOID_TAGS = {"elevator_outage": "elevator outages", "mold": "mold", "unresponsive_management": "slow management", "pests": "pests",
              "heat": "no heat", "noise": "noise", "leaks": "leaks"}
RECORD_TOPICS = {"class_c_violations": "serious violations", "heat_hot_water_complaints": "heat and hot water complaints",
                 "mold_complaints": "mold complaints", "pest_complaints": "pest complaints"}


def avoid_reason_from_list(reasons):
    """One plain sentence from data/avoid_buildings.csv `reasons`, or None when nothing can be said in plain words."""
    out = []
    for part in [p.strip() for p in str(reasons).split(";") if p.strip()]:
        m = re.match(r"elevator: (\d+)\+ complaints to the city in (\d+) months", part)
        if m:
            out.append(f"City records show {m.group(1)} or more elevator complaints here in {m.group(2)} months, more than at 9 in 10 similar buildings.")
            continue
        m = re.match(r"elevator: (\d+) tenant reports of outages in (\d+) months", part)
        if m:
            out.append(f"{m.group(1)} tenants reported elevator outages here in the last {m.group(2)} months.")
            continue
        m = re.match(r"management: city records in the last (\d+) months above the 90th percentile on (.+)", part)
        if m:
            topics = [RECORD_TOPICS.get(t.strip(), t.strip().replace("_", " ")) for t in m.group(2).split(",")]
            out.append(f"City records for the last {m.group(1)} months show more {', '.join(topics)} here than at 9 in 10 similar buildings.")
            continue
        m = re.match(r"management: (\d+) (?:separate dated )?tenant reports of (?:serious )?problems in the last (\d+) months", part)
        if m:
            out.append(f"{m.group(1)} tenants reported serious problems with the management here in the last {m.group(2)} months.")
            continue
        m = re.match(r"reviews: (\d+) negative reviews in the last (\d+) months \(([^)]*)\)", part)
        if m:
            tg = [AVOID_TAGS[t] for t in m.group(3).split(";") if t in AVOID_TAGS]
            out.append(f"{m.group(1)} reviews in the last {m.group(2)} months report serious problems" + (f" ({', '.join(tg)})." if tg else "."))
    out = [s for s in out if text_ok(s)]
    return out[0] if out else None


def build_buildings(U, src, hood_median):
    """{hood_id: [building dict]} for every building with a studio or one-bedroom listed at $2,000 or less."""
    tpl_unknown = U[(U.template != "") & U.listed_rent.isna() & (U.advertised_rent <= RENT_SHOW) & U.hood_id.notna() & U.has_street]
    P = pd.concat([U[(U.listed_rent <= RENT_SHOW) & U.hood_id.notna() & U.has_street], tpl_unknown])
    allrows = {k: g for k, g in U.groupby("bkey")}
    out = defaultdict(list)
    for (h, bk), g in P.groupby(["hood_id", "bkey"]):
        g = g.sort_values(["listed_rent", "listing_id"]).drop_duplicates("dedupe_key")
        every = allrows[bk]
        real_rows = g[g.listed_rent.notna()]
        template_only = not len(real_rows)          # every price here is a template figure with no real rent on record
        has_template = bool((every.template != "").any())
        if template_only:
            g = g.assign(listed_rent=g.advertised_rent)
        else:
            g = real_rows
        use = g[~g.stated_fail]
        shown = use if len(use) else g
        names = [n for n in every.building_name.dropna().astype(str)          # an owner's company name is not a building name
                 if n.strip() and not re.search(r"\b(llc|inc|corp|l\.l\.c|realty|management|properties|associates)\b", n, re.I)]
        addr = Counter(every.address.dropna().astype(str)).most_common(1)
        address = addr[0][0] if addr and re.match(r"\s*\d", addr[0][0]) else str(g.addr_key.iloc[0]).split("|")[0].title()
        name = Counter(names).most_common(1)[0][0] if names else address
        name, address = plain_place(name), plain_place(address)
        first = shown.iloc[0]
        b = {"id": bk, "name": name, "address": address, "city": str(first.city), "state": str(first.state),
             "zip": str(first.zip5).split(".")[0], "rent_range": [int(shown.listed_rent.min()), int(shown.listed_rent.max())],
             "apartments": int(len(shown)), "apartments_listed": int(len(g)), "usable": bool(len(use))}
        b["rent_text"] = (f"Rent {money(b['rent_range'][0])}" if b["rent_range"][0] == b["rent_range"][1]
                          else f"Rent {money(b['rent_range'][0])} to {money(b['rent_range'][1])}")
        known, ask = [], []
        # dogs
        dy, dn, pg = (every.dogs_adj == "yes").any(), bool(len(g)) and (g.dogs_adj == "no").all(), every.pets_general.any()
        lim = every.loc[every.dogs_adj == "yes", "dog_weight_limit_lb"].dropna()
        if dy and not (shown.dogs_adj == "no").all():
            known.append(f"Dogs allowed up to {int(lim.min())} lb" if len(lim) and lim.min() > 0 else "Dogs allowed")
            b["dogs"] = "yes"
            if not len(lim):
                ask.append("Is there a weight limit for dogs?")
        elif dn:
            known.append("No dogs")
            b["dogs"] = "no"
        elif pg:
            known.append("Pets allowed")
            ask.append("Are dogs allowed, and up to what weight?")
            b["dogs"] = "pets"
        else:
            ask.append("Are dogs allowed?")
            b["dogs"] = "unknown"
        # elevator and floor
        elev = (every.elevator == "yes").any()
        floors = shown.floor_used.dropna()
        ground_only = bool(len(g)) and (g.floor_elevator_code == "ground_floor").all()
        if elev:
            known.append("Elevator")
            if not len(floors):
                ask.append("Which floor is it on? (never the ground floor)")
        elif len(floors) and (floors == 2).any():
            known.append("Second floor")
        elif ground_only:
            known.append("Ground floor only")
        else:
            ask.append("Which floor is it on, and is there an elevator?")
        b["elevator_or_floor2"] = bool(elev or (len(floors) and (floors == 2).any()))
        # parking
        kinds = set(every.park_kind) - {""}
        if "garage" in kinds:
            known.append("Garage parking")
        elif "offstreet" in kinds:
            known.append("Off-street parking")
        elif "street" in kinds:
            known.append("Street parking only")
        elif "none" in kinds:
            known.append("No parking on site")
        if not kinds & {"street", "none"}:
            ask.append("What does parking cost each month?" if kinds else "Is there parking, and what does it cost?")
        # move-in
        dates = shown.available_date.dropna().astype(str)
        ok = [d for d in dates if d == "now" or d[:10] <= MOVE_IN_BY]
        late = sorted(d for d in dates if d != "now" and d[:10] > MOVE_IN_BY)
        if "now" in ok:
            known.append("Available now")
        elif ok:
            known.append(f"Available {date_words(sorted(ok)[0])}")
        elif late:
            known.append(f"Available from {date_words(late[0])}")
        else:
            ask.append("When is it available?")
        # size
        sq = shown.sqft.dropna()
        sq = sq[(sq >= 150) & (sq <= 2500)]
        if len(sq):
            lo, hi = int(sq.min()), int(sq.max())
            known.append(f"{lo:,} sq ft" if lo == hi else f"{lo:,} to {hi:,} sq ft")
        else:
            ask.append("How big is it?")
        if template_only:
            ask.insert(0, TEMPLATE_ASK)
            b["rent_text"] = f"Advertised at {money(b['rent_range'][0])} with months paid up front; the real rent is not stated"
        elif has_template:
            ask.insert(0, "Does this apartment exist, and what is its number?")
        b["rent_is_template"], b["has_template_listing"] = template_only, has_template
        b["known"], b["to_ask"] = known, ask
        # rating
        keys = list(dict.fromkeys(every.addr_key))
        rt = None
        c = src["census"].get(bk)
        if c is not None:
            rt = {"value": round(float(c.rating), 1), "count": int(c.review_count), "site": SITE_NAMES.get(c.platform, str(c.platform).replace("_", " ")),
                  "source_url": c.source_url if isinstance(c.source_url, str) else None}
        for k in keys:
            r = src["rstd"].get(k)
            if rt is None and r is not None and num(r.rating) is not None and num(r.review_count):
                rt = {"value": round(float(r.rating), 1), "count": int(r.review_count), "site": SITE_NAMES.get(r.best_source, str(r.best_source).replace("_", " ")),
                      "source_url": r.source_url if isinstance(r.source_url, str) else None}
        b["rating_held"] = rt
        rt = rt if rt and rt["count"] >= MIN_REVIEWS_SHOWN else None
        b["rating"] = rt
        # contact (public offices only)
        ct, o = src["contacts"].get(bk), src["own"].get(bk)
        contact = None
        if o is not None and isinstance(o.leasing_phone, str) and (ct is None or ct.contact_kind in PUBLIC_CONTACT_KINDS):
            contact = {"phone": o.leasing_phone, "site": o.own_site_url if isinstance(o.own_site_url, str) else None,
                       "hours": o.office_hours if isinstance(o.office_hours, str) else None, "kind": "leasing office", "own_site": True}
        elif ct is not None and ct.contact_kind in PUBLIC_CONTACT_KINDS:
            contact = {"phone": ct.leasing_phone if isinstance(ct.leasing_phone, str) else None,
                       "site": ct.leasing_url if isinstance(ct.leasing_url, str) else None,
                       "hours": ct.office_hours if isinstance(ct.office_hours, str) else None, "kind": ct.contact_kind, "own_site": False}
        b["contact"] = contact
        b["listing_url"] = first.url if isinstance(first.url, str) else None
        b["photo_url"] = first.photo_url if isinstance(first.photo_url, str) else None
        # verified on the page
        v = src["verified"].get(bk)
        vids = [a["id"] for a in v["apartments"] if a.get("rent") is not None and a["rent"] <= RENT_SHOW] if v else []
        b["verified"] = {"on_page": bool(vids), "apartment_ids": vids,
                         "first_page_ids": sorted(src["page_units"].get(bk, []))}
        if vids and v["facts"].get("total_from") is not None:
            b["verified"]["total_with_utilities_and_fees"] = [v["facts"]["total_from"], v["facts"]["total_to"]]
            b["verified"]["total_text"] = (f"Total with utilities and fees {money(v['facts']['total_from'])}"
                                           + ("" if v["facts"]["total_from"] == v["facts"]["total_to"] else f" to {money(v['facts']['total_to'])}"))
        # avoid evidence, strongest first
        av = None
        listed = [src["avoid"][k] for k in keys if k in src["avoid"]]
        held_back = False
        if listed:
            s = avoid_reason_from_list(listed[0].reasons)
            ev = []
            try:
                ev = [e.get("url") for e in json.loads(listed[0].evidence_json) if e.get("url")]
            except (TypeError, ValueError):
                pass
            if s:
                av = {"kind": "avoid_list", "priority": 1, "reason": s,
                      "source": {"name": "The search's avoid list (city records and tenant reports)", "file": "data/avoid_buildings.csv",
                                 "url": ev[0] if ev else None, "key": listed[0].addr_key}}
            else:
                held_back = True                 # on the avoid list for a reason this page does not put in words
        if av is None:
            for k in keys:
                r = src["rstd"].get(k)
                if r is not None and r.rating_verdict == "avoid" and isinstance(r.rating_verdict_why, str):
                    m = re.match(r"(\d+) negative reviews in the last (\d+) months", r.rating_verdict_why)
                    s = (f"{m.group(1)} tenant reviews in the last {m.group(2)} months report serious problems here." if m
                         else "Tenant reviews of this building are poor, with enough reviews to count.")
                    av = {"kind": "low_rating", "priority": 2, "reason": s,
                          "source": {"name": "Review screen of this search", "file": "data/evidence/rating_standard.csv",
                                     "url": r.source_url if isinstance(r.source_url, str) else None, "key": k}}
                    break
        if av is None and not vids and set(g.listing_id) & src["unverified"] and set(g.listing_id) <= src["unverified"]:
            av = {"kind": "unverified_listing", "priority": 4,
                  "reason": "A reviewer who read this listing could not confirm it is a real apartment that is available.",
                  "source": {"name": "Listing review of this search", "file": "data/evidence/review_verdicts.csv",
                             "url": b["listing_url"], "key": sorted(set(g.listing_id) & src["unverified"])[0]}}
        if av is None and not vids and not has_template:
            med = hood_median.get((h, int(first.beds)))
            if med and med[1] >= 10 and b["rent_range"][1] < 0.55 * med[0]:
                kind = "studios" if int(first.beds) == 0 else "one-bedrooms"
                av = {"kind": "price_far_below", "priority": 5,
                      "reason": (f"The rent asked ({money(b['rent_range'][1])}) is far below what {kind} here usually list for "
                                 f"({money(med[0])}), which often means a listing is not what it seems."),
                      "source": {"name": "Listing compared with the neighborhood's listings", "file": "data/listings.csv",
                                 "url": b["listing_url"], "key": str(first.listing_id)}}
        if av is None and dn:
            av = {"kind": "no_dogs", "priority": 6, "reason": "The listing says dogs are not allowed.",
                  "source": {"name": "The listing page", "file": "data/listings.csv", "url": b["listing_url"], "key": str(g.listing_id.iloc[0])}}
        if av is None and ground_only:
            av = {"kind": "ground_floor_only", "priority": 7,
                  "reason": "Every apartment listed here at $2,000 or less is on the ground floor.",
                  "source": {"name": "The listing page", "file": "data/listings.csv", "url": b["listing_url"], "key": str(g.listing_id.iloc[0])}}
        b["avoid"], b["held_back"] = av, held_back
        # building-level evidence score for the top three
        rec_known = any(k in src["rec_held"] for k in keys)
        pts = {"verified": 100 if vids else 0,
               "dogs": 20 if b["dogs"] == "yes" else 12 if b["dogs"] == "pets" else 0,
               "elevator_or_floor2": 15 if b["elevator_or_floor2"] else 0,
               "rating": round(max(-12.0, min(12.0, (rt["value"] - 3.5) * 8)), 1) if rt and rt["count"] >= 10 else 0,
               "record": 4 if rec_known and not listed else 0,
               "apartments": min(int(len(use)), 10),
               "own_site_contact": 5 if contact and contact.get("own_site") else 0}
        b["evidence_points"] = pts
        b["evidence_score"] = round(sum(pts.values()), 1)
        out[h].append(b)
    return out


def pick_buildings(bs):
    cand = [b for b in bs if b["usable"] and b["avoid"] is None and not b["held_back"] and not b["has_template_listing"]]
    top = sorted(cand, key=lambda b: (-b["evidence_score"], b["rent_range"][0], b["id"]))[:3]
    bad = sorted([b for b in bs if b["avoid"] and not b["rent_is_template"]], key=lambda b: (b["avoid"]["priority"], -b["apartments_listed"], b["id"]))[:2]
    return top, bad


def card(b, role):
    keep = ["id", "name", "address", "city", "state", "zip", "rent_range", "rent_text", "apartments", "known", "to_ask", "rating",
            "contact", "listing_url", "photo_url", "verified", "evidence_score", "evidence_points"]
    d = {k: b[k] for k in keep}
    if role == "avoid":
        d["reason"], d["source"], d["avoid_kind"] = b["avoid"]["reason"], b["avoid"]["source"], b["avoid"]["kind"]
        d["apartments"] = b["apartments_listed"]
    return d


# ---------------------------------------------------------------- neighborhood extras
def life_here():
    out = defaultdict(list)
    for f in ("life_here_facts.csv", "life_here_facts_nj.csv", "life_here_facts_ctny.csv"):
        for r in read(DATA / "reference" / f).itertuples():
            if isinstance(r.building_id, str) or r.moment != "neighborhood" or not isinstance(r.fact, str):
                continue
            if not text_ok(r.fact) or PHONE_RE.search(r.fact):
                continue
            item = {"place": r.place_name if isinstance(r.place_name, str) else None, "kind": r.place_kind if isinstance(r.place_kind, str) else None,
                    "fact": r.fact, "schedule": r.schedule if isinstance(r.schedule, str) and text_ok(r.schedule) else None,
                    "source_name": r.source_name, "source_url": r.source_url, "confidence": r.confidence}
            if item["fact"] not in [x["fact"] for x in out[r.neighborhood_id]]:
                out[r.neighborhood_id].append(item)
    return out


def overnight_rules():
    out = {}
    for r in read(DATA / "reference" / "overnight_parking_towns.csv").itertuples():
        for h in str(r.applies_to_hood_ids).split(";"):
            if h.strip():
                out[h.strip()] = {"severity": r.severity, "source_url": r.source_url, "town": r.municipality}
    return out


def confidence(width, listings):
    """How firmly the rank holds: from the width of the stable rank range and the number of listings behind it."""
    if width <= 12 and listings >= 30:
        return "high"
    if width > 40 or listings < 15:
        return "low"
    return "medium"


def clean_name(n):
    return re.sub(r"\s+city \(balance\)$", "", str(n))


# ---------------------------------------------------------------- build
def build():
    U, counts, zstats = load_listings()
    H = read(DATA / "neighborhoods.csv")
    S_ = read(DATA / "neighborhood_safety.csv").set_index("hood_id")
    jam = S_.loc["ny:jamaica"]
    H["rec_v"], H["rec_p"] = H.hood_id.map(S_.violent), H.hood_id.map(S_.property)
    H["rec_cut"] = (H.rec_v > jam.violent) | (H.rec_p > jam.property)          # the owner's Jamaica rule, as scripts/lifestyle_groups.py
    H["rec_index"] = 0.5 * H.rec_v / jam.violent + 0.5 * H.rec_p / jam.property
    groups = read(DATA / "lifestyle_groups.csv")
    overnight = overnight_rules()
    src = building_sources()

    assign = assign_hoods(U, H)
    U["hood_id"] = U.addr_key.map(lambda k: assign.get(k, (None, "no_coordinates"))[0])
    U["hood_method"] = U.addr_key.map(lambda k: assign.get(k, (None, "no_coordinates"))[1])
    U["bkey"] = U.addr_key.map(lambda k: bkey_of(k, src["cross"]))
    tstats = apply_templates(U)
    ids = set(H.hood_id)
    P20 = U[U.listed_rent <= RENT_SHOW]
    method_counts = {k: int(v) for k, v in U.hood_method.value_counts().sort_index().items()}
    cov = {"listings_used": int(len(U)), "assigned_to_any_neighborhood": int(U.hood_id.notna().sum()),
           "in_a_neighborhood_with_a_record": int(U.hood_id.isin(ids).sum()), "by_method": method_counts,
           "at_2000_or_less": int(len(P20)), "at_2000_or_less_in_a_neighborhood_with_a_record": int(P20.hood_id.isin(ids).sum())}

    supply = P20[P20.hood_id.notna()].groupby("hood_id").agg(a=("dedupe_key", "nunique"))
    supply["b"] = P20[P20.hood_id.notna() & P20.has_street].groupby("hood_id").bkey.nunique()
    supply["b"] = supply.b.fillna(0).astype(int)
    considered = sorted(supply.index)
    no_record = [h for h in considered if h not in ids]
    M = hood_measures(U, H, groups, overnight)
    Hx = H.set_index("hood_id")
    status = {}
    for h in considered:
        if h not in ids:
            status[h] = "no_neighborhood_record"
        elif Hx.drive_min[h] >= MAX_DRIVE_MIN:
            status[h] = "drive_2_hours_or_more"
        elif bool(Hx.rec_cut[h]):
            status[h] = "jamaica_rule"
        elif M[h]["buildings_2000"] < MIN_BUILDINGS:
            status[h] = "too_little_supply"
        else:
            status[h] = "ranked"
    eligible = sorted(h for h, s in status.items() if s == "ranked")
    S = measure_scores(M, eligible)
    sc_all = scenarios()
    ranks = {name: rank_ids(S, w)[0] for name, w in sc_all.items()}
    base_rank, base_score = rank_ids(S, WEIGHTS)

    med = {}
    P22 = U[U.listed_rent <= RENT_POOL]
    for (h, beds), g in P22[P22.hood_id.isin(eligible)].groupby(["hood_id", "beds"]):
        med[(h, int(beds))] = (float(g.listed_rent.median()), int(len(g)))
    B = build_buildings(U[U.hood_id.isin(eligible)], src, med)
    life = life_here()
    Gx = groups.set_index("hood_id")
    parent = {}
    for ft in json.loads((DATA / "reference" / "subcity_neighborhoods.geojson").read_text())["features"]:
        parent[ft["properties"]["hood_id"]] = ft["properties"]["parent_hood_id"]

    med_fig = {}
    for k in ("drive_min", "places_10min", "median_sqft", "dogs_yes_share", "park_walk_min", "median_rent", "apartments_2000"):
        vals = [M[h][k] for h in eligible if M[h].get(k) is not None]
        med_fig[k] = statistics.median(vals) if vals else None
    hoods = []
    for h in sorted(eligible, key=lambda x: base_rank[x]):
        m = M[h]
        why, know, pct = why_and_know(h, S, M, eligible, med_fig)
        tags, tags_true = tags_for(m, pct)
        top, bad = pick_buildings(B.get(h, []))
        role = {b["id"]: "top" for b in top}
        role.update({b["id"]: "avoid" for b in bad})
        rr = [ranks[n][h] for n in sc_all]
        measures = {}
        for meas in WEIGHTS:
            d = {"weight": WEIGHTS[meas], "score": S[h][meas], "known": S[h][meas] is not None}
            if meas != "records":
                d["figures"] = {k: m.get(k) for k, _, _, _ in SUBS[meas]}
            measures[meas] = d
        dn = display_figures("near", m)
        measures["near"]["figures"].update({"hours_per_month": dn["hours_per_month"], "toll_per_month": dn["toll_per_month"]})
        measures["cost"]["figures"].update({"listings": m["listings"], "typical_rent_shown": m["typical_rent_shown"], "buildings_2000": m["buildings_2000"]})
        measures["supply"]["figures"].update({k: m[k] for k in ("listings", "dogs_yes", "pets_general", "dogs_no", "elevator_or_floor2")})
        measures["going_out"]["figures"].update({"restaurants": m["restaurants"], "bars": m["bars"], "cafes": m["cafes"], "buildings_measured": m["record_buildings"]})
        measures["green"]["figures"]["buildings_measured"] = m["record_buildings"]
        measures["space"]["figures"]["sqft_stated"] = m["sqft_stated"]
        measures["parking"]["figures"].update({k: m[k] for k in ("parking_stated_buildings", "parking_offstreet_buildings", "overnight_rule")})
        lh = life.get(h) or [dict(x, about=clean_name(Hx.hood.get(parent.get(h), "the city")) + " as a whole") for x in life.get(parent.get(h), [])]
        o = overnight.get(h)
        row = Hx.loc[h]
        hoods.append({
            "id": h, "rank": base_rank[h], "name": clean_name(row.hood), "area": row.area, "state": row.state,
            "lat": round(float(row.lat), 5), "lon": round(float(row.lon), 5),
            "score": round(base_score[h], 1), "rank_range": [min(rr), max(rr)],
            "illustration_key": Gx.group_key.get(h) if h in Gx.index else None,
            "experience_label": Gx.group_label.get(h) if h in Gx.index else None,
            "tags": tags, "tags_true": tags_true,
            "typical_rent": int(round(m["typical_rent_shown"])), "typical_rent_note": "middle listed rent of the studios and one-bedrooms at $2,000 or less",
            "drive_min": int(round(m["drive_min"])), "toll_round_trip": m["toll_round_trip"],
            "counts": {"buildings": m["buildings_2000"], "apartments": m["apartments_2000"],
                       "buildings_usable": sum(1 for b in B.get(h, []) if b["usable"] and not b["rent_is_template"]),
                       "buildings_template_price_only": sum(1 for b in B.get(h, []) if b["rent_is_template"]), "listings_in_pool": m["listings"]},
            "measures": measures, "measures_known": sum(1 for v in measures.values() if v["known"]),
            "why": why, "know_this": know,
            "overnight_parking": ({"rule": o["severity"], "text": sentence("parking", dict(m, offstreet_share=None))[0], "source_url": o["source_url"]} if o else None),
            "life_here": lh[:6],
            "top_buildings": [card(b, "top") for b in top],
            "avoid_buildings": [card(b, "avoid") for b in bad],
            "all_buildings": [{"id": b["id"], "name": b["name"], "rent_range": b["rent_range"], "apartments": b["apartments_listed"],
                               "known": b["known"], "to_ask": b["to_ask"], "role": role.get(b["id"], "listed"),
                               "rent_text": b["rent_text"], "rent_is_template": b["rent_is_template"],
                               "verified": b["verified"]["on_page"], "listing_url": b["listing_url"]}
                              for b in sorted(B.get(h, []), key=lambda b: (-b["evidence_score"], b["rent_range"][0], b["id"]))],
            "sensitivity": {n: ranks[n][h] for n in sc_all},
            "supply_note": (None if len(top) >= 3 else
                            f"Only {len(top)} {'building here has' if len(top) == 1 else 'buildings here have'} an apartment at $2,000 or less "
                            "with nothing stated against it." if top else "No building here has an apartment at $2,000 or less with nothing stated against it."),
            "confidence": confidence(max(rr) - min(rr), m["listings"]),
            "confidence_basis": {"rank_range_width": max(rr) - min(rr), "listings": m["listings"]},
        })

    n_el = len(eligible)
    coverage = {}
    for meas, subs in SUBS.items():
        coverage[meas] = {"neighborhoods_with_measure": sum(1 for h in eligible if S[h][meas] is not None), "of": n_el,
                          "parts": {k: sum(1 for h in eligible if M[h].get(k) is not None) for k, _, _, _ in subs}}
    cut_j = [h for h, s in status.items() if s == "jamaica_rule"]
    meta = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_as_of": str(U.last_seen.max())[:10],
        "rent_limit": RENT_SHOW, "rent_pool": RENT_POOL, "max_drive_min": MAX_DRIVE_MIN, "min_buildings": MIN_BUILDINGS,
        "visits_per_month": VISITS_PER_MONTH, "move_in_by": MOVE_IN_BY,
        "weights": WEIGHTS,
        "measures": {k: {"label": MEASURE_LABELS[k], "weight": WEIGHTS[k], "shown_as_text": k != "records",
                         "parts": [{"key": key, "share": w, "higher_is_better": hb, "scale": how or "linear"} for key, w, hb, how in SUBS[k]]}
                     for k in WEIGHTS},
        "scoring": ("Each part is scaled 0 to 1 across the ranked neighborhoods (between the 5th and 95th percentile, so one extreme place "
                    "does not flatten the rest). A measure is the weighted mean of its known parts. The score is the weighted mean of the "
                    "known measures, times 100: a missing measure earns nothing and costs nothing."),
        "coverage": coverage,
        "counts": dict(counts, **{
            "listings_at_2000_or_less": int(len(P20)),
            "listings_at_2000_or_less_without_a_street_address": int((~P20.has_street).sum()),
            "listings_at_2000_or_less_in_ranked_neighborhoods": int(P20.hood_id.isin(eligible).sum()),
            "neighborhoods_considered": len(considered),
            "no_neighborhood_record": len(no_record),
            "no_neighborhood_record_with_5_buildings": int(sum(1 for h in no_record if supply.b[h] >= MIN_BUILDINGS)),
            "with_a_record": len(considered) - len(no_record),
            "cut_drive": sum(1 for s in status.values() if s == "drive_2_hours_or_more"),
            "cut_by_the_jamaica_rule": len(cut_j),
            "cut_by_the_jamaica_rule_with_5_buildings": sum(1 for h in cut_j if M[h]["buildings_2000"] >= MIN_BUILDINGS),
            "too_little_supply": sum(1 for s in status.values() if s == "too_little_supply"),
            "eligible": n_el,
            "buildings_in_ranked_neighborhoods": sum(len(B.get(h, [])) for h in eligible),
            "top_buildings": sum(len(x["top_buildings"]) for x in hoods), "avoid_buildings": sum(len(x["avoid_buildings"]) for x in hoods),
            "buildings_held_back_without_text": sum(1 for h in eligible for b in B.get(h, []) if b["held_back"]),
        }),
        "neighborhood_assignment": cov,
        "template_prices": tstats,
        "zumper_no_pets_block": dict(zstats, finding="a real statement by the lister, not a site default"),
        "sensitivity": {"scenarios": {n: w for n, w in sc_all.items()},
                        "note": "rank under each weight x1.5 and x0.5 and under equal weights; rank_range is the lowest and highest of these"},
        "tag_floors": TAG_FLOORS,
        "list_medians": med_fig,
        "know_this_rule": "a measure in the bottom 40% of the ranked list whose own figure is worse than the list's median; none when nothing qualifies",
        "confidence_rule": "high: rank range 12 or narrower and 30+ listings; low: range wider than 40 or under 15 listings; otherwise medium",
        "min_reviews_for_rating": MIN_REVIEWS_SHOWN,
        "top_building_points": {"verified on the page": 100, "dogs stated allowed": 20, "pets stated allowed": 12, "elevator or second floor stated": 15,
                                "rating (10+ reviews)": "(rating - 3.5) x 8, between -12 and 12", "record held and clean": 4,
                                "apartments listed (each, up to 10)": 1, "own-site contact": 5},
        "avoid_order": ["avoid_list", "low_rating", "unverified_listing", "price_far_below", "no_dogs", "ground_floor_only"],
        "not_measured": ["Listing descriptions are not held in the listings table, so repeated template text is not tested.",
                         "Going out and green come from the neighborhood record, measured at the buildings that passed the earlier checks.",
                         "Overnight street parking is known only for the towns whose rules were read."],
    }
    table = []
    for h in considered:
        st = status[h]
        r = {"rank": base_rank.get(h, ""), "hood_id": h, "name": clean_name(Hx.hood[h]) if h in ids else "", "state": h[:2].upper(), "status": st,
             "score": round(base_score[h], 1) if st == "ranked" else "",
             "rank_low": min(ranks[n][h] for n in sc_all) if st == "ranked" else "", "rank_high": max(ranks[n][h] for n in sc_all) if st == "ranked" else "",
             "buildings_2000": int(supply.b[h]), "apartments_2000": int(supply.a[h])}
        if h in ids:
            m = M[h]
            for k in ("listings", "drive_min", "toll_round_trip", "median_rent", "typical_rent_shown", "dogs_yes", "pets_general", "dogs_no",
                      "elevator_or_floor2", "places_10min", "park_walk_min", "park_ha_800m", "dog_run_miles", "median_sqft", "sqft_stated",
                      "parking_offstreet_buildings", "parking_stated_buildings", "overnight_rule"):
                r[k] = "" if m.get(k) is None else m[k]
        if st == "ranked":
            for meas in WEIGHTS:
                r["score_" + meas] = "" if S[h][meas] is None else round(S[h][meas], 3)
            for n in sc_all:
                r["rank_" + n] = ranks[n][h]
            hd = next(x for x in hoods if x["id"] == h)
            r["tags"] = "; ".join(hd["tags"])
            r["top_buildings"] = "; ".join(b["name"] for b in hd["top_buildings"])
            r["avoid_buildings"] = "; ".join(b["name"] for b in hd["avoid_buildings"])
        table.append(r)
    order = {"ranked": 0, "too_little_supply": 1, "jamaica_rule": 2, "drive_2_hours_or_more": 3, "no_neighborhood_record": 4}
    table.sort(key=lambda r: (order[r["status"]], r["rank"] if r["rank"] != "" else 0, -r["buildings_2000"], r["hood_id"]))
    return {"meta": meta, "neighborhoods": hoods}, table


def write(doc, table):
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    cols = list(dict.fromkeys(k for r in table for k in r))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(table)


def main():
    doc, table = build()
    write(doc, table)
    c = doc["meta"]["counts"]
    print(f"listings used {c['listings_used']}; neighborhoods considered {c['neighborhoods_considered']}, no record {c['no_neighborhood_record']}, "
          f"Jamaica rule {c['cut_by_the_jamaica_rule']}, too little supply {c['too_little_supply']}, ranked {c['eligible']}")
    for h in doc["neighborhoods"][:12]:
        print(f"{h['rank']:>3} {h['name'][:38]:38} {h['score']:5.1f}  range {h['rank_range'][0]}-{h['rank_range'][1]}  {', '.join(h['tags'])}")
    print(f"wrote {OUT_CSV.relative_to(ROOT)} and {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
