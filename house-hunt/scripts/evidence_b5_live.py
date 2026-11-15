"""Evidence batch 5: write data/evidence/live_check_batch_5.csv from the re-fetched listing pages (no network)."""
import csv, json, sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
E = lib.RAW / "evidence_b5"
state = json.loads((E / "_state.json").read_text())
tr = json.loads((E / "_trulia_parsed.json").read_text())
za = json.loads((E / "_za_parsed.json").read_text())
rows = list(csv.DictReader(open(lib.DATA / "reference/evidence_batches/batch_5.csv")))
SITE = {"shearwood-station": "https://www.shearwoodstation.com/", "the-leaf": "https://theleafnewrochelle.com/",
        "motif": "https://livemotifapts.com/", "two-clinton-park": "https://www.two.clintonpark.com/",
        "stella": "https://www.rentstella.com/", "illustrator": "https://www.livetheillustrator.com/",
        "one-clinton-park": "https://www.one.clintonpark.com/", "25-maple-avenue": "https://rent25maple.com/"}
EXTRA = json.loads((E / "_live_notes.json").read_text()) if (E / "_live_notes.json").exists() else {}
ep = lambda s: dt.datetime.fromtimestamp(s, dt.timezone.utc).date().isoformat() if s else ""
out = []
for r in rows:
    units = [u.strip() for u in r["unit_list"].split(",")]
    rents = [x.strip() for x in r["rents"].split(",")]
    url = r["urls"].split("|")[0].strip()
    s = state[url]
    slug = url.rstrip("/").split("/")[-1]
    for unit, rent in zip(units, rents):
        row = dict(addr_key=r["addr_key"], listing_url=url, unit=unit, status="", price_now="", available_now_text="",
                   matches_stored="", building_site_url=SITE.get(slug, ""), checked_at=s["retrieved_at"], notes="")
        notes = []
        if "trulia.com" in url:
            o = tr[url]
            row.update(price_now=o["price"], available_now_text=o["avail"] or "")
            live = bool(o["active"])
            notes.append(f"Trulia status '{o['label']}'; date listed {str(o['date_listed'])[:10]}")
            if "Decreased" in (o["fees"][2] or ""):
                notes.append(o["fees"][2].split("\n")[0])
        elif "zumper.com" in url:
            e = za[url]
            if e.get("floorplan_listings"):
                F = [f for f in e["floorplan_listings"] if f.get("bedrooms") == 0][0]
                row.update(price_now=F["price"], available_now_text=F["date_available"])
                live = F.get("listing_status") == 1
                notes.append(f"building page, studio floor plan (no unit number); listed_on {ep(F.get('listed_on'))}; 1BR plan is $"
                             + str([f for f in e['floorplan_listings'] if f.get('bedrooms') == 1][0]['price']))
            else:
                row.update(price_now=e.get("price"), available_now_text=e.get("date_available"))
                live = e.get("listing_status") == 1
                notes.append(f"page address '{e.get('address')}'; first created {ep(e.get('created_on'))}, listed_on {ep(e.get('listed_on'))}")
        else:
            L = za[url]; x = None
            for fp in L.get("available_units") or []:
                for c in fp.get("units") or []:
                    if str(c.get("name")) == unit:
                        x = c; plan = fp.get("name")
            live = bool(x) and x.get("availability") == "available"
            if x:
                row.update(price_now=x["price"], available_now_text=("now; " if x.get("available_now") else "") + "available_on " + str(x.get("available_on")))
                notes.append(f"plan {plan}; unit record updated {x.get('updated_at')}; lease {x.get('lease_length')} mo")
                if x.get("required_fees"):
                    notes.append(f"page shows required fees ${x['required_fees']}/mo, total ${x.get('total_price')}")
            notes.append(f"page updated_at {L.get('updated_at')}")
        if not live:
            row["status"] = "gone"; row["matches_stored"] = "no"
        else:
            same = str(row["price_now"]) == rent
            row["status"] = "live" if same else "changed"; row["matches_stored"] = "yes" if same else "no"
        if EXTRA.get(r["addr_key"]):
            notes.append(EXTRA[r["addr_key"]])
        row["notes"] = "; ".join(notes)
        out.append(row)
(lib.DATA / "evidence").mkdir(exist_ok=True)
with open(lib.DATA / "evidence/live_check_batch_5.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
import collections
print(len(out), collections.Counter(o["status"] for o in out))
