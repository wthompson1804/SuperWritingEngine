#!/usr/bin/env python3
"""Structured rent terms for every passing unit: data/rent_terms.csv.

Reads data/units.csv (unit_status == pass), each unit's cached page (raw_path) and the evidence
CSVs. No network access. Rule-based: the offer text is kept verbatim and every derived number
carries its formula (computed_how) and a confidence label. Nothing is guessed:

* listed_price_is = net_effective only when a page or an evidence row says so;
  = gross when a page states the gross rent, an evidence row confirms it, or the unit has no
  free-rent offer; otherwise unknown.
* gross_monthly_rent stays empty when the basis is unknown. The two scenario columns
  (gross_if_listed_is_net, net_if_listed_is_gross) show the exposure without claiming a rent.
* first_full_payment_date needs the free-period timing to be stated; otherwise it is empty and
  first_full_payment_note says why.

Rerunnable: rewrites data/rent_terms.csv and docs/harvest_notes/rent_terms.md from scratch.
Usage: python3 scripts/rent_terms.py [--dump]   (--dump prints each distinct offer text + parse)
"""
from __future__ import annotations

import calendar
import csv
import glob
import html as htmllib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNITS = ROOT / "data" / "units.csv"
OUT = ROOT / "data" / "rent_terms.csv"
NOTE = ROOT / "docs" / "harvest_notes" / "rent_terms.md"
EVID = ROOT / "data" / "evidence"
DEFAULT_MOVE_IN = date(2026, 12, 1)       # used when the unit is "available now"
YEAR = 2026

COLS = ["listing_id", "addr_key", "listed_rent", "listed_price_is", "offer_text", "offer_text_page", "offer_type", "free_months",
        "free_period_timing", "lease_months", "gross_monthly_rent", "net_effective_monthly",
        "first_full_payment_date", "first_full_payment_note", "offer_expires", "conditions", "computed_how",
        "confidence", "source_url", "needs_call", "gross_if_listed_is_net", "net_if_listed_is_gross"]

DEC = json.JSONDecoder()

# ------------------------------------------------------------------ text triggers
TRIG = re.compile(
    r"months?['’]?s?\s+(?:of\s+)?(?:rent\s+)?free|free\s+(?:base\s+)?(?:rent|months?)\b|weeks?\s+free|"
    r"net[- ]?effective|gross rent|concession|(?:rent|move[- ]in)\s+(?:credit|bonus)|\bmonths?\s+off\b|"
    r"\$\s?[\d,]+\s+off\b|half\s+(?:a\s+)?month|(?:leasing|move[- ]in|rent|lease)[- ]?\s*(?:special|promotion)s?|"
    r"special offer|incentive|(?:reduced|low)\s+(?:security\s+)?deposit|\$\s?\d+\s+(?:security\s+)?deposit|"
    r"deposit special|waived|month\s+(?:rent\s+)?free|\bfree\*", re.I)
NOT_OFFER = re.compile(r"smoke[- ]free|rent credit, fitness|reward", re.I)

NUMW = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "half": 0.5,
        "half a": 0.5, "1/2": 0.5, "one and a half": 1.5, "1 1/2": 1.5, "a half": 0.5, "one-half": 0.5}
Q = r"(?:\d+(?:\.\d+)?|one and a half|1 1/2|one-half|one|two|three|four|five|six|half(?: a)?|1/2|an?)"
FREE = re.compile(
    r"(?P<upto>up\s+to\s+(?:a\s+)?)?(?<![\d,.$])(?P<q1>" + Q + r")(?:\s*(?:-|–|to|or)\s*(?P<q2>" + Q + r"))?\s*[- ]?\s*"
    r"(?P<unit>month|week)s?(?:['’]s)?\s*[- ]?\s*(?:of\s+)?"
    r"(?:free\b|off\b|rent[- ]free|(?:base\s+)?rent\s+free|rent\s+concession|of\s+free)", re.I)
FREE_SPECIAL = re.compile(r"\b(?P<q>one month and a half|" + Q + r")(?:\s*[- ]?months?)?\s+special\b", re.I)
UNCLEAR = re.compile(r"months?\s+fee\s+rent|rent concession|months?\s+off\b|months?\s+special", re.I)
EV_NET = re.compile(r"'\$\s?([\d,]+)\*?'\s*=\s*net effective", re.I)
FREE_NOQ = re.compile(r"\b(?:first|1st)\s+(?:full\s+)?month(?:['’]s)?(?:\s+(?:of\s+)?(?:base\s+)?rent)?\s+(?:is\s+)?free|"
                      r"\bfree\s+(?:first\s+)?month\b(?!s)|\b13th\s+month\s+(?:rent\s+)?free", re.I)
MONTHNAMES = "january february march april may june july august september october november december".split()
MON = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
FREE_NAMED = re.compile(r"\b(" + MON + r")\.?[- ]?(20\d\d)?\s+(?:rent\s+)?free\b", re.I)
LEASE = re.compile(
    r"(?P<a>\d{1,2})\s*(?:(?:-|–|to)\s*(?P<b>\d{1,2}))?\s*(?P<p1>\+)?\s*[- ]?\s*months?\s*(?P<p2>\+)?"
    r"(?P<p3>\s*or\s*(?:longer|greater|more))?\s*(?:new\s+)?(?:lease|term|in length|mth)|"
    r"\b(?:on(?:\s+an?)?|lease\s+of|for|lease)\s+(?P<c>\d{1,2})\s*months?\b(?P<p4>\s*or\s*(?:longer|greater|more))?(?!\s*(?:of\s+)?(?:free|off|rent))|"
    r"(?P<d>\d{1,2})\s*MTH\b", re.I)
SELECT = re.compile(r"\bselect(?:ed)?\b|\bfew apartment|\bqualif|\bcertain\b|\bparticipating\b", re.I)
RENEW = re.compile(r"\brenew|second year|2nd year", re.I)
NET_STMT = re.compile(r"net[- ]?effective|price includes concessions|after (?:rent )?concessions|"
                      r"inclusive of concessions|reflects? net|net rent", re.I)
# A sentence that says the page does NOT say whether the price is net-effective is not a net-effective statement
# (independent check 2, D14: Beacon Mill Village, Arcade Apartments, Avalon Somerville were costed as net-effective).
NET_NEG = re.compile(r"not the net[- ]effective|based on the gross rent|(?:does not|doesn't|neither page|no page|nor does it) says? whether|"
                     r"whether (?:the |\$[\d,]+ |rent |price )?(?:is |are )?(?:gross or net|net[- ]effective or gross)|gross or net(?:[- ]effective)? not stated|"
                     r"net[- ]effective equals price|not (?:a )?net[- ]effective|discount is on move-in costs|"
                     # independent check 3, D5: the checker's own "the page does not say" sentences, in every wording seen:
                     # "Gross or net-effective: not stated", "not stated as net-effective", "not stated whether the listed
                     # price is gross or net-effective", "gross or net-effective listing price: not stated"
                     r"(?:gross or net|net[- ]effective)[^.;|]{0,60}(?:not stated|unstated|not said|not given|not published|unknown|unclear)|"
                     r"(?:not stated|not said|unstated|does not (?:say|state)|doesn't (?:say|state)|unclear|unknown)[^.;|]{0,60}(?:gross or net|net[- ]effective)|"
                     r"(?:is|are|shows?) (?:the )?base rent\b[^.;|]{0,40}(?:not|no) [^.;|]{0,20}net", re.I)
# Text a checker or harvester wrote ABOUT the page, or raw page data: never shown as the offer's own words (docs/PENDING_FIXES.md)
NOT_PAGE_WORDS = re.compile(r"\[evidence\]|\[live check\]|not stated|not said|capture \d|\bUTC\b|base_price|total_?price|netEffective|price_basis|page data|"
                            r"\bper (?:Trulia|Zumper|Apartment List)\b|unit data|own site|\(.{0,30}field\)|stored price|\bterm \d+: price|^\s*\w+[:=]\s*[\w$.,-]+\s*[;,]\s*\w+[:=]|"
                            r"\bgross unknown\b|so likely|refreshed 20\d\d", re.I)
GROSS_AMT = re.compile(r"gross rent\s+(?:of|is)\s+\$\s?([\d,]+)|\$\s?([\d,]+)\s+gross\b", re.I)
UNIT_GROSS = re.compile(r"\b(?:unit\s+)?#?(\w{1,6})\s+is\s+a\s+[^$]{0,60}?gross rent of\s+\$\s?([\d,]+)", re.I)
DEPOSIT = re.compile(r"deposit|\bsecurity\b", re.I)
FEEWAIVE = re.compile(r"waive|no (?:application|amenity|broker|move[- ]in) fee|free (?:garage |indoor )?parking|"
                      r"free amenit|parking incentive|free electric", re.I)
CREDIT = re.compile(r"\$\s?\$?([\d,]{3,6})(?:\.00)?\s*(?:one[- ]time\s+)?(?:move[- ]in\s+(?:credit|bonus)|rent\s+credit|"
                    r"off\b|credit|gift\s*card)|(?:rent\s+credit|credit)\s+of\s+\$\s?([\d,]{3,6})", re.I)
LOOKLEASE = re.compile(r"within\s+\d{2}\s*-?\s*(?:hours?|hrs?)|same[- ]day\s+appl|look\s*(?:and|&|n)\s*lease|"
                       r"\d{2}\s*hours?\s+(?:post|of|after)", re.I)
NOT_RENT = re.compile(r"\s*(?:of\s+)?(?:free\s+)?(?:garage\s+|indoor\s+|offsite\s+)?(?:parking|pet rent|amenit|electric|storage|gym|internet|wifi|cable)", re.I)
UNIT_LIST = re.compile(r"\bApts?\.?\s+((?:[A-Z]?\d{3,4}\*?(?:\s*,\s*|\s+and\s+|\s*&\s*)?)+)")
UPFRONT = re.compile(r"\bfirst\s+(?:full\s+)?month|1st\s+month|move[- ]in\s+month|up[- ]?front|month of move", re.I)
ENDLEASE = re.compile(r"\b13th\s+month|last\s+month|final\s+month|end of (?:the |your )?lease", re.I)
SPREAD = re.compile(r"\bspread\b|prorated over|amortiz|pay\s+\$\s?[\d,]+\s+net effective", re.I)
SECOND_MONTH = re.compile(r"(?:applied to|off) (?:the |your )?(?:2nd|second)(?: full)? month", re.I)
DATE_NUM = re.compile(r"(?:by|before|thru|through|until|till|expires?|good thru|ends?)\s*:?\s*(?:on\s+)?"
                      r"(\d{1,2})\s*[/-]\s*(\d{1,2})(?:\s*[/-]\s*(\d{2,4}))?", re.I)
DATE_NAME = re.compile(r"(?:by|before|thru|through|until|till|expires?|good thru|ends?)\s*:?\s*(?:on\s+)?(" + MON +
                       r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(20\d\d))?", re.I)
OTHER_BEDS = re.compile(r"\b(2|two|3|three|4|four)[- ]?(?:bed(?:room)?s?|br)\b", re.I)
VAGUE = re.compile(r"promotions?|free rent|special offer|incentive|concession|net[- ]?effective|gross rent|months? free|"
                   r"move[- ]in special|leasing special|specials", re.I)


def num(s):
    s = re.sub(r"\s+", " ", str(s).strip().lower())
    if s in NUMW:
        return NUMW[s]
    try:
        return float(s)
    except ValueError:
        return None


def fnum(x):
    """Format a number without a trailing .0."""
    if x is None or x == "":
        return ""
    x = float(x)
    return str(int(x)) if abs(x - round(x)) < 1e-9 else f"{x:.2f}".rstrip("0").rstrip(".")


def clean(s):
    s = htmllib.unescape(re.sub(r"<[^>]+>", " ", str(s or "")))
    return re.sub(r"[ \t\r\f\v]+", " ", s.replace("\\n", "\n")).replace("$$", "$").strip()


def sentences(text):
    return [p.strip() for p in re.split(r"\n+|(?<=[.!?])\s+(?=[A-Z0-9*$(])|\s*•\s*|;\s+", text) if p.strip()]


def offer_sentences(desc):
    """Sentences of a free-text description that carry rent-offer language (verbatim)."""
    out = []
    for s in sentences(clean(desc)):
        if TRIG.search(s) and not NOT_OFFER.search(s):
            out.append(s[:400])
    return out


# ------------------------------------------------------------------ per-source readers of the cached page
def _flight(html):
    out = []
    for c in re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html):
        try:
            out.append(json.loads(c))
        except json.JSONDecodeError:
            pass
    return "".join(out)


def read_apartmentlist(text):
    fl, best = _flight(text), None
    for m in re.finditer(r'"listing":\{"rental_id"', fl):
        try:
            o, _ = DEC.raw_decode(fl, m.start() + 10)
        except json.JSONDecodeError:
            continue
        if "available_units" in o and (best is None or len(o) > len(best)):
            best = o
    pieces, exp = [], ""
    if not best:
        return pieces, exp, "listing object not found in cached page"
    # The page carries the listing twice; only the shorter copy (big fields replaced by "$ref" pointers) has its
    # `specials` list filled, and `best` is the longer one, whose specials are always []. Collect specials from every
    # copy of the same rental_id, as scripts/h_apartmentlist.py: parse_listing does (independent check W6).
    specials, seen_sp = list(best.get("specials") or []), set()
    for m in re.finditer(r'"specials":\[\{', fl):
        try:
            arr, _ = DEC.raw_decode(fl, m.start() + 11)
        except json.JSONDecodeError:
            continue
        back = fl.rfind('"listing":{"rental_id":"', 0, m.start())
        if back < 0 or not fl.startswith(str(best.get("rental_id")), back + 24):
            continue
        for sp in arr:
            if isinstance(sp, dict) and sp.get("id") not in seen_sp:
                seen_sp.add(sp.get("id"))
                specials.append(sp)
    for s in specials:
        if isinstance(s, dict):
            t = clean(s.get("raw_text") or s.get("description") or s.get("title") or "")
            if t:
                pieces.append(("special", t))
            if s.get("expires_at"):
                exp = str(s["expires_at"])[:10]
    for k in ("description", "long_highlight", "short_highlight", "lease_terms_text", "why_we_love_it"):
        for s in offer_sentences(best.get(k) if isinstance(best.get(k), str) else ""):
            pieces.append(("description", s))
    return pieces, exp, ""


def read_trulia(text):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not m:
        return [], "", "__NEXT_DATA__ not found in cached page"
    try:
        hd = (json.loads(m.group(1)).get("props") or {}).get("homeDetails") or {}
    except json.JSONDecodeError:
        return [], "", "__NEXT_DATA__ not parseable"
    pieces = []
    for s in hd.get("specialOffers") or []:
        t = clean(" ".join(x for x in (s.get("description"), s.get("subText")) if x))
        if t:
            pieces.append(("special", t))
    d = hd.get("description") or {}
    for s in offer_sentences(d.get("value") if isinstance(d, dict) else d):
        pieces.append(("description", s))
    return pieces, "", ""


def read_zumper(text):
    i = text.find("window.__PRELOADED_STATE__ = ")
    if i < 0:
        return [], "", "preloaded state not found in cached page"
    try:
        st, _ = DEC.raw_decode(text[i + len("window.__PRELOADED_STATE__ = "):])
    except json.JSONDecodeError:
        return [], "", "preloaded state not parseable"
    e = (((st or {}).get("detail") or {}).get("entity") or {}).get("data") or {}
    pieces = []
    sp = e.get("specials")
    if sp:
        for s in (sp if isinstance(sp, list) else [sp]):
            pieces.append(("special", clean(s if isinstance(s, str) else json.dumps(s, ensure_ascii=False))))
    for k in ("title", "short_description", "description"):
        for s in offer_sentences(e.get(k) or ""):
            if k == "short_description" and any(s.rstrip(". ")[:60] in p[1] for p in pieces):
                continue
            pieces.append(("description", s))
    tags = (e.get("amenity_tags") or []) + (e.get("building_amenity_tags") or [])
    if any(str(t).lower() == "free rent" for t in tags):
        pieces.append(("tag", "amenity tag: Free Rent"))
    return pieces, "", ""


def read_generic(text):
    """Zillow building pages and manager sites: specialOffers JSON strings and special-offer blocks."""
    pieces = []
    t = text.replace('\\"', '"') if '\\"specialOffers' in text else text
    for m in re.finditer(r'"specialOffers":\[(.*?)\]', t, re.S):
        for d in re.finditer(r'"description":("(?:[^"\\]|\\.)*")', m.group(1)):
            try:
                pieces.append(("special", clean(json.loads(d.group(1)))))
            except json.JSONDecodeError:
                pass
    for m in re.finditer(r'<div class="specials\s*"\s*>(.*?)</div>', text, re.S):
        pieces.append(("special", re.sub(r"\s+", " ", clean(m.group(1)))))
    for m in re.finditer(r"Prices listed are after rent concessions are applied\.", text):
        pieces.append(("description", m.group(0)))
    return pieces, "", ""


_page_cache: dict[str, tuple] = {}


def page_pieces(raw_path):
    if raw_path in _page_cache:
        return _page_cache[raw_path]
    p = ROOT / raw_path.split("#")[0]
    if not raw_path or not p.exists():
        res = ([], "", "cached page missing")
    else:
        text = p.read_text("utf8", "replace")
        if "/apartmentlist/" in raw_path:
            res = read_apartmentlist(text)
        elif "/trulia/" in raw_path or "/manual_envy/" in raw_path:
            res = read_trulia(text)
        elif "/zumper/" in raw_path:
            res = read_zumper(text)
        else:
            res = read_generic(text)
    seen, out = set(), []
    for origin, t in res[0]:
        k = re.sub(r"\W+", "", t.lower())
        if k and k not in seen:
            seen.add(k)
            out.append((origin, t))
    _page_cache[raw_path] = (out, res[1], res[2])
    return _page_cache[raw_path]


# ------------------------------------------------------------------ evidence
def load_evidence():
    facts, live = defaultdict(list), defaultdict(list)
    for f in sorted(glob.glob(str(EVID / "facts_batch_*.csv"))):
        for r in csv.DictReader(open(f, newline="", encoding="utf8")):
            if (r.get("fact") or "").startswith(("concession", "price_basis", "special")):
                facts[r["addr_key"]].append(r)
    for f in sorted(glob.glob(str(EVID / "live_check_batch_*.csv"))):
        for r in csv.DictReader(open(f, newline="", encoding="utf8")):
            if TRIG.search(r.get("notes") or "") or re.search(r"gross|free on", r.get("notes") or "", re.I):
                live[r["addr_key"]].append(r)
    return facts, live


# ------------------------------------------------------------------ parsing
def parse_date(s):
    """First 'by / through <date>' in s as ISO, else ''."""
    m = DATE_NUM.search(s)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), m.group(3)
        y = int(y) if y else YEAR
        y = y + 2000 if y < 100 else y
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return ""
    m = DATE_NAME.search(s)
    if m:
        mo = next(i + 1 for i, n in enumerate(MONTHNAMES) if n.startswith(m.group(1).lower()[:3]))
        try:
            return date(int(m.group(3) or YEAR), mo, int(m.group(2))).isoformat()
        except ValueError:
            return ""
    return ""


def own_beds_re(beds):
    if str(beds) in ("0", "0.0"):
        return re.compile(r"studio|all (?:available )?(?:units|apartments|homes)", re.I)
    return re.compile(r"\b(?:1|one)[- ]?(?:bed|br)|\b(?:1|one)\s*(?:,|&|and|or)\s*(?:2|two)\b|all (?:available )?(?:units|apartments|homes)", re.I)


def parse_piece(text, beds, unit_no=""):
    """Offers found in one verbatim piece. Returns dict of findings for this piece."""
    own = own_beds_re(beds)
    out = {"offers": [], "credits": [], "deposit": False, "fee": False, "looklease": False, "net": False,
           "net_neg": False, "select": False, "not_for_unit": [], "renewal": False, "timing": "", "dates": [],
           "gross": [], "unit_gross": {}, "named_only": []}
    restricted = False
    for cl in sentences(text):
        ob = OTHER_BEDS.search(cl)
        if own.search(cl):
            restricted = False
        elif ob or re.search(r"\bpenthouse", cl, re.I):
            restricted = True
        frees = []
        for m in FREE.finditer(cl):
            q1, q2 = num(m.group("q1")), num(m.group("q2")) if m.group("q2") else None
            if q1 is None or NOT_RENT.match(cl[m.end():m.end() + 30]):
                continue
            pre = cl[max(0, m.start() - 12):m.start()].lower()
            if re.search(r"and\s+a\s*$", pre):          # "one and a half months" split oddly
                pass
            unit = m.group("unit").lower()
            frees.append({"s": m.start(), "e": m.end(), "lo": min(q1, q2) if q2 else q1, "hi": max(q1, q2) if q2 else q1,
                          "upto": bool(m.group("upto")) or bool(q2), "unit": unit, "named": ""})
        if not frees and re.search(r"prorated", cl, re.I):
            for m in FREE_SPECIAL.finditer(cl):
                q = 1.5 if "and a half" in m.group("q").lower() else num(m.group("q"))
                if q:
                    frees.append({"s": m.start(), "e": m.end(), "lo": q, "hi": q, "upto": False, "unit": "month", "named": ""})
        if not frees:
            for m in FREE_NOQ.finditer(cl):
                frees.append({"s": m.start(), "e": m.end(), "lo": 1, "hi": 1, "upto": False, "unit": "month",
                              "named": "month 13" if "13th" in m.group(0).lower() else "first month"})
            for m in FREE_NAMED.finditer(cl):
                mo = next(n for n in MONTHNAMES if n.startswith(m.group(1).lower()[:3]))
                frees.append({"s": m.start(), "e": m.end(), "lo": 1, "hi": 1, "upto": False, "unit": "month",
                              "named": f"{mo.title()} {m.group(2) or YEAR}"})
        named_units = [x.strip("*") for m in UNIT_LIST.finditer(cl) for x in re.findall(r"[A-Z]?\d{3,4}", m.group(1))]
        if named_units and unit_no not in named_units:
            if frees:
                out["named_only"].append(", ".join(named_units))
            frees = []
        leases = [(m.start(), m) for m in LEASE.finditer(cl)]
        for i, f in enumerate(frees):
            nxt = frees[i + 1]["s"] if i + 1 < len(frees) else len(cl)
            prv = frees[i - 1]["e"] if i else 0
            lm = next((m for s, m in leases if f["e"] <= s < nxt), None) or \
                next((m for s, m in reversed(leases) if prv <= s < f["s"]), None)
            lo = hi = None
            if lm:
                a = lm.group("a") or lm.group("c") or lm.group("d")
                lo = int(a)
                hi = int(lm.group("b")) if lm.group("b") else lo
                if lm.group("p1") or lm.group("p2") or lm.group("p3") or lm.group("p4"):
                    hi = 99
                if lo < 3:
                    lo = hi = None
            f.update(lease_lo=lo, lease_hi=hi, clause=cl, select=bool(SELECT.search(cl)))
            if RENEW.search(cl):
                out["renewal"] = True
                continue
            if restricted:
                out["not_for_unit"].append(cl[:160])
                continue
            out["offers"].append(f)
        if restricted:
            if ob and not frees and (NET_STMT.search(cl) or CREDIT.search(cl)):
                out["not_for_unit"].append(cl[:160])
            continue
        if SELECT.search(cl):
            out["select"] = True
        if NET_NEG.search(cl):
            out["net_neg"] = True
        elif NET_STMT.search(cl):
            out["net"] = True
        for m in GROSS_AMT.finditer(cl):
            out["gross"].append(int((m.group(1) or m.group(2)).replace(",", "")))
        for m in UNIT_GROSS.finditer(cl):
            out["unit_gross"][m.group(1).upper()] = int(m.group(2).replace(",", ""))
        for m in re.finditer(r"\band\s+(\w{1,6})\s+is\s+a\s+[^$]{0,60}?gross rent of\s+\$\s?([\d,]+)", cl, re.I):
            out["unit_gross"][m.group(1).upper()] = int(m.group(2).replace(",", ""))
        dep = bool(DEPOSIT.search(cl))
        for m in CREDIT.finditer(cl):
            amt = int((m.group(1) or m.group(2)).replace(",", ""))
            ctx = cl[max(0, m.start() - 40):m.end() + 25]
            if re.search(r"deposit|security|waive|amenity fee", ctx, re.I) and not re.search(r"credit|bonus|\boff\b", m.group(0), re.I):
                continue
            if re.search(r"security deposit", cl[max(0, m.start() - 30):m.end() + 5], re.I):
                continue
            out["credits"].append({"amt": amt, "clause": cl, "upto": bool(re.search(r"up to\s*$", cl[:m.start()], re.I)),
                                   "select": bool(SELECT.search(cl)), "looklease": bool(LOOKLEASE.search(cl)),
                                   "recurring": bool(re.search(r"monthly|per month|/mo", cl[m.end() - 5:m.end() + 30], re.I))})
        if dep and re.search(r"\$\s?\d+|reduc|special|50% off|0%|waiv|low|half month", cl, re.I):
            out["deposit"] = True
        if FEEWAIVE.search(cl):
            out["fee"] = True
        if LOOKLEASE.search(cl):
            out["looklease"] = True
        if frees and not out["timing"]:
            if SPREAD.search(cl) or re.search(r"special (?:which will be )?prorated within", cl, re.I):
                out["timing"] = "spread_monthly"
            elif SECOND_MONTH.search(cl):
                out["timing"] = "specific_months: month 2"
            elif any(f["named"] == "month 13" for f in frees) or ENDLEASE.search(cl):
                out["timing"] = "end_of_lease"
            elif any(f["named"] and f["named"] not in ("first month",) for f in frees):
                out["timing"] = "specific_months: " + ", ".join(f["named"] for f in frees if f["named"])
            elif UPFRONT.search(cl) and not re.search(r"first month of the new year", cl, re.I):
                out["timing"] = "upfront"
        d = parse_date(cl)
        if d:
            out["dates"].append((d, cl[:120]))
    return out


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, min(d.day, calendar.monthrange(d.year + y, m + 1)[1]))


def first_of_month_on_or_after(d):
    return d if d.day == 1 else add_months(date(d.year, d.month, 1), 1)


def build_row(u, facts, live):
    lid, akey = u["listing_id"], u["addr_key"]
    listed = float(u["listed_rent"]) if re.fullmatch(r"\d+(\.\d+)?", u["listed_rent"] or "") else None
    beds = u.get("beds", "")
    unit_no = (u.get("unit") or "").strip().upper()
    basis_txt = u.get("price_basis", "")
    m = re.search(r"(\d+)-month", basis_txt)
    lease_unit = int(m.group(1)) if m else None

    # ---- gather verbatim pieces
    pieces = []          # (origin, text, url)
    page, exp_at, page_problem = page_pieces(u.get("raw_path", ""))
    for origin, t in page:
        pieces.append((origin, t, u["url"]))
    if u.get("concession_text"):
        for part in re.split(r"\s+\|\s+|\s;\s", clean(u["concession_text"])):
            if part and not part.startswith(("[", "tags:")):
                pieces.append(("stored", part, u["url"]))
            elif part.startswith("["):
                try:
                    for x in json.loads(part):
                        pieces.append(("stored", clean(x if isinstance(x, str) else json.dumps(x)), u["url"]))
                except Exception:
                    pieces.append(("stored", part, u["url"]))
            elif part.startswith("tags:"):
                pieces.append(("tag", part, u["url"]))
    if NET_STMT.search(basis_txt):
        pieces.append(("price_basis", basis_txt, u["url"]))
    for s in offer_sentences(re.sub(r"(?:^|; )(?:drive_min|rental_type|source_name|neighborhood|mls_number|"
                                    r"availability_last_checked_at|floorplan|unit_updated_at|website_url|"
                                    r"total_units_count|year_built)=[^;]*", "", u.get("notes", ""))):
        pieces.append(("notes", s, u["url"]))
    ev_gross_confirmed = False
    ev_gross = ev_net = None
    for r in facts.get(akey, []):
        t = clean(r.get("quote") or r.get("value") or "")
        if t:
            pieces.append(("evidence", t, r.get("source_url") or ""))
        if r["fact"].startswith("price_basis") and NET_STMT.search((r.get("value") or "") + " " + t):
            pieces.append(("evidence", "[evidence] " + clean(r.get("value")), r.get("source_url") or ""))
    for r in live.get(akey, []):
        ru = (r.get("unit") or "").upper()
        if unit_no and ru and unit_no != ru and unit_no not in re.split(r"[^\w-]+", ru):
            continue
        n = clean(r.get("notes"))
        pieces.append(("live_check", "[live check] " + n, r.get("building_site_url") or r.get("listing_url") or ""))
        if re.search(r"match(?:es|ing) the stored gross rent|data-rent \d[\d.]* matches stored", n, re.I):
            ev_gross_confirmed = True
        mg = re.search(r"gross rent is \$\s?([\d,]+)", n, re.I)
        if mg:
            ev_gross = int(mg.group(1).replace(",", ""))
        mn = EV_NET.search(n)
        if mn:
            ev_net = int(mn.group(1).replace(",", ""))

    # de-duplicate (stored text usually repeats the page's special)
    seen, uniq = [], []
    for origin, t, url in pieces:
        k = re.sub(r"\W+", "", t.lower())
        if not k or any(k in s or (len(k) > 40 and s in k) or (origin == "stored" and len(k) > 70 and k[20:60] in s)
                        for s in seen):
            continue
        seen.append(k)
        uniq.append((origin, t, url))
    pieces = uniq
    # D5: a piece that is ONLY the checker saying "the page does not say whether the price is net-effective" is not offer
    # language. It still sets net_neg (so nothing is read as net-effective) but does not make an "offer" out of no offer.
    neg_only = [(o, t, url) for o, t, url in pieces if all(NET_NEG.search(c) for c in sentences(re.sub(r"^\[(?:evidence|live check)\]\s*", "", t)))]
    if neg_only:
        pieces = [x for x in pieces if x not in neg_only]

    # ---- parse
    P = [(o, t, url, parse_piece(t, beds, unit_no)) for o, t, url in pieces]
    offers = [dict(f, origin=o) for o, t, url, p in P for f in p["offers"]]
    credits = list({c["amt"]: c for o, t, url, p in P for c in p["credits"]}.values())
    piece_select = {id(f): p["select"] for o, t, url, p in P for f in p["offers"]}
    net = any(p["net"] for *_, p in P)
    net_neg = any(p["net_neg"] for *_, p in P) or bool(neg_only)
    deposit = any(p["deposit"] for *_, p in P)
    fee = any(p["fee"] for *_, p in P)
    looklease = any(p["looklease"] for *_, p in P)
    not_for_unit = [x for *_, p in P for x in p["not_for_unit"]]
    renewal = any(p["renewal"] for *_, p in P)
    timing = next((p["timing"] for *_, p in P if p["timing"]), "")
    dates = sorted({d for *_, p in P for d in p["dates"]})
    gross_stated = sorted({g for *_, p in P for g in p["gross"]})
    unit_gross = {}
    for *_, p in P:
        unit_gross.update(p["unit_gross"])

    cond, how = [], []
    month_offers = [f for f in offers if f["unit"] == "month"]
    week_offers = [f for f in offers if f["unit"] == "week"]

    # ---- choose the offer that applies to this unit's price
    conv = (12 / 52) if (week_offers and not month_offers) else 1
    options = []
    chosen, definite = None, False
    f_lo = f_hi = None
    l_lo = l_hi = None
    pool = month_offers or week_offers
    if pool:
        def key(f):
            return (f["lo"], f["hi"], f["lease_lo"], f["lease_hi"])
        distinct = {key(f): f for f in pool}
        for k0 in [k for k in distinct if k[2] is None]:      # same amount stated again without the lease term
            if any(k[:2] == k0[:2] and k[2] is not None for k in distinct):
                del distinct[k0]
        options = [(f["lo"], f["hi"], f["lease_lo"] if f["lease_lo"] and f["lease_lo"] == f["lease_hi"] else None)
                   for f in distinct.values()]
        match = [f for f in distinct.values() if lease_unit and f["lease_lo"] and f["lease_lo"] <= lease_unit <= f["lease_hi"]]
        netpair = [f for f in distinct.values() if NET_STMT.search(f["clause"]) and not NET_NEG.search(f["clause"])]
        if len(match) == 1:
            chosen = match[0]
        elif len(netpair) == 1:
            chosen = netpair[0]
        elif len(distinct) == 1:
            chosen = next(iter(distinct.values()))
        if chosen:
            f_lo, f_hi, l_lo, l_hi = chosen["lo"], chosen["hi"], chosen["lease_lo"], chosen["lease_hi"]
            sel = chosen["select"] or piece_select.get(id(chosen), False) or any(
                p["select"] for o, t, url, p in P if chosen["clause"] in t)
            definite = not chosen["upto"] and f_lo == f_hi and not sel
            if chosen["upto"]:
                cond.append("'up to' / range offer: amount for this unit not stated")
            if sel:
                cond.append("select units / restrictions: not confirmed for this unit")
            others = [f for f in distinct.values() if f is not chosen]
            if others:
                cond.append("other options on page: " + "; ".join(
                    f"{fnum(f['lo'])}{'-' + fnum(f['hi']) if f['hi'] != f['lo'] else ''} {f['unit']}(s) free"
                    + (f" on {f['lease_lo']}{'+' if f['lease_hi'] == 99 else ('-' + str(f['lease_hi']) if f['lease_hi'] != f['lease_lo'] else '')}-month lease" if f["lease_lo"] else "")
                    for f in others))
        else:
            f_lo = min(f["lo"] for f in pool)
            f_hi = max(f["hi"] for f in pool)
            cond.append("several offers on page, none tied to this unit's lease term: " + "; ".join(
                f"{fnum(f['lo'])}{'-' + fnum(f['hi']) if f['hi'] != f['lo'] else ''} {f['unit']}(s) free"
                + (f" on {f['lease_lo']}{'+' if f['lease_hi'] == 99 else ''}-month lease" if f["lease_lo"] else "")
                for f in distinct.values()))

    # ---- lease term the offer and price apply to
    lease, lease_assumed = None, False
    if l_lo:
        if l_lo == l_hi:
            lease = l_lo
            if lease_unit and lease_unit != l_lo:
                cond.append(f"listed price is quoted for a {lease_unit}-month lease; offer requires {l_lo} months")
                definite = False
        elif lease_unit and l_lo <= lease_unit <= l_hi:
            lease = lease_unit
            cond.append(f"offer for leases of {l_lo}{'+' if l_hi == 99 else '-' + str(l_hi)} months")
        else:
            cond.append(f"offer for leases of {l_lo}{'+' if l_hi == 99 else '-' + str(l_hi)} months; "
                        + (f"listed price is for {lease_unit} months" if lease_unit else "unit's lease term not stated"))
            definite = False
            if lease_unit:
                lease = lease_unit
    elif lease_unit:
        lease = lease_unit
        if pool:
            cond.append(f"offer does not state a lease term; listed price is for a {lease_unit}-month lease")
    if pool and lease is None:
        definite = False
        lease_assumed = True
    if lease_unit and lease_unit != 12 and not any(f"{lease_unit}-month lease" in c or f"for {lease_unit} months" in c for c in cond):
        cond.append(f"listed price is for a {lease_unit}-month lease")

    # ---- offer type
    is_week = bool(week_offers) and not month_offers
    if month_offers:
        otype = "months_free"
    elif week_offers:
        otype = "weeks_free"
    elif credits and looklease:
        otype = "look_and_lease"
    elif credits:
        otype = "dollar_credit"
    elif deposit or fee:
        otype = "reduced_deposit_or_fee"
    elif looklease:
        otype = "look_and_lease"
    elif any(o in ("special", "stored", "tag", "description", "evidence", "live_check", "notes", "price_basis") for o, *_ in P):
        otype = "other"
    else:
        otype = "none"
    free_rent = otype in ("months_free", "weeks_free")
    if free_rent and (deposit or fee):
        cond.append("page also offers a deposit reduction or fee/parking waiver (no change to rent)")
    if free_rent and credits:
        cond.append("plus dollar credit(s): " + ", ".join("$" + fnum(c["amt"]) for c in credits))
    named_only = [x for *_, p in P for x in p["named_only"]]
    if named_only:
        cond.append("a free month on the page is for named units only (" + "; ".join(dict.fromkeys(named_only)) + "), not this unit")
    if renewal:
        cond.append("a further free month is offered on renewal (not part of this lease)")
    if not_for_unit:
        cond.append("offer text for other unit types, not applied: " + " / ".join(dict.fromkeys(not_for_unit))[:220])
    if looklease:
        cond.append("look-and-lease condition (apply within 24-48 h of touring) on part of the offer")
    for d, cl in dates:
        cond.append(f"deadline {d}: '{cl}'")
    offer_expires = dates[0][0] if dates else (exp_at or "")
    if exp_at and not dates:
        cond.append(f"listing feed gives offer expiry {exp_at}")
    if "total monthly" in basis_txt:
        cond.append("listed price is a total that includes required monthly fees, so it overstates base rent")
    if page_problem:
        cond.append(page_problem)

    # free months as months (weeks converted at 12/52)

    fm_lo = f_lo * conv if f_lo is not None else None
    fm_hi = f_hi * conv if f_hi is not None else None
    if not free_rent:
        fm_lo = fm_hi = None
    free_txt = ""
    if fm_lo is not None:
        free_txt = fnum(round(fm_lo, 2)) if fm_lo == fm_hi else f"{fnum(round(fm_lo, 2))}-{fnum(round(fm_hi, 2))}"
        if is_week:
            how.append(f"{fnum(f_lo)}{'-' + fnum(f_hi) if f_hi != f_lo else ''} weeks free = weeks x 12/52 months")

    # ---- price basis
    gross = netv = None
    g_if_net = n_if_gross = ""
    confidence, needs_call = "stated_on_page", "no"
    price_is = "gross"
    the_gross = unit_gross.get(unit_no) or ev_gross
    if the_gross is None and len(gross_stated) == 1 and not unit_gross and listed and gross_stated[0] >= listed:
        the_gross = gross_stated[0]
    L = lease or (12 if lease_assumed else None)

    def scen(net_side):
        """Scenario range over the page's options (each with its own lease term, else L)."""
        vals = []
        opts = options if (pool and not chosen) else [(f_lo, f_hi, None)]
        for lo, hi, ol in opts:
            ll = ol or L
            for fq in {lo * conv, hi * conv}:
                if ll and ll > fq:
                    vals.append(listed * (ll - fq) / ll if net_side else listed * ll / (ll - fq))
        if not vals:
            return ""
        a, b = round(min(vals)), round(max(vals))
        return fnum(a) if a == b else f"{fnum(a)}-{fnum(b)}"
    ev_stated = False

    if listed is None:
        price_is, confidence, needs_call = "unknown", "assumed_terms", "yes"
        how.append("listed rent is not a number")
    elif the_gross is not None:
        gross = float(the_gross)
        if gross > listed + 0.5:
            price_is, netv = "net_effective", listed
            how.append(f"page states gross rent ${fnum(gross)}; listed ${fnum(listed)} is the net-effective price")
            if definite and L:
                chk = gross * (L - fm_lo) / L
                how.append(f"check: {fnum(gross)} x ({L} - {fnum(fm_lo)}) / {L} = {fnum(round(chk))}")
        else:
            price_is = "gross"
            how.append(f"page states gross rent ${fnum(gross)} = listed")
            if definite and L:
                netv = gross * (L - fm_lo) / L
                how.append(f"net = {fnum(gross)} x ({L} - {fnum(fm_lo)}) / {L}")
                confidence = "computed_from_stated_terms"
    elif ev_gross_confirmed:
        price_is, gross = "gross", listed
        how.append("evidence: building's own table shows the stored price as the gross rent")
        if ev_net and free_rent:
            netv, ev_stated = float(ev_net), True
            how.append(f"own site shows net-effective ${ev_net} for the same unit"
                       + (f"; check: {fnum(gross)} x ({L} - {fnum(fm_lo)}) / {L} = {fnum(round(gross * (L - fm_lo) / L))}" if L and fm_lo == fm_hi else ""))
        elif free_rent and definite and L and not lease_assumed:
            netv = gross * (L - fm_lo) / L
            how.append(f"net = {fnum(gross)} x ({L} - {fnum(fm_lo)}) / {L}")
            confidence = "computed_from_stated_terms"
        elif free_rent:
            confidence, needs_call = "assumed_terms", "yes"
    elif net and not net_neg:
        price_is, netv = "net_effective", listed
        if free_rent and definite and L and not lease_assumed:
            gross = listed * L / (L - fm_lo)
            how.append(f"page says price is net-effective; gross = {fnum(listed)} x {L} / ({L} - {fnum(fm_lo)})")
            confidence = "computed_from_stated_terms"
        else:
            confidence, needs_call = "assumed_terms", "yes"
            how.append("page says price is net-effective but the free months and/or lease term for this unit are not definite: gross not computed")
            if fm_hi and L:
                g_if_net = scen(False)
                how.append("scenario: listed x lease / (lease - free)" + ("; 12-month lease assumed where the offer states none" if lease_assumed else f"; lease {L}"))
    elif free_rent:
        price_is, confidence, needs_call = "unknown", "assumed_terms", "yes"
        how.append("page does not say whether the listed price is gross or net of the free rent: gross not set")
        if fm_hi and L and L > fm_hi:
            g_if_net, n_if_gross = scen(False), scen(True)
            how.append("scenarios: gross_if_listed_is_net = listed x lease / (lease - free); net_if_listed_is_gross = listed x (lease - free) / lease"
                       + ("; 12-month lease assumed where the offer states none (scenarios only)" if lease_assumed else f"; lease {L}"))
    elif otype in ("dollar_credit", "look_and_lease") and credits:
        price_is, gross = "gross", listed
        c = credits[0]
        amt_txt = ", ".join(("up to " if x["upto"] else "") + "$" + fnum(x["amt"]) + (" per month" if x["recurring"] else " one-time") for x in credits)
        cond.append("credit: " + amt_txt)
        if len(credits) == 1 and not c["upto"] and not c["select"] and not c["recurring"] and lease and not c["looklease"]:
            netv = gross - c["amt"] / lease
            how.append(f"one-time credit: net = {fnum(gross)} - {c['amt']} / {lease}")
            confidence = "computed_from_stated_terms"
        else:
            confidence, needs_call = "assumed_terms", "yes"
            how.append("monthly rent unchanged (gross = listed); credit amount, eligibility or lease term for this unit not definite, so net not computed")
    elif otype == "reduced_deposit_or_fee" and not UNCLEAR.search(" ".join(t for _, t, _ in pieces)):
        price_is, gross, netv = "gross", listed, listed
        how.append("deposit / fee offer only: monthly rent unchanged, gross = listed")
    elif otype == "other" or (otype == "reduced_deposit_or_fee" and UNCLEAR.search(" ".join(t for _, t, _ in pieces))):
        txt = " ".join(t for _, t, _ in pieces)
        if otype != "other":
            otype = "other"
            cond.append("wording of a possible rent concession is unclear on the page")
        if net_neg or not_for_unit or VAGUE.search(txt) or UNCLEAR.search(txt):
            price_is, confidence, needs_call = "unknown", "assumed_terms", "yes"
            how.append("offer language without terms: cannot tell whether a rent concession is built into the listed price")
        else:
            price_is, gross, netv = "gross", listed, listed
            how.append("no rent concession stated: gross = listed")
    else:
        price_is, gross, netv = "gross", listed, listed
        how.append("no concession language on the listing: gross = listed")

    if free_rent and gross is not None and not timing:
        needs_call = "yes"
    if free_rent and not definite and the_gross is None and not ev_stated:
        confidence, needs_call = "assumed_terms", "yes"

    # ---- first full payment
    avail = u.get("available_date", "")
    try:
        move_in = date.fromisoformat(avail)
        mi_note = f"move-in {move_in.isoformat()} (available date)"
    except ValueError:
        move_in = DEFAULT_MOVE_IN
        mi_note = f"move-in {move_in.isoformat()} assumed (available now)"
    ffp, ffp_note = "", ""
    if not free_rent:
        ffp = first_of_month_on_or_after(move_in).isoformat()
        ffp_note = f"{mi_note}; no free period; rent due on the 1st, first month prorated if move-in is mid-month"
        timing_out = ""
    else:
        timing_out = timing or "unknown"
        if not timing:
            ffp_note = "free-period timing not stated on the page (upfront, end of lease or spread): ask"
        elif fm_lo != fm_hi or fm_lo is None:
            ffp_note = "timing stated but number of free months is a range: ask"
        elif timing == "upfront":
            whole, frac = int(fm_lo), fm_lo - int(fm_lo)
            end = add_months(move_in, whole) + timedelta(days=round(frac * 30))
            ffp = first_of_month_on_or_after(end).isoformat()
            ffp_note = f"{mi_note}; {fnum(round(fm_lo, 2))} month(s) free from move-in; rent assumed due on the 1st"
        elif timing == "end_of_lease":
            ffp = first_of_month_on_or_after(move_in).isoformat()
            ffp_note = f"{mi_note}; free month(s) fall at the end of the lease, so full rent is due from the start"
        elif timing == "spread_monthly":
            if lease:
                ffp = first_of_month_on_or_after(add_months(move_in, lease)).isoformat()
                ffp_note = f"{mi_note}; concession spread over the lease: net rent paid monthly, gross first charged at renewal after {lease} months"
            else:
                ffp_note = "concession spread monthly; lease term not stated, so the renewal date is unknown"
        elif timing == "specific_months: month 2":
            ffp = (move_in if move_in.day == 1 else add_months(first_of_month_on_or_after(move_in), 1)).isoformat()
            ffp_note = f"{mi_note}; free month is the second month of the lease; first month is paid in full (prorated first if move-in is mid-month)"
        elif timing.startswith("specific_months"):
            mm = re.findall(r"(" + "|".join(n.title() for n in MONTHNAMES) + r") (20\d\d)", timing)
            if mm:
                last = max(date(int(y), MONTHNAMES.index(n.lower()) + 1, 1) for n, y in mm)
                ffp = max(add_months(last, 1), first_of_month_on_or_after(move_in)).isoformat()
                ffp_note = f"{mi_note}; free month(s) named on the page ({timing.split(': ', 1)[1]}); next rent due on the 1st after"
            else:
                ffp_note = "free months are specific but not datable from the text: ask"

    # ---- offer text (verbatim), most relevant first
    rank = {"special": 0, "stored": 0, "description": 1, "notes": 2, "price_basis": 2, "evidence": 3, "live_check": 4, "tag": 5}
    ordered = sorted(enumerate(pieces), key=lambda x: (rank.get(x[1][0], 9), x[0]))
    offer_text = " | ".join(re.sub(r"\s*\n\s*", " / ", t) for _, (o, t, url) in ordered)
    if len(offer_text) > 400:
        offer_text = offer_text[:397] + "..."
    # the offer in the page's own words only (special banner, stored concession text, description): no checker notes, no raw page data
    page_txt = [re.sub(r"\s*\n\s*", " / ", t) for _, (o, t, url) in ordered if o in ("special", "stored", "description") and not NOT_PAGE_WORDS.search(t)]
    offer_text_page = " | ".join(dict.fromkeys(page_txt))
    if len(offer_text_page) > 300:
        offer_text_page = offer_text_page[:297].rsplit(" ", 1)[0] + "..."
    urls = list(dict.fromkeys([u["url"]] + [url for o, t, url in pieces if url]))

    if otype == "none":
        confidence = "stated_on_page"
    return {
        "listing_id": lid, "addr_key": akey, "listed_rent": u["listed_rent"], "listed_price_is": price_is,
        "offer_text": offer_text, "offer_text_page": offer_text_page, "offer_type": otype, "free_months": free_txt,
        "free_period_timing": timing_out, "lease_months": lease or "",
        "gross_monthly_rent": fnum(round(gross)) if gross is not None else "",
        "net_effective_monthly": fnum(round(netv)) if netv is not None else "",
        "first_full_payment_date": ffp, "first_full_payment_note": ffp_note, "offer_expires": offer_expires,
        "conditions": "; ".join(dict.fromkeys(cond)), "computed_how": "; ".join(how),
        "confidence": confidence, "source_url": " | ".join(urls), "needs_call": needs_call,
        "gross_if_listed_is_net": g_if_net, "net_if_listed_is_gross": n_if_gross,
    }


def hi_of(s):
    """Upper end of a number or 'a-b' range string."""
    try:
        return float(str(s).split("-")[-1])
    except ValueError:
        return None


def write_note(rows, units):
    by = {u["listing_id"]: u for u in units}
    n = len(rows)
    c_type = Counter(r["offer_type"] for r in rows)
    c_is = Counter(r["listed_price_is"] for r in rows)
    c_conf = Counter(r["confidence"] for r in rows)
    c_tim = Counter((r["free_period_timing"] or "(no free period)").split(":")[0] for r in rows)
    calls = [r for r in rows if r["needs_call"] == "yes"]
    call_bld = len({r["addr_key"] for r in calls})
    gaps = []
    for r in rows:
        if r["gross_monthly_rent"] and float(r["gross_monthly_rent"]) > float(r["listed_rent"]) + 0.5:
            gaps.append((float(r["gross_monthly_rent"]) - float(r["listed_rent"]), r))
    gaps.sort(key=lambda x: -x[0])
    scen = []
    for r in rows:
        h = hi_of(r["gross_if_listed_is_net"]) if r["gross_if_listed_is_net"] else None
        if h:
            scen.append((h - float(r["listed_rent"]), h, r))
    scen.sort(key=lambda x: -x[0])
    over_stated = [r for r in rows if r["gross_monthly_rent"] and float(r["gross_monthly_rent"]) > 3000]
    over_scen = [(h, r) for _, h, r in scen if h > 3000]
    nonterm = sum(1 for r in rows if r["lease_months"] not in ("", "12", 12))

    def name(r):
        u = by[r["listing_id"]]
        return f"{u.get('building_name') or u.get('address')} {('#' + u['unit']) if u.get('unit') else ''}".strip().replace("|", "/")

    L = ["# Rent terms (scripts/rent_terms.py -> data/rent_terms.csv)", "",
         "Rebuilt from data/units.csv, each unit's cached page (`raw_path`) and data/evidence/*.csv. No network "
         "requests. Every passing unit was checked and has one row.", "",
         f"- Units checked: **{n}** (one row each; `offer_type = none` for units with no such language).",
         f"- Units with any concession, special-offer or price-basis language: **{n - c_type['none']}**.",
         f"- Units whose price or offer is for a lease term other than 12 months: **{nonterm}**.",
         f"- Units that need a call (`needs_call = yes`): **{len(calls)}** in {call_bld} buildings.", "",
         "## Counts by offer_type", "", "| offer_type | units |", "|---|---|"]
    for k, v in c_type.most_common():
        L.append(f"| {k} | {v} |")
    L += ["", "## Listed price basis", "", "| listed_price_is | units |", "|---|---|"]
    for k, v in c_is.most_common():
        L.append(f"| {k} | {v} |")
    L += ["", "## Confidence", "", "| confidence | units |", "|---|---|"]
    for k, v in c_conf.most_common():
        L.append(f"| {k} | {v} |")
    L += ["", "## Free-period timing", "", "| timing | units |", "|---|---|"]
    for k, v in c_tim.most_common():
        L.append(f"| {k} | {v} |")
    L += ["", "## Gross rent above the listed price (stated or computed from stated terms)", "",
          f"**{len(gaps)}** units have a determined gross rent above the listed price.", ""]
    if gaps:
        L += ["| unit | listed | gross | gap | free months / lease | confidence |", "|---|---|---|---|---|---|"]
        for g, r in gaps[:25]:
            L.append(f"| {name(r)} | {r['listed_rent']} | {r['gross_monthly_rent']} | {fnum(round(g))} | "
                     f"{r['free_months']} / {r['lease_months']} | {r['confidence']} |")
    L += ["", "## Largest possible gaps where the basis is unknown (scenario: listed price is net-effective)", "",
          f"{len(scen)} units carry a scenario figure. These are **not** stated rents: they show what the monthly "
          "rent would be if the advertised price already has the free months spread in. Top 25:", "",
          "| unit | listed | gross if listed is net | gap | free months / lease | basis |", "|---|---|---|---|---|---|"]
    for g, h, r in scen[:25]:
        L.append(f"| {name(r)} | {r['listed_rent']} | {r['gross_if_listed_is_net']} | {fnum(round(g))} | "
                 f"{r['free_months']} / {r['lease_months'] or '12 assumed'} | {r['listed_price_is']} |")
    L += ["", "## Gross rent over $3,000 (rent only, all-in aside)", "",
          f"- Determined gross over $3,000: **{len(over_stated)}** units"
          + (": " + "; ".join(f"{name(r)} (${r['gross_monthly_rent']})" for r in over_stated) if over_stated else "."),
          f"- Scenario gross over $3,000 (upper end, if the listed price is net-effective): **{len(over_scen)}** units "
          f"in {len({r['addr_key'] for _, r in over_scen})} buildings.", ""]
    bl = defaultdict(list)
    for h, r in over_scen:
        bl[(by[r["listing_id"]].get("building_name") or by[r["listing_id"]].get("address")).replace("|", "/")].append((h, r))
    if bl:
        L += ["| building | units | listed range | scenario gross (max) | free months / lease |", "|---|---|---|---|---|"]
        for b, xs in sorted(bl.items(), key=lambda kv: -max(h for h, _ in kv[1])):
            rents = [float(r["listed_rent"]) for _, r in xs]
            r0 = xs[0][1]
            L.append(f"| {b} | {len(xs)} | {fnum(min(rents))}-{fnum(max(rents))} | {fnum(max(h for h, _ in xs))} | "
                     f"{r0['free_months']} / {r0['lease_months'] or '12 assumed'} |")
    L += ["", "## Method and limits", "",
          "- Offer text is verbatim from the cached listing page (Apartment List `specials[].raw_text`, Trulia / Zillow "
          "`specialOffers`, Zumper description and tags, Garden Communities special block), the stored `concession_text`, "
          "and evidence rows. Text marked `[live check]` or `[evidence]` is an earlier agent's note, not page wording.",
          "- All 693 Apartment List rows had an empty `concession_text` in units.csv (the harvester read the wrong field); "
          "this script reads the offers from the cached pages instead.",
          "- `listed_price_is` is `net_effective` only where a page or evidence row says so, `gross` where a gross rent is "
          "stated, confirmed, or there is no free-rent offer, and `unknown` for every other free-rent offer. Trulia's "
          "'prices shown are base rent' label is not treated as proof of gross (Envy by Gomes shows net prices under it).",
          "- Gross is never guessed. Net stated plus definite free months and lease term gives gross = net x lease / "
          "(lease - free). 'Up to', ranges and 'select units' are recorded as ranges with `assumed_terms` and a call.",
          "- Scenario columns use a 12-month lease when neither the offer nor the price states a term; `computed_how` says so.",
          "- First full payment assumes move-in on the available date (2026-12-01 when 'now') and rent due on the 1st. "
          "It is filled only when the timing is stated; otherwise `first_full_payment_note` gives the reason.",
          "- Weeks free are converted at 12/52 months per week.",
          "- Offers worded for other unit types (for example two-bedroom specials) are not applied to studios and "
          "one-bedrooms; the text is kept in `conditions`.",
          "- Deadlines are copied from the offer; several fall on or before 2026-11-30 and may lapse before a tour.", ""]
    NOTE.parent.mkdir(parents=True, exist_ok=True)
    NOTE.write_text("\n".join(L), encoding="utf8")


def main():
    units = [r for r in csv.DictReader(open(UNITS, newline="", encoding="utf8")) if r.get("unit_status") == "pass"]
    facts, live = load_evidence()
    rows, seen = [], set()
    for u in units:
        if u["listing_id"] in seen:
            continue
        seen.add(u["listing_id"])
        rows.append(build_row(u, facts, live))
    with open(OUT, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    write_note(rows, units)
    print(f"{len(rows)} rows -> {OUT.relative_to(ROOT)}")
    print("offer_type:", dict(Counter(r["offer_type"] for r in rows)))
    print("listed_price_is:", dict(Counter(r["listed_price_is"] for r in rows)))
    print("needs_call:", dict(Counter(r["needs_call"] for r in rows)))
    if "--dump" in sys.argv:
        groups = defaultdict(list)
        for r in rows:
            if r["offer_type"] != "none":
                groups[(r["offer_text"], r["offer_type"], r["free_months"], r["free_period_timing"], r["lease_months"],
                        r["listed_price_is"], r["confidence"], r["needs_call"], r["offer_expires"])].append(r)
        for k, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            r = rs[0]
            print(f"\n[{len(rs)}] {k[0]}\n   -> type={k[1]} free={k[2]} timing={k[3]} lease={k[4]} is={k[5]} conf={k[6]} call={k[7]} exp={k[8]}"
                  f"\n   listed={r['listed_rent']} gross={r['gross_monthly_rent']} net={r['net_effective_monthly']} "
                  f"g_if_net={r['gross_if_listed_is_net']} n_if_gross={r['net_if_listed_is_gross']} ffp={r['first_full_payment_date']}"
                  f"\n   cond: {r['conditions'][:400]}\n   how: {r['computed_how'][:300]}")


if __name__ == "__main__":
    main()
