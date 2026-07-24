"""Bronze row builders and Delta appends."""
from __future__ import annotations

import hashlib
import json
import uuid

from pipeline.common.datetime_utils import utc_now_iso_z
from pipeline.config.constants import BRONZE_TABLE, TZ_NOTE


def bronze_row(
    source_system: str,
    resource_kind: str,
    resource_key: str,
    http_status,
    payload_obj: dict,
) -> dict:
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


def bronze_row_alerts(http_status: int, payload_obj: dict) -> dict:
    payload_s = json.dumps(payload_obj, ensure_ascii=False)
    return {
        "ingest_id": str(uuid.uuid4()),
        "ingested_at": utc_now_iso_z(),
        "source_system": "MDB_GTFS_RT",
        "resource_kind": "servicealerts",
        "resource_key": "proto",
        "http_status": str(http_status),
        "api_code": "",
        "api_description": None,
        "payload": payload_s,
        "content_sha256": hashlib.sha256(payload_s.encode("utf-8")).hexdigest(),
        "timezone_note": TZ_NOTE,
    }


def append_bronze_rows(spark, rows: list[dict], *, table: str = BRONZE_TABLE) -> int:
    if not rows:
        return 0
    # Lazy: keeps bronze_row* usable without pyspark (Phase 4 / UDF).
    from pipeline.validation.schema import BRONZE_SCHEMA

    spark.createDataFrame(rows, schema=BRONZE_SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(table)
    return len(rows)
