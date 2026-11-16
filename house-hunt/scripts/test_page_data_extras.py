#!/usr/bin/env python3
"""Tests for scripts/page_data_extras.py and scripts/build_artifact.py.

Run from the house-hunt folder:  python3 scripts/test_page_data_extras.py     (or: python3 -m unittest scripts/test_page_data_extras.py)

Every block is exercised on a small made-up page in a temp folder: it attaches what it should, it is skipped (and
leaves the page alone) when its input is absent or half-written, a second run changes nothing, and a row that leaves a
CSV leaves the page. Then the rules that have gone wrong before: the Jersey City parent fallback, broker numbers never
shown, the own-site number preferred, the order descriptions are chosen in, ratings filtering, the quote screen (it
keeps "diverse", drops a quote naming a group), the neighborhood ranking by building (penalty, tie-break), the photos
link preference, the New York City rule copy, the shape check. One integration test runs the real script twice on a
copy of the current site/data.json against the real data folder and asserts that the second run changes nothing and
that no NaN or "nan"-like value is anywhere in the output.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_artifact as A  # noqa: E402
import page_data_extras as X  # noqa: E402

REAL_ROOT = HERE.parent


def unit(uid, hood, building, rank, **more):
    u = {"id": uid, "building_id": building, "hood_id": hood, "scores": {"rank": rank},
         "links": {"listing": f"https://www.trulia.com/listing/{uid}", "building": f"https://www.trulia.com/building/{building}"}}
    u.update(more)
    return u


def hood(hid, year="quiet", state="NJ", area="Union County", **more):
    h = {"id": hid, "name": hid.split(":")[1].title(), "state": state, "area": area, "year": year, "lat": 40.0, "lon": -74.0,
         "unit_ids": [], "local": {"parking_rules": None, "dog_rules": None, "voices": [], "survey": []}}
    h.update(more)
    return h


def page():
    """Two experiences. 'quiet': Garwood (three buildings), Cranford (one building, two units), Westfield (no row in
    any CSV). 'city': two children of the split city Jersey City, and two New York City neighborhoods."""
    hoods = [
        hood("nj:garwood"), hood("nj:cranford"), hood("nj:westfield"),
        hood("nj:jersey-city-downtown", "city", area="Hudson County", parent_id="nj:jersey-city", parent_name="Jersey City", short_name="Downtown"),
        hood("nj:jersey-city-the-heights", "city", area="Hudson County", parent_id="nj:jersey-city", parent_name="Jersey City", short_name="The Heights"),
        hood("ny:sunnyside", "city", "NY", "Queens"), hood("ny:bay-ridge", "city", "NY", "Brooklyn"), hood("ny:jamaica", "city", "NY", "Queens"),
    ]
    units = [
        unit("g1", "nj:garwood", "bA", 60.0), unit("g2", "nj:garwood", "bB", 54.0), unit("g3", "nj:garwood", "bC", 48.0),
        unit("c1", "nj:cranford", "bD", 70.0), unit("c2", "nj:cranford", "bD", 68.0),
        unit("w1", "nj:westfield", "bE", 50.0),
        unit("d1", "nj:jersey-city-downtown", "bF", 55.0), unit("h1", "nj:jersey-city-the-heights", "bG", 52.0),
        unit("s1", "ny:sunnyside", "bH", 51.0), unit("r1", "ny:bay-ridge", "bI", 49.0), unit("j1", "ny:jamaica", "bJ", 47.0),
    ]
    by = {h["id"]: h for h in hoods}
    for u in units:
        by[u["hood_id"]]["unit_ids"].append(u["id"])
    buildings = []
    for u in units:
        if not any(b["id"] == u["building_id"] for b in buildings):
            buildings.append({"id": u["building_id"], "hood_id": u["hood_id"], "best_unit_id": u["id"], "best_rank_score": u["scores"]["rank"],
                              "links": {"building": u["links"]["building"]}})
    nyc_rule = lambda rule: {"rule": rule, "summary": f"{rule} in the city", "quote": "q", "url": f"https://nyc.gov/{rule}", "municipality": "New York City", "about": None}
    for hid in ("ny:sunnyside", "ny:jamaica"):
        by[hid]["local"]["parking_rules"] = [nyc_rule("alternate_side"), nyc_rule("hydrant")]
        by[hid]["local"]["dog_rules"] = [nyc_rule("leash_law")]
    by["ny:jamaica"]["local"]["parking_rules"].append({**nyc_rule("municipal_garage"), "summary": "A garage by Jamaica station"})
    by["nj:garwood"]["local"]["voices"] = [{"excerpt": "Quiet and friendly.", "theme": "feel", "sentiment": "positive", "context": None, "source": "niche.com",
                                            "date": "2025-01-01", "url": "https://niche.com/g/1", "source_area": None, "about": None}]
    by["nj:garwood"]["local"]["survey"] = [{"measure": "niche_overall_rating", "value": "3.9", "source": "niche.com", "as_of": "2026-11-15",
                                            "url": "https://niche.com/g", "source_area": "Garwood, NJ", "about": None}]
    years = [{"id": "quiet", "label": "The Quiet-Street Year", "subhead": "Builder subhead.", "medians": {"all_in": 2900.0}, "ranges": {"all_in": [2600.0, 2990.0]},
              "drive_min_range_hoods": {"nearest": {"hood_id": "nj:garwood"}}, "hood_ids": ["nj:westfield", "nj:garwood", "nj:cranford"]},
             {"id": "city", "label": "The Little-City Year", "subhead": "City subhead.", "medians": {"all_in": 2800.0}, "ranges": {"all_in": [2500.0, 2950.0]},
              "hood_ids": ["ny:jamaica", "nj:jersey-city-downtown", "nj:jersey-city-the-heights", "ny:sunnyside", "ny:bay-ridge"]}]
    return {"meta": {"built_at": "2026-11-16T00:00:00+00:00"}, "years": years, "neighborhoods": hoods, "buildings": buildings, "units": units,
            "avoid": [], "held": []}


class Sandbox(unittest.TestCase):
    """A temp house-hunt folder with site/data.json; CSVs are written per test."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="extras_test_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.P = X.Paths(self.root)
        self.P.data_json.parent.mkdir(parents=True)
        self.save(page())
        self.out = []

    def save(self, d):
        self.P.data_json.write_text(json.dumps(d), encoding="utf-8")

    def csv(self, path, rows, cols=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        cols = cols or list(dict.fromkeys(k for r in rows for k in r))
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)

    def run_script(self, **kw):
        self.out = []
        code = X.run(self.root, wait=0, out=self.out.append, **kw)
        return code, json.loads(self.P.data_json.read_text(encoding="utf-8"))

    def data(self, **kw):
        return self.run_script(**kw)[1]

    def assertSecondRunChangesNothing(self):
        self.run_script()
        first = self.P.data_json.read_bytes()
        stamp = self.P.data_json.stat().st_mtime_ns
        self.run_script()
        self.assertEqual(first, self.P.data_json.read_bytes())
        self.assertEqual(stamp, self.P.data_json.stat().st_mtime_ns, "an unchanged file must not be rewritten")
        self.assertIn("unchanged", self.out[0])

    @staticmethod
    def H(d, hid):
        return next(h for h in d["neighborhoods"] if h["id"] == hid)

    @staticmethod
    def U(d, uid):
        return next(u for u in d["units"] if u["id"] == uid)

    @staticmethod
    def B(d, bid):
        return next(b for b in d["buildings"] if b["id"] == bid)

    @staticmethod
    def Y(d, yid):
        return next(y for y in d["years"] if y["id"] == yid)


# ----------------------------------------------------------------------------------------------------------------------
class Helpers(Sandbox):
    def test_read_csv_absent_extra_and_missing_columns(self):
        p = self.root / "t.csv"
        self.assertEqual(X.read_csv(p, wait=0), (None, "missing"))
        self.csv(p, [{"a": "1", "b": " nan ", "extra": "x"}, {"a": "", "b": "None", "extra": ""}])
        rows, why = X.read_csv(p, need=("a",), wait=0)
        self.assertIsNone(why)
        self.assertEqual([r["b"] for r in rows], ["", ""], '"nan" and "None" cells read as empty')
        self.assertEqual(rows[0]["not_a_column"], "", "a column the file lacks reads as empty")
        self.assertIn("extra", rows.columns)
        rows, why = X.read_csv(p, need=("a", "zzz"), wait=0)
        self.assertIsNone(rows)
        self.assertIn("zzz", why)

    def test_read_csv_half_written(self):
        p = self.root / "t.csv"
        p.write_text('a,b\n1,"an open quote that never clo', encoding="utf-8")
        rows, why = X.read_csv(p, wait=0)
        self.assertIsNone(rows)
        self.assertIn("half-written", why)
        p.write_text("", encoding="utf-8")
        self.assertIsNone(X.read_csv(p, wait=0)[0])
        p.write_text("a,b\n1,2\n3,4", encoding="utf-8")          # no final line break, but whole and stable: a hand-made file
        rows, why = X.read_csv(p, wait=0)
        self.assertEqual(len(rows), 2)
        p.write_text("a,b,c\n1,2,3\n4,5", encoding="utf-8")       # the writer stopped in the middle of a row
        rows, why = X.read_csv(p, wait=0)
        self.assertIsNone(rows)
        self.assertIn("cut short", why)

    def test_json_safe_and_cells(self):
        safe, n = X.json_safe({"a": float("nan"), "b": ["nan", "None", float("inf"), "fine", 1, None, True], "c": "N/A"})
        self.assertEqual(safe, {"a": None, "b": [None, None, None, "fine", 1, None, True], "c": "N/A"})
        self.assertEqual(n, 4)
        self.assertIsNone(X.json_cell("NaN"))
        self.assertIsNone(X.json_cell("{broken"))
        self.assertIsNone(X.json_cell('{"a": 1}'), "a list is wanted")
        self.assertEqual(X.json_cell('[{"icon": "dog", "text": "t"}]'), [{"icon": "dog", "text": "t"}])
        self.assertEqual((X.whole_number("12.0"), X.whole_number("1,234"), X.whole_number("12.5"), X.whole_number("-3"), X.whole_number("x")), (12, 1234, None, None, None))

    def test_nan_in_page_data_becomes_null_and_no_input_at_all_is_fine(self):
        d = page()
        d["units"][0]["sqft"] = float("nan")
        d["units"][1]["floor"] = "nan"
        self.P.data_json.write_text(json.dumps(d), encoding="utf-8")       # json.dumps writes a bare NaN: not valid JSON for the page
        code, d = self.run_script()
        self.assertEqual(code, 0)
        self.assertIsNone(d["units"][0]["sqft"])
        self.assertIsNone(d["units"][1]["floor"])
        self.assertNotIn("NaN", self.P.data_json.read_text())
        self.assertTrue(any("skipped" in v for v in d["meta"]["extras"].values()))
        self.assertSecondRunChangesNothing()

    def test_page_data_missing_or_broken(self):
        self.P.data_json.write_text('{"meta": {}, "years": [', encoding="utf-8")
        self.assertEqual(X.run(self.root, wait=0, out=self.out.append), 2)
        self.assertIn("half-written", self.out[0])
        self.P.data_json.unlink()
        self.assertEqual(X.run(self.root, wait=0, out=self.out.append), 2)

    def test_dry_run_writes_nothing(self):
        before = self.P.data_json.read_bytes()
        self.run_script(dry_run=True)
        self.assertEqual(before, self.P.data_json.read_bytes())

    def test_builder_figures_are_not_touched(self):
        before = page()
        d = self.data()
        for y0, y1 in zip(before["years"], d["years"]):
            for k in ("medians", "ranges", "drive_min_range_hoods", "label", "id"):
                self.assertEqual(y0.get(k), y1.get(k), k)


# ----------------------------------------------------------------------------------------------------------------------
class SceneText(Sandbox):
    def years_csv(self, **more):
        row = {"year_label": "The Quiet-Street Year", "display_label": "The Quiet-Street Experience", "tagline": "Lawns and quiet.", "subhead": "CSV subhead.",
               "scene": "You work at home.", "promise": "Quiet streets.", "catch": "Everything is a drive.", "host_intro": "An apartment among houses.",
               "host_walkthrough": "Weekdays are calm.\n\nSaturday is a drive.", "sub_cost": "Near the top of your budget.", "sub_green": "nan",
               "about_points_json": '[{"icon": "ruler", "text": "About 710 square feet."}]', "day_moments_json": "NaN", "evidence_json": "{}"}
        row.update(more)
        self.csv(self.P.scene_years, [row])

    def test_experience_text_attaches(self):
        self.years_csv()
        d = self.data()
        y = self.Y(d, "quiet")
        self.assertEqual(y["prose"], {"scene": "You work at home.", "promise": "Quiet streets.", "catch": "Everything is a drive."})
        self.assertEqual(y["host"], {"intro": "An apartment among houses.", "walkthrough": ["Weekdays are calm.", "Saturday is a drive."]})
        self.assertEqual(y["about_points"], [{"icon": "ruler", "text": "About 710 square feet."}])
        self.assertNotIn("day_moments", y, "a NaN cell attaches nothing")
        self.assertEqual((y["subhead"], y["subhead_original"]), ("CSV subhead.", "Builder subhead."))
        self.assertEqual(y["headlines"], {"cost": {"subhead": "Near the top of your budget."}}, 'a "nan" subhead is not a subhead')
        self.assertEqual(y["tagline"], "Lawns and quiet.")
        other = self.Y(d, "city")
        self.assertNotIn("prose", other)
        self.assertEqual(other["display_label"], "The Little-City Experience", "default label: Year becomes Experience")
        self.assertSecondRunChangesNothing()
        self.assertEqual(self.Y(self.data(), "quiet")["subhead_original"], "Builder subhead.", "the builder's subhead survives reruns")

    def test_display_label_from_the_csv_is_kept(self):
        self.years_csv(display_label="The Lawn Experience")
        self.assertEqual(self.Y(self.data(), "quiet")["display_label"], "The Lawn Experience", "the ranking block used to overwrite this")

    def test_join_on_display_label_or_id(self):
        self.years_csv(year_label="The Quiet-Street Experience")
        self.assertIn("prose", self.Y(self.data(), "quiet"))
        self.years_csv(year_label="quiet")
        self.assertIn("prose", self.Y(self.data(), "quiet"))

    def test_skipped_when_absent_and_cleared_when_the_row_goes(self):
        d = self.data()
        self.assertIn("skipped", d["meta"]["extras"]["experience_text"])
        self.assertEqual(self.Y(d, "quiet")["display_label"], "The Quiet-Street Experience")
        self.years_csv()
        self.data()
        self.P.scene_years.unlink()
        self.assertIn("prose", self.Y(self.data(), "quiet"), "an absent input leaves what is on the page")
        self.years_csv(scene="")
        y = self.Y(self.data(), "quiet")
        self.assertNotIn("prose", y, "a row that lost its text leaves the page")
        self.assertNotIn("subhead_original", y)
        self.assertEqual(y["subhead"], "Builder subhead.")

    def hoods_csv(self, rows):
        base = {"hood_name": "", "year_label": "", "scene": "", "good_for_her": "", "watch_for": "", "host_intro": "", "sub_dog": "", "about_points_json": ""}
        self.csv(self.P.scene_hoods, [{**base, **r} for r in rows])

    def test_neighborhood_text_and_the_split_city(self):
        self.hoods_csv([
            {"hood_id": "nj:jersey-city", "scene": "The city as a whole.", "good_for_her": "Trains.", "watch_for": "Parking.", "host_intro": "City intro.", "sub_dog": "City dogs."},
            {"hood_id": "nj:garwood", "scene": "Garwood scene.", "good_for_her": "Quiet.", "watch_for": "Few shops.", "host_intro": "Garwood intro.", "sub_dog": "A park nearby.",
             "about_points_json": '[{"icon": "dog", "text": "A park."}]'},
            {"hood_id": "nj:jersey-city-downtown", "scene": "Downtown scene.", "good_for_her": "Walkable.", "watch_for": "Noise.", "host_intro": "Downtown intro."},
            {"hood_id": "nj:jersey-city-the-heights", "scene": ""},                     # a row with no text is not "its own text"
            {"hood_id": "nj:not-on-page", "scene": "Nowhere."},
        ])
        d = self.data()
        g = self.H(d, "nj:garwood")
        self.assertEqual(g["prose"], {"scene": "Garwood scene.", "good_for_her": "Quiet.", "watch_for": "Few shops."})
        self.assertEqual((g["host"], g["headlines"], g["about_points"]), ({"intro": "Garwood intro."}, {"dog": {"subhead": "A park nearby."}}, [{"icon": "dog", "text": "A park."}]))
        down = self.H(d, "nj:jersey-city-downtown")
        self.assertEqual(down["prose"]["scene"], "Downtown scene.", "its own row wins although the city's row comes first")
        self.assertNotIn("about", down["prose"])
        heights = self.H(d, "nj:jersey-city-the-heights")
        self.assertEqual(heights["prose"], {"scene": "The city as a whole.", "good_for_her": "Trains.", "watch_for": "Parking.",
                                            "about": "Jersey City as a whole", "inherited_from": "nj:jersey-city"})
        self.assertNotIn("host", heights, "the city's host text and subheads are not handed down")
        self.assertNotIn("headlines", heights)
        self.assertNotIn("prose", self.H(d, "nj:westfield"))
        self.assertSecondRunChangesNothing()

    def test_row_for_the_current_experience_wins(self):
        self.hoods_csv([{"hood_id": "nj:garwood", "year_label": "The Quiet-Street Year", "scene": "Right text."},
                        {"hood_id": "nj:garwood", "year_label": "The Little-City Year", "scene": "Text from an old grouping."}])
        self.assertEqual(self.H(self.data(), "nj:garwood")["prose"]["scene"], "Right text.")


# ----------------------------------------------------------------------------------------------------------------------
class VoicesSurveyRules(Sandbox):
    def quotes(self, rows):
        base = {"neighborhood": "", "theme": "feel", "sentiment": "positive", "speaker_context": "", "source_site": "niche.com", "post_date": "2025-05-01",
                "permalink": "https://niche.com/q", "source_area": "", "verified": "yes"}
        self.csv(self.P.quotes2, [{**base, **r} for r in rows])

    def test_quotes_attach_route_and_screen(self):
        self.quotes([
            {"hood_id": "nj:garwood", "neighborhood": "Garwood", "excerpt": "A very diverse town, which I love.", "source_area": "Garwood, NJ"},
            {"hood_id": "nj:garwood", "neighborhood": "Garwood", "excerpt": "Great Chinese food on the main street."},
            {"hood_id": "nj:garwood", "neighborhood": "Garwood", "excerpt": "Lots of hispanics live around here."},
            {"hood_id": "nj:garwood", "neighborhood": "Garwood", "excerpt": "Quiet and  friendly!"},                        # already shown (round 1)
            {"hood_id": "nj:garwood", "neighborhood": "Garwood", "excerpt": "Not checked.", "verified": "no"},
            {"hood_id": "nj:garwood", "neighborhood": "Garwood", "excerpt": "No link.", "permalink": ""},
            {"hood_id": "nj:garwood", "neighborhood": "Garwood", "excerpt": "Decided against: wrong town."},
            {"hood_id": "nj:cranford", "neighborhood": "Cranford", "excerpt": "The county parks are great.", "source_area": "Union County (enclosing area)"},
            {"hood_id": "nj:jersey-city", "neighborhood": "Jersey City", "excerpt": "The whole city is changing fast.", "source_area": "Jersey City, NJ"},
            {"hood_id": "nj:jersey-city", "neighborhood": "Jersey City", "excerpt": "Downtown has every restaurant.", "source_area": "Downtown Jersey City"},
            {"hood_id": "nj:jersey-city", "neighborhood": "Jersey City", "excerpt": "The Heights has the best views.", "source_area": "Jersey City Heights"},
            {"hood_id": "nj:jersey-city", "neighborhood": "Jersey City", "excerpt": "Greenville is far from the PATH.", "source_area": "Greenville, Jersey City"},
            {"hood_id": "nj:elsewhere", "neighborhood": "Elsewhere", "excerpt": "Not on the page."},
        ])
        self.csv(self.P.quote_exclusions, [{"hood_id": "nj:garwood", "excerpt_starts_with": "Decided against", "reason": "wrong town", "decided": "2026-11-16"}])
        d = self.data()
        g = [v["excerpt"] for v in self.H(d, "nj:garwood")["local"]["voices"]]
        self.assertEqual(g, ["Quiet and friendly.", "A very diverse town, which I love.", "Great Chinese food on the main street."])
        v = self.H(d, "nj:garwood")["local"]["voices"][1]
        self.assertEqual((v["round"], v["about"], v["url"], v["context"]), (2, None, "https://niche.com/q", None))
        self.assertEqual(self.H(d, "nj:cranford")["local"]["voices"][0]["about"], "Union County", "a wider source area is named")
        down = {v["excerpt"]: v["about"] for v in self.H(d, "nj:jersey-city-downtown")["local"]["voices"]}
        heights = {v["excerpt"]: v["about"] for v in self.H(d, "nj:jersey-city-the-heights")["local"]["voices"]}
        self.assertEqual(down, {"The whole city is changing fast.": "Jersey City as a whole", "Downtown has every restaurant.": None})
        self.assertEqual(heights, {"The whole city is changing fast.": "Jersey City as a whole", "The Heights has the best views.": None},
                         "a quote about a part of the city with no page (Greenville) goes nowhere, not everywhere")
        self.assertIn("for places not on the page", d["meta"]["extras"]["round2_quotes"])
        self.assertSecondRunChangesNothing()

    def test_quotes_skipped_when_absent_or_half_written_and_removed_with_the_row(self):
        self.assertIn("skipped", self.data()["meta"]["extras"]["round2_quotes"])
        self.quotes([{"hood_id": "nj:garwood", "excerpt": "First."}, {"hood_id": "nj:garwood", "excerpt": "Second."}])
        self.assertEqual(len(self.H(self.data(), "nj:garwood")["local"]["voices"]), 3)
        good = self.P.quotes2.read_text()
        self.P.quotes2.write_text(good[:-12] + '"cut off in the mid', encoding="utf-8")
        d = self.data()
        self.assertIn("half-written", d["meta"]["extras"]["round2_quotes"])
        self.assertEqual(len(self.H(d, "nj:garwood")["local"]["voices"]), 3, "a half-written input leaves the page alone")
        self.quotes([{"hood_id": "nj:garwood", "excerpt": "Second."}])
        self.assertEqual([v["excerpt"] for v in self.H(self.data(), "nj:garwood")["local"]["voices"]], ["Quiet and friendly.", "Second."],
                         "a quote that left the CSV leaves the page; round 1 stays")

    def test_quote_screen_keeps_diverse_and_drops_named_groups(self):
        for keep in ("It is a diverse neighborhood and that is why we moved here.", "So much diversity, every culture is welcome.",
                     "Amazing Italian restaurants and a Chinese bakery.", "Quiet streets, good schools."):
            self.assertFalse(X.names_a_group(keep), keep)
        for drop in ("Lots of hispanics", "It is a mostly Jewish community.", "The area is predominantly Asian now."):
            self.assertTrue(X.names_a_group(drop), drop)
        d = page()
        self.H(d, "nj:garwood")["local"]["voices"] += [{"excerpt": "Lots of hispanics", "url": "u"}, {"excerpt": "Very diverse and friendly.", "url": "u"}]
        self.save(d)
        got = [v["excerpt"] for v in self.H(self.data(), "nj:garwood")["local"]["voices"]]
        self.assertEqual(got, ["Quiet and friendly.", "Very diverse and friendly."], "the screen also covers quotes the builder put on the page")
        self.assertSecondRunChangesNothing()

    def test_survey(self):
        self.csv(self.P.survey2, [
            {"hood_id": "nj:garwood", "source_site": "niche.com", "measure": "niche_overall_rating", "value": "3.9", "as_of": "2026-11-15", "source_url": "https://niche.com/g",
             "source_area": "Garwood, NJ - Niche"},                                     # the same figure as round 1, filed under another area name
            {"hood_id": "nj:garwood", "source_site": "trulia.com", "measure": "trulia_quiet_pct", "value": "81", "as_of": "early 2026", "source_url": "https://trulia.com/g", "source_area": "Garwood"},
            {"hood_id": "nj:jersey-city", "source_site": "niche.com", "measure": "niche_overall_rating", "value": "3.7", "as_of": "2026-11-15", "source_url": "https://niche.com/jc", "source_area": "Jersey City, NJ"},
            {"hood_id": "nj:jersey-city", "source_site": "trulia.com", "measure": "trulia_quiet_pct", "value": "40", "as_of": "early 2026", "source_url": "https://trulia.com/d", "source_area": "Downtown, Jersey City"},
            {"hood_id": "nj:garwood", "source_site": "niche.com", "measure": "empty", "value": "nan", "as_of": "", "source_url": ""},
        ])
        d = self.data()
        g = self.H(d, "nj:garwood")["local"]["survey"]
        self.assertEqual([(s["measure"], s["value"], s.get("round")) for s in g], [("niche_overall_rating", "3.9", None), ("trulia_quiet_pct", "81", 2)])
        self.assertEqual([(s["value"], s["about"]) for s in self.H(d, "nj:jersey-city-downtown")["local"]["survey"]], [("3.7", "Jersey City as a whole"), ("40", None)])
        self.assertEqual([s["value"] for s in self.H(d, "nj:jersey-city-the-heights")["local"]["survey"]], ["3.7"])
        self.assertSecondRunChangesNothing()
        self.P.survey2.unlink()
        self.assertEqual(len(self.H(self.data(), "nj:garwood")["local"]["survey"]), 2, "absent input: the page is left alone")

    def rules(self, rows):
        base = {"state": "NJ", "quote": "the law", "source_url": "https://ecode360.com/x", "source_type": "code", "retrieved_at": "2026-11-16T00:00:00Z", "value_type": "found"}
        self.csv(self.P.rules2, [{**base, **r} for r in rows])

    def test_rules(self):
        self.rules([
            {"municipality": "Garwood", "applies_to_hood_ids": "nj:garwood; nj:not-on-page", "topic": "street_parking", "rule": "overnight_parking", "summary": "No parking 2-6 AM."},
            {"municipality": "Garwood", "applies_to_hood_ids": "nj:garwood", "topic": "dogs", "rule": "leash_law", "summary": "Dogs on a leash."},
            {"municipality": "Garwood", "applies_to_hood_ids": "nj:garwood", "topic": "dogs", "rule": "dog_limit", "summary": "", "quote": "", "value_type": "not_found"},
            {"municipality": "Garwood", "applies_to_hood_ids": "nj:garwood", "topic": "noise", "rule": "quiet_hours", "summary": "Not a topic the page shows."},
            {"municipality": "Garwood", "applies_to_hood_ids": "nj:garwood", "topic": "dogs", "rule": "waste", "summary": "No link.", "source_url": ""},
            {"municipality": "Jersey City", "applies_to_hood_ids": "nj:jersey-city", "topic": "street_parking", "rule": "resident_permit", "summary": "Zone permits."},
        ])
        d = self.data()
        g = self.H(d, "nj:garwood")["local"]
        self.assertEqual([(r["rule"], r["round"], r["about"]) for r in g["parking_rules"]], [("overnight_parking", 2, None)])
        self.assertEqual([r["rule"] for r in g["dog_rules"]], ["leash_law"])
        for child in ("nj:jersey-city-downtown", "nj:jersey-city-the-heights"):
            self.assertEqual([(r["rule"], r["about"]) for r in self.H(d, child)["local"]["parking_rules"]], [("resident_permit", "Jersey City as a whole")])
        self.assertIsNone(self.H(d, "nj:westfield")["local"]["parking_rules"])
        self.assertSecondRunChangesNothing()
        self.rules([{"municipality": "Garwood", "applies_to_hood_ids": "nj:garwood", "topic": "dogs", "rule": "leash_law", "summary": "Dogs on a leash."}])
        g = self.H(self.data(), "nj:garwood")["local"]
        self.assertIsNone(g["parking_rules"], "the rule that left the CSV leaves the page, and an emptied list reads as none")
        self.csv(self.P.rules2, [{"municipality": "Garwood", "topic": "dogs"}])
        self.assertIn("no column", self.data()["meta"]["extras"]["round2_rules"])

    def test_nyc_rules_reach_every_borough_and_only_citywide_ones(self):
        d = self.data()
        bay = self.H(d, "ny:bay-ridge")["local"]
        self.assertEqual([(r["rule"], r.get("copied")) for r in bay["parking_rules"]], [("alternate_side", True), ("hydrant", True)],
                         "Brooklyn is New York City; the garage by Jamaica station is not a citywide rule")
        self.assertEqual([r["rule"] for r in bay["dog_rules"]], ["leash_law"])
        self.assertEqual(len(self.H(d, "ny:jamaica")["local"]["parking_rules"]), 3, "a neighborhood with city rules of its own is left as it is")
        self.assertIsNone(self.H(d, "nj:garwood")["local"]["parking_rules"])
        self.assertTrue(all(X.is_nyc({"state": "NY", "area": a}) for a in ("Brooklyn", "Queens", "Manhattan", "Bronx", "Staten Island", "Kings County", "New York County", "Richmond County")))
        self.assertFalse(any(X.is_nyc({"state": s, "area": a}) for s, a in (("NY", "Westchester County"), ("NJ", "Queens"), ("NY", "Nassau County"), ("NY", None))))
        self.assertSecondRunChangesNothing()
        self.assertEqual(len(self.H(self.data(), "ny:bay-ridge")["local"]["parking_rules"]), 2, "copies are not copied again")


# ----------------------------------------------------------------------------------------------------------------------
class PerBuilding(Sandbox):
    def contact_files(self, own=True):
        self.csv(self.P.contacts, [
            {"building_id": "bA", "leasing_phone": "(908) 555-0101", "leasing_phone_source_url": "https://trulia.com/a", "leasing_url": "https://www.trulia.com/building/bA",
             "office_hours": "Mon-Fri 9-5", "contact_kind": "leasing office", "note": "listing-site number"},
            {"building_id": "bB", "leasing_phone": "(908) 555-0202", "leasing_phone_source_url": "https://trulia.com/b", "leasing_url": "https://www.trulia.com/listing/g2",
             "office_hours": "", "contact_kind": "broker", "note": "brokerage number"},
            {"building_id": "bC", "leasing_phone": "(908) 555-0303", "leasing_phone_source_url": "", "leasing_url": "", "office_hours": "", "contact_kind": "individual owner", "note": ""},
            {"building_id": "bD", "leasing_phone": "nan", "leasing_phone_source_url": "", "leasing_url": "https://cranfordliving.example/", "office_hours": "nan",
             "contact_kind": "management company", "note": ""},
            {"building_id": "bF", "leasing_phone": "", "leasing_phone_source_url": "", "leasing_url": "", "office_hours": "", "contact_kind": "leasing office", "note": ""},
            {"building_id": "bH", "leasing_phone": "call us", "leasing_phone_source_url": "https://x.example", "leasing_url": "https://www.zumper.com/h", "office_hours": "",
             "contact_kind": "leasing office", "note": ""},
        ])
        if own:
            self.csv(self.P.contacts_own, [
                {"building_id": "bA", "own_site_url": "https://thegarwood.example/", "leasing_phone": "(908) 555-9999", "phone_page_url": "https://thegarwood.example/contact",
                 "office_hours": "", "confidence": "high"},
                {"building_id": "bB", "own_site_url": "https://lowconfidence.example/", "leasing_phone": "(908) 555-8888", "phone_page_url": "", "office_hours": "", "confidence": "low"},
                {"building_id": "bE", "own_site_url": "https://westfieldarms.example/", "leasing_phone": "(908) 555-7777", "phone_page_url": "https://westfieldarms.example/",
                 "office_hours": "Daily 10-6", "confidence": "medium"},
                {"building_id": "bG", "own_site_url": "https://heightsview.example/", "leasing_phone": "", "phone_page_url": "", "office_hours": "", "confidence": "high"},
            ])

    def test_contacts(self):
        self.contact_files()
        d = self.data()
        a = self.U(d, "g1")["contact"]
        self.assertEqual(a, {"phone": "(908) 555-9999", "hours": "Mon-Fri 9-5", "site": "https://thegarwood.example/", "kind": "leasing office", "note": None,
                             "source": "https://thegarwood.example/contact"}, "the building's own number wins; hours fall back to the listed ones")
        b = self.U(d, "g2")["contact"]
        self.assertEqual((b["phone"], b["kind"], b["site"], b["source"]), (None, "broker", "https://www.trulia.com/listing/g2", None), "a broker's number is never shown")
        self.assertEqual(b["note"], X.BROKER_NOTE)
        self.assertIsNone(self.U(d, "g3")["contact"]["phone"], "an individual owner's number is never shown")
        cranford = self.U(d, "c1")["contact"]
        self.assertEqual((cranford["phone"], cranford["hours"], cranford["site"]), (None, None, "https://cranfordliving.example/"), '"nan" is not a phone number')
        self.assertEqual(self.U(d, "c1")["contact"], self.U(d, "c2")["contact"])
        self.assertEqual(self.U(d, "w1")["contact"]["phone"], "(908) 555-7777", "a building only the own-site file lists still gets its contact")
        self.assertNotIn("contact", self.U(d, "d1"), "nothing to show: no contact")
        self.assertNotIn("contact", self.U(d, "h1"), "an own-site row without a number is not a contact")
        self.assertIsNone(self.U(d, "s1")["contact"]["phone"], "words in the phone column are not a number")
        self.assertEqual(self.B(d, "bA")["contact"], a, "buildings[] carries the same contact")
        self.assertIsNone(self.B(d, "bB")["contact"]["phone"])
        self.assertEqual(X.validate(d), [])
        self.assertSecondRunChangesNothing()

    def test_contacts_without_one_file_or_both(self):
        self.assertIn("skipped", self.data()["meta"]["extras"]["contacts"])
        self.contact_files(own=False)
        d = self.data()
        self.assertEqual(self.U(d, "g1")["contact"]["phone"], "(908) 555-0101")
        self.assertNotIn("contact", self.U(d, "w1"))
        self.contact_files()
        self.P.contacts.unlink()
        d = self.data()
        self.assertEqual(self.U(d, "g1")["contact"]["phone"], "(908) 555-9999")
        self.assertIsNone(self.U(d, "g2")["contact"]["phone"], "what the missing file put on the page stays, still without the broker's number")

    def test_about_building(self):
        self.assertIn("skipped", self.data()["meta"]["extras"]["about_building"])
        self.csv(self.P.building_about, [
            {"building_id": "bA", "about_building": "Parking is included. The train is close.", "about_points_json": '[{"icon": "dog", "text": "Dog park."}]', "facts_used_json": "{}"},
            {"building_id": "bD", "about_building": "A quiet block.", "about_points_json": "nan", "facts_used_json": "{}"},
            {"building_id": "bB", "about_building": "", "about_points_json": '[{"icon": "x", "text": "orphan"}]', "facts_used_json": "{}"},
        ])
        d = self.data()
        for o in (self.U(d, "g1"), self.B(d, "bA")):
            self.assertEqual((o["about_building"], o["about_points"]), ("Parking is included. The train is close.", [{"icon": "dog", "text": "Dog park."}]))
        self.assertEqual((self.U(d, "c2")["about_building"], self.U(d, "c2")["about_points"]), ("A quiet block.", None))
        self.assertNotIn("about_building", self.U(d, "g2"))
        self.assertNotIn("about_points", self.U(d, "g2"))
        self.assertSecondRunChangesNothing()
        self.csv(self.P.building_about, [{"building_id": "bD", "about_building": "A quiet block.", "about_points_json": ""}])
        self.assertNotIn("about_building", self.B(self.data(), "bA"), "a building that left the CSV loses its text")

    def test_realtor_lines(self):
        self.assertIn("skipped", self.data()["meta"]["extras"]["realtor_lines"])
        self.csv(self.P.realtor_lines, [
            {"listing_id": "g1", "host_line": "The biggest unit in the building.", "host_catch": "The elevator is not confirmed.", "sub_cost": "Ask for the full bill.", "sub_parking": "", "facts_used_json": "{}"},
            {"listing_id": "g2", "host_line": "", "host_catch": "A catch with no line.", "sub_cost": "", "sub_parking": "The spot is included.", "facts_used_json": "{}"},
            {"listing_id": "c1", "host_line": "A line with no catch.", "host_catch": "nan", "sub_cost": "", "sub_parking": "", "facts_used_json": "{}"},
        ])
        d = self.data()
        self.assertEqual(self.U(d, "g1")["host"], {"line": "The biggest unit in the building.", "catch": "The elevator is not confirmed."})
        self.assertEqual(self.U(d, "g1")["headlines"], {"cost": {"subhead": "Ask for the full bill."}})
        self.assertNotIn("host", self.U(d, "g2"))
        self.assertEqual(self.U(d, "g2")["headlines"], {"parking": {"subhead": "The spot is included."}})
        self.assertEqual(self.U(d, "c1")["host"], {"line": "A line with no catch.", "catch": None})
        self.assertNotIn("headlines", self.U(d, "c1"))
        self.assertNotIn("host", self.U(d, "c2"), "joined on the listing id, not the building")
        self.assertNotIn("host", self.B(d, "bA"))
        self.assertSecondRunChangesNothing()

    def census(self, rows):
        base = {"status": "found", "rating_scale": "5", "review_count": "", "basis": "search_result_display", "source_url": "https://example.com/r",
                "match_confidence": "high", "retrieved_at": "2026-11-16T01:00:00Z", "note": ""}
        self.csv(self.P.ratings, [{**base, **r} for r in rows])

    def test_ratings_filtering(self):
        self.census([
            {"building_id": "bA", "platform": "google", "rating": "4.26", "review_count": "120"},
            {"building_id": "bA", "platform": "google", "rating": "4.4", "review_count": "80"},                        # fewer reviews: the other row is kept
            {"building_id": "bA", "platform": "apartments_com", "rating": "3.9", "review_count": "12.0"},
            {"building_id": "bA", "platform": "yelp", "rating": "7.5", "review_count": "10"},                         # outside 0-5
            {"building_id": "bA", "platform": "zillow", "rating": "4.0", "review_count": "about 30"},                 # count is not a whole number
            {"building_id": "bA", "platform": "openigloo", "rating": "nan", "review_count": "5"},
            {"building_id": "bA", "platform": "birdeye", "rating": "8.8", "rating_scale": "10", "review_count": "50"},
            {"building_id": "bA", "platform": "forrent", "rating": "3.9", "review_count": "12"},                       # repeats Apartments.com
            {"building_id": "bA", "platform": "rentcafe", "rating": "4.9", "review_count": "300", "match_confidence": "low"},
            {"building_id": "bA", "platform": "facebook", "rating": "4.9", "review_count": "300", "status": "not_seen"},
            {"building_id": "bA", "platform": "apartment_list", "rating": "4.1", "review_count": "", "retrieved_at": ""},
            {"building_id": "bA", "platform": "rentable", "rating": "-1", "review_count": "3"},
            {"building_id": "bB", "platform": "google", "status": "not_seen", "rating": "", "note": "one web search run; no rating for this building"},
            {"building_id": "bC", "platform": "google", "status": "not_seen", "rating": "", "note": "NO WEB SEARCH RUN for this building"},
        ])
        d = self.data()
        r = self.U(d, "g1")["ratings"]
        self.assertEqual([(p["platform"], p["rating"], p["count"]) for p in r["platforms"]], [("Google", 4.3, 120), ("Apartments.com", 3.9, 12), ("Apartment List", 4.1, None)])
        self.assertTrue(all(isinstance(p["rating"], float) and (p["count"] is None or type(p["count"]) is int) for p in r["platforms"]))
        self.assertEqual((r["most_reviews"], r["searched"], r["found_any"]), (120, True, True))
        self.assertEqual((r["platforms"][0]["as_of"], r["platforms"][2]["as_of"], r["platforms"][0]["seen_via"]), ("2026-11-16", None, "search result display"))
        self.assertEqual(self.U(d, "g2")["ratings"], {"platforms": [], "most_reviews": 0, "searched": True, "found_any": False})
        self.assertFalse(self.U(d, "g3")["ratings"]["searched"], "the census says no search was run")
        self.assertFalse(self.U(d, "c1")["ratings"]["searched"], 'a building the census never lists was not looked up: "Not looked up yet"')
        self.assertEqual(self.B(d, "bA")["ratings"], r)
        self.assertEqual(X.validate(d), [])
        self.assertSecondRunChangesNothing()

    def test_ratings_skipped_when_absent_or_missing_a_column(self):
        self.assertIn("skipped", self.data()["meta"]["extras"]["ratings"])
        self.assertNotIn("ratings", self.U(self.data(), "g1"))
        self.csv(self.P.ratings, [{"building_id": "bA", "platform": "google", "rating": "4"}])
        self.assertIn("no column status", self.data()["meta"]["extras"]["ratings"])

    def test_photos_link_preference(self):
        d = page()
        self.U(d, "g3")["links"] = {"listing": "https://www.zumper.com/g3", "building": "https://thirdplace.example/"}       # a building link that is its own site
        self.U(d, "c1")["links"] = {"listing": None, "building": "https://www.apartments.com/bD"}
        self.U(d, "w1")["links"] = {}
        self.save(d)
        self.csv(self.P.contacts, [
            {"building_id": "bB", "leasing_phone": "", "leasing_url": "https://brokerage.example/agent", "contact_kind": "broker"},
            {"building_id": "bF", "leasing_phone": "(201) 555-0100", "leasing_url": "https://downtownlofts.example/", "contact_kind": "leasing office"},
            {"building_id": "bG", "leasing_phone": "(201) 555-0101", "leasing_url": "https://www.apartmentlist.com/bG", "contact_kind": "leasing office"},
        ])
        self.csv(self.P.contacts_own, [
            {"building_id": "bA", "own_site_url": "https://thegarwood.example/", "leasing_phone": "", "confidence": "high"},
            {"building_id": "bB", "own_site_url": "https://unsure.example/", "leasing_phone": "", "confidence": "low"},
        ])
        d = self.data()
        own = {"where": "the building's own site", "kind": "own_site"}
        self.assertEqual(self.U(d, "g1")["photos"], {"url": "https://thegarwood.example/", **own}, "1: the own-site file")
        self.assertEqual(self.U(d, "d1")["photos"], {"url": "https://downtownlofts.example/", **own}, "2: the contact's site when it is not a listing site")
        self.assertEqual(self.U(d, "g3")["photos"], {"url": "https://thirdplace.example/", **own}, "2: the building link when it is not a listing site")
        self.assertEqual(self.U(d, "g2")["photos"], {"url": "https://www.trulia.com/listing/g2", "where": "trulia.com", "kind": "listing"},
                         "a broker's page is not the building's own site, and a low-confidence own site is not used")
        self.assertEqual(self.U(d, "h1")["photos"]["url"], "https://www.trulia.com/listing/h1", "3: the listing page, before a listing site's building page")
        self.assertEqual(self.U(d, "c1")["photos"], {"url": "https://www.apartments.com/bD", "where": "apartments.com", "kind": "listing"}, "4: the building's listing page")
        self.assertNotIn("photos", self.U(d, "w1"))
        self.assertEqual(self.B(d, "bA")["photos"], self.U(d, "g1")["photos"])
        self.assertEqual(self.B(d, "bI")["photos"]["url"], "https://www.trulia.com/listing/r1", "a building borrows its best unit's listing page")
        self.assertSecondRunChangesNothing()


# ----------------------------------------------------------------------------------------------------------------------
class Descriptions(Sandbox):
    def desc(self, rows2=(), rows1=()):
        base = {"hood_name": "", "source_name": "Wikipedia", "source_url": "https://en.wikipedia.org/wiki/X", "about_area": "", "scope": "exact",
                "licence_note": "CC BY-SA", "retrieved_at": "2026-11-16", "verified": "yes"}
        if rows2 is not None:
            self.csv(self.P.descriptions2, [{**base, "character": "2", "topic": "", **r} for r in rows2])
        if rows1 is not None:
            self.csv(self.P.descriptions1, [{**base, **r} for r in rows1])

    GARWOOD_BARE = "Garwood is a borough in Union County, in the U.S. state of New Jersey."

    def test_bare_location_sentence(self):
        for q in (self.GARWOOD_BARE, "Elizabeth is a city in and the county seat of Union County, in the U.S. state of New Jersey.",
                  "The City of Orange (known simply as Orange) is a township in Essex County, in the U.S. state of New Jersey.",
                  "Bay Ridge is a neighborhood in the southwest corner of the New York City borough of Brooklyn."):
            self.assertTrue(X.is_bare_location(q), q)
        for q in ("The Capitol Theatre is a historic theater located in the village of Port Chester, Westchester County, New York.",
                  "It is a great community in which to raise kids.",
                  "The borough is roughly bisected by the tracks of NJ Transit's Raritan Valley Line.",
                  "Garwood is a borough in Union County. Its main street is lined with diners and family shops.",
                  "Bath Beach is a neighborhood in the New York City borough of Brooklyn, located at the southwestern edge of the borough on Gravesend Bay, with a long waterfront promenade."):
            self.assertFalse(X.is_bare_location(q), q)

    def test_selection_order(self):
        self.desc(
            rows2=[{"hood_id": "nj:garwood", "quote": "Most streets south of the railroad are named after trees.", "character": "3", "topic": "housing feel"},
                   {"hood_id": "nj:garwood", "quote": "The borough is bisected by the Raritan Valley Line.", "character": "2", "topic": "transit"},
                   {"hood_id": "nj:garwood", "quote": "A second line about trains that is weaker.", "character": "2", "topic": "transit"},
                   {"hood_id": "nj:garwood", "quote": "Who lives here: the racial makeup of the borough.", "character": "3", "topic": "history"},
                   {"hood_id": "nj:garwood", "quote": "Unverified.", "character": "3", "topic": "event", "verified": "no"},
                   {"hood_id": "nj:garwood", "quote": "No source.", "character": "3", "topic": "landmark", "source_url": ""}],
            rows1=[{"hood_id": "nj:garwood", "quote": self.GARWOOD_BARE},
                   {"hood_id": "nj:garwood", "quote": "most streets south of the railroad are named after trees"},          # the same quote again
                   {"hood_id": "nj:garwood", "quote": "The main street has a hardware store older than the borough."}])
        d = self.data()
        got = self.H(d, "nj:garwood")["described"]
        self.assertEqual([x["quote"] for x in got], ["Most streets south of the railroad are named after trees.",
                                                     "The borough is bisected by the Raritan Valley Line.",
                                                     "The main street has a hardware store older than the borough."],
                         "character 3 first, round 2 before round 1, one per topic, no repeat, and never the bare location sentence beside better ones")
        self.assertEqual(set(got[0]), {"quote", "source", "url", "about", "topic", "licence", "featured"})
        self.assertTrue(got[0]["featured"])
        self.assertTrue(all("featured" not in x for x in got[1:]))
        self.assertTrue(all(x["source"] and x["url"] for x in got))
        self.assertIn("no source or link", d["meta"]["extras"]["descriptions"])
        self.assertEqual(X.validate(d), [])
        self.assertSecondRunChangesNothing()

    def test_bare_sentence_only_when_it_is_all_there_is(self):
        self.desc(rows2=[{"hood_id": "nj:cranford", "quote": "A low-character line.", "character": "1", "topic": "history"}],
                  rows1=[{"hood_id": "nj:garwood", "quote": self.GARWOOD_BARE}, {"hood_id": "nj:cranford", "quote": "Cranford is a township in Union County, New Jersey."}])
        d = self.data()
        self.assertEqual([x["quote"] for x in self.H(d, "nj:garwood")["described"]], [self.GARWOOD_BARE])
        self.assertEqual(len(self.H(d, "nj:cranford")["described"]), 1, "two weak lines: one is shown, not both")
        self.assertNotIn("described", self.H(d, "nj:westfield"))

    def test_split_city_and_missing_files(self):
        self.assertIn("skipped", self.data()["meta"]["extras"]["descriptions"])
        self.desc(rows2=[{"hood_id": "nj:jersey-city-downtown", "quote": "Exchange Place faces the Manhattan skyline.", "character": "3", "topic": "waterfront",
                          "about_area": "Exchange Place", "scope": "part"}],
                  rows1=[{"hood_id": "nj:jersey-city", "quote": "Jersey City has a long waterfront walkway."}])
        d = self.data()
        down = self.H(d, "nj:jersey-city-downtown")["described"]
        self.assertEqual([(x["quote"], x["about"]) for x in down], [("Exchange Place faces the Manhattan skyline.", "Exchange Place")], "its own descriptions win over the city's")
        self.assertEqual([(x["quote"], x["about"]) for x in self.H(d, "nj:jersey-city-the-heights")["described"]],
                         [("Jersey City has a long waterfront walkway.", "Jersey City as a whole")])
        self.assertSecondRunChangesNothing()
        self.P.descriptions2.unlink()                           # one round is enough to go on
        d = self.data()
        self.assertEqual(self.H(d, "nj:jersey-city-downtown")["described"][0]["about"], "Jersey City as a whole")
        self.P.descriptions1.unlink()
        self.assertEqual(len(self.H(self.data(), "nj:jersey-city-downtown")["described"]), 1, "both absent: the page is left alone")


# ----------------------------------------------------------------------------------------------------------------------
class RankingAndPlace(Sandbox):
    def test_ranking_by_building_with_penalty(self):
        d = self.data()
        g, c, w = (self.H(d, i) for i in ("nj:garwood", "nj:cranford", "nj:westfield"))
        self.assertEqual(g["experience_score"], 54.0, "mean of three buildings: 60, 54, 48")
        self.assertEqual(c["experience_score"], 66.0, "one building counts once (70, not the mean of 70 and 68), minus 2 x 2")
        self.assertEqual(w["experience_score"], 46.0)
        self.assertEqual(c["experience_score_basis"], "mean of the best place in each of its top 1 building(s), minus 4 for having fewer than three buildings")
        self.assertEqual(g["experience_score_basis"], "mean of the best place in each of its top 3 building(s)")
        self.assertEqual((c.get("single_building"), w.get("single_building"), g.get("single_building")), (True, True, None))
        self.assertEqual(self.Y(d, "quiet")["hood_ids"], ["nj:cranford", "nj:garwood", "nj:westfield"])
        self.assertEqual([(c["rank_in_experience"], g["rank_in_experience"], w["rank_in_experience"])], [(1, 2, 3)])
        self.assertIs(type(c["rank_in_experience"]), int)
        self.assertEqual(X.validate(d), [])
        self.assertSecondRunChangesNothing()

    def test_two_buildings_lose_two_points(self):
        d = page()
        d["units"] = [u for u in d["units"] if u["id"] != "g3"]
        d["buildings"] = [b for b in d["buildings"] if b["id"] != "bC"]
        self.save(d)
        g = self.H(self.data(), "nj:garwood")
        self.assertEqual(g["experience_score"], 55.0, "(60 + 54) / 2 - 2")
        self.assertIn("top 2 building(s), minus 2", g["experience_score_basis"])

    def test_tie_breaks_on_the_neighborhood_id(self):
        d = page()
        for u in d["units"]:
            if u["hood_id"] in ("ny:sunnyside", "ny:bay-ridge"):
                u["scores"]["rank"] = 50.0
        for b in d["buildings"]:
            if b["id"] in ("bH", "bI"):
                b["best_rank_score"] = 50.0
        self.save(d)
        d = self.data()
        order = self.Y(d, "city")["hood_ids"]
        self.assertLess(order.index("ny:bay-ridge"), order.index("ny:sunnyside"))
        self.assertEqual([self.H(d, i)["rank_in_experience"] for i in order], [1, 2, 3, 4, 5])

    def test_units_of_another_neighborhood_do_not_count_and_scores_fall_back_to_units(self):
        d = page()
        del d["buildings"]                                                    # an older page: no buildings[]
        self.H(d, "nj:westfield")["unit_ids"].append("c1")                    # a list that names a place from elsewhere
        self.U(d, "g2")["scores"] = {"rank": None}                            # an unscored place is not a zero
        self.save(d)
        d = self.data()
        self.assertEqual(self.H(d, "nj:westfield")["experience_score"], 46.0, "Cranford's 70 is not Westfield's")
        self.assertEqual(self.H(d, "nj:cranford")["experience_score"], 66.0, "two units of one building are one building")
        self.assertEqual(self.H(d, "nj:garwood")["experience_score"], 52.0, "(60 + 48) / 2 - 2: the unscored place is a missing building")
        self.assertTrue(any("not their own" in p for p in X.validate(d)))

    def test_stale_rank_is_cleared_and_empty_neighborhood_is_last(self):
        d = page()
        self.Y(d, "quiet")["hood_ids"] = ["nj:garwood", "nj:westfield"]
        self.H(d, "nj:cranford").update({"rank_in_experience": 1, "experience_score": 99.0, "experience_score_basis": "old", "single_building": True})
        d["units"] = [u for u in d["units"] if u["id"] != "w1"]
        d["buildings"] = [b for b in d["buildings"] if b["id"] != "bE"]
        self.H(d, "nj:westfield")["unit_ids"] = []
        self.save(d)
        d = self.data()
        c = self.H(d, "nj:cranford")
        self.assertFalse(any(k in c for k in X.RANK_FIELDS), "a neighborhood in no experience carries no rank from an earlier run")
        w = self.H(d, "nj:westfield")
        self.assertEqual((w["experience_score"], w["experience_score_basis"], w["rank_in_experience"]), (None, None, 2))

    def test_coordinates_use_the_shown_places(self):
        self.assertIn("skipped", self.data()["meta"]["extras"]["coordinates"])
        self.csv(self.P.ranked_units, [
            {"listing_id": "g1", "hood_id": "nj:garwood", "lat": "40.651234", "lon": "-74.321234", "shown": "True", "other": "x"},
            {"listing_id": "g2", "hood_id": "nj:garwood", "lat": "40.653234", "lon": "-74.323234", "shown": "True", "other": "x"},
            {"listing_id": "gx", "hood_id": "nj:garwood", "lat": "40.9", "lon": "-74.9", "shown": "False", "other": "x"},        # ranked, not on the page
            {"listing_id": "cx", "hood_id": "nj:cranford", "lat": "40.66", "lon": "-74.30", "shown": "False", "other": "x"},
            {"listing_id": "cy", "hood_id": "nj:cranford", "lat": "nan", "lon": "", "shown": "True", "other": "x"},
            {"listing_id": "zz", "hood_id": "nj:not-on-page", "lat": "41", "lon": "-73", "shown": "True", "other": "x"},
        ])
        d = self.data()
        g = self.H(d, "nj:garwood")
        self.assertEqual((g["lat"], g["lon"]), (40.65223, -74.32223), "the mean of the two shown places, five decimals, as numbers")
        self.assertEqual((self.H(d, "nj:cranford")["lat"], self.H(d, "nj:cranford")["lon"]), (40.66, -74.3), "nothing shown with a position: the ranked ones")
        self.assertEqual(self.H(d, "nj:westfield")["lat"], 40.0)
        self.assertSecondRunChangesNothing()

    def test_shape_check_and_strict(self):
        d = self.data()
        self.assertEqual(X.validate(d), [])
        self.assertEqual(self.run_script(strict=True)[0], 0)
        bad = json.loads(json.dumps(d))
        bad["years"][0]["display_label"] = ""
        bad["years"][0]["hood_ids"].append("nj:gone")
        self.H(bad, "nj:garwood")["rank_in_experience"] = 7
        self.U(bad, "g1")["hood_id"] = "nj:nowhere"
        self.U(bad, "g2")["contact"] = {"phone": "(908) 555-0202", "kind": "broker"}
        self.B(bad, "bC")["contact"] = {"phone": "(908) 555-0303", "kind": "individual owner"}
        self.H(bad, "nj:cranford")["described"] = [{"quote": "No source.", "source": "", "url": "https://x"}]
        self.U(bad, "c1")["ratings"] = {"platforms": [{"platform": "Google", "rating": 9.1, "count": "12"}]}
        self.U(bad, "c2")["floor"] = "nan"
        problems = "\n".join(X.validate(bad))
        for needle in ("without display_label", "do not exist: nj:gone", "rank_in_experience is not 1..", "whose neighborhood does not exist", "2 place(s) or building(s) show a phone",
                       "without a source and a link", "rating outside 0-5", "printed missing value"):
            self.assertIn(needle, problems)
        self.assertEqual(X.validate({"years": "broken"})[:0], [], "the check never raises")
        # strict: a page whose shape the blocks cannot repair (a place in a neighborhood that does not exist)
        d = page()
        self.U(d, "g1")["hood_id"] = "nj:nowhere"
        self.save(d)
        self.assertEqual(self.run_script()[0], 0, "violations are printed, not fatal")
        self.assertTrue(any("shape check:" in line and "problem(s)" in line for line in self.out))
        self.assertEqual(self.run_script(strict=True)[0], 1)

    def test_main_takes_root_and_strict(self):
        self.assertEqual(X.main(["--root", str(self.root), "--strict"]), 0)


# ----------------------------------------------------------------------------------------------------------------------
class EverythingTogether(Sandbox):
    def test_all_inputs_twice_then_inputs_vanish(self):
        """Every input present: the second run changes nothing. Then every input removed: the page keeps what it has
        and the run still changes nothing but the report."""
        SceneText.years_csv(self)
        SceneText.hoods_csv(self, [{"hood_id": "nj:garwood", "scene": "Garwood scene."}, {"hood_id": "nj:jersey-city", "scene": "City scene."}])
        VoicesSurveyRules.quotes(self, [{"hood_id": "nj:garwood", "excerpt": "A diverse, friendly town."}, {"hood_id": "nj:jersey-city", "excerpt": "Citywide.", "source_area": "Jersey City"}])
        VoicesSurveyRules.rules(self, [{"municipality": "Garwood", "applies_to_hood_ids": "nj:garwood", "topic": "dogs", "rule": "leash_law", "summary": "Leash."}])
        PerBuilding.contact_files(self)
        PerBuilding.census(self, [{"building_id": "bA", "platform": "google", "rating": "4.2", "review_count": "10"}])
        Descriptions.desc(self, rows2=[{"hood_id": "nj:garwood", "quote": "Named after trees.", "character": "3", "topic": "housing feel"}],
                          rows1=[{"hood_id": "nj:cranford", "quote": "A river runs through the township."}])
        self.csv(self.P.survey2, [{"hood_id": "nj:cranford", "source_site": "niche.com", "measure": "niche_overall_rating", "value": "4.1", "as_of": "2026-11-15",
                                   "source_url": "https://niche.com/c", "source_area": "Cranford, NJ"}])
        self.csv(self.P.building_about, [{"building_id": "bA", "about_building": "Text.", "about_points_json": "[]"}])
        self.csv(self.P.realtor_lines, [{"listing_id": "g1", "host_line": "Line.", "host_catch": "Catch.", "sub_cost": "Cost."}])
        self.csv(self.P.ranked_units, [{"hood_id": "nj:garwood", "lat": "40.65", "lon": "-74.32", "shown": "True"}])
        code, d = self.run_script(strict=True)
        self.assertEqual(code, 0, self.out)
        self.assertFalse(any("skipped" in v or "FAILED" in v for v in d["meta"]["extras"].values()), d["meta"]["extras"])
        self.assertSecondRunChangesNothing()
        text = self.P.data_json.read_text()
        for bad in ("NaN", '"nan"', '"None"', '"null"', "Infinity"):
            self.assertNotIn(bad, text)
        g = self.U(d, "g1")
        self.assertEqual(list(g)[-len(X.OWNED["units"]):], list(X.OWNED["units"]), "the added fields sit last, in one fixed order")
        shutil.rmtree(self.root / "data")
        code, after = self.run_script()
        self.assertEqual(code, 0)
        d["meta"].pop("extras")
        report = after["meta"].pop("extras")
        self.assertEqual(d, after, "with every input gone the page keeps what it had")
        self.assertTrue(all("skipped" in report[k] for k in ("experience_text", "round2_quotes", "contacts", "ratings", "descriptions", "coordinates")))


# ----------------------------------------------------------------------------------------------------------------------
@unittest.skipUnless((REAL_ROOT / "site" / "data.json").exists(), "no site/data.json to run against")
class Integration(unittest.TestCase):
    def test_real_script_twice_on_a_copy_of_the_live_page_data(self):
        tmp = Path(tempfile.mkdtemp(prefix="extras_live_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "site").mkdir()
        target = tmp / "site" / "data.json"
        try:
            json.loads((REAL_ROOT / "site" / "data.json").read_text(encoding="utf-8"))
        except ValueError:
            self.skipTest("site/data.json is being rewritten right now")
        shutil.copy(REAL_ROOT / "site" / "data.json", target)
        os.symlink(REAL_ROOT / "data", tmp / "data")                          # the real inputs, read-only use
        cmd = [sys.executable, str(HERE / "page_data_extras.py"), "--root", str(tmp)]
        first = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        once = target.read_bytes()
        second = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(once, target.read_bytes(), "the second run changed the file")
        self.assertIn("unchanged", second.stdout.splitlines()[0])
        self.assertNotIn("FAILED", second.stdout)
        text = once.decode("utf-8")

        def no_constant(name):
            raise AssertionError(f"{name} in the output JSON")
        d = json.loads(text, parse_constant=no_constant)
        self.assertEqual(X._nan_like(d), [], 'NaN, "nan", "None" or "null" as a value')
        self.assertEqual(json.loads(second.stdout and text)["meta"]["extras"], d["meta"]["extras"])
        for y in d["years"]:
            self.assertTrue(y.get("display_label"))
            ranks = [next(h for h in d["neighborhoods"] if h["id"] == i)["rank_in_experience"] for i in y["hood_ids"]]
            self.assertEqual(ranks, list(range(1, len(ranks) + 1)))
        for o in d["units"] + d.get("buildings", []):
            c = o.get("contact") or {}
            self.assertFalse(c.get("phone") and X.is_private_line(c.get("kind")), o.get("id"))


# ----------------------------------------------------------------------------------------------------------------------
class Artifact(unittest.TestCase):
    PAGE = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>House Hunt</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<style>body{margin:0}</style>\n</head>\n<body>\n\n<main id="view"></main>\n'
            '<script>var s="<body> and </body></html> inside a string stay";</script>\n</body>\n</html>\n')

    def test_shell_is_removed_and_the_rest_kept(self):
        out = A.to_artifact(self.PAGE)
        self.assertEqual(out, '<title>House Hunt</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
                              '<link rel="preconnect" href="https://fonts.googleapis.com">\n<style>body{margin:0}</style>\n<main id="view"></main>\n'
                              '<script>var s="<body> and </body></html> inside a string stay";</script>\n')
        self.assertEqual(A.check(out), [])
        self.assertEqual(A.to_artifact(self.PAGE), out)

    def test_banner_goes_first_in_the_body(self):
        out = A.to_artifact(self.PAGE, "Preview <draft> & more")
        self.assertIn('</style>\n<div id="draftbar" role="note" style="background:var(--butter);color:var(--ink);', out)
        self.assertIn(">Preview &lt;draft&gt; &amp; more</div>\n<main", out)

    def test_checks_and_cli(self):
        self.assertTrue(any("<title>" in p for p in A.check("<style>" + "x" * 9000 + "</style><title>Late</title>")))
        self.assertTrue(any("16 MB" in p for p in A.check("<title>Big</title>" + "x" * (16 * 1024 * 1024))))
        self.assertRaises(ValueError, A.to_artifact, "<p>not a whole page</p>")
        tmp = Path(tempfile.mkdtemp(prefix="artifact_test_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "index.html").write_text(self.PAGE, encoding="utf-8")
        self.assertEqual(A.main(["--src", str(tmp / "index.html"), "--out", str(tmp / "artifact.html"), "--banner", "Preview"]), 0)
        self.assertTrue((tmp / "artifact.html").read_text().startswith("<title>House Hunt</title>"))
        self.assertEqual(A.main(["--src", str(tmp / "missing.html"), "--out", str(tmp / "x.html")]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=1)
