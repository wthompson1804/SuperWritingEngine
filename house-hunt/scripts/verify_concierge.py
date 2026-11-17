#!/usr/bin/env python3
"""One command that says whether the concierge page (the short version) is publishable.

Runs, in order: the data build, its tests, the published-text check on the concierge data, the pick-logic tests, the
page build and (with --with-browser) the phone walk-through. Prints one line per step and a final verdict. It does not
touch the first page; `verify_all.py` remains that page's check.
"""
from __future__ import annotations
import argparse, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def steps(with_browser: bool):
    s = [
        ("concierge data build", ["python3", "scripts/concierge_data.py"]),
        ("concierge data tests", ["python3", "scripts/test_concierge_data.py"]),
        ("published text on concierge data", ["python3", "scripts/check_published_text.py", "--data", "site/_concierge_base.json", "--out-suffix", "_u2000"]),
        ("recommender logic tests (examples exact)", ["node", "scripts/test_concierge_pick.js"]),
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
