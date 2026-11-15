"""Evidence pass, batch 4: robots-checked fetch of one page; prints visible text (or greps it).
Usage: evidence_batch_4_get.py URL [regex] ; robots groups for Claude agents and * must all allow the path."""
import html, re, sys, time
from pathlib import Path
from urllib.parse import urlparse
from urllib import robotparser
sys.path.insert(0, str(Path(__file__).parent))
import lib
SRC = "evidence_b4"
def allowed(url):
    p = urlparse(url)
    try:
        c, m = lib.cached_get(f"{p.scheme}://{p.netloc}/robots.txt", SRC, ext="txt", retries=1, timeout=30)
    except RuntimeError as e:
        return False, f"robots fetch failed: {e}"
    if m["status"] in (401, 403):
        return False, f"robots.txt HTTP {m['status']}"
    if m["status"] != 200:
        return True, f"robots.txt HTTP {m['status']} (treated as no rules)"
    rp = robotparser.RobotFileParser(); rp.parse(c.decode("utf8", "replace").splitlines())
    for ua in ("ClaudeBot", "Claude-User", "Claude-SearchBot", "anthropic-ai", "house-hunt-research"):
        if not rp.can_fetch(ua, url):
            return False, f"robots disallows for {ua}"
    cd = rp.crawl_delay("ClaudeBot") or rp.crawl_delay("*")
    return True, f"ok crawl_delay={cd}"
def text_of(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "|", t)))
    return re.sub(r"(\|\s*)+", "|", t)
if __name__ == "__main__":
    url = sys.argv[1]
    ok, why = allowed(url)
    print("ROBOTS:", why)
    if not ok: sys.exit(0)
    time.sleep(2)
    try:
        c, m = lib.cached_get(url, SRC, ext="html", retries=1, timeout=40)
    except RuntimeError as e:
        print("FETCH ERROR", str(e)[-200:]); sys.exit(0)
    print("STATUS", m["status"], "at", m["retrieved_at"], "len", len(c))
    raw = c.decode("utf8", "replace")
    vt = text_of(raw)
    for mm in re.finditer(r'"(datePublished|dateModified)"\s*:\s*"([^"]+)"|property="article:(published_time|modified_time)" content="([^"]+)"', raw):
        print("DATE", mm.group(0)[:90])
    if len(sys.argv) > 2:
        for mm in re.finditer(sys.argv[2], vt, re.I):
            print("  ~", vt[max(0, mm.start()-250):mm.start()+350])
    else:
        print(vt[:int(sys.argv[3]) if len(sys.argv) > 3 else 6000])
