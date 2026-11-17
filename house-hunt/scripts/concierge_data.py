#!/usr/bin/env python3
"""Build site/concierge_data.json, the data of the concierge page (docs/CONCIERGE_DESIGN.md), from site/data.json.

site/data.json is read and never written. No network.

WHAT IT DOES, IN ORDER
  1 KEEP      apartments whose listed base rent AS IT NOW STANDS (rent_now: the price of the latest re-read where
              one changed it) is <= RENT_LIMIT, and the buildings, neighborhoods and experiences they leave non-empty.
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

ADDED 2026-11-17 (fields are only ever added to the contract, never renamed)
  apartments[].checked          {status, date, note}: "confirmed_today" (seen listed at the same rent on the day of the
                                latest re-read), "price_changed_today" (seen that day at a new rent; rent_before is
                                the old one) or "last_seen" (date = the last day the apartment was actually seen
                                listed: its harvest date, or an earlier re-read). From data/evidence/
                                live_check_batch_*.csv; a 'not_read' row is not a re-read (parsers.live_row_learned)
                                and only adds "it could not be read again" to the note.
  buildings[].checked_summary   {date, apartments, confirmed_today, price_changed_today, last_seen, text}
  neighborhoods[].parked_distance_km / parked_label   for a parked one-apartment neighborhood: the distance to its
                                host, and "Also nearby" within NEARBY_KM, otherwise "Also in this kind of life"
  buildings[].why_topic         the topic `why` speaks of. `why` is chosen from HER priorities first (PRIORITY, in the
                                order she raised them: parking, the dog, greenery, going out, Mom and Dad, room to
                                work from home, value); a sentence about a pool, a gym or another amenity is used
                                only when the building has nothing true and positive on any of those.

VERSION 2 (docs/CONCIERGE_DESIGN.md "Version 2"; add_version_two(), section 5), all added, nothing renamed
  questions[]                   the eight questions, in order: visits, drive (must-have), room (must-have for "A separate
                                bedroom"), saturday, dog, car, total (must-have), top_two (pick_two). Each answer has
                                filter {field, op, value} | null on buildings[].fit, weights {score key: number}, and
                                fits_alone (the buildings that pass that answer alone). Thresholds come from the kept
                                buildings: drive DRIVE_STEPS (30, 60, 90 minutes) kept only where each splits the set and
                                leaves MIN_FITS; totals the round $100 steps whose share of buildings at or under them is
                                nearest a third, a half and three quarters (today $2,000 / $2,100 / $2,200).
  SCORING (meta.matching; match() is the reference the page's JS is tested against through meta.matching_examples)
      w_k = sum of the chosen single answers' weights on k; then for each picked "matters most" answer, in the order
            picked, w_k = max(w_k, PICK_FLOOR = 10) x 2
      score = rank_score + sum_k w_k x scores[k] + CONFIRMED_BONUS (8) when an apartment was seen listed today
      must-haves are filters on fit: a building that fails one is listed apart, with the answer as its reason; a null
      fit field passes. Order: score descending, then id. Weights: visits weekly 30 / every other week 20 / monthly 10
      / now and then 0 on parents; separate bedroom 10 (studio with a desk 5) on home; walking out 20 on going_out,
      driving somewhere 10 on parking, staying in 10 on home; a park 20, a dog area 15 on green; garage 25, off-street
      15 on parking, street 5 on value; total $2,000 15 / $2,100 10 / $2,200 5 on value.
  buildings[].fit               drive_min, toll_round_trip, has_one_bedroom, has_studio, studio_only, min_total, max_total,
                                parking_kind (realtor_lines.parking_facts of the best apartment), parking_included,
                                parking_fee, garage_or_covered, off_street, dog_area_in_building (amenities.dog_park_or_run
                                as the building data states it), park_walk_min / park_name (moments.wake), dog_run_name /
                                dog_run_m, restaurants_10min / bars_10min / cafes_10min (mapped places within 800 m, the
                                "10-minute walk" of the existing text), sqft_max / sqft_studio / sqft_one_bedroom.
  buildings[].fit_chips         {answer id: at most 7 words with the building's real figure for that answer};
  buildings[].fit_misses        the same text for the answers it misses (a must-have it fails, a preference it does not
                                meet: drive over 30 / 60 / 90 minutes for weekly / every other week / monthly visits and
                                over 60 for "Close to Mom and Dad", studio only, under 10 restaurants, a park 10 minutes
                                or more away, no dog area listed, no garage, street or unnamed parking, a total above
                                the kept buildings' median for "Money left over").
  experiences[].line, buildings[].experience_line   the experience's guarded tagline (first sentence of at most 16
                                words of tagline, promise, subhead).
  buildings[].life_here         up to four moments (weekday, saturday, sunday, dog), each 1 to 3 sentences and at most 45
                                words, with places [{name, kind, walk_min, distance_mi, source_name, source_url}] and
                                sources [{name, url}]. Built from the fit fields, the named mapped places of
                                data/enriched/<sha1(addr_key)[:14]>.json and data/enriched_color/ (OpenStreetMap; the join of
                                scripts/rank.py color_table, through data/reference/building_crosswalk.csv) and the
                                confidence-'high' rows of data/reference/life_here_facts.csv (re-read on every run; absent
                                or partial is fine; other rows are counted in meta.life_here_facts). Walking minutes are
                                computed here: straight-line metres x 1.3 / 80 m a minute, as scripts/tools/places.py makes
                                park_walk_min; beyond WALK_MAX_MIN (20) the distance is given in miles. A walk or distance
                                in the web text is never used. A moment with nothing to say is left out.

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
import parsers  # noqa: E402                 unit_key(), live_row_learned(): the live-check rows as the master reads them
import build_page_data as BP  # noqa: E402   v(), shown_figures(): the page builder's own helpers
import page_data_extras as X  # noqa: E402   the text blocks, is_private_line(), ranking()
import realtor_lines as RL  # noqa: E402     parking_facts(), usd()

RENT_LIMIT = 2000                 # listed base rent; a rule for this page only (Will, 2026-11-16/17)
NEARBY_KM = 10.0                  # a parked neighborhood is "Also nearby" only within this distance of its host
SUFFIX = "_u2000"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data.json"
BASE = ROOT / "site" / "_concierge_base.json"
OUT = ROOT / "site" / "concierge_data.json"
REF = ROOT / "data" / "reference"
EVID = ROOT / "data" / "evidence"
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


def rent_now(u):
    """The listed base rent as it now stands: the price of the latest re-read where that changed it (the page data
    keeps the harvested price in rent.listed and the current one in rent.basis, kind "listed"). A 12-month or an
    after-free-months basis is not a listed price, so rent.listed stands there."""
    r = u.get("rent") or {}
    b = num(r.get("basis"))
    return b if b is not None and r.get("basis_kind") == "listed" else num(r.get("listed"))


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
    """-> the page data restricted to apartments with rent_now <= limit (None: all), every figure of an
    experience, a neighborhood and a building recomputed over those apartments. Written text is cleared: it is
    attached again from the tables built over this file. Fields that do not depend on which apartments are shown
    (traits, safety, local rules, quotes, descriptions, contacts, ratings, photos) are carried as they are."""
    d = copy.deepcopy(d)
    keep = [u for u in d["units"] if limit is None or (rent_now(u) is not None and rent_now(u) <= limit)]
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


def parked_label(km):
    """The heading a parked neighborhood is listed under at its host: "Also nearby" only where it IS near (within
    NEARBY_KM, great-circle); otherwise it shares the experience, not the place (Bloomfield under Yonkers is 29 km)."""
    return "Also nearby" if km <= NEARBY_KM else "Also in this kind of life"


def park_neighborhoods(hoods, n_apts):
    """parked_under / also_nearby (the rule of docs/CONCIERGE_DESIGN.md): a neighborhood with exactly one apartment is
    parked under the nearest neighborhood (great-circle distance) of its experience that has two or more. Where an
    experience has none with two or more, ONE neighborhood stays a stop (the most apartments; on a tie the one
    nearest the others, then the id) and the others are parked under it, so a parked neighborhood is never a host.
    -> notes for the report."""
    notes = []
    for h in hoods:
        h["parked_under"], h["also_nearby"] = None, []
        h["parked_distance_km"], h["parked_label"] = None, None
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
            km = round(haversine_km(h, host), 1)
            h["parked_under"] = host["id"]
            h["parked_distance_km"], h["parked_label"] = km, parked_label(km)
            by[host["id"]]["also_nearby"].append(h["id"])
            notes.append({"neighborhood": h["id"], "under": host["id"], "km": km, "label": h["parked_label"], "fallback": fallback})
    return notes


# ---- why / give_up: one existing, guarded sentence each ------------------------------------------------------------
ASKS = re.compile(r"\bask\b|\bconfirm|\bnot published\b|\bnot stated\b|\bnot mention|\bcheck\b|\bfew details\b|\$3,000|"
                  r"\bspecial offer\b|\bnot say\b|\bin writing\b|\bto choose from\b|\bto compare\b", re.I)
# topic -> (pattern of a sentence that states a strength, test on the building's own facts)
# HER PRIORITIES, in the order she raised them most often (coordinator, 2026-11-17): easy parking (she drives), the
# dog (under 25 lb: a dog area, a park close by), greenery, going out, closer to Mom and Dad, room to work from home,
# value for the rent. `why` is chosen among THESE topics first: the one this building stands highest on among the kept
# buildings that has a sentence stating that strength and true of this building (ties go to the earlier priority).
PRIORITY = ("parking", "dog", "green", "going_out", "parents", "work", "value")
TOPIC_SCORE = {"parking": "parking", "dog": "green", "green": "green", "going_out": "going_out", "parents": "parents",
               "work": "home", "value": "value"}        # the building score each topic's standing is read from
GOOD = {
    "parking": (re.compile(r"included in the rent|rent includes a space|free off-street|park free|parking (?:in the open lot )?is free|not pay extra|"
                           r"garage (?:among|for your car)|own garage|only building[^.]*with a garage|covered parking", re.I),
                lambda f: f["park_kind"] in ("garage", "covered") or f["park_included"]),
    "dog": (re.compile(r"own dog (?:park|run|area)|dog (?:park|run|area) on the property|take the dog out|dog (?:park|run) is (?:close|a short walk)|"
                       r"dog (?:park|run) is 0\.[0-5] miles", re.I),
            lambda f: f["own_dog"] or (f["dogpark_m"] is not None and f["dogpark_m"] <= 800)),
    "green": (re.compile(r"minutes (?:away )?on foot|minutes to [A-Z]|could walk to [A-Z][^.]* in about|walk to [A-Z][^.]* takes about|"
                         r"closest to a park|waterfront|riverfront", re.I),
              lambda f: f["parkwalk"] is not None and f["parkwalk"] <= 5),
    "going_out": (re.compile(r"restaurants (?:are )?within a 10-minute walk|walk to dinner|eating out|plenty to eat|choice of restaurants", re.I),
                  lambda f: (f["rest"] or 0) >= 10),
    "parents": (re.compile(r"parents are (?:about \d+ minutes|very close|close)|close to your parents|drive to your parents has no tolls", re.I),
                lambda f: f["drive"] is not None and f["drive"] <= 30),
    # room to work from home is about the apartment (a separate bedroom, a large apartment), or a sentence that says so
    # itself; a bare "lounge or coworking room" is an amenity
    "work": (re.compile(r"large apartment|1-bedroom|separate bedroom|work from home|room for a (?:proper )?desk|work can stay out", re.I), lambda f: True),
    "value": (re.compile(r"well under your limit|room in your budget|price is low|prices are low|lower-priced|costs less|far below your limit|"
                         r"leaves room", re.I), lambda f: True),
}
# Not her priorities: an amenity the building text states as a plus. Used for `why` only when no priority topic has a
# sentence that is true and positive for this building (test_concierge_data.py holds this).
AMENITY = re.compile(r"\bpools?\b|\bgym\b|fitness|washer and dryer|laundry (?:is )?in the apartment|concierge|front desk|doorman|package room|roof ?(?:top|deck)|"
                     r"\blounge\b|coworking|garage parking costs|(?:train|subway|PATH|light rail) station is 0\.[0-4] miles|supermarket[^.]* is 0\.[0-3] miles", re.I)
GOOD_MINOR = AMENITY                                    # the name the first version used
# A sentence that is ONLY about such an amenity never stands for a priority topic, whatever else it matches ("The
# building has a pool, and laundry is in the apartment" is not about room to work). A coworking room is: she works from home.
AMENITY_ONLY = re.compile(r"\bpools?\b|\bgym\b|fitness|washer and dryer|laundry (?:is )?in the apartment|concierge|front desk|doorman|package room|"
                          r"roof ?(?:top|deck)", re.I)
INITIAL_END = re.compile(r"\b[A-Z]\.$")                 # "... on foot to Margaret I." is half a sentence, cut at an initial
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
    return [(w, s) for w, s in out if s and len(sentences(s)) == 1 and not INITIAL_END.search(s.strip())]


def pick_why_give_up(b, us, hood, scores, standing):
    """-> (why, why_source, give_up, give_up_source, why_topic). `standing`: {score key: this building's percentile
    among the kept buildings}. why: HER priority topics (PRIORITY) in descending standing, the first that has a
    sentence stating that strength and true of this building; only when none has, an amenity sentence of the
    building's own text (why_topic "amenity"), else its first plain statement ("other"). give_up: the scores in
    ascending standing, the first that has a sentence stating that cost; else the neighborhood's catch, the
    building's warning, the apartment's catch."""
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
    topic = None
    for k in priority_order(standing):
        why = find(GOOD, k)
        if why and not AMENITY_ONLY.search(why[0]):                      # a priority sentence, not an amenity in passing
            topic = k
            break
    else:
        why = None
    if why is None:                                   # nothing true and positive on her priorities: an amenity the building text states
        why = next(((s, w) for w, s in cands if AMENITY.search(s) and not ASKS.search(s) and not NOT_A_PLUS.search(s)
                    and w in ("building about", "building point", "apartment headline (building)")), None)
        topic = "amenity" if why else None
    if why is None:                                   # else the building's first plain statement
        why = next(((s, w) for w, s in cands if not ASKS.search(s) and w in ("building about", "building point", "apartment line")), None)
        topic = "other" if why else None
    give = next((x for x in (find(BAD, k) for k in reversed(order)) if x and (why is None or x[0] != why[0])), None)
    if give is None:
        for want in ("neighborhood watch_for", "building warning", "apartment catch"):
            give = next(((s, w) for w, s in cands if w == want and (not w.startswith("neighborhood") or holds_here(s, f))
                         and (why is None or s != why[0])), None)
            if give:
                break
    return (voice(why[0]) if why else None, why[1] if why else None, voice(give[0]) if give else None, give[1] if give else None, topic)


def priority_order(standing):
    """PRIORITY in the order `why` tries them: the highest standing among the kept buildings first, ties (and the two
    topics that share the dog-and-green score) in the order she raised them."""
    return sorted(PRIORITY, key=lambda k: (-(standing.get(TOPIC_SCORE[k]) or 0), PRIORITY.index(k)))


def priority_sentences(b, us, hood):
    """[(topic, sentence, where)]: every sentence about one of her priorities that states a strength and is true of
    this building. Empty only where the building has nothing true and positive on any of them."""
    f = building_facts(b, us, hood)
    out = []
    for k in PRIORITY:
        rx, test = GOOD[k]
        if not test(f):
            continue
        for where, s in candidates(b, us, hood):
            if not rx.search(s) or ASKS.search(s) or NOT_A_PLUS.search(s) or where in ("building warning", "neighborhood watch_for", "apartment catch"):
                continue
            if where.startswith("neighborhood") and not holds_here(s, f):
                continue
            if AMENITY_ONLY.search(s):
                continue
            out.append((k, s, where))
    return out


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
    """'Floor 5', 'Floor 4 (read from the apartment number)'. Owner, 2026-11-17: an apartment the floor-and-elevator rule
    settles on floor 2 without an elevator says so in plain words, 'Floor 2, a single flight up, no elevator needed'
    (elevator.words from parsers.walkup_words: 'no elevator' only where a page or record says there is none)."""
    f = num(u.get("floor"))
    if f is None:
        return None
    basis = str(u.get("floor_basis") or "")
    words = (u.get("elevator") or {}).get("words") if (u.get("elevator") or {}).get("walkup_floor_2") is True else None
    read = " (read from the apartment number)" if basis == "inferred" else ""
    if words:
        return f"Floor {int(f)}, {words[0].lower()}{words[1:]}{read}"
    return f"Floor {int(f)}" + read


def available_text(u):
    a = str(u.get("available") or "")
    if a == "now":
        return "Available now"
    d = BP.day(a)
    return f"Available {d.rsplit(',', 1)[0]}" if d else None


def last_read(u):
    seen = [str(x)[:10] for x in (u.get("price_seen_at"), (u.get("live") or {}).get("checked_at")) if x]
    return max(seen) if seen else None


# ---- checked: what the live-check rows say about each apartment ------------------------------------------------------
def day_words(iso):
    """'2026-11-17' -> 'November 17'."""
    d = datetime.strptime(str(iso)[:10], "%Y-%m-%d")
    return f"{d.strftime('%B')} {d.day}"


def live_rows():
    """({(building id, unit key): [rows, oldest first]}, the day of the latest re-read) from data/evidence/
    live_check_batch_*.csv, matched to apartments the way scripts/build_master.py matches them (building through
    data/reference/building_crosswalk.csv, apartment through parsers.unit_key)."""
    import glob
    xw = pd.read_csv(REF / "building_crosswalk.csv", dtype=str, keep_default_na=False)
    a2b = dict(zip(xw.addr_key, xw.building_id))
    rows, day = defaultdict(list), ""
    for f in sorted(glob.glob(str(EVID / "live_check_batch_*.csv"))):
        for r in pd.read_csv(f, dtype=str, keep_default_na=False).to_dict("records"):
            b = a2b.get(r.get("addr_key"))
            day = max(day, str(r.get("checked_at") or "")[:10])
            if b and parsers.unit_label_key(r.get("unit")):
                rows[(b, parsers.unit_key(r["unit"]))].append(r)
    for k in rows:
        rows[k].sort(key=lambda r: str(r.get("checked_at") or ""))
    return rows, day


def checked(u, rows, day):
    """{status, date, note, rent_before}. `rows`: this apartment's live-check rows, oldest first; `day`: the day of
    the latest re-read ("today"). A 'not_read' row is not a re-read: it changes neither status nor date."""
    learned = parsers.latest_live_row(rows)
    st = str((learned or {}).get("status") or "")
    at = str((learned or {}).get("checked_at") or "")[:10]
    tried = max([str(r.get("checked_at") or "")[:10] for r in rows if not parsers.live_row_learned(r.get("status"))], default="")
    rent, old = rent_now(u), num((u.get("rent") or {}).get("listed"))
    by_label = "not by apartment number" in str((learned or {}).get("notes") or "")
    if st == "live" and at == day:
        note = f"Still listed at the same rent on {day_words(day)}."
        if by_label:
            note += " The broker's page gives the street, the size and the rent, not the apartment number."
        return {"status": "confirmed_today", "date": day, "note": note, "rent_before": None}
    if st == "changed" and at == day:
        if rent is not None and old is not None and rent != old:
            note = f"The rent is now {RL.usd(rent)}, {'down' if rent < old else 'up'} from {RL.usd(old)}, as read on {day_words(day)}."
        else:
            note = f"Listed at a new rent when it was read on {day_words(day)}."
        return {"status": "price_changed_today", "date": day, "note": note, "rent_before": tidy(old) if old != rent else None}
    seen = [str(u.get("price_seen_at") or "")[:10]] + ([at] if st in ("live", "changed") else [])
    seen = max([x for x in seen if x], default=None)
    note = f"Last seen listed on {day_words(seen)}." if seen else "The day it was last seen listed is not recorded."
    if tried and (not seen or tried > seen):
        note += f" It could not be read again on {day_words(tried)}."
    return {"status": "last_seen", "date": seen, "note": note, "rent_before": None}


def checked_summary(apts, day):
    """A building's line: how many of its apartments were seen listed on the day of the latest re-read."""
    n = Counter(a["checked"]["status"] for a in apts)
    seen = n["confirmed_today"] + n["price_changed_today"]
    if seen:
        text = f"Confirmed {seen} of {len(apts)} on {day_words(day)}" + (f", {n['price_changed_today']} at a new rent" if n["price_changed_today"] else "")
    else:
        last = max([a["checked"]["date"] for a in apts if a["checked"]["date"]], default=None)
        text = f"Last seen listed on {day_words(last)}" if last else "Not seen listed again since it was collected"
    return {"date": day, "apartments": len(apts), "confirmed_today": n["confirmed_today"], "price_changed_today": n["price_changed_today"],
            "last_seen": n["last_seen"], "text": text}


def apartment(u):
    c = u.get("confirm") or {}
    star = bool(c.get("asterisk"))
    offer = next((x for x in u.get("disclosures") or [] if x.get("label") == "special offer"), None)
    offer_text = (offer or {}).get("why")
    if offer_text and (BANNED.search(offer_text) or CRIME.search(offer_text)):
        offer_text = None
    return {"id": u["id"], "label": f"Apartment {u['unit']}" if not miss(u.get("unit")) else "Apartment",
            "beds": u.get("beds"), "sqft": tidy(num(u.get("sqft"))), "floor_text": floor_text(u),
            "rent": tidy(rent_now(u)), "total": tidy(num(u.get("all_in"))),
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
    rents = [rent_now(u) for u in us]
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
    live, check_day = live_rows()
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
        # A disclosure is shown as what to ask (its question), not as its internal label: "something else to know" told
        # her nothing (2026-11-17). The label is kept only where a disclosure carries no question.
        disc = [d for d, _ in Counter((x.get("question") or x.get("label")) for u in us for x in u.get("disclosures") or []
                                      if (x.get("question") or x.get("label"))).most_common()]
        rents = [rent_now(u) for u in us]
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
            "day": day_moments(best),
            "apartments": [dict(apartment(u), checked=checked(u, live.get((bd["id"], parsers.unit_key(u.get("unit"))), []), check_day)) for u in us]})
        blds[-1]["checked_summary"] = checked_summary(blds[-1]["apartments"], check_day)
    # standing of each building on each score among the kept buildings, then why / give_up
    for k in SCORE_KEYS:
        ranks = pct_rank([x["scores"][k] for x in blds])
        for x in blds:
            x.setdefault("_standing", {})[k] = None if x["scores"][k] is None else ranks[x["scores"][k]]
    src = {bd["id"]: bd for bd in b["buildings"]}
    for x in blds:
        why, ws, give, gs, topic = pick_why_give_up(src[x["id"]], by_b[x["id"]], hoods_b[x["neighborhood_id"]], x["scores"], x.pop("_standing"))
        x.update({"why": why, "give_up": give, "why_source": ws, "give_up_source": gs, "why_topic": topic})
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
                      "rent_range": [tidy(v_) for v_ in span(rent_now(u) for u in b["units"] if u["hood_id"] == h["id"])],
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
                     "checked_day": check_day, "nearby_km": NEARBY_KM,
                     "checked_counts": dict(Counter(a["checked"]["status"] for x in blds for a in x["apartments"])),
                     "anchor": {"lat": m["anchor"]["lat"], "lon": m["anchor"]["lon"]},
                     "source": "site/data.json", "source_built_at": (m.get("concierge") or {}).get("source_built_at"),
                     "score_keys": list(SCORE_KEYS), "parked": parked, "either_or_audit": audit,
                     "notes": ["Drive times are estimates with no traffic.",
                               "Tolls are round trip at New York E-ZPass rates, weekend off-peak.",
                               "The total with utilities and fees is the rent plus required fees, pet rent, parking where its "
                               "price is published, and estimated electricity, gas and internet."]},
            "experiences": exps, "neighborhoods": hoods, "buildings": blds, "either_or": questions}


# ---------------------------------------------------------------------------------------------------------------------
# 5. Version 2: questions, fit, fit_chips / fit_misses, experience_line, life_here (docs/CONCIERGE_DESIGN.md "Version 2")
# ---------------------------------------------------------------------------------------------------------------------
CONFIRMED_BONUS = 8                 # as the version-1 page: a building with an apartment seen listed today goes ahead
PICK_FLOOR = 10                     # a "matters most" key counts at least this much before it is doubled
DRIVE_STEPS = (30, 60, 90)          # minutes each way; each must split the kept buildings (checked when built)
TOTAL_TARGETS = (1 / 3, 1 / 2, 3 / 4)   # the $100 steps whose share of buildings is nearest these shares
MIN_FITS = 3                        # every answer that screens must leave at least this many buildings alone
WALK_DETOUR, WALK_M_PER_MIN = 1.3, 80.0   # scripts/tools/places.py _walk_min: straight line x 1.3 / 80 m a minute
WALK_MAX_MIN = 20                   # a place farther than this on foot is given in miles
NEAR_MIN = 15                       # a café, bar, bakery or library is named only within this walk
DOG_RUN_MAX_M, VET_MAX_M = 3219, 4828     # 2 miles, 3 miles straight line
LIFE_MAX_WORDS, LIFE_MAX_SENTENCES, CHIP_MAX_WORDS = 45, 3, 7
LIFE_FACTS = REF / "life_here_facts.csv"
ENRICHED, COLOR = ROOT / "data" / "enriched", ROOT / "data" / "enriched_color"
OSM = "OpenStreetMap"
MOMENTS = (("weekday", "A weekday"), ("saturday", "Saturday night"), ("sunday", "Sunday with Mom and Dad"), ("dog", "The dog's walk"))
HYPE = re.compile(r"\b(stunning|nestled|boasts?|vibrant|bustling|oasis|hidden gem|luxur\w+|breathtaking|must-see|coveted|sought-after)\b", re.I)


def half_up(x):
    return int(math.floor(float(x) + 0.5))


def walk_min_of(m):
    """Straight-line metres -> walking minutes, exactly as the existing walk minutes (park_walk_min) are made."""
    return None if m is None else round(float(m) * WALK_DETOUR / WALK_M_PER_MIN, 1)


def miles_of(m):
    return None if m is None else round(float(m) / 1609.344, 1)


def clean_name(s):
    s = re.sub(r"\s*[—–]\s*", " - ", str(s or "")).strip()
    return s or None


def name_ok(s):
    return bool(s) and not (BANNED.search(s) or CRIME.search(s) or HYPE.search(s) or "?" in s) and name_key(s) not in BLOCKED


def a_walk(n):
    n = max(1, half_up(n))
    return ("an " if n in (8, 11, 18) or 80 <= n < 90 else "a ") + f"{n}-minute walk"


def minutes(n):
    n = max(1, half_up(n))
    return f"{n} minute" + ("" if n == 1 else "s")


def words(s):
    return len(str(s or "").split())


# ---- the questions -----------------------------------------------------------------------------------------------
def _total_steps(totals, n):
    lo, hi = int(math.ceil(min(totals) / 100) * 100), int(math.floor(max(totals) / 100) * 100)
    counts = {s: sum(1 for t in totals if t <= s) for s in range(lo, hi + 1, 100)}
    ok = {s: c for s, c in counts.items() if MIN_FITS <= c < n}
    out = []
    for share in TOTAL_TARGETS:
        best = min((s for s in ok if s not in out), key=lambda s: (abs(ok[s] - share * n), s), default=None)
        if best is not None:
            out.append(best)
    return sorted(set(out))


def build_questions(blds):
    """The eight questions of the version-2 flow. Thresholds come from the kept buildings: the drive steps are
    DRIVE_STEPS, kept only where they split the set; the totals are the round $100 steps whose share of buildings at
    or under them is nearest a third, a half and three quarters. fits_alone is added after (count_fits)."""
    n = len(blds)
    drives = [x["fit"]["drive_min"] for x in blds if x["fit"]["drive_min"] is not None]
    totals = [x["fit"]["min_total"] for x in blds if x["fit"]["min_total"] is not None]
    dsteps = [s for s in DRIVE_STEPS if MIN_FITS <= sum(1 for d in drives if d <= s) < n]
    dlabel = {30: ("Up to 30 minutes", "Close enough for a weeknight dinner"),
              60: ("Up to an hour", "An easy Sunday drive"),
              90: ("Up to 1½ hours", "A real trip, but doable")}
    tsteps = _total_steps(totals, n)
    tsub = ["The most left over each month", "A little more room to choose", "The widest choice"]
    tweight = [15, 10, 5]
    A = lambda i, label, sub, filt=None, w=None, **kw: dict({"id": i, "label": label, "sublabel": sub, "filter": filt, "weights": w or {}}, **kw)
    return [
        {"id": "visits", "text": "How often do you want to see Mom and Dad?", "help": "This sets how much the drive counts.",
         "kind": "single", "must_have": False, "answers": [
             A("visits_weekly", "Every week", "Most Sundays, at least", None, {"parents": 30}, visits_per_month=4),
             A("visits_fortnightly", "Every other week", "Twice a month or so", None, {"parents": 20}, visits_per_month=2),
             A("visits_monthly", "About once a month", "A visit every few weeks", None, {"parents": 10}, visits_per_month=1),
             A("visits_rarely", "Now and then", "Holidays and birthdays", None, {}, visits_per_month=None)]},
        {"id": "drive", "text": "What is the longest drive you would make for a visit?",
         "help": "Each way, with no traffic.", "kind": "single", "must_have": True, "answers":
             [A(f"drive_{s}", *dlabel.get(s, (f"Up to {s} minutes", "")), {"field": "drive_min", "op": "<=", "value": s}) for s in dsteps]
             + [A("drive_any", "Any of them", "Distance is not the deciding thing")]},
        {"id": "room", "text": "When you work from home, what do you need?", "help": None, "kind": "single", "must_have": True,
         "answers": [
             A("room_bedroom", "A separate bedroom", "A door to close at the end of the day",
               {"field": "has_one_bedroom", "op": "==", "value": True}, {"home": 10}),
             A("room_desk", "Studio with room for a desk", "One room, set up well", None, {"home": 5}),
             A("room_either", "Either works", "Any good space will do")]},
        {"id": "saturday", "text": "What does a good Saturday night look like?", "help": None, "kind": "single", "must_have": False,
         "answers": [
             A("sat_walk", "Walking out to dinner", "Restaurants and bars a short walk away", None, {"going_out": 20}),
             A("sat_drive", "Driving somewhere fun", "Easy parking matters more than the corner bar", None, {"parking": 10}),
             A("sat_stay", "Staying in", "A comfortable home matters most", None, {"home": 10})]},
        {"id": "dog", "text": "What does the dog's daily walk look like?", "help": None, "kind": "single", "must_have": False,
         "answers": [
             A("dog_park", "A park to walk to", "Green space a few minutes from the door", None, {"green": 20}),
             A("dog_area", "A dog area at the building", "Quick trips out without going far", None, {"green": 15}),
             A("dog_either", "Either is fine", "Any good walk will do")]},
        {"id": "car", "text": "Where will your car sleep at night?", "help": None, "kind": "single", "must_have": False,
         "answers": [
             A("car_garage", "A garage, even if it costs", "Covered and close, worth paying for", None, {"parking": 25}),
             A("car_offstreet", "Any spot off the street", "A lot or a driveway space is fine", None, {"parking": 15}),
             A("car_street", "On the street is fine", "Keep the money instead", None, {"value": 5})]},
        {"id": "total", "text": "What monthly total feels right to you, with utilities and fees?",
         "help": "Rent plus electricity, gas, internet, pet rent and required fees.", "kind": "single", "must_have": True,
         "answers": [A(f"total_{s}", f"Up to ${s:,}", tsub[i] if i < len(tsub) else "", {"field": "min_total", "op": "<=", "value": s},
                       {"value": tweight[i] if i < len(tweight) else 0}) for i, s in enumerate(tsteps)]
                    + [A("total_any", "Any of them", "Price is not the deciding thing")]},
        {"id": "top_two", "text": "Which two matter most to you?", "help": "Pick two.", "kind": "pick_two", "must_have": False,
         "weights_mode": "double", "answers": [
             A("pick_parents", "Close to Mom and Dad", "Shorter drives for visits", None, {"parents": 2}),
             A("pick_room", "Room to work", "A separate bedroom, or more space", None, {"home": 2}),
             A("pick_going_out", "Going out nearby", "Dinner and drinks on foot", None, {"going_out": 2}),
             A("pick_green", "Green space for the dog", "A park close by", None, {"green": 2}),
             A("pick_parking", "Easy parking", "A space at the building", None, {"parking": 2}),
             A("pick_money", "Money left over", "The lowest total each month", None, {"value": 2})]},
    ]


def passes(fit, f):
    """A must-have filter on a building's fit fields. An unknown field (null) passes: a building misses a must-have
    only on a stated fact, as every gate of this project works (CLAUDE.md rule 10)."""
    x = fit.get(f["field"])
    if x is None:
        return True
    return {"<=": lambda: x <= f["value"], ">=": lambda: x >= f["value"], "==": lambda: x == f["value"]}[f["op"]]()


def count_fits(questions, blds):
    for q in questions:
        for a in q["answers"]:
            a["fits_alone"] = sum(1 for x in blds if a["filter"] is None or passes(x["fit"], a["filter"]))


def match(buildings, answers, questions):
    """The reference implementation of meta.matching (the page's JS must give the same order).
    answers: {question id: answer id} and, for the pick_two question, {question id: [answer id, answer id]}; a
    question left out was skipped. -> {"fits": [ids, best first], "doesnt_fit": [{"id", "reasons": [answer ids]}],
    "scores": {id: score}}. Ties go to the lower id."""
    Q = {q["id"]: q for q in questions}
    w = defaultdict(float)
    filters = []
    for qid, aid in answers.items():
        q = Q[qid]
        if q["kind"] == "pick_two":
            continue
        a = next(a for a in q["answers"] if a["id"] == aid)
        for k, x in a["weights"].items():
            w[k] += x
        if a["filter"]:
            filters.append((aid, a["filter"]))
    for qid, aids in answers.items():
        if Q[qid]["kind"] != "pick_two":
            continue
        for aid in list(aids)[:2]:                    # in the order she picked them
            a = next(a for a in Q[qid]["answers"] if a["id"] == aid)
            for k, m in a["weights"].items():
                w[k] = max(w[k], PICK_FLOOR) * m
    scores = {}
    for b in buildings:
        s = num(b.get("rank_score")) or 0.0
        s += sum(x * (num((b.get("scores") or {}).get(k)) or 0.0) for k, x in w.items())
        if any((a.get("checked") or {}).get("status") in ("confirmed_today", "price_changed_today") for a in b.get("apartments") or []):
            s += CONFIRMED_BONUS
        scores[b["id"]] = round(s, 6)
    order = sorted(buildings, key=lambda b: (-scores[b["id"]], b["id"]))
    fits, out = [], []
    for b in order:
        miss_ = [aid for aid, f in filters if not passes(b["fit"], f)]
        (out.append({"id": b["id"], "reasons": miss_}) if miss_ else fits.append(b["id"]))
    return {"fits": fits, "doesnt_fit": out, "scores": scores}


MATCHING = {
    "formula": "score = rank_score + sum over score keys k of (w_k x scores[k]) + CONFIRMED_BONUS when any apartment's "
               "checked.status is confirmed_today or price_changed_today",
    "weights": "w_k starts at 0. For every answered single question, add the chosen answer's weights. Then, for each of "
               "the (at most two) answers picked in the pick_two question, in the order picked, for each key k in its "
               "weights: w_k = max(w_k, pick_floor) x that weight (2: doubled), so a key that matters most counts at "
               "least 2 x pick_floor. A skipped question adds nothing.",
    "must_haves": "For every answered question whose chosen answer has a filter (only must_have questions have one) {field, op, value}: a "
                  "building passes when fit[field] op value holds (op is <=, >= or ==). A null fit field passes. A "
                  "building that fails any goes to 'Doesn't fit what you said', with the failed answer ids as "
                  "reasons (its fit_misses text for each); nothing is deleted.",
    "order": "Fitting buildings by score, highest first; equal scores by id, ascending. The non-fitting group is in "
             "the same order.",
    "confirmed_bonus": CONFIRMED_BONUS, "pick_floor": PICK_FLOOR, "unknown_passes": True,
    "reference": "scripts/concierge_data.py: match(buildings, answers, questions)",
}


NAMES = ("weekly visits, close by, out on foot", "a separate bedroom within an hour, garage", "rarely visits, money first",
         "every other week, within 1½ hours, going out and parking")


def matching_examples(blds, questions):
    sets = [
        {"visits": "visits_weekly", "drive": "drive_30", "room": "room_either", "saturday": "sat_walk", "dog": "dog_park",
         "car": "car_offstreet", "total": "total_2200", "top_two": ["pick_parents", "pick_going_out"]},
        {"visits": "visits_monthly", "drive": "drive_60", "room": "room_bedroom", "saturday": "sat_stay", "dog": "dog_area",
         "car": "car_garage", "total": "total_any", "top_two": ["pick_room", "pick_parking"]},
        {"visits": "visits_rarely", "drive": "drive_any", "room": "room_desk", "saturday": "sat_drive", "dog": "dog_either",
         "car": "car_street", "total": "total_2000", "top_two": ["pick_money", "pick_green"]},
        {"visits": "visits_fortnightly", "drive": "drive_90", "saturday": "sat_walk", "car": "car_garage",
         "total": "total_2100", "top_two": ["pick_going_out", "pick_parking"]},
    ]
    ids = {a["id"] for q in questions for a in q["answers"]}
    out = []
    for s in sets:
        s = {k: (v_ if isinstance(v_, list) else v_) for k, v_ in s.items()
             if (all(x in ids for x in v_) if isinstance(v_, list) else v_ in ids)}
        r = match(blds, s, questions)
        out.append({"name": NAMES[len(out)], "answers": s, "expected_fits": r["fits"], "expected_doesnt_fit": [x["id"] for x in r["doesnt_fit"]],
                    "order": r["fits"], "failing": [x["id"] for x in r["doesnt_fit"]],
                    "expected_scores": {i: round(x, 3) for i, x in sorted(r["scores"].items())}})
    return out


# ---- fit ---------------------------------------------------------------------------------------------------------
def fit_fields(x, src_b, us):
    """The fields filters and chips read, from structured data only. null where the data does not say."""
    best = us[0]
    P = RL.parking_facts(best)
    kind = P["kind"] or None
    beds = [int(u["beds"]) for u in us if u.get("beds") is not None]
    w = (best.get("moments") or {}).get("wake") or {}
    a = (best.get("moments") or {}).get("after") or {}
    am = src_b.get("amenities") or {}
    dog_area = am.get("dog_park_or_run")
    return {"drive_min": x["facts"]["drive_min"], "toll_round_trip": x["facts"]["toll_round_trip"],
            "has_one_bedroom": any(b_ >= 1 for b_ in beds) if beds else None,
            "has_studio": any(b_ == 0 for b_ in beds) if beds else None,
            "studio_only": (all(b_ == 0 for b_ in beds) if beds else None),
            "min_total": x["facts"]["total_from"], "max_total": x["facts"]["total_to"],
            "parking_kind": kind, "parking_included": bool(P["included"]) if kind else None,
            "parking_fee": tidy(P["fee"], 2) if kind else None,
            "garage_or_covered": (kind in ("garage", "covered")) if kind else None,
            "off_street": (kind != "street") if kind else None,
            "dog_area_in_building": bool(dog_area) if dog_area is not None else None,
            "park_walk_min": tidy(num(w.get("park_walk_min"))), "park_name": w.get("park") or None,
            "dog_run_name": w.get("dog_park") or None, "dog_run_m": tidy(num(w.get("dog_park_m")), 0),
            "restaurants_10min": tidy(num(a.get("restaurants_800m")), 0), "bars_10min": tidy(num(a.get("bars_800m")), 0),
            "cafes_10min": tidy(num(a.get("cafes_800m")), 0),
            "sqft_max": tidy(max([num(u.get("sqft")) for u in us if num(u.get("sqft")) is not None], default=None) or None, 0),
            "sqft_studio": tidy(max([num(u.get("sqft")) for u in us if u.get("beds") == 0 and num(u.get("sqft")) is not None], default=None) or None, 0),
            "sqft_one_bedroom": tidy(max([num(u.get("sqft")) for u in us if (u.get("beds") or 0) >= 1 and num(u.get("sqft")) is not None], default=None) or None, 0)}


# ---- fit_chips / fit_misses --------------------------------------------------------------------------------------
def _drive_chip(f):
    return None if f["drive_min"] is None else f"About {half_up(f['drive_min'])} minutes to Mom and Dad"


def _rest_chip(f):
    r = f["restaurants_10min"]
    if r is None:
        return None
    r = int(r)
    if r == 0:
        return "No restaurants within a 10-minute walk"
    return f"{'About ' if r >= 10 else ''}{r} restaurant{'s' if r != 1 else ''} within a 10-minute walk"


def _park_chip(f):
    if f["park_walk_min"] is None:
        return None
    t = f"{f['park_name']}, {minutes(f['park_walk_min'])} on foot" if f["park_name"] else None
    return t if t and words(t) <= CHIP_MAX_WORDS else f"A park {minutes(f['park_walk_min'])} on foot"


def _parking_chip(f):
    k = f["parking_kind"]
    if k is None:
        return "Parking not named in the listing"
    base = {"garage": "Garage parking", "covered": "Covered parking", "lot": "A parking lot", "off_street": "Off-street parking",
            "street": "Street parking only"}.get(k, "Parking named in the listing")
    if k == "street":
        return base
    if f["parking_included"]:
        return f"{base}, included in the rent"
    if f["parking_fee"]:
        return f"{base}, ${half_up(f['parking_fee'])} a month"
    return base


def _room_chip(f):
    if f["has_one_bedroom"]:
        return f"Separate bedroom, about {int(f['sqft_one_bedroom']):,} square feet" if f["sqft_one_bedroom"] else "A separate bedroom"
    if f["has_one_bedroom"] is False:
        return f"Studio only, about {int(f['sqft_studio']):,} square feet" if f["sqft_studio"] else "Studio only"
    return None


def _total_chip(f):
    if f["min_total"] is None:
        return None
    lo = f"${half_up(f['min_total']):,}"
    return f"Total about {lo} a month" if f["max_total"] == f["min_total"] else f"Total from about {lo} a month"


def chips_for(x, questions, med_total):
    """{answer id: chip} and {answer id: miss}. A chip states the building's real figure for that answer; a miss is
    the same kind of statement where the building misses the answer (a must-have it fails, or a preference it does
    not meet). Answers that ask for nothing ("Either works", "Any of them", "Now and then") carry neither."""
    f = x["fit"]
    chips, misses = {}, {}
    drive, rest, park, parking, room, total = _drive_chip(f), _rest_chip(f), _park_chip(f), _parking_chip(f), _room_chip(f), _total_chip(f)
    miss_drive = {"visits_weekly": 30, "visits_fortnightly": 60, "visits_monthly": 90, "pick_parents": 60}
    for q in questions:
        for a in q["answers"]:
            i, c, m = a["id"], None, False
            if i in miss_drive or (i.startswith("drive_") and a["filter"]):
                c = drive
                lim = miss_drive.get(i) or (a["filter"] or {}).get("value")
                m = lim is not None and f["drive_min"] is not None and f["drive_min"] > lim
            elif i in ("room_bedroom", "pick_room"):
                c, m = room, f["has_one_bedroom"] is False
            elif i == "room_desk":
                c = room if f["has_one_bedroom"] is False else (room if f["has_one_bedroom"] else None)
                if f["has_one_bedroom"] is False and not f["sqft_studio"]:
                    c = "A studio; size not published"
            elif i in ("sat_walk", "pick_going_out"):
                c, m = rest, f["restaurants_10min"] is not None and f["restaurants_10min"] < 10
            elif i == "sat_drive":
                c, m = parking, f["parking_kind"] == "street"
            elif i == "sat_stay":
                c = (f"Up to about {int(f['sqft_max']):,} square feet" if f["sqft_max"] else None)
            elif i in ("dog_park", "pick_green"):
                c = park
                m = f["park_walk_min"] is not None and half_up(f["park_walk_min"]) >= 10
                if m:
                    c = f"Nearest park about {minutes(f['park_walk_min'])} on foot"
            elif i == "dog_area":
                c = "A dog area at the building" if f["dog_area_in_building"] else "No dog area listed at the building"
                m = not f["dog_area_in_building"]
            elif i in ("car_garage", "car_offstreet", "pick_parking"):
                c = parking
                m = (not f["garage_or_covered"]) if i == "car_garage" else (f["parking_kind"] in (None, "street"))
            elif i.startswith("total_") and a["filter"]:
                c, m = total, not passes(f, a["filter"])
            elif i == "pick_money":
                c, m = total, f["min_total"] is not None and f["min_total"] > med_total
            if c:
                chips[i] = c
                if m:
                    misses[i] = c
    return chips, misses


# ---- experience line ---------------------------------------------------------------------------------------------
def experience_line(e, base_year):
    """One plain sentence on what the kind of life means: the experience's guarded tagline, else the first sentence of
    its promise, else of its subhead, whichever first has at most 16 words. A sentence that names particular towns is
    skipped: the line is shown on every building of the experience, and must be true of each one's kind of place."""
    towns = {str(h.get("name") or "") for h in (base_year.get("_hood_names") or [])}
    for t in (e.get("tagline"), (base_year.get("prose") or {}).get("promise"), base_year.get("subhead")):
        s = sentences(voice(t))
        if s and words(s[0]) <= 16 and not re.search(r"\bin [A-Z][a-z]+(?: [A-Z][a-z]+)* and [A-Z]", s[0]):
            return s[0]
    return EXPERIENCE_LINE_FALLBACK.get(e.get("id"))


# Used only when every guarded sentence names particular towns (Will, 2026-11-17: the line labels every building of
# the experience). Each is checked against the kept set in test_concierge_data.py.
EXPERIENCE_LINE_FALLBACK = {
    "space": "Towns farther out, where the typical apartment is bigger.",
}


# ---- life here ---------------------------------------------------------------------------------------------------
def enriched_for(bid, lat, lon):
    """(places record of data/enriched/<hash>.json, colour record of data/enriched_color/<hash>.json, point) for a
    building: its address keys through data/reference/building_crosswalk.csv, the file name the sha1 of the key
    (scripts/rank.py color_table, scripts/enrich_units.py), the key whose point is nearest the building."""
    import hashlib
    xw = _crosswalk()
    best = None
    for k in sorted(xw.get(bid, []), key=len):
        h = hashlib.sha1(k.encode()).hexdigest()[:14]
        f = ENRICHED / f"{h}.json"
        if not f.exists():
            continue
        e = json.loads(f.read_text(encoding="utf-8"))
        d = haversine_km({"lat": lat, "lon": lon}, {"lat": e["lat"], "lon": e["lon"]})
        if best is None or d < best[0] - 1e-9:
            c = COLOR / f"{h}.json"
            best = (d, e, json.loads(c.read_text(encoding="utf-8")) if c.exists() else {})
    if best is None:
        return {}, {}, None
    return best[1], best[2], {"lat": best[1]["lat"], "lon": best[1]["lon"]}


_XW = None


def _crosswalk():
    global _XW
    if _XW is None:
        xw = pd.read_csv(REF / "building_crosswalk.csv", dtype=str, keep_default_na=False)
        _XW = defaultdict(list)
        for a, b in zip(xw.addr_key, xw.building_id):
            _XW[b].append(a)
    return _XW


def osm_list(rec):
    v_ = (rec or {}).get("value")
    return [p for p in v_ if isinstance(p, dict) and p.get("name") and p.get("metres") is not None] if isinstance(v_, list) else []


def osm_one(rec):
    rec = rec or {}
    if rec.get("name") and num(rec.get("value")) is not None:
        return [{"name": rec["name"], "metres": num(rec["value"]), "osm_url": rec.get("osm_url")}]
    return []


def place(p, kind, source_name=OSM, url=None):
    m = num(p.get("metres"))
    return {"name": clean_name(p["name"]), "kind": kind, "walk_min": walk_min_of(m), "distance_mi": miles_of(m),
            "source_name": source_name, "source_url": url or p.get("osm_url") or "https://www.openstreetmap.org/"}


def nearest(cands, kind, max_walk=NEAR_MIN, skip=()):
    for p in sorted(cands, key=lambda p: num(p.get("metres"))):
        n = clean_name(p.get("name"))
        if not name_ok(n) or n in skip:
            continue
        pl = place(p, kind)
        if max_walk is None or pl["walk_min"] <= max_walk:
            return pl
        return None
    return None


def far_words(pl):
    """'a 6-minute walk' up to WALK_MAX_MIN, else 'N miles away' (straight line)."""
    return a_walk(pl["walk_min"]) if pl["walk_min"] <= WALK_MAX_MIN else f"{pl['distance_mi']:.1f} miles away"


# The researcher's doubts, as the coordinator ruled on them (2026-11-17)
CLOSED = re.compile(r"\(closed\)", re.I)
CLOSED_NOTE = re.compile(r"\bwarning row\b|\bnot for display\b|\bhas closed\b|\bpermanently closed\b", re.I)
UNCONFIRMED = re.compile(r"operation (?:is )?not confirmed|not confirmed on (?:its|the cafe's|the restaurant's) own (?:page|site)|"
                         r"current hours not confirmed|\bpredates\b|\bolder\b.*\b20(?:1\d|2[0-3])\b|"
                         r"\b(?:article|story|itinerary|report|review|listing)\b[^.]{0,30}\b(?:from|dated)\b[^.]{0,15}\b(?:19\d\d|20(?:[01]\d|2[0-3]))\b|"
                         r"\b(?:dates?|date from)\b[^.]{0,20}\b(?:19\d\d|20(?:[01]\d|2[0-3]))\b|\bnot confirmed\b[^.]{0,40}\b(?:dates?|rules?)\b|"
                         r"\b(?:2026|main) dates not confirmed\b|\bappears to date from\b", re.I)
BLOCKED = set(["four city"])                      # never named: closed June 2025, still mapped (coordinator, 2026-11-17)
FACT_OVERRIDE = {"CityCenter Danbury Farmers' Market": ("There is a Saturday market downtown in season, on the CityCenter Green.", "",
                                                         "CityCenter Green")}


def name_key(n):
    """The first two words of a name, lower case: 'Four City Brewing' and the mapped 'Four City Brewery' share it."""
    return " ".join(re.findall(r"[a-z0-9']+", str(n or "").lower())[:2])


def load_life_facts():
    """data/reference/life_here_facts.csv as {building id: [rows]} and {neighborhood id: [rows]}: absent or partial is
    fine (written by a research agent; the script picks up more rows on its next run). Only confidence 'high' rows
    are used; the counts of the rest are reported."""
    out_b, out_h, skipped = defaultdict(list), defaultdict(list), Counter()
    if not LIFE_FACTS.exists():
        return out_b, out_h, {"file": "absent"}
    try:
        t = pd.read_csv(LIFE_FACTS, dtype=str, keep_default_na=False, on_bad_lines="skip")
    except (OSError, ValueError, pd.errors.ParserError) as e:
        return out_b, out_h, {"file": f"unreadable: {e}"[:200]}
    BLOCKED.clear()
    for r in t.to_dict("records"):
        r = {k: str(v_ or "").strip() for k, v_ in r.items()}
        if CLOSED.search(r.get("place_name", "")) or CLOSED_NOTE.search(r.get("notes", "")):
            BLOCKED.add(name_key(re.sub(r"\s*\(closed\)", "", r["place_name"], flags=re.I)))
    for r in t.to_dict("records"):
        r = {k: str(v_ or "").strip() for k, v_ in r.items()}
        conf = r.get("confidence", "").lower()
        if r.get("place_name") in FACT_OVERRIDE:
            r["fact"], r["schedule"], r["place_name"] = FACT_OVERRIDE[r["place_name"]]
            conf = "high"                             # the coordinator's wording (2026-11-17), no dated detail
        if name_key(r.get("place_name", "")) in BLOCKED:
            skipped["closed or warning"] += 1
            continue
        if UNCONFIRMED.search(r.get("notes", "")):
            skipped["operation unconfirmed or source before 2024"] += 1
            continue
        if conf != "high":
            skipped[f"confidence {conf or 'blank'}"] += 1
            continue
        r["moment"] = MOMENT_ALIASES.get(r.get("moment", "").lower(), r.get("moment", "").lower())
        if r["moment"] not in dict(MOMENTS):
            skipped[f"moment {r['moment'] or 'blank'} (not one of the four)"] += 1
            continue
        if not (r.get("fact") and r.get("place_name") and r.get("source_url", "").startswith("http")):
            skipped["incomplete"] += 1
            continue
        if r.get("building_id"):
            out_b[r["building_id"]].append(r)
        elif r.get("neighborhood_id"):
            out_h[r["neighborhood_id"]].append(r)
        else:
            skipped["no building or neighborhood"] += 1
    return out_b, out_h, {"file": "present", "rows": int(len(t)), "used_high": sum(map(len, out_b.values())) + sum(map(len, out_h.values())),
                          "skipped": dict(skipped)}


DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
MOMENT_ALIASES = {"dog_walk": "dog", "dog's walk": "dog", "sat": "saturday", "sun": "sunday", "work": "weekday"}


def name_span(name, text):
    """The longest run of two or more words of `name` that the text contains (case-insensitive), as the text writes
    it; the whole name when it is one word and present. None when the text does not name the place."""
    ws = name.split()
    for n in range(len(ws), 0, -1):
        if n == 1 and len(ws) > 1:
            break
        for i in range(0, len(ws) - n + 1):
            span = " ".join(ws[i:i + n])
            m = re.search(r"(?<!\w)" + re.escape(span) + r"(?!\w)", text, re.I)
            if m:
                return text[m.start():m.end()]
    for w_ in ws:                                     # one distinctive word of the name ("Berlinetta"), as written
        if len(w_) >= 5 and w_[0].isupper() and w_.lower() not in GENERIC_NAME_WORDS:
            m = re.search(r"(?<!\w)" + re.escape(w_) + r"(?!\w)", text)
            if m:
                return w_
    return None


GENERIC_NAME_WORDS = {"park", "parks", "street", "avenue", "downtown", "market", "library", "center", "centre", "theater",
                      "theatre", "night", "music", "trivia", "farmers", "public", "garden", "gardens", "green", "plaza",
                      "square", "beach", "river", "brewing", "brewery", "coffee", "house", "hall", "branch", "jazz",
                      "sunday", "saturday", "weekly", "school", "church", "museum", "festival", "series", "stamford",
                      "bridgeport", "flushing", "yonkers", "newark", "danbury", "hamden", "orange", "bloomfield",
                      "belleville", "brooklyn", "queens"}


def fact_sentence(r, pt):
    """A research row -> (fact sentence, walk sentence or None, place or None, extra source or None), or None.
    The fact is the row's own words (a dash between two words becomes a hyphen), with its schedule in brackets where
    the fact does not already say it. Where the row has coordinates, the walk is computed here from the building's
    point; a distance or a walking time in the web text is never used (the row is skipped). Not used: a banned,
    crime or hype word, a question, more than 32 words, coordinates more than 25 miles from the building."""
    name = clean_name(r["place_name"])
    fact = re.sub(r"(?<=\w)\s*[–—]\s*(?=\w)", "-", re.sub(r"\s+", " ", r["fact"])).strip().rstrip(".") + "."
    sched = re.sub(r"(?<=\w)\s*[–—]\s*(?=\w)", "-", r.get("schedule", "").strip())
    if not name_ok(name) or BANNED.search(fact + " " + sched) or CRIME.search(fact) or HYPE.search(fact) or re.search(r"[—–?]", fact + sched):
        return None
    if re.search(r"\b(minutes?|miles?|blocks?|feet|meters?)\b[^.]{0,12}\b(away|from|walk|drive)\b|\bwalking distance\b", fact, re.I):
        return None
    days = {d for d in DAYS if re.search(rf"\b{d}", fact + " " + sched, re.I)}
    want = {"saturday": "sat", "sunday": "sun"}.get(r["moment"])
    if days and ((want and want not in days) or (r["moment"] == "weekday" and days <= {"sat", "sun"})):
        return None                                   # an event on another day is never put under this moment
    lat, lon = num(r.get("lat")), num(r.get("lon"))
    m = haversine_km(pt, {"lat": lat, "lon": lon}) * 1000 if (pt and lat is not None and lon is not None) else None
    if m is not None and m > 1609.344 * 25:
        return None
    kind = r.get("place_kind") or "place"
    src = {"name": r.get("source_name") or "Source", "url": r["source_url"]}
    if kind == "route":
        return (fact, None, mentioned(fact, [], src), src) if words(fact) <= 32 else None
    sched = re.sub(r"\s*\([^)]*\)", "", sched).strip(" ,;")
    span = name_span(name, fact)
    named_after = False
    if span is None:
        if re.match(r"(The|A|An|It) ", fact) and ":" not in fact:
            fact = f"At {name}, {fact[0].lower()}{fact[1:]}"
        else:
            named_after = True                         # "City park rules: ... (Seaside Park)."
        span = name
    cal = {w_.lower().rstrip("s") for w_ in re.findall(r"[A-Za-z]+", sched) if CAL_WORDS.match(w_)}
    says_when = any(re.search(rf"\b{c}", fact, re.I) for c in cal)
    extra = []
    sw = [w_ for w_ in re.findall(r"[a-z0-9:]+", sched.lower()) if len(w_) > 2]
    overlap = sum(1 for w_ in sw if w_ in fact.lower()) / len(sw) if sw else 1
    if sched and sched.lower() not in fact.lower() and overlap < 0.6 and (re.search(r"\d", sched) or not says_when):
        extra.append(sched)
    if named_after:
        extra.insert(0, name)
    if extra and words(fact) + sum(words(x) for x in extra) <= 30:
        fact = fact.rstrip(".") + f" ({'; '.join(extra)})."
    elif named_after:
        return None
    if words(fact) > 32:
        return None
    pl = {"name": span, "official_name": name, "kind": kind, "walk_min": walk_min_of(m), "distance_mi": miles_of(m),
          "source_name": src["name"], "source_url": src["url"]}
    if kind in ("park", "trail", "greenway", "beach") and pl["walk_min"] is not None:
        pl["walk_min"] = pl["distance_mi"] = None     # a large area's coordinates are its middle, not its nearest edge
    walk = f"It is {far_words(pl)}." if pl["walk_min"] is not None else None
    return fact, walk, [pl] + mentioned(fact, [span, name], src), None


CAL_WORDS = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*$|^(January|February|March|April|May|June|July|August|September|October|"
                       r"November|December|Thanksgiving|Christmas)$")


def mentioned(text, own, src):
    """Other places a research fact names (two or more capitalised words in a row, not opening the sentence, not a
    day or month): each goes into places[] with the row's source, as 'named in the source', with no walk."""
    t = text
    for n in sorted(own, key=len, reverse=True):
        t = re.sub(re.escape(n), " ", t, flags=re.I)
    out = []
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][\w'’&]+(?:\s+(?:of|the|and|&|de)\s+[A-Z][\w'’&]+|\s+[A-Z][\w'’&]+)+)", t):
        run = m.group(1).strip()
        while run.split() and CAL_WORDS.match(run.split()[0]):
            run = " ".join(run.split()[1:])            # "Each April Branch Brook Park" names Branch Brook Park
        run = re.sub(r"'s$|’s$", "", run)
        parts = run.split()
        if len(parts) < 2:
            continue
        if all(CAL_WORDS.match(w_) for w_ in parts if w_[0].isupper()) or run in [p["name"] for p in out]:
            continue
        out.append({"name": run, "official_name": run, "kind": "named in the source", "walk_min": None, "distance_mi": None,
                    "source_name": src["name"], "source_url": src["url"]})
    return out


def life_here(x, src_b, us, life_b, life_h):
    """Four moments (weekday, saturday, sunday, dog) for one building, from structured data, the named mapped places of
    data/enriched*/ (OpenStreetMap) and the high-confidence rows of data/reference/life_here_facts.csv. Each sentence is
    a candidate with a priority; they are added in order while the text stays within 3 sentences and 45 words. A moment
    with no candidate is left out."""
    e, c, pt = enriched_for(x["id"], x["lat"], x["lon"])
    P = (e.get("places") or {})
    go, er, gs = P.get("going_out") or {}, P.get("errands") or {}, P.get("green_space") or {}
    best = us[0]
    f = x["fit"]
    rows = life_b.get(x["id"], []) + life_h.get(x["neighborhood_id"], [])
    cand = defaultdict(list)                         # moment -> [(priority, sentence, [places], [sources])]

    def add(mom, pri, s, places=(), sources=(), n_sent=1, alt=None):
        cand[mom].append((pri, s, list(places), list(sources), n_sent, alt))

    # weekday
    cafe = nearest(osm_list(go.get("nearest_cafes")), "café")
    if cafe:
        add("weekday", 1, f"Coffee at {cafe['name']}, {minutes(cafe['walk_min'])} on foot, then back to the desk.", [cafe])
    sup = nearest(osm_one(er.get("nearest_supermarket")), "supermarket", max_walk=None)
    if sup:
        add("weekday", 3, f"For groceries, {sup['name']} is {far_words(sup)}.", [sup])
    lib = nearest([p for p in osm_list((c.get("culture") or {}).get("library_examples")) if not re.search(r"\blaw\b|judicial|museum", p["name"], re.I)],
                  "library")
    if lib:
        add("weekday", 4, f"For a change of desk, {lib['name']} is {a_walk(lib['walk_min'])}.", [lib])
    # saturday
    r8 = f["restaurants_10min"]
    bar = nearest(osm_list(go.get("nearest_bars")), "bar")
    show = nearest(osm_list((c.get("culture") or {}).get("cinema_theatre_examples")), "cinema or theater", max_walk=WALK_MAX_MIN)
    if r8 is not None and (r8 >= 5 or bar or show):
        n = int(r8)
        cnt = (go.get("restaurant_count_800m") or {}).get("source_url")
        if n:
            add("saturday", 1, f"{n} restaurant{' is' if n == 1 else 's are'} within a 10-minute walk.", [],
                [{"name": f"{OSM} (mapped places within 800 m)", "url": cnt}] if cnt else [])
    if bar:
        add("saturday", 3, f"The nearest bar, {bar['name']}, is {minutes(bar['walk_min'])} on foot.", [bar])
    if show:
        add("saturday", 4, f"For a night out, {show['name']} is {a_walk(show['walk_min'])}.", [show])
    # sunday
    d, toll = f["drive_min"], f["toll_round_trip"]
    if d is not None:
        t = "" if toll is None else (", with no tolls" if toll == 0 else f", about ${half_up(toll)} round trip in tolls")
        src = []
        dr = (e.get("drive") or {}).get("minutes_to_jamaica") or {}
        if dr.get("source_url"):
            src.append({"name": "OSRM route estimate, no traffic", "url": dr["source_url"]})
        for it in ((e.get("drive") or {}).get("toll_round_trip_ezpass") or {}).get("items") or []:
            if str(it.get("source_url") or "").startswith("http") and toll:
                src.append({"name": f"Toll rates: {it.get('agency') or it.get('facility')}", "url": it["source_url"]})
        add("sunday", 1, f"Mom and Dad are about {minutes(d)} away by car{t}.", [], src)
    bak = nearest(osm_list(go.get("nearest_bakeries")), "bakery")
    if bak:
        add("sunday", 4, f"Bring something from {bak['name']}, {a_walk(bak['walk_min'])}.", [bak])
    # dog
    pw = f["park_walk_min"]
    if pw is not None:
        if f["park_name"]:
            rec = next((r for r in (gs.get("nearest_named_park"), gs.get("nearest_park")) if (r or {}).get("name") and f["park_name"] in clean_name(r["name"])), None) or {}
            pk = {"name": f["park_name"], "kind": "park", "walk_min": pw, "distance_mi": miles_of(num(rec.get("value"))),
                  "source_name": OSM, "source_url": rec.get("osm_url") or "https://www.openstreetmap.org/"}
            add("dog", 1, f"{f['park_name']} is {a_walk(pw)} for the daily loop.", [pk])
        else:
            u_ = ((gs.get("nearest_named_park") or {}).get("osm_url") or (gs.get("nearest_park") or {}).get("osm_url"))
            add("dog", 1, f"The nearest park is {a_walk(pw)} for the daily loop.", [], [{"name": OSM, "url": u_}] if u_ else [])
    if f["dog_area_in_building"]:
        add("dog", 2, "The building lists its own dog area.", [],
            [{"name": "The building's listing", "url": x.get("listing_url") or x.get("photos_url")}] if (x.get("listing_url") or x.get("photos_url")) else [])
    else:
        run = nearest(osm_one(gs.get("nearest_dog_park")), "dog run", max_walk=None)
        if run and num(gs.get("nearest_dog_park", {}).get("value")) <= DOG_RUN_MAX_M:
            nm = run["name"]
            add("dog", 3, (f"{nm} is {far_words(run)}." if re.search(r"\bdog\b", nm, re.I) else f"The nearest dog run is at {nm}, {far_words(run)}."), [run])
    vet = nearest(osm_one(er.get("nearest_veterinary")), "vet", max_walk=None)
    if vet and num(er.get("nearest_veterinary", {}).get("value")) <= VET_MAX_M:
        add("dog", 4, f"The nearest vet, {vet['name']}, is {far_words(vet)}.", [vet])
    # research rows: after the first sentence of the moment
    for r in rows:
        fs = fact_sentence(r, pt)
        if not fs:
            continue
        fact, walk, pls, src = fs
        pl = (pls or [None])[0]
        add(r["moment"], 2, fact + (" " + walk if walk else ""), pls or [], [src] if src else [], 2 if walk else 1,
            alt=fact if walk else None)               # the fact alone, where the walk to the place is already said
    out = []
    for mom, title in MOMENTS:
        cs = sorted(cand.get(mom, []), key=lambda t: t[0])
        if not cs:
            continue
        take, n_w, n_s = [], 0, 0
        for pri, s, pls, srcs, k, alt in cs:
            key = lambda n: re.sub(r"[^a-z]", "", str(n or "").lower())
            said = {key(p["name"]) for t in take for p in t[2]} | {key(p.get("official_name")) for t in take for p in t[2]}
            if alt and pls and (key(pls[0]["name"]) in said or key(pls[0]["official_name"]) in said):
                s, k = alt, 1
            if n_s + k > LIFE_MAX_SENTENCES or n_w + words(s) > LIFE_MAX_WORDS or any(s == t[1] for t in take):
                continue
            take.append((pri, s, pls, srcs))
            n_w += words(s)
            n_s += k
        places, sources, seen = [], [], set()
        for _, _, pls, srcs in take:
            for p in pls:
                if p["name"] not in {q["name"] for q in places}:
                    places.append(p)
                if p["source_url"] not in seen:
                    seen.add(p["source_url"])
                    sources.append({"name": p["source_name"], "url": p["source_url"]})
            for s_ in srcs:
                if s_["url"] and s_["url"] not in seen:
                    seen.add(s_["url"])
                    sources.append(s_)
        out.append({"moment": mom, "title": title, "text": " ".join(t[1] for t in take),
                    "places": places, "sources": sources})
    return out


def add_version_two(out, b_base):
    """Adds questions, buildings[].fit / fit_chips / fit_misses / experience_line / life_here, experiences[].line and
    meta.matching / matching_examples / life_here_facts to the concierge data. Nothing existing is changed."""
    blds = out["buildings"]
    src = {bd["id"]: bd for bd in b_base["buildings"]}
    by_b = defaultdict(list)
    for u in sorted(b_base["units"], key=lambda u: (-(num((u.get("scores") or {}).get("rank")) or 0), u["id"])):
        by_b[u["building_id"]].append(u)
    for x in blds:
        x["fit"] = fit_fields(x, src[x["id"]], by_b[x["id"]])
    questions = build_questions(blds)
    count_fits(questions, blds)
    med_total = median(x["fit"]["min_total"] for x in blds)
    years = {y["id"]: y for y in b_base["years"]}
    lines = {}
    for e in out["experiences"]:
        e["line"] = experience_line(e, years.get(e["id"]) or {})
        lines[e["id"]] = e["line"]
    life_b, life_h, facts_report = load_life_facts()
    for x in blds:
        x["fit_chips"], x["fit_misses"] = chips_for(x, questions, med_total)
        x["experience_line"] = lines.get(x["experience_id"])
        x["life_here"] = life_here(x, src[x["id"]], by_b[x["id"]], life_b, life_h)
    out["questions"] = questions
    m = out["meta"]
    m["matching"] = MATCHING
    m["matching_examples"] = matching_examples(blds, questions)
    m["walk_pace"] = (f"Walking minutes are straight-line metres x {WALK_DETOUR} / {WALK_M_PER_MIN:.0f} m a minute, as the "
                      f"park walks elsewhere on the page; miles are straight line. Counts 'within a 10-minute walk' are "
                      f"mapped places within 800 m.")
    m["life_here_facts"] = facts_report
    m["life_here_counts"] = dict(Counter(mo_["moment"] for x in blds for mo_ in x["life_here"]))
    return out


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
    out = add_version_two(concierge(b, d), b)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, allow_nan=False), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {out['meta']['counts']}")
    for p in out["meta"]["parked"]:
        print(f"  parked: {p['neighborhood']} under {p['under']} ({p['km']} km, \"{p['label']}\"{', fallback' if p['fallback'] else ''})")
    print(f"  checked on {out['meta']['checked_day']}: {out['meta']['checked_counts']}")
    for q in out["questions"]:
        print(f"  question {q['id']}: " + ", ".join(f"{a['id']} {a['fits_alone']}" for a in q["answers"]))
    print(f"  life here: {out['meta']['life_here_counts']}; facts file: {out['meta']['life_here_facts']}")
    for q in out["meta"]["either_or_audit"]:
        print(f"  either/or {q['id']}: spearman {q['spearman']}, top-5 shared {q['top5_shared']} -> {'kept' if q['kept'] else 'trade-off, not among the three' if q['trade_off'] else 'no trade-off'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
