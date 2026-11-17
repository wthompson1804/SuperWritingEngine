"""A stand-in for site/concierge_data.json, for building and testing the concierge page before the real file exists.

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


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
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
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{OUT}: {out['meta']['counts']}, parked: {sum(1 for h in hoods if h['parked_under'])}")


if __name__ == "__main__":
    main()
