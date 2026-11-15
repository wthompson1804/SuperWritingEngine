"""Official NYC public records per candidate building (NYC Open Data / Socrata), for "avoid" decisions.

Inputs : data/reference/evidence_batches/all_candidate_buildings.csv (rows with pluto_bbl), or --buildings CSV
         with columns addr_key, address, zip, pluto_bbl; or --bbl 4006060029 [--bbl ...] for ad-hoc lots.
Outputs: data/evidence/nyc_records.csv            one row per building x record type x period
         data/evidence/nyc_records_baseline.csv   citywide yardstick (PLUTO class D*, 20+ residential units)
         data/evidence/nyc_records_flags.csv      per-building flags against the yardstick
         data/evidence/nyc_records_match.csv      per-building match table (which datasets know the lot)
         data/evidence/nyc_records_summary.json   numbers quoted in docs/harvest_notes/nyc_records.md

Idempotent: every response is cached under raw/nyc_records/ by URL (scripts/lib.py); the outputs are rebuilt
whole from the cache on each run, so re-running never duplicates rows. The as-of date is part of every query,
so a run on a later day fetches fresh data. --refresh refetches today's queries too.

How records are fetched: ONE batched query per dataset for all candidate lots (bbl IN (...)), not one request
per building. The `query_url` written on each row is the equivalent single-building count query, so anyone can
click it and reproduce the number. --verify N re-runs N of those URLs live and compares.

Counting rules (the same rule is used for the building and for the citywide baseline):
  * HPD complaints (ygpa-z7cr) are counted at PROBLEM level (one row = one problem inside a complaint).
  * HPD violations (wvxf-dwi5) are dated by inspectiondate ("opened in the period").
  * 311 requests (erm2-nwe9) are dated by created_date; 311 HEAT/HOT WATER, UNSANITARY CONDITION and ELEVATOR(HPD)
    are the same reports that reach HPD, so never add them to the HPD complaint counts.
  * "Elevator complaints" for flags = 311 complaint_type 'Elevator' routed to DOB (the defect / out-of-service
    channel). HPD's ELEVATOR category is kept separately (it is mostly dirty cab / broken light, not outages).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import lib  # noqa: E402
from lib import DATA, ROOT, get_json, now_iso  # noqa: E402

lib.HOST_DELAY["data.cityofnewyork.us"] = 1.0  # robots.txt: Crawl-delay: 1

BASE = "https://data.cityofnewyork.us/resource"
SRC = "nyc_records"
OUT = DATA / "evidence"
CAND = DATA / "reference" / "evidence_batches" / "all_candidate_buildings.csv"

DS = {
    "pluto": "64uk-42ks",            # Primary Land Use Tax Lot Output (PLUTO)
    "hpd_viol": "wvxf-dwi5",         # Housing Maintenance Code Violations
    "hpd_compl": "ygpa-z7cr",        # Housing Maintenance Code Complaints and Problems
    "hpd_bldg": "kj4p-ruqc",         # Buildings Subject to HPD Jurisdiction
    "hpd_reg": "tesw-yqqr",          # Multiple Dwelling Registrations
    "hpd_contacts": "feu5-w2e2",     # Registration Contacts
    "bedbug": "wz6d-d3jb",           # Bedbug Reporting
    "sr311": "erm2-nwe9",            # 311 Service Requests from 2020 to Present
    "dob_compl": "eabe-havv",        # DOB Complaints Received
    "dob_elev": "e5aq-a4j2",         # DOB NOW Elevator Safety Compliance (device list)
    "dob_safety_viol": "855j-jady",  # DOB Safety Violations (device_type = 'Elevators')
    "evictions": "6z8x-wfk4",        # Evictions (city marshals)
}
# DOB complaint categories about elevators. 13/62/63/80/81 are in the category list attached to eabe-havv
# (DOBComplaints_complaint_category_list.pdf); 6S / 6M / 7G occur in the data but are not in that PDF.
DOB_ELEV_CATS = ["13", "62", "63", "80", "81", "6S", "6M", "7G"]
DOB_CAT_LIST_URL = ("https://data.cityofnewyork.us/api/views/eabe-havv/files/dc709ed2-7af1-429c-92c9-71ec3a4c23fa"
                    "?download=true&filename=DOBComplaints_complaint_category_list.pdf")

FIELDS = ["addr_key", "bbl", "bin", "record_type", "period", "count", "detail", "units_in_building",
          "per_100_units", "match_basis", "query_url", "retrieved_at"]


# ----------------------------------------------------------------------------------------------- helpers
def q(v) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def in_list(vals, quote=True) -> str:
    return "(" + ",".join(q(v) if quote else str(v) for v in vals) + ")"


def chunks(seq, n):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


class Fetcher:
    def __init__(self, refresh=False):
        self.refresh = refresh
        self.requests = 0
        self.stamp = {}  # tag -> earliest retrieved_at

    def rows(self, ds_key, params, tag=None, page=50000, timeout=240):
        """All rows for a SoQL query, paged with a stable $order. Returns (rows, earliest retrieved_at)."""
        out, off, first = [], 0, None
        p = dict(params)
        if "$order" not in p:
            p["$order"] = ":id"
        while True:
            js, meta = get_json(f"{BASE}/{DS[ds_key]}.json", SRC, params={**p, "$limit": page, "$offset": off},
                                timeout=timeout, refresh=self.refresh)
            self.requests += 1
            if isinstance(js, dict):
                raise RuntimeError(f"Socrata error for {meta['url']}: {js}")
            first = min(first, meta["retrieved_at"]) if first else meta["retrieved_at"]
            out += js
            if len(js) < page:
                break
            off += page
        t = tag or ds_key
        self.stamp[t] = min(self.stamp.get(t, first), first)
        return out, first


def month_shift(d: date, months: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + months, 12)
    m += 1
    last = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))


def periods(as_of: date):
    """(name, start inclusive, end exclusive). 'To date' ends on the as-of day inclusive."""
    end = as_of + timedelta(days=1)
    out = [("last_6_months", month_shift(as_of, -6), end), ("last_24_months", month_shift(as_of, -24), end)]
    for y in range(2023, as_of.year):
        out.append((str(y), date(y, 1, 1), date(y + 1, 1, 1)))
    out.append((f"{as_of.year}_ytd", date(as_of.year, 1, 1), end))
    return out


def top(counter: Counter, n=6) -> str:
    return "; ".join(f"{k}={v}" for k, v in counter.most_common(n))


def url_count(ds_key, where) -> str:
    return f"{BASE}/{DS[ds_key]}.json?" + urlencode({"$select": "count(*)", "$where": where})


def url_rows(ds_key, where, order=None) -> str:
    p = {"$where": where}
    if order:
        p["$order"] = order
    return f"{BASE}/{DS[ds_key]}.json?" + urlencode(p)


def bbl_parts(bbl: str):
    return int(bbl[0]), int(bbl[1:6]), int(bbl[6:10])


def bbl_or_clause(bbls) -> str:
    return " OR ".join("(boroid={} AND block={} AND lot={})".format(*bbl_parts(b)) for b in bbls)


def d10(s) -> str:
    return (s or "")[:10]


_ABBR = {"STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "DRIVE": "DR", "ROAD": "RD", "PLACE": "PL", "LANE": "LN",
         "COURT": "CT", "PARKWAY": "PKWY", "TERRACE": "TER", "EXPRESSWAY": "EXPY", "TURNPIKE": "TPKE", "HIGHWAY": "HWY",
         "EAST": "E", "WEST": "W", "NORTH": "N", "SOUTH": "S", "SAINT": "ST", "FIRST": "1", "SECOND": "2", "THIRD": "3",
         "FOURTH": "4", "FIFTH": "5", "SIXTH": "6", "SEVENTH": "7", "EIGHTH": "8", "NINTH": "9", "TENTH": "10"}


def norm_addr(a: str) -> str:
    """House number + street only, upper case, hyphenless house number, common suffixes abbreviated."""
    a = re.sub(r"[.,]", " ", str(a).upper())
    a = re.split(r"\s+(?:APT|UNIT|#|FL|FLOOR|SUITE|STE)\b", a)[0]
    t = a.split()
    if not t:
        return ""
    t[0] = t[0].replace("-", "")
    t = [re.sub(r"^(\d+)(ST|ND|RD|TH)$", r"\1", _ABBR.get(x, x)) for x in t]
    return " ".join(t)


def house_number(a: str) -> str:
    m = re.match(r"\s*(\d+(?:-\d+)?)", str(a))
    return m.group(1).replace("-", "") if m else ""


# ------------------------------------------------------------------------------------------- record specs
# (record_type, SoQL condition, python predicate, detail function)
def _c(r, k):
    return (r.get(k) or "").upper()


HPD_COMPLAINT_TYPES = [
    ("hpd_complaints_heat_hot_water", "major_category='HEAT/HOT WATER'",
     lambda r: _c(r, "major_category") == "HEAT/HOT WATER", lambda r: f"{_c(r, 'minor_category')}/{_c(r, 'problem_code')}"),
    ("hpd_complaints_pests", "minor_category='PESTS'",
     lambda r: _c(r, "minor_category") == "PESTS", lambda r: _c(r, "problem_code")),
    ("hpd_complaints_mold", "minor_category='MOLD'",
     lambda r: _c(r, "minor_category") == "MOLD", lambda r: _c(r, "space_type") or "MOLD"),
    ("hpd_complaints_elevator", "major_category='ELEVATOR'",
     lambda r: _c(r, "major_category") == "ELEVATOR", lambda r: _c(r, "problem_code")),
    ("hpd_complaints_door_window_security", "(major_category='DOOR/WINDOW' OR minor_category='BELL/BUZZER/INTERCOM')",
     lambda r: _c(r, "major_category") == "DOOR/WINDOW" or _c(r, "minor_category") == "BELL/BUZZER/INTERCOM",
     lambda r: f"{_c(r, 'minor_category')}/{_c(r, 'problem_code')}"),
    ("hpd_complaints_all", "problem_id IS NOT NULL", lambda r: True, lambda r: _c(r, "major_category")),
]
SR311_TYPES = [
    ("sr311_heat_hot_water", ["HEAT/HOT WATER"], None),
    ("sr311_elevator_dob", ["ELEVATOR"], "DOB"),
    ("sr311_elevator_hpd", ["ELEVATOR"], "HPD"),
    ("sr311_noise_residential", ["NOISE - RESIDENTIAL"], None),
    ("sr311_unsanitary_condition", ["UNSANITARY CONDITION"], None),
    ("sr311_illegal_parking", ["ILLEGAL PARKING"], None),
    ("sr311_blocked_driveway", ["BLOCKED DRIVEWAY"], None),
    ("sr311_derelict_or_abandoned_vehicle", ["DERELICT VEHICLE", "DERELICT VEHICLES", "ABANDONED VEHICLE"], None),
]
SR311_ALL = sorted({t for _, ts, _ in SR311_TYPES for t in ts})
VIOL_KEYWORDS = [("heat", r"\bHEAT\b"), ("hot_water", r"HOT WATER"), ("roaches", r"ROACH"), ("mice_rats", r"\bMICE\b|\bRATS?\b|RODENT"),
                 ("bedbugs", r"BED ?BUG"), ("mold", r"\bMOLD\b"), ("lead_paint", r"LEAD"), ("self_closing_door", r"SELF[- ]CLOS"),
                 ("smoke_co_detector", r"SMOKE|CARBON MONOXIDE"), ("elevator", r"ELEVATOR"), ("leak", r"\bLEAK")]

# Baseline metrics: (metric, dataset, date field, SoQL condition)
BASE_METRICS = [
    ("heat_hot_water_complaints", "hpd_compl", "received_date", "major_category='HEAT/HOT WATER'"),
    ("pest_complaints", "hpd_compl", "received_date", "minor_category='PESTS'"),
    ("mold_complaints", "hpd_compl", "received_date", "minor_category='MOLD'"),
    ("elevator_complaints", "sr311", "created_date", "complaint_type='Elevator' AND agency='DOB'"),
    ("hpd_elevator_complaints", "hpd_compl", "received_date", "major_category='ELEVATOR'"),
    ("class_c_violations", "hpd_viol", "inspectiondate", "class='C'"),
]
# metric -> record_type in nyc_records.csv carrying the building's number
METRIC_RECORD = {
    "heat_hot_water_complaints": "hpd_complaints_heat_hot_water", "pest_complaints": "hpd_complaints_pests",
    "mold_complaints": "hpd_complaints_mold", "elevator_complaints": "sr311_elevator_dob",
    "hpd_elevator_complaints": "hpd_complaints_elevator", "class_c_violations": "hpd_violations_class_C",
}
SIZE_BANDS = [("all_20plus", 20, 10 ** 9), ("20-49", 20, 50), ("50-99", 50, 100), ("100-199", 100, 200), ("200plus", 200, 10 ** 9)]


# ------------------------------------------------------------------------------------------------ main
def load_candidates(args) -> pd.DataFrame:
    if args.bbl:
        return pd.DataFrame([{"addr_key": f"bbl:{b}", "address": "", "zip": "", "bbl": b} for b in args.bbl])
    d = pd.read_csv(args.buildings, dtype=str, keep_default_na=False)
    d = d[d.pluto_bbl.str.strip() != ""].copy()
    d["bbl"] = d.pluto_bbl.map(lambda x: str(int(float(x))))
    d = d[d.bbl.str.len() == 10]
    return d.drop_duplicates("addr_key")[["addr_key", "address", "zip", "bbl"]].reset_index(drop=True)


def build(args):
    as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc).date()
    P = periods(as_of)
    t0 = min(p[1] for p in P)                      # earliest date needed (2023-01-01)
    end = as_of + timedelta(days=1)
    F = Fetcher(refresh=args.refresh)
    cand = load_candidates(args)
    bbls = sorted(cand.bbl.unique())
    print(f"as_of={as_of} candidates={len(cand)} distinct_bbl={len(bbls)}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    failures = []

    # ---- PLUTO: units, class, address
    pl = {}
    for ch in chunks(bbls, 100):
        js, _ = F.rows("pluto", {"$select": "bbl,address,zipcode,bldgclass,unitsres,unitstotal,numbldgs,numfloors,yearbuilt,ownername",
                                 "$where": f"bbl in {in_list(ch, quote=False)}"}, tag="pluto")
        for r in js:
            pl[str(int(float(r["bbl"])))] = r
    units = {b: int(float(pl[b].get("unitsres") or 0)) if b in pl else None for b in bbls}

    # ---- batched pulls -------------------------------------------------------------------------------
    def pull(ds_key, select, where_tail, keyfield="bbl", order=None, tag=None):
        rows = []
        for ch in chunks(bbls, 100):
            w = f"{keyfield} in {in_list(ch)}" + (f" AND {where_tail}" if where_tail else "")
            p = {"$where": w}
            if select:
                p["$select"] = select
            if order:
                p["$order"] = order
            js, _ = F.rows(ds_key, p, tag=tag or ds_key)
            rows += js
        return rows

    by = lambda rows, k="bbl": _group(rows, k)

    viol = pull("hpd_viol", "violationid,bbl,bin,class,inspectiondate,violationstatus,currentstatus,novdescription,apartment",
                f"(inspectiondate>='{t0}' OR (class='C' AND violationstatus='Open'))", order="violationid")
    compl = pull("hpd_compl", "problem_id,complaint_id,bbl,bin,received_date,major_category,minor_category,problem_code,"
                              "space_type,type,problem_status,problem_duplicate_flag,apartment",
                 f"received_date>='{t0}'", order="problem_id")
    sr = pull("sr311", "unique_key,bbl,created_date,agency,complaint_type,descriptor,incident_address,status",
              f"created_date>='{t0}' AND upper(complaint_type) in {in_list(SR311_ALL)}", order="unique_key")
    devices = pull("dob_elev", None, None, order="device_number")
    dsv = pull("dob_safety_viol", "bbl,bin,violation_issue_date,violation_number,violation_type,violation_status,device_number,violation_remarks",
               "device_type='Elevators'", order="violation_number")
    bed = pull("bedbug", None, None, order="filing_date")
    evi = pull("evictions", None, f"executed_date>='2024-01-01' AND residential_commercial_ind='Residential'", order="executed_date")

    # evictions with no BBL in the dataset: fall back to house number + street within the candidates' ZIP codes
    zips = sorted({(pl[b].get("zipcode") or "") for b in bbls if b in pl} - {""})
    evi_nobbl = []
    for ch in chunks(zips, 60):
        js, _ = F.rows("evictions", {"$where": f"bbl IS NULL AND eviction_zip in {in_list(ch)} AND executed_date>='2024-01-01' "
                                               f"AND residential_commercial_ind='Residential'", "$order": "executed_date"},
                       tag="evictions_addr")
        evi_nobbl += js
    addr2bbl = {norm_addr(pl[b]["address"]): b for b in bbls if b in pl and pl[b].get("address")}
    evi_addr = defaultdict(list)
    for r in evi_nobbl:
        b = addr2bbl.get(norm_addr(r.get("eviction_address", "")))
        if b and (pl[b].get("zipcode") == r.get("eviction_zip")):
            evi_addr[b].append(r)

    # HPD building + registration (boro/block/lot), then contacts by registration id
    hb, reg = [], []
    for ch in chunks(bbls, 30):
        js, _ = F.rows("hpd_bldg", {"$where": bbl_or_clause(ch), "$order": "buildingid"}, tag="hpd_bldg")
        hb += js
        js, _ = F.rows("hpd_reg", {"$where": bbl_or_clause(ch), "$order": "registrationid"}, tag="hpd_reg")
        reg += js
    bkey = lambda r: f"{int(r['boroid'])}{int(float(r['block'])):05d}{int(float(r['lot'])):04d}"
    hb_by, reg_by = defaultdict(list), defaultdict(list)
    for r in hb:
        hb_by[bkey(r)].append(r)
    for r in reg:
        reg_by[bkey(r)].append(r)
    regids = sorted({r["registrationid"] for r in reg if r.get("registrationid") not in (None, "0")})
    contacts = []
    for ch in chunks(regids, 150):
        js, _ = F.rows("hpd_contacts", {"$where": f"registrationid in {in_list(ch, quote=False)}", "$order": "registrationcontactid"},
                       tag="hpd_contacts")
        contacts += js
    con_by = defaultdict(list)
    for r in contacts:
        con_by[r["registrationid"]].append(r)

    # BINs per lot, from every dataset that carries one
    bins = defaultdict(set)
    for rows in (viol, compl, devices, dsv, bed, evi):
        for r in rows:
            b = str(r.get("bin") or "")
            if re.fullmatch(r"[1-5]\d{6}", b) and not b.endswith("000000"):
                bins[r["bbl"]].add(b)
    for b, rs in list(reg_by.items()) + list(hb_by.items()):
        for r in rs:
            x = str(r.get("bin") or "")
            if re.fullmatch(r"[1-5]\d{6}", x) and not x.endswith("000000"):
                bins[b].add(x)

    # DOB complaints (BIN only; text dates, so filter by category and split by date here)
    all_bins = sorted({x for s in bins.values() for x in s})
    dobc = []
    for ch in chunks(all_bins, 150):
        js, _ = F.rows("dob_compl", {"$where": f"bin in {in_list(ch)} AND complaint_category in {in_list(DOB_ELEV_CATS)}",
                                     "$order": "complaint_number"}, tag="dob_compl")
        dobc += js
    yr, _ = F.rows("dob_compl", {"$select": "substring(date_entered,7,4) as y,count(*) as n", "$group": "y", "$order": "y DESC"},
                   tag="dob_compl_years")
    dob_years = {r["y"]: int(r["n"]) for r in yr if r.get("y")}
    dob_max_year = max(dob_years) if dob_years else "none"
    dob_total = sum(dob_years.values())
    dob_note = f"eabe-havv as retrieved holds {dob_total} rows, latest date_entered year {dob_max_year}"
    if dob_max_year != "none" and int(dob_max_year) < as_of.year - 1:
        failures.append(f"DOB Complaints Received (eabe-havv): {dob_note}; no rows in any reporting period, "
                        f"so DOB elevator complaints are taken from 311 (complaint_type 'Elevator', agency DOB) instead")
    dob_by_bin = by(dobc, "bin")

    V, C, S, DV, DSV, BED, EVI = by(viol), by(compl), by(sr), by(devices), by(dsv), by(bed), by(evi)
    st = F.stamp

    # ---- assemble rows per BBL -----------------------------------------------------------------------
    recs = defaultdict(list)  # bbl -> list of dict (without addr_key)

    def add(b, rtype, period, count, detail, basis, url, ts):
        u = units.get(b)
        per = round(count / u * 100, 2) if (isinstance(count, (int, float)) and u) else ""
        recs[b].append({"bbl": b, "bin": ";".join(sorted(bins[b])), "record_type": rtype, "period": period, "count": count,
                        "detail": detail, "units_in_building": u if u is not None else "", "per_100_units": per,
                        "match_basis": basis, "query_url": url, "retrieved_at": ts})

    def within(v, s, e):
        return bool(v) and s.isoformat() <= d10(v) < e.isoformat()

    for b in bbls:
        kb = f"bbl={q(b)}"
        # PLUTO lot facts
        if b in pl:
            p = pl[b]
            add(b, "pluto_lot", "current", units[b],
                f"address={p.get('address')}; bldgclass={p.get('bldgclass')}; unitsres={p.get('unitsres')}; unitstotal={p.get('unitstotal')}; "
                f"numbldgs={p.get('numbldgs')}; numfloors={p.get('numfloors')}; yearbuilt={p.get('yearbuilt')}; owner={p.get('ownername')}",
                "bbl", url_rows("pluto", f"bbl={b}"), st["pluto"])
        else:
            add(b, "pluto_lot", "current", "", "not_found in PLUTO 64uk-42ks", "bbl", url_rows("pluto", f"bbl={b}"), st["pluto"])

        # HPD violations by class, opened in period
        for cls in "ABC":
            for name, s, e in P:
                rows = [r for r in V.get(b, []) if r.get("class") == cls and within(r.get("inspectiondate"), s, e)]
                kw = Counter()
                for r in rows:
                    for k, pat in VIOL_KEYWORDS:
                        if re.search(pat, (r.get("novdescription") or "").upper()):
                            kw[k] += 1
                opn = sum(1 for r in rows if r.get("violationstatus") == "Open")
                det = f"still_open={opn}" + (f"; keywords in description (overlapping): {top(kw, 8)}" if kw else "") if rows else ""
                add(b, f"hpd_violations_class_{cls}", name, len(rows), det, "bbl",
                    url_count("hpd_viol", f"{kb} AND class='{cls}' AND inspectiondate>='{s}' AND inspectiondate<'{e}'"), st["hpd_viol"])
        rows = [r for r in V.get(b, []) if r.get("class") == "C" and r.get("violationstatus") == "Open"]
        kw = Counter()
        for r in rows:
            for k, pat in VIOL_KEYWORDS:
                if re.search(pat, (r.get("novdescription") or "").upper()):
                    kw[k] += 1
        yrs = Counter(d10(r.get("inspectiondate"))[:4] for r in rows)
        add(b, "hpd_violations_class_C_open", "current", len(rows),
            (f"by inspection year: {top(Counter(dict(sorted(yrs.items(), reverse=True))), 8)}; keywords (overlapping): {top(kw, 8)}" if rows else ""),
            "bbl", url_count("hpd_viol", f"{kb} AND class='C' AND violationstatus='Open'"), st["hpd_viol"])

        # HPD complaints / problems
        for rtype, cond, pred, detf in HPD_COMPLAINT_TYPES:
            for name, s, e in P:
                rows = [r for r in C.get(b, []) if pred(r) and within(r.get("received_date"), s, e)]
                det = ""
                if rows:
                    det = (f"problems={len(rows)}; distinct_complaints={len({r.get('complaint_id') for r in rows})}; "
                           f"distinct_apartments={len({r.get('apartment') for r in rows if r.get('apartment')})}; top: {top(Counter(detf(r) for r in rows))}")
                add(b, rtype, name, len(rows), det, "bbl",
                    url_count("hpd_compl", f"{kb} AND {cond} AND received_date>='{s}' AND received_date<'{e}'"), st["hpd_compl"])

        # 311
        for rtype, types, agency in SR311_TYPES:
            cond = f"upper(complaint_type) in {in_list(types)}" + (f" AND agency='{agency}'" if agency else "")
            for name, s, e in P:
                rows = [r for r in S.get(b, []) if _c(r, "complaint_type") in types and (not agency or r.get("agency") == agency)
                        and within(r.get("created_date"), s, e)]
                det = f"top descriptors: {top(Counter(r.get('descriptor') or 'n/a' for r in rows))}" if rows else ""
                add(b, rtype, name, len(rows), det, "bbl",
                    url_count("sr311", f"{kb} AND {cond} AND created_date>='{s}' AND created_date<'{e}'"), st["sr311"])

        # DOB complaints about elevators (by BIN)
        bl = sorted(bins[b])
        drows = [r for x in bl for r in dob_by_bin.get(x, [])]

        def dob_date(r):
            try:
                return datetime.strptime(r.get("date_entered", ""), "%m/%d/%Y").date().isoformat()
            except ValueError:
                return ""
        durl = url_rows("dob_compl", f"bin in {in_list(bl)} AND complaint_category in {in_list(DOB_ELEV_CATS)}") if bl else ""
        for name, s, e in P:
            rows = [r for r in drows if within(dob_date(r), s, e)]
            det = (f"categories: {top(Counter(r.get('complaint_category') for r in rows))}; " if rows else "") + dob_note
            add(b, "dob_elevator_complaints", name, len(rows) if bl else "", det if bl else "no BIN found for this lot; " + dob_note,
                "bin", durl, st.get("dob_compl", st["dob_compl_years"]))
        if bl:
            last = max((dob_date(r) for r in drows), default="")
            add(b, "dob_elevator_complaints", "all_years_in_dataset", len(drows),
                (f"categories: {top(Counter(r.get('complaint_category') for r in drows))}; latest={last}; " if drows else "") + dob_note,
                "bin", durl, st.get("dob_compl", st["dob_compl_years"]))

        # DOB elevator devices
        rows = DV.get(b, [])
        act = [r for r in rows if r.get("device_type") == "Elevator" and r.get("device_status") == "Active"]
        det = "no device record for this BBL in e5aq-a4j2"
        if rows:
            det = (f"devices by type/status: {top(Counter(str(r.get('device_type')) + '/' + str(r.get('device_status')) for r in rows), 8)}; "
                   f"latest periodic inspection (active elevators)={max((d10(r.get('periodic_latest_inspection')) for r in act), default='n/a')}; "
                   f"oldest periodic inspection (active elevators)={min((d10(r.get('periodic_latest_inspection')) for r in act if r.get('periodic_latest_inspection')), default='n/a')}; "
                   f"latest CAT1 filed={max((d10(r.get('cat1_latest_report_filed')) for r in act), default='n/a')}")
        add(b, "dob_elevator_devices_active", "current", len(act), det, "bbl", url_rows("dob_elev", kb), st["dob_elev"])

        # DOB safety violations on elevators
        rows_all = DSV.get(b, [])
        for name, s, e in P:
            rows = [r for r in rows_all if within(r.get("violation_issue_date"), s, e)]
            det = f"type/status: {top(Counter(str(r.get('violation_type')) + '/' + str(r.get('violation_status')) for r in rows), 8)}" if rows else ""
            add(b, "dob_elevator_violations", name, len(rows), det, "bbl",
                url_count("dob_safety_viol", f"{kb} AND device_type='Elevators' AND violation_issue_date>='{s}' AND violation_issue_date<'{e}'"),
                st["dob_safety_viol"])
        rows = [r for r in rows_all if r.get("violation_status") == "Active"]
        add(b, "dob_elevator_violations_active", "current", len(rows),
            (f"types: {top(Counter(str(r.get('violation_type')) for r in rows), 8)}; issued {min(d10(r.get('violation_issue_date')) for r in rows)}"
             f" to {max(d10(r.get('violation_issue_date')) for r in rows)}" if rows else ""),
            "bbl", url_count("dob_safety_viol", f"{kb} AND device_type='Elevators' AND violation_status='Active'"), st["dob_safety_viol"])

        # Bedbug annual filing (latest)
        rows = sorted(BED.get(b, []), key=lambda r: (d10(r.get("filling_period_end_date")), d10(r.get("filing_date"))))
        burl = url_rows("bedbug", kb, "filing_date DESC")
        if rows:
            lastp = d10(rows[-1].get("filling_period_end_date"))
            latest = [r for r in rows if d10(r.get("filling_period_end_date")) == lastp]
            inf = sum(int(float(r.get("infested_dwelling_unit_count") or 0)) for r in latest)
            hist = Counter()
            for r in rows:
                hist[d10(r.get("filling_period_end_date"))[:4]] += int(float(r.get("infested_dwelling_unit_count") or 0))
            add(b, "bedbug_infested_units", "latest_filing", inf,
                f"filing period {d10(latest[0].get('filing_period_start_date'))} to {lastp}; filed {max(d10(r.get('filing_date')) for r in latest)}; "
                f"filings in period={len(latest)}; dwelling units reported={sum(int(float(r.get('of_dwelling_units') or 0)) for r in latest)}; "
                f"eradicated={sum(int(float(r.get('eradicated_unit_count') or 0)) for r in latest)}; "
                f"re-infested={sum(int(float(r.get('re_infested_dwelling_unit') or 0)) for r in latest)}; "
                f"infested units by period end year: {'; '.join(f'{k}={v}' for k, v in sorted(hist.items(), reverse=True)[:6])}",
                "bbl", burl, st["bedbug"])
        else:
            add(b, "bedbug_infested_units", "latest_filing", "", "not_found: no bedbug filing for this BBL in wz6d-d3jb", "bbl", burl, st["bedbug"])

        # Evictions
        erows = [(r, "bbl") for r in EVI.get(b, [])] + [(r, "address") for r in evi_addr.get(b, [])]
        basis = "bbl" if not evi_addr.get(b) else "bbl+address (rows with no BBL matched on house number + street + ZIP)"
        eP = [p for p in P if p[1] >= date(2024, 1, 1) or p[0].startswith("last_")] + [("2024_to_date", date(2024, 1, 1), end)]
        for name, s, e in eP:
            rows = [r for r, _ in erows if within(r.get("executed_date"), s, e)]
            det = f"executed dates: {', '.join(sorted(d10(r.get('executed_date')) for r in rows)[:12])}" if rows else ""
            add(b, "marshal_evictions_residential", name, len(rows), det, basis,
                url_count("evictions", f"{kb} AND residential_commercial_ind='Residential' AND executed_date>='{s}' AND executed_date<'{e}'"),
                st["evictions"])

        # HPD building record + registration
        rows = hb_by.get(b, [])
        okey = "boroid={} AND block={} AND lot={}".format(*bbl_parts(b))
        add(b, "hpd_building_record", "current", len(rows),
            ("; ".join(f"buildingid={r.get('buildingid')} {r.get('housenumber')} {r.get('streetname')} status={r.get('recordstatus')} "
                       f"lifecycle={r.get('lifecycle')} program={r.get('managementprogram')} classA_units={r.get('legalclassa', 'n/a')} "
                       f"stories={r.get('legalstories', 'n/a')}" for r in rows[:6]) + (f"; (+{len(rows) - 6} more)" if len(rows) > 6 else ""))
            if rows else "not_found in Buildings Subject to HPD Jurisdiction (kj4p-ruqc) for this boro/block/lot",
            "boro_block_lot", url_rows("hpd_bldg", okey), st["hpd_bldg"])
        rows = reg_by.get(b, [])
        if rows:
            parts = []
            for r in sorted(rows, key=lambda r: d10(r.get("lastregistrationdate")), reverse=True)[:4]:
                cs = con_by.get(r["registrationid"], [])

                def names(t):
                    out = []
                    for c in cs:
                        if c.get("type") == t:
                            corp = (c.get("corporationname") or "").strip()
                            person = " ".join(x for x in [(c.get("firstname") or "").strip(), (c.get("lastname") or "").strip()] if x)
                            out.append(" / ".join(x for x in [corp, person] if x))
                    return " | ".join(dict.fromkeys(x for x in out if x)) or "n/a"
                parts.append(f"registrationid={r['registrationid']} ({r.get('housenumber')} {r.get('streetname')}): owner_corporation={names('CorporateOwner')}; "
                             f"individual_owner={names('IndividualOwner')}; head_officer={names('HeadOfficer')}; managing_agent={names('Agent')}; "
                             f"site_manager={names('SiteManager')}; last_registered={d10(r.get('lastregistrationdate'))}; "
                             f"registration_ends={d10(r.get('registrationenddate'))}")
            add(b, "hpd_registration", "current", len(rows), " || ".join(parts) + (f" || (+{len(rows) - 4} more registrations)" if len(rows) > 4 else ""),
                "boro_block_lot", url_rows("hpd_reg", okey), min(st["hpd_reg"], st.get("hpd_contacts", st["hpd_reg"])))
        else:
            add(b, "hpd_registration", "current", 0, "not_found in Multiple Dwelling Registrations (tesw-yqqr) for this boro/block/lot",
                "boro_block_lot", url_rows("hpd_reg", okey), st["hpd_reg"])

    # ---- write nyc_records.csv ----------------------------------------------------------------------
    n = 0
    with open(OUT / "nyc_records.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for _, c in cand.iterrows():
            for r in recs[c.bbl]:
                w.writerow({"addr_key": c.addr_key, **r})
                n += 1
    print(f"nyc_records.csv rows={n}", flush=True)

    # ---- match table --------------------------------------------------------------------------------
    mrows = []
    for _, c in cand.iterrows():
        b = c.bbl
        p = pl.get(b, {})
        hn_c, hn_p = house_number(c.address), house_number(p.get("address", ""))
        mrows.append({"addr_key": c.addr_key, "bbl": b, "candidate_address": c.address, "pluto_address": p.get("address", ""),
                      "house_number_agrees": "" if not (hn_c and hn_p) else ("yes" if hn_c == hn_p else "no"),
                      "pluto_bldgclass": p.get("bldgclass", ""), "pluto_unitsres": p.get("unitsres", ""), "pluto_numbldgs": p.get("numbldgs", ""),
                      "bins": ";".join(sorted(bins[b])), "in_pluto": int(b in pl), "in_hpd_buildings": int(bool(hb_by.get(b))),
                      "has_hpd_registration": int(bool(reg_by.get(b))), "has_hpd_complaint_rows": int(bool(C.get(b))),
                      "has_hpd_violation_rows": int(bool(V.get(b))), "has_311_rows": int(bool(S.get(b))),
                      "has_dob_elevator_device": int(bool(DV.get(b))), "has_bedbug_filing": int(bool(BED.get(b))),
                      "has_eviction_rows": int(bool(EVI.get(b) or evi_addr.get(b)))})
    M = pd.DataFrame(mrows)
    M.to_csv(OUT / "nyc_records_match.csv", index=False)

    # ---- citywide baseline --------------------------------------------------------------------------
    d6, d24 = month_shift(as_of, -6), month_shift(as_of, -24)
    pop, _ = F.rows("pluto", {"$select": "bbl,unitsres,bldgclass,numfloors", "$where": "unitsres>=20 AND bldgclass like 'D%'", "$order": "bbl"},
                    tag="pluto_population")
    popdf = pd.DataFrame(pop)
    popdf["bbl"] = popdf.bbl.map(lambda x: str(int(float(x))))
    popdf["units"] = popdf.unitsres.astype(float)
    popdf = popdf.drop_duplicates("bbl").set_index("bbl")
    base_rows, base_lookup = [], {}
    for metric, ds_key, dfield, cond in BASE_METRICS:
        where = f"{dfield}>='{d24}' AND {dfield}<'{end}' AND {cond}"
        params = {"$select": f"bbl,count(*) as n24,sum(case({dfield}>='{d6}',1,true,0)) as n6", "$where": where, "$group": "bbl", "$order": "bbl"}
        js, ts = F.rows(ds_key, params, tag=f"baseline_{metric}")
        g = {str(r["bbl"]): (int(r["n24"]), int(float(r["n6"]))) for r in js if r.get("bbl")}
        n24 = popdf.index.map(lambda b: g.get(b, (0, 0))[0]).to_numpy(dtype=float)
        n6 = popdf.index.map(lambda b: g.get(b, (0, 0))[1]).to_numpy(dtype=float)
        qurl = f"{BASE}/{DS[ds_key]}.json?" + urlencode(params)
        for pname, cnt in (("last_24_months", n24), ("last_6_months", n6)):
            rate = cnt / popdf.units.to_numpy() * 100
            for band, lo, hi in SIZE_BANDS:
                m = ((popdf.units >= lo) & (popdf.units < hi)).to_numpy()
                x = rate[m]
                row = {"metric": metric, "period": pname, "size_band_units": band, "buildings_n": int(m.sum()),
                       "share_with_zero": round(float((x == 0).mean()), 4), "mean_per_100_units": round(float(x.mean()), 2),
                       "median_per_100_units": round(float(np.percentile(x, 50)), 2), "p80_per_100_units": round(float(np.percentile(x, 80)), 2),
                       "p90_per_100_units": round(float(np.percentile(x, 90)), 2), "p95_per_100_units": round(float(np.percentile(x, 95)), 2),
                       "total_records_in_group": int(cnt[m].sum()),
                       "period_start": str(d24 if pname == "last_24_months" else d6), "period_end": str(as_of),
                       "population": "PLUTO lots with unitsres>=20 AND bldgclass like 'D%' (elevator apartment classes); every such lot, no sampling",
                       "counting_rule": f"{DS[ds_key]}: {cond}; dated by {dfield}; joined on BBL; lots with no record count as 0",
                       "query_url": qurl, "pluto_query_url": f"{BASE}/{DS['pluto']}.json?" + urlencode({"$select": "bbl,unitsres,bldgclass,numfloors", "$where": "unitsres>=20 AND bldgclass like 'D%'"}),
                       "retrieved_at": ts}
                base_rows.append(row)
                base_lookup[(metric, pname, band)] = row
    pd.DataFrame(base_rows).to_csv(OUT / "nyc_records_baseline.csv", index=False)
    print(f"baseline population={len(popdf)} rows={len(base_rows)}", flush=True)

    # ---- flags --------------------------------------------------------------------------------------
    R = {(r["bbl"], r["record_type"], r["period"]): r for b in bbls for r in recs[b]}
    frows = []
    for _, c in cand.iterrows():
        b = c.bbl
        u = units.get(b)
        mm = M[M.addr_key == c.addr_key].iloc[0]
        caution = []
        if not u:
            caution.append("PLUTO has no residential unit count: no per-unit rate")
        elif u < 20:
            caution.append(f"only {u} units: per-100-unit rates are jumpy and the yardstick is 20+ unit elevator buildings")
        if b in pl and not (pl[b].get("bldgclass") or "").startswith("D"):
            caution.append(f"PLUTO class {pl[b].get('bldgclass')} is not a D (elevator apartment) class")
        if mm.house_number_agrees == "no":
            caution.append(f"house number differs from PLUTO lot address ({mm.pluto_address}): check the BBL")
        if b in pl and int(float(pl[b].get("numbldgs") or 1)) > 1:
            caution.append(f"lot holds {pl[b].get('numbldgs')} buildings: counts cover the whole lot")
        if not mm.in_hpd_buildings:
            caution.append("lot not found in HPD building list: HPD zeros may be a non-match")
        base = {"addr_key": c.addr_key, "bbl": b, "address": c.address, "units_in_building": u if u is not None else "",
                "caution": " | ".join(caution)}
        got = []
        for metric in ("heat_hot_water_complaints", "pest_complaints", "mold_complaints", "elevator_complaints", "class_c_violations"):
            for pname in ("last_6_months", "last_24_months"):
                r = R.get((b, METRIC_RECORD[metric], pname))
                bl_ = base_lookup[(metric, pname, "all_20plus")]
                if r and r["per_100_units"] != "" and r["count"] and r["per_100_units"] > bl_["p90_per_100_units"]:
                    got.append({**base, "flag": f"{metric}_{'6m' if pname == 'last_6_months' else '24m'}_above_p90", "metric": metric,
                                "period": pname, "count": r["count"], "per_100_units": r["per_100_units"],
                                "baseline_median": bl_["median_per_100_units"], "baseline_p80": bl_["p80_per_100_units"],
                                "baseline_p90": bl_["p90_per_100_units"], "baseline_p95": bl_["p95_per_100_units"],
                                "above_p95": "yes" if r["per_100_units"] > bl_["p95_per_100_units"] else "no",
                                "detail": r["detail"], "query_url": r["query_url"], "retrieved_at": r["retrieved_at"]})
        for pname, thr, label in (("last_24_months", 3, "elevator_complaints_24m_ge_3"), ("last_6_months", 1, "elevator_complaints_6m_ge_1")):
            r = R.get((b, "sr311_elevator_dob", pname))
            h = R.get((b, "hpd_complaints_elevator", pname))
            if r and r["count"] >= thr:
                bl_ = base_lookup[("elevator_complaints", pname, "all_20plus")]
                got.append({**base, "flag": label, "metric": "elevator_complaints", "period": pname, "count": r["count"],
                            "per_100_units": r["per_100_units"], "baseline_median": bl_["median_per_100_units"],
                            "baseline_p80": bl_["p80_per_100_units"], "baseline_p90": bl_["p90_per_100_units"],
                            "baseline_p95": bl_["p95_per_100_units"],
                            "above_p95": "" if r["per_100_units"] == "" else ("yes" if r["per_100_units"] > bl_["p95_per_100_units"] else "no"),
                            "detail": f"311 Elevator complaints routed to DOB: {r['detail']}; separately, HPD ELEVATOR-category problems in the same period={h['count'] if h else 'n/a'}",
                            "query_url": r["query_url"], "retrieved_at": r["retrieved_at"]})
        if not got:
            got = [{**base, "flag": "none", "metric": "", "period": "", "count": "", "per_100_units": "", "baseline_median": "",
                    "baseline_p80": "", "baseline_p90": "", "baseline_p95": "", "above_p95": "", "detail": "", "query_url": "",
                    "retrieved_at": st["hpd_compl"]}]
        frows += got
    FL = pd.DataFrame(frows)
    FL.to_csv(OUT / "nyc_records_flags.csv", index=False)

    # ---- summary for the notes ----------------------------------------------------------------------
    Mb = M.drop_duplicates("bbl")
    summary = {
        "as_of": str(as_of), "built_at": now_iso(), "candidates": len(cand), "distinct_bbl": len(bbls), "requests_this_run": F.requests,
        "periods": [(a, str(s), str(e - timedelta(days=1))) for a, s, e in P],
        "match_rates_by_bbl": {k: f"{int(Mb[k].sum())}/{len(Mb)}" for k in Mb.columns if k.startswith(("in_", "has_"))},
        "house_number_disagrees": M[M.house_number_agrees == "no"][["addr_key", "bbl", "pluto_address"]].to_dict("records"),
        "bbl_without_bin": sorted(Mb[Mb.bins == ""].bbl),
        "non_D_class": Mb[~Mb.pluto_bldgclass.str.startswith("D")][["bbl", "pluto_address", "pluto_bldgclass", "pluto_unitsres"]].to_dict("records"),
        "evictions_matched_by_address": {b: len(v) for b, v in evi_addr.items()},
        "dob_complaints_dataset": dob_note, "dob_complaints_years": dict(sorted(dob_years.items(), reverse=True)[:8]),
        "baseline_population": len(popdf),
        "baseline_all_20plus": {f"{m}|{p}": {k: base_lookup[(m, p, 'all_20plus')][k] for k in
                                             ("buildings_n", "share_with_zero", "median_per_100_units", "p80_per_100_units", "p90_per_100_units", "p95_per_100_units")}
                                for m, _, _, _ in BASE_METRICS for p in ("last_24_months", "last_6_months")},
        "flag_counts_by_addr_key": FL[FL.flag != "none"].flag.value_counts().to_dict(),
        "addr_keys_with_flags": int(FL[FL.flag != "none"].addr_key.nunique()), "bbls_with_flags": int(FL[FL.flag != "none"].bbl.nunique()),
        "retrieved_at_by_query": dict(sorted(st.items())), "failures": failures,
    }
    (OUT / "nyc_records_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: summary[k] for k in ("match_rates_by_bbl", "flag_counts_by_addr_key", "addr_keys_with_flags", "bbls_with_flags",
                                              "requests_this_run", "failures")}, indent=1))

    if args.verify:
        verify(args.verify, recs, bbls)


def _group(rows, k):
    d = defaultdict(list)
    for r in rows:
        if r.get(k):
            d[str(r[k])].append(r)
    return d


def verify(n, recs, bbls):
    """Re-run n single-building count URLs live (uncached) and compare with the batched numbers."""
    import random
    import time
    import requests
    rng = random.Random(7)
    pool = [r for b in bbls for r in recs[b] if "count(*)" in r["query_url"].replace("%28", "(").replace("%2A", "*").replace("%29", ")")
            and isinstance(r["count"], int)]
    pool_nz = [r for r in pool if r["count"] > 0]
    pick = rng.sample(pool_nz, min(n - n // 4, len(pool_nz))) + rng.sample(pool, min(n // 4, len(pool)))
    bad = 0
    for r in pick:
        time.sleep(1.0)
        js = requests.get(r["query_url"], headers={"User-Agent": lib.USER_AGENT}, timeout=120).json()
        live = int(js[0]["count"])
        ok = live == r["count"]
        bad += not ok
        print(("OK  " if ok else "DIFF"), r["bbl"], r["record_type"], r["period"], "csv=", r["count"], "live=", live, flush=True)
    print(f"verify: {len(pick) - bad}/{len(pick)} agree")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--buildings", default=str(CAND), help="CSV with addr_key, address, zip, pluto_bbl")
    ap.add_argument("--bbl", action="append", help="ad-hoc 10-digit BBL (repeatable); replaces --buildings")
    ap.add_argument("--as-of", default="", help="YYYY-MM-DD, default today (UTC)")
    ap.add_argument("--refresh", action="store_true", help="refetch even if cached")
    ap.add_argument("--verify", type=int, default=0, help="re-run N single-building count URLs live and compare")
    build(ap.parse_args())
