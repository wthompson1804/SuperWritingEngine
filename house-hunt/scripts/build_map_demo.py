"""Embed a trimmed copy of site/data.json and site/map_base.json into site/map_component.html, the standalone
demo of the map component, so the demo opens from file:// with no fetch.

Only the two <script type="application/json"> blocks (ids hhm-demo-data and hhm-demo-base) are rewritten; the
component between <!-- MAP COMPONENT START --> and <!-- MAP COMPONENT END --> is left as it is. Idempotent.

Run:  python3 scripts/build_map_base.py && python3 scripts/build_map_demo.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "site" / "map_component.html"
DATA = ROOT / "site" / "data.json"
BASE = ROOT / "site" / "map_base.json"

# The only fields the component reads.
HOOD_FIELDS = ("id", "name", "state", "year", "lat", "lon", "drive_min", "toll_round_trip")
SAFETY_FIELDS = ("violent_per_1000", "property_per_1000", "year")


def trimmed() -> dict:
    d = json.loads(DATA.read_text())
    hoods = []
    for h in d["neighborhoods"]:
        o = {k: h.get(k) for k in HOOD_FIELDS}
        o["counts"] = {"shown": (h.get("counts") or {}).get("shown")}
        s = h.get("safety") or {}
        o["safety"] = {k: s.get(k) for k in SAFETY_FIELDS}
        hoods.append(o)
    m = d["meta"]
    return {
        "meta": {"built_at": m.get("built_at"), "anchor": m.get("anchor"), "jamaica_yardstick": m.get("jamaica_yardstick")},
        "years": [{"id": y["id"], "label": y.get("label")} for y in d["years"]],
        "neighborhoods": hoods,
    }


def put(html: str, script_id: str, obj: dict) -> str:
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    pat = re.compile(r'(<script id="%s" type="application/json">)(.*?)(</script>)' % re.escape(script_id), re.S)
    if not pat.search(html):
        raise SystemExit(f"marker script #{script_id} not found in {PAGE}")
    return pat.sub(lambda m: m.group(1) + body + m.group(3), html, count=1)


def main() -> None:
    html = PAGE.read_text()
    data = trimmed()
    html = put(html, "hhm-demo-data", data)
    html = put(html, "hhm-demo-base", json.loads(BASE.read_text()))
    PAGE.write_text(html)
    a = html.index("<!-- MAP COMPONENT START -->")
    b = html.index("<!-- MAP COMPONENT END -->")
    comp = len(html[a:b].encode())
    base = BASE.stat().st_size
    print(f"wrote {PAGE.relative_to(ROOT)}: {len(html.encode()) / 1024:.1f} KB "
          f"({len(data['neighborhoods'])} neighborhoods embedded)")
    print(f"component block {comp / 1024:.1f} KB + map_base.json {base / 1024:.1f} KB = {(comp + base) / 1024:.1f} KB "
          f"(budget 250 KB)")


if __name__ == "__main__":
    main()
