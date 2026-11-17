"""Second trawl, step 6: the apartments that would be shown if they had a reviewed verdict, and the counts by area.

  python3 scripts/trawl2_needs_review.py                  writes out/trawl2_needs_review*.csv (after scripts/run_all.py)
  python3 scripts/trawl2_needs_review.py --counts BEFORE   also prints the before -> after counts table, BEFORE being a
                                                           folder holding the earlier listings.csv and ranked_units.csv

"Would be shown if it had a verdict" (CLAUDE.md, "Reviewed verdicts are required"): ranked (passes every gate and the
evidence rules: data/ranked_units.csv), not an avoid building, listed base rent at most $2,200 (the rent as it now
stands: the live price where a re-read found one), at most one open item (rank.py: open_items), and no current
showable verdict in data/evidence/review_verdicts.csv (verdicts.unreviewed). A unit whose verdict is current is
"shown now". The per-building cap of 8 and the thin-neighborhood rule are not applied here (they act on what is
reviewed); `rank_shown` says whether rank.py would show the unit today, `nth_in_building` its place in its building.
A building with no evidence rows cannot be shown even with a verdict: `building_has_evidence` says which need an
evidence pass first.

Priority: 1 = at most $2,000 in a priority area (New Jersey, Brooklyn, Connecticut, Long Island, Long Island City);
2 = at most $2,000 elsewhere; 3 = $2,001 to $2,200.

Three files for three reviewers, by state (out/trawl2_needs_review_{nj,ct,ny}.csv). Whole buildings stay together, so
no two reviewers read the same building's evidence. Reads only; writes nothing in data/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT  # noqa: E402

OUT = ROOT / "out"
PRIORITY_AREAS = ("NJ", "CT", "Brooklyn", "LIC", "Long Island")
AREAS = ("NJ", "CT", "Brooklyn", "LIC", "Long Island", "Queens other", "rest")
LIC_ZIPS = {"11101", "11109", "11120"}
QUEENS_110 = {"11004", "11005"}                  # Glen Oaks / Floral Park, Queens side; the rest of 110xx is Nassau


def area_of(state, zip5, city="", hood_area="", hood=""):
    """NJ / CT / Brooklyn / LIC / Long Island / Queens other / rest, from the state, ZIP and (where present) the
    neighborhood assignment. Long Island is Nassau and Suffolk; LIC is ZIP 11101 / 11109 / 11120 or the neighborhood."""
    st, z = str(state or "").upper(), str(zip5 or "").strip()[:5]
    ha, hd, c = str(hood_area or ""), str(hood or ""), str(city or "").strip().lower()
    if st == "NJ":
        return "NJ"
    if st == "CT":
        return "CT"
    if st != "NY":
        return "rest"
    if ha in ("Nassau County", "Suffolk County"):
        return "Long Island"
    if ha == "Brooklyn" or c == "brooklyn" or z.startswith("112"):
        return "Brooklyn"
    queens = ha == "Queens" or z in QUEENS_110 or z[:3] in ("111", "113", "114", "116")
    if queens and (z in LIC_ZIPS or "long island city" in hd.lower() or "hunters point" in hd.lower() or c == "long island city"):
        return "LIC"
    if queens:
        return "Queens other"
    if (z[:3] in ("115", "117", "118", "119") or (z[:3] == "110" and z not in QUEENS_110)) and not ha:
        return "Long Island"
    return "rest"


def rent_now(R):
    lp = pd.to_numeric(R.get("live_price"), errors="coerce")
    live = R.get("live_status", pd.Series("", index=R.index)).isin(["live", "changed"])
    return lp.where(live & lp.notna(), pd.to_numeric(R.listed_rent, errors="coerce"))


def load_ranked(path):
    R = pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)
    R["rent"] = rent_now(R)
    R["area"] = [area_of(*x) for x in zip(R.state, R.get("zip5", R.get("zip", "")), R.city, R.get("hood_area", ""), R.get("hood", ""))]
    R["open_n"] = pd.to_numeric(R.open_items, errors="coerce").fillna(0)
    R["ev_n"] = pd.to_numeric(R.get("evidence_rows"), errors="coerce").fillna(0)
    R["would_show"] = (R.get("ev_avoid", "") != "yes") & (R.open_n <= 1) & (R.rent <= 2200)
    return R


def current_verdict(R):
    import verdicts
    pend = dict(verdicts.unreviewed(R))
    return R.listing_id.map(lambda l: l not in pend)


def counts(L_path, R_path, verdict_current=None):
    """Area x {<= 2000, <= 2200} counts: listings passing the gate, ranked, shown now (verdict present), waiting."""
    L = pd.read_csv(L_path, dtype=str, keep_default_na=False, low_memory=False, usecols=["state", "zip5", "city", "listed_rent", "gate_status"])
    L["rent"] = pd.to_numeric(L.listed_rent, errors="coerce")
    L["area"] = [area_of(s, z, c) for s, z, c in zip(L.state, L.zip5, L.city)]
    R = load_ranked(R_path)
    vc = current_verdict(R) if verdict_current is None else verdict_current(R)
    R["shown_now"] = (R.shown == "True") & vc
    R["waiting"] = R.would_show & ~vc
    rows = []
    for lim in (2000, 2200):
        for a in AREAS + ("all",):
            l_ = L[(L.rent <= lim) & ((L.area == a) | (a == "all"))]
            r_ = R[(R.rent <= lim) & ((R.area == a) | (a == "all"))]
            rows.append({"limit": lim, "area": a, "pass_gate": int((l_.gate_status == "pass").sum()), "ranked": len(r_),
                         "shown_now": int(r_.shown_now.sum()), "waiting": int(r_.waiting.sum())})
    return pd.DataFrame(rows)


def needs_review():
    R = load_ranked(DATA / "ranked_units.csv")
    R["verdict_current"] = current_verdict(R)
    import verdicts
    VU = verdicts.by_unit()
    W = R[R.would_show & ~R.verdict_current].copy()
    W["priority"] = [1 if (r <= 2000 and a in PRIORITY_AREAS) else (2 if r <= 2000 else 3) for r, a in zip(W.rent, W.area)]
    W["verdict_state"] = W.listing_id.map(lambda l: "stale: evidence changed since the verdict" if l in VU else "no verdict")
    W["open_item"] = W.confirm_what.where(W.open_n >= 1, "")
    W["open_item_why"] = W.confirm_why.where(W.open_n >= 1, "")
    W["building_has_evidence"] = (W.ev_n > 0).map({True: "yes", False: "no"})
    W["unit_key"] = W.listing_id
    W["listed_rent"] = W.rent.round(0).astype("Int64")
    W["rank_shown"] = W.shown
    cols = ["priority", "unit_key", "building_id", "building", "address", "unit", "city", "state", "area", "listed_rent", "url", "source_site",
            "building_has_evidence", "evidence_rows", "open_item", "open_item_why", "verdict_state", "hood", "rank_score", "rank_shown", "nth_in_building"]
    W["building"] = W.building_name
    W["nth_in_building"] = W.groupby("building_id").rank_score.rank(method="first", ascending=False).astype(int)
    W = W.sort_values(["priority", "state", "building_id", "nth_in_building"])[cols]
    OUT.mkdir(exist_ok=True)
    W.to_csv(OUT / "trawl2_needs_review.csv", index=False)
    files = {}
    for st, name in (("NJ", "nj"), ("CT", "ct"), ("NY", "ny")):
        part = W[W.state == st] if st != "NY" else W[~W.state.isin(["NJ", "CT"])]
        part.to_csv(OUT / f"trawl2_needs_review_{name}.csv", index=False)
        files[name] = part
    # one building, one file
    owners = pd.concat([f.assign(_f=n)[["building_id", "_f"]] for n, f in files.items()]).drop_duplicates()
    assert not owners.building_id.duplicated().any(), "a building sits in two reviewer files"
    print(f"needs review: {len(W)} units in {W.building_id.nunique()} buildings; by priority {W.priority.value_counts().sort_index().to_dict()}")
    print(f"  without evidence rows (an evidence pass is needed before a verdict can show them): {int((W.building_has_evidence == 'no').sum())} units, "
          f"{W[W.building_has_evidence == 'no'].building_id.nunique()} buildings")
    for n, f in files.items():
        print(f"  {n}: {len(f)} units, {f.building_id.nunique()} buildings, by priority {f.priority.value_counts().sort_index().to_dict()}, "
              f"no evidence {int((f.building_has_evidence == 'no').sum())}")
    return W


if __name__ == "__main__":
    needs_review()
    if "--counts" in sys.argv:
        before = Path(sys.argv[sys.argv.index("--counts") + 1])
        # the earlier run passed scripts/check_registry.py, so every unit it showed had a current verdict then (the
        # fingerprint is recomputed with today's crosswalk, which no longer matches a few of those buildings)
        B = counts(before / "listings.csv", before / "ranked_units.csv", verdict_current=lambda R: current_verdict(R) | (R.shown == "True"))
        A = counts(DATA / "listings.csv", DATA / "ranked_units.csv")
        T = B.merge(A, on=["limit", "area"], suffixes=("_before", "_after"))
        print(T.to_string(index=False))
        T.to_csv(OUT / "trawl2_counts_before_after.csv", index=False)
