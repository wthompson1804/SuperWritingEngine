"""Build data/reference/local_rules.csv and dog_parks.csv from hand-entered rows.

Input: scripts/local_rules_rows.jsonl (one JSON object per rule, entered by the harvesting agent after reading
the page) and scripts/local_rules_dogparks.jsonl. Every `quote` must appear verbatim (whitespace and curly
quotes normalised) in the cached text of `url` (raw/local_rules/text/). Rows that fail are printed and left out.
Idempotent: output files are rewritten from the inputs each run.
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib
from local_rules_fetch import norm, text_path, PAGES

ROOT = lib.ROOT
MUNIS = json.loads((ROOT / "scripts/local_rules_munis.json").read_text())
hoods = list(csv.DictReader(open(ROOT / "data/reference/shown_neighborhoods.csv")))
NYC_BORO = {"Queens", "Brooklyn", "Manhattan", "Bronx", "Staten Island"}
NYC_IDS = [h["id"] for h in hoods if h["area"] in NYC_BORO]
MUNIS["nyc"] = ["New York City", "NY", ";".join(NYC_IDS), []]
ALL_IDS = {"NY": [h["id"] for h in hoods if h["state"] == "NY" and h["area"] not in NYC_BORO],
           "NJ": [h["id"] for h in hoods if h["state"] == "NJ"], "CT": [h["id"] for h in hoods if h["state"] == "CT"]}
MUNIS["nj-state"] = ["New Jersey (statewide)", "NJ", ";".join(ALL_IDS["NJ"]), []]
MUNIS["ny-state"] = ["New York State (outside NYC)", "NY", ";".join(ALL_IDS["NY"]), []]
MUNIS["ct-state"] = ["Connecticut (statewide)", "CT", ";".join(ALL_IDS["CT"]), []]
when = {}
for l in PAGES.read_text().splitlines():
    r = json.loads(l)
    when[r["url"]] = r["retrieved_at"]


def check(url: str, quote: str) -> bool:
    tp = text_path(url)
    return tp.exists() and norm(quote) in norm(tp.read_text())


def main() -> None:
    out, bad, seen = [], 0, set()
    for i, l in enumerate((ROOT / "scripts/local_rules_rows.jsonl").read_text().splitlines(), 1):
        if not l.strip():
            continue
        r = json.loads(l)
        m = MUNIS[r["m"]]
        key = (r["m"], r["rule"], r.get("url", ""), r.get("quote", "")[:60], r.get("hoods", ""))
        if key in seen:
            continue
        seen.add(key)
        vt = r.get("vt", "found")
        if vt == "found" and not check(r["url"], r["quote"]):
            bad += 1
            print(f"QUOTE NOT VERIFIED line {i}: {r['m']} {r['rule']} :: {r['quote'][:90]}")
            continue
        out.append({"municipality": m[0], "state": m[1], "applies_to_hood_ids": r.get("hoods") or m[2],
                    "topic": r["t"], "rule": r["rule"], "summary": r["s"], "quote": r.get("quote", ""),
                    "source_url": r.get("url", ""), "source_type": r.get("st", "municipal page"),
                    "retrieved_at": when.get(r.get("url", ""), r.get("at", "")), "value_type": vt})
    # not_found rows for core rules with nothing found, with where we looked or why the source was blocked
    CORE = [("street_parking", "overnight_parking"), ("street_parking", "resident_permit"),
            ("street_parking", "alternate_side"), ("street_parking", "snow_emergency"),
            ("street_parking", "municipal_garage_monthly"), ("dogs", "dog_license"), ("dogs", "leash_law"),
            ("dogs", "dog_park"), ("dogs", "parks_and_beaches"), ("dogs", "waste")]
    BLOCK = json.loads((ROOT / "scripts/local_rules_blocks.json").read_text())
    npages = {}
    for l in PAGES.read_text().splitlines():
        r = json.loads(l)
        npages.setdefault(r["muni"], set()).add(r["url"])
    have = {(o["municipality"], o["rule"]) for o in out}
    for k, m in MUNIS.items():
        if k.endswith("-state"):
            continue
        for t, rule in CORE:
            if (m[0], rule) in have:
                continue
            if k in BLOCK:
                why = BLOCK[k]
            else:
                hosts = sorted({u.split("/")[2] for u in npages.get(k, [])})
                why = (f"Not stated on the {len(npages.get(k, []))} official pages read on {', '.join(hosts) or 'the municipal site'}"
                       " (home page, sitemap pages matching parking / dog / snow keywords). The municipal code is hosted on"
                       " ecode360 / Municode / American Legal, whose robots.txt disallows Claude agents, so it was not read.")
            out.append({"municipality": m[0], "state": m[1], "applies_to_hood_ids": m[2], "topic": t, "rule": rule,
                        "summary": why, "quote": "", "source_url": (m[3][0] if m[3] else ""),
                        "source_type": "municipal page", "retrieved_at": lib.now_iso()[:10], "value_type": "not_found"})
    cols = ["municipality", "state", "applies_to_hood_ids", "topic", "rule", "summary", "quote", "source_url",
            "source_type", "retrieved_at", "value_type"]
    with open(ROOT / "data/reference/local_rules.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(out)
    dp, dseen = [], set()
    p = ROOT / "scripts/local_rules_dogparks.jsonl"
    for i, l in enumerate(p.read_text().splitlines() if p.exists() else [], 1):
        if not l.strip():
            continue
        r = json.loads(l)
        if (r["name"], r["municipality"], r.get("address", "")) in dseen:
            continue
        dseen.add((r["name"], r["municipality"], r.get("address", "")))
        if r.get("check", True) and not check(r["source_url"], r.get("quote") or r["name"]):
            bad += 1
            print(f"DOG PARK NOT VERIFIED line {i}: {r['name']}")
            continue
        dp.append(r)
    dcols = ["name", "municipality", "state", "address", "lat", "lon", "hours", "rules", "quote", "source_url", "retrieved_at"]
    with open(ROOT / "data/reference/dog_parks.csv", "w", newline="") as f:
        w = csv.DictWriter(f, dcols, extrasaction="ignore"); w.writeheader()
        for r in dp:
            r.setdefault("retrieved_at", when.get(r["source_url"], ""))
            w.writerow(r)
    print(f"local_rules.csv: {len(out)} rows ({bad} rejected); dog_parks.csv: {len(dp)} rows")


if __name__ == "__main__":
    main()
