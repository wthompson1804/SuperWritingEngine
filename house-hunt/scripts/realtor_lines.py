#!/usr/bin/env python3
"""Compose the host's line and the honest catch for every unit shown on the page.

The unit list changes with every repair run, so nothing here is hand-written per unit. For each unit in
site/data.json this script reads the unit's own fields, works out which facts are most distinctive (against the other
units shown in the same neighbourhood first, then on their own), and fills one of the hand-written sentences below.

  host_line   1 or 2 sentences, at most 45 words: the most distinctive fact, then the price and one or two more facts
  host_catch  1 sentence: the open question (the asterisk) if the unit has one, else what the listing does not
              publish, else the weakest fact
  sub_cost, sub_parking, sub_dog, sub_building   one optional short line (at most 14 words, no numbers) for under each
              section headline of the place; empty when the fields give nothing distinctive to say
  facts_used_json   the wording chosen and every value that was printed, so each word can be traced to a field

How the wording is spread (2026-11-16, second pass). The page shows a neighbourhood's top three places together, and
the same sentence on card after card kills the walk-through. So:
  * every condition (a fact that can lead a line, a kind of catch, a subhead case) has at least 8 different sentences,
    written from different angles, never one template with synonyms swapped;
  * a lead leads with what sets THIS place apart from the others shown in its neighbourhood where it can (cheapest,
    most room, most room per dollar, highest floor, soonest move-in, newest listing, the only pool / garage / doorman /
    in-unit laundry / dog spot, nearest dog run or park, fewest open questions, the host's own first choice);
  * no line wording is used for more than LINE_SHARE of the units, no catch wording for more than CATCH_SHARE, no
    subhead wording for more than LINE_SHARE (the run prints the distribution; the tests hold the thresholds);
  * the three top-ranked places of a neighbourhood have three different lead angles and three different catch
    wordings, and two neighbouring units never open with the same three words.

Rules the code keeps (scripts/test_realtor_lines.py checks them):
  * deterministic: choices are seeded by listing_id and made in a fixed order (neighbourhood, then rank), so a rerun
    on the same data gives the same text;
  * an unknown is never stated as a fact: no parking type means parking is not mentioned in the line and the catch
    says it is not published; a garage with no price is "fee not published", never "free";
  * a superlative ("the most room here") is claimed only when every other unit shown there publishes the figure;
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
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data.json"
OUT = ROOT / "data" / "reference" / "realtor_lines.csv"
MAX_WORDS = 45
WALK_RADIUS = "10-minute walk"            # the page's wording for the 800 m radius
LINE_SHARE = 0.04                         # no lead wording, second-sentence frame or subhead on more than 4% of units
CATCH_SHARE = 0.05                        # no catch wording on more than 5% of units
COND_SHARE = 0.08                         # a lead condition used this often is set back, so other angles get a turn
MIN_WORDINGS = 8                          # sentences per condition
UNPRICED = re.compile(r"not published|does not publish|unpublished", re.I)   # every unpriced-garage lead says so


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


def open3(text: str) -> str:
    """The first three words, lower case: two neighbouring units never share them."""
    return " ".join(re.findall(r"[A-Za-z0-9$'-]+", text.lower())[:3])


def rotate(options, listing_id, salt):
    """The options in an order seeded by the listing id (stable across reruns)."""
    k = seed(listing_id, salt) % len(options)
    return options[k:] + options[:k]


def share_cap(share, n):
    return max(3, int(share * n))


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
    return {
        "id": u["id"], "hood": u.get("hood_id"),
        "beds": "studio" if u.get("beds") == 0 else "1-bedroom" if u.get("beds") == 1 else None,
        "all_in": all_in, "sqft": sqft,
        "per_sqft": all_in / sqft if all_in and sqft else None,
        "floor": int(floor) if floor and floor >= 2 else None,
        "floor_sure": u.get("floor_basis") in ("confirmed", "stated"),
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
        "no_weight_limit": str(get(u, "dog", "weight_limit_lb") or "").lower() == "no limit",
    }


def only(f, peers, test):
    return len(peers) >= 2 and test(f) and not any(test(p) for p in peers if p["id"] != f["id"])


def extreme(f, peers, key, best=max, everyone=True):
    """True when this unit alone holds the best value of `key` among the units shown in its neighbourhood. With
    `everyone` (the default) every one of them must publish the value, so "the most room here" is simply true; without
    it, at least 2 must, and the sentence has to say it speaks only of the listings that give the figure."""
    vals = [p[key] for p in peers if p[key] is not None]
    if f[key] is None or len(vals) < 2 or (everyone and len(vals) < len(peers)):
        return False
    top = best(vals)
    return f[key] == top and vals.count(top) == 1


def soonest(f, peers):
    """'now' when it is the only unit available now; 'date' when its date is alone the earliest and nothing is now.
    Every unit shown there must publish a date."""
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


# ------------------------------------------------------------------ the lead library
# LEADS[condition] = (angle, [sentences]). The angle is what the line is about; the three top-ranked places of a
# neighbourhood never share one. Each sentence is hand-written; {n} is the number of units shown in the neighbourhood
# and every other {field} is filled from the unit's own fields. A condition is offered only when its fact is true.

LEADS = {
    # ---- against the other places shown in the same neighbourhood
    "only_pool": ("pool", [
        "The only pool among the {n} places here is this building's.",
        "Of the {n} places in this neighborhood, this is the one with a pool.",
        "If a pool matters to you, this is the single building of the {n} here that lists one.",
        "Summer is easier in this building, because no other place here lists a pool.",
        "A pool, which no other building on this neighborhood's list offers you.",
        "I went through all {n} places here looking for a pool, and this is where the search ended.",
        "Every other listing here sends you elsewhere to swim, and this building has its own pool.",
        "This is the swimmer's pick: the lone pool among the {n} places we found here.",
    ]),
    "only_garage": ("parking", [
        "No other place of the {n} here lists a garage, and this one does{gtail}.",
        "Garage parking, the only one of the {n} places here to list it{gtail}.",
        "Your car gets a garage here, alone among the places in this neighborhood{gtail}.",
        "Of the {n} places here, this is the single listing that puts the car indoors{gtail}.",
        "For the car, this is the standout: the lone garage on this neighborhood's list{gtail}.",
        "No other listing here mentions a garage, so this is where the car sleeps indoors{gtail}.",
        "If the car is the priority, start with this building, the only garage among the {n}{gtail}.",
        "A garage is hard to find in this neighborhood, and this is the only listing of {n} with one{gtail}.",
    ]),
    "cheapest": ("price", [
        "This is the {low} all-in of the {n} places here, about {price} a month.",
        "Start with the number: about {price} a month all in, the {low} of the {n} here.",
        "Nothing else in this neighborhood comes in under this place, at about {price} a month all in.",
        "The budget pick: about {price} a month all in, below every other place on this neighborhood's list.",
        "About {price} a month all in, and no other place we found here beats that.",
        "If the monthly number decides it, this place wins the neighborhood at about {price} all in.",
        "Your wallet's favorite of the {n} here, at about {price} a month all in.",
        "Of the {n} places here, this asks the least of you each month, about {price} all in.",
    ]),
    "biggest": ("size", [
        "The {big} of the {n} places here, at {sqft} square feet.",
        "{sqft} square feet, more than any other place we found in this neighborhood.",
        "For space, nothing here tops this place: {sqft} square feet.",
        "The desk, the sofa and the dog bed all fit in {sqft} square feet, the most on this neighborhood's list.",
        "You work from home, so notice this: {sqft} square feet, the most room of the {n} here.",
        "No other place here gives you this much floor, {sqft} square feet of it.",
        "Of the {n} places here, this has the most room to spread out, {sqft} square feet.",
        "Room wins here: at {sqft} square feet, this is the largest place on the neighborhood's list.",
    ]),
    "value": ("value", [
        "The most room for the money here: {sqft} square feet for about {price} a month all in.",
        "Dollar for square foot, this is the best deal of the {n} places here, {sqft} square feet at about {price} all in.",
        "About {price} a month all in buys {sqft} square feet, the strongest trade on this neighborhood's list.",
        "If you measure by what each dollar buys, this wins the neighborhood: {sqft} square feet, about {price} all in.",
        "No other place here stretches the budget as far, {sqft} square feet for about {price} a month all in.",
        "The value pick of the {n} here, {sqft} square feet at about {price} a month all in.",
        "You get more floor per dollar here than anywhere else in this neighborhood: {sqft} square feet, about {price} all in.",
        "Run the math on all {n} places here and this comes out ahead, {sqft} square feet for about {price} all in.",
    ]),
    "pick": ("pick", [                               # the top-ranked place of 3 or more, said as the host's own choice
        "If I could only show you one place here, it's this one.",
        "This is the door I would open first in this neighborhood.",
        "Of the {n} places here, this is where I would start the tour.",
        "My pick of the neighborhood, and I would not make you wait to see it.",
        "Clear your calendar for this one before any other place here.",
        "When people ask me where to begin in this neighborhood, this is the address I give.",
        "Put this at the top of your list for this neighborhood.",
        "I would fight for this place on your behalf before any other here.",
        "See this one first, and judge the other places here against it.",
        "Of everything we found in this neighborhood, this is the place I keep coming back to.",
    ]),
    "only_doorman": ("doorman", [
        "The only building of the {n} here with a doorman.",
        "Someone staffs the front door here, and no other listing in this neighborhood says the same.",
        "Of the {n} places here, this is the lone building with a doorman.",
        "A doorman, which none of the other buildings we found here lists.",
        "Packages, late nights, a familiar face: this is the single doorman building of the {n} here.",
        "If you want a staffed front door in this neighborhood, this building is the choice.",
        "No other building here lists a person at the door, and this one does.",
        "This is the neighborhood's doorman building, the only one among the {n} places we found.",
    ]),
    "highest": ("floor", [
        "Floor {floor}, the {high} of the places we found here.",
        "You are up on floor {floor}, above every other place on this neighborhood's list.",
        "Nothing else here sits as high as this place, on floor {floor}.",
        "The high-floor pick: floor {floor}, above any other place we found in this neighborhood.",
        "Of the {n} places here, this is the one farthest above the street, on floor {floor}.",
        "Press the button for floor {floor}, the top of this neighborhood's list.",
        "Floor {floor} puts you above all the other places here.",
        "If you like height, this is the place: floor {floor}, the {high} here.",
    ]),
    "only_laundry": ("laundry", [
        "The only place of the {n} here with a washer and dryer in the apartment.",
        "Laundry happens inside your own apartment here, and no other listing in this neighborhood says the same.",
        "Of the {n} places here, this is the lone listing with a washer and dryer in the unit.",
        "No other place here lists machines in the unit, and this one does, so skip the laundry room.",
        "A washer and dryer of your own, which the other places in this neighborhood do not list.",
        "If hauling a laundry bag is a dealbreaker, this is your place here, the only in-unit set of the {n}.",
        "The machines are in the apartment, a claim no other listing in this neighborhood makes.",
        "This is the neighborhood's in-unit laundry pick, alone among the {n} places we found.",
    ]),
    "only_dogspot": ("dog", [
        "The only building of the {n} here with its own {dogthing}.",
        "A {dogthing} on the property, which no other place in this neighborhood lists.",
        "Of the {n} places here, this is the lone building where the dog has a spot without leaving the grounds.",
        "No other listing here mentions a {dogthing} of its own, and this one does.",
        "For the dog, this is the neighborhood's standout: the single building with a {dogthing} on site.",
        "The early walk can be an elevator ride here, thanks to the only on-site {dogthing} among the {n}.",
        "If the dog gets a vote, this wins: it is the single building here with a {dogthing}.",
        "This building keeps a {dogthing} for residents, alone among the places we found here.",
    ]),
    "fewest_questions": ("clean", [
        "The fewest loose ends of the {n} places here, so the tour can be about the apartment.",
        "This listing leaves less for you to chase than any other in this neighborhood.",
        "Of the {n} places here, this has the shortest list of things to ask.",
        "The most complete listing in the neighborhood, which makes your homework lighter.",
        "You would walk in here with fewer open questions than at any other place on this list.",
        "On paper this is the tidiest of the {n} here, with the least left to confirm.",
        "Less guesswork here than anywhere else in this neighborhood.",
        "If you hate surprises, start here: no other place on this list leaves so little unanswered.",
    ]),
    "closest_run": ("dog", [
        "{dogpark} is {dogpark_mi} miles away, closer than a dog run is to any other place here.",
        "The shortest trip to a dog run on this neighborhood's list: {dogpark_mi} miles to {dogpark}.",
        "Of the {n} places here, this puts the dog nearest a proper run, {dogpark_mi} miles from {dogpark}.",
        "Your dog would vote for this one, with {dogpark} {dogpark_mi} miles off, the nearest run to any place here.",
        "No other place here is nearer a dog run, with {dogpark} {dogpark_mi} miles from the door.",
        "For off-leash time this leads the neighborhood, {dogpark_mi} miles from {dogpark}.",
        "It is {dogpark_mi} miles to {dogpark}, and every other place here is farther from a dog run.",
        "The dog's pick of the {n}: {dogpark} sits {dogpark_mi} miles away, the closest run on this list.",
    ]),
    "soonest_now": ("date", [
        "Available now, which no other place in this neighborhood is.",
        "You could move in right away here, and every other place on this list makes you wait.",
        "The keys are ready now, ahead of all the other places here.",
        "Of the {n} places here, this is the only one open today.",
        "No waiting on this one: it is the lone place here available now.",
        "If you want to move fast, this is the place, the only one here ready now.",
        "Ready when you are, and that is true of no other place in this neighborhood.",
        "This is the move-in-now option, alone among the {n} places here.",
    ]),
    "soonest_date": ("date", [
        "Ready {date}, the earliest date in this neighborhood.",
        "This opens {date}, before any other place here.",
        "The first move-in date on this neighborhood's list: {date}.",
        "Of the {n} places here, this gets you in soonest, on {date}.",
        "Circle {date}, because nothing else here is ready earlier.",
        "If the calendar matters, this one leads the neighborhood with a {date} move-in.",
        "You would have keys on {date}, ahead of every other place here.",
        "Nothing here beats a {date} start, and this is the place that offers it.",
    ]),
    "newest": ("new", [                              # speaks only of the listings that show a posting date
        "Fresh on the market: listed {ago}, the newest listing we can date in this neighborhood.",
        "This went up {ago}, the most recent posting date we have here.",
        "Listed {ago}, so you are seeing it early, ahead of every other dated listing here.",
        "New to the list: posted {ago}, the latest dated listing in this neighborhood.",
        "Of the listings here that show a date, this is the newest, posted {ago}.",
        "It was posted {ago}, later than any other dated listing we found here.",
        "The newcomer of the neighborhood, listed {ago}.",
        "Posted {ago}, which makes this the freshest dated listing here.",
    ]),
    "closest_park": ("green", [
        "{park} is about {park_mins} on foot, the shortest walk to green from any place here.",
        "The quickest route to a park on this neighborhood's list: about {park_mins} to {park}.",
        "Of the {n} places here, this is nearest a park, about {park_mins} from {park}.",
        "Morning walks start sooner here than anywhere else in the neighborhood, about {park_mins} from {park}.",
        "No other place here is closer to green, with {park} about {park_mins} away.",
        "About {park_mins} to {park}, and every other place here has a longer walk to a park.",
        "For the daily loop this leads the neighborhood, about {park_mins} on foot from {park}.",
        "The leash-and-coffee pick of the {n}, about {park_mins} from {park}.",
    ]),
    # ---- facts that stand on their own
    "parking_included": ("parking", [
        "A parking spot comes with the lease, so the car adds nothing to the bill.",
        "Parking is included in the lease here, which is one less thing to negotiate.",
        "The rent already takes care of the car: the listing includes a spot.",
        "No separate parking bill here, because a spot is part of the lease.",
        "Your car has a place and it is already paid for in the rent.",
        "They include a parking spot, and in this search that is worth real money.",
        "The line you will not find on the bill here is parking, since a spot is included.",
        "The spot is included, so the matter of where the car sleeps is settled on day one.",
    ]),
    "dog_onsite": ("dog", [
        "The building has a {dogthing} of its own, so the early walk can be an elevator ride.",
        "For the dog: a {dogthing} on site.",
        "A {dogthing} on the property means the last walk of the night is a short one.",
        "Rainy mornings are easier here, with a {dogthing} right on the grounds.",
        "Your dog gets a {dogthing} without either of you crossing a street.",
        "There is a {dogthing} on site, and a new puppy will use it several times a day.",
        "Leash, elevator, {dogthing}: the building keeps one on the property.",
        "The property has its own {dogthing}, which makes weekday exercise simple.",
    ]),
    "garage_priced": ("parking", [
        "The car gets a garage here, at {fee} a month.",
        "Pull in, park in the garage, go upstairs, for {fee} a month.",
        "Garage parking is {fee} a month, and the price is right there on the page.",
        "For {fee} a month your car sleeps indoors.",
        "You love that car, and here it gets a garage for {fee} a month.",
        "A garage spot runs {fee} a month, so you can budget for it today.",
        "No circling the block: the garage is {fee} a month.",
        "They publish the garage price, {fee} a month, which makes the car easy to plan for.",
    ]),
    "garage_unpriced": ("parking", [
        "The car gets a garage here, though the fee is not published.",
        "Pull in, park in the garage, go upstairs, though the listing does not publish the fee.",
        "There is a garage for the car, and the fee is not published, so ask.",
        "Your car would sleep indoors here, at a price the listing does not publish.",
        "A garage comes with the building, and what it costs is not published yet.",
        "You love that car, and here it gets a garage, with the monthly fee not published.",
        "The listing promises a garage and does not publish the fee, so get the number in writing.",
        "Indoor parking is on offer, though the fee is not published anywhere we could read.",
        "A garage is the good news, and the unpublished fee is the thing to ask about.",
        "The building has a garage, with the fee not published on the listing.",
    ]),
    "concession": ("offer", [
        "The listing advertises {free} free, so read the lease math carefully.",
        "There is an offer of {free} free on this one, and the real monthly rent is the thing to pin down.",
        "The headline here is {free} free, and the fine print is where you should look.",
        "They are dangling {free} free, which is nice, as long as you know the rent after it ends.",
        "A special of {free} free is on the table, so ask what the rent is once it runs out.",
        "The deal on the page is {free} free, and deals like that deserve a second read.",
        "You would get {free} free under the current offer, so compare this place on its full rent.",
        "This comes with {free} free, and I would rather you judge it by the regular rent.",
    ]),
    "big": ("size", [
        "{sqft} square feet, so the desk gets its own corner.",
        "Room to work from home: {sqft} square feet.",
        "At {sqft} square feet, the laptop never has to share the dinner table.",
        "You get {sqft} square feet, which is real room for a desk and a dog.",
        "The floor plan runs {sqft} square feet, generous for a first place.",
        "There is space to pace on a work call here, {sqft} square feet of it.",
        "With {sqft} square feet, the dog can have the zoomies without rearranging your office.",
        "This is a roomy one at {sqft} square feet.",
    ]),
    "pool": ("pool", [
        "There is a pool, and yes, you would use it.",
        "A pool comes with the building.",
        "Summer weekends are handled: the building has a pool.",
        "The building has a pool, which is a nice thing to come home to in July.",
        "You get a pool here, and your friends will find reasons to visit.",
        "A pool is part of the package in this building.",
        "After a day at the desk, the pool is right there on the property.",
        "Pack a swimsuit, because this building has a pool.",
    ]),
    "dogpark_near": ("dog", [
        "{dogpark} is {dogpark_mi} miles away, close enough for the first walk of the day.",
        "The dog's morning is easy: {dogpark}, {dogpark_mi} miles from the door.",
        "A proper run for the dog is {dogpark_mi} miles off at {dogpark}.",
        "You can reach {dogpark} on foot, {dogpark_mi} miles away, before your first meeting.",
        "Off-leash time is close here, with {dogpark} {dogpark_mi} miles from the lobby.",
        "For a puppy with energy to burn, {dogpark} is {dogpark_mi} miles away.",
        "It is {dogpark_mi} miles to {dogpark}, a walk the dog will learn fast.",
        "Lunch-break fetch is realistic here: {dogpark} sits {dogpark_mi} miles away.",
    ]),
    "front_desk": ("doorman", [
        "Someone is at the front desk around the clock.",
        "The front desk is staffed 24 hours, so a late arrival is never a lonely one.",
        "There is a person at the desk day and night.",
        "A 24-hour front desk means your packages and your late nights are both looked after.",
        "Whatever time you come home, somebody is at the desk.",
        "The lobby is staffed at every hour.",
        "Deliveries land with a person here, since the desk never closes.",
        "A staffed desk, all day and all night, comes with this building.",
    ]),
    "doorman": ("doorman", [
        "There is a doorman at the front door.",
        "A doorman greets you here, which helps with packages and late arrivals.",
        "The building has a doorman, a small thing that changes how coming home feels.",
        "Someone holds the door in this building.",
        "You get a doorman, so there is a familiar face at the end of the day.",
        "This is a doorman building.",
        "A doorman is on the payroll here, good news for anyone expecting deliveries.",
        "The front door comes with a doorman.",
    ]),
    "high_floor": ("floor", [
        "Floor {floor}, well above the street.",
        "You would be up on floor {floor}.",
        "The elevator takes you to floor {floor}, a long way from the sidewalk.",
        "This one sits on floor {floor}, high enough to leave the street behind.",
        "Up on floor {floor}, the block stays well below you.",
        "Floor {floor} is the address, so bring your head for heights.",
        "It is a floor {floor} apartment, well clear of the ground level you asked to avoid.",
        "High up, on floor {floor}.",
    ]),
    "margin": ("price", [
        "About {price} a month all in, which leaves about {margin} under your cap.",
        "This comes in about {margin} below your ceiling, at about {price} a month all in.",
        "There is breathing room in the budget here: about {price} all in, about {margin} to spare.",
        "At about {price} a month all in, you keep about {margin} of your budget.",
        "The bill is about {price} a month all in, a comfortable {margin} or so under your limit.",
        "You would have about {margin} left each month, with the all-in at about {price}.",
        "Easy on the budget: about {price} all in, roughly {margin} under what you set.",
        "About {margin} of headroom under your cap, on an all-in of about {price} a month.",
    ]),
    "laundry": ("laundry", [
        "Washer and dryer inside the apartment, so no laundry-room trips.",
        "The washer and dryer are in the unit.",
        "Laundry happens at home here, on your schedule.",
        "You get your own washer and dryer, which you will appreciate every single week.",
        "No quarters, no laundry room: the machines are in the apartment.",
        "There is a washer and dryer in the unit, and a dog owner does a lot of laundry.",
        "Your own machines, inside your own door.",
        "In-unit laundry is on the list here.",
    ]),
    "covered": ("parking", [
        "Covered parking for the car{ptail}.",
        "The car gets a roof over it here{ptail}.",
        "Parking is covered at this building{ptail}.",
        "No scraping ice off the windshield, since the parking is covered{ptail}.",
        "Your car parks under cover{ptail}.",
        "They offer covered parking{ptail}.",
        "A covered spot is available for the car{ptail}.",
        "There is covered parking on the property{ptail}.",
    ]),
    "food": ("food", [
        "About {rest} restaurants sit within a {w10}.",
        "Dinner is a walk: about {rest} restaurants within a {w10} of the door.",
        "You could eat out for weeks without repeating, with about {rest} restaurants a {w10} or less away.",
        "Step outside and there are about {rest} restaurants within a {w10}.",
        "For nights you do not cook, about {rest} restaurants are a {w10} or closer.",
        "The block feeds you well, with about {rest} restaurants inside a {w10}.",
        "Saturday dinner needs no car here: about {rest} restaurants within a {w10}.",
        "Count about {rest} restaurants within a {w10} of this address.",
    ]),
    "park_near": ("green", [
        "{park} is about {park_mins} on foot.",
        "The morning walk reaches {park} in about {park_mins}.",
        "Green is close: about {park_mins} to {park}.",
        "You and the dog are about {park_mins} from {park}.",
        "It is about {park_mins} on foot to {park}, short enough for a lunch-break loop.",
        "About {park_mins} out the door, you are at {park}.",
        "A quick walk, about {park_mins}, puts you in {park}.",
        "For daily walks, {park} is about {park_mins} away.",
    ]),
    "dog_no_limit": ("dog", [
        "Dogs are welcome with no weight limit.",
        "No weight limit on dogs here, so the puppy can grow into whatever it becomes.",
        "The pet policy sets no weight limit, which keeps your choice of dog open.",
        "Big dog, small dog, the building does not mind: there is no weight limit.",
        "You can pick the dog you want, because the policy has no weight limit.",
        "There is no weight cap on dogs in this building.",
        "The listing puts no weight limit on dogs, and that is worth noticing.",
        "Any size of dog is fine by the policy here, with no weight limit.",
    ]),
    "newer": ("newer", [
        "The building dates from {built}, so it is among the newer ones you will see.",
        "This is a newer building, finished in {built}.",
        "Construction finished in {built}, so you would be an early tenant in the building's life.",
        "A {built} building, with the newer feel that comes with it.",
        "The building went up in {built}.",
        "You would be living in a building from {built}, young by this region's standards.",
        "It is a recent building, completed in {built}.",
        "Finished in {built}, this is the newer end of what is out there.",
    ]),
    "lot": ("parking", [
        "The car goes in the building's lot{ptail}.",
        "There is a lot on the property for the car{ptail}.",
        "Parking is in an on-site lot{ptail}.",
        "Your car gets a space in the lot{ptail}.",
        "The building has its own lot{ptail}.",
        "You would park in the building's lot{ptail}.",
        "Off-street parking is a lot on the grounds{ptail}.",
        "For the car, there is a lot on site{ptail}.",
    ]),
    "lounge": ("work", [
        "When the apartment gets small on a workday, the building has a lounge or coworking room.",
        "There is a lounge or coworking space in the building, handy for someone who works from home.",
        "You work from home, and this building gives you a second place to do it.",
        "A shared lounge or work room comes with the building, for the days you need new walls.",
        "The building has a common lounge or coworking area, so video calls have a backup spot.",
        "For work-from-home days there is a resident lounge or coworking room.",
        "Some mornings you will want to work outside the apartment, and the building has a room for that.",
        "A lounge or coworking room on site means the desk is optional some days.",
    ]),
    "station": ("train", [
        "The train at {station} is {station_mi} miles away, for the days you would rather not drive.",
        "A train is close: {station}, {station_mi} miles from the door.",
        "You can walk to the train at {station}, {station_mi} miles off.",
        "Friends coming by train get off at {station}, {station_mi} miles away.",
        "The car can stay parked some days, with the train at {station} {station_mi} miles away.",
        "It is {station_mi} miles to the train at {station}.",
        "For a night out without the car, {station} is {station_mi} miles from the lobby.",
        "The nearest train stop, {station}, is {station_mi} miles away.",
    ]),
    "errands": ("errands", [
        "{market} is {market_mi} miles away, so groceries are a walk.",
        "Groceries are close: {market}, {market_mi} miles from the door.",
        "You can carry the groceries home from {market}, {market_mi} miles off.",
        "It is {market_mi} miles to {market}, which makes a forgotten ingredient a small problem.",
        "The weekly shop is a short trip, with {market} {market_mi} miles away.",
        "For dog food and dinner both, {market} is {market_mi} miles from the lobby.",
        "A supermarket, {market}, sits {market_mi} miles away.",
        "The nearest supermarket is {market}, {market_mi} miles off.",
    ]),
    "gym": ("gym", [
        "There is a gym in the building.",
        "The gym is an elevator ride away.",
        "A gym comes with the building, which helps on work-from-home days.",
        "You can skip the gym down the road, because the building has its own.",
        "The building keeps a gym for residents.",
        "A workout is close, in the building's own gym.",
        "On-site gym, so the commute to exercise is the elevator.",
        "A fitness room on the property saves you a membership somewhere else.",
    ]),
    "avail_now": ("date", [
        "It is available now.",
        "The keys could be yours right away.",
        "This one is open today, with no waiting list to sit on.",
        "Move-in is immediate here.",
        "Available now, so the timing is entirely yours.",
        "You would not wait for this one: it is ready now.",
        "Ready now, which suits a search that starts this month.",
        "Nothing to wait for here, since the apartment is open now.",
    ]),
    "avail_date": ("date", [
        "It opens on {date}.",
        "Move-in is {date}.",
        "The keys are ready {date}.",
        "Mark {date}, the day this one becomes available.",
        "Available from {date}.",
        "You could move in on {date}.",
        "This one frees up on {date}.",
        "The listing gives {date} as the move-in date.",
    ]),
    # ---- always on offer, so there is always another angle to turn to
    "basic": ("price", [
        "{Akind} at about {price} a month all in.",
        "The plain facts: {akind}, about {price} a month all in.",
        "This is {akind} that runs about {price} a month all in.",
        "On the bill, {akind} here comes to about {price} a month all in.",
        "Simple offer: {akind} for about {price} a month all in.",
        "{Akind}, about {price} a month once everything is counted.",
        "You are looking at {akind} for about {price} a month all in.",
        "No frills to report, just {akind} at about {price} a month all in.",
    ]),
    "basic_no_price": ("cost_open", [
        "{Akind} in this neighborhood, with the all-in cost still to be worked out.",
        "The plain facts: {akind}, with no all-in figure yet.",
        "This is {akind}, and the full monthly cost is still an open number.",
        "{Akind} here, though we cannot give you an all-in figure yet.",
        "You are looking at {akind}, with the monthly total still to pin down.",
        "{Akind}, and the first job is getting the full monthly cost from the office.",
        "A straightforward {kind}, with the complete bill not worked out yet.",
        "For now this is {akind} without a firm all-in number.",
    ]),
    "type": ("type", [
        "{Akind}, plain and simple.",
        "What is on offer here is {akind}.",
        "This listing is for {akind}.",
        "Think of this as {akind} that does what it says.",
        "The layout is {akind}.",
        "Here you would be renting {akind}.",
        "It is {akind}, with no surprises in the floor plan.",
        "On the page this is {akind}, nothing more complicated.",
    ]),
    "tour": ("tour", [
        "I would put this one on the tour list and let the visit decide.",
        "This is one to judge in person.",
        "Keep this on the list, because some places only make sense once you stand in them.",
        "Worth a look with your own eyes before you rule it in or out.",
        "Let the walkthrough make the case for this one.",
        "Go see it, and trust what you notice in the first minute.",
        "The listing is modest about itself, so the tour has to speak for it.",
        "Hold your verdict on this one until you have walked through it.",
    ]),
}
COVERS = {"value": {"value", "size"}}              # support facts a lead already uses, besides its own angle
PATTERN_IDS = [f"{cond}_{i + 1}" for cond, (_, texts) in LEADS.items() for i in range(len(texts))]
PEER_CONDITIONS = {"only_pool", "only_garage", "cheapest", "biggest", "value", "pick", "only_doorman", "highest",
                   "only_laundry", "only_dogspot", "fewest_questions", "closest_run", "soonest_now", "soonest_date",
                   "newest", "closest_park"}


def minutes(x) -> str:
    m = int(round(max(1.0, float(x))))
    return f"{m} minute" if m == 1 else f"{m} minutes"


def lead_conditions(f, peers):
    """-> [(score, condition, values to fill, fields used)], every condition whose fact is true for this unit.
    Higher score = more distinctive."""
    n = len(peers)
    two = n == 2
    small = -25 if two else 0                         # "the cheaper of 2" is worth less than "the cheapest of 9"
    out = []

    def add(score, cond, vals=None, **used):
        out.append((score, cond, {"n": n, "w10": WALK_RADIUS, **(vals or {})}, used))

    price = usd(f["all_in"]) if f["all_in"] else None
    sqft = whole(f["sqft"]) if f["sqft"] else None
    onsite = f["dog_amenity"][2:-8] if f["dog_amenity"] and "on site" in f["dog_amenity"] else None   # "dog park"
    fee_tail = f", at {usd(f['park_fee'])} a month" if f["park_fee"] else ", though the fee is not published"
    run = {"dogpark": f["dog_park"], "dogpark_mi": miles(f["dog_park_m"])} if f["dog_park"] and f["dog_park_m"] is not None else None
    park = {"park": f["park"], "park_mins": minutes(f["park_walk"])} if f["park"] and f["park_walk"] is not None else None

    # ---- against the other places shown in the same neighbourhood
    if only(f, peers, lambda p: p["pool"]):
        add(90 + small, "only_pool", peers=n, pool=True)
    if only(f, peers, lambda p: p["park_kind"] == "garage"):
        add(88 + small, "only_garage", {"gtail": "" if f["park_included"] else fee_tail}, peers=n, parking="garage",
            parking_fee=f["park_fee"])
    if extreme(f, peers, "all_in", min):
        add(85 + small, "cheapest", {"price": price, "low": "lower" if two else "lowest"}, peers=n, all_in=f["all_in"])
    if extreme(f, peers, "sqft", max):
        add(80 + small, "biggest", {"sqft": sqft, "big": "roomier" if two else "roomiest"}, peers=n, sqft=f["sqft"])
    if f["rank"] == 1 and n >= 3:
        add(75, "pick", peers=n, hood_rank=1)
    if only(f, peers, lambda p: bool(p["doorman"])):
        add(72 + small, "only_doorman", peers=n, doorman=f["doorman"])
    if f["floor_sure"] and extreme(f, peers, "floor", max):
        add(70 + small, "highest", {"floor": f["floor"], "high": "higher" if two else "highest"}, peers=n, floor=f["floor"])
    if only(f, peers, lambda p: p["laundry"]):
        add(68 + small, "only_laundry", peers=n, in_unit_laundry=True)
    if onsite and only(f, peers, lambda p: bool(p["dog_amenity"]) and "on site" in p["dog_amenity"]):
        add(67 + small, "only_dogspot", {"dogthing": onsite}, peers=n, dog_amenities=f["dog_amenity"])
    if extreme(f, peers, "per_sqft", min):
        add(66 + small, "value", {"price": price, "sqft": sqft}, peers=n, all_in=f["all_in"], sqft=f["sqft"])
    if extreme(f, peers, "open_questions", min):
        add(64 + small, "fewest_questions", peers=n, open_questions=f["open_questions"])
    if run and f["dog_park_m"] <= 1600 and extreme(f, peers, "dog_park_m", min):
        add(63 + small, "closest_run", run, peers=n, dog_park=f["dog_park"], dog_park_miles=run["dogpark_mi"])
    s = soonest(f, peers)
    if s == "now":
        add(62 + small, "soonest_now", peers=n, available="now")
    elif s == "date":
        add(60 + small, "soonest_date", {"date": f["avail"]}, peers=n, available=f["avail"])
    if f["age_days"] is not None and f["age_days"] <= 14 and extreme(f, peers, "age_days", min, everyone=False):
        d = f["age_days"]
        add(58 + small, "newest", {"ago": "today" if d == 0 else "1 day ago" if d == 1 else f"{d} days ago"},
            peers=n, listing_age_days=d)
    if park and f["park_walk"] <= 8 and extreme(f, peers, "park_walk", min):
        add(56 + small, "closest_park", park, peers=n, park=f["park"], park_walk_min=park["park_mins"].split()[0])

    # ---- facts that stand on their own
    if f["park_included"]:
        add(65, "parking_included", parking="included")
    if onsite:
        add(58, "dog_onsite", {"dogthing": onsite}, dog_amenities=f["dog_amenity"])
    if f["park_kind"] == "garage" and not f["park_included"]:
        if f["park_fee"]:
            add(55, "garage_priced", {"fee": usd(f["park_fee"])}, parking="garage", parking_fee=f["park_fee"])
        else:
            add(55, "garage_unpriced", parking="garage", parking_fee=None)
    if f["free_months"]:
        m = "month" if f["free_months"] == 1 else "months"
        add(52, "concession", {"free": f"{f['free_months']} {m}"}, free_months=f["free_months"])
    if f["sqft"] and f["sqft"] >= 850:
        add(50, "big", {"sqft": sqft}, sqft=f["sqft"])
    if f["pool"]:
        add(50, "pool", pool=True)
    if run and f["dog_park_m"] <= 800:
        add(48, "dogpark_near", run, dog_park=f["dog_park"], dog_park_miles=run["dogpark_mi"])
    if f["doorman"]:
        add(45, "front_desk" if f["doorman"] == "24-hour" else "doorman", doorman=f["doorman"])
    if f["floor"] and f["floor"] >= 10 and f["floor_sure"]:
        add(45, "high_floor", {"floor": f["floor"]}, floor=f["floor"])
    if f["margin"] is not None and f["margin"] >= 400 and f["all_in"]:
        add(42, "margin", {"price": price, "margin": usd(f["margin"])}, all_in=f["all_in"], cap_margin=f["margin"])
    if f["laundry"]:
        add(40, "laundry", in_unit_laundry=True)
    if f["park_kind"] == "covered" and not f["park_included"]:
        tail = f", at {usd(f['park_fee'])} a month" if f["park_fee"] else ", with the fee not published"
        add(40, "covered", {"ptail": tail}, parking="covered", parking_fee=f["park_fee"])
    if f["restaurants"] is not None and f["restaurants"] >= 20:
        add(38, "food", {"rest": whole(f["restaurants"])}, restaurants_800m=int(f["restaurants"]))
    if park and f["park_walk"] <= 5:
        add(35, "park_near", park, park=f["park"], park_walk_min=park["park_mins"].split()[0])
    if f["no_weight_limit"]:
        add(34, "dog_no_limit", dog_weight_limit="no limit")
    if f["built"] and f["built"] >= 2015:
        add(32, "newer", {"built": f["built"]}, year_built=f["built"])
    if f["park_kind"] == "lot" and not f["park_included"]:
        tail = f", at {usd(f['park_fee'])} a month" if f["park_fee"] else ", with the fee not published"
        add(30, "lot", {"ptail": tail}, parking="lot", parking_fee=f["park_fee"])
    if f["lounge"]:
        add(28, "lounge", lounge_or_coworking=True)
    if f["station"] and f["station_m"] is not None and f["station_m"] <= 800:
        add(26, "station", {"station": f["station"], "station_mi": miles(f["station_m"])},
            train_station=f["station"], train_station_miles=miles(f["station_m"]))
    if f["market"] and f["market_m"] is not None and f["market_m"] <= 500:
        add(24, "errands", {"market": f["market"], "market_mi": miles(f["market_m"])},
            supermarket=f["market"], supermarket_miles=miles(f["market_m"]))
    if f["gym"]:
        add(20, "gym", gym=True)
    if f["avail"] == "now":
        add(12, "avail_now", available="now")
    elif f["avail"]:
        add(12, "avail_date", {"date": f["avail"]}, available=f["avail"])
    # always on offer, so there is always another angle to turn to
    kind = f["beds"] or "place"
    names = {"kind": kind, "akind": f"a {kind}", "Akind": f"A {kind}"}
    if f["all_in"]:
        add(5, "basic", {**names, "price": price}, beds=f["beds"], all_in=f["all_in"])
    else:
        add(5, "basic_no_price", names, beds=f["beds"])
    add(3, "type", names, beds=f["beds"])
    add(1, "tour")
    return out


def support_phrases(f, covered):
    """Short noun phrases for the second sentence, most useful first; never a fact the lead already used."""
    out = []

    def add(score, kind, text, **used):
        if kind not in covered:
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
FRAMES = {"wp": SECOND_WITH_PRICE, "np": SECOND_NO_PRICE, "po": PRICE_ONLY}


def words(text):
    return len(text.split())


class Spread:
    """Keeps count of how often each wording has been used in this run, so none passes its share of the units."""

    def __init__(self, n_units):
        self.n = n_units
        self.used = defaultdict(Counter)                # family -> wording id -> count
        self.line_cap = share_cap(LINE_SHARE, n_units)
        self.catch_cap = share_cap(CATCH_SHARE, n_units)
        self.cond_cap = share_cap(COND_SHARE, n_units)

    def cap(self, family):
        return self.catch_cap if family == "catch" else self.line_cap

    def free(self, family, key):
        return self.used[family][key] < self.cap(family)

    def take(self, family, key):
        self.used[family][key] += 1

    def choose(self, family, keys, listing_id, salt, avoid=(), must=False):
        """The first key, in the listing's own seeded order, that is under its cap and not in `avoid`. With `must`,
        a key is always returned: the least used one outside `avoid` when every cap is reached."""
        order = rotate(list(keys), listing_id, salt)
        for k in order:
            if k not in avoid and self.free(family, k):
                return k
        if not must:
            return None
        rest = [k for k in order if k not in avoid] or order
        return min(rest, key=lambda k: self.used[family][k])


def compose_line(f, peers, spread=None, before=()):
    """-> (host_line, pattern_id, used, meta). `before` is the list of meta dicts of the units ranked above this one
    in the same neighbourhood, nearest last. Rules kept here: the three top-ranked places have three different
    angles; a unit never repeats the condition or the opening three words of the unit just above it; no wording
    passes its share of the page."""
    spread = spread or Spread(len(peers))
    before = list(before)
    rank_index = len(before)
    last = before[-1] if before else {}
    top_angles = {b["angle"] for b in before[:3]} if rank_index < 3 else set()
    recent_angles = {b["angle"] for b in before[-2:]}
    recent_opens = {b["open3"] for b in before[-2:]}
    heard = {b["pattern"] for b in before}
    heard_frames = {b["frame"] for b in before}

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
        if c[1] == last.get("cond"):
            return False
        return not strict_angle or LEADS[c[1]][0] not in top_angles

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


# ------------------------------------------------------------------ the catch
# CATCHES[kind] = [sentences]. One sentence each, never about crime: every unit shown has already passed the safety
# rule, so the catch is about living there (owner's rule, 2026-11-16). An unknown is an "ask", never a statement.

UNKNOWN_NAMES = {"building fees": "building fees", "pet rent": "pet rent", "parking fee": "the parking fee", "gas": "the gas bill"}
CATCHES = {
    "confirm:listing": [
        "There is an open question about whether this unit is still available at this price, so call before you plan a visit.",
        "Before you get attached, phone the office and confirm this exact unit is still offered at this price.",
        "We could not fully confirm this listing is current, so make the first call about whether it still exists at this rent.",
        "Treat the price and the availability as unverified until the leasing office says yes to both.",
        "This one needs a phone call first, because whether it is still available at this price is not settled.",
        "Ask the office to confirm the unit and the rent in an email before you spend a Saturday on it.",
        "The listing could have changed since we read it, so check that it is live before you tour.",
        "Whether this unit is really on offer at this price is still unsettled, and a single call will clear it up.",
    ],
    "confirm:live check": [
        "We have not re-checked this listing live yet, so the price and the date are as first collected.",
        "The price and move-in date here are from our first read and still await a fresh check.",
        "This listing is waiting on our live re-check, so confirm the rent and the date when you call.",
        "Take the numbers as a first reading, because we have not been back to verify them.",
        "A second look at this listing is still pending, so ask the office to confirm today's rent.",
        "Until we re-check it, treat the rent and the availability date as a snapshot.",
        "The figures are from our first pass and not yet re-verified, so open your call by confirming them.",
        "We owe this listing a fresh check, and until then the rent and date are provisional.",
    ],
    "confirm:elevator": [
        "Elevator access for this exact unit is not confirmed, so ask before you tour.",
        "The elevator is the open item here: get a clear yes for this unit before you visit.",
        "You said no stairs, and the elevator for this unit is still unconfirmed, so ask first.",
        "Make the first thing you ask whether an elevator reaches this apartment, because we could not confirm it.",
        "Nothing we read settles whether this unit has elevator access, so open with that.",
        "Hold off on booking the tour until the office confirms an elevator serves this unit.",
        "Whether an elevator reaches this apartment is unanswered, and it is a dealbreaker, so ask early.",
        "Ask them to put elevator access for this unit in writing, since it is not confirmed yet.",
    ],
    "confirm:dogs allowed": [
        "Listing sites disagree on whether dogs are allowed here, so get the dog policy in writing.",
        "The dog policy is the open item: the sources conflict, so ask for a written yes.",
        "Before anything else, have the office confirm in writing that your dog is welcome, because the listings do not agree.",
        "We found mixed signals on dogs here, so settle that with the office before you tour.",
        "Whether dogs are allowed is not settled for this place, and it has to be before you apply.",
        "The listings contradict each other on dogs, so let the leasing office break the tie in writing.",
        "Keep your heart out of this one until someone at the office confirms the dog policy.",
        "A firm answer on dogs is still missing here, since what we read about the policy conflicts.",
    ],
    "confirm:dogs": [
        "The dog policy here is not settled, so get it in writing.",
        "We could not pin down the dog policy, so ask the office for it in an email.",
        "Dogs are the open item at this address, so have the office confirm before you tour.",
        "Until the office confirms the dog policy, treat this one as a maybe.",
        "The pet rules are unclear here, so ask for a written yes on dogs.",
        "Get the dog policy from the leasing office directly, because the listing leaves it unsettled.",
        "Make the dog policy your opening topic, since nothing we read settles it.",
        "Ask them to confirm that a dog is welcome, in writing, before you apply.",
    ],
    "confirm:availability": [
        "This is a floor plan and not a specific apartment yet, so ask which unit, which floor and what date.",
        "What is advertised is a layout, so ask the office which actual unit is open and when.",
        "The listing shows a plan type only, so the unit number, the floor and the date are yours to ask for.",
        "No specific apartment is attached to this price yet, so get a unit number before you tour.",
        "You would be touring a model of this plan unless you ask which exact unit is available.",
        "Pin down the actual unit behind this floor plan, including its floor and its move-in date.",
        "The price is for a plan, and the apartment itself is still unnamed, so ask which unit it is.",
        "Ask them to name the unit, because right now this is a floor plan with a price on it.",
    ],
    "confirm:eligibility": [
        "Who qualifies to rent here is not settled, so ask whether there is an income limit before you tour.",
        "Ask first whether this unit is open to any renter, because an income limit is possible here.",
        "Eligibility is the open item: confirm with the office that you can apply at all.",
        "There are signs this building has income rules, so check that you qualify before you get attached.",
        "Before the tour, have the office tell you whether an income limit applies to this unit.",
        "We could not settle whether this unit has an income cap, so start your call there.",
        "An income restriction is possible on this unit, so confirm you are eligible before spending time on it.",
        "The office needs to confirm that this apartment is open to all renters, since what we read conflicts.",
    ],
    "confirm:floor": [
        "The floor is not published, so confirm it is above the ground floor.",
        "No floor is given for this unit, so ask which floor it is on before you tour.",
        "Ask which floor this apartment sits on, since the listing leaves it out.",
        "The listing skips the floor, and you want to be above ground level, so ask.",
        "Confirm the floor with the office, because the page does not give it.",
        "Which floor this is remains unstated, so get it before you visit.",
        "You asked for no ground-floor units, and this listing does not state its floor.",
        "Get the floor number in writing, since it is missing from the listing.",
    ],
    "confirm:lease term": [
        "The lease term behind this price is not clear, so ask what a 12-month lease costs.",
        "Ask which lease length this rent belongs to, because the page does not say.",
        "The price comes without a stated term, so get the 12-month figure.",
        "Before you compare, find out what lease length earns this rent.",
        "The term attached to this rent is unstated, so ask for it.",
        "Get the lease length in writing, since the price depends on it.",
        "This rent could belong to an unusual term, so ask what a 12-month lease would cost.",
        "Ask the office what term this price assumes.",
    ],
    "confirm:cost near the cap": [
        "The all-in sits close to your cap, so any fee the listing left out could push it over.",
        "This is near the top of your budget, so ask about every fee before you tour.",
        "There is little room under your cap here, so get the full monthly bill in writing.",
        "A single unlisted fee would put this over your limit, so ask for all of them.",
        "The bill is close to your ceiling, which makes every missing fee matter.",
        "Check the complete monthly cost first, because this one has almost no cushion.",
        "With the total this near your cap, ask the office to list every charge.",
        "You are at the edge of your budget here, so leave nothing unpriced.",
    ],
    "confirm:question": [                            # {q} is the unit's own open question, quoted as it stands
        "One thing is unconfirmed, so ask the leasing office this: {q}",
        "Before you tour, put this to the office: {q}",
        "There is an open item here, and the way to close it is to ask: {q}",
        "Start your call with this, because we could not confirm it: {q}",
        "The thing to settle first is this: {q}",
        "Ask the office directly, since nothing we read answers it: {q}",
        "Hold your plans until someone answers this for you: {q}",
        "A single unanswered point stands between you and a tour: {q}",
    ],
    "confirm:other": [
        "One thing about this listing is unconfirmed, so call the leasing office before you tour.",
        "There is an open item on this listing, so ask the office about it before you visit.",
        "Something here still needs confirming, so phone ahead.",
        "This listing has a loose end, and a call to the office should tie it off.",
        "Before you tour, have the office settle the open item on this listing.",
        "We could not confirm everything about this place, so check with the office first.",
        "Hold your plans until the office answers the open item here.",
        "A detail on this listing is unverified, so start with a phone call.",
    ],
    "rent:net_effective": [
        "The price shown is a net-effective rent, so the monthly bill will be higher than it looks, and you should ask for the gross rent.",
        "This rent is averaged over a free period, so ask what you actually pay in a normal month.",
        "The advertised number already has the special baked in, which means the real monthly rent is higher.",
        "Read this price as an average after free time, and get the full monthly rent before you compare.",
        "What you see is a net-effective figure, so the check you write each month will be bigger.",
        "The listing quotes rent after its discount, so ask for the gross rent and budget on that.",
        "This is a discounted average and the lease will state a higher monthly rent, so ask for that number.",
        "Do your math on the gross rent, because the price shown spreads a free period across the lease.",
    ],
    "rent:needs_call": [
        "The page does not say whether the advertised rent is before or after its special, so ask for the full monthly rent.",
        "There is a special on this listing and no word on whether the price already includes it, so ask what the rent is in a normal month.",
        "Ask whether the advertised rent is the full monthly rent or an average after the free period, because the page does not say.",
        "A special is attached to this price and its effect is unstated, so get the regular rent in writing.",
        "The rent could be a before-special or an after-special number, and only the office can tell you which.",
        "Until they tell you what a month costs once the offer ends, treat this price as a maybe.",
        "The offer muddies the price, so start by asking what the lease will say you owe each month.",
        "I cannot tell from the page whether the special is already in this rent, so make them spell it out.",
        "Get the first full payment and the regular monthly rent from the office, since the special leaves both unclear.",
        "This price has a special riding on it, and the listing never says how the pieces fit together, so ask.",
        "Compare this one only after you have the rent without the special, which the page leaves out.",
        "The honest status of this price is unconfirmed, because the listing does not explain how its special applies.",
    ],
    "unknown:parking": [
        "Parking isn't published for this place, so ask where the car goes and what it costs before anything else.",
        "The listing says nothing about parking, so ask where the car sleeps and what that costs before you tour.",
        "For you the first thing to learn is where the car goes and for how much, because parking isn't published here.",
        "Nobody has told us where a car lives at this address, so that is the first thing to ask.",
        "There is no word on parking, and you are bringing a car, so settle that before the tour.",
        "The gap in this listing is the car: no parking details at all, so ask for the options and the prices.",
        "Until the office explains parking, I would hold your enthusiasm, because the listing is silent on it.",
        "Ask what parking exists and what it costs, since the page skips the subject entirely.",
        "Your car is unaccounted for here, so get the parking answer in writing before you apply.",
        "The listing leaves parking out, which for a driver is the thing to ask about first.",
    ],
    "unknown:costs_tight": [
        "{Names} {verb} not published, and with only {margin} under your cap the real all-in could go over, so ask.",
        "With just {margin} of room under your cap, the unpublished {bare} could tip this over, so get the numbers.",
        "The all-in here leaves out {names}, and {margin} of headroom could fall short of covering them.",
        "Ask for {names} in dollars, because only {margin} separates this place from your ceiling.",
        "This fits your budget by {margin} on paper, before {names}, which the listing does not give.",
        "The listing omits {names}, and you have {margin} to absorb them before you pass your cap.",
        "Get {names} confirmed first, since the cushion under your cap is only {margin}.",
        "On paper you are {margin} under your limit, and the missing {bare} could easily eat that.",
    ],
    "lease_term": [
        "This price is tied to a {months}-month lease, so ask what other terms cost.",
        "The rent shown is for a {months}-month lease, so ask for the 12-month price too.",
        "You are looking at a {months}-month lease price, and a different term could cost more.",
        "The listed rent assumes a {months}-month lease, so check what the term you want would run.",
        "Mind the term: this rent goes with a {months}-month lease.",
        "A {months}-month lease is what earns this price, so ask about the standard term.",
        "The number on the page is the {months}-month rate, so ask how other lease lengths are priced.",
        "Before you compare, ask what this costs on a 12-month lease, since the price shown is for {months} months.",
    ],
    "weak:distance": [
        "The weak spot is distance: about {drive} minutes to your parents each way, before traffic.",
        "Sunday dinner is about {drive} minutes each way from here, and that is without traffic.",
        "The trade is the drive home, about {drive} minutes each way on a clear road.",
        "What you give up here is closeness: your parents are about {drive} minutes away with no traffic.",
        "Be honest with yourself about a drive of about {drive} minutes each way to see your parents.",
        "The catch is on the map, about {drive} minutes to your parents before any traffic.",
        "Every visit home costs about {drive} minutes each way, on a good day.",
        "It is about {drive} minutes to your parents each way with clear roads, the price of this address.",
    ],
    "weak:space": [
        "The weak spot is size, at {sqft} square feet for you, a desk and a dog.",
        "At {sqft} square feet, you, the desk and the dog will be sharing closely.",
        "The trade is room: {sqft} square feet has to hold your office and your dog.",
        "Measure your desk before you fall for this, because {sqft} square feet goes fast.",
        "It is on the small side at {sqft} square feet, and you work from home.",
        "The catch is the floor plan, {sqft} square feet for a life that includes a home office.",
        "You would feel the {sqft} square feet on a long workday with a restless dog.",
        "Space is what you give up here, with {sqft} square feet in total.",
    ],
    "weak:cost": [
        "The weak spot is cost: about {price} all in leaves only about {margin} under your cap.",
        "At about {price} all in, you are within about {margin} of your ceiling.",
        "The trade is the bill, about {price} a month all in, with about {margin} to spare.",
        "This sits near the top of your budget, about {margin} under the cap at about {price} all in.",
        "There is little slack here: about {price} all in, about {margin} from your limit.",
        "The catch is the price, about {price} a month all in, only about {margin} below your cap.",
        "You would be spending nearly all of your budget, with about {margin} left after about {price} all in.",
        "Money is the tight part, at about {price} all in and about {margin} of room.",
    ],
    "weak:daily": [
        "The weak spot is daily life on foot, with {what} within a {w10}.",
        "Walking to dinner is the thin part here, with {what} within a {w10}.",
        "Most meals out would start in the car, with {what} within a {w10}.",
        "The trade is the neighborhood on foot: {what} within a {w10}.",
        "Leave the idea of strolling to dinner behind, with {what} within a {w10}.",
        "The catch is what is outside the door, {what} within a {w10}.",
        "On foot the options are few, with {what} within a {w10}.",
        "Errands and dinners lean on the car here, with {what} within a {w10}.",
    ],
    "weak:dog": [
        "The weak spot is the dog's routine: the nearest dog park is {dogpark_mi} miles away.",
        "For the dog, the trade is distance, with the nearest dog park {dogpark_mi} miles off.",
        "Off-leash time takes a trip here, since the closest dog park is {dogpark_mi} miles away.",
        "The catch is for the puppy: {dogpark_mi} miles to the nearest dog park.",
        "Plan on long leash walks, because the nearest dog park is {dogpark_mi} miles from the door.",
        "The dog park is the weak link, {dogpark_mi} miles away at the nearest.",
        "The nearest dog park sits {dogpark_mi} miles out, which shapes the dog's whole week.",
        "It is {dogpark_mi} miles to the closest dog park, so weekday exercise is on you and the sidewalk.",
    ],
    "weak:car": [
        "The weak spot is the car: the listing offers {pphrase}, so see the space yourself.",
        "For the car you get {pphrase}, which is the thinnest part of this offer, so look at it in person.",
        "Parking is the soft spot, {pphrase}, so walk out and see where the car would sit.",
        "The catch is where the car lives: {pphrase}, and you should inspect it on the tour.",
        "Ask to see the parking before the apartment, since {pphrase} is the weakest thing here.",
        "What the listing gives the car is {pphrase}, so judge that with your own eyes.",
        "The trade here is parking, {pphrase}, and a look at the actual space will tell you the rest.",
        "Your car gets {pphrase}, the least convincing line on this listing, so check it yourself.",
    ],
    "weak:building": [
        "The building is the part I am least sure of, so look hard at the lobby, the elevator and the hallways on the tour.",
        "Of everything here, the building itself impresses me least, so judge the common areas in person.",
        "Give the hallways, the elevator and the mail room a long look, because the building is the soft spot.",
        "The apartment could charm you, so make a point of inspecting the rest of the building too.",
        "The catch is the building around the unit, so ride the elevator and walk a hallway before you decide.",
        "On the tour, spend as long in the lobby and the corridors as in the apartment, since the building is the weaker half.",
        "What the building offers beyond the unit is thin, so see the shared spaces for yourself.",
        "I would test the elevator and look at upkeep in the halls, because the building is where this place is weakest.",
    ],
    "unknown:costs": [
        "{Names} {verb} not published, so ask what {they} to the monthly bill.",
        "The listing leaves out {names}, so get the figures before you compare.",
        "Ask for {names} in dollars, since the all-in above does not have them.",
        "The all-in is missing {names}, so the true bill could run higher.",
        "Before you compare this with others, get {names} from the office.",
        "A few lines are blank on this one, namely {names}, so ask.",
        "The office still owes you {names}, which the listing does not give.",
        "Fill in {names} with a phone call, because the page leaves them out.",
    ],
    "none": [
        "Nothing stands out as a problem on paper, which is exactly when a tour matters most.",
        "I have no caution to give you from the listing, so let the tour look for one.",
        "On paper this is clean, and the visit is where you test that.",
        "The listing holds up, so use the tour to check what a page cannot show, like light and noise.",
        "No red flag in the data, which leaves the in-person look as the real test.",
        "The catch, if there is one, will show on the tour, because the listing gives me nothing to warn you about.",
        "I looked for the weak spot and did not find one in the listing, so look for it in person.",
        "Everything checks out in writing, so bring your skepticism to the walkthrough.",
    ],
}
CONFIRM_KINDS = {"listing", "live check", "elevator", "dogs allowed", "dogs", "availability", "eligibility", "floor",
                 "lease term", "cost near the cap"}
SWAPPABLE = {"rent:net_effective", "rent:needs_call", "unknown:parking", "unknown:costs_tight", "lease_term"}


def catch_options(u, f):
    """-> [(kind, values to fill, fields used)], most important first. In this order: the unit's open question (its
    asterisk); a rent the page leaves ambiguous; parking not published; unpublished costs that could break the cap;
    an unusual lease term; otherwise the unit's weakest fact. The first is the catch; the later ones are true too,
    and one of them is used only so that the three top-ranked places of a neighbourhood do not all carry the same
    caution (the section subhead under "what it costs you" still flags an ambiguous rent)."""
    out = []
    c = u.get("confirm") or {}
    if c.get("asterisk") and c.get("what"):
        what = str(c["what"])
        text = (str(c.get("why") or "") + " " + str(c.get("question") or "")).lower()
        if what in CONFIRM_KINDS and (what != "eligibility" or "income" in text):
            return [(f"confirm:{what}", {}, {"confirm_what": what})]
        q = str(c.get("question") or "").strip()
        if q:
            return [(f"confirm:{what}", {"_library": "confirm:question", "q": q},
                     {"confirm_what": what, "confirm_question": q})]
        return [("confirm:other", {}, {"confirm_what": what})]
    rent = u.get("rent") or {}
    if rent.get("basis_kind") == "net_effective":
        out.append(("rent:net_effective", {}, {"rent_basis_kind": "net_effective"}))
    elif rent.get("asterisk") and rent.get("needs_call"):
        out.append(("rent:needs_call", {}, {"rent_needs_call": True}))
    if f["park_kind"] is None:
        out.append(("unknown:parking", {}, {"parking": None}))
    names = u.get("all_in_unknown") or []
    unknown = [UNKNOWN_NAMES.get(x, x) for x in names]
    cost_vals = {"names": join_and(unknown), "Names": cap_first(join_and(unknown)), "bare": join_and(list(names)),
                 "verb": "is" if len(unknown) == 1 else "are", "they": "it adds" if len(unknown) == 1 else "they add"}
    tight = f["margin"] is not None and 0 < f["margin"] < 100 * len(unknown)   # each missing line could be about $100
    if unknown and f["all_in"] and tight:
        out.append(("unknown:costs_tight", {**cost_vals, "margin": usd(f["margin"])},
                    {"all_in_unknown": names, "cap_margin": f["margin"]}))
    lease = num(get(u, "cost_check", "lease_term_months")) or num(rent.get("lease_months"))
    if lease and int(lease) != 12:
        out.append(("lease_term", {"months": int(lease)}, {"lease_months": int(lease)}))
    out.append(weakest(u, f, unknown, cost_vals, names))
    return out


def weakest(u, f, unknown=(), cost_vals=None, names=()):
    """The lowest-scoring part of the unit that can be said from its own fields. Safety is skipped on purpose."""
    parts = {k: v for k, v in (get(u, "scores", "parts") or {}).items() if num(v) is not None}
    for kind in sorted(parts, key=lambda k: (parts[k], k)):
        drive = num(get(u, "moments", "sun", "drive_min"))
        if kind == "distance" and drive:
            return "weak:distance", {"drive": whole(drive)}, {"drive_min": drive}
        if kind == "space" and f["sqft"]:
            return "weak:space", {"sqft": whole(f["sqft"])}, {"sqft": f["sqft"]}
        if kind == "cost" and f["all_in"] and f["margin"] is not None:
            return ("weak:cost", {"price": usd(f["all_in"]), "margin": usd(f["margin"])},
                    {"all_in": f["all_in"], "cap_margin": f["margin"]})
        rest = num(get(u, "moments", "after", "restaurants_800m"))
        if kind == "daily" and rest is not None:
            n = int(rest)
            what = "no restaurants" if n == 0 else f"only {n} restaurant" + ("" if n == 1 else "s")
            return "weak:daily", {"what": what, "w10": WALK_RADIUS}, {"restaurants_800m": n}
        if kind == "dog" and f["dog_park_m"] is not None:
            return "weak:dog", {"dogpark_mi": miles(f["dog_park_m"])}, {"dog_park_miles": miles(f["dog_park_m"])}
        if kind == "car" and f["park_kind"]:
            return ("weak:car", {"pphrase": parking_phrase(f["park_kind"], f["park_fee"], f["park_included"])},
                    {"parking": f["park_kind"], "parking_fee": f["park_fee"]})
        if kind == "building":
            return "weak:building", {}, {"weakest_part": "building"}
    if unknown:
        return "unknown:costs", cost_vals, {"all_in_unknown": list(names)}
    return "none", {}, {}


def compose_catch(u, f, spread=None, before=()):
    """-> (host_catch, kind, used, wording id). One sentence. `before` as in compose_line: among the three top-ranked
    places of a neighbourhood no catch wording repeats, and where a unit has a second real caution the kind does not
    repeat either."""
    spread = spread or Spread(1)
    before = list(before)
    options = catch_options(u, f)
    kind, vals, used = options[0]
    if len(before) < 3 and kind in SWAPPABLE:
        taken = {b["catch_kind"] for b in before}
        if kind in taken:
            for other in options[1:]:
                if other[0] in SWAPPABLE and other[0] not in taken:
                    kind, vals, used = other
                    break
    library = vals.get("_library", kind)                 # "_library": the unit's own question, quoted in a frame
    texts = CATCHES.get(library) or CATCHES["confirm:other"]
    recent = {b["catch_id"] for b in before[-2:]}
    vals = {k: v for k, v in vals.items() if k != "_library"}
    ids = [f"{library}_{i + 1}" for i in range(len(texts))]
    cid = spread.choose("catch", ids, f["id"], "catch", avoid={b["catch_id"] for b in before}) \
        or spread.choose("catch", ids, f["id"], "catch", avoid=recent, must=True)
    text = cap_first(texts[ids.index(cid)].format(**vals))
    spread.take("catch", cid)
    return text, kind.replace("costs_tight", "costs"), used, cid


# ------------------------------------------------------------------ section subheads
# One short line (at most 14 words, no numbers: the section's headline states them) under the cost, parking, dog and
# building headlines of a place. Each is picked by what the unit's fields say; an unknown gets an "ask" line, never a
# statement; when nothing distinctive can be said, or every wording has reached its share, the subhead is empty.

SUB_MAX_WORDS = 14
SUBS = {
    "cost": [
        ("net_effective", [
            "The price shown is after a discount, so ask for the real monthly rent.",
            "This is a net-effective number, and the monthly bill will be higher.",
            "The rent is an average over a free period, so budget on the gross.",
            "Ask for the gross rent, because this figure already has the special in it.",
            "What you pay each month is more than the number shown here.",
            "A discounted average, so get the lease rent before you compare.",
            "The special is baked into this price, so the real rent runs higher.",
            "Do the math on the full rent, since this spreads out a free period.",
        ]),
        ("ambiguous_rent", [
            "There is a special here, so ask what a normal month costs.",
            "Ask whether this price is before or after the free period.",
            "A special clouds this number, so get the regular rent in writing.",
            "The offer and the rent are tangled, so ask them to separate the pieces.",
            "Find out what you owe monthly once the special runs out.",
            "This price rides on a special, and the page never explains how.",
            "Treat the rent as unconfirmed until the office explains the offer.",
            "Ask for the rent without the special before you compare anything.",
            "The headline price has an offer attached, so ask for the plain number.",
            "Get the first full payment in writing, because the special blurs it.",
            "Nobody says whether the special is already counted, so ask.",
            "The deal is real, and the true monthly rent is still unanswered.",
            "Make them spell out the rent after the offer ends.",
            "Before or after the special is what this price leaves open.",
        ]),
        ("tight", [
            "Right at your ceiling, so a single surprise fee tips it over.",
            "No room to spare here, so every unlisted fee matters.",
            "This sits at the top of your budget, with nothing left for extras.",
            "The bill nearly touches your cap, so ask about every fee.",
            "There is almost no cushion under your limit here.",
            "Any fee they forgot to list would push this past your cap.",
            "Budget-wise this is the edge, so get the full bill in writing.",
            "You would be spending right up to your limit each month.",
        ]),
        ("unpublished", [
            "Some costs are unpublished, so treat this number as a floor.",
            "They leave some fees off the page, so ask for the full monthly bill.",
            "The total is missing a few lines, so it could climb.",
            "Ask what the listing leaves out before you trust the total.",
            "This is the bill so far, with some fees still unpublished.",
            "A few charges are blank, so the real number could run higher.",
            "The page skips some fees, so get them from the office.",
            "Count this as a starting figure until the missing fees come in.",
            "Some fees go unlisted here, so ask for the complete monthly cost.",
            "There are gaps in the fee list, and each is something to ask.",
            "The all-in is honest about what it knows and silent on the rest.",
            "Fill in the unlisted fees before you compare this with the others.",
        ]),
        ("roomy", [
            "Leaves real room under your ceiling for the things nobody lists.",
            "Comfortably inside your budget, with money left for the sofa.",
            "Well under your cap, so a surprise fee would not sink it.",
            "There is slack in the budget here, and slack is a comfort.",
            "You keep a good piece of your budget every month.",
            "The bill leaves room for furniture, vet visits and a night out.",
            "Easy on your limit, with a cushion to spare.",
            "This place gives your budget room to breathe.",
        ]),
    ],
    "parking": [
        ("unknown", [
            "They say nothing about parking, so make it your opening question.",
            "Parking is not published here, so ask before you fall for it.",
            "No word on where the car goes, so ask first.",
            "The listing is silent on parking, so the question is yours to ask.",
            "Where the car sleeps is unanswered, so ask before the tour.",
            "Ask what parking exists and what it costs, since the page skips it.",
            "The car is the open question at this address.",
            "Ask for the parking answer in writing before anything else.",
        ]),
        ("included", [
            "The spot comes with the lease, so the car costs nothing extra.",
            "Parking is part of the deal, so there is no monthly fee to chase.",
            "A spot is included, which settles the car on day one.",
            "No parking bill here, since the lease includes a space.",
            "The car is taken care of in the rent.",
            "Your space is in the lease, with nothing added for it.",
            "They include parking, and that is money you keep.",
            "The spot is yours with the apartment.",
        ]),
        ("garage_priced", [
            "Your car sleeps indoors, and you never circle the block.",
            "Pull in, park under a roof, and the day is over.",
            "A garage with the price on the page, so you can budget now.",
            "Indoor parking at a stated price, which is how it should be.",
            "The car gets a garage, and they tell you what it costs.",
            "No hunting for a spot, and no guessing at the fee.",
            "Garage parking with a published price, an easy yes for a driver.",
            "The garage fee is listed, so the car's cost is settled.",
        ]),
        ("garage_unpriced", [
            "Indoor parking, but they don't publish the price, so ask before you commit.",
            "A garage with no price listed, so get the monthly fee in writing.",
            "The car gets a garage, and the fee is still a question.",
            "There is a garage, with the price missing from the page.",
            "A garage is promised, so ask what it adds each month.",
            "Indoor parking exists, and the cost is yours to ask about.",
            "The garage is real and its fee is unpublished, so ask.",
            "Your car parks inside, at a price they have not shared.",
            "Ask for the garage fee before you count this as affordable.",
            "Garage, yes, and the monthly charge is not published.",
            "They list a garage and skip the price, so ask for it.",
            "The garage fee is the missing number here.",
            "A roof for the car, with the fee left for you to ask.",
            "Get the garage price from the office, because the listing leaves it out.",
        ]),
        ("covered_priced", [
            "A roof over the car, with the price on the page.",
            "Covered parking, so no scraping ice in January.",
            "The car parks under cover at a stated price.",
            "Covered and priced, which makes the car easy to budget.",
            "Your car stays out of the weather, and you know the fee.",
            "A covered spot with a published price.",
            "Rain or snow, the car is under a roof, at a listed fee.",
            "They cover the car and they print the price.",
        ]),
        ("covered_unpriced", [
            "Covered parking, though they don't publish the price, so ask.",
            "The car gets a roof, and the fee is a question for the office.",
            "A covered spot exists, with the price left off the page.",
            "Ask what covered parking costs, since the listing does not say.",
            "Under cover, yes, and the monthly fee is still unknown.",
            "The covered parking has no price listed, so get it in writing.",
            "Your car stays dry here, at a fee you will have to ask for.",
            "Covered parking is offered, and its cost is the missing piece.",
        ]),
        ("lot_priced", [
            "A spot in the building's lot, so you are off the street.",
            "Lot parking with a listed price, which beats hunting the curb.",
            "The car gets a lot space at a stated fee.",
            "Off-street parking in the lot, with the price published.",
            "You park in the building's lot, and you know what it costs.",
            "A lot on site and a fee on the page.",
            "The lot keeps you off the curb, at a listed price.",
            "Parking is a lot space, priced in the listing.",
        ]),
        ("lot_unpriced", [
            "A lot on site, but no price on the page, so ask.",
            "There is a lot, and what it costs is still a question.",
            "The car goes in the lot, at a fee they have not published.",
            "Ask what a lot space costs, since the listing skips it.",
            "Off-street parking exists, with the price missing.",
            "A lot is listed and its fee is left out, so ask.",
            "You would park in the lot, and the cost is yours to confirm.",
            "The lot has no posted price, so get the fee in writing.",
        ]),
        ("onsite_unpriced", [
            "Parking exists on site, and the details are yours to ask for.",
            "They mention parking and little else, so ask what kind and how much.",
            "There is parking, with the type and the fee both unstated.",
            "Ask what the on-site parking is and what it costs.",
            "Parking is promised in a word, so get the specifics.",
            "The listing says parking and stops there, so ask for the rest.",
            "On-site parking, with everything else about it left to ask.",
            "Some parking exists here, and the office has to fill in the details.",
        ]),
    ],
    "dog": [
        ("conflicting", [
            "The dog policy is unsettled, so get a yes in writing.",
            "Listings disagree about dogs here, so confirm before you tour.",
            "Mixed signals on dogs, so ask the office to settle it.",
            "Whether dogs are welcome is not settled, so ask first.",
            "Get the dog policy confirmed before you get attached.",
            "The sources conflict on dogs, so only a written answer counts.",
            "Ask them to confirm dogs are allowed, because the listings differ.",
            "Dogs are a question mark here until the office says yes.",
        ]),
        ("onsite", [
            "The dog's first walk of the day can start in the elevator.",
            "A place for the dog without leaving the property.",
            "The building keeps a spot for dogs on the grounds.",
            "Late-night walks can be short ones, right on the property.",
            "Your dog gets its own corner of the property.",
            "On rainy mornings, the on-site dog area earns its keep.",
            "The dog has somewhere to go that is still home.",
            "A dog area on site makes a puppy's schedule easier.",
        ]),
        ("near_run", [
            "A dog run is close enough for a quick morning lap.",
            "The dog gets a proper run before your first meeting.",
            "Within walking reach of the door, there is a dog run.",
            "Off-leash time is a short walk away.",
            "The nearest dog run is close, which a puppy will love.",
            "You can make the dog run a daily habit from here.",
            "Fetch before work is realistic at this address.",
            "The dog run is near enough to visit on a lunch break.",
        ]),
        ("small_only", [
            "The page says small dogs and gives no weight, so ask for the number.",
            "Small dogs are welcome, and the exact limit is a question to ask.",
            "They say small dogs only, without saying how small.",
            "Ask what small means in pounds before you choose a puppy.",
            "The policy mentions small dogs and no weight, so get the figure.",
            "Fine for small dogs, with the cutoff left unstated.",
            "Find out the weight behind the words small dog.",
            "A small-dog policy with no number, so ask for the limit.",
        ]),
        ("weight_limit", [
            "There is a weight limit, so check it against the dog you choose.",
            "Dogs are welcome up to a weight limit, so choose the puppy accordingly.",
            "The policy caps a dog's weight, so think about adult size.",
            "Mind the weight limit when you pick a breed.",
            "Dogs are allowed under a set weight, so know your puppy's future.",
            "A weight limit applies, and puppies grow.",
            "Check the adult weight of your dog against the policy here.",
            "The dog policy has a weight ceiling to plan around.",
        ]),
        ("pet_rent_unknown", [
            "Dogs are welcome, though they don't publish the pet rent, so ask.",
            "No pet rent on the page, so ask what the dog adds each month.",
            "The dog is welcome, and the monthly pet charge is unstated.",
            "Ask about pet rent and any pet fee before you apply.",
            "Pet rent is the missing line, so get it from the office.",
            "They allow dogs and leave the pet rent off the page.",
            "What the dog costs each month here is still a question.",
            "Dogs, yes, and the pet rent is yours to ask about.",
            "The pet charge is unpublished, so add it to your call list.",
            "Find out the pet rent, because the listing skips it.",
        ]),
    ],
    "building": [
        ("front_desk", [
            "Someone is at the desk when you come home late.",
            "A staffed front desk, which also means your packages wait for you.",
            "The desk is staffed around the clock.",
            "There is always a person in the lobby.",
            "Day or night, somebody is at the front desk.",
            "A desk that never closes, handy for deliveries and late nights.",
            "Packages and visitors meet a person here, at any hour.",
            "The lobby has staff at all hours.",
        ]),
        ("doorman", [
            "A doorman at the door, and a familiar face after a long day.",
            "There is a doorman, so deliveries and late arrivals are easier.",
            "This is a doorman building.",
            "Someone holds the door, which you will come to like.",
            "A doorman comes with the address.",
            "The front door is staffed by a doorman.",
            "You get a doorman, a small daily comfort.",
            "A doorman greets you on the way in.",
        ]),
        ("pool_laundry", [
            "A pool on the property and laundry in your own apartment.",
            "Laundry at home and a pool for the weekend.",
            "Your own washer and dryer, plus a pool.",
            "The machines are in the unit and the pool is on the grounds.",
            "In-unit laundry for weekdays, a pool for weekends.",
            "A pool to swim in and no laundry room to visit.",
            "A pool outside and a washer and dryer inside your own door.",
            "Wash at home, then go for a swim.",
        ]),
        ("laundry", [
            "Laundry happens in your own apartment, on your own schedule.",
            "The washer and dryer are yours alone.",
            "In-unit laundry, so no trips with a basket.",
            "Your own machines, behind your own door.",
            "A washer and dryer in the unit, which a dog owner will use.",
            "No laundry room runs from this apartment.",
            "The laundry is in the apartment.",
            "You can run a load without leaving home.",
        ]),
        ("pool", [
            "A pool comes with the building, and summer gets easier.",
            "There is a pool, and yes, you would use it.",
            "The building has a pool for residents.",
            "Summer weekends have a pool attached.",
            "A pool on the property, for hot days and visiting friends.",
            "You get a pool with this address.",
            "The pool is part of the package.",
            "After work in July, there is a pool waiting.",
        ]),
        ("gym", [
            "A gym in the building, which helps in February.",
            "The gym is an elevator ride away.",
            "There is a gym on the property.",
            "A resident gym comes with the building.",
            "You can work out without leaving the building.",
            "The building's gym makes a membership optional.",
            "A fitness room is part of the building.",
            "Exercise is close, in the building's own gym.",
        ]),
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


# ------------------------------------------------------------------ the run

FIELDS = ["listing_id", "host_line", "host_catch", "sub_cost", "sub_parking", "sub_dog", "sub_building", "facts_used_json"]
SUB_COLS = ["sub_cost", "sub_parking", "sub_dog", "sub_building"]


def build(units):
    """units: the `units` list of site/data.json. -> rows with the columns in FIELDS. Neighbourhoods are taken in
    name order and units in rank order, so the same data always gives the same text."""
    by_hood = defaultdict(list)
    for u in units:
        by_hood[u.get("hood_id")].append(u)
    spread = Spread(len(units))
    rows = []
    for hood in sorted(by_hood, key=str):
        group = sorted(by_hood[hood], key=lambda u: (num(get(u, "scores", "hood_rank")) or 1e9, str(u["id"])))
        peers = [facts(u) for u in group]
        before = []
        for u, f in zip(group, peers):
            line, pid, used, meta = compose_line(f, peers, spread, before)
            catch, ckind, cused, cid = compose_catch(u, f, spread, before)
            subs, sub_kinds = compose_subs(u, f, spread, before)
            before.append({**meta, "catch_kind": ckind if not ckind.endswith(":costs") else cid.rsplit("_", 1)[0],
                           "catch_id": cid, "subs": {s[4:]: t for s, t in subs.items()}})
            rows.append({"listing_id": u["id"], "host_line": line, "host_catch": catch, **subs,
                         "facts_used_json": json.dumps({"hood_id": hood, "pattern": pid, "angle": meta["angle"],
                                                        "frame": meta["frame"], "line": used, "catch_kind": ckind,
                                                        "catch_id": cid, "catch": cused, "subs": sub_kinds},
                                                       ensure_ascii=False, sort_keys=True)})
    return rows


def distribution(rows):
    """-> {family: (units carrying a text, distinct wordings, the commonest wording, its count)} for the report."""
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
    print(f"{len(rows)} units written to {a.out}")
    print(f"limits: a line wording or subhead on at most {LINE_SHARE:.0%} of units, a catch wording on at most {CATCH_SHARE:.0%}")
    for name, d in distribution(rows).items():
        print(f"  {name:22} {d['with_text']:4} units, {d['distinct']:3} distinct, commonest {d['top_count']:3} "
              f"({d['top_share']:.1%}): {str(d['top'])[:60]}")
    kinds = Counter(json.loads(r["facts_used_json"])["catch_kind"] for r in rows)
    print(f"catch kinds: {dict(kinds.most_common())}")


if __name__ == "__main__":
    main()
