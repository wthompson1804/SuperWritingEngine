#!/usr/bin/env python3
"""Tests for scripts/realtor_lines.py.

Run from the house-hunt folder:  python3 scripts/test_realtor_lines.py     (or: python3 -m pytest scripts/test_realtor_lines.py)

THE PLAIN-LANGUAGE GUARDS are not written here. They are imported from scripts/check_scene_text.py, the checker of
the experience and neighborhood text, so the apartment and building text is held to the same standard as the rest of
the page and the two cannot drift apart:
    check_plain   CONCEITS (the constructions the copy edit of 2026-11-16 removed: a thing acting on "you", "where the
                  car sleeps", template seams such as "then the practical side" / "count on about" / "then there is"),
                  VOCAB ("unit", "place" for an apartment, "all-in" / "all in", "everything included", "Mom and Dad", British spelling, "we found"),
                  INTERNAL (ranked, scorecard, verified, live check, net-effective, gate, asterisk, cap, ceiling),
                  FIGURE (at most one figure-of-speech marker per text) and the readability limits
                  (sentences average at most 20 words, none over 32)
    BANNED        dashes, question marks, "not X but Y", wording about race or religion, listing-ad hype
    CRIME         no crime or safety wording at all
    NUMBER_WORDS  no spelled-out quantities
    STAGE         no host on screen ("I", "let me", "your host")
EXTRA below is stricter still for this text: no "unit" in any form, no narrator ("we", "our", "us"), and the template
connectives the owner's editor flagged in the old lines ("Add ...", "Note ... as well", "the rest of the story").
`guard()` runs all of it. It is applied to EVERY sentence in the libraries and to EVERY generated line, catch,
subhead, About sentence and icon point for everything in site/data.json.

Also covered: what sets an apartment apart inside its building; the catch (a reason is stated only when the
apartment's own fields give it); "About the building"; unknowns never stated as fact; an open dog policy never yields
"dogs are allowed"; no number that is not in the apartment's or building's fields (after the page's rounding);
"a month with utilities and fees" on the first monthly total of a text, "rent" for what the listing asks; stability across reruns; length limits; and
that the two CSVs on disk have exactly the page's apartments and buildings.

REPETITION. Variety matters less than clarity, so the limit is deliberately loose: no lead wording, catch wording,
subhead or building sentence may be on more than 8% of the rows (R.SHARE; it was 4% and 5% before the copy edit, and
chasing it is where the odd lines came from). The price-and-size sentence, the icon points and the warning are plain
facts in fixed words and are not counted. What must differ is what sits side by side: the first three apartments of a
building lead with different facts and none reads the same as another, and the first three buildings of a
neighborhood do not read identically.
"""
import copy
import csv
import itertools
import json
import re
import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_scene_text as G  # noqa: E402   the guards of the experience and neighborhood text
import realtor_lines as R  # noqa: E402

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
# Stricter than the scene-text checker, for wording the owner's editor flagged in the old apartment and building lines.
EXTRA = [
    (re.compile(r"\bunits?\b", re.I), "'unit' (say 'apartment')"),
    (re.compile(r"\b(we|we're|we've|our|ours|us)\b", re.I), "a narrator ('we', 'our')"),
    (re.compile(r"\ball in\b|\ball-in\b", re.I), "'all in' (say 'with utilities and fees')"),
    (re.compile(r"\beverything(?: is)? included\b", re.I), "'everything included' (say 'with utilities and fees')"),
    (re.compile(r"\bheadroom\b|\bcushion\b|\bbudget pick\b|\bwallet\b", re.I), "budget jargon or a joke"),
    (re.compile(r"^(add|note|count|figure|expect|budget|call it|set aside|round it)\b|\bas well\.$|\bbesides\.$|"
                r"\bthe practical side\b|\bthe rest of the story\b|\bon top of that\b|\bbeyond that\b|\bthe plain facts\b|"
                r"\bthe numbers:", re.I), "a template connective"),
    (re.compile(r"\bcircle the block\b|\bfavorite\b|\byes, you would\b|\bfor the tour to show\b|"
                r"\bforgotten ingredient\b|\byour own door\b|\bdangling\b|\bbaked in\b|\bfine print\b|\bloose ends?\b",
                re.I), "one of the cut jokes or figures"),
    (re.compile(r"\bdogs are welcome\b", re.I), "'dogs are welcome' (say 'dogs are allowed', and only when they are)"),
    (re.compile(r"\byears?\b", re.I), "'year' (experiences are not years; a building's year is 'built in')"),
]
HEDGE = re.compile(r"\b(may|might|perhaps|probably|possibly|somewhat|fairly|arguably|seems?)\b", re.I)


def guard(text, masked=None):
    """Every plain-language and house-style fault in one text -> list of messages (empty = clean). `masked` is the
    same text with names from the data (a park, a station, a supermarket) replaced, so a name cannot trip a rule."""
    bare = masked if masked is not None else text
    out = G.check_plain("text", bare)
    for rx, what in G.BANNED + EXTRA:
        m = rx.search(bare)
        if m:
            out.append(f"{what}: '{m.group(0)}'")
    m = G.CRIME.search(bare) or re.search(r"\bsafe\w*", bare, re.I)
    if m:
        out.append(f"crime or safety wording '{m.group(0)}'")
    m = G.NUMBER_WORDS.search(bare)
    if m:
        out.append(f"spelled-out quantity '{m.group(0)}'")
    m = G.STAGE.search(bare)
    if m:
        out.append(f"stage business '{m.group(0)}'")
    return out


def sentences(text):
    return G.sentences(text)


def unit(uid, hood="xx:test", building=None, **over):
    """A complete synthetic apartment with nothing remarkable about it; `over` replaces top-level keys. By default
    every apartment is its own building."""
    u = {
        "id": uid, "hood_id": hood, "building_id": building or "b-" + uid, "beds": 1, "sqft": 700.0, "floor": 3.0,
        "floor_basis": "confirmed", "available": "now",
        "rent": {"listed": 2300, "gross": 2300, "basis_kind": "listed", "asterisk": False, "needs_call": False,
                 "free_months": None, "lease_months": 12.0, "offer_text": None},
        "all_in": 2500, "all_in_unknown": [],
        "elevator": {"value": "yes", "listing_site_only": False},
        "dog": {"allowed": "yes", "weight_limit_lb": None, "pet_rent": 50.0, "size_note": None},
        "parking": {"type": "garage: garage, $150/mo", "rank": 4.0, "fee": 150.0, "fee_note": "single price stated"},
        "amenities": {"pool": None, "doorman": None, "gym": None, "in_unit_laundry": None, "dog_amenities": None},
        "moments": {"wake": {"park": "Test Park", "park_walk_min": 9.0, "dog_park": "Test Dog Run", "dog_park_m": 2500},
                    "after": {"restaurants_800m": 6}, "night": {"violent_per_1000": 2.0},
                    "sun": {"drive_min": 40.0}},
        "scores": {"hood_rank": 1.0, "parts": {"safety": 60, "building": 55, "cost": 50, "car": 70, "space": 45,
                                                 "distance": 30, "dog": 40, "daily": 35}},
        "confirm": {"asterisk": False, "what": None, "why": None, "question": None},
        "cost_check": {"cap_margin": 500, "unknown_count": 0, "lease_term_months": 12.0},
        "disclosures": [],
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(u.get(k), dict):
            u[k] = {**u[k], **v}
        else:
            u[k] = v
    return u


def run(units):
    return {r["listing_id"]: r for r in R.build(units)}


def buildings(units):
    return {r["building_id"]: r for r in R.build_buildings(units)}


def meta(row):
    return json.loads(row["facts_used_json"])


def cond(row):
    return meta(row)["pattern"].rsplit("_", 1)[0]


def catch_kind(row):
    return meta(row)["catch_kind"]


def points(row):
    return json.loads(row["about_points_json"])


def numbers(text):
    return [n.replace(",", "").rstrip(".") for n in NUMBER.findall(text)]


def names(u):
    return (R.get(u, "moments", "wake", "park"), R.get(u, "moments", "wake", "dog_park"),
            R.get(u, "moments", "sat", "train_station"), R.get(u, "moments", "work", "supermarket"))


def mask(text, u):
    """The text with the names taken from the data replaced by NAME (longest first)."""
    for name in sorted((str(n) for n in names(u) if n), key=lambda x: -len(x)):
        text = text.replace(name, "NAME").replace(re.sub(r"\s*\(.*?\)", "", name).strip(), "NAME")
    return text


def rent_line(u):
    """The page's "Rent": the amount of the rent line of the cost lines (site/index.html rentOf), in whole dollars."""
    for x in u.get("all_in_lines") or []:
        if isinstance(x, dict) and re.match(r"rent\b", str(x.get("line") or ""), re.I) and R.num(x.get("amount")) is not None:
            return int(round(R.num(x["amount"])))
    return None


def allowed_numbers(u, n_peers):
    """Every number a text about this apartment or its building may contain, worked out from the fields without
    using the generator's own templates: its figures as the page rounds them in a sentence (prices and sizes to the
    nearest 10), her limit and what is left under it, the size of the group it is compared with, fixed wordings."""
    ok = {str(n) for n in n_peers} | {"10", "12", str(R.CAP)}             # "10-minute walk", "12-month lease", her limit
    if u.get("beds") == 1 or u.get("beds") is None:
        ok.add("1")                                           # "1-bedroom"

    def put(x, rounded=False):
        v = R.num(x)
        if v is not None:
            ok.add(str(R.round10(v)) if rounded else str(int(round(v))))
            if not rounded:
                ok.add(f"{v:.1f}")
    for path in (("all_in",), ("sqft",), ("cost_check", "cap_margin")):
        put(R.get(u, *path), rounded=True)
    if rent_line(u) is not None:
        ok.add(str(rent_line(u)))                             # "The rent is $2,345": exact, as the page prints it
    if R.num(u.get("all_in")) is not None:
        ok.add(str(R.CAP - R.round10(u["all_in"])))           # "about $520 under your $3,000 limit"
    for path in (("floor",), ("parking", "fee"), ("rent", "free_months"), ("rent", "lease_months"),
                 ("cost_check", "lease_term_months"), ("moments", "wake", "park_walk_min"),
                 ("moments", "after", "restaurants_800m"), ("amenities", "year_built"), ("dog", "weight_limit_lb")):
        put(R.get(u, *path))
    for path in (("moments", "wake", "dog_park_m"), ("moments", "sat", "train_station_m"),
                 ("moments", "work", "supermarket_m")):
        v = R.num(R.get(u, *path))
        if v is not None:
            ok.add(R.miles(v))
    if "24h" in (R.get(u, "amenities", "doorman"), R.get(u, "amenities", "concierge"), R.get(u, "amenities", "front_desk")):
        ok.add("24")                                          # "staffed 24 hours a day"
    try:
        ok.add(str(date.fromisoformat(str(u.get("available"))[:10]).day))
    except ValueError:
        pass
    for k in ("income_requirement", "credit_score_requirement"):      # a condition quoted from the listing (D8)
        ok.update(numbers(str(R.get(u, "conditions", k) or "")))
    for text in names(u):                                     # a name quoted from the data
        ok.update(numbers(str(text or "")))
    for o in R.get(u, "parking", "optional_kinds") or []:     # "garage spaces are $125 a month": the other kind's own fee
        if isinstance(o, dict):
            put(o.get("fee"))
    return ok


FILL = {"n": 5, "low": "lowest", "big": "largest", "high": "highest", "least": "the least", "most": "the most",
        "floor": 6, "date": "December 1", "sqft": "610", "price": "$2,780", "rent": "$2,455", "gap": "about $220 under your $3,000 limit",
        "limit": "$3,000", "free": "1 month", "this_kind": "this studio", "This_kind": "This studio",
        "Type_sentence": "This is a studio.", "months": 15, "names": "building fees and the parking fee",
        "Names": "Building fees and the parking fee", "are": "are", "them": "them", "amounts": "amounts",
        "gtail": ", with the fee not published", "ptail": ", and the fee is not published", "dogthing": "dog park",
        "fee": "$150", "built": 2019, "Dogpark": "NAME", "dogpark_end": "NAME", "dogpark_mi": "0.3", "park": "NAME",
        "park_mins": "4 minutes", "rest": "31", "w10": R.WALK_RADIUS, "station": "NAME", "Station": "NAME",
        "station_mi": "0.4", "market": "NAME", "market_mi": "0.2", "Rest_few": "6 restaurants are",
        "Rest_count": "About 31 restaurants are", "Apts_listed": "5 apartments are listed", "lb": "50",
        "parking": "garage", "income": "3x the rent in household income", "credit": "700+",
        "Incl": "A garage space", "incl": "a garage space", "Lot_space": "A space in the open lot",
        "lot_space": "a space in the open lot", "extra": "; garage spaces cost extra", "where": "in an off-site deck",
        "parking_point": "A free open lot; garage spaces cost extra."}


def families():
    """Every (family name, [sentences]) in the libraries."""
    for c, (_, texts) in R.LEADS.items():
        yield "lead:" + c, texts
    for name, texts in R.SECOND.items():
        yield "second:" + name, texts
    for name, texts in R.SECOND_RENT.items():
        yield "second_rent:" + name, texts
    for c, (_, _, texts) in R.BUILDING.items():
        yield "building:" + c, texts
    for kind, texts in R.CATCHES.items():
        yield "catch:" + kind, texts
    for section, entries in R.SUBS.items():
        for key, texts in entries:
            yield f"sub:{section}.{key}", texts
    for key, (_, _, text) in R.POINTS.items():
        yield "point:" + key, [text]
    for key, (_, text) in R.WARNINGS.items():
        yield "point:warning." + key, [text]


def page_units():
    return json.loads(R.DATA.read_text(encoding="utf-8"))["units"] if R.DATA.exists() else None


class Library(unittest.TestCase):
    def test_every_sentence_passes_the_plain_language_guards(self):
        n = 0
        for name, texts in families():
            self.assertTrue(texts, name)
            self.assertEqual(len(set(texts)), len(texts), f"{name}: a sentence appears twice")
            for t in texts:
                filled = t.format(**FILL)
                self.assertEqual(guard(filled), [], f"{name}: {filled}")
                n += 1
        self.assertGreater(n, 250)

    def test_the_guards_catch_what_the_copy_edit_removed(self):
        # the lines the owner's editor flagged must fail, or the guards are not guarding
        for bad in ("About $1,297 of headroom under your cap, on an all-in of about $1,703 a month.",
                    "The price shown is a net-effective rent, so ask for the gross rent.",
                    "We owe this listing a fresh check, and until then the rent and date are provisional.",
                    "No other apartment we found in this building comes in under this one.",
                    "The washer and dryer are in the unit.",
                    "Where the car sleeps is unanswered, so ask before the tour.",
                    "Your car sleeps indoors, and you never circle the block.",
                    "Then the practical side: about $1,967 a month all in, with 614 square feet.",
                    "Then there is 554 square feet.", "Count on about $2,044 a month all in.", "Add 773 square feet.",
                    "Note 725 square feet as well.", "There is a pool, and yes, you would use it.",
                    "Your wallet's favorite of the 2 here.", "Your own machines, inside your own door.",
                    "It is 0.2 miles to Seabra Foods, which makes a forgotten ingredient a small problem.",
                    "What is around the door is for the tour to show you.", "Dogs are welcome with no weight limit.",
                    "This sits near your ceiling.", "The scorecard ranked this first.", "Is it still available?",
                    "The neighbourhood is low on crime."):
            self.assertNotEqual(guard(bad), [], f"the guards let this through: {bad}")

    def test_lengths_and_shapes(self):
        for name, texts in families():
            for t in texts:
                n = len(sentences(t.format(**FILL)))
                if name.startswith(("lead:", "second:", "building:", "sub:", "point:")):
                    self.assertEqual(n, 1, f"{name}: one sentence wanted: {t}")
                if name.startswith("catch:"):
                    self.assertIn(n, (1, 2), f"{name}: one or two sentences wanted: {t}")
                if name.startswith(("sub:", "point:")):
                    self.assertLessEqual(len(t.split()), 14, t)
                if name.startswith("sub:"):
                    self.assertNotRegex(t, r"\d", t)
                    self.assertIsNone(HEDGE.search(t), t)

    def test_no_typed_numbers(self):
        # the only digits typed in the libraries are fixed wordings: a 12-month lease, a 24-hour desk, a 1-bedroom
        for name, texts in families():
            for t in texts:
                bare = re.sub(r"\{[A-Za-z_0-9]+\}", "", t)
                for fixed in ("12-month", "24 hours", "1-bedroom"):
                    bare = bare.replace(fixed, "")
                self.assertNotRegex(bare, r"\d", f"{name}: {t}")

    def test_a_monthly_total_always_says_with_utilities_and_fees(self):
        for name, texts in families():
            for t in texts:
                self.assertNotRegex(t, r"(?i)everything included|\ball[- ]in\b", f"{name}: {t}")
                if "{price}" in t:
                    self.assertRegex(t, r"about \{price\} a month with utilities and fees", f"{name}: {t}")
                if "{rent}" in t:                         # what the listing asks is called rent, and is not "about"
                    self.assertRegex(t, r"\b[Rr]ent is \{rent\}", f"{name}: {t}")

    def test_the_line_gives_the_rent_and_the_total_where_the_rent_is_plain(self):
        lines = [{"line": "rent (as listed)", "amount": 2345.0, "code": "rent_listed"}, {"line": "pet rent", "amount": 50}]
        base = {"all_in": 2672, "all_in_lines": lines, "cost_check": {"cap_margin": 328}}
        u = unit("a", **base)
        line = run([u])["a"]["host_line"]
        self.assertRegex(line, r"[Rr]ent is \$2,345[,;] about \$2,670 a month with utilities and fees")
        self.assertEqual(guard(line), [])
        # an offer, an open question on the rent, a 12-month or after-offer price: the total alone
        for change in ({"rent": {"asterisk": True}}, {"rent": {"needs_call": True}}, {"rent": {"basis_kind": "net_effective"}},
                       {"all_in_lines": [{"line": "rent (12-month lease)", "amount": 2345.0, "code": "rent_12_month"}]},
                       {"disclosures": [{"what": "special offer"}]}, {"all_in_lines": []}):
            line = run([unit("a", **{**base, **change})])["a"]["host_line"]
            self.assertNotRegex(line, r"(?i)\brent is\b", change)
            self.assertIn("about $2,670 a month with utilities and fees", line)

    def test_the_guard_wants_each_monthly_price_named(self):
        self.assertEqual(guard("It costs about $2,670 a month with utilities and fees."), [])
        self.assertEqual(guard("The rent is $2,345, about $2,670 a month with utilities and fees."), [])
        for bad in ("It costs about $2,670 a month.", "It costs about $2,670 a month, everything included.",
                    "It costs about $2,670 a month all-in.", "About $2,670 a month all in, with parking.",
                    "It costs about $2,670 a month with utilities and fees, or about $2,700 a month with utilities and fees."):
            self.assertNotEqual(guard(bad), [], bad)
        self.assertEqual(guard("It costs about $2,670 a month with utilities and fees, or about $2,700 a month with a space."), [])

    def test_unpriced_parking_sentences_say_the_fee_is_missing(self):
        for t in R.BUILDING["garage_unpriced"][2]:
            self.assertRegex(t, R.UNPRICED, t)
            self.assertNotRegex(t.lower(), r"free|included")
        for head in ("garage: x", "covered: x", "lot: x", "assigned: x", "offsite: x"):
            pt = R.parking_point(R.parking_facts({"parking": {"type": head, "fee": None}}))
            self.assertRegex(pt.lower(), r"not published", head)
            self.assertNotRegex(pt.lower(), r"free|included", head)
        self.assertRegex(R.parking_point(R.parking_facts({"parking": {"type": "parking", "fee": None}})), r"without saying what kind")
        for key in ("parking_fee", "parking_assigned"):
            self.assertRegex(R.WARNINGS[key][1], r"not published")

    def test_icons_are_from_the_fixed_set(self):
        for key, (icon, _, _) in R.POINTS.items():
            self.assertIn(icon, R.ICONS, key)
            self.assertNotEqual(icon, "warning", key)

    def test_an_open_dog_policy_is_never_called_allowed(self):
        yes = r"small dogs are allowed|dogs are allowed[.,]|dogs are welcome|takes dogs|dog-friendly"
        asked = lambda t: re.sub(r"(not confirmed that|whether) dogs are allowed", "", t.lower())   # asking is not stating
        for key in ("conflicting", "unsettled"):
            for t in dict(R.SUBS["dog"])[key]:
                self.assertNotRegex(asked(t), yes, t)
        for kind, texts in R.CATCHES.items():
            if kind.startswith("confirm:dogs"):
                for t in texts:
                    self.assertNotRegex(asked(t), yes, t)
                    if kind != "confirm:dogs conflict":       # a reason needs its field
                        self.assertNotRegex(t.lower(), r"disagree|do not agree|conflict|contradict", t)
        self.assertNotRegex(asked(R.WARNINGS["dog_unsettled"][1]), yes)

    def test_only_the_after_offer_family_says_the_price_includes_the_offer(self):
        claim = r"price shown includes|lowers (this|the) price|price includes a special|lower than a normal month"
        for name, texts in families():
            for t in texts:
                if name in ("catch:rent:net_effective", "sub:cost.net_effective"):
                    self.assertNotRegex(t.lower(), r"net.effective|gross", t)     # said in plain words
                else:
                    self.assertNotRegex(t.lower(), claim, f"{name}: {t}")


class UnitLine(unittest.TestCase):
    def test_an_apartment_is_compared_with_the_apartments_of_its_own_building(self):
        us = [unit("a", building="B", all_in=2100, scores={"hood_rank": 2.0}),
              unit("b", building="B", all_in=2600, scores={"hood_rank": 1.0}),
              unit("c", building="B", all_in=2700, scores={"hood_rank": 3.0}),
              unit("z", building="Z", all_in=1900, scores={"hood_rank": 4.0})]      # cheaper, but another building
        peers = [R.facts(u) for u in us[:3]]
        conds = {c[1] for c in R.lead_conditions(peers[0], peers)}
        self.assertIn("cheapest", conds)
        alone = {c[1] for c in R.lead_conditions(R.facts(us[3]), [R.facts(us[3])])}
        self.assertFalse(alone & R.PEER_CONDITIONS)                 # alone in its building: no comparison at all

    def test_the_line_gives_the_total_rounded_with_utilities_and_fees(self):
        us = [unit("a", building="B", all_in=2104, sqft=613.0, scores={"hood_rank": 2.0}),
              unit("b", building="B", all_in=2600, scores={"hood_rank": 1.0}),
              unit("c", building="B", all_in=2700, scores={"hood_rank": 3.0})]
        line = run(us)["a"]["host_line"]
        self.assertIn("about $2,100 a month with utilities and fees", line)
        self.assertIn("about 610 square feet", line)
        self.assertNotIn("2,104", line)

    def test_two_figures_in_one_sentence_add_up_to_her_limit(self):
        f = R.facts(unit("a", all_in=2705, cost_check={"cap_margin": 295}))
        self.assertEqual(R.price_words(f), ("$2,710", "about $290 under your $3,000 limit"))
        f = R.facts(unit("a", all_in=2998, cost_check={"cap_margin": 2}))
        self.assertEqual(R.price_words(f), ("$3,000", "at your $3,000 limit"))

    def test_biggest_highest_value_soonest(self):
        us = [unit("a", building="B", sqft=950.0, all_in=2600, scores={"hood_rank": 2.0}),
              unit("b", building="B", sqft=500.0, all_in=2000, scores={"hood_rank": 3.0}),
              unit("c", building="B", sqft=800.0, all_in=2100, floor=9.0, available="2026-12-01", scores={"hood_rank": 4.0}),
              unit("d", building="B", sqft=600.0, all_in=2460, available="2026-12-05")]
        peers = [R.facts(u) for u in us]
        got = lambda i: {c[1] for c in R.lead_conditions(peers[i], peers)}
        self.assertIn("biggest", got(0))
        self.assertIn("cheapest", got(1))
        self.assertLessEqual({"highest", "value"}, got(2))
        self.assertNotIn("soonest_date", got(2))                    # two apartments are available now

    def test_a_tie_is_not_called_the_best(self):
        us = [unit("a", building="B"), unit("b", building="B", scores={"hood_rank": 2.0})]      # identical
        for r in run(us).values():
            self.assertNotIn(cond(r), R.PEER_CONDITIONS)

    def test_a_superlative_needs_every_apartment_to_publish_the_figure(self):
        us = [unit("a", building="B", sqft=950.0), unit("b", building="B", sqft=700.0, scores={"hood_rank": 2.0}),
              unit("c", building="B", sqft=None, scores={"hood_rank": 3.0})]
        peers = [R.facts(u) for u in us]
        conds = {c[1] for c in R.lead_conditions(peers[0], peers)}
        self.assertNotIn("biggest", conds)
        self.assertNotIn("value", conds)

    def test_the_building_is_not_described_in_the_apartment_line(self):
        rich = dict(amenities={"pool": "pool", "doorman": "24h", "gym": "yes", "in_unit_laundry": "yes",
                               "dog_amenities": "dog park"})
        for salt in range(20):
            row = run([unit(f"a{salt}", **rich)])[f"a{salt}"]
            self.assertNotRegex(row["host_line"].lower(), r"pool|doorman|front desk|gym|garage|parking|dog park|washer")

    def test_rerun_gives_the_same_text(self):
        us = [unit(f"u{i}", building="B" if i < 4 else None, scores={"hood_rank": float(i + 1)}, all_in=2400 + 10 * i)
              for i in range(6)]
        self.assertEqual(R.build(copy.deepcopy(us)), R.build(copy.deepcopy(us)))
        self.assertEqual(R.build(us), R.build(list(reversed(us))))            # input order does not matter
        self.assertEqual(R.build_buildings(us), R.build_buildings(list(reversed(us))))

    def test_unknown_size_and_floor_are_left_out(self):
        u = unit("a", sqft=None, floor=None, floor_basis="unknown")
        line = run([u])["a"]["host_line"].lower()
        self.assertNotIn("square feet", line)
        self.assertNotIn("floor", line)

    def test_an_inferred_floor_is_not_stated_as_fact(self):
        us = [unit("a", building="B", floor=12.0, floor_basis="inferred"), unit("b", building="B", scores={"hood_rank": 2.0})]
        self.assertNotIn("floor", run(us)["a"]["host_line"].lower())

    def test_missing_cost_prints_no_price(self):
        u = unit("a", all_in=None, cost_check={"cap_margin": None})
        line = run([u])["a"]["host_line"]
        self.assertNotIn("$", line)
        self.assertNotIn("a month", line)

    def test_a_lead_does_not_repeat_the_catch(self):
        special = {"asterisk": True, "needs_call": True, "free_months": "2"}
        for salt in range(20):
            row = run([unit(f"a{salt}", rent=special)])[f"a{salt}"]
            self.assertEqual(catch_kind(row), "rent:needs_call")
            self.assertNotEqual(cond(row), "concession", row["host_line"])


class Catch(unittest.TestCase):
    def dog(self, why, **dog):
        ask = {"asterisk": True, "what": "dogs allowed", "why": why, "question": "Are dogs allowed?"}
        return unit("a", confirm=ask, dog=dog or {})

    def test_sources_disagree_only_when_the_open_item_says_so(self):
        row = run([self.dog("Two listing sites disagree on whether dogs are allowed, and the building's own page does not settle it.")])["a"]
        self.assertEqual(catch_kind(row), "confirm:dogs conflict")
        for why, kind, word in (
                ("Dogs are not confirmed as allowed here: dogs are not named as allowed ('upon approval')", "approval", "upon approval"),
                ("A condo where pets are considered case by case, so dogs are not explicitly allowed.", "case", "case by case"),
                ("dogs are not named as allowed (the only policy text is 'contact for more information on pet policy')", "contact", "contact the office"),
                ("The listing says only 'small pets allowed'; dogs are not named.", "small pets", "small pets"),
                ("Dogs are allowed only according to a listing site's pet data; there is no policy text.", "no text", "no policy text")):
            for salt in range(4):
                u = self.dog(why)
                u["id"] = f"a{salt}"
                row = run([u])[f"a{salt}"]
                self.assertEqual(catch_kind(row), "confirm:dogs " + kind, why)
                self.assertIn(word, row["host_catch"].lower())
                self.assertNotRegex(row["host_catch"].lower(), r"disagree|do not agree|conflict|contradict")

    def test_an_open_dog_item_with_no_stated_reason_asserts_none(self):
        row = run([self.dog("Not settled.")])["a"]
        self.assertEqual(catch_kind(row), "confirm:dogs open")
        self.assertNotRegex(row["host_catch"].lower(), r"disagree|do not agree|approval|case by case|small pets")

    def test_nothing_says_dogs_are_allowed_while_dogs_are_open(self):
        u = self.dog("The listing says only 'small pets allowed'; dogs are not named.",
                     size_note="page says small dogs; no weight number")
        row = run([u])["a"]
        self.assertEqual(meta(row)["subs"]["dog"], "unsettled")
        b = buildings([u])["b-a"]
        self.assertEqual(json.loads(b["facts_used_json"])["warning"], "dog_unsettled")
        everything = " ".join([row["host_line"], row["sub_dog"], b["about_building"]] +
                              [p["text"] for p in points(b) if p["icon"] != "warning"]).lower()
        self.assertNotRegex(everything.replace("not confirmed that dogs are allowed", ""),
                            r"dogs are allowed|small dogs are|welcome|takes dogs|friendly")

    def test_the_price_includes_an_offer_only_when_the_rent_block_says_so(self):
        special = {"basis_kind": "net_effective", "listed": 2300, "gross": 2600, "asterisk": True, "needs_call": True,
                   "offer_text": "2 months free on a 14-month lease; price shown is net effective"}
        row = run([unit("a", rent=special)])["a"]
        self.assertEqual(catch_kind(row), "rent:net_effective")
        self.assertEqual(meta(row)["subs"]["cost"], "net_effective")
        self.assertRegex(row["host_catch"].lower(), r"special offer")
        self.assertRegex(row["host_catch"].lower(), r"ask (what|for)")
        for change in ({"offer_text": "Gross or net-effective: not stated"}, {"basis_kind": "listed"}):
            row = run([unit("a", rent={**special, **change})])["a"]
            self.assertEqual(catch_kind(row), "rent:needs_call", change)
            self.assertEqual(meta(row)["subs"]["cost"], "ambiguous_rent", change)
            text = (row["host_catch"] + " " + row["sub_cost"]).lower()
            self.assertNotRegex(text, r"price shown includes|lowers (this|the) price|lower than a normal month", change)

    def test_the_open_item_comes_first_and_is_said_with_its_own_reason(self):
        u = unit("a", confirm={"asterisk": True, "what": "elevator", "why": "x", "question": "Does it have one?"},
                 rent={"asterisk": True, "needs_call": True})
        self.assertEqual(catch_kind(run([u])["a"]), "confirm:elevator")
        named = "An elevator is named for this property, but it is a low-rise or multi-building complex."
        u = unit("a", confirm={"asterisk": True, "what": "elevator", "why": named, "question": "q"})
        self.assertEqual(catch_kind(run([u])["a"]), "confirm:elevator named")
        for why, q, kind in (("The listing page was last changed on 8 July 2026.", "Is it still available?", "confirm:listing stale"),
                             ("This unit appears on one listing site only.", "Is it available?", "confirm:listing one site"),
                             ("The page describes another building.", "Which building is this unit in?", "confirm:listing which building"),
                             ("An open house is still advertised.", "Is it still available?", "confirm:listing")):
            u = unit("a", confirm={"asterisk": True, "what": "listing", "why": why, "question": q})
            row = run([u])["a"]
            self.assertEqual(catch_kind(row), kind, why)
            self.assertNotIn(q, row["host_catch"])                  # the open item's question is never pasted in
        u = unit("a", confirm={"asterisk": True, "what": "something new", "why": "x", "question": "Is it real?"})
        self.assertEqual(catch_kind(run([u])["a"]), "confirm:other")

    def test_a_floor_plan_is_called_one_only_when_the_open_item_says_so(self):
        u = unit("a", confirm={"asterisk": True, "what": "availability", "why": "Floor plan only: no unit, floor or date.",
                               "question": "Which unit?"})
        self.assertEqual(catch_kind(run([u])["a"]), "confirm:availability plan")
        u = unit("a", confirm={"asterisk": True, "what": "availability", "why": "Date unclear.", "question": "When is it free?"})
        row = run([u])["a"]
        self.assertEqual(catch_kind(row), "confirm:availability")
        self.assertNotRegex(row["host_catch"].lower(), r"floor plan|layout|plan type")

    def test_income_and_age_limits_need_the_open_item_to_say_so(self):
        for why, kind in (("Eligibility is not settled: INCOME-RESTRICTED per a listing tag.", "confirm:eligibility income"),
                          ("One of the communities at this address is for ages 55 and over.", "confirm:eligibility age"),
                          ("Who may apply is unclear.", "confirm:eligibility")):
            u = unit("a", confirm={"asterisk": True, "what": "eligibility", "why": why, "question": "q"})
            row = run([u])["a"]
            self.assertEqual(catch_kind(row), kind)
            self.assertNotIn("55", row["host_catch"])

    def test_the_floor_is_the_catch_when_nothing_else_is_open(self):
        row = run([unit("a", floor=None, floor_basis="unknown")])["a"]
        self.assertEqual(catch_kind(row), "floor:unpublished")
        row = run([unit("a", floor=6.0, floor_basis="inferred")])["a"]
        self.assertEqual(catch_kind(row), "floor:inferred")
        self.assertIn("6", numbers(row["host_catch"]))

    def test_unpublished_costs_that_could_pass_her_limit(self):
        u = unit("a", all_in_unknown=["building fees", "parking fee"], cost_check={"cap_margin": 120}, all_in=2880,
                 parking={"type": "garage: fee not stated", "fee": None, "fee_note": ""})
        row = run([u])["a"]
        self.assertEqual(catch_kind(row), "costs:could_pass")
        self.assertRegex(row["host_catch"], r"[Bb]uilding fees and the parking fee")
        self.assertIn("$3,000 limit", row["host_catch"])
        u["disclosures"] = [{"what": "could pass $3,000"}]
        u["cost_check"]["cap_margin"] = 400                          # the page's own disclosure is enough
        self.assertEqual(catch_kind(run([u])["a"]), "costs:could_pass")
        u["parking"] = {"type": None, "fee": None, "fee_note": None}   # parking itself unknown: not "the parking fee"
        self.assertNotIn("the parking fee", run([u])["a"]["host_catch"])

    def test_lease_term_dog_weight_and_condo_come_from_the_disclosures(self):
        row = run([unit("a", cost_check={"lease_term_months": 15.0}, rent={"lease_months": 15.0})])["a"]
        self.assertEqual(catch_kind(row), "lease_term")
        self.assertIn("15", numbers(row["host_catch"]))
        row = run([unit("a", disclosures=[{"what": "dog weight limit not published"}])])["a"]
        self.assertEqual(catch_kind(row), "dog_weight")
        row = run([unit("a", disclosures=[{"what": "condo rented by its owner"}])])["a"]
        self.assertEqual(catch_kind(row), "condo")

    def test_small_or_dear_is_said_only_when_it_is_plainly_so(self):
        u = unit("a", scores={"hood_rank": 1.0, "parts": {"safety": 1, "distance": 2, "space": 45, "cost": 50}})
        self.assertEqual(catch_kind(run([u])["a"]), "none")          # 700 square feet is not small: nothing is claimed
        self.assertEqual(catch_kind(run([dict(u, sqft=480.0)])["a"]), "weak:space")
        u = unit("a", all_in=2950, cost_check={"cap_margin": 50},
                 scores={"hood_rank": 1.0, "parts": {"space": 80, "cost": 5}})
        row = run([u])["a"]
        self.assertEqual(catch_kind(row), "weak:cost")
        self.assertIn("about $2,950 a month with utilities and fees", row["host_catch"])
        self.assertIn("about $50 under your $3,000 limit", row["host_catch"])

    def test_every_catch_on_the_page_that_gives_a_reason_has_it_in_the_apartments_fields(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        by_id = {u["id"]: u for u in units}
        for r in R.build(units):
            u, m = by_id[r["listing_id"]], meta(r)
            family = m["catch_id"].rsplit("_", 1)[0]
            self.assertEqual(family, m["catch_kind"])
            if family in R.CATCH_BASIS:
                self.assertTrue(R.CATCH_BASIS[family](u), f"{r['listing_id']}: '{r['host_catch']}' has no basis in the apartment")
            text = r["host_catch"].lower()
            why = str(R.get(u, "confirm", "why") or "").lower()
            if "dog" in text and re.search(r"disagree|do not agree", text):
                self.assertRegex(why, r"disagree|and another says", r["listing_id"])
            for phrase, need in (("upon approval", "approval"), ("case by case", "case by case"),
                                 ("contact the office", "contact"), ("small pets", "small pets"),
                                 ("income", "income"), ("floor plan", "plan"), ("older residents", "55")):
                if phrase in text and family.startswith("confirm:"):
                    self.assertIn(need, why, f"{r['listing_id']}: {r['host_catch']}")
            if re.search(r"price shown includes|lowers (this|the) price|lower than a normal month",
                         text + " " + r["sub_cost"].lower()):
                self.assertTrue(R.net_effective(u), f"{r['listing_id']}: an after-offer price said without the rent block's word")
            if R.dog_open(u):                                         # dogs are the open item
                self.assertIn(m["subs"]["dog"], ("conflicting", "unsettled"), r["listing_id"])
                if m["subs"]["dog"] == "conflicting":
                    self.assertTrue(R.dog_open(u) == "conflict" or R.get(u, "dog", "allowed") == "conflicting", r["listing_id"])


class FloorAndElevator(unittest.TestCase):
    """Owner, 2026-11-17 (second trawl): a walk-up on floor 2 (elevator.walkup_floor_2) and the open item 'floor and
    elevator' (code floor_or_elevator). Synthetic apartments of each kind."""
    WALK = {"value": "", "listing_site_only": False, "walkup_floor_2": True, "rule": "floor_2", "words": "A single flight up, no elevator needed"}

    def test_the_open_item_floor_and_elevator(self):
        ask = {"asterisk": True, "what": "floor and elevator", "label": "the floor, and whether there is an elevator",
               "why": "No page we read gives the floor or says the building has an elevator.", "question": "Which floor?", "code": "floor_or_elevator"}
        row = run([unit("a", floor=None, floor_basis="unknown", elevator={"value": "", "walkup_floor_2": False}, confirm=ask)])["a"]
        self.assertEqual(catch_kind(row), "confirm:floor and elevator")
        self.assertRegex(row["host_catch"], r"floor")
        self.assertRegex(row["host_catch"], r"elevator")
        self.assertEqual(guard(row["host_catch"]), [], row["host_catch"])
        self.assertNotRegex(row["host_line"] + " " + row["host_catch"], r"The building has an elevator")

    def test_a_walkup_on_floor_2_stated(self):
        us = [unit("a", building="W", floor=2.0, floor_basis="stated", elevator=self.WALK, scores={"hood_rank": 1.0}),
              unit("b", building="W", floor=2.0, floor_basis="stated", elevator=self.WALK, scores={"hood_rank": 2.0}, sqft=650.0)]
        rows = run(us)
        for r_ in rows.values():
            self.assertNotRegex(r_["host_line"] + " " + r_["host_catch"], r"The building has an elevator")
        b = buildings(us)["W"]
        text = b["about_building"] + " " + " ".join(p["text"] for p in points(b))
        self.assertNotIn("The building has an elevator.", text)
        self.assertNotIn("the elevator and the mail room", text)
        # the plain fact, when the floor is the lead
        f = R.facts(us[0])
        self.assertTrue(f["walkup"] and not f["elevator_sure"])

    def test_a_walkup_with_an_elevator_named_in_doubt_never_claims_it(self):
        doubt = dict(self.WALK, value="yes")
        us = [unit("a", building="D", floor=2.0, floor_basis="stated", elevator=doubt)]
        b = buildings(us)["D"]
        self.assertNotIn("The building has an elevator.", b["about_building"] + " " + " ".join(p["text"] for p in points(b)))

    def test_a_walkup_floor_read_from_the_number(self):
        row = run([unit("a", floor=2.0, floor_basis="inferred", elevator=self.WALK)])["a"]
        self.assertEqual(catch_kind(row), "floor:walkup inferred")
        self.assertIn("single flight up", row["host_catch"])
        self.assertIn("2", numbers(row["host_catch"]))
        self.assertEqual(guard(row["host_catch"]), [], row["host_catch"])

    def test_an_elevator_building_is_unaffected(self):
        row = run([unit("a", floor=6.0, floor_basis="inferred")])["a"]
        self.assertEqual(catch_kind(row), "floor:inferred")
        f = R.facts(unit("e", building="E"))
        self.assertTrue(f["elevator_sure"] and not f["walkup"])
        self.assertEqual(R.building_warning(R.building_facts([unit("e", building="E", dog={"pet_rent": 50.0})])), "tour")


class Subheads(unittest.TestCase):
    COLS = ("sub_cost", "sub_parking", "sub_dog", "sub_building")

    def test_unknown_parking_gets_an_ask_line(self):
        row = run([unit("a", parking={"type": None, "fee": None, "fee_note": None})])["a"]
        self.assertRegex(row["sub_parking"].lower(), r"\bask\b")
        self.assertNotRegex(row["sub_parking"].lower(), r"garage|indoors|free|included")

    def test_unpriced_garage_says_the_price_is_missing(self):
        row = run([unit("a", parking={"type": "garage: fee not stated", "fee": None, "fee_note": ""})])["a"]
        ask = r"\bask\b|in writing|not published|does not give"
        self.assertRegex(row["sub_parking"].lower(), ask)
        for t in dict(R.SUBS["parking"])["garage_unpriced"]:
            self.assertRegex(t.lower(), ask, t)

    def test_priced_garage_included_space_and_street(self):
        self.assertEqual(meta(run([unit("a")])["a"])["subs"]["parking"], "garage_priced")
        inc = unit("a", parking={"type": "lot: assigned", "fee": 0.0, "fee_note": "a spot is included or free: assigned"})
        self.assertEqual(meta(run([inc])["a"])["subs"]["parking"], "included_lot")   # the included space, by its kind
        street = unit("a", parking={"type": "street_only", "fee": None, "fee_note": ""})
        self.assertEqual(meta(run([street])["a"])["subs"]["parking"], "street")       # never "on-site parking"
        b = buildings([street])["b-a"]
        self.assertNotRegex(b["about_building"].lower(), r"garage|parking lot|on-site")

    def test_unknown_pet_rent(self):
        row = run([unit("a", dog={"allowed": "yes", "weight_limit_lb": None, "pet_rent": None})])["a"]
        self.assertRegex(row["sub_dog"].lower(), r"\bask\b")

    def test_nothing_distinctive_stays_empty(self):
        row = run([unit("a", cost_check={"cap_margin": 250})])["a"]      # known pet rent, no amenities, mid budget
        self.assertEqual(row["sub_cost"], "")
        self.assertEqual(row["sub_dog"], "")
        self.assertEqual(row["sub_building"], "")

    def test_the_best_apartment_of_each_building_is_served_first(self):
        # the page shows the subheads of a building's best apartment: it gets one even when a wording runs out
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        rows = run(units)
        best = {}
        for u in sorted(units, key=R.rank_key):
            best.setdefault(u.get("building_id") or u["id"], u)
        for u in best.values():
            for section, key in meta(rows[u["id"]])["subs"].items():
                if key:
                    self.assertTrue(rows[u["id"]]["sub_" + section], f"{u['id']}: no {section} subhead for '{key}'")


class Building(unittest.TestCase):
    def check(self, units):
        by_b = {}
        for u in units:
            by_b.setdefault(u.get("building_id") or u["id"], []).append(u)
        hood_sizes = Counter()
        for g in by_b.values():
            hood_sizes[g[0].get("hood_id")] += 1
        rows = buildings(units)
        self.assertEqual(set(rows), set(by_b))
        for bid, group in by_b.items():
            r = rows[bid]
            top = min(group, key=R.rank_key)
            ok = allowed_numbers(top, (hood_sizes[top.get("hood_id")], len(group)))
            text = r["about_building"]
            self.assertLessEqual(len(text.split()), R.ABOUT_MAX_WORDS, text)
            self.assertIn(len(sentences(mask(text, top))), (1, 2), text)
            pts = points(r)
            self.assertTrue(R.POINTS_COUNT[0] <= len(pts) <= R.POINTS_COUNT[1], pts)
            self.assertEqual(sum(p["icon"] == "warning" for p in pts), 1, pts)
            self.assertEqual(len({p["text"] for p in pts}), len(pts), pts)
            for p in pts:
                self.assertEqual(set(p), {"icon", "text"})
                self.assertIn(p["icon"], R.ICONS)
                self.assertLessEqual(len(mask(p["text"], top).split()), R.POINT_MAX_WORDS, p["text"])
                self.assertEqual(len(sentences(mask(p["text"], top))), 1, p["text"])
            for t in [text] + [p["text"] for p in pts]:
                for n in numbers(t):
                    self.assertIn(n, ok, f"{bid}: '{n}' is not in the building's fields: {t}")
                self.assertEqual(guard(t, mask(t, top)), [], f"{bid}: {t}")
            # the sentences and the points do not say the same thing twice
            lead = re.findall(r"[a-z#'é$-]+", re.sub(r"\d[\d,.]*", "#", text.lower()))
            runs = {" ".join(lead[i:i + 6]) for i in range(len(lead) - 5)}
            for p in pts:
                w = re.findall(r"[a-z#'é$-]+", re.sub(r"\d[\d,.]*", "#", p["text"].lower()))
                for i in range(len(w) - 5):
                    self.assertNotIn(" ".join(w[i:i + 6]), runs, f"{bid}: a point repeats the sentences: {p['text']}")
            everything = mask(" ".join([text] + [p["text"] for p in pts]), top).lower()
            kind, fee, included = R.parking_kind(top)
            if kind is None:                                         # parking not published: an ask, never a description
                self.assertNotRegex(mask(text, top).lower(), r"garage|parking|\blot\b")
                self.assertFalse([p for p in pts if p["icon"] == "parking"], pts)
            if kind in ("garage", "covered", "lot") and not fee and not included and \
                    re.search(r"garage(?! spaces)|covered parking|parking lot|building's lot", everything):
                self.assertRegex(everything, r"not published|does not publish", f"{bid}: a fee that is not published must be called that")
                self.assertNotRegex(everything, r"\bfree\b|included in the rent", bid)
            if any(R.dog_open(u) for u in group):                    # an open dog policy never yields "dogs are allowed"
                self.assertNotRegex(everything.replace("it is not confirmed that dogs are allowed", ""),
                                    r"dogs are allowed|small dogs are|welcome|no weight limit", bid)

    def test_synthetic_buildings(self):
        us = [unit("a", building="B1", amenities={"pool": "pool", "doorman": "24h", "in_unit_laundry": "yes"}),
              unit("b", building="B1", scores={"hood_rank": 2.0}, sqft=820.0),
              unit("c", building="B2", scores={"hood_rank": 3.0}, parking={"type": None, "fee": None, "fee_note": None},
                   moments={"wake": {"park": "Pier 4 Park", "park_walk_min": 2.4, "dog_park": "Run 105", "dog_park_m": 480}}),
              unit("d", building="B3", scores={"hood_rank": 4.0}, parking={"type": "garage: fee not stated", "fee": None, "fee_note": ""},
                   amenities={"year_built": 2019.0, "gym": "yes"}, dog={"weight_limit_lb": "50"})]
        self.check(us)
        rows = buildings(us)
        self.assertEqual(json.loads(rows["B2"]["facts_used_json"])["warning"], "parking_unknown")
        self.assertEqual(json.loads(rows["B3"]["facts_used_json"])["warning"], "parking_fee")
        text = rows["B3"]["about_building"] + " " + " ".join(p["text"] for p in points(rows["B3"]))
        self.assertIn("The garage fee is not published", text)
        self.assertNotRegex(text.lower(), r"free parking|parking is free|included")

    def test_the_warning_is_the_most_pressing_thing_to_ask(self):
        ask = {"asterisk": True, "what": "elevator", "why": "x", "question": "Is there one?"}
        b = buildings([unit("a", confirm=ask, parking={"type": None, "fee": None, "fee_note": None})])["b-a"]
        self.assertEqual(json.loads(b["facts_used_json"])["warning"], "elevator_open")
        self.assertFalse([p for p in points(b) if p["text"] == R.POINTS["elevator"][2]])
        b = buildings([unit("a")])["b-a"]                             # garage priced, pet rent known, nothing unknown
        self.assertEqual(json.loads(b["facts_used_json"])["warning"], "tour")

    def test_only_pool_is_against_the_buildings_of_the_neighborhood(self):
        us = [unit("a", building="B1", amenities={"pool": "pool"}), unit("b", building="B2", scores={"hood_rank": 2.0}),
              unit("c", building="B3", scores={"hood_rank": 3.0})]
        peers = [R.building_facts([u]) for u in us]
        self.assertIn("only_pool", {c[1] for c in R.building_conditions(peers[0], peers)})
        self.assertNotIn("only_pool", {c[1] for c in R.building_conditions(peers[1], peers)})

    def test_names_from_the_data_read_as_plain_words(self):
        self.assertEqual(R.dog_park_words("Dog Run"), "the nearest dog park")
        self.assertEqual(R.dog_park_words("Oyster Shell Dog Park"), "Oyster Shell Dog Park")
        self.assertEqual(R.dog_park_words("The Sirius Dog Park (For Large Dogs)"), "The Sirius Dog Park")
        self.assertEqual(R.dog_park_words("Liberty Park II"), "the nearest dog park, Liberty Park II,")
        self.assertEqual(R.station_words("Newark Penn Station"), "Newark Penn Station")
        self.assertEqual(R.station_words("Kew Gardens"), "the Kew Gardens train station")
        self.assertEqual(R.restaurants_words(0), "No restaurants are")       # never "about 0"
        self.assertEqual(R.restaurants_words(1), "1 restaurant is")
        self.assertEqual(R.restaurants_words(31), "About 31 restaurants are")

    def test_every_building_on_the_page(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        self.check(units)
        rows = R.build_buildings(units)
        self.assertEqual(rows, R.build_buildings(units))
        d = R.building_distribution(rows)
        self.assertLessEqual(d["building sentence"]["top_share"], R.SHARE + 1e-9, d["building sentence"])
        by_hood = {}
        for r in rows:
            by_hood.setdefault(json.loads(r["facts_used_json"])["hood_id"], []).append(r)
        for hood, group in by_hood.items():
            for a, b in itertools.combinations(group[:3], 2):         # the top three buildings do not read identically
                self.assertNotEqual(a["about_building"], b["about_building"], hood)
            for a, b in zip(group, group[1:]):                        # neighboring buildings do not open the same way
                self.assertNotEqual(sentences(a["about_building"])[0], sentences(b["about_building"])[0],
                                    f"{hood}: {a['about_building']}")


class AmenityFields(unittest.TestCase):
    """Independent check 4, D9 and item 5: a sentence about an amenity says exactly what its field says."""

    def all_text(self, **am):
        u = unit("a1", amenities=am)
        r, b = run([u])["a1"], buildings([u])["b-a1"]
        return " ".join([r["host_line"], r["host_catch"], r["sub_building"], b["about_building"]]
                        + [p["text"] for p in json.loads(b["about_points_json"])])

    def test_desk_kind(self):
        k = R.desk_kind
        self.assertEqual(k({"doorman": "doorman", "doorman_text": "Concierge"}), "concierge")
        self.assertEqual(k({"doorman": "doorman", "doorman_text": "concierge (listing-site amenity tag)"}), "concierge")
        self.assertEqual(k({"doorman": "24h", "doorman_text": "24hr concierge"}), "concierge24")
        self.assertEqual(k({"doorman": "24h", "doorman_text": "24hr concierge, Doorman"}), "doorman24")
        self.assertEqual(k({"doorman": "doorman", "doorman_text": "Door Person"}), "doorman")
        self.assertEqual(k({"doorman": "doorman", "doorman_text": "yes"}), "doorman")
        self.assertEqual(k({"doorman": "24h", "doorman_text": "24/7 attended lobby"}), "attended24")
        self.assertEqual(k({"doorman": "doorman", "doorman_text": "attended lobby"}), "attended")
        self.assertIsNone(k({"doorman": None, "doorman_text": "virtual doorman"}))
        self.assertIsNone(k({"doorman": "doorman", "doorman_text": "virtual doorman"}))
        self.assertIsNone(k({"doorman": None, "doorman_text": None}))
        # the page data's separate fields (after independent check 4): each is said as what it is
        self.assertEqual(k({"doorman": None, "concierge": "concierge", "front_desk": None}), "concierge")
        self.assertEqual(k({"doorman": None, "concierge": "24h", "front_desk": None}), "concierge24")
        self.assertEqual(k({"doorman": "doorman", "concierge": "concierge", "front_desk": None}), "doorman")
        self.assertEqual(k({"doorman": "24h", "concierge": None, "front_desk": None}), "doorman24")
        self.assertEqual(k({"doorman": None, "concierge": None, "front_desk": "24h"}), "attended24")
        self.assertEqual(k({"doorman": None, "concierge": None, "front_desk": "front desk"}), "attended")
        self.assertIsNone(k({"doorman": None, "concierge": None, "front_desk": None, "doorman_text": "virtual doorman"}))

    def test_a_concierge_is_never_called_a_doorman(self):
        for am in ({"doorman": "doorman", "doorman_text": "Concierge"}, {"doorman": "24h", "doorman_text": "24hr concierge"},
                   {"doorman": None, "concierge": "concierge", "front_desk": None}):
            text = self.all_text(**am)
            self.assertNotRegex(text, r"(?i)doorman|front door|front desk is staffed", f"{am}: {text}")
            self.assertRegex(text, r"(?i)concierge", f"{am}: {text}")
        self.assertRegex(self.all_text(doorman="doorman", doorman_text="Doorman"), r"(?i)doorman")
        self.assertNotRegex(self.all_text(doorman="doorman", doorman_text="virtual doorman"), r"(?i)doorman|concierge")

    def test_only_doorman_needs_a_doorman(self):
        us = [unit("a1", hood="xx:h", amenities={"doorman": "doorman", "doorman_text": "Concierge"}),
              unit("a2", hood="xx:h"), unit("a3", hood="xx:h")]
        self.assertNotRegex(buildings(us)["b-a1"]["about_building"], r"(?i)doorman")

    def test_laundry_says_what_the_field_says(self):
        k = R.laundry_kind
        self.assertEqual(k({"in_unit_laundry": "yes", "laundry": "Washer, Dryer"}), "wd")
        self.assertEqual(k({"in_unit_laundry": "yes", "laundry": "In unit laundry"}), "in_unit")
        self.assertEqual(k({"in_unit_laundry": "yes", "laundry": "Washer"}), "in_unit")
        self.assertEqual(k({"in_unit_laundry": "yes", "laundry": None}), "in_unit")
        self.assertIsNone(k({"in_unit_laundry": "yes", "laundry": "On-site laundry"}))
        self.assertIsNone(k({"in_unit_laundry": "yes", "laundry": "W/D hookup; On-site laundry"}))
        self.assertIsNone(k({"in_unit_laundry": "yes", "laundry": "laundry room, additional fees may apply (not in unit)"}))
        self.assertIsNone(k({"in_unit_laundry": "on_site_only", "laundry": "Washer, Dryer"}))
        self.assertNotRegex(self.all_text(in_unit_laundry="yes", laundry="In unit laundry"), r"(?i)washer|dryer")
        self.assertNotRegex(self.all_text(in_unit_laundry="yes", laundry="On-site laundry"), r"(?i)laundry|washer")
        self.assertNotRegex(self.all_text(in_unit_laundry="on_site_only", laundry="Yes"), r"(?i)laundry|washer")
        self.assertRegex(self.all_text(in_unit_laundry="yes", laundry="Washer, Dryer"), r"(?i)washer and dryer")

    def test_parking_is_read_from_the_structured_fields(self):
        """Independent check 5, N1: the kind, the fee and what is included come from parking.kind / included_kind /
        optional_kinds, never from the head of the type string. The sentences are the ones the owner asked for."""
        def text(p):
            u = unit("a1", parking=p)
            r, b = run([u])["a1"], buildings([u])["b-a1"]
            return " ".join([r["sub_parking"], b["about_building"]] + [x["text"] for x in json.loads(b["about_points_json"])])
        pt = lambda p: R.parking_point(R.parking_facts({"parking": p}))
        lot = {"type": "garage: Open parking: included in lease; Garage: $125 month", "fee": 0.0, "fee_basis": "published",
               "kind": "open_lot", "included_kind": "open_lot", "fee_kind": "open_lot", "garage_is_optional_extra": True,
               "optional_kinds": [{"kind": "garage", "fee": 125.0, "fee_basis": "published"}]}
        # the type string still begins "garage:", as the six buildings of the check did: the structured kind wins
        self.assertEqual(R.parking_kind({"parking": lot}), ("lot", 0.0, True))
        self.assertEqual(pt(lot), "A free open lot; garage spaces are $125 a month.")
        self.assertEqual(pt({**lot, "optional_kinds": [{"kind": "garage", "fee": None}]}), "A free open lot; garage spaces cost extra.")
        t = text(lot)
        self.assertNotRegex(t, r"(?i)garage parking|park indoors|has a garage|building's garage|garage fee", t)
        self.assertRegex(t, r"(?i)open lot")
        deck = {"type": "offsite: no on-site parking: permit at a nearby deck $185/month", "fee": 185.0, "fee_basis": "published",
                "kind": "offsite", "fee_kind": "offsite", "offsite": True,
                "optional_kinds": [{"kind": "offsite", "fee": 100.0, "fee_basis": "published"}]}
        self.assertEqual(R.parking_kind({"parking": deck})[0], "offsite")
        self.assertEqual(pt(deck), "Parking is in an off-site deck, $185 a month.")
        t = text(deck)
        self.assertIn("Parking is in an off-site deck, $185 a month.", t)
        self.assertNotRegex(t, r"(?i)building's lot|parking lot|garage|\$100", t)       # the failing subhead of The George
        self.assertEqual(meta(run([unit("a1", parking=deck)])["a1"])["subs"]["parking"], "offsite_priced")
        assigned = {"type": "assigned: one assigned space included per unit; garage and outdoor parking", "fee": 0.0,
                    "fee_basis": "published", "kind": "assigned", "included_kind": "assigned", "fee_kind": "assigned", "assigned": True}
        self.assertEqual(pt(assigned), "An assigned space is included; the listing does not say where.")
        self.assertEqual(R.parking_point(R.parking_facts({"parking": assigned}), long=True),
                         "An assigned space is included; the listing does not say whether it is a garage or a lot.")
        self.assertIn("An assigned space is included; the listing does not say whether it is a garage or a lot.", text(assigned))
        self.assertEqual(pt({"type": "lot: off-street parking included", "fee": 0.0, "fee_basis": "published", "kind": "off_street",
                             "included_kind": "off_street", "fee_kind": "off_street"}), "Free off-street parking.")
        unnamed = {"type": "parking", "fee": None, "kind": "unspecified"}
        self.assertEqual(pt(unnamed), "The listing mentions parking without saying what kind: ask.")
        self.assertNotRegex(text(unnamed), r"(?i)garage|\blot\b|covered|free|included")
        # an included space whose kind the listing does not name, filed as an open lot for the score
        self.assertEqual(pt({"type": "lot", "fee": 0.0, "fee_basis": "published", "kind": "open_lot", "included_kind": "unspecified",
                             "fee_kind": "unspecified"}), "A parking space is included; the listing does not say what kind.")
        # never a fee attached to the wrong kind: the fee is the garage's, the space she would park in is the lot
        wrong = {"type": "lot: surface parking", "fee": 150.0, "fee_basis": "published", "kind": "open_lot", "fee_kind": "garage"}
        self.assertEqual(R.parking_kind({"parking": wrong}), ("lot", None, False))
        self.assertNotIn("$150", text(wrong))
        # a resident's estimate is not the building's price
        self.assertIsNone(R.parking_kind({"parking": {"type": "garage: x", "kind": "garage", "fee": 90.0, "fee_basis": "estimate from a review"}})[1])

    def test_every_parking_text_on_the_page_matches_the_structured_fields(self):
        """All shown buildings: no text says "garage" unless the kind is a garage (or names it as the paid extra), and
        every parking fee printed is the fee of the space she would park in or of the extra it names."""
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        rows, brows = run(units), buildings(units)
        for u in units:
            P = R.parking_facts(u)
            b = brows[u.get("building_id") or u["id"]]
            texts = [rows[u["id"]]["sub_parking"], b["about_building"]] + [x["text"] for x in json.loads(b["about_points_json"])]
            for t in texts:
                t = mask(t, u)
                bare = re.sub(r"garage spaces? (?:are \$[\d,]+ a month|cost extra)|a garage space (?:costs extra|is an added cost)|"
                              r"whether it is a garage or a lot|is in a garage or a lot", "", t)
                if re.search(r"(?i)\bgarage\b|park indoors", bare):
                    self.assertEqual(P["kind"], "garage", f"{u['id']}: {t}")
                if re.search(r"(?i)building's lot|parking lot|open lot", bare):
                    self.assertEqual(P["kind"], "lot", f"{u['id']}: {t}")
                if re.search(r"(?i)\bfree\b|included in the rent|rent includes|is included", bare) and re.search(r"(?i)park|space|lot", bare):
                    self.assertTrue(P["included"], f"{u['id']}: {t}")
                if re.search(r"(?i)off-site", bare):
                    self.assertEqual(P["kind"], "offsite", f"{u['id']}: {t}")

    def test_washer_only_and_listing_tag_laundry(self):
        washer = dict(in_unit_laundry="yes", laundry="In-unit washer (no dryer named)", in_unit_appliances="washer",
                      in_unit_laundry_basis="listing_site_appliance_list")
        self.assertEqual(R.laundry_kind(washer), "washer")
        t = self.all_text(**washer)
        self.assertNotRegex(t, r"(?i)washer and dryer", t)
        self.assertRegex(t, r"(?i)washer in the apartment|names a washer|washer is on the listing", t)
        tag = dict(in_unit_laundry="yes", laundry="In-unit washer and dryer", in_unit_appliances="washer and dryer",
                   in_unit_laundry_basis="listing_site_appliance_list")
        t = self.all_text(**tag)
        for sent in sentences(t):
            if re.search(r"(?i)washer|laundry", sent):
                self.assertRegex(sent, r"(?i)listing", sent)                      # "The listing shows ...", never flat
        own = dict(in_unit_laundry="yes", laundry="In-unit washer and dryer", in_unit_appliances="washer and dryer",
                   in_unit_laundry_basis="page_says_in_apartment")
        self.assertRegex(self.all_text(**own), r"(?i)washer and dryer")

    def test_the_station_is_named_by_its_kind(self):
        self.assertEqual(R.station_words("Journal Square", "PATH"), "the Journal Square PATH station")
        self.assertEqual(R.station_words("Elmhurst Av", "subway"), "the Elmhurst Av subway station")
        self.assertEqual(R.station_words("Port Imperial", "light rail"), "the Port Imperial light rail stop")
        self.assertEqual(R.station_words("Kew Gardens", "train"), "the Kew Gardens train station")
        u = unit("a1", moments={"sat": {"train_station": "Journal Square", "train_station_m": 300, "train_station_kind": "PATH"}})
        b = buildings([u])["b-a1"]
        t = " ".join([b["about_building"]] + [x["text"] for x in json.loads(b["about_points_json"])])
        self.assertNotIn("train station", t)

    def test_a_garage_beside_a_lot_is_not_where_she_would_park(self):
        u = unit("a1", parking={"type": "garage: surface lot; garage $50/month", "fee": 50.0})
        self.assertTrue(R.garage_mixed(u))
        self.assertFalse(R.garage_mixed(unit("a2")))
        r, b = run([u])["a1"], buildings([u])["b-a1"]
        text = " ".join([r["sub_parking"], b["about_building"]] + [p["text"] for p in json.loads(b["about_points_json"])])
        self.assertNotRegex(text, r"(?i)you would park in the building's garage|park indoors", text)

    def test_a_pool_table_is_not_a_pool(self):
        self.assertNotRegex(self.all_text(pool=None, pool_text="Pool table"), r"(?i)\bpool\b")

    def test_a_pet_spa_or_an_unnamed_dog_amenity_is_not_a_dog_area(self):
        for a in ("pet spa", "yes", "dog wash", "pet washing station; no dog run listed"):
            self.assertNotRegex(self.all_text(dog_amenities=a), r"(?i)its own dog (park|run|area)|dog (park|run) on site", a)
        self.assertRegex(self.all_text(dog_amenities="dog park; pet spa"), r"(?i)its own dog park")

    def test_no_stale_wording_in_the_libraries(self):
        for name, texts in families():
            for t in texts:
                for rx, what in G.STALE:
                    self.assertIsNone(rx.search(t), f"{name}: {what}: {t}")


class Offers(unittest.TestCase):
    """Independent check 4, D20: "up to 2 months free" on the page is not "2 months free" in the sentence."""

    def lines(self, offer):
        us = [unit(f"o{i}", building="b-o", sqft=None, floor=None, floor_basis="unknown", available=None, all_in=2500 + i,
                   rent={"free_months": 2, "offer_text": offer}) for i in range(1, 9)]
        return [r["host_line"] for r in run(us).values() if "free" in r["host_line"]]

    def test_up_to_is_kept(self):
        got = self.lines("Lease by 11/30 to receive up to 2 months free off base rent.")
        self.assertTrue(got)
        for line in got:
            self.assertIn("up to 2 months", line)

    def test_a_plain_offer_stays_plain(self):
        got = self.lines("2 months free on a 14-month lease.")
        self.assertTrue(got)
        for line in got:
            self.assertNotIn("up to", line)


class OnThePage(unittest.TestCase):
    """Every generated text for every apartment in site/data.json, against the guards, the numbers and the limits."""

    def check(self, units):
        by_b = {}
        for u in units:
            by_b.setdefault(u.get("building_id") or u["id"], []).append(u)
        rows = run(units)
        for u in units:
            ok = allowed_numbers(u, (len(by_b[u.get("building_id") or u["id"]]),))
            r = rows[u["id"]]
            for col in ("host_line", "host_catch"):
                text = r[col]
                self.assertTrue(text, f"{u['id']}: empty {col}")
                self.assertEqual(guard(text), [], f"{u['id']} {col}: {text}")
                for n in numbers(text):
                    self.assertIn(n, ok, f"{u['id']} {col}: '{n}' is not in the apartment's fields: {text}")
                self.assertIn(len(sentences(text)), (1, 2), text)
                # the first monthly figure of a text is "a month with utilities and fees", never the old wording;
                # a price is always "about", except the rent the listing asks, which is exact and called rent
                self.assertNotRegex(text, r"(?i)everything included|\ball[- ]in\b", f"{u['id']} {col}")
                first = re.search(r"\$[\d,]+ a month( with utilities and fees)?", text)
                if first:
                    self.assertTrue(first.group(1), f"{u['id']} {col}: {text}")
                asked = re.search(r"\b[Rr]ent is \$([\d,]+)", text)
                if asked:
                    self.assertEqual(int(asked.group(1).replace(",", "")), rent_line(u), f"{u['id']} {col}: {text}")
                quoted = str(R.get(u, "conditions", "income_requirement") or "")      # the listing's own figure, quoted
                for m in re.finditer(r"(about |[Rr]ent is )?\$([\d,]+)", text):
                    if int(m.group(2).replace(",", "")) != R.CAP and "$" + m.group(2) not in quoted:
                        self.assertTrue(m.group(1), f"{u['id']} {col}: a price without 'about': {text}")
                for m in re.finditer(r"(about )?([\d,]+) square feet", text):
                    self.assertTrue(m.group(1), f"{u['id']} {col}: a size without 'about': {text}")
            self.assertLessEqual(len(r["host_line"].split()), R.MAX_WORDS, r["host_line"])
            self.assertLessEqual(len(r["host_catch"].split()), R.CATCH_MAX_WORDS, r["host_catch"])
            if u.get("floor_basis") not in ("confirmed", "stated"):      # an unknown is never stated as fact
                self.assertNotRegex(r["host_line"].lower(), r"\bfloor \d", f"{u['id']}: a floor that no page states")
            if R.num(u.get("sqft")) is None:
                self.assertNotIn("square feet", r["host_line"] + r["host_catch"])
            if R.dog_open(u) or str(R.get(u, "dog", "allowed") or "").lower() != "yes":
                asked = re.sub(r"(not confirmed that|whether|confirm that) (dogs are|a dog is) allowed", "",
                               " ".join(r[c] for c in ("host_line", "host_catch", "sub_dog")).lower())   # asking is not stating
                self.assertNotRegex(asked, r"dogs are allowed|a dog is allowed|small dogs are allowed|dogs are welcome", u["id"])
            if not R.get(u, "parking", "type"):
                self.assertNotRegex(r["sub_parking"].lower(), r"garage|indoors|included|\blot\b", u["id"])
            for c in Subheads.COLS:
                if r[c]:
                    self.assertEqual(guard(r[c]), [], f"{u['id']} {c}: {r[c]}")
                    self.assertLessEqual(len(r[c].split()), R.SUB_MAX_WORDS, r[c])
                    self.assertEqual(len(sentences(r[c])), 1, r[c])
                    self.assertNotRegex(r[c], r"\d", r[c])
                    self.assertIsNone(HEDGE.search(r[c]), r[c])

    def test_synthetic_apartments(self):
        us = [unit("a", building="B", all_in=2111, sqft=913.0, floor=14.0, amenities={"pool": "pool", "doorman": "24h"}),
              unit("b", building="B", scores={"hood_rank": 2.0}, available="2026-12-07", rent={"free_months": "2"},
                   parking={"type": "covered: carport", "fee": 45.0, "fee_note": "single price stated"}),
              unit("c", scores={"hood_rank": 3.0}, moments={"wake": {"park": "Pier 4 Park", "park_walk_min": 2.4,
                                                                       "dog_park": "Run 105", "dog_park_m": 480}}),
              unit("d", scores={"hood_rank": 4.0}, beds=None, all_in=None, sqft=None, floor=None, floor_basis="unknown",
                   available=None, cost_check={"cap_margin": None}, parking={"type": None, "fee": None, "fee_note": None})]
        self.check(us)

    def test_every_apartment_on_the_page(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        self.check(units)
        rows = R.build(units)
        self.assertEqual(len(rows), len(units))
        self.assertEqual(rows, R.build(units))

    def test_the_csvs_on_disk_have_exactly_the_pages_apartments_and_buildings(self):
        units = page_units()
        if units is None or not R.OUT.exists() or not R.OUT_BUILDINGS.exists():
            self.skipTest("site/data.json or the CSVs are not here")
        with open(R.OUT, newline="", encoding="utf-8") as fh:
            on_disk = [r["listing_id"] for r in csv.DictReader(fh)]
        self.assertEqual(sorted(on_disk), sorted(u["id"] for u in units),
                         "data/reference/realtor_lines.csv is stale: run python3 scripts/realtor_lines.py")
        with open(R.OUT_BUILDINGS, newline="", encoding="utf-8") as fh:
            on_disk = [r["building_id"] for r in csv.DictReader(fh)]
        self.assertEqual(sorted(on_disk), sorted({u.get("building_id") or u["id"] for u in units}),
                         "data/reference/building_about.csv is stale: run python3 scripts/realtor_lines.py")


def groups(rows, key):
    """rows of R.build (which come out in neighborhood rank order) -> {hood_id or building_id: [row, ...]}"""
    out = {}
    for r in rows:
        out.setdefault(meta(r)[key], []).append(r)
    return out


class Repetition(unittest.TestCase):
    """What repeats side by side is what the reader notices; across the page, the limit is a loose 8% per wording."""

    def check_neighbors(self, rows):
        for name, group in groups(rows, "building_id").items():
            for a, b in itertools.combinations(group[:3], 2):
                self.assertNotEqual(meta(a)["angle"], meta(b)["angle"], f"{name}: two of the first three lead with the same kind of fact")
                self.assertNotEqual(a["host_line"], b["host_line"], name)
            for a, b in zip(group, group[1:]):
                self.assertNotEqual(meta(a)["pattern"], meta(b)["pattern"], name)

    def test_identical_apartments_in_one_building_still_read_differently(self):
        us = [unit(f"u{i}", building="B", scores={"hood_rank": float(i + 1)}) for i in range(8)]   # eight identical
        self.check_neighbors(R.build(us))

    def test_apartments_with_nothing_published_still_read_differently(self):
        bare = dict(all_in=None, sqft=None, floor=None, floor_basis="unknown", available=None, beds=None,
                    parking={"type": None, "fee": None, "fee_note": None}, cost_check={"cap_margin": None})
        us = [unit(f"u{i}", building="B", scores={"hood_rank": float(i + 1)}, **bare) for i in range(3)]
        rows = R.build(us)
        self.check_neighbors(rows)
        for r in rows:
            self.assertEqual(guard(r["host_line"]), [], r["host_line"])

    def test_the_same_caution_is_said_to_every_apartment_that_has_it(self):
        # the catch is the apartment's most important open point; it is never swapped for a lesser one for variety
        special = {"asterisk": True, "needs_call": True}
        us = [unit("a", building="B", rent=special), unit("b", building="B", rent=special, scores={"hood_rank": 2.0}),
              unit("c", building="B", rent=special, scores={"hood_rank": 3.0}, floor=None, floor_basis="unknown")]
        rows = run(us)
        self.assertEqual({catch_kind(rows[k]) for k in "abc"}, {"rent:needs_call"})
        self.assertEqual(len({rows[k]["host_catch"] for k in "abc"}), 3)     # in different words while wordings last

    def test_every_building_on_the_page(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        self.check_neighbors(R.build(units))

    def test_no_wording_is_on_more_than_8_percent_of_the_page(self):
        self.assertEqual(R.SHARE, 0.08)      # the owner's editor set 8%: clarity first, enough variety side by side
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        rows = R.build(units)
        d = R.distribution(rows)
        print()
        for name, x in {**d, **R.building_distribution(R.build_buildings(units))}.items():
            print(f"    {name:22} commonest on {x['top_count']:3} ({x['top_share']:.1%}), {x['distinct']} distinct")
        self.assertLessEqual(d["lead wording"]["top_share"], R.SHARE, d["lead wording"])
        self.assertLessEqual(d["catch wording"]["top_share"], R.SHARE, d["catch wording"])
        for c in Subheads.COLS:
            self.assertLessEqual(d[c]["top_share"], R.SHARE, d[c])
        # the same threshold on the finished sentences, whatever the ids say
        lead = Counter(re.sub(r"\d[\d,.]*", "#", sentences(r["host_line"])[0]) for r in rows).most_common(1)[0]
        catch = Counter(re.sub(r"\d[\d,.]*", "#", r["host_catch"]) for r in rows).most_common(1)[0]
        self.assertLessEqual(lead[1] / len(rows), R.SHARE, lead)
        self.assertLessEqual(catch[1] / len(rows), R.SHARE, catch)


if __name__ == "__main__":
    unittest.main(verbosity=1)
