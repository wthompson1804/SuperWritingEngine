#!/usr/bin/env python3
"""Tests for scripts/check_published_text.py and for the guards it imports from scripts/check_scene_text.py.

Run from the house-hunt folder:  python3 scripts/test_check_published_text.py

The planted examples are the ones independent check 4 (docs/INDEPENDENT_CHECK_4.md, "Guards") wrote into the scene
files, the two realtor tables and site/data.json and saw pass every checker. Each must now fail. The tests work on a
copy of the page data in memory; nothing on disk is changed.
"""
import copy
import csv
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_published_text as P  # noqa: E402
import check_scene_text as G  # noqa: E402

CONCEIT = "The lawns keep their own counsel."
JARGON = "This unit passed every gate, and the all-in is under the cap."
FALSE_NUMBER = "It is about 1,400 square feet and costs about $1,200 a month with utilities and fees."
OLD_PRICE_WORDS = ("It costs about {price} a month, everything included.", "It costs about {price} a month all-in.",
                   "It costs about {price} a month all in.", "It costs about {price} a month.")


def page():
    return json.loads(P.DATA.read_text(encoding="utf-8"))


def fails(d, kind=None, oid=None, owner="text"):
    return [f for f in P.audit(d) if f.owner == owner and (kind is None or f.kind == kind) and (oid is None or f.id == oid)]


class Conceit(unittest.TestCase):
    """The noun x verb guard (a thing as the subject of a verb of intention or speech)."""

    def test_the_planted_conceits(self):
        for t in (CONCEIT, "The river tucks the town in at night.", "The dog walks you to the river each morning.",
                  "The town never sleeps.", "A park waits at the end of the block.", "The street promises quiet.",
                  "The garage forgives a late return.", "The price tells its own story."):
            self.assertTrue(G.check_plain("x", t), t)

    def test_plain_sentences_pass(self):
        for t in ("Street spaces are scarce, so ask where you would park.", "Ask the building what a space costs.",
                  "The town bans overnight street parking.", "The building has a pool.", "Residents say parking is hard.",
                  "A park is about 4 minutes on foot.", "The listing says this apartment is available now.",
                  "Most households here keep a car.", "Before you tour, ask the office what a garage space costs.",
                  "You would park in the building's garage and pay a monthly fee."):
            self.assertEqual([p for p in G.check_plain("x", t) if "intention" in p], [], t)

    def test_documented_limits(self):
        # a noun that is not on the list, and a verb in a relative clause, are not seen (docs/SCENE_TEXT_NOTES.md)
        self.assertIsNone(G.agency("The cul-de-sac keeps its secrets."))
        self.assertIsNone(G.agency("It is a town that welcomes dogs."))


class StaleWording(unittest.TestCase):
    def test_not_checked_again(self):
        for t in ("These listings were not checked again this year.", "The price has not been checked again.",
                  "This listing was not re-checked."):
            self.assertTrue(any("not checked again" in p for p in G.check_plain("x", t)), t)

    def test_queens_as_a_place(self):
        self.assertTrue(G.check_plain("x", "Compared to staying in Queens, the monthly cost goes up."))
        self.assertTrue(G.check_plain("x", "More room than Queens, and far less within walking distance."))
        self.assertEqual(G.check_plain("x", "Costs more than a typical Queens apartment."), [])


class SceneFiles(unittest.TestCase):
    """The three examples that passed in the scene CSVs."""

    @classmethod
    def setUpClass(cls):
        P.use_page(page())
        with open(G.YEARS, newline="", encoding="utf-8") as f:
            cls.years = list(csv.DictReader(f))
        with open(G.HOODS, newline="", encoding="utf-8") as f:
            cls.hoods = {r["hood_id"]: r for r in csv.DictReader(f)}

    def check(self, kind, row, **change):
        cols = G.COLUMNS[kind]
        texts = {c: row[c] or "" for c in cols}
        texts.update(change)
        key = row["year_label"] if kind == "year" else row["hood_id"]
        return G.check_row(kind, key, texts, json.loads(row["evidence_json"]))[0]

    def own_dog_hood(self):
        b = G.table(G.DOOR_SOURCE)
        for hid, g in b.groupby("hood_id"):
            if len(g) == 1 and g["own_dog_area"].mean() == 1 and hid in self.hoods:
                return self.hoods[hid]
        self.skipTest("no single-building neighborhood whose building has its own dog area is shown")

    def test_a_conceit_that_is_not_on_the_list_in_an_experience_catch(self):
        row = self.years[0]
        self.assertEqual(self.check("year", row), [])
        self.assertTrue(any("intention" in p for p in self.check("year", row, catch=CONCEIT)))

    def test_not_checked_again_in_a_neighborhood_scene(self):
        row = self.own_dog_hood()
        probs = self.check("hood", row, scene="These listings were not checked again this year.")
        self.assertTrue(any("not checked again" in p for p in probs), probs)

    def test_no_building_here_has_a_dog_park_where_the_building_has_one(self):
        row = self.own_dog_hood()
        self.assertEqual(self.check("hood", row), [])
        probs = self.check("hood", row, scene="No building here has a dog park.")
        self.assertTrue(any("own dog area" in p for p in probs), probs)

    def test_the_dog_park_is_not_the_catch_where_the_building_has_its_own(self):
        row = self.own_dog_hood()
        probs = self.check("hood", row, watch_for="The nearest dog park is far away, so weekday walks are on the leash.")
        self.assertTrue(any("dog" in p for p in probs), probs)

    def hood_where(self, test):
        b = G.table(G.DOOR_SOURCE)
        for hid, g in b.groupby("hood_id"):
            if hid in self.hoods and test(g):
                return self.hoods[hid]
        self.skipTest("no such neighborhood is shown today")

    def test_singular_and_plural_follow_the_count(self):
        many = self.hood_where(lambda g: g["n_units"].sum() >= 2)
        self.assertTrue(any("speaks of one apartment" in p for p in
                            self.check("hood", many, scene="The apartment here is large.")))
        single = self.hood_where(lambda g: g["n_units"].sum() == 1)
        self.assertTrue(any("speaks of several apartments" in p for p in
                            self.check("hood", single, scene="The apartments here are large.")))
        two = self.hood_where(lambda g: g["n_units"].sum() == 2)
        self.assertTrue(any("'typical' from 2" in p for p in self.check("hood", two, scene="The typical apartment is large.")))

    def test_one_building_is_not_each_building(self):
        single = self.hood_where(lambda g: len(g) == 1)
        self.assertTrue(any("several buildings" in p for p in
                            self.check("hood", single, watch_for="Ask each building where you would park.")))
        self.assertTrue(any("most buildings here" in p for p in
                            self.check("hood", single, good_for_her="A park is close to most buildings here.")))

    def test_a_garage_at_every_building_changes_the_parking_advice(self):
        row = self.hood_where(lambda g: g["own_garage"].mean() == 1)
        probs = self.check("hood", row, watch_for="Street parking is hard, so look for a building with a garage.")
        self.assertTrue(any("garage" in p for p in probs), probs)

    def test_a_door_distance_fact_must_come_from_the_shown_buildings(self):
        row = self.hood_where(lambda g: len(g) >= 1)
        ev = json.loads(row["evidence_json"]) + [{"claim": "x", "field": "t_restaurants_800m", "value": 1,
                                                  "source_file": G.PAGE + "#neighborhoods", "row": {"hood_id": row["hood_id"]},
                                                  "holds_if": [">=", "0"]}]
        texts = {c: row[c] or "" for c in G.COLUMNS["hood"]}
        self.assertTrue(any("door-distance fact" in p for p in G.check_row("hood", row["hood_id"], texts, ev)[0]))

    def test_an_experience_claim_needs_three_quarters_of_its_apartments(self):
        u = G._units_with_hood()
        for row in self.years:
            g = u[u["year_label"] == row["year_label"]]
            share = (g["hood_drive_min"] <= G.CLOSE_DRIVE_MIN).mean() if len(g) >= G.SMALL_EXPERIENCE else None
            if share is not None and share < G.MOST_SHARE:
                probs = self.check("year", row, promise="You stay close to your parents.")
                self.assertTrue(any("close to your parents" in p for p in probs), probs)
                return
        self.skipTest("every experience is close to her parents today")

    def test_a_small_experience_is_not_typical(self):
        for row in self.years:
            if G.is_small_experience(row["year_label"]):
                probs = self.check("year", row, promise="The typical apartment is close to dinner.")
                self.assertTrue(any("typical" in p for p in probs), probs)
                probs = self.check("year", row, catch="Only 33 percent of the listings mention parking.")
                self.assertTrue(any("percent" in p for p in probs), probs)
                return
        self.skipTest("no experience shows fewer than 8 apartments today")

    def test_a_doorman_and_a_pool_for_every_building(self):
        d = page()
        h = next(x for x in d["neighborhoods"] if (x.get("counts") or {}).get("shown") and (x.get("prose") or {}).get("scene")
                 and not (x.get("prose") or {}).get("inherited_from"))
        firsts = [u for u in d["units"] if u["hood_id"] == h["id"]]
        if all(P.R.desk_kind(u.get("amenities")) in ("doorman", "doorman24") for u in firsts):
            self.skipTest("every building there does have a doorman")
        h["prose"]["scene"] = "Every building here has a doorman."
        self.assertTrue(any("doorman" in f.problem or "SOURCE" in f.problem for f in fails(d, "neighborhood", h["id"])))


class PublishedData(unittest.TestCase):
    """The same three kinds, written straight into site/data.json (in a copy)."""

    @classmethod
    def setUpClass(cls):
        cls.d = page()
        cls.clean = fails(copy.deepcopy(cls.d))

    def planted(self, edit):
        d = copy.deepcopy(self.d)
        kind, oid = edit(d)
        before = {str(f) for f in self.clean}
        return [f for f in fails(d, kind, oid) if str(f) not in before]

    def unit(self, d):
        return next(u for u in d["units"] if (u.get("host") or {}).get("line"))

    def test_apartment_line(self):
        for text, word in ((CONCEIT, "intention"), (JARGON, "unit"), (FALSE_NUMBER, "NUMBER")):
            def edit(d, text=text):
                u = self.unit(d)
                u["host"]["line"] = text
                return "apartment", u["id"]
            got = self.planted(edit)
            self.assertTrue(any("SOURCE" in f.problem for f in got), text)
            self.assertTrue(any(word in f.problem for f in got), f"{text}: {[f.problem for f in got]}")

    def test_old_price_words_and_wrong_prices(self):
        """The page shows "Rent" and "Total with utilities and fees"; the text may not use the old vocabulary, leave a
        monthly price unnamed, or give a rent or a total that is not the page's."""
        def plant(text):
            def edit(d):
                u = next(x for x in d["units"] if P.R.rent_asked(x) and x.get("all_in"))
                price = "$" + format(P.R.round10(x_total(u)), ",")
                u["host"]["line"] = text.format(price=price, rent="$" + format(P.R.rent_asked(u) + 7, ","),
                                                off="$" + format(P.R.round10(x_total(u)) + 40, ","))
                return "apartment", u["id"]
            return [f.problem for f in self.planted(edit)]

        def x_total(u):
            return u["all_in"]
        for text, word in zip(OLD_PRICE_WORDS, ("everything included", "all-in", "all-in", "does not say which")):
            got = plant(text)
            self.assertTrue(any(word in p for p in got), f"{text}: {got}")
        got = plant("The rent is {rent}, about {price} a month with utilities and fees.")
        self.assertTrue(any("PRICE" in p and "rent" in p for p in got), got)
        got = plant("It costs about {off} a month with utilities and fees.")
        self.assertTrue(any("PRICE" in p and "total" in p for p in got), got)

    def test_building_text(self):
        for text, word in ((CONCEIT, "intention"), ("Verified by a live check on the scorecard.", "internal term"),
                           ("The building has a doorman, and garage parking costs $20 a month.", "CLAIM")):
            def edit(d, text=text):
                b = next(x for x in d["buildings"] if x.get("about_building")
                         and P.R.desk_kind(x.get("amenities")) not in ("doorman", "doorman24"))
                b["about_building"] = text
                return "building", b["id"]
            got = self.planted(edit)
            self.assertTrue(any("SOURCE" in f.problem for f in got), text)
            self.assertTrue(any(word in f.problem for f in got), f"{text}: {[f.problem for f in got]}")

    def test_neighborhood_lead(self):
        for text, word in ((CONCEIT, "intention"), (JARGON, "unit"), ("About 99 restaurants are within a 10-minute walk.", "99")):
            def edit(d, text=text):
                h = next(x for x in d["neighborhoods"] if (x.get("host") or {}).get("intro") and (x.get("counts") or {}).get("shown"))
                h["host"]["intro"] = text
                return "neighborhood", h["id"]
            got = self.planted(edit)
            self.assertTrue(any("SOURCE" in f.problem for f in got), text)
            self.assertTrue(any(word in f.problem for f in got), f"{text}: {[f.problem for f in got]}")

    def test_experience_tagline(self):
        for text, word in ((CONCEIT, "intention"), (JARGON, "unit")):
            def edit(d, text=text):
                y = d["years"][0]
                y["tagline"] = text
                return "experience", y["id"]
            got = self.planted(edit)
            self.assertTrue(any("SOURCE" in f.problem for f in got), text)
            self.assertTrue(any(word in f.problem for f in got), f"{text}: {[f.problem for f in got]}")

    def test_a_pool_that_the_building_does_not_have(self):
        def edit(d):
            b = next(x for x in d["buildings"] if x.get("about_building") and not (x.get("amenities") or {}).get("pool"))
            b["about_points"] = list(b.get("about_points") or []) + [{"icon": "pool", "text": "The building has a pool."}]
            return "building", b["id"]
        self.assertTrue(any("a pool" in f.problem for f in self.planted(edit)))

    def test_stale_wording_in_a_pipeline_string(self):
        d = copy.deepcopy(self.d)
        u = d["units"][0]
        u.setdefault("tour_questions", []).append("This listing was not checked again; is the unit still available?")
        got = [f for f in fails(d, owner="pipeline") if f.id == u["id"]]
        self.assertTrue(any("not checked again" in f.problem for f in got))


if __name__ == "__main__":
    unittest.main()
