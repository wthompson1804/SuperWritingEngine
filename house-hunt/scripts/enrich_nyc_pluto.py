"""NYC building facts from PLUTO (NYC Open Data 64uk-42ks), matched to listings by location.

Downloads every lot with 4+ residential units (bbl, address, class, floors, units, year, owner, lat/lon) into
raw/big/pluto/, then for each NYC listing with coordinates finds the nearest lot within 40 m, preferring an exact
house-number match. Writes data/reference/nyc_building_facts.csv keyed by listings' addr_key:
  pluto_bbl, pluto_address, pluto_class, pluto_floors, pluto_units, pluto_year, pluto_owner, match_m, match_basis,
  elevator_from_class (yes/no/unknown)
Building class -> elevator (NYC Dept of Finance building classification):
  D* elevator apartments -> yes;  C* walk-up apartments -> no;  R4 condo in elevator building -> yes;
  R2/R6 condo walk-up -> no;  H* hotels, RM/others -> unknown;  A*/B* 1-2 family -> no.
"""
import csv, json, math, re, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, RAW, get_json, now_iso

URL = "https://data.cityofnewyork.us/resource/64uk-42ks.json"
SRC = "https://data.cityofnewyork.us/Housing-Development/Primary-Land-Use-Tax-Lot-Output-PLUTO-/64uk-42ks"
COLS = "bbl,address,zipcode,bldgclass,numfloors,unitsres,yearbuilt,ownername,latitude,longitude"


def load_pluto():
    out = RAW / "big" / "pluto" / "pluto_res4plus.csv"
    if out.exists():
        return pd.read_csv(out, dtype=str, keep_default_na=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows, off = [], 0
    while True:
        js, _ = get_json(URL, "pluto_pages", params={"$select": COLS, "$where": "unitsres>=4 AND latitude IS NOT NULL",
                                                    "$order": "bbl", "$limit": 50000, "$offset": off}, timeout=180)
        rows += js
        print(off, len(rows), flush=True)
        if len(js) < 50000:
            break
        off += 50000
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    return pd.read_csv(out, dtype=str, keep_default_na=False)


def elev(cls):
    c = (cls or "").upper()
    if c.startswith("D") or c == "R4" or c in ("RD",):
        return "yes"
    if c.startswith(("C", "A", "B")) or c in ("R2", "R6", "S3", "S4", "S5", "S9"):
        return "no"
    return "unknown"


def housenum(a):
    m = re.match(r"\s*(\d+[- ]?\d*)", str(a))
    return re.sub(r"[^0-9]", "", m.group(1)) if m else ""


def main():
    p = load_pluto()
    p["lat"] = p.latitude.astype(float); p["lon"] = p.longitude.astype(float)
    p["hn"] = p.address.map(housenum)
    # grid index, ~55 m cells
    cell = lambda la, lo: (int(la * 2000), int(lo * 2000))
    idx = {}
    for i, (la, lo) in enumerate(zip(p.lat, p.lon)):
        idx.setdefault(cell(la, lo), []).append(i)
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    L = L[(L.state == "NY") & (L.lat != "") & (L.zip5.str[:3].isin(["100", "101", "102", "103", "104", "110", "111", "112", "113", "114", "116"]))]
    B = L.drop_duplicates("addr_key")
    rows = []
    for _, r in B.iterrows():
        try:
            la, lo = float(r.lat), float(r.lon)
        except ValueError:
            continue
        c = cell(la, lo); best = None
        hn = housenum(r.address)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in idx.get((c[0] + dx, c[1] + dy), []):
                    d = math.hypot((p.lat[i] - la) * 111320, (p.lon[i] - lo) * 111320 * math.cos(math.radians(la)))
                    same = hn != "" and p.hn[i] == hn
                    key = (0 if same else 1, d)
                    if d <= (80 if same else 40) and (best is None or key < best[0]):
                        best = (key, i, d, same)
        if best is None:
            rows.append({"addr_key": r.addr_key, "match_basis": "no_lot_within_40m"}); continue
        i, d, same = best[1], best[2], best[3]
        rows.append({"addr_key": r.addr_key, "pluto_bbl": p.bbl[i].split(".")[0], "pluto_address": p.address[i],
                     "pluto_class": p.bldgclass[i], "pluto_floors": p.numfloors[i].split(".")[0],
                     "pluto_units": p.unitsres[i], "pluto_year": p.yearbuilt[i], "pluto_owner": p.ownername[i],
                     "match_m": round(d), "match_basis": "house_number+location" if same else "nearest_lot",
                     "elevator_from_class": elev(p.bldgclass[i]), "source_url": SRC, "retrieved_at": now_iso()})
    out = pd.DataFrame(rows)
    out.to_csv(DATA / "reference" / "nyc_building_facts.csv", index=False)
    print(len(B), "NYC buildings;", out.match_basis.value_counts().to_dict())
    print(out.elevator_from_class.value_counts(dropna=False).to_dict())


if __name__ == "__main__":
    main()
