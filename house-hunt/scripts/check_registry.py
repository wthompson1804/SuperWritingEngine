"""Field registry and wiring check (plan v4, Part 2). Runs first in scripts/run_all.py.

Builds data/reference/field_registry.csv: every column of the master tables and every evidence family, with the
scripts that reference it and a status:
  used          referenced by a gate, cost, ranking, avoid or grouping script
  provenance    <field>_basis / <field>_source / URL / timestamp columns that travel with a used field
  display       shown on the page or kept for the reader, not scored (listed in DISPLAY, with the reason)
  not_used      deliberately unused (listed in NOT_USED, with the reason)
  UNACCOUNTED   collected, referenced nowhere and not explained -> the check fails
It also fails if an analysis script reads a side file directly instead of the master tables.
"""
import glob, re, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT

ANALYSIS = ["all_in.py", "rank.py"]                      # must read only the master tables (+ group / evidence-rule outputs)
ALLOWED_INPUTS = {"master_units.csv", "master_buildings.csv", "lifestyle_groups.csv", "unit_exclusions.csv", "avoid_buildings.csv",
                  "rent_terms.csv", "building_crosswalk.csv", "lifestyle_color.csv"}
USERS = ["gates.py", "build_master.py", "all_in.py", "rank.py", "avoid.py", "build_neighborhoods.py", "lifestyle_features.py",
         "lifestyle_color.py", "lifestyle_groups.py", "crime_benchmarks.py", "rent_terms.py", "rating_standard.py", "enrich_units.py"]
DISPLAY = {  # pattern -> why it is kept but not scored
    r"^(photo_url|url|building_url|also_seen_at|listing_url|building_site_url)$": "link shown on the page",
    r"^(building_name|address|city|state|zip5|unit|baths|hood|hood_area|manager|park_name|dog_park_name|supermarket|train_station|police_agency|police_geography|unit_count)$": "label shown on the page",
    r"^(dog_policy_text|required_fees_text|lease_terms_text|pet_one_time_fee_text|concession_text.*|rent_regulation|listing_warning|live_notes|live_available_text|available_date_text|transit_summary|transit_sat_summary|toll_items|all_in_lines|all_in_unknown_lines|all_in_estimated_lines)$": "text shown on the unit card or cost receipt",
    r"^rent_(offer_text|free_months|lease_months|first_full_payment_date|first_full_payment_note|needs_call|listed_price_is|gross|basis_kind|asterisk)$": "rent terms shown beside the asterisk",
    r"^(excerpt|quote|item_date|about|category|building_site|detail)$": "evidence text shown on avoid and pause cards",
    r"^(near_vs_baseline|crime_latest|crime_source|crime_year|nyc_record_flags)$": "context shown when she asks how a score was reached",
    r"^nycrec_": "NYC record counts by period: shown in the building's record summary; flags derived from them drive the avoid rule",
    r"^near250_.*_(2023|2025|borough_median|above_borough_p80)$": "context for the nearby-crime figures",
    r"^agency_(property|burglary)_per_1000_": "area context shown beside the violent-crime trend",
    r"^(toll_known_subtotal|toll_complete|drive_min_from|drive_miles|transit_sat_fastest|transit_status|transit_sun_return_fastest|last_sat_departure|util_1br|util_studio|util_1br_complete|coast_m|beach_m|park_ha_800m)$": "figure shown in a scene or receipt",
}
NOT_USED = {
    r"^(first_seen|last_seen|detail_level|raw_path|notes|listing_type|price_basis|gate_status|g_floor|floor|floor_used|stale_listing|addr_key|addr_keys|street_key|n_listed_units|other_monthly_fees_json|live_checked_at|checked_at|retrieved_at|matches_stored|_file|batch|status|fact|value|unit_floor_source|pluto_.*|lat|lon|live_price)$": "bookkeeping or already folded into a merged field",
    r"^(income_requirement|building_type)$": "used only as a hard exclusion",
    r"^(rating_|review_count|reviews_|negative_|serious_issue_tags|as_of_date)": "ratings: used by scripts/rating_standard.py for the outside-NYC standard, not by the ranking",
    r"^(bbl|bin|units_in_building|caution|baseline_.*|above_p95|per_100_units|metric|period|count|query_url|flag|match_basis|record_type)$": "NYC records detail behind the flags",
}


def main():
    code = {s: (ROOT / "scripts" / s).read_text() for s in USERS if (ROOT / "scripts" / s).exists()}
    rows, bad = [], []
    tables = {"master_units": DATA / "master_units.csv", "master_buildings": DATA / "master_buildings.csv"}
    for fam in ["items", "facts", "confirm", "live_check", "ratings"]:
        fs = sorted(glob.glob(str(DATA / "evidence" / f"{fam}_batch_*.csv")))
        if fs:
            tables["evidence:" + fam] = Path(fs[0])
    for name, extra in [("evidence:nyc_records_flags", DATA / "evidence" / "nyc_records_flags.csv"), ("evidence:rating_standard", DATA / "evidence" / "rating_standard.csv"),
                        ("rent_terms", DATA / "rent_terms.csv")]:
        if extra.exists():
            tables[name] = extra
    for t, p in tables.items():
        if not p.exists():
            continue
        for c in pd.read_csv(p, nrows=0).columns:
            base = re.sub(r"_(basis|source)$", "", c)
            refs = [s for s, txt in code.items() if re.search(r"[\"'.]" + re.escape(c) + r"\b", txt) or (c.startswith("near250_") and "near250_" in txt)
                    or (c.startswith("agency_violent") and "agency_violent" in txt)]
            status, why = "", ""
            if refs and (t.startswith("evidence") or not (len(refs) == 1 and refs[0] == "build_master.py")):
                status = "used"
            elif c != base:
                status, why = "provenance", f"travels with {base}"
            else:
                for pats, st in ((DISPLAY, "display"), (NOT_USED, "not_used")):
                    for pat, reason in pats.items():
                        if re.search(pat, c):
                            status, why = st, reason
                            break
                    if status:
                        break
            if not status:
                status = "UNACCOUNTED"; bad.append(f"{t}.{c}")
            rows.append({"table": t, "field": c, "status": status, "referenced_by": ";".join(refs), "note": why})
    pd.DataFrame(rows).to_csv(DATA / "reference" / "field_registry.csv", index=False)
    wiring = []
    for s in ANALYSIS:
        txt = (ROOT / "scripts" / s).read_text()
        for m in re.finditer(r"[\"']([\w./-]+\.csv)[\"']", txt):
            f = Path(m.group(1)).name
            line = txt[:m.start()].count("\n") + 1
            ctx = txt[txt.rfind("\n", 0, m.start()):txt.find("\n", m.end())]
            if "read_csv" in ctx or ".exists()" in ctx or "= DATA" in ctx:
                if f not in ALLOWED_INPUTS and "to_csv" not in ctx and not re.search(r"excluded|needs_confirmation|ranked_units|group_exchange|queens_spectrum", f):
                    wiring.append(f"{s}:{line} reads {f}")
    st = pd.DataFrame(rows).status.value_counts().to_dict()
    print("field registry:", st)
    if bad:
        print("UNACCOUNTED fields (collected, used nowhere, not explained):"); [print("  ", b) for b in bad]
    if wiring:
        print("Scripts reading side files instead of the master:"); [print("  ", w) for w in wiring]
    return 1 if (bad or wiring) else 0


if __name__ == "__main__":
    sys.exit(main())
