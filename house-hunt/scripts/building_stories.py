"""Building storeys from records, and apartment floors read from unit labels (second trawl, step 3).

Why: since 2026-11-17 a walk-up is allowed when the apartment is on floor 2; floor 3 and above need an elevator
(CLAUDE.md, "Second trawl"). So every candidate building needs its number of storeys from a reliable record, and every
apartment its floor.

Writes (headers are a contract with scripts/build_master.py; do not change them):
  data/reference/building_stories.csv
      addr_key, address, city, state, zip, lat, lon, stories, stories_basis (official_record|osm|listing),
      source_name, source_url, retrieved_at, notes
      One row per candidate building: every distinct addr_key in data/listings.csv with listed_rent <= 2200 and
      gate_status pending or pass. Priority areas first (New Jersey, Brooklyn, Connecticut, Long Island, Long Island
      City), then the rest. A building with no storeys found has stories and stories_basis empty and says in notes
      where we looked (rule 1: missing is not_found plus where you looked).
  data/reference/unit_floor_reads.csv
      listing_id, unit, floor, basis ("read from the apartment number"), convention, notes
      One row per candidate listing whose unit label has a clear floor pattern ('2B', '205', '#2R', '158-2H',
      'B-305'), or whose complex has a reviewed numbering convention (data/reference/unit_numbering_conventions.csv).
      Ambiguous labels ('A', 'PH', '1-12', bare four-digit numbers with no convention) are not read.

Sources, in order of preference for each building:
  1. official_record
     - NYC (all five boroughs): PLUTO `numfloors`, from the copy already held in raw/big/pluto/pluto_res4plus.csv
       (lots with 4+ residential units; downloaded 2026-11-15 by scripts/enrich_nyc_pluto.py). No request is made to
       data.cityofnewyork.us (it refused us on 2026-11-17). Joined by house number + street name within 80 m.
     - New Jersey: the NJ Office of GIS "Parcels and MOD-IV" county file geodatabases (one zip per county, from
       geoapps.nj.gov, linked from https://www.nj.gov/njgin/edata/parcels/). The tax list's BLDG_DESC begins with
       the storey count ('3S-B-D-6U-H' = 3 storeys, brick, detached, 6 units, heated; '4B-8U-H' = 4 storeys brick;
       '16S-C-348U' = 16 storeys). Joined by house number + street name to a tax record whose parcel lies within
       400 m of the building point.
     - Connecticut (CT OPM / CT GIS Office CAMA and parcel layer) and New York State outside NYC (NYS Tax Parcels
       Public, Suffolk County tax parcels) were checked on 2026-11-17: none carries a storey field, so they are not
       used (docs/harvest_notes/building_stories.md).
  2. listing: a building floor count stated on a listing detail page we hold (data/listings.csv building_floors,
     detail pages only; never a search card or snippet).
  3. osm: OpenStreetMap `building:levels` of the outline that contains the building point (or the nearest outline
     within 20 m), from the Geofabrik extract already held (raw/big/osm, read with scripts/tools/places.py).

Usage:
  python3 scripts/building_stories.py download   # NJ county files (skips files already on disk; resumable)
  python3 scripts/building_stories.py build      # both CSVs from what is on disk (no network)
  python3 scripts/building_stories.py            # download, then build

Idempotent: both outputs are rewritten whole from the inputs. Downloads are written to <name>.part and renamed when
complete; a county already on disk is not fetched again. Per-county extracts are cached as
raw/building_stories/nj_modiv/<County>_taxlist.csv.gz. Zips are git-ignored (raw/building_stories/.gitignore) and
re-created by `download`.

One refusal ends a host: a 401, 403 or 429, or a bot-wall page instead of a zip, is written to
raw/_host_kill_shared.json and the download stops.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
from lib import DATA, RAW, ROOT, now_iso  # noqa: E402
import parsers  # noqa: E402

OUT_STORIES = DATA / "reference" / "building_stories.csv"
OUT_FLOORS = DATA / "reference" / "unit_floor_reads.csv"
CONVENTIONS = DATA / "reference" / "unit_numbering_conventions.csv"
CROSSWALK = DATA / "reference" / "building_crosswalk.csv"
NYC_FACTS = DATA / "reference" / "nyc_building_facts.csv"
LISTINGS = DATA / "listings.csv"
RAWDIR = RAW / "building_stories"
NJDIR = RAWDIR / "nj_modiv"
PLUTO_RAW = RAW / "big" / "pluto" / "pluto_res4plus.csv"
PLUTO_INDEX = RAW / "pluto_pages" / "_index.jsonl"
COUNTY_ZIP = RAW / "census_cb" / "a31400440e704704.zip"   # cb_2023_us_county_500k (scripts/build_map_base.py)
KILL = RAW / "_host_kill_shared.json"

STORIES_COLS = ["addr_key", "address", "city", "state", "zip", "lat", "lon", "stories", "stories_basis",
                "source_name", "source_url", "retrieved_at", "notes"]
FLOOR_COLS = ["listing_id", "unit", "floor", "basis", "convention", "notes"]
RENT_MAX = 2200
FLOOR_BASIS = "read from the apartment number"

PLUTO_SRC = "https://data.cityofnewyork.us/Housing-Development/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks"
NJGIN_PAGE = "https://www.nj.gov/njgin/edata/parcels/"
ITEM_URL = "https://www.arcgis.com/sharing/rest/content/items/{}"
# County "Parcels & MOD-IV" file geodatabase items, as linked from NJGIN_PAGE on 2026-11-17
NJ_ITEMS = {
    "Atlantic": "52c8da02ed454135bd04bf77af6f17bb", "Bergen": "920feb01c4544e5397b05e15f844d640",
    "Burlington": "5432e41873f64196b8d5dc01a87c2428", "Camden": "844d60453e3e4664a097c5c57bc8ad29",
    "Cape May": "9eaf2161dd094357b6878736a5116732", "Cumberland": "b336916089424f089424d59b73ccdcf7",
    "Essex": "dee9661eab744433a8f1e4d141308bb4", "Gloucester": "f74e347c0622425cbcb6d59d93ca6ac0",
    "Hudson": "ea1be78d1bb04de1a13e236bf97f3737", "Hunterdon": "93575d7d60244e08a59650fb7bc6d235",
    "Mercer": "9310ce145949424caa1eef3b4911c537", "Middlesex": "cae0c9f99c28401cbb7b9c4364648ce9",
    "Monmouth": "372377f86745436b821f2f4b93485be6", "Morris": "bd538e4bd3db4822a77e4f4915065709",
    "Ocean": "cae7138df4594d839b9982d2b005aaa3", "Passaic": "383bc45ca33b4466ab89e6ee57551859",
    "Salem": "98612e23ebe14911b60f4df4d1441ad9", "Somerset": "333f558cfa6f4d3dbe14e4acf9dc633d",
    "Sussex": "6a7fb6b968d649248bcf5f82d50b30cd", "Union": "2abc1d31e61842ea85b237104ddc9576",
    "Warren": "45c73f57ad8a4c38b9768671aa967850",
}
DOWNLOAD_DELAY = 3.0          # seconds between bulk downloads from the same host

NYC_COUNTIES = {"Kings": "Brooklyn", "Queens": "Queens", "New York": "Manhattan", "Bronx": "Bronx",
                "Richmond": "Staten Island"}
LIC_ZIPS = {"11101", "11109", "11120"}
AREA_ORDER = ["New Jersey", "Brooklyn", "Connecticut", "Long Island", "Long Island City"]


# ---------------------------------------------------------------- refusals and downloads
def record_refusal(host: str, url: str, reason: str) -> None:
    try:
        kill = json.loads(KILL.read_text())
    except (OSError, ValueError):
        kill = {}
    if host not in kill:
        kill[host] = {"reason": reason, "url": url, "at": now_iso(), "by": "scripts/building_stories.py"}
        KILL.write_text(json.dumps(kill, indent=1) + "\n")
    print(f"REFUSED {host}: {reason} -> recorded in raw/{KILL.name}", flush=True)


def _log(entry: dict) -> None:
    RAWDIR.mkdir(parents=True, exist_ok=True)
    with open(RAWDIR / "_index.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def stream_download(url: str, dest: Path) -> dict | None:
    """Fetch url to dest (via dest.part). Returns the meta dict, or None when the host refused (recorded)."""
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    lib.check_host(host)
    lib._throttle(host)
    part = dest.with_name(dest.name + ".part")
    with requests.get(url, headers={"User-Agent": lib.USER_AGENT}, stream=True, timeout=120) as r:
        meta = {"url": url, "retrieved_at": now_iso(), "status": r.status_code,
                "content_type": r.headers.get("content-type", ""), "bytes_expected": r.headers.get("content-length"),
                "last_modified": r.headers.get("last-modified", ""), "path": str(dest.relative_to(ROOT))}
        if r.status_code in (401, 403, 429):
            _log(meta)
            record_refusal(host, url, f"HTTP {r.status_code}")
            return None
        if r.status_code != 200:
            _log(meta)
            raise RuntimeError(f"HTTP {r.status_code} for {url}")
        if "zip" not in meta["content_type"] and "octet-stream" not in meta["content_type"]:
            head = r.raw.read(600, decode_content=True)
            meta["note"] = "not a zip: " + head[:200].decode("utf-8", "replace")
            _log(meta)
            record_refusal(host, url, f"bot wall or page instead of the file ({meta['content_type']})")
            return None
        n = 0
        with open(part, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                n += len(chunk)
    exp = meta["bytes_expected"]
    if exp and int(exp) != n:
        raise RuntimeError(f"short download {n} of {exp} bytes: {url}")
    part.rename(dest)
    meta["bytes"] = n
    _log(meta)
    dest.with_name(dest.name + ".meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def nj_counties_needed() -> list[str]:
    b = load_buildings()
    return sorted({c for c, s in zip(b["county"], b["state"]) if s == "NJ" and c in NJ_ITEMS})


def download(counties: list[str] | None = None) -> None:
    NJDIR.mkdir(parents=True, exist_ok=True)
    counties = counties or nj_counties_needed()
    print("NJ counties needed:", ", ".join(counties), flush=True)
    for c in counties:
        item, meta = lib.get_json(ITEM_URL.format(NJ_ITEMS[c]), "building_stories/arcgis_items", params={"f": "json"})
        url = item.get("url") or ""
        if not url.endswith(".zip"):
            print(f"  {c}: item has no zip url ({url!r}); skipped", flush=True)
            continue
        dest = NJDIR / url.rsplit("/", 1)[1]
        if dest.exists() and dest.with_name(dest.name + ".meta.json").exists():
            print(f"  {c}: on disk ({dest.name})", flush=True)
            continue
        if lib.host_refusal(url.split("/")[2]):
            print(f"  {c}: host refused earlier; stop", flush=True)
            return
        print(f"  {c}: downloading {url}", flush=True)
        m = stream_download(url, dest)
        if m is None:
            return
        print(f"  {c}: {m['bytes'] / 1e6:.1f} MB", flush=True)
        time.sleep(DOWNLOAD_DELAY)


# ---------------------------------------------------------------- candidates
_BUILDINGS = None


def load_buildings():
    """Candidate buildings with county and area, one row per addr_key, in output order."""
    global _BUILDINGS
    if _BUILDINGS is not None:
        return _BUILDINGS
    import geopandas as gpd
    import pandas as pd
    L = pd.read_csv(LISTINGS, dtype=str, keep_default_na=False)
    L["rent_num"] = pd.to_numeric(L.listed_rent, errors="coerce")
    C = L[(L.rent_num <= RENT_MAX) & L.gate_status.isin(["pending", "pass"]) & (L.addr_key != "")].copy()

    def mode(s):
        s = [x for x in s if x]
        return Counter(s).most_common(1)[0][0] if s else ""

    g = C.groupby("addr_key")
    B = pd.DataFrame({
        "address": g.address.agg(mode), "city": g.city.agg(mode), "state": g.state.agg(mode),
        "zip": g.zip5.agg(mode), "lat": g.lat.agg(mode), "lon": g.lon.agg(mode),
        "n_listings": g.size(),
    }).reset_index()
    B["latf"] = pd.to_numeric(B.lat, errors="coerce")
    B["lonf"] = pd.to_numeric(B.lon, errors="coerce")
    co = gpd.read_file(f"zip://{COUNTY_ZIP}")
    co = co[co.STATEFP.isin(["09", "34", "36", "42"])][["STATEFP", "NAME", "geometry"]]
    pts = gpd.GeoDataFrame(B, geometry=gpd.points_from_xy(B.lonf, B.latf), crs=4326).to_crs(co.crs)
    j = gpd.sjoin(pts, co, how="left", predicate="within")
    j = j[~j.index.duplicated()]
    B["county"] = j["NAME"].fillna("").values
    B["county_state"] = j["STATEFP"].fillna("").values

    def area(r):
        if r.state == "NJ" or r.county_state == "34":
            return "New Jersey"
        if r.state == "CT" or r.county_state == "09":
            return "Connecticut"
        if r.county in ("Nassau", "Suffolk"):
            return "Long Island"
        if r.county == "Queens" and r.zip in LIC_ZIPS:
            return "Long Island City"
        if r.county == "Kings":
            return "Brooklyn"
        if r.county in NYC_COUNTIES:
            return NYC_COUNTIES[r.county]
        return (r.county + " County") if r.county else ("PA" if r.state == "PA" else r.state or "unknown")

    B["area"] = [area(r) for r in B.itertuples()]
    B["prio"] = B.area.map(lambda a: AREA_ORDER.index(a) if a in AREA_ORDER else len(AREA_ORDER))
    B = B.sort_values(["prio", "area", "addr_key"]).reset_index(drop=True)
    _BUILDINGS = B
    return B


# ---------------------------------------------------------------- main
def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "all"
    if cmd in ("download", "all"):
        download(argv[1:] if cmd == "download" and len(argv) > 1 else None)
    if cmd in ("build", "all"):
        build()


if __name__ == "__main__":
    main(sys.argv[1:])
