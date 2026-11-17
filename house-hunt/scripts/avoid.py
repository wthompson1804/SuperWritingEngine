"""Apply the evidence pass: drop units that are not real or fail a gate on closer reading, and mark avoid buildings.

Inputs: data/evidence/{live_check,confirm,items,facts}_batch_*.csv, data/evidence/nyc_records_flags.csv
Outputs:
  data/unit_exclusions.csv    addr_key, unit ("" = whole building), reason, source   -> removed before ranking
  data/avoid_buildings.csv    addr_key, avoid (yes/no), reasons, evidence_json, pause_notes  -> shown as avoid cards
  data/reference/ground_reading_unassigned.csv   checker's ground-floor readings that could not be tied to a unit
Rules (Will, docs/PLAN_V3_APPROVED_2026-11-15.md, later amendments):
  DROP   listing gone; dogs clearly not allowed, or the elevator contradicted, on the building's page; ground-floor unit;
         listing the checker judged not open-market, not genuine, stale or a duplicate.
         NOT a drop: a dog policy that CONFLICTS between sources. That is one open gate fact (dogs), raised in
         scripts/rank.py; the building's own or its manager's page settles it.
  AVOID  car crime: 3+ independent reports at the building or its parking in 24 months, or (NYC, police-located
         incidents) vehicle theft + theft from vehicles within 250 m in 24 months at least double the median for
         candidate buildings in the city
         elevator: 3+ independent outage reports in 24 months, or (NYC) 3+ elevator complaints AND above the citywide
                   90th percentile for similar buildings in 24 months
         management, judged on the LAST 6 MONTHS: 3+ dated tenant reports of serious problems in that window, or (NYC)
                   heat / pest / mold / class C violation rate above the citywide 90th percentile in the last 6 months
                   on 2+ measures
  PAUSE  the same kinds of evidence, older than 6 months or below the thresholds -> "Gives us pause", not avoid.
"""
import glob, json, re, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA
import parsers

TODAY = pd.Timestamp("2026-11-15")
M6, M24 = TODAY - pd.DateOffset(months=6), TODAY - pd.DateOffset(months=24)
NOT_REAL = re.compile(r"not an open-market|income restricted|far under market|not a real|not genuine|scam|likely a co-op|co-op sublet|"
                      r"listing looks stale|duplicate candidate|out-of-state phone|below the median price|probably not a real|verify before relying", re.I)


# Findings that make a listing unusable for her, wherever the checker wrote them (live-check notes or facts).
INELIGIBLE = re.compile(r"AGE-RESTRICTED|55\+ (?:only|senior|independent|communit)|(?:this as|is) a 55\+ communit|senior housing|active adult community designed|"
                        r"(?-i:WAITLIST)|No Units currently available|Rented/Leased|income[- ]restricted|income limits|Pet-free community|"
                        r"probably a dead listing|cannot be found|describes? a different building", re.I)
BUILDING_WIDE = re.compile(r"AGE-RESTRICTED|55\+|senior housing|active adult|income[- ]restricted|income limits|Pet-free", re.I)
NO_LIFT_READING = re.compile(r"probably (?:a )?walk-?up|probably no elevator|my reading: (?:no elevator|unlikely|probably)|My reading: unlikely|fits a small walk-?up|"
                             r"without elevators|came from the unit label only|height inference came from reading|low-rise garden|garden complex: probably", re.I)
GROUND_READING = re.compile(r"ground|first[- ]floor|\bfloor 1\b|reading 1\b|^\s*\)?\s*:\s*1\b|:\s*1\?|:\s*1\b(?!\d)", re.I)


GROUND_LIKELY = re.compile(r"(?:possibl[ey]|likely|probably|may be|would be|could be)[^.;|]{0,30}(?:ground|floor 1\b|first[- ]floor)|"
                           r"(?:ground|floor 1\b)[^.;|]{0,25}(?:is possible|possible)|ground-level entry|floor 1, if", re.I)


# Independent check 2, D5: this pattern was written r"\\bco-?op\\b", which in a raw string is a literal backslash + "b",
# so the first alternative could never match. The other patterns above were checked for the same slip: none has it
# (scripts/test_rules.py asserts that no pattern in this file contains a doubled backslash and that each one matches
# its own example).
COOP = re.compile(r"\bco-?ops?\b|board approval|approval by (?:the )?board|cooperative (?:apartment|building|unit)|tenants corp|owners corp|owners,? inc", re.I)
NOT_COOP = re.compile(r"different co-op buildings|not (?:a |in a )?co-?op|co-?op city|no co-?op|condo/co-?op or owner-rented|rather than (?:a )?co-?op|is a rental,? not", re.I)


def _around(t, m, n=70):
    t = str(t)
    return t[max(0, m.start() - n): m.end() + n].replace("\n", " ").strip()


def cat(kind):
    fs = glob.glob(str(DATA / "evidence" / f"{kind}_batch_*.csv"))
    return pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False).assign(batch=Path(f).stem.split("_batch_")[-1]) for f in fs], ignore_index=True)


def when(s):
    """Date of an item. A year-only date is placed at January 1 (the earliest it can mean), a month-only date at the
    1st: an item is never counted as more recent than its date proves (independent check W19)."""
    s = str(s).strip()
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", s)
    if not m:
        return pd.NaT
    return pd.Timestamp(int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1))


def month_known(s):
    return bool(re.match(r"\d{4}-\d{2}", str(s).strip()))


OUTAGE = re.compile(r"out of (?:service|order)|broke|break|outage|not work|doesn.?t work|don.?t work|\bdown\b|stuck|inoperable|repair|fail|restore service|"
                    r"shut|trapped|unreliable|malfunction|out for|wasn.?t working|weren.?t working|not functioning", re.I)
# An income-restricted TAG that only a listing site shows, where the checker read the manager's own page and found no income
# limit, is not a finding that the unit is closed to her: it is one open "eligibility" fact (scripts/build_master.py reads the
# evidence fact 'eligibility'; scripts/rank.py counts it). Batch 19: 111 Prospect St and 25 Third Street, Stamford.
TAG_ONLY = re.compile(r"manager's (?:own )?page (?:does not say so|states no income limit)|states no income limit|gives no income limit", re.I)
INCOME_WORDS = re.compile(r"income[- ]restricted|income limits", re.I)
AGGREGATOR = re.compile(r"trulia|zumper|apartmentlist|zillow|apartments\.com|rent\.com", re.I)


def main():
    L, C, I = cat("live_check"), cat("confirm"), cat("items")
    L = parsers.live_rows_learned(L).reset_index(drop=True)      # a 'not_read' row learned nothing (batch 21)
    F0 = cat("facts")
    tag_only = {r.addr_key for r in L.itertuples() if TAG_ONLY.search(r.notes or "") and INCOME_WORDS.search(r.notes or "")} | \
               ({r.addr_key for r in F0.itertuples() if TAG_ONLY.search(r.value or "") and INCOME_WORDS.search(r.value or "")} if len(F0) else set())
    income_tag_only = lambda key, text: key in tag_only and not NOT_REAL.search(INCOME_WORDS.sub(" ", re.sub(r"income restricted", " ", text or "", flags=re.I)))
    ex = []
    # addresses where the evidence pass saw a numbered unit live: there a "gone" row with no unit number is one floor-plan
    # row that left the page, not the whole building (111 Prospect St, batch 19: the plan row is gone, #206, #306 and #511
    # are on the manager's page). The plan row itself is dropped through its own live status in the master table.
    live_named = {r.addr_key for r in L.itertuples() if r.status in ("live", "changed") and parsers.unit_label_key(r.unit)}
    for r in L.itertuples():
        if r.status == "gone" and not parsers.unit_label_key(r.unit) and r.addr_key in live_named:
            continue
        if r.status == "gone":
            ex.append((r.addr_key, r.unit, "listing gone at live check", r.listing_url))
        elif NOT_REAL.search(r.notes or "") and not income_tag_only(r.addr_key, r.notes):
            ex.append((r.addr_key, r.unit, "checker judged the listing not open-market, not genuine, stale or duplicate: " + r.notes[:160], r.listing_url))
    xwf = DATA / "reference" / "building_crosswalk.csv"
    XW = pd.read_csv(xwf, dtype=str).set_index("addr_key").building_id.to_dict() if xwf.exists() else {}
    bkey = lambda k: XW.get(k, k)
    # dog policy: only a real "no" excludes. Where sources disagree, the building's own or its manager's page wins;
    # aggregator against aggregator is left as an open fact for scripts/rank.py to hold back (independent check W20).
    dog_rows = C[C.fact.str.lower().str.startswith("dogs_allowed")]
    own_yes = {bkey(r.addr_key) for r in dog_rows[dog_rows.status == "confirmed"].itertuples() if not AGGREGATOR.search(r.source_url or "")}
    for b_, g in dog_rows[dog_rows.status == "contradicts"].groupby(dog_rows.addr_key.map(bkey)):
        verdict = parsers.dog_conflict("; ".join(dict.fromkeys(g.value)))
        if verdict == "no" and not (b_ in own_yes and AGGREGATOR.search(" ".join(g.source_url)) and not re.search(r"service|emotional", " ".join(g.value), re.I)):
            for k in sorted(set(g.addr_key)):
                ex.append((k, "", "dogs not allowed: " + g.value.iloc[0][:120], g.source_url.iloc[0]))
    for r in C[C.status == "contradicts"].itertuples():
        f = r.fact.lower()
        if f.startswith("elevator"):
            ex.append((r.addr_key, "", "elevator contradicted: " + r.value[:120], r.source_url))
        elif f.startswith("floor"):
            # "unit 5106: floor 1 (ground floor)" -> unit 5106 only; "1 (ground floor)" -> the listed unit (W18)
            pairs, _ = parsers.parse_floor_confirm(r.value)
            gf = [lab for lab, fl_ in pairs if fl_ <= 1 and lab != "*"]
            if gf or any(lab == "*" and fl_ <= 1 for lab, fl_ in pairs):
                ex.append((r.addr_key, ";".join(gf), "ground-floor unit: " + r.value[:120], r.source_url))
        elif f.startswith("dog_weight") and re.search(r"\b(1\d|2[0-4]) ?lb", r.value):
            ex.append((r.addr_key, "", "dog weight limit under 25 lb: " + r.value[:120], r.source_url))
    # --- eligibility and checker readings (round 3 review): a finding in the checker's notes must reach the list ---
    F = cat("facts")
    for r in L.itertuples():
        m = INELIGIBLE.search(r.notes or "")
        if m and INCOME_WORDS.fullmatch(m.group(0)) and r.addr_key in tag_only:
            m = INELIGIBLE.search(INCOME_WORDS.sub(" ", r.notes))          # the tag alone does not exclude; anything else in the note still does
        if m:
            whole = bool(BUILDING_WIDE.search(m.group(0)))
            ex.append((r.addr_key, "" if whole else r.unit, "not open to her or not really available: " + _around(r.notes, m), r.listing_url))
    for r in F.itertuples():
        m = INELIGIBLE.search(r.value)                      # the checker's own statement, not a quoted page line
        if m and INCOME_WORDS.fullmatch(m.group(0)) and r.addr_key in tag_only:
            continue
        if m and BUILDING_WIDE.search(m.group(0)) and not re.search(r"market[- ]rate and|are not\b", r.value, re.I):
            ex.append((r.addr_key, "", "not open to her: " + _around(r.value, m), r.source_url))
    MU = pd.read_csv(DATA / "master_units.csv", dtype=str, keep_default_na=False, usecols=["addr_key", "unit"], low_memory=False)
    MU_ID = pd.read_csv(DATA / "master_units.csv", dtype=str, keep_default_na=False, usecols=["addr_key", "unit", "listing_id"], low_memory=False)
    unassigned = []
    units_at = MU.groupby("addr_key").unit.apply(lambda x: sorted(set(x))).to_dict()
    # a floor the checker CONFIRMED as 1 / ground is a gate failure too, not only a "contradicts" row (batch 13: J Centra)
    for r in C[(C.status == "confirmed") & C.fact.str.lower().str.startswith("floor")].itertuples():
        pairs, _ = parsers.parse_floor_confirm(r.value)
        qlab = re.findall(r"\bUnit ([\w-]+)", r.quote or "")
        for lab, fl_ in pairs:
            if fl_ <= 1:
                lab_ = lab if lab != "*" else (qlab[0] if len(qlab) == 1 else "")
                ex.append((r.addr_key, lab_, "ground-floor unit (confirmed): " + f"{r.value} | {r.quote}"[:140], r.source_url))
    for r in C[C.status != "confirmed"].itertuples():
        f, t = r.fact.lower(), f"{r.value} | {r.quote}"
        if f.startswith("elevator") and r.status != "contradicts":
            m = NO_LIFT_READING.search(t)
            if m:
                ex.append((r.addr_key, "", "elevator not stated anywhere and the checker's reading is that there is none: " + _around(t, m), r.source_url))
        elif f.startswith("floor") and r.status != "contradicts":
            labs = [x for x in units_at.get(r.addr_key, []) if x]
            named = [x for x in labs if re.search(r"(?<![\w-])" + re.escape(x) + r"(?![\w-])", t)]
            if named:
                hit_named = False
                for x in named:
                    clause = next((c for c in re.split(r"[;|]|\. ", t) if re.search(r"(?<![\w-])" + re.escape(x) + r"(?![\w-])", c)), "")
                    after = clause.split(x, 1)[1] if x in clause else clause
                    if GROUND_READING.search(after):
                        ex.append((r.addr_key, x, "possible ground-floor unit (checker's reading; no page states the floor): " + clause.strip()[:140], r.source_url))
                        hit_named = True
                if not hit_named and len(named) == 1 and GROUND_LIKELY.search(t):
                    ex.append((r.addr_key, named[0], "possible ground-floor unit (checker's reading; no page states the floor): " + t[:140], r.source_url))
            else:
                # unit labels written differently from ours ("2106: floor 1"): take the labels from the text
                labs1 = re.findall(r"(?<![\w-])([A-Za-z]{0,3}-?\d[\w-]{1,7}):\s*(?:floor\s*)?1\b(?!\d)", t)
                if labs1:
                    ex.append((r.addr_key, ";".join(dict.fromkeys(labs1)), "possible ground-floor unit (checker's reading; no page states the floor): " + t[:140], r.source_url))
                elif GROUND_LIKELY.search(t):
                    # Independent check 2: this used to exclude the WHOLE building when no unit could be named (62 Treat
                    # St lost plan "208" because plan "103" reads as floor 1). Now: the floor-plan row the text names;
                    # the building's only listed row; otherwise nothing is excluded and the reading is left to the
                    # reviewer (data/reference/ground_reading_unassigned.csv).
                    rows_here = MU_ID[MU_ID.addr_key == r.addr_key]
                    hit_plan = [x.listing_id for x in rows_here.itertuples()
                                if (pm := re.search(r":plan-([^:]+)", x.listing_id)) and re.search(r"[\"'“ ]" + re.escape(pm.group(1).replace("_", " ")) + r"[\"'” ,:;.]", t)
                                and GROUND_LIKELY.search(next((c for c in re.split(r"[;|]|\. (?=Plan)", t) if pm.group(1).replace("_", " ") in c), ""))]
                    if hit_plan:
                        for lid in hit_plan:
                            ex.append((r.addr_key, "", "possible ground-floor unit (checker's reading; no page states the floor): " + t[:140], r.source_url, lid))
                    elif len(rows_here) == 1:
                        ex.append((r.addr_key, "", "possible ground-floor unit (checker's reading; no page states the floor): " + t[:140], r.source_url))
                    else:
                        unassigned.append({"addr_key": r.addr_key, "reading": t[:300], "source": r.source_url})
    # co-op rentals are out (owner, 2026-11-15): board approval may not fit a Dec 15 move-in. A building is a co-op when
    # the city's record classes it as one (PLUTO D0, D4, C6, C8) or a checker's note / the listing says co-op or board approval.
    MP = pd.read_csv(DATA / "master_units.csv", dtype=str, keep_default_na=False, low_memory=False)
    for k, g in MP[MP.get("pluto_class", "").isin(["D0", "D4", "C6", "C8"])].groupby("addr_key"):
        ex.append((k, "", f"co-op building (city record, building class {g.pluto_class.iloc[0]})", "https://www.nyc.gov/site/planning/data-maps/open-data/dwn-pluto-mappluto.page"))
    for k, g in MP.groupby("addr_key"):
        t = " | ".join(" ".join(g[c].astype(str)) for c in ["notes", "building_type", "required_fees_text", "building_name"] if c in g)
        m = COOP.search(t)
        if m and not NOT_COOP.search(t):
            ex.append((k, "", "co-op rental (listing text): " + _around(t, m), g.url.iloc[0] if "url" in g else ""))
    for D, cols, src in [(L, ["notes"], "listing_url"), (F, ["fact", "value", "quote"], "source_url"), (C, ["value", "quote"], "source_url")]:
        for r in D.to_dict("records"):
            t = " | ".join(str(r.get(c, "")) for c in cols)
            m = COOP.search(t)
            if m and not NOT_COOP.search(t):
                ex.append((r["addr_key"], "", "co-op rental (checker's note): " + _around(t, m), r.get(src, "")))
    X = pd.DataFrame([e if len(e) == 5 else e + ("",) for e in ex], columns=["addr_key", "unit", "reason", "source", "listing_id"]).drop_duplicates()
    # a whole-building row (unit == "" and no listing_id) excludes every unit; a row with listing_id excludes that row only
    X.to_csv(DATA / "unit_exclusions.csv", index=False)
    pd.DataFrame(unassigned, columns=["addr_key", "reading", "source"]).to_csv(DATA / "reference" / "ground_reading_unassigned.csv", index=False)

    I = I[~I.category.isin(["none_found", ""])].copy()
    I["dt"] = I.item_date.map(when)
    # one incident reported under several address keys of the same building counts once (W19)
    I["bkey"] = I.addr_key.map(bkey)
    I = I.drop_duplicates(["bkey", "category", "excerpt"])
    is_count_summary = I.source_site.str.contains("311|HPD|NYC Open Data", case=False)   # counted via nyc_records_flags instead
    R = I[~is_count_summary]
    nf = DATA / "evidence" / "nyc_records_flags.csv"
    N = pd.read_csv(nf, dtype=str, keep_default_na=False) if nf.exists() else pd.DataFrame(columns=["addr_key", "flag", "count", "per_100_units", "baseline_p90", "query_url", "metric", "period"])
    # police-located car crime near the building (NYC only): the approved rule is "at least double the median for
    # candidate buildings in the same city". Counts = vehicle theft + theft from vehicle within 250 m, last 24 months.
    U = pd.read_csv(DATA / "units.csv", low_memory=False)
    U = U[U.unit_status == "pass"].drop_duplicates("addr_key")
    U["car250"] = pd.to_numeric(U.near_veh_theft_24m, errors="coerce") + pd.to_numeric(U.near_theft_from_veh_24m, errors="coerce").fillna(0)
    car_med = U.car250.median()
    car250 = U.set_index("addr_key").car250.dropna()
    # outside NYC: Jersey City police incidents (about 10.5 months), NJ state housing inspections, rating screen
    jc, jc_med, jc_period, jc_url, bhi, rating = {}, None, "", "", {}, {}
    nn = DATA / "evidence" / "non_nyc_records.csv"
    if nn.exists():
        NN = pd.read_csv(nn, dtype=str, keep_default_na=False)
        P = NN[NN.record_type == "police_incidents"]
        for k, g in P.groupby("addr_key"):
            t = g[g.metric == "vehicle_crime_250m_total"]
            m = g[g.metric == "city_candidate_median_vehicle_crime_250m"]
            if len(t):
                jc[k] = float(t.value.iloc[0]); jc_period, jc_url = t.period.iloc[0], t.query_url.iloc[0]
            if len(m):
                jc_med = float(m.value.iloc[0])
        Hh = NN[(NN.record_type == "housing_inspection") & (NN.metric == "bhi_latest_report_open_violations")]
        bhi = {r.addr_key: (r.value, r.period, r.query_url) for r in Hh.itertuples()}
    rs = DATA / "evidence" / "rating_standard.csv"
    if rs.exists():
        RS = pd.read_csv(rs, dtype=str, keep_default_na=False).drop_duplicates("addr_key")
        rating = {r.addr_key: r for r in RS.itertuples()}
    rows = []
    keys = sorted(set(I.addr_key) | set(N.addr_key) | set(L.addr_key) | set(car250.index) | set(jc) | set(rating))
    for k in keys:
        r, n = R[R.bkey == bkey(k)], N[N.addr_key == k]
        flags = set(n.flag)
        def reports(x):
            """Distinct dated reports: one per source page and date, however many excerpts were taken from it."""
            return len(x[x.item_date.astype(str).str.strip() != ""].drop_duplicates(["source_url", "item_date"]))
        def cnt(c, since=None, need_month=False):
            x = r[r.category == c]
            if c == "elevator":
                x = x[x.excerpt.map(lambda e: bool(OUTAGE.search(str(e)))).astype(bool)]          # an outage, not "no elevator here"
            if c == "management":
                x = x[x.about != "garage_or_lot"]                                    # parking prices are not management failures
            if since is not None:
                x = x[x.dt >= since]
            if need_month:
                x = x[x.item_date.map(month_known).astype(bool)]
            return reports(x)
        car24, el24 = cnt("car_crime", M24), cnt("elevator", M24)
        mg6 = cnt("management", M6, need_month=True)
        mg_all = cnt("management")
        mg_old = max(mg_all - mg6, 0)
        mg6_pages = r[(r.category == "management") & (r.about != "garage_or_lot") & (r.dt >= M6) & r.item_date.map(month_known).astype(bool)].source_url.nunique()
        nyc6 = [f for f in flags if f.endswith("_6m_above_p90") and not f.startswith("elevator")]
        nyc_el = "elevator_complaints_24m_ge_3" in flags and "elevator_complaints_24m_above_p90" in flags
        reasons, pause = [], []
        c250 = car250.get(k)
        if c250 is not None and c250 >= 2 * car_med:
            reasons.append(f"car crime: {int(c250)} vehicle thefts and thefts from vehicles within 250 m in 24 months (police data), at least double the median of {car_med:.0f} for candidate buildings in New York City")
        if k in jc and jc_med and jc[k] >= 2 * jc_med:
            reasons.append(f"car crime: {int(jc[k])} vehicle thefts and thefts from vehicles within 250 m ({jc_period.split(' (')[0]}, about 10.5 months, Jersey City police data), at least double the median of {jc_med:.0f} for candidate buildings in Jersey City")
        if car24 >= 3: reasons.append(f"car crime: {car24} separate dated reports in 24 months")
        elif cnt("car_crime"): pause.append(f"car crime mentioned ({cnt('car_crime')} report(s), below the threshold or older)")
        if el24 >= 3: reasons.append(f"elevator: {el24} separate dated reports of outages in 24 months")
        if nyc_el: reasons.append("elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings")
        if not (el24 >= 3 or nyc_el) and (el24 or "elevator_complaints_6m_ge_1" in flags): pause.append("some elevator complaints, below the threshold")
        if mg6 >= 3: reasons.append(f"management: {mg6} separate dated tenant reports of problems in the last 6 months" + (" (all on one reviews page)" if mg6_pages == 1 else ""))
        if len(nyc6) >= 2: reasons.append("management: city records in the last 6 months above the 90th percentile on " + ", ".join(sorted(f.split('_6m')[0] for f in nyc6)))
        if not (mg6 >= 3 or len(nyc6) >= 2):
            if mg6 or len(nyc6) == 1: pause.append("recent management complaints, below the threshold")
            if mg_old: pause.append(f"{mg_old} older management complaint(s); management may have changed")
        rt = rating.get(k)
        verdict = getattr(rt, "rating_verdict", "") if rt is not None else ""
        if rt is not None and getattr(rt, "has_nyc_records", "") not in ("True", "true", "yes", "1"):
            if verdict == "avoid" and not reasons:
                reasons.append("reviews: " + rt.rating_verdict_why)
            elif verdict == "pause":
                pause.append("reviews: " + rt.rating_verdict_why)
        if k in bhi and bhi[k][0] not in ("", "0"):
            pause.append(f"NJ state housing inspection: {bhi[k][0]} open violations at the latest report ({bhi[k][1]})")
        if cnt("safety_incident"): pause.append(f"{cnt('safety_incident')} safety incident report(s) at the address")
        ev = [{"category": x.category, "date": x.item_date, "excerpt": x.excerpt[:300], "url": x.source_url, "source": x.source_site}
              for x in r[r.category.isin(["car_crime", "elevator", "management", "safety_incident"])].sort_values("dt", ascending=False).head(8).itertuples()]
        ev += [{"category": x.metric, "date": x.period, "excerpt": f"{x.count} ({x.per_100_units} per 100 units; citywide 90th percentile {x.baseline_p90})", "url": x.query_url, "source": "NYC Open Data"}
               for x in n[n.flag.str.contains("above_p90")].head(6).itertuples()]
        pos = r[r.category == "positive"].sort_values("dt", ascending=False).head(3)
        rows.append({"addr_key": k, "avoid": "yes" if reasons else "no", "reasons": "; ".join(reasons), "pause_notes": "; ".join(pause),
                     "evidence_json": json.dumps(ev), "positive_json": json.dumps([{"date": x.item_date, "excerpt": x.excerpt[:300], "url": x.source_url} for x in pos.itertuples()]),
                     "public_evidence": ("NYC records" if len(n) else ("rating screen: " + verdict if verdict else "none readable")),
                     "car_crime_250m_24m": c250 if c250 is not None else "", "nyc_candidate_median_car_crime": car_med,
                     "n_car24": car24, "n_elevator24": el24, "n_mgmt_6m": mg6, "n_mgmt_older": mg_old, "nyc_flags": ";".join(sorted(flags - {"none"}))})
    A = pd.DataFrame(rows); A.to_csv(DATA / "avoid_buildings.csv", index=False)
    print(f"exclusions: {len(X)} rows on {X.addr_key.nunique()} buildings; avoid buildings: {(A.avoid == 'yes').sum()} of {len(A)}; with pause notes: {(A.pause_notes != '').sum()}")
    print(A[A.avoid == "yes"][["addr_key", "reasons"]].to_string(index=False)[:3500])


if __name__ == "__main__":
    main()
