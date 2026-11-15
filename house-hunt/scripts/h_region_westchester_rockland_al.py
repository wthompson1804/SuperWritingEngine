"""Region pass (westchester_rockland): building enumeration through Apartment List town pages.

For each town slug: read the 1-bedroom and studio filter pages (discovery only), then every property page found
(price, dates, pet policy, amenities read from the property page). Reuses the parser in h_apartmentlist.py.
Pages already cached today under raw/apartmentlist/ are reused; new fetches are cached under
raw/region_westchester_rockland/ (2.5 s per request; robots.txt: Allow / for *; no Claude-named group).
Output: raw/region_westchester_rockland/al_props.jsonl (one line per property; resumable, keyed by slug).
Usage: python3 scripts/h_region_westchester_rockland_al.py [town-slug ...]
"""
from __future__ import annotations
import hashlib, json, re, sys, time
import lib
import h_apartmentlist as ha

SRC = "region_westchester_rockland"
OUT = lib.RAW / SRC / "al_props.jsonl"
TOWNS = ["mount-vernon", "pelham", "new-rochelle", "yonkers", "bronxville", "tuckahoe", "eastchester", "scarsdale", "hartsdale",
         "white-plains", "harrison", "mamaroneck", "larchmont", "rye", "port-chester", "tarrytown", "sleepy-hollow", "dobbs-ferry",
         "hastings-on-hudson", "irvington", "elmsford", "ossining", "croton-on-hudson", "peekskill", "mount-kisco", "pleasantville",
         "nyack", "piermont", "pearl-river", "nanuet", "spring-valley", "suffern", "haverstraw", "west-haverstraw", "orangeburg",
         "west-nyack", "briarcliff-manor", "rye-brook", "ardsley", "new-city", "stony-point", "valley-cottage", "pelham-manor", "west-harrison", "purchase", "cortlandt-manor", "buchanan", "garnerville", "congers", "tappan", "blauvelt"]
lib.HOST_DELAY[ha.HOST] = 2.5


def fetch(path, refresh=None):
    url = ha.BASE + path
    key = hashlib.sha1(("GET " + url + " ").encode()).hexdigest()[:16]
    src = "apartmentlist" if (lib.RAW / "apartmentlist" / f"{key}.html").exists() else SRC
    try:
        content, meta = lib.cached_get(url, src, ext="html")
    except RuntimeError as e:
        raise ha.Blocked(str(e))
    if meta["status"] in (403, 429):
        raise ha.Blocked(f"HTTP {meta['status']} {path}")
    html = content.decode("utf8", "replace")
    if meta["status"] == 200 and re.search(r"captcha|px-captcha|cf-challenge|Just a moment", html[:20000], re.I):
        raise ha.Blocked(f"challenge page {path}")
    return html, meta


ha.fetch = fetch


def main():
    towns = sys.argv[1:] or TOWNS
    grid = ha.load_grid(); gz = {z[0]: z[3] for z in grid}
    done = {}
    if OUT.exists():
        for l in OUT.read_text().splitlines():
            d = json.loads(l); done[d["slug"]] = d
    stats = {"srp_pages": 0}
    for t in towns:
        try:
            found = ha.discover_city("ny/" + t, stats)
        except ha.Blocked as e:
            print("BLOCKED", t, e); break
        new = [s for s in found if s not in done]
        print(t, "props", len(found), "new", len(new), flush=True)
        for s in new:
            try:
                html, meta = fetch(s)
            except ha.Blocked as e:
                print("BLOCKED", s, e); return
            rec = {"slug": s, "town": t, "status": meta["status"], "at": meta["retrieved_at"], "path": meta.get("path")}
            L = ha.parse_listing(html) if meta["status"] == 200 else None
            if L:
                am = ha.amen_names(L, "community_amenities") + ha.amen_names(L, "unit_amenities") + ha.amen_names(L, "top_amenities")
                rows, reason = ha.build_rows(L, s, meta, gz, grid)
                dogs, policy, wl, pet_rent = ha.pet_facts(L)
                desc = ha.txt(L.get("description"))
                prices = [u.get("base_price") or u.get("price") for fp in (L.get("available_units") or []) if fp.get("bed") in (0, 1) for u in (fp.get("units") or [])]
                prices += [fp.get("price") for fp in (L.get("available_units") or []) if fp.get("bed") in (0, 1) and not fp.get("units")]
                prices = [p for p in prices if isinstance(p, (int, float)) and p > 0]
                rec.update(name=ha.txt(L.get("display_name")), address=ha.txt(L.get("street_address") or L.get("street")), city=ha.txt(L.get("city")),
                           zip=ha.txt(L.get("zip"))[:5], lat=L.get("lat"), lon=L.get("lon"), dogs=dogs, policy=policy, wl=wl, pet_rent=pet_rent,
                           amenities=sorted(set(am)), rental_type=ha.txt(L.get("rental_type")), units_total=L.get("total_units_count"),
                           year_built=ha.txt(L.get("year_built")), pmc=ha.txt(L.get("pmc_display_name")), website=ha.txt(L.get("website_url")),
                           reason=reason, min_price=min(prices) if prices else None, rows=rows,
                           elev_sent=[x.strip()[:220] for x in re.split(r"(?<=[.!?])\s+", desc) if re.search(r"(?i)elevator|walk[- ]?up|\bstor(y|ies)\b|high[- ]rise|mid[- ]rise|doorman|concierge|indoor pool", x)][:6],
                           utilities=ha.txt(L.get("utilities_included_text")), parking_text=ha.txt(L.get("parking_details_text")))
            else:
                rec["reason"] = "unparseable"
            done[s] = rec
            with open(OUT, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("total props", len(done))


if __name__ == "__main__":
    main()
