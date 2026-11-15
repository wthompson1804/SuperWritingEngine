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
import parsers  # noqa: E402

CAP = 3000


def num(x):
    try:
        v = float(str(x).replace(",", "").replace("$", ""))
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def monthly_fees_from_text(text: str, unit: str = ""):
    """Required monthly fees in one fee sentence (scripts/parsers.py; independent check W9)."""
    return parsers.monthly_fees_from_text(text, unit)


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
        listed_old = num(r["listed_rent"])
        live = num(r.get("live_price")) if r.get("live_status") == "changed" and num(r.get("live_price")) else None
        listed = live or listed_old
        t = RT.loc[r["listing_id"]].to_dict() if len(RT) and r["listing_id"] in RT.index else {}
        net, gross = num(t.get("net_effective_monthly")), num(t.get("gross_monthly_rent"))
        gross_if_net = num(t.get("gross_if_listed_is_net"))
        offer = bool(t) and t.get("offer_type", "none") not in ("", "none")
        price_note = ""
        if live and listed_old and abs(live - listed_old) > 0.5:
            # rent_terms.csv was computed on the stored price: re-base its figures on the live price (W13)
            k = live / listed_old
            net, gross, gross_if_net = (round(v * k) if v else v for v in (net, gross, gross_if_net))
            price_note = f"price changed at the live check: ${listed_old:g} -> ${live:g}"
        ev_offer = str(r.get("concession_text_evidence", "")).strip()
        has_offer = offer or bool(str(r.get("concession_text", "")).strip()) or bool(ev_offer)
        # "net-effective" only when an offer really changes the monthly figure (no-offer rows also carry a net = listed)
        is_net = offer and net is not None and (abs(net - (listed or 0)) > 0.5 or t.get("listed_price_is") == "net_effective")
        rent_basis_val = net if is_net else listed
        rent_gross_val = (gross if offer and gross else None) or (gross_if_net if t.get("listed_price_is") == "net_effective" else None) or listed
        lines.append({"line": "rent (net-effective)" if is_net else "rent (as listed)", "amount": rent_basis_val,
                      "basis": "computed from stated terms" if is_net else ("live check" if live else "stated"), "note": price_note})
        # required building fees: the listing's fee lines, and each fee sentence from the community page / evidence.
        # Sentences are alternatives (several sources describing the same fees), so the largest reading is used, never a sum.
        fj = parsers.fees_from_json(r.get("other_monthly_fees_json"), r.get("unit", ""))
        cands, fee_notes = [], []
        if fj["fee"] is not None:
            cands.append((fj["fee"], fj["fee_note"] or "the listing's fee lines", "stated"))
        elif fj["fee_note"]:
            fee_notes.append(fj["fee_note"])
        for seg in [x for x in str(r.get("required_fees_text", "")).split(" || ") if x.strip()]:
            ft, note = monthly_fees_from_text(seg, r.get("unit", ""))
            if ft is not None:
                cands.append((ft, note, r.get("required_fees_text_basis") or "stated"))
            elif note:
                fee_notes.append(note)
        offer_all = " ".join([str(t.get("offer_text", "")), str(r.get("concession_text", "")), ev_offer]).lower()
        if re.search(r"waive[ds]?[^.;|]{0,40}amenity fee|amenity fee[^.;|]{0,40}waive", offer_all):
            fee_notes.append("a monthly amenity fee exists (the special offer waives it for a period); amount not published")
        fee_notes = list(dict.fromkeys(fee_notes))
        open_note = next((n for n in fee_notes if "fee exists" in n or "not counted" in n), "")
        if cands:
            amt, note, basis = max(cands, key=lambda c: c[0])
            lines.append({"line": "required building fees", "amount": round(amt), "basis": basis, "note": "; ".join(dict.fromkeys([note] + fee_notes))[:300]})
            if open_note and ("amenity fee exists" in open_note or amt == 0):
                unknown.append("building fees (part)")
        else:
            lines.append({"line": "required building fees", "amount": 0, "basis": "unknown", "note": "; ".join(fee_notes)[:300]}); unknown.append("building fees")
        pet = num(r.get("pet_rent_monthly"))
        if pet is not None and pet <= 150:
            lines.append({"line": "pet rent", "amount": pet, "basis": r.get("pet_rent_monthly_basis", "stated"), "note": r.get("pet_rent_note", "")})
        else:
            lines.append({"line": "pet rent", "amount": 0, "basis": "unknown"}); unknown.append("pet rent")
        pk, ptype = num(r.get("parking_fee_monthly")), str(r.get("parking_type", "")).lower()
        pnote = "; ".join(x for x in [str(r.get("parking_fee_note", "")), ("prices listed: " + str(r.get("parking_options", ""))) if r.get("parking_options") else ""] if x)[:400]
        if pk is not None and pk <= 1000:
            lines.append({"line": "parking (a spot is included)" if pk == 0 else "parking", "amount": pk, "basis": r.get("parking_fee_monthly_basis", "stated"), "note": pnote})
        elif "street" in ptype and not re.search(r"garage|off[- ]street|lot", ptype):
            lines.append({"line": "parking (street)", "amount": 0, "basis": "stated"})
        else:
            lines.append({"line": "parking", "amount": 0, "basis": "unknown", "note": pnote}); unknown.append("parking fee")
        # utilities: only an explicit "included" removes an estimate; "paid by resident" never does (W5)
        inc, ten, none_ = set(), set(), set()
        for seg in str(r.get("utilities_included", "")).split(" || "):
            pu = parsers.parse_utilities(seg)
            inc |= pu["included"]; ten |= pu["tenant"]; none_ |= pu["none"]
        inc -= ten
        u = util.get((r["building_id"], "utilities_studio" if str(r["beds"]).startswith("0") else "utilities_1br"), {})
        ub = r.get("utilities_included_basis") or "stated"
        for name, key in [("electricity (est.)", "electric"), ("gas (est.)", "gas"), ("internet (est.)", "internet")]:
            amt = num(u.get(key))
            if key in inc:
                lines.append({"line": name.replace(" (est.)", " (included in rent)"), "amount": 0, "basis": ub})
            elif key == "gas" and "gas" in none_ and "gas" not in ten:
                lines.append({"line": "gas (no gas service)", "amount": 0, "basis": ub})
            elif amt is not None:
                note = "cooking gas only; heat is included in the rent" if key == "gas" and "heat" in inc else ""
                lines.append({"line": name, "amount": round(amt), "basis": "estimate", "note": note})
            else:
                lines.append({"line": name, "amount": 0, "basis": "unknown"}); unknown.append(key)
        extras = sum(l["amount"] or 0 for l in lines[1:])
        all_in = round((rent_basis_val or 0) + extras)
        offer_text = " | ".join(dict.fromkeys(x for x in [t.get("offer_text", "") or r.get("concession_text", ""), ev_offer if not offer else ""] if x))
        out.append({"listing_id": r["listing_id"], "rent_basis": rent_basis_val, "rent_basis_kind": "net_effective" if is_net else "listed",
                    "rent_gross": rent_gross_val, "rent_asterisk": "yes" if has_offer else "",
                    "rent_listed_price_is": t.get("listed_price_is", ""), "rent_offer_text": offer_text,
                    "rent_free_months": t.get("free_months", ""), "rent_lease_months": t.get("lease_months", ""),
                    "rent_first_full_payment_date": t.get("first_full_payment_date", ""), "rent_first_full_payment_note": t.get("first_full_payment_note", ""),
                    "rent_needs_call": "yes" if has_offer and (not t or not offer) else t.get("needs_call", ""),
                    "all_in": all_in, "all_in_gross": round((rent_gross_val or 0) + extras), "all_in_lines": json.dumps(lines),
                    "all_in_unknown_lines": "; ".join(unknown), "all_in_estimated_lines": "; ".join(l["line"] for l in lines if l["basis"] == "estimate"),
                    "all_in_stated_line_count": sum(1 for l in lines[1:] if l["basis"] not in ("estimate", "unknown")),
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
