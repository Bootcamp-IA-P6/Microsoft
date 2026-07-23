# Fabric notebook — contract v4.3 poll + transform (arrives Pipeline step, paste-only)
#
# Prereq: create/migrate + bootstrap → silver_arrives
# If ImportError: run once → %pip install requests
# Pipeline: nb_poll_and_transform only (alerts = nb_alerts_silver_gold)
# Guide: docs/manual-lakehouse-ingestion.md

# COMMAND ----------

# MAGIC %md
# MAGIC # Poll arrives → bronze → silver_arrives → gold ETA/freq (contract v4.3)
# MAGIC Does **not** update Gold `alert_*` — that is `nb_alerts_silver_gold`.

# COMMAND ----------

stop_ids = ""  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
max_retries_per_stop = 2  # @param {type:"number"}
token_skew_sec = 90  # @param {type:"number"}
stale_after_sec = 900  # @param {type:"number"}
incremental = True  # @param {type:"boolean"}
freq_min_samples = 20  # @param {type:"number"}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Shared helpers (inlined)

# COMMAND ----------

import hashlib
import json
import re
import time
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
HTTP_HEADERS_BASE = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; emt-pipeline/0.1; "
        "+https://github.com/Bootcamp-IA-P6/Microsoft)"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Connection": "close",
}


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


def _is_transient_http_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if "unexpected_eof" in msg or "ssl" in msg or "connection" in msg or "timed out" in msg:
        return True
    try:
        import requests

        return isinstance(
            exc,
            (
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ),
        )
    except ImportError:
        return False


def http_json(
    method: str,
    path: str,
    headers=None,
    body=None,
    timeout: int = 30,
    *,
    attempts: int = 5,
) -> tuple[dict, int]:
    """EMT OpenAPI JSON call with retries — Fabric urllib often hits SSL EOF."""
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "requests is required — run once: %pip install requests"
        ) from exc

    url = f"{BASE_URL}{path}"
    hdrs = {**HTTP_HEADERS_BASE, **(headers or {})}
    last_err: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            resp = requests.request(
                method=method.upper(),
                url=url,
                headers=hdrs,
                data=body,
                timeout=timeout,
                allow_redirects=True,
            )
            raw = resp.text
            if resp.status_code == 401:
                raise TokenExpiredError(f"HTTP 401 on {path}: {raw[:200]}")
            if resp.status_code in {408, 425, 429, 500, 502, 503, 504}:
                raise RuntimeError(f"HTTP {resp.status_code} on {path}: {raw[:300]}")
            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code} on {path}: {raw[:300]}")
            try:
                payload = resp.json()
            except ValueError as exc:
                raise RuntimeError(f"Non-JSON on {path}: {raw[:300]}") from exc
            if not isinstance(payload, dict):
                raise RuntimeError(f"Unexpected JSON type on {path}: {type(payload)}")
            return payload, int(resp.status_code)
        except TokenExpiredError:
            raise
        except RuntimeError as exc:
            last_err = exc
            # Non-retryable client errors (except the transient set raised above)
            m = re.match(r"HTTP (\d+)", str(exc))
            if m:
                code = int(m.group(1))
                if code >= 400 and code not in {408, 425, 429, 500, 502, 503, 504}:
                    raise
            if attempt < attempts:
                sleep_s = min(2**attempt, 20)
                print(
                    f"HTTP {method.upper()} {path} failed "
                    f"(attempt {attempt}/{attempts}): {exc!r}; retry in {sleep_s}s"
                )
                time.sleep(sleep_s)
                continue
            break
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < attempts and _is_transient_http_error(exc):
                sleep_s = min(2**attempt, 20)
                print(
                    f"HTTP {method.upper()} {path} failed "
                    f"(attempt {attempt}/{attempts}): {exc!r}; retry in {sleep_s}s"
                )
                time.sleep(sleep_s)
                continue
            if attempt < attempts:
                sleep_s = min(2**attempt, 20)
                print(
                    f"HTTP {method.upper()} {path} failed "
                    f"(attempt {attempt}/{attempts}): {exc!r}; retry in {sleep_s}s"
                )
                time.sleep(sleep_s)
                continue
            break

    raise RuntimeError(
        f"HTTP {method.upper()} {path} failed after {attempts} attempts: {last_err}"
    ) from last_err


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



# COMMAND ----------

from pyspark.sql import functions as F


def resolve_stop_ids(spark, override_csv: str) -> list[str]:
    manual = [s.strip() for s in str(override_csv or "").split(",") if s.strip()]
    if manual:
        print(f"Manual stop_ids ({len(manual)}): {manual}")
        return manual
    if not spark.catalog.tableExists("silver_arrives"):
        raise RuntimeError("silver_arrives missing — run nb_bootstrap_gtfs_silver first")
    rows = (
        spark.table("silver_arrives")
        .select("stop_id")
        .distinct()
        .orderBy("stop_id")
        .collect()
    )
    ids = [str(r["stop_id"]) for r in rows]
    if not ids:
        raise RuntimeError("silver_arrives has no stop_id — re-run bootstrap")
    print(f"Loaded {len(ids)} stop_id(s) from silver_arrives")
    return ids


def latest_catalog_rows(spark):
    from pyspark.sql import Window

    catalog = (
        spark.table("silver_arrives")
        .filter("bus_id IS NULL AND map_ok = true AND direction_id IS NOT NULL")
        .select(
            "stop_id",
            "line_id",
            "line_label",
            "direction_id",
            "stop_name",
            "stop_lat",
            "stop_lon",
            "direction_text",
            "name_a",
            "name_b",
            "is_terminus",
            "catalog_loaded_at",
            "day_type",
        )
    )
    return (
        catalog.withColumn(
            "_rn",
            F.row_number().over(
                Window.partitionBy("stop_id", "line_id", "direction_id").orderBy(
                    F.col("catalog_loaded_at").desc_nulls_last()
                )
            ),
        )
        .filter("_rn = 1")
        .drop("_rn")
        .collect()
    )



# COMMAND ----------

# MAGIC %md
# MAGIC ## A — Direct ingest → bronze_emt_raw

# COMMAND ----------

import time

from pyspark.sql.types import StringType, StructField, StructType



BRONZE_SCHEMA = StructType(
    [
        StructField(c, StringType(), True)
        for c in [
            "ingest_id",
            "ingested_at",
            "source_system",
            "resource_kind",
            "resource_key",
            "http_status",
            "api_code",
            "api_description",
            "payload",
            "content_sha256",
            "timezone_note",
        ]
    ]
)


def run_direct_ingest(
    spark,
    *,
    stop_ids: str,
    variable_library_name: str,
    bronze_table: str,
    max_retries_per_stop: int,
    token_skew_sec: int,
) -> None:
    client_id, pass_key = load_emt_credentials(variable_library_name)
    parsed = resolve_stop_ids(spark, stop_ids)
    session = EmtTokenSession(client_id, pass_key, token_skew_sec)
    print(f"Polling {len(parsed)} stop(s) → {bronze_table}")

    rows, failures = [], []
    t0 = time.time()
    for sid in parsed:
        payload = None
        status = None
        last_err = None
        for attempt in range(int(max_retries_per_stop) + 1):
            try:
                token = session.ensure()
                payload, status = fetch_arrives(token, sid)
                break
            except TokenExpiredError as exc:
                last_err = exc
                session.ensure(force=True)
                time.sleep(0.5)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(1 + attempt)
        if payload is None:
            failures.append(f"stop {sid}: {last_err}")
            continue
        if str(payload.get("code", "")) != "00":
            failures.append(f"stop {sid}: api_code={payload.get('code')}")
            continue
        rows.append(bronze_row("EMT_OPENAPI", "arrives", str(sid), status or 200, payload))
        print(f"  stop {sid}: ok")

    print(f"Round {time.time() - t0:.1f}s success={len(rows)} fail={len(failures)}")
    if not rows:
        raise RuntimeError("No rows\n" + "\n".join(failures))

    spark.createDataFrame(rows, schema=BRONZE_SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(bronze_table)
    print(f"Appended {len(rows)} → {bronze_table}")
    for f in failures:
        print(f"  fail: {f}")
    display(spark.table(bronze_table).orderBy("ingested_at", ascending=False).limit(10))



run_direct_ingest(
    spark,
    stop_ids=stop_ids,
    variable_library_name=variable_library_name,
    bronze_table=bronze_table,
    max_retries_per_stop=max_retries_per_stop,
    token_skew_sec=token_skew_sec,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## B — Transform → silver_arrives + gold_emt_stop_line

# COMMAND ----------

import json
import statistics
from datetime import datetime

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)



SILVER_SCHEMA = StructType(
    [
        StructField("_rk", StringType(), False),
        StructField("stop_id", StringType(), False),
        StructField("line_id", StringType(), False),
        StructField("line_label", StringType(), False),
        StructField("direction_id", IntegerType(), True),
        StructField("bus_id", StringType(), True),
        StructField("destination", StringType(), True),
        StructField("eta_seconds", IntegerType(), True),
        StructField("datetime_polling", TimestampType(), False),
        StructField("ingested_at", TimestampType(), False),
        StructField("stop_name", StringType(), True),
        StructField("stop_lat", DoubleType(), True),
        StructField("stop_lon", DoubleType(), True),
        StructField("direction_text", StringType(), True),
        StructField("name_a", StringType(), True),
        StructField("name_b", StringType(), True),
        StructField("is_terminus", BooleanType(), True),
        StructField("catalog_loaded_at", DateType(), True),
        StructField("day_type", StringType(), True),
        StructField("map_ok", BooleanType(), True),
    ]
)

# Arrives stage only — alert_* owned by nb_alerts_silver_gold
GOLD_ARRIVES_SCHEMA = StructType(
    [
        StructField("stop_id", StringType(), False),
        StructField("line_id", StringType(), False),
        StructField("direction_id", IntegerType(), False),
        StructField("line_label", StringType(), False),
        StructField("stop_name", StringType(), False),
        StructField("direction_text", StringType(), True),
        StructField("name_a", StringType(), True),
        StructField("name_b", StringType(), True),
        StructField("destination", StringType(), True),
        StructField("eta_seconds_1", IntegerType(), True),
        StructField("bus_id_1", StringType(), True),
        StructField("eta_seconds_2", IntegerType(), True),
        StructField("bus_id_2", StringType(), True),
        StructField("has_upcoming_bus", BooleanType(), False),
        StructField("is_stale", BooleanType(), False),
        StructField("origin_stop_notice", BooleanType(), False),
        StructField("is_terminus", BooleanType(), False),
        StructField("catalog_loaded_at", DateType(), False),
        StructField("day_type", StringType(), False),
        StructField("updated_at", TimestampType(), False),
        StructField("freq_observed_weekday_min", DoubleType(), True),
        StructField("freq_observed_weekend_min", DoubleType(), True),
        StructField("freq_sample_size_weekday", IntegerType(), True),
        StructField("freq_sample_size_weekend", IntegerType(), True),
    ]
)


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


def delta_sql_retry(spark, sql: str, *, label: str, attempts: int = 6) -> None:
    """Retry Delta MERGE/DELETE on ConcurrentAppendException (arrives+alerts share gold)."""
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            spark.sql(sql)
            if attempt > 1:
                print(f"{label}: succeeded on attempt {attempt}/{attempts}")
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            name = type(exc).__name__
            msg = str(exc)
            concurrent = (
                "ConcurrentAppendException" in name
                or "ConcurrentAppendException" in msg
                or "DELTA_CONCURRENT_APPEND" in msg
                or "ConcurrentTransactionException" in msg
            )
            if not concurrent or attempt >= attempts:
                raise
            sleep_s = min(2**attempt, 30)
            print(
                f"{label}: concurrent Delta write "
                f"(attempt {attempt}/{attempts}); retry in {sleep_s}s"
            )
            time.sleep(sleep_s)
    raise RuntimeError(f"{label}: exhausted retries") from last


def median_gaps_minutes(timestamps: list[datetime]) -> tuple[float | None, int]:
    uniq = sorted(set(timestamps))
    n = len(uniq)
    if n < 2:
        return None, n
    gaps = [(uniq[i] - uniq[i - 1]).total_seconds() / 60.0 for i in range(1, n)]
    gaps = [g for g in gaps if g > 0]
    if not gaps:
        return None, n
    return float(statistics.median(gaps)), n


def run_transform(spark, *, stale_after_sec: int, bronze_table: str, incremental: bool, freq_min_samples: int) -> None:
    stale_after_sec = int(stale_after_sec)
    freq_min = int(freq_min_samples)

    if not spark.catalog.tableExists("silver_arrives"):
        raise RuntimeError("silver_arrives missing — run nb_bootstrap_gtfs_silver")

    cat_rows = latest_catalog_rows(spark)
    cat_by_grain = {(r["stop_id"], r["line_id"], int(r["direction_id"])): r for r in cat_rows}
    label_at_stop: dict[tuple[str, str], str] = {}
    line_names: dict[str, tuple[str | None, str | None]] = {}
    for r in cat_rows:
        label_at_stop[(r["stop_id"], r["line_label"])] = r["line_id"]
        line_names[r["line_id"]] = (r["name_a"], r["name_b"])
    day_type_today = next((r["day_type"] for r in cat_rows if r["day_type"]), "LA")
    print(f"Catalogue grains={len(cat_by_grain)} day_type={day_type_today}")

    bronze = (
        spark.table(bronze_table)
        .withColumn("ingested_at_ts", F.to_timestamp(F.col("ingested_at")))
        .filter("resource_kind = 'arrives' AND api_code = '00'")
    )
    if incremental:
        max_poll = (
            spark.table("silver_arrives")
            .filter("bus_id IS NOT NULL OR eta_seconds IS NOT NULL")
            .agg(F.max("ingested_at"))
            .collect()[0][0]
        )
        max_any = spark.table("silver_arrives").agg(F.max("ingested_at")).collect()[0][0]
        cutoff = max_poll or max_any
        if cutoff is not None:
            bronze = bronze.filter(F.col("ingested_at_ts") > F.lit(cutoff))
            print(f"Incremental bronze ingested_at > {cutoff}")

    bronze_list = bronze.orderBy("ingested_at_ts").collect()
    print(f"Bronze arrives rows to process: {len(bronze_list)}")

    candidates: list[dict] = []
    quarantine: list[str] = []

    for br in bronze_list:
        try:
            payload = json.loads(br["payload"])
        except (TypeError, json.JSONDecodeError) as exc:
            quarantine.append(f"bad JSON key={br['resource_key']}: {exc}")
            continue

        dt_poll = parse_api_datetime_to_utc_naive(payload.get("datetime"))
        ingested_at_ts = br["ingested_at_ts"]
        if dt_poll is None:
            dt_poll = (
                ingested_at_ts.replace(microsecond=0)
                if ingested_at_ts
                else datetime.now(UTC).replace(tzinfo=None, microsecond=0)
            )
        stop_key = str(br["resource_key"])
        ingested_at = ingested_at_ts

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
                    quarantine.append(f"missing label stop={stop_key}")
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
                    quarantine.append(f"map_ok=false stop={sid} label={line_label}")
                name_a = name_b = None
                if map_ok:
                    name_a, name_b = line_names.get(line_id, (None, None))
                direction_id = map_destination_to_direction(destination, name_a, name_b)
                denorm = None
                if map_ok and direction_id is not None:
                    denorm = cat_by_grain.get((sid, line_id, direction_id))
                if denorm is None and map_ok:
                    for (s, l, _d), row in cat_by_grain.items():
                        if s == sid and l == line_id:
                            denorm = row
                            break
                if direction_id is None:
                    quarantine.append(
                        f"no direction match stop={sid} label={line_label} dest={destination}"
                    )
                    map_ok = False
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
                        "datetime_polling": dt_poll,
                        "ingested_at": ingested_at,
                        "stop_name": denorm["stop_name"] if denorm else None,
                        "stop_lat": denorm["stop_lat"] if denorm else None,
                        "stop_lon": denorm["stop_lon"] if denorm else None,
                        "direction_text": denorm["direction_text"] if denorm else None,
                        "name_a": name_a if name_a is not None else (denorm["name_a"] if denorm else None),
                        "name_b": name_b if name_b is not None else (denorm["name_b"] if denorm else None),
                        "is_terminus": denorm["is_terminus"] if denorm else False,
                        "catalog_loaded_at": denorm["catalog_loaded_at"] if denorm else None,
                        "day_type": (denorm["day_type"] if denorm else None) or day_type_today,
                        "map_ok": bool(map_ok and direction_id is not None),
                    }
                )

        if not arrives_found:
            for (s, l, d), row in cat_by_grain.items():
                if s != stop_key:
                    continue
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
                        "datetime_polling": dt_poll,
                        "ingested_at": ingested_at,
                        "stop_name": row["stop_name"],
                        "stop_lat": row["stop_lat"],
                        "stop_lon": row["stop_lon"],
                        "direction_text": row["direction_text"],
                        "name_a": row["name_a"],
                        "name_b": row["name_b"],
                        "is_terminus": row["is_terminus"],
                        "catalog_loaded_at": row["catalog_loaded_at"],
                        "day_type": row["day_type"] or day_type_today,
                        "map_ok": True,
                    }
                )

    print(f"Candidates={len(candidates)} quarantine={len(quarantine)}")
    for q in quarantine[:30]:
        print(f"  Q: {q}")

    inserted = 0
    if candidates:
        cand_df = spark.createDataFrame(candidates, schema=SILVER_SCHEMA).dropDuplicates(["_rk"])
        existing = spark.table("silver_arrives").select("_rk")
        new_df = cand_df.join(existing, on="_rk", how="left_anti")
        inserted = new_df.count()
        if inserted:
            new_df.write.format("delta").mode("append").saveAsTable("silver_arrives")
    print(f"Inserted silver poll rows: {inserted}")
    print(f"silver_arrives total: {spark.table('silver_arrives').count()}")

    polls = (
        spark.table("silver_arrives")
        .filter("bus_id IS NOT NULL AND map_ok = true")
        .select("line_id", "bus_id", "datetime_polling", "day_type")
        .collect()
    )
    seen = set()
    by_line_window: dict[tuple[str, str], list[datetime]] = {}
    for p in polls:
        key = (p["line_id"], p["bus_id"], p["datetime_polling"])
        if key in seen:
            continue
        seen.add(key)
        if p["day_type"] not in ("LA", "SA", "FE"):
            continue
        window = "weekday" if p["day_type"] == "LA" else "weekend"
        by_line_window.setdefault((p["line_id"], window), []).append(p["datetime_polling"])

    freq_by_line: dict[str, dict] = {}
    for (lid, window), ts_list in by_line_window.items():
        med, n = median_gaps_minutes(ts_list)
        slot = freq_by_line.setdefault(
            lid,
            {
                "freq_observed_weekday_min": None,
                "freq_observed_weekend_min": None,
                "freq_sample_size_weekday": 0,
                "freq_sample_size_weekend": 0,
            },
        )
        if window == "weekday":
            slot["freq_sample_size_weekday"] = n
            slot["freq_observed_weekday_min"] = med if n >= freq_min else None
        else:
            slot["freq_sample_size_weekend"] = n
            slot["freq_observed_weekend_min"] = med if n >= freq_min else None

    now_utc = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    latest_polls = (
        spark.table("silver_arrives")
        .filter("map_ok = true AND direction_id IS NOT NULL")
        .withColumn(
            "_rn",
            F.row_number().over(
                Window.partitionBy("stop_id", "line_id", "direction_id").orderBy(
                    F.col("datetime_polling").desc()
                )
            ),
        )
        .filter("_rn = 1")
        .drop("_rn")
    )
    poll_ts_per_grain = {
        (r["stop_id"], r["line_id"], int(r["direction_id"])): r["datetime_polling"]
        for r in latest_polls.collect()
    }
    silver_all = (
        spark.table("silver_arrives")
        .filter("map_ok = true AND direction_id IS NOT NULL")
        .collect()
    )
    buses_at: dict[tuple, list] = {}
    for r in silver_all:
        g = (r["stop_id"], r["line_id"], int(r["direction_id"]))
        ts = poll_ts_per_grain.get(g)
        if ts is None or r["datetime_polling"] != ts:
            continue
        if r["bus_id"] is None and r["eta_seconds"] is None:
            buses_at.setdefault(g, [])
            continue
        buses_at.setdefault(g, []).append(r)

    gold_rows = []
    for (sid, lid, did), cat in cat_by_grain.items():
        g = (sid, lid, did)
        buses = sorted(
            # Spark Row has no .get(); use key access
            [b for b in buses_at.get(g, []) if b["eta_seconds"] is not None],
            key=lambda b: b["eta_seconds"],
        )
        updated_at = poll_ts_per_grain.get(g) or now_utc
        eta1 = buses[0]["eta_seconds"] if len(buses) > 0 else None
        bus1 = buses[0]["bus_id"] if len(buses) > 0 else None
        dest = buses[0]["destination"] if len(buses) > 0 else None
        eta2 = buses[1]["eta_seconds"] if len(buses) > 1 else None
        bus2 = buses[1]["bus_id"] if len(buses) > 1 else None
        is_terminus = bool(cat["is_terminus"])
        has_bus = eta1 is not None
        is_stale = (now_utc - updated_at).total_seconds() > stale_after_sec
        origin_notice = bool(is_terminus and eta1 is None)
        freq = freq_by_line.get(
            lid,
            {
                "freq_observed_weekday_min": None,
                "freq_observed_weekend_min": None,
                "freq_sample_size_weekday": 0,
                "freq_sample_size_weekend": 0,
            },
        )
        gold_rows.append(
            {
                "stop_id": sid,
                "line_id": lid,
                "direction_id": did,
                "line_label": cat["line_label"],
                "stop_name": cat["stop_name"] or sid,
                "direction_text": cat["direction_text"],
                "name_a": cat["name_a"],
                "name_b": cat["name_b"],
                "destination": dest,
                "eta_seconds_1": eta1,
                "bus_id_1": bus1,
                "eta_seconds_2": eta2,
                "bus_id_2": bus2,
                "has_upcoming_bus": has_bus,
                "is_stale": bool(is_stale),
                "origin_stop_notice": origin_notice,
                "is_terminus": is_terminus,
                "catalog_loaded_at": cat["catalog_loaded_at"],
                "day_type": cat["day_type"] or day_type_today,
                "updated_at": updated_at,
                "freq_observed_weekday_min": freq["freq_observed_weekday_min"],
                "freq_observed_weekend_min": freq["freq_observed_weekend_min"],
                "freq_sample_size_weekday": int(freq["freq_sample_size_weekday"] or 0),
                "freq_sample_size_weekend": int(freq["freq_sample_size_weekend"] or 0),
            }
        )

    if not gold_rows:
        print("No gold rows — catalogue empty?")
    else:
        gold_df = spark.createDataFrame(gold_rows, schema=GOLD_ARRIVES_SCHEMA)
        gold_df.createOrReplaceTempView("gold_arrives_stage")
        # MATCHED: ETA/freq/stale only — never touch alert_*
        # NOT MATCHED: new grains get alert_* = inactive defaults
        delta_sql_retry(
            spark,
            """
            MERGE INTO gold_emt_stop_line AS t
            USING gold_arrives_stage AS s
            ON t.stop_id = s.stop_id
               AND t.line_id = s.line_id
               AND t.direction_id = s.direction_id
            WHEN MATCHED THEN UPDATE SET
              t.line_label = s.line_label,
              t.stop_name = s.stop_name,
              t.direction_text = s.direction_text,
              t.name_a = s.name_a,
              t.name_b = s.name_b,
              t.destination = s.destination,
              t.eta_seconds_1 = s.eta_seconds_1,
              t.bus_id_1 = s.bus_id_1,
              t.eta_seconds_2 = s.eta_seconds_2,
              t.bus_id_2 = s.bus_id_2,
              t.has_upcoming_bus = s.has_upcoming_bus,
              t.is_stale = s.is_stale,
              t.origin_stop_notice = s.origin_stop_notice,
              t.is_terminus = s.is_terminus,
              t.catalog_loaded_at = s.catalog_loaded_at,
              t.day_type = s.day_type,
              t.updated_at = s.updated_at,
              t.freq_observed_weekday_min = s.freq_observed_weekday_min,
              t.freq_observed_weekend_min = s.freq_observed_weekend_min,
              t.freq_sample_size_weekday = s.freq_sample_size_weekday,
              t.freq_sample_size_weekend = s.freq_sample_size_weekend
            WHEN NOT MATCHED THEN INSERT (
              stop_id, line_id, direction_id, line_label, stop_name,
              direction_text, name_a, name_b, destination,
              eta_seconds_1, bus_id_1, eta_seconds_2, bus_id_2,
              has_upcoming_bus, is_stale, origin_stop_notice, is_terminus,
              catalog_loaded_at, day_type, updated_at,
              freq_observed_weekday_min, freq_observed_weekend_min,
              freq_sample_size_weekday, freq_sample_size_weekend,
              alert_active, alert_header, alert_cause, alert_effect, alert_url
            ) VALUES (
              s.stop_id, s.line_id, s.direction_id, s.line_label, s.stop_name,
              s.direction_text, s.name_a, s.name_b, s.destination,
              s.eta_seconds_1, s.bus_id_1, s.eta_seconds_2, s.bus_id_2,
              s.has_upcoming_bus, s.is_stale, s.origin_stop_notice, s.is_terminus,
              s.catalog_loaded_at, s.day_type, s.updated_at,
              s.freq_observed_weekday_min, s.freq_observed_weekend_min,
              s.freq_sample_size_weekday, s.freq_sample_size_weekend,
              false, NULL, NULL, NULL, NULL
            )
            """,
            label="gold arrives MERGE",
        )
        print(f"MERGE gold_emt_stop_line (arrives cols only) staged={len(gold_rows)}")
        display(
            spark.table("gold_emt_stop_line")
            .orderBy("stop_id", "line_id", "direction_id")
            .limit(40)
        )

    print("=== SUMMARY (contract v4.3 arrives) ===")
    print(f"stale_after_sec={stale_after_sec} silver_inserted={inserted}")
    print(f"bronze={spark.table(bronze_table).count()}")
    print(f"silver_arrives={spark.table('silver_arrives').count()}")
    print(f"gold_emt_stop_line={spark.table('gold_emt_stop_line').count()}")
    dup = spark.table("silver_arrives").groupBy("_rk").count().filter("count > 1").count()
    print(f"duplicate _rk={dup} (must be 0)")



run_transform(
    spark,
    stale_after_sec=int(stale_after_sec),
    bronze_table=bronze_table,
    incremental=bool(incremental),
    freq_min_samples=int(freq_min_samples),
)
