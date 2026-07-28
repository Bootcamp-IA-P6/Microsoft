"""
Fabric User Data Function item: udf-emt-ingest
PASTE THIS ENTIRE FILE into the UDF (single-module).

Phase 4 production poller:
  - Scope stops = ALL distinct stop_id from Lakehouse silver_arrives (bootstrap catalogue)
  - Optional stopIdsCsv override / batchOffset+batchLimit for Pipeline chunking
  - Arrives → bronze + silver_arrives facts → Eventstreams
  - Alerts → full GTFS-RT decode → bronze + silver_alerts → Eventstreams
  - Gold ETA patch + gold alerts patch events (EH applies / or KQL MV)

Libraries (Library management → Publish):
  requests==2.32.5
  azure-eventhub==5.15.1

Connections (Manage connections):
  - Lakehouse alias → parameter lhSql (FabricLakehouseClient + connectToSql)
  - Variable Library varemtmadrid → parameter varLib
  Do NOT use FabricSqlConnection.connect() for a Lakehouse connection.
"""
import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

import fabric.functions as fn
import requests

udf = fn.UserDataFunctions()

MADRID = ZoneInfo("Europe/Madrid")
UTC = timezone.utc
BASE_URL = "https://openapi.emtmadrid.es"
SERVICEALERTS_URL = "https://openapi.emtmadrid.es/v1/bus/servicealerts/proto"
ARRIVES_BODY = {
    "cultureInfo": "es",
    "Text_StopRequired_YN": "Y",
    "Text_EstimationsRequired_YN": "Y",
    "Text_IncidencesRequired_YN": "N",
}
ARRIVES_BODY_BYTES = json.dumps(ARRIVES_BODY, ensure_ascii=False).encode("utf-8")
AUTH_API_CODES = frozenset({"80", "81", "82", "83", "89", "90"})
HTTP_HEADERS_JSON = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; emt-pipeline/0.1; "
        "+https://github.com/Bootcamp-IA-P6/Microsoft)"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Connection": "close",
}
STALE_AFTER_SEC_DEFAULT = 900

# Lakehouse *item* name for three-part SQL (NOT the UDF connection alias `lhemtmadrid`)
LH_SQL_DB = "lh_emt_madrid"

# --- Eventstream connection strings (Custom endpoint → SAS primary) ---
ARRIVES_BRONZE_CONN = ""
ARRIVES_SILVER_CONN = ""
ALERTS_BRONZE_CONN = ""
ALERTS_SILVER_CONN = ""
GOLD_PATCH_CONN = ""  # optional: gold_arrives_patch / gold_alerts_patch events
ARRIVES_BRONZE_HUB = ""
ARRIVES_SILVER_HUB = ""
ALERTS_BRONZE_HUB = ""
ALERTS_SILVER_HUB = ""
GOLD_PATCH_HUB = ""

_GTFS_CAUSE = {
    1: "UNKNOWN_CAUSE", 2: "OTHER_CAUSE", 3: "TECHNICAL_PROBLEM", 4: "STRIKE",
    5: "DEMONSTRATION", 6: "ACCIDENT", 7: "HOLIDAY", 8: "WEATHER", 9: "MAINTENANCE",
    10: "CONSTRUCTION", 11: "POLICE_ACTIVITY", 12: "MEDICAL_EMERGENCY",
}
_GTFS_EFFECT = {
    1: "NO_SERVICE", 2: "REDUCED_SERVICE", 3: "SIGNIFICANT_DELAYS", 4: "DETOUR",
    5: "ADDITIONAL_SERVICE", 6: "MODIFIED_SERVICE", 7: "OTHER_EFFECT", 8: "UNKNOWN_EFFECT",
    9: "STOP_MOVED", 10: "NO_EFFECT", 11: "ACCESSIBILITY_ISSUE",
}


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def _utc_now_z() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_name(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().upper())


def _to_int(v):
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None


def _parse_arrive_geometry(geom):
    """GeoJSON Point → (bus_lat, bus_lon). coordinates are [lon, lat]. Missing/bad → (None, None)."""
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
    if lon != lon or lat != lat:  # NaN
        return None, None
    return lat, lon


def _map_dir(destination, name_a, name_b):
    d = _norm_name(destination)
    if not d:
        return None
    nb, na = _norm_name(name_b), _norm_name(name_a)
    if nb and (d == nb or nb in d or d in nb):
        return 0
    if na and (d == na or na in d or d in na):
        return 1
    return None


def _parse_api_dt(raw):
    if raw is None or raw == "":
        return None
    s = str(raw).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00")) if "T" in s or s.endswith("Z") else datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=MADRID)
    return dt.astimezone(UTC).replace(tzinfo=None, microsecond=0)


def _sha_rk(stop_id, line_id, direction_id, bus_id, datetime_polling: datetime) -> str:
    ts = datetime_polling.isoformat(sep="T", timespec="seconds")
    parts = [str(stop_id), str(line_id), "" if direction_id is None else str(direction_id),
             "" if bus_id is None else str(bus_id), ts]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _sha_alert_rk(alert_id, route_id, snapshot_at: datetime) -> str:
    ts = snapshot_at.isoformat(sep="T", timespec="seconds")
    rid = "" if route_id is None else str(route_id)
    return hashlib.sha256(f"{alert_id}|{rid}|{ts}".encode("utf-8")).hexdigest()


def _bronze(source_system, resource_kind, resource_key, http_status, payload_obj, api_code="", api_description=None):
    payload_s = json.dumps(payload_obj, ensure_ascii=False)
    return {
        "emt_record": "bronze",
        "ingest_id": str(uuid.uuid4()),
        "ingested_at": _utc_now_z(),
        "source_system": source_system,
        "resource_kind": resource_kind,
        "resource_key": str(resource_key),
        "http_status": str(http_status),
        "api_code": str(api_code or ""),
        "api_description": api_description,
        "payload": payload_s,
        "content_sha256": hashlib.sha256(payload_s.encode("utf-8")).hexdigest(),
        "timezone_note": "Europe/Madrid",
    }


def _send(conn_str: str, hub: str, events: list) -> int:
    if not events:
        return 0
    if not (conn_str or "").strip():
        raise ValueError("Eventstream connection string empty — set CONN constants after Custom endpoint Publish")
    from azure.eventhub import EventData, EventHubProducerClient
    kwargs = {"conn_str": conn_str}
    if (hub or "").strip():
        kwargs["eventhub_name"] = hub.strip()
    producer = EventHubProducerClient.from_connection_string(**kwargs)
    # Event Hubs max batch ~1MB; chunk
    sent = 0
    chunk: list = []
    size = 0
    with producer:
        for ev in events:
            raw = json.dumps(ev, ensure_ascii=False, default=str)
            if chunk and size + len(raw) > 900_000:
                producer.send_batch([EventData(x) for x in chunk])
                sent += len(chunk)
                chunk, size = [], 0
            chunk.append(raw)
            size += len(raw)
        if chunk:
            producer.send_batch([EventData(x) for x in chunk])
            sent += len(chunk)
    return sent


# --- minimal protobuf decode (servicealerts) ---
def _pb_read_varint(buf, i):
    result = shift = 0
    while True:
        b = buf[i]; i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7

def _pb_skip(buf, i, wt):
    if wt == 0:
        _, i = _pb_read_varint(buf, i); return i
    if wt == 1: return i + 8
    if wt == 2:
        ln, i = _pb_read_varint(buf, i); return i + ln
    if wt == 5: return i + 4
    raise ValueError(wt)

def _pb_parse(buf, i, end, handlers, out=None):
    if out is None: out = {}
    while i < end:
        key, i = _pb_read_varint(buf, i)
        fn, wt = key >> 3, key & 7
        i = handlers[fn](buf, i, wt, out) if fn in handlers else _pb_skip(buf, i, wt)
    return out, i

def _pb_len(buf, i, wt):
    if wt != 2: raise ValueError("len")
    ln, i = _pb_read_varint(buf, i)
    return i, i + ln

def _pb_translated(buf, i, end):
    translations = []
    def h_tr(buf, i, wt, out):
        i0, i1 = _pb_len(buf, i, wt)
        def h_text(buf, i, wt, o):
            a, b = _pb_len(buf, i, wt); o["text"] = buf[a:b].decode("utf-8", "replace"); return b
        def h_lang(buf, i, wt, o):
            a, b = _pb_len(buf, i, wt); o["language"] = buf[a:b].decode("utf-8", "replace"); return b
        translations.append(_pb_parse(buf, i0, i1, {1: h_text, 2: h_lang})[0]); return i1
    _pb_parse(buf, i, end, {1: h_tr}); return {"translation": translations}

def _pb_time_range(buf, i, end):
    def h_start(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i); out["start"] = str(v); return i
    def h_end(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i); out["end"] = str(v); return i
    return _pb_parse(buf, i, end, {1: h_start, 2: h_end})[0]

def _pb_entity_selector(buf, i, end):
    def h_agency(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["agency_id"] = buf[a:b].decode("utf-8", "replace"); return b
    def h_route(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["route_id"] = buf[a:b].decode("utf-8", "replace"); return b
    def h_rtype(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i); out["route_type"] = v; return i
    def h_trip(buf, i, wt, out): return _pb_skip(buf, i, wt)
    def h_stop(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["stop_id"] = buf[a:b].decode("utf-8", "replace"); return b
    return _pb_parse(buf, i, end, {1: h_agency, 2: h_route, 3: h_rtype, 4: h_trip, 5: h_stop})[0]

def _pb_alert(buf, i, end):
    out = {"active_period": [], "informed_entity": []}
    def h_period(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["active_period"].append(_pb_time_range(buf, a, b)); return b
    def h_ie(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["informed_entity"].append(_pb_entity_selector(buf, a, b)); return b
    def h_cause(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i); out["cause"] = _GTFS_CAUSE.get(v, str(v)); return i
    def h_effect(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i); out["effect"] = _GTFS_EFFECT.get(v, str(v)); return i
    def h_url(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["url"] = _pb_translated(buf, a, b); return b
    def h_header(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["header_text"] = _pb_translated(buf, a, b); return b
    def h_desc(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["description_text"] = _pb_translated(buf, a, b); return b
    return _pb_parse(buf, i, end, {1: h_period, 5: h_ie, 6: h_cause, 7: h_effect, 8: h_url, 10: h_header, 11: h_desc}, out=out)[0]

def _pb_entity(buf, i, end):
    def h_id(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["id"] = buf[a:b].decode("utf-8", "replace"); return b
    def h_alert(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["alert"] = _pb_alert(buf, a, b); return b
    return _pb_parse(buf, i, end, {1: h_id, 5: h_alert})[0]

def _pb_header(buf, i, end):
    def h_ver(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["gtfs_realtime_version"] = buf[a:b].decode("utf-8", "replace"); return b
    def h_inc(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i); out["incrementality"] = v; return i
    def h_ts(buf, i, wt, out):
        v, i = _pb_read_varint(buf, i); out["timestamp"] = str(v); return i
    return _pb_parse(buf, i, end, {1: h_ver, 2: h_inc, 3: h_ts})[0]

def decode_feed_to_dict(raw: bytes) -> dict:
    out = {"header": {}, "entity": []}
    def h_header(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["header"] = _pb_header(buf, a, b); return b
    def h_ent(buf, i, wt, out):
        a, b = _pb_len(buf, i, wt); out["entity"].append(_pb_entity(buf, a, b)); return b
    return _pb_parse(raw, 0, len(raw), {1: h_header, 2: h_ent}, out=out)[0]


def _creds(varLib, clientId: str, passKey: str):
    if clientId and passKey:
        return clientId, passKey
    if varLib is None:
        raise ValueError("Pass clientId/passKey or connect Variable Library")
    variables = varLib.getVariables()
    cid = (clientId or variables.get("EMT_CLIENT_ID") or "").strip()
    pk = (passKey or variables.get("EMT_MADRID_PASS_KEY") or "").strip()
    if not cid or not pk:
        raise ValueError("EMT_CLIENT_ID / EMT_MADRID_PASS_KEY missing")
    return cid, pk


def _login(client_id: str, pass_key: str) -> str:
    last_err = None
    for attempt in range(1, 4):
        try:
            r = requests.get(
                f"{BASE_URL}/v1/mobilitylabs/user/login/",
                headers={
                    **HTTP_HEADERS_JSON,
                    "X-ClientId": client_id,
                    "passKey": pass_key,
                },
                timeout=60,
            )
            raw = r.text
            if r.status_code >= 400:
                raise RuntimeError(f"login HTTP {r.status_code}: {raw[:200]}")
            body = r.json()
            if str(body.get("code", "")) not in ("00", "01"):
                raise RuntimeError(
                    f"login code={body.get('code')}: {body.get('description')}"
                )
            return body["data"][0]["accessToken"]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"login failed: {last_err}")


def _fetch_arrives(token: str, stop_id: str):
    """Match Lakehouse pipeline: raw JSON bytes body + accessToken header."""
    sid = str(stop_id).strip()
    if sid.isdigit():
        sid = str(int(sid))  # normalize "02711" / "2711 "
    path = f"/v2/transport/busemtmad/stops/{sid}/arrives/"
    url = f"{BASE_URL}{path}"
    last_err = None
    for attempt in range(1, 5):
        try:
            r = requests.post(
                url,
                headers={
                    **HTTP_HEADERS_JSON,
                    "accessToken": token,
                    "Content-Type": "application/json",
                },
                data=ARRIVES_BODY_BYTES,
                timeout=30,
            )
            raw = r.text
            if r.status_code == 401:
                return None, 401, "http_401_token", sid
            if r.status_code in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"HTTP {r.status_code}: {raw[:200]}")
            if r.status_code >= 400:
                return None, r.status_code, f"http_{r.status_code}:{raw[:120]}", sid
            try:
                body = r.json()
            except ValueError:
                return None, r.status_code, f"non-json:{raw[:120]}", sid
            if not isinstance(body, dict):
                return None, r.status_code, f"bad_json_type:{type(body)}", sid
            return body, int(r.status_code), None, sid
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(min(2**attempt, 10))
    return None, 0, f"retries_exhausted:{last_err}", sid


def _sql_table(name: str) -> str:
    """Three-part name: [LakehouseItem].[dbo].[table] — alias ≠ item name."""
    return f"[{LH_SQL_DB}].[dbo].[{name}]"


def _connect_sql(lakehouse: fn.FabricLakehouseClient):
    """Lakehouse connection → SQL endpoint (not FabricSqlConnection.connect)."""
    return lakehouse.connectToSql()


def _load_scope_and_catalogue(lakehouse: fn.FabricLakehouseClient):
    """All in-scope stops + catalogue grains from Lakehouse silver_arrives (bootstrap)."""
    if lakehouse is None:
        raise ValueError("Lakehouse connection required (alias lhemtmadrid)")
    conn = _connect_sql(lakehouse)
    cur = conn.cursor()
    # T-SQL / ODBC: use 1 not true for bit/boolean columns
    try:
        cur.execute(
            f"""
            SELECT stop_id, line_id, direction_id, line_label, stop_name, stop_lat, stop_lon,
                   direction_text, name_a, name_b, is_terminus, catalog_loaded_at, day_type
            FROM {_sql_table("silver_arrives")}
            WHERE bus_id IS NULL AND map_ok = 1 AND direction_id IS NOT NULL
            """
        )
    except Exception as exc:  # noqa: BLE001
        # Helpful hint when LH_SQL_DB does not match the workspace lakehouse item name
        try:
            cur2 = conn.cursor()
            cur2.execute(
                "SELECT name FROM sys.databases WHERE database_id > 4 ORDER BY name"
            )
            dbs = [str(r[0]) for r in cur2.fetchall()]
            cur2.close()
        except Exception:  # noqa: BLE001
            dbs = []
        raise RuntimeError(
            f"SQL failed on {_sql_table('silver_arrives')}: {exc}. "
            f"Set LH_SQL_DB to your Lakehouse *item* name (not alias lhemtmadrid). "
            f"Visible DBs sample: {dbs[:20]}"
        ) from exc

    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    if not rows:
        raise RuntimeError("No catalogue rows in silver_arrives — run daily bootstrap first")
    cat_by_grain, grains_by_stop, label_at_stop, line_names = {}, {}, {}, {}
    day_type = "LA"
    stops = set()
    for r in rows:
        sid, lid, did = str(r["stop_id"]), str(r["line_id"]), int(r["direction_id"])
        # normalize types from SQL
        r = {**r, "stop_id": sid, "line_id": lid, "direction_id": did, "line_label": str(r["line_label"])}
        cat_by_grain[(sid, lid, did)] = r
        grains_by_stop.setdefault(sid, []).append(((sid, lid, did), r))
        label_at_stop[(sid, str(r["line_label"]))] = lid
        line_names[lid] = (r.get("name_a"), r.get("name_b"))
        stops.add(sid)
        if r.get("day_type"):
            day_type = str(r["day_type"])
    return sorted(stops), cat_by_grain, grains_by_stop, label_at_stop, line_names, day_type, rows


def _expand_arrives(payload, resource_key, ingested_at, cat_by_grain, grains_by_stop, label_at_stop, line_names, day_type):
    candidates = []
    dt_poll = _parse_api_dt(payload.get("datetime")) or ingested_at
    stop_key = str(resource_key)
    label_to_line = {}
    for block in payload.get("data", []) or []:
        for si in block.get("StopInfo", []) or []:
            for ln in si.get("lines", []) or []:
                label = str(ln.get("label") or "").strip()
                line_id = str(ln.get("line") or "").strip()
                if label and line_id:
                    label_to_line[label] = line_id
    found = False
    for block in payload.get("data", []) or []:
        for arr in block.get("Arrive", []) or []:
            found = True
            line_label = str(arr.get("line") or "").strip()
            if not line_label:
                continue
            sid = str(_to_int(arr.get("stop")) or stop_key)
            bus_raw = arr.get("bus")
            bus_id = None if bus_raw is None or bus_raw == "" else str(bus_raw).strip()
            destination = str(arr.get("destination") or "").strip() or None
            eta = _to_int(arr.get("estimateArrive"))
            line_id = label_to_line.get(line_label) or label_at_stop.get((sid, line_label))
            map_ok = line_id is not None
            if not map_ok:
                line_id = line_label
            name_a = name_b = None
            if map_ok:
                name_a, name_b = line_names.get(line_id, (None, None))
            direction_id = _map_dir(destination, name_a, name_b)
            denorm = cat_by_grain.get((sid, line_id, direction_id)) if map_ok and direction_id is not None else None
            if denorm is None and map_ok:
                for (_g, row) in grains_by_stop.get(sid, []):
                    if _g[1] == line_id:
                        denorm = row
                        break
            if direction_id is None:
                map_ok = False
            bus_lat, bus_lon = _parse_arrive_geometry(arr.get("geometry"))
            candidates.append({
                "emt_record": "silver_arrives",
                "_rk": _sha_rk(sid, line_id, direction_id, bus_id, dt_poll),
                "stop_id": sid, "line_id": str(line_id), "line_label": line_label,
                "direction_id": direction_id, "bus_id": bus_id, "destination": destination,
                "eta_seconds": eta,
                "bus_lat": bus_lat, "bus_lon": bus_lon,
                "datetime_polling": dt_poll.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ingested_at": ingested_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stop_name": denorm["stop_name"] if denorm else None,
                "stop_lat": float(denorm["stop_lat"]) if denorm and denorm.get("stop_lat") is not None else None,
                "stop_lon": float(denorm["stop_lon"]) if denorm and denorm.get("stop_lon") is not None else None,
                "direction_text": denorm["direction_text"] if denorm else None,
                "name_a": name_a if name_a is not None else (denorm["name_a"] if denorm else None),
                "name_b": name_b if name_b is not None else (denorm["name_b"] if denorm else None),
                "is_terminus": bool(denorm["is_terminus"]) if denorm else False,
                "catalog_loaded_at": str(denorm["catalog_loaded_at"]) if denorm and denorm.get("catalog_loaded_at") else None,
                "day_type": (denorm["day_type"] if denorm else None) or day_type,
                "map_ok": bool(map_ok and direction_id is not None),
            })
    if not found:
        for (g, row) in grains_by_stop.get(stop_key, []):
            s, l, d = g
            candidates.append({
                "emt_record": "silver_arrives",
                "_rk": _sha_rk(s, l, d, None, dt_poll),
                "stop_id": s, "line_id": l, "line_label": row["line_label"], "direction_id": d,
                "bus_id": None, "destination": None, "eta_seconds": None,
                "bus_lat": None, "bus_lon": None,
                "datetime_polling": dt_poll.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ingested_at": ingested_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stop_name": row["stop_name"], "stop_lat": float(row["stop_lat"]) if row.get("stop_lat") is not None else None,
                "stop_lon": float(row["stop_lon"]) if row.get("stop_lon") is not None else None,
                "direction_text": row["direction_text"], "name_a": row["name_a"], "name_b": row["name_b"],
                "is_terminus": bool(row["is_terminus"]),
                "catalog_loaded_at": str(row["catalog_loaded_at"]) if row.get("catalog_loaded_at") else None,
                "day_type": row["day_type"] or day_type, "map_ok": True,
            })
    return candidates


def _gold_eta_from_facts(facts, stale_after_sec):
    now = _utc_now()
    by = {}
    for r in facts:
        if not r.get("map_ok") or r.get("direction_id") is None:
            continue
        key = (r["stop_id"], r["line_id"], int(r["direction_id"]))
        by.setdefault(key, []).append(r)
    out = []
    for (sid, lid, did), rows in by.items():
        def ts(x):
            return datetime.fromisoformat(str(x["datetime_polling"]).replace("Z", ""))
        max_ts = max(ts(r) for r in rows)
        latest = [r for r in rows if ts(r) == max_ts]
        buses = sorted([r for r in latest if r.get("eta_seconds") is not None], key=lambda r: int(r["eta_seconds"]))
        head = latest[0]
        eta1 = int(buses[0]["eta_seconds"]) if buses else None
        out.append({
            "emt_record": "gold_arrives_patch",
            "stop_id": sid, "line_id": lid, "direction_id": did,
            "line_label": head.get("line_label"), "stop_name": head.get("stop_name"),
            "stop_lat": head.get("stop_lat"), "stop_lon": head.get("stop_lon"),
            "direction_text": head.get("direction_text"), "name_a": head.get("name_a"), "name_b": head.get("name_b"),
            "destination": (buses[0].get("destination") if buses else head.get("destination")),
            "eta_seconds_1": eta1, "bus_id_1": buses[0].get("bus_id") if buses else None,
            "bus_lat_1": buses[0].get("bus_lat") if buses else None,
            "bus_lon_1": buses[0].get("bus_lon") if buses else None,
            "eta_seconds_2": int(buses[1]["eta_seconds"]) if len(buses) > 1 else None,
            "bus_id_2": buses[1].get("bus_id") if len(buses) > 1 else None,
            "bus_lat_2": buses[1].get("bus_lat") if len(buses) > 1 else None,
            "bus_lon_2": buses[1].get("bus_lon") if len(buses) > 1 else None,
            "has_upcoming_bus": eta1 is not None,
            "is_stale": (now - max_ts).total_seconds() > int(stale_after_sec),
            "origin_stop_notice": bool(head.get("is_terminus")) and eta1 is None,
            "is_terminus": bool(head.get("is_terminus")),
            "catalog_loaded_at": head.get("catalog_loaded_at"), "day_type": head.get("day_type"),
            "updated_at": max_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return out


def _pick_tr(field):
    if not isinstance(field, dict):
        return None
    texts = field.get("translation") or []
    for t in texts:
        if isinstance(t, dict) and t.get("language") == "es" and t.get("text"):
            return str(t["text"])
    if texts and isinstance(texts[0], dict) and texts[0].get("text"):
        return str(texts[0]["text"])
    return None


def _unix_naive(raw):
    if raw is None or raw == "":
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=UTC).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
        return None


def _expand_alerts(payload, known, ingested_at):
    header = payload.get("header") or {}
    snap = _unix_naive(header.get("timestamp")) or ingested_at
    rows = []
    for ent in payload.get("entity") or []:
        if not isinstance(ent, dict):
            continue
        alert = ent.get("alert") or {}
        if not alert:
            continue
        alert_id = str(ent.get("id") or "").strip()
        if not alert_id:
            continue
        periods = alert.get("active_period") or []
        starts = [t for t in (_unix_naive(p.get("start")) for p in periods if isinstance(p, dict)) if t]
        ends = [t for t in (_unix_naive(p.get("end")) for p in periods if isinstance(p, dict)) if t]
        period_start = min(starts) if starts else None
        period_end = max(ends) if ends else None
        route_ids = []
        for ie in alert.get("informed_entity") or []:
            if isinstance(ie, dict) and ie.get("route_id"):
                route_ids.append(str(ie["route_id"]).strip())
        if not route_ids:
            route_ids = [None]
        for rid in route_ids:
            map_ok = bool(rid and rid in known)
            rows.append({
                "emt_record": "silver_alerts",
                "_rk": _sha_alert_rk(alert_id, rid, snap),
                "alert_id": alert_id,
                "line_id": rid if map_ok else None,
                "alert_header": _pick_tr(alert.get("header_text")),
                "alert_cause": str(alert["cause"]) if alert.get("cause") is not None else None,
                "alert_effect": str(alert["effect"]) if alert.get("effect") is not None else None,
                "alert_url": _pick_tr(alert.get("url")),
                "active_period_start": period_start.strftime("%Y-%m-%dT%H:%M:%SZ") if period_start else None,
                "active_period_end": period_end.strftime("%Y-%m-%dT%H:%M:%SZ") if period_end else None,
                "snapshot_at": snap.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ingested_at": ingested_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "map_ok": map_ok,
            })
    return rows


@udf.function()
def ping() -> str:
    return f"udf-emt-ingest ok @ {_utc_now_z()}"


@udf.connection(argName="lhSql", alias="lhemtmadrid")
@udf.connection(argName="varLib", alias="varemtmadrid")
@udf.function()
def poll_arrives_scope(
    lhSql: fn.FabricLakehouseClient,
    varLib: fn.FabricVariablesClient,
    stopIdsCsv: str = "",
    batchOffset: int = 0,
    batchLimit: int = 0,
    clientId: str = "",
    passKey: str = "",
    staleAfterSec: int = 900,
) -> str:
    """
    Poll ALL catalogue scope stops (or stopIdsCsv override), emit bronze + silver + gold ETA patch.
    Pipeline: call with batchOffset/batchLimit if invocation timeout (e.g. 50 stops per call).
    """
    stops_all, cat_by_grain, grains_by_stop, label_at_stop, line_names, day_type, _cat_rows = _load_scope_and_catalogue(lhSql)
    if (stopIdsCsv or "").strip():
        stops_all = [s.strip() for s in stopIdsCsv.split(",") if s.strip()]
    offset = max(0, int(batchOffset or 0))
    limit = int(batchLimit or 0)
    stops = stops_all[offset: (offset + limit if limit > 0 else None)]
    if not stops:
        return f"no stops in batch offset={offset} total_scope={len(stops_all)}"

    cid, pk = _creds(varLib, clientId, passKey)
    token = _login(cid, pk)
    bronze_events, silver_events = [], []
    fail_details: list = []
    ingested_at = _utc_now()
    for sid in stops:
        body, status, err, sid_norm = _fetch_arrives(token, sid)
        api_code = str((body or {}).get("code", "")) if body else ""
        # Token / auth API codes → refresh once and retry
        if api_code in AUTH_API_CODES or status == 401 or err == "http_401_token":
            token = _login(cid, pk)
            body, status, err, sid_norm = _fetch_arrives(token, sid)
            api_code = str((body or {}).get("code", "")) if body else ""
        # EMT: 00 = OK with data; 01 = OK but no estimations (still a valid poll → bronze)
        ok_codes = frozenset({"00", "01"})
        if body is None or api_code not in ok_codes:
            desc = ""
            if body and isinstance(body, dict):
                desc = str(body.get("description") or body.get("descriptionCode") or "")[:80]
            fail_details.append(
                f"{sid_norm}:api={api_code or '-'} http={status} err={err or '-'} {desc}".strip()
            )
            continue
        br = _bronze(
            "EMT_OPENAPI",
            "arrives",
            sid_norm,
            status,
            body,
            api_code=api_code,
            api_description=body.get("description"),
        )
        bronze_events.append(br)
        # Silver expand: empty Arrive[] still seeds catalogue grains for that stop
        silver_events.extend(
            _expand_arrives(
                body,
                sid_norm,
                ingested_at,
                cat_by_grain,
                grains_by_stop,
                label_at_stop,
                line_names,
                day_type,
            )
        )

    n_b = _send(ARRIVES_BRONZE_CONN, ARRIVES_BRONZE_HUB, bronze_events)
    n_s = _send(
        ARRIVES_SILVER_CONN or ARRIVES_BRONZE_CONN,
        ARRIVES_SILVER_HUB or ARRIVES_BRONZE_HUB,
        silver_events,
    )
    gold_rows = _gold_eta_from_facts(silver_events, staleAfterSec or STALE_AFTER_SEC_DEFAULT)
    n_g = 0
    if (GOLD_PATCH_CONN or "").strip():
        n_g = _send(GOLD_PATCH_CONN, GOLD_PATCH_HUB, gold_rows)
    fail_preview = " | ".join(fail_details[:5])
    if len(fail_details) > 5:
        fail_preview += f" …(+{len(fail_details) - 5})"
    return (
        f"scope_total={len(stops_all)} batch={len(stops)} offset={offset} "
        f"bronze={n_b} silver={n_s} "
        f"gold_patches={n_g if (GOLD_PATCH_CONN or '').strip() else len(gold_rows)}(local) "
        f"fails={len(fail_details)}"
        + (f" detail=[{fail_preview}]" if fail_details else "")
    )


@udf.connection(argName="lhSql", alias="lhemtmadrid")
@udf.function()
def poll_alerts_scope(lhSql: fn.FabricLakehouseClient) -> str:
    """Fetch servicealerts, decode protobuf, emit bronze + silver_alerts snapshot rows."""
    conn = _connect_sql(lhSql)
    cur = conn.cursor()
    cur.execute(
        f"SELECT DISTINCT line_id FROM {_sql_table('silver_arrives')} WHERE line_id IS NOT NULL"
    )
    known = {str(r[0]).strip() for r in cur.fetchall() if r[0]}
    cur.close()
    conn.close()

    resp = requests.get(SERVICEALERTS_URL, headers={"Accept": "application/x-protobuf"}, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"servicealerts HTTP {resp.status_code}")
    payload = decode_feed_to_dict(resp.content)
    ingested_at = _utc_now()
    bronze = _bronze("MDB_GTFS_RT", "servicealerts", "proto", resp.status_code, payload)
    silver = _expand_alerts(payload, known, ingested_at)
    n_b = _send(ALERTS_BRONZE_CONN or ARRIVES_BRONZE_CONN, ALERTS_BRONZE_HUB, [bronze])
    n_s = _send(ALERTS_SILVER_CONN or ALERTS_BRONZE_CONN or ARRIVES_BRONZE_CONN, ALERTS_SILVER_HUB, silver)
    return f"alerts bronze={n_b} silver_rows={n_s} entities={len(payload.get('entity') or [])} known_lines={len(known)}"
