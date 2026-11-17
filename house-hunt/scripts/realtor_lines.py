#!/usr/bin/env python3
"""Compose the "About the building" text and the per-apartment line and catch for everything shown on the page.

The apartment list changes with every repair run, so nothing here is hand-written per apartment or per building. For
each building in site/data.json (its apartments grouped by building_id) and for each apartment, this script reads the
fields, works out which facts are most distinctive, and fills one of the hand-written sentences in the libraries below.

Per BUILDING  ->  data/reference/building_about.csv
  about_building     1 or 2 sentences, at most 40 words: the building's most distinctive feature (parking, a pool, a
                     doorman, laundry, a dog area, its age), then the most useful thing near it
  about_points_json  3 to 5 icon points [{icon, text}], text at most 14 words; exactly one has the icon "warning": the
                     main thing to ask about. A fact the sentences already state is not repeated as a point.
  facts_used_json    the sentences chosen and every value printed

Per APARTMENT  ->  data/reference/realtor_lines.csv
  host_line   1 or 2 short sentences: what sets THIS apartment apart inside its building (price, size, floor, move-in
              date, how little is left to ask) or, failing that, its own most useful fact; then its price and size.
              The building's features are in "About the building" and are not repeated here.
  host_catch  1 or 2 short sentences: the one thing to ask or watch, taken from the apartment's own open item, else
              from its disclosures (a special offer, costs that could pass the limit, the lease term, the dog weight
              limit, a condo, the floor), else its weakest own fact
  sub_cost, sub_parking, sub_dog, sub_building   one optional short line (at most 14 words, no numbers) for under each
              section headline; empty when the fields give nothing to say
  facts_used_json   the wording chosen and every value that was printed, so each word can be traced to a field

THE STANDARD (copy edit of 2026-11-16, the same one applied to the experience and neighborhood text; the guards are in
scripts/check_scene_text.py and are run over every text by scripts/test_realtor_lines.py):
  * every sentence makes sense on first read. No personification, no joke, nothing that needs decoding, no template
    connective ("Then the practical side", "Count on", "Add ...", "Note ... as well");
  * vocabulary: apartment (never unit), building, "your $3,000 limit" (never cap or ceiling), no narrator (no "we",
    "our", "I"), no project terms (net-effective, scorecard, ranked, verified, live check, gate, asterisk);
  * numbers only when useful, with their units, rounded as the page rounds in sentences: prices to the nearest $10
    with "about", sizes "about 610 square feet"; the page shows two labelled prices and
    the text names which one it gives: the total is "about $2,670 a month with utilities and fees" on the first
    mention in a text ("about $2,670 a month" after), what the listing asks is "rent", exact to the dollar ("The rent
    is $2,345, about $2,670 a month with utilities and fees."); never "everything included", never "all-in";
  * short is better. A line is the plain fact; a catch is the plain question.

How the wording is spread. Variety matters less than clarity, so there are only a few wordings per fact, all plain:
  * no lead wording, catch wording, building sentence or subhead is on more than SHARE (8%) of the rows. A subhead
    that has reached its share is left empty (each building's best apartment, the one the page shows, is served first);
  * the price-and-size sentence, the icon points and the warning are plain facts in the same words wherever the fact
    is the same, as on the neighborhood pages; they are not varied;
  * the first three apartments of a building lead with different facts, and no two of them read identically; two
    neighboring buildings do not open with the same sentence.

Rules the code keeps (scripts/test_realtor_lines.py checks them):
  * deterministic: choices are seeded by listing_id / building_id and made in a fixed order, so a rerun on the same
    data gives the same text;
  * an unknown is never stated as a fact: parking that is not published is an "ask"; a garage with no price is "fee
    not published", never "free"; a dog policy that is not settled is never "dogs are allowed";
  * parking is read from the STRUCTURED fields (parking_facts: parking.kind, included_kind, fee, fee_kind,
    optional_kinds; independent check 5, N1): "garage" only where the space she would park in is a garage, a fee only
    for the kind it belongs to, the other kind named as what it is ("A free open lot; garage spaces are $125 a
    month."), off-site parking called off-site, an assigned or unnamed space said to be that;
  * the nearest station is named by its kind (station_words: train station / subway station / PATH station / light
    rail stop); "washer and dryer" only where a source names both, "the listing shows ..." where the only source is
    a listing site's appliance list (laundry_mode);
  * a catch states a reason only when the apartment's own fields give it (CATCH_BASIS): "listing sites disagree about
    dogs" only where the open item says so; "the price shown includes a special offer" only where the rent block says
    the price is the average after an offer; otherwise "the listing does not say whether the price includes it";
  * a superlative ("the largest in the building") is claimed only when every other apartment there publishes the figure;
  * every number printed is the apartment's or building's own field (rounded), the count it is compared with, or her
    limit; none is typed;
  * no crime or safety wording.

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
CAP = 3000                                # her monthly limit, on the total with utilities and fees (meta.cap_all_in in site/data.json)
MAX_WORDS = 45                            # host_line
CATCH_MAX_WORDS = 40                      # host_catch
ABOUT_MAX_WORDS = 40                      # about_building
POINT_MAX_WORDS = 14
SUB_MAX_WORDS = 14
POINTS_COUNT = (3, 5)
WALK_RADIUS = "10-minute walk"            # the page's wording for the 800 m radius
SHARE = 0.08                              # no lead, catch, building sentence or subhead wording on more than 8% of rows
LINE_SHARE = CATCH_SHARE = SUB_SHARE = SHARE
UNPRICED = re.compile(r"not published|does not publish|does not give", re.I)   # every unpriced-parking sentence says so
ICONS = ["home", "dog", "park", "car", "parking", "fork", "cocktail", "coffee", "train", "money", "clock", "moon", "sun",
         "water", "key", "heart", "people", "ruler", "laundry", "pool", "warning"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
          "December"]


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


def round10(x) -> int:
    """To the nearest 10, halves up: how the page's sentences round prices and sizes."""
    return int(float(x) / 10 + 0.5) * 10


def about_usd(x) -> str:
    return f"${round10(x):,}"


def about_sqft(x) -> str:
    return f"{round10(x):,}"


def miles(meters) -> str:
    return f"{max(0.1, round(float(meters) / 1609.34, 1)):.1f}"


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
    """'now' -> ('now', None); '2026-12-01' -> ('December 1', date)."""
    if not avail:
        return None, None
    if str(avail).lower() == "now":
        return "now", None
    try:
        d = date.fromisoformat(str(avail)[:10])
    except ValueError:
        return None, None
    return f"{MONTHS[d.month - 1]} {d.day}", d


def rotate(options, key, salt):
    """The options in an order seeded by the listing or building id (stable across reruns)."""
    k = seed(key, salt) % len(options)
    return options[k:] + options[:k]


def share_cap(share, n):
    return max(3, int(share * n))


def words(text):
    return len(text.split())


# ------------------------------------------------------------------ what the fields say

# How the page data files a parking space (parking.kind / included_kind / optional_kinds[].kind, and the head of the
# older parking.type string) -> the kind the sentences speak of. A lot is a lot whether open, gated or assigned.
PARK_KIND = {"garage": "garage", "covered": "covered", "gated_lot": "lot", "assigned_lot": "lot", "open_lot": "lot",
             "open lot": "lot", "lot": "lot", "off_street": "off_street", "assigned": "assigned", "offsite": "offsite",
             "street": "street", "street_only": "street", "unspecified": "unspecified", "parking": "unspecified"}


def parking_facts(u):
    """What the listing says about parking, read from the STRUCTURED fields (independent check 5, N1: "garage" was
    written for an open lot because the text read the head of parking.type, and an off-site deck became "the
    building's lot"). -> {kind, detail, fee, included, extras, deck, assigned}
      kind      the space she would park in: None (nothing published) | garage | covered | lot | off_street | assigned
                (an assigned space, the listing does not say where) | offsite | street | unspecified (parking of a
                kind the listing does not name). Where a space is included, this is the INCLUDED kind.
      detail    the page data's own word for it (open_lot, gated_lot, assigned_lot, ...)
      fee       the published monthly fee of THAT kind (never a resident's estimate, never the fee of another kind);
                0.0 where a space is included; None where it is not published
      included  a space of this kind comes with the rent (parking.fee is 0 and parking.included_kind is set)
      extras    [(detail kind, published fee or None)]: the other spaces offered at an added cost
      deck      the off-site parking is a parking deck (the source's own word)
    Page data written before the structured fields existed (and the tests' short records) is read from the head of
    parking.type and from fee_note, as before."""
    p = u.get("parking") or {}
    t = str(p.get("type") or "").strip()
    head, _, tail = t.partition(":")
    head = head.strip().lower()
    raw = str(p.get("kind") or "").strip().lower()
    none = {"kind": None, "detail": None, "fee": None, "included": False, "extras": [], "deck": False, "assigned": False}
    if not t and not raw:
        return none
    fee = num(p.get("fee"))
    if str(p.get("fee_basis") or "").lower().startswith("estimate"):
        fee = None                                   # a figure from a resident's review is not the building's published price (D18)
    if raw:
        inc_kind = str(p.get("included_kind") or "").strip().lower()
        included = fee == 0 and bool(inc_kind)
        detail = inc_kind if included else raw
    else:
        detail = "garage" if head.startswith("garage") else "covered" if head.startswith("covered") else \
            "open_lot" if head in ("lot", "open_lot", "open lot") else "street" if head.startswith("street") else \
            "assigned" if head == "assigned" else "offsite" if head.startswith("offsite") or head.startswith("off-site") \
            else "unspecified"
        included = fee == 0 and "included or free" in str(p.get("fee_note") or "")
    if detail not in PARK_KIND:
        detail = "unspecified"
    if fee == 0 and not included:
        fee = None                                   # a zero with no "included" note is not a published price
    fee_kind = str(p.get("fee_kind") or "").strip().lower()
    if fee and fee_kind and PARK_KIND.get(fee_kind) != PARK_KIND[detail]:
        fee = None                                   # the fee belongs to another kind of space: never attach it to this one
    extras = []
    for o in p.get("optional_kinds") or []:
        if isinstance(o, dict) and str(o.get("kind") or "").lower() in PARK_KIND:
            f = num(o.get("fee"))
            if str(o.get("fee_basis") or "").lower().startswith("estimate") or not f:
                f = None
            extras.append((str(o["kind"]).lower(), f))
    return {"kind": PARK_KIND[detail], "detail": detail, "fee": fee, "included": included, "extras": extras,
            "deck": PARK_KIND[detail] == "offsite" and bool(re.search(r"\bdeck\b", tail, re.I)),
            "assigned": bool(p.get("assigned")) or detail in ("assigned", "assigned_lot")}


def parking_kind(u):
    """-> (kind, fee, included): the first three of parking_facts(). kind is None when the listing publishes nothing
    about parking."""
    P = parking_facts(u)
    return P["kind"], P["fee"], P["included"]


EXTRA_RANK = ["garage", "covered", "gated_lot", "assigned_lot", "open_lot", "off_street"]
EXTRA_WORDS = {"garage": "garage spaces", "covered": "covered spaces", "gated_lot": "spaces in the gated lot",
               "assigned_lot": "assigned outdoor spaces", "open_lot": "open-lot spaces", "off_street": "off-street spaces"}


def parking_extra(P):
    """The one other kind of space worth naming beside the space she would park in -> (detail kind, fee) or None.
    A garage first, then covered parking, then the lots; a second price for the SAME kind is named last ("other
    spaces"). Off-site and street parking name no extra."""
    if P["kind"] in (None, "offsite", "street") or not P["extras"]:
        return None
    rank = lambda e: (e[0] == P["detail"], EXTRA_RANK.index(e[0]) if e[0] in EXTRA_RANK else 99)
    ex = sorted((e for e in P["extras"] if e[0] in EXTRA_RANK), key=rank)
    return ex[0] if ex else None


def extra_words(P):
    """-> "; garage spaces are $125 a month" | "; garage spaces cost extra" | "" """
    e = parking_extra(P)
    if not e:
        return ""
    what = "other spaces" if e[0] == P["detail"] else EXTRA_WORDS[e[0]]
    return f"; {what} are {usd(e[1])} a month" if e[1] else f"; {what} cost extra"


def lot_space(P):
    return {"assigned_lot": "an assigned space in an open lot", "gated_lot": "a space in the gated lot"}.get(
        P["detail"], "a space in the open lot")


def offsite_where(P):
    return "in an off-site deck" if P["deck"] else "off-site, not at the building"


def parking_point(P, long=False):
    """The one plain sentence that says exactly what the structured parking fields carry: the kind of space, whether
    it is included or what it costs, and the other kind offered at a cost. Never "garage" unless the kind is a
    garage; never a fee that belongs to another kind. `long` allows the fuller wording of an assigned space."""
    k, fee, inc = P["kind"], P["fee"], P["included"]
    if k is None:
        return ""
    x = extra_words(P)
    money = usd(fee) if fee else None
    if k == "garage":
        s = "A garage space is included in the rent" if inc else f"Garage parking costs {money} a month" if fee else \
            "Garage parking, with the fee not published"
    elif k == "covered":
        s = "A covered parking space is included in the rent" if inc else f"Covered parking costs {money} a month" if fee \
            else "Covered parking, with the fee not published"
    elif k == "lot":
        if P["detail"] == "open_lot":
            s = "A free open lot" if inc else f"A space in the building's lot costs {money} a month" if fee else \
                "A parking lot, with the fee not published"
        else:
            sp = cap_first(lot_space(P))
            s = f"{sp} is included" if inc else f"{sp} costs {money} a month" if fee else f"{sp}, with the fee not published"
    elif k == "off_street":
        s = "Free off-street parking" if inc else f"Off-street parking costs {money} a month" if fee else \
            "Off-street parking, with the fee not published"
    elif k == "assigned":
        s = ("An assigned space is included; the listing does not say " + ("whether it is a garage or a lot" if long else "where")) \
            if inc else f"An assigned space costs {money} a month; the listing does not say where" if fee else \
            "An assigned space, with its kind and fee not published"
        x = ""
    elif k == "offsite":
        s = f"Parking is {offsite_where(P)}, {money} a month" if fee else f"Parking is {offsite_where(P)}, with the fee not published"
    elif k == "street":
        s = "The only parking named is on the street"
    else:
        s = "A parking space is included; the listing does not say what kind" if inc else \
            f"Parking of an unnamed kind costs {money} a month" if fee else \
            "The listing mentions parking without saying what kind: ask"
        x = ""
    if x and len((s + x).split()) > POINT_MAX_WORDS:
        x = ""
    return s + x + "."


def rent_asked(u):
    """The page's "Rent": the rent line of the cost lines, in whole dollars. Given only where it is plainly what the
    listing asks every month: the line is the listed rent (not a 12-month or an after-offer price) and no offer or
    open question hangs on it. None otherwise; the text then gives the total alone."""
    rent = u.get("rent") or {}
    if has_special(u) or rent.get("asterisk") or rent.get("needs_call") or rent.get("basis_kind") not in (None, "listed"):
        return None
    for x in u.get("all_in_lines") or []:
        if isinstance(x, dict) and re.match(r"rent\b", str(x.get("line") or ""), re.I):
            v = num(x.get("amount"))
            if x.get("code") != "rent_listed" or v is None or v != int(v) or v <= 0:
                return None
            return int(v)
    return None


def dog_amenity(u):
    # the kind (park, run, spa, wash) is in the source's words; amenities.dog_park_or_run is the same reading as a flag
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


def desk_kind(am):
    """What the building's front-door amenity really is, read from the exact fields (independent check 4, D9: "A
    doorman is at the front door" was written for 87 apartments whose source says only "Concierge").
    -> None | 'doorman' | 'doorman24' | 'concierge' | 'concierge24' | 'attended' | 'attended24'.
    'doorman' is said only when the doorman amenity is set AND its source text does not say something else:
      - a text naming a doorman or door person -> doorman;      - a text naming only a concierge -> concierge;
      - "attended lobby" -> attended;                           - "virtual doorman" alone -> nothing;
      - a separate concierge amenity (amenities.concierge, the pipeline's split field) with no doorman -> concierge.
    A bare "yes" beside the doorman field is the field's own word and stays a doorman."""
    am = am or {}
    if "concierge" in am or "front_desk" in am:
        # the page data after independent check 4: three separate fields, each set only from a source that says so
        # (amenities.doorman, .concierge, .front_desk; "24h" = staffed around the clock). Each is said as what it is.
        clean = lambda k: "" if str(am.get(k) or "").strip().lower() in ("", "no", "none", "false", "nan") else str(am[k]).strip().lower()
        door, conc, desk = clean("doorman"), clean("concierge"), clean("front_desk")
        if door:
            return "doorman24" if door == "24h" else "doorman"
        if conc:
            return "concierge24" if conc == "24h" else "concierge"
        if desk:
            return "attended24" if desk == "24h" else "attended"
        return None
    val = str(am.get("doorman") or "").strip().lower()
    text = str(am.get("doorman_text") or "").strip().lower()
    conc = str(am.get("concierge") or "").strip().lower()
    conc_text = str(am.get("concierge_text") or "").strip().lower()
    if val in ("no", "none", "false", "nan"):
        val = ""
    if conc in ("no", "none", "false", "nan"):
        conc = ""
    both = text + " " + conc_text
    all_day = val == "24h" or conc == "24h" or bool(re.search(r"24|all hours|round[- ]the[- ]clock", both))
    names_door = bool(re.search(r"(?<!virtual )\bdoor ?(?:man|men|person|woman|staff|attendant)", text))
    names_conc = "concierge" in both
    attended = bool(re.search(r"attended lobby|lobby attendant|front desk", both))
    if val and names_door:
        return "doorman24" if all_day else "doorman"
    if (val and names_conc) or (conc and not names_door and not (val and not text)):
        return "concierge24" if all_day else "concierge"
    if val and attended:
        return "attended24" if all_day else "attended"
    if val and "virtual" in text:
        return None
    if val:
        return "doorman24" if val == "24h" else "doorman"
    return None


def laundry_kind(am):
    """-> 'wd' (a washer AND a dryer are named in the apartment) | 'washer' (a washer only: the source names no
    dryer; independent check 5, N6) | 'in_unit' (laundry in the apartment, machines not named) | None. The in-unit
    flag alone is not enough when the source text beside it says something else ("On-site laundry", "W/D hookup",
    "not in unit"): then nothing is claimed. amenities.in_unit_appliances, where the page data has it, says which
    machines a source names: 'washer' is never written as "washer and dryer"."""
    am = am or {}
    if am.get("in_unit_laundry") != "yes":
        return None
    t = str(am.get("laundry") or "").strip().lower()
    if re.search(r"not in unit|not in-unit", t):
        return None
    says_in = bool(re.search(r"in[ _-]?unit|washer|dryer|^yes$", t))
    if t and not says_in:                                  # "On-site laundry", "W/D hookup; On-site laundry"
        return None
    app = str(am.get("in_unit_appliances") or "").strip().lower()
    if app == "washer" or re.search(r"\bno dryer\b", t):
        return "washer"
    if app == "dryer" or re.search(r"\bno washer\b", t):
        return "in_unit"
    if re.search(r"washer", t) and re.search(r"dryer", t):
        return "wd"
    return "in_unit"


def laundry_listed(am):
    """True when the only source for laundry in the apartment is a listing site's appliance list (a tag "Washer,
    Dryer"), which no page's own words confirm: the text then says "The listing shows ...", never a flat assertion."""
    return str((am or {}).get("in_unit_laundry_basis") or "") == "listing_site_appliance_list"


def laundry_mode(am):
    """-> None | 'wd' | 'in_unit' (a page says so) | 'washer' | 'listed_wd' | 'listed_washer' | 'listed' (a listing
    site's appliance list only)."""
    k = laundry_kind(am)
    if k is None:
        return None
    if k == "washer":
        return "listed_washer" if laundry_listed(am) else "washer"
    if laundry_listed(am):
        return "listed_wd" if k == "wd" else "listed"
    return k


def garage_mixed(u):
    """She would park in a garage, and the listing also names a surface lot or outdoor spaces: "a garage" is true,
    "you would park in the garage" is more than the field says (D18)."""
    P = parking_facts(u)
    if P["kind"] != "garage":
        return False
    if any(PARK_KIND.get(k) in ("lot", "off_street") for k, _ in P["extras"]):
        return True
    t = str((u.get("parking") or {}).get("type") or "").lower()
    rest = t.split(":", 1)[1] if ":" in t else ""
    return bool(re.search(r"surface|\blot\b|outdoor|outside|uncovered|open parking|off-street|carport", rest))


OVERCLAIM = {                                           # a wording is skipped when the field does not carry it
    "laundry_plain": re.compile(r"washer|dryer", re.I),
    "garage_mixed": re.compile(r"you would park in the building's garage|park indoors|under cover|there is a garage for your car", re.I),
}


def fits(text, f):
    """May this wording be used for an apartment or building with these facts?"""
    if f.get("laundry") and f.get("laundry_mode", "in_unit") == "in_unit" and not f.get("laundry_wd") and \
            OVERCLAIM["laundry_plain"].search(text):
        return False
    if f.get("garage_mixed") and OVERCLAIM["garage_mixed"].search(text):
        return False
    return True


def disclosed(u):
    return {str(d.get("what")) for d in (u.get("disclosures") or []) if isinstance(d, dict)}


def net_effective(u):
    """True only when the rent block itself says the price shown is the average after an offer, and its offer text
    does not say the page leaves the point unstated. Anything less is "a special offer, ask"."""
    rent = u.get("rent") or {}
    if rent.get("basis_kind") != "net_effective":
        return False
    return not re.search(r"not stated|does not say|unstated", str(rent.get("offer_text") or ""), re.I)


def has_special(u):
    """An offer makes the rent unclear: the page flags it and wants a call, or the unit carries the "special offer"
    disclosure, or it was marked as an after-offer price without the proof net_effective wants."""
    rent = u.get("rent") or {}
    return bool(rent.get("asterisk") and rent.get("needs_call")) or "special offer" in disclosed(u) or \
        (rent.get("basis_kind") == "net_effective" and not net_effective(u))


DOG_REASONS = [                                        # (what the open item's text says, the catch family it allows)
    (r"disagree|and another says", "conflict"),
    (r"upon approval|on approval", "approval"),
    (r"case by case", "case"),
    (r"contact for more information|contact the building for its pet policy", "contact"),
    (r"small pets", "small pets"),
    (r"no policy text", "no text"),
]


def dog_open(u):
    """The apartment's open item is whether dogs are allowed -> the reason its own text gives (a key of DOG_REASONS),
    or 'open' (no reason that can be stated). None when dogs are not the open item."""
    c = u.get("confirm") or {}
    if not (c.get("asterisk") and str(c.get("what") or "").startswith("dogs")):
        return None
    why = str(c.get("why") or "").lower()
    for key, reason in DOG_REASONS:
        if re.search(key, why):
            return reason
    return "open"


def facts(u):
    """Everything the sentences may use, read straight from the apartment. Missing stays None."""
    am = u.get("amenities") or {}
    park = parking_facts(u)
    kind, fee, included = park["kind"], park["fee"], park["included"]
    floor = num(u.get("floor"))
    label, day = when(u.get("available"))
    free = str(get(u, "rent", "free_months") or "")
    desk = desk_kind(am)
    wash = laundry_kind(am)
    all_in, sqft = num(u.get("all_in")), num(u.get("sqft"))
    built = num(am.get("year_built"))
    questions = u.get("tour_questions")
    dog = u.get("dog") or {}
    limit = str(dog.get("weight_limit_lb") or "").strip().lower()
    sure = u.get("floor_basis") in ("confirmed", "stated")
    margin = num(get(u, "cost_check", "cap_margin"))
    return {
        "id": u["id"], "hood": u.get("hood_id"), "building": u.get("building_id") or u["id"],
        "beds": "studio" if u.get("beds") == 0 else "1-bedroom" if u.get("beds") == 1 else None,
        "all_in": all_in, "sqft": sqft, "rent": rent_asked(u),
        "per_sqft": all_in / sqft if all_in and sqft else None,
        "floor": int(floor) if floor and floor >= 2 else None,
        "floor_sure": sure,
        "margin": margin,
        "parking": park, "park_kind": kind, "park_fee": fee, "park_included": included,
        "pool": bool(am.get("pool")), "gym": am.get("gym") == "yes",
        # the front door: "doorman" only where the doorman amenity itself is set (desk_kind); a concierge is a concierge
        "desk": desk,
        "doorman": "24-hour" if desk in ("doorman24", "attended24") else "yes" if desk == "doorman" else None,
        "laundry": wash is not None, "laundry_wd": wash == "wd", "laundry_mode": laundry_mode(am),
        "garage_mixed": garage_mixed(u),
        "lounge": am.get("lounge_or_coworking") == "yes",
        "built": int(built) if built else None,
        "dog_amenity": dog_amenity(u),
        "dog_park": get(u, "moments", "wake", "dog_park"), "dog_park_m": num(get(u, "moments", "wake", "dog_park_m")),
        "park": get(u, "moments", "wake", "park"), "park_walk": num(get(u, "moments", "wake", "park_walk_min")),
        "restaurants": num(get(u, "moments", "after", "restaurants_800m")),
        "station": get(u, "moments", "sat", "train_station"), "station_m": num(get(u, "moments", "sat", "train_station_m")),
        "station_kind": get(u, "moments", "sat", "train_station_kind"),
        "market": get(u, "moments", "work", "supermarket"), "market_m": num(get(u, "moments", "work", "supermarket_m")),
        "avail": label, "avail_date": day,
        "open_questions": len(questions) if isinstance(questions, list) else None,
        "free_months": int(free) if free in ("1", "2", "3") else None,
        "free_up_to": bool(get(u, "rent", "offer_up_to")) or bool(re.search(r"\bup to\b", str(get(u, "rent", "offer_text") or ""), re.I)),
        "free_text": get(u, "rent", "free_text"),
        "rank": num(get(u, "scores", "hood_rank")),
        "no_weight_limit": limit == "no limit",
        "weight_limit": num(limit),
        "small_only": bool(dog.get("size_note")) and "small" in str(dog.get("size_note")).lower() and not limit,
        "dog_allowed": str(dog.get("allowed") or "").lower() == "yes",
        "dog_open": dog_open(u),
        "pet_rent_known": dog.get("pet_rent") is not None,
        "elevator_open": bool(get(u, "confirm", "asterisk")) and get(u, "confirm", "what") in ("elevator", "floor and elevator"),
        # owner, 2026-11-17: an apartment one flight up (floor 2) needs no elevator; on such an apartment the building's
        # elevator is never stated as a reason to like it (it may be in doubt)
        "walkup": get(u, "elevator", "walkup_floor_2") is True,
        "elevator_sure": get(u, "elevator", "value") == "yes" and not get(u, "elevator", "listing_site_only") and get(u, "elevator", "walkup_floor_2") is not True,
        "unknown": list(u.get("all_in_unknown") or []),
        "disclosures": disclosed(u),
    }


def price_words(f):
    """-> (price, gap): 'about $2,780' style figures for a sentence. `gap` says where the price sits against her
    limit, from the same rounded price, so the two figures in one sentence always add up."""
    if not f["all_in"]:
        return None, None
    shown = round10(f["all_in"])
    left = CAP - shown if f["margin"] is not None and abs((CAP - f["all_in"]) - f["margin"]) < 1 else \
        round10(f["margin"]) if f["margin"] is not None else None
    if left is None:
        gap = None
    elif left < 10:
        gap = f"at your {usd(CAP)} limit"
    else:
        gap = f"about {usd(left)} under your {usd(CAP)} limit"
    return f"${shown:,}", gap


def only(f, peers, test):
    return len(peers) >= 2 and test(f) and not any(test(p) for p in peers if p["id"] != f["id"])


def extreme(f, peers, key, best=max):
    """True when this one alone holds the best value of `key` among its peers (the apartments of its building, or the
    buildings of its neighborhood). Every peer must publish the value, so "the largest in the building" is simply true."""
    vals = [p[key] for p in peers if p[key] is not None]
    if f[key] is None or len(vals) < 2 or len(vals) < len(peers):
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
# Hand-written and plain. A condition is offered only when its fact is true; {fields} are filled from the data.

# LEADS[condition] = (angle, [sentences]): what sets THIS apartment apart inside its building, or its own most useful
# fact. {n} is the number of apartments listed in the building; {limit} is her monthly limit.
LEADS = {
    "cheapest": ("price", [
        "This is the {low}-priced of the {n} apartments listed in this building.",
        "Of the {n} apartments listed in this building, this apartment costs {least}.",
        "No other apartment listed in this building costs less than this apartment."]),
    "biggest": ("size", [
        "This is the {big} of the {n} apartments listed in this building.",
        "Of the {n} apartments listed in this building, this apartment has {most} space.",
        "No other apartment listed in this building is as large as this apartment."]),
    "value": ("value", [
        "Of the {n} apartments listed in this building, this apartment gives you {most} space for the price.",
        "You get more space for the price here than in any other apartment listed in this building."]),
    "highest": ("floor", [
        "This is the {high} of the {n} apartments listed in this building, on floor {floor}.",
        "On floor {floor}, this apartment is higher up than any other listed in this building."]),
    "fewest_questions": ("clean", [
        "This apartment has fewer things left to confirm than any other listed in this building.",
        "Of the {n} apartments listed in this building, this apartment leaves the least to ask about."]),
    "soonest_now": ("date", [
        "Of the {n} apartments listed in this building, only this apartment is available now.",
        "This is the only apartment listed in this building that is available now."]),
    "soonest_date": ("date", [
        "This apartment is available on {date}, earlier than any other listed in this building.",
        "Of the {n} apartments listed in this building, this apartment is available earliest, on {date}."]),
    "big": ("size", [
        "This is a large apartment, about {sqft} square feet, which helps when you work from home.",
        "At about {sqft} square feet, this apartment has room for a desk, a sofa and a dog."]),
    "margin": ("price", [
        "This apartment costs about {price} a month with utilities and fees, which is {gap}.",
        "At about {price} a month with utilities and fees, this apartment is {gap}.",
        "You would pay about {price} a month with utilities and fees, which is {gap}."]),
    "high_floor": ("floor", [
        "This apartment is high up, on floor {floor}.",
        "This apartment is on floor {floor}, well above the street."]),
    "concession": ("offer", [
        "The listing offers {free} free.",
        "The listing advertises {free} of free rent.",
        "A special offer of {free} free comes with this listing."]),
    "one_bed": ("layout", [
        "This is a 1-bedroom, so your desk does not have to be in the room where you sleep.",
        "This is a 1-bedroom, with the bedroom separate from the room you would work in.",
        "This is a 1-bedroom, so work can stay out of the bedroom."]),
    "studio": ("layout", [
        "This is a studio, so you would work and sleep in the same room.",
        "This is a studio, with the bed, the desk and the sofa in the same room.",
        "This is a studio, so plan where the desk would go."]),
    "size": ("size", [
        "This apartment is about {sqft} square feet.",
        "The listing puts this apartment at about {sqft} square feet.",
        "You would have about {sqft} square feet here."]),
    "walkup": ("floor", [                                   # owner, 2026-11-17: floor 2 stated, no elevator needed
        "This apartment is on floor {floor}, a single flight of stairs up, so you do not need an elevator.",
        "The listing puts this apartment on floor {floor}, a single flight up, so no elevator is needed."]),
    "floor": ("floor", [
        "This apartment is on floor {floor}.",
        "The listing puts this apartment on floor {floor}, above the ground floor."]),
    "avail_date": ("date", [
        "This apartment is available on {date}.",
        "The listing gives {date} as the move-in date.",
        "You could move in on {date}."]),
    "avail_now": ("date", [
        "This apartment is available now.",
        "The listing says this apartment is available now.",
        "You could move in right away, because the listing says available now."]),
    "basic": ("cost", [
        "{This_kind} costs about {price} a month with utilities and fees.",
        "The cost of {this_kind} is about {price} a month with utilities and fees."]),
    "basic_no_price": ("cost_open", [
        "The full monthly cost of {this_kind} is not known yet."]),
    "type": ("type", [
        "{Type_sentence}"]),
    "plain": ("plain", [
        "The listing gives few details about this apartment."]),
}
PEER_CONDITIONS = {"cheapest", "biggest", "value", "highest", "fewest_questions", "soonest_now", "soonest_date"}

# The second sentence: the price and the size, whichever the lead has not already given. Plain facts in fixed words;
# these are not varied beyond the three orders below.
SECOND = {
    "price_size": ["It costs about {price} a month with utilities and fees, and is about {sqft} square feet.",
                   "It is about {sqft} square feet and costs about {price} a month with utilities and fees.",
                   "The cost is about {price} a month with utilities and fees, for about {sqft} square feet."],
    "price": ["It costs about {price} a month with utilities and fees.",
              "The cost is about {price} a month with utilities and fees."],
    "size": ["It is about {sqft} square feet."],
}
# The same sentence where the rent the listing asks is plain (rent_asked): both of the page's prices, each named.
SECOND_RENT = {
    "price_size": ["The rent is {rent}, about {price} a month with utilities and fees, for about {sqft} square feet.",
                   "It is about {sqft} square feet, and the rent is {rent}, about {price} a month with utilities and fees.",
                   "Rent is {rent}; about {price} a month with utilities and fees, for about {sqft} square feet."],
    "price": ["The rent is {rent}, about {price} a month with utilities and fees.",
              "Rent is {rent}; about {price} a month with utilities and fees."],
}

# CATCHES[kind] = [texts]: one or two short sentences, the one thing to ask or watch. A kind that states a reason is
# used only where the apartment's own fields give that reason (CATCH_BASIS).
CATCHES = {
    "confirm:live check": [
        "The price and the move-in date were read from the listing once. Call to confirm both.",
        "Call to confirm that this apartment is still available at this price.",
        "Before you plan around this apartment, ask the leasing office to confirm the rent and the move-in date. Both "
        "come from a single reading of the listing.",
        "Ask the leasing office whether this apartment is still available and what the rent is today. The listing was "
        "read only once.",
        "The rent and the move-in date come from a single reading of the listing, so confirm both by phone.",
        "Before you tour, confirm the price and the move-in date by phone."],
    "confirm:elevator named": [
        "The listing names an elevator for the property and does not say it serves this apartment. Ask before you tour.",
        "Ask whether an elevator serves this apartment's building and floor. The listing names an elevator for the "
        "property only.",
        "An elevator is listed for the property, and it is not confirmed for this apartment. Ask before you tour."],
    "confirm:elevator": [
        "It is not confirmed that this building has an elevator. Ask before you tour.",
        "Ask whether the building has an elevator that serves this apartment. That is not confirmed.",
        "An elevator is not confirmed for this apartment, so ask before you tour."],
    "confirm:listing stale": [
        "This listing has not been updated in a long time. Ask whether the apartment is still available, and at what price.",
        "The listing is old, so the apartment could already be rented. Ask whether it is still available, and at what price.",
        "Ask whether this apartment is still available, and at what price. The listing has not been updated in a long time."],
    "confirm:listing one site": [
        "This apartment appears on a listing site and not on the building's own site. Ask the office whether it is "
        "really available.",
        "Ask the office whether this apartment is really available. It is on a listing site and not on the building's "
        "own site."],
    "confirm:listing which building": [
        "It is not clear which building this apartment is in. Ask the office before you tour.",
        "Ask the office which building this apartment is in. The listing does not make that clear."],
    "confirm:listing lease price": [
        "The price shown is for a longer lease. Ask for the price on a 12-month lease before you compare.",
        "Ask for the price on a 12-month lease. The price shown is for a longer lease."],
    "confirm:listing permit": [                             # N16: say the reason, which the open item itself gives
        "A review claims apartments here were advertised without an occupancy permit, and that is not confirmed. Ask to "
        "see the certificate of occupancy.",
        "Ask to see the building's certificate of occupancy. A review claims apartments here were advertised without "
        "a permit, and that is not confirmed."],
    "confirm:listing": [
        "Part of this listing could not be confirmed. Ask whether the apartment is still available, and at what price.",
        "Ask whether this apartment is still available, and at what price. The listing could not be fully confirmed."],
    "confirm:availability plan": [
        "This price is for a floor plan, with no specific apartment named. Ask which apartment is available, on which "
        "floor, and from what date.",
        "The listing shows a floor plan and no apartment number. Ask which apartment you would get, its floor and its "
        "move-in date.",
        "Ask which apartment is available at this price, on which floor, and from what date. The listing names only a "
        "floor plan."],
    "confirm:availability": [
        "It is not confirmed that this apartment is available. Ask for an apartment number and a move-in date."],
    "confirm:eligibility income": [
        "This building may have an income limit for renters. Ask whether it applies to you before you tour.",
        "Ask before you tour whether an income limit applies to this apartment. The building may be income-restricted."],
    "confirm:eligibility age": [
        "A community at this address is for older residents only. Ask whether this apartment is open to renters of any age.",
        "Ask whether this apartment is open to renters of any age. A community at this address is for older residents only."],
    "confirm:eligibility": [
        "It is not confirmed that any renter can apply for this apartment. Ask the office before you tour."],
    "confirm:dogs conflict": [
        "Listing sites disagree about whether dogs are allowed here. Get the dog policy in writing before you tour.",
        "Get the dog policy in writing before you tour. The listings do not agree on whether dogs are allowed."],
    "confirm:dogs approval": [
        "The pet policy says pets are welcome upon approval, which is not a clear yes for a dog. Get a yes in writing.",
        "Get a yes for your dog in writing. The pet policy says only that pets are welcome upon approval."],
    "confirm:dogs case": [
        "Pets are considered case by case here, so a dog is not a sure yes. Get the answer in writing."],
    "confirm:dogs contact": [
        "The only pet policy in the listing says to contact the office. Ask whether dogs are allowed, and get the answer "
        "in writing.",
        "Ask whether dogs are allowed, and get the answer in writing. The listing's pet policy says only to contact the "
        "office."],
    "confirm:dogs small pets": [
        "The listing says small pets are allowed and does not name dogs. Ask whether a dog is allowed, and get the answer "
        "in writing."],
    "confirm:dogs no text": [
        "Dogs appear only in a listing site's pet details, with no policy text. Ask the office for the dog policy in "
        "writing."],
    "confirm:dogs open": [
        "It is not confirmed that dogs are allowed here. Get the dog policy in writing before you tour.",
        "Ask the office whether dogs are allowed, and get the answer in writing. The listing does not settle it."],
    "confirm:other": [
        "Part of this listing could not be confirmed. Call the leasing office before you tour.",
        "Call the leasing office before you tour. Part of this listing could not be confirmed."],
    "rent:net_effective": [
        "The price shown includes a special offer. Ask what a normal month costs.",
        "The price shown is lower than a normal month because of a special offer. Ask for the normal monthly rent.",
        "A special offer lowers the price shown. Ask what the rent is in a month without it."],
    "rent:needs_call": [
        "There is a special offer, and the listing does not say whether the price shown already includes it. Ask what a "
        "normal month costs.",
        "The listing has a special offer. Ask whether the price shown is the normal monthly rent.",
        "Ask what a normal month costs. The listing has a special offer and does not say how it changes the rent.",
        "A special offer comes with this listing, and its effect on the rent is not stated. Ask for the normal monthly rent.",
        "Ask whether the price shown already includes the special offer. The listing does not say."],
    "costs:could_pass": [
        "{Names} {are} not published, so this price leaves {them} out. With {them} added, the monthly cost could pass "
        "your {limit} limit.",
        "This price does not include {names}. Ask for the missing {amounts}, because the total could pass your {limit} "
        "limit.",
        "Ask for {names}, which the listing does not publish. With {them} added, the monthly cost could pass your "
        "{limit} limit."],
    "lease_term": [
        "The price shown is for a {months}-month lease. Ask what a 12-month lease costs.",
        "This rent goes with a {months}-month lease, and the 12-month price is not published. Ask for it.",
        "Ask what the rent is on a 12-month lease. The price shown is for {months} months."],
    "dog_weight": [
        "The listing says a dog weight limit applies and gives no number. Ask for the limit in pounds.",
        "Ask for the dog weight limit in pounds. The listing says there is a limit and does not give it."],
    # conditions the renter must meet or know (independent check 4, D8): the figure itself is on the disclosure
    "conditions:income": [
        "The listing sets an income requirement: {income}. Check that you meet it, or ask whether a guarantor counts.",
        "This apartment has an income requirement: {income}. Ask whether a guarantor counts."],
    "conditions:income_plain": [
        "The listing sets an income requirement. Check that you meet it, or ask whether a guarantor counts."],
    "conditions:credit": [
        "The listing asks for a credit score of {credit}. Check yours against it before you apply.",
        "A credit score of {credit} is required here. Check yours before you apply."],
    "conditions:credit_plain": [
        "The listing asks for a minimum credit score. Ask what score the application needs."],
    "conditions:furnished": [
        "The listing says this apartment is furnished. Ask whether the furniture is optional and whether the lease is a "
        "standard 12-month lease.",
        "This apartment is listed as furnished. Ask whether you can rent it without the furniture, on a 12-month lease."],
    "condo": [
        "This apartment is in a condominium and is rented by its owner. Ask about the building's rules for renters, "
        "including pets.",
        "The owner rents out this apartment in a condominium building. Ask what the building requires of renters, "
        "including its pet rules."],
    "floor:unpublished": [
        "The listing does not give the floor. Confirm that the apartment is above the ground floor.",
        "Ask which floor this apartment is on. The listing does not say, and you want to be above the ground floor.",
        "The floor is not published, so confirm that it is above the ground floor before you tour."],
    "floor:walkup inferred": [                             # owner, 2026-11-17: floor 2 read from the number, no elevator established
        "The apartment number suggests floor {floor}, a single flight up. No elevator is confirmed here, so confirm the floor.",
        "Ask the office to confirm the floor is {floor}, a single flight up. No elevator is confirmed here."],
    "confirm:floor and elevator": [                        # owner, 2026-11-17: one open item, parsers.floor_elevator_rule
        "The listing gives no floor and does not say there is an elevator. Ask both: without an elevator, only the floor just "
        "above the ground floor works.",
        "Ask which floor this apartment is on and whether the building has an elevator. Without an elevator, only the floor "
        "just above the ground floor works.",
        # the same fact in other words, so that no wording is on more than SHARE of the page (2026-11-17, trawl 2: this
        # catch applies to more than half of the apartments shown)
        "The floor and the elevator are both left out of the listing. Ask about each: with no elevator, only the floor "
        "just above the ground floor works.",
        "Confirm the floor and whether there is an elevator. The listing gives neither, and without an elevator only the "
        "floor just above the ground floor works.",
        "This listing names no floor and no elevator. Ask about both, since without an elevator only the floor just above "
        "the ground floor works.",
        "Before you tour, ask which floor this is and whether an elevator serves it. Without an elevator, only the floor "
        "just above the ground floor works.",
        "The floor is not given, and no elevator is mentioned. Ask both questions: without an elevator, only the floor just "
        "above the ground floor works.",
        "Ask the office for the floor and whether there is an elevator. The listing says neither, and a walk-up works only "
        "on the floor just above the ground floor.",
        "No floor or elevator is listed for this apartment. Ask about both, because without an elevator only the floor just "
        "above the ground floor works.",
        "Find out the floor and whether the building has an elevator. The listing says neither, and without an elevator "
        "only the floor just above the ground floor works."],
    "floor:inferred": [
        "The listing does not state the floor. The apartment number suggests floor {floor}, so confirm it.",
        "Floor {floor} is read from the apartment number, and the listing does not state it. Ask the office to confirm "
        "the floor.",
        "Ask the office to confirm the floor. The apartment number suggests floor {floor}, and the listing does not say."],
    "weak:space": [
        "At about {sqft} square feet, this is a small apartment for working from home with a dog.",
        "This apartment is about {sqft} square feet, which is small for a home office and a dog."],
    "weak:cost": [
        "At about {price} a month with utilities and fees, this apartment is {gap}.",
        "This apartment costs about {price} a month with utilities and fees, which is {gap}."],
    "none": [
        "The listing leaves no open question. On the tour, check the light, the noise and the hallways.",
        "Nothing in the listing needs a call before the tour. Use the tour to check the light and the noise."],
}

# SUBS[section] = [(case, [lines])]: one short line (at most 14 words, no numbers) under a section headline.
SUBS = {
    "cost": [
        ("net_effective", [
            "The price shown includes a special offer, so a normal month costs more.",
            "A special offer lowers this price, so ask what a normal month costs.",
            "Ask for the normal monthly rent, because this price includes a special offer."]),
        ("ambiguous_rent", [
            "The listing has a special offer, so ask what a normal month costs.",
            "Ask whether the price shown already includes the special offer.",
            "A special offer applies, so confirm the normal monthly rent.",
            "Ask what the rent is after the special offer ends.",
            "The special offer is not explained, so ask for the normal monthly rent.",
            "Confirm with the office how the special offer changes the rent."]),
        ("tight", [
            "This is almost at your limit, so ask about every fee.",
            "Very little room is left under your limit.",
            "Any added fee would put this over your limit."]),
        ("unpublished", [
            "Some fees are not published, so the real cost could be higher.",
            "Ask for the fees that the listing does not publish.",
            "This total leaves out fees that the listing does not publish.",
            "The listing leaves out some fees, so ask for the full monthly cost.",
            "The listing does not publish every fee, so ask for them all.",
            "Ask the office for any fee the listing leaves out.",
            "Some charges are not listed, so the monthly cost could rise.",
            "Get every fee in writing, because the listing does not publish them all.",
            "Fees are missing from this listing, so ask what a month really costs."]),
        ("roomy", [
            "This is well under your limit.",
            "Well under your limit, so an added fee would still fit.",
            "This leaves room in your budget each month."]),
    ],
    "parking": [
        ("unknown", [
            "The listing does not mention parking, so ask before you tour.",
            "Ask whether the building has parking and what a space costs.",
            "Parking is not mentioned, so ask where you would park."]),
        ("included", [
            "A parking space is included, so the car adds nothing to the monthly cost.",
            "Parking is included in the rent.",
            "You would not pay extra to park here."]),
        ("included_lot", [
            "You would park free in the building's open lot.",
            "A space in the open lot is included in the rent.",
            "Parking in the open lot is free."]),
        ("included_lot_garage", [
            "A free open lot; garage spaces cost extra.",
            "Parking in the open lot is free, and a garage space costs extra.",
            "The open lot is included, and a garage space is an added cost."]),
        ("included_off_street", [
            "Free off-street parking.",
            "Off-street parking is included in the rent.",
            "You would not pay extra for off-street parking."]),
        ("included_assigned", [
            "An assigned space is included, and the listing does not say where.",
            "A space is assigned to you at no charge, so ask where it is.",
            "Ask whether the included assigned space is in a garage or a lot."]),
        ("included_unspecified", [
            "A parking space is included; the listing does not say what kind.",
            "Ask what kind of parking space the rent includes.",
            "A parking space comes with the rent, and its kind is not stated."]),
        ("garage_priced", [
            "You would park indoors, and the price is published.",
            "The garage fee is published, so you can budget for it now.",
            "Garage parking, with the monthly fee published."]),
        ("garage_unpriced", [
            "You would park indoors, so ask what the garage costs each month.",
            "There is a garage, and the listing does not give its price.",
            "Ask for the monthly garage fee before you compare costs.",
            "The garage fee is not published, so ask for it.",
            "A garage is listed without a price, so ask what it costs.",
            "Get the garage fee in writing before you apply."]),
        ("covered_priced", [
            "Covered parking, with the monthly fee published.",
            "Your car would be under cover, and the price is published.",
            "The covered parking fee is published, so you can budget for it."]),
        ("covered_unpriced", [
            "Covered parking is offered, so ask what it costs each month.",
            "The covered parking fee is not published, so ask for it.",
            "Ask for the monthly fee for covered parking."]),
        ("lot_priced", [
            "You would park in the building's lot, and the price is published.",
            "The lot fee is published, so you can budget for it.",
            "Parking is in the building's lot, with the fee published."]),
        ("lot_unpriced", [
            "You would park in the building's lot, so ask what a space costs.",
            "The lot fee is not published, so ask for it.",
            "Ask what a space in the building's lot costs each month."]),
        ("off_street_priced", [
            "Off-street parking is offered, and the fee is published."]),
        ("off_street_unpriced", [
            "Off-street parking is offered, so ask what it costs each month."]),
        ("assigned_priced", [
            "The assigned space has a published fee, so ask where the space is."]),
        ("assigned_unpriced", [
            "An assigned space is listed, so ask where it is and what it costs.",
            "Ask whether the assigned space is in a garage or a lot.",
            "The listing names an assigned space without a kind or a price."]),
        ("offsite_priced", [
            "Parking is off-site, not at the building, and the fee is published.",
            "There is no parking at the building, and the off-site fee is published.",
            "You would park off-site, at a published monthly fee."]),
        ("offsite_unpriced", [
            "Parking is off-site, so ask where it is and what it costs."]),
        ("unspecified_priced", [
            "A parking fee is published without the kind of space, so ask."]),
        ("unspecified_unpriced", [
            "The listing mentions parking without saying what kind: ask.",
            "Ask what kind of parking the building has and what it costs.",
            "Parking is mentioned without a type or a price, so ask."]),
        ("street", [
            "The only parking named is on the street, so ask about overnight rules.",
            "Ask where you would park overnight, because the listing names street parking only."]),
    ],
    "dog": [
        ("conflicting", [
            "Listing sites disagree about dogs, so get the policy in writing.",
            "The listings do not agree about dogs, so ask the office.",
            "Get a written yes for a dog, because the listings disagree."]),
        ("unsettled", [
            "It is not confirmed that dogs are allowed, so ask before you tour.",
            "Get the dog policy in writing before you tour.",
            "Ask the office to confirm that a dog is allowed."]),
        ("small_only", [
            "The listing says small dogs and gives no weight, so ask for the limit.",
            "Ask what weight counts as a small dog here.",
            "Small dogs are allowed, and the weight limit is not published.",
            "Ask for the dog weight limit in pounds before you apply."]),
        ("weight_unpublished", [
            "A dog weight limit applies, and the number is not published.",
            "Ask for the dog weight limit in pounds."]),
        ("weight_limit", [
            "Check the weight limit against the adult size of your dog.",
            "Dogs are allowed up to a weight limit, so check it against your dog.",
            "The weight limit applies to the adult dog, so plan for that."]),
        ("onsite", [
            "The building has its own dog area for quick trips outside.",
            "A dog area on the property makes late walks short.",
            "You could take the dog out without leaving the property."]),
        ("near_run", [
            "A dog park is within walking distance.",
            "You could walk the dog to a dog park from here.",
            "The nearest dog park is close enough to use every day."]),
        ("pet_rent_unknown", [
            "Pet rent is not published, so ask what a dog adds each month.",
            "Ask for the pet rent and any pet fee.",
            "The cost of a dog here is not published, so ask.",
            "Ask the office for the monthly pet rent."]),
    ],
    "building": [
        ("front_desk", [
            "The front desk is staffed day and night, which helps with packages.",
            "Someone is at the front desk at all hours.",
            "A staffed front desk can receive your packages."]),
        ("doorman", [
            "The building has a doorman.",
            "A doorman is at the front door.",
            "A doorman can receive deliveries when you are out.",
            "There is a doorman, which helps with packages."]),
        ("concierge24", [
            "The building has a concierge at all hours.",
            "A concierge is listed as available day and night.",
            "The listing names a concierge at all hours."]),
        ("concierge", [
            "The building has a concierge desk.",
            "A concierge desk is listed for the building.",
            "The listing names a concierge desk."]),
        ("attended", [
            "The lobby is attended.",
            "The listing says the lobby is attended.",
            "Someone staffs the lobby."]),
        ("pool_laundry", [
            "A pool, and a washer and dryer in the apartment.",
            "You get a pool and your own washer and dryer.",
            "Laundry is in the apartment, and the building has a pool.",
            "The building has a pool, and laundry is in the apartment."]),
        ("laundry_listed_wd", [
            "The listing shows a washer and dryer in the apartment.",
            "The listing's appliance list names a washer and dryer.",
            "A washer and dryer are on the listing's appliance list: check on the tour."]),
        ("laundry_listed_washer", [
            "The listing shows a washer in the apartment and names no dryer.",
            "The listing's appliance list names a washer and no dryer.",
            "A washer is on the listing's appliance list, so ask about a dryer."]),
        ("laundry_washer", [
            "A washer is in the apartment, and no dryer is named."]),
        ("laundry_listed", [
            "The listing shows laundry in the apartment."]),
        ("laundry", [
            "The washer and dryer are inside the apartment.",
            "You would do laundry in your own apartment.",
            "Laundry is inside the apartment.",
            "No shared laundry room, because the washer and dryer are in the apartment.",
            "Your own washer and dryer come with the apartment."]),
        ("pool", [
            "The building has a pool.",
            "A pool is on the property.",
            "Residents can use the pool."]),
        ("gym", [
            "The building has a gym.",
            "A gym is on the property.",
            "You could exercise without leaving the building."]),
    ],
}

# BUILDING[condition] = (angle, 'inside' | 'around', [sentences]): the building's most distinctive feature, and the
# most useful thing near it. {n} here is the number of buildings listed in the neighborhood.
BUILDING = {
    "only_pool": ("pool", "inside", [
        "This is the only building of the {n} listed in this neighborhood with a pool.",
        "No other building listed in this neighborhood has a pool."]),
    "only_garage": ("parking", "inside", [
        "This is the only building of the {n} listed in this neighborhood with a garage{gtail}.",
        "The only garage among the {n} buildings listed in this neighborhood is here{gtail}."]),
    "only_doorman": ("doorman", "inside", [
        "This is the only building of the {n} listed in this neighborhood with a doorman.",
        "No other building listed in this neighborhood has a doorman."]),
    "only_laundry": ("laundry", "inside", [
        "This is the only building of the {n} listed in this neighborhood with a washer and dryer in the apartment.",
        "No other building listed in this neighborhood has a washer and dryer in the apartment.",
        "This is the only building of the {n} listed in this neighborhood with laundry in the apartment.",
        "No other building listed in this neighborhood has laundry in the apartment."]),
    "only_dogspot": ("dog", "inside", [
        "This is the only building of the {n} listed in this neighborhood with its own {dogthing}.",
        "No other building listed in this neighborhood has its own {dogthing}."]),
    "parking_included": ("parking", "inside", [             # a garage or covered space, named as what it is
        "{Incl} is included in the rent.",
        "The rent includes {incl}.",
        "You would not pay extra to park here, because {incl} is included in the rent."]),
    "lot_included": ("parking", "inside", [
        "{Lot_space} is included in the rent{extra}.",
        "The rent includes {lot_space}{extra}."]),
    "off_street_included": ("parking", "inside", [
        "Off-street parking is free{extra}.",
        "Free off-street parking comes with the apartment{extra}."]),
    "assigned_included": ("parking", "inside", [
        "An assigned space is included; the listing does not say whether it is a garage or a lot."]),
    "unspecified_included": ("parking", "inside", [
        "A parking space is included; the listing does not say what kind."]),
    "offsite": ("parking", "inside", [
        "Parking is {where}, {fee} a month."]),
    "offsite_unpriced": ("parking", "inside", [
        "Parking is {where}, and the fee is not published."]),
    "off_street": ("parking", "inside", [
        "The building has off-street parking{ptail}{extra}."]),
    "assigned": ("parking", "inside", [
        "The listing names an assigned parking space and does not say whether it is a garage or a lot."]),
    "dog_onsite": ("dog", "inside", [
        "The building has its own {dogthing}.",
        "There is a {dogthing} on the property.",
        "Residents have a {dogthing} on the property."]),
    "garage_priced": ("parking", "inside", [
        "The building has a garage, and a space costs {fee} a month.",
        "Garage parking costs {fee} a month.",
        "You would park in the building's garage for {fee} a month."]),
    "garage_fee_asked": ("parking", "inside", [             # used when the warning beside it says the fee is not published
        "The building has a garage.",
        "You would park in the building's garage.",
        "There is a garage for your car."]),
    "garage_unpriced": ("parking", "inside", [
        "The building has a garage, and the fee is not published.",
        "There is a garage, and the listing does not publish what it costs.",
        "You would park in the building's garage, and the fee is not published.",
        "Garage parking is offered, and the monthly fee is not published.",
        "The building has garage parking, and the listing does not publish the fee.",
        "A garage is listed for this building, and its fee is not published."]),
    "pool": ("pool", "inside", [
        "The building has a pool.",
        "There is a pool on the property.",
        "Residents can use the building's pool."]),
    "front_desk": ("doorman", "inside", [
        "The front desk is staffed 24 hours a day.",
        "Someone is at the front desk 24 hours a day."]),
    "doorman": ("doorman", "inside", [
        "The building has a doorman.",
        "A doorman is at the front door.",
        "There is a doorman, which helps with packages and deliveries."]),
    "concierge24": ("doorman", "inside", [
        "The building has a concierge 24 hours a day.",
        "The listing names a concierge, available 24 hours a day."]),
    "concierge": ("doorman", "inside", [
        "The building has a concierge desk.",
        "A concierge desk is listed for the building."]),
    "attended": ("doorman", "inside", [
        "The lobby is attended.",
        "The listing says the lobby is attended."]),
    "laundry_listed_wd": ("laundry", "inside", [
        "The listing shows a washer and dryer in the apartment.",
        "The listing's appliance list names a washer and dryer."]),
    "laundry_listed_washer": ("laundry", "inside", [
        "The listing shows a washer in the apartment and names no dryer."]),
    "laundry_washer": ("laundry", "inside", [
        "A washer is in the apartment, and the listing names no dryer."]),
    "laundry_listed": ("laundry", "inside", [
        "The listing shows laundry in the apartment."]),
    "laundry": ("laundry", "inside", [
        "Laundry is inside the apartment.",
        "You would do laundry inside the apartment.",
        "The apartment has its own washer and dryer.",
        "A washer and dryer are inside the apartment.",
        "You would do laundry inside the apartment, with your own washer and dryer."]),
    "covered": ("parking", "inside", [
        "The building has covered parking{ptail}.",
        "Covered parking is offered{ptail}."]),
    "dog_no_limit": ("dog", "inside", [
        "Dogs are allowed with no weight limit.",
        "The dog policy sets no weight limit."]),
    "newer": ("newer", "inside", [
        "This is a newer building, built in {built}.",
        "The building is recent, built in {built}."]),
    "lot": ("parking", "inside", [
        "The building has its own parking lot{ptail}{extra}.",
        "You would park in the building's lot{ptail}{extra}."]),
    "lounge": ("work", "inside", [
        "The building has a lounge or coworking room, which is useful when you work from home.",
        "There is a lounge or coworking room for days when you want to work outside the apartment."]),
    "gym": ("gym", "inside", [
        "The building has a gym.",
        "There is a gym in the building."]),
    "dated": ("newer", "inside", [
        "The building was built in {built}.",
        "The building dates from {built}."]),
    "street_parking": ("parking", "inside", [
        "The only parking named in the listing is on the street."]),
    "unspecified_parking": ("parking", "inside", [
        "The listing mentions parking without saying what kind."]),
    "plain": ("plain", "inside", [
        "The listing gives few details about the building itself.",
        "Few details about the building itself are published.",
        "The listing says little about the building itself.",
        "Little is published about the building itself.",
        "The building's own details are mostly missing from the listing.",
        "The listing describes the apartment more than the building.",
        "Not much about the building is in the listing.",
        "The building is described only briefly in the listing."]),
    "closest_run": ("dog", "around", [
        "{Dogpark} is {dogpark_mi} miles away, closer than from any other building listed in this neighborhood.",
        "Of the {n} buildings listed in this neighborhood, this is the closest to a dog park, {dogpark_mi} miles away."]),
    "closest_park": ("green", "around", [
        "No building listed in this neighborhood has a shorter walk to a park, about {park_mins} to {park}.",
        "Of the {n} buildings listed in this neighborhood, this is the closest to a park, about {park_mins} to {park}."]),
    "closest_run_also": ("dog", "around", [                 # after a first sentence that already compares the buildings
        "This building is also the closest to a dog park, {dogpark_mi} miles away."]),
    "closest_park_also": ("green", "around", [
        "This building also has the shortest walk to a park, about {park_mins} to {park}."]),
    "dogpark_near": ("dog", "around", [
        "{Dogpark} is {dogpark_mi} miles away.",
        "It is {dogpark_mi} miles to {dogpark_end}."]),
    "food": ("food", "around", [
        "About {rest} restaurants are within a {w10}.",
        "You could walk to dinner, with about {rest} restaurants within a {w10}.",
        "There are about {rest} restaurants within a {w10}."]),
    "park": ("green", "around", [
        "{park} is about {park_mins} away on foot.",
        "It is about {park_mins} on foot to {park}.",
        "The walk to {park} takes about {park_mins}.",
        "You could walk to {park} in about {park_mins}."]),
    "station": ("train", "around", [
        "{Station} is {station_mi} miles away.",
        "It is {station_mi} miles to {station}."]),
    "errands": ("errands", "around", [
        "A supermarket, {market}, is {market_mi} miles away.",
        "The nearest supermarket, {market}, is {market_mi} miles away.",
        "It is {market_mi} miles to the nearest supermarket, {market}."]),
    "food_few": ("food", "around", [
        "{Rest_few} within a {w10}.",
        "{Rest_few} within a {w10} of the building.",
        "{Rest_few} within a {w10} of the door."]),
    "market_far": ("errands", "around", [
        "The nearest supermarket, {market}, is {market_mi} miles away."]),
}
BUILDING_PEER_CONDITIONS = {"only_pool", "only_garage", "only_doorman", "only_laundry", "only_dogspot", "closest_run",
                            "closest_park", "closest_run_also", "closest_park_also"}               # building against the other buildings of its neighborhood

# The icon points of "About the building": POINTS[key] = (icon, topic, text). Plain facts, one wording each, the same
# words wherever the fact is the same (as on the neighborhood pages). The warning is the main thing to ask.
POINTS = {
    "parking": ("parking", "parking", "{parking_point}"),   # parking_point(): exactly what the structured fields carry
    "dog_onsite": ("dog", "dogspot", "The building has its own {dogthing}."),
    "dog_no_limit": ("dog", "dog", "Dogs are allowed, with no weight limit."),
    "dog_limit": ("dog", "dog", "Dogs are allowed up to {lb} pounds."),
    "dog_small": ("dog", "dog", "Small dogs are allowed, and the weight limit is not published."),
    "dog_ok": ("dog", "dog", "Dogs are allowed."),
    "pool": ("pool", "pool", "The building has a pool."),
    "laundry": ("laundry", "laundry", "Washer and dryer in the apartment."),
    "laundry_plain": ("laundry", "laundry", "Laundry in the apartment."),
    "laundry_listed_wd": ("laundry", "laundry", "The listing shows a washer and dryer in the apartment."),
    "laundry_listed_washer": ("laundry", "laundry", "The listing shows a washer in the apartment, with no dryer named."),
    "laundry_washer": ("laundry", "laundry", "A washer in the apartment, with no dryer named."),
    "laundry_listed": ("laundry", "laundry", "The listing shows laundry in the apartment."),
    "front_desk": ("key", "doorman", "The front desk is staffed 24 hours a day."),
    "doorman": ("key", "doorman", "The building has a doorman."),
    "concierge24": ("key", "doorman", "A concierge is available 24 hours a day."),
    "concierge": ("key", "doorman", "The building has a concierge desk."),
    "attended": ("key", "doorman", "The lobby is attended."),
    "gym": ("heart", "gym", "The building has a gym."),
    "lounge": ("coffee", "lounge", "The building has a lounge or coworking room."),
    "park": ("park", "park", "{park} is about {park_mins} away on foot."),
    "dogrun": ("dog", "dogrun", "{Dogpark} is {dogpark_mi} miles away."),
    "food": ("fork", "food", "{Rest_count} within a {w10}."),
    "train": ("train", "train", "{Station} is {station_mi} miles away."),
    "built": ("home", "built", "Built in {built}."),
    "elevator": ("home", "elevator", "The building has an elevator."),
    "units": ("home", "units", "{Apts_listed} in this building."),
}
WARNINGS = {                                           # key: (topic, text); the first that applies is used
    "dog_unsettled": ("dog", "It is not confirmed that dogs are allowed, so get a yes in writing."),
    "elevator_open": ("elevator", "An elevator is not confirmed for every apartment here, so ask before you tour."),
    "parking_unknown": ("parking", "The listing does not mention parking, so ask where you would park."),
    "parking_street": ("parking", "The only parking named is on the street, so ask about overnight rules."),
    "parking_kind": ("parking", "The listing mentions parking without saying what kind or what it costs: ask."),
    "parking_assigned": ("parking", "An assigned space is listed, with its kind and fee not published, so ask."),
    "parking_fee": ("parking", "The {parking} fee is not published, so ask what it costs each month."),
    "pet_rent": ("dogcost", "Pet rent is not published, so ask what a dog adds each month."),
    "fees": ("fees", "Building fees are not published, so ask what is added to the rent."),
    "weight": ("dog", "The listing says small dogs and gives no weight, so ask for the limit."),
    "overnight": ("street", "The town restricts overnight street parking, so get a parking space in writing."),
    "tour": ("tour", "On the tour, look at the hallways, the elevator and the mail room."),
    "tour_walkup": ("tour", "On the tour, look at the hallways, the stairs and the mail room."),
}
PARKING_NAMES = {"garage": "garage", "covered": "covered parking", "lot": "parking lot", "off_street": "off-street parking",
                 "offsite": "off-site parking", "assigned": "assigned parking", "unspecified": "parking"}
ANGLE_TOPIC = {"parking": "parking", "pool": "pool", "doorman": "doorman", "laundry": "laundry", "gym": "gym", "work": "lounge",
               "newer": "built", "food": "food", "train": "train", "green": "park"}   # a sentence's angle -> the point it replaces


# ------------------------------------------------------------------ the line (per apartment)

def lead_conditions(f, peers):
    """-> [(score, condition, values to fill, fields used)]: every condition whose fact is true for this apartment.
    `peers` are the apartments listed in the same building (this one included). Higher score = more distinctive."""
    n = len(peers)
    two = n == 2
    small = -20 if two else 0                         # "the cheaper of 2" is worth less than "the cheapest of 6"
    out = []

    def add(score, cond, vals=None, **used):
        out.append((score, cond, {"n": n, "limit": usd(CAP), **(vals or {})}, used))

    price, gap = price_words(f)
    sqft = about_sqft(f["sqft"]) if f["sqft"] else None
    # ---- against the other apartments listed in the same building
    if extreme(f, peers, "all_in", min):
        add(85 + small, "cheapest", {"low": "lower" if two else "lowest", "least": "less" if two else "the least"}, peers=n)
    if extreme(f, peers, "sqft", max):
        add(80 + small, "biggest", {"big": "larger" if two else "largest", "most": "more" if two else "the most"}, peers=n)
    if f["floor_sure"] and extreme(f, peers, "floor", max) and all(p["floor_sure"] for p in peers):
        add(70 + small, "highest", {"floor": f["floor"], "high": "higher" if two else "highest"}, peers=n, floor=f["floor"])
    if extreme(f, peers, "per_sqft", min):
        add(66 + small, "value", {"most": "more" if two else "the most"}, peers=n)
    s = soonest(f, peers)
    if s == "now":
        add(64 + small, "soonest_now", peers=n, available="now")
    elif s == "date":
        add(62 + small, "soonest_date", {"date": f["avail"]}, peers=n, available=f["avail"])
    if extreme(f, peers, "open_questions", min):
        add(58 + small, "fewest_questions", peers=n, open_questions=f["open_questions"])
    # ---- the apartment's own facts
    if f["sqft"] and f["sqft"] >= 850:
        add(52, "big", {"sqft": sqft}, sqft=f["sqft"])
    if f["margin"] is not None and f["margin"] >= 400 and price and gap:
        add(48, "margin", {"price": price, "gap": gap}, all_in=f["all_in"], cap_margin=f["margin"])
    if f["floor"] and f["floor"] >= 10 and f["floor_sure"]:
        add(46, "high_floor", {"floor": f["floor"]}, floor=f["floor"])
    if f["free_months"]:
        m = "month" if f["free_months"] == 1 else "months"
        # "up to 2 months free" on the page stays "up to" in the sentence (independent check 4, D20)
        # the page data's own phrase where it has one (rent.free_text: "up to 2 months"); else built from the count
        ft = str(f["free_text"] or "")
        phrase = ft if re.fullmatch(r"(?:up to )?[123] months?", ft) else f"{'up to ' if f['free_up_to'] else ''}{f['free_months']} {m}"
        add(40, "concession", {"free": phrase}, free_months=f["free_months"])
    if f["beds"] == "1-bedroom":
        add(36, "one_bed", beds=f["beds"])
    elif f["beds"] == "studio":
        add(36, "studio", beds=f["beds"])
    if f["sqft"] and f["sqft"] < 850:
        add(32, "size", {"sqft": sqft}, sqft=f["sqft"])
    if f["walkup"] and f["floor"] == 2 and f["floor_sure"]:
        add(33, "walkup", {"floor": f["floor"]}, floor=f["floor"], walkup_floor_2=True)
    elif f["floor"] and f["floor"] < 10 and f["floor_sure"]:
        add(32, "floor", {"floor": f["floor"]}, floor=f["floor"])
    if f["avail"] and f["avail"] != "now":
        add(30, "avail_date", {"date": f["avail"]}, available=f["avail"])
    elif f["avail"] == "now":
        add(24, "avail_now", available="now")
    # always on offer, so there is always another fact to turn to
    kind = f"this {f['beds']}" if f["beds"] else "this apartment"
    names = {"this_kind": kind, "This_kind": cap_first(kind),
             "Type_sentence": f"This is a {f['beds']}." if f["beds"] else
             "The listing does not say whether this is a studio or a 1-bedroom."}
    if price:
        add(22, "basic", {**names, "price": price}, beds=f["beds"], all_in=f["all_in"])
    else:
        add(5, "basic_no_price", names, beds=f["beds"])
    add(3, "type", names, beds=f["beds"])
    add(1, "plain")
    return out


class Spread:
    """Keeps count of how often each wording has been used in this run, so none passes its share of the rows."""

    def __init__(self, n_units, n_buildings=None):
        self.used = defaultdict(Counter)                # family -> wording id -> count
        self.unit_cap = share_cap(SHARE, n_units)
        self.building_cap = share_cap(SHARE, n_buildings or n_units)

    def cap(self, family):
        return self.building_cap if family.startswith("b:") else self.unit_cap

    def free(self, family, key):
        return self.used[family][key] < self.cap(family)

    def take(self, family, key):
        self.used[family][key] += 1

    def choose(self, family, keys, row_id, salt, avoid=(), must=False):
        """The first key, in the row's own seeded order, that is under its cap and not in `avoid`. With `must`,
        a key is always returned: the least used one (outside `avoid` if possible) when every cap is reached."""
        order = rotate(list(keys), row_id, salt)
        for k in order:
            if k not in avoid and self.free(family, k):
                return k
        for k in order:                                  # every fresh wording is at its cap: one already heard nearby
            if self.free(family, k):
                return k
        if not must:
            return None
        rest = [k for k in order if k not in avoid] or order
        return min(rest, key=lambda k: self.used[family][k])


# A catch about one thing makes a lead about the same thing a repeat: catch kind -> lead angles set back.
CATCH_COVERS = {"rent:net_effective": {"offer"}, "rent:needs_call": {"offer"}, "weak:space": {"size"},
                "weak:cost": {"price", "cost"}, "costs:could_pass": {"price", "cost"}}


def compose_line(f, peers, spread=None, siblings=(), catch_kind=None):
    """-> (host_line, pattern_id, used, meta). `siblings`: the meta of the apartments of the same building already
    written (best-ranked first). Rules kept here: the first three apartments of a building lead with three different
    kinds of fact; an apartment never repeats the condition of the sibling just before it; a lead about the same
    thing as the apartment's catch is set back; no wording passes its share of the page."""
    spread = spread or Spread(len(peers))
    siblings = list(siblings)
    top_angles = {b["angle"] for b in siblings} if len(siblings) < 3 else set()
    recent_conds = {b["cond"] for b in siblings[-1:]}
    heard = {b["pattern"] for b in siblings}
    covered = CATCH_COVERS.get(catch_kind, set())

    scored = []
    for score, cond, vals, used in lead_conditions(f, peers):
        if LEADS[cond][0] in covered and cond not in PEER_CONDITIONS:
            score -= 30                                  # the catch already says this
        scored.append((score, cond, vals, used))
    scored.sort(key=lambda c: (-c[0], c[1]))
    best = scored[0][0]
    pool = [c for c in scored if c[0] >= best - 8]
    order = rotate(pool, f["id"], "lead") + [c for c in scored if c[0] < best - 8]

    def wording(c, capped):
        texts = LEADS[c[1]][1]
        for fresh in (True, False):
            for i in rotate(list(range(len(texts))), f["id"], "wording:" + c[1]):
                pid = f"{c[1]}_{i + 1}"
                if (capped and not spread.free("lead", pid)) or (fresh and pid in heard):
                    continue
                return i, cap_first(texts[i].format(**c[2]))
        return None

    choice = None
    for strict_angle, capped in ((True, True), (False, True), (True, False), (False, False)):
        for c in order:
            if c[1] in recent_conds or (strict_angle and LEADS[c[1]][0] in top_angles):
                continue
            w = wording(c, capped)
            if w:
                choice = (c, w)
                break
        if choice:
            break
    if not choice:                                       # a building of identical, bare listings: repeat rather than fail
        c = order[0]
        choice = (c, (0, cap_first(LEADS[c[1]][1][0].format(**c[2]))))
    (score, cond, vals, used), (i, lead) = choice
    angle = LEADS[cond][0]
    pid = f"{cond}_{i + 1}"
    used = {k: v for k, v in used.items() if v is not None}

    # the second sentence: the price and the size, whichever the lead has not given
    price, _ = price_words(f)
    want_price = bool(price) and "all_in" not in used
    want_size = bool(f["sqft"]) and "sqft" not in used
    family = "price_size" if want_price and want_size else "price" if want_price else "size" if want_size else None
    second, frame_id = "", None
    if family:
        k = seed(f["id"], "second") % len(SECOND[family])
        second = SECOND[family][k].format(price=price, sqft=about_sqft(f["sqft"]) if f["sqft"] else "")
        frame_id = f"{family}_{k + 1}"
        if want_price and f.get("rent") and f["rent"] <= f["all_in"]:
            both = SECOND_RENT[family][k].format(rent=usd(f["rent"]), price=price,
                                                 sqft=about_sqft(f["sqft"]) if f["sqft"] else "")
            if len((lead + " " + both).split()) <= MAX_WORDS:
                second, frame_id = both, f"{family}_rent_{k + 1}"
                used["rent"] = f["rent"]
        if want_price:
            used["all_in"] = f["all_in"]
        if want_size:
            used["sqft"] = f["sqft"]
    line = (lead + " " + second).strip()
    spread.take("lead", pid)
    return line, pid, used, {"cond": cond, "angle": angle, "frame": frame_id, "pattern": pid}


# ------------------------------------------------------------------ the catch (per apartment)

UNKNOWN_NAMES = {"building fees": "building fees", "pet rent": "pet rent", "parking fee": "the parking fee", "gas": "the gas bill"}


def _why(u):
    return str(get(u, "confirm", "why") or "")


def _code(u):
    """The open item's reason code in the page data (confirm.code: complex, select_buildings, stale_page, ...)."""
    return str(get(u, "confirm", "code") or "") if get(u, "confirm", "asterisk") else ""


def _what(u):
    return get(u, "confirm", "what") if get(u, "confirm", "asterisk") else None


# A catch of these kinds states a reason, so the apartment must carry that reason: kind -> test on the apartment.
CATCH_BASIS = {
    "confirm:live check": lambda u: _what(u) == "live check",
    "confirm:elevator": lambda u: _what(u) == "elevator",
    "confirm:elevator named": lambda u: _what(u) == "elevator" and (_code(u) in ("complex", "select_buildings") or bool(
        re.search(r"elevator is named for (?:this|the) property|select buildings|some (?:of its )?buildings", _why(u), re.I))),
    "confirm:listing": lambda u: _what(u) == "listing",
    "confirm:listing permit": lambda u: _what(u) == "listing" and bool(re.search(r"occupancy permit|certificate of occupancy", _why(u), re.I)),
    "confirm:listing stale": lambda u: _what(u) == "listing" and (_code(u) == "stale_page" or bool(
        re.search(r"last changed|last updated|last refreshed|stale|months old|availability date is", _why(u), re.I))),
    "confirm:listing lease price": lambda u: _what(u) == "listing" and (_code(u) == "sibling_12" or "12-month price" in str(
        get(u, "confirm", "label") or "")),
    "confirm:listing one site": lambda u: _what(u) == "listing" and bool(re.search(r"one listing site only", _why(u), re.I)),
    "confirm:listing which building": lambda u: _what(u) == "listing" and (_code(u) == "address_mismatch" or str(
        get(u, "confirm", "question") or "").lower().startswith("which building")),
    "confirm:availability": lambda u: _what(u) == "availability",
    "confirm:availability plan": lambda u: _what(u) == "availability" and bool(re.search(r"floor.?plan", _why(u), re.I)),
    "confirm:eligibility": lambda u: _what(u) == "eligibility",
    "confirm:eligibility income": lambda u: _what(u) == "eligibility" and "income" in _why(u).lower(),
    "confirm:eligibility age": lambda u: _what(u) == "eligibility" and bool(re.search(r"\bages? \d+|\d+ and over", _why(u), re.I)),
    "confirm:dogs conflict": lambda u: dog_open(u) == "conflict",
    "confirm:dogs approval": lambda u: dog_open(u) == "approval",
    "confirm:dogs case": lambda u: dog_open(u) == "case",
    "confirm:dogs contact": lambda u: dog_open(u) == "contact",
    "confirm:dogs small pets": lambda u: dog_open(u) == "small pets",
    "confirm:dogs no text": lambda u: dog_open(u) == "no text",
    "confirm:dogs open": lambda u: dog_open(u) is not None,
    "rent:net_effective": net_effective,
    "rent:needs_call": has_special,
    "costs:could_pass": lambda u: bool(u.get("all_in_unknown")) and (
        "could pass $3,000" in disclosed(u) or could_pass(u)),
    "lease_term": lambda u: lease_months(u) is not None,
    "dog_weight": lambda u: "dog weight limit not published" in disclosed(u),
    "condo": lambda u: "condo rented by its owner" in disclosed(u),
    "conditions:income": lambda u: "income requirement" in disclosed(u),
    "conditions:credit": lambda u: "credit score requirement" in disclosed(u),
    "conditions:income_plain": lambda u: "income requirement" in disclosed(u),
    "conditions:credit_plain": lambda u: "credit score requirement" in disclosed(u),
    "conditions:furnished": lambda u: "furnished apartment" in disclosed(u),
    "floor:unpublished": lambda u: num(u.get("floor")) is None,
    "floor:walkup inferred": lambda u: get(u, "elevator", "walkup_floor_2") is True and u.get("floor_basis") not in ("confirmed", "stated"),
    "confirm:floor and elevator": lambda u: _what(u) == "floor and elevator",
    "floor:inferred": lambda u: num(u.get("floor")) is not None and u.get("floor_basis") not in ("confirmed", "stated"),
    "weak:space": lambda u: num(u.get("sqft")) is not None and num(u.get("sqft")) < 600,
    "weak:cost": lambda u: num(get(u, "cost_check", "cap_margin")) is not None and num(get(u, "cost_check", "cap_margin")) < 150,
}
CONFIRM_ORDER = {                                       # the open item -> its families, the most specific first
    "live check": ["confirm:live check"],
    "elevator": ["confirm:elevator named", "confirm:elevator"],
    "floor and elevator": ["confirm:floor and elevator"],
    "listing": ["confirm:listing permit", "confirm:listing lease price", "confirm:listing which building", "confirm:listing one site",
                "confirm:listing stale", "confirm:listing"],
    "availability": ["confirm:availability plan", "confirm:availability"],
    "eligibility": ["confirm:eligibility income", "confirm:eligibility age", "confirm:eligibility"],
}


def lease_months(u):
    """The lease length the price shown belongs to, when it is not 12 months."""
    m = num(get(u, "cost_check", "lease_term_months")) or num(get(u, "rent", "lease_months"))
    return int(m) if m and int(m) != 12 else None


def could_pass(u):
    """Unpublished cost lines that could carry the total past her limit: each missing line could be about $100."""
    margin, unknown = num(get(u, "cost_check", "cap_margin")), u.get("all_in_unknown") or []
    return bool(unknown) and num(u.get("all_in")) is not None and margin is not None and 0 < margin < 100 * len(unknown)


def catch_options(u, f):
    """-> [(kind, values to fill, fields used)], the most important first; the first is the catch. The apartment's
    open item comes before everything (said with its own reason where the open item gives one); then a price that
    includes an offer; costs that could pass her limit; an offer whose effect is not stated; the lease term; an
    unpublished dog weight limit; a condo rented by its owner; the floor; else its weakest own fact."""
    # a condition she must meet comes first, with the listing's own figure (independent check 4, D8)
    income = str(get(u, "conditions", "income_requirement") or "").strip().rstrip(".")
    income = re.sub(r"\b(?:a|per|each) year\b", "yearly", income)      # the page keeps "year" for a building's age
    credit = str(get(u, "conditions", "credit_score_requirement") or "").strip().rstrip(".")
    if "income requirement" in f["disclosures"]:
        return [("conditions:income", {"income": income}, {"income_requirement": income}) if income else
                ("conditions:income_plain", {}, {"disclosure": "income requirement"})]
    if "credit score requirement" in f["disclosures"]:
        return [("conditions:credit", {"credit": credit}, {"credit_score_requirement": credit}) if credit else
                ("conditions:credit_plain", {}, {"disclosure": "credit score requirement"})]
    c = u.get("confirm") or {}
    if c.get("asterisk") and c.get("what"):
        what = str(c["what"])
        used = {"confirm_what": what, "confirm_why": c.get("why")}
        if f["dog_open"]:
            kind = "confirm:dogs " + f["dog_open"]
            return [(kind if kind in CATCHES else "confirm:dogs open", {}, used)]
        for kind in CONFIRM_ORDER.get(what, []):
            if CATCH_BASIS[kind](u):
                return [(kind, {}, used)]
        return [("confirm:other", {}, used)]
    out = []
    rent = u.get("rent") or {}
    if "furnished apartment" in f["disclosures"]:
        out.append(("conditions:furnished", {}, {"disclosure": "furnished apartment"}))
    if net_effective(u):
        out.append(("rent:net_effective", {}, {"rent_basis_kind": "net_effective"}))
    names = f["unknown"]
    if CATCH_BASIS["costs:could_pass"](u):
        unknown = ["parking" if x == "parking fee" and f["park_kind"] is None else UNKNOWN_NAMES.get(x, x) for x in names]
        one = len(unknown) == 1 and unknown[0] != "building fees"   # "building fees are", "the parking fee is"
        out.append(("costs:could_pass",
                    {"names": join_and(unknown), "Names": cap_first(join_and(unknown)), "are": "is" if one else "are",
                     "them": "it" if one else "them", "amounts": "amount" if one else "amounts", "limit": usd(CAP)},
                    {"all_in_unknown": names, "cap_margin": f["margin"]}))
    if has_special(u) and not net_effective(u):
        out.append(("rent:needs_call", {}, {"rent_needs_call": bool(rent.get("needs_call")),
                                            "special_offer_disclosed": "special offer" in f["disclosures"]}))
    lease = lease_months(u)
    if lease:
        out.append(("lease_term", {"months": lease}, {"lease_months": lease}))
    if "dog weight limit not published" in f["disclosures"]:
        out.append(("dog_weight", {}, {"disclosure": "dog weight limit not published"}))
    if "condo rented by its owner" in f["disclosures"]:
        out.append(("condo", {}, {"disclosure": "condo rented by its owner"}))
    if num(u.get("floor")) is None:
        out.append(("floor:unpublished", {}, {"floor": None}))
    elif not f["floor_sure"] and f["floor"] and f["walkup"]:
        out.append(("floor:walkup inferred", {"floor": f["floor"]}, {"floor": f["floor"], "floor_basis": u.get("floor_basis"), "walkup_floor_2": True}))
    elif not f["floor_sure"] and f["floor"]:
        out.append(("floor:inferred", {"floor": f["floor"]}, {"floor": f["floor"], "floor_basis": u.get("floor_basis")}))
    out.append(weakest(u, f))
    return out


def weakest(u, f):
    """The weaker of the apartment's own two scored facts, size and cost, when it is weak in plain terms too: under
    600 square feet, or within $150 of her limit."""
    parts = {k: v for k, v in (get(u, "scores", "parts") or {}).items() if k in ("space", "cost") and num(v) is not None}
    price, gap = price_words(f)
    for kind in sorted(parts, key=lambda k: (parts[k], k)):
        if kind == "space" and CATCH_BASIS["weak:space"](u):
            return "weak:space", {"sqft": about_sqft(f["sqft"])}, {"sqft": f["sqft"]}
        if kind == "cost" and price and gap and CATCH_BASIS["weak:cost"](u):
            return "weak:cost", {"price": price, "gap": gap}, {"all_in": f["all_in"], "cap_margin": f["margin"]}
    return "none", {}, {}


def compose_catch(u, f, spread=None, siblings=()):
    """-> (host_catch, kind, used, wording id). The catch is always the apartment's most important open point; only
    its wording is chosen, and a wording its building has not used yet comes first."""
    spread = spread or Spread(1)
    kind, vals, used = catch_options(u, f)[0]
    texts = CATCHES[kind]
    ids = [f"{kind}_{i + 1}" for i in range(len(texts))]
    cid = spread.choose("catch", ids, f["id"], "catch", avoid={b["catch_id"] for b in siblings}, must=True)
    text = cap_first(texts[ids.index(cid)].format(**vals))
    spread.take("catch", cid)
    return text, kind, used, cid


# ------------------------------------------------------------------ section subheads (per apartment)
# One short line (at most 14 words, no numbers: the section's headline states them) under the cost, parking, dog and
# building headlines. Each is picked by what the apartment's fields say; an unknown gets an "ask" line, never a
# statement; when nothing can be said, or every wording has reached its share, the subhead is empty.

def sub_keys(u, f):
    """Which library entry applies in each section, from the apartment's own fields. None = say nothing."""
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
    P = f["parking"]
    k = P["kind"]
    priced = "priced" if P["fee"] else "unpriced"
    if k is None:
        parking = "unknown"
    elif P["included"]:                                  # the included space, named as the kind it is
        extra = parking_extra(P)
        if k == "lot" and P["detail"] != "gated_lot":
            parking = "included_lot_garage" if extra and extra[0] == "garage" else "included_lot"
        elif k in ("off_street", "assigned", "unspecified"):
            parking = "included_" + k
        else:
            parking = "included"
    elif k == "street":
        parking = "street"
    else:                                                # garage, covered, lot, off_street, assigned, offsite, unspecified
        parking = f"{k}_{priced}"
    dog_field = u.get("dog") or {}
    limit = str(dog_field.get("weight_limit_lb") or "").strip().lower()
    if f["dog_open"] == "conflict" or str(dog_field.get("allowed") or "").lower() == "conflicting":
        dog = "conflicting"
    elif f["dog_open"]:                                  # dogs are the open item: nothing here may say they are allowed
        dog = "unsettled"
    elif f["small_only"]:
        dog = "small_only"
    elif "dog weight limit not published" in f["disclosures"]:
        dog = "weight_unpublished"
    elif limit and limit != "no limit":
        dog = "weight_limit"
    elif f["dog_amenity"] and "on site" in f["dog_amenity"]:
        dog = "onsite"
    elif f["dog_park_m"] is not None and f["dog_park_m"] <= 800:
        dog = "near_run"
    elif dog_field.get("pet_rent") is None:
        dog = "pet_rent_unknown"
    else:
        dog = None
    if f["doorman"] == "24-hour":
        building = "front_desk"
    elif f["doorman"]:
        building = "doorman"
    elif f["desk"] in ("concierge24", "concierge", "attended"):
        building = f["desk"]
    elif f["pool"] and f["laundry_mode"] in ("wd", "in_unit"):
        building = "pool_laundry"
    elif f["laundry"]:                                   # a listing site's appliance list is "the listing shows", a washer a washer
        building = "laundry" if f["laundry_mode"] in ("wd", "in_unit") else "laundry_" + str(f["laundry_mode"])
    elif f["pool"]:
        building = "pool"
    elif f["gym"]:
        building = "gym"
    else:
        building = None
    return {"cost": cost, "parking": parking, "dog": dog, "building": building}


def compose_subs(u, f, spread=None, before=()):
    """-> ({sub_cost, sub_parking, sub_dog, sub_building}, {section: library key}). A wording the building has
    already used comes last, and one that has reached its share of the page is left out."""
    spread = spread or Spread(1)
    keys = sub_keys(u, f)
    out = {}
    for section, key in keys.items():
        options = dict(SUBS[section]).get(key) if key else None
        options = [o for o in options if fits(o, f)] if options else options
        text = ""
        if options:
            heard = {b.get(section) for b in before}
            text = spread.choose("sub_" + section, options, f["id"], "sub_" + section, avoid=heard) or ""
            if text:
                spread.take("sub_" + section, text)
        out["sub_" + section] = text
    return out, keys


# ------------------------------------------------------------------ About the building

def building_facts(group):
    """group: the apartments listed in one building, best-ranked first -> the building's own facts. Building-level
    fields are read from the best-ranked apartment; an open item on any of its apartments counts for the building."""
    fs = [facts(u) for u in group]
    b = dict(fs[0])
    b["id"] = fs[0]["building"]
    b["n_units"] = len(group)
    b["dog_open"] = next((f["dog_open"] for f in fs if f["dog_open"]), None)
    b["elevator_open"] = any(f["elevator_open"] for f in fs)
    b["walkup_all"] = all(f["walkup"] for f in fs)          # owner, 2026-11-17: every listed apartment is a floor-2 walk-up
    b["elevator_sure"] = b["elevator_sure"] and not any(f["walkup"] for f in fs)
    b["unknown"] = sorted({x for f in fs for x in f["unknown"]})
    b["disclosures"] = set().union(*(f["disclosures"] for f in fs))
    b["pet_rent_known"] = all(f["pet_rent_known"] for f in fs)
    return b


def dog_park_words(name):
    """How a sentence names the nearest dog park: its own name when the name says what it is, otherwise "the nearest
    dog park, <name>," and just "the nearest dog park" for a name that is only the words."""
    name = re.sub(r"\s*\(.*?\)", "", str(name)).strip()
    if name.lower() in ("dog run", "dog park", ""):
        return "the nearest dog park"
    if re.search(r"\bdog\b|\bbark", name, re.I):
        return name
    return f"the nearest dog park, {name},"


STATION_NOUN = {"train": "train station", "subway": "subway station", "PATH": "PATH station", "light rail": "light rail stop"}


def station_words(name, kind=None):
    """How a sentence names the nearest station, by its kind (independent check 5, N3: the nearest station is now of
    any kind, moments.sat.train_station_kind = train / subway / PATH / light rail): "Newark Penn Station", "the Kew
    Gardens train station", "the Elmhurst Av subway station", "the Journal Square PATH station", "the Port Imperial
    light rail stop". A kind the data does not give is a train station, as before."""
    name = str(name).strip()
    kind = str(kind or "train").strip()
    kind = {"path": "PATH"}.get(kind.lower(), kind.lower())
    if kind == "train" and re.search(r"\bstation\b", name, re.I):
        return name
    return f"the {name} {STATION_NOUN.get(kind, 'station')}"


def restaurants_words(n):
    n = int(n)
    return "No restaurants are" if n == 0 else "1 restaurant is" if n == 1 else \
        f"{n} restaurants are" if n < 10 else f"About {n} restaurants are"


def building_warning(b):
    """The main thing to ask about this building -> key of WARNINGS. Most pressing first."""
    if b["dog_open"]:
        return "dog_unsettled"
    if b["elevator_open"]:
        return "elevator_open"
    if b["park_kind"] is None:
        return "parking_unknown"
    if b["park_kind"] == "street":
        return "parking_street"
    if not b["park_included"] and not b["park_fee"]:
        return {"unspecified": "parking_kind", "assigned": "parking_assigned"}.get(b["park_kind"], "parking_fee")
    if not b["pet_rent_known"] or "pet rent" in b["unknown"]:
        return "pet_rent"
    if "building fees" in b["unknown"]:
        return "fees"
    if b["small_only"]:
        return "weight"
    if "overnight street parking" in b["disclosures"]:
        return "overnight"
    return "tour_walkup" if b.get("walkup_all") else "tour"


def building_conditions(b, peers):
    """-> [(score, condition, values, fields used)] for the sentences of About the building. `peers`: the buildings
    listed in the same neighborhood (this one included)."""
    n = len(peers)
    small = -25 if n == 2 else 0
    out = []
    fee_asked = building_warning(b) in ("parking_fee", "parking_kind", "parking_assigned")   # the warning will say the fee is not published, and to ask

    def add(score, cond, vals=None, **used):
        out.append((score, cond, {"n": n, "w10": WALK_RADIUS, **(vals or {})}, used))

    onsite = b["dog_amenity"][2:-8] if b["dog_amenity"] and "on site" in b["dog_amenity"] else None   # "dog park"
    tail = f", and a space costs {usd(b['park_fee'])} a month" if b["park_fee"] else "" if fee_asked else \
        ", and the fee is not published"                # the warning already says so when the fee is the thing to ask
    run = None
    if b["dog_park"] and b["dog_park_m"] is not None:
        dp = dog_park_words(b["dog_park"])
        run = {"dogpark_end": dp.rstrip(","), "Dogpark": cap_first(dp), "dogpark_mi": miles(b["dog_park_m"])}
    park = {"park": b["park"], "park_mins": minutes(b["park_walk"])} if b["park"] and b["park_walk"] is not None else None
    # ---- inside: against the other buildings listed in the neighborhood
    if only(b, peers, lambda p: p["pool"]):
        add(90 + small, "only_pool", peers=n, pool=True)
    if only(b, peers, lambda p: p["park_kind"] == "garage"):
        gtail = ", and parking is included" if b["park_included"] else f", at {usd(b['park_fee'])} a month" if b["park_fee"] \
            else "" if fee_asked else ", with the fee not published"
        add(88 + small, "only_garage", {"gtail": gtail}, peers=n, parking="garage", parking_fee=b["park_fee"])
    if only(b, peers, lambda p: p["desk"] in ("doorman", "doorman24")):     # "a doorman" only where the amenity is one
        add(72 + small, "only_doorman", peers=n, doorman=b["doorman"])
    if b["laundry_mode"] in ("wd", "in_unit") and only(b, peers, lambda p: p["laundry"]):
        add(68 + small, "only_laundry", peers=n, in_unit_laundry=True)
    if onsite and only(b, peers, lambda p: bool(p["dog_amenity"]) and "on site" in p["dog_amenity"]):
        add(67 + small, "only_dogspot", {"dogthing": onsite}, peers=n, dog_amenities=b["dog_amenity"])
    # ---- inside: on its own
    P = b["parking"]
    extra = extra_words(P)
    xused = {"parking_extra": parking_extra(P)} if extra else {}
    if b["park_included"]:
        k = b["park_kind"]
        if k == "lot":
            add(65, "lot_included", {"lot_space": lot_space(P), "Lot_space": cap_first(lot_space(P)), "extra": extra},
                parking="included", parking_kind=P["detail"], **xused)
        elif k == "off_street":
            add(65, "off_street_included", {"extra": extra}, parking="included", parking_kind=k, **xused)
        elif k in ("assigned", "unspecified"):
            add(65, k + "_included", parking="included", parking_kind=k)
        else:
            incl = {"garage": "a garage space", "covered": "a covered parking space"}.get(k, "a parking space")
            add(65, "parking_included", {"incl": incl, "Incl": cap_first(incl)}, parking="included", parking_kind=k)
    if onsite:
        add(58, "dog_onsite", {"dogthing": onsite}, dog_amenities=b["dog_amenity"])
    if b["park_kind"] == "garage" and not b["park_included"]:
        if b["park_fee"]:
            add(55, "garage_priced", {"fee": usd(b["park_fee"])}, parking="garage", parking_fee=b["park_fee"])
        else:
            add(55, "garage_fee_asked" if fee_asked else "garage_unpriced", parking="garage", parking_fee=None)
    if b["pool"]:
        add(50, "pool", pool=True)
    if b["doorman"]:
        add(45, "front_desk" if b["doorman"] == "24-hour" else "doorman", doorman=b["doorman"])
    elif b["desk"] in ("concierge24", "concierge", "attended"):
        add(42, b["desk"], desk=b["desk"])
    if b["laundry"]:
        mode = b["laundry_mode"]                         # "the listing shows" where a listing site's tag is the only source
        add(40, "laundry" if mode in ("wd", "in_unit") else "laundry_" + str(mode), in_unit_laundry=True, laundry_mode=mode)
    if b["park_kind"] == "covered" and not b["park_included"]:
        add(40, "covered", {"ptail": tail}, parking="covered", parking_fee=b["park_fee"])
    if b["no_weight_limit"] and not b["dog_open"]:
        add(34, "dog_no_limit", dog_weight_limit="no limit")
    if b["built"] and b["built"] >= 2015:
        add(32, "newer", {"built": b["built"]}, year_built=b["built"])
    if b["park_kind"] == "lot" and not b["park_included"]:
        add(30, "lot", {"ptail": tail, "extra": extra}, parking="lot", parking_fee=b["park_fee"], **xused)
    if b["park_kind"] == "off_street" and not b["park_included"]:
        add(30, "off_street", {"ptail": tail, "extra": extra}, parking="off_street", parking_fee=b["park_fee"], **xused)
    if b["park_kind"] == "offsite":                      # no parking at the building: the first thing to know about it
        if b["park_fee"]:
            add(60, "offsite", {"where": offsite_where(P), "fee": usd(b["park_fee"])}, parking="offsite", parking_fee=b["park_fee"])
        elif not fee_asked:
            add(60, "offsite_unpriced", {"where": offsite_where(P)}, parking="offsite", parking_fee=None)
    if b["park_kind"] == "assigned" and not b["park_included"] and not fee_asked:
        add(30, "assigned", parking="assigned")
    if b["lounge"]:
        add(28, "lounge", lounge_or_coworking=True)
    if b["gym"]:
        add(20, "gym", gym=True)
    if b["built"] and b["built"] < 2015:
        add(15, "dated", {"built": b["built"]}, year_built=b["built"])
    if b["park_kind"] == "street":
        add(12, "street_parking", parking="street")
    if b["park_kind"] == "unspecified" and not b["park_included"] and not fee_asked:
        add(8, "unspecified_parking", parking="unspecified")
    add(1, "plain")
    # ---- near the building
    if run and b["dog_park_m"] <= 1600 and extreme(b, peers, "dog_park_m", min):
        add(63 + small, "closest_run", run, peers=n, dog_park=b["dog_park"], dog_park_miles=run["dogpark_mi"])
    if park and b["park_walk"] <= 8 and extreme(b, peers, "park_walk", min):
        add(56 + small, "closest_park", park, peers=n, park=b["park"], park_walk_min=park["park_mins"].split()[0])
    if run and b["dog_park_m"] <= 800:
        add(48, "dogpark_near", run, dog_park=b["dog_park"], dog_park_miles=run["dogpark_mi"])
    if b["restaurants"] is not None and b["restaurants"] >= 20:
        add(38, "food", {"rest": whole(b["restaurants"])}, restaurants_800m=int(b["restaurants"]))
    if park and b["park_walk"] <= 5:
        add(35, "park", park, park=b["park"], park_walk_min=park["park_mins"].split()[0])
    if b["station"] and b["station_m"] is not None and b["station_m"] <= 800:
        st = station_words(b["station"], b["station_kind"])
        add(26, "station", {"station": st, "Station": cap_first(st), "station_mi": miles(b["station_m"])},
            train_station=b["station"], train_station_kind=b["station_kind"], train_station_miles=miles(b["station_m"]))
    if b["market"] and b["market_m"] is not None and b["market_m"] <= 500:
        add(24, "errands", {"market": b["market"], "market_mi": miles(b["market_m"])},
            supermarket=b["market"], supermarket_miles=miles(b["market_m"]))
    if park and 5 < b["park_walk"] <= 20:
        add(10, "park", park, park=b["park"], park_walk_min=park["park_mins"].split()[0])
    if b["restaurants"] is not None and b["restaurants"] < 20:
        add(6, "food_few", {"Rest_few": restaurants_words(b["restaurants"])}, restaurants_800m=int(b["restaurants"]))
    if b["market"] and b["market_m"] is not None and b["market_m"] > 500:
        add(4, "market_far", {"market": b["market"], "market_mi": miles(b["market_m"])},
            supermarket=b["market"], supermarket_miles=miles(b["market_m"]))
    return out


def building_points(b):
    """Every icon point this building's fields support -> [(key, values, fields used)], the steady ones first
    (parking, the dog policy), then the rest."""
    out = []

    def add(key, vals=None, **used):
        out.append((key, {"w10": WALK_RADIUS, **(vals or {})}, used))

    P = b["parking"]
    if P["kind"]:                                        # one sentence, composed from the structured fields
        e = parking_extra(P)
        add("parking", {"parking_point": parking_point(P)}, parking=P["kind"], parking_detail=P["detail"],
            parking_fee=P["fee"], parking_included=P["included"], **({"parking_extra": list(e)} if e else {}))
    if b["dog_amenity"] and "on site" in b["dog_amenity"]:
        add("dog_onsite", {"dogthing": b["dog_amenity"][2:-8]}, dog_amenities=b["dog_amenity"])
    if not b["dog_open"]:                                # an unsettled dog policy is never stated as a yes
        if b["no_weight_limit"]:
            add("dog_no_limit", dog_weight_limit="no limit")
        elif b["weight_limit"]:
            add("dog_limit", {"lb": whole(b["weight_limit"])}, dog_weight_limit_lb=b["weight_limit"])
        elif b["dog_allowed"] and b["small_only"]:
            add("dog_small", dog_allowed="yes", dog_size_note="small dogs, no weight")
        elif b["dog_allowed"]:
            add("dog_ok", dog_allowed="yes")
    rest = []

    def more(key, vals=None, **used):
        rest.append((key, {"w10": WALK_RADIUS, **(vals or {})}, used))

    if b["laundry"]:
        mode = b["laundry_mode"]
        more({"wd": "laundry", "in_unit": "laundry_plain"}.get(mode, "laundry_" + str(mode)), in_unit_laundry=True, laundry_mode=mode)
    if b["pool"]:
        more("pool", pool=True)
    if b["doorman"]:
        more("front_desk" if b["doorman"] == "24-hour" else "doorman", doorman=b["doorman"])
    elif b["desk"] in ("concierge24", "concierge", "attended"):
        more(b["desk"], desk=b["desk"])
    if b["gym"]:
        more("gym", gym=True)
    if b["lounge"]:
        more("lounge", lounge_or_coworking=True)
    if b["park"] and b["park_walk"] is not None and b["park_walk"] <= 15:
        more("park", {"park": b["park"], "park_mins": minutes(b["park_walk"])}, park=b["park"],
             park_walk_min=minutes(b["park_walk"]).split()[0])
    if b["dog_park"] and b["dog_park_m"] is not None and b["dog_park_m"] <= 1600:
        more("dogrun", {"Dogpark": cap_first(dog_park_words(b["dog_park"])), "dogpark_mi": miles(b["dog_park_m"])},
             dog_park=b["dog_park"], dog_park_miles=miles(b["dog_park_m"]))
    if b["restaurants"] is not None and b["restaurants"] >= 4:
        more("food", {"Rest_count": restaurants_words(b["restaurants"])}, restaurants_800m=int(b["restaurants"]))
    if b["station"] and b["station_m"] is not None and b["station_m"] <= 1200:
        more("train", {"Station": cap_first(station_words(b["station"], b["station_kind"])), "station_mi": miles(b["station_m"])},
             train_station=b["station"], train_station_kind=b["station_kind"], train_station_miles=miles(b["station_m"]))
    if b["built"]:
        more("built", {"built": b["built"]}, year_built=b["built"])
    last = []
    if b["elevator_sure"] and not b["elevator_open"]:
        last.append(("elevator", {}, {"elevator": "yes"}))
    n = b["n_units"]
    last.append(("units", {"Apts_listed": "1 apartment is listed" if n == 1 else f"{n} apartments are listed"},
                 {"units_shown": n}))
    return out, rest, last


def compose_building(b, peers, spread=None, before=()):
    """-> (about_building, about_points, facts used, meta). `before`: the meta of the buildings already written in
    the same neighborhood. One or two sentences, at most ABOUT_MAX_WORDS: the building itself, then what is near
    it; then 3 to 5 icon points, one of them the warning, none repeating a fact the sentences state."""
    spread = spread or Spread(len(peers), len(peers))
    before = list(before)
    conds = building_conditions(b, peers)
    last = before[-1] if before else {}
    heard = {x for m in before for x in m["patterns"]}
    chosen, used_all, budget = [], {}, ABOUT_MAX_WORDS
    for group in ("inside", "around"):
        scored = []
        for score, cond, vals, used in conds:
            if BUILDING[cond][1] != group:
                continue
            if group == "around" and cond in ("closest_run", "closest_park") and chosen and \
                    chosen[0][0] in BUILDING_PEER_CONDITIONS:
                cond += "_also"                          # the first sentence has already named the neighborhood's buildings
            if cond in last.get("conds", ()) and cond not in BUILDING_PEER_CONDITIONS:
                score -= 10                              # the building just above opened on this fact
            if group == "around" and BUILDING[cond][0] in {BUILDING[c][0] for c, _, _ in chosen}:
                score -= 30                              # the first sentence was already about the dog
            scored.append((score, cond, vals, used))
        if not scored:
            continue                                     # nothing is known about what is near: one sentence
        scored.sort(key=lambda c: (-c[0], c[1]))
        best = scored[0][0]
        pool = [c for c in scored if c[0] >= best - 8]
        order = rotate(pool, b["id"], "b:" + group) + [c for c in scored if c[0] < best - 8]
        pick = None
        for capped, fresh in ((True, True), (True, False), (False, False)):
            for c in order:
                texts = BUILDING[c[1]][2]
                for i in rotate(list(range(len(texts))), b["id"], "b:wording:" + c[1]):
                    pid = f"{c[1]}_{i + 1}"
                    if (capped and not spread.free("b:sentence", pid)) or (fresh and pid in heard):
                        continue
                    text = cap_first(texts[i].format(**c[2]))
                    if words(text) > budget - (8 if group == "inside" else 0) or not fits(text, b):
                        continue
                    pick = (c, pid, text)
                    break
                if pick:
                    break
            if pick:
                break
        if not pick:
            continue
        (score, cond, vals, used), pid, text = pick
        spread.take("b:sentence", pid)
        budget -= words(text)
        chosen.append((cond, pid, text))
        used_all.update({k: v for k, v in used.items() if v is not None})
    about = " ".join(t for _, _, t in chosen)

    # the icon points: the warning, then facts the sentences have not already stated
    said = {ANGLE_TOPIC.get(BUILDING[c][0]) for c, _, _ in chosen}
    said |= {"dogspot" for c, _, _ in chosen if c in ("dog_onsite", "only_dogspot")}
    said |= {"dogrun" for c, _, _ in chosen if c in ("dogpark_near", "closest_run", "closest_run_also")}
    said |= {"dog" for c, _, _ in chosen if c == "dog_no_limit"}
    wkey = building_warning(b)
    wtopic, wtext = WARNINGS[wkey]
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
        icon, topic, text = POINTS[key]
        points.append({"icon": icon, "text": cap_first(text.format(**vals))})
        keys.append(key)
        used_all.update({k: v for k, v in used.items() if v is not None})
    points.append({"icon": "warning", "text": wtext.format(parking=PARKING_NAMES.get(b["park_kind"], "parking"))})
    meta = {"conds": [c for c, _, _ in chosen], "patterns": [p for _, p, _ in chosen]}
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
    """units: the `units` list of site/data.json. -> rows with the columns in FIELDS. Neighborhoods are taken in
    name order and apartments in rank order, so the same data always gives the same text. An apartment is compared
    with the other apartments listed in its own building."""
    tree = grouped(units)
    spread = Spread(len(units))
    rows, done = [], {}
    for hood in sorted(tree, key=str):
        peers = {bid: [facts(u) for u in group] for bid, group in tree[hood].items()}
        siblings = defaultdict(list)
        for u in sorted((u for g in tree[hood].values() for u in g), key=rank_key):
            bid = u.get("building_id") or u["id"]
            f = next(p for p in peers[bid] if p["id"] == u["id"])
            catch, ckind, cused, cid = compose_catch(u, f, spread, siblings[bid])
            line, pid, used, meta = compose_line(f, peers[bid], spread, siblings[bid], ckind)
            siblings[bid].append({**meta, "catch_kind": ckind, "catch_id": cid})
            done[u["id"]] = {"listing_id": u["id"], "host_line": line, "host_catch": catch,
                             "meta": {"hood_id": hood, "building_id": bid, "pattern": pid, "angle": meta["angle"],
                                      "frame": meta["frame"], "line": used, "catch_kind": ckind, "catch_id": cid,
                                      "catch": cused}}
            rows.append(done[u["id"]])
    # The subheads. The page shows them for each building's best apartment, so those are served first; the others
    # get one while its wording is still under its share of the page.
    heard = defaultdict(list)
    for first in (True, False):
        for hood in sorted(tree, key=str):
            for bid, group in tree[hood].items():
                for u in (group[:1] if first else group[1:]):
                    f = facts(u)
                    subs, kinds = compose_subs(u, f, spread, heard[bid])
                    heard[bid].append({s[4:]: t for s, t in subs.items()})
                    done[u["id"]].update(subs)
                    done[u["id"]]["meta"]["subs"] = kinds
    for r in rows:
        r["facts_used_json"] = json.dumps(r.pop("meta"), ensure_ascii=False, sort_keys=True)
    return [{k: r[k] for k in FIELDS} for r in rows]


def build_buildings(units):
    """-> rows with the columns in BUILDING_FIELDS, one per building_id, in neighborhood order then best rank."""
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
    """-> {family: {with_text, distinct, top, top_count, top_share}} for the apartment rows."""
    n = len(rows)
    meta = [json.loads(r["facts_used_json"]) for r in rows]
    out = {}
    for name, values in (("lead wording", [m["pattern"] for m in meta]),
                         ("lead condition", [m["pattern"].rsplit("_", 1)[0] for m in meta]),
                         ("catch wording", [m["catch_id"] for m in meta]),
                         ("catch kind", [m["catch_kind"] for m in meta]),
                         *((c, [r[c] for r in rows if r[c]]) for c in SUB_COLS)):
        top, count = Counter(values).most_common(1)[0] if values else ("", 0)
        out[name] = {"with_text": len(values), "distinct": len(set(values)), "top": top, "top_count": count,
                     "top_share": count / n if n else 0.0}
    return out


def building_distribution(rows):
    """The same for the building rows: the sentences (capped) and, for information, the points and warnings."""
    n = len(rows)
    meta = [json.loads(r["facts_used_json"]) for r in rows]
    out = {}
    for name, values in (("building sentence", [p for m in meta for p in m["sentences"]]),
                         ("building point", [k for m in meta for k in m["points"]]),
                         ("building warning", [m["warning"] for m in meta])):
        top, count = Counter(values).most_common(1)[0] if values else ("", 0)
        out[name] = {"with_text": len(values), "distinct": len(set(values)), "top": top, "top_count": count,
                     "top_share": count / n if n else 0.0}
    return out


def main():
    global CAP
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(DATA), help="page data to read (default site/data.json)")
    ap.add_argument("--out", default=str(OUT), help="apartment CSV to write (default data/reference/realtor_lines.csv)")
    ap.add_argument("--out-buildings", default=str(OUT_BUILDINGS),
                    help="building CSV to write (default data/reference/building_about.csv)")
    a = ap.parse_args()
    page = json.loads(Path(a.data).read_text(encoding="utf-8"))
    units = page["units"]
    cap = num(get(page, "meta", "cap_all_in"))
    if cap:
        CAP = int(cap)
    rows, brows = build(units), build_buildings(units)
    for path, fields, data in ((a.out, FIELDS, rows), (a.out_buildings, BUILDING_FIELDS, brows)):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(data)
    print(f"{len(rows)} apartments written to {a.out}")
    print(f"{len(brows)} buildings written to {a.out_buildings}")
    print(f"limit: a lead, catch, subhead or building-sentence wording on at most {SHARE:.0%} of rows "
          f"(the price-and-size sentence, icon points and warnings are plain facts and are not varied)")
    for d in (distribution(rows), building_distribution(brows)):
        for name, x in d.items():
            print(f"  {name:22} {x['with_text']:4} uses, {x['distinct']:3} distinct, commonest {x['top_count']:3} "
                  f"({x['top_share']:.1%}): {str(x['top'])[:60]}")
    kinds = Counter(json.loads(r["facts_used_json"])["catch_kind"] for r in rows)
    print(f"catch kinds: {dict(kinds.most_common())}")


if __name__ == "__main__":
    main()
