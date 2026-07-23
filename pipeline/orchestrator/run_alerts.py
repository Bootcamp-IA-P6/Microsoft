"""Orchestrator: S2 alerts ingest + transform (split for Phase 3)."""
from __future__ import annotations

from pipeline.aggregate.alerts_transform import run_alerts_transform
from pipeline.config.constants import (
    BRONZE_TABLE,
    GOLD_TABLE,
    SERVICEALERTS_URL,
    SILVER_ALERTS,
)
from pipeline.ingestion.alerts_ingest import run_alerts_ingest


def run_alerts_ingest_only(
    spark,
    *,
    bronze_table: str = BRONZE_TABLE,
    servicealerts_url: str = SERVICEALERTS_URL,
) -> dict:
    """HTTP → bronze only; returns decoded payload (optional for same-session use)."""
    return run_alerts_ingest(
        spark, url=servicealerts_url, bronze_table=bronze_table
    )


def run_alerts_transform_only(
    spark,
    *,
    bronze_table: str = BRONZE_TABLE,
    silver_alerts_table: str = SILVER_ALERTS,
    gold_table: str = GOLD_TABLE,
    verbose_display: bool = False,
    payload: dict | None = None,
) -> None:
    """Bronze (latest servicealerts) → silver_alerts → gold alert_* (no HTTP)."""
    run_alerts_transform(
        spark,
        payload,
        silver_alerts_table=silver_alerts_table,
        gold_table=gold_table,
        bronze_table=bronze_table,
        verbose_display=verbose_display,
    )


def run_alerts(
    spark,
    *,
    bronze_table: str = BRONZE_TABLE,
    silver_alerts_table: str = SILVER_ALERTS,
    gold_table: str = GOLD_TABLE,
    servicealerts_url: str = SERVICEALERTS_URL,
    verbose_display: bool = False,
) -> None:
    """Combined ingest+transform (debug / single-notebook fallback)."""
    payload = run_alerts_ingest_only(
        spark, bronze_table=bronze_table, servicealerts_url=servicealerts_url
    )
    run_alerts_transform_only(
        spark,
        bronze_table=bronze_table,
        silver_alerts_table=silver_alerts_table,
        gold_table=gold_table,
        verbose_display=verbose_display,
        payload=payload,
    )
