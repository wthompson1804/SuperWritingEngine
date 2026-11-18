"""Build the short page (version 7, "zoom out to neighborhoods"): site/concierge.html with its data inlined.

  site/concierge.html                       the template (never changed by this script)
  + site/neighborhoods_data.json            the ranked neighborhoods and their buildings (scripts/neighborhood_rank.py); see --data
  + site/concierge_data.json                only the fuller sheets of buildings marked verified in the file above
  + site/illustrations.json                 the six scenes, one per neighborhood card (illustration_key)
  + site/map_base.json                      land and state lines for the dot map on Everything (left out when missing)
  -> site/dist/concierge.html               the whole page in one file
  -> site/dist/concierge_artifact.html      the same without the outer shell, for publishing (build_artifact.to_artifact)

    python3 scripts/build_concierge.py
    python3 scripts/build_concierge.py --data some_other_neighborhoods.json

What the page never reads is left out on the way in (in memory only; no data file is changed): the sensitivity
tables, the scoring points of each building, photo addresses (photos are a link to the listing, never loaded), and
file names and keys inside a source. Nothing is renamed and no value is changed.
Exit code 1 when a slot is missing from the template, the data has no neighborhoods, or the artifact check fails.
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
PLACES_SLOT = "<!--CONCIERGE_PLACES_SLOT-->"
MAP_SLOT = "<!--CONCIERGE_MAP_SLOT-->"
ILLUS_SLOT = "<!--CONCIERGE_ILLUS_SLOT-->"
SCENE_IDS = ("enclave", "middle", "new_water", "pre_car", "settled", "space")   # the six scenes, by illustration_key
HOOD_DROP = ("sensitivity",)                       # per neighborhood: not shown
BUILDING_DROP = ("evidence_points", "evidence_score", "photo_url")   # per building: not shown, photos never loaded
META_DROP = ("sensitivity", "neighborhood_assignment", "zumper_no_pets_block", "template_prices")
PLACE_KEEP = ("id", "name", "facts", "confirm", "disclosures", "about", "points")
APT_KEEP = ("id", "label", "beds", "sqft", "floor_text", "rent", "total", "available_text", "offer_text", "star",
            "confirm_question", "listing_url")


def js_json(obj) -> str:
    """JSON that is safe inside a <script> element."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            .replace("</", "<\\/").replace("<!--", "<\\!--").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def script(var: str, obj) -> str:
    return f"<script>window.{var}={js_json(obj)};</script>"


def slim(data: dict) -> dict:
    """The neighborhoods data without the parts the page never reads. Fields are dropped whole, never renamed."""
    out = dict(data)
    out["meta"] = {k: v for k, v in (data.get("meta") or {}).items() if k not in META_DROP}
    hoods = []
    for h in data.get("neighborhoods") or []:
        if not isinstance(h, dict):
            continue
        h = {k: v for k, v in h.items() if k not in HOOD_DROP}
        for key in ("top_buildings", "avoid_buildings", "all_buildings"):
            rows = []
            for b in h.get(key) or []:
                if not isinstance(b, dict):
                    continue
                b = {k: v for k, v in b.items() if k not in BUILDING_DROP}
                if isinstance(b.get("source"), dict):
                    b["source"] = {k: v for k, v in b["source"].items() if k in ("name", "url")}
                rows.append(b)
            h[key] = rows
        hoods.append(h)
    out["neighborhoods"] = hoods
    return out


def verified_ids(data: dict) -> set:
    ids = set()
    for h in data.get("neighborhoods") or []:
        for key in ("top_buildings", "avoid_buildings", "all_buildings"):
            for b in h.get(key) or []:
                v = b.get("verified") if isinstance(b, dict) else None
                if v is True or (isinstance(v, dict) and v.get("on_page")):
                    ids.add(b.get("id"))
    return ids


def places(data: dict) -> dict:
    """The fuller sheets (site/concierge_data.json) of the buildings the neighborhoods data marks verified, by id,
    cut to what the building screen shows. A private person's contact is not carried at all."""
    path = SITE / "concierge_data.json"
    if not path.exists():
        return {"meta": {}, "buildings": {}}
    c = json.loads(path.read_text(encoding="utf-8"))
    want, out = verified_ids(data), {}
    for b in c.get("buildings") or []:
        if b.get("id") not in want:
            continue
        p = {k: b[k] for k in PLACE_KEEP if k in b}
        p["apartments"] = [{k: a[k] for k in APT_KEEP if k in a} for a in b.get("apartments") or [] if isinstance(a, dict)]
        out[b["id"]] = p
    m = c.get("meta") or {}
    return {"meta": {k: m[k] for k in ("anchor", "anchor_label") if k in m}, "buildings": out}


def map_base() -> dict | None:
    path = SITE / "map_base.json"
    if not path.exists():
        return None
    m = json.loads(path.read_text(encoding="utf-8"))
    return {k: m[k] for k in ("proj", "land", "state_lines") if k in m} if m.get("proj") else None


def illustrations() -> dict:
    """The six scenes from site/illustrations.json, keyed by illustration_key ({alt, banner, tall} each)."""
    path = SITE / "illustrations.json"
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for k in SCENE_IDS:
        v = d.get(k)
        v = d.get(v) if isinstance(v, str) else v
        if isinstance(v, dict) and isinstance(v.get("banner"), str):
            out[k] = {"alt": v.get("alt"), "banner": v["banner"], "tall": v.get("tall") or v["banner"]}
    return out


def pick_data(arg: str | None) -> Path:
    if arg:
        return Path(arg) if Path(arg).is_absolute() else (ROOT / arg if (ROOT / arg).exists() else Path(arg).resolve())
    return SITE / "neighborhoods_data.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build site/dist/concierge.html and site/dist/concierge_artifact.html.")
    ap.add_argument("--data", default=None, help="the neighborhoods data file (default: site/neighborhoods_data.json)")
    ap.add_argument("--banner", default=None, help="one line shown at the very top of the artifact file")
    a = ap.parse_args(argv)
    data_path = pick_data(a.data)
    try:
        page = (SITE / "concierge.html").read_text(encoding="utf-8")
        data = json.loads(data_path.read_text(encoding="utf-8"))
        if not isinstance(data.get("neighborhoods"), list) or not data["neighborhoods"]:
            raise ValueError(f"{data_path} has no neighborhoods")
        for slot in (DATA_SLOT, PLACES_SLOT, MAP_SLOT, ILLUS_SLOT):
            if page.count(slot) != 1:
                raise ValueError(f"{slot} must be in site/concierge.html exactly once")
        pl, base = places(data), map_base()
        if base is None:
            print("build_concierge: no map file; the page is built without the map")
    except (OSError, ValueError) as e:
        print(f"build_concierge: {e}; nothing written")
        return 1
    page = (page.replace(DATA_SLOT, script("CONCIERGE_DATA", slim(data)))
                .replace(PLACES_SLOT, script("CONCIERGE_PLACES", pl))
                .replace(ILLUS_SLOT, script("CONCIERGE_ILLUS", illustrations()))
                .replace(MAP_SLOT, script("HOUSE_HUNT_MAP_BASE", base) if base else ""))
    DIST.mkdir(parents=True, exist_ok=True)
    full, art = DIST / "concierge.html", DIST / "concierge_artifact.html"
    full.write_text(page, encoding="utf-8")
    text = to_artifact(page, a.banner)
    art.write_text(text, encoding="utf-8")
    problems = check(text)
    hoods = data["neighborhoods"]
    print(f"data: {data_path} ({len(hoods)} neighborhoods, {sum(len(h.get('top_buildings') or []) for h in hoods)} top buildings, "
          f"{sum(len(h.get('avoid_buildings') or []) for h in hoods)} to avoid, {len(pl['buildings'])} fuller sheets)")
    print(f"{full}: {len(page.encode('utf-8')):,} bytes")
    print(f"{art}: {len(text.encode('utf-8')):,} bytes")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
