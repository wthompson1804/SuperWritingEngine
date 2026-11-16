"""Tests for the consistency helpers of verify_all.py. Synthetic inputs only; no project file is read or written.

    python3 scripts/test_verify_all.py        (or: python3 -m pytest scripts/test_verify_all.py)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_all as va  # noqa: E402


class CompareIds(unittest.TestCase):
    def test_same_set_any_order(self):
        self.assertEqual(va.compare_ids("a", ["u1", "u2"], "b", ["u2", "u1"]), [])

    def test_missing_on_each_side_and_repeat(self):
        out = va.compare_ids("ranked", ["u1", "u2", "u2"], "page", ["u1", "u3"])
        self.assertEqual(len(out), 3)
        self.assertTrue(any("repeated in ranked" in s and "u2" in s for s in out))
        self.assertTrue(any("in ranked but not in page: u2" in s for s in out))
        self.assertTrue(any("in page but not in ranked: u3" in s for s in out))


class Verdicts(unittest.TestCase):
    def test_gaps(self):
        rows = [{"listing_id": "u1", "verdict": "ok"}, {"listing_id": "u2", "verdict": "disclose"},
                {"listing_id": "u2", "verdict": "remove"}, {"listing_id": "u4", "verdict": "asterisk"}]
        self.assertEqual(va.verdict_gaps(["u1", "u2", "u3", "u4"], rows), [("u2", "verdict is 'remove'"), ("u3", "no reviewed verdict")])
        self.assertEqual(va.verdict_gaps([], rows), [])


class SceneText(unittest.TestCase):
    def test_only_neighborhoods_with_apartments_need_text(self):
        hoods = [{"id": "h1", "unit_ids": ["u1"], "prose": {"scene": "A quiet street."}},
                 {"id": "h2", "unit_ids": ["u2"], "prose": {"scene": "  "}},
                 {"id": "h3", "unit_ids": ["u3"]},
                 {"id": "h4", "unit_ids": [], "prose": None}]
        self.assertEqual(va.hoods_without_scene(hoods), ["h2", "h3"])


class Kinds(unittest.TestCase):
    def test_field_absent_is_reported_as_absent(self):
        self.assertEqual(va.non_apartment_rows([{"id": "u1", "rent": 2000}]), ([], []))

    def test_floor_plan_and_status_caught(self):
        present, bad = va.non_apartment_rows([{"id": "u1", "kind": "apartment"}, {"id": "u2", "listing_kind": "floor_plan"},
                                              {"id": "u3", "status": "not_an_apartment"}])
        self.assertEqual(present, ["kind", "listing_kind", "status"])
        self.assertEqual(bad, [("u2", "listing_kind", "floor_plan"), ("u3", "status", "not_an_apartment")])


class Keys(unittest.TestCase):
    def test_line_numbers_only(self):
        blob = (b"id,url\n"
                b"1,https://api.example.org/x?get=NAME&key=REDACTED\n"
                b"2,https://api.example.org/x?key=" + b"a" * 19 + b"&y=1\n"
                b"3,https://api.example.org/x?api_key=" + b"b" * 40 + b"\n"
                b"4,https://api.example.org/x?KEY=" + b"c" * 20 + b"&z=2\n")
        self.assertEqual(va.key_leaks(blob), [4, 5])
        self.assertEqual(va.key_leaks(b""), [])


class Fresh(unittest.TestCase):
    def test_missing_and_stale(self):
        self.assertEqual(va.stale_outputs({"dist": 20.0, "artifact": 21.0}, {"data": 10.0, "template": 19.0}), ([], []))
        missing, stale = va.stale_outputs({"dist": 15.0, "artifact": None}, {"data": 10.0, "template": 19.0})
        self.assertEqual(missing, ["artifact"])
        self.assertEqual(stale, ["dist is older than template"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
