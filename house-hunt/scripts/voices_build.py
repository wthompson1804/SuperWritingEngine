"""Build data/voices/{neighborhood_quotes,neighborhood_survey,coverage}.csv from raw/voices_pool/*.jsonl.

Excerpts are whole sentences (one, or two adjacent) copied verbatim from a resident review or forum post.
Theme and sentiment are keyword classifications of the excerpt (stated in docs/harvest_notes/voices.md), not
judgments about the place. Idempotent: every run rewrites the three CSVs. Run verify_quotes.py afterwards.
"""
import csv, json, re, glob, collections, sys
import lib
from voices_targets import TRULIA, T

POOL = lib.RAW / "voices_pool"; OUT = lib.DATA / "voices"; OUT.mkdir(exist_ok=True)
MAXQ = 14
shown = list(csv.DictReader(open(lib.DATA / "reference/shown_neighborhoods.csv")))
hs = {r["hood_id"]: r for r in csv.DictReader(open(lib.DATA / "neighborhoods.csv"))}
shown.sort(key=lambda r: float(hs.get(r["id"], {}).get("drive_min") or 999))
NAME = {r["id"]: r["name"] for r in shown}

def load(name):
    p = POOL / name
    return [json.loads(l) for l in open(p)] if p.exists() else []
pool = load("trulia.jsonl") + load("niche.jsonl") + load("citydata.jsonl")
MANUAL = {}
mp = lib.ROOT / "scripts/voices_manual.json"   # optional hand edits: {"drop": [excerpt prefixes], "theme": {excerpt prefix: theme}, "sentiment": {...}}
if mp.exists(): MANUAL = json.load(open(mp))

TH = collections.OrderedDict([
 ("car_crime", r"car (break|theft|thefts|thieves|jack)|cars? (was|were|got|get|gets|been|being|is|are) (broken|stolen|vandal)|broke into (my|our|the|his|her) car|broken into|stolen car|car stolen|catalytic|car ?-?jack|cars? (can|could|might|will) (be|get) stolen|auto theft|vehicle theft|stole my car|vandaliz\w+ (my |our )?cars?|break-?ins"),
 ("safety", r"\bsafe\b|\bsafer\b|\bsafest\b|safety|unsafe|\bcrime|dangerous|at night|robber|mugg|police|shooting|sketchy|violen|gang|after dark|well[- ]lit|walk(ing)? alone|feel secure|drug"),
 ("parking", r"parking|\bpark (my|your|the|a) car|alternate side|find a spot|parking spot|garage"),
 ("dogs_green", r"\bdogs?\b|\bpets?\b|puppy|\bparks?\b(?!ing)|green space|greenery|\btrees?\b|tree-lined|trail|nature|garden|waterfront|\bbeach|hik(e|ing)|outdoor"),
 ("social_life", r"restaurant|\bbars?\b|nightlife|night life|caf[eé]|coffee shop|things to do|nothing to do|meet (new )?people|community events?|events|live music|social|going out|brewer|food scene|entertainment|boring|downtown"),
 ("noise", r"\bnois|\bloud|\bquiet|siren|peaceful|calm\b|music blasting|honking"),
 ("value", r"\brent\b|rents\b|expensive|afford|cost of living|pricey|overpriced|price|cheap|taxes|costly"),
 ("people", r"neighbors?\b|famil(y|ies)|young professionals|students|retirees|community|residents|friendly|welcoming|people (are|here)"),
 ("travel", r"commut|subway|\btrains?\b|\bbus(es)?\b|highway|lirr|metro-?north|nj transit|path\b|traffic|drive to|minutes (to|from)|transportation|transit|parkway|expressway"),
])
REGRET = r"can'?t wait to (leave|move)|moved (out|away)|i left\b|we left\b|would not recommend|wouldn'?t recommend|do not recommend|don'?t recommend|regret|not (move|live) here again|glad (i|we) (left|moved)|planning to (leave|move)|want to (leave|move out)|moving out"
SURPRISE = r"surpris|didn'?t expect|did not expect|hidden gem|underrated|pleasantly|to my surprise|never (thought|expected)"
FROM_NYC = r"moved (here )?from (queens|brooklyn|the bronx|bronx|manhattan|nyc|new york city|the city|astoria|flushing|jamaica|harlem)|coming from (queens|brooklyn|the bronx|manhattan|nyc|the city)"
POS = r"\blove|\bgreat|\bnice|beautiful|friendly|peaceful|\bclean\b|convenien|\bbest\b|\bgood\b|amazing|wonderful|enjoy|affordab|plenty|\beasy\b|vibrant|welcoming|excellent|perfect|favorite|well[- ]kept|well[- ]maintained|well[- ]lit|\bsafe\b|\bsafer\b|\bsafest\b|\bquiet\b|\bcalm\b|comfortable|lovely|charming|fantastic|awesome|pleasant|happy|recommend|walkable|lively|fun\b|gem\b"
NEG = r"unsafe|\bcrimes?\b|dangerous|expensive|\bdirty|nois[ye]|\bloud|crowded|homeless|break-?ins?|broken into|stolen|theft|robber|hard to find|difficult|\black\b|lacks|lacking|worst|\bbad\b|terrible|trash|garbage|litter|sketchy|violen|shooting|gang|drugs?\b|overpriced|traffic|pricey|congest|\brude|nightmare|limited|challeng\w+|\btough|nonexistent|\btight\b|hassle|frustrat\w+|\bsucks?\b|ticket(ed|ing|s)?\b|forbids|denied|lucky if|concern\w*|worr(y|ied|ies|isome)|careful|cautio\w+|\bwary|\bavoid|not the safest|no parking|struggle|impossible|problem|issues?\b|downside|\bpoor\b|horrible|awful|scary|afraid|vandal|rats?\b|nothing to do|boring|not recommend|decline|worse|unfortunately|disappoint|high (rent|taxes|cost|prices)|costly|run[- ]down|neglect|can'?t wait to leave|filthy|sirens"
NEGATE = r"(\bnot|n't|n’t|\bnever|\bno|\bisnt|\bdont|\bhardly|\bbarely|\blittle|\blow|\bless|\bfew|\bwithout|\bfree of|\brarely)\s+(\w+\s+){0,3}$"
BLOCK = r"\b(white|black|blacks|whites|hispanic|latin[oax]s?|asian|jewish|jews?|muslims?|christian|catholic|chinese|korean|indian|russian|uzbek|italian|irish|greek|polish|caribbean|african|haitian|jamaican|dominican|mexican|puerto rican|bangladeshi|pakistani|arab|ethnic\w*|racial\w*|race|racis\w+|religio\w+|orthodox|hasid\w+|dominicans?|bachata|bukharian|bengalis?|haitians?|brazilians?|jamaicans?|immigrants?|minorit\w+|synagogues?|mosques?)\b"

def sentences(text):
    out = []
    for para in text.split("\n"):
        para = re.sub(r"\s+", " ", para).strip()
        if not para: continue
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“'(])", para)
        out.append([p for p in parts if p])
    return out

def sentiment(x, rating):
    xl = x.lower(); p = n = 0
    xl, k = re.subn(r"crimes?( rates?)? (is|are|was|has been|have been|stays?|remains?) (very |relatively |pretty |quite |fairly |generally )?(low|rare|minimal|down|not (a|an) (big |major )?(issue|problem))|(low|little to no|little|minimal|no|hardly any) crime", " ", xl); p += k
    for m in re.finditer(POS, xl):
        if re.search(NEGATE, xl[max(0, m.start() - 30):m.start()]): n += 1
        else: p += 1
    for m in re.finditer(NEG, xl):
        if re.search(NEGATE, xl[max(0, m.start() - 30):m.start()]): p += 1
        else: n += 1
    if p and n: return "mixed"
    if p: return "positive"
    if n: return "negative"
    if rating: return "positive" if rating >= 4 else "negative" if rating <= 2 else "mixed"
    return None

def theme(x):
    xl = x.lower()
    if re.search(REGRET, xl): return "regret", 3
    for t, rx in TH.items():
        k = len(re.findall(rx, xl))
        if k:
            if t in ("people", "travel", "value", "noise") and re.search(SURPRISE, xl): return "surprise", 2
            return t, k
    if re.search(SURPRISE, xl): return "surprise", 2
    return None, 0

def context(r, x, full):
    bits = []
    w = (r.get("who") or "").strip()
    if w: bits.append(w.lower())
    if r.get("category") and r["category"] != "General": bits.append(f"posted under '{r['category']}'")
    fl = full.lower()
    m = re.search(r"(lived|living|been) (here|in [A-Z][\w ]{2,25}?) (for )?(over |about |almost |nearly |more than )?((\d+|a|one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty)\+? (years?|months?|decades?))", full)
    if m: bits.append("says lived there " + (m.group(4) or "") + m.group(5))
    elif re.search(r"my (whole|entire) life|all my life|born and raised|grew up here|grew up in", fl): bits.append("says grew up / lifelong there")
    if re.search(r"\bmy dogs?\b|\bour dogs?\b|i have a dog|we have a dog|dog owner|walk(ing)? my dog", fl): bits.append("dog owner")
    m = re.search(FROM_NYC, fl)
    if m: bits.append("moved from " + (m.group(2) or m.group(3)).title().replace("Nyc", "NYC"))
    if re.search(r"\bi rent\b|as a renter|my landlord|my apartment|our apartment", fl): bits.append("renter/apartment dweller")
    if r["source"] == "city-data" and not bits: bits.append("forum poster (relationship to the place not stated)")
    return "; ".join(dict.fromkeys(bits))

CONTRAST = r"\b(but|however|although|though|except|could be better|wish|downside|unfortunately|yet)\b"
def arealess(x, r):
    """Blank the place name so that 'Rego Park' or 'Kew Gardens' does not count as a park or garden."""
    names = {NAME.get(r["hood_id"], "")} | {re.sub(r" Reviews - Niche$| - Niche$", "", r.get("area") or "")}
    for n in list(names):
        for part in re.split(r"[-()]|, ", n): names.add(part.strip())
    for n in sorted((n for n in names if len(n) > 4), key=len, reverse=True):
        x = re.sub(re.escape(n), "PLACE", x, flags=re.I)
    return x

def cd_candidates(r):
    out = []
    norm = re.sub(r"\s+", " ", r["text"])
    for k in MANUAL.get("citydata_keep", []):
        if k["post_id"] != r["post_id"]: continue
        if k["excerpt"] not in norm: print("WARN manual excerpt not in post", k["post_id"], k["excerpt"][:50]); continue
        out.append(dict(ex=k["excerpt"], theme=k["theme"], sent=k["sentiment"], score=50, r=r, ctx=k["context"]))
    return out

def candidates(r, hood_id):
    if r["source"] == "city-data": return cd_candidates(r)
    if r["source"] == "niche" and r.get("who") not in ("Current Resident", "Former Resident"): return []
    full = r["text"]; year = int(r["date"][:4]); out = []
    for para in sentences(full):
        for i in range(len(para)):
            for ex in (para[i], " ".join(para[i:i + 2]) if i + 1 < len(para) else None):
                if not ex or not (55 <= len(ex) <= 330): continue
                if re.search(BLOCK, ex, re.I) or re.search(r"\bDR\b|[Ll]ittle [A-Z]", ex) or "http" in ex or ex.endswith("?"): continue
                if r["source"] == "city-data":
                    multi = len(r.get("_hoods", [])) > 1 or r.get("_generic")
                    nm = NAME[hood_id].split("-")[0].split("(")[0].strip().lower()
                    if multi and nm not in ex.lower(): continue
                    if not multi and nm not in full.lower() and nm not in r["area"].lower(): continue
                exa = arealess(ex, r)
                t, k = theme(exa)
                if not t: continue
                s = sentiment(exa, r.get("rating"))
                if not s: continue
                st = r.get("rating")
                if s == "positive" and re.search(CONTRAST, exa.lower()): s = "mixed"
                if st and ((s == "negative" and st >= 4) or (s == "positive" and st <= 2)): s = "mixed"
                pair = ex is not para[i]
                if pair and (theme(arealess(para[i], r))[0] is None or theme(arealess(para[i + 1], r))[0] is None): k -= 2
                elif pair: k -= 0.5
                sc = k + (2 if year >= 2024 else 1 if year >= 2022 else -2 if year < 2019 else 0)
                sc += 1 if re.search(r"\b(I|my|we|our|I've|I'm)\b", ex) else 0
                sc += 1 if 90 <= len(ex) <= 260 else 0
                sc += 1 if t in ("car_crime", "safety", "parking", "dogs_green") else 0
                sc += 1 if r["source"] != "niche" else 0
                sc -= 1.5 if len(re.findall(r",", ex)) >= 5 else 0      # laundry lists read badly
                out.append(dict(ex=ex, theme=t, sent=s, score=sc, r=r, ctx=context(r, ex, full)))
    return out

def pick(cands):
    chosen = []; per_post = collections.Counter(); per_theme = collections.Counter()
    def ok(c):
        if per_post[c["r"]["post_id"]] >= 2 or per_theme[c["theme"]] >= 3: return False
        return not any(c["ex"] in d["ex"] or d["ex"] in c["ex"] or (c["r"]["post_id"] == d["r"]["post_id"] and set(c["ex"].split(". ")) & set(d["ex"].split(". "))) for d in chosen)
    def take(c):
        chosen.append(c); per_post[c["r"]["post_id"]] += 1; per_theme[c["theme"]] += 1
    cands = sorted(cands, key=lambda c: -c["score"])
    themes = ["car_crime", "safety", "parking", "dogs_green", "social_life", "noise", "value", "people", "regret", "surprise", "travel"]
    for t in themes:                                   # pass 1: best per theme
        for c in cands:
            if c["theme"] == t and ok(c): take(c); break
    for t in themes:                                   # pass 2: a different sentiment per theme
        if len(chosen) >= MAXQ: break
        have = {c["sent"] for c in chosen if c["theme"] == t}
        for c in cands:
            if c["theme"] == t and c["sent"] not in have and ok(c): take(c); break
    return chosen[:MAXQ]

# ---------- quotes
tmeta = {}
for l in load("citydata_status.json") if False else []: pass
cd_status = json.load(open(POOL / "citydata_status.json")) if (POOL / "citydata_status.json").exists() else []
hoods_of = {s["url"]: s.get("hoods", []) for s in cd_status}
GENERIC = ("nice-diverse-suburb", "montclair-state-university", "move-westchester-advice")
by_hood = collections.defaultdict(dict)
for r in pool:
    if r["kind"] != "review": continue
    if r["source"] == "city-data":
        base = r["url"].split("#")[0]; r["_hoods"] = hoods_of.get(base, []); r["_generic"] = any(g in base for g in GENERIC)
    by_hood[r["hood_id"]].setdefault((r["source"], r["post_id"]), r)
# generic City-Data threads: let any shown hood named in a post use it
for r in [x for x in pool if x["kind"] == "review" and x["source"] == "city-data" and x.get("_generic")]:
    for hid, nm in NAME.items():
        n0 = nm.split("-")[0].split("(")[0].strip()
        if len(n0) > 5 and n0.lower() in r["text"].lower() and hid.split(":")[0] in ("nj", "ny", "ct"):
            if (hid.startswith("nj") and "new-jersey" in r["url"]) or (hid.startswith("ny") and "westchester" in r["url"]):
                r2 = dict(r, hood_id=hid); by_hood[hid].setdefault((r["source"], r["post_id"]), r2)

qrows = []; cov = {}
for h in shown:
    hid = h["id"]; cands = []
    for r in by_hood.get(hid, {}).values(): cands += candidates(r, hid)
    cands = [c for c in cands if not any(c["ex"].startswith(d) for d in MANUAL.get("drop", []))]
    for c in cands:
        for k, v in MANUAL.get("theme", {}).items():
            if c["ex"].startswith(k): c["theme"] = v
        for k, v in MANUAL.get("sentiment", {}).items():
            if c["ex"].startswith(k): c["sent"] = v
    for c in pick(cands):
        r = c["r"]
        qrows.append(dict(hood_id=hid, neighborhood=h["name"], excerpt=c["ex"], theme=c["theme"], sentiment=c["sent"], speaker_context=c["ctx"],
                          source_site={"trulia": "trulia.com", "niche": "niche.com", "city-data": "city-data.com/forum"}[r["source"]],
                          post_date=r["date"], permalink=r["url"], retrieved_at=r["retrieved_at"], stars=r.get("rating") or "",
                          source_area=re.sub(r" Reviews - Niche$| - Niche$", "", r.get("area") or "")[:90]))
QF = ["hood_id", "neighborhood", "excerpt", "theme", "sentiment", "speaker_context", "source_site", "post_date", "permalink", "retrieved_at", "stars", "source_area"]
with open(OUT / "neighborhood_quotes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, QF); w.writeheader(); w.writerows(qrows)

# ---------- survey
srows = {}
TMEAS = {"DogFriendly": "trulia_dog_friendly_pct", "WellLitStreets": "trulia_well_lit_pct", "WalkableToRestaurants": "trulia_walkable_restaurants_pct",
         "NeedACar": "trulia_car_needed_pct", "LongTermResidents": "trulia_plan_to_stay_pct", "PeopleWouldWalkAloneAtNight": "trulia_walk_alone_at_night_pct",
         "EasyParking": "trulia_easy_parking_pct", "Quiet": "trulia_quiet_pct", "FriendlyNeighbors": "trulia_friendly_neighbors_pct",
         "CommunityEvents": "trulia_community_events_pct", "WalkableToGroceries": "trulia_walkable_groceries_pct", "Sidewalks": "trulia_sidewalks_pct",
         "KidsPlayOutside": "trulia_kids_play_outside_pct", "HolidaySpirit": "trulia_holiday_spirit_pct", "WellKeptYards": "trulia_yards_well_kept_pct",
         "Wildlife": "trulia_wildlife_pct", "MinResponseCount": "trulia_min_response_count", "ReviewCount": "trulia_review_count"}
for r in pool:
    if r["kind"] != "stat": continue
    if r["source"] == "trulia":
        srows[(r["hood_id"], TMEAS[r["measure"]], r["area"])] = dict(hood_id=r["hood_id"], neighborhood=NAME[r["hood_id"]], source_site="trulia.com", measure=TMEAS[r["measure"]],
            value=r["value"], as_of=r["retrieved_at"][:10], source_url=r["url"], source_area=r["area"], note="neighborhood page")
    else:
        if "/reviews/" not in r["url"]: continue
        area = re.sub(r" Reviews - Niche$", "", r["area"])
        srows[(r["hood_id"], r["measure"], area)] = dict(hood_id=r["hood_id"], neighborhood=NAME[r["hood_id"]], source_site="niche.com", measure=r["measure"], value=r["value"],
            as_of=r["retrieved_at"][:10], source_url=r["url"], source_area=area, note="")
# Trulia survey shares already present in listing pages cached by the earlier listing harvest (no new requests)
QMAP = [("sidewalks", "Sidewalks"), ("grocery", "WalkableToGroceries"), ("restaurants", "WalkableToRestaurants"), ("dog-friendly", "DogFriendly"), ("well-lit", "WellLitStreets"),
        ("walk alone at night", "PeopleWouldWalkAloneAtNight"), ("stay at least 5 years", "LongTermResidents"), ("holiday spirit", "HolidaySpirit"), ("kids play", "KidsPlayOutside"),
        ("yards", "WellKeptYards"), ("quiet", "Quiet"), ("car needed", "NeedACar"), ("parking easy", "EasyParking"), ("neighbors friendly", "FriendlyNeighbors"),
        ("wildlife", "Wildlife"), ("community events", "CommunityEvents")]
want = collections.defaultdict(list)
for hid, lst in TRULIA.items():
    for path, area in lst: want[T + path].append((hid, area))
found = {}
for f in sorted(glob.glob(str(lib.RAW / "trulia/*.html"))):
    s = open(f, errors="ignore").read()
    m = re.search(r'"ndpUrl":"(https://www.trulia.com/n/[^"]+)"', s)
    if not m or m.group(1) not in want or m.group(1) in found: continue
    qa = re.findall(r'\{"question":"([^"]+)","answer":"((As of [^,]+), (\d+)% of users say [^"]+)"', s)
    if not qa: continue
    try: meta = json.load(open(f.rsplit(".", 1)[0] + ".meta.json"))
    except Exception: continue
    found[m.group(1)] = (qa, meta)
for ndp, (qa, meta) in found.items():
    for hid, area in want[ndp]:
        if hid not in NAME or any(k[0] == hid and k[2] == area and v["note"] == "neighborhood page" for k, v in srows.items()): continue
        for q, ans, asof, pct in qa:
            typ = next((t for k, t in QMAP if k in q.lower()), None)
            if not typ: continue
            srows[(hid, TMEAS[typ], area)] = dict(hood_id=hid, neighborhood=NAME[hid], source_site="trulia.com", measure=TMEAS[typ], value=pct,
                as_of=asof.replace("As of ", "") + " (as stated on page)", source_url=meta["url"], source_area=area,
                note=f"read from a listing page cached {meta['retrieved_at'][:10]}; neighborhood page {ndp}")
SF = ["hood_id", "neighborhood", "source_site", "measure", "value", "as_of", "source_url", "source_area", "note"]
order = {h["id"]: i for i, h in enumerate(shown)}
with open(OUT / "neighborhood_survey.csv", "w", newline="") as f:
    w = csv.DictWriter(f, SF); w.writeheader(); w.writerows(sorted(srows.values(), key=lambda r: (order[r["hood_id"]], r["source_site"], r["source_area"], r["measure"])))

# ---------- coverage
status = load("_status.jsonl")
themes = ["safety", "car_crime", "parking", "dogs_green", "social_life", "noise", "value", "people", "travel", "regret", "surprise", "other"]
with open(OUT / "coverage.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["hood_id", "neighborhood", "drive_min", "quotes_total"] + [f"q_{t}" for t in themes] + ["survey_measures", "sources_worked", "sources_skipped"])
    for h in shown:
        hid = h["id"]; q = [r for r in qrows if r["hood_id"] == hid]; c = collections.Counter(r["theme"] for r in q)
        worked = []; skipped = []
        nq = collections.Counter(r["source_site"] for r in q)
        st = [s for s in status if s["hood_id"] == hid]
        n_ok = list({s["title"]: s for s in st if s["source"] == "niche" and s.get("status") == 200 and "/reviews/" in s["url"] and "?page" not in s["url"] and "Reviews" in (s.get("title") or "")}.values())
        if any(s["source"] == "niche" and s.get("status") == 403 for s in st): skipped.append("niche: HTTP 403 on this place's review page, not retried")
        if n_ok: worked.append("niche (" + "; ".join(re.sub(r" Reviews - Niche$", "", s["title"]) + f": {s.get('reviews')} reviews read" for s in n_ok) + f"; {nq['niche.com']} quotes)")
        else:
            bad = [s["url"].split("/")[-3] for s in st if s["source"] == "niche" and s.get("status") == 404]
            if not any("403" in x for x in skipped): skipped.append("niche: no place page found (404 for " + ", ".join(bad) + ")" if bad else "niche: no page tried")
        t_ok = [s for s in st if s["source"] == "trulia" and s.get("status") == 200]
        tsurv = sorted({r["source_area"] for r in srows.values() if r["hood_id"] == hid and r["source_site"] == "trulia.com"})
        if t_ok: worked.append(f"trulia neighborhood page ({nq['trulia.com']} quotes, survey)")
        elif tsurv: worked.append("trulia survey shares from cached listing pages (" + "; ".join(tsurv) + ")"); skipped.append("trulia comments: neighborhood pages returned a PerimeterX CAPTCHA (403) after the first page, stopped")
        elif hid in TRULIA: skipped.append("trulia: CAPTCHA wall on neighborhood pages; no survey block in cached listing pages")
        else: skipped.append("trulia: no matching neighborhood page identified; neighborhood pages behind CAPTCHA wall")
        if nq["city-data.com/forum"]: worked.append(f"city-data forum ({nq['city-data.com/forum']} quotes)")
        else: skipped.append("city-data: no usable recent thread located (forum search is disallowed; only index pages and a few web searches were used)")
        skipped.append("local blogs: not attempted (time)")
        w.writerow([hid, h["name"], hs[hid]["drive_min"], len(q)] + [c.get(t, 0) for t in themes] + [sum(1 for r in srows.values() if r["hood_id"] == hid), " | ".join(worked), " | ".join(skipped)])
print("quotes", len(qrows), "hoods with quotes", len({r["hood_id"] for r in qrows}), "survey rows", len(srows))
print(collections.Counter(r["theme"] for r in qrows)); print(collections.Counter(r["source_site"] for r in qrows)); print(collections.Counter(r["sentiment"] for r in qrows))
