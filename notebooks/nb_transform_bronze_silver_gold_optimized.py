# Fabric notebook source — docs v1.1 (Spark-optimized)
#
# How to use (Fabric UI):
#   1. Prereqs: nb_create_tables → nb_bootstrap_gtfs_silver → nb_ingest_emt_arrives
#   2. New Notebook → name: nb_transform_bronze_silver_gold_optimized → attach Lakehouse
#   3. Split on "# COMMAND ----------" → Run All
#   4. Prefer this notebook in the ~60s Pipeline (faster than Python collect version)
#   5. Idempotency / row checks → use a separate QA notebook (not this path)
#
# Contract: docs/03, docs/04 §6–§8, docs/05 §2–§3
# Fixes vs naive Spark rewrite:
#   - snapshot time from payload_json.datetime (no bronze api_datetime column)
#   - _rk material matches legacy: sha256(f"{stop_id}{line_id}{bus_id}{iso_seconds}")
#   - line_id priority: StopInfo.lines label match → silver_stop_lines → silver_lines_dim

# COMMAND ----------

# MAGIC %md
# MAGIC # Transform bronze → silver → gold (optimized)
# MAGIC Pure Spark: `from_json` / explode / broadcast joins — no `collect()` loops.
# MAGIC - Silver: Arrive[] → `silver_arrival_observations` (`_rk` anti-join)
# MAGIC - Gold: catalogue LEFT JOIN latest poll → overwrite `gold_stop_line_eta_latest`
# MAGIC - Empty Arrive still rebuilds gold (`docs/04` §8)

# COMMAND ----------

poll_interval_sec = 60  # @param {type:"number"}
stale_multiplier = 3  # @param {type:"number"}
bronze_table = "bronze_emt_raw"  # @param {type:"string"}
# True = only bronze newer than last silver ingested_at (Pipeline)
incremental = True  # @param {type:"boolean"}

# COMMAND ----------

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

STALE_AFTER_SEC = int(poll_interval_sec) * int(stale_multiplier)

# Write-heavy small PoC jobs: avoid excess shuffle partitions
spark.conf.set("spark.sql.shuffle.partitions", "8")
spark.conf.set("spark.sql.adaptive.enabled", "true")

# --- JSON schemas (MVP fields only) ---
arrive_schema = StructType(
    [
        StructField("stop", StringType(), True),
        StructField("line", StringType(), True),
        StructField("bus", StringType(), True),
        StructField("destination", StringType(), True),
        StructField("estimateArrive", StringType(), True),
    ]
)
stop_line_schema = StructType(
    [
        StructField("line", StringType(), True),
        StructField("label", StringType(), True),
    ]
)
stop_info_schema = StructType(
    [
        StructField("lines", ArrayType(stop_line_schema), True),
    ]
)
data_block_schema = StructType(
    [
        StructField("Arrive", ArrayType(arrive_schema), True),
        StructField("StopInfo", ArrayType(stop_info_schema), True),
    ]
)
payload_schema = StructType(
    [
        StructField("datetime", StringType(), True),
        StructField("data", ArrayType(data_block_schema), True),
    ]
)


def envelope_datetime_utc(col):
    """docs/04: naive envelope datetime = Europe/Madrid → UTC; truncate to seconds."""
    # EMT arrives samples are naive local wall-clock; treat as Madrid then store UTC.
    return F.date_trunc(
        "second",
        F.to_utc_timestamp(F.to_timestamp(col), "Europe/Madrid"),
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze → `silver_arrival_observations`

# COMMAND ----------

bronze = (
    spark.table(bronze_table)
    .filter((F.col("api_code") == "00") & (F.col("endpoint") == "arrives"))
    .select("ingested_at", "request_stop_id", "payload_json")
)

if incremental and spark.catalog.tableExists("silver_arrival_observations"):
    max_row = (
        spark.table("silver_arrival_observations")
        .select(F.max("ingested_at").alias("max_ingested_at"))
        .first()
    )
    max_ingested_at = max_row["max_ingested_at"] if max_row else None
    if max_ingested_at is not None:
        bronze = bronze.filter(F.col("ingested_at") > F.lit(max_ingested_at))
        print(f"Incremental: bronze ingested_at > {max_ingested_at}")

parsed = (
    bronze.withColumn("payload", F.from_json("payload_json", payload_schema))
    .filter(F.col("payload").isNotNull())
    .withColumn("datetime_polling", envelope_datetime_utc(F.col("payload.datetime")))
    .withColumn("data_block", F.explode_outer("payload.data"))
)

# Priority-1 line_id map: StopInfo.lines label → line (same poll / stop)
stopinfo_lines = (
    parsed.withColumn("si", F.explode_outer("data_block.StopInfo"))
    .withColumn("ln", F.explode_outer("si.lines"))
    .select(
        F.col("request_stop_id").cast("int").alias("si_stop_id"),
        "ingested_at",
        "datetime_polling",
        F.trim(F.col("ln.label")).alias("si_label"),
        F.trim(F.col("ln.line").cast("string")).alias("si_line_id"),
    )
    .filter(
        F.col("si_label").isNotNull()
        & (F.col("si_label") != "")
        & F.col("si_line_id").isNotNull()
        & (F.col("si_line_id") != "")
    )
    .dropDuplicates(["si_stop_id", "ingested_at", "datetime_polling", "si_label"])
)

arrives = (
    parsed.withColumn("arrive", F.explode_outer("data_block.Arrive"))
    .filter(F.col("arrive").isNotNull())
    .select(
        F.coalesce(
            F.col("arrive.stop").cast("int"),
            F.col("request_stop_id").cast("int"),
        ).alias("stop_id"),
        F.trim(F.col("arrive.line")).alias("line_label"),
        F.trim(F.col("arrive.bus").cast("string")).alias("bus_id"),
        F.trim(F.coalesce(F.col("arrive.destination"), F.lit(""))).alias("destination"),
        F.col("arrive.estimateArrive").cast("int").alias("eta_seconds"),
        "datetime_polling",
        "ingested_at",
        F.col("request_stop_id").cast("int").alias("request_stop_id"),
    )
    .filter(
        F.col("stop_id").isNotNull()
        & F.col("line_label").isNotNull()
        & (F.col("line_label") != "")
        & F.col("bus_id").isNotNull()
        & (F.col("bus_id") != "")
        & F.col("datetime_polling").isNotNull()
    )
)

stop_lines_lookup = (
    spark.table("silver_stop_lines")
    .select(
        F.col("stop_id").cast("int").alias("sl_stop_id"),
        F.trim("line_label").alias("sl_line_label"),
        F.col("line_id").cast("string").alias("sl_line_id"),
    )
    .dropDuplicates(["sl_stop_id", "sl_line_label"])
)

lines_lookup = (
    spark.table("silver_lines_dim")
    .select(
        F.trim("line_label").alias("ld_line_label"),
        F.col("line_id").cast("string").alias("ld_line_id"),
    )
    .dropDuplicates(["ld_line_label"])
)

silver_candidates = (
    arrives.alias("a")
    .join(
        stopinfo_lines.alias("si"),
        (F.col("a.stop_id") == F.col("si.si_stop_id"))
        & (F.col("a.ingested_at") == F.col("si.ingested_at"))
        & (F.col("a.datetime_polling") == F.col("si.datetime_polling"))
        & (F.col("a.line_label") == F.col("si.si_label")),
        "left",
    )
    .join(
        F.broadcast(stop_lines_lookup),
        (F.col("a.stop_id") == F.col("sl_stop_id"))
        & (F.col("a.line_label") == F.col("sl_line_label")),
        "left",
    )
    .join(
        F.broadcast(lines_lookup),
        F.col("a.line_label") == F.col("ld_line_label"),
        "left",
    )
    .withColumn(
        "line_id",
        F.coalesce(F.col("si.si_line_id"), F.col("sl_line_id"), F.col("ld_line_id")),
    )
    .filter(F.col("line_id").isNotNull())
    # Legacy _rk material (no separators) — keep stable vs Python notebook / existing silver
    .withColumn(
        "_rk",
        F.sha2(
            F.concat(
                F.col("a.stop_id").cast("string"),
                F.col("line_id"),
                F.col("a.bus_id"),
                F.date_format(F.col("a.datetime_polling"), "yyyy-MM-dd'T'HH:mm:ss"),
            ),
            256,
        ),
    )
    .select(
        "_rk",
        F.col("a.stop_id").alias("stop_id"),
        "line_id",
        F.col("a.line_label").alias("line_label"),
        F.col("a.bus_id").alias("bus_id"),
        F.col("a.destination").alias("destination"),
        F.col("a.eta_seconds").alias("eta_seconds"),
        F.col("a.datetime_polling").alias("datetime_polling"),
        F.col("a.ingested_at").alias("ingested_at"),
    )
    .dropDuplicates(["_rk"])
)

if spark.catalog.tableExists("silver_arrival_observations"):
    existing_keys = spark.table("silver_arrival_observations").select("_rk")
    new_silver = silver_candidates.join(existing_keys, on="_rk", how="left_anti")
else:
    new_silver = silver_candidates

new_silver = new_silver.cache()
inserted = new_silver.count()

if inserted > 0:
    (
        new_silver.coalesce(1)
        .write.format("delta")
        .mode("append")
        .saveAsTable("silver_arrival_observations")
    )

new_silver.unpersist()
print(f"Inserted silver observations: {inserted}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver → `gold_stop_line_eta_latest`
# MAGIC Latest successful bronze poll per stop (from `payload_json.datetime`) + catalogue LEFT JOIN.

# COMMAND ----------

latest_window = Window.partitionBy("request_stop_id").orderBy(F.col("ingested_at").desc())

latest_poll = (
    spark.table(bronze_table)
    .filter((F.col("api_code") == "00") & (F.col("endpoint") == "arrives"))
    .withColumn("payload", F.from_json("payload_json", payload_schema))
    .withColumn("rn", F.row_number().over(latest_window))
    .filter(F.col("rn") == 1)
    .select(
        F.col("request_stop_id").cast("int").alias("stop_id"),
        envelope_datetime_utc(F.col("payload.datetime")).alias("latest_snapshot_ts"),
    )
    .filter(F.col("latest_snapshot_ts").isNotNull())
)

observations = spark.table("silver_arrival_observations")

latest_observations = observations.alias("o").join(
    latest_poll.alias("p"),
    (F.col("o.stop_id") == F.col("p.stop_id"))
    & (F.col("o.datetime_polling") == F.col("p.latest_snapshot_ts")),
    "inner",
)

best_bus_window = Window.partitionBy("o.stop_id", "o.line_id").orderBy(
    F.col("o.eta_seconds").isNull().cast("int").asc(),
    F.col("o.eta_seconds").asc_nulls_last(),
    F.col("o.bus_id").asc(),
)

best_observation = (
    latest_observations.withColumn("rn", F.row_number().over(best_bus_window))
    .filter(F.col("rn") == 1)
    .select(
        F.col("o.stop_id").alias("obs_stop_id"),
        F.col("o.line_id").alias("obs_line_id"),
        F.col("o.destination").alias("obs_destination"),
        F.col("o.eta_seconds"),
    )
)

catalogue = (
    spark.table("silver_stop_lines")
    .groupBy("stop_id", "line_id", "line_label")
    .agg(F.max(F.col("is_terminus").cast("int")).cast("boolean").alias("is_terminus"))
)

line_headers = (
    spark.table("silver_lines_dim")
    .select("line_id", "name_a", "name_b")
    .dropDuplicates(["line_id"])
)

gold_df = (
    catalogue.alias("c")
    .join(latest_poll.alias("p"), F.col("c.stop_id") == F.col("p.stop_id"), "inner")
    .join(
        best_observation.alias("o"),
        (F.col("c.stop_id") == F.col("o.obs_stop_id"))
        & (F.col("c.line_id") == F.col("o.obs_line_id")),
        "left",
    )
    .join(F.broadcast(line_headers).alias("l"), F.col("c.line_id") == F.col("l.line_id"), "left")
    .select(
        F.col("c.stop_id").cast("int").alias("stop_id"),
        F.col("c.line_id").cast("string").alias("line_id"),
        F.col("c.line_label").cast("string").alias("line_label"),
        F.coalesce(
            F.nullif(F.trim(F.col("o.obs_destination")), F.lit("")),
            F.nullif(F.trim(F.col("l.name_a")), F.lit("")),
            F.nullif(F.trim(F.col("l.name_b")), F.lit("")),
            F.lit(""),
        ).alias("destination"),
        F.col("o.eta_seconds").cast("int").alias("eta_seconds"),
        F.col("o.eta_seconds").isNotNull().alias("has_upcoming_bus"),
        (F.col("c.is_terminus") & F.col("o.eta_seconds").isNull()).alias("origin_stop_notice"),
        (
            (
                F.unix_timestamp(F.current_timestamp())
                - F.unix_timestamp(F.col("p.latest_snapshot_ts"))
            )
            > F.lit(STALE_AFTER_SEC)
        ).alias("is_stale"),
        F.col("p.latest_snapshot_ts").alias("updated_at"),
    )
    .dropDuplicates(["stop_id", "line_id"])
)

gold_df = gold_df.cache()
gold_count = gold_df.count()

if gold_count == 0:
    gold_df.unpersist()
    raise RuntimeError(
        "No gold rows generated. Check latest bronze polls (payload.datetime) and catalogue."
    )

(
    gold_df.coalesce(1)
    .write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("gold_stop_line_eta_latest")
)

gold_df.unpersist()
print(f"Gold rows written: {gold_count}")
print(f"stale_after_sec = {STALE_AFTER_SEC}")
print("Done. Run QA notebook separately for idempotency / dup _rk checks.")
