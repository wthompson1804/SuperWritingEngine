"""thin_call_contacts: phone, hours and leasing URL for the 82 one-question buildings of the three thin experiences.

    python3 scripts/thin_call_contacts.py            # offline: only pages already cached under raw/ (no request)
    python3 scripts/thin_call_contacts.py --fetch    # then at most ONE Apartment List / Zumper page per building
                                                     # that still has no phone (never its own site, never Trulia)

Reads (never writes) data/evidence_pending/{open_questions_by_building,resolved_candidates,candidates,building_sites}.csv,
data/evidence_pending/site_pages.jsonl, data/listings.csv and the raw/ caches. The extraction functions are imported
read-only from scripts/building_contacts.py, so a number means here what it means in data/reference/building_contacts.csv.

Writes data/evidence_pending/open_questions_contacts.csv and out/call_sheet_thin_experiences.md (both rebuilt whole on
every run), raw/thin_call_contacts/ (fetched pages and `_state.json`) and, on a refusal only, one new entry in
data/evidence_pending/refused_hosts.json and raw/_host_kill_shared.json.

phone_kind
  own office         the building's or its manager's own site (JSON-LD telephone, tel: link, or the only number on the page)
  property-supplied  Apartment List `original_phone` (the number the property gave Apartment List), or the number on a
                     Zumper building page that is not a Zumper proxy line (not checked against the building's own site)
  tracking           a listing-site forwarding number (Trulia / Zillow building page, Apartment List displayed number,
                     Zumper `(844) ... ext.` proxy line). It may stop working when the listing ends.
  brokerage          the published office number of the brokerage that lists the unit (reaches the brokerage, not the building)
  broker             a brokerage is named but no number is on any cached page (phone blank)
  individual owner   the unit is listed by a person with no brokerage: no phone and no name is ever recorded
  none               a managed building with no number on any cached page

Fetch rules: hosts in data/evidence_pending/refused_hosts.json, raw/_host_kill_shared.json and every earlier harvest's
block list are never requested; one refusal (401/403/429, CAPTCHA or bot wall) ends the host and is written to both
ledgers at once; trulia.com, zillow.com, streeteasy.com and apartments.com are never requested; `lib.cached_get`
throttles and is called with retries=1 so a 429 is never retried.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import building_contacts as bc  # noqa: E402  (read-only use of its parsers)
from lib import DATA, RAW, ROOT, cached_get, now_iso  # noqa: E402

csv.field_size_limit(10 ** 9)

PEND = DATA / "evidence_pending"
OUT_CSV = PEND / "open_questions_contacts.csv"
OUT_MD = ROOT / "out" / "call_sheet_thin_experiences.md"
SRC = "thin_call_contacts"
STATE_F = RAW / SRC / "_state.json"
REFUSED_F = PEND / "refused_hosts.json"
SHARED_F = RAW / "_host_kill_shared.json"
COLS = ["year", "hood", "building", "addr_key", "leasing_phone", "phone_kind", "office_hours", "leasing_url",
        "example_url", "question", "units", "min_rent", "source_url", "retrieved_at"]
NEVER = ("trulia.com", "zillow.com", "streeteasy.com", "apartments.com")
FETCHABLE = re.compile(r"(^|\.)(apartmentlist\.com|zumper\.com)$")
REAL = ("own office", "property-supplied")
EXPERIENCE_ORDER = ["The Fresh-Start Year", "The Quiet-Street Year", "The Walk-Everywhere Year"]


def base_host(h: str) -> str:
    return h.lower().removeprefix("www.")


def kind_of(c) -> str:
    if not c["phone"]:
        return ""
    if bc.TRACK in c["note"]:
        return "tracking"
    if c["kind"] == "broker":
        return "brokerage"
    return "own office" if c["rank"] <= 10 else "property-supplied"


# ------------------------------------------------------------------------------------------------- the 82 buildings
def load_buildings():
    """The rows of open_questions_by_building.csv, each with its bkey and its candidate listings."""
    C = {r["listing_id"]: r for r in bc.read_csv(PEND / "candidates.csv")}
    groups = defaultdict(list)
    for r in bc.read_csv(PEND / "resolved_candidates.csv"):
        if r["verdict"].startswith("still_open") and r["open_questions"] == "1" and r["listing_id"] in C:
            groups[(r["year"], r["hood"], r["building"], C[r["listing_id"]]["bkey"])].append((r, C[r["listing_id"]]))
    out, used = [], set()
    for q in bc.read_csv(PEND / "open_questions_by_building.csv"):
        hit = [k for k, g in groups.items() if k[:3] == (q["year"], q["hood"], q["building"]) and k not in used
               and len(g) == int(q["units"]) and g[0][0]["source_url"] == q["example_url"]]
        if not hit:
            hit = [k for k in groups if k[:3] == (q["year"], q["hood"], q["building"]) and k not in used]
        if not hit:
            raise SystemExit(f"no candidate rows for {q['building']} ({q['hood']})")
        used.add(hit[0])
        out.append({"q": q, "bkey": hit[0][3], "rows": [c for _, c in groups[hit[0]]]})
    return out


def same_building_rows(buildings):
    """Other rows of data/listings.csv at the same building (same street address + ZIP, or same name + ZIP)."""
    import resolve_pending_thin_years as rp  # read-only: its building_key defines `bkey`
    nk = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
    by_key, by_name = defaultdict(list), defaultdict(list)
    want_key = {b["bkey"] for b in buildings}
    want_name = {(nk(b["rows"][0]["building_name"]), b["rows"][0]["zip5"]) for b in buildings
                 if len(nk(b["rows"][0]["building_name"])) >= 6 and not re.match(r"\d", b["rows"][0]["building_name"])}

    class R:  # building_key reads .address and .zip5
        __slots__ = ("address", "zip5")

    with open(DATA / "listings.csv", newline="", encoding="utf-8", errors="replace") as f:
        for x in csv.DictReader(f):
            if not x.get("raw_path"):
                continue
            r = R()
            r.address, r.zip5 = x.get("address", ""), x.get("zip5", "")
            slim = {k: x.get(k, "") for k in ("url", "raw_path", "building_url", "also_seen_at", "manager", "source_site")}
            try:
                k = rp.building_key(r)
            except Exception:
                k = ""
            if k in want_key:
                by_key[k].append(slim)
            n = (nk(x.get("building_name")), x.get("zip5", ""))
            if n in want_name:
                by_name[n].append(slim)
    for b in buildings:
        r0 = b["rows"][0]
        extra = by_key.get(b["bkey"], []) + by_name.get((nk(r0["building_name"]), r0["zip5"]), [])
        b["extra"] = list({(x["raw_path"], x["url"]): x for x in extra}.values())


def site_pages():
    """bkey -> [(path, url, retrieved_at)] own-site pages cached by the resolve pass (home page of a manager's
    portfolio site is left out: its number is the head office's, not the building's)."""
    out, sites = defaultdict(list), {}
    for x in bc.read_csv(PEND / "building_sites.csv"):
        site = (x.get("site") or "").strip()
        if site and not re.match(r"https?://", site):
            site = "https://" + site             # Zumper `homepage` is sometimes stored without a scheme
        if site and bc.is_own(site) and bc.clean_url(site):
            sites[x["bkey"]] = bc.clean_url(site)
    p = PEND / "site_pages.jsonl"
    if p.exists():
        for line in p.read_text(errors="replace").splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            site = sites.get(d.get("bkey"), "")
            site_path = bc.urlparse(site).path.rstrip("/") if site else ""
            for pg in d.get("pages") or []:
                if pg.get("status") != 200 or not pg.get("path") or not (ROOT / pg["path"]).exists():
                    continue
                if not bc.is_own(pg["url"]) or pg["url"].rstrip("/").endswith("robots.txt"):
                    continue
                if site_path and not bc.urlparse(pg["url"]).path.startswith(site_path):
                    continue                     # e.g. avaloncommunities.com/ for a building at /new-jersey/.../avalon-x
                out[d["bkey"]].append((pg["path"], pg["url"], pg.get("retrieved_at", "")))
    return out, sites


def al_listing(text: str):
    """The `listing` object of an Apartment List page (same search as building_contacts.parse_apartmentlist)."""
    fl, best = bc.al_flight(text), None
    for m in re.finditer(r'"listing":\{"rental_id"', fl):
        try:
            o, _ = bc.DEC.raw_decode(fl, m.start() + 10)
        except json.JSONDecodeError:
            continue
        if "available_units" in o and (best is None or len(o) > len(best)):
            best = o
    return best


def parse(path: str, url: str):
    """building_contacts.parse_page, plus one rule it does not have: an Apartment List page that is a single unit
    from a long-tail feed (`contract` = free: Propertyware, ListHub, Avail, Tenant Turner, Listanza; no unit count, no
    management company, no office hours) carries the number of whoever posted the unit, a private landlord or an
    individual agent, never a number known to be a brokerage's office line. That number is NOT recorded."""
    if "apartmentlist.com" in bc.host_of(url):
        try:
            o = al_listing((ROOT / path).read_text(errors="replace"))
        except OSError:
            o = None
        if o and not (o.get("total_units_count") or o.get("pmc_display_name") or o.get("office_hours_this_week")
                      or (o.get("contract") or "free") != "free"):
            if (o.get("brokerage_name") or "").strip():
                return [bc.cand(92, url, kind="broker",
                                note="single unit from an agent feed on Apartment List; the number shown is the "
                                     "poster's, not a published office line, and is not recorded")]
            return [bc.cand(95, url, kind="individual owner",
                            note="single unit posted on Apartment List with no brokerage or manager named; number not recorded")]
    try:
        return bc.parse_page(path, url)
    except (AttributeError, TypeError, ValueError, KeyError):   # a page shape the parser does not expect
        return []


def build_slug_index(idx):
    """last path segment (letters and digits only) -> [(norm_url, path, url, retrieved_at)] for cached HTML pages."""
    out = defaultdict(list)
    for k, (path, url, when) in idx.items():
        if path.endswith(".json") or "/" not in k:
            continue
        seg = re.sub(r"--\d+$", "", k.rsplit("/", 1)[1])
        seg = re.sub(r"[^a-z0-9]", "", seg)
        if len(seg) >= 8:
            out[seg].append((k, path, url, when))
    return out


def candidates_for(b, idx, spages, sites, slugs):
    pages, seen = [], set()
    r0 = b["rows"][0]

    def add(path, url, when="", own_row=False):
        if path and path not in seen and (ROOT / path).exists():
            seen.add(path)
            pages.append((path, url, when or bc.meta_of(path).get("retrieved_at", ""), own_row))

    urls, named_own = [], []
    for x in b["rows"]:
        add(x["raw_path"], x["url"], own_row=True)
    for x in b["rows"] + b.get("extra", []):
        add(x["raw_path"], x["url"])
        for col in ("url", "building_url", "also_seen_at"):
            urls += bc.urls_in(x.get(col, ""))
    # cached pages named after the building: its Apartment List page in the same state, or a page on a manager's site
    name = re.sub(r"[^a-z0-9]", "", r0["building_name"].lower())
    if len(name) >= 8 and not r0["building_name"][:1].isdigit():
        for k, path, url, when in slugs.get(name, []):
            h = bc.host_of(url)
            if "apartmentlist.com" in h and f"/{r0['state'].lower()}/" in k:
                add(path, url, when)
                urls.append(url)
            elif bc.is_own(url) and "?" not in url:
                named_own.append((path, url, when))
    mine = {bc.norm_url(x["url"]) for x in b["rows"]}
    for u in dict.fromkeys(urls):               # newest cached copy of the same URL (the resolve pass re-read them)
        hit = idx.get(bc.norm_url(u))
        if hit:
            add(hit[0], u, hit[2], own_row=bc.norm_url(u) in mine)
    cands = []
    for path, url, when, own_row in pages:
        for c in parse(path, url):
            if c["kind"] != "leasing office" and not own_row:
                continue                         # a broker or owner of ANOTHER unit at the address is not this unit's contact
            c["when"] = when
            cands.append(c)
    own = [bc.clean_url(c["site"]) for c in cands if c.get("site")]
    if sites.get(b["bkey"]):
        own.append(sites[b["bkey"]])
    own += [u for _, u, _ in named_own]
    own += [bc.clean_url(u) for u in urls if bc.is_own(u) and "?" not in u]
    own = [u for u in dict.fromkeys(own) if u and bc.is_own(u)]
    for path, url, when in named_own:
        if path not in seen:
            seen.add(path)
            for c in bc.parse_own_site((ROOT / path).read_text(errors="replace"), url, rank=9):
                c["when"] = when
                cands.append(c)
    for path, url, when in spages.get(b["bkey"], []):
        if path in seen:
            continue
        seen.add(path)
        home = bc.norm_url(url) == bc.norm_url(own[0]) if own else False
        for c in bc.parse_own_site((ROOT / path).read_text(errors="replace"), url, rank=9 if home else 10):
            c["when"] = when
            cands.append(c)
    for u in own:
        hit = idx.get(bc.norm_url(u))
        if hit and hit[0] not in seen and not hit[0].endswith(".json"):
            seen.add(hit[0])
            for c in bc.parse_own_site((ROOT / hit[0]).read_text(errors="replace"), hit[1], rank=9):
                c["when"] = hit[2]
                cands.append(c)
    return cands, own, urls


def build_row(b, cands, own):
    q = b["q"]
    cands = sorted(cands, key=lambda c: (c["rank"], -len(c.get("hours") or ""), c["src"]))
    with_phone = [c for c in cands if c["phone"]]
    managed = any(c["kind"] == "leasing office" for c in cands)
    if managed:                                  # a building-level page exists: a unit broker's line is not the office
        with_phone = [c for c in with_phone if c["kind"] == "leasing office"] or with_phone
    # own-site pages can carry several numbers; take the one most own-site pages agree on
    local = lambda p: p[1:4] in bc.LOCAL_CODES or bc.is_tollfree(p)
    supplied_local = any(10 < c["rank"] <= 30 and local(c["phone"]) for c in with_phone)
    # a manager's portfolio site can show its head office (e.g. a Florida number for a New Jersey building):
    # an out-of-area own-site number gives way to a local number the property itself supplied
    top = [c for c in with_phone if c["rank"] <= 10 and (local(c["phone"]) or not supplied_local)]
    if top:
        n = Counter(c["phone"] for c in top)
        top.sort(key=lambda c: (-n[c["phone"]], c["rank"], c["src"]))
        best = top[0]
    else:
        rest = [c for c in with_phone if c["rank"] > 10] or with_phone
        best = rest[0] if rest else None
    row = {k: "" for k in COLS}
    row.update(year=q["year"], hood=q["hood"], building=q["building"], addr_key=b["bkey"], example_url=q["example_url"],
               question=q["question"], units=q["units"], min_rent=q["min_rent"])
    if best:
        row.update(leasing_phone=best["phone"], phone_kind=kind_of(best), source_url=best["src"], retrieved_at=best["when"])
    else:
        first = cands[0] if cands else None
        if managed:
            row["phone_kind"] = "none"
        elif any(c["kind"] == "broker" for c in cands):
            row["phone_kind"] = "broker"
        elif any(c["kind"] == "individual owner" for c in cands):
            row["phone_kind"] = "individual owner"
        else:
            row["phone_kind"] = "none"
        if first:
            row.update(source_url=first["src"], retrieved_at=first["when"])
    if row["phone_kind"] not in ("brokerage", "broker", "individual owner"):
        row["office_hours"] = next((c["hours"] for c in cands if c.get("hours") and c["kind"] == "leasing office"), "")
        row["leasing_url"] = own[0] if own else ""
    return row


# ------------------------------------------------------------------------------------------------- fetch (step 2)
class Ledger:
    def __init__(self, prior: dict):
        self.own = bc.load_json(REFUSED_F, {})
        self.shared = bc.load_json(SHARED_F, {})
        self.dead = {base_host(h) for h in list(self.own) + list(self.shared) + list(prior)}

    def blocked(self, host: str) -> bool:
        h = base_host(host)
        return h in self.dead or any(h == n or h.endswith("." + n) for n in NEVER)

    def refuse(self, host: str, why: str, url: str):
        at = now_iso()
        self.dead.add(base_host(host))
        self.own = bc.load_json(REFUSED_F, {})
        self.own[base_host(host)] = {"why": why, "url": url, "at": at}
        bc.save_json(REFUSED_F, self.own)
        self.shared = bc.load_json(SHARED_F, {})
        self.shared[host] = {"reason": why, "url": url, "at": at, "by": "scripts/thin_call_contacts.py"}
        bc.save_json(SHARED_F, self.shared)


def fetch_one(url: str, led: Ledger, state: dict):
    """One GET; returns (path, retrieved_at) or (None, why). The outcome is stored so a re-run never asks twice."""
    host = bc.host_of(url)
    if url in state["urls"]:
        s = state["urls"][url]
        return (s["path"], s["at"]) if s.get("path") else (None, s.get("why", "tried before"))
    if led.blocked(host) or not FETCHABLE.search(base_host(host)):
        return None, "host not allowed"
    try:
        body, meta = cached_get(url, SRC, ext="html", retries=1, timeout=40,
                                headers={"Accept": "text/html,application/xhtml+xml"})
    except RuntimeError as e:
        why = str(e)[-120:]
        if "429" in why:
            led.refuse(host, "HTTP 429", url)
        state["urls"][url] = {"why": why, "at": now_iso()}
        bc.save_json(STATE_F, state)
        return None, why
    st = meta.get("status")
    text = body.decode("utf-8", "replace")
    if st in (401, 403, 429) or (st == 200 and len(text) < 60000 and bc.BOTWALL.search(text[:20000])):
        why = f"HTTP {st}" if st != 200 else "bot wall page"
        led.refuse(host, why, url)
        state["urls"][url] = {"why": why, "at": now_iso()}
    elif st != 200:
        state["urls"][url] = {"why": f"HTTP {st}", "at": now_iso()}
    else:
        state["urls"][url] = {"path": meta["path"], "at": meta.get("retrieved_at", "")}
    bc.save_json(STATE_F, state)
    s = state["urls"][url]
    return (s["path"], s["at"]) if s.get("path") else (None, s["why"])


def fetch_target(urls, idx, state):
    """An Apartment List / Zumper page of this building that is not on disk yet (building pages before unit pages)."""
    pick = [u for u in dict.fromkeys(urls) if FETCHABLE.search(base_host(bc.host_of(u)))
            and (u in state["urls"] or bc.norm_url(u) not in idx)]
    pick.sort(key=lambda u: (u not in state["urls"], "/apartment-buildings/" not in u and "apartmentlist.com" not in u))
    return pick[0] if pick else ""


# ------------------------------------------------------------------------------------------------- outputs
def experience(year: str) -> str:
    return re.sub(r"\bYear$", "Experience", year)


def short(u: str) -> str:
    s = re.sub(r"^https?://(www\.)?", "", u)
    return s[:60]


def write_md(rows, dropped):
    L = ["# One-question calls for the three thin experiences", "",
         "Each building below is one answer away from being considered. Buildings flagged as likely to fail the $3,000 "
         "all-in cap are left out.",
         "Source: `data/evidence_pending/open_questions_by_building.csv` (set-aside listings pass, 2026-11-16); contacts: "
         "`data/evidence_pending/open_questions_contacts.csv` (`scripts/thin_call_contacts.py`, read from pages already "
         "cached).", "",
         "How to read the phone: **office** = the building's own site; **supplied** = the number the property gave the "
         "listing site; **tracking** = a listing-site forwarding number that may stop working when the listing ends "
         "(check the building's site first); **brokerage** = the listing brokerage's office, not the building. "
         "Owner-listed units carry no phone by design: use the listing link.", ""]
    label = {"own office": "office", "property-supplied": "supplied", "tracking": "tracking", "brokerage": "brokerage"}
    order = {"own office": 0, "property-supplied": 0, "tracking": 1, "brokerage": 2, "none": 3, "broker": 3, "individual owner": 3}
    for y in EXPERIENCE_ORDER:
        g = [r for r in rows if r["year"] == y]
        if not g:
            continue
        g.sort(key=lambda r: (order[r["phone_kind"]], -int(r["units"]), r["hood"], r["building"]))
        real = sum(1 for r in g if r["phone_kind"] in REAL)
        L.append(f"## The {experience(y).removeprefix('The ')} ({len(g)} buildings, {sum(int(r['units']) for r in g)} units; "
                 f"{real} with a real office number)")
        L.append("")
        for r in g:
            if r["leasing_phone"]:
                ph = f"Phone ({label[r['phone_kind']]}): {r['leasing_phone']}"
            elif r["phone_kind"] == "individual owner":
                ph = "Phone: none (listed by an individual owner; contact through the listing)"
            elif r["phone_kind"] == "broker":
                ph = "Phone: none on the listing (broker-listed; contact through the listing)"
            else:
                ph = "Phone: not found on any saved page"
            hrs = f" Hours: {r['office_hours']}." if r["office_hours"] else ""
            site = f" Site: [{short(r['leasing_url'])}]({r['leasing_url']})." if r["leasing_url"] else ""
            L.append(f"- [ ] **{r['building']}**, {r['hood']}: {r['units']} unit(s) from ${r['min_rent']}. "
                     f"Ask: {r['question']} [{short(r['example_url'])}]({r['example_url']})")
            L.append(f"  - {ph}.{hrs}{site}")
            L.append("  - Answer: ____________________")
        L.append("")
    if dropped:
        L.append(f"Left out ({len(dropped)}, likely to fail the all-in cap): " + ", ".join(dropped) + ".")
        L.append("")
    OUT_MD.write_text("\n".join(L))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    a = ap.parse_args(argv)
    buildings = load_buildings()
    same_building_rows(buildings)
    idx, prior_refused = bc.build_index()
    spages, sites = site_pages()
    slugs = build_slug_index(idx)
    led = Ledger(prior_refused)
    state = bc.load_json(STATE_F, {"urls": {}, "building": {}})
    rows, fetched = [], 0
    for b in buildings:
        cands, own, urls = candidates_for(b, idx, spages, sites, slugs)
        bid = f"{b['q']['year']}|{b['q']['hood']}|{b['q']['building']}|{b['bkey']}"
        if not any(c["phone"] for c in cands) and not any(c["kind"] in ("individual owner", "broker") for c in cands):
            u = state["building"].get(bid) or (fetch_target(urls, idx, state) if a.fetch else "")
            if u and (a.fetch or u in state["urls"]):
                state["building"][bid] = u            # the one request this building gets, ever
                bc.save_json(STATE_F, state)
                fetched += u not in state["urls"]
                path, when = fetch_one(u, led, state)
                if path:
                    for c in parse(path, u):
                        c["when"] = when
                        cands.append(c)
                    own += [bc.clean_url(c["site"]) for c in cands if c.get("site") and bc.clean_url(c["site"]) not in own]
        rows.append((b, build_row(b, cands, own)))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(r for _, r in rows)
    write_md([r for b, r in rows if not b["q"]["all_in_warning"]],
             [f"{b['q']['building']} ({b['q']['hood']})" for b, _ in rows if b["q"]["all_in_warning"]])
    print(f"{len(rows)} buildings; requests made this run: {fetched}")
    t = defaultdict(Counter)
    for _, r in rows:
        t[r["year"]][r["phone_kind"]] += 1
    for y in EXPERIENCE_ORDER:
        print(f"  {experience(y)}: {dict(t[y])}")
    print("  hours:", sum(1 for _, r in rows if r["office_hours"]), " own-site URL:", sum(1 for _, r in rows if r["leasing_url"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
