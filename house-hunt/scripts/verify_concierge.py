#!/usr/bin/env python3
"""One command that says whether the concierge page (the short version) is publishable.

Runs, in order: the neighborhood ranking build (scripts/neighborhood_rank.py, which rewrites
site/neighborhoods_data.json), its tests, the tests of the data the page shows, the page build and (with
--with-browser) the phone walk-through. Prints one line per step and a final verdict. It does not touch the first
page; `verify_all.py` remains that page's check. (Version 7: the page reads the ranked neighborhoods; the steps of
the earlier versions, the concierge data build, its tests and the published-text check, no longer apply here.)
"""
from __future__ import annotations
import argparse, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def steps(with_browser: bool):
    s = [
        ("neighborhood ranking build", ["python3", "scripts/neighborhood_rank.py"]),
        ("neighborhood ranking tests", ["python3", "scripts/test_neighborhood_rank.py"]),
        ("page data tests (what the page shows)", ["node", "scripts/test_concierge_pick.js"]),
        ("page build", ["python3", "scripts/build_concierge.py"]),
    ]
    if with_browser:
        s.append(("phone walk-through", ["node", "scripts/concierge_walkthrough_test.js"]))
    return s

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--with-browser", action="store_true")
    a = ap.parse_args()
    failed = 0
    for name, cmd in steps(a.with_browser):
        t = time.time()
        if not (ROOT / cmd[1]).exists():
            print(f"{name:40s} FAIL   missing {cmd[1]}"); failed += 1; continue
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        ok = r.returncode == 0
        failed += 0 if ok else 1
        tail = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or [""])[-1][:110]
        print(f"{name:40s} {'PASS' if ok else 'FAIL'} {time.time()-t:6.0f}s  {tail}")
        if not ok:
            print("    " + "\n    ".join((r.stdout + r.stderr).strip().splitlines()[-12:]))
    print(f"\n{'publishable' if not failed else 'NOT publishable'}: {failed} step(s) failed")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
