"""Evidence batch 5: re-fetch every listing URL (refresh) into raw/evidence_b5/. Idempotent via state file."""
import csv, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib
lib.HOST_DELAY.update({"www.trulia.com": 2.5, "www.zumper.com": 2.5, "www.apartmentlist.com": 2.5})
state_p = lib.RAW / "evidence_b5" / "_state.json"
state_p.parent.mkdir(parents=True, exist_ok=True)
state = json.loads(state_p.read_text()) if state_p.exists() else {}
rows = list(csv.DictReader(open(lib.DATA / "reference/evidence_batches/batch_5.csv")))
for r in rows:
    for u in dict.fromkeys(x.strip() for x in r["urls"].split("|")):
        if u in state: continue
        try:
            c, m = lib.cached_get(u, "evidence_b5", ext="html", refresh=True)
            state[u] = {"status": m["status"], "path": m.get("path"), "retrieved_at": m["retrieved_at"], "len": len(c)}
        except Exception as e:
            state[u] = {"status": "error", "err": str(e)[:200], "retrieved_at": lib.now_iso()}
        print(state[u].get("status"), state[u].get("len"), u, flush=True)
        state_p.write_text(json.dumps(state, indent=1))
        if state[u].get("status") in (403, 429):
            print("BLOCK - stopping host"); sys.exit(1)
