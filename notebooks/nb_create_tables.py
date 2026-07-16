# Fabric notebook source — docs v1.1
#
# How to use (Fabric UI):
#   1. Workspace → New item → Lakehouse (e.g. lh_emt_madrid)
#   2. Workspace → New item → Notebook → name: nb_create_tables
#   3. Attach Lakehouse as default
#   4. Split on "# COMMAND ----------" into cells → Run All
#
# Contract: docs/03-schema-contract.md (MVP tables only)

# COMMAND ----------

# MAGIC %md
# MAGIC # Create medallion tables (empty)
# MAGIC MVP tables from `docs/03` v1.1. Safe to re-run (`IF NOT EXISTS`).
# MAGIC
# MAGIC **Does not create** postponed tables (`silver_incidents`, `gold_incident_line_current`, `gold_line_status_5m`).

# COMMAND ----------

# Bronze — docs/03 §3 (field list from PO; types chosen for Spark / silver joins)
spark.sql(
    """
    CREATE TABLE IF NOT EXISTS bronze_emt_raw (
      ingested_at TIMESTAMP,
      endpoint STRING,
      request_stop_id INT,
      api_code STRING,
      api_description STRING,
      payload_json STRING
    ) USING DELTA
    """
)

# Silver observations — docs/03 §4
spark.sql(
    """
    CREATE TABLE IF NOT EXISTS silver_arrival_observations (
      _rk STRING NOT NULL,
      stop_id INT NOT NULL,
      line_id STRING NOT NULL,
      line_label STRING NOT NULL,
      bus_id STRING NOT NULL,
      destination STRING NOT NULL,
      eta_seconds INT,
      datetime_polling TIMESTAMP NOT NULL,
      ingested_at TIMESTAMP NOT NULL
    ) USING DELTA
    """
)

# Silver dims — docs/03 §5–§7
spark.sql(
    """
    CREATE TABLE IF NOT EXISTS silver_stops_dim (
      stop_id INT,
      stop_name STRING,
      stop_lat DOUBLE,
      stop_lon DOUBLE,
      direction_text STRING,
      in_scope BOOLEAN,
      catalog_loaded_at DATE
    ) USING DELTA
    """
)

spark.sql(
    """
    CREATE TABLE IF NOT EXISTS silver_lines_dim (
      line_id STRING,
      line_label STRING,
      name_a STRING,
      name_b STRING,
      in_scope BOOLEAN,
      catalog_loaded_at DATE
    ) USING DELTA
    """
)

spark.sql(
    """
    CREATE TABLE IF NOT EXISTS silver_stop_lines (
      stop_id INT,
      line_id STRING,
      line_label STRING,
      is_terminus BOOLEAN,
      direction_id INT,
      catalog_loaded_at DATE
    ) USING DELTA
    """
)

# Gold — docs/03 §8
spark.sql(
    """
    CREATE TABLE IF NOT EXISTS gold_stop_line_eta_latest (
      stop_id INT NOT NULL,
      line_id STRING NOT NULL,
      line_label STRING NOT NULL,
      destination STRING NOT NULL,
      eta_seconds INT,
      has_upcoming_bus BOOLEAN NOT NULL,
      origin_stop_notice BOOLEAN NOT NULL,
      is_stale BOOLEAN NOT NULL,
      updated_at TIMESTAMP NOT NULL
    ) USING DELTA
    """
)

print("Tables ready (docs/03 v1.1 MVP):")
for t in [
    "bronze_emt_raw",
    "silver_arrival_observations",
    "silver_stops_dim",
    "silver_lines_dim",
    "silver_stop_lines",
    "gold_stop_line_eta_latest",
]:
    print(f"  {t}: {spark.table(t).count()} row(s)")
