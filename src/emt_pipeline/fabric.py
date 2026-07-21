from pyspark.sql import functions as F


def resolve_stop_ids(spark, override_csv: str) -> list[str]:
    manual = [s.strip() for s in str(override_csv or "").split(",") if s.strip()]
    if manual:
        print(f"Manual stop_ids ({len(manual)}): {manual}")
        return manual
    if not spark.catalog.tableExists("silver_emt"):
        raise RuntimeError("silver_emt missing — run nb_bootstrap_silver_emt first")
    rows = (
        spark.table("silver_emt")
        .select("stop_id")
        .distinct()
        .orderBy("stop_id")
        .collect()
    )
    ids = [str(r["stop_id"]) for r in rows]
    if not ids:
        raise RuntimeError("silver_emt has no stop_id — re-run bootstrap")
    print(f"Loaded {len(ids)} stop_id(s) from silver_emt")
    return ids


def latest_catalog_rows(spark):
    from pyspark.sql import Window

    catalog = (
        spark.table("silver_emt")
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

