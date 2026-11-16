#!/usr/bin/env python3
"""Turn the hand-written drafts in data/reference/scene_text_source.txt into the two scene-text CSVs.

The drafts are prose written by hand. Numbers are never typed: each one is a token that names a measured field,
so the builder fills the number in from the data and writes the matching evidence item. Nothing is generated; if a
token's value is missing the build stops, and the sentence has to be rewritten without it.

Tokens
  {alias}            the value, rounded the alias's usual way      {drive} -> 38
  {alias:how}        the value, rounded another way                {drive:r5} -> 40   (int 1dp r5 r10 pct mi mi0 str time12)
  {!alias OP value}  nothing is printed; the sentence is recorded as resting on this field, and the checker
                     re-tests it later                             {!bars==0}  {!b_tollok==False}  {!viol missing}
  {w10}  {mile}      the fixed wordings for the 800 m and 1,600 m search radii ("10-minute walk", "1 mile")
  [[ ... ]]          an optional stretch of text: dropped whole when any value inside it is missing or any hidden
                     test inside it fails, so a fact that is not in the data is simply not said
Lines
  === year: <label>      then  scene: / promise: / catch: / display: / tagline: / host_intro: / walk1: walk2: walk3:
  === hood: <hood_id>    then  scene: / good: / watch: / host_intro: , and optionally
      rules: Municipality|rule ; Municipality|rule      numbers typed in the prose must come from these summaries
      voices: theme, theme                              themes whose balance of comments the prose paraphrases
  A block may appear twice (the host voice sits in its own section of the file); the two are merged, and their
  rules: and voices: lines are added together.
Year tokens: m_ / max_ / min_ + a neighborhood alias (median neighborhood, lifestyle_groups.csv); p_... the page's own
  unit-weighted tile figures (site/data.json years[]); u_... medians and shares over the units shown on the page.
Neighborhood tokens: the aliases in HOOD; b_... over the neighborhood's buildings (tolls come from data/enriched);
  pg_... the page's all-in range for the neighborhood (use inside [[ ]]: a neighborhood can leave the page).

Run from the house-hunt folder: python3 scripts/build_scene_text.py && python3 scripts/check_scene_text.py
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_scene_text as C  # noqa: E402

ROOT = C.ROOT
SOURCE = ROOT / "data/reference/scene_text_source.txt"
LG, MB, GX = "data/lifestyle_groups.csv", "data/master_buildings.csv", "data/group_exchange.csv"
RULES, QUOTES = "data/reference/local_rules.csv", "data/voices/neighborhood_quotes.csv"
RULES2, QUOTES2 = "data/reference/local_rules_round2.csv", "data/voices/neighborhood_quotes_round2.csv"
TOLLS, PAGE_Y, PAGE_H, PAGE_U = C.TOLLS, C.PAGE + "#years", C.PAGE + "#neighborhoods", C.PAGE + "#units"

# alias: (field in lifestyle_groups.csv, usual rounding)
HOOD = {
    "drive": ("drive_min", "int"), "transit": ("transit_to_parents_min", "int"),
    "viol": ("violent", "1dp"), "prop": ("property", "1dp"), "mvt": ("motor_vehicle_theft", "1dp"),
    "rest": ("restaurants_800m", "int"), "bars": ("bars_800m", "int"), "cafes": ("cafes_800m", "int"),
    "rest1600": ("restaurants_1600m", "int"), "brew": ("breweries_1600m", "int"), "music": ("music_1600m", "int"),
    "parkwalk": ("park_walk_min", "int"), "parkha": ("park_ha_800m", "int"),
    "dogpark": ("dog_park_m", "mi"), "water": ("open_water_m", "mi"), "beach": ("beach_m", "mi"),
    "super": ("supermarket_m_c", "mi"), "tj": ("trader_joes_m", "mi"), "vet": ("vet_m", "mi"),
    "station": ("train_station_m_c", "mi"),
    "nocar": ("no_car_share", "pct"), "detached": ("detached_house_share", "pct"),
    "bigbldg": ("big_building_share", "pct"), "renters": ("renter_share", "pct"),
    "alone": ("living_alone_share", "pct"), "newcomers": ("newcomer_share", "pct"), "wfh": ("wfh_share", "pct"),
    "young": ("age_25_34_share", "pct"), "pre1940": ("built_before_1940_share", "pct"),
    "post2010": ("built_since_2010_share", "pct"), "yrbuilt": ("median_year_built", "int"),
    "kids": ("households_with_kids_share", "pct"), "sqft": ("unit_sqft", "r10"),
    "police": ("police", "str"),
}
# alias: (field in master_buildings.csv, aggregation over the neighborhood's buildings, usual rounding)
BLDG = {
    "b_toll": ("toll_round_trip_ezpass", "median", "int"), "b_tollmax": ("toll_round_trip_ezpass", "max", "int"),
    "b_tollok": ("complete", "all_true", "str"),
    "b_station": ("train_station", "mode", "str"), "b_dogpark": ("dog_park_name", "mode", "str"),
    "b_park": ("park_name", "mode", "str"), "b_super": ("supermarket", "mode", "str"),
    "b_lasttrain": ("last_sat_departure", "mode", "time12"),
}
FROM_TOLLS = {"b_toll", "b_tollmax", "b_tollok"}       # read from data/enriched, not master_buildings.csv
# alias: (column of site/data.json#neighborhoods, usual rounding)
HOOD_PAGE = {"pg_lo": ("all_in_lo", "usd50"), "pg_hi": ("all_in_hi", "usd50"), "pg_n": ("shown", "int"),
             "pg_sqft": ("sqft_median", "r10"), "pg_safe": ("violent_pctile", "pct"),
             # the page's 1-to-5 comparison with the Queens median (3 = about the same, 5 = much better for her)
             "q_cost": ("vq_all_in", "int"), "q_sqft": ("vq_sqft", "int"), "q_drive": ("vq_drive_min", "int"),
             "q_food": ("vq_food_and_drink_nearby", "int"), "q_green": ("vq_walk_to_green", "int")}
# alias: (column of site/data.json#years, usual rounding)   the page's own tile figures
YEAR_PAGE = {
    "p_allin": ("all_in", "usd50"), "p_allin_lo": ("all_in_lo", "usd50"), "p_allin_hi": ("all_in_hi", "usd50"),
    "p_sqft": ("sqft", "r10"), "p_drive": ("drive_min", "int"), "p_drive_lo": ("drive_min_lo", "int"),
    "p_drive_hi": ("drive_min_hi", "int"), "p_transit": ("transit_min", "r5"),
    "p_viol": ("violent_per_1000", "1dp"), "p_prop": ("property_per_1000", "1dp"),
    "p_rest": ("restaurants_800m", "int"), "p_parkwalk": ("park_walk_min", "int"),
    "p_hoods": ("neighborhoods", "int"), "p_places": ("shown", "int"),
    "p_near": ("nearest_name", "str"), "p_near_drive": ("nearest_drive_min", "int"),
    "q_cost": ("vq_all_in", "int"), "q_sqft": ("vq_sqft", "int"), "q_drive": ("vq_drive_min", "int"),
    "q_food": ("vq_food_and_drink_nearby", "int"), "q_green": ("vq_walk_to_green", "int"),
}
# alias: (column of site/data.json#units, aggregation over the year's shown units, usual rounding)
YEAR_UNITS = {
    "u_toll": ("toll_rt", "median", "int"), "u_tollmax": ("toll_rt", "max", "int"),
    "u_dogpark": ("dog_park_m", "median", "mi"), "u_super": ("supermarket_m", "median", "mi"),
    "u_cafes": ("cafes_800m", "median", "int"), "u_bars": ("bars_800m", "median", "int"),
    "u_rest1600": ("restaurants_1600m", "median", "int"), "u_bars1600": ("bars_1600m", "median", "int"),
    "u_garage": ("garage_or_covered", "mean", "pct"), "u_parkpub": ("parking_published", "mean", "pct"),
    "u_pool": ("pool", "mean", "pct"), "u_doorman": ("doorman", "mean", "pct"), "u_gym": ("gym", "mean", "pct"),
    "u_laundry": ("in_unit_laundry", "mean", "pct"), "u_n": ("listing_id", "count", "int"),
}
CONVENTION = {
    "w10": ("10-minute walk", "restaurants_800m", "800 m radius, written as a 10-minute walk"),
    "mile": ("1 mile", "restaurants_1600m", "1,600 m radius, written as 1 mile"),
}
# numbers that are part of a field's definition, allowed wherever that field is cited
DEFINITION = {"built_before_1940_share": "before 1940", "built_since_2010_share": "since 2010",
              "age_25_34_share": "aged 25 to 34"}
JAMAICA = {"jv": ("jamaica_violent", "1dp"), "jp": ("jamaica_property", "1dp")}
TOKEN = re.compile(r"\{(!?)([a-z_0-9]+)(?::([a-z0-9]+))?\s*(?:(==|!=|<=|>=|<|>|missing|present)\s*([^}]*))?\}")


def resolve(alias, ctx):
    """-> (source_file, field, row, agg, usual rounding)"""
    if alias in JAMAICA:
        f, how = JAMAICA[alias]
        return LG, f, {"hood_id": "ny:jamaica"}, None, how
    if ctx["kind"] == "hood":
        if alias in HOOD:
            f, how = HOOD[alias]
            return LG, f, {"hood_id": ctx["id"]}, None, how
        if alias in BLDG:
            f, agg, how = BLDG[alias]
            return (TOLLS if alias in FROM_TOLLS else MB), f, {"hood_id": ctx["id"]}, agg, how
        if alias in HOOD_PAGE:
            f, how = HOOD_PAGE[alias]
            return PAGE_H, f, {"hood_id": ctx["id"]}, None, how
    else:
        if alias in YEAR_PAGE:
            f, how = YEAR_PAGE[alias]
            return PAGE_Y, f, {"year_label": ctx["id"]}, None, how
        if alias in YEAR_UNITS:
            f, agg, how = YEAR_UNITS[alias]
            return PAGE_U, f, {"year_label": ctx["id"]}, agg, how
        row = {"group_label": ctx["id"], "safety_cut": False}
        for pre, agg in (("m_", "median"), ("max_", "max"), ("min_", "min")):
            if alias.startswith(pre) and alias[len(pre):] in HOOD:
                f, how = HOOD[alias[len(pre):]]
                return LG, f, row, agg, how
        if alias == "n_hoods":
            return LG, "hood_id", row, "count", "int"
        if alias.startswith("x_") and alias[2:] in C.table(GX).columns:   # the page's own unit-weighted year figures
            return GX, alias[2:], {"group": ctx["id"]}, None, "int"
    raise KeyError(f"{ctx['id']}: unknown token {{{alias}}}")


def drop_optional(raw, ctx):
    """[[ ... ]] stays only when every value inside it is present and every hidden test inside it holds."""
    def keep(m):
        for t in TOKEN.finditer(m.group(1)):
            hidden, alias, _, op, operand = t.groups()
            if alias in CONVENTION:
                continue
            try:
                src, field, row, agg, _ = resolve(alias, ctx)
                value = C.lookup(src, field, row, agg)
            except LookupError:
                return ""
            if hidden and op:
                if not C.holds(value, [op] if op in ("missing", "present") else [op, operand.strip()]):
                    return ""
            elif C.is_missing(value):
                return ""
        return m.group(1)
    return re.sub(r"\[\[(.*?)\]\]", keep, raw)


def render(raw, ctx, evidence):
    raw = drop_optional(raw, ctx)
    out = []
    held = []                                         # tokens are set aside so a full stop inside one cannot split a sentence

    def hold(m):
        held.append(m.group(0))
        return f"\x00{len(held) - 1}\x00"

    for sent in C.sentences(TOKEN.sub(hold, raw)):
        sent = re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], sent)
        pending = []

        def sub(m):
            hidden, alias, how, op, operand = m.groups()
            if alias in CONVENTION:
                words, field, note = CONVENTION[alias]
                pending.append({"field": field, "value": note, "source_file": LG, "transform": "convention",
                                "shown": [words]})
                return words
            src, field, row, agg, usual = resolve(alias, ctx)
            value = C.lookup(src, field, row, agg)
            ev = {"field": field, "value": value, "source_file": src, "row": row}
            extra = [DEFINITION[field]] if field in DEFINITION else []
            if agg:
                ev["agg"] = agg
            if hidden:
                if not op:
                    raise ValueError(f"{ctx['id']}: {{!{alias}}} needs a test, such as {{!{alias}==0}}")
                operand = operand.strip()
                test = [op] if op in ("missing", "present") else [op, operand]
                if not C.holds(value, test):
                    raise ValueError(f"{ctx['id']}: {alias} is {value}, which fails {test}: {sent[:80]}")
                ev["holds_if"] = test
                if extra:
                    ev["transform"], ev["shown"] = usual, [C.transform(value, usual)] + extra
                pending.append(ev)
                return ""
            shown = C.transform(value, how or usual)
            if shown is None:
                raise ValueError(f"{ctx['id']}: {alias} is missing; rewrite without it: {sent[:80]}")
            ev["transform"], ev["shown"] = how or usual, [shown] + extra
            pending.append(ev)
            return shown

        text = TOKEN.sub(sub, sent)
        if "{" in text or "}" in text:
            raise ValueError(f"{ctx['id']}: unparsed token in: {text}")
        text = re.sub(r"\s+([.,;])", r"\1", re.sub(r"\s{2,}", " ", text)).strip()
        for ev in pending:
            evidence.append({"claim": text, **ev})
        out.append(text)
    return " ".join(out)


def attach_rules(ctx, spec, texts, evidence):
    cited = []
    for part in [p.strip() for p in spec.split(";") if p.strip()]:
        muni, rule = [x.strip() for x in part.split("|")]
        found = False
        for rules_file in (RULES, RULES2):
            row = {"municipality": muni, "rule": rule, "value_type": "found"}
            for s in C.lookup(rules_file, "summary", row, "any_row"):
                found = True
                cited.append({"claim": f"local rule cited: {muni}, {rule}", "field": "summary", "value": s,
                              "source_file": rules_file, "row": row, "agg": "any_row", "transform": "in_text",
                              "shown": []})
        if not found:
            raise ValueError(f"{ctx['id']}: no found rule {muni}|{rule}")
    covered = set()
    for ev in evidence:
        covered |= set(C.numbers_in(" ".join(ev.get("shown", []))))
    used = []
    for text in texts.values():
        for n in C.numbers_in(text):
            if n in covered:
                continue
            for ev in cited:
                if n in C.numbers_in(ev["value"]):
                    ev["shown"].append(n)
                    if ev not in used:
                        used.append(ev)
                    break
    # keep every rule summary that supplied a number, and the first summary of each cited rule
    seen = set()
    for ev in cited:
        k = (ev["source_file"], ev["row"]["municipality"], ev["row"]["rule"])
        if ev in used or k not in seen and not any(u["row"] == ev["row"] and u["source_file"] == ev["source_file"] for u in used):
            evidence.append(ev)
        seen.add(k)


def attach_voices(ctx, spec, texts, evidence):
    claim = " ".join(s for t in texts.values() for s in C.sentences(t) if C.VOICE_PHRASE.search(s))
    if not claim:
        raise ValueError(f"{ctx['id']}: voices cited but no sentence says 'review sites' or 'people who live here'")
    for theme in dict.fromkeys(t.strip() for t in spec.split(",") if t.strip()):
        row, n = {"hood_id": ctx["id"], "theme": theme}, 0
        for quotes_file in (QUOTES, QUOTES2):
            counts = C.lookup(quotes_file, "sentiment", row, "sentiment_counts")
            if counts != "positive=0;mixed=0;negative=0":
                n += 1
                evidence.append({"claim": claim, "field": "sentiment", "value": counts, "source_file": quotes_file,
                                 "row": row, "agg": "sentiment_counts"})
        if not n:
            raise ValueError(f"{ctx['id']}: no quotes on {theme}")


def parse(path):
    blocks, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = re.match(r"=== sub: (year|hood)\.(\w+)", line)
        if m:                                             # conditional drafts for a section subhead
            cur = {"kind": "sub", "id": (m.group(1), m.group(2)), "rules": []}
            blocks.append(cur)
            continue
        if cur is not None and cur["kind"] == "sub":
            if not line.startswith("==="):
                conds, sep, variants = line.partition("::")
                if not sep:
                    raise ValueError(f"cannot read subhead draft: {line[:80]}")
                cur["rules"].append(([c.strip() for c in conds.split(",") if c.strip()],
                                     [v.strip() for v in variants.split("|") if v.strip()]))
                continue
        m = re.match(r"=== (year|hood): (.+)", line)
        if m:
            key = (m.group(1), m.group(2).strip())
            cur = next((b for b in blocks if (b["kind"], b["id"]) == key), None)
            if cur is None:
                cur = {"kind": key[0], "id": key[1], "f": {}}
                blocks.append(cur)
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if cur is None or not _:
            raise ValueError(f"cannot read line: {line[:80]}")
        if k in ("rules", "voices"):                  # a second block adds to the first block's citations
            sep = "; " if k == "rules" else ", "
            cur["f"][k] = sep.join(x for x in (cur["f"].get(k, ""), v) if x)
        elif k in cur["f"]:
            raise ValueError(f"{cur['id']}: '{k}:' appears twice")
        else:
            cur["f"][k] = v
    return blocks


COND = re.compile(r"^(?:v:(\w+):(positive|mixed|negative)|rule:(\w+)(?:~(.+))?|([a-z_0-9]+))\s*(==|!=|<=|>=|<|>)?\s*(.*)$")


def hood_rules(hood_id, rule, pattern=None):
    """Found local rules of this kind that apply to the neighborhood (and whose summary matches `pattern`, when one
    is given: "rule:overnight_parking~banned|prohibited") -> [(file, municipality, summary)]."""
    out = []
    for f in (RULES, RULES2):
        t = C.table(f)
        if "applies_to_hood_ids" not in t.columns:
            continue
        for r in t[(t.value_type == "found") & (t.rule == rule)].itertuples():
            ids = [x.strip() for x in str(r.applies_to_hood_ids).split(";")]
            if pattern and not re.search(pattern, str(r.summary), re.I):
                continue
            if any(hood_id == i or hood_id.startswith(i + "-") for i in ids if i and i != "nan"):
                out.append((f, r.municipality, r.summary))
    return out


SUB_MIN_WORDINGS = 5                                   # wordings per condition in the "=== sub:" drafts
SUB_USED = {}                                          # (kind, section) -> Counter of wordings used so far in this build


def pick_sub(rules, ctx, salt, cap=None):
    """The first draft whose conditions all hold for this row -> (sentence, evidence). ('' , []) when none does.
    Every condition becomes an evidence item with a test, so the checker re-runs it after a data change. The wording
    is the first one, in an order seeded by the row's id, that has not reached `cap` uses in this build; when every
    wording of the matching draft has, the subhead stays empty (better than the same line once more)."""
    import hashlib
    from collections import Counter
    used = SUB_USED.setdefault((ctx["kind"], salt), Counter())
    for conds, variants in rules:
        evs, ok = [], True
        for cond in conds:
            m = COND.match(cond)
            if not m:
                raise ValueError(f"cannot read condition '{cond}'")
            theme, sent, rule, pattern, alias, op, operand = m.groups()
            operand = operand.strip()
            if theme:                                     # v:parking:negative>=1  (residents' comments, both files)
                if ctx["kind"] != "hood":
                    ok = False
                    break
                n, items = 0, []
                for qf in (QUOTES, QUOTES2):
                    row = {"hood_id": ctx["id"], "theme": theme}
                    counts = C.lookup(qf, "sentiment", row, "sentiment_counts")
                    n += int(dict(x.split("=") for x in counts.split(";"))[sent])
                    if counts != "positive=0;mixed=0;negative=0":
                        items.append({"field": "sentiment", "value": counts, "source_file": qf, "row": row,
                                      "agg": "sentiment_counts"})
                if not C.holds(n, [op or ">=", operand or "1"]):
                    ok = False
                    break
                evs += items
            elif rule:                                    # rule:overnight_parking  (a found local rule applies here)
                found = hood_rules(ctx["id"], rule, pattern) if ctx["kind"] == "hood" else []
                if not found:
                    ok = False
                    break
                f, muni, summary = found[0]
                evs.append({"field": "summary", "value": summary, "source_file": f,
                            "row": {"municipality": muni, "rule": rule, "value_type": "found"}, "agg": "any_row",
                            "transform": "in_text", "shown": []})
            else:
                try:
                    src, field, row, agg, _ = resolve(alias, ctx)
                    value = C.lookup(src, field, row, agg)
                except (KeyError, LookupError):
                    ok = False
                    break
                test = [op, operand]
                if not op or not C.holds(value, test):
                    ok = False
                    break
                ev = {"field": field, "value": value, "source_file": src, "row": row, "holds_if": test}
                if agg:
                    ev["agg"] = agg
                evs.append(ev)
        if ok:
            i = int(hashlib.sha1(f"{ctx['id']}|{salt}".encode()).hexdigest()[:8], 16) % len(variants)
            for text in variants[i:] + variants[:i]:
                if cap is None or used[text] < cap:
                    used[text] += 1
                    return text, [{"claim": text, **e} for e in evs]
            return "", []
    return "", []


YEAR_COLS = {"display": "display_label", "tagline": "tagline", "subhead": "subhead", "scene": "scene", "promise": "promise", "catch": "catch",
             "host_intro": "host_intro"}
HOOD_COLS = {"scene": "scene", "good": "good_for_her", "watch": "watch_for", "host_intro": "host_intro"}
WALK = ["walk1", "walk2", "walk3"]                    # a weekday, a Saturday night, a Sunday with her parents


def main():
    lg = C.table(LG).set_index("hood_id")
    years, hoods, errors, stale = [], [], [], []
    blocks = parse(SOURCE)
    subs = {b["id"]: b["rules"] for b in blocks if b["kind"] == "sub"}
    SUB_USED.clear()
    for (kind, section), rules in subs.items():
        for conds, variants in rules:
            if len(variants) < SUB_MIN_WORDINGS or len(set(variants)) < len(variants):
                errors.append(f"sub {kind}.{section} [{', '.join(conds)}]: {len(set(variants))} different wordings, "
                              f"wanted at least {SUB_MIN_WORDINGS}")
    n_hoods = sum(1 for b in blocks if b["kind"] == "hood" and b["id"] in lg.index)
    sub_cap = {"hood": int(n_hoods * C.SUB_SHARE), "year": None}
    closes = {}
    for b in blocks:
        if b["kind"] == "sub":
            continue
        ctx, f, evidence = {"kind": b["kind"], "id": b["id"]}, b["f"], []
        cols = YEAR_COLS if b["kind"] == "year" else HOOD_COLS
        if b["kind"] == "hood" and b["id"] not in lg.index:       # the data no longer has this neighborhood
            stale.append(b["id"])
            continue
        try:
            lacking = [k for k in list(cols) + (WALK if b["kind"] == "year" else []) if not f.get(k)]
            if lacking:
                raise ValueError(f"{b['id']}: no text for {lacking}")
            texts = {out: render(f[src], ctx, evidence) for src, out in cols.items()}
            if b["kind"] == "year":
                texts["host_walkthrough"] = "\n\n".join(render(f[k], ctx, evidence) for k in WALK)
            if b["kind"] == "hood":
                if f.get("rules"):
                    attach_rules(ctx, f["rules"], texts, evidence)
                if f.get("voices"):
                    attach_voices(ctx, f["voices"], texts, evidence)
                elif any(C.VOICE_PHRASE.search(t) for t in texts.values()):
                    raise ValueError(f"{b['id']}: paraphrases residents without a voices: line")
                # close: says what the last sentence of the host_intro turns on (see the note above the hood intros)
                tag = f.get("close", "")
                if tag not in C.CLOSE_KINDS:
                    raise ValueError(f"{b['id']}: 'close:' must be one of {C.CLOSE_KINDS}, found '{tag}'")
                if (tag == "drive") != C.ends_on_drive(texts["host_intro"]):
                    raise ValueError(f"{b['id']}: close: {tag}, but the last sentence reads otherwise: "
                                     f"{C.closing(texts['host_intro'])}")
                closes[b["id"]] = tag
            for section in C.SUB_SECTIONS[b["kind"]]:
                texts["sub_" + section], evs = pick_sub(subs.get((b["kind"], section), []), ctx, section,
                                                         sub_cap[b["kind"]])
                evidence += evs
            problems, _ = C.check_row(b["kind"], b["id"], texts, evidence)
            errors += [f"{b['id']}: {p}" for p in problems]
        except (KeyError, ValueError, LookupError) as e:
            errors.append(str(e))
            continue
        ej = json.dumps(evidence, ensure_ascii=False)
        if b["kind"] == "year":
            years.append({"year_label": b["id"], **{c: texts[c] for c in C.COLUMNS["year"]}, "evidence_json": ej})
        else:
            hoods.append({"hood_id": b["id"], "hood_name": lg.loc[b["id"], "hood"],
                          "year_label": lg.loc[b["id"], "group_label"], **{c: texts[c] for c in C.COLUMNS["hood"]},
                          "evidence_json": ej})
    for col, rows, key in (("host_intro", years, "year_label"), ("host_intro", hoods, "hood_id")):
        errors += C.check_repetition(col, {r[key]: r[col] for r in rows})
    errors += C.check_closings("host_intro", {r["hood_id"]: r["host_intro"] for r in hoods})
    errors += C.check_sub_shares("hood", hoods)
    from collections import Counter
    kinds = Counter(closes.values())
    if hoods and len([k for k, n in kinds.items() if n >= 3]) < 6:
        errors.append(f"host_intro closes: fewer than 6 kinds of close are in real use: {dict(kinds)}")
    for name, rows in ((C.YEARS, years), (C.HOODS, hoods)):
        if rows:
            with open(name, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    print(f"{len(years)} years, {len(hoods)} neighborhoods written; {len(errors)} problems")
    print(f"host_intro closes by kind: {dict(kinds.most_common())}")
    for section in C.SUB_SECTIONS["hood"]:
        c = Counter(r["sub_" + section] for r in hoods if r["sub_" + section])
        if c:
            text, n = c.most_common(1)[0]
            print(f"  sub_{section:20} {sum(c.values()):3} neighborhoods, {len(c):2} wordings, commonest {n} "
                  f"({n / len(hoods):.1%}): {text[:50]}")
    for e in errors:
        print("  ", e)
    if stale:
        print(f"skipped {len(stale)} drafts whose neighborhood is no longer in {LG}: {stale}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
