"""Load every top-level CSV in data/ into data/house_hunt.sqlite (one table per file). Rebuilds from scratch."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA  # noqa: E402


def main():
    db = DATA / "house_hunt.sqlite"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    for p in sorted(DATA.glob("*.csv")):
        if p.stem.endswith("_problems"):
            continue
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        df.to_sql(p.stem, con, index=False)
        print(f"{p.stem}: {len(df)} rows")
    if (DATA / "area_metrics.csv").exists():
        con.execute("CREATE INDEX ix_am ON area_metrics(area_id, domain, metric)")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
