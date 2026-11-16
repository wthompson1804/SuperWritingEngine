"""Build the single-file page: site/dist/index.html = site/index.html with site/data.json and site/map_base.json inlined.

site/index.html reads `window.HOUSE_HUNT_DATA` when it exists and otherwise fetches data.json from its own folder.
This script fills the `<!--HOUSE_HUNT_DATA_SLOT-->` marker with a script tag that sets that variable, so the built
file opens straight from disk or from any static host with no second request. A second marker,
`<!--HOUSE_HUNT_MAP_BASE_SLOT-->`, is filled the same way with `window.HOUSE_HUNT_MAP_BASE` (the map's land and
borough outlines, built by build_map_base.py). A third, `<!--HOUSE_HUNT_ILLUS_SLOT-->`, takes `window.HOUSE_HUNT_ILLUS`
from site/illustrations.json when that file exists (the six experience drawings); without it the slot is left empty. Idempotent: rerun after build_page_data.py.

The data is slimmed on the way in (site/data.json itself is never changed): fields the template does not read are left
out, see DROP below. The page opened beside its files (site/index.html) still fetches the whole data.json.

Usage: python3 scripts/build_site.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SLOT = "<!--HOUSE_HUNT_DATA_SLOT-->"
MAP_SLOT = "<!--HOUSE_HUNT_MAP_BASE_SLOT-->"
ILLUS_SLOT = "<!--HOUSE_HUNT_ILLUS_SLOT-->"


# ---------------------------------------------------------------------------------------------------------------------
# What is left out of the built page. site/index.html never reads these (checked by scanning the template for each
# property name, then by rendering every page from the whole data and from the slimmed data and comparing the text;
# scripts/site_walkthrough_test.js repeats that comparison on a sample). A path is dotted; "[]" steps into every item of
# a list. Add a field here only after checking the template; remove it from here the day the template starts to read it.
# Read by key pattern, so NOT listed although their names are not in the template: any "toll…mail…" key (tollMail()),
# the lease and 12-month price keys (LEASE_KEYS, P12_KEYS), headlines.* (hlSub()).
UNIT_DROP = [
    "scores",                       # the ranking's working figures; the page shows only the order
    "confidence", "listing_age_days", "more_in_building", "zip", "floor_basis_note",
    "moments.sat.parking_type", "moments.night.parking_type",   # copies of parking.type
    "moments.sun.toll_basis", "moments.sun.toll_mail_note", "moments.sun.drive_basis",
    "dog.size_only_source", "parking.options_text", "parking.fee_note",
    "amenities.laundry", "amenities.pool_text", "amenities.doorman_text",
    "elevator.listing_site_only", "disclosures[].severity",
    "cost_check.unknown_count", "cost_check.cap_margin", "confirm.reviewed",
    "ratings.most_reviews", "ratings.platforms[].seen_via",
]
# Avoid cards and "worth a phone call" items are short cards: name, price, what to confirm, the evidence, the questions.
SHORT_CARD_DROP = UNIT_DROP + ["moments", "vs_queens", "vs_queens_diff", "amenities", "all_in_lines", "host", "headlines", "ratings", "photos"]
DROP = {
    "units[]": UNIT_DROP,
    "avoid[]": SHORT_CARD_DROP,
    "held[]": SHORT_CARD_DROP,
    "neighborhoods[]": [
        "described[].licence",      # licence notes are not shown; the source name and link are
        "described[].topic",
        "local.voices[].source_area",   # local.survey[].source_area is read since UI pass 5 (shown when it is not the neighborhood itself)
        "experience_score_basis",       # the scoring sentence is no longer shown (audit item 28)
        "safety.subcity_estimate", "safety.vs_metro", "safety.vs_local",
        "toll_basis", "experience_score", "sqft_median", "parent_id",
        "traits.built_before_1940_share", "traits.built_since_2010_share", "traits.college_degree_share",
        "traits.detached_house_share", "traits.median_hh_income",
    ],
}
# buildings[]: the template reads only the building's own copies of these (bView() in site/index.html); everything else
# about a building it still takes from the building's apartments.
BUILDING_KEEP = ("id", "contact", "about_building", "about_points", "ratings", "photos")
# A local rule's "quote" is shown only when it has no "summary" (ruleLi: r.summary || r.quote): duplicate text otherwise.
RULE_LISTS = ("parking_rules", "dog_rules")
# A key whose value is null reads the same as a missing key everywhere in the template except under these, where
# "null" and "absent" mean different things (evidence.public_evidence: "not checked yet" against "no line at all").
KEEP_NULLS_UNDER = ("evidence",)


def _drop(obj, parts):
    """Remove the field at a dotted path; '[]' on a part steps into each item of that list."""
    if obj is None:
        return
    head, rest = parts[0], parts[1:]
    many = head.endswith("[]")
    key = head[:-2] if many else head
    if not isinstance(obj, dict) or key not in obj:
        return
    if not rest:
        del obj[key]
    elif many:
        for item in obj[key] if isinstance(obj[key], list) else []:
            _drop(item, rest)
    else:
        _drop(obj[key], rest)


def _no_nulls(obj):
    if isinstance(obj, dict):
        return {k: (v if k in KEEP_NULLS_UNDER else _no_nulls(v)) for k, v in obj.items() if v is not None or k in KEEP_NULLS_UNDER}
    if isinstance(obj, list):
        return [_no_nulls(v) for v in obj]   # a null inside a list keeps its place
    return obj


def slim(data):
    """A copy of the page data without what the template never reads."""
    data = json.loads(json.dumps(data))
    for where, paths in DROP.items():
        for rec in data.get(where[:-2]) or []:
            for path in paths:
                _drop(rec, path.split("."))
    for hood in data.get("neighborhoods") or []:
        local = hood.get("local")
        if not isinstance(local, dict):
            continue
        for key in RULE_LISTS:
            for rule in local.get(key) or []:
                if isinstance(rule, dict) and rule.get("summary") and "quote" in rule:
                    del rule["quote"]
    if isinstance(data.get("buildings"), list):
        data["buildings"] = [{k: b[k] for k in BUILDING_KEEP if k in b} for b in data["buildings"] if isinstance(b, dict)]
        for b in data["buildings"]:
            r = b.get("ratings")
            if isinstance(r, dict):
                r.pop("most_reviews", None)
                for p in r.get("platforms") or []:
                    if isinstance(p, dict):
                        p.pop("seen_via", None)
    for key in ("units", "avoid", "held", "neighborhoods", "awaiting_live_check"):
        if isinstance(data.get(key), list):
            data[key] = [_no_nulls(rec) for rec in data[key]]
    return data


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

    full_bytes = len(js(data).encode("utf-8"))
    data = slim(data)
    slim_bytes = len(js(data).encode("utf-8"))
    out = page.replace(SLOT, "<script>window.HOUSE_HUNT_DATA=" + js(data) + ";</script>")
    if page.count(MAP_SLOT) != 1:
        sys.exit(f"site/index.html must contain {MAP_SLOT} exactly once (found {page.count(MAP_SLOT)})")
    base = json.loads((SITE / "map_base.json").read_text(encoding="utf-8"))
    for key in ("proj", "land"):
        if key not in base:
            sys.exit(f"site/map_base.json has no '{key}'")
    out = out.replace(MAP_SLOT, "<script>window.HOUSE_HUNT_MAP_BASE=" + js(base) + ";</script>")
    # The drawings (site/illustrations.json, built by build_illustrations.py) are optional: without the file the slot is
    # emptied and the page shows no art.
    illus_path = SITE / "illustrations.json"
    if page.count(ILLUS_SLOT) != 1:
        sys.exit(f"site/index.html must contain {ILLUS_SLOT} exactly once (found {page.count(ILLUS_SLOT)})")
    illus = None
    if illus_path.exists():
        try:
            illus = json.loads(illus_path.read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"site/illustrations.json could not be read ({e}); the page is built without drawings")
    if not isinstance(illus, dict) or not illus:
        illus = None
    out = out.replace(ILLUS_SLOT, "<script>window.HOUSE_HUNT_ILLUS=" + js(illus) + ";</script>" if illus else "")
    dist = SITE / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "index.html").write_text(out, encoding="utf-8")
    print(f"data in the page: {slim_bytes // 1024} KB of {full_bytes // 1024} KB (fields the template never reads are left out)")
    print(f"site/dist/index.html: {len(out.encode('utf-8')) // 1024} KB, {len(data['units'])} shown, "
          f"{len(data['avoid'])} avoid, {len(data['held'])} held, data built {data['meta'].get('built_at')}")


if __name__ == "__main__":
    main()
