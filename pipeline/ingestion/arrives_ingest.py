"""S1 arrives → bronze."""
from __future__ import annotations

import time

from pipeline.config.settings import load_emt_credentials
from pipeline.ingestion.bronze_writer import bronze_row
from pipeline.ingestion.emt_client import EmtTokenSession, TokenExpiredError, fetch_arrives
from pipeline.transform.enrich import resolve_stop_ids
from pipeline.validation.schema import BRONZE_SCHEMA


def run_direct_ingest(
    spark,
    *,
    stop_ids: str,
    variable_library_name: str,
    bronze_table: str,
    max_retries_per_stop: int,
    token_skew_sec: int,
    verbose_display: bool = False,
) -> None:
    t_http0 = time.perf_counter()
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
    print(f"[phase1 timing] HTTP arrives poll: {time.perf_counter() - t_http0:.2f}s")
    if not rows:
        raise RuntimeError("No rows\n" + "\n".join(failures))

    t_w0 = time.perf_counter()
    spark.createDataFrame(rows, schema=BRONZE_SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(bronze_table)
    print(f"Appended {len(rows)} → {bronze_table}")
    print(f"[phase1 timing] bronze append: {time.perf_counter() - t_w0:.2f}s")
    for f in failures:
        print(f"  fail: {f}")
    if verbose_display:
        display(spark.table(bronze_table).orderBy("ingested_at", ascending=False).limit(10))
