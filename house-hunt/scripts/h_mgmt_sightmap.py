"""SightMap (Engrain) embed reader, shared by management-site harvesters.

A community's availability page embeds https://sightmap.com/embed/<hash>; that page's window.__APP_CONFIG__
names https://sightmap.com/app/api/v1/<key>/sightmaps/<id>, the JSON the embed itself loads (robots.txt on
sightmap.com disallows only /manage and /auth). Units carry unit_number, floor, area, price, available_on.
"""
from __future__ import annotations

import json
import re

from h_mgmt_common import polite_get

EMBED_RE = re.compile(r"https://sightmap\.com/embed/([a-z0-9]{6,})")


def find_embed(html: str) -> str:
    m = EMBED_RE.search(html.replace("\\/", "/"))
    return m.group(0) if m and m.group(1) != "api" else ""


def units(embed_url: str, src: str, refresh: bool = False) -> tuple[list[dict], dict]:
    """Return (units, info). Each unit: unit, floor, building, beds, baths, sqft, price, total_min, total_max,
    available_on, available_text, plan, image, required_fees (label -> amount), specials, affordable, raw_path, seen."""
    html, m = polite_get(embed_url, src, refresh=refresh)
    if m["status"] != 200:
        return [], {"error": f"embed {m['status']}"}
    hrefs = re.findall(r'"href":"(https:\\?/\\?/sightmap\.com\\?/app\\?/api\\?/v1\\?/[^"]+)"', html)
    out: list[dict] = []
    info: dict = {"embed": embed_url, "apis": []}
    ld = re.search(r'"@type":"PostalAddress","streetAddress":"([^"]*)","addressLocality":"([^"]*)","addressRegion":"([^"]*)","postalCode":"([^"]*)"', html)
    if ld:
        info["address"] = {"street": ld.group(1), "city": ld.group(2), "state": ld.group(3), "zip": ld.group(4)}
    geo = re.search(r'"latitude":([-\d.]+),"longitude":([-\d.]+)', html)
    if geo:
        info["lat"], info["lon"] = float(geo.group(1)), float(geo.group(2))
    for href in dict.fromkeys(h.replace("\\/", "/") for h in hrefs):
        t, am = polite_get(href, src, ext="json", refresh=refresh)
        if am["status"] != 200:
            info.setdefault("errors", []).append(f"{am['status']} {href}")
            continue
        d = json.loads(t).get("data") or {}
        info["apis"].append(href)
        info["asset_name"] = (d.get("asset") or {}).get("name")
        floors = {f["id"]: f for f in d.get("floors") or []}
        plans = {p["id"]: p for p in d.get("floor_plans") or []}
        info["floor_labels"] = sorted({f.get("filter_short_label") for f in floors.values() if f.get("filter_short_label")}, key=lambda x: (len(x), x))
        for u in d.get("units") or []:
            p = plans.get(u.get("floor_plan_id"), {})
            f = floors.get(u.get("floor_id"), {})
            req = {}
            for grp in u.get("static_expenses") or []:
                if grp.get("key") != "monthly":
                    continue
                for e in grp.get("expenses") or []:
                    if e.get("is_required") and not e.get("is_included"):
                        a = (u.get("static_expense_amounts") or {}).get(e["id"], {})
                        req[e["label"]] = a.get("amount") or a.get("text_amount") or "amount not stated"
            tp = u.get("total_price") or [None, None]
            out.append({
                "unit": u.get("unit_number"), "floor": f.get("filter_short_label") or "", "building": u.get("building") or "",
                "beds": p.get("bedroom_count"), "baths": p.get("bathroom_count"), "sqft": u.get("area"),
                "price": u.get("price"), "total_min": tp[0] if isinstance(tp, list) else tp,
                "total_max": tp[-1] if isinstance(tp, list) else tp,
                "available_on": u.get("available_on") or "", "available_text": u.get("display_available_on") or "",
                "plan": p.get("name") or "", "image": p.get("image_url") or "", "required_fees": req,
                "specials": u.get("specials_description") or "", "lease_term": u.get("display_lease_term") or "",
                "affordable": bool((u.get("affordable_housing_info") or {}).get("is_affordable_housing_unit")),
                "sightmap_unit_id": u.get("id"), "raw_path": am["path"], "seen": am["retrieved_at"],
            })
    return out, info
