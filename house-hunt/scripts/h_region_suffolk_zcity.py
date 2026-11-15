"""Suffolk region pass: Zumper city pages (allowed path /apartments-for-rent/<city>) -> building-page links found."""
import json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib, h_zumper as Z
OUT = lib.ROOT / "raw" / "region_suffolk" / "zumper_city_buildings.json"
found = json.loads(OUT.read_text()) if OUT.exists() else {}
for c in sys.argv[1:]:
    if c in found: continue
    try:
        st, meta, text = Z.fetch(f"/apartments-for-rent/{c}"); time.sleep(2.2)
    except Z.Blocked as e:
        print("BLOCKED", c, e); break
    except Exception as e:
        print("ERR", c, repr(e)[:100]); continue
    links = sorted(set(re.findall(r'/apartment-buildings/p?\d+/[a-z0-9-]+', text)))
    found[c] = links
    OUT.write_text(json.dumps(found, indent=1))
    print(c, meta["status"], len(links), flush=True)
allb = sorted({l for v in found.values() for l in v})
print(len(allb)); print("\n".join(allb))
