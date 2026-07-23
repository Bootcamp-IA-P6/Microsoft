"""S2 servicealerts → silver_alerts rows."""
from __future__ import annotations

from datetime import datetime

from pipeline.common.datetime_utils import unix_to_naive_utc
from pipeline.common.keys import sha_alert_rk


def pick_translated(field) -> str | None:
    if not isinstance(field, dict):
        return None
    texts = field.get("translation") or []
    if not texts:
        return None
    for t in texts:
        if isinstance(t, dict) and t.get("language") == "es" and t.get("text"):
            return str(t["text"])
    first = texts[0] if isinstance(texts[0], dict) else None
    if first and first.get("text"):
        return str(first["text"])
    return None


def expand_silver_rows(
    payload: dict, known: set[str], ingested_at: datetime
) -> tuple[list[dict], datetime]:
    header = payload.get("header") or {}
    snap = unix_to_naive_utc(header.get("timestamp")) or ingested_at
    rows: list[dict] = []
    unmapped = 0

    for ent in payload.get("entity") or []:
        if not isinstance(ent, dict):
            continue
        alert = ent.get("alert") or {}
        if not alert:
            continue
        alert_id = str(ent.get("id") or "").strip()
        if not alert_id:
            continue

        header_txt = pick_translated(alert.get("header_text"))
        url_txt = pick_translated(alert.get("url"))
        cause = alert.get("cause")
        effect = alert.get("effect")
        cause_s = str(cause) if cause is not None else None
        effect_s = str(effect) if effect is not None else None

        periods = alert.get("active_period") or []
        starts = [
            unix_to_naive_utc(p.get("start")) for p in periods if isinstance(p, dict)
        ]
        ends = [unix_to_naive_utc(p.get("end")) for p in periods if isinstance(p, dict)]
        starts = [t for t in starts if t is not None]
        ends = [t for t in ends if t is not None]
        period_start = min(starts) if starts else None
        period_end = max(ends) if ends else None

        route_ids: list[str | None] = []
        for ie in alert.get("informed_entity") or []:
            if not isinstance(ie, dict):
                continue
            # Never join on RT stop_id (EMT leaves it empty)
            rid = ie.get("route_id")
            rid_s = str(rid).strip() if rid not in (None, "") else None
            if rid_s:
                route_ids.append(rid_s)
        if not route_ids:
            route_ids = [None]

        for rid in route_ids:
            map_ok = bool(rid and rid in known)
            if rid and not map_ok:
                unmapped += 1
            # Contract: line_id NULL when map_ok=false; _rk still hashes route_id for uniqueness
            rows.append(
                {
                    "_rk": sha_alert_rk(alert_id, rid, snap),
                    "alert_id": alert_id,
                    "line_id": rid if map_ok else None,
                    "alert_header": header_txt,
                    "alert_cause": cause_s,
                    "alert_effect": effect_s,
                    "alert_url": url_txt,
                    "active_period_start": period_start,
                    "active_period_end": period_end,
                    "snapshot_at": snap,
                    "ingested_at": ingested_at,
                    "map_ok": map_ok,
                }
            )

    print(f"silver_alerts candidate rows={len(rows)} unmapped_route_refs={unmapped}")
    return rows, snap
