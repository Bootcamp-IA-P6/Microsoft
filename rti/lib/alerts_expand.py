"""Spark-free alerts expand (alerts_normalize port)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from rti.lib.keys import sha_alert_rk

UTC = timezone.utc
MADRID = ZoneInfo("Europe/Madrid")


def unix_to_naive_utc(raw) -> datetime | None:
    if raw is None or raw == "":
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


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


def expand_alerts_payload(
    payload: dict, known: set[str], ingested_at: datetime
) -> tuple[list[dict], datetime]:
    header = payload.get("header") or {}
    snap = unix_to_naive_utc(header.get("timestamp")) or ingested_at
    rows: list[dict] = []
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
        periods = alert.get("active_period") or []
        starts = [unix_to_naive_utc(p.get("start")) for p in periods if isinstance(p, dict)]
        ends = [unix_to_naive_utc(p.get("end")) for p in periods if isinstance(p, dict)]
        starts = [t for t in starts if t is not None]
        ends = [t for t in ends if t is not None]
        period_start = min(starts) if starts else None
        period_end = max(ends) if ends else None
        route_ids: list[str | None] = []
        for ie in alert.get("informed_entity") or []:
            if not isinstance(ie, dict):
                continue
            rid = ie.get("route_id")
            rid_s = str(rid).strip() if rid not in (None, "") else None
            if rid_s:
                route_ids.append(rid_s)
        if not route_ids:
            route_ids = [None]
        for rid in route_ids:
            map_ok = bool(rid and rid in known)
            rows.append(
                {
                    "emt_record": "silver_alerts",
                    "_rk": sha_alert_rk(alert_id, rid, snap),
                    "alert_id": alert_id,
                    "line_id": rid if map_ok else None,
                    "alert_header": header_txt,
                    "alert_cause": str(cause) if cause is not None else None,
                    "alert_effect": str(effect) if effect is not None else None,
                    "alert_url": url_txt,
                    "active_period_start": period_start.isoformat(sep="T", timespec="seconds") + "Z"
                    if period_start
                    else None,
                    "active_period_end": period_end.isoformat(sep="T", timespec="seconds") + "Z"
                    if period_end
                    else None,
                    "snapshot_at": snap.isoformat(sep="T", timespec="seconds") + "Z",
                    "ingested_at": ingested_at.isoformat(sep="T", timespec="seconds") + "Z",
                    "map_ok": map_ok,
                }
            )
    return rows, snap


def project_gold_alerts(silver_rows: list[dict], gold_line_ids: list[str], now_naive: datetime) -> list[dict]:
    by_line: dict[str, dict] = {}
    for r in silver_rows:
        if not r.get("map_ok") or not r.get("line_id"):
            continue
        start = r.get("active_period_start")
        end = r.get("active_period_end")

        def _p(x):
            if x is None:
                return None
            if isinstance(x, datetime):
                return x.replace(tzinfo=None) if x.tzinfo else x
            return datetime.fromisoformat(str(x).replace("Z", ""))

        st, en = _p(start), _p(end)
        if st is not None and now_naive < st:
            continue
        if en is not None and now_naive >= en:
            continue
        lid = str(r["line_id"])
        aid = str(r.get("alert_id") or "")
        prev = by_line.get(lid)
        if prev is None or aid < prev["alert_id"]:
            by_line[lid] = {
                "alert_id": aid,
                "alert_header": r.get("alert_header"),
                "alert_cause": r.get("alert_cause"),
                "alert_effect": r.get("alert_effect"),
                "alert_url": r.get("alert_url"),
            }
    stage = []
    for lid in gold_line_ids:
        hit = by_line.get(lid)
        if hit:
            stage.append(
                {
                    "emt_record": "gold_alerts_patch",
                    "line_id": lid,
                    "alert_active": True,
                    **{k: hit[k] for k in ("alert_header", "alert_cause", "alert_effect", "alert_url")},
                }
            )
        else:
            stage.append(
                {
                    "emt_record": "gold_alerts_patch",
                    "line_id": lid,
                    "alert_active": False,
                    "alert_header": None,
                    "alert_cause": None,
                    "alert_effect": None,
                    "alert_url": None,
                }
            )
    return stage
