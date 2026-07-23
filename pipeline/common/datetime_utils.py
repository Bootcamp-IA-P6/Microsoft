"""Timezone / datetime helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pipeline.config.constants import TZ_NOTE

UTC = timezone.utc
MADRID = ZoneInfo(TZ_NOTE)


def utc_now_iso_z() -> str:
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def parse_api_datetime_to_utc_naive(raw: str | None) -> datetime | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        try:
            if "." not in s:
                return None
            main, rest = s.split(".", 1)
            frac = "".join(ch for ch in rest if ch.isdigit())[:6]
            tzpart = "".join(ch for ch in rest if not ch.isdigit())
            dt = datetime.fromisoformat(f"{main}.{frac}{tzpart}")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MADRID)
    return dt.astimezone(UTC).replace(tzinfo=None, microsecond=0)


def unix_to_naive_utc(ts) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None
