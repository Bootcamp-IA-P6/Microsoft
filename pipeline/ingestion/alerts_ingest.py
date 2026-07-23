"""S2 servicealerts → bronze."""
from __future__ import annotations

from pipeline.ingestion.bronze_writer import bronze_row_alerts
from pipeline.ingestion.gtfs_rt_client import decode_feed_to_dict, http_bytes
from pipeline.validation.schema import BRONZE_SCHEMA


def run_alerts_ingest(spark, *, url: str, bronze_table: str) -> dict:
    raw, status = http_bytes(url)
    payload = decode_feed_to_dict(raw)
    n_ent = len(payload.get("entity") or [])
    print(f"Fetched servicealerts HTTP {status}, bytes={len(raw)}, entities={n_ent}")
    row = bronze_row_alerts(status, payload)
    spark.createDataFrame([row], schema=BRONZE_SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(bronze_table)
    print(f"Appended 1 → {bronze_table} (resource_kind=servicealerts)")
    return payload
