import sys, re
sys.path.insert(0,"scripts")
import ev_b1_fetch as f
from urllib.parse import urljoin
for u in sys.argv[1:]:
    c,m=f.get(u)
    print("##",u,m.get("status"),m.get("why",""),len(c or b""))
    if not c or m["status"]!=200: continue
    h=c.decode("utf8","replace")
    links=sorted(set(urljoin(u,x) for x in re.findall(r'href="([^"#]+)"',h) if re.search(r"pet|amenit|floor|faq|avail|feature|parking|neighbo|residen|fees",x,re.I) and not re.search(r"\.(css|js|png|jpg|svg|woff)",x)))
    for l in links[:25]: print("   ",l)
