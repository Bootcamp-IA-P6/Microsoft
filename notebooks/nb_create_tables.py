# Fabric notebook — contract v4.3 CREATE / migrate 
#
# Data-safe: does NOT drop bronze / gold / silver_arrives.
# Migrates silver_emt → silver_arrives (copy then drop old name).
# Guide: docs/manual-lakehouse-ingestion.md
# Contract: docs/data-source-contract-v4.md (v4.3)

# COMMAND ----------

# MAGIC %md
# MAGIC # Create / migrate tables (contract v4.3)
# MAGIC `bronze_emt_raw` · `silver_arrives` · `silver_alerts` · `gold_emt_stop_line`
# MAGIC Preserves existing data. Renames `silver_emt` → `silver_arrives` if needed.



# COMMAND ----------

spark.sql(
    """
    CREATE TABLE IF NOT EXISTS bronze_emt_raw (
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
    """
    CREATE TABLE IF NOT EXISTS silver_arrives (
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
    """
    CREATE TABLE IF NOT EXISTS silver_alerts (
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
    """
    CREATE TABLE IF NOT EXISTS gold_emt_stop_line (
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

print("Tables ready (contract v4.3 — bronze + silver_arrives + silver_alerts + gold):")
for t in ["bronze_emt_raw", "silver_arrives", "silver_alerts", "gold_emt_stop_line"]:
    if spark.catalog.tableExists(t):
        print(f"  {t}: {spark.table(t).count()} row(s)")
    else:
        print(f"  {t}: MISSING")
