"""Fetch helper for the neighborhood-voices lookups: honest UA, >= 3 s per host (more if robots says so)."""
from __future__ import annotations
import lib
UA = "house-hunt-research/0.1 (personal research for one renter; user-requested lookups)"
for h in ("www.trulia.com", "www.niche.com", "www.city-data.com"):
    lib.HOST_DELAY[h] = 3.5
lib.DEFAULT_DELAY = max(lib.DEFAULT_DELAY, 3.5)

def get(url, source, ext="html", **kw):
    return lib.cached_get(url, source, ext=ext, headers={"User-Agent": UA, "Accept": "text/html,*/*"}, retries=1, timeout=40, **kw)
