#!/usr/bin/env python3
"""Build site/concierge_data.json, the data of the concierge page (docs/CONCIERGE_DESIGN.md), from site/data.json.

site/data.json is read and never written. No network.

WHAT IT DOES, IN ORDER
  1 KEEP      apartments with rent.listed <= RENT_LIMIT, and the buildings, neighborhoods and experiences they leave
              non-empty.
  2 BASE      site/_concierge_base.json: a copy of the page data in the SAME SHAPE holding only what is kept, with
              every experience and neighborhood figure recomputed over the kept apartments (base_page). The
              recomputation is the one scripts/build_page_data.py does, here from the page data's own apartments
              (its helpers v, shown_figures are imported). `--self-check` runs it over ALL apartments and compares
              with the figures site/data.json already carries, so the method is tested against the pipeline.
  3 TEXT      the existing drafts and guards are run over the base file, nothing is written by this script:
                realtor_lines.py --data <base> --out ..._u2000.csv        apartment lines, building About
                build_scene_text.py --data <base> --out-suffix _u2000     experience and neighborhood text
                check_scene_text.py --data <base> --out-suffix _u2000
              then the text is attached to the base with page_data_extras's own blocks (experience_text,
              neighborhood_text, about_building, realtor_lines, ranking, display_labels), and
                check_published_text.py --data <base> --out-suffix _u2000 --text-only
              audits the result. Any failure stops the build (exit 1); `--no-text` skips the three builders and
              reuses the _u2000 tables on disk.
  4 CONCIERGE site/concierge_data.json in the shape of the data contract: story cards, why / give_up, facts, scores,
              parking of one-apartment neighborhoods, either/or questions.

BUILDING SCORES (0..1, for re-weighting on the page). They come from the apartment `scores.parts` of the page data
(scripts/rank.py, docs/RANKING.md section 5: each part is 0-100, a blend of percentiles across all ranked
apartments). A building's value is the mean over its kept apartments, divided by 100.
    parents    parts.distance   drive to her parents 50, transit 20, tolls 12, transfers, last train, Sunday return
    value      parts.cost       total with utilities and fees 85, cost lines stated rather than estimated 15
    parking    parts.car        kind of parking space 50, parking fee, surface parking, vehicle safety
    green      parts.dog        walk to green 25, park area, dog park, woods, vets, dog amenities, weight limit, pet rent
    home       (12 x parts.space + 16 x parts.building) / 28   size and a separate bedroom; laundry, gym, lounge,
               front desk, controlled entry, year built (the two parts weighted as rank.py weights them)
    going_out  NO PART MEASURES IT (parts.daily is supermarket, cafés, gyms, corner stores). It is built the way
               rank.py builds a part, a blend of percentiles (average rank, 0-100) over every apartment in
               site/data.json: restaurants within 800 m 40, bars within 800 m 20, restaurants within 1,600 m 20,
               bars within 1,600 m 20 (the fields of the "after work" and "Saturday night" moments).
parts.safety is not exposed: nothing about crime is said on this page, and everything shown already passed the rule.

Run from the house-hunt folder:
    python3 scripts/concierge_data.py              build everything
    python3 scripts/concierge_data.py --no-text    reuse the _u2000 text tables on disk
    python3 scripts/concierge_data.py --self-check compare the recomputation with site/data.json over all apartments
Tests: python3 scripts/test_concierge_data.py
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_page_data as BP  # noqa: E402   v(), shown_figures(): the page builder's own helpers
import page_data_extras as X  # noqa: E402   the text blocks, is_private_line(), ranking()
import realtor_lines as RL  # noqa: E402     parking_facts(), usd()

RENT_LIMIT = 2000                 # listed base rent; a rule for this page only (Will, 2026-11-16/17)
SUFFIX = "_u2000"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data.json"
BASE = ROOT / "site" / "_concierge_base.json"
OUT = ROOT / "site" / "concierge_data.json"
REF = ROOT / "data" / "reference"
TOUR_START, MOVE_IN_BY, ANCHOR_LABEL = "2026-11-22", "2026-12-15", "Mom and Dad"

# ---------------------------------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------------------------------
v = BP.v


def miss(x):
    return x is None or (isinstance(x, float) and math.isnan(x)) or (isinstance(x, str) and not x.strip())


def num(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def median(xs):
    xs = sorted(x for x in (num(x) for x in xs) if x is not None)
    if not xs:
        return None
    k = len(xs) // 2
    return xs[k] if len(xs) % 2 else (xs[k - 1] + xs[k]) / 2


def span(xs):
    xs = [x for x in (num(x) for x in xs) if x is not None]
    return [min(xs), max(xs)] if xs else None


def tidy(x, nd=1):
    """A JSON number: whole where it is whole, else rounded; None stays None."""
    if x is None:
        return None
    x = round(float(x), nd)
    return int(x) if x == int(x) else x


def mo(u, a, b):
    return ((u.get("moments") or {}).get(a) or {}).get(b)


def hood_rank(u):
    return (num((u.get("scores") or {}).get("hood_rank")) or 1e9, str(u["id"]))


def toll_known(u, key="toll_round_trip"):
    """The round-trip toll of an apartment's route, only when every crossing has a rate (never 0 for unknown)."""
    return num(mo(u, "sun", key)) if mo(u, "sun", "toll_complete") else None


# ---------------------------------------------------------------------------------------------------------------------
# 2. The base: the page data, kept apartments only, figures recomputed (same shape as site/data.json)
# ---------------------------------------------------------------------------------------------------------------------
# years[].medians keys -> how an apartment's value is read from the page data (scripts/build_page_data.py MEAS)
MEASURES = {
    "all_in": lambda u, h: u.get("all_in"),
    "sqft": lambda u, h: u.get("sqft"),
    "drive_min": lambda u, h: mo(u, "sun", "drive_min"),
    "transit_min": lambda u, h: mo(u, "sun", "transit_min"),
    "toll_round_trip": lambda u, h: toll_known(u),
    "toll_round_trip_mail": lambda u, h: mo(u, "sun", "toll_round_trip_mail"),
    "violent_per_1000": lambda u, h: (h.get("safety") or {}).get("violent_per_1000"),
    "property_per_1000": lambda u, h: (h.get("safety") or {}).get("property_per_1000"),
    "restaurants_800m": lambda u, h: mo(u, "after", "restaurants_800m"),
    "park_walk_min": lambda u, h: mo(u, "wake", "park_walk_min"),
    "parking_rank": lambda u, h: (u.get("parking") or {}).get("rank"),
}


def _master_distances():
    """park_ha_800m and open_water_m per building: the two door-distance figures the page data does not carry on an
    apartment (scripts/check_scene_text.py reads them from the same file the same way)."""
    try:
        mb = pd.read_csv(ROOT / "data" / "master_buildings.csv", low_memory=False,
                         usecols=lambda c: c in ("building_id", "open_water_m", "park_ha_800m"))
        return mb.drop_duplicates("building_id").set_index("building_id")
    except (OSError, ValueError):
        return pd.DataFrame()


def _shown_frame(us, mb):
    """The kept apartments of one neighborhood as the rows BP.shown_figures reads."""
    rows = []
    for i, u in enumerate(sorted(us, key=hood_rank), 1):
        b = u.get("building_id")
        r = {"building_id": b, "shown_rank": i,
             "restaurants_800m": mo(u, "after", "restaurants_800m"), "bars_800m": mo(u, "after", "bars_800m"),
             "cafes_800m": mo(u, "after", "cafes_800m"), "park_walk_min": mo(u, "wake", "park_walk_min"),
             "dog_park_m": mo(u, "wake", "dog_park_m"), "supermarket_m": mo(u, "work", "supermarket_m"),
             "train_station_m": mo(u, "sat", "train_station_m"), "motorway_m": mo(u, "work", "motorway_m"),
             "restaurants_1600m": mo(u, "sat", "restaurants_1600m"), "bars_1600m": mo(u, "sat", "bars_1600m"),
             "train_station_kind": mo(u, "sat", "train_station_kind"), "train_station": mo(u, "sat", "train_station"),
             "train_station_system": mo(u, "sat", "train_station_system"),
             "commuter_station_m": mo(u, "sat", "commuter_station_m")}
        for k in ("park_ha_800m", "open_water_m"):
            r[k] = mb.at[b, k] if (len(mb) and k in mb.columns and b in mb.index) else None
        rows.append(r)
    return pd.DataFrame(rows)


def base_page(d, limit=RENT_LIMIT):
    """-> the page data restricted to apartments with rent.listed <= limit (None: all), every figure of an
    experience, a neighborhood and a building recomputed over those apartments. Written text is cleared: it is
    attached again from the tables built over this file. Fields that do not depend on which apartments are shown
    (traits, safety, local rules, quotes, descriptions, contacts, ratings, photos) are carried as they are."""
    d = copy.deepcopy(d)
    keep = [u for u in d["units"] if limit is None or (num((u.get("rent") or {}).get("listed")) is not None
                                                        and u["rent"]["listed"] <= limit)]
    all_units = d["units"]
    hoods_all = {h["id"]: h for h in d["neighborhoods"]}
    by_b, by_h, by_y = defaultdict(list), defaultdict(list), defaultdict(list)
    for u in keep:
        by_b[u["building_id"]].append(u)
        by_h[u["hood_id"]].append(u)
        by_y[u["year"]].append(u)
    mb = _master_distances()
    # buildings
    blds = []
    for b in d.get("buildings") or []:
        us = sorted(by_b.get(b["id"]) or [], key=hood_rank)
        if not us:
            continue
        ex = [u["all_in"] for u in us if not miss(u.get("all_in"))]
        likely = [u.get("all_in_likely") for u in us if not miss(u.get("all_in_likely"))]
        best = us[0]
        b.update({"unit_ids": [u["id"] for u in us], "n_units": len(us),
                  "from_all_in": v(min(ex)) if ex else None, "to_all_in": v(max(ex)) if ex else None,
                  "from_all_in_likely": v(min(likely)) if likely else None,
                  "best_unit_id": best["id"], "best_rank_score": (best.get("scores") or {}).get("rank"),
                  "open_items": sorted({x for u in us for x in str((u.get("confirm") or {}).get("what") or "").split("; ") if x}),
                  "units_with_asterisk": sum(1 for u in us if (u.get("confirm") or {}).get("asterisk"))})
        blds.append(b)
    per_hood = defaultdict(list)
    for b in blds:
        per_hood[b["hood_id"]].append(b)
    for hid, bl in per_hood.items():
        bl.sort(key=lambda b: hood_rank(by_b[b["id"]][0]))
        for i, b in enumerate(bl, 1):
            b["rank_in_neighborhood"] = i
    # neighborhoods
    hoods = []
    for h in d["neighborhoods"]:
        us = sorted(by_h.get(h["id"]) or [], key=hood_rank)
        if not us:
            continue
        bl = per_hood[h["id"]]
        complete = all(bool(mo(u, "sun", "toll_complete")) for u in us)
        tolls = [toll_known(u) for u in us]
        mails = [num(mo(u, "sun", "toll_round_trip_mail")) for u in us]
        h["counts"] = {**(h.get("counts") or {}), "shown": len(us), "buildings": len(bl)}
        h.update({
            "lat": round(sum(u["lat"] for u in us) / len(us), 5), "lon": round(sum(u["lon"] for u in us) / len(us), 5),
            "building_ids": [b["id"] for b in bl],
            "all_in_range": [v(min(u["all_in"] for u in us)), v(max(u["all_in"] for u in us))],
            "sqft_median": v(median(u.get("sqft") for u in us)),
            "drive_min": v(median(mo(u, "sun", "drive_min") for u in us)),
            "transit_min": v(median(mo(u, "sun", "transit_min") for u in us)),
            "toll_round_trip": v(median(tolls)) if complete else None,
            "toll_round_trip_range": ([v(x) for x in span(tolls)] if complete and span(tolls) else None),
            "toll_round_trip_mail_range": ([v(x) for x in span(mails)] if complete and span(mails) else None),
            "toll_round_trip_mail": v(median(mails)) if complete and all(m is not None for m in mails) else None,
            "toll_complete": complete,
            "shown_figures": BP.shown_figures(_shown_frame(us, mb), bl),
            "vs_queens": {k: v(median((u.get("vs_queens") or {}).get(k) for u in us)) for k in (h.get("vs_queens") or {})},
            "unit_ids": [u["id"] for u in us]})
        X.clear_text_fields(h, also=("at_a_glance",))
        hoods.append(h)
    # experiences. The Queens baseline of vs_queens_diff stays the page's own (the Queens apartments of site/data.json):
    # it is the yardstick "a typical Queens apartment", not a figure of this page.
    queens = [u for u in all_units if str(hoods_all.get(u["hood_id"], {}).get("area") or "") == "Queens"]
    years = []
    for y in d["years"]:
        us = by_y.get(y["id"]) or []
        if not us:
            continue
        vals = {k: [x for x in (num(f(u, hoods_all.get(u["hood_id"]) or {})) for u in us) if x is not None]
                for k, f in MEASURES.items()}
        home = {k: [x for x in (num(f(u, hoods_all.get(u["hood_id"]) or {})) for u in queens) if x is not None]
                for k, f in MEASURES.items()}
        dh = {hid: median(mo(u, "sun", "drive_min") for u in g) for hid, g in by_h.items() if g[0]["year"] == y["id"]}
        dh = {k: x for k, x in dh.items() if x is not None}
        ends = None
        if dh:
            near, far = min(sorted(dh), key=dh.get), max(sorted(dh), key=dh.get)
            ends = {"nearest": {"hood_id": near, "name": hoods_all[near]["name"], "drive_min": v(round(dh[near], 1))},
                    "farthest": {"hood_id": far, "name": hoods_all[far]["name"], "drive_min": v(round(dh[far], 1))}}
        mine = [h for h in hoods if h["year"] == y["id"]]
        y["counts"] = {**(y.get("counts") or {}), "neighborhoods": len(mine), "buildings": len({u["building_id"] for u in us}),
                       "shown": len(us)}
        y.update({
            "all_in_range": [v(min(u["all_in"] for u in us)), v(max(u["all_in"] for u in us))],
            "drive_min_range": [v(x) for x in span(mo(u, "sun", "drive_min") for u in us)] if vals["drive_min"] else None,
            "drive_min_range_hoods": ends,
            "medians": {k: (v(round(median(x), 1)) if x else None) for k, x in vals.items()},
            "ranges": {k: ([v(round(min(x), 1)), v(round(max(x), 1))] if x else None) for k, x in vals.items()},
            "vs_queens": {k: v(median((u.get("vs_queens") or {}).get(k) for u in us)) for k in (y.get("vs_queens") or {})},
            "vs_queens_diff": {k: (v(round(median(vals[k]) - median(home[k]), 1)) if vals[k] and home[k] else None)
                               for k in MEASURES},
            "hood_ids": [h["id"] for h in sorted(mine, key=lambda h: h["drive_min"] or 999)]})
        X.clear_text_fields(y, also=("display_label",))
        years.append(y)
    d["units"], d["buildings"], d["neighborhoods"], d["years"] = keep, blds, hoods, years
    for u in keep:                                   # apartment text is attached again from the _u2000 tables
        u.pop("host", None)
        u.pop("headlines", None)
    for k in ("neighborhoods_avoid_only", "avoid", "held", "awaiting_live_check"):
        d[k] = []                                    # not part of this page
    m = d["meta"]
    m["counts"] = {**m.get("counts", {}), "shown": len(keep), "buildings": len(blds), "neighborhoods": len(hoods),
                   "shown_with_asterisk": sum(1 for u in keep if (u.get("confirm") or {}).get("asterisk")),
                   "avoid": 0, "held": 0, "neighborhoods_avoid_only": 0}
    if limit is not None:
        m["concierge"] = {"rent_limit": limit, "source": "site/data.json", "source_built_at": m.get("built_at"),
                          "note": "A filtered copy for the concierge page: only apartments at or under the rent limit, "
                                  "figures recomputed over them. Built by scripts/concierge_data.py; never published."}
    return d


def self_check(d):
    """The recomputation over ALL apartments must give the figures site/data.json carries. -> list of differences."""
    b = base_page(d, None)
    out = []

    def same(a, c):
        if isinstance(a, dict) and isinstance(c, dict):
            return set(a) == set(c) and all(same(a[k], c[k]) for k in a)
        if isinstance(a, (list, tuple)) and isinstance(c, (list, tuple)):
            return len(a) == len(c) and all(same(x, y) for x, y in zip(a, c))
        if isinstance(a, (int, float)) and isinstance(c, (int, float)) and not isinstance(a, bool):
            return abs(a - c) <= 0.0051        # the page rounds a median toll to cents from unrounded routes
        return a == c
    for kind, keys in (("years", ("counts", "all_in_range", "drive_min_range", "drive_min_range_hoods", "medians", "ranges",
                                  "vs_queens", "vs_queens_diff")),
                       ("neighborhoods", ("counts", "lat", "lon", "building_ids", "all_in_range", "sqft_median", "drive_min",
                                          "transit_min", "toll_round_trip", "toll_round_trip_range",
                                          "toll_round_trip_mail_range", "toll_round_trip_mail", "toll_complete",
                                          "shown_figures", "vs_queens", "unit_ids")),
                       ("buildings", ("unit_ids", "n_units", "from_all_in", "to_all_in", "from_all_in_likely", "best_unit_id",
                                      "best_rank_score", "open_items", "units_with_asterisk", "rank_in_neighborhood"))):
        old = {o["id"]: o for o in d[kind]}
        new = {o["id"]: o for o in b[kind]}
        if set(old) != set(new):
            out.append(f"{kind}: ids differ ({sorted(set(old) ^ set(new))[:5]})")
        for i in sorted(set(old) & set(new)):
            for k in keys:
                if not same(old[i].get(k), new[i].get(k)):
                    out.append(f"{kind} {i} {k}: page {json.dumps(old[i].get(k))[:140]} / recomputed {json.dumps(new[i].get(k))[:140]}")
    return out




# ---------------------------------------------------------------------------------------------------------------------
# 3. Text: the existing builders and guards, run over the base file
# ---------------------------------------------------------------------------------------------------------------------
class SubsetPaths(X.Paths):
    """page_data_extras's paths, with the four text tables read from their _u2000 copies."""

    def __init__(self):
        super().__init__(ROOT, BASE)
        for k in ("scene_years", "scene_hoods", "building_about", "realtor_lines"):
            q = getattr(self, k)
            setattr(self, k, q.with_name(q.stem + SUFFIX + q.suffix))


def run(cmd, out=print):
    r = subprocess.run([sys.executable] + cmd, cwd=ROOT, capture_output=True, text=True)
    tail = [ln for ln in (r.stdout + r.stderr).strip().splitlines() if ln.strip()]
    out(f"  {' '.join(cmd[:1])}: exit {r.returncode}" + (f"; {tail[-1][:150]}" if tail else ""))
    if r.returncode:
        for ln in tail[-25:]:
            out("    " + ln)
    return r.returncode


def write_base(b):
    BASE.write_text(json.dumps(b, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def attach_text(b):
    """The _u2000 tables onto the base, with page_data_extras's own blocks (and its neighborhood ranking)."""
    c = X.Ctx(b, SubsetPaths())
    rep = {f.__name__: f(c) for f in (X.experience_text, X.neighborhood_text, X.about_building, X.realtor_lines,
                                      X.ranking, X.display_labels)}
    b["meta"]["extras"] = rep
    return rep


def build_text(b, rebuild=True, out=print):
    """Writes the base, runs the builders and guards over it, attaches the text. -> number of failing steps."""
    rel = str(BASE.relative_to(ROOT))
    write_base(b)
    bad = 0
    if rebuild:
        bad += bool(run(["scripts/realtor_lines.py", "--data", rel, "--out", f"data/reference/realtor_lines{SUFFIX}.csv",
                         "--out-buildings", f"data/reference/building_about{SUFFIX}.csv"], out))
        bad += bool(run(["scripts/build_scene_text.py", "--data", rel, "--out-suffix", SUFFIX], out))
    bad += bool(run(["scripts/check_scene_text.py", "--data", rel, "--out-suffix", SUFFIX], out))
    for k, r in attach_text(b).items():
        out(f"  {k}: {r}")
    write_base(b)
    bad += bool(run(["scripts/check_published_text.py", "--data", rel, "--out-suffix", SUFFIX, "--text-only"], out))
    return bad


# ---------------------------------------------------------------------------------------------------------------------
# 4. The concierge data
# ---------------------------------------------------------------------------------------------------------------------
SCORE_KEYS = ("parents", "going_out", "green", "value", "parking", "home")
BANNED = re.compile(r"\ball[- ]in\b|\bcaps?\b|\bunits?\b|\bgates?\b|\bwe\b|\bnet[- ]effective\b", re.I)
CRIME = re.compile(r"\bcrimes?\b|\bviolent\b|burglar|\bthefts?\b|\bstolen\b|break-ins?|per 1,000", re.I)
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"])")


def sentences(text):
    return [x.strip() for x in SENT.split(str(text or "").replace("St. ", "St ").strip()) if x.strip()]


def voice(text):
    """On this page her parents are "Mom and Dad" (the page-one text says "your parents"). Nothing else changes."""
    if text is None:
        return None
    t = str(text).replace("St ", "St. ")
    t = re.sub(r"\bYour parents\b", "Mom and Dad", t)
    t = re.sub(r"\byour parents\b", "Mom and Dad", t)
    return t


def pct_rank(values):
    """value -> its average-rank percentile (0-100) among `values`, the way rank.py's pct() scores a variable."""
    s = pd.Series([x for x in values if x is not None], dtype=float)
    r = s.rank(pct=True, method="average") * 100
    return dict(zip(s.tolist(), r.tolist()))


def going_out_scores(all_units):
    """{apartment id: 0-100}: see the module docstring (going_out)."""
    parts = (("after", "restaurants_800m", 40), ("after", "bars_800m", 20), ("sat", "restaurants_1600m", 20), ("sat", "bars_1600m", 20))
    ranks = {(a, k): pct_rank([num(mo(u, a, k)) for u in all_units]) for a, k, _ in parts}
    out = {}
    for u in all_units:
        tot = wsum = 0.0
        for a, k, w in parts:
            x = num(mo(u, a, k))
            tot += (ranks[(a, k)][x] if x is not None else 25.0) * w      # unknown = 25th percentile, as in rank.py
            wsum += w
        out[u["id"]] = tot / wsum
    return out


def apartment_scores(u, going):
    p = (u.get("scores") or {}).get("parts") or {}
    g = lambda k: num(p.get(k))
    home = None if g("space") is None or g("building") is None else (12 * g("space") + 16 * g("building")) / 28
    raw = {"parents": g("distance"), "going_out": going.get(u["id"]), "green": g("dog"), "value": g("cost"),
           "parking": g("car"), "home": home}
    return {k: (None if x is None else x / 100) for k, x in raw.items()}


def haversine_km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def park_neighborhoods(hoods, n_apts):
    """parked_under / also_nearby (the rule of docs/CONCIERGE_DESIGN.md): a neighborhood with exactly one apartment is
    parked under the nearest neighborhood (great-circle distance) of its experience that has two or more. Where an
    experience has none with two or more, ONE neighborhood stays a stop (the most apartments; on a tie the one
    nearest the others, then the id) and the others are parked under it, so a parked neighborhood is never a host.
    -> notes for the report."""
    notes = []
    for h in hoods:
        h["parked_under"], h["also_nearby"] = None, []
    by = {h["id"]: h for h in hoods}
    for exp in sorted({h["experience_id"] for h in hoods}):
        mine = [h for h in hoods if h["experience_id"] == exp]
        hosts, fallback = [h for h in mine if n_apts[h["id"]] >= 2], False
        if not hosts and len(mine) > 1:
            hosts = [min(mine, key=lambda h: (-n_apts[h["id"]], sum(haversine_km(h, o) for o in mine), h["id"]))]
            fallback = True
        for h in mine:
            if n_apts[h["id"]] != 1 or h in hosts or not hosts:
                continue
            host = min(hosts, key=lambda o: (haversine_km(h, o), o["id"]))
            h["parked_under"] = host["id"]
            by[host["id"]]["also_nearby"].append(h["id"])
            notes.append({"neighborhood": h["id"], "under": host["id"], "km": round(haversine_km(h, host), 1), "fallback": fallback})
    return notes


# ---- why / give_up: one existing, guarded sentence each ------------------------------------------------------------
ASKS = re.compile(r"\bask\b|\bconfirm|\bnot published\b|\bnot stated\b|\bnot mention|\bcheck\b|\bfew details\b|\$3,000|"
                  r"\bspecial offer\b|\bnot say\b|\bin writing\b|\bto choose from\b|\bto compare\b", re.I)
# topic -> (pattern of a sentence that states a strength, test on the building's own facts)
GOOD = {
    "parents": (re.compile(r"parents are (?:about \d+ minutes|very close|close)|close to your parents|drive to your parents has no tolls", re.I),
                lambda f: f["drive"] is not None and f["drive"] <= 30),
    "going_out": (re.compile(r"restaurants (?:are )?within a 10-minute walk|walk to dinner|eating out|plenty to eat|choice of restaurants", re.I),
                  lambda f: (f["rest"] or 0) >= 10),
    "green": (re.compile(r"minutes (?:away )?on foot|minutes to [A-Z]|could walk to [A-Z][^.]* in about|walk to [A-Z][^.]* takes about|own dog (?:park|run|area)|dog (?:park|run) on the property|"
                         r"waterfront|riverfront|take the dog out", re.I),
              lambda f: (f["parkwalk"] is not None and f["parkwalk"] <= 5) or f["own_dog"]),
    "value": (re.compile(r"well under your limit|room in your budget|price is low|prices are low|lower-priced|costs less|far below your limit|"
                         r"leaves room", re.I), lambda f: True),
    "parking": (re.compile(r"included in the rent|rent includes a space|free off-street|park free|parking (?:in the open lot )?is free|not pay extra|"
                           r"garage (?:among|for your car)|own garage|only building[^.]*with a garage|covered parking", re.I),
                lambda f: f["park_kind"] in ("garage", "covered") or f["park_included"]),
    "home": (re.compile(r"large apartment|1-bedroom|washer and dryer|laundry in the apartment|\bpool\b", re.I),
             lambda f: True),
}
# a second pass, used only when no topic has a sentence above: smaller things the building text states as a plus
GOOD_MINOR = re.compile(r"garage parking costs|coworking|\bgym\b|concierge|train station is 0\.[0-4] miles|subway station is 0\.[0-4] miles|"
                        r"minutes (?:away )?on foot|supermarket[^.]* is 0\.[0-3] miles", re.I)
# topic -> (pattern of a sentence that states the cost of choosing this building, test on its facts)
BAD = {
    "parents": (re.compile(r"parents are about \d+ minutes away|drive to your parents is very long|visiting your parents costs|visits would be day trips|"
                           r"visits would be by car", re.I),
                lambda f: f["drive"] is not None and (f["drive"] > 30 or (f["toll"] or 0) > 0)),
    "going_out": (re.compile(r"drive for every meal|going out means driving|you would usually drive|no restaurants are within|little is within|"
                             r"evenings are quiet|no nightlife|there are no bars|nothing to eat or drink|not much to do", re.I),
                  lambda f: (f["rest"] or 0) < 15 or (f["bars"] or 0) == 0),
    "green": (re.compile(r"nearest park is about \d+ minutes|nearest (?:public )?dog (?:run|park) is [\d.]+ miles", re.I),
              lambda f: (f["parkwalk"] is not None and f["parkwalk"] >= 9) or (not f["own_dog"] and (f["dogpark_m"] or 0) >= 1600)),
    "parking": (re.compile(r"only parking named is on the street|does not mention parking|street parking is (?:very )?hard|parking is hard|"
                           r"parking is almost nonexistent|parking spaces are hard|have no car", re.I),
                lambda f: f["park_kind"] in (None, "street")),
    "home": (re.compile(r"this is a studio|apartment is small|typical apartment is small", re.I), lambda f: True),
    "value": (re.compile(r"\bnothing matches\b"), lambda f: False),
}
NOT_A_PLUS = re.compile(r"\bnearest (?:public )?dog (?:run|park) is\b|\bhard\b|\bno bars\b|\bnot much\b|\bno nightlife\b|\bdrive\b|\bsmall\b", re.I)
NUMBERED = [(re.compile(r"parents are about (\d+) minutes"), "drive", 3.0), (re.compile(r"\bpark is about (\d+) minutes?"), "parkwalk", 1.0), (re.compile(r"about \$(\d+) round trip"), "toll", 1.0),
            (re.compile(r"nearest park is about (\d+) minutes"), "parkwalk", 1.0), (re.compile(r"About (\d+) restaurants"), "rest", 2.0),
            (re.compile(r"^(\d+) restaurants"), "rest", 2.0)]
SEVERAL = re.compile(r"\bmost buildings here\b|\b(?:every|each|some) buildings? (?:shown )?here\b|\bapartments (?:here|listed in)\b|"
                     r"\btypical apartment\b|\bmany households\b", re.I)


def holds_here(sentence, f):
    """A neighborhood sentence may stand for a building only where its numbers are the building's own."""
    if SEVERAL.search(sentence) and f["hood_buildings"] > 1:
        return False
    for rx, key, tol in NUMBERED:
        m = rx.search(sentence)
        if m and (f[key] is None or abs(float(m.group(1)) - f[key]) > tol):
            return False
    return True


def building_facts(b, us, hood):
    best = us[0]
    P = RL.parking_facts(best)
    am = b.get("amenities") or {}
    return {"drive": num(mo(best, "sun", "drive_min")), "toll": toll_known(best),
            "rest": num(mo(best, "after", "restaurants_800m")), "bars": num(mo(best, "after", "bars_800m")),
            "parkwalk": num(mo(best, "wake", "park_walk_min")), "dogpark_m": num(mo(best, "wake", "dog_park_m")),
            "own_dog": bool(am.get("dog_park_or_run")), "park_kind": P["kind"], "park_included": P["included"],
            "hood_buildings": (hood.get("counts") or {}).get("buildings") or 1}


def candidates(b, us, hood):
    """[(where it stands on the page, sentence)]: the building's own text first, then its best apartment's, then its
    neighborhood's. All of it is text the builders wrote over the kept set and the guards passed."""
    best = us[0]
    host, heads = best.get("host") or {}, best.get("headlines") or {}
    pts = b.get("about_points") or []
    hp = hood.get("about_points") or []
    prose = hood.get("prose") or {}
    out = [("building about", s) for s in sentences(b.get("about_building"))]
    out += [("building point", p["text"]) for p in pts if p.get("icon") != "warning"]
    out += [("apartment line", s) for s in sentences(host.get("line"))]
    out += [(f"apartment headline ({k})", (heads.get(k) or {}).get("subhead")) for k in ("cost", "parking", "dog", "building") if (heads.get(k) or {}).get("subhead")]
    out += [("neighborhood good_for_her", prose.get("good_for_her")), ("neighborhood watch_for", prose.get("watch_for"))]
    out += [("neighborhood point", p["text"]) for p in hp]
    out += [("neighborhood about", s) for s in sentences((hood.get("host") or {}).get("intro"))]
    out += [("neighborhood scene", s) for s in sentences(prose.get("scene"))]
    out += [("building warning", p["text"]) for p in pts if p.get("icon") == "warning"]
    out += [("apartment catch", s) for s in sentences(host.get("catch"))]
    return [(w, s) for w, s in out if s and len(sentences(s)) == 1]


def pick_why_give_up(b, us, hood, scores, standing):
    """-> (why, why_source, give_up, give_up_source). `standing`: {score key: this building's percentile among the
    kept buildings}. why: the topics in descending standing, the first that has a sentence stating that strength and
    true of this building. give_up: the topics in ascending standing, the first that has a sentence stating that
    cost; else the neighborhood's catch, the building's warning, the apartment's catch."""
    f = building_facts(b, us, hood)
    cands = candidates(b, us, hood)

    def find(table, topic, own_first=True):
        rx, test = table[topic]
        if not test(f):
            return None
        for where, s in cands:
            if not rx.search(s):
                continue
            if table is GOOD and (ASKS.search(s) or NOT_A_PLUS.search(s) or where in ("building warning", "neighborhood watch_for", "apartment catch")):
                continue
            if table is BAD and (where == "neighborhood good_for_her" or where.startswith("apartment headline") or ASKS.search(s)):
                continue                              # a thing to ask is not what she gives up: it is under `confirm`
            if where.startswith("neighborhood") and not holds_here(s, f):
                continue
            return s, where
        return None
    order = sorted(SCORE_KEYS, key=lambda k: (-(standing.get(k) or 0), k))
    why = next((x for x in (find(GOOD, k) for k in order) if x), None)
    if why is None:                                   # no topic has a sentence: a smaller plus the building text states
        why = next(((s, w) for w, s in cands if GOOD_MINOR.search(s) and not ASKS.search(s)
                    and w in ("building about", "building point")), None)
    if why is None:                                   # else the building's first plain statement
        why = next(((s, w) for w, s in cands if not ASKS.search(s) and w in ("building about", "building point", "apartment line")), None)
    give = next((x for x in (find(BAD, k) for k in reversed(order)) if x and (why is None or x[0] != why[0])), None)
    if give is None:
        for want in ("neighborhood watch_for", "building warning", "apartment catch"):
            give = next(((s, w) for w, s in cands if w == want and (not w.startswith("neighborhood") or holds_here(s, f))
                         and (why is None or s != why[0])), None)
            if give:
                break
    return (voice(why[0]) if why else None, why[1] if why else None, voice(give[0]) if give else None, give[1] if give else None)


# ---- facts, day, apartments ----------------------------------------------------------------------------------------
DAY_TITLES = (("wake", "Morning walk"), ("work", "Working from home"), ("after", "After work"), ("night", "Coming home at night"),
              ("sat", "Saturday night"), ("sun", "Sunday with Mom and Dad"))


def n_things(n, one, many):
    n = int(round(n))
    return f"{n} {one if n == 1 else many}"


def day_moments(u):
    """The six moments of the building's best kept apartment: a plain statement of the measured fields, and the
    rating the page data gives the moment (strong / mixed / weak; meta.moment_thresholds of site/data.json)."""
    g = lambda a, k: mo(u, a, k)
    text = {}
    if g("wake", "park") and num(g("wake", "park_walk_min")) is not None:
        text["wake"] = f"{g('wake', 'park')} is about {n_things(g('wake', 'park_walk_min'), 'minute', 'minutes')} on foot."
    sq = num(u.get("sqft"))
    if u.get("beds") is not None:
        kind = "A studio" if int(u["beds"]) == 0 else "A separate bedroom"
        text["work"] = f"{kind}, about {int(round(sq)):,} square feet." if sq else f"{kind}; the size is not published."
    r8, b8 = num(g("after", "restaurants_800m")), num(g("after", "bars_800m"))
    if r8 is not None and b8 is not None:
        text["after"] = f"{n_things(r8, 'restaurant', 'restaurants')} and {n_things(b8, 'bar', 'bars')} within a 10-minute walk."
    text["night"] = (u.get("parking") or {}).get("summary") or "The listing does not mention parking."
    r16, b16 = num(g("sat", "restaurants_1600m")), num(g("sat", "bars_1600m"))
    if r16 is not None and b16 is not None:
        text["sat"] = f"{n_things(r16, 'restaurant', 'restaurants')} and {n_things(b16, 'bar', 'bars')} within 1 mile."
    dm, toll = num(g("sun", "drive_min")), toll_known(u)
    if dm is not None:
        t = "" if toll is None else (", with no tolls" if toll == 0 else f", about ${int(round(toll))} round trip in tolls")
        text["sun"] = f"About {n_things(dm, 'minute', 'minutes')} by car{t}."
    return [{"title": title, "text": text.get(k), "level": ((u.get("moments") or {}).get(k) or {}).get("rating")}
            for k, title in DAY_TITLES if (u.get("moments") or {}).get(k)]


def dog_fact(b, us):
    dog = (us[0].get("dog") or b.get("dogs") or {})
    pts = [p["text"] for p in b.get("about_points") or [] if re.search(r"\bdogs? (?:are|is) allowed\b|\bdogs are allowed\b", p.get("text") or "", re.I)]
    w = dog.get("weight_limit_lb")
    return {"summary": pts[0] if pts else None, "weight_limit_lb": tidy(num(w)) if num(w) is not None else None,
            "no_weight_limit": str(w).strip().lower() == "no limit", "allowed": dog.get("allowed")}


def floor_text(u):
    f = num(u.get("floor"))
    if f is None:
        return None
    basis = str(u.get("floor_basis") or "")
    return f"Floor {int(f)}" + (" (read from the apartment number)" if basis == "inferred" else "")


def available_text(u):
    a = str(u.get("available") or "")
    if a == "now":
        return "Available now"
    d = BP.day(a)
    return f"Available {d.rsplit(',', 1)[0]}" if d else None


def last_read(u):
    seen = [str(x)[:10] for x in (u.get("price_seen_at"), (u.get("live") or {}).get("checked_at")) if x]
    return max(seen) if seen else None


def apartment(u):
    c = u.get("confirm") or {}
    star = bool(c.get("asterisk"))
    offer = next((x for x in u.get("disclosures") or [] if x.get("label") == "special offer"), None)
    offer_text = (offer or {}).get("why")
    if offer_text and (BANNED.search(offer_text) or CRIME.search(offer_text)):
        offer_text = None
    return {"id": u["id"], "label": f"Apartment {u['unit']}" if not miss(u.get("unit")) else "Apartment",
            "beds": u.get("beds"), "sqft": tidy(num(u.get("sqft"))), "floor_text": floor_text(u),
            "rent": tidy(num((u.get("rent") or {}).get("listed"))), "total": tidy(num(u.get("all_in"))),
            "available_text": available_text(u), "offer": bool((u.get("rent") or {}).get("asterisk")), "offer_text": offer_text,
            "star": star, "confirm_label": (f"To confirm: {c['label']}" if star and c.get("label") else None),
            "confirm_question": c.get("question") if star else None,
            "listing_url": (u.get("links") or {}).get("listing"), "source_site": u.get("source_site"), "last_read": last_read(u)}


def contact(b):
    """{office_phone, site, ...} or null. A broker's or an individual owner's number may be one person's own line:
    it is never given (scripts/page_data_extras.py: is_private_line), whatever the page data holds."""
    ct = b.get("contact")
    if not isinstance(ct, dict) or not (ct.get("phone") or ct.get("site")):
        return None
    private = X.is_private_line(ct.get("kind"))
    phone = None if private else X._phone(ct.get("phone"))
    return {"office_phone": phone, "site": ct.get("site"), "hours": ct.get("hours") if phone else None,
            "kind": ct.get("kind"), "private": private,
            "note": X.BROKER_NOTE if private else None}


def spearman(xs, ys):
    s = pd.DataFrame({"x": xs, "y": ys}).dropna()
    return float(s["x"].rank().corr(s["y"].rank())) if len(s) >= 5 else None


EITHER_OR = [   # candidates, in the order they would be asked; each is kept only if the kept buildings trade off on it
    ("parents_or_out", "Closer to Mom and Dad, or more to do nearby?", "parents", "A shorter drive to Mom and Dad",
     "going_out", "Dinner and a drink a walk from the door"),
    ("parking_or_rent", "Easier parking, or a lower total each month?", "parking", "A garage or a space at the building",
     "value", "The lowest total with utilities and fees"),
    ("green_or_lively", "Greener, or livelier?", "green", "A park close by for the dog", "going_out", "Restaurants and bars close by"),
    ("room_or_parents", "More room at home, or closer to Mom and Dad?", "home", "More room and a better building",
     "parents", "A shorter drive to Mom and Dad"),
    ("room_or_rent", "More room at home, or a lower total each month?", "home", "More room and a better building",
     "value", "The lowest total with utilities and fees"),
    ("room_or_out", "More room at home, or more to do nearby?", "home", "More room and a better building",
     "going_out", "Restaurants and bars close by"),
    ("parents_or_rent", "Closer to Mom and Dad, or a lower total each month?", "parents", "A shorter drive to Mom and Dad",
     "value", "The lowest total with utilities and fees"),
    ("green_or_room", "Greener, or more room at home?", "green", "A park close by for the dog", "home", "More room and a better building"),
    ("parking_or_room", "Easier parking, or more room at home?", "parking", "A garage or a space at the building",
     "home", "More room and a better building"),
    ("green_or_parking", "Greener, or easier parking?", "green", "A park close by for the dog", "parking", "A garage or a space at the building"),
]
TRADE_RHO, TOP_N, TOP_OVERLAP, WEIGHT_DELTA, MAX_QUESTIONS, MAX_PER_KEY = -0.2, 5, 1, 30, 3, 2


def either_or(buildings):
    """At most MAX_QUESTIONS questions. A candidate is a real trade-off when, over the kept buildings, the Spearman
    correlation of its two scores is negative AND (it is TRADE_RHO or lower, or at most TOP_OVERLAP of the TOP_N best
    buildings on one are among the TOP_N best on the other). The strongest trade-offs (lowest correlation) are kept,
    a score key in at most MAX_PER_KEY questions so the three do not all turn on one thing.
    -> (questions, the audit of every candidate)."""
    audit = []
    for qid, question, ka, la, kb, lb in EITHER_OR:
        xs, ys = [b["scores"][ka] for b in buildings], [b["scores"][kb] for b in buildings]
        rho = spearman(xs, ys)
        top = lambda k: {b["id"] for b in sorted(buildings, key=lambda b: (-(b["scores"][k] or 0), b["id"]))[:TOP_N]}
        overlap = len(top(ka) & top(kb))
        keep = rho is not None and rho < 0 and (rho <= TRADE_RHO or overlap <= TOP_OVERLAP)
        audit.append({"id": qid, "a": ka, "b": kb, "spearman": None if rho is None else round(rho, 2),
                      "top5_shared": overlap, "trade_off": keep, "question": question, "la": la, "lb": lb})
    chosen, used = [], Counter()
    for a in sorted([a for a in audit if a["trade_off"]], key=lambda a: (a["spearman"], a["id"])):
        if len(chosen) < MAX_QUESTIONS and used[a["a"]] < MAX_PER_KEY and used[a["b"]] < MAX_PER_KEY:
            chosen.append(a)
            used.update([a["a"], a["b"]])
    order = [q[0] for q in EITHER_OR]
    chosen.sort(key=lambda a: order.index(a["id"]))
    out = [{"id": a["id"], "question": a["question"], "a": {"label": a["la"], "weight": {a["a"]: WEIGHT_DELTA}},
            "b": {"label": a["lb"], "weight": {a["b"]: WEIGHT_DELTA}},
            "basis": {"spearman": a["spearman"], "top5_shared": a["top5_shared"], "buildings": len(buildings)}} for a in chosen]
    for a in audit:
        a["kept"] = a["id"] in {q["id"] for q in out}
        for k in ("question", "la", "lb"):
            a.pop(k)
    return out, audit


def usd10(x):
    return f"${int(math.floor(float(x) / 10 + 0.5) * 10):,}"


def two(text):
    """At most the first two sentences of a guarded text."""
    return voice(" ".join(sentences(text)[:2])) or None


def figures(us):
    """An experience's figures over its kept apartments."""
    rents = [num((u.get("rent") or {}).get("listed")) for u in us]
    totals = [num(u.get("all_in")) for u in us]
    drives = [num(mo(u, "sun", "drive_min")) for u in us]
    tolls = [toll_known(u) for u in us]
    r = lambda x: None if x is None else [tidy(x[0], 2), tidy(x[1], 2)]
    return {"rent_median": tidy(median(rents)), "rent_range": r(span(rents)),
            "total_median": tidy(median(totals)), "total_range": r(span(totals)),
            "drive_min_median": tidy(median(drives)), "drive_min_range": r(span(drives)),
            "toll_round_trip_range": r(span(tolls)),
            "apartments": len(us), "buildings": len({u["building_id"] for u in us}),
            "neighborhoods": len({u["hood_id"] for u in us}), "sqft_median": tidy(median(u.get("sqft") for u in us))}


def story(y, fig):
    prose = y.get("prose") or {}
    cards = [{"kind": "promise", "title": y.get("display_label") or y.get("label"), "text": two(prose.get("promise") or y.get("tagline")), "icon": "home"}]
    for m, (kind, title) in zip(y.get("day_moments") or [], (("weekday", "A weekday"), ("saturday", "Saturday night"), ("sunday", "Sunday with Mom and Dad"))):
        cards.append({"kind": kind, "title": title, "text": two(m.get("text")), "icon": m.get("icon")})
    cost = (f"Rent is typically about {usd10(fig['rent_median'])} a month. The total with utilities and fees is typically "
            f"about {usd10(fig['total_median'])}.")
    cards.append({"kind": "cost", "title": "What it costs", "text": cost, "icon": "money"})
    if prose.get("catch"):
        cards.append({"kind": "catch", "title": "The catch", "text": two(prose["catch"]), "icon": "warning"})
    return cards


def concierge(b, source):
    """The base page (text attached) -> the data contract of docs/CONCIERGE_DESIGN.md. `source`: site/data.json, for
    the going_out percentiles over every apartment of the first page."""
    going = going_out_scores(source["units"])
    hoods_b = {h["id"]: h for h in b["neighborhoods"]}
    by_b = defaultdict(list)
    for u in sorted(b["units"], key=lambda u: (-(num((u.get("scores") or {}).get("rank")) or 0), u["id"])):
        by_b[u["building_id"]].append(u)
    blds = []
    for bd in b["buildings"]:
        us = by_b[bd["id"]]
        best = us[0]
        per = [apartment_scores(u, going) for u in us]
        scores = {k: (lambda xs: round(sum(xs) / len(xs), 3) if xs else None)([p[k] for p in per if p[k] is not None]) for k in SCORE_KEYS}
        P = RL.parking_facts(best)
        confirm, seen = [], set()
        for u in us:
            c = u.get("confirm") or {}
            if c.get("asterisk") and c.get("question") and c["question"] not in seen:
                seen.add(c["question"])
                confirm.append({"label": c.get("label"), "question": c["question"]})
        tq = [q for q, _ in Counter(q for u in us for q in u.get("tour_questions") or [] if q not in seen).most_common()]
        disc = [d for d, _ in Counter(x.get("label") for u in us for x in u.get("disclosures") or [] if x.get("label")).most_common()]
        rents = [u["rent"]["listed"] for u in us]
        totals = [u["all_in"] for u in us]
        blds.append({
            "id": bd["id"], "name": bd.get("name") or bd.get("address"), "address": bd.get("address"), "city": bd.get("city"),
            "state": bd.get("state"), "lat": round(sum(u["lat"] for u in us) / len(us), 5), "lon": round(sum(u["lon"] for u in us) / len(us), 5),
            "neighborhood_id": bd["hood_id"], "experience_id": bd.get("experience") or best.get("year"),
            "rank_score": num((best.get("scores") or {}).get("rank")),
            "why": None, "give_up": None,
            "facts": {"rent_from": tidy(min(rents)), "rent_to": tidy(max(rents)), "total_from": tidy(min(totals)), "total_to": tidy(max(totals)),
                      "drive_min": tidy(num(mo(best, "sun", "drive_min"))), "toll_round_trip": tidy(toll_known(best), 2),
                      "parking": {"summary": (best.get("parking") or {}).get("summary"), "kind": P["kind"], "fee": tidy(P["fee"], 2),
                                  "included": bool(P["included"])},
                      "dog": dog_fact(bd, us)},
            "scores": scores, "confirm": confirm, "tour_questions": tq, "disclosures": disc,
            "photos_url": (bd.get("photos") or {}).get("url"), "listing_url": (best.get("links") or {}).get("listing"),
            "contact": contact(bd), "about": voice(bd.get("about_building")),
            "points": [{"icon": p.get("icon"), "text": voice(p.get("text"))} for p in bd.get("about_points") or []],
            "day": day_moments(best), "apartments": [apartment(u) for u in us]})
    # standing of each building on each score among the kept buildings, then why / give_up
    for k in SCORE_KEYS:
        ranks = pct_rank([x["scores"][k] for x in blds])
        for x in blds:
            x.setdefault("_standing", {})[k] = None if x["scores"][k] is None else ranks[x["scores"][k]]
    src = {bd["id"]: bd for bd in b["buildings"]}
    for x in blds:
        why, ws, give, gs = pick_why_give_up(src[x["id"]], by_b[x["id"]], hoods_b[x["neighborhood_id"]], x["scores"], x.pop("_standing"))
        x.update({"why": why, "give_up": give, "why_source": ws, "give_up_source": gs})
    blds.sort(key=lambda x: (-(x["rank_score"] or 0), x["id"]))
    # neighborhoods
    n_apts = Counter(u["hood_id"] for u in b["units"])
    hoods = []
    for h in b["neighborhoods"]:
        mine = [x for x in blds if x["neighborhood_id"] == h["id"]]
        hoods.append({"id": h["id"], "name": h.get("name"), "state": h.get("state"), "experience_id": h.get("year"),
                      "lat": h.get("lat"), "lon": h.get("lon"), "drive_min": tidy(h.get("drive_min")),
                      "toll_round_trip": tidy(h.get("toll_round_trip"), 2),
                      "about": voice((h.get("host") or {}).get("intro")),
                      "points": [{"icon": p.get("icon"), "text": voice(p.get("text"))} for p in h.get("about_points") or []],
                      "parked_under": None, "also_nearby": [], "building_ids": [x["id"] for x in mine],
                      "apartments": n_apts[h["id"]], "buildings": len(mine),
                      "rent_range": [tidy(v_) for v_ in span(u["rent"]["listed"] for u in b["units"] if u["hood_id"] == h["id"])],
                      "total_range": [tidy(v_) for v_ in span(u["all_in"] for u in b["units"] if u["hood_id"] == h["id"])],
                      "good": voice((h.get("prose") or {}).get("good_for_her")), "watch": voice((h.get("prose") or {}).get("watch_for"))})
    parked = park_neighborhoods(hoods, n_apts)
    # experiences
    exps = []
    for y in b["years"]:
        us = [u for u in b["units"] if u["year"] == y["id"]]
        fig = figures(us)
        order = [i for i in y.get("hood_ids") or [] if i in hoods_b]
        exps.append({"id": y["id"], "label": y.get("display_label") or y.get("label"), "tagline": voice(y.get("tagline")),
                     "illustration_id": y["id"], "figures": fig, "story": story(y, fig),
                     "neighborhood_ids": order, "about": voice((y.get("host") or {}).get("intro")),
                     "points": [{"icon": p.get("icon"), "text": voice(p.get("text"))} for p in y.get("about_points") or []]})
    exps.sort(key=lambda e: (-e["figures"]["apartments"], e["id"]))
    questions, audit = either_or(blds)
    m = b["meta"]
    return {"meta": {"built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "rent_limit": RENT_LIMIT,
                     "counts": {"apartments": len(b["units"]), "buildings": len(blds), "neighborhoods": len(hoods), "experiences": len(exps)},
                     "tour_start": TOUR_START, "move_in_by": MOVE_IN_BY, "anchor_label": ANCHOR_LABEL,
                     "anchor": {"lat": m["anchor"]["lat"], "lon": m["anchor"]["lon"]},
                     "source": "site/data.json", "source_built_at": (m.get("concierge") or {}).get("source_built_at"),
                     "score_keys": list(SCORE_KEYS), "parked": parked, "either_or_audit": audit,
                     "notes": ["Drive times are estimates with no traffic.",
                               "Tolls are round trip at New York E-ZPass rates, weekend off-peak.",
                               "The total with utilities and fees is the rent plus required fees, pet rent, parking where its "
                               "price is published, and estimated electricity, gas and internet."]},
            "experiences": exps, "neighborhoods": hoods, "buildings": blds, "either_or": questions}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-text", action="store_true", help="reuse the _u2000 text tables on disk (the guards still run)")
    ap.add_argument("--self-check", action="store_true", help="compare the recomputation with site/data.json over all apartments")
    a = ap.parse_args(argv)
    d = json.loads(DATA.read_text(encoding="utf-8"))
    if a.self_check:
        diffs = self_check(d)
        print(f"self-check: {len(diffs)} difference(s) between the recomputation over all apartments and site/data.json")
        for x in diffs[:40]:
            print("  " + x)
        return 1 if diffs else 0
    b = base_page(d)
    print(f"kept at or under ${RENT_LIMIT:,} listed rent: {len(b['units'])} apartments, {len(b['buildings'])} buildings, "
          f"{len(b['neighborhoods'])} neighborhoods, {len(b['years'])} experiences")
    bad = build_text(b, rebuild=not a.no_text)
    if bad:
        print(f"{bad} text step(s) failed: {OUT.name} not written")
        return 1
    out = concierge(b, d)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, allow_nan=False), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {out['meta']['counts']}")
    for p in out["meta"]["parked"]:
        print(f"  parked: {p['neighborhood']} under {p['under']} ({p['km']} km{', fallback' if p['fallback'] else ''})")
    for q in out["meta"]["either_or_audit"]:
        print(f"  either/or {q['id']}: spearman {q['spearman']}, top-5 shared {q['top5_shared']} -> {'kept' if q['kept'] else 'trade-off, not among the three' if q['trade_off'] else 'no trade-off'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
