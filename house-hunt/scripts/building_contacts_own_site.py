#!/usr/bin/env python3
"""Own-site leasing phone for buildings whose only number is a listing-site tracking line, or that have none.

Input  (read only): data/reference/building_contacts.csv, data/ranked_units.csv (`shown`),
                    raw/building_contacts_own_site/search_seeds.jsonl (one web search per building, done by the
                    agent: the building's own site, or "" when the search found none; last row per building wins).
Output: data/reference/building_contacts_own_site.csv (rebuilt whole from the caches on every run)
        raw/building_contacts_own_site/  page cache, _index.jsonl, _state.json, _refused_hosts.json

Rules built in:
  * a phone is only ever read from a fetched page of the building's / manager's own site; the page URL is recorded
  * robots.txt first (groups that name Claude override `*`), 1 request/second/host (scripts/lib.py)
  * at most 2 page fetches per building (robots.txt not counted), at most MAX_BUILDINGS buildings
  * one refusal (401/403/429, CAPTCHA, bot wall) ends requests to that host; it is written to
    _refused_hosts.json at once and honoured on every later run. Hosts refused in earlier harvests are skipped too.
  * individual-owner listings are skipped: no private person's phone or name is recorded
  * aggregator hosts are never requested

Usage:
  python3 scripts/building_contacts_own_site.py            # offline: rebuild the CSV from what is cached
  python3 scripts/building_contacts_own_site.py --fetch    # fetch what is not cached yet (resumable)
"""
from __future__ import annotations

import argparse
import csv
import html as htmllib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import building_contacts as bc  # noqa: E402  (helpers only; nothing in it is modified on disk)
from lib import DATA, RAW, ROOT, now_iso  # noqa: E402

SRC = "building_contacts_own_site"
# The Fetcher in building_contacts.py reads these module globals at call time: point it at our own folder.
bc.SRC = SRC
bc.STATE_F = RAW / SRC / "_state.json"
bc.REFUSED_F = RAW / SRC / "_refused_hosts.json"
bc.NEVER = tuple(bc.NEVER) + ("apartmentratings.com", "apartmentlist.com", "zumper.com", "rentcafe.com")

SEEDS = RAW / SRC / "search_seeds.jsonl"
OUT = DATA / "reference" / "building_contacts_own_site.csv"
CONTACTS = DATA / "reference" / "building_contacts.csv"
RANKED = DATA / "ranked_units.csv"
MAX_BUILDINGS = 110
MAX_PAGES = 2

COLS = ["building_id", "addr_key", "building_name", "own_site_url", "leasing_phone", "phone_page_url",
        "office_hours", "manager_name", "retrieved_at", "confidence", "note",
        "stated_elevator", "stated_pet_policy", "stated_pet_rent", "stated_parking", "stated_income_requirement"]

GENERIC = set("the a an at of and on by apartments apartment apts luxury llc community communities residences "
              "village suites tower towers house new".split())
DIR = {"n": "north", "s": "south", "e": "east", "w": "west"}
SUFFIX = {"st": "street", "ave": "avenue", "blvd": "boulevard", "rd": "road", "ct": "court", "hwy": "highway",
          "sq": "square", "pl": "place", "dr": "drive", "ln": "lane", "pkwy": "parkway", "expy": "expressway"}


# ----------------------------------------------------------------------------------------------- page text
def visible_text(html: str) -> str:
    t = re.sub(r"(?is)<(script|style|noscript|svg|template)[^>]*>.*?</\1>", "\n", html)
    t = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr|/td|/section|/span|/a)[^>]*>", "\n", t)
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", t))
    t = t.replace("\xa0", " ")
    lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in t.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def all_text(html: str) -> str:
    """Visible text plus JSON-LD and meta descriptions (sites built in JavaScript keep their facts there)."""
    extra = []
    for o in bc.jsonld_objects(html):
        for k in ("name", "description", "streetAddress", "telephone", "addressLocality", "postalCode"):
            v = o.get(k)
            if isinstance(v, str):
                extra.append(v)
    for m in re.finditer(r'<meta[^>]+content=["\']([^"\']{10,600})["\']', html, re.I):
        extra.append(htmllib.unescape(m.group(1)))
    for m in re.finditer(r"<title[^>]*>(.*?)</title>", html, re.I | re.S):
        extra.append(htmllib.unescape(m.group(1)))
    return visible_text(html) + "\n" + "\n".join(extra)


def squash(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def addr_variants(address: str) -> list[str]:
    """'house-number first-street-words' forms to look for in a page, e.g. '440 elizabeth', '1 north main'."""
    first = address.split(",")[0].split("#")[0]
    a = squash(first)
    a = re.sub(r"^(\d+) (\d+) ", r"\1\2 ", a) if re.match(r"^\d+ \d+ \d", a) else a   # '147 25 94th' -> '14725 94th'
    toks = a.split()
    if len(toks) < 2 or not toks[0][0].isdigit():
        return []
    num, rest = toks[0], toks[1:]
    nums = {num}
    m = re.match(r"^\s*(\d+)-(\d+)", first)
    if m:                                             # '65-77 Prospect St' / '89-25 162nd St'
        if rest and rest[0] == m.group(2):
            rest = rest[1:]
        nums |= {m.group(1), m.group(2), m.group(1) + m.group(2), f"{m.group(1)} {m.group(2)}"}
    if len(num) >= 4 and num.isdigit():               # '14725' may be written '147-25' on the page
        nums.add(f"{num[:-2]} {num[-2:]}")
    words = []
    for w in rest:                                    # street words up to the suffix ('st', 'ave', ...)
        if w in SUFFIX or w in SUFFIX.values():
            break
        words.append(w)
    words = words[:2] or rest[:1]
    alts = [words]
    if words and words[0] in DIR and len(words) > 1:
        alts += [[DIR[words[0]]] + words[1:], words[1:]]
    out = set()
    for n in nums:
        for w in alts:
            if w:
                out.add(f"{n} " + " ".join(w))
    return sorted(out)


def address_named(name: str, address: str) -> bool:
    """True when the 'name' is only the street address ('93 Richards', '750 Summer Street')."""
    n = squash(name)
    return bool(n) and n.split()[0][0].isdigit() and any(n.startswith(v) or v in n for v in addr_variants(address))


def name_tokens(name: str) -> list[str]:
    return [t for t in squash(name).split() if t not in GENERIC]


def match_flags(text: str, name: str, address: str) -> tuple[bool, bool]:
    sq = " " + squash(text) + " "
    glued = sq.replace(" ", "")
    toks = name_tokens(name)
    name_ok = bool(toks) and (all(f" {t} " in sq for t in toks) or "".join(toks) in glued)
    # a name that is only the address ('93 Richards', '750 Summer Street') proves nothing on its own
    if name_ok and address_named(name, address):
        name_ok = False
    addr_ok = any(f" {v} " in sq or f" {v}" in sq for v in addr_variants(address))
    return name_ok, addr_ok


# ----------------------------------------------------------------------------------------------- extraction
def phones_on_page(html: str) -> list[tuple[str, str]]:
    """[(phone, how)] in order of preference: JSON-LD telephone, tel: links (by frequency), page text."""
    out, seen = [], set()

    def add(p, how):
        if p and p not in seen:
            seen.add(p)
            out.append((p, how))
    for o in bc.jsonld_objects(html):
        t = o.get("telephone")
        if isinstance(t, str):
            add(bc.norm_phone(t), "JSON-LD telephone")
    tels = [bc.norm_phone(htmllib.unescape(t).replace("%20", "")) for t in re.findall(r'href=["\']tel:([^"\']+)["\']', html, re.I)]
    for p, _ in Counter(t for t in tels if t).most_common():
        add(p, "tel: link")
    for m in bc.PHONE_TXT.finditer(visible_text(html)):
        add(bc.norm_phone("".join(m.groups())), "page text")
    return out


def phone_class(p: str) -> int:
    """0 local (NY/NJ/CT area code), 1 toll-free, 2 other area code."""
    return 1 if bc.is_tollfree(p) else (0 if p[1:4] in bc.LOCAL_CODES else 2)


def choose_phone(html: str, ph: list[tuple[str, str]], address: str) -> tuple[str, str]:
    """A page that lists several properties: the number printed right after this building's address.
    Otherwise a local-area-code number before a toll-free or out-of-region one (those are often vendor
    call-tracking lines), keeping the JSON-LD > tel: link > page text order inside each class."""
    txt = " " + re.sub(r"\s+", " ", squash_keep(visible_text(html))) + " "
    in_text = {}
    for m in bc.PHONE_TXT.finditer(txt):
        in_text.setdefault(bc.norm_phone("".join(m.groups())), []).append(m.start())
    if len(in_text) >= 3:
        for v in addr_variants(address):
            for am in re.finditer(r"(?<![a-z0-9])" + re.escape(v) + r"(?![a-z0-9])", txt):
                near = [(pos - am.end(), p) for p, poss in in_text.items() for pos in poss if 0 <= pos - am.end() <= 140]
                if near:
                    return min(near)[1], "page text, the number printed next to this building's address on a multi-property page"
    return sorted(ph, key=lambda x: phone_class(x[0]))[0]


def squash_keep(s: str) -> str:
    """Lower-case, punctuation other than phone punctuation turned into spaces (keeps '(203) 212-5085' intact)."""
    return re.sub(r"[^a-z0-9()+.\- ]+", " ", s.lower().replace("\n", " "))


def hours_on_page(html: str) -> str:
    for c in bc.parse_own_site(html, "x"):
        if c.get("hours"):
            return c["hours"]
    txt = visible_text(html).replace("\n", " ")
    m = re.search(r"\b(Mon(?:day)?s?\b[^|]{0,170}?\d\s?(?:am|pm|a\.m\.|p\.m\.)[^|]{0,120})", txt, re.I)
    if m:
        s = m.group(1)
        cut = re.search(r"\b(Sun(?:day)?)\b[^A-Z]{0,40}?(?:closed|\d{1,2}(?::\d\d)?\s?(?:am|pm)\s?(?:-|–|to)\s?\d{1,2}(?::\d\d)?\s?(?:am|pm))", s, re.I)
        s = s[:cut.end()] if cut else s[:150]
        return re.sub(r"\s+", " ", s).strip()
    return ""


def manager_on_page(html: str) -> str:
    txt = visible_text(html).replace("\n", " ")
    m = re.search(r"(?:professionally |proudly )?managed by:?\s+([A-Z][A-Za-z0-9&.'\- ]{2,45}?)(?=[.,|©]|\s{2}| and | All | Equal |$)", txt)
    return m.group(1).strip() if m else ""


def fragments(text: str) -> list[str]:
    out = []
    for ln in text.split("\n"):
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z$])", ln):
            s = s.strip()
            if 4 <= len(s) <= 400:
                out.append(s)
    return out


def quote(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= 220 else s[:217] + "..."


FACTS = {
    "stated_elevator": [r"\belevators?\b"],
    "stated_pet_policy": [r"\b(pets?|dogs?)\b.*\b(\d+\s?(lbs?|pounds)|weight|breed)\b|\b(\d+\s?(lbs?|pounds)|weight limit|breed restrictions?)\b.*\b(pets?|dogs?)\b",
                          r"\bno (pets|dogs)\b|\b(pets|dogs) (are )?not (allowed|permitted)\b|\bcats only\b",
                          r"\b(pet|dog)[- ]friendly\b|\b(pets?|dogs?) (are )?(welcome|allowed|permitted)\b|\bwe (love|welcome) (your )?(pets|dogs)\b"],
    "stated_pet_rent": [r"\bpet rent\b.*\$\s?\d+|\$\s?\d+.*\bpet rent\b",
                        r"\b(pets?|dogs?|cats?)\b[^$]{0,80}\$\s?\d+[^.]{0,40}(month|/mo\b|monthly)|\$\s?\d+[^.]{0,40}(month|/mo\b|monthly)[^$]{0,60}\b(per )?(pet|dog|cat)\b"],
    "stated_parking": [r"\bparking\b[^$]{0,100}\$\s?\d+|\$\s?\d+[^.]{0,60}\bparking\b",
                       r"\b(free|complimentary|included)\b[^.]{0,40}\bparking\b|\bparking\b[^.]{0,40}\b(included|free of charge|at no (extra|additional) (cost|charge))\b",
                       r"\b(garage|covered|on-?site|reserved|assigned|surface|indoor|underground|valet) parking\b|\bparking (garage|available|lot)\b"],
    "stated_income_requirement": [r"\bincome\b.*\b(\d+(\.\d+)?\s?x|\d+ times|times the (monthly )?rent|requirement|must (earn|make))\b|\b(\d+(\.\d+)?\s?x|\d+ times)\b.*\b(rent|income)\b.*\bincome\b",
                                  r"\b(annual|gross|household|monthly) income\b.*\b(rent|qualif)"],
}


def stated_facts(texts: list[str]) -> dict:
    res = {k: "" for k in FACTS}
    frs = [f for t in texts for f in fragments(t)]
    for key, pats in FACTS.items():
        for pat in pats:
            hit = next((f for f in frs if re.search(pat, f, re.I)), None)
            if hit:
                res[key] = quote(hit)
                break
    return res


def property_link(html: str, base: str, name: str, address: str) -> str:
    """On a manager's index page, the link that leads to this building (by name or street in the link)."""
    toks = name_tokens(name)
    street = [v for v in addr_variants(address)]
    best = ""
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        href, label = m.group(1), squash(re.sub(r"<[^>]+>", " ", m.group(2)))
        u = urljoin(base, htmllib.unescape(href))
        if urlparse(u).netloc.lower().removeprefix("www.") != urlparse(base).netloc.lower().removeprefix("www."):
            continue
        hay = " " + label + " " + squash(urlparse(u).path) + " "
        if (toks and all(f" {t} " in hay for t in toks)) or any(f" {v} " in hay for v in street):
            if u.rstrip("/") != base.rstrip("/"):
                best = u
                break
    return best


def contact_link(html: str, base: str) -> str:
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        href, label = m.group(1), squash(re.sub(r"<[^>]+>", " ", m.group(2)))
        u = urljoin(base, htmllib.unescape(href))
        if urlparse(u).scheme not in ("http", "https"):
            continue
        if urlparse(u).netloc.lower().removeprefix("www.") != urlparse(base).netloc.lower().removeprefix("www."):
            continue
        if re.search(r"contact", label + " " + urlparse(u).path, re.I) and u.rstrip("/") != base.rstrip("/"):
            return u
    return ""


# ----------------------------------------------------------------------------------------------- inputs
def load_seeds() -> dict:
    seeds = {}
    if SEEDS.exists():
        for line in SEEDS.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                seeds[d["building_id"]] = d
    return seeds


def load_targets(seeds: dict) -> list[dict]:
    contacts = {r["building_id"]: r for r in csv.DictReader(open(CONTACTS, newline=""))}
    shown = set()
    with open(RANKED, newline="") as f:
        for r in csv.DictReader(f):
            if r.get("shown") == "True":
                shown.add(r["building_id"])
    out = []
    for bid, r in contacts.items():
        note = r["note"]
        if "tracking number" in note and "trulia.com" in r["leasing_phone_source_url"]:
            why = "tracking"
        elif not r["leasing_phone"]:
            why = "no_phone"
        elif "is outside NY/NJ/CT" in note:
            why = "out_of_region"
        else:
            continue
        out.append({**r, "why": why, "shown": bid in shown, "seed": seeds.get(bid)})
    order = {"tracking": 0, "out_of_region": 1, "no_phone": 2}
    out.sort(key=lambda t: (order[t["why"]], not t["shown"], t["building_id"]))
    return out


# ----------------------------------------------------------------------------------------------- one building
def process(t: dict, fx, fetch: bool) -> dict:
    row = {c: "" for c in COLS}
    row.update(building_id=t["building_id"], addr_key=t["addr_key"], building_name=t["building_name"])
    old = t["leasing_phone"]
    seed = t["seed"]
    if t["contact_kind"] == "individual owner":
        row.update(confidence="", note="skipped: owner-listed single unit; no private person's phone or name is recorded")
        return row
    if not seed:
        row["note"] = "not searched yet"
        return row
    if not seed.get("own_site_url"):
        row["note"] = "own site not found: " + seed.get("note", "")
        return row

    first = seed["own_site_url"]
    row["own_site_url"] = first
    pages, tried, budget = [], [], MAX_PAGES     # pages: (url, html, retrieved_at)

    def get(u):
        nonlocal budget
        if budget <= 0 or any(u == p[0] for p in pages):
            return None
        known = u in fx.state
        why = fx.blocked(bc.host_of(u))
        if why and not (known and fx.state[u].get("status") == 200):
            tried.append(f"{u} not fetched ({why})")
            return None
        if not known and not fetch:
            tried.append(f"{u} not fetched (run with --fetch)")
            return None
        path, info = fx.page(u)
        if u in fx.state and fx.state[u].get("status", -1) != -1:
            budget -= 1                          # a request was made for this page (now or on an earlier run)
        if not path:
            tried.append(f"{u} not fetched ({info})")
            return None
        html = (ROOT / path).read_text(errors="replace")
        pages.append((u, html, info))
        return html

    def good(html) -> bool:
        nm, ad = match_flags(all_text(html), t["building_name"], t["address"])
        return bool(phones_on_page(html)) and (nm or ad)

    html = get(first)
    if html is not None and not good(html):
        nxt = property_link(html, first, t["building_name"], t["address"]) or seed.get("alt_url") or contact_link(html, first)
        if nxt:
            get(nxt)
    elif html is None and seed.get("alt_url") and urlparse(seed["alt_url"]).netloc == urlparse(first).netloc:
        if not fx.blocked(bc.host_of(first)) and not any("robots.txt" in x for x in tried):
            get(seed["alt_url"])

    notes = [seed["note"]] if seed.get("note") else []
    if not pages:
        row["note"] = "; ".join(notes + tried) or "page not fetched"
        return row

    # choose the page: one that names the building / its address and carries a phone; else the first with a phone
    scored = []
    for u, h, when in pages:
        nm, ad = match_flags(all_text(h), t["building_name"], t["address"])
        ph = phones_on_page(h)
        scored.append((bool(ph), nm + ad, u, h, when, nm, ad, ph))
    scored.sort(key=lambda s: (not s[0], -s[1]))
    has_phone, _, u, h, when, nm, ad, ph = scored[0]
    any_nm, any_ad = any(s[5] for s in scored), any(s[6] for s in scored)
    row["retrieved_at"] = when
    texts = [all_text(p[1]) for p in pages]
    row.update(stated_facts([visible_text(p[1]) for p in pages]))
    row["office_hours"] = next((x for x in (hours_on_page(p[1]) for p in pages) if x), "")
    row["manager_name"] = next((x for x in (manager_on_page(p[1]) for p in pages) if x), "")
    if not has_phone:
        row["confidence"] = "low"
        row["note"] = "; ".join(notes + [f"no phone number on the fetched page(s): {', '.join(p[0] for p in pages)}"] + tried)
        return row
    phone, how = choose_phone(h, ph, t["address"])
    ph = [(phone, how)] + [x for x in ph if x[0] != phone]
    row["leasing_phone"], row["phone_page_url"] = phone, u
    named = bool(name_tokens(t["building_name"]))
    host = bc.host_of(u)
    housenum = squash(t["building_name"]).split()[0] if squash(t["building_name"]) else ""
    if nm and ad:
        conf = "high"
    elif ad and address_named(t["building_name"], t["address"]) and housenum and housenum in host:
        conf = "high"
        notes.append("the building is named after its address; the address is on the page and the site's domain carries it")
    elif ad and not named:
        conf = "medium"
        notes.append("the address is on the page; the data has no building name to match")
    elif ad and not nm:
        conf = "medium"
        notes.append("the address is on the page; the building's name as held in the data is not (or is only the address)")
    elif nm:
        conf = "medium"
        notes.append("the building's name is on the page; its street address is not")
    else:
        conf = "low"
        notes.append("neither the building's name nor its address is on the page that carries the phone")
    if conf != "high" and (any_nm and any_ad) and (nm or ad):
        notes.append("name and address both appear across the two fetched pages")
    notes.append(f"phone read from {how}")
    others = [p for p, _ in ph[1:4]]
    if others:
        notes.append("other numbers on the page: " + ", ".join(others))
    if phone[1:4] not in bc.LOCAL_CODES and not bc.is_tollfree(phone):
        notes.append(f"area code {phone[1:4]} is outside NY/NJ/CT: may be a vendor call-tracking line")
    if bc.is_tollfree(phone):
        notes.append("toll-free number: may be a vendor call-tracking line or a central leasing line")
    if old and old == phone:
        notes.append("same number as building_contacts.csv")
    elif old:
        notes.append(f"replaces {old} in building_contacts.csv ({t['why'].replace('_', ' ')})")
    row["confidence"] = conf
    row["note"] = "; ".join(notes + tried)
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fetch", action="store_true", help="fetch pages that are not cached yet")
    ap.add_argument("--limit", type=int, default=0, help="stop fetching after this many buildings (0 = no limit)")
    a = ap.parse_args(argv)

    seeds = load_seeds()
    targets = load_targets(seeds)
    _, prior = bc.build_index()
    (RAW / SRC).mkdir(parents=True, exist_ok=True)
    fx = bc.Fetcher(prior)
    rows, attempted = [], 0
    for t in targets:
        with_site = bool(t["seed"] and t["seed"].get("own_site_url")) and t["contact_kind"] != "individual owner"
        can_fetch = a.fetch and with_site and attempted < MAX_BUILDINGS and not (a.limit and attempted >= a.limit)
        if with_site:
            attempted += 1
        before = fx.requests
        row = process(t, fx, can_fetch)
        rows.append(row)
        if fx.requests > before:
            print(f"{t['building_id']} {t['building_name'] or t['address']}: {row['leasing_phone'] or '-'} "
                  f"[{row['confidence'] or '-'}]", flush=True)
            write(rows)                          # written as we go
    # a number carried by several buildings' pages is the manager's shared line
    by_phone = Counter(r["leasing_phone"] for r in rows if r["leasing_phone"])
    for r in rows:
        if r["leasing_phone"] and by_phone[r["leasing_phone"]] > 1:
            r["note"] += f"; same number on {by_phone[r['leasing_phone']]} buildings in this file: the manager's shared line"
    write(rows)
    c = Counter((r["confidence"] or ("skipped" if r["note"].startswith("skipped") else "no result")) for r in rows)
    print(f"rows {len(rows)}; {dict(c)}; with phone {sum(1 for r in rows if r['leasing_phone'])}; "
          f"requests this run {fx.requests}; refused hosts {len(fx.refused)}")
    return 0


def write(rows):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(OUT)


if __name__ == "__main__":
    sys.exit(main())
