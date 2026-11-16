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
all-in over $3,000; available after 2026-12-15; a duplicate unit; more than 8 shown in one building;
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
CAP, WINDOW_END, MAX_PER_BUILDING, MIN_DOG_LB = 3000, "2026-12-15", 8, 25
DISPLAY = {  # pattern -> why it is kept but not scored
    r"^(photo_url|url|building_url|also_seen_at|listing_url|building_site_url)$": "link shown on the page",
    r"^(building_name|address|city|state|zip5|unit|baths|hood|hood_area|manager|park_name|dog_park_name|supermarket|train_station|police_agency|police_geography|unit_count)$": "label shown on the page",
    r"^(dog_policy_text|required_fees_text|lease_terms_text|pet_one_time_fee_text|concession_text.*|rent_regulation|listing_warning|live_notes|live_available_text|available_date_text|transit_summary|transit_sat_summary|toll_items|all_in_lines|all_in_unknown_lines|all_in_estimated_lines)$": "text shown on the unit card or cost receipt",
    r"^rent_(offer_text|free_months|lease_months|first_full_payment_date|first_full_payment_note|needs_call|listed_price_is|gross|basis_kind|asterisk)$": "rent terms shown beside the asterisk",
    r"^(excerpt|quote|item_date|about|category|building_site|detail)$": "evidence text shown on avoid and pause cards",
    r"^(parking_text|optional_fees_text|dog_weight_text|dogs_allowed_note|elevator_note)$": "source sentence kept for display beside the parsed value (shown with an asterisk when the parse is unknown)",
    r"^(price_term_text|price_lease_quote|price_lease_source|pluto_lot_address|review_kind)$": "source sentence or record behind the lease-term asterisk and the NYC lot check (independent check 2)",
    r"^(dob_active_elevators)$": "the city's count of active passenger elevators on the lot: gate input in build_master.py, asserted in this script",
    r"^(call_notes|call_income_multiple|call_called_at|call_building_called_at|call_available|required_fees_phone)$": "phone answers (data/evidence/call_answers.csv): notes and when the call was made; the fee total is read by all_in.py",
    r"^(page_modified_date|page_modified_source|listing_stale_days|listing_stale_why|elevator_aggregator_only|street_overnight_town|street_overnight_rule|street_overnight_url)$": "the date and sentence behind the staleness rule, the elevator-evidence count and the overnight-parking disclosure",
    r"^(resolved_by)$": "which later evidence batch settled a pending listing's missing gate fact, and how (gates.py: apply_resolved_pending)",
    r"^(disclosures|more_in_building)$": "shown on the unit card: conditions to know (never an open gate fact), and further showable units in the building",
    r"^(address_override_source|city_override_source|live_url|all_in_likely_note|rent_offer_type|rent_offer_kind|offer_text_page|unknown_cost_lines)$": "independent check 3: where a corrected address comes from, the page a live check read, the note behind all_in_likely, and the offer in the page's own words",
    r"^(duplicate_listing_ids)$": "other listings of the same unit, merged into this row (their links are in also_seen_at)",
    r"^(near_vs_baseline|crime_latest|crime_source|crime_year|nyc_record_flags)$": "context shown when she asks how a score was reached",
    r"^nycrec_": "NYC record counts by period: shown in the building's record summary; flags derived from them drive the avoid rule",
    r"^near250_.*_(2023|2025|borough_median|above_borough_p80)$": "context for the nearby-crime figures",
    r"^agency_(property|burglary)_per_1000_": "area context shown beside the violent-crime trend",
    r"^(toll_known_subtotal|toll_rt_mail_subtotal|toll_rt_mail_note|toll_complete|drive_min_from|drive_miles|transit_sat_fastest|transit_status|transit_sun_return_fastest|last_sat_departure|util_1br|util_studio|util_1br_complete|coast_m|beach_m|park_ha_800m)$": "figure shown in a scene or receipt",
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
    open_e = (el != "yes") | ~col("elevator_basis").isin(["confirmed_by_phone", "confirmed", "stated", "official_record", "amenities_page", "community_page"]) | (col("elevator_evidence_open") != "") \
        | ((col("elevator_doubt") != "") & (col("elevator_basis") != "confirmed_by_phone"))       # the reviewed doubt table and the garden-style rule (owner, 2026-11-16)
    fl, fb, fk = num("unit_floor"), col("unit_floor_basis"), col("unit_floor_label_kind")
    flag(fl < 2, "floor under 2")
    open_f = ~(fb.isin(["confirmed_by_phone", "confirmed", "stated"]) | ((fb == "inferred") & (fk == "simple") & (fl >= 3)))
    dg = col("dogs_allowed").str.lower()
    flag(dg == "no", "dogs not allowed")
    flag((dg == "yes") & ~col("dogs_allowed_basis").isin(["confirmed_by_phone", "confirmed", "stated", "community_page", "amenities_page"]), "dogs-allowed basis is inferred or unknown")
    open_d = (dg != "yes") | (col("dogs_evidence_open") != "")
    open_l = ~col("live_status").isin(["live", "changed"])
    # independent check 2: lease term over 13 months (D8), cost near the cap with an unknown line (D12), a floor-plan
    # row (D1), an evidence warning about the listing (D6), and whatever a reviewer's asterisk verdict names
    open_lease = (num("price_lease_months") > 13) | (col("price_lowest_of_terms") == "yes")
    open_cost = (num("all_in") <= CAP) & (num("all_in_likely") > CAP)        # owner, 2026-11-16: replaces "cost near the cap"
    open_avail = (S.unit.map(parsers.unit_label_key) == "") & ((col("detail_level") == "building_floorplan") | col("listing_id").str.contains(":plan-") | (S.unit.str.strip() != ""))
    phone = col("phone_settled")                   # facts answered on the phone (rank.py): no longer open, whatever an older row or verdict says
    by_phone = lambda lab: phone.str.split(";").map(lambda xs: lab in xs)
    open_avail = open_avail & ~by_phone("availability")
    stale_rule = (col("listing_stale") == "open") & ~by_phone("listing")
    open_listing = ((col("listing_warning") != "") | stale_rule | (col("live_notes").map(parsers.price_doubt) & ~by_phone("listing")))
    # GATE facts count toward "at most one open"; DISCLOSURES (lease term, cost near the cap, condo rented by its owner,
    # net-effective rent) never do, but must be listed on the unit (owner, 2026-11-16)
    # (a floor that is not published is a disclosure too: owner, 2026-11-16; a floor under 2 is still flagged above)
    opens = {"elevator": open_e, "dogs allowed": open_d, "availability": open_avail, "listing": open_listing, "eligibility": col("eligibility_open") != ""}
    not_published = ~fb.isin(["confirmed_by_phone", "confirmed", "stated"])
    flag(not_published & ~col("disclosures").str.contains('"what": "floor not published"', regex=False), "floor not published but the disclosure is missing")
    flag(not_published & ~col("tour_confirm").str.contains("confirm it is above the ground floor"), "floor not published but the tour question is missing")
    disc = col("disclosures")
    flag(open_lease & ~disc.str.contains('"what": "lease term"', regex=False), "price is for a lease over 13 months but the disclosure 'lease term' is missing")
    flag(open_cost & ~disc.str.contains('"what": "could pass $3,000"', regex=False), "all-in within the cap but likely over it once parking and fees are known, and the disclosure is missing")
    flag(~open_cost & disc.str.contains('"what": "could pass $3,000"', regex=False), "the 'could pass $3,000' disclosure sits on a unit it does not apply to")
    flag(disc.str.contains('"what": "cost near the cap"', regex=False), "the old 'cost near the cap' disclosure is still present")
    flag((col("rent_basis_kind") == "net_effective") & ~disc.str.contains('"what": "net-effective rent"', regex=False), "net-effective rent without its disclosure")
    # independent check 3, D5: net-effective is stated only where the evidence says the listed price is net-effective
    flag((col("rent_basis_kind") == "net_effective") & (col("rent_listed_price_is") != "net_effective"), "rent called net-effective though no page or evidence row says the listed price is")
    flag(disc.str.contains('"what": "net-effective rent"', regex=False) & (col("rent_listed_price_is") != "net_effective"), "net-effective disclosure without a statement that the price is net-effective")
    flag((col("rent_offer_kind") == "special_offer") & ~disc.str.contains('"what": "special offer"', regex=False), "a special offer is advertised but the 'special offer' disclosure is missing")
    flag(num("rent_gross").notna() & (col("rent_basis_kind") != "net_effective") & (num("rent_gross") != num("rent_basis")), "a gross rent is given for a unit whose price is not stated to be net-effective")
    flag(col("all_in_unknown_lines").str.contains("pet rent"), "pet rent counted as nothing: it must be stated or estimated (owner, 2026-11-16)")
    flag(disc.str.contains('"what": "(?:elevator|dogs allowed|availability|listing|eligibility)"'), "a gate fact is listed as a disclosure")
    import verdicts
    VU = verdicts.by_unit()                          # several rows per unit, one per kind (independent check 3, D22)
    KIND_LABEL = {"elevator": "elevator", "dogs": "dogs allowed", "not_available": "availability", "unverified": "listing",
                  "wrong_building": "listing", "restricted": "eligibility"}
    kinds_of = lambda l, verdict: [r["kind"] for r in VU[l]["rows"] if r["verdict"] == verdict] if l in VU else []
    vdisc = S.listing_id.map(lambda l: kinds_of(l, "disclose"))
    why_of_kind = lambda l, k: " ".join(r["why"] for r in VU[l]["rows"] if r["kind"] == k).lower() if l in VU else ""
    flag(pd.Series([("coop_condo" in ks) or ("other" in ks and "condo" in why_of_kind(l, "other")) for l, ks in zip(S.listing_id, vdisc)], index=S.index)
         & ~disc.str.contains('"what": "condo rented by its owner"', regex=False), "a reviewer's condo verdict is not among the disclosures")
    flag(vdisc.map(lambda ks: "lease_term" in ks) & ~disc.str.contains('"what": "lease term"', regex=False), "a reviewer's lease-term verdict is not among the disclosures")
    flag(S.listing_id.map(lambda l: any(r["verdict"] == "asterisk" and r["kind"] in verdicts.DISCLOSURE_KINDS for r in VU[l]["rows"]) if l in VU else False),
         "a verdict row is an asterisk on a disclosure kind: the verdict column must say what the page does (D22)")
    # D8: a condominium lot (city class R*) at the listing's own address, not a managed rental, carries the condo disclosure
    flag(((col("pluto_class").str.upper().str.startswith("R") & (col("pluto_lot_ok") == "yes") & (col("listing_type") != "managed_building")) | col("listing_type").str.contains("condo", case=False))
         & ~disc.str.contains('"what": "condo rented by its owner"', regex=False), "a condominium unit (city class R*, or a listing typed condo) is shown without the condo disclosure")
    vgate = S.listing_id.map(lambda l: {KIND_LABEL.get(k, "") for k in kinds_of(l, "asterisk")} - {""})
    # 4b: staleness by rule is the open item "listing"; where the reviewer wrote the same doubt up as availability it counts once
    opens["listing"] = opens["listing"] & ~(vgate.map(lambda ks: "availability" in ks) & (col("listing_warning") == "") & ~col("live_notes").map(parsers.price_doubt))
    for lab in opens:
        opens[lab] = opens[lab] | (vgate.map(lambda ks, lab=lab: lab in ks) & ~by_phone(lab))
    # D2: sibling consistency on unit numbers a reviewer read as first-floor
    rem = {}
    for l, d in VU.items():
        for r in d["rows"]:
            if r["verdict"] == "remove" and r["kind"] == "floor" and parsers.unit_label_key(r["unit"]) and re.search(r"first[- ]floor|floor 1\b|ground", r["why"], re.I):
                rem.setdefault(r["building_id"], []).append(r["unit"])
    flag(pd.Series([b in rem and parsers.reads_as_ground_like_siblings(un, rem[b]) for b, un in zip(S.building_id, S.unit)], index=S.index),
         "the unit number has the same shape as siblings a reviewer removed as first-floor units")
    # D3 / D11: a stale page is never switched off by a 'second site' that is the same site
    import build_master as _bm
    flag((num("listing_stale_days") > 60) & (col("listing_stale") == "") & (col("call_called_at") == "")
         & ~pd.Series([_bm.second_site(a, b) or bool(str(d).strip()) for a, b, d in zip(col("url"), col("also_seen_at"), col("duplicate_listing_ids"))], index=S.index),
         "the listing page is over 60 days unchanged, no second site lists the unit, and the staleness item is missing")
    flag(col("listing_stale") == "remove", "the listing page was unchanged for more than six months when it was read")
    import rank as _rank
    need_p = pd.Series([_rank.needs_parking_disclosure(a, b, c) for a, b, c in zip(col("street_overnight_severity"), col("parking_type"), col("parking_fee"))], index=S.index)
    flag(need_p & ~disc.str.contains('"what": "overnight street parking"', regex=False), "overnight street parking is restricted in this town and the unit's parking is not confirmed, but the disclosure is missing")
    flag((col("dog_weight_unstated") != "") & num("dog_weight_limit_lb").isna() & (col("dog_weight_limit_lb").str.lower() != "no limit") & ~col("tour_confirm").str.contains("dog weight limit"),
         "a dog weight limit with no number is stated, but the tour question is missing")
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
    flag((col("parking_type").map(lambda t: bool(parsers.OFFSITE_PARKING.search(str(t))))) & (num("parking_rank") > 2), "off-site parking is scored as parking at the building (D10)")
    flag(~(num("evidence_rows") > 0), "the building has no evidence rows: nothing was read, so the unit cannot be shown")
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
