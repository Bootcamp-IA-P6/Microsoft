"""Small parse helpers."""
from __future__ import annotations

import re


def stop_id_str(raw) -> str | None:
    s = str(raw or "").strip()
    if not s:
        return None
    if re.fullmatch(r"-?\d+", s):
        return str(int(s))
    m = re.search(r"(\d+)$", s)
    return str(int(m.group(1))) if m else None


def to_int_or_none(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


def norm_name(s: str | None) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().upper())
