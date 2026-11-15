"""GTFS feed download and calendar-validity check for the travel_transit domain.

Feeds go to raw/big/gtfs_transit/ (git-ignored) through lib.cached_get, so they are
re-downloaded when missing. A small committed manifest (raw/transit/feeds_manifest.json)
records url, retrieval time, sha1, size and service-date range of every feed used.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import ROOT, cached_get  # noqa: E402

MANIFEST = ROOT / "raw" / "transit" / "feeds_manifest.json"

# key -> (system label, list of candidate URLs in priority order, required)
FEEDS = {
    "lirr": ("LIRR", ["https://rrgtfsfeeds.s3.amazonaws.com/gtfslirr.zip"]),
    "mnr": ("MNR", ["https://rrgtfsfeeds.s3.amazonaws.com/gtfsmnr.zip"]),
    "subway": ("NYCT subway/SIR", ["https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"]),
    # Official NJ Transit link; www.njtransit.com/rail_data.zip redirects to this public file.
    "njt_rail": ("NJT rail/light rail", ["https://www.njtransit.com/rail_data.zip",
                  "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/us-new-jersey-new-jersey-transit-nj-transit-gtfs-509.zip?alt=media"]),
    "njt_bus": ("NJT bus", ["https://www.njtransit.com/bus_data.zip",
                 "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/us-new-jersey-new-jersey-transit-nj-transit-gtfs-508.zip?alt=media"]),
    "path": ("PATH", ["https://data.trilliumtransit.com/gtfs/path-nj-us/path-nj-us.zip",
              "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/us-new-jersey-port-authority-trans-hudson-path-gtfs-517.zip?alt=media"]),
    "septa_rail": ("SEPTA Regional Rail", ["https://www3.septa.org/developer/google_rail.zip",
                    "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/us-pennsylvania-southeastern-pennsylvania-transportation-authority-gtfs-503.zip?alt=media"]),
    "si_ferry": ("Staten Island Ferry", ["https://www.nyc.gov/html/dot/downloads/misc/siferry-gtfs.zip",
                  "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/us-new-york-staten-island-ferry-gtfs-518.zip?alt=media"]),
    "nyc_ferry": ("NYC Ferry", ["https://nycferry.connexionz.net/rtt/public/resource/gtfs.zip"]),
    "ny_waterway": ("NY Waterway", ["https://nywaterway.connexionz.net/rtt/public/resource/gtfs.zip"]),
    "bus_q": ("NYCT Queens bus", ["https://rrgtfsfeeds.s3.amazonaws.com/gtfs_q.zip"]),
    "bus_busco": ("MTA Bus Co", ["https://rrgtfsfeeds.s3.amazonaws.com/gtfs_busco.zip"]),
    "hudson_link": ("Hudson Link", ["https://data.trilliumtransit.com/gtfs/hudsonlink-ny-us/hudsonlink-ny-us.zip"]),
    "beeline": ("Bee-Line", ["https://planning.westchestergov.com/images/stories/zip/GTFS.zip"]),
    "suffolk_bus": ("Suffolk County Transit", ["https://tracksctbus.org/gtfs"]),
    "leprechaun": ("Leprechaun Lines", ["https://s3.amazonaws.com/datatools-511ny/public/Leprechaun_Connection.zip"]),
}


def service_range(zbytes: bytes) -> tuple[str | None, str | None]:
    z = zipfile.ZipFile(io.BytesIO(zbytes))
    names = set(z.namelist())
    lo, hi = [], []
    if "calendar.txt" in names:
        for r in csv.DictReader(io.TextIOWrapper(z.open("calendar.txt"), "utf-8-sig")):
            lo.append(r["start_date"].strip()); hi.append(r["end_date"].strip())
    if "calendar_dates.txt" in names:
        for r in csv.DictReader(io.TextIOWrapper(z.open("calendar_dates.txt"), "utf-8-sig")):
            if r["exception_type"].strip() == "1":
                lo.append(r["date"].strip()); hi.append(r["date"].strip())
    return (min(lo) if lo else None, max(hi) if hi else None)


def fetch_all(refresh: bool = False) -> dict:
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for key, (label, urls) in FEEDS.items():
        if key in man and not refresh and (ROOT / man[key]["raw_path"]).exists():
            continue
        tried = []
        for u in urls:
            try:
                content, meta = cached_get(u, "big/gtfs_transit", ext="zip", timeout=300, refresh=refresh)
            except RuntimeError as e:
                tried.append({"url": u, "error": str(e)[:200]}); continue
            if meta["status"] != 200 or content[:2] != b"PK":
                tried.append({"url": u, "status": meta["status"], "error": "not a zip"}); continue
            lo, hi = service_range(content)
            man[key] = {"system": label, "url": u, "retrieved_at": meta["retrieved_at"],
                        "raw_path": meta["path"], "sha1": hashlib.sha1(content).hexdigest(),
                        "bytes": len(content), "service_start": lo, "service_end": hi,
                        "tried_before": tried}
            break
        else:
            man[key] = {"system": label, "url": None, "error": "all candidates failed", "tried": tried}
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(man, indent=1))
    return man


if __name__ == "__main__":
    m = fetch_all(refresh="--refresh" in sys.argv)
    for k, v in m.items():
        print(k, v.get("service_start"), v.get("service_end"), v.get("bytes"), v.get("url"))
