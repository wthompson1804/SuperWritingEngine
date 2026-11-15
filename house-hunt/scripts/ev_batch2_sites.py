"""Evidence batch 2: fetch building-site pages (robots-checked) and print gate-fact sentences.
usage: ev_batch2_sites.py key=url [key=url ...]"""
import sys, re
sys.path.insert(0, "scripts")
from ev_batch2_grab import grab
PAT = r"(?i)\b(elevators?|\d+[- ]stor(?:y|ies)|[a-z]+[- ]story|lbs?\.?|pounds?|weight (?:limit|restriction)|breed|pet rent|pet fee|pet deposit|per pet|garage|parking)\b"
for a in sys.argv[1:]:
    if a.startswith("-"): continue
    k, u = a.split("=", 1)
    txt = grab(k, u, None)
    if not txt: continue
    seen = []
    for m in re.finditer(PAT, txt):
        s = txt[max(0, m.start()-110):m.end()+140]
        if any(s[:50] in x or x[60:110] in s for x in seen): continue
        seen.append(s)
        if len(seen) > 7: break
    for s in seen: print("   |", s)
