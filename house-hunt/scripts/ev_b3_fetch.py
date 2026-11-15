"""Evidence batch 3: polite fetch helper. usage: ev_b3_fetch.py URL [URL...] [--refresh]
Prints status, cache path and size per URL. Robots (incl. Claude-named groups) checked by h_mgmt_common."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib, h_mgmt_common as C
from urllib.parse import urlparse
SRC = "evidence_b3"
def get(url, refresh=False):
    host = urlparse(url).netloc
    lib.HOST_DELAY[host] = max(lib.HOST_DELAY.get(host, 0), 2.5)
    try:
        t, m = C.polite_get(url, SRC, refresh=refresh, retries=2, timeout=40)
        return t, m
    except C.BotWall as e:
        return None, {"url": url, "status": "blocked", "err": str(e), "retrieved_at": lib.now_iso()}
    except Exception as e:
        return None, {"url": url, "status": "error", "err": str(e)[:200], "retrieved_at": lib.now_iso()}
if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    for u in [a for a in sys.argv[1:] if not a.startswith("--")]:
        t, m = get(u, refresh)
        print(json.dumps({k: m.get(k) for k in ("status", "path", "retrieved_at", "err")}), len(t or ""), u, flush=True)
