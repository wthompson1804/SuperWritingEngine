"""One command for the whole pipeline, in a fixed order, with a stage report (plan v4, Part 7).

  python3 scripts/run_all.py            full run (lookup tools are cached; new buildings take about 2 s each)
  python3 scripts/run_all.py --fast     skip the neighborhood / lifestyle rebuild (use after evidence-only changes)
Tests run first, the registry and shown-list assertions last. The text check (scripts/check_scene_text.py) is NOT part of
this run: it is a separate step after scripts/page_data_extras.py.
Writes docs/RUN_REPORT.md: counts in and out of every stage with the reasons, fill rates among shown units, and the
change from the previous run (data/reference/run_history.csv).
"""
import subprocess, sys, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT

TESTS = [("parser tests (every example in docs/INDEPENDENT_CHECK.md)", "test_parsers.py"),
         ("rule tests (every repaired defect and rule, pure)", "test_rules.py")]
FULL = [("gates (merge, dedupe, gate each listing)", "gates.py"), ("NYC building class (PLUTO)", "enrich_nyc_pluto.py"), ("gates again with PLUTO", "gates.py"),
        ("lookup tools per building", "enrich_units.py"), ("neighborhood assignment", "build_neighborhoods.py"),
        ("lifestyle features", "lifestyle_features.py"), ("lifestyle colour", "lifestyle_color.py"), ("crime benchmarks", "crime_benchmarks.py"),
        ("lifestyle groups (saved centres)", "lifestyle_groups.py")]
ALWAYS = [("building amenities (cached pages)", "building_amenities.py --no-fetch"), ("master tables", "build_master.py"), ("rent terms", "rent_terms.py"),
          ("all-in cost", "all_in.py"), ("evidence rules (avoid, exclusions)", "avoid.py"), ("ranking and selection", "rank.py"),
          ("rule tests on the output", "test_rules.py --data"),
          ("field registry, wiring check, shown-list assertions and the review rule", "check_registry.py")]


def run(label, cmd, log):
    r = subprocess.run([sys.executable] + [str(ROOT / "scripts" / cmd.split()[0])] + cmd.split()[1:], capture_output=True, text=True, cwd=ROOT)
    tail = [l for l in (r.stdout + r.stderr).splitlines() if l.strip() and "Warning" not in l and "frame" not in l][-6:]
    log.append((label, cmd, r.returncode, tail))
    print(f"[{'ok' if r.returncode == 0 else 'FAIL ' + str(r.returncode)}] {label}")
    return r.returncode


def main():
    log = []
    steps = TESTS + (FULL if "--fast" not in sys.argv else []) + ALWAYS
    failed = False
    for label, cmd in steps:
        rc = run(label, cmd, log)
        failed = failed or rc != 0
        if rc != 0 and "check_registry" not in cmd and "--data" not in cmd:
            break
    L = pd.read_csv(DATA / "listings.csv", dtype=str, keep_default_na=False, low_memory=False)
    M = pd.read_csv(DATA / "master_units.csv", low_memory=False)
    R = pd.read_csv(DATA / "ranked_units.csv", low_memory=False)
    stage = [("listings harvested (after dedupe)", len(L)), ("pass every listing gate", int((L.gate_status == "pass").sum())),
             ("  pending: a gate fact is unstated", int((L.gate_status == "pending").sum())), ("  fail a gate", int((L.gate_status == "fail").sum())),
             ("costed in the master table", len(M)), ("within the $3,000 all-in cap", int((M.cost_gate == "pass").sum())),
             ("ranked (after safety rule, confirmed-fact gates, sketchy and evidence exclusions)", len(R)),
             ("shown (real apartments, at most one open item, up to 8 per building, after the thin-neighborhood rule)", int(R.shown.sum())),
             ("  neighborhoods shown", int(R[R.shown].hood_id.nunique())), ("  buildings shown", int(R[R.shown].building_id.nunique())),
             ("not an apartment: floor plan, building price or co-living room (data/excluded_not_an_apartment.csv)", len(pd.read_csv(DATA / "excluded_not_an_apartment.csv", usecols=["listing_id"])) if (DATA / "excluded_not_an_apartment.csv").exists() else 0),
             ("no apartment number from any source (data/excluded_no_apartment_number.csv)", len(pd.read_csv(DATA / "excluded_no_apartment_number.csv", usecols=["listing_id"])) if (DATA / "excluded_no_apartment_number.csv").exists() else 0),
             ("thin neighborhoods cut (one apartment, not both well attested and promising)", int(R.thin_neighborhood.sum()) if "thin_neighborhood" in R else 0),
             ("avoid cards", int(R.avoid_card.sum())),
             ("  shown with an asterisk (one thing to confirm)", int((R.shown & (R.confirm_asterisk == "yes")).sum()) if "confirm_asterisk" in R else 0),
             ("removed by a reviewed verdict (data/evidence/review_verdicts.csv)", len(pd.read_csv(DATA / "excluded_by_review.csv", usecols=["listing_id"])) if (DATA / "excluded_by_review.csv").exists() else 0),
             ("held back for one confirmation", int(R.held_for_confirmation.sum()) if "held_for_confirmation" in R else 0),
             ("neighborhoods with 3+ shown places", int((R[R.shown].groupby("hood_id").size() >= 3).sum())),
             ("buildings in the master table", M.building_id.nunique())]
    drops = []
    for f, why in [("excluded_by_confirmed_facts.csv", "drop_reason"), ("excluded_sketchy.csv", "sketchy_reason")]:
        if (DATA / f).exists():
            d = pd.read_csv(DATA / f, low_memory=False)
            drops.append((f, d[why].astype(str).str.split("; ").explode().str.strip().replace("", pd.NA).dropna().value_counts().head(8).to_dict()))
    S = R[R.shown]
    fill_cols = ["sqft", "unit_floor", "elevator_basis", "dog_weight_limit_lb", "parking_type", "parking_fee", "pet_rent", "pool", "doorman", "year_built",
                 "toll_rt_ezpass", "transit_sat_median", "near_violent_250m_24m", "live_status", "rent_first_full_payment_date", "ev_pause_notes"]
    fill = {c: round(float(S[c].notna().mean() if c in S else 0) * 100) for c in fill_cols}
    hist = DATA / "reference" / "run_history.csv"
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    row = {"run_at": now, **{k.strip(): v for k, v in stage}}
    H = pd.concat([pd.read_csv(hist), pd.DataFrame([row])]) if hist.exists() else pd.DataFrame([row])
    H.to_csv(hist, index=False)
    prev = H.iloc[-2].to_dict() if len(H) > 1 else {}
    md = [f"# Run report ({now})", "", "## Steps", "", "| Step | Script | Result |", "|---|---|---|"]
    md += [f"| {l} | `{c}` | {'ok' if rc == 0 else 'FAILED'} |" for l, c, rc, _ in log]
    md += ["", "## Stage counts", "", "| Stage | Now | Previous run | Change |", "|---|---|---|---|"]
    for k, v in stage:
        p = prev.get(k.strip())
        p = None if p is None or pd.isna(p) else p
        md.append(f"| {k} | {v} | {'' if p is None or pd.isna(p) else int(p)} | {'' if p is None or pd.isna(p) else f'{v - int(p):+d}'} |")
    md += ["", "## Why units left", ""]
    for f, d in drops:
        md += [f"**{f}**", ""] + [f"- {k}: {v}" for k, v in d.items()] + [""]
    md += ["## Shown units by year", "", R.groupby("group_label").agg(neighborhoods=("hood_id", "nunique"), ranked=("listing_id", "count"), shown=("shown", "sum"), avoid_cards=("avoid_card", "sum")).to_markdown(), "",
           "## Fill rate among shown units (percent with a value)", "", "| Field | % |", "|---|---|"] + [f"| {k} | {v} |" for k, v in fill.items()]
    md += ["", "## Last lines of each step", ""]
    for l, c, rc, tail in log:
        md += [f"**{l}**", "```"] + tail + ["```", ""]
    (ROOT / "docs" / "RUN_REPORT.md").write_text("\n".join(md) + "\n")
    print("\n".join(f"{k:85s} {v}" for k, v in stage))
    if failed:
        print("RUN FAILED: see docs/RUN_REPORT.md (a step returned an error, or a shown unit breaks a rule)")
        sys.exit(1)


if __name__ == "__main__":
    main()
