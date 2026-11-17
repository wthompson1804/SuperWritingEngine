#!/usr/bin/env python3
"""Check the text of the experience pages and the neighborhood pages against the data it cites, and against the
plain-language rules of the 2026-11-16 copy edit.

Reads data/reference/scene_text_years.csv (the six experiences; the key column is still `year_label`) and
data/reference/scene_text_neighborhoods.csv. For every row and every prose column
(years: display_label, tagline, subhead, promise, catch, host_intro, the icon points and the three day moments;
 neighborhoods: scene, good_for_her, watch_for, host_intro, the icon points; both: the sub_ section subheads):

TRUE
1. every number in the prose must be "shown" by an item in that row's evidence_json;
2. every evidence item is looked up again in its source. The text passes when the CURRENT value still rounds to the
   printed number, a claim without a number still satisfies its `holds_if` test, a cited local rule is still in
   local_rules*.csv with the numbers quoted from it, and a paraphrase of residents rests on the same counts;
3. THE FIGURE STRIP (check_strip): counts, prices and minutes to her parents must be the ones the page prints in the
   strip above the text, recomputed here from site/data.json: apartments = counts.shown, buildings = counts.buildings,
   neighborhoods = len(hood_ids), typical total with utilities and fees = the median shown apartment, lowest / highest = all_in_range,
   minutes = medians.drive_min / transit_min (a neighborhood's own drive_min / transit_min). Any "$2,840", any
   "17 apartments", any "N minutes" in a sentence about her parents that is not the strip's figure fails; so does an
   evidence item that computes one of these from the unit list instead of reading the strip's field;
3b. DOOR-DISTANCE FACTS (independent check 4, D16): in a neighborhood with apartments on the page, restaurants, bars,
   cafés, the walk to a park, the dog park, the supermarket, the station, the water and the beach must be computed over
   the BUILDINGS SHOWN there (site/data.json#buildings: the median building; the building itself when one is shown).
   The neighborhood's frozen area profile (traits) is refused for them. glance_json, the "At a glance" facts written
   beside each neighborhood text, is recomputed here and must match (glance());
3c. WHAT THE SHOWN BUILDINGS SUPPLY, AND HOW MANY (check_shown; D6, D25): where every shown building has its own dog
   area the text says so and speaks of a dog park only as the public one; where some do, the distance is never the
   catch; where every shown building has a garage, street-parking trouble comes with "the building has its own
   garage" and never with advice to look for one; "The apartment ..." needs 1 apartment shown, "the apartments"
   2, "typical" 3; with several buildings a door-distance figure is scoped "most buildings here";
3d. WHAT AN EXPERIENCE MAY CLAIM (check_experience; D7, D11, D12): a claim such as "close to your parents", "no
   tolls", "you drive to dinner", "small apartments", "a garage" must hold for 75% of the apartments shown and for
   every neighborhood shown under it, or name the exceptions, or be limited to named places, or say "most" (60%).
   An experience with fewer than 8 apartments names its neighborhoods and uses no "typical", percentage or "most".
   A named neighborhood's figure never sits beside an unscoped figure for the whole experience;
PLAIN (check_plain; the reason for the edit: lines that tried to be clever and read like an error)
4. no thing as the subject of a verb of intention or speech (AGENCY, a noun-list x verb-list pattern: "the lawns
   keep their own counsel"), no stale wording (STALE: "not checked again", "compared to staying in Queens"), and
   no construction from the removed list (CONCEITS): a thing acting on "you" ("the dog walks you"), "has a bedtime",
   "where the car sleeps", "the cost is the ...", "the upside is", "the rest of the story", "count on about", "then
   there is", "on the table", "green" or "sand" as a noun, "home" for her parents' house, "about 0";
5. readability, per text: sentences average at most 20 words, none over 32, at most one figure-of-speech marker
   (FIGURE: "like a", "as if", "steps from", "around the corner" ...). What is NOT checked: a metaphor with no marker
   and an unclear pronoun both still need a human read;
6. the page's vocabulary: "your parents" (never "Mom and Dad" in a sentence), "apartment" (never "unit" or "place"),
   "experience" (never "... Year"), no "all-in" / "all in" and no "everything included" (a monthly total is
   "about $X a month with utilities and fees" on first mention, a quoted price is "rent"), no project terms (ranked, scorecard, verified, live check,
   net-effective, gate, asterisk, cap, ceiling), no "we", American spelling;
7. a text the page uses as a row headline (promise, good_for_her) fits whole in 64 characters, because the page cuts a
   longer one at a comma;
HOUSE STYLE (unchanged)
8. word limits, one-sentence fields, no question marks, no em or en dashes, no "not ... but", no spelled-out
   quantities, no wording about race, ethnicity or religion, no listing-ad hype words;
9. no crime wording in any open field. One fixed wording is allowed, only as an icon point of a neighborhood and only
   with a test in the evidence: "Among the safest places on the list." (lowest TENTH by violent rate among the page's
   neighborhoods, never where no rate is published; independent check 5, D27);
9b. INDEPENDENT CHECK 5 (each rule computed from the same field for every sentence; see the functions named):
   check_quantities    no two sentences of a neighborhood give incompatible amounts of restaurants, bars or cafés
                       ("no bars" beside "few bars"; "nothing is within walking distance" beside "2 cafés");
   dangling            no text opens on a sentence that leans on another ("too", "also", "as well", "And", "But");
   agreement           "N of the M buildings here has / have ..." agrees with N, in every text and glance label;
   check_station_words the nearest station is named by its kind (train station / subway / PATH / light rail);
   check_toll_range    a toll that differs by more than $5 between the buildings shown is given as a range;
   parking             what a garage is comes from the structured parking fields (realtor_lines.parking_facts);
ACROSS ROWS
10. a neighborhood's lead (the first sentence of host_intro, also its line on the experience page) may not open on a
    statistic that more than a third of the neighborhoods in the same experience also open on (check_leads);
11. form-letter limits, relaxed on purpose in the copy edit because they had pushed the writing toward forced
    variety: at most 8 host_intro texts open with the same 3 words, no run of 6 words in more than a quarter of them,
    no closing shape in more than 15%, the drive-and-toll close on at most a third and never on a text that opened
    with the drive, and no section subhead on more than 12% of the neighborhoods.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import realtor_lines as _RL  # noqa: E402   parking_facts(): the one reading of the structured parking fields

ROOT = Path(__file__).resolve().parent.parent
YEARS = ROOT / "data/reference/scene_text_years.csv"
HOODS = ROOT / "data/reference/scene_text_neighborhoods.csv"

TOLLS = "data/enriched/*.json"                     # virtual table: one row per building, see _toll_table()
PAGE = "site/data.json"                            # virtual tables "site/data.json#years|neighborhoods|units"

# host_intro is the lead of "About this experience" / "About <neighborhood>": 2 or 3 sentences, short, because the
# facts sit beside it as icon points (about_points_json) and must not be said twice.
LIMITS = {"year": {"host_intro": (25, 60), "tagline": (4, 14), "subhead": (6, 22)},
          "hood": {"scene": (8, 60), "host_intro": (8, 50)}}
LEAD_SENTENCES = (1, 3)
ICONS = ["home", "dog", "park", "car", "parking", "fork", "cocktail", "coffee", "train", "money", "clock", "moon", "sun",
         "water", "key", "heart", "people", "ruler", "laundry", "pool", "warning"]
POINTS_COUNT, POINT_MAX_WORDS = (3, 6), 14            # about_points_json: 4 to 6 {icon, text}; exactly one "warning"
MOMENT_TITLES, MOMENT_MAX_WORDS = ["A weekday", "Saturday night", "Sunday with Mom and Dad"], 35
JSON_COLS = {"year": ["about_points_json", "day_moments_json"], "hood": ["about_points_json"]}
STAGE = re.compile(r"\b(I|I'll|I'd|I've|my|me)\b|\blet's\b|\blet me\b|picture this|\bokay\b|your host", re.I)
PARAGRAPHS = {"year": {}, "hood": {}}      # (host_walkthrough and the year scene are now the three day moments, joined)
ONE_SENTENCE = {"year": ["promise", "tagline", "subhead"], "hood": ["good_for_her", "watch_for"]}
ONE_OR_TWO = {"year": ["catch"], "hood": []}
# The page uses these as the headline of a closed row (site/index.html, HL.first: whole when it fits in HL_MAX = 64
# characters, otherwise cut at a clause boundary), so they must fit whole.
HEADLINE_COLS, HEADLINE_MAX = {"year": ["promise"], "hood": ["good_for_her"]}, 64
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
VOICE_PHRASE = re.compile(r"review sites|people who live (here|in )|residents (of [A-Z][\w ]+ )?(also |here |still )?(say|like|praise|love|call|wish|"
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
# Independent check 5 (D27, N13) tightened it: the wording is now an icon point of its own, never a sentence tacked
# on to a paragraph about restaurants; only for the lowest TENTH by violent rate among the neighborhoods shown (it was
# the lowest fifth, 15 neighborhoods); and never where no rate is published (safety.status = not_published).
SAFEST = "Among the safest places on the list"            # the whole icon point, as written
SAFEST_OLD = re.compile(r"safest (?:spots?|places?|neighborhoods?) on the (?:whole )?list", re.I)
SAFEST_FIELD, SAFEST_MAX = "violent_pctile", 0.1          # share of the page's neighborhoods at or below its violent rate
# (A second wording, "the safety limit we set", was removed on the owner's instruction, 2026-11-16: safety is not a
# recurring theme, and a neighborhood near the limit simply gets no safety remark. It now fails like any crime wording.)
# Figures that describe the places SHOWN on the page: in a neighborhood that has shown units, these must be computed
# from those units (site/data.json#units), never from every candidate building or the area-wide file.
SHOWN_ONLY_FIELDS = {"restaurants_800m", "bars_800m", "cafes_800m", "restaurants_1600m", "park_walk_min", "dog_park_m",
                     "supermarket_m_c", "unit_sqft", "drive_min", "transit_to_parents_min", "train_station_m_c",
                     "toll_round_trip_ezpass", "dog_park_name", "park_name", "train_station"}


GLANCE_TRAITS = ["restaurants_800m", "bars_800m", "cafes_800m", "park_walk_min", "park_ha_800m", "dog_park_m",
                 "supermarket_m_c", "open_water_m"]
# DOOR-DISTANCE FACTS (independent check 4, D16). Things measured from the door of the buildings she would live in:
# in a neighborhood with apartments on the page they must be computed over the SHOWN BUILDINGS
# (site/data.json#buildings: the median building, which is the building itself when one is shown). The neighborhood's
# frozen area profile (traits, the t_ columns) and the area file are refused for them, and so is a median over the
# apartments (a building with 8 apartments would count 8 times). Before D16 the rule was the opposite: the text had
# to quote the traits because "At a glance" printed them; "At a glance" now reads glance_json (see glance()).
DOOR_FIELDS = {"restaurants_800m", "bars_800m", "cafes_800m", "restaurants_1600m", "park_walk_min", "dog_park_m",
               "supermarket_m", "supermarket_m_c", "train_station_m", "train_station_m_c", "open_water_m", "beach_m",
               "park_ha_800m", "t_restaurants_800m", "t_bars_800m", "t_cafes_800m", "t_park_walk_min",
               "t_park_ha_800m", "t_dog_park_m", "t_supermarket_m_c", "t_open_water_m"}
DOOR_SOURCE = PAGE + "#buildings"


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


def _range_fields(name, rng, single=None):
    """{name_lo, name_hi, name_spread} from a [low, high] pair; a single figure stands for both where there is no pair."""
    lo, hi = (list(rng) + [None, None])[:2] if isinstance(rng, (list, tuple)) else (None, None)
    lo = single if is_missing(lo) else lo
    hi = single if is_missing(hi) else hi
    return {name + "_lo": lo, name + "_hi": hi,
            name + "_spread": None if is_missing(lo) or is_missing(hi) else float(hi) - float(lo)}


def _span(xs):
    xs = [float(x) for x in xs if not is_missing(x)]
    return [min(xs), max(xs)] if xs else None


def year_key(label):
    """The internal key stays '... Year' whatever the page calls it."""
    return re.sub(r"\bExperience$", "Year", str(label).strip())


PAGE_FILE = ROOT / PAGE                             # the file behind the virtual page tables (see use_files)
SUBSET = False                                     # True while a --data file is checked (see use_files)
OUT_SUFFIX = ""                                    # the --out-suffix in use


def use_files(data=None, out_suffix=""):
    """Options --data and --out-suffix (added for the concierge page, docs/CONCIERGE_DESIGN.md): run the same drafts
    and guards over another page-data file (a filtered copy of site/data.json in the same shape) and read or write
    data/reference/scene_text_years<suffix>.csv and scene_text_neighborhoods<suffix>.csv. In evidence items the
    virtual tables keep their names ("site/data.json#units" ...): with --data they are the tables of that file.
    With no options nothing changes. With --data the texts describe a SUBSET of the page: the guards on each text
    all run, and the two guards that only spread wordings across the whole page (a section subhead on at most
    SUB_SHARE of the neighborhoods; the drive-and-toll close on at most a third) are skipped."""
    global PAGE_FILE, YEARS, HOODS, SUBSET, OUT_SUFFIX
    if data:
        PAGE_FILE = Path(data) if Path(data).is_absolute() else Path.cwd() / data
        SUBSET = True
    if out_suffix:
        OUT_SUFFIX = out_suffix
        YEARS = YEARS.with_name(YEARS.stem + out_suffix + YEARS.suffix)
        HOODS = HOODS.with_name(HOODS.stem + out_suffix + HOODS.suffix)
    for f in (_page, table, shown_hoods, _units_with_hood):
        f.cache_clear()


def _options(argv, description):
    import argparse
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--data", default=None, help="page data to read instead of site/data.json (same shape)")
    ap.add_argument("--out-suffix", default="", help="suffix of the two scene-text CSVs, for example _u2000")
    a = ap.parse_args(argv)
    if a.data or a.out_suffix:
        use_files(a.data, a.out_suffix)
    return a


@lru_cache(maxsize=None)
def _page():
    return json.loads(PAGE_FILE.read_text(encoding="utf-8"))


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
            r.update(_split_fields(d, y))
            rows.append(r)
        return pd.DataFrame(rows)
    if part == "neighborhoods":
        rows = []
        for h in d["neighborhoods"]:
            lo, hi = (h.get("all_in_range") or [None, None])[:2]
            mine = sorted(u["all_in"] for u in d["units"] if u.get("hood_id") == h["id"] and u.get("all_in") is not None)
            mid = None if not mine else (mine[len(mine) // 2] if len(mine) % 2 else (mine[len(mine) // 2 - 1] + mine[len(mine) // 2]) / 2)
            rows.append({"hood_id": h["id"], "all_in_lo": lo, "all_in_hi": hi, "sqft_median": h.get("sqft_median"),
                         "all_in_median": mid,                    # the strip's typical total: the median shown unit
                         "shown": (h.get("counts") or {}).get("shown"),
                         "buildings": (h.get("counts") or {}).get("buildings"),
                         "drive_min": h.get("drive_min"), "transit_min": h.get("transit_min"),
                         "toll_round_trip": h.get("toll_round_trip"),
                         # the lowest and highest toll among the buildings shown (independent check 5, N9)
                         **_range_fields("toll", h.get("toll_round_trip_range"), h.get("toll_round_trip")),
                         "safety_published": int((h.get("safety") or {}).get("status") != "not_published"
                                                 and (h.get("safety") or {}).get("violent_per_1000") is not None),
                         "in_queens": int(str(h.get("area") or "") == "Queens"),
                         "name": h.get("name"), "area": h.get("area"), "year": h.get("year"),
                         # the neighborhood's frozen area profile (its traits): area-wide facts only since D16
                         **{"t_" + k: (h.get("traits") or {}).get(k) for k in GLANCE_TRAITS},
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
            kind = parking_head(pk)
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
                "garage_or_covered": float(kind in ("garage", "covered")),
                "station_is_train": (None if not (mo.get("sat") or {}).get("train_station_kind") else
                                     float((mo.get("sat") or {}).get("train_station_kind") == "train")),
                "parking_published": float(bool(kind)),
                "pool": float(bool(am.get("pool"))), "doorman": float(bool(am.get("doorman"))),
                "gym": float(bool(am.get("gym"))), "in_unit_laundry": float(am.get("in_unit_laundry") == "yes"),
                "building_id": u.get("building_id"), "own_dog_area": float(own_dog_area(am)),
                "own_parking": float(kind in OWN_PARKING),
                "toll_own": (mo.get("sun") or {}).get("toll_round_trip"),
                "year_built": am.get("year_built"),
            })
        t = pd.DataFrame(rows)
        bt = _building_table(d, labels)
        if len(bt):                                   # the distance to open water is a building's, kept in master_buildings.csv
            t["open_water_m"] = t["building_id"].map(bt.set_index("building_id")["open_water_m"])
        else:
            t["open_water_m"] = None
        return t
    if part == "buildings":
        return _building_table(d, labels)
    raise KeyError(f"no page table '{part}'")


# What a building supplies itself (2026-11-16, independent check 4, D6): twelve neighborhoods lamented the distance to
# a public dog park while their only building had its own. The neighborhood text now reads these.
def own_dog_area(amenities):
    """True when the building's own amenity list names a dog park or a dog run on the property. A pet spa, a dog wash
    or a bare "yes" is not a place to let a dog out, so it does not count."""
    am = amenities or {}
    if isinstance(am.get("dog_park_or_run"), bool):       # the pipeline's own reading of each source's words
        return am["dog_park_or_run"]
    a = str(am.get("dog_amenities") or "").lower()        # page data written before that field existed
    a = re.sub(r"no dog (run|park)[^;]*", " ", a)
    return bool(re.search(r"dog (park|run)|pet park|bark park", a))


def dog_amenity_any(amenities):
    """True when the building lists any dog amenity at all: a dog park or run, a pet spa or dog wash, or one whose
    kind the source does not say."""
    am = amenities or {}
    flags = [am.get(k) for k in ("dog_park_or_run", "pet_spa_or_wash", "dog_amenity_unspecified")]
    if all(isinstance(x, bool) for x in flags):
        return any(flags)
    return bool(str(am.get("dog_amenities") or "").strip())


OWN_PARKING = ("garage", "covered", "lot", "off_street", "assigned", "unspecified")   # a space at the building


def parking_head(parking):
    """The space she would park in -> 'garage' | 'covered' | 'lot' | 'off_street' | 'assigned' | 'offsite' | 'street' |
    'unspecified' | '' (nothing published). Read from the page's STRUCTURED parking fields (parking.kind,
    included_kind) through realtor_lines.parking_facts, so the neighborhood text, the building text and "At a glance"
    cannot disagree about what a garage is (independent check 5, N1 and N8: an open lot with a garage as a paid
    extra is not a garage; an off-site deck is not parking at the building)."""
    return _RL.parking_facts({"parking": parking or {}})["kind"] or ""


def _building_table(d, labels):
    """One row per building SHOWN on the page (site/data.json buildings[]), with the door-distance figures of its own
    apartments (every apartment of a building carries the same ones; the first that has a value is used), what the
    building itself supplies (a dog area, a garage) and three distances the page data lacks, read from
    data/master_buildings.csv by building id (open_water_m, beach_m, park_ha_800m). A neighborhood's door-distance
    figure is the median over these rows: the building's own figure when one building is shown."""
    units = {}
    for u in d["units"]:
        units.setdefault(u.get("building_id"), []).append(u)
    try:
        mb = pd.read_csv(ROOT / "data/master_buildings.csv", low_memory=False,
                         usecols=lambda c: c in ("building_id", "open_water_m", "beach_m", "park_ha_800m"))
        mb = mb.drop_duplicates("building_id").set_index("building_id")
    except (OSError, ValueError):
        mb = pd.DataFrame()
    def first(us, a, b):
        for u in us:
            v = ((u.get("moments") or {}).get(a) or {}).get(b)
            if not is_missing(v):
                return v
        return None
    rows = []
    for b in d.get("buildings") or []:
        us = units.get(b["id"]) or []
        if not us:
            continue
        head = parking_head(b.get("parking"))
        am = b.get("amenities") or {}
        r = {"building_id": b["id"], "hood_id": b.get("hood_id"), "year_label": labels.get(b.get("experience")),
             "name": b.get("name"), "n_units": len(us),
             "restaurants_800m": first(us, "after", "restaurants_800m"), "bars_800m": first(us, "after", "bars_800m"),
             "cafes_800m": first(us, "after", "cafes_800m"), "restaurants_1600m": first(us, "sat", "restaurants_1600m"),
             "bars_1600m": first(us, "sat", "bars_1600m"),
             "park_walk_min": first(us, "wake", "park_walk_min"), "dog_park_m": first(us, "wake", "dog_park_m"),
             "supermarket_m": first(us, "work", "supermarket_m"), "train_station_m": first(us, "sat", "train_station_m"),
             "park": first(us, "wake", "park"), "dog_park": first(us, "wake", "dog_park"),
             "train_station": first(us, "sat", "train_station"),
             # the nearest station is of any kind since independent check 5 (N3): train / subway / PATH / light rail
             "train_station_kind": first(us, "sat", "train_station_kind") or ("train" if first(us, "sat", "train_station") else None),
             "train_station_system": first(us, "sat", "train_station_system"),
             "commuter_station_m": first(us, "sat", "commuter_station_m"),
             "commuter_station": first(us, "sat", "commuter_station"),
             "pet_spa": float(bool(am.get("pet_spa_or_wash"))),
             "drive_min": first(us, "sun", "drive_min"),
             "own_dog_area": float(own_dog_area(b.get("amenities"))),
             # any dog amenity at all, also a pet spa or dog wash or one of unnamed kind: not a dog area the text may
             # claim, but enough that the distance to a public dog park is not the catch
             "dog_amenity_any": float(dog_amenity_any(b.get("amenities"))),
             "own_garage": float(head == "garage"),         # a garage, not covered parking or a lot
             "own_parking": float(head in OWN_PARKING),
             "year_built": (b.get("amenities") or {}).get("year_built")}
        for k in ("open_water_m", "beach_m", "park_ha_800m"):
            r[k] = plain(mb.at[b["id"], k]) if (len(mb) and k in mb.columns and b["id"] in mb.index) else None
        rows.append(r)
    return pd.DataFrame(rows)


CLOSE_DRIVE_MIN = 30          # "close to your parents": the page's own line for a strong Sunday (30 minutes or less)
SMALL_EXPERIENCE = 8          # an experience showing fewer apartments than this is written as a short note (D11)


def join_and(items):
    items = [str(x) for x in items]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1] if items else ""


def _median(xs):
    xs = sorted(x for x in xs if not is_missing(x))
    if not xs:
        return None
    k = len(xs) // 2
    return xs[k] if len(xs) % 2 else (xs[k - 1] + xs[k]) / 2


def _split_fields(d, y):
    """How an experience's shown apartments divide on the drive to her parents (D12: "close to your parents" was
    written over an experience with 29 of 81 apartments in Newark, 47 minutes and a toll away). `close` = a drive of
    CLOSE_DRIVE_MIN minutes or less. Names are joined in descending order of apartments, so a draft can test them
    ({!far_names==Newark}) and then name them in plain words."""
    from collections import Counter
    hoods = {h["id"]: h for h in d["neighborhoods"]}
    us = [u for u in d["units"] if u.get("year") == y["id"]]
    sun = lambda u: (u.get("moments") or {}).get("sun") or {}
    hd = lambda u: (hoods.get(u.get("hood_id")) or {}).get("drive_min")      # the neighborhood's own figure, as on its page
    close = [u for u in us if not is_missing(hd(u)) and hd(u) <= CLOSE_DRIVE_MIN]
    far = [u for u in us if not is_missing(hd(u)) and hd(u) > CLOSE_DRIVE_MIN]
    free = [u for u in us if sun(u).get("toll_complete") and sun(u).get("toll_round_trip") == 0]
    def names(group, key):
        c = Counter((hoods.get(u.get("hood_id")) or {}).get(key) for u in group)
        return join_and([k for k, _ in sorted(c.items(), key=lambda kv: (-kv[1], str(kv[0]))) if k])
    per_hood = Counter(u.get("hood_id") for u in us)
    return {
        "hood_names": "; ".join(sorted((hoods.get(h) or {}).get("name") or h for h in per_hood)),
        "by_hood": join_and([f"{n} in {(hoods.get(h) or {}).get('name') or h}" for h, n in
                             sorted(per_hood.items(), key=lambda kv: (-kv[1], str(kv[0])))]),
        "close_n": len(close), "far_n": len(far), "close_share": len(close) / len(us) if us else None,
        "close_areas": names(close, "area"), "far_names": names(far, "name"),
        "close_drive_hi": max((sun(u)["drive_min"] for u in close), default=None),
        "far_drive": _median(sun(u).get("drive_min") for u in far),
        "far_toll": _median(sun(u).get("toll_round_trip") for u in far),
        # the lowest and highest toll of each group a sentence may speak of (independent check 5, N9: "From Newark
        # each visit costs about $24" was wrong for 7 of 21 apartments, up to $43)
        **_range_fields("toll", _span(sun(u).get("toll_round_trip") for u in us)),
        **_range_fields("far_toll", _span(sun(u).get("toll_round_trip") for u in far)),
        **_range_fields("close_toll", _span(sun(u).get("toll_round_trip") for u in close if u not in free)),
        "tollfree_share": len(free) / len(us) if us else None, "tollfree_areas": names(free, "area"),
        "toll_areas": names([u for u in close if u not in free], "area"),
        "close_toll": _median(sun(u).get("toll_round_trip") for u in close if u not in free),
    }


def is_small_experience(label):
    t = table(PAGE + "#years")
    r = t[t["year_label"].astype(str) == year_key(label)]
    return bool(len(r)) and not is_missing(r.iloc[0]["shown"]) and int(r.iloc[0]["shown"]) < SMALL_EXPERIENCE


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
    if agg == "share":              # a mean that is 0 over no rows: "no building shown here has it" also where none is shown
        num = pd.to_numeric(s, errors="coerce").dropna()
        return plain(float(num.mean())) if len(num) else 0.0
    if agg == "nunique":
        return int(s.dropna().astype(str).nunique())
    if agg == "uniform":            # the one value every row shares, "mixed" where they differ, None where none has one
        vals = sorted(set(s.dropna().astype(str)))
        return vals[0] if len(vals) == 1 else "mixed" if vals else None
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
        return f"{int(half_up(x, 10)):,}"
    if how == "usd50":                                # dollars to the nearest 50, with a comma: 2707 -> "2,700"
        return f"{int(half_up(x, 50)):,}"
    if how == "usd10":                                # dollars to the nearest 10 (the page's rule for prices in sentences)
        return f"{int(half_up(x, 10)):,}"
    if how == "pct":                                  # a share 0..1 -> whole percent
        return f"{int(half_up(x * 100))}"
    if how == "mi0":                                  # meters -> whole miles (for far-away things)
        return f"{int(half_up(x / 1609.34))}"
    if how == "mi":                                   # meters -> miles, one decimal, never below 0.1
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
    (r"\babout (0|no|zero)\b(?!\.\d)|\bonly no\b", "'about 0' (say there are none)"),
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
    (re.compile(r"\ball[- ]in\b", re.I),
     "'all-in' / 'all in' (the page says 'with utilities and fees' for the total, 'rent' for what the listing asks)"),
    (re.compile(r"\beverything(?: is)? included\b", re.I),
     "'everything included' (the page says 'with utilities and fees')"),
    (re.compile(r"\b(licence|theatre|programme|neighbour\w*|colour\w*|centre|favourite|kerb|storey|metres?|organis\w+|"
                r"realis\w+|travell\w+|grey)\b", re.I), "British spelling"),
    (re.compile(r"\bwe (found|set|would|think|looked)\b|\bour (list|scorecard|search)\b", re.I),
     "'we' / 'our' (no narrator on the page)"),
]
# Wording that was true of an earlier state of the project and must not come back (independent check 4, D15).
STALE = [
    (re.compile(r"\bnot (?:been )?(?:checked|read|re-read|re-checked|rechecked|looked at) again\b|\bnot re-?checked\b|"
                r"\bnever re-?read\b|\bnot yet re-?checked\b", re.I),
     "'not checked again' (a listing that was never re-read carries no remark; owner's rule of 2026-11-16)"),
    (re.compile(r"\bcompared to staying in Queens\b|\bthan (?:in )?(?:most of )?Queens\b(?! apartments?\b)|"
                r"\b(?:like|over|as in|in most of) Queens\b(?! apartments?\b)", re.I),
     "a comparison with 'Queens' as a place (some of these neighborhoods are in Queens: compare with 'a typical "
     "Queens apartment')"),
]

# THE GENERAL CONCEIT GUARD (independent check 4, D15b). The list above only catches constructions that were already
# cut once; "The lawns keep their own counsel." passed. This rule catches the family: a sentence in which a THING is
# the grammatical subject of a verb of intention or speech. It is a noun-list x verb-list pattern, nothing cleverer:
#   subject = a noun of THING_NOUNS (singular or plural), optionally one adverb, immediately followed by
#   a verb of INTENT_VERBS in the present or the past ("the lawns keep", "the river tucks", "the town never sleeps").
# Limits, on purpose and documented in docs/SCENE_TEXT_NOTES.md:
#   - only a noun on the list is seen ("the cul-de-sac keeps its secrets" passes until "cul-de-sac" is added);
#   - the verb must follow the noun directly (or after one adverb): "the town, people say, never sleeps" and a verb in
#     a relative clause ("a town that welcomes dogs") pass;
#   - verbs with a plain everyday use for a thing are NOT on the list (has, is, offers, lists, costs, takes, needs,
#     allows, bans, restricts, runs, sits, opens, closes, includes), so "the town bans overnight parking" passes;
#   - a metaphor with no such verb ("a harbor of calm") still needs a human read.
THING_NOUNS = ("lawn|street|block|avenue|sidewalk|park|town|city|village|suburb|neighborhood|building|tower|garage|lot|"
               "downtown|drive|road|highway|car|water|river|harbor|bay|ocean|sea|beach|shore|waterfront|pond|lake|"
               "price|rent|cost|toll|budget|lease|apartment|studio|kitchen|bedroom|lobby|elevator|hallway|morning|"
               "evening|night|weekend|day|train|station|bus|house|yard|tree|bar|restaurant|café|cafe|shop|store|"
               "supermarket|view|skyline|bridge|tunnel|pool|gym|desk|sofa|door|window|map|dog run|dog park|commute|"
               "parking|quiet|silence|trail|boardwalk|pier|field|garden|hill")
INTENT_VERBS = ("keeps?|kept|tells?|told|knows?|knew|wants?|wanted|asks?|asked|rewards?|rewarded|pays?|paid|greets?|"
                "greeted|waits?|waited|sleeps?|slept|speaks?|spoke|promises?|promised|forgives?|forgave|whispers?|"
                "whispered|welcomes?|welcomed|invites?|invited|remembers?|remembered|forgets?|forgot|hugs?|hugged|"
                "embraces?|embraced|tucks?|tucked|sings?|sang|smiles?|smiled|beckons?|beckoned|watches|watch|watched|"
                "loves?|loved|hates?|hated|hopes?|hoped|dreams?|dreamed|wakes?|woke|breathes?|breathed|listens?|"
                "listened|insists?|insisted|demands?|demanded|refuses?|refused|nods?|nodded|winks?|winked|hums?|"
                "hummed|talks?|talked|shouts?|shouted|decides?|decided|tries|tried|thinks?|thought|feels?|felt|"
                "minds?|minded|cares?|cared|laughs?|laughed|cries|cried|begs?|begged|owes?|owed|forgives|teaches|"
                "taught|learns?|learned|plays?|played host|stands? guard|holds? its breath")
AGENCY = re.compile(rf"\b(?:{THING_NOUNS})s? (?:(?:still|never|always|only|just|really|simply|quietly|gently|also|"
                    rf"almost|usually|often|rarely|barely|hardly|finally) )?(?:{INTENT_VERBS})\b", re.I)
# "... so ask the office", "before you tour ask": an imperative or an infinitive after the noun is not the noun acting
AGENCY_OK = re.compile(r"\b(?:to|and|or|then|so|please|would|will|can|could|should|must|may|might|you|they|we|i) $", re.I)


def agency(text):
    """A thing as the subject of a verb of intention or speech -> the matched words, or None."""
    for m in AGENCY.finditer(text):
        if AGENCY_OK.search(text[:m.start()] + " "):
            continue
        return m.group(0)
    return None


# Markers of a figure of speech. One per text is tolerated when its meaning is unmistakable; two is decoration.
FIGURE = re.compile(r"\blike a\b|\bas if\b|\bas though\b|\bfeels like\b|\bkind of\b|\bsort of\b|\bso to speak\b|"
                    r"\bthe heart of\b|\ba world away\b|\bat your door(step)?\b|\bon your doorstep\b|\bstone's throw\b|"
                    r"\bsteps (from|away)\b|\baround the corner\b|\bdownstairs\b", re.I)
MAX_FIGURES = 1
AVG_SENTENCE_WORDS, MAX_SENTENCE_WORDS = 20, 32          # per text: the average sentence, and the longest allowed


def check_plain(col, text):
    """Clarity guards for one text: removed conceits, internal terms, page vocabulary, sentence length, figures."""
    out = []
    plain_text = text.replace(SAFEST, "Among them")       # the one fixed wording about safety (its "places" are neighborhoods)
    for rx, what in CONCEITS + VOCAB + STALE:
        m = rx.search(plain_text)
        if m:
            out.append(f"{col}: {what}: '{m.group(0)}'")
    hit = agency(text)
    if hit:
        out.append(f"{col}: a thing as the subject of a verb of intention or speech (say the plain fact): '{hit}'")
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
    out += [f"{col}: {p}" for p in monthly_price(text)]
    return out


# The page shows two labelled prices: "Rent" (what the listing asks) and "Total with utilities and fees". A sentence
# says which one it gives: the first monthly figure of $1,000 or more in a text is "about $X a month with utilities and
# fees" (later ones "about $X a month"), unless the sentence calls the figure rent.
MONTHLY_PRICE = re.compile(r"\$\s?\d{1,3},\d{3}(?:\{[^}]*\})* a month\b(?P<uf> with utilities and fees\b)?", re.I)
RENT_FIGURE = re.compile(r"\brent (?:is|of|starts at|from)(?: about)? \$\s?\d{1,3},\d{3}\b", re.I)


def monthly_price(text):
    """-> messages. The first monthly total of a text must say 'with utilities and fees'; a later one must not repeat it."""
    out, seen = [], False
    for m in MONTHLY_PRICE.finditer(text):
        if m.group("uf") and seen:
            out.append(f"'with utilities and fees' repeated: say 'about $X a month' after the first mention: '{m.group(0)}'")
        elif not m.group("uf") and not seen:
            out.append(f"a monthly price that does not say which: write '{m.group(0)} with utilities and fees' "
                       f"(the total) or 'the rent is $X'")
        seen = True
    return out


# ---------------------------------------------------------------------------------------------------------------
# The figure strip. Every count and money figure in the prose must be the one the strip above it shows, recomputed
# here from site/data.json: apartments = counts.shown, buildings = counts.buildings, neighborhoods = len(hood_ids),
# typical total with utilities and fees = the median shown apartment (years[].medians.all_in; for a neighborhood the median of its units),
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
COUNTED_NOUN = re.compile(r"\b(\d[\d,]*) (?:[a-z]+ )?(apartments?|places?|listings?|buildings?|neighborhoods?|towns?|cities)\b", re.I)
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
        if kind == "hood" and on_page and field in DOOR_FIELDS and src != DOOR_SOURCE and ev.get("transform") != "convention":
            out.append(f"{field} is read from {src}, but it is a door-distance fact: it must be the median over the "
                       f"buildings shown here ({DOOR_SOURCE}), not the area profile ({ev.get('claim', '')[:50]})")
        if src == PAGE + "#units" and (field, agg) in STRIP_OLD and on_page:
            out.append(f"{field} ({agg}) is computed from the unit list; take it from the figure strip "
                       f"({STRIP_SOURCE[kind]}) so the text and the strip cannot differ ({ev.get('claim', '')[:50]})")
    want = {"apartment": "apartments", "place": "apartments", "listing": "apartments", "building": "buildings",
            "neighborhood": "neighborhoods", "town": "neighborhoods", "cities": "neighborhoods", "city": "neighborhoods"}
    for col, text in texts:
        for m in BIG_MONEY.finditer(text):
            if m.group(1) not in strip.get("money", set()):
                out.append(f"{col}: ${m.group(1)} is not a figure of the strip (typical, lowest or highest total with utilities and fees: "
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
                    named = set()                         # an experience text may give a named neighborhood's own minutes
                    if kind == "year":
                        ht = table(PAGE + "#neighborhoods")
                        for h in ht[ht["name"].notna()].itertuples():
                            if str(h.name) in sent:
                                named |= {transform(x, "int") for x in (h.drive_min, h.transit_min) if not is_missing(x)}
                        yr = table(PAGE + "#years")
                        yr = yr[yr["year_label"].astype(str) == str(key)]
                        if len(yr):                       # and the two halves of a split (D12)
                            named |= {transform(yr.iloc[0][c], how) for c in ("far_drive", "close_drive_hi")
                                      for how in ("int", "r5") if not is_missing(yr.iloc[0][c])}
                    for n in PARENT_MIN.findall(sent):
                        if n in named:
                            continue
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


# A text may not begin with a sentence that leans on one that is not there (independent check 5, N16: Ridgewood's
# paragraph opened "9 cafés are close too, and the supermarket is 0.1 miles away."). Every field is shown on its own,
# so its first sentence must stand alone: no "too", "also", "as well", "either" (unless "either ... or"), no opening
# "And" / "But". The builder refuses the same thing after an optional sentence that dropped.
DANGLING = re.compile(r"\btoo(?=[,.;!]|$)|\b(?:also|as well)\b|\beither\b(?![^.]*\bor\b)|^(?:And|But)\b")   # not "too far"


def dangling(text):
    first = (sentences(text.replace("St. ", "St ")) or [""])[0]
    m = DANGLING.search(first)
    return [f"the text opens with a sentence that leans on an earlier one ('{m.group(0)}'): it must stand alone: "
            f"{first[:80]}"] if m else []


# "N of the M buildings here has / have ..." (N17: "1 of the 4 buildings here have their own dog area").
N_OF_M = re.compile(r"\b(\d+) of the (\d+) ([a-z ]+?) (has|have|is|are|lists|list|offers|offer)\b(?: (its|their)\b)?", re.I)
SINGULAR_VERBS = {"has", "is", "lists", "offers"}


def agreement(text):
    """Singular / plural agreement of every "N of the M ... has/have" -> messages."""
    out = []
    for m in N_OF_M.finditer(str(text or "")):
        one = int(m.group(1)) == 1
        verb, poss = m.group(4).lower(), (m.group(5) or "").lower()
        if (verb in SINGULAR_VERBS) != one or (poss and (poss == "its") != one):
            out.append(f"'{m.group(0)}': {'1 ... has its' if one else str(m.group(1)) + ' ... have their'} (agreement)")
    return out


def check_style(kind, col, text):
    out = check_plain(col, text)
    bare = text
    for name in PLACE_NAMES:
        bare = bare.replace(name, "")
    for rx, what in BANNED:          # (dollar amounts are no longer banned by column: check_strip ties each to the strip)
        m = rx.search(bare)
        if m:
            out.append(f"{col}: {what}: '{m.group(0)}'")
    # the one safety wording allowed is a whole icon point of a neighborhood, exactly as written (check_row tests it)
    open_text = "" if (kind == "hood" and col == "point" and text.strip() == SAFEST + ".") else bare
    m = CRIME.search(open_text) or re.search(r"\bsafe\w*", open_text, re.I)
    if m:
        out.append(f"{col}: crime or safety wording '{m.group(0)}' (the open prose is about living there; the one "
                   f"allowed wording is the icon point \"{SAFEST}.\")")
    m = NUMBER_WORDS.search(text)
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
    if col in HEADLINE_COLS[kind] and len(sentences(text)[0]) > HEADLINE_MAX:
        out.append(f"{col}: {len(sentences(text)[0])} characters; the page prints it as a row headline and cuts anything "
                   f"over {HEADLINE_MAX} at a comma, which leaves half a list")
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


# ---------------------------------------------------------------------------------------------------------------
# WHAT THE SHOWN BUILDINGS SUPPLY, AND HOW MANY THERE ARE (independent check 4: D6, D16, D25).
DOG_PLACE = re.compile(r"\bdog (?:park|run)s?\b|\boff-leash\b", re.I)
OWN_DOG = re.compile(r"\b(?:has|have) (?:its|their) own dog (?:area|park|run)s?\b|\bdog area on the property\b", re.I)
SOME_OWN_DOG = re.compile(r"\bsome (?:of these )?buildings (?:here )?have (?:their own dog area|a dog area)|"
                          r"\bwhich buildings have their own dog area", re.I)
NO_OWN_DOG = re.compile(r"\bno (?:building|dog run|dog park) (?:here |is nearby|nearby)?(?:has|is)?\b.*\bdog\b|"
                        r"\bno dog (?:run|park) is (?:nearby|close)\b|\bno building here has\b[^.]*\bdog\b", re.I)
DOG_LAMENT = re.compile(r"\bso you would drive\b|\bis a drive\b|\bare (?:both )?(?:a drive|drives)\b|\bneeds? the car\b|"
                        r"\ba long drive\b|\bmeans a drive\b|\bon the (?:street|sidewalk|leash)\b", re.I)
STREET_CATCH = re.compile(r"\bstreet parking\b|\bstreet spaces?\b|\bparking (?:is|was) (?:very |almost |the )?(?:hard|"
                          r"tough|a problem|difficult|scarce|limited|tight|short|nonexistent|a nightmare|horrendous|"
                          r"frustrating)|\bpark on the street\b|\bovernight (?:street )?parking\b|\bparking spaces? "
                          r"(?:is|are) hard\b|\bask (?:each|every) building\b|\bparking space in writing\b|"
                          r"\bwhere you would park\b|\bask about (?:parking|a garage)\b|\bparking spots? (?:is|are) hard",
                          re.I)
GARAGE_SOLVES = re.compile(r"\bbuilding has its own garage\b|\bevery building (?:shown )?here has a garage\b|"
                           r"\bthe building's garage\b|\beach building's garage\b", re.I)
GARAGE_ADVICE = re.compile(r"\blook for a building with\b|\bfavor buildings with\b|\bask (?:each|every) building "
                           r"(?:about parking|about a (?:garage|reserved)|where you would park|for a (?:garage|parking|"
                           r"guaranteed|reserved)|what parking)|\bask about a garage\b|\brule out any building\b|"
                           r"\bbuilding with its own garage is simpler\b|\bask where you would park\b", re.I)
ONE_APARTMENT = re.compile(r"\bThe apartment (?:in [A-Z][\w .'-]+? |here )?(?:is|costs|has)\b|\bthe apartment here\b|"
                           r"\bOnly 1 apartment\b|\bthe (?:one|only|single) apartment\b")
MANY_APARTMENTS = re.compile(r"\bapartments (?:in [A-Z][\w .'-]+? |here |listed )?(?:are|cost|run|have)\b|"
                             r"\bapartments to (?:choose|compare)\b|\btypical apartment\b|\bevery apartment\b|"
                             r"\beach apartment\b|\bmany apartments\b|\blarge apartments\b|\bsmall apartments\b", re.I)
SEVERAL_BUILDINGS = re.compile(r"\b(?:each|every) building\b(?! shown)|\blook for a building\b|\bfavor buildings\b|"
                               r"\ba building with its own garage is simpler\b|\bbuilding by building\b|\bmany buildings\b", re.I)
NEW_BUILDINGS = re.compile(r"\b(?:apartments|buildings) (?:here |in [A-Z][\w .'-]+? )?are (?:in )?(?:new|newer)\b|"
                           r"\bin (?:new|newer) buildings\b", re.I)
TYPICAL = re.compile(r"\btypical(?:ly)?\b", re.I)
TYPICAL_MIN = 3                       # "typical" needs at least this many apartments behind it
SCOPE_MANY_RX = re.compile(r"\bmost buildings here\b", re.I)


# ---------------------------------------------------------------------------------------------------------------
# INDEPENDENT CHECK 5: three rules on what a neighborhood says, each computed from the SAME field for every sentence.
# (a) QUANTITIES (N15). No two sentences of one neighborhood may give incompatible amounts of the same thing: "There
#     are no bars within a 10-minute walk" beside "Few bars are within a 10-minute walk"; "nothing here is within
#     walking distance" beside "2 cafés are within a 10-minute walk". Each wording is tested against the median of the
#     buildings shown (the figure every count in the text already is): "no X" needs 0, "almost no X" 0 or 1, "few X"
#     1 to 5, "nothing is within walking distance" and "nothing to eat or drink" need no restaurants, bars or cafés.
QTY_THINGS = {"restaurant": "restaurants_800m", "bar": "bars_800m", "café": "cafes_800m", "cafe": "cafes_800m"}
_T = r"(restaurants?|bars?|caf[ée]s?)"
QTY_MILE = re.compile(r"(?:,? and)?(?: only| about)? (?:\d+|no|few) (?:restaurants?|bars?|caf[ée]s? )?(?:are |is )?within 1 mile|"
                      r"[^,;]*\bwithin 1 mile\b[^,;]*", re.I)
QTY_NONE = re.compile(rf"(?<!almost )\bno {_T}(?: or {_T})?\b", re.I)
QTY_ALMOST = re.compile(rf"\balmost no {_T}(?: or {_T})?\b", re.I)
QTY_FEW = re.compile(rf"\bfew {_T}\b", re.I)
QTY_N = re.compile(rf"\b(\d+) {_T}\b", re.I)
QTY_NOTHING = re.compile(r"(?<!almost )\bnothing (?:here |else )?is within (?:walking distance|a 10-minute walk)|"
                         r"(?<!almost )\bnothing to eat or drink is within", re.I)
FEW_MAX = 5


def _thing(word):
    w = word.lower().rstrip("s")
    return QTY_THINGS.get(w)


def quantity_claims(sent):
    """-> [(field, class, words)] with class none | almost | few | some, for restaurants, bars and cafés within a walk."""
    s = QTY_MILE.sub(" ", sent)                           # a count "within 1 mile" is another figure
    out = []
    for rx, cls in ((QTY_NONE, "none"), (QTY_ALMOST, "almost"), (QTY_FEW, "few")):
        for m in rx.finditer(s):
            for g in m.groups():
                if g and _thing(g):
                    out.append((_thing(g), cls, m.group(0)))
    for m in QTY_N.finditer(s):
        out.append((_thing(m.group(2)), "none" if int(m.group(1)) == 0 else "some", m.group(0)))
    m = QTY_NOTHING.search(s)
    if m:
        out += [(f, "none", m.group(0)) for f in ("restaurants_800m", "bars_800m", "cafes_800m")]
    return out


def check_quantities(b, cols):
    out, said = [], {}
    for col, text in cols:
        for sent in sentences(text):
            for field, cls, words in quantity_claims(sent):
                v = _median(b[field].tolist())
                if v is None:
                    continue
                n = int(half_up(v))
                ok = {"none": n == 0, "almost": n <= 1, "few": 1 <= n <= FEW_MAX, "some": n > 0}[cls]
                thing = field.split("_")[0]
                if not ok:
                    out.append(f"{col}: \"{words}\" but the buildings shown have {n} {thing} within a 10-minute walk "
                               f"({'say there are none' if n == 0 else 'give the number'}): {sent[:90]}")
                group = "none" if cls == "none" else "some" if cls in ("few", "some") else None
                if group:
                    other = said.setdefault(field, {}).setdefault(group, (col, sent))
                    clash = said[field].get("some" if group == "none" else "none")
                    if clash and clash[1] != sent:
                        out.append(f"{col}: two sentences give incompatible amounts of {thing}: \"{sent[:70]}\" and "
                                   f"({clash[0]}) \"{clash[1][:70]}\"")
    return list(dict.fromkeys(out))


# (b) THE STATION BY ITS KIND (N3). The nearest station is of any kind now. "train station" and "the train" may be
#     said only where every shown building's nearest station is commuter rail; "subway", "PATH" and "light rail" only
#     where it is that. Where the buildings differ, the words are neutral ("the nearest station").
STATION_SAYS = [("train", re.compile(r"\btrain station\b|\bthe train\b(?! and bus)", re.I)),
                ("subway", re.compile(r"\bsubway\b", re.I)), ("PATH", re.compile(r"\bPATH\b")),
                ("light rail", re.compile(r"\blight rail\b", re.I))]


def station_kind(b):
    vals = sorted(set(str(x) for x in b["train_station_kind"].tolist() if not is_missing(x)))
    return vals[0] if len(vals) == 1 else "mixed" if vals else None


def check_station_words(b, cols):
    out, kind = [], station_kind(b)
    for col, text in cols:
        for sent in sentences(text):
            for says, rx in STATION_SAYS:
                m = rx.search(sent)
                if m and says != kind:
                    out.append(f"{col}: says \"{m.group(0)}\", but the nearest station of the buildings shown is "
                               f"{'of different kinds' if kind == 'mixed' else kind or 'not known'}: name it by its kind: {sent[:90]}")
    return out


# (c) TOLLS THAT DIFFER BY BUILDING (N9). Where the tolls of the buildings shown differ by more than TOLL_SPREAD
#     dollars, a toll sentence gives the range ("about $24 to $43 round trip with a New York E-ZPass").
TOLL_SPREAD = 5
TOLL_ONE = re.compile(r"about \$(\d+) round trip with a New York E-ZPass")
TOLL_RANGE = re.compile(r"about \$(\d+) to \$(\d+) round trip with a New York E-ZPass|up to about \$(\d+) round trip with a New York E-ZPass")


def check_toll_range(key, cols):
    out = []
    try:
        spread = lookup(PAGE + "#neighborhoods", "toll_spread", {"hood_id": key})
        lo, hi = (lookup(PAGE + "#neighborhoods", f, {"hood_id": key}) for f in ("toll_lo", "toll_hi"))
    except LookupError:
        return out
    for col, text in cols:
        for sent in sentences(text):
            wide = not is_missing(spread) and spread > TOLL_SPREAD
            if TOLL_ONE.search(sent) and not TOLL_RANGE.search(sent) and wide:
                out.append(f"{col}: one toll figure, but the tolls of the buildings shown run from ${transform(lo, 'int')} "
                           f"to ${transform(hi, 'int')}: say the range: {sent[:90]}")
            m = TOLL_RANGE.search(sent)
            if m and not wide:
                out.append(f"{col}: a toll range, but the tolls of the buildings shown differ by ${spread}: {sent[:90]}")
    return out


def shown_buildings(hood_id):
    t = table(DOOR_SOURCE)
    return t[t["hood_id"].astype(str) == str(hood_id)]


def check_shown(key, cols, evidence):
    """cols: [(column, text)] of one neighborhood, the icon points as ('point', text) and the catch as ('warning',
    text). Rules, each re-read from the buildings and apartments shown on the page:
      dogs     every shown building has its own dog area -> the text must say so, and may speak of a dog park or dog
               run only as "public"; some do -> the text says "some buildings here have their own dog area" and the
               distance may not be the catch; none does -> free. "No building here has a dog park" needs none to.
      parking  every shown building has a garage -> a sentence about street parking needs the garage said beside it
               somewhere in the row, and advice to "look for a building with a garage" is wrong;
      count    "The apartment ..." needs exactly 1 apartment shown, "the apartments ..." at least 2, "typical" 3;
      scope    with several buildings shown, a lead or scene that gives a door-distance figure says "most buildings
               here"; with one building it must not."""
    out = []
    b = shown_buildings(key)
    if not len(b):
        return out
    nb, n = len(b), int(b["n_units"].sum())
    own, gar = float(b["own_dog_area"].mean()), float(b["own_garage"].mean())
    some_dog = float(b["dog_amenity_any"].mean())         # includes amenities whose kind the data does not give
    every = " ".join(t for _, t in cols)
    catch_cols = {"watch_for", "warning"}
    for col, text in cols:
        for sent in sentences(text):
            dog = DOG_PLACE.search(sent)
            if dog and own == 1 and not OWN_DOG.search(sent) and not re.search(r"\bpublic\b|\btownship\b|\btown park\b|"
                                                                               r"\bcity dog park\b|\btown dog park\b|\bThe Town of\b", sent):
                out.append(f"{col}: every building shown here has its own dog area, so a dog park or dog run may only "
                           f"be mentioned as the public one, never as what the dog has: {sent[:90]}")
            if dog and 0 < some_dog and (col in catch_cols or DOG_LAMENT.search(sent)) and not OWN_DOG.search(sent) \
                    and not SOME_OWN_DOG.search(sent) and not re.search(r"\bpublic\b", sent):
                out.append(f"{col}: {int(round(some_dog * nb))} of the {nb} buildings shown here list a dog amenity of "
                           f"their own, so the distance to a dog park cannot be the catch or a complaint: {sent[:90]}")
            if NO_OWN_DOG.search(sent) and own > 0:
                out.append(f"{col}: says no dog run is here, but {int(round(own * nb))} of the {nb} buildings shown "
                           f"have their own dog area: {sent[:90]}")
            if gar == 1 and GARAGE_ADVICE.search(sent):
                out.append(f"{col}: every building shown here has a garage, so advice to look or ask for one is "
                           f"wrong; say the building's garage solves it: {sent[:90]}")
            if nb == 1 and SEVERAL_BUILDINGS.search(sent):
                out.append(f"{col}: speaks of several buildings, but 1 is shown here (say \"the building\"): {sent[:90]}")
            if NEW_BUILDINGS.search(sent) and not re.search(r"\barea\b|\bdistrict\b|\baround\b|\bhousing\b", sent):
                out.append(f"{col}: says the shown buildings are new on the strength of the area's census profile; "
                           f"word it as the area (\"much of the housing around here is new\"): {sent[:90]}")
            if n >= 2 and ONE_APARTMENT.search(sent):
                out.append(f"{col}: speaks of one apartment, but {n} are shown here: {sent[:90]}")
            if n == 1 and MANY_APARTMENTS.search(sent):
                out.append(f"{col}: speaks of several apartments, but 1 is shown here: {sent[:90]}")
            if n < TYPICAL_MIN and TYPICAL.search(sent) and "Queens" not in sent:
                out.append(f"{col}: 'typical' from {n} apartment{'s' if n != 1 else ''}: give the figure itself: {sent[:90]}")
    if own == 1 and not OWN_DOG.search(every):
        out.append("every building shown here has its own dog area, and the text does not say so "
                   "(\"The building has its own dog area\")")
    if 0 < own < 1 and DOG_PLACE.search(every) and not SOME_OWN_DOG.search(every):
        out.append(f"{int(round(own * nb))} of the {nb} buildings shown have their own dog area, and the text speaks "
                   f"of dog parks without saying \"some buildings here have their own dog area\"")
    if gar == 1 and STREET_CATCH.search(every) and not GARAGE_SOLVES.search(every):
        out.append("every building shown here has a garage: the text raises street parking and never says the "
                   "building's garage solves it")
    out += check_quantities(b, cols) + check_station_words(b, cols) + check_toll_range(key, cols)
    lead_scene = " ".join(t for c, t in cols if c in ("host_intro", "scene"))
    door_numbers = any(ev.get("source_file") == DOOR_SOURCE and ev.get("shown") and ev.get("claim") in
                       sentences(lead_scene.replace("St. ", "St ")) for ev in evidence)
    if nb >= 2 and door_numbers and not SCOPE_MANY_RX.search(lead_scene):
        out.append(f"{nb} buildings are shown here, so a figure measured from the door is the median building's: the "
                   f"lead or the scene must say \"most buildings here\"")
    if nb == 1 and SCOPE_MANY_RX.search(every):
        out.append("says \"most buildings here\", but 1 building is shown")
    return out


# ---------------------------------------------------------------------------------------------------------------
# WHAT AN EXPERIENCE MAY CLAIM (independent check 4: D7, D11, D12). A sentence of an experience that makes one of the
# claims below is tested against the apartments shown in it and against every neighborhood shown under it.
#   (name, pattern, column of #units, test, what it means)   a unit with no value is left out of the share
EXP_CLAIMS = [
    ("close to your parents",
     r"close to your parents|parents are close|without moving far from your parents|(?<!cannot )drop (?:by|in)\b|weeknight visit|close enough for (?:a weeknight|sunday|dinner)|"
     r"stay close to your parents|parents are (?:very )?close|near your parents|easy trip",
     "hood_drive_min", ("<=", CLOSE_DRIVE_MIN)),
    ("no tolls", r"\bno tolls?\b|toll-free|without a toll|nothing to pay on the (?:way|road)", "toll_own", ("==", 0)),
    ("you drive to everything",
     r"drive to (?:almost |nearly )?everything|(?:almost )?nothing (?:is |else is )?within walking distance|every outing "
     r"starts in the car|going out means driving|(?:almost )?no restaurants are within|walking anywhere|"
     r"drive to dinner|dinner[^.]{0,40}all a drive|nearly everything is a drive|drive to nearly everything",
     "restaurants_800m", ("<=", 3)),
    ("you walk to dinner",
     r"walk to dinner|downtown to walk to|walk to a small downtown|dinner[^.]{0,30}(?:on foot|a short walk)|"
     r"short walk away|you walk to dinner", "restaurants_800m", (">=", 4)),
    ("small apartments", r"apartments (?:also )?(?:are|run) small|small apartments|apartment is small|give up is space\b|"
     r"give up space", "sqft", ("<=", 650)),
    ("bigger apartments", r"bigger apartments|more (?:space|room) for you|room for a (?:proper )?desk", "sqft", (">=", 650)),
    ("far from your parents", r"far(?:ther)? from your parents|long drive (?:from|away)|cannot drop in|"
     r"planned trips?|visits become planned|take planning", "hood_drive_min", (">", CLOSE_DRIVE_MIN)),
    ("a longer drive than from Queens", r"longer drive to your parents", "hood_drive_min", (">", 15)),
    ("a garage", r"a garage for the car|park in a garage|garage to return to|simple parking at the building|"
     r"\bgarages?\b(?! or covered)", "garage_or_covered", ("==", 1)),
    ("easy parking", r"parking is easy|easy parking(?! is what you give up)|own parking", "own_parking", ("==", 1)),
    ("a gym", r"\bwith a gym\b|\ba gym,|every building here has a gym|has a gym", "gym", ("==", 1)),
    ("near the water", r"near the water|follow the water|water close by|the water and a park are a short walk",
     "open_water_m", ("<=", 800)),
    ("few bars", r"bars are (?:few|scarce|fewer)|no bars close by|give up is (?:space and )?nightlife|give up nightlife",
     "bars_800m", ("<=", 3)),
    ("houses and lawns", r"houses and lawns|town of houses", "hood_detached", (">=", 0.5)),
    # tested on the buildings that publish a year (about half do); the others are left out of the share
    ("a newer building", r"\bnewer buildings?\b", "year_built", (">=", 2000)),
    # the nearest station is of any kind (N3): "train station" needs commuter rail to be the nearest
    ("a train station", r"\btrain station\b", "station_is_train", ("==", 1)),
]
EXP_CLAIMS = [(n, re.compile(rx, re.I), f, t) for n, rx, f, t in EXP_CLAIMS]
CLAIM_SHARE = 0.75                    # a claim about the experience must hold for this share of its apartments
SPLIT_WORDS = re.compile(r"\bexcept\b|\bapart from\b|\boutside\b|\bmost of these\b|\bthe [A-Z][\w .'-]+? (?:ones?|apartments?)\b|"
                         r"\bones in\b|\bonly in\b|\bin [A-Z][\w .'-]+? (?:only|alone)\b", re.I)
GIVE_UP = re.compile(r"\bgive up\b|\bwhat you give up\b", re.I)       # "what you give up is easy parking" denies the claim
SMALL_BANNED = re.compile(r"\btypical(?:ly)?\b(?! Queens)|\bpercent\b|\bmost\b|\busually\b|\bnearly (?:all|every)\b|\bon average\b|"
                          r"\bmany\b|\bplenty\b", re.I)
PAIR_SCOPE = re.compile(r"\btypical\b|\bmost\b|\bacross\b|\bfrom the others\b|\bfrom most\b", re.I)


@lru_cache(maxsize=None)
def _units_with_hood():
    u = table(PAGE + "#units").copy()
    h = _page()["neighborhoods"]
    drive = {x["id"]: x.get("drive_min") for x in h}
    det = {x["id"]: (x.get("traits") or {}).get("detached_house_share") for x in h}
    u["hood_drive_min"], u["hood_detached"] = u["hood_id"].map(drive), u["hood_id"].map(det)
    u["hood_name"] = u["hood_id"].map({x["id"]: x.get("name") for x in h})
    u["hood_area"] = u["hood_id"].map({x["id"]: x.get("area") for x in h})
    return u


EXCEPTION_BEFORE = re.compile(r"(?:\bexcept|\bapart from|\boutside|\bother than|\bunlike)(?: in| for| from)?(?: the)? (?:[A-Z][\w.'-]+(?:,| and| or)? )*$")


def claim_scope(sent, units):
    """A claim that names some of the experience's neighborhoods or areas ("From Brooklyn and Queens the drive has no
    tolls", "In Westport and Teaneck you drive to dinner") is a claim about those apartments only -> the units it is
    about. A name given as the exception ("except in Newark", "the Newark ones") does not narrow the claim."""
    keep = None
    for col in ("hood_name", "hood_area"):
        for nm in sorted(set(units[col].dropna()), key=len, reverse=True):
            for m in re.finditer(re.escape(str(nm)) + r"\b", sent):
                if EXCEPTION_BEFORE.search(sent[:m.start()]) or re.match(r" (?:ones?|apartments?)\b", sent[m.end():]):
                    continue
                mask = units[col] == nm
                keep = mask if keep is None else (keep | mask)
    return units if keep is None else units[keep]


def claim_share(units, field, test):
    """-> (share of the units with a value that satisfy the test, how many have a value)."""
    vals = [v for v in units[field].tolist() if not is_missing(v)]
    if not vals:
        return None, 0
    return sum(holds(v, list(test)) for v in vals) / len(vals), len(vals)


def check_experience(key, cols, evidence):
    """cols: [(column, text)] of one experience (tagline, subhead, lead, points, moments, promise, catch, subheads).
      share   a claim of EXP_CLAIMS must hold for CLAIM_SHARE of the apartments shown, or its sentence must be worded as
              a split ("Most of these ...; the Newark ones ...", "except Fairfield");
      cards   and for every neighborhood shown under the experience: a neighborhood where the claim fails for most of
              its apartments must be named in the same text (D7: "Almost no restaurants are within a 10-minute walk"
              above a Fairfield card with 8 restaurants). A sentence that itself says "most", "usually",
              "often" or "typical" passes when the claim holds for MOST_SHARE (60%) of the apartments, and a
              sentence that names places ("From Brooklyn and Queens ...") is tested on those places only;
      small   an experience with fewer than SMALL_EXPERIENCE apartments is a short note: it names each of its
              neighborhoods and uses no "typical", no percentage, no "most", "usually", "many" (D11);
      pairs   a text that gives a named neighborhood's own figure may give another figure only in a sentence that
              says whose it is (D12: Jamaica's 3-minute drive beside the experience's 65-minute train)."""
    out = []
    u = _units_with_hood()
    u = u[u["year_label"].astype(str) == str(key)]
    if not len(u):
        return out
    small = len(u) < SMALL_EXPERIENCE
    names = sorted(set(u["hood_name"].dropna()))
    every = " ".join(t for _, t in cols)
    if small:
        for col, text in cols:
            m = SMALL_BANNED.search(text)
            if m:
                out.append(f"{col}: '{m.group(0)}' in an experience with {len(u)} apartments: name the apartments "
                           f"and neighborhoods and give each one's own figure: {text[:90]}")
        for nm in names:
            if nm not in every:
                out.append(f"an experience with {len(u)} apartments must name each neighborhood it shows; "
                           f"'{nm}' is not in the text")
    for col, text in cols:
        for sent in sentences(text):
            for name, rx, field, test in EXP_CLAIMS:
                m = rx.search(sent)
                if not m or field not in u.columns:
                    continue
                if GIVE_UP.search(sent) and name in ("easy parking", "a garage", "you walk to dinner", "bigger apartments",
                                                     "close to your parents"):
                    continue                              # the sentence says she gives this up
                if name == "a garage" and re.search(r"\bpercent\b|\bask\b|\bnot list\b|\bno garage\b|\bwithout a garage\b", sent):
                    continue                              # a share, a question or a denial, not the claim
                about = claim_scope(sent, u)              # the apartments the sentence is about
                share, known = claim_share(about, field, test)
                if share is None:
                    continue
                failing = []
                for nm, g in about.groupby("hood_name"):
                    sh, k = claim_share(g, field, test)
                    if sh is not None and sh < 0.5:
                        failing.append(nm)
                named = [nm for nm in failing if nm in text]
                where = f"{sent[:90]}"
                if failing and len(named) == len(failing) and SPLIT_WORDS.search(text):
                    continue                              # worded as a split, every exception named
                if not small and QUANTIFIED.search(sent) and share >= MOST_SHARE:
                    continue                              # "most of these ...": true of a clear majority, and said so
                if share < CLAIM_SHARE:
                    out.append(f"{col}: \"{m.group(0)}\" ({name}) holds for {share:.0%} of the {known} apartments shown "
                               f"with a value (under {CLAIM_SHARE:.0%}): word it as a split, naming {failing[:6]}: {where}")
                elif failing:
                    out.append(f"{col}: \"{m.group(0)}\" ({name}) is contradicted by the neighborhood card(s) shown "
                               f"under this experience: {failing[:8]}; say \"except ...\" or drop the claim: {where}")
    # tolls (N9): one figure for a group whose tolls differ by more than TOLL_SPREAD dollars must be a range
    yt = table(PAGE + "#years")
    yt = yt[yt["year_label"].astype(str) == str(key)]
    spreads = {"toll_round_trip": "toll_spread", "far_toll": "far_toll_spread", "close_toll": "close_toll_spread"}
    for col, text in cols:
        for sent in sentences(text):
            if not TOLL_ONE.search(sent) or TOLL_RANGE.search(sent) or not len(yt):
                continue
            for ev in evidence:
                if ev.get("claim") != sent or not ev.get("shown"):
                    continue
                f = spreads.get(ev.get("field")) if str(ev.get("source_file")) == PAGE + "#years" else None
                sp = yt.iloc[0][f] if f else None
                if str(ev.get("source_file")) == PAGE + "#neighborhoods" and ev.get("field") == "toll_round_trip":
                    try:
                        sp = lookup(PAGE + "#neighborhoods", "toll_spread", ev.get("row", {}))
                    except LookupError:
                        sp = None
                if not is_missing(sp) and sp > TOLL_SPREAD:
                    out.append(f"{col}: one toll figure for apartments whose tolls differ by ${sp:.0f}: say the range "
                               f"(\"about $A to $B round trip with a New York E-ZPass\"): {sent[:90]}")
                    break
    # pairs
    for col, text in cols:
        sents = sentences(text)
        named_fig = [s for s in sents if any(ev.get("claim") == s and ev.get("field") in ("nearest_drive_min",)
                                             and ev.get("shown") for ev in evidence)]
        if not named_fig:
            continue
        for s2 in sents:
            if s2 in named_fig:
                continue
            if any(ev.get("claim") == s2 and ev.get("shown") and ev.get("transform") not in ("convention",)
                   and ev.get("field") in ("transit_min", "drive_min") for ev in evidence) and not PAIR_SCOPE.search(s2) \
                    and not any(nm in s2 for nm in names):
                out.append(f"{col}: a named neighborhood's figure sits beside a figure for the whole experience with "
                           f"nothing saying whose it is: {s2[:90]}")
    return out


MOST_SHARE = 0.6                      # a sentence that says "most", "usually", "often", "typical" needs this share
QUANTIFIED = re.compile(r"\bmost(?:ly)?\b|\bmany\b|\boften\b|\busually\b|\btypical(?:ly)?\b|\bnearly (?:all|every)\b", re.I)


# ---------------------------------------------------------------------------------------------------------------
# "AT A GLANCE" (independent check 4, D16). The facts the neighborhood page prints beside the text, computed here
# from the buildings shown, so the text and the row cannot disagree. Written to scene_text_neighborhoods.csv as
# glance_json; scripts/page_data_extras.py attaches it as neighborhoods[].at_a_glance and the page prints it in
# place of the area profile (traits).
WALK_M_PER_MIN = 80                   # the page's own conversion (site/index.html)


def _dist_words(m):
    """The page's distShort(): a walk in minutes up to 1,600 m, miles beyond."""
    if is_missing(m):
        return None
    if m <= 1600:
        return f"{max(1, int(half_up(m / WALK_M_PER_MIN)))} min walk"
    mi = m / 1609.34
    return f"{half_up(mi, 0.1):.1f} miles" if mi < 3 else f"{int(half_up(mi))} miles"


def _miles_words(m):
    """A distance in miles as measured: one decimal under 3 miles (never below 0.1), whole miles beyond."""
    mi = m / 1609.34
    return f"{max(0.1, half_up(mi, 0.1)):.1f} miles" if mi < 3 else f"{int(half_up(mi))} miles"


STATION_LABEL = {"train": "to the train", "subway": "to the subway", "PATH": "to PATH", "light rail": "to light rail",
                 "mixed": "to the nearest station"}


def _count_words(n, one):
    n = int(half_up(n))
    return f"{n} {one if n == 1 else one + 's'}"


def glance(hood_id):
    """-> the "At a glance" facts of a neighborhood with apartments on the page ([] otherwise). Each fact:
         key      food | park | dog | supermarket | train_station | garage
                  (train_station also carries kind = train | subway | PATH | light rail | mixed, kinds {kind: buildings},
                  station (the name, where the shown buildings share one), stations [names], and, where the nearest
                  station is not commuter rail, commuter_station_m / _text / _label)
         icon     the page's icon name
         text     the bold words ("66 restaurants, 8 bars"), ready to print
         label    the small words after them, scope included ("within a 10-minute walk of most buildings here")
         value    the number behind `text` (median over the shown buildings), unit: count | minutes | meters | share
         scope    "this building" (1 building shown) | "most buildings here" (2 or more: the median building)
         buildings   how many shown buildings the figure rests on;  range [lowest, highest] over them
       Area-wide facts (the town's parking rule, the trip to her parents by train and bus) stay with the page: they
       are the neighborhood's own fields and are true of every building in it."""
    b = shown_buildings(hood_id)
    if not len(b):
        return []
    nb = len(b)
    many = nb >= 2
    scope = "most buildings here" if many else "this building"
    def med(col):
        v = pd.to_numeric(b[col], errors="coerce").dropna()
        return (float(v.median()), [plain(float(v.min())), plain(float(v.max()))], int(len(v))) if len(v) else (None, None, 0)
    out = []
    def add(key, icon, text, label, value, unit, rng, k, **more):
        out.append({"key": key, "icon": icon, "text": text, "label": label, "value": plain(value), "unit": unit,
                    "scope": scope, "buildings": k, "range": rng, **more})
    r, rr, k = med("restaurants_800m")
    if r is not None:
        bars, br, _ = med("bars_800m")
        text = _count_words(r, "restaurant") + (", " + _count_words(bars, "bar") if bars is not None and half_up(bars) > 0 else "")
        add("food", "fork", text, "within a 10-minute walk" + (" of most buildings here" if many else ""), r, "count", rr, k,
            bars=plain(bars), bars_range=br)
    p, pr_, k = med("park_walk_min")
    if p is not None:
        add("park", "park", f"{max(1, int(half_up(p)))} min walk", "to a park" + (" from most buildings here" if many else ""),
            p, "minutes", pr_, k)
    dg, dr, k = med("dog_park_m")
    own = float(b["own_dog_area"].mean())
    public = _dist_words(dg)
    if own == 1:
        add("dog", "dog", "Own dog area", ("at every building here" if many else "at the building")
            + (f"; the nearest public dog park is {public} away" if public else ""), 1.0, "share", [1.0, 1.0], nb,
            own_dog_area="all", public_dog_park_m=plain(dg), public_dog_park_text=public)
    elif own > 0:
        add("dog", "dog", public or "Ask", "to the public dog park" + (" from most buildings here" if many else "")
            + f"; {int(round(own * nb))} of the {nb} buildings here "
            + ("has its" if int(round(own * nb)) == 1 else "have their") + " own dog area", dg, "meters", dr, k,
            own_dog_area="some", own_dog_area_buildings=int(round(own * nb)), public_dog_park_m=plain(dg),
            public_dog_park_text=public)
    elif dg is not None:
        add("dog", "dog", public, "to the dog park" + (" from most buildings here" if many else ""), dg, "meters", dr, k,
            own_dog_area="none", public_dog_park_m=plain(dg), public_dog_park_text=public)
    sm, sr, k = med("supermarket_m")
    if sm is not None:
        add("supermarket", "bag", _dist_words(sm), "to a supermarket" + (" from most buildings here" if many else ""),
            sm, "meters", sr, k)
    tr, trr, k = med("train_station_m")
    if tr is not None:
        # The nearest station, named by its kind (N3). `kind` is the one every shown building shares, "mixed" where
        # they differ; `station` is the name where they share one. The distance is in miles as measured: no walking
        # time to a station is in the data.
        kind = station_kind(b) or "mixed"
        names = sorted(set(str(x) for x in b["train_station"].tolist() if not is_missing(x)))
        station = names[0] if len(names) == 1 else None
        kinds = {str(kk): int(v) for kk, v in b["train_station_kind"].dropna().astype(str).value_counts().sort_index().items()}
        label = STATION_LABEL.get(kind, "to the nearest station") + (f" ({station})" if station and kind != "mixed" else "")
        more = {"kind": kind, "kinds": kinds, "station": station, "stations": names}
        cm, cr, ck = med("commuter_station_m")
        if kind != "train" and cm is not None:            # the nearest commuter-rail station, where that is another one
            more.update({"commuter_station_m": plain(cm), "commuter_station_text": _miles_words(cm),
                         "commuter_station_label": "to the nearest commuter train station"})
        add("train_station", "train", _miles_words(tr), label + (" from most buildings here" if many else ""),
            tr, "meters", trr, k, **more)
    gar = float(b["own_garage"].mean())
    if gar > 0:
        ng = int(round(gar * nb))
        add("garage", "parking", "Garage", ("at the building" if not many else "at every building here" if gar == 1
                                              else f"at {ng} of the {nb} buildings here"), gar, "share", None, nb,
            own_garage="all" if gar == 1 else "some", own_garage_buildings=ng)
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
    joined = " ".join(list(texts.values()) + [t for _, t in extra])
    if SAFEST_OLD.search(joined):
        # D27 / N13: at most the lowest tenth by violent rate, as an icon point of its own, never without a rate
        if kind != "hood":
            problems.append(f"'{SAFEST}' is a neighborhood's icon point; an experience does not say it")
        elif not backed(SAFEST_FIELD, ("<=", "<"), SAFEST_MAX):
            problems.append(f"'{SAFEST}' needs a test that the neighborhood is in the lowest tenth by violent rate "
                            f"({SAFEST_FIELD} <= {SAFEST_MAX})")
        if len(SAFEST_OLD.findall(joined)) > 1:
            problems.append(f"'{SAFEST}' is said more than once")
        if kind == "hood":
            try:
                if not lookup(PAGE + "#neighborhoods", "safety_published", {"hood_id": key}):
                    problems.append(f"'{SAFEST}' where no crime rate is published for the neighborhood (safety.status "
                                    f"is not_published): nothing may be said about safety here")
                pct = lookup(PAGE + "#neighborhoods", SAFEST_FIELD, {"hood_id": key})
                if is_missing(pct) or pct > SAFEST_MAX:
                    problems.append(f"'{SAFEST}' but the neighborhood is not in the lowest tenth by violent rate "
                                    f"among those shown ({SAFEST_FIELD} = {pct})")
            except LookupError:
                problems.append(f"'{SAFEST}' on a neighborhood that is not on the page")
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
        problems += [f"{col}: {p}" for p in dangling(text) + agreement(text)]
        for n in numbers_in(text):
            if n not in allowed:
                problems.append(f"{col}: number '{n}' has no evidence item: {text[:60]}")
    shown_cols = [(c, t) for c, t in list(texts.items()) + extra
                  if not (kind == "year" and c in ("scene", "host_walkthrough"))]     # those two repeat the moments
    problems += check_strip(kind, key, shown_cols, evidence)
    claim_cols = [(c, t) for c, t in shown_cols if c != "display_label" and t.strip()]
    if kind == "hood":
        warn = [str(p.get("text", "")) for p in points if p.get("icon") == "warning"]
        claim_cols = [(c, t) for c, t in claim_cols if not (c == "point" and t in warn)] + [("warning", t) for t in warn]
        problems += check_shown(key, claim_cols, evidence)
    else:
        problems += check_experience(key, claim_cols, evidence)
    for run in shared_runs({"lead": [texts.get("host_intro", "")], "points": [p.get("text", "") for p in points],
                            "moments": [m.get("text", "") for m in moments],
                            "promise": [texts.get("promise", "")], "catch": [texts.get("catch", "")]}):
        problems.append(f"the lead, the points and the moments repeat each other: '{run}'")
    return problems, drift


# Fixed wordings that every text may use: the toll sentence and the units of the crime figures.
REQUIRED_PHRASE = re.compile(r"about \$?# to \$?# round trip with a new york e-zpass(?:, depending on the building)?|"
                             r"about \$?# round trip with a new york e-zpass|per # residents|per #|against jamaica's #")
OPENING_WORDS, OPENING_MAX = 3, 8        # at most 8 texts may start with the same 3 words
RUN_WORDS, RUN_SHARE, RUN_FLOOR = 6, 0.25, 8   # no run of 6 words in more than a quarter of the texts (never fewer than 8)


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
SUB_SHARE = 0.12                                            # a section subhead on fewer than 6% of the neighborhoods


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


def main(argv=None):
    _options(argv, "Re-test the scene text against the current data.")
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
                if kind == "hood":                        # "At a glance" must be the shown buildings' figures, as of now
                    try:
                        have = json.loads(r.get("glance_json") or "null")
                    except json.JSONDecodeError:
                        have = None
                    want = json.loads(json.dumps(glance(r[key])))
                    if have != want:
                        problems.append("glance_json is missing or no longer equals the figures of the buildings "
                                        "shown (rebuild: python3 scripts/build_scene_text.py)")
                    for g in want or []:
                        problems += [f"glance_json [{g.get('key')}]: {p}" for p in agreement(f"{g.get('text')} {g.get('label')}")]
                for p in problems:
                    print(f"FAIL {r[key]}: {p}")
                for d in drift:
                    print(f"drift {r[key]}: {d}")
                fails += bool(problems)
                drifts += bool(drift)
                host[r[key]] = r["host_intro"]
                seen.append(r)
                r["evidence"] = evidence
        across = check_repetition("host_intro", host) + ([] if SUBSET else check_sub_shares(kind, seen))
        if kind == "hood":
            across += ([] if SUBSET else check_closings("host_intro", host)) + check_leads(seen)
            n_drive = sum(ends_on_drive(t) for t in host.values())
            print(f"host_intro closes: {n_drive} of {len(host)} end on the drive, the toll or transit")
        for p in across:
            print(f"FAIL {kind} texts: {p}")
            fails += 1
    print(f"{rows} rows checked, {fails} failing, {drifts} with drift only")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
