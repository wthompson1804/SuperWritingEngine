"""Floor-plan pages of one website template used by several CT buildings ("Name. 1 Bed | 1 Bath | 700 sq. ft. | $2250 | ... N UNITS AVAILABLE").
Writes raw/region_connecticut/fp_<slug>.json: floor plans with price range and units-available count. Usage: URL slug"""
import re, sys, json
from h_mgmt_common import polite_get, strip_tags
import lib
u, slug = sys.argv[1], sys.argv[2]
h, m = polite_get(u, "region_connecticut")
t = re.sub(r"\s+", " ", strip_tags(h))
out = []
for mm in re.finditer(r"([A-Z][\w\- ]{0,25})\. (Studio|\d Beds?) \| ([\d.]+) Baths? \| ([\d,]+)(?: - [\d,]+)? sq\. ft\. \| \$([\d,]+)\s*(?:-\s*\$?([\d,]+))? \| Deposit: .*?(\d+) UNITS? AVAILABLE", t):
    out.append({"plan": mm.group(1).split("Floorplan ")[-1].replace("3D Tour ", "").strip(), "beds": 0 if mm.group(2) == "Studio" else int(mm.group(2)[0]), "baths": mm.group(3), "sqft": mm.group(4).replace(",", ""),
                "min": int(mm.group(5).replace(",", "")), "max": int((mm.group(6) or mm.group(5)).replace(",", "")), "avail": int(mm.group(7))})
json.dump({"url": u, "seen": m["retrieved_at"], "raw": m["path"], "plans": out}, open(lib.RAW / "region_connecticut" / f"fp_{slug}.json", "w"))
print(slug, m["status"], "plans", len(out), "avail 0/1BR<=3000:", [(p["plan"], p["beds"], p["min"], p["max"], p["avail"]) for p in out if p["beds"] < 2 and p["avail"] and p["min"] <= 3000])
