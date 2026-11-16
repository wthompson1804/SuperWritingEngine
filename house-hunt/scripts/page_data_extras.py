"""Add the pieces built alongside the pipeline to site/data.json.

Run after scripts/build_page_data.py and before scripts/build_site.py:

    python3 scripts/page_data_extras.py            add the extras, print a report and the shape check
    python3 scripts/page_data_extras.py --strict   the same, exit 1 when the shape check finds anything
    python3 scripts/page_data_extras.py --dry-run  report only, write nothing
    python3 scripts/page_data_extras.py --root DIR use DIR/site/data.json and DIR/data/... (tests)

Idempotent: a second run changes nothing, and the file is not rewritten when nothing changed. Every block owns its
fields: when its input is read, the block first clears what it wrote before and then writes again, so a row that left
a CSV also leaves the page. When an input is absent or half-written (read twice, RETRY_WAIT seconds apart) the block
is skipped with a message and whatever an earlier run attached stays in place. Extra columns are ignored; a missing
optional column reads as empty; a missing required column skips the block.

Blocks, in the order main() runs them (each is one function, its docstring gives the input, the fields and the rule):

   1 experience_text     data/reference/scene_text_years.csv
   2 neighborhood_text   data/reference/scene_text_neighborhoods.csv
   3 round2_quotes       data/voices/neighborhood_quotes_round2.csv, data/voices/quote_exclusions.csv
   4 round2_survey       data/voices/neighborhood_survey_round2.csv
   5 round2_rules        data/reference/local_rules_round2.csv
   6 nyc_rules           (the page data itself; after 5, because round 2 can add New York City rules)
   7 contacts            data/reference/building_contacts.csv, building_contacts_own_site.csv
   8 about_building      data/reference/building_about.csv
   9 realtor_lines       data/reference/realtor_lines.csv
  10 ratings             data/evidence/ratings_census.csv
  11 descriptions        data/reference/neighborhood_descriptions_round2.csv, neighborhood_descriptions.csv
  12 quote_screen        (the page data itself; after 3, it screens every resident quote on the page)
  13 coordinates         data/ranked_units.csv
  14 ranking             (the page data itself: each building's best rank score)
  15 display_labels      (the page data itself; after 1, so a label written in the CSV is kept)
  16 photos              data/reference/building_contacts_own_site.csv (after 7: it reads contact.site and contact.kind)
  then: JSON-safe pass (NaN, infinity and "nan"-like strings become null), shape check, atomic write.

Fields written, per object type (names are the page template's; do not rename):

  object          field                                      block  value
  --------------  -----------------------------------------  -----  ------------------------------------------------
  meta            extras                                     main   {block: one-line result}; state, never a delta
  years[]         prose {scene, promise, catch}                1    text
                  host {intro, walkthrough[]}                  1    text, list of paragraphs
                  about_points[], day_moments[]                1    lists of {icon, text} / {icon, title, text}
                  tagline, subhead, subhead_original           1    text (subhead_original keeps the builder's subhead)
                  headlines.<key>.subhead                      1    text, one per sub_<key> column
                  display_label                               1,15  text ("... Experience")
                  hood_ids                                     14   reordered: best neighborhood first
  neighborhoods[] prose {scene, good_for_her, watch_for}       2    text; plus {about, inherited_from} when the text
                                                                    is the whole city's (a split city's child)
                  host {intro}, about_points[], tagline,       2    as for years (own rows only, never inherited)
                  subhead, subhead_original, headlines.*
                  local.voices[] {excerpt, theme, sentiment,   3    appended rows carry round: 2
                    context, source, date, url, source_area,
                    about, round}
                  local.voices (filtered)                      12   rows naming a group are removed
                  local.survey[] {measure, value, source,      4    appended rows carry round: 2; value is text
                    as_of, url, source_area, about, round}
                  local.parking_rules[], local.dog_rules[]     5    appended rows carry round: 2
                    {rule, summary, quote, url, municipality,
                    about, round}
                  local.parking_rules[], local.dog_rules[]     6    citywide New York City rows copied in carry
                                                                    copied: true
                  described[] {quote, source, url, about,      11   at most three
                    topic, licence}
                  lat, lon                                     13   numbers, five decimals
                  experience_score                             14   number, one decimal, or null
                  experience_score_basis                       14   text or null
                  rank_in_experience                           14   integer 1..N inside its experience
                  single_building                              14   true, only when the score rests on one building
  units[] and     contact {phone, hours, site, kind, note,     7    phone is null for a broker or an individual owner
  buildings[]       source}
                  about_building                               8    text
                  about_points[]                               8    list of {icon, text} or null
                  ratings {platforms[] {platform, rating,      10   rating is a number 0-5, count an integer or null;
                    count, seen_via, url, as_of},                   most_reviews integer; searched, found_any booleans
                    most_reviews, searched, found_any}
                  photos {url, where, kind}                    16   kind is "own_site" or "listing"
  units[] only    host {line, catch}                           9    text; catch may be null
                  headlines.<key>.subhead                      9    text, one per sub_<key> column

Not touched: everything scripts/build_page_data.py computes (experience medians, ranges, drive_min_range_hoods, the
units' costs, disclosures, parking and evidence fields). This script reads none of the renamed pipeline fields
(disclosure names, parking type, pet-rent lines, review verdicts).

Nothing here is invented: every row attached comes from a CSV that carries its own source, and a quote, description
or rule without a link is not attached.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parsers  # noqa: E402  (plain regex rules, no network; shared with build_page_data.py)

ROOT = Path(__file__).resolve().parent.parent
RETRY_WAIT = 0.5          # seconds before the second and last attempt at an input that is absent or half-written
YES = {"yes", "true", "1"}
NAN_LIKE = {"nan", "none", "null", "nat", "<na>", "n/a", "#n/a"}


# ----------------------------------------------------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------------------------------------------------
class Paths:
    """Every file the script touches, under one root (the house-hunt folder; a temp folder in the tests)."""

    def __init__(self, root=ROOT, data_json=None):
        root = Path(root)
        ref, voices = root / "data" / "reference", root / "data" / "voices"
        self.root = root
        self.data_json = Path(data_json) if data_json else root / "site" / "data.json"
        self.scene_years = ref / "scene_text_years.csv"
        self.scene_hoods = ref / "scene_text_neighborhoods.csv"
        self.quotes2 = voices / "neighborhood_quotes_round2.csv"
        self.quote_exclusions = voices / "quote_exclusions.csv"
        self.survey2 = voices / "neighborhood_survey_round2.csv"
        self.rules2 = ref / "local_rules_round2.csv"
        self.contacts = ref / "building_contacts.csv"
        self.contacts_own = ref / "building_contacts_own_site.csv"
        self.building_about = ref / "building_about.csv"
        self.realtor_lines = ref / "realtor_lines.csv"
        self.ratings = root / "data" / "evidence" / "ratings_census.csv"
        self.descriptions2 = ref / "neighborhood_descriptions_round2.csv"
        self.descriptions1 = ref / "neighborhood_descriptions.csv"
        self.ranked_units = root / "data" / "ranked_units.csv"

    def rel(self, p):
        try:
            return str(Path(p).relative_to(self.root))
        except ValueError:
            return str(p)


# ----------------------------------------------------------------------------------------------------------------------
# Shared helpers: JSON-safe values and safe reading
# ----------------------------------------------------------------------------------------------------------------------
def clean(x) -> str:
    """A CSV cell as text: stripped; empty for None, NaN and the strings pandas or Python print for a missing value."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    s = str(x).strip()
    return "" if s.lower() in NAN_LIKE else s


def none_if_blank(x):
    return clean(x) or None


def number(x):
    """A finite float, or None."""
    try:
        f = float(clean(x).replace(",", ""))
    except ValueError:
        return None
    return f if math.isfinite(f) else None


def whole_number(x):
    """A non-negative integer from '12', '12.0' or '1,234'; None for anything else (including '12.5' and '-3')."""
    f = number(x)
    return int(f) if f is not None and f >= 0 and f == int(f) else None


def letters(t) -> str:
    return re.sub(r"[^a-z]", "", str(t or "").lower())


def squash(t) -> str:
    """Text reduced to letters and digits, for comparing two quotes."""
    return re.sub(r"[^a-z0-9]", "", str(t or "").lower())


def json_safe(o):
    """(a copy of o that is valid, honest JSON, how many values were changed): NaN and infinity become null, and so do
    strings that are only a printed missing value ("nan", "None", "null")."""
    n = 0

    def walk(v):
        nonlocal n
        if isinstance(v, dict):
            return {str(k): walk(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [walk(x) for x in v]
        if isinstance(v, bool) or v is None or isinstance(v, int):
            return v
        if isinstance(v, float):
            if math.isfinite(v):
                return v
            n += 1
            return None
        if isinstance(v, str):
            if v.strip().lower() in NAN_LIKE - {"n/a", "#n/a"}:
                n += 1
                return None
            return v
        if hasattr(v, "item"):                       # a numpy scalar that slipped in
            return walk(v.item())
        n += 1
        return str(v)
    return walk(o), n


def json_cell(text, kind=list):
    """A JSON cell of a CSV as a value of the wanted kind, made JSON-safe; None when empty, broken or another kind."""
    text = clean(text)
    if not text:
        return None

    def no_constants(name):
        raise ValueError(name)
    try:
        v = json.loads(text, parse_constant=no_constants)
    except ValueError:
        return None
    if not isinstance(v, kind) or not v:
        return None
    return json_safe(v)[0]


class Row(dict):
    """A CSV row; a column the file does not have reads as empty."""

    def __missing__(self, key):
        return ""


class Table(list):
    """Rows of a CSV plus the set of columns the file really has."""
    columns: frozenset = frozenset()


def read_csv(path, need=(), wait=None):
    """(Table, None), or (None, reason) when the file is absent, half-written or lacks a required column.

    Read as text, every cell cleaned (see clean). A file that fails to parse, is empty, has a quoted field that never
    closes, or does not end with a line break (the sign of a writer still at work) is read once more after `wait`
    seconds; it is accepted then only when it parses, every quote closes, and, if it still has no final line break,
    its last row is whole and it did not change in between."""
    path = Path(path)
    wait = RETRY_WAIT if wait is None else wait
    first, reason = None, "missing"
    for attempt in (1, 2):
        if attempt == 2 and wait:
            time.sleep(wait)
        try:
            raw = path.read_bytes()
        except OSError:
            reason = "missing"
            continue
        try:
            text = raw.decode("utf-8-sig")
            if not text.strip():
                raise ValueError("empty file")
            df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
        except Exception as e:               # pandas raises several unrelated types for a truncated file
            reason = f"unreadable ({type(e).__name__}: {str(e)[:80]}), probably half-written"
            first = raw
            continue
        if text.count('"') % 2:
            reason, first = "a quoted field never closes: half-written", raw
            continue
        if not text.endswith("\n"):
            last = text.rsplit("\n", 1)[-1]
            short = last.count('"') % 2 == 0 and len(next(csv.reader([last]), [])) < len(df.columns)
            if short or attempt == 1 or raw != first:
                reason, first = ("the last row is cut short: half-written" if short else "no final line break and still changing: half-written"), raw
                continue
        missing = [c for c in need if c not in df.columns]
        if missing:
            return None, "no column " + ", ".join(missing)
        df = df.fillna("")
        cols = [str(c) for c in df.columns]
        out = Table(Row(zip(cols, (clean(v) for v in rec))) for rec in df.itertuples(index=False, name=None))
        out.columns = frozenset(cols)
        return out, None
    return None, reason


def read_json(path, wait=None):
    """(data, None) or (None, reason); read once more after `wait` seconds when it does not parse."""
    wait = RETRY_WAIT if wait is None else wait
    reason = "missing"
    for attempt in (1, 2):
        if attempt == 2 and wait:
            time.sleep(wait)
        try:
            return json.loads(Path(path).read_text(encoding="utf-8")), None
        except OSError:
            reason = "missing"
        except ValueError as e:
            reason = f"not valid JSON ({str(e)[:60]}), probably half-written"
    return None, reason


def dump(d) -> str:
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


# ----------------------------------------------------------------------------------------------------------------------
# Context: the page data, its indexes, the report
# ----------------------------------------------------------------------------------------------------------------------
PART_FILLER = re.compile(r"\(.*?\)|\b(?:as a whole|whole|enclosing area|city of|city|town|the|nj|ny|ct|new jersey|new york|connecticut|usa?)\b", re.I)


class Ctx:
    def __init__(self, d, paths, wait=None):
        self.d, self.P, self.wait = d, paths, wait
        for key in ("years", "neighborhoods", "units"):
            if not isinstance(d.get(key), list):
                d[key] = []
        self.years = [y for y in d["years"] if isinstance(y, dict)]
        self.units = [u for u in d["units"] if isinstance(u, dict)]
        self.buildings = [b for b in d.get("buildings") or [] if isinstance(b, dict) and b.get("id")]
        self.places = self.units + self.buildings      # what the per-building blocks write on: every unit and every building
        self.hoods = {h["id"]: h for h in d["neighborhoods"] if isinstance(h, dict) and h.get("id")}
        self.kids = {}
        for h in self.hoods.values():
            if h.get("parent_id"):
                self.kids.setdefault(h["parent_id"], []).append(h)
        self.rep = {}        # block -> result, stored in meta.extras; describes the state, so a rerun writes the same
        self.said = []       # passing remarks for the console only

    def csv(self, path, need=()):
        rows, why = read_csv(path, need, self.wait)
        return rows, (None if rows is not None else f"skipped: {self.P.rel(path)} {why}")

    def targets(self, hood_id, source_area=""):
        """Where content keyed on hood_id goes on the page: [(neighborhood, about)].

        A neighborhood on the page: itself, about None. A split city's id (Jersey City: only its children are on the
        page): the children the source area names, about None; when the source area is the city itself or is empty,
        every child, about "<City> as a whole"; when it names some other part of the city (one that is not on the
        page), nowhere. Any other id: nowhere."""
        if hood_id in self.hoods:
            return [(self.hoods[hood_id], None)]
        kids = self.kids.get(hood_id) or []
        if not kids:
            return []
        city = letters(kids[0].get("parent_name"))
        area = letters(source_area)
        rest = area.replace(city, "") if city else area
        named = []
        for k in kids:
            name = letters(k.get("short_name"))
            bare = letters(re.sub(r"^the\s+", "", str(k.get("short_name") or ""), flags=re.I))
            if name and (name in area or (bare and bare in rest)):
                named.append(k)
        if named:
            return [(k, None) for k in named]
        own_name = re.escape(str(kids[0].get("parent_name") or "\0"))
        left = letters(PART_FILLER.sub(" ", re.sub(own_name, " ", str(source_area or ""), flags=re.I)))
        if left:
            return []                                     # about a part of the city that has no page of its own
        return [(k, f"{k.get('parent_name')} as a whole") for k in kids]


def building_id_of(o):
    """A unit's building_id; a buildings[] entry's own id."""
    return o.get("building_id") or o.get("id")


def counted(c, test):
    """'N of M places, N of M buildings' for the objects that pass test."""
    u, b = sum(1 for o in c.units if test(o)), sum(1 for o in c.buildings if test(o))
    return f"{u} of {len(c.units)} places" + (f", {b} of {len(c.buildings)} buildings" if c.buildings else "")


def local_of(h):
    lo = h.get("local")
    if not isinstance(lo, dict):
        lo = h["local"] = {}
    return lo


def area_key(t):
    t = re.sub(r",\s*[A-Z]{2}$", "", str(t).strip())
    return re.sub(r"\b(township|city of|city|town|village|borough)\b|\(.*?\)|[^a-z]", "", t.lower())


def verified(rows):
    """Rows marked verified, when the file has that column; every row when it does not."""
    return [r for r in rows if r["verified"].lower() in YES] if "verified" in rows.columns else list(rows)


# ----------------------------------------------------------------------------------------------------------------------
# 1, 2. Scene text
# ----------------------------------------------------------------------------------------------------------------------
TEXT_FIELDS = ("prose", "host", "about_points", "day_moments", "tagline", "headlines")


def clear_text_fields(obj, also=()):
    for k in TEXT_FIELDS + tuple(also):
        obj.pop(k, None)
    if "subhead_original" in obj:
        obj["subhead"] = obj.pop("subhead_original")


def apply_text_fields(obj, r):
    """The written fields of one scene-text row (scripts/build_scene_text.py) onto a year or a neighborhood: host.intro,
    host.walkthrough (paragraphs), about_points, day_moments, tagline, display_label, subhead (the builder's own is kept
    as subhead_original) and one headlines.<key>.subhead per sub_<key> column. Empty cells write nothing."""
    host = {}
    if r["host_intro"]:
        host["intro"] = r["host_intro"]
    paras = [x.strip() for x in r["host_walkthrough"].split("\n\n") if x.strip()]
    if paras:
        host["walkthrough"] = paras
    if host:
        obj["host"] = host
    for col, key in (("about_points_json", "about_points"), ("day_moments_json", "day_moments")):
        v = json_cell(r[col], list)
        if v:
            obj[key] = v
    for c in ("tagline", "display_label"):
        if r[c]:
            obj[c] = r[c]
    if r["subhead"]:
        obj["subhead_original"] = obj.get("subhead")
        obj["subhead"] = r["subhead"]
    heads = {k[4:]: {"subhead": v} for k, v in r.items() if k.startswith("sub_") and len(k) > 4 and v}
    if heads:
        obj["headlines"] = heads


def label_key(t):
    """'The Quiet-Street Year' and 'The Quiet-Street Experience' are the same experience."""
    return re.sub(r"\s+(year|experience)$", "", clean(t).lower())


def experience_text(c):
    """Input: data/reference/scene_text_years.csv (needs year_label, scene).
    Writes on years[]: prose {scene, promise, catch} and the fields of apply_text_fields.
    Rule: a row belongs to the experience whose label, display label or id it names (" Year" and " Experience" read the
    same); a row with an empty scene attaches nothing; an experience with no row carries none of these fields."""
    rows, skip = c.csv(c.P.scene_years, need=("year_label", "scene"))
    if skip:
        return skip
    by = {label_key(r["year_label"]): r for r in rows if r["scene"]}
    n = 0
    for y in c.years:
        clear_text_fields(y, also=("display_label",))
        r = next((by[k] for k in map(label_key, (y.get("label"), y.get("id"))) if k and k in by), None)
        if r is None:
            continue
        y["prose"] = {"scene": r["scene"], "promise": none_if_blank(r["promise"]), "catch": none_if_blank(r["catch"])}
        apply_text_fields(y, r)
        n += 1
    return f"{n} of {len(c.years)} experiences"


def neighborhood_text(c):
    """Input: data/reference/scene_text_neighborhoods.csv (needs hood_id, scene).
    Writes on neighborhoods[]: prose {scene, good_for_her, watch_for} and the fields of apply_text_fields; on a child of
    a split city that has no row of its own, prose only, from the city's row, with prose.about ("<City> as a whole")
    and prose.inherited_from (the city's id).
    Rule: a neighborhood's own row always wins, whatever the row order; when an id has several rows, the one written
    for the neighborhood's current experience is used; the city's row never supplies host text, points or subheads,
    because its figures are the city's."""
    rows, skip = c.csv(c.P.scene_hoods, need=("hood_id", "scene"))
    if skip:
        return skip
    year_label = {y.get("id"): label_key(y.get("label")) for y in c.years}
    best = {}
    for r in rows:
        if not r["scene"]:
            continue
        cur = best.get(r["hood_id"])
        h = c.hoods.get(r["hood_id"])
        fits = bool(h) and bool(r["year_label"]) and label_key(r["year_label"]) == year_label.get(h.get("year"))
        if cur is None or fits or not cur[1]:
            best[r["hood_id"]] = (r, fits)
    for h in c.hoods.values():
        clear_text_fields(h)
    own = inherited = 0
    for hid, (r, _) in best.items():
        if hid in c.hoods:
            h = c.hoods[hid]
            h["prose"] = {"scene": r["scene"], "good_for_her": none_if_blank(r["good_for_her"]), "watch_for": none_if_blank(r["watch_for"])}
            apply_text_fields(h, r)
            own += 1
    for hid, (r, _) in best.items():
        if hid in c.hoods:
            continue
        for h in c.kids.get(hid) or []:
            if "prose" not in h:
                h["prose"] = {"scene": r["scene"], "good_for_her": none_if_blank(r["good_for_her"]), "watch_for": none_if_blank(r["watch_for"]),
                              "about": f"{h.get('parent_name')} as a whole", "inherited_from": hid}
                inherited += 1
    return f"{own + inherited} of {len(c.hoods)} neighborhoods" + (f" ({inherited} from the city's text, labelled)" if inherited else "")


# ----------------------------------------------------------------------------------------------------------------------
# 3-6, 12. Resident quotes, survey figures, local rules
# ----------------------------------------------------------------------------------------------------------------------
def names_a_group(text) -> bool:
    """A resident quote is left out only when it singles out residents by a named race, ethnicity, religion or national
    origin (owner, 2026-11-16). The rule is the pipeline's own, parsers.characterises_residents_by_group: a group word
    used of people, not of a cuisine or a shop ("Chinese food"). Praise or talk of diversity stays."""
    return bool(parsers.characterises_residents_by_group(text))


def _drop_tagged(lst, key, value=2):
    return [x for x in lst or [] if not (isinstance(x, dict) and x.get(key) == value)]


def round2_quotes(c):
    """Input: data/voices/neighborhood_quotes_round2.csv (needs hood_id, excerpt); optional
    data/voices/quote_exclusions.csv (hood_id, excerpt_starts_with).
    Writes: neighborhoods[].local.voices, appending rows tagged round: 2.
    Rule: only verified rows (when the file has that column) with a permalink; not excluded by decision; not naming a
    group (names_a_group); routed by Ctx.targets (a citywide quote goes to each child of a split city, labelled; one
    that names a child goes to that child only); never a quote the neighborhood already shows. `about` names the
    source area when that is a different or wider place than the neighborhood."""
    rows, skip = c.csv(c.P.quotes2, need=("hood_id", "excerpt"))
    if skip:
        return skip
    excl, _ = read_csv(c.P.quote_exclusions, need=("hood_id", "excerpt_starts_with"), wait=0)
    excl = [(r["hood_id"], r["excerpt_starts_with"]) for r in excl or [] if r["excerpt_starts_with"]]
    for h in c.hoods.values():
        lo = local_of(h)
        lo["voices"] = _drop_tagged(lo.get("voices"), "round")
    shown = off_page = no_link = 0
    for r in verified(rows):
        ex = r["excerpt"]
        if not ex or any(r["hood_id"] == a and ex.startswith(b) for a, b in excl) or names_a_group(ex):
            continue
        if not r["permalink"]:
            no_link += 1
            continue
        tg = c.targets(r["hood_id"], r["source_area"])
        off_page += not tg
        sa = r["source_area"]
        plain = re.sub(r"\s*\((?:enclosing area|whole)\)", "", sa)
        about = re.sub(r",\s*[A-Z]{2}$", "", plain) if sa and len(plain) <= 40 and area_key(plain) != area_key(r["neighborhood"]) else None
        if r["hood_id"] not in c.hoods:
            about = None                                  # routed to a child of a split city: it is that child's, or labelled as the city's
        for h, whole in tg:
            vs = local_of(h)["voices"]
            if not any(isinstance(v, dict) and squash(v.get("excerpt")) == squash(ex) for v in vs):
                vs.append({"excerpt": ex, "theme": none_if_blank(r["theme"]), "sentiment": none_if_blank(r["sentiment"]),
                           "context": none_if_blank(r["speaker_context"]), "source": none_if_blank(r["source_site"]), "date": none_if_blank(r["post_date"]),
                           "url": r["permalink"], "source_area": sa or None, "about": whole or about, "round": 2})
            shown += 1
    return (f"{shown} round 2 quotes on the page" + (f"; {off_page} for places not on the page" if off_page else "")
            + (f"; {no_link} left out for having no link" if no_link else ""))


def round2_survey(c):
    """Input: data/voices/neighborhood_survey_round2.csv (needs hood_id, measure, value).
    Writes: neighborhoods[].local.survey, appending rows tagged round: 2 (value stays text, as in round 1).
    Rule: routed by Ctx.targets; a figure the neighborhood already shows (same measure, value, source and date: the
    page treats those as one) is not added again."""
    rows, skip = c.csv(c.P.survey2, need=("hood_id", "measure", "value"))
    if skip:
        return skip
    same = lambda x: (x.get("measure"), str(x.get("value")), x.get("source"), x.get("as_of"))
    for h in c.hoods.values():
        lo = local_of(h)
        lo["survey"] = _drop_tagged(lo.get("survey"), "round")
    shown = off_page = 0
    for r in rows:
        if not r["measure"] or not r["value"]:
            continue
        tg = c.targets(r["hood_id"], r["source_area"])
        off_page += not tg
        for h, whole in tg:
            row = {"measure": r["measure"], "value": r["value"], "source": none_if_blank(r["source_site"]), "as_of": none_if_blank(r["as_of"]),
                   "url": none_if_blank(r["source_url"]), "source_area": none_if_blank(r["source_area"]), "about": whole, "round": 2}
            sv = local_of(h)["survey"]
            if not any(isinstance(x, dict) and same(x) == same(row) for x in sv):
                sv.append(row)
            shown += 1
    return f"{shown} round 2 survey figures on the page" + (f"; {off_page} for places not on the page" if off_page else "")


RULE_LISTS = {"street_parking": "parking_rules", "dogs": "dog_rules"}
_rule_key = lambda x: (x.get("rule"), x.get("summary"), x.get("url"), x.get("municipality"))


def round2_rules(c):
    """Input: data/reference/local_rules_round2.csv (needs value_type, applies_to_hood_ids, topic).
    Writes: neighborhoods[].local.parking_rules and .dog_rules, appending rows tagged round: 2.
    Rule: only value_type "found" rows of topic street_parking or dogs that carry a source link; each id in
    applies_to_hood_ids is routed by Ctx.targets (a city's law applies in each of its neighborhoods, labelled); a rule
    the neighborhood already lists is not added again."""
    rows, skip = c.csv(c.P.rules2, need=("value_type", "applies_to_hood_ids", "topic"))
    if skip:
        return skip
    for h in c.hoods.values():
        lo = local_of(h)
        for key in RULE_LISTS.values():
            if lo.get(key):
                lo[key] = _drop_tagged(lo[key], "round") or None
    shown = no_link = 0
    for r in rows:
        key = RULE_LISTS.get(r["topic"])
        if r["value_type"] != "found" or not key or not (r["summary"] or r["quote"]):
            continue
        if not r["source_url"]:
            no_link += 1
            continue
        for hid in [x.strip() for x in r["applies_to_hood_ids"].split(";") if x.strip()]:
            for h, whole in c.targets(hid):
                row = {"rule": none_if_blank(r["rule"]), "summary": none_if_blank(r["summary"]), "quote": none_if_blank(r["quote"]),
                       "url": r["source_url"], "municipality": none_if_blank(r["municipality"]), "about": whole, "round": 2}
                lo = local_of(h)
                lst = lo.get(key) or []
                if not any(isinstance(x, dict) and _rule_key(x) == _rule_key(row) for x in lst):
                    lst.append(row)
                lo[key] = lst
                shown += 1
    return f"{shown} round 2 local rules on the page" + (f"; {no_link} left out for having no link" if no_link else "")


NYC_AREAS = {"brooklyn", "kings", "queens", "manhattan", "newyork", "bronx", "thebronx", "statenisland", "richmond"}
NYC_NAME = "New York City"


def is_nyc(h) -> bool:
    return str(h.get("state") or "").upper() == "NY" and letters(re.sub(r"\bcounty\b", "", str(h.get("area") or ""), flags=re.I)) in NYC_AREAS


def nyc_rules(c):
    """Input: the page data (neighborhoods[].local after round2_rules).
    Writes: neighborhoods[].local.parking_rules and .dog_rules on New York City neighborhoods that list no New York
    City rule of that kind, as copies tagged copied: true.
    Rule: a neighborhood is in the city when its state is NY and its area is one of the five boroughs (by borough or
    county name). A rule is citywide when more than half of the city's neighborhoods that carry New York City rules
    carry it, so a rule written for one place (a garage by Jamaica station) is not handed to the others."""
    nyc = [h for h in c.hoods.values() if is_nyc(h)]
    for h in nyc:
        lo = local_of(h)
        for key in RULE_LISTS.values():
            if lo.get(key):
                lo[key] = _drop_tagged(lo[key], "copied", True) or None
    lists = hoods_done = 0
    for key in RULE_LISTS.values():
        have = [h for h in nyc if any(isinstance(x, dict) and x.get("municipality") == NYC_NAME for x in h["local"].get(key) or [])]
        seen, order = {}, []
        for h in have:
            for x in h["local"][key]:
                if isinstance(x, dict) and x.get("municipality") == NYC_NAME:
                    k = _rule_key(x)
                    if k not in seen:
                        seen[k] = [x, 0]
                        order.append(k)
                    seen[k][1] += 1
        citywide = [seen[k][0] for k in order if seen[k][1] * 2 > len(have)]
        if not citywide:
            continue
        for h in nyc:
            if h in have:
                continue
            copies = [{k: v for k, v in x.items() if k not in ("round", "copied")} | {"about": None, "copied": True} for x in citywide]
            h["local"][key] = (h["local"].get(key) or []) + copies
            lists += 1
    hoods_done = sum(1 for h in nyc if any(isinstance(x, dict) and x.get("copied") for key in RULE_LISTS.values() for x in h["local"].get(key) or []))
    return f"citywide rules copied to {hoods_done} of {len(nyc)} New York City neighborhoods ({lists} lists)"


def quote_screen(c):
    """Input: the page data (neighborhoods[].local.voices, rounds 1 and 2).
    Writes: neighborhoods[].local.voices without the quotes that fail the screen.
    Rule: names_a_group, which is parsers.characterises_residents_by_group: a quote that singles out residents by a
    named race, ethnicity, religion or national origin is not shown; quotes about diversity in general, and a cuisine
    or a shop named by origin, stay (owner, 2026-11-16)."""
    dropped = kept = 0
    for h in c.hoods.values():
        vs = (h.get("local") or {}).get("voices")
        if not isinstance(vs, list):
            continue
        keep = [v for v in vs if not names_a_group(v.get("excerpt") if isinstance(v, dict) else v)]
        dropped += len(vs) - len(keep)
        kept += len(keep)
        h["local"]["voices"] = keep
    if dropped:
        c.said.append(f"quote screen: {dropped} resident quote(s) removed for naming a group")
    return f"{kept} resident quotes on the page pass the screen"


# ----------------------------------------------------------------------------------------------------------------------
# 7-10, 16. Per place: contact, about the building, realtor lines, ratings, photos
# ----------------------------------------------------------------------------------------------------------------------
PRIVATE_KIND = re.compile(r"broker|agent|individual|\bowner\b", re.I)
BROKER_NOTE = "Listed by a broker or the owner: get in touch through the listing page."


def is_private_line(kind) -> bool:
    """A broker's or an individual owner's number may be one person's own line: it is never shown."""
    return bool(PRIVATE_KIND.search(str(kind or "").replace("_", " ")))


def _phone(x):
    x = clean(x)
    return x if len(re.sub(r"\D", "", x)) >= 7 else None


def _good_own_rows(rows):
    return {r["building_id"]: r for r in rows or [] if r["building_id"] and r["confidence"].lower() in ("high", "medium")}


def contacts(c):
    """Input: data/reference/building_contacts.csv (needs building_id) and building_contacts_own_site.csv (needs
    building_id); either may be absent.
    Writes: units[].contact and buildings[].contact {phone, hours, site, kind, note, source} (the same value).
    Rule, per building: (1) a number read from the building's own site with high or medium confidence wins, kind
    "leasing office", also for a building the first file does not list; (2) else, when the contact is a broker or an
    individual owner, no number is shown, only the listing page and a line saying so; (3) else the listed number
    and/or page. A value that is not a phone number is not shown as one. A unit whose building is in neither file has
    no contact; while building_contacts.csv is unreadable, contacts already on the page are left alone."""
    C, why_c = c.csv(c.P.contacts, need=("building_id",))
    O, why_o = c.csv(c.P.contacts_own, need=("building_id",))
    if C is None and O is None:
        return why_c
    by_c = {r["building_id"]: r for r in C or [] if r["building_id"]}
    by_o = {b: r for b, r in _good_own_rows(O).items() if _phone(r["leasing_phone"])}
    own, hidden = set(), set()
    for u in c.places:
        b = building_id_of(u)
        o, r = by_o.get(b), by_c.get(b) or Row()
        new = None
        if o is not None:
            new = {"phone": _phone(o["leasing_phone"]), "hours": none_if_blank(o["office_hours"]) or none_if_blank(r["office_hours"]),
                   "site": none_if_blank(o["own_site_url"]) or none_if_blank(r["leasing_url"]), "kind": "leasing office", "note": None,
                   "source": none_if_blank(o["phone_page_url"])}
            own.add(b)
        elif b in by_c and is_private_line(r["contact_kind"]):
            new = {"phone": None, "hours": None, "site": none_if_blank(r["leasing_url"]), "kind": r["contact_kind"], "note": BROKER_NOTE, "source": None}
            hidden.add(b)
        elif b in by_c and (_phone(r["leasing_phone"]) or r["leasing_url"]):
            ph = _phone(r["leasing_phone"])
            new = {"phone": ph, "hours": none_if_blank(r["office_hours"]), "site": none_if_blank(r["leasing_url"]), "kind": none_if_blank(r["contact_kind"]),
                   "note": none_if_blank(r["note"]), "source": none_if_blank(r["leasing_phone_source_url"]) if ph else None}
        if new is not None:
            u["contact"] = new
        elif C is not None:
            u.pop("contact", None)
    return (counted(c, lambda o: o.get("contact")) + f" have a contact ({len(own)} buildings from their own site, {len(hidden)} broker or owner with the number withheld)"
            + ("; " + why_c if C is None else "") + ("; " + why_o if O is None else ""))


def about_building(c):
    """Input: data/reference/building_about.csv (needs building_id, about_building), from scripts/realtor_lines.py.
    Writes: about_building (text) and about_points (list, or null when the row has none) on units[] and on buildings[].
    Rule: joined on the building id; a building with no text leaves both fields off itself and its units."""
    rows, skip = c.csv(c.P.building_about, need=("building_id", "about_building"))
    if skip:
        return skip
    by = {r["building_id"]: r for r in rows if r["about_building"]}
    for u in c.places:
        # about_points on a unit or a building is only ever written here, together with about_building
        if "about_building" in u:
            u.pop("about_building", None)
            u.pop("about_points", None)
        r = by.get(building_id_of(u))
        if r is not None:
            u["about_building"] = r["about_building"]
            u["about_points"] = json_cell(r["about_points_json"], list)
    return counted(c, lambda o: o.get("about_building"))


def realtor_lines(c):
    """Input: data/reference/realtor_lines.csv (needs listing_id), from scripts/realtor_lines.py.
    Writes: units[].host {line, catch} and units[].headlines.<key>.subhead, one per sub_<key> column.
    Rule: joined on the unit's id (the listing id); no host without a line; a unit with no row carries neither field."""
    rows, skip = c.csv(c.P.realtor_lines, need=("listing_id",))
    if skip:
        return skip
    by = {r["listing_id"]: r for r in rows}
    n = 0
    for u in c.units:
        u.pop("host", None)
        u.pop("headlines", None)
        r = by.get(u.get("id"))
        if r is None:
            continue
        if r["host_line"]:
            u["host"] = {"line": r["host_line"], "catch": none_if_blank(r["host_catch"])}
            n += 1
        heads = {k[4:]: {"subhead": v} for k, v in r.items() if k.startswith("sub_") and len(k) > 4 and v}
        if heads:
            u["headlines"] = heads
    return f"{n} of {len(c.units)} places have a line"


PLATFORM_NAMES = {"google": "Google", "apartments_com": "Apartments.com", "rentcafe": "RentCafe", "openigloo": "Openigloo", "birdeye": "Birdeye",
                  "apartment_list": "Apartment List", "yelp": "Yelp", "zillow": "Zillow", "apartmentratings": "ApartmentRatings", "facebook": "Facebook",
                  "rentable": "Rentable"}
NOT_SEARCHED = re.compile(r"NO WEB SEARCH RUN|WEB SEARCH NOT RUN", re.I)


def ratings(c):
    """Input: data/evidence/ratings_census.csv (needs building_id, platform, status, rating), see
    docs/RATINGS_CENSUS_BRIEF.md.
    Writes: ratings {platforms[] {platform, rating, count, seen_via, url, as_of}, most_reviews, searched, found_any}
    on every unit and every buildings[] entry. Information only: no drop rule.
    Rule: a row is shown when its status is "found", the match confidence is high or medium, the platform is one of
    PLATFORM_NAMES (ForRent and ApartmentFinder repeat Apartments.com and are left out), the scale is 5 (or blank), the
    rating is a number from 0 to 5 and the review count is blank or a whole number. One row per platform (the one with
    more reviews), at most four, most reviews first, ties by platform name (never by the rating itself). searched is false for a building the census never lists or lists
    with a "web search not run" note: the page says "Not looked up yet" for those."""
    need = ("building_id", "platform", "status", "rating")
    rows, skip = c.csv(c.P.ratings, need=need)
    if skip:
        return skip
    listed = {r["building_id"] for r in rows}
    unsearched = {r["building_id"] for r in rows if NOT_SEARCHED.search(r["note"])}
    by, bad = {}, 0
    for r in rows:
        if r["status"] != "found" or r["match_confidence"] not in ("high", "medium") or r["platform"] not in PLATFORM_NAMES:
            continue
        rating, scale = number(r["rating"]), number(r["rating_scale"] or 5)
        if scale != 5:
            continue
        count = whole_number(r["review_count"]) if r["review_count"] else None
        if rating is None or not 0 <= rating <= 5 or (r["review_count"] and count is None):
            bad += 1
            continue
        cur = by.setdefault(r["building_id"], {})
        if r["platform"] not in cur or (count or 0) > (cur[r["platform"]]["count"] or 0):
            cur[r["platform"]] = {"platform": PLATFORM_NAMES[r["platform"]], "rating": round(rating, 1), "count": count,
                                  "seen_via": r["basis"].replace("_", " ") or None, "url": none_if_blank(r["source_url"]),
                                  "as_of": r["retrieved_at"][:10] or None}
    for u in c.places:
        b = building_id_of(u)
        got = sorted(by.get(b, {}).values(), key=lambda x: (-(x["count"] or 0), x["count"] is None, x["platform"]))
        u["ratings"] = {"platforms": [dict(x) for x in got[:4]], "most_reviews": max([x["count"] or 0 for x in got], default=0),
                        "searched": b in listed and b not in unsearched, "found_any": bool(got)}
    return counted(c, lambda o: o["ratings"]["found_any"]) + " have a rating" + (f"; {bad} census row(s) left out for a rating outside 0-5 or a broken count" if bad else "")


AGGREGATOR = re.compile(r"trulia|zumper|padmapper|apartmentlist|zillow|hotpads|apartments\.com|rent\.com|realtor\.com|streeteasy|craigslist|redfin|renthop|"
                        r"apartmentguide|forrent\.com|apartmentfinder|rentable\.co|rentcafe\.com/apartments|facebook\.com|compass\.com|nakedapartments", re.I)


def photos(c):
    """Input: data/reference/building_contacts_own_site.csv (optional), the contact written by contacts, and links.
    Writes: units[].photos and buildings[].photos {url, where, kind}: a link out to the page that carries the photos
    (photos are not copied). A building's listing page is its best unit's.
    Rule, first that exists: the building's own site from the own-site file (high or medium confidence); the contact's
    site or the building link when it is not a listing site and the contact is not a broker's or an owner's; the
    listing page for the apartment; the building's listing page. kind is "own_site" for the first two (where: "the
    building's own site"), else "listing" (where: the host name). A unit with no link at all has no photos field.
    While the own-site file is unreadable, an own-site link already on the page is kept."""
    O, why = c.csv(c.P.contacts_own, need=("building_id",))
    own_site = {b: r["own_site_url"] for b, r in _good_own_rows(O).items() if r["own_site_url"]}
    unit_links = {u.get("id"): u.get("links") for u in c.units if isinstance(u.get("links"), dict)}
    for u in c.places:
        if O is None and isinstance(u.get("photos"), dict) and u["photos"].get("kind") == "own_site":
            continue                                                   # the own-site file is unreadable: keep the link it gave
        ln = dict(u.get("links")) if isinstance(u.get("links"), dict) else {}
        if "building_id" not in u:                                     # a buildings[] entry: borrow its best unit's listing page
            ln.setdefault("listing", (unit_links.get(u.get("best_unit_id")) or {}).get("listing"))
        ct = u.get("contact") if isinstance(u.get("contact"), dict) else {}
        maybe = [None if is_private_line(ct.get("kind")) else ct.get("site"), ln.get("building")]
        site = own_site.get(building_id_of(u)) or next((x for x in maybe if clean(x) and not AGGREGATOR.search(x)), None)
        url = site or none_if_blank(ln.get("listing")) or none_if_blank(ln.get("building"))
        if not url:
            u.pop("photos", None)
            continue
        host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", url).split("/")[0])
        u["photos"] = {"url": url, "where": "the building's own site" if site else host, "kind": "own_site" if site else "listing"}
    own = sum(1 for u in c.units if (u.get("photos") or {}).get("kind") == "own_site")
    return counted(c, lambda o: o.get("photos")) + f" have a photos link ({own} places to the building's own site)" + ("; " + why if O is None else "")


# ----------------------------------------------------------------------------------------------------------------------
# 11. Outside descriptions
# ----------------------------------------------------------------------------------------------------------------------
_PLACE_KIND = (r"borough|town|township|city|village|hamlet|census-designated place|cdp|neighbou?rhood|community|section|suburb|municipality|"
               r"county seat|district|area")
BARE_LOCATION = re.compile(
    r"^[^,;:]{1,70}?\s(?:is|was)\s(?:an?|the)\s(?:(?!(?:in|of|on|within|located|situated)\b)[\w'-]+\s){0,4}?(?:" + _PLACE_KIND + r")\b"
    r"(?:\s+and\s+(?:[\w'-]+\s+){0,3}?(?:" + _PLACE_KIND + r"))?(?:\s+(?:in\s+and|and)\s+the\s+county\s+seat)?,?(?:\s+(?:located|situated))?"
    r"\s+(?:in|of|on|within)\s+(?:[a-z-]+\s+){0,5}?[A-Z]")          # ... in <a named place>; case matters here
# round 1's topic filter missed some word forms ("immigrants", "segregation"); every row is screened again here
COMPOSITION = re.compile(r"immigra|segregat|demograph|ethnic|racial|\brace\b(?! ?(?:track|course))|religio|"
                         r"\b(?:white|black|hispanic|latino|asian|jewish|catholic|muslim)\b (?:resident|population|communit|famil|neighbo)", re.I)
BARE_MAX_WORDS = 22


def is_bare_location(quote) -> bool:
    """"X is a borough in Y County, in the U.S. state of New Jersey.": one short sentence that only places the town.
    It says nothing about living there, so it is shown only when it is all there is."""
    t = re.sub(r"\b([A-Z])\.(?=[A-Z]\.)|(?<=\b[A-Z])\.(?=\s+[a-z])", r"\1", str(quote or ""))     # U.S. state -> US state
    t = re.sub(r"\s*\([^)]*\)", "", t).strip()
    if len(t.split()) > BARE_MAX_WORDS or re.search(r"[.!?]\s+\S", t):
        return False
    return bool(BARE_LOCATION.match(t))


# What it is like to be there comes first; a fact about the economy or the founding date comes last.
TOPIC_ORDER = ["main street", "food and nightlife", "parks", "waterfront", "housing feel", "landmark", "event", "transit", "history"]


def topic_rank(topic):
    """Position of a description's topic in TOPIC_ORDER; a row with no topic (round 1) sorts after all of them."""
    t = (topic or "").strip().lower()
    return TOPIC_ORDER.index(t) if t in TOPIC_ORDER else len(TOPIC_ORDER)


def pick_descriptions(rows):
    """The descriptions to show for one place, best first. Each row: {quote, topic, _c (character), _r (round)}.
    Rule: higher character first, round 2 before round 1 at equal character; never the same quote twice (nor one that
    is contained in another already taken); one per topic when there are more than three to choose from; at most
    three; a row with character 1 (a bare location sentence) only when nothing better exists, and then alone."""
    order = sorted(range(len(rows)), key=lambda i: (-rows[i]["_c"], topic_rank(rows[i].get("topic")), -rows[i]["_r"], i))
    taken, picked, topics = [], [], set()
    for i in order:
        x, q = rows[i], squash(rows[i]["quote"])
        if not q or any(q in t or t in q for t in taken):
            continue
        if x.get("topic") and x["topic"] in topics and len(rows) > 3:
            continue
        taken.append(q)
        topics.add(x.get("topic"))
        picked.append(x)
        if len(picked) == 3:
            break
    return [x for x in picked if x["_c"] >= 2] or picked[:1]


def descriptions(c):
    """Input: data/reference/neighborhood_descriptions_round2.csv and neighborhood_descriptions.csv (each needs hood_id,
    quote; at least one must be readable), from scripts/neighborhood_descriptions*.py.
    Writes: neighborhoods[].described[] {quote, source, url, about, topic, licence}.
    Rule: verified rows only (when the file has the column), with a source name and a link, and not about who lives
    there (COMPOSITION). Character: round 2 uses its 1-3 score; a row without one counts 2, or 1 when it is a bare
    location sentence (is_bare_location). Selection: pick_descriptions. A neighborhood's own descriptions win; a child
    of a split city with none of its own shows the city's, with `about` saying so."""
    pool, read, why, unsourced = {}, 0, [], 0
    for path, rnd in ((c.P.descriptions2, 2), (c.P.descriptions1, 1)):
        rows, skip = c.csv(path, need=("hood_id", "quote"))
        if skip:
            why.append(skip)
            continue
        read += 1
        for r in verified(rows):
            if not r["quote"] or COMPOSITION.search(r["quote"]):
                continue
            if not r["source_name"] or not r["source_url"]:
                unsourced += 1
                continue
            score = whole_number(r["character"])
            character = score if score is not None else (1 if is_bare_location(r["quote"]) else 2)
            pool.setdefault(r["hood_id"], []).append({
                "quote": r["quote"], "source": r["source_name"], "url": r["source_url"],
                "about": r["about_area"] if r["about_area"] and r["scope"] != "exact" and r["about_area"] != r["hood_name"] else None,
                "topic": none_if_blank(r["topic"]), "licence": none_if_blank(r["licence_note"]), "_c": character, "_r": rnd})
    if not read:
        return "; ".join(why)
    def public_list(picked, about=None):
        """The rows as the page reads them; the first (best) one is marked `featured` for the pull quote, unless it
        is only a bare fact (character below 2)."""
        out = [{k: v for k, v in x.items() if not k.startswith("_")} | ({"about": x["about"] or about} if about else {}) for x in picked]
        if out and picked[0]["_c"] >= 2:
            out[0]["featured"] = True
        return out
    for h in c.hoods.values():
        h.pop("described", None)
    picks = {hid: pick_descriptions(rows) for hid, rows in pool.items()}
    for hid, picked in picks.items():
        if hid in c.hoods and picked:
            c.hoods[hid]["described"] = public_list(picked)
    inherited = 0
    for hid, picked in picks.items():
        if hid in c.hoods or not picked:
            continue
        for h in c.kids.get(hid) or []:
            if not h.get("described"):
                h["described"] = public_list(picked, f"{h.get('parent_name')} as a whole")
                inherited += 1
    n = sum(1 for h in c.hoods.values() if h.get("described"))
    return (f"{n} of {len(c.hoods)} neighborhoods" + (f" ({inherited} show the city's)" if inherited else "")
            + (f"; {unsourced} row(s) left out for having no source or link" if unsourced else "") + ("; " + "; ".join(why) if why else ""))


# ----------------------------------------------------------------------------------------------------------------------
# 13-15. Coordinates, ranking, labels
# ----------------------------------------------------------------------------------------------------------------------
def coordinates(c):
    """Input: data/ranked_units.csv (needs hood_id, lat, lon; uses `shown` when present).
    Writes: neighborhoods[].lat and .lon, numbers rounded to five decimals (the page builder rounds to two, about 1 km).
    Rule: the mean position of the neighborhood's shown places, the same set the page builder averages; of all its
    ranked places only when none is shown (or the file has no `shown` column)."""
    rows, skip = c.csv(c.P.ranked_units, need=("hood_id", "lat", "lon"))
    if skip:
        return skip
    pts = {}
    for r in rows:
        lat, lon = number(r["lat"]), number(r["lon"])
        if r["hood_id"] in c.hoods and lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180:
            shown = r["shown"].lower() in ("true", "1", "yes") if "shown" in rows.columns else True
            pts.setdefault(r["hood_id"], {True: [], False: []})[shown].append((lat, lon))
    n = 0
    for hid, g in pts.items():
        use = g[True] or g[False]
        c.hoods[hid]["lat"] = round(sum(p[0] for p in use) / len(use), 5)
        c.hoods[hid]["lon"] = round(sum(p[1] for p in use) / len(use), 5)
        n += 1
    return f"{n} of {len(c.hoods)} neighborhoods"


MISSING_BUILDING_PENALTY = 2
RANK_FIELDS = ("experience_score", "experience_score_basis", "rank_in_experience", "single_building")


def building_scores(c):
    """{neighborhood id: {building id: the rank score of the building's best shown place}}.
    buildings[].best_rank_score when the entry has one (and names that neighborhood); for any other building, the best
    scores.rank among the units that carry that building_id and whose own hood_id is the neighborhood."""
    out = {}
    for b in c.buildings:
        s = number(b.get("best_rank_score"))
        if s is not None and b.get("hood_id"):
            out.setdefault(b["hood_id"], {})[b["id"]] = s
    listed = {b["id"] for b in c.buildings if number(b.get("best_rank_score")) is not None}
    for u in c.units:
        s = number(u["scores"].get("rank")) if isinstance(u.get("scores"), dict) else None
        b = u.get("building_id") or u.get("id")          # a unit with no building stands for itself
        if s is None or b in listed:
            continue
        g = out.setdefault(u.get("hood_id"), {})
        g[b] = max(g.get(b, s), s)
    return out


def ranking(c):
    """Input: the page data (buildings[].best_rank_score, units[].scores.rank / building_id / hood_id, years[].hood_ids).
    See docs/RANKING.md.
    Writes: neighborhoods[].experience_score, .experience_score_basis, .rank_in_experience, .single_building (true,
    only on a neighborhood whose score rests on one building); years[].hood_ids reordered.
    Rule (owner, 2026-11-16: show the top three, the rest on "show more", in descending order): a building counts once,
    by its best shown place (up to eight units of one building are shown, so three units could all be one building).
    A neighborhood's score is the mean of its three best buildings; with fewer than three it loses 2 points per missing
    building, so one good building does not outrank real choice. Rank 1..N inside the experience by score, ties on the
    neighborhood id; a neighborhood with no scored place comes last. Neighborhoods in no experience carry none of the
    four fields."""
    scores = building_scores(c)
    for h in c.hoods.values():
        for k in RANK_FIELDS:
            h.pop(k, None)
    n = single = 0
    for y in c.years:
        seen, hs = set(), []
        for i in y.get("hood_ids") or []:
            if i in c.hoods and i not in seen:
                seen.add(i)
                hs.append(c.hoods[i])
        for h in hs:
            top = sorted(scores.get(h["id"], {}).values(), reverse=True)[:3]
            short = 3 - len(top)
            h["experience_score"] = round(sum(top) / len(top) - MISSING_BUILDING_PENALTY * short, 1) if top else None
            h["experience_score_basis"] = (f"mean of the best place in each of its top {len(top)} building(s)"
                                           + (f", minus {MISSING_BUILDING_PENALTY * short} for having fewer than three buildings" if short else "")) if top else None
            if len(scores.get(h["id"], {})) == 1:
                h["single_building"] = True
                single += 1
        ranked = sorted(hs, key=lambda h: (h["experience_score"] is None, -(h["experience_score"] or 0), h["id"]))
        for i, h in enumerate(ranked, 1):
            h["rank_in_experience"] = i
        gone = [i for i in y.get("hood_ids") or [] if i not in c.hoods]
        y["hood_ids"] = [h["id"] for h in ranked] + gone          # unknown ids are kept, last, for the shape check to name
        n += len(ranked)
    return f"{n} neighborhoods ranked in {len(c.years)} experiences by their three best buildings ({single} rest on one building)"


def display_labels(c):
    """Input: the page data (years[].label, and display_label when experience_text wrote one from the CSV).
    Writes: years[].display_label.
    Rule: "years" are called "experiences" on the page; a label written in scene_text_years.csv is kept, otherwise the
    builder's label with a final " Year" turned into " Experience". Only the shown label changes, never a key."""
    n = 0
    for y in c.years:
        y["display_label"] = clean(y.get("display_label")) or re.sub(r" Year$", " Experience", clean(y.get("label")) or clean(y.get("id")))
        n += bool(y["display_label"])
    return f"{n} of {len(c.years)} experiences"


# ----------------------------------------------------------------------------------------------------------------------
# Shape check
# ----------------------------------------------------------------------------------------------------------------------
def validate(d):
    """Shape invariants the page relies on, as a list of plain sentences (empty when all hold). Never raises."""
    out = []

    def some(ids, n=4):
        ids = [str(i) for i in ids]
        return ", ".join(ids[:n]) + (f" and {len(ids) - n} more" if len(ids) > n else "")
    try:
        years = [y for y in d.get("years") or [] if isinstance(y, dict)]
        hoods = {h.get("id"): h for h in d.get("neighborhoods") or [] if isinstance(h, dict)}
        units = [u for u in d.get("units") or [] if isinstance(u, dict)]
        unit_ids = {u.get("id") for u in units}
        bad = [y.get("id") for y in years if not clean(y.get("display_label"))]
        if bad:
            out.append(f"experience without display_label: {some(bad)}")
        in_year = {}
        for y in years:
            ids = y.get("hood_ids") or []
            gone = [i for i in ids if i not in hoods]
            if gone:
                out.append(f"experience {y.get('id')} lists neighborhoods that do not exist: {some(gone)}")
            if len(set(ids)) != len(ids):
                out.append(f"experience {y.get('id')} lists a neighborhood twice")
            ranks = sorted((hoods[i].get("rank_in_experience") for i in ids if i in hoods), key=lambda r: (r is None, r if isinstance(r, int) else 0))
            if ranks != list(range(1, len(ranks) + 1)):
                out.append(f"experience {y.get('id')}: rank_in_experience is not 1..{len(ranks)} without gaps")
            order = [hoods[i].get("rank_in_experience") for i in ids if i in hoods]
            if all(isinstance(r, int) for r in order) and order != sorted(order):
                out.append(f"experience {y.get('id')}: hood_ids are not in rank order")
            for i in ids:
                if i in hoods:
                    in_year.setdefault(i, []).append(y.get("id"))
                    if hoods[i].get("year") not in (None, y.get("id")):
                        out.append(f"neighborhood {i} is listed under experience {y.get('id')} but says it belongs to {hoods[i].get('year')}")
        twice = [i for i, ys in in_year.items() if len(ys) > 1]
        if twice:
            out.append(f"neighborhood in more than one experience: {some(twice)}")
        stray = [i for i, h in hoods.items() if h.get("rank_in_experience") is not None and i not in in_year]
        if stray:
            out.append(f"neighborhood ranked but in no experience: {some(stray)}")
        lost = [u.get("id") for u in units if u.get("hood_id") not in hoods]
        if lost:
            out.append(f"{len(lost)} place(s) whose neighborhood does not exist: {some(lost)}")
        for i, h in hoods.items():
            ids = h.get("unit_ids") or []
            wrong = [x for x in ids if x not in unit_ids]
            if wrong:
                out.append(f"neighborhood {i} lists places that are not shown: {some(wrong)}")
        by_id = {u.get("id"): u for u in units}
        elsewhere = [x for i, h in hoods.items() for x in h.get("unit_ids") or [] if x in by_id and by_id[x].get("hood_id") != i]
        if elsewhere:
            out.append(f"{len(elsewhere)} place(s) listed under a neighborhood that is not their own: {some(elsewhere)}")
        phones = [u.get("id") for u in units + [b for b in d.get("buildings") or [] if isinstance(b, dict)] if isinstance(u.get("contact"), dict) and u["contact"].get("phone") and is_private_line(u["contact"].get("kind"))]
        if phones:
            out.append(f"{len(phones)} place(s) or building(s) show a phone number for a broker or an individual owner: {some(phones)}")
        unsourced = [i for i, h in hoods.items() for x in h.get("described") or [] if not (isinstance(x, dict) and clean(x.get("source")) and clean(x.get("url")))]
        if unsourced:
            out.append(f"described quote without a source and a link in: {some(sorted(set(unsourced)))}")
        repeats = [i for i, h in hoods.items() if len({squash(x.get("quote")) for x in h.get("described") or [] if isinstance(x, dict)}) < len(h.get("described") or [])]
        if repeats:
            out.append(f"the same described quote twice in: {some(repeats)}")
        odd = []
        for u in units:
            for p in (u.get("ratings") or {}).get("platforms") or [] if isinstance(u.get("ratings"), dict) else []:
                r, n = p.get("rating"), p.get("count")
                if isinstance(r, bool) or not isinstance(r, (int, float)) or not 0 <= r <= 5 or not (n is None or (isinstance(n, int) and not isinstance(n, bool) and n >= 0)):
                    odd.append(u.get("id"))
        if odd:
            out.append(f"{len(odd)} rating row(s) with a rating outside 0-5 or a count that is not a whole number: {some(odd)}")
        nan = _nan_like(d)
        if nan:
            out.append(f"{len(nan)} value(s) that are NaN or a printed missing value: {some(nan)}")
    except Exception as e:                    # the check must never stop the run
        out.append(f"the shape check itself failed ({type(e).__name__}: {e})")
    return out


def _nan_like(o, path=""):
    found = []
    if isinstance(o, dict):
        for k, v in o.items():
            found += _nan_like(v, f"{path}.{k}")
    elif isinstance(o, list):
        for v in o:
            found += _nan_like(v, path + "[]")
    elif (isinstance(o, float) and not math.isfinite(o)) or (isinstance(o, str) and o.strip().lower() in ("nan", "none", "null", "nat", "<na>")):
        found.append(path.lstrip("."))
    return found


# ----------------------------------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------------------------------
BLOCKS = [experience_text, neighborhood_text, round2_quotes, round2_survey, round2_rules, nyc_rules, contacts, about_building,
          realtor_lines, ratings, descriptions, quote_screen, coordinates, ranking, display_labels, photos]


# Top-level fields this script adds, per object type, in the order they are kept in the file (fields it only edits in
# place, such as subhead, lat, lon, hood_ids and local, keep the builder's position).
OWNED = {
    "years": ("prose", "host", "about_points", "day_moments", "tagline", "subhead_original", "headlines", "display_label"),
    "neighborhoods": ("prose", "host", "about_points", "tagline", "subhead_original", "headlines", "described",
                      "experience_score", "experience_score_basis", "rank_in_experience", "single_building"),
    "units": ("contact", "about_building", "about_points", "host", "headlines", "ratings", "photos"),
    "buildings": ("contact", "about_building", "about_points", "ratings", "photos"),
}


def apply_all(d, paths, wait=None):
    """Run every block on the page data in the stated order. Returns (data made JSON-safe, context). A block that
    raises is reported and the run goes on: one broken input must not take the other fifteen with it."""
    c = Ctx(d, paths, wait)
    for block in BLOCKS:
        try:
            c.rep[block.__name__] = block(c)
        except Exception as e:
            c.rep[block.__name__] = f"FAILED ({type(e).__name__}: {str(e)[:120]})"
    # the fields written here sit last on each object, in one fixed order, whatever a block cleared and wrote again:
    # without this a second run would reorder keys and rewrite a file that says the same thing
    for objs, keys in ((c.years, OWNED["years"]), (c.hoods.values(), OWNED["neighborhoods"]), (c.units, OWNED["units"]), (c.buildings, OWNED["buildings"])):
        for o in objs:
            for k in keys:
                if k in o:
                    o[k] = o.pop(k)
    safe, fixed = json_safe(d)
    if fixed:
        c.said.append(f"{fixed} NaN or \"nan\"-like value(s) turned into null")
    if not isinstance(safe.get("meta"), dict):
        safe["meta"] = {}
    safe["meta"]["extras"] = dict(c.rep)
    return safe, c


def run(root=ROOT, data_json=None, strict=False, dry_run=False, wait=None, out=print):
    """Read the page data, apply every block, check the shape, write (atomically, and only when something changed).
    Returns the exit code: 0, 1 with strict and a shape violation, 2 when the page data could not be read or written."""
    P = Paths(root, data_json)
    for attempt in (1, 2, 3):
        try:
            before = P.data_json.stat()
        except OSError:
            before = None
        d, why = read_json(P.data_json, wait)
        if d is None or not isinstance(d, dict):
            out(f"page_data_extras: {P.rel(P.data_json)} {why or 'is not an object'}; nothing done (run scripts/build_page_data.py first)")
            return 2
        old_text = dump(d) if not _nan_like(d) else None      # None: the file needs rewriting whatever the blocks do
        new, c = apply_all(d, P, wait)
        text = dump(new)
        problems = validate(new)
        changed = text != old_text
        if dry_run or not changed:
            break
        try:
            now = P.data_json.stat()
        except OSError:
            now = None
        if before is None or now is None or (now.st_mtime_ns, now.st_size) != (before.st_mtime_ns, before.st_size):
            if attempt < 3:
                out(f"page_data_extras: {P.rel(P.data_json)} changed while this ran; starting again")
                continue
            out(f"page_data_extras: {P.rel(P.data_json)} keeps changing; nothing written")
            return 2
        tmp = P.data_json.with_name(P.data_json.name + ".extras.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, P.data_json)
        break
    width = max(len(k) for k in c.rep)
    out(f"page_data_extras: {P.rel(P.data_json)} " + ("would change (dry run)" if dry_run and changed else "written" if changed else "unchanged"))
    for k, v in c.rep.items():
        out(f"  {k:<{width}}  {v}")
    for s in c.said:
        out(f"  note: {s}")
    if problems:
        out(f"  shape check: {len(problems)} problem(s)")
        for p in problems:
            out(f"    - {p}")
    else:
        out("  shape check: ok")
    return 1 if strict and problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Add prose, quotes, rules, contacts, ratings, descriptions and ranking to site/data.json.")
    ap.add_argument("--root", default=str(ROOT), help="the house-hunt folder (default: this script's parent folder)")
    ap.add_argument("--data-json", default=None, help="the page data file (default: ROOT/site/data.json)")
    ap.add_argument("--strict", action="store_true", help="exit 1 when the shape check finds a problem")
    ap.add_argument("--dry-run", action="store_true", help="report, write nothing")
    a = ap.parse_args(argv)
    return run(a.root, a.data_json, strict=a.strict, dry_run=a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
