"""One-time costs a listing's own page states: broker fee (or 'no broker fee'), application / administrative / holding /
move-in fees, a security deposit (independent check 5, N4: 525 Riverdale Ave 5U says "Broker fee." and the page did not).

for_raw_paths(paths) reads each cached listing page once (the listing's own description only: parsers.listing_descriptions),
and returns {raw_path: {broker, broker_quote, items, deposit_months, deposit_dollars, deposit_text}}. Results are kept in
data/reference/listing_fee_statements.csv keyed on the raw path and the file's size, so a rerun reads no page again.
Nothing is fetched. A statement on a building's page applies to every apartment listed on that page.
"""
import html
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import DATA, ROOT  # noqa: E402
import parsers  # noqa: E402

OUT = DATA / "reference" / "listing_fee_statements.csv"
COLS = ["raw_path", "bytes", "broker", "broker_quote", "items", "deposit_months", "deposit_dollars", "deposit_up_to", "deposit_text"]


def read_one(raw_path):
    p = ROOT / str(raw_path)
    row = {c: "" for c in COLS}
    row["raw_path"] = str(raw_path)
    if not p.is_file():
        return row
    row["bytes"] = p.stat().st_size
    desc = parsers.listing_descriptions(html.unescape(p.read_text(errors="ignore")))
    kind, quote = parsers.broker_fee_statement(desc)
    otc = parsers.one_time_costs(desc)
    row.update(broker=kind, broker_quote=quote, items="; ".join(otc["items"]), deposit_months=otc["deposit_months"] or "",
               deposit_dollars=otc["deposit_dollars"] or "", deposit_up_to="yes" if otc["deposit_up_to"] else "", deposit_text=otc["deposit_text"])
    return row


def for_raw_paths(paths):
    paths = sorted({str(p) for p in paths if str(p).strip() and str(p) != "nan"})
    old = pd.read_csv(OUT, dtype=str, keep_default_na=False) if OUT.exists() else pd.DataFrame(columns=COLS)
    have = {r["raw_path"]: r for r in old.to_dict("records")}
    rows = []
    for p in paths:
        f = ROOT / p
        size = str(f.stat().st_size) if f.is_file() else ""
        r = have.get(p)
        rows.append(r if r is not None and str(r.get("bytes", "")) == size else {k: str(v) for k, v in read_one(p).items()})
    df = pd.DataFrame(rows, columns=COLS).sort_values("raw_path")
    if not (len(df) == len(old) and df.astype(str).reset_index(drop=True).equals(old.astype(str).sort_values("raw_path").reset_index(drop=True))):
        df.to_csv(OUT, index=False)
    return {r["raw_path"]: r for r in df.to_dict("records")}


if __name__ == "__main__":
    M = pd.read_csv(DATA / "master_units.csv", usecols=["raw_path"], dtype=str, keep_default_na=False)
    if "--rebuild" in sys.argv and OUT.exists():
        OUT.unlink()
    res = for_raw_paths(M.raw_path)
    print(len(res), "pages;", sum(1 for r in res.values() if r["broker"] == "applies"), "say a broker fee applies;",
          sum(1 for r in res.values() if r["broker"] == "none"), "say no broker fee;", sum(1 for r in res.values() if r["items"]), "state one-time fees")
