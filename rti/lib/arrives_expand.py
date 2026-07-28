"""Spark-free arrives payload → silver fact rows (Lakehouse arrives_transform port)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from rti.lib.keys import sha_rk

MADRID = ZoneInfo("Europe/Madrid")
UTC = timezone.utc


def norm_name(s: str | None) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().upper())


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


def map_destination_to_direction(destination: str | None, name_a, name_b) -> int | None:
    d = norm_name(destination)
    if not d:
        return None
    nb, na = norm_name(name_b), norm_name(name_a)
    if nb and (d == nb or nb in d or d in nb):
        return 0
    if na and (d == na or na in d or d in na):
        return 1
    return None


def parse_arrive_geometry(geom: Any) -> tuple[float | None, float | None]:
    """GeoJSON Point → (bus_lat, bus_lon). coordinates are [lon, lat]."""
    if not isinstance(geom, dict):
        return None, None
    coords = geom.get("coordinates")
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None, None
    try:
        lon = float(coords[0])
        lat = float(coords[1])
    except (TypeError, ValueError):
        return None, None
    if lon != lon or lat != lat:
        return None, None
    return lat, lon


def parse_api_datetime_to_utc_naive(raw) -> datetime | None:
    if raw is None or raw == "":
        return None
    s = str(raw).strip()
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MADRID)
    return dt.astimezone(UTC).replace(tzinfo=None, microsecond=0)


def expand_arrives_bronze(
    *,
    payload: dict,
    resource_key: str,
    ingested_at: datetime,
    cat_by_grain: dict,
    grains_by_stop: dict,
    label_at_stop: dict,
    line_names: dict,
    day_type_today: str,
) -> list[dict]:
    """Same candidate rules as pipeline.aggregate.arrives_transform."""
    candidates: list[dict] = []
    dt_poll = parse_api_datetime_to_utc_naive(payload.get("datetime"))
    if dt_poll is None:
        dt_poll = ingested_at.replace(microsecond=0) if ingested_at else datetime.now(UTC).replace(
            tzinfo=None, microsecond=0
        )
    stop_key = str(resource_key)

    label_to_line: dict[str, str] = {}
    for block in payload.get("data", []) or []:
        for si in block.get("StopInfo", []) or []:
            for ln in si.get("lines", []) or []:
                label = str(ln.get("label") or "").strip()
                line_id = str(ln.get("line") or "").strip()
                if label and line_id:
                    label_to_line[label] = line_id

    arrives_found = False
    for block in payload.get("data", []) or []:
        for arr in block.get("Arrive", []) or []:
            arrives_found = True
            line_label = str(arr.get("line") or "").strip()
            if not line_label:
                continue
            sid = str(to_int_or_none(arr.get("stop")) or stop_key)
            bus_raw = arr.get("bus")
            bus_id = None if bus_raw is None or bus_raw == "" else str(bus_raw).strip()
            destination = str(arr.get("destination") or "").strip() or None
            eta = to_int_or_none(arr.get("estimateArrive"))
            line_id = label_to_line.get(line_label) or label_at_stop.get((sid, line_label))
            map_ok = line_id is not None
            if not map_ok:
                line_id = line_label
            name_a = name_b = None
            if map_ok:
                name_a, name_b = line_names.get(line_id, (None, None))
            direction_id = map_destination_to_direction(destination, name_a, name_b)
            denorm = None
            if map_ok and direction_id is not None:
                denorm = cat_by_grain.get((sid, line_id, direction_id))
            if denorm is None and map_ok:
                for (_g, row) in grains_by_stop.get(sid, []):
                    if _g[1] == line_id:
                        denorm = row
                        break
            if direction_id is None:
                map_ok = False
            bus_lat, bus_lon = parse_arrive_geometry(arr.get("geometry"))
            candidates.append(
                {
                    "_rk": sha_rk(sid, line_id, direction_id, bus_id, dt_poll),
                    "stop_id": sid,
                    "line_id": str(line_id),
                    "line_label": line_label,
                    "direction_id": direction_id,
                    "bus_id": bus_id,
                    "destination": destination,
                    "eta_seconds": eta,
                    "bus_lat": bus_lat,
                    "bus_lon": bus_lon,
                    "datetime_polling": dt_poll.isoformat(sep="T", timespec="seconds") + "Z",
                    "ingested_at": ingested_at.isoformat(sep="T", timespec="seconds") + "Z"
                    if isinstance(ingested_at, datetime)
                    else str(ingested_at),
                    "stop_name": denorm["stop_name"] if denorm else None,
                    "stop_lat": denorm["stop_lat"] if denorm else None,
                    "stop_lon": denorm["stop_lon"] if denorm else None,
                    "direction_text": denorm["direction_text"] if denorm else None,
                    "name_a": name_a if name_a is not None else (denorm["name_a"] if denorm else None),
                    "name_b": name_b if name_b is not None else (denorm["name_b"] if denorm else None),
                    "is_terminus": bool(denorm["is_terminus"]) if denorm else False,
                    "catalog_loaded_at": (
                        denorm["catalog_loaded_at"].isoformat(sep="T", timespec="seconds") + "Z"
                        if denorm and denorm.get("catalog_loaded_at") and hasattr(denorm["catalog_loaded_at"], "isoformat")
                        else (str(denorm["catalog_loaded_at"]) if denorm else None)
                    ),
                    "day_type": (denorm["day_type"] if denorm else None) or day_type_today,
                    "map_ok": bool(map_ok and direction_id is not None),
                    "emt_record": "silver_arrives",
                }
            )

    if not arrives_found:
        for (g, row) in grains_by_stop.get(stop_key, []):
            s, l, d = g
            candidates.append(
                {
                    "_rk": sha_rk(s, l, d, None, dt_poll),
                    "stop_id": s,
                    "line_id": l,
                    "line_label": row["line_label"],
                    "direction_id": d,
                    "bus_id": None,
                    "destination": None,
                    "eta_seconds": None,
                    "bus_lat": None,
                    "bus_lon": None,
                    "datetime_polling": dt_poll.isoformat(sep="T", timespec="seconds") + "Z",
                    "ingested_at": ingested_at.isoformat(sep="T", timespec="seconds") + "Z"
                    if isinstance(ingested_at, datetime)
                    else str(ingested_at),
                    "stop_name": row["stop_name"],
                    "stop_lat": row["stop_lat"],
                    "stop_lon": row["stop_lon"],
                    "direction_text": row["direction_text"],
                    "name_a": row["name_a"],
                    "name_b": row["name_b"],
                    "is_terminus": bool(row["is_terminus"]),
                    "catalog_loaded_at": (
                        row["catalog_loaded_at"].isoformat(sep="T", timespec="seconds") + "Z"
                        if row.get("catalog_loaded_at") and hasattr(row["catalog_loaded_at"], "isoformat")
                        else str(row.get("catalog_loaded_at") or "")
                    ),
                    "day_type": row["day_type"] or day_type_today,
                    "map_ok": True,
                    "emt_record": "silver_arrives",
                }
            )
    return candidates


def index_catalogue(rows: list[dict]) -> tuple[dict, dict, dict, dict, str]:
    cat_by_grain = {}
    grains_by_stop: dict[str, list] = {}
    label_at_stop: dict[tuple[str, str], str] = {}
    line_names: dict[str, tuple] = {}
    day_type_today = "LA"
    for r in rows:
        sid, lid, did = str(r["stop_id"]), str(r["line_id"]), int(r["direction_id"])
        cat_by_grain[(sid, lid, did)] = r
        grains_by_stop.setdefault(sid, []).append(((sid, lid, did), r))
        label_at_stop[(sid, str(r["line_label"]))] = lid
        line_names[lid] = (r.get("name_a"), r.get("name_b"))
        if r.get("day_type"):
            day_type_today = str(r["day_type"])
    return cat_by_grain, grains_by_stop, label_at_stop, line_names, day_type_today


def build_gold_eta_rows(
    silver_facts: list[dict],
    *,
    now_utc: datetime | None = None,
    stale_after_sec: int = 900,
    freq_by_line: dict | None = None,
) -> list[dict]:
    """Latest poll per grain → eta_1/2 (arrives ownership only; no alert_*)."""
    now_utc = now_utc or datetime.now(UTC).replace(tzinfo=None)
    freq_by_line = freq_by_line or {}
    by_grain: dict[tuple, list] = {}
    for r in silver_facts:
        if not r.get("map_ok") or r.get("direction_id") is None:
            continue
        key = (r["stop_id"], r["line_id"], int(r["direction_id"]))
        by_grain.setdefault(key, []).append(r)

    out: list[dict] = []
    for (sid, lid, did), rows in by_grain.items():
        # max datetime_polling
        def _ts(x):
            raw = x.get("datetime_polling")
            if isinstance(raw, datetime):
                return raw.replace(tzinfo=None) if raw.tzinfo else raw
            s = str(raw).replace("Z", "")
            try:
                return datetime.fromisoformat(s)
            except ValueError:
                return datetime.min

        max_ts = max(_ts(r) for r in rows)
        latest = [r for r in rows if _ts(r) == max_ts]
        buses = [
            r
            for r in latest
            if r.get("eta_seconds") is not None
        ]
        buses.sort(key=lambda r: int(r["eta_seconds"]))
        head = latest[0]
        eta1 = int(buses[0]["eta_seconds"]) if buses else None
        bus1 = buses[0].get("bus_id") if buses else None
        dest = buses[0].get("destination") if buses else head.get("destination")
        eta2 = int(buses[1]["eta_seconds"]) if len(buses) > 1 else None
        bus2 = buses[1].get("bus_id") if len(buses) > 1 else None
        updated_at = max_ts
        is_stale = (now_utc - updated_at).total_seconds() > int(stale_after_sec)
        freq = freq_by_line.get(str(lid), {})
        out.append(
            {
                "emt_record": "gold_arrives_patch",
                "stop_id": sid,
                "line_id": lid,
                "direction_id": did,
                "line_label": head.get("line_label"),
                "stop_name": head.get("stop_name"),
                "direction_text": head.get("direction_text"),
                "name_a": head.get("name_a"),
                "name_b": head.get("name_b"),
                "destination": dest,
                "stop_lat": head.get("stop_lat"),
                "stop_lon": head.get("stop_lon"),
                "eta_seconds_1": eta1,
                "bus_id_1": bus1,
                "bus_lat_1": buses[0].get("bus_lat") if buses else None,
                "bus_lon_1": buses[0].get("bus_lon") if buses else None,
                "eta_seconds_2": eta2,
                "bus_id_2": bus2,
                "bus_lat_2": buses[1].get("bus_lat") if len(buses) > 1 else None,
                "bus_lon_2": buses[1].get("bus_lon") if len(buses) > 1 else None,
                "has_upcoming_bus": eta1 is not None,
                "is_stale": is_stale,
                "origin_stop_notice": bool(head.get("is_terminus")) and eta1 is None,
                "is_terminus": bool(head.get("is_terminus")),
                "catalog_loaded_at": head.get("catalog_loaded_at"),
                "day_type": head.get("day_type"),
                "updated_at": updated_at.isoformat(sep="T", timespec="seconds") + "Z",
                "freq_observed_weekday_min": freq.get("weekday"),
                "freq_observed_weekend_min": freq.get("weekend"),
                "freq_sample_size_weekday": freq.get("weekday_n"),
                "freq_sample_size_weekend": freq.get("weekend_n"),
            }
        )
    return out
