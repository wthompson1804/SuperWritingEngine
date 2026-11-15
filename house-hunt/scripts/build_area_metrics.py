"""Merge data/metrics/*.csv into data/area_metrics.csv, validate, and write a coverage summary.

Validation (problems are written to data/area_metrics_problems.csv, not silently fixed):
  - exact column set and order
  - area_id exists in areas.csv
  - value_type in {found, estimate, not_found}
  - found/estimate rows have a value and a source_url; not_found rows have notes
  - estimate rows have a method
  - duplicate (area_id, metric, source, geography, period) keys
Coverage: docs/COVERAGE_PHASE1.md, area x domain counts by value_type.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT  # noqa: E402

COLS = ["area_id", "domain", "metric", "value", "unit", "geography", "period", "source", "source_url",
        "retrieved_at", "raw_path", "value_type", "method", "population_used", "notes"]
KEY = ["area_id", "metric", "source", "geography", "period"]


def main():
    areas = pd.read_csv(DATA / "areas.csv", dtype=str)
    frames, problems = [], []
    for p in sorted((DATA / "metrics").glob("*.csv")):
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        if list(df.columns) != COLS:
            missing = [c for c in COLS if c not in df.columns]
            extra = [c for c in df.columns if c not in COLS]
            problems.append({"file": p.name, "row": "", "problem": f"columns differ; missing={missing} extra={extra}"})
            for c in missing:
                df[c] = ""
            df = df[COLS]
        df.insert(0, "_file", p.name)
        df.insert(1, "_row", range(2, len(df) + 2))
        frames.append(df)
    if not frames:
        print("no metric files yet")
        return
    m = pd.concat(frames, ignore_index=True)

    def flag(mask, msg):
        for _, r in m[mask].iterrows():
            problems.append({"file": r["_file"], "row": r["_row"], "problem": msg})

    flag(~m.area_id.isin(areas.id), "unknown area_id")
    flag(~m.value_type.isin(["found", "estimate", "not_found"]), "bad value_type")
    has_val = m.value_type.isin(["found", "estimate"])
    flag(has_val & (m.value.str.strip() == ""), "found/estimate without value")
    flag(has_val & (m.source_url.str.strip() == ""), "found/estimate without source_url")
    flag((m.value_type == "not_found") & (m.notes.str.strip() == ""), "not_found without notes")
    flag((m.value_type == "estimate") & (m.method.str.strip() == ""), "estimate without method")
    dup = m.duplicated(KEY, keep=False)
    flag(dup, "duplicate key " + "+".join(KEY))

    out = m.drop(columns=["_file", "_row"]).drop_duplicates(KEY, keep="first")
    out.to_csv(DATA / "area_metrics.csv", index=False)
    pd.DataFrame(problems, columns=["file", "row", "problem"]).to_csv(DATA / "area_metrics_problems.csv", index=False)

    # coverage
    cov = out.groupby(["area_id", "domain", "value_type"]).size().unstack(fill_value=0)
    lines = ["# Phase 1 coverage", "",
             f"Rows: {len(out)} from {len(frames)} files. Validation problems: {len(problems)} "
             "(see `data/area_metrics_problems.csv`).", "",
             "## Rows by domain and value_type", "",
             out.groupby(["domain", "value_type"]).size().unstack(fill_value=0).to_markdown(), "",
             "## Distinct metrics by domain", ""]
    for d, g in out.groupby("domain"):
        lines.append(f"- **{d}** ({g.metric.nunique()}): " + ", ".join(sorted(g.metric.unique())))
    lines += ["", "## Areas: share of metric rows found or estimate, by domain", ""]
    share = out.assign(ok=out.value_type.isin(["found", "estimate"])).pivot_table(
        index="area_id", columns="domain", values="ok", aggfunc="mean")
    share = (share * 100).round(0).astype("Int64")
    share = share.reindex(areas.id)
    lines.append(share.to_markdown())
    missing_areas = sorted(set(areas.id) - set(out.area_id))
    if missing_areas:
        lines += ["", f"Areas with no rows at all: {', '.join(missing_areas)}"]
    (ROOT / "docs" / "COVERAGE_PHASE1.md").write_text("\n".join(lines) + "\n")
    print(f"{len(out)} rows, {len(problems)} problems")
    print(out.groupby(["domain", "value_type"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
