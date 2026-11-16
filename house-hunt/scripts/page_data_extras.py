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


SUBS = ["cost", "to_parents", "parking", "dog", "building", "going_out", "green", "residents_say", "local_rules", "compared_to_queens"]


def _host_fields(obj, r):
    """Host voice and section subheads from a scene-text row (scripts/build_scene_text.py). Empty cells are skipped."""
    g = lambda c: str(getattr(r, c, "") or "").strip()
    host = {}
    if g("host_intro"):
        host["intro"] = g("host_intro")
    if g("host_walkthrough"):
        host["walkthrough"] = [x.strip() for x in g("host_walkthrough").split("\n\n") if x.strip()]
    if host:
        obj["host"] = {**(obj.get("host") or {}), **host}
    for col, key in (("about_points_json", "about_points"), ("day_moments_json", "day_moments")):
        if g(col) and g(col).lower() != "nan":
            try:
                obj[key] = json.loads(g(col))
            except ValueError:
                pass
    for c in ("tagline", "display_label"):
        if g(c):
            obj[c] = g(c)
    if g("subhead"):
        obj["subhead_original"] = obj.get("subhead_original") or obj.get("subhead")
        obj["subhead"] = g("subhead")
    hl = obj.get("headlines") or {}
    for k in SUBS:
        if g("sub_" + k) and g("sub_" + k).lower() != "nan":
            hl.setdefault(k, {})["subhead"] = g("sub_" + k)
    if hl:
        obj["headlines"] = hl


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
                _host_fields(y, r)
                n += 1
        rep["year prose"] = f"{n} of {len(d['years'])}"

    H = rd(DATA / "reference" / "scene_text_neighborhoods.csv")
    hoods = {h["id"]: h for h in d["neighborhoods"]}
    # a split city (Jersey City): content keyed on the city's old id attaches to each of its neighborhoods on the page,
    # labelled as about the city as a whole; content that names one neighborhood goes to that one only
    kids = {}
    for h in hoods.values():
        if h.get("parent_id"):
            kids.setdefault(h["parent_id"], []).append(h)

    def targets(hid, source_area=""):
        """[(neighborhood, about)] for content keyed on hid."""
        if hid in hoods:
            return [(hoods[hid], None)]
        ks = kids.get(hid, [])
        letters = lambda t: re.sub(r"[^a-z]", "", str(t).lower())
        named = [k for k in ks if letters(k.get("short_name")) and letters(k.get("short_name")) in letters(source_area)]
        return [(k, None) for k in named] if named else [(k, f"{k.get('parent_name')} as a whole") for k in ks]
    if H is not None:
        n = inherited = 0
        own = set(H.hood_id)
        for r in H.itertuples():
            for h, about in targets(r.hood_id):
                if r.scene.strip() and not (about and h["id"] in own):
                    h["prose"] = {"scene": r.scene, "good_for_her": r.good_for_her, "watch_for": r.watch_for}
                    if not about:
                        _host_fields(h, r)
                    if about:           # written for the whole city before the split: its figures are the city's, not this neighborhood's
                        h["prose"].update({"about": about, "inherited_from": r.hood_id})
                        inherited += 1
                    n += 1
        rep["neighborhood prose"] = f"{n} of {len(hoods)}" + (f" ({inherited} inherited from the city's text, labelled)" if inherited else "")

    Q = rd(DATA / "voices" / "neighborhood_quotes_round2.csv")
    if Q is not None:
        if "verified" in Q:
            Q = Q[Q.verified.str.lower().isin(["true", "yes", "1"])]
        qx = rd(DATA / "voices" / "quote_exclusions.csv")
        QX = [(r.hood_id, r.excerpt_starts_with) for r in qx.itertuples()] if qx is not None else []
        n = 0
        for r in Q.itertuples():
            if any(r.hood_id == a and r.excerpt.startswith(b) for a, b in QX):
                continue
            for h, whole in targets(r.hood_id, r.source_area):
                vs = h.setdefault("local", {}).setdefault("voices", [])
                if any(v.get("excerpt") == r.excerpt for v in vs):
                    continue
                sa = r.source_area
                plain = re.sub(r"\s*\((?:enclosing area|whole)\)", "", sa)
                about = re.sub(r",\s*[A-Z]{2}$", "", plain) if sa and len(plain) <= 40 and area_key(plain) != area_key(r.neighborhood) else None
                vs.append({"excerpt": r.excerpt, "theme": r.theme, "sentiment": r.sentiment, "context": r.speaker_context, "source": r.source_site,
                           "date": r.post_date, "url": r.permalink, "source_area": sa or None, "about": whole or about})
                n += 1
        rep["round 2 quotes added"] = n
    S = rd(DATA / "voices" / "neighborhood_survey_round2.csv")
    if S is not None:
        n = 0
        for r in S.itertuples():
            for h, whole in targets(r.hood_id, getattr(r, "source_area", "")):
                sv = h.setdefault("local", {}).setdefault("survey", [])
                row = {"measure": r.measure, "value": r.value, "source": r.source_site, "as_of": r.as_of, "url": r.source_url,
                       "source_area": getattr(r, "source_area", "") or None, "about": whole}
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
            for hid in [x.strip() for x in r.applies_to_hood_ids.split(";") if x.strip()]:
                for h, whole in targets(hid):
                    row = {"rule": r.rule, "summary": r.summary, "quote": r.quote, "url": r.source_url, "municipality": r.municipality, "about": whole}
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
            elif c.contact_kind in ("broker", "individual owner"):
                # a number on a single listing may be one agent's or owner's own line: never shown; go through the listing page
                u["contact"] = {"phone": None, "hours": None, "site": c.leasing_url or None, "kind": c.contact_kind,
                                "note": "Listed by a broker or the owner: get in touch through the listing page.", "source": None}
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

    # "About the building": two sentences and a few points per building (scripts/realtor_lines.py)
    BA = rd(DATA / "reference" / "building_about.csv")
    if BA is not None:
        ba = {r.building_id: r for r in BA.itertuples()}
        n = 0
        for u in d["units"]:
            r = ba.get(u.get("building_id"))
            if r is None or not str(r.about_building).strip():
                continue
            u["about_building"] = str(r.about_building).strip()
            try:
                u["about_points"] = json.loads(r.about_points_json) if str(getattr(r, "about_points_json", "")).strip() else None
            except ValueError:
                u["about_points"] = None
            n += 1
        rep["places with an About-the-building text"] = f"{n} of {len(d['units'])}"

    # ratings census (docs/RATINGS_CENSUS_BRIEF.md): aggregate rating and review count per platform, as information only.
    # Shown: 5-star-scale figures matched with high or medium confidence; ForRent and ApartmentFinder repeat the
    # Apartments.com reviews and are left out. "searched" says whether a web search was run for the building at all.
    RC = rd(DATA / "evidence" / "ratings_census.csv")
    if RC is not None:
        NAMES = {"google": "Google", "apartments_com": "Apartments.com", "rentcafe": "RentCafe", "openigloo": "Openigloo", "birdeye": "Birdeye",
                 "apartment_list": "Apartment List", "yelp": "Yelp", "zillow": "Zillow", "apartmentratings": "ApartmentRatings", "facebook": "Facebook", "rentable": "Rentable"}
        by = {}
        unsearched = set(RC[RC.note.str.contains("NO WEB SEARCH RUN|WEB SEARCH NOT RUN", case=False)].building_id)
        for r in RC[(RC.status == "found") & RC.match_confidence.isin(["high", "medium"])].itertuples():
            try:
                rating, scale = float(r.rating), float(r.rating_scale or 5)
            except ValueError:
                continue
            if scale != 5 or r.platform not in NAMES:
                continue
            cnt = int(float(r.review_count)) if str(r.review_count).replace(".", "", 1).isdigit() else None
            cur = by.setdefault(r.building_id, {})
            if r.platform not in cur or (cnt or 0) > (cur[r.platform]["count"] or 0):
                cur[r.platform] = {"platform": NAMES[r.platform], "rating": round(rating, 1), "count": cnt, "seen_via": r.basis.replace("_", " "),
                                   "url": r.source_url or None, "as_of": r.retrieved_at[:10]}
        n = 0
        for u in d["units"]:
            b = u.get("building_id")
            rows = sorted(by.get(b, {}).values(), key=lambda x: -(x["count"] or 0))
            u["ratings"] = {"platforms": rows[:4], "most_reviews": max([x["count"] or 0 for x in rows], default=0),
                            "searched": b not in unsearched, "found_any": bool(rows)}
            n += bool(rows)
        rep["places with a rating on some platform"] = f"{n} of {len(d['units'])}"

    # the host's line and honest catch for each place, and its section subheads (scripts/realtor_lines.py)
    RL = rd(DATA / "reference" / "realtor_lines.csv")
    if RL is not None:
        rl = {r.listing_id: r for r in RL.itertuples()}
        n = 0
        for u in d["units"]:
            r = rl.get(u.get("id"))
            if r is None:
                continue
            g = lambda c: str(getattr(r, c, "") or "").strip()
            if g("host_line"):
                u["host"] = {"line": g("host_line"), "catch": g("host_catch") or None}
                n += 1
            hl = u.get("headlines") or {}
            for k in SUBS:
                if g("sub_" + k) and g("sub_" + k).lower() != "nan":
                    hl.setdefault(k, {})["subhead"] = g("sub_" + k)
            if hl:
                u["headlines"] = hl
        rep["places with a host line"] = f"{n} of {len(d['units'])}"

    # short attributed outside descriptions of each place (scripts/neighborhood_descriptions.py). A bare location
    # sentence ("X is a borough in Y County") says nothing about the place, so it is kept only when it is all there is.
    BLAND = re.compile(r"^[^.]{0,60}\bis an? [^.]{0,60}\b(borough|town|township|city|village|hamlet|census-designated place|neighborhood|community|section)\b[^.]{0,120}\b(County|borough of|New York City|New York|New Jersey|Connecticut)\b[^.]*\.?$")
    # round 1's topic filter missed some word forms ("immigrants", "segregation"); screen every row again here
    COMPOSITION = re.compile(r"immigra|segregat|demograph|ethnic|racial|\brace\b(?! ?(?:track|course))|religio|\b(?:white|black|hispanic|latino|asian|jewish|catholic|muslim)\b (?:resident|population|communit|famil|neighbo)", re.I)
    pool = {}
    for fn, rnd in (("neighborhood_descriptions_round2.csv", 2), ("neighborhood_descriptions.csv", 1)):
        ND = rd(DATA / "reference" / fn)
        if ND is None:
            continue
        if "verified" in ND:
            ND = ND[ND.verified.str.lower().isin(["yes", "true", "1"])]
        for r in ND.itertuples():
            if COMPOSITION.search(r.quote):
                continue
            bland = bool(BLAND.match(r.quote)) and len(r.quote.split()) <= 22
            ch = int(getattr(r, "character", "") or 0) if rnd == 2 and str(getattr(r, "character", "")).isdigit() else (1 if bland else 2)
            pool.setdefault(r.hood_id, []).append({"quote": r.quote, "source": r.source_name, "url": r.source_url,
                                                   "about": r.about_area if r.scope != "exact" and r.about_area != r.hood_name else None,
                                                   "topic": getattr(r, "topic", "") or None, "licence": r.licence_note, "_c": ch, "_r": rnd})
    n = 0
    for hid, rows in pool.items():
        rows = sorted(rows, key=lambda x: (-x["_c"], -x["_r"]))
        seen, picked, topics = set(), [], set()
        for x in rows:                                   # best first, one per topic where there is a choice, no repeats
            if x["quote"] in seen or (x["topic"] and x["topic"] in topics and len(rows) > 3):
                continue
            seen.add(x["quote"]); topics.add(x["topic"]); picked.append(x)
            if len(picked) == 3:
                break
        picked = [x for x in picked if x["_c"] >= 2] or picked[:1]
        for t, about in targets(hid):
            if about and t.get("described"):
                continue                                 # the neighborhood's own quotes win over the whole city's
            t["described"] = [{k: v for k, v in x.items() if not k.startswith("_")} | ({"about": x["about"] or about} if about else {}) for x in picked]
            n += 1
    if pool:
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
