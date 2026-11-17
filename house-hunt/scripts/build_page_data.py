"""Export the page's data contract: site/data.json (read by the page; nothing else feeds the UI).

Shape: meta, years[], neighborhoods[], units[] (shown), avoid[] (avoid cards), held[] (good candidates waiting on one
confirmation). Every number that appears on the page comes from data/ranked_units.csv (which reads only the master
tables) and data/lifestyle_groups.csv. Unknown values are null; the page must show "Not known yet", never a guess.
"""
import json, sys, re
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT
import parsers
import build_neighborhoods as BN

PARENTS = BN.subcity_parents()          # child hood_id -> its city (Jersey City is split into neighborhoods)
ROUTE = lambda hid, source_area="": BN.route_to_children(hid, source_area, PARENTS)


def v(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return round(float(x), 2)
    s = str(x)
    return None if s in ("", "nan", "NaN") else x


def j(x, default):
    try:
        return json.loads(x) if isinstance(x, str) and x else default
    except ValueError:
        return default


# Day moments: a three-level rating per moment (strong / mixed / weak; None = the data cannot say, no chip).
# Owner, 2026-11-16: the levels are ABSOLUTE thresholds on each moment's own measure, not a scale against staying in
# Queens (that scale made Sunday "weak" almost everywhere, which says nothing). They are set so that across the shown
# places no level holds more than about 60 percent for any moment; scripts/test_rules.py --data checks that.
MOMENT_THRESHOLDS = {
    "wake": {"measure": "minutes on foot to the nearest green space", "strong": "3 minutes or less", "mixed": "over 3 and up to 10 minutes", "weak": "more than 10 minutes"},
    "work": {"measure": "room for a work day at home: size and a separate bedroom", "strong": "a separate bedroom and 700 sq ft or more",
             "mixed": "everything between", "weak": "under 550 sq ft, or a studio under 600 sq ft", "null": "size not published"},
    "after": {"measure": "restaurants and bars within a 10-minute walk (800 m)", "strong": "15 or more restaurants and at least one bar", "mixed": "4 or more restaurants", "weak": "fewer than 4 restaurants"},
    "night": {"measure": "where you would park overnight", "strong": "a garage or gated parking at the building, and a front desk or controlled entry is stated",
              "mixed": "a garage with no stated front desk or controlled entry, covered parking, a lot, off-site parking, or parking not known",
              "weak": "street parking only, or the town restricts overnight street parking and no space at the building is confirmed"},
    "sat": {"measure": "bars and restaurants within 1,600 m", "strong": "5 or more bars and 30 or more restaurants", "mixed": "everything between", "weak": "at most 1 bar and fewer than 15 restaurants"},
    "sun": {"measure": "the drive to her parents, one way, with no traffic", "strong": "30 minutes or less", "mixed": "31 to 60 minutes", "weak": "more than 60 minutes"},
}


# Notes for the reader (they may be shown behind "See how we got this"): plain sentences, no field names, no working
# vocabulary. "Total with utilities and fees" is the page's name for the all-in figure. scripts/test_rules.py checks them.
META_NOTES = [
    "Drive times are estimates with no traffic.",
    parsers.TOLL_NOTE,
    "An asterisk on the rent means a special offer applies. The rent terms say what it is.",
    "Where a floor was read from the apartment number, the listing page does not state it. Confirm it on the tour.",
    "For a few towns no police agency publishes a crime rate for the town alone. There, the rule that nothing shown has more crime than Jamaica could not be tested, and the page says so.",
    "A parking fee counts as published only when the building's own page or a listing states it. A figure from a resident's review is an estimate and is labelled as one.",
    "An apartment with an asterisk has one thing still to confirm: the elevator, whether dogs are allowed, or whether the listing is real and available. The text beside it says what and why.",
    "Some things are worth knowing and never remove an apartment: a floor that is not published, a price quoted for a lease that is not 12 months, a cost that could pass $3,000 once parking and fees are known, a price that already has free months averaged in (only where the listing says so), a special offer (ask what a normal month costs), a condo rented by its owner, a dog weight limit with no number, and a town rule that restricts overnight street parking where the building's parking is not confirmed.",
    "Pet rent is always counted. Where a building does not publish it, the cost uses an estimate, the median of the known pet rents in the same state, and it is marked as an estimate.",
    "Where a building does not publish its parking fee or its required fees, a second figure adds the median of the known ones. It is shown beside the total with utilities and fees and is never used for the $3,000 limit.",
    "Experience and neighborhood figures (medians and ranges) are computed over the apartments shown on the page. A neighborhood's distances from the door are those of its median building.",
    "Where an elevator is named only on a listing site, in its amenity list or its text, it has not been confirmed on the building's own page.",
    "Each apartment carries the date its price was read.",
    "Cost lines that are not published add nothing to the total with utilities and fees. Each receipt names them as not published.",
]

SHOWN_FIGURE_KEYS = ["restaurants_800m", "bars_800m", "cafes_800m", "park_ha_800m", "park_walk_min", "open_water_m", "dog_park_m", "supermarket_m",
                     "train_station_m", "motorway_m", "restaurants_1600m", "bars_1600m"]


def toll_range(g, col):
    """[lowest, highest] round-trip toll among the rows, or None unless every route has a complete toll (never 0 for unknown)."""
    if col not in g or not g.toll_complete.astype(str).str.lower().eq("true").all():
        return None
    x = pd.Series([parsers.toll_known(a, b) for a, b in zip(g[col], g.toll_complete)], dtype=float).dropna()
    return [v(float(x.min())), v(float(x.max()))] if len(x) else None


def shown_figures(s, bl):
    """A neighborhood's door-distance figures over the BUILDINGS shown in it: one vote per building (the first shown
    apartment of the building that has the figure), then the median over the buildings. The written text and "At a
    glance" are computed the same way (scripts/check_scene_text.py: _building_table, glance), so the two agree. They
    used to be medians over the shown APARTMENTS, which let one building with eight apartments outvote seven buildings
    with one each. `s`: the shown rows of the neighborhood; `bl`: its buildings as the page data carries them.

    buildings_with_own_dog_area counts only a dog park or dog run on the property (amenities.dog_park_or_run). A pet
    spa or dog wash, and a dog amenity of unnamed kind, are counted apart."""
    order = s.sort_values("shown_rank") if "shown_rank" in s else s
    out = {}
    for k in SHOWN_FIGURE_KEYS:
        if k not in order:
            out[k] = None
            continue
        per_building = pd.to_numeric(order[k], errors="coerce").groupby(order.building_id).first().dropna()
        out[k] = v(float(per_building.median())) if len(per_building) else None
    am = [(b_.get("amenities") or {}) for b_ in bl]
    first = order.groupby("building_id").first()
    if "train_station_kind" in first:
        # independent check 5, N3: which kind of station the "train station" figure measures in this neighborhood (the kind of
        # the median building's station; kinds lists every kind among the shown buildings), and the commuter-rail distance
        tk = first.dropna(subset=["train_station_m"]).sort_values(["train_station_m", "train_station"]) if "train_station_m" in first else first.iloc[0:0]
        mid = tk.iloc[(len(tk) - 1) // 2] if len(tk) else None
        out["train_station_kind"] = v(mid.train_station_kind) if mid is not None else None
        out["train_station"] = v(mid.train_station) if mid is not None else None
        out["train_station_system"] = v(mid.train_station_system) if mid is not None else None
        out["train_station_kinds"] = {str(k): int(n) for k, n in first.train_station_kind.dropna().value_counts().sort_index().items()}
        cm = pd.to_numeric(first.commuter_station_m, errors="coerce").dropna() if "commuter_station_m" in first else pd.Series(dtype=float)
        out["commuter_station_m"] = v(float(cm.median())) if len(cm) else None
    pk = [(b_.get("parking") or {}).get("kind") for b_ in bl]
    out["buildings_with_garage"] = int(sum(1 for k in pk if k in ("garage", "gated_lot")))
    out["buildings_with_garage_or_covered"] = int(sum(1 for k in pk if k in ("garage", "gated_lot", "covered")))
    out["buildings_with_garage_as_paid_extra"] = int(sum(1 for b_ in bl if (b_.get("parking") or {}).get("garage_is_optional_extra")))
    out.update({"figures_over": "shown buildings (the median building)",
                "buildings_with_own_dog_area": int(sum(1 for a in am if a.get("dog_park_or_run"))),
                "buildings_with_pet_spa_or_wash": int(sum(1 for a in am if a.get("pet_spa_or_wash"))),
                "buildings_with_unspecified_dog_amenity": int(sum(1 for a in am if a.get("dog_amenity_unspecified"))),
                "buildings": len(bl)})
    return out


def moment_ratings(m, parking_rank=None, offsite=False, secured=False, overnight_restricted=False, sqft=None, beds=None):
    f = lambda x: None if x is None or x != x else float(x)
    out = {}
    w = f(m["wake"].get("park_walk_min"))
    out["wake"] = None if w is None else ("strong" if w <= 3 else ("weak" if w > 10 else "mixed"))
    sq, bed = f(sqft), (f(beds) or 0) >= 1
    out["work"] = None if sq is None else ("strong" if bed and sq >= 700 else ("weak" if (sq < 550 or (not bed and sq < 600)) else "mixed"))
    r, b = f(m["after"].get("restaurants_800m")), f(m["after"].get("bars_800m"))
    out["after"] = None if r is None else ("strong" if (r >= 15 and (b or 0) >= 1) else ("weak" if r < 4 else "mixed"))
    pr = f(parking_rank)
    if pr == 1 or overnight_restricted:
        out["night"] = "weak"
    elif pr == 4 and not offsite and secured:
        out["night"] = "strong"
    else:
        out["night"] = "mixed"                    # parking unknown is "mixed" by the owner's rule, not null
    bs, rs = f(m["sat"].get("bars_1600m")), f(m["sat"].get("restaurants_1600m"))
    out["sat"] = None if bs is None or rs is None else ("strong" if (bs >= 5 and rs >= 30) else ("weak" if (bs <= 1 and rs < 15) else "mixed"))
    d = f(m["sun"].get("drive_min")) if "sun" in m else None
    out["sun"] = None if d is None else ("strong" if d <= 30 else ("weak" if d > 60 else "mixed"))
    return out


# ============================================================================================================
# READER TEXT (independent check 4, D24). Everything the page prints about what is open, what to know and what each
# cost line rests on is WRITTEN HERE, from structured fields, through a small set of plain templates:
#   confirm.what / label / why / question, disclosures[].why / question / label, all_in_lines[].note / label,
#   tour_questions[], evidence.pause_points / avoid_points, neighborhoods[].safety.status_note.
# The pipeline's own working notes (rank.py's confirm_why, a checker's sentence, a parser's note) are kept only in
# the *_internal fields, which the page must not show. A reviewer's sentence from data/evidence/review_verdicts.csv
# (reviewed text, "plain words for the page") is used in place of a template only when it passes reader_ok() after
# plain(); otherwise the template for its kind is used. scripts/test_rules.py --data walks the whole page data.
# Vocabulary: apartment, never unit; no file paths; no pipeline or agent words; dates written out in full.
BANNED = re.compile(
    r"\bunits?\b|evidence pass|\bharvest\w*|\bbatch(?:es)?\b|docs/|\.csv\b|\.py\b|\.md\b|\.json\b|\bverdicts?\b|\bgates?\b|\bpipeline\b|\bcheckers?\b|live check|"
    r"\brefetch\w*|\bre-read\b|not re-read|stored value|HTTP \d|\brobots\b|refused us|the host is|\bscrap\w+|listing_id|\b[a-z]+_[a-z_]+\b|"
    r"(?:19|20)\d\d-\d\d-\d(?!\d)|(?:19|20)\d\d-\d(?!\d)|\.\.\.$|…$|\bnan\b|\bNone\b", re.I)
# the list in the task ("unit", "evidence pass", "harvest", "batch", a file path, "docs/", ".csv", "verdict", "gate",
# "pipeline", a truncated date): applied to every prose field of the page data, old and new
BANNED_CORE = re.compile(r"\bunits?\b|evidence pass|\bharvest\w*|\bbatch(?:es)?\b|docs/|\.csv\b|\bverdicts?\b|\bgates?\b|\bpipeline\b|"
                         r"(?:^|[\s(])(?:[\w.-]+/)+[\w.-]+\.(?:py|csv|md|json|txt)\b|(?:19|20)\d\d-\d\d-\d(?!\d)", re.I)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def reader_ok(text) -> bool:
    return not BANNED.search(str(text or ""))


def day(iso) -> str:
    """'2026-08-22' -> 'August 22, 2026'; '' when it is not a full date (a date is never printed cut short)."""
    m = re.match(r"((?:19|20)\d\d)-(\d\d)-(\d\d)", str(iso or ""))
    if not m or not 1 <= int(m.group(2)) <= 12:
        return ""
    return f"{MONTHS[int(m.group(2)) - 1]} {int(m.group(3))}, {m.group(1)}"


def usd(x) -> str:
    try:
        return "${:,.0f}".format(float(x))
    except (TypeError, ValueError):
        return ""


def plain(text) -> str:
    """A reviewed sentence in the page's vocabulary: apartment for unit, ISO dates written out. Nothing else is changed."""
    t = str(text or "").strip()
    t = re.sub(r"\bunit map\b", "map of apartments", t)
    t = re.sub(r"\bUnits\b", "Apartments", t)
    t = re.sub(r"\bunits\b", "apartments", t)
    t = re.sub(r"\bUnit\b", "Apartment", t)
    t = re.sub(r"\bunit\b", "apartment", t)
    t = re.sub(r"\ban apartment\b", "an apartment", t)
    t = re.sub(r"\ba apartment\b", "an apartment", t)
    t = re.sub(r"((?:19|20)\d\d-\d\d-\d\d)", lambda m: day(m.group(1)) or m.group(1), t)
    return t


def reviewed(text):
    """The reviewer's sentence when it is fit to print, else None (the caller then uses the template)."""
    t = plain(text)
    return t if t and reader_ok(t) and len(t) <= 420 else None


def _f(r, c):
    x = r.get(c)
    return None if x is None or (isinstance(x, float) and np.isnan(x)) or str(x) in ("", "nan") else x


def _num(r, c):
    try:
        x = float(_f(r, c))
        return None if np.isnan(x) else x
    except (TypeError, ValueError):
        return None


def _months(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _a(n) -> str:
    """'an 11-month lease', 'an 18-month lease', 'a 13-month lease'."""
    return "an" if str(n).startswith(("8", "11", "18")) else "a"


OPEN_LABEL = {"elevator": "the elevator", parsers.FLOOR_OR_ELEVATOR_LABEL: parsers.FLOOR_OR_ELEVATOR_READER_LABEL, "dogs allowed": "whether dogs are allowed", "availability": "whether this apartment is still available",
              "listing": "whether this listing is current", "eligibility": "who can rent this apartment"}
LISTING_LABEL = {"place": "the building's exact address", "address_mismatch": "which building this apartment is in", "price_doubt": "the price", "sibling_12": "the 12-month price"}
ELEVATOR_WHY = {
    "select_buildings": "The building's own page says only some of its buildings have an elevator. It does not say which.",
    "city_record": "The city's record for this address describes a building without an elevator, while a listing names one.",
    "low_rise": "A listing site names an elevator, but the property is described as low buildings or townhomes.",
    "listing_site_only": "A listing site names an elevator. The building's own page does not mention one.",
    "height_implied": "No page says in words that the building has an elevator. Its height suggests one.",
    "not_confirmed": "A listing names an elevator, but no page of the building's own confirms it.",
    "complex": "An elevator is named for the property as a whole. The property has several buildings, so that does not tell us one serves this apartment.",
    "reviewer": "An elevator is not confirmed for this apartment.",
}
DOGS_WHY = {
    "sources_disagree": "Two listing sites disagree on whether dogs are allowed, and the building's own page does not settle it.",
    "case_by_case": "The pet policy says pets are welcome on approval. It does not say dogs are allowed.",
    "ask_policy": "The listing says to contact the building for its pet policy. No page says dogs are allowed.",
    "dogs_not_named": "The listing says small pets are allowed and does not name dogs.",
    "not_reread": "A listing said dogs are allowed, but the page could not be opened again to confirm it.",
    "listing_site_only": "One listing site says small dogs are allowed. No page of the building's own confirms it.",
    "not_confirmed": "No page we read confirms that dogs are allowed.",
    "reviewer": "It is not confirmed that dogs are allowed here.",
}


def _sibling(r):
    """('425', 2606, 24, 3210) from the sibling long-lease note, or None."""
    m = re.search(r"unit (\S+) of this building is \$([\d,]+) on its (\d+)-month price and \$([\d,]+) on a 12-month lease", str(_f(r, "price_12_sibling_why") or ""))
    return (m.group(1), float(m.group(2).replace(",", "")), int(m.group(3)), float(m.group(4).replace(",", ""))) if m else None


def _stale(r):
    """(date, days) of the stale page or old availability date behind a 'listing' item, from the structured columns first."""
    why = str(_f(r, "listing_stale_why") or "") + " " + str(_f(r, "listing_warning") or "")
    m = re.search(r"availability date ((?:19|20)\d\d-\d\d-\d\d) (?:was|is) (\d+) days", why)
    if m:
        return "date", m.group(1), int(m.group(2))
    d = _f(r, "page_modified_date")
    m = re.search(r"last changed on ((?:19|20)\d\d-\d\d-\d\d), (\d+) days", why) or re.search(r"STALE PAGE ((?:19|20)\d\d-\d\d-\d\d)", why)
    if m:
        return "page", m.group(1), int(m.group(2)) if m.lastindex and m.lastindex >= 2 else _months(_f(r, "listing_stale_days"))
    return ("page", str(d)[:10], _months(_f(r, "listing_stale_days"))) if d else ("page", "", None)


def open_item_text(r):
    """(what, label, why, question, why_internal) for the ONE open item of a shown apartment, or None."""
    keys = [k for k in str(_f(r, "open_keys") or "").split(";") if k]
    if not keys:
        return None
    key = keys[0]
    code = (str(_f(r, "open_codes") or "").split(";") + [""])[0]
    what = str(_f(r, "confirm_what") or "").split("; ")[0] or {"dogs": "dogs allowed"}.get(key, key)
    rv_why, rv_q = reviewed(_f(r, "open_review_why")) if len(keys) == 1 else None, reviewed(_f(r, "open_review_question")) if len(keys) == 1 else None
    label, why, q = OPEN_LABEL.get(what, what), "", ""
    if key == "elevator" and code == parsers.FLOOR_OR_ELEVATOR_CODE:
        # owner, 2026-11-17: no elevator established and no floor published: ONE open item (parsers.floor_elevator_rule)
        label = parsers.FLOOR_OR_ELEVATOR_READER_LABEL
        why = ("A page we read says this building has no elevator, and no page gives the floor. Without an elevator, only an apartment a single flight up (floor 2) qualifies."
               if str(_f(r, "elevator") or "").lower() in ("no", "conflicting") or _f(r, "elevator_said_no") == "yes"
               else "No page we read gives the floor or says the building has an elevator. An apartment a single flight up (floor 2) needs no elevator; a higher floor does.")
        q = parsers.FLOOR_OR_ELEVATOR_READER_Q
    elif key == "elevator":
        if code == "height_only":
            fl = _months(_f(r, "building_floors")) or _months(_f(r, "pluto_floors"))
            why = f"No page we read says the building has an elevator. It has {fl} floors, which suggests one." if fl and fl >= 6 else "No page we read says the building has an elevator. Its height suggests one."
        else:
            why = ELEVATOR_WHY.get(code, ELEVATOR_WHY["reviewer"])
        q = "Is there an elevator in this apartment's building, and does it reach this floor?" if code in ("complex", "select_buildings", "low_rise") else "Does the building have an elevator?"
    elif key == "dogs":
        why, q = DOGS_WHY.get(code, DOGS_WHY["reviewer"]), "Are dogs allowed? Ask for the pet policy in writing."
    elif key == "availability":
        why = ("Another listing site shows this address without this apartment, and the listing itself could not be opened again." if code == "second_site"
               else "It is not confirmed that this apartment is still available.")
        q = "Is this apartment still available, and at this price?"
    elif key == "listing":
        label = LISTING_LABEL.get(code, label)
        q = "Is this apartment still available, and at this price?"
        if code == "place":
            why, q = "The listing's map position and its street address do not match, so the drive time and the surroundings shown here may be for another spot.", "What is the building's exact street address?"
        elif code == "address_mismatch":
            why, q = "The listing's address and the building's own information differ. This apartment may be in a neighboring building of the same complex.", "Which building is this apartment in, and what is its address?"
        elif code == "price_doubt":
            why, q = "The price is well below similar apartments nearby.", "Is this price real? Confirm it by phone before touring."
        elif code == "sibling_12":
            sb, lm = _sibling(r), _months(_f(r, "price_lease_months"))
            term = f"for {_a(lm)} {lm}-month lease" if lm else "for a long lease"
            why = (f"The price shown is {term}. Another apartment in this building costs {usd(sb[1])} on its {sb[2]}-month lease and {usd(sb[3])} on a 12-month lease, so this one's 12-month price may be much higher."
                   if sb else f"The price shown is {term}, and the 12-month price in this building can be much higher.")
            q = "What is the rent on a 12-month lease? Ask before touring."
        elif code in ("stale_page", "stale_date"):
            kind, d, n = _stale(r)
            if kind == "date" and day(d):
                why = f"The move-in date on the listing is {day(d)}, more than six months ago. The apartment may have sat empty, or the date may be out of date."
            elif day(d):
                why = f"The listing page was last changed on {day(d)}" + (f", {n} days before {'the first tour day, November 22' if 'by the first tour day' in str(_f(r, 'listing_stale_why') or '') else 'we read it'}" if n else "") + ", and no second site lists this apartment."
            else:
                why = "The listing page has not changed in over two months, and no second site lists this apartment."
        else:
            why = "Something about this listing did not match the building's own information." if code == "warning" else "This listing could not be fully confirmed."
    elif key == "eligibility":
        q = "Is this apartment open to any renter on an ordinary lease?"
        if code == "income_tag":
            why, q = "A listing site tags this building as income-restricted. The manager's own page does not say so and gives no income limit.", "Is this apartment open to any renter, or is there an income limit?"
        elif code == "not_normal_lease":
            why = "The listing's wording suggests this is not an ordinary one-year lease (for example a short stay, a sublet, or student or corporate housing)."
        else:
            why = "It is not settled who can rent this apartment."
    # a reviewer's sentence about THIS apartment is more specific than the template: used when it is fit to print
    if rv_why and (code == "reviewer" or key in ("listing", "availability", "eligibility")) and code not in ("place", "sibling_12"):
        why = rv_why
    if rv_q and (code == "reviewer" or key in ("listing", "availability", "eligibility")) and code not in ("place", "sibling_12"):
        q = rv_q
    return what, label, why, q, str(_f(r, "confirm_why") or "")


OFFER_WORD = {"dollar_credit": "a one-time credit or gift", "look_and_lease": "a one-time credit for applying quickly", "reduced_deposit_or_fee": "a reduced deposit or a waived fee"}
DISCLOSURE_LABEL = {"floor not published": "floor not published", "lease term": "lease length", "could pass $3,000": "could pass $3,000", "special offer": "special offer",
                    "net-effective rent": "average rent after free months", "condo rented by its owner": "condo rented by its owner",
                    "dog weight limit not published": "dog weight limit not published", "overnight street parking": "overnight street parking",
                    "income requirement": "income requirement", "credit score requirement": "credit score requirement", "furnished apartment": "furnished apartment",
                    "broker fee": "broker fee", "no broker fee": "no broker fee", "one-time costs": "one-time costs", "washer and dryer to confirm": "washer and dryer to confirm",
                    "something else to know": "something else to know"}


def _free_text(r):
    """'up to 2 months' / '6 weeks' / '' from the structured offer fields (independent check 4, D20: 'up to' is kept)."""
    fm, typ = str(_f(r, "rent_free_months") or ""), str(_f(r, "rent_offer_type") or "")
    up = "up to " if _f(r, "rent_offer_up_to") == "yes" else ""
    m = re.fullmatch(r"\s*([\d.]+)(?:\s*-\s*([\d.]+))?\s*", fm)
    if not m:
        return ""
    hi = float(m.group(2) or m.group(1))
    if typ == "weeks_free":
        w = round(hi * 52 / 12)
        return f"{up}{w} week{'s' if w != 1 else ''}"
    n = f"{hi:g}"
    return f"{up or ('up to ' if m.group(2) else '')}{n} month{'s' if hi != 1 else ''}"


def disclosure_text(d, r):
    """(label, why, question) for one disclosure, from its code and the row's structured columns."""
    what, code = d.get("what") or "", d.get("code") or ""
    kind, _, sub = code.partition(":")
    rv_why, rv_q = reviewed(d.get("review_why")), reviewed(d.get("review_question"))
    label, why, q = DISCLOSURE_LABEL.get(what, what), "", ""
    lm, p12 = _months(_f(r, "price_lease_months")), _num(r, "price_12_month")
    if kind == "floor":
        fl, un = _months(_f(r, "unit_floor")), _f(r, "unit")
        why = (f"The listing does not give the floor. Floor {fl} is our reading of the apartment number {un}." if sub == "floor_read_from_number" and fl and un
               else "The listing does not give the floor.")
        q = d.get("question") or "Floor not published: confirm it is above the ground floor"
    elif kind == "lease":
        q = "What is the rent on a 12-month lease?"
        listed = _num(r, "live_price") if str(_f(r, "live_status")) in ("live", "changed") and _num(r, "live_price") else _num(r, "listed_rent")
        if sub == "uses_12_month" and p12:
            why = (f"The listing shows {usd(listed)} for {_a(lm)} {lm}-month lease. " if lm and listed else "The price on the listing is not the 12-month price. ") + f"The rent and the total here use the 12-month price, {usd(p12)}."
        elif sub == "sibling_12":
            why = (f"The price shown is for {_a(lm)} {lm}-month lease. " if lm else "The price shown is for a long lease. ") + "The 12-month price is not published, and in this building it can be much higher: ask for it."
        elif sub == "term" and lm:
            why = f"The price shown is for {_a(lm)} {lm}-month lease: ask for the 12-month price."
        elif sub == "lowest_of_terms":
            why = "The price shown is the lowest across the lease lengths offered. The listing does not say which length it belongs to."
        else:
            why = rv_why or "The price shown may not be the 12-month price: ask for it."
    elif kind == "cost":
        a, l = _num(r, "all_in"), _num(r, "all_in_likely")
        # N11: a utility with no estimate here (gas, in a few Connecticut towns) is one of the unpublished lines too
        names = [{"electric": "electricity"}.get(x, x) for x in str(_f(r, "unknown_cost_lines") or "").split("; ")
                 if x in ("parking", "required fees", "some required fees", "gas", "electric", "internet")]
        subj = (", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]) if names else "parking and the required fees"
        verb = "costs what it typically does" if len(names) == 1 and names[0] in ("parking", "gas", "electricity", "internet") else "cost what they typically do"
        why = (f"On what is published the total is {usd(a)} a month. If {subj} {verb}, it would be about {usd(l)}."
               if a and l else "Parking or required fees are not published; once they are known the total could pass $3,000.")
        q = "What do parking and the required monthly fees cost here?" if not names or any(n in ("parking", "required fees", "some required fees") for n in names) else "Who pays for heat and cooking gas, and what does it cost?"
    elif kind == "condo":
        why = rv_why or ("City records show this building is a condominium, so the apartment is rented out by its owner, not by a leasing office." if sub == "city_record"
                         else "The listing is for a condo or co-op apartment rented out by its owner, not by a leasing office.")
        q = rv_q or "What are the building's rules for renting this apartment (application, fees, pets)?"
    elif kind == "other":
        why = rv_why or "There is one more thing to ask about this apartment before touring."
        q = rv_q or ""
    elif kind == "net_effective":
        why, q = "The rent shown is the average after free months, not what you pay each month.", "What is the full monthly rent, and when is the first full payment due?"
    elif kind == "offer":
        free, lease = _free_text(r), _months(_f(r, "rent_lease_months"))
        if sub in ("months_free", "weeks_free") and free:
            why = f"The listing advertises {free} of free rent" + (f" on {_a(lease)} {lease}-month lease" if lease and lease != 12 else "") + "."
        elif sub in ("months_free", "weeks_free"):
            why = "The listing advertises free rent."
        else:
            why = f"The listing advertises {OFFER_WORD.get(sub, 'a special offer')}."
        if _f(r, "rent_offer_select_units") == "yes":
            why += " It applies to selected apartments only."
        why += " The page does not say the price shown already includes it, so the price is treated as the normal monthly rent."
        q = "Special offer: ask what a normal month costs"
    elif kind == "dog_weight":
        why, q = "The pet policy says a weight limit applies and gives no number.", parsers.DOG_WEIGHT_QUESTION
    elif kind == "overnight_parking":
        town, rule = str(_f(r, "street_overnight_town") or "").strip(), plain(_f(r, "street_overnight_rule"))
        why = f"{town}: {rule}" if town and rule else "The town restricts overnight parking on the street."
        q = "Overnight street parking is restricted here: confirm the building has a space, and its cost"
    elif kind == "income_requirement":
        v_ = plain(str(_f(r, "cond_income") or "")).strip().rstrip(".")
        why, q = (f"Income requirement: {v_}." if v_ and reader_ok(v_) else "The listing states an income requirement."), "Do you meet the income requirement, and does a guarantor count?"
    elif kind == "credit_requirement":
        why, q = f"Credit score requirement: {_f(r, 'cond_credit')}.", "What credit score does the application need?"
    elif kind == "furnished":
        why, q = "Furnished apartment.", "Is the furniture optional, and is this a standard 12-month lease?"
    elif kind == "broker_fee":
        why, q = "Broker fee: the listing says a broker fee applies; ask how much.", "How much is the broker fee, and who pays it?"
    elif kind == "no_broker_fee":
        why, q = "No broker fee, per the listing.", ""
    elif kind == "one_time_costs":
        v_ = str(_f(r, "one_time_costs") or "").strip()
        why, q = (f"One-time costs, per the listing: {v_}. They are not part of the monthly total." if v_ else "The listing states one-time costs at signing."), "What is due at signing, in total?"
    elif kind == "laundry_appliance_list":
        why, q = parsers.laundry_tag_text(_f(r, "in_unit_appliances")) + ".", parsers.laundry_tag_question(_f(r, "in_unit_appliances"))
    else:
        why, q = rv_why or "", rv_q or ""
    return label, why, q


LINE_LABEL = {"rent (net-effective)": "rent (average after free months)"}
STATE_NAME = {"NJ": "New Jersey", "NY": "New York", "CT": "Connecticut"}


def receipt_note(l):
    """The reader's note for one cost line, from its code and data (all_in.py). Never the parser's working note."""
    code, d, amount = l.get("code") or "", l.get("data") or {}, l.get("amount")
    bits = []
    if code.startswith("rent"):
        lm = _months(d.get("lease_months"))
        if code == "rent_12_month":
            bits.append((f"The listing shows {usd(d.get('listed'))} for {_a(lm)} {lm}-month lease. " if lm else "") + "This is the 12-month price.")
        elif code == "rent_net_effective":
            bits.append("The average monthly rent after the free months in the offer." + (f" The full monthly rent is {usd(d.get('gross'))}." if d.get("gross") and d.get("gross") != amount else ""))
        elif lm:
            bits.append(f"The price shown is for {_a(lm)} {lm}-month lease. The 12-month price is not published.")
        if d.get("old_price"):
            bits.append(f"The price changed since we first read it: it was {usd(d.get('old_price'))}.")
    elif code == "fees_unknown":
        bits.append("The building charges a monthly fee, but the amount is not published." if d.get("fee_exists") else "Not published. Ask which monthly fees are added to the rent.")
    elif code == "fees_in_price":
        bits.append("Already inside the price shown.")
    elif code == "fees_published":
        bits.append("The required monthly fees published for this building.")
        if d.get("alternatives"):
            bits.append("The page gives more than one amount; the higher is used.")
        if d.get("differs_by_unit"):
            bits.append("The fee differs from apartment to apartment.")
        if d.get("more_not_published"):
            bits.append("A further fee exists whose amount is not published.")
    elif code == "pet_published":
        bits.append("As published for this building." + (" The page gives more than one amount; this is for one pet." if d.get("several_amounts") else ""))
    elif code == "pet_estimate":
        st = STATE_NAME.get(d.get("state"), "")
        bits.append("Not published for this building. This is the typical pet rent" + (f" in {st}" if st else "") + (f", from {d.get('buildings')} buildings that publish one." if d.get("buildings") else "."))
    elif code == "pet_unknown":
        bits.append("Not published.")
    elif code == "parking_included":
        bits.append("A space is included at no charge.")
    elif code == "parking_street":
        bits.append("Street parking only: the listing names no garage or lot.")
    elif code == "parking_estimate_review":
        bits.append("From a resident's review" + (f" dated {day(d.get('review_date'))}" if day(d.get("review_date")) else "") + ", not from the building: an estimate.")
    elif code == "parking_published":
        pick, lo, hi = d.get("pick"), d.get("low"), d.get("high")
        if pick == "first_space":
            bits.append("The price of the first space.")
        elif pick == "lowest_covered":
            bits.append("The lowest published price for a covered or garage space.")
        elif pick == "lowest_listed" and lo and hi:
            bits.append(f"The lowest of the published prices ({usd(lo)} to {usd(hi)}).")
        elif pick == "range" and lo and hi:
            bits.append(f"The low end of the published range, {usd(lo)} to {usd(hi)}.")
        else:
            bits.append("As published for this building.")
        if d.get("limited_time_free_not_counted"):
            bits.append("A free-parking offer for a limited time is not counted.")
    elif code == "parking_unknown":
        if d.get("extra_space_only"):
            bits.append("Only the price of an extra space is published.")
        elif d.get("limited_time_free_not_counted"):
            bits.append("Free for a limited time only; the regular fee is not published.")
        else:
            bits.append("Not published. Ask what a space costs.")
    elif code == "utility_estimate":
        bits.append("Cooking gas only; heat is included in the rent." if d.get("cooking_gas_only") else "An estimate for an apartment of this size in this area, not a quote.")
    elif code == "utility_included":
        bits.append("Included in the rent.")
    elif code == "utility_in_fees":
        bits.append("Covered by the building's required fees.")
    elif code == "utility_no_gas":
        bits.append("The building has no gas service.")
    elif code == "utility_unknown":
        bits.append("No estimate could be made.")
    return " ".join(bits) or None


def receipt_lines(lines):
    out = []
    for l in lines:
        out.append({"line": l.get("line"), "label": LINE_LABEL.get(l.get("line"), l.get("line")), "amount": l.get("amount"), "basis": l.get("basis"),
                    "note": receipt_note(l), "note_internal": l.get("note") or None, "code": l.get("code")})
    return out


_SRC_NAME = {"google_via_zumper": "Google reviews shown on Zumper", "own_site_widget": "the reviews on the building's own site", "google": "Google reviews", "apartments_com": "Apartments.com",
             "apartmentlist": "Apartment List", "zumper": "Zumper", "trulia": "Trulia"}
_CAT_NAME = {"class_c_violations": "serious housing violations", "heat_hot_water_complaints": "heat and hot water complaints", "pest_complaints": "pest complaints", "mold_complaints": "mold complaints",
             "elevator_outage": "elevator outages", "mold": "mold", "safety_incident": "safety incidents", "unresponsive_management": "management that does not respond", "pests": "pests",
             "car_crime": "car crime", "noise": "noise", "heat_hot_water": "heat and hot water"}
_cat = lambda t: _CAT_NAME.get(t.strip(), t.strip().replace("_", " "))


def evidence_points(text):
    """The avoid reasons / things worth knowing as plain sentences (the stored strings are in a fixed, internal
    vocabulary written by scripts/avoid.py; each known shape has one template; an unknown shape is dropped unless it
    is already fit to print)."""
    out = []
    for part in re.split(r"\s*\|\|\s*|;\s+(?=(?:reviews:|management:|elevator:|car crime:|NJ state|recent management|some elevator|\d+ (?:older|safety)|car crime mentioned))", str(text or "")):
        t = part.strip().rstrip(";")
        if not t:
            continue
        m = re.fullmatch(r"NJ state housing inspection: (\d+) open violations? at the latest report \(((?:19|20)\d\d-\d\d-\d\d)\)", t)
        if m:
            out.append(f"The state's latest housing inspection report ({day(m.group(2))}) listed {m.group(1)} open violation{'s' if m.group(1) != '1' else ''}."); continue
        m = re.fullmatch(r"(\d+) older management complaint\(s\); management may have changed", t)
        if m:
            out.append(f"{m.group(1)} older complaint{'s' if m.group(1) != '1' else ''} about management; the management may have changed since."); continue
        m = re.fullmatch(r"(\d+) safety incident report\(s\) at the address", t)
        if m:
            out.append(f"{m.group(1)} report{'s' if m.group(1) != '1' else ''} of a safety incident at the address."); continue
        m = re.fullmatch(r"car crime mentioned \((\d+) report\(s\), below the threshold or older\)", t)
        if m:
            out.append(f"{m.group(1)} mention{'s' if m.group(1) != '1' else ''} of car crime at the building, too few or too old to count against it."); continue
        if t == "some elevator complaints, below the threshold":
            out.append("A few complaints about the elevator."); continue
        if t == "recent management complaints, below the threshold":
            out.append("A few recent complaints about management."); continue
        m = re.fullmatch(r"reviews: rating at or below the pause line [\d.]+; (\w+) ([\d.]+) from (\d+) reviews, as of ((?:19|20)\d\d-\d\d-\d\d)(; rating figure is over \d+ months old)?", t)
        if m:
            out.append(f"Low review rating: {m.group(2)} out of 5 from {m.group(3)} reviews ({_SRC_NAME.get(m.group(1), m.group(1).replace('_', ' '))}, {day(m.group(4))})."
                       + (" The figure is more than a year and a half old." if m.group(5) else "")); continue
        m = re.fullmatch(r"reviews: (\d+) negative reviews in the last (\d+) months \(([^)]*)\); (\w+) ([\d.]+) from (\d+) reviews, as of ((?:19|20)\d\d-\d\d-\d\d).*", t)
        if m:
            out.append(f"Reviews: {m.group(1)} negative reviews in the last {m.group(2)} months ({', '.join(_cat(x) for x in m.group(3).split(';') if x.strip())}). "
                       f"Rating {m.group(5)} out of 5 from {m.group(6)} reviews ({_SRC_NAME.get(m.group(4), m.group(4).replace('_', ' '))}, {day(m.group(7))})."); continue
        m = re.fullmatch(r"elevator: (\d+)\+ complaints to the city in (\d+) months, above the 90th percentile for similar buildings", t)
        if m:
            out.append(f"Elevator: {m.group(1)} or more complaints to the city in {m.group(2)} months, more than at nine in ten similar buildings."); continue
        m = re.fullmatch(r"management: city records in the last (\d+) months above the 90th percentile on (.+)", t)
        if m:
            out.append(f"Management: in the last {m.group(1)} months, city records show more {', '.join(_cat(x) for x in m.group(2).split(','))} than at nine in ten similar buildings."); continue
        m = re.fullmatch(r"car crime: (\d+) vehicle thefts and thefts from vehicles within (\d+) m (?:in (\d+) months \(police data\)|\(((?:19|20)\d\d-\d\d-\d\d) to ((?:19|20)\d\d-\d\d-\d\d),? about ([\d.]+) months, ([^)]*)\)), "
                         r"at least double the median of ([\d.]+) for candidate buildings in (.+)", t)
        if m:
            out.append(car_crime_sentence(int(m.group(1)), int(m.group(2)), float(m.group(3) or m.group(6)), float(m.group(8)), m.group(9))); continue
        t2 = plain(t)
        if reader_ok(t2):
            out.append(t2[0].upper() + t2[1:] + ("" if t2.endswith(".") else "."))
    return list(dict.fromkeys(out))


def _times(ratio):
    """'about twice', 'about three times', 'more than ten times' for a ratio of 2 or more."""
    words = {2: "twice", 3: "three times", 4: "four times", 5: "five times", 6: "six times", 7: "seven times", 8: "eight times", 9: "nine times", 10: "ten times"}
    n = int(round(ratio))
    return "more than ten times" if ratio > 10.5 else "about " + words.get(max(2, n), "twice")


def _span_words(months):
    months = float(months)
    return {6: "six months", 12: "a year", 24: "two years"}.get(months, f"about {months:g} months")


def car_crime_sentence(n, metres, months, median, area) -> str:
    """Independent check 5, N19 / N13: the car-crime reason of an avoid card as one plain sentence from the counts.
    (The one place crime is stated: inside an avoid card.)"""
    ratio = n / median if median else None
    cmp_ = f"{_times(ratio)} what is typical for the buildings we looked at in {area}" if ratio and ratio >= 1.75 else f"more than is typical for the buildings we looked at in {area}"
    return f"Police recorded {n} car break-in{'s' if n != 1 else ''} or thefts within about {metres} meters (a few blocks) in {_span_words(months)}, {cmp_}."


_RECORD_THING = {"class_c_violations": ("serious housing violation", "serious housing violations"), "heat_hot_water_complaints": ("heat or hot water complaint", "heat and hot water complaints"),
                 "pest_complaints": ("pest complaint", "pest complaints"), "mold_complaints": ("mold complaint", "mold complaints"),
                 "elevator_complaints": ("elevator complaint", "elevator complaints")}


def record_sentence(category, window, excerpt):
    """'11 (22.92 per 100 units; citywide 90th percentile 15.79)' with its category and window -> '11 serious housing
    violations recorded by the city here in the last six months, more for its size than at nine in ten buildings in the
    city.' (it starts with the count: the page prints "On record: " before a text that starts with a digit)
    None when the excerpt is not a city-record count."""
    m = re.fullmatch(r"\s*(\d+) \(([\d.]+) per 100 units; citywide 90th percentile ([\d.]+)\)\s*", str(excerpt or ""))
    thing = _RECORD_THING.get(str(category or ""))
    if not m or not thing:
        return None
    n, rate, p90 = int(m.group(1)), float(m.group(2)), float(m.group(3))
    mw = re.fullmatch(r"last_(\d+)_months", str(window or ""))
    span = f" in the last {_span_words(mw.group(1))}" if mw else ""
    if p90 > 0 and rate >= 3 * p90:
        cmp_ = ", far more for its size than at nine in ten buildings in the city"
    elif rate > p90:
        cmp_ = ", more for its size than at nine in ten buildings in the city"
    else:
        cmp_ = ", which is within the usual range for a building its size"
    return f"{n} {thing[0] if n == 1 else thing[1]} recorded by the city here{span}{cmp_}."


def evidence_items(items):
    """The evidence items of an avoid or pause card. A city-record count ('23 (34.33 per 100 units; citywide 90th
    percentile 2.9)') becomes a reader sentence in `excerpt`; the raw count string is kept in `excerpt_internal`, and
    `kind` is 'record' (a count from a public record) or 'quote' (someone's words)."""
    out = []
    for it in items or []:
        it = dict(it)
        sent = record_sentence(it.get("category"), it.get("date"), it.get("excerpt"))
        if sent:
            it["excerpt_internal"], it["excerpt"], it["kind"] = it.get("excerpt"), sent, "record"
            mw = re.fullmatch(r"last_(\d+)_months", str(it.get("date") or ""))
            it["window_words"] = f"the last {_span_words(mw.group(1))}" if mw else None     # `date` stays as it was ('last_6_months')
        else:
            it.setdefault("kind", "quote")
        out.append(it)
    return out


PUBLIC_EVIDENCE = {}  # building_id -> what the evidence pass could read (data/avoid_buildings.csv: public_evidence); filled in main()


def safety_status(h):
    """('published', None) when the neighborhood's police agency publishes both a violent and a property rate, else
    ('not_published', why). The reason is a plain sentence for the page."""
    def has(k):
        x = h.get(k) if hasattr(h, "get") else None
        return x is not None and not (isinstance(x, float) and np.isnan(x)) and str(x) not in ("", "nan")
    if has("violent") and has("property"):
        return "published", None
    missing = "violent or property crime rate" if not has("violent") and not has("property") else ("violent crime rate" if not has("violent") else "property crime rate")
    st = STATE_NAME.get(str(h.get("state") if hasattr(h, "get") else ""), "")
    name = str(h.get("hood") if hasattr(h, "get") else "") or "This town"
    return "not_published", (f"No {missing} is published for {name}. It has no police department of its own in the FBI's list of reporting agencies; "
                             + (f"the {st} State Police cover it and report one total for the whole state, not a figure for the town. " if st == "Connecticut" else "the agency that covers it reports no figure for the town alone. ")
                             + "So the rule that nothing here has more crime than Jamaica could not be tested for this place, and no figure is guessed.")


def dedupe_questions(qs):
    """One question once (independent check 5, N20): 'What is the rent on a 12-month lease? Ask before touring.' and
    'What is the rent on a 12-month lease?' are the same question; the first wording met is kept."""
    key = lambda q: re.sub(r"\W+", " ", re.sub(r"(?i)\s*ask before touring\.?\s*$", "", str(q))).strip().lower()
    out, seen = [], set()
    for q in qs:
        k = key(q)
        if q and k not in seen:
            seen.add(k)
            out.append(q)
    return out


def unit(r):
    g = lambda c: v(r.get(c))
    # independent check 4, D24: every question is written from structured fields (apartment, never unit)
    oi = open_item_text(r) if g("confirm_asterisk") == "yes" or g("open_keys") else None
    disc = []
    for d in j(r.get("disclosures"), []):
        label, why, q = disclosure_text(d, r)
        disc.append({"what": d.get("what"), "label": label, "why": why or None, "question": q or None, "url": d.get("url") or None, "severity": d.get("severity") or None,
                     "code": d.get("code") or None, "why_internal": d.get("why") or None})
    qs = [oi[3]] if oi and oi[3] else []
    qs += [d["question"] for d in disc if d["question"]]
    for q in str(g("tour_confirm") or "").split("; "):
        if q and "dog weight" in q:
            qs.append(q + (" (the page says small dogs and gives no number)" if g("dog_size_note") else " (the page says weight restrictions apply and gives no number)"))
        elif q:
            qs.append(q)
    if g("rent_needs_call") == "yes":
        qs.append("Is the advertised rent the full monthly rent, or the average after free months? What is the first full payment and when is it due?")
    for line in str(g("all_in_unknown_lines") or "").split("; "):
        if line:
            qs.append({"parking fee": "What does a parking spot cost per month, and is one guaranteed in the lease?", "pet rent": "What is the monthly pet rent and any one-time pet fee?",
                       "building fees": "What required monthly fees are added to the rent (amenity, trash, technology)?",
                       "building fees (part)": "Which required monthly fees have no published amount (for example an amenity fee), and how much are they?", "gas": "Who pays for heat and cooking gas?"}.get(line, f"What is the {line}?"))
    if "pet rent" in str(g("all_in_estimated_lines") or ""):
        qs.append("What is the monthly pet rent and any one-time pet fee? (the figure in the cost is an estimate)")
    if "parking" in str(g("all_in_estimated_lines") or ""):
        qs.append("What does a parking spot cost per month? (the figure in the cost comes from a resident's review)")
    # independent check 5, N26: while "are dogs allowed" is itself the open item, the weight question is part of it, not a
    # second question that presumes a policy ('the page says small dogs') the open item says is unconfirmed
    dogs_open = bool(oi) and g("confirm_asterisk") == "yes" and oi[0] == "dogs allowed"
    if dogs_open and any("dog weight limit" in q for q in qs):
        qs = [q for q in qs if "dog weight limit" not in q]
        qs = [("Are dogs allowed, and up to what weight? Ask for the pet policy in writing." if q == oi[3] and q.startswith("Are dogs allowed?") else q) for q in qs]
    qs = dedupe_questions(qs)
    out = unit_core(r, g, qs)
    if dogs_open and (str(g("open_codes") or "").split(";")[0] == "dogs_not_named"):
        out["dog"]["size_note"] = None              # 'the page says small dogs' beside 'the listing does not name dogs' (142-38 37th Ave 8E)
    # independent check 4, D25: a property whose own title names the apartment ('416 Highland Ave - 312', one row labelled
    # '1 Bed') is apartment 312 at that address: the label is the number, and the title is not a building name
    tu = parsers.title_unit(g("building_name")) if parsers.is_plan_label(g("unit")) else ""
    if tu:
        out["unit"], out["building"], out["unit_label_basis"] = tu, None, "from the listing's title"
    out["disclosures"] = disc
    out["confirm"] = {"asterisk": g("confirm_asterisk") == "yes", "what": oi[0] if oi and g("confirm_asterisk") == "yes" else None,
                      "label": oi[1] if oi and g("confirm_asterisk") == "yes" else None, "why": oi[2] if oi and g("confirm_asterisk") == "yes" else None,
                      "question": (qs[0] if dogs_open and qs and qs[0].startswith("Are dogs allowed, and up to what weight") else oi[3]) if oi and g("confirm_asterisk") == "yes" else None, "code": (str(g("open_codes") or "").split(";")[0] or None) if oi else None,
                      "why_internal": oi[4] if oi else None, "reviewed": g("review_verdict")}
    am = out["amenities"]
    mr = moment_ratings(out["moments"], g("parking_rank"), out["parking"]["offsite"],
                        secured=bool(am["doorman"] or am["concierge"] or am["front_desk"]) or str(am["controlled_access"] or "").strip().lower().startswith(("yes", "true")),
                        overnight_restricted=any(d["what"] == "overnight street parking" for d in out["disclosures"]), sqft=g("sqft"), beds=g("beds"))
    for k, val in mr.items():
        out["moments"][k]["rating"] = val
    return out


def parking_block(g):
    kinds = [k for k in str(g("parking_kinds") or "").split("; ") if k]
    kind, inc = g("parking_kind") or None, g("parking_included_kind") or None
    opt = j(g("parking_optional"), [])
    basis = j(g("parking_kind_basis"), {})
    est = g("parking_fee_monthly_basis") == "resident_review"
    plain = kind in ("open_lot", "assigned_lot", "off_street", "assigned")
    return {"kinds": kinds, "kind": kind, "kind_words": parsers.PARKING_KIND_WORDS.get(kind) if kind else None,
            "included_kind": inc if g("parking_fee") == 0 else None, "included_words_internal": (g("parking_included_quote") or None) if g("parking_fee") == 0 else None,
            "included_basis": parsers.PARKING_BASIS_WORDS.get(g("parking_included_basis")) if g("parking_fee") == 0 else None,
            "optional_kinds": [{"kind": o.get("kind"), "kind_words": parsers.PARKING_KIND_WORDS.get(o.get("kind")), "fee": o.get("fee"), "fee_high": o.get("fee_high"),
                                "fee_basis": "published" if o.get("fee") is not None else None} for o in opt],
            "fee_kind": g("parking_fee_kind") or None, "assigned": g("parking_assigned") == "yes",
            "kinds_basis": {k: parsers.PARKING_BASIS_WORDS.get(b_, b_) for k, b_ in basis.items()} or None,
            "garage_is_optional_extra": bool(plain and any(o.get("kind") in ("garage", "covered", "gated_lot") for o in opt)),
            "summary": parsers.parking_summary(kind, inc, g("parking_fee"), opt, est) or None,
            "reviewed_note": g("parking_reviewed") or None}


def unit_core(r, g, qs):
    return {
        "id": g("listing_id"), "building_id": g("building_id"), "hood_id": g("hood_id"), "year": g("group_key"),
        "building": g("building_name"), "address": g("address"), "unit": g("unit"), "kind": g("listing_kind") or "unit", "beds": g("beds"), "sqft": g("sqft"),
        # owner, 2026-11-17: a floor-2 walk-up whose floor is read under the complex's numbering convention carries that floor
        **({"floor": g("unit_floor"), "floor_basis": g("unit_floor_basis")} if not (g("floor_elevator_code") == "floor_2" and g("unit_floor") is None and g("unit_floor_reading") is not None)
           else {"floor": g("unit_floor_reading"), "floor_basis": "inferred"}),
        "floor_basis_note": "read from the apartment number" if g("floor_basis_note") else None, "zip": g("zip5"), "lat": g("lat"), "lon": g("lon"),
        "available": g("available_date"), "listing_age_days": g("listing_age_days"),
        "rent": {"listed": g("listed_rent"), "basis": g("rent_basis"), "basis_kind": g("rent_basis_kind"), "gross": g("rent_gross"),
                 "asterisk": g("rent_asterisk") == "yes", "offer_text": g("rent_offer_text"), "offer_kind": g("rent_offer_kind"), "offer_type": g("rent_offer_type"), "free_months": g("rent_free_months"),
                 # independent check 4, D20: "up to 2 months free" is not "2 months free". free_text carries the qualifier.
                 "offer_up_to": g("rent_offer_up_to") == "yes", "offer_selected_apartments_only": g("rent_offer_select_units") == "yes", "free_text": _free_text(r) or None,
                 "lease_months": g("rent_lease_months"), "first_full_payment_date": g("rent_first_full_payment_date"),
                 "first_full_payment_note": g("rent_first_full_payment_note"), "needs_call": g("rent_needs_call") == "yes"},
        "all_in": g("all_in"), "all_in_gross": g("all_in_gross"), "all_in_lines": receipt_lines(j(r.get("all_in_lines"), [])),
        "all_in_unknown": [x for x in str(g("all_in_unknown_lines") or "").split("; ") if x],
        # owner, 2026-11-16: all_in plus the median known parking fee and required fees for the lines not published here.
        # Never used for the cap. unknown_cost_lines names the parking / fee lines that are not published.
        "all_in_likely": g("all_in_likely"), "all_in_likely_note": g("all_in_likely_note"),
        "unknown_cost_lines": [{"parking fee": "parking", "building fees": "required fees", "building fees (part)": "some required fees"}.get(x, x)
                               for x in str(g("all_in_unknown_lines") or "").split("; ") if x],
        "estimated_cost_lines": [x for x in str(g("all_in_estimated_lines") or "").split("; ") if x],
        "elevator": {"value": g("elevator"), "basis": g("elevator_basis"), "listing_site_only": g("elevator_aggregator_only") == "yes",
                     # owner, 2026-11-17: floor and elevator together (parsers.floor_elevator_rule). walkup_floor_2: settled on
                     # floor 2 with no elevator established; words: the plain line for the fact list and the compare row
                     "rule": g("floor_elevator_code") or None, "walkup_floor_2": g("floor_elevator_code") == "floor_2",
                     "words": parsers.walkup_words(g("floor_elevator_code"), g("elevator"))},
        "dog": {"allowed": g("dogs_allowed"), "basis": g("dogs_allowed_basis"), "weight_limit_lb": g("dog_weight_limit_lb"), "size_note": g("dog_size_note"), "size_only_source": g("dog_size_only"), "policy_text": g("dog_policy_text"), "pet_rent": g("pet_rent")},
        "parking": {"type": g("parking_type"), "rank": g("parking_rank"), "fee": g("parking_fee"), "fee_note": g("parking_fee_note"), "options_text": g("parking_options"),
                    # independent check 4, D18: where the fee comes from (the building's page or a listing, or a resident's
                    # review: then it is an estimate), and every kind of parking the sentence names: "surface parking;
                    # optional garages" is a lot with an optional garage, not "garage parking"
                    "fee_basis": ("estimate from a resident's review" if g("parking_fee_monthly_basis") == "resident_review" else ("published" if g("parking_fee") is not None else None)),
                    # independent check 5, N1 / D18: structured parking from every source's words (parsers.parking_facts).
                    # kind: the space she would actually park in (a free open lot is 'open_lot' whatever garage is also
                    # offered); kinds: every kind a source names (garage, gated_lot, covered, assigned_lot, open_lot,
                    # off_street, assigned, offsite, street); included_kind: which kind the free space is; optional_kinds:
                    # the other kinds offered for a fee ({kind, fee, fee_high}; fee null = not published); fee_kind: the
                    # kind `fee` pays for; summary: one sentence to use as it stands.
                    **parking_block(g),
                    # D10: parking that is not at the building ("2 blocks away") is never "covered parking" on the page
                    "offsite": bool(parsers.OFFSITE_PARKING.search(str(g("parking_type") or "")))},
        # independent check 4, D9: doorman and concierge are separate, each only from a source that says so; front_desk is
        # an attended lobby or desk that is called neither. doorman_text is the internal source sentence.
        "amenities": {"pool": g("pool") or None, "pool_text": g("pool_text"), "doorman": g("doorman") or None, "concierge": g("concierge") or None, "front_desk": g("front_desk") or None,
                      "doorman_text": g("doorman_text"), "controlled_access": g("controlled_access"),
                      "gym": g("gym"), "in_unit_laundry": g("in_unit_laundry"), "laundry": g("laundry"), "package_room": g("package_room"),
                      # independent check 5, N6: where in-unit laundry comes from. 'listing_site_appliance_list' = only a listing
                      # site's appliance list names the machines, which does not say they are in the apartment (the unit then
                      # carries the "washer and dryer to confirm" disclosure); 'page_says_in_apartment' = a page's own words.
                      # in_unit_appliances: 'washer and dryer', or 'washer' / 'dryer' when only one is named.
                      "in_unit_laundry_basis": ({"appliance_list": "listing_site_appliance_list", "says_in_apartment": "page_says_in_apartment"}.get(g("in_unit_laundry_source_kind"))
                                                if g("in_unit_laundry") == "yes" else None),
                      "in_unit_appliances": (g("in_unit_appliances") or None) if g("in_unit_laundry") == "yes" else None,
                      "outdoor_space": g("outdoor_space"), "lounge_or_coworking": g("lounge_or_coworking"), "dog_amenities": g("dog_amenities"),
                      # 2026-11-16: laundry and dog amenities as structured facts, each from every source's own words
                      # (parsers.laundry_facts, parsers.dog_amenity_facts). in_unit_laundry is 'yes' only where a source says
                      # the washer / dryer is IN the apartment ('on_site_only' and 'select_apartments' are not yes); hookups
                      # and a shared laundry room are their own flags; `laundry` is a plain label that agrees with them.
                      # dog_park_or_run: a dog park, dog run, bark park or fenced dog area ON the property. A pet spa or
                      # dog wash is pet_spa_or_wash. dog_amenity_unspecified: a source says "yes" and none says what.
                      # `dog_amenities` stays as the label 'dog run; dog park; pet spa; dog wash' (or 'yes' when unspecified).
                      "washer_dryer_hookups": g("washer_dryer_hookups") == "yes", "on_site_laundry": g("on_site_laundry") == "yes",
                      "dog_park_or_run": g("dog_park_or_run") == "yes", "pet_spa_or_wash": g("pet_spa_or_wash") == "yes",
                      "dog_amenity_unspecified": g("dog_amenity_unspecified") == "yes",
                      "year_built": g("year_built"), "building_floors": g("building_floors"),
                      # D19: 'at_least' = no page gives the whole building's height; this is the highest floor a page states for an apartment here
                      "building_floors_at_least": g("building_floors_basis") == "at_least",
                      # manager_name is the name alone; `manager` is the internal note that says where it was read
                      "manager": g("manager"), "manager_name": parsers.manager_name(g("manager")) or None},
        "moments": {
            "wake": {"park": g("park_name"), "park_walk_min": g("park_walk_min"), "dog_park": g("dog_park_name"), "dog_park_m": g("dog_park_m"), "woods_ha_800m": g("woods_ha_within_800m")},
            "work": {"sqft": g("sqft"), "separate_bedroom": (g("beds") or 0) >= 1, "cafes_800m": g("cafes_800m"), "gyms_800m": g("gym_count_800m"), "supermarket": g("supermarket"),
                     "supermarket_m": g("supermarket_m"), "library_1600m": g("library_count_1600m"), "motorway_m": g("motorway_m"), "fiber": None},
            "after": {"restaurants_800m": g("restaurants_800m"), "bars_800m": g("bars_800m"), "cafes_800m": g("cafes_800m"), "cinema_theatre_1600m": g("cinema_theatre_count_1600m"),
                      "bookshops_1600m": g("bookshop_count_1600m"), "markets_1600m": g("market_count_1600m"), "shops_800m": g("shop_any_count_800m")},
            "night": {"parking_type": g("parking_type"), "doorman": g("doorman"), "concierge": g("concierge"), "front_desk": g("front_desk"), "controlled_access": g("controlled_access"),
                      "violent_per_1000": g("violent"), "violent_vs_jamaica": g("violent_vs_jamaica"), "near_violent_250m_24m": g("near_violent_250m_24m"),
                      "near_violent_evening_250m_24m": g("near_violent_evening_250m_24m"), "car_crime_250m_24m": (g("near_veh_theft_24m") or 0) + (g("near_theft_from_veh_24m") or 0) if g("near_veh_theft_24m") is not None else None,
                      "vehicle_theft_per_1000": g("motor_vehicle_theft"), "police": g("police_agency"), "police_geography": g("police_geography")},
            "sat": {"bars_1600m": g("bars_1600m"), "music_1600m": g("music_1600m"), "restaurants_1600m": g("restaurants_1600m"), "parking_type": g("parking_type"), "train_station": g("train_station"), "train_station_m": g("train_station_m"),
                    # independent check 5, N3: train_station is the nearest rail station of ANY kind; train_station_kind is the
                    # word for it ('train' = commuter rail, 'subway', 'PATH', 'light rail') and train_station_system its
                    # operator. commuter_station is the nearest commuter-rail station (the same station when kind is 'train').
                    "train_station_kind": g("train_station_kind"), "train_station_system": g("train_station_system"),
                    "commuter_station": g("commuter_station"), "commuter_station_m": g("commuter_station_m"), "commuter_station_system": g("commuter_station_system")},
            "sun": {"drive_min": g("drive_min_to"), "drive_miles": g("drive_miles"), "drive_basis": "free-flow estimate, no traffic",
                    # null when a crossing on the route has no rate (never 0 for unknown); NY E-ZPass, with the mail rate beside it
                    "toll_round_trip": parsers.toll_known(g("toll_rt_ezpass"), g("toll_complete")),
                    "toll_round_trip_mail": parsers.toll_known(g("toll_rt_mail"), g("toll_complete")), "toll_basis": "New York E-ZPass, weekend off-peak",
                    # where one crossing has no published mail rate the mail figure is null: the sum of the known crossings is a floor
                    "toll_round_trip_mail_at_least": g("toll_rt_mail_subtotal") if g("toll_rt_mail") is None else None, "toll_mail_note": g("toll_rt_mail_note"),
                    "toll_complete": str(g("toll_complete")) == "True", "toll_items": g("toll_items"), "transit_min": g("transit_sat_median"), "transit_transfers": g("transit_sat_transfers"),
                    "transit_summary": g("transit_sat_summary"), "last_train_home_sat": g("transit_last_sat_departure_from_jamaica"), "sunday_return_min": g("transit_sun_return_median")}},
        "scores": {"rank": g("rank_score"), "universal": g("universal"), "promise": g("promise"), "pool_bump": g("pool_bump"), "hood_rank": g("shown_rank") or g("hood_rank"),
                   "parts": {k: g("p_" + k) for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily"]},
                   "in_year": {k: g(k + "_in_year") for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily", "rank_score"]},
                   "overall": {k: g(k + "_overall") for k in ["safety", "building", "cost", "car", "space", "distance", "dog", "daily", "rank_score"]}},
        "vs_queens": {k[4:]: g(k) for k in r.index if k.startswith("vsq_") and not k.endswith("_diff")},
        "vs_queens_diff": {k[4:-5]: g(k) for k in r.index if k.startswith("vsq_") and k.endswith("_diff")},
        "evidence": {"checked": bool(r.get("evidence_checked")), "avoid": g("ev_avoid") == "yes", "avoid_reasons": g("ev_reasons"), "pause_notes": g("ev_pause_notes"),
                     "items": evidence_items(j(r.get("ev_evidence_json"), [])), "positive": j(r.get("ev_positive_json"), []),
                     # the same two notes as plain sentences (independent check 4, D24): print these, not the strings above
                     "avoid_points": evidence_points(g("ev_reasons")), "pause_points": evidence_points(g("ev_pause_notes")),
                     # display field for the page: "NYC records", "rating screen: <verdict>", "none readable", or null when the building was not in the evidence pass
                     "public_evidence": PUBLIC_EVIDENCE.get(g("building_id"))},
        "confirm": None, "disclosures": [],          # written in unit(): reader text from structured fields
        # conditions from the evidence (independent check 4, D8); each is also among the disclosures
        "conditions": {"income_requirement": g("cond_income"), "credit_score_requirement": g("cond_credit"), "furnished": g("cond_furnished") == "yes"},
        # independent check 5, N4: one-time costs the listing states; never part of the monthly total. broker_fee is
        # 'applies', 'none' or null (the listing says nothing); one_time_costs is a ready phrase or null.
        "one_time": {"broker_fee": g("broker_fee") or None, "broker_fee_source": g("broker_fee_source") or None, "one_time_costs": g("one_time_costs") or None,
                     "in_monthly_total": False},
        "more_in_building": g("more_in_building"), "rank_in_building": g("nth_shown_in_building"),
        "cost_check": {"cap_margin": g("cap_margin"), "unknown_count": g("all_in_unknown_count"), "lease_term_months": g("rent_lease_term_months"), "price_12_month": g("rent_12_month_price")},
        "confidence": g("confidence"), "tour_questions": qs,
        "links": {"listing": g("url"), "building": g("building_url")}, "source_site": g("source_site"),
        "live": {"status": g("live_status"), "checked_at": g("live_checked_at")}, "price_seen_at": g("last_seen"),
    }


BUILDINGS = []


def buildings(shown):
    """One entry per building with a shown unit (owner, 2026-11-16: the page groups apartments under their building).
    unit_ids are in rank order (the same score as everywhere); rank_in_neighborhood orders buildings by their best unit.
    Shared facts are the building's merged facts (they are the same on every unit row); ratings stay on the units."""
    out = []
    for b, g in shown.sort_values(["hood_id", "shown_rank"]).groupby("building_id", sort=False):
        r0 = g.iloc[0]
        g0 = lambda c: v(r0.get(c))
        u0 = unit(r0)
        ex = pd.to_numeric(g.all_in, errors="coerce")
        likely = pd.to_numeric(g.all_in_likely, errors="coerce") if "all_in_likely" in g else ex
        # independent check 4, D17: `city` is the municipality the building stands in (Census geography at its point);
        # `postal_city` is the city the listing wrote (a mailing or market name), given only where it differs
        out.append({"id": b, "name": None if (parsers.title_unit(g0("building_name")) and parsers.is_plan_label(g0("unit"))) else g0("building_name"), "address": g0("address"), "city": g0("city"), "state": g0("state"), "zip": g0("zip5"),
                    "postal_city": g0("city_listed") if g0("city_listed") and not parsers.same_municipality(g0("city_listed"), g0("city"))
                    and not re.search(r"\d|\b(?:blvd|st|ave|rd|dr|street|avenue)\b", str(g0("city_listed")), re.I) else None,
                    "location_basis": g0("coord_basis"), "location_check": g0("coord_check"),
                    "hood_id": g0("hood_id"), "experience": g0("group_key"), "lat": g0("lat"), "lon": g0("lon"),
                    "unit_ids": list(g.listing_id), "n_units": int(len(g)), "more_showable_not_shown": int(g0("more_in_building") or 0),
                    "from_all_in": v(ex.min()), "to_all_in": v(ex.max()), "from_all_in_likely": v(likely.min()),
                    "best_unit_id": r0.listing_id, "best_rank_score": g0("rank_score"), "best_shown_rank": int(r0.shown_rank),
                    # some units of one building can differ in address (EDGE: two buildings leased together)
                    "addresses": sorted(set(str(a) for a in g.address.dropna())),
                    "elevator": u0["elevator"], "dogs": u0["dog"], "parking": u0["parking"], "amenities": u0["amenities"],
                    "links": {"building": g0("building_url")}, "manager": g0("manager"), "manager_name": parsers.manager_name(g0("manager")) or None,
                    "open_items": sorted(set(x for w in g.confirm_what.dropna().astype(str) for x in w.split("; ") if x and x != "nan")),
                    "units_with_asterisk": int((g.confirm_asterisk == "yes").sum())})
    by_h = {}
    for e in sorted(out, key=lambda e: (e["hood_id"], e["best_shown_rank"])):
        by_h[e["hood_id"]] = by_h.get(e["hood_id"], 0) + 1
        e["rank_in_neighborhood"] = by_h[e["hood_id"]]
    return out


def main():
    R = pd.read_csv(DATA / "ranked_units.csv", low_memory=False, dtype={"zip5": str})
    G = pd.read_csv(DATA / "lifestyle_groups.csv").set_index("hood_id")
    E = pd.read_csv(DATA / "group_exchange.csv")
    # same join as scripts/rank.py (address key -> building id, avoid rows first), carrying the one column rank.py leaves behind
    af, xwf = DATA / "avoid_buildings.csv", DATA / "reference" / "building_crosswalk.csv"
    if af.exists() and xwf.exists():
        AV = pd.read_csv(af, dtype=str, keep_default_na=False)
        if "public_evidence" in AV:
            AV["building_id"] = AV.addr_key.map(pd.read_csv(xwf, dtype=str).set_index("addr_key").building_id)
            AV = AV.dropna(subset=["building_id"]).sort_values("avoid", ascending=False).drop_duplicates("building_id")
            PUBLIC_EVIDENCE.update({b: (e or None) for b, e in zip(AV.building_id, AV.public_evidence)})
    held_ids = set(pd.read_csv(DATA / "needs_confirmation.csv").listing_id) if (DATA / "needs_confirmation.csv").exists() else set()
    shown, avoid, held = R[R.shown], R[R.avoid_card], R[R.listing_id.isin(held_ids) & ~R.shown]
    # Owner, 2026-11-16 ("Forget call check"): a listing never re-read is not an open item, so there is no "awaiting a live
    # check" list any more. The key stays in the page data as an EMPTY array (and the count as 0) so the page does not break.
    awaiting = R.iloc[0:0]
    # local rules (street parking, dogs) and resident voices, keyed by neighborhood
    local, voices, survey = {}, {}, {}
    lr = DATA / "reference" / "local_rules.csv"
    if lr.exists():
        LR = pd.read_csv(lr, dtype=str, keep_default_na=False)
        for r in LR[LR.value_type == "found"].itertuples():
            for hid0 in [h.strip() for h in r.applies_to_hood_ids.split(";") if h.strip()]:
                for hid, about in ROUTE(hid0):         # a city's law applies in each of its neighborhoods; it says so
                    local.setdefault(hid, {"street_parking": [], "dogs": []}).setdefault(r.topic, []).append(
                        {"rule": r.rule, "summary": r.summary, "quote": r.quote, "url": r.source_url, "municipality": r.municipality, "about": about})
    vq = DATA / "voices" / "neighborhood_quotes.csv"
    if vq.exists():
        VQ = pd.read_csv(vq, dtype=str, keep_default_na=False)
        if "verified" in VQ:
            VQ = VQ[VQ.verified.str.lower().isin(["true", "yes", "1"])]
        # independent check 2, D20: quotes dropped by decision (wrong municipality; a writer named by office)
        qx = DATA / "voices" / "quote_exclusions.csv"
        QX = [(r.hood_id, r.excerpt_starts_with) for r in pd.read_csv(qx, dtype=str, keep_default_na=False).itertuples()] if qx.exists() else []

        def area_key(t):
            t = re.sub(r",\s*[A-Z]{2}$", "", str(t).strip())
            return re.sub(r"\b(township|city of|city|town|village|borough)\b|\(.*?\)|[^a-z]", "", t.lower())
        for r in VQ.itertuples():
            if any(r.hood_id == h and r.excerpt.startswith(x) for h, x in QX) or parsers.characterises_residents_by_group(r.excerpt):
                continue                              # D24: also any quote that characterises residents by ethnicity, race or religion
            # D20: keep source_area. A quote about a wider or different area than the neighborhood it is filed under
            # says so ("about Corona" under North Corona). Thread titles used as an area name are not shown.
            sa = getattr(r, "source_area", "")
            about = re.sub(r",\s*[A-Z]{2}$", "", sa) if sa and len(sa) <= 40 and area_key(sa) != area_key(r.neighborhood) else None
            for hid, whole in ROUTE(r.hood_id, sa):    # a citywide quote is shown on each neighborhood of a split city, labelled
                voices.setdefault(hid, []).append({"excerpt": r.excerpt, "theme": r.theme, "sentiment": r.sentiment, "context": r.speaker_context,
                                                   "source": r.source_site, "date": r.post_date, "url": r.permalink, "source_area": sa or None, "about": whole or about})
    vs = DATA / "voices" / "neighborhood_survey.csv"
    if vs.exists():
        for r in pd.read_csv(vs, dtype=str, keep_default_na=False).itertuples():
            for hid, whole in ROUTE(r.hood_id, getattr(r, "source_area", "")):   # "Journal Square, Jersey City" rows go to Journal Square only
                survey.setdefault(hid, []).append({"measure": r.measure, "value": r.value, "source": r.source_site, "as_of": r.as_of, "url": r.source_url,
                                                   "source_area": getattr(r, "source_area", "") or None, "about": whole})
    # sub-city crime context for a split city: a labelled estimate, shown beside the citywide police rate, never used by the safety rule
    sub_crime = {}
    scf = DATA / "reference" / "subcity_crime_jersey_city.csv"
    if scf.exists():
        for r in pd.read_csv(scf).itertuples():
            sub_crime[r.hood_id] = {"label": "10-month estimate from the city's incident portal, not an official rate", "value_type": "estimate", "used_for_safety_rule": False,
                                    "violent_per_1000_scaled": v(r.violent_per_1000_scaled_to_fbi_2025), "property_per_1000_scaled": v(r.property_per_1000_scaled_to_fbi_2025),
                                    "violent_ratio_to_city": v(r.violent_ratio_to_city_portal), "property_ratio_to_city": v(r.property_ratio_to_city_portal),
                                    "window": r.window, "method": re.sub(r";?\s*see data/\S+$", "", str(r.method)), "source_url": r.source_url}
    MEAS = [("all_in", "all_in"), ("sqft", "sqft"), ("drive_min", "drive_min_to"), ("transit_min", "transit_sat_median"), ("toll_round_trip", "toll_rt_known"),
            ("toll_round_trip_mail", "toll_rt_mail"), ("violent_per_1000", "violent"), ("property_per_1000", "property"), ("restaurants_800m", "restaurants_800m"),
            ("park_walk_min", "park_walk_min"), ("parking_rank", "parking_rank")]
    HOME = shown[shown.hood_area.astype(str).eq("Queens")]
    BUILDINGS.clear()
    BUILDINGS.extend(buildings(shown))
    hoods = []
    for hid, g in R.groupby("hood_id"):
        s = g[g.shown]
        if not len(s) and not len(g[g.avoid_card]):
            continue
        if not len(s) and "thin_neighborhood" in g and g.thin_neighborhood.astype(str).eq("True").any():
            continue            # owner, 2026-11-16: a neighborhood cut by the thin-neighborhood rule does not appear on the page
        h = G.loc[hid] if hid in G.index else {}
        # independent check 3, D12: figures describe the SHOWN places (a neighborhood with only avoid cards uses its ranked units)
        g_all, g = g, (s if len(s) else g)
        num = lambda c: v(pd.to_numeric(g[c], errors="coerce").median()) if c in g else None
        # null unless every route in the neighborhood has a complete toll (never 0 for unknown)
        tollmed = lambda c: v(pd.Series([parsers.toll_known(a, b) for a, b in zip(g[c], g.toll_complete)], dtype=float).median()) \
            if c in g and g.toll_complete.astype(str).str.lower().eq("true").all() else None
        bl = [b_ for b_ in BUILDINGS if b_["hood_id"] == hid]
        hoods.append({"id": hid, "name": g.hood.iloc[0], "area": v(g.hood_area.iloc[0]), "state": v(g.state.iloc[0]) if "state" in g else None, "year": g.group_key.iloc[0],
                      "lat": v(pd.to_numeric(g.lat, errors="coerce").mean()), "lon": v(pd.to_numeric(g.lon, errors="coerce").mean()),
                      "counts": {"shown": int(len(s)), "buildings": len(bl), "avoid": int(g_all.avoid_card.sum()), "held": int((g_all.listing_id.isin(held_ids) & ~g_all.shown).sum()), "ranked": int(len(g_all))},
                      "figures_over": "shown places" if len(s) else "ranked apartments (nothing is shown here)",
                      "building_ids": [b_["id"] for b_ in sorted(bl, key=lambda b_: b_["rank_in_neighborhood"])],
                      "all_in_range": [v(s.all_in.min()), v(s.all_in.max())] if len(s) else None, "sqft_median": num("sqft"),
                      "drive_min": num("drive_min_to"), "transit_min": num("transit_sat_median"),
                      "toll_round_trip": tollmed("toll_rt_ezpass"),
                      # independent check 5, N9: tolls are per building (Newark: $24 at most buildings, $33 and $43 at two); the
                      # median stays, and the lowest and highest round trip among the shown apartments go with it
                      "toll_round_trip_range": toll_range(g, "toll_rt_ezpass"), "toll_round_trip_mail_range": toll_range(g, "toll_rt_mail"),
                      "toll_round_trip_mail": tollmed("toll_rt_mail") if "toll_rt_mail" in g and pd.to_numeric(g.toll_rt_mail, errors="coerce").notna().all() else None,
                      "toll_round_trip_mail_at_least": (v(pd.to_numeric(g.toll_rt_mail_subtotal, errors="coerce").median()) if "toll_rt_mail_subtotal" in g and not pd.to_numeric(g.toll_rt_mail, errors="coerce").notna().all() else None), "toll_basis": "New York E-ZPass, weekend off-peak",
                      "toll_complete": bool(g.toll_complete.astype(str).str.lower().eq("true").all()),
                      # independent check 4, D10: the owner's safety rule ("no crime higher than Jamaica") can only be
                      # established where both rates are published. Where one is missing the neighborhood is kept, but it
                      # says so: status 'not_published', with the reason, for "See how we got this". Never a guess.
                      "safety": {"status": safety_status(h)[0], "status_note": safety_status(h)[1],
                                 "violent_per_1000": v(h.get("violent")), "property_per_1000": v(h.get("property")), "vehicle_theft_per_1000": v(h.get("motor_vehicle_theft")),
                                 "vs_jamaica": v(h.get("violent_vs_jamaica")), "property_vs_jamaica": v(h.get("property_vs_jamaica")), "vs_us": v(h.get("violent_vs_us")),
                                 "vs_metro": v(h.get("violent_vs_metro")), "vs_local": v(h.get("violent_vs_local")), "police": v(h.get("police")), "geography": v(h.get("geography")), "year": v(h.get("crime_year")),
                                 # inside a split city every neighborhood carries the same citywide police rate: say so, and give the estimate as context
                                 "basis": (f"citywide police rate for {PARENTS[hid]['parent_name']}: the same figure for every {PARENTS[hid]['parent_name']} neighborhood, not a rate for {PARENTS[hid]['name']}" if hid in PARENTS else None),
                                 "subcity_estimate": sub_crime.get(hid) if hid in PARENTS else None},
                      "parent_id": PARENTS[hid]["parent_id"] if hid in PARENTS else None, "parent_name": PARENTS[hid]["parent_name"] if hid in PARENTS else None,
                      "short_name": PARENTS[hid]["name"] if hid in PARENTS else None,
                      # independent check 4, D16 / D6: the same measures over the BUILDINGS shown here (the median
                      # building, one vote per building: see shown_figures; the `traits` below describe the wider area
                      # profile the experiences were fitted on), and how many of the shown buildings have a dog park or
                      # dog run of their own
                      "shown_figures": shown_figures(s, bl) if len(s) else None,
                      "traits": {k: v(h.get(k)) for k in ["no_car_share", "age_25_34_share", "living_alone_share", "households_with_kids_share", "college_degree_share", "newcomer_share",
                                                          "wfh_share", "median_hh_income", "detached_house_share", "built_since_2010_share", "built_before_1940_share", "restaurants_800m",
                                                          "bars_800m", "cafes_800m", "park_ha_800m", "park_walk_min", "open_water_m", "dog_park_m", "supermarket_m_c"]},
                      "vs_queens": {k[4:]: v(pd.to_numeric(g[k], errors="coerce").median()) for k in g.columns if k.startswith("vsq_") and not k.endswith("_diff")},
                      "unit_ids": list(s.sort_values("shown_rank").listing_id), "avoid_ids": list(g_all[g_all.avoid_card].listing_id),
                      "local": {"parking_rules": local.get(hid, {}).get("street_parking") or None, "dog_rules": local.get(hid, {}).get("dogs") or None,
                                "voices": voices.get(hid, []), "survey": survey.get(hid, [])}})
    # independent check 4, D21: only neighborhoods with at least one apartment to show are neighborhoods of the page.
    # A place that has only an avoid card goes to neighborhoods_avoid_only: the page can list the card there, and must
    # not count the place among the neighborhoods, on the map chips or anywhere else.
    avoid_only = [h for h in hoods if not h["counts"]["shown"]]
    hoods = [h for h in hoods if h["counts"]["shown"]]
    years = []
    for key, g in R.groupby("group_key"):
        s = g[g.shown]
        # independent check 3, D12: every experience figure is computed over the SHOWN units of the experience (it used
        # to come from data/group_exchange.csv, over all ranked units, more than half of them not on the page), and the
        # median and the range now describe the same set. Queens baseline: the shown units in Queens.
        col_of = dict(MEAS)
        sv = lambda k: pd.to_numeric(s[col_of[k]], errors="coerce").dropna()
        hv = lambda k: pd.to_numeric(HOME[col_of[k]], errors="coerce").dropna()
        med = {k: (v(round(float(sv(k).median()), 1)) if len(sv(k)) else None) for k in col_of}
        rng = {k: ([v(round(float(sv(k).min()), 1)), v(round(float(sv(k).max()), 1))] if len(sv(k)) else None) for k in col_of}
        dh = s.groupby("hood_id").drive_min_to.median().dropna() if len(s) else pd.Series(dtype=float)
        ends = None
        if len(dh):
            near, far = dh.idxmin(), dh.idxmax()
            ends = {"nearest": {"hood_id": near, "name": s[s.hood_id == near].hood.iloc[0], "drive_min": v(round(float(dh[near]), 1))},
                    "farthest": {"hood_id": far, "name": s[s.hood_id == far].hood.iloc[0], "drive_min": v(round(float(dh[far]), 1))}}
        years.append({"id": key, "label": g.group_label.iloc[0], "subhead": g.group_subhead.iloc[0],
                      "counts": {"neighborhoods": int(s.hood_id.nunique()), "buildings": int(s.building_id.nunique()), "shown": int(len(s)), "avoid": int(g.avoid_card.sum())},
                      "figures_over": "shown places",
                      "all_in_range": [v(s.all_in.min()), v(s.all_in.max())] if len(s) else None,
                      "drive_min_range": [v(s.drive_min_to.min()), v(s.drive_min_to.max())] if len(s) else None,
                      "drive_min_range_hoods": ends,
                      "medians": med, "ranges": rng,
                      "vs_queens": {k[4:]: v(pd.to_numeric(s[k], errors="coerce").median()) for k in s.columns if k.startswith("vsq_") and not k.endswith("_diff")} if len(s) else {},
                      "vs_queens_diff": {k: (v(round(float(sv(k).median() - hv(k).median()), 1)) if len(sv(k)) and len(hv(k)) else None) for k in col_of},
                      "hood_ids": [h["id"] for h in sorted([h for h in hoods if h["year"] == key and h["counts"]["shown"]], key=lambda h: h["drive_min"] or 999)],
                      "catch": None, "scenes": None})
    spec = pd.read_csv(DATA / "reference" / "queens_spectrum_definition.csv").to_dict("records")
    out = {"meta": {"built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "cap_all_in": 3000, "move_in_window": "now to 2026-12-15",
                    "anchor": {"name": "Mom and Dad (Jamaica station)", "lat": 40.699608, "lon": -73.808530},
                    "jamaica_yardstick": {"violent_per_1000": v(G.jamaica_violent.iloc[0]), "property_per_1000": v(G.jamaica_property.iloc[0])},
                    "queens_spectrum": spec, "weights": {"safety": 22, "building": 16, "cost": 12, "car": 12, "space": 12, "distance": 10, "dog": 8, "daily": 8},
                    "counts": {"shown": int(len(shown)), "shown_with_asterisk": int((shown.confirm_asterisk == "yes").sum()), "avoid": int(len(avoid)), "held": int(len(held)),
                               "awaiting_live_check": int(len(awaiting)), "ranked": int(len(R)), "buildings": len(BUILDINGS),
                               "neighborhoods": len(hoods), "neighborhoods_avoid_only": len(avoid_only),
                               "neighborhoods_safety_not_published": sum(1 for h in hoods if h["safety"]["status"] != "published")},
                    "toll_basis": {"assumes": "New York E-ZPass", "rate_time": "weekend off-peak", "mail_rate_field": "toll_round_trip_mail", "note": parsers.TOLL_NOTE},
                    "notes": META_NOTES,
                    "moment_thresholds": MOMENT_THRESHOLDS, "max_units_per_building": 8},
           "years": years, "neighborhoods": hoods, "neighborhoods_avoid_only": avoid_only, "buildings": BUILDINGS, "units": [unit(r) for _, r in shown.iterrows()],
           "avoid": [unit(r) for _, r in avoid.iterrows()], "held": [unit(r) for _, r in held.iterrows()],
           "awaiting_live_check": [{"id": r.listing_id, "building": v(r.building_name), "address": v(r.address), "unit": v(r.unit), "hood_id": r.hood_id, "year": v(r.group_key), "price_seen_at": v(r.last_seen),
                                    "rank": v(r.rank_score), "all_in": v(r.all_in), "listing": v(r.url)} for r in awaiting.itertuples()]}
    (ROOT / "site").mkdir(exist_ok=True)
    (ROOT / "site" / "data.json").write_text(json.dumps(out, default=str, allow_nan=False))
    print(f"site/data.json: {len(out['years'])} years, {len(hoods)} neighborhoods, {len(out['units'])} shown, {len(out['avoid'])} avoid, {len(out['held'])} held; {(ROOT / 'site' / 'data.json').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
