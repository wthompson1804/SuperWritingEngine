"""Door-to-door public-transit lookup between any point and Jamaica LIRR station (LIRR GTFS stop_id 102).

    from tools.transit import route
    route(40.7196, -73.8448, when="sat_midday")

`when` is one of
    sat_midday              point -> Jamaica, leave the door every 15 min, Sat 10:00-13:00
    sun_evening_return      Jamaica -> point, leave Jamaica every 15 min, Sun 17:00-20:00
    weekday_evening_return  Jamaica -> point, leave Jamaica every 15 min, weekday 18:00-19:00

Every result also carries `last_departure_from_jamaica_sat` (latest Saturday-night departure from Jamaica,
after 21:00, that still reaches the point before 05:00 Sunday).

How it works (details in docs/tools_notes/transit.md):
  * GTFS feeds listed in FEEDS are merged into one stop graph (platforms collapsed to parent stations,
    walking transfers of up to 400 m between stations of any system).
  * Because one end is always Jamaica, everything is precomputed once into raw/big/transit/network_v*.pkl:
      - sat_midday: an all-stops-to-Jamaica profile (connection-scan, scanned backwards in time), which gives
        for every stop and every departure second the best arrival at Jamaica;
      - return windows: one forward connection scan from Jamaica per sampled departure, with one label per
        number of rides, so the (arrival, transfers) trade-off is exact;
      - Saturday night: a time-mirrored profile from Jamaica (latest departure that still reaches each stop).
    A lookup is then a spatial search for stops within 1.5 km plus a few array look-ups (a few ms).
  * Journeys minimise arrival time + TRANSFER_PENALTY_S per transfer; the minutes reported are the real
    door-to-door minutes of that journey.

Run `python3 scripts/tools/transit.py` for the self-test, `--rebuild` to rebuild the network.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import pickle
import sys
import time
import zipfile
from bisect import bisect_right
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib import ROOT, cached_get  # noqa: E402

# ----------------------------------------------------------------------------------------------- parameters
NET_VERSION = 4
BIG = ROOT / "raw" / "big" / "transit"
NET_PATH = BIG / f"network_v{NET_VERSION}.pkl"
MANIFEST = ROOT / "raw" / "transit" / "feeds_manifest.json"

ANCHOR = {"name": "Jamaica LIRR station", "feed": "lirr", "stop_id": "102", "lat": 40.699608, "lon": -73.808530}

SERVICE_DATES = {"sat": "20261205", "sun": "20261206", "wkd": "20261202"}  # Sat, Sun, Wed (not a holiday week)

WALK_KMH = 4.8
WALK_DETOUR = 1.3            # straight-line metres -> walked metres (street-grid detour), an estimate
ACCESS_MAX_M = 1500.0        # straight-line radius for the walk between the door and a stop
TRANSFER_MAX_M = 400.0       # straight-line radius for walking transfers between stops
TRANSFER_BUFFER_S = 60       # added to the walk time of a station-to-station transfer
TRANSFER_MIN_S = 180         # floor for any station-to-station walking transfer
DEFAULT_CHANGE_S = 120       # change of vehicle at the same stop when the feed gives no minimum
TRANSFER_PENALTY_S = 120     # generalized-cost penalty per transfer (not added to reported minutes)
MAX_RIDES = 6                # return searches: at most 6 vehicles (5 transfers)
INF = 1 << 30

# (feed key, GTFS stop_id) -> minimum seconds for a walking transfer to or from that station.
# These are our estimates for deep or sprawling terminals; GTFS has no pathway data for them.
HUB_MIN_TRANSFER_S = {
    ("lirr", "349"): 600,    # Grand Central Madison (deep cavern under Grand Central)
    ("lirr", "237"): 360,    # Penn Station (LIRR concourse <-> NJ Transit / subway)
    ("mnr", "1"): 300,       # Grand Central Terminal
}

# Station pairs linked on foot although they are a little over TRANSFER_MAX_M apart in the GTFS coordinates.
# Only one: PATH 33rd Street <-> LIRR at Penn Station (about 480 m; NJ Transit's Penn Station stop is already
# within 400 m of PATH, and LIRR shares that building). Without it the router rides a bus for one block.
EXTRA_TRANSFER_PAIRS = [(("path", "781740"), ("lirr", "237")), (("path", "781742"), ("lirr", "237"))]

# key -> (system label, source of the zip). "manifest" = downloaded by scripts/p1_transit_feeds.py.
FEEDS = {
    "lirr": ("LIRR", "manifest"),
    "mnr": ("Metro-North", "manifest"),
    "subway": ("NYC Subway", "manifest"),          # includes Staten Island Railway
    "njt_rail": ("NJ Transit rail", "manifest"),   # includes HBLR, Newark Light Rail, River Line
    "path": ("PATH", "manifest"),
    "septa_rail": ("SEPTA Regional Rail", "manifest"),
    "si_ferry": ("Staten Island Ferry", "manifest"),
    "nyc_ferry": ("NYC Ferry", "manifest"),
    "ny_waterway": ("NY Waterway", "manifest"),
    "bus_q": ("NYC Bus (NYCT Queens feed)", "manifest"),
    "bus_busco": ("MTA Bus Company", "manifest"),
    "njt_bus": ("NJ Transit bus", "manifest"),
    "hudson_link": ("Hudson Link bus", "manifest"),
    "suffolk_bus": ("Suffolk County Transit", "manifest"),
    "beeline": ("Westchester Bee-Line bus", "https://planning.westchestergov.com/images/stories/zip/GTFS.zip"),
    "bus_b": ("NYC Bus (NYCT Brooklyn feed)", "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_b.zip"),
    "bus_bx": ("NYC Bus (NYCT Bronx feed)", "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_bx.zip"),
    "bus_m": ("NYC Bus (NYCT Manhattan feed)", "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_m.zip"),
    "bus_si": ("NYC Bus (NYCT Staten Island feed)", "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_si.zip"),
    "nice": ("NICE bus (Nassau)", "https://www.nicebus.com/NICE/media/nicebus-gtfs/NICE_GTFS.zip"),
    "long_beach": ("City of Long Beach bus", "https://s3.amazonaws.com/datatools-511ny/public/City_of_Long_Beach.zip"),
    "cttransit": ("CTtransit bus", "https://www.cttransit.com/sites/default/files/gtfs/googlect_transit.zip"),
    "norwalk": ("Norwalk Transit District", "https://www.norwalktransit.com/s/GTFS_Data.zip"),
}
FEED_ERRORS = {}   # feeds that could not be downloaded or read in this build (key -> reason)
MODE = {0: "light rail", 1: "subway", 2: "rail", 3: "bus", 4: "ferry", 5: "cable tram", 6: "gondola",
        7: "funicular", 11: "trolleybus", 12: "monorail"}

WINDOWS = {
    "sat_midday": dict(day="sat", direction="to_jamaica", start=10 * 3600, end=13 * 3600, step=900,
                       label="Saturday 10:00-13:00, leaving the door every 15 min, to Jamaica"),
    "sun_evening_return": dict(day="sun", direction="from_jamaica", start=17 * 3600, end=20 * 3600, step=900,
                               label="Sunday 17:00-20:00, leaving Jamaica every 15 min"),
    "weekday_evening_return": dict(day="wkd", direction="from_jamaica", start=18 * 3600, end=19 * 3600, step=900,
                                   label="weekday 18:00-19:00, leaving Jamaica every 15 min"),
}
SAT_MIDDAY_HORIZON = 19 * 3600 + 1800      # connections considered for sat_midday end 19:30
RETURN_HORIZON_S = 6 * 3600                # each return search follows connections for 6 h
NIGHT_START = 21 * 3600
NIGHT_END = 29 * 3600                      # 05:00 Sunday


# ------------------------------------------------------------------------------------------------- helpers
def _hav_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371008.8 * 2 * math.asin(math.sqrt(a))


def _walk_s(m):
    return int(round(m * WALK_DETOUR / (WALK_KMH / 3.6)))


def _hhmm(sec):
    sec = int(sec)
    d, rem = divmod(sec, 86400)
    s = f"{rem // 3600:02d}:{rem % 3600 // 60:02d}"
    return s + (" (+1 day)" if d >= 1 else "")


def _tsec(s):
    s = s.strip()
    if not s:
        return -1
    h, m, x = s.split(":")
    return int(h) * 3600 + int(m) * 60 + int(x)


def _rows(z, name):
    mm = {n.rsplit("/", 1)[-1]: n for n in z.namelist() if n.endswith(".txt")}
    if name not in mm:
        return []
    with z.open(mm[name]) as f:
        return [{(k or "").strip(): (v or "").strip() for k, v in r.items()}
                for r in csv.DictReader(io.TextIOWrapper(f, "utf-8-sig"))]


def _feed_files():
    """key -> dict(system, url, retrieved_at, path). Downloads through lib.cached_get when missing."""
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    need = [k for k, (_, src) in FEEDS.items() if src == "manifest"
            and not (k in man and man[k].get("raw_path") and (ROOT / man[k]["raw_path"]).exists())]
    if need:
        import p1_transit_feeds  # noqa: PLC0415  (re-download; only when a zip is missing)
        man = p1_transit_feeds.fetch_all()
    out = {}
    for k, (label, src) in FEEDS.items():
        if src == "manifest":
            e = man.get(k) or {}
            if not e.get("raw_path"):
                FEED_ERRORS[k] = "not in raw/transit/feeds_manifest.json (download failed earlier)"
                continue
            out[k] = dict(system=label, url=e["url"], retrieved_at=e["retrieved_at"], path=ROOT / e["raw_path"])
        else:
            try:
                content, meta = cached_get(src, "big/gtfs_transit", ext="zip", timeout=300, retries=2)
            except RuntimeError as e:
                FEED_ERRORS[k] = f"download failed: {str(e)[:120]}"
                continue
            if meta.get("status") != 200 or content[:2] != b"PK":
                FEED_ERRORS[k] = f"HTTP {meta.get('status')} or not a zip at {src}"
                continue
            out[k] = dict(system=label, url=src, retrieved_at=meta["retrieved_at"], path=ROOT / meta["path"])
    return out


# ------------------------------------------------------------------------------------------ GTFS -> memory
def _active_services(cal, cal_dates, date):
    d = dt.date(int(date[:4]), int(date[4:6]), int(date[6:]))
    wd = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][d.weekday()]
    s = {r["service_id"] for r in cal if r.get(wd) == "1" and r["start_date"] <= date <= r["end_date"]}
    for r in cal_dates:
        if r["date"] == date:
            (s.add if r["exception_type"] == "1" else s.discard)(r["service_id"])
    return s


def _load_feed(key, info):
    """Read one GTFS zip. Returns a dict with stops, routes, trips for the three service days, fares."""
    z = zipfile.ZipFile(info["path"])
    stops_raw = {r["stop_id"]: r for r in _rows(z, "stops.txt")}
    node_of, node_info = {}, {}
    for sid, r in stops_raw.items():
        par = r.get("parent_station") or ""
        nid = par if par and par in stops_raw else sid
        node_of[sid] = nid
    for nid in set(node_of.values()):
        r = stops_raw[nid]
        try:
            node_info[nid] = (r["stop_name"].strip().strip('"'), float(r["stop_lat"]), float(r["stop_lon"]))
        except ValueError:
            pass
    routes = {r["route_id"]: (r.get("route_short_name", ""), r.get("route_long_name", ""),
                              int(r.get("route_type") or 3)) for r in _rows(z, "routes.txt")}
    cal, cal_dates = _rows(z, "calendar.txt"), _rows(z, "calendar_dates.txt")
    trips_raw = _rows(z, "trips.txt")
    by_service = {}
    for r in trips_raw:
        by_service.setdefault(r["service_id"], []).append(r["trip_id"])
    trip_meta = {r["trip_id"]: (r["route_id"], r.get("trip_headsign", "")) for r in trips_raw}

    days, subs = {}, {}
    for day, date in SERVICE_DATES.items():
        used = date
        act = _active_services(cal, cal_dates, date)
        if not any(by_service.get(s) for s in act):
            # Calendar does not cover the date: fall back to the latest earlier date of the same weekday.
            d0 = dt.date(int(date[:4]), int(date[4:6]), int(date[6:]))
            for k in range(1, 160):
                cand = (d0 - dt.timedelta(days=7 * k)).strftime("%Y%m%d")
                act = _active_services(cal, cal_dates, cand)
                if any(by_service.get(s) for s in act):
                    used = cand
                    break
            else:
                act = set()
            ends = [r["end_date"] for r in cal] + [r["date"] for r in cal_dates if r["exception_type"] == "1"]
            subs[day] = dict(requested=date, used=used if act else None,
                             reason=f"feed calendar ends {max(ends) if ends else 'unknown'}, before the service "
                                    f"date; used the latest earlier date of the same weekday with service")
        days[day] = dict(date=used, trips={t for s in act for t in by_service.get(s, [])})
    wanted = set().union(*(d["trips"] for d in days.values()))

    st = {}
    mm = {n.rsplit("/", 1)[-1]: n for n in z.namelist() if n.endswith(".txt")}
    with z.open(mm["stop_times.txt"]) as f:
        rd = csv.reader(io.TextIOWrapper(f, "utf-8-sig"))
        hdr = [h.strip() for h in next(rd)]
        it, ia, idp, isd, isq = (hdr.index(c) for c in
                                 ("trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"))
        ipu = hdr.index("pickup_type") if "pickup_type" in hdr else None
        ido = hdr.index("drop_off_type") if "drop_off_type" in hdr else None
        for row in rd:
            t = row[it].strip()
            if t not in wanted:
                continue
            a, d = _tsec(row[ia]), _tsec(row[idp])
            if a < 0 and d < 0:
                continue
            a, d = (a if a >= 0 else d), (d if d >= 0 else a)
            nid = node_of.get(row[isd].strip())
            if nid is None or nid not in node_info:
                continue
            pu = 0 if ipu is None else (1 if row[ipu].strip() == "1" else 0)
            do = 0 if ido is None else (1 if row[ido].strip() == "1" else 0)
            st.setdefault(t, []).append((int(row[isq]), nid, a, d, pu, do))
    for v in st.values():
        v.sort()

    # frequencies.txt: expand headway-based trips into explicit runs (none of the current feeds use it)
    freq = _rows(z, "frequencies.txt")
    if freq:
        byt = {}
        for r in freq:
            byt.setdefault(r["trip_id"], []).append(r)
        for t, frs in byt.items():
            if t not in st:
                continue
            base = st.pop(t)
            t0 = base[0][3]
            n = 0
            for fr in frs:
                x, end, hw = _tsec(fr["start_time"]), _tsec(fr["end_time"]), int(fr["headway_secs"])
                while x < end:
                    nt = f"{t}#f{n}"
                    n += 1
                    st[nt] = [(q, s, a - t0 + x, d - t0 + x, pu, do) for q, s, a, d, pu, do in base]
                    trip_meta[nt] = trip_meta[t]
                    for dd in days.values():
                        if t in dd["trips"]:
                            dd["trips"].add(nt)
                    x += hw

    change = {}   # node -> min seconds to change vehicles there; pairs -> walking transfer
    pair = {}
    for r in _rows(z, "transfers.txt"):
        if r.get("transfer_type") != "2" or r.get("from_trip_id") or r.get("to_trip_id") \
                or r.get("from_route_id") or r.get("to_route_id"):
            continue
        a, b = node_of.get(r["from_stop_id"]), node_of.get(r["to_stop_id"])
        if a is None or b is None or not r.get("min_transfer_time"):
            continue
        sec = int(float(r["min_transfer_time"]))
        if a == b:
            change[a] = max(change.get(a, 0), sec)
        else:
            pair[(a, b)] = max(pair.get((a, b), 0), sec)

    fares = dict(v1=_rows(z, "fare_attributes.txt"), v1_rules=_rows(z, "fare_rules.txt"),
                 products=_rows(z, "fare_products.txt"), leg_rules=_rows(z, "fare_leg_rules.txt"),
                 stop_areas=_rows(z, "stop_areas.txt"))
    return dict(key=key, nodes=node_info, routes=routes, trip_meta=trip_meta, st=st, days=days, subs=subs,
                change=change, pair=pair, fares=fares)


# --------------------------------------------------------------------------------------------- algorithms
def _insert(keys, vals, ns, cins, couts, nk, val, n, cin, cout):
    """Insert (key=-departure, val=cost) into a Pareto list (keys ascending, vals strictly descending)."""
    pos = bisect_right(keys, nk)
    if pos and vals[pos - 1] <= val:
        return False
    L = len(keys)
    if pos == L and not (pos and keys[pos - 1] == nk):
        keys.append(nk); vals.append(val); ns.append(n); cins.append(cin); couts.append(cout)
        return True
    j = pos
    while j < L and vals[j] >= val:
        j += 1
    s = pos - 1 if pos and keys[pos - 1] == nk else pos
    keys[s:j] = [nk]; vals[s:j] = [val]; ns[s:j] = [n]; cins[s:j] = [cin]; couts[s:j] = [cout]
    return True


def _profile(n_nodes, n_trips, C, order, chg, foot, target_walk, penalty):
    """All-to-one profile connection scan.

    C = (cu, cv, cd, ca, ct, cb, cal) python lists; `order` lists connection indexes by decreasing departure.
    Returns D, W: per node five parallel lists (key=-dep, cost, transfers, first connection, exit connection).
    D = journeys that board at the node; W = journeys that first walk to a neighbouring node.
    """
    cu, cv, cd, ca, ct, cb, cal = C
    D = [([], [], [], [], []) for _ in range(n_nodes)]
    W = [([], [], [], [], []) for _ in range(n_nodes)]
    Tc = [INF] * n_trips
    Tn = [0] * n_trips
    Tx = [-1] * n_trips
    tget = target_walk.get
    for ci in order:
        tr = ct[ci]
        best, bn, bx = Tc[tr], Tn[tr], Tx[tr]
        if cal[ci]:
            v, a = cv[ci], ca[ci]
            tw = tget(v)
            if tw is not None and a + tw < best:
                best, bn, bx = a + tw, 0, ci
            dk = D[v]
            if dk[0]:
                i = bisect_right(dk[0], -(a + chg[v])) - 1
                if i >= 0 and dk[1][i] + penalty < best:
                    best, bn, bx = dk[1][i] + penalty, dk[2][i] + 1, ci
            wk = W[v]
            if wk[0]:
                i = bisect_right(wk[0], -a) - 1
                if i >= 0 and wk[1][i] + penalty < best:
                    best, bn, bx = wk[1][i] + penalty, wk[2][i] + 1, ci
        if best >= INF:
            continue
        Tc[tr], Tn[tr], Tx[tr] = best, bn, bx
        if cb[ci]:
            u, d = cu[ci], cd[ci]
            if _insert(*D[u], -d, best, bn, ci, bx):
                for w, dur in foot[u]:
                    _insert(*W[w], dur - d, best, bn, ci, bx)
    return D, W


def _pack(P):
    off = np.zeros(len(P) + 1, dtype=np.int64)
    for i, p in enumerate(P):
        off[i + 1] = off[i] + len(p[0])
    cat = lambda j, t: np.fromiter((x for p in P for x in p[j]), dtype=t, count=int(off[-1]))  # noqa: E731
    return dict(off=off, key=cat(0, np.int32), val=cat(1, np.int32), n=cat(2, np.int8),
                cin=cat(3, np.int32), cout=cat(4, np.int32))


def _forward(n_nodes, n_trips, C, lo, hi, chg, foot, src_ready, K):
    """Forward connection scan from Jamaica with one label per number of rides (1..K).

    C lists are sorted by departure; lo..hi is the index range to scan. src_ready = {node: time ready to board}.
    Returns A[k][node] arrival by the k-th ride, Ain/Aout (boarding and alighting connection) and
    Rsrc[k][node] (node where the k-th ride was left before walking here; -1 = straight from Jamaica).
    """
    cu, cv, cd, ca, ct, cb, cal = C
    R = [[INF] * n_nodes for _ in range(K + 1)]
    Rsrc = [[-1] * n_nodes for _ in range(K + 1)]
    Rmin = [INF] * n_nodes
    A = [[INF] * n_nodes for _ in range(K + 1)]
    Ain = [[-1] * n_nodes for _ in range(K + 1)]
    Aout = [[-1] * n_nodes for _ in range(K + 1)]
    Tmask = [0] * n_trips
    Tin = [[-1] * n_trips for _ in range(K + 1)]
    for s, t in src_ready.items():
        R[0][s] = t
        Rmin[s] = t
    ks = range(1, K + 1)
    for ci in range(lo, hi):
        tr = ct[ci]
        tm = Tmask[tr]
        u, d = cu[ci], cd[ci]
        ok = Rmin[u] <= d
        if not tm and not ok:
            continue
        if ok and cb[ci]:
            for k in ks:
                if not (tm >> k) & 1 and R[k - 1][u] <= d:
                    tm |= 1 << k
                    Tin[k][tr] = ci
            Tmask[tr] = tm
        if tm and cal[ci]:
            v, a = cv[ci], ca[ci]
            for k in ks:
                if (tm >> k) & 1 and a < A[k][v]:
                    A[k][v] = a; Ain[k][v] = Tin[k][tr]; Aout[k][v] = ci
                    if k < K:
                        x = a + chg[v]
                        if x < R[k][v]:
                            R[k][v] = x; Rsrc[k][v] = v
                            if x < Rmin[v]:
                                Rmin[v] = x
                        for w, dur in foot[v]:
                            y = a + dur
                            if y < R[k][w]:
                                R[k][w] = y; Rsrc[k][w] = v
                                if y < Rmin[w]:
                                    Rmin[w] = y
    return A, Ain, Aout, Rsrc


# ------------------------------------------------------------------------------------------------- build
_G = {}


def _run_job(job):
    """Worker entry (fork): job = (kind, timetable name, extra)."""
    kind, name, extra = job
    g = _G
    tt = g["tts"][name]
    n_nodes, chg, foot = g["n_nodes"], g["chg"], g["foot"]
    C = tt["C"]
    if kind == "profile":
        mirrored, penalty = extra
        if mirrored:
            cu, cv, cd, ca, ct, cb, cal = C
            Cm = (cv, cu, [-x for x in ca], [-x for x in cd], ct, cal, cb)
            order = sorted(range(len(cu)), key=lambda i: (ca[i], tt["seq"][i]))
            D, W = _profile(n_nodes, tt["n_trips"], Cm, order, chg, foot, g["target_walk"], penalty)
        else:
            order = sorted(range(len(C[0])), key=lambda i: (-C[2][i], -tt["seq"][i]))
            D, W = _profile(n_nodes, tt["n_trips"], C, order, chg, foot, g["target_walk"], penalty)
        return job, (_pack(D), _pack(W))
    dep = extra
    lo = int(np.searchsorted(tt["cd_np"], dep, "left"))
    hi = int(np.searchsorted(tt["cd_np"], dep + RETURN_HORIZON_S, "right"))
    src = {g["jam"]: dep}
    for w, dur in g["target_walk"].items():
        if w != g["jam"]:
            src[w] = dep + dur
    A, Ain, Aout, Rsrc = _forward(n_nodes, tt["n_trips"], C, lo, hi, chg, foot, src, MAX_RIDES)
    arr = lambda X: np.array(X, dtype=np.int32)  # noqa: E731
    return job, (arr(A), arr(Ain), arr(Aout), arr(Rsrc))


def build(verbose=True):
    t0 = time.time()
    log = (lambda *a: print(f"[transit build {time.time() - t0:6.1f}s]", *a, flush=True)) if verbose else (lambda *a: None)
    files = _feed_files()
    feeds = {}
    for k, info in files.items():
        try:
            feeds[k] = _load_feed(k, info)
        except Exception as e:  # noqa: BLE001  (a broken optional feed must not stop the build)
            FEED_ERRORS[k] = f"unreadable GTFS: {type(e).__name__}: {str(e)[:120]}"
            log("SKIPPED", k, FEED_ERRORS[k])
            continue
        if not any(v["trips"] for v in feeds[k]["days"].values()):
            FEED_ERRORS[k] = "no trips on any service date, even after calendar fallback"
            del feeds[k]
            continue
        log("loaded", k, {d: len(v["trips"]) for d, v in feeds[k]["days"].items()}, feeds[k]["subs"] or "")

    # ---- global nodes
    nodes, node_idx = [], {}

    def nid(feed, n):
        key = (feed, n)
        i = node_idx.get(key)
        if i is None:
            nm, la, lo = feeds[feed]["nodes"][n]
            i = node_idx[key] = len(nodes)
            nodes.append([feed, n, nm, la, lo, set()])
        return i

    routes, route_idx = [], {}

    def rid(feed, r):
        key = (feed, r)
        i = route_idx.get(key)
        if i is None:
            sh, lg, ty = feeds[feed]["routes"].get(r, ("", "", 3))
            i = route_idx[key] = len(routes)
            routes.append((feed, r, sh, lg, ty))
        return i

    # ---- timetables
    specs = {
        "sat_midday": [("sat", 0, WINDOWS["sat_midday"]["start"], SAT_MIDDAY_HORIZON)],
        "sun_evening_return": [("sun", 0, WINDOWS["sun_evening_return"]["start"],
                                WINDOWS["sun_evening_return"]["end"] + RETURN_HORIZON_S)],
        "weekday_evening_return": [("wkd", 0, WINDOWS["weekday_evening_return"]["start"],
                                    WINDOWS["weekday_evening_return"]["end"] + RETURN_HORIZON_S)],
        "sat_night": [("sat", 0, NIGHT_START, NIGHT_END), ("sun", 86400, NIGHT_START, NIGHT_END)],
    }
    tts = {}
    for name, parts in specs.items():
        rows, trips = [], []
        for day, shift, lo, hi in parts:
            for fk, fd in feeds.items():
                st, tm = fd["st"], fd["trip_meta"]
                for t in fd["days"][day]["trips"]:
                    seq = st.get(t)
                    if not seq or len(seq) < 2:
                        continue
                    if seq[-1][2] + shift < lo or seq[0][3] + shift > hi:
                        continue
                    ti = -1
                    for (q0, n0, _, d0, pu0, _), (q1, n1, a1, _, _, do1) in zip(seq, seq[1:]):
                        d0 += shift; a1 += shift
                        if d0 < lo or a1 > hi or n0 == n1 or a1 < d0:
                            continue
                        if ti < 0:
                            ti = len(trips)
                            r, hs = tm[t]
                            trips.append((rid(fk, r), hs))
                        u, v = nid(fk, n0), nid(fk, n1)
                        ty = routes[trips[ti][0]][4]
                        nodes[u][5].add(ty); nodes[v][5].add(ty)
                        rows.append((d0, q0, u, v, a1, ti, 0 if pu0 else 1, 0 if do1 else 1))
        rows.sort()
        tts[name] = dict(C=tuple([r[j] for r in rows] for j in (2, 3, 0, 4, 5, 6, 7)), seq=[r[1] for r in rows],
                         n_trips=len(trips), trips=trips)
        tts[name]["cd_np"] = np.array(tts[name]["C"][2], dtype=np.int64)
        log(name, "connections", len(rows), "trips", len(trips))
    n_nodes = len(nodes)

    # ---- change times and walking transfers
    chg = [DEFAULT_CHANGE_S] * n_nodes
    foot_d = [dict() for _ in range(n_nodes)]
    for fk, fd in feeds.items():
        for n, sec in fd["change"].items():
            if (fk, n) in node_idx:
                chg[node_idx[(fk, n)]] = max(60, sec)
    cell = {}
    for i, nd in enumerate(nodes):
        cell.setdefault((int(nd[3] / 0.005), int(nd[4] / 0.005)), []).append(i)
    hub = {node_idx[k]: v for k, v in HUB_MIN_TRANSFER_S.items() if k in node_idx}
    for i, nd in enumerate(nodes):
        cy, cx = int(nd[3] / 0.005), int(nd[4] / 0.005)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for j in cell.get((cy + dy, cx + dx), ()):
                    if j <= i:
                        continue
                    m = _hav_m(nd[3], nd[4], nodes[j][3], nodes[j][4])
                    if m > TRANSFER_MAX_M:
                        continue
                    dur = max(TRANSFER_MIN_S, _walk_s(m) + TRANSFER_BUFFER_S, hub.get(i, 0), hub.get(j, 0))
                    foot_d[i][j] = dur; foot_d[j][i] = dur
    for ka, kb in EXTRA_TRANSFER_PAIRS:
        if ka in node_idx and kb in node_idx:
            i, j = node_idx[ka], node_idx[kb]
            m = _hav_m(nodes[i][3], nodes[i][4], nodes[j][3], nodes[j][4])
            dur = max(TRANSFER_MIN_S, _walk_s(m) + TRANSFER_BUFFER_S, hub.get(i, 0), hub.get(j, 0))
            foot_d[i][j] = dur; foot_d[j][i] = dur
    for fk, fd in feeds.items():       # feed-stated station-to-station transfers override the distance rule
        for (a, b), sec in fd["pair"].items():
            if (fk, a) in node_idx and (fk, b) in node_idx:
                foot_d[node_idx[(fk, b)]][node_idx[(fk, a)]] = max(120, sec)
    foot = [sorted(d.items()) for d in foot_d]   # foot[u] = [(w, seconds)]: walk between w and u
    log("nodes", n_nodes, "walking-transfer pairs", sum(len(f) for f in foot) // 2)

    jam = node_idx[(ANCHOR["feed"], ANCHOR["stop_id"])]
    target_walk = {jam: 0}
    for w, dur in foot[jam]:
        target_walk[w] = dur

    # ---- searches (forked workers share the big lists)
    _G.update(tts=tts, n_nodes=n_nodes, chg=chg, foot=foot, jam=jam, target_walk=target_walk)
    jobs = [("profile", "sat_midday", (False, TRANSFER_PENALTY_S)), ("profile", "sat_night", (True, 0))]
    for name in ("sun_evening_return", "weekday_evening_return"):
        w = WINDOWS[name]
        jobs += [("forward", name, dep) for dep in range(w["start"], w["end"] + 1, w["step"])]
    import multiprocessing as mp
    results = {}
    with mp.get_context("fork").Pool(min(4, mp.cpu_count())) as pool:
        for job, res in pool.imap_unordered(_run_job, jobs):
            results[job] = res
            log("done", job[0], job[1], job[2] if job[0] == "forward" else "")
    _G.clear()

    net = dict(version=NET_VERSION, built_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               params=dict(WALK_KMH=WALK_KMH, WALK_DETOUR=WALK_DETOUR, ACCESS_MAX_M=ACCESS_MAX_M,
                           TRANSFER_MAX_M=TRANSFER_MAX_M, TRANSFER_PENALTY_S=TRANSFER_PENALTY_S,
                           MAX_RIDES=MAX_RIDES, SERVICE_DATES=SERVICE_DATES),
               feeds={k: dict(system=files[k]["system"], url=files[k]["url"], retrieved_at=files[k]["retrieved_at"],
                              dates={d: v["date"] for d, v in feeds[k]["days"].items()}, subs=feeds[k]["subs"])
                      for k in feeds},
               node_feed=[n[0] for n in nodes], node_id=[n[1] for n in nodes], node_name=[n[2] for n in nodes],
               node_lat=np.array([n[3] for n in nodes]), node_lon=np.array([n[4] for n in nodes]),
               node_modes=[sorted(n[5]) for n in nodes],
               feed_errors=dict(FEED_ERRORS), routes=routes, chg=np.array(chg, dtype=np.int32), foot=foot, jam=jam, target_walk=target_walk,
               fares={k: feeds[k]["fares"] for k in feeds if any(feeds[k]["fares"].values())}, tt={})
    for name, tt in tts.items():
        cu, cv, cd, ca, ct, cb, cal = tt["C"]
        e = dict(cb=np.array(cb, dtype=np.int8), cal=np.array(cal, dtype=np.int8),
                 cu=np.array(cu, dtype=np.int32), cv=np.array(cv, dtype=np.int32), cd=np.array(cd, dtype=np.int32),
                 ca=np.array(ca, dtype=np.int32), ct=np.array(ct, dtype=np.int32),
                 trip_route=np.array([t[0] for t in tt["trips"]], dtype=np.int32),
                 trip_head=[t[1] for t in tt["trips"]])
        if name == "sat_midday":
            e["D"], e["W"] = results[("profile", name, (False, TRANSFER_PENALTY_S))]
        elif name == "sat_night":
            e["D"], e["W"] = results[("profile", name, (True, 0))]
        else:
            w = WINDOWS[name]
            deps = list(range(w["start"], w["end"] + 1, w["step"]))
            rs = [results[("forward", name, d)] for d in deps]
            e["deps"] = deps
            for j, nm in enumerate(("A", "Ain", "Aout", "Rsrc")):
                e[nm] = np.stack([r[j] for r in rs])
        net["tt"][name] = e
    BIG.mkdir(parents=True, exist_ok=True)
    tmp = NET_PATH.with_suffix(".tmp")
    with open(tmp, "wb") as f:
        pickle.dump(net, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(NET_PATH)
    log("wrote", NET_PATH, f"{NET_PATH.stat().st_size / 1e6:.0f} MB")
    _write_feed_table(net)
    return net


def _write_feed_table(net):
    """data/reference/transit_feeds.csv: one row per feed with what the router used."""
    out = ROOT / "data" / "reference" / "transit_feeds.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    counts = {}
    for fk in net["node_feed"]:
        counts[fk] = counts.get(fk, 0) + 1
    with open(out, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["feed_key", "system", "status", "source_url", "retrieved_at", "saturday_date_used",
                     "sunday_date_used", "weekday_date_used", "calendar_substituted", "stops_in_network", "notes"])
        for k, (label, src) in FEEDS.items():
            if k in net["feeds"]:
                e = net["feeds"][k]
                sub = "; ".join(sorted({v["reason"] for v in e["subs"].values()}))
                wr.writerow([k, label, "used", e["url"], e["retrieved_at"], e["dates"]["sat"], e["dates"]["sun"],
                             e["dates"]["wkd"], "yes" if e["subs"] else "no", counts.get(k, 0), sub])
            else:
                wr.writerow([k, label, "not_used", src if src != "manifest" else "", "", "", "", "", "", 0,
                             net["feed_errors"].get(k, "")])


# ------------------------------------------------------------------------------------------------- lookup
_NET = None


def _net():
    global _NET
    if _NET is None:
        if not NET_PATH.exists():
            build()
        with open(NET_PATH, "rb") as f:
            _NET = pickle.load(f)
        n = _NET
        grid = {}
        for i, (la, lo) in enumerate(zip(n["node_lat"].tolist(), n["node_lon"].tolist())):
            grid.setdefault((int(la / 0.01), int(lo / 0.01)), []).append(i)
        n["grid"] = grid
        n["lat_l"], n["lon_l"] = n["node_lat"].tolist(), n["node_lon"].tolist()
        n["rail_nodes"] = [i for i, m in enumerate(n["node_modes"]) if any(x != 3 for x in m)]
        # nodes usable in each timetable
        for name, tt in n["tt"].items():
            if "D" in tt:
                off = tt["D"]["off"]
                tt["usable"] = (off[1:] > off[:-1])
            else:
                tt["usable"] = (tt["A"] < INF).any(axis=(0, 1))
    return _NET


def _near(n, lat, lon, radius_m):
    """[(metres, node)] within radius, nearest first."""
    out = []
    dlat = radius_m / 111000.0
    dlon = radius_m / (111000.0 * math.cos(math.radians(lat)))
    la, lo, grid = n["lat_l"], n["lon_l"], n["grid"]
    for cy in range(int((lat - dlat) / 0.01) - 1, int((lat + dlat) / 0.01) + 2):
        for cx in range(int((lon - dlon) / 0.01) - 1, int((lon + dlon) / 0.01) + 2):
            for i in grid.get((cy, cx), ()):
                m = _hav_m(lat, lon, la[i], lo[i])
                if m <= radius_m:
                    out.append((m, i))
    out.sort()
    return out


def _nearest(n, lat, lon, idxs=None, usable=None):
    best = (float("inf"), -1)
    la, lo = n["lat_l"], n["lon_l"]
    c = math.cos(math.radians(lat))
    rng = idxs if idxs is not None else range(len(la))
    for i in rng:
        if usable is not None and not usable[i]:
            continue
        d = (la[i] - lat) ** 2 + ((lo[i] - lon) * c) ** 2
        if d < best[0]:
            best = (d, i)
    if best[1] < 0:
        return None
    i = best[1]
    return dict(name=n["node_name"][i], system=n["feeds"][n["node_feed"][i]]["system"],
                stop_id=n["node_id"][i], lat=la[i], lon=lo[i],
                modes=[MODE.get(m, "bus") for m in n["node_modes"][i]],
                distance_km=round(_hav_m(lat, lon, la[i], lo[i]) / 1000, 2))


def _ride(n, tt, c_board, c_alight, mirrored):
    """Describe one vehicle ride between two connection indexes (real-time orientation)."""
    tr = int(tt["ct"][c_board])
    feed, r_id, sh, lg, ty = n["routes"][int(tt["trip_route"][tr])]
    u, v = int(tt["cu"][c_board]), int(tt["cv"][c_alight])
    return dict(kind="ride", feed=feed, system=n["feeds"][feed]["system"], mode=MODE.get(ty, "bus"),
                line=(sh or lg or r_id), line_long=lg, route_id=r_id, headsign=tt["trip_head"][tr],
                from_node=u, to_node=v, dep=int(tt["cd"][c_board]), arr=int(tt["ca"][c_alight]))


def _eval(P, s, key):
    """Index (absolute) of the profile entry of node s with the largest key <= `key`, or -1."""
    a, b = int(P["off"][s]), int(P["off"][s + 1])
    if a == b:
        return -1
    i = int(np.searchsorted(P["key"][a:b], key, "right")) - 1
    return a + i if i >= 0 else -1


def _profile_legs(n, tt, s, i, mirrored, penalty):
    """Follow a profile entry to Jamaica. Returns rides in profile order (reverse of real time if mirrored)
    and the final walk seconds at Jamaica. Profile space: mirrored times are negated and u/v swapped."""
    D, W = tt["D"], tt["W"]
    cu, cv, cd, ca = tt["cu"], tt["cv"], tt["cd"], tt["ca"]
    chg, tw = n["chg"], n["target_walk"]
    rides, P = [], D
    for _ in range(40):
        cin, cout, cost = int(P["cin"][i]), int(P["cout"][i]), int(P["val"][i])
        if mirrored:
            rides.append(_ride(n, tt, cout, cin, True))
            v, a = int(cu[cout]), -int(cd[cout])
        else:
            rides.append(_ride(n, tt, cin, cout, False))
            v, a = int(cv[cout]), int(ca[cout])
        if v in tw and a + tw[v] == cost:
            return rides, tw[v]
        j = _eval(D, v, -(a + int(chg[v])))
        if j >= 0 and int(D["val"][j]) + penalty == cost:
            P, i = D, j
            continue
        j = _eval(W, v, -a)
        if j >= 0 and int(W["val"][j]) + penalty == cost:
            P, i = W, j
            continue
        raise RuntimeError("profile journey reconstruction failed")
    raise RuntimeError("profile journey too long")


def _forward_legs(n, tt, run, s, k):
    A, Ain, Aout, Rsrc = tt["A"][run], tt["Ain"][run], tt["Aout"][run], tt["Rsrc"][run]
    rides = []
    while k >= 1:
        cin, cout = int(Ain[k][s]), int(Aout[k][s])
        rides.append(_ride(n, tt, cin, cout, False))
        u = int(tt["cu"][cin])
        k -= 1
        s = int(Rsrc[k][u]) if k >= 1 else u
    rides.reverse()
    return rides


def _fare(n, ride, day):
    """One-way adult fare for one ride from the feed's own fare tables, else not_found."""
    feed = ride["feed"]
    f = n["fares"].get(feed)
    src = n["feeds"][feed]
    base = dict(source_url=src["url"], retrieved_at=src["retrieved_at"])
    if not f:
        return dict(value=None, value_type="not_found", reason="feed has no fare tables (fare_attributes / "
                    "fare_products); fare not looked up elsewhere by this tool", **base)
    if f["leg_rules"]:      # GTFS Fares v2 (SEPTA)
        areas = {}
        for r in f["stop_areas"]:
            areas.setdefault(r["stop_id"], set()).add(r["area_id"])
        fa = areas.get(n["node_id"][ride["from_node"]], set())
        ta = areas.get(n["node_id"][ride["to_node"]], set())
        tf = "weekday" if day == "wkd" else "weekend"
        cands = [r for r in f["leg_rules"] if r["from_area_id"] in fa and r["to_area_id"] in ta
                 and r.get("from_timeframe_group_id", "") in ("", tf)]
        if not cands:
            return dict(value=None, value_type="not_found",
                        reason="no fare_leg_rule matches this station pair (e.g. a trip through Center City)", **base)
        rule = max(cands, key=lambda r: int(r.get("rule_priority") or 0))
        prods = [p for p in f["products"] if p["fare_product_id"] == rule["fare_product_id"]]
        pick = [p for p in prods if p.get("fare_media_id") == "contactless"] or prods
        if not pick:
            return dict(value=None, value_type="not_found", reason="fare product missing", **base)
        p = pick[0]
        return dict(value=float(p["amount"]), currency=p.get("currency", "USD"), value_type="found",
                    method=f"GTFS Fares v2: fare_leg_rules {rule['from_area_id']}->{rule['to_area_id']} "
                           f"({tf}), product {p['fare_product_id']}, media {p.get('fare_media_id')}; highest "
                           f"rule_priority among {len(cands)} matching rule(s)", **base)
    if f["v1"]:
        rules = f["v1_rules"]
        ids = {r["fare_id"] for r in rules if r.get("route_id") in ("", ride["route_id"])} if rules \
            else {r["fare_id"] for r in f["v1"]}
        c = [r for r in f["v1"] if r["fare_id"] in ids]
        if len(c) > 1:
            c2 = [r for r in c if any(w in r["fare_id"].upper() for w in ("FULL", "ADULT", "REGULAR"))]
            if len(c2) == 1:
                c = c2
        if len(c) == 1:
            return dict(value=float(c[0]["price"]), currency=c[0].get("currency_type", "USD"), value_type="found",
                        method=f"GTFS fare_attributes fare_id {c[0]['fare_id']} (flat fare, no peak pricing in feed)",
                        **base)
        return dict(value=None, value_type="not_found",
                    reason=f"{len(c)} fares in fare_attributes apply and the feed does not say which is the adult "
                           f"single fare", **base)
    return dict(value=None, value_type="not_found", reason="no usable fare table", **base)


def _fmt_legs(n, rides, first_walk, last_walk, door_first, day):
    """Build the public leg list from rides (real-time order).

    first_walk / last_walk = (seconds, metres or None, from name, to name) or None.
    """
    legs = []
    names = n["node_name"]
    if first_walk and first_walk[0] > 0:
        legs.append(dict(mode="walk", **{"from": first_walk[2], "to": first_walk[3]},
                         minutes=round(first_walk[0] / 60, 1),
                         straight_line_m=None if first_walk[1] is None else int(round(first_walk[1]))))
    prev = None
    for r in rides:
        if prev is not None and prev["to_node"] != r["from_node"]:
            m = _hav_m(n["lat_l"][prev["to_node"]], n["lon_l"][prev["to_node"]],
                       n["lat_l"][r["from_node"]], n["lon_l"][r["from_node"]])
            legs.append(dict(mode="walk", **{"from": names[prev["to_node"]], "to": names[r["from_node"]]},
                             minutes=round(dict(n["foot"][prev["to_node"]])[r["from_node"]] / 60, 1),
                             straight_line_m=int(round(m)), transfer=True))
        legs.append(dict(mode=r["mode"], system=r["system"], line=r["line"], line_name=r["line_long"] or r["line"],
                         headsign=r["headsign"],
                         **{"from": names[r["from_node"]], "to": names[r["to_node"]]},
                         depart=_hhmm(r["dep"]), arrive=_hhmm(r["arr"]),
                         minutes=round((r["arr"] - r["dep"]) / 60, 1),
                         fare_one_way=_fare(n, r, day)))
        prev = r
    if last_walk and last_walk[0] > 0:
        legs.append(dict(mode="walk", **{"from": last_walk[2], "to": last_walk[3]},
                         minutes=round(last_walk[0] / 60, 1),
                         straight_line_m=None if last_walk[1] is None else int(round(last_walk[1]))))
    return legs


def _label(system, line):
    return system if len(line) >= 4 and line.lower() in system.lower() else f"{system} {line}"


def _summary(legs):
    parts = []
    for g in legs:
        if g["mode"] == "walk":
            parts.append(f"walk {g['minutes']:.0f} min to {g['to']}")
        else:
            parts.append(f"{_label(g['system'], g['line'])} {g['from']} {g['depart']} -> {g['to']} {g['arrive']}")
    return "; ".join(parts)


def _prov(n, feeds_used, day_keys, extra_method=""):
    """Provenance block for values derived from the given feeds."""
    feeds_used = sorted(set(feeds_used))
    subs = []
    for fk in feeds_used:
        for d in day_keys:
            s = n["feeds"][fk]["subs"].get(d)
            if s:
                subs.append(f"{n['feeds'][fk]['system']}: {s['reason']} (requested {s['requested']}, used {s['used']})")
    urls = [n["feeds"][fk]["url"] for fk in feeds_used]
    rts = [n["feeds"][fk]["retrieved_at"] for fk in feeds_used]
    method = ("Scheduled GTFS timetables for " + ", ".join(sorted({SERVICE_DATES[d] for d in day_keys})) +
              f"; walking at {WALK_KMH} km/h over straight-line distance x {WALK_DETOUR}." +
              (" " + extra_method if extra_method else
               f" Journeys minimise arrival time + {TRANSFER_PENALTY_S // 60} min per transfer."))
    p = dict(value_type="estimate" if subs else "found", source_url="; ".join(urls) if urls else None,
             retrieved_at=min(rts) if rts else n["built_at"], method=method)
    if subs:
        p["estimate_reason"] = "; ".join(subs)
    return p


def _last_departure(n, lat, lon, near):
    tt = n["tt"]["sat_night"]
    D = tt["D"]
    jm = _hav_m(lat, lon, ANCHOR["lat"], ANCHOR["lon"])
    best = None
    for m, s in near:
        a, b = int(D["off"][s]), int(D["off"][s + 1])
        if a == b:
            continue
        w = _walk_s(m)
        keys = D["key"][a:b]                       # real arrival at the stop, ascending
        i = int(np.searchsorted(keys, NIGHT_END - w, "right")) - 1
        if i < 0:
            continue
        dep = -int(D["val"][a + i])                # real departure from Jamaica (penalty 0 in this profile)
        if best is None or dep > best[0] or (dep == best[0] and int(keys[i]) + w < best[1]):
            best = (dep, int(keys[i]) + w, s, a + i, m, w)
    out_base = dict(search_window="Saturday 21:00 to Sunday 05:00 (arrive at the door by 05:00)")
    if jm <= ACCESS_MAX_M and (best is None or best[0] < NIGHT_END - _walk_s(jm)):
        return dict(value="any time (walk)", value_type="found", source_url=None, retrieved_at=n["built_at"],
                    method=f"point is {jm:.0f} m from Jamaica station: walking, no timetable needed", **out_base)
    if best is None or best[0] < NIGHT_START:
        return dict(value=None, value_type="not_found",
                    reason="no departure from Jamaica after 21:00 on the Saturday timetable reaches a stop within "
                           "1.5 km of the point by 05:00", source_url=None, retrieved_at=n["built_at"], **out_base)
    dep, arr, s, i, m, w = best
    rides, jw = _profile_legs(n, tt, s, i, True, 0)
    rides.reverse()
    prov = _prov(n, [r["feed"] for r in rides], ["sat", "sun"] if arr > 86400 or dep >= 86400 else ["sat"],
                 "Latest departure found with a time-mirrored profile search (no transfer penalty).")
    first = rides[0]
    jam_name = n["node_name"][n["jam"]]
    legs = _fmt_legs(n, rides, (jw, None, ANCHOR["name"], n["node_name"][first["from_node"]]) if jw else None,
                     (w, m, n["node_name"][s], "door"), False, "sat")
    return dict(value=_hhmm(dep), leaves_jamaica_station_at=_hhmm(dep), arrives_door=_hhmm(arr),
                minutes=round((arr - dep) / 60, 1), transfers=len(rides) - 1,
                lines=[_label(r["system"], r["line"]) for r in rides], leg_summary=_summary(legs),
                effectively_all_night=dep >= 27 * 3600,
                note="Leave-Jamaica time; journeys that start with the walk to the Sutphin Blvd subway leave the "
                     "LIRR station at this time." if jw else None, **prov, **out_base)


def route(lat: float, lon: float, when: str = "sat_midday") -> dict:
    """Door-to-door transit between (lat, lon) and Jamaica LIRR station. See module docstring."""
    if when not in WINDOWS:
        raise ValueError(f"when must be one of {sorted(WINDOWS)}")
    n = _net()
    w = WINDOWS[when]
    tt = n["tt"][when]
    day = w["day"]
    res = dict(input=dict(lat=lat, lon=lon, when=when), anchor=ANCHOR, direction=w["direction"],
               window=w["label"], service_date=SERVICE_DATES[day])
    jm = _hav_m(lat, lon, ANCHOR["lat"], ANCHOR["lon"])
    near_all = _near(n, lat, lon, ACCESS_MAX_M)
    usable = tt["usable"]
    near = [(m, s) for m, s in near_all if usable[s]]
    deps = list(range(w["start"], w["end"] + 1, w["step"]))
    gen = dict(source_url="; ".join(sorted(f["url"] for f in n["feeds"].values())), retrieved_at=n["built_at"])

    res["last_departure_from_jamaica_sat"] = _last_departure(n, lat, lon, near_all)

    if not near and jm > ACCESS_MAX_M:
        res.update(status="not_found",
                   reason=f"no stop with service in this window within {ACCESS_MAX_M / 1000:.1f} km straight-line "
                          f"of the point (park-and-ride is out of scope)",
                   nearest_stop=_nearest(n, lat, lon, usable=usable),
                   nearest_rail_or_ferry_station=_nearest(n, lat, lon, idxs=n["rail_nodes"], usable=usable),
                   value_type="not_found", method="nearest stop by straight-line distance among the merged GTFS feeds",
                   **gen)
        return res

    walk_only = _walk_s(jm) if jm <= ACCESS_MAX_M else None
    samples = []      # per departure: (minutes, cost, stop, pointer, walk_s, metres) or None
    P = TRANSFER_PENALTY_S
    if w["direction"] == "to_jamaica":
        D = tt["D"]
        for t in deps:
            best = None
            for m, s in near:
                ws = _walk_s(m)
                i = _eval(D, s, -(t + ws))
                if i >= 0:
                    c = int(D["val"][i])
                    if best is None or c < best[1]:
                        best = ((c - P * int(D["n"][i]) - t) / 60.0, c, s, i, ws, m)
            if walk_only is not None and (best is None or t + walk_only <= best[1]):
                best = (walk_only / 60.0, t + walk_only, -1, -1, walk_only, jm)
            samples.append(best)
    else:
        A = tt["A"]
        ss = np.array([s for _, s in near], dtype=np.int64)
        wsv = np.array([_walk_s(m) for m, _ in near], dtype=np.int64)
        pen = (np.arange(MAX_RIDES + 1, dtype=np.int64) - 1) * P
        for ri, t in enumerate(deps):
            best = None
            if len(ss):
                arr = A[ri][:, ss].astype(np.int64) + wsv[None, :]        # (K+1, stops)
                cost = arr + pen[:, None]
                k, j = np.unravel_index(int(np.argmin(cost[1:])), cost[1:].shape)
                k += 1
                if arr[k, j] < INF:
                    best = ((int(arr[k, j]) - t) / 60.0, int(cost[k, j]), int(ss[j]), int(k), int(wsv[j]), near[j][0])
            if walk_only is not None and (best is None or t + walk_only <= best[1]):
                best = (walk_only / 60.0, t + walk_only, -1, -1, walk_only, jm)
            samples.append(best)

    ok = [(x[0], idx) for idx, x in enumerate(samples) if x is not None]
    res["departures_sampled"] = len(deps)
    res["departures_with_route"] = len(ok)
    res["minutes_by_departure"] = {_hhmm(t): (None if x is None else round(x[0], 1)) for t, x in zip(deps, samples)}
    if not ok:
        res.update(status="not_found",
                   reason="stops within 1.5 km have service in this window but no journey to/from Jamaica was found",
                   nearest_stop=_nearest(n, lat, lon, usable=usable), value_type="not_found",
                   method="timetable search over the merged GTFS feeds", **gen)
        return res

    mins = sorted(x[0] for x in ok)
    fastest_min, fi = min(ok)
    mid = len(mins) // 2
    median = mins[mid] if len(mins) % 2 else (mins[mid - 1] + mins[mid]) / 2
    best = samples[fi]
    t = deps[fi]
    if best[2] < 0:
        rides = []
        legs = [dict(mode="walk", **{"from": "door" if w["direction"] == "to_jamaica" else ANCHOR["name"],
                                     "to": ANCHOR["name"] if w["direction"] == "to_jamaica" else "door"},
                     minutes=round(best[4] / 60, 1), straight_line_m=int(round(jm)))]
    elif w["direction"] == "to_jamaica":
        rides, jw = _profile_legs(n, tt, best[2], best[3], False, P)
        legs = _fmt_legs(n, rides, (best[4], best[5], "door", n["node_name"][best[2]]),
                         (jw, None, n["node_name"][rides[-1]["to_node"]], ANCHOR["name"]) if jw else None, True, day)
    else:
        rides = _forward_legs(n, tt, fi, best[2], best[3])
        first = rides[0]["from_node"]
        jw = n["target_walk"].get(first, 0)
        legs = _fmt_legs(n, rides, (jw, None, ANCHOR["name"], n["node_name"][first]) if jw else None,
                         (best[4], best[5], n["node_name"][best[2]], "door"), False, day)

    # provenance: the fastest journey's feeds for its own values; every sampled journey's feeds for the median
    used = [r["feed"] for r in rides]
    prov = _prov(n, used, [day])
    all_used = set(used)
    for idx, x in enumerate(samples):
        if x is None or x[2] < 0 or idx == fi:
            continue
        rs = _profile_legs(n, tt, x[2], x[3], False, P)[0] if w["direction"] == "to_jamaica" \
            else _forward_legs(n, tt, idx, x[2], x[3])
        all_used.update(r["feed"] for r in rs)
    prov_med = _prov(n, all_used, [day], f"Journeys minimise arrival time + {TRANSFER_PENALTY_S // 60} min per transfer. Median over the "
                     "sampled departures (feeds of every sampled journey listed).")
    res.update(
        status="ok",
        fastest_minutes=dict(value=round(fastest_min, 1), departure=_hhmm(t), **prov),
        median_minutes=dict(value=round(median, 1), **prov_med),
        transfers=dict(value=max(0, len(rides) - 1), **prov),
        systems=dict(value=list(dict.fromkeys(r["system"] for r in rides)), **prov),
        lines=dict(value=[_label(r["system"], r["line"]) for r in rides], **prov),
        legs=legs,
        leg_summary=dict(value=_summary(legs), **prov),
    )
    fares = [g["fare_one_way"] for g in legs if "fare_one_way" in g]
    if rides and all(f["value_type"] == "found" for f in fares):
        res["fare_one_way_total"] = dict(value=round(sum(f["value"] for f in fares), 2), value_type="found",
                                         method="sum of per-leg fares from GTFS fare tables (free transfers "
                                                "between legs not modelled)",
                                         source_url=prov["source_url"], retrieved_at=prov["retrieved_at"])
    else:
        res["fare_one_way_total"] = dict(value=None, value_type="not_found",
                                         reason="walk only" if not rides else
                                         "at least one leg's feed has no fare table; see legs[].fare_one_way",
                                         source_url=prov["source_url"], retrieved_at=prov["retrieved_at"])
    return res


# ----------------------------------------------------------------------------------------------- self-test
TEST_POINTS = [("Jamaica station", 40.699608, -73.808530), ("Forest Hills", 40.7196, -73.8448),
               ("Long Beach NY", 40.5890, -73.6649), ("Stamford CT", 41.0469, -73.5419),
               ("Jersey City Grove St", 40.7196, -74.0431), ("Beacon NY", 41.5060, -73.9845)]

if __name__ == "__main__":
    if "--rebuild" in sys.argv or not NET_PATH.exists():
        build()
    t0 = time.time()
    _net()
    print(f"network loaded in {time.time() - t0:.1f}s")
    full = "--json" in sys.argv
    for name, la, lo in TEST_POINTS:
        print(f"\n=== {name} ({la}, {lo})")
        for when in WINDOWS:
            t1 = time.time()
            r = route(la, lo, when)
            ms = (time.time() - t1) * 1000
            if full:
                print(json.dumps(r, indent=1, default=str))
                continue
            if r["status"] != "ok":
                print(f"  {when}: NOT FOUND ({r['reason']}); nearest stop {r.get('nearest_stop')}  [{ms:.0f} ms]")
            else:
                print(f"  {when}: fastest {r['fastest_minutes']['value']} min (dep {r['fastest_minutes']['departure']}),"
                      f" median {r['median_minutes']['value']} min, transfers {r['transfers']['value']},"
                      f" {r['departures_with_route']}/{r['departures_sampled']} departures,"
                      f" {r['fastest_minutes']['value_type']}, fare {r['fare_one_way_total']['value']}  [{ms:.0f} ms]")
                print(f"      {r['leg_summary']['value']}")
        ld = r["last_departure_from_jamaica_sat"]
        print(f"  last Sat departure from Jamaica: {ld.get('value')} ({ld['value_type']})"
              f" arrives {ld.get('arrives_door')}; {ld.get('leg_summary') or ld.get('reason') or ld.get('method')}")
