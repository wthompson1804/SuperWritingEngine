"""A rating-based avoid standard for buildings outside New York City, calibrated against NYC official records.

Inputs (all optional except the first two; rerun as more ratings arrive):
  data/evidence/ratings_round1.csv, data/evidence/ratings_batch_*.csv   structured ratings, one row per source
  data/reference/evidence_batches/{all,round2}_candidate_buildings.csv  the building list
  data/evidence/nyc_records_flags.csv                                   NYC record flags per building
  data/avoid_buildings.csv                                              the current avoid decision and its reasons
Outputs:
  data/evidence/rating_standard.csv   per building: rating facts, proposed verdict (avoid / pause / ok /
                                      not_enough_data) and why
  docs/RATING_STANDARD.md             method, numbers, the rule, its weaknesses (regenerated from the data)
Nothing is fetched. Sources are never blended into one number: each building's "best" rating is the single source
with the most reviews; counts of recent review texts are summed across sources and labelled as such.
"""
import glob, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT

TODAY = pd.Timestamp("2026-11-15")
RNG = np.random.default_rng(20261115)
MIN_FULL, MIN_THIN = 20, 5          # reviews behind a star rating: >= 20 full weight, 5-19 thin, < 5 not judged
STALE_MONTHS = 12
NYC_ZIP = re.compile(r"^(100|101|102|103|104|111|112|113|114|116)\d\d$|^1100[45]$")


def family(s):
    s = str(s).lower()
    if "none_found" in s: return "none"
    if "zumper" in s: return "google_via_zumper"
    if "apartment list" in s or "apartmentlist" in s: return "apartment_list"
    if "openigloo" in s: return "openigloo"
    if "google" in s or "widget" in s or "own site" in s: return "own_site_widget"
    return "other"


def num(x):
    return pd.to_numeric(x, errors="coerce")


def load():
    fs = [DATA / "evidence/ratings_round1.csv"] + sorted(Path(p) for p in glob.glob(str(DATA / "evidence/ratings_batch_*.csv")))
    R = pd.concat([pd.read_csv(f, dtype=str).assign(ratings_file=f.name) for f in fs if f.exists()], ignore_index=True)
    R["family"] = R.rating_source.map(family)
    for c in ("rating_value", "rating_scale", "review_count", "reviews_read", "reviews_last_6_months", "negative_last_6_months", "negative_older"):
        R[c] = num(R[c])
    R["rating5"] = R.rating_value / R.rating_scale.fillna(5) * 5
    R["as_of"] = pd.to_datetime(R.as_of_date, errors="coerce")
    B = pd.concat([pd.read_csv(DATA / "reference/evidence_batches" / f, dtype=str).assign(round=n)
                   for f, n in (("all_candidate_buildings.csv", "1"), ("round2_candidate_buildings.csv", "2"))
                   if (DATA / "reference/evidence_batches" / f).exists()], ignore_index=True).drop_duplicates("addr_key")
    B["zip5"] = B.zip.str.split(".").str[0].str.zfill(5)
    B["region"] = np.where(B.zip5.str.match(NYC_ZIP) | B.pluto_bbl.notna(), "NYC", "outside NYC")
    return R, B, [f.name for f in fs if f.exists()]


def per_building(R, B):
    rows = []
    for k, g in R.groupby("addr_key"):
        rated = g[(g.family != "none") & g.rating5.notna()].copy()
        d = {"addr_key": k, "ratings_checked": "yes", "sources_with_rating": len(rated)}
        if len(rated):
            rated["rc"] = rated.review_count.fillna(0)
            b = rated.sort_values("rc", ascending=False).iloc[0]
            d.update(best_source=b.family, best_source_label=b.rating_source, rating=round(float(b.rating5), 2),
                     review_count=int(b.rc), rating_as_of=b.as_of_date, source_url=b.source_url,
                     rating_age_months=(round((TODAY - b.as_of).days / 30.4, 1) if pd.notna(b.as_of) else np.nan),
                     all_sources="; ".join(f"{r.family} {r.rating5:.1f} ({int(r.rc)})" for r in rated.itertuples()))
        d.update(reviews_read_all_sources=int(g.reviews_read.fillna(0).sum()), recent_reviews_read=int(g.reviews_last_6_months.fillna(0).sum()),
                 recent_negative=int(g.negative_last_6_months.fillna(0).sum()), older_negative=int(g.negative_older.fillna(0).sum()),
                 recent_tags=";".join(sorted({t for s in g.serious_issue_tags_last_6_months.dropna() for t in str(s).split(";") if t})))
        rows.append(d)
    P = B[["addr_key", "building_name", "city", "state", "zip5", "region", "round"]].merge(pd.DataFrame(rows), on="addr_key", how="left")
    P["ratings_checked"] = P.ratings_checked.fillna("no")
    return P


def nyc_targets(P):
    A = pd.read_csv(DATA / "avoid_buildings.csv", dtype=str)
    F = pd.read_csv(DATA / "evidence/nyc_records_flags.csv", dtype=str)
    fl = F[F.flag != "none"].groupby("addr_key").flag.apply(lambda s: ";".join(sorted(set(s))))
    P = P.merge(A[["addr_key", "avoid", "reasons"]], on="addr_key", how="left").merge(fl.rename("nyc_record_flags"), on="addr_key", how="left")
    P["has_nyc_records"] = P.addr_key.isin(F.addr_key)
    rs = P.reasons.fillna("")
    P["avoid_any"] = P.avoid.eq("yes")
    P["avoid_records_building"] = rs.str.contains(r"complaints to the city|city records", regex=True)   # elevator / management, from city records
    P["avoid_car_crime_only"] = P.avoid_any & rs.str.contains("car crime") & ~P.avoid_records_building & ~rs.str.contains("tenant reports")
    P["any_record_flag"] = P.nyc_record_flags.notna()
    P["mgmt_record_flag"] = P.nyc_record_flags.fillna("").str.contains(r"(?:heat_hot_water|pest|mold|class_c)\w*_6m_above_p90", regex=True)
    return P


def auc(pos, neg):
    """P(a flagged building has a LOWER rating than an unflagged one), ties count half. 0.5 = no relationship."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if not len(pos) or not len(neg):
        return np.nan
    d = pos[:, None] - neg[None, :]
    return float(((d < 0).sum() + 0.5 * (d == 0).sum()) / d.size)


def auc_ci(x, y, n=2000):
    x, y = np.asarray(x, float), np.asarray(y, bool)
    if y.sum() < 2 or (~y).sum() < 2:
        return (np.nan, np.nan)
    v = []
    for _ in range(n):
        i = RNG.integers(0, len(x), len(x))
        if y[i].sum() and (~y[i]).sum():
            v.append(auc(x[i][y[i]], x[i][~y[i]]))
    return tuple(np.round(np.percentile(v, [2.5, 97.5]), 2))


def sweep(x, y, grid):
    out = []
    for t in grid:
        pred = x <= t
        tp, fp, fn = int((pred & y).sum()), int((pred & ~y).sum()), int((~pred & y).sum())
        prec = tp / (tp + fp) if tp + fp else np.nan
        rec = tp / (tp + fn) if tp + fn else np.nan
        f1 = 2 * prec * rec / (prec + rec) if prec and rec and prec + rec else 0.0
        out.append(dict(threshold=t, flagged=tp + fp, true_pos=tp, precision=prec, recall=rec, f1=f1, share_flagged=float(pred.mean())))
    return pd.DataFrame(out)


def q(s):
    s = pd.Series(s).dropna()
    if not len(s):
        return "n=0"
    a = np.percentile(s, [25, 50, 75])
    return f"n={len(s)}, median {a[1]:.2f}, quartiles {a[0]:.2f} to {a[2]:.2f}, min {s.min():.1f}, max {s.max():.1f}"


def fmt(x, d=2):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        lines.append("| " + " | ".join(fmt(v) if isinstance(v, float) else str(v) for v in r) + " |")
    return "\n".join(lines)


def main():
    R, B, files = load()
    P = nyc_targets(per_building(R, B))
    rated = P.rating.notna()
    nyc, out = P.region.eq("NYC"), P.region.eq("outside NYC")
    chk = P.ratings_checked.eq("yes")

    # ---------- NYC calibration
    C = P[nyc & rated & P.has_nyc_records].copy()
    targets = [("avoid_records_building", "record-based avoid (elevator or management, from city records)"),
               ("any_record_flag", "any city-record flag (softer: includes single elevator complaints)"),
               ("mgmt_record_flag", "management record flag (heat, pests, mold or class C above the 90th percentile, last 6 months)"),
               ("avoid_any", "avoid for any reason (mostly car crime near the address, which reviews cannot see)")]
    cal, sweeps = [], {}
    for col, label in targets:
        for name, sub in (("all rated", C), ("3+ reviews", C[C.review_count >= 3]), (f"{MIN_THIN}+ reviews", C[C.review_count >= MIN_THIN])):
            y = sub[col].to_numpy(bool); x = sub.rating.to_numpy(float)
            a = auc(x[y], x[~y]); lo, hi = auc_ci(x, y)
            cal.append(dict(target=label, subset=name, buildings=len(sub), flagged=int(y.sum()),
                            median_rating_flagged=(float(np.median(x[y])) if y.sum() else np.nan),
                            median_rating_not_flagged=(float(np.median(x[~y])) if (~y).sum() else np.nan), auc=a, auc_95ci=f"{lo} to {hi}"))
            if name == "all rated":
                sweeps[col] = sweep(x, y, [1.5, 2.0, 2.5, 3.0, 3.5, 4.0])
    cal = pd.DataFrame(cal)
    main_row = cal[(cal.target == targets[0][1]) & (cal.subset == "all rated")].iloc[0]
    lo, hi = [float(v) for v in main_row.auc_95ci.split(" to ")] if "nan" not in main_row.auc_95ci else (np.nan, np.nan)
    weak = bool(np.isnan(main_row.auc) or lo <= 0.5)
    sw = sweeps["avoid_records_building"]
    best = sw.sort_values(["f1", "precision"], ascending=False).iloc[0]
    # recent-negative share
    Cn = C[C.recent_reviews_read > 0]
    older_neg = C.assign(any_neg=(C.recent_negative + C.older_negative) > 0)
    neg_tab = older_neg.groupby("avoid_records_building").agg(buildings=("any_neg", "size"), with_any_negative_text=("any_neg", "sum"),
                                                              with_recent_review=("recent_reviews_read", lambda s: int((s > 0).sum())),
                                                              with_recent_negative=("recent_negative", lambda s: int((s > 0).sum()))).reset_index()

    # ---------- inside vs outside
    comp = []
    for name, m in (("NYC", nyc), ("outside NYC", out)):
        s = P[m & chk]
        r = s[s.rating.notna()]
        comp.append(dict(region=name, buildings_checked=len(s), with_any_rating=len(r), share_with_rating=len(r) / len(s) if len(s) else np.nan,
                         median_rating=r.rating.median(), q1=r.rating.quantile(.25), q3=r.rating.quantile(.75),
                         median_review_count=r.review_count.median(), with_20plus_reviews=int((r.review_count >= MIN_FULL).sum()),
                         with_5plus_reviews=int((r.review_count >= MIN_THIN).sum()),
                         with_recent_review_text=int((s.recent_reviews_read > 0).sum()),
                         median_rating_age_months=r.rating_age_months.median()))
    comp = pd.DataFrame(comp)
    bysrc = P[rated].groupby(["region", "best_source"]).agg(buildings=("rating", "size"), median_rating=("rating", "median"),
                                                            q1=("rating", lambda s: s.quantile(.25)), q3=("rating", lambda s: s.quantile(.75)),
                                                            median_reviews=("review_count", "median"),
                                                            median_age_months=("rating_age_months", "median")).reset_index()

    # ---------- thresholds per source family (quantile mapping from the NYC calibration, or the lower quartile when weak)
    G = P[rated & (P.review_count >= MIN_FULL) & P.best_source.isin(["google_via_zumper", "own_site_widget"])].rating
    G_out = P[out & rated & (P.review_count >= MIN_FULL) & P.best_source.isin(["google_via_zumper", "own_site_widget"])].rating
    base_rate = float(P[nyc & P.has_nyc_records].avoid_records_building.mean())
    if len(G_out) >= 8:
        g_pause = float(np.round(np.percentile(G_out, 25), 1))
        g_low = float(np.round(np.percentile(G_out, max(5.0, base_rate * 100)), 1))
    else:
        g_pause, g_low = 3.8, 3.5
    g_low = min(g_low, g_pause - 0.3)
    thr = {"google_via_zumper": (g_low, g_pause), "own_site_widget": (g_low, g_pause),
           "openigloo": (2.0, 2.5), "apartment_list": (2.5, 3.5), "other": (2.5, 3.5)}

    def verdict(r):
        if r.ratings_checked != "yes":
            return "not_enough_data", "ratings not collected yet for this building"
        why = []
        rn, rr, tags = int(r.recent_negative or 0), int(r.recent_reviews_read or 0), (r.recent_tags if isinstance(r.recent_tags, str) else "")
        has = pd.notna(r.rating)
        n = int(r.review_count) if has else 0
        low, pause = thr.get(r.best_source, (2.5, 3.5)) if has else (None, None)
        stale = has and pd.notna(r.rating_age_months) and r.rating_age_months > STALE_MONTHS
        base = f"{r.best_source} {r.rating:.1f} from {n} reviews, as of {r.rating_as_of}" if has else "no rating shown on any allowed page"
        if rn >= 3:
            return "avoid", f"{rn} negative reviews in the last 6 months ({tags or 'no issue tag'}); {base}"
        if has and n >= MIN_FULL and r.rating <= low and rn >= 2 and not stale:
            return "avoid", f"rating at or below {low} with {rn} negative reviews in the last 6 months; {base}"
        if rn >= 1:
            why.append(f"{rn} negative review(s) in the last 6 months ({tags or 'no issue tag'})")
        if has and n >= MIN_THIN and r.rating <= pause:
            why.append(f"rating at or below the pause line {pause}" + (" (thin: under 20 reviews)" if n < MIN_FULL else ""))
        if why:
            return "pause", "; ".join(why) + f"; {base}" + ("; rating figure is over 12 months old" if stale else "")
        if not has or n < MIN_THIN:
            if rr >= 3:
                return "ok", f"{rr} review texts from the last 6 months read, none negative; {base}"
            return "not_enough_data", f"{base}; under {MIN_THIN} reviews and under 3 recent review texts"
        if n < MIN_FULL and rr < 3:
            return "not_enough_data", f"{base}; {n} reviews is too few to clear a building (need {MIN_FULL}, or 3 recent review texts)"
        return "ok", f"{base}; above the pause line {pause}, no negative review in the last 6 months among {rr} recent texts read" + \
                     ("; STALE: the rating is over 12 months old and no recent review text could be read, so this says nothing about the last 6 months" if stale and rr == 0 else "")
    V = P.apply(verdict, axis=1, result_type="expand")
    P["rating_verdict"], P["rating_verdict_why"] = V[0], V[1]
    P["rating_stale"] = np.where(P.rating_age_months > STALE_MONTHS, "yes", np.where(P.rating.notna(), "no", ""))
    P["rule_applies"] = np.where(out, "yes (outside NYC)", "shown for comparison only; NYC uses city records")
    cols = ["addr_key", "building_name", "city", "state", "zip5", "region", "round", "ratings_checked", "best_source", "best_source_label", "rating",
            "review_count", "rating_as_of", "rating_age_months", "rating_stale", "all_sources", "reviews_read_all_sources", "recent_reviews_read",
            "recent_negative", "older_negative", "recent_tags", "rating_verdict", "rating_verdict_why", "rule_applies", "source_url",
            "has_nyc_records", "avoid", "reasons", "nyc_record_flags"]
    P[cols].to_csv(DATA / "evidence/rating_standard.csv", index=False)

    vt = P[chk].groupby(["region", "rating_verdict"]).size().unstack(fill_value=0).reset_index()
    # how the rule would have done in NYC, against records
    N = P[nyc & chk & P.has_nyc_records]
    xt = N.groupby(["rating_verdict", "avoid_records_building"]).size().unstack(fill_value=0)
    xt.columns = ["records: not avoid" if not c else "records: avoid" for c in xt.columns]
    xt = xt.reset_index()
    usable = lambda m: int((m & rated & (P.review_count >= MIN_THIN)).sum())

    L = []
    A = L.append
    A("# Rating standard for buildings outside New York City\n")
    A(f"Generated by `scripts/rating_standard.py` on {TODAY.date()} from: {', '.join('`'+f+'`' for f in files)}, "
      "`nyc_records_flags.csv`, `avoid_buildings.csv`. Rerun the script when more `ratings_batch_*.csv` files arrive; every number below is recomputed.\n")
    A("## Bottom line\n")
    A(f"- **Ratings cannot stand in for city records.** Among NYC buildings that have both a rating and city records, the star rating "
      f"{'does not separate' if weak else 'separates'} record-based avoid buildings from the rest "
      f"(AUC {fmt(main_row.auc)}, 95% interval {main_row.auc_95ci}; 0.5 means no relationship; {int(main_row.flagged)} flagged of {int(main_row.buildings)}).")
    A(f"- **The ratings are thin and old.** {int(comp.with_any_rating.sum())} of {int(comp.buildings_checked.sum())} checked buildings show any rating. "
      f"Outside NYC the usual source is the Google figure that Zumper displays, which Zumper last refreshed a median of "
      f"{fmt(float(P[out & rated].rating_age_months.median()), 0)} months ago; "
      f"{int(comp[comp.region == 'outside NYC'].with_recent_review_text.iloc[0])} outside-NYC buildings had a readable review from the last 6 months.")
    A("- **So the rule below is a screen, not a verdict.** It can raise a flag (\"pause\") and, rarely, an avoid. It cannot prove a suburban building clean: "
      "\"ok\" on an old rating says nothing about the last 6 months, and most buildings land in \"not enough data\".\n")
    A("## 1. What was collected\n")
    A("One row per building per source: stars, review count, date of the figure, review texts read, how many are from the last 6 months "
      "(on or after 2026-05-15), how many of those are negative, and serious-issue tags. Negative = 1 or 2 stars, or (3 stars or no star value) text naming a serious issue.\n")
    A("| Source | What the page gives | Limits |\n|---|---|---|")
    A("| Google rating shown on Zumper building pages | Google average and count, 8 review texts | Zumper pulled the figures between late 2024 and early 2025 and shows only the 8 *highest rated* texts, so recent and negative reviews are invisible |")
    A("| Apartment List | average, count and dated verified-renter reviews | 1 to 4 reviews per building; most pages have none |")
    A("| Openigloo (NYC only) | average, count, 2 review texts with relative ages | median 1 review per building; no per-review stars |")
    A("| Building's own site widget | Google average and count, a few recent texts | only a few sites embed one |")
    A("| Trulia building pages | no rating | |\n")
    A("## 2. Inside vs outside NYC\n")
    A(md_table(comp.round(2)) + "\n")
    A("By source of each building's best rating (the one with the most reviews):\n")
    A(md_table(bysrc.round(2)) + "\n")
    A(f"Buildings with a rating resting on at least {MIN_THIN} reviews (the minimum this standard will read): **{usable(nyc)} in NYC, {usable(out)} outside NYC**. "
      f"With at least {MIN_FULL}: {int((nyc & rated & (P.review_count >= MIN_FULL)).sum())} in NYC, {int((out & rated & (P.review_count >= MIN_FULL)).sum())} outside.\n")
    A("**The delta is mostly a difference of instruments, not of buildings.** NYC ratings are Openigloo tenant reviews (few, critical, median near 3). "
      "Outside NYC they are Google ratings (many, lenient, median above 4, and they mix residents with visitors and prospects). "
      "A 3.5 means \"about average\" on Openigloo and \"bottom of the pack\" on Google. Thresholds therefore have to be set per source, by position in that source's own distribution, never on a shared star scale.\n")
    A("## 3. Do ratings track the NYC record-based decision?\n")
    A(f"Calibration set: NYC buildings with city records and a rating ({len(C)} buildings). AUC = chance that a flagged building has the lower rating; 0.5 = none, 1.0 = perfect.\n")
    A(md_table(cal.round(2)) + "\n")
    A("Thresholds against the record-based avoid (\"flag when rating is at or below t\"), all rated NYC buildings:\n")
    A(md_table(sw.round(2)) + "\n")
    A(f"Best single threshold by F1: rating at or below {best.threshold} flags {int(best.flagged)} buildings, {int(best.true_pos)} of them record-based avoids "
      f"(precision {fmt(best.precision)}, recall {fmt(best.recall)}). The base rate of record-based avoids among NYC buildings with records is {base_rate:.0%}, "
      f"so a threshold is only useful if its precision is well above that.\n")
    A("Negative review text vs the record-based avoid (NYC, rated buildings):\n")
    A(md_table(neg_tab) + "\n")
    A(("**Plainly: the relationship is weak.** " if weak else "**The relationship is measurable but rests on few buildings.** ") +
      f"Only {len(Cn)} calibration buildings had any review text from the last 6 months, so the \"recent-negative share\" cannot be measured as a distribution. "
      "Reasons: Openigloo ratings rest on 1 to 3 reviews; the record-based avoids are mostly elevator complaints, which a building-wide star average barely reflects; "
      "and most NYC avoids are car crime near the address, which no review source sees.\n")
    A("## 4. Proposed rule for buildings outside NYC\n")
    A("Applied per building, in this order. Review counts refer to the single best source; recent counts are review texts dated in the last 6 months, summed over sources.\n")
    A("| Outcome | Condition |\n|---|---|")
    A("| **avoid** | 3 or more negative reviews in the last 6 months (the plan's existing management test, now counted in a structured way); **or** a rating at or below the low line "
      f"on {MIN_FULL}+ reviews, not older than {STALE_MONTHS} months, together with 2 or more negative reviews in the last 6 months |")
    A(f"| **pause** | 1 or 2 negative reviews in the last 6 months; **or** a rating at or below the pause line on {MIN_THIN}+ reviews |")
    A(f"| **ok** | rating above the pause line on {MIN_FULL}+ reviews with no negative review in the last 6 months; or 3+ recent review texts, none negative. Marked STALE when the rating is over {STALE_MONTHS} months old and no recent text was readable |")
    A(f"| **not_enough_data** | no rating; or fewer than {MIN_THIN} reviews; or {MIN_THIN} to {MIN_FULL - 1} reviews with fewer than 3 recent texts (too few to clear a building) |\n")
    A("Lines per source (stars out of 5):\n")
    A("| Source | Low line | Pause line | Basis |\n|---|---|---|---|")
    A(f"| Google (via Zumper or own-site widget) | {g_low} | {g_pause} | pause = lower quartile of outside-NYC Google ratings with {MIN_FULL}+ reviews (n={len(G_out)}); "
      f"low = the percentile equal to the NYC record-based avoid base rate ({base_rate:.0%}), at least 0.3 below the pause line |")
    A("| Openigloo | 2.0 | 2.5 | lower quartile of NYC Openigloo ratings; not used outside NYC |")
    A("| Apartment List, other | 2.5 | 3.5 | judgment; these almost never reach the review minimum |\n")
    A(f"**Why {MIN_FULL} and {MIN_THIN} reviews.** Star ratings within one building typically spread about 1.3 to 1.5 stars. The average of 5 reviews is then uncertain by more than a star "
      f"either way (95%), which cannot tell a 3.5 building from a 4.5 one; at {MIN_FULL} reviews it is about 0.6 stars, enough to place a building below or above the pause line. "
      "Below 5, a rating is one or two people's experience and is reported, not judged.\n")
    A("**Why the last 6 months carry the avoid.** Will's management rule judges the last 6 months. An all-time star average cannot show a recent change of manager or a new outage problem, "
      "so a low average alone only earns \"pause\".\n")
    A("### What the rule gives today\n")
    A(md_table(vt) + "\n")
    A("Check against NYC records (the rule applied to NYC buildings, for comparison only):\n")
    A(md_table(xt) + "\n")
    A("## 5. Weaknesses\n")
    A("1. **Not validated.** The NYC calibration does not show that ratings predict record-based problems, so the lines are distribution-based (bottom quartile), not accuracy-based. Treat \"pause\" as \"ask on the tour\", not as evidence.")
    A("2. **Stale Google figures.** Zumper's copies date from late 2024 to early 2025. A building can have changed manager since. Google itself is off limits to us (Google Maps robots rules), so the live figure and the newest reviews must be read by hand on a phone.")
    A("3. **Selection in the texts.** Zumper shows the eight highest-rated reviews. Zero negatives among them means nothing; the rule therefore never counts them as \"recent, none negative\" unless they are actually dated in the last 6 months.")
    A("4. **Different instruments inside and outside NYC.** No building has both an Openigloo and a meaningful Google rating, so the two scales cannot be cross-walked directly; the per-source quartile is the only link.")
    A("5. **Car break-ins and elevator outages are not visible in ratings.** Reviews rarely mention them, and star averages do not move on them. Outside NYC these two deal-breakers rest on dated reports and, where they exist, official records (`data/evidence/non_nyc_records.csv`: NJ housing-inspection reports for New Jersey buildings, Jersey City police incidents).")
    A("6. **Small numbers.** Every figure here rests on tens of buildings. Rerun after round 2.")
    A("7. **Keyword tagging.** Serious-issue tags come from keyword matching with a simple negation guard; Openigloo has no per-review stars, so its \"negative\" count means a serious issue named under Cons.\n")
    A("## 6. What would make this a real standard\n")
    A("- Someone reads the live Google listing for each outside-NYC finalist and records the current rating, count, and the newest 10 reviews with dates (ten minutes per building).")
    A("- For New Jersey, use the state housing-inspection reports as the record-based test (open violations at the last inspection, repeat reinspections), as NYC uses HPD.")
    A("- Keep \"no avoid flag outside NYC\" worded as \"not checked against records\", not \"clean\".\n")
    (ROOT / "docs/RATING_STANDARD.md").write_text("\n".join(L))
    print(comp.round(2).to_string()); print(cal.round(2).to_string()); print(sw.round(2).to_string()); print(vt.to_string()); print(xt.to_string())
    print("usable (>=5 reviews): NYC", usable(nyc), "outside", usable(out), "| weak:", weak, "| google lines", g_low, g_pause, "n", len(G_out))


if __name__ == "__main__":
    main()
