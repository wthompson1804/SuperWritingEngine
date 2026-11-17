"""Build the short page ("the concierge draft"): site/concierge.html with its data, drawings and map inlined.

  site/concierge.html                       the template (never changed by this script)
  + site/concierge_data.json                the page's data (scripts/concierge_data.py); see --data
  + site/map_component.html, map_base.json  the map (the block between its MAP COMPONENT markers) and its outlines
  -> site/dist/concierge.html               the whole page in one file
  -> site/dist/concierge_artifact.html      the same without the outer shell, for publishing (build_artifact.to_artifact)

    python3 scripts/build_concierge.py
    python3 scripts/build_concierge.py --data site/_concierge_fixture.json     # the test stand-in

Without --data the script uses site/concierge_data.json when it carries the recommender fields the page needs
(recommender_samples, meta.recommender with its version 4 `conjoint`, buildings[].features) and otherwise the fixture (site/_concierge_fixture.json,
written by scripts/concierge_fixture.py), and says which. Version 3 shows no experience drawings, so none are inlined.

Two things are done to the map block on the way in, in memory only (site/map_component.html is not changed):
  - the part of its card that shows crime rates, and the helper that drew it, are taken out, because this page
    shows no crime wording. Nothing else is touched.
Exit code 1 when a slot is missing from the template, the map block cannot be found, or the artifact check fails.
Idempotent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_artifact import check, to_artifact  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DIST = SITE / "dist"
DATA_SLOT = "<!--CONCIERGE_DATA_SLOT-->"
MAP_SLOT = "<!--CONCIERGE_MAP_SLOT-->"
MAP_START, MAP_END = "<!-- MAP COMPONENT START -->", "<!-- MAP COMPONENT END -->"
# the crime part of the map's card: from the opening "(cr?" to the end of its "not known yet" branch
CRIME_FN_FROM, CRIME_FN_TO = "function crime(label,v,ref){", 'card.className="hhm-card";'   # the helper that drew the bars
CRIME_FROM, CRIME_TO = "(cr?'<div class=\"hhm-crime\">'", "Crime rates not known yet.</p>')+"


def js_json(obj) -> str:
    """JSON that is safe inside a <script> element."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            .replace("</", "<\\/").replace("<!--", "<\\!--").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def script(var: str, obj) -> str:
    return f"<script>window.{var}={js_json(obj)};</script>"


def map_block() -> str:
    text = (SITE / "map_component.html").read_text(encoding="utf-8")
    a, b = text.find(MAP_START), text.find(MAP_END)
    if a < 0 or b < 0:
        raise ValueError("the MAP COMPONENT markers are not in site/map_component.html")
    block = text[a + len(MAP_START):b].strip()
    i, j = block.find(CRIME_FROM), block.find(CRIME_TO)
    if i < 0 or j < i:
        raise ValueError("the crime part of the map card was not found; check CRIME_FROM / CRIME_TO against site/map_component.html")
    block = block[:i] + block[j + len(CRIME_TO):]
    i, j = block.find(CRIME_FN_FROM), block.find(CRIME_FN_TO)
    if i < 0 or j < i:
        raise ValueError("the map's crime-bar function was not found; check CRIME_FN_FROM / CRIME_FN_TO")
    block = block[:i] + block[j:]
    if "crime" in block.lower().replace("hhm-crime", ""):
        raise ValueError("the map block still has crime wording after the cut")
    return block


def has_v3(path: Path) -> bool:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    rec = (d.get("meta") or {}).get("recommender") or {}
    return bool(d.get("recommender_samples")) and bool(rec) and bool(rec.get("conjoint")) \
        and all(isinstance(b.get("features"), dict) for b in d.get("buildings") or [{}])


def pick_data(arg: str | None) -> Path:
    if arg:
        return Path(arg) if Path(arg).is_absolute() else (ROOT / arg if (ROOT / arg).exists() else Path(arg).resolve())
    real, fixture = SITE / "concierge_data.json", SITE / "_concierge_fixture.json"
    return real if real.exists() and (has_v3(real) or not fixture.exists()) else fixture


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build site/dist/concierge.html and site/dist/concierge_artifact.html.")
    ap.add_argument("--data", default=None, help="the data file (default: site/concierge_data.json, else the fixture)")
    ap.add_argument("--banner", default=None, help="one line shown at the very top of the artifact file")
    a = ap.parse_args(argv)
    data_path = pick_data(a.data)
    try:
        page = (SITE / "concierge.html").read_text(encoding="utf-8")
        data = json.loads(data_path.read_text(encoding="utf-8"))
        for slot in (DATA_SLOT, MAP_SLOT):
            if page.count(slot) != 1:
                raise ValueError(f"{slot} must be in site/concierge.html exactly once")
        base_path = SITE / "map_base.json"
        if base_path.exists() and (SITE / "map_component.html").exists():
            map_html = script("HOUSE_HUNT_MAP_BASE", json.loads(base_path.read_text(encoding="utf-8"))) + "\n" + map_block()
        else:
            map_html = ""
            print("build_concierge: no map files; the page is built without the map")
    except (OSError, ValueError) as e:
        print(f"build_concierge: {e}; nothing written")
        return 1
    page = (page.replace(DATA_SLOT, script("CONCIERGE_DATA", data))
                .replace(MAP_SLOT, map_html))
    DIST.mkdir(parents=True, exist_ok=True)
    full, art = DIST / "concierge.html", DIST / "concierge_artifact.html"
    full.write_text(page, encoding="utf-8")
    text = to_artifact(page, a.banner)
    art.write_text(text, encoding="utf-8")
    problems = check(text)
    counts = (data.get("meta") or {}).get("counts") or {}
    print(f"data: {data_path} ({counts.get('buildings')} buildings, {counts.get('apartments')} apartments)"
          + ("  [TEST FIXTURE, not the reviewed data]" if (data.get("meta") or {}).get("fixture") else "")
          + ("" if data.get("recommender_samples") else "  [no recommender fields: the page shows the list only]"))
    print(f"{full}: {len(page.encode('utf-8')):,} bytes")
    print(f"{art}: {len(text.encode('utf-8')):,} bytes")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
