"""Write live-check rows and Apartment List-derived confirm/fact rows from the refreshed pages."""
import json, csv, re, sys
sys.path.insert(0, "scripts")
import ev_b1_add
S = json.load(open("raw/evidence_b1/al_summary.json"))
def clean(s): return re.sub(r"\s+", " ", str(s or "")).replace("$$", "$").strip()
recs = []
for k, s in S.items():
    site = (s["site"] or "").split("?")[0]
    for un, pr in s["stored"].items():
        hit = [u for u in s["units"] if str(u["unit"]) == un]
        if not hit:
            recs.append(dict(t="live", addr_key=k, listing_url=s["url"], unit=un, status="gone", price_now="", available_now_text="", matches_stored="no", building_site_url=site, checked_at=s["at"], notes="unit no longer in the page's unit list")); continue
        u = hit[0]
        on = u["on"] or ""; now = u["now"]
        txt = "available now" + (f" (available_on {on})" if on else "") if now else f"available {on}"
        ok_date = now or (on and on <= "2026-12-15")
        price_ok = str(u["price"]) == str(pr)
        status = "live" if price_ok else "changed"
        notes = []
        if not price_ok: notes.append(f"stored {pr}")
        if u["price"] and u["price"] > 3000: notes.append("repriced above $3,000")
        if not ok_date: notes.append("NOT available by 2026-12-15")
        if on and on < "2026-08-15": notes.append(f"available_on date is old ({on}): unit has been vacant or the feed date is stale")
        notes.append(f"Apartment List feed={s['source']}; page availability_last_checked_at {s['checked']}")
        recs.append(dict(t="live", addr_key=k, listing_url=s["url"], unit=un, status=status, price_now=u["price"], available_now_text=txt, matches_stored="yes" if price_ok else "no", building_site_url=site, checked_at=s["at"], notes="; ".join(notes)))
    # elevator from AL amenity list
    if s["elevator"]:
        recs.append(dict(t="confirm", addr_key=k, fact="elevator", value="yes", quote="Apartment List community amenity: Elevator", source_url=s["url"], status="confirmed"))
    p = s["pets"] or {}
    ap = [x.lower() for x in p.get("allowed_pets") or []]
    if "dogs" in ap or "Dogs allowed" in s["amen"]:
        recs.append(dict(t="confirm", addr_key=k, fact="dogs_allowed", value="yes", quote=("allowed_pets: " + ", ".join(ap)) if "dogs" in ap else "Apartment List amenity: Dogs allowed", source_url=s["url"], status="confirmed"))
    for grp in ("dogs", "general"):
        g = p.get(grp) or {}
        for fld, fact in (("rent", "pet_rent"), ("fee", "pet_fee"), ("deposit", "pet_deposit"), ("limit", "pet_count_limit"), ("restrictions", "pet_restrictions")):
            v = clean(g.get(fld))
            if v: recs.append(dict(t="fact", addr_key=k, fact=f"{fact} ({grp})", value=v[:300], quote=v[:400], source_url=s["url"]))
    for fact, v in (("year_built", s["year"]), ("management_company", s["pmc"]), ("total_units", s["total_units"]), ("parking", clean(s["parking_text"]) or "; ".join(sorted(set(clean(x.get("comment") or x.get("category")) for x in (s["parking"] or []) if (x.get("comment") or x.get("category")) and x.get("category") != "none"))) ), ("required_fees_text", clean(s["addfees"])), ("utilities_included", clean(s["util"])), ("building_site", site)):
        if v: recs.append(dict(t="fact", addr_key=k, fact=fact, value=str(v)[:300], quote="", source_url=s["url"]))
    pool = [a for a in s["amen"] if re.search(r"pool", a, re.I)]
    if pool: recs.append(dict(t="fact", addr_key=k, fact="pool", value=", ".join(pool), quote="", source_url=s["url"]))
    dm = [a for a in s["amen"] if re.search(r"doorman|concierge", a, re.I)]
    if dm: recs.append(dict(t="fact", addr_key=k, fact="doorman_or_concierge", value=", ".join(dm), quote="", source_url=s["url"]))
ev_b1_add.add(recs)
