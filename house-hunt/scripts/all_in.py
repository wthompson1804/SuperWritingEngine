"""All-in monthly cost, rebuilt on the master tables (plan v4, Part 4). Adds columns to data/master_units.csv.

all_in        = rent basis + required building fees + pet rent + parking fee + utilities not included in rent
all_in_gross  = the same with the gross rent (what a paying month costs), where a concession is known
Rent basis (Will): the net-effective rent where the terms are known; otherwise the listed price. A unit with any
concession language gets rent_asterisk = yes, and rent_terms columns say what the monthly rent is and when the
first full payment falls due (data/rent_terms.csv from scripts/rent_terms.py, when present).
Every line carries a basis: confirmed / stated / estimate / unknown. Unknown lines count as $0 and are listed in
all_in_unknown_lines so the page can show an asterisk. Cap: all_in <= $3,000 -> cost_gate = pass.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import DATA  # noqa: E402

CAP = 3000


def num(x):
    try:
        v = float(str(x).replace(",", "").replace("$", ""))
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def monthly_fees_from_text(text: str):
    """Sum the dollar amounts in a required-fees sentence that are monthly and not already inside the rent."""
    t = str(text)
    if not t or t.lower() in ("nan", "none"):
        return None, ""
    if re.search(r"included in (the )?(advertised )?rent", t, re.I):
        return 0.0, "stated as included in the advertised rent"
    tot, found = 0.0, False
    for m in re.finditer(r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)([^$;]{0,40})", t):
        amt, tail = float(m.group(1).replace(",", "")), m.group(2).lower()
        if re.search(r"one[- ]time|at move|per year|a year|annual|deposit|application|total shown", tail) or amt > 400:
            continue
        tot += amt; found = True
    return (tot, "parsed from the fee text") if found else (None, "fee exists, amount not published" if re.search(r"fee", t, re.I) else "")


def main():
    U = pd.read_csv(DATA / "master_units.csv", dtype=str, keep_default_na=False, low_memory=False)
    util = {}
    xw = pd.read_csv(DATA / "reference" / "building_crosswalk.csv", dtype=str).set_index("addr_key").building_id
    for f in glob.glob(str(DATA / "enriched" / "*.json")):
        e = json.load(open(f)); b = xw.get(e.get("addr_key"))
        if b is None:
            continue
        for kind in ("utilities_1br", "utilities_studio"):
            u = e.get(kind) or {}
            g = lambda k: (u.get(k) or {}).get("amount") if isinstance(u.get(k), dict) else None
            util[(b, kind)] = {"electric": g("electric"), "gas": g("gas"), "internet": g("internet")}
    rt = DATA / "rent_terms.csv"
    RT = pd.read_csv(rt, dtype=str, keep_default_na=False).drop_duplicates("listing_id").set_index("listing_id") if rt.exists() else pd.DataFrame()

    out = []
    for r in U.to_dict("records"):
        lines, unknown = [], []
        listed = num(r.get("live_price")) if r.get("live_status") == "changed" and num(r.get("live_price")) else num(r["listed_rent"])
        t = RT.loc[r["listing_id"]].to_dict() if len(RT) and r["listing_id"] in RT.index else {}
        net, gross = num(t.get("net_effective_monthly")), num(t.get("gross_monthly_rent"))
        has_offer = bool(t) and t.get("offer_type", "none") not in ("", "none") or bool(str(r.get("concession_text", "")).strip())
        rent_basis_val = net if net else listed
        rent_gross_val = gross if gross else (num(t.get("gross_if_listed_is_net")) if t.get("listed_price_is") == "net_effective" else None) or listed
        lines.append({"line": "rent (net-effective)" if net else "rent (as listed)", "amount": rent_basis_val,
                      "basis": "computed from stated terms" if net else "stated"})
        # required building fees: listing JSON + fee text from community page / evidence
        fee = 0.0; fee_known = False
        try:
            j = json.loads(r.get("other_monthly_fees_json") or "{}")
            skip = re.compile(r"deposit|application|one_time|one-time|security|lease|non_monthly|move|admin(?!istrative)|pet", re.I)
            if isinstance(j, dict):
                if num(j.get("required_total_min")) is not None:
                    fee, fee_known = num(j["required_total_min"]), True
                elif num(j.get("required_monthly_fees_min")) is not None:
                    fee, fee_known = num(j["required_monthly_fees_min"]), True
                else:
                    for k, val in j.items():
                        a = num(val)
                        if a is not None and 0 < a <= 400 and not skip.search(k):
                            fee += a; fee_known = True
            elif isinstance(j, list):
                for it in j:
                    a = num(it.get("amount")) if isinstance(it, dict) else None
                    if a and a <= 400 and not skip.search(str(it.get("name", ""))) and "month" in str(it.get("cadence", "month")).lower():
                        fee += a; fee_known = True
        except (ValueError, TypeError):
            pass
        ft, note = monthly_fees_from_text(r.get("required_fees_text", ""))
        if ft is not None:
            fee = max(fee, ft); fee_known = True
        if fee_known:
            lines.append({"line": "required building fees", "amount": round(fee), "basis": r.get("required_fees_text_basis") or "stated", "note": note})
        else:
            lines.append({"line": "required building fees", "amount": 0, "basis": "unknown", "note": note}); unknown.append("building fees")
        pet = num(r.get("pet_rent_monthly"))
        if pet is not None and pet <= 300:
            lines.append({"line": "pet rent", "amount": pet, "basis": r.get("pet_rent_monthly_basis", "stated")})
        else:
            lines.append({"line": "pet rent", "amount": 0, "basis": "unknown"}); unknown.append("pet rent")
        pk, ptype = num(r.get("parking_fee_monthly")), str(r.get("parking_type", "")).lower()
        if pk is not None and pk <= 600:
            lines.append({"line": "parking", "amount": pk, "basis": r.get("parking_fee_monthly_basis", "stated")})
        elif "street" in ptype and "garage" not in ptype:
            lines.append({"line": "parking (street)", "amount": 0, "basis": "stated"})
        else:
            lines.append({"line": "parking", "amount": 0, "basis": "unknown"}); unknown.append("parking fee")
        # utilities, minus what the rent includes
        inc = str(r.get("utilities_included", "")).lower()
        u = util.get((r["building_id"], "utilities_studio" if str(r["beds"]).startswith("0") else "utilities_1br"), {})
        for name, key, pat in [("electricity (est.)", "electric", r"electric"), ("gas (est.)", "gas", r"\bgas\b|\bheat\b|all utilities"),
                               ("internet (est.)", "internet", r"internet|wi-?fi|all utilities")]:
            amt = num(u.get(key))
            if re.search(pat, inc) or ("all utilities" in inc):
                lines.append({"line": name.replace(" (est.)", " (included in rent)"), "amount": 0, "basis": r.get("utilities_included_basis", "stated")})
            elif amt is not None:
                lines.append({"line": name, "amount": round(amt), "basis": "estimate"})
            else:
                lines.append({"line": name, "amount": 0, "basis": "unknown"}); unknown.append(key)
        extras = sum(l["amount"] or 0 for l in lines[1:])
        all_in = round((rent_basis_val or 0) + extras)
        out.append({"listing_id": r["listing_id"], "rent_basis": rent_basis_val, "rent_basis_kind": "net_effective" if net else "listed",
                    "rent_gross": rent_gross_val, "rent_asterisk": "yes" if has_offer else "",
                    "rent_listed_price_is": t.get("listed_price_is", ""), "rent_offer_text": t.get("offer_text", "") or r.get("concession_text", ""),
                    "rent_free_months": t.get("free_months", ""), "rent_lease_months": t.get("lease_months", ""),
                    "rent_first_full_payment_date": t.get("first_full_payment_date", ""), "rent_first_full_payment_note": t.get("first_full_payment_note", ""),
                    "rent_needs_call": t.get("needs_call", "yes" if has_offer and not t else ""),
                    "all_in": all_in, "all_in_gross": round((rent_gross_val or 0) + extras), "all_in_lines": json.dumps(lines),
                    "all_in_unknown_lines": "; ".join(unknown), "all_in_estimated_lines": "; ".join(l["line"] for l in lines if l["basis"] == "estimate"),
                    "cost_gate": "pass" if all_in <= CAP else "fail"})
    O = pd.DataFrame(out).set_index("listing_id")
    U = U.drop(columns=[c for c in O.columns if c in U.columns]).join(O, on="listing_id")
    U.to_csv(DATA / "master_units.csv", index=False)
    print(f"units {len(U)}; cost gate {U.cost_gate.value_counts().to_dict()}; rent asterisk {int((U.rent_asterisk == 'yes').sum())}; "
          f"rent terms file {'present' if len(RT) else 'absent'}")
    for k in ["building fees", "pet rent", "parking fee", "gas"]:
        print(f"  unknown {k}: {int(U.all_in_unknown_lines.str.contains(k).sum())}")
    print("  gross above cap while basis passes:", int(((U.cost_gate == "pass") & (pd.to_numeric(U.all_in_gross) > CAP)).sum()))


if __name__ == "__main__":
    main()
