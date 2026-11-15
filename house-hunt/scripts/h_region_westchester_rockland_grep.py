"""Ad-hoc reader for the region pass: fetch one page through polite_get (cache raw/region_westchester_rockland/)
and print the text around a regex. Usage: python3 h_region_westchester_rockland_grep.py '<regex>' <url> [width] [max]"""
import re, sys
from h_mgmt_common import polite_get, strip_tags, BotWall
rx, url = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 200
mx = int(sys.argv[4]) if len(sys.argv) > 4 else 8
try:
    h, m = polite_get(url, "region_westchester_rockland")
except BotWall as e:
    print("BLOCK", e); sys.exit()
t = strip_tags(h)
print(m["status"], m["retrieved_at"], len(t), m.get("path"))
last, n = -9999, 0
for mm in re.finditer(rx, t):
    if mm.start() - last < w: continue
    last = mm.start(); n += 1
    print(" >", t[max(0, mm.start() - w // 2):mm.start() + w])
    if n >= mx: break
