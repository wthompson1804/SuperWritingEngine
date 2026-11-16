"""Add the pieces built alongside the pipeline to site/data.json. Run after scripts/build_page_data.py, before
scripts/build_site.py. Idempotent: running it twice changes nothing.

  years          prose {scene, promise, catch}                    data/reference/scene_text_years.csv
  neighborhoods  prose {scene, good_for_her, watch_for}           data/reference/scene_text_neighborhoods.csv
                 local.voices / local.survey (round 2)            data/voices/neighborhood_*_round2.csv
                 local.parking_rules / dog_rules (round 2)        data/reference/local_rules_round2.csv
  units          contact {phone, hours, site, kind, note}         data/reference/building_contacts*.csv

Prose is only attached when scripts/check_scene_text.py passes for that row's numbers (the checker is run by run_all;
here a row is skipped if its text is empty). A missing input file is skipped and reported.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA  # noqa: E402

SITE = Path(__file__).resolve().parent.parent / "site"


def rd(p: Path):
    return pd.read_csv(p, dtype=str, keep_default_na=False) if p.exists() else None


def area_key(t):
    t = re.sub(r",\s*[A-Z]{2}$", "", str(t).strip())
    return re.sub(r"\b(township|city of|city|town|village|borough)\b|\(.*?\)|[^a-z]", "", t.lower())


def main():
    f = SITE / "data.json"
    d = json.load(open(f, encoding="utf-8"))
    rep = {}

    Y = rd(DATA / "reference" / "scene_text_years.csv")
    if Y is not None:
        by = {r.year_label: r for r in Y.itertuples()}
        n = 0
        for y in d["years"]:
            r = by.get(y.get("label"))
            if r is not None and r.scene.strip():
                y["prose"] = {"scene": r.scene, "promise": r.promise, "catch": r.catch}
                n += 1
        rep["year prose"] = f"{n} of {len(d['years'])}"

    H = rd(DATA / "reference" / "scene_text_neighborhoods.csv")
    hoods = {h["id"]: h for h in d["neighborhoods"]}
    if H is not None:
        n = 0
        for r in H.itertuples():
            h = hoods.get(r.hood_id)
            if h is not None and r.scene.strip():
                h["prose"] = {"scene": r.scene, "good_for_her": r.good_for_her, "watch_for": r.watch_for}
                n += 1
        rep["neighborhood prose"] = f"{n} of {len(hoods)}"

    Q = rd(DATA / "voices" / "neighborhood_quotes_round2.csv")
    if Q is not None:
        if "verified" in Q:
            Q = Q[Q.verified.str.lower().isin(["true", "yes", "1"])]
        qx = rd(DATA / "voices" / "quote_exclusions.csv")
        QX = [(r.hood_id, r.excerpt_starts_with) for r in qx.itertuples()] if qx is not None else []
        n = 0
        for r in Q.itertuples():
            h = hoods.get(r.hood_id)
            if h is None or any(r.hood_id == a and r.excerpt.startswith(b) for a, b in QX):
                continue
            vs = h.setdefault("local", {}).setdefault("voices", [])
            if any(v.get("excerpt") == r.excerpt for v in vs):
                continue
            sa = r.source_area
            plain = re.sub(r"\s*\((?:enclosing area|whole)\)", "", sa)
            about = re.sub(r",\s*[A-Z]{2}$", "", plain) if sa and len(plain) <= 40 and area_key(plain) != area_key(r.neighborhood) else None
            vs.append({"excerpt": r.excerpt, "theme": r.theme, "sentiment": r.sentiment, "context": r.speaker_context, "source": r.source_site,
                       "date": r.post_date, "url": r.permalink, "source_area": sa or None, "about": about})
            n += 1
        rep["round 2 quotes added"] = n
    S = rd(DATA / "voices" / "neighborhood_survey_round2.csv")
    if S is not None:
        n = 0
        for r in S.itertuples():
            h = hoods.get(r.hood_id)
            if h is None:
                continue
            sv = h.setdefault("local", {}).setdefault("survey", [])
            row = {"measure": r.measure, "value": r.value, "source": r.source_site, "as_of": r.as_of, "url": r.source_url}
            if row not in sv:
                sv.append(row); n += 1
        rep["round 2 survey rows added"] = n

    L = rd(DATA / "reference" / "local_rules_round2.csv")
    if L is not None and {"value_type", "applies_to_hood_ids", "topic"} <= set(L.columns):
        n = 0
        for r in L[L.value_type == "found"].itertuples():
            key = {"street_parking": "parking_rules", "dogs": "dog_rules"}.get(r.topic)
            if not key:
                continue
            row = {"rule": r.rule, "summary": r.summary, "quote": r.quote, "url": r.source_url, "municipality": r.municipality}
            for hid in [x.strip() for x in r.applies_to_hood_ids.split(";") if x.strip()]:
                h = hoods.get(hid)
                if h is None:
                    continue
                lst = h.setdefault("local", {}).get(key) or []
                if row not in lst:
                    lst.append(row); n += 1
                h["local"][key] = lst
        rep["round 2 local rules added"] = n

    # New York City's rules apply to every NYC neighborhood, including ones added to the page after round 1
    NYC = re.compile(r"\b(kings|queens|new york|bronx|richmond)\b", re.I)
    nyc = [h for h in hoods.values() if h.get("state") == "NY" and NYC.search(str(h.get("area") or ""))]
    donor = next((h for h in nyc if (h.get("local") or {}).get("parking_rules")), None)
    if donor:
        n = 0
        for h in nyc:
            lo = h.setdefault("local", {})
            for key in ("parking_rules", "dog_rules"):
                if not lo.get(key) and donor["local"].get(key):
                    lo[key] = [r for r in donor["local"][key] if r.get("municipality") == "New York City"]; n += 1
        rep["NYC rules copied to later NYC neighborhoods"] = n

    C = rd(DATA / "reference" / "building_contacts.csv")
    if C is not None:
        own = rd(DATA / "reference" / "building_contacts_own_site.csv")
        ownb = {}
        if own is not None:
            for r in own.itertuples():
                if r.leasing_phone and getattr(r, "confidence", "") in ("high", "medium"):
                    ownb[r.building_id] = r
        cb = {r.building_id: r for r in C.itertuples()}
        n = 0
        for u in d["units"]:
            c = cb.get(u.get("building_id"))
            if c is None:
                continue
            o = ownb.get(u.get("building_id"))
            if o is not None:
                u["contact"] = {"phone": o.leasing_phone, "hours": o.office_hours or c.office_hours or None, "site": o.own_site_url or c.leasing_url or None,
                                "kind": "leasing office", "note": None, "source": o.phone_page_url}
            elif c.leasing_phone or c.leasing_url:
                u["contact"] = {"phone": c.leasing_phone or None, "hours": c.office_hours or None, "site": c.leasing_url or None, "kind": c.contact_kind or None,
                                "note": c.note or None, "source": c.leasing_phone_source_url or None}
            else:
                continue
            n += 1
        rep["units with a contact"] = f"{n} of {len(d['units'])}"

    # Neighborhood order inside an experience (owner, 2026-11-16: show the top three, the rest on "show more", in
    # descending order). Score = the mean rank score of the neighborhood's three best shown places; a neighborhood with
    # fewer than three loses 2 points per missing place, so one good apartment does not outrank real choice.
    units = {u["id"]: u for u in d["units"]}
    for y in d["years"]:
        y["display_label"] = re.sub(r" Year$", " Experience", y.get("label", ""))
        hs = [hoods[i] for i in y.get("hood_ids", []) if i in hoods]
        for h in hs:
            sc = sorted([(units[i].get("scores") or {}).get("rank") or 0 for i in h.get("unit_ids", []) if i in units], reverse=True)[:3]
            h["experience_score"] = round(sum(sc) / len(sc) - 2 * (3 - len(sc)), 1) if sc else None
            h["experience_score_basis"] = f"mean rank score of its top {len(sc)} shown place(s)" + (f", minus {2 * (3 - len(sc))} for having fewer than three" if 0 < len(sc) < 3 else "")
        ranked = sorted(hs, key=lambda h: (-(h["experience_score"] if h["experience_score"] is not None else -1e9), h["id"]))
        for i, h in enumerate(ranked, 1):
            h["rank_in_experience"] = i
        y["hood_ids"] = [h["id"] for h in ranked]
    rep["neighborhoods ranked within experiences"] = sum(1 for h in hoods.values() if h.get("rank_in_experience"))

    # short attributed outside descriptions of each place (scripts/neighborhood_descriptions.py). A bare location
    # sentence ("X is a borough in Y County") says nothing about the place, so it is kept only when it is all there is.
    ND = rd(DATA / "reference" / "neighborhood_descriptions.csv")
    if ND is not None:
        BLAND = re.compile(r"^[^.]{0,60}\bis an? [^.]{0,60}\b(borough|town|township|city|village|hamlet|census-designated place|neighborhood|community|section)\b[^.]{0,120}\b(County|borough of|New York City|New York|New Jersey|Connecticut)\b[^.]*\.?$")
        if "verified" in ND:
            ND = ND[ND.verified.str.lower().isin(["yes", "true", "1"])]
        n = 0
        for hid, g in ND.groupby("hood_id"):
            h = hoods.get(hid) or next((x for k, x in hoods.items() if k.startswith("nj:jersey-city") and hid == "nj:jersey-city"), None)
            targets = [x for k, x in hoods.items() if k == hid or (hid == "nj:jersey-city" and k.startswith("nj:jersey-city-"))]
            rows = [{"quote": r.quote, "source": r.source_name, "url": r.source_url, "about": r.about_area if r.scope != "exact" else None,
                     "licence": r.licence_note, "bland": bool(BLAND.match(r.quote)) and len(r.quote.split()) <= 22} for r in g.itertuples()]
            good = [r for r in rows if not r["bland"]] or rows[:1]
            for t in targets:
                t["described"] = [{k: v for k, v in r.items() if k != "bland"} | ({"about": r["about"] or "Jersey City"} if t["id"] != hid else {}) for r in good[:3]]
                n += 1
        rep["neighborhoods with outside descriptions"] = n

    # finer neighborhood coordinates for the map (the page builder rounds to two decimals, about 1 km)
    ru = DATA / "ranked_units.csv"
    if ru.exists():
        RU = pd.read_csv(ru, usecols=lambda c: c in ("hood_id", "lat", "lon"), low_memory=False)
        if {"hood_id", "lat", "lon"} <= set(RU.columns):
            g = RU.assign(lat=pd.to_numeric(RU.lat, errors="coerce"), lon=pd.to_numeric(RU.lon, errors="coerce")).groupby("hood_id")[["lat", "lon"]].mean()
            for hid, r in g.iterrows():
                if hid in hoods and pd.notna(r.lat) and pd.notna(r.lon):
                    hoods[hid]["lat"], hoods[hid]["lon"] = round(float(r.lat), 5), round(float(r.lon), 5)

    d.setdefault("meta", {})["extras"] = rep
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("site/data.json extras:", rep)


if __name__ == "__main__":
    main()
