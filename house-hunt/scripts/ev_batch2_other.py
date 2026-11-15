"""Evidence batch 2: refresh the non-Apartment-List listing pages; save text dumps to raw/evidence_batch2/."""
import sys, json, re
sys.path.insert(0, "scripts")
from h_mgmt_common import polite_get, BotWall, strip_tags
import lib
OUT = lib.ROOT / "raw" / "evidence_batch2"
URLS = {
 "gc_jefferson": "https://www.gardencommunities.com/Properties/NJ/Bergen/The-Jefferson-Hackensack.aspx",
 "gc_pondview": "https://www.gardencommunities.com/Properties/NJ/Morris/Pondview-Estates.aspx",
 "blt_beacon_avail": "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/availability/",
 "blt_beacon": "https://bltliveworkplay.com/apartments/jersey-city/the-beacon/",
 "gs_quincy": "https://www.greystar.com/the-quincy-new-brunswick-nj/p_17425",
 "gs_grand": "https://www.greystar.com/the-grand-west-new-york-nj/p_22449",
 "gs_parq": "https://www.greystar.com/500-parq-parisppany-nj/p_20984",
 "zu_clinton": "https://www.zumper.com/apartment-buildings/p1647219/clinton-flats-newark-central-business-district-newark-nj",
 "zu_palisade": "https://www.zumper.com/listings/30002373p/1-bedroom-north-bergen-nj",
 "av_9206": "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge/apartment/NJ032-NJ032-009-9206",
 "av_9204": "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge/apartment/NJ032-NJ032-009-9204",
 "av_oldbridge": "https://www.avaloncommunities.com/new-jersey/old-bridge-apartments/avalon-old-bridge",
}
for k, u in URLS.items():
    if len(sys.argv) > 1 and k not in sys.argv[1:]:
        continue
    try:
        t, m = polite_get(u, "evidence_batch2", refresh=True)
    except BotWall as e:
        print("BLOCKED", k, e); continue
    (OUT / f"{k}.html").write_text(t)
    (OUT / f"{k}.meta.json").write_text(json.dumps(m))
    print(m["status"], k, len(t), m["retrieved_at"])
