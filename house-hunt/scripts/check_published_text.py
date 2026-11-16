#!/usr/bin/env python3
"""The final-text audit: check the words that are actually PUBLISHED, in site/data.json.

Why (independent check 4, D15): the other guards read drafts and generators, not the page. A conceit, a project term
or a false number written into site/data.json, data/reference/realtor_lines.csv or building_about.csv passed
check_scene_text.py, test_realtor_lines.py and verify_all.py. This script reads site/data.json and nothing else decides
what the reader sees.

WHAT IS READ (every prose field the page shows; the list follows scripts/page_data_extras.py's field table and the
renderers in site/index.html):
  experiences   years[]: display_label, tagline, subhead, prose.{scene, promise, catch}, host.intro,
                host.walkthrough[], about_points[].text, day_moments[].text, headlines.<key>.subhead
  neighborhoods neighborhoods[]: prose.{scene, good_for_her, watch_for}, host.intro, about_points[].text,
                headlines.<key>.subhead, and at_a_glance[] {text, label} when page_data_extras attaches it
  buildings     buildings[]: about_building, about_points[].text
  apartments    units[]: host.{line, catch}, headlines.<key>.subhead, about_building, about_points[].text
  pipeline strings (owned by the pipeline, printed by the page; checked for vocabulary and stale wording only):
                units[]: confirm.{what, why, question}, disclosures[].{what, why, question}, tour_questions[],
                all_in_lines[].{line, note}, all_in_likely_note, rent.first_full_payment_note; meta.notes[],
                meta.moment_thresholds
  the page template (site/index.html) is not data: `--template` scans its string literals for the same banned
                constructions and lists what it finds (informational; the template is the page agent's).
  NOT read: resident quotes, outside descriptions, local rule summaries and listing offer text. They are other
                people's words, quoted with their source.

THE CHECKS
  1 SOURCE   the published text is exactly what the checked source says today:
             experiences and neighborhoods = their row in data/reference/scene_text_*.csv;
             apartments and buildings = what scripts/realtor_lines.py writes from THIS data, regenerated here (so a line
             edited in realtor_lines.csv, building_about.csv or site/data.json itself is caught).
  2 PLAIN    the banned constructions, vocabulary, stale wording and readability rules of check_scene_text.py
             (imported: CONCEITS, the noun x verb conceit guard, VOCAB, INTERNAL, STALE, FIGURE, sentence length,
             BANNED, CRIME, NUMBER_WORDS), applied to the published text.
  3 NUMBERS  every number in a sentence must be a field of the object the sentence is about, after the page's rounding.
             Experiences and neighborhoods: the evidence items of the row, each looked up again (check_row), and the
             figure strip. Apartments and buildings: the object's own fields (test_realtor_lines.allowed_numbers).
             An unmatched number is reported.
  4 CLAIMS   a fixed list of checkable claims, each a pattern compared with a field (CLAIMS below): has a pool / gym /
             garage / covered parking / doorman / concierge / dog area / washer and dryer / lounge / elevator; dogs
             allowed; "no bars", "no restaurants"; "the only building of N with ..."; "the lowest-priced / largest /
             highest of the N apartments"; "N apartments are listed"; the distance to the dog park, a park, the
             supermarket and the station; minutes to her parents; tolls; "its own dog area / garage" for a
             neighborhood. For experiences, check_scene_text.check_experience (75% of the apartments, every
             neighborhood card).
  5 ACROSS   contradictions on the same page: a neighborhood that says the dog park is far, or that no building has
             one, above a building text that says "its own dog park"; a neighborhood that says nothing to eat is
             within a walk above its only building's "N restaurants are within a 10-minute walk"; advice to look for
             a garage where every building text says it has one.
  6 STALE    "not checked again", "year" for an experience, "unit", "all-in", "cap" and the other project terms, in
             every field above including the pipeline's strings.

LIMITS. The claims audit sees only the patterns listed; a claim worded another way passes 4 and is left to 1 (it
must equal the generated text) and 3. A wrong figure that happens to equal another field of the same object passes 3.
Pipeline strings get checks 2 (vocabulary only) and 6, not 3 and 4.

Run from the house-hunt folder:
    python3 scripts/check_published_text.py              all checks; exit 1 on any failure in the text or the pipeline strings
    python3 scripts/check_published_text.py --text-only  exit code from the written text only (pipeline strings listed)
    python3 scripts/check_published_text.py --template   also list banned constructions in site/index.html (informational)
Each failure prints: owner | object kind and id | field | problem | sentence.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_scene_text as G  # noqa: E402
import realtor_lines as R  # noqa: E402
import test_realtor_lines as T  # noqa: E402   guard(), allowed_numbers(), mask(): the apartment text's own guards

ROOT = G.ROOT
DATA = ROOT / "site" / "data.json"
TEMPLATE = ROOT / "site" / "index.html"


class Fail:
    def __init__(self, owner, kind, oid, field, problem, sentence=""):
        self.owner, self.kind, self.id, self.field, self.problem, self.sentence = owner, kind, oid, field, problem, sentence

    def __str__(self):
        return f"{self.owner} | {self.kind} {self.id} | {self.field} | {self.problem}" + (f" | {self.sentence}" if self.sentence else "")


def use_page(d):
    """Point check_scene_text's page tables at this page data (the file on disk, or a copy under test)."""
    G._page.cache_clear() if hasattr(G._page, "cache_clear") else None
    G._page = lambda: d
    for f in (G.table, G.shown_hoods, G._units_with_hood):
        f.cache_clear()


def sents(text):
    return G.sentences(str(text or "").replace("St. ", "St "))


# ---------------------------------------------------------------------------------------------------------------
# 1-3 for experiences and neighborhoods: the published fields, laid out as the scene CSV's columns

def year_texts(y):
    heads = y.get("headlines") or {}
    return {"display_label": y.get("display_label") or "", "tagline": y.get("tagline") or "", "subhead": y.get("subhead") or "",
            "scene": (y.get("prose") or {}).get("scene") or "", "promise": (y.get("prose") or {}).get("promise") or "",
            "catch": (y.get("prose") or {}).get("catch") or "", "host_intro": (y.get("host") or {}).get("intro") or "",
            "host_walkthrough": "\n\n".join((y.get("host") or {}).get("walkthrough") or []),
            **{"sub_" + k: (heads.get(k) or {}).get("subhead") or "" for k in G.SUB_SECTIONS["year"]},
            "about_points_json": json.dumps(y.get("about_points") or [], ensure_ascii=False),
            "day_moments_json": json.dumps(y.get("day_moments") or [], ensure_ascii=False)}


def hood_texts(h):
    heads = h.get("headlines") or {}
    p = h.get("prose") or {}
    return {"scene": p.get("scene") or "", "good_for_her": p.get("good_for_her") or "", "watch_for": p.get("watch_for") or "",
            "host_intro": (h.get("host") or {}).get("intro") or "",
            **{"sub_" + k: (heads.get(k) or {}).get("subhead") or "" for k in G.SUB_SECTIONS["hood"]},
            "about_points_json": json.dumps(h.get("about_points") or [], ensure_ascii=False)}


def read_rows(path, key):
    if not Path(path).exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r[key]: r for r in csv.DictReader(f)}


def same_json(a, b):
    try:
        return json.loads(a or "[]") == json.loads(b or "[]")
    except json.JSONDecodeError:
        return False


def audit_scene(d, out):
    years = read_rows(G.YEARS, "year_label")
    hoods = read_rows(G.HOODS, "hood_id")
    for y in d.get("years") or []:
        key = G.year_key(y.get("label"))
        texts = year_texts(y)
        row = years.get(key)
        if row is None:
            if any(v.strip() and v not in ("[]",) for k, v in texts.items() if k != "subhead"):
                out.append(Fail("text", "experience", y.get("id"), "*", "has text on the page and no row in scene_text_years.csv"))
            continue
        for col, pub in texts.items():
            src = row.get(col) or ""
            if col == "host_walkthrough":
                src = "\n\n".join(x.strip() for x in src.split("\n\n") if x.strip())
            if col == "subhead" and not src:
                continue
            ok = same_json(pub, src) if col.endswith("_json") else pub == src
            if not ok:
                out.append(Fail("text", "experience", y.get("id"), col, "SOURCE: differs from scene_text_years.csv "
                                "(rebuild, then page_data_extras.py)", pub[:160]))
        try:
            ev = json.loads(row.get("evidence_json") or "[]")
        except json.JSONDecodeError:
            ev = []
        for p in G.check_row("year", key, texts, ev)[0]:
            out.append(Fail("text", "experience", y.get("id"), p.split(":")[0], p))
    for h in d.get("neighborhoods") or []:
        texts = hood_texts(h)
        if (h.get("prose") or {}).get("inherited_from"):       # a split city's child: the city's row, labelled as such
            for col in ("scene", "good_for_her", "watch_for"):
                for p in G.check_plain(col, texts[col]) if texts[col] else []:
                    out.append(Fail("text", "neighborhood", h["id"], col, p, texts[col][:160]))
            continue
        row = hoods.get(h["id"])
        has_text = any(texts[c].strip() for c in ("scene", "good_for_her", "watch_for", "host_intro"))
        if row is None:
            if has_text:
                out.append(Fail("text", "neighborhood", h["id"], "*", "has text on the page and no row in scene_text_neighborhoods.csv"))
            elif (h.get("counts") or {}).get("shown"):
                out.append(Fail("text", "neighborhood", h["id"], "*", "shows apartments and has no text at all "
                                "(write a block in scene_text_source.txt)"))
            continue
        if not has_text:
            if (h.get("counts") or {}).get("shown"):
                out.append(Fail("text", "neighborhood", h["id"], "*", "shows apartments and the page data carries no "
                                "text for it (run page_data_extras.py)"))
            continue
        for col, pub in texts.items():
            src = row.get(col) or ""
            ok = same_json(pub, src) if col.endswith("_json") else pub == src
            if not ok:
                out.append(Fail("text", "neighborhood", h["id"], col, "SOURCE: differs from scene_text_neighborhoods.csv "
                                "(rebuild, then page_data_extras.py)", pub[:160]))
        try:
            ev = json.loads(row.get("evidence_json") or "[]")
        except json.JSONDecodeError:
            ev = []
        for p in G.check_row("hood", h["id"], texts, ev)[0]:
            out.append(Fail("text", "neighborhood", h["id"], p.split(":")[0], p))
        # "At a glance": when the page data carries it, it must be the shown buildings' figures as of now
        if "at_a_glance" in h:
            want = json.loads(json.dumps(G.glance(h["id"])))
            if h.get("at_a_glance") != want:
                out.append(Fail("text", "neighborhood", h["id"], "at_a_glance", "is not the figures of the buildings shown "
                                "(rebuild scene text, then page_data_extras.py)"))
        elif (h.get("counts") or {}).get("shown") and row.get("glance_json") in (None, ""):
            out.append(Fail("text", "neighborhood", h["id"], "glance_json", "scene_text_neighborhoods.csv has no glance_json"))


# ---------------------------------------------------------------------------------------------------------------
# 4. Claims of an apartment's or a building's text: pattern -> field

def _am(u):
    return u.get("amenities") or {}


def _dog_area(u):
    return G.own_dog_area(_am(u))


def _pk(u):
    return R.parking_kind(u)[0]


def _dogs_settled(us):
    return all(str((u.get("dog") or {}).get("allowed") or "").lower() == "yes" and not R.dog_open(u) for u in us)


def _elevator_settled(us):
    return all(R.get(u, "elevator", "value") == "yes" and not R.get(u, "elevator", "listing_site_only")
               and not (R.get(u, "confirm", "asterisk") and R.get(u, "confirm", "what") == "elevator") for u in us)


# (name, pattern, test(u, building's shown units) -> bool, the field it rests on).  A sentence that asks, or says the
# thing is not published / not confirmed / not mentioned, is not a claim (NOT_A_CLAIM).
PLACE_CLAIMS = [
    ("a pool", r"\bpool\b(?! table)", lambda u, us: bool(_am(u).get("pool")), "amenities.pool"),
    ("a gym", r"\bgym\b|\bexercise without leaving\b", lambda u, us: _am(u).get("gym") == "yes", "amenities.gym"),
    ("a garage", r"\bgarage\b|\bpark indoors\b", lambda u, us: _pk(u) == "garage", "parking.type"),
    ("covered parking", r"\bcovered parking\b|\bunder cover\b", lambda u, us: _pk(u) in ("covered", "garage"), "parking.type"),
    ("a parking lot", r"\bbuilding's lot\b|\bparking lot\b|\bits own parking lot\b", lambda u, us: _pk(u) == "lot", "parking.type"),
    ("parking included", r"\b(?:parking space|space) is included\b|\bparking is included\b|\bincludes a parking space\b|"
     r"\bnot pay extra to park\b", lambda u, us: R.parking_kind(u)[2], "parking.fee + fee_note"),
    ("a doorman", r"\bdoorman\b|\bat the front door\b", lambda u, us: R.desk_kind(_am(u)) in ("doorman", "doorman24"),
     "amenities.doorman + doorman_text"),
    ("a concierge", r"\bconcierge\b", lambda u, us: R.desk_kind(_am(u)) in ("concierge", "concierge24"),
     "amenities.doorman_text / concierge"),
    ("a staffed front desk", r"\bfront desk\b|\bstaffs the lobby\b|\blobby is attended\b",
     lambda u, us: R.desk_kind(_am(u)) in ("doorman24", "attended24", "attended"), "amenities.doorman + doorman_text"),
    ("its own dog area", r"\bits own dog (?:park|run|area)\b|\bdog (?:park|run) on (?:site|the property)\b|"
     r"\bdog area on the property\b|\bwithout leaving the property\b|\bown dog area\b", lambda u, us: _dog_area(u),
     "amenities.dog_amenities"),
    ("a washer and dryer in the apartment", r"\bwasher\b|\bdryer\b", lambda u, us: R.laundry_kind(_am(u)) == "wd",
     "amenities.in_unit_laundry + laundry"),
    ("laundry in the apartment", r"\blaundry (?:is )?(?:in|inside) (?:the|your own) apartment\b|\bno shared laundry room\b",
     lambda u, us: R.laundry_kind(_am(u)) is not None, "amenities.in_unit_laundry + laundry"),
    ("a lounge or coworking room", r"\blounge or coworking\b", lambda u, us: _am(u).get("lounge_or_coworking") == "yes",
     "amenities.lounge_or_coworking"),
    ("dogs are allowed", r"\b[Dd]ogs are allowed\b|\bdog policy sets no weight limit\b", lambda u, us: _dogs_settled(us),
     "dog.allowed + confirm"),
    ("an elevator", r"\bhas an elevator\b", lambda u, us: _elevator_settled(us), "elevator + confirm"),
]
PLACE_CLAIMS = [(n, re.compile(rx, re.I), t, f) for n, rx, t, f in PLACE_CLAIMS]
NOT_A_CLAIM = re.compile(r"^ask\b|\bwhether\b|\bdisagree\b|\bdo not agree\b|\bask (?:whether|what kind|where|the office|for|before|about)\b|\bnot (?:published|confirmed|"
                         r"mentioned|known|say|give)\b|\bdoes not (?:mention|say|give|publish)\b|\bis not confirmed\b|"
                         r"\bconfirm\b|\bno other (?:building|apartment)\b|\bthe only (?:building|garage)\b|\bnot explained\b",
                         re.I)
ONLY_BUILDING = re.compile(r"only building of the (\d+) listed in this neighborhood with (.+?)[.,]|"
                           r"No other building listed in this neighborhood has (.+?)[.,]|"
                           r"The only (garage) among the (\d+) buildings listed in this neighborhood is here", re.I)
ONLY_WHAT = [("pool", lambda u: bool(_am(u).get("pool"))), ("garage", lambda u: _pk(u) == "garage"),
             ("doorman", lambda u: R.desk_kind(_am(u)) in ("doorman", "doorman24")),
             ("washer and dryer", lambda u: R.laundry_kind(_am(u)) is not None),
             ("laundry", lambda u: R.laundry_kind(_am(u)) is not None),
             ("dog", lambda u: _dog_area(u))]
OF_N_APTS = re.compile(r"(?:of the|Of the) (\d+) apartments listed in this building", re.I)
N_LISTED = re.compile(r"\b(\d+) apartments? (?:is|are) listed in this building", re.I)
SUPER = [(re.compile(r"\b(lowest)-priced of the|costs (the least)\b|No other apartment listed in this building costs less", re.I), "all_in", min),
         (re.compile(r"\b(largest) of the|has (the most) space\b|is as large as this apartment", re.I), "sqft", max),
         (re.compile(r"\b(highest) of the|higher up than any other", re.I), "floor", max)]


def place_claims(field, text, u, ctx, out, kind, oid):
    us = ctx["by_building"].get(u.get("building_id")) or [u]
    peers = ctx["buildings_in_hood"].get(u.get("hood_id")) or []
    for sent in sents(text):
        for name, rx, test, basis in PLACE_CLAIMS:
            if rx.search(sent) and not NOT_A_CLAIM.search(sent) and not test(u, us):
                out.append(Fail("text", kind, oid, field, f"CLAIM: says \"{name}\", and {basis} does not carry it", sent))
        m = ONLY_BUILDING.search(sent)
        if m:
            n = m.group(1) or m.group(5)
            what = (m.group(2) or m.group(3) or m.group(4) or "").lower()
            if n and int(n) != len(peers):
                out.append(Fail("text", kind, oid, field, f"CLAIM: \"of the {n}\" buildings, and {len(peers)} are shown "
                                "in this neighborhood", sent))
            for word, has in ONLY_WHAT:
                if word in what:
                    mine = has(u)
                    others = [b for b in peers if b["id"] != u.get("building_id") and has(ctx["first_unit"][b["id"]])]
                    if not mine or others:
                        out.append(Fail("text", kind, oid, field, f"CLAIM: \"the only building with {word}\": "
                                        f"{'this one has none' if not mine else str(len(others)) + ' other building(s) here have it too'}", sent))
                    break
        m = OF_N_APTS.search(sent)
        if m and int(m.group(1)) != len(us):
            out.append(Fail("text", kind, oid, field, f"CLAIM: \"of the {m.group(1)} apartments\", and {len(us)} are shown "
                            "in this building", sent))
        m = N_LISTED.search(sent)
        if m and int(m.group(1)) != len(us):
            out.append(Fail("text", kind, oid, field, f"CLAIM: \"{m.group(1)} apartments are listed\", and {len(us)} are shown", sent))
        if kind == "apartment":
            for rx, key, best in SUPER:
                if rx.search(sent):
                    vals = [R.num(x.get(key)) for x in us]
                    mine = R.num(u.get(key))
                    if mine is None or any(v is None for v in vals) or mine != best(vals) or vals.count(mine) != 1:
                        out.append(Fail("text", kind, oid, field, f"CLAIM: a superlative on {key} that the {len(us)} apartments "
                                        "shown in this building do not bear out", sent))
            if re.search(r"only this apartment is available now|only apartment listed in this building that is available now", sent, re.I):
                now = [x for x in us if str(x.get("available")).lower() == "now"]
                if len(now) != 1 or now[0] is not u:
                    out.append(Fail("text", kind, oid, field, "CLAIM: \"the only apartment available now\" is not so", sent))
        # distances and minutes, each against the apartment's own moment fields
        for rx, path, how in DIST:
            for m in rx.finditer(sent):
                v = R.num(R.get(u, *path))
                want = None if v is None else (R.miles(v) if how == "mi" else str(int(G.half_up(v))))
                got = next((g for g in m.groups() if g), None)
                if want is None or got != want:
                    out.append(Fail("text", kind, oid, field, f"CLAIM: \"{m.group(0)}\", and {'.'.join(path)} reads "
                                    f"{want if want is not None else 'nothing'}", sent))


DIST = [(re.compile(r"\b(?:dog park|dog run)\b[^.;]*?\b(\d+\.\d) miles", re.I), ("moments", "wake", "dog_park_m"), "mi"),
        (re.compile(r"\bsupermarket\b[^.;]*?\b(\d+\.\d) miles", re.I), ("moments", "work", "supermarket_m"), "mi"),
        (re.compile(r"\b(\d+\.\d) miles to the nearest supermarket", re.I), ("moments", "work", "supermarket_m"), "mi"),
        (re.compile(r"\b[Aa]bout (\d+) restaurants? (?:is|are)? ?within", re.I), ("moments", "after", "restaurants_800m"), "int"),
        (re.compile(r"\bwith about (\d+) restaurants within", re.I), ("moments", "after", "restaurants_800m"), "int"),
        (re.compile(r"\bBuilt in (\d{4})|built in (\d{4})|dates from (\d{4})", re.I), ("amenities", "year_built"), "year")]


def audit_places(d, out):
    units = d.get("units") or []
    blds = {b["id"]: b for b in d.get("buildings") or []}
    by_b = defaultdict(list)
    for u in units:
        by_b[u.get("building_id")].append(u)
    in_hood = defaultdict(list)
    for b in blds.values():
        if by_b.get(b["id"]):
            in_hood[b.get("hood_id")].append(b)
    ctx = {"by_building": by_b, "buildings_in_hood": in_hood, "first_unit": {bid: us[0] for bid, us in by_b.items()}}
    # 1. what the generator writes from this data, today
    try:
        want_u = {r["listing_id"]: r for r in R.build(units)}
        want_b = {r["building_id"]: r for r in R.build_buildings(units)}
    except Exception as e:                                # noqa: BLE001
        out.append(Fail("text", "page", "-", "*", f"realtor_lines.py cannot compose from this data: {type(e).__name__}: {e}"))
        want_u, want_b = {}, {}
    for u in units:
        uid = u.get("id")
        w = want_u.get(uid)
        host, heads = u.get("host") or {}, u.get("headlines") or {}
        fields = {"host.line": host.get("line") or "", "host.catch": host.get("catch") or "",
                  **{f"headlines.{k}.subhead": (heads.get(k) or {}).get("subhead") or "" for k in ("cost", "parking", "dog", "building")}}
        if w:
            src = {"host.line": w["host_line"], "host.catch": w["host_catch"],
                   **{f"headlines.{c[4:]}.subhead": w[c] for c in R.SUB_COLS}}
            for f, pub in fields.items():
                if pub != (src.get(f) or ""):
                    out.append(Fail("text", "apartment", uid, f, "SOURCE: is not what realtor_lines.py writes from this data "
                                    "(rerun realtor_lines.py, then page_data_extras.py)", pub[:160]))
        if not fields["host.line"]:
            out.append(Fail("text", "apartment", uid, "host.line", "no line on the page"))
        ok = T.allowed_numbers(u, (len(by_b[u.get("building_id")]),))
        for f, text in fields.items():
            if not text:
                continue
            for p in T.guard(text, T.mask(text, u)):
                out.append(Fail("text", "apartment", uid, f, "PLAIN: " + p, text[:160]))
            for n in T.numbers(T.mask(text, u)):
                if n not in ok:
                    out.append(Fail("text", "apartment", uid, f, f"NUMBER: '{n}' is not a field of this apartment (after rounding)", text[:160]))
            place_claims(f, text, u, ctx, out, "apartment", uid)
    for bid, b in blds.items():
        us = by_b.get(bid) or []
        if not us:
            continue
        first = us[0]
        w = want_b.get(bid)
        about = b.get("about_building") or ""
        pts = b.get("about_points") or []
        if w:
            if about != w["about_building"]:
                out.append(Fail("text", "building", bid, "about_building", "SOURCE: is not what realtor_lines.py writes from "
                                "this data", about[:160]))
            if pts != json.loads(w["about_points_json"] or "[]"):
                out.append(Fail("text", "building", bid, "about_points", "SOURCE: is not what realtor_lines.py writes from this data"))
        for u in us:                                      # the copies on the building's apartments must be the same words
            if (u.get("about_building") or "") != about or (u.get("about_points") or []) != pts:
                out.append(Fail("text", "apartment", u.get("id"), "about_building", "ACROSS: differs from its building's text"))
                break
        ok = set()
        for u in us:
            ok |= T.allowed_numbers(u, (len(us), len(in_hood.get(b.get("hood_id")) or [])))
        ok |= {str(len(us)), str(len(in_hood.get(b.get("hood_id")) or []))}
        for f, text in [("about_building", about)] + [(f"about_points[{i}]", str(p.get("text") or "")) for i, p in enumerate(pts)]:
            if not text:
                continue
            for p in T.guard(text, T.mask(text, first)):
                out.append(Fail("text", "building", bid, f, "PLAIN: " + p, text[:160]))
            for n in T.numbers(T.mask(text, first)):
                if n not in ok:
                    out.append(Fail("text", "building", bid, f, f"NUMBER: '{n}' is not a field of this building or its apartments", text[:160]))
            place_claims(f, text, first, ctx, out, "building", bid)
    return ctx


# ---------------------------------------------------------------------------------------------------------------
# 4-5 for neighborhoods: pattern -> the buildings shown, and against the buildings' own published text

HOOD_DIST = [(re.compile(r"\b(?:dog park|dog run)\b[^.;,]*?\b(\d+\.\d) miles", re.I), "dog_park_m", "mi"),
             (re.compile(r"\bsupermarket\b(?: is)?(?: at)? (\d+\.\d) miles", re.I), "supermarket_m", "mi"),
             (re.compile(r"\btrain station\b(?: is)? (\d+\.\d) miles", re.I), "train_station_m", "mi"),
             (re.compile(r"\b[Pp]ark\b(?: is)? about (\d+) minutes", re.I), "park_walk_min", "int"),
             (re.compile(r"\b[Aa]bout (\d+) restaurants\b", re.I), "restaurants_800m", "int")]
EVERY_HAS = [(re.compile(r"\bevery building (?:shown )?here has (?:a |its own )?(doorman|pool|gym|garage|dog area)", re.I))]
EVERY_TEST = {"doorman": lambda u: R.desk_kind(_am(u)) in ("doorman", "doorman24"), "pool": lambda u: bool(_am(u).get("pool")),
              "gym": lambda u: _am(u).get("gym") == "yes", "garage": lambda u: _pk(u) == "garage", "dog area": _dog_area}


def hood_fields(h):
    p, heads = h.get("prose") or {}, h.get("headlines") or {}
    out = [("prose.scene", p.get("scene")), ("prose.good_for_her", p.get("good_for_her")), ("prose.watch_for", p.get("watch_for")),
           ("host.intro", (h.get("host") or {}).get("intro"))]
    out += [(f"about_points[{i}]", x.get("text")) for i, x in enumerate(h.get("about_points") or [])]
    out += [(f"headlines.{k}.subhead", (v or {}).get("subhead")) for k, v in heads.items()]
    return [(f, str(t)) for f, t in out if t]


def audit_hood_claims(d, ctx, out):
    bt = G.table(G.DOOR_SOURCE)
    for h in d.get("neighborhoods") or []:
        hid = h["id"]
        blds = ctx["buildings_in_hood"].get(hid) or []
        if not blds or (h.get("prose") or {}).get("inherited_from"):
            continue
        mine = bt[bt["hood_id"].astype(str) == hid]
        firsts = [ctx["first_unit"][b["id"]] for b in blds]
        n_units = sum(len(ctx["by_building"][b["id"]]) for b in blds)
        b_text = " ".join(" ".join([b.get("about_building") or ""] + [str(p.get("text") or "") for p in b.get("about_points") or []])
                          for b in blds)
        own_in_text = len(re.findall(r"has its own dog (?:park|run)", b_text))
        for f, text in hood_fields(h):
            for sent in sents(text):
                if "vet" not in sent.lower():
                    for rx, col, how in HOOD_DIST:
                        for m in rx.finditer(sent):
                            v = G._median(mine[col].tolist())
                            want = G.transform(v, how)
                            if want is None or m.group(1) != want:
                                out.append(Fail("text", "neighborhood", hid, f, f"CLAIM: \"{m.group(0)}\", and the median of the "
                                                f"{len(blds)} building(s) shown reads {want}", sent))
                m = re.search(r"\b(\d+) apartments\b", sent)
                if m and int(m.group(1)) != n_units and not re.search(r"\bof the\b", sent[:m.start()][-12:]):
                    out.append(Fail("text", "neighborhood", hid, f, f"CLAIM: \"{m.group(0)}\", and {n_units} are shown here", sent))
                almost = 1 if re.search(r"\balmost no", sent, re.I) else 0          # "almost no" allows 1
                if re.search(r"\bno bars?\b(?! or)|\bno bar is within\b", sent, re.I) and G.half_up(G._median(mine["bars_800m"].tolist()) or 0) > almost:
                    out.append(Fail("text", "neighborhood", hid, f, "CLAIM: \"no bars\", and the buildings shown have bars within a walk", sent))
                if re.search(r"\bno restaurants?\b|\bnothing to eat\b", sent, re.I) and G.half_up(G._median(mine["restaurants_800m"].tolist()) or 0) > almost:
                    out.append(Fail("text", "neighborhood", hid, f, "CLAIM: \"no restaurants\", and the buildings shown have restaurants within a walk", sent))
                m = re.search(r"about (\d+) minutes (?:from your parents|away|from their door)|parents (?:are|is) about (\d+) minutes", sent)
                if m and "parents" in sent and not re.search(r"train|bus", sent):
                    got = m.group(1) or m.group(2)
                    if G.transform(h.get("drive_min"), "int") != got:
                        out.append(Fail("text", "neighborhood", hid, f, f"CLAIM: \"{got} minutes\" to her parents, and drive_min reads "
                                        f"{G.transform(h.get('drive_min'), 'int')}", sent))
                m = re.search(r"about \$(\d+) round trip with a New York E-ZPass", sent)
                if m and G.transform(h.get("toll_round_trip"), "int") != m.group(1):
                    out.append(Fail("text", "neighborhood", hid, f, f"CLAIM: a toll of ${m.group(1)}, and toll_round_trip reads "
                                    f"{h.get('toll_round_trip')}", sent))
                if re.search(r"\bno tolls?\b", sent, re.I) and (h.get("toll_round_trip") or 0) > 0:
                    out.append(Fail("text", "neighborhood", hid, f, "CLAIM: \"no tolls\", and toll_round_trip is above 0", sent))
                for rx in EVERY_HAS:
                    m = rx.search(sent)
                    if m and not all(EVERY_TEST[m.group(1).lower()](u) for u in firsts):
                        out.append(Fail("text", "neighborhood", hid, f, f"CLAIM: \"every building here has a {m.group(1)}\" is not so", sent))
                if re.search(r"\bbuilding has its own dog area\b", sent) and not all(_dog_area(u) for u in firsts):
                    out.append(Fail("text", "neighborhood", hid, f, "CLAIM: \"its own dog area\", and a shown building lists none", sent))
                if re.search(r"\bbuilding has its own garage\b", sent) and not all(_pk(u) == "garage" for u in firsts):
                    out.append(Fail("text", "neighborhood", hid, f, "CLAIM: \"its own garage\", and a shown building has none", sent))
                # 5. against the buildings' own published text
                if own_in_text and (G.NO_OWN_DOG.search(sent) or (G.DOG_PLACE.search(sent) and G.DOG_LAMENT.search(sent)
                                                                  and "public" not in sent)):
                    out.append(Fail("text", "neighborhood", hid, f, f"ACROSS: complains about the dog park, above {own_in_text} "
                                    "building text(s) on this page that say \"its own dog park\"", sent))
                if len(blds) == 1 and re.search(r"\bnothing to eat\b|\bno restaurants?\b", sent, re.I):
                    m2 = re.search(r"(\d+) restaurants? (?:is|are) within", b_text)
                    if m2 and int(m2.group(1)) > 0:
                        out.append(Fail("text", "neighborhood", hid, f, f"ACROSS: says nothing to eat is within a walk, above its "
                                        f"building's \"{m2.group(0)}\"", sent))
                if G.GARAGE_ADVICE.search(sent) and all(re.search(r"\bgarage\b", " ".join([b.get("about_building") or ""] + [
                        str(p.get("text") or "") for p in b.get("about_points") or [] if p.get("icon") != "warning"]), re.I) for b in blds):
                    out.append(Fail("text", "neighborhood", hid, f, "ACROSS: advises looking for a garage, above building texts that "
                                    "all say they have one", sent))


# ---------------------------------------------------------------------------------------------------------------
# 6. The pipeline's own strings: vocabulary and stale wording only

PIPELINE_TERMS = re.compile(r"\bevidence pass\b|\bharvest(?:ed)? row\b|\bdocs/|\bPENDING_FIXES\b|\bstored value\b|\bunit prefix|"
                            r"\brefused us\b|\bnet[- ]effective\b|\blisting sites disagree\b|\bnot re-?read\b|\bre-?read\b|"
                            r"\bscorecard\b|\bgate fact\b|\bverdict\b|\baggregator\b|\bvalue_type\b|\b[a-z]+_[a-z_]+\b", re.I)


def pipeline_strings(d):
    for u in d.get("units") or []:
        uid = u.get("id")
        c = u.get("confirm") or {}
        for k in ("what", "why", "question"):
            if c.get("asterisk") and c.get(k):
                yield "apartment", uid, f"confirm.{k}", str(c[k])
        for i, x in enumerate(u.get("disclosures") or []):
            if isinstance(x, dict):
                for k in ("what", "why", "question"):
                    if x.get(k):
                        yield "apartment", uid, f"disclosures[{i}].{k}", str(x[k])
        for i, q in enumerate(u.get("tour_questions") or []):
            yield "apartment", uid, f"tour_questions[{i}]", str(q)
        for i, x in enumerate(u.get("all_in_lines") or []):
            if isinstance(x, dict):
                for k in ("line", "note"):
                    if x.get(k):
                        yield "apartment", uid, f"all_in_lines[{i}].{k}", str(x[k])
        for k in ("all_in_likely_note",):
            if u.get(k):
                yield "apartment", uid, k, str(u[k])
    meta = d.get("meta") or {}
    for i, n in enumerate(meta.get("notes") or []):
        yield "meta", "notes", f"notes[{i}]", str(n)
    for k, v in (meta.get("moment_thresholds") or {}).items():
        for kk, vv in (v or {}).items():
            yield "meta", "moment_thresholds", f"{k}.{kk}", str(vv)


def audit_pipeline(d, out):
    seen = Counter()
    for kind, oid, field, text in pipeline_strings(d):
        probs = []
        for rx, what in G.VOCAB + G.STALE + G.CONCEITS:
            m = rx.search(text)
            if m:
                probs.append(f"{what}: '{m.group(0)}'")
        m = PIPELINE_TERMS.search(text)
        if m:
            probs.append(f"project term '{m.group(0)}'")
        hit = G.agency(text)
        if hit:
            probs.append(f"a thing as the subject of a verb of intention: '{hit}'")
        for p in probs:
            key = (re.sub(r"\[\d+\]", "[]", field), p)
            seen[key] += 1
            if seen[key] <= 3:                            # the same fault on hundreds of apartments is printed three times
                out.append(Fail("pipeline", kind, oid, field, "STALE/VOCAB: " + p, text[:200]))
    for (field, p), n in seen.items():
        if n > 3:
            out.append(Fail("pipeline", "summary", "-", field, f"STALE/VOCAB: {p}: {n} strings in all"))


# ---------------------------------------------------------------------------------------------------------------
# The page template: informational

def audit_template(out, path=TEMPLATE):
    if not Path(path).exists():
        return
    src = Path(path).read_text(encoding="utf-8")
    for i, line in enumerate(src.split("\n"), 1):
        for m in re.finditer(r"\"((?:[^\"\\]|\\.){12,240})\"|'((?:[^'\\]|\\.){12,240})'", line):
            t = m.group(1) or m.group(2)
            if t.count(" ") < 2 or re.search(r"[<>{};=]|function|var ", t):
                continue
            probs = [f"{what}: '{x.group(0)}'" for rx, what in G.CONCEITS + G.STALE for x in [rx.search(t)] if x]
            hit = G.agency(t)
            if hit:
                probs.append(f"a thing as the subject of a verb of intention: '{hit}'")
            if re.search(r"\b[Aa]n one-bedroom\b|\bunit\b", t):
                probs.append("template wording ('An one-bedroom' / 'unit')")
            for p in probs:
                out.append(Fail("template", "site/index.html", f"line {i}", "string", p, t[:160]))


# ---------------------------------------------------------------------------------------------------------------

def audit(d, template=False):
    """-> [Fail]. Every check on this page data."""
    use_page(d)
    out = []
    audit_scene(d, out)
    ctx = audit_places(d, out)
    audit_hood_claims(d, ctx, out)
    audit_pipeline(d, out)
    if template:
        audit_template(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--text-only", action="store_true", help="exit code from the written text only")
    ap.add_argument("--template", action="store_true", help="also scan site/index.html (informational)")
    ap.add_argument("--max", type=int, default=400, help="print at most this many failures per owner")
    a = ap.parse_args(argv)
    d = json.loads(Path(a.data).read_text(encoding="utf-8"))
    fails = audit(d, template=a.template)
    by = defaultdict(list)
    for f in fails:
        by[f.owner].append(f)
    for owner in ("text", "pipeline", "template"):
        for f in by[owner][:a.max]:
            print("FAIL " + str(f))
        if len(by[owner]) > a.max:
            print(f"... and {len(by[owner]) - a.max} more for owner '{owner}'")
    n = {k: len(v) for k, v in by.items()}
    counts = (f"{len(d.get('years') or [])} experiences, {len(d.get('neighborhoods') or [])} neighborhoods, "
              f"{len(d.get('buildings') or [])} buildings, {len(d.get('units') or [])} apartments read")
    print(f"check_published_text: {counts}; failures: text {n.get('text', 0)}, pipeline strings {n.get('pipeline', 0)}"
          + (f", template {n.get('template', 0)} (informational)" if a.template else ""))
    bad = n.get("text", 0) + (0 if a.text_only else n.get("pipeline", 0))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
