"""Suffolk region pass: enumerate Apartment List property slugs per town (city SRP pages, robots-allowed)."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib, h_apartmentlist as A
OUT = lib.ROOT / "raw" / "region_suffolk" / "al_city_props.json"
TOWNS = """amityville copiague lindenhurst babylon west-babylon north-babylon wyandanch deer-park huntington huntington-station melville
bay-shore islip central-islip brentwood sayville patchogue east-patchogue ronkonkoma hauppauge smithtown kings-park port-jefferson
port-jefferson-station coram bohemia holbrook riverhead commack farmingville yaphank medford selden centereach lake-grove stony-brook
northport east-northport islandia holtsville mount-sinai middle-island oakdale west-islip east-islip greenlawn dix-hills nesconset
st-james rocky-point miller-place shirley mastic center-moriches calverton wading-river lake-ronkonkoma north-amityville east-farmingdale""".split()
found = json.loads(OUT.read_text()) if OUT.exists() else {}
for t in TOWNS:
    if t in found: continue
    props_all, page = {}, 1
    try:
        while page <= 6:
            html, meta = A.fetch(f"/ny/{t}" + (f"/page-{page}" if page > 1 else ""))
            time.sleep(2.2)
            if meta["status"] != 200: break
            props, low, tc, _ = A.parse_srp(html)
            new = {s: low.get(s) for s in props.values() if s not in props_all}
            if not new: break
            props_all.update(new); page += 1
    except A.Blocked as e:
        print("BLOCKED", t, e); break
    found[t] = props_all
    OUT.write_text(json.dumps(found, indent=1))
    print(t, len(props_all), flush=True)
allp = {}
for t, d in found.items():
    for s, lp in d.items(): allp.setdefault(s, lp)
print(len(allp))
for s in sorted(allp): print(s, allp[s])
