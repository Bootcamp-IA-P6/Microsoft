"""Row key hashes."""
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


def sha_alert_rk(alert_id: str, line_id: str | None, snapshot_at: datetime) -> str:
    ts = snapshot_at.isoformat(sep="T", timespec="seconds")
    parts = [str(alert_id), "" if line_id is None else str(line_id), ts]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
