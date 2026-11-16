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
import shutil
import sys
import tempfile
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


class RealtorTables(unittest.TestCase):
    """Independent check 5, "Guards": five edits planted directly in data/reference/realtor_lines.csv and
    building_about.csv all slipped through, because the audit compared the generator with the page only. Each is
    planted here in a COPY of the two tables (nothing on disk is changed) and must fail."""

    @classmethod
    def setUpClass(cls):
        cls.d = page()
        cls.tmp = Path(tempfile.mkdtemp(prefix="realtor_tables_"))
        cls.clean = {str(f) for f in P.audit(copy.deepcopy(cls.d))}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def planted(self, table, edit):
        """table: 'lines' | 'about'. edit(rows) changes the copy's rows in place and returns the id it touched."""
        src = {"lines": P.R.OUT, "about": P.R.OUT_BUILDINGS}
        paths = {}
        for name, path in src.items():
            paths[name] = self.tmp / Path(path).name      # the copies keep the tables' names
            shutil.copyfile(path, paths[name])
        with open(paths[table], newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        oid = edit(rows)
        with open(paths[table], "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        got = P.audit(copy.deepcopy(self.d), lines_csv=paths["lines"], about_csv=paths["about"])
        return [f for f in got if f.owner == "text" and str(f) not in self.clean and f.id == oid]

    def test_the_tables_on_disk_are_what_the_generator_writes(self):
        self.assertEqual([f for f in self.clean if "SOURCE" in f and ".csv" in f], [])

    def test_the_five_planted_edits(self):
        cases = [("lines", "host_line", CONCEIT),                                      # a conceit
                 ("lines", "host_catch", JARGON),                                      # jargon
                 ("lines", "host_line", FALSE_NUMBER),                                 # a wrong number
                 ("about", "about_building", "The building has a pool."),              # a false amenity (see below)
                 ("lines", "host_line", "The rent is $2,999, about $2,999 a month with utilities and fees.")]   # rent called the total
        for table, col, text in cases:
            def edit(rows, col=col, text=text):
                r = rows[0]
                r[col] = text
                return r.get("listing_id") or r.get("building_id")
            got = self.planted(table, edit)
            self.assertTrue(any("SOURCE" in f.problem and ".csv" in f.problem for f in got), f"{table}.{col}: {text}: slipped through")

    def test_an_edited_icon_point_a_missing_row_and_an_extra_row(self):
        def point(rows):
            r = rows[0]
            r["about_points_json"] = json.dumps(json.loads(r["about_points_json"]) + [{"icon": "pool", "text": "The building has a pool."}])
            return r["building_id"]
        self.assertTrue(any("building_about.csv" in f.problem for f in self.planted("about", point)))

        def missing(rows):
            return rows.pop(0)["listing_id"]
        self.assertTrue(any("no row" in f.problem for f in self.planted("lines", missing)))

        def extra(rows):
            rows.append({**rows[0], "listing_id": "planted:not-on-the-page"})
            return "planted:not-on-the-page"
        self.assertTrue(any("not on the page" in f.problem for f in self.planted("lines", extra)))

    def test_a_subhead_edited_in_the_table(self):
        def edit(rows):
            r = next(x for x in rows if x["sub_parking"])
            r["sub_parking"] = "Garage parking, with the monthly fee published and a valet."
            return r["listing_id"]
        self.assertTrue(any("realtor_lines.csv:sub_parking" in f.field for f in self.planted("lines", edit)))


def synthetic(parking=None, amenities=None, dog=None, kind=None):
    u = {"id": "x", "building_id": "b", "hood_id": "h", "parking": parking or {}, "amenities": amenities or {},
         "dog": dog or {"allowed": "yes"}, "moments": {"sat": {"train_station": "Journal Square", "train_station_kind": kind}}}
    return u


OPEN_LOT_GARAGE_EXTRA = {"type": "lot: Open parking: included in lease; Garage: $125 month", "fee": 0.0, "fee_basis": "published",
                         "kind": "open_lot", "included_kind": "open_lot", "fee_kind": "open_lot",
                         "optional_kinds": [{"kind": "garage", "fee": 125.0, "fee_basis": "published"}]}
OFFSITE_DECK = {"type": "offsite: no on-site parking: permit at a nearby deck $185/month", "fee": 185.0, "fee_basis": "published",
                "kind": "offsite", "fee_kind": "offsite", "offsite": True,
                "optional_kinds": [{"kind": "offsite", "fee": 100.0, "fee_basis": "published"}]}
ASSIGNED_INCLUDED = {"type": "assigned: one assigned space included per unit", "fee": 0.0, "fee_basis": "published",
                     "kind": "assigned", "included_kind": "assigned", "fee_kind": "assigned", "assigned": True}
UNNAMED = {"type": "parking", "fee": None, "kind": "unspecified"}


class StructuredClaims(unittest.TestCase):
    """Independent check 5: the claims audit against the structured fields (parking kind, station kind, washer and
    dryer wording, dog weight limit). The sentences are the ones the check quoted, and their repairs."""

    def test_parking_says_exactly_what_the_structured_fields_carry(self):
        lot, deck = synthetic(OPEN_LOT_GARAGE_EXTRA), synthetic(OFFSITE_DECK)
        for u, good in ((lot, "A free open lot; garage spaces are $125 a month."), (lot, "A free open lot; garage spaces cost extra."),
                        (lot, "The rent includes a space in the open lot; garage spaces are $125 a month."),
                        (deck, "Parking is in an off-site deck, $185 a month."),
                        (deck, "Parking is off-site, not at the building, and the fee is published."),
                        (synthetic(ASSIGNED_INCLUDED), "An assigned space is included; the listing does not say whether it is a garage or a lot."),
                        (synthetic(UNNAMED), "The listing mentions parking without saying what kind: ask."),
                        (synthetic({}), "The listing does not mention parking, so ask where you would park.")):
            self.assertEqual(P.parking_claims(good, u), [], good)
        for u, bad in ((lot, "Garage parking, no monthly charge."),                  # N1, the sentence the check quoted
                       (lot, "Garage parking costs $125 a month."),                  # the garage's fee on the space she parks in
                       (lot, "A space in the building's lot costs $125 a month."),   # a fee attached to the wrong kind
                       (lot, "A free open lot; garage spaces are $99 a month."),     # the extra's fee is $125
                       (lot, "A free open lot; covered spaces cost extra."),         # no covered space is offered
                       (lot, "The garage fee is not published, so ask what it costs each month."),
                       (deck, "Parking is in the building's lot, with the fee published."),   # the failing sentence of The George
                       (deck, "The building has a garage, and a space costs $185 a month."),
                       (deck, "Parking is in an off-site deck, $100 a month."),
                       (synthetic(ASSIGNED_INCLUDED), "A garage space is included in the rent."),
                       (synthetic(UNNAMED), "You would park in the building's lot, so ask what a space costs."),
                       (synthetic({}), "Parking is included in the rent."),
                       (synthetic({"type": "garage: fee not stated", "kind": "garage", "fee": None}), "Garage parking costs $150 a month."),
                       (synthetic({"type": "garage", "kind": "garage", "fee": 150.0, "fee_kind": "garage"}), "The garage fee is not published, so ask for it.")):
            self.assertNotEqual(P.parking_claims(bad, u), [], bad)

    def test_a_cost_sentence_that_names_the_parking_fee_is_not_a_parking_claim(self):
        u = synthetic(OPEN_LOT_GARAGE_EXTRA)
        self.assertEqual(P.parking_claims("Building fees and the parking fee are not published, so this price leaves them out.", u), [])

    def test_station_by_its_kind(self):
        self.assertEqual(P.station_claims("The Journal Square PATH station is 0.4 miles away.", synthetic(kind="PATH")), [])
        self.assertTrue(P.station_claims("The Journal Square train station is 0.4 miles away.", synthetic(kind="PATH")))
        self.assertTrue(P.station_claims("It is 0.2 miles to the Elmhurst Av train station.", synthetic(kind="subway")))
        self.assertTrue(P.station_claims("The Port Imperial subway station is 0.2 miles away.", synthetic(kind="light rail")))
        self.assertEqual(P.station_claims("The Kew Gardens train station is 0.3 miles away.", synthetic(kind="train")), [])

    def test_washer_and_dryer_wording(self):
        both = {"in_unit_laundry": "yes", "laundry": "In-unit washer and dryer", "in_unit_appliances": "washer and dryer",
                "in_unit_laundry_basis": "page_says_in_apartment"}
        tag = {**both, "in_unit_laundry_basis": "listing_site_appliance_list"}
        washer = {"in_unit_laundry": "yes", "laundry": "In-unit washer (no dryer named)", "in_unit_appliances": "washer",
                  "in_unit_laundry_basis": "listing_site_appliance_list"}
        ok = lambda am, t: self.assertEqual(P.laundry_claims(t, synthetic(amenities=am)), [], t)
        bad = lambda am, t: self.assertNotEqual(P.laundry_claims(t, synthetic(amenities=am)), [], t)
        ok(both, "Washer and dryer in the apartment.")
        ok(tag, "The listing shows a washer and dryer in the apartment.")
        bad(tag, "Washer and dryer in the apartment.")                        # N6: a tag is not a flat assertion
        bad(tag, "A washer and dryer are inside the apartment.")
        ok(washer, "The listing shows a washer in the apartment, with no dryer named.")
        bad(washer, "The listing shows a washer and dryer in the apartment.")  # Parkway Lofts, 121 Towne: a washer only
        bad(washer, "Washer and dryer in the apartment.")
        bad({"in_unit_laundry": "on_site_only", "laundry": "On-site laundry room"}, "Laundry is inside the apartment.")
        self.assertEqual(P.R.laundry_kind(washer), "washer")
        self.assertEqual(P.R.laundry_mode(tag), "listed_wd")

    def test_dog_weight_limit_only_where_a_page_states_it(self):
        small = synthetic(dog={"allowed": "yes", "weight_limit_lb": None, "size_note": "page says small dogs; no weight"})
        self.assertTrue(P.dog_weight_claims("Dogs are allowed up to 25 pounds.", [small]))      # N5, Brookview Commons East
        self.assertEqual(P.dog_weight_claims("Dogs are allowed up to 50 pounds.", [synthetic(dog={"allowed": "yes", "weight_limit_lb": "50"})]), [])
        self.assertTrue(P.dog_weight_claims("Dogs are allowed, with no weight limit.", [small]))

    def test_planted_on_the_page(self):
        """The same faults written into a copy of site/data.json, on the buildings the check named."""
        d = page()
        clean = {str(f) for f in P.audit(copy.deepcopy(d))}

        def plant(pick, text):
            c = copy.deepcopy(d)
            first = {}
            for u in c["units"]:
                first.setdefault(u["building_id"], u)
            b = next((x for x in c["buildings"] if x["id"] in first and pick(first[x["id"]])), None)
            if b is None:
                return None
            b["about_points"] = list(b.get("about_points") or []) + [{"icon": "parking", "text": text}]
            return [f.problem for f in P.audit(c) if str(f) not in clean and f.id == b["id"] and "CLAIM" in f.problem]
        cases = [(lambda u: P.R.parking_facts(u)["kind"] == "offsite", "Parking is in the building's lot, with the fee published."),
                 (lambda u: P.R.parking_facts(u)["kind"] == "lot" and P.R.parking_facts(u)["included"], "Garage parking, no monthly charge."),
                 (lambda u: R_kind(u) == "PATH", "The train station is 0.3 miles away, by the train station entrance."),
                 (lambda u: P.R.laundry_mode(u.get("amenities")) == "listed_washer", "Washer and dryer in the apartment."),
                 (lambda u: P.R.laundry_mode(u.get("amenities")) == "listed_wd", "A washer and dryer are inside the apartment."),
                 (lambda u: not (u.get("dog") or {}).get("weight_limit_lb"), "Dogs are allowed up to 25 pounds.")]
        for pick, text in cases:
            got = plant(pick, text)
            if got is None:
                continue                                  # no such building is shown today
            self.assertTrue(got, f"slipped through: {text}")


def R_kind(u):
    return P.R.get(u, "moments", "sat", "train_station_kind")


class NeighborhoodRules(unittest.TestCase):
    """Independent check 5, N15 to N17, N3, N9, D27: the rules added to check_scene_text.py, with the sentences the
    check quoted."""

    @classmethod
    def setUpClass(cls):
        P.use_page(page())
        with open(G.HOODS, newline="", encoding="utf-8") as f:
            cls.hoods = {r["hood_id"]: r for r in csv.DictReader(f)}

    def check(self, row, **change):
        texts = {c: row[c] or "" for c in G.COLUMNS["hood"]}
        texts.update(change)
        return G.check_row("hood", row["hood_id"], texts, json.loads(row["evidence_json"]))[0]

    def hood_where(self, test):
        b = G.table(G.DOOR_SOURCE)
        for hid, g in b.groupby("hood_id"):
            if hid in self.hoods and test(g):
                return self.hoods[hid]
        self.skipTest("no such neighborhood is shown today")

    def test_no_two_sentences_give_incompatible_amounts(self):
        none = self.hood_where(lambda g: G.half_up(g["bars_800m"].median()) == 0)       # Jamaica's case
        probs = self.check(none, watch_for="Few bars are within a 10-minute walk.")
        self.assertTrue(any("Few bars" in p for p in probs), probs)
        some = self.hood_where(lambda g: G.half_up(g["cafes_800m"].median()) >= 2)       # Westport's case
        probs = self.check(some, watch_for="Your parents are far away, and nothing here is within walking distance.")
        self.assertTrue(any("nothing here is within walking distance" in p for p in probs), probs)
        probs = self.check(some, watch_for="There are no cafés within a 10-minute walk.")
        self.assertTrue(any("no cafés" in p for p in probs), probs)
        self.assertEqual([c for _, c, _ in G.quantity_claims("No restaurants are within a 10-minute walk, and only 4 within 1 mile.")], ["none"])
        self.assertEqual([(f, c) for f, c, _ in G.quantity_claims("About 12 restaurants are within a 10-minute walk, and few bars.")],
                         [("bars_800m", "few"), ("restaurants_800m", "some")])

    def test_a_text_may_not_open_on_a_sentence_that_leans_on_another(self):
        row = self.hood_where(lambda g: len(g) >= 1)
        for bad in ("9 cafés are close too, and the supermarket is 0.1 miles away.",   # Ridgewood, as the check quoted it
                    "The supermarket is also close.", "And the supermarket is close.", "But the supermarket is far.",
                    "Groceries are close as well."):
            self.assertTrue(G.dangling(bad), bad)
            self.assertTrue(any("leans on" in p for p in self.check(row, scene=bad)), bad)
        for good in ("The nearest park is too far for a daily dog walk.", "A park is close. The supermarket is close too.",
                     "You can walk either to the park or to the water."):
            self.assertEqual(G.dangling(good), [], good)

    def test_n_of_the_m_agrees(self):
        self.assertTrue(G.agreement("1 of the 4 buildings here have their own dog area"))      # N17
        self.assertEqual(G.agreement("1 of the 4 buildings here has its own dog area"), [])
        self.assertEqual(G.agreement("2 of the 4 buildings here have their own dog area"), [])
        self.assertTrue(G.agreement("3 of the 5 buildings here has its own dog area"))
        self.assertTrue(G.agreement("1 of the 4 buildings shown here list a dog amenity"))
        for hid in self.hoods:
            for g in G.glance(hid):
                self.assertEqual(G.agreement(f"{g['text']} {g['label']}"), [], hid)

    def test_the_station_is_named_by_its_kind(self):
        path = self.hood_where(lambda g: set(g["train_station_kind"].dropna()) == {"PATH"})
        probs = self.check(path, scene="The train station is 0.4 miles away.")
        self.assertTrue(any("name it by its kind" in p for p in probs), probs)
        item = next(g for g in G.glance(path["hood_id"]) if g["key"] == "train_station")
        self.assertEqual(item["kind"], "PATH")
        self.assertTrue(item["label"].startswith("to PATH"), item["label"])
        self.assertRegex(item["text"], r"^\d+(\.\d)? miles$")
        subway = self.hood_where(lambda g: set(g["train_station_kind"].dropna()) == {"subway"})
        self.assertTrue(any("name it by its kind" in p for p in self.check(subway, good_for_her="The train is close.")))

    def test_a_toll_that_differs_by_building_is_a_range(self):
        t = G.table(G.PAGE + "#neighborhoods")
        wide = t[(t["toll_spread"] > G.TOLL_SPREAD) & t["hood_id"].isin(self.hoods)]
        if not len(wide):
            self.skipTest("no neighborhood's tolls differ by more than $5 today")
        r = wide.iloc[0]
        row = self.hoods[r["hood_id"]]
        one = f"Each visit costs about ${G.transform(r['toll_round_trip'], 'int')} round trip with a New York E-ZPass."
        self.assertTrue(any("say the range" in p for p in self.check(row, watch_for=one)), one)        # N9, Newark
        self.assertEqual(G.check_toll_range(r["hood_id"], [("watch_for", f"Each visit costs about ${G.transform(r['toll_lo'], 'int')} to "
                                                            f"${G.transform(r['toll_hi'], 'int')} round trip with a New York E-ZPass.")]), [])

    def test_safest_is_an_icon_point_for_the_lowest_tenth_only(self):
        t = G.table(G.PAGE + "#neighborhoods")
        said = [h for h, r in self.hoods.items() if "safest" in r["about_points_json"].lower()]
        shown = [h for h in self.hoods if h in set(t["hood_id"])]
        self.assertLessEqual(len(said), max(1, len(shown) // 10))                       # at most the lowest tenth
        for h in said:
            self.assertLessEqual(float(t[t["hood_id"] == h]["violent_pctile"].iloc[0]), G.SAFEST_MAX, h)
        for h, r in self.hoods.items():                                                # never tacked on to a paragraph
            self.assertNotIn("safest", " ".join(r[c] for c in ("scene", "host_intro", "good_for_her", "watch_for")).lower(), h)
        row = self.hoods[said[0]] if said else self.hood_where(lambda g: len(g) >= 1)
        old = "This is also one of the safest spots on the whole list."
        self.assertTrue(any("safe" in p for p in self.check(row, scene=row["scene"] + " " + old)))
        other = next(self.hoods[h] for h in shown if h not in said and float(t[t["hood_id"] == h]["safety_published"].iloc[0]))
        pts = json.dumps(json.loads(other["about_points_json"])[:4] + [{"icon": "heart", "text": G.SAFEST + "."}]
                         + [p for p in json.loads(other["about_points_json"]) if p["icon"] == "warning"][:1])
        self.assertTrue(any("lowest tenth" in p for p in self.check(other, about_points_json=pts)))
        unpublished = [h for h in shown if not float(t[t["hood_id"] == h]["safety_published"].iloc[0])]
        for h in unpublished:
            r = self.hoods[h]
            pts = json.dumps(json.loads(r["about_points_json"])[:4] + [{"icon": "heart", "text": G.SAFEST + "."}])
            self.assertTrue(any("no crime rate is published" in p for p in self.check(r, about_points_json=pts)), h)


if __name__ == "__main__":
    unittest.main()
