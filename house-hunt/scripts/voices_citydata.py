"""City-Data forum threads for shown neighborhoods (user-requested lookups; robots `*` group: thread and forum
index pages allowed, /forum/search.php and /forum/members not touched). Thread URLs were found by reading the forum
index pages (raw/voices_pool/citydata_index.json) or a web search; text is read only from the thread page itself.
Usernames are removed from the cached copy. Output: raw/voices_pool/citydata.jsonl
"""
import json, re, html
import lib, voices_lib as v
B = "https://www.city-data.com/forum/"
THREADS = [  # (hood_ids, thread path, how found)
 (["ny:new-rochelle"], "westchester-county/3496962-how-life-new-rochelle.html", "forum index"),
 (["ny:new-rochelle"], "westchester-county/3423620-new-rochelle-come-up.html", "forum index"),
 (["ny:white-plains"], "westchester-county/3513383-white-plains-good-area.html", "forum index"),
 (["ny:white-plains"], "westchester-county/3282955-white-plains-growing-decline.html", "forum index"),
 (["ny:mount-vernon"], "westchester-county/3469191-mount-vernon-ny.html", "forum index"),
 (["ny:yonkers"], "westchester-county/3481804-peabody-hill-yonkers.html", "forum index"),
 (["ny:yonkers", "ny:new-rochelle"], "westchester-county/2720438-move-westchester-advice-please-yonkers-new.html", "web search"),
 (["ny:port-chester"], "westchester-county/3447678-port-chester-development.html", "forum index"),
 (["nj:jersey-city"], "new-jersey/3500876-nice-diverse-suburb-short-commute-jersey.html", "forum index"),
 (["nj:montclair"], "new-jersey/3538990-montclair-state-university-area-rentals.html", "forum index"),
 (["ct:stamford"], "connecticut/3537693-stamford-must-visit-gem.html", "forum index"),
 (["ny:forest-hills"], "new-york-city/2579836-forest-hills-single-young-person-2.html", "web search"),
 (["ny:forest-hills"], "new-york-city/2579836-forest-hills-single-young-person.html", "web search (page 1 of the same thread)"),
 (["ny:jamaica"], "new-york-city/2122955-working-living-jamaica-queens-2.html", "web search"),
 (["ny:jamaica"], "new-york-city/2122955-working-living-jamaica-queens.html", "web search (page 1 of the same thread)"),
]
def text(x):
    x = re.sub(r"<br\s*/?>", "\n", x)
    x = html.unescape(re.sub(r"<[^>]+>", " ", x))
    return "\n".join(re.sub(r"[ \t\r\f\v]+", " ", l).strip() for l in x.split("\n") if l.strip())
def scrub(s):
    s = re.sub(r'(class="bigusername"[^>]*>).*?</a>', r"\1[member]</a>", s, flags=re.S)
    s = re.sub(r"(Originally Posted by <strong>).*?(</strong>)", r"\1[member]\2", s, flags=re.S)
    s = re.sub(r"/forum/members/[^\"'\s>]+", "/forum/members/[member]", s)
    s = re.sub(r"alt='[^']*won \$[^']*'", "alt=''", s, flags=re.S)
    return s
def main():
    out = []; log = []
    for hoods, path, how in THREADS:
        url = B + path
        try: c, m = v.get(url, "voices_citydata")
        except Exception as e: log.append(dict(url=url, status="error", note=str(e)[:100])); continue
        s = c.decode("utf-8", "ignore")
        if m["status"] != 200 or "post_message_" not in s:
            log.append(dict(url=url, status=m["status"], note="no posts / blocked")); 
            if m["status"] in (403, 429): break
            continue
        s2 = scrub(s); (lib.ROOT / m["path"]).write_bytes(s2.encode("utf-8")); s = s2
        title = text(re.search(r"<title>(.*?)</title>", s, re.S).group(1))
        n = 0
        for blk in re.split(r'(?=<table class="tborder" id="post\d+")', s)[1:]:
            pid = re.match(r'<table class="tborder" id="post(\d+)"', blk).group(1)
            d = re.search(r"(\d\d)-(\d\d)-(\d{4}), \d", blk)
            b = re.search(r'<div id="post_message_%s">(.*?)<!-- / message -->' % pid, blk, re.S)
            if not d or not b: continue
            body = re.sub(r'<div style="margin:20px; margin-top:5px; ">.*?</table>\s*</div>', " ", b.group(1), flags=re.S)  # drop quoted posts
            for h in hoods:
                out.append(dict(hood_id=h, source="city-data", url=url + "#post" + pid, area=title, kind="review", post_id=pid, text=text(body),
                                date=f"{d.group(3)}-{d.group(1)}-{d.group(2)}", who="", category="", rating=None, retrieved_at=m["retrieved_at"], path=m["path"], how=how))
            n += 1
        log.append(dict(url=url, status=200, posts=n, title=title, hoods=hoods, how=how)); print(url, n, title[:70], flush=True)
    with open(lib.RAW / "voices_pool/citydata.jsonl", "w") as f:
        for r in out: f.write(json.dumps(r) + "\n")
    json.dump(log, open(lib.RAW / "voices_pool/citydata_status.json", "w"), indent=1)
main()
