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


# ---------------------------------------------------------------------------------------------------------------
# Plain-language guards (copy edit of 2026-11-16). The owner's complaint was lines that try to be clever and end up
# unclear ("the dog walks you toward the water"). Each pattern below is a construction that was removed from the
# drafts; it fails wherever it comes back. Add to the list when a new one is cut.
CONCEITS = [
    # an inanimate subject doing something to "you"
    (r"\b(walks|sends|feeds|rewards|pays) you\b", "a thing acting on 'you' (say what she would do or find)"),
    (r"\b(the|a|your|this|its) (dog|street|block|park|town|city|neighborhood|building|garage|downtown|drive|road|curb|"
     r"car|water|beach|list|map|price|rent|toll|experience|apartment|place|morning|evening|day)s? (takes|tells|sells|"
     r"wants|asks|hands|owes) you\b", "a thing acting on 'you'"),
    (r"\bhas (a bedtime|wheels|your back|its own bedtime)\b", "personification"),
    (r"\b(car|cars|it) (sleeps?|lives?|would live|would sleep)\b|\bwhere (the|your|a) car (sleeps|lives|goes to sleep)",
     "'where the car sleeps' (say 'where you would park')"),
    (r"\bthe (cost|price|trade|upside|downside|rub|gap|catch|weak spot|soft spot|headline|answer) is (the |a |green|"
     r"distance|space|choice|miles)", "a noun phrase standing in for a claim ('the cost is the map')"),
    (r"\bthe upside is\b|\bthe rest of the story\b|\bcount on about\b|\bthen there is\b|\bon the table\b|"
     r"\bthen the practical side\b|\bnow the catch(es)?\b|\bknow the limits\b|\bboth are true\b|\bthe rest is\b|"
     r"\bhonest note\b|\bhard truth\b|\bthe honest\b|\bby the numbers\b|\bin the (best|kindest) sense\b",
     "a template seam or filler phrase"),
    (r"\bthe curb\b|\bshort straw\b|\brides? (shotgun|along)\b|\bhomework\b|\bdoes the talking\b|\bspeed dial\b|"
     r"\bfamily orbit\b|\bpoint of comedy\b|\bsalt air\b|\bcar keys\b|\bwalls close in\b|\bstay for seconds\b|"
     r"\bfiling complaints\b|\bzoomies\b|\bcaution label\b|\bsensible cousin\b|\bquiet surprise\b|\bthe lottery\b|"
     r"\bmembers-only\b|\bnot invited\b|\bbrag\b|\bsighs?\b|\bnightcap\b|\bfront yard\b|\bbackyard\b|\bmenus\b|"
     r"\bthe whole (game|case|pitch|answer|argument|evening|story)\b|\b(dog|dog's) (vote|whole case|whole life)\b|"
     r"\bwould pick this\b|\bis the neighbor\b|\bsquare feet with miles\b|\bpays? (for it )?in (distance|miles)\b|"
     r"\bsorted\b|\bfor once\b|\bpracticall?y (at|your)\b|\bcar country\b|\bapartment country\b|\bpark country\b",
     "a joke or figure of speech that needs decoding"),
    (r"\b(green|sand|trees) (is|are|takes|starts|sits|gets)\b|\bgain green\b|\breal green\b",
     "'green' / 'sand' used as a noun for parks or the beach (name the park or the beach)"),
    (r"\b(drive|trip|way|road|visit|visits|haul) home\b|\bhome is (close|near|about|a |far)|\bgoing home is\b",
     "'home' used for her parents' house (say 'to your parents')"),
    (r"\babout (0|no|zero)\b|\bonly no\b", "'about 0' (say there are none)"),
]
CONCEITS = [(re.compile(rx, re.I), what) for rx, what in CONCEITS]
# Words from inside the project that mean nothing to the reader, and wording the page does not use.
INTERNAL = re.compile(r"\b(ranked|ranks|ranking|scorecard|verified|live check|net-effective|net effective|gates?|asterisks?|"
                      r"cap|ceiling|shortlist|shown units?|listing ids?|unit-weighted|medians?)\b", re.I)
VOCAB = [
    (re.compile(r"\bMom and Dad\b"), "'Mom and Dad' in a sentence (labels use it; sentences say 'your parents')"),
    (re.compile(r"\b(the|a|an|each|every|this) unit\b|\bunits\b|\bin the unit\b", re.I), "'unit' (say 'apartment')"),
    (re.compile(r"\b(typical|only|lone|the) place\b|\bplaces? (here|found|we found|on the list|of this kind|turned up)\b|"
                r"\b\d+ places?\b", re.I), "'place' for an apartment (say 'apartment')"),
    (re.compile(r"\b(Walk-Everywhere|Old-Neighborhood|Little-City|Fresh-Start|Quiet-Street|Room-to-Breathe) Year\b|"
                r"\bthis year of\b|\ba year (here|like this)\b", re.I), "'year' for an experience"),
    (re.compile(r"\ball[- ]in\b(?! \(rent plus fees, parking and utilities\))", re.I),
     "'all-in' without its explanation (write 'everything included', or 'all-in (rent plus fees, parking and utilities)')"),
    (re.compile(r"\b(licence|theatre|programme|neighbour\w*|colour\w*|centre|favourite|kerb|storey|metres?|organis\w+|"
                r"realis\w+|travell\w+|grey)\b", re.I), "British spelling"),
    (re.compile(r"\bwe (found|set|would|think|looked)\b|\bour (list|scorecard|search)\b", re.I),
     "'we' / 'our' (no narrator on the page)"),
]
# Markers of a figure of speech. One per text is tolerated when its meaning is unmistakable; two is decoration.
FIGURE = re.compile(r"\blike a\b|\bas if\b|\bas though\b|\bfeels like\b|\bkind of\b|\bsort of\b|\bso to speak\b|"
                    r"\bthe heart of\b|\ba world away\b|\bat your door(step)?\b|\bon your doorstep\b|\bstone's throw\b|"
                    r"\bsteps (from|away)\b|\baround the corner\b|\bdownstairs\b", re.I)
MAX_FIGURES = 1
AVG_SENTENCE_WORDS, MAX_SENTENCE_WORDS = 20, 32          # per text: the average sentence, and the longest allowed


def check_plain(col, text):
    """Clarity guards for one text: removed conceits, internal terms, page vocabulary, sentence length, figures."""
    out = []
    for rx, what in CONCEITS + VOCAB:
        m = rx.search(text)
        if m:
            out.append(f"{col}: {what}: '{m.group(0)}'")
    m = INTERNAL.search(text)
    if m:
        out.append(f"{col}: internal term '{m.group(0)}'")
    figs = FIGURE.findall(text)
    if len(figs) > MAX_FIGURES:
        out.append(f"{col}: {len(figs)} figures of speech in one text ({', '.join(figs)}); at most {MAX_FIGURES}")
    lens = [len(x.split()) for x in sentences(text.replace("St. ", "St "))]
    if lens:
        if max(lens) > MAX_SENTENCE_WORDS:
            out.append(f"{col}: a sentence of {max(lens)} words (limit {MAX_SENTENCE_WORDS})")
        if sum(lens) / len(lens) > AVG_SENTENCE_WORDS:
            out.append(f"{col}: sentences average {sum(lens) / len(lens):.0f} words (limit {AVG_SENTENCE_WORDS})")
    return out


# ---------------------------------------------------------------------------------------------------------------
# The figure strip. Every count and money figure in the prose must be the one the strip above it shows, recomputed
# here from site/data.json: apartments = counts.shown, buildings = counts.buildings, neighborhoods = len(hood_ids),
# typical all-in = the median shown apartment (years[].medians.all_in; for a neighborhood the median of its units),
# its lowest and highest = all_in_range, minutes to her parents = medians.drive_min / transit_min (a neighborhood's
# own drive_min / transit_min). Prices in sentences are rounded to the nearest $10, minutes to the whole minute.
STRIP_SOURCE = {"year": PAGE + "#years", "hood": PAGE + "#neighborhoods"}
STRIP_KEY = {"year": "year_label", "hood": "hood_id"}
STRIP_FIELDS = {"year": {"all_in", "all_in_lo", "all_in_hi", "shown", "buildings", "n_hoods", "drive_min", "transit_min",
                         "toll_round_trip", "sqft"},
                "hood": {"all_in_median", "all_in_lo", "all_in_hi", "shown", "buildings", "drive_min", "transit_min",
                         "toll_round_trip", "sqft_median"}}
# the same quantities under the names they had when they were computed here from the unit list: no longer accepted
STRIP_OLD = {("listing_id", "count"), ("hood_id", "nunique"), ("building_id", "nunique"), ("all_in", "median"),
             ("drive_min", "median"), ("transit_min", "median"), ("toll_rt", "median"), ("sqft", "median")}
COUNTED_NOUN = re.compile(r"\b(\d[\d,]*) (apartments?|places?|listings?|buildings?|neighborhoods?|towns?|cities)\b", re.I)
BIG_MONEY = re.compile(r"\$\s?(\d{1,3},\d{3})")
PARENT_MIN = re.compile(r"(\d+) minutes")


def strip_values(kind, key):
    """What the page's figure strip shows for this row -> dict (empty when the row is not on the page)."""
    t = table(STRIP_SOURCE[kind])
    r = t[t[STRIP_KEY[kind]].astype(str) == str(key)]
    if len(r) != 1:
        return {}
    r = {k: plain(v) for k, v in r.iloc[0].to_dict().items()}
    if kind == "hood" and not r.get("shown"):
        return {}
    mid = r.get("all_in") if kind == "year" else r.get("all_in_median")
    v = {"money": {transform(x, "usd10") for x in (mid, r.get("all_in_lo"), r.get("all_in_hi")) if not is_missing(x)},
         "apartments": r.get("shown"), "buildings": r.get("buildings"),
         "neighborhoods": r.get("n_hoods") if kind == "year" else None,
         "minutes": {transform(x, "int") for x in (r.get("drive_min"), r.get("transit_min"), r.get("nearest_drive_min"))
                     if not is_missing(x)}}
    return v


def check_strip(kind, key, texts, evidence):
    """texts: [(column, prose)]. Counts, prices and minutes to her parents must be the figure strip's own."""
    out, strip = [], strip_values(kind, key)
    on_page = bool(strip)
    for ev in evidence:
        src, field, agg = str(ev.get("source_file", "")), ev.get("field"), ev.get("agg")
        if src == PAGE + "#units" and (field, agg) in STRIP_OLD and on_page:
            out.append(f"{field} ({agg}) is computed from the unit list; take it from the figure strip "
                       f"({STRIP_SOURCE[kind]}) so the text and the strip cannot differ ({ev.get('claim', '')[:50]})")
    want = {"apartment": "apartments", "place": "apartments", "listing": "apartments", "building": "buildings",
            "neighborhood": "neighborhoods", "town": "neighborhoods", "cities": "neighborhoods", "city": "neighborhoods"}
    for col, text in texts:
        for m in BIG_MONEY.finditer(text):
            if m.group(1) not in strip.get("money", set()):
                out.append(f"{col}: ${m.group(1)} is not a figure of the strip (typical, lowest or highest all-in: "
                           f"{sorted(strip.get('money', []))})")
        for m in COUNTED_NOUN.finditer(text):
            noun = m.group(2).lower()
            k = want.get(noun.rstrip("s"), want.get(noun))
            have = strip.get(k)
            if is_missing(have) or int(m.group(1).replace(",", "")) != int(have):
                out.append(f"{col}: '{m.group(0)}' but the strip counts {have} {k}")
        if on_page:
            for sent in sentences(text):
                if re.search(r"\bparents\b", sent) and not re.search(r"\b(park|dog run|on foot|walk)\b", sent):
                    for n in PARENT_MIN.findall(sent):
                        if n not in strip["minutes"]:
                            out.append(f"{col}: '{n} minutes' to her parents, but the strip has {sorted(strip['minutes'])}")
    return out


# ---------------------------------------------------------------------------------------------------------------
# A neighborhood's lead (the first sentence of its host_intro, which is also its line on the experience page) must say
# what sets the place apart. It may not open on a statistic that more than a third of the neighborhoods in the same
# experience also open on.
LEAD_SHARE, LEAD_MIN_ROWS = 1 / 3, 4


def lead_fields(text, evidence):
    """Measured fields quoted as a number in the first sentence of a lead."""
    first = (sentences(text.replace("St. ", "St ")) or [""])[0].replace("St ", "St. ")
    out = set()
    for ev in evidence:
        if ev.get("claim") == first and ev.get("shown") and ev.get("transform") not in ("convention", "in_text"):
            if any(n in numbers_in(first) for n in numbers_in(" ".join(ev["shown"]))):
                out.add(ev["field"])
    return out


def check_leads(rows):
    """rows: [{hood_id, year_label, host_intro, evidence (list)}] -> problems."""
    from collections import defaultdict
    by = defaultdict(list)
    for r in rows:
        if r.get("host_intro", "").strip():
            by[r["year_label"]].append(r)
    out = []
    for label, rs in by.items():
        if len(rs) < LEAD_MIN_ROWS:
            continue
        use = defaultdict(list)
        for r in rs:
            for f in lead_fields(r["host_intro"], r["evidence"]):
                use[f].append(r["hood_id"])
        for f, ids in use.items():
            if len(ids) > len(rs) * LEAD_SHARE:
                out.append(f"host_intro: {len(ids)} of the {len(rs)} neighborhoods in {label} open on the same "
                           f"statistic ({f}); a lead says what is different about the place: {sorted(ids)[:6]}")
    return out


def check_style(kind, col, text):
    out = check_plain(col, text)
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
    shown_cols = [(c, t) for c, t in list(texts.items()) + extra
                  if not (kind == "year" and c in ("scene", "host_walkthrough"))]     # those two repeat the moments
    problems += check_strip(kind, key, shown_cols, evidence)
    for run in shared_runs({"lead": [texts.get("host_intro", "")], "points": [p.get("text", "") for p in points],
                            "moments": [m.get("text", "") for m in moments],
                            "promise": [texts.get("promise", "")], "catch": [texts.get("catch", "")]}):
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
                r["evidence"] = evidence
        across = check_repetition("host_intro", host) + check_sub_shares(kind, seen)
        if kind == "hood":
            across += check_closings("host_intro", host) + check_leads(seen)
            n_drive = sum(ends_on_drive(t) for t in host.values())
            print(f"host_intro closes: {n_drive} of {len(host)} end on the drive, the toll or transit")
        for p in across:
            print(f"FAIL {kind} texts: {p}")
            fails += 1
    print(f"{rows} rows checked, {fails} failing, {drifts} with drift only")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
