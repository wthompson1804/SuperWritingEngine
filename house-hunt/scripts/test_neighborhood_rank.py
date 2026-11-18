"""Checks on scripts/neighborhood_rank.py and its two outputs. Plain asserts: python3 scripts/test_neighborhood_rank.py"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import neighborhood_rank as nr  # noqa: E402

DOC = json.loads(nr.OUT_JSON.read_text(encoding="utf-8"))
ROWS = list(csv.DictReader(open(nr.OUT_CSV, encoding="utf-8")))
HOODS, META = DOC["neighborhoods"], DOC["meta"]
PROPER = {"name", "address", "city", "place", "source_name", "area", "id", "key", "file", "site", "source_url", "listing_url", "photo_url", "url"}


def flat(h):
    m = {}
    for d in h["measures"].values():
        m.update(d.get("figures", {}))
    return m


def strings(o, key=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v, k)
    elif isinstance(o, list):
        for v in o:
            yield from strings(v, key)
    elif isinstance(o, str):
        yield key, o


def test_figures_in_sentences():
    """Every figure in a why / know-this sentence is the measure's own figure, and no other number appears."""
    allowed_extra = {"2,000", "10", "0"}            # the rent limit, "10-minute walk", "$0"
    n = 0
    for h in HOODS:
        m = flat(h)
        assert len(h["why"]) == 3, (h["id"], len(h["why"]))
        assert len(h["know_this"]) <= 2, h["id"]
        assert not {w["measure"] for w in h["why"]} & {w["measure"] for w in h["know_this"]}, h["id"]
        for w in h["why"] + h["know_this"]:
            assert w["measure"] != "records", h["id"]
            full = nr.display_figures(w["measure"], m)
            expect = {k: full[k] for k in w["figures"]}
            assert w["figures"] == expect, (h["id"], w["measure"], w["figures"], full)
            if w in h["why"]:
                assert expect == full, (h["id"], w["measure"])
            want = {nr.figure_text(k, v).lstrip("$") for k, v in expect.items()}
            found = set(re.findall(r"\d[\d,]*(?:\.\d+)?", w["text"]))
            assert want <= found | {"0"}, (h["id"], w["text"], want)
            assert found <= want | allowed_extra, (h["id"], w["text"], found - want)
            n += 1
    return n


def test_measures_from_listings():
    """Cost and supply figures recomputed straight from the listings table for every ranked neighborhood."""
    U, _, _ = nr.load_listings()
    H = nr.read(nr.DATA / "neighborhoods.csv")
    a = nr.assign_hoods(U, H)
    U["hood_id"] = U.addr_key.map(lambda k: a.get(k, (None, ""))[0])
    nr.apply_templates(U)
    assert not ((U.template != "") & (U.listed_rent == U.advertised_rent)).any(), "a template price used as rent"
    for h in HOODS:
        g = U[(U.hood_id == h["id"]) & (U.listed_rent <= 2200)]
        s = g[g.listed_rent <= 2000]
        m = flat(h)
        assert m["median_rent"] == float(g.listed_rent.median()), h["id"]
        assert m["apartments_2000"] == s.dedupe_key.nunique() == h["counts"]["apartments"], h["id"]
        assert m["dogs_yes"] == int((g.dogs_adj == "yes").sum()) and m["listings"] == len(g), h["id"]
        assert h["typical_rent"] == int(round(s.listed_rent.median())) <= 2000, h["id"]
        row = H[H.hood_id == h["id"]].iloc[0]
        assert h["drive_min"] == int(round(round(float(row.drive_min), 1))) and abs(h["toll_round_trip"] - row.toll_rt) < 0.006, h["id"]


def test_reproducible():
    doc, table = nr.build()
    assert doc["neighborhoods"] == HOODS, "neighborhoods differ on a second build"
    a, b = dict(doc["meta"]), dict(META)
    a.pop("built_at"), b.pop("built_at")
    assert a == b
    assert [(r["hood_id"], str(r["rank"]), str(r["score"])) for r in table] == [(r["hood_id"], r["rank"], r["score"]) for r in ROWS]


def test_eligibility():
    S = nr.read(nr.DATA / "neighborhood_safety.csv").set_index("hood_id")
    H = nr.read(nr.DATA / "neighborhoods.csv").set_index("hood_id")
    jam = S.loc["ny:jamaica"]
    assert [h["rank"] for h in HOODS] == list(range(1, len(HOODS) + 1))
    assert len(HOODS) == META["counts"]["eligible"] == sum(1 for r in ROWS if r["status"] == "ranked")
    for h in HOODS:
        i = h["id"]
        assert H.drive_min[i] < 120, i
        assert not (S.violent[i] > jam.violent) and not (S.property[i] > jam.property), i
        assert h["counts"]["buildings"] >= 5, i
        assert len({b["id"] for b in h["all_buildings"]}) == len(h["all_buildings"]), i
        assert sum(1 for b in h["all_buildings"] if not b["rent_is_template"]) == h["counts"]["buildings"], i
        assert all(b["rent_range"][0] <= 2000 for b in h["all_buildings"]), i
        assert h["illustration_key"], i
        assert len(h["tags"]) <= 2 and set(h["tags"]) <= set(h["tags_true"]) <= set(META["tag_floors"]), i
    c = META["counts"]
    assert c["neighborhoods_considered"] == len(ROWS)
    assert c["neighborhoods_considered"] == (c["no_neighborhood_record"] + c["cut_drive"] + c["cut_by_the_jamaica_rule"]
                                             + c["too_little_supply"] + c["eligible"])
    for r in ROWS:
        if r["status"] == "jamaica_rule":
            assert S.violent[r["hood_id"]] > jam.violent or S.property[r["hood_id"]] > jam.property
        if r["status"] == "too_little_supply":
            assert int(r["buildings_2000"]) < 5


def test_know_this_is_a_drawback():
    med = META["list_medians"]
    for h in HOODS:
        m = flat(h)
        for w in h["know_this"]:
            assert w["standing"] < 0.4, (h["id"], w["measure"])
            k = w["measure"]
            if k in nr.DRAWBACK:
                key, hb = nr.DRAWBACK[k]
                assert (m[key] < med[key]) if hb else (m[key] > med[key]), (h["id"], k, m[key], med[key])
            elif k == "cost":
                assert m["median_rent"] > med["median_rent"] or m["apartments_2000"] < med["apartments_2000"], h["id"]
            else:
                assert k == "parking" and (m["overnight_rule"] or m["offstreet_share"] < 0.5), h["id"]


def test_tags_true():
    for h in HOODS:
        m = flat(h)
        for t in h["tags"]:
            ok = {"near family": m["drive_min"] <= 30, "lively": (m["places_10min"] or 0) >= 20, "quiet": m["places_10min"] is not None and m["places_10min"] <= 5,
                  "more room": (m["median_sqft"] or 0) >= 650, "good value": m["median_rent"] <= 1700, "green": m["park_walk_min"] <= 5,
                  "easy parking": (m["offstreet_share"] or 0) > 0.5, "dog friendly": m["dogs_yes_share"] >= 0.5, "lots of choice": m["apartments_2000"] >= 40}[t]
            assert ok, (h["id"], t)


def test_buildings():
    for h in HOODS:
        top, bad = h["top_buildings"], h["avoid_buildings"]
        assert len(top) <= 3 and len(bad) <= 2, h["id"]
        assert not {b["id"] for b in top} & {b["id"] for b in bad}, h["id"]
        roles = {b["id"]: b["role"] for b in h["all_buildings"]}
        for b in top + bad:
            assert b["name"] and b["address"] and re.match(r"\s*\d", b["address"]), (h["id"], b["id"])
            assert b["rent_range"][0] <= b["rent_range"][1] <= 2000, (h["id"], b["id"])
            assert b["apartments"] >= 1 and b["listing_url"], (h["id"], b["id"])
            assert b["known"] or b["to_ask"], b["id"]
            if b["rating"]:
                assert 0 < b["rating"]["value"] <= 5 and b["rating"]["count"] >= 1 and b["rating"]["site"], b["id"]
            if b["verified"]["on_page"]:
                assert b["verified"]["apartment_ids"], b["id"]
        assert (h["supply_note"] is None) == (len(top) == 3), h["id"]
        assert h["confidence"] in ("high", "medium", "low"), h["id"]
        tpl = {b["id"] for b in h["all_buildings"] if b["rent_is_template"]}
        for b in h["all_buildings"]:
            if b["rent_is_template"]:
                assert b["role"] == "listed" and b["to_ask"][0] == nr.TEMPLATE_ASK, b["id"]
        for b in top:
            assert b["id"] not in tpl and not any("exist" in q for q in b["to_ask"]), b["id"]
            assert b["rating"] is None or b["rating"]["count"] >= 5, b["id"]
        for b in top:
            assert roles[b["id"]] == "top" and "No dogs" not in b["known"] and "Ground floor only" not in b["known"], b["id"]
        assert [b["evidence_score"] for b in top] == sorted((b["evidence_score"] for b in top), reverse=True), h["id"]
        for b in bad:
            assert roles[b["id"]] == "avoid", b["id"]
            assert b["reason"].strip() and b["reason"].endswith("."), b["id"]
            s = b["source"]
            assert s["name"] and s["file"] and (nr.ROOT / s["file"]).exists() and (s.get("url") or s.get("key")), b["id"]
            assert b["avoid_kind"] in META["avoid_order"], b["id"]


def test_verified_ids_exist():
    conc = json.loads((nr.SITE / "concierge_data.json").read_text())
    ok = {a["id"] for b in conc["buildings"] for a in b["apartments"]}
    page = {u["id"] for u in json.loads((nr.SITE / "data.json").read_text())["units"]}
    for h in HOODS:
        for b in h["top_buildings"] + h["avoid_buildings"]:
            assert set(b["verified"]["apartment_ids"]) <= ok and set(b["verified"]["first_page_ids"]) <= page, b["id"]


def test_no_private_phone():
    allowed, private = set(), set()
    for f in ("building_contacts.csv", "building_contacts_trawl2.csv"):
        for r in nr.read(nr.DATA / "reference" / f).itertuples():
            if isinstance(r.leasing_phone, str):
                (allowed if r.contact_kind in nr.PUBLIC_CONTACT_KINDS else private).add(r.leasing_phone)
    for r in nr.read(nr.DATA / "reference" / "building_contacts_own_site.csv").itertuples():
        if isinstance(r.leasing_phone, str):
            allowed.add(r.leasing_phone)
    digits = lambda s: re.sub(r"\D", "", s)  # noqa: E731
    shown = set()
    for h in HOODS:
        for b in h["top_buildings"] + h["avoid_buildings"]:
            c = b["contact"]
            if c:
                assert c["kind"] in nr.PUBLIC_CONTACT_KINDS, b["id"]
                if c["phone"]:
                    shown.add(c["phone"])
    assert shown <= allowed, shown - allowed
    assert not {digits(p) for p in shown} & ({digits(p) for p in private} - {digits(p) for p in allowed})
    for key, s in strings(HOODS):
        if key not in ("phone", "source_url", "listing_url", "photo_url", "url", "site", "key", "id"):
            assert not nr.PHONE_RE.search(s), (key, s)
    return len(shown)


def test_plain_words():
    n = 0
    for key, s in strings(HOODS):
        if key in PROPER or s.startswith("http"):
            continue
        assert nr.text_ok(s), (key, s)
        n += 1
    for key, s in strings(META):
        if key in ("scoring", "note", "finding") or key in META["tag_floors"]:
            assert nr.text_ok(s), (key, s)
    for h in HOODS:
        for b in h["top_buildings"] + h["avoid_buildings"]:
            assert not re.search(r"\bunits?\b", b["name"] + " " + b["address"], re.I), b["id"]
        assert "records" not in {w["measure"] for w in h["why"] + h["know_this"]}
        assert "figures" not in h["measures"]["records"], h["id"]
    blob = " ".join(s for _, s in strings(HOODS) if "Mom" in s or "parents" in s.lower())
    assert "parents" not in blob.lower() and "Mom and Dad" in blob
    return n


def test_sensitivity():
    sc = META["sensitivity"]["scenarios"]
    assert set(sc) == {"base", "equal"} | {f"{m}_{d}" for m in META["weights"] for d in ("up", "down")}
    for m, w in META["weights"].items():
        assert sc[f"{m}_up"][m] == 1.5 * w and sc[f"{m}_down"][m] == 0.5 * w
    assert sum(META["weights"].values()) == 100
    S = {h["id"]: {m: d["score"] for m, d in h["measures"].items()} for h in HOODS}
    for name, w in sc.items():
        ranks, scores = nr.rank_ids(S, w)
        assert sorted(ranks.values()) == list(range(1, len(HOODS) + 1))
        for h in HOODS:
            assert h["sensitivity"][name] == ranks[h["id"]], (name, h["id"])
            if name == "base":
                assert h["rank"] == ranks[h["id"]] and h["score"] == round(scores[h["id"]], 1)
    for h in HOODS:
        v = h["sensitivity"].values()
        assert h["rank_range"] == [min(v), max(v)] and h["rank_range"][0] <= h["rank"] <= h["rank_range"][1], h["id"]
        for m, d in h["measures"].items():
            assert (d["score"] is None) == (not d["known"]) and (d["score"] is None or 0 <= d["score"] <= 1), (h["id"], m)
    row = {r["hood_id"]: r for r in ROWS if r["status"] == "ranked"}
    for h in HOODS:
        r = row[h["id"]]
        assert int(r["rank"]) == h["rank"] and int(r["rank_low"]) == h["rank_range"][0] and int(r["rank_high"]) == h["rank_range"][1]
        assert all(int(r["rank_" + n]) == h["sensitivity"][n] for n in sc)


def test_coverage_and_zumper():
    for m, c in META["coverage"].items():
        assert c["neighborhoods_with_measure"] == sum(1 for h in HOODS if h["measures"][m]["known"]) <= c["of"] == len(HOODS)
    z = META["zumper_no_pets_block"]
    assert z["rows_with_block"] == z["kept_as_no_dogs"] + z["set_to_unknown_for_conflict"]
    a = META["neighborhood_assignment"]
    assert sum(a["by_method"].values()) == a["listings_used"] == META["counts"]["listings_used"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            out = fn()
            print(f"ok  {name}" + (f" ({out})" if out is not None else ""))
    print("all checks passed")

