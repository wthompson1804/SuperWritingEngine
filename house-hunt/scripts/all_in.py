"""All-in monthly cost, rebuilt on the master tables (plan v4, Part 4). Adds columns to data/master_units.csv.

all_in        = rent basis + required building fees + pet rent + parking fee + utilities not included in rent
all_in_gross  = the same with the gross rent (what a paying month costs), where a concession is known
Rent basis (Will): the net-effective rent where the terms are known; otherwise the listed price. A unit with any
concession language gets rent_asterisk = yes, and rent_terms columns say what the monthly rent is and when the
first full payment falls due (data/rent_terms.csv from scripts/rent_terms.py, when present).
Every line carries a basis: confirmed / stated / estimate / unknown. Unknown lines are not published: they add nothing
to all_in and are listed in all_in_unknown_lines so the page can name them. Cap: all_in <= $3,000 -> cost_gate = pass.

Owner's decisions of 2026-11-16 (independent check 3, D7):
  (a) PET RENT is certain for her (she is getting a dog). Where a building's pet rent is not published the line is an
      ESTIMATE: the median of the known pet rents of buildings in the same state (line "pet rent (est.)", basis estimate,
      like the utilities). It counts toward all_in and so toward the cap.
  (b) PARKING and REQUIRED BUILDING FEES stay unknown (nothing is estimated into all_in). all_in_likely = all_in + the
      median known parking fee (same state, same kind of parking where known) + the median known required fees, for the
      lines that are unknown. Where all_in <= $3,000 < all_in_likely the unit carries the disclosure "Could pass $3,000
      once parking and fees are known" (scripts/rank.py). The cap itself stays on all_in.
  The medians are written to data/reference/cost_estimates.csv with their counts. They are taken over the buildings of
  the master table (every building with a unit that passes the listing gates), one value per building, because the set
  of ranked buildings depends on the cost gate itself; scripts/test_rules.py --data compares them with the ranked set.

A rent is NET-EFFECTIVE only when the evidence says the listed price is (data/rent_terms.csv: listed_price_is). A gift
card, a one-time credit or a free month whose effect on the listed price is not stated never lowers the rent used here,
and no gross figure is invented for it (independent check 3, D5, D16): such a unit carries rent_offer_kind = special_offer.
"""
from __future__ import annotations

import glob
import os
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
MIN_N = 5                                   # fewest buildings a median may rest on before the wider group is used
EST_FILE = DATA / "reference" / "cost_estimates.csv"


def _median(vals):
    v = sorted(float(x) for x in vals)
    n = len(v)
    return None if not n else (v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2)


def known_medians(units, fee_of):
    """Medians of the KNOWN values, one value per building, for the estimate lines.
    units: master rows (dicts). fee_of: building_id -> known required-fee amount (or absent).
    Returns {"pet": {state: (median, n)}, "parking": {(state, kind): (median, n), (state, ""): ..., ("", ""): ...},
             "fees": {state: (median, n), "": ...}}. Groups under MIN_N buildings are left out (the caller falls back)."""
    seen, pet, park, fees = set(), {}, {}, {}
    for r in units:
        b = r["building_id"]
        if b in seen:
            continue
        seen.add(b)
        st = r.get("state", "")
        pr = num(r.get("pet_rent_monthly"))
        if pr is not None and 0 <= pr <= 150:
            pet.setdefault(st, []).append(pr); pet.setdefault("", []).append(pr)
        pk = num(r.get("parking_fee_monthly"))
        if pk is not None and 0 <= pk <= 1000:
            kind = parsers.parking_kind(r.get("parking_type", ""))
            for key in dict.fromkeys(((st, kind), (st, ""), ("", ""))):
                park.setdefault(key, []).append(pk)
        if b in fee_of:
            fees.setdefault(st, []).append(fee_of[b]); fees.setdefault("", []).append(fee_of[b])
    cut = lambda d: {k: (_median(v), len(v)) for k, v in d.items() if len(v) >= MIN_N}
    return {"pet": cut(pet), "parking": cut(park), "fees": cut(fees)}


def pick(table, *keys):
    """First key present in a medians table: (median, n, key) or (None, 0, None)."""
    for k in keys:
        if k in table:
            return table[k][0], table[k][1], k
    return None, 0, None


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

    # the medians behind the estimate lines: two passes. Pass 1 costs every unit with no medians (to learn each building's
    # known required fees); pass 2 uses the medians. The medians do not depend on pass-1 estimates, so this is stable.
    recs = U.to_dict("records")
    MED = {"pet": {}, "parking": {}, "fees": {}}
    first = [cost_unit(r, util, RT, MED) for r in recs]
    fee_by_b = {}
    for r, o in zip(recs, first):
        fl = next(l for l in json.loads(o["all_in_lines"]) if l["line"] == "required building fees")
        if fl["basis"] != "unknown" and not any(x.startswith("building fees") for x in o["all_in_unknown_lines"].split("; ")):
            fee_by_b.setdefault(r["building_id"], []).append(fl["amount"] or 0)
    MED = known_medians(recs, {b: _median(v) for b, v in fee_by_b.items()})
    out = [cost_unit(r, util, RT, MED) for r in recs]
    est_rows = [{"line": "pet rent", "state": k or "all", "parking_kind": "", "median": m, "buildings": n} for k, (m, n) in sorted(MED["pet"].items())] \
        + [{"line": "parking", "state": k[0] or "all", "parking_kind": k[1] or "any", "median": m, "buildings": n} for k, (m, n) in sorted(MED["parking"].items())] \
        + [{"line": "required fees", "state": k or "all", "parking_kind": "", "median": m, "buildings": n} for k, (m, n) in sorted(MED["fees"].items())]
    pd.DataFrame(est_rows).assign(method="median of the known values, one value per building, over the buildings of the master table; groups under "
                                  + str(MIN_N) + " buildings are not used").to_csv(EST_FILE, index=False)
    finish(U, out, RT)


def cost_unit(r, util, RT, MED):
    if True:
        lines, unknown = [], []
        listed_old = num(r["listed_rent"])
        # the price read at the live check is the rent whenever the check saw the listing (independent check 2, D15:
        # Avalon Maplewood's check read $2,590 with status "live" and the rent line stayed at $2,600)
        live = num(r.get("live_price")) if r.get("live_status") in ("changed", "live") and num(r.get("live_price")) else None
        if live and listed_old and abs(live - listed_old) <= 0.5:
            live = None
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
        # independent check 3, D5 / D16: the rent is net-effective ONLY when the evidence says the listed price is. The
        # rent used is always the listed price; a credit, a gift card or a free month the page does not tie to the price
        # never lowers it, and a gross figure is given only where the page states net-effective pricing.
        is_net = offer and t.get("listed_price_is") == "net_effective"
        rent_basis_val = listed
        rent_gross_val = ((gross if gross and gross >= (listed or 0) else None) or gross_if_net or listed) if is_net else listed
        # D8: the listed price belongs to a lease longer than 13 months. Where the page gives the 12-month price, the
        # cost (and so the $3,000 cap) is worked on the 12-month price; otherwise the listed price stands and the
        # unit carries the lease-term asterisk (scripts/rank.py).
        lease_m, p12 = num(r.get("price_lease_months")), num(r.get("price_12_month"))
        long_lease = lease_m is not None and lease_m > 13
        rent_line = "rent (net-effective)" if is_net else "rent (as listed)"
        if long_lease and p12 and p12 >= (listed or 0):
            price_note = "; ".join(x for x in [price_note, f"the listed ${listed:g} is the {lease_m:g}-month lease price; ${p12:g} is the 12-month price"] if x)
            rent_basis_val, rent_gross_val, rent_line, is_net = p12, max(p12, rent_gross_val or 0), "rent (12-month lease price)", False
        elif long_lease:
            price_note = "; ".join(x for x in [price_note, f"this price is for a {lease_m:g}-month lease; the 12-month price is not published"] if x)
        lines.append({"line": rent_line, "amount": rent_basis_val,
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
        total_price = bool(re.search(r"total monthly|isTotalMonthlyFeeIncluded", str(r.get("price_basis", ""))))
        if total_price:
            # D15 of check 2 (Metrovue, Metro Point): the listed price is the page's "total price", which already contains
            # the required monthly fees. The fee line is a known $0 on top of it, not an unknown.
            # Independent check 3, D14 (Parc at Glenbrook 2328, Residences at The Summit): this holds ALSO where a fee
            # sentence was parsed: that fee is inside the total, so adding it counted it twice.
            inside = max((c[0] for c in cands), default=0)
            cands = [(0.0, "the listed price is the page's total price, which already includes the required monthly fees"
                      + (f" (${inside:g} of fees named on the page are inside it)" if inside else ""), "stated")]
            fee_notes = [n for n in fee_notes if "fee exists" not in n]
            open_note = ""
        ph = num(r.get("required_fees_phone")) if str(r.get("required_fees_phone", "")).strip() else None
        if ph is not None:
            # a total given on the phone replaces every reading of the pages (highest precedence), and nothing stays open
            cands, fee_notes, open_note = [(ph, "total of the required monthly fees, by " + str(r.get("required_fees_phone_source", "phone call")), "confirmed_by_phone")], [], ""
        fee_has_internet = False
        if cands:
            amt, note, basis = max(cands, key=lambda c: c[0])
            # D13 (Atlas): a fee sentence that prices internet ("Internet: $65") covers it; no estimate on top
            fee_src = " | ".join([str(r.get("required_fees_text", "")), str(r.get("other_monthly_fees_json", ""))])
            fee_has_internet = amt > 0 and bool(re.search(r"internet[^,;|\"]{0,14}\$?\s?\d{2}|wi-?fi[^,;|\"]{0,14}\$\s?\d{2}", fee_src, re.I)) and not re.search(r"internet[^,;|]{0,20}optional", fee_src, re.I)
            lines.append({"line": "required building fees", "amount": round(amt), "basis": basis, "note": "; ".join(dict.fromkeys([note] + fee_notes))[:300]})
            if open_note and ("amenity fee exists" in open_note or amt == 0):
                unknown.append("building fees (part)")
        else:
            lines.append({"line": "required building fees", "amount": 0, "basis": "unknown", "note": "; ".join(fee_notes)[:300]}); unknown.append("building fees")
        pet = num(r.get("pet_rent_monthly"))
        st_ = r.get("state", "")
        if pet is not None and pet <= 150:
            lines.append({"line": "pet rent", "amount": pet, "basis": r.get("pet_rent_monthly_basis", "stated"), "note": r.get("pet_rent_note", "")})
        else:
            # owner, 2026-11-16: she is getting a dog, so pet rent is certain. Not published -> an estimate, never $0.
            pm, pn, pkey = pick(MED["pet"], st_, "") if os.environ.get("HH_NO_PET_ESTIMATE") != "1" else (None, 0, None)   # measurement switch only
            if pm is not None:
                lines.append({"line": "pet rent (est.)", "amount": round(pm), "basis": "estimate",
                              "note": f"not published for this building; estimate = the median of the known pet rents of {pn} buildings in {pkey or 'all three states'}"})
            else:
                lines.append({"line": "pet rent", "amount": 0, "basis": "unknown"}); unknown.append("pet rent")
        pk, ptype = num(r.get("parking_fee_monthly")), str(r.get("parking_type", "")).lower()
        pnote = "; ".join(x for x in [str(r.get("parking_fee_note", "")), ("prices listed: " + str(r.get("parking_options", ""))) if r.get("parking_options") else ""] if x)[:400]
        if pk is not None and pk <= 1000:
            lines.append({"line": "parking (a spot is included)" if pk == 0 else "parking", "amount": pk, "basis": r.get("parking_fee_monthly_basis", "stated"), "note": pnote})
        elif "street" in ptype and not re.search(r"garage|off[- ]street|lot", ptype):
            # D21: $0 because a listing for this building says street parking and none mentions a garage or lot
            lines.append({"line": "parking (street)", "amount": 0, "basis": "stated", "note": "street parking only, per a listing for this building; no garage or lot is mentioned"})
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
            elif key == "internet" and fee_has_internet:
                lines.append({"line": "internet (in the required building fees)", "amount": 0, "basis": "stated", "note": "the fee line above prices internet"})
            elif key == "gas" and "gas" in none_ and "gas" not in ten:
                lines.append({"line": "gas (no gas service)", "amount": 0, "basis": ub})
            elif amt is not None:
                note = "cooking gas only; heat is included in the rent" if key == "gas" and "heat" in inc else ""
                lines.append({"line": name, "amount": round(amt), "basis": "estimate", "note": note})
            else:
                lines.append({"line": name, "amount": 0, "basis": "unknown"}); unknown.append(key)
        extras = sum(l["amount"] or 0 for l in lines[1:])
        all_in_exact = (rent_basis_val or 0) + extras
        all_in = round(all_in_exact)
        # (b) what the bill would likely be once the unknown parking and fee lines are known (never part of all_in)
        likely_add, likely_notes = 0.0, []
        if "parking fee" in unknown:
            kind = parsers.parking_kind(r.get("parking_type", ""))
            m_, n_, k_ = pick(MED["parking"], (st_, kind), (st_, ""), ("", ""))
            if m_ is not None:
                likely_add += m_
                likely_notes.append(f"parking ${m_:g} (median of {n_} known fees: {k_[0] or 'all states'}{', ' + k_[1] + ' parking' if k_[1] else ''})")
        fee_unknown = next((x for x in unknown if x.startswith("building fees")), "")
        if fee_unknown:
            m_, n_, k_ = pick(MED["fees"], st_, "")
            known_part = next((l["amount"] or 0 for l in lines if l["line"] == "required building fees"), 0)
            if m_ is not None and m_ > known_part:
                likely_add += m_ - known_part
                likely_notes.append(f"required fees ${m_:g} (median of {n_} buildings with known fees: {k_ or 'all states'})" + (f", of which ${known_part:g} is already counted" if known_part else ""))
        all_in_likely = round(all_in + likely_add)
        # the offer in the page's own words only: no checker's note, no raw page data (docs/PENDING_FIXES.md)
        offer_text = t.get("offer_text_page", "") if t else ""
        if not offer_text and str(r.get("concession_text", "")).strip() and not re.search(r"not stated|\[|capture|field\)|[:=]\s*\w+;", str(r.get("concession_text", ""))):
            offer_text = str(r.get("concession_text", "")).strip()[:300]
        otype = t.get("offer_type", "") if t else ""
        offer_kind = "net_effective" if is_net else ("special_offer" if (otype in ("months_free", "weeks_free", "dollar_credit", "look_and_lease")
                                                                         or (otype == "other" and t.get("listed_price_is") == "unknown")) else
                                                     ("deposit_or_fee" if otype == "reduced_deposit_or_fee" else ("special_offer" if has_offer and not t else "")))
        return ({"listing_id": r["listing_id"], "rent_basis": rent_basis_val, "rent_basis_kind": "net_effective" if is_net else "listed",
                    "rent_gross": rent_gross_val, "rent_asterisk": "yes" if has_offer else "",
                    "rent_listed_price_is": t.get("listed_price_is", ""), "rent_offer_text": offer_text, "rent_offer_kind": offer_kind,
                    "rent_offer_type": otype, "all_in_likely": all_in_likely, "all_in_likely_note": "; ".join(likely_notes),
                    "rent_free_months": t.get("free_months", ""), "rent_lease_months": t.get("lease_months", ""),
                    "rent_first_full_payment_date": t.get("first_full_payment_date", ""), "rent_first_full_payment_note": t.get("first_full_payment_note", ""),
                    "rent_needs_call": "yes" if has_offer and (not t or not offer) else t.get("needs_call", ""),
                    # D12: how close to the cap, and how many of parking / required fees (and pet rent, where no estimate exists) are not published
                    "cap_margin": CAP - all_in,
                    "all_in_unknown_count": sum(1 for k in ("building fees", "pet rent", "parking fee") if any(x.startswith(k) for x in unknown)),
                    "rent_lease_term_months": f"{lease_m:g}" if lease_m else "", "rent_12_month_price": f"{p12:g}" if p12 else "",
                    "all_in": all_in, "all_in_gross": round((rent_gross_val or 0) + extras), "all_in_lines": json.dumps(lines),
                    "all_in_unknown_lines": "; ".join(unknown), "all_in_estimated_lines": "; ".join(l["line"] for l in lines if l["basis"] == "estimate"),
                    "all_in_stated_line_count": sum(1 for l in lines[1:] if l["basis"] not in ("estimate", "unknown")),
                    "cost_gate": "pass" if all_in_exact <= CAP else "fail"})     # on the unrounded sum: round() takes $3,000.50 down to $3,000


def finish(U, out, RT):
    O = pd.DataFrame(out).set_index("listing_id")
    U = U.drop(columns=[c for c in O.columns if c in U.columns]).join(O, on="listing_id")
    U.to_csv(DATA / "master_units.csv", index=False)
    print(f"units {len(U)}; cost gate {U.cost_gate.value_counts().to_dict()}; rent asterisk {int((U.rent_asterisk == 'yes').sum())}; "
          f"rent terms file {'present' if len(RT) else 'absent'}")
    for k in ["building fees", "pet rent", "parking fee", "gas"]:
        print(f"  unknown {k}: {int(U.all_in_unknown_lines.str.contains(k).sum())}")
    print("  pet rent estimated:", int(U.all_in_estimated_lines.str.contains("pet rent").sum()),
          "| within the cap but likely over once parking and fees are known:", int(((U.cost_gate == "pass") & (pd.to_numeric(U.all_in_likely) > CAP)).sum()))
    print("  gross above cap while basis passes:", int(((U.cost_gate == "pass") & (pd.to_numeric(U.all_in_gross) > CAP)).sum()))


if __name__ == "__main__":
    main()
