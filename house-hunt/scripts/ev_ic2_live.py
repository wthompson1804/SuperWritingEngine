"""Live-check rows from the second independent check's own page fetches (docs/INDEPENDENT_CHECK_2.md, D15).

The checker fetched 8 Apartment List and 2 Zumper pages at 23:21 UTC on 2026-11-15 and recorded what each page showed
in data/evidence/independent_check_2_units.csv. Where the rent on the page differed from the master (Avalon Teaneck
001-215: $2,521 against $2,516; Avalon Maplewood 001-324: $2,590 against $2,600), that reading is a later live check.
This script writes those readings as data/evidence/live_check_batch_ic2.csv so the pipeline uses them like any other
live-check row. The earlier check's note is kept inside the new note (it carries lease-term and fee findings).
No page is fetched here. Idempotent: the file is rebuilt from the two inputs each time.
"""
import glob
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA  # noqa: E402
import parsers  # noqa: E402

OUT = DATA / "evidence" / "live_check_batch_ic2.csv"
COLS = ["addr_key", "listing_url", "unit", "status", "price_now", "available_now_text", "matches_stored", "building_site_url", "checked_at", "notes"]


def main():
    IC = pd.read_csv(DATA / "evidence" / "independent_check_2_units.csv", dtype=str, keep_default_na=False)
    M = pd.read_csv(DATA / "master_units.csv", dtype=str, keep_default_na=False, low_memory=False, usecols=["listing_id", "addr_key", "building_id", "unit"]).set_index("listing_id")
    L = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in sorted(glob.glob(str(DATA / "evidence" / "live_check_batch_*.csv"))) if not f.endswith("_ic2.csv")], ignore_index=True)
    xw = pd.read_csv(DATA / "reference" / "building_crosswalk.csv", dtype=str).set_index("addr_key").building_id
    L["building_id"] = L.addr_key.map(xw)
    rows = []
    rent = IC[(IC.field == "rent") & (IC.verdict == "disagree") & ~IC.source_url.str.contains("trulia")]
    for r in rent.itertuples():
        if r.listing_id not in M.index:
            continue
        m = M.loc[r.listing_id]
        prev = L[(L.building_id == m.building_id) & L.unit.map(lambda x: parsers.units_match(x, m.unit))].sort_values("checked_at")
        av = IC[(IC.listing_id == r.listing_id) & (IC.field == "availability_date")]
        old = prev.iloc[-1] if len(prev) else None
        price = str(int(float(r.source_value)))
        rows.append({"addr_key": m.addr_key, "listing_url": r.source_url, "unit": m.unit, "status": "changed", "price_now": price,
                     "available_now_text": av.source_value.iloc[0] if len(av) else "", "matches_stored": "no",
                     "building_site_url": old.building_site_url if old is not None else "", "checked_at": r.checked_at,
                     "notes": f"Independent check 2 fetched the listing page at {r.checked_at}: unit {m.unit} now ${int(price):,}. {r.note}."
                              + (f" Earlier live check ({old.checked_at}): {old.notes}" if old is not None else "")})
    pd.DataFrame(rows, columns=COLS).to_csv(OUT, index=False)
    print(f"{OUT.name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
