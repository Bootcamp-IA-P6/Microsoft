"""Observed headway (ADR-038) from silver_arrives history."""
from __future__ import annotations

import statistics

from pyspark.sql import Window
from pyspark.sql import functions as F

from pipeline.config.constants import (
    FREQ_GAP_MAX_MIN,
    FREQ_GAP_MIN_MIN,
    FREQ_VISIT_BREAK_MIN,
    SILVER_ARRIVES,
)

def compute_freq_by_line_spark(spark, *, freq_min: int) -> dict[str, dict]:
    """Median headway (min) per line×window from visit first-seen observations.

    1) Sightings with bus_id at stop×line×direction×window
    2) New observation when first sighting of bus, or same bus reappears after
       FREQ_VISIT_BREAK_MIN
    3) Successive observation gaps within stop×line×direction×window
    4) Keep gaps in [FREQ_GAP_MIN_MIN, FREQ_GAP_MAX_MIN]
    5) Pool gaps by line×window → statistics.median; sample = observation count
    """
    polls = (
        spark.table(SILVER_ARRIVES)
        .filter(
            "bus_id IS NOT NULL AND map_ok = true AND day_type IN ('LA','SA','FE') "
            "AND direction_id IS NOT NULL"
        )
        .select(
            "stop_id",
            "line_id",
            "direction_id",
            "bus_id",
            "datetime_polling",
            F.when(F.col("day_type") == "LA", F.lit("weekday"))
            .otherwise(F.lit("weekend"))
            .alias("window"),
        )
        .dropDuplicates(
            [
                "stop_id",
                "line_id",
                "direction_id",
                "bus_id",
                "datetime_polling",
                "window",
            ]
        )
    )

    w_bus = Window.partitionBy(
        "stop_id", "line_id", "direction_id", "bus_id", "window"
    ).orderBy("datetime_polling")
    observations = (
        polls.withColumn("prev_bus_ts", F.lag("datetime_polling").over(w_bus))
        .withColumn(
            "gap_same_bus_min",
            F.when(
                F.col("prev_bus_ts").isNotNull(),
                (F.unix_timestamp("datetime_polling") - F.unix_timestamp("prev_bus_ts"))
                / 60.0,
            ),
        )
        .withColumn(
            "is_new_observation",
            F.col("prev_bus_ts").isNull()
            | (F.col("gap_same_bus_min") >= F.lit(FREQ_VISIT_BREAK_MIN)),
        )
        .filter(F.col("is_new_observation"))
        .select(
            "stop_id",
            "line_id",
            "direction_id",
            "window",
            F.col("datetime_polling").alias("obs_ts"),
        )
    )

    w_obs = Window.partitionBy(
        "stop_id", "line_id", "direction_id", "window"
    ).orderBy("obs_ts")
    gaps = (
        observations.withColumn("prev_obs", F.lag("obs_ts").over(w_obs))
        .withColumn(
            "gap_min",
            (F.unix_timestamp("obs_ts") - F.unix_timestamp("prev_obs")) / 60.0,
        )
        .filter(
            F.col("prev_obs").isNotNull()
            & (F.col("gap_min") >= F.lit(FREQ_GAP_MIN_MIN))
            & (F.col("gap_min") <= F.lit(FREQ_GAP_MAX_MIN))
        )
        .select("line_id", "window", "gap_min")
    )

    n_by = {
        (r["line_id"], r["window"]): int(r["n"])
        for r in observations.groupBy("line_id", "window")
        .agg(F.count("*").alias("n"))
        .collect()
    }
    gaps_by: dict[tuple[str, str], list[float]] = {}
    for r in gaps.collect():
        gaps_by.setdefault((r["line_id"], r["window"]), []).append(float(r["gap_min"]))

    freq_by_line: dict[str, dict] = {}
    for lid, window in set(n_by) | set(gaps_by):
        n = n_by.get((lid, window), 0)
        gap_list = gaps_by.get((lid, window), [])
        med = float(statistics.median(gap_list)) if gap_list else None
        slot = freq_by_line.setdefault(
            lid,
            {
                "freq_observed_weekday_min": None,
                "freq_observed_weekend_min": None,
                "freq_sample_size_weekday": 0,
                "freq_sample_size_weekend": 0,
            },
        )
        if window == "weekday":
            slot["freq_sample_size_weekday"] = n
            slot["freq_observed_weekday_min"] = med if n >= freq_min else None
        else:
            slot["freq_sample_size_weekend"] = n
            slot["freq_observed_weekend_min"] = med if n >= freq_min else None
    return freq_by_line
