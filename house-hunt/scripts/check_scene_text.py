#!/usr/bin/env python3
"""Check the written scene text against the data it cites.

Reads data/reference/scene_text_years.csv and data/reference/scene_text_neighborhoods.csv and, for every row:

1. every number in the prose (digits, decimals, dollar amounts, clock times, years, precinct numbers) must be
   "shown" by at least one item in that row's evidence_json;
2. every evidence item is looked up again in its source file (file, field, row filter, aggregation). The text
   passes when the CURRENT value still supports what was written:
     - a shown number must still be what the current value rounds to (transform),
     - a claim without a number ("no bars", "tolls not fully known") must still satisfy its `holds_if` test,
     - a cited local rule must still be in local_rules.csv with the same summary, and every number quoted
       from it must be in that summary,
     - a paraphrase of resident comments must rest on the same positive / mixed / negative counts;
3. house style: word limits, no question marks, no em or en dashes, no "not ... but", no spelled-out quantities
   (so that rule 1 cannot be dodged), no wording about race, ethnicity or religion, no dollar rents.

A value that moved but still rounds to the same words is reported as drift, not failure.

Run from the house-hunt folder:  python3 scripts/check_scene_text.py   (exit code 1 on any failure)
The functions here are also imported by scripts/build_scene_text.py, so the builder and the checker cannot disagree.
"""
import csv
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
YEARS = ROOT / "data/reference/scene_text_years.csv"
HOODS = ROOT / "data/reference/scene_text_neighborhoods.csv"

LIMITS = {"year": {"scene": (60, 90)}, "hood": {"scene": (35, 60)}}
ONE_SENTENCE = {"year": ["promise"], "hood": ["good_for_her", "watch_for"]}
ONE_OR_TWO = {"year": ["catch"], "hood": []}

NUMBER = re.compile(r"\d{1,2}:\d{2}|\d[\d,]*(?:\.\d+)?")
UNIT_PHRASES = [r"per 1,000"]                      # a unit, not a quantity
NUMBER_WORDS = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|hundred|"
    r"thousand|half|halves|third|thirds|quarter|quarters|twice|double|triple|dozen|dozens|couple)\b", re.I)
BANNED = [
    (re.compile(r"[—–]"), "em or en dash"),
    (re.compile(r"\?"), "question mark"),
    (re.compile(r"\bnot\b[^.]{0,60}\bbut\b", re.I), '"not X but Y"'),
    (re.compile(r"\$\s?\d{1,3},?\d{3}"), "a dollar amount of 1,000 or more (no rents or prices in scene text)"),
    (re.compile(r"\b(white|black|hispanic|latino|latina|latinx|asian|jewish|muslim|christian|catholic|hindu|"
                r"orthodox|ethnic|ethnicity|race|racial|religion|religious|immigrant|immigrants|diverse|diversity)\b",
                re.I), "wording about race, ethnicity or religion"),
]


@lru_cache(maxsize=None)
def table(rel):
    return pd.read_csv(ROOT / rel, low_memory=False)


def is_missing(v):
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and v.strip() == "")


def plain(v):
    """A JSON-safe python value."""
    if is_missing(v):
        return None
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float):
        return round(v, 6)
    return v


def lookup(source_file, field, row, agg=None):
    """Current value of `field` in `source_file` for the rows matching `row` ({column: value}), aggregated by `agg`."""
    t = table(source_file)
    if field not in t.columns:
        raise KeyError(f"{source_file} has no column {field}")
    m = pd.Series(True, index=t.index)
    for col, want in row.items():
        if col not in t.columns:
            raise KeyError(f"{source_file} has no column {col}")
        if isinstance(want, bool):
            m &= t[col].astype(str).str.lower().eq(str(want).lower())
        else:
            m &= t[col].astype(str).eq(str(want))
    s = t.loc[m, field]
    if agg in (None, "single"):
        if len(s) != 1:
            raise LookupError(f"{source_file} {row}: {len(s)} rows, expected 1")
        return plain(s.iloc[0])
    if agg == "any_row":            # local rules: several rows can share municipality + rule
        return [plain(x) for x in s.tolist()]
    if agg == "count":
        return int(len(s))
    if agg == "sentiment_counts":
        vc = s.astype(str).str.lower().value_counts()
        return ";".join(f"{k}={int(vc.get(k, 0))}" for k in ("positive", "mixed", "negative"))
    if not len(s):
        return None
    if agg == "all_true":
        return bool(s.astype(str).str.lower().eq("true").all())
    if agg == "mode":
        s = s.dropna().astype(str)
        if not len(s):
            return None
        vc = s.value_counts()
        top = sorted(vc[vc == vc.iloc[0]].index)
        return top[0]
    num = pd.to_numeric(s, errors="coerce").dropna()
    if not len(num):
        return None
    if agg in ("median", "max", "min"):
        return plain(float(getattr(num, agg)()))
    raise ValueError(f"unknown aggregation {agg}")


def half_up(x, step=1.0):
    return math.floor(x / step + 0.5) * step


def transform(value, how):
    """The words a value turns into. Returns a string, or None when the value is missing."""
    if is_missing(value):
        return None
    if how == "str":
        return str(value)
    if how == "time12":                               # "01:13 (+1 day)" -> "1:13 AM"
        m = re.match(r"(\d{1,2}):(\d{2})", str(value))
        h, mi = int(m.group(1)) % 24, m.group(2)
        return f"{(h % 12) or 12}:{mi} {'AM' if h < 12 else 'PM'}"
    x = float(value)
    if how == "int":
        return f"{int(half_up(x))}"
    if how == "1dp":
        return f"{half_up(x, 0.1):.1f}"
    if how == "r5":
        return f"{int(half_up(x, 5))}"
    if how == "r10":
        return f"{int(half_up(x, 10))}"
    if how == "pct":                                  # a share 0..1 -> whole percent
        return f"{int(half_up(x * 100))}"
    if how == "mi":                                   # metres -> miles, one decimal, never below 0.1
        return f"{max(0.1, half_up(x / 1609.34, 0.1)):.1f}"
    raise ValueError(f"unknown transform {how}")


def numbers_in(text):
    for u in UNIT_PHRASES:
        text = re.sub(u, " ", text)
    return [n.replace(",", "").rstrip(".") for n in NUMBER.findall(text)]


def holds(value, test):
    """test: [op, operand] with op in == != < <= > >= missing present."""
    op, want = test[0], (test[1] if len(test) > 1 else None)
    if op == "missing":
        return is_missing(value)
    if op == "present":
        return not is_missing(value)
    if is_missing(value):
        return False
    if op in ("==", "!="):
        try:
            same = abs(float(value) - float(want)) < 1e-9
        except (TypeError, ValueError):
            same = str(value).lower() == str(want).lower()
        return same if op == "==" else not same
    a, b = float(value), float(want)
    return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]


def same_value(a, b):
    if is_missing(a) and is_missing(b):
        return True
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return str(a) == str(b)


def check_evidence(ev):
    """Returns (problems, drift_notes, shown_numbers) for one evidence item."""
    problems, drift, shown = [], [], []
    for k in ("claim", "field", "value", "source_file"):
        if k not in ev:
            return [f"evidence item lacks '{k}': {ev}"], [], []
    how = ev.get("transform")
    tag = f"{ev['source_file']}:{ev['field']} {ev.get('row', {})}"
    if how == "convention":                           # a fixed wording for a search radius; only the column must exist
        if ev["field"] not in table(ev["source_file"]).columns:
            problems.append(f"{tag}: column is gone")
        return problems, drift, numbers_in(" ".join(ev.get("shown", [])))
    try:
        now = lookup(ev["source_file"], ev["field"], ev.get("row", {}), ev.get("agg"))
    except Exception as e:                            # noqa: BLE001  (report, do not crash)
        return [f"{tag}: {e}"], [], numbers_in(" ".join(ev.get("shown", [])))
    if how == "in_text":                              # a local rule summary and the numbers quoted from it
        if ev["value"] not in now:
            problems.append(f"{tag}: the rule summary cited is no longer in the file")
        have = numbers_in(str(ev["value"]))
        for s in ev.get("shown", []):
            for n in numbers_in(s):
                if n not in have:
                    problems.append(f"{tag}: '{n}' is not in the rule summary")
        return problems, drift, numbers_in(" ".join(ev.get("shown", [])))
    if ev.get("shown"):
        want = transform(now, how)
        if want is None:
            problems.append(f"{tag}: now missing, text shows {ev['shown']}")
        elif want not in ev["shown"]:
            problems.append(f"{tag}: text shows {ev['shown']}, current value {now} reads '{want}'")
        shown = numbers_in(" ".join(ev["shown"]))
    if ev.get("holds_if"):
        if not holds(now, ev["holds_if"]):
            problems.append(f"{tag}: current value {now} no longer satisfies {ev['holds_if']} ({ev['claim'][:70]})")
    if not ev.get("shown") and not ev.get("holds_if") and not same_value(now, ev["value"]):
        problems.append(f"{tag}: was {ev['value']}, now {now}")
    if not problems and not same_value(now, ev["value"]):
        drift.append(f"{tag}: {ev['value']} -> {now} (text still holds)")
    return problems, drift, shown


def sentences(text):
    return [s for s in re.split(r"(?<=[.!])\s+", text.strip()) if s]


def check_style(kind, col, text):
    out = []
    for rx, what in BANNED:
        m = rx.search(text)
        if m:
            out.append(f"{col}: {what}: '{m.group(0)}'")
    m = NUMBER_WORDS.search(text)
    if m:
        out.append(f"{col}: spelled-out quantity '{m.group(0)}' (write digits and cite them)")
    words = len(text.split())
    if col in LIMITS[kind]:
        lo, hi = LIMITS[kind][col]
        if not lo <= words <= hi:
            out.append(f"{col}: {words} words, wanted {lo} to {hi}")
    n = len(sentences(text))
    if col in ONE_SENTENCE[kind] and n != 1:
        out.append(f"{col}: {n} sentences, wanted 1")
    if col in ONE_OR_TWO[kind] and n not in (1, 2):
        out.append(f"{col}: {n} sentences, wanted 1 or 2")
    return out


def check_row(kind, key, texts, evidence):
    """texts: {column: prose}. Returns (problems, drift)."""
    problems, drift, allowed = [], [], set()
    for ev in evidence:
        p, d, shown = check_evidence(ev)
        problems += p
        drift += d
        allowed |= set(shown)
    for col, text in texts.items():
        if not text.strip():
            problems.append(f"{col}: empty")
            continue
        problems += check_style(kind, col, text)
        for n in numbers_in(text):
            if n not in allowed:
                problems.append(f"{col}: number '{n}' has no evidence item")
    return problems, drift


def main():
    fails = drifts = rows = 0
    for kind, path, key, cols in (("year", YEARS, "year_label", ["scene", "promise", "catch"]),
                                  ("hood", HOODS, "hood_id", ["scene", "good_for_her", "watch_for"])):
        if not path.exists():
            print(f"MISSING {path}")
            fails += 1
            continue
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows += 1
                try:
                    evidence = json.loads(r["evidence_json"])
                except json.JSONDecodeError as e:
                    print(f"FAIL {r[key]}: evidence_json does not parse ({e})")
                    fails += 1
                    continue
                problems, drift = check_row(kind, r[key], {c: r[c] for c in cols}, evidence)
                for p in problems:
                    print(f"FAIL {r[key]}: {p}")
                for d in drift:
                    print(f"drift {r[key]}: {d}")
                fails += bool(problems)
                drifts += bool(drift)
    print(f"{rows} rows checked, {fails} failing, {drifts} with drift only")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
