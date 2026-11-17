#!/usr/bin/env python3
"""Tests for scripts/h_inbox.py (the inbox drop box). No network: links are "fetched" by a fake that records calls.

Fixtures in scripts/fixtures/inbox/ are made up (fictional addresses, ZIPs 00001-00006):
  jsonld_streeteasy.html  JSON-LD Apartment + Offer, canonical link, visible text (floor, dogs, fees)
  next_trulia.html        __NEXT_DATA__ building page with a unit table, a 2-bed, an over-limit unit and similarHomes
  next_zillow.html        __NEXT_DATA__ whose state is a JSON string (gdpClientCache), with nearbyHomes
  plain_craigslist.html   no JSON: visible text only
  printed_zumper.pdf      a printed page (text PDF)
  screenshot.png          a screenshot (needs reading unless tesseract is installed)
  links.txt               Trulia / Zillow / StreetEasy / Apartments.com / a refused host / Craigslist / an open host
Run: python3 scripts/test_inbox.py
"""
import csv
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import h_inbox as H  # noqa: E402

FIX = HERE / "fixtures" / "inbox"
N, FAILS = [0], []


def eq(got, want, what):
    N[0] += 1
    if str(got) != str(want):
        FAILS.append(f"{what}: got {got!r}, want {want!r}")


def ok(cond, what):
    N[0] += 1
    if not cond:
        FAILS.append(what)


CALLS = []


def fake_fetch(url, ext):
    CALLS.append(url)
    meta = {"status": 200, "retrieved_at": "2026-11-17T12:00:00+00:00", "path": "raw/inbox_links/fake.html"}
    if url.endswith("/robots.txt"):
        if "fake-building.example" in url:
            return b"User-agent: *\nDisallow: /private/\n", meta
        return b"", dict(meta, status=404)
    if "craigslist" in url:
        return (FIX / "plain_craigslist.html").read_bytes(), meta
    return b"<html><title>t</title><body>7 Nothing Pl, Fakeville, NY 00006. Rent: $1,500. Studio.</body></html>", meta


def by_file(rows, name):
    return [r for r in rows if r["raw_path"].endswith(name)]


def main():
    tmp = Path(tempfile.mkdtemp(prefix="test_inbox_"))
    try:
        inbox = tmp / "inbox"
        shutil.copytree(FIX, inbox)
        (inbox / "README.md").write_text("ignored")
        (inbox / "page_files").mkdir()                       # "Webpage, complete" side folder: skipped
        (inbox / "page_files" / "x.html").write_text("<html>$999/mo 1 Nope St, X, NJ 00000</html>")
        out, status_p = tmp / "manual_inbox.csv", tmp / "STATUS.txt"
        H.run(inbox, out, fake_fetch, status_p, date(2026, 11, 17))
        rows = list(csv.DictReader(open(out, newline="")))
        status = status_p.read_text()
        eq(list(rows[0].keys()), H.COLS, "contract columns")

        # JSON-LD
        se = by_file(rows, "jsonld_streeteasy.html")
        eq(len(se), 1, "JSON-LD: one row")
        r = se[0]
        for k, v in dict(source_site="streeteasy.com", url="https://streeteasy.com/building/fake-example/2b",
                         address="123 Example Street", unit="2B", city="Faketown", state="NY", zip="00001", beds=1,
                         sqft=615, listed_rent=1950, available_date="2026-12-01", dogs="yes", dog_weight_limit_lb=60,
                         elevator="yes", floor=2, lat=40.1, laundry="in_building",
                         building_name="The Example Arms (fictional)").items():
            eq(r[k], v, f"JSON-LD {k}")
        ok(r["notes"].startswith("provided by the owner (saved page jsonld_streeteasy.html)"), "JSON-LD notes head")
        ok("address from JSON-LD" in r["notes"], "JSON-LD: address source named")
        ok('"required_monthly_total": 25' in r["other_monthly_fees_json"], "JSON-LD: amenity fee $25 read")
        ok("No fee" not in r["other_monthly_fees_json"], "broker 'No fee' is not a building fee")
        eq(r["first_seen"], H.iso_utc((inbox / "jsonld_streeteasy.html").stat().st_mtime), "retrieved_at = file save time")

        # __NEXT_DATA__ building page with a unit table
        tr = sorted(by_file(rows, "next_trulia.html"), key=lambda x: x["unit"])
        eq([x["unit"] for x in tr], ["3A", "4C"], "NEXT_DATA: units kept (2-bed, over $2,200 and similarHomes left out)")
        eq(tr[0]["beds"], 0, "NEXT_DATA studio")
        eq(tr[0]["listed_rent"], 1700, "NEXT_DATA rent 3A")
        eq(tr[0]["sqft"], 480, "NEXT_DATA sqft 3A")
        eq(tr[0]["available_date"], "2026-12-01", "NEXT_DATA date 3A")
        eq(tr[1]["available_date"], "now", "NEXT_DATA isAvailableNow")
        eq(tr[1]["source_site"], "trulia", "NEXT_DATA site from og:url")
        eq(tr[1]["dogs"], "yes", "NEXT_DATA petPolicy dogs")
        eq(tr[1]["dog_weight_limit_lb"], 50, "NEXT_DATA dog weight")
        eq(tr[1]["pet_rent"], 40, "NEXT_DATA pet rent")
        eq(tr[1]["parking_fee"], 150, "NEXT_DATA parking fee")
        eq(tr[1]["elevator"], "yes", "NEXT_DATA elevator from amenity list")
        ok(not any("Elsewhere" in x["address"] for x in rows), "similarHomes not read as a listing")
        ok("above the $2,200 collection limit" in status and "outside the search" in status, "left-out units named in STATUS")

        # JSON held in a string (Zillow gdpClientCache)
        z = by_file(rows, "next_zillow.html")
        eq(len(z), 1, "Zillow: one row (nearbyHomes skipped)")
        for k, v in dict(source_site="zillow.com", address="789 Placeholder Rd", unit="2", zip="00003", listed_rent=1875,
                         beds=1, sqft=640, available_date="2026-12-05", dogs="yes", elevator="yes").items():
            eq(z[0][k], v, f"Zillow {k}")

        # visible text only
        c = by_file(rows, "plain_craigslist.html")
        eq(len(c), 1, "plain text: one row")
        for k, v in dict(source_site="craigslist", address="12 Imaginary Lane", city="Nowhere", state="CT", listed_rent=1650,
                         beds=1, sqft=600, available_date="2026-11-25", dogs="yes", elevator="no", floor=2).items():
            eq(c[0][k], v, f"plain text {k}")

        # PDF
        p = by_file(rows, "printed_zumper.pdf")
        eq(len(p), 1, "PDF: one row")
        for k, v in dict(source_site="zumper", address="999 Fictional Boulevard", unit="5F", beds=0, listed_rent=2050,
                         sqft=410, available_date="2026-12-10", dogs="no", elevator="yes", building_floors=12).items():
            eq(p[0][k], v, f"PDF {k}")
        ok(p[0]["notes"].startswith("provided by the owner (PDF printed_zumper.pdf)"), "PDF notes head")

        # screenshot
        if shutil.which("tesseract") is None:
            ok("screenshot.png: needs reading" in status, "screenshot without OCR: needs reading")
            eq(len(by_file(rows, "screenshot.png")), 0, "screenshot without OCR: no row")

        # links: forbidden hosts are never requested
        for host in ("trulia.com", "zillow.com", "streeteasy.com", "apartments.com", "stamfordcommons.com"):
            ok(not any(host in u for u in CALLS), f"forbidden link host requested: {host}")
        ok(status.count("save the page instead") >= 5, "forbidden links told to save the page instead")
        ok("Trulia pages are never opened" in status, "Trulia link answer")
        ok(any("craigslist.org/apa/" in u for u in CALLS), "a pasted Craigslist link may be opened")
        lk = [x for x in rows if x["source_site"] == "fake-building.example"]
        eq(len(lk), 1, "open-host link parsed")
        ok(lk[0]["notes"].startswith("provided by the owner (link in inbox/links.txt"), "link notes head")
        eq(lk[0]["first_seen"], "2026-11-17T12:00:00+00:00", "link retrieved_at = fetch time")
        ok(not any("Nope St" in x["address"] for x in rows), "the _files folder is not read")
        eq(H.link_verdict("https://www.hotpads.com/x"), "hotpads.com is off limits to our tools (CLAUDE.md): save the page instead",
           "HotPads off limits")

        # idempotent: a second run gives the same file; a row whose file left the inbox is kept
        before = out.read_text()
        H.run(inbox, out, fake_fetch, status_p, date(2026, 11, 17))
        eq(out.read_text() == before, True, "second run identical")
        (inbox / "next_zillow.html").unlink()
        H.run(inbox, out, fake_fetch, status_p, date(2026, 11, 17))
        eq(out.read_text() == before, True, "row kept when its raw file is gone")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # small readers
    eq(H.to_date("Dec 1", date(2026, 11, 17)), "2026-12-01", "to_date month day")
    eq(H.to_date("Jan 5", date(2026, 11, 17)), "2027-01-05", "to_date rolls the year")
    eq(H.to_date("12/10/26"), "2026-12-10", "to_date m/d/yy")
    eq(H.to_money("$1,800 - $2,000/mo"), 1800, "to_money range low end")
    eq(H.to_money(99), None, "to_money not a rent")
    eq(H.to_beds({"formattedValue": "Studio"}), 0, "to_beds studio")


if __name__ == "__main__":
    main()
    print(f"test_inbox: {N[0]} checks, {len(FAILS)} failed")
    for f in FAILS:
        print("  FAIL", f)
    sys.exit(1 if FAILS else 0)
