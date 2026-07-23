"""Spark StructTypes for bronze / silver / gold stages."""
from __future__ import annotations

from pyspark.sql.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

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

SILVER_ARRIVES_SCHEMA = StructType(
    [
        StructField("_rk", StringType(), False),
        StructField("stop_id", StringType(), False),
        StructField("line_id", StringType(), False),
        StructField("line_label", StringType(), False),
        StructField("direction_id", IntegerType(), True),
        StructField("bus_id", StringType(), True),
        StructField("destination", StringType(), True),
        StructField("eta_seconds", IntegerType(), True),
        StructField("datetime_polling", TimestampType(), False),
        StructField("ingested_at", TimestampType(), False),
        StructField("stop_name", StringType(), True),
        StructField("stop_lat", DoubleType(), True),
        StructField("stop_lon", DoubleType(), True),
        StructField("direction_text", StringType(), True),
        StructField("name_a", StringType(), True),
        StructField("name_b", StringType(), True),
        StructField("is_terminus", BooleanType(), True),
        StructField("catalog_loaded_at", DateType(), True),
        StructField("day_type", StringType(), True),
        StructField("map_ok", BooleanType(), True),
    ]
)

# Alias used by seed bootstrap
SILVER_SEED_SCHEMA = SILVER_ARRIVES_SCHEMA

GOLD_ARRIVES_SCHEMA = StructType(
    [
        StructField("stop_id", StringType(), False),
        StructField("line_id", StringType(), False),
        StructField("direction_id", IntegerType(), False),
        StructField("line_label", StringType(), False),
        StructField("stop_name", StringType(), False),
        StructField("direction_text", StringType(), True),
        StructField("name_a", StringType(), True),
        StructField("name_b", StringType(), True),
        StructField("destination", StringType(), True),
        StructField("eta_seconds_1", IntegerType(), True),
        StructField("bus_id_1", StringType(), True),
        StructField("eta_seconds_2", IntegerType(), True),
        StructField("bus_id_2", StringType(), True),
        StructField("has_upcoming_bus", BooleanType(), False),
        StructField("is_stale", BooleanType(), False),
        StructField("origin_stop_notice", BooleanType(), False),
        StructField("is_terminus", BooleanType(), False),
        StructField("catalog_loaded_at", DateType(), False),
        StructField("day_type", StringType(), False),
        StructField("updated_at", TimestampType(), False),
        StructField("freq_observed_weekday_min", DoubleType(), True),
        StructField("freq_observed_weekend_min", DoubleType(), True),
        StructField("freq_sample_size_weekday", IntegerType(), True),
        StructField("freq_sample_size_weekend", IntegerType(), True),
    ]
)

SILVER_ALERTS_SCHEMA = StructType(
    [
        StructField("_rk", StringType(), False),
        StructField("alert_id", StringType(), True),
        StructField("line_id", StringType(), True),
        StructField("alert_header", StringType(), True),
        StructField("alert_cause", StringType(), True),
        StructField("alert_effect", StringType(), True),
        StructField("alert_url", StringType(), True),
        StructField("active_period_start", TimestampType(), True),
        StructField("active_period_end", TimestampType(), True),
        StructField("snapshot_at", TimestampType(), True),
        StructField("ingested_at", TimestampType(), True),
        StructField("map_ok", BooleanType(), True),
    ]
)

GOLD_ALERT_STAGE_SCHEMA = StructType(
    [
        StructField("line_id", StringType(), False),
        StructField("alert_active", BooleanType(), False),
        StructField("alert_header", StringType(), True),
        StructField("alert_cause", StringType(), True),
        StructField("alert_effect", StringType(), True),
        StructField("alert_url", StringType(), True),
    ]
)
