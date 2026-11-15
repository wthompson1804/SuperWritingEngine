"""Evidence batch 5: parse the re-fetched Trulia pages into a summary JSON (no network)."""
import csv, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib, h_trulia as T
state = json.loads((lib.RAW / "evidence_b5/_state.json").read_text())
out = {}
for u, s in state.items():
    if "trulia.com" not in u: continue
    html = (lib.ROOT / s["path"]).read_text(errors="replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    hd = json.loads(m.group(1))["props"].get("homeDetails") or {}
    st = hd.get("currentStatus") or {}
    feats, hl = T.flat_features(hd.get("features")), T.highlighted(hd.get("features"))
    afr = hd.get("activeForRentListing") or {}
    out[u] = dict(retrieved_at=s["retrieved_at"], active=st.get("isActiveForRent"), label=st.get("label"),
        price=(hd.get("price") or {}).get("price"), avail=hd.get("formattedAvailableDate"),
        street=(hd.get("location") or {}).get("streetAddress"), date_listed=afr.get("dateListed"),
        pet=afr.get("petPolicy"), hl=hl, feats=[f for f in feats if re.search(r"elevator|pet|dog|parking|floor|stories|year built|doorman|pool|laundry|fee|garage", " ".join(f), re.I)],
        fees=T.fees_home(hd.get("rentalCostsAndFees") or {}),
        provider=afr.get("provider"), desc=((hd.get("description") or {}).get("value") or ""))
(lib.RAW / "evidence_b5/_trulia_parsed.json").write_text(json.dumps(out, indent=1, default=str))
for u, o in out.items():
    print(u.split("/home/")[1][:40], "|", o["active"], o["label"], o["price"], o["avail"], o["date_listed"])
