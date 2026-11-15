"""recheck_shortlist: look at each short-listed listing page once more and say whether it is still there.

    python3 scripts/recheck_shortlist.py --ids out/shortlist.txt [--dry-run] [--allow-trulia] [--refresh]

Writes out/recheck_<YYYY-MM-DD>.csv with one row per listing_id and a `status`:

    still_listed    the unit is on the page at the same price
    price_changed   the unit is on the page at a different price (price_now, price_delta)
    gone            HTTP 404/410, or the page parsed and the unit is no longer in its available list
    blocked         the host refused (403, 429 or a challenge page), or it refused earlier in this run and was not asked again
    skipped         a host this tool never requests (see NEVER_HOSTS), or Trulia without --allow-trulia
    unparsed        the page came back but no parser here can find the unit on it (read it by hand)
    error           network error or a 5xx
    not_in_data     the listing_id is not in data/ranked_units.csv

Hard rules, enforced in code (HostGate):
  * at most MAX_LISTINGS (40) listing_ids per run; a longer list stops the run before any request;
  * never request Zillow, StreetEasy, Apartments.com or Craigslist;
  * never request trulia.com unless --allow-trulia is passed;
  * one refusal (403, 429, CAPTCHA or challenge page) from a host ends every request to that host for the run;
  * one request per distinct URL (units of one building share a page), through lib.cached_get with retries=1 and
    at least MIN_DELAY seconds between requests to a host.

Pages are cached under raw/recheck/<date>/, so a second run on the same day reads the cache; --refresh refetches.
Parsers are the harvesters' own: h_apartmentlist.parse_listing and h_zumper.parse_state (imported read-only), and
Trulia's __NEXT_DATA__ block. Any other site is fetched and reported as `unparsed`, with a note on whether the
old price still appears in the page text.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import call_sheet as cs  # noqa: E402

MAX_LISTINGS = 40
MIN_DELAY = 2.5
NEVER_HOSTS = ("zillow.com", "streeteasy.com", "apartments.com", "craigslist.org")
TRULIA = "trulia.com"
REFUSAL_STATUS = (403, 429)
CHALLENGE_RE = re.compile(r"px-captcha|cf-challenge|captcha-delivery|Just a moment\.\.\.|are you a robot|"
                          r"Access to this page has been denied|unusual traffic|Pardon Our Interruption", re.I)
NEXT_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
# Apartment List robots.txt disallowed paths, as read by h_apartmentlist.py on 2026-11-15.
AL_DISALLOW = ("/users/login", "/experiments", "/light_cycle", "/shortlist", "/signup", "/base-price-lock",
               "/all-in-price-lock", "/app/open")

COLS = ["listing_id", "building_name", "address", "unit", "url", "host", "listed_rent", "status", "price_now",
        "price_delta", "available_now_text", "http_status", "checked_at", "detail", "raw_path"]


class TooManyListings(SystemExit):
    pass


def enforce_cap(ids: list[str], cap: int = MAX_LISTINGS) -> list[str]:
    """De-duplicate; stop the run when the list is longer than the cap."""
    ids = list(dict.fromkeys(ids))
    if len(ids) > cap:
        raise TooManyListings(f"{len(ids)} listings given; this tool re-checks at most {cap} per run. "
                              "Shorten the list. Nothing was requested.")
    return ids


def host_of(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0]


def _is(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


class HostGate:
    """Decides whether a URL may be requested. One refusal stops a host for the rest of the run."""

    def __init__(self, allow_trulia: bool = False):
        self.allow_trulia = allow_trulia
        self.stopped: dict[str, str] = {}

    def check(self, url: str) -> tuple[bool, str, str]:
        """(may_request, status_if_not, reason)."""
        host = host_of(url)
        if not host or urlparse(url).scheme not in ("http", "https"):
            return False, "error", "no usable URL in the data"
        for d in NEVER_HOSTS:
            if _is(host, d):
                return False, "skipped", f"{d} is never requested by this tool"
        if _is(host, TRULIA) and not self.allow_trulia:
            return False, "skipped", "trulia.com is not requested unless --allow-trulia is passed (it has been blocking us)"
        if _is(host, "apartmentlist.com") and any(urlparse(url).path.startswith(p) for p in AL_DISALLOW):
            return False, "skipped", "path is disallowed by apartmentlist.com robots.txt"
        if host in self.stopped:
            return False, "blocked", f"not requested: {host} refused earlier in this run ({self.stopped[host]})"
        return True, "", ""

    def refuse(self, url: str, why: str) -> None:
        self.stopped.setdefault(host_of(url), why)


def is_challenge(html: str) -> bool:
    head = html[:20000]
    return bool(CHALLENGE_RE.search(head)) or (len(html) < 30000 and "captcha" in head.lower())


# ------------------------------------------------------------------------------------------------- fetch
def lib_fetcher(date: str, refresh: bool = False):
    """A fetcher(url) -> (status, html, path) built on lib.cached_get. Imported lazily so tests need no network code."""
    import lib

    def fetch(url: str):
        host = host_of(url)
        lib.HOST_DELAY[host] = max(lib.HOST_DELAY.get(host, lib.DEFAULT_DELAY), MIN_DELAY)
        try:
            content, meta = lib.cached_get(url, f"recheck/{date}", ext="html", refresh=refresh, retries=1, timeout=45)
        except RuntimeError as e:   # lib raises after a 429 / 5xx / network error (retries=1: a single request)
            m = re.search(r"HTTP (\d{3})", str(e))
            return (int(m.group(1)) if m else 0), "", ""
        status = int(meta.get("status", 0))
        return status, content.decode("utf8", "replace"), meta.get("path", "") if status == 200 else ""
    return fetch


# ------------------------------------------------------------------------------------------------- parsers
# Each parser returns {"found": True | False | None, "price": number | None, "available": text, "detail": text}.
# found=None means "this page cannot tell us"; found=False means the page lists units and this one is not there.
def _result(found, price=None, available="", detail=""):
    return {"found": found, "price": price, "available": available, "detail": detail}


def parse_apartmentlist(html: str, row: dict) -> dict:
    import h_apartmentlist as A
    L = A.parse_listing(html)
    if L is None:
        return _result(None, detail="no listing block on the page")
    lid = cs.val(row, "listing_id").split(":", 1)[-1]
    n_units = 0
    for fp in L.get("available_units") or []:
        if f"{L.get('rental_id')}-fp{fp.get('id')}" == lid:
            return _result(True, fp.get("price"), "", f"floor plan {fp.get('name')}; floor-plan price")
        for u in fp.get("units") or []:
            n_units += 1
            if lid in (str(u.get("unit_rental_id") or ""), f"{L.get('rental_id')}-u{u.get('id')}"):
                if str(u.get("availability") or "").lower() not in ("", "available"):
                    return _result(False, detail=f"unit is on the page as '{u.get('availability')}'")
                base, price = u.get("base_price"), u.get("price")
                rent = base if isinstance(base, (int, float)) and base > 0 else price
                when = "now" if u.get("available_now") else str(u.get("available_on") or "")
                return _result(True, rent, when, f"unit {u.get('display_name') or u.get('name')}")
    return _result(False, detail=f"unit not among the {n_units} units the page lists as available")


def parse_zumper(html: str, row: dict) -> dict:
    import h_zumper as Z
    st = Z.parse_state(html)
    e = (((st or {}).get("detail") or {}).get("entity") or {}).get("data") or {}
    if not e:
        return _result(None, detail="no page state")
    want = cs.val(row, "listing_id").replace("zumper-", "")
    if str(e.get("listing_id")) != want:
        return _result(None, detail=f"page is for Zumper listing {e.get('listing_id')}, not {want} (a building page?)")
    price = e.get("price") or e.get("min_price")
    status = e.get("listing_status")
    if status not in (1, None):
        return _result(False, price, "", f"Zumper listing_status={status} (1 means active)")
    return _result(True, price, str(e.get("date_available") or ""), f"listing_status={status}")


def parse_trulia(html: str, row: dict) -> dict:
    m = NEXT_RE.search(html)
    if not m:
        return _result(None, detail="no __NEXT_DATA__ block")
    try:
        hd = (json.loads(m.group(1)).get("props") or {}).get("homeDetails") or {}
    except json.JSONDecodeError:
        return _result(None, detail="__NEXT_DATA__ is not JSON")
    if not hd:
        return _result(None, detail="no homeDetails on the page")
    lid = cs.val(row, "listing_id")
    tail = lid.rsplit(":", 1)[-1]
    unit = cs.val(row, "unit").lower()
    groups = (hd.get("floorPlans") or {}).get("floorPlanGroups") or []
    n_units = 0
    for g in groups:
        for p in g.get("plans") or []:
            for u in p.get("units") or []:
                n_units += 1
                name = str(u.get("name") or "").lower()
                if str(u.get("id")) == tail or (unit and name in (unit, "unit " + unit)):
                    pr = (u.get("priceRange") or {}).get("min")
                    return _result(True, pr, str(u.get("availabilityText") or ""), f"{u.get('name')}")
            if ":plan-" in lid and str(p.get("id")) == tail:
                pr = (p.get("priceRange") or {}).get("min")
                return _result(True, pr, str(p.get("availabilityText") or ""), f"floor plan {p.get('name')}")
    if groups:
        return _result(False, detail=f"unit not among the {n_units} units the page lists")
    price = (hd.get("price") or {})
    status = hd.get("currentStatus") or {}
    if isinstance(status, dict) and (status.get("isOffMarket") or status.get("isRecentlyRented")):
        return _result(False, detail=f"page status: {status.get('label') or 'off market'}")
    amount = (price.get("price") or price.get("min")) if isinstance(price, dict) else None
    if amount:
        return _result(True, amount, "", "single-home page price")
    return _result(None, detail="no price found on the page")


def parse_generic(html: str, row: dict) -> dict:
    rent = cs.num(cs.val(row, "listed_rent"))
    seen = rent is not None and re.search(rf"\$\s?{int(rent):,}\b|\$\s?{int(rent)}\b", html) is not None
    return _result(None, detail="no parser for this site; the old price "
                                + ("still appears in the page text" if seen else "does not appear in the page text")
                                + " (many of these sites load units with scripts)")


def parser_for(url: str):
    h = host_of(url)
    if _is(h, "apartmentlist.com"):
        return parse_apartmentlist
    if _is(h, "zumper.com"):
        return parse_zumper
    if _is(h, TRULIA):
        return parse_trulia
    return parse_generic


def classify(old_rent, parsed: dict) -> tuple[str, str, str]:
    """(status, price_now, price_delta) from the old rent and a parser result."""
    if parsed["found"] is None:
        return "unparsed", "", ""
    if parsed["found"] is False:
        return "gone", "", ""
    new, old = cs.num(parsed.get("price")), cs.num(old_rent)
    if new is None or old is None:
        return "still_listed", "" if new is None else f"{new:g}", ""
    if abs(new - old) < 0.5:
        return "still_listed", f"{new:g}", "0"
    return "price_changed", f"{new:g}", f"{new - old:+g}"


# ------------------------------------------------------------------------------------------------- run
def recheck(rows: list[dict], gate: HostGate, fetch, now=None) -> list[dict]:
    """rows: dicts with listing_id, url, unit, listed_rent (and optionally building_name, address)."""
    now = now or (lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    pages: dict[str, tuple] = {}   # url -> (status, html, path, checked_at) so each URL is requested once
    out = []
    for r in rows:
        url = cs.val(r, "url")
        base = {"listing_id": cs.val(r, "listing_id"), "building_name": cs.val(r, "building_name"),
                "address": cs.val(r, "address"), "unit": cs.val(r, "unit"), "url": url, "host": host_of(url),
                "listed_rent": cs.val(r, "listed_rent"), "price_now": "", "price_delta": "", "available_now_text": "",
                "http_status": "", "checked_at": "", "detail": "", "raw_path": ""}
        if r.get("_missing"):
            out.append({**base, "status": "not_in_data", "detail": "listing_id not found in ranked_units.csv"})
            continue
        if url not in pages:
            ok, status, reason = gate.check(url)
            if not ok:
                out.append({**base, "status": status, "detail": reason})
                continue
            code, html, path = fetch(url)
            pages[url] = (code, html, path, now())
            if code in REFUSAL_STATUS:
                gate.refuse(url, f"HTTP {code}")
            elif code == 200 and is_challenge(html):
                gate.refuse(url, "challenge page")
                pages[url] = (-1, html, path, pages[url][3])
        code, html, path, at = pages[url]
        base.update(http_status=code if code > 0 else "", checked_at=at, raw_path=path)
        if code in REFUSAL_STATUS:
            out.append({**base, "status": "blocked", "detail": f"HTTP {code}"})
        elif code == -1:
            out.append({**base, "status": "blocked", "http_status": 200, "detail": "CAPTCHA or challenge page"})
        elif code in (404, 410):
            out.append({**base, "status": "gone", "detail": f"HTTP {code}"})
        elif code != 200:
            out.append({**base, "status": "error", "detail": f"HTTP {code}" if code else "network error"})
        else:
            try:
                parsed = parser_for(url)(html, r)
            except Exception as e:  # a parser must never end the run
                parsed = _result(None, detail=f"parser failed: {type(e).__name__}: {e}")
            status, price_now, delta = classify(cs.val(r, "listed_rent"), parsed)
            out.append({**base, "status": status, "price_now": price_now, "price_delta": delta,
                        "available_now_text": parsed.get("available", ""), "detail": parsed.get("detail", "")})
    return out


def rows_for_ids(df: pd.DataFrame, ids: list[str]) -> list[dict]:
    by_id = {r["listing_id"]: r.to_dict() for _, r in df.iterrows()}
    return [by_id.get(i) or {"listing_id": i, "_missing": True} for i in ids]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ids", required=True, help="file (one listing_id per line, or a CSV with a listing_id column) or a comma list")
    ap.add_argument("--allow-trulia", action="store_true", help="permit requests to trulia.com (off by default)")
    ap.add_argument("--refresh", action="store_true", help="refetch even if today's cache has the page")
    ap.add_argument("--dry-run", action="store_true", help="show what would be requested; no network")
    ap.add_argument("--ranked", default=str(cs.RANKED))
    ap.add_argument("--out-dir", default=str(cs.OUT))
    a = ap.parse_args(argv)

    ids = enforce_cap(cs.read_ids(a.ids))
    rows = rows_for_ids(cs.load_ranked(Path(a.ranked)), ids)
    gate = HostGate(allow_trulia=a.allow_trulia)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if a.dry_run:
        seen = set()
        for r in rows:
            url = cs.val(r, "url")
            ok, status, reason = (False, "not_in_data", "") if r.get("_missing") else gate.check(url)
            what = "REQUEST" if ok and url not in seen else ("same page as above" if ok else f"{status}: {reason}")
            seen.add(url)
            print(f"{r['listing_id']}\t{host_of(url)}\t{what}")
        return 0

    result = recheck(rows, gate, lib_fetcher(date, a.refresh))
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"recheck_{date}.csv"
    pd.DataFrame(result, columns=COLS).to_csv(path, index=False)
    counts = pd.Series([r["status"] for r in result]).value_counts().to_dict()
    print(f"{len(result)} listings -> {path}: {counts}")
    for h, why in gate.stopped.items():
        print(f"STOPPED {h} after one refusal ({why}); no further requests were sent to it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
