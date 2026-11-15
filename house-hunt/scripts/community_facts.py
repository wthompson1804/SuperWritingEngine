"""Building-facts pass for the property-management communities in data/listings_raw/mgmt_*.csv.

For every community with at least one studio / 1BR row at listed_rent <= $2,850, read the community's own pages
(overview, amenities, pet policy, FAQ, fees, parking: whatever the site has) and record the gate facts, each with
the page URL it came from and a short verbatim snippet.

Output: data/reference/community_facts.csv (one row per community, rewritten in full each run, nearest first).

Rules kept (docs/HARVEST_AGENT_BRIEF.md): robots.txt incl. Claude-named groups, Crawl-delay, >= 2 s per host,
stop at 401/403/429/challenge pages (the host is then skipped for the rest of the run and logged in `blocks`),
never invent: a fact without page text stays `unknown` (or blank) with an empty snippet.
`dogs=yes` needs the page to name dogs; "pet-friendly" alone is kept in `pet_policy_text` and dogs stays unknown.

Idempotent / resumable: every fetch goes through lib.cached_get (raw/community_facts/ or the mgmt_* cache the unit
harvest already filled); failed fetches are remembered in raw/community_facts/_fetch_state.json so a re-run does
not hit them again (pass --retry to try them again, --refresh to refetch everything, --limit N for a short run,
--stop-at 2026-11-15T20:00:00+00:00 to stop starting new communities at a set UTC time; the CSV then holds the
nearest communities processed so far).

Two sources are structured page data rather than prose (snippets then quote the data field, marked `[page data]`):
  greystar.com   property page, Next.js payload: about.buildingType, amenities, features, fees[]
  avaloncommunities.com  community + unit page, Fusion.globalContent: policies, fees, utilities, communityFeatures
"""
from __future__ import annotations

import csv
import glob
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from h_mgmt_common import BotWall, grid, polite_get  # noqa: E402

ROOT = lib.ROOT
SRC = "community_facts"
OUT = ROOT / "data" / "reference" / "community_facts.csv"
STATE = ROOT / "raw" / SRC / "_fetch_state.json"
CAP = 2850
REFRESH = "--refresh" in sys.argv
RETRY = "--retry" in sys.argv
LIMIT = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
MAX_EXTRA_PAGES = 2  # coordinator: one or two pages per community beyond the page already cached
STOP_AT = sys.argv[sys.argv.index("--stop-at") + 1] if "--stop-at" in sys.argv else ""  # UTC ISO time: stop starting new communities

# cache folder used by the unit harvest for each CSV (so already-fetched pages are reused, not refetched)
CACHE_SRC = {"mgmt_avalon": "mgmt_avalon", "mgmt_blt": "mgmt_blt", "mgmt_fairfield": "mgmt_fairfield",
             "mgmt_gardencommunities": "mgmt_gardencommunities", "mgmt_gardenhomes": "mgmt_gardenhomes",
             "mgmt_gdc": "mgmt_gdc", "mgmt_greystar": "mgmt_greystar", "mgmt_newport": "mgmt_newport",
             "mgmt_russo": "mgmt_russo", "mgmt_sightmap_sites": "mgmt_sightmap_sites"}
MANAGER = {"mgmt_avalon": ("AvalonBay Communities", r"AvalonBay|Avalon Communities"),
           "mgmt_blt": ("BLT (Building and Land Technology)", r"BLT\b|Building and Land Technology"),
           "mgmt_fairfield": ("Fairfield Properties", r"Fairfield Properties"),
           "mgmt_gardencommunities": ("Garden Communities", r"Garden Communities"),
           "mgmt_gardenhomes": ("Garden Homes Management", r"Garden Homes"),
           "mgmt_gdc": ("GDC (Ginsburg Development Companies)", r"\bGDC\b|Ginsburg"),
           "mgmt_greystar": ("Greystar", r"Greystar"),
           "mgmt_newport": ("LeFrak (Newport)", r"LeFrak|Newport"),
           "mgmt_russo": ("Russo Development (Vermella)", r"Russo|Vermella"),
           "mgmt_sightmap_sites": ("", r"TRITEC|Tritec")}

FACTS = ["elevator", "building_type", "floors_total", "highest_floor_mentioned", "dogs", "pet_policy_text",
         "dog_weight_limit_lb", "breed_restrictions", "max_pets", "pet_rent_monthly", "pet_one_time_fee",
         "parking_type", "parking_fee_monthly", "parking_included", "required_monthly_fees", "utilities_included",
         "utilities_resident_pays", "pool", "dog_park_pet_spa", "gym", "package_room", "controlled_access",
         "coworking", "manager", "year_built"]
COLS = (["source_site", "building_name", "address", "city", "state", "zip", "drive_min", "community_url",
         "community_website", "qualifying_rows", "min_listed_rent"]
        + [c for f in FACTS for c in (f, f + "_source_url", f + "_snippet")]
        + ["dogs_basis", "pages_read", "blocks", "notes", "retrieved_at"])

# ---------------------------------------------------------------- fetch layer

_state: dict = {}
_blocked_hosts: dict[str, str] = {}


def load_state() -> None:
    global _state
    if STATE.exists():
        _state = json.loads(STATE.read_text())


def save_state() -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(_state, indent=0))


def fetch(url: str, src: str = SRC):
    """Return (html, meta) or (None, reason). Never raises; bot walls block the host for the rest of the run."""
    host = urlparse(url).netloc.lower()
    if host in _blocked_hosts:
        return None, _blocked_hosts[host]
    if url in _state and not (RETRY or REFRESH):
        st = _state[url]
        if st.startswith("blocked"):
            _blocked_hosts[host] = st
        return None, st
    try:
        html, m = polite_get(url, src, refresh=REFRESH)
    except BotWall as e:
        reason = "blocked: " + str(e)[:140]
        _blocked_hosts[host] = reason
        _state[url] = reason
        save_state()
        return None, reason
    except Exception as e:  # network failure
        reason = "error: " + str(e)[:140]
        _state[url] = reason
        save_state()
        return None, reason
    if m["status"] != 200:
        reason = f"http {m['status']}"
        _state[url] = reason
        save_state()
        return None, reason
    return html, m


# ---------------------------------------------------------------- html -> segments

AGO = re.compile(r"^(a|an|\d+) (day|week|month|year)s? ago$", re.I)


def segments(html: str, site: str = "") -> list[str]:
    """Visible text as short lines (list items, paragraphs split into sentences). Nav / header / footer dropped.
    Embedded resident reviews (lines around 'N weeks ago') are dropped: they are not statements by the manager."""
    s = BeautifulSoup(html, "lxml")
    for t in s(["script", "style", "noscript", "nav", "header", "footer", "select", "svg", "template"]):
        t.decompose()
    lines = []
    for ln in s.get_text("\n").split("\n"):
        ln = re.sub(r"\s+", " ", ln.replace("​", "")).strip()
        if len(ln) > 2:
            lines.append(ln)
    ago = [i for i, ln in enumerate(lines) if AGO.match(ln)]
    if len(ago) >= 2:
        lines = lines[:max(0, ago[0] - 3)] + lines[ago[-1] + 8:]
    lines = site_trim(lines, site)
    out = []
    for ln in lines:
        if len(ln) <= 320:
            out.append(ln)
        else:
            for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z*o•])", ln):
                out.append(sent[:400])
    return out


def site_trim(lines: list[str], site: str) -> list[str]:
    """Cut cross-community text (other communities' blurbs, site-wide link lists) so facts cannot leak between them."""
    def cut_at(pat):
        for i, ln in enumerate(lines):
            if re.match(pat, ln):
                return lines[:i]
        return lines
    if site == "mgmt_fairfield":
        lines = cut_at(r"^(PROPERTIES IN THIS COMMUNITY|Apartment Styles|Contact Us)$")
        lines = [ln for ln in lines if ln not in ("Home", "Apartment Communities")]
    elif site == "mgmt_gardencommunities":
        lines = cut_at(r"^Nearby Properties$")
        lines = [ln for ln in lines if not re.match(r"^(Pet-Friendly Communities|Public Transit Communities|.* County Apartments)$", ln)]
    elif site == "mgmt_gdc":
        lines = cut_at(r"^(NAVIGATION|APARTMENTS FOR RENT)$")
    return lines


def candidates(url: str, segs: list[str]) -> list[tuple[str, str]]:
    """Each line, plus 'heading | value' pairs so that 'Pet Rent' / '$50' on two lines can be read together."""
    out = [(url, s) for s in segs]
    for a, b in zip(segs, segs[1:]):
        if (len(a) < 45 or len(b) < 45) and len(a) + len(b) < 380:
            out.append((url, a + " | " + b))
    return out


LINK_KW = re.compile(r"(?i)amenit|pet|faq|fee|parking|feature|polic")
LINK_SKIP = re.compile(r"(?i)privacy|cookie|/feed|\.(css|js|png|jpe?g|svg|pdf|webp|ico)(\?|$)|^data:|^mailto:|^tel:|javascript:|"
                       r"petscreening|ourpetpolicy|floor-?plan|gallery|photo")


def discover(home_url: str, html: str) -> list[str]:
    """Same-host links from the home page that look like amenities / pet / FAQ / fees / parking / features pages."""
    host = urlparse(home_url).netloc.lower().removeprefix("www.")
    found: dict[str, int] = {}
    s = BeautifulSoup(html, "lxml")
    for a in s.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(" ", strip=True)
        if LINK_SKIP.search(href) or href.startswith("#"):
            continue
        if not (LINK_KW.search(href) or LINK_KW.search(text[:40])):
            continue
        u = urljoin(home_url, href).split("#")[0]
        if urlparse(u).netloc.lower().removeprefix("www.") != host or urlparse(u).scheme not in ("http", "https"):
            continue
        key = u.rstrip("/").lower()
        if key == home_url.rstrip("/").lower():
            continue
        blob = (href + " " + text).lower()
        rank = 0 if "pet" in blob else 1 if "faq" in blob else 2 if "amenit" in blob else 3 if "feature" in blob else 4
        if key not in found or rank < found[key][0]:
            found[key] = (rank, u)
    return [u for _, u in sorted(found.values())][:MAX_EXTRA_PAGES]


# ---------------------------------------------------------------- fact extraction from text

WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
           "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
           "eighteen": 18, "nineteen": 19, "twenty": 20}
ORD = {"second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
       "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15, "sixteenth": 16,
       "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20}


def num(x: str) -> int:
    return int(x) if x.isdigit() else WORDNUM[x.lower()]


def snip(text: str, m: re.Match | None = None, width: int = 240) -> str:
    text = text.strip()
    if len(text) <= width or m is None:
        return text[:width]
    a = max(0, m.start() - width // 2)
    return ("…" if a else "") + text[a:a + width] + ("…" if a + width < len(text) else "")


def first(cands, pat, flags=re.I, where=None, veto=None):
    rx = re.compile(pat, flags)
    for url, t in cands:
        if where and not where.search(t):
            continue
        if veto and veto.search(t):
            continue
        m = rx.search(t)
        if m:
            return url, t, m
    return None


def collect(cands, pat, where=None, veto=None, limit=3):
    """Up to `limit` distinct matching lines: [(url, text, match)]. Shorter lines first (they are the cleaner quote)."""
    rx = re.compile(pat, re.I)
    seen, out = set(), []
    for url, t in cands:
        if where and not where.search(t):
            continue
        if veto and veto.search(t):
            continue
        m = rx.search(t)
        if m and t not in seen and not any(t in s or s in t for s in seen):
            seen.add(t)
            out.append((url, t, m))
    return out[:limit]


def put(row, fact, value, hits):
    """hits: list of (url, text, match). Value with its source URL(s) and snippet(s)."""
    if not hits:
        return
    row[fact] = value
    urls = []
    for u, _, _ in hits:
        if u not in urls:
            urls.append(u)
    row[fact + "_source_url"] = " | ".join(urls)
    row[fact + "_snippet"] = " || ".join(snip(t, m) for _, t, m in hits)[:600]


PETW = re.compile(r"(?i)\bpets?\b|\bdogs?\b|\bcats?\b|\bcanine|\banimals?\b|\bbreeds?\b")
DOG_NO = re.compile(r"(?i)\bno (pets|dogs)\b(?! (fee|rent|deposit))|\b(pets?|dogs?) (are |is )?not (allowed|permitted|accepted)(?! (in|on|at|inside|within))"
                    r"|\bcats only\b|\bpet[- ]free (community|building)|\bno[- ]pets? (policy|community|building)|sorry,? no (pets|dogs)")
DOG_POLICY = re.compile(r"(?i)\bdogs? (are |is )?(welcome|allowed|permitted|accepted)|\bcats? ?(and|&|or|/) ?dogs?\b|\bdogs? ?(and|&|or|/) ?cats?\b"
                        r"|\bper dog\b|\bdogs?:? ?\$\d|\bdog (fee|rent|deposit)s?\b|\bdog[- ]friendly|\bdogs?:\s|\bdogs? (up to|under|over|weigh)"
                        r"|\b(welcome|allow|accept)s?\b[^.|]{0,40}\bdogs?\b|\bpet dog\b|\b(large|small) dogs?\b|\bdogs? (must|may|should)\b")
DOG_AMENITY = re.compile(r"(?i)\bdog (run|park|wash|spa|station|grooming|walk|area|lounge|washing)s?\b|\bbark park|\bpaw wash|\bcanine")
PET_POLICYISH = re.compile(r"(?i)pet[- ]?friendly|pets? (are |is )?(welcome|allowed|accepted|permitted)|pet policy|pet (fee|rent|deposit)|"
                           r"\bbreeds?\b|weight limit|pets? (allowed|welcome)|we love (your )?pets|furry")


def extract_text_facts(row: dict, cands: list[tuple[str, str]]) -> None:
    """Fill any fact still empty from page text. cands = [(url, line)] in page order (most specific pages first)."""
    def empty(f):
        return not row.get(f) or row.get(f) == "unknown"

    # --- elevator, building type, floors
    if empty("elevator"):
        h = first(cands, r"\bno elevators?\b|\bwalk[- ]?ups?\b(?! to)|without (an )?elevator")
        if h:
            put(row, "elevator", "no", [h])
        else:
            hs = collect(cands, r"\belevators?\b", limit=2)
            if hs:
                put(row, "elevator", "yes", hs)
    if empty("building_type"):
        types, hits = [], []
        for label, pat in (("high-rise", r"\bhigh[- ]?rise"), ("mid-rise", r"\bmid[- ]?rise"), ("low-rise", r"\blow[- ]?rise"),
                           ("garden-style", r"\bgarden[- ]style|\bgarden apartments?\b"),
                           ("townhome", r"\btown\s?ho(me|use)s?\b"), ("loft", r"\bloft[- ]style"),
                           ("tower", r"\btowers?\b"), ("boutique building", r"\bboutique[- ](scaled )?(building|community)")):
            h = first(cands, pat)
            if h:
                types.append(label)
                hits.append(h)
        if types:
            put(row, "building_type", "; ".join(types), hits[:3])
    if empty("floors_total"):
        h = first(cands, r"\b(\d{1,2}|" + "|".join(WORDNUM) + r")[- ]?stor(?:y|ies|ey)\b(?=[^.|]{0,30}(building|tower|communit|campus|complex|mid-rise|high-rise))(?![^.|]{0,25}(clubhouse|lobby|fitness|lounge|penthouse|atrium|gym|amenity|townho|loft|window|ceiling|parking|garage))"
                         r"|\b(\d{1,2}) floors of (apartments|residences|homes)")
        if h:
            g = h[2].group(1) or h[2].group(3)
            put(row, "floors_total", str(num(g)), [h])
    if empty("highest_floor_mentioned"):
        best = None
        rx = re.compile(r"(?i)\b(?:(\d{1,2})(?:st|nd|rd|th)|(" + "|".join(ORD) + r"))[- ]floor\b")
        for url, t in cands:
            for m in rx.finditer(t):
                n = int(m.group(1)) if m.group(1) else ORD[m.group(2).lower()]
                if n < 70 and (best is None or n > best[0]):
                    best = (n, (url, t, m))
        if best:
            put(row, "highest_floor_mentioned", str(best[0]), [best[1]])

    # --- pets
    petc = [(u, t) for u, t in cands if PETW.search(t)]
    if empty("dogs"):
        no = first(petc, DOG_NO.pattern)
        pol = collect(petc, DOG_POLICY.pattern, limit=2)
        amen = collect(petc, DOG_AMENITY.pattern, limit=2)
        if pol and no:
            put(row, "dogs", "conflict", pol[:1] + [no])
            row["dogs_basis"] = "page has both an allow and a deny statement"
        elif pol:
            put(row, "dogs", "yes", pol)
            row["dogs_basis"] = "policy text names dogs"
        elif no:
            put(row, "dogs", "no", [no])
            row["dogs_basis"] = "policy text"
        elif amen:
            put(row, "dogs", "yes", amen)
            row["dogs_basis"] = "dog amenity only (dog run / dog park / dog wash on site); no policy sentence"
    if empty("pet_policy_text"):
        hs = collect(petc, PET_POLICYISH.pattern, veto=re.compile(r"(?i)^pet (policy|rent|fee|deposit)( type)?:?$"), limit=3)
        if hs:
            put(row, "pet_policy_text", " / ".join(snip(t, m, 160) for _, t, m in hs)[:400], hs)
    if empty("dog_weight_limit_lb"):
        wc = [(u, t) for u, t in cands if re.search(r"(?i)\bpets?\b|\bdogs?\b|\bweight\b|\bbreeds?\b|\banimals?\b", t)]
        h = first(wc, r"\bno (weight|size) (limit|restriction)s?|\b(all|any) (sizes?|weights?)\b|regardless of (size|weight)|no (breed|weight) (or|and|&) (weight|breed|size) (limit|restriction)s?")
        if h:
            put(row, "dog_weight_limit_lb", "none (page says no limit)", [h])
        else:
            vals, hits = [], []
            for h in collect(wc, r"(\d{2,3})\s*(?:-\s*)?(?:lbs?\b\.?|pounds?\b|lb\.|#)", limit=3):
                for v in re.findall(r"(?i)(\d{2,3})\s*(?:-\s*)?(?:lbs?\b|pounds?\b|lb\.|#)", h[1]):
                    if v not in vals:
                        vals.append(v)
                hits.append(h)
            if vals:
                put(row, "dog_weight_limit_lb", ";".join(vals), hits)
    if empty("breed_restrictions"):
        h = first(petc, r"\bno breed (or weight |or size )?restrictions?|\ball breeds\b|\bany breed\b|no (weight|size) (or|and|&) breed restrictions?")
        if h:
            put(row, "breed_restrictions", "no", [h])
        else:
            h = first(petc, r"breed restrictions?|restricted breeds?|breeds? (are |is )?(restricted|prohibited|not (allowed|permitted|accepted))|"
                            r"aggressive breeds?|certain breeds|following breeds|breed limitations?|non-aggressive")
            if h:
                put(row, "breed_restrictions", "yes", [h])
    if empty("max_pets"):
        n = "|".join(["\\d"] + list(WORDNUM)[:5])
        h = first(petc, rf"\b(?:maximum|max\.?|limit)(?: of)?\s*({n})\s*(?:\(\d\)\s*)?(?:pets?|animals?|dogs?)\b"
                        rf"|\b({n})\s*(?:\(\d\)\s*)?(?:pets?|animals?)\s*(?:per|max|maximum|limit|allowed|are allowed|permitted|are permitted)\b"
                        rf"|\bup to ({n})\s*(?:\(\d\)\s*)?(?:pets?|animals?|dogs?)\b|\b({n})[- ]pet (?:max|maximum|limit)")
        if h:
            g = next(x for x in h[2].groups() if x)
            put(row, "max_pets", str(num(g)), [h])
    money_pet = [(u, t) for u, t in petc if "$" in t]
    dog_first = sorted(money_pet, key=lambda c: 0 if re.search(r"(?i)\bdogs?\b", c[1]) else 1)
    if empty("pet_rent_monthly"):
        h = first(dog_first, r"\$\s?(\d{2,3})(?:\.\d\d)?(?![\d,])[^|;$]{0,45}?(?:per month|/\s?mo\b|monthly|a month|/\s?month|pet rent|per dog)"
                             r"|(?:pet rent|monthly (?:pet )?(?:fee|rent|charge)s?|per month)[^$|]{0,45}\$\s?(\d{2,3})(?![\d,])")
        if h:
            put(row, "pet_rent_monthly", h[2].group(1) or h[2].group(2), [h])
    if empty("pet_one_time_fee"):
        h = first(dog_first, r"\$\s?(\d{2,4})(?:\.\d\d)?(?![\d,])[^|;$]{0,45}?(one[- ]time|non-?refundable|pet fee|deposit|per pet fee)"
                             r"|(one[- ]time|non-?refundable|pet deposit|pet fee|security deposit)[^$|]{0,45}\$\s?(\d{2,4})(?![\d,])")
        if h:
            m = h[2]
            amt, kind = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
            put(row, "pet_one_time_fee", f"{amt} ({kind.lower()})", [h])

    # --- parking
    PARK = re.compile(r"(?i)\bparking\b|\bgarages?\b|\bcarports?\b")
    parkc = [(u, t) for u, t in cands if PARK.search(t) and not re.search(r"(?i)bike|bicycle|parking lot sale", t)]
    if empty("parking_type"):
        types, hits = [], []
        for label, pat in (("garage", r"\bgarages?\b"), ("covered", r"\bcovered parking|\bcarports?\b|\bunderground parking|\bindoor parking"),
                           ("gated lot", r"\bgated parking|\bsecured? parking|\bcontrolled[- ]access (parking|garage)"),
                           ("open lot", r"\boff[- ]street parking|\bsurface (lot|parking)|\bparking lots?\b|\boutdoor (&|and)?[^|.]{0,12}parking|\bample parking|\bopen parking|\bassigned parking|\breserved parking|\bon-?site parking|\bfree parking|\bresident parking|\bprivate parking"),
                           ("street", r"(?<!off[- ])\bstreet parking|\bon[- ]street")):
            h = first(parkc, pat)
            if h:
                types.append(label)
                if not any(h[1] == x[1] for x in hits):
                    hits.append(h)
        if types:
            put(row, "parking_type", "; ".join(types), hits[:3])
        elif parkc:
            h = first(parkc, PARK.pattern)
            put(row, "parking_type", "parking mentioned, type not stated", [h])
    if empty("parking_fee_monthly"):
        h = first(parkc, r"\$\s?(\d{2,3})(?:\.\d\d)?(?![\d,])[^|;$]{0,40}?(?:per month|/\s?mo\b|monthly|a month|/\s?month|per (space|spot|car|vehicle))"
                         r"|(?:parking|garage)[^$|]{0,40}\$\s?(\d{2,3})(?![\d,])", veto=re.compile(r"(?i)\bpets?\b|guest|visitor"))
        if h:
            put(row, "parking_fee_monthly", h[2].group(1) or h[2].group(3), [h])
        else:
            h = first(parkc, r"additional (monthly )?(fee|cost|charge)|for a(n additional)? (monthly )?fee|parking fees? appl|available for rent|fees? may apply",
                      veto=re.compile(r"(?i)guest|visitor"))
            if h:
                put(row, "parking_fee_monthly", "fee charged, amount not stated", [h])
    if empty("parking_included"):
        h = first(parkc, r"parking (is |space )?included|\bfree (resident |on-?site |off-?street )?parking|complimentary (resident )?parking|"
                         r"\b(one|1|two|2) (assigned |reserved |parking |garage )*(space|spot)s? (is |are )?(included|per (apartment|unit|home))|"
                         r"parking at no (additional|extra) (cost|charge)|includes? (one|1|a|an) (assigned |reserved )?(parking|garage) (space|spot)|no (charge|fee) for parking",
                  veto=re.compile(r"(?i)guest|visitor"))
        if h:
            put(row, "parking_included", "yes", [h])
        elif row.get("parking_fee_monthly"):
            row["parking_included"] = "no (fee stated)"
            row["parking_included_source_url"] = row.get("parking_fee_monthly_source_url", "")
            row["parking_included_snippet"] = row.get("parking_fee_monthly_snippet", "")

    # --- fees and utilities
    if empty("required_monthly_fees"):
        hs = collect(cands, r"(amenity|trash|technology|tech package|pest|administrative|admin|community|package|cable|internet|wi-?fi|utility|water|sewer)"
                            r"[^|$]{0,50}\$\s?\d{1,3}(?![\d,])[^|$]{0,30}(month|/\s?mo\b)",
                     where=re.compile(r"(?i)fee|package|charge|required|mandatory"),
                     veto=re.compile(r"(?i)\bpets?\b|\bdogs?\b|\bcats?\b|parking|garage|application|storage|late fee|deposit|from \$|starting at"), limit=3)
        if hs:
            put(row, "required_monthly_fees", " / ".join(snip(t, m, 120) for _, t, m in hs)[:300], hs)
    UT = (("heat", r"\bheat(ing)?\b"), ("hot water", r"\bhot water\b"), ("water", r"(?<!hot )\bwater\b"), ("sewer", r"\bsewer"),
          ("gas", r"\bgas\b"), ("electric", r"\belectric"), ("trash", r"\btrash|\bgarbage|\brefuse"),
          ("internet", r"\binternet|\bwi-?fi"), ("cable", r"\bcable\b"))

    def ut_names(t):
        return [n for n, p in UT if re.search("(?i)" + p, t)]
    if empty("utilities_included"):
        hs = collect(cands, r"utilities included:?|included in (the |your )?(monthly )?rent|(heat|hot water|gas|water|electric\w*|sewer|trash|wi-?fi|internet)[^.|]{0,60}\b(is |are )?included\b|"
                            r"\b(rent )?includes? (free )?(heat|hot water|gas|water|electric|all utilities|utilities)|\bfree (heat|hot water|gas|utilities)|all utilities (are )?included",
                     veto=re.compile(r"(?i)not included|cable ready|gas (range|cooking|stove|grill|fireplace)s?$"), limit=2)
        hs = [h for h in hs if ut_names(h[1]) or re.search(r"(?i)all utilities", h[1])]
        if hs:
            names = []
            for h in hs:
                for n in (["all utilities"] if re.search(r"(?i)all utilities", h[1]) else []) + ut_names(h[1]):
                    if n not in names:
                        names.append(n)
            put(row, "utilities_included", "; ".join(names), hs)
    if empty("utilities_resident_pays"):
        h = first(cands, r"residents? (is |are )?responsib\w+( for)?:?|resident responsibilit\w+:?|tenants? pays?|residents? pays?|tenant (is )?responsible")
        if h and ut_names(h[1]):
            put(row, "utilities_resident_pays", "; ".join(ut_names(h[1])), [h])

    # --- on-site features
    if empty("pool"):
        hs = collect(cands, r"\b(swimming )?pools?\b(?! table)|\bswimming\b", veto=re.compile(r"(?i)car ?pool|pool table|billiard|whirlpool tub$"), limit=3)
        if hs:
            blob = " ".join(t for _, t, _ in hs)
            ind, outd = re.search(r"(?i)indoor[^|.]{0,25}pool|indoor/outdoor", blob), re.search(r"(?i)outdoor[^|.]{0,25}pool|rooftop pool|pool[^|.]{0,20}(sundeck|sun deck|cabana)|indoor/outdoor|seasonal", blob)
            put(row, "pool", "indoor and outdoor" if ind and outd else "indoor" if ind else "outdoor" if outd else "yes (indoor/outdoor not stated)", hs[:2])
    for fact, pat, veto in (
        ("dog_park_pet_spa", r"\bdog (run|park|wash|spa|washing|grooming)s?\b|\bbark park|\bpet (spa|wash|park|grooming|salon|washing|run|area|care)s?\b|\bpaw (wash|spa)|\bgrooming (station|room|salon)", None),
        ("gym", r"\bfitness (cent(er|re)|studio|room|club|facilit|area|and yoga|&)|\bgym(nasium)?s?\b|\bstate-of-the-art fitness|\byoga (studio|room)|\bhealth club|\bfitness\b", None),
        ("package_room", r"\bpackage (room|locker|concierge|acceptance|receiving|service|system|hub|center|delivery)s?|\bparcel|\bamazon hub|\bluxer|\bpackage lockers?", None),
        ("controlled_access", r"\bcontrolled[- ]access|\bgated (community|entr|access)|\bkey ?fob|\bkeyless|\bsecured? (entry|access|building|lobby|entrance)|\bintercom|\bdoorm[ae]n|\bconcierge|"
                              r"\b24[- /]?(hour|hr|7) (security|attended|concierge)|\bsecurity (guard|patrol|camera|system)|\bvideo (entry|intercom)|\blimited access|\battended lobby|\bbutterflymx|\bLatch\b", re.compile(r"(?i)package concierge")),
        ("coworking", r"\bco-?working|\bbusiness cent(er|re)|\bwork lounge|\bconference rooms?|\bwork ?spaces?\b|\bprivate (offices?|work)|\bwork pods?|\bworkstations?\b|\bwork[- ]from[- ]home", None),
    ):
        if empty(fact):
            hs = collect(cands, pat, veto=veto, limit=2)
            if hs:
                put(row, fact, "yes", hs)
    if empty("year_built"):
        h = first(cands, r"\b(?:built|constructed|completed|opened|established|erected|renovated)\s+in\s+((?:19|20)\d\d)\b|\byear built:?\s*((?:19|20)\d\d)\b")
        if h and not re.search(r"(?i)renovated in", h[2].group(0)):
            put(row, "year_built", h[2].group(1) or h[2].group(2), [h])


# ---------------------------------------------------------------- structured page data (Greystar, Avalon)

def greystar_struct(row: dict, html: str, url: str) -> tuple[list[str], str]:
    """Fill fee / type facts from the Next.js payload. Returns (text lines for the prose extractor, community website)."""
    import h_mgmt_greystar as G
    s = G.flight(html)
    prop = G.grab(s, "property", '{"id"')
    if not prop:
        return [], ""
    about = prop.get("about") or {}
    hit = lambda text: [(url, "[page data] " + text, None)]  # noqa: E731
    if about.get("buildingType"):
        put(row, "building_type", about["buildingType"].lower(), hit(f"buildingType: {about['buildingType']}"))
    fees = [f for f in (prop.get("fees") or []) if f.get("isEnabled", True)]

    def desc(f):
        d = f"{f.get('label')}: {G.amt(f)} ({f.get('frequency')}; required={f.get('isRequired')}; included={f.get('isIncluded')})"
        return d + (f" - {f['disclaimer']}" if f.get("disclaimer") else "")
    pets = [f for f in fees if f.get("category") == "pets" or re.search(r"(?i)\bpet\b|\bdog\b", f.get("label", ""))]
    prent = [f for f in pets if f.get("frequency") == "monthly"]
    ponce = [f for f in pets if f.get("frequency") == "one_time"]
    dogf = lambda fs: sorted(fs, key=lambda f: 0 if re.search(r"(?i)dog", f.get("label", "") + str(f.get("type"))) else 1)  # noqa: E731
    if prent:
        put(row, "pet_rent_monthly", "; ".join(dict.fromkeys(G.amt(f) for f in dogf(prent))), hit(" ; ".join(desc(f) for f in dogf(prent))))
    if ponce:
        put(row, "pet_one_time_fee", "; ".join(dict.fromkeys(f"{G.amt(f)} ({f.get('label')})" for f in dogf(ponce))), hit(" ; ".join(desc(f) for f in dogf(ponce))))
    park = [f for f in fees if (f.get("group") == "parking" or re.search(r"(?i)parking|garage|carport", f.get("label", "")))]
    pmon = [f for f in park if f.get("frequency") == "monthly"]
    if pmon:
        put(row, "parking_fee_monthly", "; ".join(f"{f.get('label')}: {G.amt(f)}" for f in pmon), hit(" ; ".join(desc(f) for f in pmon)))
        if any(f.get("isIncluded") for f in pmon):
            put(row, "parking_included", "yes", hit(" ; ".join(desc(f) for f in pmon if f.get("isIncluded"))))
        else:
            put(row, "parking_included", "no (fee stated)", hit(" ; ".join(desc(f) for f in pmon)))
    monthly = [f for f in fees if f.get("frequency") == "monthly"]
    req = [f for f in monthly if f.get("isRequired") and not f.get("isIncluded")]
    rmin, rmax = prop.get("requiredMonthlyFeesMin"), prop.get("requiredMonthlyFeesMax")
    if req or rmin is not None:
        val = "; ".join(f"{f.get('label')}: {G.amt(f)}" for f in req)
        tot = f"requiredMonthlyFeesMin: {rmin}; requiredMonthlyFeesMax: {rmax}"
        put(row, "required_monthly_fees", f"{val} [site total of priced required fees: {rmin}" + (f"-{rmax}" if rmax != rmin else "") + "]",
            hit(tot + " ; " + " ; ".join(desc(f) for f in req)))
    incl = [f for f in monthly if f.get("isIncluded")]
    if incl:
        put(row, "utilities_included", "; ".join(f.get("label") for f in incl), hit(" ; ".join(desc(f) for f in incl)))
    elif fees:
        ut = [f for f in req if f.get("group") == "utilities"]
        if ut:
            put(row, "utilities_resident_pays", "; ".join(f.get("label") for f in ut), hit(" ; ".join(desc(f) for f in ut)))
    lines = [x for x in (prop.get("amenities") or []) + (prop.get("features") or []) if isinstance(x, str)]
    for k in ("longDescription", "policies"):
        if about.get(k):
            lines += re.split(r"(?<=[.!?])\s+", about[k])
    lines += [f"{f.get('label')}" + (f" - {f['disclaimer']}" if f.get("disclaimer") else "") for f in pets]
    return lines, ((prop.get("contact") or {}).get("communityWebsiteUrl") or "").strip()


def avalon_struct(row: dict, chtml: str, curl: str, uhtml: str | None, uurl: str) -> list[tuple[str, str]]:
    import h_mgmt_avalon as A
    d = A.fusion(chtml) or {}
    ud = (A.fusion(uhtml) or {}) if uhtml else {}
    hit = lambda u, text: [(u, "[page data] " + text, None)]  # noqa: E731
    pol = ud.get("policies") or d.get("policies") or {}
    purl = uurl if ud.get("policies") else curl
    allowed = ud.get("allowedPets") or d.get("allowedPets") or []
    ptxt = (pol.get("petPolicy") or "").strip()
    if "dogs" in [a.lower() for a in allowed] or re.search(r"(?i)dogs? (are )?welcome|cats and dogs", ptxt):
        put(row, "dogs", "yes", hit(purl, f"allowedPets: {allowed}; petPolicy: {ptxt}"))
        row["dogs_basis"] = "policy text names dogs"
    elif allowed or ptxt:
        put(row, "dogs", "no" if re.search(r"(?i)no pets|not allowed", ptxt) else "unknown", hit(purl, f"allowedPets: {allowed}; petPolicy: {ptxt}"))
    if ptxt:
        put(row, "pet_policy_text", ptxt[:400], hit(purl, f"petPolicy: {ptxt}"))
    if "maximumPetWeight" in pol:
        w = pol.get("maximumPetWeight")
        put(row, "dog_weight_limit_lb", str(w) if w else "none stated", hit(purl, f"maximumPetWeight: {w}"))
    if pol.get("maximumPets"):
        put(row, "max_pets", str(pol["maximumPets"]), hit(purl, f"maximumPets: {pol['maximumPets']}"))
    rb = (pol.get("restrictedBreeds") or {}).get("breeds") or []
    if rb:
        put(row, "breed_restrictions", "yes", hit(purl, f"restrictedBreeds: {(pol['restrictedBreeds'].get('introduction') or '')}: {', '.join(rb)}"))
    fees = ud.get("fees") or []

    def fd(f):
        a = f.get("amount") or {}
        v = a.get("min") if a.get("min") == a.get("max") else f"{a.get('min')}-{a.get('max')}"
        return v, f"{f.get('name')}: {v} (dueAt={f.get('dueAt')}; optional={f.get('optional')})"
    def pick(name_rx, due):
        return [f for f in fees if re.search(name_rx, f.get("name", "")) and f.get("dueAt") == due]
    for fact, rx, due in (("pet_rent_monthly", r"(?i)dog", "Monthly"), ("pet_one_time_fee", r"(?i)dog", "MoveIn"),
                          ("parking_fee_monthly", r"(?i)parking|garage", "Monthly")):
        fs = pick(rx, due)
        if fs:
            put(row, fact, "; ".join(str(fd(f)[0]) for f in fs), hit(uurl, " ; ".join(fd(f)[1] for f in fs)))
    if row.get("parking_fee_monthly"):
        put(row, "parking_included", "no (fee stated)", hit(uurl, row["parking_fee_monthly_snippet"].replace("[page data] ", "")))
    req = [f for f in fees if f.get("dueAt") == "Monthly" and f.get("optional") is False]
    if req:
        put(row, "required_monthly_fees", "; ".join(f"{f.get('name')}: {fd(f)[0]}" for f in req), hit(uurl, " ; ".join(fd(f)[1] for f in req)))
    elif fees:
        put(row, "required_monthly_fees", "none listed as required monthly", hit(uurl, "fees[]: no entry with dueAt=Monthly and optional=false"))
    ut = ud.get("utilities") or d.get("utilities") or []
    if ut:
        uu = uurl if ud.get("utilities") else curl
        txt = "utilities: " + "; ".join(f"{u.get('name')}={u.get('responsibleSide')}" for u in ut)
        inc = [u["name"] for u in ut if str(u.get("responsibleSide", "")).lower() in ("community", "owner", "landlord", "included")]
        res = [u["name"] for u in ut if str(u.get("responsibleSide", "")).lower() == "resident"]
        put(row, "utilities_included", "; ".join(inc) if inc else "none", hit(uu, txt))
        if res:
            put(row, "utilities_resident_pays", "; ".join(res), hit(uu, txt))
    cands = []
    for src_d, u in ((ud, uurl), (d, curl)):
        for key in ("communityFeatures", "features", "unitFeatures"):
            for f in src_d.get(key) or []:
                if isinstance(f, dict):
                    t = (f.get("name") or "") + (": " + f["description"] if f.get("description") else "")
                    if t.strip():
                        cands.append((u, t.strip()))
        p = src_d.get("policies") or {}
        for key in ("residentPolicy", "futureResidentPolicy", "basicPolicy", "globalPetPolicy"):
            for sent in re.split(r"(?<=[.!?])\s+", (p.get(key) or "").strip()):
                if sent.strip():
                    cands.append((u, sent.strip()))
        if cands:
            break
    return cands


# ---------------------------------------------------------------- communities

def load_communities() -> list[dict]:
    g = grid()
    comms: dict[tuple, dict] = {}
    for path in sorted(glob.glob(str(ROOT / "data" / "listings_raw" / "mgmt_*.csv"))):
        site = Path(path).stem
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                try:
                    beds, rent = float(r["beds"]), float(r["listed_rent"])
                except ValueError:
                    continue
                if beds not in (0.0, 1.0) or rent > CAP:
                    continue
                key = (site, r["building_url"] or r["building_name"])
                c = comms.setdefault(key, {"site": site, "source_site": r["source_site"], "building_name": r["building_name"],
                                           "address": r["address"], "city": r["city"], "state": r["state"], "zip": r["zip"],
                                           "community_url": r["building_url"], "unit_url": r["url"], "unit_raw": r["raw_path"],
                                           "manager_csv": r["manager"], "n": 0, "min_rent": rent, "notes_csv": r["notes"]})
                c["n"] += 1
                c["min_rent"] = min(c["min_rent"], rent)
                for k in ("address", "city", "state", "zip"):
                    if not c[k] and r[k]:
                        c[k] = r[k]
    out = list(comms.values())
    for c in out:
        z = (c["zip"] or "")[:5]
        c["drive_min"] = g.get(z)
        if c["drive_min"] is None:  # no ZIP on the row: the unit harvest wrote the nearest grid ZCTA into notes
            m = re.search(r"\b(\d{5})\b", c["notes_csv"] or "")
            if m and m.group(1) in g:
                c["drive_min"] = g[m.group(1)]
    out.sort(key=lambda c: (c["drive_min"] if c["drive_min"] is not None else 9999, c["building_name"]))
    return out


def process(c: dict) -> dict:
    site = c["site"]
    row = {k: "" for k in COLS}
    row.update({"source_site": c["source_site"], "building_name": c["building_name"], "address": c["address"], "city": c["city"],
                "state": c["state"], "zip": c["zip"], "drive_min": "" if c["drive_min"] is None else c["drive_min"],
                "community_url": c["community_url"], "qualifying_rows": c["n"], "min_listed_rent": c["min_rent"]})
    for f in ("elevator", "dogs"):
        row[f] = "unknown"
    pages, blocks, notes, times = [], [], [], []
    cands: list[tuple[str, str]] = []
    cache = CACHE_SRC.get(site, SRC)
    home_html, home_url = None, c["community_url"]

    def get(url, src=SRC):
        html, m = fetch(url, src)
        if html is None:
            blocks.append(f"{url}: {m}")
            return None
        pages.append(url)
        times.append(m["retrieved_at"])
        return html

    if not home_url:
        notes.append("no community URL in the harvest CSV")
    elif site == "mgmt_greystar":
        html = get(home_url, cache)
        web = ""
        if html:
            lines, web = greystar_struct(row, html, home_url)
            cands += candidates(home_url, lines)
        if web:
            row["community_website"] = web
            home_html, home_url = get(web), web
            if home_html:
                cands = candidates(web, segments(home_html)) + cands
    elif site == "mgmt_avalon":
        chtml = get(home_url, cache)
        uhtml = get(c["unit_url"], cache) if c["unit_url"] and c["unit_url"] != home_url else None
        if chtml:
            try:
                cands += avalon_struct(row, chtml, home_url, uhtml, c["unit_url"])
            except Exception as e:  # payload shape changed
                notes.append("avalon page data not parsed: " + str(e)[:80])
            cands += candidates(home_url, segments(chtml))
    else:
        home_html = get(home_url, cache)
        if home_html:
            cands += candidates(home_url, segments(home_html, site))
        if site == "mgmt_fairfield" and c["unit_url"] and c["unit_url"] != home_url:
            # some Fairfield community pages carry no text; the floor-plan page (already cached) repeats the policy block
            uh = get(c["unit_url"], cache)
            if uh:
                cands += candidates(c["unit_url"], segments(uh, site))

    # sub-pages (amenities / pet / FAQ / features / parking) on the community's own site
    if home_html and site not in ("mgmt_fairfield", "mgmt_gardencommunities", "mgmt_avalon", "mgmt_gardenhomes"):
        extra = []
        for u in discover(home_url, home_html):
            if site == "mgmt_blt" and "/apartments/" in u and not u.rstrip("/").startswith(c["community_url"].rstrip("/")):
                continue  # other BLT communities
            if site == "mgmt_gdc":
                continue  # gdcrentals.com: one page per community; other links are other communities
            html = get(u)
            if html:
                extra += candidates(u, segments(html, site))
        cands = extra + cands  # dedicated pages first: their wording is the more specific

    extract_text_facts(row, cands)

    if row["pet_policy_text"] and not row["dog_weight_limit_lb"]:
        row["dog_weight_limit_lb"] = "none stated"
        row["dog_weight_limit_lb_source_url"] = row["pet_policy_text_source_url"]
        row["dog_weight_limit_lb_snippet"] = row["pet_policy_text_snippet"]
    elif row["dogs"] == "yes" and not row["dog_weight_limit_lb"]:
        row["dog_weight_limit_lb"] = "none stated"
        row["dog_weight_limit_lb_source_url"] = row["dogs_source_url"]
        row["dog_weight_limit_lb_snippet"] = row["dogs_snippet"]
    name, rx = MANAGER.get(site, ("", ""))
    name = name or c["manager_csv"]
    if name and pages:
        h = first(cands, rx, flags=0) if rx else None
        row["manager"] = name
        row["manager_source_url"] = h[0] if h else pages[0]
        row["manager_snippet"] = snip(h[1], h[2]) if h else "(operator of the site the page is on; name not in the page body)"
    row["pages_read"] = " | ".join(pages)
    row["blocks"] = " | ".join(blocks)
    row["notes"] = "; ".join(notes)
    row["retrieved_at"] = max(times) if times else ""
    return row


def write(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})
    tmp.replace(OUT)


def known(v: str) -> bool:
    return bool(v) and v not in ("unknown", "none stated")


def main() -> None:
    load_state()
    comms = load_communities()
    if LIMIT:
        comms = comms[:LIMIT]
    print("communities:", len(comms), flush=True)
    rows = []
    for i, c in enumerate(comms, 1):
        if STOP_AT and lib.now_iso() >= STOP_AT:
            print("stop time reached at community", i, flush=True)
            break
        try:
            rows.append(process(c))
        except Exception as e:  # keep going; the row records the failure
            r = {k: "" for k in COLS}
            r.update({"source_site": c["source_site"], "building_name": c["building_name"], "community_url": c["community_url"],
                      "zip": c["zip"], "elevator": "unknown", "dogs": "unknown", "notes": "processing error: " + repr(e)[:150]})
            rows.append(r)
        if i % 20 == 0:
            write(rows)
            print(f"{i}/{len(comms)}", flush=True)
    write(rows)
    save_state()
    n = len(rows) or 1
    print("rows:", len(rows), "with a page read:", sum(1 for r in rows if r["pages_read"]))
    for f in FACTS:
        print(f"  {f:26s} {sum(1 for r in rows if known(r[f])) / n:5.0%}")
    print("blocked hosts:", json.dumps(_blocked_hosts, indent=0)[:1500])


if __name__ == "__main__":
    main()
