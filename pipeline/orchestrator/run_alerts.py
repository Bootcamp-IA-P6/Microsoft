"""Orchestrator: S2 alerts ingest + transform."""
from __future__ import annotations

from pipeline.aggregate.alerts_transform import run_alerts_transform
from pipeline.config.constants import (
    BRONZE_TABLE,
    GOLD_TABLE,
    SERVICEALERTS_URL,
    SILVER_ALERTS,
)
from pipeline.ingestion.alerts_ingest import run_alerts_ingest


def run_alerts(
    spark,
    *,
    bronze_table: str = BRONZE_TABLE,
    silver_alerts_table: str = SILVER_ALERTS,
    gold_table: str = GOLD_TABLE,
    servicealerts_url: str = SERVICEALERTS_URL,
    verbose_display: bool = False,
) -> None:
    payload = run_alerts_ingest(
        spark, url=servicealerts_url, bronze_table=bronze_table
    )
    run_alerts_transform(
        spark,
        payload,
        silver_alerts_table=silver_alerts_table,
        gold_table=gold_table,
        bronze_table=bronze_table,
        verbose_display=verbose_display,
    )
