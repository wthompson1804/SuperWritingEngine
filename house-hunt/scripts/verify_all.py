"""One read-only command: is the project in a publishable state?

    python3 scripts/verify_all.py                 everything except the browser walk-through
    python3 scripts/verify_all.py --quick         skip the slow suites (see SLOW) and the walk-through
    python3 scripts/verify_all.py --with-browser  also run scripts/site_walkthrough_test.js at W=390 (minutes; needs
                                                  node, Playwright and Chromium)
    python3 scripts/verify_all.py --tail 15       lines of each step's output to print (default 6)

It changes nothing in the project: no data file, no site file, no cache, no network. It runs, in this order,
  1. every scripts/test_*.py, each as `python3 <file>`, and `test_rules.py --data`;
  2. scripts/check_registry.py, with its one write (data/reference/field_registry.csv) switched off: the script is
     run through a wrapper that makes DataFrame.to_csv do nothing, so the checks run and the table is left alone;
  3. scripts/check_scene_text.py;
  4. scripts/page_data_extras.py --dry-run --strict (with --dry-run the script stops before its only write);
  5. its own checks across the built files (the helpers below);
  6. with --with-browser, the page walk-through, served from a throwaway local server, screenshots to a temp folder.
Wording rules ("all-in", "net-effective", "cap", ...) are left to check_scene_text.py and test_realtor_lines.py.

The exit code is 0 only when every step passes. A WARN (a built page older than its inputs) and a SKIP are printed
in the final table and do not change the exit code. Standard library and pandas only.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

FIRST_TESTS = ["test_parsers.py", "test_rules.py", "test_page_data_extras.py", "test_realtor_lines.py", "test_shortlist_tools.py"]
SLOW = {"test_page_data_extras.py", "test_rules.py --data", "check_registry.py"}       # skipped by --quick
KIND_FIELDS = ("kind", "listing_kind", "unit_kind", "row_kind", "status", "gate_status")
NOT_APARTMENT = re.compile(r"not[_ ]an[_ ]apartment|floor[_ -]?plan|building[_ ]offer|shared[_ ]suite", re.I)
KEY_IN_URL = re.compile(rb"(?i)key=([^&\s\"',<>|\\]{20,})")
SHOWABLE = ("ok", "asterisk", "disclose")


# ---------------------------------------------------------------- consistency helpers (pure; tested in test_verify_all.py)
def compare_ids(name_a: str, ids_a, name_b: str, ids_b, show: int = 5) -> list[str]:
    """Problems when the two id collections are not the same set, or one of them repeats an id."""
    a, b = [str(x) for x in ids_a], [str(x) for x in ids_b]
    out = []
    for name, xs in ((name_a, a), (name_b, b)):
        dup = sorted({x for x in xs if xs.count(x) > 1}) if len(set(xs)) != len(xs) else []
        if dup:
            out.append(f"{len(dup)} id(s) repeated in {name}: {', '.join(dup[:show])}")
    sa, sb = set(a), set(b)
    for only, here, there in ((sorted(sa - sb), name_a, name_b), (sorted(sb - sa), name_b, name_a)):
        if only:
            out.append(f"{len(only)} id(s) in {here} but not in {there}: {', '.join(only[:show])}" + (" ..." if len(only) > show else ""))
    return out


def verdict_gaps(shown_ids, verdict_rows) -> list[tuple[str, str]]:
    """(id, why) for each shown id with no showable verdict. verdict_rows: dicts with listing_id and verdict. A unit
    with several rows takes the strongest (remove beats the rest). Does not test whether the verdict is current:
    scripts/verdicts.py does that, and main() uses it when it can be imported."""
    order = {"remove": 0, "asterisk": 1, "disclose": 2, "ok": 3}
    best: dict[str, str] = {}
    for r in verdict_rows:
        lid, v = str(r.get("listing_id", "")), str(r.get("verdict", "")).strip()
        if lid and (lid not in best or order.get(v, 9) < order.get(best[lid], 9)):
            best[lid] = v
    out = []
    for lid in map(str, shown_ids):
        if lid not in best:
            out.append((lid, "no reviewed verdict"))
        elif best[lid] not in SHOWABLE:
            out.append((lid, f"verdict is '{best[lid]}'"))
    return out


def hoods_without_scene(neighborhoods) -> list[str]:
    """Ids of page neighborhoods that show apartments and have no scene text (prose.scene)."""
    out = []
    for n in neighborhoods:
        if not n.get("unit_ids"):
            continue
        prose = n.get("prose")
        scene = prose.get("scene") if isinstance(prose, dict) else None
        if not (isinstance(scene, str) and scene.strip()):
            out.append(str(n.get("id")))
    return out


def non_apartment_rows(records, fields=KIND_FIELDS) -> tuple[list[str], list[tuple[str, str, str]]]:
    """(fields present on at least one record, [(id, field, value)] for rows whose kind says it is not an apartment)."""
    present, bad = [], []
    for r in records:
        for f in fields:
            if f in r:
                if f not in present:
                    present.append(f)
                v = r[f]
                if isinstance(v, str) and NOT_APARTMENT.search(v):
                    bad.append((str(r.get("id", r.get("listing_id", "?"))), f, v))
    return present, bad


def key_leaks(blob: bytes) -> list[int]:
    """Line numbers (from 1) where `key=` is followed by 20 or more characters. Values are never returned.
    A value that lib.redact() already replaced is 8 characters long and does not match."""
    return sorted({blob.count(b"\n", 0, m.start()) + 1 for m in KEY_IN_URL.finditer(blob)})


def stale_outputs(outputs: dict, inputs: dict) -> tuple[list[str], list[str]]:
    """outputs / inputs: name -> mtime (None when the file is missing). Returns (missing outputs, stale messages)."""
    missing = [n for n, t in outputs.items() if t is None]
    stale = []
    for n, t in outputs.items():
        if t is None:
            continue
        newer = [i for i, ti in inputs.items() if ti is not None and ti > t]
        if newer:
            stale.append(f"{n} is older than {', '.join(newer)}")
    return missing, stale


# ---------------------------------------------------------------- running things
class Report:
    def __init__(self, tail: int):
        self.rows, self.tail = [], tail

    def add(self, name: str, status: str, secs: float = 0.0, note: str = "", output: str = ""):
        self.rows.append((name, status, secs, note))
        print(f"[{status}] {name}" + (f"  ({secs:.1f}s)" if secs else "") + (f"  {note}" if note else ""), flush=True)
        lines = [l for l in output.rstrip().splitlines() if l.strip()]
        for l in lines[-self.tail:] if self.tail else []:
            print("      " + l[:220])

    def failed(self) -> bool:
        return any(s == "FAIL" for _, s, _, _ in self.rows)

    def table(self):
        w = max(len(n) for n, *_ in self.rows)
        print("\n" + f"{'step':<{w}}  result  secs  note")
        print("-" * (w + 22))
        for n, s, t, note in self.rows:
            print(f"{n:<{w}}  {s:<6}  {t:>4.0f}  {note[:150]}")
        c = {k: sum(1 for _, s, _, _ in self.rows if s == k) for k in ("PASS", "FAIL", "WARN", "SKIP")}
        print(f"\n{c['PASS']} passed, {c['FAIL']} failed, {c['WARN']} warning(s), {c['SKIP']} skipped: "
              + ("NOT publishable" if c["FAIL"] else "publishable" + (" (see warnings)" if c["WARN"] else "")
                 + (" as far as checked: rerun without --quick before publishing" if any(n == "--quick" for *_, n in self.rows) else "")))


def child_env(**extra) -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **extra)
    env.pop("HOUSE_HUNT_ALLOW_HOST", None)
    return env


def run_step(rep: Report, name: str, cmd: list[str], timeout: int = 1800, env: dict | None = None):
    t = time.time()
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env or child_env())
        out, ok, note = (r.stdout or "") + (r.stderr or ""), r.returncode == 0, "" if r.returncode == 0 else f"exit code {r.returncode}"
    except subprocess.TimeoutExpired as e:
        out, ok, note = str(e.stdout or "") + str(e.stderr or ""), False, f"timed out after {timeout}s"
    except OSError as e:
        out, ok, note = "", False, f"could not start: {e}"
    rep.add(name, "PASS" if ok else "FAIL", time.time() - t, note, out)


REGISTRY_WRAPPER = ("import sys, runpy, pandas as pd; sys.path.insert(0, 'scripts'); "
                    "pd.DataFrame.to_csv = lambda self, *a, **k: None; "
                    "sys.argv = ['scripts/check_registry.py']; runpy.run_path('scripts/check_registry.py', run_name='__main__')")


def test_files() -> list[str]:
    found = sorted(p.name for p in SCRIPTS.glob("test_*.py"))
    return [f for f in FIRST_TESTS if f in found] + [f for f in found if f not in FIRST_TESTS]


# ---------------------------------------------------------------- the built-file checks
def mtime(p: Path):
    try:
        return p.stat().st_mtime
    except OSError:
        return None


def read_csv_rows(p: Path) -> list[dict]:
    csv.field_size_limit(1 << 30)
    with open(p, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def artefact_checks(rep: Report, root: Path = ROOT):
    def check(name, fn):
        t = time.time()
        try:
            status, note, detail = fn()
        except Exception as e:  # a missing or unreadable file is a failure of that check, not of the command
            status, note, detail = "FAIL", f"{type(e).__name__}: {str(e)[:150]}", ""
        rep.add(name, status, time.time() - t, note, detail)

    page = {}
    try:
        page = json.loads((root / "site" / "data.json").read_text(encoding="utf-8"))
    except Exception as e:
        rep.add("site/data.json readable", "FAIL", 0, f"{type(e).__name__}: {str(e)[:150]}")
    units, buildings = page.get("units") or [], page.get("buildings") or []
    unit_ids, building_ids = [u.get("id") for u in units], [b.get("id") for b in buildings]
    shown: list[dict] = []

    def ranked_vs_page():
        import pandas as pd
        R = pd.read_csv(root / "data" / "ranked_units.csv", dtype=str, keep_default_na=False, low_memory=False)
        shown.extend(R[R["shown"] == "True"].to_dict("records"))
        bad = compare_ids("ranked_units.csv (shown)", [r["listing_id"] for r in shown], "site/data.json units", unit_ids)
        return ("FAIL" if bad else "PASS"), ("; ".join(b.split(":")[0] for b in bad) if bad else f"{len(unit_ids)} apartments"), "\n".join(bad)

    def verdicts_current():
        if not shown:
            return "FAIL", "no shown rows were read from data/ranked_units.csv", ""
        ids = [r["listing_id"] for r in shown]
        try:
            if root != ROOT:
                raise ImportError("not the project folder")
            sys.path.insert(0, str(SCRIPTS))
            sys.dont_write_bytecode = True
            import verdicts as V  # read-only use: unreviewed() only reads
            gaps, how = V.unreviewed(), "scripts/verdicts.py (verdict present, showable, written against the evidence as it stands)"
        except Exception as e:
            gaps = verdict_gaps(ids, read_csv_rows(root / "data" / "evidence" / "review_verdicts.csv"))
            how = f"plain table check, currency NOT tested (verdicts.py not usable: {type(e).__name__})"
        lines = [f"{lid}: {why}" for lid, why in gaps[:8]]
        return ("FAIL" if gaps else "PASS"), (f"{len(gaps)} of {len(ids)} shown units without a current verdict; {how}" if gaps else f"{len(ids)} units; {how}"), "\n".join(lines)

    def table_ids(fname, col, want, what):
        def fn():
            rows = read_csv_rows(root / "data" / "reference" / fname)
            bad = compare_ids(f"data/reference/{fname}", [r.get(col, "") for r in rows], f"site/data.json {what}", want)
            return ("FAIL" if bad else "PASS"), ("; ".join(b.split(":")[0] for b in bad) if bad else f"{len(rows)} rows"), "\n".join(bad)
        return fn

    def scene_text():
        hoods = page.get("neighborhoods") or []
        on_page = [n for n in hoods if n.get("unit_ids")]
        bad = hoods_without_scene(hoods)
        return ("FAIL" if bad or not on_page else "PASS"), (f"{len(bad)} of {len(on_page)} neighborhoods with apartments have no scene text" if bad else f"{len(on_page)} neighborhoods with apartments"), ", ".join(bad[:12])

    def no_floor_plans():
        present, bad = non_apartment_rows(units)
        p2, b2 = non_apartment_rows(shown)
        present, bad = present + [f"ranked_units.{f}" for f in p2], bad + b2
        kind_fields = [f for f in present if "kind" in f]
        if bad:
            return "FAIL", f"{len(bad)} row(s) on the page are not apartments", "\n".join(f"{i}: {f} = {v}" for i, f, v in bad[:8])
        if not kind_fields:
            return "SKIP", "no kind / listing_kind field in the page data or ranked_units.csv yet" + (f" (looked at {', '.join(present)}: clean)" if present else ""), ""
        return "PASS", f"fields checked: {', '.join(present)}", ""

    def keys():
        files = [root / "site" / "data.json"] + sorted((root / "data").rglob("*.csv"))
        hits = []
        for p in files:
            try:
                for ln in key_leaks(p.read_bytes()):
                    hits.append(f"{p.relative_to(root)}:{ln}")
            except OSError:
                continue
        return ("FAIL" if hits else "PASS"), (f"{len(hits)} line(s) with key= and 20+ characters (values not printed)" if hits else f"{len(files)} files"), "\n".join(hits[:20])

    def built_pages():
        s = root / "site"
        outputs = {"site/dist/index.html": mtime(s / "dist" / "index.html"), "site/dist/artifact.html": mtime(s / "dist" / "artifact.html")}
        inputs = {"site/data.json": mtime(s / "data.json"), "site/index.html": mtime(s / "index.html")}
        missing, stale = stale_outputs(outputs, inputs)
        if missing:
            return "FAIL", "missing: " + ", ".join(missing), ""
        if stale:
            return "WARN", "stale: " + "; ".join(stale) + " (rebuild: build_site.py, then build_artifact.py)", ""
        return "PASS", "both newer than site/data.json and site/index.html", ""

    check("shown ids: ranked_units.csv = site/data.json", ranked_vs_page)
    check("every shown unit has a current verdict", verdicts_current)
    check("realtor_lines.csv ids = page apartments", table_ids("realtor_lines.csv", "listing_id", unit_ids, "units"))
    check("building_about.csv ids = page buildings", table_ids("building_about.csv", "building_id", building_ids, "buildings"))
    check("every page neighborhood has scene text", scene_text)
    check("no floor plan / not_an_apartment row on the page", no_floor_plans)
    check("no key=<20+ chars> in site/data.json, data/**/*.csv", keys)
    check("site/dist pages exist and are fresh", built_pages)


def walkthrough(rep: Report):
    name = "page walk-through, W=390 (browser)"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=ROOT / "site",
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.0)
        with tempfile.TemporaryDirectory(prefix="verify_all_screens_") as out:      # screenshots stay out of site/screens
            run_step(rep, name, ["node", "scripts/site_walkthrough_test.js"], timeout=3600,
                     env=child_env(BASE=f"http://127.0.0.1:{port}", OUT=out, W="390"))
    finally:
        server.terminate()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Read-only check that the project is in a publishable state.")
    ap.add_argument("--quick", action="store_true", help="skip the slow suites: " + ", ".join(sorted(SLOW)))
    ap.add_argument("--with-browser", action="store_true", help="also run the page walk-through at W=390 (minutes)")
    ap.add_argument("--tail", type=int, default=6, help="lines of each step's output to print (default 6)")
    a = ap.parse_args(argv)
    rep = Report(a.tail)
    py = sys.executable or "python3"

    def step(name, cmd, **kw):
        if a.quick and name in SLOW:
            rep.add(name, "SKIP", note="--quick")
        else:
            run_step(rep, name, cmd, **kw)

    for f in test_files():
        step(f, [py, f"scripts/{f}"])
        if f == "test_rules.py":
            step("test_rules.py --data", [py, "scripts/test_rules.py", "--data"])
    step("check_registry.py", [py, "-c", REGISTRY_WRAPPER])
    step("check_scene_text.py", [py, "scripts/check_scene_text.py"])
    step("page_data_extras.py --dry-run --strict", [py, "scripts/page_data_extras.py", "--dry-run", "--strict"])
    # the text as published in site/data.json: equals its source, plain-language rules, numbers, claims, contradictions.
    # --text-only until the pipeline's own strings pass too (a British spelling in a rule summary, 2026-11-16).
    step("check_published_text.py --text-only", [py, "scripts/check_published_text.py", "--text-only"])
    artefact_checks(rep)
    if a.with_browser and not a.quick:
        walkthrough(rep)
    else:
        rep.add("page walk-through, W=390 (browser)", "SKIP", note="run with --with-browser (needs a browser, takes minutes)")
    rep.table()
    return 1 if rep.failed() else 0


if __name__ == "__main__":
    sys.exit(main())
