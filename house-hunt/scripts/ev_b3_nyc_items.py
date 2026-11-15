"""Evidence batch 3: turn raw/evidence_b3_nyc/_summary.json (311 + HPD by BBL, last 24 months) into item rows."""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
from ev_b3_util import put
d = json.load(open(lib.RAW / "evidence_b3_nyc" / "_summary.json"))
batch = [b for b in csv.DictReader(open(lib.DATA / "reference" / "evidence_batches" / "batch_3.csv")) if b["pluto_bbl"]]
rows = []
P = "Record summary (counts, not a quote), tax lot BBL {bbl}, 2024-11-15 to 2026-11-15: "
def grp(r, test):
    xs = [x for x in r["311"] if test(x["complaint_type"], x.get("descriptor", ""))]
    return sum(int(x["n"]) for x in xs), max([x["last"][:10] for x in xs] or [""]), min([x["first"][:10] for x in xs] or [""])
for b in batch:
    bbl = str(int(float(b["pluto_bbl"]))); r = d[bbl]
    name = b["building_name"] or b["address"].split(",")[0]
    def add(cat, date, text, url, about="building", site="NYC 311 service requests (NYC Open Data)"):
        rows.append(dict(addr_key=b["addr_key"], building_name=name, category=cat, item_date=date, excerpt=P.format(bbl=bbl) + text,
                         source_site=site, source_url=url, about=about, retrieved_at=r["retrieved_at"]))
    n0 = len(rows)
    n, last, first = grp(r, lambda c, s: "levator" in c)
    if n: add("elevator", last, f"{n} elevator complaints filed with 311 (first {first}, latest {last}).", r["urls"][0])
    n, last, first = grp(r, lambda c, s: c == "HEAT/HOT WATER")
    if n >= 3: add("management", last, f"{n} heat or hot water complaints filed with 311 (first {first}, latest {last}).", r["urls"][0])
    n, last, first = grp(r, lambda c, s: s in ("PESTS", "MOLD") or c == "Rodent")
    if n >= 3: add("management", last, f"{n} pest, rodent or mold complaints filed with 311 (first {first}, latest {last}).", r["urls"][0])
    n, last, first = grp(r, lambda c, s: c == "Noise - Residential")
    if n >= 10: add("noise", last, f"{n} residential noise complaints filed with 311 (first {first}, latest {last}).", r["urls"][0])
    n, last, first = grp(r, lambda c, s: c in ("Illegal Parking", "Blocked Driveway", "Abandoned Vehicle", "Derelict Vehicles"))
    if n >= 10: add("other", last, f"{n} illegal parking, blocked driveway or abandoned vehicle complaints filed with 311 at this lot's address (first {first}, latest {last}).", r["urls"][0], about="street")
    h = {x.get("class"): x for x in r["hpd"]}
    if h:
        tot = sum(int(x["n"]) for x in h.values()); c = h.get("C", {}); last = max(x["last"][:10] for x in h.values())
        add("management", last, f"{tot} HPD housing code violations issued (class C 'immediately hazardous': {c.get('n', 0)}, of which still open: {c.get('open_n', 0)}; class B: {h.get('B', {}).get('n', 0)}); latest inspection {last}.",
            r["urls"][1], site="HPD Housing Maintenance Code Violations (NYC Open Data)")
    for x in [x for x in r["hpd_detail"] if "ELEVATOR" in x["novdescription"].upper()][:2]:
        rows.append(dict(addr_key=b["addr_key"], building_name=name, category="elevator", item_date=x["inspectiondate"][:10],
                         excerpt=x["novdescription"][:300], source_site="HPD Housing Maintenance Code Violations (NYC Open Data)",
                         source_url=r["urls"][2], about="building", retrieved_at=r["retrieved_at"]))
    if len(rows) == n0:
        rows.append(dict(addr_key=b["addr_key"], building_name=name, category="none_found", item_date="", excerpt=f"No 311 elevator, heat, pest, mold or noise cluster and no HPD violations for BBL {bbl} since 2024-11-15 (looked: NYC 311 and HPD violations open data).",
                         source_site="NYC Open Data", source_url=r["urls"][0], about="building", retrieved_at=r["retrieved_at"]))
print(put("items", rows), "item rows")
