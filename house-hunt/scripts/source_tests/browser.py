"""Robots-checked headless-browser probe. usage: python3 browser.py name=url [name=url ...]
Checks robots.txt ('*' group) with probe.py logic, then renders allowed URLs with render.js.
Rendered HTML -> raw/source_tests/<host>/<name>.browser.html; rows -> raw/source_tests/_browser.jsonl"""
import json, subprocess, sys, time
from pathlib import Path
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).parent))
import probe

HERE = Path(__file__).parent
for arg in sys.argv[1:]:
    name, url = arg.split("=", 1)
    u = urlparse(url)
    rb = probe.robots_for(u.scheme, u.netloc)
    path = (u.path or "/") + (("?" + u.query) if u.query else "")
    ok = rb["mode"] == "none" or (rb["mode"] == "rules" and probe.allowed(rb["star"], path)[0])
    row = {"name": name, "url": url, "at": probe.now(), "robots_allowed": ok}
    if ok:
        time.sleep(2.1)
        out = probe.OUT / u.netloc / f"{name}.browser.html"
        p = subprocess.run(["node", str(HERE / "render.js"), url, str(out)], capture_output=True, text=True, timeout=120)
        try:
            row.update(json.loads(p.stdout.strip().splitlines()[-1]))
        except Exception:
            row["error"] = (p.stdout + p.stderr)[-500:]
    else:
        row["skipped"] = "disallowed by robots.txt"
    with open(probe.OUT / "_browser.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row)[:1500], flush=True)
