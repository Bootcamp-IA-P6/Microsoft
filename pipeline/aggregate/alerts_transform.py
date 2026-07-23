"""Alerts bronze payload → silver_alerts (latest-only) → gold alert_* MERGE."""
from __future__ import annotations

from datetime import datetime

from pipeline.aggregate.alerts_project import known_line_ids, project_gold_alerts
from pipeline.common.datetime_utils import MADRID, UTC
from pipeline.common.delta_retry import delta_sql_retry
from pipeline.config.constants import (
    BRONZE_TABLE,
    GOLD_TABLE,
    SILVER_ALERTS,
)
from pipeline.transform.alerts_normalize import expand_silver_rows
from pipeline.validation.schema import GOLD_ALERT_STAGE_SCHEMA, SILVER_ALERTS_SCHEMA


def run_alerts_transform(
    spark,
    payload: dict,
    *,
    silver_alerts_table: str = SILVER_ALERTS,
    gold_table: str = GOLD_TABLE,
    bronze_table: str = BRONZE_TABLE,
    verbose_display: bool = False,
) -> None:
    if not spark.catalog.tableExists(silver_alerts_table):
        raise RuntimeError(f"{silver_alerts_table} missing — run nb_create_tables")

    known = known_line_ids(spark, gold_table=gold_table)
    print(f"Known line_id count={len(known)}")
    ingested_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    silver_rows, snap = expand_silver_rows(payload, known, ingested_at)

    spark.sql(f"DELETE FROM {silver_alerts_table}")
    if silver_rows:
        spark.createDataFrame(silver_rows, schema=SILVER_ALERTS_SCHEMA).write.format(
            "delta"
        ).mode("append").saveAsTable(silver_alerts_table)
    print(f"{silver_alerts_table} rows written={len(silver_rows)} snapshot_at={snap}")

    now_naive = datetime.now(MADRID).astimezone(UTC).replace(tzinfo=None, microsecond=0)
    stage = project_gold_alerts(
        spark,
        now_naive=now_naive,
        gold_table=gold_table,
        silver_alerts_table=silver_alerts_table,
    )
    if not stage:
        print("No gold lines to update")
        return

    spark.createDataFrame(stage, schema=GOLD_ALERT_STAGE_SCHEMA).createOrReplaceTempView(
        "gold_alerts_stage"
    )
    delta_sql_retry(
        spark,
        f"""
        MERGE INTO {gold_table} AS t
        USING gold_alerts_stage AS s
        ON t.line_id = s.line_id
        WHEN MATCHED THEN UPDATE SET
          t.alert_active = s.alert_active,
          t.alert_header = s.alert_header,
          t.alert_cause = s.alert_cause,
          t.alert_effect = s.alert_effect,
          t.alert_url = s.alert_url
        """,
        label="gold alerts MERGE",
    )
    print(f"MERGE {gold_table} alert_* by line_id done")
    if verbose_display:
        display(  # noqa: F821 — Fabric notebook builtin
            spark.table(gold_table)
            .filter("alert_active = true")
            .select(
                "stop_id",
                "line_id",
                "direction_id",
                "alert_active",
                "alert_header",
                "alert_cause",
                "alert_effect",
            )
            .orderBy("line_id", "stop_id")
            .limit(40)
        )
        print("=== SUMMARY (contract v4.3 alerts) ===")
        print(f"bronze={spark.table(bronze_table).count()}")
        print(f"silver_alerts={spark.table(silver_alerts_table).count()}")
        print(
            f"gold alert_active=true: "
            f"{spark.table(gold_table).filter('alert_active = true').count()}"
        )
    else:
        print("=== SUMMARY (contract v4.3 alerts · phase2) ===")
        print(f"stage_lines={len(stage)} verbose_display=False")
