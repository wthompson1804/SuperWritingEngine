"""Print the visible text of a page (polite fetch into raw/region_connecticut/), optionally only windows around a regex.
Usage: python3 h_region_connecticut_text.py URL [regex] [width]"""
import re, sys
from h_mgmt_common import polite_get, BotWall, strip_tags
u = sys.argv[1]; rx = sys.argv[2] if len(sys.argv) > 2 else None; w = int(sys.argv[3]) if len(sys.argv) > 3 else 150
try:
    h, m = polite_get(u, "region_connecticut")
except BotWall as e:
    print("BOTWALL", e); sys.exit()
except Exception as e:
    print("ERR", str(e)[:200]); sys.exit()
t = re.sub(r"\s+", " ", strip_tags(h))
print(f"## {u} status={m['status']} seen={m['retrieved_at']} raw={m['path']} textlen={len(t)}")
if not rx: print(t[:6000])
else:
    last = -10**9
    for mm in re.finditer(rx, t, re.I):
        if mm.start() - last < w: continue
        last = mm.start(); print("  ~", t[max(0, mm.start() - w): mm.end() + w])
