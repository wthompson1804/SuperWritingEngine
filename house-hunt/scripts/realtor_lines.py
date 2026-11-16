#!/usr/bin/env python3
"""Compose the "About the building" text and the per-unit line and catch for everything shown on the page.

The unit list changes with every repair run, so nothing here is hand-written per unit or per building. For each
building in site/data.json (its units grouped by building_id) and for each unit, this script reads the fields, works
out which facts are most distinctive, and fills one of the hand-written sentences in the libraries below.

Per BUILDING  ->  data/reference/building_about.csv
  about_building     2 sentences, at most 40 words: what the building is like to live in (parking, pool, doorman,
                     laundry, a dog area, its age where known), then what is around its door
  about_points_json  3 to 5 icon points [{icon, text}], text at most 14 words; exactly one has the icon "warning": the
                     main thing to ask about. A fact the two sentences already state is not repeated as a point.
  facts_used_json    the sentences chosen and every value printed

Per UNIT  ->  data/reference/realtor_lines.csv
  host_line   1 or 2 sentences, at most 45 words: what sets THIS unit apart inside its building (price, size, floor,
              move-in date, how new the listing is, how little is left to ask), then its price and one or two more
              of its own facts. The building's features are in "About the building" and are not repeated here.
  host_catch  1 sentence: the unit's own open question (its asterisk), else an offer that clouds its rent, its lease
              term, unpublished costs that could break the cap, its unpublished floor; else its weakest own fact
  sub_cost, sub_parking, sub_dog, sub_building   one optional short line (at most 14 words, no numbers) for under each
              section headline; empty when the fields give nothing distinctive to say
  facts_used_json   the wording chosen and every value that was printed, so each word can be traced to a field

The page shows these as plain "About ..." text with no host on screen, so no sentence says "I" or stages a tour guide.

How the wording is spread. The same sentence on card after card kills the read, so:
  * every condition (a fact that can lead, a kind of catch, a subhead case) has at least 8 different sentences,
    written from different angles, never one template with synonyms swapped (icon points: at least 4);
  * no line wording, second-sentence frame, subhead, building sentence or point is on more than LINE_SHARE of the
    rows, no catch wording on more than CATCH_SHARE (the run prints the distribution; the tests hold the limits);
  * the three top-ranked units of a neighbourhood, and the units of one building, lead with different angles and
    carry different catch wordings; two neighbouring units never open with the same three words; two neighbouring
    buildings never open the same way.

Rules the code keeps (scripts/test_realtor_lines.py checks them):
  * deterministic: choices are seeded by listing_id / building_id and made in a fixed order, so a rerun on the same
    data gives the same text;
  * an unknown is never stated as a fact: parking that is not published is an "ask"; a garage with no price is "fee
    not published", never "free"; a dog policy that is not settled is never "dogs are welcome";
  * a catch states a reason only when the unit's own fields give it: "listings disagree about dogs" only where the
    open item says the sources disagree; "net-effective" only where the rent block has that basis AND a gross figure
    and its offer text does not say the page leaves it unstated (otherwise: there is a special, ask what a normal
    month costs);
  * a superlative ("the most room in the building") is claimed only when every other unit there publishes the figure;
  * every number printed is the unit's or building's own field (or the count it is compared with), never typed;
  * no crime or safety wording: everything shown has passed the safety rule, so the text is about living there.

Run from the house-hunt folder:  python3 scripts/realtor_lines.py     (reads site/data.json, read-only)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data.json"
OUT = ROOT / "data" / "reference" / "realtor_lines.csv"
OUT_BUILDINGS = ROOT / "data" / "reference" / "building_about.csv"
MAX_WORDS = 45                            # host_line
ABOUT_MAX_WORDS = 40                      # about_building
POINT_MAX_WORDS = 14
POINTS_COUNT = (3, 5)
WALK_RADIUS = "10-minute walk"            # the page's wording for the 800 m radius
LINE_SHARE = 0.04                         # no lead wording, frame, subhead, building sentence or point on more than 4%
CATCH_SHARE = 0.05                        # no catch wording on more than 5% of units
COND_SHARE = 0.08                         # a lead condition used this often is set back, so other angles get a turn
MIN_WORDINGS = 8                          # sentences per condition
MIN_POINT_WORDINGS = 4                    # wordings per icon point
UNPRICED = re.compile(r"not published|does not publish|unpublished", re.I)   # every unpriced-garage sentence says so
ICONS = ["home", "dog", "park", "car", "parking", "fork", "cocktail", "coffee", "train", "money", "clock", "moon", "sun",
         "water", "key", "heart", "people", "ruler", "laundry", "pool", "warning"]


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


def minutes(x) -> str:
    m = int(round(max(1.0, float(x))))
    return f"{m} minute" if m == 1 else f"{m} minutes"


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


def open3(text: str) -> str:
    """The first three words, lower case: two neighbouring units never share them."""
    return " ".join(re.findall(r"[A-Za-z0-9$'-]+", text.lower())[:3])


def rotate(options, key, salt):
    """The options in an order seeded by the listing or building id (stable across reruns)."""
    k = seed(key, salt) % len(options)
    return options[k:] + options[:k]


def share_cap(share, n):
    return max(3, int(share * n))


def words(text):
    return len(text.split())


# ------------------------------------------------------------------ what the fields say

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


def net_effective(u):
    """True only when the rent block itself says the price is net-effective AND carries a gross figure above it, and
    its offer text does not say the page leaves the point unstated. Anything less is "a special, ask"."""
    rent = u.get("rent") or {}
    gross, listed = num(rent.get("gross")), num(rent.get("listed"))
    if rent.get("basis_kind") != "net_effective" or gross is None or listed is None or gross <= listed:
        return False
    return not re.search(r"not stated|does not say|unstated", str(rent.get("offer_text") or ""), re.I)


def has_special(u):
    """An offer clouds the rent: the page flags it, or it was marked net-effective without the proof net_effective wants."""
    rent = u.get("rent") or {}
    return bool(rent.get("asterisk") and rent.get("needs_call")) or \
        (rent.get("basis_kind") == "net_effective" and not net_effective(u))


def dog_open(u):
    """The unit's open item is whether dogs are allowed -> 'conflict' (the sources disagree), a reason phrase taken
    from the open item's own text, or 'open' (no reason we can state). None when dogs are not the open item."""
    c = u.get("confirm") or {}
    if not (c.get("asterisk") and str(c.get("what") or "").startswith("dogs")):
        return None
    why = str(c.get("why") or "").lower()
    for key, reason in DOG_REASONS:
        if re.search(key, why):
            return reason
    return "open"


DOG_REASONS = [                                        # (what the open item's text says, the clause the catch may use)
    (r"disagree|and another says", "conflict"),
    (r"upon approval|on approval", "the policy says pets are welcome upon approval"),
    (r"case by case", "pets are considered case by case here"),
    (r"contact for more information", "the only pet policy text says to contact the office"),
    (r"small pets", "the listing says small pets and does not name dogs"),
    (r"no policy text", "dogs appear only in a listing site's pet data, with no policy text"),
]


def facts(u):
    """Everything the sentences may use, read straight from the unit. Missing stays None."""
    am = u.get("amenities") or {}
    kind, fee, included = parking_kind(u)
    floor = num(u.get("floor"))
    label, day = when(u.get("available"))
    free = str(get(u, "rent", "free_months") or "")
    doorman = am.get("doorman")
    all_in, sqft = num(u.get("all_in")), num(u.get("sqft"))
    age = num(u.get("listing_age_days"))
    built = num(am.get("year_built"))
    questions = u.get("tour_questions")
    dog = u.get("dog") or {}
    limit = str(dog.get("weight_limit_lb") or "").strip().lower()
    sure = u.get("floor_basis") in ("confirmed", "stated")
    return {
        "id": u["id"], "hood": u.get("hood_id"), "building": u.get("building_id") or u["id"],
        "beds": "studio" if u.get("beds") == 0 else "1-bedroom" if u.get("beds") == 1 else None,
        "all_in": all_in, "sqft": sqft,
        "per_sqft": all_in / sqft if all_in and sqft else None,
        "floor": int(floor) if floor and floor >= 2 else None,
        "floor_sure": sure,
        "margin": num(get(u, "cost_check", "cap_margin")),
        "park_kind": kind, "park_fee": fee, "park_included": included,
        "pool": bool(am.get("pool")), "gym": am.get("gym") == "yes",
        "doorman": "24-hour" if doorman == "24h" else "yes" if doorman else None,
        "laundry": am.get("in_unit_laundry") == "yes",
        "lounge": am.get("lounge_or_coworking") == "yes",
        "built": int(built) if built else None,
        "dog_amenity": dog_amenity(u),
        "dog_park": get(u, "moments", "wake", "dog_park"), "dog_park_m": num(get(u, "moments", "wake", "dog_park_m")),
        "park": get(u, "moments", "wake", "park"), "park_walk": num(get(u, "moments", "wake", "park_walk_min")),
        "restaurants": num(get(u, "moments", "after", "restaurants_800m")),
        "station": get(u, "moments", "sat", "train_station"), "station_m": num(get(u, "moments", "sat", "train_station_m")),
        "market": get(u, "moments", "work", "supermarket"), "market_m": num(get(u, "moments", "work", "supermarket_m")),
        "avail": label, "avail_date": day,
        "age_days": int(age) if age is not None and age >= 0 else None,
        "open_questions": len(questions) if isinstance(questions, list) else None,
        "free_months": int(free) if free in ("1", "2", "3") else None,
        "rank": num(get(u, "scores", "hood_rank")),
        "no_weight_limit": limit == "no limit",
        "weight_limit": num(limit),
        "small_only": bool(dog.get("size_note")) and "small" in str(dog.get("size_note")).lower() and not limit,
        "dog_allowed": str(dog.get("allowed") or "").lower() == "yes",
        "dog_open": dog_open(u),
        "pet_rent_known": dog.get("pet_rent") is not None,
        "elevator_open": bool(get(u, "confirm", "asterisk")) and get(u, "confirm", "what") == "elevator",
        "elevator_sure": get(u, "elevator", "value") == "yes" and not get(u, "elevator", "listing_site_only"),
        "unknown": list(u.get("all_in_unknown") or []),
        "disclosures": {str(d.get("what")) for d in (u.get("disclosures") or []) if isinstance(d, dict)},
    }


def only(f, peers, test):
    return len(peers) >= 2 and test(f) and not any(test(p) for p in peers if p["id"] != f["id"])


def extreme(f, peers, key, best=max, everyone=True):
    """True when this one alone holds the best value of `key` among its peers (the units of its building, or the
    buildings of its neighbourhood). With `everyone` (the default) every peer must publish the value, so "the most
    room in the building" is simply true; without it, at least 2 must, and the sentence has to say it speaks only of
    the listings that give the figure."""
    vals = [p[key] for p in peers if p[key] is not None]
    if f[key] is None or len(vals) < 2 or (everyone and len(vals) < len(peers)):
        return False
    top = best(vals)
    return f[key] == top and vals.count(top) == 1


def soonest(f, peers):
    """'now' when it is the only peer available now; 'date' when its date is alone the earliest and nothing is now.
    Every peer must publish a date."""
    known = [p for p in peers if p["avail"]]
    if f["avail"] is None or len(known) < 2 or len(known) < len(peers):
        return None
    nows = [p for p in known if p["avail"] == "now"]
    if f["avail"] == "now":
        return "now" if len(nows) == 1 else None
    if nows:
        return None
    days = [p["avail_date"] for p in known]
    return "date" if f["avail_date"] == min(days) and days.count(min(days)) == 1 else None


# ------------------------------------------------------------------ the sentence libraries
# Hand-written. A condition is offered only when its fact is true; {fields} are filled from the data.

# LEADS[condition] = (angle, [sentences]): what sets THIS unit apart inside its building. {n} is the number of
# apartments we found in the building; every other {field} is filled from the unit's own fields.
LEADS = {'cheapest': ('price',
              ['The {low} all-in of the {n} apartments we found in this building, about {price} a month.',
               'Start with the number: about {price} a month all in, the {low} of the {n} in this building.',
               'No other apartment we found in this building comes in under this one, at about {price} a month all '
               'in.',
               'The budget pick of the building: about {price} a month all in.',
               'About {price} a month all in, and no other listing in the building beats that.',
               'If the monthly number decides it, this is the unit to ask about, at about {price} all in.',
               "Your wallet's favorite of the {n} here, at about {price} a month all in.",
               'Of the {n} apartments in this building, this asks the least of you each month, about {price} all '
               'in.']),
 'biggest': ('size',
             ['The {big} of the {n} apartments we found in this building, at {sqft} square feet.',
              '{sqft} square feet, more than any other apartment we found in the building.',
              'For space, nothing else in the building tops this unit: {sqft} square feet.',
              'The desk, the sofa and the dog bed all fit in {sqft} square feet, the most of the {n} here.',
              "You work from home, so notice this: {sqft} square feet, the most room in the building's listings.",
              'No other listing in this building gives you this much floor, {sqft} square feet of it.',
              'Of the {n} apartments here, this has the most room to spread out, {sqft} square feet.',
              'Room wins with this unit: at {sqft} square feet, it is the largest we found in the building.']),
 'value': ('value',
           ['The most room for the money in this building: {sqft} square feet for about {price} a month all in.',
            'Dollar for square foot, this is the best deal of the {n} apartments here, {sqft} square feet at about '
            '{price} all in.',
            "About {price} a month all in buys {sqft} square feet, the strongest trade among the building's "
            'listings.',
            'If you measure by what each dollar buys, this unit wins the building: {sqft} square feet, about {price} '
            'all in.',
            'No other apartment here stretches the budget as far, {sqft} square feet for about {price} a month all '
            'in.',
            'The value pick of the {n} here, {sqft} square feet at about {price} a month all in.',
            'You get more floor per dollar in this unit than in any other we found here: {sqft} square feet, about '
            '{price} all in.',
            'Run the math on all {n} apartments in the building and this comes out ahead, {sqft} square feet for '
            'about {price} all in.']),
 'pick': ('pick',
          ['If you see only one apartment in this building, see this one.',
           'This is the door to open first in this building.',
           'Of the {n} apartments here, this is where to start the tour.',
           'The pick of the building, and worth seeing before the others.',
           'Clear your calendar for this unit before any other in the building.',
           'Start here: of everything listed in this building, this unit fits you best.',
           'Put this unit at the top of your list for this building.',
           "See this one first, and judge the building's other apartments against it."]),
 'highest': ('floor',
             ['Floor {floor}, the {high} of the apartments we found in this building.',
              'You are up on floor {floor}, above every other listing in the building.',
              'No other apartment we found here sits as high as this one, on floor {floor}.',
              "The high-floor pick: floor {floor}, above the building's other listings.",
              'Of the {n} apartments here, this is the one farthest above the street, on floor {floor}.',
              "Press the button for floor {floor}, the top of this building's listings.",
              'Floor {floor} puts you above all the other apartments we found here.',
              'If you like height, this is the unit: floor {floor}, the {high} on offer here.']),
 'fewest_questions': ('clean',
                      ['The fewest loose ends of the {n} apartments here, so the tour can be about the rooms.',
                       'This listing leaves less for you to chase than any other in the building.',
                       'Of the {n} apartments here, this has the shortest list of things to ask.',
                       'The most complete listing in the building, which makes your homework lighter.',
                       'You would walk in with fewer open questions than for any other unit here.',
                       'On paper this is the tidiest of the {n}, with the least left to confirm.',
                       'Less guesswork with this unit than with the others in the building.',
                       'If you hate surprises, start with this one: no other listing here leaves so little '
                       'unanswered.']),
 'soonest_now': ('date',
                 ['Available now, which no other apartment we found in this building is.',
                  "You could move in right away, and the building's other listings make you wait.",
                  'The keys are ready now, ahead of the other apartments here.',
                  'Of the {n} apartments here, this is the only one open today.',
                  'No waiting on this one: it is the lone unit in the building available now.',
                  'If you want to move fast, this is the unit, the only one here ready now.',
                  'Ready when you are, and that is true of no other listing in the building.',
                  'This is the move-in-now option, alone among the {n} apartments here.']),
 'soonest_date': ('date',
                  ["Ready {date}, the earliest date among this building's listings.",
                   'This opens {date}, before any other apartment we found here.',
                   'The first move-in date in the building: {date}.',
                   'Of the {n} apartments here, this gets you in soonest, on {date}.',
                   'Circle {date}, because no other unit here is ready earlier.',
                   'If the calendar matters, this unit leads the building with a {date} move-in.',
                   'You would have keys on {date}, ahead of every other listing here.',
                   'Nothing in the building beats a {date} start, and this is the unit that offers it.']),
 'newest': ('new',
            ['Fresh on the market: listed {ago}, the newest listing we can date in this building.',
             'This went up {ago}, the most recent posting date we have for the building.',
             'Listed {ago}, so you are seeing it early, ahead of every other dated listing here.',
             'New to the list: posted {ago}, the latest dated listing in the building.',
             'Of the listings here that show a date, this is the newest, posted {ago}.',
             'It was posted {ago}, later than any other dated listing we found in the building.',
             'The newcomer of the building, listed {ago}.',
             'Posted {ago}, which makes this the freshest dated listing here.']),
 'concession': ('offer',
                ['The listing advertises {free} free, so read the lease math carefully.',
                 'There is an offer of {free} free on this one, and the real monthly rent is the thing to pin down.',
                 'The headline here is {free} free, and the fine print is where you should look.',
                 'They are dangling {free} free, which is nice, as long as you know the rent after it ends.',
                 'A special of {free} free is on the table, so ask what the rent is once it runs out.',
                 'The deal on the page is {free} free, and deals like that deserve a second read.',
                 'You would get {free} free under the current offer, so compare this place on its full rent.',
                 'This comes with {free} free, and it is fairer to judge it by the regular rent.']),
 'big': ('size',
         ['{sqft} square feet, so the desk gets its own corner.',
          'Room to work from home: {sqft} square feet.',
          'At {sqft} square feet, the laptop never has to share the dinner table.',
          'You get {sqft} square feet, which is real room for a desk and a dog.',
          'The floor plan runs {sqft} square feet, generous for a first place.',
          'There is space to pace on a work call here, {sqft} square feet of it.',
          'With {sqft} square feet, the dog can have the zoomies without rearranging your office.',
          'This is a roomy one at {sqft} square feet.']),
 'high_floor': ('floor',
                ['Floor {floor}, well above the street.',
                 'You would be up on floor {floor}.',
                 'The elevator takes you to floor {floor}, a long way from the sidewalk.',
                 'This one sits on floor {floor}, high enough to leave the street behind.',
                 'Up on floor {floor}, the block stays well below you.',
                 'Floor {floor} is the address, so bring your head for heights.',
                 'It is a floor {floor} apartment, well clear of the ground level you asked to avoid.',
                 'High up, on floor {floor}.']),
 'margin': ('price',
            ['About {price} a month all in, which leaves about {margin} under your cap.',
             'This comes in about {margin} below your ceiling, at about {price} a month all in.',
             'There is breathing room in the budget here: about {price} all in, about {margin} to spare.',
             'At about {price} a month all in, you keep about {margin} of your budget.',
             'The bill is about {price} a month all in, a comfortable {margin} or so under your limit.',
             'You would have about {margin} left each month, with the all-in at about {price}.',
             'Easy on the budget: about {price} all in, roughly {margin} under what you set.',
             'About {margin} of headroom under your cap, on an all-in of about {price} a month.']),
 'size': ('size',
          ['This one measures {sqft} square feet.',
           '{sqft} square feet to work with.',
           'The floor plan runs {sqft} square feet.',
           'You would have {sqft} square feet for the desk, the sofa and the dog.',
           'At {sqft} square feet, measure your desk before you measure anything else.',
           'It comes to {sqft} square feet in all.',
           'Room for you and the dog: {sqft} square feet.',
           'On paper, {sqft} square feet.']),
 'floor': ('floor',
           ['It is on floor {floor}.',
            'Floor {floor}, so you are off the ground level you asked to avoid.',
            'The elevator stops at floor {floor} for this one.',
            'You would live on floor {floor}.',
            'This unit sits on floor {floor}.',
            'Up on floor {floor}, clear of the street.',
            'The address ends on floor {floor}.',
            'A floor {floor} apartment.']),
 'one_bed': ('layout',
             ['A true 1-bedroom, so the desk stays out of the room you sleep in.',
              'The bedroom has a door, which matters when the living room is also the office.',
              'A 1-bedroom, with a wall between work and sleep.',
              'You get a separate bedroom here.',
              'It is a 1-bedroom, so a late work call does not happen next to the bed.',
              'Bedroom and living room are separate rooms in this one.',
              'This is a 1-bedroom layout, the better shape for working from home.',
              "With a separate bedroom, the dog's bed and your desk both find a place."]),
 'studio': ('layout',
            ['A studio, so the desk and the bed share the room.',
             'This is a studio, with living, working and sleeping in the same room.',
             'It is a studio layout, which keeps the furniture close.',
             'You would be living in an open room here, studio style.',
             'The layout is a studio, so plan where the desk goes before you sign.',
             'Studio living: everything within a few steps, including the office.',
             'Studio layout, which works if you like your space simple.',
             'Bed, desk and sofa share the floor here, as studios go.']),
 'avail_now': ('date',
               ['It is available now.',
                'The keys could be yours right away.',
                'This one is open today, with no waiting list to sit on.',
                'Move-in is immediate here.',
                'Available now, so the timing is entirely yours.',
                'You would not wait for this one: it is ready now.',
                'Ready now, which suits a search that starts this month.',
                'Nothing to wait for here, since the apartment is open now.']),
 'avail_date': ('date',
                ['It opens on {date}.',
                 'Move-in is {date}.',
                 'The keys are ready {date}.',
                 'Mark {date}, the day this one becomes available.',
                 'Available from {date}.',
                 'You could move in on {date}.',
                 'This one frees up on {date}.',
                 'The listing gives {date} as the move-in date.']),
 'basic': ('price',
           ['{Akind} at about {price} a month all in.',
            'The plain facts: {akind}, about {price} a month all in.',
            'This is {akind} that runs about {price} a month all in.',
            'On the bill, {akind} here comes to about {price} a month all in.',
            'Simple offer: {akind} for about {price} a month all in.',
            '{Akind}, about {price} a month once everything is counted.',
            'You are looking at {akind} for about {price} a month all in.',
            'No frills to report, just {akind} at about {price} a month all in.']),
 'basic_no_price': ('cost_open',
                    ['{Akind} in this neighborhood, with the all-in cost still to be worked out.',
                     'The plain facts: {akind}, with no all-in figure yet.',
                     'This is {akind}, and the full monthly cost is still an open number.',
                     '{Akind} here, though we cannot give you an all-in figure yet.',
                     'You are looking at {akind}, with the monthly total still to pin down.',
                     '{Akind}, and the first job is getting the full monthly cost from the office.',
                     'A straightforward {kind}, with the complete bill not worked out yet.',
                     'For now this is {akind} without a firm all-in number.']),
 'type': ('type',
          ['{Akind}, plain and simple.',
           'What is on offer here is {akind}.',
           'This listing is for {akind}.',
           'Think of this as {akind} that does what it says.',
           'The layout is {akind}.',
           'Here you would be renting {akind}.',
           'It is {akind}, with no surprises in the floor plan.',
           'On the page this is {akind}, nothing more complicated.']),
 'tour': ('tour',
          ['Put this one on the tour list and let the visit decide.',
           'This is one to judge in person.',
           'Keep this on the list, because some places only make sense once you stand in them.',
           'Worth a look with your own eyes before you rule it in or out.',
           'Let the walkthrough make the case for this one.',
           'Go see it, and trust what you notice in the first minute.',
           'The listing is modest about itself, so the tour has to speak for it.',
           'Hold your verdict on this one until you have walked through it.'])}

# BUILDING[condition] = (angle, 'inside' | 'around', [sentences]): what the building is like to live in, and what is
# around its door. {n} here is the number of buildings shown in the neighbourhood.
BUILDING = {'only_pool': ('pool',
               'inside',
               ["The only pool among the {n} buildings here is this building's.",
                'Of the {n} buildings in this neighborhood, this is the one with a pool.',
                'If a pool matters to you, this is the single building of the {n} here that lists one.',
                'Summer is easier in this building, because no other building here lists a pool.',
                "A pool, which no other building on this neighborhood's list offers you.",
                'A search of all {n} buildings here for a pool ends at this one.',
                'Every other building here sends you elsewhere to swim, and this building has its own pool.',
                "This is the swimmer's pick: the lone pool among the {n} buildings we found here."]),
 'only_garage': ('parking',
                 'inside',
                 ['No other building of the {n} here lists a garage, and this one does{gtail}.',
                  'Garage parking, the only one of the {n} buildings here to list it{gtail}.',
                  'Your car gets a garage here, alone among the buildings in this neighborhood{gtail}.',
                  'Of the {n} buildings here, this is the single building that puts the car indoors{gtail}.',
                  "For the car, this is the standout: the lone garage on this neighborhood's list{gtail}.",
                  'This is where the car sleeps indoors, since no other building here mentions a garage{gtail}.',
                  'If the car is the priority, start with this building, the only garage among the {n}{gtail}.',
                  'A garage is hard to find in this neighborhood, and this is the only building of {n} with '
                  'one{gtail}.']),
 'only_doorman': ('doorman',
                  'inside',
                  ['The only building of the {n} here with a doorman.',
                   'Someone staffs the front door here, and no other building in this neighborhood says the same.',
                   'Of the {n} buildings here, this is the lone building with a doorman.',
                   'A doorman, which none of the other buildings we found here lists.',
                   'Packages, late nights, a familiar face: this is the single doorman building of the {n} here.',
                   'If you want a staffed front door in this neighborhood, this building is the choice.',
                   'No other building here lists a person at the door, and this one does.',
                   "This is the neighborhood's doorman building, the only one among the {n} buildings we found."]),
 'only_laundry': ('laundry',
                  'inside',
                  ['The only building of the {n} here that lists a washer and dryer in the apartment.',
                   'Laundry happens inside your own apartment here, and no other building in this neighborhood says '
                   'the same.',
                   'Of the {n} buildings here, this is the lone building with a washer and dryer in the unit.',
                   'No other building here lists machines in the unit, and this one does, so skip the laundry room.',
                   'A washer and dryer of your own, which the other buildings in this neighborhood do not list.',
                   'If hauling a laundry bag is a dealbreaker, this is your building here, the only in-unit set of '
                   'the {n}.',
                   'The machines are in the apartment, a claim no other building in this neighborhood makes.',
                   "This is the neighborhood's in-unit laundry pick, alone among the {n} buildings we found."]),
 'only_dogspot': ('dog',
                  'inside',
                  ['The only building of the {n} here with its own {dogthing}.',
                   'A {dogthing} on the property, which no other building in this neighborhood lists.',
                   'Of the {n} buildings here, this is the lone building where the dog has a spot without leaving '
                   'the grounds.',
                   'No other building here mentions a {dogthing} of its own, and this one does.',
                   "For the dog, this is the neighborhood's standout: the single building with a {dogthing} on site.",
                   'The early walk can be an elevator ride here, thanks to the only on-site {dogthing} among the '
                   '{n}.',
                   'If the dog gets a vote, this wins: it is the single building here with a {dogthing}.',
                   'This building keeps a {dogthing} for residents, alone among the buildings we found here.']),
 'closest_run': ('dog',
                 'around',
                 ['{dogpark} is {dogpark_mi} miles away, closer than a dog run is to any other building here.',
                  "The shortest trip to a dog run on this neighborhood's list: {dogpark_mi} miles to {dogpark}.",
                  'Of the {n} buildings here, this puts the dog nearest a proper run, {dogpark_mi} miles from '
                  '{dogpark}.',
                  'Your dog would vote for this one, with {dogpark} {dogpark_mi} miles off, the nearest run to any '
                  'building here.',
                  'No other building here is nearer a dog run, with {dogpark} {dogpark_mi} miles from the door.',
                  'For off-leash time this leads the neighborhood, {dogpark_mi} miles from {dogpark}.',
                  'It is {dogpark_mi} miles to {dogpark}, and every other building here is farther from a dog run.',
                  "The dog's pick of the {n}: {dogpark} sits {dogpark_mi} miles away, the closest run on this "
                  'list.']),
 'closest_park': ('green',
                  'around',
                  ['{park} is about {park_mins} on foot, the shortest walk to green from any building here.',
                   "The quickest route to a park on this neighborhood's list: about {park_mins} to {park}.",
                   'Of the {n} buildings here, this is nearest a park, about {park_mins} from {park}.',
                   'Morning walks start sooner here than anywhere else in the neighborhood, about {park_mins} from '
                   '{park}.',
                   'No other building here is closer to green, with {park} about {park_mins} away.',
                   'About {park_mins} to {park}, and every other building here has a longer walk to a park.',
                   'For the daily loop this leads the neighborhood, about {park_mins} on foot from {park}.',
                   'The leash-and-coffee pick of the {n}, about {park_mins} from {park}.']),
 'parking_included': ('parking',
                      'inside',
                      ['A parking spot comes with the lease, so the car adds nothing to the bill.',
                       'Parking is included in the lease here, which is one less thing to negotiate.',
                       'The rent already takes care of the car: the listing includes a spot.',
                       'No separate parking bill here, because a spot is part of the lease.',
                       'Your car has a place and it is already paid for in the rent.',
                       'They include a parking spot, and in this search that is worth real money.',
                       'The line you will not find on the bill here is parking, since a spot is included.',
                       'The spot is included, so the matter of where the car sleeps is settled on day one.']),
 'dog_onsite': ('dog',
                'inside',
                ['The building has a {dogthing} of its own, so the early walk can be an elevator ride.',
                 'For the dog: a {dogthing} on site.',
                 'A {dogthing} on the property means the last walk of the night is a short one.',
                 'Rainy mornings are easier here, with a {dogthing} right on the grounds.',
                 'Your dog gets a {dogthing} without either of you crossing a street.',
                 'There is a {dogthing} on site, and a new puppy will use it several times a day.',
                 'Leash, elevator, {dogthing}: the building keeps one on the property.',
                 'The property has its own {dogthing}, which makes weekday exercise simple.']),
 'garage_priced': ('parking',
                   'inside',
                   ['The car gets a garage here, at {fee} a month.',
                    'Pull in, park in the garage, go upstairs, for {fee} a month.',
                    'Garage parking is {fee} a month, and the price is right there on the page.',
                    'For {fee} a month your car sleeps indoors.',
                    'You love that car, and here it gets a garage for {fee} a month.',
                    'A garage spot runs {fee} a month, so you can budget for it today.',
                    'No circling the block: the garage is {fee} a month.',
                    'They publish the garage price, {fee} a month, which makes the car easy to plan for.']),
 'garage_unpriced': ('parking',
                     'inside',
                     ['The car gets a garage here, though the fee is not published.',
                      'Pull in, park in the garage, go upstairs, though the listing does not publish the fee.',
                      'There is a garage for the car, and the fee is not published, so ask.',
                      'Your car would sleep indoors here, at a price the listing does not publish.',
                      'A garage comes with the building, and what it costs is not published yet.',
                      'You love that car, and here it gets a garage, with the monthly fee not published.',
                      'The listing promises a garage and does not publish the fee, so get the number in writing.',
                      'Indoor parking is on offer, though the fee is not published anywhere we could read.',
                      'A garage is the good news, and the unpublished fee is the thing to ask about.',
                      'The building has a garage, with the fee not published on the listing.']),
 'pool': ('pool',
          'inside',
          ['There is a pool, and yes, you would use it.',
           'A pool comes with the building.',
           'Summer weekends are handled: the building has a pool.',
           'The building has a pool, which is a nice thing to come home to in July.',
           'You get a pool here, and your friends will find reasons to visit.',
           'A pool is part of the package in this building.',
           'After a day at the desk, the pool is right there on the property.',
           'Pack a swimsuit, because this building has a pool.']),
 'front_desk': ('doorman',
                'inside',
                ['Someone is at the front desk around the clock.',
                 'The front desk is staffed 24 hours, so a late arrival is never a lonely one.',
                 'There is a person at the desk day and night.',
                 'A 24-hour front desk means your packages and your late nights are both looked after.',
                 'Whatever time you come home, somebody is at the desk.',
                 'The lobby is staffed at every hour.',
                 'Deliveries land with a person here, since the desk never closes.',
                 'A staffed desk, all day and all night, comes with this building.']),
 'doorman': ('doorman',
             'inside',
             ['There is a doorman at the front door.',
              'A doorman greets you here, which helps with packages and late arrivals.',
              'The building has a doorman, a small thing that changes how coming home feels.',
              'Someone holds the door in this building.',
              'You get a doorman, so there is a familiar face at the end of the day.',
              'This is a doorman building.',
              'A doorman is on the payroll here, good news for anyone expecting deliveries.',
              'The front door comes with a doorman.']),
 'laundry': ('laundry',
             'inside',
             ['Washer and dryer inside the apartment, so no laundry-room trips.',
              'The washer and dryer are in the unit.',
              'Laundry happens at home here, on your schedule.',
              'You get your own washer and dryer, which you will appreciate every single week.',
              'No quarters, no laundry room: the machines are in the apartment.',
              'There is a washer and dryer in the unit, and a dog owner does a lot of laundry.',
              'Your own machines, inside your own door.',
              'In-unit laundry is on the list here.']),
 'covered': ('parking',
             'inside',
             ['Covered parking for the car{ptail}.',
              'The car gets a roof over it here{ptail}.',
              'Parking is covered at this building{ptail}.',
              'No scraping ice off the windshield, since the parking is covered{ptail}.',
              'Your car parks under cover{ptail}.',
              'They offer covered parking{ptail}.',
              'A covered spot is available for the car{ptail}.',
              'There is covered parking on the property{ptail}.']),
 'dog_no_limit': ('dog',
                  'inside',
                  ['Dogs are welcome with no weight limit.',
                   'No weight limit on dogs here, so the puppy can grow into whatever it becomes.',
                   'The pet policy sets no weight limit, which keeps your choice of dog open.',
                   'Big dog, small dog, the building does not mind: there is no weight limit.',
                   'You can pick the dog you want, because the policy has no weight limit.',
                   'There is no weight cap on dogs in this building.',
                   'The listing puts no weight limit on dogs, and that is worth noticing.',
                   'Any size of dog is fine by the policy here, with no weight limit.']),
 'newer': ('newer',
           'inside',
           ['The building dates from {built}, so it is among the newer ones you will see.',
            'This is a newer building, finished in {built}.',
            "Construction finished in {built}, so you would be an early tenant in the building's life.",
            'A {built} building, with the newer feel that comes with it.',
            'The building went up in {built}.',
            "You would be living in a building from {built}, young by this region's standards.",
            'It is a recent building, completed in {built}.',
            'Finished in {built}, this is the newer end of what is out there.']),
 'lot': ('parking',
         'inside',
         ["The car goes in the building's lot{ptail}.",
          'There is a lot on the property for the car{ptail}.',
          'Parking is in an on-site lot{ptail}.',
          'Your car gets a space in the lot{ptail}.',
          'The building has its own lot{ptail}.',
          "You would park in the building's lot{ptail}.",
          'Off-street parking is a lot on the grounds{ptail}.',
          'For the car, there is a lot on site{ptail}.']),
 'lounge': ('work',
            'inside',
            ['When the apartment gets small on a workday, the building has a lounge or coworking room.',
             'There is a lounge or coworking space in the building, handy for someone who works from home.',
             'You work from home, and this building gives you a second place to do it.',
             'A shared lounge or work room comes with the building, for the days you need new walls.',
             'The building has a common lounge or coworking area, so video calls have a backup spot.',
             'For work-from-home days there is a resident lounge or coworking room.',
             'Some mornings you will want to work outside the apartment, and the building has a room for that.',
             'A lounge or coworking room on site means the desk is optional some days.']),
 'gym': ('gym',
         'inside',
         ['There is a gym in the building.',
          'The gym is an elevator ride away.',
          'A gym comes with the building, which helps on work-from-home days.',
          'You can skip the gym down the road, because the building has its own.',
          'The building keeps a gym for residents.',
          "A workout is close, in the building's own gym.",
          'On-site gym, so the commute to exercise is the elevator.',
          'A fitness room on the property saves you a membership somewhere else.']),
 'dogpark_near': ('dog',
                  'around',
                  ['{dogpark} is {dogpark_mi} miles away, close enough for the first walk of the day.',
                   "The dog's morning is easy: {dogpark}, {dogpark_mi} miles from the door.",
                   'A proper run for the dog is {dogpark_mi} miles off at {dogpark}.',
                   'You can reach {dogpark} on foot, {dogpark_mi} miles away, before your first meeting.',
                   'Off-leash time is close here, with {dogpark} {dogpark_mi} miles from the lobby.',
                   'For a puppy with energy to burn, {dogpark} is {dogpark_mi} miles away.',
                   'It is {dogpark_mi} miles to {dogpark}, a walk the dog will learn fast.',
                   'Lunch-break fetch is realistic here: {dogpark} sits {dogpark_mi} miles away.']),
 'food': ('food',
          'around',
          ['About {rest} restaurants sit within a {w10}.',
           'Dinner is a walk: about {rest} restaurants within a {w10} of the door.',
           'You could eat out for weeks without repeating, with about {rest} restaurants a {w10} or less away.',
           'Step outside and there are about {rest} restaurants within a {w10}.',
           'For nights you do not cook, about {rest} restaurants are a {w10} or closer.',
           'The block feeds you well, with about {rest} restaurants inside a {w10}.',
           'Saturday dinner needs no car here: about {rest} restaurants within a {w10}.',
           'Count about {rest} restaurants within a {w10} of this address.']),
 'park_near': ('green',
               'around',
               ['{park} is about {park_mins} on foot.',
                'The morning walk reaches {park} in about {park_mins}.',
                'Green is close: about {park_mins} to {park}.',
                'You and the dog are about {park_mins} from {park}.',
                'It is about {park_mins} on foot to {park}, short enough for a lunch-break loop.',
                'About {park_mins} out the door, you are at {park}.',
                'A quick walk, about {park_mins}, puts you in {park}.',
                'For daily walks, {park} is about {park_mins} away.']),
 'station': ('train',
             'around',
             ['The train at {station} is {station_mi} miles away, for the days you would rather not drive.',
              'A train is close: {station}, {station_mi} miles from the door.',
              'You can walk to the train at {station}, {station_mi} miles off.',
              'Friends coming by train get off at {station}, {station_mi} miles away.',
              'The car can stay parked some days, with the train at {station} {station_mi} miles away.',
              'It is {station_mi} miles to the train at {station}.',
              'For a night out without the car, {station} is {station_mi} miles from the lobby.',
              'The nearest train stop, {station}, is {station_mi} miles away.']),
 'errands': ('errands',
             'around',
             ['{market} is {market_mi} miles away, so groceries are a walk.',
              'Groceries are close: {market}, {market_mi} miles from the door.',
              'You can carry the groceries home from {market}, {market_mi} miles off.',
              'It is {market_mi} miles to {market}, which makes a forgotten ingredient a small problem.',
              'The weekly shop is a short trip, with {market} {market_mi} miles away.',
              'For dog food and dinner both, {market} is {market_mi} miles from the lobby.',
              'A supermarket, {market}, sits {market_mi} miles away.',
              'The nearest supermarket is {market}, {market_mi} miles off.']),
 'dated': ('newer',
           'inside',
           ['The building dates from {built}.',
            'It went up in {built}.',
            'This is a {built} building.',
            'Built in {built}, it has been here a while.',
            'The building has stood since {built}.',
            'Construction dates to {built}.',
            'A building from {built}.',
            'It was finished in {built}.']),
 'plain': ('plain',
           'inside',
           ['The listing says little about the building itself, so the tour has to fill that in.',
            'Few building details are published, which makes the visit the real introduction.',
            'On paper the building keeps quiet about itself, so look around when you go.',
            'There is little on the page about the building beyond the apartment.',
            "The building's own features are thinly described, so ask what comes with the lease.",
            'What the building offers beyond the unit is mostly unlisted.',
            'Details on the building are sparse, so bring your list of things to ask.',
            'The page describes the apartment more than the building around it.']),
 'park_walk': ('green',
               'around',
               ['The nearest park, {park}, is about {park_mins} on foot.',
                'For green, {park} is about {park_mins} away on foot.',
                'A walk of about {park_mins} gets you to {park}.',
                '{park} sits about {park_mins} from the door on foot.',
                'Count about {park_mins} on foot to reach {park}.',
                "The dog's nearest park is {park}, about {park_mins} away on foot.",
                'Out the door, {park} is about {park_mins} on foot.',
                'Green is {park}, about {park_mins} of walking.']),
 'around_plain': ('street',
                  'around',
                  ['What is around the door is for the tour to show you.',
                   'Walk the block when you visit, because the page says little about it.',
                   'The surroundings are best judged on foot, on the day you tour.',
                   'See the street for yourself before you decide.',
                   'Give yourself a few minutes outside the building when you go.',
                   'The neighborhood page has the wider picture of what is nearby.',
                   'Look at what is within a short walk when you visit.',
                   "Take the dog's route around the block before you sign."])}

# CATCHES[kind] = [sentences]. One sentence each, about the unit's own open question. An unknown is an "ask".
# A sentence states a reason only where the unit's own fields give that reason (see catch_options and CATCH_BASIS).
CATCHES = {'confirm:live check': ['We have not re-checked this listing live yet, so the price and the date are as first '
                        'collected.',
                        'The price and move-in date here are from our first read and still await a fresh check.',
                        'This listing is waiting on our live re-check, so confirm the rent and the date when you '
                        'call.',
                        'Take the numbers as a first reading, because we have not been back to verify them.',
                        "A second look at this listing is still pending, so ask the office to confirm today's rent.",
                        'Until we re-check it, treat the rent and the availability date as a snapshot.',
                        'The figures are from our first pass and not yet re-verified, so open your call by '
                        'confirming them.',
                        'We owe this listing a fresh check, and until then the rent and date are provisional.',
                         'Nobody has looked at this listing a second time yet, so confirm the rent before you plan around it.',
                         'This one is still in line for a live check, so the price could have moved since it was collected.',
                         'The rent and date come from a single reading, so have the office confirm both.',
                         'A live re-check is still outstanding here, so call to make sure the listing stands.',
                         'What you see was collected once and has yet to be looked at again, so verify it by phone.',
                         'The listing has yet to be re-verified, so start by asking whether it is still offered at this rent.'],
 'confirm:elevator': ['Elevator access for this exact unit is not confirmed, so ask before you tour.',
                      'The elevator is the open item here: get a clear yes for this unit before you visit.',
                      'You said no stairs, and the elevator for this unit is still unconfirmed, so ask first.',
                      'Make the first thing you ask whether an elevator reaches this apartment, because we could not '
                      'confirm it.',
                      'Nothing we read settles whether this unit has elevator access, so open with that.',
                      'Hold off on booking the tour until the office confirms an elevator serves this unit.',
                      'Whether an elevator reaches this apartment is unanswered, and it is a dealbreaker, so ask '
                      'early.',
                      'Ask them to put elevator access for this unit in writing, since it is not confirmed yet.'],
 'confirm:availability': ['This is a floor plan and not a specific apartment yet, so ask which unit, which floor and '
                          'what date.',
                          'What is advertised is a layout, so ask the office which actual unit is open and when.',
                          'The listing shows a plan type only, so the unit number, the floor and the date are yours '
                          'to ask for.',
                          'No specific apartment is attached to this price yet, so get a unit number before you '
                          'tour.',
                          'You would be touring a model of this plan unless you ask which exact unit is available.',
                          'Pin down the actual unit behind this floor plan, including its floor and its move-in '
                          'date.',
                          'The price is for a plan, and the apartment itself is still unnamed, so ask which unit it '
                          'is.',
                          'Ask them to name the unit, because right now this is a floor plan with a price on it.'],
 'confirm:eligibility': ['Who qualifies to rent here is not settled, so ask whether there is an income limit before '
                         'you tour.',
                         'Ask first whether this unit is open to any renter, because an income limit is possible '
                         'here.',
                         'Eligibility is the open item: confirm with the office that you can apply at all.',
                         'There are signs this building has income rules, so check that you qualify before you get '
                         'attached.',
                         'Before the tour, have the office tell you whether an income limit applies to this unit.',
                         'We could not settle whether this unit has an income cap, so start your call there.',
                         'An income restriction is possible on this unit, so confirm you are eligible before '
                         'spending time on it.',
                         'The office needs to confirm that this apartment is open to all renters, since what we read '
                         'conflicts.'],
 'confirm:question': ['One thing is unconfirmed, so ask the leasing office this: {q}',
                      'Before you tour, put this to the office: {q}',
                      'There is an open item here, and the way to close it is to ask: {q}',
                      'Start your call with this, because we could not confirm it: {q}',
                      'The thing to settle first is this: {q}',
                      'Ask the office directly, since nothing we read answers it: {q}',
                      'Hold your plans until someone answers this for you: {q}',
                      'A single unanswered point stands between you and a tour: {q}'],
 'confirm:other': ['One thing about this listing is unconfirmed, so call the leasing office before you tour.',
                   'There is an open item on this listing, so ask the office about it before you visit.',
                   'Something here still needs confirming, so phone ahead.',
                   'This listing has a loose end, and a call to the office should tie it off.',
                   'Before you tour, have the office settle the open item on this listing.',
                   'We could not confirm everything about this place, so check with the office first.',
                   'Hold your plans until the office answers the open item here.',
                   'A detail on this listing is unverified, so start with a phone call.'],
 'rent:net_effective': ['The price shown is a net-effective rent, so the monthly bill will be higher than it looks, '
                        'and you should ask for the gross rent.',
                        'This rent is averaged over a free period, so ask what you actually pay in a normal month.',
                        'The advertised number already has the special baked in, which means the real monthly rent '
                        'is higher.',
                        'Read this price as an average after free time, and get the full monthly rent before you '
                        'compare.',
                        'What you see is a net-effective figure, so the check you write each month will be bigger.',
                        'The listing quotes rent after its discount, so ask for the gross rent and budget on that.',
                        'This is a discounted average and the lease will state a higher monthly rent, so ask for '
                        'that number.',
                        'Do your math on the gross rent, because the price shown spreads a free period across the '
                        'lease.'],
 'rent:needs_call': ['The page does not say whether the advertised rent is before or after its special, so ask for '
                     'the full monthly rent.',
                     'There is a special on this listing and no word on whether the price already includes it, so '
                     'ask what the rent is in a normal month.',
                     'Ask whether the advertised rent is the full monthly rent or an average after the free period, '
                     'because the page does not say.',
                     'A special is attached to this price and its effect is unstated, so get the regular rent in '
                     'writing.',
                     'The rent could be a before-special or an after-special number, and only the office can tell '
                     'you which.',
                     'Until they tell you what a month costs once the offer ends, treat this price as a maybe.',
                     'The offer muddies the price, so start by asking what the lease will say you owe each month.',
                     'Nothing on the page reveals whether the special is already in this rent, so make them spell it '
                     'out.',
                     'Get the first full payment and the regular monthly rent from the office, since the special '
                     'leaves both unclear.',
                     'This price has a special riding on it, and the listing never says how the pieces fit together, '
                     'so ask.',
                     'Compare this one only after you have the rent without the special, which the page leaves out.',
                     'The honest status of this price is unconfirmed, because the listing does not explain how its '
                     'special applies.'],
 'unknown:costs_tight': ['{Names} {verb} not published, and with only {margin} under your cap the real all-in could '
                         'go over, so ask.',
                         'With just {margin} of room under your cap, the unpublished {bare} could tip this over, so '
                         'get the numbers.',
                         'The all-in here leaves out {names}, and {margin} of headroom could fall short of covering '
                         'them.',
                         'Ask for {names} in dollars, because only {margin} separates this place from your ceiling.',
                         'This fits your budget by {margin} on paper, before {names}, which the listing does not '
                         'give.',
                         'The listing omits {names}, and you have {margin} to absorb them before you pass your cap.',
                         'Get {names} confirmed first, since the cushion under your cap is only {margin}.',
                         'On paper you are {margin} under your limit, and the missing {bare} could easily eat that.'],
 'lease_term': ['This price is tied to a {months}-month lease, so ask what other terms cost.',
                'The rent shown is for a {months}-month lease, so ask for the 12-month price too.',
                'You are looking at a {months}-month lease price, and a different term could cost more.',
                'The listed rent assumes a {months}-month lease, so check what the term you want would run.',
                'Mind the term: this rent goes with a {months}-month lease.',
                'A {months}-month lease is what earns this price, so ask about the standard term.',
                'The number on the page is the {months}-month rate, so ask how other lease lengths are priced.',
                'Before you compare, ask what this costs on a 12-month lease, since the price shown is for {months} '
                'months.'],
 'weak:space': ['The weak spot is size, at {sqft} square feet for you, a desk and a dog.',
                'At {sqft} square feet, you, the desk and the dog will be sharing closely.',
                'The trade is room: {sqft} square feet has to hold your office and your dog.',
                'Measure your desk before you fall for this, because {sqft} square feet goes fast.',
                'It is on the small side at {sqft} square feet, and you work from home.',
                'The catch is the floor plan, {sqft} square feet for a life that includes a home office.',
                'You would feel the {sqft} square feet on a long workday with a restless dog.',
                'Space is what you give up here, with {sqft} square feet in total.'],
 'weak:cost': ['The weak spot is cost: about {price} all in leaves only about {margin} under your cap.',
               'At about {price} all in, you are within about {margin} of your ceiling.',
               'The trade is the bill, about {price} a month all in, with about {margin} to spare.',
               'This sits near the top of your budget, about {margin} under the cap at about {price} all in.',
               'There is little slack here: about {price} all in, about {margin} from your limit.',
               'The catch is the price, about {price} a month all in, only about {margin} below your cap.',
               'You would be spending nearly all of your budget, with about {margin} left after about {price} all '
               'in.',
               'Money is the tight part, at about {price} all in and about {margin} of room.'],
 'none': ['Nothing stands out as a problem on paper, which is exactly when a tour matters most.',
          'The listing gives no caution to pass on, so let the tour look for one.',
          'On paper this is clean, and the visit is where you test that.',
          'The listing holds up, so use the tour to check what a page cannot show, like light and noise.',
          'No red flag in the data, which leaves the in-person look as the real test.',
          'The catch, if there is one, will show on the tour, because the listing offers nothing to warn you about.',
          'A search for the weak spot in this listing found none, so look for it in person.',
          'Everything checks out in writing, so bring your skepticism to the walkthrough.'],
 'confirm:dogs conflict': ['Listing sites disagree on whether dogs are allowed here, so get the dog policy in '
                           'writing.',
                           'The dog policy is the open item: the sources conflict, so ask for a written yes.',
                           'Before anything else, have the office confirm in writing that your dog is welcome, '
                           'because the listings do not agree.',
                           'We found mixed signals on dogs here, so settle that with the office before you tour.',
                           'Whether dogs are allowed is not settled for this place, and it has to be before you '
                           'apply.',
                           'The listings contradict each other on dogs, so let the leasing office break the tie in '
                           'writing.',
                           'Keep your heart out of this one until someone at the office confirms the dog policy.',
                           'A firm answer on dogs is still missing here, since what we read about the policy '
                           'conflicts.'],
 'confirm:dogs reason': ['{Reason}, so get a written yes for your dog before you tour.',
                         'Ask for a clear yes on dogs in writing, because {reason}.',
                         'On dogs, {reason}, which is short of a yes, so ask.',
                         'Before you get attached, settle the dog: {reason}.',
                         'The open item is the dog, since {reason}.',
                         'A dog is still unconfirmed here: {reason}, so have the office say yes in writing.',
                         'Make the dog your opening topic, because {reason}.',
                         'Have the office confirm your dog is welcome, given that {reason}.'],
 'confirm:dogs open': ['Whether dogs are allowed is not settled for this unit, so get the policy in writing.',
                       'The dog policy is the open item here, so ask the office for it in an email.',
                       'Dogs are still to confirm at this address, so have the office say yes before you tour.',
                       'Until the office confirms the dog policy, treat this one as a maybe.',
                       'The pet rules are unclear here, so ask for a written yes on dogs.',
                       'Get the dog policy from the leasing office directly, because the listing leaves it '
                       'unsettled.',
                       'Make the dog policy your opening topic, since nothing on the page settles it.',
                       'Ask them to confirm that a dog is welcome, in writing, before you apply.'],
 'floor:unpublished': ['The floor is not published, so confirm it is above the ground floor.',
                       'No floor is given for this unit, so ask which floor it is on before you tour.',
                       'Ask which floor this apartment sits on, since the listing leaves it out.',
                       'The listing skips the floor, and you want to be above ground level, so ask.',
                       'Confirm the floor with the office, because the page does not give it.',
                       'Which floor this is remains unstated, so get it before you visit.',
                       'You asked for no ground-floor units, and this listing does not state its floor.',
                       'Get the floor number in writing, since it is missing from the listing.'],
 'floor:inferred': ['Floor {floor} is our reading of the unit number, so confirm it on the tour.',
                    'No page states the floor, and the unit number suggests floor {floor}, so check.',
                    'The floor is read from the unit number only, floor {floor} by that reading, so ask.',
                    'Ask them to confirm this is floor {floor}, because the listing never says so itself.',
                    'The unit number points to floor {floor}, which the listing does not state, so verify it.',
                    'Treat floor {floor} as a guess from the unit number until the office confirms it.',
                    'Confirm the floor when you call, since floor {floor} comes from the unit number alone.',
                    'You want to be above the ground floor, and floor {floor} is only inferred here, so ask.',
                    'Have the office state the floor, because floor {floor} is an inference from the unit number.',
                    'Nothing on the listing gives the floor, and floor {floor} is only what the unit number '
                    'implies.']}

# SUBS[section] = [(case, [lines])]: one short line (at most 14 words, no numbers) under a section headline.
SUBS = {'cost': [('net_effective',
           ['The price shown is after a discount, so ask for the real monthly rent.',
            'This is a net-effective number, and the monthly bill will be higher.',
            'The rent is an average over a free period, so budget on the gross.',
            'Ask for the gross rent, because this figure already has the special in it.',
            'What you pay each month is more than the number shown here.',
            'A discounted average, so get the lease rent before you compare.',
            'The special is baked into this price, so the real rent runs higher.',
            'Do the math on the full rent, since this spreads out a free period.']),
          ('ambiguous_rent',
           ['There is a special here, so ask what a normal month costs.',
            'Ask whether this price is before or after the free period.',
            'A special clouds this number, so get the regular rent in writing.',
            'The offer and the rent are tangled, so ask them to separate the pieces.',
            'Find out what you owe monthly once the special runs out.',
            'This price rides on a special, and the page never explains how.',
            'Treat the rent as unconfirmed until the office explains the offer.',
            'Ask for the rent without the special before you compare anything.',
            'The headline price has an offer attached, so ask for the plain number.',
            'Get the first full payment in writing, because the special blurs it.',
            'Nobody says whether the special is already counted, so ask.',
            'The deal is real, and the true monthly rent is still unanswered.',
            'Make them spell out the rent after the offer ends.',
            'Before or after the special is what this price leaves open.']),
          ('tight',
           ['Right at your ceiling, so a single surprise fee tips it over.',
            'No room to spare here, so every unlisted fee matters.',
            'This sits at the top of your budget, with nothing left for extras.',
            'The bill nearly touches your cap, so ask about every fee.',
            'There is almost no cushion under your limit here.',
            'Any fee they forgot to list would push this past your cap.',
            'Budget-wise this is the edge, so get the full bill in writing.',
            'You would be spending right up to your limit each month.']),
          ('unpublished',
           ['Some costs are unpublished, so treat this number as a floor.',
            'They leave some fees off the page, so ask for the full monthly bill.',
            'The total is missing a few lines, so it could climb.',
            'Ask what the listing leaves out before you trust the total.',
            'This is the bill so far, with some fees still unpublished.',
            'A few charges are blank, so the real number could run higher.',
            'The page skips some fees, so get them from the office.',
            'Count this as a starting figure until the missing fees come in.',
            'Some fees go unlisted here, so ask for the complete monthly cost.',
            'There are gaps in the fee list, and each is something to ask.',
            'The all-in is honest about what it knows and silent on the rest.',
            'Fill in the unlisted fees before you compare this with the others.']),
          ('roomy',
           ['Leaves real room under your ceiling for the things nobody lists.',
            'Comfortably inside your budget, with money left for the sofa.',
            'Well under your cap, so a surprise fee would not sink it.',
            'There is slack in the budget here, and slack is a comfort.',
            'You keep a good piece of your budget every month.',
            'The bill leaves room for furniture, vet visits and a night out.',
            'Easy on your limit, with a cushion to spare.',
            'This place gives your budget room to breathe.'])],
 'parking': [('unknown',
              ['They say nothing about parking, so make it your opening question.',
               'Parking is not published here, so ask before you fall for it.',
               'No word on where the car goes, so ask first.',
               'The listing is silent on parking, so the question is yours to ask.',
               'Where the car sleeps is unanswered, so ask before the tour.',
               'Ask what parking exists and what it costs, since the page skips it.',
               'The car is the open question at this address.',
               'Ask for the parking answer in writing before anything else.']),
             ('included',
              ['The spot comes with the lease, so the car costs nothing extra.',
               'Parking is part of the deal, so there is no monthly fee to chase.',
               'A spot is included, which settles the car on day one.',
               'No parking bill here, since the lease includes a space.',
               'The car is taken care of in the rent.',
               'Your space is in the lease, with nothing added for it.',
               'They include parking, and that is money you keep.',
               'The spot is yours with the apartment.']),
             ('garage_priced',
              ['Your car sleeps indoors, and you never circle the block.',
               'Pull in, park under a roof, and the day is over.',
               'A garage with the price on the page, so you can budget now.',
               'Indoor parking at a stated price, which is how it should be.',
               'The car gets a garage, and they tell you what it costs.',
               'No hunting for a spot, and no guessing at the fee.',
               'Garage parking with a published price, an easy yes for a driver.',
               "The garage fee is listed, so the car's cost is settled."]),
             ('garage_unpriced',
              ["Indoor parking, but they don't publish the price, so ask before you commit.",
               'A garage with no price listed, so get the monthly fee in writing.',
               'The car gets a garage, and the fee is still a question.',
               'There is a garage, with the price missing from the page.',
               'A garage is promised, so ask what it adds each month.',
               'Indoor parking exists, and the cost is yours to ask about.',
               'The garage is real and its fee is unpublished, so ask.',
               'Your car parks inside, at a price they have not shared.',
               'Ask for the garage fee before you count this as affordable.',
               'Garage, yes, and the monthly charge is not published.',
               'They list a garage and skip the price, so ask for it.',
               'The garage fee is the missing number here.',
               'A roof for the car, with the fee left for you to ask.',
               'Get the garage price from the office, because the listing leaves it out.']),
             ('covered_priced',
              ['A roof over the car, with the price on the page.',
               'Covered parking, so no scraping ice in January.',
               'The car parks under cover at a stated price.',
               'Covered and priced, which makes the car easy to budget.',
               'Your car stays out of the weather, and you know the fee.',
               'A covered spot with a published price.',
               'Rain or snow, the car is under a roof, at a listed fee.',
               'They cover the car and they print the price.']),
             ('covered_unpriced',
              ["Covered parking, though they don't publish the price, so ask.",
               'The car gets a roof, and the fee is a question for the office.',
               'A covered spot exists, with the price left off the page.',
               'Ask what covered parking costs, since the listing does not say.',
               'Under cover, yes, and the monthly fee is still unknown.',
               'The covered parking has no price listed, so get it in writing.',
               'Your car stays dry here, at a fee you will have to ask for.',
               'Covered parking is offered, and its cost is the missing piece.']),
             ('lot_priced',
              ["A spot in the building's lot, so you are off the street.",
               'Lot parking with a listed price, which beats hunting the curb.',
               'The car gets a lot space at a stated fee.',
               'Off-street parking in the lot, with the price published.',
               "You park in the building's lot, and you know what it costs.",
               'A lot on site and a fee on the page.',
               'The lot keeps you off the curb, at a listed price.',
               'Parking is a lot space, priced in the listing.']),
             ('lot_unpriced',
              ['A lot on site, but no price on the page, so ask.',
               'There is a lot, and what it costs is still a question.',
               'The car goes in the lot, at a fee they have not published.',
               'Ask what a lot space costs, since the listing skips it.',
               'Off-street parking exists, with the price missing.',
               'A lot is listed and its fee is left out, so ask.',
               'You would park in the lot, and the cost is yours to confirm.',
               'The lot has no posted price, so get the fee in writing.']),
             ('onsite_unpriced',
              ['Parking exists on site, and the details are yours to ask for.',
               'They mention parking and little else, so ask what kind and how much.',
               'There is parking, with the type and the fee both unstated.',
               'Ask what the on-site parking is and what it costs.',
               'Parking is promised in a word, so get the specifics.',
               'The listing says parking and stops there, so ask for the rest.',
               'On-site parking, with everything else about it left to ask.',
               'Some parking exists here, and the office has to fill in the details.'])],
 'dog': [('conflicting',
          ['Listings disagree about dogs here, so confirm before you tour.',
           'The sources conflict on dogs, so only a written answer counts.',
           'Ask them to confirm dogs are allowed, because the listings differ.',
           'Mixed signals on dogs, so ask the office to settle it.',
           'Two sources, two answers on dogs, so get it in writing.',
           'The dog policy reads differently from site to site, so ask.',
           'Conflicting listings on dogs make a written yes essential.',
           'Dogs are a question mark here until the office breaks the tie.']),
         ('unsettled',
          ['The dog policy is unsettled, so get a yes in writing.',
           'Whether dogs are welcome is not settled, so ask first.',
           'Get the dog policy confirmed before you get attached.',
           'Dogs are a question mark here until the office says yes.',
           'A clear yes on dogs is still missing, so ask for it.',
           'Confirm your dog is welcome before you book the tour.',
           'The page stops short of a yes on dogs, so ask.',
           'Ask for the dog policy in writing, because it is still open.']),
         ('onsite',
          ["The dog's first walk of the day can start in the elevator.",
           'A place for the dog without leaving the property.',
           'The building keeps a spot for dogs on the grounds.',
           'Late-night walks can be short ones, right on the property.',
           'Your dog gets its own corner of the property.',
           'On rainy mornings, the on-site dog area earns its keep.',
           'The dog has somewhere to go that is still home.',
           "A dog area on site makes a puppy's schedule easier."]),
         ('near_run',
          ['A dog run is close enough for a quick morning lap.',
           'The dog gets a proper run before your first meeting.',
           'Within walking reach of the door, there is a dog run.',
           'Off-leash time is a short walk away.',
           'The nearest dog run is close, which a puppy will love.',
           'You can make the dog run a daily habit from here.',
           'Fetch before work is realistic at this address.',
           'The dog run is near enough to visit on a lunch break.']),
         ('small_only',
          ['The page says small dogs and gives no weight, so ask for the number.',
           'Small dogs are welcome, and the exact limit is a question to ask.',
           'They say small dogs only, without saying how small.',
           'Ask what small means in pounds before you choose a puppy.',
           'The policy mentions small dogs and no weight, so get the figure.',
           'Fine for small dogs, with the cutoff left unstated.',
           'Find out the weight behind the words small dog.',
           'A small-dog policy with no number, so ask for the limit.']),
         ('weight_limit',
          ['There is a weight limit, so check it against the dog you choose.',
           'Dogs are welcome up to a weight limit, so choose the puppy accordingly.',
           "The policy caps a dog's weight, so think about adult size.",
           'Mind the weight limit when you pick a breed.',
           "Dogs are allowed under a set weight, so know your puppy's future.",
           'A weight limit applies, and puppies grow.',
           'Check the adult weight of your dog against the policy here.',
           'The dog policy has a weight ceiling to plan around.']),
         ('pet_rent_unknown',
          ["Dogs are welcome, though they don't publish the pet rent, so ask.",
           'No pet rent on the page, so ask what the dog adds each month.',
           'The dog is welcome, and the monthly pet charge is unstated.',
           'Ask about pet rent and any pet fee before you apply.',
           'Pet rent is the missing line, so get it from the office.',
           'They allow dogs and leave the pet rent off the page.',
           'What the dog costs each month here is still a question.',
           'Dogs, yes, and the pet rent is yours to ask about.',
           'The pet charge is unpublished, so add it to your call list.',
           'Find out the pet rent, because the listing skips it.'])],
 'building': [('front_desk',
               ['Someone is at the desk when you come home late.',
                'A staffed front desk, which also means your packages wait for you.',
                'The desk is staffed around the clock.',
                'There is always a person in the lobby.',
                'Day or night, somebody is at the front desk.',
                'A desk that never closes, handy for deliveries and late nights.',
                'Packages and visitors meet a person here, at any hour.',
                'The lobby has staff at all hours.']),
              ('doorman',
               ['A doorman at the door, and a familiar face after a long day.',
                'There is a doorman, so deliveries and late arrivals are easier.',
                'This is a doorman building.',
                'Someone holds the door, which you will come to like.',
                'A doorman comes with the address.',
                'The front door is staffed by a doorman.',
                'You get a doorman, a small daily comfort.',
                'A doorman greets you on the way in.']),
              ('pool_laundry',
               ['A pool on the property and laundry in your own apartment.',
                'Laundry at home and a pool for the weekend.',
                'Your own washer and dryer, plus a pool.',
                'The machines are in the unit and the pool is on the grounds.',
                'In-unit laundry for weekdays, a pool for weekends.',
                'A pool to swim in and no laundry room to visit.',
                'A pool outside and a washer and dryer inside your own door.',
                'Wash at home, then go for a swim.']),
              ('laundry',
               ['Laundry happens in your own apartment, on your own schedule.',
                'The washer and dryer are yours alone.',
                'In-unit laundry, so no trips with a basket.',
                'Your own machines, behind your own door.',
                'A washer and dryer in the unit, which a dog owner will use.',
                'No laundry room runs from this apartment.',
                'The laundry is in the apartment.',
                'You can run a load without leaving home.']),
              ('pool',
               ['A pool comes with the building, and summer gets easier.',
                'There is a pool, and yes, you would use it.',
                'The building has a pool for residents.',
                'Summer weekends have a pool attached.',
                'A pool on the property, for hot days and visiting friends.',
                'You get a pool with this address.',
                'The pool is part of the package.',
                'After work in July, there is a pool waiting.']),
              ('gym',
               ['A gym in the building, which helps in February.',
                'The gym is an elevator ride away.',
                'There is a gym on the property.',
                'A resident gym comes with the building.',
                'You can work out without leaving the building.',
                "The building's gym makes a membership optional.",
                'A fitness room is part of the building.',
                "Exercise is close, in the building's own gym."])]}

# The second sentence: the price and one or two more facts. {extras} is a list of noun phrases.
SECOND_WITH_PRICE = [
    "It runs about {price} a month all in, with {extras}.",
    "About {price} a month all in, and you get {extras}.",
    "Add {extras}, at about {price} a month all in.",
    "The all-in is about {price} a month, with {extras}.",
    "You also get {extras}, for about {price} a month all in.",
    "The monthly total is about {price} all in, and it comes with {extras}.",
    "Figure about {price} a month all in, alongside {extras}.",
    "Expect about {price} a month all in, with {extras} as well.",
    "It has {extras}, and the bill is about {price} a month all in.",
    "At about {price} a month all in, it also offers {extras}.",
    "Budget about {price} a month all in, and count {extras} in its favor.",
    "The rest of the story: {extras}, at about {price} a month all in.",
    "On top of that, {extras}, for about {price} a month all in.",
    "All in, it comes to about {price} a month, with {extras}.",
    "Beyond that you get {extras}, and the all-in is about {price} a month.",
    "Count on about {price} a month all in, and note {extras}.",
    "Then the practical side: about {price} a month all in, with {extras}.",
    "You would pay about {price} a month all in, and have {extras}.",
    "It lists {extras}, and the all-in works out to about {price} a month.",
    "The numbers: about {price} a month all in, with {extras}.",
    "With {extras}, it totals about {price} a month all in.",
    "Along with {extras}, the all-in lands at about {price} a month.",
    "Call it about {price} a month all in, and {extras} besides.",
    "For about {price} a month all in, you get {extras}.",
    "Its all-in is about {price} a month, and the listing adds {extras}.",
    "Set aside about {price} a month all in, and you also get {extras}.",
    "What comes with it: {extras}, on an all-in of about {price} a month.",
    "Round it to about {price} a month all in, with {extras} on the list.",
]
SECOND_NO_PRICE = [
    "It also has {extras}.", "You also get {extras}.", "Add {extras}.", "It comes with {extras} too.",
    "There is more: {extras}.", "The listing also gives you {extras}.", "On top of that, {extras}.",
    "Beyond that, count {extras}.", "Then there is {extras}.", "Note {extras} as well.",
]
PRICE_ONLY = [
    "It runs about {price} a month all in.", "The all-in is about {price} a month.",
    "Figure about {price} a month all in.", "Expect about {price} a month all in.",
    "The monthly total comes to about {price} all in.", "All in, that is about {price} a month.",
    "Your bill would be about {price} a month all in.", "Budget about {price} a month all in.",
    "Count on about {price} a month all in.", "That is about {price} a month once everything is counted.",
]

PATTERN_IDS = [f"{cond}_{i + 1}" for cond, (_, texts) in LEADS.items() for i in range(len(texts))]
PEER_CONDITIONS = {"cheapest", "biggest", "value", "pick", "highest", "fewest_questions", "soonest_now", "soonest_date",
                   "newest"}                              # unit against the other units of its building
BUILDING_PEER_CONDITIONS = {"only_pool", "only_garage", "only_doorman", "only_laundry", "only_dogspot", "closest_run",
                            "closest_park"}               # building against the other buildings of its neighbourhood
COVERS = {"value": {"value", "size"}}                   # support facts a lead already uses, besides its own angle

# The icon points of "About the building": POINTS[key] = (icon, topic, [wordings]). The warning is the main thing to ask.
POINTS = {
    "parking_included": ("parking", "parking", ["A parking spot is included.", "Parking comes with the lease.",
                                                "The lease includes a space for the car.", "A spot for the car, included in the lease."]),
    "garage_priced": ("parking", "parking", ["Garage parking at {fee} a month.", "A garage spot runs {fee} a month.",
                                             "Garage for the car, {fee} a month.", "Indoor parking, priced at {fee} a month."]),
    "garage_unpriced": ("parking", "parking", ["Garage parking, fee not published.", "A garage, with no price listed.",
                                               "Indoor parking, cost unpublished.", "Garage on site, fee not stated."]),
    "covered_priced": ("parking", "parking", ["Covered parking at {fee} a month.", "A covered spot runs {fee} a month.",
                                              "Parking under cover, {fee} a month.", "Covered parking, priced at {fee} a month."]),
    "covered_unpriced": ("parking", "parking", ["Covered parking, fee not published.", "A covered spot, with no price listed.",
                                                "Parking under cover, cost unpublished.", "Covered parking, fee not stated."]),
    "lot_priced": ("parking", "parking", ["Lot parking at {fee} a month.", "A lot space runs {fee} a month.",
                                          "Parking in the building's lot, {fee} a month.", "On-site lot, priced at {fee} a month."]),
    "lot_unpriced": ("parking", "parking", ["Lot parking, fee not published.", "A lot on site, with no price listed.",
                                            "Parking in the building's lot, cost unpublished.", "On-site lot, fee not stated."]),
    "onsite_unpriced": ("parking", "parking", ["Parking on site, details not published.", "Some parking exists, with no price listed.",
                                               "On-site parking, type and cost unpublished.", "Parking is mentioned, with the fee not stated."]),
    "dog_onsite": ("dog", "dogspot", ["A {dogthing} on the property.", "Its own {dogthing} for residents.",
                                      "A {dogthing} without leaving the grounds.", "On-site {dogthing} for quick walks."]),
    "dog_no_limit": ("dog", "dog", ["Dogs welcome, with no weight limit.", "No weight limit on dogs.",
                                    "Any size of dog is allowed.", "The dog policy has no weight cap."]),
    "dog_limit": ("dog", "dog", ["Dogs up to {lb} pounds.", "Dog weight limit: {lb} pounds.",
                                 "Dogs are allowed up to {lb} pounds.", "The policy takes dogs to {lb} pounds."]),
    "dog_ok": ("dog", "dog", ["Dogs are allowed.", "The building takes dogs.", "A dog-friendly policy.", "Dogs are welcome here.",
                           "Dogs are allowed by the listing.", "The policy allows dogs."]),
    "pool": ("pool", "pool", ["A pool on the property.", "The building has a pool.", "A pool for residents.", "Pool on site."]),
    "laundry": ("laundry", "laundry", ["Washer and dryer in the unit.", "In-unit laundry.", "Your own washer and dryer.",
                                       "Laundry inside the apartment.", "Machines in the apartment.",
                                       "No laundry room: the machines are in the unit."]),
    "front_desk": ("key", "doorman", ["A 24-hour front desk.", "Front desk staffed around the clock.",
                                      "Someone at the desk day and night.", "Round-the-clock desk staff."]),
    "doorman": ("key", "doorman", ["A doorman at the door.", "Doorman building.", "The front door has a doorman.", "A doorman on duty."]),
    "gym": ("heart", "gym", ["A gym in the building.", "On-site gym.", "A fitness room for residents.", "The building has its own gym.",
                             "Gym on the property.", "A gym comes with the building."]),
    "lounge": ("coffee", "lounge", ["A lounge or coworking room.", "Shared space to work outside the apartment.",
                                    "A resident lounge or work room.", "A coworking or lounge space on site.",
                                    "Lounge or coworking space for residents.", "A common room for working or relaxing."]),
    "park": ("park", "park", ["{park}, about {park_mins} on foot.", "About {park_mins} on foot to {park}.",
                              "{park} is about {park_mins} away on foot.", "A walk of about {park_mins} to {park}.",
                              "{park} is a walk of about {park_mins}.", "On foot, {park} is about {park_mins} off."]),
    "dogrun": ("dog", "dogrun", ["{dogpark}, {dogpark_mi} miles away.", "A dog run {dogpark_mi} miles off, at {dogpark}.",
                                 "{dogpark} is {dogpark_mi} miles from the door.", "It is {dogpark_mi} miles to {dogpark}."]),
    "food": ("fork", "food", ["About {rest} restaurants within a {w10}.", "Dinner on foot: about {rest} restaurants within a {w10}.",
                              "About {rest} restaurants are within a {w10}.", "Within a {w10}, about {rest} restaurants.",
                              "About {rest} restaurants a {w10} or less away.", "Restaurants within a {w10}: about {rest}."]),
    "train": ("train", "train", ["{station} train, {station_mi} miles away.", "The train at {station} is {station_mi} miles off.",
                                 "{station_mi} miles to the train at {station}.", "A train stop, {station}, {station_mi} miles away."]),
    "built": ("home", "built", ["Built in {built}.", "The building dates from {built}.", "A {built} building.", "Finished in {built}.",
                                "It dates from {built}.", "Constructed in {built}."]),
    "elevator": ("home", "elevator", ["An elevator building.", "The building has an elevator.", "Elevator access, as you asked.",
                                      "No stairs to climb: there is an elevator."]),
    "units": ("home", "units", ["{n} {apts} found in this building.", "We found {n} {apts} here.",
                                "{n} {apts} on the list in this building.", "Listings found here: {n}."]),
}
WARNINGS = {                                           # key: (topic, [wordings]); the first that applies is used
    "dog_unsettled": ("dog", ["Dogs are not confirmed here, so get a yes in writing.", "Ask for the dog policy in writing before you tour.",
                              "The dog policy is still open, so settle it first.", "Confirm that your dog is welcome before anything else."]),
    "elevator_open": ("elevator", ["Elevator access is not confirmed, so ask before you tour.", "Confirm an elevator reaches the apartment.",
                                   "Ask whether the unit has elevator access.", "The elevator is still to confirm.",
                                   "Get elevator access for the unit confirmed in writing.", "Check that an elevator serves the unit before you visit."]),
    "parking_unknown": ("parking", ["Ask where the car goes and what it costs.", "Parking is not published, so ask first.",
                                    "No word on parking, so make it your opening question.", "Find out where a car would sleep here.",
                                    "The listing never mentions parking, so ask about it.", "Where the car goes is unanswered, so ask before you tour.",
                                    "Ask whether the building has any parking at all.", "Nothing is published on parking, so raise it first."]),
    "parking_fee": ("parking", ["Ask what parking costs each month.", "The parking fee is not published, so ask.",
                                "Get the monthly parking fee in writing.", "Parking exists, and its price is still to ask.",
                                "Ask for the parking price before you tour.", "What the parking costs is not on the page, so ask.",
                                "The listing gives no parking price, so get it by phone.", "Find out the monthly charge for the car.",
                                "A parking price is missing here, so ask for it.", "Ask what a space for the car adds to the bill.",
                                "Parking is offered without a price, so ask.", "Before you budget, get the parking fee."]),
    "pet_rent": ("dogcost", ["Ask what the dog adds to the rent each month.", "Pet rent is not published, so ask.",
                             "Get the pet rent and any pet fee in writing.", "The monthly pet charge is still to ask."]),
    "fees": ("fees", ["Ask which monthly fees are added to the rent.", "Building fees are not published, so ask for them.",
                      "Get the required monthly fees in writing.", "The fee list is incomplete, so ask what is added."]),
    "weight": ("dog", ["Ask for the dog weight limit in pounds.", "The page says small dogs and gives no number, so ask.",
                       "Get the exact weight limit before you choose a puppy.", "Small dogs only, by the listing, with no weight stated."]),
    "overnight": ("street", ["The town restricts overnight street parking, so confirm your space.",
                             "Overnight street parking is limited here, so get a space in writing.",
                             "Check the town's overnight parking rule against the building's parking.",
                             "Street parking overnight is restricted, so the building must park you."]),
    "tour": ("tour", ["Ask to see the elevator, the hallways and the mail room.", "Walk the common areas before you decide.",
                      "On the tour, look at the lobby and halls as closely as the unit.",
                      "Check upkeep in the shared spaces when you visit.",
                      "Give the hallways and the elevator a look when you tour.", "See the building's shared spaces before you sign."]),
}
ANGLE_TOPIC = {"parking": "parking", "pool": "pool", "doorman": "doorman", "laundry": "laundry", "gym": "gym", "work": "lounge",
               "newer": "built", "food": "food", "train": "train", "green": "park"}   # a sentence's angle -> the point it replaces


def lead_conditions(f, peers):
    """-> [(score, condition, values to fill, fields used)]: every condition whose fact is true for this unit.
    `peers` are the units shown in the same building (this one included). Higher score = more distinctive."""
    n = len(peers)
    two = n == 2
    small = -25 if two else 0                         # "the cheaper of 2" is worth less than "the cheapest of 6"
    out = []

    def add(score, cond, vals=None, **used):
        out.append((score, cond, {"n": n, **(vals or {})}, used))

    price = usd(f["all_in"]) if f["all_in"] else None
    sqft = whole(f["sqft"]) if f["sqft"] else None
    # ---- against the other apartments shown in the same building
    if extreme(f, peers, "all_in", min):
        add(85 + small, "cheapest", {"price": price, "low": "lower" if two else "lowest"}, peers=n, all_in=f["all_in"])
    if extreme(f, peers, "sqft", max):
        add(80 + small, "biggest", {"sqft": sqft, "big": "roomier" if two else "roomiest"}, peers=n, sqft=f["sqft"])
    if n >= 3 and extreme(f, peers, "rank", min):
        add(75, "pick", peers=n, hood_rank=f["rank"])
    if f["floor_sure"] and extreme(f, peers, "floor", max) and all(p["floor_sure"] for p in peers):
        add(70 + small, "highest", {"floor": f["floor"], "high": "higher" if two else "highest"}, peers=n, floor=f["floor"])
    if extreme(f, peers, "per_sqft", min):
        add(66 + small, "value", {"price": price, "sqft": sqft}, peers=n, all_in=f["all_in"], sqft=f["sqft"])
    if extreme(f, peers, "open_questions", min):
        add(64 + small, "fewest_questions", peers=n, open_questions=f["open_questions"])
    s = soonest(f, peers)
    if s == "now":
        add(62 + small, "soonest_now", peers=n, available="now")
    elif s == "date":
        add(60 + small, "soonest_date", {"date": f["avail"]}, peers=n, available=f["avail"])
    if f["age_days"] is not None and f["age_days"] <= 14 and extreme(f, peers, "age_days", min, everyone=False):
        d = f["age_days"]
        add(58 + small, "newest", {"ago": "today" if d == 0 else "1 day ago" if d == 1 else f"{d} days ago"},
            peers=n, listing_age_days=d)
    # ---- the unit's own facts
    if f["free_months"]:
        m = "month" if f["free_months"] == 1 else "months"
        add(52, "concession", {"free": f"{f['free_months']} {m}"}, free_months=f["free_months"])
    if f["sqft"] and f["sqft"] >= 850:
        add(50, "big", {"sqft": sqft}, sqft=f["sqft"])
    if f["floor"] and f["floor"] >= 10 and f["floor_sure"]:
        add(45, "high_floor", {"floor": f["floor"]}, floor=f["floor"])
    if f["margin"] is not None and f["margin"] >= 400 and f["all_in"]:
        add(42, "margin", {"price": price, "margin": usd(f["margin"])}, all_in=f["all_in"], cap_margin=f["margin"])
    if f["sqft"] and f["sqft"] < 850:
        add(32, "size", {"sqft": sqft}, sqft=f["sqft"])
    if f["floor"] and f["floor"] < 10 and f["floor_sure"]:
        add(30, "floor", {"floor": f["floor"]}, floor=f["floor"])
    if f["beds"] == "1-bedroom":
        add(28, "one_bed", beds=f["beds"])
    elif f["beds"] == "studio":
        add(24, "studio", beds=f["beds"])
    if f["avail"] == "now":
        add(26, "avail_now", available="now")
    elif f["avail"]:
        add(26, "avail_date", {"date": f["avail"]}, available=f["avail"])
    # always on offer, so there is always another angle to turn to
    kind = f["beds"] or "place"
    names = {"kind": kind, "akind": f"a {kind}", "Akind": f"A {kind}"}
    if f["all_in"]:
        add(22, "basic", {**names, "price": price}, beds=f["beds"], all_in=f["all_in"])
    else:
        add(5, "basic_no_price", names, beds=f["beds"])
    add(3, "type", names, beds=f["beds"])
    add(1, "tour")
    return out


def support_phrases(f, covered):
    """Short noun phrases for the second sentence, most useful first: the unit's own facts only, and never one the
    lead already used."""
    out = []

    def add(score, kind, text, **used):
        if kind not in covered:
            out.append((score, kind, text, used))

    if f["sqft"]:
        add(60, "size", f"{whole(f['sqft'])} square feet", sqft=f["sqft"])
    if f["floor"] and f["floor_sure"]:
        add(40, "floor", f"a spot on floor {f['floor']}", floor=f["floor"])
    if f["avail"] and f["avail"] != "now":
        add(38, "date", f"a {f['avail']} move-in date", available=f["avail"])
    elif f["avail"] == "now":
        add(20, "date", "a move-in date of today", available="now")
    return sorted(out, key=lambda x: -x[0])


FRAMES = {"wp": SECOND_WITH_PRICE, "np": SECOND_NO_PRICE, "po": PRICE_ONLY}


class Spread:
    """Keeps count of how often each wording has been used in this run, so none passes its share of the rows."""

    def __init__(self, n_units, n_buildings=None):
        self.used = defaultdict(Counter)                # family -> wording id -> count
        self.line_cap = share_cap(LINE_SHARE, n_units)
        self.catch_cap = share_cap(CATCH_SHARE, n_units)
        self.cond_cap = share_cap(COND_SHARE, n_units)
        self.building_cap = share_cap(LINE_SHARE, n_buildings or n_units)

    def cap(self, family):
        return self.catch_cap if family == "catch" else self.building_cap if family.startswith("b:") else self.line_cap

    def free(self, family, key):
        return self.used[family][key] < self.cap(family)

    def take(self, family, key):
        self.used[family][key] += 1

    def choose(self, family, keys, row_id, salt, avoid=(), must=False):
        """The first key, in the row's own seeded order, that is under its cap and not in `avoid`. With `must`,
        a key is always returned: the least used one outside `avoid` when every cap is reached."""
        order = rotate(list(keys), row_id, salt)
        for k in order:
            if k not in avoid and self.free(family, k):
                return k
        if not must:
            return None
        rest = [k for k in order if k not in avoid] or order
        return min(rest, key=lambda k: self.used[family][k])


def compose_line(f, peers, spread=None, before=(), siblings=()):
    """-> (host_line, pattern_id, used, meta). `before`: the meta of the units ranked above this one in the same
    neighbourhood, nearest last; `siblings`: the meta of the units of the same building already written. Rules kept
    here: the three top-ranked units of a neighbourhood have three different angles, and so do the first three units
    of a building; a unit never repeats the condition or the opening three words of the unit just above it or of the
    sibling just before it; no wording passes its share of the page."""
    spread = spread or Spread(len(peers))
    before, siblings = list(before), list(siblings)
    last = before[-1] if before else {}
    top_angles = {b["angle"] for b in before[:3]} if len(before) < 3 else set()
    if len(siblings) < 3:
        top_angles |= {b["angle"] for b in siblings}
    near = before[-2:] + siblings[-2:]
    recent_angles = {b["angle"] for b in near}
    recent_opens = {b["open3"] for b in near}
    recent_conds = {last.get("cond")} | {b["cond"] for b in siblings[-1:]}
    heard = {b["pattern"] for b in before + siblings}
    heard_frames = {b["frame"] for b in before + siblings}

    scored = []
    for score, cond, vals, used in lead_conditions(f, peers):
        angle = LEADS[cond][0]
        if spread.used["cond"][cond] >= spread.cond_cap:
            score -= 20                                  # this fact has led plenty of lines already
        if angle in recent_angles:
            score -= 15                                  # and the reader has just heard this angle
        scored.append((score, cond, vals, used))
    scored.sort(key=lambda c: (-c[0], c[1]))
    best = scored[0][0]
    pool = [c for c in scored if c[0] >= best - 12]
    order = rotate(pool, f["id"], "lead") + [c for c in scored if c[0] < best - 12]

    def fits(c, strict_angle):
        return c[1] not in recent_conds and (not strict_angle or LEADS[c[1]][0] not in top_angles)

    def wording(c, capped):
        """-> (index, text) of the first sentence of this condition that may be used, else None. A sentence the
        neighbourhood has not heard yet comes first."""
        texts = LEADS[c[1]][1]
        for fresh in (True, False):
            for i in rotate(list(range(len(texts))), f["id"], "wording:" + c[1]):
                pid = f"{c[1]}_{i + 1}"
                if (capped and not spread.free("lead", pid)) or (fresh and pid in heard):
                    continue
                text = cap_first(texts[i].format(**c[2]))
                if open3(text) in recent_opens:
                    continue
                return i, text
        return None

    choice = None
    for strict_angle, capped in ((True, True), (True, False), (False, True), (False, False)):
        for c in order:
            if fits(c, strict_angle):
                w = wording(c, capped)
                if w:
                    choice = (c, w)
                    break
        if choice:
            break
    (score, cond, vals, used), (i, lead) = choice
    angle = LEADS[cond][0]
    pid = f"{cond}_{i + 1}"
    used = {k: v for k, v in used.items() if v is not None}
    price_in_lead = "all_in" in used
    extras = support_phrases(f, COVERS.get(cond, set()) | {angle})[:2]
    for keep in (2, 1, 0):
        chosen = extras[:keep]
        text = join_and([e[2] for e in chosen])
        if price_in_lead or not f["all_in"]:
            family = "np" if chosen else None
        else:
            family = "wp" if chosen else "po"
        if family:
            frames = FRAMES[family]
            fresh = [k for k in range(len(frames)) if f"{family}_{k + 1}" not in heard_frames]
            k = spread.choose("frame:" + family, fresh, f["id"], "second") if fresh else None
            if k is None:
                k = spread.choose("frame:" + family, range(len(frames)), f["id"], "second", must=True)
            second = frames[k].format(price=usd(f["all_in"]) if f["all_in"] else "", extras=text)
            frame_id = f"{family}_{k + 1}"
        else:
            second, frame_id = "", None
        line = (lead + " " + second).strip()
        if words(line) <= MAX_WORDS:
            break
    spread.take("lead", pid)
    spread.take("cond", cond)
    if frame_id:
        spread.take("frame:" + frame_id.split("_")[0], int(frame_id.split("_")[1]) - 1)
    all_used = dict(used)
    for e in chosen:
        all_used.update({k: v for k, v in e[3].items() if v is not None})
    if not price_in_lead and f["all_in"]:
        all_used["all_in"] = f["all_in"]
    return line, pid, all_used, {"cond": cond, "angle": angle, "open3": open3(line), "frame": frame_id, "pattern": pid}


# ------------------------------------------------------------------ the catch (per unit)

UNKNOWN_NAMES = {"building fees": "building fees", "pet rent": "pet rent", "parking fee": "the parking fee", "gas": "the gas bill"}
SWAPPABLE = {"rent:needs_call", "unknown:costs_tight", "lease_term", "floor:unpublished", "floor:inferred"}
# A catch of these kinds states a reason, so the unit must carry that reason: kind -> test on the unit.
CATCH_BASIS = {
    "confirm:dogs conflict": lambda u: dog_open(u) == "conflict",
    "confirm:dogs reason": lambda u: dog_open(u) not in (None, "open", "conflict"),
    "confirm:availability": lambda u: bool(re.search(r"floor.?plan", str(get(u, "confirm", "why") or ""), re.I)),
    "confirm:eligibility": lambda u: "income" in str(get(u, "confirm", "why") or "").lower(),
    "confirm:elevator": lambda u: get(u, "confirm", "what") == "elevator",
    "confirm:live check": lambda u: get(u, "confirm", "what") == "live check",
    "rent:net_effective": net_effective,
    "rent:needs_call": has_special,
    "lease_term": lambda u: bool(num(get(u, "cost_check", "lease_term_months")) or num(get(u, "rent", "lease_months"))),
    "unknown:costs_tight": lambda u: bool(u.get("all_in_unknown")),
    "floor:unpublished": lambda u: num(u.get("floor")) is None,
    "floor:inferred": lambda u: num(u.get("floor")) is not None and u.get("floor_basis") not in ("confirmed", "stated"),
}


def catch_options(u, f):
    """-> [(kind, values to fill, fields used)], most important first: the unit's open question (its asterisk), said
    in the words of the open item itself; a special that clouds the rent; an unusual lease term; unpublished costs
    that could break the cap; a floor the listing does not state. The first is the catch. The later ones are true
    too, and one of them is used only so that the top-ranked units of a neighbourhood, or the units of one building,
    do not all carry the same caution (the cost subhead still flags a clouded rent)."""
    out = []
    c = u.get("confirm") or {}
    if c.get("asterisk") and c.get("what"):
        what = str(c["what"])
        q = str(c.get("question") or "").strip()
        used = {"confirm_what": what, "confirm_why": c.get("why")}
        if f["dog_open"] == "conflict":
            return [("confirm:dogs conflict", {}, used)]
        if f["dog_open"] == "open":
            return [("confirm:dogs open", {}, used)]
        if f["dog_open"]:
            return [("confirm:dogs reason", {"reason": f["dog_open"], "Reason": cap_first(f["dog_open"])}, used)]
        kind = f"confirm:{what}"
        if kind in CATCH_BASIS and kind in CATCHES and CATCH_BASIS[kind](u):
            return [(kind, {}, used)]
        if q:                                            # anything else: the unit's own question, quoted
            return [(kind, {"_library": "confirm:question", "q": q}, {**used, "confirm_question": q})]
        return [("confirm:other", {}, used)]
    rent = u.get("rent") or {}
    if net_effective(u):
        out.append(("rent:net_effective", {}, {"rent_basis_kind": "net_effective", "rent_gross": rent.get("gross")}))
    elif has_special(u):
        out.append(("rent:needs_call", {}, {"rent_needs_call": True}))
    lease = num(get(u, "cost_check", "lease_term_months")) or num(rent.get("lease_months"))
    if lease and int(lease) != 12:
        out.append(("lease_term", {"months": int(lease)}, {"lease_months": int(lease)}))
    names = f["unknown"]
    unknown = [UNKNOWN_NAMES.get(x, x) for x in names]
    tight = f["margin"] is not None and 0 < f["margin"] < 100 * len(unknown)   # each missing line could be about $100
    if unknown and f["all_in"] and tight:
        out.append(("unknown:costs_tight", {"names": join_and(unknown), "Names": cap_first(join_and(unknown)),
                                            "bare": join_and(list(names)), "verb": "is" if len(unknown) == 1 else "are",
                                            "margin": usd(f["margin"])},
                    {"all_in_unknown": names, "cap_margin": f["margin"]}))
    if num(u.get("floor")) is None:
        out.append(("floor:unpublished", {}, {"floor": None}))
    elif not f["floor_sure"] and f["floor"]:
        out.append(("floor:inferred", {"floor": f["floor"]}, {"floor": f["floor"], "floor_basis": u.get("floor_basis")}))
    out.append(weakest(u, f))
    return out


def weakest(u, f):
    """The weaker of the unit's own two scored facts, size and cost, when it can be said from its fields."""
    parts = {k: v for k, v in (get(u, "scores", "parts") or {}).items() if k in ("space", "cost") and num(v) is not None}
    for kind in sorted(parts, key=lambda k: (parts[k], k)):
        if kind == "space" and f["sqft"]:
            return "weak:space", {"sqft": whole(f["sqft"])}, {"sqft": f["sqft"]}
        if kind == "cost" and f["all_in"] and f["margin"] is not None:
            return ("weak:cost", {"price": usd(f["all_in"]), "margin": usd(f["margin"])},
                    {"all_in": f["all_in"], "cap_margin": f["margin"]})
    return "none", {}, {}


def compose_catch(u, f, spread=None, before=(), siblings=()):
    """-> (host_catch, kind, used, wording id). One sentence. Among the three top-ranked units of a neighbourhood,
    and among the units of one building, no catch wording repeats, and where a unit has a second real caution the
    kind does not repeat either."""
    spread = spread or Spread(1)
    before, siblings = list(before), list(siblings)
    options = catch_options(u, f)
    kind, vals, used = options[0]
    near = (before if len(before) < 3 else []) + siblings
    if near and kind in SWAPPABLE:
        taken = {b["catch_kind"] for b in near}
        if kind in taken:
            for other in options[1:]:
                if other[0] in SWAPPABLE and other[0] not in taken:
                    kind, vals, used = other
                    break
    library = vals.get("_library", kind)                 # "_library": the unit's own question, quoted in a frame
    texts = CATCHES.get(library) or CATCHES["confirm:other"]
    vals = {k: v for k, v in vals.items() if k != "_library"}
    ids = [f"{library}_{i + 1}" for i in range(len(texts))]
    recent = {b["catch_id"] for b in before[-2:] + siblings}
    cid = spread.choose("catch", ids, f["id"], "catch", avoid={b["catch_id"] for b in before + siblings}) \
        or spread.choose("catch", ids, f["id"], "catch", avoid=recent, must=True)
    text = cap_first(texts[ids.index(cid)].format(**vals))
    spread.take("catch", cid)
    return text, kind, used, cid


# ------------------------------------------------------------------ section subheads (per unit)
# One short line (at most 14 words, no numbers: the section's headline states them) under the cost, parking, dog and
# building headlines of a place. Each is picked by what the unit's fields say; an unknown gets an "ask" line, never a
# statement; when nothing distinctive can be said, or every wording has reached its share, the subhead is empty.

SUB_MAX_WORDS = 14


def sub_keys(u, f):
    """Which library entry applies in each section, from the unit's own fields. None = say nothing."""
    unknown = f["unknown"]
    if net_effective(u):
        cost = "net_effective"
    elif has_special(u):
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
    if f["dog_open"] == "conflict" or str(dog_field.get("allowed") or "").lower() == "conflicting":
        dog = "conflicting"
    elif f["dog_open"]:                                  # dogs are the open item: nothing here may say they are welcome
        dog = "unsettled"
    elif f["dog_amenity"] and "on site" in f["dog_amenity"]:
        dog = "onsite"
    elif f["dog_park_m"] is not None and f["dog_park_m"] <= 800:
        dog = "near_run"
    elif f["small_only"]:
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


def compose_subs(u, f, spread=None, before=()):
    """-> ({sub_cost, sub_parking, sub_dog, sub_building}, {section: library key}). A wording is not repeated on
    either of the two units ranked just above, and is left out once it has reached its share of the page."""
    spread = spread or Spread(1)
    keys = sub_keys(u, f)
    out = {}
    for section, key in keys.items():
        options = dict(SUBS[section]).get(key) if key else None
        text = ""
        if options:
            recent = {b["subs"].get(section) for b in list(before)[-2:]}
            heard = {b["subs"].get(section) for b in before}
            text = spread.choose("sub_" + section, options, f["id"], "sub_" + section, avoid=heard) \
                or spread.choose("sub_" + section, options, f["id"], "sub_" + section, avoid=recent) or ""
            if text:
                spread.take("sub_" + section, text)
        out["sub_" + section] = text
    return out, keys


# ------------------------------------------------------------------ About the building

def building_facts(group):
    """group: the units shown in one building, best-ranked first -> the building's own facts. Building-level fields
    are read from the best-ranked unit; an open item on any of its units counts for the building."""
    fs = [facts(u) for u in group]
    b = dict(fs[0])
    b["id"] = fs[0]["building"]
    b["n_units"] = len(group)
    b["dog_open"] = next((f["dog_open"] for f in fs if f["dog_open"]), None)
    b["elevator_open"] = any(f["elevator_open"] for f in fs)
    b["unknown"] = sorted({x for f in fs for x in f["unknown"]})
    b["disclosures"] = set().union(*(f["disclosures"] for f in fs))
    b["pet_rent_known"] = all(f["pet_rent_known"] for f in fs)
    return b


def building_conditions(b, peers):
    """-> [(score, condition, values, fields used)] for the sentences of About the building. `peers`: the buildings
    shown in the same neighbourhood (this one included)."""
    n = len(peers)
    small = -25 if n == 2 else 0
    out = []

    def add(score, cond, vals=None, **used):
        out.append((score, cond, {"n": n, "w10": WALK_RADIUS, **(vals or {})}, used))

    onsite = b["dog_amenity"][2:-8] if b["dog_amenity"] and "on site" in b["dog_amenity"] else None   # "dog park"
    fee_tail = f", at {usd(b['park_fee'])} a month" if b["park_fee"] else ", though the fee is not published"
    run = {"dogpark": b["dog_park"], "dogpark_mi": miles(b["dog_park_m"])} if b["dog_park"] and b["dog_park_m"] is not None else None
    park = {"park": b["park"], "park_mins": minutes(b["park_walk"])} if b["park"] and b["park_walk"] is not None else None
    # ---- inside: against the other buildings shown in the neighbourhood
    if only(b, peers, lambda p: p["pool"]):
        add(90 + small, "only_pool", peers=n, pool=True)
    if only(b, peers, lambda p: p["park_kind"] == "garage"):
        add(88 + small, "only_garage", {"gtail": "" if b["park_included"] else fee_tail}, peers=n, parking="garage",
            parking_fee=b["park_fee"])
    if only(b, peers, lambda p: bool(p["doorman"])):
        add(72 + small, "only_doorman", peers=n, doorman=b["doorman"])
    if only(b, peers, lambda p: p["laundry"]):
        add(68 + small, "only_laundry", peers=n, in_unit_laundry=True)
    if onsite and only(b, peers, lambda p: bool(p["dog_amenity"]) and "on site" in p["dog_amenity"]):
        add(67 + small, "only_dogspot", {"dogthing": onsite}, peers=n, dog_amenities=b["dog_amenity"])
    # ---- inside: on its own
    if b["park_included"]:
        add(65, "parking_included", parking="included")
    if onsite:
        add(58, "dog_onsite", {"dogthing": onsite}, dog_amenities=b["dog_amenity"])
    if b["park_kind"] == "garage" and not b["park_included"]:
        if b["park_fee"]:
            add(55, "garage_priced", {"fee": usd(b["park_fee"])}, parking="garage", parking_fee=b["park_fee"])
        else:
            add(55, "garage_unpriced", parking="garage", parking_fee=None)
    if b["pool"]:
        add(50, "pool", pool=True)
    if b["doorman"]:
        add(45, "front_desk" if b["doorman"] == "24-hour" else "doorman", doorman=b["doorman"])
    if b["laundry"]:
        add(40, "laundry", in_unit_laundry=True)
    if b["park_kind"] == "covered" and not b["park_included"]:
        tail = f", at {usd(b['park_fee'])} a month" if b["park_fee"] else ", with the fee not published"
        add(40, "covered", {"ptail": tail}, parking="covered", parking_fee=b["park_fee"])
    if b["no_weight_limit"] and not b["dog_open"]:
        add(34, "dog_no_limit", dog_weight_limit="no limit")
    if b["built"] and b["built"] >= 2015:
        add(32, "newer", {"built": b["built"]}, year_built=b["built"])
    if b["park_kind"] == "lot" and not b["park_included"]:
        tail = f", at {usd(b['park_fee'])} a month" if b["park_fee"] else ", with the fee not published"
        add(30, "lot", {"ptail": tail}, parking="lot", parking_fee=b["park_fee"])
    if b["lounge"]:
        add(28, "lounge", lounge_or_coworking=True)
    if b["gym"]:
        add(20, "gym", gym=True)
    if b["built"] and b["built"] < 2015:
        add(15, "dated", {"built": b["built"]}, year_built=b["built"])
    add(1, "plain")
    # ---- around the door
    if run and b["dog_park_m"] <= 1600 and extreme(b, peers, "dog_park_m", min):
        add(63 + small, "closest_run", run, peers=n, dog_park=b["dog_park"], dog_park_miles=run["dogpark_mi"])
    if park and b["park_walk"] <= 8 and extreme(b, peers, "park_walk", min):
        add(56 + small, "closest_park", park, peers=n, park=b["park"], park_walk_min=park["park_mins"].split()[0])
    if run and b["dog_park_m"] <= 800:
        add(48, "dogpark_near", run, dog_park=b["dog_park"], dog_park_miles=run["dogpark_mi"])
    if b["restaurants"] is not None and b["restaurants"] >= 20:
        add(38, "food", {"rest": whole(b["restaurants"])}, restaurants_800m=int(b["restaurants"]))
    if park and b["park_walk"] <= 5:
        add(35, "park_near", park, park=b["park"], park_walk_min=park["park_mins"].split()[0])
    if b["station"] and b["station_m"] is not None and b["station_m"] <= 800:
        add(26, "station", {"station": b["station"], "station_mi": miles(b["station_m"])},
            train_station=b["station"], train_station_miles=miles(b["station_m"]))
    if b["market"] and b["market_m"] is not None and b["market_m"] <= 500:
        add(24, "errands", {"market": b["market"], "market_mi": miles(b["market_m"])},
            supermarket=b["market"], supermarket_miles=miles(b["market_m"]))
    if park and b["park_walk"] <= 20:
        add(10, "park_walk", park, park=b["park"], park_walk_min=park["park_mins"].split()[0])
    add(1, "around_plain")
    return out


def building_warning(b):
    """The main thing to ask about this building -> key of WARNINGS. Most pressing first."""
    if b["dog_open"]:
        return "dog_unsettled"
    if b["elevator_open"]:
        return "elevator_open"
    if b["park_kind"] is None:
        return "parking_unknown"
    if not b["park_included"] and not b["park_fee"]:
        return "parking_fee"
    if not b["pet_rent_known"] or "pet rent" in b["unknown"]:
        return "pet_rent"
    if "building fees" in b["unknown"]:
        return "fees"
    if b["small_only"]:
        return "weight"
    if "overnight street parking" in b["disclosures"]:
        return "overnight"
    return "tour"


def building_points(b):
    """Every icon point this building's fields support -> [(key, values, fields used)], the steady ones first
    (parking, the dog policy), then the rest."""
    out = []

    def add(key, vals=None, **used):
        out.append((key, {"w10": WALK_RADIUS, **(vals or {})}, used))

    k = b["park_kind"]
    if b["park_included"]:
        add("parking_included", parking="included")
    elif k == "onsite":
        add("onsite_unpriced", parking="onsite")
    elif k:
        add(f"{k}_{'priced' if b['park_fee'] else 'unpriced'}", {"fee": usd(b["park_fee"])} if b["park_fee"] else None,
            parking=k, parking_fee=b["park_fee"])
    if b["dog_amenity"] and "on site" in b["dog_amenity"]:
        add("dog_onsite", {"dogthing": b["dog_amenity"][2:-8]}, dog_amenities=b["dog_amenity"])
    if not b["dog_open"]:                                # an unsettled dog policy is never stated as a yes
        if b["no_weight_limit"]:
            add("dog_no_limit", dog_weight_limit="no limit")
        elif b["weight_limit"]:
            add("dog_limit", {"lb": whole(b["weight_limit"])}, dog_weight_limit_lb=b["weight_limit"])
        elif b["dog_allowed"] and not b["small_only"]:
            add("dog_ok", dog_allowed="yes")
    rest = []

    def more(key, vals=None, **used):
        rest.append((key, {"w10": WALK_RADIUS, **(vals or {})}, used))

    if b["laundry"]:
        more("laundry", in_unit_laundry=True)
    if b["pool"]:
        more("pool", pool=True)
    if b["doorman"]:
        more("front_desk" if b["doorman"] == "24-hour" else "doorman", doorman=b["doorman"])
    if b["gym"]:
        more("gym", gym=True)
    if b["lounge"]:
        more("lounge", lounge_or_coworking=True)
    if b["park"] and b["park_walk"] is not None and b["park_walk"] <= 15:
        more("park", {"park": b["park"], "park_mins": minutes(b["park_walk"])}, park=b["park"],
             park_walk_min=minutes(b["park_walk"]).split()[0])
    if b["dog_park"] and b["dog_park_m"] is not None and b["dog_park_m"] <= 1600:
        more("dogrun", {"dogpark": b["dog_park"], "dogpark_mi": miles(b["dog_park_m"])}, dog_park=b["dog_park"],
             dog_park_miles=miles(b["dog_park_m"]))
    if b["restaurants"] is not None and b["restaurants"] >= 4:
        more("food", {"rest": whole(b["restaurants"])}, restaurants_800m=int(b["restaurants"]))
    if b["station"] and b["station_m"] is not None and b["station_m"] <= 1200:
        more("train", {"station": b["station"], "station_mi": miles(b["station_m"])}, train_station=b["station"],
             train_station_miles=miles(b["station_m"]))
    if b["built"]:
        more("built", {"built": b["built"]}, year_built=b["built"])
    last = []
    if b["elevator_sure"] and not b["elevator_open"]:
        last.append(("elevator", {}, {"elevator": "yes"}))
    last.append(("units", {"n": b["n_units"], "apts": "apartment" if b["n_units"] == 1 else "apartments"},
                 {"units_shown": b["n_units"]}))
    return out, rest, last


def compose_building(b, peers, spread=None, before=()):
    """-> (about_building, about_points, facts used, meta). `before`: the meta of the buildings already written in
    the same neighbourhood. Two sentences, at most ABOUT_MAX_WORDS: the building itself, then what is around its
    door; then 3 to 5 icon points, one of them the warning, none repeating a fact the sentences state."""
    spread = spread or Spread(len(peers), len(peers))
    before = list(before)
    conds = building_conditions(b, peers)
    last = before[-1] if before else {}
    heard = {x for m in before for x in m["patterns"]}
    recent_opens = {m["open3"] for m in before[-2:]}
    chosen, used_all, budget = [], {}, ABOUT_MAX_WORDS
    for group in ("inside", "around"):
        scored = []
        for score, cond, vals, used in conds:
            angle, grp, texts = BUILDING[cond]
            if grp != group:
                continue
            if spread.used["b:cond"][cond] >= share_cap(COND_SHARE, spread.building_cap * 25):
                score -= 20
            if cond in last.get("conds", ()):
                score -= 15
            scored.append((score, cond, vals, used))
        scored.sort(key=lambda c: (-c[0], c[1]))
        best = scored[0][0]
        pool = [c for c in scored if c[0] >= best - 12]
        order = rotate(pool, b["id"], "b:" + group) + [c for c in scored if c[0] < best - 12]
        pick = None
        for capped, fresh in ((True, True), (True, False), (False, False)):
            for c in order:
                texts = BUILDING[c[1]][2]
                for i in rotate(list(range(len(texts))), b["id"], "b:wording:" + c[1]):
                    pid = f"{c[1]}_{i + 1}"
                    if (capped and not spread.free("b:sentence", pid)) or (fresh and pid in heard):
                        continue
                    text = cap_first(texts[i].format(**c[2]))
                    if words(text) > budget - (8 if group == "inside" else 0):
                        continue
                    if group == "inside" and open3(text) in recent_opens:
                        continue
                    pick = (c, pid, text)
                    break
                if pick:
                    break
            if pick:
                break
        (score, cond, vals, used), pid, text = pick
        spread.take("b:sentence", pid)
        spread.take("b:cond", cond)
        budget -= words(text)
        chosen.append((cond, pid, text))
        used_all.update({k: v for k, v in used.items() if v is not None})
    about = " ".join(t for _, _, t in chosen)

    # the icon points: the warning, then facts the two sentences have not already stated
    said = {ANGLE_TOPIC.get(BUILDING[c][0]) for c, _, _ in chosen}
    said |= {"dogspot" for c, _, _ in chosen if c in ("dog_onsite", "only_dogspot")}
    said |= {"dogrun" for c, _, _ in chosen if c in ("dogpark_near", "closest_run")}
    said |= {"dog" for c, _, _ in chosen if c == "dog_no_limit"}
    wkey = building_warning(b)
    wtopic = WARNINGS[wkey][0]
    steady, rest, fallback = building_points(b)
    blocked = said | {wtopic}
    picks = [p for p in steady if POINTS[p[0]][1] not in blocked]
    rest = [p for p in rotate(rest, b["id"], "b:points") if POINTS[p[0]][1] not in blocked] if rest else []
    picks += rest[:max(0, POINTS_COUNT[1] - 1 - len(picks))]
    for p in fallback:
        if len(picks) < POINTS_COUNT[0] - 1:
            picks.append(p)
    picks = picks[:POINTS_COUNT[1] - 1]
    points, keys = [], []
    for key, vals, used in picks:
        icon, topic, texts = POINTS[key]
        text = spread.choose("b:point", texts, b["id"], "b:point:" + key, must=True)
        spread.take("b:point", text)
        points.append({"icon": icon, "text": cap_first(text.format(**vals))})
        keys.append(key)
        used_all.update({k: v for k, v in used.items() if v is not None})
    wtext = spread.choose("b:point", WARNINGS[wkey][1], b["id"], "b:warning", must=True)
    spread.take("b:point", wtext)
    points.append({"icon": "warning", "text": wtext})
    meta = {"conds": [c for c, _, _ in chosen], "patterns": [p for _, p, _ in chosen], "open3": open3(about)}
    facts_used = {"sentences": meta["patterns"], "points": keys, "warning": wkey, "values": used_all,
                  "units_shown": b["n_units"]}
    return about, points, facts_used, meta


# ------------------------------------------------------------------ the run

FIELDS = ["listing_id", "host_line", "host_catch", "sub_cost", "sub_parking", "sub_dog", "sub_building", "facts_used_json"]
BUILDING_FIELDS = ["building_id", "about_building", "about_points_json", "facts_used_json"]
SUB_COLS = ["sub_cost", "sub_parking", "sub_dog", "sub_building"]


def rank_key(u):
    return (num(get(u, "scores", "hood_rank")) or 1e9, str(u["id"]))


def grouped(units):
    """-> {hood_id: {building_id: [units, best-ranked first]}}"""
    out = defaultdict(lambda: defaultdict(list))
    for u in sorted(units, key=rank_key):
        out[u.get("hood_id")][u.get("building_id") or u["id"]].append(u)
    return out


def build(units):
    """units: the `units` list of site/data.json. -> rows with the columns in FIELDS. Neighbourhoods are taken in
    name order and units in rank order, so the same data always gives the same text. A unit is compared with the
    other units shown in its own building."""
    tree = grouped(units)
    spread = Spread(len(units))
    rows = []
    for hood in sorted(tree, key=str):
        peers = {bid: [facts(u) for u in group] for bid, group in tree[hood].items()}
        before, siblings = [], defaultdict(list)
        for u in sorted((u for g in tree[hood].values() for u in g), key=rank_key):
            bid = u.get("building_id") or u["id"]
            f = next(p for p in peers[bid] if p["id"] == u["id"])
            line, pid, used, meta = compose_line(f, peers[bid], spread, before, siblings[bid])
            catch, ckind, cused, cid = compose_catch(u, f, spread, before, siblings[bid])
            subs, sub_kinds = compose_subs(u, f, spread, before)
            entry = {**meta, "catch_kind": ckind, "catch_id": cid, "subs": {s[4:]: t for s, t in subs.items()}}
            before.append(entry)
            siblings[bid].append(entry)
            rows.append({"listing_id": u["id"], "host_line": line, "host_catch": catch, **subs,
                         "facts_used_json": json.dumps({"hood_id": hood, "building_id": bid, "pattern": pid,
                                                        "angle": meta["angle"], "frame": meta["frame"], "line": used,
                                                        "catch_kind": ckind, "catch_id": cid, "catch": cused,
                                                        "subs": sub_kinds}, ensure_ascii=False, sort_keys=True)})
    return rows


def build_buildings(units):
    """-> rows with the columns in BUILDING_FIELDS, one per building_id, in neighbourhood order then best rank."""
    tree = grouped(units)
    n_buildings = sum(len(b) for b in tree.values())
    spread = Spread(len(units), n_buildings)
    rows = []
    for hood in sorted(tree, key=str):
        bfacts = [building_facts(group) for group in tree[hood].values()]     # insertion order = best rank first
        before = []
        for b in bfacts:
            about, points, used, meta = compose_building(b, bfacts, spread, before)
            before.append(meta)
            rows.append({"building_id": b["id"], "about_building": about,
                         "about_points_json": json.dumps(points, ensure_ascii=False),
                         "facts_used_json": json.dumps({"hood_id": hood, **used}, ensure_ascii=False, sort_keys=True)})
    return rows


def distribution(rows):
    """-> {family: {with_text, distinct, top, top_count, top_share}} for the unit rows."""
    n = len(rows)
    meta = [json.loads(r["facts_used_json"]) for r in rows]
    out = {}
    for name, values in (("lead wording", [m["pattern"] for m in meta]),
                         ("lead condition", [m["pattern"].rsplit("_", 1)[0] for m in meta]),
                         ("second-sentence frame", [m["frame"] for m in meta if m["frame"]]),
                         ("catch wording", [m["catch_id"] for m in meta]),
                         ("catch kind", [m["catch_kind"] for m in meta]),
                         *((c, [r[c] for r in rows if r[c]]) for c in SUB_COLS)):
        top, count = Counter(values).most_common(1)[0] if values else ("", 0)
        out[name] = {"with_text": len(values), "distinct": len(set(values)), "top": top, "top_count": count,
                     "top_share": count / n if n else 0.0}
    return out


def building_distribution(rows):
    """The same for the building rows: sentences, and icon points with their numbers masked."""
    n = len(rows)
    meta = [json.loads(r["facts_used_json"]) for r in rows]
    out = {}
    for name, values in (("building sentence", [p for m in meta for p in m["sentences"]]),
                         ("building point", [k for m in meta for k in m["points"]]),
                         ("building warning", [m["warning"] for m in meta]),
                         ("warning wording", [p["text"] for r in rows for p in json.loads(r["about_points_json"])
                                              if p["icon"] == "warning"])):
        top, count = Counter(values).most_common(1)[0] if values else ("", 0)
        out[name] = {"with_text": len(values), "distinct": len(set(values)), "top": top, "top_count": count,
                     "top_share": count / n if n else 0.0}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(DATA), help="page data to read (default site/data.json)")
    ap.add_argument("--out", default=str(OUT), help="unit CSV to write (default data/reference/realtor_lines.csv)")
    ap.add_argument("--out-buildings", default=str(OUT_BUILDINGS),
                    help="building CSV to write (default data/reference/building_about.csv)")
    a = ap.parse_args()
    units = json.loads(Path(a.data).read_text(encoding="utf-8"))["units"]
    rows, brows = build(units), build_buildings(units)
    for path, fields, data in ((a.out, FIELDS, rows), (a.out_buildings, BUILDING_FIELDS, brows)):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(data)
    print(f"{len(rows)} units written to {a.out}")
    print(f"{len(brows)} buildings written to {a.out_buildings}")
    print(f"limits: a line wording, frame, subhead or building sentence on at most {LINE_SHARE:.0%} of rows, "
          f"a catch wording on at most {CATCH_SHARE:.0%}")
    for d in (distribution(rows), building_distribution(brows)):
        for name, x in d.items():
            print(f"  {name:22} {x['with_text']:4} uses, {x['distinct']:3} distinct, commonest {x['top_count']:3} "
                  f"({x['top_share']:.1%}): {str(x['top'])[:60]}")
    kinds = Counter(json.loads(r["facts_used_json"])["catch_kind"] for r in rows)
    print(f"catch kinds: {dict(kinds.most_common())}")


if __name__ == "__main__":
    main()
