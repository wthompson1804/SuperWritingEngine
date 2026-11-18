#!/usr/bin/env python3
"""The short version's recommender (docs/CONCIERGE_DESIGN.md "Version 3" and "Version 4"): its data and its reference.

VERSION 4 (current): the choices are eight made-up apartments in pairs (choice-based conjoint, partial profiles),
picked adaptively from a fixed pool (meta.recommender.conjoint; see the section at the end of this file: build_pool,
next_task, run_conjoint, priorities, nudge, recommend_from_weights). The posterior, the recommendation, tags and
why / gives-up are version 3's. The version 3 pair functions (next_pair, should_stop) stay for reference but no
example uses them.

Pure Python (no numpy in the reference). scripts/concierge_data.py calls add_version_three(out) as its last step; the
page's JS implements the same functions on the same shipped numbers and is tested to agree with
meta.recommender_examples.

DATA IT ADDS (nothing renamed)
  buildings[].features          {family, money, room, going_out, green, parking, sure}, each 0..1 (VALUE FUNCTIONS)
  buildings[].features_raw      the inputs: drive_min, total, sqft, bedroom, restaurants_10min, bars_10min,
                                park_walk_min, dog_area, parking_kind, checked, star
  buildings[].features_imputed  the features whose input was missing and set to the median of the set
  buildings[].similar           the 5 nearest other buildings, unweighted Euclidean distance on standardised features
  buildings[].group_id          the neighborhood the recommender counts it under (a parked neighborhood counts as its host's)
  neighborhoods[].tags          0 to 2 plain words from its strongest features against the set, each true in plain terms
                                (TAG_FLOORS: "near family" only within 30 minutes, ...)
  recommender_samples           N_SAMPLES weight vectors (FEATURES order), Dirichlet, fixed SEED, rounded to 6 decimals
  meta.recommender              every parameter, the value functions with breakpoints, standardisation, groups and
                                their similarity matrix, the algorithm in words
  meta.recommender_examples     scripted persona runs the page must reproduce exactly

THE MODEL
  utility U_w(b)   = sum_k w_k * features[k]  over the six weighted features (sure excluded)
  score_w(b)       = U_w(b) * features.sure
  group score      = expected mean of the two best of a random 3-building subset (fewer than 3: filled with the set's median)
  likelihood       gap g = U_w(a) - U_w(b);  P(a) = sig((g - band)/T), P(b) = sig((-g - band)/T), P(either) = 1 - P(a) - P(b)
  posterior        pi_s proportional to prod_j L_s(answer_j), from uniform; normalised once at the end
  mean weights     wbar = sum_s pi_s w_s; since U is linear in w, expected utility = U_wbar
  top three        MMR over groups: normalised score s' = (s - min)/(max - min) over groups (0 if all equal);
                   greedily pick argmax lambda*s' - (1-lambda)*max similarity to those already picked;
                   similarity = 1 - d/dmax, d = Euclidean distance between group centroids of standardised features
  next pair        pool = top PAIR_POOL buildings by score_wbar; for each unasked pair (a.id < b.id) the expected
                   reduction in entropy of the distribution (over samples, weighted by pi) of the per-sample top-three
                   set (unordered, by the same MMR with that sample's weights); highest gain first
  stop             at least MIN_PAIRS asked, at most MAX_PAIRS; stop once the posterior probability that the
                   sample's best neighborhood is among the current three reaches STOP_PROB
  determinism      every comparison uses values rounded to ROUND decimals; ties go to the smaller id (string order)
"""
from __future__ import annotations

import json
import math
import random
import statistics
from collections import Counter

FEATURES = ("family", "money", "room", "going_out", "green", "parking")
N_SAMPLES = 400
SEED = 20261117
# The prior: "family, going out, green and room weighted up a little; parking and money neutral". Relative mass 1.25
# against 1.0, normalised; concentration (sum of alphas) 6, so each alpha is near 1 (0.86 to 1.07): close to flat on
# the simplex, so a strong single priority ("budget first", "space first") is still well covered by the 400 samples,
# with the centre leaning her way. Chosen by simulation (see meta.recommender.tuning).
PRIOR_RELATIVE = {"family": 1.25, "money": 1.0, "room": 1.25, "going_out": 1.25, "green": 1.25, "parking": 1.0}
CONCENTRATION = 6.0
TEMPERATURE = 0.04          # logistic temperature on the utility gap (utilities run 0..1, gaps between places 0.0-0.4)
EITHER_BAND = 0.03          # a gap within this is "either is fine" (for a simulated persona, and the model's threshold)
MIN_PAIRS, MAX_PAIRS, STOP_PROB = 3, 6, 0.9
MMR_LAMBDA = 0.7
RELEVANCE_FLOOR = 0.85       # places 2 and 3 need a score >= this x the best neighborhood's ...
RELEVANCE_TOP_SHARE = 0.5   # ... and a rank in the top half by score; fewer than three clear it: fill by score
PAIR_POOL = 30
N_SIMILAR = 5
N_MORE = 3
ROUND = 9
NUDGES = (1.5, 2.0, 3.0, 5.0, 10.0)

# VALUE FUNCTIONS: piecewise linear between breakpoints (x, value), flat outside them.
FAMILY_PTS = [(0, 1.0), (25, 0.9), (35, 0.8), (90, 0.05), (120, 0.0)]          # drive minutes to Mom and Dad
MONEY_PTS = [(1700, 1.0), (2300, 0.0)]                                          # monthly total, $; $600 left = 1
ROOM_SQFT = (300, 1000)                                                         # ln scale between these
ROOM_LOG_SHARE, ROOM_BEDROOM_STEP = 0.7, 0.3
GOING_PTS = [(0, 0.0), (20, 0.6), (60, 1.0)]                                    # restaurants + bars within 800 m
GREEN_PTS = [(0, 1.0), (5, 1.0), (12, 0.5), (20, 0.15), (30, 0.05)]             # walk minutes to nearest park
GREEN_DOG_AREA = 0.1                                                            # added, capped at 1
PARKING_VALUE = {"garage": 1.0, "covered": 1.0, "carport": 1.0, "lot": 0.7, "off_street": 0.7, "driveway": 0.7, "assigned": 0.7,
                 "unspecified": 0.5,                       # parking offered, kind not stated
                 "surface": 0.7, "street": 0.2}
PARKING_UNKNOWN = 0.4
SURE_TODAY, SURE_EARLIER, SURE_STAR = 1.0, 0.6, 0.8

LABEL = {"family": "being near Mom and Dad", "money": "money left over", "room": "room at home",
         "going_out": "going out", "green": "a park nearby", "parking": "parking"}
TAG_HIGH = {"family": "near family", "money": "good value", "room": "more room", "going_out": "lively",
            "green": "green", "parking": "easy parking"}
TAG_LOW = {"going_out": "quiet"}
PARKING_WORDS = {1.0: "garage or covered parking", 0.7: "off-street parking", 0.5: "parking offered, kind not stated", 0.4: "parking not stated",
                 0.2: "street parking"}


def q(x):
    return round(x, ROUND)


def mins(n):
    return f"{n} minute{'' if n == 1 else 's'}"


def places_n(n):
    return f"{n} place{'' if n == 1 else 's'}"


def pw(x, pts):
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def clamp(x):
    return max(0.0, min(1.0, x))


def f_family(drive):
    return pw(drive, FAMILY_PTS)


def f_money(total):
    return pw(total, MONEY_PTS)


def f_room(sqft, bedroom):
    lo, hi = ROOM_SQFT
    return clamp(ROOM_LOG_SHARE * clamp(math.log(sqft / lo) / math.log(hi / lo)) + ROOM_BEDROOM_STEP * (1 if bedroom else 0))


def f_going(n):
    return pw(n, GOING_PTS)


def f_green(walk, dog_area):
    return clamp(pw(walk, GREEN_PTS) + (GREEN_DOG_AREA if dog_area else 0))


def f_parking(kind):
    return PARKING_VALUE.get(kind, PARKING_UNKNOWN) if kind else PARKING_UNKNOWN


def value_functions_doc():
    return {
        "family": {"input": "drive_min (minutes by car to Mom and Dad, free-flow estimate)", "shape": "piecewise linear",
                   "breakpoints": FAMILY_PTS, "note": "falls slowly to 25 minutes, steeply from 35 to 90; 0 from 120"},
        "money": {"input": "total (the lowest monthly total with utilities and fees)", "shape": "linear",
                  "breakpoints": MONEY_PTS, "note": "dollars left under $2,300 a month; $600 or more left = 1"},
        "room": {"input": "sqft (largest apartment) and bedroom (a separate bedroom)", "shape":
                 f"{ROOM_LOG_SHARE} x clamp(ln(sqft/{ROOM_SQFT[0]}) / ln({ROOM_SQFT[1]}/{ROOM_SQFT[0]})) + {ROOM_BEDROOM_STEP} x bedroom",
                 "breakpoints": [[ROOM_SQFT[0], 0.0], [ROOM_SQFT[1], ROOM_LOG_SHARE]], "bedroom_step": ROOM_BEDROOM_STEP},
        "going_out": {"input": "restaurants_10min + bars_10min (mapped places within 800 m)", "shape": "piecewise linear",
                      "breakpoints": GOING_PTS, "note": "steep to 20, flat after 60"},
        "green": {"input": "park_walk_min (nearest park, minutes on foot) and dog_area (a dog area in the building)",
                  "shape": "piecewise linear, plus dog_area_bonus, at most 1", "breakpoints": GREEN_PTS,
                  "dog_area_bonus": GREEN_DOG_AREA},
        "parking": {"input": "parking_kind", "shape": "step", "values": PARKING_VALUE, "unknown": PARKING_UNKNOWN},
        "sure": {"input": "checked status and star of each apartment", "shape":
                 "per apartment (1 if seen listed today, else 0.6) x (0.8 if it has one thing to confirm); the building takes its best apartment",
                 "values": {"today": SURE_TODAY, "earlier": SURE_EARLIER, "one_thing_to_confirm": SURE_STAR},
                 "note": "multiplies the utility, never adds"},
        "missing": "a missing drive, total, sqft, place count or park walk is the median of the set; the feature is listed in features_imputed",
    }


# ---------------------------------------------------------------- features, standardisation, similar, groups, tags

def _raw(b):
    f = b.get("fit") or {}
    facts = b.get("facts") or {}
    apts = b.get("apartments") or []
    today = [a for a in apts if (a.get("checked") or {}).get("status") in ("confirmed_today", "price_changed_today")]

    def sure_of(a):
        st = (a.get("checked") or {}).get("status")
        return (SURE_TODAY if st in ("confirmed_today", "price_changed_today") else SURE_EARLIER) * (SURE_STAR if a.get("star") else 1.0)
    rest, bars = f.get("restaurants_10min"), f.get("bars_10min")
    return {
        "drive_min": f.get("drive_min", facts.get("drive_min")),
        "total": f.get("min_total", facts.get("total_from")),
        "sqft": f.get("sqft_max"),
        "bedroom": bool(f.get("has_one_bedroom")),
        "restaurants_10min": rest,
        "bars_10min": bars,
        "park_walk_min": f.get("park_walk_min"),
        "dog_area": bool(f.get("dog_area_in_building")),
        "parking_kind": f.get("parking_kind"),
        "checked": "seen_today" if today else "seen_earlier",
        "star": bool(apts) and all(a.get("star") for a in apts),
    }, (max(sure_of(a) for a in apts) if apts else SURE_EARLIER * SURE_STAR)


def add_features(buildings):
    raws = []
    for b in buildings:
        r, sure = _raw(b)
        raws.append((b, r, sure))
    meds = {}
    for k in ("drive_min", "total", "sqft", "park_walk_min"):
        meds[k] = statistics.median([r[k] for _, r, _ in raws if r[k] is not None])
    meds["places"] = statistics.median([(r["restaurants_10min"] or 0) + (r["bars_10min"] or 0) for _, r, _ in raws
                                        if r["restaurants_10min"] is not None or r["bars_10min"] is not None])
    for b, r, sure in raws:
        imp = []

        def get(k, feat):
            if r[k] is None:
                imp.append(feat)
                return meds[k]
            return r[k]
        drive, total, sqft, walk = get("drive_min", "family"), get("total", "money"), get("sqft", "room"), get("park_walk_min", "green")
        if r["restaurants_10min"] is None and r["bars_10min"] is None:
            places = meds["places"]
            imp.append("going_out")
        else:
            places = (r["restaurants_10min"] or 0) + (r["bars_10min"] or 0)
        b["features_raw"] = r
        b["features"] = {"family": round(f_family(drive), 6), "money": round(f_money(total), 6),
                         "room": round(f_room(sqft, r["bedroom"]), 6), "going_out": round(f_going(places), 6),
                         "green": round(f_green(walk, r["dog_area"]), 6), "parking": round(f_parking(r["parking_kind"]), 6),
                         "sure": round(sure, 6)}
        b["features_imputed"] = sorted(set(imp))
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in meds.items()}


def standardisation(buildings):
    mean, sd = {}, {}
    for k in FEATURES:
        xs = [b["features"][k] for b in buildings]
        m = sum(xs) / len(xs)
        s = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))
        mean[k], sd[k] = round(m, 6), round(s if s > 1e-9 else 1.0, 6)
    return mean, sd


def zvec(b, mean, sd):
    return [(b["features"][k] - mean[k]) / sd[k] for k in FEATURES]


def add_similar(buildings, mean, sd):
    z = {b["id"]: zvec(b, mean, sd) for b in buildings}
    for b in buildings:
        d = sorted((q(math.sqrt(sum((x - y) ** 2 for x, y in zip(z[b["id"]], z[o["id"]])))), o["id"]) for o in buildings if o["id"] != b["id"])
        b["similar"] = [i for _, i in d[:N_SIMILAR]]


GROUP_KM = 10.0             # a one-apartment neighborhood joins its host only within this distance and in the same state


def host_of(h, by_id):
    """The group a neighborhood counts under: its parked host if that is within GROUP_KM and in the same state, else itself."""
    p = h.get("parked_under")
    if p and p in by_id and by_id[p].get("state") == h.get("state") and (h.get("parked_distance_km") or 1e9) <= GROUP_KM:
        return p
    return h["id"]


def build_groups(neighborhoods, buildings, mean, sd):
    hb = {h["id"]: h for h in neighborhoods}
    host = {h["id"]: host_of(h, hb) for h in neighborhoods}
    name = {h["id"]: h["name"] for h in neighborhoods}
    members = {}
    for b in sorted(buildings, key=lambda b: b["id"]):
        g = host.get(b["neighborhood_id"], b["neighborhood_id"])
        b["group_id"] = g
        members.setdefault(g, []).append(b["id"])
    by = {b["id"]: b for b in buildings}
    gids = sorted(members)
    cent = {}
    for g in gids:
        zs = [zvec(by[i], mean, sd) for i in members[g]]
        cent[g] = [sum(c) / len(zs) for c in zip(*zs)]
    dist = {(a, c): math.sqrt(sum((x - y) ** 2 for x, y in zip(cent[a], cent[c]))) for a in gids for c in gids}
    dmax = max(dist.values()) or 1.0
    sim = [[round(1 - dist[(a, c)] / dmax, 6) for c in gids] for a in gids]
    groups = [{"id": g, "name": name.get(g, g), "building_ids": members[g],
               "neighborhood_ids": sorted(h for h, x in host.items() if x == g and h in {by[i]["neighborhood_id"] for i in members[g]}),
               "centroid_z": [round(c, 6) for c in cent[g]]} for g in gids]
    return groups, sim


TAG_FLOORS = {"near family": "median drive to Mom and Dad <= 30 minutes",
              "lively": "median places to eat and drink within a 10-minute walk >= 20",
              "quiet": "median places to eat and drink within a 10-minute walk <= 5",
              "more room": "median size >= 650 sq ft, or most buildings with a one-bedroom",
              "good value": "median monthly total <= $1,950",
              "green": "median walk to the nearest park <= 5 minutes",
              "easy parking": "garage, covered or off-street parking at most buildings"}


def tag_holds(word, bs):
    """The tag is true in plain terms of these buildings (TAG_FLOORS), not only relative to the set."""
    r = [b["features_raw"] for b in bs]
    med = lambda xs: statistics.median(xs) if xs else None  # noqa: E731
    places = med([(x["restaurants_10min"] or 0) + (x["bars_10min"] or 0) for x in r
                  if x["restaurants_10min"] is not None or x["bars_10min"] is not None])
    if word == "near family":
        d = med([x["drive_min"] for x in r if x["drive_min"] is not None])
        return d is not None and d <= 30
    if word == "lively":
        return places is not None and places >= 20
    if word == "quiet":
        return places is not None and places <= 5
    if word == "more room":
        sq = med([x["sqft"] for x in r if x["sqft"] is not None])
        return (sq is not None and sq >= 650) or sum(x["bedroom"] for x in r) > len(r) / 2
    if word == "good value":
        t = med([x["total"] for x in r if x["total"] is not None])
        return t is not None and t <= 1950
    if word == "green":
        w = med([x["park_walk_min"] for x in r if x["park_walk_min"] is not None])
        return w is not None and w <= 5
    if word == "easy parking":
        return sum(b["features"]["parking"] >= 0.7 for b in bs) > len(bs) / 2
    return False


def _tags_for(bids, by, mean, sd):
    """Up to two tags: the strongest features against the set (standardised centroid above the mean), each kept only
    when it is true in plain terms (TAG_FLOORS). Fewer qualify: one, or none."""
    bs = [by[i] for i in bids]
    zs = [zvec(b, mean, sd) for b in bs]
    c = [sum(x) / len(zs) for x in zip(*zs)]
    cand = []
    for j, k in enumerate(FEATURES):
        cand.append((q(c[j]), k, TAG_HIGH[k]))
        if k in TAG_LOW:
            cand.append((q(-c[j]), k, TAG_LOW[k]))
    cand.sort(key=lambda t: (-t[0], t[2]))
    out, used = [], set()
    for z, k, word in cand:
        if z > 0 and k not in used and tag_holds(word, bs):
            out.append(word)
            used.add(k)
        if len(out) == 2:
            break
    return [w if i else w[0].upper() + w[1:] for i, w in enumerate(out)]


def add_tags(neighborhoods, buildings, groups, mean, sd):
    by = {b["id"]: b for b in buildings}
    gm = {g["id"]: g["building_ids"] for g in groups}
    for h in neighborhoods:
        own = [b["id"] for b in buildings if b["neighborhood_id"] == h["id"]]
        bids = gm[h["id"]] if h["id"] in gm else own
        h["tags"] = _tags_for(bids, by, mean, sd) if bids else []


def draw_samples():
    rng = random.Random(SEED)
    tot = sum(PRIOR_RELATIVE.values())
    alpha = [CONCENTRATION * PRIOR_RELATIVE[k] / tot for k in FEATURES]
    out = []
    for _ in range(N_SAMPLES):
        g = [rng.gammavariate(a, 1.0) for a in alpha]
        s = sum(g)
        out.append([round(x / s, 6) for x in g])
    return out, [round(a, 6) for a in alpha]


# ---------------------------------------------------------------- the reference algorithm

def utility(b, w):
    f = b["features"]
    return sum(w[j] * f[k] for j, k in enumerate(FEATURES))


def score(b, w):
    return utility(b, w) * b["features"]["sure"]


def _sig(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def likelihood(gap, choice, params):
    T, band = params["temperature"], params["either_band"]
    pa = _sig((gap - band) / T)
    pb = _sig((-gap - band) / T)
    if choice == "a":
        return pa
    if choice == "b":
        return pb
    return max(0.0, 1.0 - pa - pb)


def posterior(samples, answers, buildings, params):
    """pi over samples after the answers [{a, b, choice}], from uniform."""
    by = {b["id"]: b for b in buildings}
    raw = []
    for w in samples:
        p = 1.0
        for x in answers:
            gap = task_gap(w, x["task"], params) if "task" in x else utility(by[x["a"]], w) - utility(by[x["b"]], w)
            p *= likelihood(gap, x["choice"], params)
        raw.append(p)
    s = sum(raw)
    if s <= 0:
        return [1.0 / len(samples)] * len(samples)
    return [p / s for p in raw]


def mean_weights(samples, pi):
    return [sum(p * w[j] for p, w in zip(pi, samples)) for j in range(len(FEATURES))]


MIN_BUILDINGS = 3            # the page promises three neighborhoods with three buildings each: only groups with 3+


def group_scores(w, buildings, params, all_groups=False):
    """Scores of the recommendable groups (at least params['min_buildings'] buildings); all_groups=True scores every
    group (for reporting how often a small neighborhood would have been best)."""
    sc = {b["id"]: q(score(b, w)) for b in buildings}
    med = statistics.median(sc.values())               # a one-building neighborhood is not a deep one
    need = 0 if all_groups else params.get("min_buildings", 0)
    out = {}
    for g in params["groups"]:
        if len(g["building_ids"]) >= need:
            out[g["id"]] = top2_of_3(sorted((sc[i] for i in g["building_ids"]), reverse=True), med)
    return out


def top2_of_3(s, med):
    """The expected mean of the two best of a random 3-building subset of the scores s (sorted, best first): the
    neighborhood scored as if it had three buildings, so depth alone does not win. With fewer than three, the missing
    ones are the set's median score. E[top two of 3] = (E[sum of 3] - E[min of 3]) / 2, E[sum] = 3 x mean(s),
    P(the i-th best, 1-based, is the min of the subset) = C(i-1, 2) / C(n, 3)."""
    s = list(s)
    if len(s) < 3:
        s = sorted(s + [med] * (3 - len(s)), reverse=True)
        return (s[0] + s[1]) / 2
    n = len(s)
    total = math.comb(n, 3)
    e_min = sum(x * math.comb(i, 2) for i, x in enumerate(s)) / total     # i = number of better buildings
    return (3 * sum(s) / n - e_min) / 2


def eligible(gs, params):
    """The groups good enough to be recommended: the best, and those with score >= relevance_floor x the best's AND
    ranked in the top relevance_top_share by score (ceil), in score order (ties by id)."""
    order = sorted(gs, key=lambda g: (-q(gs[g]), g))
    cut = math.ceil(len(order) * params["relevance_top_share"])
    floor = q(params["relevance_floor"] * gs[order[0]])
    return [g for i, g in enumerate(order) if i == 0 or (i < cut and q(gs[g]) >= floor)], order


def mmr(gs, params, k=3):
    """MMR among the eligible groups; if fewer than k are eligible, they are all taken and the rest filled by score."""
    gids = [g["id"] for g in params["groups"]]
    idx = {g: j for j, g in enumerate(gids)}
    sim = params["group_similarity"]
    lam = params["mmr_lambda"]
    lo, hi = min(gs.values()), max(gs.values())
    norm = {g: ((gs[g] - lo) / (hi - lo) if hi - lo > 1e-12 else 0.0) for g in gs}
    ok, order = eligible(gs, params)
    k = min(k, len(gs))
    if len(ok) < k:
        return ok + [g for g in order if g not in ok][:k - len(ok)]
    pool = sorted(ok)
    picked = []
    while len(picked) < k:
        best = None
        for g in pool:
            if g in picked:
                continue
            red = max((sim[idx[g]][idx[p]] for p in picked), default=0.0)
            v = q(lam * norm[g] - (1 - lam) * red)
            if best is None or v > best[0] or (v == best[0] and g < best[1]):
                best = (v, g)
        picked.append(best[1])
    return picked


def top_set(w, buildings, params):
    return "|".join(sorted(mmr(group_scores(w, buildings, params), params)))


def set_distribution(samples, pi, sets):
    """sets: the per-sample top-three set keys (computed once). Returns {key: prob} in first-appearance order."""
    d = {}
    for p, s in zip(pi, sets):
        d[s] = d.get(s, 0.0) + p
    return d


def entropy(probs):
    return -sum(p * math.log(p) for p in probs if p > 0)


def sample_sets(samples, buildings, params):
    return [top_set(w, buildings, params) for w in samples]


def _pair_key(a, b):
    return (a, b) if a < b else (b, a)


def ranked_buildings(w, buildings):
    return sorted(buildings, key=lambda b: (-q(score(b, w)), b["id"]))


def best_group(w, buildings, params):
    gs = group_scores(w, buildings, params)
    return sorted(gs, key=lambda g: (-q(gs[g]), g))[0]


def sample_bests(samples, buildings, params):
    """For each sample, its best neighborhood (highest group score, ties by id); computed once."""
    return [best_group(w, buildings, params) for w in samples]


def stop_probability(samples, answers, buildings, params, pi=None, bests=None):
    """The posterior probability that the sample's best neighborhood is among the current three (MMR on wbar)."""
    pi = pi if pi is not None else posterior(samples, answers, buildings, params)
    bests = bests if bests is not None else sample_bests(samples, buildings, params)
    three = set(mmr(group_scores(mean_weights(samples, pi), buildings, params), params))
    return sum(p for p, b in zip(pi, bests) if b in three)


def should_stop(samples, answers, buildings, params, pi=None, bests=None):
    n = len(answers)
    if n >= params["max_pairs"]:
        return True
    if n < params["min_pairs"]:
        return False
    return q(stop_probability(samples, answers, buildings, params, pi, bests)) >= params["stop_prob"]


def next_pair(samples, answers, buildings, params, sets=None, explain=False, bests=None):
    """The next (a, b) to ask, a.id < b.id, or None when the stop rule says stop."""
    sets = sets if sets is not None else sample_sets(samples, buildings, params)
    pi = posterior(samples, answers, buildings, params)
    if should_stop(samples, answers, buildings, params, pi, bests):
        return None
    w = mean_weights(samples, pi)
    pool = ranked_buildings(w, buildings)[:params["pair_pool"]]
    asked = {_pair_key(x["a"], x["b"]) for x in answers}
    keys = list(set_distribution(samples, pi, sets))
    kidx = {k: j for j, k in enumerate(keys)}
    sidx = [kidx[s] for s in sets]
    h0 = entropy(set_distribution(samples, pi, sets).values())
    U = [[utility(b, ws) for ws in samples] for b in pool]
    T, band = params["temperature"], params["either_band"]
    best = None
    ids = [b["id"] for b in pool]
    order = sorted(range(len(pool)), key=lambda i: ids[i])
    for ii, i in enumerate(order):
        for j in order[ii + 1:]:
            a, b = ids[i], ids[j]
            if (a, b) in asked:
                continue
            mass = [[0.0] * len(keys) for _ in range(3)]
            for s in range(len(samples)):
                if pi[s] == 0.0:
                    continue
                g = U[i][s] - U[j][s]
                pa = _sig((g - band) / T)
                pb = _sig((-g - band) / T)
                pe = max(0.0, 1.0 - pa - pb)
                k = sidx[s]
                mass[0][k] += pi[s] * pa
                mass[1][k] += pi[s] * pb
                mass[2][k] += pi[s] * pe
            eh = 0.0
            for m in mass:
                P = sum(m)
                if P > 0:
                    eh += P * entropy(x / P for x in m)
            gain = q(h0 - eh)
            if best is None or gain > best[0]:
                best = (gain, a, b)
    if best is None:
        return None
    return (best[1], best[2], best[0]) if explain else (best[1], best[2])


def _group_figures(bs):
    rs = [b["features_raw"] for b in bs]
    drives = [r["drive_min"] for r in rs if r["drive_min"] is not None]
    totals = [r["total"] for r in rs if r["total"] is not None]
    sq = [r["sqft"] for r in rs if r["sqft"] is not None]
    places = [(r["restaurants_10min"] or 0) + (r["bars_10min"] or 0) for r in rs if r["restaurants_10min"] is not None or r["bars_10min"] is not None]
    walks = [r["park_walk_min"] for r in rs if r["park_walk_min"] is not None]
    return {"drive": round(statistics.median(drives)) if drives else None, "total": min(totals) if totals else None,
            "sqft": max(sq) if sq else None, "bedroom": any(r["bedroom"] for r in rs),
            "places": round(statistics.median(places)) if places else None,
            "walk": max(1, round(min(walks))) if walks else None,
            "parking": statistics.median_low([b["features"]["parking"] for b in bs])}


def _better(k, f):
    """The figure in the direction 'bigger is better', or None when it is not known."""
    if k == "family":
        return None if f["drive"] is None else -f["drive"]
    if k == "money":
        return None if f["total"] is None else -f["total"]
    if k == "room":
        return None if not f["sqft"] else f["sqft"] + (10000 if f["bedroom"] else 0)
    if k == "going_out":
        return f["places"]
    if k == "green":
        return None if f["walk"] is None else -f["walk"]
    return None if f["parking"] == PARKING_UNKNOWN else f["parking"]


def _good(k, f):
    if k == "family":
        return f"About {mins(f['drive'])} by car to Mom and Dad" if f["drive"] is not None else "Close to Mom and Dad"
    if k == "money":
        return f"Monthly totals from ${f['total']:,} with utilities and fees" if f["total"] is not None else "Lower monthly totals"
    if k == "room":
        size = f"up to {f['sqft']:,} sq ft" if f["sqft"] else "more room"
        return f"A separate bedroom, {size}" if f["bedroom"] else size[0].upper() + size[1:]
    if k == "going_out":
        return f"{places_n(f['places'])} to eat and drink within a 10-minute walk" if f["places"] is not None else "Places to eat and drink close by"
    if k == "green":
        return f"A park about {mins(f['walk'])} on foot" if f["walk"] is not None else "A park close by"
    return PARKING_WORDS.get(f["parking"], "parking not stated")[0].upper() + PARKING_WORDS.get(f["parking"], "parking not stated")[1:]


def _fig_text(k, f):
    if k == "family":
        return mins(f["drive"]) if f["drive"] is not None else "not known"
    if k == "money":
        return f"${f['total']:,}" if f["total"] is not None else "not known"
    if k == "room":
        return f"{f['sqft']:,} sq ft" if f["sqft"] else "size not published"
    if k == "going_out":
        return places_n(f["places"]) if f["places"] is not None else "not known"
    if k == "green":
        return mins(f["walk"]) if f["walk"] is not None else "not known"
    return PARKING_WORDS.get(f["parking"], "parking not stated")


def _bad(k, f, others):
    o = " and ".join(_fig_text(k, x) for x in others)
    if k == "family":
        return f"Farther from Mom and Dad: about {_fig_text(k, f)} by car (the other two: {o})"
    if k == "money":
        return f"Costs more: monthly totals from {_fig_text(k, f)} (the other two: {o})"
    if k == "room":
        return f"Smaller: up to {_fig_text(k, f)} (the other two: {o})"
    if k == "going_out":
        return f"Quieter: {_fig_text(k, f)} to eat and drink within a 10-minute walk (the other two: {o})"
    if k == "green":
        return f"The nearest park is farther: about {_fig_text(k, f)} on foot (the other two: {o})"
    return f"{_fig_text(k, f)[0].upper() + _fig_text(k, f)[1:]} (the other two: {o})"


MARGIN = {"family": "drive at least 10 minutes and 20% longer", "money": "total at least $75 a month higher",
          "room": "at least 75 sq ft smaller", "going_out": "at least 10 and 30% fewer places to eat and drink",
          "green": "park walk at least 4 minutes longer", "parking": "a lower kind of parking (garage > off-street > street)"}


def clear_margin(k, f, o):
    """True when f is worse than o on feature k by a margin worth naming (MARGIN); both figures known."""
    if k == "family":
        return f["drive"] - o["drive"] >= 10 and f["drive"] >= 1.2 * o["drive"]
    if k == "money":
        return f["total"] - o["total"] >= 75
    if k == "room":
        return o["sqft"] - f["sqft"] >= 75
    if k == "going_out":
        return o["places"] - f["places"] >= 10 and f["places"] <= 0.7 * o["places"]
    if k == "green":
        return f["walk"] - o["walk"] >= 4
    return f["parking"] < o["parking"]


UNKNOWN_TEXT = {"room": "The size isn't published yet; ask on the tour", "parking": "Parking isn't stated yet; ask on the tour",
                "family": "The drive to Mom and Dad isn't known yet", "money": "The monthly total isn't known yet; ask on the tour",
                "going_out": "Places to eat and drink nearby aren't mapped yet", "green": "The nearest park isn't mapped yet"}


def _first_after_nudge(w, buildings, params, j, factor):
    w2 = list(w)
    w2[j] *= factor
    s = sum(w2)
    w2 = [x / s for x in w2]
    gs = group_scores(w2, buildings, params)
    return sorted(gs, key=lambda g: (-q(gs[g]), g))[0]


def what_would_change(w, buildings, params, gid, position, first):
    names = {g["id"]: g["name"] for g in params["groups"]}
    for level in params["nudges"]:
        for j, k in enumerate(FEATURES):
            for direction, factor in (("more", level), ("less", 1 / level)):
                f = _first_after_nudge(w, buildings, params, j, factor)
                hit = (f != first) if position == 0 else (f == gid)
                if hit:
                    who = names[f]
                    return {"feature": k, "direction": direction, "factor": level, "neighborhood_id": f,
                            "text": f"If {LABEL[k]} mattered {direction}, {who} would come first."}
    return None


def more_like_this(building, weights, shown, buildings, params, n=N_MORE):
    """Up to n nearest other buildings: Euclidean on standardised features, each squared difference weighted by her
    mean weights; excluding `shown` and the building itself; ties by id."""
    mean, sd = params["feature_mean"], params["feature_sd"]
    zb = zvec(building, mean, sd)
    cand = []
    for o in buildings:
        if o["id"] == building["id"] or o["id"] in shown:
            continue
        zo = zvec(o, mean, sd)
        cand.append((q(math.sqrt(sum(weights[j] * (zb[j] - zo[j]) ** 2 for j in range(len(FEATURES))))), o["id"]))
    cand.sort()
    return [i for _, i in cand[:n]]


def recommend(samples, answers, buildings, params):
    return recommend_from_weights(mean_weights(samples, posterior(samples, answers, buildings, params)), buildings, params)


def recommend_from_weights(w, buildings, params):
    """The recommendation for weights w (her posterior mean, or the mean after a nudge)."""
    by = {b["id"]: b for b in buildings}
    gs = group_scores(w, buildings, params)
    picked = mmr(gs, params)
    first = sorted(gs, key=lambda g: (-q(gs[g]), g))[0]
    gmap = {g["id"]: g for g in params["groups"]}
    tops = {g: sorted(gmap[g]["building_ids"], key=lambda i: (-q(score(by[i], w)), i))[:3] for g in picked}
    figs = {g: _group_figures([by[i] for i in tops[g]]) for g in picked}
    all_mean = [sum(b["features"][k] for b in buildings) / len(buildings) for k in FEATURES]
    shown = [i for g in picked for i in tops[g]]
    taken = set(shown)
    out = []
    for pos, g in enumerate(picked):
        cent = [sum(by[i]["features"][k] for i in tops[g]) / len(tops[g]) for k in FEATURES]
        lift = sorted(((q(w[j] * (cent[j] - all_mean[j])), k) for j, k in enumerate(FEATURES)), key=lambda t: (-t[0], t[1]))
        why_k = [k for _, k in lift[:2]]
        others = [o for o in picked if o != g]
        oc = [[sum(by[i]["features"][k] for i in tops[o]) / len(tops[o]) for k in FEATURES] for o in others]
        diffs = [(q(w[j] * (cent[j] - sum(c[j] for c in oc) / len(oc))), q(cent[j] - sum(c[j] for c in oc) / len(oc)), k)
                 for j, k in enumerate(FEATURES)] if oc else []
        give, give_unknown = None, False
        for _, _, k in sorted(diffs, key=lambda t: (t[0], t[2])):
            if dict((t[2], t[1]) for t in diffs)[k] >= 0 or k in why_k:     # never give up what `why` praises
                continue
            mine, theirs = _better(k, figs[g]), [_better(k, figs[o]) for o in others]
            if mine is None:                       # the weak point is an unknown: say so plainly
                give, give_unknown = k, True
                break
            if all(x is not None for x in theirs) and all(clear_margin(k, figs[g], figs[o]) for o in others):
                give = k
                break
        bl = []
        for i in tops[g]:
            more = more_like_this(by[i], w, taken, buildings, params)
            taken.update(more)
            bl.append({"id": i, "score": round(score(by[i], w), 6), "more_like_this": more})
        out.append({"neighborhood_id": g, "name": gmap[g]["name"], "score": round(gs[g], 6),
                    "buildings": bl, "why_features": why_k,
                    "why": ". ".join(_good(k, figs[g]) for k in why_k) + ".",
                    "gives_up_feature": give,
                    "gives_up": ((UNKNOWN_TEXT[give] if give_unknown else _bad(give, figs[g], [figs[o] for o in others])) + ".") if give else None,
                    "gives_up_unknown": give_unknown,
                    "what_would_change": what_would_change(w, buildings, params, g, pos, first)})
    return {"weights": [round(x, 6) for x in w], "neighborhoods": out}


def persona_answer(a, b, hidden, buildings_by, band):
    if hidden is None:
        return "either"
    g = utility(buildings_by[a], hidden) - utility(buildings_by[b], hidden)
    if abs(g) <= band:
        return "either"
    return "a" if g > 0 else "b"


def run_persona(samples, buildings, params, hidden, sets=None, pair_fn=None, bests=None):
    by = {b["id"]: b for b in buildings}
    sets = sets if sets is not None else sample_sets(samples, buildings, params)
    bests = bests if bests is not None else sample_bests(samples, buildings, params)
    pair_fn = pair_fn or next_pair
    answers = []
    while True:
        p = pair_fn(samples, answers, buildings, params, sets=sets, bests=bests)
        if p is None:
            break
        answers.append({"a": p[0], "b": p[1], "choice": persona_answer(p[0], p[1], hidden, by, params["either_band"])})
    return answers


def true_top(hidden, buildings, params, all_groups=False):
    gs = group_scores(hidden, buildings, params, all_groups)
    return sorted(gs, key=lambda g: (-q(gs[g]), g))[0]


PERSONAS = [
    ("near family, studio fine", {"family": 0.5, "money": 0.1, "room": 0.03, "going_out": 0.22, "green": 0.1, "parking": 0.05}),
    ("space first", {"family": 0.05, "money": 0.1, "room": 0.55, "going_out": 0.05, "green": 0.1, "parking": 0.15}),
    ("budget first", {"family": 0.15, "money": 0.55, "room": 0.1, "going_out": 0.05, "green": 0.1, "parking": 0.05}),
    ("going out above all", {"family": 0.15, "money": 0.1, "room": 0.05, "going_out": 0.55, "green": 0.1, "parking": 0.05}),
    ("either to everything", None),
]


def examples(samples, buildings, params, sets, bests):
    out = []
    for name, hw in PERSONAS:
        hidden = [hw[k] for k in FEATURES] if hw else None
        ans = run_persona(samples, buildings, params, hidden, sets, bests=bests)
        rec = recommend(samples, ans, buildings, params)
        p = stop_probability(samples, ans, buildings, params, bests=bests)
        out.append({"persona": name, "hidden_weights": dict(zip(FEATURES, hidden)) if hidden else None,
                    "answer_rule": "either to every pair" if hidden is None else
                    f"the building with the higher utility under hidden_weights; 'either' when the gap is within {params['either_band']}",
                    "answers": ans, "expected_pairs": [[x["a"], x["b"]] for x in ans],
                    "expected_mean_weights": dict(zip(FEATURES, rec["weights"])),
                    "expected_stop_probability": round(p, 6),
                    "expected_top": [[n["neighborhood_id"], [b["id"] for b in n["buildings"]]] for n in rec["neighborhoods"]],
                    "expected_more_like_this": {b["id"]: b["more_like_this"] for n in rec["neighborhoods"] for b in n["buildings"]},
                    "expected_why": {n["neighborhood_id"]: n["why"] for n in rec["neighborhoods"]},
                    "expected_gives_up": {n["neighborhood_id"]: n["gives_up"] for n in rec["neighborhoods"]},
                    "expected_what_would_change": {n["neighborhood_id"]: (n["what_would_change"] or {}).get("text") for n in rec["neighborhoods"]}})
    return out


HIT_TOLERANCE = 0.02


def validation(exs, buildings, params):
    """Per persona: its true best neighborhood by its hidden weights (equal weights for "either to everything"), the
    best of the three it was given, and the gap. A hit is the true best in the three, or one within HIT_TOLERANCE of
    its score. Shown, not hidden: the tests require at least 4 of the 5 to hit."""
    rows = []
    for e in exs:
        h = [e["hidden_weights"][k] for k in FEATURES] if e["hidden_weights"] else [1 / len(FEATURES)] * len(FEATURES)
        gs = group_scores(h, buildings, params)
        truth = sorted(gs, key=lambda g: (-q(gs[g]), g))[0]
        truth_all = true_top(h, buildings, params, all_groups=True)
        top = [n for n, _ in e["expected_top"]]
        got = max(top, key=lambda g: (q(gs[g]), g))
        gap = (gs[truth] - gs[got]) / gs[truth] if gs[truth] else 0.0
        rows.append({"persona": e["persona"], "weights": "hidden" if e["hidden_weights"] else "equal (no hidden weights)",
                     "true_best": truth, "true_best_score": round(gs[truth], 6), "best_recommended": got,
                     "best_recommended_score": round(gs[got], 6), "gap_share": round(gap, 4),
                     "true_best_any_size": truth_all, "true_best_is_small": truth_all != truth,
                     "hit_strict": truth in top, "hit_within_tolerance": gap <= HIT_TOLERANCE + 1e-12})
    return {"tolerance": HIT_TOLERANCE, "required_hits": 4, "personas": rows,
            "hits": sum(r["hit_within_tolerance"] for r in rows), "missed": [r["persona"] for r in rows if not r["hit_within_tolerance"]]}


def params_block(buildings, groups, sim, mean, sd, alpha, meds):
    return {
        "features": list(FEATURES), "sure_feature": "sure",
        "value_functions": value_functions_doc(), "medians_for_missing": meds,
        "temperature": TEMPERATURE, "either_band": EITHER_BAND, "n_samples": N_SAMPLES, "seed": SEED,
        "prior": {"distribution": "Dirichlet", "relative_mass": PRIOR_RELATIVE, "concentration": CONCENTRATION, "alpha": alpha,
                  "draw": "Python random.Random(seed).gammavariate(alpha_k, 1) per feature, normalised, rounded to 6 decimals"},
        "min_pairs": MIN_PAIRS, "max_pairs": MAX_PAIRS, "stop_prob": STOP_PROB, "mmr_lambda": MMR_LAMBDA, "relevance_floor": RELEVANCE_FLOOR, "relevance_top_share": RELEVANCE_TOP_SHARE,
        "pair_pool": PAIR_POOL, "group_km": GROUP_KM, "min_buildings": MIN_BUILDINGS, "tag_floors": TAG_FLOORS, "gives_up_margin": MARGIN, "n_similar": N_SIMILAR, "n_more_like_this": N_MORE, "round_decimals": ROUND, "nudges": list(NUDGES),
        "feature_mean": mean, "feature_sd": sd,
        "groups": [{k: g[k] for k in ("id", "name", "building_ids", "neighborhood_ids")} for g in groups],
        "group_similarity": sim,
        "algorithm": {
            "version": "4: the choices are meta.recommender.conjoint tasks (eight, adaptive); next_pair, stop, sample_sets and sample_bests below are version 3's and no longer drive the page",
            "utility": "U_w(b) = sum_k w_k x features[k] over `features` (sure excluded)",
            "score": "score_w(b) = U_w(b) x features.sure",
            "group_score": "each building's score is rounded to round_decimals; a group scores the expected mean of the two best of a random 3-building subset of its buildings (exact: (3 x mean - E[min of 3]) / 2, with P(the i-th best is the min) = C(i-1, 2) / C(n, 3), i counted from 1 in score order, best first); a group with fewer than three buildings is filled to three with the median building score of the whole set under the same weights (the mean of the two middle values when the count is even), then the mean of its two best. Why (coordinator, 2026-11-17): with the mean of its two best, a deep neighborhood wins by having many buildings to pick from (Newark, 20 buildings, was in the three for 197 of 200 simulated users); a one-building neighborhood is not treated as a deep one either",
            "likelihood": "gap = U_w(a) - U_w(b); P(a) = sig((gap - either_band)/temperature); P(b) = sig((-gap - either_band)/temperature); P(either) = max(0, 1 - P(a) - P(b))",
            "posterior": "pi_s = prod over answers (in order) of the likelihood, divided by the sum over samples; uniform if the sum is 0",
            "mean_weights": "wbar_k = sum_s pi_s x w_s,k; expected utility = U_wbar",
            "recommendable": "only groups with at least min_buildings (3) buildings are scored for recommendation (group_scores), so every recommendation is three neighborhoods with three buildings each; smaller neighborhoods stay in Browse everything. Everything below (floor, MMR, true best in the simulations) is within those",
            "eligible": "order groups by round(score) desc, id; eligible = the first, plus any with rank < ceil(n x relevance_top_share) and round(score) >= round(relevance_floor x the first's score); if fewer than 3 are eligible, the recommendation is the eligible ones then the next by score (no diversity)",
            "mmr": "among the eligible groups only (iterated in id order): s' = (score - min)/(max - min) over all groups (all 0 if max - min <= 1e-12); pick 3 greedily by round(lambda x s' - (1 - lambda) x max similarity to the picked, round_decimals), ties to the smaller id; similarity is group_similarity (1 - centroid distance / largest centroid distance, standardised features)",
            "sample_sets": "for each sample, the MMR top three with that sample's weights, as sorted ids joined by '|'; computed once",
            "next_pair": "pool = top pair_pool buildings by round(score_wbar) desc, id; pairs (a, b) with a < b by id, skipping pairs asked; gain = round(H(set distribution under pi) - sum over answers of P(answer) x H(set distribution under the posterior after that answer)); highest gain, ties to the earlier pair in (a, b) id order; entropy in nats",
            "sample_bests": "for each sample, its best group (highest group score with that sample's weights, ties by id); computed once",
            "stop": "stop when answers >= max_pairs, or answers >= min_pairs and round(stop probability) >= stop_prob (0.9 from 2026-11-17), where stop probability = sum of pi_s over the samples whose best group is among the current three (MMR on wbar, as recommend). (Changed 2026-11-17 from 'the most probable top-three set has probability >= stop_prob', which almost never holds with ~57 neighborhoods.) The next pair is still chosen by the expected entropy reduction of the top-three set",
            "groups": "a one-apartment neighborhood counts under its parked host only when the host is within group_km and in the same state; otherwise it is its own group (groups lists the result)",
            "recommend": "groups by MMR on wbar; in each, the three best buildings by round(score) desc, id; why = the two features with the largest wbar_k x (group centroid_k - mean over all buildings_k); gives_up: features in order of wbar_k x (centroid_k - mean of the other two picked centroids_k), negative ones only and never one of the two `why` features (centroids over the buildings shown); the first whose figure is unknown here (sq ft not published, parking not stated) is said plainly (gives_up_unknown true), or the first where this neighborhood's figure is worse than BOTH others' known figures by the margin in gives_up_margin (both figures as in the text: drive median minutes, lowest total, largest sq ft, median places, shortest park walk rounded) is compared; none: null. Figures are over the buildings shown",
            "what_would_change": "multiply one weight by a nudge factor (more) or divide by it (less), renormalise, and see which group has the highest score; levels in `nudges` order, then features in order, then more before less; the first found where the first group changes (for the first neighborhood) or becomes this one (for the second and third)",
            "more_like_this": "for each of the nine buildings shown, in order: up to 3 nearest other buildings by sqrt(sum_k wbar_k x (z_k - z'_k)^2), z = (features - feature_mean)/feature_sd, excluding the nine and the thumbnails already given; ties by id",
            "comparisons": "values compared are rounded to round_decimals; ties go to the smaller id",
        },
    }


def add_version_three(out):
    """Adds the recommender's data to the concierge data (docs/CONCIERGE_DESIGN.md "Version 3"). Nothing renamed."""
    blds, hoods = out["buildings"], out["neighborhoods"]
    meds = add_features(blds)
    mean, sd = standardisation(blds)
    add_similar(blds, mean, sd)
    groups, sim = build_groups(hoods, blds, mean, sd)
    hname = {h["id"]: h["name"] for h in hoods}
    for b in blds:                                # the card shows the building's own neighborhood, not only its group's
        b["neighborhood_name"] = hname.get(b["neighborhood_id"])
    add_tags(hoods, blds, groups, mean, sd)
    samples, alpha = draw_samples()
    params = params_block(blds, groups, sim, mean, sd, alpha, meds)
    out["recommender_samples"] = samples
    out["meta"]["recommender"] = params
    sets = sample_sets(samples, blds, params)
    params["conjoint"] = conjoint_block(blds)                  # version 4: the choices are made-up apartments
    params["conjoint"]["flat_below"] = flat_threshold(samples)
    out["meta"]["recommender_examples"] = conjoint_examples(samples, blds, params)

    out["meta"]["data_version"] = data_version(params, samples)
    add_version_five(out, samples, blds, params)
    out["meta"]["recommender"]["validation"] = validation(out["meta"]["recommender_examples"], blds, params)
    return out


# ---------------------------------------------------------------- a numpy twin of next_pair, for simulation only

class Fast:
    """The same next_pair / posterior as the reference, vectorised with numpy, for simulating many users. Tested to
    ask the same pairs as next_pair (scripts/test_concierge_data.py). Not part of the page's contract."""

    def __init__(self, samples, buildings, params, sets):
        import numpy as np
        self.np = np
        self.params, self.buildings = params, buildings
        self.ids = [b["id"] for b in buildings]
        self.idx = {i: j for j, i in enumerate(self.ids)}
        self.W = np.array(samples, dtype=float)
        F = np.array([[b["features"][k] for k in FEATURES] for b in buildings], dtype=float)
        self.U = F @ self.W.T                                   # buildings x samples
        self.sure = np.array([b["features"]["sure"] for b in buildings])
        keys = list(dict.fromkeys(sets))
        self.nk = len(keys)
        self.S = np.zeros((len(samples), self.nk))
        self.S[np.arange(len(samples)), [keys.index(s) for s in sets]] = 1.0
        self.samples = samples
        self.bests = sample_bests(samples, buildings, params)

    def pi(self, answers):
        np, p = self.np, self.params
        lp = np.ones(self.W.shape[0])
        for x in answers:
            g = self.U[self.idx[x["a"]]] - self.U[self.idx[x["b"]]]
            pa = 1 / (1 + np.exp(-(g - p["either_band"]) / p["temperature"]))
            pb = 1 / (1 + np.exp(-(-g - p["either_band"]) / p["temperature"]))
            lp = lp * (pa if x["choice"] == "a" else pb if x["choice"] == "b" else np.maximum(0, 1 - pa - pb))
        s = lp.sum()
        return lp / s if s > 0 else np.full(len(lp), 1 / len(lp))

    @staticmethod
    def _H(m, np):
        P = m.sum(axis=-1, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.where(m > 0, m / P, 1.0)
            return -(np.where(m > 0, r * np.log(r), 0.0)).sum(axis=-1), P[..., 0]

    def next_pair(self, samples, answers, buildings, params, sets=None, bests=None):
        np, p = self.np, self.params
        pi = self.pi(answers)
        dist = pi @ self.S
        n = len(answers)
        if n >= p["max_pairs"]:
            return None
        if n >= p["min_pairs"]:
            w_ = [float(x) for x in pi @ self.W]
            three = set(mmr(group_scores(w_, self.buildings, p), p))
            if round(float(sum(pi[s] for s, b in enumerate(self.bests) if b in three)), ROUND) >= p["stop_prob"]:
                return None
        w = pi @ self.W
        util = np.array([[b["features"][k] for k in FEATURES] for b in self.buildings]) @ w * self.sure
        order = sorted(range(len(self.ids)), key=lambda j: (-round(float(util[j]), ROUND), self.ids[j]))[:p["pair_pool"]]
        pool = sorted(order, key=lambda j: self.ids[j])
        asked = {_pair_key(x["a"], x["b"]) for x in answers}
        A, B = [], []
        for ii, i in enumerate(pool):
            for j in pool[ii + 1:]:
                if (self.ids[i], self.ids[j]) not in asked:
                    A.append(i), B.append(j)
        if not A:
            return None
        g = self.U[A] - self.U[B]                               # pairs x samples
        pa = 1 / (1 + np.exp(-(g - p["either_band"]) / p["temperature"]))
        pb = 1 / (1 + np.exp(-(-g - p["either_band"]) / p["temperature"]))
        pe = np.maximum(0, 1 - pa - pb)
        h0, _ = self._H(dist[None, :], np)
        eh = 0
        for L in (pa, pb, pe):
            m = (L * pi) @ self.S                               # pairs x sets
            H, P = self._H(m, np)
            eh = eh + P * H
        gain = np.round(h0[0] - eh, ROUND)
        k = int(np.argmax(gain))                                # first maximum: pairs are in (a, b) id order
        return (self.ids[A[k]], self.ids[B[k]])


# ================================================================ VERSION 4: choice-based conjoint on made-up apartments
# docs/CONCIERGE_DESIGN.md "Version 4". Each task shows two made-up apartments that differ on two or three attributes
# (partial profiles); the rest read "Same for both". Each attribute maps onto one recommender feature through the same
# value functions, so the weights learned here apply to the real buildings. Answers: "a", "b", "either" ("No real
# difference to me"), with the same likelihood as version 3 on the task's utility gap.

N_TASKS = 8
POOL_PREFILTER = 60          # the most utility-balanced candidates (smallest |gap| at her current mean weights)
TOTAL_QUANTILES = (0.1, 0.4, 0.7, 0.95)
ATTR_ORDER = ("money", "family", "room", "going_out", "parking", "green")
ATTR_LABEL = {"money": "Monthly total with utilities and fees", "family": "Drive to Mom and Dad", "room": "Space", "going_out": "Going out",
              "parking": "Parking", "green": "A park for the dog"}
PRIORITY_WORDS = {"family": "being near Mom and Dad", "money": "the monthly cost", "room": "space",
                  "going_out": "going out", "green": "a park for the dog", "parking": "parking"}
NUDGE_TIE_STEP = 0.01


def _round50(x):
    return int(50 * round(x / 50))


def conjoint_attributes(buildings):
    """Attributes and levels, worst to best by feature value. Totals: the TOTAL_QUANTILES of the buildings' lowest
    totals, rounded to $50 (the real spread); the other levels are the design's."""
    t = sorted(b["features_raw"]["total"] for b in buildings if b["features_raw"]["total"] is not None)
    totals = sorted({_round50(t[int(qq * (len(t) - 1))]) for qq in TOTAL_QUANTILES}, reverse=True)
    lv = {
        "money": [{"text": f"${x:,} a month", "raw": {"total": x}, "value": round(f_money(x), 6)} for x in totals],
        "family": [{"text": f"{m} minutes by car", "raw": {"drive_min": m}, "value": round(f_family(m), 6)} for m in (90, 60, 35, 15)],
        "room": [{"text": t_, "raw": {"sqft": sq, "bedroom": bd}, "value": round(f_room(sq, bd), 6)}
                 for t_, sq, bd in (("Studio, about 450 sq ft", 450, False), ("Studio, about 600 sq ft", 600, False),
                                    ("One bedroom, about 700 sq ft", 700, True), ("One bedroom, about 900 sq ft", 900, True))],
        "going_out": [{"text": t_, "raw": {"places": n}, "value": round(f_going(n), 6)}
                      for t_, n in (("Quiet: a couple of places to eat nearby", 2), ("Some: about 15 places to eat and drink nearby", 15),
                                    ("Lively: 40 or more places to eat and drink nearby", 40))],
        "parking": [{"text": t_, "raw": {"parking_kind": k}, "value": round(f_parking(k), 6)}
                    for t_, k in (("Street parking only", "street"), ("A spot in a lot", "lot"), ("A garage space", "garage"))],
        "green": [{"text": f"{m} minutes' walk", "raw": {"park_walk_min": m}, "value": round(f_green(m, False), 6)} for m in (15, 8, 2)],
    }
    for k, levels in lv.items():
        vals = [x["value"] for x in levels]
        assert all(a < b for a, b in zip(vals, vals[1:])), (k, vals)       # strictly worse to better
    return [{"id": k, "label": ATTR_LABEL[k], "feature": k, "levels": lv[k]} for k in ATTR_ORDER]


MAX_LEVEL_GAP = 2            # level pairs at most two steps apart: the trade is felt but not absurd


def build_pool(attrs):
    """Every task is a pure two-attribute trade-off, in this order (the index is the tie-break): each pair of
    attributes (in ATTR_ORDER); every pair of levels one or two steps apart (MAX_LEVEL_GAP) on the first, and the same
    on the second; one apartment has the better level on the first attribute and the worse on the second, the other the
    reverse; everything else is the same. Sides alternate by index: at an even index A has the better level on the
    first attribute, at an odd index B does. Never dominated. A task is [[attr, level of A, level of B], ...] with level
    indexes worst = 0."""
    import itertools
    n = {a["id"]: len(a["levels"]) for a in attrs}
    ids = [a["id"] for a in attrs]
    pool = []
    for i, j in itertools.combinations(ids, 2):
        for lo1, hi1 in itertools.combinations(range(n[i]), 2):
            if hi1 - lo1 > MAX_LEVEL_GAP:
                continue
            for lo2, hi2 in itertools.combinations(range(n[j]), 2):
                if hi2 - lo2 > MAX_LEVEL_GAP:
                    continue
                t = [[i, hi1, lo1], [j, lo2, hi2]]
                if len(pool) % 2:
                    t = [[k, b, a] for k, a, b in t]
                pool.append(t)
    return pool


GAIN = {"money": "Cheaper", "family": "Nearer family", "room": "More room", "going_out": "Livelier",
        "parking": "Better parking", "green": "Park closer"}
COST = {"money": "pricier", "family": "longer drive", "room": "smaller", "going_out": "quieter",
        "parking": "worse parking", "green": "park farther"}


def task_headlines(task, params):
    """{a, b}: per side, the gain and the cost in at most five plain words ("More room, but quieter")."""
    lv = _level_values(params)
    out = {}
    for side, me, other in (("a", 1, 2), ("b", 2, 1)):
        gain = next(k for k, *ab in task if lv[k][ab[me - 1]] > lv[k][ab[other - 1]])
        cost = next(k for k, *ab in task if lv[k][ab[me - 1]] < lv[k][ab[other - 1]])
        out[side] = f"{GAIN[gain]}, but {COST[cost]}"
    return out


def _level_values(params):
    return {a["id"]: [x["value"] for x in a["levels"]] for a in params["conjoint"]["attributes"]}


_LV_CACHE = {}


def task_gap(w, task, params):
    """U(A) - U(B) for weights w (FEATURES order): only the attributes that differ count."""
    cj = params["conjoint"]
    hit = _LV_CACHE.get(id(cj))
    if hit is None or hit[0] is not cj:
        hit = _LV_CACHE[id(cj)] = (cj, _level_values(params))
    lv = hit[1]
    return sum(w[FEATURES.index(k)] * (lv[k][a] - lv[k][b]) for k, a, b in task)


def _key(task):
    return tuple(tuple(x) for x in task)


def coverage_rank(task, counts):
    """The coverage key of a task: (times its two attributes have been asked in all, the larger of the two)."""
    c = [counts.get(k, 0) for k, _, _ in task]
    return (sum(c), max(c))


def next_task(samples, answers, params, explain=False):
    """The next task index into the pool, or None after n_tasks. Candidates: the pool minus every task on an attribute
    PAIR already asked (15 pairs for 6 attributes, so no pair repeats within the eight); of those, only the ones whose
    two attributes have appeared least so far (coverage_rank: lowest sum of their counts, then lowest larger count),
    so each attribute appears at least twice in eight; of those, the `prefilter` most utility-balanced at her mean
    weights (round(|gap|), index); of those, the one with the largest expected reduction in posterior uncertainty: the
    trace of the posterior covariance of the weights, expected over the three answers. Ties: lower index."""
    cj = params["conjoint"]
    if len(answers) >= cj["n_tasks"]:
        return None
    pool = cj["pool"]
    pi = posterior(samples, answers, [], params)
    w = mean_weights(samples, pi)
    asked_pairs = {frozenset(k for k, _, _ in x["task"]) for x in answers}
    counts = Counter(k for x in answers for k, _, _ in x["task"])
    cand = [i for i, t in enumerate(pool) if frozenset(k for k, _, _ in t) not in asked_pairs]
    if not cand:
        return None
    least = min(coverage_rank(pool[i], counts) for i in cand)
    cand = [i for i in cand if coverage_rank(pool[i], counts) == least]
    cand.sort(key=lambda i: (q(abs(task_gap(w, pool[i], params))), i))
    cand = sorted(cand[:cj["prefilter"]])
    T, band = params["temperature"], params["either_band"]
    nf = len(FEATURES)
    best = None
    for i in cand:
        t = pool[i]
        P = [0.0, 0.0, 0.0]
        M = [[0.0] * nf for _ in range(3)]
        for s, ws in enumerate(samples):
            if pi[s] == 0.0:
                continue
            g = task_gap(ws, t, params)
            pa = _sig((g - band) / T)
            pb = _sig((-g - band) / T)
            pe = max(0.0, 1.0 - pa - pb)
            for a_, L in enumerate((pa, pb, pe)):
                m = pi[s] * L
                P[a_] += m
                row = M[a_]
                for k in range(nf):
                    row[k] += m * ws[k]
        gain = q(sum(sum(x * x for x in M[a_]) / P[a_] for a_ in range(3) if P[a_] > 0))
        if best is None or gain > best[0]:
            best = (gain, i)
    if best is None:
        return None
    return (best[1], best[0]) if explain else best[1]


def task_answer(task, hidden, params):
    """A persona's answer: the apartment with the higher utility under hidden weights; 'either' within the band."""
    if hidden is None:
        return "either"
    g = task_gap(hidden, task, params)
    if abs(g) <= params["either_band"]:
        return "either"
    return "a" if g > 0 else "b"


def run_conjoint(samples, params, answer_fn):
    answers = []
    while True:
        i = next_task(samples, answers, params)
        if i is None:
            return answers
        t = params["conjoint"]["pool"][i]
        answers.append({"task_index": i, "task": t, "choice": answer_fn(t)})


FLAT_QUANTILE = 0.01         # flat: spread (max - min) of her weights below this quantile of the prior samples' spreads
LEAN_STEP = 0.02             # ... then "if anything, X a little more" when her top weight leads the next by this much
_FLAT_CACHE = {}


def flat_threshold(samples):
    """The FLAT_QUANTILE quantile of max - min over the weight samples: flatter than 99% of the prior's own vectors."""
    key = id(samples)
    if key not in _FLAT_CACHE or _FLAT_CACHE[key][0] is not samples:
        sp = sorted(max(x) - min(x) for x in samples)
        _FLAT_CACHE[key] = (samples, round(sp[int(FLAT_QUANTILE * (len(sp) - 1))], 6))
    return _FLAT_CACHE[key][1]


def priorities(w, flat_below=None):
    """Her weights in plain-word order (highest first; ties in FEATURES order) and the one-sentence summary. When the
    spread of her weights (max - min) is below flat_below (flat_threshold of the samples), flat is true and the
    sentence says nothing stood out, adding "if anything, X a little more" when the top weight leads by LEAN_STEP."""
    order = sorted(FEATURES, key=lambda k: (-q(w[FEATURES.index(k)]), FEATURES.index(k)))
    words = [PRIORITY_WORDS[k] for k in order]
    ws = sorted(w, reverse=True)
    flat = flat_below is not None and q(ws[0] - ws[-1]) < flat_below
    if flat:
        sent = "Nothing stood out strongly; you seem fairly open on all of these."
        if q(ws[0] - ws[1]) >= LEAN_STEP:
            sent = f"Nothing stood out strongly; you seem fairly open on all of these, if anything {words[0]} a little more."
    else:
        sent = f"{words[0][0].upper() + words[0][1:]} matters most to you, then {words[1]}; {words[-1]} matters least."
    return {"order": order, "words": words, "weights": {k: round(w[FEATURES.index(k)], 6) for k in order},
            "flat": flat, "sentence": sent}


def nudge(w, feature, direction):
    """Move one priority up or down one place: swap its weight with the weight of the priority just above (up) or just
    below (down) it in priorities() order; nothing else changes (the sum stays 1). If the two weights are equal (to
    ROUND decimals), the moved one is set NUDGE_TIE_STEP above (up) or below (down) the other, floored at 0, and the six
    are renormalised to sum 1. At the top (up) or bottom (down) nothing changes. Returns the new weights."""
    order = priorities(w)["order"]
    i = order.index(feature)
    j = i - 1 if direction == "up" else i + 1
    if j < 0 or j >= len(order):
        return list(w)
    a, b = FEATURES.index(feature), FEATURES.index(order[j])
    w2 = list(w)
    if q(w2[a]) != q(w2[b]):
        w2[a], w2[b] = w2[b], w2[a]
        return w2
    w2[a] = max(0.0, w2[b] + (NUDGE_TIE_STEP if direction == "up" else -NUDGE_TIE_STEP))
    s = sum(w2)
    return [x / s for x in w2]


def task_display(task, params):
    attrs = {a["id"]: a for a in params["conjoint"]["attributes"]}
    h = task_headlines(task, params)
    return {"headline_a": h["a"], "headline_b": h["b"],
            "rows": [{"attribute": attrs[k]["label"], "a": attrs[k]["levels"][a]["text"], "b": attrs[k]["levels"][b]["text"]} for k, a, b in task]}


def conjoint_examples(samples, buildings, params):
    out = []
    for name, hw in PERSONAS:
        hidden = [hw[k] for k in FEATURES] if hw else None
        ans = run_conjoint(samples, params, lambda t: task_answer(t, hidden, params))
        rec = recommend(samples, ans, buildings, params)
        pr = priorities(rec["weights"], flat_threshold(samples))
        out.append({"persona": name, "hidden_weights": dict(zip(FEATURES, hidden)) if hidden else None,
                    "answer_rule": "either to every task" if hidden is None else
                    f"the apartment with the higher utility under hidden_weights; 'either' when the gap is within {params['either_band']}",
                    "answers": [{"task_index": x["task_index"], "task": x["task"], "choice": x["choice"]} for x in ans],
                    "expected_tasks": [x["task_index"] for x in ans],
                    "expected_tasks_shown": [task_display(x["task"], params) for x in ans],
                    "expected_mean_weights": dict(zip(FEATURES, rec["weights"])),
                    "expected_priorities": pr["order"], "expected_priorities_sentence": pr["sentence"], "expected_flat": pr["flat"],
                    "expected_top": [[n["neighborhood_id"], [b["id"] for b in n["buildings"]]] for n in rec["neighborhoods"]],
                    "expected_more_like_this": {b["id"]: b["more_like_this"] for n in rec["neighborhoods"] for b in n["buildings"]},
                    "expected_why": {n["neighborhood_id"]: n["why"] for n in rec["neighborhoods"]},
                    "expected_gives_up": {n["neighborhood_id"]: n["gives_up"] for n in rec["neighborhoods"]}})
    # the nudge, on the first persona: move its second priority up one place
    e = out[0]
    w = [e["expected_mean_weights"][k] for k in FEATURES]
    k = e["expected_priorities"][1]
    w2 = nudge(w, k, "up")
    rec2 = recommend_from_weights(w2, buildings, params)
    out[0]["nudge_example"] = {"feature": k, "direction": "up", "weights_after": dict(zip(FEATURES, [round(x, 6) for x in w2])),
                               "priorities_sentence_after": priorities(w2, flat_threshold(samples))["sentence"],
                               "expected_top_after": [[n["neighborhood_id"], [b["id"] for b in n["buildings"]]] for n in rec2["neighborhoods"]]}
    return out


def data_version(params, samples):
    """A short hash of what saved answers depend on: the conjoint pool, n_tasks, the levels and the recommender
    parameters that read answers (features, value functions, temperature, band, prior, seed) and the samples. A page
    discards answers saved under another version."""
    import hashlib
    cj = params["conjoint"]
    blob = {"pool": cj["pool"], "n_tasks": cj["n_tasks"], "prefilter": cj["prefilter"],
            "levels": [[a["id"], [x["value"] for x in a["levels"]]] for a in cj["attributes"]],
            "params": {k: params[k] for k in ("features", "value_functions", "temperature", "either_band", "seed", "prior",
                                              "min_buildings", "relevance_floor", "mmr_lambda")},
            "samples": samples}
    return "v4-" + hashlib.sha1(json.dumps(blob, sort_keys=True).encode()).hexdigest()[:10]


def conjoint_block(buildings):
    attrs = conjoint_attributes(buildings)
    return {"attributes": attrs, "n_tasks": N_TASKS, "prefilter": POOL_PREFILTER, "pool": build_pool(attrs),
            "answers": {"a": "Apartment A", "b": "Apartment B", "either": "No real difference to me"},
            "pool_rules": build_pool.__doc__.strip(), "headline_rule": task_headlines.__doc__.strip(), "gain_words": GAIN, "cost_words": COST, "selection": next_task.__doc__.strip(),
            "levels_rule": conjoint_attributes.__doc__.strip(), "priorities_rule": priorities.__doc__.strip(),
            "nudge_rule": nudge.__doc__.strip(), "priority_words": PRIORITY_WORDS,
            "flat_rule": flat_threshold.__doc__.strip(), "lean_step": LEAN_STEP}


class FastCJ:
    """next_task and posterior of version 4, vectorised with numpy, for simulating many users. Tested to choose the
    same tasks as the reference. Not part of the page's contract."""

    def __init__(self, samples, params):
        import numpy as np
        self.np, self.p = np, params
        self.W = np.array(samples, dtype=float)
        lv = _level_values(params)
        self.pool = params["conjoint"]["pool"]
        D = np.zeros((len(self.pool), len(FEATURES)))
        for i, t in enumerate(self.pool):
            for k, a, b in t:
                D[i, FEATURES.index(k)] += lv[k][a] - lv[k][b]
        self.D = D
        self.G = D @ self.W.T                                   # tasks x samples
        self.keys = [_key(t) for t in self.pool]
        self.sets = [frozenset(k for k, _, _ in t) for t in self.pool]

    def L(self, g):
        np, p = self.np, self.p
        pa = 1 / (1 + np.exp(-(g - p["either_band"]) / p["temperature"]))
        pb = 1 / (1 + np.exp(-(-g - p["either_band"]) / p["temperature"]))
        return pa, pb, np.maximum(0, 1 - pa - pb)

    def pi(self, answers):
        np = self.np
        lp = np.ones(self.W.shape[0])
        for x in answers:
            pa, pb, pe = self.L(self.G[x["task_index"]])
            lp = lp * {"a": pa, "b": pb, "either": pe}[x["choice"]]
        s = lp.sum()
        return lp / s if s > 0 else np.full(len(lp), 1 / len(lp))

    def next_task(self, answers):
        np, cj = self.np, self.p["conjoint"]
        if len(answers) >= cj["n_tasks"]:
            return None
        pi = self.pi(answers)
        w = pi @ self.W
        asked_pairs = {frozenset(k for k, _, _ in x["task"]) for x in answers}
        counts = Counter(k for x in answers for k, _, _ in x["task"])
        gb = np.round(np.abs(self.D @ w), ROUND)
        cand = [i for i in range(len(self.pool)) if self.sets[i] not in asked_pairs]
        if not cand:
            return None
        least = min(coverage_rank(self.pool[i], counts) for i in cand)
        cand = [i for i in cand if coverage_rank(self.pool[i], counts) == least]
        cand.sort(key=lambda i: (gb[i], i))
        cand = sorted(cand[:cj["prefilter"]])
        gain = 0
        for L in self.L(self.G[cand]):
            m = L * pi
            P = m.sum(axis=1)
            M = m @ self.W
            with np.errstate(divide="ignore", invalid="ignore"):
                gain = gain + np.where(P > 0, (M * M).sum(axis=1) / P, 0.0)
        gain = np.round(gain, ROUND)
        return cand[int(np.argmax(gain))]

    def run(self, answer_fn):
        answers = []
        while True:
            i = self.next_task(answers)
            if i is None:
                return answers
            answers.append({"task_index": i, "task": self.pool[i], "choice": answer_fn(self.pool[i])})


# ================================================================ VERSION 5: no questions; the default list and leanings

LEAN_WORDS = {"family": "being near Mom and Dad", "money": "the monthly cost", "room": "space", "going_out": "going out",
              "green": "a park for the dog", "parking": "parking"}


def default_recommendation(samples, buildings, params, hoods):
    """recommend_from_weights at the prior mean weights (the mean of the samples), with each neighborhood's tags and
    building names."""
    w = mean_weights(samples, [1 / len(samples)] * len(samples))
    rec = recommend_from_weights(w, buildings, params)
    hn = {h["id"]: h for h in hoods}
    by = {b["id"]: b for b in buildings}
    for n in rec["neighborhoods"]:
        n["tags"] = hn[n["neighborhood_id"]]["tags"]
        for b in n["buildings"]:
            b["name"] = by[b["id"]]["name"]
            b["neighborhood_name"] = by[b["id"]]["neighborhood_name"]
    return rec


def leanings(buildings, params, hoods, default_ids):
    """For each priority alone (its weight 1, the rest 0): the recommendable neighborhood with the highest score
    (scripts/recommender_frontier.py's rule), with a plain line. in_default_three marks a winner already among the
    default three (kept, so nothing is hidden; the page may leave those out)."""
    names = {h["id"]: h["name"] for h in hoods}
    out = []
    for i, k in enumerate(FEATURES):
        w = [0.0] * len(FEATURES)
        w[i] = 1.0
        g = best_group(w, buildings, params)
        out.append({"priority_key": k, "priority_label": LEAN_WORDS[k], "neighborhood_id": g, "neighborhood_name": names[g],
                    "line": f"If {LEAN_WORDS[k]} matters most: {names[g]}", "in_default_three": g in default_ids})
    return out


def add_version_five(out, samples, buildings, params):
    rec = default_recommendation(samples, buildings, params, out["neighborhoods"])
    out["meta"]["default_recommendation"] = rec
    out["meta"]["leanings"] = leanings(buildings, params, out["neighborhoods"], {n["neighborhood_id"] for n in rec["neighborhoods"]})
