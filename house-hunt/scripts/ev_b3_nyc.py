"""Evidence batch 3: NYC official records per building (PLUTO facts already in data/reference/nyc_building_facts.csv;
here: 311 service requests and HPD violations by BBL, last 24 months). NYC Open Data Socrata API (allowed; cached)."""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
SRC = "evidence_b3_nyc"
SINCE = "2024-11-15T00:00:00"
out = {}
batch = [b for b in csv.DictReader(open(lib.DATA / "reference" / "evidence_batches" / "batch_3.csv")) if b["pluto_bbl"]]
for b in batch:
    bbl = str(int(float(b["pluto_bbl"])))
    if bbl in out:
        continue
    r = {}
    q = {"$select": "complaint_type,descriptor,count(*) as n,max(created_date) as last,min(created_date) as first",
         "$where": f"bbl='{bbl}' AND created_date>'{SINCE}'", "$group": "complaint_type,descriptor", "$order": "n DESC", "$limit": "200"}
    r["311"], m1 = lib.get_json("https://data.cityofnewyork.us/resource/erm2-nwe9.json", SRC, params=q, refresh="--refresh" in sys.argv)
    q = {"$select": "class,count(*) as n,max(inspectiondate) as last,sum(case(violationstatus='Open',1,true,0)) as open_n",
         "$where": f"bbl='{bbl}' AND inspectiondate>'{SINCE}'", "$group": "class"}
    r["hpd"], m2 = lib.get_json("https://data.cityofnewyork.us/resource/wvxf-dwi5.json", SRC, params=q, refresh="--refresh" in sys.argv)
    q = {"$select": "inspectiondate,class,novdescription,violationstatus,apartment",
         "$where": f"bbl='{bbl}' AND inspectiondate>'{SINCE}' AND (upper(novdescription) like '%ELEVATOR%' OR upper(novdescription) like '%ROACH%' OR upper(novdescription) like '%MICE%' OR upper(novdescription) like '%BEDBUG%' OR upper(novdescription) like '%MOLD%' OR upper(novdescription) like '%HEAT%' OR upper(novdescription) like '%HOT WATER%')",
         "$order": "inspectiondate DESC", "$limit": "60"}
    r["hpd_detail"], m3 = lib.get_json("https://data.cityofnewyork.us/resource/wvxf-dwi5.json", SRC, params=q, refresh="--refresh" in sys.argv)
    r["urls"] = [m1["url"], m2["url"], m3["url"]]; r["retrieved_at"] = m1["retrieved_at"]; r["addr"] = b["address"]
    out[bbl] = r
    tot = sum(int(x["n"]) for x in r["311"])
    print(bbl, b["address"][:28], "| 311:", tot, [(x["complaint_type"], x.get("descriptor", "")[:18], x["n"]) for x in r["311"][:5]], "| HPD:", [(x.get("class"), x["n"], x.get("open_n")) for x in r["hpd"]], "| detail", len(r["hpd_detail"]), flush=True)
json.dump(out, open(lib.RAW / SRC / "_summary.json", "w"), indent=1)
