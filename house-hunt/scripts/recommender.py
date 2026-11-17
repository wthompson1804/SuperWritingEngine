#!/usr/bin/env python3
"""The short version's recommender, version 3 (docs/CONCIERGE_DESIGN.md "Version 3"): its data and its reference.

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
  neighborhoods[].tags          two plain words from its strongest features against the set ("Lively", "near family")
  recommender_samples           N_SAMPLES weight vectors (FEATURES order), Dirichlet, fixed SEED, rounded to 6 decimals
  meta.recommender              every parameter, the value functions with breakpoints, standardisation, groups and
                                their similarity matrix, the algorithm in words
  meta.recommender_examples     scripted persona runs the page must reproduce exactly

THE MODEL
  utility U_w(b)   = sum_k w_k * features[k]  over the six weighted features (sure excluded)
  score_w(b)       = U_w(b) * features.sure
  group score      = mean of the group's two best building scores; one building: mean of it and the set's median score
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
MIN_PAIRS, MAX_PAIRS, STOP_PROB = 3, 6, 0.8
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
PARKING_VALUE = {"garage": 1.0, "covered": 1.0, "carport": 1.0, "lot": 0.7, "off_street": 0.7, "driveway": 0.7,
                 "surface": 0.7, "street": 0.2}
PARKING_UNKNOWN = 0.4
SURE_TODAY, SURE_EARLIER, SURE_STAR = 1.0, 0.6, 0.8

LABEL = {"family": "being near Mom and Dad", "money": "money left over", "room": "room at home",
         "going_out": "going out", "green": "a park nearby", "parking": "parking"}
TAG_HIGH = {"family": "near family", "money": "good value", "room": "more room", "going_out": "lively",
            "green": "green", "parking": "easy parking"}
TAG_LOW = {"going_out": "quiet"}
PARKING_WORDS = {1.0: "garage or covered parking", 0.7: "off-street parking", 0.4: "parking not stated",
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


def _tags_for(bids, by, mean, sd):
    zs = [zvec(by[i], mean, sd) for i in bids]
    c = [sum(x) / len(zs) for x in zip(*zs)]
    cand = []
    for j, k in enumerate(FEATURES):
        cand.append((q(c[j]), k, TAG_HIGH[k]))
        if k in TAG_LOW:
            cand.append((q(-c[j]), k, TAG_LOW[k]))
    cand.sort(key=lambda t: (-t[0], t[2]))
    first = cand[0]
    second = next(t for t in cand[1:] if t[1] != first[1])
    return [first[2][0].upper() + first[2][1:], second[2]]


def add_tags(neighborhoods, buildings, groups, mean, sd):
    by = {b["id"]: b for b in buildings}
    gm = {g["id"]: g["building_ids"] for g in groups}
    for h in neighborhoods:
        own = [b["id"] for b in buildings if b["neighborhood_id"] == h["id"]]
        bids = gm[h["id"]] if h["id"] in gm else own
        h["tags"] = _tags_for(bids, by, mean, sd) if bids else None


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
            p *= likelihood(utility(by[x["a"]], w) - utility(by[x["b"]], w), x["choice"], params)
        raw.append(p)
    s = sum(raw)
    if s <= 0:
        return [1.0 / len(samples)] * len(samples)
    return [p / s for p in raw]


def mean_weights(samples, pi):
    return [sum(p * w[j] for p, w in zip(pi, samples)) for j in range(len(FEATURES))]


def group_scores(w, buildings, params):
    by = {b["id"]: b for b in buildings}
    sc = {b["id"]: q(score(b, w)) for b in buildings}
    med = statistics.median(sc.values())               # a one-building neighborhood is not a deep one
    out = {}
    for g in params["groups"]:
        s = sorted((sc[i] for i in g["building_ids"]), reverse=True)[:2]
        out[g["id"]] = (s[0] + s[1]) / 2 if len(s) == 2 else (s[0] + med) / 2
    _ = by
    return out


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
    norm = {g: ((gs[g] - lo) / (hi - lo) if hi - lo > 1e-12 else 0.0) for g in gids}
    ok, order = eligible(gs, params)
    k = min(k, len(gids))
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
    by = {b["id"]: b for b in buildings}
    pi = posterior(samples, answers, buildings, params)
    w = mean_weights(samples, pi)
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


def true_top(hidden, buildings, params):
    gs = group_scores(hidden, buildings, params)
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


def params_block(buildings, groups, sim, mean, sd, alpha, meds):
    return {
        "features": list(FEATURES), "sure_feature": "sure",
        "value_functions": value_functions_doc(), "medians_for_missing": meds,
        "temperature": TEMPERATURE, "either_band": EITHER_BAND, "n_samples": N_SAMPLES, "seed": SEED,
        "prior": {"distribution": "Dirichlet", "relative_mass": PRIOR_RELATIVE, "concentration": CONCENTRATION, "alpha": alpha,
                  "draw": "Python random.Random(seed).gammavariate(alpha_k, 1) per feature, normalised, rounded to 6 decimals"},
        "min_pairs": MIN_PAIRS, "max_pairs": MAX_PAIRS, "stop_prob": STOP_PROB, "mmr_lambda": MMR_LAMBDA, "relevance_floor": RELEVANCE_FLOOR, "relevance_top_share": RELEVANCE_TOP_SHARE,
        "pair_pool": PAIR_POOL, "group_km": GROUP_KM, "gives_up_margin": MARGIN, "n_similar": N_SIMILAR, "n_more_like_this": N_MORE, "round_decimals": ROUND, "nudges": list(NUDGES),
        "feature_mean": mean, "feature_sd": sd,
        "groups": [{k: g[k] for k in ("id", "name", "building_ids", "neighborhood_ids")} for g in groups],
        "group_similarity": sim,
        "algorithm": {
            "utility": "U_w(b) = sum_k w_k x features[k] over `features` (sure excluded)",
            "score": "score_w(b) = U_w(b) x features.sure",
            "group_score": "each building's score is rounded to round_decimals; a group with two or more buildings scores the mean of its two best; a group with one building scores the mean of that building and the median building score of the whole set under the same weights (the mean of the two middle values when the count is even), so one strong building is not treated as a deep neighborhood",
            "likelihood": "gap = U_w(a) - U_w(b); P(a) = sig((gap - either_band)/temperature); P(b) = sig((-gap - either_band)/temperature); P(either) = max(0, 1 - P(a) - P(b))",
            "posterior": "pi_s = prod over answers (in order) of the likelihood, divided by the sum over samples; uniform if the sum is 0",
            "mean_weights": "wbar_k = sum_s pi_s x w_s,k; expected utility = U_wbar",
            "eligible": "order groups by round(score) desc, id; eligible = the first, plus any with rank < ceil(n x relevance_top_share) and round(score) >= round(relevance_floor x the first's score); if fewer than 3 are eligible, the recommendation is the eligible ones then the next by score (no diversity)",
            "mmr": "among the eligible groups only (iterated in id order): s' = (score - min)/(max - min) over all groups (all 0 if max - min <= 1e-12); pick 3 greedily by round(lambda x s' - (1 - lambda) x max similarity to the picked, round_decimals), ties to the smaller id; similarity is group_similarity (1 - centroid distance / largest centroid distance, standardised features)",
            "sample_sets": "for each sample, the MMR top three with that sample's weights, as sorted ids joined by '|'; computed once",
            "next_pair": "pool = top pair_pool buildings by round(score_wbar) desc, id; pairs (a, b) with a < b by id, skipping pairs asked; gain = round(H(set distribution under pi) - sum over answers of P(answer) x H(set distribution under the posterior after that answer)); highest gain, ties to the earlier pair in (a, b) id order; entropy in nats",
            "sample_bests": "for each sample, its best group (highest group score with that sample's weights, ties by id); computed once",
            "stop": "stop when answers >= max_pairs, or answers >= min_pairs and round(stop probability) >= stop_prob, where stop probability = sum of pi_s over the samples whose best group is among the current three (MMR on wbar, as recommend). (Changed 2026-11-17 from 'the most probable top-three set has probability >= stop_prob', which almost never holds with ~57 neighborhoods.) The next pair is still chosen by the expected entropy reduction of the top-three set",
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
    add_tags(hoods, blds, groups, mean, sd)
    samples, alpha = draw_samples()
    params = params_block(blds, groups, sim, mean, sd, alpha, meds)
    out["recommender_samples"] = samples
    out["meta"]["recommender"] = params
    sets = sample_sets(samples, blds, params)
    out["meta"]["recommender_examples"] = examples(samples, blds, params, sets, sample_bests(samples, blds, params))
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
