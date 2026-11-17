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
    if re.search(r"could not be traced|no pound figure|no (?:number|figure) (?:on |is |was )?(?:given|stated|published|any page)", t):
        # independent check 5, N5: a checker's note that NO page states a number is not a number, whatever figure it quotes
        # in passing ('small dogs only; no pound figure on any page read (the stored 25 lb could not be traced to a page)')
        return ("size_only" if re.search(r"\bsmall\b", t) else "unknown"), None
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


_REVIEW_SRC = re.compile(r"\bper (?:a |an |one )?(?:resident|tenant|renter)s?'? reviews?|\b(?:resident|tenant|renter) reviews?\b|\bper reviews\b|\baccording to (?:a |one )?review", re.I)
_REVIEW_TAIL = re.compile(r",?\s*\(?\bper (?:a |an |one )?(?:resident|tenant|renter)s?'? reviews?(?: dated \d{4}-\d\d-\d\d)?\)?", re.I)


def review_sourced(text):
    """(True, 'YYYY-MM-DD' or '') when a sentence says its figure comes from a resident's review
    ('regular (first come) $75/month, per a resident review dated 2025-05-01'). Independent check 4, D18."""
    t = str(text or "")
    if not _REVIEW_SRC.search(t):
        return False, ""
    m = re.search(r"reviews?(?: dated| of| from)? (\d{4}-\d\d-\d\d)", t)
    return True, (m.group(1) if m else "")


def _cut_words(text, n):
    """At most n characters, cut at a word boundary: never in the middle of a word, a number or a date."""
    t = str(text)
    if len(t) <= n:
        return t
    return t[:n + 1].rsplit(" ", 1)[0].rstrip(" ,;:-(")


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
            label = _REVIEW_TAIL.sub("", label).strip(" :,-.")      # the source of the figure is not part of the option's name
            opts.append({"amt": lo, "hi": hi, "label": _cut_words(re.sub(r"\s+", " ", label), 60), "cls": _park_class(label if _park_class(label) != "generic" or len(amts) > 1 else c), "role": role})
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


TOLL_NOTE = ("Tolls are round trip at New York E-ZPass rates (a tag issued by the New York E-ZPass service center), weekend off-peak. "
             "An E-ZPass tag from New Jersey, Connecticut or any other state pays the higher Tolls by Mail rate at MTA bridges and tunnels "
             "(for example $12.03 instead of $7.46 at the Whitestone, Throgs Neck, RFK and Verrazzano bridges). That figure is given beside "
             "each toll as the mail rate. Where a route enters the Manhattan congestion zone, no mail rate for the zone was found on a page that could be "
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


# ---- live-check batch 21 (2026-11-17): 'not_read' is a status word that means NOTHING WAS LEARNED
LIVE_NOTHING_LEARNED = ("not_read",)


def live_row_learned(status) -> bool:
    """False for a live-check row whose status says the page could not be read ('not_read'): the checker looked and
    learned nothing about this apartment. Such a row is not a re-read: it never replaces an earlier live / changed / gone
    row of the same apartment, sets no status, date, price or note, and (owner, 2026-11-16: no "not re-checked" flag) is
    not an open item. Where the checker's note does lean against the listing, a reviewer writes that up as a verdict
    (scripts/verdicts.py): the row stays in the evidence files, and in the evidence fingerprint, to be read."""
    return str(status or "").strip().lower() not in LIVE_NOTHING_LEARNED


def live_rows_learned(rows):
    """The live-check rows that learned something (a DataFrame with a 'status' column, or a list of dicts)."""
    if hasattr(rows, "loc"):
        return rows[[live_row_learned(x) for x in rows["status"]]] if len(rows) and "status" in rows else rows
    return [r for r in rows if live_row_learned(r.get("status"))]


def latest_live_row(rows):
    """The row a unit's live status is taken from: the latest by 'checked_at' among those that learned something, or
    None. `rows` is a list of dicts for ONE apartment."""
    kept = sorted(live_rows_learned(list(rows)), key=lambda r: str(r.get("checked_at", "")))
    return kept[-1] if kept else None


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


TOUR_START = "2026-11-22"          # the first tour day (CLAUDE.md): staleness is judged as of this day, not the day the page was read


def staleness(modified, read_on, available_date="", second_source=False, as_of=None):
    """(level, days, reason). level: 'remove' when the page was last changed more than six months (183 days) before the
    day it is judged on; 'open' when it was last changed more than 60 days before (unless a second site also lists the
    unit), or when the availability date is more than six months old; '' otherwise. Unknown dates give ''.

    The day it is judged on is the day the page was read, or `as_of` when that is later (independent check 5, N28: the
    pipeline passes the first tour day, so a page read on Nov 16 at 58 days unchanged is 64 days unchanged when tours
    start, and carries the open item now, not on Nov 18)."""
    judged = str(read_on)[:10]
    ahead = bool(as_of) and re.fullmatch(r"\d{4}-\d\d-\d\d", str(as_of)[:10] or "") and str(as_of)[:10] > judged
    if ahead:
        judged = str(as_of)[:10]
    when = (f"by the first tour day ({judged}; the page was read on {str(read_on)[:10]})" if ahead else f"before it was read ({str(read_on)[:10]})")
    d = _days_between(modified, judged) if modified else None
    if d is not None and d > STALE_REMOVE_DAYS:
        return "remove", d, f"the listing page was last changed on {str(modified)[:10]}, {d} days {when}: more than six months unchanged"
    if d is not None and d > STALE_OPEN_DAYS and not second_source:
        return "open", d, f"the listing page was last changed on {str(modified)[:10]}, {d} days {when}, and no second site lists the unit"
    a = _days_between(available_date, judged) if re.fullmatch(r"\d{4}-\d\d-\d\d.*", str(available_date or "")) else None
    if a is not None and a > AVAIL_OLD_DAYS:
        return "open", a, f"the availability date {str(available_date)[:10]} is {a} days old {when}"
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
# What the stages do with the result: since 2026-11-17 (owner, second trawl) the status goes into floor_elevator_rule
# (below), which judges it together with the floor. Before: listing gate established, open -> pass; no -> fail;
# unknown -> pending; ranking established -> settled, open -> one open gate fact, unknown -> not shown, no -> removed.
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


# ---- floor and elevator together (owner, 2026-11-17, "Second trawl"; replaces "elevator buildings only")
# A building without an elevator is allowed when the apartment is on floor 2 (one flight up); the ground floor stays
# out; floor 3 and above need an elevator; with no elevator stated and no floor stated, that is ONE open gate fact.
#
#   floor (as the rule counts it)   elevator established   open (doubt / height)   no / conflicting   unknown
#   1 or ground                     fail                   fail                    fail               fail
#   2                               settled                settled                 settled            settled
#   3 and above                     settled                open: elevator          fail               unknown (not shown)
#   not known                       settled (disclosure)   open: elevator          open: floor_or_elevator
#                                                                                                     open: floor_or_elevator
# Floor: stated or confirmed on a page or by phone ('page'), or read from the apartment number ('label': a simple label
# such as '2B' or '305', a ground word, a complex's reviewed numbering convention, a tower label; it carries the
# disclosure "read from the apartment number"). A reading that needed the building's floor count to choose among
# several ('weak') only ever fails a unit (floor 1); it never passes one.
# Building height (data/reference/building_stories.csv, build_master.py): an official record of ONE storey puts every
# apartment on the ground floor (fail) unless a page states another floor; a building of 1-2 storeys (official record,
# OpenStreetMap or a listing) has no floor 3, so a label reading above its height is not a floor, and an elevator in
# doubt there is asked as floor_or_elevator. OpenStreetMap never infers an elevator (it is not passed as a height).
WALKUP_MAX_FLOOR = 2
FLOOR_OR_ELEVATOR_CODE = "floor_or_elevator"
FLOOR_OR_ELEVATOR_Q = "Confirm the floor, and whether there is an elevator"
FLOOR_OR_ELEVATOR_LABEL = "floor and elevator"
FLOOR_2_WALKUP_Q = "it must be floor 2 (one flight up): no elevator is confirmed here"
STORIES_BASES = ("official_record", "osm", "listing")
_FLOOR_PAGE_BASES = ("confirmed_by_phone", "confirmed", "stated")


def floor_how(unit_floor_basis="", label_kind="", reading=None):
    """How the floor of a master / listing row counts in floor_elevator_rule: 'page', 'label', 'weak' or ''.
      unit_floor_basis  confirmed_by_phone / confirmed / stated -> 'page'; inferred -> 'label' for a simple label or a
                        ground word, 'weak' for a 'complex' reading; anything else -> ''
      reading           a floor read under the complex's reviewed numbering convention or as a tower label -> 'label'"""
    b, k = str(unit_floor_basis or "").strip(), str(label_kind or "").strip()
    if b in _FLOOR_PAGE_BASES:
        return "page"
    if b == "inferred" and k in ("simple", "ground_word"):
        return "label"
    if _num(reading) is not None:
        return "label"
    if b == "inferred":
        return "weak"
    return ""


def floor_elevator_rule(elevator, floor=None, how="", stories=None, stories_basis=""):
    """The floor-and-elevator gate (truth table above). Returns (status, code):
      status  'settled' | 'open' | 'fail' | 'unknown'
      code    ''                        settled with an elevator
              'floor_2'                 settled: floor 2, no elevator needed
              'elevator'                open: the existing elevator fact ("Confirm an elevator serves this apartment")
              'floor_or_elevator'       open: "Confirm the floor, and whether there is an elevator"
              'ground_floor'            fail: floor 1 or ground
              'one_storey_building'     fail: an official record gives the building one storey
              'no_elevator_above_floor_2'  fail: floor 3 or above with no elevator (or the sources conflict)
    elevator: the status of elevator_rule ('established' / 'open' / 'no' / 'unknown'; 'conflicting' counts as 'no').
    floor, how: the floor and how it counts (floor_how). stories, stories_basis: the building's height in storeys."""
    el = str(elevator or "").strip().lower()
    el = "no" if el == "conflicting" else el
    f, how = _num(floor), str(how or "")
    if how not in ("page", "label", "weak"):
        f = None
    st = _num(stories) if str(stories_basis or "") in STORIES_BASES else None
    st = st if st is not None and st >= 1 else None
    low = st is not None and st <= WALKUP_MAX_FLOOR
    if f is not None and how != "page" and st is not None and f > st:
        f = None                                    # a label reading above the building's height is not a floor
    if f is None and st == 1 and stories_basis == "official_record":
        return "fail", "one_storey_building"
    if f is not None and f < 2:
        return "fail", "ground_floor"
    if f is not None and how == "weak":
        f = None                                    # a weak reading only fails; for anything else the floor is not known
    if el == "established":
        return "settled", ""
    if f is not None and int(f) == WALKUP_MAX_FLOOR:
        return "settled", "floor_2"
    if f is not None:                               # floor 3 and above
        if el == "no":
            return "fail", "no_elevator_above_floor_2"
        if el == "open":
            return "open", "elevator"
        return "unknown", ""
    if el == "open" and not low:
        return "open", "elevator"
    return "open", FLOOR_OR_ELEVATOR_CODE


def floor_elevator_master(get, elevator_status):
    """floor_elevator_rule on a row of the master / ranked tables (rank.py, check_registry.py, verdicts.py). `get(column)`
    returns the row's value as a string ('' when missing); elevator_status is elevator_rule_master's status, or
    'conflicting' when the merged elevator says so."""
    how = floor_how(get("unit_floor_basis"), get("unit_floor_label_kind"), get("unit_floor_reading"))
    f = get("unit_floor")
    if how == "label" and _num(f) is None:
        f = get("unit_floor_reading")
    elif how == "label" and get("unit_floor_basis") == "inferred" and _num(get("unit_floor_reading")) is not None:
        f = get("unit_floor_reading")              # the complex's reviewed convention outranks the plain label reading
    return floor_elevator_rule(elevator_status, f, how, get("building_stories"), get("building_stories_basis"))


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
    if address:
        # independent check 5 (D25): '41-42 Elbertson Street, Elmhurst NY' is the address with its town, not a name
        a_, n_ = _norm_addr_words(street_address(split_address_unit(address)[0])), _norm_addr_words(n)
        rest = n_[len(a_):].strip() if a_ and n_.startswith(a_ + " ") else None
        if rest is not None and re.search(r"\d", a_) and not re.search(r"\d", rest) and len(rest.split()) <= 4 and re.search(r",\s*[A-Za-z .]+\s+(?:NY|NJ|CT|PA)$", n):
            return ""
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


# ---- independent check 4, D22: one numbering convention per complex, established once and applied to every label
NUMBERING_CONVENTIONS = ("floor_first", "building_floor_unit")


def floor_by_convention(unit, convention):
    """The floor a bare numeric label reads as under its complex's reviewed numbering convention
    (data/reference/unit_numbering_conventions.csv), or None when the label has another shape:
      'floor_first'          '4186' -> 4   (floor, then a three-digit number: The Grove Somerset, Steel Works, Piper)
      'building_floor_unit'  '3104' -> 1, '11102' -> 1   (building, floor, two-digit number: Kensington Place, J Centra)
    A reading is still a reading, never a stated floor: it removes a unit that reads as floor 1 and is otherwise only a
    tour question. Labels with a separator ('09-326', 'B9-309') name their floor after the separator and need no table."""
    u = clean_unit(unit).strip()
    if convention == "floor_first" and re.fullmatch(r"[1-9]\d{3}", u):
        return int(u[0])
    if convention == "building_floor_unit" and re.fullmatch(r"[1-9]\d{3,4}", u):
        return int(u[-3])
    return None


def tower_label_floor(unit):
    """'01-16C' -> 16: tower 01, floor 16, line C (Prospect Place, beside '02-229' = tower 02, floor 2). None for any
    other shape. Independent check 4, D22: this label was removed as a first-floor unit; it reads as floor 16."""
    m = re.fullmatch(r"\d{1,3}[\s-]+(\d{1,2})([a-z])", clean_unit(unit).strip())
    return int(m.group(1)) if m else None


# ---- independent check 4, D8: conditions a renter must know that sit in the evidence text
_FURNISHED = re.compile(r"tags the building furnished|(?:^|[;.:]\s*)furnished(?=\s*(?:[;.]|$))|\b(?:fully|comes|is|are|rented) furnished\b|\bfurnished (?:apartment|unit|studio|rental)\b(?! from)", re.I)
_NOT_FURNISHED = re.compile(r"\bunfurnished|not furnished|furnished (?:roof|lounge|lobby|terrace|deck|model|corporate|guest suite|clubroom|courtyard)", re.I)
# a credit SCORE, never a money credit ('$500 credit', '$1,500 move-in credit'): the number-first form needs the '+' or the word 'score'
_CREDIT = re.compile(r"(?:minimum credit score|credit score(?: of| over| above)?|credit (?:over|above|of))[^\d$]{0,6}([5-8]\d0)\b\+?|(?<![$\d,.])([5-8]\d0)(?:\+\s*credit(?: score)?|\s*credit score)", re.I)
_NOT_NORMAL_LEASE = re.compile(r"short[- ]term (?:rental|lease|stay)s? only|\bcorporate (?:housing|rental|lease)s? only|\bstudent housing\b|\bstudents only\b|\bfor students\b|"
                               r"\bsublet\b|\bsublease\b|\blease takeover\b|\bextended[- ]stay\b|month[- ]to[- ]month (?:only|lease only)|\bshort[- ]term only\b", re.I)


def renter_conditions(text, fact="") -> dict:
    """Conditions stated in one evidence sentence, as {kind: value}:
      'furnished'         True   the apartment or building is let furnished (a 'Furnished' tag, '; furnished;' in a
                                 checker's note); a furnished roof deck or another site's 'furnished corporate unit' is not
      'credit'            '700+' a credit score REQUIREMENT ('700+ credit', 'minimum credit score 700'); a deposit that
                                 depends on the score ('$1,000 security for credit over 700') is not a requirement
      'not_normal_lease'  words  short-term only, corporate or student housing, a sublet or lease takeover: not a normal lease
    Income is a structured fact of its own (income_requirement) and is not parsed here."""
    t = str(text or "")
    out = {}
    f = str(fact or "").strip().lower()
    if (f.startswith("furnished") and re.match(r"\s*(?:yes|true|furnished)", t, re.I)) or (_FURNISHED.search(t) and not _NOT_FURNISHED.search(t)):
        out["furnished"] = True
    for m in _CREDIT.finditer(t):
        before = t[max(0, m.start() - 60):m.start()].lower()
        if "deposit" in before or "security" in before:
            continue                               # the DEPOSIT depends on the score: not a requirement to rent
        out["credit"] = (m.group(1) or m.group(2)) + "+"
        break
    m = _NOT_NORMAL_LEASE.search(t)
    if m:
        out["not_normal_lease"] = m.group(0).lower()
    return out


# ---- independent check 4, D24: WHY a fact is open, as a short code the page turns into a plain sentence
def elevator_open_code(evidence_text) -> str:
    """Sub-code of an elevator the evidence pass could not confirm, from its own sentence:
    select_buildings / city_record / low_rise / height_implied / listing_site_only / not_confirmed."""
    t = str(evidence_text or "").lower()
    if re.search(r"select buildings|some buildings|only in some|which buildings", t):
        return "select_buildings"
    if re.search(r"city's record|walk-?up apartments|building class", t):
        return "city_record"
    if re.search(r"townhome|town home|garden[- ]style|low-rise", t):
        return "low_rise"
    if re.search(r"amenity tag only|feature list|does not mention an elevator|no 'elevator' entry|not in the owner", t):
        return "listing_site_only"
    if re.search(r"high-rise|implied|\d+ floors|six-story|th[- ]floor|floors \d", t):
        return "height_implied"
    return "not_confirmed"


def dogs_open_code(evidence_text) -> str:
    """Sub-code of a dog policy that is not confirmed: case_by_case / ask_policy / dogs_not_named / not_reread /
    listing_site_only / not_confirmed."""
    t = str(evidence_text or "").lower()
    if re.search(r"upon approval|case by case|on approval", t):
        return "case_by_case"
    if re.search(r"contact for more information|contact for the pet policy", t):
        return "ask_policy"
    if re.search(r"dogs not named|dogs are not named|small pets", t):
        return "dogs_not_named"
    if re.search(r"blocked|not re-read|could not be read again", t):
        return "not_reread"
    if re.search(r"trulia pet field|zumper|listing site", t):
        return "listing_site_only"
    return "not_confirmed"


# ---- independent check 4, D20: "up to 2 months free" is not "2 months free"
_UP_TO_FREE = re.compile(r"\bup to\s+(?:\w+[\s-]+){0,3}?(?:\d+(?:\.\d+)?|one|two|three|four|six|eight)[\s-]*(?:months?|weeks?|mos?\b)", re.I)


def offer_is_up_to(conditions="", offer_text="", free_months="") -> bool:
    """True when the free-rent offer is an 'up to' amount: rent_terms.py recorded it among the conditions, the free
    months are a range ('1-2'), or the page's own offer text says 'up to N months / weeks' ('RECEIVE UP TO 2 MONTHS
    FREE ON BASE RENT', 'Up to 1 MONTH FREE', 'up to 6-Weeks Base Rent FREE')."""
    if "'up to'" in str(conditions or "") or re.fullmatch(r"\s*[\d.]+\s*-\s*[\d.]+\s*", str(free_months or "")):
        return True
    return bool(_UP_TO_FREE.search(str(offer_text or "")))


# ---- independent check 4, D9: doorman and concierge are separate amenities, each only from text that says so
_STAFF_VETO = r"virtual (?:doorman|door ?person|concierge)|package concierge|concierge trash|trash concierge|valet trash|video (?:door|intercom)|electronic door|cyber ?door|tele-?door"


def staff_named(text, fact="") -> dict:
    """Who staffs the front of the building according to ONE source sentence: {'doorman': '' | 'yes' | '24h',
    'concierge': ..., 'front_desk': ...}.
      doorman     the text says doorman / door person / door man
      concierge   the text says concierge (87 shown apartments in 20 buildings had 'Concierge' in an amenity list and
                  were written up as 'a doorman at the front door')
      front_desk  an attended lobby, a welcome or front desk, 'staffed', or a bare 'yes' under a fact that names neither
    A negative ('no doorman stated', 'none listed') and a virtual doorman say nothing. `fact` is the evidence fact's name:
    'concierge: yes' names a concierge; 'doorman: yes' with no other word is only a staffed front."""
    t = str(text or "").strip().lower()
    out = {"doorman": "", "concierge": "", "front_desk": ""}
    if is_blank(t):
        return out
    t2 = re.sub(_STAFF_VETO, " ", t)
    t2 = re.sub(r"\bvirtual\b", " ", t2)
    if re.search(_NEG, t2) or re.search(r"\bno (?:doorman|concierge|door ?person)", t2):
        return out
    h24 = "24h" if re.search(r"24", t2) else "yes"
    f = str(fact or "").strip().lower()
    if re.search(r"door ?m[ae]n|door ?person|door ?people", t2):
        out["doorman"] = h24
    if re.search(r"concierge", t2) or (f.startswith("concierge") and re.search(r"\byes\b|24|daytime|full[- ](?:time|service)", t2)):
        out["concierge"] = h24
    if not out["doorman"] and not out["concierge"] and re.search(r"attended|staffed|welcome desk|front desk|lobby (?:staff|attendant)|\byes\b|24|daytime|full[- ](?:time|service)", t2):
        out["front_desk"] = h24
    return out


def staff_from_sources(texts) -> dict:
    """staff_named over every source sentence of a building (' || '-joined or a list): the strongest finding per kind."""
    parts = texts if isinstance(texts, (list, tuple)) else str(texts or "").split(" || ")
    out = {"doorman": "", "concierge": "", "front_desk": ""}
    for p in parts:
        for k, v in staff_named(p).items():
            if v == "24h" or (v and not out[k]):
                out[k] = v
    if out["doorman"] or out["concierge"]:
        out["front_desk"] = ""
    return out


# ---- independent check 4, D18: every kind of parking a sentence names
def parking_kinds(text) -> list:
    """['lot', 'garage'] for 'surface parking; optional garages, rate not stated': each kind the sentence names, the
    plainest first (street, lot, covered, garage, offsite). parking_kind() gives only the best one, which is what the
    score uses; the page must not call a building with a lot and optional garages 'garage parking'."""
    t = re.sub(r"^[a-z_ ]+:\s*", "", str(text or "").lower())
    full = str(text or "").lower()
    out = []
    if OFFSITE_PARKING.search(full):
        return ["offsite"]
    if re.search(r"\bstreet\b", t) and not re.search(r"off[- ]street", t):
        out.append("street")
    if re.search(r"\blot\b|surface|off[- ]street|assigned|on[- ]site|outdoor|outside|open parking|uncovered|open_lot|surface_lot", t):
        out.append("lot")
    if re.search(r"(?<!un)covered|carport", t):
        out.append("covered")
    if re.search(r"garage|gated|underground|indoor|\bdeck\b", t) and not re.search(r"no garage", t):
        out.append("garage")
    if not out and parking_kind(full):
        out.append(parking_kind(full))
    return out


def garage_is_optional(text) -> bool:
    """True when the sentence names a lot or surface parking AND a garage that is an optional extra, an add-on or
    priced separately ('surface parking; optional garages', 'Open lot: included in lease; Underground parking garage:
    $50/month', 'open lot included in lease; covered garage also listed')."""
    k = parking_kinds(text)
    t = str(text or "").lower()
    return "lot" in k and ("garage" in k or "covered" in k) and bool(re.search(r"optional|also listed|add-on|additional|included in lease|free surface|\$\d", t))


def manager_name(text) -> str:
    """The manager's NAME for the page from the merged manager note: 'Greystar (site footer links to greystar.com)' ->
    'Greystar'; 'Jones Street Residential (Trulia capture); batch file says Konover ...' -> 'Jones Street Residential';
    'listed by Blue Chip Real Estate Group LLC (broker); manager not stated' -> '' (no manager is named).
    The note itself is internal: it records where the name was read."""
    t = str(text or "").strip()
    if is_blank(t) or re.match(r"(?i)listed by\b|manager not|not stated|unknown", t):
        return ""
    n = re.split(r"\s*[;(]", t, 1)[0].strip(" ,.-")
    return n if 2 <= len(n) <= 70 else ""


def title_unit(building_name) -> str:
    """'312' from a property title that names its apartment ('416 Highland Ave - 312', '20 Main St #4B'), else ''."""
    m = re.search(r"\s(?:-|#)\s*#?(\d{1,4}[a-z]?)\s*$", str(building_name or ""), re.I)
    return m.group(1).upper() if m and _TITLE_UNIT.search(str(building_name or "")) else ""


# ---------------------------------------------------------------------------- dog amenities and laundry, structured
# 2026-11-16 (pipeline clean-up). `dog_amenities` was whichever source ranked highest, so a management page's bare
# "yes" hid the listing site's "Dog park", and the page counted a pet spa, a dog wash and that bare "yes" as a dog area.
# `in_unit_laundry = yes` could sit beside a laundry text from another source that said "On-site laundry". Both are
# now derived from EVERY source's own words.
_DOG_NEG = re.compile(r"\bno (?:dog |pet )?(?:run|park|area|amenit\w+)\b[^;|.]*|\bno_mention\b|\bnone (?:listed|stated)\b", re.I)
_DOG_RUN = re.compile(r"\b(?:dog|pet|puppy|pup)[- ]?runs?\b(?! (?:off|free|around|loose)\b)", re.I)      # not "let your dog run off leash"
_DOG_PARK = re.compile(r"\b(?:dog|bark|pet|pooch|paw|puppy|pup|canine)[- ]?(?:parks?|yards?)\b|\boff[- ]leash (?:dog |pet )?(?:area|park|space|yard|run)\b|"
                       r"\bfenced(?:[- ]in)? (?:dog|pet) (?:area|yard|space)\b|\b(?:dog|pet) (?:play|exercise) ?(?:area|yard|space|ground)s?\b", re.I)
_DOG_SPA = re.compile(r"\b(?:pet|dog|paw|puppy)[- ]?(?:spa|salon)s?\b|\bgroom\w*", re.I)
_DOG_WASH = re.compile(r"\b(?:dog|pet|paw|puppy)[- ]?(?:wash\w*|bath\w*|shower\w*)\b|\bwash(?:ing)? station\b", re.I)
# a dog park the sentence places OUTSIDE the property ("steps from the dog park", "the city's dog park") is not the building's
_DOG_ELSEWHERE = re.compile(r"\b(?:near(?:by|est)?|close to|steps? (?:from|to)|minutes? (?:from|to|away)|walk(?:ing)?(?: distance)? to|across (?:the street )?from|"
                            r"next to|adjacent to|blocks? (?:from|to|away)|public|city|county|municipal|town|neighbou?rhood|local)\b[^.;|]{0,40}$", re.I)
_DOG_ELSEWHERE_AFTER = re.compile(r"\W*(?:is |are )?(?:close by|nearby|near\b|around the corner|down the (?:street|block|road)|across the|a short|within walking|just (?:steps|minutes|blocks))", re.I)


def dog_amenity_facts(texts) -> dict:
    """What a building's own dog amenities are, from every source's words (a string or a list of strings: the amenity
    value and the sentence or tag it was read from).

      dog_park_or_run   a source names a dog park, dog run, bark park, pet park or fenced / off-leash dog area ON the property
      pet_spa_or_wash   a source names a pet spa, grooming room, dog wash or washing station
      unspecified       a source says there is a dog amenity ("yes", "pet amenities") and none says what it is
      label             'dog run; dog park; pet spa; dog wash' in that order, or 'yes' when unspecified, or ''

    'pet washing station; no dog run listed' is a dog wash only. A dog park "steps from" the building is not its own."""
    if isinstance(texts, str) or texts is None:
        texts = [texts]
    run = park = spa = wash = said = False
    for raw in texts:
        t = str(raw or "").strip()
        if is_blank(t):
            continue
        t = _DOG_NEG.sub(" ", t)
        if not t.strip(" ;|."):
            continue
        for seg in re.split(r"\s*(?:\|\||;)\s*", t):
            if not seg.strip() or re.match(_NEG, seg.strip().lower()):
                continue
            # "there is one" with no kind: a bare yes, or "pet amenities"; a long sentence that names nothing is not a claim
            said = said or bool(re.match(r"\s*(?:yes|true|y)\b", seg, re.I) or re.search(r"\b(?:pet|dog)[- ](?:friendly )?amenit", seg, re.I))
            for rx, kind in ((_DOG_RUN, "run"), (_DOG_PARK, "park")):
                for m in rx.finditer(seg):
                    if _DOG_ELSEWHERE.search(seg[:m.start()]) or _DOG_ELSEWHERE_AFTER.match(seg[m.end():]):
                        continue
                    if kind == "run":
                        run = True
                    else:
                        park = True
            spa = spa or bool(_DOG_SPA.search(seg))
            wash = wash or bool(_DOG_WASH.search(seg))
    names = [n for n, on in (("dog run", run), ("dog park", park), ("pet spa", spa), ("dog wash", wash)) if on]
    unspecified = said and not names
    return {"dog_park_or_run": run or park, "pet_spa_or_wash": spa or wash, "unspecified": unspecified,
            "label": "; ".join(names) if names else ("yes" if unspecified else "")}


_L_HOOKUP = re.compile(r"hook-?ups?|connections?\b", re.I)
_L_NOT_IN = re.compile(r"\bnot in[ -]?(?:the |an? )?(?:unit|apartment|building)\b|\bno in[ -]?unit\b|\bnone in (?:the )?(?:unit|building)\b|"
                       r"\bin[- ]unit only in\b|\bnot in[- ]unit\b", re.I)
_L_IN = re.compile(r"\bin[ _-]?(?:unit|home|suite|apartment|residence)\b|\bin (?:each|every|your|the|all) (?:unit|home|apartment|residence|suite)s?\b|"
                   r"^\W*(?:washer|dryer)\b|\bwasher ?(?:/|&|and|,) ?dryer\b|\bwashers? (?:&|and) dryers?\b|\bw/d\b|\bfull[- ]?size(?:d)? (?:\w+ )?(?:washer|laundry)|"
                   r"\bstack(?:ed|able) (?:washer|laundry)|\bprivate (?:laundry|washer)|\b(?:your|their) own (?:washer|laundry)|\bpersonal washer", re.I)
_L_SHARED = re.compile(r"\bon[ _-]?site\b|\bshared?\b|\bcommon\b|\bcommunity laundry\b|\blaundry (?:room|facilit\w+|cent(?:er|re)|lounge)s?\b|\bin (?:the )?building\b|"
                       r"\bat (?:the )?building\b|\bbasement\b|\b(?:every|each) floor\b|\b24 ?hr laundry\b|\bcoin\b|\bcard[- ]operated\b|\blaundromat\b", re.I)
_L_SELECT = re.compile(r"\bselect\b|\b(?:in|for|on) some\b|\bsome (?:units|apartments|homes|residences|plans|floor ?plans)\b|\boptional\b|"
                       r"\bavailable (?:in|for|upon)\b|\bfor rent\b|\bper plan\b", re.I)
_L_WORD = re.compile(r"\bwashers?\b|\bdryers?\b|\blaundry\b|\bw/?d\b", re.I)


def laundry_source_flags(text, amenity_value="") -> set:
    """What ONE source says about laundry: a subset of {'in', 'select', 'not_in', 'hookups', 'shared'}.
    `amenity_value` is the parsed column that came with the words ('yes' = the amenities parser read the words as
    in-unit; 'on_site_only' = it read them as a shared room)."""
    t = str(text or "").strip()
    out = set()
    if is_blank(t) and is_blank(amenity_value):
        return out
    t = re.sub(r"^\[[^\]]*\]\s*", "", t)                           # the amenities parser's label: "[unit amenity] In unit laundry"
    t = re.sub(r"(?i)\bdish ?washers?\b", " ", t)                   # "Dishwasher In Every Unit" is not a washer
    from_page = not is_blank(amenity_value)                        # a sentence of a page: it must name laundry itself
    for seg in re.split(r"\s*(?:\|\||;)\s*", t):
        s = seg.strip()
        if not s:
            continue
        if _L_NOT_IN.search(s):
            out.add("not_in")
            if _L_SHARED.search(_L_NOT_IN.sub(" ", s)):
                out.add("shared")
            continue
        if _L_HOOKUP.search(s):
            out.add("hookups")
            s = re.sub(r"(?:washer|w/?d)[^,;]{0,20}hook-?ups?|hook-?ups?[^,;]{0,25}", " ", s, flags=re.I)
        shared = bool(_L_SHARED.search(s))
        if shared:
            out.add("shared")
        m = _L_IN.search(s)
        # "washer and dryer at building", "on-site laundry center": machines named, but in a shared room
        if m and not (shared and not re.search(r"\bin[ _-]?(?:unit|home|suite|apartment|residence)\b|\bin (?:each|every|your|the|all) (?:unit|home|apartment|residence|suite)", s, re.I)):
            if not from_page or _L_WORD.search(s):
                out.add("select" if _L_SELECT.search(s) else "in")
    v = str(amenity_value or "").strip().lower()
    if v == "yes" and not out & {"in", "select", "not_in"} and _L_WORD.search(t):
        out.add("in")                                              # the parser's reading stands where the words give no more
    if v == "on_site_only":
        out.add("shared")
    return out


def laundry_is_appliance_tag(text) -> bool:
    """True for a bare appliance list of a listing site: 'Washer, Dryer', 'Washer',
    '[features: Interior Features > Appliances & Utilities] Dryer'. 'In unit laundry', 'in_unit' and any sentence that
    says the machines are in the apartment are not."""
    t = str(text or "").strip()
    if re.search(r"Appliances\s*&\s*Utilities", t, re.I):
        return True
    t = re.sub(r"^\[[^\]]*\]\s*", "", t).strip().lower()
    return bool(re.fullmatch(r"(?:washer|dryer|washer\s*/\s*dryer)(?:\s*[,;&]\s*(?:washer|dryer))*\.?", t))


def laundry_facts(sources) -> dict:
    """The building's laundry, from every source: `sources` is a list of (text, basis, amenity_value).

      in_unit   'yes'                 a source says the washer / dryer or the laundry is IN the apartment, and no source says it is not
                'select_apartments'   only "select apartments" have it
                'on_site_only'        a shared laundry room and nothing in the apartment
                ''                    not known
      hookups   a source names washer / dryer hookups (hookups alone are not a washer)
      on_site   a source names a shared laundry room in the building
      names_both  an in-apartment source names a washer AND a dryer
      label     the plain words the page data carries beside the flag

    A source that says "not in unit" settles it against a listing site's tag, unless a source of better basis (a
    phone call, a checker's reading: 'confirmed') says in the apartment."""
    best = {"confirmed_by_phone": 0, "confirmed": 1}
    said_in, said_not, select, hook, shared, both = [], [], False, False, False, False
    tag_only, washer, dryer = True, False, False          # independent check 5, N6: is every in-apartment source a bare appliance list?
    for text, basis, val in sources:
        f = laundry_source_flags(text, val)
        rank_ = best.get(str(basis), 5)
        if "in" in f:
            said_in.append(rank_)
            t = str(text or "").lower()
            both = both or bool(re.search(r"washer|\bw/d\b", t) and re.search(r"dryer|\bw/d\b", t))
            t_ = re.sub(r"(?i)\bdish ?washers?\b", " ", t)
            washer = washer or bool(re.search(r"washer|\bw/d\b|laundry", t_))
            dryer = dryer or bool(re.search(r"dryer|\bw/d\b|laundry", t_))
            tag_only = tag_only and laundry_is_appliance_tag(text)
        if "not_in" in f:
            said_not.append(rank_)
        select = select or "select" in f
        hook = hook or "hookups" in f
        shared = shared or "shared" in f
    yes = bool(said_in) and (not said_not or min(said_in) < min(said_not))
    in_unit = "yes" if yes else "select_apartments" if (select and not said_not) else "on_site_only" if shared else ""
    parts = [("In-unit washer and dryer" if both else "In-unit laundry")] if yes else ["In-unit laundry in select apartments"] if in_unit == "select_apartments" else []
    if shared:
        parts.append("on-site laundry room" if parts else ("On-site laundry room, not in the apartment" if said_not else "On-site laundry room"))
    elif said_not and not yes:
        parts.append("No laundry in the apartment")
    if hook:
        parts.append("W/D hookups" if parts else "W/D hookups only")
    tag = yes and tag_only
    appliances = ("washer and dryer" if (washer and dryer) else "washer" if washer else "dryer" if dryer else "") if yes else ""
    if tag and appliances in ("washer", "dryer"):
        parts[0] = f"In-unit {appliances} (no {'dryer' if appliances == 'washer' else 'washer'} named)"
    return {"in_unit": in_unit, "hookups": hook, "on_site": shared, "names_both": both and yes, "label": "; ".join(parts),
            # 'appliance_list': the only source is a listing site's appliance list ('Washer, Dryer'), which does not say the
            # machines are in the apartment; 'says_in_apartment': a page's own words say so
            "basis": ("appliance_list" if tag else "says_in_apartment") if yes else "", "appliances": appliances}


# ---- independent check 5, N1 / D18 / N8: structured parking from EVERY source's own words
PARKING_KIND_RANK = {"garage": 4, "gated_lot": 4, "covered": 3, "assigned_lot": 2, "open_lot": 2, "off_street": 2, "assigned": 2, "offsite": 2, "street": 1}
PARKING_KIND_ORDER = ["street", "off_street", "assigned", "open_lot", "assigned_lot", "covered", "gated_lot", "garage", "offsite"]
PARKING_KIND_WORDS = {"garage": "garage", "gated_lot": "gated lot", "covered": "covered parking", "assigned_lot": "assigned space in an open lot",
                      "open_lot": "open lot", "off_street": "off-street parking", "assigned": "assigned space, kind not stated",
                      "offsite": "off-site parking", "street": "street parking", "unspecified": "parking, kind not stated"}
# the first word of `parking_type`, which the text system reads: garage / covered / lot / street_only; anything else is "parking on site"
PARKING_LEGACY_HEAD = {"garage": "garage", "gated_lot": "garage", "covered": "covered", "assigned_lot": "lot", "open_lot": "lot", "off_street": "lot",
                       "assigned": "assigned", "street": "street_only", "offsite": "offsite", "unspecified": "parking"}
_PK_SKIP_ATOM = re.compile(r"\bguest|visitor|motorcycle|bicycle|\bbike|not stated on the page|no parking line|not_found|\bstation\b(?! )", re.I)
_PK_EXTRA = re.compile(r"additional (?:cost|fee|charge|monthly fee)|addtional fee|optional|extra fee|for a fee|\(fee\)|\(paid\)|\bpaid\b|at an? (?:additional|extra)|charges apply|also listed", re.I)
PARKING_BASIS_WORDS = {"confirmed_by_phone": "by phone", "confirmed": "read on the page by a checker", "community_page": "the building's own page",
                       "amenities_page": "an amenity list or description on a listing or building page", "stated": "the listing",
                       "resident_review": "a resident's review", "reviewed": "reviewed against every source"}
_PK_PREC = ["confirmed_by_phone", "confirmed", "community_page", "amenities_page", "official_record", "stated", "resident_review", "inferred"]
_PK_PLAIN = ("open_lot", "assigned_lot", "off_street", "assigned")


def parking_atom_kind(atom) -> str:
    """One kind for one short phrase of a parking source ('Garage Lot', 'surface_lot', 'Assigned Outside Parking',
    'Unassigned off-street parking'): garage, gated_lot, covered, assigned_lot, open_lot, off_street, offsite, street,
    assigned (an assigned space, place not said); 'unspecified' (parking named, kind not said), or ''."""
    a = re.sub(r"[_]+", " ", str(atom or "").lower()).strip()
    if not a or _PK_SKIP_ATOM.search(a) or re.search(r"no garage|garages? (?:available|coming) soon", a):
        return ""
    if OFFSITE_PARKING.search(a) or re.search(r"nearby (?:parking )?deck|sister property|no on-site parking", a):
        return "offsite"
    if re.search(r"garage|underground|indoor|\bparking deck\b|enclosed", a):
        return "garage"
    gated = bool(re.search(r"gated (?:parking|lot|area|surface|covered)|parking[^,;]{0,20}gated", a)) and not re.search(r"outside of (?:the )?gated", a)
    if re.search(r"(?<!un)covered|carports?", a):
        return "garage" if gated else "covered"
    if gated:
        return "gated_lot"
    if re.search(r"\blots?\b|surface|outdoor|outside|open parking|uncovered", a):
        return "assigned_lot" if re.search(r"\bassigned|reserved|designated", a) and not re.search(r"unassigned", a) else "open_lot"
    if re.search(r"off[- ]street|on[- ]?site parking|onsite parking|^\s*on[- ]?site\s*$", a):
        return "off_street"
    if re.search(r"street parking|on[- ]street|street only", a):
        return "street"
    if re.search(r"(?<!un)assigned|reserved|designated", a) and (re.search(r"park|space|spot", a) or a.strip() in ("assigned",)):
        return "assigned"
    return "unspecified" if re.search(r"\bparking\b|\bvalet\b|\bspaces?\b|\bspots?\b", a) else ""


def _pk_atoms(text):
    return [x for x in re.split(r"[;|\n,/]|\.\s+|\band\b|\bor\b|\bplus\b|:\s|=", str(text or "")) if x.strip()]


def _pk_clause_kinds(clause):
    out = []
    for a in _pk_atoms(clause):
        k = parking_atom_kind(a)
        if k and k not in out:
            out.append(k)
    return out


def parking_facts(sources, fee=None) -> dict:
    """Structured parking of one building from every source's own words.

    sources: [(text, basis, source, origin)], any order. fee: the monthly parking fee the cost uses (0 = a space is
    included or free; None = not published), as resolved by parse_parking and the merge.
    Returns
      kinds           every kind a source names, plainest first
      primary_kind    the kind she would actually park in: the included kind when a space is free; the kind the counted
                      fee pays for; otherwise the best kind named, leaving out a garage or covered space that is only an
                      optional extra beside a plain lot
      included_kind   which kind the free / included space is ('' when no space is included; 'unspecified' when a space
                      is included and no source says of which kind)
      included_quote, included_basis
      optional        [{kind, fee|None, fee_high, label}] other kinds offered for a fee
      fee_kind        the kind the counted fee belongs to
      kind_basis      {kind: best basis that names it}
      assigned        a source says the space is assigned
    A free open lot is never a garage: 'Open lot: included in lease; Underground parking garage: $50/month' gives
    included_kind open_lot, primary_kind open_lot, optional [garage $50]."""
    order = {b: i for i, b in enumerate(_PK_PREC)}
    src = sorted([s_ for s_ in sources if not is_blank(s_[0])], key=lambda s_: order.get(s_[1], 9))
    kinds, kind_basis, assigned, extra, options, incl = [], {}, False, set(), [], []
    unpriced = set()                                        # kinds named somewhere other than a price label
    named = False
    for text, basis, _url, origin in src:
        t = re.sub(r"\[[^\]]{0,60}\]", " ", str(text))
        t = re.sub(r"Parking\s*&\s*Garage\s*[/:]?", " ", t)                     # a section heading of the listing site, not a garage
        if origin == "amenities page":
            t = re.sub(r"^(?:garage|covered|lot|street|offsite|open_lot|street_only|parking_type_unknown):\s+", "", t)   # the amenities parser's own class
        if re.match(r"\s*included:\s*no\b", t, re.I):
            continue
        for clause in re.split(r";|\||\n| / |\.\s+", t):
            ck = _pk_clause_kinds(clause)
            named = named or bool(ck)
            cl = clause.lower()
            priced_clause = bool(re.search(r"\$\s*\d|\bfee\b|:\s*\d", cl))
            for k in ck:
                if k == "unspecified":
                    continue
                if k not in kinds:
                    kinds.append(k)
                kind_basis.setdefault(k, basis)
                if k in ("assigned_lot", "assigned"):
                    assigned = True
                if not priced_clause:
                    unpriced.add(k)
            real = [k for k in ck if k in PARKING_KIND_RANK]
            if _PK_EXTRA.search(cl):
                if real and all(PARKING_KIND_RANK[k] >= 3 for k in real):
                    extra.update(real)                                           # 'Covered or garage parking ... at an additional cost'
                else:
                    for a in _pk_atoms(clause):                                  # 'surface parking, there is optional garage parking'
                        if _PK_EXTRA.search(a.lower()) and parking_atom_kind(a) in PARKING_KIND_RANK:
                            extra.add(parking_atom_kind(a))
            if re.search(_FREE_NEAR, cl) and not re.search(_PROMO, cl) and not re.search(r"not included|included:\s*no|included\s*=\s*false|no free|fee not|^\s*special features|months? free|months? of complimentary", cl):
                head_ = re.split(r"\$\s*\d", clause)[0]                          # the part before any price says what is free
                hk = [k for k in _pk_clause_kinds(head_) if k in PARKING_KIND_RANK]
                incl.append((hk, re.sub(r"\s+", " ", head_).strip(" :,-."), basis))
        opts_ = [x for part in re.split(r"\s/\s|\|", t) for x in parse_parking(part)["options"].split("; ") if x and "(no charge)" not in x]
        for o in opts_:
            m = re.search(r"\$(\d+(?:\.\d+)?)(?:-\$(\d+(?:\.\d+)?))?\s*$", o)
            if not m:
                continue
            label = o[:m.start()].strip(" :,-")
            if re.search(_SECOND, label.lower()) or re.search(r"tandem|motorcycle|permit fee", label.lower()):
                continue
            lk = [k for k in _pk_clause_kinds(label) if k in PARKING_KIND_RANK]
            if not lk and len(opts_) == 1:
                tk = [k for k in _pk_clause_kinds(t) if k in PARKING_KIND_RANK and k != "street"]
                lk = tk if len(tk) == 1 else []
            options.append({"kind": lk[-1] if lk else "unspecified", "fee": float(m.group(1)), "hi": float(m.group(2)) if m.group(2) else None, "label": label, "basis": basis})
    # 'Covered parking fee ($150)' is a listing site's label for a garage fee too: a covered kind named only on a price
    # label folds into the kind the other sources name (the garage, else the lot), unless both are priced apart
    if "covered" in kinds and "covered" not in unpriced:
        cov_fees = {o["fee"] for o in options if o["kind"] == "covered"}
        gar_fees = {o["fee"] for o in options if o["kind"] == "garage"}
        target = "garage" if "garage" in kinds else next((k for k in ("gated_lot", "open_lot", "assigned_lot") if k in unpriced), "")
        if target and not (target == "garage" and gar_fees - cov_fees and cov_fees - gar_fees) and not (target != "garage" and any(o["kind"] == target for o in options)):
            kinds = [k for k in kinds if k != "covered"]
            extra.discard("covered")
            for o in options:
                if o["kind"] == "covered":
                    o["kind"] = target
    f = None if fee is None or (isinstance(fee, float) and fee != fee) or str(fee).strip() == "" else float(fee)
    priced = {o["kind"] for o in options}
    included_kind, included_quote, included_basis = "", "", ""
    if f == 0:
        single = [x for x in incl if len(x[0]) == 1]
        if single:
            included_kind, included_quote, included_basis = single[0][0][0], single[0][1], single[0][2]
        else:
            cand = [k for k in kinds if k not in extra and k != "street" and k not in priced]
            included_kind = cand[0] if len(cand) == 1 else "unspecified"
            if incl:
                included_quote, included_basis = incl[0][1], incl[0][2]
    if included_kind != "off_street" and any(k not in ("off_street", "street") for k in kinds):
        kinds = [k for k in kinds if k != "off_street"]        # 'Off Street Parking' beside a named garage or lot adds no kind
    if included_kind != "assigned" and any(k not in ("assigned", "street", "off_street") for k in kinds):
        kinds = [k for k in kinds if k != "assigned"]          # 'Assigned Parking' beside a named kind is an attribute, not a kind
    kinds = sorted(dict.fromkeys(kinds), key=PARKING_KIND_ORDER.index)
    here = [k for k in kinds if k != "street"]
    best = lambda ks: max(ks, key=lambda k: (PARKING_KIND_RANK[k], PARKING_KIND_ORDER.index(k))) if ks else ""
    plainest = lambda ks: min(ks, key=lambda k: (PARKING_KIND_RANK[k], PARKING_KIND_ORDER.index(k))) if ks else ""
    fee_kind = ""
    if f is not None and f > 0:
        hit = [o["kind"] for o in options if abs(o["fee"] - f) < 0.01 and o["kind"] in kinds]
        fee_kind = best(hit) or best(here)
    if f == 0:
        if included_kind in PARKING_KIND_RANK:
            primary = included_kind
        else:
            primary = plainest([k for k in here if k not in extra and k not in priced] or here) or "unspecified"
    elif f is not None:
        primary = fee_kind or "unspecified"
    else:
        rest = [k for k in here if k not in extra]
        primary = (best(rest) if any(k in _PK_PLAIN for k in rest) else best(here)) or best(kinds) or ("unspecified" if named else "")
    optional, seen_k = [], set()
    for o in sorted(options, key=lambda o: (order.get(o["basis"], 9), o["fee"])):
        k = o["kind"]
        if k not in kinds or k in ("off_street", "assigned") or k in seen_k:
            continue
        if k == primary and not (f == 0 and o["fee"] > 0):
            continue
        seen_k.add(k)
        optional.append({"kind": k, "fee": o["fee"], "fee_high": o["hi"], "label": o["label"]})
    for k in sorted(extra, key=PARKING_KIND_ORDER.index):
        if k != primary and k not in seen_k and k in kinds:
            optional.append({"kind": k, "fee": None, "fee_high": None, "label": ""})
    return {"kinds": kinds, "primary_kind": primary, "included_kind": included_kind, "included_quote": included_quote[:200],
            "included_basis": included_basis, "optional": optional, "fee_kind": fee_kind if (f is not None and f > 0) else (included_kind if f == 0 else ""),
            "kind_basis": {k: kind_basis.get(k, "") for k in kinds}, "assigned": assigned}


def parking_kind_rank(kind):
    """The 'parking type' score of the Car part and the night moment: what she would actually park in."""
    return PARKING_KIND_RANK.get(str(kind or ""), float("nan"))


_PK_HEADS = {"garage": "garage", "covered": "covered", "lot": "lot", "assigned": "lot", "street_only": "street", "offsite": "offsite", "parking": ""}
_PK_HEAD_RANK = {"garage": 4, "covered": 3, "lot": 2, "assigned": 2, "offsite": 2, "street_only": 1}


def parking_type_head(text) -> str:
    """The head of a structured `parking_type` ('lot: Open parking: included in lease; Garage: $125' -> 'lot'), or ''
    when the text is not headed (a raw source sentence). build_master writes the head from parking_facts: it names the
    space she would actually park in, whatever else the sentence mentions."""
    m = re.match(r"\s*(garage|covered|lot|assigned|street_only|offsite|parking)\s*(?::|$)", str(text or "").lower())
    return m.group(1) if m else ""


def parking_type_kind(text) -> str:
    """parking_kind() for a headed `parking_type` (the head decides), else for a raw sentence."""
    h = parking_type_head(text)
    return _PK_HEADS[h] if h else parking_kind(text)


def parking_type_rank(text):
    """4 garage or gated, 3 covered, 2 lot / assigned / off-site, 1 street, nan unknown: from the head when there is one."""
    h = parking_type_head(text)
    if h:
        return _PK_HEAD_RANK.get(h, float("nan"))
    return None


def parking_type_text(primary_kind, old_type) -> str:
    """`parking_type` as stored: '<head>: <the source's words>'. The words are the old value without the class our own
    code had put in front of it."""
    old = str(old_type or "").strip()
    if not primary_kind:
        return old
    words = re.sub(r"^(?:garage|covered|lot|street|offsite|open_lot|open lot|street_only|assigned|parking)\s*(?::\s*|$)", "", old, flags=re.I).strip()
    head = PARKING_LEGACY_HEAD.get(primary_kind, "parking")
    return f"{head}: {words}" if words else head


_PK_NOUN = {"garage": "Garage parking", "gated_lot": "A gated lot", "covered": "Covered parking", "assigned_lot": "An assigned space in an open lot",
            "open_lot": "An open lot", "off_street": "Off-street parking", "assigned": "An assigned space (the listing does not say where)",
            "offsite": "Off-site parking, not at the building", "street": "Street parking only", "unspecified": "Parking, of a kind the listing does not name"}
_PK_FREE = {"garage": "A free garage space", "gated_lot": "A free space in a gated lot", "covered": "A free covered space", "assigned_lot": "A free assigned space in an open lot",
            "open_lot": "A free open lot", "off_street": "Free off-street parking", "assigned": "A free assigned space (the listing does not say where)",
            "offsite": "Free off-site parking", "unspecified": "A free parking space (the listing does not say what kind)"}
_PK_EXTRA_NOUN = {"garage": "garage spaces", "gated_lot": "spaces in the gated lot", "covered": "covered spaces", "assigned_lot": "assigned outdoor spaces",
                  "open_lot": "other open-lot spaces", "offsite": "off-site spaces"}


def _usd(x):
    return f"${float(x):,.0f}" if abs(float(x) - round(float(x))) < 0.005 else f"${float(x):,.2f}"


def parking_summary(kind, included_kind, fee, optional, fee_is_estimate=False) -> str:
    """One plain sentence from the structured parking, for the page and the text to use exactly:
    'A free open lot; garage spaces are $150 a month.'  'Garage parking, $100 a month.'
    'An open lot, with the fee not published; garage spaces are extra (fee not published).'  '' when nothing is known."""
    kind, included_kind = str(kind or ""), str(included_kind or "")
    if not kind:
        return ""
    f = None if fee is None or (isinstance(fee, float) and fee != fee) or str(fee).strip() == "" else float(fee)
    if kind == "street":
        head = _PK_NOUN["street"]
    elif f == 0:
        head = _PK_FREE.get(included_kind or kind, _PK_FREE["unspecified"])
    elif f is not None:
        head = f"{_PK_NOUN.get(kind, _PK_NOUN['unspecified'])}, " + (f"about {_usd(f)} a month by a resident's review" if fee_is_estimate else f"{_usd(f)} a month")
    else:
        head = f"{_PK_NOUN.get(kind, _PK_NOUN['unspecified'])}, with the fee not published"
    tails = []
    for o in optional or []:
        noun = _PK_EXTRA_NOUN.get(o.get("kind"))
        if not noun or (o.get("kind") == kind and f != 0):
            continue
        if o.get("fee") is None:
            tails.append(f"{noun} are extra (fee not published)")
        elif o.get("fee_high"):
            tails.append(f"{noun} are {_usd(o['fee'])} to {_usd(o['fee_high'])} a month")
        else:
            tails.append(f"{noun} are {_usd(o['fee'])} a month")
    return head + ("; " + "; ".join(tails) if tails else "") + "."


# ---- independent check 5, N5: a dog weight limit is stated only when a page states it
def dog_weight_traced(limit, words) -> bool:
    """True when the stored limit ('50', 'no limit') can be read in one of the sources' own words: the listing's pet
    policy text, the building's page, a checker's quote. A number with no page behind it ('small dogs' stored as 25 lb,
    the gate's threshold) is not a published limit."""
    lim = str(limit or "").strip().lower()
    if not lim:
        return True
    text = " || ".join(str(w) for w in words if not is_blank(w)).lower()
    text = re.sub(r"\([^)]*could not be traced[^)]*\)", " ", text)
    if lim == "no limit":
        return bool(re.search(r"\bno (?:upper |weight |size |pet |breed restrictions or weight )*(?:limits?|restrictions?)\b|restrictions?: none|\bunlimited\b|\bany (?:size|weight)\b"
                              r"|regardless of (?:pet )?(?:size|weight)|not have a weight limit|over \d{2,3} ?lbs?\.? extra|maximumpetweight field (?:is|=) 0", text))
    try:
        n = f"{float(lim):g}"
    except ValueError:
        return True
    return bool(re.search(rf"(?<![\d$.]){re.escape(n)}(?:\.0+)?\s*-?\s*(?:lbs?\b|pounds?|#)|(?:weight|max|limit|under|up to|lbs\.?\))[^|;]{{0,24}}?(?<![\d$.]){re.escape(n)}(?![\d.])", text))


# ---- independent check 5, N4: one-time costs a listing states (broker fee, application fee, move-in fees, a large deposit)
_BLURB = re.compile(r"you can find|if you.{0,3}re lucky|some with no|apartments that have|call \w+ home|wide selection|great for those looking", re.I)
_NO_BROKER = re.compile(r"\bno\s+broker(?:'s|’s|s)?(?:age)?\s+fees?\b|\bno[- ]fee\s+(?:apartment|rental|listing|unit|building)|\breal estate no fee\b|landlord pays the broker|\bno fee\b(?=[!.]|\s*$)", re.I)
_BROKER = re.compile(r"\bbroker(?:'s|’s|s)?(?:age)?\s+fee\b[^.;|!]{0,60}|\bfee apartment\b|\bbroker(?:'s|’s)? commission of[^.;|]{0,40}", re.I)


def broker_fee_statement(text):
    """('applies' | 'none' | '', the sentence) from a listing's own description or a checker's fact.
    'Broker fee.' and 'Broker Fee applies' -> applies; 'NO BROKER FEE', 'No broker's fee', 'Make this NO FEE apartment
    your new home' -> none. A listing site's neighborhood blurb ('some with no broker fee') is not about this apartment."""
    sents = [re.sub(r"\s+", " ", x).strip() for x in re.split(r"(?<=[.!?])\s+|\s[-•*]\s|\n+|\s{2,}|\|", str(text or ""))]
    for sent in sents:
        if not sent.strip() or _BLURB.search(sent):
            continue
        if _NO_BROKER.search(sent):
            return "none", _cut_words(sent.strip(), 160)
    for sent in sents:
        if not sent.strip() or _BLURB.search(sent):
            continue
        m = _BROKER.search(sent)
        if m and not re.search(r"\bno\s+(?:\w+\s+){0,2}$", sent[:m.start()], re.I) and not re.search(r"ask about a broker fee|whether a broker fee", sent, re.I):
            return "applies", _cut_words(sent.strip()[max(0, m.start() - 40):], 160)
    return "", ""


_OTC = [("application fee", r"application(?: fee| payment)?(?: per applicant| \(?per adult[^)]*\)?)?\s*(?:of|:|=|is|\()?\s*\$\s*(\d[\d,]*(?:\.\d\d)?)|\$\s*(\d[\d,]*(?:\.\d\d)?)\s*(?:non-?refundable\s+)?(?:application|tenant screening)(?: fee)?"),
        ("credit-check fee", r"credit check(?: fee)?\s*(?:of|:|=|is|\()?\s*\$\s*(\d[\d,]*)|\$\s*(\d[\d,]*)\s*(?:for |per )?(?:a )?credit check"),
        ("administrative fee", r"admin(?:istrative|istration)?(?: fee)?\s*(?:of|:|=|is|\()?\s*\$\s*(\d[\d,]*)|\$\s*(\d[\d,]*)\s*admin(?:istrative|istration)? fee"),
        ("holding fee", r"holding fee\s*(?:of|:|=|is|\()?\s*\$?\s*(\d[\d,]*(?:\.\d\d)?)|\$\s*(\d[\d,]*)\s*holding fee"),
        ("move-in fee", r"move[- ]in fees?(?: are| is|:| of)?\s*\$\s*(\d[\d,]*)|\$\s*(\d[\d,]*)\s*move[- ]in fee"),
        ("amenity fee (one-time)", r"amenity fee:?\s*\$\s*(\d[\d,]*)\s*(?:per lease term|due at move|one[- ]time)|\$\s*(\d[\d,]*)\s*(?:one[- ]time )?amenity fee (?:per lease term|due at move)")]


def one_time_costs(text) -> dict:
    """One-time costs stated in a listing's description or a checker's fact:
    {'items': ['application fee $50 per applicant', 'holding fee $250'], 'deposit_months': 1.5 | None,
     'deposit_dollars': 3585.0 | None, 'deposit_text': '...'}. Pet fees are not read here (the pet lines have their own
    question). A waived fee ('application fee waived') is not listed."""
    t = re.sub(r"\s+", " ", str(text or ""))
    items = []
    for label, pat in _OTC:
        for m in re.finditer(pat, t, re.I):
            ctx = t[max(0, m.start() - 12):m.end() + 40].lower()
            if re.search(r"waived|\bno application fee|\bno admin", ctx) or re.search(r"\bpet\b|\bdog\b|\bcat\b", t[max(0, m.start() - 25):m.start()].lower()):
                continue
            amt = (m.group(1) or m.group(2)).replace(",", "")
            if not amt or not (1 <= float(amt) <= 2000):
                continue
            per = " per applicant" if label in ("application fee", "credit-check fee") and re.search(r"per (?:applicant|adult|person)|/applicant|each applicant", ctx) else ""
            item = f"{label} ${float(amt):,.0f}{per}"
            if not any(i.split(" $")[0] == label for i in items):
                items.append(item)
    dep_m, dep_d, dep_t, dep_upto = None, None, "", False
    t2 = re.sub(r"(?<=\d)\.(?=\d)", "§", t)                                # '1.5 month' stays one number through the sentence split
    t2 = re.sub(r"one[- ]and[- ]a[- ]half|1 ?1/2", "1§5", t2, flags=re.I)
    t2 = re.sub(r"\btwo(?= months)", "2", re.sub(r"\bone(?= months?)", "1", t2, flags=re.I), flags=re.I)
    num_ = r"(\d(?:§\d)?)"
    for m in re.finditer(r"[^.;|]{0,60}deposit[^.;|]{0,90}", t2, re.I):
        seg = m.group(0)
        if re.search(r"\bpet\b|\bdog\b|\bcat\b|key deposit|holding|reduced|alternative|\$0\b|no (?:security )?deposit|deposit[- ]free", seg, re.I):
            continue
        mm = [x for x in re.findall(num_ + r"\s*-?\s*months?['’]?s?['’]?(?:\s+(?:of\s+)?rent)?(?:\s+as)?\s+(?:security\s+)?deposit", seg, re.I)]
        mm += [x for pair in re.findall(r"deposit[^.;|]{0,50}?" + num_ + r"(?:\s*(?:-|to)\s*" + num_ + r")?\s*-?\s*months?", seg, re.I) for x in pair if x]
        mm += [x for x in re.findall(r"\(" + num_ + r" months?\)", seg, re.I)]
        mm = [float(x.replace("§", ".")) for x in mm]
        dd = [float(x.replace(",", "")) for x in re.findall(r"deposit[^$.;|]{0,25}\$\s*(\d[\d,]{2,})", seg, re.I)
              + re.findall(r"deposit[^$.;|]{0,25}\$\s*\d[\d,]*(?:§\d\d)?\s*(?:-|to)\s*\$?\s*(\d[\d,]{2,})", seg, re.I)
              + re.findall(r"\$\s*(\d[\d,]{2,})(?:§\d\d)?\s*(?:refundable |advance |month )?(?:security )?deposit", seg, re.I)
              + re.findall(r"deposit[^.;|]{0,12}\bmax (\d{3,5})\b", seg, re.I)]
        upto = bool(re.search(r"up to|\bto\b|\d\s*-\s*\$?\d|based on credit|\bmax\b", seg, re.I))
        if mm and (dep_m is None or max(mm) > dep_m):
            dep_m, dep_t, dep_upto = max(mm), seg.strip().replace("§", "."), upto
        if dd and (dep_d is None or max(dd) > dep_d):
            dep_d = max(dd)
            if not dep_m:
                dep_t, dep_upto = seg.strip().replace("§", "."), upto
    return {"items": items, "deposit_months": dep_m, "deposit_dollars": dep_d, "deposit_text": _cut_words(dep_t, 140), "deposit_up_to": dep_upto}


def one_time_costs_sentence(items, deposit_months, deposit_dollars, deposit_up_to, rent) -> str:
    """'application fee $50 per applicant; holding fee $250; a security deposit of 1.5 months' rent' : the one-time costs
    worth a line. The deposit is named only when it is more than one month's rent (months > 1, or dollars above the
    rent). '' when there is nothing to say."""
    parts = [str(i) for i in (items or []) if str(i).strip()]
    f = lambda x: None if x is None or x != x or str(x).strip() == "" else float(x)
    dm, dd, r = f(deposit_months), f(deposit_dollars), f(rent)
    up = "up to " if deposit_up_to else ""
    if dm is not None and dm > 1:
        parts.append(f"a security deposit of {up}{dm:g} months' rent")
    elif dd is not None and r and dd > r * 1.05 and (dm is None):
        parts.append(f"a security deposit of {up}{_usd(dd)}")
    return "; ".join(parts)


def listing_descriptions(raw_text) -> str:
    """The listing's own description text out of a cached page: Trulia's "description":{"value": ...}, Zumper's and
    Apartment List's "description":"..." strings. Site navigation, labels and other listings' cards are left out."""
    out = []
    for m in re.finditer(r'"description"\s*:\s*(?:\{\s*"value"\s*:\s*)?"((?:[^"\\]|\\.){40,20000})"', str(raw_text or "")):
        s = m.group(1)
        try:
            s = json.loads('"' + s + '"')
        except ValueError:
            s = s.replace("\\n", " ").replace('\\"', '"')
        s = re.sub(r"<[^>]+>", " ", s)
        if s not in out:
            out.append(s)
    return "\n".join(out)


# ---- independent check 5, N6: in-unit laundry named only on a listing site's appliance list
def laundry_tag_text(appliances) -> str:
    a = str(appliances or "").strip()
    if a == "washer":
        return "A washer in the apartment is from the listing site's feature list, and no dryer is named: confirm both"
    if a == "dryer":
        return "A dryer in the apartment is from the listing site's feature list, and no washer is named: confirm both"
    return "Washer and dryer in the apartment is from the listing site's feature list: confirm it"


def laundry_tag_question(appliances) -> str:
    return "Is there a washer and a dryer inside the apartment?"
