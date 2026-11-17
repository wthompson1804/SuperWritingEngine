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
    B["county"] = j["NAME"].reindex(B.index).fillna("").values
    B["county_state"] = j["STATEFP"].reindex(B.index).fillna("").values

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


# ---------------------------------------------------------------- addresses
SUFFIX = {"STREET": "ST", "STR": "ST", "AVENUE": "AVE", "AV": "AVE", "AVE": "AVE", "BOULEVARD": "BLVD",
          "BLVD": "BLVD", "ROAD": "RD", "DRIVE": "DR", "DRV": "DR", "PLACE": "PL", "COURT": "CT", "LANE": "LN",
          "TERRACE": "TER", "TERR": "TER", "PARKWAY": "PKWY", "PKY": "PKWY", "HIGHWAY": "HWY", "CIRCLE": "CIR",
          "SQUARE": "SQ", "TURNPIKE": "TPKE", "TPK": "TPKE", "PLAZA": "PLZ", "EXTENSION": "EXT", "HEIGHTS": "HTS",
          "CRESCENT": "CRES", "ALLEY": "ALY", "EXPRESSWAY": "EXPY", "CENTER": "CTR", "TRAIL": "TRL", "WAY": "WAY",
          "ROW": "ROW", "WALK": "WALK", "PATH": "PATH", "LOOP": "LOOP", "RUN": "RUN", "PIKE": "PIKE", "PARK": "PARK",
          "CROSSING": "XING", "POINT": "PT", "GARDENS": "GDNS", "HILL": "HL", "BROADWAY": "BROADWAY"}
DIRS = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "N": "N", "S": "S", "E": "E", "W": "W",
        "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW"}
ORDINAL_WORDS = {"FIRST": "1", "SECOND": "2", "THIRD": "3", "FOURTH": "4", "FIFTH": "5", "SIXTH": "6",
                 "SEVENTH": "7", "EIGHTH": "8", "NINTH": "9", "TENTH": "10", "ELEVENTH": "11", "TWELFTH": "12"}
_UNIT_TAIL = re.compile(r"\s(?:#|APT|APARTMENT|UNIT|STE|SUITE|FL|FLOOR|BLDG|BUILDING|RM)\b.*$|\s#.*$")


def split_address(addr: str):
    """'243-247 Stewart Ave.' -> ('243', '247', 'STEWART AVE'); '142-38 37th Ave' -> ('142-38', None, '37 AVE').
    Returns (number, range_end or None, street) with the street normalised; (None, None, '') when no number."""
    s = str(addr or "").upper().split(",")[0]
    s = s.split("/")[0]                               # MOD-IV 'A ST/AKA B ST': the first address
    s = re.sub(r"[.']", "", s)
    s = re.sub(r"(?<=[A-Z])(APT|APARTMENT|UNIT|SUITE)(?=[\s#\d]|$)", r" \1", s)   # 'AvenueApt 9'
    s = re.sub(r"\s\d+(?:ST|ND|RD|TH)\s+(?:FL|FLR|FLOOR)\b.*$", "", s)            # '53 Budd St 2nd Fl'
    s = _UNIT_TAIL.sub("", " " + s).strip()
    s = re.sub(r"\b(?:US|NJ|NY|CT|STATE|COUNTY)?\s*(?:HIGHWAY|HWY|ROUTE|RTE|RT)\s*(\d+)", r" RT \1", s)
    s = re.sub(r"\s+", " ", s).strip()
    m = re.match(r"^(\d+[A-Z]?)(?:\s*-\s*(\d+[A-Z]?))?\s+(.*)$", s)
    if not m:
        return None, None, ""
    a, b, street = m.group(1), m.group(2), m.group(3)
    toks = []
    for t in re.split(r"[\s\-]+", street):
        if not t:
            continue
        t = ORDINAL_WORDS.get(t, t)
        t = {"SAINT": "ST", "MOUNT": "MT", "FORT": "FT"}.get(t, t)
        if t in SUFFIX:                   # type words inside a name ('BOULEVARD EAST') are spelled one way too
            t = SUFFIX[t]
        t = re.sub(r"^(\d+)(?:ST|ND|RD|TH)$", r"\1", t)
        toks.append(t)
    if toks and toks[0] in DIRS and len(toks) > 1:
        toks[0] = DIRS[toks[0]]
    if toks and toks[-1] in SUFFIX:
        toks[-1] = SUFFIX[toks[-1]]
    if len(toks) > 1 and toks[-1] in DIRS:
        toks[-1] = DIRS[toks[-1]]
    return a, b, " ".join(toks)


def street_parts(street: str) -> tuple[str, str, str]:
    """'W 19 ST' -> ('W', '19', 'ST'); 'KENNEDY BLVD' -> ('', 'KENNEDY', 'BLVD'); '37 AVE' -> ('', '37', 'AVE')."""
    toks = street.split()
    sfx = dr = ""
    if len(toks) > 1 and toks[-1] in set(DIRS.values()):
        dr = toks[-1]
        toks = toks[:-1]
    if len(toks) > 1 and toks[-1] in set(SUFFIX.values()):
        sfx = toks[-1]
        toks = toks[:-1]
    if len(toks) > 1 and toks[0] in set(DIRS.values()):
        dr = dr or toks[0]
        toks = toks[1:]
    return dr, " ".join(toks), sfx


def street_core(street: str) -> str:
    """The street name without its type and direction words (the join's first, fast test)."""
    return street_parts(street)[1]


def streets_match(s1: str, s2: str) -> bool:
    """Same name; type and direction equal where both give one ('37 AVE' is not '37 ST'; 'E 2 ST' is not 'W 2 ST')."""
    d1, n1, t1 = street_parts(s1)
    d2, n2, t2 = street_parts(s2)
    return bool(n1) and n1 == n2 and (not t1 or not t2 or t1 == t2) and (not d1 or not d2 or d1 == d2)


def _int(x):
    m = re.match(r"\d+", str(x or ""))
    return int(m.group(0)) if m else None


def numbers_match(a1, b1, a2, b2) -> bool:
    """House numbers agree: equal, or one lies in the other's range ('243-247' holds 245)."""
    if a1 is None or a2 is None:
        return False
    if a1 == a2:
        return True
    def rng(a, b):
        lo, hi = _int(a), _int(b) if b else None
        if lo is not None and hi is not None and hi > lo and hi - lo <= 400:
            return lo, hi
        return (lo, lo) if lo is not None else None
    r1, r2 = rng(a1, b1), rng(a2, b2)
    if not r1 or not r2:
        return False
    if (b1 is None and re.search(r"[A-Z]", a1)) or (b2 is None and re.search(r"[A-Z]", a2)):
        return False                                   # '5B' is not '5'
    return r1[0] <= r2[1] and r2[0] <= r1[1]


def nyc_number(addr: str) -> str:
    """Queens-style '142-38' and plain '58' as digits only (as scripts/enrich_nyc_pluto.py: housenum)."""
    m = re.match(r"\s*(\d+(?:-\d+)?)", str(addr or ""))
    return re.sub(r"[^0-9]", "", m.group(1)) if m else ""


def _metres(lat1, lon1, lat2, lon2) -> float:
    return math.hypot((lat2 - lat1) * 111320.0, (lon2 - lon1) * 111320.0 * math.cos(math.radians(lat1)))


def fmt_num(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(f) or f <= 0:
        return ""
    return str(int(f)) if f == int(f) else f"{f:g}"


# ---------------------------------------------------------------- New Jersey MOD-IV
_DESC_RANGE = re.compile(r"^(\d{1,2}(?:\.\d)?)\s?(?:&|AND|TO|/|-)\s?(\d{1,2}(?:\.\d)?)\s?S(?![A-Z]{3})")
_DESC_S = re.compile(r"^(\d{1,3}(?:\.\d{1,2})?)\s?S(?:TY|TORY|TORIES|TRY)?(?=$|[-\s+/,.(&]|[A-Z])(?!TUDIO)")
_DESC_MAT_FIRST = re.compile(r"^(?:F|B|BR|FR|M|AL|CB|ST)\s?(\d{1,2}(?:\.\d)?)\s?S(?=$|[-\s/])")   # 'F2S', 'B2S'
_DESC_STR = re.compile(r"(?:^|[-\s/])(\d{1,2}(?:\.\d)?)\s?(?:STR|STY|STORY|STORIES|STORY'S)(?=$|[-\s/,])")  # '257APT/3STR/OFF'
_DESC_INNER_S = re.compile(r"[-\s/](\d{1,2}(?:\.\d)?)S(?=$|[-\s/])")                       # '2A-F-2S'
_DESC_MAT = re.compile(r"^(\d{1,2}(?:\.\d)?)\s?(?:F|B|FR|BR|BRK|CB|M|AL|ST)\s?-\s?\d+\s?U\b")


def stories_from_desc(desc) -> tuple[str, str]:
    """Storeys stated at the start of a MOD-IV building description, as (value, how) or ('', '').
    '3S-B-D-6U-H' -> '3'; '2.5S-F-D-2U-H' -> '2.5'; '4&5S-470U-CONDO' -> '5' (4 and 5); '4B-8U-H' -> '4';
    '1BR/1BA', 'CONDO', 'VACANT LAND' -> no reading."""
    d = re.sub(r"\s+", " ", str(desc or "").upper().strip())
    if not d or d in ("NAN", "NONE"):
        return "", ""
    m = _DESC_RANGE.match(d)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        if 0 < lo < hi <= 120:
            return fmt_num(hi), f"range {fmt_num(lo)} to {fmt_num(hi)} storeys; the higher is used"
    m = _DESC_S.match(d)
    if m and not re.match(r"^\d+\s?STUDIO", d):
        v = float(m.group(1))
        if 0 < v <= 120:
            return fmt_num(v), "leading '<n>S'"
    m = _DESC_MAT.match(d)
    if m:
        v = float(m.group(1))
        if 0 < v <= 120:
            return fmt_num(v), "leading '<n><material>-<units>U'"
    m = _DESC_MAT_FIRST.match(d)
    if m and 0 < float(m.group(1)) <= 120:
        return fmt_num(m.group(1)), "material then '<n>S' ('F2S')"
    found = {float(x) for x in _DESC_STR.findall(d)} or {float(x) for x in _DESC_INNER_S.findall(d)}
    if len(found) == 1 and 0 < next(iter(found)) <= 120:
        return fmt_num(next(iter(found))), "'<n>STR' / '-<n>S' inside the description"
    return "", ""


def nj_extract(county: str):
    """Tax-list rows of one county with storeys parsed and a parcel centroid (lat/lon). Cached as csv.gz."""
    import pandas as pd
    cache = NJDIR / f"{county.replace(' ', '')}_taxlist.csv.gz"
    zips = sorted(NJDIR.glob(f"parcels_gdb_{county.replace(' ', '')}*.zip"))
    if not zips:
        return None, None
    zp = zips[0]
    meta_p = zp.with_name(zp.name + ".meta.json")
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {"url": "", "retrieved_at": ""}
    if cache.exists() and cache.stat().st_mtime >= zp.stat().st_mtime:
        return pd.read_csv(cache, dtype=str, keep_default_na=False), meta
    import pyogrio
    import geopandas as gpd
    gdbs = [n for n in __import__("zipfile").ZipFile(zp).namelist() if n.lower().endswith(".gdb/")]
    path = f"/vsizip/{zp}/{gdbs[0].rstrip('/')}" if gdbs else f"/vsizip/{zp}"
    layers = [l[0] for l in pyogrio.list_layers(path)]
    tl = next(l for l in layers if "tax" in l.lower())
    pl = next(l for l in layers if "parcel" in l.lower())
    t = pyogrio.read_dataframe(path, layer=tl, read_geometry=False,
                               columns=["GIS_PIN", "PROP_CLASS", "PROP_LOC", "MUN_NAME", "BLDG_DESC", "YR_CONSTR",
                                        "QUALIFIER"])
    p = pyogrio.read_dataframe(path, layer=pl, columns=["PAMS_PIN"])
    p = p[p.geometry.notna()]
    p["area_m2"] = p.geometry.area * 0.092903 if "foot" in str(p.crs.axis_info[0].unit_name).lower() else p.geometry.area
    c = p.geometry.representative_point()
    c = gpd.GeoSeries(c, crs=p.crs).to_crs(4326)
    p["plat"], p["plon"] = c.y.round(6), c.x.round(6)
    p = p.drop(columns="geometry").drop_duplicates("PAMS_PIN")
    t["base_pin"] = t.GIS_PIN.astype(str).str.replace(r"_[A-Z]+\d*$", "", regex=True)
    t = t.merge(p.rename(columns={"PAMS_PIN": "GIS_PIN"}), on="GIS_PIN", how="left")
    miss = t.plat.isna()
    t2 = t.loc[miss, ["base_pin"]].merge(p.rename(columns={"PAMS_PIN": "base_pin"}), on="base_pin", how="left")
    t.loc[miss, ["plat", "plon", "area_m2"]] = t2[["plat", "plon", "area_m2"]].values
    t = t[t.plat.notna()].copy()
    sv = [stories_from_desc(d) for d in t.BLDG_DESC]
    t["stories"] = [x[0] for x in sv]
    t["stories_how"] = [x[1] for x in sv]
    t["area_m2"] = pd.to_numeric(t.area_m2, errors="coerce").round(0)
    t = t.fillna("")
    t.to_csv(cache, index=False, compression="gzip")
    return pd.read_csv(cache, dtype=str, keep_default_na=False), meta


def nj_lookup(B):
    """{addr_key: result dict} for NJ buildings from the county MOD-IV files on disk."""
    import numpy as np
    from scipy.spatial import cKDTree
    out = {}
    for county in sorted(set(B.county[B.area == "New Jersey"])):
        sub = B[(B.area == "New Jersey") & (B.county == county)]
        t, meta = nj_extract(county)
        if t is None:
            for k in sub.addr_key:
                out[k] = {"status": "no_file", "note": f"MOD-IV file for {county} County not on disk"}
            continue
        lat, lon = t.plat.astype(float).values, t.plon.astype(float).values
        xy = np.c_[lat * 111.32, lon * 111.32 * math.cos(math.radians(40.5))]
        tree = cKDTree(xy)
        parts = [split_address(a) for a in t.PROP_LOC]
        cores = [street_core(s) for _, _, s in parts]
        for r in sub.itertuples():
            if not (math.isfinite(r.latf) and math.isfinite(r.lonf)):
                out[r.addr_key] = {"status": "no_point", "note": "no coordinates"}
                continue
            a, b, street = split_address(r.address)
            core = street_core(street)
            q = [r.latf * 111.32, r.lonf * 111.32 * math.cos(math.radians(40.5))]
            near = tree.query_ball_point(q, 0.4)
            hits = [i for i in near if core and cores[i] == core and streets_match(street, parts[i][2])
                    and numbers_match(a, b, parts[i][0], parts[i][1])]
            how = "address"
            if not hits:
                # an apartment complex filed under one address: the nearest parcel is a large class 4C lot on the
                # same street and the point lies well inside its footprint (a neighbour's house is never taken)
                d, i = tree.query(q)
                try:
                    area_m2 = float(t.area_m2.iloc[i])
                except ValueError:
                    area_m2 = 0.0
                if (t.PROP_CLASS.iloc[i] == "4C" and area_m2 >= 8000 and d * 1000 <= 0.5 * math.sqrt(area_m2)
                        and core and cores[i] == core and streets_match(street, parts[i][2])):
                    hits, how = [i], "location"
            if not hits:
                out[r.addr_key] = {"status": "no_match", "county": county, "meta": meta,
                                   "note": f"no MOD-IV tax record at '{r.address}' within 400 m in {county} County"}
                continue
            rows = t.iloc[hits]
            resid = rows[rows.PROP_CLASS.isin(["2", "4C", "4A"]) & (rows.stories != "")]
            if len(resid) and len(resid) < len(rows):
                rows = resid                    # a garage, vacant or exempt lot at the same address is not the building
            vals = [v for v in rows.stories if v]
            pins = sorted(set(rows.GIS_PIN))
            desc = Counter(x for x in rows.BLDG_DESC if x).most_common(3)
            base = {"county": county, "meta": meta, "pins": pins, "prop_loc": rows.PROP_LOC.iloc[0],
                    "mun": rows.MUN_NAME.iloc[0], "classes": sorted(set(rows.PROP_CLASS)), "desc": desc, "how": how,
                    "dist_m": round(_metres(r.latf, r.lonf, float(rows.plat.iloc[0]), float(rows.plon.iloc[0])))}
            if not vals:
                out[r.addr_key] = {**base, "status": "no_stories"}
                continue
            cnt = Counter(vals)
            best = max(cnt, key=lambda v: (cnt[v], float(v)))
            big = [float(a) for a, c in zip(rows.area_m2, rows.PROP_CLASS) if c == "4C" and a and float(a) >= 8000]
            out[r.addr_key] = {**base, "status": "ok", "stories": best, "values": dict(cnt), "complex": bool(big),
                               "how_desc": rows.stories_how[rows.stories == best].iloc[0],
                               "desc_used": rows.BLDG_DESC[rows.stories == best].iloc[0]}
    return out


# ---------------------------------------------------------------- NYC PLUTO (held copy only)
def pluto_lookup(B):
    import numpy as np
    import pandas as pd
    from scipy.spatial import cKDTree
    nyc = B[B.county.isin(list(NYC_COUNTIES))]
    out = {}
    if not PLUTO_RAW.exists() or nyc.empty:
        return out
    retrieved = ""
    if PLUTO_INDEX.exists():
        for line in PLUTO_INDEX.read_text().splitlines():
            try:
                retrieved = max(retrieved, json.loads(line).get("retrieved_at", ""))
            except ValueError:
                pass
    p = pd.read_csv(PLUTO_RAW, dtype=str, keep_default_na=False)
    p = p[(p.latitude != "") & (p.longitude != "")].reset_index(drop=True)
    plat, plon = p.latitude.astype(float).values, p.longitude.astype(float).values
    tree = cKDTree(np.c_[plat * 111.32, plon * 111.32 * math.cos(math.radians(40.7))])
    pnum = [nyc_number(a) for a in p.address]
    pstreet = [split_address(a)[2] for a in p.address]
    pcore = [street_core(x) for x in pstreet]
    facts = {}
    if NYC_FACTS.exists():
        f = pd.read_csv(NYC_FACTS, dtype=str, keep_default_na=False)
        facts = {r.addr_key: r for r in f.itertuples()}
    for r in nyc.itertuples():
        res = {"retrieved_at": retrieved}
        if math.isfinite(r.latf) and math.isfinite(r.lonf):
            street = split_address(r.address)[2]
            num, core = nyc_number(r.address), street_core(street)
            q = [r.latf * 111.32, r.lonf * 111.32 * math.cos(math.radians(40.7))]
            cand = [i for i in tree.query_ball_point(q, 0.15) if num and pnum[i] == num and pcore[i] == core
                    and streets_match(street, pstreet[i])]
            if cand:
                i = min(cand, key=lambda i: _metres(r.latf, r.lonf, plat[i], plon[i]))
                res.update(status="ok", bbl=p.bbl[i].split(".")[0], address=p.address[i], floors=p.numfloors[i],
                           cls=p.bldgclass[i], units=p.unitsres[i], year=p.yearbuilt[i],
                           dist=round(_metres(r.latf, r.lonf, plat[i], plon[i])), how="house number + street")
        fr = facts.get(r.addr_key)
        if res.get("status") != "ok" and fr is not None and fr.match_basis == "house_number+location" and fr.pluto_floors:
            res.update(status="ok", bbl=fr.pluto_bbl, address=fr.pluto_address, floors=fr.pluto_floors,
                       cls=fr.pluto_class, units=fr.pluto_units, year=fr.pluto_year, dist=fr.match_m,
                       how="house number + location (nyc_building_facts.csv; street spelled differently)")
        if res.get("status") != "ok":
            why = "no PLUTO lot (4+ residential units, the held copy) with this house number and street within 150 m"
            if fr is not None and fr.match_basis == "nearest_lot":
                why += f"; nyc_building_facts.csv has only a nearest-lot match ({fr.pluto_address}, {fr.match_m} m), not used"
            res.update(status="no_match", note=why)
        out[r.addr_key] = res
    return out


# ---------------------------------------------------------------- OpenStreetMap building:levels (held extract)
def osm_lookup(B, keys):
    import numpy as np
    import importlib.util
    spec = importlib.util.spec_from_file_location("hh_places", Path(__file__).parent / "tools" / "places.py")
    places = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(places)
    idx = places._load()
    meta = idx["meta"]
    out = {}
    sub = B[B.addr_key.isin(keys)]
    for r in sub.itertuples():
        if not (math.isfinite(r.latf) and math.isfinite(r.lonf)):
            out[r.addr_key] = {"status": "no_point"}
            continue
        if not places._in_coverage(idx, r.latf, r.lonf):
            out[r.addr_key] = {"status": "outside", "note": "outside the OSM extract's bounding box"}
            continue
        xy = np.array(idx["tr"].transform(r.lonf, r.latf))
        b = places._building(idx, xy)
        bl = b.get("building_levels") or {}
        bu = b.get("building") or {}
        res = {"retrieved_at": meta.get("retrieved_at", ""), "vintage": meta.get("osm_data_timestamp", ""),
               "extract": meta.get("source_url", ""), "way": bu.get("value") or "", "dist": bu.get("metres_from_point"),
               "btype": (b.get("building_type") or {}).get("value") or ""}
        if not bu.get("value"):
            res.update(status="no_outline", note="no OSM building outline within 40 m")
        elif (res["dist"] or 0) > 20:
            res.update(status="far", note=f"nearest OSM outline is {res['dist']} m from the point (over 20 m): not used")
        elif bl.get("value") is None:
            res.update(status="no_levels", note="the OSM outline has no building:levels tag")
        else:
            res.update(status="ok", levels=fmt_num(bl["value"]))
        out[r.addr_key] = res
    return out


# ---------------------------------------------------------------- listing pages we hold
def listing_lookup():
    import pandas as pd
    L = pd.read_csv(LISTINGS, dtype=str, keep_default_na=False)
    L = L[L.detail_level.isin(["detail", "building_unit", "building_page", "listing_page"]) &
          ~L.source_site.str.contains("trulia|zillow", case=False)]
    L = L[L.building_floors.str.fullmatch(r"\d{1,3}")]
    out = {}
    for k, g in L.groupby("addr_key"):
        cnt = Counter(g.building_floors)
        v = cnt.most_common(1)[0][0]
        row = g[g.building_floors == v].sort_values("last_seen").iloc[-1]
        out[k] = {"stories": v, "url": row.url, "site": row.source_site, "seen": row.last_seen, "values": dict(cnt)}
    return out


# ---------------------------------------------------------------- building_stories.csv
def build_stories():
    B = load_buildings()
    print(f"{len(B)} candidate buildings", flush=True)
    nj = nj_lookup(B)
    print("NJ MOD-IV:", Counter(v["status"] for v in nj.values()), flush=True)
    pl = pluto_lookup(B)
    print("PLUTO:", Counter(v["status"] for v in pl.values()), flush=True)
    li = listing_lookup()
    official = {k for k, v in {**nj, **pl}.items() if v.get("status") == "ok"}
    osm = osm_lookup(B, set(B.addr_key))
    print("OSM:", Counter(v["status"] for v in osm.values()), flush=True)
    rows = []
    for r in B.itertuples():
        k = r.addr_key
        base = {"addr_key": k, "address": r.address, "city": r.city, "state": r.state, "zip": r.zip,
                "lat": r.lat, "lon": r.lon}
        notes, rec = [f"area: {r.area}" + (f"; county: {r.county}" if r.county else "")], None
        o, l_ = osm.get(k, {}), li.get(k)
        if k in nj:
            v = nj[k]
            if v["status"] == "ok":
                alt = "" if len(v["values"]) == 1 else "; other records at this address read " + \
                    ", ".join(f"{s} ({n})" for s, n in v["values"].items() if s != v["stories"])
                rec = {"stories": v["stories"], "stories_basis": "official_record",
                       "source_name": f"NJ MOD-IV tax list ({v['county']} County Parcels & MOD-IV, NJ Office of GIS)",
                       "source_url": v["meta"].get("url", ""), "retrieved_at": v["meta"].get("retrieved_at", "")}
                notes.append(f"BLDG_DESC '{v['desc_used']}' ({v['how_desc']}); PIN {', '.join(v['pins'][:4])}"
                             f"{' and %d more' % (len(v['pins']) - 4) if len(v['pins']) > 4 else ''}; "
                             f"tax address '{v['prop_loc']}', {v['mun']}; class {'/'.join(v['classes'])}; joined by "
                             + ("house number and street, parcel within 400 m" if v["how"] == "address" else
                                f"location: the point lies {v['dist_m']} m from the centre of a large apartment lot (class 4C) "
                                "on the same street whose tax address has another house number")
                             + alt + ("; a large apartment lot: the description gives the lot's building type, "
                                      "and single buildings of a complex can differ" if v.get("complex") else ""))
            elif v["status"] == "no_stories":
                notes.append(f"NJ MOD-IV record found (PIN {', '.join(v['pins'][:3])}, '{v['prop_loc']}', descriptions "
                             + "; ".join(f"'{d}'" for d, _ in v["desc"]) + ") but its BLDG_DESC states no storeys")
            else:
                notes.append("NJ MOD-IV: " + v.get("note", v["status"]))
        if k in pl:
            v = pl[k]
            if v["status"] == "ok" and fmt_num(v["floors"]):
                rec = {"stories": fmt_num(v["floors"]), "stories_basis": "official_record",
                       "source_name": "NYC PLUTO numfloors (NYC Dept of City Planning; held copy, raw/big/pluto)",
                       "source_url": PLUTO_SRC, "retrieved_at": v["retrieved_at"]}
                notes.append(f"BBL {v['bbl']}, '{v['address']}', class {v['cls']}, {v['units']} residential units, "
                             f"built {v['year']}; joined by {v['how']} ({v['dist']} m); no new request to "
                             "data.cityofnewyork.us")
            elif v["status"] == "ok":
                notes.append(f"PLUTO lot {v['bbl']} found but numfloors is {v['floors']!r}")
            else:
                notes.append("PLUTO: " + v["note"])
        if r.area in ("Connecticut", "Long Island") or (r.state == "NY" and r.county not in NYC_COUNTIES):
            notes.append("no official storey record: the state/county parcel layers hold no storey field "
                         "(see docs/harvest_notes/building_stories.md)")
        if rec is None and l_:
            rec = {"stories": l_["stories"], "stories_basis": "listing", "source_name": f"listing page ({l_['site']})",
                   "source_url": l_["url"], "retrieved_at": l_["seen"]}
            notes.append("building floor count stated on the listing page (data/listings.csv building_floors)")
        elif l_ and rec and l_["stories"] != rec["stories"]:
            notes.append(f"CONFLICT: a listing page states {l_['stories']} floors ({l_['url']})")
        if rec is None and o.get("status") == "ok":
            rec = {"stories": o["levels"], "stories_basis": "osm",
                   "source_name": "OpenStreetMap building:levels (Geofabrik extract, data "
                                  f"{o['vintage'][:10]}; ODbL)", "source_url": o["way"], "retrieved_at": o["retrieved_at"]}
            notes.append(("point inside the outline" if not o["dist"] else f"nearest outline {o['dist']} m from the point")
                         + f"; building={o['btype']}; building:levels counts storeys above ground, roof levels excluded;"
                           f" extract {o['extract']}")
        elif rec and o.get("status") == "ok" and o["levels"] != rec["stories"]:
            notes.append(f"OSM building:levels says {o['levels']} ({o['way']})")
        elif rec is None:
            notes.append("OSM: " + o.get("note", o.get("status", "not looked up")))
        if rec is None:
            rec = {"stories": "", "stories_basis": "", "source_name": "", "source_url": "", "retrieved_at": ""}
            notes.insert(0, "not_found")
        rows.append({**base, **rec, "notes": "; ".join(notes)})
    write_csv(OUT_STORIES, STORIES_COLS, rows)
    return rows, B


def write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    tmp.replace(path)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)", flush=True)


# ---------------------------------------------------------------- unit_floor_reads.csv
GROUND_LABELS = {"GROUND", "GRD", "GRND", "GROUNDFLOOR", "GROUNDFL"}
BAD_PREFIX = {"G", "GR", "GD", "PH", "TH", "L", "LL", "LB", "BSMT", "BS", "M", "MZ"}  # garden/ground, penthouse,
# townhouse, lower level/lobby, basement, mezzanine: letters that can themselves name a level, so the digits are not read
_PATTERNS = [
    # (name, regex on the cleaned upper-case label, group holding the floor, description)
    ("floor_then_letter", re.compile(r"^(\d{1,2})([A-Z]{1,2})$"), 1, "floor number, then a letter line ('2B', '14N')"),
    ("floor_then_two_digits", re.compile(r"^([1-9])(\d{2})$"), 1, "three digits: floor, then a two-digit number ('205')"),
    ("building_letters_then_floor_two_digits", re.compile(r"^([A-Z]{1,4})[-\s]?([1-9])(\d{2})$"), 2,
     "building letters, then floor and a two-digit number ('JCE-205', 'A421')"),
    ("building_number_then_floor_two_digits", re.compile(r"^([A-Z]?\d{1,3})[-\s]([1-9])(\d{2})$"), 2,
     "building number, separator, then floor and a two-digit number ('09-326', 'B9-240')"),
    ("building_letters_letter_floor_two_digits", re.compile(r"^([A-Z]{2,4})[-\s]([A-Z])([1-9])(\d{2})$"), 3,
     "building code, then a letter, floor and a two-digit number ('BAY-B508')"),
    ("house_number_then_floor_letter", re.compile(r"^(\d{1,5})[-\s](\d{1,2})([A-Z]{1,2})$"), 2,
     "street number, separator, then floor and a letter ('158-2H')"),
]


def read_label(unit: str):
    """(floor, convention, description) for a clear label, else None."""
    u = parsers.clean_unit(unit).upper().strip()
    u = re.sub(r"^(?:NO\.?|NUMBER)\s*", "", u).strip("#. ")
    if not u or parsers.is_plan_label(unit):
        return None
    if re.sub(r"[^A-Z]", "", u) in GROUND_LABELS and not re.search(r"\d", u):
        return 1, "ground_word", "the label says ground floor (ground counted as floor 1)"
    for name, rx, grp, desc in _PATTERNS:
        m = rx.match(u)
        if not m:
            continue
        if name.startswith("building_letters") and m.group(1) in BAD_PREFIX:
            return None
        f = int(m.group(grp))
        if f < 1:
            return None
        return f, name, desc
    return None


def build_floors(stories_rows):
    import pandas as pd
    L = pd.read_csv(LISTINGS, dtype=str, keep_default_na=False)
    L["rent_num"] = pd.to_numeric(L.listed_rent, errors="coerce")
    C = L[(L.rent_num <= RENT_MAX) & L.gate_status.isin(["pending", "pass"]) & (L.unit.str.strip() != "")]
    conv = {}
    if CONVENTIONS.exists() and CROSSWALK.exists():
        cv = pd.read_csv(CONVENTIONS, dtype=str, keep_default_na=False)
        cw = pd.read_csv(CROSSWALK, dtype=str, keep_default_na=False)
        bid_conv = dict(zip(cv.building_id, zip(cv.convention, cv.name)))
        conv = {a: bid_conv[b] for a, b in zip(cw.addr_key, cw.building_id) if b in bid_conv}
    st = {r["addr_key"]: (r["stories"], r["stories_basis"]) for r in stories_rows if r["stories"]}
    rows, skipped = [], Counter()
    above = defaultdict(list)            # addr_key -> label floors above the recorded storeys
    for r in C.itertuples():
        unit = r.unit.strip()
        notes = []
        res = None
        c = conv.get(r.addr_key)
        if c:
            f = parsers.floor_by_convention(unit, c[0])
            if f is not None:
                res = (f, c[0], f"reviewed numbering convention of {c[1]} (data/reference/unit_numbering_conventions.csv)")
            elif re.fullmatch(r"\d{3}", parsers.clean_unit(unit)) and c[0] == "building_floor_unit":
                skipped["three digits in a building-floor-unit complex"] += 1
                continue
        if res is None:
            res = read_label(unit)
        if res is None:
            skipped["no clear pattern"] += 1
            continue
        f, name, desc = res
        s = st.get(r.addr_key)
        if s:
            try:
                top = float(s[0])
            except ValueError:
                top = None
            if top is not None and f > math.ceil(top):
                skipped["reading above the building's storeys"] += 1
                above[r.addr_key].append(f)
                continue
            notes.append(f"building has {s[0]} storeys ({s[1]})")
        elif f >= 10 and name in ("floor_then_letter", "house_number_then_floor_letter"):
            # '43L' is floor 43 in a tower but floor 4, apartment 3L in a walk-up: read only against a known height
            skipped["two-digit number + letter with no known building height"] += 1
            continue
        notes.insert(0, desc)
        stated = str(r.floor).strip()
        if stated and re.fullmatch(r"-?\d+(?:\.0)?", stated) and int(float(stated)) != f:
            notes.append(f"CONFLICT: the listing states floor {stated}")
        elif stated and re.fullmatch(r"-?\d+(?:\.0)?", stated):
            notes.append("agrees with the floor the listing states")
        rows.append({"listing_id": r.listing_id, "unit": unit, "floor": f, "basis": FLOOR_BASIS, "convention": name,
                     "notes": "; ".join(notes)})
    write_csv(OUT_FLOORS, FLOOR_COLS, rows)
    print("unit labels not read:", dict(skipped), flush=True)
    return rows, above


def build() -> None:
    rows, _ = build_stories()
    _, above = build_floors(rows)
    # a record that unit labels contradict is flagged where build_master.py will read it
    flagged = 0
    for r in rows:
        fl = above.get(r["addr_key"])
        if fl:
            flagged += 1
            r["notes"] += (f"; CHECK: {len(fl)} unit label(s) here read as floor {min(fl)}"
                           + (f" to {max(fl)}" if max(fl) != min(fl) else "")
                           + f", above the {r['stories']} storeys recorded: the record may predate the building, be "
                             "matched to another lot, or the labels may follow another numbering")
    if flagged:
        write_csv(OUT_STORIES, STORIES_COLS, rows)
    print(f"{flagged} buildings flagged where unit labels read above the recorded storeys", flush=True)


# ---------------------------------------------------------------- main
def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "all"
    if cmd in ("download", "all"):
        download(argv[1:] if cmd == "download" and len(argv) > 1 else None)
    if cmd in ("build", "all"):
        build()


if __name__ == "__main__":
    main(sys.argv[1:])
