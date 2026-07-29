"""Spark-free GTFS + S1 line-stops → silver_arrives catalogue seed rows (Phase 5).

No pandas/Spark. Used by notebooks and mirrored into UDF paste where needed.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
import shutil
import tempfile
import time
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

UTC = timezone.utc
BASE_URL = "https://openapi.emtmadrid.es"
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; emt-pipeline/0.1; "
        "+https://github.com/Bootcamp-IA-P6/Microsoft)"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Connection": "close",
}
DEFAULT_GTFS_URL = (
    "https://datos.emtmadrid.es/dataset/9b23259a-4491-494b-9695-36a7709b2c12/"
    "resource/3cba2058-9833-422c-a704-bf992d31d2ee/download/gtfs_emt.zip"
)
GEOFENCE_LAT = 40.416729
GEOFENCE_LON = -3.703339
GEOFENCE_RADIUS_M = 600


def stop_id_str(raw) -> Optional[str]:
    s = str(raw or "").strip()
    if not s:
        return None
    if re.fullmatch(r"-?\d+", s):
        return str(int(s))
    m = re.search(r"(\d+)$", s)
    return str(int(m.group(1))) if m else None


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def sha_rk(stop_id, line_id, direction_id, bus_id, datetime_polling: datetime) -> str:
    ts = datetime_polling.strftime("%Y-%m-%dT%H:%M:%S")
    parts = [
        str(stop_id),
        str(line_id),
        "" if direction_id is None else str(direction_id),
        "" if bus_id is None else str(bus_id),
        ts,
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def download_gtfs_zip(url: str, dest: Path, *, attempts: int = 8) -> Path:
    import requests

    url = str(url).strip()
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            if tmp.exists():
                tmp.unlink()
            print(f"Downloading GTFS (attempt {attempt}/{attempts}) ...")
            with requests.get(url, headers=HTTP_HEADERS, stream=True, timeout=1800) as r:
                r.raise_for_status()
                with open(tmp, "wb") as out:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            out.write(chunk)
            if tmp.stat().st_size < 1024:
                raise RuntimeError(f"Downloaded file too small ({tmp.stat().st_size} bytes)")
            tmp.replace(dest)
            print(f"GTFS saved → {dest} ({dest.stat().st_size} bytes)")
            return dest
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"GTFS download failed: {exc!r}")
            if attempt < attempts:
                time.sleep(min(2**attempt, 60))
    raise RuntimeError(f"Failed to download GTFS: {last_err}") from last_err


def resolve_zip_path(gtfs_zip_path: str, gtfs_zip_url: str = "") -> Path:
    path = Path(str(gtfs_zip_path).strip())
    url = str(gtfs_zip_url or "").strip()
    if url:
        download_gtfs_zip(url, path)
    if not path.is_file():
        raise FileNotFoundError(f"GTFS zip not found: {path}")
    return path


def _http_json(method: str, path: str, *, token: str, timeout: int = 60) -> tuple[dict, int]:
    """Prefer pipeline EMT client (retries); fallback to plain requests."""
    try:
        from pipeline.ingestion.emt_client import http_json

        return http_json(
            method,
            path,
            headers={"accessToken": token},
            timeout=timeout,
        )
    except ImportError:
        pass
    import requests

    url = f"{BASE_URL}{path}"
    r = requests.request(
        method,
        url,
        headers={**HTTP_HEADERS, "accessToken": token, "Accept": "application/json"},
        timeout=timeout,
    )
    try:
        body = r.json() if r.content else {}
    except ValueError:
        body = {"raw": r.text[:500]}
    if not isinstance(body, dict):
        body = {"data": body}
    return body, int(r.status_code)


def login_token(client_id: str, pass_key: str) -> str:
    """App credentials only — X-ClientId + passKey (never email/password)."""
    cid = (client_id or "").strip()
    pk = (pass_key or "").strip()
    if not cid or not pk:
        raise ValueError("EMT client_id/pass_key empty")
    if "@" in cid:
        raise ValueError(
            "EMT_CLIENT_ID looks like an email — use MobilityLabs *app* ClientId, "
            "not EMT_EMAIL. Headers must be X-ClientId + passKey."
        )
    print(f"EMT login AUTH=X-ClientId client_id_len={len(cid)} prefix={cid[:8]}…")

    try:
        from pipeline.ingestion.emt_client import login_token as _pipeline_login

        print("EMT login via pipeline.ingestion.emt_client")
        return _pipeline_login(cid, pk)
    except ImportError:
        print("EMT login via rti.lib.bootstrap_seed fallback (pipeline not on path)")

    import requests

    url = f"{BASE_URL}/v1/mobilitylabs/user/login/"
    last_err = None
    for attempt in range(1, 5):
        try:
            r = requests.get(
                url,
                headers={**HTTP_HEADERS, "X-ClientId": cid, "passKey": pk},
                timeout=60,
            )
            body = r.json() if r.content else {}
            if not isinstance(body, dict):
                raise RuntimeError(f"login non-dict: {body!r}")
            code = str(body.get("code", ""))
            if code not in ("00", "01"):
                raise RuntimeError(
                    f"X-ClientId login rejected code={code} desc={body.get('description')!r}"
                )
            token = (body.get("data") or [{}])[0].get("accessToken")
            if not token:
                raise RuntimeError(f"X-ClientId login ok-code but no accessToken: {body}")
            return str(token)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"X-ClientId login failed after retries: {last_err}")


def build_catalogue_seed_rows(
    *,
    client_id: str,
    pass_key: str,
    gtfs_zip_path: str,
    gtfs_zip_url: str = DEFAULT_GTFS_URL,
    geofence_lat: float = GEOFENCE_LAT,
    geofence_lon: float = GEOFENCE_LON,
    geofence_radius_m: float = GEOFENCE_RADIUS_M,
    line_ids_override: str = "",
    access_token: str = "",
) -> list[dict[str, Any]]:
    """Return JSON-ready silver_arrives seed rows (emt_record=silver_arrives_seed)."""
    zip_path = resolve_zip_path(gtfs_zip_path, gtfs_zip_url)
    catalog_date = date.today()
    sol_lat, sol_lon, radius_m = float(geofence_lat), float(geofence_lon), float(geofence_radius_m)

    local_root = Path(tempfile.mkdtemp(prefix="gtfs_"))
    try:
        with zipfile.ZipFile(zip_path.as_posix(), "r") as zf:
            zf.extractall(local_root.as_posix())
        stops_file = next(local_root.rglob("stops.txt"), None)
        if stops_file is None:
            raise FileNotFoundError("stops.txt not found in GTFS zip")
        gtfs_dir = stops_file.parent
        for name in ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt"):
            if not (gtfs_dir / name).is_file():
                raise FileNotFoundError(f"Missing {gtfs_dir / name}")

        stop_attrs: dict[str, dict] = {}
        in_scope_ids: set[str] = set()
        for r in _read_csv_dicts(gtfs_dir / "stops.txt"):
            sid = stop_id_str(r.get("stop_id"))
            if sid is None:
                continue
            try:
                lat = float(str(r.get("stop_lat", "")).strip() or "nan")
                lon = float(str(r.get("stop_lon", "")).strip() or "nan")
            except ValueError:
                lat, lon = float("nan"), float("nan")
            in_scope = lat == lat and lon == lon and haversine_m(sol_lat, sol_lon, lat, lon) <= radius_m
            stop_attrs[sid] = {
                "stop_name": r.get("stop_name") or None,
                "stop_lat": None if lat != lat else lat,
                "stop_lon": None if lon != lon else lon,
            }
            if in_scope:
                in_scope_ids.add(sid)
        print(f"GTFS stops in_scope={len(in_scope_ids)}")
        if not in_scope_ids:
            raise RuntimeError("No in-scope stops — check geofence / GTFS")

        routes = _read_csv_dicts(gtfs_dir / "routes.txt")
        trips = _read_csv_dicts(gtfs_dir / "trips.txt")
        route_label = {
            str(r["route_id"]).strip(): (
                str(r.get("route_short_name") or "").strip() or str(r["route_id"]).strip()
            )
            for r in routes
            if r.get("route_id")
        }
        trip_route = {
            str(r["trip_id"]).strip(): str(r["route_id"]).strip()
            for r in trips
            if r.get("trip_id") and r.get("route_id")
        }
        trip_dir: dict[str, int] = {}
        for r in trips:
            tid = str(r.get("trip_id") or "").strip()
            if not tid:
                continue
            try:
                trip_dir[tid] = int(str(r.get("direction_id") or "0"))
            except ValueError:
                trip_dir[tid] = 0

        candidate_lines: set[str] = set()
        terminus_keys: set[tuple[str, str, int]] = set()
        with (gtfs_dir / "stop_times.txt").open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                sid = stop_id_str(r.get("stop_id"))
                tid = str(r.get("trip_id") or "").strip()
                if sid not in in_scope_ids or tid not in trip_route:
                    continue
                lid = trip_route[tid]
                candidate_lines.add(lid)
                try:
                    seq = int(str(r.get("stop_sequence") or "0"))
                except ValueError:
                    seq = 0
                if seq == 1:
                    terminus_keys.add((sid, lid, trip_dir.get(tid, 0)))
    finally:
        shutil.rmtree(local_root, ignore_errors=True)

    manual = [x.strip() for x in str(line_ids_override or "").split(",") if x.strip()]
    if manual:
        candidate_lines = set(manual)
        print(f"line_ids_override → {sorted(candidate_lines)}")
    else:
        print(f"Candidate line_ids: {len(candidate_lines)}")

    token = (access_token or "").strip() or login_token(client_id, pass_key)
    today = date.today().strftime("%Y%m%d")

    info_payload, _ = _http_json("GET", f"/v2/transport/busemtmad/lines/info/{today}/", token=token)
    line_meta: dict[str, dict] = {}
    if str(info_payload.get("code", "")) == "00":
        for block in info_payload.get("data", []) or []:
            lid = str(block.get("line") or "").strip()
            if lid:
                line_meta[lid] = {
                    "line_label": str(block.get("label") or route_label.get(lid) or lid).strip(),
                    "name_a": block.get("nameA") or block.get("name_a"),
                    "name_b": block.get("nameB") or block.get("name_b"),
                }

    cal_payload, _ = _http_json(
        "GET", f"/v1/transport/busemtmad/calendar/{today}/{today}/", token=token
    )
    day_type = "LA"
    if str(cal_payload.get("code", "")) == "00":
        for block in cal_payload.get("data", []) or []:
            dt = str(block.get("dayType") or block.get("DayType") or "").strip().upper()
            if dt in ("LA", "SA", "FE"):
                day_type = dt
                break

    seed_keys: dict[tuple[str, str, int], dict] = {}
    path_to_dir = {"1": 0, "2": 1}
    now_utc = _utc_now()
    for lid in sorted(candidate_lines):
        for path, direction_id in path_to_dir.items():
            try:
                payload, _status = _http_json(
                    "GET",
                    f"/v1/transport/busemtmad/lines/{lid}/stops/{path}/",
                    token=token,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"  line_stops {lid}/{path}: FAIL {exc}")
                time.sleep(0.3)
                continue
            if str(payload.get("code", "")) != "00":
                print(f"  line_stops {lid}/{path}: api_code={payload.get('code')}")
                time.sleep(0.2)
                continue
            meta = line_meta.get(lid, {})
            label = meta.get("line_label") or route_label.get(lid) or lid
            name_a = meta.get("name_a")
            name_b = meta.get("name_b")
            matched = 0
            raw_stops = 0
            for block in payload.get("data", []) or []:
                stops_list = block.get("stops") or []
                first_sid = stop_id_str(stops_list[0].get("stop")) if stops_list else None
                for st in stops_list:
                    raw_stops += 1
                    sid = stop_id_str(st.get("stop"))
                    if sid is None or sid not in in_scope_ids:
                        continue
                    matched += 1
                    attrs = stop_attrs.get(sid, {})
                    is_term = (sid, lid, direction_id) in terminus_keys or first_sid == sid
                    seed_keys[(sid, lid, direction_id)] = {
                        "line_label": label,
                        "stop_name": attrs.get("stop_name") or st.get("name"),
                        "stop_lat": attrs.get("stop_lat"),
                        "stop_lon": attrs.get("stop_lon"),
                        "direction_text": name_a if direction_id == 0 else name_b,
                        "name_a": name_a,
                        "name_b": name_b,
                        "is_terminus": bool(is_term),
                    }
            print(f"  line_stops {lid}/{path}: ok stops={raw_stops} in_scope_match={matched}")
            time.sleep(0.12)

    if not seed_keys:
        raise RuntimeError(
            "No S1 line-stops seed rows (0 grains after line_stops). "
            "Usually: EMT line_stops timeout/empty, or no stops inside geofence for those lines — "
            "not a login failure (login already succeeded)."
        )

    cat_at = f"{catalog_date.isoformat()}T00:00:00Z"
    now_z = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict[str, Any]] = []
    for (sid, lid, direction_id), meta in sorted(seed_keys.items()):
        rows.append(
            {
                "emt_record": "silver_arrives_seed",
                "_rk": sha_rk(sid, lid, direction_id, None, now_utc),
                "stop_id": sid,
                "line_id": lid,
                "line_label": meta["line_label"],
                "direction_id": direction_id,
                "bus_id": None,
                "destination": None,
                "eta_seconds": None,
                "bus_lat": None,
                "bus_lon": None,
                "datetime_polling": now_z,
                "ingested_at": now_z,
                "stop_name": meta["stop_name"],
                "stop_lat": meta["stop_lat"],
                "stop_lon": meta["stop_lon"],
                "direction_text": meta["direction_text"],
                "name_a": meta["name_a"],
                "name_b": meta["name_b"],
                "is_terminus": bool(meta["is_terminus"]),
                "catalog_loaded_at": cat_at,
                "day_type": day_type,
                "map_ok": True,
            }
        )
    print(f"Built {len(rows)} silver_arrives_seed rows day_type={day_type}")
    return rows


def _parse_eventhub_conn(conn_str: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for bit in (conn_str or "").split(";"):
        bit = bit.strip()
        if not bit or "=" not in bit:
            continue
        k, v = bit.split("=", 1)
        parts[k.strip()] = v.strip()
    endpoint = parts.get("Endpoint", "")
    host = (
        endpoint.replace("sb://", "")
        .replace("https://", "")
        .replace("http://", "")
        .strip()
        .strip("/")
    )
    return {
        "host": host,
        "key_name": parts.get("SharedAccessKeyName", ""),
        "key": parts.get("SharedAccessKey", ""),
        "hub": parts.get("EntityPath", ""),
    }


def _eventhub_sas_token(resource_uri: str, key_name: str, key: str, *, ttl_sec: int = 3600) -> str:
    import base64
    import hashlib
    import hmac
    import time
    import urllib.parse

    expiry = int(time.time()) + int(ttl_sec)
    encoded_uri = urllib.parse.quote_plus(resource_uri.rstrip("/"))
    to_sign = f"{encoded_uri}\n{expiry}".encode("utf-8")
    sig = base64.b64encode(
        hmac.new(key.encode("utf-8"), to_sign, hashlib.sha256).digest()
    ).decode("utf-8")
    return (
        "SharedAccessSignature "
        f"sr={encoded_uri}&sig={urllib.parse.quote_plus(sig)}&se={expiry}&skn={key_name}"
    )


def send_events_to_eventhub(conn_str: str, hub: str, events: list[dict], *, chunk_chars: int = 900_000) -> int:
    """Send JSON events to Eventstream custom endpoint.

    Uses **requests + SAS** only (no azure.eventhub). Fabric notebooks often lack that SDK;
    do not rely on Environment — only stdlib + requests.
    """
    if not events:
        return 0
    if not (conn_str or "").strip():
        raise ValueError("Eventstream connection string empty")
    import json

    import requests

    parsed = _parse_eventhub_conn(conn_str)
    hub_name = (hub or "").strip() or parsed.get("hub") or ""
    if not parsed["host"] or not parsed["key_name"] or not parsed["key"]:
        raise ValueError("Eventstream conn string missing Endpoint / SharedAccessKeyName / SharedAccessKey")
    if not hub_name:
        raise ValueError("Event hub name missing — set arrives_silver_hub or EntityPath in conn string")

    resource_uri = f"https://{parsed['host']}/{hub_name}"
    post_url = f"{resource_uri}/messages"
    token = _eventhub_sas_token(resource_uri, parsed["key_name"], parsed["key"])
    headers_base = {
        "Authorization": token,
        "Content-Type": "application/vnd.microsoft.servicebus.json",
    }

    sent = 0
    batch: list[dict] = []
    size = 0
    for ev in events:
        raw = json.dumps(ev, ensure_ascii=False, default=str)
        # Service Bus JSON batch entry
        entry = {"Body": raw}
        entry_len = len(raw) + 32
        if batch and size + entry_len > chunk_chars:
            resp = requests.post(post_url, headers=headers_base, data=json.dumps(batch), timeout=120)
            if resp.status_code >= 300:
                raise RuntimeError(f"Event Hub send HTTP {resp.status_code}: {resp.text[:300]}")
            sent += len(batch)
            batch, size = [], 0
        batch.append(entry)
        size += entry_len
    if batch:
        resp = requests.post(post_url, headers=headers_base, data=json.dumps(batch), timeout=120)
        if resp.status_code >= 300:
            raise RuntimeError(f"Event Hub send HTTP {resp.status_code}: {resp.text[:300]}")
        sent += len(batch)
    print(f"Event Hub send via requests+SAS ok sent={sent} hub={hub_name}")
    return sent
