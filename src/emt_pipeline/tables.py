def recreate_tables(spark) -> None:
    legacy_tables = [
        "bronze_emt_es",
        "gold_stop_line_eta_latest",
        "silver_arrival_observations",
        "silver_stops_dim",
        "silver_lines_dim",
        "silver_stop_lines",
    ]
    for t in legacy_tables:
        if spark.catalog.tableExists(t):
            spark.sql(f"DROP TABLE {t}")
            print(f"DROPPED legacy: {t}")

    for t in ["gold_emt_stop_line", "silver_emt", "bronze_emt_raw"]:
        if spark.catalog.tableExists(t):
            spark.sql(f"DROP TABLE {t}")
            print(f"DROPPED: {t}")

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
        CREATE TABLE IF NOT EXISTS silver_emt (
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

    print("Tables ready (contract v4.2 — ADR-015: 3 tables):")
    for t in ["bronze_emt_raw", "silver_emt", "gold_emt_stop_line"]:
        print(f"  {t}: {spark.table(t).count()} row(s)")

