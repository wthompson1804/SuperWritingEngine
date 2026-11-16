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
   One fixed wording is allowed, only with a test in the evidence: "one of the safest spots on the whole list"
   (neighborhood in the lowest fifth by violent rate among those on the page; one field only);
5. across rows, the host voice must not read like a form letter: at most 3 host_intro texts may open with the same 3
   words, and no run of 6 words may appear in more than a tenth of them (the fixed toll wording is exempt);
6. the neighborhood host_intro texts must not all end the same way: no closing shape (the first 4 words of the last
   sentence) in more than 15% of them, the drive-and-toll close on at most a third of them, and never on a text that
   already opened with the drive;
7. section subheads (sub_ columns): no wording on more than 6% of the neighborhoods for its section.

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

# host_intro is the lead of "About this experience" / "About <neighborhood>": 2 or 3 sentences, short, because the
# facts sit beside it as icon points (about_points_json) and must not be said twice.
LIMITS = {"year": {"host_intro": (25, 60), "tagline": (4, 14), "subhead": (6, 22)},
          "hood": {"scene": (8, 60), "host_intro": (12, 50)}}
LEAD_SENTENCES = (2, 3)
ICONS = ["home", "dog", "park", "car", "parking", "fork", "cocktail", "coffee", "train", "money", "clock", "moon", "sun",
         "water", "key", "heart", "people", "ruler", "laundry", "pool", "warning"]
POINTS_COUNT, POINT_MAX_WORDS = (4, 6), 14            # about_points_json: 4 to 6 {icon, text}; exactly one "warning"
MOMENT_TITLES, MOMENT_MAX_WORDS = ["A weekday", "Saturday night", "Sunday with Mom and Dad"], 35
JSON_COLS = {"year": ["about_points_json", "day_moments_json"], "hood": ["about_points_json"]}
STAGE = re.compile(r"\b(I|I'll|I'd|I've|my|me)\b|\blet's\b|\blet me\b|picture this|\bokay\b|your host", re.I)
PARAGRAPHS = {"year": {}, "hood": {}}      # (host_walkthrough and the year scene are now the three day moments, joined)
ONE_SENTENCE = {"year": ["promise", "tagline", "subhead"], "hood": ["good_for_her", "watch_for"]}
ONE_OR_TWO = {"year": ["catch"], "hood": []}
HOST_COLS = {"host_intro", "host_walkthrough", "tagline", "display_label", "subhead", "point", "moment"}   # may state all-in dollars
# One optional line in the host's voice under each section headline of the page ("sub_" columns). They are chosen from
# the conditional drafts in the source file ("=== sub:" blocks); empty means the data gave nothing distinctive to say.
SUB_SECTIONS = {"year": ["cost", "to_parents", "going_out", "green", "compared_to_queens"],
                "hood": ["cost", "to_parents", "parking", "dog", "going_out", "green", "residents_say", "local_rules",
                         "compared_to_queens"]}
SUB_MAX_WORDS = 14
COLUMNS = {"year": ["display_label", "tagline", "subhead", "scene", "promise", "catch", "host_intro", "host_walkthrough"]
           + ["sub_" + x for x in SUB_SECTIONS["year"]] + JSON_COLS["year"],
           "hood": ["scene", "good_for_her", "watch_for", "host_intro"] + ["sub_" + x for x in SUB_SECTIONS["hood"]]
           + JSON_COLS["hood"]}
VOICE_PHRASE = re.compile(r"review sites|people who live (here|in )|residents (of [A-Z][\w ]+ )?(also |here )?(say|like|praise|love|call|wish|"
                          r"describe|talk|complain|are split|warn|advise|enjoy|mention|report)", re.I)

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
# (A second wording, "the safety limit we set", was removed on the owner's instruction, 2026-11-16: safety is not a
# recurring theme, and a neighborhood near the limit simply gets no safety remark. It now fails like any crime wording.)
# Figures that describe the places SHOWN on the page: in a neighborhood that has shown units, these must be computed
# from those units (site/data.json#units), never from every candidate building or the area-wide file.
SHOWN_ONLY_FIELDS = {"restaurants_800m", "bars_800m", "cafes_800m", "restaurants_1600m", "park_walk_min", "dog_park_m",
                     "supermarket_m_c", "unit_sqft", "drive_min", "transit_to_parents_min", "train_station_m_c",
                     "toll_round_trip_ezpass", "dog_park_name", "park_name", "train_station"}


@lru_cache(maxsize=None)
def shown_hoods():
    """hood_ids that have at least one unit shown on the page."""
    return frozenset(table(PAGE + "#units")["hood_id"].dropna().astype(str))
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
            r = {"year_label": labels[y["id"]], "id": y["id"], **(y.get("medians") or {}),
                 **{"vq_" + k: v for k, v in (y.get("vs_queens") or {}).items()}}
            for k in ("all_in", "drive_min"):
                lo, hi = (y.get(k + "_range") or [None, None])[:2]
                r[k + "_lo"], r[k + "_hi"] = lo, hi
            r["neighborhoods"] = (y.get("counts") or {}).get("neighborhoods")
            r["shown"] = (y.get("counts") or {}).get("shown")
            r["buildings"] = (y.get("counts") or {}).get("buildings")
            r["n_hoods"] = len(y.get("hood_ids") or [])          # what "See the N neighborhoods" counts
            near = sorted((h for h in d["neighborhoods"] if h.get("year") == y["id"] and h.get("drive_min") is not None
                           and (h.get("counts") or {}).get("shown")), key=lambda h: h["drive_min"])
            r["nearest_name"], r["nearest_drive_min"] = (near[0]["name"], near[0]["drive_min"]) if near else (None, None)
            rows.append(r)
        return pd.DataFrame(rows)
    if part == "neighborhoods":
        rows = []
        for h in d["neighborhoods"]:
            lo, hi = (h.get("all_in_range") or [None, None])[:2]
            mine = sorted(u["all_in"] for u in d["units"] if u.get("hood_id") == h["id"] and u.get("all_in") is not None)
            mid = None if not mine else (mine[len(mine) // 2] if len(mine) % 2 else (mine[len(mine) // 2 - 1] + mine[len(mine) // 2]) / 2)
            rows.append({"hood_id": h["id"], "all_in_lo": lo, "all_in_hi": hi, "sqft_median": h.get("sqft_median"),
                         "all_in_median": mid,                    # the strip's "typical, all-in": the median shown unit
                         "shown": (h.get("counts") or {}).get("shown"),
                         "buildings": (h.get("counts") or {}).get("buildings"),
                         "drive_min": h.get("drive_min"), "transit_min": h.get("transit_min"),
                         "toll_round_trip": h.get("toll_round_trip"),
                         "violent": (h.get("safety") or {}).get("violent_per_1000"),
                         **{"vq_" + k: v for k, v in (h.get("vs_queens") or {}).items()}})
        t = pd.DataFrame(rows)
        t["all_in_spread"] = t["all_in_hi"] - t["all_in_lo"]
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
                "toll_complete": bool((mo.get("sun") or {}).get("toll_complete")),
                "park": (mo.get("wake") or {}).get("park"), "dog_park": (mo.get("wake") or {}).get("dog_park"),
                "train_station": (mo.get("sat") or {}).get("train_station"),
                "train_station_m": (mo.get("sat") or {}).get("train_station_m"),
                "open_gate": float(bool((u.get("confirm") or {}).get("asterisk"))),
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


RUN_WORDS_ROW = 6                                  # no run of 6 words shared by a row's lead, points and moments


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
    if agg == "nunique":
        return int(s.dropna().astype(str).nunique())
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
    if how == "usd10":                                # dollars to the nearest 10 (the page's rule for prices in sentences)
        return f"{int(half_up(x, 10)):,}"
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
    open_text = bare.replace(SAFEST, "")
    m = CRIME.search(open_text) or re.search(r"\bsafe\w*", open_text, re.I)
    if m:
        out.append(f"{col}: crime or safety wording '{m.group(0)}' (the open prose is about living there)")
    if text.count(SAFEST) > 1:
        out.append(f"{col}: the 'safest' clause appears more than once")
    m = NUMBER_WORDS.search(text.replace(SAFEST, ""))
    if m:
        out.append(f"{col}: spelled-out quantity '{m.group(0)}' (write digits and cite them)")
    words = len(text.split())
    if col.startswith("sub_"):
        if words > SUB_MAX_WORDS:
            out.append(f"{col}: {words} words, wanted at most {SUB_MAX_WORDS}")
        if len(sentences(text)) != 1:
            out.append(f"{col}: {len(sentences(text))} sentences, wanted 1")
        if re.search(r"\d", text):
            out.append(f"{col}: a section subhead carries no numbers (the headline states them)")
        if re.search(r"\b(may|might|perhaps|probably|possibly|somewhat|fairly|arguably|seems?)\b", text, re.I):
            out.append(f"{col}: hedging word")
    if col in LIMITS[kind]:
        lo, hi = LIMITS[kind][col]
        if not lo <= words <= hi:
            out.append(f"{col}: {words} words, wanted {lo} to {hi}")
    if col == "host_intro":
        k = len(sentences(text.replace("St. ", "St ")))
        if not LEAD_SENTENCES[0] <= k <= LEAD_SENTENCES[1]:
            out.append(f"{col}: {k} sentences, wanted {LEAD_SENTENCES[0]} or {LEAD_SENTENCES[1]}")
    if col in ("host_intro", "point", "moment"):
        m = STAGE.search(text)
        if m:
            out.append(f"{col}: stage business '{m.group(0)}' (the text is shown as a plain 'About ...', with no host on screen)")
    if col == "point" and words > POINT_MAX_WORDS:
        out.append(f"{col}: {words} words, wanted at most {POINT_MAX_WORDS}: {text}")
    if col == "moment" and words > MOMENT_MAX_WORDS:
        out.append(f"{col}: {words} words, wanted at most {MOMENT_MAX_WORDS}: {text}")
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


def read_points(kind, texts):
    """The icon points and the day's moments of a row -> (points, moments, problems). Each is a list of dicts."""
    out, problems = {}, []
    for col in JSON_COLS[kind]:
        try:
            out[col] = json.loads(texts.get(col) or "[]")
        except json.JSONDecodeError as e:
            out[col] = []
            problems.append(f"{col}: does not parse ({e})")
    points, moments = out.get("about_points_json", []), out.get("day_moments_json", [])
    if "about_points_json" in out:
        if not POINTS_COUNT[0] <= len(points) <= POINTS_COUNT[1]:
            problems.append(f"about_points_json: {len(points)} points, wanted {POINTS_COUNT[0]} to {POINTS_COUNT[1]}")
        if sum(p.get("icon") == "warning" for p in points) != 1:
            problems.append("about_points_json: wanted exactly one 'warning' point (the honest catch)")
        for p in points:
            if set(p) != {"icon", "text"} or p["icon"] not in ICONS or not str(p["text"]).strip():
                problems.append(f"about_points_json: bad point {p}")
        if len({p.get("text") for p in points}) < len(points):
            problems.append("about_points_json: a point appears twice")
    if "day_moments_json" in out:
        if [m.get("title") for m in moments] != MOMENT_TITLES:
            problems.append(f"day_moments_json: wanted exactly the moments {MOMENT_TITLES}")
        for m in moments:
            if set(m) != {"icon", "title", "text"} or m["icon"] not in ICONS or m["icon"] == "warning" or not str(m["text"]).strip():
                problems.append(f"day_moments_json: bad moment {m}")
    return points, moments, problems


def shared_runs(groups, n=RUN_WORDS_ROW):
    """groups: {name: [text, ...]}. Runs of n words that two different groups of one row share (the lead, the points
    and the moments must each say something of their own; the fixed toll wording is exempt)."""
    seen, out = {}, []
    for name, texts in groups.items():
        for text in texts:
            for sent in sentences(text):
                for words in _norm(sent):
                    for i in range(len(words) - n + 1):
                        run = " ".join(words[i:i + n])
                        if seen.setdefault(run, name) != name and run not in out:
                            out.append(run)
    return out


def check_row(kind, key, texts, evidence):
    """texts: {column: prose}. Returns (problems, drift)."""
    problems, drift, allowed = [], [], set()
    points, moments, bad = read_points(kind, texts)
    problems += bad
    texts = {c: t for c, t in texts.items() if c not in JSON_COLS[kind]}
    extra = [("point", str(p.get("text", ""))) for p in points] + [("moment", str(m.get("text", ""))) for m in moments]
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
    if kind == "year" or key in shown_hoods():
        for ev in evidence:
            if ev.get("transform") != "convention" and ev.get("field") in SHOWN_ONLY_FIELDS \
                    and not str(ev.get("source_file", "")).startswith(PAGE):
                problems.append(f"{ev['field']} is quoted from {ev['source_file']}, but there are places on the page "
                                f"here: the figure must come from the shown units ({ev.get('claim', '')[:50]})")
    for col, text in list(texts.items()) + extra:
        if not text.strip():
            if not col.startswith("sub_"):                # an empty section subhead is allowed: better than filler
                problems.append(f"{col}: empty")
            continue
        problems += check_style(kind, col, text)
        for n in numbers_in(text):
            if n not in allowed:
                problems.append(f"{col}: number '{n}' has no evidence item: {text[:60]}")
    for run in shared_runs({"lead": [texts.get("host_intro", "")], "points": [p.get("text", "") for p in points],
                            "moments": [m.get("text", "") for m in moments]}):
        problems.append(f"the lead, the points and the moments repeat each other: '{run}'")
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


# How a host_intro ends. The last sentence is "about the drive home" when it speaks of the parents, the toll or transit.
CLOSE_WORDS, CLOSE_SHARE, CLOSE_MIN_TEXTS = 4, 0.15, 20     # no closing shape in more than 15% of the texts
DRIVE_CLOSE_SHARE = 1 / 3                                   # the drive-and-toll close on at most a third of them
DRIVE_TALK = re.compile(r"e-zpass|\btolls?\b|toll-free|\btransit\b|your parents|sunday dinner|mom and dad", re.I)
CLOSE_KINDS = ["parking", "dog_green", "dinner", "residents", "choice", "life", "drive"]
SUB_SHARE = 0.06                                            # a section subhead on fewer than 6% of the neighborhoods


def closing(text):
    s = sentences(text)
    return s[-1] if s else ""


def ends_on_drive(text):
    return bool(DRIVE_TALK.search(closing(text)))


def opens_on_drive(text):
    return bool(DRIVE_TALK.search(" ".join(sentences(text)[:2])))


def check_closings(col, texts):
    """texts: {key: prose}. The last sentence must not be the same move every time. Returns a list of problems."""
    from collections import defaultdict
    texts = {k: t for k, t in texts.items() if t.strip()}
    if len(texts) < CLOSE_MIN_TEXTS:
        return []
    shapes = defaultdict(set)
    for key, text in texts.items():
        words = [w for part in _norm(closing(text)) for w in part]
        shapes[" ".join(words[:CLOSE_WORDS])].add(key)
    limit = int(len(texts) * CLOSE_SHARE)
    out = [f"{col}: {len(k)} texts close with '{shape} ...' (limit {limit}): {sorted(k)[:5]}"
           for shape, k in shapes.items() if len(k) > limit]
    drive = sorted(k for k, t in texts.items() if ends_on_drive(t))
    if len(drive) > len(texts) * DRIVE_CLOSE_SHARE:
        out.append(f"{col}: {len(drive)} of {len(texts)} texts end on the drive, the toll or transit "
                   f"(limit a third): {drive[:5]}")
    both = [k for k in drive if opens_on_drive(texts[k])]
    if both:
        out.append(f"{col}: these open with the drive and end on it too: {both[:8]}")
    return out


def check_sub_shares(kind, rows):
    """rows: [{column: text}]. No section subhead on more than SUB_SHARE of the rows (neighborhoods only: with 6
    experiences every subhead is a sixth of them)."""
    from collections import Counter
    if kind != "hood" or len(rows) < CLOSE_MIN_TEXTS:
        return []
    out = []
    limit = int(len(rows) * SUB_SHARE)
    for section in SUB_SECTIONS[kind]:
        col = "sub_" + section
        for text, n in Counter(r.get(col) or "" for r in rows).items():
            if text and n > limit:
                out.append(f"{col}: '{text}' is on {n} of {len(rows)} neighborhoods (limit {limit})")
    return out


def main():
    fails = drifts = rows = 0
    for kind, path, key in (("year", YEARS, "year_label"), ("hood", HOODS, "hood_id")):
        cols = COLUMNS[kind]
        if not path.exists():
            print(f"MISSING {path}")
            fails += 1
            continue
        host, seen = {}, []
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
                problems, drift = check_row(kind, r[key], {c: r[c] or "" for c in cols}, evidence)
                if kind == "year" and year_key(r["display_label"]) != r[key]:
                    problems.append(f"display_label '{r['display_label']}' does not match the key")
                for p in problems:
                    print(f"FAIL {r[key]}: {p}")
                for d in drift:
                    print(f"drift {r[key]}: {d}")
                fails += bool(problems)
                drifts += bool(drift)
                host[r[key]] = r["host_intro"]
                seen.append(r)
        across = check_repetition("host_intro", host) + check_sub_shares(kind, seen)
        if kind == "hood":
            across += check_closings("host_intro", host)
            n_drive = sum(ends_on_drive(t) for t in host.values())
            print(f"host_intro closes: {n_drive} of {len(host)} end on the drive, the toll or transit")
        for p in across:
            print(f"FAIL {kind} texts: {p}")
            fails += 1
    print(f"{rows} rows checked, {fails} failing, {drifts} with drift only")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
