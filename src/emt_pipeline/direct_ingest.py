import time

from pyspark.sql.types import StringType, StructField, StructType

from .common import (
    EmtTokenSession,
    TokenExpiredError,
    bronze_row,
    fetch_arrives,
    load_emt_credentials,
)
from .fabric import resolve_stop_ids


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

