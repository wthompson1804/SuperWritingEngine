"""Field registry and wiring check (plan v4, Part 2). Runs first in scripts/run_all.py.

Builds data/reference/field_registry.csv: every column of the master tables and every evidence family, with the
scripts that reference it and a status:
  used          referenced by a gate, cost, ranking, avoid or grouping script
  provenance    <field>_basis / <field>_source / URL / timestamp columns that travel with a used field
  display       shown on the page or kept for the reader, not scored (listed in DISPLAY, with the reason)
  not_used      deliberately unused (listed in NOT_USED, with the reason)
  UNACCOUNTED   collected, referenced nowhere and not explained -> the check fails
It also fails if an analysis script reads a side file directly instead of the master tables.

Shown-list assertions (added after docs/INDEPENDENT_CHECK.md): the run fails when any unit with shown = True in
data/ranked_units.csv breaks one of Will's rules: more than one open item (elevator only inferred; floor unknown or inferred
in a way the floor rule does not accept; dogs conflicting; no live check), or one open item without the asterisk fields
(confirm_asterisk, confirm_what, confirm_why); elevator contradicted; floor under 2; dogs not explicitly allowed, or a weight limit under 25 lb (a size-only "small dogs" policy passes, by the owner's rule of
2026-11-15, but must carry its note and tour question);
all-in over $3,000; available after 2026-12-15; a duplicate unit; more than 2 shown in one building;
a neighborhood cut by the Jamaica safety rule; an avoid building; a harvest note that says BUILDING_FAILS for any reason
other than "small dogs only".
"""
import glob, re, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT

ANALYSIS = ["all_in.py", "rank.py"]                      # must read only the master tables (+ group / evidence-rule outputs)
ALLOWED_INPUTS = {"master_units.csv", "master_buildings.csv", "lifestyle_groups.csv", "unit_exclusions.csv", "avoid_buildings.csv",
                  "rent_terms.csv", "building_crosswalk.csv", "lifestyle_color.csv", "review_verdicts.csv"}
USERS = ["gates.py", "build_master.py", "all_in.py", "rank.py", "avoid.py", "build_neighborhoods.py", "lifestyle_features.py",
         "lifestyle_color.py", "lifestyle_groups.py", "crime_benchmarks.py", "rent_terms.py", "rating_standard.py", "enrich_units.py"]
CAP, WINDOW_END, MAX_PER_BUILDING, MIN_DOG_LB = 3000, "2026-12-15", 2, 25
DISPLAY = {  # pattern -> why it is kept but not scored
    r"^(photo_url|url|building_url|also_seen_at|listing_url|building_site_url)$": "link shown on the page",
    r"^(building_name|address|city|state|zip5|unit|baths|hood|hood_area|manager|park_name|dog_park_name|supermarket|train_station|police_agency|police_geography|unit_count)$": "label shown on the page",
    r"^(dog_policy_text|required_fees_text|lease_terms_text|pet_one_time_fee_text|concession_text.*|rent_regulation|listing_warning|live_notes|live_available_text|available_date_text|transit_summary|transit_sat_summary|toll_items|all_in_lines|all_in_unknown_lines|all_in_estimated_lines)$": "text shown on the unit card or cost receipt",
    r"^rent_(offer_text|free_months|lease_months|first_full_payment_date|first_full_payment_note|needs_call|listed_price_is|gross|basis_kind|asterisk)$": "rent terms shown beside the asterisk",
    r"^(excerpt|quote|item_date|about|category|building_site|detail)$": "evidence text shown on avoid and pause cards",
    r"^(parking_text|optional_fees_text|dog_weight_text|dogs_allowed_note|elevator_note)$": "source sentence kept for display beside the parsed value (shown with an asterisk when the parse is unknown)",
    r"^(duplicate_listing_ids)$": "other listings of the same unit, merged into this row (their links are in also_seen_at)",
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


def shown_violations():
    """Every rule a shown unit must satisfy, checked on the output itself. Returns a list of 'listing: what is wrong'."""
    import parsers
    f = DATA / "ranked_units.csv"
    if not f.exists():
        return []
    R = pd.read_csv(f, low_memory=False, dtype=str, keep_default_na=False)
    S = R[R.shown == "True"].copy()
    if not len(S):
        return []
    out = []

    def flag(mask, why):
        for lid, name, unit in S[mask][["listing_id", "building_name", "unit"]].itertuples(index=False):
            out.append(f"{lid} ({name} {unit}): {why}")
    num = lambda c: pd.to_numeric(S[c], errors="coerce") if c in S else pd.Series(float("nan"), index=S.index)
    col = lambda c: S[c] if c in S else pd.Series("", index=S.index)
    # Owner, 2026-11-15: a shown unit may have at most ONE open item (elevator only inferred; floor unknown or inferred
    # in a way the floor rule does not accept; dogs conflicting; no live check) and must then carry the asterisk fields.
    # A fact that fails outright (no elevator, floor under 2, dogs not allowed) is never shown.
    el = col("elevator").str.lower()
    flag(el.isin(["no", "conflicting"]), "elevator contradicted or conflicting")
    open_e = (el != "yes") | ~col("elevator_basis").isin(["confirmed", "stated", "official_record", "amenities_page", "community_page"]) | (col("elevator_evidence_open") != "")
    fl, fb, fk = num("unit_floor"), col("unit_floor_basis"), col("unit_floor_label_kind")
    flag(fl < 2, "floor under 2")
    open_f = ~(fb.isin(["confirmed", "stated"]) | ((fb == "inferred") & (fk == "simple") & (fl >= 3)))
    dg = col("dogs_allowed").str.lower()
    flag(dg == "no", "dogs not allowed")
    flag((dg == "yes") & ~col("dogs_allowed_basis").isin(["confirmed", "stated", "community_page", "amenities_page"]), "dogs-allowed basis is inferred or unknown")
    open_d = (dg != "yes") | (col("dogs_evidence_open") != "")
    open_l = ~col("live_status").isin(["live", "changed"])
    # independent check 2: lease term over 13 months (D8), cost near the cap with an unknown line (D12), a floor-plan
    # row (D1), an evidence warning about the listing (D6), and whatever a reviewer's asterisk verdict names
    open_lease = (num("price_lease_months") > 13) | (col("price_lowest_of_terms") == "yes")
    open_cost = (num("all_in") >= CAP - 100) & (num("all_in_unknown_count").fillna(0) >= 1)
    open_avail = (S.unit.map(parsers.unit_label_key) == "") & ((col("detail_level") == "building_floorplan") | col("listing_id").str.contains(":plan-") | (S.unit.str.strip() != ""))
    open_listing = col("listing_warning") != ""
    opens = {"elevator": open_e, "floor": open_f, "dogs allowed": open_d, "lease term": open_lease, "cost near the cap": open_cost,
             "availability": open_avail, "listing": open_listing, "eligibility": open_e & False, "condo rules": open_e & False, "other": open_e & False}
    import verdicts
    V = verdicts.load_verdicts().drop_duplicates("listing_id", keep="last").set_index("listing_id")
    KIND_LABEL = {"elevator": "elevator", "floor": "floor", "dogs": "dogs allowed", "lease_term": "lease term", "not_available": "availability", "unverified": "listing",
                  "wrong_building": "listing", "restricted": "eligibility", "coop_condo": "condo rules", "other": "other"}
    vlab = S.listing_id.map(lambda l: KIND_LABEL.get(V.at[l, "kind"], "") if l in V.index and V.at[l, "verdict"] == "asterisk" else "")
    for lab in opens:
        opens[lab] = opens[lab] | (vlab == lab)
    opens["live check"] = open_l
    n_open = sum(m.astype(int) for m in opens.values())
    flag(n_open > 1, "more than one open item (things to confirm plus a missing live check)")
    has_star = (col("confirm_asterisk") == "yes") & (col("confirm_what") != "") & (col("confirm_why") != "")
    flag((n_open == 1) & ~has_star, "one open item but no confirm_asterisk / confirm_what / confirm_why")
    for what, m in opens.items():
        flag((n_open == 1) & m & (col("confirm_what") != what), f"confirm_what does not name the open item ({what})")
    flag((n_open == 0) & (col("confirm_asterisk") == "yes"), "asterisk on a unit with nothing open")
    # THE REVIEW RULE (independent check 2): every shown unit must have a row in data/evidence/review_verdicts.csv with
    # verdict ok or asterisk, written against the evidence as it stands now. A unit nobody has read the evidence for
    # cannot be shown.
    why_of = dict(verdicts.unreviewed(S))
    for lid, name, unit in S[S.listing_id.isin(why_of)][["listing_id", "building_name", "unit"]].itertuples(index=False):
        out.append(f"{lid} ({name} {unit}): {why_of[lid]}")
    # D4 / D16: an elevator may not rest on the city's record of a neighbouring lot, or of a lot with no active elevator
    flag((col("elevator_basis") == "official_record") & ((col("pluto_lot_ok") != "yes") | (num("dob_active_elevators") == 0)),
         "elevator rests on the city's record for a lot that is not the listing's address, or one with no active elevator on file")
    wl = num("dog_weight_limit_lb")
    size_only = (col("dog_size_only") != "") & wl.isna()
    flag(size_only & ~(col("dog_size_note").ne("") & col("tour_confirm").str.contains("dog weight limit")), "size-only dog policy shown without its note and tour question")
    flag(wl < MIN_DOG_LB, f"dog weight limit under {MIN_DOG_LB} lb")
    flag(~(num("all_in") <= CAP), f"all-in over ${CAP:,} or missing")
    av = col("available_date").str.strip().str.lower()
    flag(~(av.isin(["now", "available now", "immediately"]) | (av.str.match(r"\d{4}-\d{2}-\d{2}") & (av.str[:10] <= WINDOW_END))), f"available after {WINDOW_END} or date unknown")
    key = S.building_id + "|" + S.unit.map(parsers.unit_key)
    nolabel = S.unit.map(parsers.unit_key) == ""
    key = key.where(~nolabel, S.building_id + "|" + col("beds") + "|" + col("sqft") + "|" + col("listed_rent"))
    flag(key.duplicated(keep=False), "duplicate unit on the shown list")
    flag(col("review_verdict") == "remove", "a reviewed verdict says remove")
    flag(S.groupby("building_id").listing_id.transform("count") > MAX_PER_BUILDING, f"more than {MAX_PER_BUILDING} shown in one building")
    flag(col("safety_cut").str.lower() == "true", "safety_cut neighborhood")
    gf = DATA / "lifestyle_groups.csv"
    if gf.exists():
        G = pd.read_csv(gf, dtype=str, keep_default_na=False)
        cut = set(G[G.safety_cut.str.lower() == "true"].hood_id)
        flag(col("hood_id").isin(cut), "neighborhood cut by the Jamaica safety rule")
    flag(col("ev_avoid") == "yes", "avoid building")
    flag(col("notes").map(parsers.building_fails_reason) != "", "harvest note says BUILDING_FAILS (for a reason other than small dogs only)")
    return out


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
    viol = shown_violations()
    if viol:
        print(f"SHOWN-LIST ASSERTIONS FAILED: {len(viol)} violation(s)")
        [print("  ", v) for v in viol[:60]]
    else:
        print("shown-list assertions: all pass")
    return 1 if (bad or wiring or viol) else 0


if __name__ == "__main__":
    sys.exit(main())
