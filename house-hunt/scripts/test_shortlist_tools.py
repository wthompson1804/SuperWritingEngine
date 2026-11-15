"""Tests for call_sheet.py, tour_days.py and recheck_shortlist.py. Synthetic rows only; no network, no data files.

    python3 scripts/test_shortlist_tools.py        (or: python3 -m pytest scripts/test_shortlist_tools.py)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import call_sheet as cs  # noqa: E402
import recheck_shortlist as rs  # noqa: E402
import tour_days as td  # noqa: E402


def settled_unit(**over) -> dict:
    """A unit with every fact confirmed. Only the always-asked questions should remain."""
    u = {
        "listing_id": "L1", "building_id": "b1", "building_name": "Test House", "address": "1 Main St",
        "city": "Testville", "state": "NY", "hood": "Testville", "group_label": "The Test Year", "unit": "4B",
        "listed_rent": "2400", "all_in": "2650", "all_in_unknown_lines": "", "shown": "True",
        "rank_score": "0.9", "shown_rank": "1", "url": "https://www.apartmentlist.com/ny/testville/test-house",
        "building_url": "", "lat": "40.75", "lon": "-73.80",
        "unit_floor": "4.0", "unit_floor_basis": "confirmed",
        "elevator": "yes", "elevator_basis": "confirmed",
        "dogs_allowed": "yes", "dogs_allowed_basis": "confirmed",
        "dog_weight_limit_lb": "50", "dog_weight_limit_lb_basis": "confirmed",
        "dog_policy_text": "Dogs welcome. No breed restrictions.",
        "pet_rent": "50.0", "pet_rent_monthly_basis": "confirmed", "pet_one_time_fee_text": "$500",
        "parking_type": "garage", "parking_fee": "100.0", "parking_fee_monthly_basis": "confirmed",
        "parking_text": "garage $100/mo, no waitlist",
        "required_fees_text": "$25/mo trash", "utilities_included": "heat and hot water",
        "utilities_included_basis": "confirmed", "income_requirement": "40x monthly rent",
        "rent_listed_price_is": "gross", "rent_needs_call": "no", "rent_asterisk": "", "rent_offer_text": "",
        "rent_lease_months": "12.0", "rent_free_months": "",
        "rent_first_full_payment_date": "2026-12-01",
        "rent_first_full_payment_note": "move-in 2026-12-01 (available date); no free period; rent due on the 1st",
        "available_date": "2026-12-01", "confirm_what": "", "confirm_why": "", "to_confirm": "", "tour_confirm": "",
    }
    u.update(over)
    return u


def keys(units) -> list[str]:
    return [k for k, _ in cs.questions_for_building(units)]


class QuestionTests(unittest.TestCase):
    ALWAYS = {"available", "guarantor", "turnaround"}

    def test_confirmed_facts_are_not_asked(self):
        self.assertEqual(set(keys([settled_unit()])), self.ALWAYS)

    def test_each_open_fact_yields_its_question(self):
        cases = {
            "floor": [dict(unit_floor="", unit_floor_basis="unknown"),
                      dict(unit_floor="2.0", unit_floor_basis="inferred"),
                      dict(confirm_what="floor"),
                      dict(tour_confirm="Confirm the floor")],
            "elevator": [dict(elevator_basis="inferred"), dict(elevator=""), dict(confirm_what="elevator")],
            "dogs_allowed": [dict(dogs_allowed="conflicting"), dict(confirm_what="dogs allowed")],
            "dog_weight": [dict(dog_weight_limit_lb="", dog_weight_limit_lb_basis=""),
                           dict(tour_confirm="Confirm the dog weight limit in pounds")],
            "dog_breeds": [dict(dog_policy_text="Dogs allowed"), dict(dog_policy_text="Breed restrictions apply")],
            "pet_rent": [dict(pet_rent="", pet_rent_monthly_basis=""), dict(all_in_unknown_lines="pet rent")],
            "pet_fee": [dict(pet_one_time_fee_text="")],
            "parking": [dict(parking_fee="", parking_fee_monthly_basis=""), dict(parking_type=""),
                        dict(all_in_unknown_lines="building fees; parking fee"), dict(parking_text="garage $100/mo")],
            "required_fees": [dict(required_fees_text=""), dict(all_in_unknown_lines="building fees"),
                              dict(required_fees_text="amenity fee (amount not shown)")],
            "utilities": [dict(utilities_included="", utilities_included_basis="")],
            "income": [dict(income_requirement="")],
            "rent_gross_or_net": [dict(rent_listed_price_is="unknown"), dict(rent_needs_call="yes")],
            "lease_term": [dict(rent_lease_months=""), dict(rent_lease_months="15.0")],
            "first_payment": [dict(rent_first_full_payment_date=""), dict(rent_free_months="1"),
                              dict(rent_listed_price_is="net_effective")],
        }
        for key, variants in cases.items():
            for over in variants:
                with self.subTest(key=key, over=over):
                    self.assertIn(key, keys([settled_unit(**over)]))

    def test_one_open_fact_adds_only_its_question(self):
        got = set(keys([settled_unit(unit_floor="", unit_floor_basis="unknown")]))
        self.assertEqual(got, self.ALWAYS | {"floor"})

    def test_question_text_names_the_unit_and_deadline(self):
        qs = dict(cs.questions_for_building([settled_unit(unit_floor="", unit_floor_basis="unknown")]))
        self.assertIn("unit 4B", qs["floor"])
        self.assertIn("Dec 15, 2026", qs["available"])

    def test_twelve_month_price_known_is_not_asked(self):
        self.assertNotIn("lease_term", keys([settled_unit(rent_lease_months="15.0", price_12_month="2500")]))

    def test_missing_columns_do_not_break(self):
        bare = {"listing_id": "L9", "unit": "2A", "listed_rent": "2000"}
        got = keys([bare])
        for k in ("floor", "elevator", "dogs_allowed", "dog_weight", "parking", "required_fees", "utilities", "income"):
            self.assertIn(k, got)

    def test_renamed_columns_are_read(self):
        u = settled_unit()
        u["pet_rent_monthly"] = u.pop("pet_rent")
        u["parking_fee_monthly"] = u.pop("parking_fee")
        self.assertEqual(set(keys([u])), self.ALWAYS)

    def test_building_fact_open_on_any_unit_is_asked_once(self):
        a, b = settled_unit(), settled_unit(listing_id="L2", unit="5C", elevator_basis="inferred")
        got = keys([a, b])
        self.assertEqual(got.count("elevator"), 1)
        self.assertEqual(got.count("available"), 2)


class SheetTests(unittest.TestCase):
    def frame(self):
        rows = [settled_unit(listing_id=f"L{i}", building_id=f"b{i // 2}", unit=f"{i}A", rank_score=str(1 - i / 100))
                for i in range(12)]
        rows.append(settled_unit(listing_id="H1", building_id="bh", shown="False", held_for_confirmation="True",
                                 rank_score="2.0"))
        rows.append(settled_unit(listing_id="O1", building_id="bo", group_label="The Other Year", rank_score="0.1"))
        df = pd.DataFrame(rows)
        if "held_for_confirmation" in df:
            df["held_for_confirmation"] = df["held_for_confirmation"].fillna("False")
        return df

    def test_top_n_buildings_per_year_one_row_per_building(self):
        picked = cs.pick_buildings(self.frame(), per_year=3)
        test_year = [b for b in picked if b["year"] == "The Test Year"]
        self.assertEqual([b["building_id"] for b in test_year], ["b0", "b1", "b2"])
        self.assertEqual([len(b["units"]) for b in test_year], [2, 2, 2])
        self.assertEqual(len([b for b in picked if b["year"] == "The Other Year"]), 1)

    def test_held_only_with_flag(self):
        ids = lambda picked: {b["building_id"] for b in picked}  # noqa: E731
        self.assertNotIn("bh", ids(cs.pick_buildings(self.frame(), per_year=10)))
        self.assertIn("bh", ids(cs.pick_buildings(self.frame(), per_year=10, include_held=True)))

    def test_year_filter(self):
        picked = cs.pick_buildings(self.frame(), per_year=2, years="other")
        self.assertEqual({b["year"] for b in picked}, {"The Other Year"})

    def test_contact_only_when_present_in_data(self):
        with tempfile.TemporaryDirectory() as d:
            rows = cs.sheet_rows(cs.pick_buildings(self.frame(), per_year=1))
            csv_path, _ = cs.write_outputs(rows, Path(d))
            cols = list(pd.read_csv(csv_path, dtype=str).columns)
            self.assertNotIn("contact", cols)
            for c in cs.ANSWER_COLS + ["listing_ids", "building_id"]:
                self.assertIn(c, cols)
            df = self.frame()
            df.loc[0, "notes"] = "ask leasing 914-635-2742"
            df.loc[2, "building_url"] = "https://www.testhouse.example/"
            rows = cs.sheet_rows(cs.pick_buildings(df, per_year=2))
            csv_path, _ = cs.write_outputs(rows, Path(d))
            out = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
            by = out.set_index("building_id")["contact"]
            self.assertIn("914-635-2742", by["b0"])
            self.assertIn("testhouse.example", by["b1"])
            self.assertEqual(by["bo"], "")

    def test_aggregator_url_is_not_a_contact(self):
        self.assertEqual(cs.contact_for([settled_unit(building_url="https://www.trulia.com/building/x")]), ("", ""))

    def test_answers_explode_to_one_row_per_listing(self):
        filled = pd.DataFrame([{"building_id": "b0", "listing_ids": "L0; L1", "units": "0A; 1A",
                                "ans_floor": "0A=3; 1A=5", "ans_elevator": "yes", "ans_available_date": "2026-12-01",
                                "called_at": "2026-11-18T15:00:00-05:00"}])
        out = cs.answers_by_listing(filled)
        self.assertEqual(list(out["listing_id"]), ["L0", "L1"])
        self.assertEqual(list(out["ans_floor"]), ["3", "5"])
        self.assertEqual(list(out["ans_elevator"]), ["yes", "yes"])
        self.assertEqual(list(out["ans_available_date"]), ["2026-12-01", "2026-12-01"])


class RecheckTests(unittest.TestCase):
    def test_cap_of_forty(self):
        self.assertEqual(rs.MAX_LISTINGS, 40)
        self.assertEqual(len(rs.enforce_cap([f"id{i}" for i in range(40)])), 40)
        with self.assertRaises(SystemExit):
            rs.enforce_cap([f"id{i}" for i in range(41)])
        self.assertEqual(len(rs.enforce_cap(["a"] * 100)), 1)   # duplicates do not count

    def test_cap_stops_main_before_any_request(self):
        with self.assertRaises(SystemExit):
            rs.main(["--ids", ",".join(f"id{i}" for i in range(41)), "--ranked", "/nonexistent/never_read.csv"])

    def test_never_hosts_and_trulia(self):
        gate = rs.HostGate()
        for url in ("https://www.zillow.com/b/x", "https://streeteasy.com/building/x", "https://www.apartments.com/x",
                    "https://newyork.craigslist.org/apa/1.html", "https://www.trulia.com/home/x"):
            ok, status, _ = gate.check(url)
            self.assertFalse(ok, url)
            self.assertEqual(status, "skipped")
        self.assertTrue(rs.HostGate(allow_trulia=True).check("https://www.trulia.com/home/x")[0])
        allowed = rs.HostGate(allow_trulia=True)
        for url in ("https://www.zillow.com/b/x", "https://streeteasy.com/x", "https://www.apartments.com/x",
                    "https://newyork.craigslist.org/apa/1.html"):
            self.assertFalse(allowed.check(url)[0], url)   # --allow-trulia opens Trulia only
        self.assertTrue(gate.check("https://www.zumper.com/listings/1p/x")[0])

    def _run(self, responses, rows, **gate_kw):
        calls = []

        def fetch(url):
            calls.append(url)
            return responses[url]
        out = rs.recheck(rows, rs.HostGate(**gate_kw), fetch, now=lambda: "2026-11-16T00:00:00+00:00")
        return out, calls

    def test_one_refusal_stops_the_host(self):
        rows = [{"listing_id": f"z{i}", "url": f"https://www.example-listings.com/p/{i}", "unit": "1", "listed_rent": "2000"}
                for i in range(4)]
        rows.append({"listing_id": "other", "url": "https://other.example.org/x", "unit": "1", "listed_rent": "2000"})
        for code in (403, 429):
            responses = {r["url"]: (200, "<html>ok $2,000</html>" + "x" * 40000, "") for r in rows}
            responses[rows[1]["url"]] = (code, "", "")
            out, calls = self._run(responses, rows)
            host_calls = [c for c in calls if "example-listings" in c]
            self.assertEqual(host_calls, [rows[0]["url"], rows[1]["url"]], f"no request after the {code}")
            self.assertEqual([r["status"] for r in out[1:4]], ["blocked"] * 3)
            self.assertIn("other.example.org", " ".join(calls))   # other hosts carry on

    def test_challenge_page_counts_as_refusal(self):
        rows = [{"listing_id": f"c{i}", "url": f"https://www.example-listings.com/p/{i}", "unit": "1", "listed_rent": "2000"}
                for i in range(3)]
        responses = {r["url"]: (200, "<html><div id='px-captcha'></div></html>", "") for r in rows}
        out, calls = self._run(responses, rows)
        self.assertEqual(len(calls), 1)
        self.assertEqual([r["status"] for r in out], ["blocked"] * 3)

    def test_trulia_is_never_fetched_without_flag(self):
        rows = [{"listing_id": "t1", "url": "https://www.trulia.com/home/x", "unit": "1", "listed_rent": "2000"}]
        out, calls = self._run({}, rows)
        self.assertEqual(calls, [])
        self.assertEqual(out[0]["status"], "skipped")

    def test_same_url_is_requested_once(self):
        url = "https://bldg.example.org/floorplans"
        rows = [{"listing_id": f"u{i}", "url": url, "unit": str(i), "listed_rent": "2000"} for i in range(3)]
        out, calls = self._run({url: (404, "", "")}, rows)
        self.assertEqual(calls, [url])
        self.assertEqual([r["status"] for r in out], ["gone"] * 3)

    def test_classify(self):
        self.assertEqual(rs.classify("2400", rs._result(True, 2400))[0], "still_listed")
        self.assertEqual(rs.classify("2400", rs._result(True, 2475)), ("price_changed", "2475", "+75"))
        self.assertEqual(rs.classify("2400", rs._result(False))[0], "gone")
        self.assertEqual(rs.classify("2400", rs._result(None))[0], "unparsed")

    def test_zumper_parse(self):
        import json
        state = {"detail": {"entity": {"data": {"listing_id": 123, "price": 2350, "listing_status": 1,
                                                 "date_available": "2026/12/05"}}}}
        html = "<script>window.__PRELOADED_STATE__ = " + json.dumps(state) + ";</script>"
        row = {"listing_id": "zumper-123", "listed_rent": "2300"}
        self.assertEqual(rs.classify("2300", rs.parse_zumper(html, row)), ("price_changed", "2350", "+50"))

    def test_trulia_parse(self):
        import json
        hd = {"floorPlans": {"floorPlanGroups": [{"plans": [{"id": "9", "units": [
            {"id": "455", "name": "Unit PA-202", "priceRange": {"min": 1805}, "availabilityText": "Available Now"}]}]}]}}
        html = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({"props": {"homeDetails": hd}}) + "</script>"
        self.assertEqual(rs.classify("1805", rs.parse_trulia(html, {"listing_id": "rc:trulia:b1:Unit_PA-202:455", "unit": "PA-202"}))[0],
                         "still_listed")
        self.assertEqual(rs.classify("1805", rs.parse_trulia(html, {"listing_id": "rc:trulia:b1:Unit_X:999", "unit": "X"}))[0], "gone")


class TourTests(unittest.TestCase):
    PTS = [("s_stamford1", 41.05, -73.54), ("s_stamford2", 41.06, -73.53), ("s_norwalk", 41.10, -73.42),
           ("q_jamaica", 40.70, -73.80), ("q_kew", 40.71, -73.83), ("q_forest", 40.72, -73.84),
           ("n_harrison", 40.74, -74.15), ("n_newark", 40.73, -74.17), ("n_montclair", 40.81, -74.21)]

    def stops(self, order=None):
        pts = self.PTS if order is None else [self.PTS[i] for i in order]
        return [{"id": i, "lat": la, "lon": lo, "year": "Y", "units": [{"building_id": i, "unit": "1"}]} for i, la, lo in pts]

    def plan(self, order=None, k=3):
        return [[s["id"] for s in day] for day in td.plan_days(self.stops(order), k, td.JAMAICA)]

    def test_grouping_is_geographic(self):
        days = self.plan()
        self.assertEqual(len(days), 3)
        for day in days:
            self.assertEqual(len({i[0] for i in day}), 1, day)   # each day is one region (id prefix)
        self.assertEqual(days[0][0], "q_jamaica")               # nearest day first, nearest stop first

    def test_grouping_is_deterministic(self):
        base = self.plan()
        self.assertEqual(base, self.plan())
        self.assertEqual(base, self.plan(order=list(reversed(range(9)))))
        self.assertEqual(base, self.plan(order=[4, 0, 8, 2, 6, 1, 7, 3, 5]))

    def test_max_per_day_splits_big_days(self):
        days = td.plan_days(self.stops(), 1, td.JAMAICA, max_per_day=3)
        self.assertTrue(all(len(d) <= 3 for d in days))
        self.assertEqual(sum(len(d) for d in days), 9)
        self.assertEqual(len(td.plan_days(self.stops(), 2, td.JAMAICA)), 2)   # explicit K is kept

    def test_nearest_neighbour_order(self):
        day = td.order_stops(self.stops()[3:6], td.JAMAICA)
        self.assertEqual([s["id"] for s in day], ["q_jamaica", "q_kew", "q_forest"])

    def test_drive_time_is_labelled_estimate(self):
        lg = td.leg((40.70, -73.80), (40.80, -73.80))
        self.assertIn("estimate", lg["basis"])
        self.assertAlmostEqual(lg["miles"], 6.9, delta=0.1)
        self.assertAlmostEqual(lg["minutes"], lg["miles"] * td.ROAD_FACTOR / td.AVG_MPH * 60)
        self.assertTrue(td.leg((40.70, -73.80), (41.05, -73.54))["crossing"])   # Queens to Stamford crosses water

    def test_default_start_is_jamaica(self):
        self.assertEqual(td.parse_start(None), (40.699608, -73.808530))
        self.assertEqual(td.parse_start("41.0, -73.5"), (41.0, -73.5))


if __name__ == "__main__":
    unittest.main(verbosity=1)
