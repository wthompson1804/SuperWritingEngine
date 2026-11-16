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
Lines
  === year: <label>      then  scene: / promise: / catch:
  === hood: <hood_id>    then  scene: / good: / watch: , and optionally
      rules: Municipality|rule ; Municipality|rule      numbers typed in the prose must come from these summaries
      voices: theme, theme                              themes whose balance of comments the prose paraphrases

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
    "b_toll": ("toll_rt_ezpass", "median", "int"), "b_tollmax": ("toll_rt_ezpass", "max", "int"),
    "b_tollok": ("toll_complete", "all_true", "str"),
    "b_station": ("train_station", "mode", "str"), "b_dogpark": ("dog_park_name", "mode", "str"),
    "b_park": ("park_name", "mode", "str"), "b_super": ("supermarket", "mode", "str"),
    "b_lasttrain": ("last_sat_departure", "mode", "time12"),
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
            return MB, f, {"hood_id": ctx["id"]}, agg, how
    else:
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


def render(raw, ctx, evidence):
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
        summaries = C.lookup(RULES, "summary", {"municipality": muni, "rule": rule, "value_type": "found"}, "any_row")
        if not summaries:
            raise ValueError(f"{ctx['id']}: no found rule {muni}|{rule}")
        for s in summaries:
            cited.append({"claim": f"local rule cited: {muni}, {rule}", "field": "summary", "value": s,
                          "source_file": RULES, "row": {"municipality": muni, "rule": rule, "value_type": "found"},
                          "agg": "any_row", "transform": "in_text", "shown": []})
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
        k = (ev["row"]["municipality"], ev["row"]["rule"])
        if ev in used or k not in seen and not any(u["row"] == ev["row"] for u in used):
            evidence.append(ev)
        seen.add(k)


def attach_voices(ctx, spec, texts, evidence):
    claim = " ".join(s for t in texts.values() for s in C.sentences(t) if re.search(r"review sites", s))
    if not claim:
        raise ValueError(f"{ctx['id']}: voices cited but no sentence says 'review sites'")
    for theme in [t.strip() for t in spec.split(",") if t.strip()]:
        row = {"hood_id": ctx["id"], "theme": theme}
        counts = C.lookup(QUOTES, "sentiment", row, "sentiment_counts")
        if counts == "positive=0;mixed=0;negative=0":
            raise ValueError(f"{ctx['id']}: no quotes on {theme}")
        evidence.append({"claim": claim, "field": "sentiment", "value": counts, "source_file": QUOTES, "row": row,
                         "agg": "sentiment_counts"})


def parse(path):
    blocks, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        m = re.match(r"=== (year|hood): (.+)", line)
        if m:
            cur = {"kind": m.group(1), "id": m.group(2).strip(), "f": {}}
            blocks.append(cur)
            continue
        k, _, v = line.partition(":")
        if cur is None or not _:
            raise ValueError(f"cannot read line: {line[:80]}")
        cur["f"][k.strip()] = v.strip()
    return blocks


def main():
    lg = C.table(LG).set_index("hood_id")
    years, hoods, errors = [], [], []
    for b in parse(SOURCE):
        ctx, f, evidence = {"kind": b["kind"], "id": b["id"]}, b["f"], []
        cols = {"scene": "scene", "promise": "promise", "catch": "catch"} if b["kind"] == "year" else \
               {"scene": "scene", "good": "good_for_her", "watch": "watch_for"}
        try:
            texts = {out: render(f[src], ctx, evidence) for src, out in cols.items()}
            if b["kind"] == "hood":
                if f.get("rules"):
                    attach_rules(ctx, f["rules"], texts, evidence)
                if f.get("voices"):
                    attach_voices(ctx, f["voices"], texts, evidence)
                elif any("review sites" in t for t in texts.values()):
                    raise ValueError(f"{b['id']}: mentions review sites without a voices: line")
            problems, _ = C.check_row(b["kind"], b["id"], texts, evidence)
            errors += [f"{b['id']}: {p}" for p in problems]
        except (KeyError, ValueError, LookupError) as e:
            errors.append(str(e))
            continue
        ej = json.dumps(evidence, ensure_ascii=False)
        if b["kind"] == "year":
            years.append({"year_label": b["id"], **texts, "evidence_json": ej})
        else:
            hoods.append({"hood_id": b["id"], "hood_name": lg.loc[b["id"], "hood"],
                          "year_label": lg.loc[b["id"], "group_label"], **texts, "evidence_json": ej})
    for name, rows in ((C.YEARS, years), (C.HOODS, hoods)):
        if rows:
            with open(name, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    print(f"{len(years)} years, {len(hoods)} neighborhoods written; {len(errors)} problems")
    for e in errors:
        print("  ", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
