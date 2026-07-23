"""Orchestrator: arrives poll + transform."""
from __future__ import annotations

from pipeline.aggregate.arrives_transform import run_transform
from pipeline.ingestion.arrives_ingest import run_direct_ingest


def run_arrives(
    spark,
    *,
    stop_ids: str = "",
    variable_library_name: str = "var_emt_madrid",
    bronze_table: str = "bronze_emt_raw",
    max_retries_per_stop: int = 2,
    token_skew_sec: int = 90,
    stale_after_sec: int = 900,
    incremental: bool = True,
    freq_min_samples: int = 20,
    verbose_display: bool = False,
) -> None:
    run_direct_ingest(
        spark,
        stop_ids=stop_ids,
        variable_library_name=variable_library_name,
        bronze_table=bronze_table,
        max_retries_per_stop=max_retries_per_stop,
        token_skew_sec=token_skew_sec,
        verbose_display=verbose_display,
    )
    run_transform(
        spark,
        stale_after_sec=stale_after_sec,
        bronze_table=bronze_table,
        incremental=incremental,
        freq_min_samples=freq_min_samples,
        verbose_display=verbose_display,
    )
