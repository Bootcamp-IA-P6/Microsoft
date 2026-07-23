"""Catalogue / direction / stop-list helpers."""
from __future__ import annotations

from pyspark.sql import Window
from pyspark.sql import functions as F

from pipeline.common.parsing import norm_name
from pipeline.config.constants import SILVER_ARRIVES


def resolve_stop_ids(spark, override_csv: str) -> list[str]:
    manual = [s.strip() for s in str(override_csv or "").split(",") if s.strip()]
    if manual:
        print(f"Manual stop_ids ({len(manual)}): {manual}")
        return manual
    if not spark.catalog.tableExists(SILVER_ARRIVES):
        raise RuntimeError("silver_arrives missing — run nb_bootstrap_gtfs_silver first")
    rows = (
        spark.table(SILVER_ARRIVES)
        .select("stop_id")
        .distinct()
        .orderBy("stop_id")
        .collect()
    )
    ids = [str(r["stop_id"]) for r in rows]
    if not ids:
        raise RuntimeError("silver_arrives has no stop_id — re-run bootstrap")
    print(f"Loaded {len(ids)} stop_id(s) from silver_arrives")
    return ids


def latest_catalog_rows(spark):
    from pyspark.sql import Window

    catalog = (
        spark.table(SILVER_ARRIVES)
        .filter("bus_id IS NULL AND map_ok = true AND direction_id IS NOT NULL")
        .select(
            "stop_id",
            "line_id",
            "line_label",
            "direction_id",
            "stop_name",
            "stop_lat",
            "stop_lon",
            "direction_text",
            "name_a",
            "name_b",
            "is_terminus",
            "catalog_loaded_at",
            "day_type",
        )
    )
    return (
        catalog.withColumn(
            "_rn",
            F.row_number().over(
                Window.partitionBy("stop_id", "line_id", "direction_id").orderBy(
                    F.col("catalog_loaded_at").desc_nulls_last()
                )
            ),
        )
        .filter("_rn = 1")
        .drop("_rn")
        .collect()
    )


def map_destination_to_direction(destination: str | None, name_a, name_b) -> int | None:
    d = norm_name(destination)
    if not d:
        return None
    nb, na = norm_name(name_b), norm_name(name_a)
    if nb and (d == nb or nb in d or d in nb):
        return 0
    if na and (d == na or na in d or d in na):
        return 1
    return None
