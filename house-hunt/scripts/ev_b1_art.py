"""Fetch an article (robots-checked) and print title, dates and sentences matching a regex."""
import sys, re, json
sys.path.insert(0, "scripts")
import ev_b1_fetch as f
kw = sys.argv[1]
for u in sys.argv[2:]:
    c, m = f.get(u)
    print("##", u, m.get("status"), m.get("why", ""), m.get("retrieved_at", ""))
    if not c or m["status"] != 200: continue
    h = c.decode("utf8", "replace")
    t = re.search(r"<title[^>]*>(.*?)</title>", h, re.S); print("   title:", f.text_of((t.group(1) if t else "").encode())[:160])
    dates = re.findall(r'"(?:datePublished|dateModified)"\s*:\s*"([^"]+)"', h)[:3] + re.findall(r'property="article:published_time" content="([^"]+)"', h)[:1] + re.findall(r'<time[^>]*datetime="([^"]+)"', h)[:2]
    print("   dates:", dates)
    txt = f.text_of(c)
    sents = re.split(r"(?<=[.!?])\s+", txt)
    n = 0
    for s in sents:
        if re.search(kw, s, re.I) and 30 < len(s) < 420:
            print("   -", s); n += 1
            if n >= 14: break
