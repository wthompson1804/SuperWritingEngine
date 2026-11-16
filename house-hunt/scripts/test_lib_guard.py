"""Tests for the refused-host guard in lib.py (cached_get / get_json). A temp raw folder and a fake `requests.request`:
no real network, no project file touched.

    python3 scripts/test_lib_guard.py        (or: python3 -m pytest scripts/test_lib_guard.py)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402


class FakeResponse:
    status_code = 200
    content = b'{"ok": true}'


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "raw").mkdir()
        self.calls = []

        def fake_request(method, url, **kw):
            self.calls.append(url)
            return FakeResponse()

        env = {k: v for k, v in os.environ.items() if k != "HOUSE_HUNT_ALLOW_HOST"}
        for p in (mock.patch.object(lib, "ROOT", root), mock.patch.object(lib, "RAW", root / "raw"),
                  mock.patch.object(lib.requests, "request", fake_request), mock.patch.object(lib, "DEFAULT_DELAY", 0.0),
                  mock.patch.object(lib, "HOST_DELAY", {}), mock.patch.dict(os.environ, env, clear=True)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.tmp.cleanup)

    def kill(self, obj):
        (lib.RAW / "_host_kill_shared.json").write_text(obj if isinstance(obj, str) else json.dumps(obj))

    def test_unrelated_host_unaffected_and_signature_kept(self):
        self.kill({"trulia.com": {"reason": "403/CAPTCHA"}})
        content, meta = lib.cached_get("https://api.example.org/a", "t")
        self.assertEqual(content, b'{"ok": true}')
        self.assertEqual((meta["status"], meta["source"], meta["url"]), (200, "t", "https://api.example.org/a"))
        self.assertEqual(lib.get_json("https://api.example.org/b", "t")[0], {"ok": True})
        self.assertEqual(len(self.calls), 2)

    def test_killed_host_raises_before_any_request(self):
        self.kill({"trulia.com": {"reason": "403/CAPTCHA, tested 2026-11-16"}})
        for url in ("https://www.trulia.com/building/x", "https://trulia.com/y", "https://m.trulia.com/z"):
            with self.assertRaises(lib.HostRefused) as cm:
                lib.cached_get(url, "t", ext="html")
            self.assertIn("trulia.com", str(cm.exception))
            self.assertIn("403/CAPTCHA", str(cm.exception))
        with self.assertRaises(lib.HostRefused):
            lib.get_json("https://www.trulia.com/api", "t")
        self.assertIsInstance(cm.exception, RuntimeError)      # callers that catch RuntimeError keep working
        self.assertEqual(self.calls, [])

    def test_www_entry_covers_bare_host_but_not_lookalikes(self):
        self.kill({"www.example-apts.com": {"status": "HTTP 403"}})
        with self.assertRaises(lib.HostRefused):
            lib.cached_get("https://example-apts.com/", "t", ext="html")
        lib.cached_get("https://notexample-apts.com/", "t", ext="html")
        lib.cached_get("https://example-apts.com.evil.org/", "t", ext="html")
        self.assertEqual(len(self.calls), 2)

    def test_cache_hit_still_served_for_a_killed_host(self):
        url = "https://www.trulia.com/building/cached"
        lib.cached_get(url, "t", ext="html")                   # fetched before the refusal
        self.kill({"trulia.com": {"reason": "403/CAPTCHA"}})
        content, meta = lib.cached_get(url, "t", ext="html")
        self.assertEqual((content, meta["status"]), (b'{"ok": true}', 200))
        self.assertEqual(len(self.calls), 1)
        with self.assertRaises(lib.HostRefused):               # a forced refresh is a network request
            lib.cached_get(url, "t", ext="html", refresh=True)
        self.assertEqual(len(self.calls), 1)

    def test_off_limits_always_even_without_a_kill_file(self):
        for host in ("www.zillow.com", "streeteasy.com", "newyork.craigslist.org", "www.reddit.com", "patch.com", "qns.com"):
            with self.assertRaises(lib.HostRefused) as cm:
                lib.cached_get(f"https://{host}/x", "t", ext="html")
            self.assertIn("off limits", str(cm.exception))
        lib.cached_get("https://files.zillowstatic.com/research/zori.csv", "t", ext="csv")     # a different domain
        self.assertEqual(len(self.calls), 1)

    def test_override_is_for_one_host_only(self):
        self.kill({"trulia.com": {"reason": "403"}, "www.other.com": {"reason": "403"}})
        with mock.patch.dict(os.environ, {"HOUSE_HUNT_ALLOW_HOST": "trulia.com"}):
            lib.cached_get("https://www.trulia.com/a", "t", ext="html")
            with self.assertRaises(lib.HostRefused):
                lib.cached_get("https://www.other.com/a", "t", ext="html")
            with self.assertRaises(lib.HostRefused):
                lib.cached_get("https://www.zillow.com/a", "t", ext="html")
        with mock.patch.dict(os.environ, {"HOUSE_HUNT_ALLOW_HOST": "trulia.com,www.other.com"}):   # a list is not a host
            with self.assertRaises(lib.HostRefused):
                lib.cached_get("https://www.other.com/b", "t", ext="html")
        self.assertEqual(self.calls, ["https://www.trulia.com/a"])

    def test_missing_or_malformed_kill_file_blocks_nothing(self):
        lib.cached_get("https://www.trulia.com/1", "t", ext="html")              # no file
        for i, bad in enumerate(("{not json", "[1, 2]", '"text"', "", json.dumps({"trulia.org": "a string, not a record", "": {}, "x.com": None}))):
            self.kill(bad)
            lib.cached_get(f"https://www.trulia.com/m{i}", "t", ext="html")
        self.assertEqual(len(self.calls), 6)
        with self.assertRaises(lib.HostRefused):                                   # odd records still name their host
            lib.cached_get("https://x.com/", "t", ext="html")


if __name__ == "__main__":
    unittest.main(verbosity=1)
