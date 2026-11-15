"""Shared helpers: cached, throttled HTTP fetch with a provenance log.

Every network response is written under raw/<source>/ and indexed in
raw/<source>/_index.jsonl (url, retrieved_at, status, path). Re-running a
script reuses the cache unless refresh=True, so normalization can be redone
without refetching.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
SEEDS = ROOT / "seeds"

USER_AGENT = "house-hunt-research/0.1 (personal non-commercial research; low volume)"
_last_hit: dict[str, float] = {}

# Minimum seconds between requests to the same host.
DEFAULT_DELAY = 1.0
HOST_DELAY = {
    "nominatim.openstreetmap.org": 1.2,  # usage policy: max 1 req/s
    "router.project-osrm.org": 1.0,
    "geocoding.geo.census.gov": 0.3,
    "data.cityofnewyork.us": 0.3,
}


_SECRET_PARAMS = re.compile(r"([?&](?:key|api_key|apikey|token)=)[^&]+", re.I)


def redact(url: str) -> str:
    """Strip API keys from URLs before they are written to raw/ or data/ (both are committed)."""
    return _SECRET_PARAMS.sub(r"\1REDACTED", url)


def census_key() -> str:
    """Census API key, kept outside the repo. Pass as params={'key': census_key()}; logs are redacted."""
    p = Path(os.environ.get("CENSUS_API_KEY_FILE", "/root/.config/house-hunt/census_api_key"))
    return os.environ.get("CENSUS_API_KEY") or (p.read_text().strip() if p.exists() else "")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _throttle(host: str) -> None:
    delay = HOST_DELAY.get(host, DEFAULT_DELAY)
    last = _last_hit.get(host, 0.0)
    wait = last + delay - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()


def cached_get(url: str, source: str, *, params: dict | None = None, ext: str = "json",
               refresh: bool = False, timeout: int = 60, retries: int = 3,
               headers: dict | None = None, method: str = "GET", data=None) -> tuple[bytes, dict]:
    """Fetch url (with params) once; return (content, meta). meta has url, retrieved_at, status, path."""
    req = requests.Request(method, url, params=params, data=data).prepare()
    full_url = req.url
    key = hashlib.sha1((method + " " + full_url + " " + (str(data) if data else "")).encode()).hexdigest()[:16]
    d = RAW / source
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{key}.{ext}"
    meta_path = d / f"{key}.meta.json"
    if path.exists() and meta_path.exists() and not refresh:
        return path.read_bytes(), json.loads(meta_path.read_text())

    host = urlparse(full_url).netloc
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    last_err = None
    for attempt in range(retries):
        _throttle(host)
        try:
            r = requests.request(method, url, params=params, data=data, headers=h, timeout=timeout)
            if r.status_code in (429, 502, 503, 504):
                last_err = f"HTTP {r.status_code}"
                time.sleep(5 * (attempt + 1))
                continue
            meta = {"url": redact(full_url), "retrieved_at": now_iso(), "status": r.status_code,
                    "path": str(path.relative_to(ROOT)), "source": source}
            if r.status_code == 200:
                path.write_bytes(r.content)
                meta_path.write_text(json.dumps(meta, indent=1))
            with open(d / "_index.jsonl", "a") as f:
                f.write(json.dumps(meta) + "\n")
            return r.content, meta
        except requests.RequestException as e:  # network hiccup: back off and retry
            last_err = repr(e)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} tries: {redact(full_url)}: {last_err}")


def get_json(url: str, source: str, *, attempts: int = 4, **kw):
    """cached_get + JSON decode. A 200 that isn't JSON (an error page) is purged and refetched."""
    for i in range(attempts):
        content, meta = cached_get(url, source, **kw)
        if meta["status"] != 200:
            raise RuntimeError(f"HTTP {meta['status']} for {meta['url']}")
        try:
            return json.loads(content), meta
        except json.JSONDecodeError:
            p = ROOT / meta["path"]
            p.unlink(missing_ok=True)
            Path(str(p).rsplit(".", 1)[0] + ".meta.json").unlink(missing_ok=True)
            time.sleep(5 * (i + 1))
            kw["refresh"] = True
    raise RuntimeError(f"non-JSON response after {attempts} tries: {redact(url)}")
