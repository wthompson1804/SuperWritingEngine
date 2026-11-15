"""Region pass (westchester_rockland): read Zumper building pages for named buildings (facts only: pets block,
amenity tags, floors, units, description sentences about elevators / storeys). Robots-allowed path
/apartment-buildings/p<id>/<slug>; 2.5 s apart; stops at a block. Appends to raw/region_westchester_rockland/zumper_buildings.jsonl.
Usage: python3 h_region_westchester_rockland_zb.py <building path> ...   (no args: every building in zumper_town_buildings.json
whose card shows a studio/1BR at or under $3,000)
"""
import json, re, sys
import lib
import h_zumper as hz
SRC = "region_westchester_rockland"
lib.HOST_DELAY["www.zumper.com"] = 2.5
OUT = lib.RAW / SRC / "zumper_buildings.jsonl"
done = {json.loads(l)["path"] for l in OUT.read_text().splitlines()} if OUT.exists() else set()
paths = sys.argv[1:]
if not paths:
    f = json.loads((lib.RAW / SRC / "zumper_town_buildings.json").read_text())
    paths = [u for u, v in f.items() if (v.get("min_beds") or 9) <= 1 and (v.get("min_price") or 9e9) <= 3000 and str(v.get("zip") or "10")[:2] == "10"]
for p in paths:
    if p in done: continue
    try:
        c, m = lib.cached_get(hz.BASE + p, SRC, ext="html", retries=2)
    except RuntimeError as e:
        print("ERR", p, str(e)[-100:]); break
    if m["status"] in (403, 429): print("BLOCKED", m["status"], p); break
    t = c.decode("utf8", "replace")
    st = hz.parse_state(t) or {}
    e = (((st.get("detail") or {}).get("entity") or {}).get("data")) or {}
    vt = hz.visible_text(t)
    try:
        facts = hz.facts_from(e, vt, None, "") if e else {}
    except Exception as ex:
        facts = {"error": repr(ex)[:100]}
    desc = e.get("description") or ""
    rec = {"path": p, "url": hz.BASE + p, "status": m["status"], "at": m["retrieved_at"], "raw_path": m.get("path"), "name": e.get("name"),
           "address": f"{e.get('house') or ''} {e.get('street') or ''}".strip(), "city": e.get("city"), "zip": e.get("zipcode"), "lat": e.get("lat"), "lon": e.get("lng"),
           "units": e.get("units"), "floors": e.get("floors"), "year_built": e.get("year_built"), "manager": e.get("brokerage_name"), "feed": e.get("feed_name"),
           "tags": e.get("amenity_tags"), "facts": {k: v for k, v in facts.items() if v not in ("", None)},
           "sent": [x.strip()[:240] for x in re.split(r"(?<=[.!?])\s+", desc) if re.search(r"(?i)elevator|walk[- ]?up|\bstor(y|ies)\b|high[- ]rise|doorman|concierge|pool|\bpets?\b|\bdogs?\b", x)][:8]}
    with open(OUT, "a") as fh: fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(rec["name"], "|", rec["address"], rec["city"], "| floors", rec["floors"], "| units", rec["units"], "| yb", rec["year_built"], "| elev tag", "Elevator" in (rec["tags"] or []), flush=True)
    print("   facts", json.dumps(rec["facts"])[:700]); print("   sent", " ".join(rec["sent"])[:500])
