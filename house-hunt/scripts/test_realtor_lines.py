#!/usr/bin/env python3
"""Tests for scripts/realtor_lines.py.

Run from the house-hunt folder:  python3 scripts/test_realtor_lines.py     (or: python3 -m pytest scripts/test_realtor_lines.py)

They cover pattern selection, the handling of unknowns, the rule that no number is printed unless it is in the unit's
own fields, the adjacent-pattern rule, stability across reruns and the length limits. The last group runs the same
checks over every unit in site/data.json when that file is present, so the tests also work as a check after a rerun.
"""
import copy
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import realtor_lines as R  # noqa: E402

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def unit(uid, hood="xx:test", **over):
    """A complete synthetic unit with nothing remarkable about it; `over` replaces top-level keys."""
    u = {
        "id": uid, "hood_id": hood, "beds": 1, "sqft": 700.0, "floor": 3.0, "floor_basis": "confirmed",
        "available": "now",
        "rent": {"listed": 2300, "basis_kind": "listed", "asterisk": False, "needs_call": False, "free_months": None,
                 "lease_months": 12.0},
        "all_in": 2500, "all_in_unknown": [],
        "dog": {"allowed": "yes", "weight_limit_lb": None, "pet_rent": 50.0},
        "parking": {"type": "garage: garage, $150/mo", "rank": 4.0, "fee": 150.0, "fee_note": "single price stated"},
        "amenities": {"pool": None, "doorman": None, "gym": None, "in_unit_laundry": None, "dog_amenities": None},
        "moments": {"wake": {"park": "Test Park", "park_walk_min": 9.0, "dog_park": "Test Dog Run", "dog_park_m": 2500},
                    "after": {"restaurants_800m": 6}, "night": {"violent_per_1000": 2.0},
                    "sun": {"drive_min": 40.0}},
        "scores": {"hood_rank": 1.0, "parts": {"safety": 60, "building": 55, "cost": 50, "car": 70, "space": 45,
                                                 "distance": 30, "dog": 40, "daily": 35}},
        "confirm": {"asterisk": False, "what": None, "why": None, "question": None},
        "cost_check": {"cap_margin": 500, "unknown_count": 0, "lease_term_months": 12.0},
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(u.get(k), dict):
            u[k] = {**u[k], **v}
        else:
            u[k] = v
    return u


def run(units):
    return {r["listing_id"]: r for r in R.build(units)}


def pattern(row):
    return json.loads(row["facts_used_json"])["pattern"]


def catch_kind(row):
    return json.loads(row["facts_used_json"])["catch_kind"]


def numbers(text):
    return [n.replace(",", "").rstrip(".") for n in NUMBER.findall(text)]


def allowed_numbers(u, n_peers):
    """Every number a line about this unit may contain, worked out from the unit's fields without using the
    generator's own templates: its figures, the size of its neighbourhood group, and the page's fixed 800 m wording."""
    ok = {str(n_peers), "10", "12"}                           # "10-minute walk", "12-month lease"
    if u.get("beds") == 1:
        ok.add("1")                                           # "1-bedroom"
    def put(x):
        v = R.num(x)
        if v is not None:
            ok.add(str(int(round(v))))
            ok.add(f"{v:.1f}")
    for path in (("all_in",), ("sqft",), ("floor",), ("cost_check", "cap_margin"), ("parking", "fee"),
                 ("rent", "free_months"), ("rent", "lease_months"), ("cost_check", "lease_term_months"),
                 ("moments", "wake", "park_walk_min"), ("moments", "sun", "drive_min"),
                 ("moments", "after", "restaurants_800m"),
                 ("scores", "hood_rank")):
        put(R.get(u, *path))
    m = R.num(R.get(u, "moments", "wake", "dog_park_m"))
    if m is not None:
        ok.add(f"{max(0.1, round(m / 1609.34, 1)):.1f}")
    if R.get(u, "amenities", "doorman") == "24h":
        ok.add("24")
    try:
        ok.add(str(date.fromisoformat(str(u.get("available"))[:10]).day))
    except ValueError:
        pass
    for text in (R.get(u, "confirm", "question"), R.get(u, "moments", "wake", "park"),
                 R.get(u, "moments", "wake", "dog_park")):          # a name or a question quoted from the unit
        ok.update(numbers(str(text or "")))
    return ok


def sentence_count(text, u):
    for name in (R.get(u, "moments", "wake", "park"), R.get(u, "moments", "wake", "dog_park"),
                 R.get(u, "confirm", "question")):
        if name:
            text = text.replace(str(name), "NAME")
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


class Library(unittest.TestCase):
    def test_at_least_25_patterns(self):
        self.assertGreaterEqual(len(set(R.PATTERN_IDS)), 25)

    def test_every_pattern_the_code_can_emit_is_listed(self):
        src = Path(R.__file__).read_text(encoding="utf-8")
        emitted = set(re.findall(r'add\(\s*[\d+\- a-z]+,\s*"([a-z_]+)",\s*"[a-z]+",', src))
        self.assertTrue(emitted, "no patterns found in the source")
        self.assertEqual(emitted - set(R.PATTERN_IDS), set())


class Selection(unittest.TestCase):
    def test_cheapest_of_three_leads_with_the_price(self):
        us = [unit("a", all_in=2100, scores={"hood_rank": 2.0}), unit("b", all_in=2600, scores={"hood_rank": 1.0}),
              unit("c", all_in=2700, scores={"hood_rank": 3.0})]
        rows = run(us)
        self.assertIn(pattern(rows["a"]), ("cheapest_a", "cheapest_b"))
        self.assertIn("2,100", rows["a"]["host_line"])
        self.assertIn("3", numbers(rows["a"]["host_line"]))

    def test_only_pool_beats_everything_else(self):
        us = [unit("a", amenities={"pool": "pool"}, all_in=2100, sqft=900.0), unit("b", scores={"hood_rank": 2.0}),
              unit("c", scores={"hood_rank": 3.0})]
        self.assertIn(pattern(run(us)["a"]), ("only_pool_a", "only_pool_b"))

    def test_only_garage(self):
        lot = {"type": "lot: surface", "fee": None, "fee_note": ""}
        us = [unit("a", scores={"hood_rank": 3.0}), unit("b", parking=lot, scores={"hood_rank": 1.0}, all_in=2400),
              unit("c", parking=lot, scores={"hood_rank": 2.0}, sqft=800.0)]
        self.assertIn(pattern(run(us)["a"]), ("only_garage_a", "only_garage_b"))

    def test_biggest_and_highest_floor(self):
        us = [unit("a", sqft=950.0, scores={"hood_rank": 2.0}), unit("b", all_in=2400, scores={"hood_rank": 3.0}),
              unit("c", floor=9.0, scores={"hood_rank": 4.0}, all_in=2450), unit("d", all_in=2460)]
        rows = run(us)
        self.assertIn(pattern(rows["a"]), ("biggest_a", "biggest_b"))
        self.assertIn(pattern(rows["c"]), ("highest_a", "highest_b"))

    def test_soonest_available(self):
        us = [unit("a", available="now", scores={"hood_rank": 3.0}),
              unit("b", available="2026-12-01", scores={"hood_rank": 1.0}, all_in=2400),
              unit("c", available="2026-12-10", scores={"hood_rank": 2.0}, sqft=800.0)]
        self.assertEqual(pattern(run(us)["a"]), "soonest_now")

    def test_a_tie_is_not_called_the_best(self):
        us = [unit("a", scores={"hood_rank": 1.0}), unit("b", scores={"hood_rank": 2.0})]      # identical units
        for r in run(us).values():
            self.assertNotRegex(pattern(r), r"^(cheapest|biggest|highest|only_|soonest)")

    def test_alone_in_its_neighbourhood_claims_no_ranking(self):
        row = run([unit("a")])["a"]
        self.assertNotRegex(pattern(row), r"^(cheapest|biggest|highest|only_|soonest|top_rank)")

    def test_adjacent_units_never_share_a_pattern(self):
        us = [unit(f"u{i}", scores={"hood_rank": float(i + 1)}) for i in range(8)]             # eight identical units
        rows = R.build(us)
        pats = [pattern(r) for r in rows]
        for a, b in zip(pats, pats[1:]):
            self.assertNotEqual(a, b)

    def test_rerun_gives_the_same_text(self):
        us = [unit(f"u{i}", scores={"hood_rank": float(i + 1)}, all_in=2400 + 10 * i) for i in range(6)]
        self.assertEqual(R.build(copy.deepcopy(us)), R.build(copy.deepcopy(us)))
        self.assertEqual(R.build(us), R.build(list(reversed(us))))            # input order does not matter


class Unknowns(unittest.TestCase):
    def test_no_parking_type_is_not_described_and_becomes_the_catch(self):
        u = unit("a", parking={"type": None, "fee": None, "fee_note": None})
        row = run([u])["a"]
        self.assertNotRegex(row["host_line"].lower(), r"garage|parking|\blot\b|car ")
        self.assertEqual(catch_kind(row), "unknown:parking")
        self.assertRegex(row["host_catch"].lower(), r"parking isn't published|says nothing about parking")

    def test_unpriced_garage_is_never_free(self):
        u = unit("a", parking={"type": "garage: garage; fee not stated", "fee": None, "fee_note": ""})
        row = run([u, unit("b", parking={"type": None, "fee": None}, scores={"hood_rank": 2.0})])["a"]
        text = (row["host_line"] + " " + row["host_catch"]).lower()
        self.assertRegex(text, r"fee (is )?not published|does not publish the fee")
        self.assertNotRegex(text, r"no parking fee|free parking|parking is free|included")

    def test_a_zero_fee_without_an_included_note_is_not_a_price(self):
        u = unit("a", parking={"type": "garage", "fee": 0.0, "fee_note": "free only for a limited time; fee not stated"})
        text = run([u])["a"]["host_line"].lower()
        self.assertNotRegex(text, r"included|\$0|free")

    def test_included_parking_needs_the_note(self):
        u = unit("a", parking={"type": "lot: assigned", "fee": 0.0, "fee_note": "a spot is included or free: assigned"})
        self.assertIn("included", run([u])["a"]["host_line"].lower() + pattern(run([u])["a"]))

    def test_unknown_size_and_floor_are_left_out(self):
        u = unit("a", sqft=None, floor=None, floor_basis="unknown")
        line = run([u])["a"]["host_line"].lower()
        self.assertNotIn("square feet", line)
        self.assertNotIn("floor", line)

    def test_an_inferred_floor_is_not_stated_as_fact(self):
        us = [unit("a", floor=12.0, floor_basis="inferred"), unit("b", scores={"hood_rank": 2.0})]
        self.assertNotIn("floor", run(us)["a"]["host_line"].lower())

    def test_missing_all_in_prints_no_price(self):
        u = unit("a", all_in=None, cost_check={"cap_margin": None})
        line = run([u])["a"]["host_line"]
        self.assertNotIn("all in", line)
        self.assertNotIn("2,500", line)

    def test_asterisk_comes_first_in_the_catch(self):
        u = unit("a", confirm={"asterisk": True, "what": "elevator", "why": "x", "question": "Does it have one?"},
                 parking={"type": None, "fee": None})
        self.assertEqual(catch_kind(run([u])["a"]), "confirm:elevator")

    def test_an_unmapped_asterisk_quotes_the_units_own_question(self):
        u = unit("a", confirm={"asterisk": True, "what": "something new", "why": "x", "question": "Is it real?"})
        self.assertIn("Is it real?", run([u])["a"]["host_catch"])

    def test_weakest_fact_when_nothing_is_open(self):
        row = run([unit("a")])["a"]                                   # distance scores lowest in the synthetic unit
        self.assertEqual(catch_kind(row), "weak:distance")
        self.assertIn("40", numbers(row["host_catch"]))

    def test_safety_is_never_the_catch(self):
        u = unit("a", scores={"hood_rank": 1.0, "parts": {"safety": 1, "building": 55, "cost": 50, "car": 70, "space": 45,
                                                            "distance": 30, "dog": 40, "daily": 35}})
        row = run([u])["a"]
        self.assertEqual(catch_kind(row), "weak:distance")

    def test_unpublished_costs_near_the_cap(self):
        u = unit("a", all_in_unknown=["pet rent", "parking fee"], cost_check={"cap_margin": 120})
        row = run([u])["a"]
        self.assertEqual(catch_kind(row), "unknown:costs")
        self.assertIn("not published", row["host_catch"])


class Subheads(unittest.TestCase):
    COLS = ("sub_cost", "sub_parking", "sub_dog", "sub_building")

    def test_library_lines_are_short_and_carry_no_numbers(self):
        for section, entries in R.SUBS.items():
            for key, options in entries:
                for text in options:
                    self.assertLessEqual(len(text.split()), R.SUB_MAX_WORDS, text)
                    self.assertNotRegex(text, r"\d", text)
                    self.assertNotRegex(text.lower(), r"crime|violent|theft|safe|police|[—–]|\b(may|might|probably|perhaps)\b", text)
                    self.assertEqual(len(re.findall(r"[.!?](\s|$)", text)), 1, text)

    def test_unknown_parking_gets_an_ask_line(self):
        row = run([unit("a", parking={"type": None, "fee": None, "fee_note": None})])["a"]
        self.assertRegex(row["sub_parking"].lower(), r"ask|question")
        self.assertNotRegex(row["sub_parking"].lower(), r"garage|indoors|free|included")

    def test_unpriced_garage_says_the_price_is_missing(self):
        row = run([unit("a", parking={"type": "garage: fee not stated", "fee": None, "fee_note": ""})])["a"]
        self.assertRegex(row["sub_parking"].lower(), r"don't publish the price|no price listed")

    def test_priced_garage_and_included_spot(self):
        self.assertEqual(json.loads(run([unit("a")])["a"]["facts_used_json"])["subs"]["parking"], "garage_priced")
        inc = unit("a", parking={"type": "lot: assigned", "fee": 0.0, "fee_note": "a spot is included or free: assigned"})
        self.assertEqual(json.loads(run([inc])["a"]["facts_used_json"])["subs"]["parking"], "included")

    def test_unknown_pet_rent_and_conflicting_policy(self):
        row = run([unit("a", dog={"allowed": "yes", "weight_limit_lb": None, "pet_rent": None})])["a"]
        self.assertRegex(row["sub_dog"].lower(), r"ask")
        row = run([unit("a", dog={"allowed": "conflicting", "weight_limit_lb": None, "pet_rent": None})])["a"]
        self.assertRegex(row["sub_dog"].lower(), r"in writing|confirm")

    def test_nothing_distinctive_stays_empty(self):
        row = run([unit("a", cost_check={"cap_margin": 250})])["a"]      # known pet rent, no amenities, mid budget
        self.assertEqual(row["sub_cost"], "")
        self.assertEqual(row["sub_dog"], "")
        self.assertEqual(row["sub_building"], "")

    def test_every_unit_on_the_page(self):
        if not R.DATA.exists():
            self.skipTest("site/data.json is not here")
        for r in R.build(json.loads(R.DATA.read_text(encoding="utf-8"))["units"]):
            for c in self.COLS:
                self.assertLessEqual(len(r[c].split()), R.SUB_MAX_WORDS, r[c])
                self.assertNotRegex(r[c], r"\d", r[c])


class Numbers(unittest.TestCase):
    def check(self, units):
        by_hood = {}
        for u in units:
            by_hood.setdefault(u.get("hood_id"), []).append(u)
        rows = run(units)
        for u in units:
            ok = allowed_numbers(u, len(by_hood[u.get("hood_id")]))
            r = rows[u["id"]]
            for col in ("host_line", "host_catch"):
                for n in numbers(r[col]):
                    self.assertIn(n, ok, f"{u['id']} {col}: '{n}' is not in the unit's fields: {r[col]}")
            self.assertLessEqual(len(r["host_line"].split()), R.MAX_WORDS, r["host_line"])
            self.assertIn(sentence_count(r["host_line"], u), (1, 2), r["host_line"])
            self.assertEqual(sentence_count(r["host_catch"], u), 1, r["host_catch"])
            self.assertNotRegex(r["host_line"] + r["host_catch"], r"[—–]|\b(stunning|nestled|boasts|vibrant)\b")
            self.assertNotRegex((r["host_line"] + r["host_catch"]).lower(),
                                r"crime|violent|burglar|theft|per 1,000|safe|police", "no crime or safety wording")

    def test_synthetic_units(self):
        us = [unit("a", all_in=2111, sqft=913.0, floor=14.0, amenities={"pool": "pool", "doorman": "24h"}),
              unit("b", scores={"hood_rank": 2.0}, available="2026-12-07", rent={"free_months": "2"},
                   parking={"type": "covered: carport", "fee": 45.0, "fee_note": "single price stated"}),
              unit("c", scores={"hood_rank": 3.0}, moments={"wake": {"park": "Pier 4 Park", "park_walk_min": 2.4,
                                                                       "dog_park": "Run 105", "dog_park_m": 480}})]
        self.check(us)

    def test_every_unit_on_the_page(self):
        if not R.DATA.exists():
            self.skipTest("site/data.json is not here")
        units = json.loads(R.DATA.read_text(encoding="utf-8"))["units"]
        self.check(units)
        rows = R.build(units)
        self.assertEqual(len(rows), len(units))
        last = {}
        for r in rows:                                               # rows come out in neighbourhood rank order
            meta = json.loads(r["facts_used_json"])
            self.assertNotEqual(last.get(meta["hood_id"]), meta["pattern"], r["listing_id"])
            last[meta["hood_id"]] = meta["pattern"]
        self.assertEqual(rows, R.build(units))


if __name__ == "__main__":
    unittest.main(verbosity=1)
