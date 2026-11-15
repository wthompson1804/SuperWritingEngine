"""Re-label mid_hudson rows after the dog weight gate moved from 40 lb to 25 lb (2026-11-15).

Rows whose only recorded failure was a weight limit of 25-39 lb no longer fail on weight. Their prefix becomes
ELEVATOR_UNKNOWN (when the elevator is unknown) or is dropped (when elevator is yes). Limits under 25 lb still fail.
'under 40' wording in other notes is updated to the new gate. Idempotent.
"""
import csv, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
L = ROOT / "data/listings_raw/region_mid_hudson.csv"
B = ROOT / "data/reference/region_buildings_mid_hudson.csv"

def fix_note(n, wl, elev):
    m = re.match(r"BUILDING_FAILS: dog weight limit (\d+) lb \(under 40\)\.", n)
    if m:
        w = int(m.group(1))
        rest = n[m.end():].strip()
        if w >= 25:
            head = (f"ELEVATOR_UNKNOWN: no elevator stated on the page (likely garden-style walk-up, confirm). "
                    if elev != "yes" else "")
            return (head + f"Dog weight limit {w} lb passes the 25 lb gate (re-checked 2026-11-15; earlier marked failing under the 40 lb gate). " + rest).strip()
        return f"BUILDING_FAILS: dog weight limit {w} lb (under 25). " + rest
    return n

rows = list(csv.DictReader(open(L, newline="")))
cols = list(rows[0].keys())
changed = {}
for r in rows:
    n2 = fix_note(r["notes"], r["dog_weight_limit_lb"], r["elevator"])
    if n2 != r["notes"]:
        changed[r["building_name"]] = (r["dog_weight_limit_lb"], r["elevator"])
        r["notes"] = n2.strip()
with open(L, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
b = list(csv.DictReader(open(B, newline="")))
bc = list(b[0].keys())
for r in b:
    m = re.match(r"building_fails:dog weight limit (\d+) lb", r["verdict"])
    if m:
        w_ = int(m.group(1))
        if w_ >= 25:
            r["verdict"] = ("pass_on_weight_elevator_unknown" if not r["elevator"].startswith("yes") else "pass_with_units") + f": weight limit {w_} lb passes 25 lb gate"
        else:
            r["verdict"] = f"fails:dog weight limit {w_} lb (under 25)"
with open(B, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=bc); w.writeheader(); w.writerows(b)
print("changed listing rows for:", changed)
