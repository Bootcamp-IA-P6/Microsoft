# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "6fc8888d-9aaf-46c0-b6fc-5aace3d34640",
# META       "default_lakehouse_name": "lh_emt_madrid",
# META       "default_lakehouse_workspace_id": "8bfdf6eb-bff5-4647-9484-daa63a5b7ff0",
# META       "known_lakehouses": [
# META         {
# META           "id": "6fc8888d-9aaf-46c0-b6fc-5aace3d34640"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Poll EMT arrives → Eventstream (contract v4.2 bronze)
# Token: login + `tokenSecExpiration` + 401 / auth api_code re-login
# Stops: distinct `stop_id` from `silver_emt` seed (paso in-scope)
# Event fields = `bronze_emt_raw` columns (`payload`, not payload_json)

# CELL ********************

pip install azure-eventhub --quiet

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# PARAMETERS CELL ********************

stop_ids = "4035"  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
poll_interval_sec = 1  # @param {type:"number"}
max_rounds = 30  # @param {type:"number"}
max_retries_per_stop = 2  # @param {type:"number"}
token_skew_sec = 90  # @param {type:"number"}
eventstream_connection_string = ""  # @param {type:"string"}

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

BASE_URL = "https://openapi.emtmadrid.es"
TZ_NOTE = "Europe/Madrid"
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


def resolve_stop_ids(override_csv: str) -> list[str]:
    manual = [s.strip() for s in str(override_csv or "").split(",") if s.strip()]
    if manual:
        print(f"Manual stop_ids ({len(manual)}): {manual}")
        return manual
    if not spark.catalog.tableExists("silver_emt"):
        raise RuntimeError("silver_emt missing — run nb_bootstrap_silver_emt first")
    rows = (
        spark.table("silver_emt")
        .select("stop_id")
        .distinct()
        .orderBy("stop_id")
        .collect()
    )
    ids = [str(r["stop_id"]) for r in rows]
    if not ids:
        raise RuntimeError("silver_emt has no stop_id — re-run bootstrap")
    print(f"Loaded {len(ids)} stop_id(s) from silver_emt")
    return ids


def _http_request(method, path, headers=None, body=None) -> tuple[dict, int]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=body, headers=headers or {}, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401:
            raise TokenExpiredError(f"HTTP 401 on {path}: {raw[:200]}") from exc
        raise RuntimeError(f"HTTP {exc.code} on {path}: {raw[:300]}") from exc


def login(client_id: str, pass_key: str) -> tuple[str, float]:
    last_err = None
    for attempt in range(3):
        try:
            payload, _ = _http_request(
                "GET",
                "/v1/mobilitylabs/user/login/",
                headers={"X-ClientId": client_id, "passKey": pass_key},
            )
            if str(payload.get("code", "")) not in ("00", "01"):
                raise RuntimeError(f"login code={payload.get('code')}: {payload.get('description')}")
            data0 = payload["data"][0]
            token = data0["accessToken"]
            try:
                ttl = float(data0.get("tokenSecExpiration") or 3000)
            except (TypeError, ValueError):
                ttl = 3000.0
            ttl = max(60.0, ttl)
            print(f"EMT login ok — TTL≈{ttl:.0f}s")
            return token, time.time() + ttl
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"login failed: {last_err}")


class EmtTokenSession:
    def __init__(self, client_id: str, pass_key: str, skew_sec: float):
        self.client_id = client_id
        self.pass_key = pass_key
        self.skew_sec = float(skew_sec)
        self.token = None
        self.expires_at = 0.0

    def ensure(self, force: bool = False) -> str:
        if force or not self.token or time.time() >= (self.expires_at - self.skew_sec):
            self.token, self.expires_at = login(self.client_id, self.pass_key)
        return self.token


def fetch_arrives(token: str, stop_id: str) -> tuple[dict, int]:
    payload, status = _http_request(
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


def to_event(stop_id: str, payload: dict, http_status: int) -> dict:
    now = datetime.now(timezone.utc)
    payload_s = json.dumps(payload, ensure_ascii=False)
    return {
        "ingest_id": str(uuid.uuid4()),
        "ingested_at": now.strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{now.microsecond // 1000:03d}Z",
        "source_system": "EMT_OPENAPI",
        "resource_kind": "arrives",
        "resource_key": str(stop_id),
        "http_status": str(http_status),
        "api_code": str(payload.get("code", "")),
        "api_description": payload.get("description"),
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


def poll_one_stop(session, stop_id_str: str, max_retries: int):
    last_err = None
    for attempt in range(int(max_retries) + 1):
        try:
            token = session.ensure()
            payload, status = fetch_arrives(token, stop_id_str)
            if str(payload.get("code", "")) != "00":
                return None, (
                    f"stop {stop_id_str}: api_code={payload.get('code')} "
                    f"({payload.get('description')})"
                )
            ev = to_event(stop_id_str, payload, status)
            print(
                f"  stop {stop_id_str}: code=00 arrivals={count_arrivals(payload)}"
            )
            return ev, None
        except TokenExpiredError as exc:
            last_err = exc
            print(f"  stop {stop_id_str}: token refresh ({exc})")
            session.ensure(force=True)
            time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1 + attempt)
    return None, f"stop {stop_id_str}: FAILED ({last_err})"


def push_events(connection_string: str, events: list[dict]) -> None:
    from azure.eventhub import EventData, EventHubProducerClient

    if not events:
        return
    producer = EventHubProducerClient.from_connection_string(connection_string)
    try:
        batch = producer.create_batch()
        for ev in events:
            data = EventData(json.dumps(ev, ensure_ascii=False))
            try:
                batch.add(data)
            except ValueError:
                producer.send_batch(batch)
                batch = producer.create_batch()
                batch.add(data)
        if len(batch) > 0:
            producer.send_batch(batch)
    finally:
        producer.close()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

client_id, pass_key = load_emt_credentials(variable_library_name)
conn_str = load_eventstream_connection_string(
    variable_library_name, eventstream_connection_string
)
parsed_stop_ids = resolve_stop_ids(stop_ids)
session = EmtTokenSession(client_id, pass_key, token_skew_sec)

est_daily = len(parsed_stop_ids) * 1440
print(f"Stops/round={len(parsed_stop_ids)}  est calls/day≈{est_daily:,}/250000")
print(f"max_rounds={max_rounds} poll_interval_sec={poll_interval_sec}")

round_durations: list[float] = []
for round_idx in range(1, int(max_rounds) + 1):
    t0 = time.time()
    print(f"\n=== Round {round_idx}/{max_rounds} ===")
    events, failures = [], []
    for sid in parsed_stop_ids:
        ev, err = poll_one_stop(session, sid, max_retries_per_stop)
        if ev:
            events.append(ev)
        if err:
            print(f"  {err}")
            failures.append(err)
    if events:
        push_events(conn_str, events)
        print(f"Pushed {len(events)} event(s) → Eventstream")
    else:
        print("No events pushed this round")
    elapsed = time.time() - t0
    round_durations.append(elapsed)
    print(f"Round done in {elapsed:.1f}s success={len(events)} fail={len(failures)}")
    if round_idx >= int(max_rounds):
        break
    sleep_for = float(poll_interval_sec) - elapsed
    if sleep_for > 0:
        print(f"Sleeping {sleep_for:.1f}s")
        time.sleep(sleep_for)
    else:
        print(
            f"WARNING: round {elapsed:.1f}s > poll_interval_sec={poll_interval_sec}"
        )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

if round_durations:
    avg_s = sum(round_durations) / len(round_durations)
    max_s = max(round_durations)
    suggested = max(60.0, max_s + 15.0)
    print(f"avg={avg_s:.1f}s max={max_s:.1f}s → suggested poll_interval_sec≈{suggested:.0f}")
    print("Next: nb_transform_bronze_silver_gold")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
