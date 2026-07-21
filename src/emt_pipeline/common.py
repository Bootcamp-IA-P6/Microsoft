import hashlib
import json
import re
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


BASE_URL = "https://openapi.emtmadrid.es"
TZ_NOTE = "Europe/Madrid"
UTC = timezone.utc
MADRID = ZoneInfo("Europe/Madrid")
ARRIVES_BODY = json.dumps(
    {
        "cultureInfo": "es",
        "Text_StopRequired_YN": "Y",
        "Text_EstimationsRequired_YN": "Y",
        "Text_IncidencesRequired_YN": "N",
    }
).encode("utf-8")
AUTH_API_CODES = frozenset({"80", "81", "82", "83", "89", "90"})


class TokenExpiredError(RuntimeError):
    pass


def utc_now_iso_z() -> str:
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def load_variable_library(library_name: str):
    try:
        import notebookutils

        return notebookutils.variableLibrary.getLibrary(library_name)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Cannot load Variable Library '{library_name}': {exc}") from exc


def lib_get(lib, name: str) -> str:
    if hasattr(lib, "getVariable"):
        try:
            return str(lib.getVariable(name) or "").strip()
        except Exception:  # noqa: BLE001
            pass
    try:
        return str(lib[name] or "").strip()
    except Exception:  # noqa: BLE001
        pass
    return str(getattr(lib, name, None) or "").strip()


def load_emt_credentials(library_name: str) -> tuple[str, str]:
    lib = load_variable_library(library_name)
    client_id = lib_get(lib, "EMT_CLIENT_ID")
    pass_key = lib_get(lib, "EMT_MADRID_PASS_KEY")
    if not client_id or not pass_key:
        raise ValueError("Need EMT_CLIENT_ID and EMT_MADRID_PASS_KEY in Variable Library")
    return client_id, pass_key


def load_eventstream_connection_string(library_name: str, override: str) -> str:
    if str(override or "").strip():
        return str(override).strip()
    lib = load_variable_library(library_name)
    conn = lib_get(lib, "EVENTSTREAM_CONNECTION_STRING") or lib_get(
        lib, "EVENTHUB_CONNECTION_STRING"
    )
    if not conn:
        raise ValueError(
            "Set EVENTSTREAM_CONNECTION_STRING in Variable Library "
            "(Eventstream Custom Endpoint SAS)."
        )
    return conn


def http_json(method: str, path: str, headers=None, body=None, timeout: int = 30) -> tuple[dict, int]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, headers=headers or {}, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            raise TokenExpiredError(f"HTTP 401 on {path}: {raw[:200]}") from exc
        raise RuntimeError(f"HTTP {exc.code} on {path}: {raw[:300]}") from exc


def login_with_ttl(client_id: str, pass_key: str) -> tuple[str, float]:
    last_err = None
    for attempt in range(3):
        try:
            payload, _ = http_json(
                "GET",
                "/v1/mobilitylabs/user/login/",
                headers={"X-ClientId": client_id, "passKey": pass_key},
            )
            if str(payload.get("code", "")) not in ("00", "01"):
                raise RuntimeError(
                    f"login code={payload.get('code')}: {payload.get('description')}"
                )
            data0 = payload["data"][0]
            ttl = float(data0.get("tokenSecExpiration") or 3000)
            return data0["accessToken"], time.time() + max(60.0, ttl)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"login failed: {last_err}")


def login_token(client_id: str, pass_key: str) -> str:
    payload, _ = http_json(
        "GET",
        "/v1/mobilitylabs/user/login/",
        headers={"X-ClientId": client_id, "passKey": pass_key},
        timeout=60,
    )
    if str(payload.get("code", "")) not in ("00", "01"):
        raise RuntimeError(f"login failed: {payload.get('description')}")
    return payload["data"][0]["accessToken"]


class EmtTokenSession:
    def __init__(self, client_id: str, pass_key: str, skew_sec: float):
        self.client_id = client_id
        self.pass_key = pass_key
        self.skew_sec = float(skew_sec)
        self.token = None
        self.expires_at = 0.0

    def ensure(self, force: bool = False) -> str:
        if force or not self.token or time.time() >= (self.expires_at - self.skew_sec):
            self.token, self.expires_at = login_with_ttl(self.client_id, self.pass_key)
            print(
                f"EMT login ok — TTL≈{max(0.0, self.expires_at - time.time()):.0f}s"
            )
        return self.token


def fetch_arrives(token: str, stop_id: str) -> tuple[dict, int]:
    payload, status = http_json(
        "POST",
        f"/v2/transport/busemtmad/stops/{stop_id}/arrives/",
        headers={"accessToken": token, "Content-Type": "application/json"},
        body=ARRIVES_BODY,
    )
    if str(payload.get("code", "")) in AUTH_API_CODES:
        raise TokenExpiredError(
            f"arrives api_code={payload.get('code')} stop={stop_id}"
        )
    return payload, status


def bronze_row(source_system: str, resource_kind: str, resource_key: str, http_status, payload_obj: dict) -> dict:
    payload_s = json.dumps(payload_obj, ensure_ascii=False)
    return {
        "ingest_id": str(uuid.uuid4()),
        "ingested_at": utc_now_iso_z(),
        "source_system": source_system,
        "resource_kind": resource_kind,
        "resource_key": resource_key,
        "http_status": str(http_status),
        "api_code": str(payload_obj.get("code", "")),
        "api_description": payload_obj.get("description"),
        "payload": payload_s,
        "content_sha256": hashlib.sha256(payload_s.encode("utf-8")).hexdigest(),
        "timezone_note": TZ_NOTE,
    }


def count_arrivals(payload: dict) -> int:
    n = 0
    for block in payload.get("data", []) or []:
        arrives = block.get("Arrive") if isinstance(block, dict) else None
        if isinstance(arrives, list):
            n += len(arrives)
    return n


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

