#!/usr/bin/env python3
"""Check the written scene text against the data it cites.

Reads data/reference/scene_text_years.csv (the six experiences; the key column is still `year_label`) and
data/reference/scene_text_neighborhoods.csv and, for every row and every prose column
(years: display_label, tagline, subhead, scene, promise, catch, host_intro, host_walkthrough;
 neighborhoods: scene, good_for_her, watch_for, host_intro):

1. every number in the prose (digits, decimals, dollar amounts, clock times, years) must be "shown" by at least one
   item in that row's evidence_json;
2. every evidence item is looked up again in its source (file, field, row filter, aggregation). Besides the CSVs there
   are virtual tables: data/enriched/*.json (complete round-trip tolls per building) and
   site/data.json#years|neighborhoods|units (the page's own unit-weighted figures). The text passes when the CURRENT
   value still supports what was written:
     - a shown number must still be what the current value rounds to (transform),
     - a claim without a number ("no bars", "most homes are houses") must still satisfy its `holds_if` test,
     - a cited local rule must still be in local_rules.csv / local_rules_round2.csv with the same summary, and every
       number quoted from it must be in that summary,
     - a paraphrase of resident comments must rest on the same positive / mixed / negative counts;
3. house style: word limits (and 3 paragraphs of 40 to 60 words for host_walkthrough), no question marks, no em or en
   dashes, no "not ... but", no spelled-out quantities (so that rule 1 cannot be dodged), no wording about race,
   ethnicity or religion, no listing-ad hype words, no dollar amounts of 1,000 or more outside the host fields;
4. no crime wording in any open field (crime, violent, burglar, theft, "per 1,000", "safer than", safe, police).
   Two fixed wordings are allowed, each only with a test in the evidence: "one of the safest spots on the whole list"
   (neighborhood in the lowest fifth by violent rate among those on the page; one field only) and "the safety limit
   we set" (watch_for only; violent rate of 8.0 or more, where Jamaica's 9.8 is the limit);
5. across rows, the host voice must not read like a form letter: at most 3 host_intro texts may open with the same 3
   words, and no run of 6 words may appear in more than a tenth of them (the fixed toll wording is exempt).

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

TOLLS = "data/enriched/*.json"                     # virtual table: one row per building, see _toll_table()
PAGE = "site/data.json"                            # virtual tables "site/data.json#years|neighborhoods|units"

LIMITS = {"year": {"scene": (60, 90), "host_intro": (110, 160), "tagline": (4, 14), "subhead": (6, 22)},
          "hood": {"scene": (35, 68), "host_intro": (60, 90)}}
PARAGRAPHS = {"year": {"host_walkthrough": (3, 40, 60)}, "hood": {}}      # column: (paragraphs, min words, max words) each
ONE_SENTENCE = {"year": ["promise", "tagline", "subhead"], "hood": ["good_for_her", "watch_for"]}
ONE_OR_TWO = {"year": ["catch"], "hood": []}
HOST_COLS = {"host_intro", "host_walkthrough", "tagline", "display_label", "subhead"}   # the host voice may state all-in dollars
COLUMNS = {"year": ["display_label", "tagline", "subhead", "scene", "promise", "catch", "host_intro", "host_walkthrough"],
           "hood": ["scene", "good_for_her", "watch_for", "host_intro"]}
VOICE_PHRASE = re.compile(r"review sites|people who live (here|in )|residents (also |here )?(say|like|praise)", re.I)

NUMBER = re.compile(r"\d{1,2}:\d{2}|\d[\d,]*(?:\.\d+)?")
UNIT_PHRASES = [r"per 1,000"]                      # a unit, not a quantity
NUMBER_WORDS = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|hundred|"
    r"thousand|half|halves|third|thirds|quarter|quarters|twice|double|triple|dozen|dozens|couple)\b", re.I)
BANNED = [
    (re.compile(r"[—–]"), "em or en dash"),
    (re.compile(r"\?"), "question mark"),
    (re.compile(r"\bnot\b[^.]{0,60}\bbut\b", re.I), '"not X but Y"'),
    (re.compile(r"\b(white|black|hispanic|latino|latina|latinx|asian|jewish|muslim|christian|catholic|hindu|"
                r"orthodox|ethnic|ethnicity|race|racial|religion|religious|immigrant|immigrants|diverse|diversity)\b",
                re.I), "wording about race, ethnicity or religion"),
    (re.compile(r"\b(stunning|nestled|boasts?|vibrant|bustling|oasis|hidden gem|gem|luxur\w+|breathtaking|dream home|"
                r"must-see|something for everyone|best of both worlds|up-and-coming|coveted|sought-after)\b", re.I),
     "listing-ad hype word"),
]
# The owner's rule (2026-11-16): everything shown already passed the safety rule, so the open prose is about living
# there, not about crime. No rates, no "per 1,000", no comparison with Jamaica's line, no "low crime" selling point.
CRIME = re.compile(r"\bcrimes?\b|\bviolent\b|burglar\w*|\bthefts?\b|\bstolen\b|break-ins?|carjack\w*|per 1,000|"
                   r"safer than|\bunsafe\b|\bsafe\b|\bsafely\b|\bpolice\b|\brobber\w*", re.I)
# Two wordings are allowed, each tied to a test the checker re-runs:
SAFEST = "one of the safest spots on the whole list"      # only where the neighborhood is in the lowest fifth by violent
SAFEST_FIELD, SAFEST_MAX = "violent_pctile", 0.2          # rate among the neighborhoods shown on the page; one clause
AT_LIMIT = "safety limit we set"                          # watch_for only, only where the violent rate is right at the
AT_LIMIT_FIELD, AT_LIMIT_MIN = "violent", 8.0             # limit (Jamaica's rate is the limit, 9.8)
DOLLARS = (re.compile(r"\$\s?\d{1,3},?\d{3}"), "a dollar amount of 1,000 or more (no rents or prices in scene text)")


@lru_cache(maxsize=None)
def table(rel):
    if rel == TOLLS:
        return _toll_table()
    if rel.startswith(PAGE + "#"):
        return _page_table(rel.split("#", 1)[1])
    return pd.read_csv(ROOT / rel, low_memory=False)


def _toll_table():
    """One row per building: the complete round-trip toll from data/enriched/<key>.json (drive.toll_round_trip_ezpass),
    joined to its building and neighborhood through building_crosswalk.csv and master_buildings.csv (both read-only)."""
    rows = []
    for f in sorted((ROOT / "data/enriched").glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        t = (j.get("drive") or {}).get("toll_round_trip_ezpass") or {}
        rows.append({"addr_key": j.get("addr_key"), "toll_round_trip_ezpass": t.get("value"),
                     "complete": bool(t.get("complete")), "enriched_file": f.name})
    e = pd.DataFrame(rows)
    cw = pd.read_csv(ROOT / "data/reference/building_crosswalk.csv", usecols=["addr_key", "building_id"])
    mb = pd.read_csv(ROOT / "data/master_buildings.csv", usecols=["building_id", "hood_id"], low_memory=False)
    return e.merge(cw, on="addr_key").merge(mb, on="building_id")


def year_key(label):
    """The internal key stays '... Year' whatever the page calls it."""
    return re.sub(r"\bExperience$", "Year", str(label).strip())


@lru_cache(maxsize=None)
def _page():
    return json.loads((ROOT / PAGE).read_text(encoding="utf-8"))


def _page_table(part):
    """Flat views of site/data.json, so the prose can quote the same unit-weighted figures the page's tiles show."""
    d = _page()
    labels = {y["id"]: year_key(y["label"]) for y in d["years"]}
    if part == "years":
        rows = []
        for y in d["years"]:
            r = {"year_label": labels[y["id"]], "id": y["id"], **(y.get("medians") or {})}
            for k in ("all_in", "drive_min"):
                lo, hi = (y.get(k + "_range") or [None, None])[:2]
                r[k + "_lo"], r[k + "_hi"] = lo, hi
            r["neighborhoods"] = (y.get("counts") or {}).get("neighborhoods")
            r["shown"] = (y.get("counts") or {}).get("shown")
            near = sorted((h for h in d["neighborhoods"] if h.get("year") == y["id"] and h.get("drive_min") is not None
                           and (h.get("counts") or {}).get("shown")), key=lambda h: h["drive_min"])
            r["nearest_name"], r["nearest_drive_min"] = (near[0]["name"], near[0]["drive_min"]) if near else (None, None)
            rows.append(r)
        return pd.DataFrame(rows)
    if part == "neighborhoods":
        rows = []
        for h in d["neighborhoods"]:
            lo, hi = (h.get("all_in_range") or [None, None])[:2]
            rows.append({"hood_id": h["id"], "all_in_lo": lo, "all_in_hi": hi, "sqft_median": h.get("sqft_median"),
                         "shown": (h.get("counts") or {}).get("shown"),
                         "violent": (h.get("safety") or {}).get("violent_per_1000")})
        t = pd.DataFrame(rows)
        # share of the page's neighborhoods (those with a rate) whose violent rate is at or below this one: 0.2 = lowest fifth
        t["violent_pctile"] = t["violent"].rank(pct=True, method="max")
        return t.drop(columns=["violent"])
    if part == "units":
        toll = table(TOLLS).drop_duplicates("building_id").set_index("building_id")["toll_round_trip_ezpass"]
        rows = []
        for u in d["units"]:
            mo, am, pk = u.get("moments") or {}, u.get("amenities") or {}, u.get("parking") or {}
            kind = str(pk.get("type") or "").lower()
            rows.append({
                "listing_id": u["id"], "hood_id": u.get("hood_id"), "year_label": labels.get(u.get("year")),
                "all_in": u.get("all_in"), "sqft": u.get("sqft"),
                "toll_rt": toll.get(u.get("building_id")),
                "drive_min": (mo.get("sun") or {}).get("drive_min"),
                "transit_min": (mo.get("sun") or {}).get("transit_min"),
                "dog_park_m": (mo.get("wake") or {}).get("dog_park_m"),
                "park_walk_min": (mo.get("wake") or {}).get("park_walk_min"),
                "supermarket_m": (mo.get("work") or {}).get("supermarket_m"),
                "cafes_800m": (mo.get("after") or {}).get("cafes_800m"),
                "bars_800m": (mo.get("after") or {}).get("bars_800m"),
                "restaurants_800m": (mo.get("after") or {}).get("restaurants_800m"),
                "restaurants_1600m": (mo.get("sat") or {}).get("restaurants_1600m"),
                "bars_1600m": (mo.get("sat") or {}).get("bars_1600m"),
                "garage_or_covered": float(kind.startswith(("garage", "covered"))),
                "parking_published": float(bool(kind)),
                "pool": float(bool(am.get("pool"))), "doorman": float(bool(am.get("doorman"))),
                "gym": float(bool(am.get("gym"))), "in_unit_laundry": float(am.get("in_unit_laundry") == "yes"),
            })
        return pd.DataFrame(rows)
    raise KeyError(f"no page table '{part}'")


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
    if agg in ("median", "max", "min", "mean"):
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
    if how == "usd50":                                # dollars to the nearest 50, with a comma: 2707 -> "2,700"
        return f"{int(half_up(x, 50)):,}"
    if how == "pct":                                  # a share 0..1 -> whole percent
        return f"{int(half_up(x * 100))}"
    if how == "mi0":                                  # metres -> whole miles (for far-away things)
        return f"{int(half_up(x / 1609.34))}"
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


PLACE_NAMES = ["White Plains"]                    # place names that would trip the wording test


def check_style(kind, col, text):
    out = []
    bare = text
    for name in PLACE_NAMES:
        bare = bare.replace(name, "")
    for rx, what in BANNED + ([] if col in HOST_COLS else [DOLLARS]):
        m = rx.search(bare)
        if m:
            out.append(f"{col}: {what}: '{m.group(0)}'")
    open_text = bare.replace(SAFEST, "").replace(AT_LIMIT, "")
    m = CRIME.search(open_text) or re.search(r"\bsafe\w*", open_text, re.I)
    if m:
        out.append(f"{col}: crime or safety wording '{m.group(0)}' (the open prose is about living there)")
    if text.count(SAFEST) > 1:
        out.append(f"{col}: the 'safest' clause appears more than once")
    if AT_LIMIT in text and col != "watch_for":
        out.append(f"{col}: the safety-limit clause is allowed in watch_for only")
    m = NUMBER_WORDS.search(text.replace(SAFEST, ""))
    if m:
        out.append(f"{col}: spelled-out quantity '{m.group(0)}' (write digits and cite them)")
    words = len(text.split())
    if col in LIMITS[kind]:
        lo, hi = LIMITS[kind][col]
        if not lo <= words <= hi:
            out.append(f"{col}: {words} words, wanted {lo} to {hi}")
    if col in PARAGRAPHS[kind]:
        want, lo, hi = PARAGRAPHS[kind][col]
        paras = [p for p in text.split("\n\n") if p.strip()]
        if len(paras) != want:
            out.append(f"{col}: {len(paras)} paragraphs, wanted {want}")
        for i, p in enumerate(paras, 1):
            if not lo <= len(p.split()) <= hi:
                out.append(f"{col}: paragraph {i} has {len(p.split())} words, wanted {lo} to {hi}")
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
    def backed(field, op, bound):
        """True when an evidence item tests `field` with `op` at least as strictly as `bound`."""
        for ev in evidence:
            test = ev.get("holds_if") or []
            if ev.get("field") == field and len(test) == 2 and test[0] in op:
                try:
                    v = float(test[1])
                except ValueError:
                    continue
                if (v <= bound) if "<" in test[0] else (v >= bound):
                    return True
        return False
    joined = " ".join(texts.values())
    if SAFEST in joined and not backed(SAFEST_FIELD, ("<=", "<"), SAFEST_MAX):
        problems.append(f"'{SAFEST}' needs a test that the neighborhood is in the lowest fifth by violent rate")
    if joined.count(SAFEST) > 1:
        problems.append(f"'{SAFEST}' is used in more than one field")
    if AT_LIMIT in joined and not backed(AT_LIMIT_FIELD, (">=", ">"), AT_LIMIT_MIN):
        problems.append(f"'{AT_LIMIT}' needs a test that the violent rate is at least {AT_LIMIT_MIN}")
    for col, text in texts.items():
        if not text.strip():
            problems.append(f"{col}: empty")
            continue
        problems += check_style(kind, col, text)
        for n in numbers_in(text):
            if n not in allowed:
                problems.append(f"{col}: number '{n}' has no evidence item")
    return problems, drift


# Fixed wordings that every text may use: the toll sentence and the units of the crime figures.
REQUIRED_PHRASE = re.compile(r"about \$?# round trip with a new york e-zpass|per # residents|per #|against jamaica's #")
OPENING_WORDS, OPENING_MAX = 3, 3        # at most 3 texts may start with the same 3 words
RUN_WORDS, RUN_SHARE, RUN_FLOOR = 6, 0.10, 8   # no run of 6 words in more than a tenth of the texts (never fewer than 8)


def _norm(sentence):
    t = REQUIRED_PHRASE.sub(" | ", re.sub(r"\d[\d,.:]*\d|\d", "#", sentence.lower()))
    return [re.findall(r"[a-z#'é$-]+", part) for part in t.split("|")]


def check_repetition(col, texts):
    """texts: {key: prose} for one column across rows. The host voice must not read like a form letter: it fails when
    too many texts open the same way or share a long run of words. Returns a list of problems."""
    from collections import defaultdict
    openers, runs = defaultdict(set), defaultdict(set)
    for key, text in texts.items():
        if not text.strip():
            continue
        words = [w for part in _norm(sentences(text)[0]) for w in part]
        openers[" ".join(words[:OPENING_WORDS])].add(key)
        for sent in sentences(text):
            for words in _norm(sent):
                for i in range(len(words) - RUN_WORDS + 1):
                    runs[" ".join(words[i:i + RUN_WORDS])].add(key)
    RUN_MAX = max(RUN_FLOOR, int(len(texts) * RUN_SHARE))
    out = [f"{col}: {len(k)} texts open with '{o} ...' (limit {OPENING_MAX}): {sorted(k)[:5]}"
           for o, k in openers.items() if len(k) > OPENING_MAX]
    seen = set()
    for run, k in sorted(runs.items(), key=lambda x: -len(x[1])):
        if len(k) > RUN_MAX and not any(len(set(run.split()) & set(s.split())) >= RUN_WORDS - 2 for s in seen):
            seen.add(run)
            out.append(f"{col}: {len(k)} texts share the words '{run}' (limit {RUN_MAX}): {sorted(k)[:5]}")
    return out


def main():
    fails = drifts = rows = 0
    for kind, path, key in (("year", YEARS, "year_label"), ("hood", HOODS, "hood_id")):
        cols = COLUMNS[kind]
        if not path.exists():
            print(f"MISSING {path}")
            fails += 1
            continue
        host = {}
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows += 1
                missing = [c for c in cols if c not in r]
                if missing:
                    print(f"FAIL {r[key]}: columns missing: {missing}")
                    fails += 1
                    continue
                try:
                    evidence = json.loads(r["evidence_json"])
                except json.JSONDecodeError as e:
                    print(f"FAIL {r[key]}: evidence_json does not parse ({e})")
                    fails += 1
                    continue
                problems, drift = check_row(kind, r[key], {c: r[c] for c in cols}, evidence)
                if kind == "year" and year_key(r["display_label"]) != r[key]:
                    problems.append(f"display_label '{r['display_label']}' does not match the key")
                for p in problems:
                    print(f"FAIL {r[key]}: {p}")
                for d in drift:
                    print(f"drift {r[key]}: {d}")
                fails += bool(problems)
                drifts += bool(drift)
                host[r[key]] = r["host_intro"]
        for p in check_repetition("host_intro", host):
            print(f"FAIL {kind} texts: {p}")
            fails += 1
    print(f"{rows} rows checked, {fails} failing, {drifts} with drift only")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
