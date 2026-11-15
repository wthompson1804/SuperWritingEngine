"""Apply the evidence pass: drop units that are not real or fail a gate on closer reading, and mark avoid buildings.

Inputs: data/evidence/{live_check,confirm,items,facts}_batch_*.csv, data/evidence/nyc_records_flags.csv
Outputs:
  data/unit_exclusions.csv    addr_key, unit ("" = whole building), reason, source   -> removed before ranking
  data/avoid_buildings.csv    addr_key, avoid (yes/no), reasons, evidence_json, pause_notes  -> shown as avoid cards
  data/evidence_summary.csv   one row per building: counts by category and period, confirmed facts
Rules (Will, docs/PLAN_V3_APPROVED_2026-11-15.md, later amendments):
  DROP   listing gone; dogs not allowed or elevator contradicted on the building's page; ground-floor unit; listing the
         checker judged not open-market, not genuine, stale or a duplicate; dog policy conflicting between sources.
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

TODAY = pd.Timestamp("2026-11-15")
M6, M24 = TODAY - pd.DateOffset(months=6), TODAY - pd.DateOffset(months=24)
NOT_REAL = re.compile(r"not an open-market|income restricted|far under market|not a real|not genuine|scam|likely a co-op|co-op sublet|"
                      r"listing looks stale|duplicate candidate|out-of-state phone|below the median price|probably not a real|verify before relying", re.I)


def cat(kind):
    fs = glob.glob(str(DATA / "evidence" / f"{kind}_batch_*.csv"))
    return pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False).assign(batch=Path(f).stem.split("_batch_")[-1]) for f in fs], ignore_index=True)


def when(s):
    s = str(s).strip()
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", s)
    if not m:
        return pd.NaT
    return pd.Timestamp(int(m.group(1)), int(m.group(2) or 6), int(m.group(3) or 15))


def main():
    L, C, I = cat("live_check"), cat("confirm"), cat("items")
    ex = []
    for r in L.itertuples():
        if r.status == "gone":
            ex.append((r.addr_key, r.unit, "listing gone at live check", r.listing_url))
        elif NOT_REAL.search(r.notes or ""):
            ex.append((r.addr_key, r.unit, "checker judged the listing not open-market, not genuine, stale or duplicate: " + r.notes[:160], r.listing_url))
    for r in C[C.status == "contradicts"].itertuples():
        f = r.fact.lower()
        if f.startswith("dogs_allowed"):
            ex.append((r.addr_key, "", "dog policy contradicted or conflicting between sources: " + r.value[:120], r.source_url))
        elif f.startswith("elevator"):
            ex.append((r.addr_key, "", "elevator contradicted: " + r.value[:120], r.source_url))
        elif f.startswith("floor"):
            units = re.findall(r"([\w-]+):? ?(?:floor|is on floor)? ?1\b", r.value)
            gf = re.findall(r"([A-Za-z0-9-]+)[^;,]*?(?:floor 1|ground floor)", r.value)
            ex.append((r.addr_key, ";".join(gf) if len(gf) and ":" in r.value else "", "ground-floor unit: " + r.value[:120], r.source_url))
        elif f.startswith("dog_weight") and re.search(r"\b(1\d|2[0-4]) ?lb", r.value):
            ex.append((r.addr_key, "", "dog weight limit under 25 lb: " + r.value[:120], r.source_url))
    X = pd.DataFrame(ex, columns=["addr_key", "unit", "reason", "source"]).drop_duplicates()
    X.to_csv(DATA / "unit_exclusions.csv", index=False)

    I = I[~I.category.isin(["none_found", ""])].copy()
    I["dt"] = I.item_date.map(when)
    I = I.drop_duplicates(["addr_key", "category", "excerpt"])
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
        r, n = R[R.addr_key == k], N[N.addr_key == k]
        flags = set(n.flag)
        def cnt(c, since=None):
            x = r[r.category == c]
            if since is not None:
                x = x[x.dt >= since]
            return x.source_url.nunique() if c == "car_crime" else len(x)
        car24, el24 = cnt("car_crime", M24), cnt("elevator", M24)
        mg6, mg_old = cnt("management", M6), len(r[(r.category == "management") & ~(r.dt >= M6)])
        nyc6 = [f for f in flags if f.endswith("_6m_above_p90") and not f.startswith("elevator")]
        nyc_el = "elevator_complaints_24m_ge_3" in flags and "elevator_complaints_24m_above_p90" in flags
        reasons, pause = [], []
        c250 = car250.get(k)
        if c250 is not None and c250 >= 2 * car_med:
            reasons.append(f"car crime: {int(c250)} vehicle thefts and thefts from vehicles within 250 m in 24 months (police data), at least double the median of {car_med:.0f} for candidate buildings in New York City")
        if k in jc and jc_med and jc[k] >= 2 * jc_med:
            reasons.append(f"car crime: {int(jc[k])} vehicle thefts and thefts from vehicles within 250 m ({jc_period.split(' (')[0]}, about 10.5 months, Jersey City police data), at least double the median of {jc_med:.0f} for candidate buildings in Jersey City")
        if car24 >= 3: reasons.append(f"car crime: {car24} independent reports in 24 months")
        elif cnt("car_crime"): pause.append(f"car crime mentioned ({cnt('car_crime')} report(s), below the threshold or older)")
        if el24 >= 3: reasons.append(f"elevator: {el24} tenant reports of outages in 24 months")
        if nyc_el: reasons.append("elevator: 3+ complaints to the city in 24 months, above the 90th percentile for similar buildings")
        if not (el24 >= 3 or nyc_el) and (el24 or "elevator_complaints_6m_ge_1" in flags): pause.append("some elevator complaints, below the threshold")
        if mg6 >= 3: reasons.append(f"management: {mg6} tenant reports of serious problems in the last 6 months")
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
