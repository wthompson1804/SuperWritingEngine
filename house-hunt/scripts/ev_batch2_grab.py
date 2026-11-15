"""Evidence batch 2 helper: robots-checked fetch of one URL, saved under raw/evidence_batch2/, keyword contexts printed.
usage: ev_batch2_grab.py <key> <url> [regex] [width] [max]"""
import sys, json, re, subprocess
sys.path.insert(0, "scripts")
from h_mgmt_common import polite_get, BotWall, strip_tags
import lib
OUT = lib.ROOT / "raw" / "evidence_batch2"
def grab(key, url, pat=None, w=150, mx=8, refresh=False, ext="html"):
    p = OUT / f"{key}.{ext}"
    try:
        t, m = polite_get(url, "evidence_batch2", refresh=refresh, ext=ext)
    except BotWall as e:
        print("BLOCKED", key, e); return None
    except Exception as e:
        print("ERROR", key, repr(e)[:200]); return None
    p.write_text(t); (OUT / f"{key}.meta.json").write_text(json.dumps(m))
    txt = strip_tags(t)
    print(m["status"], key, len(t), "text", len(txt), m["retrieved_at"])
    if pat:
        seen = set()
        for mm in re.finditer(pat, txt):
            s = txt[max(0, mm.start()-w):mm.end()+w]
            if s[:60] in seen: continue
            seen.add(s[:60]); print("  |", s)
            if len(seen) >= mx: break
    return txt
if __name__ == "__main__":
    a = sys.argv[1:]
    grab(a[0], a[1], a[2] if len(a) > 2 else None, int(a[3]) if len(a) > 3 else 150, int(a[4]) if len(a) > 4 else 8)
