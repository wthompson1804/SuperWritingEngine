"""Trawl 2, step 2 ("Trulia cards"): find the same building on a source we can read, with no network.

Trulia search cards (detail_level card) cannot be opened (Trulia is closed to us). For every card at or under $2,000
in the priority areas (New Jersey, Connecticut, Brooklyn, Long Island = Nassau/Suffolk, Long Island City), look for a
row already held from a readable source in the same building:

  1. the same normalized street key (build_master.street_key: house number + street + ZIP, unit stripped);
  2. the same building through build_master.assign_building_ids (street key, then same house number within 30 m,
     then house-number ranges) run over cards + readable rows together;
  3. the same building_id through data/reference/building_crosswalk.csv.

Readable rows: data/listings.csv, data/listings_raw/*.csv and data/listings_pending/zumper_opened.csv, any source that
is not Trulia, Zillow, Craigslist or another off-limits listing site. Writes
data/reference/trulia_card_matches.csv (offline rows: method street_key / building_id / crosswalk; a same unit label
and bed count on the sibling is method *_same_unit) and data/reference/trulia_card_unmatched_priority.csv (the ranked
list for the building-site search). Idempotent: rows with a non-offline method (building_site*, no_site_found ...)
already in the matches file are kept.
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_master as bm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "reference" / "trulia_card_matches.csv"
UNM = DATA / "reference" / "trulia_card_unmatched_priority.csv"
OFFLIMITS = ("trulia", "zillow", "craigslist", "streeteasy", "apartments.com", "realtor.com", "rent.com", "hotpads",
             "renthop", "rentcafe", "securecafe", "appfolio", "realtymx", "prospectportal")
OFFLINE_METHODS = {"street_key", "building_id", "crosswalk", "street_key_same_unit", "building_id_same_unit",
                   "crosswalk_same_unit"}
COLS = ["trulia_listing_id", "area", "address", "zip", "unit", "beds", "listed_rent", "matched_listing_ids",
        "building_site_url", "method", "notes"]

LIC = {"11101", "11109", "11120"}


def area(state, zip5):
    z = str(zip5)[:5]
    if state == "NJ":
        return "New Jersey"
    if state == "CT":
        return "Connecticut"
    if state != "NY" or not z.isdigit():
        return ""
    if z.startswith("112"):
        return "Brooklyn"
    if z in LIC:
        return "Long Island City"
    n = int(z)
    if (11001 <= n <= 11099 and z not in {"11004", "11005"}) or 11501 <= n <= 11599 or 11701 <= n <= 11999 \
            or 11801 <= n <= 11899:
        return "Long Island"
    return ""


def unit_norm(u):
    return re.sub(r"[^0-9a-z]", "", str(u).lower().replace("apt", "").replace("unit", ""))


def load_readable():
    frames = []
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    frames.append(L[bm_cols(L)])
    for f in sorted(glob.glob(str(DATA / "listings_raw" / "*.csv"))) + [str(DATA / "listings_pending" / "zumper_opened.csv")]:
        if Path(f).exists():
            d = pd.read_csv(f, dtype=str, keep_default_na=False)
            if len(d):
                frames.append(d[bm_cols(d)].assign(_file=Path(f).name))
    R = pd.concat(frames, ignore_index=True)
    R = R[~R.source_site.str.lower().str.contains("|".join(OFFLIMITS))]
    R = R[~R.url.str.lower().str.contains("|".join(OFFLIMITS))]
    R = R.drop_duplicates("listing_id", keep="first")
    return R


def bm_cols(d):
    want = ["listing_id", "source_site", "url", "detail_level", "address", "zip", "lat", "lon", "unit", "beds",
            "listed_rent", "last_seen", "state", "city"]
    return [c for c in want if c in d.columns]


def main():
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False)
    t = L[L.source_site.str.contains("trulia", case=False) & (L.detail_level == "card")].copy()
    t["r"] = pd.to_numeric(t.listed_rent, errors="coerce")
    t = t[t.r <= 2000]
    t["area"] = [area(s, z) for s, z in zip(t.state, t.zip5)]
    n_all = len(t)
    t = t[t.area != ""].copy()
    R = load_readable()
    R["zip5"] = R.zip.str[:5]
    R["r"] = pd.to_numeric(R.listed_rent, errors="coerce")
    print(f"cards <=2000: {n_all}; in priority areas: {len(t)}; readable rows: {len(R)}")

    # Building ids over cards + readable rows together.
    U = pd.concat([t[["listing_id", "address", "zip5", "lat", "lon"]].assign(_k="card"),
                   R[["listing_id", "address", "zip5", "lat", "lon"]].assign(_k="read")], ignore_index=True)
    U = U[U.address.str.strip() != ""]
    U = bm.assign_building_ids(U)
    bid = dict(zip(U.listing_id + "|" + U._k, U.building_id))
    sk = dict(zip(U.listing_id + "|" + U._k, U.street_key))
    xw = pd.read_csv(DATA / "reference" / "building_crosswalk.csv", dtype=str, keep_default_na=False)
    xw_b = dict(zip(xw.addr_key, xw.building_id))
    xw_b.update(dict(zip(xw.street_key, xw.building_id)))

    R["street_key"] = [sk.get(i + "|read", "") for i in R.listing_id]
    R["bid"] = [bid.get(i + "|read", "") for i in R.listing_id]
    R["xb"] = [xw_b.get(k, "") for k in R.street_key]
    by_sk = {k: g for k, g in R[R.street_key.str.match(r"^\d")].groupby("street_key")}
    by_bid = {k: g for k, g in R[R.street_key.str.match(r"^\d")].groupby("bid")}
    by_xb = {k: g for k, g in R[R.xb != ""].groupby("xb")}

    rows = []
    for c in t.itertuples():
        k = sk.get(c.listing_id + "|card", "")
        hit, method = None, ""
        if k and re.match(r"^\d", k):
            if k in by_sk:
                hit, method = by_sk[k], "street_key"
            elif bid.get(c.listing_id + "|card", "") in by_bid:
                hit, method = by_bid[bid[c.listing_id + "|card"]], "building_id"
            elif xw_b.get(k) and xw_b[k] in by_xb:
                hit, method = by_xb[xw_b[k]], "crosswalk"
        base = dict(trulia_listing_id=c.listing_id, area=c.area, address=c.address, zip=c.zip5, unit=c.unit,
                    beds=c.beds, listed_rent=c.listed_rent, building_site_url="")
        if hit is None:
            rows.append({**base, "matched_listing_ids": "", "method": "unmatched_offline",
                         "notes": "no address on card" if not re.match(r"^\d", k or "") else "no readable row in the building"})
            continue
        same = hit[(hit.unit.map(unit_norm) == unit_norm(c.unit)) & (hit.unit.map(unit_norm) != "") &
                   (hit.beds == c.beds)]
        if len(same):
            method += "_same_unit"
        sib = hit.sort_values("r")
        le = sib[sib.r <= 2200]
        sites = ", ".join(sorted(set(sib.source_site)))
        rows.append({**base, "matched_listing_ids": ";".join((same if len(same) else sib).listing_id.tolist()[:20]),
                     "method": method,
                     "notes": f"{len(sib)} readable rows in the building ({sites}); {len(le)} at or under $2,200"
                              + (f"; same unit label on {';'.join(same.listing_id.tolist()[:5])}" if len(same) else "")})
    M = pd.DataFrame(rows, columns=COLS)
    if OUT.exists():
        old = pd.read_csv(OUT, dtype=str, keep_default_na=False)
        keep = old[~old.method.isin(OFFLINE_METHODS | {"unmatched_offline"})]
        M = pd.concat([M[~M.trulia_listing_id.isin(keep.trulia_listing_id)], keep], ignore_index=True)[COLS]
    M.to_csv(OUT, index=False)

    m = M[M.method.isin(OFFLINE_METHODS)]
    print("matched offline:", len(m), "of", len(M))
    print(M.groupby(["area", "method"]).size().to_string())

    # Ranked unmatched list for the web search: studio/1BR first, cheaper first, grouped by building.
    un = t[t.listing_id.isin(M[M.method == "unmatched_offline"].trulia_listing_id)].copy()
    un["street_key"] = [sk.get(i + "|card", "") for i in un.listing_id]
    un = un[un.street_key.str.match(r"^\d")]
    un["b01"] = un.beds.isin(["0", "1"])
    g = un.groupby("street_key").agg(cards=("listing_id", "count"), ids=("listing_id", lambda s: ";".join(s)),
                                     address=("address", "first"), city=("city", "first"), state=("state", "first"),
                                     zip=("zip5", "first"), area=("area", "first"), building_name=("building_name", "first"),
                                     min_rent=("r", "min"), n01=("b01", "sum")).reset_index()
    g = g.sort_values(["n01", "cards", "min_rent"], ascending=[False, False, True])
    g.to_csv(UNM, index=False)
    print("unmatched buildings with an address:", len(g), "; with >=2 cards:", (g.cards >= 2).sum())


if __name__ == "__main__":
    main()
