"""Crime benchmarks so a neighborhood's rate can be read against the US, the NY metro area and its own county.

US: FBI Crime Data Explorer national monthly rates (per 100,000), summed over a calendar year -> per 1,000.
Metro: population-weighted rate over every FBI-reporting agency in the search-grid counties (one definition).
County / borough: the same, per county. NYC precincts are also compared with NYC citywide on NYPD's own counts,
because NYPD complaint categories (NY Penal Law) are close to, not identical with, FBI definitions.
Outputs: data/reference/crime_benchmarks.csv, data/neighborhood_safety.csv, docs/SAFETY_BASIS.md
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA, ROOT, get_json

API = "https://api.usa.gov/crime/fbi/cde/summarized/national/{}"
OFF = {"violent": "V", "property": "P", "motor_vehicle_theft": "motor-vehicle-theft"}


def us_rates():
    out = {}
    for k, code in OFF.items():
        js, meta = get_json(API.format(code), "fbi_cde_national", params={"from": "01-2023", "to": "12-2025"})
        m = js["offenses"]["rates"]["United States Offenses"]
        for y in (2023, 2024, 2025):
            vals = [v for mk, v in m.items() if mk.endswith(str(y))]
            if len(vals) == 12:
                out[(y, k)] = (round(sum(vals) / 100, 2), meta["url"])
    return out


def main():
    rows = []
    us = us_rates()
    for (y, k), (v, url) in us.items():
        rows.append({"scope": "United States", "year": y, "measure": k, "per_1000": v, "source": "fbi_cde national", "source_url": url})
    c = pd.read_csv(DATA / "reference" / "crime_agencies.csv", low_memory=False)
    f = c[(c.source == "fbi_cde") & (c.months_reported == 12) & c.population.gt(0) & c.violent_per_1000.notna()].copy()
    f = f[~f.notes.fillna("").str.contains("flag|implausible|under half", case=False)]
    f = f[~f.agency_name.str.contains("New York City Police", case=False) | True]
    for y, g in f.groupby("year"):
        for k in OFF:
            rows.append({"scope": "NY metro (all FBI-reporting agencies in the 2-hour search area)", "year": y, "measure": k,
                         "per_1000": round(g[k].sum() / g.population.sum() * 1000, 2), "source": "fbi_cde agencies, population-weighted",
                         "source_url": "data/reference/crime_agencies.csv"})
        for cty, gg in g.groupby(["state", "county"]):
            for k in OFF:
                rows.append({"scope": f"county: {cty[1]}, {cty[0]}", "year": y, "measure": k,
                             "per_1000": round(gg[k].sum() / gg.population.sum() * 1000, 2), "source": "fbi_cde agencies, population-weighted",
                             "source_url": "data/reference/crime_agencies.csv"})
    n = c[(c.source == "nypd_complaints") & c.population.gt(0)]
    for y, g in n.groupby("year"):
        for k in OFF:
            rows.append({"scope": "New York City (NYPD complaint categories, all precincts)", "year": y, "measure": k,
                         "per_1000": round(g[k].sum() / g.population.sum() * 1000, 2), "source": "nypd_complaints", "source_url": "data/reference/crime_agencies.csv"})
    bm = pd.DataFrame(rows); bm.to_csv(DATA / "reference" / "crime_benchmarks.csv", index=False)

    def b(scope_prefix, k, year=None):
        x = bm[bm.scope.str.startswith(scope_prefix) & (bm.measure == k)]
        if year is not None and (x.year == year).any():
            x = x[x.year == year]
        return x.sort_values("year").per_1000.iloc[-1] if len(x) else np.nan

    u = pd.read_csv(DATA / "units.csv", low_memory=False); u = u[u.unit_status == "pass"]
    recs = []
    for hid, g in u.groupby("hood_id"):
        cl = json.loads(g.crime_latest.dropna().iloc[0]) if g.crime_latest.notna().any() else {}
        src, yr = g.crime_source.iloc[0], cl.get("year")
        county = str(g.hood_area.iloc[0]).replace(" County", ""); st = g.state.iloc[0]
        nyc = src == "nypd_complaints"
        r = {"hood_id": hid, "hood": g.hood.iloc[0], "area": county, "state": st, "units": len(g), "police": g.police_agency.iloc[0],
             "geography": g.police_geography.iloc[0], "crime_source": src, "crime_year": yr}
        for k in OFF:
            v = cl.get(f"{k}_per_1000"); r[k] = v
            r[f"{k}_vs_us"] = round(v / b("United States", k, yr), 2) if v is not None else np.nan
            r[f"{k}_vs_metro"] = round(v / b("NY metro", k, yr), 2) if v is not None else np.nan
            loc = b("New York City", k, yr) if nyc else b(f"county: {county}, {st}", k, yr)
            r[f"{k}_vs_local"] = round(v / loc, 2) if v is not None and loc and not np.isnan(loc) else np.nan
        recs.append(r)
    S = pd.DataFrame(recs)
    S.to_csv(DATA / "neighborhood_safety.csv", index=False)
    print(bm[bm.scope.str.startswith(("United", "NY metro", "New York City"))].pivot_table(index=["scope", "year"], columns="measure", values="per_1000").to_string())
    print(S[["violent", "violent_vs_us", "violent_vs_metro", "violent_vs_local", "motor_vehicle_theft_vs_us"]].describe().round(2).to_string())


if __name__ == "__main__":
    main()
