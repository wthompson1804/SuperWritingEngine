#!/usr/bin/env python3
"""Compose the host's line and the honest catch for every unit shown on the page.

The unit list changes with every repair run, so nothing here is hand-written per unit. For each unit in
site/data.json this script reads the unit's own fields, works out which facts are most distinctive (against the other
units shown in the same neighbourhood first, then on their own), and fills one of the sentence patterns below.

  host_line   1 or 2 sentences, at most 45 words: the most distinctive fact, then the price and one or two more facts
  host_catch  1 sentence: the open question (the asterisk) if the unit has one, else what the listing does not
              publish, else the weakest fact
  sub_cost, sub_parking, sub_dog, sub_building   one optional short line (at most 14 words, no numbers) for under each
              section headline of the place; empty when the fields give nothing distinctive to say
  facts_used_json   the pattern chosen and every value that was printed, so each word can be traced to a field

Rules the code keeps (scripts/test_realtor_lines.py checks them):
  * deterministic: the choice among equally good patterns is seeded by listing_id, so a rerun gives the same text;
  * two neighbouring units in a neighbourhood (in rank order) never open with the same pattern;
  * an unknown is never stated as a fact: no parking type means parking is not mentioned in the line and the catch
    says it is not published; a garage with no price is "fee not published", never "free";
  * every number printed is the unit's own field (or the count of units it is compared with), never typed;
  * no crime or safety wording: everything shown has passed the safety rule, so the lines are about living there.

Run from the house-hunt folder:  python3 scripts/realtor_lines.py     (reads site/data.json, read-only)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data.json"
OUT = ROOT / "data" / "reference" / "realtor_lines.csv"
MAX_WORDS = 45
WALK_RADIUS = "10-minute walk"            # the page's wording for the 800 m radius


# ------------------------------------------------------------------ small helpers

def seed(listing_id: str, salt: str = "") -> int:
    return int(hashlib.sha1(f"{listing_id}|{salt}".encode("utf-8")).hexdigest()[:12], 16)


def num(x):
    """A float, or None for anything that is not a usable number."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def whole(x) -> str:
    return f"{int(round(float(x))):,}"


def usd(x) -> str:
    return "$" + whole(x)


def miles(metres) -> str:
    return f"{max(0.1, round(float(metres) / 1609.34, 1)):.1f}"


def get(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def join_and(items):
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:]


def when(avail):
    """'now' -> ('now', None); '2026-12-01' -> ('Dec 1', date)."""
    if not avail:
        return None, None
    if str(avail).lower() == "now":
        return "now", None
    try:
        d = date.fromisoformat(str(avail)[:10])
    except ValueError:
        return None, None
    return f"{d.strftime('%b')} {d.day}", d


# ------------------------------------------------------------------ what a unit's fields say

def parking_kind(u):
    """-> (kind, fee, included). kind is None when the listing publishes nothing about parking."""
    p = u.get("parking") or {}
    t = str(p.get("type") or "").strip().lower()
    if not t:
        return None, None, False
    head = t.split(":")[0].strip()
    kind = "garage" if head.startswith("garage") else "covered" if head.startswith("covered") else \
        "lot" if head in ("lot", "open_lot", "open lot") else "onsite"
    fee = num(p.get("fee"))
    included = fee == 0 and "included or free" in str(p.get("fee_note") or "")
    if fee == 0 and not included:
        fee = None                                   # a zero with no "included" note is not a published price
    return kind, fee, included


def parking_phrase(kind, fee, included):
    name = {"garage": "garage parking", "covered": "covered parking", "lot": "lot parking",
            "onsite": "on-site parking"}[kind]
    if included:
        return "an included parking spot"
    if fee:
        return f"{name} at {usd(fee)} a month"
    return f"{name} (fee not published)"


def dog_amenity(u):
    a = str(get(u, "amenities", "dog_amenities") or "").lower()
    if "no dog run" in a:
        a = a.split(";")[0]
    if "dog park" in a:
        return "a dog park on site"
    if "dog run" in a:
        return "a dog run on site"
    if "pet spa" in a:
        return "a pet spa"
    if "wash" in a:
        return "a dog wash station"
    return None


def facts(u):
    """Everything the patterns may use, read straight from the unit. Missing stays None."""
    am = u.get("amenities") or {}
    kind, fee, included = parking_kind(u)
    floor = num(u.get("floor"))
    label, day = when(u.get("available"))
    free = str(get(u, "rent", "free_months") or "")
    doorman = am.get("doorman")
    return {
        "id": u["id"], "hood": u.get("hood_id"),
        "beds": "studio" if u.get("beds") == 0 else "1-bedroom" if u.get("beds") == 1 else None,
        "all_in": num(u.get("all_in")), "sqft": num(u.get("sqft")),
        "floor": int(floor) if floor and floor >= 2 else None,
        "floor_sure": u.get("floor_basis") in ("confirmed", "stated"),
        "margin": num(get(u, "cost_check", "cap_margin")),
        "park_kind": kind, "park_fee": fee, "park_included": included,
        "pool": bool(am.get("pool")), "gym": am.get("gym") == "yes",
        "doorman": "24-hour" if doorman == "24h" else "yes" if doorman else None,
        "laundry": am.get("in_unit_laundry") == "yes",
        "dog_amenity": dog_amenity(u),
        "dog_park": get(u, "moments", "wake", "dog_park"), "dog_park_m": num(get(u, "moments", "wake", "dog_park_m")),
        "park": get(u, "moments", "wake", "park"), "park_walk": num(get(u, "moments", "wake", "park_walk_min")),
        "avail": label, "avail_date": day,
        "free_months": int(free) if free in ("1", "2", "3") else None,
        "rank": num(get(u, "scores", "hood_rank")),
        "no_weight_limit": str(get(u, "dog", "weight_limit_lb") or "").lower() == "no limit",
    }


def only(f, peers, test):
    return len(peers) >= 2 and test(f) and not any(test(p) for p in peers if p["id"] != f["id"])


def extreme(f, peers, key, best=max):
    """True when this unit alone holds the best value of `key` among peers that publish it (at least 2 do)."""
    vals = [p[key] for p in peers if p[key] is not None]
    if f[key] is None or len(vals) < 2:
        return False
    top = best(vals)
    return f[key] == top and vals.count(top) == 1


def soonest(f, peers):
    """'now' when it is the only unit available now; 'date' when its date is alone the earliest and nothing is now."""
    known = [p for p in peers if p["avail"]]
    if f["avail"] is None or len(known) < 2:
        return None
    nows = [p for p in known if p["avail"] == "now"]
    if f["avail"] == "now":
        return "now" if len(nows) == 1 else None
    if nows:
        return None
    days = [p["avail_date"] for p in known]
    return "date" if f["avail_date"] == min(days) and days.count(min(days)) == 1 else None


# ------------------------------------------------------------------ the pattern library
# Each pattern: (id, fact kind, lead sentence, the values it prints). `n` is the number of units shown in the
# neighbourhood. A pattern is offered only when its fact is true for the unit.

def lead_patterns(f, peers):
    """-> list of (score, pattern_id, kind, text, used). Higher score = more distinctive."""
    n = len(peers)
    two = n == 2
    small = -25 if two else 0                         # "the cheaper of 2" is worth less than "the cheapest of 9"
    out = []

    def add(score, pid, kind, text, **used):
        out.append((score, pid, kind, text, used))

    if only(f, peers, lambda p: p["pool"]):
        add(90 + small, "only_pool_a", "pool", f"The only pool among the {n} places here is this building's.", peers=n, pool=True)
        add(90 + small, "only_pool_b", "pool", f"Of the {n} places in this neighborhood, this is the one with a pool.", peers=n, pool=True)
    if only(f, peers, lambda p: p["park_kind"] == "garage"):
        add(88 + small, "only_garage_a", "parking", f"No other place of the {n} here lists a garage, and this one does.", peers=n, parking="garage")
        add(88 + small, "only_garage_b", "parking", f"Garage parking, the only one of the {n} places here to list it.", peers=n, parking="garage")
    if extreme(f, peers, "all_in", min):
        word = "lower" if two else "lowest"
        add(85 + small, "cheapest_a", "price", f"This is the {word} all-in of the {n} places here, about {usd(f['all_in'])} a month.", peers=n, all_in=f["all_in"])
        add(85 + small, "cheapest_b", "price", f"Start with the number: about {usd(f['all_in'])} a month all in, the {word} of the {n} here.", peers=n, all_in=f["all_in"])
    if extreme(f, peers, "sqft", max):
        word = "roomier" if two else "roomiest"
        add(80 + small, "biggest_a", "size", f"The {word} of the {n} places here, at {whole(f['sqft'])} square feet.", peers=n, sqft=f["sqft"])
        add(80 + small, "biggest_b", "size", f"{whole(f['sqft'])} square feet, more than any other place we found in this neighborhood.", peers=n, sqft=f["sqft"])
    if f["rank"] == 1 and n >= 3:
        add(75, "top_rank_a", "rank", f"On our scorecard this ranks first of the {n} places here.", peers=n, hood_rank=1)
        add(75, "top_rank_b", "rank", f"First of {n} in this neighborhood on the scorecard.", peers=n, hood_rank=1)
    if only(f, peers, lambda p: bool(p["doorman"])):
        add(72 + small, "only_doorman", "doorman", f"The only building of the {n} here with a doorman.", peers=n, doorman=f["doorman"])
    if f["floor_sure"] and extreme(f, peers, "floor", max):
        word = "higher" if two else "highest"
        add(70 + small, "highest_a", "floor", f"Floor {f['floor']}, the {word} of the places we found here.", peers=n, floor=f["floor"])
        add(70 + small, "highest_b", "floor", f"You are up on floor {f['floor']}, above every other place on this neighborhood's list.", peers=n, floor=f["floor"])
    if only(f, peers, lambda p: p["laundry"]):
        add(68 + small, "only_laundry", "laundry", f"The only place of the {n} here with a washer and dryer in the apartment.", peers=n, in_unit_laundry=True)
    s = soonest(f, peers)
    if s == "now":
        add(62 + small, "soonest_now", "date", "Available now, which no other place in this neighborhood is.", peers=n, available="now")
    elif s == "date":
        add(60 + small, "soonest_date", "date", f"Ready {f['avail']}, the earliest date in this neighborhood.", peers=n, available=f["avail"])

    # facts that stand on their own
    if f["park_included"]:
        add(65, "parking_included_a", "parking", "A parking spot comes with the lease, so the car adds nothing to the bill.", parking="included")
        add(65, "parking_included_b", "parking", "Parking is included in the lease here, which is one less thing to negotiate.", parking="included")
    if f["dog_amenity"] and "on site" in f["dog_amenity"]:
        add(58, "dog_onsite_a", "dog", f"The building has {f['dog_amenity'][:-8]} of its own, so the early walk can be an elevator ride.", dog_amenities=f["dog_amenity"])
        add(58, "dog_onsite_b", "dog", f"For the dog: {f['dog_amenity']}.", dog_amenities=f["dog_amenity"])
    if f["park_kind"] == "garage" and not f["park_included"]:
        price = f"at {usd(f['park_fee'])} a month" if f["park_fee"] else "though the fee is not published"
        add(55, "garage_a", "parking", f"The car gets a garage here, {price}.", parking="garage", parking_fee=f["park_fee"])
        tail = f"for {usd(f['park_fee'])} a month" if f["park_fee"] else "though the listing does not publish the fee"
        add(55, "garage_b", "parking", f"Pull in, park in the garage, go upstairs, {tail}.", parking="garage", parking_fee=f["park_fee"])
    if f["free_months"]:
        m = "month" if f["free_months"] == 1 else "months"
        add(52, "concession_a", "offer", f"The listing advertises {f['free_months']} {m} free, so read the lease math carefully.", free_months=f["free_months"])
    if f["sqft"] and f["sqft"] >= 850:
        add(50, "big_a", "size", f"{whole(f['sqft'])} square feet, so the desk gets its own corner.", sqft=f["sqft"])
        add(50, "big_b", "size", f"Room to work from home: {whole(f['sqft'])} square feet.", sqft=f["sqft"])
    if f["pool"]:
        add(50, "pool_a", "pool", "There is a pool, and yes, you would use it.", pool=True)
        add(50, "pool_b", "pool", "A pool comes with the building.", pool=True)
    if f["dog_park_m"] is not None and f["dog_park_m"] <= 800 and f["dog_park"]:
        add(48, "dogpark_near_a", "dog", f"{f['dog_park']} is {miles(f['dog_park_m'])} miles away, close enough for the first walk of the day.", dog_park=f["dog_park"], dog_park_miles=miles(f["dog_park_m"]))
        add(48, "dogpark_near_b", "dog", f"The dog's morning is easy: {f['dog_park']}, {miles(f['dog_park_m'])} miles from the door.", dog_park=f["dog_park"], dog_park_miles=miles(f["dog_park_m"]))
    if f["doorman"]:
        text = "Someone is at the front desk around the clock." if f["doorman"] == "24-hour" else "There is a doorman at the front door."
        add(45, "doorman_a", "doorman", text, doorman=f["doorman"])
    if f["floor"] and f["floor"] >= 10 and f["floor_sure"]:
        add(45, "high_floor", "floor", f"Floor {f['floor']}, well above the street.", floor=f["floor"])
    if f["margin"] is not None and f["margin"] >= 400 and f["all_in"]:
        add(42, "margin_a", "price", f"About {usd(f['all_in'])} a month all in, which leaves about {usd(f['margin'])} under your cap.", all_in=f["all_in"], cap_margin=f["margin"])
    if f["laundry"]:
        add(40, "laundry_a", "laundry", "Washer and dryer inside the apartment, so no laundry-room trips.", in_unit_laundry=True)
    if f["park_kind"] == "covered" and not f["park_included"]:
        price = f"at {usd(f['park_fee'])} a month" if f["park_fee"] else "with the fee not published"
        add(40, "covered_a", "parking", f"Covered parking for the car, {price}.", parking="covered", parking_fee=f["park_fee"])
    if f["park_walk"] is not None and f["park_walk"] <= 5 and f["park"]:
        add(35, "park_near_a", "green", f"{f['park']} is about {whole(max(1, f['park_walk']))} minutes on foot.", park=f["park"], park_walk_min=whole(max(1, f["park_walk"])))
    if f["no_weight_limit"]:
        add(34, "dog_no_limit", "dog", "Dogs are welcome with no weight limit.", dog_weight_limit="no limit")
    if f["park_kind"] == "lot" and not f["park_included"]:
        price = f"at {usd(f['park_fee'])} a month" if f["park_fee"] else "with the fee not published"
        add(30, "lot_a", "parking", f"The car goes in the building's lot, {price}.", parking="lot", parking_fee=f["park_fee"])
    if f["gym"]:
        add(20, "gym_a", "gym", "There is a gym in the building.", gym=True)
    # always available, so there is always a second choice
    kind = f["beds"] or "place"
    article = "A" if kind != "1-bedroom" else "A"
    if f["all_in"]:
        add(5, "basic_a", "price", f"{article} {kind} at about {usd(f['all_in'])} a month all in.", beds=f["beds"], all_in=f["all_in"])
        add(5, "basic_b", "price", f"The plain facts: a {kind}, about {usd(f['all_in'])} a month all in.", beds=f["beds"], all_in=f["all_in"])
    else:
        add(5, "basic_c", "plain", f"A {kind} in this neighborhood, with the all-in cost still to be worked out.", beds=f["beds"])
        add(5, "basic_d", "plain", f"The plain facts: a {kind}, with no all-in figure yet.", beds=f["beds"])
    return out


PATTERN_IDS = [
    "only_pool_a", "only_pool_b", "only_garage_a", "only_garage_b", "cheapest_a", "cheapest_b", "biggest_a", "biggest_b",
    "top_rank_a", "top_rank_b", "only_doorman", "highest_a", "highest_b", "only_laundry", "soonest_now", "soonest_date",
    "parking_included_a", "parking_included_b", "dog_onsite_a", "dog_onsite_b", "garage_a", "garage_b", "concession_a",
    "big_a", "big_b", "pool_a", "pool_b", "dogpark_near_a", "dogpark_near_b", "doorman_a", "high_floor", "margin_a",
    "laundry_a", "covered_a", "park_near_a", "dog_no_limit", "lot_a", "gym_a", "basic_a", "basic_b", "basic_c", "basic_d",
]


def support_phrases(f, lead_kind, lead_used):
    """Short noun phrases for the second sentence, most useful first; never the fact the lead already used."""
    out = []

    def add(score, kind, text, **used):
        if kind != lead_kind:
            out.append((score, kind, text, used))

    if f["park_kind"]:
        add(70, "parking", parking_phrase(f["park_kind"], f["park_fee"], f["park_included"]),
            parking=f["park_kind"], parking_fee=f["park_fee"])
    if f["sqft"]:
        add(60, "size", f"{whole(f['sqft'])} square feet", sqft=f["sqft"])
    if f["dog_amenity"]:
        add(58, "dog", f["dog_amenity"], dog_amenities=f["dog_amenity"])
    if f["pool"]:
        add(55, "pool", "a pool", pool=True)
    if f["laundry"]:
        add(50, "laundry", "a washer and dryer in the unit", in_unit_laundry=True)
    if f["doorman"]:
        add(48, "doorman", "a 24-hour front desk" if f["doorman"] == "24-hour" else "a doorman", doorman=f["doorman"])
    if f["floor"] and f["floor_sure"]:
        add(40, "floor", f"a spot on floor {f['floor']}", floor=f["floor"])
    if f["avail"] and f["avail"] != "now":
        add(38, "date", f"a {f['avail']} move-in date", available=f["avail"])
    if f["gym"]:
        add(30, "gym", "a gym", gym=True)
    return sorted(out, key=lambda x: -x[0])


SECOND_WITH_PRICE = [
    "It runs about {price} a month all in, with {extras}.",
    "About {price} a month all in, and you get {extras}.",
    "Add {extras}, at about {price} a month all in.",
    "The all-in is about {price} a month, with {extras}.",
]
SECOND_NO_PRICE = ["It also has {extras}.", "You also get {extras}.", "Add {extras}."]
PRICE_ONLY = ["It runs about {price} a month all in.", "The all-in is about {price} a month."]


def words(text):
    return len(text.split())


def compose_line(f, peers, previous_pattern=None):
    """-> (host_line, pattern_id, used). Never returns the previous unit's pattern."""
    cands = sorted(lead_patterns(f, peers), key=lambda c: (-c[0], c[1]))
    cands = [c for c in cands if c[1] != previous_pattern]
    best = cands[0][0]
    pool = [c for c in cands if c[0] >= best - 12]
    score, pid, kind, lead, used = pool[seed(f["id"], "lead") % len(pool)]
    used = {k: v for k, v in used.items() if v is not None}
    price_in_lead = "all_in" in used
    extras = support_phrases(f, kind, used)[:2]
    for keep in (2, 1, 0):
        chosen = extras[:keep]
        text = join_and([e[2] for e in chosen])
        if price_in_lead or not f["all_in"]:
            second = SECOND_NO_PRICE[seed(f["id"], "second") % len(SECOND_NO_PRICE)].format(extras=text) if chosen else ""
        elif chosen:
            second = SECOND_WITH_PRICE[seed(f["id"], "second") % len(SECOND_WITH_PRICE)].format(price=usd(f["all_in"]), extras=text)
        else:
            second = PRICE_ONLY[seed(f["id"], "second") % len(PRICE_ONLY)].format(price=usd(f["all_in"]))
        line = (lead + " " + second).strip()
        if words(line) <= MAX_WORDS:
            break
    all_used = dict(used)
    for e in chosen:
        all_used.update({k: v for k, v in e[3].items() if v is not None})
    if not price_in_lead and f["all_in"]:
        all_used["all_in"] = f["all_in"]
    return line, pid, all_used


# ------------------------------------------------------------------ the catch

UNKNOWN_NAMES = {"building fees": "building fees", "pet rent": "pet rent", "parking fee": "the parking fee", "gas": "the gas bill"}
CONFIRM = {
    "listing": "There is an open question about whether this unit is still available at this price, so call before you plan a visit.",
    "live check": "We have not re-checked this listing live yet, so the price and the date are as first collected.",
    "elevator": "Elevator access for this exact unit is not confirmed, so ask before you tour.",
    "dogs allowed": "Listing sites disagree on whether dogs are allowed here, so get the dog policy in writing.",
    "dogs": "The dog policy here is not settled, so get it in writing.",
    "availability": "This is a floor plan and not a specific apartment yet, so ask which unit, which floor and what date.",
    "floor": "The floor is not published, so confirm it is above the ground floor.",
    "lease term": "The lease term behind this price is not clear, so ask what a 12-month lease costs.",
    "cost near the cap": "The all-in sits close to your cap, so any fee the listing left out could push it over.",
}


NEEDS_CALL = [
    "The page does not say whether the advertised rent is before or after its special, so ask for the full monthly rent.",
    "There is a special on this listing and no word on whether the price already includes it, so ask what the rent is in a normal month.",
    "Ask whether the advertised rent is the full monthly rent or an average after the free period, because the page does not say.",
]
NO_PARKING = [
    "Parking isn't published for this place, so ask where the car goes and what it costs before anything else.",
    "The listing says nothing about parking, so ask where the car sleeps and what that costs before you tour.",
    "Parking isn't published here, and for you that is the opening question: where does the car go, and for how much.",
]


def pick(options, listing_id, salt):
    return options[seed(listing_id, salt) % len(options)]


def compose_catch(u, f):
    """-> (host_catch, kind, used). Never about crime: every unit shown has already passed the safety rule, so the
    catch is about living there (owner's rule, 2026-11-16). One sentence, in this order: the unit's open question (its asterisk); a rent the
    page leaves ambiguous; parking not published; unpublished costs that could break the cap; an unusual lease term;
    otherwise the unit's weakest fact."""
    c = u.get("confirm") or {}
    if c.get("asterisk") and c.get("what"):
        what = str(c["what"])
        if what in CONFIRM:
            return CONFIRM[what], f"confirm:{what}", {"confirm_what": what}
        q = str(c.get("question") or "").strip()
        if q:
            return f"One thing is unconfirmed, so ask the leasing office this: {q}", f"confirm:{what}", {"confirm_what": what, "confirm_question": q}
        return "One thing about this listing is unconfirmed, so call the leasing office before you tour.", f"confirm:{what}", {"confirm_what": what}
    rent = u.get("rent") or {}
    if rent.get("basis_kind") == "net_effective":
        return ("The price shown is a net-effective rent, so the monthly bill will be higher than it looks, and you should ask for the gross rent.",
                "rent:net_effective", {"rent_basis_kind": "net_effective"})
    if rent.get("asterisk") and rent.get("needs_call"):
        return pick(NEEDS_CALL, f["id"], "catch"), "rent:needs_call", {"rent_needs_call": True}
    if f["park_kind"] is None:
        return pick(NO_PARKING, f["id"], "catch"), "unknown:parking", {"parking": None}
    names = u.get("all_in_unknown") or []
    unknown = [UNKNOWN_NAMES.get(x, x) for x in names]
    tight = f["margin"] is not None and f["margin"] < 100 * len(unknown)      # each missing line could be about $100
    if unknown and f["all_in"] and tight:
        verb = "is" if len(unknown) == 1 else "are"
        return (f"{cap_first(join_and(unknown))} {verb} not published, and with only {usd(f['margin'])} under your cap the real all-in could go over, so ask.",
                "unknown:costs", {"all_in_unknown": names, "cap_margin": f["margin"]})
    lease = num(get(u, "cost_check", "lease_term_months")) or num(rent.get("lease_months"))
    if lease and int(lease) != 12:
        return (f"This price is tied to a {int(lease)}-month lease, so ask what other terms cost.", "lease_term", {"lease_months": int(lease)})
    return weakest(u, f, unknown)


def weakest(u, f, unknown=()):
    """The lowest-scoring part of the unit's scorecard that can be said from its own fields. Safety is skipped on
    purpose (see compose_catch)."""
    parts = {k: v for k, v in (get(u, "scores", "parts") or {}).items() if num(v) is not None}
    for kind in sorted(parts, key=lambda k: (parts[k], k)):
        drive = num(get(u, "moments", "sun", "drive_min"))
        if kind == "distance" and drive:
            return f"The weak spot is distance: about {whole(drive)} minutes to your parents each way, before traffic.", "weak:distance", {"drive_min": drive}
        if kind == "space" and f["sqft"]:
            return f"The weak spot is size, at {whole(f['sqft'])} square feet for you, a desk and a dog.", "weak:space", {"sqft": f["sqft"]}
        if kind == "cost" and f["all_in"] and f["margin"] is not None:
            return f"The weak spot is cost: about {usd(f['all_in'])} all in leaves only about {usd(f['margin'])} under your cap.", "weak:cost", {"all_in": f["all_in"], "cap_margin": f["margin"]}
        rest = num(get(u, "moments", "after", "restaurants_800m"))
        if kind == "daily" and rest is not None:
            n = int(rest)
            what = "no restaurants" if n == 0 else f"only {n} restaurant" + ("" if n == 1 else "s")
            return f"The weak spot is daily life on foot, with {what} within a {WALK_RADIUS}.", "weak:daily", {"restaurants_800m": n}
        if kind == "dog" and f["dog_park_m"] is not None:
            return f"The weak spot is the dog's routine: the nearest dog park is {miles(f['dog_park_m'])} miles away.", "weak:dog", {"dog_park_miles": miles(f["dog_park_m"])}
        if kind == "car" and f["park_kind"]:
            return (f"The weak spot is the car: the listing offers {parking_phrase(f['park_kind'], f['park_fee'], f['park_included'])}, so see the space yourself.",
                    "weak:car", {"parking": f["park_kind"], "parking_fee": f["park_fee"]})
        if kind == "building":
            return "The weak spot is the building itself on our scorecard, so look hard at the lobby, the elevator and the hallways on the tour.", "weak:building", {"weakest_part": "building"}
    if unknown:
        verb = "is" if len(unknown) == 1 else "are"
        return f"{cap_first(join_and(list(unknown)))} {verb} not published, so ask what they add to the monthly bill.", "unknown:costs", {"all_in_unknown": list(unknown)}
    return "Nothing stands out as a problem on paper, which is exactly when a tour matters most.", "none", {}


# ------------------------------------------------------------------ section subheads
# One short line (at most 14 words, no numbers: the section's headline states them) under the cost, parking, dog and
# building headlines of a place. Each is picked from a small library by what the unit's fields say; an unknown gets
# an "ask" line, never a statement; when nothing distinctive can be said the subhead is empty.

SUB_MAX_WORDS = 14
SUBS = {
    "cost": [
        ("net_effective", ["The price shown is after a discount, so ask for the real monthly rent.",
                           "This is a net-effective number, and the monthly bill will be higher."]),
        ("ambiguous_rent", ["There is a special here, so ask what a normal month costs.",
                            "Ask whether this price is before or after the free period."]),
        ("tight", ["Right at your ceiling, so a single surprise fee tips it over.",
                   "No room to spare here, so every unlisted fee matters."]),
        ("unpublished", ["Some costs are unpublished, so treat this number as a floor.",
                         "They leave some fees off the page, so ask for the full monthly bill."]),
        ("roomy", ["Leaves real room under your ceiling for the things nobody lists.",
                   "Comfortably inside your budget, with money left for the sofa."]),
    ],
    "parking": [
        ("unknown", ["They say nothing about parking, so make it your opening question.",
                     "Parking is not published here, so ask before you fall for it."]),
        ("included", ["The spot comes with the lease, so the car costs nothing extra.",
                      "Parking is part of the deal, so there is no monthly fee to chase."]),
        ("garage_priced", ["Your car sleeps indoors, and you never circle the block.",
                           "Pull in, park under a roof, and the day is over."]),
        ("garage_unpriced", ["Indoor parking, but they don't publish the price, so ask before you fall for it.",
                             "A garage with no price listed, so get the monthly fee in writing."]),
        ("covered_priced", ["A roof over the car, with the price on the page.",
                            "Covered parking, so no scraping ice in January."]),
        ("covered_unpriced", ["Covered parking, though they don't publish the price, so ask.",
                              "The car gets a roof, and the fee is a question for the office."]),
        ("lot_priced", ["A spot in the building's lot, so you are off the street.",
                        "Lot parking with a listed price, which beats hunting the curb."]),
        ("lot_unpriced", ["A lot on site, but no price on the page, so ask.",
                          "There is a lot, and what it costs is still a question."]),
        ("onsite_unpriced", ["Parking exists on site, and the details are yours to ask for.",
                             "They mention parking and little else, so ask what kind and how much."]),
    ],
    "dog": [
        ("conflicting", ["The dog policy is unsettled, so get a yes in writing.",
                         "Listings disagree about dogs here, so confirm before you tour."]),
        ("onsite", ["The dog's first walk of the day can start in the elevator.",
                    "A place for the dog without leaving the property."]),
        ("near_run", ["A dog run is close enough for a quick morning lap.",
                      "The dog gets a proper run before your first meeting."]),
        ("small_only", ["The page says small dogs and gives no weight, so ask for the number.",
                        "Small dogs are welcome, and the exact limit is a question to ask."]),
        ("weight_limit", ["There is a weight limit, so check it against the dog you choose.",
                          "Dogs are welcome up to a weight limit, so pick the puppy with that in mind."]),
        ("pet_rent_unknown", ["Dogs are welcome, though they don't publish the pet rent, so ask.",
                              "No pet rent on the page, so ask what the dog adds each month."]),
    ],
    "building": [
        ("front_desk", ["Someone is at the desk when you come home late.",
                        "A staffed front desk, which also means your packages wait for you."]),
        ("doorman", ["A doorman at the door, and a familiar face after a long day.",
                     "There is a doorman, so deliveries and late arrivals are easier."]),
        ("pool_laundry", ["A pool downstairs and laundry in your own apartment.",
                          "Laundry at home and a pool for the weekend."]),
        ("laundry", ["Laundry happens in your own apartment, on your own schedule.",
                     "The washer and dryer are yours alone."]),
        ("pool", ["A pool comes with the building, and summer gets easier.",
                  "There is a pool, and yes, you would use it."]),
        ("gym", ["A gym in the building, which helps in February.",
                 "The gym is an elevator ride away."]),
    ],
}


def sub_keys(u, f):
    """Which library entry applies in each section, from the unit's own fields. None = say nothing."""
    rent = u.get("rent") or {}
    unknown = u.get("all_in_unknown") or []
    if rent.get("basis_kind") == "net_effective":
        cost = "net_effective"
    elif rent.get("asterisk") and rent.get("needs_call"):
        cost = "ambiguous_rent"
    elif f["margin"] is not None and f["margin"] < 100:
        cost = "tight"
    elif unknown:
        cost = "unpublished"
    elif f["margin"] is not None and f["margin"] >= 400:
        cost = "roomy"
    else:
        cost = None
    k = f["park_kind"]
    if k is None:
        parking = "unknown"
    elif f["park_included"]:
        parking = "included"
    elif k == "onsite":
        parking = "onsite_unpriced" if not f["park_fee"] else "lot_priced"
    else:
        parking = f"{k}_{'priced' if f['park_fee'] else 'unpriced'}"
    dog_field = u.get("dog") or {}
    limit = str(dog_field.get("weight_limit_lb") or "").strip().lower()
    if str(dog_field.get("allowed") or "").lower() == "conflicting":
        dog = "conflicting"
    elif f["dog_amenity"] and "on site" in f["dog_amenity"]:
        dog = "onsite"
    elif f["dog_park_m"] is not None and f["dog_park_m"] <= 800:
        dog = "near_run"
    elif dog_field.get("size_note") and "small" in str(dog_field.get("size_note")).lower() and not limit:
        dog = "small_only"
    elif limit and limit != "no limit":
        dog = "weight_limit"
    elif dog_field.get("pet_rent") is None:
        dog = "pet_rent_unknown"
    else:
        dog = None
    if f["doorman"] == "24-hour":
        building = "front_desk"
    elif f["doorman"]:
        building = "doorman"
    elif f["pool"] and f["laundry"]:
        building = "pool_laundry"
    elif f["laundry"]:
        building = "laundry"
    elif f["pool"]:
        building = "pool"
    elif f["gym"]:
        building = "gym"
    else:
        building = None
    return {"cost": cost, "parking": parking, "dog": dog, "building": building}


def compose_subs(u, f):
    """-> ({sub_cost, sub_parking, sub_dog, sub_building}, {section: library key})"""
    keys = sub_keys(u, f)
    out = {}
    for section, key in keys.items():
        options = dict(SUBS[section]).get(key) if key else None
        out["sub_" + section] = pick(options, f["id"], "sub_" + section) if options else ""
    return out, keys


# ------------------------------------------------------------------ the run

FIELDS = ["listing_id", "host_line", "host_catch", "sub_cost", "sub_parking", "sub_dog", "sub_building", "facts_used_json"]


def build(units):
    """units: the `units` list of site/data.json. -> rows with the columns in FIELDS."""
    by_hood = defaultdict(list)
    for u in units:
        by_hood[u.get("hood_id")].append(u)
    rows = []
    for hood in sorted(by_hood, key=str):
        group = sorted(by_hood[hood], key=lambda u: (num(get(u, "scores", "hood_rank")) or 1e9, str(u["id"])))
        peers = [facts(u) for u in group]
        previous = None
        for u, f in zip(group, peers):
            line, pid, used = compose_line(f, peers, previous)
            previous = pid
            catch, ckind, cused = compose_catch(u, f)
            subs, sub_kinds = compose_subs(u, f)
            rows.append({"listing_id": u["id"], "host_line": line, "host_catch": catch, **subs,
                         "facts_used_json": json.dumps({"hood_id": hood, "pattern": pid, "line": used, "catch_kind": ckind,
                                                        "catch": cused, "subs": sub_kinds},
                                                       ensure_ascii=False, sort_keys=True)})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(DATA), help="page data to read (default site/data.json)")
    ap.add_argument("--out", default=str(OUT), help="CSV to write (default data/reference/realtor_lines.csv)")
    a = ap.parse_args()
    units = json.loads(Path(a.data).read_text(encoding="utf-8"))["units"]
    rows = build(units)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    pats = Counter(json.loads(r["facts_used_json"])["pattern"] for r in rows)
    catches = Counter(json.loads(r["facts_used_json"])["catch_kind"] for r in rows)
    print(f"{len(rows)} units written to {a.out}")
    print(f"{len(pats)} of {len(PATTERN_IDS)} line patterns used; most common: {pats.most_common(5)}")
    print(f"catch kinds: {dict(catches.most_common())}")


if __name__ == "__main__":
    main()
