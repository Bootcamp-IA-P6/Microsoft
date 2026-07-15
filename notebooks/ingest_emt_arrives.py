# Fabric notebook source
#
# How to use (Fabric UI — not local):
#   1. app.fabric.microsoft.com → Workspace → New item → Notebook
#   2. Name: ingest_emt_arrives
#   3. Attach your Lakehouse (Lakehouse explorer → Add → default lakehouse)
#   4. Copy each "# COMMAND ----------" block into a separate cell (or Import .py)
#   5. Fill parameters (or wire them from a Pipeline later)
#   6. Run All
#
# Repo copy: version control only. Fabric does not auto-run files from GitHub
# unless the workspace has Git integration enabled (see docs in README).

# COMMAND ----------

# MAGIC %md
# MAGIC # Ingest EMT `arrives` → bronze
# MAGIC Polls `POST /v2/transport/busemtmad/stops/{stopId}/arrives/` and appends raw rows to `bronze_emt_arrives`.
# MAGIC
# MAGIC **Prereqs:** Lakehouse attached · EMT app credentials from mobilitylabs.emtmadrid.es

# COMMAND ----------

# Parameters — set values in Fabric UI (notebook toolbar) or pass from Pipeline
stop_ids = "4035"  # @param {type:"string"}
emt_client_id = ""  # @param {type:"string"}
emt_pass_key = ""  # @param {type:"string"}
bronze_table = "bronze_emt_arrives"  # @param {type:"string"}

# COMMAND ----------

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://openapi.emtmadrid.es"
ARRIVES_BODY = json.dumps(
    {
        "cultureInfo": "es",
        "Text_StopRequired_YN": "Y",
        "Text_EstimationsRequired_YN": "Y",
        "Text_LineInfoRequired_YN": "Y",
        "Text_IncidencesRequired_YN": "Y",
    }
).encode("utf-8")


def _http_request(method: str, path: str, headers: dict[str, str] | None = None, body: bytes | None = None) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers=headers or {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login(client_id: str, pass_key: str) -> str:
    payload = _http_request(
        "GET",
        "/v1/mobilitylabs/user/login/",
        headers={"X-ClientId": client_id, "passKey": pass_key},
    )
    code = payload.get("code", "")
    if code not in ("00", "01"):
        raise RuntimeError(f"EMT login failed (code={code}): {payload.get('description', '')}")
    return payload["data"][0]["accessToken"]


def fetch_arrives(token: str, stop_id: str) -> dict:
    return _http_request(
        "POST",
        f"/v2/transport/busemtmad/stops/{stop_id}/arrives/",
        headers={
            "accessToken": token,
            "Content-Type": "application/json",
        },
        body=ARRIVES_BODY,
    )


def to_bronze_row(stop_id: str, payload: dict) -> dict:
    ingested_at = datetime.now(timezone.utc).isoformat()
    return {
        "ingested_at": ingested_at,
        "endpoint": "arrives",
        "request_stop_id": stop_id,
        "request_line_id": None,
        "api_datetime": payload.get("datetime"),
        "api_code": payload.get("code", ""),
        "api_description": payload.get("description"),
        "payload_json": json.dumps(payload, ensure_ascii=False),
    }


client_id = (emt_client_id or "").strip()
pass_key = (emt_pass_key or "").strip()
if not client_id or not pass_key:
    raise ValueError("Set emt_client_id and emt_pass_key parameters in Fabric (or pass from Pipeline).")

parsed_stop_ids = [s.strip() for s in stop_ids.split(",") if s.strip()]
if not parsed_stop_ids:
    raise ValueError("stop_ids must contain at least one stop id, e.g. 4035")

print(f"Polling {len(parsed_stop_ids)} stop(s): {parsed_stop_ids}")

token = login(client_id, pass_key)
rows = []
for stop_id in parsed_stop_ids:
    payload = fetch_arrives(token, stop_id)
    rows.append(to_bronze_row(stop_id, payload))
    arrive_count = 0
    for block in payload.get("data", []):
        if isinstance(block.get("Arrive"), list):
            arrive_count += len(block["Arrive"])
    print(f"  stop {stop_id}: code={payload.get('code')} arrivals={arrive_count}")

# COMMAND ----------

# Write to Lakehouse (requires default Lakehouse attached in notebook)
from pyspark.sql.types import StringType, StructField, StructType

if not rows:
    raise RuntimeError("No rows to write.")

# Explicit schema — Spark cannot infer types when columns are all None (e.g. request_line_id).
bronze_schema = StructType(
    [
        StructField("ingested_at", StringType(), nullable=False),
        StructField("endpoint", StringType(), nullable=False),
        StructField("request_stop_id", StringType(), nullable=True),
        StructField("request_line_id", StringType(), nullable=True),
        StructField("api_datetime", StringType(), nullable=True),
        StructField("api_code", StringType(), nullable=False),
        StructField("api_description", StringType(), nullable=True),
        StructField("payload_json", StringType(), nullable=False),
    ]
)

df = spark.createDataFrame(rows, schema=bronze_schema)
df.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(bronze_table)

print(f"Appended {len(rows)} row(s) to {bronze_table}")
display(spark.table(bronze_table).orderBy("ingested_at", ascending=False).limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick check — buses arriving now (first stop in list)
# MAGIC Answers: *¿Qué buses van a llegar a la parada Y ahora mismo?*

# COMMAND ----------

import json as _json

check_stop = parsed_stop_ids[0]
latest = (
    spark.table(bronze_table)
    .filter(f"request_stop_id = '{check_stop}'")
    .orderBy("ingested_at", ascending=False)
    .limit(1)
    .collect()
)
if not latest:
    print(f"No bronze data yet for stop {check_stop}")
else:
    payload = _json.loads(latest[0]["payload_json"])
    print(f"Parada {check_stop} — llegadas estimadas ahora:")
    printed = 0
    for block in payload.get("data", []):
        for arr in block.get("Arrive", []) or []:
            eta_s = arr.get("estimateArrive")
            eta_min = f"{int(eta_s) // 60} min" if eta_s is not None else "?"
            print(
                f"  · línea {arr.get('line')} · bus {arr.get('bus')} "
                f"→ {arr.get('destination', '').strip()} · ~{eta_min}"
            )
            printed += 1
    if printed == 0:
        print("  (sin estimaciones en este momento — snapshot vacío, no es error)")
