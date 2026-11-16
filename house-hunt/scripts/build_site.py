"""Build the single-file page: site/dist/index.html = site/index.html with site/data.json and site/map_base.json inlined.

site/index.html reads `window.HOUSE_HUNT_DATA` when it exists and otherwise fetches data.json from its own folder.
This script fills the `<!--HOUSE_HUNT_DATA_SLOT-->` marker with a script tag that sets that variable, so the built
file opens straight from disk or from any static host with no second request. A second marker,
`<!--HOUSE_HUNT_MAP_BASE_SLOT-->`, is filled the same way with `window.HOUSE_HUNT_MAP_BASE` (the map's land and
borough outlines, built by build_map_base.py). Idempotent: rerun after build_page_data.py.

Usage: python3 scripts/build_site.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SLOT = "<!--HOUSE_HUNT_DATA_SLOT-->"
MAP_SLOT = "<!--HOUSE_HUNT_MAP_BASE_SLOT-->"


def main():
    page = (SITE / "index.html").read_text(encoding="utf-8")
    if page.count(SLOT) != 1:
        sys.exit(f"site/index.html must contain {SLOT} exactly once (found {page.count(SLOT)})")
    data = json.loads((SITE / "data.json").read_text(encoding="utf-8"))
    for key in ("meta", "years", "neighborhoods", "units", "avoid", "held"):
        if key not in data:
            sys.exit(f"site/data.json has no '{key}'")
    # Compact JSON is valid JavaScript once "</" (which could end the script tag) and the two line separators
    # that old engines reject inside string literals are escaped.
    def js(obj):
        blob = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        return blob.replace("</", "<\\/").replace("<!--", "<\\!--").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

    out = page.replace(SLOT, "<script>window.HOUSE_HUNT_DATA=" + js(data) + ";</script>")
    if page.count(MAP_SLOT) != 1:
        sys.exit(f"site/index.html must contain {MAP_SLOT} exactly once (found {page.count(MAP_SLOT)})")
    base = json.loads((SITE / "map_base.json").read_text(encoding="utf-8"))
    for key in ("proj", "land"):
        if key not in base:
            sys.exit(f"site/map_base.json has no '{key}'")
    out = out.replace(MAP_SLOT, "<script>window.HOUSE_HUNT_MAP_BASE=" + js(base) + ";</script>")
    dist = SITE / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "index.html").write_text(out, encoding="utf-8")
    print(f"site/dist/index.html: {len(out.encode('utf-8')) // 1024} KB, {len(data['units'])} shown, "
          f"{len(data['avoid'])} avoid, {len(data['held'])} held, data built {data['meta'].get('built_at')}")


if __name__ == "__main__":
    main()
