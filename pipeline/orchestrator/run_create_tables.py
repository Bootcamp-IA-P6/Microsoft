"""Ensure contract v4.3.1 Lakehouse tables exist (data-safe)."""
from __future__ import annotations

from pipeline.config.constants import (
    BRONZE_TABLE,
    GOLD_TABLE,
    SILVER_ALERTS,
    SILVER_ARRIVES,
)


def run_create_tables(spark) -> None:
    """CREATE IF NOT EXISTS + optional silver_emt → silver_arrives migrate."""
    # Legacy rename (header promise in Phase 0 notebook)
    if spark.catalog.tableExists("silver_emt") and not spark.catalog.tableExists(
        SILVER_ARRIVES
    ):
        spark.sql(f"CREATE TABLE {SILVER_ARRIVES} AS SELECT * FROM silver_emt")
        print(
            f"MIGRATED silver_emt → {SILVER_ARRIVES} "
            f"({spark.table(SILVER_ARRIVES).count()} rows)"
        )
        spark.sql("DROP TABLE silver_emt")
        print("DROPPED silver_emt")
    elif spark.catalog.tableExists("silver_emt") and spark.catalog.tableExists(
        SILVER_ARRIVES
    ):
        spark.sql("DROP TABLE IF EXISTS silver_emt")
        print("DROPPED leftover silver_emt (silver_arrives already present)")

    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {BRONZE_TABLE} (
          ingest_id STRING,
          ingested_at STRING,
          source_system STRING,
          resource_kind STRING,
          resource_key STRING,
          http_status STRING,
          api_code STRING,
          api_description STRING,
          payload STRING,
          content_sha256 STRING,
          timezone_note STRING
        ) USING DELTA
        """
    )
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {SILVER_ARRIVES} (
          _rk STRING NOT NULL,
          stop_id STRING NOT NULL,
          line_id STRING NOT NULL,
          line_label STRING NOT NULL,
          direction_id INT,
          bus_id STRING,
          destination STRING,
          eta_seconds INT,
          datetime_polling TIMESTAMP NOT NULL,
          ingested_at TIMESTAMP NOT NULL,
          stop_name STRING,
          stop_lat DOUBLE,
          stop_lon DOUBLE,
          direction_text STRING,
          name_a STRING,
          name_b STRING,
          is_terminus BOOLEAN,
          catalog_loaded_at DATE,
          day_type STRING,
          map_ok BOOLEAN
        ) USING DELTA
        """
    )
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {SILVER_ALERTS} (
          _rk STRING NOT NULL,
          alert_id STRING,
          line_id STRING,
          alert_header STRING,
          alert_cause STRING,
          alert_effect STRING,
          alert_url STRING,
          active_period_start TIMESTAMP,
          active_period_end TIMESTAMP,
          snapshot_at TIMESTAMP,
          ingested_at TIMESTAMP,
          map_ok BOOLEAN
        ) USING DELTA
        """
    )
    spark.sql(
        f"""
        CREATE TABLE IF NOT EXISTS {GOLD_TABLE} (
          stop_id STRING NOT NULL,
          line_id STRING NOT NULL,
          direction_id INT NOT NULL,
          line_label STRING NOT NULL,
          stop_name STRING NOT NULL,
          direction_text STRING,
          name_a STRING,
          name_b STRING,
          destination STRING,
          eta_seconds_1 INT,
          bus_id_1 STRING,
          eta_seconds_2 INT,
          bus_id_2 STRING,
          has_upcoming_bus BOOLEAN NOT NULL,
          is_stale BOOLEAN NOT NULL,
          origin_stop_notice BOOLEAN NOT NULL,
          is_terminus BOOLEAN NOT NULL,
          catalog_loaded_at DATE NOT NULL,
          day_type STRING NOT NULL,
          updated_at TIMESTAMP NOT NULL,
          freq_observed_weekday_min DOUBLE,
          freq_observed_weekend_min DOUBLE,
          freq_sample_size_weekday INT,
          freq_sample_size_weekend INT,
          alert_active BOOLEAN NOT NULL,
          alert_header STRING,
          alert_cause STRING,
          alert_effect STRING,
          alert_url STRING
        ) USING DELTA
        """
    )

    print("Tables ready (contract v4.3.1 — bronze + silver_arrives + silver_alerts + gold):")
    for t in [BRONZE_TABLE, SILVER_ARRIVES, SILVER_ALERTS, GOLD_TABLE]:
        if spark.catalog.tableExists(t):
            print(f"  {t}: {spark.table(t).count()} row(s)")
        else:
            print(f"  {t}: MISSING")
