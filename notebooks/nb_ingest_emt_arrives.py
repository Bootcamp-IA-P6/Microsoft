# Fabric notebook source — docs v1.1
#
# How to use (Fabric UI):
#   1. Run nb_create_tables + nb_bootstrap_gtfs_silver first (need in_scope stops)
#   2. Notebook → name: nb_ingest_emt_arrives → attach Lakehouse
#   3. Credentials: Variable Library `var_emt_madrid`
#        EMT_CLIENT_ID , EMT_MADRID_PASS_KEY
#   4. stop_ids: leave EMPTY to poll ALL in_scope stops; or "4035" for smoke test
#   5. Run All once = one poll round
#   6. Continuous (~60 s): Pipeline → Notebook activity every 1 minute
#        then nb_transform_bronze_silver_gold
#
# Contract: docs/01 (in_scope), docs/02 §3–§4, docs/03 §3, docs/04 §5, docs/05

# COMMAND ----------

# MAGIC %md
# MAGIC # Ingest EMT arrives → `bronze_emt_raw`
# MAGIC - Credentials from Variable Library **`var_emt_madrid`**
# MAGIC - Default: poll every `silver_stops_dim.in_scope = true` stop (Sol 600 m)
# MAGIC - Optional `stop_ids` override for smoke tests (comma-separated)
# MAGIC - Empty `Arrive: []` + `code=00` still writes a bronze row
# MAGIC
# MAGIC **Continuous polling:** schedule this notebook every **~60 s** (Fabric Pipeline), then run transform.

# COMMAND ----------

# Leave empty ("") to auto-load all in_scope stops from silver_stops_dim.
# Smoke test example: "4035"
stop_ids = ""  # @param {type:"string"}
variable_library_name = "var_emt_madrid"  # @param {type:"string"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
max_retries_per_stop = 2  # @param {type:"number"}

# COMMAND ----------

import json
import time
import urllib.request
from datetime import datetime, timezone

from pyspark.sql.types import (
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

BASE_URL = "https://openapi.emtmadrid.es"
ARRIVES_BODY = json.dumps(
    {
        "cultureInfo": "es",
        "Text_StopRequired_YN": "Y",
        "Text_EstimationsRequired_YN": "Y",
        "Text_IncidencesRequired_YN": "N",
    }
).encode("utf-8")

BRONZE_SCHEMA = StructType(
    [
        StructField("ingested_at", TimestampType(), True),
        StructField("endpoint", StringType(), True),
        StructField("request_stop_id", IntegerType(), True),
        StructField("api_code", StringType(), True),
        StructField("api_description", StringType(), True),
        StructField("payload_json", StringType(), True),
    ]
)


def load_emt_credentials(library_name: str) -> tuple[str, str]:
    """Read EMT_CLIENT_ID / EMT_MADRID_PASS_KEY from Fabric Variable Library."""
    try:
        import notebookutils  # Fabric runtime

        lib = notebookutils.variableLibrary.getLibrary(library_name)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Cannot load Variable Library '{library_name}'. "
            "Confirm the library exists in this workspace and names match.\n"
            f"Underlying error: {exc}"
        ) from exc

    def _get(name: str) -> str:
        if hasattr(lib, "getVariable"):
            try:
                return str(lib.getVariable(name) or "").strip()
            except Exception:  # noqa: BLE001
                pass
        try:
            return str(lib[name] or "").strip()
        except Exception:  # noqa: BLE001
            pass
        val = getattr(lib, name, None)
        return str(val or "").strip()

    client_id = _get("EMT_CLIENT_ID")
    pass_key = _get("EMT_MADRID_PASS_KEY")
    if not client_id or not pass_key:
        raise ValueError(
            f"Variable Library '{library_name}' must define "
            "EMT_CLIENT_ID and EMT_MADRID_PASS_KEY (non-empty)."
        )
    return client_id, pass_key


def resolve_stop_ids(override_csv: str) -> list[str]:
    """Manual override OR all in_scope stops from silver_stops_dim (docs/01)."""
    manual = [s.strip() for s in str(override_csv or "").split(",") if s.strip()]
    if manual:
        print(f"Using manual stop_ids override ({len(manual)}): {manual}")
        return manual

    if not spark.catalog.tableExists("silver_stops_dim"):
        raise RuntimeError(
            "silver_stops_dim missing. Run nb_bootstrap_gtfs_silver first, "
            "or set stop_ids for a smoke test (e.g. 4035)."
        )

    rows = (
        spark.table("silver_stops_dim")
        .filter("in_scope = true")
        .select("stop_id")
        .orderBy("stop_id")
        .collect()
    )
    ids = [str(r["stop_id"]) for r in rows]
    if not ids:
        raise RuntimeError(
            "No in_scope stops in silver_stops_dim. Re-run GTFS bootstrap / check geofence."
        )
    print(f"Loaded {len(ids)} in_scope stop(s) from silver_stops_dim")
    return ids


def _http_request(
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers or {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login(client_id: str, pass_key: str) -> str:
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            payload = _http_request(
                "GET",
                "/v1/mobilitylabs/user/login/",
                headers={"X-ClientId": client_id, "passKey": pass_key},
            )
            code = str(payload.get("code", ""))
            if code not in ("00", "01"):
                raise RuntimeError(
                    f"EMT login failed (code={code}): {payload.get('description', '')}"
                )
            return payload["data"][0]["accessToken"]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"EMT login failed after retries: {last_err}")


def fetch_arrives(token: str, stop_id: str) -> dict:
    return _http_request(
        "POST",
        f"/v2/transport/busemtmad/stops/{stop_id}/arrives/",
        headers={"accessToken": token, "Content-Type": "application/json"},
        body=ARRIVES_BODY,
    )


def to_bronze_row(stop_id: int, payload: dict) -> dict:
    return {
        "ingested_at": datetime.now(timezone.utc).replace(tzinfo=None),
        "endpoint": "arrives",
        "request_stop_id": stop_id,
        "api_code": str(payload.get("code", "")),
        "api_description": payload.get("description"),
        "payload_json": json.dumps(payload, ensure_ascii=False),
    }


def count_arrivals(payload: dict) -> int:
    n = 0
    for block in payload.get("data", []) or []:
        arrives = block.get("Arrive") if isinstance(block, dict) else None
        if isinstance(arrives, list):
            n += len(arrives)
    return n


client_id, pass_key = load_emt_credentials(variable_library_name)
parsed_stop_ids = resolve_stop_ids(stop_ids)

# Quota sanity (docs: 250k/day; ~1440 rounds/day at 60s)
est_daily = len(parsed_stop_ids) * 1440
print(f"Polling {len(parsed_stop_ids)} stop(s) this round")
print(f"Approx calls/day at 60s cadence (stops only, excl. login): ~{est_daily:,} / 250,000")
if est_daily > 200_000:
    print("WARNING: close to daily quota — consider fewer stops or longer interval")

token = login(client_id, pass_key)

rows: list[dict] = []
failures: list[str] = []
t0 = time.time()

for stop_id_str in parsed_stop_ids:
    stop_id_int = int(stop_id_str)
    payload = None
    last_err: Exception | None = None
    for attempt in range(int(max_retries_per_stop) + 1):
        try:
            payload = fetch_arrives(token, stop_id_str)
            break
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1 + attempt)

    if payload is None:
        msg = f"stop {stop_id_str}: FAILED transport ({last_err})"
        print(f"  {msg}")
        failures.append(msg)
        continue

    api_code = str(payload.get("code", ""))
    if api_code != "00":
        msg = f"stop {stop_id_str}: FAILED api_code={api_code} ({payload.get('description')})"
        print(f"  {msg}")
        failures.append(msg)
        continue

    rows.append(to_bronze_row(stop_id_int, payload))
    print(f"  stop {stop_id_str}: code={api_code} arrivals={count_arrivals(payload)}")

elapsed = time.time() - t0
print(f"Round finished in {elapsed:.1f}s — success={len(rows)} fail={len(failures)}")

# COMMAND ----------

if not rows:
    raise RuntimeError(
        "No successful polls to write.\n" + ("\n".join(failures) or "(none)")
    )

df = spark.createDataFrame(rows, schema=BRONZE_SCHEMA)
df.write.format("delta").mode("append").saveAsTable(bronze_table)

print(f"Appended {len(rows)} row(s) → {bronze_table}")
for f in failures:
    print(f"  fail: {f}")

display(spark.table(bronze_table).orderBy("ingested_at", ascending=False).limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick check — sample stop from this round

# COMMAND ----------

import json as _json

check_stop = int(parsed_stop_ids[0])
latest = (
    spark.table(bronze_table)
    .filter(f"request_stop_id = {check_stop}")
    .orderBy("ingested_at", ascending=False)
    .limit(1)
    .collect()
)
if not latest:
    print(f"No bronze data for stop {check_stop}")
else:
    payload = _json.loads(latest[0]["payload_json"])
    print(f"Stop {check_stop}:")
    n = 0
    for block in payload.get("data", []) or []:
        for arr in block.get("Arrive", []) or []:
            eta_s = arr.get("estimateArrive")
            try:
                eta_min = f"{int(eta_s) // 60} min"
            except (TypeError, ValueError):
                eta_min = "?"
            print(
                f"  · {arr.get('line')} bus {arr.get('bus')} "
                f"→ {str(arr.get('destination', '')).strip()} · ~{eta_min}"
            )
            n += 1
    if n == 0:
        print("  (empty Arrive — valid snapshot)")
