#!/usr/bin/env python3
"""Tests for scripts/realtor_lines.py.

Run from the house-hunt folder:  python3 scripts/test_realtor_lines.py     (or: python3 -m pytest scripts/test_realtor_lines.py)

They cover the sentence libraries (at least 8 different sentences per condition, house style, no host on screen), the
unit line (what sets a unit apart inside its building), the catch (a reason is stated only when the unit's own fields
give it), "About the building" (two sentences and icon points per building), the handling of unknowns, the rule that
no number is printed unless it is in the data, the rules against repetition (shares of the page, the top three of a
neighbourhood, the units of one building, neighbouring rows), stability across reruns and the length limits. The
"on the page" tests run the same checks over everything in site/data.json when that file is present, so the tests
also work as a check after a rerun.
"""
import copy
import itertools
import json
import re
import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import realtor_lines as R  # noqa: E402

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
STYLE = re.compile(r"[—–?]|\b(stunning|nestled|boasts?|vibrant|luxur\w*|oasis|gem|bustling|breathtaking)\b|"
                   r"\bnot\b[^.]{0,60}\bbut\b|\byears?\b|scorecard|crime|violent|burglar|theft|per 1,000|safe|police", re.I)
STAGE = re.compile(r"\b(I|I'll|I'd|I've|my|me)\b|\blet's\b|\blet me\b|picture this|\bokay\b|your host")   # no host on screen


def unit(uid, hood="xx:test", building=None, **over):
    """A complete synthetic unit with nothing remarkable about it; `over` replaces top-level keys. By default every
    unit is its own building."""
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


def pattern(row):
    return meta(row)["pattern"]


def cond(row):
    return pattern(row).rsplit("_", 1)[0]


def catch_kind(row):
    return meta(row)["catch_kind"]


def points(row):
    return json.loads(row["about_points_json"])


def numbers(text):
    return [n.replace(",", "").rstrip(".") for n in NUMBER.findall(text)]


def names(u):
    return (R.get(u, "moments", "wake", "park"), R.get(u, "moments", "wake", "dog_park"),
            R.get(u, "moments", "sat", "train_station"), R.get(u, "moments", "work", "supermarket"))


def allowed_numbers(u, n_peers):
    """Every number a text about this unit or its building may contain, worked out from the fields without using the
    generator's own templates: its figures, the size of the group it is compared with, the page's fixed wordings."""
    ok = {str(n) for n in n_peers} | {"10", "12"}             # "10-minute walk", "12-month lease"
    if u.get("beds") == 1:
        ok.add("1")                                           # "1-bedroom"

    def put(x):
        v = R.num(x)
        if v is not None:
            ok.add(str(int(round(v))))
            ok.add(f"{v:.1f}")
    for path in (("all_in",), ("sqft",), ("floor",), ("cost_check", "cap_margin"), ("parking", "fee"),
                 ("rent", "free_months"), ("rent", "lease_months"), ("cost_check", "lease_term_months"),
                 ("moments", "wake", "park_walk_min"), ("moments", "after", "restaurants_800m"),
                 ("listing_age_days",), ("amenities", "year_built"), ("dog", "weight_limit_lb")):
        put(R.get(u, *path))
    for path in (("moments", "wake", "dog_park_m"), ("moments", "sat", "train_station_m"),
                 ("moments", "work", "supermarket_m")):
        v = R.num(R.get(u, *path))
        if v is not None:
            ok.add(R.miles(v))
    if R.get(u, "amenities", "doorman") == "24h":
        ok.add("24")
    try:
        ok.add(str(date.fromisoformat(str(u.get("available"))[:10]).day))
    except ValueError:
        pass
    for text in (R.get(u, "confirm", "question"),) + names(u):   # a name or a question quoted from the unit
        ok.update(numbers(str(text or "")))
    return ok


def sentence_count(text, u):
    for name in sorted((n for n in names(u) + (R.get(u, "confirm", "question"),) if n), key=lambda x: -len(str(x))):
        text = text.replace(str(name), "NAME")
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def families():
    """Every (family name, [sentences]) in the libraries."""
    for c, (_, texts) in R.LEADS.items():
        yield "lead:" + c, texts
    for c, (_, _, texts) in R.BUILDING.items():
        yield "building:" + c, texts
    for kind, texts in R.CATCHES.items():
        yield "catch:" + kind, texts
    for section, entries in R.SUBS.items():
        for key, texts in entries:
            yield f"sub:{section}.{key}", texts
    for name, texts in R.FRAMES.items():
        yield "frame:" + name, texts
    for key, (_, _, texts) in R.POINTS.items():
        yield "point:" + key, texts
    for key, (_, texts) in R.WARNINGS.items():
        yield "point:warning." + key, texts


def page_units():
    return json.loads(R.DATA.read_text(encoding="utf-8"))["units"] if R.DATA.exists() else None


class Library(unittest.TestCase):
    def test_every_condition_has_enough_sentences(self):
        for name, texts in families():
            need = R.MIN_POINT_WORDINGS if name.startswith("point:") else R.MIN_WORDINGS
            self.assertGreaterEqual(len(texts), need, name)
            self.assertEqual(len(set(texts)), len(texts), f"{name}: a sentence appears twice")

    def test_sentences_of_a_condition_start_differently(self):
        # different sentences, never a template with a synonym swapped: no shared opening inside a condition
        for name, texts in families():
            if name.startswith(("frame:", "point:")):
                continue
            opens = [" ".join(re.findall(r"[A-Za-z{}_']+", t.lower())[:3]) for t in texts]
            dup = [o for o in set(opens) if opens.count(o) > 1]
            self.assertEqual(dup, [], f"{name}: more than one sentence opens with {dup}")

    def test_no_sentence_is_shared_between_conditions(self):
        seen = {}
        for name, texts in families():
            if name.split(":")[0] in ("lead", "catch", "building"):
                for t in texts:
                    self.assertNotIn(t, seen, f"{name} repeats a sentence of {seen.get(t)}")
                    seen[t] = name

    def test_house_style_and_no_host_on_screen(self):
        for name, texts in families():
            for t in texts:
                self.assertIsNone(STYLE.search(t), f"{name}: {t}")
                self.assertIsNone(STAGE.search(t), f"{name}: stage business in: {t}")
                if not name.startswith("frame:") and "{q}" not in t:
                    self.assertEqual(len(re.findall(r"[.!](\s|$)", t)), 1, f"{name}: one sentence wanted: {t}")
                if name.startswith(("lead:", "building:")):
                    self.assertLessEqual(len(t.split()), 24, t)
                if name.startswith(("sub:", "point:")):
                    self.assertLessEqual(len(t.split()), 14, t)
                if name.startswith("sub:"):
                    self.assertNotRegex(t, r"\d", t)
                    self.assertNotRegex(t.lower(), r"\b(may|might|probably|perhaps|possibly|somewhat|fairly)\b", t)

    def test_no_typed_numbers(self):
        # the only digits typed in the libraries are fixed wordings: a 12-month lease, a 24-hour desk, a 1-bedroom
        for name, texts in families():
            for t in texts:
                bare = re.sub(r"\{[A-Za-z_0-9]+\}", "", t)
                for fixed in ("12-month", "24-hour", "24 hours", "1-bedroom"):
                    bare = bare.replace(fixed, "")
                self.assertNotRegex(bare, r"\d", f"{name}: {t}")

    def test_unpriced_garage_sentences_all_say_the_fee_is_missing(self):
        for t in R.BUILDING["garage_unpriced"][2]:
            self.assertRegex(t, R.UNPRICED, t)
            self.assertNotRegex(t.lower(), r"free|included")
        for key in ("garage_unpriced", "covered_unpriced", "lot_unpriced", "onsite_unpriced"):
            for t in R.POINTS[key][2]:
                self.assertRegex(t.lower(), r"not published|no price|unpublished|not stated", t)

    def test_icons_are_from_the_fixed_set(self):
        for key, (icon, _, _) in R.POINTS.items():
            self.assertIn(icon, R.ICONS, key)
            self.assertNotEqual(icon, "warning", key)

    def test_an_open_dog_policy_is_never_called_welcome(self):
        for key in ("conflicting", "unsettled"):
            for t in dict(R.SUBS["dog"])[key]:
                self.assertNotRegex(t.lower(), r"small dogs are|dogs, yes|allow dogs and|dogs are welcome[.,]", t)
        for kind in ("confirm:dogs open", "confirm:dogs reason", "confirm:dogs conflict"):
            for t in R.CATCHES[kind]:
                self.assertNotRegex(t.lower(), r"dogs are welcome[.,]|dogs are allowed[.,]", t)
        for t in R.CATCHES["confirm:dogs open"] + R.CATCHES["confirm:dogs reason"] + dict(R.SUBS["dog"])["unsettled"]:
            self.assertNotRegex(t.lower(), r"disagree|conflict|contradict|mixed signals|differ", t)   # a reason needs its field

    def test_only_the_net_effective_family_says_net_effective(self):
        for name, texts in families():
            if name in ("catch:rent:net_effective", "sub:cost.net_effective"):
                continue
            for t in texts:
                self.assertNotRegex(t.lower(), r"net-effective|gross rent|discounted average", f"{name}: {t}")


class UnitLine(unittest.TestCase):
    def test_a_unit_is_compared_with_the_units_of_its_own_building(self):
        us = [unit("a", building="B", all_in=2100, scores={"hood_rank": 2.0}),
              unit("b", building="B", all_in=2600, scores={"hood_rank": 1.0}),
              unit("c", building="B", all_in=2700, scores={"hood_rank": 3.0}),
              unit("z", building="Z", all_in=1900, scores={"hood_rank": 4.0})]      # cheaper, but another building
        peers = [R.facts(u) for u in us[:3]]
        conds = {c[1] for c in R.lead_conditions(peers[0], peers)}
        self.assertIn("cheapest", conds)
        alone = {c[1] for c in R.lead_conditions(R.facts(us[3]), [R.facts(us[3])])}
        self.assertFalse(alone & R.PEER_CONDITIONS)                 # alone in its building: no comparison at all

    def test_cheapest_names_the_price(self):
        us = [unit("a", building="B", all_in=2100, sqft=None, scores={"hood_rank": 2.0}),
              unit("b", building="B", all_in=2600, sqft=None, scores={"hood_rank": 1.0}),
              unit("c", building="B", all_in=2700, sqft=None, scores={"hood_rank": 3.0})]
        for salt in range(40):
            rows = run([dict(u, id=f"{u['id']}{salt}") for u in us])
            r = rows[f"a{salt}"]
            if cond(r) == "cheapest":
                self.assertIn("2,100", r["host_line"].split(". ")[0])
                return
        self.fail("the cheapest of three never led with its price")

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
        self.assertNotIn("soonest_date", got(2))                    # two units are available now

    def test_a_tie_is_not_called_the_best(self):
        us = [unit("a", building="B"), unit("b", building="B", scores={"hood_rank": 2.0})]      # identical units
        for r in run(us).values():
            self.assertNotIn(cond(r), R.PEER_CONDITIONS)

    def test_a_superlative_needs_every_unit_to_publish_the_figure(self):
        us = [unit("a", building="B", sqft=950.0), unit("b", building="B", sqft=700.0, scores={"hood_rank": 2.0}),
              unit("c", building="B", sqft=None, scores={"hood_rank": 3.0})]
        peers = [R.facts(u) for u in us]
        conds = {c[1] for c in R.lead_conditions(peers[0], peers)}
        self.assertNotIn("biggest", conds)
        self.assertNotIn("value", conds)

    def test_fewest_open_questions_and_newest_listing(self):
        us = [unit("a", building="B", tour_questions=["q1"], listing_age_days=2.0),
              unit("b", building="B", tour_questions=["q1", "q2", "q3"], listing_age_days=30.0, scores={"hood_rank": 2.0}),
              unit("c", building="B", tour_questions=["q1", "q2"], scores={"hood_rank": 3.0})]
        peers = [R.facts(u) for u in us]
        self.assertLessEqual({"fewest_questions", "newest"}, {c[1] for c in R.lead_conditions(peers[0], peers)})
        self.assertFalse({"fewest_questions", "newest"} & {c[1] for c in R.lead_conditions(peers[1], peers)})

    def test_the_building_is_not_described_in_the_unit_line(self):
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

    def test_missing_all_in_prints_no_price(self):
        u = unit("a", all_in=None, cost_check={"cap_margin": None})
        line = run([u])["a"]["host_line"]
        self.assertNotIn("all in", line)
        self.assertNotIn("2,500", line)


class Catch(unittest.TestCase):
    def dog(self, why, **dog):
        ask = {"asterisk": True, "what": "dogs allowed", "why": why, "question": "Are dogs allowed?"}
        return unit("a", confirm=ask, dog=dog or {})

    def test_sources_disagree_only_when_the_open_item_says_so(self):
        row = run([self.dog("Two listing sites disagree on whether dogs are allowed, and the building's own page does not settle it.")])["a"]
        self.assertEqual(catch_kind(row), "confirm:dogs conflict")
        for why, word in (("Dogs are not confirmed as allowed here: dogs are not named as allowed ('upon approval')", "upon approval"),
                          ("A condo unit where pets are considered case by case, so dogs are not explicitly allowed.", "case by case"),
                          ("dogs are not named as allowed (the only policy text is 'contact for more information on pet policy')", "contact the office"),
                          ("The listing says only 'small pets allowed'; dogs are not named.", "small pets"),
                          ("Dogs are allowed only according to a listing site's pet data; there is no policy text.", "no policy text")):
            for salt in range(8):
                u = self.dog(why)
                u["id"] = f"a{salt}"
                row = run([u])[f"a{salt}"]
                self.assertEqual(catch_kind(row), "confirm:dogs reason", why)
                self.assertIn(word, row["host_catch"].lower())
                self.assertNotRegex(row["host_catch"].lower(), r"disagree|conflict|contradict")

    def test_an_open_dog_item_with_no_stated_reason_asserts_none(self):
        row = run([self.dog("Not settled.")])["a"]
        self.assertEqual(catch_kind(row), "confirm:dogs open")
        self.assertNotRegex(row["host_catch"].lower(), r"disagree|conflict|approval|case by case|small pets")

    def test_the_dog_subhead_never_says_welcome_while_dogs_are_open(self):
        u = self.dog("The listing says only 'small pets allowed'; dogs are not named.",
                     size_note="page says small dogs; no weight number")
        row = run([u])["a"]
        self.assertEqual(meta(row)["subs"]["dog"], "unsettled")
        self.assertNotRegex(row["sub_dog"].lower(), r"small dogs are|welcome,|dogs are allowed")
        b = buildings([u])["b-a"]
        self.assertEqual(json.loads(b["facts_used_json"])["warning"], "dog_unsettled")
        self.assertFalse([p for p in points(b) if p["icon"] == "dog" and re.search(r"allowed|welcome|takes dogs|friendly", p["text"].lower())])

    def test_net_effective_needs_the_basis_and_a_gross_figure(self):
        special = {"basis_kind": "net_effective", "listed": 2300, "gross": 2600, "asterisk": True, "needs_call": True,
                   "offer_text": "2 months free on a 14-month lease; price shown is net effective"}
        row = run([unit("a", rent=special)])["a"]
        self.assertEqual(catch_kind(row), "rent:net_effective")
        self.assertEqual(meta(row)["subs"]["cost"], "net_effective")
        for change in ({"gross": 2300}, {"gross": None}, {"offer_text": "Gross or net-effective: not stated"},
                       {"basis_kind": "listed"}):
            row = run([unit("a", rent={**special, **change})])["a"]
            self.assertEqual(catch_kind(row), "rent:needs_call", change)
            self.assertEqual(meta(row)["subs"]["cost"], "ambiguous_rent", change)
            text = (row["host_catch"] + " " + row["sub_cost"]).lower()
            self.assertNotRegex(text, r"net-effective|gross|discounted average", change)

    def test_asterisk_comes_first_and_the_units_own_question_is_quoted(self):
        u = unit("a", confirm={"asterisk": True, "what": "elevator", "why": "x", "question": "Does it have one?"},
                 rent={"asterisk": True, "needs_call": True})
        self.assertEqual(catch_kind(run([u])["a"]), "confirm:elevator")
        u = unit("a", confirm={"asterisk": True, "what": "listing", "why": "x", "question": "Is unit 302 still available?"})
        self.assertIn("Is unit 302 still available?", run([u])["a"]["host_catch"])
        u = unit("a", confirm={"asterisk": True, "what": "something new", "why": "x", "question": "Is it real?"})
        self.assertIn("Is it real?", run([u])["a"]["host_catch"])

    def test_a_floor_plan_is_called_one_only_when_the_open_item_says_so(self):
        u = unit("a", confirm={"asterisk": True, "what": "availability", "why": "Floor plan only: no unit, floor or date.",
                               "question": "Which unit?"})
        self.assertEqual(meta(run([u])["a"])["catch_id"].rsplit("_", 1)[0], "confirm:availability")
        u = unit("a", confirm={"asterisk": True, "what": "availability", "why": "Date unclear.", "question": "When is it free?"})
        row = run([u])["a"]
        self.assertIn("When is it free?", row["host_catch"])
        self.assertNotRegex(row["host_catch"].lower(), r"floor plan|layout|plan type")

    def test_the_unpublished_floor_is_the_units_catch_when_nothing_else_is_open(self):
        row = run([unit("a", floor=None, floor_basis="unknown")])["a"]
        self.assertEqual(catch_kind(row), "floor:unpublished")
        row = run([unit("a", floor=6.0, floor_basis="inferred")])["a"]
        self.assertEqual(catch_kind(row), "floor:inferred")
        self.assertIn("6", numbers(row["host_catch"]))

    def test_unpublished_costs_near_the_cap(self):
        u = unit("a", all_in_unknown=["pet rent", "parking fee"], cost_check={"cap_margin": 120})
        row = run([u])["a"]
        self.assertEqual(catch_kind(row), "unknown:costs_tight")
        self.assertRegex(row["host_catch"], r"pet rent")
        self.assertIn("$120", row["host_catch"])

    def test_the_catch_is_never_about_safety_or_the_neighbourhood(self):
        u = unit("a", scores={"hood_rank": 1.0, "parts": {"safety": 1, "distance": 2, "space": 45, "cost": 50}})
        self.assertEqual(catch_kind(run([u])["a"]), "weak:space")

    def test_every_catch_on_the_page_that_gives_a_reason_has_it_in_the_units_fields(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        by_id = {u["id"]: u for u in units}
        for r in R.build(units):
            u, m = by_id[r["listing_id"]], meta(r)
            family = m["catch_id"].rsplit("_", 1)[0]
            if family in R.CATCH_BASIS:
                self.assertTrue(R.CATCH_BASIS[family](u), f"{r['listing_id']}: '{r['host_catch']}' has no basis in the unit")
            q = str(R.get(u, "confirm", "question") or "\0")
            text = r["host_catch"].replace(q, "").lower()
            why = str(R.get(u, "confirm", "why") or "").lower()
            if "dog" in text and re.search(r"disagree|contradict|mixed signals|sources conflict|conflicts\b|break the tie", text):
                self.assertRegex(why, r"disagree|and another says", r["listing_id"])
            for phrase, need in (("upon approval", "approval"), ("case by case", "case by case"),
                                 ("contact the office", "contact for more information"), ("small pets", "small pets"),
                                 ("income", "income"), ("floor plan", "plan")):
                if phrase in text and family.startswith("confirm:"):
                    self.assertIn(need, why, f"{r['listing_id']}: {r['host_catch']}")
            if re.search(r"net-effective|gross rent|discounted average|baked in|averaged over", text + " " + r["sub_cost"].lower()):
                self.assertTrue(R.net_effective(u), f"{r['listing_id']}: net-effective said without the rent block's proof")
            if R.dog_open(u):                                         # dogs are the open item
                self.assertIn(m["subs"]["dog"], ("conflicting", "unsettled"), r["listing_id"])
                if m["subs"]["dog"] == "conflicting":
                    self.assertTrue(R.dog_open(u) == "conflict" or R.get(u, "dog", "allowed") == "conflicting", r["listing_id"])


class Subheads(unittest.TestCase):
    COLS = ("sub_cost", "sub_parking", "sub_dog", "sub_building")

    def test_unknown_parking_gets_an_ask_line(self):
        row = run([unit("a", parking={"type": None, "fee": None, "fee_note": None})])["a"]
        self.assertRegex(row["sub_parking"].lower(), r"ask|question")
        self.assertNotRegex(row["sub_parking"].lower(), r"garage|indoors|free|included")

    def test_unpriced_garage_says_the_price_is_missing(self):
        row = run([unit("a", parking={"type": "garage: fee not stated", "fee": None, "fee_note": ""})])["a"]
        ask = r"ask|in writing|question|not published|unpublished|missing|not shared|leaves it out"
        self.assertRegex(row["sub_parking"].lower(), ask)
        for t in dict(R.SUBS["parking"])["garage_unpriced"]:
            self.assertRegex(t.lower(), ask, t)

    def test_priced_garage_and_included_spot(self):
        self.assertEqual(meta(run([unit("a")])["a"])["subs"]["parking"], "garage_priced")
        inc = unit("a", parking={"type": "lot: assigned", "fee": 0.0, "fee_note": "a spot is included or free: assigned"})
        self.assertEqual(meta(run([inc])["a"])["subs"]["parking"], "included")

    def test_unknown_pet_rent(self):
        row = run([unit("a", dog={"allowed": "yes", "weight_limit_lb": None, "pet_rent": None})])["a"]
        self.assertRegex(row["sub_dog"].lower(), r"ask|question|unstated|missing|find out|off the page|unpublished")

    def test_nothing_distinctive_stays_empty(self):
        row = run([unit("a", cost_check={"cap_margin": 250})])["a"]      # known pet rent, no amenities, mid budget
        self.assertEqual(row["sub_cost"], "")
        self.assertEqual(row["sub_dog"], "")
        self.assertEqual(row["sub_building"], "")


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
            self.assertEqual(sentence_count(text, top), 2, text)
            pts = points(r)
            self.assertTrue(R.POINTS_COUNT[0] <= len(pts) <= R.POINTS_COUNT[1], pts)
            self.assertEqual(sum(p["icon"] == "warning" for p in pts), 1, pts)
            self.assertEqual(len({p["text"] for p in pts}), len(pts), pts)
            mask = "|".join(re.escape(str(x)) for x in sorted((n for n in names(top) if n), key=lambda n: -len(str(n)))) or "$^"
            for p in pts:
                self.assertEqual(set(p), {"icon", "text"})
                self.assertIn(p["icon"], R.ICONS)
                self.assertLessEqual(len(p["text"].split()), R.POINT_MAX_WORDS + len(str(top["moments"]["wake"].get("park") or "").split()), p["text"])
            for t in [text] + [p["text"] for p in pts]:
                for n in numbers(t):
                    self.assertIn(n, ok, f"{bid}: '{n}' is not in the building's fields: {t}")
                self.assertIsNone(STYLE.search(re.sub(mask, "NAME", t)), t)
                self.assertIsNone(STAGE.search(re.sub(mask, "NAME", t)), t)
            # the two sentences and the points do not say the same thing twice
            lead = re.findall(r"[a-z#'é$-]+", re.sub(r"\d[\d,.]*", "#", text.lower()))
            runs = {" ".join(lead[i:i + 6]) for i in range(len(lead) - 5)}
            for p in pts:
                w = re.findall(r"[a-z#'é$-]+", re.sub(r"\d[\d,.]*", "#", p["text"].lower()))
                for i in range(len(w) - 5):
                    self.assertNotIn(" ".join(w[i:i + 6]), runs, f"{bid}: a point repeats the sentences: {p['text']}")
            if not R.get(top, "parking", "type"):                    # parking not published: an ask, never a description
                self.assertNotRegex(re.sub(mask, "NAME", text).lower(), r"garage|parking|\blot\b")
                self.assertFalse([p for p in pts if p["icon"] == "parking"], pts)

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
        self.assertNotRegex(text.lower(), r"free parking|parking is free|included")

    def test_the_warning_is_the_most_pressing_thing_to_ask(self):
        ask = {"asterisk": True, "what": "elevator", "why": "x", "question": "Is there one?"}
        b = buildings([unit("a", confirm=ask, parking={"type": None, "fee": None, "fee_note": None})])["b-a"]
        self.assertEqual(json.loads(b["facts_used_json"])["warning"], "elevator_open")
        self.assertFalse([p for p in points(b) if "elevator building" in p["text"].lower() or "has an elevator" in p["text"].lower()])
        b = buildings([unit("a")])["b-a"]                             # garage priced, pet rent known, nothing unknown
        self.assertEqual(json.loads(b["facts_used_json"])["warning"], "tour")

    def test_only_pool_is_against_the_buildings_of_the_neighbourhood(self):
        us = [unit("a", building="B1", amenities={"pool": "pool"}), unit("b", building="B2", scores={"hood_rank": 2.0}),
              unit("c", building="B3", scores={"hood_rank": 3.0})]
        peers = [R.building_facts([u]) for u in us]
        self.assertIn("only_pool", {c[1] for c in R.building_conditions(peers[0], peers)})
        self.assertNotIn("only_pool", {c[1] for c in R.building_conditions(peers[1], peers)})

    def test_every_building_on_the_page(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        self.check(units)
        rows = R.build_buildings(units)
        self.assertEqual(rows, R.build_buildings(units))
        d = R.building_distribution(rows)
        self.assertLessEqual(d["building sentence"]["top_share"], R.LINE_SHARE + 1e-9, d["building sentence"])
        self.assertLessEqual(d["warning wording"]["top_share"], R.CATCH_SHARE + 1e-9, d["warning wording"])
        last = {}
        for r in rows:                                               # neighbouring buildings do not open the same way
            hood = json.loads(r["facts_used_json"])["hood_id"]
            self.assertNotEqual(last.get(hood), R.open3(r["about_building"]), r["building_id"])
            last[hood] = R.open3(r["about_building"])


class Numbers(unittest.TestCase):
    def check(self, units):
        by_b = {}
        for u in units:
            by_b.setdefault(u.get("building_id") or u["id"], []).append(u)
        rows = run(units)
        for u in units:
            ok = allowed_numbers(u, (len(by_b[u.get("building_id") or u["id"]]),))
            r = rows[u["id"]]
            for col in ("host_line", "host_catch"):
                for n in numbers(r[col]):
                    self.assertIn(n, ok, f"{u['id']} {col}: '{n}' is not in the unit's fields: {r[col]}")
            self.assertLessEqual(len(r["host_line"].split()), R.MAX_WORDS, r["host_line"])
            self.assertIn(sentence_count(r["host_line"], u), (1, 2), r["host_line"])
            self.assertEqual(sentence_count(r["host_catch"], u), 1, r["host_catch"])
            q = str(R.get(u, "confirm", "question") or "\0")
            both = (r["host_line"] + " " + r["host_catch"]).replace(q, "")
            self.assertNotRegex(both, r"[—–]|\b(stunning|nestled|boasts|vibrant|luxury|oasis|gem)\b|scorecard")
            self.assertNotRegex(both.lower(), r"crime|violent|burglar|theft|per 1,000|safe|police", "no crime or safety wording")
            self.assertIsNone(STAGE.search(both), both)
            for c in Subheads.COLS:
                self.assertLessEqual(len(r[c].split()), R.SUB_MAX_WORDS, r[c])
                self.assertNotRegex(r[c], r"\d", r[c])

    def test_synthetic_units(self):
        us = [unit("a", building="B", all_in=2111, sqft=913.0, floor=14.0, amenities={"pool": "pool", "doorman": "24h"}),
              unit("b", building="B", scores={"hood_rank": 2.0}, available="2026-12-07", rent={"free_months": "2"},
                   parking={"type": "covered: carport", "fee": 45.0, "fee_note": "single price stated"}),
              unit("c", scores={"hood_rank": 3.0}, moments={"wake": {"park": "Pier 4 Park", "park_walk_min": 2.4,
                                                                       "dog_park": "Run 105", "dog_park_m": 480}})]
        self.check(us)

    def test_every_unit_on_the_page(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        self.check(units)
        rows = R.build(units)
        self.assertEqual(len(rows), len(units))
        self.assertEqual(rows, R.build(units))


def groups(rows, key):
    """rows of R.build (which come out in neighbourhood rank order) -> {hood_id or building_id: [row, ...]}"""
    out = {}
    for r in rows:
        out.setdefault(meta(r)[key], []).append(r)
    return out


class Repetition(unittest.TestCase):
    """What repeats on neighbouring cards is what the reader notices."""

    def check_neighbours(self, rows):
        for key in ("hood_id", "building_id"):
            for name, group in groups(rows, key).items():
                for a, b in itertools.combinations(group[:3], 2):
                    self.assertNotEqual(meta(a)["angle"], meta(b)["angle"], f"{name}: two of the first three lead with the same angle")
                    self.assertNotEqual(a["host_catch"], b["host_catch"], f"{name}: two of the first three share a catch")
                    self.assertNotEqual(a["host_line"], b["host_line"], name)
                for a, b in zip(group, group[1:]):
                    self.assertNotEqual(R.open3(a["host_line"]), R.open3(b["host_line"]),
                                        f"{name}: neighbouring units open with the same three words: {a['host_line'][:40]}")
                    self.assertNotEqual(meta(a)["pattern"], meta(b)["pattern"], name)
                    self.assertNotEqual(a["host_catch"], b["host_catch"], name)
                    if key == "hood_id":
                        for c in Subheads.COLS:
                            if a[c]:
                                self.assertNotEqual(a[c], b[c], f"{name}: neighbouring units share the subhead '{a[c]}'")

    def test_identical_units_in_one_building_still_get_three_angles(self):
        us = [unit(f"u{i}", building="B", scores={"hood_rank": float(i + 1)}) for i in range(8)]   # eight identical units
        self.check_neighbours(R.build(us))

    def test_identical_single_unit_buildings_still_get_three_angles(self):
        us = [unit(f"u{i}", scores={"hood_rank": float(i + 1)}) for i in range(8)]
        self.check_neighbours(R.build(us))

    def test_units_with_nothing_published_still_get_three_angles(self):
        bare = dict(all_in=None, sqft=None, floor=None, floor_basis="unknown", available=None, beds=None,
                    parking={"type": None, "fee": None, "fee_note": None}, cost_check={"cap_margin": None})
        us = [unit(f"u{i}", building="B", scores={"hood_rank": float(i + 1)}, **bare) for i in range(5)]
        self.check_neighbours(R.build(us))

    def test_units_with_the_same_caution_get_different_catches(self):
        special = {"asterisk": True, "needs_call": True}
        us = [unit("a", building="B", rent=special), unit("b", building="B", rent=special, scores={"hood_rank": 2.0}),
              unit("c", building="B", rent=special, scores={"hood_rank": 3.0}, floor=None, floor_basis="unknown")]
        rows = run(us)
        self.assertEqual(len({rows[k]["host_catch"] for k in "abc"}), 3)
        self.assertEqual(catch_kind(rows["a"]), "rent:needs_call")
        self.assertEqual(catch_kind(rows["c"]), "floor:unpublished")   # its second real caution, so the three differ
        self.assertEqual(meta(rows["c"])["subs"]["cost"], "ambiguous_rent")           # the special is still flagged

    def test_an_open_gate_question_is_never_swapped_out(self):
        ask = {"asterisk": True, "what": "elevator", "why": "x", "question": "Does it have one?"}
        us = [unit(f"u{i}", building="B", confirm=ask, scores={"hood_rank": float(i + 1)}) for i in range(3)]
        rows = R.build(us)
        self.assertEqual({catch_kind(r) for r in rows}, {"confirm:elevator"})
        self.assertEqual(len({r["host_catch"] for r in rows}), 3)

    def test_the_best_unit_of_a_building_can_be_the_pick_and_never_cites_a_score(self):
        us = [unit(f"u{i}", building="B", scores={"hood_rank": float(i + 1)}) for i in range(4)]
        picks = 0
        for salt in range(40):                                        # different ids, so different seeded choices
            rows = R.build([dict(u, id=f"{u['id']}-{salt}") for u in us])
            picks += cond(rows[0]) == "pick"
            for r in rows:
                self.assertNotRegex(r["host_line"].lower(), r"scorecard|first of|ranks? ")
            for r in rows[1:]:
                self.assertNotEqual(cond(r), "pick")
        self.assertGreater(picks, 0)

    def test_every_neighbourhood_and_building_on_the_page(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        self.check_neighbours(R.build(units))

    def test_no_wording_passes_its_share_of_the_page(self):
        units = page_units()
        if units is None:
            self.skipTest("site/data.json is not here")
        rows = R.build(units)
        d = R.distribution(rows)
        print()
        for name, x in {**d, **R.building_distribution(R.build_buildings(units))}.items():
            print(f"    {name:22} commonest on {x['top_count']:3} ({x['top_share']:.1%}), {x['distinct']} distinct")
        self.assertLessEqual(d["lead wording"]["top_share"], R.LINE_SHARE, d["lead wording"])
        self.assertLessEqual(d["second-sentence frame"]["top_share"], R.LINE_SHARE, d["second-sentence frame"])
        self.assertLessEqual(d["catch wording"]["top_share"], R.CATCH_SHARE, d["catch wording"])
        for c in Subheads.COLS:
            self.assertLessEqual(d[c]["top_share"], R.LINE_SHARE, d[c])
        # the same thresholds on the finished sentences, whatever the ids say
        lead = Counter(re.sub(r"\d[\d,.]*", "#", r["host_line"].split(". ")[0]) for r in rows).most_common(1)[0]
        catch = Counter(re.sub(r"\d[\d,.]*", "#", r["host_catch"]) for r in rows).most_common(1)[0]
        self.assertLessEqual(lead[1] / len(rows), R.LINE_SHARE, lead)
        self.assertLessEqual(catch[1] / len(rows), R.CATCH_SHARE, catch)


if __name__ == "__main__":
    unittest.main(verbosity=1)
