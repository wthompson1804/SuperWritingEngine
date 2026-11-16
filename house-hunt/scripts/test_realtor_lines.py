#!/usr/bin/env python3
"""Tests for scripts/realtor_lines.py.

Run from the house-hunt folder:  python3 scripts/test_realtor_lines.py     (or: python3 -m pytest scripts/test_realtor_lines.py)

They cover the sentence library (at least 8 different sentences per condition, house style), selection of the lead,
the handling of unknowns, the rule that no number is printed unless it is in the unit's own fields, the rules against
repetition (shares of the page, the top three of a neighbourhood, neighbouring units), stability across reruns and
the length limits. The last groups run the same checks over every unit in site/data.json when that file is present,
so the tests also work as a check after a rerun.
"""
import copy
import itertools
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


def cond(row):
    return pattern(row).rsplit("_", 1)[0]


def meta(row):
    return json.loads(row["facts_used_json"])


def catch_kind(row):
    return json.loads(row["facts_used_json"])["catch_kind"]


def numbers(text):
    return [n.replace(",", "").rstrip(".") for n in NUMBER.findall(text)]


def allowed_numbers(u, n_peers):
    """Every number a line about this unit may contain, worked out from the unit's fields without using the
    generator's own templates: its figures, the size of its neighbourhood group, and the page's fixed 800 m wording."""
    ok = {str(n_peers), "10", "12"}                           # "10-minute walk", "12-month lease"
    for path in (("listing_age_days",), ("amenities", "year_built")):
        v = R.num(R.get(u, *path))
        if v is not None:
            ok.add(str(int(v)))
    for path in (("moments", "sat", "train_station_m"), ("moments", "work", "supermarket_m")):
        v = R.num(R.get(u, *path))
        if v is not None:
            ok.add(R.miles(v))
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
    for text in (R.get(u, "confirm", "question"),) + names(u):   # a name or a question quoted from the unit
        ok.update(numbers(str(text or "")))
    return ok


def names(u):
    return (R.get(u, "moments", "wake", "park"), R.get(u, "moments", "wake", "dog_park"),
            R.get(u, "moments", "sat", "train_station"), R.get(u, "moments", "work", "supermarket"))


def sentence_count(text, u):
    for name in sorted((n for n in names(u) + (R.get(u, "confirm", "question"),) if n), key=lambda x: -len(str(x))):
        if name:
            text = text.replace(str(name), "NAME")
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


STYLE = re.compile(r"[—–?]|\b(stunning|nestled|boasts?|vibrant|luxur\w*|oasis|gem|bustling|breathtaking)\b|"
                   r"\bnot\b[^.]{0,60}\bbut\b|\byears?\b|scorecard|crime|violent|burglar|theft|per 1,000|safe|police", re.I)


def families():
    """Every (family name, [sentences]) in the library."""
    for cond, (_, texts) in R.LEADS.items():
        yield "lead:" + cond, texts
    for kind, texts in R.CATCHES.items():
        yield "catch:" + kind, texts
    for section, entries in R.SUBS.items():
        for key, texts in entries:
            yield f"sub:{section}.{key}", texts
    for name, texts in R.FRAMES.items():
        yield "frame:" + name, texts


class Library(unittest.TestCase):
    def test_every_condition_has_at_least_8_sentences(self):
        for name, texts in families():
            self.assertGreaterEqual(len(texts), R.MIN_WORDINGS, name)
            self.assertEqual(len(set(texts)), len(texts), f"{name}: a sentence appears twice")

    def test_sentences_of_a_condition_start_differently(self):
        # different sentences, never a template with a synonym swapped: no shared opening inside a condition
        for name, texts in families():
            if name.startswith("frame:"):
                continue
            opens = [" ".join(re.findall(r"[A-Za-z{}_']+", t.lower())[:3]) for t in texts]
            dup = [o for o in set(opens) if opens.count(o) > 1]
            self.assertEqual(dup, [], f"{name}: more than one sentence opens with {dup}")

    def test_no_sentence_is_shared_between_conditions(self):
        seen = {}
        for name, texts in families():
            for t in texts:
                if name.split(":")[0] in ("lead", "catch"):
                    self.assertNotIn(t, seen, f"{name} repeats a sentence of {seen.get(t)}")
                    seen[t] = name

    def test_house_style(self):
        for name, texts in families():
            for t in texts:
                self.assertIsNone(STYLE.search(t), f"{name}: {t}")
                if not name.startswith("frame:") and "{q}" not in t:
                    self.assertEqual(len(re.findall(r"[.!](\s|$)", t)), 1, f"{name}: one sentence wanted: {t}")
                if name.startswith("lead:"):
                    self.assertLessEqual(len(t.split()), 24, t)

    def test_no_typed_numbers(self):
        # the only digits typed in the library are fixed wordings: a 12-month lease, a 24-hour desk
        for name, texts in families():
            for t in texts:
                bare = re.sub(r"\{[A-Za-z_0-9]+\}", "", t).replace("12-month", "").replace("24-hour", "").replace("24 hours", "")
                self.assertNotRegex(bare, r"\d", f"{name}: {t}")

    def test_unpriced_garage_leads_all_say_the_fee_is_missing(self):
        for t in R.LEADS["garage_unpriced"][1]:
            self.assertRegex(t, R.UNPRICED, t)
            self.assertNotRegex(t.lower(), r"free|included")

    def test_every_pattern_id_is_listed_once(self):
        self.assertEqual(len(R.PATTERN_IDS), len(set(R.PATTERN_IDS)))
        self.assertGreaterEqual(len(R.PATTERN_IDS), 8 * len(R.LEADS))

    def test_the_rank_is_said_as_the_hosts_choice(self):
        for t in R.LEADS["pick"][1]:
            self.assertNotRegex(t.lower(), r"scorecard|rank|first of|score")


class Selection(unittest.TestCase):
    def test_cheapest_of_three_leads_with_the_price(self):
        us = [unit("a", all_in=2100, scores={"hood_rank": 2.0}), unit("b", all_in=2600, scores={"hood_rank": 1.0}),
              unit("c", all_in=2700, scores={"hood_rank": 3.0})]
        rows = run(us)
        self.assertEqual(cond(rows["a"]), "cheapest")
        self.assertIn("2,100", rows["a"]["host_line"].split(". ")[0])

    def test_only_pool_beats_everything_else(self):
        us = [unit("a", amenities={"pool": "pool"}, all_in=2100, sqft=900.0), unit("b", scores={"hood_rank": 2.0}),
              unit("c", scores={"hood_rank": 3.0})]
        self.assertEqual(cond(run(us)["a"]), "only_pool")

    def test_only_garage(self):
        lot = {"type": "lot: surface", "fee": None, "fee_note": ""}
        us = [unit("a", scores={"hood_rank": 3.0}), unit("b", parking=lot, scores={"hood_rank": 1.0}, all_in=2400),
              unit("c", parking=lot, scores={"hood_rank": 2.0}, sqft=800.0)]
        self.assertEqual(cond(run(us)["a"]), "only_garage")

    def test_biggest_and_highest_floor(self):
        us = [unit("a", sqft=950.0, scores={"hood_rank": 2.0}), unit("b", all_in=2400, scores={"hood_rank": 3.0}),
              unit("c", floor=9.0, scores={"hood_rank": 4.0}, all_in=2450), unit("d", all_in=2460)]
        rows = run(us)
        self.assertEqual(cond(rows["a"]), "biggest")
        self.assertEqual(cond(rows["c"]), "highest")

    def test_soonest_available(self):
        us = [unit("a", available="now", scores={"hood_rank": 3.0}),
              unit("b", available="2026-12-01", scores={"hood_rank": 1.0}, all_in=2400),
              unit("c", available="2026-12-10", scores={"hood_rank": 2.0}, sqft=800.0)]
        self.assertEqual(cond(run(us)["a"]), "soonest_now")

    def test_a_tie_is_not_called_the_best(self):
        us = [unit("a", scores={"hood_rank": 1.0}), unit("b", scores={"hood_rank": 2.0})]      # identical units
        for r in run(us).values():
            self.assertNotIn(cond(r), R.PEER_CONDITIONS)

    def test_alone_in_its_neighbourhood_claims_no_ranking(self):
        row = run([unit("a")])["a"]
        self.assertNotIn(cond(row), R.PEER_CONDITIONS)

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
        self.assertRegex(row["host_catch"].lower(), r"parking|car")
        self.assertRegex(row["host_catch"].lower(), r"ask|settle|silent|in writing|isn't published")

    def test_unpriced_garage_is_never_free(self):
        u = unit("a", parking={"type": "garage: garage; fee not stated", "fee": None, "fee_note": ""})
        row = run([u, unit("b", parking={"type": None, "fee": None}, scores={"hood_rank": 2.0})])["a"]
        text = (row["host_line"] + " " + row["host_catch"]).lower()
        self.assertIn("garage", text)                               # the only garage of the 2 leads the line
        self.assertRegex(text, R.UNPRICED)
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
        self.assertRegex(row["host_catch"], r"pet rent")
        self.assertIn("$120", row["host_catch"])


class Subheads(unittest.TestCase):
    COLS = ("sub_cost", "sub_parking", "sub_dog", "sub_building")

    def test_library_lines_are_short_and_carry_no_numbers(self):
        for section, entries in R.SUBS.items():
            for key, options in entries:
                for text in options:
                    self.assertLessEqual(len(text.split()), R.SUB_MAX_WORDS, text)
                    self.assertNotRegex(text, r"\d", text)
                    self.assertNotRegex(text.lower(), r"crime|violent|theft|safe|police|[—–]|\b(may|might|probably|perhaps|possibly|somewhat|fairly)\b", text)
                    self.assertEqual(len(re.findall(r"[.!?](\s|$)", text)), 1, text)

    def test_unknown_parking_gets_an_ask_line(self):
        row = run([unit("a", parking={"type": None, "fee": None, "fee_note": None})])["a"]
        self.assertRegex(row["sub_parking"].lower(), r"ask|question")
        self.assertNotRegex(row["sub_parking"].lower(), r"garage|indoors|free|included")

    def test_unpriced_garage_says_the_price_is_missing(self):
        row = run([unit("a", parking={"type": "garage: fee not stated", "fee": None, "fee_note": ""})])["a"]
        self.assertRegex(row["sub_parking"].lower(), r"price|fee|cost|charge|what it adds")
        self.assertRegex(row["sub_parking"].lower(), r"ask|in writing|question|not published|unpublished|missing|not shared|leaves it out")
        for t in dict(R.SUBS["parking"])["garage_unpriced"]:
            self.assertRegex(t.lower(), r"ask|in writing|question|not published|unpublished|missing|not shared|leaves it out", t)

    def test_priced_garage_and_included_spot(self):
        self.assertEqual(json.loads(run([unit("a")])["a"]["facts_used_json"])["subs"]["parking"], "garage_priced")
        inc = unit("a", parking={"type": "lot: assigned", "fee": 0.0, "fee_note": "a spot is included or free: assigned"})
        self.assertEqual(json.loads(run([inc])["a"]["facts_used_json"])["subs"]["parking"], "included")

    def test_unknown_pet_rent_and_conflicting_policy(self):
        row = run([unit("a", dog={"allowed": "yes", "weight_limit_lb": None, "pet_rent": None})])["a"]
        self.assertRegex(row["sub_dog"].lower(), r"ask|question|unstated|missing|find out|off the page|unpublished")
        row = run([unit("a", dog={"allowed": "conflicting", "weight_limit_lb": None, "pet_rent": None})])["a"]
        self.assertRegex(row["sub_dog"].lower(), r"in writing|confirm|ask|written|until the office")

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
            self.assertNotRegex(r["host_line"] + r["host_catch"], r"[—–]|\b(stunning|nestled|boasts|vibrant|luxury|oasis|gem)\b|scorecard")
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
        self.assertEqual(rows, R.build(units))


def by_hood(rows):
    """rows of R.build (which come out in neighbourhood rank order) -> {hood_id: [row, ...]}"""
    out = {}
    for r in rows:
        out.setdefault(meta(r)["hood_id"], []).append(r)
    return out


class Repetition(unittest.TestCase):
    """The page shows a neighbourhood's top three places together, so what repeats is what the reader notices."""

    def check_neighbours(self, rows):
        for hood, group in by_hood(rows).items():
            top = group[:3]
            for a, b in itertools.combinations(top, 2):
                self.assertNotEqual(meta(a)["angle"], meta(b)["angle"], f"{hood}: two of the top three lead with the same angle")
                self.assertNotEqual(a["host_catch"], b["host_catch"], f"{hood}: two of the top three share a catch")
                self.assertNotEqual(meta(a)["catch_id"], meta(b)["catch_id"], hood)
                self.assertNotEqual(a["host_line"], b["host_line"], hood)
            for a, b in zip(group, group[1:]):
                self.assertNotEqual(R.open3(a["host_line"]), R.open3(b["host_line"]),
                                    f"{hood}: neighbouring units open with the same three words: {a['host_line'][:40]}")
                self.assertNotEqual(meta(a)["pattern"], meta(b)["pattern"], hood)
                self.assertNotEqual(a["host_catch"], b["host_catch"], hood)
                for c in Subheads.COLS:
                    if a[c]:
                        self.assertNotEqual(a[c], b[c], f"{hood}: neighbouring units share the subhead '{a[c]}'")

    def test_identical_units_still_get_three_angles(self):
        us = [unit(f"u{i}", scores={"hood_rank": float(i + 1)}) for i in range(8)]             # eight identical units
        self.check_neighbours(R.build(us))

    def test_units_with_nothing_published_still_get_three_angles(self):
        bare = dict(all_in=None, sqft=None, floor=None, floor_basis="unknown", available=None,
                    parking={"type": None, "fee": None, "fee_note": None}, cost_check={"cap_margin": None},
                    moments={"wake": {"park": None, "park_walk_min": None, "dog_park": None, "dog_park_m": None}})
        us = [unit(f"u{i}", scores={"hood_rank": float(i + 1)}, **bare) for i in range(5)]
        self.check_neighbours(R.build(us))

    def test_top_three_with_the_same_caution_get_different_catches(self):
        special = {"asterisk": True, "needs_call": True}
        us = [unit("a", rent=special), unit("b", rent=special, scores={"hood_rank": 2.0}),
              unit("c", rent=special, scores={"hood_rank": 3.0}, parking={"type": None, "fee": None, "fee_note": None})]
        rows = run(us)
        self.assertEqual(len({rows[k]["host_catch"] for k in "abc"}), 3)
        self.assertEqual(catch_kind(rows["a"]), "rent:needs_call")
        self.assertEqual(catch_kind(rows["c"]), "unknown:parking")     # its second real caution, so the three differ
        self.assertEqual(meta(rows["c"])["subs"]["cost"], "ambiguous_rent")           # the special is still flagged

    def test_an_open_gate_question_is_never_swapped_out(self):
        ask = {"asterisk": True, "what": "elevator", "why": "x", "question": "Does it have one?"}
        us = [unit(f"u{i}", confirm=ask, scores={"hood_rank": float(i + 1)}) for i in range(3)]
        rows = R.build(us)
        self.assertEqual({catch_kind(r) for r in rows}, {"confirm:elevator"})
        self.assertEqual(len({r["host_catch"] for r in rows}), 3)

    def test_the_top_place_can_be_the_hosts_pick_and_never_cites_a_score(self):
        us = [unit(f"u{i}", scores={"hood_rank": float(i + 1)}) for i in range(4)]
        picks = 0
        for salt in range(40):                                        # different ids, so different seeded choices
            rows = R.build([dict(u, id=f"{u['id']}-{salt}") for u in us])
            picks += cond(rows[0]) == "pick"
            for r in rows:
                self.assertNotRegex(r["host_line"].lower(), r"scorecard|first of|ranks? ")
            for r in rows[1:]:
                self.assertNotEqual(cond(r), "pick")
        self.assertGreater(picks, 0)

    def test_every_neighbourhood_on_the_page(self):
        if not R.DATA.exists():
            self.skipTest("site/data.json is not here")
        self.check_neighbours(R.build(json.loads(R.DATA.read_text(encoding="utf-8"))["units"]))

    def test_no_wording_passes_its_share_of_the_page(self):
        if not R.DATA.exists():
            self.skipTest("site/data.json is not here")
        rows = R.build(json.loads(R.DATA.read_text(encoding="utf-8"))["units"])
        d = R.distribution(rows)
        print()
        for name, x in d.items():
            print(f"    {name:22} commonest on {x['top_count']:3} of {len(rows)} units ({x['top_share']:.1%}), {x['distinct']} distinct")
        self.assertLessEqual(d["lead wording"]["top_share"], R.LINE_SHARE, d["lead wording"])
        self.assertLessEqual(d["second-sentence frame"]["top_share"], R.LINE_SHARE, d["second-sentence frame"])
        self.assertLessEqual(d["catch wording"]["top_share"], R.CATCH_SHARE, d["catch wording"])
        for c in Subheads.COLS:
            self.assertLessEqual(d[c]["top_share"], R.LINE_SHARE, d[c])
        # the same thresholds on the finished sentences, whatever the ids say
        from collections import Counter
        lead = Counter(re.sub(r"\d[\d,.]*", "#", r["host_line"].split(". ")[0]) for r in rows).most_common(1)[0]
        catch = Counter(re.sub(r"\d[\d,.]*", "#", r["host_catch"]) for r in rows).most_common(1)[0]
        self.assertLessEqual(lead[1] / len(rows), R.LINE_SHARE, lead)
        self.assertLessEqual(catch[1] / len(rows), R.CATCH_SHARE, catch)


class NewAngles(unittest.TestCase):
    def test_most_room_per_dollar(self):
        us = [unit("a", all_in=2300, sqft=800.0, scores={"hood_rank": 3.0}),          # 2.9 a square foot
              unit("b", all_in=2200, sqft=500.0, scores={"hood_rank": 1.0}),          # cheapest
              unit("c", all_in=2900, sqft=900.0, scores={"hood_rank": 2.0})]          # biggest
        conds = {c[1] for c in R.lead_conditions(R.facts(us[0]), [R.facts(u) for u in us])}
        self.assertIn("value", conds)
        self.assertNotIn("cheapest", conds)
        self.assertNotIn("biggest", conds)

    def test_a_superlative_needs_every_unit_to_publish_the_figure(self):
        us = [unit("a", sqft=950.0), unit("b", sqft=700.0, scores={"hood_rank": 2.0}),
              unit("c", sqft=None, scores={"hood_rank": 3.0})]
        conds = {c[1] for c in R.lead_conditions(R.facts(us[0]), [R.facts(u) for u in us])}
        self.assertNotIn("biggest", conds)
        self.assertNotIn("value", conds)

    def test_fewest_open_questions_newest_listing_and_nearest_run(self):
        us = [unit("a", tour_questions=["q1"], listing_age_days=2.0,
                   moments={"wake": {"park": "Test Park", "park_walk_min": 9.0, "dog_park": "Near Run", "dog_park_m": 900}}),
              unit("b", tour_questions=["q1", "q2", "q3"], listing_age_days=30.0, scores={"hood_rank": 2.0}),
              unit("c", tour_questions=["q1", "q2"], scores={"hood_rank": 3.0})]
        peers = [R.facts(u) for u in us]
        conds = {c[1] for c in R.lead_conditions(peers[0], peers)}
        self.assertLessEqual({"fewest_questions", "newest", "closest_run"}, conds)
        other = {c[1] for c in R.lead_conditions(peers[1], peers)}
        self.assertFalse({"fewest_questions", "newest", "closest_run"} & other)

    def test_the_only_dog_spot_on_site(self):
        us = [unit("a", amenities={"dog_amenities": "dog park"}), unit("b", scores={"hood_rank": 2.0}),
              unit("c", scores={"hood_rank": 3.0})]
        peers = [R.facts(u) for u in us]
        self.assertIn("only_dogspot", {c[1] for c in R.lead_conditions(peers[0], peers)})


if __name__ == "__main__":
    unittest.main(verbosity=1)
