"""Record the outcome of the building search for unmatched Trulia cards (trawl 2, step 2).

  python3 scripts/trulia_match_rows.py al <street_key> <apartmentlist path, e.g. /nj/jersey-city/401-central-ave--1>
      Reads the Apartment List property page (h_apartmentlist.fetch: robots-allowed, cached, no retry on a refusal,
      3 s per host), checks that the page's street address normalizes to the same street key as the cards, and writes
      its available studio/1BR units at or under $2,200 to data/listings_raw/trulia_matches.csv.
  python3 scripts/trulia_match_rows.py site <street_key> <json file>
      Rows read by hand from a building's own or manager's page (already fetched with trulia_match_fetch.py). JSON: a
      list of row dicts in the 41-column contract; listing_id, url, listed_rent, first_seen required.
  python3 scripts/trulia_match_rows.py none <street_key> <method> <note> [url]
      Searched; nothing usable (method no_site_found / site_no_units / site_offlimits / refused ...).

Every outcome updates the rows of data/reference/trulia_card_matches.csv for all cards at that street key.
Idempotent: rows are keyed by listing_id; a match row is overwritten by the newer outcome.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
import build_master as bm  # noqa: E402

OUT = lib.DATA / "listings_raw" / "trulia_matches.csv"
MATCH = lib.DATA / "reference" / "trulia_card_matches.csv"
UNM = lib.DATA / "reference" / "trulia_card_unmatched_priority.csv"
COLS = ("listing_id,source_site,url,detail_level,first_seen,last_seen,building_name,address,city,state,zip,lat,lon,"
        "unit,beds,baths,sqft,listed_rent,price_basis,concession_text,available_date_text,available_date,dogs,"
        "dog_policy_text,dog_weight_limit_lb,elevator,floor,building_floors,parking_type,parking_fee,pet_rent,"
        "other_monthly_fees_json,utilities_included,laundry,listing_type,manager,listing_age_days,photo_url,"
        "building_url,raw_path,notes").split(",")
CAP = 2200


def cards_at(sk):
    with open(UNM) as f:
        for r in csv.DictReader(f):
            if r["street_key"] == sk:
                return r["ids"].split(";"), r
    raise SystemExit(f"street key not in the unmatched list: {sk}")


def save_rows(new):
    rows = {}
    if OUT.exists():
        with open(OUT) as f:
            rows = {r["listing_id"]: r for r in csv.DictReader(f)}
    for r in new:
        old = rows.get(r["listing_id"])
        if old and old.get("first_seen"):
            r["first_seen"] = min(old["first_seen"], r["first_seen"])
        rows[r["listing_id"]] = {c: r.get(c, "") for c in COLS}
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        for k in sorted(rows):
            w.writerow(rows[k])


def set_match(ids, matched, url, method, note):
    with open(MATCH) as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        rows = list(rd)
    for r in rows:
        if r["trulia_listing_id"] in ids:
            r.update(matched_listing_ids=";".join(matched), building_site_url=url, method=method, notes=note)
    with open(MATCH, "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)


def tag(rows, ids):
    via = ", ".join(ids[:5]) + (f" (+{len(ids) - 5} more)" if len(ids) > 5 else "")
    for r in rows:
        r["notes"] = f"found via Trulia card {via}; " + r.get("notes", "")
    return rows


def cmd_al(sk, path):
    import h_apartmentlist as al
    lib.HOST_DELAY[al.HOST] = 3.0
    ids, info = cards_at(sk)
    from trulia_match_fetch import wait_host
    wait_host(al.HOST)
    try:
        html, meta = al.fetch(path)
    except al.Blocked as e:
        al.record_refusal(str(e), e.url)
        set_match(ids, [], al.BASE + path, "refused", f"Apartment List refused: {e}")
        print("REFUSED", e)
        return
    L = al.parse_listing(html)
    if not L:
        if "404" in html and "rental_id" not in html:
            set_match(ids, [], al.BASE + path, "site_no_units", f"Apartment List page is a soft 404 (read {meta['retrieved_at']})")
            print("soft 404")
            return
        set_match(ids, [], al.BASE + path, "site_no_units", "Apartment List page had no listing data")
        print("no listing data")
        return
    page_sk = bm.street_key(L.get("street_address") or L.get("street") or "", str(L.get("zip") or "")[:5])
    if page_sk != sk and bm.house_no(page_sk) != bm.house_no(sk):
        set_match(ids, [], al.BASE + path, "address_mismatch", f"page address {page_sk} is not {sk}")
        print("ADDRESS MISMATCH", page_sk, sk)
        return
    rows, reason = al.build_rows(L, path, meta, *grid_args(al), ceiling=CAP)
    if rows:
        save_rows(tag(rows, ids))
        set_match(ids, [r["listing_id"] for r in rows], al.BASE + path, "apartmentlist_building_page",
                  f"Apartment List page read {meta['retrieved_at']}; {len(rows)} studio/1BR units <= ${CAP}; page address {page_sk}")
    else:
        set_match(ids, [], al.BASE + path, "site_no_units",
                  f"Apartment List page read {meta['retrieved_at']}: no available studio/1BR <= ${CAP} ({reason}); page address {page_sk}")
    print(sk, "->", len(rows), reason, page_sk)


_grid = None


def grid_args(al):
    global _grid
    if _grid is None:
        g = al.load_grid()
        _grid = ({z[0]: z[3] for z in g}, g)
    return _grid


def cmd_site(sk, jf):
    ids, info = cards_at(sk)
    rows = json.loads(Path(jf).read_text())
    for r in rows:
        for c in ("listing_id", "url", "listed_rent", "first_seen", "source_site"):
            assert r.get(c) not in (None, ""), (c, r)
        r.setdefault("last_seen", r["first_seen"])
        r.setdefault("detail_level", "building_unit")
        assert float(r["listed_rent"]) <= CAP, r
    rows = tag(rows, ids)
    save_rows(rows)
    url = rows[0].get("building_url") or rows[0]["url"]
    set_match(ids, [r["listing_id"] for r in rows], url, "building_site",
              f"read on {rows[0]['source_site']} {rows[0]['first_seen']}; {len(rows)} units <= ${CAP}")
    print(sk, "->", len(rows))


def cmd_none(sk, method, note, url=""):
    ids, info = cards_at(sk)
    set_match(ids, [], url, method, note)
    print(sk, method)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"al": lambda: cmd_al(a[1], a[2]), "site": lambda: cmd_site(a[1], a[2]),
     "none": lambda: cmd_none(a[1], a[2], a[3], a[4] if len(a) > 4 else "")}[a[0]]()
