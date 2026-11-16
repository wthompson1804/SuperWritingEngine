"""Text parsers shared by gates.py, build_master.py, all_in.py, avoid.py and rank.py.

Written after docs/INDEPENDENT_CHECK.md (W1-W20). Every function here is pure (text in, value out) and is covered by
scripts/test_parsers.py. The common rule: read a figure by what the sentence means, not by "the first number"; when
the sentence is ambiguous, return None (unknown) and let the caller keep the text for display.
"""
from __future__ import annotations

import json
import math
import re

AMT = r"\$\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?"
BLANKS = {"", "nan", "none", "unknown", "no_mention", "?", "not_found", "unconfirmed", "n/a", "see quote"}


def _f(whole, frac=None):
    return float(whole.replace(",", "") + (frac or ""))


def is_blank(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip().lower() in BLANKS


def money(text):
    """First money figure in a text: '$1,500' -> 1500, '1500' -> 1500 (not 150), '97.55' -> 97.55."""
    m = re.search(r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?", str(text))
    return _f(m.group(1), m.group(2)) if m else None


def num_str(v) -> str:
    """'6.0' -> '6', '50.00' -> '50', anything non-numeric unchanged (lower-cased): for comparing sources."""
    s = str(v).strip().lower()
    try:
        x = float(s.replace(",", "").replace("$", ""))
        return str(int(x)) if abs(x - round(x)) < 1e-9 else f"{x:g}"
    except ValueError:
        return s


# ---------------------------------------------------------------------------------------------- unit labels, floors
GROUND_WORDS = {"g", "gr", "grd", "gf", "ground", "groundfloor", "lobby", "bsmt", "basement"}
_UNIT_PREFIX = re.compile(r"^(?:unit|apt\.?|apartment|suite|ste\.?|#)\s*", re.I)


def clean_unit(unit) -> str:
    u = str(unit or "").strip().lower()
    if u in ("nan", "none"):
        return ""
    prev = None
    while prev != u:
        prev, u = u, _UNIT_PREFIX.sub("", u).strip()
    return u


def unit_key(unit) -> str:
    """Join key for a unit label: 'Unit 2F' = '#2f' = '2F'."""
    return re.sub(r"[^a-z0-9]", "", clean_unit(unit))


_PLAN_LABEL = re.compile(r"\bbeds?\b|\bbaths?\b|\$|\bstudio\b|floor ?plan|^plan\b|\bbedroom", re.I)
# Apartment List names a floor plan by the unit LINES that share it: 'B, H, K, R - Small-1', 'C, J, L, P, S - Large-1',
# 'A - Renovated-1', 'G - Small-1' (independent check 3, D26). A list of lines, or one line, then ' - <plan name>-<n>'.
_PLAN_LINES = re.compile(r"^\s*[a-z0-9]{1,3}(?:\s*,\s*[a-z0-9]{1,3})+\s+-\s+\S|^\s*[a-z0-9]{1,3}\s+-\s+[a-z][a-z ]*-\d+\s*$", re.I)


def is_plan_label(unit) -> bool:
    """True when a unit label describes a floor plan instead of naming one apartment: '1 bed, 1 bath, $1675',
    '1 Bed - 1 Bath', '1 Bedroom Large', '907 (floor plan)', 'B, H, K, R - Small-1', 'A - Large-1'.
    'Lincoln House at Hamilton Park - 107' (a building name, then a unit) and '206-A' are units."""
    u = str(unit or "")
    return bool(_PLAN_LABEL.search(u) or _PLAN_LINES.search(u))


def unit_label_key(unit) -> str:
    """unit_key, but '' for a label that describes a floor plan instead of naming a unit (is_plan_label): such a row is
    not a named unit (independent check 2, D1, D17; check 3, D26)."""
    return "" if is_plan_label(unit) else unit_key(unit)


LISTING_KINDS = ("unit", "floor_plan", "building_offer", "private_room")
NOT_AN_APARTMENT_WHY = {
    "floor_plan": "a floor plan, not an apartment: the source gives a plan's price, with no unit number for one specific home",
    "building_offer": "a building page's price with no unit number: no specific apartment is named",
    "private_room": "a private room in a co-living suite (shared apartment), not an apartment of her own",
}
_COLIVING = re.compile(r"co-?living", re.I)
_TITLE_UNIT = re.compile(r"^\s*\d+[\w-]*\s+\S.*\s(?:-|#)\s*#?\d{1,4}[a-z]?\s*$", re.I)      # '<house number> <street> - <unit>'



def listing_kind(unit, detail_level="", listing_id="", listing_type="", building_name="") -> str:
    """What a listing row IS, from the source's structure first and the label's shape second (owner, 2026-11-16: "if
    there's anything that's not a real apartment and just a floor plan, it shouldn't be in any of this").
      'floor_plan'      a floor-plan row of a building page (detail_level building_floorplan, or ':plan-' in the id:
                        Trulia's plan rows carry no unit number), or a label that names a plan (is_plan_label)
      'building_offer'  a managed building's page price with no unit number at all (a "from $X" row; Zumper building
                        pages, a manager's "one-bedroom" row)
      'private_room'    a room of a shared suite in a co-living building ('448-3' = room 3 of suite 448)
      'unit'            a real apartment: its own identifier for one specific home ('5D', 'PH2', 'B9-309', '022-265',
                        'T526', 'Lincoln House at Hamilton Park - 107'), or a single-home listing page of its own
                        (one address, one price) whose page gives no unit number
    Only 'unit' rows are apartments. The others stay in the data with status not_an_apartment and are never ranked,
    shown, counted or put on a card (rank.py). A unit is never merged into a floor plan (build_master.py)."""
    dl = str(detail_level or "").strip().lower()
    if dl == "building_floorplan" or ":plan-" in str(listing_id or ""):
        return "floor_plan"
    if is_plan_label(unit):
        # One exception, from the source's structure: a property whose own title names the unit ('416 Highland Ave - 312',
        # an owner's single apartment on Apartment List) is that one home, although its only row is labelled '1 Bed'.
        return "unit" if _TITLE_UNIT.search(str(building_name or "")) else "floor_plan"
    if not unit_key(unit):
        return "building_offer" if dl == "building_page" or str(listing_type or "").strip().lower() == "managed_building" else "unit"
    if _COLIVING.search(str(building_name or "")) and re.fullmatch(r"\d{2,4}-\d", clean_unit(unit)):
        return "private_room"
    return "unit"


_ADDR_UNIT = re.compile(r"^(.*?[^\s,])\s*,?\s*(?:#\s*|\b(?:apt|apartment|unit|ste|suite)\b\.?\s*#?\s*)([a-z0-9][\w-]*)\s*((?:,.*)?)$", re.I)


def split_address_unit(address):
    """('1775 Windsor Road', '215') from '1775 Windsor Road #215'; ('20 Gill Lane', '1E') from '20 Gill Lane, Apt. 1E';
    ('138-28 Queens Boulevard, New York, NY 11435, USA', '5K') from '138-28 Queens Boulevard #5K, New York, NY 11435, USA'.
    An address with no unit part comes back unchanged with ''. The unit belongs in the unit field, not in the address:
    left in the address it hides the unit from the floor gate and from the duplicate check (Avalon Teaneck 215)."""
    a = str(address or "").strip()
    m = _ADDR_UNIT.match(a)
    if not m or re.fullmatch(r"[\d\s-]+", m.group(1)):    # a street must remain ('1 Apt Rd' is not split)
        return a, ""
    return (m.group(1).rstrip(" #,") + m.group(3)).strip(), m.group(2)


def sizes_agree(a, b, tol=0.03) -> bool:
    """Two published sizes describe the same apartment: equal, within 3 percent (716 and 702 sq ft for Avalon Teaneck
    215 on two sites), or one of them not published."""
    x, y = _num_or_none(a), _num_or_none(b)
    if x is None or y is None or x <= 0 or y <= 0:
        return True
    return abs(x - y) <= tol * max(x, y)


def _num_or_none(v):
    try:
        x = float(str(v).replace(",", ""))
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def rents_agree(a, b, tol=0.02) -> bool:
    x, y = _num_or_none(a), _num_or_none(b)
    return x is not None and y is not None and abs(x - y) <= tol * max(x, y)


def same_listed_unit(unit_a, beds_a, sqft_a, rent_a, unit_b, beds_b, sqft_b, rent_b) -> bool:
    """Two LABELLED unit rows of one building are the same apartment: the labels are equal, or one is the other with a
    building prefix ('215' and '001-215': units_match) AND bedrooms are equal, the rents agree within 2 percent and the
    sizes agree (sizes_agree). '001-215' and '002-215' are two apartments; a floor plan is never passed here."""
    ka, kb = unit_key(unit_a), unit_key(unit_b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    return units_match(unit_a, unit_b) and _beds(beds_a) == _beds(beds_b) and rents_agree(rent_a, rent_b) and sizes_agree(sqft_a, sqft_b)


def _beds(b):
    x = _num_or_none(b)
    return str(b).strip().lower() if x is None else x


def unit_tail(unit) -> str:
    """Last segment of a label with a separator, leading zeros dropped: '005-5106' -> '5106', '001-215' -> '215'."""
    segs = [s for s in re.split(r"[^a-z0-9]+", clean_unit(unit)) if s]
    return segs[-1].lstrip("0") if segs else ""


def units_match(a, b) -> bool:
    """Same unit under two spellings: equal keys, or one is the other's last segment ('5106' vs '005-5106')."""
    ka, kb = unit_key(a), unit_key(b)
    if not ka or not kb:
        return False
    if ka == kb or ka.lstrip("0") == kb.lstrip("0"):
        return True
    ta, tb = unit_tail(a), unit_tail(b)
    return bool(ta) and bool(tb) and ((ta == kb.lstrip("0") and ta != ka.lstrip("0")) or (tb == ka.lstrip("0") and tb != kb.lstrip("0")))


def _bf(building_floors):
    try:
        v = float(building_floors)
        return int(v) if v >= 1 and math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def floor_from_label(unit, building_floors=None):
    """Guess a floor from a unit label. Returns (floor or None, kind).

    kind 'simple'       1-2 digits + letters ('4F' -> 4, '12B' -> 12) or exactly three digits ('305' -> 3)
         'complex'      a label with a separator, a building prefix or four digits; a floor is returned only when the
                        building's floor count leaves exactly one possible reading ('7012' in 13 floors -> 7)
         'ground_word'  G, GR, LOBBY, BSMT -> floor 0
         ''             no reading
    The result is always an inference: callers must store it with basis 'inferred'. A reading above the building's
    floor count is rejected (None), never clamped.
    """
    raw = clean_unit(unit)
    if not raw:
        return None, ""
    key = re.sub(r"[^a-z0-9]", "", raw)
    if key in GROUND_WORDS:
        return 0, "ground_word"
    bf = _bf(building_floors)
    if raw == key:                                       # no separator
        m = re.fullmatch(r"(\d{1,2})[a-z]{1,3}", raw)
        f = int(m.group(1)) if m else (int(raw[0]) if re.fullmatch(r"\d{3}", raw) else None)
        if f is not None:
            if f == 0 or (bf is not None and f > bf):
                return None, "simple"
            return f, "simple"
    if bf is None:
        return None, "complex"
    segs = [s for s in re.split(r"[^a-z0-9]+", raw) if s]
    if not segs:
        return None, ""
    cands: set[int] = set()
    last = segs[-1]
    m = re.fullmatch(r"[a-z]{0,3}(\d+)([a-z]{0,3})", last)
    if not m:
        return None, "complex"
    d, suffix = m.group(1), m.group(2)
    lead_letters = last[0].isalpha()
    if len(d) <= 2:
        if lead_letters or not suffix and len(segs) == 1:  # 'h41', 'c4', 'b10', 'ph2', '48': line or building, not a floor
            return None, "complex"
        cands.add(int(d))                                # '158-2l' -> 2
    elif len(d) == 3:
        cands.add(int(d[0]))                             # 'h2-316' -> 3, 'a305' -> 3
    elif len(d) == 4:
        cands |= {int(d[:2]), int(d[0]), int(d[1])}      # floor AB / floor A / building A, floor B
    else:
        return None, "complex"
    if len(segs) > 1 and re.fullmatch(r"\d{1,2}", segs[0]):
        cands.add(int(segs[0]))                          # '15-06b': the first part may be the floor
    cands = {c for c in cands if 1 <= c <= bf}
    return (cands.pop(), "complex") if len(cands) == 1 else (None, "complex")


def parse_floor_confirm(value):
    """Read an evidence 'floor' value. Returns ([(unit label or '*', floor)], inferred: bool).

    Handles '3', '1 (ground floor)', '3 (from unit number 317)', 'unit 231: 2nd Floor', 'unit 1177: 1',
    '001-436: 4; 001-324: 3', '2206: floor 2; 2321: floor 3', 'units 1-219 and 1-234: floor 2', 'unit G02: Ground Floor',
    '5 for 5G, 6 for 6A'. 'unknown' parts yield nothing. Ground floor is floor 1.
    """
    v = str(value or "").strip()
    inferred = bool(re.search(r"inferred|derived|from (?:the )?unit numbers?|by unit numbering|implied|probably", v, re.I))
    out = []
    for part in re.split(r";", v):
        p = part.strip()
        if not p or re.search(r"\bunknown\b|does not (?:show|reveal)|could be|unconfirmed", p, re.I):
            continue
        fl = r"(?:floor\s*)?(\d{1,2}|ground)(?:st|nd|rd|th)?(?:\s*floor)?"
        m = re.match(r"(?:units?\s+)?((?:[\w-]+)(?:\s*(?:,|and|&)\s*[\w-]+)*)\s*[:=]\s*" + fl + r"\b", p, re.I)
        if m and not re.fullmatch(r"floor", m.group(1), re.I):
            f = 1 if m.group(2).lower() == "ground" else int(m.group(2))
            for lab in re.split(r"\s*(?:,|and|&)\s*", m.group(1)):
                if lab and lab.lower() not in ("unit", "units"):
                    out.append((lab, f))
            continue
        pairs = re.findall(r"(\d{1,2}) for ([\w-]+)", p)
        if pairs:
            out += [(lab, int(f)) for f, lab in pairs]
            continue
        m = re.match(r"(?:floor\s*)?(\d{1,2})\s*\((?:inferred |derived )?(?:from )?(?:the )?unit(?: number)?\s+([\w-]+)\s*(?:only)?\)", p, re.I)
        if m:
            out.append((m.group(2), int(m.group(1))))
            continue
        m = re.match(r"(?:floor\s*)?(\d{1,2})\b(?!\s*(?:floors|stories|-))", p, re.I)
        if m:
            out.append(("*", int(m.group(1))))
            continue
        if re.match(r"ground floor", p, re.I):
            out.append(("*", 1))
    return out, inferred


# ---------------------------------------------------------------------------------------------------------- dogs
def parse_dog_weight(text):
    """Returns (kind, pounds). kind: 'limit' (pounds set), 'no_limit', 'size_only' (a size word, no number), 'unknown'.

    'no upper limit stated; dogs over 40 lb cost extra' is no_limit, not a 40 lb limit. A bare 'extra charge over
    40 lb' is unknown (it shows larger dogs are accepted, not what the limit is).
    """
    t = str(text or "").strip().lower()
    if is_blank(t) or re.search(r"not applicable|n/a|dogs? not allowed|no pets|not accepted", t):
        return "unknown", None
    if re.search(r"\bno (?:upper |weight |size |stated |pet )*(?:limits?|restrictions?)\b|\bunlimited\b|\bany (?:size|weight)\b|regardless of (?:pet )?(?:size|weight)", t) \
            and not re.search(r"no (?:limit|number) (?:given|published)|limit exists", t):
        return "no_limit", None
    surcharge = re.search(r"(?:over|above|more than|exceeding)\s*(\d{2,3})\s*(?:lbs?|pounds?|#)?[^;.]*(?:extra|additional|surcharge|charge|fee|cost)|"
                          r"(?:extra|additional|surcharge)[^;.]*(?:over|above|more than)\s*(\d{2,3})", t)
    m = None
    if not surcharge:
        m = re.search(r"(\d{2,3})\s*(?:-\s*)?(?:lbs?\b|pounds?|#)", t) or re.fullmatch(r"(\d{2,3})(?:\.0+)?", t) \
            or re.search(r"(?:max(?:imum)?|limit|under|up to)\D{0,12}(\d{2,3})\b(?!\s*(?:pets|dogs|%))", t)
    if m:
        return "limit", float(m.group(1))
    if re.search(r"\bsmall\b", t) and not re.search(r"small (?:and|or|,|&) ?large|small, large|large dogs? (?:are )?allowed|and large", t):
        return "size_only", None
    return "unknown", None


def dog_size_only(policy_text) -> bool:
    """True when a pet policy names a size ('small dogs', 'Size allowed: Small') and gives no pound figure."""
    t = str(policy_text or "").lower()
    if not t:
        return False
    if re.search(r"weight limit[^|;]{0,14}\d|\d{2,3}\s*(?:lbs?\b|pounds?)", t):
        return False
    m = re.search(r"dogs?: allowed \(([^)]*)\)", t)
    if m:
        size = re.search(r"size allowed: ([^;)]*)", m.group(1))
        if size:
            return "small" in size.group(1) and "large" not in size.group(1)
    if re.search(r"size allowed: small(?!,? ?(?:and )?large)", t):
        return True
    if re.search(r"large dogs? (?:are )?(?:not (?:allowed|permitted)|prohibited)|small dogs? only|small dogs? allowed|only small dogs|small pets? only|\(small dogs\)|small dogs", t):
        return not re.search(r"small(?: dogs)?,? (?:and |or )?large dogs? allowed|small, large", t)
    return False


SMALL_DOG_NOTE = "page says small dogs; no weight number"


def building_fails_reason(notes):
    """Reason a harvester's 'BUILDING_FAILS: ...' note still excludes a unit, or '' when it does not.

    Owner's rule (2026-11-15): 'small dogs' with no pound figure passes the dog gate (her dog is at most 25 lb), so a
    flag that says only 'small dogs only' no longer excludes. Every other flag does: no dogs, a stated limit under
    25 lb, income- or age-restricted, no elevator, walk-up, nothing in budget.
    """
    t = str(notes or "").strip()
    if not t.startswith("BUILDING_FAILS"):
        return ""
    reason = re.sub(r"^BUILDING_FAILS:?\s*(?:fails:)?\s*", "", t)
    first = re.split(r";|\.\s", reason)[0].lower()
    small_only = re.search(r"small dogs?|small pets?", first) and not re.search(
        r"\bno dogs\b|\bno pets\b|(?<!large )dogs? (?:are )?not allowed|weight limit|\d+ ?lbs?\b|income|age-|senior|\b55\+|lottery|walk-?up|no elevator|nothing|cats only", first)
    return "" if small_only else reason[:110]


def dog_conflict(value):
    """Read a 'dogs_allowed' evidence row marked 'contradicts'. Returns 'no', 'yes' or 'conflicting'.

    A plain 'no' (or 'service or emotional-support dogs only') is no. Where sources disagree, the building's own
    site or its management feed wins over an aggregator; aggregator against aggregator is 'conflicting'.
    """
    t = str(value or "").strip().lower()
    own = r"building(?:'s)? (?:own )?site|own site|owner'?s? (?:site|description)|management|manager|bozzuto|property site|leasing|listing's description|unit listing"
    agg = r"zumper|trulia|apartment list|apartments\.com|zillow|openigloo|rent\.com"
    neg = r"\bno\b|not allowed|no pets|not permitted|not accepted"
    pos = r"\byes\b|allowed|pet[- ]friendly|dogs ok|welcome"
    clauses = [c.strip() for c in re.split(r";|\bbut\b|, (?=the |trulia|zumper|apartment)", t) if c.strip()]
    verdicts = []                                         # (source kind, polarity)
    for c in clauses:
        kind = "own" if re.search(own, c) else ("agg" if re.search(agg, c) else "")
        c2 = re.sub(r"\([^)]*\)", " ", c)                 # parentheticals explain, they do not vote
        if re.search(r"says (?:dogs? )?no|say no|no pets|not allowed|dogs? not|^no\b|\bno \(", c) or (re.search(neg, c2) and not re.search(pos, c2)):
            verdicts.append((kind, "no"))
        elif re.search(pos, c2):
            verdicts.append((kind, "yes"))
    pols = {p for _, p in verdicts}
    if pols == {"no"}:
        kinds = {k for k, _ in verdicts}
        # a single aggregator's 'no' against the listing that said yes is aggregator vs aggregator
        return "conflicting" if kinds == {"agg"} and re.search(r"\(|page for|copy of", t) and not re.search(r"service|emotional", t) else "no"
    if pols == {"yes"}:
        return "yes"
    ownv = {p for k, p in verdicts if k == "own"}
    if len(ownv) == 1:
        return ownv.pop()
    return "conflicting"


def parse_pet_rent(text, default_monthly=True):
    """Monthly pet rent for one dog. Returns (amount or None, note).

    'one-time $500 per pet; $50 per pet monthly' -> 50; '$350 one-time; pet rent $40 or $50' -> 40. One-time fees,
    deposits and yearly charges are never returned. default_monthly: how to read a bare '$65 per pet' (True for a
    field named pet rent, False for a field named pet fees).
    """
    t = str(text or "").strip()
    if is_blank(t):
        return None, ""
    tl = t.lower()
    m = re.fullmatch(r"\$?\s*(\d{1,3})(\.\d+)?", tl)
    if m:
        v = _f(m.group(1), m.group(2))
        return (v, "") if default_monthly and 0 < v <= 150 else (None, "")
    cands = []                                            # (amount, dog_specific)
    spans = [(mm.start(), mm.end(), _f(mm.group(1), mm.group(2))) for mm in re.finditer(AMT, tl)]
    for mm in re.finditer(r"([a-z][a-z /-]{1,24}):\s*(\d{1,4})(\.\d+)?(?![\d,]*\s*(?:lb|pets?|dogs?|%)|\d)", tl):   # 'pet rent: 50.00'
        if not any(s <= mm.start(2) <= e for s, e, _ in spans) and tl[mm.start(2) - 1] != "$":
            spans.append((mm.start(2), mm.end(), _f(mm.group(2), mm.group(3))))
    spans.sort()
    ONE = r"one[- ]?time|non-?refundable|deposit|at move|move-in|per year|a year|yearly|annual|/yr|per lease|\bfee\b(?! per month| monthly|/mo)"
    MON = r"/\s*mo\b|/\s*month|per month|a month|monthly|each month|\bmo\b|\brent\b"
    for i, (s, e, amt) in enumerate(spans):
        prev_e = spans[i - 1][1] if i else 0
        next_s = spans[i + 1][0] if i + 1 < len(spans) else len(tl)
        before = re.split(r"[;|]", tl[prev_e:s])[-1][-45:]
        after = re.split(r"[;|]", tl[e:next_s])[0][:40]
        clause = tl[max(tl.rfind(";", 0, s), tl.rfind("|", 0, s)) + 1:s] + after
        a_mon, a_one = re.search(MON, after), re.search(ONE, after)
        b_mon, b_one = re.search(MON + r"|\bpet:\s*$|\bdog:\s*$", before), re.search(ONE.replace(r"\bfee\b(?! per month| monthly|/mo)", r"\bfee\b") + r"|limit|max", before)
        if a_mon and (not a_one or a_mon.start() < a_one.start()):
            kind = "monthly"
        elif a_one:
            kind = "one"
        elif b_one and (not b_mon or b_one.start() > b_mon.start()):
            kind = "one"
        elif b_mon:
            kind = "monthly"
        else:
            kind = "monthly" if default_monthly else "one"
        if re.search(r"limit|max|number allowed", before[-14:]):
            continue
        if kind == "monthly" and 0 < amt <= 150:
            cat_only = "cat" in clause and "dog" not in clause and "pet" not in clause
            cands.append((amt, not cat_only))
    if not cands:
        return None, ""
    dogs = [a for a, d in cands if d] or [a for a, _ in cands]
    vals = sorted(set(dogs))
    note = "" if len(vals) == 1 else "text gives " + " or ".join(f"${v:g}" for v in vals) + "; the lowest (one pet) is used"
    return vals[0], note


# ------------------------------------------------------------------------------------------------------- parking
_CADENCE = r"^\s*(?:/\s*mo(?:nth)?\.?|/\s*car|/\s*space|per month|a month|monthly|per vehicle|per car|per space|per spot|\(plus tax\)|each|\s)+"
_SKIP_PARK = r"one[- ]time|deposit|per day|daily|hourly|\bguest|visitor|per year|annual|\bbike|bicycle|storage|\bev\b|motorcycle|tandem|charging"
_SECOND = r"additional[\w/ -]{0,30}?(?:parking|spots?|spaces?|cars?|vehicles?)\b|\bextra (?:spots?|spaces?|cars?|vehicles?)|\b2nd\b|\bsecond\b|\b3rd\b|\bthird\b|\beach add"
_OTHER_TOPIC = r"\bpets?\b|\bdogs?\b|\bcats?\b|water|sewer|trash|\bwst\b|amenity|application|\brent\b|internet|cable|insurance"
_FIRST = r"\b1st\b|\bfirst (?:space|spot|car|vehicle)|\(1 space\)|\(1 spot\)|\bone space\b"
_FREE = r"\bfree\b|\bincluded\b|no (?:extra |additional )?(?:charge|cost|fee)\b|complimentary|at no (?:cost|charge)|\bno fee\b"
_PROMO = r"first year|1st year|1 year|one year|for \d+ months?|\d+ months? free|year free|months? of free|limited time|move[- ]in special|current offer"
_NOUN = r"(?:parking|spots?|spaces?|lot|garage|cars?|vehicles?)"
_FREE_NEAR = (r"(?:\bfree\b|complimentary|\bincluded\b|no (?:extra |additional )?(?:charge|cost|fee))[^,;.]{0,25}\b" + _NOUN + r"\b|\b" + _NOUN
              + r"\b[^,;.]{0,45}(?:\bfree\b|\bincluded\b|no (?:extra |additional )?(?:charge|cost)|complimentary|at no (?:cost|charge))")


OFFSITE_PARKING = re.compile(r"\boff[- ]?site\b|\b(?:\d+|one|two|three|four|five|a few|several) blocks? away\b|\bnearby (?:public |municipal )?(?:garage|lot)\b", re.I)


def parking_kind(text) -> str:
    """'garage', 'covered', 'lot', 'street' or '' from a parking sentence (the words rank.py scores)."""
    t = str(text or "").lower()
    if OFFSITE_PARKING.search(t):
        # independent check 3, D10 (30 Broad Street): "Offsite parking ... 2 blocks away covered" is not covered parking at
        # the building. It is its own kind, scored like a lot (off the street, but not where she lives).
        return "offsite"
    if re.search(r"garage|gated|underground|indoor|\bdeck\b", t) and not re.search(r"no garage|garage_lot: fee", t):
        return "garage"
    if re.search(r"(?<!un)covered|carport", t):
        return "covered"
    if re.search(r"\blot\b|surface|off[- ]street|assigned|on[- ]site|outdoor|open parking|uncovered", t):
        return "lot"
    return "street" if "street" in t else ""


def _park_class(label: str) -> str:
    l = label.lower()
    if re.search(r"uncovered|surface|outdoor|outside|open lot|open parking|exterior", l):
        return "surface"
    if re.search(r"covered|garage|indoor|underground|carport|\bdeck\b|interior", l):
        return "covered"
    return "surface" if re.search(r"\blot\b", l) else "generic"


def parse_parking(text):
    """Read a parking sentence. Returns {'fee': float|None, 'note': str, 'options': str, 'included': bool}.

    fee is the monthly cost of the unit's first spot: 0 when a spot is free or included ('1 free surface spot ...
    additional $50' -> 0); the first-spot price when prices are per spot ('1st $100, 2nd $75' -> 100); otherwise the
    cheapest covered or garage option, or the cheapest of all when none is labelled covered. A range counts at its
    low end. Time-limited free parking, additional-spot prices and one-time charges never set the fee. 'options'
    lists every price found so the page can show the alternatives.
    """
    out = {"fee": None, "note": "", "options": "", "included": False}
    t = re.sub(r"[ \t\xa0]+", " ", str(text or "")).strip()
    if is_blank(t):
        return out
    t = re.sub(r"\bincluded\s*=\s*true\b", "included in rent", t, flags=re.I)
    t = re.sub(r"\b\w+\s*=\s*(?:true|false)\b", " ", t, flags=re.I)
    t = re.sub(r"\[[^\]]{0,60}\]", " ", t)                                 # '[parking comment]' tags
    # a bracket that says the amount is not on this page, or quotes another listing's price, never sets the fee
    # (independent check 2, D15: 2072 20th Ln took $200 from the 1483 Shore Pkwy listing)
    t = re.sub(r"\([^)]*(?:not stated here|amount not stated|another (?:listing|building)|other (?:listing|building)|same complex|different (?:listing|building))[^)]*\)",
               " ", t, flags=re.I)
    if re.fullmatch(r"\s*\$?\d+(?:\.\d+)?(?:\s*-\s*\$?\d+(?:\.\d+)?)?\s*", t):
        t = "parking: " + t
    t = re.sub(r"(:\s*)(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?)\s*(?=$|;|\(|,)", r"\1$\2 ", t)   # 'Parking - Garage: 185'
    opts, included, promo = [], [], False
    for clause in re.split(r";|\||\n|\.\s+(?=[A-Z])|(?<=\))\s*,\s*", t):
        c = clause.strip()
        if not c:
            continue
        cl = c.lower()
        amts = list(re.finditer(AMT + r"(?:\s*(?:-|–|to)\s*\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?)?", c))
        if re.search(_PROMO, cl) and re.search(r"free|waived", cl):
            promo = True
            continue
        if not amts:
            if re.search(_FREE_NEAR, cl) and not re.search(r"not included|fee not|no free|^special features", cl):
                included.append(c)
            continue
        consumed_until = 0
        for i, m in enumerate(amts):
            nxt = amts[i + 1].start() if i + 1 < len(amts) else len(c)
            before = c[consumed_until:m.start()]
            before = re.split(r",|\band\b|\bor\b", before)[-1] if i else before
            after_raw = c[m.end():nxt]
            after = re.sub(_CADENCE, "", after_raw, flags=re.I)
            lead = after.lstrip()
            if re.match(r"(?:for\b|\(|-|:)", lead, re.I) or i + 1 == len(amts) or not before.strip():
                took = re.split(r",|\band\b|\bor\b", lead)[0] if i + 1 < len(amts) else lead
                consumed_until = m.end() + (len(after_raw) - len(lead)) + len(took) if i + 1 < len(amts) else len(c)
            else:
                took = ""
                consumed_until = m.end() + (len(after_raw) - len(after))
            label = (before + " " + took).strip(" :,-.")
            ll = label.lower()
            lo = _f(m.group(1), m.group(2))
            hi = _f(m.group(3), m.group(4)) if m.group(3) else None
            if not (5 <= lo <= 1000):
                continue
            ctx = (cl if len(amts) == 1 else ll)
            if re.search(_SKIP_PARK, ctx) or (re.search(_OTHER_TOPIC, ll) and not re.search(r"park|garage|spot|space|\blot\b", ll)):
                continue
            role = "second" if re.search(_SECOND, ll if len(amts) > 1 else cl) and not re.search(_FIRST, ll) else ("first" if re.search(_FIRST, ll if len(amts) > 1 else cl) else "")
            opts.append({"amt": lo, "hi": hi, "label": re.sub(r"\s+", " ", label)[:60], "cls": _park_class(label if _park_class(label) != "generic" or len(amts) > 1 else c), "role": role})
        if re.search(_FREE_NEAR, cl[:amts[0].start()]) and not re.search(r"not included|fee not|no free", cl):
            # a clause that also carries prices: the part before the first price says what is free
            head = c[:amts[0].start()]
            if True:
                included.append(head.strip(" :,-."))
                for o in opts:
                    if o["label"] and o["label"] in head:
                        o["role"] = "second"
    if any(re.search(_SECOND, (o["label"] or "").lower()) for o in opts) and included:
        for o in opts:
            if not o["role"]:
                o["role"] = "second"

    def show(o):
        rng = f"${o['amt']:g}" + (f"-${o['hi']:g}" if o["hi"] else "")
        return (o["label"] + " " if o["label"] else "") + rng
    included = list(dict.fromkeys(i for i in included if i))
    out["options"] = "; ".join(dict.fromkeys([f"{i} (no charge)" for i in included] + [show(o) for o in opts]))[:400]
    if included:
        out.update(fee=0.0, included=True, note="a spot is included or free: " + included[0][:120])
        return out
    firsts = [o for o in opts if o["role"] == "first"]
    normal = firsts or [o for o in opts if o["role"] != "second"]
    if not normal:
        out["note"] = ("free only for a limited time; " if promo else "") + ("only additional-spot prices are stated" if opts else "fee not stated")
        return out
    cov = [o for o in normal if o["cls"] == "covered"]
    pick = min(cov or normal, key=lambda o: o["amt"])
    out["fee"] = pick["amt"]
    bits = []
    if firsts:
        bits.append("price of the first spot")
    elif len(normal) > 1:
        bits.append("cheapest covered or garage option" if cov else "cheapest of the prices listed")
    if pick["hi"]:
        bits.append(f"low end of the stated range ${pick['amt']:g}-${pick['hi']:g}")
    if promo:
        bits.append("a time-limited free-parking offer is not counted")
    out["note"] = "; ".join(bits)
    return out


def parking_from_fee_items(items):
    """Trulia-style fee lines [{'title': 'Covered parking fee ($135)', 'value': ...}] -> one parking sentence."""
    bits = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        title, val = str(it.get("title") or it.get("name") or ""), str(it.get("value") or it.get("amount") or "")
        if re.search(r"park|garage|carport", title, re.I):
            m = re.search(AMT, title) or re.search(AMT, val)
            if re.search(r"included", val, re.I):
                bits.append(f"{title}: included in rent")
            elif m:
                bits.append(f"{re.sub(r'[(]?' + AMT + r'[^)]*[)]?', '', title).strip()} ${m.group(1)}{m.group(2) or ''}")
            else:
                bits.append(f"{title}: fee not stated")
    return "; ".join(bits)


# ---------------------------------------------------------------------------------------------------------- fees
_ONE_TIME = r"one[- ]?time|at move|move-?in|per year|a year|annual|yearly|deposit|application|(?<!billing )admin(?:istrative)? fee|holding|per lease|lease term|security|total shown|non-?refundable|background|per applicant|per adult|waived|preparation|prep fee|move-?out|redecorat|cleaning fee|key fee|reservation"
_NOT_BUILDING = r"\bpets?\b|\bdogs?\b|\bcats?\b|parking|garage|carport|storage|optional|washer|dryer|furnish|\bev\b|locker|bike|\binterior\b|\bexterior\b|\bspots?\b|\bspaces?\b|surface lot|covered"


def monthly_fees_from_text(text, unit=""):
    """Required monthly building fees in a fee sentence. Returns (total or None, note).

    Counts amounts with or without '$' ('Technology Connect: 66'); skips one-time charges, deposits, pet, parking and
    optional items; 'no amenity fee' is a known $0; an amount over $400 with no monthly wording is not counted and is
    named in the note. None means no amount could be read (the note says whether a fee is known to exist).
    """
    t = str(text or "").strip()
    if is_blank(t):
        return None, ""
    tl = t.lower()
    m = re.search(r"site total of priced required fees:\s*\$?(\d+(?:\.\d+)?)", tl)
    if m:
        return float(m.group(1)), "the site's total of priced required fees" + ("; some required items have no published amount" if "amount not stated" in tl else "")
    if re.search(r"included in (?:the )?(?:advertised |listed |base )?rent", tl) and not re.search(AMT, tl):
        return 0.0, "stated as included in the advertised rent"
    m = re.match(r"\s*" + AMT + r"\s*(?:/\s*mo(?:nth)?\.?|a month|per month|monthly)?\s*\((?:the )?total[_ ]price (?:minus|less) (?:the )?base[_ ](?:price|rent)[^)]*\)", t, re.I)
    if m:
        # independent check 3, D14 (1 Kennedy Flats): "$90/mo (total_price minus base_price); $50 amenity fee named".
        # The first figure IS the total of the required fees; whatever is named after it is a part of it, never added.
        return _f(m.group(1), m.group(2)), "the page's total price minus its base price (the fees named beside it are parts of this total)"
    if re.fullmatch(r"\$?\s*\d+(?:\.\d+)?(?:\s*/\s*mo(?:nth)?)?", tl):
        v = money(tl)
        return (v, "parsed from the fee text") if v <= 400 else (None, f"${v:g} not counted: no monthly wording")
    tot, found, notes, per_unit, counted = 0.0, False, [], {}, []
    lead = re.match(r"\s*" + AMT + r"\s*(?:/\s*mo(?:nth)?\.?|a month|per month|monthly)?\s*:", t)          # '$182: A $90 + B $92'
    if not lead:
        # '$100/mo (trash $25 + amenity $75); electricity separate': the total, then its own breakdown in brackets
        # (independent check 2, D13). Only when the bracket holds two or more amounts that add up to the total.
        lm = re.match(r"\s*" + AMT + r"\s*(?:/\s*mo(?:nth)?\.?|a month|per month|monthly)?\s*\(([^)]*)\)", t)
        if lm:
            inner = [_f(a, b) for a, b in re.findall(AMT, lm.group(3))]
            if len(inner) >= 2 and abs(sum(inner) - _f(lm.group(1), lm.group(2))) < 0.5:
                lead = lm
    # a range ('$35-$45', '$35 to $45') is one fee, counted once at its high end (the safe side for a cost cap), D13
    ranges = []

    def _range(m):
        lo, hi = _f(m.group(1), m.group(2)), _f(m.group(3), m.group(4))
        if hi >= lo:
            ranges.append((lo, hi))
            return f"${hi:g}"
        return m.group(0)
    t_r = re.sub(AMT + r"\s*(?:-|–|to)\s*" + AMT, _range, t[lead.end():] if lead else t)
    body = t_r
    for clause in re.split(r";|\||\+|\bplus\b|,(?!\d{3})|\.\s+(?=[A-Z])|\band\b(?=[^$]*\$)", body):
        c = clause.strip()
        if not c:
            continue
        cl = c.lower()
        if re.search(r"\bno (?:amenity|monthly|required|additional|community|other|extra)(?: \w+)? fees?\b|\bno fees?\b", cl) and not re.search(AMT, c):
            found = True
            notes.append("the page says no " + (re.search(r"no ((?:\w+ )?(?:\w+ )?fees?)", cl).group(1)))
            continue
        amts = [(mm, _f(mm.group(1), mm.group(2))) for mm in re.finditer(AMT, c)]
        if not amts:
            mm = re.search(r"[a-z][\w /&'()-]*?[:=]\s*(\d{1,4})(\.\d+)?\s*(?:/\s*mo\w*|monthly|a month|per month)?\s*$", cl)
            if mm and not re.search(r"\d\s*(?:lb|units?|months?|%|floors?)\b", cl):
                amts = [(mm, _f(mm.group(1), mm.group(2)))]
            elif re.fullmatch(r"\d{1,3}(?:\.\d+)?", cl):
                amts = [(None, float(cl))]
        if not amts:
            continue
        if re.search(_NOT_BUILDING, cl):
            continue
        monthly_words = bool(re.search(r"/\s*mo\b|/\s*month|per month|a month|monthly|\bmo\b", cl))
        if re.search(_ONE_TIME, cl) and not monthly_words:
            continue
        um = re.search(r"\(unit ([\w-]+)", cl)
        for _, a in amts[:1] if um or len(amts) == 1 else amts:
            if a <= 0:
                continue
            if um:
                per_unit[unit_key(um.group(1))] = a
                continue
            if a > 400 and not monthly_words:
                notes.append(f"${a:g} not counted (over $400 with no monthly wording): {c[:60]}")
                continue
            if a > 1000:
                continue
            counted.append(a)
            found = True
    # prices given as alternatives (two sources that differ, or one price per unit size) are never added together
    alternatives = bool(re.search(r"sources differ|\bstudio\b.*\b(?:one|1)[- ]?(?:bed|br)|\b(?:one|1)[- ]?(?:bed|br).*\b(?:two|2)[- ]?(?:bed|br)", tl))
    if counted:
        tot = max(counted) if alternatives else sum(counted)
        if alternatives and len(counted) > 1:
            notes.append("the text gives alternative amounts (" + ", ".join(f"${v:g}" for v in counted) + "); the highest is used")
    if lead:
        lv = _f(lead.group(1), lead.group(2))
        if lv <= 1000:
            return lv, "parsed from the fee text (stated total)"
    if per_unit:
        k = unit_key(unit)
        if k in per_unit:
            tot += per_unit[k]
            found = True
        else:
            notes.append("the fee differs by unit (" + ", ".join(f"${v:g}" for v in sorted(set(per_unit.values()))) + " seen on other units)")
    for lo, hi in ranges:
        notes.append(f"the page gives a range ${lo:g}-${hi:g}; the high end is counted")
    if found:
        return tot, "; ".join(["parsed from the fee text"] + notes)
    if re.search(r"amounts? not (?:stated|shown|published)|not published|fee exists|\bfees?\b", tl) and not re.search(r"^\s*renter'?s insurance required\s*$", tl):
        notes.insert(0, "fee exists, amount not published")
    return None, "; ".join(notes)


def fees_from_json(raw, unit=""):
    """Read a listing's other_monthly_fees_json. Returns dict(fee, fee_note, parking_text, pet_text).

    fee: required monthly building fees (None = nothing readable). parking_text / pet_text: parking and pet lines found
    among the fee items, as sentences for parse_parking / parse_pet_rent.
    """
    out = {"fee": None, "fee_note": "", "parking_text": "", "pet_text": ""}
    try:
        j = json.loads(raw) if isinstance(raw, str) and raw.strip() else None
    except ValueError:
        return out
    if j is None:
        return out
    skip = re.compile(r"deposit|application|one_?time|one-time|security|lease|non_monthly|move|admin(?!istrative)|pet|total_price|_max$|url|storage|park|optional", re.I)

    def n(x):
        try:
            v = float(str(x).replace(",", "").replace("$", ""))
            return v if math.isfinite(v) else None
        except (TypeError, ValueError):
            return None
    if isinstance(j, list):
        j = {"monthly": j}
    fee, known, notes, park, pet = 0.0, False, [], [], []
    for key in ("required_total_min", "required_monthly_fees_min", "required_fees"):
        if n(j.get(key)) is not None:
            fee, known = n(j[key]), True
            notes.append("the page's total of required monthly fees")
            break
    for k, val in j.items():
        kl = k.lower()
        if isinstance(val, list):
            required = bool(re.search(r"required", kl)) and not re.search(r"one|non_monthly", kl)
            monthly = bool(re.search(r"monthly|^monthly$", kl)) and not re.search(r"one-?time|non_monthly|onetime", kl)
            optional = "optional" in kl
            if re.search(r"one-?time|onetime|non_monthly", kl):
                continue
            for it in val:
                if not isinstance(it, dict):
                    continue
                title = str(it.get("title") or it.get("name") or "")
                v = str(it.get("value") if it.get("value") is not None else it.get("amount") or "")
                req = required or str(it.get("requirement", "")).lower() == "required" or it.get("required") is True
                cad = str(it.get("cadence", "month")).lower()
                if "month" not in cad and cad not in ("", "1"):
                    continue
                if re.search(r"park|garage|carport", title, re.I):
                    park.append(it)
                    continue
                if re.search(r"\bpet\b|\bdog\b|\bcat\b", title + " " + str(it.get("section", "")) + " " + str(it.get("species", "")), re.I):
                    if re.search(r"rent|monthly|fee", title + " " + str(it.get("terms", "")), re.I) and (monthly or optional or "month" in str(it.get("terms", "")).lower()):
                        sp = str(it.get("species", ""))
                        pet.append(f"{sp + ' ' if sp else ''}{title} rent {v if re.search(AMT, v) else ''}".strip() if not re.search(AMT, title) else f"{title} monthly")
                    continue
                if re.search(r"base rent|^rent$", title, re.I) or optional or not (req and (monthly or required)):
                    continue
                a = (re.search(AMT, title) or re.search(AMT, v))
                a = _f(a.group(1), a.group(2)) if a else n(v)
                if a is not None and 0 < a <= 400:
                    if not known or "total" not in " ".join(notes):
                        fee += a
                        known = True
                elif not re.search(r"included", v, re.I):
                    notes.append(f"fee exists, amount not published: {title}")
        elif isinstance(val, dict):
            continue
        elif isinstance(val, str) and kl in ("additional_fees", "amenity_fee"):
            ft, note = monthly_fees_from_text(val, unit)
            if ft is not None and "total" not in " ".join(notes):
                fee, known = max(fee, ft), True
            elif note:
                notes.append(note)
        elif not skip.search(k) and kl not in ("required_total_min", "required_monthly_fees_min", "required_fees") and "total" not in " ".join(notes):
            a = n(val)
            if a is not None and 0 < a <= 400:
                fee += a
                known = True
    out["fee"] = fee if known else None
    out["fee_note"] = "; ".join(dict.fromkeys(notes))
    out["parking_text"] = parking_from_fee_items(park)
    out["pet_text"] = "; ".join(pet)
    return out


# ----------------------------------------------------------------------------------------------------- utilities
_UTIL_WORDS = [("electric", r"electric(?:ity|al)?"), ("gas", r"cooking gas|natural gas|\bgas\b"), ("heat", r"\bheat(?:ing)?\b"),
               ("hot_water", r"hot water"), ("water", r"(?<!hot )\bwater\b"), ("sewer", r"sewer|sewage"), ("trash", r"trash|garbage|refuse"),
               ("internet", r"internet|wi-?fi|broadband"), ("cable", r"\bcable\b")]
_TENANT = r"paid by (?:the )?(?:resident|tenant)|(?:resident|tenant)s? (?:is |are )?(?:pays?|responsible)|not included|billed (?:separately|to|back|on top)|separately metered|sub-?metered|at (?:the )?(?:resident|tenant)'?s? expense|excluded"
_INCLUDED = r"\bincluded?\b|\bincludes\b|paid by (?:the )?(?:landlord|owner|community|building)|landlord pays"


def _utils_in(s):
    return {k for k, pat in _UTIL_WORDS if re.search(pat, s)}


def parse_utilities(text):
    """Split a utilities sentence. Returns {'included': set, 'tenant': set, 'none': set}.

    Only an explicit statement puts a utility in 'included': 'gas/electric and water/sewer paid by resident',
    'tenant pays electricity and cooking gas' and 'Electric=Resident' land in 'tenant'. 'all utilities except cooking
    gas and electricity' includes heat, hot water and water only. 'All utilities' never covers internet. 'heat' does
    not imply cooking gas. 'none' holds services the unit does not have ('no gas', 'all-electric building').
    """
    res = {"included": set(), "tenant": set(), "none": set()}
    t = str(text or "").strip().lower()
    if is_blank(t) or t.startswith("none listed"):
        return res
    for name, who in re.findall(r"([a-z /]+?)\s*=\s*([a-z/]+)", t):         # 'Electric=Resident; Trash=Community'
        u = _utils_in(name)
        if re.match(r"resident|tenant", who):
            res["tenant"] |= u
        elif re.match(r"community|included|landlord|owner|building", who):
            res["included"] |= u
        elif who.startswith("n/a"):
            res["none"] |= u & {"gas"}
    t = re.sub(r"\[[^\]]*\]", " ", t)
    if re.search(r"all[- ]electric", t):
        res["none"].add("gas")
    ALL = {"electric", "gas", "heat", "hot_water", "water"}
    for clause in re.split(r";|\.\s|\bbut\b|,\s*(?=(?:the )?(?:tenant|resident)s?\b)|\|", t):
        c = clause.strip()
        if not c:
            continue
        if re.search(r"\bno gas\b", c):
            res["none"].add("gas")
            c = re.sub(r"\bno gas\b", " ", c)
        m = re.search(r"all utilities(?: (?:are )?included)?,? (?:except|but not|other than|excluding)(?: for)? (.*)", c)
        if m:
            ex = _utils_in(m.group(1))
            res["included"] |= ALL - ex
            res["tenant"] |= ex
            continue
        c = re.sub(r"utilities included:?|included utilities:?", "included: ", c)
        found = _utils_in(c)
        if re.search(_TENANT, c) or re.search(r"\b(?:resident|tenant)s? pays?\b", c):
            res["tenant"] |= found
        elif re.search(r"all utilities|utilities (?:are )?included", c) and not re.search(r"not specified|which utilities", c):
            res["included"] |= ALL | found
        elif re.search(_INCLUDED, c) and not re.search(r"not specified|which utilities|fee", c):
            res["included"] |= found
        elif found:
            rest = c
            for _, pat in _UTIL_WORDS:
                rest = re.sub(pat, " ", rest)
            rest = re.sub(r"\b(?:and|cooking|cold|a/c|air conditioning|cooling|rent stabilized|pest control|yes|basic)\b|[,/&:\s]", "", rest)
            if not rest:                                                    # a bare list in a field named 'included'
                res["included"] |= found
    res["included"] -= res["tenant"]
    return res


# ------------------------------------------------------------------------------------------------------ amenities
_NEG = r"^\s*(?:no|none|not|n/a|false|0)\b|none listed|not listed|none stated|not stated on|no (?:\w+ )?(?:listed|stated|mentioned)|see quote|not_found|no_mention"


def amenity_yes(text) -> bool:
    """Generic 'has it' test: a non-blank value that is not a negative ('none listed', 'no', 'not stated')."""
    t = str(text or "").strip().lower()
    return not is_blank(t) and not re.search(_NEG, t)


def pool_state(text) -> str:
    """'' (no pool known), 'pool' or 'indoor'. 'Pool table', 'none listed (pool table only)' and 'see quote' are ''."""
    t = str(text or "").strip().lower()
    if is_blank(t) or re.search(_NEG, t):
        return ""
    t2 = re.sub(r"pool\s*tables?|billiards?|car\s*pool|whirlpool|pool\s*hall", " ", t)
    if not (re.search(r"\bpools?\b", t2) or re.match(r"\s*(?:yes|both|indoor|outdoor|rooftop|heated|seasonal|lap)\b", t2)):
        return ""
    indoor = (re.search(r"\bindoor\b|^both$", t2) and not re.search(r"not stated|indoor or outdoor|indoor/outdoor|no indoor", t2)) \
        or re.search(r"and indoor|indoor and outdoor", t2)
    return "indoor" if indoor else "pool"


def doorman_state(text) -> str:
    """'' (none known), 'doorman' or '24h'. 'no doorman stated', 'none listed' and 'virtual doorman' are ''."""
    t = str(text or "").strip().lower()
    if is_blank(t):
        return ""
    t2 = re.sub(r"virtual (?:doorman|door ?person|concierge)|video intercom|virtual", " ", t)
    if re.search(_NEG, t2) or re.search(r"\bno (?:doorman|concierge|door ?person)", t2):
        return ""
    if not re.search(r"door ?m[ae]n|door ?person|concierge|attended|staffed|welcome desk|front desk|lobby (?:staff|attendant)|\byes\b|24|daytime|full[- ](?:time|service)", t2):
        return ""
    return "24h" if re.search(r"24", t2) else "doorman"


def virtual_doorman(text) -> bool:
    return bool(re.search(r"virtual (?:doorman|door ?person|concierge)", str(text or "").lower()))


# --------------------------------------------------------------------------------------------------------- income
def income_restricted(text) -> bool:
    """True only for affordable-housing / income-cap language. '40x rent', '3x the rent in household income' and
    '$130,000 a year' are ordinary screening, not a restriction."""
    t = str(text or "").strip().lower()
    if is_blank(t):
        return False
    if re.search(r"affordable|income[- ]restrict|income cap|income limit|maximum (?:household )?income|max(?:imum)? income|lottery|\bami\b|"
                 r"area median income|income rules|income-?qualified|section 8 only|lihtc|not exceed|no more than \$|below \$\d", t):
        return True
    return bool(re.search(r"income (?:of |between |from )?\$[\d,]+\s*(?:to|-|–|and)\s*\$[\d,]+", t))


# ---------------------------------------------------------------------- independent check 2 (D8, D10): lease term, floor
_AMENITY_AFTER = (r"(?:\s+(?:resident'?s?|residents'|furnished|landscaped|rooftop|roof|outdoor|indoor|sky|panoramic|common|shared|private club))*"
                  r"\s+(?:terraces?|sun ?decks?|decks?|lounges?|gym|fitness|amenit\w+|laundry|pool|club ?room|clubhouse|garden|roof|"
                  r"library|playroom|party room|common|courtyard|solarium|spa|theat\w+|co-?working|storage)")
_FLOOR_WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "ground": 0}


def floor_from_description(text):
    """The unit's floor as a listing description states it, or None.

    The first 'Nth floor' phrase is NOT enough (independent check 2, D10): '8th-floor sundeck', '11th floor Terraces'
    and "7th Floor Resident's Lounge" describe an amenity, and settled three units on the wrong floor. A phrase counts
    only when it is not about an amenity; if two unit phrases disagree the floor is not stated.
    """
    t = str(text or "")
    found = []
    for m in re.finditer(r"\b(?:(\d{1,2})(?:st|nd|rd|th)|(first|second|third|fourth|fifth|sixth|seventh|ground))[- ]floor\b", t, re.I):
        after = t[m.end():m.end() + 60]
        before = t[max(0, m.start() - 40):m.start()].lower()
        if re.match(_AMENITY_AFTER, after, re.I) or re.search(r"(?:on|and|from) (?:the|our|a) (?:roof ?deck|rooftop)[^.]{0,20}$|\band\s*$", before) and re.match(r"\s+terrace", after, re.I):
            continue
        if re.search(r"\b(?:through|to|thru)\s+(?:the\s+)?$|\bfloors?\s+\d+\s*-\s*$", before):
            continue
        f = int(m.group(1)) if m.group(1) else _FLOOR_WORDS[m.group(2).lower()]
        found.append(f)
    vals = set(found)
    return found[0] if len(vals) == 1 else None


def lease_term_from_text(text):
    """What a checker's note says about the lease term the LISTED price belongs to (independent check 2, D8).

    Returns {'months': int|None, 'price_12': float|None, 'lowest_of_terms': bool, 'quote': str}.
    months      the term the listed price is quoted for ('Price is for a 24 Months lease', '$2,340 IS THE 20-MONTH
                LEASE PRICE', 'lease 15 mo', '15-month lease price', '$2,590 is the 18-month term')
    price_12    the 12-month price where the same note gives it ('12-month price $2,430', '12-month base is $2,105')
    lowest_of_terms  the note says only that the price is the lowest over the lease terms offered (term not named)
    An offer sentence ('1 month free on a 14-month lease') is not a statement about the listed price and yields nothing.
    """
    t = re.sub(r"\s+", " ", str(text or ""))
    out = {"months": None, "price_12": None, "lowest_of_terms": False, "quote": ""}
    if not t.strip():
        return out
    N = r"(\d{1,2})(?:[- ]?(?:or|/|to)[- ]?(\d{1,2}))?"
    pats = [r"price(?: shown)? is for a " + N + r"[- ]months?[- ](?:lease|term)",
            r"\bis the " + N + r"[- ]months?[- ]?(?:lease[- ])?(?:price|term|base)",
            r"\bIS THE " + N + r"-MONTH LEASE PRICE",
            N + r"-month[- ](?:lease[- ])?(?:lease price|price|base)\b",
            r"lease (?:term|length) shown(?: is)? " + N + r" months?",
            r"lowest price is for a " + N + r"-month lease",
            r"priced for a " + N + r"-month term",
            r"\blease " + N + r" mo\b",
            r"\bPlan [^,;.]{1,40}, " + N + r"-month lease",
            r"\$[\d,]+(?: base| total)?[^.;|]{0,40}\bon a " + N + r"-month lease",
            r"\(" + N + r"-month term\)", r"\(" + N + r"(?:/\d{1,2})? mo\)",
            r"for an? " + N + r"-month term", r"lease_length " + N + r"\b",
            N + r"-month lease, (?:available|move-in)"]
    best = None
    for p in pats:
        for m in re.finditer(p, t, re.I):
            pre = t[max(0, m.start() - 45):m.start()].lower()
            if re.search(r"free (?:on|with|when|for)|months? free|off (?:on|with)|sign an?|receive|special|credit on|\b12-month (?:price|base|term)", pre) and "price" not in m.group(0).lower():
                continue
            mo = max(int(x) for x in m.groups() if x)
            if mo == 12 and re.search(r"12-month (?:price|base)", m.group(0), re.I):
                continue                                   # '12-month price $2,430' is the comparison, not the listed term
            if best is None or m.start() < best[0]:
                best = (m.start(), mo, t[max(0, m.start() - 30):m.end() + 40].strip())
    if best:
        out["months"], out["quote"] = best[1], best[2]
    m = re.search(r"12-month (?:price|base(?: rent)?|term)(?: is| rent)?:? \$?(\d{1,2},?\d{3})\b", t, re.I)
    if m:
        out["price_12"] = float(m.group(1).replace(",", ""))
    m = re.search(r"lowest (?:price|of any term)? ?over (?:the )?lease terms[^.;|]{0,40}|the lowest of any term", t, re.I)
    if m:
        out["lowest_of_terms"] = True
        out["quote"] = out["quote"] or m.group(0).strip()
    return out


DOGS_NOT_EXPLICIT = re.compile(
    r"case[- ]by[- ]case|upon approval|with (?:the )?(?:landlord|owner)(?:'s)? approval|subject to (?:landlord |owner |board )?approval|dogs? (?:are )?not named|"
    r"species (?:and size )?not stated|pets? considered|pets? negotiable|contact for more information on pet|no policy text|pets allowed; species|"
    r"dogs? not mentioned|does not (?:name|mention) dogs", re.I)


def dogs_not_explicit(text) -> str:
    """The phrase that shows dogs are NOT explicitly allowed ('pets upon approval', 'case by case', small pets with dogs
    unnamed), or ''. The owner's rule: dogs must be named as allowed (independent check 2, D3)."""
    m = DOGS_NOT_EXPLICIT.search(str(text or ""))
    return m.group(0) if m else ""


def lot_address_agrees(listing_address, lot_address) -> bool:
    """True when a tax lot's address is the listing's address: same house number ('35-16' = '3516'), or the listing's
    number inside the lot's range ('1010' in '1010-1012'), on a street whose first word agrees. A neighbouring lot
    ('142-38' vs '142-32', a corner lot filed under the cross street) is not the listing's lot (independent check 2, D16)."""
    a, b = str(listing_address or "").lower(), str(lot_address or "").lower()
    ma, mb = re.match(r"\s*(\d+(?:-\d+)?)\s+(.*)", a), re.match(r"\s*(\d+(?:-\d+)?)\s+(.*)", b)
    if not ma or not mb:
        return False

    def street(s):
        s = re.split(r",", s)[0]
        s = re.sub(r"\b(?:north|south|east|west|n|s|e|w)\b\.?", " ", s)
        w = re.findall(r"[a-z0-9]+", s)
        return re.sub(r"(\d+)(?:st|nd|rd|th)$", r"\1", w[0]) if w else ""
    if street(ma.group(2)) != street(mb.group(2)):
        return False
    na, nb = ma.group(1), mb.group(1)
    if na.replace("-", "") == nb.replace("-", ""):
        return True
    if "-" in nb and "-" not in na:                       # lot filed as a range 1010-1012 (not a Queens 142-32 number)
        lo, hi = nb.split("-")
        if len(lo) == len(hi) and lo.isdigit() and hi.isdigit() and int(lo) <= int(na) <= int(hi) and int(hi) - int(lo) <= 40:
            return True
    return False


def toll_known(value, complete):
    """A round-trip toll counts as known only when every crossing on the route has a rate (toll_complete). An
    incomplete sum is not a toll, and an unknown toll is never 0: returns the number, or None."""
    if str(complete).strip().lower() != "true":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


TOLL_NOTE = ("Tolls are round trip at New York E-ZPass rates (a tag issued by the New York E-ZPass service centre), weekend off-peak. "
             "An E-ZPass tag from New Jersey, Connecticut or any other state pays the higher Tolls by Mail rate at MTA bridges and tunnels "
             "(for example $12.03 instead of $7.46 at the Whitestone, Throgs Neck, RFK and Verrazzano bridges); that figure is given beside "
             "each toll as the mail rate. Where a route enters the Manhattan congestion zone, no mail rate for the zone was found on a page we could "
             "read, so the mail figure there is given as 'at least' the sum of the other crossings. Resident discounts are not applied.")


# ---- step 4a: "weight restrictions apply" with no number
_NO_WEIGHT_LIMIT = re.compile(r"\bno (?:\w+ ){0,2}(?:weight|size) (?:limit|restriction)s?\b[^.;|]*", re.I)
_WEIGHT_LIMIT_EXISTS = re.compile(r"\b(?:weight|size)\b[^.;|]{0,25}\b(?:restrictions?|limits?)\b|\blimit exists\b|maximum weight limit", re.I)
DOG_WEIGHT_QUESTION = "Confirm the dog weight limit in pounds"


def dog_weight_unstated(text) -> bool:
    """True when a policy says a dog weight or size limit exists (or 'restrictions apply' naming weight or size) and
    gives no pound figure. 'No weight limit', breed-only restrictions and a stated number are all False. Such a unit
    passes like 'small dogs' (owner, 2026-11-15) but must carry the tour question (repair report, decision 5)."""
    t = str(text or "")
    if not t.strip() or parse_dog_weight(t)[0] == "limit":
        return False
    return bool(_WEIGHT_LIMIT_EXISTS.search(_NO_WEIGHT_LIMIT.sub(" ", t)))


# ---- the 12-month price (owner, 2026-11-16, evidence batch 20): the $3,000 total is tested on the 12-month price
# wherever the page gives one, whatever lease term the listed price is quoted for
SIBLING_12_MONTH_GAP = 0.15
SIBLING_12_MONTH_TEXT = "the 12-month price in this building is much higher than the price shown: ask for it"
_PAGE_GONE = re.compile(r"page could not be found|listing page (?:has been taken down|no longer exists)|building'?s? page (?:is gone|no longer exists|has been removed)", re.I)


def use_12_month_price(listed, price_12) -> bool:
    """True when the 12-month price is known and differs from the listed price: cost and cap then use it. The quoted
    term does not matter (Harbor Landing 452: $2,487 on 13 months, $3,040 on 12)."""
    try:
        l_, p_ = float(listed), float(price_12)
    except (TypeError, ValueError):
        return False
    return p_ == p_ and l_ == l_ and p_ > 0 and abs(p_ - l_) > 0.5


def sibling_12_month_gap(months, price_12, lowest_of_terms, siblings):
    """(flag, why) for a unit whose own 12-month price was NOT read. siblings: [(unit, listed, months, price_12)] of
    the other units of the same building. The flag is set when this unit's listed price is a long-lease price (a
    quoted term over 12 months, or 'the lowest over the lease terms') and a sibling's own 12-month price exceeded its
    listed price by more than 15 percent. No price is guessed: the unit keeps its listed price, and the open item
    'listing' says to ask."""
    num = lambda v: (float(v) if str(v).strip() not in ("", "nan", "None") else None)
    try:
        m_, own = num(months), num(price_12)
    except ValueError:
        return False, ""
    if own or not ((m_ is not None and m_ > 12) or lowest_of_terms):
        return False, ""
    worst = None
    for un, listed, sm, sp in siblings:
        try:
            l_, p_ = num(listed), num(sp)
        except ValueError:
            continue
        if not l_ or not p_ or p_ <= l_ * (1 + SIBLING_12_MONTH_GAP):
            continue
        gap = p_ / l_ - 1
        if worst is None or gap > worst[0]:
            worst = (gap, un, l_, sm, p_)
    if worst is None:
        return False, ""
    gap, un, l_, sm, p_ = worst
    try:
        term = f"{float(sm):g}-month" if str(sm).strip() not in ("", "nan") else "long-lease"
    except ValueError:
        term = "long-lease"
    return True, f"unit {un} of this building is ${l_:,.0f} on its {term} price and ${p_:,.0f} on a 12-month lease ({gap * 100:.0f} percent more)"


def listing_page_gone(status, available_text, notes) -> bool:
    """A live-check row that says the building's whole listing page is gone (not only one unit left the unit list):
    every unit listed on that page is then gone (The Mercer, batch 20)."""
    return str(status).strip() == "gone" and bool(_PAGE_GONE.search(str(available_text) + " | " + str(notes)))


# ---- step 4b: staleness of a listing page, from modification dates where the data has them
STALE_OPEN_DAYS, STALE_REMOVE_DAYS, AVAIL_OLD_DAYS = 60, 183, 183
_PAGE_MODIFIED = re.compile(r"(?:last[- ]?modified|lastDateModified|lastmod|date ?modified|\bmodified|updated_at|last updated|"
                            r"record (?:last )?updated|page updated|\bupdated)\D{0,12}(20\d\d-\d\d-\d\d)", re.I)


def page_modified_date(text) -> str:
    """The latest 'last modified / updated' date (YYYY-MM-DD) a checker's note or a fact gives for a listing page, or ''."""
    ds = _PAGE_MODIFIED.findall(str(text or ""))
    return max(ds) if ds else ""


def _days_between(earlier, later):
    from datetime import date
    try:
        a, b = date.fromisoformat(str(earlier)[:10]), date.fromisoformat(str(later)[:10])
    except ValueError:
        return None
    return (b - a).days


def staleness(modified, read_on, available_date="", second_source=False):
    """(level, days, reason). level: 'remove' when the page was last changed more than six months (183 days) before it
    was read; 'open' when it was last changed more than 60 days before (unless a second site also lists the unit), or
    when the availability date is more than six months old; '' otherwise. Unknown dates give ''."""
    d = _days_between(modified, read_on) if modified else None
    if d is not None and d > STALE_REMOVE_DAYS:
        return "remove", d, f"the listing page was last changed on {str(modified)[:10]}, {d} days before it was read ({str(read_on)[:10]}): more than six months unchanged"
    if d is not None and d > STALE_OPEN_DAYS and not second_source:
        return "open", d, f"the listing page was last changed on {str(modified)[:10]}, {d} days before it was read ({str(read_on)[:10]}), and no second site lists the unit"
    a = _days_between(available_date, read_on) if re.fullmatch(r"\d{4}-\d\d-\d\d.*", str(available_date or "")) else None
    if a is not None and a > AVAIL_OLD_DAYS:
        return "open", a, f"the availability date {str(available_date)[:10]} was {a} days old when the page was read ({str(read_on)[:10]})"
    return "", d, ""


# ---- step 4c: an elevator known only from a listing site's amenity list
_ELEV_CONTRA = re.compile(r"not (?:listed|mentioned|stated|found|shown|named) on [^.;|]{0,50}own (?:site|pages?|web ?site)|"
                          r"(?:community|building|unit)(?:'s)? features[^.;|]{0,80}do(?:es)? not include an elevator|"
                          r"own (?:site|pages?|feature list|features? (?:list|page)|amenit\w+ page)[^.;|]{0,40}(?:never mention|not mention|(?:does|do) not (?:list|mention|state)|omits?|lists? no|no elevator|none either|did not state)|"
                          r"(?:own site|manager'?s? (?:own )?page|building'?s? (?:own )?(?:site|page)|\w+'s page for the building|page for the building)[^.|]{0,140}(?:does not mention|do not mention|and no elevator|no elevator)|"
                          r"own pages never mention|omits? it|select buildings|walk-?up|my reading: (?:unlikely|no elevator|probably (?:a walk|no|not))|"
                          r"which buildings have|not established|only in (?:some|select|certain)", re.I)
_ELEV_NEG = re.compile(r"\bno elevator|not (?:listed|stated|mentioned)|none listed|no ['\"]?elevator|unknown|does not mention|lists no|has no elevator|"
                       r"no page (?:read )?(?:states|says|mentions)|implied|inferred", re.I)
_ELEV_LIST_POS = re.compile(r"amenit|tags?\b|feature|\belevator\b", re.I)


def elevator_row_kind(value, quote, source_is_aggregator, status):
    """How one elevator row of the evidence pass counts (status confirmed or unconfirmed; 'contradicts' is handled apart):
      'own'     confirmed on the building's own or its manager's page                      -> basis confirmed
      'stated'  an elevator in a listing site's amenity list, tag or text, whatever the     -> basis stated (not confirmed)
                batch called the row (batches 1, 2, 8, 9 wrote 'confirmed', 10 and 15 'unconfirmed')
      'contra'  the row itself says the building's own site omits it, or the checker reads a walk-up -> stays open
      'none'    the row found no elevator stated anywhere                                   -> stays open
    """
    txt = f"{value} | {quote}"
    if _ELEV_CONTRA.search(txt):
        return "contra"
    v = str(value).strip().lower()
    positive = v.startswith(("yes", "true")) or (status == "confirmed" and not _ELEV_NEG.search(v))
    if status == "unconfirmed":
        positive = v.startswith("yes") or bool(re.search(r"amenity tag only|tag only|(?:feature|amenity|amenities) list: ['\"]?elevator|tags? ['\"]?elevator|elevator['\"]? (?:tag|amenity|in the amenit)|amenit[^.;|]{0,30}(?:lists?|has|shows|includes) (?:an )?['\"]?elevator", txt, re.I)
                                               and not _ELEV_NEG.search(v))
    if not positive:
        return "none"
    return "stated" if source_is_aggregator else ("own" if status == "confirmed" else "none")


# ---- independent check 3
# D1 (98-76 Queens Blvd 2M): a checker's note that the PRICE itself needs verifying is an open "listing" fact.
PRICE_DOUBT = re.compile(r"verify the price|far below (?:the )?(?:area|market|neighbou?rhood|other listings)|price (?:looks|seems|is) (?:too low|suspicious|implausib\w+)|"
                         r"too good to be true|well below (?:the )?market|confirm the price (?:by phone )?before", re.I)


def price_doubt(note) -> bool:
    return bool(PRICE_DOUBT.search(str(note or "")))


def label_reading(unit):
    """(building, floor, unit-on-floor) read from a unit label of a multi-building complex, or None when the label has
    no building part. Only the shapes that name a building are read:
      '09-326', '3-329', 'PA-405', 'B9-309'   X-FUU   -> building X, floor F, unit UU
      '005-5306'                              X-BFUU  -> building B, floor F
      'K3-02', 'M4-22'                        LF-UU   -> building L (a letter), floor F
      'A207', 'B511'                          LFUU    -> building L (a letter), floor F
      '5201', '2303', '4234'                  BFUU    -> building B, floor F (second digit 1-9), unit UU
    A plain label ('305', '4F', '12B', '0705') has no building part."""
    u = clean_unit(unit).strip()
    m = re.fullmatch(r"([a-z])([1-9])[\s-]+(\d{2})", u)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    m = re.fullmatch(r"([a-z]{1,3}\d{0,2}|\d{1,3})[\s-]+([1-9])(\d{2})[a-z]?", u)
    if m:
        return m.group(1).lstrip("0") or "0", int(m.group(2)), int(m.group(3))
    m = re.fullmatch(r"([a-z])([1-9])(\d{2})", u)          # 'A207', 'B511', 'C309' (Fort Hill Peekskill): building letter, floor, unit
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    m = re.fullmatch(r"\d{1,3}[\s-]+([1-9])([1-9])(\d{2})", u)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    m = re.fullmatch(r"([1-9])([1-9])(\d{2})", u)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    return None


def building_prefix(unit) -> str:
    r = label_reading(unit)
    return r[0] if r else ""


def explicit_building_label(unit) -> bool:
    """The label names its building apart from the floor and unit: a letter before the floor digit ('K3-02', 'M4-22') or a
    building part before a separator ('B9-309', 'PA-405', '09-426', '3-329', '005-5306'). A bare four-digit label
    ('5201', '4186') is not explicit: it may be floor + three-digit unit, or a tower floor."""
    u = clean_unit(unit).strip()
    return bool(label_reading(u)) and not re.fullmatch(r"\d{4}", u)


def multi_building_labels(units) -> bool:
    """True when the unit labels of one complex read as a multi-building complex (garden-style rule, owner 2026-11-16):
      - every labelled unit has a building part (label_reading), and two or more different buildings appear;
      - labels that NAME their building (explicit_building_label: 'K3-02', 'B9-309', '09-426') need nothing more. A
        floor read from such a label is not a height (independent check 4, D3: Residences at The Summit, buildings K, L
        and M, used to escape because 'K4-19' reads as floor 4; the rule asks for a height of four floors or more ON A
        PAGE OR RECORD, which build_master.garden_style tests);
      - for the bare four-digit shape (BFUU), which could also be floor + three-digit unit ('5158' = floor 5, unit 158)
        or a tower ('1206' = floor 12): no label may read above floor 3, the floor digit must vary across the labels and
        no unit-on-floor number may exceed 40 (a floor of a garden building does not hold 86 apartments; The Grove
        Somerset 4186 is floor 4)."""
    labs = [u for u in units if unit_label_key(u)]
    rs = [label_reading(u) for u in labs]
    if len(labs) < 2 or any(r is None for r in rs):
        return False
    if len({r[0] for r in rs}) < 2:
        return False
    bare = [r for u, r in zip(labs, rs) if not explicit_building_label(u)]
    if bare and (max(r[1] for r in rs) > 3 or len({r[1] for r in bare}) < 2 or max(r[2] for r in bare) > 40):
        return False
    return True


def ground_digit_positions(removed_labels):
    """Sibling consistency (independent check 3, D2: Halstead Parsippany 2182). removed_labels: unit labels of ONE
    building that a reviewer removed because "the unit number reads as floor 1". Returns (length, [positions]) where
    every removed label has that many characters in its last segment and the digit '1' at each position, i.e. the place
    in the label the reviewer read as the floor. (0, []) when the labels share no such shape (nothing is inferred)."""
    tails = [unit_tail(u) if re.search(r"[^a-z0-9]", clean_unit(u)) else unit_key(u) for u in removed_labels]
    tails = [t for t in tails if t]
    if len(tails) < 2 or len({len(t) for t in tails}) != 1:
        return 0, []
    n = len(tails[0])
    pos = [i for i in range(n - 2) if all(t[i] == "1" for t in tails)]      # the last two characters are the unit on the floor
    # Where the removed labels share '1' in two places ('1119', '1127', '1142': floor 1, units 119-142, or building 1,
    # floor 1?) the reading is ambiguous: a sibling must then carry '1' in BOTH places to be read the same way.
    return (n, pos) if pos else (0, [])


def reads_as_ground_like_siblings(unit, removed_labels) -> bool:
    """True when `unit` has the same shape as the removed siblings and '1' in the place they carry the floor."""
    n, pos = ground_digit_positions(removed_labels)
    if not n:
        return False
    t = unit_tail(unit) if re.search(r"[^a-z0-9]", clean_unit(unit)) else unit_key(unit)
    return len(t) == n and all(t[i] == "1" for i in pos)


# D24: a resident quote that characterises who lives somewhere by ethnicity, race, religion or origin is never shown
# (working rule 9). It matches a group word used OF PEOPLE ("lots of hispanics", "mostly white people", "the Jewish
# community"), not a cuisine or a shop ("Italian restaurants", "Chinese food").
_GROUP = (r"(?:hispanics?|latin[oa]s?|latinx|blacks?|whites?|asians?|african[- ]americans?|caucasians?|jews?|jewish|muslims?|christians?|catholics?|hindus?|sikhs?|"
          r"hasidi[cm]|orthodox|indians?|chinese|koreans?|filipinos?|mexicans?|dominicans?|puerto ricans?|haitians?|jamaicans?|italians?|irish|polish|portuguese|"
          r"brazilians?|russians?|arabs?|guyanese|bangladeshis?|pakistanis?|colombians?|ecuadorians?|peruvians?|greeks?|albanians?|west indians?|caribbean|"
          r"immigrants?|minorit(?:y|ies)|foreigners?)")
_PEOPLE = r"(?:people|persons?|folks?|residents?|population|populated|communit(?:y|ies)|famil(?:y|ies)|neighbou?rs?|neighbou?rhood|area|town|kids|students|demographics?|majority|enclave)"
_NOT_PEOPLE = r"(?!\s+(?:food|restaurants?|cuisine|places?|spots?|bakery|bakeries|delis?|markets?|stores?|shops?|groceries|supermarkets?|church(?:es)?|eateries|options|dishes))"
RESIDENTS_BY_GROUP = re.compile(
    r"\b(?:lots? of|many|mostly|full of|too many|all|majority(?: of)?|predominantly|mainly|primarily|largely|heavily|a lot of|so many|nothing but|only)\s+(?:\w+\s+){0,2}?" + _GROUP + r"\b" + _NOT_PEOPLE
    + r"|\b" + _GROUP + r"\s+" + _PEOPLE + r"\b|\b" + _PEOPLE + r"\s+(?:is|are|of)\s+(?:\w+\s+){0,2}?" + _GROUP + r"\b" + _NOT_PEOPLE, re.I)


def characterises_residents_by_group(text) -> bool:
    return bool(RESIDENTS_BY_GROUP.search(str(text or "")))


# ============================================================================================ THE ELEVATOR RULE
# One rule for every stage (gates.py, build_master.py, rank.py). Before the consistency pass each stage decided "is the
# elevator established" by itself and they disagreed: a management page's "high-rise" label passed the listing gate but
# not the ranking; a page-stated unit floor of 6+ counted as height at the gate but not in the ranking; the city's
# walk-up class on a neighbouring lot failed listings although neighbouring lots are not to be used.
#
# TRUTH TABLE (first matching row wins)
#   1  a phone answer                                                             -> established / no   (confirmed_by_phone)
#   2  a page of the listing or the building says there is no elevator (walk-up)  -> no
#   3  a positive source exists:
#        S1 stated on a page (the listing, a listing site's amenity list, the building's or manager's own page)
#        S2 the city's elevator class on the listing's OWN lot, the device list not showing zero active elevators
#        S3 an evidence row graded confirmed or stated; a parsed amenities page
#      3a ... and something speaks against it: an evidence row contradicts, the city classes the listing's own lot as
#             walk-up, the building is in data/reference/elevator_doubt.csv (or the garden-style rule), or a reviewer's
#             verdict opens it                                                    -> open
#      3b ... and nothing speaks against it                                       -> established
#   4  no positive source, and the city classes the listing's OWN lot as walk-up,
#      with no height of 6+ floors on a page                                      -> no
#   5  no positive source, a REAL height of 6+ floors: a page's floor count or floor list, a floor a page states for a
#      unit, the city's floor count on the listing's own lot, a harvester's or checker's "6+ floors" read from a page's
#      floor list or floor field, or "high-rise" on the building's own / manager's page (the wording on any other page
#      counts only with a floor count of 6+ beside it, which is already a height)  -> open ("inferred from height")
#   6  anything else                                                              -> unknown
# NEVER used, to pass or to fail: a floor read from a unit label ("42M", "1804"); a neighbouring ("nearest") tax lot.
# What the stages do with the result:
#   listing gate (gates.py)   established, open -> pass;  no -> fail;  unknown -> pending
#   ranking (rank.py)         established -> settled;  open -> ONE open gate fact (asterisk);  unknown -> not shown;
#                             no -> removed
ELEVATOR_MIN_FLOORS = 6          # owner, 2026-11-15: a building of 6+ floors is treated as having an elevator (asterisk)
EXACT_LOT = "house_number+location"
_LOT_MATCHES = (EXACT_LOT, "nearest_lot")


def lot_is_exact(match_basis, listing_address, lot_address) -> bool:
    """The tax lot IS the listing's address (independent check 2, D16): the lot lookup found one (by house number and
    location, or as the nearest lot) AND the lot's address agrees with the listing's (lot_address_agrees). A nearest
    lot at another address ('142-38' matched to '142-32') is a near miss and is never used."""
    return str(match_basis) in _LOT_MATCHES and lot_address_agrees(listing_address, lot_address)


def _num(v):
    try:
        x = float(str(v).replace(",", ""))
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def real_height(page_building_floors=None, page_unit_floor=None):
    """The building's height in floors as a PAGE gives it, or None: a page's floor count or floor list, or a floor a
    page STATES for a unit (the building is at least that tall). Callers must not pass a floor read from a unit label:
    it is not a height. The city's floor count goes to elevator_rule separately (record_floors), because it counts only
    on the listing's own lot."""
    vals = [v for v in (_num(page_building_floors), _num(page_unit_floor)) if v is not None and v > 0]
    return max(vals) if vals else None


def is_high_rise(text) -> bool:
    return "high-rise" in str(text or "").lower().replace(" ", "-")


def elevator_rule(*, phone="", page_no=False, stated=False, record_class="", record_floors=None, lot_exact=False,
                  active_devices=None, evidence="", contradicted=False, doubt=False, height=None, page_height_claim=False,
                  high_rise_own_page=False):
    """The one elevator rule (truth table above). Returns (status, basis):
      status  'established' | 'open' | 'no' | 'unknown'
      basis   'confirmed_by_phone', 'stated', 'nyc_pluto_building_class', 'evidence_confirmed', 'evidence_stated',
              'amenities_page', 'inferred_6plus_floors', 'inferred_harvester', 'inferred_high_rise_label' or ''
    Arguments (every one optional; what a stage does not know it leaves out):
      phone               'yes' / 'no': the answer of a phone call
      page_no             a page says there is no elevator
      stated              a page states an elevator (listing page, a listing site's amenity list, own page)
      record_class        'yes' / 'no' from the city's building class; used ONLY when lot_exact is true
      record_floors       the city's floor count; used ONLY when lot_exact is true and the class is not walk-up
      lot_exact           the tax lot is the listing's own address (lot_is_exact)
      active_devices      the city's count of active passenger elevators on that lot (0 cancels the class)
      evidence            'evidence_confirmed' / 'evidence_stated' / 'amenities_page': an evidence row or parsed page
      contradicted        an evidence row, a reviewer or the building's own site speaks against the elevator
      doubt               the building is in the reviewed doubt table, or caught by the garden-style rule
      height              real_height(...), from a page: never a unit label
      page_height_claim   a harvester or checker read 6+ floors from a page's floor list or floor field
      high_rise_own_page  the building's own or its manager's page calls it a high-rise
    """
    phone = str(phone or "").strip().lower()
    if phone in ("yes", "no"):
        return ("established" if phone == "yes" else "no"), "confirmed_by_phone"
    if page_no:
        return "no", "stated"
    rc = str(record_class or "").strip().lower() if lot_exact else ""        # a near-miss lot says nothing, either way
    record_yes = rc == "yes" and not (active_devices is not None and active_devices <= 0)
    basis = "stated" if stated else ("nyc_pluto_building_class" if record_yes else (evidence if evidence in ("evidence_confirmed", "evidence_stated", "amenities_page") else ""))
    if basis:
        against = contradicted or doubt or (rc == "no" and basis != "nyc_pluto_building_class")
        return ("open" if against else "established"), basis
    page_h, rec_h = _num(height), (_num(record_floors) if lot_exact and rc != "no" else None)
    tall = max([v for v in (page_h, rec_h) if v is not None], default=0) >= ELEVATOR_MIN_FLOORS
    page_tall = page_height_claim or (page_h is not None and page_h >= ELEVATOR_MIN_FLOORS) or high_rise_own_page
    if rc == "no" and not page_tall:
        return "no", "nyc_pluto_building_class"
    if page_height_claim:
        return "open", "inferred_harvester"
    if tall:
        return "open", "inferred_6plus_floors"
    if high_rise_own_page:
        return "open", "inferred_high_rise_label"
    return "unknown", ""


_MASTER_STATED = ("confirmed", "community_page", "amenities_page", "stated")
_FLOOR_FROM_PAGE = ("confirmed_by_phone", "confirmed", "stated")


def elevator_rule_master(get, reviewer_open=False, use_doubt=True):
    """elevator_rule on a row of the master / ranked tables (rank.py, check_registry.py). `get(column)` returns the
    row's value as a string ('' when missing). The merged elevator basis maps onto the rule's inputs:
      confirmed_by_phone -> phone;  confirmed / community_page / amenities_page / stated -> stated on a page;
      official_record -> the city's class on the listing's own lot (build_master.py enters it only there);
      inferred / blank -> no positive source: only a real height can leave it open.
    Height: the building's floor count unless it is itself inferred, a floor a page states for the unit, the city's
    count on the listing's own lot, and the height finding the listing gate carried (elevator_height_basis)."""
    el, basis = get("elevator").strip().lower(), get("elevator_basis").strip()
    if basis == "confirmed_by_phone":
        return elevator_rule(phone=el if el in ("yes", "no") else "")
    hb = get("elevator_height_basis")
    return elevator_rule(
        page_no=el in ("no", "conflicting"),
        stated=el == "yes" and basis in _MASTER_STATED,
        record_class="yes" if el == "yes" and basis == "official_record" else "",
        record_floors=get("pluto_floors"),
        lot_exact=(el == "yes" and basis == "official_record") or get("pluto_lot_ok") == "yes",
        contradicted=bool(get("elevator_evidence_open")) or reviewer_open,
        doubt=use_doubt and bool(get("elevator_doubt")),
        height=real_height(get("building_floors") if get("building_floors_basis") not in ("inferred", "") else None,
                           get("unit_floor") if get("unit_floor_basis") in _FLOOR_FROM_PAGE else None),
        page_height_claim="inferred_harvester" in hb,
        high_rise_own_page="inferred_high_rise_label" in hb or (is_high_rise(get("building_type")) and get("building_type_basis") == "community_page"))


# ---- secrets in URLs: a third party's API key must never sit in a data file (Trulia's Street View links carried one)
_URL_SECRET = re.compile(r"(?<=[?&])(?:key|api_key|apikey|token|signature|sig|access_token)=[^&\s\"',]*&?", re.I)


def strip_url_secrets(text) -> str:
    """Remove key / token / signature query parameters from every URL in a text: '...&center=1,2&key=ABC&signature=XYZ'
    -> '...&center=1,2'. Only the URLs are touched; everything else is left byte for byte."""
    def fix(m):
        u = _URL_SECRET.sub("", m.group(0))
        return re.sub(r"[?&](?=,|$)", "", u) if u != m.group(0) else u
    return re.sub(r"https?://[^\s\"'<>]+", fix, str(text))


# ---- names shown on the page: a building's name is its NAME, not a listing title; a park's name must be a park's
_ADDR_TAIL = re.compile(r",\s*[^,]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?(?:,\s*(?:USA?|United States))?\s*$")
_STREET_WORD = (r"(?:st|street|ave|avenue|blvd|boulevard|rd|road|dr|drive|pl|place|ct|court|ln|lane|ter|terrace|pkwy|parkway|hwy|highway|way|sq|square|"
                r"plz|plaza|tpke|turnpike|broadway|row|walk|loop|cir|circle)")
_IS_ADDRESS = re.compile(r"^\s*\d+[\w-]*\s+(?:[\w.'-]+\s+){0,5}" + _STREET_WORD + r"\b\.?(?:\s+(?:n|s|e|w|north|south|east|west))?\s*$|"
                         r"^\s*(?:[\w.'-]+\s+){1,4}" + _STREET_WORD + r"\s*(?:&|and|at)\s+(?:[\w.'-]+\s+){1,4}" + _STREET_WORD + r"\s*$", re.I)
_MARKETING_TAIL = re.compile(r"\s+(?:\||~|–|—)\s+.*$|\s+-\s+(?:luxury|resort|apartments? (?:for rent|in)|brand new|now leasing|new construction)\b.*$", re.I)


def street_address(address) -> str:
    """The street part of an address that carries its city, state and ZIP: '219 Lenox Rd, Brooklyn, NY 11226, USA' ->
    '219 Lenox Rd'; '31-20 54th Street, 31-20 54th St, Flushing, NY 11377, US' -> '31-20 54th Street'. An address
    with no such tail is unchanged. (City, state and ZIP have their own fields.)"""
    a = str(address or "").strip()
    if not _ADDR_TAIL.search(a):
        return a
    return a.split(",")[0].strip()


def clean_building_name(name, address="") -> str:
    """A building's name for the page, or '' when the listing gave none. A listing TITLE is not a name:
      '80East | Luxury Apartments | Dover, NJ'                         -> '80East'
      'The Mark, Fairfield County ~ Resort-Inspired Luxury Living'     -> 'The Mark, Fairfield County'
      '219 Lenox Rd #5G, Brooklyn, NY 11226, USA'                      -> ''   (it is the address; the page shows the address)
      '31-20 54th Street #2fl , 31-20 54th St, Flushing, NY 11377, US' -> ''
      'Kew Gardens Rd & 83rd Ave, New York, NY 11415, USA'             -> ''
    A unit is never kept inside a name ('#5G' goes to the unit field: split_address_unit)."""
    n = re.sub(r"\s+", " ", str(name or "")).strip()
    if is_blank(n):
        return ""
    n = _MARKETING_TAIL.sub("", n).strip(" ,|~-")
    bare, unit = split_address_unit(n)
    street = street_address(bare)
    listing_title = bool(unit) or street != bare or bool(re.search(r",\s*(?:USA?|United States)\s*$", n))     # a unit, or city / state / ZIP / country
    if listing_title and (_IS_ADDRESS.match(street) or street != bare):
        return ""                                  # the "name" is the listing's address line
    if address and _norm_addr_words(street) == _norm_addr_words(street_address(split_address_unit(address)[0])):
        return ""                                  # the name only repeats the building's own address
    return bare if unit else n


def _norm_addr_words(a) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(a).lower()).strip()


_PARK_WORDS = re.compile(r"park|playground|green|garden|field|preserve|woods?\b|forest|reservation|commons?\b|beach|memorial|trail|reserve|sanctuary|arboretum|"
                         r"meadow|pond|lake|recreation|conservation|refuge|grove|wildlife|nature|open space|lawn|ramble|glen\b|esplanade|promenade|"
                         r"waterfront|boardwalk|riverwalk|marsh|island|triangle|oval|square", re.I)


def park_name(name) -> str:
    """The nearest green space's name when it reads as a park, else ''. OpenStreetMap tags many things leisure=park
    ('Leif Ericson Drive', 'Baldwin Plaza', 'Orange County Fair', 'Old Campus'): the distance is still right, but the
    page must say "a park", not a name that is not one."""
    n = str(name or "").strip()
    return n if n and n.lower() != "nan" and _PARK_WORDS.search(n) else ""


# ---- independent check 4, D1 / D17: a building's point must lie where its address says
COORD_AGREE_M = 150


def coord_check(zip_agrees, geocode_dist_m=None, geocode_in_address_area=False, municipality_agrees=False):
    """What to do with a building's listing coordinates, given the Census geography at that point.
      zip_agrees               the point lies in a ZIP area (ZCTA) that a listing row of the building names
      geocode_dist_m           metres from the point to the Census geocoder's match for the address (None: no match)
      geocode_in_address_area  the geocoder's point lies in the address's ZIP or in the municipality the address names
      municipality_agrees      the municipality at the listing point is the city the address names
    Returns (action, why):
      'keep'       the listing point is used
      'regeocode'  the geocoder's point for the address replaces the listing point (Harbor Pointe, Bayonne: Apartment
                   List's point was 6.9 km away in Elizabeth's port; Parkway Lofts, Bloomfield: 168 m away in East Orange)
      'flag'       neither can be trusted: the building is flagged (an open 'listing' fact), never silently used
    """
    if zip_agrees:
        return "keep", ""
    if geocode_dist_m is not None and geocode_dist_m <= COORD_AGREE_M:
        return "keep", f"the point is outside the address's ZIP area, but the address geocodes {geocode_dist_m:.0f} m from it (a ZIP boundary)"
    if geocode_dist_m is not None and geocode_in_address_area:
        return "regeocode", f"the listing's point is outside the address's ZIP area and {geocode_dist_m:.0f} m from where the address geocodes"
    if municipality_agrees:
        return "keep", "the point is outside the address's ZIP area but inside the municipality the address names; the address could not be geocoded"
    return "flag", "the listing's point is outside the ZIP area and the municipality its address names, and the address could not be geocoded to check it"


_MUNI_SUFFIX = re.compile(r"\s+(?:city|village|town|borough|township|CDP|municipality)(?:\s*\(balance\))?$", re.I)


def municipality_name(place, county_subdivision="") -> str:
    """The municipality's plain name from the Census geography at a point: the incorporated place, else the county
    subdivision, without the legal suffix ('Bloomfield township' -> 'Bloomfield', 'Milford city (balance)' -> 'Milford')."""
    n = str(place or "").strip() or str(county_subdivision or "").strip()
    n = re.sub(r"\s*\(balance\)\s*$", "", n)
    return _MUNI_SUFFIX.sub("", n).strip()


def same_municipality(a, b) -> bool:
    k = lambda s: re.sub(r"[^a-z]", "", municipality_name(re.sub(r"\b(?:city of|town of|village of|township of)\b", "", str(s), flags=re.I)).lower())
    return bool(k(a)) and k(a) == k(b)


# ---- independent check 4, D2: "a second site lists the address and does not show this apartment" is one open fact
_SECOND_SITE = r"(?:zumper|apartment ?list|trulia|the (?:second|other) site)"
SECOND_SITE_OMITS = re.compile(
    r"not on the " + _SECOND_SITE + r"(?:'s)? (?:address |building )?page|"
    + _SECOND_SITE + r"(?:'s)?(?: (?:address|building) page| page)?(?: for [^.()]{0,50}?)?(?:\s*\([^)]{0,200}\))? (?:shows?|lists?) (?:only|a different|other units?[^.]{0,80}? but not)|"
    + _SECOND_SITE + r"[^.]{0,60}? lists? (?:this|the) address but not this (?:apartment|unit)", re.I)


def second_site_omits(live_note, live_status="") -> bool:
    """A checker's finding that another listing site covers this ADDRESS and does not show this apartment
    ('Unit 16F is not on the Zumper address page', 'Zumper shows only unit #401 for this address', 'Zumper's address
    page shows a different apartment here'). It is the open item 'availability' wherever a checker recorded it and the
    apartment itself was not seen live (Bedford Creative and The Tetris carried it by a reviewer's verdict; 328 Pacific
    705, Metropolis Towers 16F, 509 MLK Dr 39E and 525 Riverdale Ave 5U did not). Not a finding: 'No other allowed site
    shows this unit' with no site covering the address ('Zumper has no address page (404)')."""
    if str(live_status or "").strip().lower() in ("live", "changed"):
        return False
    return bool(SECOND_SITE_OMITS.search(str(live_note or "")))


# ---- independent check 4, D4: labels that do not identify a real, above-ground apartment
def plan_letter_label(unit, sibling_units) -> bool:
    """True for a label that is ONE letter ('P', 'F', 'C') in a building whose other listed apartments carry a number
    ('3Pb', '4OA'; '2B', '5D'). There the letter is a plan or line letter, not one home: BE (448 Scotland Rd) 'P' and 'F'
    are 'Unit P (1Bed)', 'Unit F (1 Bed with Den)' on the page; Appletree Suites lists 'C', 'E', 'F' beside 2B to 6D. A
    single letter in a building with no numbered sibling ('F' at a two-family house) stays an apartment."""
    u = clean_unit(unit).strip()
    if not re.fullmatch(r"[a-z]", u):
        return False
    return any(re.search(r"\d", clean_unit(x)) and not is_plan_label(x) for x in sibling_units)


def sequential_number_reads_ground(unit, units_total, floors) -> bool:
    """True when a bare apartment NUMBER ('10') in a building numbered in sequence reads as the first floor: the number
    is at most the average number of apartments per floor (630 West 163rd Street: apartment 10 of 65 on six floors, about
    eleven to a floor). Labels with a letter or a floor digit ('2B', '305') are read elsewhere; unknown counts read nothing."""
    u = clean_unit(unit).strip()
    try:
        n, tot, fl = int(u), float(units_total), float(floors)
    except (TypeError, ValueError):
        return False
    if not re.fullmatch(r"\d{1,2}", u) or not (tot == tot and fl == fl) or fl < 2 or tot < fl:
        return False
    return 1 <= n <= int(tot // fl)
