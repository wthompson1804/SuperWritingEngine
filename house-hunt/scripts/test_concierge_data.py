#!/usr/bin/env python3
"""Tests for scripts/concierge_data.py and its output, site/concierge_data.json (docs/CONCIERGE_DESIGN.md).

Plain asserts; run from the house-hunt folder:  python3 scripts/test_concierge_data.py
Reads site/data.json, site/_concierge_base.json and site/concierge_data.json; writes nothing.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import concierge_data as K  # noqa: E402

D = json.loads(K.DATA.read_text(encoding="utf-8"))
BASE = json.loads(K.BASE.read_text(encoding="utf-8"))
OUT = json.loads(K.OUT.read_text(encoding="utf-8"))
KEPT = [u for u in D["units"] if K.rent_now(u) <= K.RENT_LIMIT]
EXPS, HOODS, BLDS = OUT["experiences"], OUT["neighborhoods"], OUT["buildings"]
APTS = [(b, a) for b in BLDS for a in b["apartments"]]
H = {h["id"]: h for h in HOODS}
B = {b["id"]: b for b in BLDS}
U = {u["id"]: u for u in KEPT}
TESTS = []


def test(f):
    TESTS.append(f)
    return f


def close(a, b, tol=0.051):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    return abs(float(a) - float(b)) <= tol


def strings(o, path=""):
    """Every string a reader could be shown: not ids, links, internal audit fields or the source site's name."""
    if isinstance(o, dict):
        for k, x in o.items():
            if k in ("id", "illustration_id", "name", "address", "city", "source", "source_site", "kind", "icon", "level", "why_source", "give_up_source",
                     "parked", "either_or_audit", "score_keys", "built_at", "source_built_at", "last_read", "status", "date", "checked_day",
                     "checked_counts", "why_topic") or k.endswith("_url") \
                    or k.endswith("_id") or k.endswith("_ids") or k in ("site", "parked_under", "also_nearby"):
                continue
            yield from strings(x, f"{path}.{k}")
    elif isinstance(o, list):
        for i, x in enumerate(o):
            yield from strings(x, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


@test
def rent_limit_holds():
    assert OUT["meta"]["rent_limit"] == K.RENT_LIMIT == 2000
    assert APTS and all(a["rent"] is not None and a["rent"] <= K.RENT_LIMIT for _, a in APTS)
    assert {a["id"] for _, a in APTS} == set(U), "the page holds exactly the apartments at or under the limit"
    for _, a in APTS:
        u = U[a["id"]]
        assert a["rent"] == K.rent_now(u) and a["total"] == u["all_in"], a["id"]
    assert all(K.rent_now(u) <= K.RENT_LIMIT for u in BASE["units"]) and len(BASE["units"]) == len(KEPT)


@test
def counts_are_consistent():
    c = OUT["meta"]["counts"]
    assert c == {"apartments": len(APTS), "buildings": len(BLDS), "neighborhoods": len(HOODS), "experiences": len(EXPS)}
    assert c["apartments"] == len(KEPT) and c["buildings"] == len({u["building_id"] for u in KEPT})
    assert c["neighborhoods"] == len({u["hood_id"] for u in KEPT}) and c["experiences"] == len({u["year"] for u in KEPT})
    assert len(set(B)) == len(BLDS) and len(set(H)) == len(HOODS)
    assert all(b["apartments"] for b in BLDS) and all(h["building_ids"] for h in HOODS) and all(e["neighborhood_ids"] for e in EXPS)
    for h in HOODS:
        assert all(B[i]["neighborhood_id"] == h["id"] for i in h["building_ids"])
        assert h["apartments"] == sum(len(B[i]["apartments"]) for i in h["building_ids"]) and h["buildings"] == len(h["building_ids"])
    assert sorted(i for h in HOODS for i in h["building_ids"]) == sorted(B)
    assert sorted(i for e in EXPS for i in e["neighborhood_ids"]) == sorted(H)
    for e in EXPS:
        assert all(H[i]["experience_id"] == e["id"] for i in e["neighborhood_ids"])
        mine = [b for b in BLDS if b["experience_id"] == e["id"]]
        assert e["figures"]["buildings"] == len(mine) and e["figures"]["apartments"] == sum(len(b["apartments"]) for b in mine)
        assert e["figures"]["neighborhoods"] == len(e["neighborhood_ids"])
    for b in BLDS:
        assert H[b["neighborhood_id"]]["experience_id"] == b["experience_id"]
    assert sum(e["figures"]["apartments"] for e in EXPS) == c["apartments"]


@test
def experience_figures_equal_a_recomputation():
    for e in EXPS:
        us = [u for u in KEPT if u["year"] == e["id"]]
        f = e["figures"]
        rents, totals = [K.rent_now(u) for u in us], [u["all_in"] for u in us]
        drives = [u["moments"]["sun"]["drive_min"] for u in us if u["moments"]["sun"].get("drive_min") is not None]
        tolls = [u["moments"]["sun"]["toll_round_trip"] for u in us if u["moments"]["sun"].get("toll_complete")
                 and u["moments"]["sun"].get("toll_round_trip") is not None]
        assert close(f["rent_median"], K.median(rents)) and close(f["rent_range"], [min(rents), max(rents)]), e["id"]
        assert close(f["total_median"], K.median(totals)) and close(f["total_range"], [min(totals), max(totals)]), e["id"]
        assert close(f["drive_min_median"], K.median(drives)) and close(f["drive_min_range"], [min(drives), max(drives)]), e["id"]
        assert close(f["toll_round_trip_range"], [min(tolls), max(tolls)] if tolls else None, 0.006), e["id"]
        # the same from the page's own apartments
        mine = [a for b in BLDS if b["experience_id"] == e["id"] for a in b["apartments"]]
        assert close(f["rent_median"], K.median(a["rent"] for a in mine)) and close(f["total_median"], K.median(a["total"] for a in mine))
        # and the base file, which the text was built from, carries the same figures
        y = next(y for y in BASE["years"] if y["id"] == e["id"])
        assert close(y["medians"]["all_in"], f["total_median"]) and close(y["medians"]["drive_min"], f["drive_min_median"])
        assert y["counts"]["shown"] == f["apartments"] and y["counts"]["buildings"] == f["buildings"]
        assert close(y["all_in_range"], f["total_range"]) and close(y["drive_min_range"], f["drive_min_range"])


@test
def neighborhood_and_building_figures_equal_a_recomputation():
    for h in HOODS:
        us = [u for u in KEPT if u["hood_id"] == h["id"]]
        assert close(h["drive_min"], K.median(u["moments"]["sun"].get("drive_min") for u in us)), h["id"]
        complete = all(u["moments"]["sun"].get("toll_complete") for u in us)
        want = K.median(u["moments"]["sun"].get("toll_round_trip") for u in us) if complete else None
        assert close(h["toll_round_trip"], want, 0.006), h["id"]
        assert close(h["rent_range"], [min(K.rent_now(u) for u in us), max(K.rent_now(u) for u in us)])
        assert close(h["total_range"], [min(u["all_in"] for u in us), max(u["all_in"] for u in us)])
        assert close(h["lat"], sum(u["lat"] for u in us) / len(us), 1e-4) and close(h["lon"], sum(u["lon"] for u in us) / len(us), 1e-4)
    for b in BLDS:
        us = [U[a["id"]] for a in b["apartments"]]
        f = b["facts"]
        assert all(u["building_id"] == b["id"] for u in us)
        assert f["rent_from"] == min(K.rent_now(u) for u in us) and f["rent_to"] == max(K.rent_now(u) for u in us)
        assert f["total_from"] == min(u["all_in"] for u in us) and f["total_to"] == max(u["all_in"] for u in us)
        best = max(us, key=lambda u: (u["scores"]["rank"], ), default=None)
        assert b["rank_score"] == best["scores"]["rank"]
        assert any(close(f["drive_min"], u["moments"]["sun"].get("drive_min")) for u in us), b["id"]
        P = K.RL.parking_facts(U[b["apartments"][0]["id"]])
        assert f["parking"]["kind"] == P["kind"] and close(f["parking"]["fee"], P["fee"]), b["id"]
        for k in K.SCORE_KEYS:
            assert b["scores"][k] is not None and 0.0 <= b["scores"][k] <= 1.0, (b["id"], k)
        for k, part in (("parents", "distance"), ("value", "cost"), ("parking", "car"), ("green", "dog")):
            assert close(b["scores"][k], sum(u["scores"]["parts"][part] for u in us) / len(us) / 100, 0.0006), (b["id"], k)


@test
def the_recomputation_matches_the_pipeline_over_all_apartments():
    diffs = K.self_check(D)
    assert not diffs, diffs[:5]


@test
def story_cards():
    kinds = ["promise", "weekday", "saturday", "sunday", "cost", "catch"]
    years = {y["id"]: y for y in BASE["years"]}
    for e in EXPS:
        y = years[e["id"]]
        assert [c["kind"] for c in e["story"]] == kinds, e["id"]
        source = " ".join([K.voice((y["prose"] or {}).get("promise")), K.voice((y["prose"] or {}).get("catch"))]
                          + [K.voice(m["text"]) for m in y["day_moments"]])
        for c in e["story"]:
            assert c["title"] and c["text"] and c["icon"], (e["id"], c["kind"])
            assert len(c["title"].split()) <= 5 and 1 <= len(K.sentences(c["text"])) <= 2, (e["id"], c["kind"], c["text"])
            if c["kind"] != "cost":                     # the regenerated, guarded text, sentence for sentence
                for s in K.sentences(c["text"]):
                    assert s.replace("St ", "St. ") in source, (e["id"], c["kind"], s)
        cost = next(c for c in e["story"] if c["kind"] == "cost")
        nums = [int(x.replace(",", "")) for x in re.findall(r"\$([\d,]+)", cost["text"])]
        assert nums == [int(K.usd10(e["figures"]["rent_median"])[1:].replace(",", "")),
                        int(K.usd10(e["figures"]["total_median"])[1:].replace(",", ""))], cost["text"]
        assert "Rent" in cost["text"] and "total with utilities and fees" in cost["text"]


@test
def parking_of_one_apartment_neighborhoods():
    n = {h["id"]: h["apartments"] for h in HOODS}
    hosts = {h["parked_under"] for h in HOODS if h["parked_under"]}
    for h in HOODS:
        if n[h["id"]] == 1:
            same = [o for o in HOODS if o["experience_id"] == h["experience_id"] and o["id"] != h["id"]]
            big = [o for o in same if n[o["id"]] >= 2]
            if big:
                want = min(big, key=lambda o: (K.haversine_km(h, o), o["id"]))["id"]
                assert h["parked_under"] == want, (h["id"], h["parked_under"], want)
            assert h["id"] not in hosts, f"{h['id']} is parked and is also a host"
            assert h["also_nearby"] == []
        else:
            assert h["parked_under"] is None, h["id"]
        if h["parked_under"]:
            p = H[h["parked_under"]]
            assert p["experience_id"] == h["experience_id"] and h["id"] in p["also_nearby"] and p["parked_under"] is None
    for h in HOODS:
        assert all(H[i]["parked_under"] == h["id"] for i in h["also_nearby"])
    assert not any(H[i]["parked_under"] for i in hosts), "no parked neighborhood is a host"


@test
def parked_neighborhoods_say_how_far_and_are_called_nearby_only_when_they_are():
    for h in HOODS:
        assert {"parked_distance_km", "parked_label"} <= set(h), h["id"]
        if not h["parked_under"]:
            assert h["parked_distance_km"] is None and h["parked_label"] is None, h["id"]
            continue
        km = K.haversine_km(h, H[h["parked_under"]])
        assert close(h["parked_distance_km"], km, 0.06), (h["id"], h["parked_distance_km"], km)
        assert h["parked_label"] == ("Also nearby" if h["parked_distance_km"] <= K.NEARBY_KM else "Also in this kind of life"), h["id"]
    # the three the owner named: 20 km and more from their host, never "nearby"
    for i, host in (("nj:bloomfield", "ny:yonkers"), ("ny:bath-beach", "nj:newark"),
                    ("ny:sheepshead-bay-manhattan-beach-gerritsen-beach", "ny:flushing-willets-point")):
        if i in H and H[i]["parked_under"]:
            assert H[i]["parked_under"] == host and H[i]["parked_distance_km"] >= 20 and H[i]["parked_label"] == "Also in this kind of life", i
    assert OUT["meta"]["nearby_km"] == K.NEARBY_KM
    for p in OUT["meta"]["parked"]:
        assert p["label"] == H[p["neighborhood"]]["parked_label"] and p["km"] == H[p["neighborhood"]]["parked_distance_km"]


@test
def checked_says_what_the_live_check_rows_say():
    rows, day = K.live_rows()
    assert day == OUT["meta"]["checked_day"] and re.fullmatch(r"\d{4}-\d\d-\d\d", day)
    n = Counter()
    for b, a in APTS:
        c, u = a["checked"], U[a["id"]]
        assert set(c) >= {"status", "date", "note"} and c["status"] in ("confirmed_today", "price_changed_today", "last_seen"), a["id"]
        assert c["note"] and (c["date"] is None or re.fullmatch(r"\d{4}-\d\d-\d\d", c["date"])), a["id"]
        n[c["status"]] += 1
        mine = rows.get((b["id"], K.parsers.unit_key(u["unit"])), [])
        last = K.parsers.latest_live_row(mine)                       # the latest row that learned something: never a not_read row
        assert last is None or last["status"] != "not_read"
        today = last is not None and last["checked_at"][:10] == day
        if c["status"] == "confirmed_today":
            assert today and last["status"] == "live" and c["date"] == day, a["id"]
            assert (u["live"] or {}).get("status") == "live" and u["live"]["checked_at"][:10] == day, "the page data says the same"
        elif c["status"] == "price_changed_today":
            assert today and last["status"] == "changed" and c["date"] == day, a["id"]
            assert a["rent"] == float(last["price_now"]) == K.rent_now(u), (a["id"], a["rent"], last["price_now"])
            assert c["rent_before"] in (None, u["rent"]["listed"]) and (c["rent_before"] is None) == (u["rent"]["listed"] == a["rent"])
        else:
            assert not (today and last["status"] in ("live", "changed")), a["id"]
            seen = [str(u.get("price_seen_at") or "")[:10]] + ([last["checked_at"][:10]] if last and last["status"] in ("live", "changed") else [])
            assert c["date"] == max(x for x in seen if x), (a["id"], c["date"], seen)
            assert c["date"] < day, "last seen before the day of the re-read"
            tried = [r for r in mine if r["status"] == "not_read"]
            assert ("could not be read again" in c["note"]) == bool(tried and max(r["checked_at"][:10] for r in tried) > c["date"]), a["id"]
    assert dict(n) == OUT["meta"]["checked_counts"] and sum(n.values()) == len(APTS)
    for b in BLDS:
        s, apts = b["checked_summary"], b["apartments"]
        k = Counter(a["checked"]["status"] for a in apts)
        assert (s["apartments"], s["confirmed_today"], s["price_changed_today"], s["last_seen"]) == (len(apts), k["confirmed_today"], k["price_changed_today"], k["last_seen"])
        assert s["date"] == day and s["text"]
        seen = k["confirmed_today"] + k["price_changed_today"]
        assert s["text"].startswith(f"Confirmed {seen} of {len(apts)} on ") if seen else s["text"].startswith(("Last seen listed on ", "Not seen listed again")), b["id"]
    # the rule on made-up rows: a not_read row after a live one changes nothing; alone, it leaves the harvest date
    u = {"rent": {"listed": 1650, "basis": 1650.0, "basis_kind": "listed"}, "price_seen_at": "2026-11-15T21:49:59+00:00"}
    live = {"status": "live", "checked_at": "2026-11-16T10:00:00+00:00", "notes": ""}
    nr = {"status": "not_read", "checked_at": "2026-11-17T14:00:00+00:00", "notes": "Not re-read: no page names this apartment."}
    c = K.checked(u, [live, nr], "2026-11-17")
    assert (c["status"], c["date"]) == ("last_seen", "2026-11-16") and "could not be read again on November 17" in c["note"]
    c = K.checked(u, [nr], "2026-11-17")
    assert (c["status"], c["date"]) == ("last_seen", "2026-11-15") and "could not be read again" in c["note"]
    c = K.checked(u, [], "2026-11-17")
    assert (c["status"], c["date"], c["note"]) == ("last_seen", "2026-11-15", "Last seen listed on November 15.")
    c = K.checked(u, [dict(live, checked_at="2026-11-17T13:00:00+00:00")], "2026-11-17")
    assert (c["status"], c["date"]) == ("confirmed_today", "2026-11-17")
    u2 = {"rent": {"listed": 1945, "basis": 1895.0, "basis_kind": "listed"}, "price_seen_at": "2026-11-15T21:49:59+00:00"}
    c = K.checked(u2, [{"status": "changed", "checked_at": "2026-11-17T13:00:00+00:00", "price_now": "1895", "notes": ""}], "2026-11-17")
    assert (c["status"], c["rent_before"]) == ("price_changed_today", 1945) and "$1,895, down from $1,945" in c["note"]


@test
def why_speaks_of_her_priorities_before_any_amenity():
    """Parking, the dog, greenery, going out, Mom and Dad, room to work, value come first. A sentence about a pool, a
    gym or another amenity is the `why` only where the building has nothing true and positive on any of those."""
    bb = {b["id"]: b for b in BASE["buildings"]}
    hb = {h["id"]: h for h in BASE["neighborhoods"]}
    seen = Counter()
    for b in BLDS:
        us = sorted([u for u in BASE["units"] if u["building_id"] == b["id"]], key=lambda u: (-(K.num((u.get("scores") or {}).get("rank")) or 0), u["id"]))
        have = K.priority_sentences(bb[b["id"]], us, hb[b["neighborhood_id"]])
        topic = b["why_topic"]
        seen[topic] += 1
        assert topic in K.PRIORITY + ("amenity", "other"), b["id"]
        if have:
            assert topic in K.PRIORITY, f"{b['name']}: why is '{b['why']}' ({topic}) although it has {have[:2]}"
            assert not K.AMENITY_ONLY.search(b["why"]), f"{b['name']}: an amenity sentence stands for a priority: {b['why']}"
            assert b["why"] in {K.voice(s) for k, s, _ in have if k == topic}, (b["name"], b["why"])
        else:
            assert topic in ("amenity", "other"), b["id"]
        if K.AMENITY_ONLY.search(b["why"]) or re.search(r"\bpools?\b|\bgym\b", b["why"], re.I):
            assert not have, f"{b['name']}: '{b['why']}' is about an amenity although a priority sentence exists"
    assert sum(seen[k] for k in K.PRIORITY) >= len(BLDS) * 0.75, f"most buildings have a priority why: {dict(seen)}"
    # the order: highest standing first, ties in the order she raised them (parking before the dog before greenery ...)
    assert K.priority_order({})[:3] == ["parking", "dog", "green"]
    assert K.priority_order({"going_out": 90, "green": 80, "parking": 10})[:3] == ["going_out", "dog", "green"]
    # a made-up building with a pool and a garage: the garage is the why; with only the pool, the pool
    hood = {"counts": {"buildings": 1}}
    unit = {"id": "u", "moments": {"sun": {"drive_min": 50}}, "parking": {}, "host": {}, "headlines": {}}
    b1 = {"about_building": "There is a pool on the property. The building has its own garage.", "about_points": [], "amenities": {}}
    f = K.building_facts(b1, [unit], hood)
    if f["park_kind"] not in ("garage", "covered") and not f["park_included"]:
        K_test = dict(K.GOOD)                                         # the parking test reads the apartment's parking facts
        K.GOOD["parking"] = (K.GOOD["parking"][0], lambda f: True)
    try:
        why, _, _, _, topic = K.pick_why_give_up(b1, [unit], hood, {}, {"parking": 5, "home": 99})
        assert (why, topic) == ("The building has its own garage.", "parking"), (why, topic)
        b2 = dict(b1, about_building="There is a pool on the property.")
        why, _, _, _, topic = K.pick_why_give_up(b2, [unit], hood, {}, {"parking": 5, "home": 99})
        assert (why, topic) == ("There is a pool on the property.", "amenity"), (why, topic)
    finally:
        if "K_test" in dir():
            K.GOOD.update(K_test)


@test
def why_and_give_up_are_existing_guarded_sentences():
    bb = {b["id"]: b for b in BASE["buildings"]}
    hb = {h["id"]: h for h in BASE["neighborhoods"]}
    for b in BLDS:
        assert b["why"] and b["why"].strip() and b["give_up"] and b["give_up"].strip(), b["id"]
        assert b["why"] != b["give_up"], b["id"]
        src, hood = bb[b["id"]], hb[b["neighborhood_id"]]
        us = [u for u in BASE["units"] if u["building_id"] == b["id"]]
        pool = [src.get("about_building")] + [p["text"] for p in src.get("about_points") or []]
        for u in us:
            pool += [(u.get("host") or {}).get("line"), (u.get("host") or {}).get("catch")]
            pool += [(x or {}).get("subhead") for x in (u.get("headlines") or {}).values()]
        pool += [(hood.get("host") or {}).get("intro")] + list((hood.get("prose") or {}).values()) + [p["text"] for p in hood.get("about_points") or []]
        text = " ".join(K.voice(x) for x in pool if x)
        for k in ("why", "give_up"):
            assert len(K.sentences(b[k])) == 1, (b["id"], k, b[k])
            assert b[k] in text, (b["id"], k, b[k])
            assert b[k + "_source"], b["id"]


@test
def no_banned_words_and_no_crime_wording():
    bad = re.compile(r"\ball[- ]in\b|\bcaps?\b|\bunits?\b|\bgates?\b|\bwe\b|\bnet[- ]effective\b", re.I)
    crime = re.compile(r"\bcrimes?\b|\bviolent\b|burglar|\bthefts?\b|\bstolen\b|break-ins?|carjack|per 1,000|\bpolice\b|\bsafe(?:ty|r)?\b", re.I)
    for path, s in strings(OUT):
        assert not bad.search(s), (path, s)
        assert not crime.search(s), (path, s)
        assert "your parents" not in s.lower(), (path, s)
        assert not re.search(r"\b(?:Year|years\[)\b", s) or "Year" not in s, (path, s)
    assert OUT["meta"]["anchor_label"] == "Mom and Dad"


@test
def no_phone_on_a_private_contact():
    src = {b["id"]: b for b in D["buildings"]}
    seen_private = 0
    for b in BLDS:
        c = b["contact"]
        kind = (src[b["id"]].get("contact") or {}).get("kind")
        if c is None:
            assert not src[b["id"]].get("contact"), b["id"]
            continue
        assert set(c) >= {"office_phone", "site", "private"}
        assert c["private"] == K.X.is_private_line(kind), b["id"]
        if c["private"]:
            seen_private += 1
            assert c["office_phone"] is None and c["hours"] is None, b["id"]
        if c["office_phone"] is not None:
            assert len(re.sub(r"\D", "", c["office_phone"])) >= 7 and not K.X.is_private_line(kind)
    assert seen_private >= 1, "the kept set has broker / owner listings: the test must have met one"
    # the rule itself, on made-up records
    assert K.contact({"contact": {"phone": "(555) 010-0000", "site": "https://x.example", "kind": "individual owner"}})["office_phone"] is None
    assert K.contact({"contact": {"phone": "(555) 010-0000", "site": None, "kind": "broker"}})["office_phone"] is None
    assert K.contact({"contact": {"phone": "(555) 010-0000", "site": None, "kind": "leasing office"}})["office_phone"] == "(555) 010-0000"
    assert K.contact({"contact": {"phone": "call us", "site": "https://x.example", "kind": "leasing office"}})["office_phone"] is None
    assert K.contact({}) is None


@test
def missing_values_are_null():
    raw = K.OUT.read_text(encoding="utf-8")
    json.loads(raw, parse_constant=lambda c: (_ for _ in ()).throw(AssertionError(f"{c} in the file")))

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, x in o.items():
                walk(x, f"{path}.{k}")
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, f"{path}[{i}]")
        elif isinstance(o, float):
            assert not math.isnan(o) and not math.isinf(o), path
        elif isinstance(o, str):
            assert o.strip() and o.strip().lower() not in ("nan", "none", "null", "not_found", "n/a", "unknown", "undefined"), (path, o)
    walk(OUT)
    for b in BLDS:                                    # a figure that is not known is null, never 0
        u = U[b["apartments"][0]["id"]]
        if not u["moments"]["sun"].get("toll_complete"):
            assert b["facts"]["toll_round_trip"] is None, b["id"]
        if (u.get("parking") or {}).get("kind") in (None, ""):
            assert b["facts"]["parking"]["kind"] is None and b["facts"]["parking"]["fee"] is None, b["id"]
        for a in b["apartments"]:
            s = U[a["id"]]
            assert (a["sqft"] is None) == (s.get("sqft") is None) and (a["floor_text"] is None) == (s.get("floor") is None)


@test
def contract_shape():
    assert set(OUT) == {"meta", "experiences", "neighborhoods", "buildings", "either_or"}
    assert set(OUT["meta"]) >= {"built_at", "rent_limit", "counts", "tour_start", "move_in_by", "anchor_label"}
    for e in EXPS:
        assert set(e) >= {"id", "label", "tagline", "illustration_id", "figures", "story", "neighborhood_ids"}
        assert set(e["figures"]) >= {"rent_median", "rent_range", "total_median", "total_range", "drive_min_median", "drive_min_range",
                                     "toll_round_trip_range", "apartments", "buildings"}
        assert e["label"].endswith("Experience") and e["tagline"]
    for h in HOODS:
        assert set(h) >= {"id", "name", "state", "experience_id", "lat", "lon", "drive_min", "toll_round_trip", "about", "points",
                          "parked_under", "also_nearby", "building_ids", "parked_distance_km", "parked_label"}
        assert h["about"] and h["points"] and all(set(p) == {"icon", "text"} for p in h["points"])
    for b in BLDS:
        assert set(b) >= {"id", "name", "address", "city", "state", "lat", "lon", "neighborhood_id", "experience_id", "rank_score", "why",
                          "give_up", "facts", "scores", "confirm", "tour_questions", "disclosures", "photos_url", "listing_url", "contact",
                          "about", "points", "day", "apartments", "checked_summary", "why_source", "why_topic"}
        assert b["name"] and set(b["scores"]) == set(K.SCORE_KEYS)
        assert set(b["facts"]) >= {"rent_from", "rent_to", "total_from", "total_to", "drive_min", "toll_round_trip", "parking", "dog"}
        assert set(b["facts"]["parking"]) >= {"summary", "kind", "fee"} and set(b["facts"]["dog"]) >= {"summary", "weight_limit_lb"}
        assert all(set(c) == {"label", "question"} and c["question"] for c in b["confirm"])
        assert all(d["level"] in ("strong", "mixed", "weak", None) and d["title"] for d in b["day"]) and len(b["day"]) == 6
        best = U[b["apartments"][0]["id"]]             # a moment has no level only where the page data has none (size not published)
        assert [d["level"] for d in b["day"]] == [best["moments"][k].get("rating") for k, _ in K.DAY_TITLES], b["id"]
        open_items = {(U[a["id"]]["confirm"] or {}).get("question") for a in b["apartments"] if (U[a["id"]]["confirm"] or {}).get("asterisk")}
        assert {c["question"] for c in b["confirm"]} == open_items, b["id"]
        for a in b["apartments"]:
            assert set(a) >= {"id", "label", "beds", "sqft", "floor_text", "rent", "total", "available_text", "offer", "star", "confirm_label",
                              "listing_url", "source_site", "last_read", "checked"}
            u = U[a["id"]]
            assert a["star"] == bool((u["confirm"] or {}).get("asterisk")) and (a["confirm_label"] is not None) == a["star"]
            assert a["offer"] == bool(u["rent"].get("asterisk")) and re.fullmatch(r"\d{4}-\d\d-\d\d", a["last_read"])
            assert a["label"].startswith("Apartment")


@test
def either_or_questions_are_real_trade_offs():
    qs = OUT["either_or"]
    assert len(qs) <= 3 and len({q["id"] for q in qs}) == len(qs)
    for q in qs:
        (ka, da), = q["a"]["weight"].items()
        (kb, db), = q["b"]["weight"].items()
        assert ka in K.SCORE_KEYS and kb in K.SCORE_KEYS and ka != kb and da > 0 and db > 0
        rho = K.spearman([b["scores"][ka] for b in BLDS], [b["scores"][kb] for b in BLDS])
        top = lambda k: {b["id"] for b in sorted(BLDS, key=lambda b: (-b["scores"][k], b["id"]))[:K.TOP_N]}
        assert rho < 0 and (rho <= K.TRADE_RHO or len(top(ka) & top(kb)) <= K.TOP_OVERLAP), (q["id"], rho)
        assert q["question"] and q["a"]["label"] and q["b"]["label"]
    again, _ = K.either_or(BLDS)
    assert again == qs
    # a made-up set where two scores rise together gives no question about them
    fake = [{"id": str(i), "scores": {k: i / 10 for k in K.SCORE_KEYS}} for i in range(10)]
    assert K.either_or(fake)[0] == []


@test
def helpers():
    assert K.voice("Your parents are close, and your parents visit.") == "Mom and Dad are close, and Mom and Dad visit."
    assert K.sentences("One. Two is here. Three!") == ["One.", "Two is here.", "Three!"]
    assert K.two("One. Two is here. Three!") == "One. Two is here."
    a, b = {"lat": 40.0, "lon": -74.0}, {"lat": 41.0, "lon": -74.0}
    assert abs(K.haversine_km(a, b) - 111.19) < 0.1 and K.haversine_km(a, a) == 0
    hoods = [{"id": "a", "experience_id": "x", "lat": 40.0, "lon": -74.0}, {"id": "b", "experience_id": "x", "lat": 40.1, "lon": -74.0},
             {"id": "c", "experience_id": "x", "lat": 40.9, "lon": -74.0}, {"id": "d", "experience_id": "y", "lat": 40.0, "lon": -74.0}]
    K.park_neighborhoods(hoods, {"a": 1, "b": 3, "c": 2, "d": 1})
    by = {h["id"]: h for h in hoods}
    assert by["a"]["parked_under"] == "b" and by["b"]["also_nearby"] == ["a"] and by["d"]["parked_under"] is None
    notes = K.park_neighborhoods(hoods[:3], {"a": 1, "b": 1, "c": 1})       # no neighborhood with two or more
    assert len(notes) == 2 and all(x["fallback"] for x in notes) and not any(h["parked_under"] and h["also_nearby"] for h in hoods[:3])
    assert sum(1 for h in hoods[:3] if h["parked_under"] is None) == 1
    assert K.median([3, 1, 2]) == 2 and K.median([1, 2, 3, 4]) == 2.5 and K.median([None]) is None
    assert K.usd10(2050.5) == "$2,050" and K.usd10(1805) == "$1,810"
    kept = K.base_page(D)
    assert all(K.rent_now(u) <= K.RENT_LIMIT for u in kept["units"]) and len(D["units"]) > len(kept["units"]), "the source is not changed"
    # the rent as it now stands: a re-read that changed the price moves rent.basis (kind "listed"), not rent.listed
    assert K.rent_now({"rent": {"listed": 1945, "basis": 1895.0, "basis_kind": "listed"}}) == 1895
    assert K.rent_now({"rent": {"listed": 2379, "basis": 2395.0, "basis_kind": "12_month"}}) == 2379, "a 12-month basis is not a listed price"
    assert K.rent_now({"rent": {"listed": 1700, "basis": None}}) == 1700 and K.rent_now({}) is None
    assert K.parked_label(0.8) == "Also nearby" and K.parked_label(10.0) == "Also nearby" and K.parked_label(10.1) == "Also in this kind of life"
    assert K.day_words("2026-11-17") == "November 17" and K.day_words("2026-12-01T10:00:00+00:00") == "December 1"


def main():
    failed = 0
    for f in TESTS:
        try:
            f()
            print(f"ok   {f.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {f.__name__}: {str(e)[:400]}")
    print(f"{len(TESTS) - failed} of {len(TESTS)} tests pass; {len(APTS)} apartments, {len(BLDS)} buildings, {len(HOODS)} neighborhoods, {len(EXPS)} experiences")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
