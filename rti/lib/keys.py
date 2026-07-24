"""Row keys (Spark-free)."""
from __future__ import annotations

import hashlib
from datetime import datetime


def sha_rk(stop_id, line_id, direction_id, bus_id, datetime_polling: datetime) -> str:
    ts = datetime_polling.isoformat(sep="T", timespec="seconds")
    parts = [
        str(stop_id),
        str(line_id),
        "" if direction_id is None else str(direction_id),
        "" if bus_id is None else str(bus_id),
        ts,
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def sha_alert_rk(alert_id, route_id, snapshot_at: datetime) -> str:
    ts = snapshot_at.isoformat(sep="T", timespec="seconds")
    rid = "" if route_id is None else str(route_id)
    return hashlib.sha256(f"{alert_id}|{rid}|{ts}".encode("utf-8")).hexdigest()
