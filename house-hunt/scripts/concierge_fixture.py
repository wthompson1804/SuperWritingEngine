"""A stand-in for site/concierge_data.json, for building and testing the concierge page before the real file exists.

Version 2: when site/concierge_data.json exists (the real version 1 data) it is the base, and the version 2 fields
(questions, buildings[].fit / fit_chips / fit_misses / experience_line / life_here, experiences[].line, meta.matching,
meta.matching_examples) are added as plainly marked stand-ins computed from figures in site/data.json. Otherwise the
version 1 stand-in below is built first.

Reads site/data.json and writes site/_concierge_fixture.json in the shape of the data contract in
docs/CONCIERGE_DESIGN.md. It is a TEST FIXTURE: the sentences in `why`, `give_up`, the story cards and the either/or
questions are simple stand-ins made here, not the reviewed text. scripts/concierge_data.py writes the real file, and
scripts/build_concierge.py uses that one whenever it exists.

    python3 scripts/concierge_fixture.py
"""
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "site" / "data.json"
OUT = ROOT / "site" / "_concierge_fixture.json"
RENT_LIMIT = 2000
TODAY = "2026-11-17"


def clamp(x):
    return max(0.0, min(1.0, x))


def rng(xs):
    xs = [x for x in xs if x is not None]
    return [min(xs), max(xs)] if xs else None


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def checked(u):
    """A made-up re-read result so the page's three states can be tested: by a stable hash of the id, about a third
    confirmed today, a few re-priced, the rest last seen on the day the price was read."""
    n = int(hashlib.md5(u["id"].encode()).hexdigest(), 16) % 10
    seen = (u.get("price_seen_at") or "")[:10] or None
    if n < 3:
        return {"status": "confirmed_today", "date": TODAY, "note": None}
    if n == 3:
        return {"status": "price_changed_today", "date": TODAY, "note": "fixture"}
    return {"status": "last_seen", "date": seen, "note": None}


def build_v1(d):
    """The version 1 stand-in, built from site/data.json (used only when site/concierge_data.json does not exist)."""
    units = [u for u in d["units"]
             if isinstance(u.get("rent"), dict) and u["rent"].get("listed") is not None
             and u["rent"]["listed"] <= RENT_LIMIT and u.get("all_in") is not None]
    hoods_src = {h["id"]: h for h in d["neighborhoods"]}
    b_src = {b["id"]: b for b in d["buildings"]}
    by_b = {}
    for u in units:
        by_b.setdefault(u["building_id"], []).append(u)

    buildings = []
    for bid, us in sorted(by_b.items()):
        us.sort(key=lambda u: (-(u["scores"]["rank"] or 0), u["id"]))
        b, top = b_src.get(bid, {}), us[0]
        h = hoods_src.get(top["hood_id"], {})
        sun, wake, after = top["moments"].get("sun", {}), top["moments"].get("wake", {}), top["moments"].get("after", {})
        drive = sun.get("drive_min") if sun.get("drive_min") is not None else h.get("drive_min")
        toll = sun.get("toll_round_trip") if sun.get("toll_round_trip") is not None else h.get("toll_round_trip")
        park = top.get("parking") or {}
        dog = top.get("dog") or {}
        total_from = min(u["all_in"] for u in us)
        scores = {
            "parents": clamp(1 - (drive or 120) / 120),
            "going_out": clamp((after.get("restaurants_800m") or 0) / 25),
            "green": clamp(1 - (wake.get("park_walk_min") or 20) / 20),
            "value": clamp((2700 - total_from) / 900),
            "parking": clamp((park.get("rank") or 0) / 4),
            "home": clamp(((top.get("sqft") or 500) - 400) / 500),
        }
        words = {"parents": ("It is a short drive to Mom and Dad.", "It is a long drive to Mom and Dad."),
                 "going_out": ("Dinner and a drink are a short walk away.", "Going out to dinner means driving."),
                 "green": ("A park is a few minutes on foot.", "The nearest park is a long walk."),
                 "value": ("The total each month is among the lowest here.", "The total each month is among the higher ones here."),
                 "parking": ("Parking at the building is easy.", "Ask where the car would go."),
                 "home": ("There is room for a proper desk.", "The apartment is on the small side.")}
        order = sorted(scores, key=lambda k: (-scores[k], k))
        c = top.get("confirm") or {}
        confirm = [{"label": c.get("label"), "question": c.get("question")}] if c.get("asterisk") and c.get("question") else []
        tq = []
        for u in us:
            for q in u.get("tour_questions") or []:
                if q not in tq and q not in [x["question"] for x in confirm]:
                    tq.append(q)
        ct = b.get("contact") or {}
        phone_ok = ct.get("kind") in ("leasing office", "management company") and "tracking" not in (ct.get("note") or "")
        day_titles = {"wake": "Morning walk", "work": "Working from home", "after": "After work", "night": "Coming home at night",
                      "sat": "Saturday night", "sun": "Sunday with Mom and Dad"}
        day_text = {
            "wake": (f"{wake.get('park')} is about {round(wake['park_walk_min'])} minutes on foot." if wake.get("park") and wake.get("park_walk_min") is not None else None),
            "work": (f"About {round(top['sqft'])} square feet." if top.get("sqft") else None),
            "after": (f"{after.get('restaurants_800m')} restaurants within a 10-minute walk." if after.get("restaurants_800m") is not None else None),
            "night": (park.get("summary")),
            "sat": None,
            "sun": (f"About {round(drive)} minutes by car." if drive is not None else None),
        }
        day = [{"title": day_titles[k], "text": day_text[k], "level": (top["moments"].get(k) or {}).get("rating")}
               for k in ("wake", "work", "after", "night", "sat", "sun") if top["moments"].get(k)]
        apartments = []
        for u in us:
            uc = u.get("confirm") or {}
            apartments.append({
                "id": u["id"], "label": ("Apartment " + str(u["unit"])) if u.get("unit") else "Apartment",
                "beds": u.get("beds"), "sqft": u.get("sqft"),
                "floor_text": (f"Floor {int(u['floor'])}" if isinstance(u.get("floor"), (int, float)) else None),
                "rent": u["rent"]["listed"], "total": u["all_in"],
                "available_text": "Available now" if u.get("available") == "now" else (f"Available {u['available']}" if u.get("available") else None),
                "offer": None, "star": bool(uc.get("asterisk")),
                "confirm_label": (f"To confirm: {uc['label']}" if uc.get("asterisk") and uc.get("label") else None),
                "listing_url": (u.get("links") or {}).get("listing"), "source_site": u.get("source_site"),
                "last_read": u.get("price_seen_at"), "checked": checked(u)})
        buildings.append({
            "id": bid, "name": b.get("name") or top.get("building"), "address": b.get("address") or top.get("address"),
            "city": b.get("city"), "state": b.get("state"), "lat": b.get("lat"), "lon": b.get("lon"),
            "neighborhood_id": top["hood_id"], "experience_id": top["year"], "rank_score": top["scores"]["rank"],
            "why": words[order[0]][0], "give_up": words[order[-1]][1],
            "facts": {"rent_from": min(u["rent"]["listed"] for u in us), "rent_to": max(u["rent"]["listed"] for u in us),
                      "total_from": total_from, "total_to": max(u["all_in"] for u in us),
                      "drive_min": drive, "toll_round_trip": toll,
                      "parking": {"summary": park.get("summary"), "kind": park.get("kind"), "fee": park.get("fee")},
                      "dog": {"summary": ("Dogs are allowed" + (f", up to {int(dog['weight_limit_lb'])} lb." if isinstance(dog.get("weight_limit_lb"), (int, float)) else (", with no weight limit." if dog.get("weight_limit_lb") == "no limit" else "; ask for the weight limit."))),
                              "weight_limit_lb": dog.get("weight_limit_lb") if isinstance(dog.get("weight_limit_lb"), (int, float)) else None}},
            "scores": {k: round(v, 3) for k, v in scores.items()},
            "confirm": confirm, "tour_questions": tq[:6],
            "disclosures": [x.get("label") for x in (top.get("disclosures") or []) if x.get("label")],
            "photos_url": (b.get("photos") or {}).get("url"), "listing_url": (top.get("links") or {}).get("listing"),
            "contact": ({"office_phone": ct.get("phone") if phone_ok else None, "site": ct.get("site")} if ct else None),
            "about": b.get("about_building"), "points": b.get("about_points") or [], "checked_summary": None,
            "day": day, "apartments": apartments})

    # neighborhoods; one-apartment neighborhoods are parked under the nearest larger one in the same experience
    by_h = {}
    for b in buildings:
        by_h.setdefault(b["neighborhood_id"], []).append(b)
    n_apts = {hid: sum(len(b["apartments"]) for b in bs) for hid, bs in by_h.items()}
    hoods = []
    for hid, bs in sorted(by_h.items()):
        h = hoods_src.get(hid, {})
        hoods.append({"id": hid, "name": h.get("name") or hid, "state": h.get("state"), "experience_id": bs[0]["experience_id"],
                      "lat": h.get("lat"), "lon": h.get("lon"), "drive_min": h.get("drive_min"),
                      "toll_round_trip": h.get("toll_round_trip"), "about": (h.get("host") or {}).get("intro"),
                      "points": h.get("about_points") or [], "parked_under": None, "parked_distance_km": None, "parked_label": None, "also_nearby": [],
                      "building_ids": [b["id"] for b in sorted(bs, key=lambda b: (-b["rank_score"], b["id"]))]})
    H = {h["id"]: h for h in hoods}
    for h in hoods:
        if n_apts[h["id"]] != 1:
            continue
        hosts = [o for o in hoods if o["experience_id"] == h["experience_id"] and n_apts[o["id"]] > 1]
        if not hosts or h["lat"] is None:
            continue
        host = min(hosts, key=lambda o: (math.hypot((o["lat"] - h["lat"]), (o["lon"] - h["lon"]) * 0.76), o["id"]))
        h["parked_under"] = host["id"]
        km = math.hypot((host["lat"] - h["lat"]) * 111.0, (host["lon"] - h["lon"]) * 84.4)
        h["parked_distance_km"] = round(km, 1)
        h["parked_label"] = "Also nearby" if km <= 15 else "Also in this kind of life"
        H[host["id"]]["also_nearby"].append(h["id"])

    experiences = []
    for y in d["years"]:
        bs = [b for b in buildings if b["experience_id"] == y["id"]]
        if not bs:
            continue
        ap = [a for b in bs for a in b["apartments"]]
        fig = {"rent_median": med([a["rent"] for a in ap]), "rent_range": rng([a["rent"] for a in ap]),
               "total_median": med([a["total"] for a in ap]), "total_range": rng([a["total"] for a in ap]),
               "drive_min_median": med([b["facts"]["drive_min"] for b in bs]), "drive_min_range": rng([b["facts"]["drive_min"] for b in bs]),
               "toll_round_trip_range": rng([b["facts"]["toll_round_trip"] for b in bs]),
               "apartments": len(ap), "buildings": len(bs)}
        prose = y.get("prose") or {}
        story = [{"kind": "promise", "title": (y.get("display_label") or y["label"]), "text": prose.get("promise") or y.get("tagline"), "icon": "home"}]
        for m, kind in zip(y.get("day_moments") or [], ("weekday", "saturday", "sunday")):
            story.append({"kind": kind, "title": m.get("title"), "text": m.get("text"), "icon": m.get("icon")})
        story.append({"kind": "cost", "title": "What it costs",
                      "text": f"Rent is typically about ${round(fig['rent_median']):,} a month. With utilities and fees the total is typically about ${round(fig['total_median']):,}.",
                      "icon": "coin"})
        if prose.get("catch"):
            story.append({"kind": "catch", "title": "The catch", "text": prose["catch"], "icon": "warning"})
        experiences.append({"id": y["id"], "label": y.get("display_label") or y["label"], "tagline": y.get("tagline"),
                            "illustration_id": y["id"], "figures": fig, "story": story,
                            "neighborhood_ids": [h["id"] for h in sorted(hoods, key=lambda h: (h["drive_min"] or 999, h["id"])) if h["experience_id"] == y["id"]]})

    either_or = [
        {"id": "parents_or_out", "question": "Which matters more next year?",
         "a": {"label": "A shorter drive to Mom and Dad", "weight": {"parents": 30}},
         "b": {"label": "Dinner and drinks a walk from the door", "weight": {"going_out": 30}}},
        {"id": "money_or_room", "question": "Where should the money go?",
         "a": {"label": "The lowest total each month", "weight": {"value": 30}},
         "b": {"label": "More room for a desk and the dog", "weight": {"home": 30}}},
        {"id": "green_or_garage", "question": "And for everyday life?",
         "a": {"label": "A park close by for dog walks", "weight": {"green": 30}},
         "b": {"label": "A garage for the car", "weight": {"parking": 30}}},
    ]
    out = {"meta": {"built_at": d["meta"].get("built_at"), "rent_limit": RENT_LIMIT, "fixture": True,
                    "counts": {"apartments": sum(len(b["apartments"]) for b in buildings), "buildings": len(buildings),
                               "neighborhoods": len(hoods), "experiences": len(experiences)},
                    "tour_start": "2026-11-22", "move_in_by": "2026-12-15", "anchor_label": "Mom and Dad",
                    "anchor": {"lat": d["meta"]["anchor"]["lat"], "lon": d["meta"]["anchor"]["lon"]}},
           "experiences": experiences, "neighborhoods": hoods, "buildings": buildings, "either_or": either_or}
    return out

# ======================================================================================================================
# Version 2 additions (docs/CONCIERGE_DESIGN.md, "Version 2"). FIXTURE ONLY: the questions, their wording, weights and
# thresholds, the chip and miss sentences, the experience lines and the "Life here" moments are stand-ins written here
# from figures already in site/data.json, so the page can be built and tested before scripts/concierge_data.py writes
# the reviewed ones. Every number in them is read from the data; nothing is researched or invented.
# ======================================================================================================================
EXP_LINE = {  # fixture wording, condensed from each experience's own tagline and "about" text
    "space": "Towns farther out: more room for you and a desk, and a longer drive to Mom and Dad.",
    "middle": "A small city with a downtown to walk to, and a longer drive to Mom and Dad.",
    "settled": "An older city neighborhood with errands on foot, close to Mom and Dad.",
}


def a(id_, label, sublabel=None, filt=None, weights=None, **extra):
    o = {"id": id_, "label": label, "sublabel": sublabel, "filter": filt, "weights": weights or {}}
    o.update(extra)
    return o


QUESTIONS = [
    {"id": "visits", "kind": "single", "must_have": False, "text": "How often will you see Mom and Dad?",
     "help": "Think of a normal month next year.",
     "answers": [a("visits_weekly", "Every week", "Sunday dinner, most weeks", None, {"parents": 20}, per_month=4),
                 a("visits_twice", "Twice a month", "Every other weekend", None, {"parents": 10}, per_month=2),
                 a("visits_monthly", "About once a month", "Holidays and birthdays, and a visit in between", None, {"parents": 4}, per_month=1)]},
    {"id": "longest_drive", "kind": "single", "must_have": True, "text": "What is the longest drive you would make to see them?",
     "help": "Each way, with no traffic.",
     "answers": [a("drive_30", "Half an hour", "30 minutes or less", {"field": "drive_min", "op": "<=", "value": 30}, {"parents": 5}),
                 a("drive_45", "45 minutes", "Up to three quarters of an hour", {"field": "drive_min", "op": "<=", "value": 45}, {"parents": 5}),
                 a("drive_60", "An hour", "Up to 60 minutes", {"field": "drive_min", "op": "<=", "value": 60}, {"parents": 5}),
                 a("drive_90", "An hour and a half", "Up to 90 minutes", {"field": "drive_min", "op": "<=", "value": 90}, {"parents": 5}),
                 a("drive_any", "Any drive is fine", "Up to two hours", None, {})]},
    {"id": "room", "kind": "single", "must_have": True, "text": "When you work from home, what do you need?",
     "help": None,
     "answers": [a("room_bedroom", "A separate bedroom", "A door between work and sleep", {"field": "has_one_bedroom", "op": "==", "value": True}, {"home": 10}),
                 a("room_studio", "A studio with room for a desk", "One room is fine if it is a good size", None, {"home": 4}),
                 a("room_either", "Either works", None, None, {})]},
    {"id": "saturday", "kind": "single", "must_have": False, "text": "A good Saturday night looks like…",
     "help": None,
     "answers": [a("sat_walk", "Walking out to dinner and drinks", "Restaurants and bars a few minutes away", None, {"going_out": 20}),
                 a("sat_drive", "Driving somewhere good", "Fine with a short drive for a night out", None, {"going_out": 5, "parking": 5}),
                 a("sat_home", "Staying in, friends over", "A comfortable place to host", None, {"home": 10})]},
    {"id": "dog", "kind": "single", "must_have": False, "text": "The dog's daily walk?",
     "help": None,
     "answers": [a("dog_park", "A park to walk to", "Green space a few minutes away", None, {"green": 20}),
                 a("dog_building", "A dog area in the building", "A run or dog park on site", None, {"green": 5}),
                 a("dog_either", "Either is fine", None, None, {})]},
    {"id": "car", "kind": "single", "must_have": False, "text": "Where does the car sleep?",
     "help": None,
     "answers": [a("car_garage", "In a garage, even if it costs extra", "Covered and out of the snow", None, {"parking": 20}),
                 a("car_offstreet", "Any spot off the street", "A lot or a driveway is fine", None, {"parking": 10}),
                 a("car_street", "The street is fine", None, None, {})]},
    {"id": "budget", "kind": "single", "must_have": True, "text": "What monthly total feels comfortable?",
     "help": "Rent plus utilities and fees, every month.",
     "answers": [a("total_1900", "$1,900 or less", None, {"field": "min_total", "op": "<=", "value": 1900}, {"value": 5}),
                 a("total_2100", "$2,100 or less", None, {"field": "min_total", "op": "<=", "value": 2100}, {"value": 5}),
                 a("total_2300", "$2,300 or less", None, {"field": "min_total", "op": "<=", "value": 2300}, {"value": 5}),
                 a("total_any", "Anything shown here", "Every rent here is $2,000 or less", None, {})]},
    {"id": "priorities", "kind": "pick_two", "must_have": False, "text": "Which two matter most?",
     "help": "Pick up to two. They count double.",
     "answers": [a("pri_parents", "Being close to Mom and Dad", None, None, {"parents": 15}),
                 a("pri_out", "Going out nearby", None, None, {"going_out": 15}),
                 a("pri_green", "A park for the dog", None, None, {"green": 15}),
                 a("pri_value", "A lower monthly total", None, None, {"value": 15}),
                 a("pri_room", "Room to work", None, None, {"home": 15}),
                 a("pri_car", "Easy parking", None, None, {"parking": 15})]},
]

MATCHING = {
    "fixture": True,
    "base": "rank_score",
    "priority_multiplier": 2,
    "confirmed_bonus": 8,
    "unknown_passes": True,
    "formula": ("score = rank_score + for each answered single question, for each key k of the answer's weights: "
                "weight x scores[k], multiplied by priority_multiplier when k is a key of a chosen pick_two answer's "
                "weights; + for each chosen pick_two answer: weight x scores[k]; + confirmed_bonus when at least one "
                "apartment's checked.status is confirmed_today or price_changed_today. Questions in data order, keys in "
                "the order given."),
    "filters": ("a building fails when any answered question's chosen answer has a filter {field, op, value} that is "
                "false on buildings[].fit; a null field passes (an unknown is not a miss); ops: <=, <, >=, >, ==, !=, in"),
    "order": "fits by score descending, ties by id ascending; failing buildings the same way, shown apart with reasons",
    "answers_shape": "{question id: answer id} for single, {question id: [answer ids]} for pick_two; skipped = absent",
}

TODAY_STATUS = ("confirmed_today", "price_changed_today")


def passes(fit, f):
    if not f:
        return True
    v = fit.get(f["field"])
    if v is None:
        return True
    op, x = f["op"], f["value"]
    return {"<=": lambda: v <= x, "<": lambda: v < x, ">=": lambda: v >= x, ">": lambda: v > x,
            "==": lambda: v == x, "!=": lambda: v != x, "in": lambda: v in x}[op]()


def match(buildings, questions, answers, m):
    mult, bonus = m["priority_multiplier"], m["confirmed_bonus"]
    pri = []
    for q in questions:
        if q["kind"] == "pick_two":
            for aid in answers.get(q["id"]) or []:
                an = next((x for x in q["answers"] if x["id"] == aid), None)
                if an:
                    pri.extend(k for k in an["weights"] if k not in pri)
    fits, fails = [], []
    for b in buildings:
        s, failed = b["rank_score"] or 0, []
        for q in questions:
            got = answers.get(q["id"])
            if got is None:
                continue
            if q["kind"] == "pick_two":
                for aid in got:
                    an = next((x for x in q["answers"] if x["id"] == aid), None)
                    for k, w in (an or {}).get("weights", {}).items():
                        s += w * (b["scores"].get(k) or 0)
                continue
            an = next((x for x in q["answers"] if x["id"] == got), None)
            if not an:
                continue
            for k, w in an["weights"].items():
                s += w * (b["scores"].get(k) or 0) * (mult if k in pri else 1)
            if an.get("filter") and not passes(b["fit"], an["filter"]):
                failed.append(an["id"])
        if any((ap.get("checked") or {}).get("status") in TODAY_STATUS for ap in b["apartments"]):
            s += bonus
        (fails if failed else fits).append((s, b["id"]))
    key = lambda t: (-t[0], t[1])
    return [i for _, i in sorted(fits, key=key)], [i for _, i in sorted(fails, key=key)]


def money(v):
    return f"${round(v):,}"


def add_v2(out, d):
    units = {}
    for u in d["units"]:
        units.setdefault(u["building_id"], []).append(u)
    for b in out["buildings"]:
        us = sorted(units.get(b["id"], []), key=lambda u: -(u["scores"].get("rank") or 0))
        top = us[0] if us else {}
        mo = top.get("moments") or {}
        wake, work, after, sat, sun = (mo.get(k) or {} for k in ("wake", "work", "after", "sat", "sun"))
        f, ap = b["facts"], b["apartments"]
        pk = (f.get("parking") or {}).get("kind")
        am = top.get("amenities") or {}
        beds = [x.get("beds") for x in ap]
        fit = {"drive_min": f.get("drive_min"), "toll_round_trip": f.get("toll_round_trip"),
               "has_one_bedroom": any(x == 1 for x in beds), "has_studio": any(x == 0 for x in beds),
               "studio_only": bool(beds) and all(x == 0 for x in beds),
               "min_total": f.get("total_from"), "max_total": f.get("total_to"), "parking_kind": pk,
               "garage_or_covered": (pk in ("garage", "covered")) if pk else None,
               "off_street": (pk in ("garage", "covered", "lot", "off_street")) if pk else None,
               "dog_area_in_building": am.get("dog_park_or_run") if isinstance(am.get("dog_park_or_run"), bool) else None,
               "park_walk_min": wake.get("park_walk_min"), "park_name": wake.get("park"),
               "restaurants_10min": after.get("restaurants_800m"), "bars_10min": after.get("bars_800m"),
               "cafes_10min": after.get("cafes_800m")}
        b["fit"] = fit
        dm, toll, tot = fit["drive_min"], fit["toll_round_trip"], fit["min_total"]
        sq1 = max([x["sqft"] for x in ap if x.get("beds") == 1 and x.get("sqft")] or [0]) or None
        sq0 = max([x["sqft"] for x in ap if x.get("beds") == 0 and x.get("sqft")] or [0]) or None
        chips, misses = {}, {}
        if dm is not None:
            mins = f"{round(dm)} minutes to Mom and Dad"
            for aid, lim in (("visits_weekly", 45), ("visits_twice", 60), ("visits_monthly", 90)):
                if dm <= lim:
                    chips[aid] = mins
                else:
                    misses[aid] = f"{round(dm)} minutes each way to Mom and Dad"
            for aid, lim in (("drive_30", 30), ("drive_45", 45), ("drive_60", 60), ("drive_90", 90)):
                if dm <= lim:
                    chips[aid] = mins
                else:
                    misses[aid] = f"{round(dm)} minutes to Mom and Dad, more than your {lim}"
            chips["drive_any"] = mins
        if fit["has_one_bedroom"]:
            chips["room_bedroom"] = "A separate bedroom" + (f", about {round(sq1)} sq ft" if sq1 else "")
        else:
            misses["room_bedroom"] = "Studios only here"
        if fit["has_studio"] and sq0 and sq0 >= 500:
            chips["room_studio"] = f"Studio of about {round(sq0)} sq ft, room for a desk"
        elif fit["has_one_bedroom"]:
            chips["room_studio"] = "A separate bedroom" + (f", about {round(sq1)} sq ft" if sq1 else "")
        elif sq0:
            misses["room_studio"] = f"A small studio, about {round(sq0)} sq ft"
        r = fit["restaurants_10min"]
        if r is not None:
            if r >= 15:
                chips["sat_walk"] = f"{r} restaurants within a 10-minute walk"
            elif r < 8:
                misses["sat_walk"] = f"Only {r} restaurants within a 10-minute walk"
        if fit["off_street"]:
            chips["sat_drive"] = "Parking at the building"
        if (b["scores"].get("home") or 0) >= 0.4:
            chips["sat_home"] = "More room than most here" + (f", about {round(sq1 or sq0)} sq ft" if (sq1 or sq0) else "")
        pw = fit["park_walk_min"]
        if pw is not None:
            if pw <= 6:
                chips["dog_park"] = f"{fit['park_name'] or 'A park'}, {round(pw)} minutes on foot"
            elif pw > 9:
                misses["dog_park"] = f"Nearest park is {round(pw)} minutes on foot"
        if fit["dog_area_in_building"] is True:
            chips["dog_building"] = "A dog area in the building"
        elif fit["dog_area_in_building"] is False:
            misses["dog_building"] = "No dog area in the building"
        fee = (f.get("parking") or {}).get("fee")
        psum = ({"garage": "Garage parking", "covered": "Covered parking", "lot": "A parking lot", "off_street": "Off-street parking"}.get(pk)
                if pk else None)
        if psum and fee:
            psum += f", ${round(fee)} a month"
        if fit["garage_or_covered"]:
            chips["car_garage"] = psum or "Garage parking"
        elif fit["garage_or_covered"] is False:
            misses["car_garage"] = "No garage listed"
        if fit["off_street"]:
            chips["car_offstreet"] = psum or "Parking off the street"
        elif fit["off_street"] is False:
            misses["car_offstreet"] = "Street parking only"
        if tot is not None:
            for aid, lim in (("total_1900", 1900), ("total_2100", 2100), ("total_2300", 2300)):
                if tot <= lim:
                    chips[aid] = f"Total from {money(tot)} a month"
                else:
                    misses[aid] = f"Total from {money(tot)}, over your {money(lim)}"
        b["fit_chips"], b["fit_misses"] = chips, misses
        b["experience_line"] = EXP_LINE.get(b["experience_id"])

        lat, lon = b.get("lat"), b.get("lon")
        osm = {"name": "OpenStreetMap", "url": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=16/{lat}/{lon}"} if lat else None
        life = []
        parts, places = [], []
        if work.get("supermarket") and work.get("supermarket_m"):
            parts.append(f"{work['supermarket']} is the nearest supermarket, about {work['supermarket_m'] / 1609:.1f} miles away.")
            places.append({"name": work["supermarket"], "kind": "supermarket", "walk_min": None, "distance_mi": round(work["supermarket_m"] / 1609, 1)})
        if after.get("cafes_800m"):
            parts.append(f"{after['cafes_800m']} {'cafe' if after['cafes_800m'] == 1 else 'cafes'} within a 10-minute walk.")
        if sat.get("train_station") and sat.get("train_station_m") and sat["train_station_m"] <= 1600:
            wm = max(1, round(sat["train_station_m"] / 80))
            parts.append(f"{sat['train_station']} station is {wm} {'minute' if wm == 1 else 'minutes'} on foot.")
            places.append({"name": sat["train_station"], "kind": "station", "walk_min": wm, "distance_mi": None})
        if parts and osm:
            life.append({"moment": "weekday", "title": "A weekday", "text": " ".join(parts), "places": places, "sources": [osm]})
        if sat.get("restaurants_1600m") is not None and osm:
            rr, bb = sat["restaurants_1600m"], sat.get("bars_1600m") or 0
            t = f"{rr} restaurants and {bb} {'bar' if bb == 1 else 'bars'} within a mile." if bb else f"{rr} restaurants within a mile, and no bars close by."
            life.append({"moment": "saturday", "title": "Saturday night", "text": t, "places": [], "sources": [osm]})
        if sun.get("drive_min") is not None:
            tl = sun.get("toll_round_trip")
            t = f"About {round(sun['drive_min'])} minutes by car with no traffic" + (", and no tolls." if tl == 0 else (f", ${tl:.2f} in tolls round trip." if tl else "."))
            if sun.get("transit_min"):
                t += f" By train and bus, about {round(sun['transit_min'])} minutes."
            src = [{"name": "OSRM drive estimate", "url": "https://project-osrm.org/"}]
            if tl:
                src.append({"name": "E-ZPass New York toll rates", "url": "https://www.e-zpassny.com/"})
            if sun.get("transit_min"):
                src.append({"name": "MTA timetables", "url": "https://new.mta.info/developers"})
            life.append({"moment": "sunday", "title": "Sunday with Mom and Dad", "text": t, "places": [], "sources": src})
        if pw is not None and osm:
            t = (f"{wake['park']} is about {round(pw)} minutes on foot." if wake.get("park") else f"The nearest park is about {round(pw)} minutes on foot.")
            places = [{"name": wake["park"], "kind": "park", "walk_min": round(pw), "distance_mi": None}] if wake.get("park") else []
            src = [osm]
            if fit["dog_area_in_building"]:
                t += " The building has its own dog area."
                if b.get("listing_url"):
                    src.append({"name": "The listing", "url": b["listing_url"]})
            if wake.get("dog_park") and wake.get("dog_park_m"):
                t += f" The nearest dog run is {wake['dog_park']}, about {wake['dog_park_m'] / 1609:.1f} miles away."
                places.append({"name": wake["dog_park"], "kind": "dog run", "walk_min": None, "distance_mi": round(wake["dog_park_m"] / 1609, 1)})
            life.append({"moment": "dog", "title": "The dog's walk", "text": t, "places": places, "sources": src})
        b["life_here"] = life
    for e in out["experiences"]:
        e["line"] = EXP_LINE.get(e["id"])
    out["questions"] = QUESTIONS
    out["meta"]["matching"] = MATCHING
    out["meta"]["fixture_v2"] = "questions, fit, fit_chips, fit_misses, experience_line, life_here and matching are fixture stand-ins"
    examples = [
        ("every question answered", {"visits": "visits_weekly", "longest_drive": "drive_60", "room": "room_either", "saturday": "sat_walk",
                                     "dog": "dog_park", "car": "car_offstreet", "budget": "total_2300", "priorities": ["pri_parents", "pri_out"]}),
        ("only the must-haves, everything else skipped", {"longest_drive": "drive_any", "room": "room_either", "budget": "total_any"}),
        ("tight must-haves leave few", {"longest_drive": "drive_60", "room": "room_bedroom", "budget": "total_2100", "priorities": ["pri_room"]}),
        ("must-haves that leave none", {"longest_drive": "drive_30", "room": "room_bedroom"}),
        ("room and money first", {"visits": "visits_monthly", "longest_drive": "drive_90", "room": "room_studio", "saturday": "sat_home",
                                  "dog": "dog_building", "car": "car_garage", "budget": "total_2100", "priorities": ["pri_value", "pri_room"]}),
    ]
    out["meta"]["matching_examples"] = []
    for name, ans in examples:
        order, failing = match(out["buildings"], QUESTIONS, ans, MATCHING)
        out["meta"]["matching_examples"].append({"name": name, "answers": ans, "order": order, "failing": failing})
    return out


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    real = ROOT / "site" / "concierge_data.json"
    if real.exists():
        out = json.loads(real.read_text(encoding="utf-8"))
        out["meta"]["fixture"] = True
        out["meta"]["fixture_base"] = "site/concierge_data.json (the real version 1 data) plus the fixture's version 2 fields"
    else:
        out = build_v1(d)
    out = add_v2(out, d)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT}: {out['meta']['counts']}, questions: {len(out['questions'])}")
    for ex in out["meta"]["matching_examples"]:
        print(f"  {ex['name']}: {len(ex['order'])} fit, {len(ex['failing'])} do not")


if __name__ == "__main__":
    main()
